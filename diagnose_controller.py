#!/usr/bin/env python3
"""
Controller Diagnostic Tool for Winston Entertainment System

This script helps diagnose and fix controller issues on Raspberry Pi.
It will:
1. Detect connected controllers
2. Show real-time input from all buttons, axes, and hats
3. Guide you through mapping buttons
4. Generate a controller configuration file

Run this script on the Raspberry Pi to diagnose controller issues:
    python3 diagnose_controller.py
"""

import sys
import os
import json
import time

# Add the project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    import pygame
except ImportError:
    print("ERROR: pygame is not installed!")
    print("Run: pip3 install pygame")
    sys.exit(1)

# Configuration file path
from engine import InputManager
from engine.controller_mapping import (
    BUTTON_NAMES,
    button_conflict,
    controller_profile,
    save_profile,
    valid_bindings,
)
from engine.persistence import JsonStore, data_path

CONFIG_FILE = data_path("controller_config.json")


def init_pygame():
    """Initialize pygame with minimal display for headless operation."""
    # Try to initialize with a dummy video driver for headless operation
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    pygame.joystick.init()

    print("=" * 60)
    print("  Controller Diagnostic Tool")
    print("=" * 60)
    print()


def list_controllers():
    """List all connected controllers."""
    count = pygame.joystick.get_count()

    if count == 0:
        print("No controllers detected!")
        print()
        print("Troubleshooting tips:")
        print("  1. Make sure the controller is plugged in")
        print("  2. Try a different USB port")
        print("  3. Check if the controller is recognized by the system:")
        print("     ls /dev/input/js*")
        print("     cat /proc/bus/input/devices")
        print("  4. Some controllers need drivers. Try:")
        print("     sudo apt-get install joystick")
        print()
        return []

    controllers = []
    print(f"Found {count} controller(s):")
    print()

    for i in range(count):
        js = pygame.joystick.Joystick(i)
        js.init()

        info = {
            "index": i,
            "name": js.get_name(),
            "num_buttons": js.get_numbuttons(),
            "num_axes": js.get_numaxes(),
            "num_hats": js.get_numhats(),
        }
        controllers.append(info)

        print(f"  [{i}] {info['name']}")
        print(f"      Buttons: {info['num_buttons']}")
        print(f"      Axes: {info['num_axes']}")
        print(f"      Hats (D-pads): {info['num_hats']}")
        print()

    return controllers


def monitor_controller(js_index=0):
    """Monitor controller input in real-time."""
    js = pygame.joystick.Joystick(js_index)
    js.init()

    print()
    print("=" * 60)
    print(f"  Monitoring: {js.get_name()}")
    print("=" * 60)
    print()
    print("Press buttons and move the D-pad to see which inputs register.")
    print("Press Ctrl+C to stop monitoring.")
    print()

    last_state = {}

    try:
        while True:
            pygame.event.pump()

            changes = []

            # Check buttons
            for b in range(js.get_numbuttons()):
                pressed = js.get_button(b)
                key = f"button_{b}"
                if last_state.get(key) != pressed:
                    last_state[key] = pressed
                    if pressed:
                        changes.append(f"Button {b}: PRESSED")

            # Check axes
            for a in range(js.get_numaxes()):
                value = js.get_axis(a)
                key = f"axis_{a}"
                # Only report significant changes
                if abs(value) > 0.3 or (abs(last_state.get(key, 0)) > 0.3 and abs(value) < 0.1):
                    if last_state.get(key, 0) != round(value, 1):
                        last_state[key] = round(value, 1)
                        if abs(value) > 0.3:
                            direction = "+" if value > 0 else "-"
                            changes.append(f"Axis {a}: {direction}{abs(value):.2f}")

            # Check hats
            for h in range(js.get_numhats()):
                hat = js.get_hat(h)
                key = f"hat_{h}"
                if last_state.get(key) != hat:
                    last_state[key] = hat
                    if hat != (0, 0):
                        dirs = []
                        if hat[0] < 0:
                            dirs.append("LEFT")
                        if hat[0] > 0:
                            dirs.append("RIGHT")
                        if hat[1] > 0:
                            dirs.append("UP")
                        if hat[1] < 0:
                            dirs.append("DOWN")
                        changes.append(f"Hat {h}: {'+'.join(dirs)}")

            # Print any changes
            for change in changes:
                print(f"  {change}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        print("Monitoring stopped.")


def map_controller(js_index=0, names=BUTTON_NAMES):
    """Interactive controller mapping wizard."""
    js = pygame.joystick.Joystick(js_index)
    js.init()

    print()
    print("=" * 60)
    print("  Controller Mapping Wizard")
    print("=" * 60)
    print()
    print(f"Mapping: {js.get_name()}")
    print()
    print("Follow the prompts to map each button.")
    print("Press Ctrl+C to cancel at any time.")
    print()

    guid = js.get_guid()
    existing = controller_profile(load_config() or {}, guid)
    previous = existing.get("buttons", {})
    current = dict(InputManager.DEFAULT_BUTTON_MAP)
    if isinstance(previous, dict):
        current.update(previous)
    directions = existing.get("dpad_bindings", {})
    reserved = (
        {b["index"] for b in directions.values() if b["kind"] == "button"}
        if (existing.get("dpad_type") == "bindings" and valid_bindings(directions))
        else set()
    )
    captured = {}
    try:
        for name in names:
            while True:
                print(f"Release all buttons, then press {name.upper()}...")
                while any(js.get_button(i) for i in range(js.get_numbuttons())):
                    pygame.event.pump()
                    time.sleep(0.02)
                button = None
                while button is None:
                    pygame.event.pump()
                    button = next((i for i in range(js.get_numbuttons()) if js.get_button(i)), None)
                    time.sleep(0.02)
                error = button_conflict(name, button, current, names, captured, reserved)
                if error:
                    print(error)
                    continue
                captured[name] = button
                print(f"  {name.upper()} uses button {button}")
                break
        return {"controller_guid": guid, "controller_name": js.get_name(), "buttons": captured}

    except KeyboardInterrupt:
        print()
        print("Mapping cancelled.")
        return None


def save_config(mapping):
    """Save controller configuration to file."""
    if not save_profile(
        JsonStore(CONFIG_FILE, legacy_name="controller_config.json"),
        mapping["controller_guid"],
        mapping["controller_name"],
        {"buttons": mapping["buttons"]},
    ):
        print("Could not save controller mapping; check the WES data folder permissions.")
        return False
    print(f"Configuration saved to: {CONFIG_FILE}")
    return True


def load_config():
    """Load controller configuration from file."""
    return JsonStore(CONFIG_FILE, legacy_name="controller_config.json").load() or None


def apply_config_instructions(mapping):
    """Print instructions for applying the configuration."""
    print()
    print("=" * 60)
    print("  Configuration Summary")
    print("=" * 60)
    print()
    print(f"Controller: {mapping['controller_name']}")
    print()
    print("Button Mappings:")
    for name, button_id in mapping["buttons"].items():
        print(f"  {name}: button {button_id}")
    print()
    print("D-pad calibration is available in the launcher under Controller test.")

    print()
    print("=" * 60)
    print("  How to Apply This Configuration")
    print("=" * 60)
    print()
    print("The configuration has been saved. The game will automatically")
    print("load it on next startup.")
    print()
    print("To test, run:")
    print("  python3 game_launcher.py")
    print()


def main():
    init_pygame()

    controllers = list_controllers()

    if not controllers:
        pygame.quit()
        return 1

    # Use first controller
    js_index = 0

    while True:
        print()
        print("Options:")
        print("  [1] Monitor controller input (see raw values)")
        print("  [2] Map controller buttons (create configuration)")
        print("  [3] Test current configuration")
        print("  [4] Exit")
        print()

        try:
            choice = input("Enter choice [1-4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "1":
            monitor_controller(js_index)
        elif choice == "2":
            try:
                selected = input("Map A, B, Select, Start, or all four [all]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if selected not in ("", "all", *BUTTON_NAMES):
                print("Choose one button name or all.")
                continue
            names = (selected,) if selected in BUTTON_NAMES else BUTTON_NAMES
            mapping = map_controller(js_index, names)
            if mapping and save_config(mapping):
                apply_config_instructions(mapping)
        elif choice == "3":
            config = load_config()
            if config:
                print()
                print("Current configuration:")
                print(json.dumps(config, indent=2))
            else:
                print()
                print("No configuration file found.")
                print("Use option [2] to create one.")
        elif choice == "4":
            break
        else:
            print("Invalid choice.")

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
