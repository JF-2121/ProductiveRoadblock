import bluetooth
from micropython import const
from machine import Pin

# Board Modes
BOARD_MODE_MIDI = const(0)
BOARD_MODE_GAME = const(1)
BOARD_MODE_GAMEPAD = BOARD_MODE_GAME

# PIN Configuration (GPIO PINS FROM PI PICO 2W BOARD) for NeoTrellis Keypad
# I2C Neotrellis Keypad Configuration
NEOTRELLIS_I2C_PORT = const(1)
NEOTRELLIS_I2C_SDA_PIN = Pin(const(18))
NEOTRELLIS_I2C_SCL_PIN = Pin(const(19))
NEOTRELLIS_INT_PIN = Pin(const(17), Pin.IN, Pin.PULL_UP)
NEOTRELLIS_I2C_FREQ = const(400_000)

MECH_KEY_1 = Pin(const(10), Pin.IN, Pin.PULL_UP)
MECH_KEY_2 = Pin(const(11), Pin.IN, Pin.PULL_UP)
MECH_KEY_DEBOUNCE_MS = const(10)
# Debug: print every mechanical key interrupt, including edges ignored as bounce
MECH_KEY_DEBUG_LOG = True

KEY_ACTION_RELEASED = const(0)
KEY_ACTION_PRESSED = const(1)

# The two mechanical keys are the strum keys; their key caps are blue and red.
# Pressing both at once is shown as purple (red + blue light).
STRUM_KEY_BLUE = const(32)  # MECH_KEY_1
STRUM_KEY_RED = const(33)   # MECH_KEY_2
COLOR_STRUM_RED = (255, 0, 0)
COLOR_STRUM_BLUE = (0, 0, 255)
COLOR_STRUM_BOTH = (255, 0, 255)

# Pocket Guitar board orientation. The game is laid out as in GAME_DESIGN.md (hit row 3,
# feedback column 0); these flips mirror the whole picture and the pads onto the real board.
# Both True = board turned by 180 degrees.
POCKET_GUITAR_FLIP_ROWS = True     # True: hit row is grid row 0
POCKET_GUITAR_FLIP_COLUMNS = True  # True: feedback column is grid column 7

# Portrait orientation for the start screen, Simon Says and Piano Tiles: the board is held
# turned by 90 degrees against Pocket Guitar, 4 columns wide and 8 rows tall (see game/portrait.py).
# Default: the top row is grid column 7 and the left column is grid row 0, so Piano Tiles
# tiles travel towards grid column 0 as in the first version.
PORTRAIT_FLIP_ROWS = False     # True: top and bottom swapped, tiles travel towards grid column 7
PORTRAIT_FLIP_COLUMNS = False  # True: left and right swapped

## Bluetooth Low Energy (BLE) Configuration ##
BLE_DEVICE_NAME = const("PhoneMidiBoard")
BLE_SERVICE_UUID = bluetooth.UUID("6E400000-B5A3-F393-E0A9-E50E24DCCA9E")
BLE_EVENT_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
BLE_COMMAND_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
BLE_DATA_STREAM_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

BLE_MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
BLE_MIDI_CHAR_UUID = bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")
# MIDI mode: what every pad sends is in keyboard/midi_layout.py (see keyboard/MIDI_LAYOUTS.md).
# Note velocity, and the velocity of the "accent" key of a layout.
MIDI_VELOCITY = const(100)
MIDI_ACCENT_VELOCITY = const(127)
# Everything is sent on the channel selected in the MIDI menu, except keys of type "drum":
# those always play on this channel, so a kick stays a kick (10 = General MIDI percussion).
MIDI_DRUM_CHANNEL = const(10)
# MIDI layouts are drawn in landscape: 8 columns wide, 4 rows tall, the bottom row on the side with
# the mechanical keys (bottom right corner). These flips turn the picture if the board is held the
# other way round (see game/landscape.py).
MIDI_FLIP_ROWS = False     # True: top and bottom swapped
MIDI_FLIP_COLUMNS = False  # True: left and right swapped
# While a connected client hasn't chosen game or MIDI yet, how often the board checks whether it
# subscribed to the MIDI notifications (MIDI host) or the game events (game app)
BLE_SESSION_POLL_MS = const(100)
# Largest MTU the board accepts (the phone asks for it) and the largest stream write it can take
# (MTU - 3). With the default MTU of 23 a stream chunk is 20 bytes, a Pocket Guitar song would take a minute.
BLE_MTU = const(247)
BLE_STREAM_MAX_WRITE = const(244)

### BLE Event Channel Configuration
BLE_EVENT_CHANNEL_MAX_QUEUE_SIZE = const(32)  # Max number of events in the queue
BLE_EVENT_CHANNEL_NOTIFICATION_INTERVAL_MS = const(10)  # Interval for sending notifications
# Debug: print every event notification that is sent
BLE_EVENT_DEBUG_LOG = False

## NEO TRELLIS CONFIGURATION ##
#Board Constants
NEOTRELLIS_NUM_ROWS = const(4)
NEOTRELLIS_NUM_COLS = const(4)
NEOTRELLIS_NUM_KEYS = const(16)

#Grid Constants
GRID_NUM_ROWS = const(4)
GRID_NUM_COLS = const(8)
GRID_NUM_KEYS = const(32)

# Reads per interrupt while the shared interrupt line stays low, and how often a game loop reads the
# boards itself when the line is low without a pending read (a lost interrupt edge)
NEOTRELLIS_IRQ_DRAIN_LIMIT = const(4)
NEOTRELLIS_POLL_MS = const(20)


# The physical left-to-right order of the boards. Board index 0 is the leftmost
# board, so swap these two if the grid ever runs the wrong way round.
NEOTRELLIS_I2C_ADDR_1 = const(0x2F)
NEOTRELLIS_I2C_ADDR_2 = const(0x2E)

# Seesaw keypad FIFO edge types (armed via SEESAW_KEYPAD_EVENT). The FIFO only
# reliably queues transition edges, not the level-based EDGE_HIGH(0)/EDGE_LOW(1).
# Seesaw reports a press as RISING and a release as FALLING (same as Adafruit's NeoTrellis examples).
NEOTRELLIS_EDGE_FALLING = const(2)  # key released
NEOTRELLIS_EDGE_RISING = const(3)   # key pressed


# PIN CONFIGURATION(GPIO PINS FROM PI PICO 2W BOARD) for NeoTrellis Keypad
# I2C Configuration


#Animation and Color Configuration

STARTUP_ANIMATION_STEP_MS = const(250)
KEY_PRESS_COLOR_R = const(32)
KEY_PRESS_COLOR_G = const(0)
KEY_PRESS_COLOR_B = const(0)
STARTUP_COLOR_R = const(0)
STARTUP_COLOR_G = const(32)
STARTUP_COLOR_B = const(0)

# Key Pin Configuration (GPIO PINS FROM PI PICO 2W BOARD)



## VIBRATION MOTOR CONFIGURATION ##
MOTOR_I2C_PORT = const(0)
MOTOR_I2C_SDA_PIN = const(12)
MOTOR_I2C_SCL_PIN = const(13)
MOTOR_I2C_FREQ = const(400_000)

# DRV2605L setup for the iPhone 15 Taptic Engine / LRA path.
MOTOR_DRV2605L_MODE_INTERNAL_TRIGGER = const(0x00)
MOTOR_DRV2605L_LIBRARY_ID = const(6)
MOTOR_DRV2605L_RATED_VOLTAGE = const(0x50)
MOTOR_DRV2605L_OD_CLAMP_VOLTAGE = const(0x80)
MOTOR_DRV2605L_FEEDBACK_CONTROL_LRA = const(0x80)
MOTOR_DRV2605L_CONTROL3_LRA = const(0x01)
MOTOR_DRV2605L_LRA_PERIOD = const(0x4E)

# Starter effect IDs for the keys that trigger haptics.
MOTOR_TAPTIC_EFFECTS = (1, 10, 56, 70, 82)

# Game Logic Configuration
GAME_ID_NONE = const(0x00)
GAME_ID_START_SCREEN = const(0x00)  # no game: the start screen
GAME_ID_PIANO_TILES = const(0x01)
GAME_ID_SIMON_SAYS = const(0x02)
GAME_ID_POCKET_GUITAR = const(0x03)
GAME_ID_MIDI = const(0x10)  # not a game: the MIDI pads while a MIDI host is connected (not selectable over BLE)

# Game variants, as used by the start screen and the BLE select command.
# Pocket Guitar: the variant is the difficulty 0-3 (easy, medium, hard, expert).
POCKET_GUITAR_MODE_PLAY = const(0)      # red strum key
POCKET_GUITAR_MODE_PRACTICE = const(1)  # blue strum key
SIMON_SAYS_MODE_SIMPLE = const(0)
SIMON_SAYS_MODE_ENDLESS = const(1)
PIANO_TILES_MODE_CLASSIC = const(0)
PIANO_TILES_MODE_ZEN = const(1)
PIANO_TILES_MODE_ARCADE = const(2)

# Holding both mechanical keys this long goes back one screen (Pocket Guitar: pause / quit /
# start screen; Simon Says and Piano Tiles: start screen)
BACK_HOLD_MS = const(2000)

GAME_CLOCK_MODE_TIME_BASED = const(0x00)
GAME_CLOCK_MODE_STEP_BASED = const(0x01)

GAME_STATE_INIT = const(0x00)
GAME_STATE_READY = const(0x01)
GAME_STATE_RUNNING = const(0x02)
GAME_STATE_PAUSED = const(0x03)
GAME_STATE_OVER = const(0x04)
GAME_STATE_WIN = const(0x05)

## Random Number Generator Seed
### Linear Congruential Generator (LCG) parameters
RNG_LCG_a = const(1664525)
RNG_LCG_c = const(1013904223)
RNG_LCG_m = const(2**32)

## General Config
GAME_NUMBER_OF_STEPS = const(10)
GAME_ROWS = const(4)
GAME_COLS = const(8)
GAME_NUMBER_OF_KEYS = const(GAME_ROWS * GAME_COLS)

## Piano Tiles Game Config
PIANO_TILES_STEP_WINDOW_MS = const(2000)
PIANO_TILES_STEP_ADVANCE_ON = const("hit")
PIANO_TILES_STEP_RESET_ON = const("miss")
PIANO_TILES_STEP_ON_HIT_FEEDBACK_COLOR = const((0, 255, 0))
PIANO_TILES_STEP_ON_HIT_SCORE = const(10)
PIANO_TILES_STEP_ON_MISS_ACTION = const("fail")
PIANO_TILES_STEP_ON_MISS_FEEDBACK_COLOR = const((255, 0, 0))
PIANO_TILES_STEP_ON_MISS_HAPTIC_DURATION_MS = const(250)
PIANO_TILES_STEP_ON_MISS_HAPTIC_INTENSITY = const(255)


