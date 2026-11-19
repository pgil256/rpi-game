# WES controller guide

Connect an NES-style USB gamepad before or during play. The shared input manager
keeps existing joystick handles alive when screens change, detects removal, and
reacquires available hardware. Keyboard input remains available throughout.

## Mapping

Default button numbers are A=1, B=2, Select=8 and Start=9. These are defaults,
not assumptions in game logic. Every action and the controller test use the
loaded mapping.

For a D-pad that moves incorrectly, open **Options → Controller test** (or press
**T** on the main menu), then choose **Calibrate D-pad** (C). You can also click
that button. Release all controls, then hold **Up, Right, Down, Left** when prompted,
releasing between directions. Start/Esc cancels. The mapping applies immediately
and is saved in `controller_config.json` in the WES user data folder. Test all
four directions before returning to the games. Calibration includes reversed or
nonstandard axes (such as axis 4), hats, and D-pads exposed as separate buttons.
WES stores mappings by controller GUID and loads the matching device profile on
reconnect.

To change **A/B/Select/Start**, open **Remap buttons** (R), choose a single
button or **All four buttons**, and follow the press-and-release prompts. Choose
all four to swap two assignments. Hold D-pad Left for one second, press Escape,
or click Cancel to abandon the changes. The D-pad and other button assignments
carry over. The command-line tool `python diagnose_controller.py` also supports
individual and full button mapping. Restart the launcher after using that tool.

Example:

```json
{
  "controller_name": "USB Gamepad",
  "buttons": {"a": 1, "b": 2, "select": 8, "start": 9},
  "dpad_type": "axes",
  "dpad_axes": {"x": 0, "y": 1},
  "dpad_y_inverted": false
}
```

A configured hat or axis pair is used as selected. Guided calibration saves
`dpad_type: "bindings"` with each direction's physical signal and the controller
GUID. Automatic detection prefers a hat and otherwise uses axes 0/1. A neutral hat
stays neutral even if unrelated analog axes are off-center. Deadzone defaults to
0.3 for automatic/legacy axis mappings; calibrated axes use their measured neutral
and pressed positions. Polling and queued events use the same mapping, so quick
taps and held directions agree. Invalid mappings fall back safely.

## In use

- A D-pad tap highlights the neighboring title. A or Start opens it immediately.
- B or Select opens Options from the main menu. Options includes Settings,
  Achievements, Statistics, Controller test and Quit.
- Menus accept A or Start as confirm; gameplay reserves Start for pause.
- Hold a direction to repeat menu navigation after a 250 ms delay, every 120 ms.
- Controller test shows mappings, axes and connection status on screen; connect
  a device while the test screen is open. Start or B returns.
- During games B/Select returns to the launcher and preserves the current score.
- The home screen stays on the menu when idle; games start only when selected.

Keyboard equivalents: arrows/WASD move; Enter/Space act; P pauses; Esc/Backspace
backs out; Tab is Select; M toggles saved mute. F1/F2/F3 open Settings,
Achievements and Statistics; T opens Controller test. F11/Alt+Enter toggles
fullscreen and F10 selects the next screen. Settings also offers these choices
and picture fit for a laptop or HDMI TV. A and S are movement keys.

## Troubleshooting

1. Open Options → Controller test and inspect the detected device and values.
2. Select **Calibrate D-pad** (C) if directions are wrong, then test again.
3. On Linux inspect device permissions for `/dev/input`; the console installer
   adds the selected account to input/video/render groups. Log in again after
   group changes.
4. Check `wes.log` in the WES data folder for failures. For display/audio startup
   errors on a Pi, verify the chosen desktop or console startup mode first.
