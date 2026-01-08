"""Centralized asset loading with caching for the Weasel Entertainment System.

Includes LRU cache management, platform-aware optimizations, and
game-specific asset loading/unloading for memory efficiency.
"""

import os
import sys
import platform
from collections import OrderedDict
from typing import Optional, Tuple, Dict, Set
import pygame


# Note: Color constants are defined in engine/__init__.py
# Import them if needed within this module, but they're primarily
# for external use. We keep local references for fallback surfaces.
WEASEL_BROWN = (139, 90, 43)      # Brown for head/front
WEASEL_TAN = (210, 180, 140)      # Tan/cream for body
WEASEL_WHITE = (255, 248, 220)    # Cream white for underbelly
BURROW_BROWN = (101, 67, 33)      # Dark earthy brown for background

# Platform detection
def detect_platform() -> str:
    """Detect the current platform for optimization hints.

    Returns:
        One of: 'raspberry_pi', 'linux', 'windows', 'macos', 'unknown'
    """
    system = platform.system().lower()

    if system == 'linux':
        # Check for Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                if 'raspberry' in cpuinfo or 'bcm' in cpuinfo:
                    return 'raspberry_pi'
        except (IOError, OSError):
            pass
        return 'linux'
    elif system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    return 'unknown'


# Default cache limits based on platform
def get_default_cache_limit() -> int:
    """Get the default cache limit based on platform.

    Returns smaller limits on resource-constrained platforms like RPi.
    """
    plat = detect_platform()
    if plat == 'raspberry_pi':
        return 50  # Smaller cache for RPi
    return 100  # Default for desktop


# Game asset paths for lazy loading
GAME_ASSET_PATHS = {
    'snake': [],  # Snake uses procedural graphics
    'pacman': ['soupcan_new.png', 'soupbowl.png'],
    'frogger': ['ferret-long-sprite.png'],
    'centipede': [],  # Centipede uses procedural graphics
    'digdug': ['ferret-long-sprite.png'],
    'boulderdash': [
        'games/boulder-dash/images/',  # Directory prefix
    ],
}


def get_weasel_color(index: int) -> Tuple[int, int, int]:
    """Get weasel color for segment based on index (0=head/front).

    Args:
        index: Segment index, 0 is head/front.

    Returns:
        RGB tuple for the segment color.
    """
    if index == 0:
        return WEASEL_BROWN
    elif index == 1:
        return WEASEL_TAN
    elif index == 2:
        return WEASEL_WHITE
    else:
        return WEASEL_TAN  # Repeating tans


class AssetLoader:
    """Centralized asset loading with caching and fallback support.

    Handles loading images and sounds from the media/ directory with:
    - Automatic path resolution relative to project root
    - LRU caching with configurable size limit to avoid redundant disk reads
    - Automatic surface.convert()/convert_alpha() for optimal blitting
    - Optional integer scaling for pixel art
    - Graceful fallbacks when files are missing
    - Game-specific asset preloading and unloading
    - Platform-aware optimizations
    - Optional debug logging for missing assets
    """

    # Class-level debug mode flag
    debug_mode: bool = False

    @classmethod
    def set_debug_mode(cls, enabled: bool) -> None:
        """Enable or disable debug logging for missing assets.

        Args:
            enabled: If True, prints warnings when assets fail to load.
        """
        cls.debug_mode = enabled

    def __init__(self, base_dir: Optional[str] = None, cache_limit: Optional[int] = None):
        """Initialize the asset loader.

        Args:
            base_dir: Base directory for the project. If None, auto-detects
                     from the location of game_launcher.py or uses cwd.
            cache_limit: Maximum number of images to keep in cache.
                        If None, uses platform-specific default.
        """
        if base_dir is None:
            # Try to find the project root by looking for media/ directory
            check_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if os.path.isdir(os.path.join(check_dir, 'media')):
                base_dir = check_dir
            else:
                base_dir = os.getcwd()

        self.base_dir = base_dir
        self.media_dir = os.path.join(base_dir, 'media')

        # LRU caches using OrderedDict (last accessed items at end)
        self._image_cache: OrderedDict[str, pygame.Surface] = OrderedDict()
        self._sound_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}

        # Cache limit (0 = unlimited)
        self._cache_limit = cache_limit if cache_limit is not None else get_default_cache_limit()

        # Track which assets belong to which game for unloading
        self._game_assets: Dict[str, Set[str]] = {}
        self._current_game: Optional[str] = None

        # Platform info
        self.platform = detect_platform()

        # Track if audio is available
        self._audio_available = pygame.mixer.get_init() is not None

    def _evict_lru(self) -> None:
        """Evict the least recently used item from cache if over limit."""
        if self._cache_limit > 0 and len(self._image_cache) >= self._cache_limit:
            # Remove oldest item (first in OrderedDict)
            oldest_key = next(iter(self._image_cache))
            del self._image_cache[oldest_key]
            if self.debug_mode:
                print(f"[AssetLoader] Evicted from cache: {oldest_key}")

    def _mark_used(self, cache_key: str) -> None:
        """Mark a cache entry as recently used (moves to end of OrderedDict)."""
        if cache_key in self._image_cache:
            self._image_cache.move_to_end(cache_key)

    def _track_game_asset(self, cache_key: str) -> None:
        """Track an asset as belonging to the current game."""
        if self._current_game:
            if self._current_game not in self._game_assets:
                self._game_assets[self._current_game] = set()
            self._game_assets[self._current_game].add(cache_key)

    def set_current_game(self, game_name: Optional[str]) -> None:
        """Set the current game for asset tracking.

        Args:
            game_name: Name of the game (e.g., 'snake', 'pacman'), or None.
        """
        self._current_game = game_name

    def load_image(
        self,
        filename: str,
        size: Optional[Tuple[int, int]] = None,
        use_integer_scaling: bool = True,
        preserve_aspect: bool = False,
        has_alpha: bool = True
    ) -> Optional[pygame.Surface]:
        """Load an image from the media directory with optional scaling.

        Args:
            filename: Image filename within the media/ directory.
            size: Optional (width, height) tuple to scale the image to.
            use_integer_scaling: If True and size is provided, uses nearest
                                neighbor scaling to preserve pixel art crispness.
            preserve_aspect: If True, scales to fit within size while preserving
                            aspect ratio (image may be smaller than size).
            has_alpha: If True, uses convert_alpha() for transparency support.
                      If False, uses convert() for faster opaque blitting.

        Returns:
            The loaded pygame Surface, or None if loading failed.
        """
        # Create cache key from filename and size
        cache_key = f"{filename}|{size}|{use_integer_scaling}|{preserve_aspect}|{has_alpha}"

        if cache_key in self._image_cache:
            # Move to end (mark as recently used)
            self._mark_used(cache_key)
            return self._image_cache[cache_key]

        try:
            path = os.path.join(self.media_dir, filename)
            raw_img = pygame.image.load(path)

            # Convert for optimal blitting performance
            if has_alpha:
                img = raw_img.convert_alpha()
            else:
                img = raw_img.convert()

            if size:
                if preserve_aspect:
                    # Scale to fit within size while preserving aspect ratio
                    orig_w, orig_h = img.get_size()
                    target_w, target_h = size
                    scale_w = target_w / orig_w
                    scale_h = target_h / orig_h
                    scale = min(scale_w, scale_h)
                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    new_size = (new_w, new_h)
                else:
                    new_size = size

                if use_integer_scaling:
                    # Use NEAREST for crisp pixel art scaling
                    img = pygame.transform.scale(img, new_size)
                    # Note: pygame.transform.scale uses nearest neighbor by default
                    # for pixel-perfect results with small sprites
                else:
                    # Use smooth scaling for non-pixel art
                    img = pygame.transform.smoothscale(img, new_size)

            # Evict LRU item if cache is full
            self._evict_lru()

            # Store in cache and track for current game
            self._image_cache[cache_key] = img
            self._track_game_asset(cache_key)

            return img

        except (pygame.error, FileNotFoundError, OSError) as e:
            if self.debug_mode:
                print(f"[AssetLoader] Warning: Failed to load image '{filename}': {e}")
            return None

    def create_fallback_surface(
        self,
        size: Tuple[int, int],
        color: Tuple[int, int, int],
        with_border: bool = False,
        border_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> pygame.Surface:
        """Create a colored fallback surface when an image is unavailable.

        Args:
            size: (width, height) of the surface.
            color: RGB fill color.
            with_border: If True, adds a 1-pixel border.
            border_color: RGB color for the border.

        Returns:
            A new pygame Surface filled with the specified color.
        """
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)

        if with_border:
            pygame.draw.rect(surface, border_color, surface.get_rect(), 1)

        return surface

    def load_image_or_fallback(
        self,
        filename: str,
        size: Tuple[int, int],
        fallback_color: Tuple[int, int, int],
        use_integer_scaling: bool = True,
        with_border: bool = False
    ) -> pygame.Surface:
        """Load an image with automatic fallback to a colored surface.

        Args:
            filename: Image filename within the media/ directory.
            size: (width, height) for both image and fallback.
            fallback_color: RGB color to use if image loading fails.
            use_integer_scaling: If True, uses nearest neighbor scaling.
            with_border: If True, adds border to fallback surface.

        Returns:
            The loaded image or a fallback colored surface.
        """
        img = self.load_image(filename, size, use_integer_scaling)
        if img is not None:
            return img
        return self.create_fallback_surface(size, fallback_color, with_border)

    def load_sprite_sheet(
        self,
        filename: str,
        frame_size: Tuple[int, int],
        frame_names: Dict[str, Tuple[int, int]],
        scale: Optional[int] = None
    ) -> Dict[str, pygame.Surface]:
        """Load a sprite sheet and extract named subsurfaces.

        Args:
            filename: Sprite sheet filename within the media/ directory.
            frame_size: (width, height) of each frame in the sheet.
            frame_names: Dict mapping names to (col, row) grid positions.
                        Example: {"idle": (0, 0), "walk1": (1, 0), "walk2": (2, 0)}
            scale: Optional integer scale factor (e.g., 2 for 2x size).

        Returns:
            Dict mapping frame names to pygame Surfaces.
            Returns empty dict if sprite sheet loading fails.
        """
        sprites: Dict[str, pygame.Surface] = {}

        # Load the full sprite sheet (uncached, we cache individual frames)
        try:
            path = os.path.join(self.media_dir, filename)
            sheet = pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            return sprites

        frame_w, frame_h = frame_size

        for name, (col, row) in frame_names.items():
            x = col * frame_w
            y = row * frame_h

            # Extract the subsurface
            try:
                frame = sheet.subsurface((x, y, frame_w, frame_h)).copy()

                if scale and scale > 1:
                    new_size = (frame_w * scale, frame_h * scale)
                    frame = pygame.transform.scale(frame, new_size)

                sprites[name] = frame

            except ValueError:
                # Subsurface out of bounds
                continue

        return sprites

    def load_sprite_sheet_grid(
        self,
        filename: str,
        frame_size: Tuple[int, int],
        cols: int,
        rows: int,
        scale: Optional[int] = None
    ) -> list:
        """Load a sprite sheet as a flat list of frames in row-major order.

        Args:
            filename: Sprite sheet filename within the media/ directory.
            frame_size: (width, height) of each frame in the sheet.
            cols: Number of columns in the sprite sheet.
            rows: Number of rows in the sprite sheet.
            scale: Optional integer scale factor.

        Returns:
            List of pygame Surfaces in row-major order.
            Returns empty list if sprite sheet loading fails.
        """
        sprites = []

        try:
            path = os.path.join(self.media_dir, filename)
            sheet = pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            return sprites

        frame_w, frame_h = frame_size

        for row in range(rows):
            for col in range(cols):
                x = col * frame_w
                y = row * frame_h

                try:
                    frame = sheet.subsurface((x, y, frame_w, frame_h)).copy()

                    if scale and scale > 1:
                        new_size = (frame_w * scale, frame_h * scale)
                        frame = pygame.transform.scale(frame, new_size)

                    sprites.append(frame)

                except ValueError:
                    continue

        return sprites

    def load_sound(
        self,
        filename: str,
        volume: float = 1.0
    ) -> Optional[pygame.mixer.Sound]:
        """Load a sound file with graceful fallback if audio is unavailable.

        Args:
            filename: Sound filename within the media/ directory.
            volume: Volume level from 0.0 to 1.0.

        Returns:
            The loaded pygame Sound object, or None if loading failed
            or audio is unavailable.
        """
        if not self._audio_available:
            return None

        cache_key = f"{filename}|{volume}"

        if cache_key in self._sound_cache:
            return self._sound_cache[cache_key]

        try:
            path = os.path.join(self.media_dir, filename)
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume)
            self._sound_cache[cache_key] = sound
            return sound

        except (pygame.error, FileNotFoundError, OSError) as e:
            if self.debug_mode:
                print(f"[AssetLoader] Warning: Failed to load sound '{filename}': {e}")
            self._sound_cache[cache_key] = None
            return None

    def play_sound(self, filename: str, volume: float = 1.0) -> bool:
        """Load and immediately play a sound.

        Args:
            filename: Sound filename within the media/ directory.
            volume: Volume level from 0.0 to 1.0.

        Returns:
            True if the sound was played, False otherwise.
        """
        sound = self.load_sound(filename, volume)
        if sound:
            sound.play()
            return True
        return False

    def clear_cache(self):
        """Clear all cached assets to free memory."""
        self._image_cache.clear()
        self._sound_cache.clear()
        self._game_assets.clear()

    def preload_images(self, filenames: list, size: Optional[Tuple[int, int]] = None):
        """Preload multiple images into the cache.

        Args:
            filenames: List of image filenames to preload.
            size: Optional size to scale all images to.
        """
        for filename in filenames:
            self.load_image(filename, size)

    def preload_game(self, game_name: str) -> int:
        """Preload all known assets for a specific game.

        This improves initial load time by loading assets before
        the game starts. Assets are tracked for later unloading.

        Args:
            game_name: Name of the game (e.g., 'snake', 'pacman').

        Returns:
            Number of assets preloaded.
        """
        if game_name not in GAME_ASSET_PATHS:
            return 0

        old_game = self._current_game
        self.set_current_game(game_name)

        count = 0
        for asset_path in GAME_ASSET_PATHS[game_name]:
            if asset_path.endswith('/'):
                # It's a directory prefix - scan for files
                dir_path = os.path.join(self.media_dir, asset_path)
                if os.path.isdir(dir_path):
                    for filename in os.listdir(dir_path):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                            full_path = os.path.join(asset_path, filename)
                            if self.load_image(full_path):
                                count += 1
            else:
                # Single file
                if self.load_image(asset_path):
                    count += 1

        self.set_current_game(old_game)

        if self.debug_mode:
            print(f"[AssetLoader] Preloaded {count} assets for {game_name}")

        return count

    def unload_game(self, game_name: str) -> int:
        """Unload all assets associated with a specific game.

        Removes game-specific assets from the cache to free memory.
        Useful when switching between games.

        Args:
            game_name: Name of the game to unload.

        Returns:
            Number of assets unloaded.
        """
        if game_name not in self._game_assets:
            return 0

        count = 0
        for cache_key in list(self._game_assets[game_name]):
            if cache_key in self._image_cache:
                del self._image_cache[cache_key]
                count += 1

        del self._game_assets[game_name]

        if self.debug_mode:
            print(f"[AssetLoader] Unloaded {count} assets for {game_name}")

        return count

    def get_cache_stats(self) -> dict:
        """Get statistics about the asset cache.

        Returns:
            Dict with cache statistics.
        """
        return {
            'image_count': len(self._image_cache),
            'sound_count': len(self._sound_cache),
            'cache_limit': self._cache_limit,
            'platform': self.platform,
            'games_tracked': list(self._game_assets.keys()),
        }


# Convenience: create a default global loader instance
_default_loader: Optional[AssetLoader] = None


def get_default_loader() -> AssetLoader:
    """Get or create the default global AssetLoader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = AssetLoader()
    return _default_loader


def load_media_image(
    filename: str,
    size: Optional[Tuple[int, int]] = None,
    preserve_aspect: bool = False
) -> Optional[pygame.Surface]:
    """Convenience function matching the original game_launcher API.

    Args:
        filename: Image filename within the media/ directory.
        size: Optional (width, height) to scale the image to.
        preserve_aspect: If True, scales to fit within size while preserving
                        aspect ratio.

    Returns:
        The loaded pygame Surface, or None if loading failed.
    """
    return get_default_loader().load_image(filename, size, preserve_aspect=preserve_aspect)
