#!/bin/bash

# Default values
INSTALL_DIR="/home/pi/git/BertiBox"
USER="pi"

# Function to display help
show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -d, --dir DIR     Set installation directory (default: /home/pi/git/BertiBox)"
    echo "  -u, --user USER   Set user for services (default: pi)"
    echo "  -h, --help        Show this help message"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# Remove trailing slash from INSTALL_DIR if it exists
INSTALL_DIR=${INSTALL_DIR%/}

# Stop and disable the old player service if it exists
echo "Stopping and disabling old bertibox-player service (if exists)..."
systemctl stop bertibox-player.service > /dev/null 2>&1
systemctl disable bertibox-player.service > /dev/null 2>&1
rm -f /etc/systemd/system/bertibox-player.service

# Create and configure systemd service file for web interface
cat > /etc/systemd/system/bertibox-web.service << EOF
[Unit]
Description=BertiBox Web Interface and Player Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/run.py
Restart=always
RestartSec=10
StandardOutput=append:/home/$USER/bertibox-web.log
StandardError=append:/home/$USER/bertibox-web.log
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize changes
systemctl daemon-reload

# Enable and start the web service
systemctl enable bertibox-web.service
systemctl start bertibox-web.service

echo "Installation/Update completed successfully!"
echo "The unified BertiBox service (web + player) has been started and enabled."
echo "Installation directory: $INSTALL_DIR"
echo "Service user: $USER"
echo "Check service status with: systemctl status bertibox-web.service" 