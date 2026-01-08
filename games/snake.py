"""
Snake Game - Weasel Entertainment System

A ferret-themed snake game using the AnimatedFerret sprite for the snake head.
The snake body uses the weasel color palette (brown, tan, white repeating).
"""

import pygame
import random
import sys
import os

# Add parent directory to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine
from engine import (
    BaseGame,
    AnimatedFerret,
    AudioManager,
    Difficulty,
    get_score_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    WHITE,
    RED,
    WEASEL_BROWN,
)


# Game constants
CELL_SIZE = 32  # Larger cells for better visibility (was 20)
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE   # 25 cells wide (800/32)
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE  # 18 cells tall (600/32)
SNAKE_FPS = 10  # Snake moves at 10 FPS, slower than render FPS

# Enhanced cute meadow color palette - softer and more vibrant
MEADOW_LIGHT = (170, 220, 140)    # Softer light grass
MEADOW_DARK = (140, 200, 120)     # Softer darker grass patches
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
            'snake_fps': 6,       # Slower movement
            'walls_kill': False,  # Wrap around edges
        },
        Difficulty.NORMAL: {
            'snake_fps': 10,      # Normal speed
            'walls_kill': False,  # Wrap around edges
        },
        Difficulty.HARD: {
            'snake_fps': 14,      # Faster movement
            'walls_kill': True,   # Hitting walls = death
        },
    }

    def setup(self):
        """Initialize game state and load assets."""
        self.font = pygame.font.Font(None, 36)

        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.snake_fps = preset['snake_fps']
        self.walls_kill = preset['walls_kill']

        # Load food sprite (soupbowl)
        from engine import AssetLoader
        self.asset_loader = AssetLoader()
        self.food_img = self.asset_loader.load_image('soupbowl.png', (CELL_SIZE, CELL_SIZE))

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
        random.seed(42)  # Consistent pattern
        for _ in range(100):
            x = random.randint(0, WINDOW_WIDTH)
            y = random.randint(0, WINDOW_HEIGHT)
            w = random.randint(40, 100)
            h = random.randint(30, 60)
            pygame.draw.ellipse(self._background, MEADOW_DARK, (x, y, w, h))

        # Draw small flower dots with more variety
        flower_colors = [MEADOW_FLOWER_1, MEADOW_FLOWER_2, MEADOW_FLOWER_3,
                        MEADOW_FLOWER_4, MEADOW_FLOWER_5]
        for _ in range(90):
            x = random.randint(5, WINDOW_WIDTH - 5)
            y = random.randint(5, WINDOW_HEIGHT - 5)
            color = random.choice(flower_colors)
            size = random.randint(3, 7)
            pygame.draw.circle(self._background, color, (x, y), size)
            # Add golden center dot for some flowers
            if random.random() > 0.4:
                pygame.draw.circle(self._background, (255, 220, 100), (x, y), max(1, size // 2))

        # Draw tiny grass tufts
        tuft_color = (100, 160, 80)
        for _ in range(50):
            x = random.randint(10, WINDOW_WIDTH - 10)
            y = random.randint(10, WINDOW_HEIGHT - 10)
            for i in range(3):
                dx = random.randint(-3, 3)
                pygame.draw.line(self._background, tuft_color,
                               (x + dx, y), (x + dx + random.randint(-2, 2), y - random.randint(4, 8)), 1)

        # Draw very subtle grid lines
        grid_color = (155, 210, 130)  # Very subtle
        for gx in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self._background, grid_color, (gx, 0), (gx, WINDOW_HEIGHT), 1)
        for gy in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self._background, grid_color, (0, gy), (WINDOW_WIDTH, gy), 1)

        random.seed()  # Reset random seed

        # Initialize food sparkle effect
        self._food_sparkle_timer = 0
        self._food_sparkles = []

    def reset_game(self):
        """Reset game to initial state."""
        # Snake position (grid coordinates)
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2

        # Direction (0, 0) means waiting for first input
        self.direction = (0, 0)
        self.next_direction = (0, 0)  # Buffered direction change

        # Create snake as list of AnimatedFerret sprites
        # Each segment is a ferret at a grid position
        self.body_sprites = []
        self.snake = []  # Grid positions for collision detection

        # Create head ferret
        head_pixel_x = start_x * CELL_SIZE + CELL_SIZE // 2
        head_pixel_y = start_y * CELL_SIZE + CELL_SIZE // 2
        head = self._create_ferret_segment(head_pixel_x, head_pixel_y)
        head.set_state('idle')
        self.body_sprites.append(head)
        self.snake.append((start_x, start_y))

        # Create initial body segments (2 segments behind head)
        for i in range(1, 3):
            seg_x = (start_x - i) * CELL_SIZE + CELL_SIZE // 2
            seg_y = start_y * CELL_SIZE + CELL_SIZE // 2
            segment = self._create_ferret_segment(seg_x, seg_y)
            segment.set_state('idle')
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
        self.high_score = self.score_manager.get_high_score('snake')
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
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if (x, y) not in self.snake:
                return (x, y)

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
            if self.input_manager.action_pressed():
                self.reset_game()
                return False

        # Don't process movement during death animation
        if self.playing_death or self.playing_dig:
            return False

        # Get D-pad input
        dp = self.input_manager.get_dpad()

        # Buffer direction change (prevent 180-degree turns)
        if dp != (0, 0):
            # Check for valid direction change
            # Note: When waiting_for_input, prevent left since body starts to the left of head
            if dp[1] == -1 and self.direction != (0, 1):  # Up
                self.next_direction = (0, -1)
            elif dp[1] == 1 and self.direction != (0, -1):  # Down
                self.next_direction = (0, 1)
            elif dp[0] == -1 and self.direction != (1, 0) and not self.waiting_for_input:  # Left
                self.next_direction = (-1, 0)
            elif dp[0] == 1 and self.direction != (-1, 0):  # Right
                self.next_direction = (1, 0)

            # First input starts the game (only if a valid direction was set)
            if self.waiting_for_input and self.next_direction != (0, 0):
                self.waiting_for_input = False
                self.direction = self.next_direction
                # Set all ferrets to movement state
                for sprite in self.body_sprites:
                    sprite.set_state('movement')

        return False

    def update(self, dt):
        """Update game logic."""
        # Don't update when paused
        if self.paused:
            return

        # Update all ferret animations
        # Don't pass movement to ferret.update() since we handle position via grid
        for sprite in self.body_sprites:
            sprite.update(0, 0)

        # Handle death animation
        if self.playing_death:
            self.animation_timer += dt
            # Death animation lasts about 0.8 seconds (8 frames at ~10fps)
            if self.animation_timer >= 0.8:
                self.playing_death = False
                self.game_over = True
                # Check and save high score
                if self.score_manager.set_high_score('snake', self.score):
                    self.new_high_score = True
                    self.high_score = self.score
                # Check achievements
                self.achievements.unlock('snake_first')
                if self.score >= 50:
                    self.achievements.unlock('snake_50')
                if self.score >= 100:
                    self.achievements.unlock('snake_100')
                if self.difficulty == Difficulty.HARD and self.score >= 30:
                    self.achievements.unlock('snake_hard_win')
                # Track statistics
                self.stats.increment('snake', 'games_played')
                self.stats.increment('snake', 'deaths')
                self.stats.add('snake', 'total_score', self.score)
                self.stats.max_stat('snake', 'highest_length', len(self.snake))
                self.stats.increment('global', 'games_started')
            return

        # Handle dig animation (eating food)
        if self.playing_dig:
            self.animation_timer += dt
            # Dig animation is brief (~0.3 seconds)
            if self.animation_timer >= 0.3:
                self.playing_dig = False
                self.ferret.set_state('movement')
            return

        # Don't update if game over or waiting for input
        if self.game_over or self.waiting_for_input:
            return

        # Accumulate time for snake movement
        self.move_timer += dt

        if self.move_timer >= self.move_delay:
            self.move_timer = 0

            # Apply buffered direction
            if self.next_direction != (0, 0):
                self.direction = self.next_direction

            # Move snake
            if self.direction != (0, 0):
                self._move_snake()

    def _move_snake(self):
        """Move the snake one cell in the current direction."""
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # Check wall collision
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            if self.walls_kill:
                # Hard mode: walls kill
                self._trigger_death()
                return
            else:
                # Easy/Normal mode: wrap around edges
                new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)

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
            self.food = self._spawn_food()
            # Grow the snake (add new ferret at tail position)
            self._grow_snake(prev_positions[-1], prev_facings[-1])
            # Trigger dig animation on head
            self._trigger_dig()
        else:
            # Remove tail position from grid
            self.snake.pop()

    def _grow_snake(self, tail_pos, tail_facing):
        """Add a new AnimatedFerret segment at the tail position."""
        new_segment = self._create_ferret_segment(tail_pos[0], tail_pos[1])
        new_segment.set_state('movement')
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
            sprite.set_state('death')
        self.audio.play_sound(AudioManager.SOUND_DEATH)

    def _trigger_dig(self):
        """Trigger dig animation when eating food."""
        self.playing_dig = True
        self.animation_timer = 0
        self.ferret.set_state('dig')
        self.audio.play_sound(AudioManager.SOUND_COLLECT)

    def render(self):
        """Draw the game state."""
        import math

        # Draw cute meadow background (pre-generated with flowers)
        self.screen.blit(self._background, (0, 0))

        # Draw food with sparkle glow effect
        food_x = self.food[0] * CELL_SIZE
        food_y = self.food[1] * CELL_SIZE
        food_cx = food_x + CELL_SIZE // 2
        food_cy = food_y + CELL_SIZE // 2

        # Animate food sparkle timer
        self._food_sparkle_timer += 1

        # Draw pulsing glow behind food
        glow_pulse = abs(math.sin(self._food_sparkle_timer * 0.1)) * 0.5 + 0.5
        glow_size = int(CELL_SIZE * 0.8 + glow_pulse * 8)
        glow_alpha = int(80 + glow_pulse * 40)
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*SPARKLE_GOLD, glow_alpha), (glow_size, glow_size), glow_size)
        self.screen.blit(glow_surf, (food_cx - glow_size, food_cy - glow_size))

        # Draw sparkle stars around food
        for i in range(4):
            angle = (self._food_sparkle_timer * 0.05 + i * 1.57)
            dist = 18 + math.sin(self._food_sparkle_timer * 0.15 + i) * 5
            sx = food_cx + math.cos(angle) * dist
            sy = food_cy + math.sin(angle) * dist
            star_size = 3 + int(math.sin(self._food_sparkle_timer * 0.2 + i * 0.5) * 2)
            if star_size > 0:
                sparkle_surf = pygame.Surface((star_size * 2 + 2, star_size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.line(sparkle_surf, SPARKLE_WHITE, (0, star_size), (star_size * 2, star_size), 2)
                pygame.draw.line(sparkle_surf, SPARKLE_WHITE, (star_size, 0), (star_size, star_size * 2), 2)
                self.screen.blit(sparkle_surf, (int(sx - star_size), int(sy - star_size)))

        # Draw food sprite
        if self.food_img:
            self.screen.blit(self.food_img, (food_x, food_y))
        else:
            pygame.draw.rect(self.screen, (255, 100, 100), (food_x, food_y, CELL_SIZE, CELL_SIZE))

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
            pygame.draw.circle(self.screen, WEASEL_BROWN,
                             (int(ferret_sprite.x), int(ferret_sprite.y)), CELL_SIZE // 2 - 2)

    def _draw_game_over(self):
        """Draw game over overlay."""
        # Use cached overlay surface
        if not hasattr(self, '_game_over_overlay'):
            self._game_over_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._game_over_overlay.fill((0, 0, 0, 180))
        self.screen.blit(self._game_over_overlay, (0, 0))

        y_offset = -50 if self.new_high_score else -30

        # New high score message
        if self.new_high_score:
            hs_text = self.font.render("NEW HIGH SCORE!", True, (255, 215, 0))
            hs_rect = hs_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset))
            self.screen.blit(hs_text, hs_rect)
            y_offset += 40

        # Game over text
        go_text = self.font.render("GAME OVER", True, RED)
        go_rect = go_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset))
        self.screen.blit(go_text, go_rect)

        # Restart prompt
        restart_text = self.font.render("A/START restart, B menu", True, WHITE)
        restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset + 40))
        self.screen.blit(restart_text, restart_rect)

    def _draw_start_prompt(self):
        """Draw start prompt when waiting for first input."""
        prompt_text = self.font.render("D-pad or Arrows to start", True, WHITE)
        prompt_rect = prompt_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(prompt_text, prompt_rect)

    def run(self):
        """Override run to use SNAKE_FPS for timing but smooth render."""
        dt = 0

        while True:
            # Event processing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_m:
                        self.audio.toggle_mute()

            # Handle input
            if self.handle_input():
                return

            # Update with delta time
            self.update(dt)

            # Render
            self.render()

            # Display and timing (uses scaling in fullscreen mode)
            engine.scale_to_screen()
            dt = self.clock.tick(FPS) / 1000.0


def run_snake(screen, input_manager):
    """
    Entry point for running snake game from launcher.

    Args:
        screen: Pygame display surface
        input_manager: InputManager instance
    """
    game = SnakeGame(screen, input_manager)
    game.run()


# Allow running standalone for testing
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake - Weasel Entertainment System")

    from engine import InputManager
    input_manager = InputManager()

    game = SnakeGame(screen, input_manager)
    game.run()

    pygame.quit()
