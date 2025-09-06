"""Playlist management API endpoints."""

from flask import Blueprint, jsonify, request
from ..database import Database
from ..utils.helpers import update_berti_box_playlist

bp = Blueprint('playlists', __name__)
db = Database()

@bp.route('/playlists', methods=['POST'])
def add_playlist():
    """Create a new playlist for a tag."""
    try:
        data = request.json
        tag_id = data.get('tag_id')
        playlist_name = data.get('name')
        
        if not tag_id or not playlist_name:
            return jsonify({'success': False, 'error': 'tag_id and name are required'}), 400
        
        playlist = db.add_playlist(tag_id, playlist_name)
        if playlist:
            return jsonify({
                'success': True,
                'message': 'Playlist created successfully',
                'playlist_id': playlist.id
            })
        
        return jsonify({'success': False, 'error': 'Failed to create playlist'}), 500
        
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/playlists/<int:playlist_id>/items', methods=['GET'])
def get_playlist_items(playlist_id):
    """Get all items in a playlist."""
    try:
        items = db.get_playlist_items(playlist_id)
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        print(f"Error getting playlist items: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/playlists/<int:playlist_id>/items', methods=['POST'])
def add_playlist_item(playlist_id):
    """Add an item to a playlist."""
    try:
        data = request.json
        mp3_file = data.get('mp3_file')
        
        if not mp3_file:
            return jsonify({'success': False, 'error': 'mp3_file is required'}), 400
        
        item = db.add_playlist_item(playlist_id, mp3_file)
        if item:
            # Update BertiBox if this playlist is currently playing
            update_berti_box_playlist(playlist_id)
            
            return jsonify({
                'success': True,
                'message': 'Item added successfully',
                'item': item  # item is already a dict
            })
        
        return jsonify({'success': False, 'error': 'Failed to add item'}), 500
        
    except Exception as e:
        print(f"Error adding playlist item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/playlists/<int:playlist_id>/items/batch', methods=['POST'])
def add_playlist_items_batch(playlist_id):
    """Add multiple items to a playlist."""
    try:
        data = request.json
        mp3_files = data.get('mp3_files', [])
        
        if not mp3_files:
            return jsonify({'success': False, 'error': 'mp3_files array is required'}), 400
        
        added_items = db.add_playlist_items(playlist_id, mp3_files)
        if added_items:
            # Update BertiBox if this playlist is currently playing
            update_berti_box_playlist(playlist_id)
            
            return jsonify({
                'success': True,
                'message': f'Added {len(added_items)} items successfully',
                'items': added_items
            })
        
        return jsonify({'success': False, 'error': 'Failed to add items'}), 500
        
    except Exception as e:
        print(f"Error batch adding playlist items: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/playlist-items/<int:item_id>', methods=['PUT'])
def update_playlist_item_position(item_id):
    """Update the position of an item in a playlist."""
    try:
        data = request.json
        new_position = data.get('position')
        
        if new_position is None:
            return jsonify({'success': False, 'error': 'position is required'}), 400
        
        if db.update_playlist_item_position(item_id, new_position):
            return jsonify({'success': True, 'message': 'Position updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update position'}), 500
            
    except Exception as e:
        print(f"Error updating playlist item position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/playlist-items/<int:item_id>', methods=['DELETE'])
def delete_playlist_item(item_id):
    """Delete an item from a playlist."""
    try:
        if db.delete_playlist_item(item_id):
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
            
    except Exception as e:
        print(f"Error deleting playlist item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500