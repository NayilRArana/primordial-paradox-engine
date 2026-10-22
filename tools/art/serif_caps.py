#!/usr/bin/env python3
"""Our own slab serif capitals, for the v2 title logo.

Clean room: every letterform in SERIF is drawn here as a 7 wide by 9 tall grid of characters, written in
this project for this project. Nothing is traced, copied or imported from any existing game or from any
font file, and no external font is read at runtime.

Why a new alphabet: the first title logo scaled the 5x7 UI font, which has no serifs and no stroke
weight, so the wordmark read as small computer text rather than as a chunky carved capital. A logo
wants slab serifs, thick stems and a flat foot, so the letters below are drawn from scratch on a 7x9
grid, with the serifs as explicit rows of the grid rather than as an effect applied afterwards.

The grid:
  7 wide (x 0 to 6), 9 tall (y 0 to 8)
  '#' is ink, '.' is empty

The letters present are the ones the title logo needs: PRIMORDIAL PARADOX. A letter that is not in the
dictionary raises, so a typo in the logo text fails loudly instead of drawing a blank.
"""

from __future__ import annotations

SERIF = {
    "A": [
        "..###..",
        ".#####.",
        "##...##",
        "##...##",
        "#######",
        "##...##",
        "##...##",
        "##...##",
        "###.###",
    ],
    "D": [
        "#######",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "#######",
    ],
    "I": [
        ".#####.",
        "..##...",
        "..##...",
        "..##...",
        "..##...",
        "..##...",
        "..##...",
        "..##...",
        ".#####.",
    ],
    "L": [
        "###....",
        "##.....",
        "##.....",
        "##.....",
        "##.....",
        "##.....",
        "##.....",
        "##.....",
        "#######",
    ],
    "M": [
        "##...##",
        "###.###",
        "#######",
        "##.#.##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "###.###",
    ],
    "O": [
        ".#####.",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        ".#####.",
    ],
    "P": [
        "#######",
        "##...##",
        "##...##",
        "##...##",
        "######.",
        "##.....",
        "##.....",
        "##.....",
        "####...",
    ],
    "R": [
        "#######",
        "##...##",
        "##...##",
        "##...##",
        "######.",
        "##.##..",
        "##..##.",
        "##..##.",
        "###..##",
    ],
    "X": [
        "##...##",
        "##...##",
        ".##.##.",
        "..###..",
        ".##.##.",
        "##...##",
        "##...##",
        "##...##",
        "###.###",
    ],
}

SERIF_W = 7
SERIF_H = 9


def mask(ch: str) -> set:
    """The set of filled cells of one letter, at font resolution."""
    if ch not in SERIF:
        raise KeyError("no slab serif capital for %r" % ch)
    rows = SERIF[ch]
    if len(rows) != SERIF_H or any(len(row) != SERIF_W for row in rows):
        raise ValueError("the grid of %r is not %dx%d" % (ch, SERIF_W, SERIF_H))
    return {(x, y) for y in range(SERIF_H) for x in range(SERIF_W) if rows[y][x] == "#"}
