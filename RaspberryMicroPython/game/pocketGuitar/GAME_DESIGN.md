# Pocket Guitar — Game Design

A rhythm game for the 4×8 MIDI pad in the spirit of Guitar Hero. Hold the board like a
guitar: the left hand frets on the pads, the right hand plucks the two strum keys with two
fingers. The song plays on its own and you play along. Songs are 60–90 seconds long, so a
session is a few minutes — a small break from scrolling.

This document describes *what* the game does. Code structure is decided during
implementation; the last section only maps the design onto the existing engine.

---

## 1. Hardware and grip

Layout as the game draws it (before the orientation flips, see below):

```
                    feedback  lane 0   1    2    3    4    5    6
 row 0  notes appear [ 0]    [ 1][ 2][ 3][ 4][ 5][ 6][ 7]
 row 1               [ 8]    [ 9][10][11][12][13][14][15]
 row 2               [16]    [17][18][19][20][21][22][23]
 row 3  HIT LINE     [24]    [25][26][27][28][29][30][31]  <- left-hand fingers come from this edge

 strum keys (opposite edge, in a corner):   (32) BLUE    (33) RED   <- right hand, two fingers
```

- **Lanes (frets):** 7 of the 8 columns. A fret counts as held when **any** key in its column
  is down. Two keys down in the same column are still one fret.
- **Feedback column:** the remaining column shows hit / almost / miss flashes and the streak,
  where the eyes can see it (see section 5).
- **Highway:** notes travel from row 0 to row 3. Row 3 is the hit line. The fretting fingers
  sit at the hit line edge, so the other rows are always visible; the hit row is often under
  the fingertips.
- **Orientation:** `POCKET_GUITAR_FLIP_ROWS` and `POCKET_GUITAR_FLIP_COLUMNS` in
  `pico_config.py` mirror the whole picture and the pads onto the real board. Both `True` =
  board turned by 180° (current prototype): the hit line is grid row 0 and the feedback column
  is grid column 7. Songs and the select/result screens need no changes for this.
- **Strum keys:** key 32 = blue, key 33 = red, both together = purple. Alternating the two
  fingers works like a bass player's index/middle plucking or a guitarist's down/up picking.
- **Vibration motor:** on the board, in the player's hands.
- **Sound:** played by the phone app, connected over Bluetooth (BLE).

---

## 2. Core idea

Like the original, **the song never waits for you**:

1. The notes scroll toward the hit line in time with the music.
2. Hold the right frets and strum with the right key(s) when a note reaches the hit line.
3. Hitting keeps the guitar audible and grows your streak. Missing makes the guitar cut out and
   plays a "clunk".
4. At the end you get a score, stars and accuracy, and you try to beat your best.

Hits are rewarded by the music itself. Mistakes are reported by vibration and sound, so the LED highway stays clean and readable.

---

## 3. Modes

| Mode | Clock | Song ends | Score saved | Version |
|---|---|---|---|---|
| **Play (Highscore)** | timed | always plays to the end | yes | v1 |
| **Practice** | waits at each note | end of song | no | v1 |
| **Survival** | timed | when the rock meter is empty | yes | later |
| **Sudden death** | timed | on the first miss | yes | later |

### Play (Highscore)
The main mode. Everything in sections 5–9 applies.

### Practice
- The clock runs normally, but **stops when the next note reaches its time** and waits until
  it is played with 0 mistakes. Timing is not judged.
- A wrong attempt gives the miss vibration; try again, no penalty.
- Sustains still have to be held; the clock runs while holding.
- No score, no stars, no records. Beat lines are on by default.

---

## 4. Game flow

```
 START SCREEN ──strum──> COUNT-IN ──4 beats──> PLAYING ──song ends──> RESULT ──strum──> COUNT-IN
      ^                                        |    ^                   |
      |                           hold both 2s |    | strum (1-bar      | press any pad
      |                                        v    |  count-in)        v
      └──────────── hold both 2s ───────────── PAUSED              START SCREEN

 Opened by the app: SELECT instead of the start screen (SELECT ──strum──> COUNT-IN, quit and
 "press any pad" come back to SELECT, hold both 2 s on SELECT = start screen).
```

### START SCREEN (on the board)
- Row 0 of the start screen (board upright) holds the difficulties of the song Warm-Up: Easy (green),
  Medium (yellow), Hard (orange), Expert (red). **Press a pad to select a difficulty**: the selected
  one is bright, the others dim. The selection is kept until the board is switched off.
- **Red strum = Play, blue strum = Practice.** The song starts at once with the count-in; turn the
  board to the guitar grip during it.
- After the result (press any pad), a quit or the end of Practice, the start screen comes back.

### SELECT (ready screen when the app opens Pocket Guitar)
Rows are counted from the hit row.

- **Row 0, columns 0–3:** difficulty — Easy (green), Medium (yellow), Hard (orange),
  Expert (red). The selected one is bright, the others dim. Only difficulties the song has are
  shown.
- **Row 1:** song slots, one column per song stored on the board (up to 8). The selected one is
  bright white.
- **Row 2:** personal best for the selected song and difficulty: one gold column per star.
- **Row 3:** slow purple pulse = "strum to start".
- Press a pad in row 0 or row 1 to select. **Red strum = Play, blue strum = Practice.** The song
  starts when the strum key is released; with both keys, the first one pressed decides.
- **Back to the start screen:** hold both strum keys for 2 seconds (no song starts).
- The app can do the same over BLE (select song, difficulty, mode, start).

### COUNT-IN
- One bar (4 beats) at the song's tempo.
- Each beat lights the next row, from the far row towards the hit row, and gives a tick
  vibration, stronger on beat 1.
- The app is told the song starts when the count-in starts, so it can line up the audio.

### PLAYING
See sections 5–9.

### PAUSED
- **Enter:** hold both strum keys for 2 seconds with **no frets held**, or app command.
  (Charts never make you hold the strum keys while no frets are down, so this can't trigger
  by accident.) Confirmed with a soft bump.
- **Resume:** strum any key. A 1-bar count-in plays, then the song continues where it paused.
- **Quit:** hold both strum keys for 2 seconds again. Back to the start screen (or SELECT when the app
  opened the game), nothing saved.

### RESULT
- Stars fill in one column at a time (columns 0–4), with a tick per star.
- **New personal best:** stars flash, plus the "new best" vibration.
- **Flawless** (see section 8): a rainbow sweep across the board.
- Score, accuracy and best streak go to the app.
- **Strum** = play the same song again. **Press any pad** = back to the start screen (or SELECT when the
  app opened the game).

---

## 5. The highway

### Time and rows
- A song has a constant tempo (BPM) in v1 and a note grid of **4 ticks per beat**
  (16th notes).
- **Row length** = how much song time one row stands for (e.g. ½ beat). It is set per chart
  and works as the scroll speed.
- A note is drawn in the row that matches its distance to "now", rounded to the nearest row.
  It therefore reaches the hit row half a row before its exact time.
- **Preview** = the 3 rows behind the hit line = 3 × row length. It should be at least about
  0.5 s, so a row should last at least ~170 ms. 250–500 ms feels best.
- Once in the hit row, a note stays there until it is judged or its timing window ends.

### What is drawn (priority, highest first)
1. Note head
2. Sustain tail
3. Hand-position glow
4. Beat line
5. Off

The feedback column is drawn separately and never overlaps the lanes.

### Sustains
- The head is followed by a tail in the same lane, reaching back to the note's end time.
- While the note is held, the head stays on the hit row and pulses gently; the tail shrinks toward
  it.

### Beat lines (option, default on)
- On every beat, the empty cells of that row glow very dim white and scroll with the notes,
  so the tempo is visible even without music.
- If a row is a whole beat long, beat lines mark the first beat of each bar instead.

### Hand-position glow (only in charts with hand positions)
- Empty cells in the lanes of the current hand position glow very dim cyan, so a shift is
  visible before it happens.

### Colours

| Meaning | Colour | Starting RGB |
|---|---|---|
| Note: strum red (key 33) | red | 255, 0, 0 |
| Note: strum blue (key 32) | blue | 0, 0, 255 |
| Note: strum both | purple | 255, 0, 255 |
| Note: any strum key | white | 180, 180, 180 |
| Sustain tail | note colour at ~25 % | — |
| Feedback: hit | whole column green, 150 ms | 0, 255, 0 |
| Feedback: almost | whole column orange, 150 ms | 255, 120, 0 |
| Feedback: miss / overstrum | whole column red, 250 ms | 255, 0, 0 |
| Streak meter x1 / x2 / x3 / x4 | dim green / cyan / yellow / white | see code |
| Beat line | very dim white | 6, 6, 6 |
| Hand-position glow | very dim cyan | 0, 8, 8 |

Strum key numbers and the three strum colours are defined globally in `pico_config.py`,
not per game.

Easy charts still use red and blue as a hint for which finger to use; on Easy the colour is
not graded.

### Feedback column
- Every judgement flashes the **whole column**: green = hit, orange = almost, red = miss or
  overstrum. A whole column stays visible even with fingers on the hit row.
- Between flashes the column is the **streak meter**. It fills from the far row towards the
  hit row as the streak grows towards the next multiplier (1 cell at the start, 3 cells just
  before), in the multiplier's colour. At x4 the whole column is lit white.
- Vibration and sound still carry the judgement as well; the lanes only show upcoming notes.

---

## 6. Notes

Every note has:

| Field | Meaning |
|---|---|
| time | tick in the song where it must be strummed |
| frets | which lanes must be held (1 lane = single note, 2–4 lanes = chord) |
| strum | red, blue, both (purple) or any (white, Easy only) |
| length | 0 = normal note, > 0 = sustain length in ticks |

A strum is always needed. Notes played without strumming (hammer-ons, pull-offs) are not in
v1.

---

## 7. Input and judgement

### Reading input
- **Fret state:** the set of lanes with at least one key down. It needs both press and
  release events from the pads.
- **Strum:** a press of key 32 and/or 33. Its time is taken **when the key event arrives**, not
  when the game loop processes it. Strum keys are debounced (~10 ms), otherwise contact bounce
  would count as extra strums.
- **Strum colour:** fixed 40 ms after the first strum key press. If the other key is pressed
  within those 40 ms, the strum is "both". The second press does not create a second strum.
- **Fret grace:** people often press frets and strum at the same moment. If the frets do not
  match at strum time, fret changes during the next 40 ms still count; the best result is used.

### Matching a strum to a note
- The strum belongs to the **earliest not-yet-judged note** whose timing window contains the
  strum time.
- No such note → **overstrum**.
- A note whose window ends without a strum → **Miss**.

### Timing windows

| | Easy | Medium | Hard | Expert |
|---|---|---|---|---|
| Perfect | ± 70 ms | ± 60 ms | ± 50 ms | ± 45 ms |
| Good (= whole window) | ± 130 ms | ± 115 ms | ± 100 ms | ± 90 ms |

Starting values, to be tuned while testing.

### Mistake count
Inside the window, each of these is one mistake:
- each **missing** fret
- each **extra** fret
- **wrong strum colour** — including only one key on a purple note, or both keys on a red or
  blue note (not counted on Easy)

| Mistakes | Result |
|---|---|
| 0 | **Hit** — Perfect or Good, depending on timing |
| 1 | **Almost** |
| 2 or more | **Miss** |

Examples: a wrong single note (1 missing + 1 extra) is a Miss. A 3-fret chord with one finger
missing is an Almost. An extra finger resting on the next fret is an Almost. Holding all 7 frets
to cheat is a Miss.

### What each result does

| Result | Points | Streak | Music | LED | Vibration |
|---|---|---|---|---|---|
| Perfect | 100 % | +1 | plays | green flash | none (accent on purple/chords) |
| Good | 80 % | +1 | plays | green flash | none (accent on purple/chords) |
| Almost | 50 % | unchanged | plays | amber flash | soft bump |
| Miss | 0 | reset | guitar muted + clunk | note off | short buzz |
| Overstrum | 0 | reset | clunk | — | short buzz |

### Sustains
- Strum the note, then keep **all its frets** held. Extra frets are fine while holding.
- Points build up while held; a soft steady hum plays while held.
- Releasing early just ends the points and the hum. No Miss, no streak loss.
- An Almost sustain earns tail points at 50 %.
- Any strum during a sustain ends the sustain and is judged normally.

---

## 8. Score and results

### Points
- **Note:** 50 points per fret in the note, × the result percentage (see table above).
- **Sustain:** 25 points per beat held (counted continuously), 50 % on an Almost.
- Everything is multiplied by the streak multiplier.

### Streak multiplier

| Consecutive hits | Multiplier |
|---|---|
| 0–9 | 1× |
| 10–19 | 2× |
| 20–29 | 3× |
| 30+ | 4× |

The note that reaches the threshold already counts at the new multiplier. A Miss or overstrum
resets the streak to 0.

### Results
- **Max score:** the score for all notes Perfect and all sustains held fully, with the multiplier
  building up normally. Calculated when the song is loaded.
- **Stars:** from score ÷ max score. Starting values, to be tuned while testing:

| Stars | Score reached |
|---|---|
| ★ | song finished |
| ★★ | ≥ 40 % |
| ★★★ | ≥ 60 % |
| ★★★★ | ≥ 80 % |
| ★★★★★ | ≥ 95 % |

- **Accuracy:** (hits + ½ × almosts) ÷ number of notes.
- **Best streak:** longest run of hits.
- **Flawless:** every note a Hit and no overstrum.

### Personal bests
Saved on the board per song and difficulty: best score, stars, accuracy, best streak and
whether it was Flawless. Practice mode saves nothing.

---

## 9. Vibration

Principle: **vibration carries information, not decoration.** The strum keys already click, so a
normal hit gets no vibration.

| Event | Effect (DRV2605L library ID) | Notes |
|---|---|---|
| Normal hit | — | the music is the reward |
| Hit on a purple note or chord of 3+ frets | Strong Click 100 % (1) | accent |
| Almost | Soft Bump 30 % (9) | "close, but not quite" |
| Miss / overstrum | Buzz 3 60 % (49) | cut to ~70 ms so it doesn't blur the next notes |
| Sustain held | steady low hum (real-time mode) | stops on release or end |
| Multiplier goes up | Double Click 100 % (10) | |
| Count-in beat | Sharp Tick 2 80 % (25), beat 1: Sharp Tick 1 100 % (24) | |
| Beat tick (option, default off) | Sharp Tick 3 60 % (26) | for testing and silent play |
| Pause / resume recognised | Soft Bump 100 % (7) | |
| Song result | Triple Click 100 % (12) | |
| New personal best | Transition Ramp Up Long Smooth (82) | |

- **Priority when events overlap:** Miss > multiplier up > accent > Almost > beat tick.
- The sustain hum pauses for any other effect and continues afterwards.
- Effect choices are starting points and will be tuned while testing.

---

## 10. Board ↔ app (BLE)

The board **reports what happened; the app decides what it sounds like.** Timing-critical
decisions are never made over Bluetooth.

### Timing
- The board is the master clock and judges everything.
- **Song time** = now − song start − **delay offset**. The offset covers Bluetooth and phone
  audio delay (headphones can add 100–300 ms). It shifts both the highway and the judgement, so
  both match what the player hears.
- The offset is a setting stored on the board. A calibration (strum along to 8 clicks) comes
  with the app later. Default: 0 ms.

### Events board → app

| Event | Content |
|---|---|
| Song start | song id, difficulty, mode, tempo, count-in length, delay offset |
| Note result | note number, Perfect/Good/Almost/Miss, multiplier, current score |
| Overstrum | current score |
| Sustain end | note number, how much was held |
| Song result | score, stars, accuracy, best streak, new best, Flawless |
| Song selection | song slot, number of songs, difficulty, available difficulties, mode, personal best |
| Game state | existing event: running, paused, resumed, finished, quit |

- At most one result event per note. The score is included in it instead of a separate score
  event, so dense passages don't overflow the event queue.
- The song selection is sent whenever the select screen opens or the selection changes.

### Commands app → board
- **Game control:** select (opens SELECT with a difficulty), start (selected song, difficulty and
  mode), pause, resume, reset (quit the song, back to SELECT), stop (back to the start screen).
- **Pocket Guitar:** select song, select difficulty, select mode (only on the select screen), set
  delay offset (not while a song plays), set options (beat lines, beat tick, sustain hum), get the
  selection.
- **Song upload:** the app sends a song file over the stream channel; it is selected as song slot 0xFF
  (select screen only). The app keeps the music and starts it on the song start event.

Byte layouts are in the README.

### Suggested app behaviour (for the Flutter app, later)
- The app plays the whole song itself: backing track plus a separate guitar/melody track.
- **Miss:** mute the guitar track and play a clunk. **Next Hit or Almost:** unmute.
- **Overstrum:** clunk only.

---

## 11. Settings

| Setting | Default | Notes |
|---|---|---|
| Difficulty | Easy | per song |
| Mode | Play | Play / Practice |
| Delay offset | 0 ms | |
| Beat lines | on | |
| Beat tick vibration | off | |
| Sustain hum | on | |
| Timing windows | per difficulty | see section 7 |
| Purple window | 40 ms | |
| Fret grace | 40 ms | |
| Strum debounce | 10 ms | |
| Pause hold time | 2 s | `BACK_HOLD_MS`, shared with the other games |
| Count-in | 1 bar | |
| LED brightness | existing setting | |

---

## 12. Writing songs (charting rules)

These rules are for **song authors and song tools**, not checked by the game engine. The engine
plays whatever a song contains. A validator in the song tools can check them.

### Per difficulty

| | Easy | Medium | Hard | Expert |
|---|---|---|---|---|
| Lanes used | 4 (lanes 3–6) | 6 (lanes 1–6) | all 7 | all 7 |
| Max frets per chord | 2 | 3 | 3 | 4 |
| Max chord span¹ | 3 | 4 | 5 | 6 |
| Strum colours | red, blue as a hint (not graded) | red, blue | red, blue, purple | red, blue, purple |
| Hand moves | never | rarely, between sections | yes | often |
| Min note spacing | 1 beat | ½ beat | ½ beat | ¼ beat |
| Row length | 1 beat | ½ beat | ½ beat | ¼ beat (≤ ~90 BPM), else ½ beat |

¹ Span = highest lane − lowest lane + 1.

### General rules
- **Spacing:** notes that are not simultaneous must be at least one row apart, otherwise they
  are drawn in the same row and look like a chord.
- **Preview:** row length ≥ ~170 ms.
- **Sustains:** at least 1 beat long. No other notes while a sustain is running (v1). At least
  ½ beat free after a sustain ends.
- **Hand positions:** a 4-lane window per section. Change only after at least 1 beat without
  notes. On Easy–Hard, chords stay inside the window.
- **Start:** first note in bar 2 or later, so the highway is empty after the count-in. The first
  4 bars are easier than the rest.
- **End:** finish on a strong chord with a sustain (purple on Hard and Expert).
- **Length:** 60–90 seconds.
- **Musical feel:** follow the real riff or melody rhythm. Notes on the beat are red (down-stroke),
  notes between beats are blue (up-stroke), and purple marks accents like power chords.

---

## 13. Song file (overview)

One JSON file per song in `game/pocketGuitar/songs/`. Files are listed in name order, which
is the order of the song slots on the select screen.

```json
{
  "id": "warm_up", "title": "Warm-Up", "artist": "Pocket Guitar",
  "bpm": 90, "beats_per_bar": 4, "ticks_per_beat": 4,
  "charts": {
    "easy":   { "notes": [[16, [4], "A", 0], [48, [4, 6], "A", 4]] },
    "hard":   { "row_ticks": 2, "timing": {"perfect_ms": 50, "good_ms": 100},
                "positions": [[16, 0], [48, 2]],
                "notes": [[16, [0], "P", 0], [18, [1], "B", 0]] }
  }
}
```

- **Note:** `[tick, lanes, strum, length]`
  - tick: position in ticks from song start (4 ticks = 1 beat, bar 0 is ticks 0–15)
  - lanes: list of lanes 0–6 (a bit mask number also works)
  - strum: `"R"` red, `"B"` blue, `"P"` both, `"A"` any
  - length: sustain length in ticks, 0 = normal note
- **Chart options** (all optional): `row_ticks` (default 1 beat / ½ / ½ / ¼ by difficulty),
  `timing` (defaults from section 7), `positions` as `[tick, first lane]` of the 4-lane window.
- Difficulties without a chart are simply not selectable.
- Song length = end of the last note + 1 bar.

---

## 14. Technical requirements

1. **Clock:** song time from the board's millisecond timer; the delay offset is applied once.
2. **Input time stamps:** taken when the key event arrives, passed along with the event.
3. **Debounce:** the strum keys need debouncing.
4. **Fret state:** the game needs both press and release events from the pads.
5. **No blocking:** vibration, LEDs and BLE never make the game wait. One game loop task
   (every ~5–10 ms) handles window ends, sustains, the pause gesture and redraws.
6. **Memory:** load and convert the song and clean up memory before the count-in. During the song,
   avoid creating objects per note — a garbage collection pause is a timing hiccup.
7. **Redraw only on change:** when a note crosses to the next row, or a flash starts or ends.

---

## 15. How this fits the existing engine

- **New game:** `game/pocketGuitar/`, a controller that inherits from `GameControl`, like Piano
  Tiles and Simon Says. New game id `GAME_ID_POCKET_GUITAR` in `pico_config.py`.
- **Opening the game:** the start screen (row 0: difficulty of Warm-Up, strum = start) and the BLE
  select command go through `game/game_manager.py`, which stops the previous game first. Pocket
  Guitar is the only game held in the guitar grip; the start screen, Simon Says and Piano Tiles are
  portrait.
- **Global config:** strum key numbers (32 blue, 33 red) and the three strum colours in
  `pico_config.py`.
- **States:** SELECT = `GAME_STATE_READY`; COUNT-IN and PLAYING = `GAME_STATE_RUNNING`;
  PAUSED = `GAME_STATE_PAUSED`; RESULT = `GAME_STATE_WIN` (song finished); quit =
  `GAME_STATE_OVER`.
- **Song data:** the song file is loaded into the game config. Each note maps onto the existing
  step idea (time = `at`, frets = `pads`), plus strum and length.
- **Vibration and sound:** use the existing haptic driver (effects and real-time mode) and BLE
  event channel. New event ids are added next to the existing ones.

---

## 16. Later

- Survival mode (rock meter, heartbeat vibration when low) and Sudden death
- Practice at 50 % / 75 % tempo, looping a section
- Tempo changes inside a song
- Notes without strumming (hammer-ons, pull-offs)
- A Star Power replacement that works without a tilt sensor
- Left-handed mode (mirrored layout; needs a grip test)
- Uploading songs from the app, a "daily riff", songs generated from MIDI files
