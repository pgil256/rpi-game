"""
Score Manager - Persistent high score tracking for WES games.

Provides a centralized system for loading, saving, and updating high scores
across all games in the Weasel Entertainment System.
"""

import json
import os
from typing import Dict, Optional


class ScoreManager:
    """Manages high scores with JSON persistence.

    High scores are stored per-game in a JSON file. The manager handles
    loading on startup and saving when scores change.

    Usage:
        from engine import get_score_manager

        score_mgr = get_score_manager()
        high_score = score_mgr.get_high_score('snake')
        if current_score > high_score:
            score_mgr.set_high_score('snake', current_score)
    """

    DEFAULT_FILE = 'high_scores.json'

    def __init__(self, filepath: Optional[str] = None):
        """Initialize the score manager.

        Args:
            filepath: Path to the scores JSON file. If None, uses default
                     location in the project root directory.
        """
        if filepath is None:
            # Default to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(base_dir, self.DEFAULT_FILE)

        self._filepath = filepath
        self._scores: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Load high scores from the JSON file."""
        try:
            if os.path.exists(self._filepath):
                with open(self._filepath, 'r') as f:
                    data = json.load(f)
                    # Ensure all values are integers
                    self._scores = {k: int(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError, IOError):
            # If file is corrupted or unreadable, start fresh
            self._scores = {}

    def _save(self) -> None:
        """Save high scores to the JSON file."""
        try:
            with open(self._filepath, 'w') as f:
                json.dump(self._scores, f, indent=2)
        except IOError:
            # Silently fail if we can't write (e.g., read-only filesystem)
            pass

    def get_high_score(self, game_name: str) -> int:
        """Get the high score for a game.

        Args:
            game_name: The name of the game (e.g., 'snake', 'pacman').

        Returns:
            The high score, or 0 if no score has been recorded.
        """
        return self._scores.get(game_name.lower(), 0)

    def set_high_score(self, game_name: str, score: int) -> bool:
        """Set the high score for a game if it's higher than the current record.

        Args:
            game_name: The name of the game.
            score: The new score to record.

        Returns:
            True if this was a new high score, False otherwise.
        """
        game_key = game_name.lower()
        current = self._scores.get(game_key, 0)

        if score > current:
            self._scores[game_key] = score
            self._save()
            return True

        return False

    def get_all_scores(self) -> Dict[str, int]:
        """Get all recorded high scores.

        Returns:
            A dictionary mapping game names to their high scores.
        """
        return self._scores.copy()

    def reset_score(self, game_name: str) -> None:
        """Reset the high score for a specific game.

        Args:
            game_name: The name of the game.
        """
        game_key = game_name.lower()
        if game_key in self._scores:
            del self._scores[game_key]
            self._save()

    def reset_all_scores(self) -> None:
        """Reset all high scores."""
        self._scores = {}
        self._save()

    def save(self) -> None:
        """Explicitly save scores to disk.

        This is called automatically when setting scores, but can be called
        manually to ensure data is persisted (e.g., during shutdown).
        """
        self._save()


# Singleton instance
_score_manager: Optional[ScoreManager] = None


def get_score_manager() -> ScoreManager:
    """Get the global ScoreManager instance.

    Returns:
        The singleton ScoreManager instance.
    """
    global _score_manager
    if _score_manager is None:
        _score_manager = ScoreManager()
    return _score_manager
