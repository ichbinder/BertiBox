"""Tests for TagManager class."""

import unittest
from unittest.mock import MagicMock, Mock
from src.database.tag_manager import TagManager
from src.database.models import Tag, Playlist


class TestTagManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.get_session = Mock(return_value=self.mock_session)
        self.tag_manager = TagManager(self.get_session)
    
    def test_add_tag(self):
        """Test adding a new tag."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_tag.tag_id = "TEST_TAG"
        mock_tag.name = "Test Tag"
        
        self.mock_session.add = MagicMock()
        self.mock_session.commit = MagicMock()
        self.mock_session.refresh = MagicMock()
        self.mock_session.expunge = MagicMock()
        
        # Mock the Tag constructor to return our mock
        with unittest.mock.patch('src.database.tag_manager.Tag', return_value=mock_tag):
            result = self.tag_manager.add_tag("TEST_TAG", "Test Tag")
        
        self.assertEqual(result, mock_tag)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_tag)
        self.mock_session.expunge.assert_called_once_with(mock_tag)
        self.mock_session.close.assert_called_once()
    
    def test_get_tag_found(self):
        """Test getting an existing tag."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_tag.tag_id = "TEST_TAG"
        mock_tag.name = "Test Tag"
        mock_tag.playlists = []
        
        self.mock_session.query().filter_by().first.return_value = mock_tag
        
        result = self.tag_manager.get_tag("TEST_TAG")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['tag_id'], "TEST_TAG")
        self.assertEqual(result['name'], "Test Tag")
        self.assertEqual(result['playlists'], [])
        self.mock_session.close.assert_called_once()
    
    def test_get_tag_not_found(self):
        """Test getting a non-existent tag."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.tag_manager.get_tag("NONEXISTENT")
        
        self.assertIsNone(result)
        self.mock_session.close.assert_called_once()
    
    def test_get_tag_with_playlists(self):
        """Test getting a tag with associated playlists."""
        mock_playlist = MagicMock(spec=Playlist)
        mock_playlist.id = 1
        mock_playlist.name = "Test Playlist"
        
        mock_tag = MagicMock(spec=Tag)
        mock_tag.id = 1
        mock_tag.tag_id = "TEST_TAG"
        mock_tag.name = "Test Tag"
        mock_tag.playlists = [mock_playlist]
        
        self.mock_session.query().filter_by().first.return_value = mock_tag
        
        result = self.tag_manager.get_tag("TEST_TAG")
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['playlists']), 1)
        self.assertEqual(result['playlists'][0]['name'], "Test Playlist")
        self.mock_session.close.assert_called_once()
    
    def test_delete_tag_success(self):
        """Test successful tag deletion."""
        mock_tag = MagicMock(spec=Tag)
        self.mock_session.query().filter_by().first.return_value = mock_tag
        
        result = self.tag_manager.delete_tag("TEST_TAG")
        
        self.assertTrue(result)
        self.mock_session.delete.assert_called_once_with(mock_tag)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_delete_tag_not_found(self):
        """Test deleting a non-existent tag."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.tag_manager.delete_tag("NONEXISTENT")
        
        self.assertFalse(result)
        self.mock_session.delete.assert_not_called()
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_update_tag_success(self):
        """Test successful tag update."""
        mock_tag = MagicMock(spec=Tag)
        mock_tag.name = "Old Name"
        self.mock_session.query().filter_by().first.return_value = mock_tag
        
        result = self.tag_manager.update_tag("TEST_TAG", "New Name")
        
        self.assertEqual(result, mock_tag)
        self.assertEqual(mock_tag.name, "New Name")
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_tag)
        self.mock_session.expunge.assert_called_once_with(mock_tag)
        self.mock_session.close.assert_called_once()
    
    def test_update_tag_not_found(self):
        """Test updating a non-existent tag."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.tag_manager.update_tag("NONEXISTENT", "New Name")
        
        self.assertIsNone(result)
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_get_all_tags(self):
        """Test getting all tags."""
        mock_tag1 = MagicMock(spec=Tag)
        mock_tag1.id = 1
        mock_tag1.tag_id = "TAG1"
        mock_tag1.name = "Tag 1"
        mock_tag1.playlists = []
        
        mock_tag2 = MagicMock(spec=Tag)
        mock_tag2.id = 2
        mock_tag2.tag_id = "TAG2"
        mock_tag2.name = "Tag 2"
        mock_tag2.playlists = []
        
        self.mock_session.query().all.return_value = [mock_tag1, mock_tag2]
        
        result = self.tag_manager.get_all_tags()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['tag_id'], "TAG1")
        self.assertEqual(result[1]['tag_id'], "TAG2")
        self.mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()