"""Auto-generates a basic Easy-difficulty Pocket Guitar chart from a raw WAV file.

Pipeline: pick the most energetic ~80s window (skip likely intro/outro),
trim it, detect a beat grid from the energy-onset envelope (autocorrelation),
place one note per beat on strong-enough beats (skip near-silent ones),
write the chart JSON, and convert the trimmed excerpt to a compact M4A.

This is intentionally a *basic* algorithmic chart (Easy only, energy-based
onsets, no pitch/melody analysis) - nowhere near the precision of the 3
hand-tuned existing songs. Flagged as such in catalog.json's source field.
"""
import audioop
import json
import math
import os
import subprocess
import wave

EXCERPT_S = 80.0
HOP_MS = 20  # envelope frame hop
WIN_MS = 40  # envelope frame window (for RMS)
TICKS_PER_BEAT = 4
BEATS_PER_BAR = 4
MIN_BPM = 70
MAX_BPM = 180
EASY_LANES = [3, 4, 5, 6]


def read_wav(path):
    w = wave.open(path, "rb")
    info = {
        "channels": w.getnchannels(),
        "rate": w.getframerate(),
        "sampwidth": w.getsampwidth(),
        "nframes": w.getnframes(),
    }
    data = w.readframes(info["nframes"])
    w.close()
    return info, data


def to_mono(data, info):
    if info["channels"] == 1:
        return data
    return audioop.tomono(data, info["sampwidth"], 0.5, 0.5)


def energy_envelope(mono, sampwidth, rate):
    """RMS per HOP_MS, using a WIN_MS window. Returns (envelope list, fps)."""
    hop_samples = int(rate * HOP_MS / 1000)
    win_samples = int(rate * WIN_MS / 1000)
    hop_bytes = hop_samples * sampwidth
    win_bytes = win_samples * sampwidth
    n = len(mono)
    env = []
    pos = 0
    while pos + win_bytes <= n:
        chunk = mono[pos:pos + win_bytes]
        env.append(audioop.rms(chunk, sampwidth))
        pos += hop_bytes
    fps = 1000.0 / HOP_MS
    return env, fps


def best_excerpt_window(env, fps, excerpt_s, total_s):
    """Slide an excerpt_s-wide window over the envelope, return (start_s, end_s)
    of the window with the highest total energy, avoiding the very start/end."""
    win_frames = int(excerpt_s * fps)
    if win_frames >= len(env):
        return 0.0, total_s
    # Precompute prefix sums for O(n) sliding window.
    prefix = [0] * (len(env) + 1)
    for i, v in enumerate(env):
        prefix[i + 1] = prefix[i] + v
    best_start = 0
    best_sum = -1
    # Skip first/last ~3s to dodge fade-ins/outros and silence.
    margin_frames = int(3 * fps)
    lo = margin_frames
    hi = max(lo, len(env) - win_frames - margin_frames)
    for start in range(lo, hi + 1, int(fps)):  # step ~1s for speed
        s = prefix[start + win_frames] - prefix[start]
        if s > best_sum:
            best_sum = s
            best_start = start
    start_s = best_start / fps
    return start_s, start_s + excerpt_s


def trim_wav(info, data, start_s, end_s, out_path):
    rate = info["rate"]
    sampwidth = info["sampwidth"]
    channels = info["channels"]
    frame_size = sampwidth * channels
    start_frame = int(start_s * rate)
    end_frame = min(info["nframes"], int(end_s * rate))
    start_byte = start_frame * frame_size
    end_byte = end_frame * frame_size
    trimmed = data[start_byte:end_byte]
    w = wave.open(out_path, "wb")
    w.setnchannels(channels)
    w.setsampwidth(sampwidth)
    w.setframerate(rate)
    w.writeframes(trimmed)
    w.close()
    return trimmed, (end_frame - start_frame) / rate


def onset_novelty(env):
    """Half-wave rectified first difference of a lightly smoothed envelope."""
    # 3-tap smoothing
    sm = []
    for i in range(len(env)):
        lo = max(0, i - 1)
        hi = min(len(env) - 1, i + 1)
        sm.append(sum(env[lo:hi + 1]) / (hi - lo + 1))
    nov = [0.0]
    for i in range(1, len(sm)):
        d = sm[i] - sm[i - 1]
        nov.append(d if d > 0 else 0.0)
    return nov


def estimate_bpm(nov, fps):
    """Autocorrelation of the novelty curve over the plausible BPM lag range."""
    min_lag = int(fps * 60.0 / MAX_BPM)
    max_lag = int(fps * 60.0 / MIN_BPM)
    n = len(nov)
    mean = sum(nov) / n
    centered = [x - mean for x in nov]
    best_lag = min_lag
    best_score = -1e18
    for lag in range(min_lag, min(max_lag, n - 1) + 1):
        score = 0.0
        for i in range(0, n - lag, 4):  # stride 4 for speed
            score += centered[i] * centered[i + lag]
        if score > best_score:
            best_score = score
            best_lag = lag
    period_s = best_lag / fps
    bpm = 60.0 / period_s
    return bpm, period_s


def best_phase(nov, fps, period_s, search_s=None):
    """Pick the grid start offset (0..period_s) that best lines up with onsets."""
    period_frames = period_s * fps
    steps = 40
    best_off = 0.0
    best_score = -1
    search_frames = len(nov) if search_s is None else int(search_s * fps)
    for k in range(steps):
        off = k / steps * period_frames
        score = 0.0
        beat = off
        while beat < search_frames:
            idx = int(round(beat))
            if idx < len(nov):
                score += nov[idx]
            beat += period_frames
        if score > best_score:
            best_score = score
            best_off = off
    return best_off / fps


def generate_easy_chart(env, fps, bpm, phase_s, excerpt_duration_s, song_id):
    beat_period_s = 60.0 / bpm
    beat_ms = beat_period_s * 1000.0
    # Silence gate uses raw loudness (env), not the onset-flux curve: flux is
    # near-zero almost everywhere by construction (it only spikes right at
    # attack transients), so gating placement on it rejects most genuinely
    # active beats. Loudness at the beat instant is what actually says
    # "is the song playing here" - flux is only used for BPM/phase above.
    avg_env = sum(env) / len(env) if env else 0.0
    silence_threshold = avg_env * 0.15

    notes = []
    beat_index = 0
    lane_cursor = 0
    placed = 0
    t = phase_s
    while t < excerpt_duration_s - beat_period_s:  # leave room for the final bar
        idx = int(round(t * fps))
        loudness = env[idx] if 0 <= idx < len(env) else 0.0
        on_cadence = beat_index % 2 == 0
        # Charting rule: first note in bar 2 or later (skip first 2 bars).
        if beat_index >= BEATS_PER_BAR * 2 and on_cadence and loudness >= silence_threshold:
            tick = beat_index * TICKS_PER_BEAT
            lane = EASY_LANES[lane_cursor % len(EASY_LANES)]
            lane_cursor += 1
            # Every 4th placed note is a 2-lane chord (Easy allows up to 2 frets).
            if placed % 4 == 3 and lane + 1 <= EASY_LANES[-1]:
                lanes = [lane, lane + 1]
            else:
                lanes = [lane]
            notes.append([tick, lanes, "A", 0])
            placed += 1
        beat_index += 1
        t += beat_period_s

    # Charting rule: end on a strong chord.
    if notes:
        last_tick = notes[-1][0]
        notes[-1] = [last_tick, [4, 5, 6], "A", 0]

    return {
        "id": song_id,
        "beats_per_bar": BEATS_PER_BAR,
        "ticks_per_beat": TICKS_PER_BEAT,
        "notes": notes,
        "beat_ms": beat_ms,
        "num_beats": beat_index,
    }


def convert_to_m4a(wav_path, m4a_path, bitrate=128000):
    subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", str(bitrate), wav_path, m4a_path],
        check=True,
        capture_output=True,
    )


def process(wav_path, song_id, title, artist, out_dir_songs, out_dir_audio):
    print(f"=== {song_id} ({wav_path}) ===")
    info, data = read_wav(wav_path)
    total_s = info["nframes"] / info["rate"]
    print(f"source duration: {total_s:.1f}s, {info['rate']}Hz, {info['channels']}ch")

    mono = to_mono(data, info)
    env, fps = energy_envelope(mono, info["sampwidth"], info["rate"])
    print(f"envelope frames: {len(env)} at {fps} fps")

    start_s, end_s = best_excerpt_window(env, fps, EXCERPT_S, total_s)
    print(f"chosen excerpt: {start_s:.1f}s - {end_s:.1f}s")

    trimmed_wav = f"/tmp/{song_id}_excerpt.wav"
    trimmed_data, excerpt_duration_s = trim_wav(info, data, start_s, end_s, trimmed_wav)
    print(f"trimmed duration: {excerpt_duration_s:.1f}s")

    excerpt_mono = to_mono(trimmed_data, info)
    excerpt_env, excerpt_fps = energy_envelope(excerpt_mono, info["sampwidth"], info["rate"])
    nov = onset_novelty(excerpt_env)

    bpm, period_s = estimate_bpm(nov, excerpt_fps)
    print(f"estimated bpm: {bpm:.1f}")

    phase_s = best_phase(nov, excerpt_fps, period_s, search_s=min(20.0, excerpt_duration_s))
    print(f"grid phase offset: {phase_s * 1000:.0f}ms")

    chart = generate_easy_chart(excerpt_env, excerpt_fps, bpm, phase_s, excerpt_duration_s, song_id)
    print(f"notes placed: {len(chart['notes'])} over {chart['num_beats']} beats")

    m4a_path = os.path.join(out_dir_audio, f"{song_id}.m4a")
    convert_to_m4a(trimmed_wav, m4a_path)
    m4a_size = os.path.getsize(m4a_path)
    print(f"m4a written: {m4a_path} ({m4a_size / 1024:.0f} KB)")

    song_json = {
        "id": song_id,
        "title": title,
        "artist": artist,
        "bpm": round(bpm, 1),
        "beats_per_bar": BEATS_PER_BAR,
        "ticks_per_beat": TICKS_PER_BEAT,
        "charts": {"easy": {"notes": chart["notes"]}},
    }
    song_path = os.path.join(out_dir_songs, f"{song_id}.json")
    with open(song_path, "w") as f:
        json.dump(song_json, f, indent=2)
    print(f"chart written: {song_path}")

    last_tick = chart["notes"][-1][0] if chart["notes"] else 0
    length_ms = int((last_tick / TICKS_PER_BEAT + BEATS_PER_BAR) * chart["beat_ms"])

    return {
        "id": song_id,
        "title": title,
        "artist": artist,
        "bpm": round(bpm, 1),
        "chart": f"assets/pocket_guitar/songs/{song_id}.json",
        "audio": f"assets/pocket_guitar/audio/{song_id}.m4a",
        "length_ms": length_ms,
        "source": {
            "file": os.path.basename(wav_path),
            "excerpt_start_s": round(start_s, 2),
            "excerpt_end_s": round(end_s, 2),
            "silent_lead_in_bars": 0,
            "time_warped_to_constant_bpm": False,
            "chart_generated": "auto (energy-onset detection, Easy only, no pitch/melody analysis - not hand-tuned)",
        },
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a basic auto-charted Easy-only Pocket Guitar song from a WAV "
        "file: picks the most energetic ~80s excerpt, detects a beat grid, places notes on a "
        "steady every-2-beats cadence (skipping genuine silence), and converts the excerpt to "
        "a compact M4A. This is NOT a substitute for a hand-tuned chart - it has no pitch or "
        "melody analysis, and only produces an Easy difficulty. Prints a catalog.json entry "
        "to append by hand (or with --catalog) after checking the result plays sensibly."
    )
    parser.add_argument("wav_path", help="Source WAV file (16-bit PCM)")
    parser.add_argument("song_id", help="Short id, e.g. 'my_song' - used for output filenames")
    parser.add_argument("title", help="Display title")
    parser.add_argument("artist", help="Display artist")
    parser.add_argument(
        "--songs-dir", default="assets/pocket_guitar/songs",
        help="Where to write <song_id>.json (default: assets/pocket_guitar/songs)",
    )
    parser.add_argument(
        "--audio-dir", default="assets/pocket_guitar/audio",
        help="Where to write <song_id>.m4a (default: assets/pocket_guitar/audio)",
    )
    parser.add_argument(
        "--catalog", default=None,
        help="If given, append the new entry directly into this catalog.json instead of just printing it",
    )
    args = parser.parse_args()

    os.makedirs(args.songs_dir, exist_ok=True)
    os.makedirs(args.audio_dir, exist_ok=True)
    entry = process(
        args.wav_path, args.song_id, args.title, args.artist,
        args.songs_dir, args.audio_dir,
    )

    print("\ncatalog.json entry:")
    print(json.dumps(entry, indent=2))

    if args.catalog:
        with open(args.catalog) as f:
            catalog = json.load(f)
        catalog["songs"].append(entry)
        with open(args.catalog, "w") as f:
            json.dump(catalog, f, indent=2)
        print(f"\nAppended to {args.catalog}")
    else:
        print("\nNot written to a catalog - pass --catalog assets/pocket_guitar/catalog.json to append it there.")

    print(
        "\nReminder: this chart is algorithmically generated (energy-onset detection, no "
        "pitch/melody analysis) - listen through it before shipping. For real quality, chart "
        "by hand against the actual riff/melody per RaspberryMicroPython/game/pocketGuitar/"
        "GAME_DESIGN.md section 12."
    )


if __name__ == "__main__":
    main()
