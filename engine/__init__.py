"""
Weasel Entertainment System (WES) Engine Package

This package provides reusable components for building games:
- AnimatedFerret: Animated sprite class for the ferret/weasel character
- InputManager: Unified keyboard/gamepad input handling with edge detection
- BaseGame: Abstract base class for game implementations
- AssetLoader: Centralized asset loading with caching and fallbacks
- AudioManager: Sound effects and music with graceful fallback

Usage:
    from engine import AnimatedFerret, InputManager, BaseGame, AssetLoader, AudioManager

    # Or import specific modules
    from engine.ferret_sprite import AnimatedFerret
    from engine.input_manager import InputManager
    from engine.base_game import BaseGame
    from engine.asset_loader import AssetLoader
    from engine.audio_manager import AudioManager, get_audio_manager
"""

# =============================================================================
# SHARED CONSTANTS
# =============================================================================
# These are the canonical definitions - all modules should import from here

# Window settings
WINDOW_WIDTH: int = 800
WINDOW_HEIGHT: int = 600
FPS: int = 60

# Weasel/Ferret color palette
WEASEL_BROWN: tuple = (139, 90, 43)    # Brown for head/front
WEASEL_TAN: tuple = (210, 180, 140)    # Tan/cream for body
WEASEL_WHITE: tuple = (255, 248, 220)  # Cream white for underbelly
BURROW_BROWN: tuple = (101, 67, 33)    # Dark earthy brown for background

# Alias ferret colors to weasel colors for compatibility
FERRET_BROWN = WEASEL_BROWN
FERRET_TAN = WEASEL_TAN
FERRET_WHITE = WEASEL_WHITE

# Gamepad button mappings (USB Gamepad)
# Mapping: A=1, B=2, Select=8, Start=9
BUTTON_A: int = 1       # A button (confirm/action)
BUTTON_B: int = 2       # B button (back/cancel)
BUTTON_SELECT: int = 8  # Select button
BUTTON_START: int = 9   # Start button
DEADZONE: float = 0.3   # Analog stick deadzone

# Common colors
BLACK: tuple = (0, 0, 0)
WHITE: tuple = (255, 255, 255)
RED: tuple = (255, 0, 0)
GREEN: tuple = (0, 255, 0)
BLUE: tuple = (0, 0, 255)
YELLOW: tuple = (255, 255, 0)
CYAN: tuple = (0, 255, 255)
MAGENTA: tuple = (255, 0, 255)

# Cute/Pastel color palette for soft, inviting UI
PASTEL_PINK: tuple = (255, 182, 193)       # Light pink
PASTEL_PEACH: tuple = (255, 218, 185)      # Soft peach
PASTEL_CREAM: tuple = (255, 253, 208)      # Warm cream
PASTEL_MINT: tuple = (189, 252, 201)       # Soft mint green
PASTEL_SKY: tuple = (173, 216, 230)        # Light sky blue
PASTEL_LAVENDER: tuple = (230, 190, 230)   # Soft lavender

# Cute background colors
SOFT_SAGE: tuple = (188, 210, 180)         # Soft sage green background
WARM_CREAM: tuple = (255, 248, 235)        # Warm cream background
LIGHT_TERRACOTTA: tuple = (230, 190, 165)  # Light terracotta
COZY_TAN: tuple = (235, 220, 200)          # Cozy warm tan

# Cute accent colors
CORAL_PINK: tuple = (255, 150, 150)        # Soft coral
BUTTER_YELLOW: tuple = (255, 245, 157)     # Soft butter yellow
SEAFOAM: tuple = (160, 220, 210)           # Seafoam green
BLUSH: tuple = (255, 200, 200)             # Blush pink

# UI colors for cute theme
CUTE_BG_PRIMARY: tuple = (235, 225, 210)   # Main background (warm beige)
CUTE_BG_SECONDARY: tuple = (245, 235, 220) # Lighter variation
CUTE_BUTTON_BG: tuple = (255, 240, 230)    # Button background
CUTE_BUTTON_HOVER: tuple = (255, 220, 210) # Button hover
CUTE_SHADOW: tuple = (200, 180, 165)       # Soft shadow color

# Enhanced cute game colors - softer, more kawaii palette
KAWAII_PINK: tuple = (255, 182, 193)       # Soft kawaii pink
KAWAII_BLUE: tuple = (173, 216, 230)       # Baby blue
KAWAII_PURPLE: tuple = (221, 160, 221)     # Plum/lavender
KAWAII_MINT: tuple = (152, 251, 152)       # Pale mint
KAWAII_PEACH: tuple = (255, 218, 185)      # Soft peach
KAWAII_YELLOW: tuple = (255, 250, 205)     # Lemon chiffon

# Starry/magical colors
STAR_GOLD: tuple = (255, 215, 0)           # Golden star
STAR_WHITE: tuple = (255, 255, 240)        # Ivory star
MAGIC_GLOW: tuple = (230, 230, 250)        # Lavender glow
RAINBOW_COLORS: tuple = (
    (255, 182, 193),  # Pink
    (255, 218, 185),  # Peach
    (255, 255, 180),  # Yellow
    (152, 251, 152),  # Mint
    (173, 216, 230),  # Sky blue
    (221, 160, 221),  # Lavender
)

# Gradient sky colors (top to bottom)
SKY_DAWN: tuple = ((255, 183, 197), (255, 213, 166))       # Pink to peach
SKY_DAY: tuple = ((135, 206, 235), (176, 226, 255))        # Sky blue to light blue
SKY_SUNSET: tuple = ((255, 127, 80), (255, 218, 185))      # Coral to peach
SKY_NIGHT: tuple = ((25, 25, 112), (72, 61, 139))          # Midnight to purple

# Nature colors
GRASS_LIGHT: tuple = (144, 238, 144)       # Light green grass
GRASS_DARK: tuple = (34, 139, 34)          # Forest green
WATER_LIGHT: tuple = (173, 216, 230)       # Light blue water
WATER_SHIMMER: tuple = (224, 255, 255)     # Light cyan shimmer
FLOWER_PINK: tuple = (255, 182, 193)       # Pink flower
FLOWER_YELLOW: tuple = (255, 255, 150)     # Yellow flower
FLOWER_PURPLE: tuple = (218, 112, 214)     # Orchid purple
FLOWER_WHITE: tuple = (255, 250, 250)      # Snow white


# =============================================================================
# FULLSCREEN SCALING
# =============================================================================
# The launcher sets this callback to handle scaling in fullscreen mode
_scale_to_screen_callback = None

def set_scale_callback(callback):
    """Set the callback function for fullscreen scaling.

    Called by the launcher to enable proper fullscreen scaling.
    """
    global _scale_to_screen_callback
    _scale_to_screen_callback = callback

def scale_to_screen():
    """Scale the render surface to the real screen (fullscreen mode).

    In windowed mode, this just calls pygame.display.flip().
    In fullscreen mode, this scales the 800x600 render surface to fill the screen.
    """
    if _scale_to_screen_callback:
        _scale_to_screen_callback()
    else:
        import pygame
        pygame.display.flip()


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def get_weasel_color(index: int) -> tuple:
    """Get weasel color for segment based on index (0=head/front).

    Args:
        index: Segment index, 0 is head/front.

    Returns:
        RGB tuple for the segment color.
    """
    if index == 0:
        return WEASEL_BROWN
    elif index == 1:
        return WEASEL_TAN
    elif index == 2:
        return WEASEL_WHITE
    else:
        return WEASEL_TAN  # Repeating tans


# =============================================================================
# IMPORTS FROM SUBMODULES
# =============================================================================

# Import main classes
from engine.ferret_sprite import AnimatedFerret, ANIMATION_STATES
from engine.input_manager import InputManager, get_input_manager
from engine.base_game import BaseGame
from engine.asset_loader import AssetLoader, get_default_loader, detect_platform
from engine.audio_manager import AudioManager, get_audio_manager
from engine.score_manager import ScoreManager, get_score_manager
from engine.settings_manager import SettingsManager, get_settings_manager
from engine.achievements import AchievementManager, get_achievement_manager, ACHIEVEMENTS
from engine.stats_manager import StatsManager, get_stats_manager
from engine.demo_manager import DemoManager, get_demo_manager

# Import backward-compatible module-level functions
from engine.input_manager import (
    init_joystick,
    get_dpad,
    get_button,
    get_any_action_button,
    get_any_back_button,
)
from engine.asset_loader import load_media_image

# Import game states and constants
from engine.game_states import GameState, MenuState, GhostState, Direction, TileType, Difficulty
from engine.constants import (
    # Grid constants
    CELL_SIZE_STANDARD,
    CELL_SIZE_DIGDUG,
    GRID_COLS_STANDARD,
    GRID_ROWS_STANDARD,
    # Speed classes
    PlayerSpeed,
    GhostSpeed,
    ProjectileSpeed,
    # Timing and thresholds
    GameTiming,
    GameThreshold,
    # Other classes
    CollisionRadius,
    ScoreValue,
    LevelBounds,
)


# =============================================================================
# VERSION
# =============================================================================
__version__ = '1.0.0'


# =============================================================================
# PUBLIC API
# =============================================================================
__all__ = [
    # Constants
    'WINDOW_WIDTH',
    'WINDOW_HEIGHT',
    'FPS',
    'WEASEL_BROWN',
    'WEASEL_TAN',
    'WEASEL_WHITE',
    'BURROW_BROWN',
    'FERRET_BROWN',
    'FERRET_TAN',
    'FERRET_WHITE',
    'BUTTON_A',
    'BUTTON_B',
    'BUTTON_SELECT',
    'BUTTON_START',
    'DEADZONE',
    'BLACK',
    'WHITE',
    'RED',
    'GREEN',
    'BLUE',
    'YELLOW',
    'CYAN',
    'MAGENTA',
    # Cute/Pastel colors
    'PASTEL_PINK',
    'PASTEL_PEACH',
    'PASTEL_CREAM',
    'PASTEL_MINT',
    'PASTEL_SKY',
    'PASTEL_LAVENDER',
    'SOFT_SAGE',
    'WARM_CREAM',
    'LIGHT_TERRACOTTA',
    'COZY_TAN',
    'CORAL_PINK',
    'BUTTER_YELLOW',
    'SEAFOAM',
    'BLUSH',
    'CUTE_BG_PRIMARY',
    'CUTE_BG_SECONDARY',
    'CUTE_BUTTON_BG',
    'CUTE_BUTTON_HOVER',
    'CUTE_SHADOW',
    # Kawaii colors
    'KAWAII_PINK',
    'KAWAII_BLUE',
    'KAWAII_PURPLE',
    'KAWAII_MINT',
    'KAWAII_PEACH',
    'KAWAII_YELLOW',
    # Starry/magical colors
    'STAR_GOLD',
    'STAR_WHITE',
    'MAGIC_GLOW',
    'RAINBOW_COLORS',
    # Sky gradients
    'SKY_DAWN',
    'SKY_DAY',
    'SKY_SUNSET',
    'SKY_NIGHT',
    # Nature colors
    'GRASS_LIGHT',
    'GRASS_DARK',
    'WATER_LIGHT',
    'WATER_SHIMMER',
    'FLOWER_PINK',
    'FLOWER_YELLOW',
    'FLOWER_PURPLE',
    'FLOWER_WHITE',

    # Classes
    'AnimatedFerret',
    'InputManager',
    'BaseGame',
    'AssetLoader',
    'AudioManager',
    'ScoreManager',
    'SettingsManager',
    'AchievementManager',
    'StatsManager',
    'DemoManager',

    # Animation states
    'ANIMATION_STATES',

    # Achievement definitions
    'ACHIEVEMENTS',

    # Factory functions
    'get_input_manager',
    'get_default_loader',
    'get_audio_manager',
    'get_score_manager',
    'get_settings_manager',
    'get_achievement_manager',
    'get_stats_manager',
    'get_demo_manager',

    # Backward-compatible functions
    'init_joystick',
    'get_dpad',
    'get_button',
    'get_any_action_button',
    'get_any_back_button',
    'load_media_image',
    'get_weasel_color',
    'set_scale_callback',
    'scale_to_screen',
    'detect_platform',

    # Game states (enums)
    'GameState',
    'MenuState',
    'GhostState',
    'Direction',
    'TileType',
    'Difficulty',

    # Game constants
    'CELL_SIZE_STANDARD',
    'CELL_SIZE_DIGDUG',
    'GRID_COLS_STANDARD',
    'GRID_ROWS_STANDARD',
    'PlayerSpeed',
    'GhostSpeed',
    'ProjectileSpeed',
    'GameTiming',
    'GameThreshold',
    'CollisionRadius',
    'ScoreValue',
    'LevelBounds',
]
