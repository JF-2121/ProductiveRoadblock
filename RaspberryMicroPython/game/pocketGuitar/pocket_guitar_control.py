"""Pocket Guitar: a Guitar Hero style rhythm game for the 4x8 pad (see GAME_DESIGN.md).

Board: 7 columns are the frets (any key in a column holds that fret), the 8th column shows
hit/miss feedback and the streak. Notes scroll towards the hit row next to the fretting
fingers (see POCKET_GUITAR_HIT_ROW / POCKET_GUITAR_FEEDBACK_COLUMN in pico_config.py).
Keys 32 (blue) and 33 (red) are the strum keys.

Input events are only queued by the keyboard callback and processed in the game loop,
in order and with the time they were detected, so judgement does not depend on when
the loop gets to run.

BLE events (integers little-endian):
  SONG_START      song slot u8, difficulty u8, mode u8, bpm*10 u16, start position ms i32, delay offset ms i16
  NOTE_RESULT     note index u16, grade u8 (1 perfect, 2 good, 3 almost, 4 miss), multiplier u8, score u32
  OVERSTRUM       score u32
  SUSTAIN_END     note index u16, held percent u8
  SONG_RESULT     score u32, stars u8, accuracy percent u8, best streak u16, flags u8 (bit 0 new best, bit 1 flawless)
  SONG_SELECTION  song slot u8, song count u8, difficulty u8, available difficulties u8 (bit per difficulty),
                  mode u8, best stars u8, best score u32

A song sent by the app (BLE stream message POCKET_GUITAR_SONG) is selected as song slot APP_SONG_SLOT.
"""
import gc
import json
import sys
import time
from array import array
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import globals
import pico_config as config
from ble_handler.config import (
    BLE_EVENT_ID_SONG_START, BLE_EVENT_ID_NOTE_RESULT, BLE_EVENT_ID_OVERSTRUM,
    BLE_EVENT_ID_SUSTAIN_END, BLE_EVENT_ID_SONG_RESULT, BLE_EVENT_ID_SONG_SELECTION,
)
from game.game_control import GameControl
from game.utils import GameConfig, GameState
from game.pocketGuitar import song as songs
from game.pocketGuitar.song import (
    STRUM_ANY, STRUM_RED, STRUM_BLUE, STRUM_BOTH, STRUM_NAMES, DIFFICULTIES, DIFFICULTY_EASY,
    NUM_LANES, POINTS_PER_FRET, STREAK_PER_MULTIPLIER, popcount, multiplier_for, mask_to_lanes,
)
from game.haptic_player import (
    HapticPlayer, PRIORITY_TICK, PRIORITY_ALMOST, PRIORITY_ACCENT, PRIORITY_MULTIPLIER,
    PRIORITY_MISS, PRIORITY_SYSTEM,
)
from game.pocketGuitar.records import Records

DEFAULT_SONGS_FOLDER = "game/pocketGuitar/songs"
DEFAULT_RECORDS_PATH = "pocket_guitar_records.json"
APP_SONG_SLOT = 0xFF  # song slot of a song sent by the app, see load_song_json()

LOG_OFF = 0
LOG_INFO = 1   # state changes, every judged note, results
LOG_DEBUG = 2  # additionally every key event and BLE event

MODE_PLAY = 0
MODE_PRACTICE = 1
_MODE_NAMES = ("Play", "Practice")

PHASE_SELECT = 0
PHASE_COUNT_IN = 1
PHASE_PLAY = 2
PHASE_PAUSED = 3
PHASE_RESULT = 4

NOTE_PENDING = 0
NOTE_PERFECT = 1
NOTE_GOOD = 2
NOTE_ALMOST = 3
NOTE_MISS = 4
NOTE_CLAIMED = 5   # a strum is being evaluated for this note
_COUNT_OVERSTRUM = 5
_GRADE_NAMES = ("", "PERFECT", "GOOD", "ALMOST", "MISS")
_GRADE_PERCENT = (0, 100, 80, 50, 0)

LOOP_INTERVAL_MS = 5
RENDER_INTERVAL_MS = 15
STATS_LOG_INTERVAL_MS = 5000    # how often stats_line() (loop gap, input overflows, free mem) prints during play
STRUM_WINDOW_MS = 40            # second strum key for purple notes, and fret grace
PAUSE_HOLD_MS = config.BACK_HOLD_MS
SUSTAIN_RELEASE_GRACE_MS = 30
FEEDBACK_FLASH_MS = 150
FEEDBACK_MISS_MS = 250
MISS_BUZZ_MS = 70
RESULT_INPUT_LOCK_MS = 1500
RESULT_STAR_STEP_MS = 300
RESULT_CELEBRATION_MS = 3000
STAR_THRESHOLDS = (0, 40, 60, 80, 95)  # percent of max score for 1..5 stars

# DRV2605L library effects, see GAME_DESIGN.md section 9
_FX_ACCENT = 1          # Strong Click 100 %
_FX_GESTURE = 7         # Soft Bump 100 %
_FX_ALMOST = 9          # Soft Bump 30 %
_FX_MULTIPLIER = 10     # Double Click 100 %
_FX_RESULT = 12         # Triple Click 100 %
_FX_COUNT_IN_FIRST = 24  # Sharp Tick 1 100 %
_FX_COUNT_IN = 25       # Sharp Tick 2 80 %
_FX_BEAT = 26           # Sharp Tick 3 60 %
_FX_MISS = 49           # Buzz 3 60 %
_FX_NEW_BEST = 82       # Transition Ramp Up Long Smooth 1

_WHITE_NOTE = (180, 180, 180)
_NOTE_COLORS = (_WHITE_NOTE, config.COLOR_STRUM_RED, config.COLOR_STRUM_BLUE, config.COLOR_STRUM_BOTH)
_NOTE_HALF_COLORS = tuple((c[0] // 2, c[1] // 2, c[2] // 2) for c in _NOTE_COLORS)
_TAIL_COLORS = tuple((c[0] // 4, c[1] // 4, c[2] // 4) for c in _NOTE_COLORS)
_HIT_FLASH = (0, 255, 0)
_ALMOST_FLASH = (255, 120, 0)
_MISS_FLASH = (255, 0, 0)
# Feedback column between flashes: streak meter, one colour per multiplier (x1..x4)
_STREAK_COLORS = ((0, 40, 0), (0, 160, 160), (200, 160, 0), (255, 255, 255))
_BEAT_LINE = (6, 6, 6)
_POSITION_GLOW = (0, 8, 8)
_COUNT_IN_COLOR = (40, 40, 40)
_DIFFICULTY_COLORS = ((0, 255, 0), (255, 200, 0), (255, 90, 0), (255, 0, 0))
_DIFFICULTY_DIM_COLORS = tuple((c[0] // 10, c[1] // 10, c[2] // 10) for c in _DIFFICULTY_COLORS)
_SONG_COLOR = (200, 200, 200)
_SONG_DIM_COLOR = (12, 12, 12)
_STAR_COLOR = (255, 140, 0)
_BEST_STAR_COLOR = (60, 32, 0)
_SELECT_PULSE = ((20, 0, 20), (60, 0, 60), (120, 0, 120), (60, 0, 60))
_RAINBOW = ((255, 0, 0), (255, 120, 0), (255, 255, 0), (0, 255, 0),
            (0, 255, 255), (0, 0, 255), (140, 0, 255), (255, 0, 160))

_QUEUE_SIZE = 32
_ROWS = config.GRID_NUM_ROWS
_COLS = config.GRID_NUM_COLS
_ALL_LANES = (1 << NUM_LANES) - 1

# Layout as in GAME_DESIGN.md: notes scroll from row 0 towards the hit row 3, column 0 shows
# feedback. _PHYSICAL_KEY mirrors this onto the real board (pico_config POCKET_GUITAR_FLIP_*);
# it is its own inverse, so it also maps pressed pads back to layout keys.
_HIT_ROW = _ROWS - 1
_FAR_DISTANCE = _ROWS - 1
_ROW_AT_DISTANCE = tuple(d if _HIT_ROW == 0 else _ROWS - 1 - d for d in range(_ROWS))
_FEEDBACK_COLUMN = 0
_PHYSICAL_KEY = tuple(
    ((_ROWS - 1 - key // _COLS) if config.POCKET_GUITAR_FLIP_ROWS else key // _COLS) * _COLS
    + ((_COLS - 1 - key % _COLS) if config.POCKET_GUITAR_FLIP_COLUMNS else key % _COLS)
    for key in range(_ROWS * _COLS))
_LANE_COLUMN = tuple(lane if lane < _FEEDBACK_COLUMN else lane + 1 for lane in range(NUM_LANES))
_COLUMN_LANE = tuple(-1 if c == _FEEDBACK_COLUMN else (c if c < _FEEDBACK_COLUMN else c - 1) for c in range(_COLS))


def _u16(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _u32(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF))


class PocketGuitarControl(GameControl):
    """Guitar Hero style rhythm game: select screen, count-in, song, pause, result."""

    __slots__ = [
        # settings (public, may be changed before or between songs)
        "delay_offset_ms",
        "beat_lines",
        "beat_tick",
        "sustain_hum",
        "log_level",
        # songs and selection
        "_song_files",
        "_song_slot",
        "_song",
        "_difficulty",
        "_mode",
        "_records",
        "_haptics",
        # opened from the start screen: start at once, go back there afterwards
        "_start_mode_on_open",
        "_exit_to_start_screen",
        "_leaving",
        # input queue filled by the keyboard callback
        "_queue_key",
        "_queue_action",
        "_queue_time",
        "_queue_head",
        "_queue_tail",
        "_queue_overflows",
        "_on_key_event_ref",
        # input state
        "_key_down",
        "_lane_count",
        "_frets",
        "_strum_down",
        "_hold_active",
        "_hold_start",
        "_hold_fired",
        "_paused_strum",
        "_select_strum",
        # rendering
        "_frame",
        "_blank",
        "_dirty",
        "_last_render",
        "_feedback_until",
        "_feedback_color",
        # phase
        "_phase",
        "_phase_start",
        # current run
        "_chart",
        "_note_state",
        "_t0",
        "_first_open",
        "_last_beat",
        "_preroll_until",
        "_pause_ms",
        "_waiting",
        "_wait_ms",
        "_score",
        "_streak",
        "_best_streak",
        "_counts",
        # strum being evaluated
        "_ps_active",
        "_ps_time",
        "_ps_deadline",
        "_ps_mask",
        "_ps_note",
        "_ps_fret_err",
        # sustain being held
        "_sustain_note",
        "_sustain_grade",
        "_sustain_mult",
        "_sustain_released",
        "_sustain_release_time",
        "_sustain_release_ms",
        # result
        "_result_stars",
        "_result_shown",
        "_result_new_best",
        "_result_flawless",
        # stats for the test script
        "max_loop_gap_ms",
        "renders",
        "_next_stats_ms",
    ]

    def __init__(self, game_config: GameConfig = None, game_state: GameState = None,
                 songs_folder=DEFAULT_SONGS_FOLDER, records_path=DEFAULT_RECORDS_PATH):
        super().__init__(game_config or GameConfig(game_id=config.GAME_ID_POCKET_GUITAR), game_state)
        self.delay_offset_ms = 0
        self.beat_lines = True
        self.beat_tick = False
        self.sustain_hum = True
        self.log_level = LOG_INFO

        self._song_files = songs.list_song_files(songs_folder)
        self._song_slot = 0
        self._song = None
        self._difficulty = 0
        self._mode = MODE_PLAY
        self._records = Records(records_path)
        self._haptics = HapticPlayer(globals.haptic)
        self._start_mode_on_open = -1
        self._exit_to_start_screen = False
        self._leaving = False

        self._queue_key = bytearray(_QUEUE_SIZE)
        self._queue_action = bytearray(_QUEUE_SIZE)
        self._queue_time = array("i", [0] * _QUEUE_SIZE)
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_overflows = 0
        self._on_key_event_ref = self._on_key_event

        self._key_down = bytearray(config.GRID_NUM_KEYS)
        self._lane_count = bytearray(NUM_LANES)
        self._frets = 0
        self._strum_down = 0
        self._hold_active = False
        self._hold_start = 0
        self._hold_fired = False
        self._paused_strum = False
        self._select_strum = 0

        self._frame = bytearray(config.GRID_NUM_KEYS * 3)
        self._blank = bytearray(config.GRID_NUM_KEYS * 3)
        self._dirty = True
        self._last_render = 0
        self._feedback_until = 0
        self._feedback_color = None

        self._phase = PHASE_SELECT
        self._phase_start = 0

        self._chart = None
        self._note_state = bytearray(0)
        self._t0 = 0
        self._first_open = 0
        self._last_beat = 0
        self._preroll_until = 0
        self._pause_ms = 0
        self._waiting = False
        self._wait_ms = 0
        self._score = 0
        self._streak = 0
        self._best_streak = 0
        self._counts = [0] * 6

        self._ps_active = False
        self._ps_time = 0
        self._ps_deadline = 0
        self._ps_mask = 0
        self._ps_note = -1
        self._ps_fret_err = 0

        self._sustain_note = -1
        self._sustain_grade = 0
        self._sustain_mult = 1
        self._sustain_released = False
        self._sustain_release_time = 0
        self._sustain_release_ms = 0

        self._result_stars = 0
        self._result_shown = 0
        self._result_new_best = False
        self._result_flawless = False

        self.max_loop_gap_ms = 0
        self.renders = 0
        self._next_stats_ms = time.ticks_add(time.ticks_ms(), STATS_LOG_INTERVAL_MS)

    # ==========================================================================
    # GameControl interface
    # ==========================================================================
    def load_game_config(self, game_config: GameConfig) -> None:
        """Scan the songs, show the select screen (or start the song, see start_on_open()) and start the game loop."""
        self._config = game_config
        self._state = GameState()
        if globals.keyboard:
            globals.keyboard.set_key_event_callback(self._on_key_event_ref)
        if self._song_slot != APP_SONG_SLOT or self._song is None:
            self._select_song(self._song_slot)
        now = time.ticks_ms()
        mode = self._start_mode_on_open
        self._start_mode_on_open = -1
        if mode >= 0:
            self._start_run(now, mode)
            if self._phase == PHASE_SELECT:  # no playable chart: show the select screen
                self._enter_select(now)
        else:
            self._enter_select(now)
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    def start_on_open(self, mode):
        """Start the song in `mode` as soon as the game opens and go back to the start screen when it ends
        or is quit, without showing the select screen (used by the start screen)."""
        self._start_mode_on_open = mode
        self._exit_to_start_screen = True

    def start_game(self) -> None:
        """Start the selected song (BLE start command)."""
        if self._task is None:
            self.load_game_config(self._config)
        if self._phase in (PHASE_SELECT, PHASE_RESULT):
            self._start_run(time.ticks_ms(), self._mode)

    def pause_game(self) -> None:
        if self._phase in (PHASE_COUNT_IN, PHASE_PLAY):
            self._pause(time.ticks_ms())

    def resume_game(self) -> None:
        if self._phase == PHASE_PAUSED:
            self._resume(time.ticks_ms())

    def reset_game(self) -> None:
        """Quit the running song (nothing saved), then the select screen or the start screen (BLE reset)."""
        now = time.ticks_ms()
        if self._phase in (PHASE_COUNT_IN, PHASE_PLAY, PHASE_PAUSED):
            self._quit(now)
        else:
            self._leave_run(now)

    def stop_game(self) -> None:
        """Stop the game loop, release the keyboard and turn off lights and motor."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if globals.keyboard:
            globals.keyboard.set_key_event_callback(None)
            globals.keyboard.set_color(0, 0, 0)
            globals.keyboard.show()
        self._haptics.stop()
        self._state.state = config.GAME_STATE_OVER
        self.notify_state(config.GAME_STATE_OVER)

    def UpdateGridState(self) -> None:
        self._render(time.ticks_ms())

    def next_step(self) -> None:
        """Not used: notes advance with song time, not with steps."""
        pass

    def keyPressedCallback(self, key_or_event) -> None:
        key = getattr(key_or_event, "key", key_or_event)
        self._on_key_event(key, config.KEY_ACTION_PRESSED, time.ticks_ms())

    def win(self) -> None:
        """Finish the running song and show the result."""
        if self._phase in (PHASE_COUNT_IN, PHASE_PLAY, PHASE_PAUSED):
            self._finish(time.ticks_ms())

    def lose(self) -> None:
        """Abort the running song without saving (used by quit)."""
        if self._phase in (PHASE_COUNT_IN, PHASE_PLAY, PHASE_PAUSED):
            self._quit(time.ticks_ms())

    def stats_line(self) -> str:
        line = "loop gap max %d ms, renders %d, input overflows %d, free mem %d" % (
            self.max_loop_gap_ms, self.renders, self._queue_overflows, gc.mem_free() if hasattr(gc, "mem_free") else -1)
        self.max_loop_gap_ms = 0
        self.renders = 0
        return line

    # ==========================================================================
    # Game loop
    # ==========================================================================
    async def _loop(self):
        last = time.ticks_ms()
        while True:
            now = time.ticks_ms()
            gap = time.ticks_diff(now, last)
            if gap > self.max_loop_gap_ms:
                self.max_loop_gap_ms = gap
            last = now
            try:
                self._tick(now)
            except Exception as exc:
                print("[PocketGuitar] Game loop crashed, game stopped:")
                if hasattr(sys, "print_exception"):
                    sys.print_exception(exc)
                else:
                    import traceback
                    traceback.print_exception(exc)
                self._haptics.stop()
                self._task = None
                return
            await asyncio.sleep_ms(LOOP_INTERVAL_MS)

    def _tick(self, now):
        if time.ticks_diff(now, self._next_stats_ms) >= 0:
            self._log(self.stats_line())
            self._next_stats_ms = time.ticks_add(now, STATS_LOG_INTERVAL_MS)
        if globals.keyboard:
            globals.keyboard.poll()
        self._drain_input()

        phase = self._phase
        if phase == PHASE_COUNT_IN or phase == PHASE_PLAY:
            self._update_song(now)
        elif phase == PHASE_RESULT:
            self._update_result(now)
        self._update_hold_gesture(now)
        self._haptics.update(now)

        animated = self._phase != PHASE_PAUSED
        if self._dirty or (animated and time.ticks_diff(now, self._last_render) >= RENDER_INTERVAL_MS):
            self._render(now)

    def _set_phase(self, phase, now):
        self._phase = phase
        self._phase_start = now
        self._dirty = True

    def _log(self, message, song_ms=None):
        if song_ms is None:
            print("[PocketGuitar] " + message)
        else:
            print("[PocketGuitar %7d] %s" % (song_ms, message))

    def _send(self, event_id, payload):
        ble_inst = getattr(globals, "bluetooth", None) or getattr(globals, "ble", None)
        if ble_inst and ble_inst.is_connected:
            ble_inst.send_event(event_id, payload)
        if self.log_level >= LOG_DEBUG:
            self._log("BLE event 0x%02X %s" % (event_id, payload.hex()))

    # ==========================================================================
    # Input
    # ==========================================================================
    def _on_key_event(self, key, action, event_time):
        # Runs in scheduler context between game loop bytecodes: only queue the event.
        tail = self._queue_tail
        next_tail = (tail + 1) % _QUEUE_SIZE
        if next_tail == self._queue_head:
            self._queue_overflows += 1
            return
        self._queue_key[tail] = key
        self._queue_action[tail] = action
        self._queue_time[tail] = event_time
        self._queue_tail = next_tail

    def _drain_input(self):
        while self._queue_head != self._queue_tail:
            head = self._queue_head
            key = self._queue_key[head]
            pressed = self._queue_action[head] == config.KEY_ACTION_PRESSED
            event_time = self._queue_time[head]
            self._queue_head = (head + 1) % _QUEUE_SIZE
            self._handle_input(key, pressed, event_time)

    def _handle_input(self, key, pressed, event_time):
        if self._leaving:
            return  # the start screen opens in a moment
        phase = self._phase
        now = time.ticks_ms()

        if key < config.GRID_NUM_KEYS:
            physical = key
            key = _PHYSICAL_KEY[physical]
            self._update_fret(key, pressed)
            if self.log_level >= LOG_DEBUG:
                self._log("pad %2d %s (layout key %2d) -> frets %s" % (
                    physical, "down" if pressed else "up  ", key, mask_to_lanes(self._frets)))
            if phase == PHASE_COUNT_IN or phase == PHASE_PLAY:
                if self._ps_active:
                    self._fret_changed_during_strum(event_time)
            elif pressed and phase == PHASE_SELECT:
                self._select_input(key)
            elif pressed and phase == PHASE_RESULT and self._result_unlocked(now):
                self._leave_run(now)
            return

        if key == config.STRUM_KEY_RED:
            bit = STRUM_RED
        elif key == config.STRUM_KEY_BLUE:
            bit = STRUM_BLUE
        else:
            return
        if pressed:
            self._strum_down |= bit
        else:
            self._strum_down &= ~bit
        if self.log_level >= LOG_DEBUG:
            self._log("strum %s %s" % (STRUM_NAMES[bit], "down" if pressed else "up"))

        if phase == PHASE_SELECT:
            # Start when the strum keys are released, so holding both (back to the start screen) doesn't start a song
            if pressed:
                if not self._select_strum:
                    self._select_strum = bit
            elif self._strum_down == 0:
                strum = self._select_strum
                self._select_strum = 0
                if strum and not self._hold_fired:
                    self._start_run(now, MODE_PLAY if strum == STRUM_RED else MODE_PRACTICE)
        elif phase == PHASE_PLAY:
            if pressed:
                self._strum(bit, event_time, now)
        elif phase == PHASE_PAUSED:
            if pressed:
                self._paused_strum = True
            elif self._strum_down == 0 and self._paused_strum and not self._hold_fired:
                self._resume(now)
        elif phase == PHASE_RESULT:
            if pressed and self._result_unlocked(now):
                self._start_run(now, self._mode)

    def _update_fret(self, key, pressed):
        lane = _COLUMN_LANE[key % _COLS]
        if lane < 0:
            return  # feedback column is not a fret
        if pressed and not self._key_down[key]:
            self._key_down[key] = 1
            self._lane_count[lane] += 1
            self._frets |= 1 << lane
        elif not pressed and self._key_down[key]:
            self._key_down[key] = 0
            self._lane_count[lane] -= 1
            if self._lane_count[lane] == 0:
                self._frets &= ~(1 << lane)

    def _update_hold_gesture(self, now):
        """Both strum keys held for PAUSE_HOLD_MS without frets: pause, quit when paused,
        back to the start screen on the select screen."""
        if self._leaving:
            return
        if self._strum_down == STRUM_BOTH and self._frets == 0:
            if not self._hold_active:
                self._hold_active = True
                self._hold_start = now
            elif not self._hold_fired and time.ticks_diff(now, self._hold_start) >= PAUSE_HOLD_MS:
                self._hold_fired = True
                if self._phase in (PHASE_COUNT_IN, PHASE_PLAY):
                    self._pause(now)
                elif self._phase == PHASE_PAUSED:
                    self._quit(now)
                elif self._phase == PHASE_SELECT:
                    self._back_to_start_screen()
        else:
            self._hold_active = False
            if self._strum_down == 0:
                self._hold_fired = False

    # ==========================================================================
    # Select screen
    # ==========================================================================
    def _enter_select(self, now):
        self._haptics.stop()
        self._chart = None
        self._select_strum = 0
        self._set_phase(PHASE_SELECT, now)
        self._state.state = config.GAME_STATE_READY
        self.notify_state(config.GAME_STATE_READY)
        self._after_selection()

    def _after_selection(self):
        if self.log_level >= LOG_INFO:
            self._log_menu()
        self.send_selection()

    def _back_to_start_screen(self):
        if self._leaving:
            return
        self._leaving = True
        self._haptics.play(_FX_GESTURE, PRIORITY_SYSTEM, 60)
        if self.log_level >= LOG_INFO:
            self._log("Back to the start screen.")
        from game import game_manager
        game_manager.request_open(config.GAME_ID_START_SCREEN)

    def _leave_run(self, now):
        """After a song, a quit or a BLE reset: the start screen when the song was started there, else the select screen."""
        if self._exit_to_start_screen:
            self._back_to_start_screen()
        else:
            self._enter_select(now)

    def _log_menu(self):
        self._log("===== SELECT =====")
        if not self._song_files and self._song is None:
            self._log("No songs found. Upload game/pocketGuitar/songs/*.json to the board or send a song from the app.")
            return
        for slot, path in enumerate(self._song_files[:_COLS]):
            marker = ">" if slot == self._song_slot else " "
            self._log(" %s pad %2d: %s" % (marker, _PHYSICAL_KEY[_ROW_AT_DISTANCE[1] * _COLS + slot], path.split("/")[-1]))
        song = self._song
        if song is None:
            return
        names = " ".join(DIFFICULTIES[d] for d in song.available_difficulties())
        self._log("Song: %s (%s), %.1f BPM, %d s. Difficulties: %s" % (
            song.title, song.artist, song.bpm_x10 / 10, song.length_ms // 1000, names))
        record = self._records.get(song.song_id, self._difficulty)
        best = "best %d, %d stars, %d%%" % (record["score"], record["stars"], record["accuracy"]) if record else "no record yet"
        pads = ",".join(str(_PHYSICAL_KEY[_ROW_AT_DISTANCE[0] * _COLS + d]) for d in range(len(DIFFICULTIES)))
        self._log("Difficulty: %s (%s). Pads %s = easy, medium, hard, expert." % (DIFFICULTIES[self._difficulty], best, pads))
        self._log("Red strum = Play, blue strum = Practice (starts on release). Hold both strum keys 2 s = start screen.")
        self._log("In a song: hold both strum keys 2 s (no frets) = pause.")

    def _select_input(self, key):
        row = _ROW_AT_DISTANCE[key // _COLS]  # rows counted from the hit row
        lane = key % _COLS
        if row == 0 and lane < len(DIFFICULTIES):
            self.select_difficulty(lane)
        elif row == 1 and lane < _COLS:
            self.select_song_slot(lane)

    # ==========================================================================
    # Selection from the start screen and the app (BLE)
    # ==========================================================================
    def preselect_difficulty(self, difficulty):
        """Difficulty to show when the select screen opens (used by the start screen)."""
        self._difficulty = difficulty

    def select_song_slot(self, slot):
        """Select a song on the select screen. Returns False when that is not possible now."""
        if self._phase != PHASE_SELECT or not 0 <= slot < len(self._song_files):
            return False
        if slot != self._song_slot:
            self._select_song(slot)
            self._dirty = True
            self._after_selection()
        return True

    def load_song_json(self, raw):
        """Load a song sent by the app (song file JSON as bytes) and select it as APP_SONG_SLOT.

        Only on the select screen. Returns False when that is not possible now or the song is invalid;
        the previously selected song stays selected then.
        """
        if self._phase != PHASE_SELECT:
            return False
        previous = self._song
        self._song = None
        gc.collect()
        try:
            song = songs.load_song_data(json.loads(raw), "app")
            if not song.available_difficulties():
                raise ValueError("song has no charts")
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            self._log("Could not load the song from the app: %r" % (exc,))
            self._song = previous
            return False
        del previous
        self._song = song
        self._song_slot = APP_SONG_SLOT
        available = song.available_difficulties()
        if self._difficulty not in available:
            self._difficulty = available[0]
        gc.collect()
        self._dirty = True
        if self.log_level >= LOG_INFO:
            self._log("Song from the app: %s (%s)" % (song.title, song.artist))
        self._after_selection()
        return True

    def select_difficulty(self, difficulty):
        song = self._song
        if self._phase != PHASE_SELECT or song is None or song.chart(difficulty) is None:
            return False
        if difficulty != self._difficulty:
            self._difficulty = difficulty
            self._dirty = True
            self._after_selection()
        return True

    def select_mode(self, mode):
        """Mode for the app's start command (on the board, the strum colour picks the mode)."""
        if self._phase != PHASE_SELECT or mode not in (MODE_PLAY, MODE_PRACTICE):
            return False
        if mode != self._mode:
            self._mode = mode
            self._after_selection()
        return True

    def set_delay_offset(self, offset_ms):
        if self._phase in (PHASE_COUNT_IN, PHASE_PLAY):
            return False
        self.delay_offset_ms = offset_ms
        if self.log_level >= LOG_INFO:
            self._log("Delay offset %d ms" % offset_ms)
        return True

    def set_options(self, bits):
        """bit 0 beat lines, bit 1 beat tick vibration, bit 2 sustain hum"""
        self.beat_lines = bool(bits & 1)
        self.beat_tick = bool(bits & 2)
        self.sustain_hum = bool(bits & 4)
        if not self.sustain_hum:
            self._haptics.set_hum(False)
        self._dirty = True
        if self.log_level >= LOG_INFO:
            self._log("Options: beat lines %s, beat tick %s, sustain hum %s" % (
                self.beat_lines, self.beat_tick, self.sustain_hum))
        return True

    def send_selection(self):
        song = self._song
        available = 0
        best_score = 0
        best_stars = 0
        if song is not None:
            for difficulty in song.available_difficulties():
                available |= 1 << difficulty
            record = self._records.get(song.song_id, self._difficulty)
            if record:
                best_score = record["score"]
                best_stars = record["stars"]
        self._send(BLE_EVENT_ID_SONG_SELECTION,
                   bytes((self._song_slot, len(self._song_files), self._difficulty, available, self._mode, best_stars))
                   + _u32(best_score))

    def _select_song(self, slot):
        if not self._song_files:
            self._song = None
            return
        slot = min(slot, len(self._song_files) - 1)
        self._song = None
        gc.collect()
        path = self._song_files[slot]
        try:
            self._song = songs.load_song(path)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            self._log("Could not load %s: %r" % (path, exc))
            return
        self._song_slot = slot
        available = self._song.available_difficulties()
        if available and self._difficulty not in available:
            self._difficulty = available[0]
        gc.collect()

    # ==========================================================================
    # Running a song
    # ==========================================================================
    def _start_run(self, now, mode):
        song = self._song
        chart = song.chart(self._difficulty) if song is not None else None
        if chart is None:
            self._log("No playable chart selected.")
            return
        gc.collect()
        self._mode = mode
        self._chart = chart
        self._note_state = bytearray(len(chart))
        self._first_open = 0
        self._waiting = False
        self._score = 0
        self._streak = 0
        self._best_streak = 0
        for i in range(len(self._counts)):
            self._counts[i] = 0
        self._ps_active = False
        self._sustain_note = -1
        self._feedback_color = None
        self._haptics.stop()

        self._state.score = 0
        self._state.state = config.GAME_STATE_RUNNING
        self.notify_state(config.GAME_STATE_RUNNING)
        if self.log_level >= LOG_INFO:
            self._log("===== %s: %s [%s], %d notes, max score %d, row %d ms, timing +-%d/+-%d ms, delay offset %d ms =====" % (
                _MODE_NAMES[mode].upper(), song.title, DIFFICULTIES[chart.difficulty], len(chart),
                chart.max_score, chart.row_ms, chart.perfect_ms, chart.good_ms, self.delay_offset_ms))
        self._begin_playback(now, 0)

    def _begin_playback(self, now, from_ms):
        """Start (or resume) playback with a one-bar count-in before song position from_ms."""
        song = self._song
        start = max(0, from_ms) - song.bar_ms
        self._t0 = time.ticks_add(now, -start)
        self._preroll_until = max(0, from_ms)
        self._last_beat = song.beat_index_at(self._song_ms(now)) - 1
        self._set_phase(PHASE_COUNT_IN if start < 0 else PHASE_PLAY, now)
        payload = (bytes((self._song_slot, self._difficulty, self._mode)) + _u16(song.bpm_x10)
                   + _u32(start) + _u16(self.delay_offset_ms))
        self._send(BLE_EVENT_ID_SONG_START, payload)
        if self.log_level >= LOG_INFO:
            self._log("Count-in (1 bar), song starts at %d ms" % max(0, from_ms), self._song_ms(now))

    def _song_ms(self, now):
        if self._waiting:
            return self._wait_ms
        return time.ticks_diff(now, self._t0) - self.delay_offset_ms

    def _update_song(self, now):
        song = self._song
        chart = self._chart
        song_ms = self._song_ms(now)

        if self._phase == PHASE_COUNT_IN and song_ms >= 0:
            self._set_phase(PHASE_PLAY, now)
            if self.log_level >= LOG_INFO:
                self._log("GO", song_ms)

        beat = song.beat_index_at(song_ms)
        if beat != self._last_beat:
            self._last_beat = beat
            if -song.beats_per_bar <= beat < 0:
                effect = _FX_COUNT_IN_FIRST if beat == -song.beats_per_bar else _FX_COUNT_IN
                self._haptics.play(effect, PRIORITY_TICK, 40)
                self._dirty = True
            elif beat >= 0 and song_ms < self._preroll_until:
                self._haptics.play(_FX_COUNT_IN, PRIORITY_TICK, 40)
            elif beat >= 0 and self.beat_tick:
                self._haptics.play(_FX_BEAT, PRIORITY_TICK, 40)

        if self._ps_active and time.ticks_diff(now, self._ps_deadline) >= 0:
            self._finalize_strum(now)
        if self._sustain_note >= 0:
            self._update_sustain(now, song_ms)

        if self._mode == MODE_PLAY:
            self._sweep_misses(now, song_ms)
        self._advance_first_open()
        if self._mode == MODE_PRACTICE:
            self._update_practice_wait(song_ms)

        if song_ms >= song.length_ms and not self._ps_active and self._sustain_note < 0:
            self._finish(now)

    def _sweep_misses(self, now, song_ms):
        chart = self._chart
        times = chart.times
        count = len(times)
        i = self._first_open
        while i < count and times[i] + chart.good_ms < song_ms:
            if self._note_state[i] == NOTE_PENDING:
                self._apply_result(i, NOTE_MISS, None, 0, now)
            i += 1

    def _advance_first_open(self):
        states = self._note_state
        i = self._first_open
        count = len(states)
        while i < count and states[i] != NOTE_PENDING and states[i] != NOTE_CLAIMED:
            i += 1
        self._first_open = i

    def _update_practice_wait(self, song_ms):
        if self._waiting:
            return
        i = self._first_open
        if i < len(self._note_state) and song_ms >= self._chart.times[i]:
            self._waiting = True
            self._wait_ms = self._chart.times[i]
            self._dirty = True
            if self.log_level >= LOG_INFO:
                chart = self._chart
                self._log("waiting for note %d: lanes %s, strum %s" % (
                    i, mask_to_lanes(chart.frets[i]), STRUM_NAMES[self._required_strum(i)]), self._wait_ms)

    def _required_strum(self, note):
        chart = self._chart
        return STRUM_ANY if chart.difficulty == DIFFICULTY_EASY else chart.strums[note]

    # ==========================================================================
    # Judgement
    # ==========================================================================
    def _strum(self, bit, event_time, now):
        if self._ps_active:
            if time.ticks_diff(event_time, self._ps_time) <= STRUM_WINDOW_MS and not (self._ps_mask & bit):
                self._ps_mask |= bit
                return
            self._finalize_strum(now)

        song_ms = time.ticks_diff(event_time, self._t0) - self.delay_offset_ms
        if self._waiting:
            song_ms = self._wait_ms
        if self._sustain_note >= 0:
            self._end_sustain(song_ms, "strum")

        note = self._find_note(song_ms)
        if note < 0 and self._mode == MODE_PRACTICE:
            if self.log_level >= LOG_DEBUG:
                self._log("strum ignored (practice, no note near)", song_ms)
            return

        self._ps_active = True
        self._ps_time = event_time
        self._ps_deadline = time.ticks_add(event_time, STRUM_WINDOW_MS)
        self._ps_mask = bit
        self._ps_note = note
        if note >= 0:
            self._note_state[note] = NOTE_CLAIMED
            self._ps_fret_err = popcount(self._frets ^ self._chart.frets[note])

    def _find_note(self, song_ms):
        """Earliest pending note whose timing window contains song_ms, or -1."""
        chart = self._chart
        times = chart.times
        good = chart.good_ms
        count = len(times)
        i = self._first_open
        while i < count:
            dt = song_ms - times[i]
            if dt < -good:
                break
            if dt <= good and self._note_state[i] == NOTE_PENDING:
                return i
            i += 1
        return -1

    def _fret_changed_during_strum(self, event_time):
        note = self._ps_note
        if note < 0 or time.ticks_diff(event_time, self._ps_deadline) > 0:
            return
        errors = popcount(self._frets ^ self._chart.frets[note])
        if errors < self._ps_fret_err:
            self._ps_fret_err = errors

    def _finalize_strum(self, now):
        self._ps_active = False
        note = self._ps_note
        song_ms = time.ticks_diff(self._ps_time, self._t0) - self.delay_offset_ms
        if self._waiting:
            song_ms = self._wait_ms
        if note < 0:
            self._overstrum(song_ms)
            return

        chart = self._chart
        required = self._required_strum(note)
        color_error = 1 if required != STRUM_ANY and self._ps_mask != required else 0
        mistakes = self._ps_fret_err + color_error
        dt = song_ms - chart.times[note]

        if self._mode == MODE_PRACTICE:
            if mistakes == 0:
                self._practice_hit(note, now)
            else:
                self._note_state[note] = NOTE_PENDING
                self._feedback(_MISS_FLASH, FEEDBACK_MISS_MS, now)
                self._haptics.play(_FX_MISS, PRIORITY_MISS, MISS_BUZZ_MS, cut=True)
                if self.log_level >= LOG_INFO:
                    self._log("try again: note %d needs lanes %s strum %s, you played lanes %s strum %s" % (
                        note, mask_to_lanes(chart.frets[note]), STRUM_NAMES[required],
                        mask_to_lanes(self._frets), STRUM_NAMES[self._ps_mask]), song_ms)
            return

        if mistakes == 0:
            grade = NOTE_PERFECT if -chart.perfect_ms <= dt <= chart.perfect_ms else NOTE_GOOD
        elif mistakes == 1:
            grade = NOTE_ALMOST
        else:
            grade = NOTE_MISS
        self._apply_result(note, grade, dt, mistakes, now)

    def _apply_result(self, note, grade, dt, mistakes, now):
        chart = self._chart
        frets = chart.frets[note]
        self._note_state[note] = grade
        self._counts[grade] += 1

        old_multiplier = multiplier_for(self._streak)
        if grade == NOTE_PERFECT or grade == NOTE_GOOD:
            self._streak += 1
            if self._streak > self._best_streak:
                self._best_streak = self._streak
        elif grade == NOTE_MISS:
            self._streak = 0
        multiplier = multiplier_for(self._streak)
        points = POINTS_PER_FRET * popcount(frets) * _GRADE_PERCENT[grade] // 100 * multiplier
        self._score += points
        self._state.score = self._score

        if grade == NOTE_PERFECT or grade == NOTE_GOOD:
            self._feedback(_HIT_FLASH, FEEDBACK_FLASH_MS, now)
            if multiplier > old_multiplier:
                self._haptics.play(_FX_MULTIPLIER, PRIORITY_MULTIPLIER, 120)
            elif chart.strums[note] == STRUM_BOTH or popcount(frets) >= 3:
                self._haptics.play(_FX_ACCENT, PRIORITY_ACCENT, 40)
        elif grade == NOTE_ALMOST:
            self._feedback(_ALMOST_FLASH, FEEDBACK_FLASH_MS, now)
            self._haptics.play(_FX_ALMOST, PRIORITY_ALMOST, 40)
        else:
            self._feedback(_MISS_FLASH, FEEDBACK_MISS_MS, now)
            self._haptics.play(_FX_MISS, PRIORITY_MISS, MISS_BUZZ_MS, cut=True)

        if grade != NOTE_MISS and chart.ends[note] > chart.times[note]:
            self._start_sustain(note, grade, multiplier)

        self._send(BLE_EVENT_ID_NOTE_RESULT,
                   _u16(note) + bytes((grade, multiplier)) + _u32(self._score))
        self._dirty = True

        if self.log_level >= LOG_INFO:
            required = self._required_strum(note)
            wanted = "lanes %-7s %-6s" % (mask_to_lanes(frets), STRUM_NAMES[required])
            if dt is None:
                detail = "not played"
            else:
                detail = "dt %+4d ms, played %-7s %-6s, mistakes %d" % (
                    dt, mask_to_lanes(self._frets), STRUM_NAMES[self._ps_mask], mistakes)
            self._log("%-7s note %3d  %s  %s  x%d +%d = %d" % (
                _GRADE_NAMES[grade], note, wanted, detail, multiplier, points, self._score), chart.times[note])
            if multiplier > old_multiplier:
                self._log("streak %d -> multiplier x%d" % (self._streak, multiplier))

    def _overstrum(self, song_ms):
        self._counts[_COUNT_OVERSTRUM] += 1
        broke = self._streak
        self._streak = 0
        self._feedback(_MISS_FLASH, FEEDBACK_MISS_MS, time.ticks_ms())
        self._haptics.play(_FX_MISS, PRIORITY_MISS, MISS_BUZZ_MS, cut=True)
        self._send(BLE_EVENT_ID_OVERSTRUM, _u32(self._score))
        if self.log_level >= LOG_INFO:
            self._log("OVERSTRUM no note near (strum %s, frets %s), streak %d lost" % (
                STRUM_NAMES[self._ps_mask], mask_to_lanes(self._frets), broke), song_ms)

    def _practice_hit(self, note, now):
        chart = self._chart
        self._note_state[note] = NOTE_PERFECT
        self._counts[NOTE_PERFECT] += 1
        self._feedback(_HIT_FLASH, FEEDBACK_FLASH_MS, now)
        if chart.strums[note] == STRUM_BOTH or popcount(chart.frets[note]) >= 3:
            self._haptics.play(_FX_ACCENT, PRIORITY_ACCENT, 40)
        if chart.ends[note] > chart.times[note]:
            self._start_sustain(note, NOTE_PERFECT, 1)
        if self._waiting:
            # Continue the clock from the note time
            raw_ms = time.ticks_diff(now, self._t0) - self.delay_offset_ms
            self._t0 = time.ticks_add(self._t0, raw_ms - self._wait_ms)
            self._waiting = False
        self._dirty = True
        if self.log_level >= LOG_INFO:
            self._log("OK      note %3d  lanes %s" % (note, mask_to_lanes(chart.frets[note])), chart.times[note])

    def _feedback(self, color, duration_ms, now):
        self._feedback_color = color
        self._feedback_until = time.ticks_add(now, duration_ms)
        self._dirty = True

    # ==========================================================================
    # Sustains
    # ==========================================================================
    def _start_sustain(self, note, grade, multiplier):
        self._sustain_note = note
        self._sustain_grade = grade
        self._sustain_mult = multiplier
        self._sustain_released = False
        if self.sustain_hum:
            self._haptics.set_hum(True)

    def _update_sustain(self, now, song_ms):
        chart = self._chart
        note = self._sustain_note
        if song_ms >= chart.ends[note]:
            self._end_sustain(chart.ends[note], "complete")
            return
        needed = chart.frets[note]
        if self._frets & needed == needed:
            self._sustain_released = False
        elif not self._sustain_released:
            self._sustain_released = True
            self._sustain_release_time = now
            self._sustain_release_ms = song_ms
        elif time.ticks_diff(now, self._sustain_release_time) >= SUSTAIN_RELEASE_GRACE_MS:
            self._end_sustain(self._sustain_release_ms, "released")

    def _end_sustain(self, end_ms, reason):
        chart = self._chart
        note = self._sustain_note
        self._sustain_note = -1
        self._haptics.set_hum(False)
        start = chart.times[note]
        length = chart.ends[note] - start
        held = max(0, min(end_ms, chart.ends[note]) - start)
        points = 0
        if self._mode == MODE_PLAY:
            points = self._song.sustain_points(held) * self._sustain_mult
            if self._sustain_grade == NOTE_ALMOST:
                points //= 2
            self._score += points
            self._state.score = self._score
        percent = held * 100 // length if length > 0 else 100
        self._send(BLE_EVENT_ID_SUSTAIN_END, _u16(note) + bytes((percent,)))
        self._dirty = True
        if self.log_level >= LOG_INFO:
            self._log("sustain note %3d %s: held %d%% +%d = %d" % (note, reason, percent, points, self._score), end_ms)

    # ==========================================================================
    # Pause, quit, result
    # ==========================================================================
    def _pause(self, now):
        song_ms = self._song_ms(now)
        self._pause_ms = song_ms
        if self._ps_active:
            self._ps_active = False
            if self._ps_note >= 0:
                self._note_state[self._ps_note] = NOTE_PENDING
        if self._sustain_note >= 0:
            self._end_sustain(song_ms, "paused")
        self._haptics.stop()
        self._haptics.play(_FX_GESTURE, PRIORITY_SYSTEM, 60)
        self._paused_strum = False
        self._set_phase(PHASE_PAUSED, now)
        self._state.state = config.GAME_STATE_PAUSED
        self.notify_state(config.GAME_STATE_PAUSED)
        if self.log_level >= LOG_INFO:
            self._log("PAUSED. Strum = resume, hold both strum keys 2 s = quit.", song_ms)

    def _resume(self, now):
        self._waiting = False
        self._haptics.play(_FX_GESTURE, PRIORITY_SYSTEM, 60)
        self._state.state = config.GAME_STATE_RUNNING
        self.notify_state(config.GAME_STATE_RUNNING)
        if self.log_level >= LOG_INFO:
            self._log("RESUME", self._pause_ms)
        self._begin_playback(now, self._pause_ms)

    def _quit(self, now):
        self._ps_active = False
        self._sustain_note = -1
        self._haptics.stop()
        self._haptics.play(_FX_GESTURE, PRIORITY_SYSTEM, 60)
        self.notify_state(config.GAME_STATE_OVER)
        if self.log_level >= LOG_INFO:
            self._log("QUIT, nothing saved.")
        self._leave_run(now)

    def _finish(self, now):
        song = self._song
        chart = self._chart
        self._ps_active = False
        if self._sustain_note >= 0:
            self._end_sustain(self._song_ms(now), "song end")
        self._haptics.stop()

        if self._mode == MODE_PRACTICE:
            self._haptics.play(_FX_RESULT, PRIORITY_SYSTEM, 220)
            if self.log_level >= LOG_INFO:
                self._log("Practice finished: %d notes played." % len(chart))
            self._leave_run(now)
            return

        counts = self._counts
        note_count = len(chart)
        hits = counts[NOTE_PERFECT] + counts[NOTE_GOOD]
        accuracy = (hits * 2 + counts[NOTE_ALMOST]) * 100 // (2 * note_count) if note_count else 0
        percent = self._score * 100 // chart.max_score if chart.max_score else 0
        stars = 0
        for threshold in STAR_THRESHOLDS:
            if percent >= threshold:
                stars += 1
        flawless = note_count > 0 and hits == note_count and counts[_COUNT_OVERSTRUM] == 0
        new_best = self._records.submit(song.song_id, chart.difficulty, self._score, stars,
                                        accuracy, self._best_streak, flawless)

        self._result_stars = stars
        self._result_shown = 0
        self._result_new_best = new_best
        self._result_flawless = flawless
        self._set_phase(PHASE_RESULT, now)
        self._state.state = config.GAME_STATE_WIN
        self.notify_state(config.GAME_STATE_WIN)
        self.notify_score(self._score)
        flags = (1 if new_best else 0) | (2 if flawless else 0)
        self._send(BLE_EVENT_ID_SONG_RESULT,
                   _u32(self._score) + bytes((stars, accuracy)) + _u16(self._best_streak) + bytes((flags,)))
        self._haptics.play(_FX_RESULT, PRIORITY_SYSTEM, 220)

        if self.log_level >= LOG_INFO:
            self._log("===== RESULT: %s [%s] =====" % (song.title, DIFFICULTIES[chart.difficulty]))
            self._log("Score      %d / %d (%d%%)  %s" % (self._score, chart.max_score, percent, "*" * stars))
            self._log("Accuracy   %d%%   best streak %d" % (accuracy, self._best_streak))
            self._log("Perfect %d  Good %d  Almost %d  Miss %d  Overstrum %d" % (
                counts[NOTE_PERFECT], counts[NOTE_GOOD], counts[NOTE_ALMOST], counts[NOTE_MISS], counts[_COUNT_OVERSTRUM]))
            if flawless:
                self._log("FLAWLESS!")
            if new_best:
                self._log("NEW PERSONAL BEST!")
            self._log("Strum = play again, press a pad = back to %s." % (
                "the start screen" if self._exit_to_start_screen else "select"))

    def _result_unlocked(self, now):
        return time.ticks_diff(now, self._phase_start) >= RESULT_INPUT_LOCK_MS

    def _update_result(self, now):
        elapsed = time.ticks_diff(now, self._phase_start)
        shown = min(self._result_stars, elapsed // RESULT_STAR_STEP_MS)
        if shown != self._result_shown:
            self._result_shown = shown
            self._haptics.play(_FX_COUNT_IN, PRIORITY_TICK, 40)
            if shown == self._result_stars and self._result_new_best:
                self._haptics.play(_FX_NEW_BEST, PRIORITY_SYSTEM, 600, cut=True)

    # ==========================================================================
    # Rendering
    # ==========================================================================
    def _px(self, key, color):
        offset = _PHYSICAL_KEY[key] * 3
        frame = self._frame
        frame[offset] = color[0]
        frame[offset + 1] = color[1]
        frame[offset + 2] = color[2]

    def _draw_lanes(self, row, mask, color):
        base = row * _COLS
        for lane in range(NUM_LANES):
            if mask & (1 << lane):
                self._px(base + _LANE_COLUMN[lane], color)

    def _draw_column(self, column, color, rows=_ROWS):
        """Light `rows` cells of a column, starting at the far end of the highway."""
        for distance in range(_FAR_DISTANCE, _FAR_DISTANCE - rows, -1):
            self._px(_ROW_AT_DISTANCE[distance] * _COLS + column, color)

    def _render(self, now):
        self._dirty = False
        self._last_render = now
        self.renders += 1
        frame = self._frame
        frame[:] = self._blank

        phase = self._phase
        if phase == PHASE_SELECT:
            self._render_select(now)
        elif phase == PHASE_COUNT_IN:
            # Fill from the far row towards the hit row, one row per beat
            beat = self._song.beat_index_at(self._song_ms(now))
            lit = beat + self._song.beats_per_bar + 1
            for distance in range(_FAR_DISTANCE, _FAR_DISTANCE - min(lit, _ROWS), -1):
                self._draw_lanes(_ROW_AT_DISTANCE[distance], _ALL_LANES, _COUNT_IN_COLOR)
        elif phase == PHASE_PLAY:
            self._render_highway(now, self._song_ms(now))
            self._render_feedback(now)
        elif phase == PHASE_PAUSED:
            self._render_highway(now, self._pause_ms)
            self._render_feedback(now)
            for i in range(len(frame)):
                frame[i] >>= 2
        elif phase == PHASE_RESULT:
            self._render_result(now)

        if globals.keyboard:
            globals.keyboard.write_frame(frame)

    def _render_select(self, now):
        # Rows by distance from the hit row: difficulty, song, best stars, "strum to start" pulse
        song = self._song
        if song is not None:
            base = _ROW_AT_DISTANCE[0] * _COLS
            for difficulty in range(len(DIFFICULTIES)):
                if song.chart(difficulty) is not None:
                    color = _DIFFICULTY_COLORS[difficulty] if difficulty == self._difficulty else _DIFFICULTY_DIM_COLORS[difficulty]
                    self._px(base + difficulty, color)
            record = self._records.get(song.song_id, self._difficulty)
            if record:
                base = _ROW_AT_DISTANCE[2] * _COLS
                for column in range(record["stars"]):
                    self._px(base + column, _BEST_STAR_COLOR)
        base = _ROW_AT_DISTANCE[1] * _COLS
        for slot in range(min(_COLS, len(self._song_files))):
            self._px(base + slot, _SONG_COLOR if slot == self._song_slot else _SONG_DIM_COLOR)
        base = _ROW_AT_DISTANCE[_FAR_DISTANCE] * _COLS
        pulse = _SELECT_PULSE[(now // 250) % len(_SELECT_PULSE)]
        for column in range(_COLS):
            self._px(base + column, pulse)

    def _render_highway(self, now, song_ms):
        song = self._song
        chart = self._chart
        row_ms = chart.row_ms
        half = row_ms // 2

        if self.beat_lines:
            bar_lines = row_ms >= song.beat_ms
            beats_per_bar = song.beats_per_bar
            for distance in range(_ROWS):
                low = song_ms + distance * row_ms - half
                beat = song.first_beat_at_or_after(low)
                if bar_lines:
                    beat = -((-beat) // beats_per_bar) * beats_per_bar
                if song.beat_time_ms(beat) < low + row_ms:
                    self._draw_lanes(_ROW_AT_DISTANCE[distance], _ALL_LANES, _BEAT_LINE)

        position_times = chart.position_times
        if len(position_times):
            for distance in range(_ROWS):
                center = song_ms + distance * row_ms
                mask = 0
                for i in range(len(position_times)):
                    if position_times[i] > center:
                        break
                    mask = chart.position_masks[i]
                self._draw_lanes(_ROW_AT_DISTANCE[distance], mask, _POSITION_GLOW)

        times = chart.times
        ends = chart.ends
        states = self._note_state
        count = len(times)
        horizon = song_ms + _FAR_DISTANCE * row_ms + half
        i = self._first_open
        while i < count and times[i] < horizon:
            state = states[i]
            if state == NOTE_PENDING or state == NOTE_CLAIMED:
                head = max(0, (times[i] - song_ms + half) // row_ms)
                color = chart.strums[i]
                if ends[i] > times[i]:
                    tail_end = min(_FAR_DISTANCE, (ends[i] - song_ms + half) // row_ms)
                    for distance in range(head + 1, tail_end + 1):
                        self._draw_lanes(_ROW_AT_DISTANCE[distance], chart.frets[i], _TAIL_COLORS[color])
                self._draw_lanes(_ROW_AT_DISTANCE[head], chart.frets[i], _NOTE_COLORS[color])
            i += 1

        note = self._sustain_note
        if note >= 0:
            color = chart.strums[note]
            tail_end = min(_FAR_DISTANCE, (ends[note] - song_ms + half) // row_ms)
            for distance in range(1, tail_end + 1):
                self._draw_lanes(_ROW_AT_DISTANCE[distance], chart.frets[note], _TAIL_COLORS[color])
            head = _NOTE_COLORS[color] if (now // 120) % 2 == 0 else _NOTE_HALF_COLORS[color]
            self._draw_lanes(_HIT_ROW, chart.frets[note], head)

    def _render_feedback(self, now):
        """Feedback column: flash green / orange / red on each judgement, otherwise the streak meter."""
        if self._feedback_color is not None:
            if time.ticks_diff(self._feedback_until, now) > 0:
                self._draw_column(_FEEDBACK_COLUMN, self._feedback_color)
                return
            self._feedback_color = None
        if self._mode != MODE_PLAY:
            return
        multiplier = multiplier_for(self._streak)
        if multiplier >= len(_STREAK_COLORS):
            rows = _ROWS
        else:
            rows = 1 + (self._streak % STREAK_PER_MULTIPLIER) * (_ROWS - 1) // STREAK_PER_MULTIPLIER
        self._draw_column(_FEEDBACK_COLUMN, _STREAK_COLORS[multiplier - 1], rows)

    def _render_result(self, now):
        elapsed = time.ticks_diff(now, self._phase_start)
        filled = elapsed >= self._result_stars * RESULT_STAR_STEP_MS
        celebrate = filled and elapsed - self._result_stars * RESULT_STAR_STEP_MS < RESULT_CELEBRATION_MS
        if celebrate and self._result_flawless:
            shift = now // 100
            for column in range(_COLS):
                self._draw_column(column, _RAINBOW[(column + shift) % len(_RAINBOW)])
            return
        if celebrate and self._result_new_best and (now // 250) % 2:
            return
        for column in range(self._result_shown):
            self._draw_column(column, _STAR_COLOR)
