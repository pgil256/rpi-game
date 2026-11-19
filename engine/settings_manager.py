"""Validated user preferences, saved atomically in the user data directory."""

import math
from engine.persistence import JsonStore, data_path, is_demo


class SettingsManager:
    DEFAULT_FILE = "settings.json"
    DEFAULTS = {
        "audio_volume": 100,
        "music_volume": 35,
        "effects_volume": 85,
        "muted": False,
        "fullscreen": False,
        "display_index": 0,
        "screen_fit": "aspect",
    }

    def __init__(self, filepath=None):
        self._filepath = str(data_path(self.DEFAULT_FILE) if filepath is None else filepath)
        self._store = JsonStore(
            self._filepath, legacy_name=self.DEFAULT_FILE if filepath is None else None
        )
        self._settings = self.DEFAULTS.copy()
        self._settings.update(self._validated(self._store.load()))

    def _validated(self, values):
        result = {}
        for key, value in values.items():
            if key in ("muted", "fullscreen"):
                if isinstance(value, bool):
                    result[key] = value
            elif key in ("audio_volume", "music_volume", "effects_volume"):
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                ):
                    result[key] = max(0, min(100, int(value)))
            elif key == "display_index":
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    result[key] = value
            elif key == "screen_fit":
                if value in ("aspect", "fill"):
                    result[key] = value
            else:
                result[key] = value
        return result

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value, *, persist=True):
        self.update({key: value}, persist=persist)

    def update(self, values, *, persist=True):
        if is_demo():
            return
        validated = self._validated(values)
        if any(self._settings.get(k) != v for k, v in validated.items()):
            self._settings.update(validated)
            if persist:
                self.save()

    def get_all(self):
        return self._settings.copy()

    def reset_to_defaults(self):
        if not is_demo():
            self._settings = self.DEFAULTS.copy()
            self.save()

    def save(self):
        return self._store.save(self._settings)

    _save = save


_settings_manager = None


def get_settings_manager():
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
