"""Main Flask application for BertiBox."""

import os
import atexit
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
from database import Database
from core import BertiBox
from utils import helpers
import config

# Import API blueprints
from api import (
    tags_bp, 
    playlists_bp, 
    media_bp, 
    player_bp, 
    upload_bp
)

# Import WebSocket handlers
from websocket import register_handlers

# Initialize Flask app with correct template and static paths
import os
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Initialize SocketIO
socketio = SocketIO(app)

# Initialize database
db = Database()

# Initialize BertiBox (will be done after app context is ready)
berti_box = None

# Create MP3 directory if it doesn't exist
os.makedirs(config.MP3_DIR, exist_ok=True)

# Register API blueprints
app.register_blueprint(tags_bp, url_prefix='/api')
app.register_blueprint(playlists_bp, url_prefix='/api')
app.register_blueprint(media_bp, url_prefix='/api')
app.register_blueprint(player_bp, url_prefix='/api')
app.register_blueprint(upload_bp, url_prefix='/api')

# Register WebSocket handlers
register_handlers(socketio, lambda: berti_box)

# Basic routes
@app.route('/')
def index():
    """Main page showing tag management interface."""
    try:
        tags = db.get_all_tags()
        return render_template('index.html', tags=tags)
    except Exception as e:
        print(f"Error loading index page: {e}")
        return render_template('index.html', tags=[])

@app.route('/player')
def player():
    """Player control page."""
    try:
        tags = db.get_all_tags()
        return render_template('player.html', tags=tags)
    except Exception as e:
        print(f"Error loading player page: {e}")
        return render_template('player.html', tags=[])

@app.route('/explorer')
def media_explorer():
    """Media explorer page."""
    return render_template('explorer.html')

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for undefined paths."""
    return render_template('404.html'), 404

def cleanup():
    """Cleanup function called on exit."""
    if berti_box:
        berti_box.stop()
    print("Cleanup completed.")

def init_berti_box():
    """Initialize BertiBox in a separate thread."""
    global berti_box
    print("Starting Flask app and BertiBox...")
    
    # Initialize database
    db.init_db()
    
    # Initialize BertiBox
    berti_box = BertiBox(socketio, db)
    
    # Set the BertiBox instance in helpers module
    helpers.set_berti_box_instance(berti_box)
    
    print("BertiBox initialized successfully, starting background thread...")
    
    # Start BertiBox in a separate thread
    berti_thread = threading.Thread(target=berti_box.start)
    berti_thread.daemon = True
    berti_thread.start()

# Register cleanup function
atexit.register(cleanup)

if __name__ == '__main__':
    # Initialize BertiBox before starting Flask app
    init_berti_box()
    
    # Run the Flask app with SocketIO
    socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG)