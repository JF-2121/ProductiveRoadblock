"""Synthesizes short piano-like plucked tones (no external audio sourcing -
avoids any licensing/provenance question for bundled classical recordings).

Additive synthesis: fundamental + 2 harmonics, each with its own decay rate
(higher harmonics fade faster, which is what makes a struck/plucked tone
read as "piano-ish" rather than a pure organ-like sine). Short fast attack,
exponential decay - snappy enough for rapid tile-tapping, not a sustained
ring.
"""
import math
import struct
import wave

RATE = 44100
DURATION_S = 0.5
ATTACK_S = 0.004


def synth_note(freq_hz, duration_s=DURATION_S, out_path=None):
    n = int(RATE * duration_s)
    attack_n = int(RATE * ATTACK_S)
    samples = []
    # (harmonic multiple, relative amplitude, decay time constant in seconds)
    partials = [
        (1.0, 1.00, 0.35),
        (2.0, 0.45, 0.18),
        (3.0, 0.20, 0.10),
        (4.0, 0.08, 0.07),
    ]
    peak = 0.0
    raw = []
    for i in range(n):
        t = i / RATE
        value = 0.0
        for mult, amp, tau in partials:
            value += amp * math.sin(2 * math.pi * freq_hz * mult * t) * math.exp(-t / tau)
        if i < attack_n:
            value *= i / attack_n
        raw.append(value)
        peak = max(peak, abs(value))

    scale = 0.6 / peak if peak > 0 else 1.0
    for v in raw:
        clamped = max(-1.0, min(1.0, v * scale))
        samples.append(int(clamped * 32767))

    if out_path:
        w = wave.open(out_path, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        w.close()
    return samples


if __name__ == "__main__":
    import os

    out_dir = "/Users/jfmacflatex/Desktop/apps/mobile-app/assets/sounds"
    os.makedirs(out_dir, exist_ok=True)
    # C major arpeggio, one note per Piano Tiles lane (0-3), ascending left to right.
    notes = {
        "piano_c4": 261.63,
        "piano_e4": 329.63,
        "piano_g4": 392.00,
        "piano_c5": 523.25,
    }
    for name, freq in notes.items():
        path = os.path.join(out_dir, f"{name}.wav")
        synth_note(freq, out_path=path)
        size = os.path.getsize(path)
        print(f"{name}: {freq} Hz -> {path} ({size} bytes)")
