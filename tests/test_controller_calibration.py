"""USB D-pad regressions: physical signals, queued taps, and saved calibration."""

import copy
import json
from collections import defaultdict

import pygame
import pytest

from engine import InputManager
from engine.controller_mapping import DIRECTIONS, decode_bindings, detect_binding, valid_bindings
from engine.persistence import data_path


class Gamepad:
    def __init__(self, axes=None, hats=None, buttons=None, guid="nes-controller"):
        self.axes = list(axes if axes is not None else [-0.008] * 5)
        self.hats = list(hats or [])
        self.buttons = list(buttons or [False] * 10)
        self.guid = guid

    def init(self):
        pass

    def get_name(self):
        return "USB Gamepad"

    def get_guid(self):
        return self.guid

    def get_instance_id(self):
        return 31

    def get_numaxes(self):
        return len(self.axes)

    def get_numhats(self):
        return len(self.hats)

    def get_numbuttons(self):
        return len(self.buttons)

    def get_axis(self, index):
        return self.axes[index]

    def get_hat(self, index):
        return self.hats[index]

    def get_button(self, index):
        return self.buttons[index]


@pytest.fixture
def gamepad(monkeypatch):
    device = Gamepad()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 1)
    monkeypatch.setattr(pygame.joystick, "Joystick", lambda index: device)
    return device


def unusual_axes():
    # X is axis 3 and positive Y means UP on axis 4; axes 0/1 are unrelated.
    return {
        name: {"kind": "axis", "index": index, "value": value, "center": -0.008}
        for name, index, value in (("up", 4, 1), ("right", 3, 1), ("down", 4, -1), ("left", 3, -1))
    }


@pytest.mark.parametrize("name", DIRECTIONS)
def test_calibration_handles_axis_four_inversion_and_unrelated_noise(gamepad, name):
    controls = InputManager()
    neutral = controls.raw_controller_state()
    bindings = unusual_axes()
    assert controls.save_dpad_calibration(bindings)
    signal = bindings[name]
    gamepad.axes[signal["index"]] = signal["value"]
    assert detect_binding(neutral, controls.raw_controller_state()) == signal
    # An unused axis at its extreme must never override the D-pad.
    gamepad.axes[0] = -1
    controls.handle_event(
        pygame.event.Event(
            pygame.JOYAXISMOTION, axis=signal["index"], value=signal["value"], instance_id=31
        )
    )
    controls.update()
    assert controls.get_dpad() == DIRECTIONS[name]
    controls.update()
    assert controls.get_dpad() == DIRECTIONS[name]
    gamepad.axes[signal["index"]] = -0.008
    controls.handle_event(
        pygame.event.Event(pygame.JOYAXISMOTION, axis=signal["index"], value=-0.008, instance_id=31)
    )
    controls.update()
    assert controls.get_dpad() == (0, 0)


def test_calibrated_short_taps_keep_order_and_release(gamepad):
    controls = InputManager()
    assert controls.save_dpad_calibration(unusual_axes())
    for index, value in [(4, 1), (4, -0.008), (3, -1), (3, -0.008)]:
        controls.handle_event(
            pygame.event.Event(pygame.JOYAXISMOTION, axis=index, value=value, instance_id=31)
        )
    actual = []
    for _ in range(5):
        controls.update()
        actual.append(controls.get_dpad())
    assert actual == [(0, -1), (0, 0), (-1, 0), (0, 0), (0, 0)]


def test_calibration_survives_restart_and_ignores_other_controller(gamepad):
    controls = InputManager()
    assert controls.save_dpad_calibration(unusual_axes())
    controls = InputManager()
    gamepad.axes[4] = 1
    controls.update()
    assert controls.get_dpad() == (0, -1)
    gamepad.guid = "different-controller"
    gamepad.axes[1] = 1
    controls.update()
    assert controls.get_dpad() == (0, 1)


@pytest.mark.parametrize(
    "axes, expected",
    [
        ([-0.008, -0.008, -0.008, -0.008, -1], (0, -1)),
        ([1, 1, 1, 1, -0.008], (1, 0)),
        ([-0.008, -0.008, -0.008, -0.008, 1], (0, 1)),
        ([-1, -1, -1, -1, -0.008], (-1, 0)),
        ([-0.008] * 5, (0, 0)),
    ],
)
def test_captured_usb_nes_signals_do_not_confuse_duplicate_axes(gamepad, axes, expected):
    # Physical Up/Right/Down/Left capture, 2026-11-14. Axes 1-3 mirror X.
    bindings = {
        name: {"kind": "axis", "index": index, "value": value, "center": -0.008}
        for name, index, value in (("up", 4, -1), ("right", 0, 1), ("down", 4, 1), ("left", 0, -1))
    }
    controls = InputManager()
    assert controls.save_dpad_calibration(bindings)
    gamepad.axes = axes
    for i, value in enumerate(axes):
        controls.handle_event(
            pygame.event.Event(pygame.JOYAXISMOTION, axis=i, value=value, instance_id=31)
        )
    controls.update()
    assert controls.get_dpad() == expected
    controls.update()
    assert controls.get_dpad() == expected


def test_calibration_save_failure_preserves_previous_mapping(gamepad, monkeypatch):
    from engine.persistence import JsonStore

    controls = InputManager()
    monkeypatch.setattr(JsonStore, "save", lambda *args: False)
    assert not controls.save_dpad_calibration(unusual_axes())
    assert controls.dpad_type == "auto"
    assert controls.dpad_bindings is None


def test_button_dpad_does_not_also_trigger_default_action_or_back(gamepad):
    controls = InputManager()
    bindings = {name: {"kind": "button", "index": i} for i, name in enumerate(DIRECTIONS)}
    assert controls.save_dpad_calibration(bindings)
    gamepad.buttons[1] = True
    controls.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=1, instance_id=31))
    controls.update()
    assert controls.get_dpad() == (1, 0)
    assert not controls.action_pressed()
    assert not controls.get_any_action_button()
    gamepad.buttons[1] = False
    controls.handle_event(pygame.event.Event(pygame.JOYBUTTONUP, button=1, instance_id=31))
    controls.update()
    assert controls.get_dpad() == (0, 0)


def test_neutral_hat_does_not_fall_back_to_idle_trigger_axes(gamepad):
    gamepad.hats = [(0, 0)]
    gamepad.axes = [-1, -1]
    controls = InputManager()
    controls.handle_event(
        pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=-1, instance_id=31)
    )
    controls.update()
    assert controls.get_dpad() == (0, 0)
    gamepad.hats[0] = (-1, 1)
    controls.update()
    assert controls.get_dpad() == (-1, -1)


@pytest.mark.parametrize("kind", ["hat", "button"])
def test_guided_mapping_detects_hats_and_buttons_with_diagonals(kind):
    neutral = {"axes": [0, 0], "hats": [(0, 0)], "buttons": [False] * 4}
    bindings = {}
    for index, (name, (x, y)) in enumerate(DIRECTIONS.items()):
        pressed = copy.deepcopy(neutral)
        if kind == "hat":
            pressed["hats"][0] = (x, -y)
        else:
            pressed["buttons"][index] = True
        bindings[name] = detect_binding(neutral, pressed)
    assert valid_bindings(bindings)
    assert decode_bindings(bindings, {}, {0: (1, 1)}, {0: True, 1: True}) == (1, -1)
    assert decode_bindings(bindings, {}, {0: (0, 0)}, {}) == (0, 0)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"up": {}},
        {
            name: {"kind": "axis", "index": 4, "value": float("nan"), "center": 0}
            for name in DIRECTIONS
        },
    ],
)
def test_corrupt_calibration_falls_back_safely(gamepad, bad):
    path = data_path("controller_config.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dpad_type": "bindings", "dpad_bindings": bad}))
    controls = InputManager()
    controls.update()
    assert controls.dpad_type == "auto"
    assert controls.get_dpad() == (0, 0)


def test_calibration_screen_learns_all_directions_and_saves(gamepad, monkeypatch):
    import game_launcher as launcher

    screen = launcher.initialize(False)
    elapsed = [0]
    states = [[-0.008] * 5 for _ in range(10)]
    for binding in unusual_axes().values():
        pressed = [-0.008] * 5
        pressed[binding["index"]] = binding["value"]
        states.extend([pressed] * 4)
        states.extend([[-0.008] * 5 for _ in range(4)])
    snapshots = iter(states)

    def poll():
        gamepad.axes = next(snapshots)
        elapsed[0] += 100
        return []

    monkeypatch.setattr(launcher, "poll_events", poll)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: elapsed[0])
    monkeypatch.setattr(launcher.engine, "scale_to_screen", lambda: None)
    try:
        assert launcher.calibrate_controller(screen).startswith("D-pad saved")
        saved = json.loads(data_path("controller_config.json").read_text())
        assert saved["dpad_bindings"] == unusual_axes()
        assert saved["controller_guid"] == gamepad.guid
    finally:
        launcher.cleanup()


def test_face_button_wizards_preserve_button_dpad_and_other_profiles(gamepad, monkeypatch):
    import diagnose_controller as cli
    import game_launcher as launcher

    screen = launcher.initialize(False)
    controls = launcher.input_manager
    bindings = {key: {"kind": "button", "index": i} for i, key in enumerate(DIRECTIONS, start=3)}
    assert controls.save_dpad_calibration(bindings)
    try:
        # Pick just A. Capture an ordinary short button press and release.
        monkeypatch.setattr(launcher, "choose", lambda *args: 1)
        states = iter([None, 7, None])

        def poll():
            pressed = next(states)
            gamepad.buttons = [i == pressed for i in range(10)]
            controls.update()
            return []

        monkeypatch.setattr(launcher, "poll_events", poll)
        assert launcher.remap_controller(screen).startswith("Buttons saved")
        assert controls.button_map["a"] == 7

        monkeypatch.setattr(cli, "CONFIG_FILE", data_path("controller_config.json"))
        assert cli.save_config(
            {
                "controller_name": gamepad.get_name(),
                "controller_guid": gamepad.guid,
                "buttons": {"b": 0},
            }
        )
        another = "other-device"
        assert cli.save_config(
            {"controller_name": "Second pad", "controller_guid": another, "buttons": {"start": 4}}
        )
        fresh = InputManager()
        assert fresh.button_map == {**fresh.DEFAULT_BUTTON_MAP, "a": 7, "b": 0}
        assert fresh.dpad_bindings == bindings
        for direction, binding in bindings.items():
            gamepad.buttons = [i == binding["index"] for i in range(10)]
            fresh.update()
            assert fresh.get_dpad() == DIRECTIONS[direction]
            assert not fresh.confirm_pressed() and not fresh.back_pressed()
        gamepad.guid = another
        other = InputManager()
        assert other.button_map["start"] == 4 and other.dpad_type == "auto"
        assert other.button_map["a"] == other.DEFAULT_BUTTON_MAP["a"]
    finally:
        launcher.cleanup()


def test_remap_all_accepts_old_back_and_start_and_requires_release(gamepad, monkeypatch):
    import game_launcher as launcher

    screen = launcher.initialize(False)
    controls = launcher.input_manager
    monkeypatch.setattr(launcher, "choose", lambda *args: 0)
    # A/B/Select/Start swap places. The held button is visible for two frames.
    states = iter([None, 2, 2, None, 1, None, 9, None, 8, None])

    def poll():
        n = next(states)
        gamepad.buttons = [i == n for i in range(10)]
        controls.update()
        return []

    monkeypatch.setattr(launcher, "poll_events", poll)
    try:
        assert launcher.remap_controller(screen).startswith("Buttons saved")
        assert controls.button_map == {"a": 2, "b": 1, "start": 8, "select": 9}
        assert not controls.save_button_mapping({"b": 2})
        assert InputManager().button_map == controls.button_map
    finally:
        launcher.cleanup()
