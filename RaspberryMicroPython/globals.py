# Global Variables and System Services

# Declared here (rather than only assigned in main.py) so other modules can
# import globals and reference these names before main.py has run.
keyboard = None
haptic = None
bluetooth = None

game = None
midiboard_mode = None

midi_layout = None  # MIDI layout for the host, set by main.py after reading the config from the host