"""Simon Says: repeat a growing sequence of colour blocks (see GAME_DESIGN.md).

Portrait board with 8 colour blocks of 2x2 pads. Simple: 8 steps, a mistake ends the run.
Endless: open end with 3 lives. The mechanical keys only do the back gesture.

BLE event BLE_EVENT_ID_SIMON_SAYS, byte 1 = subtype, then (integers little-endian):
  RUN_START    mode u8, steps u8 (0 = open end), lives u8 (0 in Simple)
  WATCH        round u8 (= sequence length), speed level u8, lives u8
  CUE          step u8, block u8, lit ms u16
  TURN         round u8, time per press ms u16
  PRESS        step u8, block u8, correct u8 (1 correct, 0 wrong)
  ROUND_CLEAR  round u8
  MISTAKE      step u8, pressed block u8 (0xFF = too slow), right block u8, lives left u8
  RESULT       mode u8, score u8, best u8, flags u8 (bit 0 new best, bit 1 won)
"""
import time
import pico_config as config
from ble_handler.config import (
    BLE_EVENT_ID_SIMON_SAYS, BLE_SIMON_RUN_START, BLE_SIMON_WATCH, BLE_SIMON_CUE, BLE_SIMON_TURN,
    BLE_SIMON_PRESS, BLE_SIMON_ROUND_CLEAR, BLE_SIMON_MISTAKE, BLE_SIMON_RESULT,
)
from game import portrait
from game.best_scores import BestScores
from game.board_game import BoardGame, FULL, LOG_INFO, LOG_DEBUG, u16
from game.haptic_player import (
    PRIORITY_TICK, PRIORITY_ALMOST, PRIORITY_ACCENT, PRIORITY_MULTIPLIER, PRIORITY_MISS, PRIORITY_SYSTEM,
)
from game.utils import GameConfig
from random_number_generator import RandomNumberGenerator

MODE_SIMPLE = config.SIMON_SAYS_MODE_SIMPLE
MODE_ENDLESS = config.SIMON_SAYS_MODE_ENDLESS
_MODE_NAMES = ("Simple", "Endless")
_SCORE_KEYS = ("simon:simple", "simon:endless")

SIMPLE_STEPS = 8
ENDLESS_LIVES = 3
MAX_SEQUENCE = 99
BLOCKS = 8

PHASE_READY = 0
PHASE_LIVES = 1
PHASE_WATCH = 2
PHASE_TURN = 3
PHASE_CLEAR = 4
PHASE_MISTAKE = 5
PHASE_RESULT = 6
PHASE_PAUSED = 7

LEAD_IN_MS = 800             # dimmed board before the first step is shown
PRESS_TIME_MS = 5000
PRESS_FLASH_MS = 180         # a correct press lights its block at least this long
CLEAR_PAUSE_MS = 500
MISTAKE_RED_MS = 500
MISTAKE_BLINK_MS = 130
MISTAKE_MS = MISTAKE_RED_MS + 6 * MISTAKE_BLINK_MS + 200
MISTAKE_BUZZ_MS = 300
LIVES_START_MS = 1500
LIVES_LOST_MS = 2000
LIFE_BLINK_MS = 150
NOT_NOW_MS = 500
RESULT_INPUT_LOCK_MS = 1500
RESULT_CELL_MS = 80
RESULT_CELEBRATION_MS = 2500
BREATH_STEP_MS = 150

# Speed by sequence length: faster after 5, 9 and 13 steps, like the original Simon
_SPEED_AFTER = (5, 9, 13)
_CUE_ON_MS = (520, 420, 340, 280)
_CUE_GAP_MS = (180, 150, 120, 100)

# DRV2605L library effects, see GAME_DESIGN.md section 9
_FX_GESTURE = 7      # Soft Bump 100 %
_FX_TURN = 8         # Soft Bump 60 %
_FX_NOT_NOW = 9      # Soft Bump 30 %
_FX_CLEAR = 10       # Double Click 100 %
_FX_WON = 12         # Triple Click 100 %
_FX_PRESS = 25       # Sharp Tick 2 80 %
_FX_TICK = 26        # Sharp Tick 3 60 %
_FX_MISTAKE = 47     # Buzz 1 100 %
_FX_NEW_BEST = 82    # Transition Ramp Up Long Smooth 1

# Vibration priorities: mistake > round done > your turn > correct press > ticks
_PRIO_TICK = PRIORITY_TICK
_PRIO_PRESS = PRIORITY_ALMOST
_PRIO_TURN = PRIORITY_ACCENT
_PRIO_CLEAR = PRIORITY_MULTIPLIER
_PRIO_MISTAKE = PRIORITY_MISS
_PRIO_SYSTEM = PRIORITY_SYSTEM

_BLOCK_COLORS = (
    (255, 0, 0),      # 0 red
    (0, 255, 0),      # 1 green
    (0, 60, 255),     # 2 blue
    (255, 200, 0),    # 3 yellow
    (255, 0, 200),    # 4 magenta
    (0, 220, 255),    # 5 cyan
    (255, 90, 0),     # 6 orange
    (200, 200, 200),  # 7 white
)
_RED = (255, 0, 0)
_LIFE_COLOR = (200, 0, 0)
_BEST_MARKER = (30, 30, 30)
_RAINBOW = ((255, 0, 0), (255, 120, 0), (255, 255, 0), (0, 255, 0),
            (0, 255, 255), (0, 0, 255), (140, 0, 255), (255, 0, 160))
_BREATH_LEVELS = (1, 2, 3, 4, 5, 6, 5, 4, 3, 2)  # READY, in 1/16 of full brightness
_LEVEL_WATCH = 2
_LEVEL_TURN = 4
_LEVEL_PAUSED = 1
_LEVEL_RESULT = 8

# 2x2 blocks: block = (y // 2) * 2 + x // 2
_BLOCK_OF_CELL = bytes([(cell // portrait.WIDTH // 2) * 2 + (cell % portrait.WIDTH) // 2
                        for cell in range(portrait.CELLS)])
_BLOCK_CELLS = tuple(tuple(c for c in range(portrait.CELLS) if _BLOCK_OF_CELL[c] == b) for b in range(BLOCKS))
# Life bars: life 1 = rows 6-7, life 2 = rows 3-4, life 3 = rows 0-1
_LIFE_ROWS = ((6, 7), (3, 4), (0, 1))
_TOO_SLOW = 0xFF


class SimonSaysControl(BoardGame):
    """Simon Says with Simple (8 steps) and Endless (3 lives) mode."""

    __slots__ = [
        "cue_tick",
        "_mode",
        "_steps",
        "_lives",
        "_fixed",
        "_rng",
        "_sequence",
        "_length",
        "_scores",
        "_best",
        # phase
        "_phase",
        "_phase_start",
        "_paused_phase",
        "_lives_lost",
        # sequence playback
        "_round",
        "_cue",
        "_cue_on",
        "_next_cue_at",
        # player's turn
        "_step",
        "_deadline",
        "_held",
        "_lit",
        "_flash_block",
        "_flash_until",
        "_last_not_now",
        "_mistake_pressed",
        "_mistake_right",
        # result
        "_score",
        "_new_best",
        "_won",
        "_shown",
    ]

    def __init__(self, mode=MODE_SIMPLE, game_config=None):
        super().__init__(game_config or GameConfig(game_id=config.GAME_ID_SIMON_SAYS), "SimonSays")
        self.cue_tick = True
        self._mode = mode
        # A generated config (app seed) fixes the sequence; otherwise every run is new
        steps = self._config.steps
        self._fixed = bytes([s.pads[0] % BLOCKS for s in steps if s.pads]) if steps else None
        if mode == MODE_ENDLESS:
            self._steps = MAX_SEQUENCE
        else:
            self._steps = min(len(self._fixed), MAX_SEQUENCE) if self._fixed else SIMPLE_STEPS
        self._lives = 0
        self._rng = RandomNumberGenerator()
        self._sequence = bytearray(MAX_SEQUENCE)
        self._length = 0
        self._scores = BestScores()
        self._best = self._scores.get(_SCORE_KEYS[mode]) or 0

        self._phase = PHASE_READY
        self._phase_start = 0
        self._paused_phase = PHASE_READY
        self._lives_lost = False

        self._round = 0
        self._cue = 0
        self._cue_on = False
        self._next_cue_at = 0

        self._step = 0
        self._deadline = 0
        self._held = bytearray(BLOCKS)
        self._lit = bytearray(BLOCKS)
        self._flash_block = -1
        self._flash_until = 0
        self._last_not_now = 0
        self._mistake_pressed = _TOO_SLOW
        self._mistake_right = 0

        self._score = 0
        self._new_best = False
        self._won = False
        self._shown = 0

    # ==========================================================================
    # GameControl interface
    # ==========================================================================
    def start_game(self) -> None:
        """Start a run (BLE start)."""
        if self._phase in (PHASE_READY, PHASE_RESULT):
            self._start_run(time.ticks_ms())

    def pause_game(self) -> None:
        if self._phase in (PHASE_LIVES, PHASE_WATCH, PHASE_TURN, PHASE_CLEAR, PHASE_MISTAKE):
            now = time.ticks_ms()
            self._paused_phase = self._phase
            self._haptics.stop()
            self._haptics.play(_FX_GESTURE, _PRIO_SYSTEM, 60)
            self._set_phase(PHASE_PAUSED, now)
            self.set_state(config.GAME_STATE_PAUSED)
            if self.log_level >= LOG_INFO:
                self._log("PAUSED. Press any pad or resume from the app.")

    def resume_game(self) -> None:
        if self._phase != PHASE_PAUSED:
            return
        now = time.ticks_ms()
        self._haptics.play(_FX_GESTURE, _PRIO_SYSTEM, 60)
        self.set_state(config.GAME_STATE_RUNNING)
        if self.log_level >= LOG_INFO:
            self._log("RESUME")
        if self._paused_phase == PHASE_MISTAKE:
            self._after_mistake(now)
        else:
            self._enter_watch(now)  # the round starts again

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
        self._haptics.stop()
        self._set_phase(PHASE_READY, now)
        self.set_state(config.GAME_STATE_READY)
        if self.log_level >= LOG_INFO:
            rule = "%d steps" % self._steps if self._mode == MODE_SIMPLE else "%d lives" % ENDLESS_LIVES
            self._log("===== READY: Simon Says %s (%s), best %d. Press any pad to start. =====" % (
                _MODE_NAMES[self._mode], rule, self._best))

    def _start_run(self, now):
        self._round = 1
        self._score = 0
        self._length = 0
        self._new_best = False
        self._won = False
        self._lives = ENDLESS_LIVES if self._mode == MODE_ENDLESS else 0
        self._haptics.stop()
        self._haptics.play(_FX_GESTURE, _PRIO_SYSTEM, 60)
        self._state.score = 0
        self.set_state(config.GAME_STATE_RUNNING)
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((
            BLE_SIMON_RUN_START, self._mode, 0 if self._mode == MODE_ENDLESS else self._steps, self._lives)))
        if self.log_level >= LOG_INFO:
            self._log("===== START %s =====" % _MODE_NAMES[self._mode].upper())
        if self._mode == MODE_ENDLESS:
            self._enter_lives(now, False)
        else:
            self._enter_watch(now)

    def _enter_lives(self, now, lost):
        self._lives_lost = lost
        self._set_phase(PHASE_LIVES, now)
        if self.log_level >= LOG_INFO:
            self._log("lives: %d" % self._lives)

    def _enter_watch(self, now):
        self._set_phase(PHASE_WATCH, now)
        self._cue = 0
        self._cue_on = False
        self._next_cue_at = time.ticks_add(now, LEAD_IN_MS)
        self._last_not_now = time.ticks_add(now, -NOT_NOW_MS)
        self._step = 0
        self._flash_block = -1
        for block in range(BLOCKS):
            self._lit[block] = 0
        level = self._speed_level()
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_WATCH, self._round, level, self._lives)))
        if self.log_level >= LOG_INFO:
            self._log("round %d: watch (speed %d)" % (self._round, level))

    def _enter_turn(self, now):
        self._set_phase(PHASE_TURN, now)
        self._step = 0
        self._deadline = time.ticks_add(now, PRESS_TIME_MS)
        self._haptics.play(_FX_TURN, _PRIO_TURN, 60)
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_TURN, self._round)) + u16(PRESS_TIME_MS))
        if self.log_level >= LOG_INFO:
            self._log("round %d: your turn" % self._round)

    def _speed_level(self):
        level = 0
        for length in _SPEED_AFTER:
            if self._round > length:
                level += 1
        return level

    def _block(self, index):
        """Block of step `index`. The sequence grows on demand and never changes during a run."""
        sequence = self._sequence
        fixed = self._fixed
        while self._length <= index:
            i = self._length
            if fixed is not None and i < len(fixed):
                block = fixed[i]
            else:
                block = self._rng.randint(0, BLOCKS - 1)
                if i >= 2 and sequence[i - 1] == block and sequence[i - 2] == block:
                    block = (block + 1 + self._rng.randint(0, BLOCKS - 2)) % BLOCKS
            sequence[i] = block
            self._length = i + 1
        return sequence[index]

    # ==========================================================================
    # Game loop hooks
    # ==========================================================================
    def update(self, now):
        phase = self._phase
        if phase == PHASE_WATCH:
            self._update_watch(now)
        elif phase == PHASE_TURN:
            if time.ticks_diff(now, self._deadline) >= 0:
                self._mistake(_TOO_SLOW, now)
        elif phase == PHASE_CLEAR:
            if self._elapsed(now) >= CLEAR_PAUSE_MS:
                self._enter_watch(now)
        elif phase == PHASE_LIVES:
            if self._elapsed(now) >= (LIVES_LOST_MS if self._lives_lost else LIVES_START_MS):
                self._enter_watch(now)
        elif phase == PHASE_MISTAKE:
            if self._elapsed(now) >= MISTAKE_MS:
                self._after_mistake(now)
        elif phase == PHASE_RESULT:
            self._update_result(now)

    def _update_watch(self, now):
        if time.ticks_diff(now, self._next_cue_at) < 0:
            return
        level = self._speed_level()
        self._dirty = True
        if self._cue_on:
            self._cue_on = False
            self._cue += 1
            if self._cue >= self._round:
                self._enter_turn(now)
                return
            self._next_cue_at = time.ticks_add(self._next_cue_at, _CUE_GAP_MS[level])
        else:
            self._cue_on = True
            block = self._block(self._cue)
            self._next_cue_at = time.ticks_add(self._next_cue_at, _CUE_ON_MS[level])
            if self.cue_tick:
                self._haptics.play(_FX_TICK, _PRIO_TICK, 30)
            self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_CUE, self._cue, block)) + u16(_CUE_ON_MS[level]))
            if self.log_level >= LOG_DEBUG:
                self._log("  step %d: block %d" % (self._cue + 1, block))

    def on_pad(self, cell, pressed, event_time, now):
        block = _BLOCK_OF_CELL[cell]
        held = self._held
        if not pressed:
            if held[block]:
                held[block] -= 1
                if held[block] == 0 and self._lit[block]:
                    self._lit[block] = 0
                    self._dirty = True
            return

        was_held = held[block]
        if was_held < 4:
            held[block] = was_held + 1
        phase = self._phase
        if phase == PHASE_TURN:
            if not was_held:
                self._judge(block, now)
        elif phase == PHASE_READY:
            self._start_run(now)
        elif phase == PHASE_RESULT:
            if self._elapsed(now) >= RESULT_INPUT_LOCK_MS:
                self._start_run(now)
        elif phase == PHASE_WATCH:
            if time.ticks_diff(now, self._last_not_now) >= NOT_NOW_MS:
                self._last_not_now = now
                self._haptics.play(_FX_NOT_NOW, _PRIO_TICK, 40)
        elif phase == PHASE_PAUSED:
            self.resume_game()

    # ==========================================================================
    # Judgement
    # ==========================================================================
    def _judge(self, block, now):
        step = self._step
        if block != self._block(step):
            self._mistake(block, now)
            return

        self._lit[block] = 1
        self._flash_block = block
        self._flash_until = time.ticks_add(now, PRESS_FLASH_MS)
        self._dirty = True
        self._haptics.play(_FX_PRESS, _PRIO_PRESS, 40)
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_PRESS, step, block, 1)))
        self._step = step + 1
        self._deadline = time.ticks_add(now, PRESS_TIME_MS)
        if self._step < self._round:
            return

        self._score = self._round
        self._state.score = self._score
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_ROUND_CLEAR, self._round)))
        if self.log_level >= LOG_INFO:
            self._log("round %d done" % self._round)
        if self._round >= self._steps:
            self._finish(now, True)
            return
        self._round += 1
        self._set_phase(PHASE_CLEAR, now)
        self._haptics.play(_FX_CLEAR, _PRIO_CLEAR, 120)

    def _mistake(self, pressed, now):
        step = self._step
        right = self._block(step)
        if pressed != _TOO_SLOW:
            self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_PRESS, step, pressed, 0)))
        if self._mode == MODE_ENDLESS:
            self._lives -= 1
        self._mistake_pressed = pressed
        self._mistake_right = right
        self._flash_block = -1
        self._set_phase(PHASE_MISTAKE, now)
        self._haptics.play(_FX_MISTAKE, _PRIO_MISTAKE, MISTAKE_BUZZ_MS, cut=True)
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_MISTAKE, step, pressed, right, self._lives)))
        if self.log_level >= LOG_INFO:
            what = "too slow" if pressed == _TOO_SLOW else "pressed block %d" % pressed
            self._log("MISTAKE at step %d of round %d: %s, right block %d. Lives left: %d" % (
                step + 1, self._round, what, right, self._lives))

    def _after_mistake(self, now):
        if self._mode == MODE_ENDLESS and self._lives > 0:
            self._enter_lives(now, True)  # then the same round again
        else:
            self._finish(now, False)

    # ==========================================================================
    # Result
    # ==========================================================================
    def _finish(self, now, won):
        score = self._score
        self._won = won
        self._new_best = score > 0 and self._scores.submit(_SCORE_KEYS[self._mode], score)
        if self._new_best:
            self._best = score
        self._shown = 0
        self._haptics.stop()
        self._set_phase(PHASE_RESULT, now)
        self._state.score = score
        self.set_state(config.GAME_STATE_WIN if won else config.GAME_STATE_OVER)
        self.notify_score(score)
        flags = (1 if self._new_best else 0) | (2 if won else 0)
        self.send(BLE_EVENT_ID_SIMON_SAYS, bytes((BLE_SIMON_RESULT, self._mode, score, self._best, flags)))
        if won:
            self._haptics.play(_FX_WON, _PRIO_SYSTEM, 220)
        if self.log_level >= LOG_INFO:
            self._log("===== RESULT: %s, score %d%s, best %d%s =====" % (
                _MODE_NAMES[self._mode], score, " (WON)" if won else "", self._best,
                ", NEW PERSONAL BEST!" if self._new_best else ""))
            self._log("Press any pad to play again.")

    def _update_result(self, now):
        total = min(self._score, portrait.CELLS)
        shown = min(total, self._elapsed(now) // RESULT_CELL_MS)
        if shown != self._shown:
            self._shown = shown
            self._dirty = True
            self._haptics.play(_FX_TICK, _PRIO_TICK, 30)
            if shown == total and self._new_best:
                self._haptics.play(_FX_NEW_BEST, _PRIO_SYSTEM, 600, cut=True)

    # ==========================================================================
    # Rendering
    # ==========================================================================
    def draw(self, now):
        phase = self._phase
        if phase == PHASE_READY:
            self._draw_map(_BREATH_LEVELS[(now // BREATH_STEP_MS) % len(_BREATH_LEVELS)])
        elif phase == PHASE_WATCH:
            self._draw_map(_LEVEL_WATCH)
            if self._cue_on:
                self._draw_block(self._sequence[self._cue], FULL)
        elif phase == PHASE_TURN or phase == PHASE_CLEAR:
            self._draw_map(_LEVEL_TURN)
            flash = self._flash_block
            if flash >= 0 and time.ticks_diff(self._flash_until, now) <= 0:
                flash = -1
            for block in range(BLOCKS):
                if self._lit[block] or block == flash:
                    self._draw_block(block, FULL)
        elif phase == PHASE_LIVES:
            self._draw_lives(now)
        elif phase == PHASE_MISTAKE:
            elapsed = self._elapsed(now)
            if elapsed < MISTAKE_RED_MS:
                if self._mistake_pressed != _TOO_SLOW:
                    for cell in _BLOCK_CELLS[self._mistake_pressed]:
                        self.px(cell, _RED)
            else:
                blink = (elapsed - MISTAKE_RED_MS) // MISTAKE_BLINK_MS
                if blink < 6 and blink % 2 == 0:
                    self._draw_block(self._mistake_right, FULL)
        elif phase == PHASE_RESULT:
            self._draw_result(now)
        elif phase == PHASE_PAUSED:
            self._draw_map(_LEVEL_PAUSED)

    def _draw_map(self, level):
        for cell in range(portrait.CELLS):
            self.px(cell, _BLOCK_COLORS[_BLOCK_OF_CELL[cell]], level)

    def _draw_block(self, block, level):
        color = _BLOCK_COLORS[block]
        for cell in _BLOCK_CELLS[block]:
            self.px(cell, color, level)

    def _draw_lives(self, now):
        elapsed = self._elapsed(now)
        for life in range(ENDLESS_LIVES):
            if life < self._lives:
                on = True
            elif life == self._lives and self._lives_lost:
                blink = elapsed // LIFE_BLINK_MS
                on = blink < 6 and blink % 2 == 0
            else:
                on = False
            if on:
                for y in _LIFE_ROWS[life]:
                    for x in range(portrait.WIDTH):
                        self.px(y * portrait.WIDTH + x, _LIFE_COLOR)

    def _draw_result(self, now):
        elapsed = self._elapsed(now)
        total = min(self._score, portrait.CELLS)
        filled_for = elapsed - total * RESULT_CELL_MS
        celebrate = 0 <= filled_for < RESULT_CELEBRATION_MS
        if celebrate and self._won:
            shift = now // 100
            for cell in range(portrait.CELLS):
                self.px(cell, _RAINBOW[(cell // portrait.WIDTH + shift) % len(_RAINBOW)])
            return
        if celebrate and self._new_best and (now // 250) % 2:
            return
        for cell in range(self._shown):
            self.px(cell, _BLOCK_COLORS[_BLOCK_OF_CELL[cell]], _LEVEL_RESULT)
        if filled_for >= 0 and self._score < self._best <= portrait.CELLS:
            self.px(self._best - 1, _BEST_MARKER)
