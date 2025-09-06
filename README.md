# BertiBox

A Raspberry Pi 4-based RFID music player that plays MP3s when RFID tags are placed on the reader. The system includes a modern web interface for managing RFID tag and playlist associations.

## Features

- **RFID tag detection** using RC522 module
- **MP3 playback** through Raspberry Pi audio output
- **Modern web interface** with real-time updates via WebSocket
- **Playlist management** - Multiple MP3s per RFID tag with drag & drop sorting
- **Media explorer** - Browse, upload, and manage MP3 files
- **Player controls** - Play, pause, volume control, sleep timer
- **SQLite database** for persistent data storage
- **Systemd service** for automatic startup on boot

## Hardware Requirements

- Raspberry Pi 4
- RFID-RC522 module
- Speaker/Headphones with 3.5mm jack
- Jumper wires

## Software Requirements

- Python 3.9+
- Virtual environment
- Flask with SocketIO
- RPi.GPIO
- mfrc522
- pygame
- SQLAlchemy

## Installation

### Quick Installation with Script

```bash
# Clone repository
git clone [repository-url]
cd BertiBox

# Install as systemd service
sudo ./scripts/install.sh -d /home/pi/git/BertiBox -u pi
```

### Manual Installation

1. **Clone repository:**
```bash
git clone [repository-url]
cd BertiBox
```

2. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install BertiBox package:**
```bash
# Standard installation
pip install .

# Or for development with editable install:
pip install -e .

# For development with testing tools:
pip install -e ".[dev]"
```

4. **Install system dependencies:**
```bash
sudo apt-get install libsdl2-dev libsdl2-ttf-dev libsdl2-image-dev libsdl2-mixer-dev
```

5. **Create MP3 directory:**
```bash
mkdir -p mp3
```

6. **Initialize database:**
```bash
python -c "from src.database import init_db; init_db()"
```

## Usage

### As Standalone Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start application
python run.py
# Or
python -m src
# Or if installed via pip
bertibox
```

### As Systemd Service

```bash
# Check service status
systemctl status bertibox-web.service

# View logs
journalctl -u bertibox-web.service -f
# Or
tail -f /home/pi/bertibox-web.log

# Restart service
sudo systemctl restart bertibox-web.service
```

### Web Interface

After starting, the web interface is available at:
- `http://[raspberry-pi-ip]:5000`

## Web Interface Features

### Main Page (`/`)
- Real-time current RFID tag display
- Tag management with playlist assignment
- Drag & drop for playlist ordering
- Quick MP3 selection from media explorer

### Player (`/player`)
- Play/Pause controls
- Volume control (persisted in database)
- Sleep timer function
- Current playback status

### Media Explorer (`/explorer`)
- File browser for MP3 directory
- MP3 upload with progress indicator
- File rename and delete
- Directory navigation

## Project Structure

```
BertiBox/
├── src/                     # Source code
│   ├── __main__.py         # Entry point
│   ├── app.py              # Flask application
│   ├── config.py           # Configuration
│   ├── rfid_reader.py      # RFID hardware interface
│   ├── core/               # Core functionality
│   │   └── player.py       # BertiBox player class
│   ├── api/                # REST API endpoints
│   │   ├── tags.py         # Tag management
│   │   ├── playlists.py    # Playlist management
│   │   ├── media.py        # Media explorer
│   │   ├── player.py       # Player controls
│   │   └── upload.py       # File upload
│   ├── websocket/          # WebSocket handlers
│   │   └── handlers.py     # Socket.IO events
│   ├── database/           # Database layer
│   │   ├── models.py       # SQLAlchemy models
│   │   └── manager.py      # Database operations
│   └── utils/              # Utility functions
├── tests/                   # Test suite
├── templates/               # HTML templates
├── static/                  # CSS, JavaScript
├── mp3/                     # MP3 file storage
├── scripts/                 # Installation scripts
├── systemd/                 # Service configuration
├── run.py                   # Quick start script
├── setup.py                 # Package installation
├── pyproject.toml          # Modern Python packaging
├── Makefile                # Build automation
└── CLAUDE.md               # Developer documentation
```

## API Endpoints

- `GET /api/current-tag` - Current RFID tag status
- `GET/POST /api/tags` - Tag management
- `GET/POST /api/playlist/<id>/items` - Manage playlist items
- `GET /api/explorer` - File browser
- `POST /api/player/play|pause|volume|sleep` - Player controls
- `POST /api/upload` - MP3 upload

## Development

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

### Code Quality

```bash
# Linting
make lint

# Type checking
make typecheck

# Check everything
make check
```

## Troubleshooting

### RFID Reader Not Detected
- Enable SPI in `raspi-config`
- Check wiring (see hardware documentation)
- Check service logs: `journalctl -u bertibox-web -f`

### No Audio Output
- Configure audio output: `sudo raspi-config` > Advanced Options > Audio
- Check volume: `alsamixer`
- Test sound: `speaker-test -t wav -c 2`

### Web Interface Not Accessible
- Check firewall settings
- Verify service is running: `systemctl status bertibox-web`
- Check port 5000 is free: `sudo netstat -tlnp | grep 5000`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.