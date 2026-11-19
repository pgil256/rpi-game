# Launcher, deployment and documentation resolution notes

| IDs | Change and evidence |
|---|---|
| A1 | All constructors accept difficulty; all-game/all-difficulty smoke coverage. |
| A2, A6 | Validated audio preferences apply at startup and live; M persists. Fullscreen honors saved preferences and CLI overrides, with Settings showing actual display state. |
| A3 | Launcher shares one InputManager across screens and demos never open/reset hardware. |
| A4 | Shared edge/repeat navigation; no duplicate keyboard direction branch; settings flush one update on exit. |
| A5 | ScriptedInput calls normal handle_input/update inside demo persistence protection. Tests prove all six games move, Defender fires, Boulder sprite stays aligned, and saves/achievements remain unchanged. Recording API removed. |
| B1 | Private Random(42) generators for decorations preserve gameplay randomness. |
| B2 | WASD remains movement; F1/F2/F3 open settings/achievements/stats. |
| B3 | Controller-accessible Options includes every utility screen and Quit. |
| B4 | Activity resets idle; look-around at 15 s, sleep at 30 s, attract at 60 s. Explicit menu state policy preserves animation progression. |
| B5 | Static decorations/title/help and button labels cached; shared cached toast. |
| B6 | Hover updated every frame; fullscreen mouse coordinates map through the viewport. |
| B7 | Title and help use measured centering, fit 800 pixels and were visually inspected. |
| B8 | Controller test shows no-device feedback, stays open and accepts hot-plug. |
| B9 | Common close flag and BaseGame quit_requested propagation; no submenu sys.exit. |
| B10 | Seven 54-pixel rows leave a separate scroll/help region. |
| B11 | Stable logical surface; display mode changes only at startup or preference change. |
| B12 | 4:3 letterboxing with reused scale destination; coordinate mapping regression. |
| B13 | Crash guard with readable return panel and rotating wes.log; shutdown/persistence errors logged. |
| B14 | Consistent Winston Entertainment System/Ferret Crossing naming; neutral game display names retain compatible save IDs. |
| B15 | Removed unused wrappers/imports; shared AchievementToast; Ruff checks and formatter. |
| G4 | Shared lifecycle/overlays/toast; unused wrappers removed. Game-specific HUD/art/difficulty configuration deliberately stays local. |
| D1 | Quoted requirements-file install removes accidental version-string redirection. |
| D2 | Isolated .venv with pinned requirements; no system pip or break-system-packages. |
| D3 | One start.sh launch path using .venv; SDL desktop/audio selection respects Wayland and overrides. |
| D4 | One desktop/console backend, real account/home, correct ownership, quoted generated configuration, executable scripts, console Restart=always and flock. Hardware boot acceptance remains required. |
| D5 | Explicit active-asset allowlist; no archived executable/audio, docs, saves or demos bundled. Writable user data remains outside the bundle. |
| D6 | .gitattributes, LF active source/scripts/docs, executable shell file modes. |
| D7 | Pinned runtime/development dependencies, Python >=3.10, Windows/Linux 3.10/3.12 CI. |
| R1 | Local Git baseline, CI, lint/format config. LICENSE grants no new public rights pending owner/provenance review. |
| R2 | Correct save/config/log ignores; personal launch.txt and real score file preserved locally but untracked. |
| R3 | Unused game folders/media preserved in legacy_reference, excluded from runtime build/tests/lint. |
| R4 | Procedural enemy art removes branding; neutral titles; third-party archive quarantined. Rights inventory and restrictive notice added. Public release remains blocked pending owner evidence for existing code/ferret/bowl artwork and a license decision. |
| R5 | Active Ruff unused-name/import checks pass; historical source remains untouched. |
| T1 | Assertions replace print/bool/tautology tests; returned-value warnings fail pytest. |
| T2 | Isolated regressions cover persistence, input, gameplay/lifecycle, launcher and demos. |
| T3 | 300 simulated steps for all 18 game/difficulty combinations; packaged --smoke-test exercises bundled code/assets with temporary saves. |
| X1 | Config-file/diagnostic workflow documented instead of source constant editing. |
| X2 | Configured hat/axes and auto hat then axes 0/1 documented; removed axis-4 claim. |
| X3 | Current launcher/engine/games architecture replaces stale line-count/embedded-game claims. |
| X4 | Difficulty, scores, settings, achievements, stats, scripted demos and packaging documented. |
| X5 | Current 15/30/60-second idle thresholds documented. |
| X6 | All shortcuts and controller equivalents documented, preserving WASD. |
| X7 | Historical plan marked superseded; inaccurate completion claims identified. |

Additional review regression: InputManager preserves complete keyboard/gamepad taps
between simulation steps, without sticking held input after release. Launcher tests
exercise real demo movement and distinguish dismissal from a mute-setting change.

See the final resolution ledger for consolidated test/build results and limitations.

Transient achievement-save failures now retain a dirty retry marker, retry on repeated unlock checks, and flush during launcher shutdown; a regression verifies recovery without duplicate unlock notification.
