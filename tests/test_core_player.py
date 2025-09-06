"""Tests for the refactored BertiBox core player."""

import unittest
from unittest.mock import MagicMock, Mock, patch, call
import threading
from src.core.player import BertiBox


class TestBertiBoxRefactored(unittest.TestCase):
    """Test the main BertiBox coordinator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_socketio = MagicMock()
        self.mock_db = MagicMock()
        
        # Patch all component imports
        self.patcher_audio = patch('src.core.player.AudioManager')
        self.patcher_playback = patch('src.core.player.PlaybackController')
        self.patcher_tag = patch('src.core.player.TagHandler')
        self.patcher_sleep = patch('src.core.player.SleepTimer')
        self.patcher_rfid = patch('src.core.player.RFIDReader')
        
        self.mock_audio_class = self.patcher_audio.start()
        self.mock_playback_class = self.patcher_playback.start()
        self.mock_tag_class = self.patcher_tag.start()
        self.mock_sleep_class = self.patcher_sleep.start()
        self.mock_rfid_class = self.patcher_rfid.start()
        
        # Create mock instances
        self.mock_audio = MagicMock()
        self.mock_playback = MagicMock()
        self.mock_tag = MagicMock()
        self.mock_sleep = MagicMock()
        self.mock_rfid = MagicMock()
        
        # Configure class constructors to return our mocks
        self.mock_audio_class.return_value = self.mock_audio
        self.mock_playback_class.return_value = self.mock_playback
        self.mock_tag_class.return_value = self.mock_tag
        self.mock_sleep_class.return_value = self.mock_sleep
        self.mock_rfid_class.return_value = self.mock_rfid
        
        # Create BertiBox instance
        self.bertibox = BertiBox(self.mock_socketio, self.mock_db)
    
    def tearDown(self):
        """Clean up after tests."""
        self.patcher_audio.stop()
        self.patcher_playback.stop()
        self.patcher_tag.stop()
        self.patcher_sleep.stop()
        self.patcher_rfid.stop()
    
    def test_initialization(self):
        """Test BertiBox initialization."""
        # Verify components were initialized with correct parameters
        self.mock_audio_class.assert_called_once_with(self.mock_db)
        self.mock_playback_class.assert_called_once_with(
            self.mock_audio, self.mock_db, self.mock_socketio
        )
        self.mock_tag_class.assert_called_once_with(self.mock_db, self.mock_socketio)
        self.mock_sleep_class.assert_called_once_with(self.mock_socketio)
        self.mock_rfid_class.assert_called_once()
        
        # Verify instance variables
        self.assertFalse(self.bertibox.running)
        self.assertEqual(self.bertibox.audio_manager, self.mock_audio)
        self.assertEqual(self.bertibox.playback_controller, self.mock_playback)
        self.assertEqual(self.bertibox.tag_handler, self.mock_tag)
        self.assertEqual(self.bertibox.sleep_timer, self.mock_sleep)
        self.assertEqual(self.bertibox.rfid_reader, self.mock_rfid)
    
    @patch('src.core.player.threading.Thread')
    def test_start(self, mock_thread_class):
        """Test starting the BertiBox."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        self.mock_audio.is_initialized.return_value = True
        
        self.bertibox.start()
        
        self.assertTrue(self.bertibox.running)
        mock_thread_class.assert_called_once_with(target=self.bertibox._main_loop)
        mock_thread.daemon = True
        mock_thread.start.assert_called_once()
        self.mock_rfid.start_reading.assert_called_once()
    
    def test_stop(self):
        """Test stopping the BertiBox."""
        self.bertibox.running = True
        self.mock_audio.is_initialized.return_value = True
        
        with patch('src.core.player.pygame') as mock_pygame:
            self.bertibox.stop()
        
        self.assertFalse(self.bertibox.running)
        self.mock_playback.clear_state.assert_called_once()
        self.mock_tag.clear_tag_state.assert_called_once()
        self.mock_sleep.cancel.assert_called_once()
        self.mock_rfid.stop_reading.assert_called_once()
        self.mock_rfid.cleanup.assert_called_once()
    
    @patch('src.core.player.time.sleep')
    def test_main_loop_with_tag(self, mock_sleep):
        """Test the main loop when a tag is detected."""
        # Set up mock behavior
        self.bertibox.running = True
        self.mock_rfid.get_tag.return_value = "TEST_TAG"
        self.mock_tag.current_tag_id = None
        
        # Run one iteration then stop
        def stop_after_one(delay):
            if mock_sleep.call_count >= 1:
                self.bertibox.running = False
        mock_sleep.side_effect = stop_after_one
        
        self.bertibox._main_loop()
        
        # Verify tag handling was called
        self.mock_tag.handle_tag.assert_called_with(
            "TEST_TAG", self.mock_playback
        )
        mock_sleep.assert_called_with(0.1)
    
    @patch('src.core.player.time.sleep')
    def test_main_loop_tag_removed(self, mock_sleep):
        """Test the main loop when a tag is removed."""
        # Set up mock behavior
        self.bertibox.running = True
        self.mock_rfid.get_tag.return_value = None
        self.mock_tag.current_tag_id = "OLD_TAG"
        
        # Run one iteration then stop
        def stop_after_one(delay):
            if mock_sleep.call_count >= 1:
                self.bertibox.running = False
        mock_sleep.side_effect = stop_after_one
        
        self.bertibox._main_loop()
        
        # Verify tag handling was called with None
        self.mock_tag.handle_tag.assert_called_with(None, self.mock_playback)
        mock_sleep.assert_called_with(0.1)
    
    @patch('src.core.player.time.sleep')
    def test_main_loop_no_tag_no_current(self, mock_sleep):
        """Test the main loop when no tag and no current tag."""
        # Set up mock behavior
        self.bertibox.running = True
        self.mock_rfid.get_tag.return_value = None
        self.mock_tag.current_tag_id = None
        
        # Run one iteration then stop
        def stop_after_one(delay):
            if mock_sleep.call_count >= 1:
                self.bertibox.running = False
        mock_sleep.side_effect = stop_after_one
        
        self.bertibox._main_loop()
        
        # Verify no tag handling was called (no tag and no current tag)
        self.mock_tag.handle_tag.assert_not_called()
        mock_sleep.assert_called_with(0.1)
    
    
    def test_set_volume(self):
        """Test volume setting."""
        self.mock_audio.set_volume.return_value = True
        
        with patch.object(self.bertibox, 'emit_player_status'):
            result = self.bertibox.set_volume(0.8)
        
        self.assertTrue(result)
        self.mock_audio.set_volume.assert_called_once_with(0.8)
    
    def test_pause_playback(self):
        """Test pause command."""
        self.mock_playback.pause.return_value = True
        
        with patch.object(self.bertibox, 'emit_player_status'):
            result = self.bertibox.pause_playback()
        
        self.assertTrue(result)
        self.mock_playback.pause.assert_called_once()
    
    def test_resume_playback(self):
        """Test resume command."""
        self.mock_playback.resume.return_value = True
        
        with patch.object(self.bertibox, 'emit_player_status'):
            result = self.bertibox.resume_playback()
        
        self.assertTrue(result)
        self.mock_playback.resume.assert_called_once()
    
    def test_play_next(self):
        """Test play next command."""
        self.mock_playback.play_next.return_value = True
        
        with patch.object(self.bertibox, 'emit_player_status'):
            result = self.bertibox.play_next()
        
        self.assertTrue(result)
        self.mock_playback.play_next.assert_called_once()
    
    def test_play_previous(self):
        """Test play previous command."""
        self.mock_playback.play_previous.return_value = True
        
        with patch.object(self.bertibox, 'emit_player_status'):
            result = self.bertibox.play_previous()
        
        self.assertTrue(result)
        self.mock_playback.play_previous.assert_called_once()
    
    def test_set_sleep_timer(self):
        """Test setting sleep timer."""
        self.mock_sleep.set_timer.return_value = True
        
        result = self.bertibox.set_sleep_timer(30)
        
        self.assertTrue(result)
        self.mock_sleep.set_timer.assert_called_once()
        # Check that callback was passed
        call_args = self.mock_sleep.set_timer.call_args
        self.assertEqual(call_args[0][0], 30)
    
    def test_cancel_sleep_timer(self):
        """Test canceling sleep timer."""
        self.mock_sleep.cancel.return_value = True
        
        result = self.bertibox.cancel_sleep_timer()
        
        self.assertTrue(result)
        self.mock_sleep.cancel.assert_called_once()
    
    def test_get_sleep_timer_remaining(self):
        """Test getting remaining sleep timer."""
        self.mock_sleep.get_remaining_minutes.return_value = 15
        
        result = self.bertibox.get_sleep_timer_remaining()
        
        self.assertEqual(result, 15)
        self.mock_sleep.get_remaining_minutes.assert_called_once()
    
    def test_get_player_status(self):
        """Test getting player status."""
        self.mock_playback.get_status.return_value = {
            'is_playing': True,
            'is_paused': False,
            'current_track': "test.mp3"
        }
        self.mock_tag.get_status.return_value = {
            'current_tag_id': "TEST_TAG",
            'current_tag_name': "Test Tag"
        }
        self.mock_sleep.get_status.return_value = {
            'active': True,
            'remaining_minutes': 10
        }
        self.mock_audio.get_volume.return_value = 0.7
        
        status = self.bertibox.get_player_status()
        
        self.assertEqual(status['is_playing'], True)
        self.assertEqual(status['is_paused'], False)
        self.assertEqual(status['current_track'], "test.mp3")
        self.assertEqual(status['current_tag_id'], "TEST_TAG")
        self.assertEqual(status['current_tag_name'], "Test Tag")
        self.assertEqual(status['volume'], 0.7)
        self.assertEqual(status['sleep_timer_active'], True)
        self.assertEqual(status['sleep_timer_remaining'], 10)


if __name__ == '__main__':
    unittest.main()