"""Non-blocking haptic output for the games.

Haptic.play_effect(duration_ms=...) waits until the cut-off time, which would freeze the
game loop. This player starts effects without waiting, cuts them from update(), lets
important effects win over unimportant ones, and drives a steady hum (RTP mode) that
pauses for other effects.
"""
import time
from haptic.drv2605_config import MODE_INTTRIG, MODE_REALTIME

PRIORITY_TICK = 1
PRIORITY_ALMOST = 2
PRIORITY_ACCENT = 3
PRIORITY_MULTIPLIER = 4
PRIORITY_MISS = 5
PRIORITY_SYSTEM = 6

DEFAULT_HUM_LEVEL = 0x28  # signed RTP amplitude, 0x7F = full drive


class HapticPlayer:
    __slots__ = (
        "_haptic",
        "_busy",
        "_busy_until",
        "_busy_priority",
        "_cut",
        "_hum_wanted",
        "_hum_on",
        "hum_level",
    )

    def __init__(self, haptic, hum_level=DEFAULT_HUM_LEVEL):
        self._haptic = haptic
        self._busy = False
        self._busy_until = 0
        self._busy_priority = 0
        self._cut = False
        self._hum_wanted = False
        self._hum_on = False
        self.hum_level = hum_level

    @property
    def available(self):
        return self._haptic is not None

    def play(self, effect_id, priority, duration_ms, cut=False):
        """Start a library effect. duration_ms is how long it blocks lower priorities;
        with cut=True the effect is also stopped after duration_ms."""
        if self._haptic is None:
            return False
        now = time.ticks_ms()
        if self._busy and priority < self._busy_priority and time.ticks_diff(self._busy_until, now) > 0:
            return False
        try:
            if self._hum_on:
                self._hum_hardware(False)
            self._haptic.play_effect(effect_id)
        except OSError as exc:
            self._disable(exc)
            return False
        self._busy = True
        self._busy_until = time.ticks_add(now, duration_ms)
        self._busy_priority = priority
        self._cut = cut
        return True

    def set_hum(self, on):
        self._hum_wanted = on

    def update(self, now):
        if self._haptic is None:
            return
        try:
            if self._busy and time.ticks_diff(now, self._busy_until) >= 0:
                self._busy = False
                if self._cut:
                    self._haptic.stop()
            if not self._busy and self._hum_wanted != self._hum_on:
                self._hum_hardware(self._hum_wanted)
        except OSError as exc:
            self._disable(exc)

    def stop(self):
        self._hum_wanted = False
        self._busy = False
        if self._haptic is None:
            return
        try:
            if self._hum_on:
                self._hum_hardware(False)
            self._haptic.stop()
        except OSError as exc:
            self._disable(exc)

    def _hum_hardware(self, on):
        if on:
            self._haptic.set_mode(MODE_REALTIME)
            self._haptic.set_realtime_value(self.hum_level)
        else:
            self._haptic.set_realtime_value(0)
            self._haptic.set_mode(MODE_INTTRIG)
        self._hum_on = on

    def _disable(self, exc):
        print("[HapticPlayer] I2C error (%s), haptics disabled" % exc)
        self._haptic = None
        self._busy = False
        self._hum_on = False
