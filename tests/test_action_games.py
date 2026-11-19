"""Regression scenarios for the three action games in the November audit."""

import math
import random

import pygame
import pytest

from engine import Difficulty
from games.centipede import CentipedeGame, CentipedeSegment, Flea
from games.digdug import DigDugGame, Enemy, GRID_ROWS as D_ROWS, GRID_COLS as D_COLS
from games.boulderdash import (
    BoulderDashGame,
    BouncyRock,
    TILE_EMPTY,
    TILE_WALL,
    TILE_ROCK,
    TILE_DIAMOND,
    GRID_ROWS,
    GRID_COLS,
    TILE_SIZE,
)


class Controls:
    demo_mode = False
    direction = (0, 0)
    action = False
    pause = False
    back = False

    def update(self):
        pass

    def get_dpad(self):
        return self.direction

    def action_pressed(self):
        return self.action

    def get_any_action_button(self):
        return self.action

    def pause_pressed(self):
        return self.pause

    def back_pressed(self):
        return self.back


def empty_cave(game):
    game.grid = [
        [
            TILE_WALL if r in (0, GRID_ROWS - 1) or c in (0, GRID_COLS - 1) else TILE_EMPTY
            for c in range(GRID_COLS)
        ]
        for r in range(GRID_ROWS)
    ]
    game.rocks = []
    game.diamonds = []
    game.sparkles = {}
    game.bouncy_rocks = {}
    game.falling_states = {}
    game.player_row, game.player_col = 10, 10
    game._update_ferret_visual_position()


def test_centipede_final_death_preserves_score_and_restarts_cleanly(screen):
    controls = Controls()
    game = CentipedeGame(screen, controls)
    game.score, game.lives = 777, 1
    game._centipedes_destroyed, game._spiders_killed = 8, 2
    game._player_death()
    for _ in range(20):
        game.update(1 / 60)
    assert game.player.current_frame > 0
    for _ in range(60):
        game.update(1 / 60)
    assert game.game_over and game.lives == 0 and game.score == 777
    assert game.stats.get("centipede", "centipedes_destroyed") == 8
    controls.action = True
    game.handle_input()
    assert not game.game_over and game.lives == 3 and game.score == 0
    assert not game.new_high_score and game._deaths == 0
    assert game._centipedes_destroyed == game._spiders_killed == 0
    assert game.stats.get("centipede", "games_played") == 2


def test_centipede_segments_stay_visible_through_repeated_bounces(screen):
    sprite = pygame.Surface((16, 16))
    segment = CentipedeSegment(780, 580, [sprite], [sprite], speed=6)
    for _ in range(15000):
        segment.update()
        assert 0 <= segment.rect.left and segment.rect.right <= 800
        assert 40 <= segment.rect.top and segment.rect.bottom <= 600


def test_centipede_held_action_has_one_fire_cadence_for_all_inputs(screen):
    controls = Controls()
    controls.action = True
    controls.direction = (1, 1)
    game = CentipedeGame(screen, controls)
    game.soup_bowls.empty()
    game.handle_input()
    game.update(1 / 60)
    assert len(game.bullets) == 1
    game.handle_input()
    game.update(1 / 60)
    assert len(game.bullets) == 1
    for _ in range(500):
        game.handle_input()
        game.update(1 / 60)
    assert game.player.get_rect().right <= 800
    assert game.player.get_rect().bottom <= 600


def test_centipede_wave_ramps_and_records_completion(screen):
    game = CentipedeGame(screen, Controls())
    initial = game.centipede_speed
    for _ in range(2):
        game.centipede.empty()
        game.update(1 / 60)
    assert game.wave == 3 and game.centipede_speed > initial
    assert len(game.centipede) > game.DIFFICULTY_PRESETS[game.difficulty]["centipede_segments"]
    assert game.stats.get("global", "games_completed") == 2


def test_centipede_soup_bowls_are_capped_and_deduplicated(screen):
    game = CentipedeGame(screen, Controls())
    for row in range(30):
        for col in range(40):
            game._add_soup_bowl(col * 16, row * 16)
    assert len(game.soup_bowls) == game.MAX_SOUP_BOWLS
    flea = Flea(200, 0, game.flea_sprite)
    for _ in range(160):
        flea.update(game.soup_bowls, game.soup_bowl_sprites, game.MAX_SOUP_BOWLS)
    assert len(game.soup_bowls) == game.MAX_SOUP_BOWLS


def test_decoration_rng_does_not_reseed_gameplay(screen):
    game = CentipedeGame(screen, Controls())
    random.seed(512)
    state = random.getstate()
    game._generate_garden()
    assert random.getstate() == state


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_digger_spawn_separation_and_progression(screen, difficulty):
    game = DigDugGame(screen, Controls(), difficulty)
    for enemy in game.enemies:
        assert not any(enemy.rect.colliderect(b.rect) for b in game.boulders)
    game.enemies.empty()
    for crystal in list(game.crystals):
        game.player_x, game.player_y = crystal.rect.center
        game.update(1 / 60)
    assert game.level_complete and game.score == 800
    for _ in range(90):
        game.update(1 / 60)
    assert game.level == 2 and game.crystals_needed == 4 and game.score == 800
    assert game.enemy_count > game.DIFFICULTY_PRESETS[difficulty]["enemy_count"]


def test_digger_enemy_respects_dirt_and_rock(screen):
    sprite = pygame.Surface((28, 28))
    enemy = Enemy(200, 200, sprite)
    terrain = [[True] * D_COLS for _ in range(D_ROWS)]
    original = enemy.rect.copy()
    for _ in range(100):
        enemy.update(terrain)
    assert enemy.rect == original
    terrain = [[False] * D_COLS for _ in range(D_ROWS)]
    obstacle = pygame.sprite.Sprite()
    obstacle.rect = pygame.Rect(190, 190, 70, 70)
    enemy.update(terrain, [obstacle])
    assert enemy.rect == original
    enemy.update(terrain)
    assert enemy.rect != original


def test_digger_diagonal_speed_and_collection_animation(screen):
    controls = Controls()
    controls.direction = (1, 1)
    game = DigDugGame(screen, controls)
    game.enemies.empty()
    game.boulders.empty()
    game.handle_input()
    before = (game.player_x, game.player_y)
    game.update(1 / 60)
    assert math.hypot(game.player_x - before[0], game.player_y - before[1]) == pytest.approx(4)
    crystal = next(iter(game.crystals))
    controls.direction = (0, 0)
    game.handle_input()
    game.player_x, game.player_y = crystal.rect.center
    game.update(1 / 60)
    for _ in range(10):
        game.update(1 / 60)
    assert game.ferret.state == "emerge" and game.ferret.current_frame > 0


def test_digger_three_lives_and_clean_restart(screen):
    controls = Controls()
    game = DigDugGame(screen, controls)
    game.enemies.empty()
    enemy = Enemy(186, 186, game.enemy_img)
    game.enemies.add(enemy)
    game.lives = 1
    game.invulnerable_timer = 0
    game.score = 900
    game.update(1 / 60)
    for _ in range(20):
        game.update(1 / 60)
    assert game.ferret.current_frame > 0 and game.game_over
    for _ in range(60):
        game.update(1 / 60)
    assert game.score == 900
    controls.action = True
    game.handle_input()
    assert game.lives == 3 and game.level == 1 and game.score == 0
    assert game._deaths == 0 and not game.new_high_score


@pytest.mark.parametrize("tile", [TILE_ROCK, TILE_DIAMOND])
def test_boulder_resting_objects_do_not_crush_but_falling_objects_do(screen, tile):
    game = BoulderDashGame(screen, Controls())
    empty_cave(game)
    objects = game.rocks if tile == TILE_ROCK else game.diamonds
    objects.append([9, 10])
    game.grid[9][10] = tile
    game._update_falling_objects()
    assert not game.is_dying and objects == [[9, 10]]
    objects[0][0] = 8
    game.grid[9][10] = TILE_EMPTY
    game.grid[8][10] = tile
    game._update_falling_objects()
    assert not game.is_dying and objects == [[9, 10]]
    game._update_falling_objects()
    assert game.is_dying


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_boulder_generated_objectives_reachable_and_spawn_safe(screen, difficulty):
    game = BoulderDashGame(screen, Controls(), difficulty)
    for seed in range(60):
        for level in range(1, 6):
            random.seed(seed * 7 + level)
            game._generate_level(level)
            assert game.grid[game.player_row - 1][game.player_col] not in (TILE_ROCK, TILE_DIAMOND)
            assert len(game.diamonds) == game.diamonds_needed
            gated = int(difficulty == Difficulty.HARD and level in (2, 4))
            reachable = game._reachable_cells()
            assert sum(tuple(d) not in reachable for d in game.diamonds) == gated
            for _ in range(20):
                game._update_falling_objects()
            reachable = game._reachable_cells()
            assert sum(tuple(d) not in reachable for d in game.diamonds) == gated


@pytest.mark.parametrize("seed", [676, 931])
def test_boulder_idle_gravity_preserves_spawn_escape_routes(screen, seed):
    game = BoulderDashGame(screen, Controls(), Difficulty.HARD)
    random.seed(seed)
    game._generate_level(4)
    original = [row[:] for row in game.grid]
    for _ in range(20):
        game._update_falling_objects()
    assert game.grid == original
    reachable = game._reachable_cells()
    assert [tuple(d) for d in game.diamonds if tuple(d) not in reachable] == [(2, 7)]
    assert any(
        game.grid[game.player_row + dr][game.player_col + dc] not in (TILE_WALL, TILE_ROCK)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
    )


def test_boulder_gravity_is_timed_and_bottom_to_top(screen):
    game = BoulderDashGame(screen, Controls())
    empty_cave(game)
    game.rocks = [[5, 5], [6, 5]]
    game.grid[5][5] = game.grid[6][5] = TILE_ROCK
    for _ in range(8):
        game.update(1 / 60)
    assert game.rocks == [[5, 5], [6, 5]]
    game.update(1 / 60)
    assert game.rocks == [[6, 5], [7, 5]]


def test_boulder_moves_sync_visuals_and_refuse_terminal_states(screen):
    game = BoulderDashGame(screen, Controls())
    empty_cave(game)
    assert game._try_move(0, 1)
    assert game.ferret.x == (game.player_col + 0.5) * TILE_SIZE
    assert game.ferret.y == (game.player_row + 0.5) * TILE_SIZE
    for flag in ("is_dying", "level_complete", "game_over", "game_won", "paused"):
        setattr(game, flag, True)
        assert not game._try_move(0, 1)
        setattr(game, flag, False)
    assert not game._try_move(1, 1)


def test_boulder_push_removes_stale_fall_state(screen):
    game = BoulderDashGame(screen, Controls())
    empty_cave(game)
    game.rocks = [[10, 11]]
    game.grid[10][11] = TILE_ROCK
    game.falling_states[(10, 11)] = True
    game.bouncy_rocks[(10, 11)] = BouncyRock(10, 11)
    assert game._try_move(0, 1)
    assert game.rocks == [[10, 12]]
    assert (10, 11) not in game.falling_states and (10, 11) not in game.bouncy_rocks
    assert (10, 12) in game.bouncy_rocks


def test_boulder_death_preserves_cave_and_treasure(screen):
    game = BoulderDashGame(screen, Controls())
    game.score, game.diamonds_collected, game._total_diamonds = 300, 3, 3
    grid = [row[:] for row in game.grid]
    game._start_death()
    for _ in range(60):
        game.update(1 / 60)
    assert game.lives == 2 and not game.is_dying
    assert game.score == 300 and game.diamonds_collected == 3
    assert game.grid == grid


def test_boulder_repeat_and_diagonal_input(screen):
    controls = Controls()
    controls.direction = (1, 0)
    game = BoulderDashGame(screen, controls)
    empty_cave(game)
    for _ in range(17):
        game.handle_input()
        game.update(1 / 60)
    assert game.player_col == 13
    controls.direction = (1, 1)
    for _ in range(20):
        game.handle_input()
        game.update(1 / 60)
    assert (game.player_row, game.player_col) == (10, 13)


def test_boulder_restart_resets_session_and_retry_restores_layout(screen):
    controls = Controls()
    game = BoulderDashGame(screen, controls)
    blueprint = [row[:] for row in game.grid]
    game.score = 100
    game.diamonds_collected = game._total_diamonds = 1
    game.paused = True
    controls.action = True
    game.handle_input()
    assert game.lives == 2 and game.grid == blueprint
    assert game.score == game.diamonds_collected == game._total_diamonds == 0
    game.game_over = True
    game.new_high_score = True
    game._levels_completed = 4
    game.handle_input()
    assert game.lives == 3 and game.current_level == 1 and not game.new_high_score
    assert game._deaths_this_level == game._levels_completed == game._deaths == 0


@pytest.mark.parametrize("cls", [CentipedeGame, DigDugGame, BoulderDashGame])
def test_steady_state_render_allocates_no_surfaces(screen, monkeypatch, cls):
    game = cls(screen, Controls())
    game.render()  # Populate bounded lazy caches.
    original = pygame.Surface
    allocations = []

    def surface(*args, **kwargs):
        allocations.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(pygame, "Surface", surface)
    for _ in range(30):
        game.update(1 / 60)
        game.render()
    assert allocations == []
