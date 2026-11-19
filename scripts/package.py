#!/usr/bin/env python3
"""Build tools for Winston Entertainment System.

Usage: python scripts/package.py [install|build|clean|rpi-setup]
Dependencies are installed only in .venv; rpi-setup selects desktop autostart.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(cmd, cwd=None):
    """Run a command without a shell and report errors to the caller."""
    print(f"Running: {' '.join(map(str, cmd))}")
    try:
        return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=False).returncode == 0
    except OSError as exc:
        print(f"Could not start command: {exc}")
        return False


def venv_python():
    relative = ("Scripts", "python.exe") if sys.platform == "win32" else ("bin", "python")
    return PROJECT_ROOT.joinpath(".venv", *relative)


def make_launchers_executable():
    if sys.platform != "win32":
        for name in ("start.sh", "run_game.sh", "setup_rpi.sh", "install_autostart.sh"):
            path = PROJECT_ROOT / name
            path.chmod(path.stat().st_mode | 0o111)


def install():
    """Create or repair the venv and install the pinned runtime requirements."""
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.")
        return False
    if not venv_python().is_file():
        if not run_command([sys.executable, "-m", "venv", str(PROJECT_ROOT / ".venv")]):
            return False
    # Use the interpreter to avoid pip self-upgrade errors on Windows.
    if not run_command(
        [str(venv_python()), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")]
    ):
        return False
    try:
        make_launchers_executable()
    except OSError as exc:
        print(f"Cannot make launch scripts executable: {exc}")
        return False
    print(
        "Installation complete. Run .venv Python with game_launcher.py, or ./run_game.sh on Linux."
    )
    return True


def build():
    """Build an onedir bundle with the current platform's Python."""
    if not venv_python().is_file() and not install():
        return False
    python = str(venv_python())
    if not run_command([python, "-m", "pip", "install", "pyinstaller==6.19.0"]):
        return False
    if not run_command([python, "-m", "PyInstaller", str(PROJECT_ROOT / "wes.spec")]):
        return False
    filename = "wes.exe" if sys.platform == "win32" else "wes"
    print(f"Build complete: {PROJECT_ROOT / 'dist' / 'wes' / filename}")
    return True


def _remove_artifact(path):
    root = PROJECT_ROOT.resolve()
    path = Path(path)
    # Unlink a local symlink itself, never recursively remove its destination.
    if path.is_symlink():
        if not path.parent.resolve().is_relative_to(root):
            raise ValueError(f"Refusing to remove an external link: {path}")
        path.unlink()
        return
    resolved = path.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(f"Refusing to remove a path outside the project: {resolved}")
    if path.is_dir():
        shutil.rmtree(path)


def clean():
    """Clean project build output without traversing dependency or archive trees."""
    try:
        for name in ("build", "dist", "__pycache__"):
            _remove_artifact(PROJECT_ROOT / name)
        root = PROJECT_ROOT.resolve()
        for name in ("engine", "games", "scripts", "tests"):
            directory = PROJECT_ROOT / name
            if not directory.is_dir() or not directory.resolve().is_relative_to(root):
                continue
            for parent, dirs, _ in os.walk(directory, followlinks=False):
                dirs[:] = [
                    name
                    for name in dirs
                    if name not in (".venv", "legacy_reference", ".git")
                    and not (Path(parent) / name).is_symlink()
                    and (Path(parent) / name).resolve().is_relative_to(root)
                ]
                if "__pycache__" in dirs:
                    _remove_artifact(Path(parent) / "__pycache__")
                    dirs.remove("__pycache__")
    except (OSError, ValueError) as exc:
        print(f"Clean failed: {exc}")
        return False
    print("Clean complete.")
    return True


def rpi_setup():
    """Use the single autostart installer after preparing executable launchers."""
    if not sys.platform.startswith("linux"):
        print("This command requires Linux/Raspberry Pi OS.")
        return False
    if not install():
        return False
    return run_command(["bash", str(PROJECT_ROOT / "install_autostart.sh"), "desktop"])


def main():
    commands = {"install": install, "build": build, "clean": clean, "rpi-setup": rpi_setup}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(__doc__)
        return 1
    return 0 if commands[sys.argv[1]]() else 1


if __name__ == "__main__":
    raise SystemExit(main())
