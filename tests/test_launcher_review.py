"""Independent review regressions for the launcher idle and display behavior."""

from types import SimpleNamespace

import pygame
import pytest

import game_launcher as launcher

REAL_POLL_EVENTS = launcher.poll_events


@pytest.fixture
def review_launcher(monkeypatch):
    screen = launcher.initialize(False)
    monkeypatch.setattr(launcher, "poll_events", lambda **kwargs: [])
    yield screen
    launcher.cleanup()


@pytest.mark.parametrize(
    "direction, tick, frames, expected", [((0, 0), 1000, 40, "sleep"), ((1, 0), 16, 20, "movement")]
)
def test_menu_animation_advances_and_reaches_sleep(
    review_launcher, monkeypatch, direction, tick, frames, expected
):
    elapsed = [0]
    actual = []
    original = launcher.AnimatedFerret

    def recording_ferret(*args, **kwargs):
        ferret = original(*args, **kwargs)
        actual.append(ferret)
        return ferret

    class Clock:
        def tick(self, fps):
            elapsed[0] += tick
            return tick

    monkeypatch.setattr(launcher, "AnimatedFerret", recording_ferret)
    monkeypatch.setattr(pygame.time, "Clock", Clock)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: elapsed[0])
    monkeypatch.setattr(
        launcher,
        "input_manager",
        SimpleNamespace(
            back_pressed=lambda: False,
            menu_direction=lambda: direction,
            confirm_pressed=lambda: False,
        ),
    )
    renders = [0]
    states = []

    def render():
        renders[0] += 1
        states.append((actual[0].state, actual[0]._frame))
        if renders[0] >= frames:
            launcher._quit_requested = True

    monkeypatch.setattr(launcher.engine, "scale_to_screen", render)
    launcher.run_menu(review_launcher)
    assert states[-1][0] == expected
    if direction != (0, 0):
        assert len({frame for _, frame in states}) > 1


def test_settings_reflects_current_fullscreen_override(review_launcher, monkeypatch):
    # Emulate --fullscreen overriding a stored windowed preference.
    launcher.settings_manager.set("fullscreen", False)
    monkeypatch.setattr(launcher, "_fullscreen_mode", True)
    backs = iter([False, True])
    monkeypatch.setattr(
        launcher,
        "input_manager",
        SimpleNamespace(
            back_pressed=lambda: next(backs),
            menu_direction=lambda: (0, 0),
            confirm_pressed=lambda: False,
        ),
    )
    labels = []
    original = launcher.Button

    def recording_button(rect, text, *args, **kwargs):
        labels.append(text)
        return original(rect, text, *args, **kwargs)

    monkeypatch.setattr(launcher, "Button", recording_button)
    launcher.run_settings_menu(review_launcher)
    assert "Fullscreen: ON" in labels


def test_demo_mute_key_keeps_live_and_saved_preference_in_sync(
    review_launcher, monkeypatch, simulate_game
):
    monkeypatch.setattr(launcher, "poll_events", REAL_POLL_EVENTS)
    monkeypatch.setattr(launcher.input_manager, "get_dpad", lambda: (0, 0))
    pygame.event.clear()
    before = launcher.audio_manager.muted
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    simulate_game(review_launcher, game_index=0, max_frames=1)
    assert launcher.audio_manager.muted is before
    assert launcher.audio_manager.muted == launcher.settings_manager.get("muted")


@pytest.mark.parametrize("game_index", range(6))
def test_demo_moves_every_game_through_real_input(
    review_launcher, monkeypatch, game_index, simulate_game
):
    monkeypatch.setattr(launcher.input_manager, "get_dpad", lambda: (0, 0))
    monkeypatch.setattr(launcher.input_manager, "get_any_action_button", lambda: False)
    monkeypatch.setattr(launcher.input_manager, "get_any_back_button", lambda: False)
    classes = list(launcher.GAME_CLASSES)
    real_class = classes[game_index]
    positions, calls, bullets, states = [], [], [], []

    def position(game):
        if game_index == 0:
            return game.snake[0]
        if game_index == 3:
            return (game.player.x, game.player.y)
        if game_index == 5:
            return (game.player_col, game.player_row)
        return (game.player_x, game.player_y)

    def recording_game(*args):
        game = real_class(*args)
        positions.append(position(game))
        handle, update = game.handle_input, game.update

        def record_input():
            calls.append(game.input_manager.get_dpad())
            return handle()

        def record_update(dt):
            update(dt)
            positions.append(position(game))
            states.append(getattr(game, "state", None))
            if game_index == 3:
                bullets.append(len(game.bullets))
                assert pygame.Rect(0, 0, 800, 600).contains(game.player.get_rect())
            if game_index == 5:
                assert (game.ferret.x, game.ferret.y) == (
                    game.player_col * 32 + 16,
                    game.player_row * 32 + 16,
                )

        game.handle_input = record_input
        game.update = record_update
        return game

    classes[game_index] = recording_game
    monkeypatch.setattr(launcher, "GAME_CLASSES", classes)
    simulate_game(review_launcher, game_index=game_index, max_frames=180)
    assert len(calls) == 180
    assert len(set(positions)) > 1
    if game_index == 2:
        assert "PLAY" in states
    if game_index == 3:
        assert max(bullets) > 0


def test_dpad_can_confirm_in_flight_and_return_to_the_same_title(review_launcher, monkeypatch):
    controls = launcher.input_manager
    events = iter([(1, 0), (0, 0)])
    monkeypatch.setattr(controls, "menu_direction", lambda: next(events))
    monkeypatch.setattr(controls, "confirm_pressed", lambda: True)
    assert launcher.run_menu(review_launcher) == 1
    assert launcher.run_menu(review_launcher) == 1


def test_campaign_difficulty_shows_rule_and_matching_personal_bests(review_launcher, monkeypatch):
    from engine import Difficulty

    launcher.get_score_manager().set_high_score("digdug", 4200, Difficulty.HARD)
    launcher.get_stats_manager().record_clear("digdug", Difficulty.HARD, 3621)
    screens = []

    def choose(_screen, _title, _labels, _selected, _subtitle, details):
        screens.extend(details)
        return 2

    monkeypatch.setattr(launcher, "choose", choose)
    assert launcher.select_difficulty(review_launcher, "Crystal Quest") == Difficulty.HARD
    assert "One beetle" in screens[0][0] and "No score yet" in screens[0][1]
    assert "Four beetles" in screens[2][0]
    assert "4,200" in screens[2][1] and "1:00.35" in screens[2][1]
