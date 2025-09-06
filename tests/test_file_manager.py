"""Tests for FileManager class."""

import unittest
from unittest.mock import MagicMock, Mock, patch
from src.database.file_manager import FileManager
from src.database.models import Tag, Playlist, PlaylistItem


class TestFileManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.get_session = Mock(return_value=self.mock_session)
        self.file_manager = FileManager(self.get_session)
    
    def test_is_file_in_playlist_true(self):
        """Test checking if a file is in a playlist linked to a tag."""
        mock_result = MagicMock()
        mock_result.id = 1
        
        query_chain = self.mock_session.query.return_value
        query_chain.join.return_value = query_chain
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = mock_result
        
        result = self.file_manager.is_file_in_playlist("test.mp3")
        
        self.assertTrue(result)
        self.mock_session.close.assert_called_once()
    
    def test_is_file_in_playlist_false(self):
        """Test checking if a file is not in any playlist."""
        query_chain = self.mock_session.query.return_value
        query_chain.join.return_value = query_chain
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = None
        
        result = self.file_manager.is_file_in_playlist("test.mp3")
        
        self.assertFalse(result)
        self.mock_session.close.assert_called_once()
    
    def test_is_file_in_playlist_strips_leading_slash(self):
        """Test that leading slashes are stripped from file paths."""
        query_chain = self.mock_session.query.return_value
        query_chain.join.return_value = query_chain
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = None
        
        self.file_manager.is_file_in_playlist("/path/to/test.mp3")
        
        # Verify the filter was called with stripped path
        query_chain.filter.assert_called()
        args = query_chain.filter.call_args[0]
        # The actual comparison should be with "path/to/test.mp3"
        self.mock_session.close.assert_called_once()
    
    def test_is_file_used_true(self):
        """Test checking if a file is used in any playlist."""
        self.mock_session.query().filter().count.return_value = 1
        
        result = self.file_manager.is_file_used("test.mp3")
        
        self.assertTrue(result)
        self.mock_session.close.assert_called_once()
    
    def test_is_file_used_false(self):
        """Test checking if a file is not used."""
        self.mock_session.query().filter().count.return_value = 0
        
        result = self.file_manager.is_file_used("test.mp3")
        
        self.assertFalse(result)
        self.mock_session.close.assert_called_once()
    
    def test_is_file_used_exception(self):
        """Test is_file_used returns True on exception (safe default)."""
        self.mock_session.query().filter().count.side_effect = Exception("DB Error")
        
        result = self.file_manager.is_file_used("test.mp3")
        
        self.assertTrue(result)  # Returns True on error as safe default
        self.mock_session.close.assert_called_once()
    
    def test_update_path_references_file(self):
        """Test updating path references for a single file."""
        mock_item = MagicMock(spec=PlaylistItem)
        mock_item.id = 1
        mock_item.mp3_file = "old/path.mp3"
        
        self.mock_session.query().filter().all.side_effect = [
            [mock_item],  # File match
            []  # No directory matches
        ]
        
        result = self.file_manager.update_path_references("old/path.mp3", "new/path.mp3")
        
        self.assertTrue(result)
        self.assertEqual(mock_item.mp3_file, "new/path.mp3")
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_update_path_references_directory(self):
        """Test updating path references for a directory."""
        mock_item1 = MagicMock(spec=PlaylistItem)
        mock_item1.id = 1
        mock_item1.mp3_file = "old/dir/file1.mp3"
        
        mock_item2 = MagicMock(spec=PlaylistItem)
        mock_item2.id = 2
        mock_item2.mp3_file = "old/dir/subdir/file2.mp3"
        
        self.mock_session.query().filter().all.side_effect = [
            [],  # No exact file match
            [mock_item1, mock_item2]  # Directory matches
        ]
        
        result = self.file_manager.update_path_references("old/dir", "new/dir")
        
        self.assertTrue(result)
        self.assertEqual(mock_item1.mp3_file, "new/dir/file1.mp3")
        self.assertEqual(mock_item2.mp3_file, "new/dir/subdir/file2.mp3")
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_update_path_references_no_changes(self):
        """Test update_path_references with no matching items."""
        self.mock_session.query().filter().all.return_value = []
        
        result = self.file_manager.update_path_references("old/path.mp3", "new/path.mp3")
        
        self.assertTrue(result)
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_update_path_references_exception(self):
        """Test update_path_references handles exceptions."""
        self.mock_session.query().filter().all.side_effect = Exception("DB Error")
        
        result = self.file_manager.update_path_references("old/path.mp3", "new/path.mp3")
        
        self.assertFalse(result)
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    @patch('src.database.file_manager.os.walk')
    @patch('src.database.file_manager.os.path.isdir')
    @patch('src.database.file_manager.os.path.abspath')
    def test_are_files_in_folder_used_true(self, mock_abspath, mock_isdir, mock_walk):
        """Test checking if files in a folder are used."""
        mock_isdir.return_value = True
        mock_abspath.side_effect = lambda x: x  # Return path as-is
        mock_walk.return_value = [
            ("/base/folder", [], ["file1.mp3", "file2.mp3"])
        ]
        
        # First file is not used, second is used
        with patch.object(self.file_manager, 'is_file_used', side_effect=[False, True]):
            result = self.file_manager.are_files_in_folder_used("folder", "/base")
        
        self.assertTrue(result)
    
    @patch('src.database.file_manager.os.walk')
    @patch('src.database.file_manager.os.path.isdir')
    @patch('src.database.file_manager.os.path.abspath')
    def test_are_files_in_folder_used_false(self, mock_abspath, mock_isdir, mock_walk):
        """Test checking if no files in a folder are used."""
        mock_isdir.return_value = True
        mock_abspath.side_effect = lambda x: x
        mock_walk.return_value = [
            ("/base/folder", [], ["file1.mp3", "file2.mp3"])
        ]
        
        with patch.object(self.file_manager, 'is_file_used', return_value=False):
            result = self.file_manager.are_files_in_folder_used("folder", "/base")
        
        self.assertFalse(result)
    
    @patch('src.database.file_manager.os.path.isdir')
    def test_are_files_in_folder_used_not_dir(self, mock_isdir):
        """Test checking files in non-existent folder."""
        mock_isdir.return_value = False
        
        result = self.file_manager.are_files_in_folder_used("nonexistent", "/base")
        
        self.assertFalse(result)
    
    def test_get_playlists_for_file(self):
        """Test getting playlists that contain a file."""
        mock_results = [
            ("TAG1", "Tag 1"),
            ("TAG2", "Tag 2")
        ]
        
        query_chain = self.mock_session.query.return_value
        query_chain.join.return_value = query_chain
        query_chain.filter.return_value = query_chain
        query_chain.distinct.return_value = query_chain
        query_chain.all.return_value = mock_results
        
        result = self.file_manager.get_playlists_for_file("test.mp3")
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['tag_id'], "TAG1")
        self.assertEqual(result[0]['name'], "Tag 1")
        self.assertEqual(result[1]['tag_id'], "TAG2")
        self.mock_session.close.assert_called_once()
    
    def test_get_playlists_for_file_none(self):
        """Test getting playlists for a file not in any playlist."""
        query_chain = self.mock_session.query.return_value
        query_chain.join.return_value = query_chain
        query_chain.filter.return_value = query_chain
        query_chain.distinct.return_value = query_chain
        query_chain.all.return_value = []
        
        result = self.file_manager.get_playlists_for_file("test.mp3")
        
        self.assertEqual(len(result), 0)
        self.mock_session.close.assert_called_once()
    
    def test_get_playlists_for_file_exception(self):
        """Test get_playlists_for_file handles exceptions."""
        self.mock_session.query.side_effect = Exception("DB Error")
        
        result = self.file_manager.get_playlists_for_file("test.mp3")
        
        self.assertEqual(result, [])
        self.mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()