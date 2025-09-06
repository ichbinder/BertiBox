"""File upload API endpoints."""

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import os
from .. import config

bp = Blueprint('upload', __name__)

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@bp.route('/upload-mp3', methods=['POST'])
def upload_mp3():
    """Handle MP3 file upload."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        target_folder = request.form.get('target_folder', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Create target directory if needed
            if target_folder:
                target_path = os.path.join(config.MP3_DIR, target_folder)
                os.makedirs(target_path, exist_ok=True)
            else:
                target_path = config.MP3_DIR
            
            filepath = os.path.join(target_path, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                return jsonify({'success': False, 'error': 'File already exists'}), 409
            
            file.save(filepath)
            
            # Calculate relative path for database
            relative_path = os.path.relpath(filepath, config.MP3_DIR).replace(os.sep, '/')
            
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'filename': filename,
                'path': relative_path
            })
        
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500