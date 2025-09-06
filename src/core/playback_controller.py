"""Playback control module for BertiBox - handles play, pause, stop, navigation."""

import pygame
import os
import threading
from .. import config


class PlaybackController:
    """Controls music playback operations."""
    
    def __init__(self, audio_manager, db_instance, socketio_instance):
        self.audio_manager = audio_manager
        self.db = db_instance
        self.socketio = socketio_instance
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.current_playlist = None
        self.current_playlist_items = []
        self.current_playlist_index = 0
        self.current_track_filename = None
        self.playback_check_timer = None
        self.stop_requested_by_tag_removal = False
        self.just_attempted_play = False
    
    def load_playlist(self, playlist_id):
        """Load a playlist and prepare for playback."""
        self.current_playlist = playlist_id
        self.current_playlist_items = self.db.get_playlist_items(playlist_id)
        self.current_playlist_index = 0
        
        if not self.current_playlist_items:
            print(f"Playlist {playlist_id} is empty")
            return False
        
        print(f"Loaded playlist {playlist_id} with {len(self.current_playlist_items)} items")
        return True
    
    def play_current_track(self):
        """Play the current track in the playlist."""
        if not self.current_playlist_items:
            print("No playlist loaded or playlist is empty")
            return False
        
        if 0 <= self.current_playlist_index < len(self.current_playlist_items):
            current_item = self.current_playlist_items[self.current_playlist_index]
            mp3_file = current_item.get('mp3_file')
            if mp3_file:
                return self.play_mp3(mp3_file)
        return False
    
    def play_mp3(self, mp3_file):
        """Play a specific MP3 file."""
        if not self.audio_manager.is_initialized():
            print("Audio system not initialized")
            return False
        
        # Convert potential Windows path to Unix path
        mp3_file = mp3_file.replace('\\', '/')
        
        full_path = os.path.join(config.MP3_DIR, mp3_file)
        
        if not os.path.exists(full_path):
            print(f"MP3 file not found: {full_path}")
            return False
        
        try:
            self.stop_mp3()
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            self.current_track_filename = mp3_file
            self.just_attempted_play = True
            
            print(f"Playing: {mp3_file}")
            
            # Start playback monitoring
            self._start_playback_check()
            return True
            
        except pygame.error as e:
            print(f"Error playing MP3: {e}")
            return False
    
    def stop_mp3(self):
        """Stop current playback."""
        if self.playback_check_timer:
            self.playback_check_timer.cancel()
            self.playback_check_timer = None
        
        if self.audio_manager.is_initialized():
            pygame.mixer.music.stop()
        
        self.is_playing = False
        self.is_paused = False
        self.current_track_filename = None
    
    def pause(self):
        """Pause current playback."""
        if self.is_playing and not self.is_paused and self.audio_manager.is_initialized():
            pygame.mixer.music.pause()
            self.is_paused = True
            print("Playback paused")
            return True
        return False
    
    def resume(self):
        """Resume paused playback."""
        if self.is_playing and self.is_paused and self.audio_manager.is_initialized():
            pygame.mixer.music.unpause()
            self.is_paused = False
            print("Playback resumed")
            return True
        return False
    
    def play_next(self, track_finished_naturally=False):
        """Play next track in playlist."""
        if not self.current_playlist_items:
            return False
        
        if track_finished_naturally:
            # Natural progression to next track
            self.current_playlist_index += 1
            if self.current_playlist_index >= len(self.current_playlist_items):
                self.current_playlist_index = 0
                print("Playlist finished, restarting from beginning")
        else:
            # Manual skip to next
            self.current_playlist_index = (self.current_playlist_index + 1) % len(self.current_playlist_items)
        
        return self.play_current_track()
    
    def play_previous(self):
        """Play previous track in playlist."""
        if not self.current_playlist_items:
            return False
        
        self.current_playlist_index = (self.current_playlist_index - 1) % len(self.current_playlist_items)
        return self.play_current_track()
    
    def play_track_at_index(self, index):
        """Play a specific track by index."""
        if not self.current_playlist_items:
            return False
        
        if 0 <= index < len(self.current_playlist_items):
            self.current_playlist_index = index
            return self.play_current_track()
        return False
    
    def _start_playback_check(self):
        """Start monitoring playback status."""
        if self.playback_check_timer:
            self.playback_check_timer.cancel()
        
        self.playback_check_timer = threading.Timer(0.5, self._check_playback)
        self.playback_check_timer.daemon = True
        self.playback_check_timer.start()
    
    def _check_playback(self):
        """Check if playback has finished and handle accordingly."""
        if not self.is_playing:
            return
        
        if self.audio_manager.is_initialized() and not pygame.mixer.music.get_busy():
            # Track finished
            if self.stop_requested_by_tag_removal:
                print("Playback stopped due to tag removal")
                self.stop_requested_by_tag_removal = False
                self.clear_state()
            else:
                print("Track finished naturally")
                self.play_next(track_finished_naturally=True)
                self._emit_status_update()
        else:
            # Continue monitoring
            self._start_playback_check()
    
    def _emit_status_update(self):
        """Emit status update via socketio."""
        if self.socketio:
            status = self.get_status()
            self.socketio.emit('player_status', status)
    
    def clear_state(self):
        """Clear all playback state."""
        self.stop_mp3()
        self.current_playlist = None
        self.current_playlist_items = []
        self.current_playlist_index = 0
    
    def get_status(self):
        """Get current playback status."""
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_track': self.current_track_filename,
            'current_index': self.current_playlist_index,
            'playlist_length': len(self.current_playlist_items),
            'playlist_id': self.current_playlist
        }