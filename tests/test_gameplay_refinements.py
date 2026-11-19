"""Player-visible regressions from the six-game gameplay audit."""

import os
import random
import subprocess
import sys

import pygame
import pytest

import game_launcher as launcher
from engine import Difficulty, InputManager
from engine.achievements import AchievementManager
from engine.ferret_sprite import AnimatedFerret
from engine.score_manager import ScoreManager
from engine.stats_manager import StatsManager
from games import BoulderDashGame, CentipedeGame, DigDugGame, FroggerGame, PacmanGame, SnakeGame
from games.boulderdash import TILE_DIAMOND, TILE_ROCK
from games.frogger import GRID, Lane
from games.pacman import Ghost, PEN_EXIT


def tap(controls, key):
    for kind in (pygame.KEYDOWN, pygame.KEYUP):
        controls.handle_event(pygame.event.Event(kind, key=key))


def test_power_bowl_route_and_newly_released_contact(screen):
    random.seed(19)
    controls = launcher.ScriptedInput()
    game = PacmanGame(screen, controls, Difficulty.NORMAL)
    route = [
        ((1, 0), 66),
        ((0, 1), 18),
        ((1, 0), 24),
        ((0, 1), 24),
        ((1, 0), 12),
        ((0, -1), 2),
        ((0, 0), 188),
    ]
    for direction, ticks in route:
        for _ in range(ticks):
            controls.feed(direction)
            game.advance(1 / 60)
    assert game.power_timer == 282 and game.lives == 3 and game.state == "playing"
    clyde = game.ghosts[-1]
    assert clyde.in_spawn
    for _ in range(80):
        game.advance(1 / 60)
        if not clyde.in_spawn:
            break
    assert not clyde.in_spawn and clyde.rect.center == PEN_EXIT
    assert all(h.mode == Ghost.MODE_FRIGHTENED for h in game.ghosts)
    game.player_x, game.player_y = clyde.rect.center
    game.player_dir = (0, 0)
    before = game.score
    game.advance(1 / 60)
    assert clyde.mode == Ghost.MODE_EATEN and game.score >= before + 200
    assert game.state == "playing" and game.lives == 3

    # The eyes travel home, wait, and emerge vulnerable to the same active bowl.
    reached_home = False
    for _ in range(300):
        clyde.update(game.walls, (40, 40), (1, 0), power_ticks=180)
        reached_home |= clyde.rect.center == clyde.spawn_pos
        if reached_home and not clyde.in_spawn:
            break
    assert reached_home and not clyde.in_spawn and clyde.mode == Ghost.MODE_FRIGHTENED
    assert clyde.rect.center == PEN_EXIT


@pytest.mark.parametrize("facing", [True, False])
def test_crossing_first_hop_hits_visible_paint(screen, facing):
    game = FroggerGame(screen, InputManager())
    lane = next(l for l in game.lanes if l.y == game.player_y - GRID)
    frame = pygame.Rect(game.player_x, lane.y, GRID, GRID)
    game.ferret.facing_right = facing
    game.ferret.set_state("jump")
    game.ferret.set_position(*frame.center)
    ferret = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    game.ferret.draw(ferret)
    body = pygame.mask.from_surface(ferret)
    paint = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    hits = 0
    for _ in range(120):
        lane.update()
        if lane.check_collision(frame)[0]:
            hits += 1
            paint.fill((0, 0, 0, 0))
            lane.draw_obstacles(paint)
            assert body.overlap(pygame.mask.from_surface(paint), (0, 0)) is not None
    assert 0 < hits < 120


def test_log_requires_center_footing_from_either_side():
    lane = Lane(3, "log", num_obstacles=1, obstacle_length=2, speed=-2)
    log = lane.obstacles[0].get_rect()
    frame = pygame.Rect(0, lane.y, GRID, GRID)
    for center, expected in (
        (log.left - 1, False),
        (log.left, True),
        (log.right - 1, True),
        (log.right, False),
    ):
        frame.centerx = center
        assert lane.check_collision(frame) == (False, expected, -2 if expected else 0)


def test_snake_scoring_awards_survive_back(screen):
    controls = InputManager()
    game = SnakeGame(screen, controls, Difficulty.HARD)
    for _ in range(10):
        x, y = game.snake[0]
        game.direction = (0, -1) if x >= 19 else (1, 0)
        game.food = x + game.direction[0], y + game.direction[1]
        game._move_snake()
    assert game.score == 100 and not game.playing_death
    tap(controls, pygame.K_ESCAPE)
    assert game.advance(1 / 60)
    game._track_session_stats()
    assert ScoreManager().get_high_score("snake", Difficulty.HARD) == 100
    assert all(
        AchievementManager().is_unlocked(key) for key in ("snake_hard_win", "snake_50", "snake_100")
    )


def test_defender_spider_badge_and_body_contact(screen):
    game = CentipedeGame(screen, InputManager())
    spider, shot = pygame.sprite.Sprite(), pygame.sprite.Sprite()
    spider.rect = shot.rect = pygame.Rect(250, 260, 4, 4)
    game.spiders.add(spider)
    game.bullets.add(shot)
    game.advance(1 / 60)
    assert game.score == 600 and game.wave == 1
    game._track_session_stats()
    assert AchievementManager().is_unlocked("centipede_500")
    game.spiders.add(spider)
    frame = game.player.get_rect()
    spider.rect = pygame.Rect(frame.left, frame.top, frame.width, 2)
    game.update(1 / 60)
    assert game.death_timer == 0
    spider.rect = AnimatedFerret.body_rect(frame)
    game.update(1 / 60)
    assert game.death_timer > 0


def test_game_loop_consumes_escape_once(screen, monkeypatch):
    controls = InputManager()
    game = SnakeGame(screen, controls)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE))

    # A bounded clock makes a failure deterministic even if the real display is fast.
    class Clock:
        def tick(self, fps):
            return 17

    game.clock = Clock()
    monkeypatch.setattr(
        launcher.engine, "scale_to_screen", lambda: pytest.fail("Escape should return in one step")
    )
    game.run()
    controls.update()
    assert not controls.back_pressed()


def test_focus_latch_requires_resume_and_ignores_idle_time(screen):
    controls = InputManager()
    game = SnakeGame(screen, controls, Difficulty.HARD)
    game.advance(0.25)
    assert game.play_ticks == 0
    tap(controls, pygame.K_RIGHT)
    game.advance(0.25)
    before = list(game.snake)
    active = game.play_ticks
    assert active > 0
    game._set_window_focus(False)
    tap(controls, pygame.K_p)
    for _ in range(10):
        game.advance(0.25)
    game._set_window_focus(True)
    for _ in range(10):
        game.advance(0.25)
    assert game.snake == before and game.play_ticks == active
    tap(controls, pygame.K_p)
    game.advance(1 / 60)
    game.advance(0.25)
    assert game.snake != before and game.play_ticks == active + 15
    game._track_session_stats()
    assert game.stats.get("global", "total_play_time") == pytest.approx((active + 15) / 60)
    assert not game.achievements.is_unlocked("dedicated")


@pytest.mark.parametrize("cls", [DigDugGame, BoulderDashGame])
def test_campaign_result_records_only_faster_clears(screen, cls):
    def finish(warmup, difficulty):
        controls = InputManager()
        game = cls(screen, controls, difficulty)
        for _ in range(warmup):
            game.advance(1 / 60)
        if cls is DigDugGame:
            game.level = game.max_levels
            game.enemies.empty()
            for gem in list(game.crystals):
                game.player_x, game.player_y = gem.rect.center
                game.advance(1 / 60)
            assert game.won
        else:
            game.current_level = game.max_levels
            game.diamonds_collected = game.diamonds_needed - 1
            game.score = 8500
            row, col = game.player_row, game.player_col + 1
            game.grid[row][col] = TILE_DIAMOND
            game.diamonds = [[row, col]]
            tap(controls, pygame.K_RIGHT)
            game.advance(1 / 60)
            assert game.game_won and game.score == 13100
        result = game._campaign_result()
        assert f"Lives left {game.lives}" in result[0]
        assert game.stats.format_clear(game.play_ticks) in result[1]
        game.render()
        game._track_session_stats()
        return game

    slow = finish(90, Difficulty.HARD)
    assert slow.new_clear_record
    faster = finish(40, Difficulty.HARD)
    assert faster.new_clear_record
    slower = finish(110, Difficulty.HARD)
    assert not slower.new_clear_record
    easy = finish(75, Difficulty.EASY)
    stats = StatsManager()
    assert stats.best_clear(easy.game_key, Difficulty.EASY) == easy.play_ticks
    assert stats.best_clear(easy.game_key, Difficulty.HARD) == faster.play_ticks
    incomplete = cls(screen, InputManager(), Difficulty.NORMAL)
    incomplete.advance(0.25)
    incomplete._track_session_stats()
    assert StatsManager().best_clear(easy.game_key, Difficulty.NORMAL) is None


@pytest.mark.parametrize("level", [2, 4])
def test_hard_chamber_really_requires_push_and_drop(screen, level):
    game = BoulderDashGame(screen, InputManager(), Difficulty.HARD)
    game.current_level = level
    game._generate_level(level)
    entrance = (6, 1)
    assert entrance in game._reachable_cells()
    game.player_row, game.player_col = entrance
    for _ in range(4):
        assert game._try_move(-1, 0)
    column = 6 if level == 2 else 5
    gem = (1, 6) if level == 2 else (2, 7)
    assert gem not in game._reachable_cells()
    while game.player_col < column:
        assert game._try_move(0, 1)
    assert game.grid[2][column + 1] == TILE_ROCK
    if level == 2:
        assert game._try_move(-1, 0)
    else:
        assert not game._try_move(0, 1)
        game.advance(8 / 60)
        assert not game._try_move(0, 1)
        game.advance(1 / 60)
        assert game.grid[3][column + 1] == TILE_ROCK
        assert game._try_move(0, 1)
        assert game._try_move(0, 1)
    assert (game.player_row, game.player_col) == gem
    assert game.diamonds_collected == 1 and game.lives == 3
    game._restore_level()
    assert game.grid[2][column] == TILE_ROCK and gem not in game._reachable_cells()


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher ownership")
def test_competing_launcher_cannot_overwrite_scores(tmp_path, screen):
    assert launcher.initialize(False) is not None
    launcher.get_score_manager().set_high_score("snake", 100, Difficulty.HARD)

    def run(code, profile=None):
        env = os.environ.copy()
        if profile:
            env["WES_DATA_DIR"] = str(profile)
        script = "import game_launcher as g\nfrom engine import Difficulty\n" + code
        result = subprocess.run(
            [sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=20
        )
        assert result.returncode == 0, result.stderr

    try:
        run("assert g.initialize(False) is None\nassert g.input_manager is None\ng.cleanup()")
        run("assert g.initialize(False) is not None\ng.cleanup()", tmp_path / "other")
    finally:
        launcher.cleanup()
    run(
        "assert g.initialize(False) is not None\ns=g.get_score_manager()\nassert s.get_high_score('snake', Difficulty.HARD)==100\ns.set_high_score('digdug', 600, Difficulty.NORMAL)\ng.cleanup()"
    )
    scores = ScoreManager()
    assert scores.get_high_score("snake", Difficulty.HARD) == 100
    assert scores.get_high_score("digdug", Difficulty.NORMAL) == 600


def test_switching_windows_in_running_snake_requires_a_fresh_resume(screen, monkeypatch):
    controls = InputManager()
    game = SnakeGame(screen, controls, Difficulty.HARD)
    game.stats.set("global", "total_play_time", 3599)

    def key(k):
        return [pygame.event.Event(kind, key=k) for kind in (pygame.KEYDOWN, pygame.KEYUP)]

    frames = (
        [
            key(pygame.K_RIGHT),
            [pygame.event.Event(pygame.WINDOWFOCUSLOST)],
            key(pygame.K_p),
            [pygame.event.Event(pygame.WINDOWFOCUSGAINED)],
        ]
        + [[] for _ in range(120)]
        + [key(pygame.K_p)]
        + [[] for _ in range(7)]
        + [key(pygame.K_ESCAPE)]
    )
    events = iter(frames)
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))

    class Clock:
        def tick(self, fps):
            return 17

    game.clock = Clock()
    snapshots = []
    monkeypatch.setattr(
        launcher.engine,
        "scale_to_screen",
        lambda: snapshots.append((game.snake[0], game.play_ticks)),
    )
    game.run()
    assert len(set(snapshots[1:124])) == 1
    assert snapshots[-1][0] != snapshots[1][0]
    assert 1 < game.play_ticks < 10 and not game.game_over
    assert not game.achievements.is_unlocked("dedicated")
