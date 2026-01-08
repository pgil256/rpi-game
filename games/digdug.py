"""
Ferret Digger (Dig Dug) - A Weasel Entertainment System Game

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
- 3 crystals to collect to win
- 2 roaming enemies to avoid
- Boulder obstacles that block movement
"""

import pygame
import random
import sys

from engine import (
    BaseGame,
    AnimatedFerret,
    AssetLoader,
    AudioManager,
    Difficulty,
    get_score_manager,
    get_stats_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    BLACK,
    WHITE,
    RED,
    GREEN,
    CYAN,
    BURROW_BROWN,
    WEASEL_BROWN,
    WEASEL_TAN,
)


# Grid and terrain constants
CELL_SIZE = 25  # Size of each terrain cell
GRID_COLS = WINDOW_WIDTH // CELL_SIZE
GRID_ROWS = WINDOW_HEIGHT // CELL_SIZE

# Enhanced cute underground theme colors
DIRT_DARK = (80, 55, 35)       # Softer dark brown
DIRT_MID = (120, 85, 55)       # Warmer medium brown
DIRT_LIGHT = (180, 145, 100)   # Softer light brown
DIRT_ACCENT = (100, 70, 45)    # Accent color for depth
TUNNEL_COLOR = (40, 30, 25)    # Deep tunnel color
TUNNEL_GLOW = (60, 45, 35)     # Subtle tunnel edge glow
ROCK_COLOR = (100, 95, 105)    # Slightly purple-gray rocks
ROCK_HIGHLIGHT = (130, 125, 135)  # Rock highlights
CRYSTAL_GLOW = (180, 240, 255) # Softer cyan glow
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
ENTITY_SIZE = 50
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

    def draw(self, surface):
        """Draw the crystal with enhanced glow and sparkle effects."""
        cx, cy = self.rect.centerx, self.rect.centery

        # Draw outer glow (pulsing)
        pulse = abs(math.sin(self.glow_timer * 0.08)) * 0.5 + 0.5
        glow_size = int(35 + pulse * 10)
        glow_alpha = int(60 + pulse * 40)
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*CRYSTAL_GLOW, glow_alpha), (glow_size, glow_size), glow_size)
        surface.blit(glow_surf, (cx - glow_size, cy - glow_size))

        # Draw inner brighter glow
        inner_size = int(20 + pulse * 5)
        inner_surf = pygame.Surface((inner_size * 2, inner_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(inner_surf, (*CRYSTAL_SPARKLE, int(80 + pulse * 40)), (inner_size, inner_size), inner_size)
        surface.blit(inner_surf, (cx - inner_size, cy - inner_size))

        # Draw sparkles
        for sx, sy, phase in self._sparkles:
            sparkle_val = abs(math.sin(self.glow_timer * 0.12 + phase))
            if sparkle_val > 0.6:
                spark_size = int(2 + sparkle_val * 3)
                spark_alpha = int((sparkle_val - 0.6) * 2.5 * 255)
                spark_surf = pygame.Surface((spark_size * 2 + 2, spark_size * 2 + 2), pygame.SRCALPHA)
                # Draw 4-pointed star
                pygame.draw.line(spark_surf, (*CRYSTAL_SPARKLE, spark_alpha),
                               (0, spark_size), (spark_size * 2, spark_size), 2)
                pygame.draw.line(spark_surf, (*CRYSTAL_SPARKLE, spark_alpha),
                               (spark_size, 0), (spark_size, spark_size * 2), 2)
                surface.blit(spark_surf, (cx + sx - spark_size, cy + sy - spark_size))

        # Draw the crystal image
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

    def update(self, bounds_top=100):
        """Update enemy movement with random direction changes."""
        self.change_timer += 1

        # Move
        self.rect.x += self.dx
        self.rect.y += self.dy

        # Bounce off edges
        if self.rect.left < 0 or self.rect.right > WINDOW_WIDTH:
            self.dx = -self.dx
        if self.rect.top < bounds_top or self.rect.bottom > WINDOW_HEIGHT:
            self.dy = -self.dy

        # Random direction changes
        if random.random() < 0.02:
            directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
            self.dx, self.dy = random.choice(directions)

    def draw(self, surface):
        """Draw the enemy."""
        surface.blit(self.image, self.rect)


class DigDugGame(BaseGame):
    """Ferret Digger - Dig tunnels and collect crystals underground!

    Controls:
    - D-pad/Arrow keys: Move the ferret (continuous digging movement)
    - B/ESC: Return to menu

    The ferret digs through dirt, leaving tunnels behind. Collect all 3
    crystals while avoiding enemies and boulders to win!
    """

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            'enemy_count': 1,   # Just 1 enemy
        },
        Difficulty.NORMAL: {
            'enemy_count': 2,   # 2 enemies (default)
        },
        Difficulty.HARD: {
            'enemy_count': 4,   # 4 enemies
        },
    }

    def setup(self):
        """Initialize the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.enemy_count = preset['enemy_count']

        self.font = pygame.font.Font(None, 36)

        # Create asset loader
        self.asset_loader = AssetLoader()

        # Load sprites
        self._load_sprites()

        # Create the terrain grid (True = dirt, False = tunnel)
        self._create_terrain()

        # Create the animated ferret player
        self.ferret = AnimatedFerret(
            x=200,
            y=200,
            scale=2,  # Slightly larger for visibility
            speed=0,  # We handle position directly for collision
            frame_delay=4  # Fast animation for digging
        )
        self.ferret.set_state('dig')

        # Player position (center of sprite)
        self.player_x = 200.0
        self.player_y = 200.0

        # Movement state
        self.moving = False
        self.last_dx = 0
        self.last_dy = 0

        # Create game entities
        self._create_entities()

        # Game state
        self.crystals_collected = 0
        self.game_over = False
        self.won = False
        self.paused = False
        self.score_manager = get_score_manager()
        self.stats = get_stats_manager()
        # Dig Dug uses crystals as score
        self.high_score = self.score_manager.get_high_score('digdug')
        self.new_high_score = False
        self._deaths = 0  # Track for stats

        # Dig out starting area around the player
        self._dig_tunnel(int(self.player_x), int(self.player_y), radius=40)

    def _load_sprites(self):
        """Load game sprites with fallbacks."""
        # Crystal (soupbowl)
        self.crystal_img = self.asset_loader.load_image('soupbowl.png', (ENTITY_SIZE, ENTITY_SIZE))
        if not self.crystal_img:
            self.crystal_img = self._create_fallback_sprite(ENTITY_SIZE, CYAN)

        # Enemy (soupcan_new with translucency) - preserve aspect ratio
        self.enemy_img = self.asset_loader.load_image('soupcan_new.png', (ENTITY_SIZE, ENTITY_SIZE), preserve_aspect=True)
        if not self.enemy_img:
            self.enemy_img = self._create_fallback_sprite(ENTITY_SIZE, RED)
        else:
            # Apply translucency to match other game sprites
            self.enemy_img = self.enemy_img.convert_alpha()
            self.enemy_img.set_alpha(200)

        # Boulder
        self.boulder_img = self._create_boulder_sprite()

    def _create_fallback_sprite(self, size, color):
        """Create a simple colored fallback sprite."""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, color, (0, 0, size, size))
        return surface.convert_alpha()  # Convert for optimal blitting

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
        """Create crystals, enemies, and boulders."""
        # Crystals (placed randomly in lower portion of screen)
        self.crystals = pygame.sprite.Group()
        crystal_positions = [
            (100, 300),
            (400, 400),
            (600, 350),
        ]
        for x, y in crystal_positions:
            crystal = Crystal(x, y, self.crystal_img)
            self.crystals.add(crystal)
            # Dig out area around crystal
            self._dig_tunnel(x + ENTITY_SIZE // 2, y + ENTITY_SIZE // 2, radius=30)

        # Boulders (obstacles)
        self.boulders = pygame.sprite.Group()
        boulder_positions = [
            (500, 200),
            (300, 350),
            (200, 450),
        ]
        for x, y in boulder_positions:
            boulder = Boulder(x, y, self.boulder_img)
            self.boulders.add(boulder)

        # Enemies - difficulty-based count
        self.enemies = pygame.sprite.Group()
        # Pool of possible enemy spawn positions
        all_enemy_positions = [
            (400, 300),
            (600, 400),
            (150, 450),
            (500, 200),
        ]
        # Use the first N positions based on difficulty
        for i in range(min(self.enemy_count, len(all_enemy_positions))):
            x, y = all_enemy_positions[i]
            enemy = Enemy(x, y, self.enemy_img)
            self.enemies.add(enemy)
            # Dig out area around enemy start
            self._dig_tunnel(x + ENTITY_SIZE // 2, y + ENTITY_SIZE // 2, radius=30)

    def _dig_tunnel(self, x, y, radius=20):
        """Dig out a circular area in the terrain."""
        center_col = x // CELL_SIZE
        center_row = y // CELL_SIZE
        cells_radius = radius // CELL_SIZE + 1

        for row in range(max(0, center_row - cells_radius),
                         min(GRID_ROWS, center_row + cells_radius + 1)):
            for col in range(max(0, center_col - cells_radius),
                             min(GRID_COLS, center_col + cells_radius + 1)):
                # Check if within circular radius
                dx = (col * CELL_SIZE + CELL_SIZE // 2) - x
                dy = (row * CELL_SIZE + CELL_SIZE // 2) - y
                if dx * dx + dy * dy <= radius * radius:
                    self.terrain[row][col] = False

    def _reset_game(self):
        """Reset the game to initial state."""
        self.crystals_collected = 0
        self.game_over = False
        self.won = False

        # Reset player position
        self.player_x = 200.0
        self.player_y = 200.0
        self.ferret.set_state('dig')

        # Recreate terrain and entities
        self._create_terrain()
        self._create_entities()
        self._dig_tunnel(int(self.player_x), int(self.player_y), radius=40)

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        # If game is over, wait for action button to restart
        if self.game_over or self.won:
            if self.input_manager.action_pressed():
                self._reset_game()
            return False

        # Check for pause toggle
        if self.input_manager.pause_pressed():
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Get D-pad input for continuous movement
        dp = self.input_manager.get_dpad()

        # Also check keyboard for continuous movement
        keys = pygame.key.get_pressed()
        dx = dp[0] if dp[0] != 0 else (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT])
        dy = dp[1] if dp[1] != 0 else (keys[pygame.K_DOWN] - keys[pygame.K_UP])

        self.last_dx = dx
        self.last_dy = dy
        self.moving = (dx != 0 or dy != 0)

        return False

    def update(self, dt):
        """Update game logic."""
        if self.game_over or self.won or self.paused:
            return

        # Update player position based on input
        if self.moving:
            new_x = self.player_x + self.last_dx * PLAYER_SPEED
            new_y = self.player_y + self.last_dy * PLAYER_SPEED

            # Clamp to screen bounds
            new_x = max(ENTITY_SIZE // 2, min(WINDOW_WIDTH - ENTITY_SIZE // 2, new_x))
            new_y = max(100 + ENTITY_SIZE // 2, min(WINDOW_HEIGHT - ENTITY_SIZE // 2, new_y))

            # Check boulder collisions
            player_rect = pygame.Rect(
                new_x - ENTITY_SIZE // 2,
                new_y - ENTITY_SIZE // 2,
                ENTITY_SIZE,
                ENTITY_SIZE
            )

            collision = False
            for boulder in self.boulders:
                if player_rect.colliderect(boulder.rect):
                    collision = True
                    break

            if not collision:
                self.player_x = new_x
                self.player_y = new_y

                # Dig tunnel as we move
                self._dig_tunnel(int(self.player_x), int(self.player_y), radius=20)

                # Update ferret state and facing
                if self.last_dx > 0:
                    self.ferret.facing_right = True
                elif self.last_dx < 0:
                    self.ferret.facing_right = False

                self.ferret.set_state('dig', reset_frame=False)
        else:
            # Idle when not moving
            self.ferret.set_state('idle', reset_frame=False)

        # Update ferret position
        self.ferret.x = self.player_x
        self.ferret.y = self.player_y
        self.ferret.update(0, 0)  # Update animation

        # Update crystals
        for crystal in self.crystals:
            crystal.update()

        # Check crystal collection
        player_rect = self.ferret.get_rect()
        collected = pygame.sprite.spritecollide(
            type('', (), {'rect': player_rect})(),
            self.crystals,
            True
        )
        if collected:
            self.crystals_collected += len(collected)
            self.audio.play_sound(AudioManager.SOUND_COLLECT)
            # Play emerge animation briefly when collecting
            self.ferret.set_state('emerge')
            # Achievement for first crystal
            self.achievements.unlock('digdug_first')

            if self.crystals_collected >= 3:
                # Check and save high score
                if self.score_manager.set_high_score('digdug', self.crystals_collected):
                    self.new_high_score = True
                    self.high_score = self.crystals_collected
                # Track statistics
                self.stats.increment('digdug', 'games_played')
                self.stats.increment('digdug', 'crystals_collected', self.crystals_collected)
                self.stats.increment('digdug', 'wins')
                self.stats.increment('digdug', 'deaths', self._deaths)
                self.stats.increment('global', 'games_started')
                self.stats.increment('global', 'games_completed')
                self.won = True
                self.audio.play_sound(AudioManager.SOUND_VICTORY)
                # Achievements for winning
                self.achievements.unlock('digdug_win')
                if self.difficulty == Difficulty.HARD:
                    self.achievements.unlock('digdug_hard')

        # Update enemies
        for enemy in self.enemies:
            enemy.update(bounds_top=100)

        # Check enemy collision
        for enemy in self.enemies:
            if player_rect.colliderect(enemy.rect):
                self.ferret.set_state('death')
                self._deaths += 1
                # Check and save high score (crystals as score)
                if self.score_manager.set_high_score('digdug', self.crystals_collected):
                    self.new_high_score = True
                    self.high_score = self.crystals_collected
                # Track statistics
                self.stats.increment('digdug', 'games_played')
                self.stats.increment('digdug', 'crystals_collected', self.crystals_collected)
                self.stats.increment('digdug', 'deaths', self._deaths)
                self.stats.increment('global', 'games_started')
                self.game_over = True
                self.audio.play_sound(AudioManager.SOUND_DEATH)
                break

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

        # Draw game over / win / pause overlays
        if self.paused:
            self._draw_pause_overlay()
        elif self.game_over:
            if self.new_high_score:
                self._draw_overlay("NEW HIGH SCORE! GAME OVER - Press A", (255, 215, 0))
            else:
                self._draw_overlay("GAME OVER - Press A", RED)
        elif self.won:
            if self.new_high_score:
                self._draw_overlay("NEW HIGH SCORE! YOU WIN! - Press A", (255, 215, 0))
            else:
                self._draw_overlay("YOU WIN! - Press A", GREEN)

    def _draw_terrain(self):
        """Draw the underground terrain with tunnels and enhanced visuals."""
        # Fill with gradient-like base (darker at bottom for depth)
        self.screen.fill(DIRT_DARK)

        # Draw subtle depth gradient
        for y_band in range(0, WINDOW_HEIGHT, 50):
            band_alpha = int(15 + (y_band / WINDOW_HEIGHT) * 20)
            band_surf = pygame.Surface((WINDOW_WIDTH, 50), pygame.SRCALPHA)
            band_surf.fill((0, 0, 0, band_alpha))
            self.screen.blit(band_surf, (0, y_band))

        # Draw each cell
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = col * CELL_SIZE
                y = row * CELL_SIZE

                if self.terrain[row][col]:
                    # Dirt - draw with texture
                    shade, has_rock = self.dirt_texture[row][col]
                    pygame.draw.rect(self.screen, shade, (x, y, CELL_SIZE, CELL_SIZE))

                    # Add subtle texture pattern
                    pygame.draw.line(self.screen, DIRT_ACCENT, (x, y), (x + CELL_SIZE, y), 1)
                    pygame.draw.line(self.screen, DIRT_ACCENT, (x, y), (x, y + CELL_SIZE), 1)

                    # Small rock specs with highlight
                    if has_rock:
                        pygame.draw.circle(self.screen, ROCK_COLOR,
                            (x + CELL_SIZE // 2, y + CELL_SIZE // 2), 3)
                        pygame.draw.circle(self.screen, ROCK_HIGHLIGHT,
                            (x + CELL_SIZE // 2 - 1, y + CELL_SIZE // 2 - 1), 1)
                else:
                    # Tunnel - dark excavated area with subtle glow
                    pygame.draw.rect(self.screen, TUNNEL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))

                    # Draw softer tunnel edges with glow effect
                    if row > 0 and self.terrain[row - 1][col]:
                        pygame.draw.line(self.screen, TUNNEL_GLOW, (x, y), (x + CELL_SIZE, y), 3)
                        pygame.draw.line(self.screen, DIRT_ACCENT, (x, y), (x + CELL_SIZE, y), 1)
                    if row < GRID_ROWS - 1 and self.terrain[row + 1][col]:
                        pygame.draw.line(self.screen, TUNNEL_GLOW, (x, y + CELL_SIZE - 1), (x + CELL_SIZE, y + CELL_SIZE - 1), 3)
                        pygame.draw.line(self.screen, DIRT_ACCENT, (x, y + CELL_SIZE - 1), (x + CELL_SIZE, y + CELL_SIZE - 1), 1)
                    if col > 0 and self.terrain[row][col - 1]:
                        pygame.draw.line(self.screen, TUNNEL_GLOW, (x, y), (x, y + CELL_SIZE), 3)
                        pygame.draw.line(self.screen, DIRT_ACCENT, (x, y), (x, y + CELL_SIZE), 1)
                    if col < GRID_COLS - 1 and self.terrain[row][col + 1]:
                        pygame.draw.line(self.screen, TUNNEL_GLOW, (x + CELL_SIZE - 1, y), (x + CELL_SIZE - 1, y + CELL_SIZE), 3)
                        pygame.draw.line(self.screen, DIRT_ACCENT, (x + CELL_SIZE - 1, y), (x + CELL_SIZE - 1, y + CELL_SIZE), 1)

    def _draw_hud(self):
        """Draw the heads-up display with cute styling."""
        # Draw softer HUD bar with gradient
        hud_surf = pygame.Surface((WINDOW_WIDTH, 40), pygame.SRCALPHA)
        for y in range(40):
            alpha = int(180 - y * 2)
            pygame.draw.line(hud_surf, (30, 25, 20, alpha), (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(hud_surf, (0, 0))

        # Draw crystal icons instead of text
        for i in range(3):
            cx = 15 + i * 35
            cy = 20
            if i < self.crystals_collected:
                # Collected crystal - glowing
                glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*CRYSTAL_GLOW, 100), (15, 15), 12)
                self.screen.blit(glow_surf, (cx - 15, cy - 15))
                pygame.draw.polygon(self.screen, CRYSTAL_GLOW, [
                    (cx, cy - 10), (cx + 8, cy), (cx, cy + 10), (cx - 8, cy)])
            else:
                # Uncollected - gray outline
                pygame.draw.polygon(self.screen, (80, 80, 90), [
                    (cx, cy - 10), (cx + 8, cy), (cx, cy + 10), (cx - 8, cy)], 2)

        # Draw menu hint
        hint_text = "[B] Menu"
        shadow_surface = self.font.render(hint_text, True, (20, 15, 10))
        self.screen.blit(shadow_surface, (WINDOW_WIDTH - 90, 11))
        text_surface = self.font.render(hint_text, True, (200, 190, 170))
        self.screen.blit(text_surface, (WINDOW_WIDTH - 91, 10))

    def _draw_overlay(self, message, color):
        """Draw a semi-transparent overlay with a message."""
        # Use cached overlay surface
        if not hasattr(self, '_overlay_surface'):
            self._overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._overlay_surface.fill((0, 0, 0, 180))
        self.screen.blit(self._overlay_surface, (0, 0))

        text_surface = self.font.render(message, True, color)
        text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(text_surface, text_rect)


def run_digdug(screen, input_manager):
    """Entry point for the Dig Dug game.

    Args:
        screen: The pygame display surface.
        input_manager: The InputManager instance.
    """
    game = DigDugGame(screen, input_manager)
    game.run()
