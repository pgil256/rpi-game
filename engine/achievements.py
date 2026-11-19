"""
Achievement system for the Winston Entertainment System.

Tracks and stores player achievements across all games.
Achievements are unlocked based on gameplay events and persist to JSON.

Usage:
    from engine.achievements import get_achievement_manager, Achievement

    # Get the singleton manager
    achievements = get_achievement_manager()

    # Check and unlock achievements
    if score >= 50:
        achievements.unlock('snake_50')

    # Get achievement info
    info = achievements.get_achievement('snake_50')
    print(f"{info['name']}: {info['desc']}")

    # Check if unlocked
    if achievements.is_unlocked('snake_50'):
        print("Achievement unlocked!")
"""

from engine.persistence import JsonStore, data_path, is_demo
from datetime import datetime
from typing import Optional


# Achievement definitions - id: {name, desc, game, hidden}
ACHIEVEMENTS = {
    # Global achievements
    "first_win": {
        "name": "First Victory",
        "desc": "Win any game for the first time",
        "game": "global",
        "hidden": False,
    },
    "play_all": {
        "name": "Game Sampler",
        "desc": "Play all 6 games at least once",
        "game": "global",
        "hidden": False,
    },
    "dedicated": {
        "name": "Dedicated Player",
        "desc": "Play for a total of 1 hour",
        "game": "global",
        "hidden": False,
    },
    # Snake achievements
    "snake_first": {
        "name": "Slithery Start",
        "desc": "Complete your first Snake game",
        "game": "snake",
        "hidden": False,
    },
    "snake_50": {
        "name": "Hungry Weasel",
        "desc": "Score 50 points in Snake",
        "game": "snake",
        "hidden": False,
    },
    "snake_100": {
        "name": "Super Serpent",
        "desc": "Score 100 points in Snake",
        "game": "snake",
        "hidden": False,
    },
    "snake_hard_win": {
        "name": "Wall Dodger",
        "desc": "Score 30+ in Snake on Hard difficulty",
        "game": "snake",
        "hidden": False,
    },
    # Tunnel Treats achievements
    "pacman_first": {
        "name": "Pellet Muncher",
        "desc": "Complete your first Tunnel Treats level",
        "game": "pacman",
        "hidden": False,
    },
    "pacman_ghost": {
        "name": "Ghost Buster",
        "desc": "Eat 4 ghosts in a single power pellet",
        "game": "pacman",
        "hidden": False,
    },
    "pacman_1000": {
        "name": "High Scorer",
        "desc": "Score 1000 points in Tunnel Treats",
        "game": "pacman",
        "hidden": False,
    },
    "pacman_no_death": {
        "name": "Untouchable",
        "desc": "Clear a Tunnel Treats level without dying",
        "game": "pacman",
        "hidden": False,
    },
    # Ferret Crossing achievements
    "frogger_first": {
        "name": "Safe Crossing",
        "desc": "Successfully cross the road in Ferret Crossing",
        "game": "frogger",
        "hidden": False,
    },
    "frogger_5": {
        "name": "Leap Master",
        "desc": "Complete 5 crossings in Ferret Crossing",
        "game": "frogger",
        "hidden": False,
    },
    "frogger_hard": {
        "name": "Speed Demon",
        "desc": "Complete a crossing on Hard difficulty",
        "game": "frogger",
        "hidden": False,
    },
    # Burrow Defender achievements
    "centipede_first": {
        "name": "Bug Zapper",
        "desc": "Destroy your first centipede",
        "game": "centipede",
        "hidden": False,
    },
    "centipede_500": {
        "name": "Exterminator",
        "desc": "Score 500 points in Burrow Defender",
        "game": "centipede",
        "hidden": False,
    },
    "centipede_spider": {
        "name": "Arachnophobe",
        "desc": "Destroy a spider in Burrow Defender",
        "game": "centipede",
        "hidden": False,
    },
    # Crystal Quest achievements
    "digdug_first": {
        "name": "Tunnel Digger",
        "desc": "Collect your first crystal in Crystal Quest",
        "game": "digdug",
        "hidden": False,
    },
    "digdug_win": {
        "name": "Crystal Collector",
        "desc": "Collect all crystals in Crystal Quest",
        "game": "digdug",
        "hidden": False,
    },
    "digdug_hard": {
        "name": "Brave Explorer",
        "desc": "Win Crystal Quest on Hard difficulty",
        "game": "digdug",
        "hidden": False,
    },
    # Rocky Burrow achievements
    "boulder_first": {
        "name": "Diamond Hunter",
        "desc": "Collect your first diamond in Rocky Burrow",
        "game": "boulderdash",
        "hidden": False,
    },
    "boulder_level": {
        "name": "Cave Explorer",
        "desc": "Complete a Rocky Burrow level",
        "game": "boulderdash",
        "hidden": False,
    },
    "boulder_all": {
        "name": "Treasure Master",
        "desc": "Complete all 5 Rocky Burrow levels",
        "game": "boulderdash",
        "hidden": False,
    },
    "boulder_no_crush": {
        "name": "Quick Reflexes",
        "desc": "Complete a Rocky Burrow level without getting crushed",
        "game": "boulderdash",
        "hidden": True,  # Hidden achievement
    },
}


class AchievementManager:
    """Manages achievement tracking and persistence."""

    def __init__(self, save_file: str = "achievements.json"):
        """Initialize the achievement manager.

        Args:
            save_file: Name of the JSON file to store achievements.
        """
        self.save_path = data_path(save_file)
        self._store = JsonStore(self.save_path, legacy_name=save_file)
        self.unlocked = self._load()
        self._dirty = False
        self.pending_notifications = []  # Achievements to show

    def _load(self) -> dict:
        data = self._store.load().get("unlocked", {})
        if not isinstance(data, dict):
            return {}
        return {
            key: value
            for key, value in data.items()
            if key in ACHIEVEMENTS and isinstance(value, dict)
        }

    def save(self):
        saved = self._store.save({"unlocked": self.unlocked})
        if saved:
            self._dirty = False
        return saved

    def unlock(self, achievement_id: str) -> bool:
        """Unlock an achievement.

        Args:
            achievement_id: The ID of the achievement to unlock.

        Returns:
            True if newly unlocked, False if already unlocked or invalid.
        """
        if is_demo() or achievement_id not in ACHIEVEMENTS:
            return False

        if achievement_id in self.unlocked:
            if self._dirty:
                self.save()
            return False  # Already unlocked

        # Unlock the achievement
        self.unlocked[achievement_id] = {
            "timestamp": datetime.now().isoformat(),
        }
        self._dirty = True
        self.save()

        # Queue notification
        achievement = ACHIEVEMENTS[achievement_id]
        self.pending_notifications.append(
            {
                "id": achievement_id,
                "name": achievement["name"],
                "desc": achievement["desc"],
            }
        )

        return True

    def is_unlocked(self, achievement_id: str) -> bool:
        """Check if an achievement is unlocked."""
        return achievement_id in self.unlocked

    def get_achievement(self, achievement_id: str) -> Optional[dict]:
        """Get achievement info by ID."""
        if achievement_id not in ACHIEVEMENTS:
            return None

        info = ACHIEVEMENTS[achievement_id].copy()
        info["id"] = achievement_id
        info["unlocked"] = achievement_id in self.unlocked
        if info["unlocked"]:
            info["unlock_time"] = self.unlocked[achievement_id].get("timestamp")
        return info

    def get_all_achievements(self, game: Optional[str] = None) -> list:
        """Get all achievements, optionally filtered by game.

        Args:
            game: Filter by game name, or None for all.

        Returns:
            List of achievement info dicts.
        """
        result = []
        for aid, adata in ACHIEVEMENTS.items():
            if game is not None and adata["game"] != game:
                continue

            # Don't show hidden achievements that aren't unlocked
            if adata.get("hidden", False) and aid not in self.unlocked:
                continue

            info = adata.copy()
            info["id"] = aid
            info["unlocked"] = aid in self.unlocked
            if info["unlocked"]:
                info["unlock_time"] = self.unlocked[aid].get("timestamp")
            result.append(info)

        return result

    def get_progress(self, game: Optional[str] = None) -> tuple:
        """Get achievement progress as (unlocked, total).

        Args:
            game: Filter by game name, or None for all.

        Returns:
            Tuple of (unlocked_count, total_count).
        """
        total = 0
        unlocked = 0
        for aid, adata in ACHIEVEMENTS.items():
            if game is not None and adata["game"] != game:
                continue
            if adata.get("hidden", False) and aid not in self.unlocked:
                continue
            total += 1
            if aid in self.unlocked:
                unlocked += 1
        return (unlocked, total)

    def pop_notification(self) -> Optional[dict]:
        """Get and remove the next pending achievement notification.

        Returns:
            Achievement info dict or None if no pending notifications.
        """
        if self.pending_notifications:
            return self.pending_notifications.pop(0)
        return None

    def has_notification(self) -> bool:
        """Check if there are pending notifications."""
        return len(self.pending_notifications) > 0

    def check_global_achievements(self, stats_manager=None) -> None:
        """Check and unlock global achievements based on current stats.

        Call this periodically (e.g., when returning to menu) to check:
        - first_win: Any game completed
        - play_all: All 6 games played at least once
        - dedicated: Total play time >= 1 hour

        Args:
            stats_manager: StatsManager instance (or None to import and get it)
        """
        if stats_manager is None:
            from engine.stats_manager import get_stats_manager

            stats_manager = get_stats_manager()

        # Check first_win - any game completed
        if not self.is_unlocked("first_win"):
            games_completed = stats_manager.get("global", "games_completed", 0)
            if games_completed > 0:
                self.unlock("first_win")

        # Check play_all - all 6 games played
        if not self.is_unlocked("play_all"):
            game_keys = ["snake", "pacman", "frogger", "centipede", "digdug", "boulderdash"]
            all_played = True
            for game in game_keys:
                games_played = stats_manager.get(game, "games_played", 0)
                if games_played == 0:
                    all_played = False
                    break
            if all_played:
                self.unlock("play_all")

        # Check dedicated - 1 hour total play time (3600 seconds)
        if not self.is_unlocked("dedicated"):
            total_time = stats_manager.get("global", "total_play_time", 0)
            if total_time >= 3600:
                self.unlock("dedicated")


# Singleton instance
_achievement_manager: Optional[AchievementManager] = None


def get_achievement_manager() -> AchievementManager:
    """Get the global AchievementManager instance."""
    global _achievement_manager
    if _achievement_manager is None:
        _achievement_manager = AchievementManager()
    return _achievement_manager
