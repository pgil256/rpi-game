# Audit resolution ledger - 2026-11-14

All **117** findings in [the original audit](2026-11-14-audit-findings.md) have an
implementation or explicit disposition below. The audit remains before-state
evidence. This maintenance work does not authorize a public release.

## Verification

- **147 passed, 1 skipped** in the final source suite (`python -m pytest -q`).
  The skip is Git Bash initialization inside the Windows sandbox; all four shell
  scripts separately passed `bash -n` outside that sandbox. One upstream Pygame
  `pkg_resources` deprecation warning remains in the development environment.
- `python -m ruff check .` and `python -m ruff format --check .`: passed.
- Source `python game_launcher.py --smoke-test`: exit 0; six games, three
  difficulties, 300 simulation steps each, with temporary data.
- Windows PyInstaller build: passed. `dist/wes/wes.exe --smoke-test`:
  **exit 0 in 3.75 s**, exercising the same 18 combinations using bundled assets.
  The 35.4 MiB bundle contains three media files and seven generated WAVs.
  The first build exposed a missing `jaraco` import in an optional pkg_resources
  bootstrap hook; excluding unused pkg_resources/numpy fixed it, and the corrected
  bundle was rebuilt and retested.
- Warm-render probe: zero explicit `pygame.Surface` constructors per frame for
  the six games and main menu in the sampled states. Game median render times
  were 0.12-0.73 ms on this desktop; these are not Pi benchmarks and exclude
  entity-spawn/font-output allocation costs.
- Attached HID gamepad (10 buttons, five axes) retained its original initialized
  handle after a second InputManager was created; see
  [controller probe](../verification/2026-11-14/controller-probe.json).
- All 167 archived files match the baseline Git blobs. Existing local score and
  personal launch files were verified unchanged before being removed from tracking.
- Late review adds short-tap retention, idempotent early-exit statistics,
  achievement save retry/shutdown flush, and cave spawn-support regression checks.

Evidence: [engine notes](engine-resolution-notes.md), [arcade notes](arcade-resolution-notes.md),
[action notes](action-resolution-notes.md), [launcher/deployment notes](launcher-resolution-notes.md),
and [render measurements](../verification/2026-11-14/render-metrics.json).
Screenshots in that verification folder were visually inspected. Reproduce with
`python scripts/verify_rendering.py`. The executable's `--smoke-test` uses temporary
data and dummy SDL automatically.

## External verification and release conditions

- Raspberry Pi boot/display/audio and physical unplug/replug require hardware
  acceptance. Headless Windows tests establish neither Pi performance nor boot success.
- Atomic-write interruption is simulated, not a physical power-cut experiment.
- Cave tests check structural reachability across 900 generated maps before and
  after idle gravity, plus known trap seeds 676/931, not an
  exhaustive dynamic puzzle solver. Same-layout retry handles player-created dead ends.
- R4 is addressed by containment, **not cleared for publication**. Ownership and
  permissions for pre-existing code, ferret/bowl artwork, and an owner-selected
  license remain necessary. See [the rights inventory](../../THIRD_PARTY_NOTICES.md).

## Finding dispositions

| ID | Disposition | Change / evidence |
|---|---|---|
| A1 | Resolved | All constructors accept difficulty; all-game/all-difficulty smoke coverage. [Details](launcher-resolution-notes.md). |
| A2 | Resolved | Validated audio preferences apply at startup and live; M persists. Fullscreen honors saved preferences and CLI overrides, with Settings showing actual display state. [Details](launcher-resolution-notes.md). |
| A3 | Resolved | Launcher shares one InputManager across screens and demos never open/reset hardware. [Details](launcher-resolution-notes.md). |
| A4 | Resolved | Shared edge/repeat navigation; no duplicate keyboard direction branch; settings flush one update on exit. [Details](launcher-resolution-notes.md). |
| A5 | Resolved | ScriptedInput calls normal handle_input/update inside demo persistence protection. Tests prove all six games move, Defender fires, Boulder sprite stays aligned, and saves/achievements remain unchanged. Recording API removed. [Details](launcher-resolution-notes.md). |
| A6 | Resolved | Validated audio preferences apply at startup and live; M persists. Fullscreen honors saved preferences and CLI overrides, with Settings showing actual display state. [Details](launcher-resolution-notes.md). |
| B1 | Resolved | Private Random(42) generators for decorations preserve gameplay randomness. [Details](launcher-resolution-notes.md). |
| B2 | Resolved | WASD remains movement; F1/F2/F3 open settings/achievements/stats. [Details](launcher-resolution-notes.md). |
| B3 | Resolved | Controller-accessible Options includes every utility screen and Quit. [Details](launcher-resolution-notes.md). |
| B4 | Resolved | Activity resets idle; look-around at 15 s, sleep at 30 s, attract at 60 s. Explicit menu state policy preserves animation progression. [Details](launcher-resolution-notes.md). |
| B5 | Resolved | Static decorations/title/help and button labels cached; shared cached toast. [Details](launcher-resolution-notes.md). |
| B6 | Resolved | Hover updated every frame; fullscreen mouse coordinates map through the viewport. [Details](launcher-resolution-notes.md). |
| B7 | Resolved | Title and help use measured centering, fit 800 pixels and were visually inspected. [Details](launcher-resolution-notes.md). |
| B8 | Resolved | Controller test shows no-device feedback, stays open and accepts hot-plug. [Details](launcher-resolution-notes.md). |
| B9 | Resolved | Common close flag and BaseGame quit_requested propagation; no submenu sys.exit. [Details](launcher-resolution-notes.md). |
| B10 | Resolved | Seven 54-pixel rows leave a separate scroll/help region. [Details](launcher-resolution-notes.md). |
| B11 | Resolved | Stable logical surface; display mode changes only at startup or preference change. [Details](launcher-resolution-notes.md). |
| B12 | Resolved | 4:3 letterboxing with reused scale destination; coordinate mapping regression. [Details](launcher-resolution-notes.md). |
| B13 | Resolved | Crash guard with readable return panel and rotating wes.log; shutdown/persistence errors logged. [Details](launcher-resolution-notes.md). |
| B14 | Resolved | Consistent Winston Entertainment System/Ferret Crossing naming; neutral game display names retain compatible save IDs. [Details](launcher-resolution-notes.md). |
| B15 | Resolved | Removed unused wrappers/imports; shared AchievementToast; Ruff checks and formatter. [Details](launcher-resolution-notes.md). |
| C1 | Resolved | All three use shared pause and game-over overlays and shared session bookkeeping. Unused `run_*` wrappers/imports were removed. Game-specific scenery and progression remain separate because their rules differ. [Details](action-resolution-notes.md). |
| C2 | Resolved | `BaseGame.advance(elapsed)` runs fixed 1/FPS simulation steps, handles input per step, and limits elapsed catch-up to 250 ms. `run()` uses the shared FPS value. Tests compare 30 and 60 display updates and verify stall bounds. The launcher applies equivalent fixed-step timing to scripted demos. [Details](engine-resolution-notes.md). |
| C3 | Resolved | `BaseGame` owns restart session accounting, cached pause/game-over overlays, and a shared `AchievementToast` used by the launcher. Game agents integrated the restart/overlay helpers while retaining game-specific transitions. Toast background/text are generated only for new notifications. [Details](engine-resolution-notes.md). |
| C4 | Resolved | All three now expose a points `score` for shared exit saving, explicitly select difficulty-specific records, and record meaningful level/wave completions. `BaseGame` counts starts, while end counters are recorded once. [Details](action-resolution-notes.md). |
| C5 | Resolved | `menu_direction()` returns one immediate direction then repeats after 250 ms, every 120 ms; diagonal input resolves to one axis. Enter/A are action, Start/P are pause; `confirm_pressed()` adds Start for menus. Configured mappings feed compatibility helpers. Constants come from one definition. Module-level `get_dpad()` never advances input state. [Details](engine-resolution-notes.md). |
| C6 | Resolved | `menu_direction()` returns one immediate direction then repeats after 250 ms, every 120 ms; diagonal input resolves to one axis. Enter/A are action, Start/P are pause; `confirm_pressed()` adds Start for menus. Configured mappings feed compatibility helpers. Constants come from one definition. Module-level `get_dpad()` never advances input state. [Details](engine-resolution-notes.md). |
| C7 | Resolved | `menu_direction()` returns one immediate direction then repeats after 250 ms, every 120 ms; diagonal input resolves to one axis. Enter/A are action, Start/P are pause; `confirm_pressed()` adds Start for menus. Configured mappings feed compatibility helpers. Constants come from one definition. Module-level `get_dpad()` never advances input state. [Details](engine-resolution-notes.md). |
| C8 | Resolved | Input construction no longer quits the global joystick subsystem. Device-added/removed events reacquire handles; 500 ms polling recovers absent/invalid handles even when a caller does not forward events. Hardware-free tests verify no subsystem quit and reconnection. Physical unplug/replug still needs device verification. [Details](engine-resolution-notes.md). |
| C9 | Resolved | Shared `JsonStore`: UTF-8 JSON, validated top-level structure, fsynced temporary file + atomic replacement, previous good `.bak`, logged errors and `last_error`, preserved `.corrupt-*` data and backup recovery. POSIX parent directory is fsynced after replacement. Default saves use `%LOCALAPPDATA%/WES` or `$XDG_DATA_HOME/wes` (`~/.local/share/wes` fallback). `WES_DATA_DIR` overrides all data paths for tests/portable use. Legacy project saves import only when no override is set; originals remain untouched. [Details](engine-resolution-notes.md). |
| C10 | Resolved | Shared `JsonStore`: UTF-8 JSON, validated top-level structure, fsynced temporary file + atomic replacement, previous good `.bak`, logged errors and `last_error`, preserved `.corrupt-*` data and backup recovery. POSIX parent directory is fsynced after replacement. Default saves use `%LOCALAPPDATA%/WES` or `$XDG_DATA_HOME/wes` (`~/.local/share/wes` fallback). `WES_DATA_DIR` overrides all data paths for tests/portable use. Legacy project saves import only when no override is set; originals remain untouched. [Details](engine-resolution-notes.md). |
| C11 | Resolved | Stats setters mark a batch dirty; the shared loop flushes once after each simulation step, and session close flushes remaining data. Multiple game-over updates therefore produce one stats write. [Details](engine-resolution-notes.md). |
| C12 | Resolved | All three now expose a points `score` for shared exit saving, explicitly select difficulty-specific records, and record meaningful level/wave completions. `BaseGame` counts starts, while end counters are recorded once. [Details](action-resolution-notes.md). |
| C13 | Resolved | All three now expose a points `score` for shared exit saving, explicitly select difficulty-specific records, and record meaningful level/wave completions. `BaseGame` counts starts, while end counters are recorded once. [Details](action-resolution-notes.md). |
| C14 | Resolved | Achievement progress uses the same visibility rule as the displayed list, including hidden achievements only after unlocking. [Details](engine-resolution-notes.md). |
| C15 | Resolved | `AnimatedFerret` shares decoded source art and scaled/flipped frame sets by source and size. Setting sprite_size now selects/rescales cached drawn frames and collision dimensions together. Tests assert shared image identity and independent sizes. [Details](engine-resolution-notes.md). |
| C16 | Resolved | `AnimatedFerret` shares decoded source art and scaled/flipped frame sets by source and size. Setting sprite_size now selects/rescales cached drawn frames and collision dimensions together. Tests assert shared image identity and independent sizes. [Details](engine-resolution-notes.md). |
| C17 | Resolved | One-shot special animations expose `animation_finished`; death/disappear hold on the last frame, dig/jump/emerge return to normal states. Idle alternates rather than becoming permanently idle2; enable_sleep is honored and reset restores idle. JSON hash and array exports are accepted, and actual frame durations drive advancement (scaled by frame_delay). [Details](engine-resolution-notes.md). |
| C18 | Resolved | One-shot special animations expose `animation_finished`; death/disappear hold on the last frame, dig/jump/emerge return to normal states. Idle alternates rather than becoming permanently idle2; enable_sleep is honored and reset restores idle. JSON hash and array exports are accepted, and actual frame durations drive advancement (scaled by frame_delay). [Details](engine-resolution-notes.md). |
| C19 | Removed unused API | Removed unused constants module and unused GameState/MenuState/GhostState/TileType abstractions instead of claiming games use them. Kept actively used Direction and Difficulty. [Details](engine-resolution-notes.md). |
| C20 | Removed unused API | Image loaders share a bounded LRU cache by asset root, even when games construct separate loaders. Missing images produce one warning per asset. Removed unused sound, sprite-sheet, preload and unload APIs, including the incorrect Boulder Dash preload path. Audio and AnimatedFerret retain their owning implementations. [Details](engine-resolution-notes.md). |
| C21 | Removed unused API | Scoped `persistence_session(demo=True)` prevents score/stat/settings/achievement mutations as well as disk writes. `BaseGame` recognizes `input.demo_mode`. Unused recording/playback manager removed; launcher uses scripted normal input. No demo folder is created. All six games run 300 frames at all difficulties with zero save-directory creation; launcher tests also cover 900 frames per game. [Details](engine-resolution-notes.md). |
| G1 | Resolved | All three run through `BaseGame.advance()` at fixed 60 Hz, decoupling simulation from render frequency. Movement lives in simulation updates, and Boulder gravity has its own elapsed-time accumulator. The engine owns fixed-step/catch-up tests. [Details](action-resolution-notes.md). |
| G2 | Resolved | Each fresh run resets score, death/collectible/enemy counters, level/wave, terminal flags, and `new_high_score`. Restarts call `restart_session()` once; old game-end `games_started`/`games_played` increments were removed. Regression tests cover terminal state and fresh-session counts. [Details](action-resolution-notes.md). |
| G3 | Resolved | Centipede and Dig Dug consume only the input manager's normalized keyboard/gamepad state; raw key polling and duplicate shooting were removed. [Details](action-resolution-notes.md). |
| G4 | Resolved | Shared lifecycle/overlays/toast; unused wrappers removed. Game-specific HUD/art/difficulty configuration deliberately stays local. [Details](launcher-resolution-notes.md). |
| G-SN1 | Resolved | Snake's custom loop was removed; all three use shared session tracking, achievement toast, exit score saving and fixed-step loop. All game-over overlays use the shared renderer. [Details](arcade-resolution-notes.md). |
| G-SN2 | Resolved | Movement subtracts each move interval and can consume multiple elapsed intervals. Regression counts exactly 100 Normal moves over 10 simulated seconds. [Details](arcade-resolution-notes.md). |
| G-SN3 | Resolved | Collection animation runs concurrently with movement and input; regression turns immediately after food pickup. [Details](arcade-resolution-notes.md). |
| G-SN4 | Resolved | Two-turn queue validates against its last queued direction. Quick Up then Left executes in order. [Details](arcade-resolution-notes.md). |
| G-SN5 | Resolved | Food selects from finite free cells below the HUD. A full board returns `None`, ends with a win, records the score and renders safely. [Details](arcade-resolution-notes.md). |
| G-SN6 | Resolved | Grid-controlled sprites advance animation without `update(0, 0)` reverting them to idle. [Details](arcade-resolution-notes.md). |
| G-SN7 | Resolved | Snake speeds up by one move/second per five collected foods, capped at six above the difficulty base. [Details](arcade-resolution-notes.md). |
| G-PM1 | Resolved | Board clear saves the record and preserves score and lives through a 90-tick completion message. [Details](arcade-resolution-notes.md). |
| G-PM2 | Resolved | Last death enters a persistent game-over state displaying final score; confirm starts a fresh run. [Details](arcade-resolution-notes.md). |
| G-PM3 | Resolved | 1,000-point achievement is checked during play as well as final death; a board transition no longer loses progress. [Details](arcade-resolution-notes.md). |
| G-PM4 | Resolved | Stages increase ghost speed by 8% (capped at 60%) and shorten power time to a two-second floor. [Details](arcade-resolution-notes.md). |
| G-PM5 | Resolved | Cached cave background, wall glows, pellet/power glows, ghost tint frames and eyes; cached power-pellet sizes. Warm render creates zero explicit `pygame.Surface` objects. [Details](arcade-resolution-notes.md). |
| G-PM6 | Resolved | Separate 20x20 contact box with inset ghost contact boxes; generous 32x32 pickup box retained. Regression distinguishes grazing from contact. [Details](arcade-resolution-notes.md). |
| G-FR1 | Resolved | Explicit restarts call `restart_session()` then reset score, counters, animation state, queues, progression and high-score flags. Tunnel Treats now has an explicit restart path too. [Details](arcade-resolution-notes.md). |
| G-FR2 | Resolved | Death animation advances before the dying branch returns. Last life remains zero on game over. [Details](arcade-resolution-notes.md). |
| G-FR3 | Resolved | Two-hop queue samples taps during jumps, death and emergence, then applies them as animation permits. [Details](arcade-resolution-notes.md). |
| G-FR4 | Resolved | Five crossings complete a stage (+500 bonus); next stage shifts lane obstacle positions and raises speed 10%, capped at 60%. HUD displays stage and goal progress. [Details](arcade-resolution-notes.md). |
| G-FR5 | Resolved | Cached lane scenery, lily pads, flowers and road markings; reused cloud and shimmer surfaces. Warm render creates zero explicit `pygame.Surface` objects. [Details](arcade-resolution-notes.md). |
| G-FR6 | Resolved | Uses pygame's bundled default font rather than platform-dependent Courier New lookup. [Details](arcade-resolution-notes.md). |
| G-CE1 | Resolved | Final death retains lives=0 and final score. A real game-over overlay appears after the death animation; A/Enter starts a clean session. [Details](action-resolution-notes.md). |
| G-CE2 | Resolved | Segments reverse vertical direction in the player area and clamp horizontal bounds, so dodged segments remain available to shoot. A regression runs 15,000 segment steps. [Details](action-resolution-notes.md). |
| G-CE3 | Resolved | Keyboard and gamepad share one held-action firing cadence (eight simulation ticks) with a three-bullet cap. One press no longer fires twice. [Details](action-resolution-notes.md). |
| G-CE4 | Resolved | Player art and collision bounds are both 32 pixels; clamping uses that same size. Movement normalizes diagonals. [Details](action-resolution-notes.md). |
| G-CE5 | Resolved | Death advances the ferret animation for 60 simulation ticks, then respawns or enters game over. [Details](action-resolution-notes.md). |
| G-CE6 | Resolved | Destruction/flea spawning is capped at 80 soup bowls; additions avoid duplicate occupied cells. Fleas cannot lay obstacles outside the upper playfield. [Details](action-resolution-notes.md). |
| G-CE7 | Resolved | Clearing a wave increases segment count up to 20 and speed up to six, and increments a completion milestone. [Details](action-resolution-notes.md). |
| G-CE8 | Resolved | Garden scenery is rendered once; reusable glow sprites replace per-entity allocations. Garden randomness uses `random.Random(42)` without reseeding gameplay. [Details](action-resolution-notes.md). |
| G-DD1 | Resolved | Enemies test every overlapped terrain cell plus boulders before moving. They patrol initially excavated burrows; player-dug connections change the routes they can follow. [Details](action-resolution-notes.md). |
| G-DD2 | Resolved | Three lives, three depths, randomized separated layouts, increasing crystal targets (3/4/5), escalating enemy counts/speeds, 100-point crystals and 500×depth completion bonuses replace the fixed three-point game. [Details](action-resolution-notes.md). |
| G-DD3 | Resolved | A shared occupied-position allocator prevents enemy/boulder/player/objective overlap on all difficulties. [Details](action-resolution-notes.md). |
| G-DD4 | Resolved | Player art is 32px with a deliberate 28px inner collision box; enemy art is 28px. Diagonal input is normalized to the same four-pixel speed as cardinal movement. [Details](action-resolution-notes.md). |
| G-DD5 | Resolved | Restart resets all session counters, terminal flags, high-score notification, lives and depth. [Details](action-resolution-notes.md). |
| G-DD6 | Resolved | Collection/emergence remains visible for a 40-tick special-animation window. Death continues animating for 60 ticks before respawn/game-over. [Details](action-resolution-notes.md). |
| G-DD7 | Resolved | Terrain is cached and redraws only excavated cells plus neighboring edges. HUD and 24 crystal glow frames are cached. [Details](action-resolution-notes.md). |
| G-DD8 | Resolved | Collection uses direct rect overlap against the small crystal group; no per-frame throwaway Python class is created. [Details](action-resolution-notes.md). |
| G-BD1 | Resolved | A resting object is supported by the player; only an already-falling rock/diamond can crush. Tests distinguish resting and moving objects of both types. [Details](action-resolution-notes.md). |
| G-BD2 | Resolved | Safe spawn excludes both rocks and diamonds directly above the player. [Details](action-resolution-notes.md). |
| G-BD3 | Resolved | Flood-fill connectivity checks identify sealed objectives; dirt passages connect them to the player's reachable area, removing blocking wall/rock cells. The test suite validates 900 generated maps (60 seeds × 5 levels × 3 difficulties). Pause → A explicitly retries the original level for one life if player actions create a dead end. This verifies structural reachability, not an exhaustive dynamic puzzle solver. [Details](action-resolution-notes.md). |
| G-BD4 | Resolved | Gravity advances one tile per 0.15 seconds rather than every frame. Unsupported rocks have a visible outline and an audible falling cue. [Details](action-resolution-notes.md). |
| G-BD5 | Resolved | `_try_move` itself rejects pause/dying/completed/terminal states and diagonal/non-unit moves; every successful move synchronizes the ferret position. [Details](action-resolution-notes.md). |
| G-BD6 | Resolved | Held cardinal input repeats every eight simulation ticks. Diagonal input is neutral, preventing spurious moves while rolling the d-pad. [Details](action-resolution-notes.md). |
| G-BD7 | Resolved | A fresh session resets all collectible/level/death counters and the high-score notification. A level retry rolls back that attempt's points/diamonds to prevent farming and retains the death penalty. [Details](action-resolution-notes.md). |
| G-BD8 | Resolved | A single bottom-to-top sorted list processes rocks and diamonds, independent of insertion order. Each object advances at most once per gravity tick. [Details](action-resolution-notes.md). |
| G-BD9 | Resolved | Dense-level scattered walls are added once. Layouts that generate their own walls no longer advertise ignored wall-count fields. [Details](action-resolution-notes.md). |
| G-BD10 | Resolved | Diamonds give 100 points, level completion gives 500×level, and a full win adds 2,000. Score and difficulty-specific high score are visible; full wins differ from dying on level five. [Details](action-resolution-notes.md). |
| G-BD11 | Resolved | Normal death preserves the current cave and collected treasure, respawning safely in that cave. Explicit retry uses the saved original layout instead of new randomness. The exceptional no-safe-respawn fallback also restores that same layout. [Details](action-resolution-notes.md). |
| G-BD12 | Resolved | Pushing clears stale falling/bounce entries and creates fresh tracking at the new cell. [Details](action-resolution-notes.md). |
| G-BD13 | Resolved | Particle canvases are allocated once per particle, sparkle frames and rock bounce scales are cached, and overlay fonts/full-screen surfaces are reused. HUD received a cached dark backing for contrast. [Details](action-resolution-notes.md). |
| G-BD14 | Resolved | Diamond-target docstrings now describe the per-level target. Root quarantines unused legacy level files/assets outside active code/package inputs. [Details](action-resolution-notes.md). |
| D1 | Resolved | Quoted requirements-file install removes accidental version-string redirection. [Details](launcher-resolution-notes.md). |
| D2 | Fixed; Pi acceptance pending | Isolated .venv with pinned requirements; no system pip or break-system-packages. [Details](launcher-resolution-notes.md). |
| D3 | Fixed; Pi acceptance pending | One start.sh launch path using .venv; SDL desktop/audio selection respects Wayland and overrides. [Details](launcher-resolution-notes.md). |
| D4 | Fixed; Pi acceptance pending | One desktop/console backend, real account/home, correct ownership, quoted generated configuration, executable scripts, console Restart=always and flock. Hardware boot acceptance remains required. [Details](launcher-resolution-notes.md). |
| D5 | Resolved | Explicit active-asset allowlist; no archived executable/audio, docs, saves or demos bundled. Writable user data remains outside the bundle. [Details](launcher-resolution-notes.md). |
| D6 | Resolved | .gitattributes, LF active source/scripts/docs, executable shell file modes. [Details](launcher-resolution-notes.md). |
| D7 | Resolved | Pinned runtime/development dependencies, Python >=3.10, Windows/Linux 3.10/3.12 CI. [Details](launcher-resolution-notes.md). |
| R1 | Resolved | Local Git baseline, CI, lint/format config. LICENSE grants no new public rights pending owner/provenance review. [Details](launcher-resolution-notes.md). |
| R2 | Resolved | Correct save/config/log ignores; personal launch.txt and real score file preserved locally but untracked. [Details](launcher-resolution-notes.md). |
| R3 | Resolved | Unused game folders/media preserved in legacy_reference, excluded from runtime build/tests/lint. [Details](launcher-resolution-notes.md). |
| R4 | Addressed; public release blocked | Procedural enemy art removes branding; neutral titles; third-party archive quarantined. Rights inventory and restrictive notice added. Public release remains blocked pending owner evidence for existing code/ferret/bowl artwork and a license decision. [Details](launcher-resolution-notes.md). |
| R5 | Resolved | Active Ruff unused-name/import checks pass; historical source remains untouched. [Details](launcher-resolution-notes.md). |
| T1 | Resolved | Assertions replace print/bool/tautology tests; returned-value warnings fail pytest. [Details](launcher-resolution-notes.md). |
| T2 | Resolved | Isolated regressions cover persistence, input, gameplay/lifecycle, launcher and demos. [Details](launcher-resolution-notes.md). |
| T3 | Resolved | 300 simulated steps for all 18 game/difficulty combinations; packaged --smoke-test exercises bundled code/assets with temporary saves. [Details](launcher-resolution-notes.md). |
| X1 | Resolved | Config-file/diagnostic workflow documented instead of source constant editing. [Details](launcher-resolution-notes.md). |
| X2 | Resolved | Configured hat/axes and auto hat then axes 0/1 documented; removed axis-4 claim. [Details](launcher-resolution-notes.md). |
| X3 | Resolved | Current launcher/engine/games architecture replaces stale line-count/embedded-game claims. [Details](launcher-resolution-notes.md). |
| X4 | Resolved | Difficulty, scores, settings, achievements, stats, scripted demos and packaging documented. [Details](launcher-resolution-notes.md). |
| X5 | Resolved | Current 15/30/60-second idle thresholds documented. [Details](launcher-resolution-notes.md). |
| X6 | Resolved | All shortcuts and controller equivalents documented, preserving WASD. [Details](launcher-resolution-notes.md). |
| X7 | Resolved | Historical plan marked superseded; inaccurate completion claims identified. [Details](launcher-resolution-notes.md). |
