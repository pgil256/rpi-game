"""Shared direction and difficulty values used by the games."""

from enum import Enum, auto


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
    def opposite(self) -> "Direction":
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
    def from_dpad(cls, dx: int, dy: int) -> "Direction":
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
