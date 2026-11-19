"""
Ferret Crossing (Frogger) - A Winston Entertainment System Game

Help the ferret cross dangerous terrain! Navigate through traffic and ride
logs across the river to reach safety.

This game uses the AnimatedFerret sprite with proper animations:
- JUMP animation for each grid movement (hopping)
- IDLE while standing still or riding a log
- DEATH on car collision or drowning
- EMERGE animation when respawning at bottom
"""

import pygame
from collections import deque

from engine import (
    BaseGame,
    AnimatedFerret,
    AudioManager,
    Difficulty,
    get_score_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WHITE,
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
GRASS_CUTE = (120, 200, 130)  # Softer, brighter grass
GRASS_DARK_CUTE = (90, 170, 100)  # Darker grass accent
WATER_CUTE = (130, 200, 230)  # Prettier water blue
WATER_SHIMMER = (180, 230, 255)  # Water highlights
WATER_DARK = (80, 150, 200)  # Water shadows
ROAD_CUTE = (180, 175, 170)  # Softer gray road
ROAD_LINE = (255, 255, 200)  # Yellow road lines
LOG_CUTE = (160, 110, 70)  # Warmer brown logs
LOG_HIGHLIGHT = (190, 140, 90)  # Log highlights
SKY_BLUE = (200, 220, 255)  # Soft sky color
CLOUD_WHITE = (255, 255, 255)  # Cloud color


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
        rect = self.get_rect()
        if self.is_car:
            body = rect.inflate(-2, -12)
            paint = (183, 75, 60) if self.speed > 0 else (60, 110, 151)
            pygame.draw.rect(surface, (59, 51, 58), body, border_radius=7)
            pygame.draw.rect(surface, paint, body.inflate(-2, -2), border_radius=6)
            cab = pygame.Rect(0, 0, max(16, rect.width // 3), 10)
            cab.midbottom = (rect.centerx, body.centery)
            pygame.draw.rect(surface, (188, 220, 225), cab, border_radius=3)
            front = body.right - 5 if self.speed > 0 else body.left + 5
            pygame.draw.circle(surface, (255, 226, 157), (front, body.centery), 2)
            for x in (body.left + 11, body.right - 11):
                pygame.draw.circle(surface, (49, 46, 55), (x, body.bottom - 1), 5)
                pygame.draw.circle(surface, (165, 160, 150), (x, body.bottom - 1), 2)
        else:
            log = rect.inflate(0, -6)
            pygame.draw.rect(surface, self.color, log, border_radius=8)
            pygame.draw.rect(surface, (105, 66, 48), log, 2, border_radius=8)
            for x in range(log.left + 12, log.right - 15, 22):
                pygame.draw.line(surface, (139, 86, 60), (x, log.top + 8), (x + 14, log.top + 7), 2)
            ring = pygame.Rect(log.right - 10, log.top + 2, 9, log.height - 4)
            pygame.draw.ellipse(surface, (220, 164, 110), ring)
            pygame.draw.ellipse(surface, (139, 86, 60), ring.inflate(-4, -6), 1)

    def get_rect(self):
        """Get the collision rectangle."""
        return pygame.Rect(self.x, self.y, self.width, GRID)


class Lane:
    """A horizontal lane with obstacles or safe ground."""

    def __init__(
        self,
        row,
        lane_type="safe",
        color=None,
        num_obstacles=0,
        obstacle_length=0,
        spacing=0,
        speed=0,
    ):
        self.row = row
        self.y = row * GRID + PLAY_AREA_OFFSET_Y
        self.lane_type = lane_type
        self.color = color
        self.obstacles = []

        # Create obstacles based on lane type
        if lane_type in ("car", "log"):
            obstacle_color = (128, 128, 128) if lane_type == "car" else (185, 122, 87)
            is_car = lane_type == "car"
            for i in range(num_obstacles):
                self.obstacles.append(
                    Obstacle(
                        x=spacing * i,
                        y=self.y,
                        width=obstacle_length * GRID,
                        speed=speed,
                        color=obstacle_color,
                        is_car=is_car,
                    )
                )

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
        body = AnimatedFerret.body_rect(player_rect)
        for obs in self.obstacles:
            obstacle = obs.get_rect()
            if self.lane_type == "car" and body.colliderect(obstacle.inflate(-12, -14)):
                return True, False, 0
            if self.lane_type == "log" and obstacle.collidepoint(body.center):
                return False, True, obs.speed
        return False, False, 0


class FroggerGame(BaseGame):
    """Ferret Crossing - Help the ferret cross dangerous terrain!

    Controls:
    - D-pad/Arrow keys: Move the ferret (grid-based movement)
    - B/ESC: Return to menu
    - A/Enter/Start: Start game from title screen

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
            "speed_multiplier": 0.6,  # Slower traffic and logs
        },
        Difficulty.NORMAL: {
            "speed_multiplier": 1.0,  # Normal speed
        },
        Difficulty.HARD: {
            "speed_multiplier": 1.5,  # Faster traffic and logs
        },
    }

    def setup(self):
        """Initialize the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.speed_multiplier = preset["speed_multiplier"]

        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 42)
        self.level = 1
        self.crossings_this_level = 0
        self.pending_hops = deque(maxlen=2)

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
            frame_delay=4,  # Faster animation for hops
        )
        self.ferret.set_state("idle")

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
        self._build_scenery()

        # Game state
        self.lives = 3
        self.score = 0
        self.score_manager = get_score_manager()
        self.high_score = self.score_manager.get_high_score("frogger", self.difficulty)
        self.new_high_score = False
        self.highest_row = 12  # Tracks highest row reached (lower number = closer to goal)
        self.state = "START"  # START, PLAY, GAMEOVER
        self.paused = False
        self._deaths = 0  # Track deaths for stats
        self._crossings = 0  # Track crossings for stats

    def _create_lanes(self):
        """Create all game lanes."""
        gr = self.GRASS_COLOR
        wa = self.WATER_COLOR
        rd = self.ROAD_COLOR
        sm = self.speed_multiplier * min(1.6, 1 + (self.level - 1) * 0.10)

        self.lanes = [
            # Row 1: Goal (grass)
            Lane(1, color=gr),
            # Rows 2-5: Water with logs
            Lane(2, "log", wa, num_obstacles=2, obstacle_length=6, spacing=350, speed=1.2 * sm),
            Lane(3, "log", wa, num_obstacles=3, obstacle_length=2, spacing=180, speed=-1.6 * sm),
            Lane(4, "log", wa, num_obstacles=4, obstacle_length=2, spacing=140, speed=1.6 * sm),
            Lane(5, "log", wa, num_obstacles=2, obstacle_length=3, spacing=230, speed=-2 * sm),
            # Rows 6-7: Safe grass (median)
            Lane(6, color=gr),
            Lane(7, color=gr),
            # Rows 8-11: Road with cars
            Lane(8, "car", rd, num_obstacles=3, obstacle_length=2, spacing=180, speed=-2 * sm),
            Lane(9, "car", rd, num_obstacles=2, obstacle_length=4, spacing=240, speed=-1 * sm),
            Lane(10, "car", rd, num_obstacles=4, obstacle_length=2, spacing=130, speed=2.5 * sm),
            Lane(11, "car", rd, num_obstacles=3, obstacle_length=3, spacing=200, speed=1 * sm),
            # Row 12: Starting grass
            Lane(12, color=gr),
        ]
        for lane in self.lanes:
            for obstacle in lane.obstacles:
                obstacle.x = (obstacle.x + (self.level - 1) * 47) % WINDOW_WIDTH

    def _generate_decorations(self):
        """Generate cute decorations for the background."""
        rng = random.Random(42)

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
                x = rng.randint(10, WINDOW_WIDTH - 10)
                y = row * GRID + PLAY_AREA_OFFSET_Y + rng.randint(5, GRID - 5)
                color = rng.choice(flower_colors)
                size = rng.randint(3, 5)
                self._flowers.append((x, y, color, size))

        # Clouds in the sky area (above the play area)
        self._clouds = []
        for i in range(6):  # More clouds for bigger sky
            x = rng.randint(0, WINDOW_WIDTH)
            y = rng.randint(10, PLAY_AREA_OFFSET_Y - 20)
            size = rng.randint(15, 30)
            speed = rng.uniform(0.2, 0.5)
            self._clouds.append([x, y, size, speed])

        # Low-contrast ripples mark the water between floating logs.
        self._ripples = []
        water_rows = [2, 3, 4, 5]
        for row in water_rows:
            for _ in range(3):
                x = rng.randint(20, WINDOW_WIDTH - 20)
                y = row * GRID + PLAY_AREA_OFFSET_Y + rng.randint(8, GRID - 8)
                self._ripples.append((x, y))

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
        self.ferret.set_state("emerge")
        self.ferret.x = self.player_x + GRID // 2
        self.ferret.y = self.player_y + GRID // 2

    def _start_death(self):
        """Start the death animation sequence."""
        self.is_dying = True
        self.death_timer = 45  # About 0.75 seconds for death animation
        self.ferret.set_state("death")
        self.is_jumping = False
        self.audio.play_sound(AudioManager.SOUND_DEATH)
        self._deaths += 1  # Track death for stats

    def _move_player(self, dx, dy):
        """Move the player in the specified direction with jump animation."""
        if self.state != "PLAY" or self.is_dying or self.is_respawning or self.is_jumping:
            return
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
            self.ferret.set_state("jump")
            self.audio.play_sound(AudioManager.SOUND_JUMP)

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        # Handle state-specific input
        if self.state == "START":
            if self.input_manager.confirm_pressed():
                self.state = "PLAY"
            return False

        if self.state == "GAMEOVER":
            if self.input_manager.confirm_pressed():
                self.restart_session()
                self.setup()
                self.state = "PLAY"
                self._reset_player()
            return False

        # Check for pause toggle during PLAY state
        if self.state == "PLAY" and self.input_manager.pause_pressed():
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Capture short taps even while a hop, death or emergence animation runs.
        dp = self.input_manager.get_dpad()
        if (
            dp != self.last_dpad
            and dp != (0, 0)
            and len(self.pending_hops) < self.pending_hops.maxlen
        ):
            self.pending_hops.append((dp[0], 0) if dp[0] else (0, dp[1]))
        self.last_dpad = dp

        return False

    def update(self, dt):
        """Update game logic."""
        if self.state != "PLAY" or self.paused:
            return

        self.ferret.x = self.player_x + GRID // 2
        self.ferret.y = self.player_y + GRID // 2
        self.ferret.facing_right = self.facing_right
        self.ferret._advance_animation()
        self._anim_timer += 1
        for cloud in self._clouds:
            cloud[0] += cloud[3]
            if cloud[0] > WINDOW_WIDTH + cloud[2] * 2:
                cloud[0] = -cloud[2] * 2

        # Handle animation timers
        if self.is_jumping:
            self.jump_timer -= 1
            if self.jump_timer <= 0:
                self.is_jumping = False
                self.ferret.set_state("idle")

        if self.is_respawning:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.is_respawning = False
                self.ferret.set_state("idle")

        if self.is_dying:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.is_dying = False
                self.lives -= 1
                if self.lives <= 0:
                    # Check and save high score
                    if self.score_manager.set_high_score("frogger", self.score, self.difficulty):
                        self.new_high_score = True
                        self.high_score = self.score
                    # Track statistics
                    self._finalize_game_statistics()
                    self.state = "GAMEOVER"
                else:
                    self._reset_player()
            return  # Don't update game while dying

        old_position = (self.player_x, self.player_y)
        if self.pending_hops and not self.is_jumping and not self.is_respawning:
            self._move_player(*self.pending_hops.popleft())
        hopped = old_position != (self.player_x, self.player_y)

        # Update lanes
        for lane in self.lanes:
            lane.update()

        # Apply log movement if attached
        if self.attached_log_speed != 0 and not hopped:
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

        self.ferret.set_position(self.player_x + GRID // 2, self.player_y + GRID // 2)
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            player_rect = pygame.Rect(self.player_x, self.player_y, GRID, GRID)
            hit_car, on_log, log_speed = lane.check_collision(player_rect)

            if hit_car:
                # Car collision - death!
                self._start_death()
                return

            if lane.lane_type == "log":
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
                self.crossings_this_level += 1
                # Check achievements
                self.achievements.unlock("frogger_first")
                if self._crossings >= 5:
                    self.achievements.unlock("frogger_5")
                if self.difficulty == Difficulty.HARD:
                    self.achievements.unlock("frogger_hard")
                if self.crossings_this_level >= 5:
                    self.stats.increment("global", "games_completed")
                    self.stats.increment("frogger", "levels_cleared")
                    self.level += 1
                    self.crossings_this_level = 0
                    self.score += 500
                    self._create_lanes()
                self.pending_hops.clear()
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

    def _record_game_statistics(self):
        self.stats.increment("frogger", "deaths", self._deaths)
        self.stats.increment("frogger", "crossings", self._crossings)
        self.stats.add("frogger", "total_score", self.score)

    def _build_scenery(self):
        self._scenery = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for lane in self.lanes:
            lane.draw_background(self._scenery)
        for x, y in self._ripples:
            pygame.draw.arc(
                self._scenery, (159, 217, 235), (x - 9, y - 2, 18, 6), math.pi, math.tau, 1
            )
        for x, y, color, size in self._flowers:
            self._draw_flower(x, y, color, size, self._scenery)
        for lane in self.lanes:
            if lane.lane_type == "car":
                self._draw_road_markings(lane.row, self._scenery)
        self._cloud_images = {}
        for _, _, size, _ in self._clouds:
            cloud = pygame.Surface((size * 4, size * 2), pygame.SRCALPHA)
            for cx, cy, radius in (
                (size, size, size),
                (size * 2, int(size * 0.7), int(size * 1.1)),
                (size * 3, size, size),
            ):
                pygame.draw.circle(cloud, (*CLOUD_WHITE, 180), (cx, cy), radius)
            self._cloud_images[size] = cloud
        self._shimmer = pygame.Surface((30, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(self._shimmer, WATER_SHIMMER, (0, 0, 30, 6))

    def render(self):
        """Draw cached scenery, reusable effects and moving actors."""
        self.screen.fill(SKY_BLUE)
        for x, y, size, _ in self._clouds:
            self.screen.blit(self._cloud_images[size], (int(x - size), int(y - size // 2)))
        self.screen.blit(self._scenery, (0, 0))
        if self.state == "START":
            self._draw_title_screen()
            return
        for lane in self.lanes:
            if lane.lane_type == "log":
                self._draw_water_shimmer(lane.row)

        # Draw obstacles (cars/logs) on top of lane decorations
        for lane in self.lanes:
            lane.draw_obstacles(self.screen)

        # Draw the ferret
        self.ferret.draw(self.screen)

        # Draw HUD with shadow
        hud_text = f"Stage {self.level}  Goals: {self.crossings_this_level}/5  Lives: {self.lives}  Score: {self.score}  High: {self.high_score}  [B] Menu"
        shadow_surface = self.font.render(hud_text, False, (60, 80, 60))
        self.screen.blit(shadow_surface, (11, 11))
        text_surface = self.font.render(hud_text, False, WHITE)
        self.screen.blit(text_surface, (10, 10))

        if self.paused:
            self._draw_pause_overlay()
        elif self.state == "GAMEOVER":
            self._draw_game_over()

    def _draw_water_shimmer(self, row):
        """Draw animated water shimmer effects."""
        y = row * GRID + PLAY_AREA_OFFSET_Y
        shimmer_phase = self._anim_timer * 0.1
        for i in range(10):
            shimmer_x = (i * 90 + shimmer_phase * 30) % (WINDOW_WIDTH + 50) - 25
            shimmer_alpha = int(80 + 40 * math.sin(shimmer_phase + i))
            self._shimmer.set_alpha(shimmer_alpha)
            self.screen.blit(self._shimmer, (int(shimmer_x), y + 12))

    def _draw_flower(self, x, y, color, size, target):
        """Draw a simple cute flower."""
        # Petals
        for angle in range(0, 360, 72):
            rad = math.radians(angle)
            px = x + int(size * 0.6 * math.cos(rad))
            py = y + int(size * 0.6 * math.sin(rad))
            pygame.draw.circle(target, color, (px, py), size)
        # Yellow center
        pygame.draw.circle(target, (255, 220, 100), (x, y), max(1, size // 2))

    def _draw_road_markings(self, row, target):
        """Draw dashed yellow center line on road."""
        y = row * GRID + PLAY_AREA_OFFSET_Y + GRID // 2 - 1
        for x in range(0, WINDOW_WIDTH, 40):
            pygame.draw.rect(target, ROAD_LINE, (x + 5, y, 20, 3))

    def _draw_title_screen(self):
        """Draw the title/start screen."""
        # Draw a preview of the game
        for lane in self.lanes:
            lane.draw(self.screen)

        # Draw overlay (use cached surface)
        if not hasattr(self, "_title_overlay"):
            self._title_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._title_overlay.fill((0, 0, 0, 128))
        self.screen.blit(self._title_overlay, (0, 0))

        # Draw title (use pre-created font from setup)
        title = self.title_font.render("Ferret Crossing", False, WHITE)
        self.screen.blit(
            title, (WINDOW_WIDTH // 2 - title.get_width() // 2, WINDOW_HEIGHT // 2 - 40)
        )

        # Draw instructions
        instructions = self.font.render("A/Enter/Start to play, B to return to menu", False, WHITE)
        self.screen.blit(
            instructions,
            (WINDOW_WIDTH // 2 - instructions.get_width() // 2, WINDOW_HEIGHT // 2 + 10),
        )

    def _draw_game_over(self):
        self._draw_game_over_overlay(score=self.score)
