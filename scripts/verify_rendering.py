"""Reproducible headless screenshots and warm-render allocation/timing report.

Run from the project root: python scripts/verify_rendering.py
Writes only docs/verification/2026-11-14 and an isolated temporary data folder.
Surface counts cover explicit pygame.Surface constructors, as in the audit.
"""

import json
import os
from pathlib import Path
import random
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


def main():
    with tempfile.TemporaryDirectory(prefix="wes-render-") as temporary:
        os.environ["WES_DATA_DIR"] = temporary
        import pygame
        import engine
        import game_launcher as launcher
        from engine.persistence import persistence_session

        output = ROOT / "docs" / "verification" / "2026-11-14"
        output.mkdir(parents=True, exist_ok=True)
        screen = launcher.initialize(False)
        engine.set_scale_callback(None)
        report = {}
        random.seed(20261114)
        with persistence_session(demo=True):
            for index, cls in enumerate(launcher.GAME_CLASSES):
                controls = launcher.ScriptedInput()
                game = cls(screen, controls, engine.Difficulty.NORMAL)
                for frame in range(180):
                    controls.feed(*launcher.demo_input(index, frame))
                    game.handle_input()
                    game.update(1 / 60)
                    game.render()
                pygame.image.save(screen, output / f"{launcher.GAMES[index]['key']}.png")
                original = pygame.Surface
                allocations = []
                durations = []
                count = 0

                def surface(*args, **kwargs):
                    nonlocal count
                    count += 1
                    return original(*args, **kwargs)

                try:
                    pygame.Surface = surface
                    for _ in range(120):
                        count = 0
                        start = time.perf_counter()
                        game.render()
                        durations.append((time.perf_counter() - start) * 1000)
                        allocations.append(count)
                finally:
                    pygame.Surface = original
                report[launcher.GAMES[index]["name"]] = {
                    "explicit_surfaces_per_render": statistics.mean(allocations),
                    "median_render_ms": round(statistics.median(durations), 3),
                }

        class Captured(Exception):
            pass

        launcher.input_manager.get_dpad = lambda: (0, 0)
        launcher.input_manager.menu_direction = lambda: (0, 0)
        launcher.input_manager.confirm_pressed = lambda: False
        launcher.input_manager.back_pressed = lambda: False
        launcher.input_manager.was_pressed = lambda _: False
        launcher.poll_events = lambda: []
        screens = {
            "menu": launcher.run_menu,
            "settings": launcher.run_settings_menu,
            "achievements": launcher.run_achievements_viewer,
            "statistics": launcher.run_stats_viewer,
            "controller": launcher.test_controller,
        }
        for name, callback in screens.items():
            frames = 0
            menu_allocations = []

            def capture():
                nonlocal frames, count
                if name == "menu":
                    if frames:
                        menu_allocations.append(count)
                    else:
                        pygame.Surface = surface
                    count = 0
                    frames += 1
                    if frames <= 120:
                        return
                    report["Main menu"] = {
                        "explicit_surfaces_per_render": statistics.mean(menu_allocations),
                    }
                pygame.image.save(screen, output / f"{name}.png")
                raise Captured()

            engine.set_scale_callback(capture)
            try:
                callback(screen)
            except Captured:
                pass
            finally:
                pygame.Surface = original
        (output / "render-metrics.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        launcher.cleanup()


if __name__ == "__main__":
    main()
