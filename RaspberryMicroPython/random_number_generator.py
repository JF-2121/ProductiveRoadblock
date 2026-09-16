import time

try:
    import urandom as _urandom
except ImportError:
    _urandom = None

try:
    import machine
except ImportError:
    machine = None

class RandomNumberGenerator:
    def __init__(self, seed=None):
        if seed is not None:
            self._seed(seed)
        else:
            self._seed(self._auto_seed())

    def _auto_seed(self):
        seed = time.ticks_us() ^ (time.ticks_ms() << 16)

        try:
            seed ^= time.ticks_cpu()
        except AttributeError:
            pass

        if _urandom is not None:
            try:
                seed ^= _urandom.getrandbits(32)
            except AttributeError:
                pass

        if machine is not None:
            try:
                uid = machine.unique_id()
                if len(uid) >= 4:
                    seed ^= int.from_bytes(uid[-4:], 'little')
            except AttributeError:
                pass

        seed &= 0xFFFFFFFF
        if seed == 0:
            seed = 0xA5A5A5A5
        return seed

    def _seed(self, seed_value):
        self.state = seed_value & 0xFFFFFFFF  # Ensure state is a 32-bit integer
        if self.state == 0:
            self.state = 0xA5A5A5A5

    def random(self):
        # xorshift32 gives better bit distribution than a basic LCG.
        value = self.state
        value ^= (value << 13) & 0xFFFFFFFF
        value ^= (value >> 17) & 0xFFFFFFFF
        value ^= (value << 5) & 0xFFFFFFFF
        self.state = value & 0xFFFFFFFF
        return self.state

    def randint(self, min_value, max_value):
        if min_value > max_value:
            raise ValueError("min_value must be less than or equal to max_value")
        
        range_size = max_value - min_value + 1

        # Rejection sampling avoids modulo bias for arbitrary ranges.
        limit = (0x100000000 // range_size) * range_size
        while True:
            value = self.random()
            if value < limit:
                return min_value + (value % range_size)