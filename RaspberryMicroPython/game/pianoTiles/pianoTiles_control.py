"""Piano Tiles: tap the tiles from the bottom up, never an empty pad (see GAME_DESIGN.md).

Portrait board: 4 lanes, 8 rows, tiles come from the top, one tile per row. Classic: 50 tiles
against the clock. Zen: as many tiles as possible in 30 s. Arcade: the tiles scroll by
themselves and get faster. The mechanical keys only do the back gesture.

BLE event BLE_EVENT_ID_PIANO_TILES, byte 1 = subtype, then (integers little-endian):
  RUN_START  mode u8, goal u16 (Classic: tiles, Zen: seconds, Arcade: 0), row time ms u16 (Arcade, else 0)
  TILE       tile u16, lane u8, time ms u32 since the start
  SPEED      level u8, row time ms u16
  TIME_LEFT  seconds u8
  MISTAKE    reason u8 (1 wrong pad, 2 missed tile), tile u16, x u8, y u8
  RESULT     mode u8, score u32 (Classic: ms, else tiles), tiles u16, stars u8, flags u8 (bit 0 new best, bit 1 finished)
"""
import time
import pico_config as config
from ble_handler.config import (
    BLE_EVENT_ID_PIANO_TILES, BLE_PIANO_RUN_START, BLE_PIANO_TILE, BLE_PIANO_SPEED,
    BLE_PIANO_TIME_LEFT, BLE_PIANO_MISTAKE, BLE_PIANO_RESULT,
)
from game import portrait
from game.best_scores import BestScores
from game.board_game import BoardGame, LOG_INFO, LOG_DEBUG, u16, u32
from game.haptic_player import (
    PRIORITY_TICK, PRIORITY_ALMOST, PRIORITY_ACCENT, PRIORITY_MISS, PRIORITY_SYSTEM,
)
from game.utils import GameConfig
from random_number_generator import RandomNumberGenerator

MODE_CLASSIC = config.PIANO_TILES_MODE_CLASSIC
MODE_ZEN = config.PIANO_TILES_MODE_ZEN
MODE_ARCADE = config.PIANO_TILES_MODE_ARCADE
_MODE_NAMES = ("Classic", "Zen", "Arcade")
_SCORE_KEYS = ("piano:classic", "piano:zen", "piano:arcade")

CLASSIC_TILES = 50
ZEN_TIME_MS = 30000
ZEN_WARNING_S = 5
ARCADE_ROW_MS = 400
ARCADE_SPEEDUP_TILES = 10
ARCADE_SPEEDUP_PERCENT = 90
ARCADE_MIN_ROW_MS = 130
MISSED_GRACE_MS = 80
GAME_OVER_MS = 1200
MISTAKE_BLINK_MS = 150
MISTAKE_BUZZ_MS = 300
RESULT_INPUT_LOCK_MS = 1500
RESULT_STAR_STEP_MS = 300
RESULT_CELEBRATION_MS = 3000
RESUME_TICKS = 3
RESUME_TICK_MS = 400
START_PULSE_MS = 300

# Stars, see GAME_DESIGN.md section 8 (starting values)
_CLASSIC_STAR_MS = (30000, 22000, 16000, 12000)   # 2-5 stars, finishing gives 1
_ZEN_STAR_TILES = (20, 60, 90, 120, 150)
_ARCADE_STAR_TILES = (10, 30, 60, 100, 150)

PHASE_READY = 0
PHASE_PLAY = 1
PHASE_GAME_OVER = 2
PHASE_RESULT = 3
PHASE_PAUSED = 4
PHASE_RESUME = 5  # count-in after a pause

REASON_WRONG = 1
REASON_MISSED = 2

# DRV2605L library effects, see GAME_DESIGN.md section 9
_FX_GESTURE = 7     # Soft Bump 100 %
_FX_FASTER = 10     # Double Click 100 %
_FX_DONE = 12       # Triple Click 100 %
_FX_START = 24      # Sharp Tick 1 100 %
_FX_TIME = 25       # Sharp Tick 2 80 %
_FX_TILE = 26       # Sharp Tick 3 60 %
_FX_MISTAKE = 47    # Buzz 1 100 %
_FX_NEW_BEST = 82   # Transition Ramp Up Long Smooth 1

# Vibration priorities: mistake > faster > time tick > tile tick
_PRIO_TILE = PRIORITY_TICK
_PRIO_TIME = PRIORITY_ALMOST
_PRIO_FASTER = PRIORITY_ACCENT
_PRIO_MISTAKE = PRIORITY_MISS
_PRIO_SYSTEM = PRIORITY_SYSTEM

_TILE = (0, 150, 255)
_START_BRIGHT = (160, 220, 255)
_TAPPED = (20, 20, 20)
_FINISH = (0, 160, 0)
_MISTAKE = (255, 0, 0)
_STAR = (255, 140, 0)
_NO_STAR = (40, 0, 0)

_LANES = portrait.WIDTH
_BOTTOM = portrait.HEIGHT - 1
_LANE_CHUNK = 64


class PianoTilesControl(BoardGame):
    """Piano Tiles with Classic, Zen and Arcade mode."""

    __slots__ = [
        "tile_tick",
        "_mode",
        "_goal",
        "_fixed",
        "_rng",
        "_lanes",
        "_count",
        "_scores",
        "_best",
        # phase
        "_phase",
        "_phase_start",
        # board
        "_bottom",
        "_next",
        "_tiles",
        # clocks
        "_t0",
        "_end_ms",
        "_row_ms",
        "_level",
        "_next_scroll_at",
        "_zen_end",
        "_last_second",
        "_paused_at",
        "_resume_tick",
        # Arcade: the lowest tile scrolled off the bottom and can still be tapped
        "_leaving",
        "_leaving_lane",
        "_leaving_until",
        # result
        "_mistake_cell",
        "_finished",
        "_score",
        "_stars",
        "_new_best",
        "_shown",
    ]

    def __init__(self, mode=MODE_CLASSIC, game_config=None):
        super().__init__(game_config or GameConfig(game_id=config.GAME_ID_PIANO_TILES), "PianoTiles")
        self.tile_tick = True
        self._mode = mode
        # A generated config (app seed) fixes the tiles; otherwise every run is new
        steps = self._config.steps
        self._fixed = bytes([s.pads[0] % _LANES for s in steps if s.pads]) if steps else None
        self._goal = len(self._fixed) if (self._fixed and mode == MODE_CLASSIC) else CLASSIC_TILES
        self._rng = RandomNumberGenerator()
        self._lanes = bytearray(2 * _LANE_CHUNK)
        self._count = 0
        self._scores = BestScores()
        self._best = self._scores.get(_SCORE_KEYS[mode])

        self._phase = PHASE_READY
        self._phase_start = 0

        self._bottom = 0
        self._next = 0
        self._tiles = 0

        self._t0 = 0
        self._end_ms = 0
        self._row_ms = ARCADE_ROW_MS
        self._level = 0
        self._next_scroll_at = 0
        self._zen_end = 0
        self._last_second = 0
        self._paused_at = 0
        self._resume_tick = 0

        self._leaving = False
        self._leaving_lane = 0
        self._leaving_until = 0

        self._mistake_cell = 0
        self._finished = False
        self._score = 0
        self._stars = 0
        self._new_best = False
        self._shown = 0

    # ==========================================================================
    # GameControl interface
    # ==========================================================================
    def start_game(self) -> None:
        """New tiles (BLE start). The run itself starts with the tap on the start tile."""
        if self._phase in (PHASE_READY, PHASE_RESULT):
            self.enter_ready(time.ticks_ms())

    def pause_game(self) -> None:
        if self._phase == PHASE_PLAY:
            now = time.ticks_ms()
            self._paused_at = now
            self._haptics.stop()
            self._haptics.play(_FX_GESTURE, _PRIO_SYSTEM, 60)
            self._set_phase(PHASE_PAUSED, now)
            self.set_state(config.GAME_STATE_PAUSED)
            if self.log_level >= LOG_INFO:
                self._log("PAUSED. Press any pad or resume from the app.")

    def resume_game(self) -> None:
        if self._phase == PHASE_PAUSED:
            now = time.ticks_ms()
            self._resume_tick = -1
            self._set_phase(PHASE_RESUME, now)
            self.set_state(config.GAME_STATE_RUNNING)
            if self.log_level >= LOG_INFO:
                self._log("RESUME: %d ticks, then go" % RESUME_TICKS)

    # ==========================================================================
    # Phases
    # ==========================================================================
    def _set_phase(self, phase, now):
        self._phase = phase
        self._phase_start = now
        self._dirty = True

    def _elapsed(self, now):
        return time.ticks_diff(now, self._phase_start)

    def enter_ready(self, now):
        """New tiles, the start tile waits at the bottom."""
        self._haptics.stop()
        self._count = 0
        self._bottom = 0
        self._next = 0
        self._tiles = 0
        self._leaving = False
        self._set_phase(PHASE_READY, now)
        self.set_state(config.GAME_STATE_READY)
        if self.log_level >= LOG_INFO:
            if self._mode == MODE_CLASSIC:
                rule = "%d tiles as fast as you can" % self._goal
                best = "best %d.%02d s" % (self._best // 1000, self._best % 1000 // 10) if self._best else "no best yet"
            else:
                rule = "as many tiles as you can in %d s" % (ZEN_TIME_MS // 1000) if self._mode == MODE_ZEN else "tiles scroll and get faster"
                best = "best %d tiles" % self._best if self._best else "no best yet"
            self._log("===== READY: Piano Tiles %s (%s), %s. Tap the start tile (bottom row, lane %d). =====" % (
                _MODE_NAMES[self._mode], rule, best, self._lane(0)))

    def _lane(self, index):
        """Lane of tile `index`. Tiles are generated on demand."""
        lanes = self._lanes
        fixed = self._fixed
        while self._count <= index:
            if self._count == len(lanes):
                lanes.extend(bytes(_LANE_CHUNK))
            i = self._count
            if fixed is not None and i < len(fixed):
                lane = fixed[i]
            else:
                lane = self._rng.randint(0, _LANES - 1)
                if i >= 2 and lanes[i - 1] == lane and lanes[i - 2] == lane:
                    lane = (lane + 1 + self._rng.randint(0, _LANES - 2)) % _LANES
            lanes[i] = lane
            self._count = i + 1
        return lanes[index]

    def _start_run(self, event_time, now):
        mode = self._mode
        self._t0 = event_time
        self._next = 1
        self._tiles = 1
        self._bottom = 0 if mode == MODE_ARCADE else 1
        self._row_ms = ARCADE_ROW_MS
        self._level = 0
        self._next_scroll_at = time.ticks_add(event_time, ARCADE_ROW_MS)
        self._zen_end = time.ticks_add(event_time, ZEN_TIME_MS)
        self._last_second = ZEN_TIME_MS // 1000
        self._set_phase(PHASE_PLAY, now)
        self.set_state(config.GAME_STATE_RUNNING)
        self._haptics.play(_FX_START, _PRIO_TIME, 40)

        goal = self._goal if mode == MODE_CLASSIC else (ZEN_TIME_MS // 1000 if mode == MODE_ZEN else 0)
        self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_RUN_START, mode)) + u16(goal)
                  + u16(ARCADE_ROW_MS if mode == MODE_ARCADE else 0))
        self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_TILE,)) + u16(0) + bytes((self._lane(0),)) + u32(0))
        if self.log_level >= LOG_INFO:
            self._log("===== GO: %s =====" % _MODE_NAMES[mode].upper())
        if mode == MODE_CLASSIC and self._next >= self._goal:
            self._end_ms = 0
            self._finish(now)

    # ==========================================================================
    # Game loop hooks
    # ==========================================================================
    def on_pad(self, cell, pressed, event_time, now):
        if not pressed:
            return
        x = cell % portrait.WIDTH
        y = cell // portrait.WIDTH
        phase = self._phase
        if phase == PHASE_PLAY:
            self._tap(x, y, event_time, now)
        elif phase == PHASE_READY:
            if y == _BOTTOM and x == self._lane(0):
                self._start_run(event_time, now)
        elif phase == PHASE_RESULT:
            if self._elapsed(now) >= RESULT_INPUT_LOCK_MS:
                self.enter_ready(now)
        elif phase == PHASE_PAUSED:
            self.resume_game()

    def update(self, now):
        phase = self._phase
        if phase == PHASE_PLAY:
            if self._mode == MODE_ARCADE:
                self._update_arcade(now)
            elif self._mode == MODE_ZEN:
                self._update_zen(now)
        elif phase == PHASE_GAME_OVER:
            if self._elapsed(now) >= GAME_OVER_MS:
                self._show_result(now, False)
        elif phase == PHASE_RESULT:
            self._update_result(now)
        elif phase == PHASE_RESUME:
            self._update_resume(now)

    def _update_arcade(self, now):
        if self._leaving and time.ticks_diff(now, self._leaving_until) >= 0:
            self._leaving = False
            self._mistake(REASON_MISSED, self._leaving_lane, _BOTTOM, now)
            return
        while time.ticks_diff(now, self._next_scroll_at) >= 0:
            if self._next == self._bottom:
                # The lowest tile is still untapped and scrolls off the board
                self._leaving = True
                self._leaving_lane = self._lane(self._next)
                self._leaving_until = time.ticks_add(self._next_scroll_at, MISSED_GRACE_MS)
            self._bottom += 1
            self._next_scroll_at = time.ticks_add(self._next_scroll_at, self._row_ms)
            self._dirty = True

    def _update_zen(self, now):
        left = time.ticks_diff(self._zen_end, now)
        if left <= 0:
            self._end_ms = ZEN_TIME_MS
            self._finish(now)
            return
        second = (left + 999) // 1000
        if second != self._last_second:
            self._last_second = second
            self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_TIME_LEFT, second)))
            if second <= ZEN_WARNING_S:
                self._haptics.play(_FX_TIME, _PRIO_TIME, 40)

    def _update_resume(self, now):
        tick = self._elapsed(now) // RESUME_TICK_MS
        if tick >= RESUME_TICKS:
            # The clocks continue where they stopped
            paused = time.ticks_diff(now, self._paused_at)
            self._t0 = time.ticks_add(self._t0, paused)
            self._next_scroll_at = time.ticks_add(self._next_scroll_at, paused)
            self._zen_end = time.ticks_add(self._zen_end, paused)
            self._leaving_until = time.ticks_add(self._leaving_until, paused)
            self._set_phase(PHASE_PLAY, now)
            if self.log_level >= LOG_INFO:
                self._log("GO")
        elif tick != self._resume_tick:
            self._resume_tick = tick
            self._haptics.play(_FX_TIME, _PRIO_TIME, 40)

    # ==========================================================================
    # Judgement
    # ==========================================================================
    def _tap(self, x, y, event_time, now):
        if self._leaving and y == _BOTTOM and x == self._leaving_lane:
            self._leaving = False
            self._hit(event_time, now)
            return
        index = self._bottom + _BOTTOM - y
        if self._mode == MODE_CLASSIC and index >= self._goal:
            return  # finish line, nothing above it
        if self._lane(index) != x:
            self._mistake(REASON_WRONG, x, y, now)
        elif index == self._next:
            self._hit(event_time, now)
        elif index > self._next:
            self._mistake(REASON_WRONG, x, y, now)  # tiles are tapped in order
        # index < next: a tile already tapped, ignored

    def _hit(self, event_time, now):
        index = self._next
        lane = self._lane(index)
        self._next = index + 1
        self._tiles += 1
        if self._mode != MODE_ARCADE:
            self._bottom = self._next
        self._dirty = True
        if self.tile_tick:
            self._haptics.play(_FX_TILE, _PRIO_TILE, 20)
        elapsed = time.ticks_diff(event_time, self._t0)
        self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_TILE,)) + u16(index) + bytes((lane,)) + u32(elapsed))
        if self.log_level >= LOG_DEBUG:
            self._log("tile %d (lane %d) at %d ms" % (index, lane, elapsed))

        if self._mode == MODE_CLASSIC and self._next >= self._goal:
            self._end_ms = elapsed
            self._finish(now)
        elif self._mode == MODE_ARCADE and self._tiles % ARCADE_SPEEDUP_TILES == 0 and self._row_ms > ARCADE_MIN_ROW_MS:
            self._level += 1
            self._row_ms = max(ARCADE_MIN_ROW_MS, self._row_ms * ARCADE_SPEEDUP_PERCENT // 100)
            self._haptics.play(_FX_FASTER, _PRIO_FASTER, 120)
            self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_SPEED, self._level)) + u16(self._row_ms))
            if self.log_level >= LOG_INFO:
                self._log("faster: level %d, %d ms per row (%d tiles)" % (self._level, self._row_ms, self._tiles))

    def _mistake(self, reason, x, y, now):
        self._mistake_cell = y * portrait.WIDTH + x
        self._set_phase(PHASE_GAME_OVER, now)
        self._haptics.play(_FX_MISTAKE, _PRIO_MISTAKE, MISTAKE_BUZZ_MS, cut=True)
        self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_MISTAKE, reason)) + u16(self._next) + bytes((x, y)))
        if self.log_level >= LOG_INFO:
            what = "missed tile %d" % self._next if reason == REASON_MISSED else "wrong pad x %d, y %d" % (x, y)
            self._log("GAME OVER: %s after %d tiles" % (what, self._tiles))

    # ==========================================================================
    # Result
    # ==========================================================================
    def _finish(self, now):
        """Classic: all tiles tapped, Zen: time is up."""
        self._haptics.play(_FX_DONE, _PRIO_SYSTEM, 220)
        self._show_result(now, True)

    def _show_result(self, now, finished):
        mode = self._mode
        tiles = self._tiles
        stars = 0
        new_best = False
        if mode == MODE_CLASSIC:
            score = self._end_ms if finished else 0
            if finished:
                stars = 1
                for limit in _CLASSIC_STAR_MS:
                    if score <= limit:
                        stars += 1
                new_best = self._scores.submit(_SCORE_KEYS[mode], score, lower_is_better=True)
        else:
            score = tiles
            for threshold in (_ZEN_STAR_TILES if mode == MODE_ZEN else _ARCADE_STAR_TILES):
                if tiles >= threshold:
                    stars += 1
            new_best = tiles > 0 and self._scores.submit(_SCORE_KEYS[mode], tiles)
        if new_best:
            self._best = score

        self._finished = finished
        self._score = score
        self._stars = stars
        self._new_best = new_best
        self._shown = 0
        self._set_phase(PHASE_RESULT, now)
        self._state.score = tiles
        self.set_state(config.GAME_STATE_WIN if finished else config.GAME_STATE_OVER)
        self.notify_score(tiles)
        flags = (1 if new_best else 0) | (2 if finished else 0)
        self.send(BLE_EVENT_ID_PIANO_TILES, bytes((BLE_PIANO_RESULT, mode)) + u32(score) + u16(tiles) + bytes((stars, flags)))
        if new_best and stars == 0:
            self._haptics.play(_FX_NEW_BEST, _PRIO_SYSTEM, 600, cut=True)

        if self.log_level >= LOG_INFO:
            if mode == MODE_CLASSIC:
                detail = "time %d.%02d s" % (score // 1000, score % 1000 // 10) if finished else "not finished (%d tiles)" % tiles
            else:
                detail = "%d tiles" % tiles
            self._log("===== RESULT: %s, %s, %s =====" % (
                _MODE_NAMES[mode], detail, "*" * stars if stars else "no star"))
            if new_best:
                self._log("NEW PERSONAL BEST!")
            self._log("Press any pad for new tiles.")

    def _update_result(self, now):
        shown = min(self._stars, self._elapsed(now) // RESULT_STAR_STEP_MS)
        if shown != self._shown:
            self._shown = shown
            self._dirty = True
            self._haptics.play(_FX_TIME, _PRIO_TILE, 40)
            if shown == self._stars and self._new_best:
                self._haptics.play(_FX_NEW_BEST, _PRIO_SYSTEM, 600, cut=True)

    # ==========================================================================
    # Rendering
    # ==========================================================================
    def draw(self, now):
        phase = self._phase
        if phase == PHASE_RESULT:
            self._draw_result(now)
            return
        self._draw_tiles(now)
        if phase == PHASE_GAME_OVER:
            if (self._elapsed(now) // MISTAKE_BLINK_MS) % 2 == 0:
                self.px(self._mistake_cell, _MISTAKE)
        elif phase == PHASE_PAUSED or phase == PHASE_RESUME:
            frame = self._frame
            for i in range(len(frame)):
                frame[i] >>= 2

    def _draw_tiles(self, now):
        bottom = self._bottom
        classic = self._mode == MODE_CLASSIC
        for y in range(portrait.HEIGHT):
            index = bottom + _BOTTOM - y
            if classic and index >= self._goal:
                if index == self._goal:
                    for x in range(portrait.WIDTH):
                        self.px(y * portrait.WIDTH + x, _FINISH)
                continue
            cell = y * portrait.WIDTH + self._lane(index)
            if index < self._next:
                self.px(cell, _TAPPED)
            elif index == 0 and self._phase == PHASE_READY and (now // START_PULSE_MS) % 2:
                self.px(cell, _START_BRIGHT)
            else:
                self.px(cell, _TILE)

    def _draw_result(self, now):
        if self._stars == 0:
            for x in range(portrait.WIDTH):
                self.px(_BOTTOM * portrait.WIDTH + x, _NO_STAR)
            return
        filled_for = self._elapsed(now) - self._stars * RESULT_STAR_STEP_MS
        if self._new_best and 0 <= filled_for < RESULT_CELEBRATION_MS and (now // 250) % 2:
            return
        for star in range(self._shown):
            y = _BOTTOM - star
            for x in range(portrait.WIDTH):
                self.px(y * portrait.WIDTH + x, _STAR)
