"""Start screen: pick a game and its mode.

Portrait (see game/portrait.py), one row per game with an empty row in between:
  row 0  Pocket Guitar  difficulty Easy, Medium, Hard, Expert of the song Warm-Up: press a pad to
                        select it (bright), then press a mechanical key: red = Play, blue = Practice
  row 2  Piano Tiles    Classic, Zen, Arcade
  row 4  Simon Says     Simple, Endless
Piano Tiles and Simon Says: press a pad and let go to open the game; the pad lights up while held.
In every game, holding both mechanical keys for 2 s comes back here.
"""
import pico_config as config
from game import portrait
from game.board_game import BoardGame, FULL, LOG_INFO
from game.haptic_player import PRIORITY_TICK
from game.utils import GameConfig

_FX_PRESS = 24     # Sharp Tick 1 100 %
_LEVEL = 4         # Piano Tiles and Simon Says entries at 1/4 brightness, the held one at full
_LEVEL_UNSELECTED = 2  # Pocket Guitar difficulties that are not selected

# (x, y, game id, variant, colour, name)
_ENTRIES = (
    (0, 0, config.GAME_ID_POCKET_GUITAR, 0, (0, 255, 0), "Pocket Guitar: Warm-Up, easy"),
    (1, 0, config.GAME_ID_POCKET_GUITAR, 1, (255, 200, 0), "Pocket Guitar: Warm-Up, medium"),
    (2, 0, config.GAME_ID_POCKET_GUITAR, 2, (255, 90, 0), "Pocket Guitar: Warm-Up, hard"),
    (3, 0, config.GAME_ID_POCKET_GUITAR, 3, (255, 0, 0), "Pocket Guitar: Warm-Up, expert"),
    (0, 2, config.GAME_ID_PIANO_TILES, config.PIANO_TILES_MODE_CLASSIC, (0, 150, 255), "Piano Tiles: Classic"),
    (1, 2, config.GAME_ID_PIANO_TILES, config.PIANO_TILES_MODE_ZEN, (0, 150, 255), "Piano Tiles: Zen"),
    (2, 2, config.GAME_ID_PIANO_TILES, config.PIANO_TILES_MODE_ARCADE, (0, 150, 255), "Piano Tiles: Arcade"),
    (0, 4, config.GAME_ID_SIMON_SAYS, config.SIMON_SAYS_MODE_SIMPLE, (255, 0, 200), "Simon Says: Simple"),
    (1, 4, config.GAME_ID_SIMON_SAYS, config.SIMON_SAYS_MODE_ENDLESS, (255, 0, 200), "Simon Says: Endless"),
)
_MODE_NAMES = ("Play", "Practice")

# The selected Pocket Guitar difficulty, kept while the board is on
_selected_difficulty = 0


class StartScreen(BoardGame):
    __slots__ = ["_entry_at", "_held", "_opening"]

    def __init__(self):
        super().__init__(GameConfig(game_id=config.GAME_ID_START_SCREEN), "StartScreen")
        self._entry_at = [None] * portrait.CELLS
        for entry in _ENTRIES:
            self._entry_at[entry[1] * portrait.WIDTH + entry[0]] = entry
        self._held = -1
        self._opening = False

    def enter_ready(self, now):
        self._held = -1
        self._opening = False
        self._dirty = True
        self.set_state(config.GAME_STATE_READY)
        if self.log_level >= LOG_INFO:
            self._log("===== START SCREEN (hold the board upright) =====")
            for x, y, game_id, variant, color, name in _ENTRIES:
                self._log("  row %d, column %d (pad %2d): %s" % (y, x, portrait.KEY[y * portrait.WIDTH + x], name))
            self._log("Pocket Guitar: press a difficulty pad, then red key = Play, blue key = Practice (selected: %s)."
                      % _ENTRIES[_selected_difficulty][5].split(", ")[-1])
            self._log("Piano Tiles, Simon Says: press and release a pad. In a game: hold both mechanical keys 2 s = back here.")

    def on_pad(self, cell, pressed, event_time, now):
        global _selected_difficulty
        if self._opening:
            return
        entry = self._entry_at[cell]
        if pressed:
            if entry is None or self._held >= 0:
                return
            self._held = cell
            self._dirty = True
            self._haptics.play(_FX_PRESS, PRIORITY_TICK, 40)
            if entry[2] == config.GAME_ID_POCKET_GUITAR and entry[3] != _selected_difficulty:
                _selected_difficulty = entry[3]
                if self.log_level >= LOG_INFO:
                    self._log("Selected %s. Red key = Play, blue key = Practice." % entry[5])
        elif cell == self._held:
            self._held = -1
            self._dirty = True
            if entry[2] == config.GAME_ID_POCKET_GUITAR:
                return  # only selects, the mechanical keys start
            self._opening = True
            if self.log_level >= LOG_INFO:
                self._log("Opening %s" % entry[5])
            from game import game_manager
            game_manager.request_open(entry[2], entry[3])

    def on_mech_key(self, key, pressed, now):
        if not pressed or self._opening:
            return
        mode = config.POCKET_GUITAR_MODE_PLAY if key == config.STRUM_KEY_RED else config.POCKET_GUITAR_MODE_PRACTICE
        self._opening = True
        if self.log_level >= LOG_INFO:
            self._log("Starting %s: %s" % (_ENTRIES[_selected_difficulty][5], _MODE_NAMES[mode]))
        from game import game_manager
        game_manager.request_open(config.GAME_ID_POCKET_GUITAR, _selected_difficulty, start_mode=mode)

    def on_back(self, now):
        pass  # already on the start screen

    def draw(self, now):
        for x, y, game_id, variant, color, name in _ENTRIES:
            cell = y * portrait.WIDTH + x
            if cell == self._held:
                level = FULL
            elif game_id == config.GAME_ID_POCKET_GUITAR:
                level = FULL if variant == _selected_difficulty else _LEVEL_UNSELECTED
            else:
                level = _LEVEL
            self.px(cell, color, level)
