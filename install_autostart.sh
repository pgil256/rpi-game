#!/usr/bin/env bash
# Choose ONE autostart backend: desktop (default) or console kiosk.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-desktop}"
RUN_USER="${SUDO_USER:-$(id -un)}"
if [[ "$RUN_USER" == root ]]; then
    echo 'Run from the intended non-root user account (sudo is allowed).' >&2
    exit 1
fi
if [[ "$MODE" != desktop && "$MODE" != console ]]; then
    echo 'Usage: ./install_autostart.sh [desktop|console]' >&2
    exit 1
fi
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
[[ -n "$RUN_HOME" && -d "$RUN_HOME" && -x "$SCRIPT_DIR/.venv/bin/python" ]] || {
    echo 'User home or .venv missing. Run setup_rpi.sh first.' >&2; exit 1;
}
# Render and validate before changing either startup backend.
PYTHON="$SCRIPT_DIR/.venv/bin/python"
CONFIG="$("$PYTHON" "$SCRIPT_DIR/scripts/autostart_config.py" "$MODE" "$SCRIPT_DIR" "$RUN_USER" "$RUN_HOME")"
chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/run_game.sh"
AUTOSTART_DIR="$RUN_HOME/.config/autostart"
# Install as the selected user, including newly-created parent directories.
sudo -u "$RUN_USER" mkdir -p "$AUTOSTART_DIR"
sudo rm -f -- "$AUTOSTART_DIR/wes.desktop" "$AUTOSTART_DIR/wes-game.desktop"
if [[ "$MODE" == desktop ]]; then
    if [[ -e /etc/systemd/system/wes-game.service ]]; then
        sudo systemctl disable --now wes-game.service
    fi
    printf '%s\n' "$CONFIG" | sudo -u "$RUN_USER" tee "$AUTOSTART_DIR/wes-game.desktop" >/dev/null
else
    GROUPS_TO_ADD=""
    for group in input video render; do
        if getent group "$group" >/dev/null; then
            GROUPS_TO_ADD="${GROUPS_TO_ADD:+$GROUPS_TO_ADD,}$group"
        fi
    done
    if [[ -n "$GROUPS_TO_ADD" ]]; then
        sudo usermod -a -G "$GROUPS_TO_ADD" "$RUN_USER"
    fi
    printf '%s\n' "$CONFIG" | sudo tee /etc/systemd/system/wes-game.service >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable wes-game.service
fi
printf 'Installed %s startup for %s. Console kiosk restarts after Quit; stop it with sudo systemctl stop wes-game.\n' "$MODE" "$RUN_USER"
