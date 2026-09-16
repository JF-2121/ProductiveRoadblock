import pico_config as config
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import globals
from ble_handler.config import BLE_EVENT_ID_PLAY_SOUND

class Action:
    __slots__ = ["score_update", "haptic_effects", "sound_effects", "key_light_effects"]

    def __init__(self, score_update=0, haptic_effects=None, sound_effects=None, key_light_effects=None):
        self.score_update = score_update
        self.haptic_effects = haptic_effects or []
        self.sound_effects = sound_effects or []
        self.key_light_effects = key_light_effects or []

    async def execute(self):
        async def exec_haptics():
            for h in self.haptic_effects:
                if hasattr(h, "execute_async"):
                    await h.execute_async()
                elif hasattr(h, "execute"):
                    h.execute()

        async def exec_sounds():
            for s in self.sound_effects:
                if hasattr(s, "execute_async"):
                    await s.execute_async()
                elif hasattr(s, "execute"):
                    s.execute()

        async def exec_lights():
            for k in self.key_light_effects:
                if hasattr(k, "execute"):
                    await k.execute()

        await asyncio.gather(
            exec_haptics(),
            exec_sounds(),
            exec_lights(),
        )


class HapticEffect:
    __slots__ = ["effect_id", "intensity", "duration_ms"]

    def __init__(self, effect_id=None, intensity=255, duration_ms=None):
        self.effect_id = effect_id
        self.intensity = intensity
        self.duration_ms = duration_ms

    def execute(self):
        if globals.haptic:
            eff_id = self.effect_id if self.effect_id is not None else getattr(globals, "default_haptic_effect", 1)
            dur_ms = self.duration_ms if self.duration_ms is not None else getattr(globals, "default_haptic_duration_ms", 40)
            globals.haptic.play_effect(eff_id, duration_ms=dur_ms)

    async def execute_async(self):
        if globals.haptic:
            eff_id = self.effect_id if self.effect_id is not None else getattr(globals, "default_haptic_effect", 1)
            dur_ms = self.duration_ms if self.duration_ms is not None else getattr(globals, "default_haptic_duration_ms", 40)
            await globals.haptic.play_effect_async(eff_id, duration_ms=dur_ms)


class SoundEffect:
    __slots__ = ["effect_id", "duration_ms"]

    def __init__(self, effect_id=0, duration_ms=1000):
        self.effect_id = effect_id
        self.duration_ms = duration_ms

    def execute(self):
        ble_inst = getattr(globals, "bluetooth", None) or getattr(globals, "ble", None)
        if ble_inst:
            ble_inst.send_event(
                BLE_EVENT_ID_PLAY_SOUND,
                bytes([self.effect_id, self.duration_ms & 0xFF, (self.duration_ms >> 8) & 0xFF]),
            )

class KeyLightEffect:
    __slots__ = ["effect_id", "duration_ms", "keys", "colors"]

    def __init__(self, effect_id=0, duration_ms=250, keys=None, color=(255, 255, 255)):
        self.effect_id = effect_id
        self.duration_ms = duration_ms
        if keys is None:
            self.keys = []
        elif isinstance(keys, (list, tuple)):
            self.keys = list(keys)
        else:
            self.keys = [keys]
        self.colors = [color]

    async def execute(self, key_pressed=None):
        if globals.keyboard:
            c = self.colors[0]
            for k in self.keys:
                globals.keyboard.set_key_color(k, c[0], c[1], c[2])
            globals.keyboard.show()
            asyncio.create_task(self.reset_keys_after_delay())

    async def reset_keys_after_delay(self):
        await asyncio.sleep_ms(self.duration_ms)
        if globals.keyboard:
            for k in self.keys:
                globals.keyboard.set_key_color(k, 0, 0, 0)
            globals.keyboard.show()


class Step:
    __slots__ = [
        "id",
        "clock",
        "at",
        "pads",
        "window_ms",
        "on_hit",
        "on_miss",
        "on_timeout",
        "on_advance",
        "on_reset",
    ]

    def __init__(
        self,
        id=0,
        clock="step",
        at=0,
        pads=None,
        window_ms=None,
        on_hit: Action | dict | None = None,
        on_miss: Action | dict | None = None,
        on_timeout: Action | dict | None = None,
        on_advance: Action | dict | None = None,
        on_reset: Action | dict | None = None,
    ):
        self.id = id
        self.clock = clock
        self.at = at
        self.pads = pads if pads is not None else []
        self.window_ms = window_ms
        self.on_hit = on_hit if on_hit is not None else {}
        self.on_miss = on_miss if on_miss is not None else {}
        self.on_timeout = on_timeout if on_timeout is not None else {}
        self.on_advance = on_advance
        self.on_reset = on_reset


class GameGeneratorConfig:
    __slots__ = [
        "number_of_steps",
        "number_of_rows",
        "number_of_cols",
        "number_of_keys",
        "fail_action",
        "fail_feedback_color",
        "fail_haptic_effect",
        "fail_sound_effect",
        "hit_action",
        "hit_feedback_color",
        "hit_haptic_effect",
        "hit_sound_effect",
    ]

    def __init__(
        self,
        number_of_steps=20,
        fail_action=None,
        fail_feedback_color=(255, 0, 0),
        fail_haptic_effect=None,
        fail_sound_effect=None,
        hit_action=None,
        hit_feedback_color=(0, 255, 0),
        hit_haptic_effect=None,
        hit_sound_effect=None,
    ):
        self.number_of_steps = number_of_steps
        self.number_of_rows = config.GRID_NUM_ROWS
        self.number_of_cols = config.GRID_NUM_COLS
        self.number_of_keys = config.GRID_NUM_KEYS
        self.fail_action = fail_action
        self.fail_feedback_color = fail_feedback_color
        self.fail_haptic_effect = fail_haptic_effect or HapticEffect(effect_id=47, duration_ms=250)
        self.fail_sound_effect = fail_sound_effect
        self.hit_action = hit_action
        self.hit_feedback_color = hit_feedback_color
        self.hit_haptic_effect = hit_haptic_effect or HapticEffect(effect_id=1, duration_ms=40)
        self.hit_sound_effect = hit_sound_effect


class GameConfig:
    __slots__ = [
        "game_id",
        "clocks",
        "grid",
        "step_window_size",
        "steps",
        "win_action",
        "lose_action",
    ]

    def __init__(
        self,
        game_id=config.GAME_ID_NONE,
        clocks=None,
        grid=None,
        step_window_size=8,
        steps=None,
        win_action=None,
        lose_action=None,
    ):
        self.game_id = game_id
        self.grid = grid or {"rows": config.GRID_NUM_ROWS, "cols": config.GRID_NUM_COLS}
        self.clocks = clocks
        self.steps = steps if steps is not None else []
        self.step_window_size = step_window_size
        self.win_action = win_action
        self.lose_action = lose_action


class GameState:
    __slots__ = [
        "score",
        "state",
        "start_time",
        "clock_mode",
        "current_step_index",
        "current_step_start_time",
        "current_step_end_time",
        "colors",
        "steps_in_window",
        "grid_state",
    ]

    def __init__(self):
        self.state: int = config.GAME_STATE_INIT
        self.clock_mode = "NORMAL"
        self.score = 0
        self.start_time = 0
        self.current_step_index = 0
        self.current_step_start_time = 0
        self.current_step_end_time = 0
        self.colors = bytearray([0] * (config.GRID_NUM_KEYS * 3))
        self.steps_in_window = []
        self.grid_state = [[(0, 0, 0) for _ in range(config.GRID_NUM_COLS)] for _ in range(config.GRID_NUM_ROWS)]