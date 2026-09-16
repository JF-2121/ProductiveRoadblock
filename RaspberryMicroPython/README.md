# RaspberryMicroPython

## Games

The board boots into the **start screen**. Hold the board upright (portrait, 4 columns wide and 8
rows tall):

| Row | Column 0 | Column 1 | Column 2 | Column 3 |
| --- | --- | --- | --- | --- |
| 0 | Pocket Guitar: Warm-Up, easy | Warm-Up, medium | Warm-Up, hard | Warm-Up, expert |
| 1 | — | | | |
| 2 | Piano Tiles: Classic | Piano Tiles: Zen | Piano Tiles: Arcade | |
| 3 | — | | | |
| 4 | Simon Says: Simple | Simon Says: Endless | | |

- **Pocket Guitar:** press a pad in row 0 to select the difficulty (bright), then a mechanical key
  starts the song: red = Play, blue = Practice. Afterwards the start screen comes back.
- **Piano Tiles, Simon Says:** press a pad and let go.
- **Back:** in every game, holding both mechanical keys for 2 s goes back (Pocket Guitar: pause, then
  quit).
- **Orientation:** Pocket Guitar is played in the guitar grip (`POCKET_GUITAR_FLIP_ROWS`,
  `POCKET_GUITAR_FLIP_COLUMNS`). The start screen, Simon Says and Piano Tiles are portrait
  (`PORTRAIT_FLIP_ROWS` swaps top and bottom, `PORTRAIT_FLIP_COLUMNS` swaps left and right), all in
  `pico_config.py`.
- **Designs:** [Pocket Guitar](game/pocketGuitar/GAME_DESIGN.md), [Simon Says](game/simonSays/GAME_DESIGN.md),
  [Piano Tiles](game/pianoTiles/GAME_DESIGN.md).
- **Testing without the app:** run `Test/start_screen_test.py` on the Pico.

## BLE Protocol
The Pico exposes a BLE GATT service with a command channel for short controls, an event channel for notifications, and a stream channel for chunked game configuration transfers. The implementation uses named constants for command IDs, event IDs, stream opcodes, and stream fields to keep the protocol readable and stable. All multi-byte integers in commands and events are little-endian unless noted.

### Board Modes

The board runs either the games or Bluetooth MIDI, never both. It registers the game service and the standard Bluetooth MIDI service (`03B80E5A-EDE8-4B33-A751-6CE34EC4C700`) and advertises its name with the MIDI service UUID, so MIDI apps find it (a second 128-bit UUID does not fit into the advertising data); the game app connects by name and discovers services after connecting, so it finds the game service regardless of what the advertisement itself lists.

Only one client is connected at a time. What it does first chooses the mode for the whole connection, stored in `globals.midiboard_mode`:

| The client first… | Mode | The board |
| --- | --- | --- |
| subscribes to the MIDI I/O notifications, or writes a MIDI packet | `BOARD_MODE_MIDI` | the open game stops and the MIDI screen shows the pads |
| subscribes to the game events or the stream indications, or writes a command or stream message | `BOARD_MODE_GAME` | the games run as before |

- Traffic of the other kind is ignored until the client disconnects. After a MIDI session the start screen opens again.
- A MIDI host usually never writes, so the subscriptions are checked every `BLE_SESSION_POLL_MS` until the mode is chosen. MicroPython with BTstack (Pico W) stores each subscription (CCCD) at the characteristic's value handle + 1 without sending an IRQ; the board reads it there and clears it on disconnect.
- A client that connects but neither subscribes nor writes chooses nothing; the games keep running.
- **MIDI mode:** the board is held in **landscape** here (8 columns wide, 4 rows tall, mechanical keys at the bottom right) and every key plays what the selected layout of `keyboard/midi_layout.py` maps it to: notes, CC (momentary or toggle), Program Change, pitch bend, octave shift or panic, sent on the one MIDI channel selected in its menu (drum keys always on the GM drum channel). Keys glow in their layout colour and light up in their flash colour while pressed, toggled on, or played back by the host. Holding both mechanical keys for 2 s opens the menu (layout, MIDI channel, reset, dim) and leaves it again; every switch sends All Notes Off. The sketches of all layouts, the key mappings and the colour code are in [keyboard/MIDI_LAYOUTS.md](keyboard/MIDI_LAYOUTS.md). The MIDI characteristic reads empty and takes packets up to MTU − 3 bytes with several messages and running status; SysEx is skipped. The games come back once the host disconnects.

### Command Channel
Command payloads are sent on the command characteristic as:

- byte 0: command category ID (`BLE_CMD_GAME_CONTROL`, `BLE_CMD_POCKET_GUITAR`)
- byte 1: sub-command ID
- byte 2+: optional payload bytes

#### Game control (category 0x01): acts on the open game

| Sub-command constant | Value | Payload | Description |
| --- | --- | --- | --- |
| `BLE_GAME_CONTROL_START` | 0x00 | none | Start: Pocket Guitar plays the selected song, Simon Says starts a run, Piano Tiles deals new tiles (the run starts with the tap on the start tile) |
| `BLE_GAME_CONTROL_STOP` | 0x01 | none | Quit the game and open the start screen |
| `BLE_GAME_CONTROL_RESET` | 0x02 | none | Quit the current run (nothing saved), back to the game's ready screen |
| `BLE_GAME_CONTROL_RESUME` | 0x03 | none | Resume a paused game |
| `BLE_GAME_CONTROL_SELECT` | 0x04 | `[game_id]` or `[game_id, variant]` | Open a game on its ready screen, see the table below |
| `BLE_GAME_CONTROL_LOAD` | 0x05 | none | Reload the open game (back to its ready screen) |
| `BLE_GAME_CONTROL_TRIGGER_HAPTIC` | 0x06 | `[effect_id]` | Play DRV2605L library effect 1–123 |
| `BLE_GAME_CONTROL_RUN_AUTOCAL` | 0x07 | none | Run the haptic auto-calibration; answered with a calibration report |
| `BLE_GAME_CONTROL_SET_BRIGHTNESS` | 0x08 | `[level]` | LED brightness 0–255 |
| `BLE_GAME_CONTROL_GET_TELEMETRY` | 0x09 | none | Answered with a battery report |
| `BLE_GAME_CONTROL_PAUSE` | 0x0A | none | Pause the running game (Simon Says and Piano Tiles also resume with any pad) |

| Game | `game_id` | `variant` |
| --- | --- | --- |
| Start screen | 0x00 | — |
| Piano Tiles | 0x01 | 0 Classic, 1 Zen, 2 Arcade |
| Simon Says | 0x02 | 0 Simple, 1 Endless |
| Pocket Guitar | 0x03 | difficulty 0 easy, 1 medium, 2 hard, 3 expert (preselected on its select screen) |

#### Pocket Guitar (category 0x02): only while Pocket Guitar is open

| Sub-command constant | Value | Payload | Description |
| --- | --- | --- | --- |
| `BLE_POCKET_GUITAR_SELECT_SONG` | 0x00 | `[slot]` | Select a song (select screen only) |
| `BLE_POCKET_GUITAR_SELECT_DIFFICULTY` | 0x01 | `[difficulty]` | 0–3, if the song has that chart (select screen only) |
| `BLE_POCKET_GUITAR_SELECT_MODE` | 0x02 | `[mode]` | 0 Play, 1 Practice: used by START (select screen only) |
| `BLE_POCKET_GUITAR_SET_DELAY_OFFSET` | 0x03 | `[offset i16]` | Bluetooth/audio delay in ms (not while a song plays) |
| `BLE_POCKET_GUITAR_SET_OPTIONS` | 0x04 | `[bits]` | bit 0 beat lines, bit 1 beat tick vibration, bit 2 sustain hum |
| `BLE_POCKET_GUITAR_GET_SELECTION` | 0x05 | none | Answered with a song selection event |

A command that is not possible right now (for example selecting a song during a song) is answered with an "invalid payload" error.

Example payloads:

- Open Simon Says in Endless mode: `[0x01, 0x04, 0x02, 0x01]`
- Start: `[0x01, 0x00]`
- Back to the start screen: `[0x01, 0x01]`
- Pocket Guitar song slot 1: `[0x02, 0x00, 0x01]`
- Pocket Guitar delay offset −50 ms: `[0x02, 0x03, 0xCE, 0xFF]`

### Event Channel
Notifications are sent as:

- byte 0: event ID
- byte 1+: event payload / sub-type data

| Event ID | Event type | Payload format | Description |
| --- | --- | --- | --- |
| 0x01 | Key event | `[key_event_type, key_id]` | Keyboard press or release callback |
| 0x02 | Game event | `[subtype, value...]` | Game state, score, game opened |
| 0x03 | Sound event | `[sound_id, duration_low, duration_high]` | Play a sound effect |
| 0x04 | Battery report | see below | Answer to GET_TELEMETRY |
| 0x05 | Calibration report | see below | Answer to RUN_AUTOCAL |
| 0x06–0x0B | Pocket Guitar | see below | Song start, note result, overstrum, sustain end, song result, song selection |
| 0x0C | Simon Says | `[subtype, ...]` | see below |
| 0x0D | Piano Tiles | `[subtype, ...]` | see below |
| 0xFF | Error | `[error_code, offending_command_or_value]` | BLE protocol or game error |

Events are only queued while a client is connected. When the queue is full (32 events), new events are dropped.

### Error Codes
| Error code | Value | Meaning |
| --- | --- | --- |
| Generic error | 0x00 | Unspecified failure |
| Wrong command | 0x01 | Invalid or unsupported command ID/sub-command |
| Invalid game ID | 0x02 | Selected game ID is not supported |
| Game not loaded | 0x03 | Requested game action executed before a config was loaded, or the command needs another game |
| Invalid stream | 0x04 | Stream payload could not be decoded or was malformed |
| Invalid payload | 0x05 | Required payload data was missing or malformed, or the action is not possible right now |
| Stream not initialized | 0x06 | Chunk/commit arrived before a stream init |

### Game Event Payloads (0x02)
| Event subtype | Value | Payload |
| --- | --- | --- |
| Game state update | 0x00 | `[state]`: 0 init, 1 ready, 2 running, 3 paused, 4 over (lost / quit), 5 win (finished) |
| Game score update | 0x01 | score u16 |
| Game selected | 0x02 | `[game_id, variant]` (variant 0xFF = none); sent whenever a game or the start screen opens |

### Battery Report (0x04) and Calibration Report (0x05)
| Event | Payload |
| --- | --- |
| Battery report | supply voltage mV u16 (measured by the haptic driver, updated while the motor runs), free memory KB u16, game_id u8, state u8, brightness u8 |
| Calibration report | ok u8, compensation u8, back-EMF u8, BEMF gain u8 |

### Pocket Guitar Events
| Event ID | Event | Payload |
| --- | --- | --- |
| 0x06 | Song start | song slot u8, difficulty u8, mode u8, bpm×10 u16, start position ms i32, delay offset ms i16 |
| 0x07 | Note result | note index u16, grade u8 (1 perfect, 2 good, 3 almost, 4 miss), multiplier u8, score u32 |
| 0x08 | Overstrum | score u32 |
| 0x09 | Sustain end | note index u16, held percent u8 |
| 0x0A | Song result | score u32, stars u8, accuracy percent u8, best streak u16, flags u8 (bit 0 new best, bit 1 flawless) |
| 0x0B | Song selection | song slot u8, song count u8, difficulty u8, available difficulties u8 (bit per difficulty), mode u8, best stars u8, best score u32 |

### Simon Says Events (0x0C)
| Subtype | Value | Payload |
| --- | --- | --- |
| Run start | 0x00 | mode u8, steps u8 (0 = open end), lives u8 |
| Watch | 0x01 | round u8 (= sequence length), speed level u8, lives u8 |
| Step shown | 0x02 | step u8, block u8 (0–7), lit ms u16 |
| Your turn | 0x03 | round u8, time per press ms u16 |
| Press | 0x04 | step u8, block u8, correct u8 |
| Round done | 0x05 | round u8 |
| Mistake | 0x06 | step u8, pressed block u8 (0xFF = too slow), right block u8, lives left u8 |
| Result | 0x07 | mode u8, score u8, best u8, flags u8 (bit 0 new best, bit 1 won) |

Blocks: 0 red, 1 green, 2 blue, 3 yellow, 4 magenta, 5 cyan, 6 orange, 7 white. The app plays one tone per block.

### Piano Tiles Events (0x0D)
| Subtype | Value | Payload |
| --- | --- | --- |
| Run start | 0x00 | mode u8, goal u16 (Classic: tiles, Zen: seconds, Arcade: 0), row time ms u16 (Arcade, else 0) |
| Tile | 0x01 | tile u16, lane u8, time ms u32 since the start |
| Faster | 0x02 | level u8, row time ms u16 (Arcade) |
| Time left | 0x03 | seconds u8 (Zen, once per second) |
| Mistake | 0x04 | reason u8 (1 wrong pad, 2 missed tile), tile u16, x u8, y u8 |
| Result | 0x05 | mode u8, score u32 (Classic: time ms, else tiles), tiles u16, stars u8, flags u8 (bit 0 new best, bit 1 finished) |

The tile number is the note number: the app plays note `tile` of its melody for every tile event.

### Key Event Payloads
| Key event type | Value | Meaning |
| --- | --- | --- |
| Key press | 0x00 | Physical key was pressed |
| Key release | 0x01 | Physical key was released |

### Stream Channel for Large Game Data
The stream channel supports chunked payloads for larger game descriptors, such as a generated config with a seed and hit/miss actions. The message format uses a lightweight protobuf-like structure with constant field IDs and chunk opcodes.

#### Stream opcodes
| Opcode | Constant | Meaning |
| --- | --- | --- |
| 0x10 | `BLE_STREAM_MSG_INIT` | Starts a new stream transfer |
| 0x11 | `BLE_STREAM_MSG_CHUNK` | Carries the next chunk of body data |
| 0x12 | `BLE_STREAM_MSG_COMMIT` | Finalizes the transfer and dispatches the assembled payload |
| 0x13 | `BLE_STREAM_MSG_ABORT` | Cancels the active transfer |
| 0x20 | `BLE_STREAM_MSG_GAME_CONFIG` | Full protobuf-like game configuration payload: opens the game and starts it |
| 0x21 | `BLE_STREAM_MSG_GAME_SELECT` | `[game_id]` or `[game_id, variant]`: open a game |
| 0x22 | `BLE_STREAM_MSG_GAME_LOAD` | Like GAME_CONFIG, without starting |
| 0x23 | `BLE_STREAM_MSG_POCKET_GUITAR_SONG` | Pocket Guitar song file JSON (UTF-8): opens Pocket Guitar if needed and selects the song as slot 0xFF |

#### Pocket Guitar song from the app
The app keeps the songs and their music; the board only gets the chart. To play a song from the app:

1. Send the song file JSON (the format of `game/pocketGuitar/songs/*.json`) as `BLE_STREAM_MSG_POCKET_GUITAR_SONG`:
   `[0x10, 0x23, size u32 big-endian]`, then `[0x11, chunk…]` until `size` bytes are sent. Wait for the `ACK`
   indication after every write. The board accepts writes up to `BLE_STREAM_MAX_WRITE` (244) bytes when the
   phone negotiated a large enough MTU (`BLE_MTU` 247), so a chunk is at most MTU − 4 bytes.
2. The board answers with a song selection event (song slot 0xFF). It only works on the select screen; during a
   song, or with an invalid song, it answers with an "invalid payload" error and keeps the previous song.
3. The song starts from the board (strum) or with `BLE_GAME_CONTROL_START`. On every song start event the app
   starts the music so that song position `start position ms` plays now (negative: after that many ms).
   Pause, resume, quit and the result arrive as game state events and the song start event of the resume.

#### Protobuf-like game config fields
| Field ID | Constant | Meaning |
| --- | --- | --- |
| 0x01 | `BLE_STREAM_FIELD_GAME_ID` | Game type id: Piano Tiles or Simon Says |
| 0x02 | `BLE_STREAM_FIELD_SEED` | Deterministic RNG seed |
| 0x03 | `BLE_STREAM_FIELD_NUM_STEPS` | Number of steps in the generated sequence |
| 0x04 | `BLE_STREAM_FIELD_HIT_ACTION` | Hit action payload (JSON-like dictionary or encoded action data) |
| 0x05 | `BLE_STREAM_FIELD_MISS_ACTION` | Miss action payload |
| 0x06 | `BLE_STREAM_FIELD_GAME_NAME` | Optional name for the generated game |

What a generated config does:

- **Simon Says:** Simple mode with exactly this sequence (`num_steps` blocks from `seed`), started at once.
- **Piano Tiles:** Classic mode with `num_steps` tiles from `seed`; the run starts with the tap on the start tile.
- The same seed gives the same sequence or tiles on every board. The hit and miss actions are stored in the config but not used by these games; their feedback is part of the game design.

Example for a generated game config:

- `BLE_STREAM_MSG_GAME_CONFIG` payload contains:
  - `game_id = 0x01` (Piano Tiles)
  - `seed = 123456`
  - `num_steps = 16`
  - `hit_action = { "score": 10, "haptic": { "effect_id": 1, "duration_ms": 40 }, "feedback_color": [0, 150, 255] }`
  - `miss_action = { "score": 0, "haptic": { "effect_id": 47, "duration_ms": 250 }, "action": "fail" }`

The stream layer accepts chunked transfers and reassembles them before dispatching the protobuf-like config to the game generator. This lets the phone or host device send larger sequences and generator metadata without exceeding BLE packet limits.

Example transfer sequence:

1. `BLE_STREAM_MSG_INIT` with `[message type, total size u32 big-endian]`, or only `[total size u32 big-endian]` when the assembled data starts with its message type byte (as `Test/ble_stream_game_config_test.py` sends it)
2. repeated `BLE_STREAM_MSG_CHUNK` messages with slices of the serialized protobuf payload; the transfer is dispatched as soon as the total size has arrived
3. `BLE_STREAM_MSG_COMMIT` (optional): dispatches whatever is still buffered; after a complete transfer it does nothing

A malformed transfer is answered with an "invalid stream" error and the stream channel stays usable.

This flow is designed for selecting, generating, and loading a seeded game definition over BLE while keeping packet sizes small and deterministic.
