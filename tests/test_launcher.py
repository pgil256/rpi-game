"""Launcher regressions use injected input and temporary persistence only."""

import copy
import os
from pathlib import Path
import subprocess
import sys

import pygame
import pytest

import game_launcher as launcher
from engine import get_achievement_manager, get_score_manager, get_stats_manager


@pytest.fixture
def launched(monkeypatch, tmp_path):
    monkeypatch.setenv("WES_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    screen = launcher.initialize(False)
    # Live attached hardware must not stop deterministic demo tests.
    monkeypatch.setattr(launcher.input_manager, "get_dpad", lambda: (0, 0))
    monkeypatch.setattr(launcher.input_manager, "get_any_action_button", lambda: False)
    monkeypatch.setattr(launcher.input_manager, "get_any_back_button", lambda: False)
    pygame.event.clear()
    yield screen
    launcher.cleanup()


def test_import_has_no_initialization_or_writes(tmp_path):
    env = dict(os.environ, WES_DATA_DIR=str(tmp_path))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.argv=['pytest','--unknown']; import game_launcher as g; "
            "assert not g.pygame.get_init(); assert g.input_manager is None",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("game_index", range(6))
def test_full_demo_preserves_scores_stats_and_achievements(
    launched, monkeypatch, game_index, simulate_game
):
    monkeypatch.setattr(launcher, "poll_events", lambda **_: [])
    stats = get_stats_manager()
    achievements = get_achievement_manager()
    score = get_score_manager()
    before = (
        copy.deepcopy(stats.get_all()),
        copy.deepcopy(achievements.unlocked),
        copy.deepcopy(score._scores),
        copy.deepcopy(achievements.pending_notifications),
    )
    data = Path(os.environ["WES_DATA_DIR"])
    files = {p.name: p.read_bytes() for p in data.glob("*.json")}
    assert not simulate_game(launched, game_index, max_frames=900)
    after = (
        stats.get_all(),
        achievements.unlocked,
        score._scores,
        achievements.pending_notifications,
    )
    assert before == after
    assert files == {p.name: p.read_bytes() for p in data.glob("*.json")}
    assert not (data / "demos").exists()


def test_difficulty_uses_one_direction_and_confirm(launched, monkeypatch):
    manager = launcher.input_manager
    directions = iter([(0, 1), (0, 0)])
    confirmations = iter([False, True])
    monkeypatch.setattr(launcher, "poll_events", lambda **_: [])
    monkeypatch.setattr(manager, "back_pressed", lambda: False)
    monkeypatch.setattr(manager, "menu_direction", lambda: next(directions))
    monkeypatch.setattr(manager, "confirm_pressed", lambda: next(confirmations))
    assert launcher.select_difficulty(launched, "Test") is launcher.Difficulty.HARD


def test_settings_apply_and_flush_once(launched, monkeypatch):
    manager = launcher.input_manager
    directions = iter([(1, 0), (0, 1), (1, 0)])
    backs = iter([False, False, False, True])
    saves = []
    monkeypatch.setattr(launcher, "poll_events", lambda **_: [])
    monkeypatch.setattr(manager, "menu_direction", lambda: next(directions))
    monkeypatch.setattr(manager, "back_pressed", lambda: next(backs))
    monkeypatch.setattr(manager, "confirm_pressed", lambda: False)
    monkeypatch.setattr(
        launcher.settings_manager, "update", lambda values: saves.append(values.copy())
    )
    launcher.run_settings_menu(launched)
    assert len(saves) == 1
    assert saves[0]["muted"] is True
    assert launcher.audio_manager.muted is True
    assert launcher.audio_manager.volume == saves[0]["audio_volume"] / 100


@pytest.mark.parametrize(
    "viewer",
    [launcher.run_achievements_viewer, launcher.run_stats_viewer, launcher.test_controller],
)
def test_viewers_keep_input_manager_and_close_cleanly(launched, monkeypatch, viewer):
    manager = launcher.input_manager
    calls = iter([False, True])
    monkeypatch.setattr(manager, "back_pressed", lambda: next(calls))
    monkeypatch.setattr(manager, "was_pressed", lambda _: False)
    monkeypatch.setattr(manager, "menu_direction", lambda: (0, 0))
    viewer(launched)
    assert launcher.input_manager is manager
    assert pygame.get_init()


def test_crash_guard_logs_and_returns_to_menu(launched, monkeypatch, caplog):
    messages = []
    monkeypatch.setattr(launcher, "choose", lambda *args, **kw: messages.append(args[1]))

    def broken():
        raise RuntimeError("regression probe")

    assert launcher.guarded(launched, broken) is None
    assert messages == ["This game could not continue"]
    assert "regression probe" in caplog.text


def test_letterbox_mouse_mapping(launched, monkeypatch):
    monkeypatch.setattr(launcher, "_viewport", pygame.Rect(240, 0, 1440, 1080))
    assert launcher.logical_mouse((960, 540)) == (400, 300)
    assert launcher.logical_mouse((100, 540)) == (-1, -1)


def test_shutdown_retries_failed_achievement_save(launched, monkeypatch):
    manager = get_achievement_manager()
    original = manager._store.save
    monkeypatch.setattr(manager._store, "save", lambda _: False)
    assert manager.unlock("snake_first")
    assert manager._dirty
    assert not manager.save_path.exists()
    monkeypatch.setattr(manager._store, "save", original)
    launcher.cleanup()
    assert manager.save_path.exists()
    assert not manager._dirty
