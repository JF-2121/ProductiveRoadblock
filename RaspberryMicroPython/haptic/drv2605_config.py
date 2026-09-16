"""DRV2605L Register Map, Bit Masks, Shift Values, and Field Enums.

Source: TI DRV2605L Datasheet (SLOS854D - Revised March 2018), Section 8.6 "Register Map"
"""
from micropython import const

# ==============================================================================
# I2C Address
# ==============================================================================
DRV2605_ADDR = const(0x5A)

# ==============================================================================
# Register Map Addresses (Table 3, Section 8.6)
# ==============================================================================
DRV2605_REG_STATUS = const(0x00)         # Status (RO)
DRV2605_REG_MODE = const(0x01)           # Mode (R/W)
DRV2605_REG_RTPIN = const(0x02)          # Real-time playback input (R/W)
DRV2605_REG_RTP_INPUT = const(0x02)      # Alias for RTPIN
DRV2605_REG_LIBRARY = const(0x03)        # Waveform library selection (R/W)
DRV2605_REG_LIBRARY_SEL = const(0x03)    # Alias for LIBRARY
DRV2605_REG_WAVESEQ1 = const(0x04)       # Waveform sequencer slot 1 (R/W)
DRV2605_REG_WAVESEQ2 = const(0x05)       # Waveform sequencer slot 2 (R/W)
DRV2605_REG_WAVESEQ3 = const(0x06)       # Waveform sequencer slot 3 (R/W)
DRV2605_REG_WAVESEQ4 = const(0x07)       # Waveform sequencer slot 4 (R/W)
DRV2605_REG_WAVESEQ5 = const(0x08)       # Waveform sequencer slot 5 (R/W)
DRV2605_REG_WAVESEQ6 = const(0x09)       # Waveform sequencer slot 6 (R/W)
DRV2605_REG_WAVESEQ7 = const(0x0A)       # Waveform sequencer slot 7 (R/W)
DRV2605_REG_WAVESEQ8 = const(0x0B)       # Waveform sequencer slot 8 (R/W)
DRV2605_REG_GO = const(0x0C)             # Go register (R/W)
DRV2605_REG_OVERDRIVE = const(0x0D)      # Overdrive time offset (ODT) (R/W)
DRV2605_REG_ODT = const(0x0D)            # Alias for OVERDRIVE
DRV2605_REG_SUSTAINPOS = const(0x0E)     # Sustain time offset positive (SPT) (R/W)
DRV2605_REG_SPT = const(0x0E)            # Alias for SUSTAINPOS
DRV2605_REG_SUSTAINNEG = const(0x0F)     # Sustain time offset negative (SNT) (R/W)
DRV2605_REG_SNT = const(0x0F)            # Alias for SUSTAINNEG
DRV2605_REG_BREAK = const(0x10)          # Brake time offset (BRT) (R/W)
DRV2605_REG_BRT = const(0x10)            # Alias for BREAK
DRV2605_REG_AUDIOCTRL = const(0x11)      # Audio-to-vibe control (ATH_CTRL) (R/W)
DRV2605_REG_ATH_CTRL = const(0x11)       # Alias for AUDIOCTRL
DRV2605_REG_AUDIOLVL = const(0x12)       # Audio-to-vibe min input level (ATH_MIN_INPUT) (R/W)
DRV2605_REG_ATH_MIN_INPUT = const(0x12)  # Alias for AUDIOLVL
DRV2605_REG_AUDIOMAX = const(0x13)       # Audio-to-vibe max input level (ATH_MAX_INPUT) (R/W)
DRV2605_REG_ATH_MAX_INPUT = const(0x13)  # Alias for AUDIOMAX
DRV2605_REG_AUDIOMINDRV = const(0x14)    # Audio-to-vibe min output drive (ATH_MIN_DRIVE) (R/W)
DRV2605_REG_ATH_MIN_DRIVE = const(0x14)  # Alias for AUDIOMINDRV
DRV2605_REG_AUDIOMAXDRV = const(0x15)    # Audio-to-vibe max output drive (ATH_MAX_DRIVE) (R/W)
DRV2605_REG_ATH_MAX_DRIVE = const(0x15)  # Alias for AUDIOMAXDRV
DRV2605_REG_RATEDV = const(0x16)         # Rated voltage (RATED_VOLTAGE) (R/W)
DRV2605_REG_RATED_VOLTAGE = const(0x16)  # Alias for RATEDV
DRV2605_REG_CLAMPV = const(0x17)         # Overdrive clamp voltage (OD_CLAMP) (R/W)
DRV2605_REG_OD_CLAMP = const(0x17)       # Alias for CLAMPV
DRV2605_REG_AUTOCALCOMP = const(0x18)    # Auto-cal compensation result (A_CAL_COMP) (R/W)
DRV2605_REG_A_CAL_COMP = const(0x18)     # Alias for AUTOCALCOMP
DRV2605_REG_AUTOCALEMP = const(0x19)     # Auto-cal back-EMF result (A_CAL_BEMF) (R/W)
DRV2605_REG_A_CAL_BEMF = const(0x19)     # Alias for AUTOCALEMP
DRV2605_REG_FEEDBACK = const(0x1A)       # Feedback control (R/W)
DRV2605_REG_CONTROL1 = const(0x1B)       # Control1 (R/W)
DRV2605_REG_CONTROL2 = const(0x1C)       # Control2 (R/W)
DRV2605_REG_CONTROL3 = const(0x1D)       # Control3 (R/W)
DRV2605_REG_CONTROL4 = const(0x1E)       # Control4 (R/W)
DRV2605_REG_CONTROL5 = const(0x1F)       # Control5 (R/W)
DRV2605_REG_LRA_OL_PERIOD = const(0x20)  # LRA open-loop period (OL_LRA_PERIOD) (R/W)
DRV2605_REG_OL_LRA_PERIOD = const(0x20)  # Alias for LRA_OL_PERIOD
DRV2605_REG_VBAT = const(0x21)           # V(BAT) voltage monitor (R/W)
DRV2605_REG_LRARESON = const(0x22)       # LRA resonance period (LRA_PERIOD) (R/W)
DRV2605_REG_LRA_PERIOD = const(0x22)     # Alias for LRARESON

# ==============================================================================
# Default Register Reset Values (Table 3)
# ==============================================================================
DRV2605_DEF_STATUS = const(0xE0)
DRV2605_DEF_MODE = const(0x40)
DRV2605_DEF_RTPIN = const(0x00)
DRV2605_DEF_LIBRARY = const(0x01)
DRV2605_DEF_WAVESEQ1 = const(0x01)
DRV2605_DEF_WAVESEQ2 = const(0x00)
DRV2605_DEF_WAVESEQ3 = const(0x00)
DRV2605_DEF_WAVESEQ4 = const(0x00)
DRV2605_DEF_WAVESEQ5 = const(0x00)
DRV2605_DEF_WAVESEQ6 = const(0x00)
DRV2605_DEF_WAVESEQ7 = const(0x00)
DRV2605_DEF_WAVESEQ8 = const(0x00)
DRV2605_DEF_GO = const(0x00)
DRV2605_DEF_OVERDRIVE = const(0x00)
DRV2605_DEF_SUSTAINPOS = const(0x00)
DRV2605_DEF_SUSTAINNEG = const(0x00)
DRV2605_DEF_BREAK = const(0x00)
DRV2605_DEF_AUDIOCTRL = const(0x05)
DRV2605_DEF_AUDIOLVL = const(0x19)
DRV2605_DEF_AUDIOMAX = const(0xFF)
DRV2605_DEF_AUDIOMINDRV = const(0x19)
DRV2605_DEF_AUDIOMAXDRV = const(0xFF)
DRV2605_DEF_RATEDV = const(0x3E)
DRV2605_DEF_CLAMPV = const(0x8C)
DRV2605_DEF_AUTOCALCOMP = const(0x0C)
DRV2605_DEF_AUTOCALEMP = const(0x6C)
DRV2605_DEF_FEEDBACK = const(0x36)
DRV2605_DEF_CONTROL1 = const(0x93)
DRV2605_DEF_CONTROL2 = const(0xF5)
DRV2605_DEF_CONTROL3 = const(0xA0)
DRV2605_DEF_CONTROL4 = const(0x20)
DRV2605_DEF_CONTROL5 = const(0x80)
DRV2605_DEF_LRA_OL_PERIOD = const(0x33)
DRV2605_DEF_VBAT = const(0x00)
DRV2605_DEF_LRARESON = const(0x00)

# ==============================================================================
# User-Facing Mode & Library Constants
# ==============================================================================
# MODE register (0x01) MODE[2:0] values (Table 2 & Table 5)
MODE_INTTRIG = 0x00          # Internal trigger mode
MODE_EXTTRIGEDGE = 0x01      # External trigger mode (edge)
MODE_EXTTRIGLVL = 0x02       # External trigger mode (level)
MODE_PWMANALOG = 0x03        # PWM input and analog input mode
MODE_AUDIOVIBE = 0x04        # Audio-to-vibe mode
MODE_REALTIME = 0x05         # Real-time playback (RTP) mode
MODE_DIAGNOS = 0x06          # Diagnostics mode
MODE_AUTOCAL = 0x07          # Auto calibration mode

# LIBRARY Selection register (0x03) LIBRARY_SEL[2:0] values (Table 1 & Table 7)
LIBRARY_EMPTY = 0x00         # Empty / None
LIBRARY_TS2200A = 0x01       # TS2200 Library A (ERM 1.3V rated, 3.0V overdrive)
LIBRARY_TS2200B = 0x02       # TS2200 Library B (ERM 3.0V rated, 3.0V overdrive)
LIBRARY_TS2200C = 0x03       # TS2200 Library C (ERM 3.0V rated, 3.0V overdrive)
LIBRARY_TS2200D = 0x04       # TS2200 Library D (ERM 3.0V rated, 3.0V overdrive)
LIBRARY_TS2200E = 0x05       # TS2200 Library E (ERM 3.0V rated, 3.0V overdrive)
LIBRARY_LRA = 0x06           # LRA Library (closed-loop tuned for LRAs)
LIBRARY_TS2200F = 0x07       # TS2200 Library F (ERM 4.5V rated, 5.0V overdrive)

# ==============================================================================
# Bit Masks and Shift Values for Each Register (Sections 8.6.1 - 8.6.28)
# ==============================================================================

# --- STATUS Register (0x00, Section 8.6.1, Table 4) ---
DRV2605_BITMASK_STATUS = const(0xFF)
DRV2605_BITMASK_DEVICE_ID = const(0xE0)        # bits [7:5] Part number / device identifier
DRV2605_SHIFT_DEVICE_ID = const(5)
DRV2605_BITMASK_DIAG_RESULT = const(0x08)      # bit 3 Auto-cal / diagnostic result (0=passed, 1=failed)
DRV2605_SHIFT_DIAG_RESULT = const(3)
DRV2605_BITMASK_OVER_TEMP = const(0x02)        # bit 1 Overtemperature detection flag (0=normal, 1=overtemp)
DRV2605_SHIFT_OVER_TEMP = const(1)
DRV2605_BITMASK_OC_DETECT = const(0x01)        # bit 0 Overcurrent detection flag (0=normal, 1=overcurrent)
DRV2605_SHIFT_OC_DETECT = const(0)

# --- MODE Register (0x01, Section 8.6.2, Table 5) ---
DRV2605_BITMASK_MODE_REG = const(0xFF)
DRV2605_BITMASK_DEV_RESET = const(0x80)        # bit 7 Device reset (1=reset, self-clears)
DRV2605_SHIFT_DEV_RESET = const(7)
DRV2605_BITMASK_STANDBY = const(0x40)          # bit 6 Software standby mode (0=ready, 1=standby)
DRV2605_SHIFT_STANDBY = const(6)
DRV2605_BITMASK_MODE = const(0x07)             # bits [2:0] Operating mode selection
DRV2605_SHIFT_MODE = const(0)

# --- REAL-TIME PLAYBACK INPUT (RTPIN) Register (0x02, Section 8.6.3, Table 6) ---
DRV2605_BITMASK_RTPIN = const(0xFF)            # bits [7:0] Real-time playback input value
DRV2605_SHIFT_RTPIN = const(0)
DRV2605_BITMASK_RTP_INPUT = const(0xFF)
DRV2605_SHIFT_RTP_INPUT = const(0)

# --- LIBRARY SELECTION Register (0x03, Section 8.6.4, Table 7) ---
DRV2605_BITMASK_LIBRARY_REG = const(0xFF)
DRV2605_BITMASK_HI_Z = const(0x10)             # bit 4 Output driver high-impedance state
DRV2605_SHIFT_HI_Z = const(4)
DRV2605_BITMASK_LIBRARY = const(0x07)          # bits [2:0] Waveform library selection (0-7)
DRV2605_SHIFT_LIBRARY = const(0)
DRV2605_BITMASK_LIBRARY_SEL = const(0x07)
DRV2605_SHIFT_LIBRARY_SEL = const(0)

# --- WAVEFORM SEQUENCER Registers (0x04 to 0x0B, Section 8.6.5, Table 8) ---
DRV2605_BITMASK_WAVESEQ = const(0xFF)
DRV2605_BITMASK_WAVESEQ_WAIT = const(0x80)     # bit 7 (1=Wait delay time slot, 0=Waveform effect ID slot)
DRV2605_SHIFT_WAVESEQ_WAIT = const(7)
DRV2605_BITMASK_WAIT = const(0x80)
DRV2605_SHIFT_WAIT = const(7)
DRV2605_BITMASK_WAVESEQ_EFFECT = const(0x7F)   # bits [6:0] Waveform effect ID (1-123) or wait time (x 10ms)
DRV2605_SHIFT_WAVESEQ_EFFECT = const(0)
DRV2605_BITMASK_WAV_FRM_SEQ = const(0x7F)
DRV2605_SHIFT_WAV_FRM_SEQ = const(0)

# --- GO Register (0x0C, Section 8.6.6, Table 9) ---
DRV2605_BITMASK_GO_REG = const(0xFF)
DRV2605_BITMASK_GO = const(0x01)               # bit 0 Start/stop playback or routine (1=fire/active, 0=stop/done)
DRV2605_SHIFT_GO = const(0)

# --- OVERDRIVE TIME OFFSET (ODT) Register (0x0D, Section 8.6.7, Table 10) ---
DRV2605_BITMASK_OVERDRIVE = const(0xFF)        # bits [7:0] Overdrive time offset (signed 2s complement)
DRV2605_SHIFT_OVERDRIVE = const(0)
DRV2605_BITMASK_ODT = const(0xFF)
DRV2605_SHIFT_ODT = const(0)

# --- SUSTAIN TIME OFFSET POSITIVE (SPT) Register (0x0E, Section 8.6.8, Table 11) ---
DRV2605_BITMASK_SUSTAINPOS = const(0xFF)       # bits [7:0] Positive sustain time offset (signed 2s complement)
DRV2605_SHIFT_SUSTAINPOS = const(0)
DRV2605_BITMASK_SPT = const(0xFF)
DRV2605_SHIFT_SPT = const(0)

# --- SUSTAIN TIME OFFSET NEGATIVE (SNT) Register (0x0F, Section 8.6.9, Table 12) ---
DRV2605_BITMASK_SUSTAINNEG = const(0xFF)       # bits [7:0] Negative sustain time offset (signed 2s complement)
DRV2605_SHIFT_SUSTAINNEG = const(0)
DRV2605_BITMASK_SNT = const(0xFF)
DRV2605_SHIFT_SNT = const(0)

# --- BRAKE TIME OFFSET (BRT) Register (0x10, Section 8.6.10, Table 13) ---
DRV2605_BITMASK_BREAK = const(0xFF)            # bits [7:0] Brake time offset (signed 2s complement)
DRV2605_SHIFT_BREAK = const(0)
DRV2605_BITMASK_BRT = const(0xFF)
DRV2605_SHIFT_BRT = const(0)

# --- AUDIO-TO-VIBE CONTROL (AUDIOCTRL) Register (0x11, Section 8.6.11, Table 14) ---
DRV2605_BITMASK_AUDIOCTRL = const(0xFF)
DRV2605_BITMASK_ATH_CTRL = const(0xFF)
DRV2605_BITMASK_ATH_PEAK_TIME = const(0x0C)    # bits [3:2] Peak detection time (0=10ms, 1=20ms, 2=30ms, 3=40ms)
DRV2605_SHIFT_ATH_PEAK_TIME = const(2)
DRV2605_BITMASK_ATH_FILTER = const(0x03)       # bits [1:0] Low-pass filter frequency (0=100Hz, 1=125Hz, 2=150Hz, 3=200Hz)
DRV2605_SHIFT_ATH_FILTER = const(0)

# --- AUDIO-TO-VIBE MINIMUM INPUT LEVEL Register (0x12, Section 8.6.12, Table 15) ---
DRV2605_BITMASK_AUDIOLVL = const(0xFF)         # bits [7:0] Minimum detected input voltage level (Vpp = val * 1.8V / 255)
DRV2605_SHIFT_AUDIOLVL = const(0)
DRV2605_BITMASK_ATH_MIN_INPUT = const(0xFF)
DRV2605_SHIFT_ATH_MIN_INPUT = const(0)

# --- AUDIO-TO-VIBE MAXIMUM INPUT LEVEL Register (0x13, Section 8.6.13, Table 16) ---
DRV2605_BITMASK_AUDIOMAX = const(0xFF)         # bits [7:0] Full-scale input voltage level (Vpp = val * 1.8V / 255)
DRV2605_SHIFT_AUDIOMAX = const(0)
DRV2605_BITMASK_ATH_MAX_INPUT = const(0xFF)
DRV2605_SHIFT_ATH_MAX_INPUT = const(0)

# --- AUDIO-TO-VIBE MINIMUM OUTPUT DRIVE Register (0x14, Section 8.6.14, Table 17) ---
DRV2605_BITMASK_AUDIOMINDRV = const(0xFF)      # bits [7:0] Minimum output drive level applied (% = val / 255 * 100%)
DRV2605_SHIFT_AUDIOMINDRV = const(0)
DRV2605_BITMASK_ATH_MIN_DRIVE = const(0xFF)
DRV2605_SHIFT_ATH_MIN_DRIVE = const(0)

# --- AUDIO-TO-VIBE MAXIMUM OUTPUT DRIVE Register (0x15, Section 8.6.15, Table 18) ---
DRV2605_BITMASK_AUDIOMAXDRV = const(0xFF)      # bits [7:0] Maximum output drive level applied (% = val / 255 * 100%)
DRV2605_SHIFT_AUDIOMAXDRV = const(0)
DRV2605_BITMASK_ATH_MAX_DRIVE = const(0xFF)
DRV2605_SHIFT_ATH_MAX_DRIVE = const(0)

# --- RATED VOLTAGE Register (0x16, Section 8.6.16, Table 19) ---
DRV2605_BITMASK_RATEDV = const(0xFF)           # bits [7:0] Rated voltage reference for full scale closed-loop drive
DRV2605_SHIFT_RATEDV = const(0)
DRV2605_BITMASK_RATED_VOLTAGE = const(0xFF)
DRV2605_SHIFT_RATED_VOLTAGE = const(0)

# --- OVERDRIVE CLAMP VOLTAGE Register (0x17, Section 8.6.17, Table 20) ---
DRV2605_BITMASK_CLAMPV = const(0xFF)           # bits [7:0] Overdrive voltage clamp and open-loop reference
DRV2605_SHIFT_CLAMPV = const(0)
DRV2605_BITMASK_OD_CLAMP = const(0xFF)
DRV2605_SHIFT_OD_CLAMP = const(0)

# --- AUTO-CALIBRATION COMPENSATION RESULT Register (0x18, Section 8.6.18, Table 21) ---
DRV2605_BITMASK_AUTOCALCOMP = const(0xFF)      # bits [7:0] Auto-calibration compensation result for resistive losses
DRV2605_SHIFT_AUTOCALCOMP = const(0)
DRV2605_BITMASK_A_CAL_COMP = const(0xFF)
DRV2605_SHIFT_A_CAL_COMP = const(0)

# --- AUTO-CALIBRATION BACK-EMF RESULT Register (0x19, Section 8.6.19, Table 22) ---
DRV2605_BITMASK_AUTOCALEMP = const(0xFF)       # bits [7:0] Auto-calibration rated back-EMF result
DRV2605_SHIFT_AUTOCALEMP = const(0)
DRV2605_BITMASK_A_CAL_BEMF = const(0xFF)
DRV2605_SHIFT_A_CAL_BEMF = const(0)

# --- FEEDBACK CONTROL Register (0x1A, Section 8.6.20, Table 23) ---
DRV2605_BITMASK_FEEDBACK = const(0xFF)
DRV2605_BITMASK_N_ERM_LRA = const(0x80)        # bit 7 Actuator type (0=ERM Mode, 1=LRA Mode)
DRV2605_SHIFT_N_ERM_LRA = const(7)
DRV2605_BITMASK_ERM_LRA = const(0x80)
DRV2605_SHIFT_ERM_LRA = const(7)
DRV2605_BITMASK_FEEDBACK_LRA = const(0x80)     # Alias
DRV2605_SHIFT_FEEDBACK_LRA = const(7)
DRV2605_BITMASK_FB_BRAKE_FACTOR = const(0x70)  # bits [6:4] Feedback brake factor ratio (0=1x to 6=16x, 7=disabled)
DRV2605_SHIFT_FB_BRAKE_FACTOR = const(4)
DRV2605_BITMASK_LOOP_GAIN = const(0x0C)        # bits [3:2] Feedback loop gain (0=Low, 1=Medium, 2=High, 3=Very High)
DRV2605_SHIFT_LOOP_GAIN = const(2)
DRV2605_BITMASK_BEMF_GAIN = const(0x03)        # bits [1:0] Back-EMF amplifier analog gain
DRV2605_SHIFT_BEMF_GAIN = const(0)
DRV2605_BITMASK_FEEDBACK_VALUE = const(0x7F)   # bits [6:0] Feedback parameters
DRV2605_SHIFT_FEEDBACK_VALUE = const(0)

# --- CONTROL1 Register (0x1B, Section 8.6.21, Table 24) ---
DRV2605_BITMASK_CONTROL1 = const(0xFF)
DRV2605_BITMASK_STARTUP_BOOST = const(0x80)    # bit 7 Overdrive startup boost enable (0=disabled, 1=enabled)
DRV2605_SHIFT_STARTUP_BOOST = const(7)
DRV2605_BITMASK_AC_COUPLE = const(0x20)        # bit 5 Apply 0.9V bias to IN/TRIG for AC coupling (1=enabled)
DRV2605_SHIFT_AC_COUPLE = const(5)
DRV2605_BITMASK_DRIVE_TIME = const(0x1F)       # bits [4:0] LRA drive time / ERM sample rate
DRV2605_SHIFT_DRIVE_TIME = const(0)

# --- CONTROL2 Register (0x1C, Section 8.6.22, Table 25) ---
DRV2605_BITMASK_CONTROL2 = const(0xFF)
DRV2605_BITMASK_BIDIR_INPUT = const(0x80)      # bit 7 Data interpretation mode (0=Unidirectional, 1=Bidirectional)
DRV2605_SHIFT_BIDIR_INPUT = const(7)
DRV2605_BITMASK_BRAKE_STABILIZER = const(0x40) # bit 6 Reduce loop gain when braking near completion (1=enabled)
DRV2605_SHIFT_BRAKE_STABILIZER = const(6)
DRV2605_BITMASK_SAMPLE_TIME = const(0x30)      # bits [5:4] LRA auto-resonance sample time (0=150us, 1=200us, 2=250us, 3=300us)
DRV2605_SHIFT_SAMPLE_TIME = const(4)
DRV2605_BITMASK_BLANKING_TIME = const(0x0C)    # bits [3:2] Blanking time LSBs [1:0]
DRV2605_SHIFT_BLANKING_TIME = const(2)
DRV2605_BITMASK_BLANKING_TIME_1_0 = const(0x0C)
DRV2605_SHIFT_BLANKING_TIME_1_0 = const(2)
DRV2605_BITMASK_IDISS_TIME = const(0x03)       # bits [1:0] Current dissipation time LSBs [1:0]
DRV2605_SHIFT_IDISS_TIME = const(0)
DRV2605_BITMASK_IDISS_TIME_1_0 = const(0x03)
DRV2605_SHIFT_IDISS_TIME_1_0 = const(0)

# --- CONTROL3 Register (0x1D, Section 8.6.23, Table 26) ---
DRV2605_BITMASK_CONTROL3 = const(0xFF)
DRV2605_BITMASK_NG_THRESH = const(0xC0)        # bits [7:6] Noise gate threshold (0=disabled, 1=2%, 2=4%, 3=8%)
DRV2605_SHIFT_NG_THRESH = const(6)
DRV2605_BITMASK_ERM_OPEN_LOOP = const(0x20)    # bit 5 ERM open-loop mode (0=Closed Loop, 1=Open Loop)
DRV2605_SHIFT_ERM_OPEN_LOOP = const(5)
DRV2605_BITMASK_CONTROL3_ERM_OPEN_LOOP = const(0x20) # Alias
DRV2605_SHIFT_CONTROL3_ERM_OPEN_LOOP = const(5)
DRV2605_BITMASK_SUPPLY_COMP_DIS = const(0x10)  # bit 4 Supply compensation disable (0=enabled, 1=disabled)
DRV2605_SHIFT_SUPPLY_COMP_DIS = const(4)
DRV2605_BITMASK_DATA_FORMAT_RTP = const(0x08)  # bit 3 RTP input data format (0=signed 2s complement, 1=unsigned)
DRV2605_SHIFT_DATA_FORMAT_RTP = const(3)
DRV2605_BITMASK_LRA_DRIVE_MODE = const(0x04)   # bit 2 LRA drive mode update rate (0=once per cycle, 1=twice per cycle)
DRV2605_SHIFT_LRA_DRIVE_MODE = const(2)
DRV2605_BITMASK_N_PWM_ANALOG = const(0x02)     # bit 1 Input mode for IN/TRIG when MODE=3 (0=PWM input, 1=analog input)
DRV2605_SHIFT_N_PWM_ANALOG = const(1)
DRV2605_BITMASK_LRA_OPEN_LOOP = const(0x01)    # bit 0 LRA open-loop mode (0=Auto-resonance mode, 1=Open-loop mode)
DRV2605_SHIFT_LRA_OPEN_LOOP = const(0)

# --- CONTROL4 Register (0x1E, Section 8.6.24, Table 27) ---
DRV2605_BITMASK_CONTROL4 = const(0xFF)
DRV2605_BITMASK_ZC_DET_TIME = const(0xC0)      # bits [7:6] Zero-crossing detect minimum time (0=100us, 1=200us, 2=300us, 3=390us)
DRV2605_SHIFT_ZC_DET_TIME = const(6)
DRV2605_BITMASK_AUTO_CAL_TIME = const(0x30)    # bits [5:4] Auto-calibration time (0=150-350ms, 1=250-450ms, 2=500-700ms, 3=1000-1200ms)
DRV2605_SHIFT_AUTO_CAL_TIME = const(4)
DRV2605_BITMASK_OTP_STATUS = const(0x04)       # bit 2 OTP memory programmed status (0=not programmed, 1=programmed) (RO)
DRV2605_SHIFT_OTP_STATUS = const(2)
DRV2605_BITMASK_OTP_PROGRAM = const(0x01)      # bit 0 Program OTP nonvolatile memory (write 1 to burn 0x16-0x1A)
DRV2605_SHIFT_OTP_PROGRAM = const(0)

# --- CONTROL5 Register (0x1F, Section 8.6.25, Table 28) ---
DRV2605_BITMASK_CONTROL5 = const(0xFF)
DRV2605_BITMASK_AUTO_OL_CNT = const(0xC0)      # bits [7:6] Non-synced cycles before auto open-loop (0=3, 1=4, 2=5, 3=6 attempts)
DRV2605_SHIFT_AUTO_OL_CNT = const(6)
DRV2605_BITMASK_LRA_AUTO_OPEN_LOOP = const(0x20) # bit 5 Auto open-loop transition on lost BEMF (0=never, 1=auto transition)
DRV2605_SHIFT_LRA_AUTO_OPEN_LOOP = const(5)
DRV2605_BITMASK_PLAYBACK_INTERVAL = const(0x10)  # bit 4 Memory playback interval (0=5ms, 1=1ms)
DRV2605_SHIFT_PLAYBACK_INTERVAL = const(4)
DRV2605_BITMASK_BLANKING_TIME_3_2 = const(0x0C)  # bits [3:2] MSBs [3:2] for LRA blanking time
DRV2605_SHIFT_BLANKING_TIME_3_2 = const(2)
DRV2605_BITMASK_IDISS_TIME_3_2 = const(0x03)     # bits [1:0] MSBs [3:2] for LRA current dissipation time
DRV2605_SHIFT_IDISS_TIME_3_2 = const(0)

# --- LRA OPEN LOOP PERIOD (OL_LRA_PERIOD) Register (0x20, Section 8.6.26, Table 29) ---
DRV2605_BITMASK_LRA_OL_PERIOD = const(0x7F)    # bits [6:0] LRA open-loop period (period = val * 98.46 us)
DRV2605_SHIFT_LRA_OL_PERIOD = const(0)
DRV2605_BITMASK_OL_LRA_PERIOD = const(0x7F)
DRV2605_SHIFT_OL_LRA_PERIOD = const(0)

# --- V(BAT) VOLTAGE MONITOR (VBAT) Register (0x21, Section 8.6.27, Table 30) ---
DRV2605_BITMASK_VBAT = const(0xFF)             # bits [7:0] Real-time VDD voltage reading (VDD = val * 5.6V / 255)
DRV2605_SHIFT_VBAT = const(0)

# --- LRA RESONANCE PERIOD (LRA_PERIOD) Register (0x22, Section 8.6.28, Table 31) ---
DRV2605_BITMASK_LRARESON = const(0xFF)         # bits [7:0] Real-time LRA resonance period (period = val * 98.46 us)
DRV2605_SHIFT_LRARESON = const(0)
DRV2605_BITMASK_LRA_PERIOD = const(0xFF)
DRV2605_SHIFT_LRA_PERIOD = const(0)

# ==============================================================================
# Register Field Enums & Setting Values (From Spec-DRV2605L.pdf Tables 4-31)
# ==============================================================================

# Device Identification (STATUS 0x00, DEVICE_ID[2:0], Table 4)
DEVICE_ID_DRV2605 = const(3)     # Contains licensed ROM library, does not contain RAM
DEVICE_ID_DRV2604 = const(4)     # Contains RAM, does not contain licensed ROM library
DEVICE_ID_DRV2604L = const(6)    # Low-voltage version of DRV2604
DEVICE_ID_DRV2605L = const(7)    # Low-voltage version of DRV2605

# Actuator Type Selection (FEEDBACK 0x1A, N_ERM_LRA bit 7, Table 23)
ACTUATOR_ERM = const(0)          # ERM mode
ACTUATOR_LRA = const(1)          # LRA mode

# Feedback Brake Factor (FEEDBACK 0x1A, FB_BRAKE_FACTOR[2:0], Table 23)
FB_BRAKE_FACTOR_1X = const(0)
FB_BRAKE_FACTOR_2X = const(1)
FB_BRAKE_FACTOR_3X = const(2)
FB_BRAKE_FACTOR_4X = const(3)    # Default
FB_BRAKE_FACTOR_6X = const(4)
FB_BRAKE_FACTOR_8X = const(5)
FB_BRAKE_FACTOR_16X = const(6)
FB_BRAKE_FACTOR_DISABLED = const(7)

# Loop Gain (FEEDBACK 0x1A, LOOP_GAIN[1:0], Table 23)
LOOP_GAIN_LOW = const(0)
LOOP_GAIN_MEDIUM = const(1)      # Default
LOOP_GAIN_HIGH = const(2)
LOOP_GAIN_VERY_HIGH = const(3)

# Back-EMF Gain (FEEDBACK 0x1A, BEMF_GAIN[1:0], Table 23)
# ERM Mode: 0: 0.255x, 1: 0.7875x, 2: 1.365x (default), 3: 3.0x
# LRA Mode: 0: 3.75x,  1: 7.5x,    2: 15x (default),    3: 22.5x
BEMF_GAIN_0 = const(0)
BEMF_GAIN_1 = const(1)
BEMF_GAIN_2 = const(2)           # Default
BEMF_GAIN_3 = const(3)

# Control1 (0x1B, Table 24)
STARTUP_BOOST_OFF = const(0)
STARTUP_BOOST_ON = const(1)      # Default
AC_COUPLE_OFF = const(0)         # Default (common-mode drive disabled)
AC_COUPLE_ON = const(1)          # Common-mode drive enabled (0.9V bias)

# Control2 (0x1C, Table 25)
BIDIR_INPUT_UNIDIRECTIONAL = const(0)
BIDIR_INPUT_BIDIRECTIONAL = const(1) # Default
BRAKE_STABILIZER_OFF = const(0)
BRAKE_STABILIZER_ON = const(1)       # Default
SAMPLE_TIME_150US = const(0)
SAMPLE_TIME_200US = const(1)
SAMPLE_TIME_250US = const(2)
SAMPLE_TIME_300US = const(3)         # Default

# Control3 (0x1D, Table 26)
NG_THRESH_DISABLED = const(0)
NG_THRESH_2_PERCENT = const(1)
NG_THRESH_4_PERCENT = const(2)       # Default
NG_THRESH_8_PERCENT = const(3)
ERM_LOOP_CLOSED = const(0)
ERM_LOOP_OPEN = const(1)             # Default
SUPPLY_COMP_ENABLED = const(0)       # Default
SUPPLY_COMP_DISABLED = const(1)
DATA_FORMAT_RTP_SIGNED = const(0)    # Default (signed 2s complement)
DATA_FORMAT_RTP_UNSIGNED = const(1)
LRA_DRIVE_MODE_ONCE = const(0)       # Default (once per cycle)
LRA_DRIVE_MODE_TWICE = const(1)      # Twice per cycle
INPUT_MODE_PWM = const(0)            # Default
INPUT_MODE_ANALOG = const(1)
LRA_AUTO_RESONANCE = const(0)        # Default
LRA_OPEN_LOOP = const(1)

# Control4 (0x1E, Table 27)
ZC_DET_TIME_100US = const(0)         # Default
ZC_DET_TIME_200US = const(1)
ZC_DET_TIME_300US = const(2)
ZC_DET_TIME_390US = const(3)
AUTO_CAL_TIME_150_350MS = const(0)
AUTO_CAL_TIME_250_450MS = const(1)
AUTO_CAL_TIME_500_700MS = const(2)   # Default
AUTO_CAL_TIME_1000_1200MS = const(3)
OTP_STATUS_NOT_PROGRAMMED = const(0) # Default
OTP_STATUS_PROGRAMMED = const(1)

# Control5 (0x1F, Table 28)
AUTO_OL_CNT_3_ATTEMPTS = const(0)
AUTO_OL_CNT_4_ATTEMPTS = const(1)
AUTO_OL_CNT_5_ATTEMPTS = const(2)    # Default
AUTO_OL_CNT_6_ATTEMPTS = const(3)
LRA_AUTO_OPEN_LOOP_NEVER = const(0)  # Default
LRA_AUTO_OPEN_LOOP_AUTO = const(1)
PLAYBACK_INTERVAL_5MS = const(0)     # Default
PLAYBACK_INTERVAL_1MS = const(1)

# Audio-to-Vibe Control (0x11, Table 14)
ATH_PEAK_TIME_10MS = const(0)
ATH_PEAK_TIME_20MS = const(1)        # Default
ATH_PEAK_TIME_30MS = const(2)
ATH_PEAK_TIME_40MS = const(3)
ATH_FILTER_100HZ = const(0)
ATH_FILTER_125HZ = const(1)          # Default
ATH_FILTER_150HZ = const(2)
ATH_FILTER_200HZ = const(3)

# ==============================================================================
# Helper Utilities for Register Field Manipulation
# ==============================================================================
def get_field_byte(byte_val: int, mask: int, shift: int) -> int:
	"""Extract a field value from a register byte.

	Args:
		byte_val: the original register byte value
		mask: bitmask for the field (e.g. 0xE0)
		shift: right shift of the field (number of LSBs)

	Returns:
		The integer value of the field (already shifted down).
	"""
	return (byte_val & mask) >> shift


def set_field_byte(old_byte: int, mask: int, shift: int, new_value: int) -> int:
	"""Return a new byte with the field replaced by `new_value`.

	Verifies that `new_value` fits into the field width implied by mask/shift.

	Args:
		old_byte: original register byte
		mask: bitmask for the field
		shift: right shift of the field
		new_value: integer value to place into the field

	Returns:
		New byte with the field updated.

	Raises:
		ValueError if `new_value` is too large for the field or negative.
	"""
	if shift < 0:
		raise ValueError("shift must be >= 0")
	# compute max value allowed by mask
	max_val = mask >> shift
	if new_value < 0 or new_value > max_val:
		raise ValueError("new_value %r out of range for mask 0x%02X (max %r)" % (new_value, mask, max_val))
	# clear field bits then set new value
	cleared = old_byte & (~mask & 0xFF)
	return cleared | ((new_value << shift) & mask)
