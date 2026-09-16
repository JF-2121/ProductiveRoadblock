"""Pocket Guitar song files: loading, musical time and score limits.

A song file is JSON (see game/pocketGuitar/songs/). Lanes are numbered 0-6. Musical positions are given in
ticks (4 ticks per beat by default) and converted to milliseconds once at load time,
so the game loop only works with integers.
"""
import json
import os
from array import array

STRUM_ANY = 0   # white note, either strum key (Easy)
STRUM_RED = 1   # bit per strum key, so "both" is RED | BLUE
STRUM_BLUE = 2
STRUM_BOTH = 3
_STRUM_CODES = {"A": STRUM_ANY, "R": STRUM_RED, "B": STRUM_BLUE, "P": STRUM_BOTH}
STRUM_NAMES = ("any", "red", "blue", "purple")

DIFFICULTIES = ("easy", "medium", "hard", "expert")
DIFFICULTY_EASY = 0

# (perfect_ms, good_ms) per difficulty, see GAME_DESIGN.md section 7
_DEFAULT_TIMING = ((70, 130), (60, 115), (50, 100), (45, 90))
# Default row length as a fraction of a beat per difficulty: 1, 1/2, 1/2, 1/4
_DEFAULT_ROWS_PER_BEAT = (1, 2, 2, 4)

NUM_LANES = 7  # the 8th column of the board shows feedback
POINTS_PER_FRET = 50
SUSTAIN_POINTS_PER_BEAT = 25
STREAK_PER_MULTIPLIER = 10
MAX_MULTIPLIER = 4

# bpm is stored as bpm * 10, so 1 beat = _MS_PER_MINUTE_X10 / bpm_x10 ms
_MS_PER_MINUTE_X10 = 600000


def popcount(value):
    count = 0
    while value:
        value &= value - 1
        count += 1
    return count


def multiplier_for(streak):
    return min(MAX_MULTIPLIER, 1 + streak // STREAK_PER_MULTIPLIER)


def lanes_to_mask(frets):
    """Accept a lane list like [4, 6] or a ready bit mask (bit 0 = lane 0)."""
    if isinstance(frets, int):
        return frets & ((1 << NUM_LANES) - 1)
    mask = 0
    for lane in frets:
        if 0 <= lane < NUM_LANES:
            mask |= 1 << lane
    return mask


def mask_to_lanes(mask):
    return ",".join(str(lane) for lane in range(NUM_LANES) if mask & (1 << lane)) or "-"


class Chart:
    """The notes of one difficulty, as parallel arrays sorted by time."""

    __slots__ = (
        "difficulty",
        "times",      # array('i'): note time in song ms
        "ends",       # array('i'): sustain end in song ms (== time for normal notes)
        "frets",      # bytearray: lane bit mask
        "strums",     # bytearray: STRUM_* code
        "row_ms",
        "perfect_ms",
        "good_ms",
        "position_times",  # array('i'): hand position changes in song ms
        "position_masks",  # bytearray: lanes of the 4-finger window
        "max_score",
    )

    def __len__(self):
        return len(self.times)


class Song:
    __slots__ = (
        "path",
        "song_id",
        "title",
        "artist",
        "bpm_x10",
        "beats_per_bar",
        "ticks_per_beat",
        "beat_ms",
        "bar_ms",
        "length_ms",
        "charts",  # list indexed by difficulty, None where the song has no chart
    )

    def tick_to_ms(self, tick):
        den = self.bpm_x10 * self.ticks_per_beat
        return (tick * _MS_PER_MINUTE_X10 + den // 2) // den

    def beat_time_ms(self, beat_index):
        return (beat_index * _MS_PER_MINUTE_X10 + self.bpm_x10 // 2) // self.bpm_x10

    def first_beat_at_or_after(self, ms):
        """Index of the first beat whose time is >= ms (ms may be negative)."""
        return -((-ms * self.bpm_x10) // _MS_PER_MINUTE_X10)

    def beat_index_at(self, ms):
        return (ms * self.bpm_x10) // _MS_PER_MINUTE_X10

    def sustain_points(self, held_ms):
        return held_ms * SUSTAIN_POINTS_PER_BEAT * self.bpm_x10 // _MS_PER_MINUTE_X10

    def available_difficulties(self):
        return [d for d in range(len(DIFFICULTIES)) if self.charts[d] is not None]

    def chart(self, difficulty):
        return self.charts[difficulty] if 0 <= difficulty < len(self.charts) else None


def list_song_files(folder):
    try:
        names = [n for n in os.listdir(folder) if n.endswith(".json")]
    except OSError:
        return []
    names.sort()
    return [folder + "/" + n for n in names]


def load_song(path):
    with open(path, "r") as f:
        data = json.load(f)
    return load_song_data(data, path)


def load_song_data(data, path):
    """Build a Song from parsed song JSON (a file, or a song sent by the app). path is only a name."""
    song = Song()
    song.path = path
    song.song_id = data.get("id", path)
    song.title = data.get("title", song.song_id)
    song.artist = data.get("artist", "")
    song.bpm_x10 = int(data["bpm"] * 10 + 0.5)
    song.beats_per_bar = data.get("beats_per_bar", 4)
    song.ticks_per_beat = data.get("ticks_per_beat", 4)
    song.beat_ms = song.beat_time_ms(1)
    song.bar_ms = song.beat_time_ms(song.beats_per_bar)
    song.charts = [None] * len(DIFFICULTIES)

    last_end = 0
    charts_data = data.get("charts", {})
    for difficulty, name in enumerate(DIFFICULTIES):
        chart_data = charts_data.get(name)
        if not chart_data:
            continue
        chart = _build_chart(song, difficulty, chart_data)
        song.charts[difficulty] = chart
        if len(chart):
            last_end = max(last_end, max(chart.ends))

    song.length_ms = last_end + song.bar_ms
    for chart in song.charts:
        if chart is not None:
            chart.max_score = _max_score(song, chart)
    return song


def _build_chart(song, difficulty, chart_data):
    notes = chart_data.get("notes", [])
    notes.sort(key=lambda n: n[0])
    count = len(notes)

    chart = Chart()
    chart.difficulty = difficulty
    chart.times = array("i", [0] * count)
    chart.ends = array("i", [0] * count)
    chart.frets = bytearray(count)
    chart.strums = bytearray(count)
    for i, note in enumerate(notes):
        tick = note[0]
        length = note[3] if len(note) > 3 else 0
        chart.times[i] = song.tick_to_ms(tick)
        chart.ends[i] = song.tick_to_ms(tick + length)
        chart.frets[i] = lanes_to_mask(note[1])
        strum = note[2] if len(note) > 2 else "A"
        chart.strums[i] = _STRUM_CODES.get(strum, STRUM_ANY) if isinstance(strum, str) else strum & 3

    default_row_ticks = max(1, song.ticks_per_beat // _DEFAULT_ROWS_PER_BEAT[difficulty])
    chart.row_ms = max(1, song.tick_to_ms(chart_data.get("row_ticks", default_row_ticks)))

    timing = chart_data.get("timing", {})
    chart.perfect_ms = timing.get("perfect_ms", _DEFAULT_TIMING[difficulty][0])
    chart.good_ms = timing.get("good_ms", _DEFAULT_TIMING[difficulty][1])

    positions = chart_data.get("positions", [])
    positions.sort(key=lambda p: p[0])
    chart.position_times = array("i", [song.tick_to_ms(p[0]) for p in positions])
    chart.position_masks = bytearray([(0x0F << p[1]) & ((1 << NUM_LANES) - 1) for p in positions])
    chart.max_score = 0
    return chart


def _max_score(song, chart):
    """Score for every note Perfect and every sustain held to the end."""
    score = 0
    streak = 0
    for i in range(len(chart)):
        streak += 1
        multiplier = multiplier_for(streak)
        points = POINTS_PER_FRET * popcount(chart.frets[i])
        points += song.sustain_points(chart.ends[i] - chart.times[i])
        score += points * multiplier
    return score
