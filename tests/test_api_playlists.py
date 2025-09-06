import unittest
from unittest.mock import Mock, MagicMock, patch
import json
from flask import Flask
from src.api.playlists import bp as playlists_bp


class TestPlaylistsAPI(unittest.TestCase):
    
    def setUp(self):
        """Set up Flask test client and mock dependencies."""
        self.app = Flask(__name__)
        self.app.register_blueprint(playlists_bp, url_prefix='/api')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock database
        self.db_patcher = patch('src.api.playlists.db')
        self.mock_db = self.db_patcher.start()
        
        # Mock update helper
        self.update_patcher = patch('src.api.playlists.update_berti_box_playlist')
        self.mock_update = self.update_patcher.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.db_patcher.stop()
        self.update_patcher.stop()
    
    def test_get_playlist_items(self):
        """Test getting playlist items."""
        self.mock_db.get_playlist_items.return_value = [
            {'id': 1, 'mp3_file': 'song1.mp3', 'position': 0},
            {'id': 2, 'mp3_file': 'song2.mp3', 'position': 1}
        ]
        
        response = self.client.get('/api/playlists/1/items')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['items']), 2)
        self.mock_db.get_playlist_items.assert_called_once_with(1)
    
    def test_add_playlist_item(self):
        """Test adding item to playlist."""
        self.mock_db.add_playlist_item.return_value = {
            'id': 3,
            'mp3_file': 'new_song.mp3',
            'position': 2
        }
        
        response = self.client.post('/api/playlists/1/items',
                                   json={'mp3_file': 'new_song.mp3'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['item']['mp3_file'], 'new_song.mp3')
        self.mock_update.assert_called_once_with(1)
    
    def test_add_playlist_items_batch(self):
        """Test adding multiple items to playlist."""
        self.mock_db.add_playlist_items.return_value = [
            {'id': 1, 'mp3_file': 'song1.mp3', 'position': 0},
            {'id': 2, 'mp3_file': 'song2.mp3', 'position': 1}
        ]
        
        response = self.client.post('/api/playlists/1/items/batch',
                                   json={'mp3_files': ['song1.mp3', 'song2.mp3']})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.mock_db.add_playlist_items.assert_called_once_with(1, ['song1.mp3', 'song2.mp3'])
        self.mock_update.assert_called_once_with(1)
    
    def test_delete_playlist_item(self):
        """Test deleting playlist item."""
        self.mock_db.delete_playlist_item.return_value = True
        
        response = self.client.delete('/api/playlist-items/1')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.mock_db.delete_playlist_item.assert_called_once_with(1)
    
    def test_update_playlist_item_position(self):
        """Test updating playlist item position."""
        self.mock_db.update_playlist_item_position.return_value = True
        self.mock_db.get_playlist_items.return_value = [
            {'id': 1, 'playlist_id': 1}
        ]
        
        response = self.client.put('/api/playlist-items/1',
                                  json={'position': 3})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.mock_db.update_playlist_item_position.assert_called_once_with(1, 3)
    
    def test_add_playlist(self):
        """Test creating a new playlist."""
        mock_playlist = Mock()
        mock_playlist.id = 1
        self.mock_db.add_playlist.return_value = mock_playlist
        
        response = self.client.post('/api/playlists',
                                   json={'tag_id': 'ABC123', 'name': 'My Playlist'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['playlist_id'], 1)
        self.mock_db.add_playlist.assert_called_once_with('ABC123', 'My Playlist')
    
    def test_add_playlist_missing_params(self):
        """Test creating playlist without required params."""
        response = self.client.post('/api/playlists',
                                   json={'tag_id': 'ABC123'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
    
    def test_add_playlist_failure(self):
        """Test failed playlist creation."""
        self.mock_db.add_playlist.return_value = None
        
        response = self.client.post('/api/playlists',
                                   json={'tag_id': 'ABC123', 'name': 'My Playlist'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Failed to create playlist', data['error'])
    
    def test_add_playlist_exception(self):
        """Test exception handling in add playlist."""
        self.mock_db.add_playlist.side_effect = Exception("Database error")
        
        response = self.client.post('/api/playlists',
                                   json={'tag_id': 'ABC123', 'name': 'My Playlist'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])
    
    def test_get_playlist_items_error(self):
        """Test error handling in get playlist items."""
        self.mock_db.get_playlist_items.side_effect = Exception("Database error")
        
        response = self.client.get('/api/playlists/1/items')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])
    
    def test_add_playlist_item_no_mp3(self):
        """Test adding item without mp3_file."""
        response = self.client.post('/api/playlists/1/items',
                                   json={})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('mp3_file is required', data['error'])
    
    def test_add_playlist_item_failure(self):
        """Test failed item addition."""
        self.mock_db.add_playlist_item.return_value = None
        
        response = self.client.post('/api/playlists/1/items',
                                   json={'mp3_file': 'song.mp3'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Failed to add item', data['error'])
    
    def test_add_playlist_item_exception(self):
        """Test exception handling in add playlist item."""
        self.mock_db.add_playlist_item.side_effect = Exception("Database error")
        
        response = self.client.post('/api/playlists/1/items',
                                   json={'mp3_file': 'song.mp3'})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])
    
    def test_add_playlist_items_batch_empty(self):
        """Test batch adding with empty array."""
        response = self.client.post('/api/playlists/1/items/batch',
                                   json={'mp3_files': []})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('mp3_files array is required', data['error'])
    
    def test_add_playlist_items_batch_failure(self):
        """Test failed batch addition."""
        self.mock_db.add_playlist_items.return_value = None
        
        response = self.client.post('/api/playlists/1/items/batch',
                                   json={'mp3_files': ['song1.mp3']})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Failed to add items', data['error'])
    
    def test_add_playlist_items_batch_exception(self):
        """Test exception handling in batch add."""
        self.mock_db.add_playlist_items.side_effect = Exception("Database error")
        
        response = self.client.post('/api/playlists/1/items/batch',
                                   json={'mp3_files': ['song1.mp3']})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])
    
    def test_update_playlist_item_position_no_position(self):
        """Test updating position without position param."""
        response = self.client.put('/api/playlist-items/1',
                                  json={})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('position is required', data['error'])
    
    def test_update_playlist_item_position_failure(self):
        """Test failed position update."""
        self.mock_db.update_playlist_item_position.return_value = False
        
        response = self.client.put('/api/playlist-items/1',
                                  json={'position': 3})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Failed to update position', data['error'])
    
    def test_update_playlist_item_position_exception(self):
        """Test exception handling in position update."""
        self.mock_db.update_playlist_item_position.side_effect = Exception("Database error")
        
        response = self.client.put('/api/playlist-items/1',
                                  json={'position': 3})
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])
    
    def test_delete_playlist_item_not_found(self):
        """Test deleting non-existent item."""
        self.mock_db.delete_playlist_item.return_value = False
        
        response = self.client.delete('/api/playlist-items/999')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('Item not found', data['error'])
    
    def test_delete_playlist_item_exception(self):
        """Test exception handling in delete item."""
        self.mock_db.delete_playlist_item.side_effect = Exception("Database error")
        
        response = self.client.delete('/api/playlist-items/1')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Database error', data['error'])


if __name__ == '__main__':
    unittest.main()
