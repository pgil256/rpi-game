#!/bin/bash
# Weasel Entertainment System (WES) - Raspberry Pi Setup Script
# Run this script once after copying the game to your Raspberry Pi

set -e  # Exit on any error

echo "=========================================="
echo "  Weasel Entertainment System Setup"
echo "=========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/5] Updating package lists..."
sudo apt-get update

echo ""
echo "[2/5] Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-pygame \
    python3-sdl2 \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    libportmidi-dev \
    libjpeg-dev \
    libpng-dev

echo ""
echo "[3/5] Installing Python packages..."
# Use --break-system-packages for Raspberry Pi OS Bookworm+ (Python 3.11+)
# This is safe here since we're installing to system Python intentionally
PIP_ARGS=""
if pip3 --version 2>/dev/null | grep -q "python 3.1[1-9]"; then
    PIP_ARGS="--break-system-packages"
fi
pip3 install --upgrade pip $PIP_ARGS
pip3 install pygame>=2.1.2 $PIP_ARGS

echo ""
echo "[4/5] Making scripts executable..."
chmod +x "$SCRIPT_DIR/setup_rpi.sh"
chmod +x "$SCRIPT_DIR/run_game.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/install_autostart.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/diagnose_controller.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/game_launcher.py"

echo ""
echo "[5/5] Testing pygame installation..."
python3 -c "import pygame; print(f'Pygame version: {pygame.version.ver}')"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To run the game manually:"
echo "  cd $SCRIPT_DIR"
echo "  python3 game_launcher.py"
echo ""
echo "If your controller doesn't work, run the diagnostic tool:"
echo "  python3 $SCRIPT_DIR/diagnose_controller.py"
echo ""
echo "To enable auto-start on boot, run:"
echo "  sudo $SCRIPT_DIR/install_autostart.sh"
echo ""
