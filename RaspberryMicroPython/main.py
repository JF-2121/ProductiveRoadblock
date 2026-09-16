"""Main entry point for the Raspberry Pi Pico 2 W interactive haptic game board.

Orchestrates:
1. DRV2605L LRA Haptic controller initialization & mandatory bootup auto-calibration.
2. NeoTrellis 4x8 keypad matrix & mechanical keys initialization.
3. Bluetooth Low Energy (BLE) peripheral service & GATT channels.
4. The start screen, which opens Pocket Guitar, Piano Tiles and Simon Says (game/game_manager.py).
"""
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import I2C, Pin

import globals
import pico_config as config
from ble_handler.ble_handler import BLEHandler
from game import game_manager
from haptic.haptic import Haptic
from keyboard.keyboard import Keyboard

# Pocket Guitar log level: 1 prints every judged note, 2 also every pad and BLE event.
# Mechanical key interrupts are logged by the keyboard when config.MECH_KEY_DEBUG_LOG is True.
POCKET_GUITAR_LOG_LEVEL = 1


async def main():
    print("=" * 60)
    print("Starting Raspberry Pi Pico 2 W Haptic Gaming System")
    print("=" * 60)
    # 1. Initialize Haptic controller (I2C0: GP0=SDA, GP1=SCL)
    print("[Haptic] Initializing DRV2605L driver (LRA Mode)...")
    motor_i2c = I2C(
        config.MOTOR_I2C_PORT,
        scl=Pin(config.MOTOR_I2C_SCL_PIN),
        sda=Pin(config.MOTOR_I2C_SDA_PIN),
        freq=config.MOTOR_I2C_FREQ,
    )
    print("[Haptic] I2C0 scan:", [hex(a) for a in motor_i2c.scan()])
    globals.haptic = Haptic(
        i2c=motor_i2c,
        rated_voltage=config.MOTOR_DRV2605L_RATED_VOLTAGE,
        od_clamp=config.MOTOR_DRV2605L_OD_CLAMP_VOLTAGE,
        lra_period=config.MOTOR_DRV2605L_LRA_PERIOD,
    )

    # 2. Run Auto-Calibration on every bootup
    print("[Haptic] Running DRV2605L auto-calibration on bootup...")
    cal_ok = await globals.haptic.run_auto_calibration()
    if cal_ok:
        res = globals.haptic.get_calibration_results()
        print(f"[Haptic] Auto-calibration succeeded! Comp: 0x{res['compensation']:02X}, BEMF: 0x{res['back_emf']:02X}, Gain: {res['bemf_gain']}")
    else:
        print("[Haptic Warning] Auto-calibration failed or timed out. Operating with defaults.")

    # 3. Initialize Keyboard / NeoTrellis matrix (I2C1: GP10=SDA, GP11=SCL)
    print("[Keyboard] Initializing NeoTrellis keypad & mechanical keys...")
    try:
        globals.keyboard = Keyboard()
        print("[Keyboard] NeoTrellis 4x8 matrix initialized.")
    except Exception as e:
        print(f"[Keyboard Error] Failed to initialize keypad: {e}")

    # 4. Initialize and start Bluetooth Low Energy (BLE)
    print("[BLE] Initializing BLE handler...")
    globals.bluetooth = BLEHandler()
    await globals.bluetooth.start()
    print("[BLE] game and MIDI services registered and advertising.")

    # 5. The game UI remains available until a connected session selects MIDI.
    print("[Game] Opening the start screen...")
    if config.MECH_KEY_DEBUG_LOG:
        print("[Main] Debug: logging every mechanical key interrupt ([MechKey] lines).")
    game_manager.pocket_guitar_log_level = POCKET_GUITAR_LOG_LEVEL
    game_manager.open_start_screen()

    print("[Main] System running. Awaiting input or BLE commands...")

    # Main cooperative loop
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
        if globals.haptic:
            globals.haptic.stop()
        if globals.keyboard:
            globals.keyboard.set_color(0, 0, 0)
            globals.keyboard.show()