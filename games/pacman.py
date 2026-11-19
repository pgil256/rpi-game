"""
Tunnel Treats maze game implementation for the Winston Entertainment System.

Uses AnimatedFerret for the player with directional animations and death sequence.
Ghosts are represented by original garden critter artwork.
Power pellets (large soupbowls) allow the player to eat ghosts temporarily.
"""

import os
import sys
import math
import random
from collections import deque
import pygame
from typing import Optional, Tuple, List

# Add parent directory to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import (
    BaseGame,
    AnimatedFerret,
    AssetLoader,
    AudioManager,
    Difficulty,
    get_score_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WHITE,
    YELLOW,
    BLUE,
)

# Enhanced cute color palette for underground cave theme
CAVE_BG_DARK = (25, 20, 40)  # Deep purple-black background
CAVE_BG_MID = (40, 30, 60)  # Slightly lighter cave
CAVE_WALL_GLOW = (180, 140, 200)  # Soft purple wall glow
MAZE_WALL_CUTE = (160, 120, 180)  # Softer lavender walls
PELLET_GLOW = (255, 255, 200)  # Warm yellow glow
POWER_PELLET_GLOW = (255, 200, 255)  # Pink power pellet glow


class Wall(pygame.sprite.Sprite):
    """A wall segment in the maze."""

    def __init__(self, x: int, y: int, w: int, h: int, color: tuple):
        super().__init__()
        self.image = pygame.Surface([w, h])
        self.image.fill(color)
        self.rect = self.image.get_rect(top=y, left=x)


PEN_EXIT = (303, 213)
PEN_CENTER = (303, 273)


class MazeRoutes:
    """Connected corridor centers, with the pen gate closed to roaming enemies."""

    def __init__(self, walls, gate):
        blockers = [sprite.rect for sprite in (*walls, *gate)]
        boxes = {}
        for y in range(33, 574, 30):
            for x in range(33, 574, 30):
                rect = pygame.Rect(x - 10, y - 10, 20, 20)
                if rect.collidelist(blockers) < 0:
                    boxes[x, y] = rect
        self.neighbors = {}
        pending = [PEN_EXIT]
        while pending:
            node = pending.pop()
            if node in self.neighbors:
                continue
            x, y = node
            neighbors = []
            for other in ((x - 30, y), (x + 30, y), (x, y - 30), (x, y + 30)):
                if other in boxes and boxes[node].union(boxes[other]).collidelist(blockers) < 0:
                    neighbors.append(other)
            self.neighbors[node] = neighbors
            pending.extend(neighbors)
        self._distances = {}

    def next_node(self, node, target, previous=None):
        goal = min(self.neighbors, key=lambda p: (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2)
        if goal not in self._distances:
            distances = {goal: 0}
            queue = deque([goal])
            while queue:
                current = queue.popleft()
                for other in self.neighbors[current]:
                    if other not in distances:
                        distances[other] = distances[current] + 1
                        queue.append(other)
            self._distances[goal] = distances
        choices = self.neighbors[node]
        forward = [point for point in choices if point != previous]
        return min(forward or choices, key=self._distances[goal].__getitem__)


class Ghost(pygame.sprite.Sprite):
    """A ghost enemy with AI-driven chase behavior."""

    # Ghost behavior modes
    MODE_CHASE = "chase"
    MODE_SCATTER = "scatter"
    MODE_FRIGHTENED = "frightened"
    MODE_EATEN = "eaten"

    # Speed settings
    NORMAL_SPEED = 2.3  # Normal movement speed (closer to player speed)
    CRUISE_ELROY_SPEED = 2.7  # Blinky's speed when few pellets remain
    CRUISE_ELROY2_SPEED = 3.0  # Even faster when very few pellets remain
    FRIGHTENED_SPEED = 1.2  # Slower when vulnerable
    EATEN_SPEED = 4.0  # Fast when returning to spawn

    # Flash colors for frightened mode (soup can colors cycling)
    FLASH_COLORS = [
        (255, 100, 100),  # Light red
        (100, 100, 255),  # Light blue
        (255, 255, 100),  # Yellow
        (100, 255, 100),  # Green
    ]

    def __init__(
        self,
        x: int,
        y: int,
        normal_image: pygame.Surface,
        frightened_image: pygame.Surface,
        ghost_type: str,
        spawn_pos: Tuple[int, int],
    ):
        super().__init__()
        self.normal_image = normal_image
        self.frightened_image = frightened_image  # Not used anymore, kept for API compat
        self.image = normal_image
        self.rect = self.image.get_rect(center=(x, y))
        self.ghost_type = ghost_type  # 'blinky', 'pinky', 'inky', 'clyde'
        self.spawn_pos = spawn_pos
        self.mode = self.MODE_CHASE
        self.direction = (0, 0)
        self.frightened_timer = 0
        self.flash_timer = 0
        self.consecutive_ghost_bonus = 0  # For increasing ghost eat scores

        # Position as float for smooth movement
        self.x = float(x)
        self.y = float(y)

        self.routes = None
        self._previous_node = None
        self._waypoint = None
        self._pen_path = deque()

        # Scatter/chase cycle timer (for better AI pacing)
        self.mode_timer = 0
        self.scatter_duration = 180  # 3 seconds scatter (shorter = more aggressive)
        self.chase_duration = 1200  # 20 seconds chase

        # Spawn delay - ghosts wait in pen before emerging
        self.spawn_delay = 0  # Frames to wait before leaving spawn
        self.in_spawn = True  # Whether ghost is still in spawn pen

        # Cruise Elroy mode for Blinky (speeds up when few pellets left)
        self.elroy_mode = 0  # 0=normal, 1=elroy1, 2=elroy2
        self._tinted_images = {
            color: self._create_tinted_image(color) for color in self.FLASH_COLORS
        }
        self._eyes_image = pygame.Surface((30, 30), pygame.SRCALPHA)
        for x in (10, 20):
            pygame.draw.circle(self._eyes_image, WHITE, (x, 12), 5)
            pygame.draw.circle(self._eyes_image, BLUE, (x, 12), 2)

    def _create_tinted_image(self, color: Tuple[int, int, int]) -> pygame.Surface:
        """Keep the transparent silhouette while flashing the critter's markings."""
        tinted = self.normal_image.copy()
        tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        tinted.fill(tuple(value // 3 for value in color), special_flags=pygame.BLEND_RGB_ADD)
        return tinted

    def set_frightened(self, duration: int):
        """Enter frightened mode for the given number of frames."""
        if self.mode != self.MODE_EATEN:
            self.mode = self.MODE_FRIGHTENED
            self.frightened_timer = duration
            self.flash_timer = 0
            if not self.in_spawn and self._waypoint and self._previous_node:
                self._waypoint, self._previous_node = self._previous_node, self._waypoint

    def get_eaten(self):
        """Ghost was eaten by player - return to spawn."""
        self.mode = self.MODE_EATEN
        self.frightened_timer = 0

    def update(
        self,
        walls: pygame.sprite.Group,
        player_pos: Tuple[int, int],
        player_dir: Tuple[int, int],
        blinky_pos: Optional[Tuple[int, int]] = None,
        gate: Optional[pygame.sprite.Group] = None,
        *,
        power_ticks=None,
    ):
        """Update ghost position using AI-driven movement."""

        if self.routes is None:
            self.routes = MazeRoutes(walls, () if gate is None else gate)
        if power_ticks is None:
            power_ticks = max(0, self.frightened_timer - 1)
        if self.mode != self.MODE_EATEN:
            if power_ticks:
                if self.mode != self.MODE_FRIGHTENED:
                    self.set_frightened(power_ticks)
                self.frightened_timer = power_ticks
                self.flash_timer += 1
            elif self.mode == self.MODE_FRIGHTENED:
                self.mode = self.MODE_CHASE
                self.frightened_timer = self.mode_timer = 0

        # Update mode timer for scatter/chase cycling (only in normal modes)
        if self.mode in (self.MODE_CHASE, self.MODE_SCATTER):
            self.mode_timer += 1
            if self.mode == self.MODE_SCATTER and self.mode_timer >= self.scatter_duration:
                self.mode = self.MODE_CHASE
                self.mode_timer = 0
            elif self.mode == self.MODE_CHASE and self.mode_timer >= self.chase_duration:
                self.mode = self.MODE_SCATTER
                self.mode_timer = 0

        # Update image based on mode
        if self.mode == self.MODE_FRIGHTENED:
            # Flash through colors using the soup can sprite
            if self.frightened_timer < 120:  # Last 2 seconds - flash faster
                color_index = (self.flash_timer // 5) % len(self.FLASH_COLORS)
            else:
                color_index = (self.flash_timer // 10) % len(self.FLASH_COLORS)
            self.image = self._tinted_images[self.FLASH_COLORS[color_index]]
        elif self.mode == self.MODE_EATEN:
            # Draw as small eyes only (simplified)
            self.image = self._eyes_image
        else:
            self.image = self.normal_image

        # Determine target based on mode and ghost type
        target = self._get_target(player_pos, player_dir, blinky_pos)

        # Get speed based on mode and elroy status
        if self.mode == self.MODE_FRIGHTENED:
            speed = self.FRIGHTENED_SPEED
        elif self.mode == self.MODE_EATEN:
            speed = self.EATEN_SPEED
        elif self.ghost_type == "blinky" and self.elroy_mode > 0:
            # Cruise Elroy - Blinky speeds up when few pellets remain
            if self.elroy_mode >= 2:
                speed = self.CRUISE_ELROY2_SPEED
            else:
                speed = self.CRUISE_ELROY_SPEED
        else:
            speed = self.NORMAL_SPEED

        if self.in_spawn:
            if self.spawn_delay:
                self.spawn_delay -= 1
            else:
                if not self._pen_path:
                    self._pen_path.extend((PEN_CENTER, PEN_EXIT))
                if self._move_to(self._pen_path[0], speed):
                    self._pen_path.popleft()
                    if not self._pen_path:
                        if self.mode == self.MODE_EATEN:
                            self.mode = self.MODE_CHASE
                            if power_ticks:
                                self.set_frightened(power_ticks)
                            self.spawn_delay = 45
                        else:
                            self.in_spawn = False
        else:
            if self._waypoint is None:
                node = (int(self.x), int(self.y))
                if self.mode == self.MODE_EATEN and node == PEN_EXIT:
                    self.in_spawn = True
                    self._pen_path.extend((PEN_CENTER, self.spawn_pos))
                    self._previous_node = None
                else:
                    returning = self.mode == self.MODE_EATEN
                    self._waypoint = self.routes.next_node(
                        node,
                        PEN_EXIT if returning else target,
                        None if returning else self._previous_node,
                    )
                    self._previous_node = node
            if self._waypoint is not None and self._move_to(self._waypoint, speed):
                self._waypoint = None
        self.rect.center = (round(self.x), round(self.y))

    def _move_to(self, point, speed):
        dx, dy = point[0] - self.x, point[1] - self.y
        if dx or dy:
            self.direction = (
                (int(math.copysign(1, dx)), 0) if dx else (0, int(math.copysign(1, dy)))
            )
            self.x += self.direction[0] * min(abs(dx), speed)
            self.y += self.direction[1] * min(abs(dy), speed)
        return (self.x, self.y) == point

    def _get_target(
        self,
        player_pos: Tuple[int, int],
        player_dir: Tuple[int, int],
        blinky_pos: Optional[Tuple[int, int]],
    ) -> Tuple[int, int]:
        """Get target position based on ghost type and mode."""
        if self.mode == self.MODE_EATEN:
            return self.spawn_pos

        if self.mode == self.MODE_FRIGHTENED:
            # Move away from player when frightened (smarter flee behavior)
            dx = self.x - player_pos[0]
            dy = self.y - player_pos[1]
            # Normalize and project away from player
            dist = max(1, math.sqrt(dx * dx + dy * dy))
            flee_x = self.x + (dx / dist) * 200
            flee_y = self.y + (dy / dist) * 200
            # Clamp to maze bounds
            flee_x = max(50, min(550, flee_x))
            flee_y = max(50, min(550, flee_y))
            return (int(flee_x), int(flee_y))

        if self.mode == self.MODE_SCATTER:
            # Each ghost has a corner target in scatter mode
            corners = {
                "blinky": (550, 50),
                "pinky": (50, 50),
                "inky": (550, 550),
                "clyde": (50, 550),
            }
            return corners.get(self.ghost_type, (300, 300))

        # Chase mode - each ghost has different targeting
        if self.ghost_type == "blinky":
            # Blinky: Direct chase - targets player position
            return player_pos

        elif self.ghost_type == "pinky":
            # Pinky: Ambush - targets 4 tiles ahead of player (more aggressive)
            ahead_x = player_pos[0] + player_dir[0] * 120
            ahead_y = player_pos[1] + player_dir[1] * 120
            return (int(ahead_x), int(ahead_y))

        elif self.ghost_type == "inky":
            # Inky: Unpredictable - uses Blinky's position
            if blinky_pos:
                # Target is reflection of Blinky through a point 2 tiles ahead of player
                pivot_x = player_pos[0] + player_dir[0] * 60
                pivot_y = player_pos[1] + player_dir[1] * 60
                target_x = 2 * pivot_x - blinky_pos[0]
                target_y = 2 * pivot_y - blinky_pos[1]
                return (int(target_x), int(target_y))
            return player_pos

        elif self.ghost_type == "clyde":
            # Clyde: Shy - chases when far, scatters when close (but less shy now)
            dist = math.sqrt((self.x - player_pos[0]) ** 2 + (self.y - player_pos[1]) ** 2)
            if dist > 100:  # Only retreats when very close
                return player_pos
            else:
                return (50, 550)  # Retreat to corner

        return player_pos


class Pellet(pygame.sprite.Sprite):
    """A collectible pellet/dot in the maze."""

    def __init__(
        self,
        x: int,
        y: int,
        image: Optional[pygame.Surface] = None,
        is_power_pellet: bool = False,
        power_pellet_image: Optional[pygame.Surface] = None,
    ):
        super().__init__()
        self.is_power_pellet = is_power_pellet
        self.power_pellet_base_image = power_pellet_image

        if is_power_pellet:
            # Power pellets use soupbowl image and pulse
            self.pulse_timer = 0
            if power_pellet_image:
                self.base_image = power_pellet_image
                self.image = power_pellet_image.copy()
            else:
                # Fallback to yellow circle
                self.base_size = 16
                self.image = pygame.Surface([self.base_size, self.base_size], pygame.SRCALPHA)
                pygame.draw.circle(
                    self.image,
                    YELLOW,
                    (self.base_size // 2, self.base_size // 2),
                    self.base_size // 2,
                )
                self.base_image = None
        elif image:
            self.image = image
        else:
            self.image = pygame.Surface([4, 4])
            self.image.fill(WHITE)
            pygame.draw.ellipse(self.image, YELLOW, [0, 0, 4, 4])

        self.rect = self.image.get_rect(center=(x, y))
        self._pulse_frames = {}
        if is_power_pellet:
            source = self.base_image or self.image
            for size in range(12, 30):
                self._pulse_frames[size] = pygame.transform.scale(source, (size, size))

    def update(self):
        """Update power pellet animation (pulsing scale)."""
        if self.is_power_pellet:
            self.pulse_timer += 1
            # Pulse scale between 0.8 and 1.2
            scale = 1.0 + 0.2 * math.sin(self.pulse_timer * 0.1)
            old_center = self.rect.center

            base_size = self.base_image.get_width() if self.base_image else 16
            self.image = self._pulse_frames[max(12, min(29, int(base_size * scale)))]

            self.rect = self.image.get_rect(center=old_center)


class PacmanGame(BaseGame):
    """
    Tunnel Treats game using AnimatedFerret for the player character.

    Features:
    - AnimatedFerret with movement animation while navigating
    - Directional sprite flipping based on horizontal movement
    - Death animation on ghost collision with 1-second pause
    - AI-driven ghost behavior with different personalities
    - Power pellets that allow eating ghosts
    - Original garden critters for ghosts, soupbowl for pellets
    """

    # Movement speed (reduced from 30 to make game more controllable)
    PLAYER_SPEED = 2.5

    # Maze wall data: [x, y, width, height]
    WALL_DATA = [
        [0, 0, 6, 600],
        [0, 0, 600, 6],
        [0, 600, 606, 6],
        [600, 0, 6, 606],
        [300, 0, 6, 66],
        [60, 60, 186, 6],
        [360, 60, 186, 6],
        [60, 120, 66, 6],
        [60, 120, 6, 126],
        [180, 120, 246, 6],
        [300, 120, 6, 66],
        [480, 120, 66, 6],
        [540, 120, 6, 126],
        [120, 180, 126, 6],
        [120, 180, 6, 126],
        [360, 180, 126, 6],
        [480, 180, 6, 126],
        [180, 240, 6, 126],
        [180, 360, 246, 6],
        [420, 240, 6, 126],
        [240, 240, 42, 6],
        [324, 240, 42, 6],
        [240, 240, 6, 66],
        [240, 300, 126, 6],
        [360, 240, 6, 66],
        [0, 300, 66, 6],
        [540, 300, 66, 6],
        [60, 360, 66, 6],
        [60, 360, 6, 186],
        [480, 360, 66, 6],
        [540, 360, 6, 186],
        [120, 420, 366, 6],
        [120, 420, 6, 66],
        [480, 420, 6, 66],
        [180, 480, 246, 6],
        [300, 480, 6, 66],
        [120, 540, 126, 6],
        [360, 540, 126, 6],
    ]

    # Power pellet positions (four corners of the maze)
    POWER_PELLET_POSITIONS = [
        (36, 66),  # Top-left
        (564, 66),  # Top-right
        (36, 534),  # Bottom-left
        (564, 534),  # Bottom-right
    ]

    # Player starting position (center-bottom of maze)
    PLAYER_START_X = 303
    PLAYER_START_Y = 454

    # Ghost spawn positions and types
    GHOST_DATA = [
        ("blinky", 303, 273),  # Direct chaser
        ("pinky", 303, 273),  # Ambusher
        ("inky", 273, 273),  # Flanker
        ("clyde", 333, 273),  # Shy pursuer
    ]

    # Maze colors - softer lavender cave theme
    MAZE_WALL_COLOR = MAZE_WALL_CUTE

    # Power mode duration (frames at 60 FPS)
    POWER_MODE_DURATION = 480  # 8 seconds

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            "ghost_speed": 1.6,  # Slower ghosts
            "ghost_frightened_speed": 0.9,
            "power_mode_duration": 600,  # 10 seconds power mode
        },
        Difficulty.NORMAL: {
            "ghost_speed": 2.3,  # Normal ghost speed
            "ghost_frightened_speed": 1.2,
            "power_mode_duration": 480,  # 8 seconds power mode
        },
        Difficulty.HARD: {
            "ghost_speed": 3.0,  # Faster ghosts
            "ghost_frightened_speed": 1.5,
            "power_mode_duration": 300,  # 5 seconds power mode
        },
    }

    def __init__(self, screen: pygame.Surface, input_manager, difficulty=None):
        """Initialize the Pac-Man game."""
        # Store base directory for asset loading
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.asset_loader = AssetLoader(self.base_dir)

        # Game state
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.total_pellets = 0
        self.state = "playing"  # 'playing', 'dying', 'resetting'
        self.death_timer = 0
        self.death_duration = 60  # 1 second at 60 FPS

        # Power mode tracking
        self.power_mode = False
        self.power_timer = 0
        self.ghost_eat_combo = 0  # Tracks consecutive ghost eats for bonus

        # Sprite groups
        self.walls = pygame.sprite.Group()
        self.gate = pygame.sprite.Group()
        self.pellets = pygame.sprite.Group()
        self.power_pellets = pygame.sprite.Group()
        self.ghosts: List[Ghost] = []

        # Player (AnimatedFerret)
        self.player: Optional[AnimatedFerret] = None
        self.player_dir = (1, 0)  # Current direction
        self.queued_dir = None  # Queued direction for next valid turn

        # Player position as float for smooth movement
        self.player_x = float(self.PLAYER_START_X)
        self.player_y = float(self.PLAYER_START_Y)

        # Assets
        self.ghost_images = {}
        self.pellet_img: Optional[pygame.Surface] = None

        # Font for UI
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 48)

        # Call parent init (which calls setup)
        super().__init__(screen, input_manager, difficulty)

    def setup(self):
        """Initialize or reset the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.level = 1
        self._deaths = 0
        self._deaths_this_level = 0
        self.ghost_speed = preset["ghost_speed"]
        self.ghost_frightened_speed = preset["ghost_frightened_speed"]
        self.power_mode_duration = preset["power_mode_duration"]

        # Load assets
        self._load_assets()

        # Create maze
        self._create_maze()

        # Create player
        self._create_player()

        # Create ghosts
        self._create_ghosts()

        # Create pellets
        self._create_pellets()

        # Store total pellet count (including power pellets)
        self.total_pellets = len(self.pellets) + len(self.power_pellets)

        # Reset game state
        self.score = 0
        self.lives = 3
        self.state = "playing"
        self.death_timer = 0
        self.power_mode = False
        self.power_timer = 0
        self.ghost_eat_combo = 0
        self.player_dir = (1, 0)
        self.queued_dir = None
        self.paused = False
        self.score_manager = get_score_manager()
        self.high_score = self.score_manager.get_high_score("pacman", self.difficulty)
        self.new_high_score = False
        self._build_render_cache()

    def _load_assets(self):
        """Load game assets (ghost and pellet sprites)."""
        for name, color in (
            ("blinky", (228, 117, 98)),
            ("pinky", (223, 145, 201)),
            ("inky", (103, 196, 192)),
            ("clyde", (238, 177, 82)),
        ):
            image = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(image, color, (2, 6, 26, 22))
            for x in (9, 21):
                pygame.draw.circle(image, color, (x, 6), 5)
                pygame.draw.circle(image, WHITE, (x, 15), 4)
                pygame.draw.circle(image, (45, 35, 70), (x, 15), 2)
            ink = (76, 49, 78)
            if name == "blinky":
                pygame.draw.line(image, ink, (9, 9), (14, 11), 2)
                pygame.draw.line(image, ink, (21, 9), (16, 11), 2)
            elif name == "pinky":
                pygame.draw.polygon(
                    image, ink, [(10, 2), (16, 5), (21, 2), (21, 9), (16, 6), (10, 9)]
                )
            elif name == "inky":
                pygame.draw.circle(image, ink, (12, 23), 2)
                pygame.draw.circle(image, ink, (18, 23), 2)
            else:
                pygame.draw.lines(image, ink, False, [(10, 22), (15, 25), (20, 22)], 2)
            self.ghost_images[name] = image

        # Load pellet sprite (soupbowl, sized for visibility)
        self.pellet_img = self.asset_loader.load_image("soupbowl.png", (12, 12))

        # Load power pellet sprite (larger soupbowl)
        self.power_pellet_img = self.asset_loader.load_image("soupbowl.png", (24, 24))

    def _create_maze(self):
        """Create the maze walls and ghost gate."""
        self.walls.empty()
        self.gate.empty()

        # Create walls
        for wall_data in self.WALL_DATA:
            wall = Wall(
                wall_data[0], wall_data[1], wall_data[2], wall_data[3], self.MAZE_WALL_COLOR
            )
            self.walls.add(wall)

        # Create ghost gate (thin white bar)
        gate = Wall(282, 242, 42, 2, WHITE)
        self.gate.add(gate)
        self.routes = MazeRoutes(self.walls, self.gate)

    def _create_player(self):
        """Create the player character using AnimatedFerret."""
        player_size = 28  # Slightly smaller for tighter movement
        self.player = AnimatedFerret(
            x=self.PLAYER_START_X,
            y=self.PLAYER_START_Y,
            scale=1,
            speed=0,  # We handle movement manually for wall collision
            frame_delay=4,  # Faster animation for movement
        )
        self.player.set_sprite_size(player_size)
        self.player_x = float(self.PLAYER_START_X)
        self.player_y = float(self.PLAYER_START_Y)
        self.player_dir = (0, 0)  # Start stationary
        self.queued_dir = None

    def _create_ghosts(self):
        """Create the ghost enemies with AI behavior and staggered release."""
        self.ghosts = []

        # Spawn delays in frames (60fps): Blinky starts immediately, others follow
        spawn_delays = {
            "blinky": 0,  # Starts immediately - always chasing
            "pinky": 90,  # 1.5 seconds
            "inky": 180,  # 3 seconds
            "clyde": 270,  # 4.5 seconds
        }

        for ghost_type, x, y in self.GHOST_DATA:
            ghost = Ghost(
                x=x,
                y=y,
                normal_image=self.ghost_images[ghost_type],
                frightened_image=self.ghost_images[ghost_type],
                ghost_type=ghost_type,
                spawn_pos=(x, y),
            )
            # Apply difficulty-based speeds (override class defaults)
            ghost.NORMAL_SPEED = self.ghost_speed
            ghost.FRIGHTENED_SPEED = self.ghost_frightened_speed
            # Scale cruise elroy speeds proportionally
            speed_ratio = self.ghost_speed / 2.3  # ratio vs normal default
            ghost.CRUISE_ELROY_SPEED = 2.7 * speed_ratio
            ghost.CRUISE_ELROY2_SPEED = 3.0 * speed_ratio
            # Set spawn delay based on ghost type
            ghost.routes = self.routes
            ghost.spawn_delay = spawn_delays[ghost_type]
            # Blinky starts outside the pen, others inside
            if ghost_type == "blinky":
                ghost.in_spawn = False
                ghost.x, ghost.y = PEN_EXIT
                ghost.rect.center = PEN_EXIT
                ghost.direction = (-1, 0)  # Start moving left
            self.ghosts.append(ghost)

    def _create_pellets(self):
        """Create pellets and power pellets throughout the maze."""
        self.pellets.empty()
        self.power_pellets.empty()

        # Create a temporary player rect for collision check
        player_rect = pygame.Rect(self.PLAYER_START_X - 15, self.PLAYER_START_Y - 15, 30, 30)

        # Grid-based pellet placement
        for row in range(19):
            for col in range(19):
                # Skip ghost spawn area
                if (row == 7 or row == 8) and col in (8, 9, 10):
                    continue

                x = (30 * col + 6) + 26
                y = (30 * row + 6) + 26

                # Skip positions too close to power pellet locations
                skip_for_power = False
                for px, py in self.POWER_PELLET_POSITIONS:
                    if abs(x - px) < 25 and abs(y - py) < 25:
                        skip_for_power = True
                        break

                if skip_for_power:
                    continue

                pellet = Pellet(x, y, self.pellet_img, is_power_pellet=False)

                # Don't place pellets on walls or at player start
                if not pygame.sprite.spritecollide(pellet, self.walls, False):
                    if not pellet.rect.colliderect(player_rect):
                        self.pellets.add(pellet)

        # Add power pellets at the four corners (exactly one per corner)
        for px, py in self.POWER_PELLET_POSITIONS:
            pellet = Pellet(px, py, is_power_pellet=True, power_pellet_image=self.power_pellet_img)
            if not pygame.sprite.spritecollide(pellet, self.walls, False):
                self.power_pellets.add(pellet)

    def _reset_positions(self):
        """Reset player and ghost positions after death."""
        # Reset player position
        self.player_x = float(self.PLAYER_START_X)
        self.player_y = float(self.PLAYER_START_Y)
        self.player.x = self.player_x
        self.player.y = self.player_y
        self.player.set_state("idle")
        self.player_dir = (0, 0)
        self.queued_dir = None

        self.death_timer = 0

        # Reset ghosts
        self._create_ghosts()

        # End power mode
        self.power_mode = False
        self.power_timer = 0
        self.ghost_eat_combo = 0

        self.state = "playing"

    def _reset_level(self):
        """Populate a new board while preserving the run's score and lives."""
        self._reset_positions()
        self._create_pellets()
        self.total_pellets = len(self.pellets) + len(self.power_pellets)

    def _next_level(self):
        self.level += 1
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.ghost_speed = preset["ghost_speed"] * min(1.6, 1 + 0.08 * (self.level - 1))
        self.power_mode_duration = max(120, preset["power_mode_duration"] - 30 * (self.level - 1))
        self._deaths_this_level = 0
        self._reset_level()

    def handle_input(self) -> bool:
        """Process player input. Returns True to exit to menu."""
        # Update input manager for edge detection
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        if self.state == "game_over":
            if self.input_manager.confirm_pressed():
                self.restart_session()
                self.setup()
            return False

        # Check for pause toggle
        if self.input_manager.pause_pressed() and self.state == "playing":
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Don't process movement input during death animation
        if self.state != "playing":
            return False

        # Get D-pad direction
        dp = self.input_manager.get_dpad()

        new_dir = None
        if dp[0] == -1:
            new_dir = (-1, 0)
        elif dp[0] == 1:
            new_dir = (1, 0)
        elif dp[1] == -1:
            new_dir = (0, -1)
        elif dp[1] == 1:
            new_dir = (0, 1)

        if new_dir:
            # Queue the direction change
            self.queued_dir = new_dir

            # Try to apply immediately if valid
            if self._can_move(new_dir):
                self.player_dir = new_dir
                self.queued_dir = None

        # Update facing direction
        if self.player_dir[0] > 0:
            self.player.facing_right = True
        elif self.player_dir[0] < 0:
            self.player.facing_right = False

        return False

    def _can_move(self, direction: Tuple[int, int]) -> bool:
        """Check if player can move in the given direction."""
        test_x = self.player_x + direction[0] * self.PLAYER_SPEED * 3
        test_y = self.player_y + direction[1] * self.PLAYER_SPEED * 3

        test_rect = pygame.Rect(int(test_x) - 12, int(test_y) - 12, 24, 24)

        for wall in self.walls:
            if test_rect.colliderect(wall.rect):
                return False
        for gate in self.gate:
            if test_rect.colliderect(gate.rect):
                return False
        return True

    def update(self, dt: float):
        """Update game logic."""
        # Don't update when paused
        if self.paused:
            return

        if self.state == "level_complete":
            self.level_timer -= 1
            if self.level_timer <= 0:
                self._next_level()
            return

        if self.state == "dying":
            # Update death animation
            self.death_timer += 1

            # Advance death animation
            dx = 1 if self.player.facing_right else -1
            self.player.update(dx, 0)  # Keep updating animation

            if self.death_timer >= self.death_duration:
                self.lives -= 1
                self._deaths_this_level = getattr(self, "_deaths_this_level", 0) + 1
                if self.lives <= 0:
                    # Game over - check and save high score
                    if self.score_manager.set_high_score("pacman", self.score, self.difficulty):
                        self.new_high_score = True
                        self.high_score = self.score
                    # Check achievements
                    if self.score >= 1000:
                        self.achievements.unlock("pacman_1000")
                    # Track statistics
                    self._finalize_game_statistics()
                    self.state = "game_over"
                else:
                    self._reset_positions()
            return

        if self.state != "playing":
            return

        # Update power mode timer
        if self.power_mode:
            self.power_timer -= 1
            if self.power_timer <= 0:
                self.power_mode = False
                self.ghost_eat_combo = 0

        # Try to apply queued direction
        if self.queued_dir and self._can_move(self.queued_dir):
            self.player_dir = self.queued_dir
            self.queued_dir = None

        # Move player
        if self.player_dir != (0, 0):
            new_x = self.player_x + self.player_dir[0] * self.PLAYER_SPEED
            new_y = self.player_y + self.player_dir[1] * self.PLAYER_SPEED

            # Check wall collision
            test_rect = pygame.Rect(int(new_x) - 12, int(new_y) - 12, 24, 24)
            can_move = True
            for wall in self.walls:
                if test_rect.colliderect(wall.rect):
                    can_move = False
                    break
            for gate in self.gate:
                if test_rect.colliderect(gate.rect):
                    can_move = False
                    break

            if can_move:
                self.player_x = new_x
                self.player_y = new_y
            else:
                # Stop movement on wall hit
                self.player_dir = (0, 0)

            self.player.x = self.player_x
            self.player.y = self.player_y

        # Update player animation
        if self.player_dir != (0, 0):
            if self.player.state != "movement":
                self.player.set_state("movement")
        else:
            if self.player.state != "idle":
                self.player.set_state("idle")
        self.player._advance_animation()

        # Update ghosts with AI
        blinky_pos = None
        pellets_remaining = len(self.pellets) + len(self.power_pellets)

        for ghost in self.ghosts:
            if ghost.ghost_type == "blinky":
                blinky_pos = (ghost.x, ghost.y)
                # Cruise Elroy mode - Blinky gets faster as pellets decrease
                if pellets_remaining <= 10:
                    ghost.elroy_mode = 2  # Very fast
                elif pellets_remaining <= 30:
                    ghost.elroy_mode = 1  # Fast
                else:
                    ghost.elroy_mode = 0
                break

        for ghost in self.ghosts:
            ghost.update(
                self.walls,
                (self.player_x, self.player_y),
                self.player_dir,
                blinky_pos,
                power_ticks=self.power_timer,
            )

        # Update power pellet animation
        for pellet in self.power_pellets:
            pellet.update()

        # Check pellet collection (larger hitbox for easier collection)
        player_rect = pygame.Rect(int(self.player_x) - 16, int(self.player_y) - 16, 32, 32)

        for pellet in list(self.pellets):
            if player_rect.colliderect(pellet.rect):
                self.pellets.remove(pellet)
                self.score += 10
                self.audio.play_sound(AudioManager.SOUND_PELLET)

        # Check power pellet collection
        for pellet in list(self.power_pellets):
            if player_rect.colliderect(pellet.rect):
                self.power_pellets.remove(pellet)
                self.score += 50
                self.audio.play_sound(AudioManager.SOUND_POWERUP)
                self._activate_power_mode()

        # Check ghost collision
        collision_rect = pygame.Rect(0, 0, 20, 20)
        collision_rect.center = (round(self.player_x), round(self.player_y))
        for ghost in self.ghosts:
            if not ghost.in_spawn and collision_rect.colliderect(ghost.rect.inflate(-6, -6)):
                if ghost.mode == Ghost.MODE_FRIGHTENED:
                    # Eat the ghost!
                    self.ghost_eat_combo += 1
                    ghost_score = 200 * (2 ** (self.ghost_eat_combo - 1))
                    ghost_score = min(ghost_score, 1600)  # Cap at 1600
                    self.score += ghost_score
                    ghost.get_eaten()
                    self.audio.play_sound(AudioManager.SOUND_COLLECT)
                    # Check for 4 ghosts eaten achievement
                    if self.ghost_eat_combo >= 4:
                        self.achievements.unlock("pacman_ghost")
                    # Track ghost eaten stat
                    self.stats.increment("pacman", "ghosts_eaten")
                elif ghost.mode != Ghost.MODE_EATEN:
                    # Player dies
                    self._start_death()
                    return

        if self.score >= 1000:
            self.achievements.unlock("pacman_1000")

        # Check win condition (all pellets eaten)
        if len(self.pellets) == 0 and len(self.power_pellets) == 0:
            self.high_score = max(self.high_score, self.score)
            self.audio.play_sound(AudioManager.SOUND_VICTORY)
            # Check achievements
            self.achievements.unlock("pacman_first")
            if getattr(self, "_deaths_this_level", 0) == 0:
                self.achievements.unlock("pacman_no_death")
            # Track statistics
            self.stats.increment("pacman", "levels_cleared")
            self.stats.increment("global", "games_completed")
            self.new_high_score = (
                self.score_manager.set_high_score("pacman", self.score, self.difficulty)
                or self.new_high_score
            )
            self.state = "level_complete"
            self.level_timer = 90

    def _activate_power_mode(self):
        """Activate power mode - ghosts become vulnerable."""
        self.power_mode = True
        self.power_timer = self.power_mode_duration  # Use difficulty-based duration
        self.ghost_eat_combo = 0

        for ghost in self.ghosts:
            ghost.set_frightened(self.power_mode_duration)

    def _start_death(self):
        """Start the death animation sequence."""
        if self.state != "playing":
            return
        self._deaths += 1
        self.state = "dying"
        self.death_timer = 0
        self.player.set_state("death")
        self.player_dir = (0, 0)
        self.audio.play_sound(AudioManager.SOUND_DEATH)

    def _record_game_statistics(self):
        self.stats.increment("pacman", "deaths", self._deaths)
        self.stats.add("pacman", "total_score", self.score)

    def _build_render_cache(self):
        """Bake wall glows and cave stars once; share collectible effects."""
        self._cave_background = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._cave_background.fill(CAVE_BG_DARK)
        rng = random.Random(42)
        for _ in range(30):
            pygame.draw.circle(
                self._cave_background,
                (100, 95, 110),
                (rng.randrange(10, WINDOW_WIDTH - 10), rng.randrange(10, WINDOW_HEIGHT - 10)),
                rng.randrange(1, 4),
            )
        glow_layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for wall in self.walls:
            pygame.draw.rect(
                glow_layer, (*CAVE_WALL_GLOW, 40), wall.rect.inflate(4, 4), border_radius=2
            )
        self._cave_background.blit(glow_layer, (0, 0))
        self.walls.draw(self._cave_background)
        self.gate.draw(self._cave_background)
        self._pellet_glow = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(self._pellet_glow, (*PELLET_GLOW, 60), (6, 6), 6)
        self._power_glow = pygame.Surface((56, 56), pygame.SRCALPHA)
        pygame.draw.circle(self._power_glow, (*POWER_PELLET_GLOW, 110), (28, 28), 27)
        self._ghost_glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(self._ghost_glow, (100, 100, 255, 60), (20, 20), 18)

    def render(self):
        """Draw cached artwork and current actors without per-pellet allocations."""
        self.screen.blit(self._cave_background, (0, 0))
        for pellet in self.pellets:
            self.screen.blit(self._pellet_glow, (pellet.rect.centerx - 6, pellet.rect.centery - 6))
        self.pellets.draw(self.screen)
        for pellet in self.power_pellets:
            self.screen.blit(self._power_glow, (pellet.rect.centerx - 28, pellet.rect.centery - 28))
        self.power_pellets.draw(self.screen)
        self.player.draw(self.screen)
        for ghost in self.ghosts:
            if ghost.mode == Ghost.MODE_FRIGHTENED:
                self.screen.blit(
                    self._ghost_glow, (ghost.rect.centerx - 20, ghost.rect.centery - 20)
                )
            self.screen.blit(ghost.image, ghost.rect)

        labels = [
            "Tunnel Treats",
            f"Level: {self.level}",
            f"Score: {self.score}",
            f"High: {self.high_score}",
            f"Lives: {self.lives}",
            f"Treats: {len(self.pellets) + len(self.power_pellets)}",
            "P / Start: pause",
            "B / Esc: menu",
        ]
        if self.power_mode:
            labels.append(f"POWER: {self.power_timer / 60:.1f}s")
        for row, label in enumerate(labels):
            self.screen.blit(self.font.render(label, True, WHITE), (615, 25 + row * 32))
        if self.paused:
            self._draw_pause_overlay()
        elif self.state == "game_over":
            self._draw_game_over_overlay(score=self.score)
        elif self.state in ("dying", "level_complete"):
            label = "CAUGHT!" if self.state == "dying" else f"LEVEL {self.level} COMPLETE!"
            text = self.large_font.render(label, True, (255, 200, 220))
            self.screen.blit(text, text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))
