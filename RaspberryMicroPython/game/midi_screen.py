"""MIDI mode: the board is a Bluetooth MIDI controller while a MIDI host is connected.

The board is held in landscape here, 8 columns wide and 4 rows tall, with the mechanical keys at
the bottom right (game/landscape.py). What every pad sends is in keyboard/midi_layout.py, sketched
in keyboard/MIDI_LAYOUTS.md.

The keyboard layer sends the MIDI itself as soon as a key goes down or up and updates the layout
state (toggle, octave, channel, layout select) before it (see Keyboard._handle_midi_key_event), so
this screen only shows things: every key glows in its layout colour, a key that is pressed, toggled
on or shows the current menu setting lights in its flash colour, and a note the host plays back
lights its key as well. Holding both mechanical keys for 2 s opens the menu and leaves it again.
No game runs until the host disconnects; then the start screen comes back (BLEHandler._end_session).
"""
import pico_config as config
from game import landscape
from game.board_game import BoardGame, FULL, LOG_INFO, LOG_DEBUG
from game.haptic_player import PRIORITY_SYSTEM
from game.utils import GameConfig
from keyboard.midi_layout import MidiBoardLayout, ALL_NOTES_OFF
import globals

_FX_MIDI_MODE = 7  # Soft Bump 100 %: the board is a MIDI controller now

_NOTE_OFF = 0x80
_NOTE_ON = 0x90
_CONTROL_CHANGE = 0xB0

_DIM_LEVEL = 2  # brightness (of 16) after the menu's "dim" key


class MidiScreen(BoardGame):
    LAYOUT = landscape

    __slots__ = ["_down", "_host", "_shown_layout", "_shown_channel", "_shown_octave"]

    def __init__(self):
        super().__init__(GameConfig(game_id=config.GAME_ID_MIDI), "MIDI")
        globals.midi_layout = MidiBoardLayout()  # create the layout for the MIDI pads
        self._down = bytearray(config.GRID_NUM_KEYS)  # keys held on the board, by layout cell
        self._host = bytearray(config.GRID_NUM_KEYS)  # keys the host plays back, by layout cell
        self._shown_layout = -1
        self._shown_channel = globals.midi_layout.channel
        self._shown_octave = globals.midi_layout.octave_offset

    def enter_ready(self, now):
        self._dirty = True
        self.set_state(config.GAME_STATE_READY)
        self._haptics.play(_FX_MIDI_MODE, PRIORITY_SYSTEM, 60)
        if self.log_level >= LOG_INFO:
            self._log("===== MIDI MODE (board upright in landscape, mechanical keys bottom right) =====")
            self._log("Pads and mechanical keys send what keyboard/midi_layout.py maps them to.")
            self._log("Hold both mechanical keys 2 s = menu (layout, MIDI channel), hold again = back.")
            self._log("Games come back when the MIDI device disconnects.")

    def stop_game(self):
        super().stop_game()
        globals.midi_layout = None

    def on_pad(self, cell, pressed, event_time, now):
        """A pad went down or up: show it and buzz.

        The MIDI message and the layout's own state (toggle, octave, channel, layout select) were
        already handled in Keyboard._handle_midi_key_event - by the time this queued event arrives,
        that state reflects this press, so this only reads it (calling key_pressed() again would
        toggle every toggle-mode pad twice).
        """
        layout = globals.midi_layout
        if layout is None:
            return
        self._down[cell] = 1 if pressed else 0
        self._dirty = True
        if pressed:
            haptic_effect = layout.get_haptic_feedback(cell)
            if haptic_effect:
                self._haptics.play(haptic_effect, PRIORITY_SYSTEM, 30)
        if self.log_level >= LOG_DEBUG:
            self._log("cell %d (row %d, column %d) %s" % (
                cell, cell // landscape.WIDTH, cell % landscape.WIDTH, "pressed" if pressed else "released"))

    def on_back(self, now):
        """Both mechanical keys held: open the menu, or leave it with the layout selected there."""
        layout = globals.midi_layout
        if layout is None:
            return
        layout.switch_menu()
        self._haptics.play(_FX_MIDI_MODE, PRIORITY_SYSTEM, 60)

    def midi_in(self, message):
        """A MIDI message from the host lights the key that sends the same message."""
        layout = globals.midi_layout
        if layout is None or len(message) < 3:
            return
        key = layout.get_key_from_midi_message(message)
        if key is None or key >= config.GRID_NUM_KEYS:
            return  # nothing in this layout sends it, or it is a mechanical key without an LED
        kind = message[0] & 0xF0
        if kind == _NOTE_ON:
            lit = message[2] > 0
        elif kind == _NOTE_OFF:
            lit = False
        elif kind == _CONTROL_CHANGE:
            lit = message[2] >= 64
        else:
            return
        self._host[key] = 1 if lit else 0
        self._dirty = True
        if self.log_level >= LOG_DEBUG:
            self._log("host %s -> cell %d %s" % (bytes(message).hex(), key, "on" if lit else "off"))

    def update(self, now):
        """Watch for a new layout, channel or octave: a key that is still held would send its
        note off under the new mapping, so every switch ends all notes of the old one."""
        layout = globals.midi_layout
        if layout is None:
            return
        if (layout.current_layout_index == self._shown_layout
                and layout.channel == self._shown_channel
                and layout.octave_offset == self._shown_octave):
            return

        self._all_notes_off(self._shown_channel)
        switched_layout = layout.current_layout_index != self._shown_layout
        self._shown_layout = layout.current_layout_index
        self._shown_channel = layout.channel
        self._shown_octave = layout.octave_offset
        for cell in range(config.GRID_NUM_KEYS):
            self._down[cell] = 0
            self._host[cell] = 0
        self._dirty = True
        if self.log_level >= LOG_INFO:
            self._log("%s %s, MIDI channel %d, octave %+d" % (
                "Layout" if switched_layout else "Now on", layout.layout_name(), layout.channel, layout.octave_offset))

    def _all_notes_off(self, channel):
        """End every note of a channel, and of the drum channel that the "drum" keys play on."""
        ble_inst = globals.bluetooth
        if ble_inst is None:
            return
        drum = config.MIDI_DRUM_CHANNEL
        for number in (channel,) if channel == drum else (channel, drum):
            if 1 <= number <= 16:
                ble_inst.send_midi((0xB0 | (number - 1), ALL_NOTES_OFF, 0))

    def draw(self, now):
        layout = globals.midi_layout
        if layout is None:
            return
        level = _DIM_LEVEL if layout.display_dim else FULL
        for cell in range(config.GRID_NUM_KEYS):
            self.px(cell, layout.get_key_color(cell, bool(self._down[cell] or self._host[cell])), level)
