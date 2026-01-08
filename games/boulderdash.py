"""
Boulder Dash - A Weasel Entertainment System Game

Help the ferret dig for treasure while avoiding cave-ins! Collect all 5 diamonds
while avoiding falling boulders.

This game uses the AnimatedFerret sprite with proper animations:
- DIG animation when moving through dirt tiles
- MOVEMENT when moving through empty space
- IDLE when stationary
- DEATH when crushed by falling boulder (play animation, brief pause, then respawn/game over)
- Facing direction based on horizontal movement

Now with extra cuteness: sparkles, particles, and bouncy animations!
"""

import pygame
import random
import math
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
    YELLOW,
    CYAN,
    BURROW_BROWN,
    WEASEL_BROWN,
)


# Grid configuration
TILE_SIZE = 32
GRID_COLS = WINDOW_WIDTH // TILE_SIZE  # 25 columns
GRID_ROWS = WINDOW_HEIGHT // TILE_SIZE  # 18 rows (with HUD at top)

# Tile types
TILE_EMPTY = 's'  # Space/empty
TILE_WALL = '#'   # Indestructible wall
TILE_DIRT = 'x'   # Diggable dirt
TILE_ROCK = 'o'   # Pushable/falling boulder
TILE_DIAMOND = 'd'  # Collectible diamond

# Cute pastel color palette - cozy burrow theme
CAVE_BG = (62, 48, 68)              # Soft plum background
CAVE_BG_LIGHT = (78, 62, 86)        # Slightly lighter for variation

# Pastel tile colors - warm and cozy
DIRT_CUTE = (186, 154, 126)         # Warm caramel dirt
DIRT_LIGHT = (210, 182, 158)        # Creamy highlight
WALL_CUTE = (142, 126, 158)         # Lavender stone
WALL_LIGHT = (174, 158, 186)        # Soft purple highlight
ROCK_CUTE = (178, 166, 186)         # Dusty lilac rock
ROCK_LIGHT = (206, 194, 214)        # Pale lavender highlight
EMPTY_CUTE = (52, 42, 58)           # Cozy dark purple

SPARKLE_COLORS = [
    (255, 248, 220),  # Cream
    (255, 218, 233),  # Soft pink
    (220, 248, 255),  # Baby blue
    (255, 255, 255),  # White
    (255, 234, 200),  # Peach glow
]
HEART_PINK = (255, 182, 206)        # Soft rose
HEART_RED = (255, 134, 166)         # Coral pink
DUST_COLOR = (210, 190, 174)        # Warm beige dust


class Particle:
    """A cute floating particle for visual effects."""

    def __init__(self, x, y, particle_type='sparkle'):
        self.x = x
        self.y = y
        self.particle_type = particle_type
        self.lifetime = random.randint(20, 40)
        self.max_lifetime = self.lifetime
        self.size = random.randint(2, 5)

        if particle_type == 'sparkle':
            self.vx = random.uniform(-1.5, 1.5)
            self.vy = random.uniform(-2.5, -0.5)
            self.color = random.choice(SPARKLE_COLORS)
        elif particle_type == 'heart':
            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(-2, -1)
            self.color = random.choice([HEART_PINK, HEART_RED])
            self.size = random.randint(6, 10)
            self.lifetime = random.randint(40, 70)
            self.max_lifetime = self.lifetime
        elif particle_type == 'dust':
            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(-1.5, 0)
            self.color = DUST_COLOR
            self.size = random.randint(3, 6)
            self.lifetime = random.randint(15, 25)
            self.max_lifetime = self.lifetime
        elif particle_type == 'star':
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(-1.5, -0.5)
            self.color = YELLOW
            self.size = random.randint(4, 8)
            self.lifetime = random.randint(50, 80)
            self.max_lifetime = self.lifetime
            self.rotation = random.uniform(0, math.pi * 2)
            self.rot_speed = random.uniform(-0.1, 0.1)

    def update(self):
        """Update particle position and lifetime."""
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

        # Gravity for some particles
        if self.particle_type in ('sparkle', 'dust'):
            self.vy += 0.05

        # Rotation for stars
        if self.particle_type == 'star':
            self.rotation += self.rot_speed

    def draw(self, screen):
        """Draw the particle."""
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        if alpha <= 0:
            return

        if self.particle_type == 'heart':
            self._draw_heart(screen, alpha)
        elif self.particle_type == 'star':
            self._draw_star(screen, alpha)
        else:
            # Simple circle for sparkles and dust
            color = (*self.color[:3], alpha) if len(self.color) == 3 else self.color
            size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, alpha), (size, size), size)
            screen.blit(surf, (int(self.x - size), int(self.y - size)))

    def _draw_heart(self, screen, alpha):
        """Draw a cute heart shape."""
        size = self.size
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        # Draw heart using two circles and a triangle
        r = size // 2
        color = (*self.color, alpha)
        pygame.draw.circle(surf, color, (r, r), r)
        pygame.draw.circle(surf, color, (size + r, r), r)
        pygame.draw.polygon(surf, color, [(0, r), (size * 2, r), (size, size * 2)])
        screen.blit(surf, (int(self.x - size), int(self.y - size)))

    def _draw_star(self, screen, alpha):
        """Draw a cute star shape."""
        size = self.size
        surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        cx, cy = size * 1.5, size * 1.5
        points = []
        for i in range(5):
            # Outer point
            angle = self.rotation + i * (2 * math.pi / 5) - math.pi / 2
            points.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
            # Inner point
            angle += math.pi / 5
            points.append((cx + size * 0.4 * math.cos(angle), cy + size * 0.4 * math.sin(angle)))
        pygame.draw.polygon(surf, (*self.color, alpha), points)
        screen.blit(surf, (int(self.x - size * 1.5), int(self.y - size * 1.5)))

    @property
    def alive(self):
        return self.lifetime > 0


class Sparkle:
    """A sparkling effect on diamonds."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 0
        self.sparkle_points = []
        self._regenerate_sparkles()

    def _regenerate_sparkles(self):
        """Create new sparkle positions."""
        self.sparkle_points = []
        for _ in range(3):
            ox = random.randint(-12, 12)
            oy = random.randint(-12, 12)
            self.sparkle_points.append((ox, oy, random.randint(0, 30)))

    def update(self):
        """Update sparkle animation."""
        self.timer += 1
        if self.timer >= 60:
            self.timer = 0
            self._regenerate_sparkles()

    def draw(self, screen):
        """Draw sparkles around the diamond."""
        for ox, oy, phase in self.sparkle_points:
            t = (self.timer + phase) % 30
            if t < 15:
                size = int(2 + 2 * math.sin(t * math.pi / 15))
                alpha = int(200 * math.sin(t * math.pi / 15))
                if size > 0 and alpha > 0:
                    surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                    # Draw a 4-pointed star shape
                    cx, cy = size + 1, size + 1
                    color = (255, 255, 220, alpha)
                    pygame.draw.line(surf, color, (cx - size, cy), (cx + size, cy), 2)
                    pygame.draw.line(surf, color, (cx, cy - size), (cx, cy + size), 2)
                    screen.blit(surf, (int(self.x + ox - size - 1), int(self.y + oy - size - 1)))


class BouncyRock:
    """A rock that bounces when it lands."""

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.bounce_timer = 0
        self.bounce_height = 0
        self.squish = 1.0

    def start_bounce(self):
        """Start the bounce animation."""
        self.bounce_timer = 15
        self.bounce_height = 6

    def update(self):
        """Update bounce animation."""
        if self.bounce_timer > 0:
            self.bounce_timer -= 1
            # Bouncy spring motion
            progress = self.bounce_timer / 15
            self.bounce_height = 6 * progress * abs(math.sin(progress * math.pi * 2))
            # Squish effect
            self.squish = 1.0 + 0.2 * math.sin(progress * math.pi * 3)

    @property
    def is_bouncing(self):
        return self.bounce_timer > 0


class BoulderDashGame(BaseGame):
    """Boulder Dash - Dig for diamonds and avoid falling boulders!

    Controls:
    - D-pad/Arrow keys: Move the ferret (grid-based movement)
    - B/ESC: Return to menu

    The ferret must dig through dirt to collect 5 diamonds.
    Boulders will fall when unsupported and can crush the player.
    Rocks can be pushed horizontally into empty space.
    """

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            'rock_multiplier': 0.6,    # Fewer rocks = safer
        },
        Difficulty.NORMAL: {
            'rock_multiplier': 1.0,    # Normal rock count
        },
        Difficulty.HARD: {
            'rock_multiplier': 1.5,    # More rocks = more hazards
        },
    }

    def setup(self):
        """Initialize the game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.rock_multiplier = preset['rock_multiplier']

        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)

        # Load sprites using AssetLoader
        self._load_sprites()

        # Create the animated ferret player
        self.ferret = AnimatedFerret(
            x=0,  # Will be set in _generate_level
            y=0,
            scale=1,  # 32x32 to match grid
            speed=0,  # We handle position directly
            frame_delay=4  # Faster animation for digging
        )
        self.ferret.set_state('idle')

        # Player grid position
        self.player_row = 0
        self.player_col = 0

        # Facing direction
        self.facing_right = True

        # Animation state tracking
        self.is_moving = False
        self.move_timer = 0
        self.is_dying = False
        self.death_timer = 0

        # Movement edge detection
        self.last_dpad = (0, 0)

        # Game state
        self.diamonds_collected = 0
        self.diamonds_needed = 5
        self.lives = 3
        self.game_won = False
        self.game_over = False
        self.current_level = 1
        self.max_levels = 5
        self.level_complete = False
        self.level_transition_timer = 0
        self.paused = False
        self.score_manager = get_score_manager()
        self.stats = get_stats_manager()
        # Boulder Dash high score is based on highest level reached
        self.high_score = self.score_manager.get_high_score('boulderdash')
        self.new_high_score = False
        self._total_diamonds = 0  # Track total diamonds this session
        self._levels_completed = 0  # Track levels completed this session
        self._deaths = 0  # Track deaths this session

        # Cute effects
        self.particles = []
        self.sparkles = {}  # Dict mapping (row, col) to Sparkle
        self.bouncy_rocks = {}  # Dict mapping (row, col) to BouncyRock
        self.falling_states = {}  # Dict mapping (row, col) to bool for falling state
        self.win_particles_spawned = False
        self.collect_flash_timer = 0  # Brief screen flash when collecting

        # Generate level
        self._generate_level(self.current_level)

        # Update ferret position
        self._update_ferret_visual_position()

    def _load_sprites(self):
        """Load tile sprites from sprite sheet and media directory."""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Use cute procedural tiles for a cohesive pastel aesthetic
        self.wall_sprite = self._create_fallback_tile(WALL_CUTE, 'wall')
        self.dirt_sprite = self._create_fallback_tile(DIRT_CUTE, 'dirt')
        self.rock_sprite = self._create_fallback_tile(ROCK_CUTE, 'rock')
        self.empty_sprite = self._create_fallback_tile(EMPTY_CUTE, 'empty')

        # Load soupbowl for diamonds
        asset_loader = AssetLoader(base_dir)
        self.diamond_sprite = asset_loader.load_image('soupbowl.png', (TILE_SIZE, TILE_SIZE))
        if not self.diamond_sprite:
            self.diamond_sprite = self._create_fallback_tile(CYAN)

    def _create_fallback_tile(self, color, style='flat'):
        """Create a fallback colored tile with cute styling."""
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        highlight = tuple(min(255, c + 40) for c in color)
        darker = tuple(max(0, c - 25) for c in color)
        soft_white = (255, 250, 245, 180)

        if style == 'rock':
            # Cute rounded rock with soft shine
            # Soft shadow
            pygame.draw.ellipse(surf, (*darker, 200), (4, 8, TILE_SIZE - 6, TILE_SIZE - 10))
            # Main rock body - nice rounded shape
            pygame.draw.ellipse(surf, color, (3, 4, TILE_SIZE - 6, TILE_SIZE - 8))
            # Soft inner glow
            inner_color = tuple(min(255, c + 20) for c in color)
            pygame.draw.ellipse(surf, inner_color, (6, 7, TILE_SIZE - 12, TILE_SIZE - 14))
            # Cute highlight shine (soft oval)
            pygame.draw.ellipse(surf, highlight, (7, 8, 10, 6))
            # Little sparkle dot
            pygame.draw.circle(surf, (255, 255, 255), (11, 10), 2)
            pygame.draw.circle(surf, (255, 255, 255, 150), (11, 10), 3)
        elif style == 'dirt':
            # Cozy soft dirt with warm texture
            pygame.draw.rect(surf, color, (0, 0, TILE_SIZE, TILE_SIZE), border_radius=4)
            # Subtle gradient - lighter top
            top_color = tuple(min(255, c + 15) for c in color)
            pygame.draw.rect(surf, top_color, (2, 2, TILE_SIZE-4, TILE_SIZE//3), border_radius=3)
            # Cute little texture specks
            speck_colors = [highlight, darker, tuple(min(255, c + 8) for c in color)]
            for _ in range(5):
                x = random.randint(5, TILE_SIZE - 7)
                y = random.randint(5, TILE_SIZE - 7)
                pygame.draw.circle(surf, random.choice(speck_colors), (x, y), random.randint(1, 2))
            # Tiny grass tufts (pastel green)
            grass_green = (158, 194, 142)
            for i in range(2):
                rx = 10 + i * 12
                pygame.draw.line(surf, grass_green, (rx, 0), (rx - 1, 5), 2)
                pygame.draw.line(surf, grass_green, (rx + 3, 0), (rx + 4, 4), 2)
        elif style == 'wall':
            # Cute rounded stone bricks with soft edges
            pygame.draw.rect(surf, darker, (0, 0, TILE_SIZE, TILE_SIZE), border_radius=2)
            # Top row bricks
            pygame.draw.rect(surf, color, (2, 2, TILE_SIZE//2 - 3, TILE_SIZE//2 - 3), border_radius=4)
            pygame.draw.rect(surf, color, (TILE_SIZE//2 + 1, 2, TILE_SIZE//2 - 3, TILE_SIZE//2 - 3), border_radius=4)
            # Bottom row (offset for brick pattern)
            pygame.draw.rect(surf, color, (TILE_SIZE//4, TILE_SIZE//2 + 1, TILE_SIZE//2, TILE_SIZE//2 - 3), border_radius=4)
            # Soft highlights on bricks
            pygame.draw.rect(surf, highlight, (4, 4, 8, 5), border_radius=2)
            pygame.draw.rect(surf, highlight, (TILE_SIZE//2 + 3, 4, 8, 5), border_radius=2)
            pygame.draw.rect(surf, highlight, (TILE_SIZE//4 + 2, TILE_SIZE//2 + 3, 8, 5), border_radius=2)
        elif style == 'empty':
            # Cozy cave floor with subtle warm tones
            surf.fill(color)
            # Add soft ambient texture
            for _ in range(3):
                x = random.randint(6, TILE_SIZE - 8)
                y = random.randint(6, TILE_SIZE - 8)
                pebble_color = tuple(min(255, c + random.randint(-10, 10)) for c in color)
                pygame.draw.circle(surf, pebble_color, (x, y), random.randint(1, 2))
        else:
            # Default flat fill
            surf.fill(color)

        return surf.convert_alpha()

    def _generate_level(self, level_num=1):
        """Generate a level with walls, dirt, rocks, and diamonds.

        Each level has unique characteristics:
        - Level 1: Simple open layout, few rocks
        - Level 2: Corridors with scattered rocks
        - Level 3: Chamber rooms connected by tunnels
        - Level 4: Maze-like with many rocks
        - Level 5: Dense rocks, diamonds in tricky spots
        """
        # Initialize grid with dirt
        self.grid = [[TILE_DIRT] * GRID_COLS for _ in range(GRID_ROWS)]

        # Add border walls
        for col in range(GRID_COLS):
            self.grid[0][col] = TILE_WALL
            self.grid[GRID_ROWS - 1][col] = TILE_WALL
        for row in range(GRID_ROWS):
            self.grid[row][0] = TILE_WALL
            self.grid[row][GRID_COLS - 1] = TILE_WALL

        # Track rock and diamond positions
        self.rocks = []
        self.diamonds = []

        # Reset cute effect trackers
        self.sparkles = {}
        self.bouncy_rocks = {}
        self.falling_states = {}
        self.particles = []
        self.win_particles_spawned = False
        self.level_complete = False

        # Level-specific parameters
        level_configs = {
            1: {'rocks': 12, 'diamonds': 5, 'walls': 0, 'style': 'open'},
            2: {'rocks': 18, 'diamonds': 6, 'walls': 8, 'style': 'corridors'},
            3: {'rocks': 22, 'diamonds': 7, 'walls': 15, 'style': 'chambers'},
            4: {'rocks': 28, 'diamonds': 8, 'walls': 20, 'style': 'maze'},
            5: {'rocks': 35, 'diamonds': 10, 'walls': 12, 'style': 'dense'},
        }

        config = level_configs.get(level_num, level_configs[5])
        self.diamonds_needed = config['diamonds']

        # Apply level-specific layout
        if config['style'] == 'corridors':
            self._add_corridor_walls()
        elif config['style'] == 'chambers':
            self._add_chamber_layout()
        elif config['style'] == 'maze':
            self._add_maze_walls()
        elif config['style'] == 'dense':
            self._add_scattered_walls(config['walls'])

        # Add extra internal walls based on level
        if config['style'] not in ('corridors', 'chambers', 'maze'):
            self._add_scattered_walls(config['walls'])

        # Place rocks (apply difficulty-based rock multiplier)
        target_rocks = int(config['rocks'] * self.rock_multiplier)
        rocks_placed = 0
        attempts = 0
        while rocks_placed < target_rocks and attempts < 500:
            row = random.randint(2, GRID_ROWS - 3)
            col = random.randint(2, GRID_COLS - 3)
            if self.grid[row][col] == TILE_DIRT:
                self.grid[row][col] = TILE_ROCK
                self.rocks.append([row, col])
                self.bouncy_rocks[(row, col)] = BouncyRock(row, col)
                rocks_placed += 1
            attempts += 1

        # Place diamonds in interesting spots
        diamonds_placed = 0
        attempts = 0
        while diamonds_placed < config['diamonds'] and attempts < 500:
            row = random.randint(2, GRID_ROWS - 3)
            col = random.randint(2, GRID_COLS - 3)
            if self.grid[row][col] == TILE_DIRT:
                # For harder levels, prefer spots near rocks or walls
                if level_num >= 3:
                    near_hazard = self._is_near_rock_or_wall(row, col)
                    if not near_hazard and random.random() < 0.6:
                        attempts += 1
                        continue

                self.grid[row][col] = TILE_DIAMOND
                self.diamonds.append([row, col])
                center_x = col * TILE_SIZE + TILE_SIZE // 2
                center_y = row * TILE_SIZE + TILE_SIZE // 2
                self.sparkles[(row, col)] = Sparkle(center_x, center_y)
                diamonds_placed += 1
            attempts += 1

        # Place player - find a safe starting spot
        self._place_player_safely()

    def _add_corridor_walls(self):
        """Add horizontal and vertical corridor walls."""
        # Horizontal corridors
        for row in [5, 10, 14]:
            for col in range(3, GRID_COLS - 3):
                if random.random() < 0.4:
                    self.grid[row][col] = TILE_WALL
        # Vertical corridors
        for col in [6, 12, 18]:
            for row in range(3, GRID_ROWS - 3):
                if random.random() < 0.3:
                    self.grid[row][col] = TILE_WALL

    def _add_chamber_layout(self):
        """Create chamber rooms connected by openings."""
        # Create 4 chambers with walls
        chambers = [
            (2, 2, 7, 10),      # Top-left
            (2, 14, 7, 22),     # Top-right
            (10, 2, 15, 10),    # Bottom-left
            (10, 14, 15, 22),   # Bottom-right
        ]

        for r1, c1, r2, c2 in chambers:
            # Draw chamber walls with gaps
            for col in range(c1, c2 + 1):
                if random.random() < 0.7:
                    self.grid[r1][col] = TILE_WALL
                if random.random() < 0.7:
                    self.grid[r2][col] = TILE_WALL
            for row in range(r1, r2 + 1):
                if random.random() < 0.7:
                    self.grid[row][c1] = TILE_WALL
                if random.random() < 0.7:
                    self.grid[row][c2] = TILE_WALL

            # Create doorways
            mid_row = (r1 + r2) // 2
            mid_col = (c1 + c2) // 2
            self.grid[mid_row][c1] = TILE_DIRT
            self.grid[mid_row][c2] = TILE_DIRT
            self.grid[r1][mid_col] = TILE_DIRT
            self.grid[r2][mid_col] = TILE_DIRT

    def _add_maze_walls(self):
        """Create a maze-like pattern of walls."""
        # Vertical wall segments
        for col in range(4, GRID_COLS - 4, 4):
            start_row = random.randint(2, 5)
            end_row = random.randint(GRID_ROWS - 6, GRID_ROWS - 3)
            gap = random.randint(start_row + 2, end_row - 2)
            for row in range(start_row, end_row):
                if abs(row - gap) > 1:
                    self.grid[row][col] = TILE_WALL

        # Horizontal wall segments
        for row in range(4, GRID_ROWS - 4, 4):
            start_col = random.randint(2, 5)
            end_col = random.randint(GRID_COLS - 6, GRID_COLS - 3)
            gap = random.randint(start_col + 2, end_col - 2)
            for col in range(start_col, end_col):
                if abs(col - gap) > 1:
                    self.grid[row][col] = TILE_WALL

    def _add_scattered_walls(self, count):
        """Add random scattered wall segments."""
        for _ in range(count):
            row = random.randint(3, GRID_ROWS - 4)
            col = random.randint(3, GRID_COLS - 4)
            # Create small wall clusters
            length = random.randint(2, 4)
            horizontal = random.choice([True, False])
            for i in range(length):
                if horizontal:
                    if col + i < GRID_COLS - 2:
                        self.grid[row][col + i] = TILE_WALL
                else:
                    if row + i < GRID_ROWS - 2:
                        self.grid[row + i][col] = TILE_WALL

    def _is_near_rock_or_wall(self, row, col):
        """Check if a position is adjacent to a rock or wall."""
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                    if self.grid[nr][nc] in (TILE_ROCK, TILE_WALL):
                        return True
        return False

    def _place_player_safely(self):
        """Find a safe starting position for the player."""
        # Try center first
        center_row, center_col = GRID_ROWS // 2, GRID_COLS // 2

        # Spiral outward to find a safe spot
        for radius in range(0, max(GRID_ROWS, GRID_COLS)):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    row = center_row + dr
                    col = center_col + dc
                    if 2 <= row < GRID_ROWS - 2 and 2 <= col < GRID_COLS - 2:
                        if self.grid[row][col] == TILE_DIRT:
                            # Check no rock directly above
                            if row > 1 and self.grid[row - 1][col] != TILE_ROCK:
                                self.player_row = row
                                self.player_col = col
                                self.grid[row][col] = TILE_EMPTY
                                # Clear a small safe zone
                                for adj_r, adj_c in [(row, col-1), (row, col+1)]:
                                    if 1 <= adj_c < GRID_COLS - 1:
                                        if self.grid[adj_r][adj_c] == TILE_DIRT:
                                            self.grid[adj_r][adj_c] = TILE_EMPTY
                                return

        # Fallback to center
        self.player_row = center_row
        self.player_col = center_col
        self.grid[center_row][center_col] = TILE_EMPTY

    def _update_ferret_visual_position(self):
        """Update the ferret's visual position to match grid position."""
        self.ferret.x = self.player_col * TILE_SIZE + TILE_SIZE // 2
        self.ferret.y = self.player_row * TILE_SIZE + TILE_SIZE // 2
        self.ferret.facing_right = self.facing_right

    def _spawn_collect_particles(self, row, col):
        """Spawn cute particles when collecting a diamond."""
        center_x = col * TILE_SIZE + TILE_SIZE // 2
        center_y = row * TILE_SIZE + TILE_SIZE // 2
        # Spawn sparkles
        for _ in range(8):
            self.particles.append(Particle(center_x, center_y, 'sparkle'))
        # Spawn a heart or two
        for _ in range(2):
            self.particles.append(Particle(center_x, center_y, 'heart'))
        # Flash effect
        self.collect_flash_timer = 6

    def _spawn_dust_particles(self, row, col):
        """Spawn dust puff when digging through dirt."""
        center_x = col * TILE_SIZE + TILE_SIZE // 2
        center_y = row * TILE_SIZE + TILE_SIZE // 2
        for _ in range(5):
            self.particles.append(Particle(center_x, center_y, 'dust'))

    def _spawn_win_particles(self):
        """Spawn celebration particles for winning."""
        for _ in range(30):
            x = random.randint(100, WINDOW_WIDTH - 100)
            y = random.randint(200, WINDOW_HEIGHT - 100)
            particle_type = random.choice(['heart', 'star', 'sparkle'])
            self.particles.append(Particle(x, y, particle_type))

    def _advance_to_next_level(self):
        """Advance to the next level or complete the game."""
        # Reset death counter for next level
        self._deaths_this_level = 0
        if self.current_level >= self.max_levels:
            # All levels complete! Save high score (max_levels as score)
            if self.score_manager.set_high_score('boulderdash', self.max_levels):
                self.new_high_score = True
                self.high_score = self.max_levels
            # Track statistics
            self.stats.increment('boulderdash', 'games_played')
            self.stats.increment('boulderdash', 'diamonds_collected', self._total_diamonds)
            self.stats.increment('boulderdash', 'levels_completed', self._levels_completed)
            self.stats.increment('boulderdash', 'deaths', self._deaths)
            self.stats.increment('global', 'games_started')
            self.stats.increment('global', 'games_completed')
            self.game_won = True
            self.level_complete = False
            self.win_particles_spawned = False
            # Achievement for completing all levels
            self.achievements.unlock('boulder_all')
        else:
            # Move to next level
            self.current_level += 1
            self.diamonds_collected = 0
            self.level_complete = False
            self.win_particles_spawned = False
            self._generate_level(self.current_level)
            self.ferret.set_state('emerge')
            self._update_ferret_visual_position()

    def _start_death(self):
        """Start the death animation sequence."""
        self.is_dying = True
        self.death_timer = 60  # 1 second at 60 FPS
        self.ferret.set_state('death')
        self.is_moving = False
        self.audio.play_sound(AudioManager.SOUND_DEATH)

    def _handle_death_complete(self):
        """Handle what happens after death animation completes."""
        self.is_dying = False
        self.lives -= 1
        self._deaths += 1  # Track for stats
        self._deaths_this_level = getattr(self, '_deaths_this_level', 0) + 1

        if self.lives <= 0:
            # Save high score (level reached as score)
            if self.score_manager.set_high_score('boulderdash', self.current_level):
                self.new_high_score = True
                self.high_score = self.current_level
            # Track statistics
            self.stats.increment('boulderdash', 'games_played')
            self.stats.increment('boulderdash', 'diamonds_collected', self._total_diamonds)
            self.stats.increment('boulderdash', 'levels_completed', self._levels_completed)
            self.stats.increment('boulderdash', 'deaths', self._deaths)
            self.stats.increment('global', 'games_started')
            self.game_over = True
        else:
            # Respawn player on current level
            self._generate_level(self.current_level)
            self.diamonds_collected = 0
            self.ferret.set_state('emerge')
            self._update_ferret_visual_position()

    def _try_move(self, dr, dc):
        """Attempt to move the player in the given direction.

        Args:
            dr: Row delta (-1 for up, 1 for down, 0 for none)
            dc: Column delta (-1 for left, 1 for right, 0 for none)

        Returns:
            bool: True if movement was successful
        """
        new_row = self.player_row + dr
        new_col = self.player_col + dc

        # Check bounds
        if not (0 <= new_row < GRID_ROWS and 0 <= new_col < GRID_COLS):
            return False

        target_tile = self.grid[new_row][new_col]

        # Can't move into walls
        if target_tile == TILE_WALL:
            return False

        # Handle different tile types
        if target_tile in (TILE_DIRT, TILE_EMPTY):
            # Moving through dirt = dig animation
            # Moving through empty = movement animation
            if target_tile == TILE_DIRT:
                self.ferret.set_state('dig')
                self.audio.play_sound(AudioManager.SOUND_DIG)
                # Spawn dust particles for digging
                self._spawn_dust_particles(new_row, new_col)
            else:
                self.ferret.set_state('movement')

            # Clear current position and move
            self.grid[self.player_row][self.player_col] = TILE_EMPTY
            self.player_row = new_row
            self.player_col = new_col
            self.grid[new_row][new_col] = TILE_EMPTY
            return True

        elif target_tile == TILE_DIAMOND:
            # Collect diamond with dig animation
            self.ferret.set_state('dig')
            self.grid[self.player_row][self.player_col] = TILE_EMPTY
            self.player_row = new_row
            self.player_col = new_col
            self.grid[new_row][new_col] = TILE_EMPTY
            self.diamonds_collected += 1
            self._total_diamonds += 1  # Track for stats
            self.audio.play_sound(AudioManager.SOUND_COLLECT)
            # Achievement for first diamond
            self.achievements.unlock('boulder_first')

            # Spawn cute collect particles
            self._spawn_collect_particles(new_row, new_col)

            # Remove sparkle effect for collected diamond
            if (new_row, new_col) in self.sparkles:
                del self.sparkles[(new_row, new_col)]

            # Remove from diamonds list
            self.diamonds = [d for d in self.diamonds if d != [new_row, new_col]]

            # Check for level complete
            if self.diamonds_collected >= self.diamonds_needed:
                self.level_complete = True
                self._levels_completed += 1  # Track for stats
                self.level_transition_timer = 120  # 2 seconds
                self.audio.play_sound(AudioManager.SOUND_VICTORY)
                # Achievements for level complete
                self.achievements.unlock('boulder_level')
                if getattr(self, '_deaths_this_level', 0) == 0:
                    self.achievements.unlock('boulder_no_crush')

            return True

        elif target_tile == TILE_ROCK and dr == 0:
            # Can only push rocks horizontally
            push_col = new_col + dc
            if 0 <= push_col < GRID_COLS and self.grid[new_row][push_col] == TILE_EMPTY:
                # Push the rock
                self.grid[new_row][new_col] = TILE_EMPTY
                self.grid[new_row][push_col] = TILE_ROCK

                # Update rock in list
                for rock in self.rocks:
                    if rock == [new_row, new_col]:
                        rock[0], rock[1] = new_row, push_col
                        break

                # Move player
                self.ferret.set_state('movement')
                self.grid[self.player_row][self.player_col] = TILE_EMPTY
                self.player_row = new_row
                self.player_col = new_col
                return True

        return False

    def _update_falling_objects(self):
        """Update falling physics for rocks and diamonds.

        Note: Processing bottom-to-top ensures objects can fall multiple tiles
        per frame without colliding with objects that haven't moved yet.
        """
        for objects, tile_type in [(self.rocks, TILE_ROCK), (self.diamonds, TILE_DIAMOND)]:
            for obj in objects:
                row, col = obj
                was_falling = self.falling_states.get((row, col), False)

                # Check if space below is empty
                if row + 1 < GRID_ROWS and self.grid[row + 1][col] == TILE_EMPTY:
                    # Clear current position
                    self.grid[row][col] = TILE_EMPTY

                    # Update bouncy rock tracking for rocks
                    if tile_type == TILE_ROCK and (row, col) in self.bouncy_rocks:
                        del self.bouncy_rocks[(row, col)]

                    # Update sparkle tracking for diamonds
                    if tile_type == TILE_DIAMOND and (row, col) in self.sparkles:
                        sparkle = self.sparkles.pop((row, col))
                        sparkle.x = col * TILE_SIZE + TILE_SIZE // 2
                        sparkle.y = (row + 1) * TILE_SIZE + TILE_SIZE // 2
                        self.sparkles[(row + 1, col)] = sparkle

                    # Clear old falling state and set new position
                    if (row, col) in self.falling_states:
                        del self.falling_states[(row, col)]

                    # Move down
                    obj[0] = row + 1
                    # Set new position
                    self.grid[row + 1][col] = tile_type

                    # Mark as falling at new position
                    self.falling_states[(row + 1, col)] = True

                    # Create new bouncy rock tracker at new position
                    if tile_type == TILE_ROCK:
                        self.bouncy_rocks[(row + 1, col)] = BouncyRock(row + 1, col)

                    # Check if fell on player
                    if row + 1 == self.player_row and col == self.player_col:
                        self._start_death()
                else:
                    # Object just landed
                    if was_falling:
                        self.falling_states[(row, col)] = False
                        # Trigger bounce animation for rocks
                        if tile_type == TILE_ROCK and (row, col) in self.bouncy_rocks:
                            self.bouncy_rocks[(row, col)].start_bounce()
                            # Spawn a little dust
                            self._spawn_dust_particles(row, col)

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        # Check for back button to return to menu
        if self.input_manager.back_pressed():
            return True

        # Check for pause toggle (only during normal gameplay)
        if self.input_manager.pause_pressed() and not self.is_dying and not self.level_complete and not self.game_won and not self.game_over:
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Don't process movement if dying, level complete, won, or game over
        if self.is_dying or self.level_complete or self.game_won or self.game_over:
            # Allow restart on game over or after full game win
            if (self.game_over or self.game_won) and self.input_manager.action_pressed():
                self.lives = 3
                self.diamonds_collected = 0
                self.current_level = 1
                self.game_over = False
                self.game_won = False
                self.level_complete = False
                self._generate_level(self.current_level)
                self.ferret.set_state('emerge')
                self._update_ferret_visual_position()
            return False

        # Handle movement with edge detection (grid-based)
        dp = self.input_manager.get_dpad()
        dr, dc = 0, 0

        if dp != self.last_dpad:
            if dp[1] != 0:  # Vertical movement
                dr = dp[1]
            elif dp[0] != 0:  # Horizontal movement
                dc = dp[0]

        self.last_dpad = dp

        # Process movement
        if dr != 0 or dc != 0:
            # Update facing direction for horizontal movement
            if dc > 0:
                self.facing_right = True
            elif dc < 0:
                self.facing_right = False

            if self._try_move(dr, dc):
                self.is_moving = True
                self.move_timer = 8  # Brief animation time
                self._update_ferret_visual_position()

        return False

    def update(self, dt):
        """Update game logic."""
        # Don't update when paused (except particles for visual continuity)
        if self.paused:
            return

        # Update particles (always, even during death/win)
        self.particles = [p for p in self.particles if p.alive]
        for particle in self.particles:
            particle.update()

        # Update sparkles on diamonds
        for sparkle in self.sparkles.values():
            sparkle.update()

        # Update bouncy rocks
        for rock in self.bouncy_rocks.values():
            rock.update()

        # Decrease collect flash timer
        if self.collect_flash_timer > 0:
            self.collect_flash_timer -= 1

        # Handle death animation
        if self.is_dying:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self._handle_death_complete()
            # Update ferret animation during death
            self.ferret.update(0, 0)
            return

        # Handle level complete state
        if self.level_complete:
            if not self.win_particles_spawned:
                self._spawn_win_particles()
                self.win_particles_spawned = True
            # Keep spawning particles periodically
            if random.random() < 0.1:
                x = random.randint(100, WINDOW_WIDTH - 100)
                y = random.randint(200, WINDOW_HEIGHT - 100)
                particle_type = random.choice(['heart', 'star'])
                self.particles.append(Particle(x, y, particle_type))

            # Countdown to next level
            self.level_transition_timer -= 1
            if self.level_transition_timer <= 0:
                self._advance_to_next_level()

            self.ferret.update(0, 0)
            return

        # Handle full game win state
        if self.game_won:
            if not self.win_particles_spawned:
                self._spawn_win_particles()
                self.win_particles_spawned = True
            # Keep spawning particles periodically
            if random.random() < 0.1:
                x = random.randint(100, WINDOW_WIDTH - 100)
                y = random.randint(200, WINDOW_HEIGHT - 100)
                particle_type = random.choice(['heart', 'star'])
                self.particles.append(Particle(x, y, particle_type))
            self.ferret.update(0, 0)
            return

        # Don't update if game over
        if self.game_over:
            self.ferret.update(0, 0)
            return

        # Handle movement animation timer
        if self.is_moving:
            self.move_timer -= 1
            if self.move_timer <= 0:
                self.is_moving = False
                self.ferret.set_state('idle')

        # Update falling objects
        self._update_falling_objects()

        # Update ferret animation
        self.ferret.update(0, 0)

    def render(self):
        """Draw the game state to the screen."""
        self.screen.fill(CAVE_BG)

        # Draw grid
        tile_sprites = {
            TILE_WALL: self.wall_sprite,
            TILE_DIRT: self.dirt_sprite,
            TILE_EMPTY: self.empty_sprite,
            TILE_DIAMOND: self.diamond_sprite,
        }

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                tile = self.grid[row][col]
                x = col * TILE_SIZE
                y = row * TILE_SIZE

                if tile == TILE_ROCK:
                    # Draw rocks with bounce effect
                    bouncy = self.bouncy_rocks.get((row, col))
                    if bouncy and bouncy.is_bouncing:
                        # Apply bounce offset and squish
                        bounce_y = y - bouncy.bounce_height
                        # Scale for squish effect
                        scaled_w = int(TILE_SIZE * bouncy.squish)
                        scaled_h = int(TILE_SIZE / bouncy.squish)
                        scaled_sprite = pygame.transform.scale(self.rock_sprite, (scaled_w, scaled_h))
                        # Center the scaled sprite
                        offset_x = (TILE_SIZE - scaled_w) // 2
                        offset_y = TILE_SIZE - scaled_h
                        self.screen.blit(scaled_sprite, (x + offset_x, bounce_y + offset_y))
                    else:
                        self.screen.blit(self.rock_sprite, (x, y))
                elif tile in tile_sprites:
                    self.screen.blit(tile_sprites[tile], (x, y))

        # Draw sparkles on diamonds (on top of diamond sprites)
        for sparkle in self.sparkles.values():
            sparkle.draw(self.screen)

        # Draw the ferret (on top of tiles)
        self.ferret.draw(self.screen)

        # Draw particles (on top of everything except HUD)
        for particle in self.particles:
            particle.draw(self.screen)

        # Draw collect flash effect
        if self.collect_flash_timer > 0:
            flash_alpha = int(100 * (self.collect_flash_timer / 6))
            flash_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 200, flash_alpha))
            self.screen.blit(flash_surf, (0, 0))

        # Draw HUD with cute styling
        self._draw_hud()

        # Draw win/lose/level complete/pause overlays
        if self.paused:
            self._draw_pause_overlay()
        elif self.level_complete:
            self._draw_level_complete_overlay()
        elif self.game_won:
            self._draw_win_overlay()
        elif self.game_over:
            if self.new_high_score:
                self._draw_overlay("NEW HIGH SCORE! Press A to restart", (255, 215, 0))
            else:
                self._draw_overlay("GAME OVER - Press A to restart", (255, 160, 160))

    def _draw_hud(self):
        """Draw the heads-up display with cute styling."""
        # Draw diamond count with little diamond icons
        hud_y = 8

        # Pretty diamond colors
        diamond_fill = (160, 230, 240)      # Soft cyan
        diamond_shine = (220, 250, 255)     # Light cyan shine
        diamond_empty = (120, 110, 130)     # Muted lavender outline

        # Draw collected diamonds as little icons
        icon_size = 16
        for i in range(self.diamonds_needed):
            icon_x = 10 + i * (icon_size + 6)
            diamond_points = [
                (icon_x + icon_size // 2, hud_y),
                (icon_x + icon_size, hud_y + icon_size // 2),
                (icon_x + icon_size // 2, hud_y + icon_size),
                (icon_x, hud_y + icon_size // 2)
            ]
            if i < self.diamonds_collected:
                # Filled diamond (collected) with shine
                pygame.draw.polygon(self.screen, diamond_fill, diamond_points)
                # Add cute shine line
                pygame.draw.line(self.screen, diamond_shine,
                    (icon_x + 4, hud_y + icon_size // 2 - 2),
                    (icon_x + icon_size // 2, hud_y + 3), 2)
            else:
                # Empty diamond outline (not collected)
                pygame.draw.polygon(self.screen, diamond_empty, diamond_points, 2)

        # Draw lives as little hearts with soft glow
        lives_x = 10 + self.diamonds_needed * (icon_size + 6) + 20
        for i in range(self.lives):
            hx = lives_x + i * 22
            hy = hud_y + 2
            # Soft glow behind heart
            glow_color = (*HEART_PINK[:3], 80)
            glow_surf = pygame.Surface((20, 18), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (6, 6), 6)
            pygame.draw.circle(glow_surf, glow_color, (14, 6), 6)
            self.screen.blit(glow_surf, (hx - 2, hy - 2))
            # Draw the heart
            pygame.draw.circle(self.screen, HEART_RED, (hx + 4, hy + 4), 4)
            pygame.draw.circle(self.screen, HEART_RED, (hx + 12, hy + 4), 4)
            pygame.draw.polygon(self.screen, HEART_RED, [(hx, hy + 4), (hx + 16, hy + 4), (hx + 8, hy + 14)])
            # Little shine on heart
            pygame.draw.circle(self.screen, HEART_PINK, (hx + 5, hy + 3), 2)

        # Draw level indicator
        level_color = (255, 230, 180)  # Warm cream
        level_text = self.small_font.render(f"Level {self.current_level}/{self.max_levels}", True, level_color)
        self.screen.blit(level_text, (WINDOW_WIDTH // 2 - level_text.get_width() // 2, hud_y))

        # Draw menu hint with softer color
        hint_text = self.small_font.render("[B] Menu", True, (190, 180, 200))
        self.screen.blit(hint_text, (WINDOW_WIDTH - hint_text.get_width() - 10, hud_y))

    def _draw_win_overlay(self):
        """Draw a cute win screen with celebration effects."""
        # Semi-transparent overlay with warm tint
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((40, 30, 50, 160))
        self.screen.blit(overlay, (0, 0))

        # Bouncy "YOU WIN!" text with soft golden color
        bounce = abs(math.sin(pygame.time.get_ticks() / 200)) * 10
        win_font = pygame.font.Font(None, 72)
        win_color = (255, 230, 150)  # Soft gold
        win_text = win_font.render("YOU WIN!", True, win_color)
        text_x = WINDOW_WIDTH // 2 - win_text.get_width() // 2
        text_y = WINDOW_HEIGHT // 2 - 50 - bounce
        self.screen.blit(win_text, (text_x, text_y))

        # Subtitle with cream color
        sub_color = (255, 248, 235)  # Warm cream
        sub_text = self.font.render(f"All {self.max_levels} levels complete!", True, sub_color)
        self.screen.blit(sub_text, (WINDOW_WIDTH // 2 - sub_text.get_width() // 2, WINDOW_HEIGHT // 2 + 20))

        # Hint text with soft lavender
        hint_color = (200, 190, 210)  # Soft lavender
        hint_text = self.small_font.render("Press A to play again or B for menu", True, hint_color)
        self.screen.blit(hint_text, (WINDOW_WIDTH // 2 - hint_text.get_width() // 2, WINDOW_HEIGHT // 2 + 60))

    def _draw_level_complete_overlay(self):
        """Draw a cute level complete screen."""
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((30, 40, 50, 140))
        self.screen.blit(overlay, (0, 0))

        # Bouncy level complete text
        bounce = abs(math.sin(pygame.time.get_ticks() / 150)) * 8
        complete_font = pygame.font.Font(None, 64)
        complete_color = (180, 255, 200)  # Soft mint green
        complete_text = complete_font.render(f"Level {self.current_level} Complete!", True, complete_color)
        text_x = WINDOW_WIDTH // 2 - complete_text.get_width() // 2
        text_y = WINDOW_HEIGHT // 2 - 40 - bounce
        self.screen.blit(complete_text, (text_x, text_y))

        # Next level hint
        if self.current_level < self.max_levels:
            next_text = self.font.render(f"Get ready for Level {self.current_level + 1}...", True, (255, 248, 235))
        else:
            next_text = self.font.render("Final level complete!", True, (255, 230, 150))
        self.screen.blit(next_text, (WINDOW_WIDTH // 2 - next_text.get_width() // 2, WINDOW_HEIGHT // 2 + 30))

    def _draw_overlay(self, message, color):
        """Draw a semi-transparent overlay with a message."""
        # Use cached overlay surface
        if not hasattr(self, '_overlay_surface'):
            self._overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            self._overlay_surface.fill((0, 0, 0, 180))
        self.screen.blit(self._overlay_surface, (0, 0))

        text = self.font.render(message, True, color)
        self.screen.blit(
            text,
            (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2)
        )


def run_boulderdash(screen, input_manager):
    """Entry point for the Boulder Dash game.

    Args:
        screen: The pygame display surface.
        input_manager: The InputManager instance.
    """
    game = BoulderDashGame(screen, input_manager)
    game.run()
