# Berti Box

A Raspberry Pi 4 based RFID music player that plays MP3s when specific RFID tags are placed on the reader. The system includes a web interface for managing RFID tag and MP3 associations.

## Features

- RFID tag detection using RC522 module
- MP3 playback through Raspberry Pi audio output
- Web interface for managing RFID-MP3 associations
- SQLite database for storing RFID-MP3 mappings

## Hardware Requirements

- Raspberry Pi 4
- RFID-RC522 module
- Speaker/Headphones with 3.5mm jack
- Jumper wires

## Software Requirements

- Python 3.x
- Virtual environment
- Flask
- RPi.GPIO
- mfrc522
- pygame
- SQLAlchemy

## Installation

1. Clone this repository:
```bash
git clone [repository-url]
cd BertiBox
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Install system dependencies:
```bash
sudo apt-get install libsdl2-dev libsdl2-ttf-dev libsdl2-image-dev libsdl2-mixer-dev
```

5. Create the mp3 directory:
```bash
mkdir mp3
```

6. Set up the database:
```bash
python init_db.py
```

## Usage

1. Activate the virtual environment:
```bash
source venv/bin/activate
```

2. Start the application:
```bash
python main.py
```

3. In a separate terminal, start the web interface:
```bash
source venv/bin/activate
python web_interface.py
```

4. Access the web interface at `http://[raspberry-pi-ip]:5000`

5. Place an RFID tag on the reader to play associated MP3s

## Web Interface

The web interface allows you to:
- View current RFID tag on reader
- Associate MP3 files with RFID tags
- Manage existing associations

## Project Structure

- `main.py`: Main application file
- `rfid_reader.py`: RFID reader module
- `web_interface.py`: Web interface module
- `database.py`: Database management
- `mp3/`: Directory for MP3 files
- `static/`: Web interface static files
- `templates/`: Web interface templates 