"""Render autostart files without treating paths as shell/unit syntax.

Quoting follows the freedesktop Desktop Entry Exec and systemd.service rules.
This helper only prints configuration; install_autostart.sh selects its owner
and destination.
"""

import argparse
from pathlib import Path


def _single_line(value):
    value = str(value)
    if any(char in value for char in ("\n", "\r", "\0")):
        raise ValueError("Autostart paths must not contain line breaks or NULs")
    return value


def desktop_quote(value):
    # Exec has two escaping passes: string-value decoding, then argument parsing.
    value = _single_line(value).replace("%", "%%")
    value = "".join("\\" + char if char in ("\\", '"', "$", "`") else char for char in value)
    return '"' + value.replace("\\", "\\\\") + '"'


def unit_quote(value, *, command=False):
    value = _single_line(value).replace("%", "%%")
    if command:
        value = value.replace("$", "$$")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_desktop(directory):
    command = desktop_quote(Path(directory) / "run_game.sh")
    return (
        "[Desktop Entry]\nType=Application\nName=Winston Entertainment System\n"
        f"Exec=/bin/bash {command}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n"
    )


def render_service(directory, user, home):
    user = _single_line(user)
    if not user or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for char in user
    ):
        raise ValueError("Unsupported service user name")
    working_directory = unit_quote(directory)
    command = unit_quote(Path(directory) / "run_game.sh", command=True)
    environment = unit_quote("HOME=" + str(home))
    return f"""[Unit]
Description=Winston Entertainment System console kiosk
After=systemd-user-sessions.service getty@tty1.service
Conflicts=getty@tty1.service
[Service]
Type=simple
User={user}
WorkingDirectory={working_directory}
Environment=SDL_VIDEODRIVER=kmsdrm
Environment={environment}
TTYPath=/dev/tty1
StandardInput=tty
TTYReset=yes
TTYVHangup=yes
ExecStart=/bin/bash {command}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("desktop", "console"))
    parser.add_argument("directory")
    parser.add_argument("user")
    parser.add_argument("home")
    args = parser.parse_args()
    try:
        text = (
            render_desktop(args.directory)
            if args.mode == "desktop"
            else render_service(args.directory, args.user, args.home)
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(text, end="")


if __name__ == "__main__":
    main()
