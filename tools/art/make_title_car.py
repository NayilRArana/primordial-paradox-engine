#!/usr/bin/env python
"""TS-C: the title car, the cast busts and Zander's storm cloud.

Contract: TITLE-COORD.md in the project root and specs\\14-title-screen-drive.md
plus its night drive addendum. Everything here is original, clean room: no
reference to, copy of, or trace of any existing game's art.

What this writes (deterministic: no clock, no randomness, no window, no network):
  game\\sprites_src\\title\\spr_title_wheel.png    16x16 frame, 10x10 art, 4 frames (rotation)
  game\\sprites_src\\title\\spr_title_exhaust.png  16x16 frame, 12x10 art, 4 frames (puff)
  game\\sprites_src\\title\\spr_title_konrad.png   16x16 frame, 12x12 art, 8 frames (watch glance at 5 to 7)
  game\\sprites_src\\title\\spr_title_zander.png   16x16 frame, 12x12 art, 8 frames (4 idle bob, 4 turn to speak)
  game\\sprites_src\\title\\spr_title_bubble.png   16x16 frame, 14x10 art, 3 frames (one dot, two dots, three dots)
  game\\sprites_src\\title\\spr_title_cloud.png    24x16 frame, 24x12 art, 3 frames (2 normal, 1 flash)
  plus one JSON beside each: {"name", "frame_w", "frame_h", "frames", "fps"}

The frame sizes are multiples of 8 because a pattern table tile is 8x8: a 12x12 or 10x10 sheet cannot be cut
into whole tiles, which is the grid rule tools\\nes_check.py measures. The drawing is centred (or kept on its
documented row) inside the larger frame, so the art itself has not moved.

spr_title_car is not written here: tools/art/title_car_v2.py owns it.

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

The bust tiles are 12x12 and use all 12 rows: the head fills rows 0 to 7 (the window band, when the
tile is pasted at y 4, is rows 4 to 11 of the frame, so the face sits in the glass) and the shoulders
fill rows 8 to 11 below it. Konrad is the driver, in the front window on the right of the frame.
Zander is the passenger, in the rear window to his left, one pixel column further back.

PLACEMENT (the offsets the composer needs, relative to the car origin)

  body         spr_title_car      (0, 0)
  rear wheel   spr_title_wheel    (9, 22)
  front wheel  spr_title_wheel    (41, 22)
  exhaust      spr_title_exhaust  (0, 20)
  Zander       spr_title_zander   (14, 4)
  Konrad       spr_title_konrad   (31, 4)

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
SEA = 8            # #11485c  the dark blue of the passenger's lit side ($0C in the title scene)
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
#
# Two of these letters exist for the busts and are chosen the other way round: the letter names the
# 2C02 entry the finished art will carry, not the drawing palette, because a 12x12 bust has no room
# for a colour that enforcement will only move. "U" is $0C, the dark blue of scene_title sprite
# palette 2; "W" is already $10 light grey. Both sit in one palette, so the right half of a bust can
# be blue and pale without asking the scene for a colour it does not hold.
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
    "U": SEA,
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
    """Draw a block of legend rows, one character per pixel.

    A row wider than the tile is trimmed one column at a time from each side, which keeps a centred
    bust centred; a row narrower is padded with transparency on the right. The bust tiles are 12 wide
    and some of their rows were written for 14, and that mismatch used to stop the whole sheet.
    """
    for dy, row in enumerate(rows):
        if len(row) > image.width:
            excess = len(row) - image.width
            left = excess // 2
            row = row[left:left + image.width]
        row = row + " " * (image.width - len(row))
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
#
# Card t_474cde50 (gamedev). The puff is a TILED LAYER, not a figure: over one full scroll its 16x16 window
# sits on four ground colours that span 2C02 rows 0 to 2 ($0F black, $0B green, $0C teal, $20 white), and no
# single body entry clears RULE 0 point 2 on both ends. palette_synergy judges it by R1b overlay_contrast,
# which is why save_strip declares it. The four frames are drawn in tools/art/make_title_exhaust_v2.py so one
# file owns them; this generator asks that file for them in the entries the puff can actually ship.
#
# The body is $20 white and the outline $0C, not the $10 light grey the redraw was first drawn in: the puff
# sits in screen bands 12 to 13, which data/palettes/scene_title.json paints with bg3 ($0C $0B $20), and
# tools/art/title_bands.py flattens a $10 body to $20 on the way to the tree (measured: 118 pixels move).
# A generator that drew $10 and let the band pass recolour it would be drawing something the tree never ships.
# ---------------------------------------------------------------------------------------------------

EXHAUST_BODY = "#f8f8f8"     # $20 white, the puff's body, in bg3
EXHAUST_OUTLINE = "#004058"  # $0C dark teal, the 1 px outline, in bg3


def build_exhaust_frames() -> list[Image.Image]:
    """The four puff frames, growing 5x4 to 12x10, asked for in the entries bg3 carries."""
    import make_title_exhaust_v2 as exhaust
    return exhaust.build_frames(EXHAUST_BODY, EXHAUST_OUTLINE)


# ---------------------------------------------------------------------------------------------------
# The cast
#
# Each bust tile is 12x12. The art is 8 rows tall and sits in the lower 8 rows of the tile, so
# that when the tile is pasted at y 4 the face lands inside the window band, rows 8 to 15.
# ---------------------------------------------------------------------------------------------------

BUST_W, BUST_H = 12, 12
# The bust art fills its 12 rows: the head in rows 0 to 7, the shoulders in rows 8 to 11. BUST_TOP is
# where the tile sits inside the 16x16 shipping frame (FRAMES below), not where the drawing starts.
BUST_TOP = 4

# The frame every sprite ships in, and where its art sits inside that frame.
#
# A sprite sheet has to cut into whole 8x8 pattern tiles, so its PNG width and height must be multiples of 8;
# a 12x12 bust or a 10x10 wheel cannot. These frames are the smallest whole tiles that hold each drawing, and
# the offset is chosen so the drawing does not move on screen: the busts keep the row they were drawn for (the
# art sits at row 4, the face in the window band rows 8 to 15), the cloud keeps its top edge, and the parts that
# are drawn centred in their box (wheel, exhaust, bubble) stay centred.
FRAMES = {
    "spr_title_wheel": (16, 16, 3, 3),
    # spr_title_exhaust is NOT here: its four frames are hand drawn 16x16 cells in
    # tools/art/make_title_exhaust_v2.py and are already the shipping size and position (card t_474cde50).
    "spr_title_konrad": (16, 16, 2, BUST_TOP),
    "spr_title_zander": (16, 16, 2, BUST_TOP),
    "spr_title_bubble": (16, 16, 1, 3),
    "spr_title_cloud": (24, 16, 0, 0),
}


def fit_frame(image: Image.Image, name: str) -> Image.Image:
    """The drawing in the frame it ships in. Nothing is scaled and nothing is resampled."""
    width, height, x, y = FRAMES[name]
    out = new_image(width, height)
    out.alpha_composite(image, (x, y))
    return out

# ---------------------------------------------------------------------------------------------------
# The cast, in the costume CHARACTER-BIBLE gives them
#
# A 16x16 frame costs two 8x16 OAM sprites, one per 8 px column band, and each band may use three
# entries of one sprite palette (data/palettes/scene_title.json, rule in knowledge/ART-BIBLE.md 1).
# The art is 12 px wide at frame column 2, so art columns 0 to 5 fall in the left band and columns 6
# to 11 in the right one. Both busts are drawn so each band lands inside a palette with no pixel left
# over for the enforcement pass to move:
#
#   left band, frame columns 2 to 7    sp1: $0F black, $00 grey, $28 gold
#   right band, frame columns 8 to 13  sp2: $0C dark blue, $10 light grey
#
# Konrad is warm in both bands: grey-blond hair, a gold-lit face, a grey close beard and a charcoal
# blazer with a grey shirt and a lanyard. Zander's LIT band is the blue one, which is how the light
# blue bomber reaches a title scene whose four sprite palettes hold no skin tone and no second blue:
# his jacket's lit half is $10 light grey against $0C dark blue, and the pale hair on that side is
# the headlight. The cost of that budget is stated in SPRITE-CRITIQUE 3.8: a 12 px face in three
# colours cannot carry a blond and a light blue in the same 8x16 band, so the blond is on the shaded
# half and the blue on the lit half, the way a NES sprite splits a two-palette figure.

# The driver, Konrad Skye, 47, AI research scientist. CHARACTER-BIBLE: long blond hair streaked
# white and grey, a close beard, a charcoal blazer or dark knit over an open collar shirt, an ID
# lanyard, a wristwatch, no cap. Rows 0 to 7 are the head and fill the window band; rows 8 to 11 are
# the shoulders, which sit below the sill the way a seated driver does.
KONRAD_ROWS = [
    "   DYYYYD   ",   # the crown of the hair, blond with the grey of the streaks at the temples
    "  YYYYYYYY  ",   # the hair
    " DYYYYYYYYD ",   # the long hair flaring out, the grey edge that reads on black glass
    " DYKKKKKKYD ",   # the hairline across the forehead
    "  YYYYYYYY  ",   # the face
    "  YKKYYKKY  ",   # the eyes, 2 px each with a 2 px bridge
    "  YYYYKYYY  ",   # the nose
    "  DDDKKDDD  ",   # the mouth, in the close grey beard
    " DKKDYYDKKD ",   # the neck, the shirt collar, the charcoal blazer
    " DKDDYYDDKD ",   # the open collar V
    " DKKDYDDYKK ",   # the lanyard strap, two strands
    " DKKDDYYDDK ",   # the ID badge on the lanyard
]

# The passenger, Zander Skye, 19, first year student. CHARACTER-BIBLE: messy blond hair, an oversized
# bomber in LIGHT BLUE (not green), earbuds. Left band warm (gold hair, gold face, black edge), right
# band pale and blue: light grey hair and face, dark blue hairline and jacket shadow, which is the
# lit side of the bomber. The earbud is the one light pixel at the ear; at 12 px it is a dot and
# nothing more.
ZANDER_ROWS = [
    "   YYYWWW   ",   # the messy hair, tufts
    "  YYYYWWWW  ",   # the hair, blond on the shaded band and pale under the headlight
    " DYYYYWWWWD ",   # the hair falling past the ear
    " DYKKKUUUUD ",   # the hairline, black on the shaded band and dark blue on the lit one
    "  YYYYWWWW  ",   # the forehead
    "  YKKSUUWW  ",   # the eyes
    "  YYYYKWWW  ",   # the mouth, closed until the turn
    "  DDKKUUDD  ",   # the jaw
    " DDYYYWWWDD ",   # the neck and the bomber collar
    " DDKKWWWWDD ",   # the shoulders
    " DDKDDWUWWD ",   # the jacket and its zip
    " DDDKKWUWWD ",   # the hem
]


def bust_rows(rows: list[str]) -> list[str]:
    """Assert the drawing is exactly BUST_W wide, rather than trimming it silently.

    stamp_rows pads and trims a row that does not fit, which is right for the car and wrong for a
    face: a row of 14 used to be cut from both sides and lose the eye on the edge. A bust row is
    written to the tile width or the sheet stops.
    """
    for index, row in enumerate(rows):
        if len(row) != BUST_W:
            raise SystemExit("%d characters on bust row %d, the tile is %d wide: %r"
                             % (len(row), index, BUST_W, row))
    return rows


def shifted(image: Image.Image) -> Image.Image:
    """The same drawing one pixel down: the idle bob, and the only movement Konrad needs at rest."""
    return shift_down(image, 1)


def build_konrad(frame: int) -> Image.Image:
    """Konrad Skye, the driver, in the costume CHARACTER-BIBLE gives him (see KONRAD_ROWS).

    Frames 0 to 4 are the drive: the head bobs one pixel on the off beat, and on frame 4 his eyes
    come round to the road. Frames 5 to 7 are the glance at the wristwatch: the eyes move right, the
    forearm comes up one pixel a frame and the grey watch face sits on the wrist. Checking the watch
    is Konrad's tell in CHARACTER-BIBLE, and it is the reason the role was decidable at all.
    """
    rows = [list(row) for row in bust_rows(KONRAD_ROWS)]
    image = new_image(BUST_W, BUST_H)
    if frame in (1, 3):
        # The bob. Drawn first, because the watch and the eyes are placed on the raised head.
        stamp_rows(image, 0, ["".join(row) for row in rows])
        return shifted(image)
    if frame >= 4:
        # The eyes come round, one pixel to the right: row 5 carries them at 3,4 and 7,8, and they
        # move to 4,5 and 8,9.
        rows[5][3] = "S"
        rows[5][5] = "K"
        rows[5][7] = "S"
        rows[5][9] = "K"
    if frame >= 5:
        # The forearm comes up the right edge of the blazer, one row a frame, the watch on the wrist.
        hand = {5: 10, 6: 9, 7: 8}[frame]
        rows[hand][9] = "S"
        rows[hand][10] = "W"
        for below in range(hand + 1, 12):
            rows[below][9] = "K"
            if below != hand + 1:
                rows[below][10] = "K"
    stamp_rows(image, 0, ["".join(row) for row in rows])
    return image


def build_zander(frame: int) -> Image.Image:
    """Zander Skye, the passenger, in the costume CHARACTER-BIBLE gives him (see ZANDER_ROWS).

    Frames 0 to 3 are the idle, the head bobbing on the off beat. Frames 4 to 7 are the turn to
    speak: the head comes round towards the driver, who is to his right, and the mouth opens a row
    at a time, so the "..." bubble lands on a mouth that is already open.
    """
    rows = [list(row) for row in bust_rows(ZANDER_ROWS)]
    image = new_image(BUST_W, BUST_H)
    if frame in (1, 3):
        stamp_rows(image, 0, ["".join(row) for row in rows])
        return shifted(image)
    if frame >= 4:
        turn = frame - 4
        # The head comes round towards the driver, on the right of the frame.
        for index in range(0, 8):
            rows[index] = ["."] + rows[index][:-1]
        if turn >= 1:
            # The mouth opens under the nose, the left half of it in the black of the shaded band and
            # the right half in the dark blue of the lit one.
            rows[6][5] = "K"
            rows[6][6] = "U"
        if turn >= 2:
            # The near eye comes round with the head. The head has already slid one column right, so the
            # pair sits at 4,5 and moves to 5,6.
            rows[5][4] = "S"
            rows[5][6] = "K"
        if turn >= 3:
            # The far eye follows it and the mouth widens into the word.
            rows[5][7] = "W"
            rows[5][9] = "U"
            rows[6][7] = "U"
    stamp_rows(image, 0, ["".join(row) for row in rows])
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

# Zander's storm cloud, hand authored on a grid of legend characters (card t_b08c01d5 AUTO-SPRITE-NEXT).
#
# Why only two entries are drawn here, measured and not chosen: the cloud is one of the sheets
# data/palettes/scene_title.json band-paints ("spr_title_cloud": "bg1"), so tools/art/title_bands.py
# rewrites every pixel it draws into the nearest colour of that band's background palette, which is
# $11 sky, $00 grey and $20 white. Any third entry is destroyed by that pass, not by this drawing: a
# lit cap drawn in $10 lands on $20 only because it is pale enough, and every dark under it (the $0F
# ink or the $28 gold the queue's palette_roles list) lands on $00 grey. The row's answer to the
# EYE's "cannot carry the outline RULE 0 asks for" is therefore a question for gamedev, posted in the
# queue row, and the drawing here is the strongest cloud two entries can carry: a white lit mass over
# a grey storm underside, the boundary dithered rather than a flat edge, and the flash frame inverting
# the mass so the bolt reads white against it instead of white on white.
#
# W is BRIGHT (#c8c8d4), which the band pass resolves to $20 white; G is DIM (#7a7a88), which it
# resolves to $00 grey. The frames differ slightly (a lump grows, the base puffs shift) so the two
# normal frames churn instead of repeating, and the third frame is the flash.
CLOUD_ROWS = [
    [
        "........WWWWW...........",   # the crown, centred over the mass
        ".....WWWWWWWWWW.........",   # the crown widens
        "...WWWWWWWWWWWWW........",   # the shoulders
        "..WWWWWWWWWWWWWWWWW.....",
        "WWWWWWWWWWWWWWWWWWWW....",   # the full width, lit on top
        "WWWWWWWWWWWWWWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWWGGG..",   # the right shoulder falls into shade
        "WWWGWWWGWWWGWWWGWWGGGG..",   # the dithered underside boundary
        "GGGGGGGGGGGGGGGGGGGGGG..",   # the storm base
        ".GGGGGGGGGGGGGGGGGGGG...",
        "..GGGGG....GGGGGGGGG....",   # the base puffs, ragged at the bottom
    ],
    [
        "........WWWWWW..........",   # the crown leans right as the cloud churns
        ".....WWWWWWWWWWW........",
        "...WWWWWWWWWWWWWW.......",
        "..WWWWWWWWWWWWWWWWW.....",
        "WWWWWWWWWWWWWWWWWWWW....",
        "WWWWWWWWWWWWWWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWWGGG..",
        "WWWGWWWGWWWGWWWGWWGGGG..",
        "GGGGGGGGGGGGGGGGGGGGGG..",
        ".GGGGGGGGGGGGGGGGGGGG...",
        "...GGGGGG....GGGGGGGG...",   # the puffs have shifted
    ],
    [
        "........WWWWW...........",   # the flash: the crown stays lit
        ".....WWWWWWWWWW.........",
        "...WGGGGGGGGGGGW........",   # the mass turns over, so the bolt can read
        "..WGGGGGGGGGGGGGGW......",
        "WWGGGGGGGGGGGGGGGGWW....",
        "WGGGGGGGWGGGGGGGGGGWW...",   # the bolt starts at the crown of the mass
        "WGGGGGGWGGGGGGGGGGGGW...",
        "WGGGGGWGGGGGGGGGGGGWW...",
        "GGGGGWGGGGGGGGGGGGGWG...",
        "GGGGWGGGGGGGGGGGGGGGG...",
        ".GGGWGGGGGGGGGGGGGGG....",
        "..GGWGG....GGGGGGGGG....",
        "...W....................",   # the bolt runs out of the cloud
        "..W.....................",
    ],
]


def build_cloud(frame: int) -> Image.Image:
    """Zander's storm cloud. The third frame is the flash, with the mass turned over and a bolt through it."""
    image = new_image(CLOUD_W, CLOUD_H + 2)
    stamp_rows(image, 0, CLOUD_ROWS[frame])
    return image


# ---------------------------------------------------------------------------------------------------
# Writing the strips
# ---------------------------------------------------------------------------------------------------

# Sheets the art lane declares TILED LAYERS rather than figures, so their sidecar says so and palette_synergy
# reads them through R1b overlay_contrast instead of the row gap and the blob test (gamedev rulings on card
# t_1dc346b9 for the cloud and card t_474cde50 for the exhaust). A regeneration has to carry the declaration or
# the next run silently turns a layer back into a figure.
LAYER_SHEETS = ("spr_title_cloud", "spr_title_exhaust")

# Sheets drawn in data/nes_palette.json's 2C02 entries rather than the retired data/palette.json table the
# rest of this generator draws in. Only the exhaust so far (card t_474cde50): its four cells are shared with
# tools/art/make_title_exhaust_v2.py, which is a 2C02 tool. The scene pass is a no-op on these entries because
# both of them are bg3's, so nothing the band plan owns moves.
CHIP_DRAWN_SHEETS = ("spr_title_exhaust",)


def save_strip(name: str, frames: list[Image.Image], fps: float, sprite_dir: str) -> str:
    width = frames[0].width
    height = frames[0].height
    strip = new_image(width * len(frames), height)
    for index, frame in enumerate(frames):
        strip.alpha_composite(frame, (index * width, 0))
    png_path = os.path.join(sprite_dir, name + ".png")
    strip.save(png_path, "PNG")
    meta = {"name": name, "frame_w": width, "frame_h": height, "frames": len(frames), "fps": fps}
    # Card t_1dc346b9 ruling: the cloud is a sky-band backdrop element, not a figure with feet, so it declares
    # itself a tiled layer and palette_synergy judges it by R1b overlay_contrast on its own ground crop.
    # save_strip must carry that declaration or a regeneration silently drops it (cf3d43a made a 24x16 frame
    # a figure, and the white crown then reads white_blob against the 5 white px in the sky crop).
    # Card t_474cde50 ruling: the exhaust is the same object class. Its 16x16 window crosses four ground
    # colours over one scroll ($0F, $0B, $0C, $20), so RULE 0 point 2's row gap and body contrast cannot be
    # satisfied by any single body entry and the row could never pass as a figure; R1b reads it correctly.
    if name in LAYER_SHEETS:
        meta["layer"] = True
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
    scene.alpha_composite(parts["spr_title_zander"][0], (34, 16))
    scene.alpha_composite(parts["spr_title_konrad"][0], (51, 16))

    blocks = [("THE ASSEMBLED CAR ON THE ROAD", scene, scale)]
    for label, name in [("CAR BODY 64X32 3 FRAMES 1 PX BOB", "spr_title_car"),
                        ("WHEEL 16X16 FRAME, 10X10 ART, 4 FRAMES", "spr_title_wheel"),
                        ("EXHAUST 16X16 FRAME, 12X10 ART, 4 FRAMES", "spr_title_exhaust"),
                        ("KONRAD 16X16 FRAME, 12X12 ART, 8 FRAMES WATCH GLANCE AT 5 TO 7", "spr_title_konrad"),
                        ("ZANDER 16X16 FRAME, 12X12 ART, 8 FRAMES 4 IDLE 4 TURN", "spr_title_zander"),
                        ("SPEECH BUBBLE 16X16 FRAME, 14X10 ART, 3 FRAMES", "spr_title_bubble"),
                        ("STORM CLOUD 24X16 FRAME, 24X12 ART, 2 FRAMES AND A FLASH", "spr_title_cloud")]:
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
    parser.add_argument("--no-scene-pass", action="store_true",
                        help="draw only; skip the scene palette pass at the end (used when a whole art pass is "
                             "being redrawn and the scene is solved once at the end)")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    sprite_dir = os.path.join(root, "game", "sprites_src", "title")
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(root, "output")
    os.makedirs(sprite_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    parts = {
        "spr_title_car": [build_car_body(bob) for bob in (0, 1, 0)],
        "spr_title_wheel": [build_wheel(index) for index in range(4)],
        "spr_title_exhaust": build_exhaust_frames(),
        "spr_title_konrad": [build_konrad(index) for index in range(8)],
        "spr_title_zander": [build_zander(index) for index in range(8)],
        "spr_title_bubble": [build_bubble(index) for index in range(3)],
        "spr_title_cloud": [build_cloud(index) for index in range(3)],
    }
    # A sheet must cut into whole 8x8 tiles, so every part is fitted to its shipping frame before it is written.
    for name in FRAMES:
        parts[name] = [fit_frame(frame, name) for frame in parts[name]]
    fps = {
        "spr_title_car": 15.0,
        "spr_title_wheel": 12.0,
        "spr_title_exhaust": 12.0,
        "spr_title_konrad": 8.0,
        "spr_title_zander": 8.0,
        "spr_title_bubble": 6.0,
        "spr_title_cloud": 0.0,
    }
    # spr_title_car is NOT written here any more: tools/art/title_car_v2.py owns that file (the TS2-ART-A car,
    # wheels baked in, 64x32, three frames). This file keeps its body drawing for the contact sheet only, so
    # running it can no longer put the v1 car back over the v2 one.
    written = [name for name in parts if name != "spr_title_car"]

    for name in written:
        frames = parts[name]
        path = save_strip(name, frames, fps[name], sprite_dir)
        used = set()
        for frame in frames:
            if name in CHIP_DRAWN_SHEETS:
                # This sheet is drawn in data/nes_palette.json's 2C02 entries, not in the retired
                # data/palette.json table the rest of this file draws in, so the count is of the colours
                # the sheet actually spends and tools/nes_check.py is what proves they are chip entries.
                used |= {(pixel[0], pixel[1], pixel[2]) for pixel in frame.getdata() if pixel[3]}
            else:
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
        dump(parts["spr_title_konrad"][0], "konrad frame 0")
        dump(parts["spr_title_konrad"][6], "konrad frame 6, the glance")
        dump(parts["spr_title_zander"][0], "zander frame 0")
        dump(parts["spr_title_zander"][5], "zander frame 5, turning to speak")
    # The scene palette pass: every sprite tile is rewritten into one sprite palette of three entries
    # plus transparency, from data/palettes/scene_title.json. Different tiles of one object may use
    # different palettes, which is how a NES character gets more than three colours (a face sprite
    # over a body sprite in its own palette), so the car keeps a body palette and a lights palette.
    if not args.no_scene_pass:
        import scene_palette
        scene_palette.apply_title(args.root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
