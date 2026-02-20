#!/bin/bash
#
# Install visualizer-display as a systemd service
#
# This script copies the service file and enables the service.
# Must be run as root or with sudo.
#
# Usage:
#   sudo ./scripts/install-service.sh
#   sudo CONFIG_PATH=/custom/path/config.json ./scripts/install-service.sh
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_TEMPLATE="$SCRIPT_DIR/visualizer-display.service"
SYSTEMD_DIR="/etc/systemd/system"

# Source common functions
source "$SCRIPT_DIR/common.sh"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Usage: sudo $0"
    exit 1
fi

# Check service file exists
if [ ! -f "$SERVICE_TEMPLATE" ]; then
    echo "Error: Service template not found: $SERVICE_TEMPLATE"
    exit 1
fi

# Detect the actual user (not root)
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
else
    # If not running via sudo, prompt for username
    echo "Warning: Not running via sudo, cannot detect user automatically"
    read -rp "Enter the username that owns the project: " ACTUAL_USER
fi

ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")

# Find uv binary using common function
UV_PATH=$(find_uv)

if [ -z "$UV_PATH" ]; then
    echo "Error: uv not found"
    echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Set default CONFIG_PATH if not provided
CONFIG_PATH="${CONFIG_PATH:-$ACTUAL_HOME/iot-certificates/device-config.json}"

# Set ENV_FILE path
ENV_FILE="$PROJECT_DIR/.env"

echo "Installing visualizer-display service"
echo "  User: $ACTUAL_USER"
echo "  Home: $ACTUAL_HOME"
echo "  Project: $PROJECT_DIR"
echo "  uv: $UV_PATH"
echo "  Config: $CONFIG_PATH"
echo "  Env file: $ENV_FILE"
echo ""

# Check for config file
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Warning: Config file not found: $CONFIG_PATH"
    echo "The service will fail to start until the config file exists."
    echo ""
fi

# Check for .env file
if [ ! -f "$ENV_FILE" ]; then
    echo "Warning: .env file not found: $ENV_FILE"
    echo "Please copy .env.example to .env before starting the service."
    echo ""
fi

# Create customized service file
TEMP_SERVICE=$(mktemp)

# Read template and replace paths
sed -e "s|/home/awsdemo|$ACTUAL_HOME|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" \
    -e "s|EnvironmentFile=.*|EnvironmentFile=$ENV_FILE|" \
    -e "s|Environment=\"CONFIG_PATH=.*\"|Environment=\"CONFIG_PATH=$CONFIG_PATH\"|" \
    -e "s|Environment=\"LED_MATRIX_DROP_PRIV_USER=.*\"|Environment=\"LED_MATRIX_DROP_PRIV_USER=$ACTUAL_USER\"|" \
    -e "s|Environment=\"LED_MATRIX_DROP_PRIV_GROUP=.*\"|Environment=\"LED_MATRIX_DROP_PRIV_GROUP=$ACTUAL_USER\"|" \
    -e "s|ExecStart=.*/uv|ExecStart=$UV_PATH|" \
    "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"

# Copy to systemd directory
cp "$TEMP_SERVICE" "$SYSTEMD_DIR/visualizer-display.service"
rm "$TEMP_SERVICE"

# Set correct permissions
chmod 644 "$SYSTEMD_DIR/visualizer-display.service"

# Reload systemd
systemctl daemon-reload

echo ""
echo "Service installed successfully!"
echo ""
echo "Commands:"
echo "  sudo systemctl start visualizer-display    # Start the service"
echo "  sudo systemctl stop visualizer-display     # Stop the service"
echo "  sudo systemctl status visualizer-display   # Check status"
echo "  sudo systemctl enable visualizer-display   # Enable auto-start at boot"
echo "  sudo systemctl disable visualizer-display  # Disable auto-start"
echo "  journalctl -u visualizer-display -f        # View live logs"
echo ""
echo "To enable auto-start at boot, run:"
echo "  sudo systemctl enable visualizer-display"
