"""RFID tag handling module for BertiBox."""

import time
from .. import config


class TagHandler:
    """Handles RFID tag detection and processing."""
    
    def __init__(self, db_instance, socketio_instance):
        self.db = db_instance
        self.socketio = socketio_instance
        
        # Tag state
        self.current_tag_id = None
        self.current_tag_name = None
        self.last_tag_time = 0
        self.tag_timeout = config.TAG_TIMEOUT
    
    def handle_tag(self, tag_id, playback_controller):
        """Handle a detected RFID tag."""
        current_time = time.time()
        
        if tag_id is None:
            # Tag removed
            if self.current_tag_id and (current_time - self.last_tag_time) > 0.5:
                return self._handle_tag_removal(playback_controller)
        else:
            # Tag detected
            if tag_id != self.current_tag_id:
                return self._handle_new_tag(tag_id, current_time, playback_controller)
            else:
                # Same tag, update time
                self.last_tag_time = current_time
        
        return False
    
    def _handle_new_tag(self, tag_id, current_time, playback_controller):
        """Handle a new tag being placed."""
        print(f"New tag detected: {tag_id}")
        
        # Check if tag exists in database
        tag = self.db.get_tag(tag_id)
        if not tag:
            # New unknown tag
            print(f"Unknown tag {tag_id}, adding to database...")
            self._add_new_tag(tag_id)
            self.current_tag_id = tag_id
            self.current_tag_name = f"New Tag {tag_id[:8]}"
            self.last_tag_time = current_time
            self._emit_tag_update()
            return False
        
        # Known tag - load and play playlist
        self.current_tag_id = tag_id
        self.current_tag_name = tag.name
        self.last_tag_time = current_time
        
        playlist = self.db.get_playlist(tag_id)
        if playlist:
            print(f"Loading playlist for tag: {tag.name}")
            if playback_controller.load_playlist(playlist.id):
                playback_controller.play_current_track()
                self._emit_tag_update()
                return True
        else:
            print(f"No playlist found for tag: {tag.name}")
            self._emit_tag_update()
        
        return False
    
    def _handle_tag_removal(self, playback_controller):
        """Handle tag being removed."""
        if self.current_tag_id:
            print(f"Tag removed: {self.current_tag_id}")
            playback_controller.stop_requested_by_tag_removal = True
            playback_controller.clear_state()
            self.clear_tag_state()
            self._emit_tag_update()
            return True
        return False
    
    def _add_new_tag(self, tag_id):
        """Add a new tag to the database."""
        try:
            tag_name = f"New Tag {tag_id[:8]}"
            self.db.add_tag(tag_id, tag_name)
            print(f"Added new tag to database: {tag_id}")
            
            # Create empty playlist for the tag
            playlist = self.db.add_playlist(tag_id, f"Playlist for {tag_name}")
            if playlist:
                print(f"Created empty playlist for new tag")
        except Exception as e:
            print(f"Error adding new tag: {e}")
    
    def clear_tag_state(self):
        """Clear current tag state."""
        self.current_tag_id = None
        self.current_tag_name = None
        self.last_tag_time = 0
    
    def _emit_tag_update(self):
        """Emit tag status update via socketio."""
        if self.socketio:
            status = self.get_status()
            self.socketio.emit('current_tag', status)
    
    def get_status(self):
        """Get current tag status."""
        return {
            'tag_id': self.current_tag_id,
            'tag_name': self.current_tag_name,
            'tag_present': self.current_tag_id is not None
        }