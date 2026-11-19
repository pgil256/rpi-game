"""Exercise every game's normal input/update/render path without touching saves."""

import pytest
from engine import Difficulty, InputManager
from engine.persistence import data_dir, persistence_session
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

GAMES = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]


class DemoInput(InputManager):
    demo_mode = True

    def __init__(self):
        super().__init__()
        self.frame = 0

    def update(self):
        self._prev_buttons = self._curr_buttons.copy()
        self._prev_keys = self._curr_keys.copy()
        self._prev_dpad = self._curr_dpad
        self._curr_dpad = ((1, 0), (0, -1), (-1, 0), (0, 1))[(self.frame // 60) % 4]
        self._curr_buttons = {self.button_map["a"]: self.frame % 90 == 0}
        self._curr_keys = {}
        self.frame += 1


@pytest.mark.parametrize("cls", GAMES)
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_game_survives_300_frames(cls, difficulty, screen):
    with persistence_session(demo=True, difficulty=difficulty):
        game = cls(screen, DemoInput(), difficulty)
        for _ in range(300):
            assert game.handle_input() is False
            game.update(1 / 60)
            game.render()
        game._track_session_stats()
    assert not data_dir().exists()
