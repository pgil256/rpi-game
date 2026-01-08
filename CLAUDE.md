# CLAUDE.md - Weasel Entertainment System (WES)

## Project Overview

A unified game launcher featuring 6 classic arcade games (Snake, Pac-Man, Frogger, Centipede, Dig Dug, Boulder Dash) with weasel/ferret theming. Designed for Raspberry Pi with NES-style USB gamepad support.

## Quick Start

```bash
# Run with Python
python game_launcher.py

# Windows with Anaconda
& "C:\Users\user\anaconda3\python.exe" game_launcher.py
```

## Tech Stack

- **Language**: Python 3.6+
- **Framework**: Pygame 2.1.2+
- **Window**: 800x600 @ 60 FPS
- **Platform**: Windows, Linux, macOS, Raspberry Pi

## Project Structure

```
rpi-game/
├── game_launcher.py      # Main launcher (~280 lines)
├── engine/               # Reusable game engine components
│   ├── __init__.py       # Package exports and shared constants
│   ├── ferret_sprite.py  # AnimatedFerret class
│   ├── input_manager.py  # InputManager class
│   ├── base_game.py      # BaseGame abstract class
│   ├── asset_loader.py   # AssetLoader class
│   └── audio_manager.py  # AudioManager class
├── games/                # Game implementations (one class per file)
│   ├── __init__.py       # Exports all game classes
│   ├── snake.py          # SnakeGame class
│   ├── pacman.py         # PacmanGame class
│   ├── frogger.py        # FroggerGame class
│   ├── centipede.py      # CentipedeGame class
│   ├── digdug.py         # DigDugGame class
│   └── boulderdash.py    # BoulderDashGame class
├── media/                # Shared sprite assets
│   ├── ferret-long-sprite.png   # 9x8 animation frames (32x32 each)
│   ├── soupbowl.png             # Food/collectible sprite
│   ├── soupcan_new.png           # Enemy sprite (translucent)
│   └── weasel.png               # Player character
├── sounds/               # Sound effects (optional)
│   └── README.txt        # Instructions for adding sounds
└── games/                # Game-specific assets (sprite sheets, etc.)
    ├── boulder-dash/images/
    ├── centipede/Green Sprites/
    └── ...
```

## Architecture

### Class-Based Design

Games are implemented as classes inheriting from `BaseGame`. The launcher instantiates them:

```python
from games import SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame

game_classes = [SnakeGame, PacmanGame, FroggerGame, CentipedeGame, DigDugGame, BoulderDashGame]

# In main loop:
game = game_classes[selection](screen, input_manager)
game.run()
```

### Engine Module

All shared functionality lives in `engine/`:

```python
from engine import (
    # Classes
    AnimatedFerret,    # Animated sprite for ferret character
    InputManager,      # Keyboard/gamepad input with edge detection
    BaseGame,          # Abstract base class for games
    AssetLoader,       # Image loading with caching and fallbacks
    AudioManager,      # Sound effects with graceful fallback

    # Constants
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
    WEASEL_BROWN, WEASEL_TAN, WEASEL_WHITE, BURROW_BROWN,
    BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA,
    BUTTON_A, BUTTON_B, BUTTON_SELECT, BUTTON_START, DEADZONE,

    # Helpers
    get_weasel_color,
    get_audio_manager,
)
```

### Key Constants (in engine/__init__.py)

```python
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Weasel color palette
WEASEL_BROWN = (139, 90, 43)   # Head/front
WEASEL_TAN = (210, 180, 140)   # Body
WEASEL_WHITE = (255, 248, 220) # Accent
BURROW_BROWN = (101, 67, 33)   # Background

# Gamepad buttons
BUTTON_A = 1       # Right face button (confirm)
BUTTON_B = 2       # Bottom face button (back)
BUTTON_SELECT = 8
BUTTON_START = 9
DEADZONE = 0.3
```

### InputManager Methods

```python
input_manager = InputManager()

# Call once per frame to update edge detection state
input_manager.update()

# Edge-detected button presses (True only on first frame pressed)
input_manager.action_pressed()  # A, Start, or common action buttons
input_manager.back_pressed()    # B, Select, or common back buttons

# Continuous state
input_manager.get_dpad()        # Returns (dx, dy): -1/0/+1 for each axis
input_manager.get_button(bid)   # Check specific button by ID
input_manager.get_any_action_button()  # True while held
input_manager.get_any_back_button()    # True while held
```

### AnimatedFerret States

```python
ferret = AnimatedFerret(x, y, scale=1, speed=4, frame_delay=6)

# Available states (from ANIMATION_STATES)
ferret.set_state('idle')      # Standing still
ferret.set_state('idle2')     # Looking around (auto after 5s idle)
ferret.set_state('movement')  # Walking/running
ferret.set_state('dig')       # Digging through dirt
ferret.set_state('jump')      # Jumping/hopping
ferret.set_state('death')     # Death animation
ferret.set_state('emerge')    # Emerging from ground/respawn
ferret.set_state('sleep')     # Sleeping (menu only - see note below)

# Update and render
ferret.update(dx, dy)  # dx, dy are direction inputs
ferret.draw(screen)
```

**Sleep Animation Note**: The 'sleep' state is reserved for the main menu only.
Games should NOT use the sleep animation - use idle/idle2 for inactive states.
The menu handles sleep transitions explicitly after 90 seconds of inactivity.
AnimatedFerret.update() will auto-transition to idle2 after 5s but never to sleep.

## Game Implementations

| Game | File | Movement Type | Key Mechanics |
|------|------|---------------|---------------|
| Snake | games/snake.py | Grid/discrete | Direction changes, weasel-colored body |
| Pac-Man | games/pacman.py | Continuous | Maze navigation, soupcan_new ghosts |
| Frogger | games/frogger.py | Grid/discrete | Lane crossing, log riding |
| Centipede | games/centipede.py | Continuous | Turret shooting, weasel-colored centipede |
| Dig Dug | games/digdug.py | Continuous | Tunnel digging, crystal collection |
| Boulder Dash | games/boulderdash.py | Grid/discrete | Rock pushing, falling physics |

## Adding a New Game

1. Create a new file `games/yourgame.py`:

```python
from engine import (
    BaseGame,
    AnimatedFerret,
    AssetLoader,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    # ... other constants
)

class YourGame(BaseGame):
    """Your game description."""

    def setup(self):
        """Initialize game state and load assets."""
        self.font = pygame.font.Font(None, 36)
        self.asset_loader = AssetLoader()
        # ... setup code

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        if self.input_manager.back_pressed():
            return True

        # Handle game-specific input
        dp = self.input_manager.get_dpad()
        # ...

        return False

    def update(self, dt):
        """Update game logic. dt is delta time in seconds."""
        # ... update code

    def render(self):
        """Draw the game state to self.screen."""
        self.screen.fill(BLACK)
        # ... render code


def run_yourgame(screen, input_manager):
    """Entry point for running from launcher."""
    game = YourGame(screen, input_manager)
    game.run()
```

2. Add to `games/__init__.py`:
```python
from .yourgame import YourGame
```

3. Add to `game_launcher.py`:
```python
# At top with other imports
from games import ..., YourGame

# In GAMES list
{"name": "Your Game", "description": "Description here", "color": GREEN},

# In main()
game_classes = [..., YourGame]
```

## Movement Patterns

### Continuous (Pac-Man, Centipede, Dig Dug)
```python
dp = self.input_manager.get_dpad()
self.player.update(dp[0], dp[1])
```

### Grid/Discrete (Snake, Frogger, Boulder Dash)
```python
dp = self.input_manager.get_dpad()
if dp != self.last_dpad:  # Edge detection for grid movement
    if dp[0] != 0:
        self._move_player(dp[0], 0)
    elif dp[1] != 0:
        self._move_player(0, dp[1])
self.last_dpad = dp
```

## Asset Loading

```python
from engine import AssetLoader

asset_loader = AssetLoader()  # Uses default media/ directory

# Load from media/ directory with optional scaling
img = asset_loader.load_image('soupbowl.png', (32, 32))

# All sprite loading has fallback logic
if img:
    screen.blit(img, position)
else:
    pygame.draw.rect(screen, color, rect)  # Fallback
```

## Key Classes

### AnimatedFerret (engine/ferret_sprite.py)
Animated sprite for the ferret/weasel character with multiple animation states.

### InputManager (engine/input_manager.py)
Unified keyboard/gamepad input handling with edge detection for button presses.

### BaseGame (engine/base_game.py)
Abstract base class that provides the game loop structure. Subclasses implement:
- `setup()` - Initialize state
- `handle_input()` - Process input, return True to exit
- `update(dt)` - Update game logic
- `render()` - Draw to screen

### AssetLoader (engine/asset_loader.py)
Centralized asset loading with caching and automatic fallbacks.

### AudioManager (engine/audio_manager.py)
Sound effects and music with graceful fallback when audio is unavailable.

```python
from engine import AudioManager, get_audio_manager

# Get the global audio manager instance
audio = get_audio_manager()

# Play sound effects using standard event names
audio.play_sound(AudioManager.SOUND_MENU_MOVE)    # Menu navigation
audio.play_sound(AudioManager.SOUND_MENU_SELECT)  # Game selection
audio.play_sound(AudioManager.SOUND_COLLECT)      # Collecting items
audio.play_sound(AudioManager.SOUND_DEATH)        # Player death
audio.play_sound(AudioManager.SOUND_VICTORY)      # Level/game win
audio.play_sound(AudioManager.SOUND_JUMP)         # Jump action
audio.play_sound(AudioManager.SOUND_DIG)          # Digging

# Mute control (M key toggles globally)
audio.toggle_mute()  # Toggle mute on/off
audio.muted          # Check mute state
```

Sound files go in `sounds/` directory as .wav, .ogg, or .mp3:
- `menu_move.wav` - Soft click for menu navigation
- `menu_select.wav` - Confirmation sound
- `collect.wav` - Positive chime for collecting items
- `death.wav` - Negative sound for death
- `victory.wav` - Celebration jingle
- `jump.wav` - Jump sound
- `dig.wav` - Digging sound

If sound files are missing, the game works silently without errors.

### Button (game_launcher.py)
Clickable menu button with hover states.

## Testing Controller

Press **T** at main menu to enter controller test mode:
- Shows controller name and capabilities
- Real-time axis values
- Button press detection
- D-pad interpretation

## Common Issues

- **Controller not detected**: Plug in before starting
- **Wrong button mapping**: Use test mode (T), update BUTTON_* constants in engine/__init__.py
- **D-pad issues**: Check axis values in test mode, adjust InputManager if needed
- **Images not loading**: Games use colored fallbacks automatically
- **libpng warnings**: Cosmetic only, does not affect functionality
- **No sound**: Add .wav files to sounds/ directory, or press M to check mute status
