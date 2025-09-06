"""Media explorer API endpoints - simplified version."""

from flask import Blueprint, jsonify, request
import os
import shutil
from .. import config
from ..database import Database

bp = Blueprint('media', __name__)
db = Database()

@bp.route('/mp3-files', methods=['GET'])
def get_mp3_files():
    """Get list of all MP3 files."""
    try:
        mp3_files = []
        for root, dirs, files in os.walk(config.MP3_DIR):
            for file in files:
                if file.endswith('.mp3'):
                    relative_path = os.path.relpath(os.path.join(root, file), config.MP3_DIR)
                    mp3_files.append(relative_path.replace(os.sep, '/'))
        
        return jsonify({'success': True, 'files': mp3_files})
    except Exception as e:
        print(f"Error getting MP3 files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/media', methods=['GET'])
def list_media():
    """List files and folders in a directory."""
    try:
        folder_path = request.args.get('path', '')
        
        # Strip leading slash if present
        if folder_path.startswith('/'):
            folder_path = folder_path[1:]
        
        # Security: ensure path doesn't escape MP3_DIR
        full_path = os.path.join(config.MP3_DIR, folder_path)
        full_path = os.path.abspath(full_path)
        
        if not full_path.startswith(os.path.abspath(config.MP3_DIR)):
            return jsonify({'success': False, 'error': 'Invalid path'}), 403
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': 'Path not found'}), 404
        
        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            relative_path = os.path.relpath(item_path, config.MP3_DIR).replace(os.sep, '/')
            
            if os.path.isdir(item_path):
                items.append({
                    'name': item,
                    'type': 'folder',
                    'path': relative_path
                })
            elif item.endswith('.mp3'):
                items.append({
                    'name': item,
                    'type': 'file',
                    'path': relative_path,
                    'assigned': db.is_file_in_playlist(relative_path)
                })
        
        # Sort: folders first, then files
        items.sort(key=lambda x: (x['type'] != 'folder', x['name'].lower()))
        
        return jsonify({
            'success': True,
            'current_path': folder_path,
            'items': items
        })
        
    except Exception as e:
        print(f"Error listing media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/media/folder', methods=['POST'])
def create_folder():
    """Create a new folder."""
    try:
        data = request.json
        folder_name = data.get('name')
        parent_path = data.get('parent', '')
        
        if not folder_name:
            return jsonify({'success': False, 'error': 'Folder name is required'}), 400
        
        # Sanitize folder name
        folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        if not folder_name:
            return jsonify({'success': False, 'error': 'Invalid folder name'}), 400
        
        # Create full path
        full_path = os.path.join(config.MP3_DIR, parent_path, folder_name)
        full_path = os.path.abspath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.abspath(config.MP3_DIR)):
            return jsonify({'success': False, 'error': 'Invalid path'}), 403
        
        if os.path.exists(full_path):
            return jsonify({'success': False, 'error': 'Folder already exists'}), 409
        
        os.makedirs(full_path)
        
        return jsonify({
            'success': True,
            'message': 'Folder created successfully',
            'folder_name': folder_name
        })
        
    except Exception as e:
        print(f"Error creating folder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/media/file', methods=['DELETE'])
def delete_media_file():
    """Delete a media file."""
    try:
        file_path = request.args.get('path')
        
        if not file_path:
            return jsonify({'success': False, 'error': 'File path is required'}), 400
        
        full_path = os.path.join(config.MP3_DIR, file_path)
        full_path = os.path.abspath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.abspath(config.MP3_DIR)):
            return jsonify({'success': False, 'error': 'Invalid path'}), 403
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Check if file is in use
        if db.is_file_used(file_path):
            return jsonify({'success': False, 'error': 'File is in use by a playlist'}), 409
        
        os.remove(full_path)
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/media/folder', methods=['DELETE'])
def delete_media_folder():
    """Delete a media folder."""
    try:
        folder_path = request.args.get('path')
        
        if not folder_path:
            return jsonify({'success': False, 'error': 'Folder path is required'}), 400
        
        full_path = os.path.join(config.MP3_DIR, folder_path)
        full_path = os.path.abspath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.abspath(config.MP3_DIR)):
            return jsonify({'success': False, 'error': 'Invalid path'}), 403
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': 'Folder not found'}), 404
        
        # Check if any files in folder are in use
        if db.are_files_in_folder_used(folder_path, config.MP3_DIR):
            return jsonify({'success': False, 'error': 'Folder contains files in use'}), 409
        
        shutil.rmtree(full_path)
        
        return jsonify({'success': True, 'message': 'Folder deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting folder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500