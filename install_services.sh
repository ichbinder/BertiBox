#!/bin/bash

# Default values
INSTALL_DIR="/home/pi/git/BertiBox"
SERVICE_USER="pi"

# Function to display help
show_help() {
    echo "BertiBox Service Installer"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -d, --install-dir    Specify installation directory (default: /home/pi/git/BertiBox)"
    echo "  -u, --user          Specify service user (default: pi)"
    echo ""
    echo "Examples:"
    echo "  $0 --install-dir /opt/bertibox"
    echo "  $0 --user jakob"
    echo "  $0 --install-dir /opt/bertibox --user jakob"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -u|--user)
            SERVICE_USER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Installation directory $INSTALL_DIR does not exist"
    exit 1
fi

# Check if user exists
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Error: User $SERVICE_USER does not exist"
    exit 1
fi

# Update service files with correct paths and user
sed -i "s|User=.*|User=$SERVICE_USER|g" bertibox-web.service
sed -i "s|User=.*|User=$SERVICE_USER|g" bertibox-player.service
sed -i "s|/home/pi/git/BertiBox|$INSTALL_DIR|g" bertibox-web.service
sed -i "s|/home/pi/git/BertiBox|$INSTALL_DIR|g" bertibox-player.service

# Copy service files to systemd directory
sudo cp bertibox-web.service /etc/systemd/system/
sudo cp bertibox-player.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable bertibox-web.service
sudo systemctl enable bertibox-player.service

# Start services
sudo systemctl start bertibox-web.service
sudo systemctl start bertibox-player.service

echo "Services installed and started successfully!"
echo "Installation directory: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"
echo ""
echo "To check status:"
echo "sudo systemctl status bertibox-web.service"
echo "sudo systemctl status bertibox-player.service" 