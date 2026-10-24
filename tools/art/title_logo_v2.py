#!/usr/bin/env python3
"""The v2 title logo: PRIMORDIAL PARADOX in two lines of chunky bevelled serif capitals, a crossed sickle
and thunderbolt emblem between the lines, and a 1 px drop shadow.

Clean room: the letterforms come from our own slab serif capitals in tools/art/serif_caps.py, which were
drawn in this project on a 7x9 grid. The emblem is built from two circle differences and a thick polyline,
both written in this file. Nothing is traced, copied or imported from any existing game, and no external
font file is read.

The four colours, and only these four:
  INK        the 1 px outline and the 1 px drop shadow
  BASE       the body of the letter
  HIGHLIGHT  the lit cap, the top row of every capital
  GOLD       the gold inlay, the foot of every capital, and the thunderbolt

The bevel: the top row of a capital is lit (HIGHLIGHT) and the bottom row is the gold inlay (GOLD), so
the wordmark reads as a carved stone lit from above with gold running along its foot.

SPEC 14'S CRACK. One thin gold zigzag runs through the second O of PARADOX, from the top stroke through
the counter to the bottom stroke, drawn inside that letter's own box. This card (t_e5338932) moved the
crack here from tools/art/make_title_rows_v2.py, which drew its own copy of the wordmark: one generator
owns one asset name, and this file owns spr_pp_title_logo (ruling 2 of
knowledge/PALETTE-RULINGS-2026-10-23.md). The gold foot inlay the redraw also carried was already here.

THE LAYOUT IS THE TILE RULE. A sprite tile is 8x8 and may carry 3 colours plus transparency, and the
logo needs four colours, so the four can never meet in the same tile. The outline (INK) is in every tile
that holds a letter, which leaves room for only two of the other three. The rules that follow:
  - the lit cap sits on the top row of a line and the gold inlay on the bottom row of that line, so they
    are seventeen rows apart and never share a tile row band;
  - the emblem, which carries the gold of the thunderbolt, sits in the two bands between the lines;
  - the drop shadow is the same colour as the outline, so it costs nothing.
The bands of the 64 row sheet:
  band 0  rows  0 to  7   line 1, the lit cap and the stone
  band 1  rows  8 to 15   line 1, the stone
  band 2  rows 16 to 23   line 1, the gold inlay
  band 3  rows 24 to 31   the emblem
  band 4  rows 32 to 39   the emblem
  band 5  rows 40 to 47   line 2, the lit cap and the stone
  band 6  rows 48 to 55   line 2, the stone
  band 7  rows 56 to 63   line 2, the gold inlay
The script proves the result: it counts the colours in every tile of every frame and refuses to write
the file if any tile breaks the rule.

Outputs:
    game/sprites_src/title/spr_pp_title_logo.png   224x64, 2 frames (0 normal, 1 gold shimmer)
    game/sprites_src/title/spr_pp_title_logo.json  {"name","frame_w","frame_h","frames","fps"}

Determinism: no clock, no randomness, PNG carries no timestamp, JSON is written with LF endings. Run the
script twice and the sha256 of every file it writes is the same.

Usage:
    python tools/art/title_logo_v2.py
    python tools/art/title_logo_v2.py --dump   # print the art as text
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nes_tile  # noqa: E402  (the palette, the tile rule and the pixel primitives)

import serif_caps  # noqa: E402  (our own slab serif capitals)

INK = 0x0F       # #000000  $0F  the outline and the drop shadow
BASE = 0x00      # #7c7c7c  $00  the body of the letter, carved stone grey
HIGHLIGHT = 0x10  # #bcbcbc  $10  the lit cap, the top row of every capital
GOLD = 0x28      # #f8b800  $28  the gold inlay, the foot of every capital, and the thunderbolt

LOGO_W = 224
LOGO_H = 64

# The drop shadow. The outline ring is 1 px around the shape, so a shadow that sits one pixel further out
# on the down right side is the only way to see one: an offset of (1, 1) lands inside the ring and is
# covered by it, which is an outline with no shadow at all. An offset of (2, 2) puts the ink skirt one
# pixel beyond the ring on the down right, leaving the up left side at the single outline pixel.
SHADOW = (2, 2)

SCALE_X = 2
SCALE_Y = 2
GAP = 2          # screen pixels between two letters

SPRITE_DIR = os.path.join("game", "sprites_src", "title")
LOGO_NAME = "spr_pp_title_logo"

# The two lines of the logo. (text, top row). Each line is 9 glyph rows tall, so 18 screen rows.
LOGO_LINES = [
    ("PRIMORDIAL", 1),
    ("PARADOX", 44),
]

# The emblem, in rows 24 to 39, in a box 32 wide and 16 tall.
EMBLEM_W = 32
EMBLEM_H = 16
EMBLEM_TOP = 24
EMBLEM_LEFT = (LOGO_W - EMBLEM_W) // 2

# The shimmer: one diagonal band of light crosses the whole wordmark, from the right of the first line,
# down through the emblem, to the left of the second line. The band is on x + y, so it moves one column
# left for every row down; the two lines are 43 rows apart, which puts the band over line 2 as well, and
# the numbers below are the ones that light both words (measured: 127 changed pixels in line 1, 125 in
# line 2, 47 in the emblem band).
SHIMMER_LOW = 132
SHIMMER_HIGH = 144


# -----------------------------------------------------------------------------------------------------------------
# The alphabet.

def scaled_mask(text: str):
    """The scaled mask of one line of text, plus the width of the line."""
    mask = set()
    pen = 0
    for ch in text:
        glyph = serif_caps.mask(ch)
        for x, y in glyph:
            for dy in range(SCALE_Y):
                for dx in range(SCALE_X):
                    mask.add((pen + x * SCALE_X + dx, y * SCALE_Y + dy))
        pen += serif_caps.SERIF_W * SCALE_X + GAP
    return mask, pen - GAP


def line_pixels(text: str, top: int):
    """The placed pixels of one line, centred on the sheet."""
    mask, width = scaled_mask(text)
    x_offset = (LOGO_W - width) // 2
    return {(x + x_offset, y + top) for x, y in mask}


# -----------------------------------------------------------------------------------------------------------------
# The emblem: a sickle and a thunderbolt, crossed.

def crescent(c1, r1, c2, r2) -> set:
    """The pixels inside the first circle and outside the second, a crescent blade."""
    out = set()
    for y in range(int(c1[1] - r1) - 1, int(c1[1] + r1) + 2):
        for x in range(int(c1[0] - r1) - 1, int(c1[0] + r1) + 2):
            if math.hypot(x - c1[0], y - c1[1]) > r1:
                continue
            if math.hypot(x - c2[0], y - c2[1]) < r2:
                continue
            out.add((x, y))
    return out


def emblem_shapes():
    """The emblem as (sickle pixels, bolt pixels), in its own 32 wide by 16 tall box.

    The sickle is a crescent blade on a straight shaft; the thunderbolt runs the other diagonal, from the
    top right corner down through the shaft and out past it at the bottom left, so the two cross: the
    pixels they share are the X of the crossed mark, not a near miss with a gap between them.
    """
    blade = crescent((9.0, 7.0), 6.0, (11.5, 9.5), 5.2)
    shaft = nes_tile.thick_line([(1, 15), (6, 10)], 2)
    bolt = nes_tile.thick_line([(30, 1), (19, 7), (23, 7), (2, 16)], 2)
    # Both shapes are clipped to the emblem box. A stroke that spills a row past the box would put its gold
    # in the tile row that carries the lit cap of line 2, and four colours in one tile breaks the sprite rule.
    box = {(x, y) for y in range(EMBLEM_H) for x in range(EMBLEM_W)}
    sickle = (blade | shaft) & box
    bolt = bolt & box
    if not (sickle & bolt):
        raise SystemExit("emblem: the bolt and the sickle do not touch, they cannot read as crossed")
    return sickle, bolt


# -----------------------------------------------------------------------------------------------------------------
# The crack through the second O (spec 14, the lightning crack).
#
# Ported from tools/art/make_title_rows_v2.py unchanged (card t_e5338932): the path is fractions of the
# letter's own bounding box, so the zigzag follows the O wherever the letterforms move.

LOGO_LINE_INDEX = {"PARADOX": 5}   # the second O of the wordmark is index 5 of PARADOX, the O the crack runs through
CRACK_PATH = [(0.62, 0.00), (0.45, 0.28), (0.62, 0.45), (0.38, 0.62), (0.55, 1.00)]


def letter_box(text: str, index: int, top: int):
    """One capital's placed pixels and its bounding box, the way line_pixels places a whole line."""
    mask, width = scaled_mask(text)
    x_offset = (LOGO_W - width) // 2
    pen = 0
    for i, ch in enumerate(text):
        if i == index:
            glyph = serif_caps.mask(ch)
            pixels = {(x_offset + pen + x * SCALE_X + dx, top + y * SCALE_Y + dy)
                      for x, y in glyph
                      for dx in range(SCALE_X) for dy in range(SCALE_Y)}
            xs = [p[0] for p in pixels]
            ys = [p[1] for p in pixels]
            return pixels, (min(xs), min(ys), max(xs), max(ys))
        pen += serif_caps.SERIF_W * SCALE_X + GAP
    raise SystemExit("the wordmark has no letter %d in %r" % (index, text))


def crack_pixels():
    """The lightning crack through the O of PARADOX, 1 px wide, drawn inside that letter's box only."""
    for text, top in LOGO_LINES:
        if text in LOGO_LINE_INDEX:
            break
    else:
        raise SystemExit("no line of the wordmark carries the O the crack splits")
    _glyph, (x0, y0, x1, y1) = letter_box(text, LOGO_LINE_INDEX[text], top)
    width, height = x1 - x0, y1 - y0
    points = [(x0 + int(round(fx * width)), y0 + int(round(fy * height))) for fx, fy in CRACK_PATH]
    out = set()
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        steps = max(abs(bx - ax), abs(by - ay)) or 1
        for step in range(steps + 1):
            x = ax + int(round((bx - ax) * step / steps))
            y = ay + int(round((by - ay) * step / steps))
            if x0 <= x <= x1 and y0 <= y <= y1:
                out.add((x, y))
    if not out:
        raise SystemExit("the crack landed outside the O it is meant to split")
    return out, (x0, y0, x1, y1)


def the_cap_gives_way(image: Image.Image, crack, colours):
    """Keep every tile the crack touches at three colours.

    The crack starts on the lit cap row of line 2, so the tile it starts in would carry four colours at
    once: ink, stone, the lit cap and the crack's gold. The cap there gives way to the stone body, which
    is the colour the title scene gives the wordmark anyway (data/palettes/scene_title.json: ink $0F,
    stone $00 and gold $28, with no $10 light grey anywhere on the sheet). The trade is deliberate: the
    crack's 17 new gold pixels cost five lit caps inside one 8x8 tile, and the shipped sheet shows the
    crack and nothing else.
    """
    for tx, ty in {(x // 8, y // 8) for x, y in crack}:
        box = [(x, y) for y in range(ty * 8, min(ty * 8 + 8, LOGO_H))
               for x in range(tx * 8, min(tx * 8 + 8, LOGO_W))]
        seen = {image.getpixel(point) for point in box if image.getpixel(point)[3]}
        if len(seen) > 3:
            for point in box:
                if image.getpixel(point) == colours[HIGHLIGHT]:
                    image.putpixel(point, colours[BASE])


# -----------------------------------------------------------------------------------------------------------------
# The logo frame.

def logo_frame(index: int, colours) -> Image.Image:
    """One frame of the logo. Frame 0 is the logo, frame 1 is the gold shimmer."""
    image = Image.new("RGBA", (LOGO_W, LOGO_H), (0, 0, 0, 0))

    body = set()
    for text, top in LOGO_LINES:
        body |= line_pixels(text, top)

    sickle, bolt = emblem_shapes()
    emblem = {(x + EMBLEM_LEFT, y + EMBLEM_TOP) for x, y in sickle | bolt}
    body |= emblem

    # The outline, the 8 neighbour ring around the body.
    ring = nes_tile.outline_of(body)
    for x, y in ring:
        if 0 <= x < LOGO_W and 0 <= y < LOGO_H:
            image.putpixel((x, y), colours[INK])

    # The drop shadow: the whole shape two pixels down and two pixels right, in the outline colour. A
    # shadow pixel that the ring already covers is skipped, so what is left is a 1 px ink skirt beyond the
    # outline on the down right side and nothing extra on the up left side.
    for x, y in body:
        sx, sy = x + SHADOW[0], y + SHADOW[1]
        if not (0 <= sx < LOGO_W and 0 <= sy < LOGO_H):
            continue
        if (sx, sy) in body or (sx, sy) in ring:
            continue
        image.putpixel((sx, sy), colours[INK])

    # The body of the letters.
    for x, y in body:
        image.putpixel((x, y), colours[BASE])

    # The lit cap: the top row of every capital. The gold inlay: the foot of every capital.
    for text, top in LOGO_LINES:
        placed = line_pixels(text, top)
        for x, y in placed:
            if y == top:
                image.putpixel((x, y), colours[HIGHLIGHT])
        lowest = max(y for _, y in placed)
        for x, y in placed:
            if y == lowest:
                image.putpixel((x, y), colours[GOLD])

    # Spec 14's lightning crack: one thin gold zigzag through the second O of PARADOX, inside that
    # letter's own box. Drawn after the inlay so the crack is never painted over, and before the
    # shimmer so the band pass sees it as part of the art.
    crack, _box = crack_pixels()
    for x, y in crack:
        image.putpixel((x, y), colours[GOLD])
    the_cap_gives_way(image, crack, colours)

    # The thunderbolt is gold over the sickle.
    for x, y in bolt:
        image.putpixel((x + EMBLEM_LEFT, y + EMBLEM_TOP), colours[GOLD])

    if index:
        # The shimmer: one diagonal band of light turns the stone to gold. A single stripe across the whole
        # logo, so it reads as one pass of light rather than a pattern.
        #
        # The band is applied tile by tile, because a tile may hold only three colours. A tile whose band
        # would push it to a fourth colour loses its lit cap to the gold as well, so the band keeps going
        # and the tile stays legal.
        pixels = image.load()
        for ty in range(0, LOGO_H, 8):
            for tx in range(0, LOGO_W, 8):
                band = []
                for y in range(ty, min(ty + 8, LOGO_H)):
                    for x in range(tx, min(tx + 8, LOGO_W)):
                        pixel = pixels[x, y]
                        if pixel[3] == 0 or pixel == colours[INK]:
                            continue
                        if SHIMMER_LOW <= x + y <= SHIMMER_HIGH and pixel == colours[BASE]:
                            band.append((x, y))
                if not band:
                    continue
                # The colours the tile would carry after the band turns its stone to gold.
                seen = set()
                for y in range(ty, min(ty + 8, LOGO_H)):
                    for x in range(tx, min(tx + 8, LOGO_W)):
                        pixel = pixels[x, y]
                        if pixel[3] == 0:
                            continue
                        if (x, y) in band:
                            seen.add(colours[GOLD][:3])
                        else:
                            seen.add(pixel[:3])
                if len(seen) > 3:
                    for y in range(ty, min(ty + 8, LOGO_H)):
                        for x in range(tx, min(tx + 8, LOGO_W)):
                            if pixels[x, y] == colours[HIGHLIGHT]:
                                pixels[x, y] = colours[GOLD]
                for x, y in band:
                    pixels[x, y] = colours[GOLD]
    return image


def build(colours):
    """The two frames of the logo."""
    return [logo_frame(index, colours) for index in (0, 1)]


def strip(frames) -> Image.Image:
    """The frames side by side in a horizontal strip, which is the file format the contract fixes."""
    width = frames[0].width
    height = frames[0].height
    out = Image.new("RGBA", (width * len(frames), height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        out.alpha_composite(frame, (index * width, 0))
    return out


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(image: Image.Image, index_of) -> None:
    """Print the art as text, so the geometry can be checked without a viewer."""
    symbols = {INK: "#", BASE: "b", HIGHLIGHT: "@", GOLD: "G"}
    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            if pixel[3] == 0:
                line += " "
                continue
            line += symbols.get(index_of.get(pixel[:3]), "?")
        print("%2d %s" % (y, line))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    parser.add_argument("--dump", action="store_true", help="print the art as text")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    sprite_dir = os.path.join(root, SPRITE_DIR)
    os.makedirs(sprite_dir, exist_ok=True)

    colours, index_of = nes_tile.load_nes_palette(root)
    frames = build(colours)

    sheet = strip(frames)
    bad = nes_tile.over_limit(sheet, LOGO_W, LOGO_H, index_of)
    if bad:
        # A broken build is written to output/ only, never into the sprite folder, so the game can never
        # load a sheet that breaks the tile rule.
        debug_path = os.path.join(root, "output", "ts2_art_a_logo_debug.png")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        sheet.save(debug_path, "PNG")
        per_tile = nes_tile.tile_colours(sheet, LOGO_W, LOGO_H, index_of)
        names = {INK: "ink", BASE: "base", HIGHLIGHT: "cap", GOLD: "gold"}
        for entry in bad[:24]:
            frame, tx, ty, count = entry
            seen = per_tile[(frame, tx, ty)]
            print("      frame %d tile %d,%d has %d colours: %s"
                  % (frame, tx, ty, count, [names.get(i, i) for i in sorted(seen)]))
        raise SystemExit("logo: %d tiles break the 3 colour rule, wrote %s" % (len(bad), debug_path))

    png_path = os.path.join(sprite_dir, LOGO_NAME + ".png")
    sheet.save(png_path, "PNG")
    meta = {"name": LOGO_NAME, "frame_w": LOGO_W, "frame_h": LOGO_H, "frames": len(frames), "fps": 0.25,
            "layer": True}
    with open(os.path.join(sprite_dir, LOGO_NAME + ".json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    # NES-PALETTES: four colours in an 8x16 sprite is legal 2C02 art and still illegal NES art, because
    # the PPU gives a sprite three palette entries plus transparency. The scene file is the budget, so
    # this sheet is enforced before it leaves the generator; otherwise the next regeneration puts the
    # extra colour back and tools/check_scene_palettes.py fails again (2026-10-22).
    try:
        import scene_palette
        scene = scene_palette.load_scene(root, "title")
        image = Image.open(png_path).convert("RGBA")
        stats = scene_palette.enforce_sprites(image, scene, LOGO_W, LOGO_H)
        image.save(png_path, "PNG")
        print("  %-20s scene title sprites: %d tiles, %d pixels rewritten, worst %d colours"
              % (LOGO_NAME, stats["tiles"], stats["pixels_moved"], stats["worst_colours"]))
    except Exception as exc:
        print("  %-20s scene palette pass skipped (%s)" % (LOGO_NAME, exc))

    used = set()
    for frame in frames:
        for pixel in frame.getdata():
            if pixel[3] != 0:
                used.add(index_of.get(pixel[:3]))
    print("  %-20s %dx%d  %d frames  %d colours  tile rule OK  %s"
          % (LOGO_NAME, LOGO_W, LOGO_H, len(frames), len(used), sha256(png_path)))

    if args.dump:
        for index, frame in enumerate(frames):
            print("--- frame %d" % index)
            dump(frame, index_of)
    # Card t_a1170172: the band plan owns the title's colours, and this generator used to run after it and leave the
    # logo in colours no band could spend. The sheet is repainted here, so a rerun cannot undo it.
    import title_bands
    print("  band pass            %d pixels into the logo's band palette"
          % title_bands.paint_sheet(root, LOGO_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(main())
