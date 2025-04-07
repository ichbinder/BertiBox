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

# Create and configure systemd service files
cat > /etc/systemd/system/bertibox-web.service << EOF
[Unit]
Description=BertiBox Web Interface Service
After=network.target bertibox-player.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/web_interface.py
Restart=always
RestartSec=10
StandardOutput=append:/home/$USER/bertibox-web.log
StandardError=append:/home/$USER/bertibox-web.log

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/bertibox-player.service << EOF
[Unit]
Description=BertiBox MP3 Player Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/$USER/bertibox-player.log
StandardError=append:/home/$USER/bertibox-player.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new services
systemctl daemon-reload

# Enable and start services
systemctl enable bertibox-web.service
systemctl enable bertibox-player.service
systemctl start bertibox-web.service
systemctl start bertibox-player.service

echo "Installation completed successfully!"
echo "Services have been started and enabled."
echo "Installation directory: $INSTALL_DIR"
echo "Service user: $USER"
echo "Check service status with: systemctl status bertibox-web.service bertibox-player.service" 