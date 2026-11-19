#!/usr/bin/env bash
# Install runtime packages in an isolated environment on Raspberry Pi OS.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev libportmidi-dev libjpeg-dev libpng-dev
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/run_game.sh" "$SCRIPT_DIR/install_autostart.sh"
"$SCRIPT_DIR/.venv/bin/python" -c 'import pygame; print(pygame.version.ver)'
printf 'Setup complete. Run ./run_game.sh. For login startup: ./install_autostart.sh desktop\n'
