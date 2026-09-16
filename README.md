# Productive Roadblock

A Flutter app + a Raspberry Pi Pico game controller that turns real, active play into earned
screen time. Complete a physical minigame on the board (or a phone-only fallback if you don't have
one) to unlock a distracting app like Instagram for exactly as long as you actively played.

The Pico isn't optional set dressing — the two halves are built to work together:

```
 You open Instagram
         │  (iOS Shortcuts automation, see below)
         ▼
 Productive Roadblock opens, locked
         │
         ▼
 Connect the board over Bluetooth (or use the phone-only fallback)
         │
         ▼
 Play Piano Tiles / Simon Says / Pocket Guitar on the physical NeoTrellis grid
         │  (active seconds only — sitting idle earns nothing)
         ▼
 Time played → time unlocked, 1:1 by default
         │
         ▼
 Instagram is usable for exactly that long, then it locks again
```

## 🎮 The games

Three real games run **on the board itself** — the Pico drives its own LEDs, haptics and game
logic; the phone just follows along and turns active play into unlocked time:

| Game | On the board | On the phone (no board) |
| --- | --- | --- |
| **Piano Tiles** | Physical pads light up, hit them in time | On-screen tap grid |
| **Simon Says** | Watch the board's light sequence, repeat it | On-screen sequence game |
| **Pocket Guitar** | Strum along to a real song on the pads | — (board required; the phone streams the audio in sync) |

The board also doubles as a **Bluetooth MIDI controller** for a DAW when no phone is connected in
game mode — same hardware, held sideways, see
[`RaspberryMicroPython/README.md`](RaspberryMicroPython/README.md#board-modes).

## 📦 Repo layout

```
lib/                      Flutter app
├── main.dart             Routes, app lifecycle, board-started-game following
├── models/                board_games.dart (routes ↔ BLE game ids), song/track formats
├── screens/               game_menu_screen, home_screen, piano_tiles/simon_says/pocket_guitar
│                          screens, freeplay (phone-only fallback), debug tools, setup wizard
├── services/              ble_service.dart (the BLE protocol), one *_session.dart per game
│                          (board sync + audio/scoring), sound_cache, notifications
├── state/                 session_manager.dart (locked/unlocked + earned time),
│                          play_time.dart (idle-gated active-play tracking → credits time),
│                          app_state.dart (BLE connection state)
└── widgets/               game_ui.dart, board_connect.dart, on-phone fallback games

RaspberryMicroPython/      Pico firmware (MicroPython) — the other half of the app
├── main.py                Entry point
├── pico_config.py         Pins, BLE name/UUIDs, per-game tuning
├── ble_handler/           GATT service: commands, events, chunked stream transfers
├── game/                  Game manager + Piano Tiles / Simon Says / Pocket Guitar / MIDI screen
├── keyboard/              NeoTrellis driver, mechanical strum keys, MIDI layouts
├── haptic/                DRV2605L haptic driver
└── test/                  Standalone BLE/game smoke tests (bypass the app entirely)
```

## 🔧 Requirements

**Phone app**
- Flutter SDK (stable channel) + `flutter doctor` passing
- Xcode, for iOS (this app is built and tested for iOS; Android/desktop targets exist via Flutter
  but aren't the focus)

**Board (optional but recommended — this is half the project)**
- Raspberry Pi Pico W or Pico 2W
- 2× Adafruit NeoTrellis 4×4 (I2C, forming one 4×8 grid)
- 2 mechanical buttons (Pocket Guitar's strum keys)
- A DRV2605L haptic driver + motor (optional, for buzz feedback)

The app works fully without any of this — every game has an on-screen fallback — but the physical
board is the intended way to play.

## 🚀 Quick start

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/ProductiveRoadblock.git
cd ProductiveRoadblock
flutter pub get
```

### 2. Run the phone app (no hardware needed yet)

```bash
flutter run --release
```

or open `ios/Runner.xcworkspace` in Xcode and run on a physical iPhone. Everything works without
a board: use **DEBUG: SKIP BLUETOOTH** on the home screen, or the **DEBUG CONTROLS** screen, to
bypass the lock and try every screen/game in its phone-only form.

### 3. Flash and pair the Pico (to play for real)

1. Flash MicroPython onto the Pico W/2W.
2. Wire it up (see below), then copy the whole [`RaspberryMicroPython/`](RaspberryMicroPython/)
   folder onto the board — with Thonny, or the MicroPico VS Code extension. **If you're
   re-flashing an already-used board, wipe it first** (`MicroPico: Delete all files from board`);
   an incremental upload can leave a stale `main.py` still running underneath your new files.
3. Reset the board. It advertises as **`PhoneMidiBoard`**, boots to its own start screen, and is
   ready to be found.
4. In the app, tap **connect** (the home screen / game menu scan for it automatically once
   Bluetooth is on). Once connected, playing any game on the physical grid earns time exactly
   like the on-screen version does — and pressing Play on the board itself opens the matching
   phone screen automatically, so the two always stay in sync.

**Full BLE protocol, wiring diagrams, MIDI mode, and every game's on-board design doc:**
[`RaspberryMicroPython/README.md`](RaspberryMicroPython/README.md) — that file is the source of
truth for anything hardware-side; this README only covers the shape of it.

#### Wiring reference

| Signal | GPIO |
| --- | --- |
| NeoTrellis I2C SDA | 18 |
| NeoTrellis I2C SCL | 19 |
| NeoTrellis interrupt | 17 |
| NeoTrellis I2C addresses | `0x2F` / `0x2E` |
| Mechanical strum key 1 (blue) | 10 |
| Mechanical strum key 2 (red) | 11 |
| Haptic driver I2C SDA | 12 |
| Haptic driver I2C SCL | 13 |

## 🔗 iOS Shortcuts automation (2 minutes)

This is what actually blocks Instagram and brings you back here — no Screen Time API access is
needed (Apple doesn't grant that outside Family Sharing), so the trick is a Shortcuts automation
that fires the instant Instagram opens:

1. Open the **Shortcuts** app → **Automation** tab → **+** → **App**.
2. Choose **Instagram**, **Is Opened**, **Next**.
3. Add action **Show Notification** (title/body of your choice).
4. Add action **Open App** → **Productive Roadblock**.
5. Turn **Ask Before Running** **OFF** (this is the step that makes it automatic) → **Done**.
6. Test it: open Instagram, the notification should appear and tapping it opens this app.

The in-app setup screen (`/setup`) walks through the same steps with screenshots.

## 🐛 Troubleshooting

- **Board won't connect** — confirm it's powered and advertising as `PhoneMidiBoard`, Bluetooth is
  on, and no other phone/laptop already has a connection open (the Pico only accepts one central
  at a time and stops advertising while connected — disconnect before running anything in
  `RaspberryMicroPython/test/`).
- **NeoTrellis not wired up yet** — that's fine, `keyboard/neotrellis.py` logs a warning and
  continues instead of crashing; BLE still comes up so you can bring up firmware before hardware
  arrives.
- **Stale firmware after re-flashing** — wipe the board before uploading (see step 2 above); we've
  lost real debugging time to an old `main.py` silently still running.
- **Notification never appears** — check the Shortcuts automation is enabled and **Ask Before
  Running** is off, and that Shortcuts has notification permission.

## 📄 License

No license has been chosen yet for this repository.
