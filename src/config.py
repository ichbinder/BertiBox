"""Configuration settings for BertiBox application."""

import os

# Directory configuration
MP3_DIR = 'mp3'
DATABASE_FILE = 'bertibox.db'

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key_here!')  # TODO: Use environment variable
HOST = '0.0.0.0'
PORT = 8080
DEBUG = False

# Audio configuration
AUDIO_FREQUENCY = 44100
AUDIO_SIZE = -16
AUDIO_CHANNELS = 2
AUDIO_BUFFER = 16384
DEFAULT_VOLUME = 0.8

# RFID configuration
TAG_TIMEOUT = 2.0  # Seconds before a tag is considered removed
PLAYBACK_CHECK_INTERVAL = 0.2  # Seconds between playback status checks
MAIN_LOOP_INTERVAL = 0.05  # Seconds between RFID reader checks

# File upload configuration
ALLOWED_EXTENSIONS = {'mp3'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size