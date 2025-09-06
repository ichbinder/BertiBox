#!/usr/bin/env python3
"""Convenience script to run BertiBox directly."""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

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