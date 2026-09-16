import json
from random_number_generator import RandomNumberGenerator
import pico_config as config
from game.utils import *
from keyboard.utils import xy_to_grid_key

class GameGenerator:
    config: GameGeneratorConfig = GameGeneratorConfig(number_of_steps=15)

    @staticmethod
    def _merge_action(base_action, override_action=None):
        if override_action is None:
            return base_action
        if not isinstance(override_action, dict):
            return base_action
        merged = dict(base_action)
        merged.update(override_action)
        return merged

    @staticmethod
    def create_game_instance(game_config: GameConfig):
        """Open the game of a generated config (stops the open game, see game/game_manager.py)."""
        from game import game_manager
        return game_manager.open_game(game_config.game_id, None, game_config)

    @staticmethod
    def create_game_instance_for_id(game_id: int):
        from game import game_manager
        return game_manager.open_game(game_id)

    @staticmethod
    def _random_sequence(random, count: int, choices: int) -> list:
        """Random values 0..choices-1, the same value at most twice in a row."""
        values = []
        for i in range(count):
            value = random.randint(0, choices - 1)
            if i >= 2 and values[i - 1] == value and values[i - 2] == value:
                value = (value + 1 + random.randint(0, choices - 2)) % choices
            values.append(value)
        return values

    @staticmethod
    def generate_game(game_id: int, num_steps: int = 20, seed: int | None = None, hit_action: dict | None = None, miss_action: dict | None = None, game_name: str | None = None):
        if game_id == config.GAME_ID_SIMON_SAYS:
            return GameGenerator.generateSimonSays(num_steps=num_steps, seed=seed, hit_action=hit_action, miss_action=miss_action, game_name=game_name)
        if game_id == config.GAME_ID_PIANO_TILES:
            return GameGenerator.generatePianoTiles(num_steps=num_steps, seed=seed, hit_action=hit_action, miss_action=miss_action, game_name=game_name)
        raise ValueError(f"Unsupported game ID: {game_id}")

    @staticmethod
    def generatePianoTiles(num_steps: int = 20, seed: int | None = None, hit_action: dict | None = None, miss_action: dict | None = None, game_name: str | None = None) -> GameConfig:
        """Generate Piano Tiles tiles: one step per tile, pads = [lane 0-3] (portrait columns, see game/pianoTiles/GAME_DESIGN.md)."""
        steps = []
        random = RandomNumberGenerator(seed)
        num_lanes = config.GRID_NUM_ROWS  # 4 lanes: the board is held upright
        lanes = GameGenerator._random_sequence(random, num_steps, num_lanes)
        default_hit = {
            "score": 10,
            "haptic": {"effect_id": 1, "duration_ms": 40},
            "sound": {"effect_id": 1, "duration_ms": 40},
            "feedback_color": (0, 150, 255),
        }
        default_miss = {
            "score": 0,
            "haptic": {"effect_id": 47, "duration_ms": 250},
            "sound": {"effect_id": 47, "duration_ms": 250},
            "feedback_color": (255, 0, 0),
            "action": "fail",
        }

        for step_idx in range(num_steps):
            step_hit = GameGenerator._merge_action(default_hit, hit_action)
            step_miss = GameGenerator._merge_action(default_miss, miss_action)

            step = Step(
                id=step_idx,
                clock="step",
                at=step_idx,
                pads=[lanes[step_idx]],
                window_ms=None,
                on_hit=step_hit,
                on_miss=step_miss,
                on_timeout={},
            )
            steps.append(step)

        # Portrait: 4 lanes wide, 8 rows tall
        grid = {"rows": config.GRID_NUM_COLS, "cols": config.GRID_NUM_ROWS}
        return GameConfig(
            game_id=config.GAME_ID_PIANO_TILES,
            grid=grid,
            step_window_size=config.GRID_NUM_COLS,
            steps=steps,
        )

    @staticmethod
    def generateSimonSays(num_steps: int = 8, seed: int | None = None, hit_action: dict | None = None, miss_action: dict | None = None, game_name: str | None = None) -> GameConfig:
        """Generate a Simon Says sequence: one step per block, pads = [block 0-7] (2x2 colour blocks, see game/simonSays/GAME_DESIGN.md)."""
        steps = []
        random = RandomNumberGenerator(seed)
        blocks = GameGenerator._random_sequence(random, num_steps, 8)
        default_hit = {
            "score": 10,
            "haptic": {"effect_id": 1, "duration_ms": 40},
            "sound": {"effect_id": 1, "duration_ms": 40},
        }
        default_miss = {
            "score": 0,
            "haptic": {"effect_id": 47, "duration_ms": 250},
            "sound": {"effect_id": 47, "duration_ms": 250},
            "action": "fail",
        }

        for step_idx in range(num_steps):
            step_hit = GameGenerator._merge_action(default_hit, hit_action)
            step_miss = GameGenerator._merge_action(default_miss, miss_action)

            step = Step(
                id=step_idx,
                clock="step",
                at=step_idx,
                pads=[blocks[step_idx]],
                window_ms=5000,
                on_hit=step_hit,
                on_miss=step_miss,
            )
            steps.append(step)

        # Portrait: 2 blocks wide, 4 blocks tall
        grid = {"rows": config.GRID_NUM_COLS, "cols": config.GRID_NUM_ROWS}
        return GameConfig(
            game_id=config.GAME_ID_SIMON_SAYS,
            grid=grid,
            steps=steps,
        )

    @staticmethod
    def load_from_json(filepath: str) -> GameConfig:
        """Load and parse a GameConfig from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        game_id_str = data.get("game_id", "")
        if "piano" in game_id_str.lower():
            gid = config.GAME_ID_PIANO_TILES
        elif "simon" in game_id_str.lower():
            gid = config.GAME_ID_SIMON_SAYS
        else:
            gid = config.GAME_ID_NONE

        steps = []
        for s_data in data.get("steps", []):
            step = Step(
                id=s_data.get("id", 0),
                clock=s_data.get("clock", "step"),
                at=s_data.get("at", 0),
                pads=s_data.get("pads", []),
                window_ms=s_data.get("window_ms"),
                on_hit=s_data.get("on_hit", {}),
                on_miss=s_data.get("on_miss", {}),
                on_timeout=s_data.get("on_timeout", {}),
                on_advance=s_data.get("on_advance"),
                on_reset=s_data.get("on_reset"),
            )
            steps.append(step)

        return GameConfig(
            game_id=gid,
            grid=data.get("grid"),
            clocks=data.get("clocks"),
            steps=steps,
        )