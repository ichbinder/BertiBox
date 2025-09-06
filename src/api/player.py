"""Player control API endpoints."""

from flask import Blueprint, jsonify

bp = Blueprint('player', __name__)

# Player control endpoints would be here
# Most player control is handled via WebSocket events
# This could include REST endpoints for player status if needed