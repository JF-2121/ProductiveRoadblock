from machine import I2C
import time
import pico_config as config
from keyboard.utils import *

"""MicroPython NeoTrellis driver.

This is a direct port of the C helper used in the Pico project. It keeps the
same seesaw register layout, keypad edge handling, and NeoPixel buffer format.

Two 4x4 boards sit side by side on the same I2C bus. The A0 jumper picks the
address: open = 0x2E, bridged = 0x2F. On this rig the A0-bridged board sits on
the left, so 0x2F is the left half of the grid and 0x2E the right half. Together
they form one 4x8 grid, numbered row by row from the top left across both.
"""

#SEESAW Register Constants
SEESAW_STATUS_BASE = const(0x00)
SEESAW_NEOPIXEL_BASE = const(0x0E)
SEESAW_KEYPAD_BASE = const(0x10)

SEESAW_STATUS_HW_ID = const(0x01)
SEESAW_STATUS_SWRST = const(0x7F)
SEESAW_HW_ID_CODE_SAMD09 = const(0x55)

SEESAW_NEOPIXEL_PIN = const(0x01)
SEESAW_NEOPIXEL_SPEED = const(0x02)
SEESAW_NEOPIXEL_BUF_LENGTH = const(0x03)
SEESAW_NEOPIXEL_BUF = const(0x04)
SEESAW_NEOPIXEL_SHOW = const(0x05)

SEESAW_KEYPAD_EVENT = const(0x01)
SEESAW_KEYPAD_INTENSET = const(0x02)
SEESAW_KEYPAD_COUNT = const(0x04)
SEESAW_KEYPAD_FIFO = const(0x10)

NEOTRELLIS_NEOPIX_PIN = const(3)
SEESAW_INTER_TRANSACTION_DELAY_US = const(1000)
SEESAW_I2C_TIMEOUT_US = const(50000)

# The seesaw keypad numbers its keys in rows of 8 (row * 8 + column), the NeoTrellis in rows of 4,
# as in Adafruit's NeoTrellis driver. With rows of 4, only board rows 0 and 1 were armed and a
# press in row 1 was reported as row 2.
SEESAW_KEYPAD_COLS = const(8)

def _key_to_seesaw(key):
    return (key // config.NEOTRELLIS_NUM_COLS) * SEESAW_KEYPAD_COLS + (key % config.NEOTRELLIS_NUM_COLS)

def _seesaw_to_key(seesaw_key):
    """NeoTrellis key of a seesaw keypad number, or -1 for a column the NeoTrellis doesn't have."""
    col = seesaw_key % SEESAW_KEYPAD_COLS
    if col >= config.NEOTRELLIS_NUM_COLS:
        return -1
    return (seesaw_key // SEESAW_KEYPAD_COLS) * config.NEOTRELLIS_NUM_COLS + col

class NeoTrellis:
    __slots__ = ['_i2c', '_addr', '_board_index', '_key_callback']
    def __init__(self, i2c: I2C, addr: int = 0x2E, board_index: int = 0, key_callback=None):
        self._i2c = i2c
        self._addr = addr
        self._board_index = board_index
        self._key_callback = key_callback

        self.initialize()
            
    def initialize(self):
        """Initialize the NeoTrellis board."""
        self._write(SEESAW_STATUS_BASE, SEESAW_STATUS_SWRST, b'\xff')
        time.sleep_ms(500)

        found = False
        for _ in range(10):
            hw_id = self._read(SEESAW_STATUS_BASE, SEESAW_STATUS_HW_ID, 1, 250)
            if hw_id and hw_id[0] == SEESAW_HW_ID_CODE_SAMD09:
                found = True
                break
            time.sleep_ms(10)

        if not found:
            print('NeoTrellis 0x%02x: not found on I2C bus, resetting' % self._addr)
            return

        self._write(SEESAW_NEOPIXEL_BASE, SEESAW_NEOPIXEL_SPEED, b'\x01')
        num_bytes = config.NEOTRELLIS_NUM_KEYS * 3
        self._write(
            SEESAW_NEOPIXEL_BASE,
            SEESAW_NEOPIXEL_BUF_LENGTH,
            bytes([(num_bytes >> 8) & 0xFF, num_bytes & 0xFF]),
        )
        self._write(SEESAW_NEOPIXEL_BASE, SEESAW_NEOPIXEL_PIN, bytes([NEOTRELLIS_NEOPIX_PIN]))

        for key in range(config.NEOTRELLIS_NUM_KEYS):
            self._activate_key(key, config.NEOTRELLIS_EDGE_FALLING, True)
            self._activate_key(key, config.NEOTRELLIS_EDGE_RISING, True)

        self._enable_interrupt()

    def _write(self, module_addr, func_addr, data=b''):
        payload = bytes([module_addr, func_addr]) + bytes(data)
        try:
            written = self._i2c.writeto(self._addr, payload)
        except OSError as exc:
            print(
                'NeoTrellis 0x%02x: I2C write to module 0x%02x func 0x%02x failed (%s)'
                % (self._addr, module_addr, func_addr, exc)
            )
            time.sleep_us(SEESAW_INTER_TRANSACTION_DELAY_US)
            return False
        time.sleep_us(SEESAW_INTER_TRANSACTION_DELAY_US)
        if written != len(payload):
            print(
                'NeoTrellis 0x%02x: I2C write to module 0x%02x func 0x%02x failed (%d)'
                % (self._addr, module_addr, func_addr, written)
            )
            return False
        return True

    def _read(self, module_addr, func_addr, length, delay_us=0):
        try:
            self._i2c.writeto(self._addr, bytes([module_addr, func_addr]))
        except OSError as exc:
            print(
                'NeoTrellis 0x%02x: I2C read setup to module 0x%02x func 0x%02x failed (%s)'
                % (self._addr, module_addr, func_addr, exc)
            )
            time.sleep_us(SEESAW_INTER_TRANSACTION_DELAY_US)
            return None

        if delay_us:
            time.sleep_us(delay_us)

        try:
            data = self._i2c.readfrom(self._addr, length)
        except OSError as exc:
            print(
                'NeoTrellis 0x%02x: I2C read from module 0x%02x func 0x%02x failed (%s)'
                % (self._addr, module_addr, func_addr, exc)
            )
            time.sleep_us(SEESAW_INTER_TRANSACTION_DELAY_US)
            return None

        time.sleep_us(SEESAW_INTER_TRANSACTION_DELAY_US)
        if len(data) != length:
            print(
                'NeoTrellis 0x%02x: I2C read from module 0x%02x func 0x%02x failed (%d)'
                % (self._addr, module_addr, func_addr, len(data))
            )
            return None
        return data        

    def _activate_key(self, key, edge, enable):
        seesaw_key = _key_to_seesaw(key)
        state = (1 if enable else 0) | ((1 << edge) << 1)
        self._write(SEESAW_KEYPAD_BASE, SEESAW_KEYPAD_EVENT, bytes([seesaw_key, state]))

    def _enable_interrupt(self):
        self._write(SEESAW_KEYPAD_BASE, SEESAW_KEYPAD_INTENSET, b'\x01')

    def set_pixel_color(self, key, r, g, b):
        offset = key * 3
        self._write(
            SEESAW_NEOPIXEL_BASE,
            SEESAW_NEOPIXEL_BUF,
            bytes([(offset >> 8) & 0xFF, offset & 0xFF, g, r, b]),
        )

    def set_pixel_colors(self, first_key, rgb, rgb_offset, count):
        """Write `count` neighbouring pixels in one I2C transaction.

        `rgb` holds 3 bytes (R, G, B) per pixel, starting at `rgb_offset`.
        """
        offset = first_key * 3
        data = bytearray(2 + count * 3)
        data[0] = (offset >> 8) & 0xFF
        data[1] = offset & 0xFF
        for i in range(count):
            src = rgb_offset + i * 3
            dst = 2 + i * 3
            data[dst] = rgb[src + 1]
            data[dst + 1] = rgb[src]
            data[dst + 2] = rgb[src + 2]
        self._write(SEESAW_NEOPIXEL_BASE, SEESAW_NEOPIXEL_BUF, data)

    def show(self):
        self._write(SEESAW_NEOPIXEL_BASE, SEESAW_NEOPIXEL_SHOW)

    def process_events(self):
        while True:
            # Process events for this NeoTrellis board
            count_data = self._read(SEESAW_KEYPAD_BASE, SEESAW_KEYPAD_COUNT, 1, 500)
            if not count_data:
                return False

            count = count_data[0]
            if count == 0 or count > 16:
                return True

            raw = self._read(SEESAW_KEYPAD_BASE, SEESAW_KEYPAD_FIFO, count, 1000)
            if raw is None:
                return False

            for value in raw:
                edge = value & 0x03
                seesaw_key = value >> 2
                key = _seesaw_to_key(seesaw_key)
                if 0 <= key < 16 and self._key_callback is not None:
                    action = config.KEY_ACTION_PRESSED if edge == config.NEOTRELLIS_EDGE_RISING else config.KEY_ACTION_RELEASED
                    event = KeyEvent(action=action, key=key)
                    self._key_callback(event, board_index=self._board_index)

    @property
    def board_index(self):
        return self._board_index

    @property
    def addr(self):
        return self._addr