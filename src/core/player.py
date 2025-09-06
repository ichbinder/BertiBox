"""Main BertiBox player class that coordinates all components."""

import pygame
import threading
import time
from ..rfid_reader import RFIDReader
from .audio_manager import AudioManager
from .playback_controller import PlaybackController
from .tag_handler import TagHandler
from .sleep_timer import SleepTimer


class BertiBox:
    """Main BertiBox player coordinating all components."""
    
    def __init__(self, socketio_instance, db_instance):
        self.socketio = socketio_instance
        self.db = db_instance
        self.running = False
        
        # Initialize components
        self.audio_manager = AudioManager(db_instance)
        self.playback_controller = PlaybackController(
            self.audio_manager, db_instance, socketio_instance
        )
        self.tag_handler = TagHandler(db_instance, socketio_instance)
        self.sleep_timer = SleepTimer(socketio_instance)
        self.rfid_reader = RFIDReader()
        
        print("BertiBox initialized")
    
    def start(self):
        """Start the BertiBox main loop."""
        if not self.audio_manager.is_initialized():
            print("Cannot start BertiBox: Audio system not initialized.")
            return
        
        self.running = True
        self.rfid_reader.start_reading()
        
        # Start main loop in separate thread
        main_thread = threading.Thread(target=self._main_loop)
        main_thread.daemon = True
        main_thread.start()
        
        print("BertiBox started")
    
    def _main_loop(self):
        """Main loop checking for RFID tags."""
        while self.running:
            try:
                tag_id = self.rfid_reader.get_tag()
                if tag_id is not None or self.tag_handler.current_tag_id:
                    self.tag_handler.handle_tag(tag_id, self.playback_controller)
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop BertiBox and cleanup."""
        print("Stopping BertiBox...")
        self.running = False
        
        # Stop components
        self.playback_controller.clear_state()
        self.tag_handler.clear_tag_state()
        self.sleep_timer.cancel()
        self.rfid_reader.stop_reading()
        self.rfid_reader.cleanup()
        
        # Cleanup pygame
        if self.audio_manager.is_initialized():
            pygame.mixer.quit()
            pygame.quit()
        
        print("BertiBox stopped")
    
    # Public API methods for web interface
    
    def pause_playback(self):
        """Pause current playback."""
        success = self.playback_controller.pause()
        self.emit_player_status()
        return success
    
    def resume_playback(self):
        """Resume paused playback."""
        success = self.playback_controller.resume()
        self.emit_player_status()
        return success
    
    def play_pause_toggle(self):
        """Toggle between play and pause."""
        if self.playback_controller.is_paused:
            return self.resume_playback()
        else:
            return self.pause_playback()
    
    def play_next(self):
        """Skip to next track."""
        success = self.playback_controller.play_next()
        self.emit_player_status()
        return success
    
    def play_previous(self):
        """Go to previous track."""
        success = self.playback_controller.play_previous()
        self.emit_player_status()
        return success
    
    def play_track_at_index(self, index):
        """Play specific track by index."""
        success = self.playback_controller.play_track_at_index(index)
        self.emit_player_status()
        return success
    
    def set_volume(self, volume):
        """Set playback volume (0.0 to 1.0)."""
        success = self.audio_manager.set_volume(volume)
        self.emit_player_status()
        return success
    
    def set_sleep_timer(self, duration_minutes):
        """Set sleep timer."""
        return self.sleep_timer.set_timer(
            duration_minutes,
            self._handle_sleep_timer_expired
        )
    
    def cancel_sleep_timer(self):
        """Cancel sleep timer."""
        return self.sleep_timer.cancel()
    
    def get_sleep_timer_remaining(self):
        """Get remaining sleep timer minutes."""
        return self.sleep_timer.get_remaining_minutes()
    
    def _handle_sleep_timer_expired(self):
        """Handle sleep timer expiration."""
        print("Sleep timer expired, stopping playback")
        self.playback_controller.clear_state()
        self.tag_handler.clear_tag_state()
        self.emit_player_status()
    
    def reset_audio_subsystem(self):
        """Reset audio system."""
        was_playing = self.playback_controller.is_playing
        current_track = self.playback_controller.current_track_filename
        
        # Stop playback
        self.playback_controller.stop_mp3()
        
        # Reset audio
        success = self.audio_manager.reset_audio_subsystem()
        
        # Resume if was playing
        if success and was_playing and current_track:
            self.playback_controller.play_mp3(current_track)
        
        return success
    
    def get_player_status(self):
        """Get complete player status."""
        playback_status = self.playback_controller.get_status()
        tag_status = self.tag_handler.get_status()
        timer_status = self.sleep_timer.get_status()
        
        return {
            **playback_status,
            **tag_status,
            'volume': self.audio_manager.get_volume(),
            'sleep_timer_active': timer_status['active'],
            'sleep_timer_remaining': timer_status['remaining_minutes']
        }
    
    def emit_player_status(self):
        """Emit current player status via socketio."""
        if self.socketio:
            status = self.get_player_status()
            self.socketio.emit('player_status', status)