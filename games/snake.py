"""
Snake Game - Winston Entertainment System

A ferret-themed snake game using the AnimatedFerret sprite for the snake head.
The snake body uses the weasel color palette (brown, tan, white repeating).
"""

import pygame
import random
import sys
import os
from collections import deque

# Add parent directory to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import (
    BaseGame,
    AnimatedFerret,
    AudioManager,
    Difficulty,
    get_score_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WHITE,
    RED,
    WEASEL_BROWN,
)


# Game constants
CELL_SIZE = 32  # Larger cells for better visibility (was 20)
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE  # 25 cells wide (800/32)
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE  # 18 cells tall (600/32)
FIRST_PLAY_ROW = 2  # Keep food and movement below the HUD.
SNAKE_FPS = 10  # Snake moves at 10 FPS, slower than render FPS

# Enhanced cute meadow color palette - softer and more vibrant
MEADOW_LIGHT = (170, 220, 140)  # Softer light grass
MEADOW_DARK = (140, 200, 120)  # Softer darker grass patches
MEADOW_FLOWER_1 = (255, 182, 193)  # Pink flower dots (lighter)
MEADOW_FLOWER_2 = (173, 216, 230)  # Baby blue flower dots
MEADOW_FLOWER_3 = (255, 255, 180)  # Soft yellow flower dots
MEADOW_FLOWER_4 = (221, 160, 221)  # Lavender flower dots
MEADOW_FLOWER_5 = (255, 218, 185)  # Peach flower dots

# Sparkle colors for food glow
SPARKLE_GOLD = (255, 215, 100)
SPARKLE_WHITE = (255, 255, 240)


class SnakeGame(BaseGame):
    """
    Snake game implementation using BaseGame pattern.

    Features:
    - AnimatedFerret sprites for entire snake (head and body)
    - Cute meadow background with flowers
    - Death animation before game over screen
    - Dig animation when eating food
    """

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            "snake_fps": 6,  # Slower movement
            "walls_kill": False,  # Wrap around edges
        },
        Difficulty.NORMAL: {
            "snake_fps": 10,  # Normal speed
            "walls_kill": False,  # Wrap around edges
        },
        Difficulty.HARD: {
            "snake_fps": 14,  # Faster movement
            "walls_kill": True,  # Hitting walls = death
        },
    }

    def setup(self):
        """Initialize game state and load assets."""
        self.font = pygame.font.Font(None, 36)

        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.snake_fps = preset["snake_fps"]
        self.walls_kill = preset["walls_kill"]

        # Load food sprite (soupbowl)
        from engine import AssetLoader

        self.asset_loader = AssetLoader()
        self.food_img = self.asset_loader.load_image("soupbowl.png", (CELL_SIZE, CELL_SIZE))

        # Game timing
        self.move_timer = 0
        self.move_delay = 1.0 / self.snake_fps  # Time between snake moves (difficulty-adjusted)

        # Animation timing for special states
        self.animation_timer = 0
        self.animation_duration = 0
        self.pending_state = None  # State to transition to after animation

        # Generate background with flowers (only once)
        self._generate_background()

        # Reset game state
        self.reset_game()

    def _generate_background(self):
        """Generate a cute meadow background with grass patches and flowers."""
        self._background = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._background.fill(MEADOW_LIGHT)

        # Draw softer grass patches with more organic shapes
        rng = random.Random(42)  # Decorations must not reseed gameplay.
        for _ in range(100):
            x = rng.randint(0, WINDOW_WIDTH)
            y = rng.randint(0, WINDOW_HEIGHT)
            w = rng.randint(40, 100)
            h = rng.randint(30, 60)
            pygame.draw.ellipse(self._background, MEADOW_DARK, (x, y, w, h))

        # Draw small flower dots with more variety
        flower_colors = [
            MEADOW_FLOWER_1,
            MEADOW_FLOWER_2,
            MEADOW_FLOWER_3,
            MEADOW_FLOWER_4,
            MEADOW_FLOWER_5,
        ]
        for _ in range(90):
            x = rng.randint(5, WINDOW_WIDTH - 5)
            y = rng.randint(5, WINDOW_HEIGHT - 5)
            color = rng.choice(flower_colors)
            size = rng.randint(3, 7)
            pygame.draw.circle(self._background, color, (x, y), size)
            # Add golden center dot for some flowers
            if rng.random() > 0.4:
                pygame.draw.circle(self._background, (255, 220, 100), (x, y), max(1, size // 2))

        # Draw tiny grass tufts
        tuft_color = (100, 160, 80)
        for _ in range(50):
            x = rng.randint(10, WINDOW_WIDTH - 10)
            y = rng.randint(10, WINDOW_HEIGHT - 10)
            for i in range(3):
                dx = rng.randint(-3, 3)
                pygame.draw.line(
                    self._background,
                    tuft_color,
                    (x + dx, y),
                    (x + dx + rng.randint(-2, 2), y - rng.randint(4, 8)),
                    1,
                )

        # Draw very subtle grid lines
        grid_color = (155, 210, 130)  # Very subtle
        for gx in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self._background, grid_color, (gx, 0), (gx, WINDOW_HEIGHT), 1)
        for gy in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self._background, grid_color, (0, gy), (WINDOW_WIDTH, gy), 1)

        # Initialize food sparkle effect
        self._food_sparkle_timer = 0
        self._food_sparkles = []

    def reset_game(self):
        """Reset game to initial state."""
        # Snake position (grid coordinates)
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2

        # Direction (0, 0) means waiting for first input
        self.direction = (1, 0)
        self.turn_queue = deque(maxlen=2)
        self._last_dpad = (0, 0)
        self.move_timer = 0
        self.move_delay = 1.0 / self.snake_fps
        self.won = False

        # Create snake as list of AnimatedFerret sprites
        # Each segment is a ferret at a grid position
        self.body_sprites = []
        self.snake = []  # Grid positions for collision detection

        # Create head ferret
        head_pixel_x = start_x * CELL_SIZE + CELL_SIZE // 2
        head_pixel_y = start_y * CELL_SIZE + CELL_SIZE // 2
        head = self._create_ferret_segment(head_pixel_x, head_pixel_y)
        head.set_state("idle")
        self.body_sprites.append(head)
        self.snake.append((start_x, start_y))

        # Create initial body segments (2 segments behind head)
        for i in range(1, 3):
            seg_x = (start_x - i) * CELL_SIZE + CELL_SIZE // 2
            seg_y = start_y * CELL_SIZE + CELL_SIZE // 2
            segment = self._create_ferret_segment(seg_x, seg_y)
            segment.set_state("idle")
            # Offset animation frames so they don't all animate in sync
            segment._frame = i * 2
            self.body_sprites.append(segment)
            self.snake.append((start_x - i, start_y))

        # Reference to head for convenience
        self.ferret = self.body_sprites[0]

        # Spawn food
        self.food = self._spawn_food()

        # Game state
        self.score = 0
        self.game_over = False
        self.waiting_for_input = True
        self.score_manager = get_score_manager()
        self.high_score = self.score_manager.get_high_score("snake", self.difficulty)
        self.new_high_score = False
        self.paused = False

        # Animation state
        self.playing_death = False
        self.playing_dig = False
        self.animation_timer = 0

    def _create_ferret_segment(self, pixel_x, pixel_y):
        """Create an AnimatedFerret for a snake segment at given pixel position."""
        ferret = AnimatedFerret(
            x=pixel_x,
            y=pixel_y,
            scale=1,  # Base scale; actual sprite size is set below
            speed=0,  # We handle movement via grid
            frame_delay=6,  # Animation speed
        )
        # Adjust sprite size to match cell size (using public method)
        ferret.set_sprite_size(CELL_SIZE)
        return ferret

    def _spawn_food(self):
        """Spawn food at random location not occupied by snake."""
        occupied = set(self.snake)
        free = [
            (x, y)
            for y in range(FIRST_PLAY_ROW, GRID_HEIGHT)
            for x in range(GRID_WIDTH)
            if (x, y) not in occupied
        ]
        return random.choice(free) if free else None

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        # Update input manager state
        self.input_manager.update()

        # Check for back button (exit to menu)
        if self.input_manager.back_pressed():
            return True

        # Check for pause toggle (only during gameplay)
        if self.input_manager.pause_pressed() and not self.game_over and not self.waiting_for_input:
            self.paused = not self.paused
            return False

        # Don't process other input when paused
        if self.paused:
            return False

        # Check for action button (restart after game over)
        if self.game_over and not self.playing_death:
            if self.input_manager.confirm_pressed():
                self.restart_session()
                self.reset_game()
                return False

        # Don't process movement during death animation
        if self.playing_death or self.game_over:
            return False

        # Get D-pad input
        dp = self.input_manager.get_dpad()

        if dp != self._last_dpad and dp != (0, 0):
            turn = (0, dp[1]) if dp[1] else (dp[0], 0)
            previous = self.turn_queue[-1] if self.turn_queue else self.direction
            if turn != (-previous[0], -previous[1]):
                if turn != previous and len(self.turn_queue) < self.turn_queue.maxlen:
                    self.turn_queue.append(turn)
                    self.audio.play_sound(AudioManager.SOUND_TURN)
                self.waiting_for_input = False
                for sprite in self.body_sprites:
                    sprite.set_state("movement")
        self._last_dpad = dp

        return False

    def update(self, dt):
        """Update game logic."""
        # Don't update when paused
        if self.paused:
            return

        # Update all ferret animations
        # Don't pass movement to ferret.update() since we handle position via grid
        for sprite in self.body_sprites:
            # Grid positions are owned here; advance frames without reverting to idle.
            sprite._advance_animation()

        # Handle death animation
        if self.playing_death:
            self.animation_timer += dt
            # Death animation lasts about 0.8 seconds (8 frames at ~10fps)
            if self.animation_timer >= 0.8:
                self.playing_death = False
                self.game_over = True
                # Check and save high score
                if self.score_manager.set_high_score("snake", self.score, self.difficulty):
                    self.new_high_score = True
                    self.high_score = self.score
                # Check achievements
                self.achievements.unlock("snake_first")
                # Track statistics
                self._finalize_game_statistics()
            return

        # Handle dig animation (eating food)
        if self.playing_dig:
            self.animation_timer += dt
            # Dig animation is brief (~0.3 seconds)
            if self.animation_timer >= 0.3:
                self.playing_dig = False
                self.ferret.set_state("movement")
        # Don't update if game over or waiting for input
        if self.game_over or self.waiting_for_input:
            return

        # Accumulate time for snake movement
        self.move_timer += dt

        while (
            self.move_timer + 1e-9 >= self.move_delay
            and not self.playing_death
            and not self.game_over
        ):
            self.move_timer -= self.move_delay

            # Apply buffered direction
            if self.turn_queue:
                self.direction = self.turn_queue.popleft()

            # Move snake
            if self.direction != (0, 0):
                self._move_snake()

    def _move_snake(self):
        """Move the snake one cell in the current direction."""
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # Check wall collision
        if (
            new_head[0] < 0
            or new_head[0] >= GRID_WIDTH
            or new_head[1] < FIRST_PLAY_ROW
            or new_head[1] >= GRID_HEIGHT
        ):
            if self.walls_kill:
                # Hard mode: walls kill
                self._trigger_death()
                return
            else:
                # Easy/Normal mode: wrap around edges
                new_head = (
                    new_head[0] % GRID_WIDTH,
                    FIRST_PLAY_ROW
                    + (new_head[1] - FIRST_PLAY_ROW) % (GRID_HEIGHT - FIRST_PLAY_ROW),
                )

        # Check self collision (exclude tail which will move)
        if new_head in self.snake[:-1]:
            self._trigger_death()
            return

        # Store previous positions for cascading body movement
        prev_positions = [(s.x, s.y) for s in self.body_sprites]
        prev_facings = [s.facing_right for s in self.body_sprites]

        # Move grid position
        self.snake.insert(0, new_head)

        # Update head ferret position
        head_pixel_x = new_head[0] * CELL_SIZE + CELL_SIZE // 2
        head_pixel_y = new_head[1] * CELL_SIZE + CELL_SIZE // 2
        self.body_sprites[0].x = head_pixel_x
        self.body_sprites[0].y = head_pixel_y

        # Update head facing direction
        if self.direction[0] > 0:
            self.body_sprites[0].facing_right = True
        elif self.direction[0] < 0:
            self.body_sprites[0].facing_right = False

        # Cascade body segment positions - each follows the one ahead
        for i in range(1, len(self.body_sprites)):
            self.body_sprites[i].x = prev_positions[i - 1][0]
            self.body_sprites[i].y = prev_positions[i - 1][1]
            self.body_sprites[i].facing_right = prev_facings[i - 1]

        # Check food collision
        if new_head == self.food:
            self.score += 10
            if self.score == 30 and self.difficulty == Difficulty.HARD:
                self.achievements.unlock("snake_hard_win")
            if self.score in (50, 100):
                self.achievements.unlock(f"snake_{self.score}")
            self.food = self._spawn_food()
            # Grow the snake (add new ferret at tail position)
            self._grow_snake(prev_positions[-1], prev_facings[-1])
            self.move_delay = 1.0 / min(
                self.snake_fps + 6, self.snake_fps + (len(self.snake) - 3) // 5
            )
            # Trigger dig animation on head
            self._trigger_dig()
            if self.food is None:
                self.won = self.game_over = True
                self.playing_dig = False
                self.stats.increment("global", "games_completed")
                self._finalize_game_statistics()
                self.achievements.unlock("snake_first")
                self.new_high_score = self.score_manager.set_high_score(
                    "snake", self.score, self.difficulty
                )
                self.high_score = max(self.high_score, self.score)
        else:
            # Remove tail position from grid
            self.snake.pop()

    def _record_game_statistics(self):
        died = self.playing_death or (self.game_over and not self.won)
        self.stats.increment("snake", "deaths", int(died))
        self.stats.add("snake", "total_score", self.score)
        self.stats.max_stat("snake", "highest_length", len(self.snake))

    def _grow_snake(self, tail_pos, tail_facing):
        """Add a new AnimatedFerret segment at the tail position."""
        new_segment = self._create_ferret_segment(tail_pos[0], tail_pos[1])
        new_segment.set_state("movement")
        new_segment.facing_right = tail_facing
        # Offset frame to desync animation
        new_segment._frame = len(self.body_sprites) % 8
        self.body_sprites.append(new_segment)

    def _trigger_death(self):
        """Trigger death animation on all ferrets."""
        self.playing_death = True
        self.animation_timer = 0
        self.high_score = max(self.high_score, self.score)
        # Set death state on all ferret sprites
        for sprite in self.body_sprites:
            sprite.set_state("death")
        self.audio.play_sound(AudioManager.SOUND_DEATH)

    def _trigger_dig(self):
        """Trigger dig animation when eating food."""
        self.playing_dig = True
        self.animation_timer = 0
        self.ferret.set_state("dig")
        self.audio.play_sound(AudioManager.SOUND_COLLECT)

    def render(self):
        """Draw the game state."""
        import math

        # Draw cute meadow background (pre-generated with flowers)
        self.screen.blit(self._background, (0, 0))

        if self.food is not None:
            food_x, food_y = (value * CELL_SIZE for value in self.food)
            food_cx, food_cy = food_x + CELL_SIZE // 2, food_y + CELL_SIZE // 2
            self._food_sparkle_timer += 1
            if not hasattr(self, "_food_glow"):
                self._food_glow = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.circle(self._food_glow, (*SPARKLE_GOLD, 100), (32, 32), 28)
            self.screen.blit(self._food_glow, (food_cx - 32, food_cy - 32))
            for i in range(4):
                angle = self._food_sparkle_timer * 0.05 + i * math.pi / 2
                sx = round(food_cx + math.cos(angle) * 22)
                sy = round(food_cy + math.sin(angle) * 22)
                pygame.draw.line(self.screen, SPARKLE_WHITE, (sx - 3, sy), (sx + 3, sy), 2)
                pygame.draw.line(self.screen, SPARKLE_WHITE, (sx, sy - 3), (sx, sy + 3), 2)
            if self.food_img:
                self.screen.blit(self.food_img, (food_x, food_y))
            else:
                pygame.draw.rect(self.screen, RED, (food_x, food_y, CELL_SIZE, CELL_SIZE))

        # Draw all ferret sprites (tail to head so head appears on top)
        for sprite in reversed(self.body_sprites):
            self._draw_ferret_sprite(sprite)

        # Draw UI with shadow for readability on meadow background
        score_text = f"Score: {self.score}  High: {self.high_score}  [B] Menu"
        # Shadow
        shadow_surface = self.font.render(score_text, True, (50, 80, 50))
        self.screen.blit(shadow_surface, (11, 11))
        # Main text
        text_surface = self.font.render(score_text, True, WHITE)
        self.screen.blit(text_surface, (10, 10))

        # Draw game state messages
        if self.paused:
            self._draw_pause_overlay()
        elif self.game_over and not self.playing_death:
            self._draw_game_over()
        elif self.waiting_for_input:
            self._draw_start_prompt()

    def _draw_ferret_sprite(self, ferret_sprite):
        """Draw a single ferret sprite at its current position."""
        sprite = ferret_sprite.get_image()

        if sprite:
            # Scale sprite to cell size if needed
            if sprite.get_width() != CELL_SIZE:
                sprite = pygame.transform.scale(sprite, (CELL_SIZE, CELL_SIZE))

            # Draw at pixel position (ferret position is center, so offset by half cell)
            draw_x = ferret_sprite.x - CELL_SIZE // 2
            draw_y = ferret_sprite.y - CELL_SIZE // 2
            self.screen.blit(sprite, (draw_x, draw_y))
        else:
            # Fallback: draw colored circle
            pygame.draw.circle(
                self.screen,
                WEASEL_BROWN,
                (int(ferret_sprite.x), int(ferret_sprite.y)),
                CELL_SIZE // 2 - 2,
            )

    def _draw_game_over(self):
        self._draw_game_over_overlay(
            title="MEADOW COMPLETE!" if self.won else "GAME OVER", score=self.score
        )

    def _draw_start_prompt(self):
        """Draw start prompt when waiting for first input."""
        prompt_text = self.font.render("D-pad or Arrows to start", True, WHITE)
        prompt_rect = prompt_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(prompt_text, prompt_rect)
