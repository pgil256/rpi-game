#!/usr/bin/env python3
"""
Generate simple retro-style sound effects for the Weasel Entertainment System.
Run this script once to create all the required sound files.
"""

import wave
import struct
import math
import os

# Sound output directory
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')

# Audio parameters
SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


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
        freq = start_freq + (end_freq - start_freq) * progress

        # Calculate phase (integral of frequency)
        phase = 2 * math.pi * (start_freq * t + 0.5 * (end_freq - start_freq) * t * t / duration)
        value = math.sin(phase)

        # Fade out
        fade_factor = 1.0 - progress ** 2
        value *= fade_factor

        sample = int(value * volume * 32767)
        samples.append(sample)

    return samples


def generate_noise_burst(duration, volume=0.3):
    """Generate a short noise burst with decay."""
    import random
    num_samples = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(num_samples):
        progress = i / num_samples
        # White noise with exponential decay
        value = random.uniform(-1, 1) * math.exp(-5 * progress)
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
        value *= (1.0 - progress ** 0.5)

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
            value *= (1.0 - progress ** 2)

            sample = int(value * volume * 32767)
            samples.append(sample)

    return samples


def save_wav(filename, samples):
    """Save samples to a WAV file."""
    filepath = os.path.join(SOUNDS_DIR, filename)

    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)

        # Pack samples as signed 16-bit integers
        packed_samples = struct.pack('<' + 'h' * len(samples), *samples)
        wav_file.writeframes(packed_samples)

    print(f"Created: {filepath}")


def main():
    """Generate all required sound effects."""
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    print("Generating sound effects for Weasel Entertainment System...")
    print()

    # Menu move - soft click/chirp
    samples = generate_chirp(800, 400, 0.05, volume=0.3)
    save_wav('menu_move.wav', samples)

    # Menu select - confirmation beep (two-tone)
    samples1 = generate_blip(880, 0.08, volume=0.4)
    samples2 = generate_blip(1320, 0.12, volume=0.4)
    save_wav('menu_select.wav', samples1 + samples2)

    # Collect - positive chime (ascending arpeggio)
    samples = generate_arpeggio([523, 659, 784], 0.06, volume=0.35)
    save_wav('collect.wav', samples)

    # Death - negative sound (descending tones)
    samples = generate_chirp(440, 110, 0.3, volume=0.4)
    # Add noise at the end
    samples += generate_noise_burst(0.1, volume=0.2)
    save_wav('death.wav', samples)

    # Victory - celebration jingle
    # C-E-G-C (octave higher) arpeggio
    samples = generate_arpeggio([523, 659, 784, 1047], 0.1, volume=0.4)
    # Add a final sustained note
    samples += generate_tone(1047, 0.3, volume=0.3)
    save_wav('victory.wav', samples)

    # Jump - bounce sound (quick upward chirp)
    samples = generate_chirp(200, 600, 0.1, volume=0.35)
    save_wav('jump.wav', samples)

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
    save_wav('dig.wav', samples)

    print()
    print("All sound effects generated successfully!")
    print("The game will now play sounds when navigating menus and playing games.")


if __name__ == '__main__':
    main()
