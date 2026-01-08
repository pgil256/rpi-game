#!/usr/bin/env python3
"""
Retro Game Launcher - A unified launcher for classic arcade games
All games run in the same window.
Supports NES-style gamepad: D-pad, A, B, Start, Select
"""

import pygame
import sys
import os
import argparse
import atexit

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Weasel Entertainment System')
parser.add_argument('--fullscreen', action='store_true', help='Run in fullscreen mode')
args = parser.parse_args()

# Initialize pygame - pre_init mixer BEFORE pygame.init() for reliable audio
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.init()
pygame.joystick.init()

# Import engine modules
import engine
from engine import (
    AnimatedFerret,
    InputManager,
    AssetLoader,
    AudioManager,
    Difficulty,
    get_audio_manager,
    get_score_manager,
    get_settings_manager,
    get_achievement_manager,
    get_stats_manager,
    get_demo_manager,
    set_scale_callback,
    # Constants
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    BLACK,
    WHITE,
    YELLOW,
    CYAN,
    MAGENTA,
    GREEN,
    RED,
    WEASEL_BROWN,
    WEASEL_TAN,
    WEASEL_WHITE,
    BURROW_BROWN,
    BUTTON_A,
    BUTTON_B,
    BUTTON_SELECT,
    BUTTON_START,
    DEADZONE,
    # Cute colors for redesigned menu
    CUTE_BG_PRIMARY,
    CUTE_BG_SECONDARY,
    CUTE_BUTTON_BG,
    CUTE_BUTTON_HOVER,
    CUTE_SHADOW,
    PASTEL_PINK,
    PASTEL_PEACH,
    PASTEL_CREAM,
    PASTEL_MINT,
    PASTEL_SKY,
    PASTEL_LAVENDER,
    CORAL_PINK,
    BLUSH,
    # Helper functions
    get_weasel_color,
)

# Import game classes
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

# Title color - warm golden yellow for cute theme
TITLE_COLOR = (255, 200, 100)
TITLE_SHADOW = (180, 120, 60)

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')

# Create global instances
input_manager = InputManager()
asset_loader = AssetLoader(BASE_DIR)
audio_manager = get_audio_manager()

# Load and apply saved settings
settings_manager = get_settings_manager()
if settings_manager.get('muted', False):
    audio_manager.muted = True

# Fullscreen scaling globals
_fullscreen_mode = False
_real_screen = None
_render_surface = None

def _do_scale_to_screen():
    """Scale the render surface to fill the real screen (for fullscreen mode)."""
    if _fullscreen_mode and _render_surface is not None and _real_screen is not None:
        # Scale render surface to fill the screen
        scaled = pygame.transform.scale(_render_surface, _real_screen.get_size())
        _real_screen.blit(scaled, (0, 0))
        pygame.display.flip()
    else:
        pygame.display.flip()

def scale_to_screen():
    """Wrapper that calls the engine's scale function."""
    engine.scale_to_screen()

# Backward-compatible wrapper functions for games (they still use these)
def load_media_image(filename, size=None):
    """Load an image from the media directory, optionally scaling it."""
    return asset_loader.load_image(filename, size)

def get_dpad():
    """Returns (dx, dy) where -1=left/up, +1=right/down, 0=neutral"""
    return input_manager.get_dpad()

def get_button(bid):
    """Check if button is pressed. Returns False if button doesn't exist."""
    return input_manager.get_button(bid)

def get_any_action_button():
    """Returns True if A, Start, or common action buttons pressed"""
    return input_manager.get_any_action_button()

def get_any_back_button():
    """Returns True if B, Select, or common back buttons pressed"""
    return input_manager.get_any_back_button()

GAMES = [
    {"name": "Snake", "description": "Grow your ferret family - eat soup and get longer!", "color": GREEN},
    {"name": "Pac-Man", "description": "Navigate the tunnels and eat all the treats!", "color": YELLOW},
    {"name": "Ferret Crossing", "description": "Help the ferret cross dangerous terrain!", "color": CYAN},
    {"name": "Centipede", "description": "Defend your burrow from the centipede invasion!", "color": MAGENTA},
    {"name": "Dig Dug", "description": "Dig for crystals in the underground maze!", "color": RED},
    {"name": "Boulder Dash", "description": "Collect diamonds but watch for falling rocks!", "color": WHITE},
]

class Button:
    def __init__(self, x, y, w, h, text, color, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.text, self.color, self.font = text, color, font
        self.is_hovered = False

    def draw(self, surface, selected=False):
        # Draw soft shadow for depth
        shadow_rect = self.rect.move(3, 3)
        pygame.draw.rect(surface, CUTE_SHADOW, shadow_rect, border_radius=15)

        # Button background - softer colors
        if self.is_hovered or selected:
            bg = CUTE_BUTTON_HOVER
        else:
            bg = CUTE_BUTTON_BG

        pygame.draw.rect(surface, bg, self.rect, border_radius=15)

        # Softer border with thicker line for selected
        border_width = 4 if selected else 2
        pygame.draw.rect(surface, self.color, self.rect, border_width, border_radius=15)

        # Add a subtle inner highlight for dimension
        if selected:
            inner_rect = self.rect.inflate(-6, -6)
            highlight_color = tuple(min(255, c + 40) for c in bg)
            pygame.draw.rect(surface, highlight_color, inner_rect, border_radius=12)

        # Draw text with subtle shadow for readability
        txt_shadow = self.font.render(self.text, True, CUTE_SHADOW)
        txt = self.font.render(self.text, True, self.color)
        shadow_pos = txt_shadow.get_rect(center=(self.rect.centerx + 1, self.rect.centery + 1))
        txt_pos = txt.get_rect(center=self.rect.center)
        surface.blit(txt_shadow, shadow_pos)
        surface.blit(txt, txt_pos)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def is_clicked(self, pos): return self.rect.collidepoint(pos)




class FloatingCloud:
    """A cute floating cloud that drifts across the screen."""

    def __init__(self, x, y, size, speed):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed

    def update(self):
        """Move the cloud slowly across the screen."""
        self.x += self.speed
        if self.x > WINDOW_WIDTH + self.size * 3:
            self.x = -self.size * 3
        elif self.x < -self.size * 3:
            self.x = WINDOW_WIDTH + self.size * 3

    def draw(self, surface):
        """Draw a cute fluffy cloud."""
        alpha = 60
        s = pygame.Surface((self.size * 4, self.size * 2), pygame.SRCALPHA)
        color = (255, 255, 255, alpha)
        # Draw overlapping circles to create cloud shape
        pygame.draw.circle(s, color, (self.size, self.size), self.size)
        pygame.draw.circle(s, color, (self.size * 2, int(self.size * 0.8)), int(self.size * 1.2))
        pygame.draw.circle(s, color, (self.size * 3, self.size), self.size)
        pygame.draw.circle(s, color, (int(self.size * 1.5), int(self.size * 1.3)), int(self.size * 0.8))
        pygame.draw.circle(s, color, (int(self.size * 2.5), int(self.size * 1.3)), int(self.size * 0.8))
        surface.blit(s, (int(self.x - self.size * 2), int(self.y - self.size)))


class FloatingHeart:
    """A floating heart that gently rises and fades."""

    def __init__(self, x, y):
        import random
        self.x = x + random.uniform(-20, 20)
        self.y = y
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.8, -0.3)
        self.size = random.randint(4, 8)
        self.life = random.randint(80, 150)
        self.max_life = self.life
        # Cute heart colors
        self.color = random.choice([
            (255, 182, 193),  # Pink
            (255, 105, 180),  # Hot pink
            (255, 160, 160),  # Light red
        ])

    def update(self):
        """Float upward with gentle wave motion."""
        import math
        self.x += self.vx + 0.5 * math.sin(self.life * 0.1)
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        """Draw a cute heart shape."""
        alpha = int(200 * (self.life / self.max_life))
        size = self.size
        s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        color = (*self.color, alpha)
        # Draw heart using circles and triangle
        pygame.draw.circle(s, color, (size, size), size // 2 + 1)
        pygame.draw.circle(s, color, (size * 2, size), size // 2 + 1)
        points = [(size // 2, size), (size * 5 // 2, size), (size * 3 // 2, size * 5 // 2)]
        pygame.draw.polygon(s, color, points)
        surface.blit(s, (int(self.x - size), int(self.y - size)))


def generate_cute_decorations(random_module):
    """Generate playful polka dots and confetti for a cute background."""
    decorations = []

    # Soft pastel colors for polka dots - more variety and softer
    dot_colors = [
        (255, 200, 200, 50),   # Soft pink
        (200, 230, 255, 50),   # Soft blue
        (255, 240, 200, 50),   # Soft cream
        (200, 255, 220, 50),   # Soft mint
        (240, 220, 255, 50),   # Soft lavender
        (255, 220, 180, 45),   # Soft peach
        (255, 255, 200, 45),   # Soft yellow
        (220, 255, 255, 45),   # Soft cyan
    ]

    # Create evenly distributed polka dots - more dots for fuller look
    for _ in range(80):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6, 7, 8, 10, 12, 15, 18])
        color = random_module.choice(dot_colors)
        decorations.append(('dot', x, y, size, color))

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
        decorations.append(('star', x, y, size, color))

    # Add small heart shapes - more hearts
    heart_colors = [
        (255, 182, 193, 60),   # Light pink
        (255, 160, 180, 55),   # Rose pink
        (255, 200, 200, 50),   # Blush
    ]
    for _ in range(18):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([5, 6, 7, 8, 10])
        color = random_module.choice(heart_colors)
        decorations.append(('heart', x, y, size, color))

    # Add tiny paw prints
    paw_colors = [
        (220, 190, 160, 45),   # Light brown
        (200, 180, 160, 45),   # Soft taupe
    ]
    for _ in range(20):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6, 7])
        color = random_module.choice(paw_colors)
        decorations.append(('paw', x, y, size, color))

    # Add tiny flowers
    flower_colors = [
        (255, 200, 210, 70),   # Pink
        (255, 255, 180, 70),   # Yellow
        (200, 220, 255, 70),   # Blue
        (255, 220, 255, 70),   # Lavender
    ]
    for _ in range(15):
        x = random_module.randint(0, WINDOW_WIDTH)
        y = random_module.randint(0, WINDOW_HEIGHT)
        size = random_module.choice([4, 5, 6])
        color = random_module.choice(flower_colors)
        decorations.append(('flower', x, y, size, color))

    return decorations


def draw_decorations(surface, decorations):
    """Draw the cute decorations on the surface."""
    for deco in decorations:
        deco_type = deco[0]
        x, y, size, color = deco[1], deco[2], deco[3], deco[4]

        # Create surface with alpha for transparency
        if deco_type == 'dot':
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (size, size), size)
            surface.blit(s, (x - size, y - size))

        elif deco_type == 'star':
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

        elif deco_type == 'heart':
            # Simple heart shape using circles and triangle
            s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            # Two circles for top of heart
            pygame.draw.circle(s, color, (size, size), size // 2 + 1)
            pygame.draw.circle(s, color, (size * 2, size), size // 2 + 1)
            # Triangle for bottom
            points = [(size // 2, size), (size * 5 // 2, size), (size * 3 // 2, size * 5 // 2)]
            pygame.draw.polygon(s, color, points)
            surface.blit(s, (x - size, y - size))

        elif deco_type == 'paw':
            # Simple paw print - one pad and three toes
            s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            # Main pad
            pygame.draw.ellipse(s, color, (size // 2, size, size * 2, size * 3 // 2))
            # Three toe beans
            pygame.draw.circle(s, color, (size // 2, size // 2 + 2), size // 3)
            pygame.draw.circle(s, color, (size * 3 // 2, size // 3), size // 3)
            pygame.draw.circle(s, color, (size * 5 // 2, size // 2 + 2), size // 3)
            surface.blit(s, (x - size, y - size))

        elif deco_type == 'flower':
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
        rect = pygame.Rect(inset, inset, WINDOW_WIDTH - 2*inset, WINDOW_HEIGHT - 2*inset)
        pygame.draw.rect(vignette, color, rect, width=max(1, inset // 8))

    return vignette


class SparkleParticle:
    """Cute sparkle particle for movement effect."""
    # Pre-create particle surface cache (class-level to share across all particles)
    _surface_cache = {}

    def __init__(self, x, y):
        import random
        self.x = x + random.uniform(-10, 10)
        self.y = y + random.uniform(-5, 5)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1.5, -0.5)  # Drift upward
        self.life = random.randint(15, 30)
        self.max_life = self.life
        self.size = random.randint(2, 4)
        # Softer, pastel sparkle colors
        self.color = random.choice([
            (255, 220, 200),  # Soft peach
            (255, 200, 220),  # Soft pink
            (220, 240, 255),  # Soft blue
            (255, 255, 200),  # Soft yellow
        ])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        # Quantize alpha to reduce number of cached surfaces (5 levels)
        alpha_ratio = self.life / self.max_life
        alpha_level = int(alpha_ratio * 4)  # 0-4 levels
        alpha = int((alpha_level / 4) * 255)

        # Cache key based on size, color, and quantized alpha
        cache_key = (self.size, self.color, alpha_level)

        if cache_key not in SparkleParticle._surface_cache:
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            SparkleParticle._surface_cache[cache_key] = s

        surface.blit(SparkleParticle._surface_cache[cache_key], (int(self.x - self.size), int(self.y - self.size)))


def run_menu(screen):
    clock = pygame.time.Clock()
    tf, bf, df, inf = pygame.font.Font(None, 72), pygame.font.Font(None, 36), pygame.font.Font(None, 24), pygame.font.Font(None, 28)
    bw, bh, sy, sp = 300, 60, 150, 75
    lx, rx = WINDOW_WIDTH//4 - bw//2, 3*WINDOW_WIDTH//4 - bw//2
    btns = [Button(lx if i%2==0 else rx, sy+(i//2)*sp, bw, bh, g["name"], g["color"], bf) for i, g in enumerate(GAMES)]
    import random
    random.seed(42)

    # Achievement notification state
    achievement_mgr = get_achievement_manager()
    achievement_notification = None
    notification_timer = 0
    NOTIFICATION_DURATION = 180  # 3 seconds at 60 FPS

    # Create cute decorations (polka dots, stars, hearts, paw prints, flowers)
    decorations = generate_cute_decorations(random)

    # Create floating clouds
    clouds = [
        FloatingCloud(100, 80, 25, 0.3),
        FloatingCloud(400, 50, 30, 0.2),
        FloatingCloud(650, 100, 20, 0.4),
        FloatingCloud(250, 130, 18, -0.25),
    ]

    # Floating hearts list (will be spawned during gameplay)
    floating_hearts = []
    heart_spawn_timer = 0

    # Pre-compute decorative connector paths between buttons (softer curved paths)
    connector_paths = []
    # Connect left column buttons vertically
    for i in range(0, len(btns)-2, 2):
        if i+2 < len(btns):
            start = (btns[i].rect.centerx, btns[i].rect.bottom)
            end = (btns[i+2].rect.centerx, btns[i+2].rect.top)
            connector_paths.append((start, end))
    # Connect right column buttons vertically
    for i in range(1, len(btns)-2, 2):
        if i+2 < len(btns):
            start = (btns[i].rect.centerx, btns[i].rect.bottom)
            end = (btns[i+2].rect.centerx, btns[i+2].rect.top)
            connector_paths.append((start, end))
    # Connect horizontally between columns at each row
    for i in range(0, len(btns)-1, 2):
        if i+1 < len(btns):
            start = (btns[i].rect.right, btns[i].rect.centery)
            end = (btns[i+1].rect.left, btns[i+1].rect.centery)
            connector_paths.append((start, end))

    # Create vignette overlay
    vignette = create_vignette_surface()

    sel = None  # No selection until ferret touches a button
    prev_sel = None  # Track previous selection for sound on change

    # Create animated ferret avatar using engine module - start in center of screen
    ferret = AnimatedFerret(
        x=WINDOW_WIDTH // 2,
        y=WINDOW_HEIGHT // 2,
        scale=2,
        speed=4.0,
        frame_delay=6
    )

    # Track idle time for animation state changes (at 60 FPS)
    # Sleep threshold is intentionally long - only for extended AFK in menu
    idle_frames = 0
    IDLE2_THRESHOLD = 15 * FPS   # 15 seconds -> looking around animation
    SLEEP_THRESHOLD = 90 * FPS   # 90 seconds (1.5 minutes) -> sleep animation
    ATTRACT_THRESHOLD = 60 * FPS  # 60 seconds -> start attract/demo mode

    # Sparkle particles list
    sparkle_particles = []
    sparkle_spawn_timer = 0

    while True:
        # Update input manager state for edge detection
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_RETURN and sel is not None:
                    audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                    return sel
                if e.key == pygame.K_t: return -1  # Controller test mode
                if e.key == pygame.K_s: return -2  # Settings menu
                if e.key == pygame.K_a: return -3  # Achievements viewer
                if e.key == pygame.K_x: return -4  # Statistics viewer
                if e.key == pygame.K_m:
                    audio_manager.toggle_mute()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, b in enumerate(btns):
                    if b.is_clicked(pygame.mouse.get_pos()):
                        audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                        return i

        # Gamepad buttons with edge detection using InputManager
        if input_manager.action_pressed() and sel is not None:
            audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
            return sel

        # D-pad moves the ferret
        dp = input_manager.get_dpad()

        # Track idle state and handle animation transitions
        if dp[0] != 0 or dp[1] != 0:
            # Movement detected - wake up ferret
            if idle_frames > IDLE2_THRESHOLD:
                # Was idle/sleeping, transition back to movement
                ferret.set_state('idle')
            idle_frames = 0

            # Spawn sparkle particles when moving (limit frequency for performance)
            sparkle_spawn_timer += 1
            if sparkle_spawn_timer >= 4:  # Spawn every 4 frames
                sparkle_spawn_timer = 0
                sparkle_particles.append(SparkleParticle(ferret.x, ferret.y + ferret.sprite_size // 3))
        else:
            idle_frames += 1
            # Progressive idle states
            if idle_frames == SLEEP_THRESHOLD:
                ferret.set_state('sleep')
            elif idle_frames == IDLE2_THRESHOLD:
                ferret.set_state('idle2')
            # Trigger attract mode after ATTRACT_THRESHOLD
            if idle_frames >= ATTRACT_THRESHOLD:
                return -5  # Attract/demo mode

        # Update ferret with D-pad direction
        ferret.update(dp[0], dp[1])

        # Keep ferret within screen bounds
        ferret.clamp_to_bounds(
            ferret.sprite_size // 2,
            ferret.sprite_size // 2,
            WINDOW_WIDTH - ferret.sprite_size // 2,
            WINDOW_HEIGHT - ferret.sprite_size // 2
        )

        # Update sparkle particles
        sparkle_particles = [p for p in sparkle_particles if p.update()]

        # Update floating clouds
        for cloud in clouds:
            cloud.update()

        # Update and spawn floating hearts
        floating_hearts = [h for h in floating_hearts if h.update()]
        heart_spawn_timer += 1
        if heart_spawn_timer >= 120:  # Spawn every 2 seconds
            heart_spawn_timer = 0
            # Spawn a heart at a random position near the bottom
            import random as rand_mod
            floating_hearts.append(FloatingHeart(
                rand_mod.randint(100, WINDOW_WIDTH - 100),
                rand_mod.randint(WINDOW_HEIGHT - 150, WINDOW_HEIGHT - 50)
            ))

        # Check if ferret's center overlaps any button to select it
        # Use center point collision - ferret must visually overlap the button
        ferret_center = (ferret.x, ferret.y)
        sel = None  # Reset selection each frame
        for i, b in enumerate(btns):
            # Only select when ferret's center is inside the button rectangle
            if b.rect.collidepoint(ferret_center):
                sel = i
                break  # Take first overlapping button

        # Play sound when selection changes
        if sel != prev_sel and sel is not None:
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        prev_sel = sel

        # Draw cute warm background
        screen.fill(CUTE_BG_PRIMARY)

        # Draw cute decorations (polka dots, stars, hearts, paw prints, flowers)
        draw_decorations(screen, decorations)

        # Draw floating clouds (behind buttons but above decorations)
        for cloud in clouds:
            cloud.draw(screen)

        # Draw soft connector paths between buttons
        connector_color = (215, 200, 185)  # Soft warm gray
        for start, end in connector_paths:
            # Draw soft dotted/dashed line instead of solid tunnel
            pygame.draw.line(screen, connector_color, start, end, 3)

        # Draw title with shadow for depth
        title_text = "Winston Entertainment System"
        t_shadow = tf.render(title_text, True, TITLE_SHADOW)
        t = tf.render(title_text, True, TITLE_COLOR)
        screen.blit(t_shadow, (WINDOW_WIDTH//2 - t.get_width()//2 + 2, 62))
        screen.blit(t, (WINDOW_WIDTH//2 - t.get_width()//2, 60))

        # Subtitle with softer color - positioned with more spacing below title
        subtitle = df.render("Move ferret to a game, press A to play!", True, WEASEL_BROWN)
        screen.blit(subtitle, (WINDOW_WIDTH//2 - subtitle.get_width()//2, 125))

        # Draw buttons
        for i, b in enumerate(btns):
            b.draw(screen, sel == i)

        # Draw game description if selected
        if sel is not None:
            d = df.render(GAMES[sel]["description"], True, GAMES[sel]["color"])
            screen.blit(d, (WINDOW_WIDTH//2 - d.get_width()//2, 400))

        # Draw sparkle particles behind ferret
        for p in sparkle_particles:
            p.draw(screen)

        # Draw floating hearts (behind ferret)
        for heart in floating_hearts:
            heart.draw(screen)

        # Draw ferret avatar
        ferret.draw(screen)

        # Apply soft vignette overlay for cozy depth effect
        screen.blit(vignette, (0, 0))

        help_text = "D-pad: Navigate | A: Select | S: Settings | M: Mute | T: Test"
        help_color = (160, 140, 120)  # Warm gray
        screen.blit(inf.render(help_text, True, help_color), (WINDOW_WIDTH//2-180, WINDOW_HEIGHT-50))
        # Only show mute status indicator when muted
        if audio_manager.muted:
            screen.blit(inf.render("[MUTED]", True, (200, 180, 100)), (WINDOW_WIDTH//2 + 140, WINDOW_HEIGHT-50))

        # Update and draw achievement notifications
        if notification_timer > 0:
            notification_timer -= 1
            if notification_timer <= 0:
                achievement_notification = None
        if achievement_notification is None and achievement_mgr.has_notification():
            achievement_notification = achievement_mgr.pop_notification()
            notification_timer = NOTIFICATION_DURATION

        # Draw achievement notification toast at top of screen
        if achievement_notification is not None:
            # Calculate slide animation
            progress = notification_timer / NOTIFICATION_DURATION
            if progress > 0.9:
                slide = 1.0 - ((progress - 0.9) / 0.1)
            elif progress < 0.1:
                slide = progress / 0.1
            else:
                slide = 1.0

            toast_width, toast_height = 320, 80
            toast_x = (WINDOW_WIDTH - toast_width) // 2
            toast_y = int(-toast_height + slide * (toast_height + 10))

            # Create toast surface
            toast_surf = pygame.Surface((toast_width, toast_height), pygame.SRCALPHA)
            pygame.draw.rect(toast_surf, (40, 40, 40, 230), (0, 0, toast_width, toast_height), border_radius=12)
            pygame.draw.rect(toast_surf, (255, 215, 0), (0, 0, toast_width, toast_height), width=3, border_radius=12)

            # Trophy icon
            pygame.draw.circle(toast_surf, (255, 215, 0), (25, 40), 15)
            pygame.draw.rect(toast_surf, (255, 215, 0), (17, 50, 16, 8))

            # Achievement text
            label_font = pygame.font.Font(None, 24)
            name_font = pygame.font.Font(None, 28)
            label_text = label_font.render("ACHIEVEMENT UNLOCKED!", True, (255, 215, 0))
            toast_surf.blit(label_text, (50, 15))
            name_text = name_font.render(achievement_notification["name"], True, (255, 255, 255))
            toast_surf.blit(name_text, (50, 40))

            screen.blit(toast_surf, (toast_x, toast_y))

        scale_to_screen()
        clock.tick(FPS)


def test_controller(screen):
    """Test controller to see button/axis mappings - press Start to exit"""
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 20)

    # Get controller info from InputManager
    controller_info = input_manager.get_controller_info()
    joystick = input_manager.joystick  # Direct access for detailed info

    if not controller_info:
        print("No controller detected!")
        return

    print("\n=== CONTROLLER TEST MODE ===")
    print("Press buttons and move D-pad to see mappings")
    print(f"Press START (button {BUTTON_START}) to exit test mode\n")

    # Track last pressed button for identification
    last_pressed_button = None

    while True:
        # Update input manager for edge detection
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.JOYBUTTONDOWN:
                last_pressed_button = e.button
                # Identify the button role
                role = ""
                if e.button == BUTTON_A:
                    role = " (mapped as A/Action)"
                elif e.button == BUTTON_B:
                    role = " (mapped as B/Back)"
                elif e.button == BUTTON_SELECT:
                    role = " (mapped as Select)"
                elif e.button == BUTTON_START:
                    role = " (mapped as Start)"
                print(f"Button {e.button} pressed{role}")
                if e.button == BUTTON_START: return

        screen.fill(BLACK)
        y = 20
        screen.blit(font.render(f"Controller: {controller_info['name']}", True, WHITE), (20, y)); y += 25
        screen.blit(font.render(f"Buttons: {controller_info['num_buttons']}, Axes: {controller_info['num_axes']}, Hats: {controller_info['num_hats']}", True, WHITE), (20, y)); y += 30

        # Show expected button mappings
        screen.blit(font.render("Expected Button Mapping:", True, CYAN), (20, y)); y += 22
        screen.blit(small_font.render(f"  A (Action):  Button {BUTTON_A}  |  B (Back):  Button {BUTTON_B}", True, (180, 180, 180)), (20, y)); y += 18
        screen.blit(small_font.render(f"  Select:      Button {BUTTON_SELECT}  |  Start:    Button {BUTTON_START}", True, (180, 180, 180)), (20, y)); y += 25

        # Show hat state
        if joystick and joystick.get_numhats() > 0:
            hat = joystick.get_hat(0)
            screen.blit(font.render(f"Hat 0 (D-pad): {hat}", True, CYAN), (20, y)); y += 22

        # Show axes with role labels
        if joystick:
            screen.blit(font.render("Analog Axes:", True, CYAN), (20, y)); y += 20
            axis_labels = ["Left Stick X", "Left Stick Y", "Right Stick X", "Right Stick Y", "L Trigger", "R Trigger"]
            for i in range(min(joystick.get_numaxes(), 6)):
                ax = joystick.get_axis(i)
                color = GREEN if abs(ax) > DEADZONE else WHITE
                label = axis_labels[i] if i < len(axis_labels) else f"Axis {i}"
                screen.blit(font.render(f"  Axis {i} ({label}): {ax:+.2f}", True, color), (20, y)); y += 20

        y += 10
        # Show currently pressed buttons with role identification
        if joystick:
            pressed = []
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    role = ""
                    if i == BUTTON_A: role = "=A"
                    elif i == BUTTON_B: role = "=B"
                    elif i == BUTTON_SELECT: role = "=Sel"
                    elif i == BUTTON_START: role = "=Start"
                    pressed.append(f"{i}{role}")
            screen.blit(font.render(f"Pressed: {pressed if pressed else 'None'}", True, YELLOW), (20, y)); y += 25

            # Show last pressed button prominently
            if last_pressed_button is not None:
                role = "Unknown"
                if last_pressed_button == BUTTON_A: role = "A (Action)"
                elif last_pressed_button == BUTTON_B: role = "B (Back)"
                elif last_pressed_button == BUTTON_SELECT: role = "Select"
                elif last_pressed_button == BUTTON_START: role = "Start"
                screen.blit(font.render(f"Last button: {last_pressed_button} -> {role}", True, MAGENTA), (20, y)); y += 30

        # Show D-pad interpretation using InputManager
        dp = input_manager.get_dpad()
        screen.blit(font.render(f"D-pad/Stick interpreted as: {dp}", True, GREEN), (20, y)); y += 25
        dirs = []
        if dp[0] == -1: dirs.append("LEFT")
        elif dp[0] == 1: dirs.append("RIGHT")
        if dp[1] == -1: dirs.append("UP")
        elif dp[1] == 1: dirs.append("DOWN")
        screen.blit(font.render(f"Direction: {' + '.join(dirs) if dirs else 'CENTER'}", True, GREEN), (20, y)); y += 35

        # Show action/back detection
        action_held = input_manager.get_any_action_button()
        back_held = input_manager.get_any_back_button()
        action_color = GREEN if action_held else (100, 100, 100)
        back_color = GREEN if back_held else (100, 100, 100)
        screen.blit(font.render(f"Action button: {'PRESSED' if action_held else 'released'}", True, action_color), (20, y)); y += 22
        screen.blit(font.render(f"Back button:   {'PRESSED' if back_held else 'released'}", True, back_color), (20, y)); y += 30

        screen.blit(font.render(f"Press START (button {BUTTON_START}) to exit, or ESC", True, (150,150,150)), (20, y))

        scale_to_screen()
        clock.tick(30)


def select_difficulty(screen, game_name, game_color):
    """Show difficulty selection screen before starting a game.

    Args:
        screen: The pygame display surface.
        game_name: Name of the game being started.
        game_color: Color associated with the game.

    Returns:
        Selected Difficulty enum, or None if cancelled.
    """
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)

    difficulties = [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]
    selected = 1  # Default to NORMAL

    # Difficulty-specific colors
    diff_colors = {
        Difficulty.EASY: (100, 200, 100),    # Green
        Difficulty.NORMAL: (200, 200, 100),  # Yellow
        Difficulty.HARD: (200, 100, 100),    # Red
    }

    while True:
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
                if e.key == pygame.K_UP or e.key == pygame.K_LEFT:
                    selected = (selected - 1) % len(difficulties)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if e.key == pygame.K_DOWN or e.key == pygame.K_RIGHT:
                    selected = (selected + 1) % len(difficulties)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if e.key == pygame.K_RETURN or e.key == pygame.K_SPACE:
                    audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                    return difficulties[selected]

        # Gamepad navigation
        dp = input_manager.get_dpad()
        if dp[1] == -1 or dp[0] == -1:  # Up or Left
            selected = (selected - 1) % len(difficulties)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        elif dp[1] == 1 or dp[0] == 1:  # Down or Right
            selected = (selected + 1) % len(difficulties)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)

        if input_manager.back_pressed():
            return None

        if input_manager.action_pressed():
            audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
            return difficulties[selected]

        # Draw
        screen.fill(CUTE_BG_PRIMARY)

        # Game title
        title = title_font.render(game_name, True, game_color)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 80))

        # "Select Difficulty" subtitle
        subtitle = font.render("Select Difficulty", True, WEASEL_BROWN)
        screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 150))

        # Draw difficulty options
        y = 220
        for i, diff in enumerate(difficulties):
            is_selected = (i == selected)
            color = diff_colors[diff] if is_selected else (120, 100, 80)

            # Draw selection box
            box_rect = pygame.Rect(WINDOW_WIDTH // 2 - 150, y - 5, 300, 50)
            if is_selected:
                pygame.draw.rect(screen, CUTE_BUTTON_HOVER, box_rect, border_radius=10)
                pygame.draw.rect(screen, color, box_rect, 3, border_radius=10)
            else:
                pygame.draw.rect(screen, CUTE_BUTTON_BG, box_rect, border_radius=10)
                pygame.draw.rect(screen, (180, 160, 140), box_rect, 2, border_radius=10)

            # Draw difficulty name
            name_text = font.render(diff.display_name, True, color)
            screen.blit(name_text, (WINDOW_WIDTH // 2 - name_text.get_width() // 2, y + 5))

            y += 70

        # Draw description of selected difficulty
        desc = difficulties[selected].description
        desc_text = small_font.render(desc, True, (100, 80, 60))
        screen.blit(desc_text, (WINDOW_WIDTH // 2 - desc_text.get_width() // 2, 450))

        # Controls help
        help_text = small_font.render("Up/Down: Select | A/Enter: Start | B/ESC: Back", True, (140, 120, 100))
        screen.blit(help_text, (WINDOW_WIDTH // 2 - help_text.get_width() // 2, WINDOW_HEIGHT - 60))

        scale_to_screen()
        clock.tick(FPS)


def run_settings_menu(screen):
    """Settings menu for audio, display, and controls."""
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 28)

    settings = get_settings_manager()

    # Menu options
    options = [
        {'key': 'audio_volume', 'label': 'Volume', 'type': 'slider', 'min': 0, 'max': 100},
        {'key': 'muted', 'label': 'Mute', 'type': 'toggle'},
        {'key': 'fullscreen', 'label': 'Fullscreen', 'type': 'toggle', 'note': '(requires restart)'},
    ]
    selected = 0

    while True:
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE or e.key == pygame.K_s:
                    return
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if e.key == pygame.K_LEFT or e.key == pygame.K_RIGHT:
                    opt = options[selected]
                    if opt['type'] == 'slider':
                        delta = 10 if e.key == pygame.K_RIGHT else -10
                        current = settings.get(opt['key'], 100)
                        new_val = max(opt['min'], min(opt['max'], current + delta))
                        settings.set(opt['key'], new_val)
                        audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                    elif opt['type'] == 'toggle':
                        current = settings.get(opt['key'], False)
                        settings.set(opt['key'], not current)
                        # Sync mute state with audio manager
                        if opt['key'] == 'muted':
                            if settings.get('muted'):
                                audio_manager.muted = True
                            else:
                                audio_manager.muted = False
                        audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)
                if e.key == pygame.K_RETURN or e.key == pygame.K_SPACE:
                    opt = options[selected]
                    if opt['type'] == 'toggle':
                        current = settings.get(opt['key'], False)
                        settings.set(opt['key'], not current)
                        if opt['key'] == 'muted':
                            audio_manager.muted = settings.get('muted')
                        audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)

        # Gamepad navigation
        dp = input_manager.get_dpad()
        if dp[1] == -1:  # Up
            selected = (selected - 1) % len(options)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        elif dp[1] == 1:  # Down
            selected = (selected + 1) % len(options)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        elif dp[0] != 0:  # Left/Right
            opt = options[selected]
            if opt['type'] == 'slider':
                delta = 10 if dp[0] > 0 else -10
                current = settings.get(opt['key'], 100)
                new_val = max(opt['min'], min(opt['max'], current + delta))
                settings.set(opt['key'], new_val)
            elif opt['type'] == 'toggle':
                current = settings.get(opt['key'], False)
                settings.set(opt['key'], not current)
                if opt['key'] == 'muted':
                    audio_manager.muted = settings.get('muted')
                audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)

        if input_manager.back_pressed():
            return

        if input_manager.action_pressed():
            opt = options[selected]
            if opt['type'] == 'toggle':
                current = settings.get(opt['key'], False)
                settings.set(opt['key'], not current)
                if opt['key'] == 'muted':
                    audio_manager.muted = settings.get('muted')
                audio_manager.play_sound(AudioManager.SOUND_MENU_SELECT)

        # Draw
        screen.fill(CUTE_BG_PRIMARY)

        # Title
        title = title_font.render("Settings", True, TITLE_COLOR)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 50))

        # Draw options
        y = 150
        for i, opt in enumerate(options):
            is_selected = (i == selected)
            color = WEASEL_BROWN if is_selected else (120, 100, 80)

            # Draw selection indicator
            if is_selected:
                indicator = font.render(">", True, WEASEL_BROWN)
                screen.blit(indicator, (150, y))

            # Draw label
            label = font.render(opt['label'] + ":", True, color)
            screen.blit(label, (180, y))

            # Draw value
            value = settings.get(opt['key'])
            if opt['type'] == 'slider':
                # Draw slider bar
                bar_x, bar_y = 350, y + 10
                bar_w, bar_h = 200, 16
                pygame.draw.rect(screen, (180, 160, 140), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
                fill_w = int(bar_w * (value / opt['max']))
                if fill_w > 0:
                    pygame.draw.rect(screen, WEASEL_BROWN, (bar_x, bar_y, fill_w, bar_h), border_radius=8)
                # Draw value text
                val_text = font.render(f"{value}%", True, color)
                screen.blit(val_text, (bar_x + bar_w + 20, y))
            elif opt['type'] == 'toggle':
                val_text = "ON" if value else "OFF"
                val_color = GREEN if value else RED
                rendered = font.render(val_text, True, val_color)
                screen.blit(rendered, (350, y))

            # Draw note if present
            if 'note' in opt:
                note = small_font.render(opt['note'], True, (150, 130, 110))
                screen.blit(note, (450, y + 5))

            y += 60

        # Controls help
        help_text = small_font.render("Up/Down: Navigate | Left/Right: Change | B/ESC: Back", True, (140, 120, 100))
        screen.blit(help_text, (WINDOW_WIDTH // 2 - help_text.get_width() // 2, WINDOW_HEIGHT - 80))

        # Control scheme display
        y = 350
        controls_title = font.render("Controls:", True, WEASEL_BROWN)
        screen.blit(controls_title, (180, y))
        y += 40
        controls = [
            "D-pad / Arrows: Move",
            "A / Enter / Space: Action / Confirm",
            "B / ESC: Back / Menu",
            "P / Start: Pause",
            "M: Toggle Mute",
        ]
        for ctrl in controls:
            ctrl_text = small_font.render(ctrl, True, (120, 100, 80))
            screen.blit(ctrl_text, (200, y))
            y += 28

        scale_to_screen()
        clock.tick(FPS)


def run_achievements_viewer(screen):
    """Display achievements viewer with progress and unlock status."""
    clock = pygame.time.Clock()
    input_manager = InputManager()
    audio_manager = get_audio_manager()
    achievements = get_achievement_manager()

    # Fonts
    title_font = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24)

    # Get all achievements
    all_achievements = achievements.get_all_achievements()

    # Group by game
    games = {'global': [], 'snake': [], 'pacman': [], 'frogger': [],
             'centipede': [], 'digdug': [], 'boulderdash': []}
    for ach in all_achievements:
        game = ach.get('game', 'global')
        if game in games:
            games[game].append(ach)

    # Flatten into display list with headers
    display_items = []
    game_names = {
        'global': 'Global',
        'snake': 'Snake',
        'pacman': 'Pac-Man',
        'frogger': 'Frogger',
        'centipede': 'Centipede',
        'digdug': 'Dig Dug',
        'boulderdash': 'Boulder Dash',
    }
    for game_id, game_name in game_names.items():
        if games[game_id]:
            display_items.append({'type': 'header', 'name': game_name})
            display_items.extend([{'type': 'achievement', **a} for a in games[game_id]])

    scroll_offset = 0
    max_visible = 10
    max_scroll = max(0, len(display_items) - max_visible)

    while True:
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE or e.key == pygame.K_a:
                    return
                if e.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - 1)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
                if e.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + 1)
                    audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)

        # Gamepad navigation
        if input_manager.back_pressed():
            return

        dp = input_manager.get_dpad()
        if dp[1] == -1:  # Up
            scroll_offset = max(0, scroll_offset - 1)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)
        elif dp[1] == 1:  # Down
            scroll_offset = min(max_scroll, scroll_offset + 1)
            audio_manager.play_sound(AudioManager.SOUND_MENU_MOVE)

        # Draw
        screen.fill(CUTE_BG_PRIMARY)

        # Title
        title = title_font.render("Achievements", True, TITLE_COLOR)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 30))

        # Progress
        unlocked, total = achievements.get_progress()
        progress_text = font.render(f"Unlocked: {unlocked}/{total}", True, WEASEL_BROWN)
        screen.blit(progress_text, (WINDOW_WIDTH // 2 - progress_text.get_width() // 2, 75))

        # Draw achievements list
        y = 120
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(display_items))):
            item = display_items[i]

            if item['type'] == 'header':
                # Section header
                header = font.render(item['name'], True, WEASEL_BROWN)
                screen.blit(header, (100, y))
                y += 40
            else:
                # Achievement
                is_unlocked = item.get('unlocked', False)

                # Background box
                box_color = (230, 220, 200) if is_unlocked else (200, 190, 180)
                pygame.draw.rect(screen, box_color, (100, y, 600, 40), border_radius=8)

                # Trophy icon
                if is_unlocked:
                    icon = font.render("*", True, (255, 215, 0))  # Gold star
                else:
                    icon = font.render("-", True, (150, 140, 130))  # Gray dash
                screen.blit(icon, (115, y + 8))

                # Achievement name
                name_color = WEASEL_BROWN if is_unlocked else (150, 140, 130)
                name = font.render(item['name'], True, name_color)
                screen.blit(name, (150, y + 5))

                # Description
                desc_color = (100, 90, 80) if is_unlocked else (160, 150, 140)
                desc = small_font.render(item['desc'], True, desc_color)
                screen.blit(desc, (350, y + 12))

                y += 45

        # Scroll indicators
        if scroll_offset > 0:
            up_indicator = font.render("^ More above ^", True, (140, 120, 100))
            screen.blit(up_indicator, (WINDOW_WIDTH // 2 - up_indicator.get_width() // 2, 105))
        if scroll_offset < max_scroll:
            down_indicator = font.render("v More below v", True, (140, 120, 100))
            screen.blit(down_indicator, (WINDOW_WIDTH // 2 - down_indicator.get_width() // 2, WINDOW_HEIGHT - 60))

        # Controls help
        help_text = small_font.render("Up/Down: Scroll | B/ESC: Back", True, (140, 120, 100))
        screen.blit(help_text, (WINDOW_WIDTH // 2 - help_text.get_width() // 2, WINDOW_HEIGHT - 35))

        scale_to_screen()
        clock.tick(FPS)


def run_stats_viewer(screen):
    """Display statistics viewer with gameplay data."""
    clock = pygame.time.Clock()
    input_manager = InputManager()
    audio_manager = get_audio_manager()
    stats = get_stats_manager()

    # Fonts
    title_font = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)

    # Build display data
    game_stats = [
        ('Global', 'global', [
            ('Total Play Time', lambda s: stats.format_play_time(s.get('global', 'total_play_time', 0))),
            ('Games Started', lambda s: str(s.get('global', 'games_started', 0))),
            ('Games Won', lambda s: str(s.get('global', 'games_completed', 0))),
        ]),
        ('Snake', 'snake', [
            ('Games Played', lambda s: str(s.get('snake', 'games_played', 0))),
            ('Total Score', lambda s: str(s.get('snake', 'total_score', 0))),
            ('Longest Snake', lambda s: str(s.get('snake', 'highest_length', 0))),
            ('Deaths', lambda s: str(s.get('snake', 'deaths', 0))),
        ]),
        ('Pac-Man', 'pacman', [
            ('Games Played', lambda s: str(s.get('pacman', 'games_played', 0))),
            ('Total Score', lambda s: str(s.get('pacman', 'total_score', 0))),
            ('Ghosts Eaten', lambda s: str(s.get('pacman', 'ghosts_eaten', 0))),
            ('Levels Cleared', lambda s: str(s.get('pacman', 'levels_cleared', 0))),
        ]),
        ('Frogger', 'frogger', [
            ('Games Played', lambda s: str(s.get('frogger', 'games_played', 0))),
            ('Crossings', lambda s: str(s.get('frogger', 'crossings', 0))),
            ('Deaths', lambda s: str(s.get('frogger', 'deaths', 0))),
        ]),
        ('Centipede', 'centipede', [
            ('Games Played', lambda s: str(s.get('centipede', 'games_played', 0))),
            ('Total Score', lambda s: str(s.get('centipede', 'total_score', 0))),
            ('Spiders Killed', lambda s: str(s.get('centipede', 'spiders_killed', 0))),
        ]),
        ('Dig Dug', 'digdug', [
            ('Games Played', lambda s: str(s.get('digdug', 'games_played', 0))),
            ('Crystals Collected', lambda s: str(s.get('digdug', 'crystals_collected', 0))),
            ('Wins', lambda s: str(s.get('digdug', 'wins', 0))),
        ]),
        ('Boulder Dash', 'boulderdash', [
            ('Games Played', lambda s: str(s.get('boulderdash', 'games_played', 0))),
            ('Diamonds Collected', lambda s: str(s.get('boulderdash', 'diamonds_collected', 0))),
            ('Levels Completed', lambda s: str(s.get('boulderdash', 'levels_completed', 0))),
        ]),
    ]

    scroll_offset = 0
    max_visible = 8
    total_items = sum(1 + len(items) for _, _, items in game_stats)
    max_scroll = max(0, total_items - max_visible)

    while True:
        input_manager.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE or e.key == pygame.K_x:
                    return
                if e.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - 1)
                if e.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + 1)

        # Gamepad navigation
        if input_manager.back_pressed():
            return

        dp = input_manager.get_dpad()
        if dp[1] == -1:  # Up
            scroll_offset = max(0, scroll_offset - 1)
        elif dp[1] == 1:  # Down
            scroll_offset = min(max_scroll, scroll_offset + 1)

        # Draw
        screen.fill(CUTE_BG_PRIMARY)

        # Title
        title = title_font.render("Statistics", True, TITLE_COLOR)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 30))

        # Build flat list of items to display
        display_items = []
        for game_name, game_id, stat_list in game_stats:
            display_items.append({'type': 'header', 'name': game_name})
            for stat_name, getter in stat_list:
                display_items.append({'type': 'stat', 'name': stat_name, 'value': getter(stats)})

        # Draw items
        y = 90
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(display_items))):
            item = display_items[i]

            if item['type'] == 'header':
                header = font.render(item['name'], True, WEASEL_BROWN)
                screen.blit(header, (100, y))
                y += 35
            else:
                # Stat row
                name = small_font.render(item['name'] + ":", True, (100, 90, 80))
                screen.blit(name, (130, y))
                value = small_font.render(item['value'], True, (80, 70, 60))
                screen.blit(value, (320, y))
                y += 28

        # Scroll indicators
        if scroll_offset > 0:
            up_ind = small_font.render("^ More above ^", True, (140, 120, 100))
            screen.blit(up_ind, (WINDOW_WIDTH // 2 - up_ind.get_width() // 2, 75))
        if scroll_offset < max_scroll:
            down_ind = small_font.render("v More below v", True, (140, 120, 100))
            screen.blit(down_ind, (WINDOW_WIDTH // 2 - down_ind.get_width() // 2, WINDOW_HEIGHT - 60))

        # Controls help
        help_text = small_font.render("Up/Down: Scroll | B/ESC: Back", True, (140, 120, 100))
        screen.blit(help_text, (WINDOW_WIDTH // 2 - help_text.get_width() // 2, WINDOW_HEIGHT - 35))

        scale_to_screen()
        clock.tick(FPS)


def _get_demo_ai_input(game, game_index, frame, ai_state):
    """Get AI input for demo mode based on game type.

    Args:
        game: The game instance
        game_index: Index of the game (0-5)
        frame: Current frame number
        ai_state: Dict to maintain AI state between frames

    Returns:
        Tuple of (direction, action_pressed) for this frame
    """
    import random

    # Initialize AI state if needed
    if 'direction' not in ai_state:
        ai_state['direction'] = (1, 0)
        ai_state['timer'] = 0
        ai_state['action_timer'] = 0

    direction = ai_state['direction']
    action = False
    ai_state['timer'] += 1
    ai_state['action_timer'] += 1

    # Game-specific AI behavior
    if game_index == 0:  # Snake
        # Change direction every 0.5-1.5 seconds, avoid reverse
        if ai_state['timer'] >= random.randint(30, 90):
            ai_state['timer'] = 0
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            opposite = (-direction[0], -direction[1])
            valid_dirs = [d for d in directions if d != opposite]
            direction = random.choice(valid_dirs)

    elif game_index == 1:  # Pac-Man
        # Change direction frequently to navigate maze
        if ai_state['timer'] >= random.randint(15, 45):
            ai_state['timer'] = 0
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            direction = random.choice(directions)

    elif game_index == 2:  # Frogger
        # Move forward mostly, occasional sideways
        if ai_state['timer'] >= random.randint(20, 60):
            ai_state['timer'] = 0
            # 60% chance forward, 20% left, 20% right
            r = random.random()
            if r < 0.6:
                direction = (0, -1)  # Forward (up)
            elif r < 0.8:
                direction = (-1, 0)  # Left
            else:
                direction = (1, 0)   # Right

    elif game_index == 3:  # Centipede
        # Move left/right at bottom, shoot frequently
        if ai_state['timer'] >= random.randint(10, 30):
            ai_state['timer'] = 0
            # Mostly horizontal movement
            if random.random() < 0.8:
                direction = (random.choice([-1, 1]), 0)
            else:
                direction = (0, random.choice([-1, 1]))
        # Shoot every 10-20 frames
        if ai_state['action_timer'] >= random.randint(10, 20):
            ai_state['action_timer'] = 0
            action = True

    elif game_index == 4:  # Dig Dug
        # Move in all directions to dig tunnels
        if ai_state['timer'] >= random.randint(20, 50):
            ai_state['timer'] = 0
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            direction = random.choice(directions)

    elif game_index == 5:  # Boulder Dash
        # Move in all directions, favor down and right
        if ai_state['timer'] >= random.randint(15, 40):
            ai_state['timer'] = 0
            # Slight bias toward exploring (down/right)
            directions = [(0, -1), (0, 1), (0, 1), (-1, 0), (1, 0), (1, 0)]
            direction = random.choice(directions)

    ai_state['direction'] = direction
    return direction, action


def run_attract_mode(screen):
    """Run attract/demo mode - shows AI or recorded demo playing a random game.

    Tries to use recorded demos first, falls back to AI control.
    Returns when any input is detected.
    """
    import random

    clock = pygame.time.Clock()
    input_manager_local = InputManager()
    demo_manager = get_demo_manager()

    # Pick a random game to demo
    game_index = random.randint(0, len(GAMES) - 1)
    game_name = GAMES[game_index]["name"]
    game_key = game_name.lower().replace(' ', '').replace('-', '')
    game_classes = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]

    # Create fonts for the overlay
    overlay_font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 28)

    # Create the game in demo mode (using Difficulty.EASY for smoother demo)
    game = game_classes[game_index](screen, input_manager_local, Difficulty.EASY)

    # Check if we have a recorded demo
    using_recorded_demo = demo_manager.has_demo(game_key)
    if using_recorded_demo:
        demo_manager.start_playback(game_key)

    # AI state for fallback
    ai_state = {}
    demo_frame = 0
    max_demo_frames = 15 * FPS  # 15 seconds

    while demo_frame < max_demo_frames:
        input_manager_local.update()

        # Check for any user input to exit demo
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if using_recorded_demo:
                    demo_manager.stop_playback()
                return True  # Signal to quit
            if e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                if using_recorded_demo:
                    demo_manager.stop_playback()
                return False  # Return to menu

        # Check gamepad input
        if input_manager_local.action_pressed() or input_manager_local.back_pressed():
            if using_recorded_demo:
                demo_manager.stop_playback()
            return False  # Return to menu

        dp = input_manager_local.get_dpad()
        if dp != (0, 0):
            if using_recorded_demo:
                demo_manager.stop_playback()
            return False  # Return to menu

        # Get input from demo or AI
        if using_recorded_demo:
            frame_data = demo_manager.get_playback_frame()
            if frame_data is None:
                # Demo ended, switch to AI
                using_recorded_demo = False
                demo_manager.stop_playback()
                ai_direction, ai_action = _get_demo_ai_input(game, game_index, demo_frame, ai_state)
            else:
                ai_direction = tuple(frame_data.get('dpad', [0, 0]))
                ai_action = frame_data.get('buttons', {}).get('action', False)
        else:
            ai_direction, ai_action = _get_demo_ai_input(game, game_index, demo_frame, ai_state)

        # Apply AI/demo input to game based on game type
        if game_index == 0:  # Snake
            if hasattr(game, 'next_direction'):
                game.next_direction = ai_direction
        elif game_index == 1:  # Pac-Man
            if hasattr(game, 'player_dir'):
                game.player_dir = ai_direction
        elif game_index == 2:  # Frogger
            # Frogger uses discrete movement, simulate via last_dpad
            if hasattr(game, 'last_dpad'):
                game.last_dpad = (0, 0)  # Reset to allow new movement
            if ai_direction != (0, 0) and hasattr(game, '_move_player'):
                game._move_player(ai_direction[0], ai_direction[1])
        elif game_index == 3:  # Centipede
            # Move player and fire
            if hasattr(game, 'player'):
                game.player.update(ai_direction[0], ai_direction[1])
            if ai_action and hasattr(game, '_fire'):
                game._fire()
        elif game_index == 4:  # Dig Dug
            # Store direction for movement
            if hasattr(game, 'last_dx'):
                game.last_dx = ai_direction[0]
                game.last_dy = ai_direction[1]
        elif game_index == 5:  # Boulder Dash
            # Boulder Dash uses discrete movement
            if hasattr(game, 'last_dpad'):
                game.last_dpad = (0, 0)
            if ai_direction != (0, 0) and hasattr(game, '_try_move'):
                game._try_move(ai_direction[1], ai_direction[0])

        # Update game
        dt = 1.0 / 60.0
        if hasattr(game, 'paused'):
            game.paused = False
        game.update(dt)

        # Render game
        game.render()

        # Draw "DEMO" overlay
        overlay = pygame.Surface((WINDOW_WIDTH, 80), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, WINDOW_HEIGHT - 80))

        # "DEMO MODE" text
        demo_text = overlay_font.render("DEMO MODE", True, (255, 255, 100))
        screen.blit(demo_text, (WINDOW_WIDTH // 2 - demo_text.get_width() // 2, WINDOW_HEIGHT - 70))

        # "Press any key to start" text (blinking)
        if (demo_frame // 30) % 2 == 0:
            start_text = small_font.render("Press any key to play!", True, (255, 255, 255))
            screen.blit(start_text, (WINDOW_WIDTH // 2 - start_text.get_width() // 2, WINDOW_HEIGHT - 35))

        # Game name in corner
        name_text = small_font.render(game_name, True, (200, 200, 200))
        screen.blit(name_text, (10, WINDOW_HEIGHT - 30))

        scale_to_screen()
        clock.tick(FPS)
        demo_frame += 1

    if using_recorded_demo:
        demo_manager.stop_playback()
    return False  # Return to menu after demo ends


def cleanup():
    """Clean shutdown handler - saves scores, settings, and cleans up pygame."""
    try:
        # Save any pending high scores
        score_mgr = get_score_manager()
        score_mgr.save()
    except Exception:
        pass  # Silently fail if score manager not initialized

    try:
        # Save any pending settings
        settings_mgr = get_settings_manager()
        settings_mgr.save()
    except Exception:
        pass  # Silently fail if settings manager not initialized

    try:
        pygame.quit()
    except Exception:
        pass  # Silently fail if pygame already quit


# Register cleanup handler for clean shutdown
atexit.register(cleanup)


def main():
    global _fullscreen_mode, _real_screen, _render_surface

    # Set up display mode based on command-line arguments
    if args.fullscreen:
        # Try to get native display resolution for fullscreen
        display_info = pygame.display.Info()
        _real_screen = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)  # Hide cursor in fullscreen
        # Create a render surface at game resolution - will be scaled to screen
        _render_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        screen = _render_surface
        _fullscreen_mode = True
        # Register the scale callback with the engine so games use it too
        set_scale_callback(_do_scale_to_screen)
    else:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        _real_screen = screen
        _render_surface = None
        _fullscreen_mode = False
    pygame.display.set_caption("Winston Entertainment System (WES)")

    # Run controller test if controller connected and 'T' pressed
    print("\nPress 'T' at the menu to test your controller mappings")

    game_classes = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]
    achievement_manager = get_achievement_manager()
    while True:
        ch = run_menu(screen)
        if ch is None: break
        if ch == -1:  # Controller test mode
            test_controller(screen)
            continue
        if ch == -2:  # Settings menu
            run_settings_menu(screen)
            continue
        if ch == -3:  # Achievements viewer
            run_achievements_viewer(screen)
            continue
        if ch == -4:  # Statistics viewer
            run_stats_viewer(screen)
            continue
        if ch == -5:  # Attract/demo mode
            should_quit = run_attract_mode(screen)
            if should_quit:
                break
            continue
        # Show difficulty selection
        difficulty = select_difficulty(screen, GAMES[ch]["name"], GAMES[ch]["color"])
        if difficulty is None:
            continue  # User cancelled, return to menu

        pygame.display.set_caption(GAMES[ch]["name"])
        game = game_classes[ch](screen, input_manager, difficulty)
        game.run()
        # Check global achievements after game ends
        achievement_manager.check_global_achievements()
        # Clear any pending events and reset input state after game exits
        # This prevents stale button presses from affecting the menu
        pygame.event.clear()
        input_manager.update()  # Capture current state
        input_manager.update()  # Clear edge detection (prev = curr)
        # Restore display mode after game exits
        if args.fullscreen:
            display_info = pygame.display.Info()
            _real_screen = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)
            _render_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            screen = _render_surface
        else:
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            _real_screen = screen
        # Clear events again after display mode change (can generate spurious events on some systems)
        pygame.event.clear()
        pygame.display.set_caption("Winston Entertainment System (WES)")
    pygame.quit(); sys.exit()

if __name__ == "__main__": main()
