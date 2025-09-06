import unittest
from unittest.mock import Mock, MagicMock, patch
import json
from flask import Flask
from src.api.tags import bp as tags_bp


class TestTagsAPI(unittest.TestCase):
    
    def setUp(self):
        """Set up Flask test client and mock database."""
        self.app = Flask(__name__)
        self.app.register_blueprint(tags_bp, url_prefix='/api')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock database
        self.db_patcher = patch('src.api.tags.db')
        self.mock_db = self.db_patcher.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.db_patcher.stop()
    
    def test_get_tags_success(self):
        """Test successful retrieval of all tags."""
        mock_tags = [
            {
                'id': 1,
                'tag_id': 'TAG1',
                'name': 'Tag One',
                'playlists': [{'id': 1, 'name': 'Playlist 1'}]
            },
            {
                'id': 2,
                'tag_id': 'TAG2',
                'name': 'Tag Two',
                'playlists': []
            }
        ]
        self.mock_db.get_all_tags.return_value = mock_tags
        
        response = self.client.get('/api/tags')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['tags']), 2)
        self.assertEqual(data['tags'][0]['tag_id'], 'TAG1')
    
    def test_get_tags_error(self):
        """Test error handling when getting tags fails."""
        self.mock_db.get_all_tags.side_effect = Exception("Database error")
        
        response = self.client.get('/api/tags')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_add_tag_success(self):
        """Test successful tag creation."""
        self.mock_db.get_tag.return_value = None  # Tag doesn't exist
        
        mock_tag = MagicMock()
        mock_tag.id = 1
        self.mock_db.add_tag.return_value = mock_tag
        
        mock_playlist = MagicMock()
        mock_playlist.id = 10
        self.mock_db.add_playlist.return_value = mock_playlist
        
        response = self.client.post('/api/tags',
                                   json={
                                       'tag_id': 'NEW_TAG',
                                       'tag_name': 'New Tag Name',
                                       'playlist_name': 'New Playlist'
                                   })
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['tag_id'], 'NEW_TAG')
        self.assertEqual(data['playlist_id'], 10)
        
        self.mock_db.add_tag.assert_called_once_with('NEW_TAG', 'New Tag Name')
        self.mock_db.add_playlist.assert_called_once_with('NEW_TAG', 'New Playlist')
    
    def test_add_tag_missing_id(self):
        """Test adding tag without tag_id."""
        response = self.client.post('/api/tags',
                                   json={'tag_name': 'Name Only'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('tag_id is required', data['error'])
    
    def test_add_tag_already_exists(self):
        """Test adding tag that already exists."""
        existing_tag = {'id': 1, 'tag_id': 'EXISTING', 'name': 'Existing Tag'}
        self.mock_db.get_tag.return_value = existing_tag
        
        response = self.client.post('/api/tags',
                                   json={'tag_id': 'EXISTING'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 409)
        self.assertFalse(data['success'])
        self.assertIn('already exists', data['error'])
    
    def test_add_tag_with_defaults(self):
        """Test adding tag with default names."""
        self.mock_db.get_tag.return_value = None
        
        mock_tag = MagicMock()
        mock_tag.id = 1
        self.mock_db.add_tag.return_value = mock_tag
        
        mock_playlist = MagicMock()
        mock_playlist.id = 10
        self.mock_db.add_playlist.return_value = mock_playlist
        
        response = self.client.post('/api/tags',
                                   json={'tag_id': 'DEFAULT_TAG'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        
        # Check default names were used
        self.mock_db.add_tag.assert_called_once_with('DEFAULT_TAG', 'Neuer Tag DEFAULT_TAG')
        self.mock_db.add_playlist.assert_called_once_with('DEFAULT_TAG', 'Neuer Tag DEFAULT_TAG')
    
    def test_delete_tag_success(self):
        """Test successful tag deletion."""
        self.mock_db.delete_tag.return_value = True
        
        response = self.client.delete('/api/tags/TAG_TO_DELETE')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('deleted successfully', data['message'])
        self.mock_db.delete_tag.assert_called_once_with('TAG_TO_DELETE')
    
    def test_delete_tag_not_found(self):
        """Test deleting non-existent tag."""
        self.mock_db.delete_tag.return_value = False
        
        response = self.client.delete('/api/tags/NONEXISTENT')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    def test_delete_tag_error(self):
        """Test error handling when deleting tag fails."""
        self.mock_db.delete_tag.side_effect = Exception("Database error")
        
        response = self.client.delete('/api/tags/ERROR_TAG')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_get_tag_playlist_success(self):
        """Test getting playlist for a tag."""
        mock_tag = {
            'id': 1,
            'tag_id': 'TAG1',
            'name': 'Tag One',
            'playlists': [{'id': 10, 'name': 'Playlist'}]
        }
        self.mock_db.get_tag.return_value = mock_tag
        
        mock_items = [
            {'id': 1, 'mp3_file': 'song1.mp3', 'position': 0},
            {'id': 2, 'mp3_file': 'song2.mp3', 'position': 1}
        ]
        self.mock_db.get_playlist_items.return_value = mock_items
        
        response = self.client.get('/api/tags/TAG1/playlist')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['playlist_id'], 10)
        self.assertEqual(len(data['items']), 2)
        self.mock_db.get_playlist_items.assert_called_once_with(10)
    
    def test_get_tag_playlist_no_playlist(self):
        """Test getting playlist for tag without playlist."""
        mock_tag = {
            'id': 1,
            'tag_id': 'TAG_NO_PLAYLIST',
            'name': 'Tag Without Playlist',
            'playlists': []
        }
        self.mock_db.get_tag.return_value = mock_tag
        
        response = self.client.get('/api/tags/TAG_NO_PLAYLIST/playlist')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIsNone(data['playlist_id'])
        self.assertEqual(data['items'], [])
    
    def test_get_tag_playlist_tag_not_found(self):
        """Test getting playlist for non-existent tag."""
        self.mock_db.get_tag.return_value = None
        
        response = self.client.get('/api/tags/NONEXISTENT/playlist')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    def test_get_tag_playlist_error(self):
        """Test error handling when getting tag playlist fails."""
        self.mock_db.get_tag.side_effect = Exception("Database error")
        
        response = self.client.get('/api/tags/ERROR_TAG/playlist')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()