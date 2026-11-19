import json
import pygame
import pytest
from engine import AnimatedFerret, InputManager
from engine.audio_manager import AudioManager
from engine.achievements import AchievementManager
from engine.base_game import BaseGame
from engine.persistence import JsonStore, data_dir, persistence_session
from engine.score_manager import ScoreManager
from engine.settings_manager import SettingsManager
from engine.stats_manager import StatsManager


def test_atomic_recovery_and_corrupt_types(tmp_path):
    path = tmp_path / "record.json"
    store = JsonStore(path)
    assert store.save({"score": 10})
    assert store.save({"score": 20})
    path.write_text("{broken", encoding="utf-8")
    assert store.load() == {"score": 10}
    assert list(tmp_path.glob("record.json.corrupt-*"))
    assert store.save({"score": 30})
    assert json.loads(path.read_text()) == {"score": 30}
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_failure_preserves_previous_data(tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    store = JsonStore(path)
    assert store.save({"score": 10})

    def fail(*args):
        raise PermissionError("read-only")

    monkeypatch.setattr("engine.persistence.os.replace", fail)
    assert not store.save({"score": 20})
    assert json.loads(path.read_text()) == {"score": 10}
    assert store.last_error


def test_scores_migrate_and_separate_difficulty(tmp_path):
    path = tmp_path / "high_scores.json"
    path.write_text(json.dumps({"snake": 15, "bad": None, "worse": [], "broken": {"easy": "no"}}))
    scores = ScoreManager(path)
    assert scores.get_high_score("snake", "normal") == 15
    assert scores.get_high_score("snake", "easy") == 0
    assert scores.set_high_score("snake", 12, "hard")
    assert ScoreManager(path).get_high_score("snake", "hard") == 12
    assert scores.get_high_score("bad") == 0


def test_settings_validate_and_batch(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"muted": "yes", "fullscreen": [], "audio_volume": "loud"}))
    settings = SettingsManager(path)
    assert settings.get_all() == SettingsManager.DEFAULTS
    calls = []
    monkeypatch.setattr(settings._store, "save", lambda values: calls.append(dict(values)))
    settings.update({"muted": True, "audio_volume": 30})
    assert len(calls) == 1
    settings.update({"muted": True, "audio_volume": 30})
    assert len(calls) == 1


def test_demo_blocks_mutations_and_files(tmp_path):
    scores, stats, achievements, settings = (
        ScoreManager(),
        StatsManager(),
        AchievementManager(),
        SettingsManager(),
    )
    before = (
        scores.get_all_scores(),
        stats.get_all(),
        dict(achievements.unlocked),
        settings.get_all(),
    )
    with persistence_session(demo=True):
        scores.set_high_score("snake", 999)
        stats.increment("global", "games_started")
        stats.save()
        achievements.unlock("first_win")
        settings.set("muted", True)
    after = (
        scores.get_all_scores(),
        stats.get_all(),
        dict(achievements.unlocked),
        settings.get_all(),
    )
    assert before == after
    assert not data_dir().exists()
    assert not achievements.pending_notifications


def test_stats_batch_and_hidden_progress(monkeypatch):
    stats = StatsManager()
    calls = []
    monkeypatch.setattr(stats._store, "save", lambda values: calls.append(values.copy()) or True)
    stats.increment("global", "games_started")
    stats.add("global", "total_play_time", 5)
    assert not calls
    assert stats.save()
    assert len(calls) == 1
    assert not stats.save()
    achievements = AchievementManager()
    unlocked, total = achievements.get_progress()
    assert total == len(achievements.get_all_achievements())
    assert unlocked == 0


def test_menu_tap_repeat_and_release():
    manager = InputManager()
    manager._curr_dpad = (0, 1)
    assert manager.menu_direction(0) == (0, 1)
    assert manager.menu_direction(100) == (0, 0)
    assert manager.menu_direction(249) == (0, 0)
    assert manager.menu_direction(250) == (0, 1)
    assert manager.menu_direction(369) == (0, 0)
    assert manager.menu_direction(370) == (0, 1)
    manager._curr_dpad = (0, 0)
    assert manager.menu_direction(400) == (0, 0)
    manager._curr_dpad = (0, 1)
    assert manager.menu_direction(410) == (0, 1)


def test_enter_action_and_start_pause_do_not_collide():
    manager = InputManager(button_map={"a": 5, "start": 6})
    manager._curr_keys = {pygame.K_RETURN: True}
    assert manager.action_pressed()
    assert not manager.pause_pressed()
    manager._curr_keys.clear()
    manager._curr_buttons = {6: True}
    assert manager.pause_pressed() and manager.confirm_pressed()
    assert not manager.action_pressed()
    manager._curr_buttons = {5: True}
    assert manager.get_any_action_button()


def test_second_input_manager_does_not_quit_joysticks(monkeypatch):
    calls = []
    monkeypatch.setattr(pygame.joystick, "quit", lambda: calls.append(True))
    InputManager()
    InputManager()
    assert not calls


def test_input_hotplug_reacquires(monkeypatch):
    class Joystick:
        def init(self):
            pass

        def get_name(self):
            return "test pad"

        def get_guid(self):
            return "test-pad"

        def get_numbuttons(self):
            return 1

        def get_numaxes(self):
            return 0

        def get_numhats(self):
            return 0

        def get_button(self, index):
            return False

    manager = InputManager()
    joystick = Joystick()
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 1)
    monkeypatch.setattr(pygame.joystick, "Joystick", lambda index: joystick)
    manager._next_joystick_check = 0
    manager.update()
    assert manager.joystick is joystick


def test_audio_missing_sound_volume_and_persistent_mute():
    audio = AudioManager()
    audio._sounds["missing"] = None
    audio.volume = 0.25
    assert audio.volume == 0.25
    audio.set_mute(True)
    assert audio.muted
    audio.toggle_mute()
    from engine.settings_manager import get_settings_manager

    assert get_settings_manager().get("muted") is False


def test_sprite_one_shot_and_sleep():
    sprite = AnimatedFerret(scale=1, enable_sleep=True)
    sprite.set_state("death")
    for _ in range(200):
        sprite.update()
    assert sprite.animation_finished
    assert sprite.current_frame == len(sprite._animations["death"]) - 1
    sprite.set_state("idle")
    for _ in range(901):
        sprite.update()
    assert sprite.state == "sleep"
    sprite.reset_idle_timer()
    assert sprite.state == "idle"


def test_aseprite_array_and_frame_durations(tmp_path):
    from engine.ferret_sprite import parse_animation_json

    path = tmp_path / "frames.json"
    path.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "filename": "Ferret (idle) 0",
                        "frame": {"x": 0, "y": 0, "w": 32, "h": 32},
                        "duration": 200,
                    }
                ]
            }
        )
    )
    assert parse_animation_json(str(path))["idle"][0]["duration"] == 200
    sprite = AnimatedFerret(scale=1)
    sprite._animation_data = {"idle": [{"duration": 200}] * 8}
    for _ in range(11):
        sprite.update()
    assert sprite.current_frame == 0
    for _ in range(2):
        sprite.update()
    assert sprite.current_frame == 1


class CounterGame(BaseGame):
    def setup(self):
        self.steps = 0
        self.score = 7

    def handle_input(self):
        return False

    def update(self, dt):
        assert dt == pytest.approx(1 / 60)
        self.steps += 1

    def render(self):
        pass


def test_fixed_step_30_and_60_fps_and_stall_clamp(screen):
    one, two = CounterGame(screen, InputManager()), CounterGame(screen, InputManager())
    for _ in range(60):
        one.advance(1 / 60)
    for _ in range(30):
        two.advance(1 / 30)
    assert one.steps == two.steps == 60
    one.advance(10)
    assert one.steps == 75


def test_exit_records_score_and_time_once(screen):
    game = CounterGame(screen, InputManager())
    for _ in range(8):
        game.advance(0.25)
    game.paused = True
    for _ in range(4):
        game.advance(0.25)
    game._track_session_stats()
    game._track_session_stats()
    assert game.stats.get("global", "games_started") == 1
    assert game.stats.get("global", "total_play_time") == pytest.approx(2, abs=0.1)
    from engine.score_manager import get_score_manager

    assert get_score_manager().get_high_score(game.game_key) == 7
