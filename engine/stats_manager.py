"""
Statistics tracking for the Winston Entertainment System.

Tracks and persists gameplay statistics like play time, games played, deaths, etc.

Usage:
    from engine.stats_manager import get_stats_manager

    stats = get_stats_manager()

    # Track events
    stats.increment('snake', 'games_played')
    stats.increment('snake', 'deaths')
    stats.add('snake', 'total_score', 150)
    stats.add('global', 'play_time', 60.5)  # seconds

    # Get stats
    games = stats.get('snake', 'games_played')
    total_time = stats.get('global', 'play_time')
"""

import math
from copy import deepcopy
from engine.persistence import JsonStore, data_path, is_demo
from typing import Optional, Any


class StatsManager:
    """Manages gameplay statistics and persistence."""

    def __init__(self, save_file: str = "stats.json"):
        """Initialize the stats manager.

        Args:
            save_file: Name of the JSON file to store stats.
        """
        self.save_path = data_path(save_file)
        self._store = JsonStore(self.save_path, legacy_name=save_file)
        self._dirty = False
        self.stats = self._load()

    def _load(self) -> dict:
        result = self._default_stats()
        for category, values in self._store.load().items():
            if isinstance(values, dict):
                valid = {
                    k: v
                    for k, v in values.items()
                    if isinstance(v, (int, float))
                    and not isinstance(v, bool)
                    and math.isfinite(v)
                    and v >= 0
                }
                result.setdefault(category, {}).update(valid)
        return result

    def _default_stats(self) -> dict:
        """Return default stats structure."""
        return {
            "global": {
                "total_play_time": 0,  # Total seconds played
                "games_started": 0,  # Total games started
                "games_completed": 0,  # Total games completed/won
            },
            "snake": {
                "games_played": 0,
                "total_score": 0,
                "highest_length": 0,
                "deaths": 0,
            },
            "pacman": {
                "games_played": 0,
                "total_score": 0,
                "ghosts_eaten": 0,
                "levels_cleared": 0,
                "deaths": 0,
            },
            "frogger": {
                "games_played": 0,
                "crossings": 0,
                "deaths": 0,
            },
            "centipede": {
                "games_played": 0,
                "total_score": 0,
                "centipedes_destroyed": 0,
                "spiders_killed": 0,
                "deaths": 0,
            },
            "digdug": {
                "games_played": 0,
                "crystals_collected": 0,
                "wins": 0,
                "deaths": 0,
            },
            "boulderdash": {
                "games_played": 0,
                "diamonds_collected": 0,
                "levels_completed": 0,
                "deaths": 0,
            },
        }

    def save(self) -> bool:
        """Flush a batch of changes; the game loop calls this after each step."""
        if is_demo() or not self._dirty:
            return False
        saved = self._store.save(self.stats)
        if saved:
            self._dirty = False
        return saved

    def get(self, category: str, stat_name: str, default: Any = 0) -> Any:
        """Get a statistic value.

        Args:
            category: Category name ('global', 'snake', etc.)
            stat_name: Name of the statistic
            default: Default value if not found

        Returns:
            The statistic value or default.
        """
        if category not in self.stats:
            return default
        return self.stats[category].get(stat_name, default)

    def set(self, category: str, stat_name: str, value: Any) -> None:
        """Set a statistic value.

        Args:
            category: Category name ('global', 'snake', etc.)
            stat_name: Name of the statistic
            value: Value to set
        """
        if is_demo():
            return
        if category not in self.stats:
            self.stats[category] = {}
        if self.stats[category].get(stat_name) != value:
            self.stats[category][stat_name] = value
            self._dirty = True

    def increment(self, category: str, stat_name: str, amount: int = 1) -> int:
        """Increment a statistic by amount.

        Args:
            category: Category name ('global', 'snake', etc.)
            stat_name: Name of the statistic
            amount: Amount to increment by

        Returns:
            New value after increment.
        """
        current = self.get(category, stat_name, 0)
        new_value = current + amount
        self.set(category, stat_name, new_value)
        return new_value

    def add(self, category: str, stat_name: str, value: float) -> float:
        """Add to a statistic (same as increment but clearer for floats).

        Args:
            category: Category name
            stat_name: Name of the statistic
            value: Value to add

        Returns:
            New value after addition.
        """
        current = self.get(category, stat_name, 0)
        new_value = current + value
        self.set(category, stat_name, new_value)
        return new_value

    def max_stat(self, category: str, stat_name: str, value: Any) -> Any:
        """Update a statistic only if new value is greater.

        Args:
            category: Category name
            stat_name: Name of the statistic
            value: Potential new value

        Returns:
            The (potentially updated) value.
        """
        current = self.get(category, stat_name, 0)
        if value > current:
            self.set(category, stat_name, value)
            return value
        return current

    def get_all(self, category: Optional[str] = None) -> dict:
        """Get all stats, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            Dictionary of stats.
        """
        if category:
            return deepcopy(self.stats.get(category, {}))
        return deepcopy(self.stats)

    def best_clear(self, game, difficulty):
        ticks = self.get(game, f"best_clear_ticks_{difficulty.name.lower()}")
        return ticks if type(ticks) is int and ticks > 0 else None

    def record_clear(self, game, difficulty, ticks):
        best = self.best_clear(game, difficulty)
        if is_demo() or ticks <= 0 or (best is not None and ticks >= best):
            return False
        self.set(game, f"best_clear_ticks_{difficulty.name.lower()}", ticks)
        return True

    @staticmethod
    def format_clear(ticks):
        from engine import FPS

        if not ticks:
            return "—"
        seconds, remainder = divmod(ticks, FPS)
        return f"{seconds // 60}:{seconds % 60:02d}.{remainder * 100 // FPS:02d}"

    def format_play_time(self, seconds: float) -> str:
        """Format play time in human-readable format.

        Args:
            seconds: Total seconds

        Returns:
            Formatted string like "2h 15m" or "45m 30s"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# Singleton instance
_stats_manager: Optional[StatsManager] = None


def get_stats_manager() -> StatsManager:
    """Get the global StatsManager instance."""
    global _stats_manager
    if _stats_manager is None:
        _stats_manager = StatsManager()
    return _stats_manager
