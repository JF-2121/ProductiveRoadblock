"""Personal bests per song and difficulty, stored as JSON on the board's flash."""
import json


class Records:
    __slots__ = ("_path", "_data")

    def __init__(self, path):
        self._path = path
        self._data = {}
        try:
            with open(path, "r") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            self._data = {}

    @staticmethod
    def _key(song_id, difficulty):
        return "%s:%d" % (song_id, difficulty)

    def get(self, song_id, difficulty):
        return self._data.get(self._key(song_id, difficulty))

    def submit(self, song_id, difficulty, score, stars, accuracy, best_streak, flawless):
        """Store a finished run. Returns True when the score is a new personal best."""
        key = self._key(song_id, difficulty)
        old = self._data.get(key)
        new_best = old is None or score > old["score"]
        if old is None:
            old = {"score": 0, "stars": 0, "accuracy": 0, "streak": 0, "flawless": False}
        record = {
            "score": max(score, old["score"]),
            "stars": max(stars, old["stars"]),
            "accuracy": max(accuracy, old["accuracy"]),
            "streak": max(best_streak, old["streak"]),
            "flawless": flawless or old["flawless"],
        }
        if record != old:
            self._data[key] = record
            try:
                with open(self._path, "w") as f:
                    json.dump(self._data, f)
            except OSError as exc:
                print("[Records] Could not save %s: %s" % (self._path, exc))
        return new_best
