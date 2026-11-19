"""Run totals survive early exit and are committed once across terminal/restart paths."""

import json
from pathlib import Path

import pytest

from engine import Difficulty
from engine.persistence import data_path, persistence_session
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame
from games.digdug import Enemy

GAMES = (SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame)


class SessionControls:
    demo_mode = False
    action = False

    def update(self):
        pass

    def get_dpad(self):
        return (0, 0)

    def back_pressed(self):
        return False

    def pause_pressed(self):
        return False

    def action_pressed(self):
        return self.action

    def confirm_pressed(self):
        return self.action

    def get_any_action_button(self):
        return self.action


def start_death(game, final=False):
    if final and hasattr(game, "lives"):
        game.lives = 1
    if isinstance(game, SnakeGame):
        game._trigger_death()
    elif isinstance(game, PacmanGame):
        game._start_death()
    elif isinstance(game, FroggerGame):
        game.state = "PLAY"
        game._start_death()
    elif isinstance(game, CentipedeGame):
        game._player_death()
    elif isinstance(game, DigDugGame):
        game.invulnerable_timer = 0
        game.enemies.empty()
        game.enemies.add(Enemy(186, 186, game.enemy_img))
        game.update(1 / 60)
    elif isinstance(game, BoulderDashGame):
        game._start_death()


def pending_activity(game):
    """Accrued cumulative counters, before the terminal hook has been reached."""
    game.score = 120
    expected = {"total_score": 120, "deaths": 1}
    if isinstance(game, SnakeGame):
        expected["highest_length"] = len(game.snake)
    elif isinstance(game, FroggerGame):
        game._crossings = 2
        expected["crossings"] = 2
    elif isinstance(game, CentipedeGame):
        game._centipedes_destroyed = 3
        game._spiders_killed = 1
        expected.update(centipedes_destroyed=3, spiders_killed=1)
    elif isinstance(game, DigDugGame):
        game._total_crystals = 2
        expected["crystals_collected"] = 2
    elif isinstance(game, BoulderDashGame):
        game._total_diamonds = 2
        game._levels_completed = 1
        expected.update(diamonds_collected=2, levels_completed=1)
    return expected


@pytest.mark.parametrize("cls", GAMES)
def test_early_exit_saves_pending_totals_and_score_once(screen, cls):
    game = cls(screen, SessionControls(), Difficulty.HARD)
    expected = pending_activity(game)
    start_death(game)
    # run() invokes this finally block for B, Esc, window close, and exceptions.
    game._track_session_stats()
    game._track_session_stats()
    persisted = json.loads(data_path("stats.json").read_text())
    for key, value in expected.items():
        assert persisted[game.game_key][key] == value
    assert persisted[game.game_key]["games_played"] == 1
    assert game.score_manager.get_high_score(game.game_key, Difficulty.HARD) == 120


@pytest.mark.parametrize("cls", GAMES)
def test_terminal_then_restart_does_not_duplicate_old_totals(screen, cls):
    controls = SessionControls()
    game = cls(screen, controls)
    expected = pending_activity(game)
    start_death(game, final=True)
    for _ in range(65):
        game.update(1 / 60)
    assert game._game_statistics_recorded
    for key, value in expected.items():
        assert game.stats.get(game.game_key, key) == value
    controls.action = True
    game.handle_input()
    controls.action = False
    assert game.score == 0
    assert game.stats.get(game.game_key, "games_played") == 2
    for key, value in expected.items():
        assert game.stats.get(game.game_key, key) == value
    game.score = 40
    game._track_session_stats()
    assert game.stats.get(game.game_key, "total_score") == 160
    assert game.stats.get(game.game_key, "deaths") == 1


@pytest.mark.parametrize("cls", GAMES)
def test_demo_terminal_restart_and_exit_do_not_mutate_real_totals(screen, cls):
    controls = SessionControls()
    controls.demo_mode = True
    with persistence_session(demo=True):
        game = cls(screen, controls)
        before = game.stats.get_all()
        achievements = dict(game.achievements.unlocked)
        scores = game.score_manager.get_all_scores()
        pending_activity(game)
        start_death(game, final=True)
        for _ in range(65):
            game.update(1 / 60)
        controls.action = True
        game.handle_input()
    game._track_session_stats()
    assert game.stats.get_all() == before
    assert game.achievements.unlocked == achievements
    assert game.score_manager.get_all_scores() == scores
    assert not Path(data_path("stats.json")).exists()
