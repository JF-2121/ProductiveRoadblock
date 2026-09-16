# MIDI layouts

What every pad and mechanical key of the board sends in MIDI mode, how the board looks while it
does it, and how to change it. The layouts are in [`keyboard/midi_layout.py`](midi_layout.py), the
screen that draws them in [`game/midi_screen.py`](../game/midi_screen.py).

---

## 1. Holding the board

MIDI mode is played in **landscape**: 8 columns wide, 4 rows tall, with the **mechanical keys at the
bottom right**. The bottom row of every layout is its base row (the white keys, the drum pads), so
it sits right above the mechanical keys.

```
        col 0    1      2      3      4      5      6      7
 row 0  [  0 ] [  1 ] [  2 ] [  3 ] [  4 ] [  5 ] [  6 ] [  7 ]
 row 1  [  8 ] [  9 ] [ 10 ] [ 11 ] [ 12 ] [ 13 ] [ 14 ] [ 15 ]
 row 2  [ 16 ] [ 17 ] [ 18 ] [ 19 ] [ 20 ] [ 21 ] [ 22 ] [ 23 ]
 row 3  [ 24 ] [ 25 ] [ 26 ] [ 27 ] [ 28 ] [ 29 ] [ 30 ] [ 31 ]
                                                    (32)   (33)   <- mechanical keys
```

The numbers are the key numbers of the layout arrays: `index = row * 8 + column`, 32 is the left
mechanical key and 33 the right one.

Turned the other way round? `MIDI_FLIP_ROWS` (top and bottom) and `MIDI_FLIP_COLUMNS` (left and
right) in `pico_config.py` mirror the picture onto the board; the key numbers stay as they are here.

---

## 2. Getting in and out

- **MIDI mode starts** when a MIDI app connects over Bluetooth (see the README). The open game
  stops, the board shows the layout, and one soft bump confirms it.
- **MIDI mode ends** when that app disconnects: the start screen comes back.
- **Menu:** hold **both mechanical keys for 2 seconds**. Holding them again leaves the menu with the
  layout that is selected there; the `EXIT` pad does the same.
- Whenever the layout, the MIDI channel or the octave changes, the board sends **All Notes Off**
  (CC 123) on the channel it used before and on the drum channel, so nothing keeps ringing on the
  host.

---

## 3. Colour code

Every key has a colour while it is idle and a brighter "flash" colour while it is **pressed**,
**toggled on**, or **shows the current setting** in the menu.

| Colour | RGB | Means |
|---|---|---|
| dark blue | 0, 0, 30 | preset (Program Change) |
| orange | 30, 15, 0 | octave down / up |
| green | 0, 30, 0 | control change: modulation, sustain, filter, clip launch |
| red | 30, 0, 0 | panic (all notes off), track mute |
| purple | 40, 0, 40 | black key (note) |
| warm white | 30, 30, 25 | white key (note) |
| grey | 5, 5, 5 / 10, 10, 10 | pitch bend, sequencer step |
| cyan | 0, 30, 30 | drum: kick and snare |
| yellow | 30, 30, 0 | drum: hi-hats and toms, track solo |
| pink | 30, 0, 15 | melodic drum-layout pads |
| teal | 0, 100, 100 | menu: layout choice |
| olive | 15, 15, 0 | menu: MIDI channel |
| dark red | 50, 0, 0 | menu: reset, dim |
| bright red | 100, 0, 0 | menu: exit |
| off | 0, 0, 0 | key does nothing |

Flash colours: **white** for notes, presets, menu choices and sequencer steps, **green** for control
changes, **cyan** for pitch bend, **red** for panic and mutes, **yellow** for solos, **blue** for
track select.

A note the host plays back lights the key that sends the same note, in the same flash colour. The
menu's `DIM` key turns the whole board down to 1/8 brightness (press it again to go back).

---

## 4. Layout 1: Synth keyboard

One octave of a piano keyboard on the two lower rows, presets on top.

```
        col 0    1      2      3      4      5      6      7
 row 0  PC 0   PC 1   PC 2   PC 3   PC 4   PC 5   PC 6   PC 7     presets      (blue)
 row 1  Oct-   Oct+   Mod    Sust   Flt-   Flt+   Panic   --      utility      (orange/green/red)
 row 2  C#     D#     Mod!   F#     G#     A#     Bend-  Bend+    black keys   (purple/grey)
 row 3  C      D      E      F      G      A      B      C'       white keys   (warm white)
                                                    (32) Kick (33) Snare       (drums, channel 10)
```

| Keys | What they send | Mode |
|---|---|---|
| 0–7 | Program Change 0–7 | on press |
| 8, 9 | octave down / up, −4 to +4 octaves (moves every note of the layout) | on press |
| 10 | CC 1 (modulation) 127 / 0 | toggle |
| 11 | CC 64 (sustain) 127 while held | momentary |
| 12, 13 | CC 74 (filter) value 0 / value 127 | on press |
| 14 | CC 123 (all notes off) | on press |
| 15 | nothing | |
| 16, 17, 19, 20, 21 | notes 61, 63, 66, 68, 70 (C#, D#, F#, G#, A#) | momentary |
| 18 | CC 1 (modulation) 127 while held | momentary |
| 22, 23 | pitch bend down / up while held, back to the middle on release | momentary |
| 24–31 | notes 60, 62, 64, 65, 67, 69, 71, 72 (C, D, E, F, G, A, B, C) | momentary |
| 32, 33 | kick (note 36) and snare (note 38), always on the drum channel 10 and never transposed | momentary |

Key 18 sits where the black key between E and F would be, so the black keys stay in the right
places.

---

## 5. Layout 2: Drums and sequencer

Sixteen drum and melody pads on top, a 16-step sequencer below.

```
        col 0    1      2      3      4      5      6      7
 row 0  Kick   Snare  HH cl  HH op  C4     C#4    D4     D#4      drums A / melody  (cyan/yellow/pink)
 row 1  Kick2  Tom L  Tom M  Tom H  E4     F4     F#4    G4       drums B / melody
 row 2  Step1  Step2  Step3  Step4  Step5  Step6  Step7  Step8    sequencer 1-8     (grey)
 row 3  Step9  St.10  St.11  St.12  St.13  St.14  St.15  St.16    sequencer 9-16
                                                    (32) Accent (33) Roll
```

| Keys | What they send | Mode |
|---|---|---|
| 0–3 | notes 36, 38, 42, 46 (kick, snare, closed and open hi-hat) | momentary |
| 4–7 | notes 60–63 | momentary |
| 8–11 | notes 35, 40, 50, 41 (second kick, toms) | momentary |
| 12–15 | notes 64–67 | momentary |
| 16–23 | CC 60–67, 127 / 0 (sequencer steps 1–8) | toggle |
| 24–31 | CC 68–75, 127 / 0 (sequencer steps 9–16) | toggle |
| 32 | accent: notes played while it is held use velocity 127 instead of 100 | held |
| 33 | roll: reserved, sends nothing yet | |

The note numbers follow the General MIDI drum map, but they are sent on the layout's current
channel, so pick channel 10 in the menu for a GM drum kit.

---

## 6. Layout 3: DAW control

Eight tracks, one column each: mute, solo, select, launch.

```
        col 0    1      2      3      4      5      6      7
 row 0  Mute1  Mute2  Mute3  Mute4  Mute5  Mute6  Mute7  Mute8    CC 16-23  (red)
 row 1  Solo1  Solo2  Solo3  Solo4  Solo5  Solo6  Solo7  Solo8    CC 24-31  (yellow)
 row 2  Sel 1  Sel 2  Sel 3  Sel 4  Sel 5  Sel 6  Sel 7  Sel 8    CC 32-39  (blue)
 row 3  Clip1  Clip2  Clip3  Clip4  Clip5  Clip6  Clip7  Clip8    CC 40-47  (green)
                                                    (32) CC 115 (33) CC 114
```

| Keys | What they send | Mode |
|---|---|---|
| 0–7 | CC 16–23 (mute), 127 / 0 | toggle |
| 8–15 | CC 24–31 (solo), 127 / 0 | toggle |
| 16–23 | CC 32–39 (select), 127 / 0 | toggle |
| 24–31 | CC 40–47 (clip launch), 127 while held | momentary |
| 32, 33 | CC 115, CC 114, 127 / 0 | toggle |

---

## 7. Menu

Reached by holding both mechanical keys for 2 seconds. It sends no MIDI except the All Notes Off of
`RESET`.

```
        col 0    1      2      3      4      5      6      7
 row 0  Synth  Drums  DAW     --     --     --     --     --      layout      (teal, white = selected)
 row 1  Ch 1   Ch 2   Ch 3   Ch 4   Ch 5   Ch 6   Ch 7   Ch 8     channel     (olive, white = current)
 row 2  Ch 9   Ch10   Ch11   Ch12   Ch13   Ch14   Ch15   Ch16
 row 3   --     --     --     --     --    RESET  DIM    EXIT     system      (dark red / bright red)
                                                    (32) --   (33) --
```

| Keys | What they do |
|---|---|
| 0–2 | choose the layout that `EXIT` and the hold gesture load |
| 8–23 | MIDI channel 1–16 for everything the board sends |
| 29 | reset: all toggles off, octave 0, channel 1, full brightness, and All Notes Off |
| 30 | dim the board to 1/8 brightness, press again for full brightness |
| 31 | leave the menu and load the selected layout |
| 32, 33 | nothing: hold both for 2 s to leave the menu |

---

## 8. MIDI channel

Everything the board sends goes out on the **one channel selected in the menu** (channel 1 after a
reset). The `ch` field in the layout data is a backup for later and is not used.

The only exception are keys of type **`drum`**: they always play on `MIDI_DRUM_CHANNEL`
(10, General MIDI percussion) and are never moved by the octave keys, so the kick and snare on the
mechanical keys of layout 1 sound like drums whatever channel is selected. The drum pads of layout 2
are plain notes on the selected channel, so pick channel 10 there for a GM kit — or give them the
type `drum` if you want them fixed to it as well.

Notes the host sends back light the key that sends the same message, on the current channel (drum
keys on the drum channel) and at the current octave.

---

## 9. Changing a layout

A layout is a tuple of 34 entries: 32 pads in the order of the picture above, then the two
mechanical keys. Every entry is a dict:

| Field | Meaning |
|---|---|
| `type` | `note`, `drum`, `cc`, `pc`, `pitch`, `panic`, `accent`, `roll` (reserved), `none`; in the menu `load`, `set_ch`, `oct_up`, `oct_dn`, `reset`, `sleep`, `exit` |
| `val` | note number, CC number, program number, or the value of a menu key |
| `ch` | the channel this key was meant for — a backup, not used, see section 8 |
| `color` | colour while the key is idle |
| `flash` | colour while it is pressed, toggled on, or current in the menu |
| `mode` | `momentary` (acts on press and release) or `toggle` (flips on every press) |
| `state` | toggle state while the board runs, always starts off |
| `haptic` | DRV2605L effect played when a **pad** is pressed, 0 for none (the mechanical keys click by themselves) |
| `value` | optional: a momentary CC key that sends this one fixed value on press |

To add a layout: write the tuple, add it to `self.layouts` in `MidiBoardLayout.__init__`, add its
name to `LAYOUT_NAMES`, and give the menu a `load` key with its index.
