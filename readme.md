# Weasel Entertainment System (WES)

A unified game launcher featuring 6 classic arcade games with a charming ferret burrow theme. All games feature an animated ferret protagonist navigating an underground world of tunnels and treasures. Designed for Raspberry Pi with NES-style USB gamepad support.

## Quick Start

```bash
python game_launcher.py
```

Or with a specific Python path:
```powershell
& "C:\Users\user\anaconda3\python.exe" game_launcher.py
```

## Requirements

- Python 3.6+
- Pygame 2.1.2+ (`pip install pygame`)

## Games Included

| Game | Description | Controls |
|------|-------------|----------|
| Snake | Grow your ferret family - eat soup and get longer! | D-pad: direction |
| Pac-Man | Navigate the tunnels and eat all the treats! | D-pad: continuous movement |
| Ferret Crossing | Help the ferret cross dangerous terrain! | D-pad: grid movement |
| Centipede | Defend your burrow from the centipede invasion! | D-pad: move, A: shoot |
| Dig Dug | Dig for crystals in the underground maze! | D-pad: continuous movement |
| Boulder Dash | Collect diamonds but watch for falling rocks! | D-pad: grid movement |

## Controller Support

### Supported Input Methods
- **Keyboard**: Arrow keys, WASD, Enter, ESC, M (mute toggle)
- **Mouse**: Click menu buttons
- **Gamepad**: NES-style USB controllers

### Default Button Mapping

```
BUTTON_A = 1        # Action/confirm (right face button)
BUTTON_B = 2        # Back to menu (bottom face button)
BUTTON_SELECT = 8   # Back to menu (alternate)
BUTTON_START = 9    # Start/confirm
```

### D-pad Input Methods

The launcher supports multiple D-pad input methods for maximum compatibility:

1. **Hat/POV** - Most common for NES USB controllers
2. **Axis 0** - Left/Right (X axis)
3. **Axis 4** - Up/Down (some controllers use this for D-pad Y)
4. **Axis 1** - Up/Down fallback

### Controller Test Mode

Press **T** at the main menu to enter controller test mode. This displays:
- Controller name and capabilities
- Real-time axis values
- Button press detection
- D-pad interpretation

Use this to identify your controller's button/axis mappings.

## Customizing Controller Mapping

Edit the constants at the top of `game_launcher.py` (around line 70):

```python
BUTTON_A = 1       # Change to match your controller
BUTTON_B = 2
BUTTON_SELECT = 8
BUTTON_START = 9
DEADZONE = 0.3     # Adjust if D-pad is too sensitive/unresponsive
```

### Finding Your Controller's Mapping

1. Run the launcher
2. Press **T** to enter test mode
3. Press each button and note the number shown
4. Move the D-pad and observe which axes change
5. Update the constants accordingly

## Project Structure

```
rpi-game/
├── game_launcher.py      # Main launcher (~280 lines)
├── engine/               # Reusable game engine components
│   ├── __init__.py       # Package exports and shared constants
│   ├── ferret_sprite.py  # AnimatedFerret class (9 animation states)
│   ├── input_manager.py  # InputManager class (keyboard/gamepad)
│   ├── base_game.py      # BaseGame abstract class
│   ├── asset_loader.py   # AssetLoader class (caching, fallbacks)
│   └── audio_manager.py  # AudioManager class (sound effects)
├── games/                # Game implementations (one class per file)
│   ├── __init__.py       # Exports all game classes
│   ├── snake.py          # SnakeGame class
│   ├── pacman.py         # PacmanGame class
│   ├── frogger.py        # FroggerGame class
│   ├── centipede.py      # CentipedeGame class
│   ├── digdug.py         # DigDugGame class
│   └── boulderdash.py    # BoulderDashGame class
├── sounds/               # Sound effect files (optional)
│   └── *.wav/.ogg/.mp3   # menu_move, collect, death, etc.
├── media/                # Shared sprite assets
│   ├── ferret-long-sprite.png  # 9x8 animation frames (32x32 each)
│   ├── soupbowl.png      # Food/collectible sprite
│   ├── soupcan_new.png   # Enemy sprite (translucent)
│   └── weasel.png        # Player character
└── games/                # Game-specific assets
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
ferret.set_state('movement')  # Walking/running
ferret.set_state('dig')       # Digging through dirt
ferret.set_state('jump')      # Jumping/hopping
ferret.set_state('death')     # Death animation
ferret.set_state('emerge')    # Emerging from ground/respawn

# Update and render
ferret.update(dx, dy)  # dx, dy are direction inputs
ferret.draw(screen)
```

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

## Theming

All games feature a consistent "ferret burrow" aesthetic with an animated ferret protagonist, thematic sprites, and an underground color palette.

### The Burrow Aesthetic

The launcher creates an underground burrow atmosphere with:
- **Burrow Brown Background**: Dark earthy brown `(101, 67, 33)` as the base
- **Organic Dirt Spots**: Procedurally generated clusters in earthy tones
- **Tunnel Lines**: Dark connections between game buttons suggesting burrow passages
- **Vignette Overlay**: Darkened edges for depth and underground feel
- **Dust Particles**: Subtle dust effects when the ferret moves

### Ferret Color Palette

```python
WEASEL_BROWN = (139, 90, 43)     # Head/front - rich brown
WEASEL_TAN = (210, 180, 140)     # Body segments - tan/cream
WEASEL_WHITE = (255, 248, 220)   # Accent - cream white underbelly
BURROW_BROWN = (101, 67, 33)     # Background - dark earthy brown
```

### Media Assets

| Asset | File | Usage |
|-------|------|-------|
| Animated Ferret | `ferret-long-sprite.png` | 9-row × 8-frame sprite sheet (32×32 per frame) |
| Player Character | `weasel.png` | Player in Pac-Man, Dig Dug, Boulder Dash |
| Enemy | `soupcan_new.png` | Ghosts, enemies, obstacles (translucent) |
| Collectible | `soupbowl.png` | Food, pellets, diamonds, crystals |

### AnimatedFerret States

The ferret character has 9 animation states with automatic idle transitions:

| State | Trigger | Description |
|-------|---------|-------------|
| `idle` | Default | Standing still, alert |
| `idle2` | 10+ seconds idle | Looking around, curious |
| `sleep` | 30+ seconds idle | Sleeping |
| `movement` | D-pad input | Walking/running |
| `dig` | Game-specific | Digging through dirt |
| `jump` | Game-specific | Hopping motion |
| `death` | Game over | Death animation |
| `emerge` | Respawn | Emerging from ground |

### Game-Specific Theming

| Game | Player | Collectible | Theme |
|------|--------|-------------|-------|
| Snake | Ferret palette body | Soupbowl | Growing ferret family |
| Pac-Man | Weasel sprite | Soupbowl pellets | Tunnel navigation |
| Ferret Crossing | AnimatedFerret | - | Dangerous terrain |
| Centipede | Soupcan_new turret | - | Burrow defense |
| Dig Dug | Weasel + dig animation | Soupbowl crystals | Underground mining |
| Boulder Dash | Weasel sprite | Soupbowl diamonds | Crystal collection |

### Sound Effects

The `AudioManager` provides themed sound events with graceful fallback:

| Event | File | Usage |
|-------|------|-------|
| `menu_move` | `menu_move.wav` | Menu navigation click |
| `menu_select` | `menu_select.wav` | Game selection confirm |
| `collect` | `collect.wav` | Collecting items |
| `death` | `death.wav` | Player death |
| `victory` | `victory.wav` | Level/game win |
| `jump` | `jump.wav` | Jump action |
| `dig` | `dig.wav` | Digging sound |

Press **M** to toggle mute. Sound files are optional - games work silently if missing.

## Troubleshooting

### Controller not detected
- Plug in controller before starting the launcher
- Check console output for "Controller detected" message
- Try a different USB port

### D-pad directions wrong
1. Press **T** to enter test mode
2. Observe which axes respond to D-pad
3. Update `get_dpad()` function to use correct axes

### Buttons mapped incorrectly
1. Press **T** to enter test mode
2. Press A and B buttons, note their numbers
3. Update `BUTTON_A` and `BUTTON_B` constants

### Game exits immediately when pressing B
- This is intended behavior - B returns to menu from games
- B does nothing at the main menu (only ESC exits the app)

## License

Educational/personal use project.
