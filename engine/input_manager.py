"""
Input Manager for Winston Entertainment System

Consolidates all gamepad/keyboard input handling into a single class.
Provides edge detection, unified keyboard/gamepad interface, and configurable button mappings.
"""

import pygame
from collections import deque
from engine.persistence import JsonStore, data_path
from engine.controller_mapping import (
    BUTTON_NAMES,
    controller_profile,
    save_profile,
    decode_bindings,
    valid_bindings,
)
from engine import BUTTON_A, BUTTON_B, BUTTON_SELECT, BUTTON_START, DEADZONE


def _controller_store():
    return JsonStore(data_path("controller_config.json"), legacy_name="controller_config.json")


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
        "a": BUTTON_A,  # A button (confirm/action)
        "b": BUTTON_B,  # B button (back/cancel)
        "select": BUTTON_SELECT,  # Select button
        "start": BUTTON_START,  # Start button
    }

    # Default keyboard mappings
    DEFAULT_KEY_MAP = {
        "up": [pygame.K_UP, pygame.K_w],
        "down": [pygame.K_DOWN, pygame.K_s],
        "left": [pygame.K_LEFT, pygame.K_a],
        "right": [pygame.K_RIGHT, pygame.K_d],
        "action": [pygame.K_RETURN, pygame.K_SPACE],
        "back": [pygame.K_ESCAPE, pygame.K_BACKSPACE],
        "start": [],
        "select": [pygame.K_TAB],
        "pause": [pygame.K_p],
    }

    # Constants for USB Gamepad
    BUTTON_A = BUTTON_A
    BUTTON_B = BUTTON_B
    BUTTON_SELECT = BUTTON_SELECT
    BUTTON_START = BUTTON_START
    DEADZONE = DEADZONE

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
        self.button_map = self.DEFAULT_BUTTON_MAP.copy()
        if button_map:
            self.button_map.update(button_map)
        self._base_button_map = self.button_map.copy()
        self.key_map = key_map or self.DEFAULT_KEY_MAP.copy()
        self.deadzone = deadzone if deadzone is not None else self.DEADZONE

        # D-pad configuration (can be overridden by config file)
        self._load_config()

        # Joystick reference
        self.joystick = None

        # State tracking for edge detection
        self._prev_buttons = {}  # Gamepad buttons: button_id -> bool
        self._prev_keys = {}  # Keyboard keys: key_code -> bool
        self._prev_dpad = (0, 0)

        # Current frame state
        self._curr_buttons = {}
        self._curr_keys = {}
        self._curr_dpad = (0, 0)

        self._menu_direction = (0, 0)
        self._menu_next_repeat = 0
        self._next_joystick_check = 0
        # SDL may deliver a complete tap between simulation steps. Keep the
        # events until update consumes them, independent of final held state.
        self._pending_key_presses = set()
        self._pending_key_releases = set()
        self._pending_button_presses = set()
        self._pending_button_releases = set()
        self._event_pressed_keys = set()
        self._event_released_keys = set()
        self._event_pressed_buttons = set()
        self._event_released_buttons = set()
        self._pending_directions = deque(maxlen=16)
        self._direction_keys = set()
        self._event_hats = {}
        self._event_axes = {}
        self._event_pad_buttons = {}
        self._suppressed_keys = set()

        # Initialize joystick
        self.init_joystick()

    def _load_config(self, guid=None):
        """Select this device's bindings, with defaults for a new controller."""
        self.button_map = self._base_button_map.copy()
        self.dpad_type = "auto"
        self.dpad_hat = 0
        self.dpad_axes = {"x": None, "y": None}
        self.dpad_y_inverted = False
        self.dpad_bindings = None
        self._profile_guid = None
        config = controller_profile(_controller_store().load(), guid)
        if config:
            print(f"Loaded controller config: {config.get('controller_name', 'Unknown')}")

            # Apply button mappings
            if isinstance(config.get("buttons"), dict):
                for name, button_id in config["buttons"].items():
                    if isinstance(button_id, int) and button_id >= 0:
                        self.button_map[name] = button_id

            # Apply D-pad configuration
            if config.get("dpad_type") in ("auto", "hat", "axes", "bindings"):
                self.dpad_type = config["dpad_type"]
            if isinstance(config.get("dpad_hat"), int) and config["dpad_hat"] >= 0:
                self.dpad_hat = config["dpad_hat"]
            if isinstance(config.get("dpad_axes"), dict):
                self.dpad_axes = {
                    key: value if isinstance(value, int) and value >= 0 else None
                    for key, value in config["dpad_axes"].items()
                }
            if isinstance(config.get("dpad_y_inverted"), bool):
                self.dpad_y_inverted = config["dpad_y_inverted"]
            self._profile_guid = config.get("controller_guid")
            if valid_bindings(config.get("dpad_bindings")):
                self.dpad_bindings = config["dpad_bindings"]
            elif self.dpad_type == "bindings":
                self.dpad_type = "auto"

    def init_joystick(self):
        """
        Initialize or reinitialize the joystick.

        Returns:
            bool: True if a joystick was detected, False otherwise.
        """
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self._load_config(self.joystick.get_guid())
            self._seed_gamepad_events()
            print(f"Controller detected: {self.joystick.get_name()}")
            print(
                f"  Buttons: {self.joystick.get_numbuttons()}, "
                f"Axes: {self.joystick.get_numaxes()}, "
                f"Hats: {self.joystick.get_numhats()}"
            )
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
        if self.joystick is None and pygame.time.get_ticks() >= self._next_joystick_check:
            self._next_joystick_check = pygame.time.get_ticks() + 500
            self.init_joystick()
        # Move current state to previous
        self._prev_buttons = self._curr_buttons.copy()
        self._prev_keys = self._curr_keys.copy()
        self._prev_dpad = self._curr_dpad
        self._event_pressed_keys, self._pending_key_presses = self._pending_key_presses, set()
        self._event_released_keys, self._pending_key_releases = self._pending_key_releases, set()
        self._event_pressed_buttons, self._pending_button_presses = (
            self._pending_button_presses,
            set(),
        )
        self._event_released_buttons, self._pending_button_releases = (
            self._pending_button_releases,
            set(),
        )

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
        # One-step pulses also let held-action consumers (automatic firing)
        # respond once to a short tap, without sticking after release.
        for button in self._event_pressed_buttons:
            self._curr_buttons[button] = True
        for button in self._dpad_button_ids():
            self._curr_buttons.pop(button, None)

        # Capture current keyboard state
        keys = pygame.key.get_pressed()
        self._suppressed_keys = {key for key in self._suppressed_keys if keys[key]}
        self._curr_keys = {}
        for key_list in self.key_map.values():
            for key in key_list:
                self._curr_keys[key] = keys[key] and key not in self._suppressed_keys
        self._direction_keys = {key for key, held in self._curr_keys.items() if held}
        for key in self._event_pressed_keys:
            self._curr_keys[key] = True

        # Capture current D-pad state
        self._curr_dpad = self._read_dpad_raw()
        if self._pending_directions:
            self._curr_dpad = self._pending_directions.popleft()

    def _read_dpad_raw(self):
        """
        Read raw D-pad state from gamepad and keyboard.

        Returns:
            tuple: (dx, dy) where -1=left/up, +1=right/down, 0=neutral
        """
        dx, dy = 0, 0

        # Check keyboard first
        keys = pygame.key.get_pressed()
        for key in self.key_map.get("left", []):
            if keys[key]:
                dx = -1
                break
        if dx == 0:
            for key in self.key_map.get("right", []):
                if keys[key]:
                    dx = 1
                    break

        for key in self.key_map.get("up", []):
            if keys[key]:
                dy = -1
                break
        if dy == 0:
            for key in self.key_map.get("down", []):
                if keys[key]:
                    dy = 1
                    break

        snapshot = self.raw_controller_state()
        if snapshot is not None:
            gx, gy = self._decode_gamepad(
                dict(enumerate(snapshot["axes"])),
                dict(enumerate(snapshot["hats"])),
                dict(enumerate(snapshot["buttons"])),
            )
            dx, dy = gx or dx, gy or dy

        return (dx, dy)

    def raw_controller_state(self):
        """Actual hardware values for the controller test and guided calibration."""
        if self.joystick is None:
            return None
        try:
            return {
                "axes": [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())],
                "hats": [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())],
                "buttons": [
                    bool(self.joystick.get_button(i)) for i in range(self.joystick.get_numbuttons())
                ],
            }
        except pygame.error:
            self.joystick = None
            return None

    def _seed_gamepad_events(self):
        snapshot = self.raw_controller_state()
        if snapshot is not None:
            self._event_axes = dict(enumerate(snapshot["axes"]))
            self._event_hats = dict(enumerate(snapshot["hats"]))
            self._event_pad_buttons = dict(enumerate(snapshot["buttons"]))

    def _decode_gamepad(self, axes, hats, buttons):
        # Polling and event buffering must interpret the same physical controls.
        mode = self.dpad_type
        other_controller = False
        if mode == "bindings" and self.dpad_bindings is not None:
            if not self._profile_guid or self._profile_guid == self.joystick.get_guid():
                return decode_bindings(self.dpad_bindings, axes, hats, buttons)
            mode = "auto"  # A different controller must not inherit this calibration.
            other_controller = True
        hat_index = 0 if other_controller else self.dpad_hat
        if mode == "hat" or (mode == "auto" and hat_index in hats):
            hx, hy = hats.get(hat_index, (0, 0))
            return hx, -hy
        x_index = 0 if other_controller else self.dpad_axes.get("x")
        y_index = 1 if other_controller else self.dpad_axes.get("y")
        x = axes.get(0 if x_index is None else x_index, 0)
        y = axes.get(1 if y_index is None else y_index, 0)
        if self.dpad_y_inverted and not other_controller:
            y = -y

        def digital(value):
            return -1 if value < -self.deadzone else 1 if value > self.deadzone else 0

        return digital(x), digital(y)

    def _dpad_button_ids(self):
        """Calibrated D-pad buttons must not also confirm, pause, or leave a game."""
        if (
            self.joystick is not None
            and self.dpad_type == "bindings"
            and self.dpad_bindings is not None
            and (not self._profile_guid or self._profile_guid == self.joystick.get_guid())
        ):
            return {
                binding["index"]
                for binding in self.dpad_bindings.values()
                if binding["kind"] == "button"
            }
        return set()

    def save_dpad_calibration(self, bindings):
        if self.joystick is None or not valid_bindings(bindings):
            return False
        guid = self.joystick.get_guid()
        if not save_profile(
            _controller_store(),
            guid,
            self.joystick.get_name(),
            {"dpad_type": "bindings", "dpad_bindings": bindings},
        ):
            return False
        self.dpad_bindings = bindings
        self.dpad_type = "bindings"
        self._profile_guid = guid
        self._pending_directions.clear()
        self._curr_dpad = self._prev_dpad = (0, 0)
        self.reset_repeat()
        self._seed_gamepad_events()
        return True

    def save_button_mapping(self, buttons):
        if self.joystick is None or not buttons:
            return False
        reserved = self._dpad_button_ids()
        limit = self.joystick.get_numbuttons()
        for name, number in buttons.items():
            if (
                name not in BUTTON_NAMES
                or type(number) is not int
                or not 0 <= number < limit
                or number in reserved
            ):
                return False
        updated = {**self.button_map, **buttons}
        if any(
            sum(value == number for value in updated.values()) > 1 for number in buttons.values()
        ):
            return False
        if not save_profile(
            _controller_store(),
            self.joystick.get_guid(),
            self.joystick.get_name(),
            {"buttons": buttons},
        ):
            return False
        self.button_map = updated
        return True

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
        return bool(self._curr_buttons.get(button_id, False))

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
        if any(key in self._event_pressed_keys for key in self.key_map.get(name, ())):
            return True
        if self.button_map.get(name) in self._event_pressed_buttons:
            return True
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
        if any(key in self._event_released_keys for key in self.key_map.get(name, ())):
            return True
        if self.button_map.get(name) in self._event_released_buttons:
            return True
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
        return self.is_pressed("action") or self.is_pressed("a")

    def get_any_back_button(self):
        return self.is_pressed("back") or self.is_pressed("b") or self.is_pressed("select")

    def confirm_pressed(self):
        """Menu confirmation includes Start; in-game action deliberately does not."""
        return self.action_pressed() or self.was_pressed("start")

    def menu_direction(self, now_ms=None, initial_delay=250, repeat_delay=120):
        """One direction per tap, then controlled repeats while held."""
        now = pygame.time.get_ticks() if now_ms is None else now_ms
        direction = self.get_dpad()
        # Resolve diagonals to one axis, avoiding phantom two-axis tile moves.
        if direction[1]:
            direction = (0, direction[1])
        if direction != self._menu_direction:
            self._menu_direction = direction
            self._menu_next_repeat = now + initial_delay
            return direction
        if direction != (0, 0) and now >= self._menu_next_repeat:
            self._menu_next_repeat = now + repeat_delay
            return direction
        return (0, 0)

    def reset_repeat(self):
        self._menu_direction = self.get_dpad()
        self._menu_next_repeat = pygame.time.get_ticks() + 250

    def handle_event(self, event):
        """Forward SDL events before update so short taps and hot-plug survive."""
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            if event.key in self._suppressed_keys:
                if event.type == pygame.KEYUP:
                    self._suppressed_keys.discard(event.key)
                return
            pressed = event.type == pygame.KEYDOWN
            if pressed and getattr(event, "repeat", False):
                return
            pending = self._pending_key_presses if pressed else self._pending_key_releases
            pending.add(event.key)
            if pressed:
                self._direction_keys.add(event.key)
            else:
                self._direction_keys.discard(event.key)
            if any(
                event.key in self.key_map.get(name, ()) for name in ("up", "down", "left", "right")
            ):
                self._queue_event_direction()
            return
        if event.type in (
            pygame.JOYBUTTONDOWN,
            pygame.JOYBUTTONUP,
            pygame.JOYHATMOTION,
            pygame.JOYAXISMOTION,
        ):
            if self.joystick is None:
                return
            try:
                if (
                    hasattr(event, "instance_id")
                    and event.instance_id != self.joystick.get_instance_id()
                ):
                    return
            except pygame.error:
                return
            if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
                pending = (
                    self._pending_button_presses
                    if event.type == pygame.JOYBUTTONDOWN
                    else self._pending_button_releases
                )
                if event.button not in self._dpad_button_ids():
                    pending.add(event.button)
                self._event_pad_buttons[event.button] = event.type == pygame.JOYBUTTONDOWN
                if self.dpad_type == "bindings":
                    self._queue_event_direction()
            elif event.type == pygame.JOYHATMOTION:
                self._event_hats[event.hat] = event.value
                self._queue_event_direction()
            elif event.type == pygame.JOYAXISMOTION:
                self._event_axes[event.axis] = event.value
                self._queue_event_direction()
            return
        if event.type == pygame.JOYDEVICEADDED and self.joystick is None:
            self.init_joystick()
        elif event.type == pygame.JOYDEVICEREMOVED and self.joystick is not None:
            try:
                removed = self.joystick.get_instance_id() == event.instance_id
            except pygame.error:
                removed = True
            if removed:
                self.joystick = None
                self._curr_buttons.clear()
                self._next_joystick_check = 0
                self._pending_button_presses.clear()
                self._pending_button_releases.clear()
                self._pending_directions.clear()
                self._event_hats.clear()
                self._event_axes.clear()
                self._event_pad_buttons.clear()

    def discard_pending(self):
        """Drop input accumulated before a focus or control-mapping transition."""
        self._pending_directions.clear()
        self._pending_button_presses.clear()
        self._pending_button_releases.clear()
        self._pending_key_presses.clear()
        self._pending_key_releases.clear()
        self.update()
        self._seed_gamepad_events()
        self.reset_repeat()

    def suppress_key(self, key):
        """A global shortcut such as Alt+Enter must not also fire a game action."""
        self._suppressed_keys.add(key)
        self._pending_key_presses.discard(key)
        self._event_pressed_keys.discard(key)
        self._curr_keys[key] = False
        self._prev_keys[key] = False

    def _queue_event_direction(self):
        """Preserve directional changes (including release) in arrival order."""
        held = lambda name: any(key in self._direction_keys for key in self.key_map.get(name, ()))
        dx = -1 if held("left") else 1 if held("right") else 0
        dy = -1 if held("up") else 1 if held("down") else 0
        if self.joystick is not None:
            pad_x, pad_y = self._decode_gamepad(
                self._event_axes, self._event_hats, self._event_pad_buttons
            )
            dx, dy = pad_x or dx, pad_y or dy
        direction = (dx, dy)
        previous = self._pending_directions[-1] if self._pending_directions else self._curr_dpad
        if direction != previous:
            self._pending_directions.append(direction)

    def action_pressed(self):
        """
        Check if action button was just pressed (edge detected).
        Convenience method combining get_any_action_button with edge detection.

        Returns:
            bool: True if action button was pressed this frame.
        """
        return self.was_pressed("action") or self.was_pressed("a")

    def back_pressed(self):
        """
        Check if back button was just pressed (edge detected).
        Convenience method combining get_any_back_button with edge detection.

        Returns:
            bool: True if back button was pressed this frame.
        """
        return self.was_pressed("back") or self.was_pressed("b") or self.was_pressed("select")

    def pause_pressed(self):
        """
        Check if pause button was just pressed (edge detected).
        P key or Start button toggles pause.

        Returns:
            bool: True if pause button was pressed this frame.
        """
        return self.was_pressed("pause") or self.was_pressed("start")

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

        try:
            return {
                "name": self.joystick.get_name(),
                "num_buttons": self.joystick.get_numbuttons(),
                "num_axes": self.joystick.get_numaxes(),
                "num_hats": self.joystick.get_numhats(),
            }
        except pygame.error:
            self.joystick = None
            self._next_joystick_check = 0
            return None


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
    """Return the current snapshot; the owner advances it once via update()."""
    return get_input_manager().get_dpad()


def get_button(button_id):
    """Backwards compatible get_button function."""
    return get_input_manager().get_button(button_id)


def get_any_action_button():
    """Backwards compatible get_any_action_button function."""
    return get_input_manager().get_any_action_button()


def get_any_back_button():
    """Backwards compatible get_any_back_button function."""
    return get_input_manager().get_any_back_button()
