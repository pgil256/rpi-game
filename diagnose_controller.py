#!/usr/bin/env python3
"""
Controller Diagnostic Tool for Weasel Entertainment System

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
CONFIG_FILE = os.path.join(SCRIPT_DIR, "controller_config.json")


def init_pygame():
    """Initialize pygame with minimal display for headless operation."""
    # Try to initialize with a dummy video driver for headless operation
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

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
            'index': i,
            'name': js.get_name(),
            'num_buttons': js.get_numbuttons(),
            'num_axes': js.get_numaxes(),
            'num_hats': js.get_numhats(),
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
                key = f'button_{b}'
                if last_state.get(key) != pressed:
                    last_state[key] = pressed
                    if pressed:
                        changes.append(f"Button {b}: PRESSED")

            # Check axes
            for a in range(js.get_numaxes()):
                value = js.get_axis(a)
                key = f'axis_{a}'
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
                key = f'hat_{h}'
                if last_state.get(key) != hat:
                    last_state[key] = hat
                    if hat != (0, 0):
                        dirs = []
                        if hat[0] < 0: dirs.append("LEFT")
                        if hat[0] > 0: dirs.append("RIGHT")
                        if hat[1] > 0: dirs.append("UP")
                        if hat[1] < 0: dirs.append("DOWN")
                        changes.append(f"Hat {h}: {'+'.join(dirs)}")

            # Print any changes
            for change in changes:
                print(f"  {change}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        print("Monitoring stopped.")


def map_controller(js_index=0):
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

    mapping = {
        'controller_name': js.get_name(),
        'buttons': {},
        'dpad_type': 'unknown',
        'dpad_axes': {'x': None, 'y': None},
    }

    buttons_to_map = [
        ('a', 'A button (primary action/confirm)'),
        ('b', 'B button (secondary/back)'),
        ('start', 'START button'),
        ('select', 'SELECT button'),
    ]

    try:
        # Map buttons
        for button_name, description in buttons_to_map:
            print(f"Press the {description}...")

            while True:
                pygame.event.pump()

                for b in range(js.get_numbuttons()):
                    if js.get_button(b):
                        mapping['buttons'][button_name] = b
                        print(f"  -> Mapped to button {b}")
                        # Wait for release
                        while js.get_button(b):
                            pygame.event.pump()
                            time.sleep(0.05)
                        time.sleep(0.3)
                        break
                else:
                    time.sleep(0.05)
                    continue
                break

        print()
        print("Now let's map the D-pad...")
        print()

        # Detect D-pad type
        print("Press LEFT on the D-pad...")

        dpad_detected = False
        while not dpad_detected:
            pygame.event.pump()

            # Check hats first
            for h in range(js.get_numhats()):
                hat = js.get_hat(h)
                if hat[0] < 0:  # Left pressed
                    mapping['dpad_type'] = 'hat'
                    mapping['dpad_hat'] = h
                    print(f"  -> D-pad uses Hat {h}")
                    dpad_detected = True
                    break

            if dpad_detected:
                break

            # Check axes
            for a in range(js.get_numaxes()):
                value = js.get_axis(a)
                if value < -0.5:
                    mapping['dpad_type'] = 'axes'
                    mapping['dpad_axes']['x'] = a
                    print(f"  -> D-pad X uses Axis {a}")
                    dpad_detected = True
                    break

            time.sleep(0.05)

        # If axes, also get Y axis
        if mapping['dpad_type'] == 'axes':
            # Wait for release
            time.sleep(0.5)
            print("Press UP on the D-pad...")

            while mapping['dpad_axes']['y'] is None:
                pygame.event.pump()

                for a in range(js.get_numaxes()):
                    if a == mapping['dpad_axes']['x']:
                        continue
                    value = js.get_axis(a)
                    if abs(value) > 0.5:
                        mapping['dpad_axes']['y'] = a
                        # Check if Y is inverted
                        mapping['dpad_y_inverted'] = value > 0  # Up should be negative normally
                        print(f"  -> D-pad Y uses Axis {a} (inverted: {mapping['dpad_y_inverted']})")
                        break

                time.sleep(0.05)

        print()
        print("Mapping complete!")
        print()

        return mapping

    except KeyboardInterrupt:
        print()
        print("Mapping cancelled.")
        return None


def save_config(mapping):
    """Save controller configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)
    print(f"Configuration saved to: {CONFIG_FILE}")


def load_config():
    """Load controller configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None


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
    for name, button_id in mapping['buttons'].items():
        print(f"  {name}: button {button_id}")
    print()
    print(f"D-pad Type: {mapping['dpad_type']}")
    if mapping['dpad_type'] == 'hat':
        print(f"  Hat index: {mapping.get('dpad_hat', 0)}")
    elif mapping['dpad_type'] == 'axes':
        print(f"  X axis: {mapping['dpad_axes']['x']}")
        print(f"  Y axis: {mapping['dpad_axes']['y']}")
        print(f"  Y inverted: {mapping.get('dpad_y_inverted', False)}")

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


def generate_input_manager_patch(mapping):
    """Generate code to patch input_manager.py with correct mappings."""
    print()
    print("=" * 60)
    print("  Manual Fix (if auto-config doesn't work)")
    print("=" * 60)
    print()
    print("Edit engine/input_manager.py and update these values:")
    print()
    print("DEFAULT_BUTTON_MAP = {")
    for name, button_id in mapping['buttons'].items():
        print(f"    '{name}': {button_id},")
    print("}")
    print()

    if mapping['dpad_type'] == 'axes':
        x_axis = mapping['dpad_axes']['x']
        y_axis = mapping['dpad_axes']['y']
        print(f"In _read_dpad_raw(), update axis numbers:")
        print(f"  X axis: {x_axis}")
        print(f"  Y axis: {y_axis}")
        if mapping.get('dpad_y_inverted'):
            print(f"  Note: Y axis may need to be inverted")


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

        if choice == '1':
            monitor_controller(js_index)
        elif choice == '2':
            mapping = map_controller(js_index)
            if mapping:
                save_config(mapping)
                apply_config_instructions(mapping)
                generate_input_manager_patch(mapping)
        elif choice == '3':
            config = load_config()
            if config:
                print()
                print("Current configuration:")
                print(json.dumps(config, indent=2))
            else:
                print()
                print("No configuration file found.")
                print("Use option [2] to create one.")
        elif choice == '4':
            break
        else:
            print("Invalid choice.")

    pygame.quit()
    return 0


if __name__ == '__main__':
    sys.exit(main())
