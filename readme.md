# Winston Entertainment System (WES)

Six ferret-themed arcade games in a shared 800×600 Pygame launcher: Snake,
Tunnel Treats, Ferret Crossing, Burrow Defender, Crystal Quest, and Rocky Burrow.
The original module/save IDs remain stable so existing records can migrate.

## Run

Python 3.10 or newer is required; development checks use Python 3.12 and Pygame 2.6.1.

```sh
python scripts/package.py install
# Windows:
.venv/Scripts/python game_launcher.py
# Linux / Raspberry Pi:
./start.sh
```

Press **F11** or **Alt+Enter** to switch fullscreen on or off in any menu or game.
Fullscreen uses the selected laptop/TV screen's current resolution. Settings →
Picture offers **Keep proportions** (4:3 with side bars) or **Fill screen
(stretch)**. Display changes apply immediately and preserve the running game.

For an HDMI TV, connect it and use Settings → Screen or **F10** to select the TV
when Windows extends the desktop. With duplicated displays, both show the same
game. Screen numbers follow the order reported by SDL and may differ from Windows
Display Settings. Disconnecting the selected screen falls back to Screen 1.
Fullscreen, screen selection, and picture fit are saved for the next launch.

Command-line overrides: `--fullscreen`, `--windowed`, and `--display N` (1-based).
For example: `wes.exe --fullscreen --display 2`.

## Controls

| Action | Keyboard | Gamepad |
|---|---|---|
| Move / navigate | Arrows or WASD | D-pad or stick |
| Action / confirm | Enter or Space | A |
| Pause / resume a game | P | Start |
| Back / options from main menu | Escape, Backspace or Tab | B or Select |
| Confirm a menu choice | Enter or Space | A or Start |
| Settings / achievements / statistics | F1 / F2 / F3 | Options menu |
| Controller test | T | Options menu |
| Fullscreen on/off | F11 or Alt+Enter | Settings menu |
| Next connected screen | F10 | Settings → Screen |
| Mute | M | Settings menu |
| Quit | Options → Quit, or close window | Options → Quit |

Tap the D-pad to highlight a title and press A or Enter to play. The ferret follows
your selection. The menu remembers the last highlighted game. Each difficulty
shows its rules and your best score. In Crystal Quest and Rocky Burrow, completing
the campaign also sets a time to beat on that difficulty. The results show your
clear time and remaining lives. On Hard, Rocky Burrow caves 2 and 4 contain
rock-pushing puzzles.

Open **Controller test** with **T** or through **Options**. Choose **Calibrate D-pad**
(C) to learn four directions, or **Remap buttons** (R) to change A, B, Select or
Start individually or together. Both changes apply immediately.

See [CONTROLLER_GUIDE.md](CONTROLLER_GUIDE.md) for mapping and hot-plug support.

## Sound and saves

The home screen and all six games have their own original looping chiptune theme.
Selection, back, pause/resume, achievements, pickups, power-ups, jumps, shots,
rock impacts and digging have distinct sound cues. Frequent effects are throttled
to keep repeated actions from overwhelming the mix. Music pauses with gameplay
and returns to the home theme when leaving a game. Switching away pauses an active
game. Press P or Start to resume. Play time and campaign records count active gameplay.

Settings has separate **Music volume** and **Effects volume** controls, alongside
the master Volume and Mute settings. M mutes both music and effects. Generate all
25 audio files reproducibly with `python generate_sounds.py`.

Scores (separate for each difficulty), settings, achievements, statistics,
controller mapping, and `wes.log` live in the user data directory:

- Windows: `%LOCALAPPDATA%/WES`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/wes`
- Override for testing/portable use: `WES_DATA_DIR`

Windows opens one launcher per save folder. Opening WES again brings the running
game forward, subject to Windows focus settings.

Legacy JSON saves beside the source are imported on first use when there is no
new save and no override. Legacy single scores become Normal records. Originals
are preserved. JSON replacement is atomic with a `.bak` recovery copy; malformed
files are preserved as `.corrupt-*` and errors are logged.

At 15 seconds idle the menu ferret looks around; at 30 seconds it sleeps. The
home screen stays open until you select a game. There are no automatic game
previews. Scripted input remains only for isolated verification/smoke checks.

## Raspberry Pi

```sh
./setup_rpi.sh
./run_game.sh
./install_autostart.sh desktop   # login session; X11 or Wayland selected by SDL
# OR:
./install_autostart.sh console   # dedicated kmsdrm kiosk on tty1
```

Choose one startup mode. The installer disables/removes the alternate WES entry;
`start.sh` also prevents duplicate instances using `flock`. All paths use `.venv`.
Console mode restarts after a clean Quit; stop it with
`sudo systemctl stop wes-game`. Desktop mode exits normally. Do not run the
installer as root without `SUDO_USER`; it must identify your actual account.
Hardware display, audio and boot behavior still require a real Pi acceptance run.

## Development and packaging

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/package.py build
# Verify a Windows bundle without using real saves:
dist/wes/wes.exe --smoke-test
```

Tests isolate persistence and use dummy SDL video/audio. CI checks Windows and
Linux on Python 3.10 and 3.12. `wes.spec` packages only imported active modules,
the ferret sheet/metadata, soup bowl and generated WAV sounds. `legacy_reference/`
is archival material, excluded from the build, tests and lint. It is not runtime
content and has unresolved third-party provenance.

## Bundled game sources

| Component | Source and scope |
| --- | --- |
| Pac-Man | The Windows installer is credited to hbokmann/Pacman. The launcher runs `games/pacman.py`. [Archived README](legacy_reference/games/pacman/README.md) · [Upstream project](https://github.com/hbokmann/Pacman) |
| Boulder Dash sound effects | The archived game's README credits the effects to irmen/bouldercaves. [Archived README](legacy_reference/games/boulder-dash/README.md) · [Upstream project](https://github.com/irmen/bouldercaves) |
| Archived implementations | The archive notes identify the historical modules and the games that replaced them. [Archive notes](legacy_reference/games/_archive/README.md) |

Public distribution is not cleared. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and [LICENSE](LICENSE). The audit and its resolution evidence are in
[docs/plans/2026-11-14-audit-resolution.md](docs/plans/2026-11-14-audit-resolution.md).
