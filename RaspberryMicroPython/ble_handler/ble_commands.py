"""BLE command handlers: game control, device actions, Pocket Guitar selection and stream messages.

The byte layouts of all commands and events are listed in the README.
"""
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import gc

import globals
import pico_config as config
import ble_handler.config as ble_config
from ble_handler.stream_protocol import decode_game_config_message
from game import game_manager
from game.game_generator import GameGenerator
from game.haptic_player import PRIORITY_SYSTEM


def _send_ble_error(error_code: int, payload: int | bytes = b""):
    if isinstance(payload, int):
        payload_bytes = bytes([payload & 0xFF])
    else:
        payload_bytes = bytes(payload) if payload else b""

    ble_inst = getattr(globals, "ble", None) or getattr(globals, "bluetooth", None)
    if ble_inst:
        ble_inst.send_event(ble_config.BLE_EVENT_ID_ERROR, bytes([error_code]) + payload_bytes)


def _send_event(event_id: int, payload: bytes):
    ble_inst = getattr(globals, "ble", None) or getattr(globals, "bluetooth", None)
    if ble_inst:
        ble_inst.send_event(event_id, payload)


def _u16(value: int) -> bytes:
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


def _require_game_loaded():
    game = getattr(globals, "game", None)
    if game is None:
        _send_ble_error(ble_config.BLE_ERROR_CODE_GAME_NOT_LOADED)
        raise ValueError("No active game is loaded.")
    return game


def _open_game(game_id: int, variant: int | None = None, game_config=None):
    if game_id not in game_manager.VARIANTS:
        _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_GAME_ID, game_id)
        raise ValueError(f"Unsupported game ID: {game_id}")
    try:
        return game_manager.open_game(game_id, variant, game_config)
    except ValueError:
        _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, game_id)
        raise


def _build_game_config_from_stream(payload: bytes):
    if not payload:
        raise ValueError("Stream payload is empty.")

    decoded = decode_game_config_message(payload)
    if not decoded:
        raise ValueError("Stream payload did not contain a valid game configuration.")

    game_id = decoded.get("game_id", config.GAME_ID_PIANO_TILES)
    seed = decoded.get("seed", 0)
    num_steps = decoded.get("num_steps", config.GAME_NUMBER_OF_STEPS)
    return GameGenerator.generate_game(
        game_id=game_id,
        num_steps=num_steps,
        seed=seed,
        hit_action=decoded.get("hit_action"),
        miss_action=decoded.get("miss_action"),
        game_name=decoded.get("game_name"),
    )


def handle_stream_message(message_type: int, payload: bytes):
    """Handle protobuf-like stream payloads for game selection and larger configuration transfers."""
    if message_type == ble_config.BLE_STREAM_MSG_GAME_CONFIG:
        # Simon Says: Simple with the generated sequence, started at once. Piano Tiles: Classic with the generated tiles.
        cfg = _build_game_config_from_stream(payload)
        _open_game(cfg.game_id, None, cfg).start_game()
        return cfg

    if message_type == ble_config.BLE_STREAM_MSG_GAME_SELECT:
        if not payload:
            raise ValueError("Game selection payload is empty.")
        return _open_game(payload[0], payload[1] if len(payload) > 1 else None)

    if message_type == ble_config.BLE_STREAM_MSG_GAME_LOAD:
        cfg = _build_game_config_from_stream(payload)
        _open_game(cfg.game_id, None, cfg)
        return cfg

    if message_type == ble_config.BLE_STREAM_MSG_POCKET_GUITAR_SONG:
        # Pocket Guitar song from the app: open Pocket Guitar if needed and select the song
        game = getattr(globals, "game", None)
        if game is None or game.config.game_id != config.GAME_ID_POCKET_GUITAR:
            game = _open_game(config.GAME_ID_POCKET_GUITAR)
        if not game.load_song_json(payload):
            _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, message_type)
            raise ValueError("Pocket Guitar song could not be loaded (invalid, or a song is running).")
        return game

    raise ValueError(f"Unsupported stream message type: 0x{message_type:02X}")


def game_interaction(command: int, value: bytes):
    """Processes game control commands (category BLE_CMD_GAME_CONTROL)."""
    if command == ble_config.BLE_GAME_CONTROL_START:
        print("[Game] Starting game")
        _require_game_loaded().start_game()

    elif command == ble_config.BLE_GAME_CONTROL_STOP:
        print("[Game] Stopping game, back to the start screen")
        game_manager.open_start_screen()

    elif command == ble_config.BLE_GAME_CONTROL_RESET:
        print("[Game] Resetting game")
        _require_game_loaded().reset_game()

    elif command == ble_config.BLE_GAME_CONTROL_RESUME:
        print("[Game] Resuming game")
        _require_game_loaded().resume_game()

    elif command == ble_config.BLE_GAME_CONTROL_PAUSE:
        print("[Game] Pausing game")
        _require_game_loaded().pause_game()

    elif command == ble_config.BLE_GAME_CONTROL_SELECT:
        if not value:
            _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, command)
            raise ValueError("Game selection requires a game ID byte.")
        game_id = value[0]
        variant = value[1] if len(value) > 1 else None
        print(f"[Game] Selecting game with ID: 0x{game_id:02X}, variant {variant}")
        _open_game(game_id, variant)

    elif command == ble_config.BLE_GAME_CONTROL_LOAD:
        print("[Game] Loading game configuration")
        _require_game_loaded().load_game()

    elif command == ble_config.BLE_GAME_CONTROL_TRIGGER_HAPTIC:
        if not value or not 1 <= value[0] <= 123:
            _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, command)
            raise ValueError("Trigger haptic requires an effect ID 1-123.")
        _trigger_haptic(value[0])

    elif command == ble_config.BLE_GAME_CONTROL_RUN_AUTOCAL:
        print("[Haptic] Auto-calibration requested")
        asyncio.create_task(_run_auto_calibration())

    elif command == ble_config.BLE_GAME_CONTROL_SET_BRIGHTNESS:
        if not value:
            _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, command)
            raise ValueError("Set brightness requires a level byte.")
        if globals.keyboard:
            globals.keyboard.set_brightness(value[0])

    elif command == ble_config.BLE_GAME_CONTROL_GET_TELEMETRY:
        _send_telemetry()

    else:
        print(f"[Game] Unknown command {command} with value {value.hex() if value else b''}")
        _send_ble_error(ble_config.BLE_ERROR_CODE_WRONG_COMMAND, command)


def pocket_guitar_interaction(command: int, value: bytes):
    """Processes Pocket Guitar commands (category BLE_CMD_POCKET_GUITAR). Selections only work on its select screen."""
    game = getattr(globals, "game", None)
    if game is None or game.config.game_id != config.GAME_ID_POCKET_GUITAR:
        _send_ble_error(ble_config.BLE_ERROR_CODE_GAME_NOT_LOADED, command)
        raise ValueError("Pocket Guitar is not open.")

    if command == ble_config.BLE_POCKET_GUITAR_SELECT_SONG:
        ok = bool(value) and game.select_song_slot(value[0])
    elif command == ble_config.BLE_POCKET_GUITAR_SELECT_DIFFICULTY:
        ok = bool(value) and game.select_difficulty(value[0])
    elif command == ble_config.BLE_POCKET_GUITAR_SELECT_MODE:
        ok = bool(value) and game.select_mode(value[0])
    elif command == ble_config.BLE_POCKET_GUITAR_SET_DELAY_OFFSET:
        ok = len(value) >= 2
        if ok:
            offset = value[0] | (value[1] << 8)
            if offset >= 0x8000:
                offset -= 0x10000
            ok = game.set_delay_offset(offset)
    elif command == ble_config.BLE_POCKET_GUITAR_SET_OPTIONS:
        ok = bool(value) and game.set_options(value[0])
    elif command == ble_config.BLE_POCKET_GUITAR_GET_SELECTION:
        game.send_selection()
        ok = True
    else:
        _send_ble_error(ble_config.BLE_ERROR_CODE_WRONG_COMMAND, command)
        raise ValueError(f"Unknown Pocket Guitar command {command}")

    if not ok:
        _send_ble_error(ble_config.BLE_ERROR_CODE_INVALID_PAYLOAD, command)


def _trigger_haptic(effect_id: int):
    # Through the game's haptic player when it has one, so the effect doesn't fight the game's own effects
    haptics = getattr(globals.game, "_haptics", None) if globals.game is not None else None
    if haptics is not None:
        haptics.play(effect_id, PRIORITY_SYSTEM, 100)
    elif globals.haptic:
        globals.haptic.play_effect(effect_id)


async def _run_auto_calibration():
    haptic = globals.haptic
    if not haptic:
        _send_ble_error(ble_config.BLE_ERROR_CODE_GENERIC, ble_config.BLE_GAME_CONTROL_RUN_AUTOCAL)
        return
    haptics = getattr(globals.game, "_haptics", None) if globals.game is not None else None
    if haptics is not None:
        haptics.stop()
    try:
        ok = await haptic.run_auto_calibration()
        result = haptic.get_calibration_results()
    except OSError as exc:
        print(f"[Haptic] Auto-calibration failed: {exc}")
        _send_ble_error(ble_config.BLE_ERROR_CODE_GENERIC, ble_config.BLE_GAME_CONTROL_RUN_AUTOCAL)
        return
    print(f"[Haptic] Auto-calibration {'ok' if ok else 'failed'}: {result}")
    _send_event(ble_config.BLE_EVENT_ID_CALIBRATION_REPORT, bytes([
        1 if ok else 0, result["compensation"] & 0xFF, result["back_emf"] & 0xFF, result["bemf_gain"] & 0xFF]))


def _send_telemetry():
    vbat_mv = 0
    if globals.haptic:
        try:
            vbat_mv = int(globals.haptic.read_vbat() * 1000)
        except OSError:
            pass
    free_kb = gc.mem_free() // 1024 if hasattr(gc, "mem_free") else 0
    game = getattr(globals, "game", None)
    game_id = game.config.game_id if game is not None else config.GAME_ID_START_SCREEN
    state = game.state.state if game is not None else config.GAME_STATE_INIT
    brightness = globals.keyboard.get_brightness() if globals.keyboard else 255
    _send_event(ble_config.BLE_EVENT_ID_BATTERY_REPORT,
                _u16(vbat_mv) + _u16(min(free_kb, 0xFFFF)) + bytes([game_id, state, brightness]))
