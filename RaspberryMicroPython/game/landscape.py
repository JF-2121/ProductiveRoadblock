"""Landscape layout for the MIDI screen: 8 columns wide, 4 rows tall.

The board is held with the mechanical keys at the bottom right, so the bottom row of the picture is
the edge with the mechanical keys and the base row of a layout (the white keys, the drum pads) is
right above them. Cells are numbered row by row from the top left, cell = y * WIDTH + x, which is
also the grid key of that pad. MIDI_FLIP_ROWS / MIDI_FLIP_COLUMNS in pico_config.py mirror the
picture onto the board when it is held the other way round.
"""
import pico_config as config

WIDTH = config.GRID_NUM_COLS   # 8 columns
HEIGHT = config.GRID_NUM_ROWS  # 4 rows
CELLS = WIDTH * HEIGHT


def _grid_key(cell):
    x = cell % WIDTH
    y = cell // WIDTH
    grid_row = HEIGHT - 1 - y if config.MIDI_FLIP_ROWS else y
    grid_col = WIDTH - 1 - x if config.MIDI_FLIP_COLUMNS else x
    return grid_row * config.GRID_NUM_COLS + grid_col


# KEY[cell] = grid key that shows a cell, CELL[grid key] = cell of a pressed pad
KEY = tuple(_grid_key(cell) for cell in range(CELLS))
CELL = tuple(KEY.index(key) for key in range(CELLS))
