"""Sleep timer module for BertiBox."""

import threading
import time


class SleepTimer:
    """Manages sleep timer functionality."""
    
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.timer = None
        self.end_time = None
    
    def set_timer(self, duration_minutes, callback):
        """Set a sleep timer for specified minutes."""
        if duration_minutes <= 0:
            return False
        
        # Cancel existing timer
        self.cancel()
        
        # Set new timer
        duration_seconds = duration_minutes * 60
        self.end_time = time.time() + duration_seconds
        
        self.timer = threading.Timer(duration_seconds, callback)
        self.timer.daemon = True
        self.timer.start()
        
        print(f"Sleep timer set for {duration_minutes} minutes")
        self._emit_status()
        return True
    
    def cancel(self):
        """Cancel the sleep timer."""
        if self.timer:
            self.timer.cancel()
            self.timer = None
            self.end_time = None
            print("Sleep timer cancelled")
            self._emit_status()
            return True
        return False
    
    def get_remaining_minutes(self):
        """Get remaining time in minutes."""
        if self.end_time:
            remaining = self.end_time - time.time()
            if remaining > 0:
                return int(remaining / 60)
        return 0
    
    def is_active(self):
        """Check if timer is active."""
        return self.timer is not None and self.end_time is not None
    
    def _emit_status(self):
        """Emit timer status update."""
        if self.socketio:
            status = self.get_status()
            self.socketio.emit('sleep_timer_status', status)
    
    def get_status(self):
        """Get timer status."""
        return {
            'active': self.is_active(),
            'remaining_minutes': self.get_remaining_minutes()
        }