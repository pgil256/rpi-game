"""Fullscreen on laptop/HDMI, safe fallbacks, and shortcuts during gameplay."""

from collections import defaultdict

import pygame
import pytest

import engine
import game_launcher as launcher
from engine.settings_manager import SettingsManager


@pytest.fixture
def displays(monkeypatch):
    screen = launcher.initialize(False)
    desktops = [(1280, 720), (1920, 1080), (3840, 2160)]
    calls = []

    def set_mode(size, flags=0, *, display=0):
        calls.append((size, flags, display))
        return pygame.Surface(size)

    monkeypatch.setattr(pygame.display, "get_desktop_sizes", lambda: desktops)
    monkeypatch.setattr(pygame.display, "set_mode", set_mode)
    yield screen, desktops, calls
    launcher.cleanup()


@pytest.mark.parametrize("index", range(3))
def test_fullscreen_uses_selected_native_size_without_replacing_game_surface(displays, index):
    logical, desktops, calls = displays
    launcher.configure_display(True, index, "aspect")
    assert calls[-1] == (desktops[index], pygame.FULLSCREEN, index)
    assert launcher._render_surface is logical
    assert launcher._viewport.height == desktops[index][1]
    assert launcher._viewport.width * 3 == launcher._viewport.height * 4
    assert launcher.logical_mouse((desktops[index][0] / 2, desktops[index][1] / 2)) == (400, 300)
    assert launcher.logical_mouse((0, 0)) == (-1, -1)


def test_stretch_fills_tv_and_maps_clicks(displays):
    launcher.configure_display(True, 1, "fill")
    assert launcher._viewport == pygame.Rect(0, 0, 1920, 1080)
    assert launcher.logical_mouse((960, 540)) == (400, 300)
    assert launcher.logical_mouse((0, 0)) == (0, 0)


def test_removed_hdmi_returns_to_laptop_and_handles_resolution_change(displays, monkeypatch):
    _, desktops, calls = displays
    launcher.configure_display(True, 1)
    desktops[:] = [(1280, 720)]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 5000)
    launcher._refresh_displays()
    assert calls[-1] == ((1280, 720), pygame.FULLSCREEN, 0)
    assert launcher._display_index == 0
    desktops[:] = [(1600, 900)]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 7000)
    launcher._refresh_displays()
    assert calls[-1][0] == (1600, 900)


def test_unavailable_saved_monitor_falls_back_and_mode_failure_opens_window(displays, monkeypatch):
    launcher.configure_display(True, 99)
    assert launcher._display_index == 0
    assert "unavailable" in launcher._display_notice
    original = pygame.display.set_mode

    def fail_fullscreen(size, flags=0, *, display=0):
        if flags & pygame.FULLSCREEN:
            raise pygame.error("TV disconnected")
        return original(size, flags, display=display)

    monkeypatch.setattr(pygame.display, "set_mode", fail_fullscreen)
    launcher.configure_display(True, 1)
    assert not launcher._fullscreen_mode
    assert launcher._display_index == 0
    assert launcher._real_screen.get_size() == (800, 600)


def test_shortcuts_use_game_event_hook_and_alt_enter_does_not_fire(displays, monkeypatch):
    keys = defaultdict(bool, {pygame.K_RETURN: True})
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: keys)
    launcher.configure_display(False, 0)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_ALT)
    assert engine.handle_global_event(event)
    launcher.input_manager.update()
    assert launcher._fullscreen_mode
    assert not launcher.input_manager.action_pressed()
    assert not launcher.input_manager.get_any_action_button()
    launcher.input_manager.update()
    assert not launcher.input_manager.get_any_action_button()
    keys[pygame.K_RETURN] = False
    launcher.input_manager.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
    launcher.input_manager.update()
    keys[pygame.K_RETURN] = True
    launcher.input_manager.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    launcher.input_manager.update()
    assert launcher.input_manager.action_pressed()
    assert engine.handle_global_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F10))
    assert launcher._display_index == 1
    saved = SettingsManager()
    assert saved.get("fullscreen") is True
    assert saved.get("display_index") == 1
    assert engine.handle_global_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
    assert not launcher._fullscreen_mode


def test_settings_apply_screen_and_fit_and_restore_on_next_launch(displays, monkeypatch):
    screen, _, _ = displays
    directions = iter([(0, 1), (0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0)])
    backs = iter([False] * 7 + [True])
    monkeypatch.setattr(launcher, "poll_events", lambda: [])
    monkeypatch.setattr(launcher.input_manager, "menu_direction", lambda: next(directions))
    monkeypatch.setattr(launcher.input_manager, "back_pressed", lambda: next(backs))
    monkeypatch.setattr(launcher.input_manager, "confirm_pressed", lambda: False)
    launcher.configure_display(False, 0, "aspect")
    launcher.run_settings_menu(screen)
    assert launcher._fullscreen_mode
    assert launcher._display_index == 1
    assert launcher._screen_fit == "fill"
    saved = SettingsManager()
    assert saved.get("fullscreen") is True
    assert saved.get("display_index") == 1
    assert saved.get("screen_fit") == "fill"


def test_display_settings_reject_invalid_values():
    settings = SettingsManager()
    settings.update({"display_index": -2, "screen_fit": ["fill"]})
    assert settings.get("display_index") == 0
    assert settings.get("screen_fit") == "aspect"
