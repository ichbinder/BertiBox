from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from database import Database, Base, Tag, Playlist, PlaylistItem
import os
import atexit

app = Flask(__name__)
socketio = SocketIO(app)
db = Database()

# MP3-Verzeichnis
MP3_DIR = 'mp3'

@app.route('/')
def index():
    # MP3-Dateien aus dem Verzeichnis laden
    mp3_files = [f for f in os.listdir(MP3_DIR) if f.endswith('.mp3')]
    return render_template('index.html', mp3_files=mp3_files)

@app.route('/api/current-tag', methods=['POST'])
def current_tag():
    data = request.get_json()
    tag_id = data.get('tag_id')
    socketio.emit('tag_detected', {'tag_id': tag_id})
    
    try:
        # Tag und Playlist finden oder erstellen
        tag = db.get_tag(tag_id)
        if not tag:
            tag = db.add_tag(tag_id)
        
        # Hole die Playlist in einer neuen Session
        session = db.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if not tag.playlists:
                # Neue Playlist erstellen
                playlist = Playlist(name=f"Playlist für {tag.name or tag_id}")
                tag.playlists.append(playlist)
                session.add(playlist)
                session.commit()
                playlist_id = playlist.id
            else:
                playlist_id = tag.playlists[0].id
                
            # Hole die Playlist-Items
            items = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).order_by(PlaylistItem.position).all()
            
            # Sende die Playlist-Informationen an den Client
            socketio.emit('playlist_selected', {
                'id': playlist_id,
                'name': tag.playlists[0].name,
                'items': [{
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                } for item in items]
            })
            
            return jsonify({'status': 'success'})
        finally:
            session.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags', methods=['GET'])
def get_tags():
    try:
        tags = db.get_all_tags()
        return jsonify([{
            'id': tag['id'],
            'tag_id': tag['tag_id'],
            'name': tag['name'],
            'playlist': tag['playlists'][0]['name'] if tag['playlists'] else None
        } for tag in tags])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags', methods=['POST'])
def add_tag():
    data = request.get_json()
    tag_id = data.get('tag_id')
    name = data.get('name')
    
    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400
        
    try:
        # Prüfe, ob der Tag bereits existiert
        existing_tag = db.get_tag(tag_id)
        if existing_tag:
            # Tag aktualisieren
            updated_tag = db.update_tag(tag_id, name)
            if updated_tag:
                return jsonify({
                    'id': updated_tag.id,
                    'tag_id': updated_tag.tag_id,
                    'name': updated_tag.name
                })
            return jsonify({'error': 'Failed to update tag'}), 500
            
        # Neuen Tag erstellen
        tag = db.add_tag(tag_id, name)
        return jsonify({
            'id': tag.id,
            'tag_id': tag.tag_id,
            'name': tag.name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags/<tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    if db.delete_tag(tag_id):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Tag not found'}), 404

@app.route('/api/playlists', methods=['POST'])
def add_playlist():
    data = request.get_json()
    tag_id = data.get('tag_id')
    name = data.get('name')
    
    if not tag_id or not name:
        return jsonify({'error': 'Tag ID and name are required'}), 400
        
    try:
        # Tag und Playlist in einer Session erstellen
        session = db.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if not tag:
                tag = Tag(tag_id=tag_id)
                session.add(tag)
            
            playlist = Playlist(name=name)
            tag.playlists.append(playlist)
            session.add(playlist)
            session.commit()
            
            # Hole die ID vor dem Schließen der Session
            playlist_id = playlist.id
            playlist_name = playlist.name
            
            return jsonify({
                'id': playlist_id,
                'name': playlist_name,
                'tag_id': tag_id
            })
        finally:
            session.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlists/<int:playlist_id>/items', methods=['GET'])
def get_playlist_items(playlist_id):
    try:
        items = db.get_playlist_items(playlist_id)
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlists/<int:playlist_id>/items', methods=['POST'])
def add_playlist_item(playlist_id):
    data = request.get_json()
    mp3_file = data.get('mp3_file')
    position = data.get('position', 0)
    
    if not mp3_file:
        return jsonify({'error': 'MP3 file is required'}), 400
    
    try:
        # Hole die aktuelle Anzahl der Items in der Playlist
        current_items = db.get_playlist_items(playlist_id)
        position = len(current_items)
        
        item = db.add_playlist_item(playlist_id, mp3_file, position)
        if item:
            return jsonify({
                'id': item.id,
                'playlist_id': item.playlist_id,
                'mp3_file': item.mp3_file,
                'position': item.position
            })
        return jsonify({'error': 'Playlist not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist-items/<item_id>', methods=['PUT'])
def update_playlist_item(item_id):
    data = request.get_json()
    new_position = data.get('position')
    
    if new_position is None:
        return jsonify({'error': 'Position is required'}), 400
        
    if db.update_playlist_item_position(item_id, new_position):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Item not found'}), 404

@app.route('/api/playlist-items/<item_id>', methods=['DELETE'])
def delete_playlist_item(item_id):
    if db.delete_playlist_item(item_id):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Item not found'}), 404

@app.route('/api/mp3-files', methods=['GET'])
def get_mp3_files():
    mp3_files = [f for f in os.listdir(MP3_DIR) if f.endswith('.mp3')]
    return jsonify(mp3_files)

@app.route('/api/tags/<tag_id>/playlist', methods=['GET'])
def get_tag_playlist(tag_id):
    try:
        # Hole den Tag mit seinen Playlists
        tag = db.get_tag(tag_id)
        if not tag:
            return jsonify({'playlist_id': None})
            
        # Hole die Playlist in einer neuen Session
        session = db.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if not tag.playlists:
                return jsonify({'playlist_id': None})
                
            playlist = tag.playlists[0]
            items = session.query(PlaylistItem).filter_by(playlist_id=playlist.id).order_by(PlaylistItem.position).all()
            
            return jsonify({
                'id': playlist.id,
                'name': playlist.name,
                'items': [{
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                } for item in items]
            })
        finally:
            session.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlists/<int:playlist_id>/items/batch', methods=['POST'])
def add_playlist_items_batch(playlist_id):
    data = request.get_json()
    mp3_files = data.get('mp3_files', [])
    
    if not mp3_files:
        return jsonify({'error': 'MP3 files are required'}), 400
    
    try:
        items = db.add_playlist_items(playlist_id, mp3_files)
        if items:
            return jsonify(items)
        return jsonify({'error': 'Playlist not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup():
    db.cleanup()

if __name__ == '__main__':
    atexit.register(cleanup)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 