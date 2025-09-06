"""Tag management API endpoints."""

from flask import Blueprint, jsonify, request
from ..database import Database

bp = Blueprint('tags', __name__)
db = Database()

@bp.route('/tags', methods=['GET'])
def get_tags():
    """Get all tags with their playlists."""
    try:
        tags = db.get_all_tags()
        return jsonify({'success': True, 'tags': tags})
    except Exception as e:
        print(f"Error getting tags: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/tags', methods=['POST'])
def add_tag():
    """Add a new tag with optional playlist."""
    try:
        data = request.json
        tag_id = data.get('tag_id')
        tag_name = data.get('tag_name', f'Neuer Tag {tag_id}')
        playlist_name = data.get('playlist_name', tag_name)
        
        if not tag_id:
            return jsonify({'success': False, 'error': 'tag_id is required'}), 400
        
        # Check if tag exists
        existing_tag = db.get_tag(tag_id)
        if existing_tag:
            return jsonify({'success': False, 'error': 'Tag already exists'}), 409
        
        # Add tag
        new_tag = db.add_tag(tag_id, tag_name)
        
        # Add default playlist
        if new_tag:
            playlist = db.add_playlist(tag_id, playlist_name)
            if playlist:
                return jsonify({
                    'success': True,
                    'message': 'Tag and playlist created successfully',
                    'tag_id': tag_id,
                    'playlist_id': playlist.id
                })
        
        return jsonify({'success': False, 'error': 'Failed to create tag'}), 500
        
    except Exception as e:
        print(f"Error adding tag: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/tags/<tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag and its associated playlists."""
    try:
        if db.delete_tag(tag_id):
            return jsonify({'success': True, 'message': 'Tag deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
    except Exception as e:
        print(f"Error deleting tag {tag_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/tags/<tag_id>/playlist', methods=['GET'])
def get_tag_playlist(tag_id):
    """Get the playlist associated with a tag."""
    try:
        tag = db.get_tag(tag_id)
        if not tag:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
        
        if tag.get('playlists'):
            playlist_id = tag['playlists'][0]['id']
            items = db.get_playlist_items(playlist_id)
            return jsonify({
                'success': True,
                'id': playlist_id,  # Frontend expects 'id' not 'playlist_id'
                'playlist_id': playlist_id,  # Keep for backward compatibility
                'items': items
            })
        
        return jsonify({'success': True, 'id': None, 'playlist_id': None, 'items': []})
        
    except Exception as e:
        print(f"Error getting playlist for tag {tag_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500