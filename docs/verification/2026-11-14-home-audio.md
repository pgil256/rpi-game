# Home screen and audio update

The user confirmed sound playback was working and requested removal of the idle
game preview, more sound design/music, and a fullscreen executable relaunch.

## Result

- Removed the home screen's 60-second automatic game launch and the interactive
  preview renderer/route. The ferret can idle/sleep while the menu stays open.
  Scripted simulation remains only in verification code and the smoke check.
- Added seven original 16-bar chiptune themes: home, Snake, Tunnel Treats,
  Ferret Crossing, Burrow Defender, Crystal Quest, and Rocky Burrow. Each has
  melody, arpeggiated chords, bass, and synthesized percussion. Themes run
  approximately 28–40 seconds and loop with zero-valued boundaries/headroom.
- Added eleven effects and refined the original seven, for 18 total. New event
  coverage includes menu/back/start, pause/resume, achievements, Snake turns,
  regular treats/powerups, hops, shots/hits, fresh digging, and rock pushes/landings.
- Music stays continuous across utility menus, changes for each game, pauses
  with gameplay/game over, and returns to the home theme on leaving a game.
  Muting while paused cannot accidentally resume music; switching tracks while
  muted can subsequently unmute correctly.
- Added saved music/effects volume controls (35%/85% defaults) under the existing
  master volume. Repeated action sounds have short cooldowns to avoid a noisy mix.
- All audio is generated reproducibly by `generate_sounds.py`, with no downloaded
  assets or additional runtime dependencies. All 25 WAVs are included in the build.

## Verification and delivery

- **190 tests passed, 1 skipped** (existing Windows Bash limitation).
- Ruff lint/format and `git diff --check` passed.
- Idle-menu regression simulates more than ten minutes without starting a game.
- Checked every effect loads, all seven themes start, themes are distinct and
  unclipped, pause/mute/track transitions work, and independent volumes persist.
- Visually reviewed the expanded Settings screen; all seven rows and help text fit.
- PyInstaller 6.19.0 build passed the enhanced packaged `--smoke-test`, including
  decoding all effects, starting all themes, and six games × three difficulties.
- Closed the previous running game through Options → Quit, copied the verified
  bundle to `dist/wes`, and verified the executable plus all 25 WAV hashes.
- Relaunched `dist/wes/wes.exe --fullscreen` natively on Windows.
- Installed executable SHA-256:
  `56F8B36C9797DC4971C380652435C760B609FD31FF5FF50B9C13E5396EC95EF7`.

No Windows sound routing changes were made after the user confirmed sound worked.
