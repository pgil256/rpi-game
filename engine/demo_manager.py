"""
Demo recording and playback system for the Weasel Entertainment System.

Records player inputs during gameplay and plays them back for attract mode.
Demo data is stored as JSON files in the demos/ directory.

Usage:
    from engine.demo_manager import DemoManager, get_demo_manager

    # Recording (during gameplay)
    demo = get_demo_manager()
    demo.start_recording('snake')
    # Each frame:
    demo.record_frame(dpad=(dx, dy), buttons={'action': False, 'back': False})
    # When done:
    demo.stop_recording()

    # Playback (for attract mode)
    demo.start_playback('snake')
    # Each frame:
    inputs = demo.get_playback_frame()
    if inputs is None:  # Demo ended
        demo.stop_playback()
"""

import json
import os
import random
from pathlib import Path
from typing import Optional, Dict, Any, List


class DemoManager:
    """Manages demo recording and playback."""

    def __init__(self, demo_dir: str = "demos"):
        """Initialize the demo manager.

        Args:
            demo_dir: Directory to store demo files.
        """
        self.demo_path = Path(__file__).parent.parent / demo_dir
        self.demo_path.mkdir(exist_ok=True)

        # Recording state
        self.is_recording = False
        self.recording_game = None
        self.recorded_frames: List[Dict] = []

        # Playback state
        self.is_playing = False
        self.playback_game = None
        self.playback_frames: List[Dict] = []
        self.playback_index = 0

    def get_available_demos(self) -> Dict[str, List[str]]:
        """Get available demo files organized by game.

        Returns:
            Dict mapping game names to lists of demo filenames.
        """
        demos = {}
        for file in self.demo_path.glob("*.json"):
            parts = file.stem.split("_")
            if len(parts) >= 2:
                game = parts[0]
                if game not in demos:
                    demos[game] = []
                demos[game].append(file.name)
        return demos

    def has_demo(self, game: str) -> bool:
        """Check if a demo exists for a game."""
        demos = self.get_available_demos()
        return game in demos and len(demos[game]) > 0

    def start_recording(self, game: str) -> None:
        """Start recording a demo for a game.

        Args:
            game: Name of the game being recorded.
        """
        self.is_recording = True
        self.recording_game = game
        self.recorded_frames = []

    def record_frame(self, dpad: tuple = (0, 0), buttons: Dict[str, bool] = None) -> None:
        """Record a single frame of input.

        Args:
            dpad: D-pad state as (dx, dy) tuple.
            buttons: Dict of button states {'action': bool, 'back': bool, 'pause': bool}.
        """
        if not self.is_recording:
            return

        if buttons is None:
            buttons = {'action': False, 'back': False, 'pause': False}

        self.recorded_frames.append({
            'dpad': list(dpad),
            'buttons': buttons,
        })

    def stop_recording(self, save: bool = True) -> Optional[str]:
        """Stop recording and optionally save the demo.

        Args:
            save: Whether to save the recording to file.

        Returns:
            Filename if saved, None otherwise.
        """
        if not self.is_recording:
            return None

        self.is_recording = False
        filename = None

        if save and len(self.recorded_frames) > 60:  # At least 1 second of gameplay
            # Generate filename with timestamp
            import time
            timestamp = int(time.time())
            filename = f"{self.recording_game}_{timestamp}.json"
            filepath = self.demo_path / filename

            demo_data = {
                'game': self.recording_game,
                'frames': self.recorded_frames,
                'frame_count': len(self.recorded_frames),
            }

            try:
                filepath.write_text(json.dumps(demo_data))
            except IOError:
                filename = None

        self.recording_game = None
        self.recorded_frames = []
        return filename

    def start_playback(self, game: str) -> bool:
        """Start playing back a demo for a game.

        Args:
            game: Name of the game to play demo for.

        Returns:
            True if demo started, False if no demo available.
        """
        demos = self.get_available_demos()
        if game not in demos or not demos[game]:
            return False

        # Pick a random demo for variety
        demo_file = random.choice(demos[game])
        filepath = self.demo_path / demo_file

        try:
            data = json.loads(filepath.read_text())
            self.playback_frames = data.get('frames', [])
            self.playback_index = 0
            self.is_playing = True
            self.playback_game = game
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def get_playback_frame(self) -> Optional[Dict]:
        """Get the next frame of playback input.

        Returns:
            Input dict with 'dpad' and 'buttons', or None if playback ended.
        """
        if not self.is_playing or self.playback_index >= len(self.playback_frames):
            return None

        frame = self.playback_frames[self.playback_index]
        self.playback_index += 1
        return frame

    def stop_playback(self) -> None:
        """Stop demo playback."""
        self.is_playing = False
        self.playback_game = None
        self.playback_frames = []
        self.playback_index = 0

    def get_playback_progress(self) -> float:
        """Get playback progress as 0.0-1.0.

        Returns:
            Progress ratio, or 0 if not playing.
        """
        if not self.is_playing or not self.playback_frames:
            return 0.0
        return self.playback_index / len(self.playback_frames)


# Singleton instance
_demo_manager: Optional[DemoManager] = None


def get_demo_manager() -> DemoManager:
    """Get the global DemoManager instance."""
    global _demo_manager
    if _demo_manager is None:
        _demo_manager = DemoManager()
    return _demo_manager
