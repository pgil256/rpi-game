# Action-game audit resolution notes — 2026-11-14

Scope: `games/centipede.py`, `games/digdug.py`, `games/boulderdash.py`, and `tests/test_action_games.py`. Display names are Burrow Defender, Crystal Quest, and Rocky Burrow; module/save IDs remain compatible.

## Shared findings

| IDs | Resolution and evidence |
|---|---|
| G1 | All three run through `BaseGame.advance()` at fixed 60 Hz, decoupling simulation from render frequency. Movement lives in simulation updates, and Boulder gravity has its own elapsed-time accumulator. The engine owns fixed-step/catch-up tests. |
| G2 | Each fresh run resets score, death/collectible/enemy counters, level/wave, terminal flags, and `new_high_score`. Restarts call `restart_session()` once; old game-end `games_started`/`games_played` increments were removed. Regression tests cover terminal state and fresh-session counts. |
| G3 | Centipede and Dig Dug consume only the input manager's normalized keyboard/gamepad state; raw key polling and duplicate shooting were removed. |
| G4 / C1 | All three use shared pause and game-over overlays and shared session bookkeeping. Unused `run_*` wrappers/imports were removed. Game-specific scenery and progression remain separate because their rules differ. |
| C4 / C12 / C13 | All three now expose a points `score` for shared exit saving, explicitly select difficulty-specific records, and record meaningful level/wave completions. `BaseGame` counts starts, while end counters are recorded once. |
| A5 | Demos use ordinary input/update APIs; no private movement shortcut is necessary. Engine persistence sessions suppress demo writes. |
| R4 / R5 | Branded can sprites were replaced with original procedural beetle art, and unused imports/variables were removed. Root handles the asset archive/provenance policy. |

## Burrow Defender (Centipede)

| ID | Resolution |
|---|---|
| G-CE1 | Final death retains lives=0 and final score. A real game-over overlay appears after the death animation; A/Enter starts a clean session. |
| G-CE2 | Segments reverse vertical direction in the player area and clamp horizontal bounds, so dodged segments remain available to shoot. A regression runs 15,000 segment steps. |
| G-CE3 | Keyboard and gamepad share one held-action firing cadence (eight simulation ticks) with a three-bullet cap. One press no longer fires twice. |
| G-CE4 | Player art and collision bounds are both 32 pixels; clamping uses that same size. Movement normalizes diagonals. |
| G-CE5 | Death advances the ferret animation for 60 simulation ticks, then respawns or enters game over. |
| G-CE6 | Destruction/flea spawning is capped at 80 soup bowls; additions avoid duplicate occupied cells. Fleas cannot lay obstacles outside the upper playfield. |
| G-CE7 | Clearing a wave increases segment count up to 20 and speed up to six, and increments a completion milestone. |
| G-CE8 / B1 | Garden scenery is rendered once; reusable glow sprites replace per-entity allocations. Garden randomness uses `random.Random(42)` without reseeding gameplay. |

## Crystal Quest (Dig Dug)

| ID | Resolution |
|---|---|
| G-DD1 | Enemies test every overlapped terrain cell plus boulders before moving. They patrol initially excavated burrows; player-dug connections change the routes they can follow. |
| G-DD2 | Three lives, three depths, randomized separated layouts, increasing crystal targets (3/4/5), escalating enemy counts/speeds, 100-point crystals and 500×depth completion bonuses replace the fixed three-point game. |
| G-DD3 | A shared occupied-position allocator prevents enemy/boulder/player/objective overlap on all difficulties. |
| G-DD4 | Player art is 32px with a deliberate 28px inner collision box; enemy art is 28px. Diagonal input is normalized to the same four-pixel speed as cardinal movement. |
| G-DD5 | Restart resets all session counters, terminal flags, high-score notification, lives and depth. |
| G-DD6 | Collection/emergence remains visible for a 40-tick special-animation window. Death continues animating for 60 ticks before respawn/game-over. |
| G-DD7 | Terrain is cached and redraws only excavated cells plus neighboring edges. HUD and 24 crystal glow frames are cached. |
| G-DD8 | Collection uses direct rect overlap against the small crystal group; no per-frame throwaway Python class is created. |

## Rocky Burrow (Boulder Dash)

| ID | Resolution |
|---|---|
| G-BD1 | A resting object is supported by the player; only an already-falling rock/diamond can crush. Tests distinguish resting and moving objects of both types. |
| G-BD2 | Safe spawn excludes both rocks and diamonds directly above the player. |
| G-BD3 | Flood-fill connectivity checks identify sealed objectives; dirt passages connect them to the player's reachable area, removing blocking wall/rock cells. The test suite validates 900 generated maps (60 seeds × 5 levels × 3 difficulties). Pause → A explicitly retries the original level for one life if player actions create a dead end. This verifies structural reachability, not an exhaustive dynamic puzzle solver. |
| G-BD4 | Gravity advances one tile per 0.15 seconds rather than every frame. Unsupported rocks have a visible outline and an audible falling cue. |
| G-BD5 | `_try_move` itself rejects pause/dying/completed/terminal states and diagonal/non-unit moves; every successful move synchronizes the ferret position. |
| G-BD6 | Held cardinal input repeats every eight simulation ticks. Diagonal input is neutral, preventing spurious moves while rolling the d-pad. |
| G-BD7 | A fresh session resets all collectible/level/death counters and the high-score notification. A level retry rolls back that attempt's points/diamonds to prevent farming and retains the death penalty. |
| G-BD8 | A single bottom-to-top sorted list processes rocks and diamonds, independent of insertion order. Each object advances at most once per gravity tick. |
| G-BD9 | Dense-level scattered walls are added once. Layouts that generate their own walls no longer advertise ignored wall-count fields. |
| G-BD10 | Diamonds give 100 points, level completion gives 500×level, and a full win adds 2,000. Score and difficulty-specific high score are visible; full wins differ from dying on level five. |
| G-BD11 | Normal death preserves the current cave and collected treasure, respawning safely in that cave. Explicit retry uses the saved original layout instead of new randomness. The exceptional no-safe-respawn fallback also restores that same layout. |
| G-BD12 | Pushing clears stale falling/bounce entries and creates fresh tracking at the new cell. |
| G-BD13 | Particle canvases are allocated once per particle, sparkle frames and rock bounce scales are cached, and overlay fonts/full-screen surfaces are reused. HUD received a cached dark backing for contrast. |
| G-BD14 | Diamond-target docstrings now describe the per-level target. Root quarantines unused legacy level files/assets outside active code/package inputs. |

## Verification

- `python -m pytest tests/test_action_games.py tests/test_smoke.py -q`: **44 passed** (26 action regressions plus 18 game/difficulty smoke cases).
- `python -m ruff check games/centipede.py games/digdug.py games/boulderdash.py tests/test_action_games.py`: passed; these files were formatted with Ruff.
- Explicit `pygame.Surface` constructor instrumentation reports **zero new surfaces per warmed-up render/update frame** for all three at rest. This counts explicit surface allocations, not font-render output or allocations when spawning new entities.
- Inspected headless screenshots of all three initial boards for visible layout and HUD placement. Raspberry Pi performance and physical-controller play remain part of the root's hardware validation limits.

## Follow-up lifecycle review

An independent pass reproduced lost pending game totals on early exit in all six games: high scores were saved, but an earned crystal, diamond, segment kill, crossing/death, snake length, or score total could be omitted from statistics when returning before game over. `BaseGame._finalize_game_statistics()` now invokes each game's cumulative-statistics hook exactly once, both at terminal state and from the shared exit/finally path. Restart resets that bookkeeping before the next run. Deaths already animating at exit are included, and demo scopes prevent mutations.

`tests/test_session_statistics.py` adds 18 cases across all six games: early exit writes totals/score once, terminal→restart avoids duplication and records the next run, and demo terminal→restart→exit leaves real scores/stats/achievements/files untouched. The focused integration run (session, arcade, action, engine suites) passed **84 tests**.

The follow-up cave review found and fixed an idle spawn trap in Hard maze seeds 676 and 931: clearing the dirt beside the player removed support from two rocks, which fell into both exits on the first gravity tick. Spawn now excavates only the player cell; neighboring diggable dirt remains supporting. Dedicated regressions cover both seeds, and all 900 generated-layout checks now also verify objective connectivity after 20 idle gravity ticks. This remains a structural/initial-gravity guarantee, not an exhaustive solver for every sequence of player moves. The updated action plus lifecycle suites passed **46 tests**.
