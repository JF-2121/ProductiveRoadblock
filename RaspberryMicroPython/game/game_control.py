"""Base Game Control engine for interactive grid games."""
import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import globals

import pico_config as config
from keyboard.utils import KeyEvent
from game.utils import *
from ble_handler.config import *


class GameControl:
    """Base class for interactive games running on the NeoTrellis matrix.

    MicroPython has no `abc` module, so subclasses must override the
    methods below by convention rather than enforced abstraction.
    """

    __slots__ = [
        "_config",
        "_state",
        "_task",
    ]

    def __init__(self, game_config: GameConfig | None = None, game_state: GameState | None = None):
        self._config = game_config or GameConfig()
        self._state = game_state or GameState()
        self._task = None

    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def state(self) -> GameState:
        return self._state

    def load_game_config(self, game_config: GameConfig) -> None:
        """Load a game configuration and reset game state."""
        self._config = game_config
        self._state = GameState()
        self._state.state = config.GAME_STATE_READY
        self.UpdateGridState()

    def start_game(self) -> None:
        """Start or restart the game."""
        if not self._config:
            raise RuntimeError("Game configuration is not loaded.")
        if self._state.state == config.GAME_STATE_RUNNING:
            return

        self._state.state = config.GAME_STATE_RUNNING
        self._state.start_time = time.ticks_ms()
        self._state.score = 0
        self._state.current_step_index = 0

        # Register input callback with keyboard
        if globals.keyboard:
            globals.keyboard.set_key_pressed_callback(self.keyPressedCallback)
            globals.keyboard.set_color(0, 0, 0)
            globals.keyboard.show()

        # Notify BLE client of game start
        self.notify_state(config.GAME_STATE_RUNNING)
        self.notify_score()

        self.UpdateGridState()

    def pause_game(self) -> None:
        """Pause the current game."""
        if self._state.state == config.GAME_STATE_RUNNING:
            self._state.state = config.GAME_STATE_PAUSED
            self.notify_state(config.GAME_STATE_PAUSED)

    def resume_game(self) -> None:
        """Resume a paused game."""
        if self._state.state == config.GAME_STATE_PAUSED:
            self._state.state = config.GAME_STATE_RUNNING
            self.notify_state(config.GAME_STATE_RUNNING)

    def stop_game(self) -> None:
        """Stop game playback and turn off motor/lights."""
        self._state.state = config.GAME_STATE_OVER
        if globals.haptic:
            globals.haptic.stop()
        if globals.keyboard:
            globals.keyboard.set_color(0, 0, 0)
            globals.keyboard.show()
        self.notify_state(config.GAME_STATE_OVER)

    def reset_game(self) -> None:
        """Reset game state and prepare for a new game."""
        self._state = GameState()
        self._state.state = config.GAME_STATE_READY
        self.notify_state(config.GAME_STATE_READY)
        self.notify_score(0)

    def select_game(self, game_id: int, *, auto_start: bool = True):
        """Stop this game and open another one by BLE game ID (see game/game_manager.py)."""
        from game import game_manager

        next_game = game_manager.open_game(game_id)
        if auto_start:
            next_game.start_game()
        return next_game

    def load_game(self, game_config: GameConfig | None = None, *, auto_start: bool = False):
        """Load a game configuration onto the current controller."""
        if game_config is not None:
            self.load_game_config(game_config)
        elif getattr(self, "_config", None) is not None:
            self.load_game_config(self._config)
        else:
            raise ValueError("No game configuration available to load.")

        if auto_start:
            self.start_game()
        return self._config

    def notify_score(self, score: int | None = None) -> None:
        """Send current score to connected BLE client."""
        if score is None:
            score = self._state.score
        ble_inst = getattr(globals, "bluetooth", None) or getattr(globals, "ble", None)
        if ble_inst:
            # Send score as 2-byte little-endian value
            value = bytes([BLE_GAME_SCORE_UPDATE]) + bytes([score & 0xFF, (score >> 8) & 0xFF])
            ble_inst.send_event(
                BLE_EVENT_ID_GAME,
                value,
            )

    def notify_state(self, state_val: int | None = None) -> None:
        """Send game state transition event to connected BLE client."""
        if state_val is None:
            state_val = self._state.state
        ble_inst = getattr(globals, "bluetooth", None) or getattr(globals, "ble", None)
        if ble_inst:
            value = bytes([BLE_GAME_STATE_UPDATE]) + bytes([state_val & 0xFF])
            ble_inst.send_event(
                BLE_EVENT_ID_GAME,
                value,
            )

    def trigger_haptic(self, effect_id: int, duration_ms: int) -> None:
        """Trigger game-driven haptic feedback on the DRV2605L."""
        if not globals.haptic:
            return
        eff_id = effect_id if effect_id is not None else getattr(globals, "default_haptic_effect", 1)
        dur_ms = duration_ms if duration_ms is not None else getattr(globals, "default_haptic_duration_ms", 40)
        globals.haptic.play_effect(eff_id, duration_ms=dur_ms)

    def execute_action(self, action) -> None:
        """Execute hit, miss, win, or lose action."""
        if action is None:
            return
        if isinstance(action, Action):
            asyncio.create_task(action.execute())
        elif isinstance(action, dict):
            # Parse dict action {haptic, sound, feedback_color, ...}
            haptic_cfg = action.get("haptic")
            if haptic_cfg and globals.haptic:
                dur = haptic_cfg.get("duration_ms", getattr(globals, "default_haptic_duration_ms", 40))
                eff = haptic_cfg.get("effect_id", getattr(globals, "default_haptic_effect", 1))
                self.trigger_haptic(eff, dur)
        elif callable(action):
            action()

    def UpdateGridState(self) -> None:
        """Render the current step / game visualization on the keyboard grid."""
        raise NotImplementedError

    def next_step(self) -> None:
        """Advance game to the next step or round."""
        raise NotImplementedError

    def keyPressedCallback(self, key_or_event) -> None:
        """Handle player key press event."""
        raise NotImplementedError

    def win(self) -> None:
        """Handle victory condition."""
        raise NotImplementedError

    def lose(self) -> None:
        """Handle game over condition."""
        raise NotImplementedError