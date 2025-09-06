"""Audio management module for BertiBox - handles pygame mixer and volume control."""

import pygame
import subprocess
from .. import config


class AudioManager:
    """Manages audio initialization, volume control and pygame mixer."""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.pygame_initialized = False
        self.mixer_initialized = False
        self.current_volume = config.DEFAULT_VOLUME
        
        # Initialize everything
        self._initialize_volume()
        self._configure_audio_output()
        self._initialize_pygame()
    
    def _initialize_volume(self):
        """Load and set initial volume from database."""
        try:
            initial_volume_str = self.db.get_setting('global_volume', str(config.DEFAULT_VOLUME))
            self.current_volume = float(initial_volume_str)
            if not (0.0 <= self.current_volume <= 1.0):
                print(f"Warning: Invalid volume '{self.current_volume}' loaded from DB, resetting to {config.DEFAULT_VOLUME}")
                self.current_volume = config.DEFAULT_VOLUME
                self.db.set_setting('global_volume', str(self.current_volume))
            print(f"Initial volume loaded from DB: {self.current_volume}")
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse volume from DB. Using default {config.DEFAULT_VOLUME}. Error: {e}")
            self.current_volume = config.DEFAULT_VOLUME
            self.db.set_setting('global_volume', str(self.current_volume))
    
    def _configure_audio_output(self):
        """Configure system audio output using amixer."""
        try:
            subprocess.run(['amixer', 'set', 'PCM', '100%'], check=True)
            subprocess.run(['amixer', 'set', 'PCM', 'unmute'], check=True)
            print("Audio output configured.")
        except Exception as e:
            print(f"Warning: Could not configure audio output via amixer: {e}")
            print("Playback might use default output or fail.")
    
    def _initialize_pygame(self):
        """Initialize Pygame and audio mixer."""
        try:
            pygame.init()
            pygame.mixer.init(
                frequency=config.AUDIO_FREQUENCY,
                size=config.AUDIO_SIZE,
                channels=config.AUDIO_CHANNELS,
                buffer=config.AUDIO_BUFFER
            )
            pygame.mixer.set_num_channels(1)
            pygame.mixer.music.set_volume(self.current_volume)
            print("Pygame Mixer initialized with increased buffer.")
            self.pygame_initialized = True
            self.mixer_initialized = True
        except pygame.error as e:
            print(f"Error initializing Pygame Mixer: {e}")
            print("Audio playback will not be available.")
            self.mixer_initialized = False
    
    def set_volume(self, volume_float):
        """Set the playback volume (0.0 to 1.0)."""
        if not isinstance(volume_float, (int, float)):
            print(f"Invalid volume type: {type(volume_float)}")
            return False
        
        if not (0.0 <= volume_float <= 1.0):
            print(f"Invalid volume value: {volume_float}. Must be between 0.0 and 1.0")
            return False
        
        self.current_volume = float(volume_float)
        
        # Update mixer volume if initialized
        if self.mixer_initialized:
            pygame.mixer.music.set_volume(self.current_volume)
        
        # Save to database
        self.db.set_setting('global_volume', str(self.current_volume))
        print(f"Volume set to {self.current_volume}")
        return True
    
    def get_volume(self):
        """Get current volume level."""
        return self.current_volume
    
    def reset_audio_subsystem(self):
        """Reset the audio subsystem to recover from errors."""
        print("Resetting audio subsystem...")
        
        try:
            # Quit pygame mixer if initialized
            if self.mixer_initialized:
                pygame.mixer.quit()
                self.mixer_initialized = False
            
            # Re-initialize
            self._initialize_pygame()
            
            print("Audio subsystem reset complete.")
            return True
        except Exception as e:
            print(f"Error resetting audio subsystem: {e}")
            return False
    
    def is_initialized(self):
        """Check if audio system is properly initialized."""
        return self.mixer_initialized and pygame.mixer.get_init() is not None