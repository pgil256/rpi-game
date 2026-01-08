"""
Settings Manager - Persistent settings for WES.

Manages user preferences like audio volume, mute state, and fullscreen mode.
Settings are stored in a JSON file and loaded on startup.
"""

import json
import os
from typing import Any, Dict, Optional


class SettingsManager:
    """Manages user settings with JSON persistence.

    Settings are stored in a JSON file and include:
    - audio_volume: 0-100 (default 100)
    - muted: bool (default False)
    - fullscreen: bool (default False)

    Usage:
        from engine import get_settings_manager

        settings = get_settings_manager()
        volume = settings.get('audio_volume', 100)
        settings.set('muted', True)
    """

    DEFAULT_FILE = 'settings.json'

    # Default settings values
    DEFAULTS = {
        'audio_volume': 100,
        'muted': False,
        'fullscreen': False,
    }

    def __init__(self, filepath: Optional[str] = None):
        """Initialize the settings manager.

        Args:
            filepath: Path to the settings JSON file. If None, uses default
                     location in the project root directory.
        """
        if filepath is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(base_dir, self.DEFAULT_FILE)

        self._filepath = filepath
        self._settings: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load settings from the JSON file."""
        # Start with defaults
        self._settings = self.DEFAULTS.copy()

        try:
            if os.path.exists(self._filepath):
                with open(self._filepath, 'r') as f:
                    data = json.load(f)
                    # Merge loaded settings over defaults
                    self._settings.update(data)
        except (json.JSONDecodeError, ValueError, IOError):
            # If file is corrupted or unreadable, use defaults
            pass

    def _save(self) -> None:
        """Save settings to the JSON file."""
        try:
            with open(self._filepath, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError:
            # Silently fail if we can't write
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: The setting key.
            default: Default value if key doesn't exist.

        Returns:
            The setting value, or default if not found.
        """
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value and save.

        Args:
            key: The setting key.
            value: The value to set.
        """
        self._settings[key] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings.

        Returns:
            A copy of all current settings.
        """
        return self._settings.copy()

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self._settings = self.DEFAULTS.copy()
        self._save()

    def save(self) -> None:
        """Explicitly save settings to disk."""
        self._save()


# Singleton instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global SettingsManager instance.

    Returns:
        The singleton SettingsManager instance.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
