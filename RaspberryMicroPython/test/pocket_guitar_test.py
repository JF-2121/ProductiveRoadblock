"""Play Pocket Guitar on the board without the phone app, with console logging.

Run on the Pico (e.g. MicroPico "Run current file on Pico") after uploading the project,
including game/pocketGuitar/songs/. No Bluetooth is started; everything the app would
receive is printed instead when LOG_LEVEL is 2.
"""
import gc
import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import I2C, Pin
import pico_config as config
import globals
from haptic.haptic import Haptic
from keyboard.keyboard import Keyboard
from game.pocketGuitar.pocket_guitar_control import PocketGuitarControl, LOG_INFO, LOG_DEBUG

# ---- Test settings ----------------------------------------------------------
LOG_LEVEL = LOG_INFO          # LOG_DEBUG also prints every key and BLE event
BEAT_TICK = True              # tick on every beat: helps to keep time without music
BEAT_LINES = True
SUSTAIN_HUM = True
DELAY_OFFSET_MS = 0
RUN_HAPTIC_CALIBRATION = True
STATS_INTERVAL_S = 10         # print loop timing and memory while running, 0 = off
# -----------------------------------------------------------------------------

CONTROLS = """Controls
  Select screen   pads for difficulty and song are printed in the SELECT log
                  red strum (key 33) = Play    blue strum (key 32) = Practice
  In a song       hold frets (any key in a column) and strum when notes reach the hit row
                  the feedback column flashes green = hit, orange = almost, red = miss; otherwise it shows the streak
                  hold both strum keys 2 s with no frets = pause
  Paused          strum = resume              hold both strum keys 2 s = quit
  Result          strum = play again          press a pad = back to select
"""


def init_haptic():
    try:
        motor_i2c = I2C(
            config.MOTOR_I2C_PORT,
            scl=Pin(config.MOTOR_I2C_SCL_PIN),
            sda=Pin(config.MOTOR_I2C_SDA_PIN),
            freq=config.MOTOR_I2C_FREQ,
        )
        return Haptic(
            i2c=motor_i2c,
            rated_voltage=config.MOTOR_DRV2605L_RATED_VOLTAGE,
            od_clamp=config.MOTOR_DRV2605L_OD_CLAMP_VOLTAGE,
            lra_period=config.MOTOR_DRV2605L_LRA_PERIOD,
        )
    except OSError as exc:
        print("[Test] Haptic driver not found (%s), playing without vibration." % exc)
        return None


async def main():
    print("=" * 60)
    print("Pocket Guitar test (no app)")
    print("=" * 60)
    print(CONTROLS)

    globals.haptic = init_haptic()
    if globals.haptic and RUN_HAPTIC_CALIBRATION:
        print("[Test] Haptic auto-calibration...")
        ok = await globals.haptic.run_auto_calibration()
        print("[Test] Haptic calibration %s" % ("ok" if ok else "failed, using defaults"))

    print("[Test] Initializing keyboard...")
    globals.keyboard = Keyboard()
    globals.bluetooth = None
    globals.ble = None

    game = PocketGuitarControl()
    game.log_level = LOG_LEVEL
    game.beat_tick = BEAT_TICK
    game.beat_lines = BEAT_LINES
    game.sustain_hum = SUSTAIN_HUM
    game.delay_offset_ms = DELAY_OFFSET_MS
    globals.game = game

    gc.collect()
    game.load_game_config(game.config)
    print("[Test] Running. Free memory: %d bytes" % gc.mem_free())

    last_stats = time.ticks_ms()
    while True:
        await asyncio.sleep_ms(500)
        if STATS_INTERVAL_S and time.ticks_diff(time.ticks_ms(), last_stats) >= STATS_INTERVAL_S * 1000:
            last_stats = time.ticks_ms()
            print("[Test] " + game.stats_line())


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n[Test] Stopped.")
finally:
    if globals.haptic:
        globals.haptic.stop()
    if globals.keyboard:
        globals.keyboard.set_color(0, 0, 0)
        globals.keyboard.show()
    asyncio.new_event_loop()
