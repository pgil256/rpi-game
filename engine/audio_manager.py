"""
Audio Manager for the Weasel Entertainment System.

Provides sound effect and music playback with graceful fallback when audio
is unavailable. Supports global mute toggle that persists across games.
"""

import os
import pygame
from typing import Dict, Optional


class AudioManager:
    """Manages sound effects and music playback with graceful degradation.

    Features:
    - Automatic fallback to silence when audio is unavailable
    - Sound caching to prevent repeated disk loads
    - Global mute toggle (M key)
    - Volume control
    - Short sound effect playback
    - Background music support

    Usage:
        audio = AudioManager()
        audio.play_sound('collect')  # Plays collect.wav or .ogg from sounds/
        audio.play_music('theme')    # Plays theme.wav or .ogg as background
        audio.toggle_mute()          # Toggle mute on/off
    """

    # Standard sound event names used across all games
    SOUND_MENU_MOVE = 'menu_move'       # Menu navigation
    SOUND_MENU_SELECT = 'menu_select'   # Selecting a menu item
    SOUND_COLLECT = 'collect'           # Collecting items (food, pellets, diamonds)
    SOUND_DEATH = 'death'               # Player death/hit
    SOUND_VICTORY = 'victory'           # Level complete or win
    SOUND_JUMP = 'jump'                 # Jump action (frogger)
    SOUND_DIG = 'dig'                   # Digging (boulder dash, dig dug)

    def __init__(self, sounds_dir: Optional[str] = None):
        """Initialize the audio manager.

        Args:
            sounds_dir: Path to directory containing sound files.
                       Defaults to 'sounds/' relative to the project root.
        """
        self._available = False
        self._muted = False
        self._volume = 0.5
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._current_music: Optional[str] = None

        # Determine sounds directory
        if sounds_dir is None:
            # Default to sounds/ in project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._sounds_dir = os.path.join(base_dir, 'sounds')
        else:
            self._sounds_dir = sounds_dir

        # Try to initialize pygame mixer
        self._init_mixer()

    def _init_mixer(self):
        """Initialize pygame mixer with graceful fallback."""
        try:
            # Check if mixer is already initialized
            mixer_init = pygame.mixer.get_init()
            if mixer_init is None:
                # Try to initialize mixer
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                mixer_init = pygame.mixer.get_init()
                print(f"[AudioManager] Initialized mixer: {mixer_init}")
            else:
                print(f"[AudioManager] Mixer already initialized: {mixer_init}")

            # Verify initialization worked
            if mixer_init is not None:
                self._available = True
                # Reserve channels for sound effects
                pygame.mixer.set_num_channels(8)
                print(f"[AudioManager] Audio available. Sounds directory: {self._sounds_dir}")

                # Check if sounds directory exists
                if os.path.exists(self._sounds_dir):
                    files = [f for f in os.listdir(self._sounds_dir) if f.endswith(('.wav', '.ogg', '.mp3'))]
                    if files:
                        print(f"[AudioManager] Found {len(files)} sound file(s): {files}")
                    else:
                        print(f"[AudioManager] WARNING: No sound files found in {self._sounds_dir}")
                else:
                    print(f"[AudioManager] WARNING: Sounds directory does not exist: {self._sounds_dir}")
            else:
                print("[AudioManager] WARNING: Mixer init returned None")
                self._available = False
        except pygame.error as e:
            print(f"[AudioManager] Audio unavailable (pygame error): {e}")
            self._available = False
        except Exception as e:
            print(f"[AudioManager] Audio initialization failed: {e}")
            self._available = False

    @property
    def available(self) -> bool:
        """Check if audio system is available."""
        return self._available

    @property
    def muted(self) -> bool:
        """Check if audio is currently muted."""
        return self._muted

    @property
    def volume(self) -> float:
        """Get current volume (0.0 to 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, value: float):
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, value))
        # Update volume on all cached sounds
        for sound in self._sounds.values():
            sound.set_volume(self._volume)

    def toggle_mute(self) -> bool:
        """Toggle mute state. Returns new mute state."""
        self._muted = not self._muted
        if self._muted:
            # Mute: stop all sounds and pause music
            if self._available:
                pygame.mixer.stop()
                pygame.mixer.music.pause()
        else:
            # Unmute: resume music if it was playing
            if self._available and self._current_music:
                pygame.mixer.music.unpause()
        return self._muted

    def set_mute(self, muted: bool):
        """Explicitly set mute state."""
        if muted != self._muted:
            self.toggle_mute()

    def _find_sound_file(self, name: str) -> Optional[str]:
        """Find a sound file by name, trying common extensions.

        Args:
            name: Sound name without extension (e.g., 'collect')

        Returns:
            Full path to sound file, or None if not found.
        """
        extensions = ['.wav', '.ogg', '.mp3']

        for ext in extensions:
            path = os.path.join(self._sounds_dir, name + ext)
            if os.path.exists(path):
                return path

        return None

    def _load_sound(self, name: str) -> Optional[pygame.mixer.Sound]:
        """Load a sound effect, using cache if available.

        Args:
            name: Sound name without extension.

        Returns:
            Loaded Sound object, or None if unavailable.
        """
        if not self._available:
            return None

        # Check cache first
        if name in self._sounds:
            return self._sounds[name]

        # Find and load the sound file
        path = self._find_sound_file(name)
        if path is None:
            # Only log once per sound to avoid spamming console
            if name not in self._sounds:
                self._sounds[name] = None  # Mark as checked but not found
            return None

        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self._volume)
            self._sounds[name] = sound
            print(f"[AudioManager] Loaded sound: {name} from {path}")
            return sound
        except pygame.error as e:
            print(f"[AudioManager] Failed to load sound '{name}': {e}")
            self._sounds[name] = None  # Mark as failed
            return None

    def play_sound(self, name: str) -> bool:
        """Play a sound effect.

        Args:
            name: Sound name without extension (e.g., 'collect').

        Returns:
            True if sound was played, False otherwise.
        """
        if not self._available or self._muted:
            return False

        sound = self._load_sound(name)
        if sound is None:
            return False

        try:
            channel = sound.play()
            return channel is not None
        except pygame.error as e:
            print(f"[AudioManager] Error playing sound '{name}': {e}")
            return False

    def play_music(self, name: str, loops: int = -1) -> bool:
        """Play background music.

        Args:
            name: Music file name without extension.
            loops: Number of times to loop (-1 for infinite).

        Returns:
            True if music started, False otherwise.
        """
        if not self._available:
            return False

        path = self._find_sound_file(name)
        if path is None:
            return False

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._volume * 0.7)  # Music slightly quieter
            if not self._muted:
                pygame.mixer.music.play(loops)
            self._current_music = name
            return True
        except pygame.error as e:
            print(f"Failed to play music '{name}': {e}")
            return False

    def stop_music(self):
        """Stop currently playing background music."""
        if self._available:
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self._current_music = None

    def pause_music(self):
        """Pause background music."""
        if self._available:
            try:
                pygame.mixer.music.pause()
            except pygame.error:
                pass

    def resume_music(self):
        """Resume paused background music."""
        if self._available and not self._muted:
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass

    def stop_all(self):
        """Stop all sounds and music."""
        if self._available:
            try:
                pygame.mixer.stop()
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self._current_music = None

    def preload(self, *names: str):
        """Preload sounds into cache for faster playback.

        Args:
            *names: Sound names to preload.
        """
        for name in names:
            self._load_sound(name)


# Global audio manager instance (singleton pattern)
_audio_manager: Optional[AudioManager] = None


def get_audio_manager() -> AudioManager:
    """Get or create the global AudioManager instance.

    Returns:
        The global AudioManager instance.
    """
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager
