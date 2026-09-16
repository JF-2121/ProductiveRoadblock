import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import I2C, Pin
import pico_config as config
from ble_handler.config import BLE_EVENT_ID_KEY_PRESS, BLE_KEY_PRESS, BLE_KEY_RELEASE
import micropython
import globals

from keyboard.neotrellis import NeoTrellis
from keyboard.utils import *

class Keyboard:
    __slots__ = (
        "_neo_trellis_boards",
        "_keyPressedCallback",
        "_keyReleasedCallback",
        "_keyEventCallback",
        "_colors",
        "_shown",
        "_scaled",
        "_brightness",
        "_mech_down",
        "_mech_changed_ms",
        "_process_boards_ref",
        "_boards_scheduled",
        "_boards_polled_ms",
        )

    def __init__(self):
        self._keyPressedCallback = None
        self._keyReleasedCallback = None
        self._keyEventCallback = None

        self._neo_trellis_boards = []
        i2c = I2C(config.NEOTRELLIS_I2C_PORT, scl=config.NEOTRELLIS_I2C_SCL_PIN, sda=config.NEOTRELLIS_I2C_SDA_PIN, freq=config.NEOTRELLIS_I2C_FREQ)
        self._neo_trellis_boards.append(NeoTrellis(i2c, config.NEOTRELLIS_I2C_ADDR_1, board_index=0, key_callback=self._handle_key_event))
        self._neo_trellis_boards.append(NeoTrellis(i2c, config.NEOTRELLIS_I2C_ADDR_2, board_index=1, key_callback=self._handle_key_event))

        # Debounced state of the mechanical keys (index 0 = MECH_KEY_1 = key 32, 1 = MECH_KEY_2 = key 33)
        self._mech_down = bytearray(2)
        self._mech_changed_ms = [0, 0]
        self._mech_down[0] = 1 if config.MECH_KEY_1.value() == 0 else 0
        self._mech_down[1] = 1 if config.MECH_KEY_2.value() == 0 else 0

        # Bound method created once, so scheduling it from the IRQ does not allocate
        self._process_boards_ref = self._process_boards
        self._boards_scheduled = False
        self._boards_polled_ms = time.ticks_ms()

        # Set up Interrupts for NeoTrellis and mechanical keys
        config.NEOTRELLIS_INT_PIN.irq(trigger=Pin.IRQ_FALLING, handler=self._irq_handler)
        config.MECH_KEY_1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_handler)
        config.MECH_KEY_2.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_handler)

        # 3 bytes (R, G, B) per key. _colors is the cached grid, _shown what the LEDs currently display
        # (both before brightness scaling), _scaled a work buffer for dimmed rows.
        self._colors = bytearray(config.GRID_NUM_KEYS * 3)
        self._shown = bytearray(config.GRID_NUM_KEYS * 3)
        self._scaled = bytearray(config.GRID_NUM_KEYS * 3)
        self._brightness = 255
        self.set_grid_color(self._colors)

    # Soft IRQ context: runs shortly after the edge, so ticks_ms() is an accurate event time
    def _irq_handler(self, pin):
        if pin == config.NEOTRELLIS_INT_PIN:
            self._schedule_boards()
        elif pin == config.MECH_KEY_1:
            self._update_mech_key(0, pin.value() == 0, time.ticks_ms(), "irq")
        elif pin == config.MECH_KEY_2:
            self._update_mech_key(1, pin.value() == 0, time.ticks_ms(), "irq")

    def _schedule_boards(self):
        # Board reads always run as scheduled callbacks: they never nest, so the two-step I2C
        # register reads of one board can't interleave.
        if self._boards_scheduled:
            return
        try:
            micropython.schedule(self._process_boards_ref, None)
            self._boards_scheduled = True
        except RuntimeError:
            pass  # schedule queue full: poll() tries again while the line stays low

    def _process_boards(self, _):
        self._boards_scheduled = False
        # Both boards share one active-low interrupt line: an event on one board while the other
        # is read keeps the line low without a new falling edge, so read again while it is low.
        for _ in range(config.NEOTRELLIS_IRQ_DRAIN_LIMIT):
            for board in self._neo_trellis_boards:
                board.process_events()
            if config.NEOTRELLIS_INT_PIN.value():
                return

    def poll(self):
        """Call regularly (every few ms) from a game loop: re-reads the mechanical keys, and reads the
        pads when their interrupt line is low but no read is pending. Without this, a lost interrupt
        edge (full schedule queue, I2C error) would leave the line low and the pads silent for good."""
        self.poll_mech_keys()
        if not self._boards_scheduled and config.NEOTRELLIS_INT_PIN.value() == 0:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._boards_polled_ms) >= config.NEOTRELLIS_POLL_MS:
                self._boards_polled_ms = now
                self._schedule_boards()

    def _update_mech_key(self, index, pressed, now, source):
        since_change = time.ticks_diff(now, self._mech_changed_ms[index])
        if pressed == (self._mech_down[index] == 1):
            # if config.MECH_KEY_DEBUG_LOG and source == "irq":
            #     print("[MechKey] key %d %-8s t=%d  +%d ms  ignored: no state change" % (
            #         32 + index, "pressed" if pressed else "released", now, since_change))
            return
        # Edges right after an accepted change are contact bounce. A real edge that gets
        # dropped here is picked up later by poll_mech_keys().
        if since_change < config.MECH_KEY_DEBOUNCE_MS:
            # if config.MECH_KEY_DEBUG_LOG and source == "irq":
            #     print("[MechKey] key %d %-8s t=%d  +%d ms  ignored: bounce" % (
            #         32 + index, "pressed" if pressed else "released", now, since_change))
            return
        if config.MECH_KEY_DEBUG_LOG:
            print("[MechKey] key %d %-8s t=%d  +%d ms  accepted (%s)" % (
                32 + index, "PRESSED" if pressed else "RELEASED", now, since_change, source))
        self._mech_down[index] = 1 if pressed else 0
        self._mech_changed_ms[index] = now
        action = config.KEY_ACTION_PRESSED if pressed else config.KEY_ACTION_RELEASED
        self._handle_key_event(KeyEvent(action=action, key=32 + index, time=now))

    def poll_mech_keys(self):
        """Re-read the mechanical keys and emit any change the debounce filter swallowed.

        Call this regularly (every few ms) from a game loop that needs exact key state.
        """
        now = time.ticks_ms()
        self._update_mech_key(0, config.MECH_KEY_1.value() == 0, now, "poll")
        self._update_mech_key(1, config.MECH_KEY_2.value() == 0, now, "poll")

    def _handle_midi_key_event(self, key, pressed, event_time):
        """Handle a key event while a MIDI host is connected. `key` must already be in the
        same space the layout arrays use: landscape cell 0-31 for pads, 32/33 for the
        mechanical keys unchanged (see the conversion in _handle_key_event below)."""
        if globals.midiboard_mode != config.BOARD_MODE_MIDI:
            return
        midi_layout = getattr(globals, "midi_layout", None)
        if midi_layout is None:
            return

        # Update the layout state (toggle, octave, channel, layout select, menu actions) *before*
        # building the message, so e.g. a toggle-mode CC's value reflects this press, not the
        # previous one. on_pad() (queued, processed later) only reads this state for the pad's
        # visuals - it must not call key_pressed() again, or every toggle would flip twice.
        if midi_layout.key_pressed(key, pressed):
            return  # the key loaded another layout, where its number means something else
        message = midi_layout.get_midi_message(key, pressed)  # menu keys return None: the menu sends no MIDI
        if message:
            ble_inst = getattr(globals, "bluetooth", None)
            if ble_inst:
                ble_inst.send_midi(message, event_time)

    def _handle_key_event(self, event, board_index=None):
        key = board_to_grid(board_index, event.key) if board_index is not None else event.key
        action = event.action
        event_time = event.time if event.time is not None else time.ticks_ms()
        pressed = action == config.KEY_ACTION_PRESSED

        ble_inst = getattr(globals, "bluetooth", None)
        if ble_inst and ble_inst.is_connected:
            if globals.midiboard_mode == config.BOARD_MODE_MIDI:
                # MIDI layouts are indexed by the active screen's LAYOUT cell (landscape for the
                # MIDI screen, see game/midi_screen.py / game/landscape.py) - the mechanical keys
                # (32/33) need no conversion, LAYOUT.CELL only covers the 32 pads. globals.game is
                # always the MidiScreen here: game_manager refuses to open any other game while
                # midiboard_mode is MIDI.
                layout_key = globals.game.LAYOUT.CELL[key] if key < config.GRID_NUM_KEYS else key
                self._handle_midi_key_event(layout_key, pressed, event_time)
            else:
                sub_code = BLE_KEY_PRESS if pressed else BLE_KEY_RELEASE
                ble_inst.send_event(BLE_EVENT_ID_KEY_PRESS, bytes([sub_code, key]))

        if self._keyEventCallback:
            self._keyEventCallback(key, action, event_time)

        if action == config.KEY_ACTION_PRESSED:
            if self._keyPressedCallback:
                self._keyPressedCallback(key)
        elif action == config.KEY_ACTION_RELEASED:
            if self._keyReleasedCallback:
                self._keyReleasedCallback(key)

    def show(self):
        for board in self._neo_trellis_boards:
            board.show()

    """
    Set the color of a specific key in the 4x8 grid to RGB values.
    This method updates the color of the specified key on the appropriate NeoTrellis board and caches the color state in the `_colors` bytearray.
    """
    def set_key_color(self, key: int, r: int, g: int, b: int):
        if not 0 <= key < config.GRID_NUM_KEYS:
            return  # e.g. the mechanical keys 32 and 33 have no LED
        board_index, local_key = grid_to_board(key)
        if board_index is not None:
            self._neo_trellis_boards[board_index].set_pixel_color(local_key, self._dim(r), self._dim(g), self._dim(b))

        offset = key * 3
        self._colors[offset] = r
        self._colors[offset + 1] = g
        self._colors[offset + 2] = b
        self._shown[offset] = r
        self._shown[offset + 1] = g
        self._shown[offset + 2] = b

    """
    Get the RGB color of a specific key in the 4x8 grid.
    This method retrieves the cached color state from the `_colors` bytearray for the specified key.
    """
    def get_key_color(self, key: int):
        offset = key * 3
        return self._colors[offset], self._colors[offset + 1], self._colors[offset + 2]

    """
    Set the color of the entire 4x8 grid to RGB Values in the colors bytearray (3 bytes per key * 32 keys => 96 bytes).
    This method updates the color of all keys on both NeoTrellis boards and caches the color state in the `_colors` bytearray.
    """
    def set_grid_color(self, colors: bytearray):
        if colors is not self._colors:
            self._colors[:] = colors
        for key in range(config.GRID_NUM_KEYS):
            r = colors[key * 3]
            g = colors[key * 3 + 1]
            b = colors[key * 3 + 2]
            board_index, local_key = grid_to_board(key)
            if board_index is not None:
                self._neo_trellis_boards[board_index].set_pixel_color(local_key, self._dim(r), self._dim(g), self._dim(b))
        self._shown[:] = self._colors

    """
    LED brightness 0-255 for everything shown from now on. What is shown is redrawn right away.
    """
    def set_brightness(self, level: int):
        level = max(0, min(255, level))
        if level == self._brightness:
            return
        self._brightness = level
        frame = bytearray(self._shown)
        for i in range(len(frame)):
            self._shown[i] = frame[i] ^ 0xFF  # every row differs, so write_frame() sends all of them
        self.write_frame(frame)

    def get_brightness(self):
        return self._brightness

    def _dim(self, value):
        return (value * (self._brightness + 1)) >> 8

    """
    Show a complete frame (3 bytes RGB per key, 96 bytes) and call show() on the boards.
    Only rows that differ from what the LEDs currently display are sent, one I2C transaction per row,
    which keeps redraws fast enough for animations.
    """
    def write_frame(self, frame: bytearray):
        shown = self._shown
        if frame == shown:
            return
        cols = config.NEOTRELLIS_NUM_COLS
        for board_index, board in enumerate(self._neo_trellis_boards):
            board_changed = False
            for row in range(config.GRID_NUM_ROWS):
                first = (row * config.GRID_NUM_COLS + board_index * cols) * 3
                last = first + cols * 3
                i = first
                while i < last and frame[i] == shown[i]:
                    i += 1
                if i == last:
                    continue
                if self._brightness == 255:
                    board.set_pixel_colors(row * cols, frame, first, cols)
                else:
                    scaled = self._scaled
                    factor = self._brightness + 1
                    for j in range(first, last):
                        scaled[j] = (frame[j] * factor) >> 8
                    board.set_pixel_colors(row * cols, scaled, first, cols)
                for j in range(first, last):
                    shown[j] = frame[j]
                board_changed = True
            if board_changed:
                board.show()
        self._colors[:] = frame

    """
    Get the cached color state of the entire 4x8 grid.
    This method returns the `_colors` bytearray, which contains the RGB values for all keys in the grid (3 bytes per key * 32 keys => 96 bytes).
    """
    def get_grid_color(self):
        return self._colors

    """
    Set the color of the entire 4x8 grid to a specific RGB value.
    This method updates the color of all keys on both NeoTrellis boards and caches the color state in the `_colors` bytearray.
    """
    def set_color(self, r, g, b):
        """Light the whole 4x8 grid on both boards."""
        for board in self._neo_trellis_boards:
            for key in range(config.NEOTRELLIS_NUM_KEYS):
                board.set_pixel_color(key, self._dim(r), self._dim(g), self._dim(b))
        # Update the cached color grid
        for key in range(config.GRID_NUM_KEYS):
            offset = key * 3
            self._colors[offset] = r
            self._colors[offset + 1] = g
            self._colors[offset + 2] = b
        self._shown[:] = self._colors

    """
    Flash the whole 4x8 grid on both boards with a specific RGB color for a duration in ms.
    """
    def flash_color(self, r, g, b, duration_ms=500, repeat=1, reset_color=None):
        asyncio.create_task(self._flash_grid(r, g, b, duration_ms, repeat, reset_color))

    async def _flash_grid(self, r, g, b, duration_ms, repeat, reset_color=None):
        for _ in range(repeat):
            self.set_color(r, g, b)
            await asyncio.sleep_ms(duration_ms)
            self.set_color(0, 0, 0)  # Turn off after flashing
            await asyncio.sleep_ms(duration_ms)

        if reset_color is not None:
            self.set_color(*reset_color)
        else:
            self.set_grid_color(self._colors)  # Reset to the cached color grid

    def set_key_pressed_callback(self, callback):
        self._keyPressedCallback = callback

    def set_key_released_callback(self, callback):
        self._keyReleasedCallback = callback

    def set_key_event_callback(self, callback):
        """Register callback(key, action, time_ms) for presses and releases, with the time the event was detected."""
        self._keyEventCallback = callback


    # TODO: Add Display Method for String Representation of the Grid, if needed in the future.
    def display(self):
        """Display the current state of the grid. This is a placeholder for future implementation."""
        pass
