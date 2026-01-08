#!/usr/bin/env python3
"""
Packaging script for Weasel Entertainment System.

Usage:
    python scripts/package.py [command]

Commands:
    install     Set up virtual environment and install dependencies
    build       Build standalone executable using PyInstaller
    clean       Remove build artifacts
    rpi-setup   Set up for Raspberry Pi auto-start
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT)
    return result.returncode == 0


def install():
    """Set up virtual environment and install dependencies."""
    venv_path = PROJECT_ROOT / '.venv'

    # Create venv if it doesn't exist
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command([sys.executable, '-m', 'venv', str(venv_path)]):
            print("Failed to create virtual environment")
            return False

    # Determine pip path
    if sys.platform == 'win32':
        pip_path = venv_path / 'Scripts' / 'pip'
    else:
        pip_path = venv_path / 'bin' / 'pip'

    # Upgrade pip
    print("Upgrading pip...")
    run_command([str(pip_path), 'install', '--upgrade', 'pip'])

    # Install requirements
    print("Installing dependencies...")
    req_file = PROJECT_ROOT / 'requirements.txt'
    if not run_command([str(pip_path), 'install', '-r', str(req_file)]):
        print("Failed to install dependencies")
        return False

    print("\nInstallation complete!")
    print(f"Activate the virtual environment with:")
    if sys.platform == 'win32':
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print(f"  source {venv_path}/bin/activate")
    print(f"\nThen run: python game_launcher.py")
    return True


def build():
    """Build standalone executable using PyInstaller."""
    venv_path = PROJECT_ROOT / '.venv'

    # Determine python/pip paths
    if sys.platform == 'win32':
        pip_path = venv_path / 'Scripts' / 'pip'
        python_path = venv_path / 'Scripts' / 'python'
    else:
        pip_path = venv_path / 'bin' / 'pip'
        python_path = venv_path / 'bin' / 'python'

    # Ensure venv exists
    if not venv_path.exists():
        print("Virtual environment not found. Running install first...")
        if not install():
            return False

    # Install PyInstaller
    print("Installing PyInstaller...")
    if not run_command([str(pip_path), 'install', 'pyinstaller']):
        print("Failed to install PyInstaller")
        return False

    # Build with PyInstaller
    print("Building executable...")
    spec_file = PROJECT_ROOT / 'wes.spec'
    if not run_command([str(python_path), '-m', 'PyInstaller', str(spec_file)]):
        print("Build failed")
        return False

    print("\nBuild complete!")
    dist_path = PROJECT_ROOT / 'dist' / 'wes'
    print(f"Executable located at: {dist_path}")
    return True


def clean():
    """Remove build artifacts."""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.pyc', '*.pyo', '*.spec.bak']

    for dir_name in dirs_to_remove:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            print(f"Removing {dir_path}...")
            shutil.rmtree(dir_path)

    # Clean __pycache__ in subdirectories
    for pycache in PROJECT_ROOT.rglob('__pycache__'):
        print(f"Removing {pycache}...")
        shutil.rmtree(pycache)

    print("Clean complete!")
    return True


def rpi_setup():
    """Set up for Raspberry Pi auto-start."""
    if sys.platform == 'win32':
        print("This command is only for Linux/Raspberry Pi")
        return False

    # First run install
    if not install():
        return False

    # Create desktop entry
    desktop_entry = """[Desktop Entry]
Type=Application
Name=Weasel Entertainment System
Comment=Classic arcade games with weasel theming
Exec={script_path}
Icon={icon_path}
Terminal=false
Categories=Game;
X-GNOME-Autostart-enabled=true
"""

    script_path = PROJECT_ROOT / 'start.sh'
    icon_path = PROJECT_ROOT / 'media' / 'weasel.png'

    entry_content = desktop_entry.format(
        script_path=script_path,
        icon_path=icon_path
    )

    # Write to autostart directory
    autostart_dir = Path.home() / '.config' / 'autostart'
    autostart_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = autostart_dir / 'wes.desktop'
    desktop_file.write_text(entry_content)
    print(f"Created autostart entry: {desktop_file}")

    # Make start.sh executable
    run_command(['chmod', '+x', str(script_path)])

    print("\nRaspberry Pi setup complete!")
    print("The game will start automatically on login.")
    print(f"To start manually: {script_path}")
    return True


def main():
    commands = {
        'install': install,
        'build': build,
        'clean': clean,
        'rpi-setup': rpi_setup,
    }

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands:", ', '.join(commands.keys()))
        return 1

    cmd = sys.argv[1]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print("Available commands:", ', '.join(commands.keys()))
        return 1

    success = commands[cmd]()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
