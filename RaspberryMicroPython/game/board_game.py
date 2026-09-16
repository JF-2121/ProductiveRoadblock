"""Base class for the portrait games: the start screen, Simon Says and Piano Tiles.

Like Pocket Guitar, the keyboard callback only queues input events. One game loop task
processes them in order, updates the game and redraws the LEDs, so nothing blocks the board.
The base class keeps the input queue, the LED frame, non-blocking vibration, BLE sending and
the back gesture: holding both mechanical keys for BACK_HOLD_MS opens the start screen. The
mechanical keys do nothing else in these games.

A subclass implements:
  enter_ready(now)                         show the ready screen (also when the game is opened)
  on_pad(cell, pressed, event_time, now)   a pad went down or up, cell 0-31 in the screen's LAYOUT
  update(now)                              timers, called on every loop
  draw(now)                                paint the frame with px()
and optionally on_mech_key(key, pressed, now) for a screen that uses the mechanical keys.
"""
import gc
import sys
import time
from array import array
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import globals
import pico_config as config
from game import portrait
from game.game_control import GameControl
from game.haptic_player import HapticPlayer

LOG_OFF = 0
LOG_INFO = 1   # phases, mistakes and results
LOG_DEBUG = 2  # additionally every pad and BLE event

LOOP_INTERVAL_MS = 10
RENDER_INTERVAL_MS = 30
FULL = 16  # px() brightness level: 16 = full colour, 4 = a quarter, 1 = 1/16

_QUEUE_SIZE = 32
_MECH_BLUE = 1
_MECH_RED = 2
_MECH_BOTH = 3


def u16(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def u32(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF))


class BoardGame(GameControl):
    """Game loop, input queue, LED frame, haptics and back gesture for the games and screens.

    LAYOUT is the picture the screen is drawn in and the cell numbers of on_pad() and px():
    portrait for the games (game/portrait.py), landscape for the MIDI screen (game/landscape.py).
    """

    LAYOUT = portrait

    __slots__ = [
        "log_level",
        "_name",
        "_haptics",
        # input queue filled by the keyboard callback
        "_queue_key",
        "_queue_action",
        "_queue_time",
        "_queue_head",
        "_queue_tail",
        "_queue_overflows",
        "_on_key_event_ref",
        # back gesture
        "_mech_down",
        "_hold_active",
        "_hold_start",
        "_hold_fired",
        # rendering
        "_frame",
        "_blank",
        "_dirty",
        "_last_render",
        "_alive",
        # LAYOUT tables, cached once: LAYOUT never changes for a given instance, and px() reads
        # KEY on every lit cell of every rendered frame - not worth re-resolving self.LAYOUT.KEY
        # each time.
        "_layout_cell",
        "_layout_key",
    ]

    def __init__(self, game_config, name):
        super().__init__(game_config, None)
        self.log_level = LOG_INFO
        self._name = name
        self._haptics = HapticPlayer(globals.haptic)
        self._layout_cell = self.LAYOUT.CELL
        self._layout_key = self.LAYOUT.KEY

        self._queue_key = bytearray(_QUEUE_SIZE)
        self._queue_action = bytearray(_QUEUE_SIZE)
        self._queue_time = array("i", [0] * _QUEUE_SIZE)
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_overflows = 0
        self._on_key_event_ref = self._on_key_event

        self._mech_down = 0
        self._hold_active = False
        self._hold_start = 0
        self._hold_fired = False

        self._frame = bytearray(config.GRID_NUM_KEYS * 3)
        self._blank = bytearray(config.GRID_NUM_KEYS * 3)
        self._dirty = True
        self._last_render = 0
        self._alive = False

    # ==========================================================================
    # GameControl interface
    # ==========================================================================
    def load_game_config(self, game_config) -> None:
        """Take over the keyboard, show the ready screen and start the game loop."""
        self._config = game_config
        if globals.keyboard:
            globals.keyboard.set_key_pressed_callback(None)
            globals.keyboard.set_key_released_callback(None)
            globals.keyboard.set_key_event_callback(self._on_key_event_ref)
        self._alive = True
        self.enter_ready(time.ticks_ms())
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    def stop_game(self) -> None:
        """Stop the game loop, release the keyboard and turn off lights and motor."""
        self._alive = False
        task = self._task
        self._task = None
        if task is not None:
            try:
                task.cancel()
            except RuntimeError:
                pass  # stopped from its own loop: the loop ends by itself
        if globals.keyboard:
            globals.keyboard.set_key_event_callback(None)
            globals.keyboard.set_color(0, 0, 0)
            globals.keyboard.show()
        self._haptics.stop()
        self._state.state = config.GAME_STATE_OVER
        self.notify_state(config.GAME_STATE_OVER)

    def reset_game(self) -> None:
        """Back to the ready screen (BLE reset)."""
        self.enter_ready(time.ticks_ms())

    def pause_game(self) -> None:
        pass

    def resume_game(self) -> None:
        pass

    def UpdateGridState(self) -> None:
        self._render(time.ticks_ms())

    def next_step(self) -> None:
        """Not used: the game loop drives the game."""
        pass

    def keyPressedCallback(self, key_or_event) -> None:
        key = getattr(key_or_event, "key", key_or_event)
        self._on_key_event(key, config.KEY_ACTION_PRESSED, time.ticks_ms())

    def win(self) -> None:
        pass

    def lose(self) -> None:
        pass

    def stats_line(self) -> str:
        return "input overflows %d, free mem %d" % (
            self._queue_overflows, gc.mem_free() if hasattr(gc, "mem_free") else -1)

    # ==========================================================================
    # Subclass hooks
    # ==========================================================================
    def enter_ready(self, now):
        raise NotImplementedError

    def on_pad(self, cell, pressed, event_time, now):
        raise NotImplementedError

    def update(self, now):
        pass

    def draw(self, now):
        raise NotImplementedError

    def on_mech_key(self, key, pressed, now):
        """A mechanical key went down or up. The games ignore it; only the back gesture counts there."""
        pass

    def on_back(self, now):
        """Both mechanical keys held: back to the start screen."""
        if self.log_level >= LOG_INFO:
            self._log("Back to the start screen.")
        from game import game_manager
        game_manager.request_open(config.GAME_ID_START_SCREEN)

    # ==========================================================================
    # Game loop
    # ==========================================================================
    async def _loop(self):
        while self._alive:
            try:
                self._tick(time.ticks_ms())
            except Exception as exc:
                print("[%s] Game loop crashed, game stopped:" % self._name)
                if hasattr(sys, "print_exception"):
                    sys.print_exception(exc)
                else:
                    import traceback
                    traceback.print_exception(exc)
                self._haptics.stop()
                self._alive = False
                self._task = None
                return
            await asyncio.sleep_ms(LOOP_INTERVAL_MS)

    def _tick(self, now):
        if globals.keyboard:
            globals.keyboard.poll()
        self._drain_input(now)
        self._update_hold(now)
        if not self._alive:
            return
        self.update(now)
        self._haptics.update(now)
        if self._dirty or time.ticks_diff(now, self._last_render) >= RENDER_INTERVAL_MS:
            self._render(now)

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

    def _drain_input(self, now):
        while self._queue_head != self._queue_tail and self._alive:
            head = self._queue_head
            key = self._queue_key[head]
            pressed = self._queue_action[head] == config.KEY_ACTION_PRESSED
            event_time = self._queue_time[head]
            self._queue_head = (head + 1) % _QUEUE_SIZE
            if key < config.GRID_NUM_KEYS:
                cell = self._layout_cell[key]
                if self.log_level >= LOG_DEBUG:
                    self._log("pad %2d %s -> x %d, y %d" % (
                        key, "down" if pressed else "up  ", cell % self.LAYOUT.WIDTH, cell // self.LAYOUT.WIDTH))
                self.on_pad(cell, pressed, event_time, now)
            elif key == config.STRUM_KEY_BLUE or key == config.STRUM_KEY_RED:
                bit = _MECH_BLUE if key == config.STRUM_KEY_BLUE else _MECH_RED
                if pressed:
                    self._mech_down |= bit
                else:
                    self._mech_down &= ~bit
                self.on_mech_key(key, pressed, now)

    def _update_hold(self, now):
        """Both mechanical keys held for BACK_HOLD_MS: on_back(), once per hold."""
        if self._mech_down == _MECH_BOTH:
            if not self._hold_active:
                self._hold_active = True
                self._hold_start = now
            elif not self._hold_fired and time.ticks_diff(now, self._hold_start) >= config.BACK_HOLD_MS:
                self._hold_fired = True
                self.on_back(now)
        else:
            self._hold_active = False
            if self._mech_down == 0:
                self._hold_fired = False

    # ==========================================================================
    # Output
    # ==========================================================================
    def _render(self, now):
        self._dirty = False
        self._last_render = now
        frame = self._frame
        frame[:] = self._blank
        self.draw(now)
        if globals.keyboard:
            globals.keyboard.write_frame(frame)

    def px(self, cell, color, level=FULL):
        """Light a cell of the screen's layout, with the colour scaled by level / 16."""
        offset = self._layout_key[cell] * 3
        frame = self._frame
        if level >= FULL:
            frame[offset] = color[0]
            frame[offset + 1] = color[1]
            frame[offset + 2] = color[2]
        else:
            frame[offset] = color[0] * level >> 4
            frame[offset + 1] = color[1] * level >> 4
            frame[offset + 2] = color[2] * level >> 4

    def set_state(self, state):
        """Set the game state and tell the app when it changed."""
        if self._state.state != state:
            self._state.state = state
            self.notify_state(state)

    def send(self, event_id, payload):
        ble_inst = getattr(globals, "bluetooth", None)
        if ble_inst and ble_inst.is_connected:
            ble_inst.send_event(event_id, payload)
        if self.log_level >= LOG_DEBUG:
            self._log("BLE event 0x%02X %s" % (event_id, payload.hex()))

    def _log(self, message):
        print("[%s] %s" % (self._name, message))
