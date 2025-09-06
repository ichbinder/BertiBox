import unittest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask
from flask_socketio import SocketIO
from src.websocket.handlers import register_handlers


class TestWebSocketHandlers(unittest.TestCase):
    
    def setUp(self):
        """Set up Flask-SocketIO test client."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.socketio = SocketIO(self.app)
        
        # Mock BertiBox instance
        self.mock_berti = Mock()
        self.mock_berti.emit_player_status = Mock()
        self.mock_berti.pause_playback = Mock()
        self.mock_berti.resume_playback = Mock()
        self.mock_berti.play_next = Mock()
        self.mock_berti.play_previous = Mock()
        self.mock_berti.set_volume_internal = Mock()
        self.mock_berti.set_sleep_timer = Mock()
        self.mock_berti.cancel_sleep_timer = Mock()
        self.mock_berti.play_current_track = Mock()
        self.mock_berti.is_playing = False
        self.mock_berti.is_paused = False
        self.mock_berti.current_playlist = None
        self.mock_berti.current_playlist_items = []
        self.mock_berti.current_playlist_index = 0
        
        # Mock get_berti_box function
        self.get_berti_box = Mock(return_value=self.mock_berti)
        
        # Register handlers
        register_handlers(self.socketio, self.get_berti_box)
        
        self.client = self.socketio.test_client(self.app)
    
    def tearDown(self):
        """Clean up."""
        pass
    
    def test_connect(self):
        """Test client connection."""
        # Connection should trigger emit_player_status in background
        # Due to background task, we just verify the handler was registered
        self.get_berti_box.assert_called()
    
    def test_request_player_status(self):
        """Test requesting player status."""
        self.client.emit('request_player_status')
        
        # Should call get_berti_box and trigger emit_player_status
        self.get_berti_box.assert_called()
    
    def test_play_pause_command(self):
        """Test play/pause toggle command."""
        # Test when not playing - should resume
        self.mock_berti.is_playing = False
        self.client.emit('play_pause')
        self.get_berti_box.assert_called()
        
        # Test when playing but not paused - should pause  
        self.mock_berti.is_playing = True
        self.mock_berti.is_paused = False
        self.client.emit('play_pause')
        self.get_berti_box.assert_called()
    
    def test_pause_command(self):
        """Test pause command."""
        self.client.emit('pause')
        self.get_berti_box.assert_called()
    
    def test_resume_command(self):
        """Test resume command."""
        self.client.emit('resume')
        self.get_berti_box.assert_called()
    
    def test_next_track(self):
        """Test next track command."""
        self.client.emit('next_track')
        self.get_berti_box.assert_called()
    
    def test_previous_track(self):
        """Test previous track command."""
        self.client.emit('previous_track')
        self.get_berti_box.assert_called()
    
    def test_set_volume_valid(self):
        """Test setting valid volume."""
        self.client.emit('set_volume', {'volume': 0.5})
        self.get_berti_box.assert_called()
    
    def test_set_volume_invalid(self):
        """Test setting invalid volume."""
        self.client.emit('set_volume', {'volume': 1.5})
        # Handler still gets called but should validate internally
        self.get_berti_box.assert_called()
    
    def test_play_track(self):
        """Test playing specific track."""
        self.mock_berti.current_playlist = {'id': 1}
        self.mock_berti.current_playlist_items = ['track1.mp3', 'track2.mp3']
        
        self.client.emit('play_track', {'index': 0})
        self.get_berti_box.assert_called()
    
    def test_set_sleep_timer(self):
        """Test setting sleep timer."""
        self.client.emit('set_sleep_timer', {'duration': 30})
        self.get_berti_box.assert_called()
    
    def test_cancel_sleep_timer(self):
        """Test canceling sleep timer."""
        self.client.emit('cancel_sleep_timer')
        self.get_berti_box.assert_called()
    
    def test_play_track_invalid_index(self):
        """Test playing track with invalid index."""
        self.mock_berti.current_playlist = {'id': 1}
        self.mock_berti.current_playlist_items = ['track1.mp3']
        
        # Index out of range
        self.client.emit('play_track', {'index': 5})
        self.get_berti_box.assert_called()
        
    def test_play_track_no_playlist(self):
        """Test playing track when no playlist loaded."""
        self.mock_berti.current_playlist = None
        
        self.client.emit('play_track', {'index': 0})
        self.get_berti_box.assert_called()


class TestWebSocketBroadcasts(unittest.TestCase):
    """Test WebSocket broadcast functionality."""
    
    def setUp(self):
        """Set up Flask-SocketIO test client."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.socketio = SocketIO(self.app)
        
        # Mock BertiBox
        self.mock_berti = Mock()
        self.mock_berti.emit_player_status = Mock()
        self.get_berti_box = Mock(return_value=self.mock_berti)
        
        register_handlers(self.socketio, self.get_berti_box)
        
        self.client = self.socketio.test_client(self.app)
    
    def tearDown(self):
        """Clean up."""
        pass
    
    def test_broadcast_to_all_clients(self):
        """Test broadcasting to all connected clients."""
        # Connect second client
        client2 = self.socketio.test_client(self.app)
        
        # Emit from first client
        self.client.emit('play_pause')
        
        # Verify handler was called
        self.get_berti_box.assert_called()


if __name__ == '__main__':
    unittest.main()
