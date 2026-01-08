# WES Improvement Plan

Comprehensive plan to improve the Weasel Entertainment System across four areas: release readiness, new features, code quality, and performance.

---

## Progress Tracker

| Phase | Status | Completed |
|-------|--------|-----------|
| Phase 1: Code Quality | **COMPLETE** | 2026-01-07 |
| Phase 2: Release Readiness | Not Started | - |
| Phase 3: New Features | Not Started | - |
| Phase 4: Performance & Platform | Not Started | - |

---

## Current State Summary

- **Architecture**: Excellent BaseGame pattern, clean engine separation (9/10)
- **Code Quality**: Readable but has duplicates and magic numbers (7/10)
- **Polish**: Cute visuals, smooth animations (8/10)
- **Testing**: Minimal automated tests (4/10)
- **Overall**: 7.4/10 - solid foundation needing consolidation

---

## Phase 1: Code Quality (Foundation) - COMPLETE

*Completed: 2026-01-07*

### 1.1 Consolidate Duplicate Game Files - DONE

**What was done**:
- Moved 9 legacy Python files to `games/_archive/`
- Kept asset directories in place (images, sounds, fonts, levels)
- Removed empty `games/frogger/` directory (only had metadata)
- Created `games/_archive/README.md` documenting the archive

**Files archived**:
| Original | Archived As |
|----------|-------------|
| `games/snake/snake_game.py` | `_archive/snake_game_legacy.py` |
| `games/pacman/pacman.py` | `_archive/pacman_legacy.py` |
| `games/frogger/frogger.py` | `_archive/frogger_legacy.py` |
| `games/frogger/actors.py` | `_archive/frogger_actors_legacy.py` |
| `games/centipede/GameMain.py` | `_archive/centipede_GameMain_legacy.py` |
| `games/centipede/GameSprites.py` | `_archive/centipede_GameSprites_legacy.py` |
| `games/dig-dug/Game.py` | `_archive/digdug_Game_legacy.py` |
| `games/dig-dug/Classes.py` | `_archive/digdug_Classes_legacy.py` |
| `games/boulder-dash/BoulderDash.py` | `_archive/boulderdash_legacy.py` |

**Asset directories kept** (still needed by main games):
- `games/boulder-dash/` - Level data, images, sounds
- `games/centipede/` - Sprites, sounds, fonts
- `games/dig-dug/` - Tunnel and enemy sprites
- `games/pacman/` - Images, sounds, fonts

### 1.2 Extract Magic Numbers to Constants - DONE

**Created `engine/constants.py`** with organized classes:

| Class | Purpose |
|-------|---------|
| `PlayerSpeed` | Movement speeds (SLOW, NORMAL, FAST, VERY_FAST) |
| `GhostSpeed` | Pac-Man ghost AI speeds |
| `ProjectileSpeed` | Bullet/projectile speeds |
| `GameTiming` | Animation and tick timing constants |
| `GameThreshold` | Gameplay threshold values |
| `CollisionRadius` | Collision detection radii |
| `ScoreValue` | Point values for game events |
| `LevelBounds` | Level boundary definitions |

**Also includes**:
- Grid constants (`CELL_SIZE_STANDARD`, `GRID_COLS_STANDARD`, etc.)
- Backward-compatible exports (`CELL_SIZE`, `GRID_WIDTH`, etc.)

### 1.3 Add Game State Enums - DONE

**Created `engine/game_states.py`** with enums:

| Enum | Values |
|------|--------|
| `GameState` | PLAYING, PAUSED, DYING, GAME_OVER, VICTORY, RESETTING, COUNTDOWN, READY |
| `MenuState` | MAIN, SETTINGS, CONTROLS, CREDITS, CONFIRM_EXIT |
| `GhostState` | SCATTER, CHASE, FRIGHTENED, EATEN, IN_HOUSE, LEAVING_HOUSE |
| `Direction` | UP, DOWN, LEFT, RIGHT, NONE (with helper methods) |
| `TileType` | EMPTY, WALL, DIRT, BOULDER, DIAMOND, EXIT, etc. |

**Direction enum features**:
- `.dx` and `.dy` properties for movement
- `.opposite` property for reverse direction
- `from_dpad(dx, dy)` class method for input conversion

### 1.4 Fix Encapsulation Issues - DONE

**Added to `engine/ferret_sprite.py`**:
```python
@sprite_size.setter
def sprite_size(self, size: int) -> None:
    self._sprite_size = size

def set_sprite_size(self, size: int) -> None:
    """Method form for compatibility."""
    self._sprite_size = size
```

**Updated games to use public method**:
- `games/snake.py` (line 196)
- `games/pacman.py` (line 634)
- `games/centipede.py` (line 231)

### 1.5 Updated Engine Exports - DONE

**Updated `engine/__init__.py`** to export:
- All new enums: `GameState`, `MenuState`, `GhostState`, `Direction`, `TileType`
- All constant classes: `PlayerSpeed`, `GhostSpeed`, `GameTiming`, etc.
- Grid constants: `CELL_SIZE_STANDARD`, `GRID_COLS_STANDARD`, etc.

---

## Phase 2: Release Readiness (Stability)

### 2.1 Add Pause Functionality

**All games should support pause with P key or Start button.**

**Implementation**:
```python
# In BaseGame or each game's handle_input()
if self.input_manager.pause_pressed():  # Add to InputManager
    if self.state == GameState.PLAYING:
        self.state = GameState.PAUSED
    elif self.state == GameState.PAUSED:
        self.state = GameState.PLAYING
    return False

# In update()
if self.state == GameState.PAUSED:
    return  # Skip game logic

# In render()
if self.state == GameState.PAUSED:
    self._draw_pause_overlay()
```

**Steps**:
1. Add `pause_pressed()` to InputManager (P key + Start button)
2. Add `_draw_pause_overlay()` helper to BaseGame
3. Implement pause in each game's handle_input/update/render
4. Test all 6 games

### 2.2 Implement High Score Persistence

**Problem**: Scores lost when app closes.

**Create `engine/score_manager.py`**:
```python
import json
from pathlib import Path

class ScoreManager:
    def __init__(self, save_file: str = "highscores.json"):
        self.save_path = Path(__file__).parent.parent / save_file
        self.scores = self._load()

    def _load(self) -> dict:
        if self.save_path.exists():
            return json.loads(self.save_path.read_text())
        return {}

    def save(self) -> None:
        self.save_path.write_text(json.dumps(self.scores, indent=2))

    def get_high_score(self, game: str) -> int:
        return self.scores.get(game, 0)

    def update_high_score(self, game: str, score: int) -> bool:
        if score > self.get_high_score(game):
            self.scores[game] = score
            self.save()
            return True  # New high score!
        return False
```

**Steps**:
1. Create ScoreManager class
2. Add `get_score_manager()` singleton to engine
3. Update each game to load/save high scores
4. Show "NEW HIGH SCORE!" message when beaten

### 2.3 Add Settings Menu

**Features**:
- Audio volume (0-100%)
- Mute toggle
- Fullscreen toggle
- Control scheme display

**Implementation**:
1. Create `SettingsMenu` class in `game_launcher.py`
2. Add "Settings" button to main menu
3. Store settings in `settings.json`
4. Load settings on startup

### 2.4 Improve Error Handling

**Problem**: Inconsistent error handling across modules.

**Standard pattern**:
```python
# For assets - return None, caller draws fallback
image = asset_loader.load_image('sprite.png')
if image:
    screen.blit(image, pos)
else:
    pygame.draw.rect(screen, FALLBACK_COLOR, rect)

# For audio - fail silently (already implemented)
audio.play_sound(AudioManager.SOUND_COLLECT)  # No-op if unavailable
```

**Steps**:
1. Audit all asset loading calls
2. Ensure all have fallback rendering
3. Add warning logs for missing assets (optional debug mode)

### 2.5 Add Proper Exit Handling

**Ensure clean shutdown**:
```python
def cleanup():
    score_manager.save()
    pygame.mixer.quit()
    pygame.quit()

# Register with atexit
import atexit
atexit.register(cleanup)
```

---

## Phase 3: New Features

### 3.1 Difficulty Levels

**Add Easy/Normal/Hard presets for each game.**

| Game | Easy | Normal | Hard |
|------|------|--------|------|
| Snake | Slow speed, no walls | Normal speed | Fast, walls kill |
| Pac-Man | Slow ghosts | Normal | Fast ghosts, less power-up time |
| Frogger | Slow traffic | Normal | Fast traffic, more lanes |
| Centipede | Slow centipede | Normal | Fast, more segments |
| Dig Dug | Few enemies | Normal | Many enemies |
| Boulder Dash | More time | Normal | Less time, more rocks |

**Implementation**:
1. Add `Difficulty` enum (EASY, NORMAL, HARD)
2. Create difficulty presets dict in each game
3. Add difficulty selection to game start (or settings)
4. Apply presets in `setup()`

### 3.2 Achievements System

**Simple local achievements**:
```python
ACHIEVEMENTS = {
    "first_win": {"name": "First Victory", "desc": "Win any game"},
    "snake_50": {"name": "Hungry Weasel", "desc": "Score 50 in Snake"},
    "pacman_clear": {"name": "Ghost Buster", "desc": "Clear a Pac-Man level"},
    "no_death": {"name": "Untouchable", "desc": "Complete a level without dying"},
    # ...more per game
}
```

**Steps**:
1. Create `engine/achievements.py`
2. Track unlocked achievements in JSON
3. Show notification when achievement unlocked
4. Add achievements viewer to menu

### 3.3 Demo/Attract Mode

**Auto-play when idle on menu for 60 seconds.**

**Implementation**:
1. Record gameplay inputs to file
2. Play back inputs in demo mode
3. Show "PRESS START" overlay during demo
4. Return to menu on any input

### 3.4 Statistics Tracking

**Track and display**:
- Total play time per game
- Games played
- Total score accumulated
- Deaths
- Best streaks

**Steps**:
1. Create `engine/stats_manager.py`
2. Track events during gameplay
3. Add stats viewer to menu
4. Persist to `stats.json`

---

## Phase 4: Performance & Platform

### 4.1 Raspberry Pi Optimization

**Target**: Smooth 60 FPS on Raspberry Pi 4.

**Optimizations**:
1. **Reduce surface creation**: Pre-create surfaces, reuse buffers
2. **Limit particles**: Cap sparkle/decoration count
3. **Sprite batching**: Use `pygame.sprite.Group` for batch rendering
4. **Resolution scaling**: Optionally render at 640x480 and scale up

**Steps**:
1. Profile on actual Raspberry Pi hardware
2. Identify bottlenecks (likely rendering)
3. Apply targeted optimizations
4. Test at 720p and 1080p outputs

### 4.2 Memory Optimization

**Current issues**:
- Sprite caching unbounded
- No explicit surface cleanup

**Fixes**:
1. Add LRU cache limit to AssetLoader
2. Call `surface.convert()` or `convert_alpha()` after loading
3. Explicitly free unused surfaces when switching games

### 4.3 Startup Time Optimization

**Problem**: Loading all assets on startup is slow.

**Solution**: Lazy loading per game.
```python
class AssetLoader:
    def preload_game(self, game_name: str):
        """Preload assets for specific game."""
        # Load only that game's assets

    def unload_game(self, game_name: str):
        """Free assets no longer needed."""
        # Clear from cache
```

### 4.4 Platform Testing Matrix

| Platform | Status | Notes |
|----------|--------|-------|
| Windows 10/11 | Primary dev | Working |
| Linux (Ubuntu) | Secondary | Likely working |
| Raspberry Pi OS | Target | Needs testing |
| macOS | Optional | Untested |

**Steps**:
1. Create test checklist per platform
2. Test on Raspberry Pi 4 with official display
3. Document any platform-specific issues
4. Add platform detection for optimizations

### 4.5 Packaging for Distribution

**Options**:
1. **PyInstaller** - Single executable for Windows
2. **AppImage** - Single file for Linux
3. **Shell script** - For Raspberry Pi (auto-start on boot)

**Raspberry Pi auto-start**:
```bash
# /etc/xdg/autostart/wes.desktop
[Desktop Entry]
Type=Application
Name=Weasel Entertainment System
Exec=/home/pi/wes/start.sh
```

---

## Implementation Order

Recommended sequence for maximum impact:

```
Phase 1: Code Quality - COMPLETE
├── 1.1 Consolidate duplicates ........... DONE
├── 1.2 Extract constants ................ DONE
├── 1.3 Add state enums .................. DONE
├── 1.4 Fix encapsulation ................ DONE
└── 1.5 Update engine exports ............ DONE

Phase 2: Release Readiness - UP NEXT
├── 2.1 Pause functionality
├── 2.2 High score persistence
├── 2.3 Settings menu
├── 2.4 Error handling
└── 2.5 Exit handling

Phase 3: Features
├── 3.1 Difficulty levels
├── 3.2 Achievements
├── 3.3 Demo mode
└── 3.4 Statistics

Phase 4: Performance
├── 4.1 RPi optimization
├── 4.2 Memory optimization
├── 4.3 Startup optimization
├── 4.4 Platform testing
└── 4.5 Packaging
```

---

## Quick Wins

| Task | Impact | Status |
|------|--------|--------|
| Add pause (P key) | High user impact | Phase 2 |
| Save high scores to JSON | Users expect this | Phase 2 |
| Remove duplicate game folders | Reduces confusion | DONE |
| Add `set_sprite_size()` method | Fixes encapsulation | DONE |

---

## Success Criteria

**Code Quality** (Phase 1 - COMPLETE):
- [x] No duplicate game implementations
- [x] All magic numbers extracted to constants
- [x] Game states use enums (enums created, games can adopt incrementally)
- [x] No direct private attribute access

**Release Readiness** (Phase 2):
- [ ] All games pausable
- [ ] High scores persist across sessions
- [ ] Settings menu functional
- [ ] Clean exit on all platforms

**Features** (Phase 3):
- [ ] Difficulty selection available
- [ ] At least 10 achievements implemented
- [ ] Demo mode plays after 60s idle
- [ ] Statistics viewable in menu

**Performance** (Phase 4):
- [ ] Consistent 60 FPS on Raspberry Pi 4
- [ ] Startup under 3 seconds
- [ ] Memory usage under 200MB
- [ ] Packaged for easy installation

---

## Files to Create

| File | Purpose | Status |
|------|---------|--------|
| `engine/constants.py` | Extracted magic numbers | CREATED |
| `engine/game_states.py` | GameState enum | CREATED |
| `engine/score_manager.py` | High score persistence | Phase 2 |
| `engine/achievements.py` | Achievement system | Phase 3 |
| `engine/stats_manager.py` | Statistics tracking | Phase 3 |
| `highscores.json` | High score data | Phase 2 |
| `settings.json` | User settings | Phase 2 |
| `stats.json` | Play statistics | Phase 3 |
| `games/_archive/README.md` | Documents archived legacy code | CREATED |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing games | Test each game after every change |
| RPi performance unknown | Profile early, don't assume |
| Scope creep | Stick to this plan, defer new ideas |
| Asset compatibility | Keep all fallback rendering |

---

## What's Next

### Phase 2: Release Readiness (Recommended Next)

**Priority order**:
1. **Pause functionality** (2.1) - Most visible user feature
2. **High score persistence** (2.2) - Expected by users
3. **Exit handling** (2.5) - Quick win, ensures scores save
4. **Settings menu** (2.3) - Nice to have
5. **Error handling audit** (2.4) - Polish

**Key files to create**:
- `engine/score_manager.py`
- `settings.json`

**Key files to modify**:
- `engine/input_manager.py` - Add `pause_pressed()`
- `engine/base_game.py` - Add pause overlay helper
- All 6 game files - Add pause support

### Phase 3: New Features

**Can be done incrementally**. Start with:
1. **Difficulty levels** (3.1) - Adds replayability
2. **Statistics tracking** (3.4) - Foundation for achievements
3. **Achievements** (3.2) - Uses statistics
4. **Demo mode** (3.3) - Polish feature

### Phase 4: Performance & Platform

**Do this when ready to deploy**:
1. Get Raspberry Pi hardware for testing
2. Profile actual performance
3. Apply targeted optimizations
4. Package for distribution
