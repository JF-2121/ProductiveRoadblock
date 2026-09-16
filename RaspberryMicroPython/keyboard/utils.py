import pico_config as config


class KeyEvent:
    __slots__ = ['action', 'key', 'time']
    def __init__(self, action: int, key: int, time: int = None):
        self.action = action
        self.key = key
        self.time = time  # time.ticks_ms() when the event was detected, None if unknown

def grid_to_board(grid_key):
    """Map a key of the combined 4x8 grid to (board index, on-board key)."""
    row = grid_key // config.GRID_NUM_COLS
    col = grid_key % config.GRID_NUM_COLS
    board_index = col // config.NEOTRELLIS_NUM_COLS
    return board_index, row * config.NEOTRELLIS_NUM_COLS + (col % config.NEOTRELLIS_NUM_COLS)

def board_to_grid(board_index, key):
    """Map an on-board key of board `board_index` to the combined 4x8 grid."""
    row = key // config.NEOTRELLIS_NUM_COLS
    col = key % config.NEOTRELLIS_NUM_COLS
    return row * config.GRID_NUM_COLS + board_index * config.NEOTRELLIS_NUM_COLS + col

def grid_key_to_xy(grid_key):
    """Map a combined grid key to (x, y) coordinates."""
    return grid_key % config.GRID_NUM_COLS, grid_key // config.GRID_NUM_COLS

def xy_to_grid_key(x, y):
    """Map (x, y) coordinates to a combined grid key."""
    return y * config.GRID_NUM_COLS + x