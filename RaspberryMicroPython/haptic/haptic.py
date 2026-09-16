"""High-level Haptic Controller for the TI DRV2605L motor driver (LRA Mode).

Provides:
- Dedicated configuration and auto-calibration for Linear Resonant Actuators (LRA)
  per TI DRV2605L datasheet (SLOS854D), Section 8.5.6.
- Sequencer queue management (enqueuing effect IDs 1-123 and timed pauses 10-1270 ms).
- Playback with optional truncated duration (time limits shorter than standard waveform duration).
- Both asynchronous (async/await via asyncio) and synchronous interfaces.
- Real-time diagnostic reporting, VDD battery voltage reading, and resonance frequency tracking.
"""
import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import I2C
import haptic.drv2605 as driver
from haptic.drv2605_config import *

try:
    import pico_config as config
    _DEFAULT_RATED_VOLTAGE = config.MOTOR_DRV2605L_RATED_VOLTAGE
    _DEFAULT_OD_CLAMP = config.MOTOR_DRV2605L_OD_CLAMP_VOLTAGE
    _DEFAULT_LRA_PERIOD = config.MOTOR_DRV2605L_LRA_PERIOD
except (ImportError, AttributeError):
    _DEFAULT_RATED_VOLTAGE = const(0x50)  # ~1.69 V RMS
    _DEFAULT_OD_CLAMP = const(0x80)       # ~2.71 V peak
    _DEFAULT_LRA_PERIOD = const(0x4E)     # Default ~205 Hz period register


class Haptic:
    """High-level LRA controller for the TI DRV2605L haptic driver."""

    __slots__ = (
        "_drv2605",
        "_ready",
        "_rated_voltage",
        "_od_clamp",
        "_drive_time",
        "_lra_period",
        "_queue",
        "_cal_comp",
        "_cal_bemf",
        "_bemf_gain",
    )

    def __init__(
        self,
        i2c: I2C,
        address: int = DRV2605_ADDR,
        rated_voltage: int = _DEFAULT_RATED_VOLTAGE,
        od_clamp: int = _DEFAULT_OD_CLAMP,
        lra_period: int = _DEFAULT_LRA_PERIOD,
        drive_time: int = 0x13,
    ) -> None:
        """Initialize the DRV2605L for LRA operation.

        Args:
            i2c: Initialized machine.I2C bus instance.
            address: 7-bit I2C device address (default 0x5A).
            rated_voltage: Rated RMS drive voltage register value (0x16).
            od_clamp: Overdrive clamp peak voltage register value (0x17).
            lra_period: Open-loop period register value (0x20).
            drive_time: Initial guess for half-period drive time (0x1B).
        """
        self._drv2605 = driver.DRV2605(i2c, address=address)
        self._ready = False
        self._rated_voltage = rated_voltage & 0xFF
        self._od_clamp = od_clamp & 0xFF
        self._drive_time = drive_time & 0x1F
        self._lra_period = lra_period & 0x7F
        self._queue = []
        self._cal_comp = 0
        self._cal_bemf = 0
        self._bemf_gain = 0

        # Configure chip defaults for LRA actuator
        self._configure_lra()

    # ==========================================================================
    # Device State & Low-Level Register Access
    # ==========================================================================
    def is_ready(self) -> bool:
        """Return True if the controller has successfully completed auto-calibration."""
        return self._ready

    def _read_u8(self, reg: int) -> int:
        return self._drv2605._read_u8(reg)

    def _write_u8(self, reg: int, val: int) -> None:
        self._drv2605._write_u8(reg, val)

    def _configure_lra(self) -> None:
        """Configure registers for LRA closed-loop operation."""
        # 1. Take out of standby, internal trigger mode
        self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
        # 2. Select LRA waveform library (Library 6)
        self._write_u8(DRV2605_REG_LIBRARY, LIBRARY_LRA)
        # 3. Configure Feedback register (0x1A): LRA mode, default brake factor, loop gain
        fb = self._read_u8(DRV2605_REG_FEEDBACK)
        fb |= DRV2605_BITMASK_N_ERM_LRA
        self._write_u8(DRV2605_REG_FEEDBACK, fb)
        # 4. Rated & clamp voltages
        self._write_u8(DRV2605_REG_RATEDV, self._rated_voltage)
        self._write_u8(DRV2605_REG_CLAMPV, self._od_clamp)
        # 5. Open loop period register (0x20)
        self._write_u8(DRV2605_REG_LRA_OL_PERIOD, self._lra_period)
        # 6. Clear initial sequence
        self._write_u8(DRV2605_REG_WAVESEQ1, 1)
        self._write_u8(DRV2605_REG_WAVESEQ2, 0)

    def standby(self, enable: bool = True) -> None:
        """Put the device into or wake out of low-power standby mode."""
        mode = self._read_u8(DRV2605_REG_MODE)
        if enable:
            mode |= DRV2605_BITMASK_STANDBY
        else:
            mode &= ~DRV2605_BITMASK_STANDBY & 0xFF
        self._write_u8(DRV2605_REG_MODE, mode)

    def reset(self) -> None:
        """Perform a software reset and reconfigure LRA defaults."""
        self._write_u8(DRV2605_REG_MODE, DRV2605_BITMASK_DEV_RESET)
        time.sleep_ms(5)
        while self._read_u8(DRV2605_REG_MODE) & DRV2605_BITMASK_DEV_RESET:
            time.sleep_ms(1)
        self._ready = False
        self._configure_lra()

    # ==========================================================================
    # Auto-Calibration (Datasheet SLOS854D, Section 8.5.6)
    # ==========================================================================
    def _setup_calibration_registers(
        self,
        rated_voltage: int = None,
        od_clamp: int = None,
        drive_time: int = None,
    ) -> None:
        """Populate input registers required by the calibration engine."""
        if rated_voltage is not None:
            self._rated_voltage = rated_voltage & 0xFF
        if od_clamp is not None:
            self._od_clamp = od_clamp & 0xFF
        if drive_time is not None:
            self._drive_time = drive_time & 0x1F

        # Step 2: Set MODE register to Auto-Calibration Mode (0x07), exiting standby
        self._write_u8(DRV2605_REG_MODE, MODE_AUTOCAL)

        # Step 3a, 3b, 3c: Feedback register (0x1A)
        # N_ERM_LRA = 1 (LRA), FB_BRAKE_FACTOR = 2 (3x), LOOP_GAIN = 2 (High), BEMF_GAIN = 2 (15x default)
        fb_val = (
            DRV2605_BITMASK_N_ERM_LRA
            | (FB_BRAKE_FACTOR_3X << DRV2605_SHIFT_FB_BRAKE_FACTOR)
            | (LOOP_GAIN_HIGH << DRV2605_SHIFT_LOOP_GAIN)
            | (BEMF_GAIN_2 << DRV2605_SHIFT_BEMF_GAIN)
        )
        self._write_u8(DRV2605_REG_FEEDBACK, fb_val)

        # Step 3d: Rated voltage
        self._write_u8(DRV2605_REG_RATEDV, self._rated_voltage)

        # Step 3e: Overdrive clamp voltage
        self._write_u8(DRV2605_REG_CLAMPV, self._od_clamp)

        # Step 3f, 3k: Control4 (0x1E)
        # AUTO_CAL_TIME = 3 (1000-1200ms), ZC_DET_TIME = 0 (100us)
        ctrl4_val = (
            (AUTO_CAL_TIME_1000_1200MS << DRV2605_SHIFT_AUTO_CAL_TIME)
            | (ZC_DET_TIME_100US << DRV2605_SHIFT_ZC_DET_TIME)
        )
        self._write_u8(DRV2605_REG_CONTROL4, ctrl4_val)

        # Step 3g: Control1 (0x1B)
        # STARTUP_BOOST = 1, DRIVE_TIME = drive_time
        ctrl1_val = DRV2605_BITMASK_STARTUP_BOOST | (self._drive_time & DRV2605_BITMASK_DRIVE_TIME)
        self._write_u8(DRV2605_REG_CONTROL1, ctrl1_val)

        # Step 3h, 3i, 3j: Control2 (0x1C)
        # BIDIR_INPUT = 1, BRAKE_STABILIZER = 1, SAMPLE_TIME = 3 (300us), BLANKING = 1, IDISS = 1
        ctrl2_val = (
            DRV2605_BITMASK_BIDIR_INPUT
            | DRV2605_BITMASK_BRAKE_STABILIZER
            | (SAMPLE_TIME_300US << DRV2605_SHIFT_SAMPLE_TIME)
            | (1 << DRV2605_SHIFT_BLANKING_TIME)
            | (1 << DRV2605_SHIFT_IDISS_TIME)
        )
        self._write_u8(DRV2605_REG_CONTROL2, ctrl2_val)

        # Control5 (0x1F): Upper blanking/idiss bits = 0
        self._write_u8(DRV2605_REG_CONTROL5, DRV2605_DEF_CONTROL5)

    def _evaluate_calibration_result(self) -> bool:
        """Evaluate calibration result and restore operational mode."""
        status = self._read_u8(DRV2605_REG_STATUS)
        passed = (status & DRV2605_BITMASK_DIAG_RESULT) == 0

        # Return to internal trigger mode and restore LRA library
        self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
        self._write_u8(DRV2605_REG_LIBRARY, LIBRARY_LRA)

        if passed:
            self._cal_comp = self._read_u8(DRV2605_REG_AUTOCALCOMP)
            self._cal_bemf = self._read_u8(DRV2605_REG_AUTOCALEMP)
            self._bemf_gain = self._read_u8(DRV2605_REG_FEEDBACK) & DRV2605_BITMASK_BEMF_GAIN
            self._ready = True
        else:
            self._ready = False

        return self._ready

    async def run_auto_calibration(
        self,
        rated_voltage: int = None,
        od_clamp: int = None,
        drive_time: int = None,
        timeout_ms: int = 2500,
    ) -> bool:
        """Asynchronously run auto-calibration on the DRV2605L for LRA.

        Cooperatively yields execution to the asyncio event loop while waiting
        for hardware calibration to converge.
        """
        self._setup_calibration_registers(rated_voltage, od_clamp, drive_time)
        # Step 4: Fire calibration
        self._write_u8(DRV2605_REG_GO, 1)

        # Step 5: Wait until GO self-clears
        start_ms = time.ticks_ms()
        while self.is_playing():
            if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_ms:
                self.stop()
                self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
                self._ready = False
                return False
            await asyncio.sleep_ms(20)

        # Step 6: Verify diagnostic result
        return self._evaluate_calibration_result()

    def auto_calibrate(
        self,
        rated_voltage: int = None,
        od_clamp: int = None,
        drive_time: int = None,
        timeout_ms: int = 2500,
    ) -> bool:
        """Synchronously run auto-calibration on the DRV2605L for LRA (blocking)."""
        self._setup_calibration_registers(rated_voltage, od_clamp, drive_time)
        self._write_u8(DRV2605_REG_GO, 1)

        start_ms = time.ticks_ms()
        while self.is_playing():
            if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_ms:
                self.stop()
                self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
                self._ready = False
                return False
            time.sleep_ms(20)

        return self._evaluate_calibration_result()

    def get_calibration_results(self) -> dict:
        """Return a dictionary of stored auto-calibration parameters."""
        return {
            "ready": self._ready,
            "compensation": self._cal_comp,
            "back_emf": self._cal_bemf,
            "bemf_gain": self._bemf_gain,
        }

    # ==========================================================================
    # Diagnostics Routine (Section 8.6.2, MODE 6)
    # ==========================================================================
    async def run_diagnostics(self, timeout_ms: int = 1000) -> bool:
        """Asynchronously run actuator diagnostics to detect open/short/faults.

        Returns True if actuator is operating normally, False on fault.
        """
        self._write_u8(DRV2605_REG_MODE, MODE_DIAGNOS)
        self._write_u8(DRV2605_REG_GO, 1)

        start_ms = time.ticks_ms()
        while self.is_playing():
            if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_ms:
                self.stop()
                self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
                return False
            await asyncio.sleep_ms(15)

        status = self._read_u8(DRV2605_REG_STATUS)
        self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
        return (status & DRV2605_BITMASK_DIAG_RESULT) == 0

    def run_diagnostics_sync(self, timeout_ms: int = 1000) -> bool:
        """Synchronously run actuator diagnostics to detect open/short/faults."""
        self._write_u8(DRV2605_REG_MODE, MODE_DIAGNOS)
        self._write_u8(DRV2605_REG_GO, 1)

        start_ms = time.ticks_ms()
        while self.is_playing():
            if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_ms:
                self.stop()
                self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
                return False
            time.sleep_ms(15)

        status = self._read_u8(DRV2605_REG_STATUS)
        self._write_u8(DRV2605_REG_MODE, MODE_INTTRIG)
        return (status & DRV2605_BITMASK_DIAG_RESULT) == 0

    # ==========================================================================
    # Sequencer Queue Management (Effects & Pauses)
    # ==========================================================================
    def clear_queue(self) -> None:
        """Clear the pending sequence queue."""
        self._queue.clear()

    def enqueue_effect(self, effect_id: int) -> "Haptic":
        """Enqueue a ROM library effect (1 to 123).

        Returns self for method chaining.
        """
        if not 1 <= effect_id <= 123:
            raise ValueError("Effect ID must be between 1 and 123 (got %d)" % effect_id)
        if len(self._queue) >= 8:
            raise ValueError("Sequencer queue full (maximum 8 slots)")
        self._queue.append(effect_id & 0x7F)
        return self

    def enqueue_pause(self, duration_ms: int) -> "Haptic":
        """Enqueue a timed pause between effects (10 ms to 1270 ms).

        Resolution is 10 ms (1 centisecond). Returns self for method chaining.
        """
        if duration_ms < 10 or duration_ms > 1270:
            raise ValueError("Pause duration must be between 10 ms and 1270 ms (got %d ms)" % duration_ms)
        if len(self._queue) >= 8:
            raise ValueError("Sequencer queue full (maximum 8 slots)")
        steps = min(127, max(1, round(duration_ms / 10.0)))
        self._queue.append(DRV2605_BITMASK_WAVESEQ_WAIT | (steps & 0x7F))
        return self

    def commit_queue(self) -> None:
        """Flush the queued effects and pauses into the 8 hardware registers."""
        count = len(self._queue)
        for i in range(8):
            val = self._queue[i] if i < count else 0
            self._write_u8(DRV2605_REG_WAVESEQ1 + i, val)

    def set_sequence(self, sequence) -> None:
        """Directly write a complete sequence of effects and/or pauses.

        Accepts an iterable of up to 8 elements:
        - int: effect ID (1-123)
        - float: pause duration in seconds (e.g. 0.05 = 50ms)
        - tuple ('pause', ms) or ('effect', id)
        - driver.Effect or driver.Pause instance
        """
        self.clear_queue()
        for item in sequence:
            if isinstance(item, int):
                self.enqueue_effect(item)
            elif isinstance(item, float):
                self.enqueue_pause(int(round(item * 1000.0)))
            elif isinstance(item, tuple) and len(item) == 2:
                kind, val = item
                if kind in ("pause", "delay", "wait"):
                    self.enqueue_pause(int(val))
                elif kind in ("effect", "fx"):
                    self.enqueue_effect(int(val))
                else:
                    raise ValueError("Unknown sequence tuple kind: %s" % kind)
            elif hasattr(item, "raw_value"):
                if len(self._queue) >= 8:
                    raise ValueError("Sequencer full (max 8 slots)")
                self._queue.append(item.raw_value & 0xFF)
            else:
                raise TypeError("Unsupported sequence element: %r" % (item,))
        self.commit_queue()

    def set_slot(self, slot: int, item) -> None:
        """Write a specific sequencer slot (0-7)."""
        if not 0 <= slot <= 7:
            raise IndexError("Slot index must be between 0 and 7")
        if isinstance(item, int):
            if item == 0:
                raw_val = 0
            elif 1 <= item <= 123:
                raw_val = item & 0x7F
            else:
                raw_val = item & 0xFF
        elif isinstance(item, float):
            steps = min(127, max(1, round((item * 1000.0) / 10.0)))
            raw_val = DRV2605_BITMASK_WAVESEQ_WAIT | (steps & 0x7F)
        elif hasattr(item, "raw_value"):
            raw_val = item.raw_value & 0xFF
        else:
            raise TypeError("Unsupported slot element: %r" % (item,))
        self._write_u8(DRV2605_REG_WAVESEQ1 + slot, raw_val)

    def get_sequence(self) -> list:
        """Read and decode the current 8 sequencer slots from hardware."""
        seq = []
        for i in range(8):
            val = self._read_u8(DRV2605_REG_WAVESEQ1 + i)
            if val == 0:
                break
            if val & DRV2605_BITMASK_WAVESEQ_WAIT:
                seq.append(("pause_ms", (val & DRV2605_BITMASK_WAVESEQ_EFFECT) * 10))
            else:
                seq.append(("effect_id", val & DRV2605_BITMASK_WAVESEQ_EFFECT))
        return seq

    # ==========================================================================
    # Playback Control (with Truncated Duration / Time-Limit Support)
    # ==========================================================================
    def is_playing(self) -> bool:
        """Return True while the waveform sequence or process is currently active."""
        return bool(self._read_u8(DRV2605_REG_GO) & DRV2605_BITMASK_GO)

    def stop(self) -> None:
        """Instantly stop ongoing haptic playback or cancel pending sequence."""
        self._write_u8(DRV2605_REG_GO, 0)

    def play(self, duration_ms: int = None, blocking: bool = False) -> None:
        """Play back the currently queued waveform sequence.

        Args:
            duration_ms: Optional explicit cutoff duration in milliseconds.
                If provided, playback is stopped after duration_ms even if the
                underlying waveform is longer.
            blocking: If True and duration_ms is None, wait until playback completes.
        """
        self._write_u8(DRV2605_REG_GO, 1)

        if duration_ms is not None:
            if duration_ms <= 0:
                self.stop()
                return
            start_ms = time.ticks_ms()
            while self.is_playing():
                if time.ticks_diff(time.ticks_ms(), start_ms) >= duration_ms:
                    self.stop()
                    break
                time.sleep_ms(1)
        elif blocking:
            while self.is_playing():
                time.sleep_ms(5)

    async def play_async(self, duration_ms: int = None) -> None:
        """Asynchronously play back the sequence without blocking the event loop.

        Args:
            duration_ms: Optional explicit cutoff duration in milliseconds.
                If provided, terminates playback after duration_ms.
        """
        self._write_u8(DRV2605_REG_GO, 1)

        if duration_ms is not None:
            if duration_ms <= 0:
                self.stop()
                return
            start_ms = time.ticks_ms()
            while self.is_playing():
                elapsed = time.ticks_diff(time.ticks_ms(), start_ms)
                if elapsed >= duration_ms:
                    self.stop()
                    break
                remaining = duration_ms - elapsed
                await asyncio.sleep_ms(min(remaining, 10))
        else:
            while self.is_playing():
                await asyncio.sleep_ms(10)

    def play_effect(
        self,
        effect_id: int,
        duration_ms: int = None,
        blocking: bool = False,
    ) -> None:
        """Convenience method: Load a single effect and play with optional time limit."""
        if not 1 <= effect_id <= 123:
            raise ValueError("Effect ID must be between 1 and 123")
        self._write_u8(DRV2605_REG_WAVESEQ1, effect_id & 0x7F)
        self._write_u8(DRV2605_REG_WAVESEQ2, 0)
        self.play(duration_ms=duration_ms, blocking=blocking)

    async def play_effect_async(
        self,
        effect_id: int,
        duration_ms: int = None,
    ) -> None:
        """Asynchronously load a single effect and play with optional time limit."""
        if not 1 <= effect_id <= 123:
            raise ValueError("Effect ID must be between 1 and 123")
        self._write_u8(DRV2605_REG_WAVESEQ1, effect_id & 0x7F)
        self._write_u8(DRV2605_REG_WAVESEQ2, 0)
        await self.play_async(duration_ms=duration_ms)

    # ==========================================================================
    # Real-Time Playback (RTP) & Telemetry
    # ==========================================================================
    def set_realtime_value(self, value: int) -> None:
        """Write to RTPIN (0x02) for direct amplitude drive in RTP mode."""
        self._write_u8(DRV2605_REG_RTPIN, value & 0xFF)

    def set_mode(self, mode: int) -> None:
        """Set operating mode (0-7) while preserving standby state."""
        current = self._read_u8(DRV2605_REG_MODE)
        self._write_u8(
            DRV2605_REG_MODE,
            (current & DRV2605_BITMASK_STANDBY) | (mode & DRV2605_BITMASK_MODE),
        )

    def read_vbat(self) -> float:
        """Read real-time VDD voltage via the VBAT register during active playback.

        Formula per Section 8.6.27: VDD = VBAT * 5.6V / 255
        """
        raw = self._read_u8(DRV2605_REG_VBAT)
        return (raw * 5.6) / 255.0

    def read_lra_period_us(self) -> float:
        """Read real-time LRA resonance period in microseconds during active playback.

        Formula per Section 8.6.28: period = LRA_PERIOD * 98.46 us
        """
        raw = self._read_u8(DRV2605_REG_LRA_PERIOD)
        return raw * 98.46

    def read_lra_frequency_hz(self) -> float:
        """Calculate real-time LRA resonance frequency in Hz from reported period."""
        period_us = self.read_lra_period_us()
        if period_us <= 0:
            return 0.0
        return 1_000_000.0 / period_us

    def get_status(self) -> dict:
        """Read and decode the STATUS register (0x00)."""
        status = self._read_u8(DRV2605_REG_STATUS)
        return {
            "raw": status,
            "device_id": (status & DRV2605_BITMASK_DEVICE_ID) >> DRV2605_SHIFT_DEVICE_ID,
            "diag_result": bool(status & DRV2605_BITMASK_DIAG_RESULT),
            "over_temp": bool(status & DRV2605_BITMASK_OVER_TEMP),
            "oc_detect": bool(status & DRV2605_BITMASK_OC_DETECT),
        }