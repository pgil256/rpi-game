#!/bin/bash
# Weasel Entertainment System - Raspberry Pi Start Script
#
# This script starts the game with optimal settings for Raspberry Pi.
# Install as auto-start by creating /etc/xdg/autostart/wes.desktop:
#
#   [Desktop Entry]
#   Type=Application
#   Name=Weasel Entertainment System
#   Exec=/home/pi/wes/start.sh
#   X-GNOME-Autostart-enabled=true
#
# Or add to /etc/rc.local (before 'exit 0'):
#   su - pi -c '/home/pi/wes/start.sh' &

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set environment variables for Raspberry Pi optimization
export SDL_VIDEODRIVER=x11  # or 'kmsdrm' for console-only
export SDL_AUDIODRIVER=pulse  # or 'alsa' for direct ALSA

# Disable screen saver and power management
if command -v xset &> /dev/null; then
    xset s off
    xset -dpms
    xset s noblank
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the game
# Use nice to give the game high priority
exec nice -n -5 python3 game_launcher.py "$@"
