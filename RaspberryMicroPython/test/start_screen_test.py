"""Play all games from the start screen on the board, without the phone app, with console logging.

Run on the Pico (e.g. MicroPico "Run current file on Pico") after uploading the project,
including game/pocketGuitar/songs/. No Bluetooth is started; set LOG_LEVEL to 2 to print
everything the app would receive.
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
from game import game_manager

# ---- Test settings ----------------------------------------------------------
LOG_LEVEL = 1                 # 2 also prints every pad and BLE event
RUN_HAPTIC_CALIBRATION = True
STATS_INTERVAL_S = 10         # print input overflows and memory while running, 0 = off
# -----------------------------------------------------------------------------

CONTROLS = """Controls
  Start screen    hold the board upright (the pads are printed below)
                  row 0 Pocket Guitar: press a difficulty pad, then red key = Play, blue key = Practice
                  row 2 Piano Tiles (Classic, Zen, Arcade), row 4 Simon Says (Simple, Endless): press and release
  Simon Says      press any pad to start, watch the blocks, repeat them
  Piano Tiles     tap the start tile at the bottom, then always the lowest tile, never an empty pad
  Pocket Guitar   turn the board to the guitar grip during the count-in; after the result press a pad
  Everywhere      hold both mechanical keys 2 s = back (Pocket Guitar: pause, then quit)
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
    print("Start screen test (no app)")
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

    gc.collect()
    game_manager.pocket_guitar_log_level = LOG_LEVEL
    game_manager.open_start_screen()
    globals.game.log_level = LOG_LEVEL
    print("[Test] Running. Free memory: %d bytes" % gc.mem_free())

    last_game = globals.game
    last_stats = time.ticks_ms()
    while True:
        await asyncio.sleep_ms(200)
        game = globals.game
        if game is not None and game is not last_game:
            last_game = game
            game.log_level = LOG_LEVEL
            gc.collect()
            print("[Test] Free memory: %d bytes" % gc.mem_free())
        if STATS_INTERVAL_S and game is not None and time.ticks_diff(time.ticks_ms(), last_stats) >= STATS_INTERVAL_S * 1000:
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
