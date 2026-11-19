# Arcade game resolution notes — 2026-11-14

Implementation owner: Snake, Tunnel Treats (`pacman` save ID), and Ferret Crossing.

All three use BaseGame's fixed 60 Hz simulation, shared pause/game-over overlays,
session bookkeeping, demo persistence scope, and exit score saving. Deprecated
`run_*` wrappers were removed. Stored game and achievement IDs remain compatible.

| Finding | Resolution and evidence |
|---|---|
| A1 | `PacmanGame` accepts optional difficulty and forwards it to BaseGame; all three difficulties construct and run in the smoke regression. |
| A5 (these games) | Normal `handle_input()` paths accept scripted confirm/direction input. Snake starts moving; Crossing leaves START. No launcher-only private movement calls are needed. Demo persistence protection is owned by engine/launcher. |
| B1 | Snake and Crossing decorative art uses private `random.Random(42)` generators. Regression checks prove drawing setup preserves global RNG state. |
| C1 / C4 / G-SN1 | Snake's custom loop was removed; all three use shared session tracking, achievement toast, exit score saving and fixed-step loop. All game-over overlays use the shared renderer. |
| C13 | End-of-game duplicate `games_started` / `games_played` increments removed. Wins are a full Snake board, a cleared Tunnel Treats board, or a five-goal Crossing stage; each records global completion. |
| G1 | BaseGame fixed simulation steps decouple all frame-based game timers from render FPS; Snake also retains elapsed movement remainder. Render-only animations do not affect gameplay speed. |
| G2 / G-FR1 | Explicit restarts call `restart_session()` then reset score, counters, animation state, queues, progression and high-score flags. Tunnel Treats now has an explicit restart path too. |
| G3 | Tunnel Treats reads movement only through InputManager. |
| G4 | Removed unused wrappers and duplicated game-over overlays; retained game-specific HUD layouts and difficulty presets for readability. |
| G-SN2 | Movement subtracts each move interval and can consume multiple elapsed intervals. Regression counts exactly 100 Normal moves over 10 simulated seconds. |
| G-SN3 | Collection animation runs concurrently with movement and input; regression turns immediately after food pickup. |
| G-SN4 | Two-turn queue validates against its last queued direction. Quick Up then Left executes in order. |
| G-SN5 | Food selects from finite free cells below the HUD. A full board returns `None`, ends with a win, records the score and renders safely. |
| G-SN6 | Grid-controlled sprites advance animation without `update(0, 0)` reverting them to idle. |
| G-SN7 | Snake speeds up by one move/second per five collected foods, capped at six above the difficulty base. |
| G-PM1 | Board clear saves the record and preserves score and lives through a 90-tick completion message. |
| G-PM2 | Last death enters a persistent game-over state displaying final score; confirm starts a fresh run. |
| G-PM3 | 1,000-point achievement is checked during play as well as final death; a board transition no longer loses progress. |
| G-PM4 | Stages increase ghost speed by 8% (capped at 60%) and shorten power time to a two-second floor. |
| G-PM5 | Cached cave background, wall glows, pellet/power glows, ghost tint frames and eyes; cached power-pellet sizes. Warm render creates zero explicit `pygame.Surface` objects. |
| G-PM6 | Separate 20x20 contact box with inset ghost contact boxes; generous 32x32 pickup box retained. Regression distinguishes grazing from contact. |
| G-FR2 | Death animation advances before the dying branch returns. Last life remains zero on game over. |
| G-FR3 | Two-hop queue samples taps during jumps, death and emergence, then applies them as animation permits. |
| G-FR4 | Five crossings complete a stage (+500 bonus); next stage shifts lane obstacle positions and raises speed 10%, capped at 60%. HUD displays stage and goal progress. |
| G-FR5 | Cached lane scenery, lily pads, flowers and road markings; reused cloud and shimmer surfaces. Warm render creates zero explicit `pygame.Surface` objects. |
| G-FR6 | Uses pygame's bundled default font rather than platform-dependent Courier New lookup. |
| R4 (active maze art) | Replaced branded soup-can ghost image with original procedural garden critters. Display title is Tunnel Treats; existing save IDs remain `pacman`. |
| R5 (owned files) | Ruff unused-name checks pass. |

Validation: `python -m pytest tests/test_arcade_games.py -q` reports **25 passed**.
The cases cover 300 simulated frames for every game/difficulty, actual input,
movement timing, buffered turns, score retention, game-over/restart, stage
progression, collision margins, animation frames, RNG isolation and reusable
render surfaces. The only emitted warning is pygame's upstream pkg_resources
deprecation. Tests use the shared temporary-data fixture; no real saves are used.

Visual review: inspected screenshots of all three gameplay screens in
`docs/verification/2026-11-14/` (`snake.png`, `tunnel-treats.png`,
`ferret-crossing.png`). Text, goals and artwork fit the logical 800x600 canvas.
These are desktop headless checks, not Raspberry Pi hardware measurements.

Independent launcher review: `tests/test_launcher_review.py` adds **10 passing**
regressions. It reproduced and then verified the fixes for menu sleep being
overwritten, moving animation resetting every frame, stale fullscreen status
under CLI overrides, and demo dismissal by M. Six additional cases record 180
normal input/update steps per demo and prove that every player moves, Crossing
starts, Defender fires while remaining on screen, and Rocky Burrow's visual
sprite stays aligned to its tile. No game-state shortcuts are used by these
probes or by the launcher demo driver.

Final input review found and fixed a further short-tap defect: a press and release
arriving in the same SDL event batch were discarded by held-state polling.
`InputManager` now retains press/release edges until the next simulation update,
provides a single-step action pulse for automatic-fire consumers, and queues
bounded keyboard/hat/axis direction changes with release transitions. Seven
regressions in `tests/test_input_review.py` cover these cases, held-key behavior,
and one short Space tap firing exactly once. The combined relevant suite reports
**89 passed** (engine, smoke, launcher, both review suites, and arcade games).
The active bundled font, three media files and seven sounds were also confirmed
present in the PyInstaller output; the final bundle must be rebuilt after the
input change.
