# Winston Entertainment System gameplay audit

November 18, 2026 · Windows working copy · All six games and the launcher

The findings below describe the November 18 build. The November 19 release addresses them. [Implementation and verification](#implementation-and-verification)

Start with two situations where the screen gives the player the wrong information. Tunnel Treats can take a life during a power-up, and Ferret Crossing can count a collision through empty space around the ferret. For replay value, the biggest opportunity is in Crystal Quest and Rocky Burrow. Finishing either campaign once sets the highest score that campaign can award.

## Gameplay and saved progress

| Priority | Finding and evidence | Suggested change |
| --- | --- | --- |
| High | **Tunnel Treats can take a life with power remaining.** A Normal run collected a power bowl on tick 136. Two enemies left the pen in chase mode while the power timer was active. One caught the player on tick 334 with **4.7 seconds** showing. [Enemy release](../../games/pacman.py#L171) · [Contact rules](../../games/pacman.py#L1047) · [Captured frame](../verification/2026-11-18-tunnel-treats-power.png) | Give a waiting enemy the remaining power time when it leaves the pen. Exercise an early pickup followed by contact with a newly released enemy. |
| High | **Ferret Crossing counts traffic hits in transparent sprite padding.** On Normal, I varied the first upward hop by one tick across 120 starting delays. Eight timings killed the ferret even though the car missed the bounding box of the visible jump artwork at the destination. The collision check uses the entire 32 × 32 tile. The same overlap rule lets one pixel of log support the player. [Lane collision](../../games/frogger.py#L148) · [Player rectangle](../../games/frogger.py#L499) | Use a stable, inset body rectangle for traffic and a separate footing test for logs. Check approaches from both sides at the exact edges. Burrow Defender also uses the full sprite square, including 20 transparent rows above the first idle pose. [Defender contact](../../games/centipede.py#L436) |
| High when two copies are open | **A second Windows instance can erase a high score.** Two launcher processes loaded one temporary profile. One saved 100 in Hard Snake and quit. The other saved 600 in Normal Crystal Quest and quit. The score file then contained only Crystal Quest. Each process saves its own snapshot of all records. [Score storage](../../engine/score_manager.py#L29) · [Launcher shutdown](../../game_launcher.py#L1012) | Give each save directory one active Windows instance and bring its window forward on a second launch. Verify both games’ records survive the two-process sequence. |
| Medium | **Snake and Burrow Defender can withhold earned badges.** A Hard Snake run reached 100 and returned to the menu with the record saved. The 30-on-Hard, 50-point, and 100-point badges all stayed locked. In a controlled wave-one Defender encounter, one spider awarded 600 points and its spider badge while the 500-point badge stayed locked. Snake checks those thresholds on death. Defender checks its threshold on wave clear. [Snake awards](../../games/snake.py#L318) · [Defender awards](../../games/centipede.py#L455) | Check score milestones when points are awarded. Verify the badge remains earned after an immediate return to the menu. |
| Medium | **One Escape press backs out twice.** Pressing and releasing Escape in a game returned from play and immediately opened Options. The game loop forwards the press to the shared input manager, then returns before the game consumes it. The home menu receives the pending Back action. [Game event loop](../../engine/base_game.py#L227) · [Home menu](../../game_launcher.py#L540) | Route Escape through the same Back action as the controller. One press should leave the player on game selection, ready to choose another title. |
| Medium | **Remapping face buttons can discard a calibrated D-pad.** The documented command-line wizard requires a fresh D-pad mapping after A/B/Start/Select. Its Left prompt recognizes hats or a negative axis. A pad with four directional buttons cannot finish that step. Saving the wizard’s output over a calibrated test profile removed its device GUID and four direction bindings. [Mapping wizard](../../diagnose_controller.py#L225) · [Profile write](../../diagnose_controller.py#L293) | Allow face-button remapping in Controller Test and update only the selected bindings in the device profile. Verify all four directions after remapping A. |
| Medium | **Switching windows can cost a life, and paused time counts as play.** A moving Hard Snake reached game over after a simulated window-focus loss. Separately, advancing the test clock by an hour while paused earned Dedicated Player. The session timer measures time between starting and leaving the run. [Event handling](../../engine/base_game.py#L225) · [Play-time calculation](../../engine/base_game.py#L138) | Pause active play on focus loss, require an explicit resume, and accumulate play time during active simulation. |

To reproduce the Tunnel Treats capture, seed Python’s gameplay RNG with 19 and start a fresh Normal board. At 60 updates per second, hold Right for 66 ticks, Down for 18, Right for 24, Down for 24, Right for 12, and Up for 2, then release. The normal input and update methods produce the captured collision.

## Replay value and difficulty

**Give completed campaigns a record worth chasing.** Crystal Quest has 12 required gems across three depths and always finishes at **4,200**. Rocky Burrow has 36 required diamonds across five caves and always finishes at **13,100**. Crystal Quest runs with one and three lives remaining produced the same final score. Keep the existing points and add a best clear time per difficulty, with remaining lives shown on the result screen. A player can then tell what improved on a second run. [Crystal Quest scoring](../../games/digdug.py#L474) · [Rocky Burrow cave targets](../../games/boulderdash.py#L510) · [Campaign finish bonus](../../games/boulderdash.py#L832)

**Give Hard Rocky Burrow a reason to push rocks.** A scripted player walked to the nearest reachable diamond, recalculating a four-direction route on the current board each tick. It treated rocks as impassable, used ordinary directional input, and had no lookahead for gravity. Across seeds 0–23, with five caves per campaign and a cutoff of 8,500 ticks, it produced these results. [Cave generation](../../games/boulderdash.py#L534) · [Reachability repair](../../games/boulderdash.py#L600) · [Rock pushing](../../games/boulderdash.py#L980)

| Difficulty | Campaigns cleared | Clears with all three lives |
| --- | ---: | ---: |
| Easy | 22 of 24 | 22 |
| Normal | 23 of 24 | 23 |
| Hard | 22 of 24 | 21 |

These counts measure what that one strategy can accomplish. A short authored chamber on Hard could teach a horizontal push, then pay it off with a second puzzle that asks the player to time a drop. That would give Hard a distinct skill to master.

## Presentation and controls

- **Make the first minute easier to learn.** The difficulty screen has room beneath its three choices. Use it for a rule that changes with the selection and the player’s best for that difficulty. In Snake, Hard turns the wrapping edges into lethal walls. In Burrow Defender, “Hold A or Space to fire” explains the main action missing from the playfield HUD. [Difficulty screen](../../game_launcher.py#L626) · [Snake presets](../../games/snake.py#L63) · [Defender HUD](../../games/centipede.py#L632)
- **Keep the ferret on the home screen and make selection quicker.** The cursor begins over Snake after every trip home. The first button ends at x=350 and the next begins at x=450, leaving a 100-pixel gap where Confirm has no effect. Let a D-pad tap move focus to the neighboring title, animate the ferret to it, and restore the last selection on return. [Button layout](../../game_launcher.py#L488) · [Selection and confirmation](../../game_launcher.py#L553)
- **Match pickups and hazards to what the player sees.** Crystal Quest calls its pickups gems and Rocky Burrow counts diamond-shaped HUD icons, while both playfields show soup bowls. Give the gems a matching silhouette or carry the soup theme through the objective and HUD. In Ferret Crossing, decorative lily pads sit in lethal water and cars and logs are both drawn as blocks. Wheels, bark, and a clearer distinction between scenery and safe footing would communicate the rules at a glance. [Crystal Quest artwork](../../games/digdug.py#L230) · [Rocky Burrow artwork](../../games/boulderdash.py#L374) · [Crossing obstacles](../../games/frogger.py#L75) · [Lily pads](../../games/frogger.py#L328)
- **Make Tunnel Treats enemies recognizable and able to leave the pen.** All four use the same pink sprite despite having different pursuit rules. In a one-minute Normal run alternating right and left in the starting corridor every 140 ticks, Clyde spent the entire final 50 seconds at y=272, moving between x=275 and x=332 inside the pen. Give each enemy a distinguishing mark and use a route through corridor junctions for entering and leaving the pen. [Enemy artwork](../../games/pacman.py#L740) · [Movement decisions](../../games/pacman.py#L323)

## Verification

The Windows source suite finished with **190 passed and one skipped**. The skip was Git Bash initialization inside the sandbox. All four Raspberry Pi shell scripts passed individual Bash syntax checks outside it. Ruff lint and formatting passed. The existing Windows executable passed its smoke test across six games, three difficulties, and 300 updates per combination, including loading the audio assets. [Packaged smoke coverage](../../game_launcher.py#L1089)

Gameplay probes used temporary save profiles and SDL dummy video and audio. Visual review covered current rendered frames of the launcher and all six games. Physical controller feel, TV viewing distance, speaker output, and Raspberry Pi frame pacing still need hardware playtesting.


## Implementation and verification

November 19, 2026 · Windows release

| Area | Result |
| --- | --- |
| Tunnel Treats | Replaying the original route reached tick 334 with all three lives and 4.7 seconds of power. Clyde left the pen frightened, could be eaten on contact, and returned through the gate. Each critter now has its own color and marking. |
| Ferret Crossing and Burrow Defender | Across 120 starting delays in each facing direction, every first-hop traffic hit overlapped painted pixels. Log support requires the center of the ferret to be on the log. Defender damage uses the inset body, and the HUD shows how to fire. |
| Progress and controls | Score badges survive an immediate return to the menu. One Escape press returns to game selection. Focus loss suspends active play until P or Start, and the play clock excludes pauses and transitions. The controller screen and command-line wizard can remap one or four buttons while preserving the device’s directional calibration. |
| Launcher and Windows saves | A D-pad tap selects a title immediately. The launcher remembers the last title and shows rules and records for the highlighted difficulty. Two processes using the same profile preserved both records. A second launch restored the first minimized SDL window on a private Windows desktop. |
| Campaigns | A scripted Normal Crystal Quest run finished all three depths with 4,200 points, one life, and a saved clear time of 0:14.80. A scripted Hard Rocky Burrow run finished all five caves with 13,100 points, three lives, and a saved clear time of 0:32.13. Caves 2 and 4 required a sideways push and a timed drop respectively. Both campaigns display faceted gems and show the clear time, personal best and lives at the finish. |

The Windows suite passed 208 tests. The runner skipped one Bash syntax check and all four scripts passed that check separately in Git Bash. Ruff lint, formatting and the Git whitespace check passed. The installed Windows bundle matched all 148 files in the tested build by SHA-256. Its smoke test exercised six games at three difficulties for 300 steps each and loaded all 25 sound files.

The native window check ran on a private desktop and verified restoration from minimized. Physical gamepad feel, TV readability, speaker output and Raspberry Pi performance still need a hardware playtest.
