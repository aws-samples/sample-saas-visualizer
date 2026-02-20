#!/bin/bash
#
# Run visualizer-display in hardware mode
#
# This script runs the application with hardware display support.
# Works with both regular user execution and sudo (required for GPIO access).
# uv automatically manages the virtual environment.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Source common functions
source "$SCRIPT_DIR/common.sh"

# Find uv binary (exits with error if not found)
UV_BIN=$(require_uv)
echo "Using uv: $UV_BIN"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Please run: cp .env.example .env"
    exit 1
fi

# Ensure LED_EMULATOR_MODE is false (or unset)
export LED_EMULATOR_MODE=false

# Set default config path (can be overridden with CONFIG_PATH env var)
# For Raspberry Pi with awsdemo user
CONFIG_PATH="${CONFIG_PATH:-/home/awsdemo/iot-certificates/device-config.json}"

# Check if config file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Configuration file not found: $CONFIG_PATH"
    echo "Please ensure device-config.json exists or set CONFIG_PATH environment variable"
    exit 1
fi

# Run the application (uv handles virtualenv automatically)
echo "Starting visualizer-display in HARDWARE mode..."
echo "Using config: $CONFIG_PATH"
"$UV_BIN" run python -m visualizer_display --config "$CONFIG_PATH"
