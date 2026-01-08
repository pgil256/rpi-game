"""
Ferret Crossing (Frogger) - A Weasel Entertainment System Game

Help the ferret cross dangerous terrain! Navigate through traffic and ride
logs across the river to reach safety.

This game uses the AnimatedFerret sprite with proper animations:
- JUMP animation for each grid movement (hopping)
- IDLE while standing still or riding a log
- DEATH on car collision or drowning
- EMERGE animation when respawning at bottom
"""

import pygame
import sys

from engine import (
    BaseGame,
    AnimatedFerret,
    AudioManager,
    Difficulty,
    get_score_manager,
    get_stats_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    BLACK,
    WHITE,
    RED,
    get_weasel_color,
)

import math
import random

# Lane configuration constants
GRID = 32
ROWS = WINDOW_HEIGHT // GRID
# Vertical offset to center the play area
# Play area: rows 1-12, from y=32 to y=416 (384px height), centered in 600px window
# Center of play: (32+416)/2 = 224px, window center: 300px, offset: 300-224 = 76px
PLAY_AREA_OFFSET_Y = 76

# Enhanced cute color palette
GRASS_CUTE = (120, 200, 130)          # Softer, brighter grass
GRASS_DARK_CUTE = (90, 170, 100)      # Darker grass accent
WATER_CUTE = (130, 200, 230)          # Prettier water blue
WATER_SHIMMER = (180, 230, 255)       # Water highlights
WATER_DARK = (80, 150, 200)           # Water shadows
ROAD_CUTE = (180, 175, 170)           # Softer gray road
ROAD_LINE = (255, 255, 200)           # Yellow road lines
LOG_CUTE = (160, 110, 70)             # Warmer brown logs
LOG_HIGHLIGHT = (190, 140, 90)        # Log highlights
SKY_BLUE = (200, 220, 255)            # Soft sky color
CLOUD_WHITE = (255, 255, 255)         # Cloud color
LILY_PAD = (100, 180, 100)            # Lily pad green
LILY_FLOWER = (255, 200, 220)         # Pink lily flower


class Obstacle:
    """A moving obstacle (car or log) in a lane."""

    def __init__(self, x, y, width, speed, color, is_car=False):
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed
        self.color = color
        self.is_car = is_car

    def update(self):
        """Move the obstacle and wrap around screen edges."""
        self.x += self.speed
        if self.speed > 0 and self.x > WINDOW_WIDTH + GRID:
            self.x = -self.width
        elif self.speed < 0 and self.x < -self.width:
            self.x = WINDOW_WIDTH

    def draw(self, surface):
        """Draw the obstacle to the surface."""
        if self.is_car:
            # Draw car with weasel palette (segmented)
            num_segments = max(1, int(self.width / GRID))
            for i in range(num_segments):
                seg_x = self.x + i * GRID
                color = get_weasel_color(i)
                pygame.draw.rect(surface, color, (seg_x, self.y, GRID, GRID))
        else:
            # Logs are brown
            pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, GRID))

    def get_rect(self):
        """Get the collision rectangle."""
        return pygame.Rect(self.x, self.y, self.width, GRID)


class Lane:
    """A horizontal lane with obstacles or safe ground."""

    def __init__(self, row, lane_type='safe', color=None, num_obstacles=0,
                 obstacle_length=0, spacing=0, speed=0):
        self.row = row
        self.y = row * GRID + PLAY_AREA_OFFSET_Y
        self.lane_type = lane_type
        self.color = color
        self.obstacles = []

        # Create obstacles based on lane type
        if lane_type in ('car', 'log'):
            obstacle_color = (128, 128, 128) if lane_type == 'car' else (185, 122, 87)
            is_car = (lane_type == 'car')
            for i in range(num_obstacles):
                self.obstacles.append(Obstacle(
                    x=spacing * i,
                    y=self.y,
                    width=obstacle_length * GRID,
                    speed=speed,
                    color=obstacle_color,
                    is_car=is_car
                ))

    def update(self):
        """Update all obstacles in this lane."""
        for obs in self.obstacles:
            obs.update()

    def draw_background(self, surface):
        """Draw just the lane background color."""
        if self.color:
            pygame.draw.rect(surface, self.color, (0, self.y, WINDOW_WIDTH, GRID))

    def draw_obstacles(self, surface):
        """Draw the obstacles (cars/logs) on top of everything."""
        for obs in self.obstacles:
            obs.draw(surface)

    def draw(self, surface):
        """Draw the lane background and obstacles."""
        self.draw_background(surface)
        self.draw_obstacles(surface)

    def check_collision(self, player_rect):
        """Check collision with player.

        Returns:
            tuple: (hit_car, riding_log, log_speed)
            - hit_car: True if player collided with a car
            - riding_log: True if player is on a log
            - log_speed: Speed of the log being ridden (0 if not on log)
        """
        for obs in self.obstacles:
            if player_rect.colliderect(obs.get_rect()):
                if self.lane_type == 'car':
                    return (True, False, 0)
                if self.lane_type == 'log':
                    return (False, True, obs.speed)

        # In water but not on a log = drowning
        if self.lane_type == 'log':
            return (False, False, 0)  # Will be interpreted as drowning

        return (False, False, 0)


class FroggerGame(BaseGame):
    """Ferret Crossing - Help the ferret cross dangerous terrain!

    Controls:
    - D-pad/Arrow keys: Move the ferret (grid-based movement)
    - B/ESC: Return to menu
    - A/START: Start game from title screen

    The ferret must navigate through traffic lanes and ride logs
    across the river to reach the goal at the top.
    """

    # Lane colors - using enhanced cute palette
    GRASS_COLOR = GRASS_CUTE
    WATER_COLOR = WATER_CUTE
    ROAD_COLOR = ROAD_CUTE

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            'speed_multiplier': 0.6,   # Slower traffic and logs
        },
        Difficulty.NORMAL: {
            'speed_multiplier': 1.0,   # Normal speed
        },
        Difficulty.HARD: {
            'speed_multiplier': 1.5,   # Faster traffic and logs
        },
    }

    def setup(self):
        """Initialize the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.speed_multiplier = preset['speed_multiplier']

        self.font = pygame.font.SysFont('Courier New', 16)
        self.title_font = pygame.font.SysFont('Courier New', 32)  # Pre-create fonts

        # Animation timer for water shimmer and other effects
        self._anim_timer = 0

        # Generate background decorations (flowers, clouds)
        self._generate_decorations()

        # Create the animated ferret player
        # Start at row 12 (the bottom grass lane in our lane configuration)
        start_row = 12
        self.ferret = AnimatedFerret(
            x=WINDOW_WIDTH // 2,
            y=start_row * GRID + PLAY_AREA_OFFSET_Y + GRID // 2,  # Center of bottom lane (row 12)
            scale=1,  # 32x32 to match grid
            speed=0,  # We handle position directly
            frame_delay=4  # Faster animation for hops
        )
        self.ferret.set_state('idle')

        # Player grid position (separate from ferret visual position)
        self.player_x = WINDOW_WIDTH // 2 - GRID // 2
        self.player_y = start_row * GRID + PLAY_AREA_OFFSET_Y  # Row 12 = start position

        # Facing direction for the ferret
        self.facing_right = True

        # Animation state tracking
        self.is_jumping = False
        self.jump_timer = 0
        self.is_dying = False
        self.death_timer = 0
        self.is_respawning = False
        self.respawn_timer = 0

        # Movement tracking for edge detection
        self.last_dpad = (0, 0)

        # Log attachment
        self.attached_log_speed = 0

        # Create lanes (from top to bottom, rows 1-12)
        self._create_lanes()

        # Game state
        self.lives = 3
        self.score = 0
        self.score_manager = get_score_manager()
        self.stats = get_stats_manager()
        self.high_score = self.score_manager.get_high_score('frogger')
        self.new_high_score = False
        self.highest_row = 12  # Tracks highest row reached (lower number = closer to goal)
        self.state = 'START'  # START, PLAY, GAMEOVER
        self.paused = False
        self._deaths = 0  # Track deaths for stats
        self._crossings = 0  # Track crossings for stats

    def _create_lanes(self):
        """Create all game lanes."""
        gr = self.GRASS_COLOR
        wa = self.WATER_COLOR
        rd = self.ROAD_COLOR
        sm = self.speed_multiplier  # Difficulty-based speed multiplier

        self.lanes = [
            # Row 1: Goal (grass)
            Lane(1, color=gr),
            # Rows 2-5: Water with logs
            Lane(2, 'log', wa, num_obstacles=2, obstacle_length=6, spacing=350, speed=1.2 * sm),
            Lane(3, 'log', wa, num_obstacles=3, obstacle_length=2, spacing=180, speed=-1.6 * sm),
            Lane(4, 'log', wa, num_obstacles=4, obstacle_length=2, spacing=140, speed=1.6 * sm),
            Lane(5, 'log', wa, num_obstacles=2, obstacle_length=3, spacing=230, speed=-2 * sm),
            # Rows 6-7: Safe grass (median)
            Lane(6, color=gr),
            Lane(7, color=gr),
            # Rows 8-11: Road with cars
            Lane(8, 'car', rd, num_obstacles=3, obstacle_length=2, spacing=180, speed=-2 * sm),
            Lane(9, 'car', rd, num_obstacles=2, obstacle_length=4, spacing=240, speed=-1 * sm),
            Lane(10, 'car', rd, num_obstacles=4, obstacle_length=2, spacing=130, speed=2.5 * sm),
            Lane(11, 'car', rd, num_obstacles=3, obstacle_length=3, spacing=200, speed=1 * sm),
            # Row 12: Starting grass
            Lane(12, color=gr),
        ]

    def _generate_decorations(self):
        """Generate cute decorations for the background."""
        random.seed(42)  # Consistent decorations

        # Flowers on grass lanes
        self._flowers = []
        grass_rows = [1, 6, 7, 12]
        flower_colors = [
            (255, 200, 220),  # Pink
            (255, 255, 180),  # Yellow
            (200, 220, 255),  # Blue
            (255, 220, 255),  # Lavender
        ]
        for row in grass_rows:
            for _ in range(8):
                x = random.randint(10, WINDOW_WIDTH - 10)
                y = row * GRID + PLAY_AREA_OFFSET_Y + random.randint(5, GRID - 5)
                color = random.choice(flower_colors)
                size = random.randint(3, 5)
                self._flowers.append((x, y, color, size))

        # Clouds in the sky area (above the play area)
        self._clouds = []
        for i in range(6):  # More clouds for bigger sky
            x = random.randint(0, WINDOW_WIDTH)
            y = random.randint(10, PLAY_AREA_OFFSET_Y - 20)  # Spread across sky area
            size = random.randint(15, 30)
            speed = random.uniform(0.2, 0.5)
            self._clouds.append([x, y, size, speed])

        # Lily pads on water lanes
        self._lily_pads = []
        water_rows = [2, 3, 4, 5]
        for row in water_rows:
            for _ in range(3):
                x = random.randint(20, WINDOW_WIDTH - 20)
                y = row * GRID + PLAY_AREA_OFFSET_Y + random.randint(8, GRID - 8)
                has_flower = random.random() > 0.5
                self._lily_pads.append((x, y, has_flower))

        random.seed()

    def _reset_player(self):
        """Reset player to starting position."""
        start_row = 12  # Bottom grass lane
        self.player_x = WINDOW_WIDTH // 2 - GRID // 2
        self.player_y = start_row * GRID + PLAY_AREA_OFFSET_Y
        self.attached_log_speed = 0
        self.highest_row = start_row  # Reset to bottom (lower number = closer to goal)
        self.is_jumping = False
        self.is_dying = False

        # Play emerge animation when respawning
        self.is_respawning = True
        self.respawn_timer = 30  # About 0.5 seconds at 60 FPS
        self.ferret.set_state('emerge')

    def _start_death(self):
        """Start the death animation sequence."""
        self.is_dying = True
        self.death_timer = 45  # About 0.75 seconds for death animation
        self.ferret.set_state('death')
        self.is_jumping = False
        self.audio.play_sound(AudioManager.SOUND_DEATH)
        self._deaths += 1  # Track death for stats

    def _move_player(self, dx, dy):
        """Move the player in the specified direction with jump animation."""
        # Constrain movement to the play area (rows 1-12 with offset)
        min_y = GRID + PLAY_AREA_OFFSET_Y  # Top of row 1 (goal)
        max_y = 12 * GRID + PLAY_AREA_OFFSET_Y  # Top of row 12 (start)
        new_x = max(0, min(WINDOW_WIDTH - GRID, self.player_x + dx * GRID))
        new_y = max(min_y, min(max_y, self.player_y + dy * GRID))

        if new_x != self.player_x or new_y != self.player_y:
            self.player_x = new_x
            self.player_y = new_y

            # Update facing direction based on horizontal movement
            if dx > 0:
                self.facing_right = True
            elif dx < 0:
                self.facing_right = False

            # Start jump animation for hopping
            self.is_jumping = True
            self.jump_timer = 8  # About 0.13 seconds at 60 FPS
            self.ferret.set_state('jump')

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        # Handle state-specific input
        if self.state == 'START':
            if self.input_manager.action_pressed():
                self.state = 'PLAY'
            return False

        if self.state == 'GAMEOVER':
            if self.input_manager.action_pressed():
                self.lives = 3
                self.score = 0
                self.state = 'PLAY'
                self._reset_player()
            return False

        # Check for pause toggle during PLAY state
        if self.state == 'PLAY' and self.input_manager.pause_pressed():
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # PLAY state - handle movement (only when not animating)
        if not self.is_jumping and not self.is_dying and not self.is_respawning:
            dp = self.input_manager.get_dpad()

            # Edge detection for grid movement
            if dp != self.last_dpad:
                if dp[0] != 0:
                    self._move_player(dp[0], 0)
                elif dp[1] != 0:
                    self._move_player(0, dp[1])

            self.last_dpad = dp

        return False

    def update(self, dt):
        """Update game logic."""
        if self.state != 'PLAY' or self.paused:
            return

        # Handle animation timers
        if self.is_jumping:
            self.jump_timer -= 1
            if self.jump_timer <= 0:
                self.is_jumping = False
                self.ferret.set_state('idle')

        if self.is_respawning:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.is_respawning = False
                self.ferret.set_state('idle')

        if self.is_dying:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.is_dying = False
                self.lives -= 1
                if self.lives <= 0:
                    # Check and save high score
                    if self.score_manager.set_high_score('frogger', self.score):
                        self.new_high_score = True
                        self.high_score = self.score
                    # Track statistics
                    self.stats.increment('frogger', 'games_played')
                    self.stats.increment('frogger', 'deaths', self._deaths)
                    self.stats.increment('frogger', 'crossings', self._crossings)
                    self.stats.increment('global', 'games_started')
                    self.state = 'GAMEOVER'
                    self.lives = 3
                else:
                    self._reset_player()
            return  # Don't update game while dying

        # Update lanes
        for lane in self.lanes:
            lane.update()

        # Apply log movement if attached
        if self.attached_log_speed != 0:
            self.player_x += self.attached_log_speed
            # Check if carried off screen by log - causes death
            if self.player_x < -GRID // 2 or self.player_x > WINDOW_WIDTH - GRID // 2:
                self._start_death()
                return

        # Check lane collisions
        # Convert player_y (with offset) back to lane row, then to lane index
        lane_row = (self.player_y - PLAY_AREA_OFFSET_Y) // GRID
        lane_index = lane_row - 1  # Lanes are stored as rows 1-12, so index = row - 1
        self.attached_log_speed = 0

        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            player_rect = pygame.Rect(self.player_x, self.player_y, GRID, GRID)
            hit_car, on_log, log_speed = lane.check_collision(player_rect)

            if hit_car:
                # Car collision - death!
                self._start_death()
                return

            if lane.lane_type == 'log':
                if on_log:
                    self.attached_log_speed = log_speed
                else:
                    # In water but not on log - drowning!
                    self._start_death()
                    return

        # Check for reaching the goal (row 1 = top safe zone)
        # Lane rows are 1-12 from top to bottom, player_y is pixel position with offset
        # Row 1 (goal) is at y = GRID + PLAY_AREA_OFFSET_Y
        current_row = (self.player_y - PLAY_AREA_OFFSET_Y) // GRID  # 1 = top goal, 12 = start

        if current_row < self.highest_row:
            # Player moved up (lower row number = higher on screen)
            if current_row <= 1:
                # Reached the top goal (row 1)!
                self.score += 200
                self.audio.play_sound(AudioManager.SOUND_VICTORY)
                # Track successful crossings
                self._crossings += 1
                # Check achievements
                self.achievements.unlock('frogger_first')
                if self._crossings >= 5:
                    self.achievements.unlock('frogger_5')
                if self.difficulty == Difficulty.HARD:
                    self.achievements.unlock('frogger_hard')
                self._reset_player()
            else:
                # Progress bonus for each new row reached
                self.score += 10
                self.audio.play_sound(AudioManager.SOUND_COLLECT)
                self.highest_row = current_row

        self.high_score = max(self.high_score, self.score)

        # Update ferret visual position to match player position
        self.ferret.x = self.player_x + GRID // 2
        self.ferret.y = self.player_y + GRID // 2
        self.ferret.facing_right = self.facing_right

        # Update ferret animation (this advances frames)
        self.ferret.update(0, 0)

    def render(self):
        """Draw the game state to the screen."""
        # Soft sky blue background
        self.screen.fill(SKY_BLUE)

        # Update animation timer
        self._anim_timer += 1

        # Update and draw clouds
        for cloud in self._clouds:
            cloud[0] += cloud[3]  # Move cloud
            if cloud[0] > WINDOW_WIDTH + cloud[2] * 2:
                cloud[0] = -cloud[2] * 2
            self._draw_cloud(cloud[0], cloud[1], cloud[2])

        if self.state == 'START':
            self._draw_title_screen()
            return

        # Draw lane backgrounds first
        for lane in self.lanes:
            lane.draw_background(self.screen)

        # Draw water shimmer effects on water lanes
        for lane in self.lanes:
            if lane.lane_type == 'log':
                self._draw_water_shimmer(lane.row)

        # Draw lily pads on water
        for x, y, has_flower in self._lily_pads:
            self._draw_lily_pad(x, y, has_flower)

        # Draw flowers on grass lanes
        for x, y, color, size in self._flowers:
            self._draw_flower(x, y, color, size)

        # Draw road lane markings
        for lane in self.lanes:
            if lane.lane_type == 'car':
                self._draw_road_markings(lane.row)

        # Draw obstacles (cars/logs) on top of lane decorations
        for lane in self.lanes:
            lane.draw_obstacles(self.screen)

        # Draw the ferret
        self.ferret.draw(self.screen)

        # Draw HUD with shadow
        hud_text = f"Lives: {self.lives}  Score: {self.score}  High: {self.high_score}  [B] Menu"
        shadow_surface = self.font.render(hud_text, False, (60, 80, 60))
        self.screen.blit(shadow_surface, (11, 11))
        text_surface = self.font.render(hud_text, False, WHITE)
        self.screen.blit(text_surface, (10, 10))

        if self.paused:
            self._draw_pause_overlay()
        elif self.state == 'GAMEOVER':
            self._draw_game_over()

    def _draw_cloud(self, x, y, size):
        """Draw a cute fluffy cloud."""
        cloud_surf = pygame.Surface((size * 4, size * 2), pygame.SRCALPHA)
        alpha = 180
        color = (*CLOUD_WHITE, alpha)
        pygame.draw.circle(cloud_surf, color, (size, size), size)
        pygame.draw.circle(cloud_surf, color, (size * 2, int(size * 0.7)), int(size * 1.1))
        pygame.draw.circle(cloud_surf, color, (size * 3, size), size)
        self.screen.blit(cloud_surf, (int(x - size), int(y - size // 2)))

    def _draw_water_shimmer(self, row):
        """Draw animated water shimmer effects."""
        y = row * GRID + PLAY_AREA_OFFSET_Y
        shimmer_phase = self._anim_timer * 0.1
        for i in range(10):
            shimmer_x = (i * 90 + shimmer_phase * 30) % (WINDOW_WIDTH + 50) - 25
            shimmer_alpha = int(80 + 40 * math.sin(shimmer_phase + i))
            shimmer_surf = pygame.Surface((30, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(shimmer_surf, (*WATER_SHIMMER, shimmer_alpha), (0, 0, 30, 6))
            self.screen.blit(shimmer_surf, (int(shimmer_x), y + 12))

    def _draw_lily_pad(self, x, y, has_flower):
        """Draw a cute lily pad with optional flower."""
        # Green pad
        pad_surf = pygame.Surface((20, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(pad_surf, LILY_PAD, (0, 2, 20, 12))
        # Notch in the pad
        pygame.draw.polygon(pad_surf, (0, 0, 0, 0), [(10, 8), (12, 0), (8, 0)])
        self.screen.blit(pad_surf, (x - 10, y - 8))
        # Pink flower
        if has_flower:
            flower_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(flower_surf, LILY_FLOWER, (5, 5), 4)
            pygame.draw.circle(flower_surf, (255, 255, 200), (5, 5), 2)
            self.screen.blit(flower_surf, (x - 5, y - 10))

    def _draw_flower(self, x, y, color, size):
        """Draw a simple cute flower."""
        # Petals
        for angle in range(0, 360, 72):
            rad = math.radians(angle)
            px = x + int(size * 0.6 * math.cos(rad))
            py = y + int(size * 0.6 * math.sin(rad))
            pygame.draw.circle(self.screen, color, (px, py), size)
        # Yellow center
        pygame.draw.circle(self.screen, (255, 220, 100), (x, y), max(1, size // 2))

    def _draw_road_markings(self, row):
        """Draw dashed yellow center line on road."""
        y = row * GRID + PLAY_AREA_OFFSET_Y + GRID // 2 - 1
        for x in range(0, WINDOW_WIDTH, 40):
            pygame.draw.rect(self.screen, ROAD_LINE, (x + 5, y, 20, 3))

    def _draw_title_screen(self):
        """Draw the title/start screen."""
        # Draw a preview of the game
        for lane in self.lanes:
            lane.draw(self.screen)

        # Draw overlay (use cached surface)
        if not hasattr(self, '_title_overlay'):
            self._title_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._title_overlay.fill((0, 0, 0, 128))
        self.screen.blit(self._title_overlay, (0, 0))

        # Draw title (use pre-created font from setup)
        title = self.title_font.render("Ferret Crossing", False, WHITE)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, WINDOW_HEIGHT // 2 - 40))

        # Draw instructions
        instructions = self.font.render("A/START to play, B to return to menu", False, WHITE)
        self.screen.blit(instructions, (WINDOW_WIDTH // 2 - instructions.get_width() // 2, WINDOW_HEIGHT // 2 + 10))

    def _draw_game_over(self):
        """Draw the game over overlay."""
        # Use cached overlay surface
        if not hasattr(self, '_game_over_overlay'):
            self._game_over_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._game_over_overlay.fill((0, 0, 0, 180))
        self.screen.blit(self._game_over_overlay, (0, 0))

        y_offset = -50 if self.new_high_score else -30

        # New high score message
        if self.new_high_score:
            hs_text = self.title_font.render("NEW HIGH SCORE!", False, (255, 215, 0))
            self.screen.blit(hs_text, (WINDOW_WIDTH // 2 - hs_text.get_width() // 2, WINDOW_HEIGHT // 2 + y_offset))
            y_offset += 40

        # Use pre-created font from setup
        game_over = self.title_font.render("GAME OVER", False, RED)
        self.screen.blit(game_over, (WINDOW_WIDTH // 2 - game_over.get_width() // 2, WINDOW_HEIGHT // 2 + y_offset))

        restart = self.font.render("A/START to restart, B for menu", False, WHITE)
        self.screen.blit(restart, (WINDOW_WIDTH // 2 - restart.get_width() // 2, WINDOW_HEIGHT // 2 + y_offset + 50))


def run_frogger(screen, input_manager):
    """Entry point for the Frogger game.

    Args:
        screen: The pygame display surface.
        input_manager: The InputManager instance.
    """
    game = FroggerGame(screen, input_manager)
    game.run()
