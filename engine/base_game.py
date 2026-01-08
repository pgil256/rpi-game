"""Abstract base class for all games in the Weasel Entertainment System."""

from abc import ABC, abstractmethod
import pygame
import sys
from typing import Optional

from engine.audio_manager import get_audio_manager
from engine.achievements import get_achievement_manager
from engine.stats_manager import get_stats_manager
from engine.game_states import Difficulty
import engine


# Achievement notification display duration (frames at 60 FPS)
ACHIEVEMENT_DISPLAY_DURATION = 180  # 3 seconds


class BaseGame(ABC):
    """Abstract base class that enforces a consistent game loop pattern.

    All games should inherit from this class and implement the abstract methods.
    """

    def __init__(self, screen, input_manager, difficulty: Optional[Difficulty] = None):
        """Initialize the game with screen and input manager references.

        Args:
            screen: The pygame display surface to render to.
            input_manager: The InputManager instance for handling input.
            difficulty: The difficulty level (defaults to NORMAL if not specified).
        """
        self.screen = screen
        self.input_manager = input_manager
        self.difficulty = difficulty if difficulty is not None else Difficulty.NORMAL
        self.clock = pygame.time.Clock()
        self.audio = get_audio_manager()
        self.achievements = get_achievement_manager()
        self.stats = get_stats_manager()
        self._achievement_notification = None
        self._notification_timer = 0
        self._session_start_time = pygame.time.get_ticks()
        self.setup()

    @abstractmethod
    def setup(self):
        """Initialize game-specific state.

        Called automatically at the end of __init__.
        Override this to set up game objects, load assets, reset scores, etc.
        """
        pass

    @abstractmethod
    def handle_input(self):
        """Process player input.

        Returns:
            bool: True to exit to menu, False to continue running.
        """
        pass

    @abstractmethod
    def update(self, dt):
        """Update game logic.

        Args:
            dt: Delta time in seconds since the last frame.
        """
        pass

    @abstractmethod
    def render(self):
        """Draw the game state to the screen.

        Do not call pygame.display.flip() here - the run() method handles that.
        """
        pass

    def _draw_pause_overlay(self):
        """Draw a semi-transparent pause overlay with 'PAUSED' text.

        Call this from render() when the game is paused.
        """
        # Semi-transparent dark overlay
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # "PAUSED" text
        font = pygame.font.Font(None, 72)
        text = font.render("PAUSED", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2,
                                          self.screen.get_height() // 2 - 30))
        self.screen.blit(text, text_rect)

        # Instructions
        small_font = pygame.font.Font(None, 36)
        hint = small_font.render("Press P or Start to resume", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(self.screen.get_width() // 2,
                                          self.screen.get_height() // 2 + 30))
        self.screen.blit(hint, hint_rect)

    def _update_achievement_notification(self):
        """Update achievement notification timer and check for new notifications."""
        # Decrease timer for current notification
        if self._notification_timer > 0:
            self._notification_timer -= 1
            if self._notification_timer <= 0:
                self._achievement_notification = None

        # Check for new notifications if none is currently displayed
        if self._achievement_notification is None and self.achievements.has_notification():
            self._achievement_notification = self.achievements.pop_notification()
            self._notification_timer = ACHIEVEMENT_DISPLAY_DURATION

    def _draw_achievement_notification(self):
        """Draw achievement notification toast at top of screen.

        Call this at the end of render() to show achievement pop-ups.
        """
        if self._achievement_notification is None:
            return

        # Calculate slide-in/slide-out animation
        progress = self._notification_timer / ACHIEVEMENT_DISPLAY_DURATION
        if progress > 0.9:
            # Slide in (first 10%)
            slide = 1.0 - ((progress - 0.9) / 0.1)
        elif progress < 0.1:
            # Slide out (last 10%)
            slide = progress / 0.1
        else:
            slide = 1.0

        # Toast dimensions and position
        toast_width = 320
        toast_height = 70
        toast_x = (self.screen.get_width() - toast_width) // 2
        toast_y = int(-toast_height + (toast_height + 10) * slide)

        # Draw toast background with rounded corners effect
        toast_surf = pygame.Surface((toast_width, toast_height), pygame.SRCALPHA)

        # Gold gradient background
        for y in range(toast_height):
            alpha = 220
            r = 60 + int(20 * (y / toast_height))
            g = 50 + int(15 * (y / toast_height))
            b = 30
            pygame.draw.line(toast_surf, (r, g, b, alpha), (0, y), (toast_width, y))

        # Gold border
        pygame.draw.rect(toast_surf, (255, 215, 0), (0, 0, toast_width, toast_height), 3)

        # Trophy icon (simple star)
        star_x, star_y = 25, toast_height // 2
        star_color = (255, 215, 0)
        points = []
        import math
        for i in range(5):
            angle = math.radians(i * 72 - 90)
            points.append((star_x + 15 * math.cos(angle), star_y + 15 * math.sin(angle)))
            angle = math.radians(i * 72 - 90 + 36)
            points.append((star_x + 7 * math.cos(angle), star_y + 7 * math.sin(angle)))
        pygame.draw.polygon(toast_surf, star_color, points)

        # Achievement text
        title_font = pygame.font.Font(None, 28)
        desc_font = pygame.font.Font(None, 22)

        title_text = title_font.render("Achievement Unlocked!", True, (255, 215, 0))
        toast_surf.blit(title_text, (50, 10))

        name_text = desc_font.render(self._achievement_notification["name"], True, (255, 255, 255))
        toast_surf.blit(name_text, (50, 35))

        # Blit to screen
        self.screen.blit(toast_surf, (toast_x, toast_y))

    def _track_session_stats(self):
        """Track play time when game session ends. Called automatically by run()."""
        session_time = (pygame.time.get_ticks() - self._session_start_time) / 1000.0
        self.stats.add('global', 'total_play_time', session_time)

    def run(self):
        """Main game loop. Handles events, input, update, and render cycle.

        This is a concrete method that provides the standard game loop.
        Override only if you need custom loop behavior.
        """
        dt = 0

        while True:
            # Event processing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._track_session_stats()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._track_session_stats()
                        return
                    if event.key == pygame.K_m:
                        self.audio.toggle_mute()

            # Handle input - exit if returns True
            if self.handle_input():
                self._track_session_stats()
                return

            # Update game logic with delta time
            self.update(dt)

            # Update achievement notifications
            self._update_achievement_notification()

            # Render the frame
            self.render()

            # Draw achievement notification on top
            self._draw_achievement_notification()

            # Display and timing (uses scaling in fullscreen mode)
            engine.scale_to_screen()
            dt = self.clock.tick(60) / 1000.0  # Convert ms to seconds
