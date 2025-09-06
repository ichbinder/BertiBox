"""Helper functions for BertiBox."""

import os
import traceback
from pathlib import Path

# Global reference to BertiBox instance (will be set by app.py)
berti_box = None

def set_berti_box_instance(instance):
    """Set the global BertiBox instance reference."""
    global berti_box
    berti_box = instance

def update_berti_box_playlist(playlist_id):
    """Helper to reload playlist items in BertiBox and emit status.
    
    Args:
        playlist_id: The ID of the playlist to update
    """
    if not berti_box:
        print("Update Helper: BertiBox not initialized.")
        return
    
    print(f"Helper: Updating BertiBox internal playlist for ID: {playlist_id}")
    try:
        from ..database import Database
        db = Database()
        
        updated_items_data = db.get_playlist_items(playlist_id)
        if berti_box.current_playlist and berti_box.current_playlist.get('id') == playlist_id:
            berti_box.current_playlist_items = updated_items_data
            # Also update the simplified list in the main playlist dict
            berti_box.current_playlist['items'] = [
                {'id': i['id'], 'mp3_file': i['mp3_file'], 'position': i['position']} 
                for i in updated_items_data
            ]
            # Adjust index if it's now out of bounds (e.g., after deletions)
            if berti_box.current_playlist_index >= len(updated_items_data):
                berti_box.current_playlist_index = max(0, len(updated_items_data) - 1)
            print(f"Helper: BertiBox playlist {playlist_id} updated internally.")
            berti_box.emit_player_status()  # Send update with new list/index
        else:
            # Playlist is not the currently active one in BertiBox, no internal update needed
            print(f"Helper: Playlist {playlist_id} is not the active one in BertiBox.")
    except Exception as e:
        print(f"Helper: Error updating BertiBox playlist {playlist_id}: {e}")
        traceback.print_exc()


def sanitize_path(path):
    """Sanitize a file path to prevent directory traversal.
    
    Args:
        path: The path to sanitize
        
    Returns:
        Sanitized path as string
    """
    # Convert to Path object for normalization
    p = Path(path)
    # Remove any parent directory references
    parts = []
    for part in p.parts:
        if part == '..' or part == '.':
            continue
        if part.startswith('/'):
            part = part[1:]
        parts.append(part)
    
    result = '/'.join(parts)
    # Remove leading slash
    if result.startswith('/'):
        result = result[1:]
    # Replace backslashes
    result = result.replace('\\', '/')
    # Remove duplicate slashes
    while '//' in result:
        result = result.replace('//', '/')
    return result


def is_safe_path(base_dir, path):
    """Check if a path is safe (within base directory).
    
    Args:
        base_dir: The base directory
        path: The path to check
        
    Returns:
        True if safe, False otherwise
    """
    try:
        # Resolve both paths to absolute
        base = os.path.abspath(base_dir)
        target = os.path.abspath(os.path.join(base_dir, path))
        # Check if target is within base
        return target.startswith(base)
    except:
        return False


def get_file_extension(filename):
    """Get file extension in lowercase.
    
    Args:
        filename: The filename
        
    Returns:
        Extension with dot (e.g., '.mp3') or empty string
    """
    if not filename:
        return ''
    ext = os.path.splitext(filename)[1]
    return ext.lower() if ext else ''


def format_file_size(size_bytes):
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    if size_bytes == 0:
        return '0 B'
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:  # Bytes
        return f'{int(size)} {units[unit_index]}'
    else:
        return f'{size:.1f} {units[unit_index]}'


def validate_mp3_file(filename):
    """Validate if a file is an MP3 file.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if valid MP3 file, False otherwise
    """
    if not filename:
        return False
    return get_file_extension(filename) == '.mp3'


def ensure_directory_exists(directory):
    """Ensure a directory exists, create if not.
    
    Args:
        directory: Directory path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(directory):
            return True
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {e}")
        return False


def normalize_path(path):
    """Normalize a path for cross-platform compatibility.
    
    Args:
        path: The path to normalize
        
    Returns:
        Normalized path string
    """
    if not path:
        return ''
    # Convert backslashes to forward slashes
    path = path.replace('\\', '/')
    # Remove leading slash
    if path.startswith('/'):
        path = path[1:]
    # Remove duplicate slashes
    while '//' in path:
        path = path.replace('//', '/')
    return path


def get_file_info(file_path):
    """Get information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file info or None if not found
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        name = os.path.basename(file_path)
        
        return {
            'name': name,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'extension': get_file_extension(name),
            'modified': stat.st_mtime
        }
    except Exception as e:
        print(f"Error getting file info for {file_path}: {e}")
        return None


def is_valid_filename(filename):
    """Check if a filename is valid.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in filename:
            return False
    
    return True