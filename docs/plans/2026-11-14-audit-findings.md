# WES audit findings — 2026-11-14

Audit of the whole project (launcher, `engine/`, six games, Pi scripts, packaging, docs).
This file preserves the original audit before-state. Repairs and verification are tracked in
[the resolution ledger](2026-11-14-audit-resolution.md), which addresses all 117 finding IDs.

## How to read this

Every finding has an ID and a verification tag:

| Tag | Meaning |
|---|---|
| **[R]** | Reproduced at runtime during the audit (headless, in a throwaway copy of the project) |
| **[S]** | Confirmed by reading the source lines cited |
| **[A]** | Measured by a reviewer's runtime probe; not re-run afterwards |
| **[P]** | Plausible, not verified (mostly Raspberry Pi behaviour — nothing was run on a Pi) |

Line numbers refer to the files as they were on 2026-11-14.

## Before you change anything

- **The project is not a git repository.** Consider `git init` and a first commit before editing, so changes are reviewable. (Owner's call.)
- **Save files are written next to the code**: `high_scores.json`, `settings.json`, `stats.json`, `achievements.json`, `controller_config.json`, and a `demos/` folder. Running the launcher or any game from the project folder writes them. For experiments, work in a copy or redirect the managers to a temp folder.
- **Headless runs**: set `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.
- **`game_launcher.py` has import-time side effects**: it calls `argparse.parse_args()`, `pygame.init()` and builds global managers at import. To import it from a test, set `sys.argv = ["game_launcher.py"]` first.
- **A real "USB Gamepad" (10 buttons, 5 axes, 0 hats) was attached to the dev PC** during the audit, so joystick behaviour can be tested for real there.
- **Current test status**: `python -m pytest engine/test_integration.py` reports 7 passed, but those tests cannot fail (see T1).

---

## 1. Critical — breaks the game today

### A1 [R] Pac-Man cannot be launched
- `PacmanGame.__init__(self, screen, input_manager)` (`games/pacman.py:534`) takes no difficulty and calls `super().__init__(screen, input_manager)` (`:580`).
- The launcher calls `game_classes[ch](screen, input_manager, difficulty)` (`game_launcher.py:1722`) → `TypeError: PacmanGame.__init__() takes 3 positional arguments but 4 were given`. Nothing catches it, so the whole launcher dies.
- Attract mode makes the same call (`game_launcher.py:1524`) with a random game, so it has a 1-in-6 chance of crashing the launcher every time it starts (after every 60 s of idling).
- The `DIFFICULTY_PRESETS` in the class are therefore never applied except NORMAL.
- **Fix**: accept `difficulty=None` and pass it to `super().__init__`.

### A2 [R] Toggling Mute in Settings crashes, and then the launcher cannot start again
- `AudioManager.muted` is a read-only property (`engine/audio_manager.py:108-111`). The launcher assigns to it at `game_launcher.py:96`, `1026`, `1028`, `1036`, `1058`, `1070` → `AttributeError: property 'muted' of 'AudioManager' object has no setter`.
- In the settings menu the value is saved (`settings.set(...)`) *before* the assignment, so `settings.json` ends up with `"muted": true`. On the next launch, line 96 crashes at import. The launcher stays dead until `settings.json` is deleted.
- **Fix**: use the existing `audio_manager.set_mute(bool)` (`audio_manager.py:140`) or add a setter. Make startup tolerant of bad settings.

### A3 [R] Gamepad stops working after attract mode, Achievements or Stats
- `InputManager.init_joystick()` calls `pygame.joystick.quit(); pygame.joystick.init()` (`engine/input_manager.py:149-150`). That closes every existing `Joystick` object.
- Three launcher screens build a fresh `InputManager()`: `run_achievements_viewer` (`game_launcher.py:1149`), `run_stats_viewer` (`:1286`), `run_attract_mode` (`:1510`).
- Afterwards the global manager's handle raises `pygame.error: Joystick not initialized`; `update()` catches it and sets `self.joystick = None` (`input_manager.py:202-204`). There is no re-detection, so the gamepad is dead in the menu and in every game for the rest of the session.
- Attract mode starts by itself after 60 s idle, so a gamepad-only Pi loses its controller after the first idle minute.
- Reproduced with the real gamepad: handle present before, `None` after another `InputManager()` was constructed.
- **Fix**: pass the global manager into those screens instead of constructing new ones; stop calling `joystick.quit()` in `init_joystick()`; handle `JOYDEVICEADDED` / `JOYDEVICEREMOVED` (or re-acquire when `joystick is None`) so hot-plug works.
- Related dead code that does the same: `run_centipede` (`games/centipede.py:820`), `run_pacman` (`games/pacman.py:1146`), `run_snake` (`games/snake.py:601`).

### A4 [R] Menu screens spin on the d-pad
- `select_difficulty` (`game_launcher.py:920-926`), `run_settings_menu` (`:1040-1059`), `run_achievements_viewer` (`:1210-1216`) and `run_stats_viewer` (`:1360-1364`) read the *held* d-pad every frame with no edge detection or repeat delay.
- Measured on the difficulty screen, starting on Normal: Down held 50 ms → Normal, 83 ms → Easy, 100 ms → Normal, 133 ms → Easy. The result of a tap is effectively random.
- `get_dpad()` includes the keyboard arrows, so an arrow key is handled twice: once by the `KEYDOWN` branch and again every frame by the d-pad branch.
- In Settings a held Left/Right flips a toggle 60 times a second and writes `settings.json` on every frame (30 writes in 0.5 s measured).
- **Fix**: add an edge/auto-repeat helper to `InputManager` (e.g. first repeat after ~250 ms, then every ~120 ms) and use it in all four screens; remove the duplicate keyboard path; save settings once when leaving the screen.

### A5 [R] Attract (demo) mode is broken for all six games
`run_attract_mode` (`game_launcher.py:1501-1640`) never calls `handle_input()`; it pokes attributes guarded by `hasattr`, so mismatches fail silently. Result of forcing each game for 15 s:

| Game | What happens | Why |
|---|---|---|
| Snake | Nothing moves | `waiting_for_input` is only cleared in `handle_input` (`games/snake.py:278-280`); `update` returns at `:335` |
| Pac-Man | Launcher crashes | A1 |
| Ferret Crossing | Stays on its START screen | `update` returns unless `state == 'PLAY'` (`games/frogger.py:422`); meanwhile `_move_player` is called every frame and teleports the hidden player to the top row |
| Centipede | Never fires, player walks off-screen (ended at y=694 in a 600 px window) | launcher calls `_fire` (`game_launcher.py:1593`), the method is `_fire_bullet` (`games/centipede.py:348`); clamping only happens in `handle_input` (`:339`) |
| Dig Dug | Nothing moves | launcher sets `last_dx/last_dy`, but `update` only moves when `self.moving` is true, which only `handle_input` sets (`games/digdug.py:424`, `:434`) |
| Boulder Dash | Player moves a tile per frame with the sprite left behind, loses all 3 lives, writes real save data (5 `stats.json` writes in one 15 s demo) | `_try_move` has no dying/complete guards and never updates the sprite position (`games/boulderdash.py:755`); see [A] details in G-BD5 |

- The demo can unlock real achievements and inflate stats (`games_played` can unlock the global `play_all`).
- Simply entering attract mode creates a `demos/` folder in the project (`engine/demo_manager.py:43`).
- `game_key` for the third game is `ferretcrossing` (`game_launcher.py:1516`) while everything else uses `frogger`.
- Demo recording is never started anywhere (`start_recording` / `record_frame` have no callers), so the recorded-demo playback path is dead code.
- **Fix direction**: drive demos through the normal path — give the game a scripted `InputManager` and call `handle_input()` — and add a demo flag on `BaseGame` that disables score, stats and achievement writes.

### A6 [R] Two settings do nothing
- **Volume**: `audio_volume` is saved but never applied; `AudioManager.volume` stays at its default 0.5. No code assigns `.volume` anywhere.
  - Note: the `volume` setter iterates `self._sounds.values()` and calls `.set_volume` (`audio_manager.py:123-124`), but missing sounds are cached as `None` (`:184`, `:195`), so wiring it up as-is would crash once any sound is missing.
- **Fullscreen**: the toggle (`game_launcher.py:993`) is saved but never read; only the `--fullscreen` flag matters (`:1673`).
- **Mute with M** (`game_launcher.py:570-571`, `engine/base_game.py:206`) is not written to settings, so the Settings screen shows a stale value.

---

## 2. Launcher and menu

- **B1 [S] Global RNG reseeded.** `random.seed(42)` in `run_menu` (`game_launcher.py:485`) reseeds the module-level RNG every time the menu opens. Snake, Ferret Crossing and Centipede reseed afterwards; Pac-Man, Dig Dug and Boulder Dash do not, so their "random" behaviour is partly repeatable. Use a local `random.Random(42)` for the decorations. The same seed/unseed pattern is in `games/snake.py:114/152`, `games/frogger.py:287/325`, `games/centipede.py:522/551`.
- **B2 [S] Keyboard shortcuts collide with WASD.** WASD is mapped to the d-pad (`engine/input_manager.py:62-65`), but in the menu `A` opens Achievements and `S` opens Settings (`game_launcher.py:567-568`), so WASD cannot steer left/down there. In Settings `S` also closes the screen.
- **B3 [S] No gamepad route to Settings, Achievements, Stats, Controller Test or Quit.** They are keyboard-only (`game_launcher.py:562-571`). The on-screen help lists only some of them (`:705`).
- **B4 [S] Sleep animation unreachable.** `SLEEP_THRESHOLD` is 90 s but attract mode returns at 60 s (`game_launcher.py:547-549`, `:607`). The idle timer only resets on d-pad input, not on mouse or key presses.
- **B5 [R] Menu allocates ~168 new Surfaces per frame.** `draw_decorations` builds one SRCALPHA surface per decoration (163 of them) every frame (`game_launcher.py:345-406`); clouds and hearts do the same; the achievement toast creates two fonts per frame (`:746-747`). Render the static decorations once to a background surface.
- **B6 [S] Mouse hover never updates.** `Button.check_hover` is never called, so `is_hovered` is always false.
- **B7 [R] Help text is off-centre.** Drawn from a hard-coded `WINDOW_WIDTH//2-180` (`game_launcher.py:707`): it spans x=220..753 instead of 134..666. The title is 745 px wide in an 800 px window.
- **B8 [S] Controller test gives no on-screen feedback without a controller**; it prints to the console and returns (`game_launcher.py:769-771`).
- **B9 [S] Inconsistent quit handling.** Achievements and Stats call `pygame.quit(); sys.exit()` on window close (`:1193-1195`, `:1345-1347`); other screens return.
- **B10 [S] Achievements list overlaps its own hint.** Ten rows of up to 45 px starting at y=120 run past the "More below" hint at y=540 (`game_launcher.py:1186`, `:1231-1273`).
- **B11 [S] Display mode is re-set after every game** (`game_launcher.py:1732-1740`), a leftover from when games changed the mode. It recreates the window each time.
- **B12 [S] Fullscreen scaling** uses `pygame.transform.scale` on the whole frame every frame and stretches 4:3 to the display's aspect ratio (`game_launcher.py:103-111`). Consider the `pygame.SCALED` display flag or letterboxing.
- **B13 [S] No crash guard.** An exception inside any game (`game.run()` at `:1723`) ends the launcher. On a kiosk that means dropping to the desktop or a dead console. There is no log file; `cleanup()` swallows every exception (`:1643-1662`).
- **B14 [S] Naming drift.** The menu title and window caption say "Winston Entertainment System" (`:672`, `:1689`, `:1743`); the argparse description and all docs say "Weasel". The achievements viewer labels the third game "Frogger" (`:1175`) while the menu calls it "Ferret Crossing".
- **B15 [S] Housekeeping.** 13 unused imports and one unused local (`:1287`) per pyflakes; the achievement toast is implemented twice (`game_launcher.py:712-753` and `engine/base_game.py:105-180`); module-level wrapper functions (`:118-136`) are unused.

---

## 3. Engine

### BaseGame (`engine/base_game.py`)
- **C1 [S]** No shared pause, game-over or restart flow. Each of the six games re-implements pause; several have no game-over screen at all (see section 4). `GameState` in `engine/game_states.py` exists for this but no game uses it.
- **C2 [S]** `update(dt)` gets raw `dt` with no clamp, and the loop hard-codes `clock.tick(60)` (`:228`) instead of `FPS`.
- **C3 [S]** `_draw_pause_overlay` creates a full-screen surface and two fonts every paused frame (`:86-100`); `_draw_achievement_notification` creates a surface, 70 gradient lines and two fonts every frame for 180 frames (`:144-177`).
- **C4 [S]** High scores are only saved by game code on game over; quitting with B/ESC loses the score in every game.

### InputManager (`engine/input_manager.py`)
- **C5 [S]** Start (and Enter) trigger both "action" and "pause": `'start': [K_RETURN]` is in the key map (`:68`), `action_pressed` includes `start` (`:497`) and so does `pause_pressed` (`:517`).
- **C6 [S]** Button IDs are defined three times: `engine/__init__.py:45-48`, class constants (`input_manager.py:74-77`) and `DEFAULT_BUTTON_MAP` (`:53-58`). `controller_config.json` only updates `button_map`; `get_any_action_button` / `get_any_back_button` (`:459`, `:483`) and the launcher's test screen still use the constants.
- **C7 [S]** The module-level `get_dpad()` calls `update()` itself (`:586`), which breaks edge detection if anything uses it alongside a manager.
- **C8 [S]** No hot-plug support; the controller must be connected before launch.

### Persistence (`score_manager.py`, `settings_manager.py`, `stats_manager.py`, `achievements.py`)
- **C9 [S]** Four near-identical JSON stores with two different styles (`open()` vs `Path.write_text`). Writes are not atomic, a corrupt file silently resets to empty, and write errors are swallowed. A power cut on a Pi during a write loses the data.
- **C10 [S]** All of them write next to `__file__`. That fails or is wiped in a packaged build or a read-only install (see D5).
- **C11 [S]** `StatsManager.set` writes the whole file on every call (`stats_manager.py:128`); a game over triggers 5–6 full rewrites.
- **C12 [S]** One high score per game, shared across Easy/Normal/Hard. `ScoreManager._load` does `int(v)` and only catches `ValueError` (`score_manager.py:53-54`), so a non-numeric JSON value raises `TypeError` at startup.
- **C13 [S]** `global.games_started` is incremented when a game *ends*, in every game. `global.games_completed` is only incremented by Pac-Man (per level), Dig Dug and Boulder Dash, so `first_win` can never come from Snake, Ferret Crossing or Centipede.
- **C14 [S]** `get_progress()` counts hidden achievements in the total while `get_all_achievements()` hides them, so the viewer shows e.g. "x/24" with 23 listed (`achievements.py:286-316`).

### AnimatedFerret (`engine/ferret_sprite.py`)
- **C15 [A]** No class-level cache: every instance re-reads the PNG and JSON and builds 144 surfaces (~3 ms on desktop). Snake creates one per body segment and one more on every food (`games/snake.py:212-223`, `:412`); Centipede and Boulder Dash create one per respawn.
- **C16 [A]** `set_sprite_size()` / the `sprite_size` setter change only the collision size, not the drawn frames (`:721-736`). Centipede's player is drawn 32×32 with a 16×16 hitbox; Pac-Man's is 28 vs 32.
- **C17 [A]** Special states (`dig`, `jump`, `emerge`, `death`) loop forever and never signal completion (`:510`, `:547`). `enable_sleep` is stored but never read. After 300 frames of `update(0, 0)` every `idle` becomes `idle2` for the rest of the session.
- **C18 [A]** `media/ferret-long-sprite.json` is read but matches the hard-coded 9×8 grid exactly, and its frame durations are ignored. An Aseprite "array" export would raise `AttributeError` in the parser (`:100-106`).

### Other
- **C19 [S]** `engine/constants.py` (speeds, timings, score values, bounds) and the `GameState`, `MenuState`, `GhostState`, `TileType` enums are imported by no game. `Direction` is the only one used.
- **C20 [A]** `AssetLoader`: every game builds its own instance, so the cache is never shared; most of its API has no callers (`preload_game`, `unload_game`, `load_sound`, `load_sprite_sheet*`, …); `preload_game('boulderdash')` joins the wrong base path (`asset_loader.py:68-70`, `:505`); missing images return `None` silently unless debug mode is on (`:258-261`).
- **C21 [S]** `DemoManager.__init__` creates `demos/` unconditionally with no error handling (`demo_manager.py:43`).

---

## 4. Games

### Cross-game
- **G1 [S/A]** Movement and timers count frames; `dt` is ignored in every game except parts of Snake. Below 60 fps the games run in slow motion.
- **G2 [S/A]** Restart does not reset per-session counters or the `new_high_score` flag (Frogger, Dig Dug, Boulder Dash, Centipede). Stats are added cumulatively on each game over, and "NEW HIGH SCORE!" sticks after the first record.
- **G3 [S]** Direct `pygame.key.get_pressed()` reads duplicate what `get_dpad()` already covers (Pac-Man `:807-818`, Dig Dug `:418-420`, Centipede `:316-332`).
- **G4 [S]** Duplicated code across games: game-over overlays, HUD shadow text, difficulty-preset boilerplate, flower drawing, the unused `run_<game>()` wrappers.

### Snake (`games/snake.py`)
- **G-SN1 [S]** Custom `run()` (`:551-579`) skips `_track_session_stats`, `_update_achievement_notification` and `_draw_achievement_notification`. Snake play time never counts towards the "Dedicated Player" achievement and its achievement pop-ups appear later, in another game.
- **G-SN2 [A]** Movement is slower than configured: `move_timer = 0` (`:342`) discards the remainder. Measured 85 moves per 10 s on Normal instead of 100.
- **G-SN3 [A]** The snake freezes for 0.3 s on every food and ignores input during that time (`:258-259`, `:326-332`).
- **G-SN4 [A]** One-slot turn buffer checked against the current direction (`:268-275`), so a quick Up-then-Left is dropped.
- **G-SN5 [A]** `_spawn_food` loops forever if the board is full (`:225-231`). Food can spawn under the HUD in row 0.
- **G-SN6 [A]** The "movement" animation never shows; segments fall back to idle/idle2 (`:295-296`).
- **G-SN7 [S]** Difficulty changes only speed (6/10/14) and wall death on Hard; no speed-up with length.

### Pac-Man (`games/pacman.py`)
- **G-PM1 [R]** Clearing the board resets the score to 0 and never saves the high score: the win branch (`:1004-1016`) calls `_reset_level()`, which sets `self.score = 0` (`:779`); `set_high_score` is only called on game over (`:871`). Reproduced: cleared with 2340 points → score 0, nothing written.
- **G-PM2 [S]** No game-over screen. On the last life the game resets and continues (`:869-882`). "GAME OVER" is only drawn when `new_high_score` is already true (`:1121`), which is set after the death animation has finished, so it effectively never appears the first time and appears wrongly later.
- **G-PM3 [S]** `pacman_1000` is only checked at game over, after G-PM1 may have zeroed the score.
- **G-PM4 [S]** No level progression; a cleared board restarts identically.
- **G-PM5 [R]** 271 new Surfaces per frame: one per star (30), per wall glow (38), per pellet glow (203) (`:1053-1086`); frightened ghosts rebuild a tinted copy every frame (`:119-129`, `:194`); eaten ghosts build a new surface every frame (`:197`).
- **G-PM6 [S]** The 32×32 player box (`:967`) is used for ghost collisions as well as pellet pickup.

### Ferret Crossing (`games/frogger.py`)
- **G-FR1 [S]** Restart resets only lives, score and state (`:388-393`); see G2.
- **G-FR2 [A]** The death animation is frozen on frame 0: the dying branch returns (`:457`) before the sprite update (`:529`).
- **G-FR3 [A]** Hops pressed during the 8-frame hop, the 30-frame respawn or the 45-frame death are dropped (`:406-416`).
- **G-FR4 [S]** No goal or progression: each crossing gives +200 and resets the player with identical lanes (`:502-514`). Difficulty only scales obstacle speed (`:263`).
- **G-FR5 [R]** 64 new Surfaces per frame (clouds, 40 water shimmers, lily pads, flowers) (`:593-642`).
- **G-FR6 [P]** `pygame.font.SysFont('Courier New', …)` (`:200-201`) is usually missing on a Pi and its lookup can be slow.

### Centipede (`games/centipede.py`)
- **G-CE1 [S/A]** No game-over state. At 0 lives the code sets `game_over = True; lives = 3; score = 0` (`:493-507`) and play continues after the respawn. `game_over` is never cleared, which disables pause for the rest of the session (`:299`), and the final score is never shown.
- **G-CE2 [S/A]** Segments never stop descending: a wall bounce always does `rect.y += 16` with no bottom limit (`:676-679`). Dodged segments leave the screen, the wave can never be cleared and no new wave spawns (`:462-468`).
- **G-CE3 [A]** One Space press fires two bullets (`:312` and `:317` both fire on the same frame); Space auto-fires when held, the gamepad A button does not.
- **G-CE4 [A]** Player hitbox is half the drawn size (C16) and the sprite hangs 8 px off the screen edges.
- **G-CE5 [A]** The death animation never plays (both `handle_input` `:308` and `update` `:365-369` return early).
- **G-CE6 [A]** Soup bowls accumulate without limit (`:412`, `:806`); collision cost and per-bowl surface allocation grow over a session.
- **G-CE7 [S]** No difficulty ramp: a cleared wave is recreated identically (`:468`).
- **G-CE8 [R]** ~40 new Surfaces per frame (`:562-613`).

### Dig Dug (`games/digdug.py`)
- **G-DD1 [S]** Enemies ignore terrain and boulders (`Enemy.update`, `:159-176`): they random-walk through dirt. Digging tunnels has no effect on play.
- **G-DD2 [S]** The whole game is three crystals at fixed positions (`:320-324`), three fixed boulders and 1/2/4 enemies. One touch is game over; there are no lives, levels or points. The "high score" is crystals collected, so its maximum is 3.
- **G-DD3 [S]** On Hard the fourth enemy spawns at (500, 200), the same spot as a boulder (`:334`, `:349`).
- **G-DD4 [S]** The player box is the 64×64 scaled sprite (`:484`) against 50 px enemies; diagonal movement is √2 faster (`:435-436`).
- **G-DD5 [S]** `_reset_game` (`:375-389`) does not reset `new_high_score` or `_deaths`; see G2.
- **G-DD6 [S]** The collect "emerge" animation (`:494`) is overwritten next frame; the death animation is frozen because `update` returns once `game_over` is set (`:430`).
- **G-DD7 [R]** Slowest frame of all games (4.2 ms average on desktop): `_draw_terrain` builds 12 full-width alpha surfaces and redraws all 768 cells with several draw calls each, every frame (`:576-625`); each crystal builds 2–6 surfaces per frame (`:99-132`); the HUD builds an 800×40 surface with 40 lines per frame (`:630-634`). Cache the terrain to a surface and redraw only dug cells.
- **G-DD8 [S]** `type('', (), {'rect': player_rect})()` creates a throwaway class every frame for `spritecollide` (`:485-489`).

### Boulder Dash (`games/boulderdash.py`)
- **G-BD1 [S/A]** A rock or diamond directly above the player always kills, even one that was resting: the player's cell is `TILE_EMPTY`, so anything above counts as unsupported (`:868`), and the crush check ignores `was_falling` (`:900`). Digging under a resting rock is instant death.
- **G-BD2 [A]** The player can spawn directly under a diamond (`:640` only checks for rocks): 126 of 4,500 generated levels (2.8%).
- **G-BD3 [A]** Level 4 ("maze") is unwinnable in about 30% of generated levels (98 of 300 on Normal): `_add_maze_walls` (`:578-596`) creates sealed cells that diamonds are placed in. There is no restart-level option.
- **G-BD4 [A]** Rocks fall one tile per frame (60 tiles/s) (`:887-890`) with no sound or warning.
- **G-BD5 [A]** `_try_move` (`:755`) has no dying / level-complete / game-over guards (those are only in `handle_input`, `:930`) and never updates the sprite position. This is what makes the demo destructive (A5).
- **G-BD6 [A]** Movement fires only on a d-pad change (`:948-954`): one press per tile, no hold-to-repeat, and phantom moves when rolling between diagonals.
- **G-BD7 [A]** Restart with A (`:932-941`) does not reset `_total_diamonds`, `_levels_completed`, `_deaths`, `new_high_score`, `_deaths_this_level`; see G2. `boulder_no_crush` cannot unlock on level 1 after a restart.
- **G-BD8 [A]** The fall loop iterates in list order, not bottom-to-top as its docstring says (`:858-863`), so stacked rocks behave differently depending on insertion order.
- **G-BD9 [A]** Level 5 gets double the scattered walls (`:488-493`); the `walls` values for three layouts are unused.
- **G-BD10 [A]** The high score is "level reached" (1–5) and cannot tell a win from dying on level 5 (`:696`, `:738`); it is never drawn. There are no points.
- **G-BD11 [A]** Dying regenerates a new random level and resets the diamond count (`:750-751`).
- **G-BD12 [A]** Pushing a rock leaves stale bounce/fall state at the old cell (`:838-845`).
- **G-BD13 [A]** Per-frame allocations: fonts in the win and level-complete overlays (`:1193`, `:1219`), full-screen alpha surfaces (`:1106`, `:1187`, `:1213`), a surface per particle and sparkle (`:147-217`), a per-frame rescale of bouncing rocks (`:1082`).
- **G-BD14 [A]** `BoulderLevels.txt` and everything in `games/boulder-dash/` are unused; levels are random. Docstrings still say "collect all 5 diamonds" (`:4`, `:263`).

---

## 5. Performance summary (Raspberry Pi)

New `pygame.Surface` objects created per frame, measured over scripted play:

| Screen | Surfaces per frame |
|---|---|
| Pac-Man | 271 |
| Main menu | 168 |
| Ferret Crossing | 64 |
| Centipede | 40 |
| Dig Dug | 26 (but the slowest frame time) |
| Boulder Dash | 11 |
| Snake | 5 |

Common remedies: pre-render static backgrounds and decorations once; build glow sprites once and reuse them; create fonts in `setup()`; cache `AnimatedFerret` frames at class level; share one `AssetLoader`; batch stats writes.

---

## 6. Deployment and packaging

Nothing in this section was run on a Pi; D1 and D6 are confirmed by reading or byte inspection, the rest are [P].

- **D1 [S]** `setup_rpi.sh:44`: `pip3 install pygame>=2.1.2 $PIP_ARGS` is unquoted. The shell treats `>` as a redirect: it installs plain `pygame`, writes the output to a file named `=2.1.2`, and drops the version floor.
- **D2 [P]** `setup_rpi.sh:37-44` mixes the apt `python3-pygame` with `pip --break-system-packages` and upgrades pip with pip. A venv (which `start.sh:32` and `scripts/package.py` already assume) avoids this. The script ignores `requirements.txt`.
- **D3 [P]** Launch paths disagree:

  | Path | Python | Fullscreen |
  |---|---|---|
  | `start.sh` | `.venv`, forces `SDL_VIDEODRIVER=x11` and `pulse` | no |
  | `run_game.sh` | system python, ignores `.venv` | yes |
  | systemd unit (`install_autostart.sh:38-65`) | hard-coded `/usr/bin/python3` | yes |

- **D4 [P]** `install_autostart.sh` installs both a systemd service on tty1 and a desktop autostart entry (`:36-82`); `scripts/package.py rpi-setup` adds a third. On a desktop image more than one instance may start. `Restart=on-failure` does not restart after a clean ESC exit (exit code 0), leaving a dead console. It falls back to user `pi` (`:24-26`), which current Pi OS images do not have, and can create root-owned `~/.config` folders (`:69`). `run_game.sh:15-21` checks only `$DISPLAY`, not `WAYLAND_DISPLAY`. `SDL_NOMOUSE` is an SDL 1.2 variable with no effect.
- **D5 [S]** `wes.spec:18-27` bundles all of `games/` and `docs/`: that includes a 5.8 MB third-party `games/pacman/pacman.exe`, `pacman.mp3`, about 16 MB of unreferenced assets and the legacy archive. Save files resolve inside the bundle (C10).
- **D6 [R]** Mixed line endings. CRLF: `game_launcher.py`, `diagnose_controller.py`, and in `engine/`: `achievements`, `asset_loader`, `audio_manager`, `demo_manager`, `ferret_sprite`, `score_manager`, `settings_manager`, `stats_manager`, `test_integration`. Everything else, including the four shell scripts, is LF. The launcher's shebang is `#!/usr/bin/env python3\r`, so `./game_launcher.py` fails on Linux (running it via `python3 game_launcher.py` works). Add a `.gitattributes` and normalise.
- **D7 [S]** `requirements.txt` is a single unpinned `pygame>=2.1.2`; there are no dev requirements. Docs claim "Python 3.6+" but `engine/ferret_sprite.py:23` uses `from __future__ import annotations` (3.7+).

---

## 7. Repo hygiene and licensing

- **R1 [S]** Not a git repository; no LICENSE; no CI, lint or format configuration.
- **R2 [S]** `.gitignore:24` ignores `highscores.json`, but the real file is `high_scores.json` (`engine/score_manager.py:28`), which is present in the project. `controller_config.json` is not ignored. `launch.txt` contains a personal path.
- **R3 [S]** Unused files (not referenced by `game_launcher.py`, `engine/*.py` or `games/*.py`):
  - the asset folders `games/pacman/`, `games/centipede/`, `games/dig-dug/`, `games/boulder-dash/` (~16 MB), including `pacman.exe`, `pacman.mp3`, fonts, `games/centipede/index.html` and `highscore.txt`
  - `games/_archive/` (9 legacy files, ~3.6k lines)
  - in `media/`: `weasel.png` (byte-identical to `ferret-standing-sprite.png`), `65c1afdc63d71f95c327ce8805c399e6.png`, `soupcan.png`, `soupcan_8bit.png`, `ferret-long-sprite-brown-backup.png`
  - Active code uses only `ferret-long-sprite.png/.json`, `soupbowl.png`, `soupcan_new.png` and `sounds/*.wav`.
- **R4 [S]** Third-party IP and provenance:
  - Menu names "Pac-Man", "Dig Dug", "Centipede" and "Boulder Dash" are other companies' trademarks.
  - The enemy sprite `media/soupcan_new.png` is a recognisable branded soup can.
  - `games/_archive/boulderdash_legacy.py` is GPL-3.0; other archived files carry other authors' names with no licence file.
  - The Centipede sound files are Freesound downloads (usually CC-BY) with no attribution.
  - Only `sounds/*.wav` have clean provenance (generated by `generate_sounds.py`).
  - Fine for private use; before sharing publicly, rename and re-skin, add attribution, and choose a licence.
- **R5 [S]** pyflakes reports about 60 unused imports and variables across the active code.

---

## 8. Tests

- **T1 [R]** `engine/test_integration.py` is a print-based script: each `test_*` returns a bool instead of asserting, so pytest passes regardless (7 passed). One check is a tautology (`:450`, `img is not None or True`).
- **T2 [S]** Nothing tests: constructing each game, save/load and corrupt-file handling, input edge detection, the launcher screens, attract mode.
- **T3** Suggested first test — it would have caught A1 and most of A5. It needs a fixture that redirects the save files to a temp folder first (see C10):

  ```python
  # tests/test_smoke.py  (run with SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy)
  import pygame, pytest
  from engine import InputManager, Difficulty
  from games import (SnakeGame, PacmanGame, FroggerGame,
                     CentipedeGame, DigDugGame, BoulderDashGame)

  GAMES = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]

  @pytest.mark.parametrize("cls", GAMES)
  @pytest.mark.parametrize("difficulty", list(Difficulty))
  def test_game_survives_300_frames(cls, difficulty):
      pygame.init()
      screen = pygame.display.set_mode((800, 600))
      game = cls(screen, InputManager(), difficulty)
      for _ in range(300):
          assert game.handle_input() is False
          game.update(1 / 60)
          game.render()
  ```

---

## 9. Documentation drift

- **X1** `readme.md:69-77` says to edit mapping constants "at the top of `game_launcher.py`"; they live in `engine/__init__.py:45-49` and `engine/input_manager.py:53-78`. The real mechanism (`controller_config.json`, written by `diagnose_controller.py`) is not documented anywhere.
- **X2** `readme.md:52-55`, `DOCUMENTATION.md:437-441` and `CONTROLLER_GUIDE.md:138-178` describe "axis 4" d-pad logic that the code does not have (`input_manager.py:256-308` uses hat, then configured axes, then axes 0/1).
- **X3** `readme.md:91` says the launcher is ~280 lines and `DOCUMENTATION.md` says 1,081 with embedded games; it is 1,746 lines and the games are in `games/`.
- **X4** Docs show `game_classes[i](screen, input_manager)` and never mention difficulty, high scores, settings, achievements, stats, attract mode or packaging.
- **X5** Idle thresholds are documented as 10 s / 30 s; the code uses 15 s / 90 s.
- **X6** Keyboard shortcuts S, A, X and P are missing from the docs.
- **X7** `docs/plans/2026-01-07-wes-improvement-plan.md` still shows phases 2–4 as "Not Started" while the session notes claim them done. Claimed but not true: magic numbers extracted / enums in use (C19), asset unloading (C20), recorded demos (A5), working Fullscreen setting (A6).

---

## 10. Suggested order of work

1. **Stop the crashes**: A1, A2, A3, A4, plus a crash guard and log file around `game.run()` (B13) and the smoke test (T3).
2. **Foundations**: rebuild attract mode on scripted input with saving disabled (A5); one atomic JSON store in a user data folder (C9–C11); shared pause / game-over / restart flow in `BaseGame` (C1, G2); wire up Volume and Fullscreen (A6).
3. **Performance**: pre-render static art (section 5), class-level sprite cache (C15), `dt`-based movement (G1).
4. **Gameplay**: per-game fixes in section 4, starting with G-CE1, G-CE2, G-BD1, G-BD3, G-PM1.
5. **Cleanup**: unused assets and dead code (R3, C19, C20), line endings (D6), Pi scripts (D1–D4), docs (section 9), licensing (R4).
