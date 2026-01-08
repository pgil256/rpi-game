"""
Animated Ferret Sprite Module

A reusable animated sprite class for the ferret character, extracted and improved
from the WeaselAvatar class in game_launcher.py. Parses the ferret-long-sprite.png
sprite sheet using animation data from ferret-long-sprite.json.

Usage:
    import pygame
    from engine.ferret_sprite import AnimatedFerret

    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    # Create a ferret at position (400, 300) with 2x scale
    ferret = AnimatedFerret(x=400, y=300, scale=2)

    # In game loop:
    ferret.update(dx, dy)  # dx/dy are -1, 0, or 1 for direction
    ferret.draw(screen)
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

# Pygame may not be initialized when this module is imported
# We defer pygame operations to runtime methods
try:
    import pygame
except ImportError:
    pygame = None  # type: ignore


# =============================================================================
# CONSTANTS
# =============================================================================

# Default weasel/ferret color palette used for fallback rendering
FERRET_BROWN: Tuple[int, int, int] = (139, 90, 43)    # Primary body color
FERRET_TAN: Tuple[int, int, int] = (210, 180, 140)    # Secondary body color
FERRET_WHITE: Tuple[int, int, int] = (255, 248, 220)  # Underbelly/accent

# Sprite sheet configuration
FRAME_WIDTH: int = 32   # Width of each frame in pixels
FRAME_HEIGHT: int = 32  # Height of each frame in pixels
FRAMES_PER_ROW: int = 8 # Number of frames per animation row

# Animation state names matching the sprite sheet rows (top to bottom)
ANIMATION_STATES: Tuple[str, ...] = (
    'idle',       # Row 0: Default idle animation
    'idle2',      # Row 1: Alternate idle (e.g., looking around)
    'movement',   # Row 2: Walking/running animation
    'dig',        # Row 3: Digging animation
    'disappear',  # Row 4: Vanishing/hiding animation
    'jump',       # Row 5: Jumping animation
    'emerge',     # Row 6: Emerging from ground
    'sleep',      # Row 7: Sleeping animation
    'death',      # Row 8: Death animation
)


# =============================================================================
# ANIMATION DATA PARSER
# =============================================================================

def parse_animation_json(json_path: str) -> Dict[str, List[Dict]]:
    """
    Parse the Aseprite-exported JSON file to extract animation frame data.

    The JSON file contains frame coordinates and durations for each animation.
    Frame names follow the pattern: "Ferret Sprite Sheet (AnimName) N.ase"
    where AnimName is the animation name and N is the frame index.

    Args:
        json_path: Path to the ferret-long-sprite.json file

    Returns:
        Dictionary mapping animation names (lowercase) to lists of frame data.
        Each frame data dict contains: x, y, w, h, duration

    Example:
        {
            'idle': [
                {'x': 0, 'y': 0, 'w': 32, 'h': 32, 'duration': 100},
                {'x': 32, 'y': 0, 'w': 32, 'h': 32, 'duration': 100},
                ...
            ],
            'movement': [...],
            ...
        }
    """
    animations: Dict[str, List[Dict]] = {}

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse animation JSON: {e}")
        return animations

    frames = data.get('frames', {})

    for frame_name, frame_data in frames.items():
        # Parse frame name: "Ferret Sprite Sheet (AnimName) N.ase"
        # Extract the animation name from between parentheses
        try:
            # Find content between parentheses
            start = frame_name.find('(')
            end = frame_name.find(')')
            if start == -1 or end == -1:
                continue

            anim_name = frame_name[start + 1:end].lower()

            # Extract frame rect and duration from JSON
            frame_rect = frame_data.get('frame', {})
            frame_info = {
                'x': frame_rect.get('x', 0),
                'y': frame_rect.get('y', 0),
                'w': frame_rect.get('w', FRAME_WIDTH),
                'h': frame_rect.get('h', FRAME_HEIGHT),
                'duration': frame_data.get('duration', 100)  # ms per frame
            }

            # Add to animations dict
            if anim_name not in animations:
                animations[anim_name] = []
            animations[anim_name].append(frame_info)

        except (ValueError, KeyError):
            continue

    # Sort frames by x position within each animation (ensures correct order)
    # Frames in the same row have the same y, so sorting by x gives frame order
    for anim_name in animations:
        animations[anim_name].sort(key=lambda f: (f['y'], f['x']))

    return animations


# =============================================================================
# ANIMATED FERRET CLASS
# =============================================================================

class AnimatedFerret:
    """
    A reusable animated ferret sprite with multiple animation states.

    This class handles:
    - Loading and parsing the sprite sheet from ferret-long-sprite.png
    - Automatic animation state transitions based on movement
    - Horizontal sprite flipping based on facing direction
    - Configurable scale, position, and animation speed
    - Robust fallback rendering if sprite loading fails

    Animation States:
        - idle: Default standing animation
        - idle2: Alternate idle (used after extended idle time)
        - movement: Walking/running (used when moving)
        - dig: Digging animation
        - disappear: Vanishing animation
        - jump: Jumping animation
        - emerge: Emerging from ground
        - sleep: Sleeping animation (used after very long idle)
        - death: Death animation

    Attributes:
        x (float): Current x position (center of sprite)
        y (float): Current y position (center of sprite)
        scale (int): Scale multiplier for sprite size (default 2)
        speed (float): Movement speed in pixels per update
        facing_right (bool): True if ferret is facing right
        state (str): Current animation state name

    Example:
        ferret = AnimatedFerret(x=100, y=200, scale=2, speed=4.0)

        # In game loop:
        dx, dy = get_input()  # -1, 0, or 1
        ferret.update(dx, dy)
        ferret.draw(screen)

        # Change to specific state:
        ferret.set_state('jump')
    """

    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        scale: int = 2,
        speed: float = 4.0,
        frame_delay: int = 6,
        sprite_path: Optional[str] = None,
        json_path: Optional[str] = None,
        enable_sleep: bool = False,
    ) -> None:
        """
        Initialize the animated ferret sprite.

        Args:
            x: Initial x position (center of sprite)
            y: Initial y position (center of sprite)
            scale: Scale multiplier for sprite size (1 = 32x32 pixels)
            speed: Movement speed in pixels per update call
            frame_delay: Number of update() calls between animation frames.
                        Lower = faster animation. At 60 FPS, delay of 6 = 10 FPS animation.
            sprite_path: Optional custom path to sprite sheet PNG.
                        If None, searches in ../media/ relative to this file.
            json_path: Optional custom path to animation JSON.
                      If None, searches in ../media/ relative to this file.
            enable_sleep: If True, enables automatic transition to 'sleep' state
                         after extended idle. If False (default), the maximum
                         automatic idle state is 'idle2'. Sleep is reserved for
                         menu contexts where extended AFK detection is desired.
        """
        # Position and movement
        self.x: float = x
        self.y: float = y
        self.speed: float = speed
        self.facing_right: bool = True

        # Current movement direction (set by update())
        self._dx: int = 0
        self._dy: int = 0

        # Animation state
        self._state: str = 'idle'
        self._frame: int = 0
        self._frame_timer: int = 0
        self._frame_delay: int = frame_delay
        self._idle_timer: int = 0
        self._is_moving: bool = False
        self._enable_sleep: bool = enable_sleep

        # Sprite configuration
        self.scale: int = scale
        self._sprite_size: int = FRAME_WIDTH * scale

        # Sprite sheet and animations storage
        # Each animation is a list of pygame.Surface objects (scaled frames)
        self._sprite_sheet: Optional[pygame.Surface] = None
        self._animations: Dict[str, List[pygame.Surface]] = {}
        self._animations_flipped: Dict[str, List[pygame.Surface]] = {}  # Cached flipped sprites
        self._animation_data: Dict[str, List[Dict]] = {}
        self._sprites_loaded: bool = False

        # Determine paths to sprite assets
        self._sprite_path = sprite_path
        self._json_path = json_path
        if self._sprite_path is None or self._json_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            media_dir = os.path.join(base_dir, 'media')
            if self._sprite_path is None:
                self._sprite_path = os.path.join(media_dir, 'ferret-long-sprite.png')
            if self._json_path is None:
                self._json_path = os.path.join(media_dir, 'ferret-long-sprite.json')

        # Load sprites (deferred until pygame is available)
        self._load_sprites()

    def _load_sprites(self) -> None:
        """
        Load and parse the ferret sprite sheet.

        This method:
        1. Parses the JSON file to get frame coordinates and durations
        2. Loads the sprite sheet PNG
        3. Extracts each frame as a subsurface
        4. Scales frames according to self.scale
        5. Stores frames organized by animation name

        If loading fails, creates fallback colored ellipse sprites.
        """
        if pygame is None:
            print("Warning: pygame not available, sprites will use fallback")
            self._create_fallback_sprites()
            return

        try:
            # Parse the JSON animation data first
            # This gives us precise frame coordinates and durations
            self._animation_data = parse_animation_json(self._json_path)

            # Load the sprite sheet image
            self._sprite_sheet = pygame.image.load(self._sprite_path).convert_alpha()

            # Extract frames for each animation using JSON data
            if self._animation_data:
                self._load_frames_from_json()
            else:
                # Fallback: load using hardcoded row positions (original approach)
                self._load_frames_hardcoded()

            self._sprites_loaded = True

        except (pygame.error, FileNotFoundError, OSError) as e:
            print(f"Warning: Failed to load ferret sprites: {e}")
            self._create_fallback_sprites()

    def _load_frames_from_json(self) -> None:
        """
        Extract animation frames using coordinates from the JSON file.

        Uses the parsed animation data to precisely extract each frame
        from the sprite sheet, then scales to the configured size.
        Also creates pre-flipped versions for left-facing sprites.
        """
        if self._sprite_sheet is None:
            return

        for anim_name, frames_data in self._animation_data.items():
            frames: List[pygame.Surface] = []
            frames_flipped: List[pygame.Surface] = []

            for frame_info in frames_data:
                # Extract frame rect from sprite sheet
                rect = pygame.Rect(
                    frame_info['x'],
                    frame_info['y'],
                    frame_info['w'],
                    frame_info['h']
                )

                # Get subsurface and scale it
                try:
                    frame_surface = self._sprite_sheet.subsurface(rect)
                    scaled = pygame.transform.scale(
                        frame_surface,
                        (self._sprite_size, self._sprite_size)
                    )
                    frames.append(scaled)
                    # Pre-create flipped version to avoid per-frame flip
                    frames_flipped.append(pygame.transform.flip(scaled, True, False))
                except ValueError as e:
                    # Invalid rect, skip this frame
                    print(f"Warning: Could not extract frame for {anim_name}: {e}")
                    continue

            if frames:
                self._animations[anim_name] = frames
                self._animations_flipped[anim_name] = frames_flipped

    def _load_frames_hardcoded(self) -> None:
        """
        Fallback frame loading using hardcoded row positions.

        Used when JSON parsing fails. Assumes standard layout:
        - 9 rows of animations (matching ANIMATION_STATES)
        - 8 frames per row
        - 32x32 pixels per frame
        Also creates pre-flipped versions for left-facing sprites.
        """
        if self._sprite_sheet is None:
            return

        # Animation row y-offsets (32 pixels per row)
        for row_index, anim_name in enumerate(ANIMATION_STATES):
            y_offset = row_index * FRAME_HEIGHT
            frames: List[pygame.Surface] = []
            frames_flipped: List[pygame.Surface] = []

            for frame_index in range(FRAMES_PER_ROW):
                x_offset = frame_index * FRAME_WIDTH
                rect = pygame.Rect(x_offset, y_offset, FRAME_WIDTH, FRAME_HEIGHT)

                try:
                    frame_surface = self._sprite_sheet.subsurface(rect)
                    scaled = pygame.transform.scale(
                        frame_surface,
                        (self._sprite_size, self._sprite_size)
                    )
                    frames.append(scaled)
                    # Pre-create flipped version to avoid per-frame flip
                    frames_flipped.append(pygame.transform.flip(scaled, True, False))
                except ValueError:
                    continue

            if frames:
                self._animations[anim_name] = frames
                self._animations_flipped[anim_name] = frames_flipped

    def _create_fallback_sprites(self) -> None:
        """
        Create simple colored ellipse sprites as fallback when loading fails.

        Creates a basic brown ellipse for each animation state.
        This ensures the game can still run even without the sprite sheet.
        Also creates pre-flipped versions for left-facing sprites.
        """
        if pygame is None:
            return

        fallback = self._make_fallback_surface()
        fallback_flipped = pygame.transform.flip(fallback, True, False)

        # Create minimal fallback animations
        # At minimum need 'idle' and 'movement'
        for anim_name in ('idle', 'idle2', 'movement', 'dig', 'disappear',
                          'jump', 'emerge', 'sleep', 'death'):
            self._animations[anim_name] = [fallback]
            self._animations_flipped[anim_name] = [fallback_flipped]

        self._sprites_loaded = True

    def _make_fallback_surface(self) -> pygame.Surface:
        """
        Create a single fallback sprite surface.

        Returns:
            A pygame.Surface with a colored ellipse representing the ferret.
        """
        if pygame is None:
            raise RuntimeError("pygame not initialized")

        surf = pygame.Surface(
            (self._sprite_size, self._sprite_size),
            pygame.SRCALPHA
        )
        # Draw ferret-colored ellipse
        pygame.draw.ellipse(surf, FERRET_BROWN, surf.get_rect())
        # Add a small eye detail
        eye_size = max(2, self._sprite_size // 16)
        eye_x = self._sprite_size * 3 // 4
        eye_y = self._sprite_size // 3
        pygame.draw.circle(surf, (0, 0, 0), (eye_x, eye_y), eye_size)
        return surf

    @property
    def state(self) -> str:
        """Get the current animation state name."""
        return self._state

    def set_state(self, state: str, reset_frame: bool = True) -> None:
        """
        Manually set the animation state.

        Use this for special animations like 'death', 'jump', 'dig', etc.
        The automatic state machine (idle/movement) will resume when
        update() is called with movement input.

        Args:
            state: Animation state name. Must be one of:
                   'idle', 'idle2', 'movement', 'dig', 'disappear',
                   'jump', 'emerge', 'sleep', 'death'
            reset_frame: If True, restart animation from frame 0.
                        If False, continue from current frame.

        Raises:
            ValueError: If state name is not recognized.
        """
        if state not in self._animations and state not in ANIMATION_STATES:
            valid = ', '.join(ANIMATION_STATES)
            raise ValueError(f"Unknown animation state '{state}'. Valid states: {valid}")

        self._state = state
        if reset_frame:
            self._frame = 0
            self._frame_timer = 0

    def update(self, dx: int = 0, dy: int = 0) -> None:
        """
        Update ferret position and animation based on input direction.

        This method should be called once per game frame. It handles:
        - Moving the ferret based on dx/dy direction
        - Updating facing direction for sprite flipping
        - Advancing animation frames
        - Automatic state transitions (idle <-> movement)

        Args:
            dx: Horizontal direction (-1 = left, 0 = none, 1 = right)
            dy: Vertical direction (-1 = up, 0 = none, 1 = down)

        The automatic state machine:
        - Moving (dx or dy != 0) -> 'movement' state
        - Stopped for < 5 seconds -> 'idle' state
        - Stopped for > 5 seconds -> 'idle2' state

        Note: Sleep state is NOT automatically triggered by update().
        Use set_state('sleep') explicitly in menu/launcher code after
        extended idle periods. Games should not use sleep animation.
        """
        self._dx = dx
        self._dy = dy

        # Update position based on direction and speed
        if dx != 0 or dy != 0:
            self._is_moving = True
            self._idle_timer = 0

            # Move in the specified direction
            self.x += dx * self.speed
            self.y += dy * self.speed

            # Update facing direction (only horizontal matters for flipping)
            if dx > 0:
                self.facing_right = True
            elif dx < 0:
                self.facing_right = False
        else:
            self._is_moving = False
            self._idle_timer += 1

        # Automatic state transitions based on movement
        # Only override state if not in a "special" animation
        special_states = {'dig', 'disappear', 'jump', 'emerge', 'death'}
        if self._state not in special_states:
            if self._is_moving:
                if self._state != 'movement':
                    self.set_state('movement')
            else:
                # Progressive idle states based on idle time
                # Assuming 60 FPS: 300 frames = 5 sec
                # Sleep transition only occurs if enable_sleep=True
                # When enable_sleep=False (default), idle2 is the maximum auto state
                if self._idle_timer > 300:
                    if self._state != 'idle2':
                        self.set_state('idle2', reset_frame=False)
                else:
                    if self._state not in ('idle', 'idle2'):
                        self.set_state('idle')

        # Advance animation frame
        self._advance_animation()

    def _advance_animation(self) -> None:
        """
        Advance to the next animation frame based on frame delay.

        The frame advances every self._frame_delay update() calls.
        When the last frame is reached, the animation loops back to frame 0.
        """
        self._frame_timer += 1

        if self._frame_timer >= self._frame_delay:
            self._frame_timer = 0

            # Get current animation frame list
            anim_frames = self._get_current_animation()
            num_frames = len(anim_frames)

            if num_frames > 0:
                self._frame = (self._frame + 1) % num_frames

    def _get_current_animation(self) -> List[pygame.Surface]:
        """
        Get the frame list for the current animation state.

        Returns:
            List of pygame.Surface objects for the current animation.
            Falls back to 'idle' if current state not found.
        """
        # Try to get the current state's animation
        if self._state in self._animations:
            return self._animations[self._state]

        # Fallback chain: idle2 -> idle, movement -> idle
        if 'idle' in self._animations:
            return self._animations['idle']

        # Last resort: return any available animation
        for anim in self._animations.values():
            if anim:
                return anim

        return []

    def _get_current_animation_flipped(self) -> List[pygame.Surface]:
        """
        Get the pre-flipped frame list for the current animation state.

        Returns:
            List of horizontally flipped pygame.Surface objects for the current animation.
            Falls back to 'idle' if current state not found.
        """
        # Try to get the current state's flipped animation
        if self._state in self._animations_flipped:
            return self._animations_flipped[self._state]

        # Fallback chain: idle2 -> idle, movement -> idle
        if 'idle' in self._animations_flipped:
            return self._animations_flipped['idle']

        # Last resort: return any available flipped animation
        for anim in self._animations_flipped.values():
            if anim:
                return anim

        return []

    def get_image(self) -> Optional[pygame.Surface]:
        """
        Get the current animation frame as a pygame Surface.

        The returned surface is already flipped horizontally if the
        ferret is facing left. Uses pre-cached flipped sprites for
        optimal performance (no per-frame surface creation).

        Returns:
            The current frame surface, or None if no sprites loaded.
        """
        # Use the appropriate animation dict based on facing direction
        if self.facing_right:
            anim_frames = self._get_current_animation()
        else:
            anim_frames = self._get_current_animation_flipped()

        if not anim_frames:
            return None

        # Get current frame (safely handle frame index overflow)
        frame_index = self._frame % len(anim_frames)
        return anim_frames[frame_index]

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draw the ferret sprite to a surface at its current position.

        The sprite is drawn centered on (self.x, self.y).
        Handles horizontal flipping based on facing direction.

        Args:
            surface: The pygame surface to draw on (usually the screen).

        Example:
            ferret.draw(screen)
        """
        sprite = self.get_image()
        if sprite is None:
            return

        # Draw centered on position
        rect = sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(sprite, rect)

    def get_rect(self) -> pygame.Rect:
        """
        Get the ferret's bounding rectangle for collision detection.

        The rect is centered on the ferret's position.

        Returns:
            A pygame.Rect representing the ferret's bounds.

        Example:
            if ferret.get_rect().colliderect(enemy.rect):
                handle_collision()
        """
        return pygame.Rect(
            int(self.x - self._sprite_size // 2),
            int(self.y - self._sprite_size // 2),
            self._sprite_size,
            self._sprite_size
        )

    def set_position(self, x: float, y: float) -> None:
        """
        Set the ferret's position directly.

        Args:
            x: New x position (center of sprite)
            y: New y position (center of sprite)
        """
        self.x = x
        self.y = y

    def clamp_to_bounds(
        self,
        min_x: float = 0,
        min_y: float = 0,
        max_x: Optional[float] = None,
        max_y: Optional[float] = None,
    ) -> None:
        """
        Constrain the ferret's position within given bounds.

        Useful for keeping the ferret within screen/play area boundaries.
        The bounds apply to the sprite's center position, adjusted for
        the sprite's half-size so the sprite stays fully visible.

        Args:
            min_x: Minimum x position (left edge). Default 0.
            min_y: Minimum y position (top edge). Default 0.
            max_x: Maximum x position (right edge). If None, no limit.
            max_y: Maximum y position (bottom edge). If None, no limit.

        Example:
            # Keep ferret within 800x600 window
            ferret.clamp_to_bounds(0, 0, 800, 600)
        """
        half_size = self._sprite_size // 2

        # Clamp x position
        self.x = max(min_x + half_size, self.x)
        if max_x is not None:
            self.x = min(max_x - half_size, self.x)

        # Clamp y position
        self.y = max(min_y + half_size, self.y)
        if max_y is not None:
            self.y = min(max_y - half_size, self.y)

    def reset_animation(self) -> None:
        """Reset animation to frame 0 of current state."""
        self._frame = 0
        self._frame_timer = 0

    def reset_idle_timer(self) -> None:
        """Reset the idle timer (prevents automatic idle2/sleep transitions)."""
        self._idle_timer = 0

    @property
    def sprite_size(self) -> int:
        """Get the actual pixel size of the sprite (after scaling)."""
        return self._sprite_size

    @sprite_size.setter
    def sprite_size(self, size: int) -> None:
        """Set the sprite display size.

        Args:
            size: New pixel size for the sprite (width and height).
        """
        self._sprite_size = size

    def set_sprite_size(self, size: int) -> None:
        """Set the sprite display size (method form for compatibility).

        Args:
            size: New pixel size for the sprite (width and height).
        """
        self._sprite_size = size

    @property
    def is_moving(self) -> bool:
        """Check if the ferret is currently moving."""
        return self._is_moving

    @property
    def current_frame(self) -> int:
        """Get the current animation frame index."""
        return self._frame

    @property
    def animation_states(self) -> Tuple[str, ...]:
        """Get tuple of all available animation state names."""
        return ANIMATION_STATES

    def get_available_animations(self) -> List[str]:
        """
        Get list of animations that were successfully loaded.

        Returns:
            List of animation state names that have frames loaded.
        """
        return list(self._animations.keys())


# =============================================================================
# MODULE-LEVEL TESTING
# =============================================================================

if __name__ == '__main__':
    """
    Standalone test mode - run this file directly to test the AnimatedFerret class.

    Usage:
        python engine/ferret_sprite.py

    Controls:
        Arrow keys: Move ferret
        1-9: Switch animation states
        ESC: Exit
    """
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("AnimatedFerret Test")
    clock = pygame.time.Clock()

    # Create ferret in center of screen
    ferret = AnimatedFerret(x=400, y=300, scale=3, speed=5.0)

    print("AnimatedFerret Test Mode")
    print("=" * 40)
    print(f"Sprite size: {ferret.sprite_size}x{ferret.sprite_size}")
    print(f"Available animations: {ferret.get_available_animations()}")
    print()
    print("Controls:")
    print("  Arrow keys: Move")
    print("  1-9: Switch animation state")
    print("  ESC: Exit")

    # Map number keys to animation states
    state_keys = {
        pygame.K_1: 'idle',
        pygame.K_2: 'idle2',
        pygame.K_3: 'movement',
        pygame.K_4: 'dig',
        pygame.K_5: 'disappear',
        pygame.K_6: 'jump',
        pygame.K_7: 'emerge',
        pygame.K_8: 'sleep',
        pygame.K_9: 'death',
    }

    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in state_keys:
                    try:
                        ferret.set_state(state_keys[event.key])
                        print(f"State: {ferret.state}")
                    except ValueError as e:
                        print(f"Error: {e}")

        # Get movement input
        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]

        # Update ferret
        ferret.update(dx, dy)
        ferret.clamp_to_bounds(0, 0, 800, 600)

        # Render
        screen.fill((101, 67, 33))  # Burrow brown background
        ferret.draw(screen)

        # Draw info text
        font = pygame.font.Font(None, 24)
        info_lines = [
            f"State: {ferret.state}",
            f"Frame: {ferret.current_frame}",
            f"Position: ({ferret.x:.0f}, {ferret.y:.0f})",
            f"Facing: {'Right' if ferret.facing_right else 'Left'}",
        ]
        for i, line in enumerate(info_lines):
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (10, 10 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
