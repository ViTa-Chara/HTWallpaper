#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "HTWallpaper Setup"
echo "========================================"
echo

# Check if uv is already installed system-wide
if command -v uv &>/dev/null; then
    echo "[OK] uv is already installed system-wide."
    UV="uv"
else
    # Check if local uv exists
    LOCAL_UV="$ROOT_DIR/.uv/uv"
    if [ -x "$LOCAL_UV" ]; then
        echo "[OK] Found local uv at .uv/uv"
        UV="$LOCAL_UV"
    else
        # Download and install uv locally
        echo "[INFO] uv not found. Installing uv locally..."
        UV_DIR="$ROOT_DIR/.uv"
        mkdir -p "$UV_DIR"
        
        # Download uv
        curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$UV_DIR" sh
        
        if [ ! -x "$LOCAL_UV" ]; then
            echo "[ERROR] Failed to install uv."
            exit 1
        fi
        
        UV="$LOCAL_UV"
        echo "[OK] uv installed at $UV"
    fi
fi

# Sync dependencies
echo
echo "[INFO] Syncing dependencies..."
"$UV" sync --no-dev

echo
echo "========================================"
echo "[OK] Setup complete!"
echo "========================================"
echo
echo "You can now run the application using:"
echo "  ./run.command"
echo
