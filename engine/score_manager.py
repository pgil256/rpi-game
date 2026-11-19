"""Difficulty-specific records with migration of legacy scores to Normal."""

from engine.persistence import JsonStore, data_path, difficulty_key, is_demo


class ScoreManager:
    DEFAULT_FILE = "high_scores.json"

    def __init__(self, filepath=None):
        self._filepath = str(data_path(self.DEFAULT_FILE) if filepath is None else filepath)
        self._store = JsonStore(
            self._filepath, legacy_name=self.DEFAULT_FILE if filepath is None else None
        )
        self._scores = {}
        for game, value in self._store.load().items():
            entries = value if isinstance(value, dict) else {"normal": value}
            scores = {}
            for difficulty, score in entries.items():
                try:
                    if not isinstance(score, bool):
                        scores[str(difficulty).lower()] = max(0, int(score))
                except (ValueError, TypeError, OverflowError):
                    continue
            self._scores[str(game).lower()] = scores

    def get_high_score(self, game_name, difficulty=None):
        return self._scores.get(game_name.lower(), {}).get(difficulty_key(difficulty), 0)

    def set_high_score(self, game_name, score, difficulty=None):
        if is_demo():
            return False
        try:
            score = int(score)
        except (ValueError, TypeError, OverflowError):
            return False
        key = difficulty_key(difficulty)
        game = game_name.lower()
        if score > self.get_high_score(game, key):
            self._scores.setdefault(game, {})[key] = score
            self.save()
            return True
        return False

    def get_all_scores(self, difficulty=None):
        return {
            game: scores.get(difficulty_key(difficulty), 0) for game, scores in self._scores.items()
        }

    def reset_score(self, game_name, difficulty=None):
        if not is_demo():
            self._scores.get(game_name.lower(), {}).pop(difficulty_key(difficulty), None)
            self.save()

    def reset_all_scores(self):
        if not is_demo():
            self._scores.clear()
            self.save()

    def save(self):
        return self._store.save(self._scores)

    _save = save


_score_manager = None


def get_score_manager():
    global _score_manager
    if _score_manager is None:
        _score_manager = ScoreManager()
    return _score_manager
