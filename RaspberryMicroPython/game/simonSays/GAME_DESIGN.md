# Simon Says — Game Design

A memory game for the 4×8 MIDI pad in the spirit of the Simon toy. The board is covered with
8 colour blocks. It lights them up one after another, and you repeat the sequence. Every
round adds one step at the end. A run takes one to three minutes.

This document describes *what* the game does. Code structure is decided during
implementation; the last sections only map the design onto the existing engine.

---

## 1. Hardware and grip

Hold the board **upright (portrait)**: turned by 90° against Pocket Guitar, 4 columns wide and
8 rows tall, the way you hold a phone. Layout as the game draws it:

```
        x 0    1    2    3
 y 0   [ R ][ R ][ G ][ G ]      block 0 = R red       block 1 = G green
 y 1   [ R ][ R ][ G ][ G ]
 y 2   [ B ][ B ][ Y ][ Y ]      block 2 = B blue      block 3 = Y yellow
 y 3   [ B ][ B ][ Y ][ Y ]
 y 4   [ M ][ M ][ C ][ C ]      block 4 = M magenta   block 5 = C cyan
 y 5   [ M ][ M ][ C ][ C ]
 y 6   [ O ][ O ][ W ][ W ]      block 6 = O orange    block 7 = W white
 y 7   [ O ][ O ][ W ][ W ]
```

- **Blocks:** 8 blocks of 2×2 pads, each with its own colour. Any pad of a block presses the
  block. Big blocks are easy to hit and give 8 clearly different colours.
- **Orientation:** `PORTRAIT_FLIP_ROWS` and `PORTRAIT_FLIP_COLUMNS` in `pico_config.py` mirror
  the picture onto the real board. They are shared with Piano Tiles and the start screen.
  Default: the top row is grid column 7, the left column is grid row 0.
- **Mechanical keys:** not used for playing. Holding both for 2 seconds goes back to the start
  screen.
- **Vibration motor:** on the board, in the player's hands.
- **Sound:** played by the phone app, connected over Bluetooth (BLE).

---

## 2. Core idea

1. The board plays the sequence: one block after another lights up.
2. You repeat it by pressing the blocks in the same order.
3. Right: the board plays the sequence again, with one more step at the end.
4. A wrong block or waiting too long ends the run (Simple) or costs a life (Endless).
5. The score is the longest sequence you repeated. Try to beat your best.

The colours are landmarks: "red, blue, blue, white" is much easier to remember than
positions on a plain plane. With the app, every colour also has its own tone, so the sequence
becomes a little melody.

---

## 3. Modes

| Mode | Sequence | A mistake | Run ends | Best saved |
|---|---|---|---|---|
| **Simple** | 8 steps | ends the run | after step 8 (won) or on a mistake | yes |
| **Endless** | open end | costs 1 of 3 lives, the round starts again | when all lives are gone | yes |

### Simple
Short and friendly: repeat a sequence of 8 steps and you win.

### Endless
The sequence keeps growing. You have **3 lives**. The lives are shown at the start of the run
and again after every life you lose, then the same round is played again from the start.

---

## 4. Game flow

```
 START SCREEN ──pad──> READY ──press a pad──> LIVES* ──> WATCH ──> YOUR TURN ──round done──┐
                                                ^          ^                              │
                                                │          └──── one step more ───────────┘
                                                │                          │
                                                │                          │ wrong block / too slow
                                                │                          v
                                                └── Endless, lives left ── MISTAKE
                                                                           │
                                                          Simple, or no    │
                                                          lives left       v
                                                                         RESULT ──press a pad──> new run

 * LIVES is only shown in Endless.   Hold both mechanical keys 2 s anywhere = back to the start screen.
```

### READY
- The colour map breathes slowly (dim, brighter, dim). **Press any pad to start.**
- The app can start the run as well.

### LIVES (Endless only)
- At the start of a run (1.5 s) and after each lost life (2 s).
- Lives are thick red bars: rows 6–7 = life 1, rows 3–4 = life 2, rows 0–1 = life 3.
- The life just lost blinks three times and goes out.

### WATCH
- The colour map dims. After 0.8 s the sequence plays: each step lights its block at full
  brightness, with a light tick vibration.
- Presses are ignored; a very soft bump says "not now".

### YOUR TURN
- The colour map gets brighter and a soft bump says "go".
- Press the blocks in order. A pressed block lights up at full brightness while you hold it.
- **Round done:** double click, 0.5 s pause, then WATCH with one step more.

### MISTAKE
- The board goes dark. The block you pressed flashes red (not shown when you were too slow).
- Then the **right block blinks three times**, so you see where it was. Buzz.
- Endless with lives left: LIVES, then the same round again. Otherwise: RESULT.

### RESULT
- One pad per step of your score lights up, in reading order from the top, each in the colour of
  its block (see section 8).
- **Won** (Simple, all 8 steps): a rainbow sweep.
- **New personal best:** the pads blink, plus the "new best" vibration.
- After 1.5 s, **press any pad** = play the same mode again.

### PAUSED (app only)
- Only the app pauses. The board goes very dim.
- **Resume:** press any pad, or the app. The current round starts again with WATCH.

---

## 5. The board

### Brightness

| Phase | Colour map | Highlight |
|---|---|---|
| READY | breathing, 1/16–3/8 | — |
| WATCH | 1/8 | the step being shown: full |
| YOUR TURN | 1/4 | the block being held: full |
| MISTAKE | off | pressed block red, then right block blinking |
| PAUSED | 1/16 | — |

### Colours

| Meaning | Colour | Starting RGB |
|---|---|---|
| Block 0 | red | 255, 0, 0 |
| Block 1 | green | 0, 255, 0 |
| Block 2 | blue | 0, 60, 255 |
| Block 3 | yellow | 255, 200, 0 |
| Block 4 | magenta | 255, 0, 200 |
| Block 5 | cyan | 0, 220, 255 |
| Block 6 | orange | 255, 90, 0 |
| Block 7 | white | 200, 200, 200 |
| Mistake: pressed block | red, 500 ms | 255, 0, 0 |
| Lives | red bars | 200, 0, 0 |
| Best score marker | dim white | 30, 30, 30 |

Neighbouring blocks have clearly different colours. The highlight is always the block's **own
colour at full brightness**, never red, because red means "mistake".

---

## 6. The sequence

- A new random sequence for every run.
- The same block at most **twice in a row** (three identical steps are hard to count).
- The sequence only grows at the end; earlier steps never change during a run.
- The app can send a seed (and for Simple the number of steps), so everyone can play the same
  sequence.

### Speed
Like the original Simon, the sequence is played faster as it gets longer:

| Sequence length | Block lit | Pause between steps |
|---|---|---|
| 1–5 | 520 ms | 180 ms |
| 6–9 | 420 ms | 150 ms |
| 10–13 | 340 ms | 120 ms |
| 14 and more | 280 ms | 100 ms |

Starting values, to be tuned while testing.

---

## 7. Input and judgement

- Only **presses** count, at the moment they happen. Releases don't matter.
- A block is pressed when one of its pads goes down while none of its pads is held yet. A finger
  on two pads of the same block is one press. To press the same block twice, let go in between.
- During YOUR TURN each press is compared with the next step of the sequence: the right block is
  correct, any other block is a **mistake**.
- **Too slow:** more than **5 s** since the turn started or since the last correct press is a
  mistake.
- Presses during WATCH are ignored (soft "not now" bump, at most every 0.5 s). Presses during
  LIVES and MISTAKE are ignored silently.

---

## 8. Score and results

- **Score** = the longest sequence you repeated correctly (Simple: 0–8, Endless: up to 99).
- **Won** = Simple with all 8 steps.
- **Personal best** per mode, saved on the board. A score of 0 is never a new best.
- **Result screen:** pads fill in reading order from the top, one pad per step, 80 ms each with a
  tick. Every pad shows the colour of its block. When your best is higher than this score, the pad
  of your best glows dim white. A score of 32 or more lights the whole board.

---

## 9. Vibration

Principle: **vibration carries information, not decoration.**

| Event | Effect (DRV2605L library ID) | Notes |
|---|---|---|
| Run starts | Soft Bump 100 % (7) | |
| Step shown (WATCH) | Sharp Tick 3 60 % (26) | helps to feel the rhythm; option, default on |
| Your turn | Soft Bump 60 % (8) | "go" |
| Correct press | Sharp Tick 2 80 % (25) | pads don't click, so a press needs a feel |
| Press while the board is playing | Soft Bump 30 % (9) | "not now" |
| Round done | Double Click 100 % (10) | |
| Mistake / too slow | Buzz 1 100 % (47) | cut to 300 ms |
| Result pad fills | Sharp Tick 3 60 % (26) | |
| Won | Triple Click 100 % (12) | |
| New personal best | Transition Ramp Up Long Smooth 1 (82) | |
| Pause / resume recognised | Soft Bump 100 % (7) | |

- **Priority when events overlap:** Mistake > round done > your turn > correct press > ticks.
- Effect choices are starting points and will be tuned while testing.

---

## 10. Board ↔ app (BLE)

The board **reports what happened; the app decides what it sounds like.** Byte layouts are in the
README.

### Events board → app

| Event | Content |
|---|---|
| Run start | mode, number of steps (0 = open end), lives |
| Watch | round (= sequence length), speed level, lives |
| Step shown | step number, block, how long it is lit |
| Your turn | round, time per press |
| Press | step number, block, correct or not |
| Round done | round |
| Mistake | step number, pressed block (or "too slow"), right block, lives left |
| Result | mode, score, best, new best, won |
| Game state | existing event: ready, running, paused, over (lost), win |

### Commands app → board
- **Select:** open Simon Says in a mode (game control "select" with the mode as variant).
- **Start, pause, resume, reset** (back to READY), **stop** (back to the start screen).
- **Game config over the stream channel:** seed and number of steps → Simple with that sequence.

### Suggested app behaviour
- One tone per block colour, played for "step shown" and for every correct press.
- A low "razz" for a mistake, a short fanfare for a won run.

---

## 11. Settings

| Setting | Default | Notes |
|---|---|---|
| Mode | Simple | chosen on the start screen |
| Steps in Simple | 8 | the app can send a different length |
| Lives in Endless | 3 | |
| Time per press | 5 s | |
| Step tick vibration | on | |
| Back gesture hold time | 2 s | `BACK_HOLD_MS` |
| Orientation | portrait | `PORTRAIT_FLIP_ROWS`, `PORTRAIT_FLIP_COLUMNS` |

---

## 12. How this fits the existing engine

- **Controller:** `game/simonSays/simon_says_control.py`, based on `BoardGame`
  (`game/board_game.py`): one game loop task, input queue, LED frame, non-blocking vibration and
  the "hold both mechanical keys" gesture, shared with Piano Tiles and the start screen.
- **Opening the game:** `game/game_manager.py` stops the previous game and opens this one; it is
  used by the start screen, the back gesture and BLE.
- **States:** READY = `GAME_STATE_READY`; LIVES, WATCH, YOUR TURN and MISTAKE =
  `GAME_STATE_RUNNING`; PAUSED = `GAME_STATE_PAUSED`; RESULT = `GAME_STATE_WIN` (won) or
  `GAME_STATE_OVER`.
- **Sequence data:** a generated game config (`GameGenerator.generateSimonSays`) stores one
  block number 0–7 per step in `pads`.
- **Personal bests:** `game_scores.json` on the board, shared with Piano Tiles.

---

## 13. Later

- Two players taking turns, each adding a step (Game 3 of the original)
- A kids mode with 4 big zones and an expert mode on single pads
- Repeat the sequence backwards
- A daily sequence that is the same for everyone
