# WES architecture and maintenance

The [README](readme.md) is the current operations guide. This document describes
the active implementation, replacing the obsolete embedded-game documentation.

## Boundaries

`game_launcher.py` is import-safe. `main(argv)` parses command-line flags;
`initialize()` opens devices, loads preferences and installs letterboxed display
scaling. Every submenu uses the same `InputManager`. Games receive
`GameClass(screen, input_manager, difficulty=None)` and never change the window.

`engine/base_game.py` owns a fixed 60 Hz simulation accumulator, 250 ms elapsed
clamp, session start/end accounting, cached pause/game-over overlays, and the
shared achievement toast. Existing game timers use fixed simulation steps rather
than rendering frames, so display rates below 60 Hz catch up within that bound.
The active-play counter stops during pause, loss of focus, title screens, and level
or death transitions. Both finite campaigns store their fastest clear in integer
60 Hz ticks for each difficulty. Game-specific movement and restart state remain in the six `games/*.py` modules.

`engine/input_manager.py` is the canonical keyboard/gamepad mapping and input
snapshot API. `menu_direction()` supplies edge/repeat navigation;
`action_pressed()` excludes Start, while `confirm_pressed()` includes it.
`engine/game_states.py` retains the used `Direction` and `Difficulty` enums.
Unused global constants/state abstractions were removed instead of claiming games
used them. Each game keeps its actual difficulty settings near its implementation.

## Data and lifecycle

On Windows, the launcher acquires a per-save-directory mutex before opening any
manager and releases it after shutdown writes. The tagged SDL window can be
reactivated by a second launch.

`engine/persistence.py` owns user-data paths, migration, JSON recovery and atomic
replacement. `persistence_session(demo=True, difficulty=...)` suppresses mutations
and writes across global managers. `BaseGame` also derives demo mode from its input
object and wraps setup and fixed-step execution. Test overrides never migrate the
user's real saves. Stats accumulate in memory and flush at boundaries rather than
rewriting for each field. Difficulty-specific score access uses the current
session or an explicit difficulty argument.

`ScriptedInput` in the launcher provides the regular game interface without
opening or resetting hardware for the packaged smoke check. The interactive
attract/preview mode has been removed; idle time never starts a game. A scripted
simulation fixture in tests still verifies fixed-step play and data isolation.

## Audio

`generate_sounds.py` deterministically synthesizes 18 effects and seven original
16-bar themes. It uses only the standard library; no synthesis runs in the game.
The home theme continues across utility screens. `BaseGame.run()` selects each
game's theme, pauses it for pause/game-over states, and stops it on exit. The audio
manager keeps mute and gameplay-pause state separate and applies independent
master/music/effects levels. Short cooldowns prevent repeated action effects from
flooding the eight sound channels. The smoke check decodes every packaged effect
and loads/starts every music track before exercising all games.

## Rendering

The launcher pre-renders static decorations and text. Fullscreen scales into a
reused destination surface and letterboxes 4:3. `AnimatedFerret` shares cached,
size-aware sheet frames; special animations expose completion. `AssetLoader`
shares an image cache across instances. Games cache terrain, backgrounds, glows
and effects instead of rebuilding them each frame. Display/font objects must be
created after Pygame initialization.

## Failure handling

A game/screen exception is logged and returns to a readable launcher error panel.
Close requests propagate back to `main`; submenus do not call `sys.exit()`.
Shutdown save errors are logged. The rotating log retains two prior files.
Persistence failures preserve recoverable data and report errors rather than
silently claiming a successful write.

## Verification and release

Run the commands in the README. `tests/` contains targeted gameplay regressions,
all-game/all-difficulty smoke coverage, persistence corruption/recovery checks,
fixed-step timing and input checks, launcher navigation, soundtrack lifecycle,
idle-menu stability, and scripted-play data isolation. `engine/test_integration.py` uses assertions, with no tautological
success paths. Shell scripts can be syntax-checked with `bash -n`.

`wes.spec` uses an explicit runtime asset allowlist. `scripts/package.py rpi-setup`
delegates to the single autostart installer. Four shell scripts use LF endings.
Raspberry Pi behavior must be verified on hardware; desktop/headless checks do
not establish Pi frame rate, driver compatibility or boot success.

See the audit resolution ledger for finding-level evidence and remaining release
conditions. `legacy_reference/` is preserved historical material, not an active
asset dependency. Public licensing and provenance remain owner review items.
