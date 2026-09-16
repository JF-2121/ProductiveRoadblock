"""Portrait layout for the start screen, Simon Says and Piano Tiles.

These screens are used with the board turned by 90 degrees against Pocket Guitar: 4 columns
wide and 8 rows tall. Cells are numbered row by row from the top left, cell = y * WIDTH + x.
PORTRAIT_FLIP_ROWS / PORTRAIT_FLIP_COLUMNS in pico_config.py mirror the picture onto the board.
"""
import pico_config as config

WIDTH = config.GRID_NUM_ROWS   # 4 columns
HEIGHT = config.GRID_NUM_COLS  # 8 rows
CELLS = WIDTH * HEIGHT


def _grid_key(cell):
    x = cell % WIDTH
    y = cell // WIDTH
    grid_row = WIDTH - 1 - x if config.PORTRAIT_FLIP_COLUMNS else x
    grid_col = y if config.PORTRAIT_FLIP_ROWS else HEIGHT - 1 - y
    return grid_row * config.GRID_NUM_COLS + grid_col


# KEY[cell] = grid key that shows a cell, CELL[grid key] = cell of a pressed pad
KEY = tuple(_grid_key(cell) for cell in range(CELLS))
CELL = tuple(KEY.index(key) for key in range(CELLS))
