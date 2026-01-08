#!/bin/bash
# Weasel Entertainment System - Install Autostart on Boot
# This script configures the game to run automatically on boot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="wes-game"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=========================================="
echo "  Installing WES Autostart Service"
echo "=========================================="
echo ""

# Detect the current user (not root)
if [ "$SUDO_USER" ]; then
    RUN_USER="$SUDO_USER"
else
    RUN_USER="$(whoami)"
fi

# For Raspberry Pi, typically the user is 'pi'
if [ "$RUN_USER" = "root" ]; then
    RUN_USER="pi"
fi

echo "Game will run as user: $RUN_USER"
echo "Game directory: $SCRIPT_DIR"
echo ""

# Ensure user has access to input and video devices for kiosk mode
echo "Adding user to required groups for kiosk mode..."
sudo usermod -a -G input,video,render,tty "$RUN_USER" 2>/dev/null || true

# Create the systemd service file
echo "Creating systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Weasel Entertainment System Game Launcher
After=multi-user.target systemd-user-sessions.service
Conflicts=getty@tty1.service
Wants=graphical.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$SCRIPT_DIR
Environment="SDL_VIDEODRIVER=kmsdrm"
Environment="SDL_NOMOUSE=1"
# Required for kmsdrm access without X11
TTYPath=/dev/tty1
StandardInput=tty
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
ExecStart=/usr/bin/python3 $SCRIPT_DIR/game_launcher.py --fullscreen
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Alternative: Create an autostart desktop entry (for desktop environments)
AUTOSTART_DIR="/home/$RUN_USER/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/wes-game.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Weasel Entertainment System
Exec=$SCRIPT_DIR/run_game.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Launch WES game on startup
EOF

chown "$RUN_USER:$RUN_USER" "$AUTOSTART_DIR/wes-game.desktop"

# Enable and start the service
echo "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "=========================================="
echo "  Autostart Installation Complete!"
echo "=========================================="
echo ""
echo "The game will now start automatically on boot."
echo ""
echo "Useful commands:"
echo "  sudo systemctl start $SERVICE_NAME    # Start now"
echo "  sudo systemctl stop $SERVICE_NAME     # Stop the game"
echo "  sudo systemctl status $SERVICE_NAME   # Check status"
echo "  sudo systemctl disable $SERVICE_NAME  # Disable autostart"
echo ""
echo "To test immediately, reboot with:"
echo "  sudo reboot"
echo ""
