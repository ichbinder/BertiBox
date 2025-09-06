import unittest
from unittest.mock import Mock, MagicMock, patch
import os
from src.utils.helpers import (
    sanitize_path,
    is_safe_path,
    get_file_extension,
    format_file_size,
    validate_mp3_file,
    ensure_directory_exists
)


class TestUtilsHelpers(unittest.TestCase):
    
    def test_sanitize_path(self):
        """Test path sanitization."""
        # Normal paths
        self.assertEqual(sanitize_path('folder/file.mp3'), 'folder/file.mp3')
        self.assertEqual(sanitize_path('/folder/file.mp3'), 'folder/file.mp3')
        
        # Path traversal attempts
        self.assertEqual(sanitize_path('../../../etc/passwd'), 'etc/passwd')
        self.assertEqual(sanitize_path('folder/../file.mp3'), 'folder/file.mp3')
        
        # Windows paths
        self.assertEqual(sanitize_path('C:\\folder\\file.mp3'), 'C:/folder/file.mp3')
        
        # Multiple slashes
        self.assertEqual(sanitize_path('folder//file.mp3'), 'folder/file.mp3')
    
    def test_is_safe_path(self):
        """Test path safety validation."""
        base_dir = '/home/user/mp3'
        
        # Safe paths
        self.assertTrue(is_safe_path(base_dir, 'folder/file.mp3'))
        self.assertTrue(is_safe_path(base_dir, 'file.mp3'))
        
        # Unsafe paths
        self.assertFalse(is_safe_path(base_dir, '../../../etc/passwd'))
        self.assertFalse(is_safe_path(base_dir, '/etc/passwd'))
        self.assertFalse(is_safe_path(base_dir, '..'))
    
    def test_get_file_extension(self):
        """Test getting file extension."""
        self.assertEqual(get_file_extension('song.mp3'), '.mp3')
        self.assertEqual(get_file_extension('song.MP3'), '.mp3')
        self.assertEqual(get_file_extension('folder/song.mp3'), '.mp3')
        self.assertEqual(get_file_extension('no_extension'), '')
        self.assertEqual(get_file_extension('.hidden'), '')
        self.assertEqual(get_file_extension('file.tar.gz'), '.gz')
    
    def test_format_file_size(self):
        """Test file size formatting."""
        self.assertEqual(format_file_size(0), '0 B')
        self.assertEqual(format_file_size(512), '512 B')
        self.assertEqual(format_file_size(1024), '1.0 KB')
        self.assertEqual(format_file_size(1536), '1.5 KB')
        self.assertEqual(format_file_size(1048576), '1.0 MB')
        self.assertEqual(format_file_size(1572864), '1.5 MB')
        self.assertEqual(format_file_size(1073741824), '1.0 GB')
        self.assertEqual(format_file_size(1610612736), '1.5 GB')
    
    def test_validate_mp3_file(self):
        """Test MP3 file validation."""
        # Valid MP3 files
        self.assertTrue(validate_mp3_file('song.mp3'))
        self.assertTrue(validate_mp3_file('song.MP3'))
        self.assertTrue(validate_mp3_file('folder/song.mp3'))
        
        # Invalid files
        self.assertFalse(validate_mp3_file('song.wav'))
        self.assertFalse(validate_mp3_file('song.txt'))
        self.assertFalse(validate_mp3_file('song'))
        self.assertFalse(validate_mp3_file(''))
        self.assertFalse(validate_mp3_file(None))
    
    @patch('src.utils.helpers.os.makedirs')
    @patch('src.utils.helpers.os.path.exists')
    def test_ensure_directory_exists_creates(self, mock_exists, mock_makedirs):
        """Test creating directory when it doesn't exist."""
        mock_exists.return_value = False
        
        result = ensure_directory_exists('/path/to/dir')
        
        self.assertTrue(result)
        mock_makedirs.assert_called_once_with('/path/to/dir', exist_ok=True)
    
    @patch('src.utils.helpers.os.path.exists')
    def test_ensure_directory_exists_already_exists(self, mock_exists):
        """Test when directory already exists."""
        mock_exists.return_value = True
        
        result = ensure_directory_exists('/existing/dir')
        
        self.assertTrue(result)
    
    @patch('src.utils.helpers.os.makedirs')
    @patch('src.utils.helpers.os.path.exists')
    def test_ensure_directory_exists_error(self, mock_exists, mock_makedirs):
        """Test handling error when creating directory."""
        mock_exists.return_value = False
        mock_makedirs.side_effect = OSError("Permission denied")
        
        result = ensure_directory_exists('/restricted/dir')
        
        self.assertFalse(result)


class TestPathNormalization(unittest.TestCase):
    """Test path normalization across different OS."""
    
    def test_normalize_path_unix(self):
        """Test path normalization on Unix systems."""
        from src.utils.helpers import normalize_path
        
        # Unix paths
        self.assertEqual(normalize_path('/home/user/file.mp3'), 'home/user/file.mp3')
        self.assertEqual(normalize_path('folder/file.mp3'), 'folder/file.mp3')
        
        # Remove duplicates
        self.assertEqual(normalize_path('folder//file.mp3'), 'folder/file.mp3')
    
    def test_normalize_path_windows(self):
        """Test path normalization on Windows systems."""
        from src.utils.helpers import normalize_path
        
        # Windows paths
        self.assertEqual(normalize_path('C:\\folder\\file.mp3'), 'C:/folder/file.mp3')
        self.assertEqual(normalize_path('folder\\subfolder\\file.mp3'), 'folder/subfolder/file.mp3')
    
    def test_normalize_path_mixed(self):
        """Test normalization with mixed separators."""
        from src.utils.helpers import normalize_path
        
        self.assertEqual(normalize_path('folder\\subfolder/file.mp3'), 'folder/subfolder/file.mp3')
        self.assertEqual(normalize_path('folder/subfolder\\file.mp3'), 'folder/subfolder/file.mp3')


class TestFileOperationHelpers(unittest.TestCase):
    """Test file operation helper functions."""
    
    @patch('src.utils.helpers.os.stat')
    @patch('src.utils.helpers.os.path.exists')
    def test_get_file_info(self, mock_exists, mock_stat):
        """Test getting file information."""
        from src.utils.helpers import get_file_info
        
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 3145728  # 3MB
        mock_stat_result.st_mtime = 1609459200  # 2021-01-01
        mock_stat.return_value = mock_stat_result
        
        info = get_file_info('/path/to/file.mp3')
        
        self.assertEqual(info['name'], 'file.mp3')
        self.assertEqual(info['size'], 3145728)
        self.assertEqual(info['size_formatted'], '3.0 MB')
        self.assertEqual(info['extension'], '.mp3')
        self.assertIn('modified', info)
    
    @patch('src.utils.helpers.os.path.exists')
    def test_get_file_info_not_found(self, mock_exists):
        """Test getting info for non-existent file."""
        from src.utils.helpers import get_file_info
        
        mock_exists.return_value = False
        
        info = get_file_info('/nonexistent/file.mp3')
        
        self.assertIsNone(info)
    
    def test_is_valid_filename(self):
        """Test filename validation."""
        from src.utils.helpers import is_valid_filename
        
        # Valid filenames
        self.assertTrue(is_valid_filename('song.mp3'))
        self.assertTrue(is_valid_filename('my-song_2021.mp3'))
        self.assertTrue(is_valid_filename('01 Track.mp3'))
        
        # Invalid filenames
        self.assertFalse(is_valid_filename(''))
        self.assertFalse(is_valid_filename('..'))
        self.assertFalse(is_valid_filename('../etc/passwd'))
        self.assertFalse(is_valid_filename('file/with/slash.mp3'))
        self.assertFalse(is_valid_filename('file\\with\\backslash.mp3'))
        self.assertFalse(is_valid_filename('file:with:colon.mp3'))
        self.assertFalse(is_valid_filename('file*with*asterisk.mp3'))


if __name__ == '__main__':
    unittest.main()