WINSTON ENTERTAINMENT SYSTEM - ORIGINAL AUDIO
===========================================

Regenerate all files from the project root:
    python generate_sounds.py

Seven original 16-bar looping themes:
    home_theme.wav        Warm, playful welcome (96 BPM, C major)
    snake_theme.wav       Light, nimble movement (116 BPM, D major)
    pacman_theme.wav      Tunnel Treats chase (128 BPM, C minor)
    frogger_theme.wav     Bouncy crossing theme (110 BPM, F major)
    centipede_theme.wav   Burrow Defender pulse (138 BPM, A minor)
    digdug_theme.wav      Crystal Quest exploration (104 BPM, D minor)
    boulderdash_theme.wav Rocky Burrow exploration (100 BPM, C minor)

Each has melody, arpeggiated harmony, bass, and quiet synthesized percussion.
Music is 22050 Hz, mono, 16-bit PCM, with headroom and zero-valued loop edges.
Effects are 44100 Hz, mono, 16-bit PCM, with short attack/release fades.

Eighteen effects:
    menu_move, menu_select, menu_back, start, pause, resume,
    collect, pellet, powerup, jump, dig, shot, hit, rock, turn,
    death, victory, achievement

Settings provides master, music and effects levels. M toggles global mute.
Music is quieter than effects by default; repeated action sounds are throttled.
Game music pauses on pause/game over and stops when returning to the home screen.

All notes and synthesized sounds are authored in generate_sounds.py. No audio
from legacy_reference or third-party recordings is included in the build.
