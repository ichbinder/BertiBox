"""Tests for PlaylistManager class."""

import unittest
from unittest.mock import MagicMock, Mock, patch
from src.database.playlist_manager import PlaylistManager
from src.database.models import Tag, Playlist, PlaylistItem


class TestPlaylistManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.get_session = Mock(return_value=self.mock_session)
        self.playlist_manager = PlaylistManager(self.get_session)
    
    def test_add_playlist_with_existing_tag(self):
        """Test adding a playlist to an existing tag."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_playlist = MagicMock(spec=Playlist)
        mock_playlist.tag = mock_tag
        
        self.mock_session.query().filter_by().first.return_value = mock_tag
        
        with patch('src.database.playlist_manager.Playlist', return_value=mock_playlist):
            result = self.playlist_manager.add_playlist("TEST_TAG", "Test Playlist")
        
        self.assertEqual(result, mock_playlist)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_add_playlist_creates_new_tag(self):
        """Test adding a playlist creates a new tag if needed."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_playlist = MagicMock(spec=Playlist)
        mock_playlist.tag = mock_tag
        
        self.mock_session.query().filter_by().first.return_value = None
        
        with patch('src.database.playlist_manager.Tag', return_value=mock_tag):
            with patch('src.database.playlist_manager.Playlist', return_value=mock_playlist):
                result = self.playlist_manager.add_playlist("NEW_TAG", "Test Playlist")
        
        self.assertEqual(result, mock_playlist)
        # Tag should be added
        self.assertEqual(self.mock_session.add.call_count, 2)
        self.mock_session.flush.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_get_playlist(self):
        """Test getting a playlist."""
        mock_playlist = MagicMock(spec=Playlist)
        mock_playlist.id = 1
        mock_playlist.tag = MagicMock()
        mock_playlist.items = []
        
        self.mock_session.query().filter_by().first.return_value = mock_playlist
        
        result = self.playlist_manager.get_playlist(1)
        
        self.assertEqual(result, mock_playlist)
        self.mock_session.expunge.assert_called_once_with(mock_playlist)
        self.mock_session.close.assert_called_once()
    
    def test_get_playlist_not_found(self):
        """Test getting a non-existent playlist."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.playlist_manager.get_playlist(999)
        
        self.assertIsNone(result)
        self.mock_session.close.assert_called_once()
    
    def test_add_playlist_item(self):
        """Test adding an item to a playlist."""
        mock_playlist = MagicMock(spec=Playlist)
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.id = 1
        mock_item.playlist_id = 1
        mock_item.mp3_file = "test.mp3"
        mock_item.position = 0
        
        self.mock_session.query().filter_by().first.return_value = mock_playlist
        self.mock_session.query().filter_by().count.return_value = 0
        
        with patch('src.database.playlist_manager.PlaylistItem', return_value=mock_item):
            result = self.playlist_manager.add_playlist_item(1, "test.mp3")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['mp3_file'], "test.mp3")
        self.assertEqual(result['position'], 0)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_add_playlist_item_invalid_playlist(self):
        """Test adding an item to a non-existent playlist."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.playlist_manager.add_playlist_item(999, "test.mp3")
        
        self.assertIsNone(result)
        self.mock_session.add.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_get_playlist_items(self):
        """Test getting playlist items."""
        mock_item1 = MagicMock(spec=PlaylistItem)
        mock_item1.id = 1
        mock_item1.playlist_id = 1
        mock_item1.mp3_file = "song1.mp3"
        mock_item1.position = 0
        
        mock_item2 = MagicMock(spec=PlaylistItem)
        mock_item2.id = 2
        mock_item2.playlist_id = 1
        mock_item2.mp3_file = "song2.mp3"
        mock_item2.position = 1
        
        self.mock_session.query().filter_by().order_by().all.return_value = [mock_item1, mock_item2]
        
        result = self.playlist_manager.get_playlist_items(1)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['mp3_file'], "song1.mp3")
        self.assertEqual(result[1]['mp3_file'], "song2.mp3")
        self.mock_session.close.assert_called_once()
    
    def test_delete_playlist_item(self):
        """Test deleting a playlist item."""
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.playlist_id = 1
        mock_item.position = 1
        
        remaining_item = MagicMock(spec=PlaylistItem)
        remaining_item.id = 2
        remaining_item.position = 2
        remaining_item.mp3_file = "remaining.mp3"
        
        self.mock_session.query().filter_by().first.return_value = mock_item
        self.mock_session.query().filter_by().order_by().all.return_value = [remaining_item]
        
        result = self.playlist_manager.delete_playlist_item(1)
        
        self.assertTrue(result)
        self.mock_session.delete.assert_called_once_with(mock_item)
        self.mock_session.commit.assert_called()
        self.assertEqual(remaining_item.position, 0)  # Should be resequenced
        self.mock_session.close.assert_called_once()
    
    def test_delete_playlist_item_not_found(self):
        """Test deleting a non-existent item."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.playlist_manager.delete_playlist_item(999)
        
        self.assertFalse(result)
        self.mock_session.delete.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_update_playlist_item_position_move_down(self):
        """Test moving an item down in the playlist."""
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.playlist_id = 1
        mock_item.position = 0
        
        self.mock_session.query().filter_by().first.return_value = mock_item
        
        result = self.playlist_manager.update_playlist_item_position(1, 2)
        
        self.assertTrue(result)
        self.assertEqual(mock_item.position, 2)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_update_playlist_item_position_move_up(self):
        """Test moving an item up in the playlist."""
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.playlist_id = 1
        mock_item.position = 3
        
        self.mock_session.query().filter_by().first.return_value = mock_item
        
        result = self.playlist_manager.update_playlist_item_position(1, 1)
        
        self.assertTrue(result)
        self.assertEqual(mock_item.position, 1)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_update_playlist_item_position_same(self):
        """Test updating position to the same position."""
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.position = 2
        
        self.mock_session.query().filter_by().first.return_value = mock_item
        
        result = self.playlist_manager.update_playlist_item_position(1, 2)
        
        self.assertTrue(result)
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_add_playlist_items_batch(self):
        """Test adding multiple items at once."""
        mock_playlist = MagicMock(spec=Playlist)
        self.mock_session.query().filter_by().first.return_value = mock_playlist
        self.mock_session.query().filter_by().count.return_value = 2  # Existing items
        
        mp3_files = ["song1.mp3", "song2.mp3", "song3.mp3"]
        
        # Mock PlaylistItem creation
        mock_items = []
        for i, mp3 in enumerate(mp3_files):
            mock_item = MagicMock(spec=PlaylistItem)
            mock_item.id = i + 1
            mock_item.playlist_id = 1
            mock_item.mp3_file = mp3
            mock_item.position = 2 + i
            mock_items.append(mock_item)
        
        with patch('src.database.playlist_manager.PlaylistItem', side_effect=mock_items):
            result = self.playlist_manager.add_playlist_items(1, mp3_files)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['mp3_file'], "song1.mp3")
        self.assertEqual(result[0]['position'], 2)
        self.assertEqual(result[2]['position'], 4)
        self.assertEqual(self.mock_session.add.call_count, 3)
        self.mock_session.flush.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_assign_tag_to_file(self):
        """Test assigning a tag to a file."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_tag.name = "Test Tag"
        
        mock_playlist = MagicMock(spec=Playlist)
        mock_playlist.id = 1
        mock_playlist.name = "Test Playlist"
        mock_tag.playlists = [mock_playlist]
        
        self.mock_session.query().filter().first.return_value = mock_tag
        
        # Mock the add_playlist_item method
        with patch.object(self.playlist_manager, 'add_playlist_item', return_value={'id': 1}) as mock_add:
            result = self.playlist_manager.assign_tag_to_file(1, "test.mp3")
        
        self.assertTrue(result)
        mock_add.assert_called_once_with(1, "test.mp3")
        self.mock_session.close.assert_called_once()
    
    def test_assign_tag_to_file_no_tag(self):
        """Test assigning a non-existent tag to a file."""
        self.mock_session.query().filter().first.return_value = None
        
        result = self.playlist_manager.assign_tag_to_file(999, "test.mp3")
        
        self.assertFalse(result)
        self.mock_session.close.assert_called_once()
    
    def test_assign_tag_to_file_no_playlist(self):
        """Test assigning a tag with no playlist to a file."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_tag.name = "Test Tag"
        mock_tag.playlists = []
        
        self.mock_session.query().filter().first.return_value = mock_tag
        
        result = self.playlist_manager.assign_tag_to_file(1, "test.mp3")
        
        self.assertFalse(result)
        self.mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()