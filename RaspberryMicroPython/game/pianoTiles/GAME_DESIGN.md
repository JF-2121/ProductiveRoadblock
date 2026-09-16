# Piano Tiles — Game Design

A speed game for the 4×8 MIDI pad in the spirit of Piano Tiles ("Don't Tap the White Tile").
Hold the board upright: 4 lanes, tiles come from the top. Tap the tiles from the bottom up and
never tap an empty pad. With the app, every tile plays the next note of a song. A run takes 10
to 60 seconds.

This document describes *what* the game does. Code structure is decided during
implementation; the last sections only map the design onto the existing engine.

---

## 1. Hardware and grip

Hold the board **upright (portrait)** like Simon Says: turned by 90° against Pocket Guitar, 4
columns wide and 8 rows tall. Layout as the game draws it:

```
         lane 0   1     2     3
 row 0   [    ][ ## ][    ][    ]   <- tiles appear here
 row 1   [ ## ][    ][    ][    ]
 row 2   [    ][    ][    ][ ## ]
 row 3   [    ][    ][ ## ][    ]
 row 4   [    ][ ## ][    ][    ]
 row 5   [    ][    ][    ][ ## ]
 row 6   [ ## ][    ][    ][    ]
 row 7   [    ][    ][ ## ][    ]   <- the next tile (always here in Classic and Zen)
```

- **Lanes:** the 4 columns, like the original game. **Rows:** 8, so you see the next 8 tiles.
- **One tile per row.**
- **Orientation:** `PORTRAIT_FLIP_ROWS` and `PORTRAIT_FLIP_COLUMNS` in `pico_config.py` mirror
  the picture onto the real board. They are shared with Simon Says and the start screen.
  Default: tiles travel from grid column 7 towards grid column 0, as in the first Piano Tiles
  version; `PORTRAIT_FLIP_ROWS = True` reverses the direction.
- **Mechanical keys:** not used for playing. Holding both for 2 seconds goes back to the start
  screen.
- **Vibration motor:** on the board, in the player's hands.
- **Sound:** played by the phone app, connected over Bluetooth (BLE).

---

## 2. Core idea

1. Tap the **lowest tile**. In Classic and Zen the board then moves down one row, so the next tile
   is always in the bottom row. In Arcade the tiles move by themselves, and you tap the lowest
   tile wherever it is.
2. Tapping an empty pad ends the run. In Arcade, a tile that leaves the board untapped ends it
   too.
3. Every tile is the next note of a song. Tapping fast and steadily makes the song sound right.
4. At the end you get stars, and you try to beat your best.

---

## 3. Modes

| Mode | Clock | Board moves | Run ends | Score |
|---|---|---|---|---|
| **Classic** | stopwatch, from the first tap | one row per tap | after 50 tiles or on a mistake | time for 50 tiles (lower is better) |
| **Zen** | 30 s countdown, from the first tap | one row per tap | time is up, or on a mistake | tiles |
| **Arcade** | — | by itself, faster every 10 tiles | on a mistake or a missed tile | tiles |

---

## 4. Game flow

```
 START SCREEN ──pad──> READY ──tap the start tile──> PLAYING ──finished / time up──> RESULT
                                                        │                             ^   │
                                                        │ mistake / missed tile       │   │ press a pad
                                                        v                             │   v
                                                     GAME OVER ───────────────────────┘  READY

 Hold both mechanical keys 2 s anywhere = back to the start screen.
```

### READY
- The first 8 tiles are shown. The bottom one is the **start tile** and pulses.
- **Tap the start tile to start.** The clock starts with this tap. Other pads are ignored.
- The app "start" command deals new tiles.

### PLAYING
See sections 5–7. Classic shows a green **finish line** above tile 50.

### GAME OVER
- The board freezes. The wrong pad (or the missed tile) blinks red four times. Buzz.
- After 1.2 s: RESULT.

### RESULT
- Stars fill one row at a time from the bottom (rows 7 to 3), with a tick per star.
- No star: the bottom row glows dim red.
- **New personal best:** the stars blink, plus the "new best" vibration.
- After 1.5 s, **press any pad** = READY with new tiles.

### PAUSED (app only)
- Only the app pauses. The board goes dim and the clock stops.
- **Resume:** press any pad, or the app. 3 ticks count in (1.2 s), then the clock and the tiles
  continue.

---

## 5. The board

| Meaning | Colour | Starting RGB |
|---|---|---|
| Tile | blue | 0, 150, 255 |
| Start tile (READY) | pulsing light blue | 0, 150, 255 ↔ 160, 220, 255 |
| Tapped tile (Arcade, scrolls away) | dim grey | 20, 20, 20 |
| Finish line (Classic) | green row | 0, 160, 0 |
| Mistake | red, blinking | 255, 0, 0 |
| Star (result) | gold row | 255, 140, 0 |
| No star (result) | dim red row | 40, 0, 0 |

Empty pads are off, so a tile is always clearly visible. In Classic and Zen a tapped tile leaves
the board at once.

---

## 6. Tiles

- One tile per row in a random lane. The same lane at most **twice in a row**.
- New tiles for every run. The app can send a seed (and for Classic the number of tiles), so
  everyone can play the same tiles.

### Arcade speed

| Tiles tapped | Time per row | Tiles per second |
|---|---|---|
| 0–9 | 400 ms | 2.5 |
| every 10 more | 10 % less | |
| minimum | 130 ms | 7.7 |

The first tap only starts the clock; the tiles start moving one row later. A new tile appears at
the top for every row the board moves, so the next 8 tiles are always visible.

Starting values, to be tuned while testing.

---

## 7. Input and judgement

- Only **presses** count, at the moment they happen. Releases don't matter.
- The **lowest tile not tapped yet** is the only right pad:

| Press on | Result |
|---|---|
| the lowest tile not tapped yet | **hit**: next tile |
| a tile already tapped (Arcade) | ignored |
| the finish line (Classic) | ignored |
| an empty pad | **mistake**, game over |
| a tile above the lowest one | **mistake** (tiles are tapped in order), game over |

- **Missed tile (Arcade):** when the lowest tile scrolls off the bottom untapped, a tap on its lane
  in the bottom row still counts for **80 ms**. After that the run is over.
- **READY:** only the start tile counts, other pads are ignored.

---

## 8. Score and results

### Stars
Starting values, to be tuned while testing:

| Stars | Classic (time for 50 tiles) | Zen (tiles in 30 s) | Arcade (tiles) |
|---|---|---|---|
| ★ | finished | 20 | 10 |
| ★★ | ≤ 30 s | 60 | 30 |
| ★★★ | ≤ 22 s | 90 | 60 |
| ★★★★ | ≤ 16 s | 120 | 100 |
| ★★★★★ | ≤ 12 s | 150 | 150 |

- **Classic** with a mistake: not finished, 0 stars, no time.
- **Zen** with a mistake: the tiles so far count.

### Personal bests
Saved on the board per mode: Classic the best time (finished runs only), Zen and Arcade the most
tiles.

---

## 9. Vibration

Principle: **vibration carries information, not decoration.**

| Event | Effect (DRV2605L library ID) | Notes |
|---|---|---|
| Start tile tapped | Sharp Tick 1 100 % (24) | the clock starts |
| Tile tapped | Sharp Tick 3 60 % (26) | pads don't click; option, default on |
| Arcade gets faster | Double Click 100 % (10) | |
| Zen, last 5 seconds | Sharp Tick 2 80 % (25), once per second | |
| Mistake / missed tile | Buzz 1 100 % (47) | cut to 300 ms |
| Finished (Classic) / time up (Zen) | Triple Click 100 % (12) | |
| Star on the result screen | Sharp Tick 2 80 % (25) | |
| New personal best | Transition Ramp Up Long Smooth 1 (82) | |
| Pause recognised | Soft Bump 100 % (7) | |
| Resume count-in | Sharp Tick 2 80 % (25), 3 ticks | |

- **Priority when events overlap:** Mistake > faster > time tick > tile tick.
- Effect choices are starting points and will be tuned while testing.

---

## 10. Board ↔ app (BLE)

The board **reports what happened; the app decides what it sounds like.** Byte layouts are in the
README.

### Events board → app

| Event | Content |
|---|---|
| Run start | mode, goal (Classic tiles / Zen seconds), Arcade start speed |
| Tile | tile number, lane, time since the start |
| Faster (Arcade) | speed level, time per row |
| Time left (Zen) | seconds left, once per second |
| Mistake | reason (empty pad / missed tile), tile number, position |
| Result | mode, score (Classic: time, else tiles), tiles, stars, new best, finished |
| Game state | existing event: ready, running, paused, over, win |

### Commands app → board
- **Select:** open Piano Tiles in a mode (game control "select" with the mode as variant).
- **Start** (new tiles), **pause, resume, reset** (back to READY), **stop** (back to the start
  screen).
- **Game config over the stream channel:** seed and number of tiles → Classic with those tiles.

### Suggested app behaviour
- The app holds a melody. Every tile event plays its next note; the tile number is the note
  number, so a dropped event can't shift the song.
- A mistake plays a wrong chord; a finished Classic run a short final chord.

---

## 11. Settings

| Setting | Default | Notes |
|---|---|---|
| Mode | Classic | chosen on the start screen |
| Classic tiles | 50 | the app can send a different number |
| Zen time | 30 s | |
| Arcade speed | 400 ms per row, 10 % faster every 10 tiles, minimum 130 ms | |
| Missed tile grace | 80 ms | |
| Tile tick vibration | on | |
| Back gesture hold time | 2 s | `BACK_HOLD_MS` |
| Orientation | portrait | `PORTRAIT_FLIP_ROWS`, `PORTRAIT_FLIP_COLUMNS` |

---

## 12. How this fits the existing engine

- **Controller:** `game/pianoTiles/pianoTiles_control.py`, based on `BoardGame`
  (`game/board_game.py`), shared with Simon Says and the start screen.
- **Opening the game:** `game/game_manager.py`.
- **States:** READY = `GAME_STATE_READY`; PLAYING and GAME OVER = `GAME_STATE_RUNNING`; PAUSED =
  `GAME_STATE_PAUSED`; RESULT = `GAME_STATE_WIN` (Classic finished, Zen time up) or
  `GAME_STATE_OVER`.
- **Tile data:** a generated game config (`GameGenerator.generatePianoTiles`) stores one lane 0–3
  per tile in `pads`.
- **Personal bests:** `game_scores.json` on the board, shared with Simon Says.

---

## 13. Later

- Long tiles (hold) and double tiles (two at once), like the sustains and chords of Pocket Guitar
- Songs: tiles in the rhythm of a real melody, from a song file
- Rush (Arcade that speeds up continuously) and Relay (50 tiles per 10 s round)
