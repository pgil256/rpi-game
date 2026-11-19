# NES controller and laptop/HDMI display update

## Changes

- One shared D-pad decoder now handles live polling and queued input events.
  A neutral hat no longer falls back to unrelated analog axes. Short taps and
  releases retain their order.
- Controller test (T from the menu) offers A/C or mouse-accessible guided D-pad
  calibration. It records Up, Right, Down, Left from hats, arbitrary/inverted axes,
  or buttons, saves the neutral/pressed values and SDL device GUID, and applies
  immediately. Other controller GUIDs use automatic mapping. Failed/cancelled
  calibration leaves the prior mapping intact. Calibrated direction buttons do
  not also activate A/B/Start actions.
- F11/Alt+Enter toggles fullscreen from every menu and game; F10 cycles screens.
  Settings offers Fullscreen, Screen, and Picture fit. Fullscreen uses the chosen
  desktop resolution; picture fit preserves 4:3 by default, with an optional
  stretch-to-fill setting. The logical game surface survives display changes.
- Screen selection and picture fit persist. A disconnected selected display
  falls back to Screen 1; fullscreen resolution changes are detected. A failed
  display-mode request falls back to a window. CLI `--display N` is 1-based.

Display API choices follow the [Pygame display documentation](https://www.pygame.org/docs/ref/display.html):
desktop sizes preserve the OS resolution and the display index selects a desktop.
Mirrored outputs can appear as a single desktop; extended outputs are selectable.

## Verification

- Final full suite: **177 passed, 1 skipped**. The skip is the existing Windows sandbox
  Bash limitation. Ruff lint and formatting passed.
- New regression tests cover axis 4/inverted axes, unrelated-axis noise, neutral
  hats, quick tap/release sequences, button D-pads, saved calibration, other GUIDs,
  corrupt data and failed saves, and the complete four-direction calibration flow.
- Display tests cover 1280×720, 1920×1080, 3840×2160, aspect/fill mouse mapping,
  unplug/resolution changes, unavailable screens/mode failure, settings persistence,
  and Alt+Enter suppression so a fullscreen shortcut does not also fire an action.
- Native Windows probe outside the device-virtualizing sandbox found one desktop,
  **1280×720**. Fullscreen used 1280×720, a centered 960×720 game viewport, and an
  unchanged 800×600 logical surface; returning to an 800×600 window succeeded.
- Actual attached device: **USB Gamepad**, 10 buttons, 5 axes, no hats,
  SDL GUID `03006ce8790000001100000000000000`. All axes were -0.0078125 at rest,
  decoded as neutral. The sandbox exposes a different virtual HID GUID/state, so
  it was not used to infer this physical device's directional mapping.
- Five additional regressions replay the captured physical cardinal/neutral
  states; all 21 controller-calibration tests passed after adding them.
- Visually inspected rendered main menu, Settings, Controller test with the real
  device information, and calibration prompt. No clipped controls/text were seen.

The user then pressed Up/Right/Down/Left and confirmed completion. The 23 captured
states show **horizontal movement duplicated across axes 0–3, vertical on axis 4**.
This explains missing Up/Down and false diagonal movement from the old axes 0/1
mapping. Saved and reloaded a GUID-bound calibration in the user's actual Windows
WES data folder: X=0, Y=4, negative Y=Up, neutral=-0.0078. Replaying the capture
now produces all four cardinal directions and neutral correctly. Some samples
contain both X/Y held; these remain diagonal input rather than being discarded.
No further calibration is required for this attached controller; T → C remains
available for other devices or later adjustments.

The native probe, capture, replay, and image outputs are local-only under
`verification/local/`. Physical HDMI-TV acceptance remains unverified because only
one desktop was connected; multi-display coverage above uses simulated enumeration.

The Windows bundle was rebuilt using PyInstaller 6.19.0, passed its packaged
`--smoke-test` (all six games × three difficulties, isolated saves), and was copied
back to `dist/wes` after closing the previous running version normally. The updated
executable was reopened natively with `--fullscreen`, and its full-screen menu was
visually confirmed. SHA-256:
`62DA9DBACAC0AF70EBD43FF51CD21C5C4511D1370AFEEBEC3228628B15CAA689`.
