"""pressstart2p_font.py: rasterise Press Start 2P to the 8x8 grid the title UI draws text on.

Licence: Press Start 2P is by CodeMan38 (cody@zone38.net), Copyright 2012 The Press Start 2P Project
Authors, released under the SIL Open Font License 1.1. The licence text is in
knowledge\\licences\\PressStart2P-OFL.txt, copied from the upstream file at
https://github.com/google/fonts/blob/main/ofl/pressstart2p/OFL.txt and checked on 2026-10-21: it is OFL
1.1, so the font may be used, embedded and redistributed with our software as long as the copyright
notice and the licence travel with it. The OFL also forbids selling the font on its own and forbids using
the Reserved Font Name "Press Start 2P" for a modified version; rasterising glyphs into a sprite sheet for
a game is use, not a modified font, and this note plus the licence file is the required notice.

The font was designed on an 8x8 pixel grid, so rendering it at 8 px with hinting and thresholding the
alpha gives one crisp 8x8 cell per glyph with no antialiasing. That is the whole trick; no scaling, no
resampling. Every glyph is checked to fit its cell, and a glyph that does not is an error rather than
something to crop, because a cropped glyph on a 1 px grid loses a stroke.

Usage:
    python tools\\art\\pressstart2p_font.py            # calibration table, exit 1 if a glyph does not fit
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

CELL = 8
THRESHOLD = 128

FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "fonts", "PressStart2P-Regular.ttf")

# The contract glyph set for spr_pp_font8, in ASCII order (TITLE-COORD.md, and tests\test_make_title_ui.py).
# 77 glyphs as of card t_f476435e (decision D13): the 74 that shipped before it plus `/`, `[` and `]`, which the
# battle HP line and the drive caption ask for. ASCII order fixes where they sit: `/` after `.` and before `0`,
# `[` and `]` after `Z` and before `a`.
GLYPHS = sorted(" !\"'()*,-./0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ[]abcdefghijklmnopqrstuvwxyz", key=ord)

_face = None


def face():
    global _face
    if _face is None:
        if not os.path.isfile(FONT_PATH):
            raise SystemExit("the Press Start 2P font is missing: %s" % FONT_PATH)
        _face = ImageFont.truetype(FONT_PATH, CELL)
    return _face


def bitmap(ch: str) -> list:
    """The glyph as 8 rows of 8 characters, '#' where the pixel is lit and '.' where it is clear."""
    canvas = Image.new("L", (CELL * 2, CELL * 2), 0)
    draw = ImageDraw.Draw(canvas)
    draw.text((0, 0), ch, font=face(), fill=255)
    pixels = canvas.load()
    rows = []
    for y in range(CELL):
        row = "".join("#" if pixels[x, y] >= THRESHOLD else "." for x in range(CELL))
        rows.append(row)
    # Anything outside the first cell is a glyph that will not fit; report it instead of cropping.
    outside = [
        (x, y) for y in range(CELL * 2) for x in range(CELL * 2)
        if pixels[x, y] >= THRESHOLD and (x >= CELL or y >= CELL)
    ]
    if outside:
        raise SystemExit("glyph %r bleeds outside an 8x8 cell at %s" % (ch, outside[:6]))
    return rows


def ink_count(ch: str) -> int:
    return sum(row.count("#") for row in bitmap(ch))


def calibration() -> tuple:
    """(rows, blank): (glyph, bbox width, bbox height, ink) for every contract glyph, plus blanks."""
    lines = []
    blank = []
    for ch in GLYPHS:
        rows = bitmap(ch)
        lit = [(x, y) for y in range(CELL) for x in range(CELL) if rows[y][x] == "#"]
        if not lit:
            if ch != " ":
                blank.append(ch)
            lines.append((repr(ch), 0, 0, 0))
            continue
        xs = [x for x, _ in lit]
        ys = [y for _, y in lit]
        lines.append((repr(ch), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, len(lit)))
    return lines, blank


def main() -> int:
    lines, blank = calibration()
    for name, width, height, ink in lines:
        print("%-6s %dx%d ink %d" % (name, width, height, ink))
    if blank:
        print("FAIL blank glyphs: %s" % ", ".join(repr(ch) for ch in blank))
        return 1
    widest = max(width for _, width, _, _ in lines)
    tallest = max(height for _, _, height, _ in lines)
    print("\n%d glyphs, widest %d, tallest %d, cell %dx%d: %s"
          % (len(lines), widest, tallest, CELL, CELL,
             "all fit" if widest <= CELL and tallest <= CELL else "DO NOT FIT"))
    return 0 if widest <= CELL and tallest <= CELL else 1


if __name__ == "__main__":
    sys.exit(main())
