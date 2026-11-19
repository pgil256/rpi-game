"""
Crystal Quest - A Winston Entertainment System Game

The MOST thematically appropriate game for a ferret - they literally dig!
Navigate underground tunnels, collect crystals, and avoid enemies.

This game uses the AnimatedFerret sprite with proper animations:
- DIG animation while moving (ferret is always digging through dirt)
- IDLE when stationary
- DEATH on enemy collision
- EMERGE when collecting a crystal

Features:
- Procedurally generated underground dirt that the ferret digs through
- Trail of tunnels left behind as the ferret moves
- Three depths with increasing crystal targets
- Tunnel-bound enemies and three lives
- Boulder obstacles that block movement
"""

import pygame
from engine.asset_loader import gem_sprite
import random

from engine import (
    BaseGame,
    AnimatedFerret,
    AudioManager,
    Difficulty,
    get_score_manager,
    get_stats_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WHITE,
    GREEN,
)


# Grid and terrain constants
CELL_SIZE = 25  # Size of each terrain cell
GRID_COLS = WINDOW_WIDTH // CELL_SIZE
GRID_ROWS = WINDOW_HEIGHT // CELL_SIZE

# Enhanced cute underground theme colors
DIRT_DARK = (80, 55, 35)  # Softer dark brown
DIRT_MID = (120, 85, 55)  # Warmer medium brown
DIRT_LIGHT = (180, 145, 100)  # Softer light brown
DIRT_ACCENT = (100, 70, 45)  # Accent color for depth
TUNNEL_COLOR = (40, 30, 25)  # Deep tunnel color
TUNNEL_GLOW = (60, 45, 35)  # Subtle tunnel edge glow
ROCK_COLOR = (100, 95, 105)  # Slightly purple-gray rocks
ROCK_HIGHLIGHT = (130, 125, 135)  # Rock highlights
CRYSTAL_GLOW = (180, 240, 255)  # Softer cyan glow
CRYSTAL_SPARKLE = (255, 255, 220)  # Crystal sparkle
GEM_COLORS = [
    (180, 240, 255),  # Cyan
    (255, 200, 220),  # Pink
    (200, 255, 200),  # Mint
]

# Particle colors for cute effects
SPARKLE_GOLD = (255, 220, 150)
DUST_COLOR = (160, 130, 100)

import math

# Entity sizes
ENTITY_SIZE = 32
PLAYER_HITBOX = 28
PLAYER_SPEED = 4


class Crystal(pygame.sprite.Sprite):
    """A collectible crystal that the ferret must gather."""

    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(x=x, y=y)
        self.glow_timer = 0
        # Sparkle positions around the crystal
        self._sparkles = []
        for _ in range(4):
            sx = random.randint(-15, 15)
            sy = random.randint(-15, 15)
            phase = random.uniform(0, 6.28)
            self._sparkles.append((sx, sy, phase))

    def update(self):
        """Update crystal animation (subtle glow effect)."""
        self.glow_timer += 1

    _glow_frames = None

    def draw(self, surface):
        """Reuse a bounded glow animation instead of allocating every frame."""
        if Crystal._glow_frames is None:
            Crystal._glow_frames = []
            for frame in range(24):
                pulse = abs(math.sin(frame * math.pi / 24))
                glow = pygame.Surface((90, 90), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow, (*CRYSTAL_GLOW, int(60 + pulse * 40)), (45, 45), int(35 + pulse * 10)
                )
                pygame.draw.circle(glow, (*CRYSTAL_SPARKLE, 100), (45, 45), 23)
                Crystal._glow_frames.append(glow)
        surface.blit(
            Crystal._glow_frames[(self.glow_timer // 2) % 24],
            (self.rect.centerx - 45, self.rect.centery - 45),
        )
        for sx, sy, phase in self._sparkles:
            if abs(math.sin(self.glow_timer * 0.12 + phase)) > 0.7:
                x, y = self.rect.centerx + sx, self.rect.centery + sy
                pygame.draw.line(surface, CRYSTAL_SPARKLE, (x - 3, y), (x + 3, y), 2)
                pygame.draw.line(surface, CRYSTAL_SPARKLE, (x, y - 3), (x, y + 3), 2)
        surface.blit(self.image, self.rect)


class Boulder(pygame.sprite.Sprite):
    """A boulder that blocks movement."""

    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(x=x, y=y)

    def draw(self, surface):
        """Draw the boulder."""
        surface.blit(self.image, self.rect)


class Enemy(pygame.sprite.Sprite):
    """An enemy that roams the tunnels."""

    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(x=x, y=y)
        self.dx = random.choice([-2, 2])
        self.dy = 0
        self.change_timer = 0

    def update(self, terrain=None, boulders=(), bounds_top=100, speed=2):
        """Patrol excavated cells; dirt and boulders block enemy movement."""
        self.change_timer += 1
        directions = [(-speed, 0), (speed, 0), (0, -speed), (0, speed)]
        current = (
            (int(math.copysign(speed, self.dx)), 0)
            if self.dx
            else (0, int(math.copysign(speed, self.dy or 1)))
        )
        if self.change_timer % 45 == 0:
            random.shuffle(directions)
        else:
            directions = [current] + [d for d in directions if d != current]
        for dx, dy in directions:
            candidate = self.rect.move(dx, dy)
            if (
                candidate.left < 0
                or candidate.right > WINDOW_WIDTH
                or candidate.top < bounds_top
                or candidate.bottom > WINDOW_HEIGHT
            ):
                continue
            if any(candidate.colliderect(b.rect) for b in boulders):
                continue
            if terrain is not None:
                cells = (
                    (row, col)
                    for row in range(
                        candidate.top // CELL_SIZE, (candidate.bottom - 1) // CELL_SIZE + 1
                    )
                    for col in range(
                        candidate.left // CELL_SIZE, (candidate.right - 1) // CELL_SIZE + 1
                    )
                )
                if any(terrain[row][col] for row, col in cells):
                    continue
            self.rect = candidate
            self.dx, self.dy = dx, dy
            return

    def draw(self, surface):
        """Draw the enemy."""
        surface.blit(self.image, self.rect)


class DigDugGame(BaseGame):
    """Ferret Digger - Dig tunnels and collect crystals underground!

    Controls:
    - D-pad/Arrow keys: Move the ferret (continuous digging movement)
    - B/ESC: Return to menu

    Dig routes through three depths, collecting each crystal target while
    avoiding tunnel-bound enemies and boulders. Three lives per expedition.
    """

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            "enemy_count": 1,  # Just 1 enemy
        },
        Difficulty.NORMAL: {
            "enemy_count": 2,  # 2 enemies (default)
        },
        Difficulty.HARD: {
            "enemy_count": 4,  # 4 enemies
        },
    }

    def setup(self):
        """Prepare reusable artwork, then start a fresh expedition."""
        self.font = pygame.font.Font(None, 30)
        self._load_sprites()
        self.score_manager = get_score_manager()
        self.stats = get_stats_manager()
        self.high_score = self.score_manager.get_high_score("digdug", difficulty=self.difficulty)
        self.ferret = AnimatedFerret(x=200, y=200, scale=1, speed=0, frame_delay=4)
        self.ferret.set_sprite_size(32)
        self._hud_surface = pygame.Surface((WINDOW_WIDTH, 40), pygame.SRCALPHA)
        for y in range(40):
            pygame.draw.line(
                self._hud_surface, (30, 25, 20, 180 - y * 2), (0, y), (WINDOW_WIDTH, y)
            )
        self._reset_game(count_session=False)

    def _load_sprites(self):
        """Load game sprites with fallbacks."""
        self.crystal_img = gem_sprite(ENTITY_SIZE)

        # Original underground beetle, rendered procedurally.
        self.enemy_img = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(self.enemy_img, (180, 90, 125), (2, 3, 24, 22))
        pygame.draw.line(self.enemy_img, (90, 40, 65), (14, 5), (14, 24), 2)
        for x in (9, 19):
            pygame.draw.circle(self.enemy_img, WHITE, (x, 8), 4)
            pygame.draw.circle(self.enemy_img, (35, 25, 40), (x, 8), 2)

        # Boulder
        self.boulder_img = self._create_boulder_sprite()

    def _create_boulder_sprite(self):
        """Create a boulder sprite with rocky texture."""
        size = ENTITY_SIZE
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        # Main rock shape
        pygame.draw.ellipse(surface, ROCK_COLOR, (2, 2, size - 4, size - 4))

        # Add some texture/shading
        pygame.draw.ellipse(surface, (70, 70, 80), (5, 5, size - 15, size - 15), 2)
        pygame.draw.ellipse(surface, (110, 110, 120), (size // 3, size // 4, size // 4, size // 4))

        return surface.convert_alpha()  # Convert for optimal blitting

    def _create_terrain(self):
        """Create the underground terrain grid."""
        self._terrain_dirty = {(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)}
        self._terrain_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
        self.terrain = [[True for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

        # Create some random dirt texture variations for visual interest
        self.dirt_texture = []
        for row in range(GRID_ROWS):
            row_data = []
            for col in range(GRID_COLS):
                # Random dirt shade
                shade = random.choice([DIRT_DARK, DIRT_MID, DIRT_LIGHT])
                # Occasionally add small rock specs
                has_rock = random.random() < 0.1
                row_data.append((shade, has_rock))
            self.dirt_texture.append(row_data)

    def _create_entities(self):
        """Place separated objectives/hazards with new layouts at each depth."""
        self.crystals = pygame.sprite.Group()
        self.boulders = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        cells = [(x, y) for y in range(275, 526, 75) for x in range(75, 726, 75)]
        random.shuffle(cells)
        occupied = [pygame.Rect(160, 160, 80, 80)]

        def position():
            while cells:
                x, y = cells.pop()
                rect = pygame.Rect(x, y, ENTITY_SIZE, ENTITY_SIZE)
                if not any(rect.inflate(30, 30).colliderect(other) for other in occupied):
                    occupied.append(rect)
                    return x, y
            raise RuntimeError("No safe entity spawn positions remain")

        for _ in range(3 + self.level):
            x, y = position()
            self.boulders.add(Boulder(x, y, self.boulder_img))
        for _ in range(self.crystals_needed):
            x, y = position()
            self.crystals.add(Crystal(x, y, self.crystal_img))
            self._dig_tunnel(x + ENTITY_SIZE // 2, y + ENTITY_SIZE // 2, radius=35)
        for _ in range(self.enemy_count):
            x, y = position()
            self.enemies.add(Enemy(x, y, self.enemy_img))
            # Each beetle starts in a small burrow. Digging connects these patrol
            # areas to the player's tunnels, so routes change the encounter.
            for tunnel_x in range(max(25, x - 75), min(WINDOW_WIDTH - 25, x + 76), 20):
                self._dig_tunnel(tunnel_x, y + 14, radius=35)

    def _dig_tunnel(self, x, y, radius=20):
        """Dig out a circular area in the terrain."""
        center_col = x // CELL_SIZE
        center_row = y // CELL_SIZE
        cells_radius = radius // CELL_SIZE + 1
        cleared = False

        for row in range(
            max(0, center_row - cells_radius), min(GRID_ROWS, center_row + cells_radius + 1)
        ):
            for col in range(
                max(0, center_col - cells_radius), min(GRID_COLS, center_col + cells_radius + 1)
            ):
                # Check if within circular radius
                dx = (col * CELL_SIZE + CELL_SIZE // 2) - x
                dy = (row * CELL_SIZE + CELL_SIZE // 2) - y
                if dx * dx + dy * dy <= radius * radius:
                    if self.terrain[row][col]:
                        cleared = True
                        self.terrain[row][col] = False
                        self._terrain_dirty.add((row, col))
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            if 0 <= row + dr < GRID_ROWS and 0 <= col + dc < GRID_COLS:
                                self._terrain_dirty.add((row + dr, col + dc))
        return cleared

    def _reset_game(self, count_session=True):
        if count_session:
            self.restart_session()
        self.score = 0
        self.level = 1
        self.max_levels = 3
        self.lives = 3
        self.new_high_score = False
        self._deaths = 0
        self._total_crystals = 0
        self._session_recorded = False
        self.game_over = False
        self.won = False
        self.paused = False
        self._start_level()

    def _start_level(self):
        self.crystals_needed = 2 + self.level
        self.crystals_collected = 0
        self.enemy_count = min(
            8, self.DIFFICULTY_PRESETS[self.difficulty]["enemy_count"] + self.level - 1
        )
        self.level_complete = False
        self.transition_timer = 0
        self.death_timer = 0
        self.special_timer = 40
        self.invulnerable_timer = 90
        self.player_x = 200.0
        self.player_y = 200.0
        self.last_dx = self.last_dy = 0
        self.moving = False
        self._create_terrain()
        self._create_entities()
        self._dig_tunnel(200, 200, radius=40)
        self.ferret.set_position(200, 200)
        self.ferret.set_state("emerge")

    def handle_input(self):
        self.input_manager.update()
        if self.input_manager.back_pressed():
            return True
        if self.game_over or self.won:
            if self.death_timer == 0 and self.input_manager.action_pressed():
                self._reset_game()
            return False
        if self.input_manager.pause_pressed() and self.death_timer == 0:
            self.paused = not self.paused
        self.last_dx, self.last_dy = self.input_manager.get_dpad()
        self.moving = bool(self.last_dx or self.last_dy)
        return False

    def _finish_session(self):
        if self._session_recorded:
            return
        self._session_recorded = True
        if self.score_manager.set_high_score("digdug", self.score, difficulty=self.difficulty):
            self.new_high_score = True
            self.high_score = self.score
        self._finalize_game_statistics()
        if self.won:
            self._record_campaign_clear()
            self.achievements.unlock("digdug_win")
            if self.difficulty == Difficulty.HARD:
                self.achievements.unlock("digdug_hard")

    def _record_game_statistics(self):
        self.stats.increment("digdug", "crystals_collected", self._total_crystals)
        self.stats.increment("digdug", "deaths", self._deaths)
        self.stats.add("digdug", "total_score", self.score)
        if self.won:
            self.stats.increment("digdug", "wins")

    def _player_rect(self, x=None, y=None):
        x = self.player_x if x is None else x
        y = self.player_y if y is None else y
        return pygame.Rect(
            int(x - PLAYER_HITBOX / 2), int(y - PLAYER_HITBOX / 2), PLAYER_HITBOX, PLAYER_HITBOX
        )

    def update(self, dt):
        if self.paused:
            return
        if self.death_timer:
            self.ferret.update(0, 0)
            self.death_timer -= 1
            if not self.death_timer and not self.game_over:
                self.player_x = self.player_y = 200.0
                self.ferret.set_position(200, 200)
                self.ferret.set_state("emerge")
                self.special_timer = 40
                self.invulnerable_timer = 120
            return
        if self.game_over or self.won:
            return
        if self.level_complete:
            self.transition_timer -= 1
            self.ferret.update(0, 0)
            if self.transition_timer <= 0:
                self.level += 1
                self._start_level()
            return
        self.invulnerable_timer = max(0, self.invulnerable_timer - 1)
        self.special_timer = max(0, self.special_timer - 1)
        dx, dy = self.last_dx, self.last_dy
        length = math.hypot(dx, dy)
        if length:
            dx, dy = dx / length * PLAYER_SPEED, dy / length * PLAYER_SPEED
            new_x = max(16, min(WINDOW_WIDTH - 16, self.player_x + dx))
            if not any(
                self._player_rect(new_x, self.player_y).colliderect(b.rect) for b in self.boulders
            ):
                self.player_x = new_x
            new_y = max(116, min(WINDOW_HEIGHT - 16, self.player_y + dy))
            if not any(
                self._player_rect(self.player_x, new_y).colliderect(b.rect) for b in self.boulders
            ):
                self.player_y = new_y
            if self._dig_tunnel(int(self.player_x), int(self.player_y), radius=30):
                self.audio.play_sound(AudioManager.SOUND_DIG)
            if dx:
                self.ferret.facing_right = dx > 0
        if not self.special_timer:
            self.ferret.set_state("dig" if length else "idle", reset_frame=False)
        self.ferret.set_position(self.player_x, self.player_y)
        self.ferret.update(0, 0)
        self.crystals.update()
        player_rect = self._player_rect()
        collected = [c for c in self.crystals if player_rect.colliderect(c.rect)]
        for crystal in collected:
            crystal.kill()
        if collected:
            self.crystals_collected += len(collected)
            self._total_crystals += len(collected)
            self.score += 100 * len(collected)
            self.ferret.set_state("emerge")
            self.special_timer = 40
            self.audio.play_sound(AudioManager.SOUND_COLLECT)
            self.achievements.unlock("digdug_first")
            if not self.crystals:
                self.score += 500 * self.level
                self.stats.increment("global", "games_completed")
                self.audio.play_sound(AudioManager.SOUND_VICTORY)
                if self.level == self.max_levels:
                    self.won = True
                    self._finish_session()
                else:
                    self.level_complete = True
                    self.transition_timer = 90
                return
        for enemy in self.enemies:
            enemy.update(self.terrain, self.boulders, speed=min(4, 1 + self.level))
        if not self.invulnerable_timer and any(
            player_rect.colliderect(e.rect) for e in self.enemies
        ):
            self.lives -= 1
            self._deaths += 1
            self.death_timer = 60
            self.ferret.set_state("death")
            self.audio.play_sound(AudioManager.SOUND_DEATH)
            if self.lives == 0:
                self.game_over = True
                self._finish_session()

    def render(self):
        """Draw the game state to the screen."""
        # Draw underground background
        self._draw_terrain()

        # Draw boulders
        for boulder in self.boulders:
            boulder.draw(self.screen)

        # Draw crystals
        for crystal in self.crystals:
            crystal.draw(self.screen)

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen)

        # Draw the ferret
        self.ferret.draw(self.screen)

        # Draw HUD
        self._draw_hud()

        if self.paused:
            self._draw_pause_overlay()
        elif self.game_over and self.death_timer == 0:
            self._draw_game_over_overlay(score=self.score)
        elif self.won:
            self._overlay(
                "EXPEDITION COMPLETE!",
                self._campaign_result(),
                "A / Enter: restart    B / Esc: menu",
            )
        elif self.level_complete:
            self._draw_overlay(f"Depth {self.level} cleared! Heading deeper...", GREEN)

    def _draw_terrain(self):
        """Only redraw excavated cells and the neighboring tunnel edges."""
        for row, col in self._terrain_dirty:
            x, y = col * CELL_SIZE, row * CELL_SIZE
            rect = (x, y, CELL_SIZE, CELL_SIZE)
            if self.terrain[row][col]:
                shade, has_rock = self.dirt_texture[row][col]
                pygame.draw.rect(self._terrain_surface, shade, rect)
                pygame.draw.line(self._terrain_surface, DIRT_ACCENT, (x, y), (x + CELL_SIZE, y))
                pygame.draw.line(self._terrain_surface, DIRT_ACCENT, (x, y), (x, y + CELL_SIZE))
                if has_rock:
                    pygame.draw.circle(self._terrain_surface, ROCK_COLOR, (x + 12, y + 12), 3)
            else:
                pygame.draw.rect(self._terrain_surface, TUNNEL_COLOR, rect)
                for dr, dc, start, end in (
                    (-1, 0, (x, y), (x + 24, y)),
                    (1, 0, (x, y + 24), (x + 24, y + 24)),
                    (0, -1, (x, y), (x, y + 24)),
                    (0, 1, (x + 24, y), (x + 24, y + 24)),
                ):
                    if (
                        0 <= row + dr < GRID_ROWS
                        and 0 <= col + dc < GRID_COLS
                        and self.terrain[row + dr][col + dc]
                    ):
                        pygame.draw.line(self._terrain_surface, TUNNEL_GLOW, start, end, 3)
        self._terrain_dirty.clear()
        self.screen.blit(self._terrain_surface, (0, 0))

    def _draw_hud(self):
        self.screen.blit(self._hud_surface, (0, 0))
        text = f"Depth {self.level}/{self.max_levels}  Gems {self.crystals_collected}/{self.crystals_needed}  Score {self.score}  High {self.high_score}  Lives {self.lives}"
        self.screen.blit(self.font.render(text, True, (225, 215, 195)), (10, 10))
        self.screen.blit(self.font.render("[B] Menu", True, (225, 215, 195)), (690, 566))

    def _draw_overlay(self, message, color):
        """Draw a semi-transparent overlay with a message."""
        # Use cached overlay surface
        if not hasattr(self, "_overlay_surface"):
            self._overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._overlay_surface.fill((0, 0, 0, 180))
        self.screen.blit(self._overlay_surface, (0, 0))

        text_surface = self.font.render(message, True, color)
        text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(text_surface, text_rect)
