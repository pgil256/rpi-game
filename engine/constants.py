"""
Game constants for the Weasel Entertainment System.

This module contains extracted magic numbers from game implementations.
Import these instead of hardcoding values in games.

Usage:
    from engine.constants import CELL_SIZE_STANDARD, GameTiming
"""

from engine import WINDOW_WIDTH, WINDOW_HEIGHT, FPS


# =============================================================================
# GRID CONSTANTS
# =============================================================================

# Standard cell/tile sizes used across games
CELL_SIZE_SMALL = 20    # Compact grid (not currently used)
CELL_SIZE_STANDARD = 32  # Snake, Boulder Dash (800/32 = 25 cols, 600/32 = 18 rows)
CELL_SIZE_LARGE = 40    # Larger grid for visibility

# Derived grid dimensions for standard cell size
GRID_COLS_STANDARD = WINDOW_WIDTH // CELL_SIZE_STANDARD   # 25 columns
GRID_ROWS_STANDARD = WINDOW_HEIGHT // CELL_SIZE_STANDARD  # 18 rows

# Dig Dug specific (uses 25px cells)
CELL_SIZE_DIGDUG = 25
GRID_COLS_DIGDUG = WINDOW_WIDTH // CELL_SIZE_DIGDUG   # 32 columns
GRID_ROWS_DIGDUG = WINDOW_HEIGHT // CELL_SIZE_DIGDUG  # 24 rows


# =============================================================================
# PLAYER SPEEDS (pixels per frame at 60 FPS)
# =============================================================================

class PlayerSpeed:
    """Player movement speeds for different games/contexts."""
    SLOW = 2.0       # Slow/careful movement
    NORMAL = 2.5     # Standard player speed (Pac-Man)
    FAST = 3.0       # Fast movement
    VERY_FAST = 4.0  # Centipede player, Dig Dug player


# =============================================================================
# GHOST/ENEMY SPEEDS (Pac-Man specific)
# =============================================================================

class GhostSpeed:
    """Ghost movement speeds for Pac-Man."""
    NORMAL = 2.3           # Standard ghost speed
    CRUISE_ELROY = 2.7     # Blinky when few pellets remain
    CRUISE_ELROY2 = 3.0    # Blinky when very few pellets remain
    FRIGHTENED = 1.2       # When ghosts are vulnerable
    EATEN = 4.0            # When returning to spawn after being eaten


# =============================================================================
# PROJECTILE SPEEDS
# =============================================================================

class ProjectileSpeed:
    """Projectile/bullet speeds."""
    BULLET_SLOW = 8
    BULLET_NORMAL = 12
    BULLET_FAST = 15  # Centipede bullets


# =============================================================================
# ANIMATION TIMING (in frames at 60 FPS)
# =============================================================================

class GameTiming:
    """Timing constants for game events and animations."""

    # Idle animation transitions
    IDLE2_FRAMES = 5 * FPS       # 300 frames = 5 seconds to idle2
    SLEEP_FRAMES = 90 * FPS      # 5400 frames = 90 seconds to sleep

    # Game tick rates (for grid-based movement)
    SNAKE_TICK_SLOW = 12         # Frames between moves (slow)
    SNAKE_TICK_NORMAL = 8        # Frames between moves (normal)
    SNAKE_TICK_FAST = 5          # Frames between moves (fast)

    # Power-up durations
    POWER_PELLET_DURATION = 10 * FPS  # 600 frames = 10 seconds
    INVINCIBILITY_DURATION = 3 * FPS  # 180 frames = 3 seconds

    # Spawn/respawn delays
    RESPAWN_DELAY = 2 * FPS      # 120 frames = 2 seconds
    DEATH_ANIMATION = 1 * FPS    # 60 frames = 1 second


# =============================================================================
# GAMEPLAY THRESHOLDS
# =============================================================================

class GameThreshold:
    """Threshold values for game logic."""

    # Centipede
    FLEA_SOUP_THRESHOLD = 20     # Spawn flea when soup bowls below this

    # Pac-Man cruise elroy mode
    ELROY1_PELLETS = 20          # Blinky speeds up with this many pellets left
    ELROY2_PELLETS = 10          # Blinky speeds up more with this many left

    # Level completion
    BOULDER_DASH_DIAMONDS = 10   # Diamonds needed to complete level


# =============================================================================
# COLLISION RADII
# =============================================================================

class CollisionRadius:
    """Collision detection radii."""
    PLAYER_SMALL = 10
    PLAYER_NORMAL = 15
    PLAYER_LARGE = 20

    PELLET = 5
    POWER_PELLET = 8
    GHOST = 12

    DIG_RADIUS = 20  # Dig Dug terrain clearing radius


# =============================================================================
# SCORE VALUES
# =============================================================================

class ScoreValue:
    """Point values for game events."""

    # Pac-Man
    PELLET = 10
    POWER_PELLET = 50
    GHOST_BASE = 200      # First ghost: 200, then 400, 800, 1600
    FRUIT_CHERRY = 100
    FRUIT_STRAWBERRY = 300
    FRUIT_ORANGE = 500

    # Snake
    FOOD = 10

    # Centipede
    CENTIPEDE_SEGMENT = 10
    CENTIPEDE_HEAD = 100
    SPIDER = 300
    FLEA = 200
    SCORPION = 1000
    MUSHROOM = 1

    # Boulder Dash
    DIAMOND = 100
    BOULDER_CRUSH = 50

    # Dig Dug
    CRYSTAL = 50
    ENEMY_PUMP = 100


# =============================================================================
# LEVEL DIMENSIONS
# =============================================================================

class LevelBounds:
    """Level boundary definitions."""

    # Pac-Man maze (in pixels)
    MAZE_LEFT = 0
    MAZE_RIGHT = WINDOW_WIDTH
    MAZE_TOP = 50       # Space for score display
    MAZE_BOTTOM = WINDOW_HEIGHT - 30  # Space for lives display

    # Frogger lanes
    FROGGER_LANES = 12
    LANE_HEIGHT = WINDOW_HEIGHT // 14


# =============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# =============================================================================

# These match the original variable names used in games
CELL_SIZE = CELL_SIZE_STANDARD
GRID_WIDTH = GRID_COLS_STANDARD
GRID_HEIGHT = GRID_ROWS_STANDARD
PLAYER_SPEED = PlayerSpeed.VERY_FAST
BULLET_SPEED = ProjectileSpeed.BULLET_FAST
