import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open
import json
import io
from flask import Flask
from werkzeug.datastructures import FileStorage
from src.api.upload import bp as upload_bp


class TestUploadAPI(unittest.TestCase):
    
    def setUp(self):
        """Set up Flask test client and mock dependencies."""
        self.app = Flask(__name__)
        self.app.register_blueprint(upload_bp, url_prefix='/api')
        self.app.config['TESTING'] = True
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
        self.client = self.app.test_client()
        
        # Mock config
        self.config_patcher = patch('src.api.upload.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.MP3_DIR = '/test/mp3'
        self.mock_config.UPLOAD_CHUNK_SIZE = 8192
        self.mock_config.ALLOWED_EXTENSIONS = {'mp3', 'MP3'}
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
    
    @patch('src.api.upload.os.makedirs')
    @patch('src.api.upload.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_upload_file_success(self, mock_file, mock_exists, mock_makedirs):
        """Test successful file upload."""
        mock_exists.return_value = False
        
        # Create a test file
        test_data = b'Test MP3 file content'
        test_file = FileStorage(
            stream=io.BytesIO(test_data),
            filename='test.mp3',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': 'uploads'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['filename'], 'test.mp3')
        mock_file.assert_called()
    
    @patch('src.api.upload.os.path.exists')
    def test_upload_file_already_exists(self, mock_exists):
        """Test uploading a file that already exists."""
        mock_exists.return_value = True
        
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='existing.mp3',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 409)
        self.assertFalse(data['success'])
        self.assertIn('already exists', data['error'])
    
    def test_upload_no_file(self):
        """Test upload without file."""
        response = self.client.post('/api/upload-mp3',
                                   data={'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('No file', data['error'])
    
    def test_upload_invalid_extension(self):
        """Test uploading file with invalid extension."""
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='test.txt',
            content_type='text/plain'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Invalid file type', data['error'])
    
    @patch('src.api.upload.os.makedirs')
    @patch('src.api.upload.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_upload_with_subdirectory(self, mock_file, mock_exists, mock_makedirs):
        """Test uploading file to subdirectory."""
        mock_exists.return_value = False
        
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='song.mp3',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': 'artist/album/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        mock_makedirs.assert_called()
    
    @patch('src.api.upload.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_upload_error_during_write(self, mock_file, mock_exists):
        """Test handling error during file write."""
        mock_exists.return_value = False
        mock_file.side_effect = IOError("Disk full")
        
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='test.mp3',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Disk full', data['error'])
    
    def test_upload_empty_filename(self):
        """Test uploading file with empty filename."""
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
    
    @patch('src.api.upload.secure_filename')
    @patch('src.api.upload.os.makedirs')
    @patch('src.api.upload.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_upload_sanitizes_filename(self, mock_file, mock_exists, mock_makedirs, mock_secure):
        """Test that filename is sanitized."""
        mock_exists.return_value = False
        mock_secure.return_value = 'sanitized.mp3'
        
        test_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='../../etc/passwd.mp3',
            content_type='audio/mpeg'
        )
        
        response = self.client.post('/api/upload-mp3',
                                   data={'file': test_file, 'target_folder': '/'},
                                   content_type='multipart/form-data')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['filename'], 'sanitized.mp3')
        mock_secure.assert_called_once_with('../../etc/passwd.mp3')


if __name__ == '__main__':
    unittest.main()