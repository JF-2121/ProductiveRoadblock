"""Opens the games: exactly one game (or the start screen) owns the keyboard and the LEDs.

Everything that switches games goes through here: main.py at boot, the start screen, the back
gesture in the games and the BLE commands. The previous game is always stopped first.
"""
import gc
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import globals
import pico_config as config
from ble_handler.config import BLE_EVENT_ID_GAME, BLE_GAME_SELECTED

# Pocket Guitar log level, set by main.py (1 = every judged note, 2 = also every pad and BLE event)
pocket_guitar_log_level = 1

# Games that can be opened, with their number of variants: Pocket Guitar difficulties,
# Simon Says and Piano Tiles modes
VARIANTS = {
    config.GAME_ID_START_SCREEN: 1,
    config.GAME_ID_PIANO_TILES: 3,
    config.GAME_ID_SIMON_SAYS: 2,
    config.GAME_ID_POCKET_GUITAR: 4,
}


def open_start_screen():
    return open_game(config.GAME_ID_START_SCREEN)


def open_midi_screen():
    """MIDI mode: stop the open game and show the MIDI pads (game/midi_screen.py)."""
    return open_game(config.GAME_ID_MIDI)


def open_game(game_id, variant=None, game_config=None, start_mode=None):
    """Stop the open game and open game_id on its ready screen. Returns the new game.

    variant: Pocket Guitar difficulty 0-3, Simon Says mode 0-1, Piano Tiles mode 0-2.
    game_config: optional generated config (Simon Says sequence, Piano Tiles tiles).
    start_mode: Pocket Guitar only, from the start screen: start the song at once in this mode
    (POCKET_GUITAR_MODE_PLAY / _PRACTICE) and come back to the start screen afterwards.
    Raises ValueError for an unknown game or variant.
    """
    if game_id == config.GAME_ID_MIDI:
        variant = None
    elif globals.midiboard_mode == config.BOARD_MODE_MIDI:
        raise ValueError("MIDI mode: no games until the MIDI device disconnects")
    elif game_id not in VARIANTS:
        raise ValueError("Unsupported game ID: %d" % game_id)
    if variant is not None and not 0 <= variant < VARIANTS[game_id]:
        raise ValueError("Unsupported variant %d for game %d" % (variant, game_id))

    old = globals.game
    globals.game = None
    if old is not None:
        old.stop_game()
    gc.collect()

    if game_id == config.GAME_ID_POCKET_GUITAR:
        from game.pocketGuitar.pocket_guitar_control import PocketGuitarControl
        game = PocketGuitarControl()
        game.log_level = pocket_guitar_log_level
        if variant is not None:
            game.preselect_difficulty(variant)
        if start_mode is not None:
            game.start_on_open(start_mode)
    elif game_id == config.GAME_ID_SIMON_SAYS:
        from game.simonSays.simon_says_control import SimonSaysControl
        game = SimonSaysControl(variant or 0, game_config)
    elif game_id == config.GAME_ID_PIANO_TILES:
        from game.pianoTiles.pianoTiles_control import PianoTilesControl
        game = PianoTilesControl(variant or 0, game_config)
    elif game_id == config.GAME_ID_MIDI:
        from game.midi_screen import MidiScreen
        game = MidiScreen()
    else:
        from game.start_screen import StartScreen
        game = StartScreen()

    globals.game = game
    _send_selected(game_id, variant)
    game.load_game_config(game.config)
    return game


def request_open(game_id, variant=None, start_mode=None):
    """Open a game from inside a game loop. The switch runs in its own task, because a game
    loop can't stop (cancel) its own task."""
    asyncio.create_task(_open_later(game_id, variant, start_mode))


async def _open_later(game_id, variant, start_mode):
    try:
        open_game(game_id, variant, None, start_mode)
    except Exception as exc:
        print("[GameManager] Could not open game %d: %r" % (game_id, exc))


def _send_selected(game_id, variant):
    ble_inst = getattr(globals, "bluetooth", None)
    if ble_inst and ble_inst.is_connected:
        ble_inst.send_event(BLE_EVENT_ID_GAME, bytes((BLE_GAME_SELECTED, game_id, 0xFF if variant is None else variant)))
