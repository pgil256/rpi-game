# Controller Configuration Guide

This guide helps you configure gamepad support for the Weasel Entertainment System.

## Keyboard Shortcuts

| Key | Action | Location |
|-----|--------|----------|
| Arrow keys | Navigate / Move | Menu, All games |
| WASD | Alternative movement | All games |
| Enter | Confirm / Select | Menu, Game over screens |
| ESC | Back / Exit | Menu (exit app), Games (return to menu) |
| Space | Shoot | Centipede |
| T | Controller test mode | Menu only |
| M | Toggle audio mute | Global (all screens) |

## Quick Reference

Button constants are defined in `engine/__init__.py` and can also be accessed via `InputManager`:

```python
from engine import BUTTON_A, BUTTON_B, BUTTON_SELECT, BUTTON_START, DEADZONE

# Or via InputManager class attributes:
from engine import InputManager
InputManager.BUTTON_A      # 1
InputManager.BUTTON_B      # 2
InputManager.BUTTON_SELECT # 8
InputManager.BUTTON_START  # 9
InputManager.DEADZONE      # 0.3
```

## Identifying Your Controller

Run the launcher and press **T** at the main menu to enter test mode.

The test screen shows:
- **Controller name** - The device name reported by the OS
- **Buttons** - Number of buttons available
- **Axes** - Number of analog axes
- **Hats** - Number of D-pad/POV hats

## Common Controller Types

### NES USB Controllers (Most Common)

Typical mapping:
```
D-pad: Hat 0 (POV)
A: Button 1
B: Button 2
Select: Button 8
Start: Button 9
```

### Generic USB Gamepads

May use axes instead of hat for D-pad:
```
D-pad Left/Right: Axis 0
D-pad Up/Down: Axis 1 or Axis 4
A: Button 0 or 1
B: Button 1 or 2
```

### Xbox-Style Controllers

```
Left Stick: Axis 0 (X), Axis 1 (Y)
D-pad: Hat 0
A: Button 0
B: Button 1
Start: Button 7
```

### PlayStation-Style Controllers

```
Left Stick: Axis 0 (X), Axis 1 (Y)
D-pad: Hat 0
Cross (X): Button 0
Circle: Button 1
Start: Button 9
```

## Configuring Your Controller

### Step 1: Identify D-pad Method

In test mode, move the D-pad and observe:

1. **If Hat 0 changes** → Your controller uses hat input (most common)
2. **If axes change** → Note which axis numbers respond:
   - Axis 0 typically = Left/Right
   - Axis 1 or 4 typically = Up/Down

### Step 2: Identify Button Numbers

Press each button and note the number displayed:
- Note the button for "A" (action/confirm)
- Note the button for "B" (back/cancel)
- Note the button for Start

### Step 3: Edit Configuration

**Option A: Edit engine constants** (affects all games)

Open `engine/__init__.py` and modify the button constants (around line 41):

```python
# Gamepad button mappings (NES-style controller)
BUTTON_A: int = 1       # Change these to match your controller
BUTTON_B: int = 2
BUTTON_SELECT: int = 8
BUTTON_START: int = 9
DEADZONE: float = 0.3
```

**Option B: Configure InputManager per-game**

For game-specific mappings, pass a custom button map:

```python
from engine import InputManager

custom_buttons = {
    'a': 0,        # Your A button
    'b': 1,        # Your B button
    'select': 10,
    'start': 11,
}

input_mgr = InputManager(button_map=custom_buttons, deadzone=0.25)
```

### Step 4: Adjust D-pad Axes (If Needed)

If your D-pad uses unusual axes, you can modify the `InputManager._read_dpad_raw()` method in `engine/input_manager.py`:

```python
# In _read_dpad_raw(), around line 200:
# Modify these lines to match your controller:
if num_axes > 4:
    ax4 = self.joystick.get_axis(4)  # Change 4 to your Up/Down axis
    if ax4 < -self.deadzone: gp_dy = -1
    elif ax4 > self.deadzone: gp_dy = 1

if gp_dy == 0 and num_axes > 0:
    ax0 = self.joystick.get_axis(0)  # Change 0 to your Left/Right axis
    if ax0 < -self.deadzone: gp_dx = -1
    elif ax0 > self.deadzone: gp_dx = 1
```

## Troubleshooting

### D-pad moves wrong directions

Your controller may have inverted axes. In `get_dpad()`, try:
```python
dy = -hat[1]  # Change to: dy = hat[1]
```

Or for axes:
```python
if ax4 < -DEADZONE: dy = -1  # Swap -1 and 1
elif ax4 > DEADZONE: dy = 1
```

### D-pad is too sensitive / unresponsive

Adjust the deadzone:
```python
DEADZONE = 0.3  # Lower = more sensitive, Higher = less sensitive
```

### Left/Right triggers Up/Down movement

Your controller has axis crosstalk. The current code checks axis 4 (Up/Down) first, then only checks axis 0 (Left/Right) if axis 4 is neutral. If your axes are different, adjust accordingly.

### Buttons don't respond

Check that button numbers are within range:
```python
def get_any_action_button():
    nb = joystick.get_numbuttons()
    for b in [0, 1, BUTTON_A, BUTTON_START]:
        if b < nb and joystick.get_button(b):  # b must be < button count
```

### Multiple controllers connected

The launcher uses the first controller (index 0). To use a different controller:
```python
joystick = pygame.joystick.Joystick(0)  # Change 0 to 1, 2, etc.
```

## Example Configurations

### 8BitDo NES30

```python
BUTTON_A = 0
BUTTON_B = 1
BUTTON_SELECT = 10
BUTTON_START = 11
# D-pad uses Hat 0
```

### Logitech F310

```python
BUTTON_A = 1
BUTTON_B = 2
BUTTON_SELECT = 8
BUTTON_START = 9
# D-pad uses Hat 0, Left stick uses Axis 0/1
```

### DragonRise Generic

```python
BUTTON_A = 1
BUTTON_B = 2
BUTTON_SELECT = 8
BUTTON_START = 9
# D-pad uses Axis 0 (X) and Axis 4 (Y) - unusual!
```

## Testing Your Configuration

After making changes:

1. Save your changes (to `engine/__init__.py` or `engine/input_manager.py`)
2. Restart the launcher
3. Press **T** to verify D-pad shows correct directions
4. Test each button shows expected behavior
5. Try a game to confirm controls work properly

## Using InputManager in Your Code

The `InputManager` class provides advanced input features:

```python
from engine import InputManager

# Create manager (auto-detects controller)
input_mgr = InputManager()

# In your game loop:
input_mgr.update()  # REQUIRED: Call once per frame

# Edge detection (fires once per press)
if input_mgr.was_pressed('action'):
    shoot_bullet()

if input_mgr.was_pressed('back'):
    return_to_menu()

# Continuous detection (fires every frame while held)
if input_mgr.is_pressed('up'):
    player.y -= speed

# D-pad direction
dx, dy = input_mgr.get_dpad()  # Returns (-1, 0, or 1) for each axis

# Check connection
if not input_mgr.has_joystick():
    print("No controller detected")

# Get controller info
info = input_mgr.get_controller_info()
if info:
    print(f"Controller: {info['name']}")
    print(f"Buttons: {info['num_buttons']}")
```

### Logical Button Names

Use these names with `was_pressed()` and `is_pressed()`:

| Name | Keyboard Keys | Gamepad |
|------|---------------|---------|
| `'action'` | Enter, Space | A, Start |
| `'back'` | ESC, Backspace | B, Select |
| `'up'` | Up, W | D-pad Up |
| `'down'` | Down, S | D-pad Down |
| `'left'` | Left, A | D-pad Left |
| `'right'` | Right, D | D-pad Right |
| `'a'` | - | Button A |
| `'b'` | - | Button B |
| `'start'` | Enter | Start |
| `'select'` | Tab | Select |
