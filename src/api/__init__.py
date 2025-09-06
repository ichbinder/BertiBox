"""API package for BertiBox."""

from .tags import bp as tags_bp
from .playlists import bp as playlists_bp
from .media import bp as media_bp
from .player import bp as player_bp
from .upload import bp as upload_bp

__all__ = ['tags_bp', 'playlists_bp', 'media_bp', 'player_bp', 'upload_bp']