"""Personal bests of Simon Says and Piano Tiles, one value per game mode, stored as JSON on the board's flash."""
import json

DEFAULT_PATH = "game_scores.json"


class BestScores:
    __slots__ = ("_path", "_data")

    def __init__(self, path=DEFAULT_PATH):
        self._path = path
        try:
            with open(path, "r") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            self._data = {}

    def get(self, key):
        return self._data.get(key)

    def submit(self, key, value, lower_is_better=False):
        """Save value if it beats the stored one. Returns True when it is a new best."""
        old = self._data.get(key)
        if old is not None and (value >= old if lower_is_better else value <= old):
            return False
        self._data[key] = value
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f)
        except OSError as exc:
            print("[BestScores] Could not save %s: %s" % (self._path, exc))
        return True
