#!/bin/bash
#
# Run visualizer-display in emulator mode
#
# This script runs the application with software emulator support for development.
# No root/sudo required - the emulator runs entirely in userspace.
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

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Please run: cp .env.example .env"
    exit 1
fi

# Force emulator mode
export LED_EMULATOR_MODE=true

# Set default config path (can be overridden with CONFIG_PATH env var)
# Relative path for development environment
CONFIG_PATH="${CONFIG_PATH:-../../iot-certificates/device-config.json}"

# Check if config file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Configuration file not found: $CONFIG_PATH"
    echo "Please ensure device-config.json exists or set CONFIG_PATH environment variable"
    exit 1
fi

# Run the application (uv handles virtualenv automatically)
echo "Starting visualizer-display in EMULATOR mode..."
echo "Using config: $CONFIG_PATH"
"$UV_BIN" run python -m visualizer_display --config "$CONFIG_PATH"
