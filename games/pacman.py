"""
Pac-Man game implementation for the Weasel Entertainment System.

Uses AnimatedFerret for the player with directional animations and death sequence.
Ghosts are represented by soupcan sprites (ferret vs soup cans theme).
Power pellets (large soupbowls) allow the player to eat ghosts temporarily.
"""

import os
import sys
import math
import random
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
    BLACK,
    WHITE,
    RED,
    YELLOW,
    CYAN,
    BLUE,
    WEASEL_BROWN,
    WEASEL_TAN,
    WEASEL_WHITE,
    PASTEL_SKY,
)

# Enhanced cute color palette for underground cave theme
CAVE_BG_DARK = (25, 20, 40)           # Deep purple-black background
CAVE_BG_MID = (40, 30, 60)            # Slightly lighter cave
CAVE_WALL_GLOW = (180, 140, 200)      # Soft purple wall glow
MAZE_WALL_CUTE = (160, 120, 180)      # Softer lavender walls
PELLET_GLOW = (255, 255, 200)         # Warm yellow glow
POWER_PELLET_GLOW = (255, 200, 255)   # Pink power pellet glow


class Wall(pygame.sprite.Sprite):
    """A wall segment in the maze."""

    def __init__(self, x: int, y: int, w: int, h: int, color: tuple):
        super().__init__()
        self.image = pygame.Surface([w, h])
        self.image.fill(color)
        self.rect = self.image.get_rect(top=y, left=x)


class Ghost(pygame.sprite.Sprite):
    """A ghost enemy with AI-driven chase behavior."""

    # Ghost behavior modes
    MODE_CHASE = 'chase'
    MODE_SCATTER = 'scatter'
    MODE_FRIGHTENED = 'frightened'
    MODE_EATEN = 'eaten'

    # Speed settings
    NORMAL_SPEED = 2.3      # Normal movement speed (closer to player speed)
    CRUISE_ELROY_SPEED = 2.7  # Blinky's speed when few pellets remain
    CRUISE_ELROY2_SPEED = 3.0  # Even faster when very few pellets remain
    FRIGHTENED_SPEED = 1.2  # Slower when vulnerable
    EATEN_SPEED = 4.0       # Fast when returning to spawn

    # Flash colors for frightened mode (soup can colors cycling)
    FLASH_COLORS = [
        (255, 100, 100),   # Light red
        (100, 100, 255),   # Light blue
        (255, 255, 100),   # Yellow
        (100, 255, 100),   # Green
    ]

    def __init__(self, x: int, y: int, normal_image: pygame.Surface,
                 frightened_image: pygame.Surface, ghost_type: str,
                 spawn_pos: Tuple[int, int]):
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

        # Decision cooldown to prevent jittery movement
        self.decision_cooldown = 0
        self.last_decision_pos = (x, y)

        # Scatter/chase cycle timer (for better AI pacing)
        self.mode_timer = 0
        self.scatter_duration = 180   # 3 seconds scatter (shorter = more aggressive)
        self.chase_duration = 1200    # 20 seconds chase

        # Spawn delay - ghosts wait in pen before emerging
        self.spawn_delay = 0          # Frames to wait before leaving spawn
        self.in_spawn = True          # Whether ghost is still in spawn pen

        # Cruise Elroy mode for Blinky (speeds up when few pellets left)
        self.elroy_mode = 0           # 0=normal, 1=elroy1, 2=elroy2

    def _create_tinted_image(self, color: Tuple[int, int, int]) -> pygame.Surface:
        """Create a color-tinted version of the soup can for flashing effect."""
        tinted = self.normal_image.copy()
        # Create a color overlay
        overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        overlay.fill((*color, 128))  # Semi-transparent tint
        tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # Add the color as an additive blend for brightness
        overlay.fill((*color, 80))
        tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return tinted

    def set_frightened(self, duration: int):
        """Enter frightened mode for the given number of frames."""
        if self.mode != self.MODE_EATEN:
            self.mode = self.MODE_FRIGHTENED
            self.frightened_timer = duration
            self.flash_timer = 0
            # Reverse direction when frightened
            self.direction = (-self.direction[0], -self.direction[1])

    def get_eaten(self):
        """Ghost was eaten by player - return to spawn."""
        self.mode = self.MODE_EATEN
        self.frightened_timer = 0

    def update(self, walls: pygame.sprite.Group, player_pos: Tuple[int, int],
               player_dir: Tuple[int, int], blinky_pos: Optional[Tuple[int, int]] = None,
               gate: Optional[pygame.sprite.Group] = None):
        """Update ghost position using AI-driven movement."""

        # Handle spawn delay - ghost waits in pen before emerging
        if self.in_spawn:
            if self.spawn_delay > 0:
                self.spawn_delay -= 1
                # Bounce up and down slightly while waiting
                bounce = math.sin(self.spawn_delay * 0.15) * 2
                self.y = self.spawn_pos[1] + bounce
                self.rect.center = (int(self.x), int(self.y))
                return
            else:
                # Time to leave the spawn - move up through gate
                self.in_spawn = False
                # Center horizontally on gate (gate is at x=303) and move above it
                self.x = 303
                self.y = self.spawn_pos[1] - 60  # Move above the gate
                self.direction = (-1, 0)  # Start moving left to avoid getting stuck
                self.mode = self.MODE_CHASE

        # Update mode timer for scatter/chase cycling (only in normal modes)
        if self.mode in (self.MODE_CHASE, self.MODE_SCATTER):
            self.mode_timer += 1
            if self.mode == self.MODE_SCATTER and self.mode_timer >= self.scatter_duration:
                self.mode = self.MODE_CHASE
                self.mode_timer = 0
            elif self.mode == self.MODE_CHASE and self.mode_timer >= self.chase_duration:
                self.mode = self.MODE_SCATTER
                self.mode_timer = 0

        # Update frightened timer
        if self.mode == self.MODE_FRIGHTENED:
            self.frightened_timer -= 1
            self.flash_timer += 1
            if self.frightened_timer <= 0:
                self.mode = self.MODE_CHASE
                self.mode_timer = 0
                self.consecutive_ghost_bonus = 0

        # Update image based on mode
        if self.mode == self.MODE_FRIGHTENED:
            # Flash through colors using the soup can sprite
            if self.frightened_timer < 120:  # Last 2 seconds - flash faster
                color_index = (self.flash_timer // 5) % len(self.FLASH_COLORS)
            else:
                color_index = (self.flash_timer // 10) % len(self.FLASH_COLORS)
            self.image = self._create_tinted_image(self.FLASH_COLORS[color_index])
        elif self.mode == self.MODE_EATEN:
            # Draw as small eyes only (simplified)
            self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(self.image, WHITE, (10, 12), 5)
            pygame.draw.circle(self.image, WHITE, (20, 12), 5)
            pygame.draw.circle(self.image, BLUE, (10, 12), 2)
            pygame.draw.circle(self.image, BLUE, (20, 12), 2)
        else:
            self.image = self.normal_image

        # Determine target based on mode and ghost type
        target = self._get_target(player_pos, player_dir, blinky_pos)

        # Get speed based on mode and elroy status
        if self.mode == self.MODE_FRIGHTENED:
            speed = self.FRIGHTENED_SPEED
        elif self.mode == self.MODE_EATEN:
            speed = self.EATEN_SPEED
        elif self.ghost_type == 'blinky' and self.elroy_mode > 0:
            # Cruise Elroy - Blinky speeds up when few pellets remain
            if self.elroy_mode >= 2:
                speed = self.CRUISE_ELROY2_SPEED
            else:
                speed = self.CRUISE_ELROY_SPEED
        else:
            speed = self.NORMAL_SPEED

        # AI movement - choose best direction at intersections
        self._move_towards_target(target, walls, speed)

        # Check if eaten ghost reached spawn
        if self.mode == self.MODE_EATEN:
            spawn_dist = math.sqrt((self.x - self.spawn_pos[0])**2 +
                                   (self.y - self.spawn_pos[1])**2)
            if spawn_dist < 15:
                self.mode = self.MODE_CHASE
                self.mode_timer = 0
                self.x, self.y = float(self.spawn_pos[0]), float(self.spawn_pos[1])

        # Update rect position
        self.rect.center = (int(self.x), int(self.y))

    def _get_target(self, player_pos: Tuple[int, int], player_dir: Tuple[int, int],
                    blinky_pos: Optional[Tuple[int, int]]) -> Tuple[int, int]:
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
                'blinky': (550, 50),
                'pinky': (50, 50),
                'inky': (550, 550),
                'clyde': (50, 550),
            }
            return corners.get(self.ghost_type, (300, 300))

        # Chase mode - each ghost has different targeting
        if self.ghost_type == 'blinky':
            # Blinky: Direct chase - targets player position
            return player_pos

        elif self.ghost_type == 'pinky':
            # Pinky: Ambush - targets 4 tiles ahead of player (more aggressive)
            ahead_x = player_pos[0] + player_dir[0] * 120
            ahead_y = player_pos[1] + player_dir[1] * 120
            return (int(ahead_x), int(ahead_y))

        elif self.ghost_type == 'inky':
            # Inky: Unpredictable - uses Blinky's position
            if blinky_pos:
                # Target is reflection of Blinky through a point 2 tiles ahead of player
                pivot_x = player_pos[0] + player_dir[0] * 60
                pivot_y = player_pos[1] + player_dir[1] * 60
                target_x = 2 * pivot_x - blinky_pos[0]
                target_y = 2 * pivot_y - blinky_pos[1]
                return (int(target_x), int(target_y))
            return player_pos

        elif self.ghost_type == 'clyde':
            # Clyde: Shy - chases when far, scatters when close (but less shy now)
            dist = math.sqrt((self.x - player_pos[0])**2 +
                             (self.y - player_pos[1])**2)
            if dist > 100:  # Only retreats when very close
                return player_pos
            else:
                return (50, 550)  # Retreat to corner

        return player_pos

    def _move_towards_target(self, target: Tuple[int, int],
                              walls: pygame.sprite.Group, speed: float):
        """Move ghost towards target, avoiding walls with smarter pathfinding."""
        # Decrease decision cooldown
        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1

        # Check if we've moved enough to make a new decision
        dist_from_last = math.sqrt((self.x - self.last_decision_pos[0])**2 +
                                   (self.y - self.last_decision_pos[1])**2)

        # Only make new direction decisions at intersections (every ~25 pixels)
        should_decide = dist_from_last >= 25 or self.decision_cooldown <= 0

        if should_decide:
            # Get possible directions
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # up, down, left, right

            # Don't reverse direction (ghosts can't turn around) unless stuck
            if self.direction != (0, 0):
                reverse = (-self.direction[0], -self.direction[1])
                directions_no_reverse = [d for d in directions if d != reverse]
            else:
                directions_no_reverse = directions

            # Find valid directions (no wall collision)
            valid_dirs = []
            for d in directions_no_reverse:
                if self._can_move_direction(d, walls, speed):
                    valid_dirs.append(d)

            # If no valid directions without reversing, allow reverse
            if not valid_dirs:
                for d in directions:
                    if self._can_move_direction(d, walls, speed):
                        valid_dirs.append(d)

            if not valid_dirs:
                # Completely stuck - shouldn't happen but handle it
                valid_dirs = [(1, 0)]

            # Choose direction closest to target (greedy pathfinding)
            best_dir = valid_dirs[0]
            best_dist = float('inf')
            for d in valid_dirs:
                # Project position in this direction
                new_x = self.x + d[0] * 30
                new_y = self.y + d[1] * 30
                dist = math.sqrt((new_x - target[0])**2 + (new_y - target[1])**2)

                # Add slight randomness for frightened mode
                if self.mode == self.MODE_FRIGHTENED:
                    dist += random.uniform(-20, 20)

                if dist < best_dist:
                    best_dist = dist
                    best_dir = d

            # Update direction if changed
            if best_dir != self.direction:
                self.direction = best_dir
                self.last_decision_pos = (self.x, self.y)
                self.decision_cooldown = 15  # Don't change direction too quickly

        # Move in current direction
        new_x = self.x + self.direction[0] * speed
        new_y = self.y + self.direction[1] * speed

        # Check wall collision for actual movement (with smaller hitbox)
        test_rect = pygame.Rect(0, 0, 20, 20)
        test_rect.center = (int(new_x), int(self.y))
        can_move_x = True
        for wall in walls:
            if test_rect.colliderect(wall.rect):
                can_move_x = False
                break

        test_rect.center = (int(self.x), int(new_y))
        can_move_y = True
        for wall in walls:
            if test_rect.colliderect(wall.rect):
                can_move_y = False
                break

        if can_move_x:
            self.x = new_x
        if can_move_y:
            self.y = new_y

        # If stuck, force a direction change
        if not can_move_x and not can_move_y:
            self.decision_cooldown = 0

    def _can_move_direction(self, direction: Tuple[int, int],
                            walls: pygame.sprite.Group, speed: float) -> bool:
        """Check if ghost can move in the given direction."""
        test_rect = pygame.Rect(0, 0, 22, 22)
        test_rect.center = (int(self.x + direction[0] * speed * 8),
                           int(self.y + direction[1] * speed * 8))

        for wall in walls:
            if test_rect.colliderect(wall.rect):
                return False
        return True


class Pellet(pygame.sprite.Sprite):
    """A collectible pellet/dot in the maze."""

    def __init__(self, x: int, y: int, image: Optional[pygame.Surface] = None,
                 is_power_pellet: bool = False, power_pellet_image: Optional[pygame.Surface] = None):
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
                pygame.draw.circle(self.image, YELLOW, (self.base_size // 2, self.base_size // 2),
                                   self.base_size // 2)
                self.base_image = None
        elif image:
            self.image = image
        else:
            self.image = pygame.Surface([4, 4])
            self.image.fill(WHITE)
            pygame.draw.ellipse(self.image, YELLOW, [0, 0, 4, 4])

        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        """Update power pellet animation (pulsing scale)."""
        if self.is_power_pellet:
            self.pulse_timer += 1
            # Pulse scale between 0.8 and 1.2
            scale = 1.0 + 0.2 * math.sin(self.pulse_timer * 0.1)
            old_center = self.rect.center

            if self.base_image:
                # Scale the soupbowl image
                base_w, base_h = self.base_image.get_size()
                new_w = int(base_w * scale)
                new_h = int(base_h * scale)
                self.image = pygame.transform.scale(self.base_image, (new_w, new_h))
            else:
                # Fallback: pulse size between 12 and 20
                size = int(16 * scale)
                self.image = pygame.Surface([size, size], pygame.SRCALPHA)
                pygame.draw.circle(self.image, YELLOW, (size // 2, size // 2), size // 2)

            self.rect = self.image.get_rect(center=old_center)


class PacmanGame(BaseGame):
    """
    Pac-Man game using AnimatedFerret for the player character.

    Features:
    - AnimatedFerret with movement animation while navigating
    - Directional sprite flipping based on horizontal movement
    - Death animation on ghost collision with 1-second pause
    - AI-driven ghost behavior with different personalities
    - Power pellets that allow eating ghosts
    - Soupcan sprites for ghosts, soupbowl for pellets
    """

    # Movement speed (reduced from 30 to make game more controllable)
    PLAYER_SPEED = 2.5

    # Maze wall data: [x, y, width, height]
    WALL_DATA = [
        [0, 0, 6, 600], [0, 0, 600, 6], [0, 600, 606, 6], [600, 0, 6, 606],
        [300, 0, 6, 66], [60, 60, 186, 6], [360, 60, 186, 6], [60, 120, 66, 6],
        [60, 120, 6, 126], [180, 120, 246, 6], [300, 120, 6, 66], [480, 120, 66, 6],
        [540, 120, 6, 126], [120, 180, 126, 6], [120, 180, 6, 126], [360, 180, 126, 6],
        [480, 180, 6, 126], [180, 240, 6, 126], [180, 360, 246, 6], [420, 240, 6, 126],
        [240, 240, 42, 6], [324, 240, 42, 6], [240, 240, 6, 66], [240, 300, 126, 6],
        [360, 240, 6, 66], [0, 300, 66, 6], [540, 300, 66, 6], [60, 360, 66, 6],
        [60, 360, 6, 186], [480, 360, 66, 6], [540, 360, 6, 186], [120, 420, 366, 6],
        [120, 420, 6, 66], [480, 420, 6, 66], [180, 480, 246, 6], [300, 480, 6, 66],
        [120, 540, 126, 6], [360, 540, 126, 6],
    ]

    # Power pellet positions (four corners of the maze)
    POWER_PELLET_POSITIONS = [
        (36, 66),     # Top-left
        (564, 66),    # Top-right
        (36, 534),    # Bottom-left
        (564, 534),   # Bottom-right
    ]

    # Player starting position (center-bottom of maze)
    PLAYER_START_X = 303
    PLAYER_START_Y = 454

    # Ghost spawn positions and types
    GHOST_DATA = [
        ('blinky', 303, 199),   # Red - direct chaser
        ('pinky', 303, 259),    # Pink - ambusher
        ('inky', 255, 259),     # Cyan - unpredictable
        ('clyde', 351, 259),    # Orange - shy
    ]

    # Maze colors - softer lavender cave theme
    MAZE_WALL_COLOR = MAZE_WALL_CUTE

    # Power mode duration (frames at 60 FPS)
    POWER_MODE_DURATION = 480  # 8 seconds

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            'ghost_speed': 1.6,           # Slower ghosts
            'ghost_frightened_speed': 0.9,
            'power_mode_duration': 600,   # 10 seconds power mode
        },
        Difficulty.NORMAL: {
            'ghost_speed': 2.3,           # Normal ghost speed
            'ghost_frightened_speed': 1.2,
            'power_mode_duration': 480,   # 8 seconds power mode
        },
        Difficulty.HARD: {
            'ghost_speed': 3.0,           # Faster ghosts
            'ghost_frightened_speed': 1.5,
            'power_mode_duration': 300,   # 5 seconds power mode
        },
    }

    def __init__(self, screen: pygame.Surface, input_manager):
        """Initialize the Pac-Man game."""
        # Store base directory for asset loading
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.asset_loader = AssetLoader(self.base_dir)

        # Game state
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.total_pellets = 0
        self.state = 'playing'  # 'playing', 'dying', 'resetting'
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
        self.queued_dir = None     # Queued direction for next valid turn

        # Player position as float for smooth movement
        self.player_x = float(self.PLAYER_START_X)
        self.player_y = float(self.PLAYER_START_Y)

        # Assets
        self.ghost_img: Optional[pygame.Surface] = None
        self.ghost_frightened_img: Optional[pygame.Surface] = None
        self.pellet_img: Optional[pygame.Surface] = None

        # Font for UI
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 48)

        # Call parent init (which calls setup)
        super().__init__(screen, input_manager)

    def setup(self):
        """Initialize or reset the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.ghost_speed = preset['ghost_speed']
        self.ghost_frightened_speed = preset['ghost_frightened_speed']
        self.power_mode_duration = preset['power_mode_duration']

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
        self.state = 'playing'
        self.death_timer = 0
        self.power_mode = False
        self.power_timer = 0
        self.ghost_eat_combo = 0
        self.player_dir = (1, 0)
        self.queued_dir = None
        self.paused = False
        self.score_manager = get_score_manager()
        self.high_score = self.score_manager.get_high_score('pacman')
        self.new_high_score = False

    def _load_assets(self):
        """Load game assets (ghost and pellet sprites)."""
        # Load ghost sprite (soupcan_new) - preserve aspect ratio to avoid distortion
        self.ghost_img = self.asset_loader.load_image('soupcan_new.png', (30, 30), preserve_aspect=True)
        if self.ghost_img is None:
            self.ghost_img = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(self.ghost_img, RED, [0, 0, 30, 30])

        # Frightened ghost will use the same soupcan but flashing colors (handled in Ghost class)
        self.ghost_frightened_img = self.ghost_img.copy()

        # Load pellet sprite (soupbowl, sized for visibility)
        self.pellet_img = self.asset_loader.load_image('soupbowl.png', (12, 12))

        # Load power pellet sprite (larger soupbowl)
        self.power_pellet_img = self.asset_loader.load_image('soupbowl.png', (24, 24))

    def _create_maze(self):
        """Create the maze walls and ghost gate."""
        self.walls.empty()
        self.gate.empty()

        # Create walls
        for wall_data in self.WALL_DATA:
            wall = Wall(wall_data[0], wall_data[1], wall_data[2], wall_data[3],
                        self.MAZE_WALL_COLOR)
            self.walls.add(wall)

        # Create ghost gate (thin white bar)
        gate = Wall(282, 242, 42, 2, WHITE)
        self.gate.add(gate)

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
            'blinky': 0,      # Starts immediately - always chasing
            'pinky': 90,      # 1.5 seconds
            'inky': 180,      # 3 seconds
            'clyde': 270,     # 4.5 seconds
        }

        for ghost_type, x, y in self.GHOST_DATA:
            ghost = Ghost(
                x=x, y=y,
                normal_image=self.ghost_img,
                frightened_image=self.ghost_frightened_img,
                ghost_type=ghost_type,
                spawn_pos=(x, y)
            )
            # Apply difficulty-based speeds (override class defaults)
            ghost.NORMAL_SPEED = self.ghost_speed
            ghost.FRIGHTENED_SPEED = self.ghost_frightened_speed
            # Scale cruise elroy speeds proportionally
            speed_ratio = self.ghost_speed / 2.3  # ratio vs normal default
            ghost.CRUISE_ELROY_SPEED = 2.7 * speed_ratio
            ghost.CRUISE_ELROY2_SPEED = 3.0 * speed_ratio
            # Set spawn delay based on ghost type
            ghost.spawn_delay = spawn_delays.get(ghost_type, 60)
            # Blinky starts outside the pen, others inside
            if ghost_type == 'blinky':
                ghost.in_spawn = False
                ghost.y = 200  # Start in the corridor above the ghost box
                ghost.direction = (-1, 0)  # Start moving left
            self.ghosts.append(ghost)

    def _create_pellets(self):
        """Create pellets and power pellets throughout the maze."""
        self.pellets.empty()
        self.power_pellets.empty()

        # Create a temporary player rect for collision check
        player_rect = pygame.Rect(
            self.PLAYER_START_X - 15,
            self.PLAYER_START_Y - 15,
            30,
            30
        )

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
        self.player.set_state('idle')
        self.player_dir = (0, 0)
        self.queued_dir = None

        # Reset ghosts
        self._create_ghosts()

        # End power mode
        self.power_mode = False
        self.power_timer = 0
        self.ghost_eat_combo = 0

        self.state = 'playing'

    def _reset_level(self):
        """Reset the entire level (all pellets, positions, score)."""
        self._reset_positions()
        self._create_pellets()
        self.total_pellets = len(self.pellets) + len(self.power_pellets)
        self.score = 0

    def handle_input(self) -> bool:
        """Process player input. Returns True to exit to menu."""
        # Update input manager for edge detection
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        # Check for pause toggle
        if self.input_manager.pause_pressed() and self.state == 'playing':
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Don't process movement input during death animation
        if self.state != 'playing':
            return False

        # Get D-pad direction
        dp = self.input_manager.get_dpad()

        # Handle keyboard input
        keys = pygame.key.get_pressed()

        # Combine keyboard and gamepad input
        new_dir = None
        if dp[0] == -1 or keys[pygame.K_LEFT]:
            new_dir = (-1, 0)
        elif dp[0] == 1 or keys[pygame.K_RIGHT]:
            new_dir = (1, 0)
        elif dp[1] == -1 or keys[pygame.K_UP]:
            new_dir = (0, -1)
        elif dp[1] == 1 or keys[pygame.K_DOWN]:
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

        if self.state == 'dying':
            # Update death animation
            self.death_timer += 1

            # Advance death animation
            dx = 1 if self.player.facing_right else -1
            self.player.update(dx, 0)  # Keep updating animation

            if self.death_timer >= self.death_duration:
                self.lives -= 1
                self._deaths_this_level = getattr(self, '_deaths_this_level', 0) + 1
                if self.lives <= 0:
                    # Game over - check and save high score
                    if self.score_manager.set_high_score('pacman', self.score):
                        self.new_high_score = True
                        self.high_score = self.score
                    # Check achievements
                    if self.score >= 1000:
                        self.achievements.unlock('pacman_1000')
                    # Track statistics
                    self.stats.increment('pacman', 'games_played')
                    self.stats.add('pacman', 'total_score', self.score)
                    self.stats.increment('global', 'games_started')
                    self._reset_level()
                    self.lives = 3
                else:
                    self._reset_positions()
            return

        if self.state != 'playing':
            return

        # Update power mode timer
        if self.power_mode:
            self.power_timer -= 1
            if self.power_timer <= 0:
                self.power_mode = False
                self.ghost_eat_combo = 0
                # Reset ghost modes
                for ghost in self.ghosts:
                    if ghost.mode == Ghost.MODE_FRIGHTENED:
                        ghost.mode = Ghost.MODE_CHASE

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
            if self.player.state != 'movement':
                self.player.set_state('movement')
        else:
            if self.player.state != 'idle':
                self.player.set_state('idle')
        self.player._advance_animation()

        # Update ghosts with AI
        blinky_pos = None
        pellets_remaining = len(self.pellets) + len(self.power_pellets)

        for ghost in self.ghosts:
            if ghost.ghost_type == 'blinky':
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
            ghost.update(self.walls, (self.player_x, self.player_y),
                         self.player_dir, blinky_pos)

        # Update power pellet animation
        for pellet in self.power_pellets:
            pellet.update()

        # Check pellet collection (larger hitbox for easier collection)
        player_rect = pygame.Rect(int(self.player_x) - 16, int(self.player_y) - 16, 32, 32)

        for pellet in list(self.pellets):
            if player_rect.colliderect(pellet.rect):
                self.pellets.remove(pellet)
                self.score += 10
                # No sound for regular pellets - only soup bowls make sound

        # Check power pellet collection
        for pellet in list(self.power_pellets):
            if player_rect.colliderect(pellet.rect):
                self.power_pellets.remove(pellet)
                self.score += 50
                self.audio.play_sound(AudioManager.SOUND_COLLECT)
                self._activate_power_mode()

        # Check ghost collision
        for ghost in self.ghosts:
            if player_rect.colliderect(ghost.rect):
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
                        self.achievements.unlock('pacman_ghost')
                    # Track ghost eaten stat
                    self.stats.increment('pacman', 'ghosts_eaten')
                elif ghost.mode != Ghost.MODE_EATEN:
                    # Player dies
                    self._start_death()
                    return

        # Check win condition (all pellets eaten)
        if len(self.pellets) == 0 and len(self.power_pellets) == 0:
            self.high_score = max(self.high_score, self.score)
            self.audio.play_sound(AudioManager.SOUND_VICTORY)
            # Check achievements
            self.achievements.unlock('pacman_first')
            if getattr(self, '_deaths_this_level', 0) == 0:
                self.achievements.unlock('pacman_no_death')
            # Track statistics
            self.stats.increment('pacman', 'levels_cleared')
            self.stats.increment('global', 'games_completed')
            self._deaths_this_level = 0  # Reset for next level
            self._reset_level()

    def _activate_power_mode(self):
        """Activate power mode - ghosts become vulnerable."""
        self.power_mode = True
        self.power_timer = self.power_mode_duration  # Use difficulty-based duration
        self.ghost_eat_combo = 0

        for ghost in self.ghosts:
            ghost.set_frightened(self.power_mode_duration)

    def _start_death(self):
        """Start the death animation sequence."""
        self.state = 'dying'
        self.death_timer = 0
        self.player.set_state('death')
        self.player_dir = (0, 0)
        self.audio.play_sound(AudioManager.SOUND_DEATH)

    def render(self):
        """Draw the game state to the screen."""
        # Draw cute cave background with gradient
        self.screen.fill(CAVE_BG_DARK)

        # Draw subtle twinkling stars in the background
        if not hasattr(self, '_star_timer'):
            self._star_timer = 0
            # Generate static star positions
            self._bg_stars = []
            for _ in range(30):
                sx = random.randint(10, WINDOW_WIDTH - 10)
                sy = random.randint(10, WINDOW_HEIGHT - 10)
                ss = random.randint(1, 3)
                sp = random.uniform(0, 6.28)  # Phase offset
                self._bg_stars.append((sx, sy, ss, sp))

        self._star_timer += 1
        for sx, sy, ss, sp in self._bg_stars:
            # Twinkling effect
            twinkle = abs(math.sin(self._star_timer * 0.05 + sp))
            alpha = int(50 + twinkle * 80)
            star_surf = pygame.Surface((ss * 2 + 2, ss * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(star_surf, (255, 255, 220, alpha), (ss + 1, ss + 1), ss)
            self.screen.blit(star_surf, (sx - ss - 1, sy - ss - 1))

        # Draw walls with soft glow effect
        for wall in self.walls:
            # Draw subtle glow behind wall
            glow_rect = wall.rect.inflate(4, 4)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*CAVE_WALL_GLOW, 40), glow_surf.get_rect(), border_radius=2)
            self.screen.blit(glow_surf, glow_rect.topleft)
        self.walls.draw(self.screen)

        # Draw gate with subtle glow
        self.gate.draw(self.screen)

        # Draw pellets with subtle glow effect
        for pellet in self.pellets:
            glow_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*PELLET_GLOW, 60), (6, 6), 6)
            self.screen.blit(glow_surf, (pellet.rect.centerx - 6, pellet.rect.centery - 6))
        self.pellets.draw(self.screen)

        # Draw power pellets with stronger glow
        for pellet in self.power_pellets:
            pulse = abs(math.sin(self._star_timer * 0.1)) * 0.5 + 0.5
            glow_size = int(20 + pulse * 8)
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*POWER_PELLET_GLOW, int(80 + pulse * 40)), (glow_size, glow_size), glow_size)
            self.screen.blit(glow_surf, (pellet.rect.centerx - glow_size, pellet.rect.centery - glow_size))
        self.power_pellets.draw(self.screen)

        # Draw player
        self.player.draw(self.screen)

        # Draw ghosts with subtle glow when frightened
        for ghost in self.ghosts:
            if ghost.mode == Ghost.MODE_FRIGHTENED:
                glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (100, 100, 255, 60), (20, 20), 18)
                self.screen.blit(glow_surf, (ghost.rect.centerx - 20, ghost.rect.centery - 20))
            self.screen.blit(ghost.image, ghost.rect)

        # Draw UI with shadow for readability
        pellets_left = len(self.pellets) + len(self.power_pellets)
        score_text = f"Score: {self.score}  High: {self.high_score}  Lives: {self.lives}  [B] Menu"
        shadow_surface = self.font.render(score_text, True, (40, 30, 60))
        self.screen.blit(shadow_surface, (11, 11))
        text_surface = self.font.render(score_text, True, WHITE)
        self.screen.blit(text_surface, (10, 10))

        # Show power mode indicator with glow
        if self.power_mode:
            remaining = self.power_timer / 60  # seconds
            power_text = f"POWER: {remaining:.1f}s"
            power_surface = self.font.render(power_text, True, (255, 200, 255))
            self.screen.blit(power_surface, (WINDOW_WIDTH - 130, 10))

        # Show pause overlay
        if self.paused:
            self._draw_pause_overlay()

        # Show death message during death animation
        if self.state == 'dying':
            if self.lives <= 1 and self.new_high_score:
                # Show new high score message on final death
                hs_text = self.large_font.render("NEW HIGH SCORE!", True, (255, 215, 0))
                hs_rect = hs_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
                self.screen.blit(hs_text, hs_rect)
                death_text = self.large_font.render("GAME OVER", True, (255, 150, 150))
                text_rect = death_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
                self.screen.blit(death_text, text_rect)
            else:
                death_text = self.large_font.render("CAUGHT!", True, (255, 150, 150))
                text_rect = death_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
                self.screen.blit(death_text, text_rect)


def run_pacman(screen: pygame.Surface) -> None:
    """
    Entry point for running Pac-Man from the game launcher.

    Args:
        screen: The pygame display surface to render to.
    """
    # Import InputManager here to avoid circular imports
    from engine import InputManager

    # Create input manager
    input_manager = InputManager()

    # Create and run the game
    game = PacmanGame(screen, input_manager)
    game.run()
