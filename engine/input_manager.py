"""
Input Manager for Weasel Entertainment System

Consolidates all gamepad/keyboard input handling into a single class.
Provides edge detection, unified keyboard/gamepad interface, and configurable button mappings.
"""

import pygame
import os
import json


# Path to controller configuration file
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "controller_config.json")


def _load_controller_config():
    """Load controller configuration from file if it exists."""
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


class InputManager:
    """
    Unified input manager for keyboard and gamepad input.

    Provides:
    - Edge detection (was_pressed, was_released)
    - Unified keyboard/gamepad interface
    - Configurable button mappings
    - D-pad reading from hat, axes, or keyboard

    Usage:
        input_mgr = InputManager()

        # In game loop:
        input_mgr.update()

        if input_mgr.was_pressed('action'):
            # Handle action button press (only fires once per press)
            pass

        dx, dy = input_mgr.get_dpad()
    """

    # Default button mappings for USB Gamepad
    # Buttons 1=A, 2=B, 8=Select, 9=Start
    DEFAULT_BUTTON_MAP = {
        'a': 1,           # A button (confirm/action)
        'b': 2,           # B button (back/cancel)
        'select': 8,      # Select button
        'start': 9,       # Start button
    }

    # Default keyboard mappings
    DEFAULT_KEY_MAP = {
        'up': [pygame.K_UP, pygame.K_w],
        'down': [pygame.K_DOWN, pygame.K_s],
        'left': [pygame.K_LEFT, pygame.K_a],
        'right': [pygame.K_RIGHT, pygame.K_d],
        'action': [pygame.K_RETURN, pygame.K_SPACE],
        'back': [pygame.K_ESCAPE, pygame.K_BACKSPACE],
        'start': [pygame.K_RETURN],
        'select': [pygame.K_TAB],
        'pause': [pygame.K_p],
    }

    # Constants for USB Gamepad
    BUTTON_A = 1
    BUTTON_B = 2
    BUTTON_SELECT = 8
    BUTTON_START = 9
    DEADZONE = 0.3

    def __init__(self, button_map=None, key_map=None, deadzone=None):
        """
        Initialize the input manager.

        Args:
            button_map: Dictionary mapping logical names to gamepad button IDs.
                       Defaults to NES-style mapping.
            key_map: Dictionary mapping logical names to lists of keyboard keys.
                    Defaults to arrow keys + WASD.
            deadzone: Analog stick deadzone threshold (0.0 to 1.0).
                     Defaults to 0.3.
        """
        self.button_map = button_map or self.DEFAULT_BUTTON_MAP.copy()
        self.key_map = key_map or self.DEFAULT_KEY_MAP.copy()
        self.deadzone = deadzone if deadzone is not None else self.DEADZONE

        # D-pad configuration (can be overridden by config file)
        self.dpad_type = 'auto'  # 'auto', 'hat', or 'axes'
        self.dpad_hat = 0
        self.dpad_axes = {'x': None, 'y': None}
        self.dpad_y_inverted = False

        # Load configuration from file if it exists
        self._load_config()

        # Joystick reference
        self.joystick = None

        # State tracking for edge detection
        self._prev_buttons = {}  # Gamepad buttons: button_id -> bool
        self._prev_keys = {}     # Keyboard keys: key_code -> bool
        self._prev_dpad = (0, 0)

        # Current frame state
        self._curr_buttons = {}
        self._curr_keys = {}
        self._curr_dpad = (0, 0)

        # Initialize joystick
        self.init_joystick()

    def _load_config(self):
        """Load controller configuration from file."""
        config = _load_controller_config()
        if config:
            print(f"Loaded controller config: {config.get('controller_name', 'Unknown')}")

            # Apply button mappings
            if 'buttons' in config:
                for name, button_id in config['buttons'].items():
                    self.button_map[name] = button_id

            # Apply D-pad configuration
            if 'dpad_type' in config:
                self.dpad_type = config['dpad_type']
            if 'dpad_hat' in config:
                self.dpad_hat = config['dpad_hat']
            if 'dpad_axes' in config:
                self.dpad_axes = config['dpad_axes']
            if 'dpad_y_inverted' in config:
                self.dpad_y_inverted = config['dpad_y_inverted']

    def init_joystick(self):
        """
        Initialize or reinitialize the joystick.

        Returns:
            bool: True if a joystick was detected, False otherwise.
        """
        pygame.joystick.quit()
        pygame.joystick.init()

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Controller detected: {self.joystick.get_name()}")
            print(f"  Buttons: {self.joystick.get_numbuttons()}, "
                  f"Axes: {self.joystick.get_numaxes()}, "
                  f"Hats: {self.joystick.get_numhats()}")
            return True

        self.joystick = None
        print("No controller detected")
        return False

    def is_connected(self):
        """
        Check if any input device is connected.

        Returns:
            bool: True if joystick is connected (keyboard always available).
        """
        return self.joystick is not None

    def has_joystick(self):
        """
        Check if a joystick/gamepad is connected.

        Returns:
            bool: True if a joystick is connected.
        """
        return self.joystick is not None

    def update(self):
        """
        Update input state. Call this once per frame before checking inputs.

        This captures the current state of all inputs and moves the previous
        frame's state to the previous state buffer for edge detection.
        """
        # Move current state to previous
        self._prev_buttons = self._curr_buttons.copy()
        self._prev_keys = self._curr_keys.copy()
        self._prev_dpad = self._curr_dpad

        # Capture current gamepad button state
        self._curr_buttons = {}
        if self.joystick:
            try:
                num_buttons = self.joystick.get_numbuttons()
                for button_id in range(num_buttons):
                    self._curr_buttons[button_id] = self.joystick.get_button(button_id)
            except pygame.error:
                # Joystick became invalid (e.g., pygame reinitialized)
                self.joystick = None

        # Capture current keyboard state
        keys = pygame.key.get_pressed()
        self._curr_keys = {}
        for key_list in self.key_map.values():
            for key in key_list:
                self._curr_keys[key] = keys[key]

        # Capture current D-pad state
        self._curr_dpad = self._read_dpad_raw()

    def _read_dpad_raw(self):
        """
        Read raw D-pad state from gamepad and keyboard.

        Returns:
            tuple: (dx, dy) where -1=left/up, +1=right/down, 0=neutral
        """
        dx, dy = 0, 0

        # Check keyboard first
        keys = pygame.key.get_pressed()
        for key in self.key_map.get('left', []):
            if keys[key]:
                dx = -1
                break
        if dx == 0:
            for key in self.key_map.get('right', []):
                if keys[key]:
                    dx = 1
                    break

        for key in self.key_map.get('up', []):
            if keys[key]:
                dy = -1
                break
        if dy == 0:
            for key in self.key_map.get('down', []):
                if keys[key]:
                    dy = 1
                    break

        # Gamepad overrides keyboard if active
        if self.joystick:
            try:
                gp_dx, gp_dy = 0, 0

                # Use configured D-pad type, or auto-detect
                use_hat = False
                use_axes = False

                if self.dpad_type == 'hat':
                    use_hat = True
                elif self.dpad_type == 'axes':
                    use_axes = True
                else:  # 'auto' - try hat first, then axes
                    use_hat = self.joystick.get_numhats() > 0
                    use_axes = True  # Fallback

                # Method 1: Hat/POV
                if use_hat and self.joystick.get_numhats() > self.dpad_hat:
                    hat = self.joystick.get_hat(self.dpad_hat)
                    gp_dx = hat[0]
                    gp_dy = -hat[1]  # Hat Y is inverted

                # Method 2: Axes (if configured or as fallback)
                if (use_axes and gp_dx == 0 and gp_dy == 0):
                    num_axes = self.joystick.get_numaxes()

                    # Use configured axes if available
                    x_axis = self.dpad_axes.get('x')
                    y_axis = self.dpad_axes.get('y')

                    if x_axis is not None and x_axis < num_axes:
                        # Use configured X axis
                        ax = self.joystick.get_axis(x_axis)
                        if ax < -self.deadzone:
                            gp_dx = -1
                        elif ax > self.deadzone:
                            gp_dx = 1
                    elif num_axes >= 1:
                        # Fallback: try axis 0 for X
                        ax = self.joystick.get_axis(0)
                        if ax < -self.deadzone:
                            gp_dx = -1
                        elif ax > self.deadzone:
                            gp_dx = 1

                    if y_axis is not None and y_axis < num_axes:
                        # Use configured Y axis
                        ax = self.joystick.get_axis(y_axis)
                        if self.dpad_y_inverted:
                            ax = -ax
                        if ax < -self.deadzone:
                            gp_dy = -1
                        elif ax > self.deadzone:
                            gp_dy = 1
                    elif num_axes >= 2:
                        # Fallback: try axis 1 for Y
                        ax = self.joystick.get_axis(1)
                        if ax < -self.deadzone:
                            gp_dy = -1
                        elif ax > self.deadzone:
                            gp_dy = 1

                # Gamepad overrides keyboard if gamepad has input
                if gp_dx != 0:
                    dx = gp_dx
                if gp_dy != 0:
                    dy = gp_dy
            except pygame.error:
                # Joystick became invalid
                self.joystick = None

        return (dx, dy)

    def get_dpad(self):
        """
        Get current D-pad direction.

        Returns:
            tuple: (dx, dy) where -1=left/up, +1=right/down, 0=neutral
        """
        return self._curr_dpad

    def dpad_changed(self):
        """
        Check if D-pad state changed since last frame.

        Returns:
            bool: True if D-pad state is different from previous frame.
        """
        return self._curr_dpad != self._prev_dpad

    def get_button(self, button_id):
        """
        Check if a specific gamepad button is currently pressed.

        Args:
            button_id: The button ID to check (0-based index).

        Returns:
            bool: True if the button is pressed, False otherwise.
        """
        if self.joystick and button_id < self.joystick.get_numbuttons():
            return self.joystick.get_button(button_id)
        return False

    def is_pressed(self, name):
        """
        Check if a logical button/key is currently pressed.

        Args:
            name: Logical name ('action', 'back', 'a', 'b', 'start', 'select',
                  'up', 'down', 'left', 'right')

        Returns:
            bool: True if any mapped key/button for this name is pressed.
        """
        # Check keyboard keys
        if name in self.key_map:
            for key in self.key_map[name]:
                if self._curr_keys.get(key, False):
                    return True

        # Check gamepad buttons
        if name in self.button_map:
            button_id = self.button_map[name]
            if self._curr_buttons.get(button_id, False):
                return True

        return False

    def was_pressed(self, name):
        """
        Check if a logical button/key was just pressed this frame (edge detection).

        Args:
            name: Logical name ('action', 'back', 'a', 'b', 'start', 'select')

        Returns:
            bool: True if the button was pressed this frame but not last frame.
        """
        curr = False
        prev = False

        # Check keyboard keys
        if name in self.key_map:
            for key in self.key_map[name]:
                if self._curr_keys.get(key, False):
                    curr = True
                if self._prev_keys.get(key, False):
                    prev = True

        # Check gamepad buttons
        if name in self.button_map:
            button_id = self.button_map[name]
            if self._curr_buttons.get(button_id, False):
                curr = True
            if self._prev_buttons.get(button_id, False):
                prev = True

        return curr and not prev

    def was_released(self, name):
        """
        Check if a logical button/key was just released this frame (edge detection).

        Args:
            name: Logical name ('action', 'back', 'a', 'b', 'start', 'select')

        Returns:
            bool: True if the button was released this frame (was pressed, now isn't).
        """
        curr = False
        prev = False

        # Check keyboard keys
        if name in self.key_map:
            for key in self.key_map[name]:
                if self._curr_keys.get(key, False):
                    curr = True
                if self._prev_keys.get(key, False):
                    prev = True

        # Check gamepad buttons
        if name in self.button_map:
            button_id = self.button_map[name]
            if self._curr_buttons.get(button_id, False):
                curr = True
            if self._prev_buttons.get(button_id, False):
                prev = True

        return prev and not curr

    def get_any_action_button(self):
        """
        Check if any action button is pressed (A, Start, or common action buttons).
        Maintains compatibility with existing game_launcher.py function.

        Returns:
            bool: True if any action button is pressed.
        """
        # Check keyboard
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN] or keys[pygame.K_SPACE]:
            return True

        # Check gamepad
        if not self.joystick:
            return False

        num_buttons = self.joystick.get_numbuttons()
        # Check buttons 0, 1, A, Start (common action buttons)
        for b in [0, 1, self.BUTTON_A, self.BUTTON_START]:
            if b < num_buttons and self.joystick.get_button(b):
                return True

        return False

    def get_any_back_button(self):
        """
        Check if any back button is pressed (B, Select, or ESC).
        Maintains compatibility with existing game_launcher.py function.

        Returns:
            bool: True if any back button is pressed.
        """
        # Check keyboard
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] or keys[pygame.K_BACKSPACE]:
            return True

        # Check gamepad
        if not self.joystick:
            return False

        num_buttons = self.joystick.get_numbuttons()
        for b in [self.BUTTON_B, self.BUTTON_SELECT]:
            if b < num_buttons and self.joystick.get_button(b):
                return True

        return False

    def action_pressed(self):
        """
        Check if action button was just pressed (edge detected).
        Convenience method combining get_any_action_button with edge detection.

        Returns:
            bool: True if action button was pressed this frame.
        """
        return self.was_pressed('action') or self.was_pressed('a') or self.was_pressed('start')

    def back_pressed(self):
        """
        Check if back button was just pressed (edge detected).
        Convenience method combining get_any_back_button with edge detection.

        Returns:
            bool: True if back button was pressed this frame.
        """
        return self.was_pressed('back') or self.was_pressed('b') or self.was_pressed('select')

    def pause_pressed(self):
        """
        Check if pause button was just pressed (edge detected).
        P key or Start button toggles pause.

        Returns:
            bool: True if pause button was pressed this frame.
        """
        return self.was_pressed('pause') or self.was_pressed('start')

    def set_button_mapping(self, name, button_id):
        """
        Configure a button mapping.

        Args:
            name: Logical name for the button (e.g., 'action', 'a', 'b')
            button_id: Gamepad button ID to map to this name
        """
        self.button_map[name] = button_id

    def set_key_mapping(self, name, keys):
        """
        Configure a key mapping.

        Args:
            name: Logical name for the key(s)
            keys: Single pygame key constant or list of key constants
        """
        if isinstance(keys, int):
            keys = [keys]
        self.key_map[name] = keys

    def get_controller_info(self):
        """
        Get information about the connected controller.

        Returns:
            dict: Controller information, or None if no controller connected.
        """
        if not self.joystick:
            return None

        return {
            'name': self.joystick.get_name(),
            'num_buttons': self.joystick.get_numbuttons(),
            'num_axes': self.joystick.get_numaxes(),
            'num_hats': self.joystick.get_numhats(),
        }


# Module-level convenience functions for backwards compatibility
_default_manager = None


def get_input_manager():
    """
    Get or create the default InputManager instance.

    Returns:
        InputManager: The default input manager.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = InputManager()
    return _default_manager


def init_joystick():
    """Backwards compatible init_joystick function."""
    return get_input_manager().init_joystick()


def get_dpad():
    """Backwards compatible get_dpad function."""
    global _default_manager
    try:
        mgr = get_input_manager()
        mgr.update()  # Ensure state is current
        return mgr.get_dpad()
    except pygame.error:
        # Pygame was reinitialized, reset the manager
        _default_manager = None
        mgr = get_input_manager()
        mgr.update()
        return mgr.get_dpad()


def get_button(button_id):
    """Backwards compatible get_button function."""
    return get_input_manager().get_button(button_id)


def get_any_action_button():
    """Backwards compatible get_any_action_button function."""
    return get_input_manager().get_any_action_button()


def get_any_back_button():
    """Backwards compatible get_any_back_button function."""
    return get_input_manager().get_any_back_button()
