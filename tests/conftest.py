"""All runtime tests use dummy SDL devices and disposable user data."""

import importlib
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("WES_DATA_DIR", str(tmp_path / "user-data"))
    pygame.init()
    pygame.display.set_mode((800, 600))
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 0)
    for name in ("settings", "score", "stats", "achievement", "audio"):
        module_name = "achievements" if name == "achievement" else name + "_manager"
        module = importlib.import_module("engine." + module_name)
        monkeypatch.setattr(module, "_" + name + "_manager", None)
    yield
    if pygame.display.get_init():
        pygame.event.clear()
    pygame.quit()


@pytest.fixture
def screen():
    return pygame.display.get_surface()


@pytest.fixture
def simulate_game():
    """Scripted verification stays in tests; there is no in-game preview mode."""
    import game_launcher as launcher
    from engine.persistence import persistence_session

    def simulate(screen, game_index=0, max_frames=900):
        controls = launcher.ScriptedInput()
        with persistence_session(demo=True, difficulty=launcher.Difficulty.EASY):
            game = launcher.GAME_CLASSES[game_index](screen, controls, launcher.Difficulty.EASY)
            for frame in range(max_frames):
                events = launcher.poll_events(shortcuts=False)
                if launcher._quit_requested or any(
                    e.type
                    in (
                        pygame.KEYDOWN,
                        pygame.MOUSEBUTTONDOWN,
                        pygame.JOYBUTTONDOWN,
                        pygame.JOYHATMOTION,
                    )
                    for e in events
                ):
                    return launcher._quit_requested
                if (
                    launcher.input_manager.get_dpad() != (0, 0)
                    or launcher.input_manager.get_any_action_button()
                    or launcher.input_manager.get_any_back_button()
                ):
                    return launcher._quit_requested
                controls.feed(*launcher.demo_input(game_index, frame))
                if game.handle_input():
                    return False
                game.update(1 / launcher.FPS)
                game.render()
                launcher.engine.scale_to_screen()
        return launcher._quit_requested

    return simulate
