#!/usr/bin/env python3
"""make_title_exhaust_v2.py: the exhaust puffs, four hand authored 16x16 frames that grow.

Card t_9774ff51 (AUTO-SPRITE-NEXT). Row `spr_title_exhaust` in data/sprite_redraw_queue.json is the
highest priority row that is not done (P1). Its shipped sheet is 64x16, four 16x16 frames, two entries
`$20` #f8f8f8 and `$0C` #004058, and card t_13e25e31 measured it at 9 failing pairs on
output/exhaust_road_ground.png: frame 0's body is `$0C`, which is the ground's own `$0C` and 0 luminance
rows from the `$0F` black, and frames 1 to 3 have a `$20` body, which is the white blob on the road's
`$20` marking.

What this file draws, and why:

  frames, size  the row's craft rule SP-046 asks a four frame effect to change SIZE, not just position.
                The puff now grows on every frame: 5x4, 8x6, 10x8 and 12x10 pixels of outer ink, and
                rises two rows as it grows, which is what an exhaust does as the car pulls away.
  entries       `$20` #f8f8f8 white is the body and `$0C` #004058 dark teal is the 1 px outline, which is
                what the tree ships. This file drew the body in `$10` #bcbcbc at first, and gamedev's ruling
                on card t_474cde50 is why it does not: the puff sits in screen bands 12 to 13, the title
                band plan paints those bands with bg3 (`$0C $0B $20`), and tools/art/title_bands.py flattens
                a `$10` body to `$20` on the way to game/sprites_src (measured: 118 pixels move, and the
                landed sheet is #f8f8f8 118 px + #004058 70 px). A redraw that is a different colour from
                the file it becomes is a preview, not a ship, so the cells are drawn in the shipping pair.
                Both entries are in title sp2 (`$0C $10 $20`) and in sp3 (`$0C $0B $20`), so R6 holds; `$0C`
                vs `$20` reads 21:1 on the tarmac and the ink carries the puff on the road's `$20` marking.
  no figure     the puff is a TILED LAYER, not a figure (card t_474cde50). Over one full scroll its 16x16
                window crosses four ground colours on 2C02 rows 0 to 2, `$0F` black 72.7 percent, `$0B`
                green 15.4, `$0C` teal 6.0, `$20` white 5.9, and no single body entry clears RULE 0 point 2
                on both ends: a body clearing 3:1 on `$0B` needs luminance 0.31 or more and one clearing 3:1
                on `$20` needs 0.30 or less. palette_synergy reads it through R1b, where the ink `$0C`
                clears the light grounds and the body `$20` clears the dark ones.

Nothing is scaled, recoloured or traced. The cells are written out by hand and the letters are looked up
in data/nes_palette.json entries only.

The file is written to output/redraws, the scratch folder a redraw goes in since game/art retired (card
t_4e54cc9e). It is drawn in the shipping pair (`$20` body, `$0C` ink) so the preview and the tree agree;
game/sprites_src/title/spr_title_exhaust.png is written by tools/art/make_title_car.py, which calls
build_frames() here rather than drawing a second copy of the same four cells.

Usage:
    python tools/art/make_title_exhaust_v2.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

ROOT = os.path.dirname(os.path.dirname(HERE))

# 2C02 entries, named, so no reader has to decode a hex twice.
SHIP_BODY = "#f8f8f8"  # $20 white, the puff's body, and the only body bg3 can carry at the puff's band
SHIP_INK = "#004058"   # $0C dark teal, the 1 px outline
LIGHT = "#bcbcbc"      # $10 light grey, the first draft's body; kept as the named alternative, never ships
TEAL = "#004058"       # $0C dark teal, the outline
CLEAR = (0, 0, 0, 0)
def hex_rgb(code):
    code = code.lstrip("#")
    return tuple(int(code[index:index + 2], 16) for index in (0, 2, 4)) + (255,)


LETTERS = {"L": hex_rgb(LIGHT), "X": hex_rgb(TEAL), ".": CLEAR}

FRAMES = [
    # frame 0, the small puff at the pipe: 5 x 4 of ink box, two rows of body inside
    ["................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "..XXX...........",
     ".XLLLX..........",
     ".XLLLX..........",
     "..XXX...........",
     "................",
     "................",
     "................"],
    # frame 1, one size up and one row higher
    ["................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "................",
     "...XXXX.........",
     "..XLLLLX........",
     ".XLLLLLLX.......",
     ".XLLLLLLX.......",
     "..XLLLLX........",
     "...XXXX.........",
     "................",
     "................",
     "................"],
    # frame 2, wider than it is tall, still rising
    ["................",
     "................",
     "................",
     "................",
     "....XXXX........",
     "...XLLLLX.......",
     "..XLLLLLLX......",
     ".XLLLLLLLLX.....",
     ".XLLLLLLLLX.....",
     "..XLLLLLLX......",
     "...XLLLLX.......",
     "....XXXX........",
     "................",
     "................",
     "................",
     "................"],
    # frame 3, the last of the cycle: the biggest, thinnest, furthest from the pipe
    ["................",
     "................",
     ".....XXXX.......",
     "....XLLLLX......",
     "...XLLLLLLX.....",
     "..XLLLLLLLLX....",
     ".XLLLLLLLLLLX...",
     ".XLLLLLLLLLLX...",
     "..XLLLLLLLLX....",
     "...XLLLLLLX.....",
     "....XLLLLX......",
     ".....XXXX.......",
     "................",
     "................",
     "................",
     "................"],
]


def check_grid(rows, index):
    if len(rows) != 16 or any(len(row) != 16 for row in rows):
        raise SystemExit("frame %d is not a 16x16 grid" % index)
    for row in rows:
        for ch in row:
            if ch not in LETTERS:
                raise SystemExit("frame %d carries the unknown cell %r" % (index, ch))


def frame_image(rows, body=None, ink=None):
    """One frame from a character grid, in the two entries asked for (default: what ships)."""
    letters = {"L": hex_rgb(body or SHIP_BODY), "X": hex_rgb(ink or SHIP_INK), ".": CLEAR}
    image = Image.new("RGBA", (16, 16), CLEAR)
    pixels = image.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            pixels[x, y] = letters[ch]
    return image


def build_frames(body=None, ink=None):
    """The four puff frames as images, drawn in `body` and `ink`.

    tools/art/make_title_car.py, the generator that owns game/sprites_src/title/spr_title_exhaust.png,
    calls this with its own two entries so one file owns the drawing and the tree cannot drift from it.
    """
    images = []
    for index, rows in enumerate(FRAMES):
        check_grid(rows, index)
        images.append(frame_image(rows, body, ink))
    return images


def audit(images):
    """Per frame: drawn pixels, entries, the largest fill, and the worst 8x8 tile."""
    report = []
    for index, image in enumerate(images):
        counts = {}
        for y in range(16):
            for x in range(16):
                r, g, b, a = image.load()[x, y]
                if a:
                    key = "#%02x%02x%02x" % (r, g, b)
                    counts[key] = counts.get(key, 0) + 1
        worst = 0
        for ty in range(0, 16, 8):
            for tx in range(0, 16, 8):
                seen = set()
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        r, g, b, a = image.load()[x, y]
                        if a:
                            seen.add((r, g, b))
                worst = max(worst, len(seen))
        total = sum(counts.values())
        largest = max(counts.items(), key=lambda item: item[1])
        report.append({"frame": index, "drawn": total, "entries": counts,
                       "largest": largest[0], "largest_px": largest[1],
                       "largest_pct": round(100.0 * largest[1] / total, 1), "worst_tile": worst})
    return report


def main() -> int:
    images = build_frames()
    out = os.path.join(ROOT, "output", "redraws")
    os.makedirs(out, exist_ok=True)
    sheet = Image.new("RGBA", (64, 16), CLEAR)
    for index, image in enumerate(images):
        sheet.alpha_composite(image, (index * 16, 0))
    path = os.path.join(out, "spr_title_exhaust.png")
    sheet.save(path, "PNG")
    print("  output/redraws/spr_title_exhaust.png %dx%d, 4 frames of 16x16" % (sheet.width, sheet.height))
    for record in audit(images):
        print("  frame %d: %d drawn px, entries %s, largest %s %d px (%.1f%%), worst 8x8 tile %d colour(s)"
              % (record["frame"], record["drawn"],
                 " ".join("%s %d" % (key, value) for key, value in sorted(record["entries"].items())),
                 record["largest"], record["largest_px"], record["largest_pct"], record["worst_tile"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
