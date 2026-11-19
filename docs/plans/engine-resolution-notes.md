# Engine audit resolution notes — 2026-11-14

Implemented against `docs/plans/2026-11-14-audit-findings.md`. This is an implementation/evidence log, not a claim of Raspberry Pi hardware validation.

| Findings | Resolution and evidence |
| --- | --- |
| A2, A6 | `AudioManager.muted` supports assignment, `set_mute` safely previews without saving, and `toggle_mute` persists the shared setting. Volume skips missing cached sounds and updates music. Settings validate types/range before use. Launcher wires these APIs to startup and menus. |
| A3, C8 | Input construction no longer quits the global joystick subsystem. Device-added/removed events reacquire handles; 500 ms polling recovers absent/invalid handles even when a caller does not forward events. Hardware-free tests verify no subsystem quit and reconnection. Physical unplug/replug still needs device verification. |
| A4, C5–C7 | `menu_direction()` returns one immediate direction then repeats after 250 ms, every 120 ms; diagonal input resolves to one axis. Enter/A are action, Start/P are pause; `confirm_pressed()` adds Start for menus. Configured mappings feed compatibility helpers. Constants come from one definition. Module-level `get_dpad()` never advances input state. |
| A5, C21 | Scoped `persistence_session(demo=True)` prevents score/stat/settings/achievement mutations as well as disk writes. `BaseGame` recognizes `input.demo_mode`. Unused recording/playback manager removed; launcher uses scripted normal input. No demo folder is created. All six games run 300 frames at all difficulties with zero save-directory creation; launcher tests also cover 900 frames per game. |
| C1, C3 | `BaseGame` owns restart session accounting, cached pause/game-over overlays, and a shared `AchievementToast` used by the launcher. Game agents integrated the restart/overlay helpers while retaining game-specific transitions. Toast background/text are generated only for new notifications. |
| C2, G1 | `BaseGame.advance(elapsed)` runs fixed 1/FPS simulation steps, handles input per step, and limits elapsed catch-up to 250 ms. `run()` uses the shared FPS value. Tests compare 30 and 60 display updates and verify stall bounds. The launcher applies equivalent fixed-step timing to scripted demos. |
| C4 | Every normal `run()` exit, including an exception, goes through idempotent session finalization and saves the current score with difficulty. QUIT is propagated as `quit_requested` to the launcher. |
| C9, C10 | Shared `JsonStore`: UTF-8 JSON, validated top-level structure, fsynced temporary file + atomic replacement, previous good `.bak`, logged errors and `last_error`, preserved `.corrupt-*` data and backup recovery. POSIX parent directory is fsynced after replacement. Default saves use `%LOCALAPPDATA%/WES` or `$XDG_DATA_HOME/wes` (`~/.local/share/wes` fallback). `WES_DATA_DIR` overrides all data paths for tests/portable use. Legacy project saves import only when no override is set; originals remain untouched. |
| C11 | Stats setters mark a batch dirty; the shared loop flushes once after each simulation step, and session close flushes remaining data. Multiple game-over updates therefore produce one stats write. |
| C12 | Scores are separate per game and difficulty. Legacy scalar records migrate to Normal. Invalid/null/list values are skipped without startup failure; tests verify migration and independent Hard records. |
| C13 | Shared session startup increments global games_started and per-game games_played, including user-requested restart. Game agents removed end-of-game duplicate increments and defined per-game successful completion milestones. |
| C14 | Achievement progress uses the same visibility rule as the displayed list, including hidden achievements only after unlocking. |
| C15, C16 | `AnimatedFerret` shares decoded source art and scaled/flipped frame sets by source and size. Setting sprite_size now selects/rescales cached drawn frames and collision dimensions together. Tests assert shared image identity and independent sizes. |
| C17, C18 | One-shot special animations expose `animation_finished`; death/disappear hold on the last frame, dig/jump/emerge return to normal states. Idle alternates rather than becoming permanently idle2; enable_sleep is honored and reset restores idle. JSON hash and array exports are accepted, and actual frame durations drive advancement (scaled by frame_delay). |
| C19 | Removed unused constants module and unused GameState/MenuState/GhostState/TileType abstractions instead of claiming games use them. Kept actively used Direction and Difficulty. |
| C20 | Image loaders share a bounded LRU cache by asset root, even when games construct separate loaders. Missing images produce one warning per asset. Removed unused sound, sprite-sheet, preload and unload APIs, including the incorrect Boulder Dash preload path. Audio and AnimatedFerret retain their owning implementations. |
| T1–T3 | Replaced bool-returning print checks with pytest assertions. Added isolated fixtures, atomic failure/recovery, malformed save files, demo isolation, input repeat/mapping/hotplug, audio/mute, frame-cache/size/duration, achievement visibility, session persistence, and fixed-step regressions; 18 construction/draw/update smoke combinations. |

Verification at this stage: `python -m ruff check engine tests/test_engine.py tests/test_smoke.py tests/conftest.py` passes. `python -m pytest engine/test_integration.py tests/test_engine.py tests/test_smoke.py tests/test_launcher.py -q` reports 50 passed (one upstream pygame/pkg_resources deprecation warning). Additional game-agent tests may increase the total in the final project report.

Scope: software tests use SDL dummy display/audio and temporary user data. No Raspberry Pi, actual power-cut test, physical hot-plug, or packaged executable validation was performed by this engine task.


## Follow-up deployment review

The second review fixed issues in the revised deployment code: all pip operations use the selected virtual environment's Python; missing/incomplete environments are repaired; failures stop the command; Linux installation and autostart ensure launcher executable bits; clean is limited to resolved paths inside this project and excludes dependencies/legacy trees. `scripts/autostart_config.py` generates desktop/systemd configuration with literal path quoting, including percent specifiers, dollars, backslashes and spaces, and rejects newline injection. The installer validates configuration before removing old startup entries and adds only device groups present on the target OS.

Quoting references: [Desktop Entry Exec specification](https://specifications.freedesktop.org/desktop-entry/latest-single/) and [systemd.service command-line rules](https://www.freedesktop.org/software/systemd/man/247/systemd.service.html).

`tests/test_deployment.py`: eight behavioral tests passed (venv repair, failed install/build stopping, missing executable reporting, cleanup containment, bundle allowlist, autostart quoting). Its Bash syntax case skips only when Git Bash cannot initialize in the Windows sandbox (0xC0000142). All four shell scripts separately passed `bash -n` outside that sandbox with explicit exit-code checking. No startup service or desktop entry was actually installed during validation.

The launcher can pass `AnimatedFerret.update(..., auto_state=False)` to retain its explicit idle/sleep timing while advancing animation. Production games keep automatic states by default.
