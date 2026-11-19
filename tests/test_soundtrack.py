"""Music lifecycle, audio balance, generated media, and a home screen that stays put."""

from array import array
from pathlib import Path
from types import SimpleNamespace
import wave

import pygame
import pytest

import game_launcher as launcher
from engine import InputManager
from engine.audio_manager import AudioManager
from engine.settings_manager import SettingsManager

SOUNDS = Path(__file__).resolve().parents[1] / "sounds"


def test_all_music_and_effects_load_and_music_loops_have_headroom():
    audio = AudioManager()
    music_hashes = set()
    for name, value in vars(AudioManager).items():
        if name.startswith("SOUND_") and isinstance(value, str):
            assert audio._load_sound(value) is not None
    for key in ["home"] + [game["key"] for game in launcher.GAMES]:
        path = SOUNDS / f"{key}_theme.wav"
        with wave.open(str(path), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            assert 25 < duration <= 40
            samples = array("h", wav.readframes(wav.getnframes()))
            assert samples[0] == samples[-1] == 0
            assert 1000 < max(abs(sample) for sample in samples) < 30000
            assert abs(sum(samples) / len(samples)) < 100
            music_hashes.add(hash(samples.tobytes()))
        assert audio.play_music(f"{key}_theme")
        assert pygame.mixer.music.get_busy()
    assert len(music_hashes) == 7
    audio.stop_music()


def test_muted_track_change_can_unmute_and_pause_survives_mute(monkeypatch):
    audio = AudioManager()
    calls = []
    for method in ("load", "play", "pause", "unpause", "set_volume"):
        monkeypatch.setattr(
            pygame.mixer.music,
            method,
            lambda *args, _method=method, **kwargs: calls.append(_method),
        )
    audio.set_mute(True)
    calls.clear()
    assert audio.play_music("home_theme")
    assert calls == ["load", "set_volume", "play", "pause"]
    calls.clear()
    assert audio.play_music("home_theme")
    assert calls == []
    audio.set_mute(False)
    assert calls == ["unpause"]
    audio.pause_music()
    audio.set_mute(True)
    calls.clear()
    audio.set_mute(False)
    assert calls == []
    audio.resume_music()
    assert calls == ["unpause"]


def test_master_changes_preserve_music_and_effect_balance():
    audio = AudioManager()
    sound = audio._load_sound("collect")
    audio.music_volume = 0.2
    audio.effects_volume = 0.8
    audio.volume = 0.5
    assert sound.get_volume() == pytest.approx(0.4, abs=0.01)
    assert pygame.mixer.music.get_volume() == pytest.approx(0.1, abs=0.01)
    assert audio.play_music("home_theme")
    assert pygame.mixer.music.get_volume() == pytest.approx(0.1, abs=0.01)
    audio.volume = 0.25
    assert sound.get_volume() == pytest.approx(0.2, abs=0.01)
    assert pygame.mixer.music.get_volume() == pytest.approx(0.05, abs=0.01)


def test_repeated_effects_are_throttled_without_delaying_first_press(monkeypatch):
    audio = AudioManager()
    ticks = [0]
    calls = []
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks[0])
    sound = SimpleNamespace(play=lambda: calls.append(ticks[0]) or object())
    monkeypatch.setattr(audio, "_load_sound", lambda name: sound)
    assert audio.play_sound(AudioManager.SOUND_PELLET)
    for tick in range(1, 90):
        ticks[0] = tick
        assert not audio.play_sound(AudioManager.SOUND_PELLET)
    ticks[0] = 90
    assert audio.play_sound(AudioManager.SOUND_PELLET)
    assert calls == [0, 90]


def test_home_stays_open_after_ten_minutes_idle(monkeypatch):
    screen = launcher.initialize(False)
    elapsed = [0]
    renders = []

    class Clock:
        def tick(self, fps):
            elapsed[0] += 10000
            return 10000

    monkeypatch.setattr(pygame.time, "Clock", Clock)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: elapsed[0])
    monkeypatch.setattr(launcher, "poll_events", lambda: [])
    monkeypatch.setattr(
        launcher,
        "input_manager",
        SimpleNamespace(
            back_pressed=lambda: False, menu_direction=lambda: (0, 0), confirm_pressed=lambda: False
        ),
    )

    def render():
        renders.append(elapsed[0])
        if len(renders) == 65:
            launcher._quit_requested = True

    monkeypatch.setattr(launcher.engine, "scale_to_screen", render)
    try:
        assert launcher.run_menu(screen) is None
        assert len(renders) == 65
        assert elapsed[0] > 600000
        assert launcher.audio_manager._current_music == "home_theme"
    finally:
        launcher.cleanup()


@pytest.mark.parametrize("cls", launcher.GAME_CLASSES)
def test_real_game_loop_selects_its_theme_and_stops_it_on_exit(screen, monkeypatch, cls):
    game = cls(screen, InputManager())
    selected = []
    stopped = []
    monkeypatch.setattr(game.audio, "play_music", lambda name: selected.append(name))
    monkeypatch.setattr(game.audio, "stop_music", lambda: stopped.append(True))
    monkeypatch.setattr(game, "handle_input", lambda: True)
    game.run()
    assert selected == [f"{game.game_key}_theme"]
    assert stopped == [True]


def test_pausing_and_restarting_game_resumes_music_correctly(screen, monkeypatch):
    from games.snake import SnakeGame

    controls = InputManager()
    game = SnakeGame(screen, controls)
    game.waiting_for_input = False
    game.audio.play_music("snake_theme")
    monkeypatch.setattr(controls, "pause_pressed", lambda: True)
    game.advance(1 / 60)
    assert game.paused and game.audio._music_paused
    game.audio.set_mute(True)
    game.audio.set_mute(False)
    assert game.audio._music_paused
    game.advance(1 / 60)
    assert not game.paused and not game.audio._music_paused


def test_music_and_effect_preferences_validate_and_persist():
    settings = SettingsManager()
    settings.update({"music_volume": 25, "effects_volume": 75})
    reloaded = SettingsManager()
    assert reloaded.get("music_volume") == 25
    assert reloaded.get("effects_volume") == 75
    reloaded.update({"music_volume": float("nan"), "effects_volume": "loud"})
    assert reloaded.get("music_volume") == 25
    assert reloaded.get("effects_volume") == 75
