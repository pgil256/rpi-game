"""Centralized asset loading with caching for the Winston Entertainment System.

Includes LRU cache management, platform-aware optimizations, and
game-specific asset loading/unloading for memory efficiency.
"""

import os
import logging
import platform
from collections import OrderedDict
from typing import Optional, Tuple
import pygame


# Note: Color constants are defined in engine/__init__.py
# Import them if needed within this module, but they're primarily
# for external use. We keep local references for fallback surfaces.
WEASEL_BROWN = (139, 90, 43)  # Brown for head/front
WEASEL_TAN = (210, 180, 140)  # Tan/cream for body
WEASEL_WHITE = (255, 248, 220)  # Cream white for underbelly
BURROW_BROWN = (101, 67, 33)  # Dark earthy brown for background


def gem_sprite(size):
    """Faceted crystal shared by the underground campaigns."""
    gem = pygame.Surface((32, 32), pygame.SRCALPHA)
    outline = [(3, 12), (9, 5), (23, 5), (29, 12), (16, 28)]
    pygame.draw.polygon(gem, (48, 62, 94), outline)
    pygame.draw.polygon(gem, (110, 224, 244), [(5, 12), (10, 7), (22, 7), (27, 12)])
    pygame.draw.polygon(gem, (81, 165, 224), [(5, 13), (27, 13), (16, 25)])
    pygame.draw.polygon(gem, (174, 245, 252), [(11, 13), (21, 13), (16, 25)])
    pygame.draw.line(gem, (246, 255, 255), (9, 10), (12, 7), 2)
    return pygame.transform.scale(gem, (size, size))


# Platform detection
def detect_platform() -> str:
    """Detect the current platform for optimization hints.

    Returns:
        One of: 'raspberry_pi', 'linux', 'windows', 'macos', 'unknown'
    """
    system = platform.system().lower()

    if system == "linux":
        # Check for Raspberry Pi
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read().lower()
                if "raspberry" in cpuinfo or "bcm" in cpuinfo:
                    return "raspberry_pi"
        except (IOError, OSError):
            pass
        return "linux"
    elif system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    return "unknown"


# Default cache limits based on platform
def get_default_cache_limit() -> int:
    """Get the default cache limit based on platform.

    Returns smaller limits on resource-constrained platforms like RPi.
    """
    plat = detect_platform()
    if plat == "raspberry_pi":
        return 50  # Smaller cache for RPi
    return 100  # Default for desktop


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
    - Shared bounded image cache
    - Platform-aware optimizations
    - Optional debug logging for missing assets
    """

    # Class-level debug mode flag
    debug_mode: bool = False
    _shared_caches = {}
    _missing = set()

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
            if os.path.isdir(os.path.join(check_dir, "media")):
                base_dir = check_dir
            else:
                base_dir = os.getcwd()

        self.base_dir = base_dir
        self.media_dir = os.path.join(base_dir, "media")

        # LRU caches using OrderedDict (last accessed items at end)
        self._image_cache = self._shared_caches.setdefault(os.path.abspath(base_dir), OrderedDict())

        # Cache limit (0 = unlimited)
        self._cache_limit = cache_limit if cache_limit is not None else get_default_cache_limit()

        # Platform info
        self.platform = detect_platform()

        # Track if audio is available

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

    def load_image(
        self,
        filename: str,
        size: Optional[Tuple[int, int]] = None,
        use_integer_scaling: bool = True,
        preserve_aspect: bool = False,
        has_alpha: bool = True,
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

            return img

        except (pygame.error, FileNotFoundError, OSError) as e:
            missing_key = (self.media_dir, filename)
            if missing_key not in self._missing:
                logging.getLogger(__name__).warning("Cannot load image %s: %s", filename, e)
                self._missing.add(missing_key)
            return None

    def create_fallback_surface(
        self,
        size: Tuple[int, int],
        color: Tuple[int, int, int],
        with_border: bool = False,
        border_color: Tuple[int, int, int] = (255, 255, 255),
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
        with_border: bool = False,
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

    def clear_cache(self):
        """Clear the shared image cache for this asset root."""
        self._image_cache.clear()

    def get_cache_stats(self):
        return {"images": len(self._image_cache), "limit": self._cache_limit}


_default_loader = None


def get_default_loader() -> AssetLoader:
    """Get or create the default global AssetLoader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = AssetLoader()
    return _default_loader


def load_media_image(
    filename: str, size: Optional[Tuple[int, int]] = None, preserve_aspect: bool = False
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
