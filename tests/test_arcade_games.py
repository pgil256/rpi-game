"""Regressions for Snake, Tunnel Treats and Ferret Crossing."""

import random
import pygame
import pytest
from engine import BaseGame, Difficulty
from engine.persistence import persistence_session
from games.snake import SnakeGame, GRID_WIDTH, GRID_HEIGHT, FIRST_PLAY_ROW
from games.pacman import PacmanGame
from games.frogger import FroggerGame, GRID, PLAY_AREA_OFFSET_Y


class ScriptedInput:
    direction = (0, 0)
    confirm = False
    pause = False
    back = False

    def update(self):
        pass

    def get_dpad(self):
        return self.direction

    def back_pressed(self):
        return self.back

    def pause_pressed(self):
        return self.pause

    def confirm_pressed(self):
        return self.confirm

    def action_pressed(self):
        return self.confirm


@pytest.mark.parametrize("cls", [SnakeGame, PacmanGame, FroggerGame])
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_arcade_plays_300_frames(screen, cls, difficulty):
    controls = ScriptedInput()
    with persistence_session(demo=True, difficulty=difficulty):
        game = cls(screen, controls, difficulty)
        for frame in range(300):
            controls.confirm = frame == 0
            controls.direction = ((1, 0), (0, -1), (-1, 0), (0, 1))[(frame // 45) % 4]
            assert game.handle_input() is False
            game.update(1 / 60)
            game.render()
        assert game.difficulty is difficulty
        if cls is FroggerGame:
            assert game.state != "START"
        if cls is SnakeGame:
            assert not game.waiting_for_input


def test_snake_shared_loop_and_movement_remainder(screen, monkeypatch):
    assert SnakeGame.run is BaseGame.run
    game = SnakeGame(screen, ScriptedInput())
    game.waiting_for_input = False
    game.food = None
    start = game.snake[0]
    moves = []
    move = game._move_snake

    def counted_move():
        moves.append(1)
        move()

    monkeypatch.setattr(game, "_move_snake", counted_move)
    for _ in range(600):
        game.update(1 / 60)
    assert len(moves) == 100
    assert game.snake[0] == ((start[0] + 100) % GRID_WIDTH, start[1])
    assert abs(game.move_timer) < 1e-8


def test_snake_two_turn_queue(screen):
    controls = ScriptedInput()
    game = SnakeGame(screen, controls)
    controls.direction = (0, -1)
    game.handle_input()
    controls.direction = (-1, 0)
    game.handle_input()
    assert list(game.turn_queue) == [(0, -1), (-1, 0)]
    start = game.snake[0]
    game.update(0.1)
    game.update(0.1)
    assert game.snake[0] == (start[0] - 1, start[1] - 1)
    assert game.ferret.state == "movement"


def test_snake_food_does_not_block_movement(screen):
    controls = ScriptedInput()
    game = SnakeGame(screen, controls)
    game.waiting_for_input = False
    x, y = game.snake[0]
    game.food = (x + 1, y)
    game.update(0.1)
    assert game.score == 10 and game.playing_dig
    controls.direction = (0, -1)
    game.handle_input()
    game.update(0.1)
    assert game.snake[0] == (x + 1, y - 1)


def test_snake_food_excludes_hud_and_full_board_terminates(screen):
    game = SnakeGame(screen, ScriptedInput())
    for _ in range(100):
        assert game._spawn_food()[1] >= FIRST_PLAY_ROW
    game.snake = [(x, y) for x in range(GRID_WIDTH) for y in range(FIRST_PLAY_ROW, GRID_HEIGHT)]
    assert game._spawn_food() is None


def test_snake_growth_increases_speed(screen):
    game = SnakeGame(screen, ScriptedInput())
    game.waiting_for_input = False
    baseline = game.move_delay
    for _ in range(5):
        x, y = game.snake[0]
        game.food = ((x + 1) % GRID_WIDTH, y)
        game.update(game.move_delay)
    assert game.move_delay < baseline and len(game.snake) == 8


def test_decorations_preserve_game_rng(screen):
    for cls, method in (
        (SnakeGame, "_generate_background"),
        (FroggerGame, "_generate_decorations"),
    ):
        game = cls(screen, ScriptedInput())
        state = random.getstate()
        getattr(game, method)()
        assert random.getstate() == state


def test_pacman_clear_preserves_score_and_advances(screen):
    game = PacmanGame(screen, ScriptedInput(), Difficulty.HARD)
    game.score = 2340
    game.ghosts = []
    game.pellets.empty()
    game.power_pellets.empty()
    with persistence_session(difficulty=Difficulty.HARD):
        game.update(1 / 60)
        assert game.score == 2340 and game.state == "level_complete"
        assert game.score_manager.get_high_score("pacman", Difficulty.HARD) == 2340
        for _ in range(90):
            game.update(1 / 60)
    assert game.score == 2340 and game.level == 2 and game.ghost_speed > 3
    assert len(game.pellets) > 0
    assert game.achievements.is_unlocked("pacman_1000")


def test_pacman_gameover_and_restart(screen):
    controls = ScriptedInput()
    game = PacmanGame(screen, controls)
    game.score, game.lives = 1250, 1
    game._start_death()
    for _ in range(120):
        game.update(1 / 60)
    assert game.state == "game_over" and game.score == 1250 and game.lives == 0
    assert game.stats.get("pacman", "deaths") == 1
    game.render()
    controls.confirm = True
    game.handle_input()
    assert game.score == 0 and game.lives == 3 and game.level == 1
    assert game.state == "playing" and not game.new_high_score


def test_pacman_ghost_hitbox_is_forgiving(screen):
    game = PacmanGame(screen, ScriptedInput())
    game.player_dir = (0, 0)
    ghost = game.ghosts[0]
    ghost.in_spawn = False
    ghost.update = lambda *args, **kwargs: None
    ghost.rect.center = (round(game.player_x) + 26, round(game.player_y))
    game.ghosts = [ghost]
    game.update(1 / 60)
    assert game.state == "playing"
    ghost.rect.center = (round(game.player_x) + 10, round(game.player_y))
    game.update(1 / 60)
    assert game.state == "dying"


def test_pacman_ghost_effects_reuse_surfaces(screen):
    game = PacmanGame(screen, ScriptedInput())
    ghost = game.ghosts[0]
    ghost.in_spawn = False
    ghost.set_frightened(300)
    ghost.update(game.walls, (300, 400), (1, 0))
    assert any(ghost.image is image for image in ghost._tinted_images.values())
    ghost.get_eaten()
    ghost.update(game.walls, (300, 400), (1, 0))
    assert ghost.image is ghost._eyes_image


def test_frogger_buffers_taps_through_respawn(screen):
    controls = ScriptedInput()
    game = FroggerGame(screen, controls)
    game.state, game.is_respawning, game.respawn_timer = "PLAY", True, 3
    controls.direction = (1, 0)
    game.handle_input()
    controls.direction = (0, 0)
    game.handle_input()
    start = game.player_x
    assert list(game.pending_hops) == [(1, 0)]
    for _ in range(3):
        game.update(1 / 60)
    assert game.player_x == start + GRID and game.is_jumping


def test_frogger_death_animation_and_gameover(screen):
    game = FroggerGame(screen, ScriptedInput())
    game.state, game.lives = "PLAY", 1
    game._start_death()
    frame = game.ferret._frame
    for _ in range(8):
        game.update(1 / 60)
    assert game.ferret._frame != frame
    for _ in range(37):
        game.update(1 / 60)
    assert game.state == "GAMEOVER" and game.lives == 0


def test_frogger_progress_and_restart_counters(screen):
    controls = ScriptedInput()
    game = FroggerGame(screen, controls)
    game.state = "PLAY"
    speed = game.lanes[1].obstacles[0].speed
    for _ in range(5):
        game.is_respawning = False
        game.player_y = GRID + PLAY_AREA_OFFSET_Y
        game.highest_row = 12
        game.update(1 / 60)
    assert game.level == 2 and game.crossings_this_level == 0
    assert game.lanes[1].obstacles[0].speed > speed
    assert game.stats.get("global", "games_completed") == 1
    game._deaths, game.new_high_score, game.state = 9, True, "GAMEOVER"
    controls.confirm = True
    game.handle_input()
    assert (game._deaths, game._crossings, game.level, game.score) == (0, 0, 1, 0)
    assert not game.new_high_score


@pytest.mark.parametrize("cls", [SnakeGame, PacmanGame, FroggerGame])
def test_arcade_render_reuses_effect_surfaces(screen, monkeypatch, cls):
    game = cls(screen, ScriptedInput())
    if cls is FroggerGame:
        game.state = "PLAY"
    game.render()
    real_surface, allocations = pygame.Surface, []

    def counted_surface(*args, **kwargs):
        allocations.append(args)
        return real_surface(*args, **kwargs)

    monkeypatch.setattr(pygame, "Surface", counted_surface)
    game.render()
    assert not allocations
