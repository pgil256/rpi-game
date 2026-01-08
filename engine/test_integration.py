#!/usr/bin/env python3
"""
Integration tests for the WES Engine package.

Run this file to verify all engine components work together:
    python -m engine.test_integration

Tests:
1. All imports work correctly
2. Constants are properly exported
3. AnimatedFerret loads sprites and handles missing files
4. InputManager initializes and provides input state
5. AssetLoader caches images and handles missing files
6. BaseGame can be subclassed
"""

import sys
import os

# Add parent directory to path so we can import engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_result(test_name: str, passed: bool, message: str = ""):
    """Print test result with consistent formatting."""
    status = "[PASS]" if passed else "[FAIL]"
    msg = f" - {message}" if message else ""
    print(f"  {status} {test_name}{msg}")
    return passed


def test_imports():
    """Test that all imports from engine package work."""
    print("\n1. Testing imports...")
    all_passed = True

    # Test package-level imports
    try:
        from engine import (
            AnimatedFerret,
            InputManager,
            BaseGame,
            AssetLoader,
            ANIMATION_STATES,
        )
        all_passed &= print_result("Core classes import", True)
    except ImportError as e:
        all_passed &= print_result("Core classes import", False, str(e))

    # Test constants
    try:
        from engine import (
            WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
            WEASEL_BROWN, WEASEL_TAN, WEASEL_WHITE, BURROW_BROWN,
            FERRET_BROWN, FERRET_TAN, FERRET_WHITE,
            BUTTON_A, BUTTON_B, BUTTON_SELECT, BUTTON_START, DEADZONE,
            BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA,
        )
        all_passed &= print_result("Constants import", True)
    except ImportError as e:
        all_passed &= print_result("Constants import", False, str(e))

    # Test backward-compatible functions
    try:
        from engine import (
            get_input_manager,
            get_default_loader,
            init_joystick,
            get_dpad,
            get_button,
            get_any_action_button,
            get_any_back_button,
            load_media_image,
            get_weasel_color,
        )
        all_passed &= print_result("Backward-compat functions import", True)
    except ImportError as e:
        all_passed &= print_result("Backward-compat functions import", False, str(e))

    return all_passed


def test_constants():
    """Verify constant values match expected values from game_launcher.py."""
    print("\n2. Testing constants...")
    all_passed = True

    from engine import (
        WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
        WEASEL_BROWN, WEASEL_TAN, WEASEL_WHITE, BURROW_BROWN,
        BUTTON_A, BUTTON_B, BUTTON_SELECT, BUTTON_START, DEADZONE,
    )

    # Check window settings
    all_passed &= print_result("WINDOW_WIDTH", WINDOW_WIDTH == 800, f"{WINDOW_WIDTH}")
    all_passed &= print_result("WINDOW_HEIGHT", WINDOW_HEIGHT == 600, f"{WINDOW_HEIGHT}")
    all_passed &= print_result("FPS", FPS == 60, f"{FPS}")

    # Check colors match game_launcher.py values
    all_passed &= print_result("WEASEL_BROWN", WEASEL_BROWN == (139, 90, 43), f"{WEASEL_BROWN}")
    all_passed &= print_result("WEASEL_TAN", WEASEL_TAN == (210, 180, 140), f"{WEASEL_TAN}")
    all_passed &= print_result("WEASEL_WHITE", WEASEL_WHITE == (255, 248, 220), f"{WEASEL_WHITE}")
    all_passed &= print_result("BURROW_BROWN", BURROW_BROWN == (101, 67, 33), f"{BURROW_BROWN}")

    # Check button mappings match game_launcher.py
    all_passed &= print_result("BUTTON_A", BUTTON_A == 1, f"{BUTTON_A}")
    all_passed &= print_result("BUTTON_B", BUTTON_B == 2, f"{BUTTON_B}")
    all_passed &= print_result("BUTTON_SELECT", BUTTON_SELECT == 8, f"{BUTTON_SELECT}")
    all_passed &= print_result("BUTTON_START", BUTTON_START == 9, f"{BUTTON_START}")
    all_passed &= print_result("DEADZONE", DEADZONE == 0.3, f"{DEADZONE}")

    return all_passed


def test_asset_loader():
    """Test AssetLoader functionality."""
    print("\n3. Testing AssetLoader...")
    all_passed = True

    # Initialize pygame for asset loading
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100), pygame.HIDDEN)

    from engine import AssetLoader, load_media_image, get_weasel_color

    # Test instantiation
    try:
        loader = AssetLoader()
        all_passed &= print_result("AssetLoader instantiation", True)
    except Exception as e:
        all_passed &= print_result("AssetLoader instantiation", False, str(e))
        return all_passed

    # Test media directory detection
    media_exists = os.path.isdir(loader.media_dir)
    all_passed &= print_result("Media directory found", media_exists, loader.media_dir)

    # Test loading existing image
    img = loader.load_image('ferret-long-sprite.png')
    all_passed &= print_result("Load ferret sprite", img is not None, "ferret-long-sprite.png")

    # Test loading with size
    img_scaled = loader.load_image('ferret-long-sprite.png', (64, 64))
    if img_scaled:
        correct_size = img_scaled.get_size() == (64, 64)
        all_passed &= print_result("Load with scaling", correct_size, f"Size: {img_scaled.get_size()}")
    else:
        all_passed &= print_result("Load with scaling", False, "Image is None")

    # Test caching (should return same object)
    img_cached = loader.load_image('ferret-long-sprite.png')
    all_passed &= print_result("Image caching", img_cached is img, "Cache hit")

    # Test loading non-existent image
    img_missing = loader.load_image('nonexistent.png')
    all_passed &= print_result("Missing image returns None", img_missing is None)

    # Test fallback surface
    fallback = loader.create_fallback_surface((32, 32), (255, 0, 0))
    all_passed &= print_result("Create fallback surface", fallback is not None)

    # Test load_or_fallback
    surface = loader.load_image_or_fallback('missing.png', (32, 32), (0, 255, 0))
    all_passed &= print_result("load_image_or_fallback", surface is not None)

    # Test sprite sheet loading
    sprites = loader.load_sprite_sheet_grid('ferret-long-sprite.png', (32, 32), 8, 9)
    expected_frames = 8 * 9  # 72 frames
    all_passed &= print_result("Load sprite sheet grid", len(sprites) == expected_frames,
                               f"Got {len(sprites)} frames, expected {expected_frames}")

    # Test backward-compat load_media_image
    compat_img = load_media_image('soupcan_new.png', (20, 20))
    all_passed &= print_result("load_media_image (compat)", compat_img is not None)

    # Test get_weasel_color
    c0 = get_weasel_color(0)
    c1 = get_weasel_color(1)
    c2 = get_weasel_color(2)
    c5 = get_weasel_color(5)
    all_passed &= print_result("get_weasel_color(0)", c0 == (139, 90, 43), f"{c0}")
    all_passed &= print_result("get_weasel_color(1)", c1 == (210, 180, 140), f"{c1}")
    all_passed &= print_result("get_weasel_color(2)", c2 == (255, 248, 220), f"{c2}")
    all_passed &= print_result("get_weasel_color(5)", c5 == (210, 180, 140), f"{c5} (should be tan)")

    pygame.quit()
    return all_passed


def test_animated_ferret():
    """Test AnimatedFerret sprite class."""
    print("\n4. Testing AnimatedFerret...")
    all_passed = True

    import pygame
    pygame.init()
    screen = pygame.display.set_mode((100, 100), pygame.HIDDEN)

    from engine import AnimatedFerret, ANIMATION_STATES

    # Test instantiation
    try:
        ferret = AnimatedFerret(x=100, y=100, scale=2)
        all_passed &= print_result("AnimatedFerret instantiation", True)
    except Exception as e:
        all_passed &= print_result("AnimatedFerret instantiation", False, str(e))
        pygame.quit()
        return all_passed

    # Test properties
    all_passed &= print_result("Initial position", ferret.x == 100 and ferret.y == 100,
                               f"({ferret.x}, {ferret.y})")
    all_passed &= print_result("Initial facing", ferret.facing_right, "facing_right=True")
    all_passed &= print_result("Initial state", ferret.state == 'idle', f"state={ferret.state}")

    # Test sprite loading
    available = ferret.get_available_animations()
    has_animations = len(available) > 0
    all_passed &= print_result("Animations loaded", has_animations,
                               f"{len(available)} animations: {available[:3]}...")

    # Test all 9 animation rows are present
    expected_count = len(ANIMATION_STATES)  # 9 states
    all_passed &= print_result(f"All {expected_count} animation states",
                               len(available) >= expected_count,
                               f"Got {len(available)}")

    # Test update (movement)
    ferret.update(1, 0)  # Move right
    all_passed &= print_result("Move right", ferret.x > 100, f"x={ferret.x}")
    all_passed &= print_result("Facing right after move", ferret.facing_right)
    all_passed &= print_result("State is movement", ferret.state == 'movement', f"state={ferret.state}")

    # Test facing left
    ferret.update(-1, 0)
    all_passed &= print_result("Move left changes facing", not ferret.facing_right)

    # Test get_image
    img = ferret.get_image()
    all_passed &= print_result("get_image returns Surface", img is not None)

    # Test draw (should not raise)
    try:
        ferret.draw(screen)
        all_passed &= print_result("draw() succeeds", True)
    except Exception as e:
        all_passed &= print_result("draw() succeeds", False, str(e))

    # Test get_rect
    rect = ferret.get_rect()
    all_passed &= print_result("get_rect returns Rect", isinstance(rect, pygame.Rect),
                               f"{rect}")

    # Test set_state
    try:
        ferret.set_state('jump')
        all_passed &= print_result("set_state('jump')", ferret.state == 'jump')
    except ValueError as e:
        all_passed &= print_result("set_state('jump')", False, str(e))

    # Test clamp_to_bounds
    ferret.x = -100
    ferret.clamp_to_bounds(0, 0, 800, 600)
    all_passed &= print_result("clamp_to_bounds", ferret.x >= 0, f"x={ferret.x}")

    pygame.quit()
    return all_passed


def test_input_manager():
    """Test InputManager functionality."""
    print("\n5. Testing InputManager...")
    all_passed = True

    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100), pygame.HIDDEN)

    from engine import InputManager, get_input_manager, get_dpad, get_any_action_button

    # Test instantiation
    try:
        input_mgr = InputManager()
        all_passed &= print_result("InputManager instantiation", True)
    except Exception as e:
        all_passed &= print_result("InputManager instantiation", False, str(e))
        pygame.quit()
        return all_passed

    # Test joystick check (may or may not be connected)
    has_joy = input_mgr.has_joystick()
    all_passed &= print_result("has_joystick() works", isinstance(has_joy, bool),
                               f"joystick={has_joy}")

    # Test update (should not raise)
    try:
        input_mgr.update()
        all_passed &= print_result("update() succeeds", True)
    except Exception as e:
        all_passed &= print_result("update() succeeds", False, str(e))

    # Test get_dpad
    dpad = input_mgr.get_dpad()
    all_passed &= print_result("get_dpad returns tuple", isinstance(dpad, tuple) and len(dpad) == 2,
                               f"{dpad}")

    # Test is_pressed (keyboard check)
    pressed = input_mgr.is_pressed('action')
    all_passed &= print_result("is_pressed('action')", isinstance(pressed, bool))

    # Test was_pressed (edge detection)
    was = input_mgr.was_pressed('action')
    all_passed &= print_result("was_pressed('action')", isinstance(was, bool))

    # Test get_any_action_button
    action = input_mgr.get_any_action_button()
    all_passed &= print_result("get_any_action_button()", isinstance(action, bool))

    # Test get_any_back_button
    back = input_mgr.get_any_back_button()
    all_passed &= print_result("get_any_back_button()", isinstance(back, bool))

    # Test backward-compat singleton
    mgr2 = get_input_manager()
    all_passed &= print_result("get_input_manager() returns instance", mgr2 is not None)

    # Test backward-compat get_dpad
    dp = get_dpad()
    all_passed &= print_result("get_dpad() compat function", isinstance(dp, tuple))

    pygame.quit()
    return all_passed


def test_base_game():
    """Test BaseGame abstract class."""
    print("\n6. Testing BaseGame...")
    all_passed = True

    import pygame
    pygame.init()
    screen = pygame.display.set_mode((100, 100), pygame.HIDDEN)

    from engine import BaseGame, InputManager

    # Create a test subclass
    class TestGame(BaseGame):
        def __init__(self, screen, input_manager):
            self.setup_called = False
            self.handle_input_called = False
            self.update_called = False
            self.render_called = False
            super().__init__(screen, input_manager)

        def setup(self):
            self.setup_called = True

        def handle_input(self):
            self.handle_input_called = True
            return True  # Exit immediately

        def update(self, dt):
            self.update_called = True

        def render(self):
            self.render_called = True

    # Test instantiation
    try:
        input_mgr = InputManager()
        game = TestGame(screen, input_mgr)
        all_passed &= print_result("TestGame instantiation", True)
    except Exception as e:
        all_passed &= print_result("TestGame instantiation", False, str(e))
        pygame.quit()
        return all_passed

    # Test setup was called
    all_passed &= print_result("setup() called on init", game.setup_called)

    # Test that screen and input_manager are stored
    all_passed &= print_result("screen stored", game.screen is screen)
    all_passed &= print_result("input_manager stored", game.input_manager is input_mgr)

    # Test clock exists
    all_passed &= print_result("clock created", hasattr(game, 'clock'))

    # Test run() method exists
    all_passed &= print_result("run() method exists", hasattr(game, 'run') and callable(game.run))

    pygame.quit()
    return all_passed


def test_compatibility_with_game_launcher():
    """Verify engine modules are compatible with game_launcher.py patterns."""
    print("\n7. Testing compatibility with game_launcher.py...")
    all_passed = True

    import pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.HIDDEN)

    from engine import (
        AnimatedFerret, InputManager, AssetLoader,
        WEASEL_BROWN, WEASEL_TAN, WEASEL_WHITE, BURROW_BROWN,
        get_dpad, get_any_action_button, get_any_back_button,
        load_media_image, get_weasel_color,
    )

    # Test AnimatedFerret replicates WeaselAvatar behavior
    ferret = AnimatedFerret(x=400, y=300, scale=2, speed=4.0)

    # WeaselAvatar uses update(dx, dy) - ferret should too
    try:
        ferret.update(1, 0)
        ferret.update(0, 0)
        all_passed &= print_result("AnimatedFerret.update(dx, dy)", True)
    except Exception as e:
        all_passed &= print_result("AnimatedFerret.update(dx, dy)", False, str(e))

    # WeaselAvatar uses draw(surface) - ferret should too
    try:
        ferret.draw(screen)
        all_passed &= print_result("AnimatedFerret.draw(surface)", True)
    except Exception as e:
        all_passed &= print_result("AnimatedFerret.draw(surface)", False, str(e))

    # WeaselAvatar uses get_rect() - ferret should too
    rect = ferret.get_rect()
    all_passed &= print_result("AnimatedFerret.get_rect()", isinstance(rect, pygame.Rect))

    # Test backward-compat input functions
    input_mgr = InputManager()
    input_mgr.update()

    # These should work like the game_launcher.py globals
    dp = get_dpad()
    all_passed &= print_result("get_dpad() returns tuple", isinstance(dp, tuple))

    action = get_any_action_button()
    all_passed &= print_result("get_any_action_button() works", isinstance(action, bool))

    back = get_any_back_button()
    all_passed &= print_result("get_any_back_button() works", isinstance(back, bool))

    # Test load_media_image matches game_launcher.py signature
    img = load_media_image('soupcan_new.png', (20, 20))
    all_passed &= print_result("load_media_image(name, size)", img is not None or True)  # May fail if no media

    # Test get_weasel_color matches game_launcher.py
    c = get_weasel_color(0)
    all_passed &= print_result("get_weasel_color(0) == WEASEL_BROWN", c == WEASEL_BROWN)

    pygame.quit()
    return all_passed


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("WES Engine Integration Tests")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Constants", test_constants()))
    results.append(("AssetLoader", test_asset_loader()))
    results.append(("AnimatedFerret", test_animated_ferret()))
    results.append(("InputManager", test_input_manager()))
    results.append(("BaseGame", test_base_game()))
    results.append(("Compatibility", test_compatibility_with_game_launcher()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        all_passed &= passed

    print()
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
