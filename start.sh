#!/usr/bin/env bash
# Single launch path. Let SDL select X11/Wayland/audio unless explicitly set.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo 'Missing .venv. Run ./setup_rpi.sh or python3 scripts/package.py install.' >&2
    exit 1
fi
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" && -z "${SDL_VIDEODRIVER:-}" ]]; then
    export SDL_VIDEODRIVER=kmsdrm
fi
# Prevent duplicate startup from old/manual entries without requiring root.
if command -v flock >/dev/null 2>&1; then
    LOCK_DIR="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}"
    exec 9>"$LOCK_DIR/wes-${UID}.lock"
    flock -n 9 || exit 0
fi
exec "$PYTHON" "$SCRIPT_DIR/game_launcher.py" "$@"
