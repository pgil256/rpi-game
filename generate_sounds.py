#!/usr/bin/env python3
"""
Generate original retro sound effects and seven arranged, looping game themes.
No downloaded recordings, melodies, or runtime synthesis dependencies are used.
"""

import wave
import math
import os
import random
import sys
from array import array
from functools import lru_cache

# Sound output directory
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

# Audio parameters
SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
MUSIC_RATE = 22050
_rng = random.Random(20261114)


def generate_tone(frequency, duration, volume=0.5, fade_out=True):
    """Generate a simple sine wave tone."""
    num_samples = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Sine wave
        value = math.sin(2 * math.pi * frequency * t)

        # Apply fade out to avoid clicks
        if fade_out:
            fade_factor = 1.0 - (i / num_samples) ** 2
            value *= fade_factor

        # Apply volume and convert to 16-bit
        sample = int(value * volume * 32767)
        samples.append(sample)

    return samples


def generate_chirp(start_freq, end_freq, duration, volume=0.5):
    """Generate a frequency sweep (chirp)."""
    num_samples = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        progress = i / num_samples

        # Linear frequency interpolation

        # Calculate phase (integral of frequency)
        phase = 2 * math.pi * (start_freq * t + 0.5 * (end_freq - start_freq) * t * t / duration)
        value = math.sin(phase)

        # Fade out
        fade_factor = 1.0 - progress**2
        value *= fade_factor

        sample = int(value * volume * 32767)
        samples.append(sample)

    return samples


def generate_noise_burst(duration, volume=0.3):
    """Generate a short noise burst with decay."""
    num_samples = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(num_samples):
        progress = i / num_samples
        # White noise with exponential decay
        value = _rng.uniform(-1, 1) * math.exp(-5 * progress)
        sample = int(value * volume * 32767)
        samples.append(sample)

    return samples


def generate_blip(frequency, duration, volume=0.5):
    """Generate a short 8-bit style blip."""
    num_samples = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        progress = i / num_samples

        # Square wave (more retro sound)
        value = 1.0 if math.sin(2 * math.pi * frequency * t) > 0 else -1.0

        # Quick fade out
        value *= 1.0 - progress**0.5

        sample = int(value * volume * 32767)
        samples.append(sample)

    return samples


def generate_arpeggio(frequencies, note_duration, volume=0.4):
    """Generate a quick arpeggio (series of notes)."""
    samples = []

    for freq in frequencies:
        num_samples = int(SAMPLE_RATE * note_duration)
        for i in range(num_samples):
            t = i / SAMPLE_RATE
            progress = i / num_samples

            # Triangle wave
            phase = (freq * t) % 1.0
            value = 4 * abs(phase - 0.5) - 1.0

            # Envelope
            value *= 1.0 - progress**2

            sample = int(value * volume * 32767)
            samples.append(sample)

    return samples


def save_wav(filename, samples, sample_rate=SAMPLE_RATE):
    """Save samples to a WAV file."""
    filepath = os.path.join(SOUNDS_DIR, filename)

    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(sample_rate)

        # Pack samples as signed 16-bit integers
        pcm = array("h", samples)
        # Start/end at zero to avoid clicks, including at a music loop boundary.
        ramp = min(int(sample_rate * 0.004), len(pcm) // 2)
        for i in range(ramp):
            pcm[i] = int(pcm[i] * i / ramp)
            pcm[-1 - i] = int(pcm[-1 - i] * i / ramp)
        if sys.byteorder != "little":
            pcm.byteswap()
        wav_file.writeframes(pcm.tobytes())

    print(f"Created: {filepath}")


MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 10)
# Tempo, tonic (MIDI), scale, four-bar harmony, and two eight-note phrases.
# Each theme has 16 bars with bass, chord arpeggios, melody, and soft percussion.
THEMES = {
    "home": (96, 60, MAJOR, (0, 5, 3, 4), (4, 2, 0, None, 1, 2, 4, 2), (0, 2, 4, 7, 6, 4, 2, None)),
    "snake": (
        116,
        62,
        MAJOR,
        (0, 3, 5, 4),
        (0, 2, 4, 2, 1, 3, 2, None),
        (4, 5, 4, 2, 0, 1, 2, None),
    ),
    "pacman": (
        128,
        60,
        MINOR,
        (0, 5, 3, 4),
        (0, None, 2, 4, None, 3, 2, 1),
        (4, 2, 5, 4, 2, 1, 0, None),
    ),
    "frogger": (
        110,
        65,
        MAJOR,
        (0, 3, 0, 4),
        (0, 2, None, 4, 2, None, 1, 2),
        (4, None, 5, 4, 2, 1, 0, None),
    ),
    "centipede": (
        138,
        57,
        MINOR,
        (0, 5, 3, 4),
        (0, 0, 4, None, 3, 2, 1, 2),
        (4, 5, 4, 2, 3, 1, 0, None),
    ),
    "digdug": (
        104,
        62,
        MINOR,
        (0, 3, 5, 4),
        (0, None, 4, 2, None, 1, 2, None),
        (7, 4, None, 2, 3, 2, 0, None),
    ),
    "boulderdash": (
        100,
        60,
        MINOR,
        (0, 5, 2, 4),
        (0, None, 2, None, 4, 3, 2, None),
        (4, 2, 0, None, 1, 2, 0, None),
    ),
}


def scale_note(tonic, scale, degree):
    octave, step = divmod(degree, 7)
    return tonic + 12 * octave + scale[step]


@lru_cache(maxsize=192)
def music_note(midi, frames, voice):
    frequency = 440 * 2 ** ((midi - 69) / 12)
    samples = array("f")
    attack = MUSIC_RATE * 0.006
    release = MUSIC_RATE * 0.025
    for i in range(frames):
        phase = frequency * i / MUSIC_RATE
        triangle = 4 * abs(phase % 1 - 0.5) - 1
        if voice == "lead":
            angle = 2 * math.pi * phase
            value = (math.sin(angle) + math.sin(3 * angle) / 3 + math.sin(5 * angle) / 5) / 1.54
        else:
            value = triangle
        envelope = min(1, i / attack, (frames - i - 1) / release)
        decay = math.exp(-(1.1 if voice == "bass" else 2.5) * i / frames)
        samples.append(value * envelope * decay)
    return samples


def music_drum(kind):
    frames = int(MUSIC_RATE * (0.16 if kind == "kick" else 0.10 if kind == "snare" else 0.04))
    rng = random.Random({"kick": 17, "snare": 29, "hat": 43}[kind])
    samples = array("f")
    previous = 0.0
    for i in range(frames):
        t = i / MUSIC_RATE
        noise = rng.uniform(-1, 1)
        if kind == "kick":
            value = math.sin(2 * math.pi * (65 * t + 4 * (1 - math.exp(-25 * t)))) * math.exp(
                -28 * t
            )
        elif kind == "snare":
            previous = 0.45 * previous + 0.55 * noise
            value = (previous + 0.2 * math.sin(2 * math.pi * 180 * t)) * math.exp(-42 * t)
        else:
            value = (noise - previous) * 0.5 * math.exp(-100 * t)
            previous = noise
        samples.append(value * min(1, i / 30))
    return samples


def compose_theme(name):
    bpm, tonic, scale, progression, phrase_a, phrase_b = THEMES[name]
    beat = 60 / bpm
    frames = round(16 * 4 * beat * MUSIC_RATE)
    mix = array("f", [0]) * frames

    def add(samples, at_beat, gain):
        start = round(at_beat * beat * MUSIC_RATE)
        for i in range(min(len(samples), frames - start)):
            mix[start + i] += samples[i] * gain

    def note(degree, at_beat, length, voice, gain):
        midi = scale_note(tonic, scale, degree)
        add(music_note(midi, round(length * beat * MUSIC_RATE), voice), at_beat, gain)

    drums = {kind: music_drum(kind) for kind in ("kick", "snare", "hat")}
    for bar in range(16):
        root = progression[bar % 4]
        phrase = phrase_a if bar < 8 else phrase_b
        for step, degree in enumerate(phrase):
            # A short answer at each phrase ending keeps the loop from feeling static.
            if bar % 4 == 3 and step >= 6:
                degree = (1, None)[step - 6]
            if degree is not None:
                note(root + degree, bar * 4 + step * 0.5, 0.40, "lead", 0.18)
        for beat_index in range(4):
            note(root - 14 + (4 if beat_index % 2 else 0), bar * 4 + beat_index, 0.82, "bass", 0.20)
            note(root - 7 + (0, 2, 4, 2)[beat_index], bar * 4 + beat_index + 0.5, 0.36, "arp", 0.09)
            add(drums["kick" if beat_index % 2 == 0 else "snare"], bar * 4 + beat_index, 0.11)
            add(drums["hat"], bar * 4 + beat_index, 0.035)
            add(drums["hat"], bar * 4 + beat_index + 0.5, 0.024)
    peak = max(abs(sample) for sample in mix) or 1
    gain = 0.55 * 32767 / peak
    return array("h", (int(sample * gain) for sample in mix))


def additional_effects():
    """Short, distinct game cues with quieter repeated actions."""
    effects = {
        "menu_back": generate_arpeggio([660, 440], 0.055, 0.20),
        "start": generate_arpeggio([392, 523, 659, 784], 0.065, 0.28),
        "pause": generate_arpeggio([523, 392], 0.065, 0.19),
        "resume": generate_arpeggio([392, 523], 0.065, 0.19),
        "pellet": generate_chirp(620, 410, 0.045, 0.13),
        "powerup": generate_arpeggio([262, 330, 392, 523, 659, 784], 0.055, 0.28),
        "shot": generate_chirp(980, 180, 0.065, 0.18),
        "hit": generate_noise_burst(0.065, 0.21) + generate_tone(180, 0.045, 0.14),
        "rock": generate_noise_burst(0.075, 0.19) + generate_chirp(150, 65, 0.13, 0.23),
        "turn": generate_chirp(290, 210, 0.035, 0.10),
        "achievement": generate_arpeggio([523, 659, 784, 1047, 784, 1047], 0.085, 0.30),
    }
    for name, samples in effects.items():
        save_wav(name + ".wav", samples)


def main():
    """Generate all required sound effects."""
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    _rng.seed(20261114)

    print("Generating sound effects for Winston Entertainment System...")
    print()

    # Menu move - soft click/chirp
    samples = generate_chirp(800, 400, 0.05, volume=0.3)
    save_wav("menu_move.wav", samples)

    # Menu select - confirmation beep (two-tone)
    samples1 = generate_blip(880, 0.08, volume=0.4)
    samples2 = generate_blip(1320, 0.12, volume=0.4)
    save_wav("menu_select.wav", samples1 + samples2)

    # Collect - positive chime (ascending arpeggio)
    samples = generate_arpeggio([523, 659, 784], 0.06, volume=0.35)
    save_wav("collect.wav", samples)

    # Death - negative sound (descending tones)
    samples = generate_chirp(440, 110, 0.3, volume=0.4)
    # Add noise at the end
    samples += generate_noise_burst(0.1, volume=0.2)
    save_wav("death.wav", samples)

    # Victory - celebration jingle
    # C-E-G-C (octave higher) arpeggio
    samples = generate_arpeggio([523, 659, 784, 1047], 0.1, volume=0.4)
    # Add a final sustained note
    samples += generate_tone(1047, 0.3, volume=0.3)
    save_wav("victory.wav", samples)

    # Jump - bounce sound (quick upward chirp)
    samples = generate_chirp(200, 600, 0.1, volume=0.35)
    save_wav("jump.wav", samples)

    # Dig - digging sound (noise + low tone)
    samples1 = generate_noise_burst(0.1, volume=0.3)
    samples2 = generate_tone(150, 0.1, volume=0.25)
    # Mix them together
    samples = []
    for i in range(max(len(samples1), len(samples2))):
        s1 = samples1[i] if i < len(samples1) else 0
        s2 = samples2[i] if i < len(samples2) else 0
        # Clamp to 16-bit range
        combined = max(-32767, min(32767, s1 + s2))
        samples.append(combined)
    save_wav("dig.wav", samples)

    additional_effects()
    for name in THEMES:
        save_wav(name + "_theme.wav", compose_theme(name), sample_rate=MUSIC_RATE)

    print()
    print("All sound effects and seven original music themes generated successfully!")
    print("The game will now play sounds when navigating menus and playing games.")


if __name__ == "__main__":
    main()
