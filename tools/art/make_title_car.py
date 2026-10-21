#!/usr/bin/env python
"""TS-C: the title car, the cast busts and Theo's storm cloud.

Contract: TITLE-COORD.md in the project root and specs\\14-title-screen-drive.md
plus its night drive addendum. Everything here is original, clean room: no
reference to, copy of, or trace of any existing game's art.

What this writes (deterministic: no clock, no randomness, no window, no network):
  game\\sprites_src\\title\\spr_title_car.png      64x32, 3 frames (1 px body bob)
  game\\sprites_src\\title\\spr_title_wheel.png    10x10, 4 frames (rotation)
  game\\sprites_src\\title\\spr_title_exhaust.png  12x10, 4 frames (puff)
  game\\sprites_src\\title\\spr_title_ronan.png    12x12, 8 frames (watch glance at 5 to 7)
  game\\sprites_src\\title\\spr_title_theo.png     12x12, 8 frames (4 idle bob, 4 turn to speak)
  game\\sprites_src\\title\\spr_title_bubble.png   14x10, 3 frames (one dot, two dots, three dots)
  game\\sprites_src\\title\\spr_title_cloud.png    24x12, 3 frames (2 normal, 1 flash)
  plus one JSON beside each: {"name", "frame_w", "frame_h", "frames", "fps"}

Preview:
  output\\title_car_preview.png   the assembled car on a road strip at 3x, then every frame of
                                  every part at 3x, labelled.

GEOMETRY (the manager's revision of 2026-10-20, which this script follows)

The car tile is 64x32, side view, facing right. The road is at tile row 31 and
the tyre bottoms touch it.

  roof            flat, row 6, x 18 to 44
  hatch           nearly vertical, at the left, x 8 to 12
  windscreen      rakes forward from the roof down to the cowl
  bonnet          flat, rows 17 to 19, at the right
  window band     rows 8 to 15, black, with the A pillar and the B pillar in it
  bottom edge     straight, row 25
  wheel arches    cut into the body at x 14 and x 46, radius 6, and the 10x10
                  wheel sits in the arch with its tyre bottom on row 31
  door            the front door, x 28 to 38, in mismatched beige
  roof rack       rails on the roof with a brown suitcase on top, x 20 to 40,
                  rows 2 to 6
  headlights      on, yellow at the right; the lit cone is drawn by the world layer
  tail light      red at the left
  bumpers         chrome at both ends

The 3 body frames differ only by a 1 px vertical bob of the body.

The bust tiles are 12x12. Only the head and the shoulders are drawn, in the
lower 8 rows of the tile, so that when the tile is pasted at y 4 the face sits
inside the window band, which is rows 8 to 15. Ronan is the driver, in the front
window on the right of the frame. Theo is the passenger, in the rear window to
his left, one pixel column further back.

PLACEMENT (the offsets the composer needs, relative to the car origin)

  body         spr_title_car      (0, 0)
  rear wheel   spr_title_wheel    (9, 22)
  front wheel  spr_title_wheel    (41, 22)
  exhaust      spr_title_exhaust  (0, 20)
  Theo         spr_title_theo     (14, 4)
  Ronan        spr_title_ronan    (31, 4)

Palette: every pixel of every file is a master palette entry from
data\\palette.json, and no single sprite uses more than 16 of them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PALETTE_PATH = os.path.join(ROOT, "data", "palette.json")
SPRITE_DIR = os.path.join(ROOT, "game", "sprites_src", "title")
OUT_DIR = os.path.join(ROOT, "output")
FONT_PATH = os.path.join(SPRITE_DIR, "spr_pp_font8.png")

MAX_SPRITE_COLOURS = 16

# ---------------------------------------------------------------------------------------------------
# Palette entries, by index into data/palette.json. The index is the truth.
#
# The colours the world layers already spend (TS-B) are reused wherever they work, so the title
# room stays as tight as it can. The cast needs a few entries the world does not have: 15 for the
# suitcase, 16 and 17 for the faces, 34 and 35 for the beige door, and 40 for the blond hair.
# ---------------------------------------------------------------------------------------------------

INK = 0            # #0b0b0f  the glass band, the wheel wells, the outlines
ASPHALT = 1        # #1c1c24  the road
DIM = 4            # #7a7a88  dim grey, the beard, the reflections
BRIGHT = 5         # #c8c8d4  white, the chrome, the spokes
BROWN = 15         # #7d4a1a  the suitcase
SKIN_DEEP = 16     # #a86d2a  a face in shadow
SKIN = 17          # #d8a55c  a face
RED = 22           # #b33a52  the tail light
GREEN_DEEP = 25    # #232a12  the shadow along the sills
GREEN_MID = 26     # #3a4420  the racing green body
GREEN_LIGHT = 27   # #55632f  the lit top surfaces, Theo's bomber jacket
STONE_DEEP = 30    # #14110f  the dark stone, the cloud underside, the tweed check
STONE_DARK = 31    # #262019  the flat cap, the roof rack
STONE_MID = 32     # #3b3226  the tweed
BEIGE = 34         # #75634c  the mismatched door, in shadow
BEIGE_LIGHT = 35   # #a6957c  the mismatched door, in the moonlight
HAIR = 40          # #b38f28  Theo's blond hair
GOLD = 41          # #e8c65a  the headlight, the lightning, the watch face
NIGHT = 42         # #0a0614  the storm cloud body, the night sky

# The character legend for the pixel art below. A space and a dot are transparent.
LEGEND = {
    " ": None,
    ".": None,
    "K": INK,
    "D": DIM,
    "W": BRIGHT,
    "G": GREEN_MID,
    "g": GREEN_LIGHT,
    "d": GREEN_DEEP,
    "B": BEIGE,
    "b": BEIGE_LIGHT,
    "N": STONE_DARK,
    "n": STONE_MID,
    "m": STONE_DEEP,
    "R": RED,
    "S": SKIN,
    "s": SKIN_DEEP,
    "h": HAIR,
    "Y": GOLD,
    "o": BROWN,
    "C": NIGHT,
}


def load_palette() -> list[tuple[int, int, int]]:
    with open(PALETTE_PATH, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    out = []
    for entry in data["colours"]:
        value = entry.lstrip("#")
        out.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
    return out


PALETTE_RGB = load_palette()
RGB_INDEX = {rgb: index for index, rgb in enumerate(PALETTE_RGB)}


def rgba(index, alpha: int = 255):
    if index is None:
        return (0, 0, 0, 0)
    r, g, b = PALETTE_RGB[index]
    return (r, g, b, alpha)


# ---------------------------------------------------------------------------------------------------
# Small drawing helpers
# ---------------------------------------------------------------------------------------------------

def new_image(width: int, height: int) -> Image.Image:
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))


def stamp_rows(image: Image.Image, top: int, rows: list[str]) -> None:
    """Draw a block of legend rows, one character per pixel."""
    for dy, row in enumerate(rows):
        if len(row) != image.width:
            raise SystemExit("row %r is %d wide, the tile is %d wide" % (row, len(row), image.width))
        for x, ch in enumerate(row):
            if ch not in LEGEND:
                raise SystemExit("unknown legend character %r" % ch)
            index = LEGEND[ch]
            if index is None:
                continue
            image.putpixel((x, top + dy), rgba(index))


def shift_down(image: Image.Image, amount: int) -> Image.Image:
    out = new_image(image.width, image.height)
    out.alpha_composite(image, (0, amount))
    return out


# ---------------------------------------------------------------------------------------------------
# The car body
#
# The silhouette is a row table: for every row, the first and the last column of the body. That
# keeps the shape boxy and readable, which is what a 1980s family hatchback needs at this size.
# ---------------------------------------------------------------------------------------------------

CAR_W, CAR_H = 64, 32

# Row: (first column, last column) of the body.
BODY_ROWS = {
    6: (18, 44),    # the flat roof
    7: (15, 46),
    8: (13, 47),
    9: (12, 48),
    10: (11, 48),
    11: (10, 49),
    12: (10, 49),
    13: (9, 50),
    14: (9, 50),
    15: (9, 51),
    16: (8, 51),    # the belt line
    17: (8, 58),    # the flat bonnet
    18: (8, 58),
    19: (8, 58),
    20: (8, 58),
    21: (8, 58),
    22: (8, 58),
    23: (8, 58),
    24: (8, 58),
    25: (8, 58),    # the straight bottom edge
}

# The wheel arches: centre x, radius. The arch is a half circle cut up into the body, and the
# 10x10 wheel sits in it with the tyre bottom on row 31.
ARCHES = [(14, 6), (46, 6)]
ARCH_CENTRE_Y = 27

# The wheel tiles, 10x10, centred on the arch centres, tyre bottom on row 31.
WHEEL_PLACE = [(9, 22), (41, 22)]

# The mismatched door, in beige, and the shut line behind it.
DOOR_X0, DOOR_X1 = 28, 38
DOOR_TOP, DOOR_BOTTOM = 16, 24

# The B pillar, in body colour, between the two side windows.
B_PILLAR = (26, 28)

# The A pillar, raked with the windscreen, one column per row from the roof down to the cowl.
A_PILLAR_TOP = 44
A_PILLAR_STEP = 6.0 / 11.0


def a_pillar_x(y: int) -> int:
    return int(round(A_PILLAR_TOP + (y - 6) * A_PILLAR_STEP))


def arch_top(cx: int, radius: int, x: int) -> float:
    """The row where the arch cut begins at column x, or a row below the body if there is none."""
    span = radius * radius - (x - cx) * (x - cx)
    if span <= 0:
        return 99.0
    return ARCH_CENTRE_Y - math.sqrt(span)


def build_car_body(bob: int) -> Image.Image:
    """One frame of the car body. The only difference between the frames is the bob."""
    image = new_image(CAR_W, CAR_H)

    # The body itself, green, row by row.
    for y, (x0, x1) in BODY_ROWS.items():
        for x in range(x0, x1 + 1):
            image.putpixel((x, y), rgba(GREEN_MID))

    # The lit top surfaces: the roof, and the flat bonnet at the right.
    for x in range(18, 45):
        image.putpixel((x, 6), rgba(GREEN_LIGHT))
    for x in range(50, 58):
        for y in (17, 18, 19):
            image.putpixel((x, y), rgba(GREEN_LIGHT))

    # The side glass, a black band from the hatch back to the A pillar.
    for y in range(8, 16):
        for x in range(BODY_ROWS[y][0] + 1, a_pillar_x(y) - 1):
            image.putpixel((x, y), rgba(INK))

    # The B pillar, in body colour.
    for y in range(8, 16):
        for x in range(B_PILLAR[0], B_PILLAR[1] + 1):
            image.putpixel((x, y), rgba(GREEN_MID))

    # The windscreen, the dark glass beyond the raked A pillar.
    for y in range(7, 17):
        for x in range(a_pillar_x(y) + 1, BODY_ROWS[y][1] + 1):
            image.putpixel((x, y), rgba(INK))

    # The A pillar itself, in body colour.
    for y in range(7, 17):
        image.putpixel((a_pillar_x(y), y), rgba(GREEN_MID))

    # A faint reflection in the side glass.
    for x, y in [(12, 9), (13, 10), (14, 11), (15, 12), (30, 9), (31, 10), (32, 11)]:
        image.putpixel((x, y), rgba(DIM))

    # The mismatched beige door, with the shut line behind it and a handle.
    for y in range(DOOR_TOP, DOOR_BOTTOM + 1):
        for x in range(DOOR_X0, DOOR_X1 + 1):
            image.putpixel((x, y), rgba(BEIGE_LIGHT))
    for x in range(DOOR_X0, DOOR_X1 + 1):
        image.putpixel((x, DOOR_BOTTOM), rgba(BEIGE))
    for y in range(DOOR_TOP, DOOR_BOTTOM + 1):
        image.putpixel((DOOR_X0, y), rgba(BEIGE))
    image.putpixel((36, 18), rgba(DIM))
    image.putpixel((37, 18), rgba(DIM))

    # The shadow along the sills, so the bottom edge reads as one straight line.
    for y in (24, 25):
        for x in range(8, 59):
            if image.getpixel((x, y))[3] > 0:
                image.putpixel((x, y), rgba(GREEN_DEEP))

    # The wheel arches, cut up into the body, and dark inside.
    for cx, radius in ARCHES:
        for x in range(cx - radius, cx + radius + 1):
            top = arch_top(cx, radius, x)
            for y in range(int(math.ceil(top)), 26):
                if image.getpixel((x, y))[3] > 0:
                    image.putpixel((x, y), rgba(INK))

    # The chrome bumpers, at both ends.
    for x in range(5, 9):
        image.putpixel((x, 22), rgba(BRIGHT))
        image.putpixel((x, 23), rgba(DIM))
    for x in range(58, 62):
        image.putpixel((x, 22), rgba(BRIGHT))
        image.putpixel((x, 23), rgba(DIM))

    # The headlight, on, at the right, and the red tail light at the left.
    for x in range(53, 58):
        image.putpixel((x, 18), rgba(GOLD))
        image.putpixel((x, 19), rgba(GOLD))
    image.putpixel((54, 18), rgba(BRIGHT))
    image.putpixel((55, 19), rgba(BRIGHT))
    for x in range(8, 12):
        image.putpixel((x, 18), rgba(RED))
        image.putpixel((x, 19), rgba(RED))

    # The roof rack: the rails on the roof, and the brown suitcase on top of them.
    for x in range(19, 42):
        image.putpixel((x, 5), rgba(STONE_DARK))
    for x in (20, 30, 40):
        image.putpixel((x, 6), rgba(STONE_DARK))
    for y in range(2, 5):
        for x in range(21, 40):
            image.putpixel((x, y), rgba(BROWN))
    for x in range(21, 40):
        image.putpixel((x, 2), rgba(STONE_DARK))
        image.putpixel((x, 4), rgba(STONE_DARK))
    for x in (26, 34):
        for y in range(2, 5):
            image.putpixel((x, y), rgba(STONE_DARK))

    # The steering wheel, in front of the driver.
    for x, y in [(34, 15), (35, 15), (36, 15), (37, 15), (38, 15)]:
        image.putpixel((x, y), rgba(DIM))

    # A few scuffs, because the car is a battered old thing.
    for x, y in [(22, 22), (23, 22), (44, 21), (45, 21)]:
        if image.getpixel((x, y))[3] > 0:
            image.putpixel((x, y), rgba(GREEN_DEEP))

    if bob:
        image = shift_down(image, bob)
    return image


# ---------------------------------------------------------------------------------------------------
# The wheel
# ---------------------------------------------------------------------------------------------------

WHEEL_W, WHEEL_H = 10, 10


def build_wheel(frame: int) -> Image.Image:
    """A wheel seen from the side, with the spokes turning."""
    image = new_image(WHEEL_W, WHEEL_H)
    draw = ImageDraw.Draw(image)

    draw.ellipse((0, 0, 9, 9), fill=rgba(INK))
    draw.ellipse((1, 1, 8, 8), fill=rgba(DIM))
    draw.ellipse((2, 2, 7, 7), fill=rgba(INK))

    for spoke in range(4):
        angle = spoke * math.pi / 2 + frame * math.pi / 8
        dx = -math.cos(angle)
        dy = math.sin(angle)
        for step in range(1, 5):
            px = int(round(4.5 + dx * step))
            py = int(round(4.5 + dy * step))
            if 0 <= px < WHEEL_W and 0 <= py < WHEEL_H:
                image.putpixel((px, py), rgba(BRIGHT))

    draw.ellipse((3, 3, 6, 6), fill=rgba(BRIGHT))
    image.putpixel((4, 4), rgba(DIM))
    return image


# ---------------------------------------------------------------------------------------------------
# The exhaust puff
# ---------------------------------------------------------------------------------------------------

EXHAUST_W, EXHAUST_H = 12, 10


def build_exhaust(frame: int) -> Image.Image:
    """A puff of exhaust, growing and fading as it goes back."""
    image = new_image(EXHAUST_W, EXHAUST_H)
    draw = ImageDraw.Draw(image)
    size = 2 + frame
    alpha = (230, 190, 150, 100)[frame]
    draw.ellipse((8 - size, 5 - size, 8 + size, 5 + size), fill=rgba(DIM, alpha))
    if frame > 0:
        inner = size - 1
        draw.ellipse((8 - inner, 5 - inner, 8 + inner, 5 + inner), fill=rgba(BRIGHT, alpha))
    return image


# ---------------------------------------------------------------------------------------------------
# The cast
#
# Each bust tile is 12x12. The art is 8 rows tall and sits in the lower 8 rows of the tile, so
# that when the tile is pasted at y 4 the face lands inside the window band, rows 8 to 15.
# ---------------------------------------------------------------------------------------------------

BUST_W, BUST_H = 12, 12
BUST_TOP = 4

# Ronan: flat cap, grey beard, tweed shoulders, a gloved hand on the wheel.
RONAN_ROWS = [
    "    NNNNNN    ",   # the flat cap
    "   NNNNNNNNN  ",   # the cap and its peak, pointing forward
    "   SSSSSSSs   ",   # the face
    "   SKSSKKSs   ",   # the face, with the eyes
    "   DDDDDDDs   ",   # the grey beard
    "    DDDDs     ",   # the beard under the chin
    "  mnnnnnnnnn  ",   # the tweed shoulders
    " mnnmnnnnmnn  ",   # the tweed check
]

# Theo: tall messy blond hair, a wired earbud, an olive bomber collar.
THEO_ROWS = [
    "  h hhhhhh h  ",   # the tall messy hair
    "   hhhhhhhh   ",   # the hair
    "   SSSSSSSs   ",   # the face
    "   SKSSKKSs   ",   # the face, with the eyes
    "   SSKKSSs  K ",   # the open mouth, and the headphone wire
    "   GGGGGGGGK  ",   # the olive bomber collar, and the wire
    "  GggggggggG  ",   # the bomber jacket
    " GggggggggggG ",   # the shoulders
]


def build_ronan(frame: int) -> Image.Image:
    """Ronan Harrow: late fifties, broad, grey beard, flat cap, tweed, driving gloves.

    Frames 5 to 7 are the glance at the wristwatch: the eyes move across the face, the wrist comes
    up with the watch on it, and the gloved hand stays on the wheel.
    """
    rows = [list(row) for row in RONAN_ROWS]
    wrist = None
    if frame >= 5:
        # The eyes move one pixel to the right, towards the watch.
        rows[3][3] = "S"
        rows[3][4] = "K"
        rows[3][7] = "S"
        rows[3][8] = "K"
        # The wrist comes up, further with each frame of the glance.
        wrist = {5: (10, 6), 6: (10, 5), 7: (10, 4)}[frame]
        rows[wrist[1]][wrist[0]] = "N"
    image = new_image(BUST_W, BUST_H)
    stamp_rows(image, BUST_TOP, ["".join(row) for row in rows])
    if wrist is not None:
        # The watch face, a bright pixel on the wrist.
        image.putpixel((wrist[0], wrist[1] - 1), rgba(GOLD))
    # The gloved hand, on the wheel, in the bottom right of the tile.
    image.putpixel((6, 11), rgba(DIM))
    image.putpixel((7, 11), rgba(DIM))
    return image


def build_theo(frame: int) -> Image.Image:
    """Theo Skye: nineteen, restless, messy blond hair, bomber jacket, wired earbuds.

    Frames 0 to 3 are the idle, the head bobbing to the music. Frames 4 to 7 are the turn to say
    something: the head comes round towards the driver and the mouth opens.
    """
    rows = [list(row) for row in THEO_ROWS]
    if frame >= 4:
        turn = frame - 4
        # The head comes round towards the driver, on the right of the frame.
        for index in range(5):
            rows[index] = ["."] + rows[index][:-1]
        if turn >= 1:
            rows[4][4] = "K"
            rows[4][5] = "K"
        if turn >= 2:
            rows[3][4] = "S"
            rows[3][5] = "."
            rows[3][8] = "S"
            rows[3][9] = "."
        if turn >= 3:
            rows[2][4] = "h"
            rows[2][5] = "h"
    else:
        # The bob: the head moves down on the off beat, the shoulders stay.
        if (0, 1, 0, 1)[frame]:
            for index in range(5):
                rows[index] = rows[index][1:] + ["."]
    image = new_image(BUST_W, BUST_H)
    stamp_rows(image, BUST_TOP, ["".join(row) for row in rows])
    return image


# ---------------------------------------------------------------------------------------------------
# The speech bubble and the storm cloud
# ---------------------------------------------------------------------------------------------------

BUBBLE_W, BUBBLE_H = 14, 10


def build_bubble(frame: int) -> Image.Image:
    """A small speech bubble, with one more dot in each frame."""
    image = new_image(BUBBLE_W, BUBBLE_H)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 13, 8), radius=3, fill=rgba(BRIGHT), outline=rgba(INK))
    draw.polygon([(3, 8), (5, 8), (3, 9)], fill=rgba(BRIGHT))
    for dot in range(frame + 1):
        x = 4 + dot * 3
        draw.rectangle((x, 3, x + 1, 4), fill=rgba(INK))
    return image


CLOUD_W, CLOUD_H = 24, 12


def build_cloud(frame: int) -> Image.Image:
    """Theo's storm cloud. The third frame is the soft distant flash."""
    image = new_image(CLOUD_W, CLOUD_H)
    draw = ImageDraw.Draw(image)
    lumps = [(1, 5, 7, 7), (6, 2, 8, 8), (13, 4, 8, 7), (17, 6, 7, 6)]
    for cx, cy, rx, ry in lumps:
        draw.ellipse((cx, cy, cx + rx, cy + ry), fill=rgba(STONE_DEEP))
    for cx, cy, rx, ry in lumps:
        draw.ellipse((cx, cy, cx + rx - 2, cy + ry - 2), fill=rgba(NIGHT))
    if frame == 2:
        draw.ellipse((1, 4, 9, 11), fill=rgba(GOLD, 150))
        draw.ellipse((6, 1, 15, 9), fill=rgba(GOLD, 110))
        draw.polygon([(12, 2), (9, 7), (11, 7), (10, 11), (14, 5), (12, 5)], fill=rgba(BRIGHT))
    else:
        for x, y in [(6, 4), (10, 3), (15, 5), (19, 6)]:
            image.putpixel((x, y), rgba(DIM))
    return image


# ---------------------------------------------------------------------------------------------------
# Writing the strips
# ---------------------------------------------------------------------------------------------------

def save_strip(name: str, frames: list[Image.Image], fps: float, sprite_dir: str) -> str:
    width = frames[0].width
    height = frames[0].height
    strip = new_image(width * len(frames), height)
    for index, frame in enumerate(frames):
        strip.alpha_composite(frame, (index * width, 0))
    png_path = os.path.join(sprite_dir, name + ".png")
    strip.save(png_path, "PNG")
    meta = {"name": name, "frame_w": width, "frame_h": height, "frames": len(frames), "fps": fps}
    with open(os.path.join(sprite_dir, name + ".json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return png_path


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def palette_indices(image: Image.Image) -> set[int]:
    seen = set()
    for pixel in image.getdata():
        if pixel[3] == 0:
            continue
        rgb = pixel[:3]
        if rgb not in RGB_INDEX:
            raise SystemExit("colour %r is not a master palette entry" % (rgb,))
        seen.add(RGB_INDEX[rgb])
    return seen


# ---------------------------------------------------------------------------------------------------
# The preview
# ---------------------------------------------------------------------------------------------------

FONT_ORDER = " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GLYPH_W, GLYPH_H = 5, 7
GLYPH_ADVANCE = 6


def load_font():
    if not os.path.isfile(FONT_PATH):
        return None
    return Image.open(FONT_PATH).convert("RGBA")


def draw_text(dst: Image.Image, font: Image.Image, text: str, x: int, y: int, index: int) -> None:
    for position, ch in enumerate(text.upper()):
        if ch == " ":
            continue
        if ch not in FONT_ORDER:
            return
        offset = FONT_ORDER.index(ch) * 8
        cell = font.crop((offset, 0, offset + 8, 8))
        ink = cell.crop((1, 0, 1 + GLYPH_W, GLYPH_H))
        tinted = Image.new("RGBA", ink.size, rgba(index))
        tinted.putalpha(ink.getchannel("A"))
        dst.alpha_composite(tinted, (x + position * GLYPH_ADVANCE, y))


def build_preview(parts: dict, out_path: str) -> None:
    """The assembled car on a road strip at 3x, then every frame of every part at 3x."""
    scale = 3
    font = load_font()

    # The 1x scene: night sky, a strip of road, and the car standing on it.
    scene_w, scene_h = 128, 56
    scene = new_image(scene_w, scene_h)
    draw = ImageDraw.Draw(scene)
    draw.rectangle((0, 0, scene_w, 30), fill=rgba(NIGHT))
    for x, y in [(9, 5), (30, 3), (52, 9), (86, 4), (108, 8), (118, 2)]:
        draw.point((x, y), fill=rgba(BRIGHT))
    draw.rectangle((0, 40, scene_w, scene_h), fill=rgba(ASPHALT))
    for x in range(0, scene_w, 16):
        draw.rectangle((x, 48, x + 8, 49), fill=rgba(DIM))
    draw.rectangle((0, 39, scene_w, 40), fill=rgba(GREEN_DEEP))

    # The car, at the placement the composer uses. The car origin is at (20, 12), so the tyre
    # bottoms land on scene row 43, on the tarmac.
    scene.alpha_composite(parts["spr_title_car"][0], (20, 12))
    scene.alpha_composite(parts["spr_title_wheel"][0], (29, 34))
    scene.alpha_composite(parts["spr_title_wheel"][0], (61, 34))
    scene.alpha_composite(parts["spr_title_exhaust"][0], (20, 32))
    scene.alpha_composite(parts["spr_title_theo"][0], (34, 16))
    scene.alpha_composite(parts["spr_title_ronan"][0], (51, 16))

    blocks = [("THE ASSEMBLED CAR ON THE ROAD", scene, scale)]
    for label, name in [("CAR BODY 64X32 3 FRAMES 1 PX BOB", "spr_title_car"),
                        ("WHEEL 10X10 4 FRAMES", "spr_title_wheel"),
                        ("EXHAUST 12X10 4 FRAMES", "spr_title_exhaust"),
                        ("RONAN 12X12 8 FRAMES WATCH GLANCE AT 5 TO 7", "spr_title_ronan"),
                        ("THEO 12X12 8 FRAMES 4 IDLE 4 TURN", "spr_title_theo"),
                        ("SPEECH BUBBLE 14X10 3 FRAMES", "spr_title_bubble"),
                        ("STORM CLOUD 24X12 2 FRAMES AND A FLASH", "spr_title_cloud")]:
        blocks.append((label, parts[name][0], scale))

    margin = 8
    label_h = 12
    gap = 10
    sheet_w = margin * 2 + max(max(b[1].width * b[2] for b in blocks), 320)
    sheet_h = margin * 2 + sum(label_h + b[1].height * b[2] + gap for b in blocks)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), rgba(INK))
    y = margin
    for label, image, zoom in blocks:
        if font is not None:
            draw_text(sheet, font, label, margin, y, BRIGHT)
        y += label_h
        big = image.resize((image.width * zoom, image.height * zoom), Image.Resampling.NEAREST)
        sheet.alpha_composite(big, (margin, y))
        y += big.height + gap
    sheet.save(out_path, "PNG")


# ---------------------------------------------------------------------------------------------------
# The main build
# ---------------------------------------------------------------------------------------------------

def dump(image: Image.Image, label: str) -> None:
    """Print an image as text, so the geometry can be checked without a viewer."""
    print("--- %s (%dx%d)" % (label, image.width, image.height))
    symbols = {INK: "#", DIM: ":", BRIGHT: "@", ASPHALT: "-", GREEN_DEEP: "v", GREEN_MID: "G",
               GREEN_LIGHT: "g", BEIGE: "B", BEIGE_LIGHT: "b", STONE_DARK: "x", STONE_MID: "n",
               STONE_DEEP: "m", RED: "r", SKIN: "S", SKIN_DEEP: "s", HAIR: "h", GOLD: "Y",
               BROWN: "o", NIGHT: "C"}
    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            if pixel[3] == 0:
                line += " "
                continue
            line += symbols.get(RGB_INDEX[pixel[:3]], "?")
        print("%2d %s" % (y, line))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--dump", action="store_true", help="print the art as text")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    sprite_dir = os.path.join(root, "game", "sprites_src", "title")
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(root, "output")
    os.makedirs(sprite_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    parts = {
        "spr_title_car": [build_car_body(bob) for bob in (0, 1, 0)],
        "spr_title_wheel": [build_wheel(index) for index in range(4)],
        "spr_title_exhaust": [build_exhaust(index) for index in range(4)],
        "spr_title_ronan": [build_ronan(index) for index in range(8)],
        "spr_title_theo": [build_theo(index) for index in range(8)],
        "spr_title_bubble": [build_bubble(index) for index in range(3)],
        "spr_title_cloud": [build_cloud(index) for index in range(3)],
    }
    fps = {
        "spr_title_car": 15.0,
        "spr_title_wheel": 12.0,
        "spr_title_exhaust": 12.0,
        "spr_title_ronan": 8.0,
        "spr_title_theo": 8.0,
        "spr_title_bubble": 6.0,
        "spr_title_cloud": 0.0,
    }

    for name, frames in parts.items():
        path = save_strip(name, frames, fps[name], sprite_dir)
        used = set()
        for frame in frames:
            used |= palette_indices(frame)
        if len(used) > MAX_SPRITE_COLOURS:
            raise SystemExit("%s uses %d colours, the limit is %d" % (name, len(used), MAX_SPRITE_COLOURS))
        print("  %-20s %dx%d  %d frames  %2d colours  %s"
              % (name, frames[0].width, frames[0].height, len(frames), len(used), sha256(path)))

    preview_path = os.path.join(out_dir, "title_car_preview.png")
    build_preview(parts, preview_path)
    print("  %-20s %s" % ("title_car_preview", sha256(preview_path)))

    if args.dump:
        dump(parts["spr_title_car"][0], "car body frame 0")
        dump(parts["spr_title_ronan"][0], "ronan frame 0")
        dump(parts["spr_title_ronan"][6], "ronan frame 6, the glance")
        dump(parts["spr_title_theo"][0], "theo frame 0")
        dump(parts["spr_title_theo"][5], "theo frame 5, turning to speak")
    return 0


if __name__ == "__main__":
    sys.exit(main())
