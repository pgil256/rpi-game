"""Assert-based integration checks; run with python -m pytest engine/test_integration.py."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import pytest
from engine import AnimatedFerret, AssetLoader, InputManager


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("WES_DATA_DIR", str(tmp_path))
    pygame.init()
    pygame.display.set_mode((800, 600))
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 0)
    yield
    pygame.quit()


def test_sprite_assets_and_shared_cache():
    one, two = AnimatedFerret(scale=1), AnimatedFerret(scale=1)
    assert one.get_image() is two.get_image()
    assert len(one._animations["movement"]) == 8
    one.sprite_size = 24
    assert one.get_image().get_size() == (24, 24)
    assert one.get_rect().size == (24, 24)
    assert two.get_image().get_size() == (32, 32)


def test_asset_loader_cache_and_fallback():
    one, two = AssetLoader(), AssetLoader()
    assert one.load_image("soupbowl.png") is two.load_image("soupbowl.png")
    assert one.load_image("does-not-exist.png") is None
    assert one.load_image_or_fallback("missing.png", (32, 32), (255, 0, 0)).get_size() == (32, 32)


def test_input_defaults():
    manager = InputManager()
    manager.update()
    assert manager.get_dpad() == (0, 0)
    assert not manager.action_pressed()
    assert not manager.pause_pressed()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
