"""Actual event batches must preserve button taps between polling snapshots."""

from collections import defaultdict
from types import SimpleNamespace

import pygame

from engine import InputManager


def test_keyboard_press_release_in_one_batch_keeps_action_edge(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    controls.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    controls.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
    controls.update()
    assert controls.action_pressed()
    controls.update()
    assert not controls.action_pressed()


def test_gamepad_press_release_in_one_batch_keeps_action_edge(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    controls.joystick = SimpleNamespace(
        get_instance_id=lambda: 31,
        get_numbuttons=lambda: 10,
        get_button=lambda button: False,
        get_numhats=lambda: 0,
        get_numaxes=lambda: 0,
    )
    button = controls.button_map["a"]
    controls.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=button, instance_id=31))
    controls.handle_event(pygame.event.Event(pygame.JOYBUTTONUP, button=button, instance_id=31))
    controls.update()
    assert controls.action_pressed()
    controls.update()
    assert not controls.action_pressed()


def test_short_directional_keyboard_taps_retain_order(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    for key in (pygame.K_UP, pygame.K_LEFT):
        controls.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        controls.handle_event(pygame.event.Event(pygame.KEYUP, key=key))
    directions = []
    for _ in range(5):
        controls.update()
        directions.append(controls.get_dpad())
    assert directions == [(0, -1), (0, 0), (-1, 0), (0, 0), (0, 0)]


def test_short_gamepad_hat_tap_does_not_stick(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    controls.joystick = SimpleNamespace(
        get_instance_id=lambda: 31,
        get_numbuttons=lambda: 0,
        get_numhats=lambda: 1,
        get_hat=lambda index: (0, 0),
        get_numaxes=lambda: 0,
    )
    controls.handle_event(
        pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(0, 1), instance_id=31)
    )
    controls.handle_event(
        pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(0, 0), instance_id=31)
    )
    controls.update()
    assert controls.get_dpad() == (0, -1)
    controls.update()
    assert controls.get_dpad() == (0, 0)
    controls.update()
    assert controls.get_dpad() == (0, 0)


def test_short_gamepad_axis_tap_does_not_stick(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    controls.joystick = SimpleNamespace(
        get_instance_id=lambda: 31,
        get_numbuttons=lambda: 0,
        get_numhats=lambda: 0,
        get_numaxes=lambda: 2,
        get_axis=lambda index: 0,
    )
    controls.handle_event(pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=1, instance_id=31))
    controls.handle_event(pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=0, instance_id=31))
    controls.update()
    assert controls.get_dpad() == (1, 0)
    controls.update()
    assert controls.get_dpad() == (0, 0)


def test_held_action_and_release_produce_one_edge(monkeypatch):
    keys = defaultdict(bool)
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: keys)
    controls = InputManager()
    keys[pygame.K_SPACE] = True
    controls.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    controls.update()
    assert controls.action_pressed() and controls.get_any_action_button()
    controls.update()
    assert not controls.action_pressed() and controls.get_any_action_button()
    keys[pygame.K_SPACE] = False
    controls.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))
    controls.update()
    assert not controls.action_pressed() and not controls.get_any_action_button()
    assert controls.was_released("action")
    controls.update()
    assert not controls.was_released("action")


def test_short_space_tap_fires_once_in_defender(screen, monkeypatch):
    from games.centipede import CentipedeGame

    monkeypatch.setattr(pygame.key, "get_pressed", lambda: defaultdict(bool))
    controls = InputManager()
    game = CentipedeGame(screen, controls)
    shots = []
    original_fire = game._fire_bullet

    def fire():
        shots.append(1)
        original_fire()

    monkeypatch.setattr(game, "_fire_bullet", fire)
    controls.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    controls.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))
    game.advance(1 / 60)
    assert len(game.bullets) == 1
    for _ in range(12):
        game.advance(1 / 60)
    assert len(shots) == 1
    assert not controls.get_any_action_button()
