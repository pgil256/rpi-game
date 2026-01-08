#!/bin/bash
# Weasel Entertainment System - Game Runner Script
# This script runs the game in fullscreen mode

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Hide mouse cursor
export SDL_NOMOUSE=1

# Determine the best video driver for this environment
# Priority: kmsdrm (Pi Lite/console) > x11 (desktop) > default (let SDL decide)

if [ -z "$DISPLAY" ]; then
    # No X11 display - we're likely on console/tty, use kmsdrm
    export SDL_VIDEODRIVER=kmsdrm
else
    # X11 is available, use it
    export SDL_VIDEODRIVER=x11
fi

# Run the game with fullscreen flag
exec python3 "$SCRIPT_DIR/game_launcher.py" --fullscreen
