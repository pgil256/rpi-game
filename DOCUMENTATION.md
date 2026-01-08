# Weasel Entertainment System (WES) - Complete Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start](#2-quick-start)
3. [Installation & Requirements](#3-installation--requirements)
4. [Project Architecture](#4-project-architecture)
5. [Games Reference](#5-games-reference)
6. [Input System](#6-input-system)
7. [Visual Theming](#7-visual-theming)
8. [Code Reference](#8-code-reference)
9. [Adding New Games](#9-adding-new-games)
10. [Troubleshooting](#10-troubleshooting)
11. [File Reference](#11-file-reference)

---

## 1. Project Overview

### What is WES?

The **Weasel Entertainment System (WES)** is a unified game launcher featuring six classic arcade games with a ferret burrow theme, designed for Raspberry Pi with NES-style USB gamepad support. All games run in a single 800x600 window with consistent ferret-themed graphics and an animated ferret protagonist.

### Features

- **6 Classic Arcade Games**: Snake, Pac-Man, Frogger, Centipede, Dig Dug, Boulder Dash
- **Unified Interface**: Single launcher with animated ferret avatar navigation
- **Modular Architecture**: Clean separation of engine, games, and assets
- **Multi-Platform Input**: Keyboard, mouse, and gamepad support (NES/Xbox/PlayStation/Generic USB)
- **Consistent Theming**: Ferret color palette and underground burrow aesthetic
- **Fallback Graphics**: Games render with colored shapes if images are unavailable
- **Cross-Platform**: Works on Windows, Linux, macOS, and Raspberry Pi

### Target Platform

- **Primary**: Raspberry Pi with NES-style USB gamepad
- **Compatible**: Any system running Python 3.6+ with Pygame 2.1.2+

---

## 2. Quick Start

### Running the Launcher

```bash
# Standard Python
python game_launcher.py

# Windows with Anaconda
& "C:\Users\user\anaconda3\python.exe" game_launcher.py

# Linux/macOS
python3 game_launcher.py
```

### Basic Controls

| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Navigate menu | Arrow keys | D-pad (moves weasel) |
| Select game | Enter | A or START |
| Return to menu | ESC | B or SELECT |
| Test controller | T | - |
| Exit application | ESC (at menu) | - |

---

## 3. Installation & Requirements

### Prerequisites

- **Python**: 3.6 or higher
- **Pygame**: 2.1.2 or higher (minimum 1.9.3)

### Installation Steps

```bash
# 1. Install Python (if not already installed)
# Windows: Download from python.org
# Linux: sudo apt install python3 python3-pip
# macOS: brew install python3

# 2. Install Pygame
pip install pygame

# Or specific version
pip install pygame==2.1.2

# 3. Run the launcher
cd /path/to/rpi-game
python game_launcher.py
```

### Verifying Installation

```bash
python -c "import pygame; print(f'Pygame version: {pygame.version.ver}')"
```

### Optional: Audio Support

For sound effects and music (Boulder Dash, Centipede, Pac-Man), ensure your system has audio libraries:

```bash
# Linux
sudo apt install libsdl2-mixer-2.0-0

# Windows/macOS
# Usually included with Pygame
```

---

## 4. Project Architecture

### Directory Structure

```
rpi-game/
├── game_launcher.py          # Main launcher (~280 lines)
├── readme.md                 # Basic project overview
├── CONTROLLER_GUIDE.md       # Gamepad configuration guide
├── DOCUMENTATION.md          # This comprehensive documentation
├── engine/                   # Reusable game engine package
│   ├── __init__.py           # Package exports and shared constants
│   ├── ferret_sprite.py      # AnimatedFerret sprite class
│   ├── input_manager.py      # InputManager for keyboard/gamepad
│   ├── base_game.py          # BaseGame abstract class
│   ├── asset_loader.py       # AssetLoader with caching
│   └── audio_manager.py      # AudioManager for sound effects
├── games/                    # Game implementations (one class per file)
│   ├── __init__.py           # Exports all game classes
│   ├── snake.py              # SnakeGame class
│   ├── pacman.py             # PacmanGame class
│   ├── frogger.py            # FroggerGame class
│   ├── centipede.py          # CentipedeGame class
│   ├── digdug.py             # DigDugGame class
│   └── boulderdash.py        # BoulderDashGame class
├── sounds/                   # Sound effect files (optional)
│   └── *.wav/.ogg/.mp3       # menu_move, collect, death, victory, etc.
├── media/                    # Shared sprite assets
│   ├── ferret-long-sprite.png    # 9x8 animated ferret (32x32 per frame)
│   ├── ferret-long-sprite.json   # Sprite metadata (Aseprite export)
│   ├── soupbowl.png              # Collectible sprite
│   ├── soupcan_new.png            # Enemy sprite (translucent)
│   └── weasel.png                # Player character sprite
└── games/                    # Game-specific assets (for reference)
    ├── boulder-dash/images/
    ├── centipede/Green Sprites/
    └── ...
```

### Engine Package

The `engine/` package provides reusable components for building games:

| Module | Class | Purpose |
|--------|-------|---------|
| `ferret_sprite.py` | `AnimatedFerret` | Animated sprite with 9 states, auto-flipping, bounds clamping |
| `input_manager.py` | `InputManager` | Unified keyboard/gamepad input with edge detection |
| `base_game.py` | `BaseGame` | Abstract base class with standard game loop |
| `asset_loader.py` | `AssetLoader` | Cached image/sound loading with fallbacks |
| `audio_manager.py` | `AudioManager` | Sound effects and music with graceful fallback |

**Shared Constants** (exported from `engine/__init__.py`):
- Window: `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `FPS`
- Colors: `WEASEL_BROWN`, `WEASEL_TAN`, `WEASEL_WHITE`, `BURROW_BROWN`, `BLACK`, `WHITE`, etc.
- Buttons: `BUTTON_A`, `BUTTON_B`, `BUTTON_SELECT`, `BUTTON_START`, `DEADZONE`

**Backward-Compatible Functions**:
- `get_dpad()`, `get_button()`, `get_any_action_button()`, `get_any_back_button()`
- `load_media_image()`, `get_weasel_color()`, `init_joystick()`

### Games Package

All games are implemented as classes inheriting from `BaseGame`:

```python
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

game_classes = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]
```

Each game class implements these methods from `BaseGame`:
- `setup()` - Initialize game state and load assets
- `handle_input()` - Process player input, return True to exit
- `update(dt)` - Update game logic with delta time
- `render()` - Draw game state to screen

### Execution Flow

```
main()
  ├─ pygame.init()
  ├─ Create InputManager
  └─ Loop:
       ├─ run_menu(screen) → AnimatedFerret navigates menu
       │                   → Returns game index or -1 (test) or None (exit)
       ├─ If -1: test_controller(screen)
       ├─ If None: exit
       └─ game_classes[index](screen, input_manager).run()
                              → Game returns to menu on B/ESC
```

**Class Instantiation Pattern**:
```python
# In game_launcher.py main():
game = game_classes[selection](screen, input_manager)
game.run()
```

---

## 5. Games Reference

### 5.1 Snake

**Location**: Embedded in `game_launcher.py` (lines 307-385)

**Description**: Classic snake game - eat food and grow longer.

**Mechanics**:
- Grid-based movement (20x20 pixel cells)
- 40x30 cell grid
- Direction changes on D-pad input
- Score +10 per food eaten
- Game over on wall/self collision

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys / WASD | D-pad |
| Restart (game over) | Enter | A / START |
| Return to menu | ESC | B |

**Visual Elements**:
- Green background with grid lines
- Weasel color palette for snake body
- `soupbowl.png` for food sprite

---

### 5.2 Pac-Man

**Location**: Embedded in `game_launcher.py` (lines 388-513)
**Original**: `games/pacman/pacman.py`

**Description**: Navigate the maze, eat all dots, avoid ghosts.

**Mechanics**:
- Continuous movement in last pressed direction
- Hardcoded maze layout
- 4 ghosts with pre-programmed movement patterns
- Collision with ghost or clearing all dots resets level

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys | D-pad (continuous) |
| Return to menu | ESC | B |

**Visual Elements**:
- Blue maze walls
- `weasel.png` for Pac-Man
- `soupcan_new.png` for ghosts (translucent)
- `soupbowl.png` (scaled) for pellets

**Classes**:
- `Wall` - Maze wall sprite
- `Player` - Pac-Man character with collision detection
- `Ghost` - Ghost with programmed movement routes
- `Block` - Pellet sprite

---

### 5.3 Frogger

**Location**: Embedded in `game_launcher.py` (lines 516-630)
**Original**: `games/frogger/frogger.py`

**Description**: Help the frog cross the road and river safely.

**Mechanics**:
- 12 lanes total (4 car lanes, 4 log lanes, 4 safe zones)
- Grid-based movement (32x32 pixels per move)
- Cars kill on contact
- Logs save from drowning (attach and ride)
- 3 lives system
- Score +10 per row, +200 for reaching top

**Lane Layout** (top to bottom):
1. Safe zone (grass)
2-5. Log lanes (water)
6-7. Safe zones (grass)
8-11. Car lanes (road)
12. Start zone (grass)

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys | D-pad (discrete) |
| Start game | Enter | A / START |
| Return to menu | ESC | B |

**Visual Elements**:
- Green grass, blue water, grey road
- `soupbowl.png` for frog
- Weasel palette for car segments
- Brown for log sprites

---

### 5.4 Centipede

**Location**: Embedded in `game_launcher.py` (lines 633-753)
**Original**: `games/centipede/GameMain.py`

**Description**: Shoot the descending centipede before it reaches you.

**Mechanics**:
- Player turret moves in bottom portion of screen
- Single bullet at a time (no rapid fire)
- 8-segment centipede with head
- Centipede bounces off walls and descends
- Mushrooms obstruct movement, 4 hits to destroy
- Dead centipede segments spawn mushrooms

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys | D-pad (continuous) |
| Shoot | Space | A |
| Return to menu | ESC | B |

**Scoring**:
- Head segment: 100 points
- Body segment: 10 points
- Mushroom: 1 point

**Visual Elements**:
- Black background
- `soupcan_new.png` for player turret (translucent)
- Weasel palette for centipede segments (brown head, tan/white body)
- Green mushroom sprites from `Green Sprites/`

---

### 5.5 Dig Dug

**Location**: Embedded in `game_launcher.py` (lines 756-832)
**Original**: `games/dig-dug/Game.py`

**Description**: Dig tunnels, collect crystals, avoid enemies.

**Mechanics**:
- Continuous movement
- 3 crystals to collect
- 2 boulders as obstacles (impassable)
- 2 enemies with random movement
- Game over on enemy collision
- Win by collecting all 3 crystals

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys | D-pad (continuous) |
| Return to menu | ESC | B |

**Visual Elements**:
- `Level.png` for background (or brown fallback)
- `weasel.png` for player
- `soupbowl.png` for crystals
- `soupcan_new.png` for enemies (translucent)

---

### 5.6 Boulder Dash

**Location**: Embedded in `game_launcher.py` (lines 835-936)
**Original**: `games/boulder-dash/BoulderDash.py`

**Description**: Collect diamonds while avoiding falling boulders.

**Mechanics**:
- Grid-based movement (32x32 tiles)
- 25x18 cell grid
- Dig through dirt by moving
- Push rocks horizontally (cannot pull)
- Rocks fall when space below is empty
- Rocks crush player if hit from above
- Collect 5 diamonds to win
- 3 lives system

**Level Elements**:
- `#` Wall (solid, cannot pass)
- `x` Dirt (diggable)
- `o` Rock (pushable, falls)
- `d` Diamond (collectible)
- `s` Space (empty)

**Controls**:
| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move | Arrow keys | D-pad (discrete) |
| Return to menu | ESC | B |

**Visual Elements**:
- Sprite sheet for walls/dirt/rocks from `images/sprites_sheet.png`
- `weasel.png` for player
- `soupbowl.png` for diamonds

---

## 6. Input System

### Keyboard Controls

All games support standard keyboard input:
- **Arrow keys**: Movement
- **WASD**: Movement (Snake only)
- **Enter**: Confirm/Start
- **ESC**: Back/Exit
- **Space**: Shoot (Centipede)
- **T**: Controller test mode (menu only)
- **M**: Toggle audio mute (global)

### Gamepad Configuration

**Default Button Mapping** (NES USB Controllers):
```python
BUTTON_A = 1       # Right face button (confirm/action)
BUTTON_B = 2       # Bottom face button (back/cancel)
BUTTON_SELECT = 8  # Select button
BUTTON_START = 9   # Start button
DEADZONE = 0.3     # Analog stick threshold
```

**D-pad Detection Priority**:
1. Hat/POV (most common for NES controllers)
2. Axis 4 (Y-axis for some generic controllers)
3. Axis 0 (X-axis fallback)
4. Axis 1 (Y-axis fallback)

### Input Functions

```python
# Get D-pad direction
def get_dpad():
    """Returns (dx, dy) where -1=left/up, +1=right/down, 0=neutral"""

# Check specific button
def get_button(bid):
    """Returns True if button is pressed"""

# Check action buttons
def get_any_action_button():
    """Returns True if A, Start, or button 0/1 pressed"""

# Check back buttons
def get_any_back_button():
    """Returns True if B or Select pressed"""
```

### Movement Patterns

**Continuous Movement** (Pac-Man, Centipede, Dig Dug):
```python
dp = get_dpad()
if dp[0] != 0: player.move(dp[0], 0)
if dp[1] != 0: player.move(0, dp[1])
```

**Grid/Discrete Movement** (Snake, Frogger, Boulder Dash):
```python
dp = get_dpad()
if dp != last_dp:  # Only on state change
    if dp[0] != 0: player.move(dp[0], 0)
    if dp[1] != 0: player.move(0, dp[1])
last_dp = dp
```

### Edge Detection Pattern

For single-press actions (prevents repeating while held):
```python
prev_back = False

while True:
    back_now = get_any_back_button()
    if back_now and not prev_back:
        return  # Exit to menu
    prev_back = back_now
```

### Controller Test Mode

Press **T** at the main menu to enter test mode:
- Displays controller name and capabilities
- Shows real-time axis values
- Displays button press detection
- Shows D-pad interpretation

---

## 7. Visual Theming

The WES features a cohesive "weasel burrow" aesthetic that creates an underground, cozy atmosphere across all games and the launcher menu.

### 7.1 Weasel Color Palette

The color palette evokes natural ferret/weasel coloring and earthy underground tones:

```python
# Primary weasel colors (defined in engine/__init__.py)
WEASEL_BROWN = (139, 90, 43)     # Rich brown - head/front segments
WEASEL_TAN = (210, 180, 140)     # Tan/cream - body segments
WEASEL_WHITE = (255, 248, 220)   # Cream white - underbelly/accent
BURROW_BROWN = (101, 67, 33)     # Dark earthy brown - backgrounds

# Aliases for compatibility
FERRET_BROWN = WEASEL_BROWN
FERRET_TAN = WEASEL_TAN
FERRET_WHITE = WEASEL_WHITE
```

**Usage Guidelines**:
- **WEASEL_BROWN**: Use for head/front of multi-segment sprites (snake head, centipede head)
- **WEASEL_TAN**: Use for body segments in repeating patterns
- **WEASEL_WHITE**: Use sparingly as accent (every 3rd segment)
- **BURROW_BROWN**: Use as background for menus and underground game areas

### 7.2 Color Selection Function

```python
def get_weasel_color(index: int) -> tuple:
    """Get weasel color for segment based on index (0=head/front).

    Pattern: Brown (head) → Tan → White → Tan → Tan → Tan...

    Args:
        index: Segment index, 0 is head/front.

    Returns:
        RGB tuple for the segment color.
    """
    if index == 0:
        return WEASEL_BROWN   # Head - rich brown
    elif index == 1:
        return WEASEL_TAN     # First body - tan
    elif index == 2:
        return WEASEL_WHITE   # Accent - cream white
    else:
        return WEASEL_TAN     # Repeating tans for rest of body
```

### 7.3 Menu Burrow Aesthetic

The launcher menu creates an underground burrow atmosphere using several layered effects:

#### Background Generation

```python
def generate_organic_dirt_spots(random_module):
    """Generate organic-looking dirt spots with clustering and varying sizes.

    Creates 15 cluster centers randomly distributed across the screen.
    Each cluster contains 4-10 dirt spots with:
    - Gaussian-like distribution around center (±80 pixels)
    - Varying sizes (2-12 pixels, weighted toward smaller)
    - Earth-tone colors from browns palette
    """
    colors = [(80, 50, 20), (120, 80, 40), (60, 40, 15), (90, 60, 25), (70, 45, 18)]
    # ... generates list of (x, y, size, color) tuples
```

#### Vignette Overlay

```python
def create_vignette_surface():
    """Create a semi-transparent vignette overlay for burrow depth effect.

    Draws 20 concentric rectangles with increasing opacity (0-80 alpha)
    from center to edges, creating a subtle darkening at screen borders
    that suggests depth and enclosed underground space.
    """
```

#### Tunnel Lines

Dark earthy lines connect game buttons, suggesting burrow passages:
- Outer line: `(70, 45, 20)` - 8px width
- Inner line: `(90, 60, 30)` - 4px width for depth effect

#### Dust Particles

```python
class DustParticle:
    """Simple dust particle spawned when ferret moves.

    - Spawns near ferret's feet with random offset
    - Drifts upward with slight horizontal movement
    - Fades out over 15-30 frames
    - Earth-tone colors: (180,140,100), (160,120,80), (140,100,60)
    """
```

### 7.4 AnimatedFerret States

The `AnimatedFerret` class (in `engine/ferret_sprite.py`) provides 9 animation states with automatic transitions based on movement and idle time.

#### Animation States Reference

| State | Row | Trigger | Duration | Description |
|-------|-----|---------|----------|-------------|
| `idle` | 0 | Default / movement stops | < 10 sec | Alert, standing still |
| `idle2` | 1 | Extended idle | 10-30 sec | Looking around, curious |
| `sleep` | 7 | Long idle | > 30 sec | Sleeping animation |
| `movement` | 2 | D-pad input | While moving | Walking/running |
| `dig` | 3 | Game-specific | Manual | Digging through dirt |
| `jump` | 5 | Game-specific | Manual | Hopping/jumping |
| `emerge` | 6 | Game-specific | Manual | Emerging from ground |
| `disappear` | 4 | Game-specific | Manual | Vanishing/hiding |
| `death` | 8 | Game over | Manual | Death animation |

#### Idle Timer Thresholds (at 60 FPS)

```python
IDLE2_THRESHOLD = 10 * FPS   # 600 frames = 10 seconds
SLEEP_THRESHOLD = 30 * FPS   # 1800 frames = 30 seconds
```

#### State Transition Logic

```python
# In menu update loop:
if dp[0] != 0 or dp[1] != 0:
    # Movement detected - wake up and reset idle timer
    if idle_frames > IDLE2_THRESHOLD:
        ferret.set_state('idle')
    idle_frames = 0
else:
    idle_frames += 1
    # Progressive idle state transitions
    if idle_frames == SLEEP_THRESHOLD:
        ferret.set_state('sleep')
    elif idle_frames == IDLE2_THRESHOLD:
        ferret.set_state('idle2')
```

#### Game-Specific State Usage

| Game | States Used | Notes |
|------|-------------|-------|
| Menu | idle, idle2, sleep, movement | Automatic transitions |
| Snake | movement | Always moving |
| Pac-Man | movement | Continuous navigation |
| Frogger | jump, movement | Hop-based movement |
| Centipede | idle, movement | Turret movement |
| Dig Dug | dig, movement, death | Digging through terrain |
| Boulder Dash | dig, movement, death, emerge | Mining and respawn |

### 7.5 Sprite Assets

| Asset | File | Dimensions | Frames | Purpose |
|-------|------|------------|--------|---------|
| Animated Ferret | `ferret-long-sprite.png` | 256×288 | 9×8 (72 total) | Menu avatar, player in some games |
| Ferret Metadata | `ferret-long-sprite.json` | - | - | Aseprite export with frame coords |
| Player Character | `weasel.png` | Various | Static | Pac-Man, Dig Dug, Boulder Dash player |
| Enemy Sprite | `soupcan_new.png` | Various | Static | Ghosts, enemies, obstacles (translucent) |
| 8-bit Enemy | `soupcan_8bit.png` | Pixel art | Static | Retro-styled enemy variant |
| Collectible | `soupbowl.png` | Various | Static | Food, pellets, diamonds, crystals |

#### Sprite Sheet Layout (ferret-long-sprite.png)

```
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 0: idle
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 1: idle2
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 2: movement
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 3: dig
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 4: disappear
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 5: jump
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 6: emerge
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 7: sleep
+-------+-------+-------+-------+-------+-------+-------+-------+
| F0    | F1    | F2    | F3    | F4    | F5    | F6    | F7    | Row 8: death
+-------+-------+-------+-------+-------+-------+-------+-------+
Each frame: 32×32 pixels
```

### 7.6 Thematic Sprite Roles

The three main sprites serve consistent thematic roles across all games:

#### Soupcan_new - The Enemy

Represents dangers and obstacles the ferret must avoid (rendered with translucency):
- **Pac-Man**: Ghosts chasing through tunnels
- **Centipede**: Part of the centipede invasion
- **Dig Dug**: Underground enemies to avoid

#### Soupbowl - The Reward

Represents food and collectibles the ferret seeks:
- **Snake**: Food that makes the ferret family grow
- **Pac-Man**: Treats scattered through tunnels
- **Dig Dug**: Crystals to collect
- **Boulder Dash**: Diamonds to mine

#### Weasel/Ferret - The Protagonist

The player character navigating the underground world:
- Uses weasel color palette for multi-segment sprites
- Uses `weasel.png` for single-sprite games
- Uses `AnimatedFerret` for animated movement

### 7.7 Game-Specific Theming Details

| Game | Player Sprite | Enemy Sprite | Collectible | Background Theme |
|------|---------------|--------------|-------------|------------------|
| Snake | Weasel palette body segments (head=brown, body=tan/white) | - | soupbowl.png | Green grass with grid |
| Pac-Man | weasel.png | soupcan_new.png ghosts (translucent) | soupbowl.png pellets | Blue maze tunnels |
| Ferret Crossing | AnimatedFerret with jump state | Weasel palette car segments | - | Road and water lanes |
| Centipede | soupcan_new.png turret | Weasel palette centipede | - | Black with mushrooms |
| Dig Dug | weasel.png + dig animation state | soupcan_new.png enemies | soupbowl.png crystals | Brown underground |
| Boulder Dash | weasel.png | Grey boulders | soupbowl.png diamonds | Dirt and rock grid |

### 7.8 Fallback Rendering

All sprite loading includes fallback logic for systems without image files:

```python
from engine import AssetLoader

loader = AssetLoader()

# Method 1: Returns None if not found
img = loader.load_image('weasel.png', (32, 32))
if img:
    screen.blit(img, position)
else:
    pygame.draw.circle(screen, WEASEL_BROWN, position, 16)

# Method 2: Always returns a surface (creates colored fallback)
img = loader.load_image_or_fallback('weasel.png', (32, 32), WEASEL_BROWN)
screen.blit(img, position)  # Always works
```

The `AnimatedFerret` class automatically creates a fallback brown ellipse sprite if the sprite sheet fails to load.

---

## 8. Code Reference

### Global Constants

```python
# Window settings (also in engine/__init__.py)
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
DARK_BLUE = (20, 20, 60)
HOVER_COLOR = (60, 60, 120)

# Weasel palette (canonical source: engine/__init__.py)
WEASEL_BROWN = (139, 90, 43)
WEASEL_TAN = (210, 180, 140)
WEASEL_WHITE = (255, 248, 220)
BURROW_BROWN = (101, 67, 33)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
```

### Engine Module Reference

#### AnimatedFerret (engine/ferret_sprite.py)

Animated ferret sprite with 9 animation states, automatic flipping, and bounds clamping.

```python
from engine import AnimatedFerret

ferret = AnimatedFerret(
    x=400,           # Initial X position (center)
    y=300,           # Initial Y position (center)
    scale=2,         # Scale multiplier (1 = 32x32)
    speed=4.0,       # Movement speed in pixels/update
    frame_delay=6,   # Frames between animation updates
    sprite_path=None,  # Custom sprite path (optional)
    json_path=None,    # Custom JSON path (optional)
)
```

**Properties**:
- `x, y` - Position (centered on sprite)
- `speed` - Movement speed
- `facing_right` - Direction flag (auto-updates on movement)
- `state` - Current animation state name
- `is_moving` - True if currently moving
- `sprite_size` - Actual pixel size after scaling

**Methods**:
```python
ferret.update(dx, dy)         # Update position/animation (-1, 0, or 1)
ferret.draw(surface)          # Render to screen (centered)
ferret.get_rect()             # Return pygame.Rect for collision
ferret.get_image()            # Get current frame as Surface
ferret.set_state(name)        # Set animation: 'idle', 'movement', 'jump', etc.
ferret.set_position(x, y)     # Set position directly
ferret.clamp_to_bounds(min_x, min_y, max_x, max_y)  # Constrain position
ferret.get_available_animations()  # List loaded animation names
```

**Animation States** (9 rows in sprite sheet):
- `idle`, `idle2`, `movement`, `dig`, `disappear`, `jump`, `emerge`, `sleep`, `death`

---

#### InputManager (engine/input_manager.py)

Unified keyboard/gamepad input handling with edge detection.

```python
from engine import InputManager

input_mgr = InputManager(
    button_map=None,   # Custom button mappings (optional)
    key_map=None,      # Custom key mappings (optional)
    deadzone=0.3,      # Analog stick threshold
)
```

**Button Constants**:
```python
InputManager.BUTTON_A = 1
InputManager.BUTTON_B = 2
InputManager.BUTTON_SELECT = 8
InputManager.BUTTON_START = 9
InputManager.DEADZONE = 0.3
```

**Methods**:
```python
input_mgr.update()                # Call once per frame (required!)
input_mgr.get_dpad()              # Returns (dx, dy) tuple
input_mgr.is_pressed(name)        # True if held: 'action', 'back', 'up', etc.
input_mgr.was_pressed(name)       # True on press edge (one frame only)
input_mgr.was_released(name)      # True on release edge
input_mgr.get_any_action_button() # True if any action button pressed
input_mgr.get_any_back_button()   # True if any back button pressed
input_mgr.get_button(button_id)   # Check specific gamepad button
input_mgr.has_joystick()          # True if gamepad connected
input_mgr.init_joystick()         # Reinitialize gamepad
input_mgr.get_controller_info()   # Dict with controller details
```

**Logical Names** for `is_pressed()` / `was_pressed()`:
- Directions: `'up'`, `'down'`, `'left'`, `'right'`
- Actions: `'action'`, `'back'`, `'start'`, `'select'`, `'a'`, `'b'`

---

#### BaseGame (engine/base_game.py)

Abstract base class for game implementations. Inherit and implement abstract methods.

```python
from engine import BaseGame, InputManager

class MyGame(BaseGame):
    def setup(self):
        """Called once at initialization. Set up game state."""
        self.score = 0
        self.player_x = 400

    def handle_input(self):
        """Process input. Return True to exit to menu."""
        if self.input_manager.was_pressed('back'):
            return True
        return False

    def update(self, dt):
        """Update game logic. dt is delta time in seconds."""
        dx, dy = self.input_manager.get_dpad()
        self.player_x += dx * 200 * dt

    def render(self):
        """Draw game. Don't call pygame.display.flip() here."""
        self.screen.fill((0, 0, 0))
        # Draw game elements

# Usage:
def run_mygame(screen):
    game = MyGame(screen, InputManager())
    game.run()
```

**Inherited Attributes**:
- `self.screen` - pygame display surface
- `self.input_manager` - InputManager instance
- `self.clock` - pygame.Clock for timing

**Game Loop** (in `run()` method):
1. Process pygame events (QUIT, ESC)
2. Call `handle_input()` → exit if returns True
3. Call `update(dt)` with delta time
4. Call `render()`
5. `pygame.display.flip()` and `clock.tick(60)`

---

#### AssetLoader (engine/asset_loader.py)

Cached asset loading with automatic fallbacks.

```python
from engine import AssetLoader

loader = AssetLoader(base_dir=None)  # Auto-detects project root
```

**Methods**:
```python
# Image loading
loader.load_image(filename, size=None)  # Returns Surface or None
loader.load_image_or_fallback(filename, size, fallback_color)  # Always returns Surface
loader.create_fallback_surface(size, color, with_border=False)

# Sprite sheets
loader.load_sprite_sheet(filename, frame_size, frame_names, scale=None)
loader.load_sprite_sheet_grid(filename, frame_size, cols, rows, scale=None)

# Audio
loader.load_sound(filename, volume=1.0)  # Returns Sound or None
loader.play_sound(filename, volume=1.0)  # Load and play immediately

# Cache management
loader.clear_cache()
loader.preload_images(filenames, size=None)
```

**Color Constants** (also exported from `engine.__init__`):
```python
WEASEL_BROWN = (139, 90, 43)
WEASEL_TAN = (210, 180, 140)
WEASEL_WHITE = (255, 248, 220)
BURROW_BROWN = (101, 67, 33)
```

**Helper Function**:
```python
from engine import get_weasel_color
color = get_weasel_color(0)  # Returns WEASEL_BROWN
color = get_weasel_color(1)  # Returns WEASEL_TAN
color = get_weasel_color(2)  # Returns WEASEL_WHITE
color = get_weasel_color(n)  # Returns WEASEL_TAN for n > 2
```

---

#### AudioManager (engine/audio_manager.py)

Sound effects and music playback with graceful fallback when audio is unavailable.

```python
from engine import AudioManager, get_audio_manager

# Get the global singleton instance (recommended)
audio = get_audio_manager()

# Or create a new instance with custom sounds directory
audio = AudioManager(sounds_dir='/path/to/sounds')
```

**Sound Event Constants**:
```python
AudioManager.SOUND_MENU_MOVE = 'menu_move'       # Menu navigation
AudioManager.SOUND_MENU_SELECT = 'menu_select'   # Selection confirm
AudioManager.SOUND_COLLECT = 'collect'           # Collecting items
AudioManager.SOUND_DEATH = 'death'               # Player death
AudioManager.SOUND_VICTORY = 'victory'           # Level/game win
AudioManager.SOUND_JUMP = 'jump'                 # Jump action
AudioManager.SOUND_DIG = 'dig'                   # Digging action
```

**Properties**:
```python
audio.available   # True if audio system initialized successfully
audio.muted       # True if audio is currently muted
audio.volume      # Current volume (0.0 to 1.0)
```

**Methods**:
```python
# Sound effects
audio.play_sound('collect')         # Play named sound effect
audio.preload('collect', 'death')   # Preload sounds for faster playback

# Music
audio.play_music('theme', loops=-1) # Play background music (-1 = infinite)
audio.stop_music()                  # Stop background music
audio.pause_music()                 # Pause music
audio.resume_music()                # Resume paused music

# Control
audio.toggle_mute()                 # Toggle mute on/off, returns new state
audio.set_mute(True)                # Explicitly set mute state
audio.volume = 0.7                  # Set volume (0.0 to 1.0)
audio.stop_all()                    # Stop all sounds and music
```

**Sound File Resolution**:

The AudioManager looks for sound files in the `sounds/` directory (relative to project root).
It tries multiple extensions in order: `.wav`, `.ogg`, `.mp3`

```
sounds/
├── menu_move.wav      # Menu navigation click
├── menu_select.wav    # Selection confirmation
├── collect.wav        # Item collection
├── death.wav          # Player death
├── victory.wav        # Win/level complete
├── jump.wav           # Jump sound
└── dig.wav            # Digging sound
```

**Graceful Fallback**:

If audio initialization fails or sound files are missing, the game continues silently:
- `audio.available` returns `False` if mixer failed to initialize
- `play_sound()` returns `False` if sound file not found
- No exceptions are raised - games work without audio

**Usage in Games**:

```python
from engine import get_audio_manager, AudioManager

class MyGame(BaseGame):
    def setup(self):
        self.audio = get_audio_manager()

    def handle_input(self):
        if self.input_manager.was_pressed('action'):
            self.audio.play_sound(AudioManager.SOUND_COLLECT)
            self.score += 10

    def on_death(self):
        self.audio.play_sound(AudioManager.SOUND_DEATH)
```

**Mute Toggle**:

Press **M** at any time to toggle audio mute. The mute state persists across games.

```python
# In menu/game loop:
if event.key == pygame.K_m:
    audio_manager.toggle_mute()

# Display mute status
mute_status = "[MUTED]" if audio_manager.muted else ""
```

---

### Game Classes Reference (games/*.py)

All games inherit from `BaseGame` and follow this pattern:

| Game | File | Class | Key Mechanics |
|------|------|-------|---------------|
| Snake | `games/snake.py` | `SnakeGame` | Grid movement, body segments |
| Pac-Man | `games/pacman.py` | `PacmanGame` | Continuous movement, maze navigation |
| Frogger | `games/frogger.py` | `FroggerGame` | Grid movement, lane crossing |
| Centipede | `games/centipede.py` | `CentipedeGame` | Continuous movement, shooting |
| Dig Dug | `games/digdug.py` | `DigDugGame` | Continuous movement, digging |
| Boulder Dash | `games/boulderdash.py` | `BoulderDashGame` | Grid movement, physics |

### Launcher Classes (game_launcher.py)

#### Button

Clickable menu button for game selection.

**Properties**:
- `rect` - pygame.Rect for positioning
- `text` - Button label
- `color` - Button color
- `is_hovered` - Hover state

**Methods**:
```python
def __init__(self, x, y, w, h, text, color, font)
def draw(self, surface, selected=False)
def check_hover(self, pos)
def is_clicked(self, pos)
```

### Backward-Compatible Functions

These functions in `engine/__init__.py` wrap `InputManager` for legacy compatibility:

```python
# Input (wrappers around InputManager)
init_joystick()              # Initialize first detected gamepad
get_dpad()                   # Returns (dx, dy) tuple
get_button(bid)              # Check specific button
get_any_action_button()      # Check action buttons
get_any_back_button()        # Check back buttons

# Assets (wrappers around AssetLoader)
load_media_image(filename, size=None)  # Load from media/
get_weasel_color(index)                # Get palette color
```

### Games List Definition

```python
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

GAMES = [
    {"name": "Snake", "description": "Classic snake game - eat food and grow!", "color": GREEN},
    {"name": "Pac-Man", "description": "Navigate the maze and eat all the dots!", "color": YELLOW},
    {"name": "Frogger", "description": "Help the frog cross the road safely!", "color": CYAN},
    {"name": "Centipede", "description": "Shoot the centipede before it reaches you!", "color": MAGENTA},
    {"name": "Dig Dug", "description": "Dig tunnels and collect crystals!", "color": RED},
    {"name": "Boulder Dash", "description": "Collect diamonds and avoid falling rocks!", "color": WHITE},
]

game_classes = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]
```

---

## 9. Adding New Games

New games should inherit from `BaseGame` and be placed in the `games/` directory.

### Step 1: Create the Game Class

Create a new file `games/yourgame.py`:

```python
"""Your game description."""
import pygame
from engine import (
    BaseGame,
    AnimatedFerret,
    AssetLoader,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WEASEL_BROWN,
    BLACK,
    WHITE,
)

class YourGame(BaseGame):
    """Example game using the engine modules."""

    def setup(self):
        """Initialize game state (called automatically by BaseGame.__init__)."""
        self.score = 0
        self.player_x = WINDOW_WIDTH // 2
        self.player_y = WINDOW_HEIGHT // 2

        # Load assets using AssetLoader
        self.loader = AssetLoader()
        self.player_img = self.loader.load_image_or_fallback(
            'weasel.png', (32, 32), WEASEL_BROWN
        )

        # Or use AnimatedFerret for animated sprites
        self.ferret = AnimatedFerret(x=400, y=300, scale=2)

        self.font = pygame.font.Font(None, 36)

    def handle_input(self):
        """Process input. Return True to exit to menu."""
        self.input_manager.update()  # REQUIRED: Call every frame

        # Edge-detected back button (fires once)
        if self.input_manager.back_pressed():
            return True  # Exit to menu

        # Edge-detected action button
        if self.input_manager.action_pressed():
            self.score += 10

        return False

    def update(self, dt):
        """Update game logic. dt is delta time in seconds."""
        # Get D-pad direction
        dx, dy = self.input_manager.get_dpad()

        # Move player (using delta time for frame-independent movement)
        self.player_x += dx * 200 * dt
        self.player_y += dy * 200 * dt

        # Or update AnimatedFerret
        self.ferret.update(dx, dy)
        self.ferret.clamp_to_bounds(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)

    def render(self):
        """Draw game. Don't call pygame.display.flip() here."""
        self.screen.fill(BLACK)

        # Draw player
        self.ferret.draw(self.screen)

        # Draw HUD
        text = self.font.render(f"Score: {self.score}  [B] Menu", True, WHITE)
        self.screen.blit(text, (10, 10))
```

### Step 2: Export from games Package

Add to `games/__init__.py`:

```python
from .yourgame import YourGame

__all__ = [
    # ... existing games ...
    'YourGame',
]
```

### Step 3: Register in Launcher

Add to `game_launcher.py`:

```python
# At top with other imports
from games import SnakeGame, PacmanGame, ..., YourGame

# In GAMES list:
GAMES = [
    # ... existing games ...
    {"name": "Your Game", "description": "Your game description", "color": GREEN},
]

# In main():
game_classes = [SnakeGame, PacmanGame, FroggerGame,
                CentipedeGame, DigDugGame, BoulderDashGame,
                YourGame]  # Add your class
```

### Loading Assets

**Using AssetLoader (recommended)**:
```python
from engine import AssetLoader, WEASEL_BROWN

loader = AssetLoader()

# Load with automatic fallback
player = loader.load_image_or_fallback('weasel.png', (32, 32), WEASEL_BROWN)

# Load sprite sheet
frames = loader.load_sprite_sheet_grid('sprites.png', (32, 32), cols=8, rows=4)
```

**Using legacy functions**:
```python
player_img = load_media_image('weasel.png', (32, 32))
if not player_img:
    # Manual fallback
    player_img = pygame.Surface((32, 32))
    player_img.fill(WEASEL_BROWN)
```

**Loading from game subdirectory**:
```python
def run_yourgame(screen):
    gd = os.path.join(BASE_DIR, "games", "yourgame")
    os.chdir(gd)

    img = pygame.image.load('local_sprite.png')

    # ... game loop ...

    os.chdir(BASE_DIR)  # IMPORTANT: Change back!
```

### Input Handling Patterns

**Using InputManager (recommended)**:
```python
input_mgr = InputManager()

# In game loop:
input_mgr.update()  # REQUIRED every frame

# Edge detection (fires once per press)
if input_mgr.was_pressed('action'):
    shoot()

if input_mgr.was_pressed('back'):
    return  # Exit

# Held detection (fires every frame while held)
if input_mgr.is_pressed('action'):
    charge_weapon()

# D-pad
dx, dy = input_mgr.get_dpad()
```

**Using legacy functions**:
```python
prev_back = False

while True:
    # Manual edge detection
    back_now = get_any_back_button()
    if back_now and not prev_back:
        return
    prev_back = back_now

    dp = get_dpad()
```

### Using the Weasel Color Palette

```python
from engine import get_weasel_color, WEASEL_BROWN, WEASEL_TAN

# For multi-segment sprites (snake, centipede)
for i, segment in enumerate(segments):
    color = get_weasel_color(i)  # 0=brown, 1=tan, 2=white, 3+=tan
    pygame.draw.rect(screen, color, segment)
```

---

## 10. Troubleshooting

### Controller Issues

**Controller not detected**
```
Symptom: "No controller detected" message
Solutions:
1. Plug in controller BEFORE starting the launcher
2. Try a different USB port
3. Check controller works in other applications
```

**D-pad directions wrong**
```
Symptom: Pressing left moves right, etc.
Solutions:
1. Press T at menu for test mode
2. Note which axes respond to D-pad
3. Edit get_dpad() function:
   - Swap -1 and 1 for inverted axes
   - Change axis numbers if different
```

**D-pad too sensitive/unresponsive**
```
Symptom: Movement triggers too easily or not at all
Solution: Adjust DEADZONE constant
  DEADZONE = 0.3  # Lower = more sensitive
```

**Wrong button numbers**
```
Symptom: A button acts like B, etc.
Solutions:
1. Press T for test mode
2. Press each button, note numbers shown
3. Update constants:
   BUTTON_A = <your A button number>
   BUTTON_B = <your B button number>
```

### Graphics Issues

**Images not loading**
```
Symptom: Colored rectangles instead of sprites
Cause: Missing or corrupted image files
Solutions:
1. Check media/ directory exists
2. Verify PNG files are present
3. Games use fallback colors automatically
```

**Window too small/large**
```
Solution: Edit window constants:
  WINDOW_WIDTH = 800   # Change as needed
  WINDOW_HEIGHT = 600
```

### Game Issues

**Game exits immediately when pressing B**
```
This is intended behavior - B returns to menu from all games
```

**No sound**
```
Solutions:
1. Check system volume
2. Verify pygame.mixer.init() succeeds
3. Check audio files exist in game directories
```

**Game runs too fast/slow**
```
Solution: Adjust clock.tick() value in game loop
  clock.tick(60)  # 60 FPS (lower = slower)
```

### Common Controller Mappings

**8BitDo NES30**
```python
BUTTON_A = 0
BUTTON_B = 1
BUTTON_SELECT = 10
BUTTON_START = 11
# D-pad uses Hat 0
```

**Logitech F310**
```python
BUTTON_A = 1
BUTTON_B = 2
BUTTON_SELECT = 8
BUTTON_START = 9
# D-pad uses Hat 0
```

**DragonRise Generic**
```python
BUTTON_A = 1
BUTTON_B = 2
BUTTON_SELECT = 8
BUTTON_START = 9
# D-pad uses Axis 0 (X) and Axis 4 (Y)
```

**Xbox Controller**
```python
BUTTON_A = 0
BUTTON_B = 1
BUTTON_START = 7
# D-pad uses Hat 0
```

---

## 11. File Reference

### Root Directory

| File | Lines | Purpose |
|------|-------|---------|
| `game_launcher.py` | 1,081 | Main launcher with all 6 embedded games |
| `readme.md` | 279 | Quick start guide and overview |
| `CONTROLLER_GUIDE.md` | 194 | Detailed gamepad configuration |
| `DOCUMENTATION.md` | - | This comprehensive documentation |

### Media Directory

| File | Size | Format | Usage |
|------|------|--------|-------|
| `ferret-long-sprite.png` | ~10KB | PNG | 9x8 animation frames (32x32 each) |
| `ferret-long-sprite.json` | ~1KB | JSON | Sprite metadata |
| `ferret-standing-sprite.png` | ~2KB | PNG | Static ferret pose |
| `soupbowl.png` | ~6KB | PNG | Food/collectible sprite |
| `soupcan_new.png` | ~3KB | PNG | Enemy sprite (translucent) |
| `soupcan_8bit.png` | ~2KB | PNG | 8-bit style variant |
| `soupcan_8bit.svg` | ~1KB | SVG | Vector source |
| `weasel.png` | ~4KB | PNG | Player character |

### Games Directory

| Game | Key Files | Description |
|------|-----------|-------------|
| boulder-dash | `BoulderDash.py`, `BoulderLevels.txt` | 32K original, level data |
| centipede | `GameMain.py`, `GameSprites.py` | Two-file architecture |
| dig-dug | `Game.py`, `Classes.py` | Entity-based design |
| frogger | `frogger.py`, `actors.py` | Actor pattern |
| pacman | `pacman.py` | Monolithic implementation |
| snake | `snake_game.py` | Simple standalone |

### Asset Directories

**boulder-dash/**
- `images/sprites_sheet.png` - Tile sprites
- `sounds/*.ogg` - 9 sound effects

**centipede/**
- `Blue Sprites/` - 50+ sprites
- `Green Sprites/` - Alternate palette
- `Sound/` - Music and SFX

**dig-dug/**
- Various PNG files for level, enemies, player

**pacman/**
- `images/` - Pac-Man, ghosts, walls
- `pacman.mp3` - Background music

---

## License

Educational/personal use project. Individual games may have their own licenses - see their respective README files.

---

*Documentation generated for Weasel Entertainment System v1.0*
