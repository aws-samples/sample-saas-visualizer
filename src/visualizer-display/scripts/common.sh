#!/bin/bash
#
# Common functions for visualizer-display scripts
#

# Find uv binary - check common locations
# When running under sudo, uses $SUDO_USER to find the original user's uv
find_uv() {
    # If uv is already in PATH, use it
    if command -v uv &> /dev/null; then
        command -v uv
        return
    fi

    # Determine the actual user (works whether running as root via sudo or directly)
    if [ -n "$SUDO_USER" ]; then
        REAL_USER="$SUDO_USER"
    else
        REAL_USER="$(whoami)"
    fi

    # Get the user's home directory
    REAL_HOME=$(eval echo "~$REAL_USER")

    # Check common uv installation locations
    local uv_paths=(
        "$REAL_HOME/.local/bin/uv"
        "$REAL_HOME/.cargo/bin/uv"
        "/usr/local/bin/uv"
        "/usr/bin/uv"
    )

    for uv_path in "${uv_paths[@]}"; do
        if [ -x "$uv_path" ]; then
            echo "$uv_path"
            return
        fi
    done

    # Not found
    echo ""
}

# Require uv to be available, exit with error if not found
require_uv() {
    local uv_bin
    uv_bin=$(find_uv)

    if [ -z "$uv_bin" ]; then
        echo "Error: uv not found"
        echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    echo "$uv_bin"
}
