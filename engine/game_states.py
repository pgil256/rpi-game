"""
Game state enumerations for the Weasel Entertainment System.

Use these enums instead of string literals for game states.
This provides type safety and IDE autocompletion.

Usage:
    from engine.game_states import GameState

    class MyGame(BaseGame):
        def setup(self):
            self.state = GameState.PLAYING

        def update(self, dt):
            if self.state == GameState.PAUSED:
                return
            # ... game logic
"""

from enum import Enum, auto


class GameState(Enum):
    """
    Standard game states used across all games.

    States:
        PLAYING: Normal gameplay, accepting input, updating game logic
        PAUSED: Game frozen, waiting for unpause
        DYING: Death animation playing, no input accepted
        GAME_OVER: Game ended, showing game over screen
        VICTORY: Level/game completed successfully
        RESETTING: Transitioning to next life or level
        COUNTDOWN: Pre-game countdown (3, 2, 1, GO!)
        READY: Waiting for player to start (press any button)
    """
    PLAYING = auto()
    PAUSED = auto()
    DYING = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    RESETTING = auto()
    COUNTDOWN = auto()
    READY = auto()


class MenuState(Enum):
    """
    Menu navigation states.

    States:
        MAIN: Main menu showing game selection
        SETTINGS: Settings/options screen
        CONTROLS: Control configuration screen
        CREDITS: Credits display
        CONFIRM_EXIT: Exit confirmation dialog
    """
    MAIN = auto()
    SETTINGS = auto()
    CONTROLS = auto()
    CREDITS = auto()
    CONFIRM_EXIT = auto()


class GhostState(Enum):
    """
    Pac-Man ghost AI states.

    States:
        SCATTER: Ghost moves to its corner
        CHASE: Ghost actively pursues player
        FRIGHTENED: Ghost runs away (after power pellet)
        EATEN: Ghost returning to spawn
        IN_HOUSE: Ghost waiting in spawn area
        LEAVING_HOUSE: Ghost exiting spawn area
    """
    SCATTER = auto()
    CHASE = auto()
    FRIGHTENED = auto()
    EATEN = auto()
    IN_HOUSE = auto()
    LEAVING_HOUSE = auto()


class Direction(Enum):
    """
    Cardinal directions for movement.

    Values are (dx, dy) tuples for easy movement calculation.
    """
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    NONE = (0, 0)

    @property
    def dx(self) -> int:
        """X component of direction."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Y component of direction."""
        return self.value[1]

    @property
    def opposite(self) -> 'Direction':
        """Return the opposite direction."""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
            Direction.NONE: Direction.NONE,
        }
        return opposites[self]

    @classmethod
    def from_dpad(cls, dx: int, dy: int) -> 'Direction':
        """Convert d-pad input to Direction enum."""
        if dy < 0:
            return cls.UP
        elif dy > 0:
            return cls.DOWN
        elif dx < 0:
            return cls.LEFT
        elif dx > 0:
            return cls.RIGHT
        return cls.NONE


class TileType(Enum):
    """
    Tile types for grid-based games (Boulder Dash, Dig Dug).

    Games can extend this with game-specific tiles.
    """
    EMPTY = auto()
    WALL = auto()
    DIRT = auto()
    BOULDER = auto()
    DIAMOND = auto()
    EXIT = auto()
    PLAYER_START = auto()
    ENEMY_START = auto()


class Difficulty(Enum):
    """
    Game difficulty levels.

    Each game implements its own presets for these difficulty levels.
    Typical adjustments:
        EASY: Slower enemies, more lives, easier objectives
        NORMAL: Default balanced gameplay
        HARD: Faster enemies, fewer lives, harder objectives
    """
    EASY = auto()
    NORMAL = auto()
    HARD = auto()

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        return self.name.capitalize()

    @property
    def description(self) -> str:
        """Short description for UI display."""
        descriptions = {
            Difficulty.EASY: "Relaxed gameplay for beginners",
            Difficulty.NORMAL: "Balanced challenge",
            Difficulty.HARD: "For experienced players",
        }
        return descriptions[self]
