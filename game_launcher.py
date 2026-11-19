#!/usr/bin/env python3
"""Winston Entertainment System. Importing this module does not open devices."""

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import random
import tempfile

import pygame
import engine
from engine import (
    AnimatedFerret,
    InputManager,
    Difficulty,
    AudioManager,
    get_audio_manager,
    get_settings_manager,
    get_achievement_manager,
    get_stats_manager,
    get_score_manager,
    set_scale_callback,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    CUTE_BG_PRIMARY,
    CUTE_BUTTON_BG,
    CUTE_BUTTON_HOVER,
    CUTE_SHADOW,
    WEASEL_BROWN,
)
from engine.persistence import data_dir, data_path, persistence_session
from engine.profile_instance import ProfileInstance
from engine.controller_mapping import (
    DIRECTIONS,
    BUTTON_NAMES,
    button_conflict,
    detect_binding,
    is_neutral,
    valid_bindings,
    binding_pressed,
)
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

TITLE_COLOR = (180, 110, 40)
TITLE = "Winston Entertainment System"
GAME_CLASSES = (SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame)
GAMES = [
    {
        "key": "snake",
        "rules": [
            "Slow pace. Wrap around the edges.",
            "Wrap around the edges at standard speed.",
            "Faster turns. Touching a wall ends the run.",
        ],
        "name": "Snake",
        "description": "Grow your ferret family with tasty soup.",
        "color": (65, 130, 70),
    },
    {
        "key": "pacman",
        "rules": [
            "Slower critters. The first power bowls last 10 seconds.",
            "The first power bowls last 8 seconds.",
            "Faster critters. The first power bowls last 5 seconds.",
        ],
        "name": "Tunnel Treats",
        "description": "Collect treats and outsmart the wandering critters.",
        "color": (160, 115, 20),
    },
    {
        "key": "frogger",
        "rules": [
            "Traffic and logs move at 60% speed.",
            "Traffic and logs move at standard speed.",
            "Traffic and logs move at 150% speed.",
        ],
        "name": "Ferret Crossing",
        "description": "Hop safely across roads and rivers.",
        "color": (35, 115, 140),
    },
    {
        "key": "centipede",
        "rules": [
            "Start against 6 slow segments. Hold A / Space to fire.",
            "Start against 8 segments. Hold A / Space to fire.",
            "Start against 12 fast segments. Hold A / Space to fire.",
        ],
        "name": "Burrow Defender",
        "description": "Defend your burrow through waves of invaders.",
        "color": (135, 65, 145),
    },
    {
        "key": "digdug",
        "rules": [
            "One beetle patrols the first depth.",
            "Two beetles patrol the first depth.",
            "Four beetles patrol the first depth.",
        ],
        "name": "Crystal Quest",
        "description": "Dig tunnels and collect underground crystals.",
        "color": (170, 65, 60),
    },
    {
        "key": "boulderdash",
        "rules": [
            "Fewer loose rocks. Collect every diamond.",
            "Dig around loose rocks and collect every diamond.",
            "More rocks. Caves 2 and 4 require a sideways push.",
        ],
        "name": "Rocky Burrow",
        "description": "Gather diamonds and dodge falling rocks.",
        "color": (90, 95, 140),
    },
]
# These are intentionally initialized by initialize(), never at import time.
input_manager = None
audio_manager = None
settings_manager = None
_real_screen = None
_render_surface = None
_scaled_surface = None
_viewport = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
_fullscreen_mode = False
_display_index = 0
_screen_fit = "aspect"
_desktop_sizes = []
_next_display_check = 0
_display_notice = ""
_quit_requested = False
_log_handler = None
_profile_instance = None
log = logging.getLogger("wes")


def initialize(fullscreen=None, display_index=None):
    global _profile_instance
    if _profile_instance is not None:
        return _render_surface
    instance = ProfileInstance(data_dir())
    if not instance.acquire():
        instance.show_existing()
        return None
    _profile_instance = instance
    try:
        return _initialize_devices(fullscreen, display_index)
    except BaseException:
        try:
            _shutdown_devices(save=False)
        finally:
            instance.close()
            _profile_instance = None
        raise


def _initialize_devices(fullscreen, display_index):
    global \
        input_manager, \
        audio_manager, \
        settings_manager, \
        _render_surface, \
        _quit_requested, \
        _log_handler
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.init()
    _quit_requested = False
    log.setLevel(logging.INFO)
    if _log_handler is None:
        try:
            path = data_path("wes.log")
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        except OSError:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger().addHandler(handler)
        _log_handler = handler
    input_manager = InputManager()
    audio_manager = get_audio_manager()
    settings_manager = get_settings_manager()
    audio_manager.set_mute(settings_manager.get("muted", False))
    audio_manager.volume = settings_manager.get("audio_volume", 100) / 100.0
    audio_manager.music_volume = settings_manager.get("music_volume", 35) / 100.0
    audio_manager.effects_volume = settings_manager.get("effects_volume", 85) / 100.0
    _render_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    configure_display(
        settings_manager.get("fullscreen", False) if fullscreen is None else fullscreen,
        settings_manager.get("display_index", 0) if display_index is None else display_index,
        settings_manager.get("screen_fit", "aspect"),
    )
    set_scale_callback(_do_scale_to_screen)
    engine.set_global_event_callback(handle_display_event)
    return _render_surface


def connected_displays():
    """Use OS desktop sizes, including extended HDMI desktops, without mode guessing."""
    sizes = pygame.display.get_desktop_sizes()
    return list(sizes) if sizes else [(WINDOW_WIDTH, WINDOW_HEIGHT)]


def configure_display(fullscreen, display_index=None, screen_fit=None):
    """Change modes only on request; keep the game's logical surface stable."""
    global _real_screen, _fullscreen_mode, _display_index, _screen_fit, _desktop_sizes
    global _display_notice, _next_display_check
    sizes = connected_displays()
    index = _display_index if display_index is None else display_index
    _display_notice = ""
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(sizes):
        index = 0
        _display_notice = "Selected screen is unavailable; using Screen 1."
    fit = _screen_fit if screen_fit is None else screen_fit
    desktop = sizes[index]
    if fullscreen:
        mode, flags = desktop, pygame.FULLSCREEN
    else:
        ratio = min(
            1, max(320, desktop[0] - 100) / WINDOW_WIDTH, max(240, desktop[1] - 100) / WINDOW_HEIGHT
        )
        mode = (round(WINDOW_WIDTH * ratio), round(WINDOW_HEIGHT * ratio))
        flags = pygame.RESIZABLE
    try:
        real_screen = pygame.display.set_mode(mode, flags, display=index)
    except pygame.error:
        log.exception("Could not open screen %s in fullscreen=%s", index + 1, fullscreen)
        index, fullscreen = 0, False
        real_screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE, display=0
        )
        _display_notice = "Display change failed; returned to a window on Screen 1."
    _real_screen = real_screen
    if _profile_instance is not None and pygame.display.get_driver() == "windows":
        _profile_instance.tag_window(pygame.display.get_wm_info().get("window"))
    _fullscreen_mode = bool(fullscreen)
    _display_index = index
    _screen_fit = fit if fit in ("aspect", "fill") else "aspect"
    _desktop_sizes = sizes
    _next_display_check = pygame.time.get_ticks() + 1000
    _resize_display_buffers()
    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(not _fullscreen_mode)


def _resize_display_buffers():
    global _viewport, _scaled_surface
    width, height = _real_screen.get_size()
    ratio = min(width / WINDOW_WIDTH, height / WINDOW_HEIGHT)
    size = (
        (width, height)
        if _screen_fit == "fill"
        else (max(1, round(WINDOW_WIDTH * ratio)), max(1, round(WINDOW_HEIGHT * ratio)))
    )
    _viewport = pygame.Rect((width - size[0]) // 2, (height - size[1]) // 2, *size)
    _scaled_surface = pygame.Surface(size).convert()


def handle_display_event(event):
    """F11 / Alt+Enter work in every menu and game; F10 selects the next screen."""
    if event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
        toggle = event.key == pygame.K_F11 or (
            event.key == pygame.K_RETURN and getattr(event, "mod", 0) & pygame.KMOD_ALT
        )
        if toggle or event.key == pygame.K_F10:
            input_manager.suppress_key(event.key)
            index = _display_index
            if event.key == pygame.K_F10:
                index = (index + 1) % len(connected_displays())
            configure_display(not _fullscreen_mode if toggle else _fullscreen_mode, index)
            settings_manager.update(
                {"fullscreen": _fullscreen_mode, "display_index": _display_index}
            )
            return True
    if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
        if _real_screen is not None:
            _resize_display_buffers()
    return False


def _refresh_displays():
    global _desktop_sizes, _next_display_check
    now = pygame.time.get_ticks()
    if now < _next_display_check:
        return
    _next_display_check = now + 1000
    sizes = connected_displays()
    if _display_index >= len(sizes) or (
        _fullscreen_mode
        and (
            _display_index >= len(_desktop_sizes)
            or sizes[_display_index] != _desktop_sizes[_display_index]
        )
    ):
        configure_display(_fullscreen_mode, _display_index)
    else:
        _desktop_sizes = sizes


def _do_scale_to_screen():
    if _render_surface is None or _real_screen is None:
        pygame.display.flip()
        return
    _refresh_displays()
    _real_screen.fill((0, 0, 0))
    if _viewport.size == _render_surface.get_size():
        _real_screen.blit(_render_surface, _viewport)
    else:
        pygame.transform.scale(_render_surface, _viewport.size, _scaled_surface)
        _real_screen.blit(_scaled_surface, _viewport)
    pygame.display.flip()


def logical_mouse(pos):
    if not _viewport.collidepoint(pos):
        return (-1, -1)
    return (
        (pos[0] - _viewport.x) * WINDOW_WIDTH / _viewport.width,
        (pos[1] - _viewport.y) * WINDOW_HEIGHT / _viewport.height,
    )


def poll_events(shortcuts=True):
    global _quit_requested
    events = [
        event for event in pygame.event.get() if not (shortcuts and handle_display_event(event))
    ]
    for event in events:
        input_manager.handle_event(event)
    input_manager.update()
    for event in events:
        if event.type == pygame.QUIT:
            _quit_requested = True
        elif shortcuts and event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            audio_manager.toggle_mute()
    return events


def centered(screen, font, text, y, color=WEASEL_BROWN):
    image = font.render(text, True, color)
    screen.blit(image, image.get_rect(midtop=(WINDOW_WIDTH // 2, y)))


class Button:
    def __init__(self, rect, text, font, color=WEASEL_BROWN):
        self.rect = pygame.Rect(rect)
        self.color = color
        self.label = font.render(text, True, color)
        self.is_hovered = False

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def draw(self, screen, selected=False):
        pygame.draw.rect(screen, CUTE_SHADOW, self.rect.move(3, 3), border_radius=12)
        pygame.draw.rect(
            screen,
            CUTE_BUTTON_HOVER if selected or self.is_hovered else CUTE_BUTTON_BG,
            self.rect,
            border_radius=12,
        )
        pygame.draw.rect(screen, self.color, self.rect, 3 if selected else 1, border_radius=12)
        screen.blit(self.label, self.label.get_rect(center=self.rect.center))


def generate_cute_decorations(random_module):
    """Generate playful polka dots and confetti for a cute background."""
    decorations = []

    # Soft pastel colors for polka dots - more variety and softer
    dot_colors = [
        (255, 200, 200, 50),  # Soft pink
        (200, 230, 255, 50),  # Soft blue
        (255, 240, 200, 50),  # Soft cream
        (200, 255, 220, 50),  # Soft mint
        (240, 220, 255, 50),  # Soft lavender
        (255, 220, 180, 45),  # Soft peach
        (255, 255, 200, 45),  # Soft yellow
        (220, 255, 255, 45),  # Soft cyan
    ]

    # Create evenly distributed polka dots - more dots for fuller look
    for _ in range(80):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6, 7, 8, 10, 12, 15, 18])
        color = random_module.choice(dot_colors)
        decorations.append(("dot", x, y, size, color))

    # Add some tiny sparkle stars - more stars
    star_colors = [
        (255, 255, 200, 120),  # Golden yellow
        (255, 220, 255, 100),  # Soft pink
        (220, 255, 255, 100),  # Soft cyan
        (255, 255, 255, 130),  # White
    ]
    for _ in range(30):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([3, 4, 5, 6])
        color = random_module.choice(star_colors)
        decorations.append(("star", x, y, size, color))

    # Add small heart shapes - more hearts
    heart_colors = [
        (255, 182, 193, 60),  # Light pink
        (255, 160, 180, 55),  # Rose pink
        (255, 200, 200, 50),  # Blush
    ]
    for _ in range(18):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([5, 6, 7, 8, 10])
        color = random_module.choice(heart_colors)
        decorations.append(("heart", x, y, size, color))

    # Add tiny paw prints
    paw_colors = [
        (220, 190, 160, 45),  # Light brown
        (200, 180, 160, 45),  # Soft taupe
    ]
    for _ in range(20):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6, 7])
        color = random_module.choice(paw_colors)
        decorations.append(("paw", x, y, size, color))

    # Add tiny flowers
    flower_colors = [
        (255, 200, 210, 70),  # Pink
        (255, 255, 180, 70),  # Yellow
        (200, 220, 255, 70),  # Blue
        (255, 220, 255, 70),  # Lavender
    ]
    for _ in range(15):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6])
        color = random_module.choice(flower_colors)
        decorations.append(("flower", x, y, size, color))

    return decorations


def draw_decorations(surface, decorations):
    """Draw the cute decorations on the surface."""
    for deco in decorations:
        deco_type = deco[0]
        x, y, size, color = deco[1], deco[2], deco[3], deco[4]

        # Create surface with alpha for transparency
        if deco_type == "dot":
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (size, size), size)
            surface.blit(s, (x - size, y - size))

        elif deco_type == "star":
            # Simple 4-point star
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            cx, cy = size, size
            # Draw small cross/sparkle
            pygame.draw.line(s, color, (cx - size, cy), (cx + size, cy), 2)
            pygame.draw.line(s, color, (cx, cy - size), (cx, cy + size), 2)
            # Diagonal lines for sparkle effect
            ds = size // 2
            pygame.draw.line(s, color, (cx - ds, cy - ds), (cx + ds, cy + ds), 1)
            pygame.draw.line(s, color, (cx - ds, cy + ds), (cx + ds, cy - ds), 1)
            surface.blit(s, (x - size, y - size))

        elif deco_type == "heart":
            # Simple heart shape using circles and triangle
            s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            # Two circles for top of heart
            pygame.draw.circle(s, color, (size, size), size // 2 + 1)
            pygame.draw.circle(s, color, (size * 2, size), size // 2 + 1)
            # Triangle for bottom
            points = [(size // 2, size), (size * 5 // 2, size), (size * 3 // 2, size * 5 // 2)]
            pygame.draw.polygon(s, color, points)
            surface.blit(s, (x - size, y - size))

        elif deco_type == "paw":
            # Simple paw print - one pad and three toes
            s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            # Main pad
            pygame.draw.ellipse(s, color, (size // 2, size, size * 2, size * 3 // 2))
            # Three toe beans
            pygame.draw.circle(s, color, (size // 2, size // 2 + 2), size // 3)
            pygame.draw.circle(s, color, (size * 3 // 2, size // 3), size // 3)
            pygame.draw.circle(s, color, (size * 5 // 2, size // 2 + 2), size // 3)
            surface.blit(s, (x - size, y - size))

        elif deco_type == "flower":
            # Simple flower with petals around a center
            import math

            s = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            cx, cy = size * 2, size * 2
            # Draw petals in a circle
            for i in range(5):
                angle = i * (2 * math.pi / 5) - math.pi / 2
                px = cx + int(size * 0.8 * math.cos(angle))
                py = cy + int(size * 0.8 * math.sin(angle))
                pygame.draw.circle(s, color, (px, py), size)
            # Yellow center
            center_color = (255, 220, 100, color[3] + 30 if len(color) > 3 else 100)
            pygame.draw.circle(s, center_color, (cx, cy), size // 2 + 1)
            surface.blit(s, (x - size * 2, y - size * 2))


def create_vignette_surface():
    """Create a soft, subtle gradient overlay for depth effect."""
    vignette = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

    # Draw radial gradient from center (transparent) to edges (soft warm tint)
    center_x, center_y = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

    # Draw concentric rectangles with soft warm tint at edges
    for i in range(25):
        # Calculate distance factor (0 at center, 1 at edges)
        factor = i / 25
        # Very subtle opacity, max 30 alpha for soft effect
        alpha = int(factor * factor * 30)
        # Warm brownish tint instead of black for cozier feel
        color = (180, 150, 120, alpha)

        # Calculate inset
        inset = int((1 - factor) * min(center_x, center_y) * 0.9)
        rect = pygame.Rect(inset, inset, WINDOW_WIDTH - 2 * inset, WINDOW_HEIGHT - 2 * inset)
        pygame.draw.rect(vignette, color, rect, width=max(1, inset // 8))

    return vignette


def run_menu(screen):
    """Ferret navigation plus an accessible controller-operated utilities menu."""
    from engine.base_game import AchievementToast

    audio_manager.play_music("home_theme")
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 55)
    font = pygame.font.Font(None, 32)
    small = pygame.font.Font(None, 25)
    buttons = [
        Button(
            (50 + (i % 2) * 400, 150 + (i // 2) * 80, 300, 60), game["name"], font, game["color"]
        )
        for i, game in enumerate(GAMES)
    ]
    tools_button = Button((270, 445, 260, 48), "Options / Quit", font)
    background = pygame.Surface(screen.get_size()).convert()
    background.fill(CUTE_BG_PRIMARY)
    draw_decorations(background, generate_cute_decorations(random.Random(42)))
    background.blit(create_vignette_surface(), (0, 0))
    centered(background, title_font, TITLE, 55, TITLE_COLOR)
    centered(background, small, "Choose a game with the D-pad, then press A / Enter", 115)
    centered(background, small, "Arrows / WASD: Move   A / Enter: Play   B / Tab: Options", 510)
    centered(
        background,
        small,
        "F1: Settings   F2: Achievements   F3: Stats   T: Controller   M: Mute",
        538,
    )
    centered(background, small, "F11: Fullscreen   F10: Next screen", 566)
    selected = next(
        (i for i, g in enumerate(GAMES) if g["key"] == settings_manager.get("last_game")), 0
    )
    column = selected % 2
    targets = [(b.rect.left + 38, b.rect.centery) for b in buttons + [tools_button]]
    ferret = AnimatedFerret(*targets[selected], scale=2, speed=1, frame_delay=4)
    toast = AchievementToast(get_achievement_manager())
    last_activity = pygame.time.get_ticks()
    shortcuts = {pygame.K_F1: -2, pygame.K_F2: -3, pygame.K_F3: -4, pygame.K_t: -1}
    while not _quit_requested:
        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        events = poll_events()
        mouse = logical_mouse(pygame.mouse.get_pos())
        for button in buttons + [tools_button]:
            button.check_hover(mouse)
        for event in events:
            if event.type in (
                pygame.KEYDOWN,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEMOTION,
                pygame.JOYBUTTONDOWN,
                pygame.JOYHATMOTION,
            ):
                last_activity = pygame.time.get_ticks()
            if event.type == pygame.KEYDOWN and event.key in shortcuts:
                audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                return shortcuts[event.key]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, button in enumerate(buttons):
                    if button.rect.collidepoint(logical_mouse(event.pos)):
                        audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                        settings_manager.set("last_game", GAMES[index]["key"], persist=False)
                        return index
                if tools_button.rect.collidepoint(logical_mouse(event.pos)):
                    audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                    return -6
        if input_manager.back_pressed():
            audio_manager.play_sound(AudioManager.SOUND_BACK)
            return -6
        dx, dy = input_manager.menu_direction()
        previous = selected
        options = len(buttons)
        if selected == options:
            if dy < 0:
                selected = options - 2 + column
        elif dy:
            selected = min(options, max(column, selected + (2 if dy > 0 else -2)))
        elif dx:
            column = int(dx > 0)
            selected = selected // 2 * 2 + column
        if dx or dy:
            last_activity = pygame.time.get_ticks()
        if selected != previous:
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
            if selected < options:
                settings_manager.set("last_game", GAMES[selected]["key"], persist=False)
        on_tools = selected == options
        if input_manager.confirm_pressed():
            audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
            return -6 if on_tools else selected
        delta = pygame.Vector2(targets[selected]) - pygame.Vector2(ferret.x, ferret.y)
        idle = (pygame.time.get_ticks() - last_activity) / 1000.0
        desired = (
            "movement"
            if delta.length_squared() > 0.01
            else "sleep"
            if idle >= 30
            else "idle2"
            if idle >= 15
            else "idle"
        )
        if ferret.state != desired:
            ferret.set_state(desired)
        if delta.length_squared() > (850 * dt) ** 2:
            delta.scale_to_length(850 * dt)
        ferret.update(delta.x, delta.y, auto_state=False)
        screen.blit(background, (0, 0))
        for index, button in enumerate(buttons):
            button.draw(screen, index == selected)
        tools_button.draw(screen, on_tools)
        if not on_tools:
            centered(screen, small, GAMES[selected]["description"], 402)
        ferret.draw(screen)
        if audio_manager.muted:
            centered(screen, small, "MUTED", 22)
        toast.update(dt)
        toast.draw(screen)
        engine.scale_to_screen()
    return None


def choose(screen, title, labels, selected=0, subtitle="", details=None):
    """Shared edge/repeat navigation for options and difficulty screens."""
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 32)
    small = pygame.font.Font(None, 25)
    buttons = [
        Button((175, 140 + index * 53, 450, 44), label, font) for index, label in enumerate(labels)
    ]
    while not _quit_requested:
        events = poll_events()
        if input_manager.back_pressed():
            audio_manager.play_sound(AudioManager.SOUND_BACK)
            return None
        dx, dy = input_manager.menu_direction()
        if dx or dy:
            selected = (selected + (dy or dx)) % len(labels)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        for event in events:
            if details and event.type == pygame.MOUSEMOTION:
                selected = next(
                    (
                        i
                        for i, b in enumerate(buttons)
                        if b.rect.collidepoint(logical_mouse(event.pos))
                    ),
                    selected,
                )
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, button in enumerate(buttons):
                    if button.rect.collidepoint(logical_mouse(event.pos)):
                        audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                        return index
        if input_manager.confirm_pressed():
            audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
            return selected
        screen.fill(CUTE_BG_PRIMARY)
        centered(screen, heading, title, 45, TITLE_COLOR)
        centered(screen, small, subtitle, 100)
        for index, button in enumerate(buttons):
            button.check_hover(logical_mouse(pygame.mouse.get_pos()))
            button.draw(screen, index == selected)
        if details:
            for i, line in enumerate(details[selected]):
                centered(screen, font if i == 0 else small, line, 365 + i * 53)
        centered(
            screen, small, "D-pad / Arrows / WASD: Select   A / Enter: Confirm   B / Esc: Back", 555
        )
        engine.scale_to_screen()
        clock.tick(FPS)
    return None


def select_difficulty(screen, game_name, game_color=None):
    choices = list(Difficulty)
    game = next((g for g in GAMES if g["name"] == game_name), None)
    details = []
    if game:
        scores, stats = get_score_manager(), get_stats_manager()
        for difficulty, rule in zip(choices, game["rules"]):
            score = scores.get_high_score(game["key"], difficulty)
            record = f"Best score  {score:,}" if score else "No score yet"
            if game["key"] in ("digdug", "boulderdash"):
                best = stats.best_clear(game["key"], difficulty)
                record += (
                    f"     |     Best clear  {stats.format_clear(best)}"
                    if best
                    else "     |     First clear still to earn"
                )
            details.append((rule, record))
    choice = choose(
        screen, game_name, [d.display_name for d in choices], 1, "Select difficulty", details
    )
    return choices[choice] if choice is not None else None


def run_options(screen):
    choice = choose(
        screen,
        "Options",
        ["Settings", "Achievements", "Statistics", "Controller test", "Back to games", "Quit"],
    )
    return {-1: None, 0: -2, 1: -3, 2: -4, 3: -1, 4: -7, 5: None}.get(choice, -7)


def run_settings_menu(screen):
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 32)
    small = pygame.font.Font(None, 25)
    values = settings_manager.get_all()
    original = values.copy()
    values["muted"] = audio_manager.muted
    values["fullscreen"] = _fullscreen_mode
    values["display_index"] = _display_index
    values["screen_fit"] = _screen_fit
    selected = 0
    options = [
        ("audio_volume", "Volume"),
        ("muted", "Mute"),
        ("fullscreen", "Fullscreen"),
        ("display_index", "Screen"),
        ("screen_fit", "Picture"),
        ("music_volume", "Music volume"),
        ("effects_volume", "Effects volume"),
    ]
    try:
        while not _quit_requested:
            events = poll_events()
            values["fullscreen"] = _fullscreen_mode
            values["display_index"] = _display_index
            values["screen_fit"] = _screen_fit
            if any(e.type == pygame.KEYDOWN and e.key == pygame.K_m for e in events):
                values["muted"] = audio_manager.muted
            if input_manager.back_pressed():
                audio_manager.play_sound(AudioManager.SOUND_BACK)
                break
            dx, dy = input_manager.menu_direction()
            if dy:
                selected = (selected + dy) % len(options)
                audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
            key = options[selected][0]
            if dx or input_manager.confirm_pressed():
                if key in ("audio_volume", "music_volume", "effects_volume"):
                    values[key] = max(0, min(100, values[key] + (dx or 1) * 10))
                elif key == "display_index":
                    values[key] = (values[key] + (dx or 1)) % len(connected_displays())
                elif key == "screen_fit":
                    values[key] = "fill" if values[key] == "aspect" else "aspect"
                else:
                    values[key] = not values[key]
                audio_manager.volume = values["audio_volume"] / 100.0
                audio_manager.music_volume = values["music_volume"] / 100.0
                audio_manager.effects_volume = values["effects_volume"] / 100.0
                audio_manager.set_mute(values["muted"])
                audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if key in ("fullscreen", "display_index", "screen_fit"):
                    configure_display(
                        values["fullscreen"], values["display_index"], values["screen_fit"]
                    )
                    values.update(
                        fullscreen=_fullscreen_mode,
                        display_index=_display_index,
                        screen_fit=_screen_fit,
                    )
            screen.fill(CUTE_BG_PRIMARY)
            centered(screen, heading, "Settings", 55, TITLE_COLOR)
            for index, (key, label) in enumerate(options):
                if key in ("audio_volume", "music_volume", "effects_volume"):
                    value = f"{values[key]}%"
                elif key == "display_index":
                    sizes = connected_displays()
                    width, height = sizes[min(values[key], len(sizes) - 1)]
                    value = f"{values[key] + 1} of {len(sizes)} ({width} x {height})"
                elif key == "screen_fit":
                    value = (
                        "Keep proportions" if values[key] == "aspect" else "Fill screen (stretch)"
                    )
                else:
                    value = "ON" if values[key] else "OFF"
                button = Button((125, 110 + index * 45, 550, 39), f"{label}: {value}", font)
                button.draw(screen, index == selected)
            note = _display_notice or (
                "HDMI TV: choose its screen here after connecting it."
                if len(connected_displays()) > 1
                else "One screen detected. HDMI mirrors it or adds a second screen."
            )
            centered(screen, small, note, 438)
            centered(
                screen,
                small,
                "Up / Down: Select   Left / Right: Change   B / Esc: Save and return",
                485,
            )
            centered(screen, small, "F11 / Alt+Enter: Fullscreen   F10: Next screen", 523)
            engine.scale_to_screen()
            clock.tick(FPS)
    finally:
        if values != original:
            settings_manager.update(values)


def show_rows(screen, title, rows, subtitle=""):
    """Seven 54px rows leave explicit space for headings and scroll hints."""
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 46)
    font = pygame.font.Font(None, 28)
    small = pygame.font.Font(None, 23)
    offset = 0
    visible = 7
    maximum = max(0, len(rows) - visible)
    while not _quit_requested:
        poll_events()
        if input_manager.back_pressed():
            return
        _, dy = input_manager.menu_direction()
        offset = max(0, min(maximum, offset + dy))
        screen.fill(CUTE_BG_PRIMARY)
        centered(screen, heading, title, 30, TITLE_COLOR)
        centered(screen, small, subtitle, 80)
        for index, (name, detail) in enumerate(rows[offset : offset + visible]):
            y = 120 + index * 54
            screen.blit(font.render(name, True, WEASEL_BROWN), (65, y))
            screen.blit(small.render(detail, True, (110, 95, 80)), (80, y + 26))
        centered(
            screen,
            small,
            f"Rows {min(offset + 1, len(rows))}-{min(offset + visible, len(rows))} of {len(rows)}",
            515,
        )
        centered(screen, small, "Up / Down: Scroll   B / Esc: Back", 555)
        engine.scale_to_screen()
        clock.tick(FPS)


def run_achievements_viewer(screen):
    manager = get_achievement_manager()
    names = {g["key"]: g["name"] for g in GAMES}
    rows = [
        (
            f"{'[Unlocked]' if a['unlocked'] else '[Locked]'} {a['name']}",
            f"{names.get(a.get('game'), 'Global')}: {a['desc']}",
        )
        for a in manager.get_all_achievements()
    ]
    unlocked, total = manager.get_progress()
    show_rows(screen, "Achievements", rows, f"{unlocked} / {total} unlocked")


def run_stats_viewer(screen):
    manager = get_stats_manager()
    names = {g["key"]: g["name"] for g in GAMES}
    rows = []
    for category, values in manager.get_all().items():
        for key, value in values.items():
            text = (
                manager.format_play_time(value)
                if key == "total_play_time"
                else str(round(value, 2))
            )
            if key.startswith("best_clear_ticks_"):
                difficulty = key.removeprefix("best_clear_ticks_").title()
                label = f"Best Clear ({difficulty})"
                text = manager.format_clear(int(value))
            else:
                label = key.replace("_", " ").title()
            rows.append((f"{names.get(category, 'Global')} - {label}", text))
    show_rows(screen, "Statistics", rows)


def test_controller(screen):
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 42)
    font = pygame.font.Font(None, 27)
    last_button = "None"
    actions = [
        Button((65, 452, 315, 44), "Calibrate D-pad  (C)", font),
        Button((420, 452, 315, 44), "Remap buttons  (R)", font),
    ]
    selected = 0
    status = ""
    while not _quit_requested:
        events = poll_events()
        for event in events:
            if event.type == pygame.JOYBUTTONDOWN:
                last_button = str(event.button)
        if input_manager.back_pressed() or input_manager.was_pressed("start"):
            return
        if input_manager.joystick:
            dx, dy = input_manager.menu_direction()
            if dx or dy:
                selected = 1 if (dx or dy) > 0 else 0
            action = selected if input_manager.action_pressed() else None
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_c, pygame.K_r):
                    action = int(event.key == pygame.K_r)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = next(
                        (
                            i
                            for i, b in enumerate(actions)
                            if b.rect.collidepoint(logical_mouse(event.pos))
                        ),
                        action,
                    )
            if action is not None:
                status = calibrate_controller(screen) if action == 0 else remap_controller(screen)
                input_manager.discard_pending()
        screen.fill(CUTE_BG_PRIMARY)
        centered(screen, heading, "Controller test", 35, TITLE_COLOR)
        info = input_manager.get_controller_info()
        rows = ["No controller detected. Connect one to test it."]
        if info:
            rows = [
                f"Controller: {info['name']}",
                f"Buttons: {info['num_buttons']}   Axes: {info['num_axes']}   Hats: {info['num_hats']}",
                "Mappings: " + ", ".join(f"{k}={v}" for k, v in input_manager.button_map.items()),
                f"D-pad: {input_manager.get_dpad()}   Last button: {last_button}",
            ]
            joystick = input_manager.joystick
            try:
                rows += [
                    f"Axis {i}: {joystick.get_axis(i):+.2f}"
                    for i in range(min(6, info["num_axes"]))
                ]
            except pygame.error:
                rows.append("Controller disconnected; reconnect to continue.")
        for index, row in enumerate(rows):
            screen.blit(font.render(row, True, WEASEL_BROWN), (40, 100 + index * 31))
        if info:
            for i, button in enumerate(actions):
                button.check_hover(logical_mouse(pygame.mouse.get_pos()))
                button.draw(screen, i == selected)
        centered(screen, font, status, 515)
        centered(screen, font, "D-pad: choose    A / Enter: open    Start / B / Esc: back", 550)
        engine.scale_to_screen()
        clock.tick(30)


def remap_controller(screen):
    choice = choose(
        screen, "Remap controller buttons", ["All four buttons"] + [n.upper() for n in BUTTON_NAMES]
    )
    if choice is None:
        return "Mapping cancelled."
    names = BUTTON_NAMES if choice == 0 else (BUTTON_NAMES[choice - 1],)
    pad = input_manager.joystick
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 45)
    font = pygame.font.Font(None, 29)
    cancel = Button((295, 460, 210, 48), "Cancel  (Esc)", font)
    captured = {}
    cancel_since = None
    released = False
    message = ""
    while not _quit_requested:
        events = poll_events()
        if any(
            (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE)
            or (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
                and cancel.rect.collidepoint(logical_mouse(e.pos))
            )
            for e in events
        ):
            return "Mapping cancelled."
        if input_manager.get_dpad() == (-1, 0):
            now = pygame.time.get_ticks()
            if cancel_since is None:
                cancel_since = now
            elif now - cancel_since >= 1000:
                return "Mapping cancelled."
        else:
            cancel_since = None
        state = input_manager.raw_controller_state()
        if state is None or input_manager.joystick is not pad:
            return "Controller disconnected. Reconnect and try again."
        held = [i for i, down in enumerate(state["buttons"]) if down]
        if released:
            pressed = next(
                (
                    e.button
                    for e in events
                    if e.type == pygame.JOYBUTTONDOWN
                    and getattr(e, "instance_id", pad.get_instance_id()) == pad.get_instance_id()
                ),
                None,
            )
            button = pressed if pressed is not None else next(iter(held), None)
            if button is not None:
                name = names[len(captured)]
                message = button_conflict(
                    name,
                    button,
                    input_manager.button_map,
                    names,
                    captured,
                    input_manager._dpad_button_ids(),
                )
                if not message:
                    captured[name] = button
                released = False
        elif not held:
            if len(captured) == len(names):
                if input_manager.save_button_mapping(captured):
                    return "Buttons saved. Try the new mapping."
                return "Could not save the mapping."
            released = True
        screen.fill(CUTE_BG_PRIMARY)
        centered(screen, heading, "Remap controller buttons", 65, TITLE_COLOR)
        prompt = (
            f"Press the physical button for {names[len(captured)].upper()}."
            if released
            else "Release all buttons."
        )
        centered(screen, heading, prompt, 205)
        centered(screen, font, message, 279)
        centered(screen, font, f"{len(captured)} of {len(names)} captured", 345)
        cancel.draw(screen)
        centered(screen, font, "Hold D-pad Left for one second to cancel.", 550)
        engine.scale_to_screen()
        clock.tick(60)
    return "Mapping cancelled."


def calibrate_controller(screen):
    """Learn four physical D-pad signals, including nonstandard USB axis layouts."""
    clock = pygame.time.Clock()
    title = pygame.font.Font(None, 46)
    font = pygame.font.Font(None, 34)
    small = pygame.font.Font(None, 25)
    names = list(DIRECTIONS)
    neutral = None
    baseline = None
    candidate = None
    held_since = None
    bindings = {}
    stage = "neutral"
    message = "Release the D-pad and all buttons."
    while not _quit_requested:
        events = poll_events()
        if input_manager.was_pressed("start") or any(
            e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE for e in events
        ):
            return "Calibration cancelled."
        current = input_manager.raw_controller_state()
        if current is None:
            return "Controller disconnected. Reconnect and try again."
        now = pygame.time.get_ticks()
        if stage == "neutral":
            if baseline is None or not is_neutral(baseline, current):
                baseline, held_since = current, now
            elif now - held_since >= 700:
                neutral = current
                stage, held_since = "press", None
        elif stage == "press":
            detected = detect_binding(neutral, current)
            axes, hats, buttons = (
                dict(enumerate(current[key])) for key in ("axes", "hats", "buttons")
            )
            if detected is None:
                candidate, held_since = None, None
            elif (
                candidate is None
                or candidate["kind"] != detected["kind"]
                or candidate["index"] != detected["index"]
                or not binding_pressed(candidate, axes, hats, buttons)
            ):
                candidate, held_since = detected, now
            elif now - held_since >= 180:
                if any(binding_pressed(b, axes, hats, buttons) for b in bindings.values()):
                    message = "Direction already used. Release and try again."
                else:
                    bindings[names[len(bindings)]] = candidate
                    message = "Captured. Release the D-pad."
                stage, held_since = "release", None
        elif stage == "release":
            if not is_neutral(neutral, current):
                held_since = None
            elif held_since is None:
                held_since = now
            elif now - held_since >= 180:
                if len(bindings) == 4:
                    if valid_bindings(bindings) and input_manager.save_dpad_calibration(bindings):
                        return "D-pad saved. Check all four directions."
                    return "Could not save calibration. Please try again."
                stage, candidate, held_since = "press", None, None
        if stage == "press":
            message = f"Press and hold {names[len(bindings)].upper()}."
        screen.fill(CUTE_BG_PRIMARY)
        centered(screen, title, "Calibrate NES D-pad", 65, TITLE_COLOR)
        centered(screen, font, message, 210)
        centered(screen, small, "Keep each direction held until it is captured, then release.", 285)
        centered(screen, font, f"Directions captured: {len(bindings)} / 4", 355)
        centered(screen, small, "Start / Esc: Cancel", 540)
        engine.scale_to_screen()
        clock.tick(60)
    return "Calibration cancelled."


class ScriptedInput(InputManager):
    """Normal game input interface with no hardware initialization or global reset."""

    demo_mode = True

    def __init__(self):
        self.button_map = self.DEFAULT_BUTTON_MAP.copy()
        self.key_map = self.DEFAULT_KEY_MAP.copy()
        self.joystick = None
        self._curr_buttons = {}
        self._prev_buttons = {}
        self._curr_keys = {}
        self._prev_keys = {}
        self._curr_dpad = (0, 0)
        self._prev_dpad = (0, 0)
        self._menu_direction = (0, 0)
        self._menu_next_repeat = 0
        self.action = False
        self.previous_action = False

    def feed(self, direction, action=False):
        self._prev_dpad, self._curr_dpad = self._curr_dpad, direction
        self.previous_action, self.action = self.action, action

    def update(self):
        pass

    def action_pressed(self):
        return self.action and not self.previous_action

    def confirm_pressed(self):
        return self.action_pressed()

    def get_any_action_button(self):
        return self.action

    def was_pressed(self, name):
        return name in ("a", "action") and self.action_pressed()

    def is_pressed(self, name):
        return name in ("a", "action") and self.action

    def back_pressed(self):
        return False

    def pause_pressed(self):
        return False

    def get_any_back_button(self):
        return False


def demo_input(game_index, frame):
    """Deterministic directions and action pulses, routed through handle_input."""
    if game_index == 2:
        direction = (0, -1) if frame % 24 < 12 else (0, 0)
    elif game_index == 3:
        direction = (1 if (frame // 80) % 2 == 0 else -1, 0)
    else:
        direction = ((1, 0), (0, 1), (-1, 0), (0, -1))[(frame // 50) % 4]
    return direction, frame % 30 < 15


def guarded(screen, callback):
    """Keep a game failure inside the launcher and preserve a useful traceback."""
    try:
        return callback()
    except Exception:
        log.exception("Screen or game failed")
        choose(
            screen,
            "This game could not continue",
            ["Return to menu"],
            subtitle="Details were saved to wes.log in your WES data folder.",
        )
        return None


def cleanup():
    global _profile_instance
    if _profile_instance is None:
        return
    try:
        _shutdown_devices(save=True)
    finally:
        _profile_instance.close()
        _profile_instance = None


def _shutdown_devices(*, save):
    global _log_handler
    for factory in (
        (
            get_score_manager,
            get_settings_manager,
            get_stats_manager,
            get_achievement_manager,
        )
        if save
        else ()
    ):
        try:
            factory().save()
        except Exception:
            log.exception("Could not save %s during shutdown", factory.__name__)
    set_scale_callback(None)
    engine.set_global_event_callback(None)
    pygame.quit()
    if _log_handler is not None:
        logging.getLogger().removeHandler(_log_handler)
        _log_handler.close()
        _log_handler = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=TITLE)
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--fullscreen", action="store_true", default=None)
    display.add_argument("--windowed", dest="fullscreen", action="store_false")
    parser.add_argument(
        "--display", type=int, metavar="N", help="Use screen N (1 = first screen, 2 = second)"
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify all games headlessly with isolated saves, then exit",
    )
    args = parser.parse_args(argv)
    if args.display is not None and args.display < 1:
        parser.error("--display must be 1 or greater")
    if args.smoke_test:
        return smoke_test()
    screen = initialize(args.fullscreen, None if args.display is None else args.display - 1)
    if screen is None:
        return 0
    screens = {
        -1: test_controller,
        -2: run_settings_menu,
        -3: run_achievements_viewer,
        -4: run_stats_viewer,
    }
    try:
        while not _quit_requested:
            choice = run_menu(screen)
            if choice == -6:
                choice = run_options(screen)
            if choice is None:
                break
            if choice == -7:
                continue
            if choice in screens:
                guarded(screen, lambda: screens[choice](screen))
            else:
                difficulty = select_difficulty(screen, GAMES[choice]["name"])
                if difficulty is not None and not _quit_requested:

                    def play():
                        with persistence_session(difficulty=difficulty):
                            game = GAME_CLASSES[choice](screen, input_manager, difficulty)
                            game.run()
                            if getattr(game, "quit_requested", False):
                                global _quit_requested
                                _quit_requested = True
                            get_achievement_manager().check_global_achievements()

                    guarded(screen, play)
            pygame.display.set_caption(TITLE)
    finally:
        cleanup()
    return 0


def smoke_test():
    """Exercise packaged assets and game code without real data or hardware input."""
    previous = {
        key: os.environ.get(key) for key in ("WES_DATA_DIR", "SDL_VIDEODRIVER", "SDL_AUDIODRIVER")
    }
    with tempfile.TemporaryDirectory(prefix="wes-smoke-") as temporary:
        os.environ.update(WES_DATA_DIR=temporary, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        try:
            screen = initialize(False)
            for name, value in vars(AudioManager).items():
                if name.startswith("SOUND_") and isinstance(value, str):
                    if audio_manager._load_sound(value) is None:
                        raise RuntimeError(f"Packaged sound is missing or invalid: {value}")
            for key in ["home"] + [game["key"] for game in GAMES]:
                if not audio_manager.play_music(f"{key}_theme"):
                    raise RuntimeError(f"Packaged music is missing or invalid: {key}")
            audio_manager.stop_music()
            with persistence_session(demo=True):
                for index, cls in enumerate(GAME_CLASSES):
                    for difficulty in Difficulty:
                        controls = ScriptedInput()
                        game = cls(screen, controls, difficulty)
                        for frame in range(300):
                            controls.feed(*demo_input(index, frame))
                            game.advance(1 / FPS)
                            game.render()
                log.info("Smoke test passed: six games, three difficulties, 300 steps each")
            return 0
        except Exception:
            log.exception("Smoke test failed")
            return 1
        finally:
            cleanup()
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
