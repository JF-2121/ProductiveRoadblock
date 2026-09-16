#### EVENT IDs for BLE Event Channel ##
##### Error Codes for BLE Event Channel ##
BLE_EVENT_ID_ERROR = const(0xFF)
BLE_ERROR_CODE_GENERIC = const(0x00)
BLE_ERROR_CODE_WRONG_COMMAND = const(0x01)
BLE_ERROR_CODE_INVALID_GAME_ID = const(0x02)
BLE_ERROR_CODE_GAME_NOT_LOADED = const(0x03)
BLE_ERROR_CODE_INVALID_STREAM = const(0x04)
BLE_ERROR_CODE_INVALID_PAYLOAD = const(0x05)
BLE_ERROR_CODE_STREAM_NOT_INITIALIZED = const(0x06)

#### Key Press/Release Events for BLE Event Channel ##
BLE_EVENT_ID_KEY_PRESS = const(0x01)
BLE_KEY_PRESS = const(0x00)
BLE_KEY_RELEASE = const(0x01)

#### Game Interaction Events for BLE Event Channel ##
BLE_EVENT_ID_GAME = const(0x02)
BLE_GAME_STATE_UPDATE = const(0x00)
BLE_GAME_SCORE_UPDATE = const(0x01)
BLE_GAME_SELECTED = const(0x02)  # [game_id, variant (0xFF = none)], game 0x00 = start screen

BLE_EVENT_ID_PLAY_SOUND = const(0x03)
BLE_EVENT_ID_BATTERY_REPORT = const(0x04)      # answer to GET_TELEMETRY
BLE_EVENT_ID_CALIBRATION_REPORT = const(0x05)  # answer to RUN_AUTOCAL

#### Pocket Guitar Events for BLE Event Channel ##
# Payloads documented in game/pocketGuitar/pocket_guitar_control.py and the README
BLE_EVENT_ID_SONG_START = const(0x06)
BLE_EVENT_ID_NOTE_RESULT = const(0x07)
BLE_EVENT_ID_OVERSTRUM = const(0x08)
BLE_EVENT_ID_SUSTAIN_END = const(0x09)
BLE_EVENT_ID_SONG_RESULT = const(0x0A)
BLE_EVENT_ID_SONG_SELECTION = const(0x0B)

#### Simon Says Events for BLE Event Channel: [subtype, payload...] ##
# Payloads documented in game/simonSays/simon_says_control.py and the README
BLE_EVENT_ID_SIMON_SAYS = const(0x0C)
BLE_SIMON_RUN_START = const(0x00)
BLE_SIMON_WATCH = const(0x01)
BLE_SIMON_CUE = const(0x02)
BLE_SIMON_TURN = const(0x03)
BLE_SIMON_PRESS = const(0x04)
BLE_SIMON_ROUND_CLEAR = const(0x05)
BLE_SIMON_MISTAKE = const(0x06)
BLE_SIMON_RESULT = const(0x07)

#### Piano Tiles Events for BLE Event Channel: [subtype, payload...] ##
# Payloads documented in game/pianoTiles/pianoTiles_control.py and the README
BLE_EVENT_ID_PIANO_TILES = const(0x0D)
BLE_PIANO_RUN_START = const(0x00)
BLE_PIANO_TILE = const(0x01)
BLE_PIANO_SPEED = const(0x02)
BLE_PIANO_TIME_LEFT = const(0x03)
BLE_PIANO_MISTAKE = const(0x04)
BLE_PIANO_RESULT = const(0x05)

### BLE Command Channel Configuration
BLE_COMMAND_CHANNEL_MAX_QUEUE_SIZE = const(10)  # Max number of commands in the queue
BLE_COMMAND_CHANNEL_PROCESSING_INTERVAL_MS = const(100)  # Interval for processing commands

#### COMMAND IDs for BLE Command Channel ##
##### Game Control Commands (act on the open game) ##
BLE_CMD_GAME_CONTROL = const(0x01)
BLE_GAME_CONTROL_START = const(0x00)
BLE_GAME_CONTROL_STOP = const(0x01)     # quit the game, back to the start screen
BLE_GAME_CONTROL_RESET = const(0x02)    # quit the run, back to the game's ready screen
BLE_GAME_CONTROL_RESUME = const(0x03)
BLE_GAME_CONTROL_SELECT = const(0x04)   # [game_id] or [game_id, variant]
BLE_GAME_CONTROL_LOAD = const(0x05)
BLE_GAME_CONTROL_TRIGGER_HAPTIC = const(0x06)  # [effect_id 1-123]
BLE_GAME_CONTROL_RUN_AUTOCAL = const(0x07)
BLE_GAME_CONTROL_SET_BRIGHTNESS = const(0x08)  # [level 0-255]
BLE_GAME_CONTROL_GET_TELEMETRY = const(0x09)
BLE_GAME_CONTROL_PAUSE = const(0x0A)

##### Pocket Guitar Commands ##
BLE_CMD_POCKET_GUITAR = const(0x02)
BLE_POCKET_GUITAR_SELECT_SONG = const(0x00)        # [song slot]
BLE_POCKET_GUITAR_SELECT_DIFFICULTY = const(0x01)  # [difficulty 0-3]
BLE_POCKET_GUITAR_SELECT_MODE = const(0x02)        # [0 play, 1 practice]
BLE_POCKET_GUITAR_SET_DELAY_OFFSET = const(0x03)   # [offset ms, i16 little-endian]
BLE_POCKET_GUITAR_SET_OPTIONS = const(0x04)        # [bits: 0 beat lines, 1 beat tick, 2 sustain hum]
BLE_POCKET_GUITAR_GET_SELECTION = const(0x05)

#### Stream Channel Message Types ##
BLE_STREAM_MSG_INIT = const(0x10)
BLE_STREAM_MSG_CHUNK = const(0x11)
BLE_STREAM_MSG_COMMIT = const(0x12)
BLE_STREAM_MSG_ABORT = const(0x13)

BLE_STREAM_MSG_GAME_CONFIG = const(0x20)
BLE_STREAM_MSG_GAME_SELECT = const(0x21)
BLE_STREAM_MSG_GAME_LOAD = const(0x22)
BLE_STREAM_MSG_POCKET_GUITAR_SONG = const(0x23)  # song file JSON (UTF-8): opens Pocket Guitar and selects the song

BLE_STREAM_FIELD_GAME_ID = const(0x01)
BLE_STREAM_FIELD_SEED = const(0x02)
BLE_STREAM_FIELD_NUM_STEPS = const(0x03)
BLE_STREAM_FIELD_HIT_ACTION = const(0x04)
BLE_STREAM_FIELD_MISS_ACTION = const(0x05)
BLE_STREAM_FIELD_GAME_NAME = const(0x06)

## BLE MIDI ##
