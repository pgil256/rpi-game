"""Shared fixed-step game loop, session bookkeeping, and cached overlays."""

from abc import ABC, abstractmethod
import pygame
import engine
from engine.audio_manager import AudioManager, get_audio_manager
from engine.achievements import get_achievement_manager
from engine.stats_manager import get_stats_manager
from engine.score_manager import get_score_manager
from engine.game_states import Difficulty
from engine.persistence import persistence_session

ACHIEVEMENT_DISPLAY_DURATION = 180


class AchievementToast:
    """Reusable notification renderer for the launcher and every game."""

    def __init__(self, manager=None):
        self.manager = manager or get_achievement_manager()
        self.notification = None
        self.timer = 0
        self.surface = None
        self.title_font = pygame.font.Font(None, 28)
        self.name_font = pygame.font.Font(None, 22)

    def update(self, dt=1 / 60):
        self.timer = max(0, self.timer - dt)
        if self.timer == 0:
            self.notification = None
        if self.notification is None and self.manager.has_notification():
            self.notification = self.manager.pop_notification()
            get_audio_manager().play_sound(AudioManager.SOUND_ACHIEVEMENT)
            self.timer = 3.0
            self.surface = pygame.Surface((340, 70), pygame.SRCALPHA)
            self.surface.fill((65, 52, 30, 235))
            pygame.draw.rect(
                self.surface, (255, 215, 0), self.surface.get_rect(), 3, border_radius=8
            )
            self.surface.blit(
                self.title_font.render("Achievement unlocked!", True, (255, 215, 0)), (14, 10)
            )
            self.surface.blit(
                self.name_font.render(self.notification["name"], True, (255, 255, 255)), (14, 38)
            )

    def draw(self, screen):
        if self.notification is None:
            return
        slide = min(1.0, (3.0 - self.timer) / 0.3, self.timer / 0.3)
        screen.blit(self.surface, ((screen.get_width() - 340) // 2, int(-70 + 80 * slide)))


class BaseGame(ABC):
    """Game logic advances at FPS even when the display is slower.

    Input handlers own the input snapshot; the loop calls them once per logic
    step. Catch-up is bounded to 250 ms to avoid huge jumps after a stall.
    """

    def __init__(self, screen, input_manager, difficulty=None):
        self.screen = screen
        self.input_manager = input_manager
        self.difficulty = difficulty if difficulty is not None else Difficulty.NORMAL
        self.demo_mode = bool(getattr(input_manager, "demo_mode", False))
        self.game_key = type(self).__module__.rsplit(".", 1)[-1]
        self.clock = pygame.time.Clock()
        self.audio = get_audio_manager()
        self.achievements = get_achievement_manager()
        self.stats = get_stats_manager()
        self._toast = AchievementToast(self.achievements)
        self._overlay_cache = {}
        self._session_closed = False
        self._window_focused = True
        self._focus_paused = False
        self._accumulator = 0.0
        self.quit_requested = False
        self._audio_suspended = False
        with persistence_session(demo=self.demo_mode, difficulty=self.difficulty):
            self.setup()
            self._start_session()

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def handle_input(self):
        """Update input and return True to leave the game."""

    @abstractmethod
    def update(self, dt):
        pass

    @abstractmethod
    def render(self):
        pass

    def _start_session(self):
        self._session_closed = False
        self._game_statistics_recorded = False
        self.play_ticks = 0
        self.new_clear_record = False
        self.stats.increment("global", "games_started")
        self.stats.increment(self.game_key, "games_played")
        self.stats.save()

    def restart_session(self):
        """Finish the old run and start accounting for a player-requested restart."""
        with persistence_session(demo=self.demo_mode, difficulty=self.difficulty):
            self._track_session_stats()
            self.new_high_score = False
            self._start_session()
        self.audio.play_sound(AudioManager.SOUND_START)

    def _save_current_score(self):
        if hasattr(self, "score"):
            changed = get_score_manager().set_high_score(self.game_key, self.score, self.difficulty)
            if changed:
                self.new_high_score = True
            if hasattr(self, "high_score"):
                self.high_score = get_score_manager().get_high_score(self.game_key, self.difficulty)

    def _record_game_statistics(self):
        """Record this run's cumulative game-specific totals.

        Games override this hook instead of writing those totals in several
        terminal/exit paths. Event counters already saved during play stay out
        of this hook.
        """

    def _finalize_game_statistics(self):
        """Commit pending run totals once, including an early return to menu."""
        if self._game_statistics_recorded:
            return
        with persistence_session(demo=self.demo_mode, difficulty=self.difficulty):
            self._record_game_statistics()
        self._game_statistics_recorded = True

    def _track_session_stats(self):
        if self._session_closed:
            return
        with persistence_session(demo=self.demo_mode, difficulty=self.difficulty):
            self._save_current_score()
            self._finalize_game_statistics()
            self.stats.add("global", "total_play_time", self.play_ticks / engine.FPS)
            self.stats.save()
            self.achievements.check_global_achievements(self.stats)
        self._session_closed = True

    def _overlay(self, title, detail, hint):
        key = (self.screen.get_size(), title, detail, hint)
        if key not in self._overlay_cache:
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            lines = detail if isinstance(detail, tuple) else (detail,)
            for text, size, y, color in (
                (title, 64, -55, (255, 245, 210)),
                *((line, 32, 5 + i * 37, (255, 255, 255)) for i, line in enumerate(lines)),
                (hint, 28, 65 + (len(lines) - 1) * 37, (220, 220, 220)),
            ):
                image = pygame.font.Font(None, size).render(text, True, color)
                overlay.blit(
                    image,
                    image.get_rect(
                        center=(overlay.get_width() // 2, overlay.get_height() // 2 + y)
                    ),
                )
            if len(self._overlay_cache) >= 12:
                self._overlay_cache.clear()
            self._overlay_cache[key] = overlay
        self.screen.blit(self._overlay_cache[key], (0, 0))

    def _draw_pause_overlay(self):
        self._overlay("PAUSED", "", "P / Start: resume    B / Esc: menu")

    def _draw_game_over_overlay(
        self, title="GAME OVER", score=None, hint="A / Enter: restart    B / Esc: menu"
    ):
        score = getattr(self, "score", 0) if score is None else score
        self._overlay(title, f"Score: {score}", hint)

    def _record_campaign_clear(self):
        self.new_clear_record = self.stats.record_clear(
            self.game_key, self.difficulty, self.play_ticks
        )

    def _campaign_result(self):
        best = self.stats.best_clear(self.game_key, self.difficulty)
        label = "New best" if self.new_clear_record else "Best"
        return (
            f"Score {self.score:,}   |   Lives left {self.lives}",
            f"Clear {self.stats.format_clear(self.play_ticks)}   |   {label} {self.stats.format_clear(best)}",
        )

    def _terminal(self):
        return any(
            getattr(self, flag, False) for flag in ("game_over", "game_won", "won")
        ) or getattr(self, "state", None) in ("GAMEOVER", "game_over")

    def _playing(self):
        return not (
            self._terminal()
            or getattr(self, "state", None) in ("START", "dying", "level_complete")
            or any(
                getattr(self, flag, False)
                for flag in (
                    "paused",
                    "waiting_for_input",
                    "level_complete",
                    "playing_death",
                    "death_timer",
                    "is_dying",
                    "is_respawning",
                )
            )
        )

    def _set_window_focus(self, focused):
        self._window_focused = focused
        self._accumulator = 0.0
        self.input_manager.discard_pending()
        waiting = (
            getattr(self, "waiting_for_input", False) or getattr(self, "state", None) == "START"
        )
        if (
            not focused
            and not waiting
            and not self._terminal()
            and not getattr(self, "paused", False)
        ):
            self._focus_paused = True
        if not self.demo_mode:
            self._sync_game_audio(bool(getattr(self, "paused", False)))

    def _update_achievement_notification(self):
        if not self.demo_mode:
            self._toast.update(1 / engine.FPS)

    def _draw_achievement_notification(self):
        if not self.demo_mode:
            self._toast.draw(self.screen)

    def advance(self, elapsed):
        """Advance bounded real elapsed time; useful for the launcher and tests."""
        if not self._window_focused:
            return False
        if self._focus_paused:
            self.input_manager.update()
            if self.input_manager.back_pressed():
                return True
            if self.input_manager.pause_pressed():
                self._focus_paused = False
                if not self.demo_mode:
                    self._sync_game_audio(False)
            return False
        self._accumulator += max(0.0, min(float(elapsed), 0.25))
        step = 1 / engine.FPS
        with persistence_session(demo=self.demo_mode, difficulty=self.difficulty):
            while self._accumulator + 1e-9 >= step:
                self._accumulator -= step
                was_paused = bool(getattr(self, "paused", False))
                if self.handle_input():
                    return True
                if self._playing():
                    self.play_ticks += 1
                self.update(step)
                if not self.demo_mode:
                    self._sync_game_audio(was_paused)
                self._update_achievement_notification()
                self.stats.save()
        return False

    def _sync_game_audio(self, was_paused):
        paused = bool(getattr(self, "paused", False))
        if paused != was_paused:
            self.audio.play_sound(AudioManager.SOUND_PAUSE if paused else AudioManager.SOUND_RESUME)
        suspended = paused or self._focus_paused or not self._window_focused or self._terminal()
        if suspended != self._audio_suspended:
            self._audio_suspended = suspended
            if suspended:
                self.audio.pause_music()
            else:
                self.audio.resume_music()

    def run(self):
        if not self.demo_mode:
            self.audio.play_music(f"{self.game_key}_theme")
            self.audio.play_sound(AudioManager.SOUND_START)
        try:
            while True:
                elapsed = self.clock.tick(engine.FPS) / 1000.0
                for event in pygame.event.get():
                    if engine.handle_global_event(event):
                        continue
                    if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
                        self._set_window_focus(event.type == pygame.WINDOWFOCUSGAINED)
                        continue
                    if self._window_focused or event.type in (
                        pygame.JOYDEVICEADDED,
                        pygame.JOYDEVICEREMOVED,
                    ):
                        self.input_manager.handle_event(event)
                    if event.type == pygame.QUIT:
                        self.quit_requested = True
                        return
                    if (
                        self._window_focused
                        and event.type == pygame.KEYDOWN
                        and event.key == pygame.K_m
                    ):
                        self.audio.toggle_mute()
                if self.advance(elapsed):
                    return
                self.render()
                if self._focus_paused:
                    self._draw_pause_overlay()
                self._draw_achievement_notification()
                engine.scale_to_screen()
        finally:
            if not self.demo_mode:
                self.audio.stop_music()
            self._track_session_stats()
