"""The MIDI layouts of the board: what every pad and mechanical key sends, and how it looks.

A layout is one entry per key, in the order the pads are drawn in landscape (game/landscape.py):
index = row * 8 + column, row 0 is the top row and row 3 the bottom one, on the side with the
mechanical keys. Index 32 is the left mechanical key, 33 the right one. See keyboard/MIDI_LAYOUTS.md
for the sketches, the key mappings and the colour code.

Every entry has:
  type    what the key does: "note", "drum", "cc", "pc", "pitch", "panic", "accent", "roll"
          (reserved), "none", and in the menu "load", "set_ch", "oct_up", "oct_dn", "reset",
          "sleep", "exit"
  val     note number, CC number, program number, or the value of a menu key
  ch      the channel the key was meant for - kept as a backup, not used: everything goes out on
          the channel selected in the menu, only "drum" keys always play on MIDI_DRUM_CHANNEL
  color   colour of the key while it is idle
  flash   colour while it is pressed, toggled on, or shows the current setting in the menu
  mode    "momentary" (acts on press and release) or "toggle" (flips on every press)
  state   toggle state, kept here while the board runs
  haptic  DRV2605L effect played on press, 0 for none
  value   optional: a momentary CC key that sends this one fixed value on press
"""
import pico_config as config

# ==============================================================================
# LAYOUT 1: MELODIC SYNTH KEYBOARD
# ==============================================================================
_LAYOUT_1_SYNTH = (
    # --- ROW 1: Presets (PC) ---
    {"type": "pc", "val": 0, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 0
    {"type": "pc", "val": 4, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 1
    {"type": "pc", "val": 26, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 2
    {"type": "pc", "val": 29, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 3
    {"type": "pc", "val": 38, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 4
    {"type": "pc", "val": 80, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 5
    {"type": "pc", "val": 88, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 6
    {"type": "pc", "val": 81, "ch": 1, "color": (0, 0, 30), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 10}, # 7

    # --- ROW 2: Utility ---
    {"type": "oct_dn", "val": -12, "ch": 1, "color": (30, 15, 0), "flash": (255, 150, 0), "mode": "momentary", "state": False, "haptic": 10}, # 8
    {"type": "oct_up", "val": 12,  "ch": 1, "color": (30, 15, 0), "flash": (255, 150, 0), "mode": "momentary", "state": False, "haptic": 10}, # 9
    {"type": "cc",     "val": 1,   "ch": 1, "color": (0, 30, 0),  "flash": (0, 255, 0),   "mode": "toggle",    "state": False, "haptic": 10}, # 10: Mod Toggle
    {"type": "cc",     "val": 64,  "ch": 1, "color": (0, 30, 0),  "flash": (0, 255, 0),   "mode": "momentary", "state": False, "haptic": 10}, # 11: Sustain
    {"type": "cc",     "val": 74,  "ch": 1, "color": (0, 30, 0),  "flash": (0, 255, 0),   "mode": "momentary", "state": False, "haptic": 10, "value": 0},   # 12: Filter closed
    {"type": "cc",     "val": 74,  "ch": 1, "color": (0, 30, 0),  "flash": (0, 255, 0),   "mode": "momentary", "state": False, "haptic": 10, "value": 127}, # 13: Filter open
    {"type": "panic",  "val": 123, "ch": 1, "color": (30, 0, 0),  "flash": (255, 0, 0),   "mode": "momentary", "state": False, "haptic": 10}, # 14: Panic
    {"type": "none",   "val": 0,   "ch": 1, "color": (0, 0, 0),   "flash": (0, 0, 0),     "mode": "momentary", "state": False, "haptic": 0},  # 15

    # --- ROW 3: Black Keys ---
    {"type": "note",  "val": 61, "ch": 1, "color": (40, 0, 40), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 16: C#
    {"type": "note",  "val": 63, "ch": 1, "color": (40, 0, 40), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 17: D#
    {"type": "cc",    "val": 1,  "ch": 1, "color": (5, 5, 5),   "flash": (0, 255, 255),   "mode": "momentary", "state": False, "haptic": 10}, # 18: Mod Max
    {"type": "note",  "val": 66, "ch": 1, "color": (40, 0, 40), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 19: F#
    {"type": "note",  "val": 68, "ch": 1, "color": (40, 0, 40), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 20: G#
    {"type": "note",  "val": 70, "ch": 1, "color": (40, 0, 40), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 21: A#
    {"type": "pitch", "val": -1, "ch": 1, "color": (5, 5, 5),   "flash": (0, 255, 255),   "mode": "momentary", "state": False, "haptic": 10}, # 22: Pitch Dn
    {"type": "pitch", "val": 1,  "ch": 1, "color": (5, 5, 5),   "flash": (0, 255, 255),   "mode": "momentary", "state": False, "haptic": 10}, # 23: Pitch Up

    # --- ROW 4: White Keys ---
    {"type": "note", "val": 60, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 24: C
    {"type": "note", "val": 62, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 25: D
    {"type": "note", "val": 64, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 26: E
    {"type": "note", "val": 65, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 27: F
    {"type": "note", "val": 67, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 28: G
    {"type": "note", "val": 69, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 29: A
    {"type": "note", "val": 71, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 30: B
    {"type": "note", "val": 72, "ch": 1, "color": (30, 30, 25), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 31: High C

    # --- MECH KEYS: drums, always on the drum channel so they sound right on any selected channel ---
    {"type": "drum", "val": 36, "ch": 10, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 32: Mech 1 (Kick)
    {"type": "drum", "val": 38, "ch": 10, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 33: Mech 2 (Snare)
)

# ==============================================================================
# LAYOUT 2: 16-PAD FINGER DRUMMING & SEQUENCER
# ==============================================================================
_LAYOUT_2_DRUMS = (
    # --- ROW 1 & 2: Drums A & B ---
    {"type": "note", "val": 36, "ch": 10, "color": (0, 30, 30), "flash": (0, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 0
    {"type": "note", "val": 38, "ch": 10, "color": (0, 30, 30), "flash": (0, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 1
    {"type": "note", "val": 42, "ch": 10, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "momentary", "state": False, "haptic": 12}, # 2
    {"type": "note", "val": 46, "ch": 10, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "momentary", "state": False, "haptic": 12}, # 3
    {"type": "note", "val": 60, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 4
    {"type": "note", "val": 61, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 5
    {"type": "note", "val": 62, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 6
    {"type": "note", "val": 63, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 7

    {"type": "note", "val": 35, "ch": 10, "color": (0, 30, 30), "flash": (0, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 8
    {"type": "note", "val": 40, "ch": 10, "color": (0, 30, 30), "flash": (0, 255, 255), "mode": "momentary", "state": False, "haptic": 12}, # 9
    {"type": "note", "val": 50, "ch": 10, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "momentary", "state": False, "haptic": 12}, # 10
    {"type": "note", "val": 41, "ch": 10, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "momentary", "state": False, "haptic": 12}, # 11
    {"type": "note", "val": 64, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 12
    {"type": "note", "val": 65, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 13
    {"type": "note", "val": 66, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 14
    {"type": "note", "val": 67, "ch": 2,  "color": (30, 0, 15), "flash": (255, 0, 127), "mode": "momentary", "state": False, "haptic": 12}, # 15

    # # --- ROW 3 & 4: Sequencer Steps ---
    # {"type": "seq", "val": 1, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 16 to 23...
    # {"type": "seq", "val": 2, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 3, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 4, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 5, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 6, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 7, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 8, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},

    # {"type": "seq", "val": 9,  "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 24 to 31...
    # {"type": "seq", "val": 10, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 11, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 12, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 13, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 14, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 15, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},
    # {"type": "seq", "val": 16, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10},

    # --- ROW 3: Sequencer Steps 1-8 (Mapped to CC 60-67) ---
    {"type": "cc", "val": 60, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 16
    {"type": "cc", "val": 61, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 17
    {"type": "cc", "val": 62, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 18
    {"type": "cc", "val": 63, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 19
    {"type": "cc", "val": 64, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 20
    {"type": "cc", "val": 65, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 21
    {"type": "cc", "val": 66, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 22
    {"type": "cc", "val": 67, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 23

    # --- ROW 4: Sequencer Steps 9-16 (Mapped to CC 68-75) ---
    {"type": "cc", "val": 68, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 24
    {"type": "cc", "val": 69, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 25
    {"type": "cc", "val": 70, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 26
    {"type": "cc", "val": 71, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 27
    {"type": "cc", "val": 72, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 28
    {"type": "cc", "val": 73, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 29
    {"type": "cc", "val": 74, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 30
    {"type": "cc", "val": 75, "ch": 10, "color": (10, 10, 10), "flash": (255, 255, 255), "mode": "toggle", "state": False, "haptic": 10}, # 31

    # --- MECH KEYS ---
    {"type": "accent", "val": 127, "ch": 0, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 32
    {"type": "roll",   "val": 0,   "ch": 0, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 33
)

# ==============================================================================
# LAYOUT 3: DAW CONTROL & TRANSPORT
# ==============================================================================
_LAYOUT_3_DAW = (
    # --- ROW 1: Mutes ---
    {"type": "cc", "val": 16, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10}, # 0 to 7...
    {"type": "cc", "val": 17, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 18, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 19, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 20, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 21, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 22, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 23, "ch": 1, "color": (30, 0, 0), "flash": (255, 0, 0), "mode": "toggle", "state": False, "haptic": 10},

    # --- ROW 2: Solos ---
    {"type": "cc", "val": 24, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10}, # 8 to 15...
    {"type": "cc", "val": 25, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 26, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 27, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 28, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 29, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 30, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 31, "ch": 1, "color": (30, 30, 0), "flash": (255, 255, 0), "mode": "toggle", "state": False, "haptic": 10},

    # --- ROW 3: Select ---
    {"type": "cc", "val": 32, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10}, # 16 to 23...
    {"type": "cc", "val": 33, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 34, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 35, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 36, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 37, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 38, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},
    {"type": "cc", "val": 39, "ch": 1, "color": (0, 0, 30), "flash": (0, 0, 255), "mode": "toggle", "state": False, "haptic": 10},

    # --- ROW 4: Launch ---
    {"type": "cc", "val": 40, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12}, # 24 to 31...
    {"type": "cc", "val": 41, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 42, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 43, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 44, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 45, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 46, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},
    {"type": "cc", "val": 47, "ch": 1, "color": (0, 30, 0), "flash": (0, 255, 0), "mode": "momentary", "state": False, "haptic": 12},

    # --- MECH KEYS ---
    {"type": "cc", "val": 115, "ch": 1, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "toggle", "state": False, "haptic": 0}, # 32
    {"type": "cc", "val": 114, "ch": 1, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "toggle", "state": False, "haptic": 0}, # 33
)

# ==============================================================================
# LAYOUT 4: SYSTEM MENU
# ==============================================================================
_LAYOUT_MENU = (
    # --- ROW 1: Layout Selection ---
    {"type": "load", "val": 1, "ch": 0, "color": (0, 100, 100), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 0
    {"type": "load", "val": 2, "ch": 0, "color": (0, 100, 100), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 1
    {"type": "load", "val": 3, "ch": 0, "color": (0, 100, 100), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 2
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0),     "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 3
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0),     "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 4
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0),     "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 5
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0),     "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 6
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0),     "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 7

    # --- ROW 2: MIDI Channel 1-8 ---
    {"type": "set_ch", "val": 1, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 8 to 15...
    {"type": "set_ch", "val": 2, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 3, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 4, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 5, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 6, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 7, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 8, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},

    # --- ROW 3: MIDI Channel 9-16 ---
    {"type": "set_ch", "val": 9,  "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 16 to 23...
    {"type": "set_ch", "val": 10, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, 
    {"type": "set_ch", "val": 11, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 12, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 13, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 14, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 15, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},
    {"type": "set_ch", "val": 16, "ch": 0, "color": (15, 15, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4},

    # --- ROW 4: System Actions ---
    {"type": "none",  "val": 0, "ch": 0, "color": (0, 0, 0),   "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 24
    {"type": "none",  "val": 0, "ch": 0, "color": (0, 0, 0),   "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 25
    {"type": "none",  "val": 0, "ch": 0, "color": (0, 0, 0),   "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 26
    {"type": "none",  "val": 0, "ch": 0, "color": (0, 0, 0),   "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 27
    {"type": "none",  "val": 0, "ch": 0, "color": (0, 0, 0),   "flash": (0, 0, 0),       "mode": "momentary", "state": False, "haptic": 0}, # 28
    {"type": "reset", "val": 0, "ch": 0, "color": (50, 0, 0),  "flash": (255, 0, 0),     "mode": "momentary", "state": False, "haptic": 4}, # 29
    {"type": "sleep", "val": 0, "ch": 0, "color": (50, 0, 0),  "flash": (255, 0, 0),     "mode": "momentary", "state": False, "haptic": 4}, # 30
    {"type": "exit",  "val": 0, "ch": 0, "color": (100, 0, 0), "flash": (255, 255, 255), "mode": "momentary", "state": False, "haptic": 4}, # 31

    # --- MECH KEYS: nothing, holding both for 2 s leaves the menu again ---
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 32
    {"type": "none", "val": 0, "ch": 0, "color": (0, 0, 0), "flash": (0, 0, 0), "mode": "momentary", "state": False, "haptic": 0}, # 33
)



LAYOUT_NAMES = ("Menu", "Synth keyboard", "Drums and sequencer", "DAW control")
MIN_OCTAVE = -4
MAX_OCTAVE = 4
ALL_NOTES_OFF = 123  # CC number of the panic / reset key


class MidiBoardLayout:
    """The MIDI layouts of the board and their live state: which layout is shown, the MIDI channel,
    the octave shift, the toggles and the accent key (see keyboard/MIDI_LAYOUTS.md)."""

    __slots__ = ["reverse_lookup_table",
                 "layouts",
                 "current_layout_index",
                 "selected_layout",
                 "channel",
                 "octave_offset",
                 "accent",
                 "display_dim",]
    def __init__(self):
        self.layouts = [_LAYOUT_MENU, _LAYOUT_1_SYNTH, _LAYOUT_2_DRUMS, _LAYOUT_3_DAW]
        self.current_layout_index = 1
        self.selected_layout = 1
        self.channel = 1
        self.octave_offset = 0
        self.accent = False
        self.display_dim = False
        self.reverse_lookup_table = {}
        # The layout data lives in this module, so toggle states would survive a reconnect
        self._reset_states()
        self._generate_reverse_lookup_table()

    def _reset_states(self):
        for layout in self.layouts:
            for key_config in layout:
                key_config["state"] = False

    def layout_name(self, index=None):
        index = self.current_layout_index if index is None else index
        return LAYOUT_NAMES[index] if 0 <= index < len(LAYOUT_NAMES) else "Layout %d" % index

    def _generate_reverse_lookup_table(self):
        """Which key of the current layout sends a given MIDI message, so an echo from the host
        lights the right key.

        get_midi_message() sends every note, CC and program change on self.channel, the one channel
        selected in the menu; the "ch" field of a key is a backup and not used. The exception are
        "drum" keys, which always play on MIDI_DRUM_CHANNEL. This table has to match what is
        actually sent, so it is built the same way and rebuilt whenever the channel or the octave
        changes (see set_channel() and set_octave()).
        """
        self.reverse_lookup_table.clear()
        ch_idx = self.channel - 1  # wire-format MIDI channels are 0-indexed
        for index, key_config in enumerate(self.layouts[self.current_layout_index]):
            type = key_config["type"]
            if type not in ("note", "drum", "cc", "pc"):
                continue  # Skip non-MIDI types
            value = key_config["val"]

            if type == "drum":
                drum_idx = config.MIDI_DRUM_CHANNEL - 1
                self.reverse_lookup_table[(0x90 | drum_idx, value & 0x7F)] = index
                self.reverse_lookup_table[(0x80 | drum_idx, value & 0x7F)] = index
            elif type == "note":
                note = self._note_value(value)  # the octave shift moves the notes we send, so it moves the echo too
                self.reverse_lookup_table[(0x90 | ch_idx, note)] = index
                self.reverse_lookup_table[(0x80 | ch_idx, note)] = index
            elif type == "cc":
                self.reverse_lookup_table[(0xB0 | ch_idx, value)] = index
            elif type == "pc":
                self.reverse_lookup_table[(0xC0 | ch_idx, value)] = index

    def is_menu_layout(self):
        """Check if the current layout is the menu layout."""
        return self.current_layout_index == 0

    def _key_config(self, key):
        if not 0 <= key < len(self.layouts[self.current_layout_index]):
            raise IndexError("Key index out of range for current layout.")
        return self.layouts[self.current_layout_index][key]

    def _note_value(self, value):
        return max(0, min(127, value + self.octave_offset * 12))

    def key_pressed(self, key, pressed):
        """Update the layout state for a key that went down or up: toggles, the accent key and the
        menu keys (octave, channel, layout select, reset, dim). The MIDI message of the key comes
        from get_midi_message() afterwards.

        Returns True when this key loaded another layout: the key numbers mean something else now,
        so the caller must not ask for this key's message any more."""
        key_config = self._key_config(key)
        type = key_config["type"]

        if key_config["mode"] == "toggle" and pressed:
            key_config["state"] = not key_config["state"]
        if type == "accent":
            self.accent = pressed  # held: notes are sent with the accent velocity
        if not pressed:
            return False

        if type == "oct_up":
            self.set_octave(self.octave_offset + 1)
        elif type == "oct_dn":
            self.set_octave(self.octave_offset - 1)
        elif type == "set_ch":
            self.set_channel(key_config["val"])
        elif type == "load":
            self.selected_layout = key_config["val"]
        elif type == "exit":
            self.load_layout(self.selected_layout)
            return True  # this key is part of another layout now
        elif type == "reset":
            self.reset()
        elif type == "sleep":
            self.display_dim = not self.display_dim
        return False

    def get_haptic_feedback(self, key):
        """Get the haptic feedback value for a specific key based on the current layout."""
        return self._key_config(key)["haptic"]

    def get_key_color(self, key, pressed=False):
        """Colour of a key: its flash colour while it is pressed, toggled on, or shows the current
        setting in the menu (selected layout, selected channel); its base colour otherwise."""
        key_config = self._key_config(key)
        return key_config["flash"] if pressed or self._is_active(key_config) else key_config["color"]

    def _is_active(self, key_config):
        if key_config["mode"] == "toggle" and key_config["state"]:
            return True
        type = key_config["type"]
        if type == "load":
            return key_config["val"] == self.selected_layout
        if type == "set_ch":
            return key_config["val"] == self.channel
        if type == "accent":
            return self.accent
        if type == "sleep":
            return self.display_dim
        return False

    def get_key_from_midi_message(self, message):
        """Get the key index from a MIDI message based on the current layout."""
        if len(message) < 2:
            raise ValueError("MIDI message must have at least two bytes.")
        status_byte = message[0]
        data_byte = message[1]
        return self.reverse_lookup_table.get((status_byte, data_byte), None)

    def get_midi_message(self, key, pressed):
        """The MIDI message a key sends, or None when it sends nothing (menu keys, and the release
        of keys that only act on press). Everything goes out on the layout's current channel."""
        key_config = self._key_config(key)
        value = key_config["val"]
        type = key_config["type"]
        mode = key_config["mode"]
        channel = self.channel - 1  # wire-format MIDI channels are 0-indexed

        if type == "note" or type == "drum":
            velocity = config.MIDI_ACCENT_VELOCITY if self.accent else config.MIDI_VELOCITY
            if type == "drum":
                # Drums keep their own channel and note: a drum map is not transposed
                return ((0x90 if pressed else 0x80) | (config.MIDI_DRUM_CHANNEL - 1),
                        value & 0x7F, velocity if pressed else 0)
            return ((0x90 if pressed else 0x80) | channel, self._note_value(value), velocity if pressed else 0)
        elif type == "cc":
            status_byte = 0xB0 | channel
            if mode == "toggle":
                if not pressed:
                    return None  # the value changed on press; the release would only repeat it
                return (status_byte, value, 127 if key_config["state"] else 0)
            if mode == "momentary":
                fixed = key_config.get("value")  # a key that sets one fixed value, on press only
                if fixed is not None:
                    return (status_byte, value, fixed) if pressed else None
                return (status_byte, value, 127 if pressed else 0)
            raise ValueError("Unknown mode '%s' for CC type." % mode)
        elif type == "pc":
            if not pressed:
                return None  # Program Change has no "off": send once, on press only
            return (0xC0 | channel, value)
        elif type == "pitch":
            # Bend fully up or down while the key is held, back to the middle when it is let go
            bend = 0x2000 + (0x1FFF * value if pressed else 0)
            bend = max(0, min(0x3FFF, bend))
            return (0xE0 | channel, bend & 0x7F, (bend >> 7) & 0x7F)
        elif type == "panic" or type == "reset":
            if not pressed:
                return None
            return (0xB0 | channel, ALL_NOTES_OFF, 0)
        return None  # For other types, no MIDI message is generated
    
    def switch_menu(self):
        """Open the menu, or leave it and load the layout that was selected there."""
        if self.current_layout_index != 0:
            self.load_layout(0)
        else:
            self.load_layout(self.selected_layout)

    def load_layout(self, layout_index):
        """Load a specific layout by index."""
        if not 0 <= layout_index < len(self.layouts):
            raise IndexError("Layout index out of range.")
        self.current_layout_index = layout_index
        self.accent = False
        self._generate_reverse_lookup_table()

    def set_channel(self, channel):
        """Set the MIDI channel for the layout."""
        if not 1 <= channel <= 16:
            raise ValueError("MIDI channel must be between 1 and 16.")
        if channel != self.channel:
            self.channel = channel
            self._generate_reverse_lookup_table()  # table is keyed on self.channel - keep it in sync

    def set_octave(self, offset):
        """Shift every note of the layout by whole octaves."""
        offset = max(MIN_OCTAVE, min(MAX_OCTAVE, offset))
        if offset != self.octave_offset:
            self.octave_offset = offset
            self._generate_reverse_lookup_table()  # the notes we send moved, so the echo moved too

    def reset(self):
        """Back to the defaults: no toggles, no octave shift, channel 1, full brightness."""
        self._reset_states()
        self.octave_offset = 0
        self.channel = 1
        self.accent = False
        self.display_dim = False
        self._generate_reverse_lookup_table()