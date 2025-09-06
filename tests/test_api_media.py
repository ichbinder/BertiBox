import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open
import json
import os
import shutil
from flask import Flask
from src.api.media import bp as media_bp


class TestMediaAPI(unittest.TestCase):
    
    def setUp(self):
        """Set up Flask test client and mock dependencies."""
        self.app = Flask(__name__)
        self.app.register_blueprint(media_bp, url_prefix='/api')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock database and config
        self.db_patcher = patch('src.api.media.db')
        self.config_patcher = patch('src.api.media.config')
        
        self.mock_db = self.db_patcher.start()
        self.mock_config = self.config_patcher.start()
        
        self.mock_config.MP3_DIR = '/test/mp3'
    
    def tearDown(self):
        """Clean up patches."""
        self.db_patcher.stop()
        self.config_patcher.stop()
    
    @patch('src.api.media.os.path.exists')
    @patch('src.api.media.os.listdir')
    @patch('src.api.media.os.path.isdir')
    def test_explore_directory(self, mock_isdir, mock_listdir, mock_exists):
        """Test exploring directory structure."""
        mock_exists.return_value = True
        mock_listdir.return_value = ['subfolder', 'file1.mp3', 'file2.mp3']
        mock_isdir.side_effect = lambda x: 'subfolder' in x
        self.mock_db.is_file_in_playlist.return_value = False
        
        response = self.client.get('/api/media?path=/')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('items', data)
    
    @patch('src.api.media.os.path.exists')
    @patch('src.api.media.os.remove')
    def test_delete_file(self, mock_remove, mock_exists):
        """Test deleting a file."""
        mock_exists.return_value = True
        self.mock_db.is_file_used.return_value = False
        
        response = self.client.delete('/api/media/file?path=test.mp3')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        mock_remove.assert_called_once()
    
    @patch('src.api.media.os.path.exists')
    def test_delete_file_in_use(self, mock_exists):
        """Test deleting a file that's in use."""
        mock_exists.return_value = True
        self.mock_db.is_file_used.return_value = True
        
        response = self.client.delete('/api/media/file?path=used.mp3')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 409)  # Conflict status
        self.assertFalse(data['success'])
        self.assertIn('in use', data['error'])
    
    @patch('src.api.media.os.walk')
    def test_get_mp3_files(self, mock_walk):
        """Test getting list of all MP3 files."""
        mock_walk.return_value = [
            ('/test/mp3', ['subfolder'], ['file1.mp3', 'file2.txt']),
            ('/test/mp3/subfolder', [], ['file3.mp3', 'readme.md'])
        ]
        
        response = self.client.get('/api/mp3-files')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['files']), 2)
        self.assertIn('file1.mp3', data['files'])
        self.assertIn('subfolder/file3.mp3', data['files'])
    
    @patch('src.api.media.os.walk')
    def test_get_mp3_files_error(self, mock_walk):
        """Test error handling when getting MP3 files."""
        mock_walk.side_effect = Exception("Permission denied")
        
        response = self.client.get('/api/mp3-files')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Permission denied', data['error'])
    
    def test_list_media_invalid_path(self):
        """Test listing media with path traversal attempt."""
        response = self.client.get('/api/media?path=../../etc')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(data['success'])
        self.assertIn('Invalid path', data['error'])
    
    @patch('src.api.media.os.path.exists')
    def test_list_media_not_found(self, mock_exists):
        """Test listing non-existent path."""
        mock_exists.return_value = False
        
        response = self.client.get('/api/media?path=nonexistent')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    @patch('src.api.media.os.path.exists')
    @patch('src.api.media.os.listdir')
    def test_list_media_error(self, mock_listdir, mock_exists):
        """Test error handling in list media."""
        mock_exists.return_value = True
        mock_listdir.side_effect = PermissionError("Access denied")
        
        response = self.client.get('/api/media?path=/')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.makedirs')
    @patch('src.api.media.os.path.exists')
    def test_create_folder(self, mock_exists, mock_makedirs):
        """Test creating a new folder."""
        mock_exists.return_value = False
        
        response = self.client.post('/api/media/folder', 
                                   json={'name': 'New Folder', 'parent': ''})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        mock_makedirs.assert_called_once()
    
    def test_create_folder_no_name(self):
        """Test creating folder without name."""
        response = self.client.post('/api/media/folder', 
                                   json={'parent': ''})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
    
    def test_create_folder_invalid_name(self):
        """Test creating folder with invalid name."""
        response = self.client.post('/api/media/folder', 
                                   json={'name': '!!!###', 'parent': ''})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Invalid', data['error'])
    
    @patch('src.api.media.os.path.exists')
    def test_create_folder_already_exists(self, mock_exists):
        """Test creating folder that already exists."""
        mock_exists.return_value = True
        
        response = self.client.post('/api/media/folder', 
                                   json={'name': 'Existing', 'parent': ''})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 409)
        self.assertFalse(data['success'])
        self.assertIn('already exists', data['error'])
    
    def test_create_folder_invalid_path(self):
        """Test creating folder with path traversal."""
        response = self.client.post('/api/media/folder', 
                                   json={'name': 'folder', 'parent': '../../etc'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.makedirs')
    @patch('src.api.media.os.path.exists')
    def test_create_folder_error(self, mock_exists, mock_makedirs):
        """Test error handling in create folder."""
        mock_exists.return_value = False
        mock_makedirs.side_effect = OSError("Disk full")
        
        response = self.client.post('/api/media/folder', 
                                   json={'name': 'folder', 'parent': ''})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
    
    def test_delete_file_no_path(self):
        """Test deleting file without path."""
        response = self.client.delete('/api/media/file')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
    
    def test_delete_file_invalid_path(self):
        """Test deleting file with invalid path."""
        response = self.client.delete('/api/media/file?path=../../etc/passwd')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.path.exists')
    def test_delete_file_not_found(self, mock_exists):
        """Test deleting non-existent file."""
        mock_exists.return_value = False
        
        response = self.client.delete('/api/media/file?path=missing.mp3')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.remove')
    @patch('src.api.media.os.path.exists')
    def test_delete_file_error(self, mock_exists, mock_remove):
        """Test error handling in delete file."""
        mock_exists.return_value = True
        self.mock_db.is_file_used.return_value = False
        mock_remove.side_effect = PermissionError("Access denied")
        
        response = self.client.delete('/api/media/file?path=file.mp3')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.shutil.rmtree')
    @patch('src.api.media.os.path.exists')
    def test_delete_folder(self, mock_exists, mock_rmtree):
        """Test deleting a folder."""
        mock_exists.return_value = True
        self.mock_db.are_files_in_folder_used.return_value = False
        
        response = self.client.delete('/api/media/folder?path=folder')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        mock_rmtree.assert_called_once()
    
    def test_delete_folder_no_path(self):
        """Test deleting folder without path."""
        response = self.client.delete('/api/media/folder')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
    
    def test_delete_folder_invalid_path(self):
        """Test deleting folder with invalid path."""
        response = self.client.delete('/api/media/folder?path=../../etc')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.path.exists')
    def test_delete_folder_not_found(self, mock_exists):
        """Test deleting non-existent folder."""
        mock_exists.return_value = False
        
        response = self.client.delete('/api/media/folder?path=missing')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
    
    @patch('src.api.media.os.path.exists')
    def test_delete_folder_in_use(self, mock_exists):
        """Test deleting folder with files in use."""
        mock_exists.return_value = True
        self.mock_db.are_files_in_folder_used.return_value = True
        
        response = self.client.delete('/api/media/folder?path=used')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 409)
        self.assertFalse(data['success'])
        self.assertIn('in use', data['error'])
    
    @patch('src.api.media.shutil.rmtree')
    @patch('src.api.media.os.path.exists')
    def test_delete_folder_error(self, mock_exists, mock_rmtree):
        """Test error handling in delete folder."""
        mock_exists.return_value = True
        self.mock_db.are_files_in_folder_used.return_value = False
        mock_rmtree.side_effect = OSError("Directory not empty")
        
        response = self.client.delete('/api/media/folder?path=folder')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
    
    # The following tests are commented out as these endpoints don't exist yet
    # They could be implemented in the future if needed
    
    # def test_rename_file(self):
    #     """Test renaming a file."""
    #     pass
    
    # def test_rename_file_already_exists(self):
    #     """Test renaming to a name that already exists."""
    #     pass
    
    # def test_create_folder(self):
    #     """Test creating a new folder."""
    #     pass
    
    # def test_create_folder_already_exists(self):
    #     """Test creating a folder that already exists."""
    #     pass
    
    # def test_get_file_tags(self):
    #     """Test getting tags associated with a file."""
    #     pass
    
    # def test_assign_tag_to_file(self):
    #     """Test assigning a tag to a file."""
    #     pass


if __name__ == '__main__':
    unittest.main()