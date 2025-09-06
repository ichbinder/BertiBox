"""Main entry point for BertiBox application.

Run with: python -m src
"""

from app import app, socketio, init_berti_box
import config

if __name__ == "__main__":
    # Initialize and start BertiBox in background
    init_berti_box()
    
    # Run Flask-SocketIO server
    print(f"Starting BertiBox Web Interface on {config.HOST}:{config.PORT}")
    socketio.run(app, 
                 host=config.HOST, 
                 port=config.PORT, 
                 debug=config.DEBUG)