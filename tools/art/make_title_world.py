#!/usr/bin/env python
"""TS-B: the night title world for "The Drive to Southampton".

Contract: TITLE-COORD.md in the project root and specs\\14-title-screen-drive.md
plus its night drive addendum. Everything here is original, clean room: no
reference to, copy of, or trace of any existing game's art, and nothing outside
this repository is read except the font sprite this project already owns.

What this writes (all deterministic, no windows, no network):
  game\\sprites_src\\title\\title_L1_sky.png     512x120, 2 frames (star twinkle variant)
  game\\sprites_src\\title\\title_L2_clouds.png  512x120, 1 frame
  game\\sprites_src\\title\\title_L3_downs.png   512x48,  1 frame
  game\\sprites_src\\title\\title_L4_fields.png  512x56,  1 frame
  game\\sprites_src\\title\\title_L5_verge.png   512x92,  1 frame
  game\\sprites_src\\title\\title_L6_road.png    512x44,  1 frame
  game\\sprites_src\\title\\title_L7_fg.png      512x44,  1 frame
  game\\sprites_src\\title\\spr_title_sign.png   89x16,  4 frames (SOUTHAMPTON 74/52/31/9)
  game\\sprites_src\\title\\spr_title_cone.png   90x40,  1 frame (headlight cone overlay)
  plus one JSON beside each: {"name", "frame_w", "frame_h", "frames", "fps"}

Review sheets and preview:
  output\\title_world_preview.png    composed 256x240 night frame at 3x (768x720)
  output\\title_world_scroll.png     the same frame at another camera x
  output\\title_world_contact.png    every layer at 1x, labelled
  output\\title_world_seams.png      every layer tiled twice at 1x, seam marked
  output\\title_world_manifest.json  size, sha256 and colour count per file

COMPOSE TABLE (screen y for the 256x240 frame, and the scroll speeds fixed by
TITLE-COORD). Each layer owns a horizontal band, so nothing hides behind the
layer in front of it:
  L1 sky     y=0    512x120  speed 0.00   banded night sky, 2 star depths, moon
  L2 clouds  y=0    512x120  speed 0.05   thin night cloud bands, transparent
  L3 downs   y=92   512x48   speed 0.15   far chalk downs, chalk horse, church spire
  L4 fields  y=128  512x56   speed 0.35   patchwork fields, oaks, lit farmhouse
  L5 verge   y=120  512x92   speed 0.70   hedge, dry stone wall, poles, phone box, sign
  L6 road    y=196  512x44   speed 1.00   two lane road, dashed centre line
  L7 fg      y=196  512x44   speed 1.30   foreground grass and fence posts
The car sits at screen x 76..140, so the headlight cone overlay belongs at
x 140..230. The cone is a separate sprite, not baked into the road tile: the
road scrolls at 1.0x, so a cone inside the 512 px tile would repeat every
512 px. The game draws spr_title_cone at the car x every frame.

Depth is carried by value, not by hue alone, so the road reads at a glance:
the far downs are the darkest and the bluest band, the mid fields are dark
green, the hedge sits one step brighter, the near verge grass is the
brightest thing in the scene, the road is dark asphalt, and the foreground
is a near black silhouette.

Palette: every pixel of every file is a master palette entry from
data\\palette.json, and the whole title room uses 16 colours, the limit in
spec 13 and TITLE-COORD. The colour list is the one below and nothing else may
enter a file.
"""

import hashlib
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PALETTE_PATH = ROOT / "data" / "palette.json"
SPRITE_DIR = ROOT / "game" / "sprites_src" / "title"
OUT_DIR = ROOT / "output"
FONT_PATH = SPRITE_DIR / "spr_pp_font8.png"

W = 512
SCREEN_W = 256
SCREEN_H = 240
TRANSPARENT = 255

# Palette indices. The title room budget is 16 colours for the whole scene, so
# these 16 are the whole budget for the layers, the sign and the cone.
INK = 0             # #0b0b0f  outlines, silhouettes, road grain
ASPHALT = 1         # #1c1c24  road surface
STAR_DIM = 4        # #7a7a88  dim stars, moonlit crests, cone dither
STAR_BRIGHT = 5     # #c8c8d4  moon, chalk horse, sign text
SKY_NAVY = 6        # #081420  sky band 2 and the far chalk downs
SKY_BLUE = 7        # #0d2b3a  sky band 3
SKY_HORIZON = 8     # #11485c  sky band 4, the low sky above the downs
SKY_ZENITH = 42     # #0a0614  sky band 1, night cloud bodies
RED = 22            # #b33a52  the red phone box
GREEN_DEEP = 25     # #232a12  field floor, hedge shadow
GREEN_MID = 26      # #3a4420  hedge mass
GREEN_LIGHT = 27    # #55632f  lit field patches, hedge crest
GREEN_PALE = 29     # #adbc74  the nearest verge grass, lit by the headlights
STONE_DEEP = 30     # #14110f  church spire, roofs, poles, tree trunks
STONE_DARK = 31     # #262019  wall block shadow
STONE_MID = 32      # #3b3226  wall blocks, farmhouse walls
GOLD = 41           # #e8c65a  lit farmhouse and church windows

SCENE_COLOURS = [INK, ASPHALT, STAR_DIM, STAR_BRIGHT, SKY_NAVY, SKY_BLUE,
                 SKY_HORIZON, SKY_ZENITH, RED, GREEN_DEEP, GREEN_MID,
                 GREEN_LIGHT, GREEN_PALE, STONE_DEEP, STONE_MID, GOLD]

# The font sprite, when this project has one, is the only letterform source
# used for the sign. Its cell order is ASCII over the 44 glyphs it owns.
FONT_ORDER = " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Fallback 5x7 glyphs, used only when spr_pp_font8.png is absent. '#' is ink.
FALLBACK_FONT = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
    ",": [".....", ".....", ".....", ".....", ".....", "..#..", ".#..."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", "..#..", "..#.."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    ":": [".....", "..#..", ".....", ".....", ".....", "..#..", "....."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
}

GLYPH_W = 5
GLYPH_H = 7
GLYPH_GAP = 1


def load_palette():
    data = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
    rgb = []
    for entry in data["colours"]:
        value = entry.lstrip("#")
        rgb.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
    return rgb


PALETTE = load_palette()


def text_width(text, advance=GLYPH_W + GLYPH_GAP):
    if not text:
        return 0
    return len(text) * advance - GLYPH_GAP


def load_glyphs():
    """Return {character: 7 rows of 5 booleans}.

    The font sprite wins when it exists, because then the sign and the menu use
    one letterform set. The sprite stores one 8x8 cell per glyph in ASCII order;
    the glyph ink sits at cell column 1, row 0.
    """
    if FONT_PATH.is_file():
        image = Image.open(FONT_PATH).convert("RGBA")
        pixels = image.load()
        width, height = image.size
        cell = 8
        if width == len(FONT_ORDER) * cell and height == cell:
            glyphs = {}
            for index, character in enumerate(FONT_ORDER):
                rows = []
                for y in range(GLYPH_H):
                    row = []
                    for x in range(GLYPH_W):
                        alpha = pixels[index * cell + 1 + x, y][3]
                        row.append(alpha > 0)
                    rows.append(row)
                glyphs[character] = rows
            return glyphs, "spr_pp_font8.png"
    glyphs = {}
    for character, rows in FALLBACK_FONT.items():
        glyphs[character] = [[cell == "#" for cell in row] for row in rows]
    return glyphs, "built in 5x7 fallback"


GLYPHS, FONT_SOURCE = load_glyphs()


class Tile:
    """Index grid. x wraps at the tile width so every drawing call is seamless."""

    def __init__(self, width, height, fill=TRANSPARENT):
        self.w = width
        self.h = height
        self.px = bytearray([fill]) * (width * height)

    def put(self, x, y, colour):
        if 0 <= y < self.h:
            self.px[y * self.w + (x % self.w)] = colour

    def get(self, x, y):
        if 0 <= y < self.h:
            return self.px[y * self.w + (x % self.w)]
        return TRANSPARENT

    def rect(self, x0, y0, x1, y1, colour):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, colour)

    def hline(self, x0, x1, y, colour):
        for x in range(x0, x1 + 1):
            self.put(x, y, colour)

    def column(self, x, y0, y1, colour):
        for y in range(y0, y1 + 1):
            self.put(x, y, colour)

    def band(self, y0, y1, colour):
        for y in range(y0, y1 + 1):
            for x in range(self.w):
                self.px[y * self.w + x] = colour

    def disc(self, cx, cy, radius, colour):
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    self.put(x, y, colour)

    def poly(self, points, colour):
        ys = [p[1] for p in points]
        top = int(math.floor(min(ys)))
        bottom = int(math.ceil(max(ys)))
        count = len(points)
        for y in range(top, bottom + 1):
            crossings = []
            for i in range(count):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % count]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y < max(y1, y2):
                    t = (y - y1) / float(y2 - y1)
                    crossings.append(x1 + t * (x2 - x1))
            crossings.sort()
            for i in range(0, len(crossings) - 1, 2):
                xa = int(math.floor(crossings[i]))
                xb = int(math.ceil(crossings[i + 1]))
                for x in range(xa, xb + 1):
                    self.put(x, y, colour)

    def text(self, x, y, msg, colour):
        cursor = x
        for character in msg.upper():
            glyph = GLYPHS.get(character)
            if glyph is None:
                cursor += GLYPH_W + GLYPH_GAP
                continue
            for ry in range(GLYPH_H):
                for rx in range(GLYPH_W):
                    if glyph[ry][rx]:
                        self.put(cursor + rx, y + ry, colour)
            cursor += GLYPH_W + GLYPH_GAP
        return cursor

    def paste(self, source, x, y):
        """Copy another tile onto this one, wrapping x like every other call."""
        for sy in range(source.h):
            for sx in range(source.w):
                self.put(x + sx, y + sy, source.get(sx, sy))

    def patch(self, x, y, rows, mapping):
        for ry, row in enumerate(rows):
            for rx, character in enumerate(row):
                colour = mapping.get(character)
                if colour is not None:
                    self.put(x + rx, y + ry, colour)

    def image(self):
        buf = bytearray(self.w * self.h * 4)
        i = 0
        for value in self.px:
            if value == TRANSPARENT:
                i += 4
                continue
            r, g, b = PALETTE[value]
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
            buf[i + 3] = 255
            i += 4
        return Image.frombytes("RGBA", (self.w, self.h), bytes(buf))

    def colours_used(self):
        return sorted(set(v for v in self.px if v != TRANSPARENT))


# ---------------------------------------------------------------- sky (L1)

SKY_BANDS = [
    (0, 24, SKY_ZENITH),
    (25, 54, SKY_NAVY),
    (55, 84, SKY_BLUE),
    (85, 119, SKY_HORIZON),
]


def sky_band_colour(y):
    for y0, y1, colour in SKY_BANDS:
        if y0 <= y <= y1:
            return colour
    return SKY_BANDS[-1][2]


def build_sky():
    """Banded night sky with two star depths, a moon, and a twinkle frame.

    The sky never scrolls, so the moon lives in the columns the frame can
    actually show: 0..255 of a 512 px tile. The right half carries only
    stars, so nothing important is ever hidden.
    """
    tile = Tile(W, 120)
    for y0, y1, colour in SKY_BANDS:
        tile.band(y0, y1, colour)

    # 25 percent dither teeth either side of each band edge. No blends.
    for index in range(1, len(SKY_BANDS)):
        edge = SKY_BANDS[index][0]
        lighter = SKY_BANDS[index][2]
        darker = SKY_BANDS[index - 1][2]
        for dy in range(1, 5):
            y = edge - dy
            for x in range(W):
                if ((x >> 1) + (y >> 1)) % 4 == 0:
                    tile.put(x, y, lighter)
        for dy in range(0, 3):
            y = edge + dy
            for x in range(W):
                if ((x >> 1) + (y >> 1)) % 4 == 1:
                    tile.put(x, y, darker)

    # Two star depths. The far depth is a single dim pixel, the near depth is
    # a bright pixel, some of them drawn as a small cross.
    rng = random.Random(1101)
    for _ in range(150):
        x = rng.randrange(W)
        # Two thirds of the stars sit in the columns the frame shows.
        if rng.random() < 0.66:
            x = rng.randrange(256)
        y = rng.randrange(4, 92)
        tile.put(x, y, STAR_DIM)

    rng = random.Random(2202)
    twinklers = []
    for _ in range(54):
        x = rng.randrange(256) if rng.random() < 0.66 else rng.randrange(W)
        y = rng.randrange(4, 80)
        colour = STAR_BRIGHT if rng.random() < 0.45 else STAR_DIM
        tile.put(x, y, colour)
        if rng.random() < 0.3:
            tile.put(x - 1, y, colour)
            tile.put(x + 1, y, colour)
            tile.put(x, y - 1, colour)
            tile.put(x, y + 1, colour)
        twinklers.append((x, y))

    # Keep the stars off the moon disc. This runs before the moon is drawn, so
    # the clearing pass cannot wipe the moon itself.
    moon_cx, moon_cy, moon_r = 176, 34, 12
    for y in range(moon_cy - moon_r - 2, moon_cy + moon_r + 3):
        for x in range(moon_cx - moon_r - 2, moon_cx + moon_r + 3):
            if (x - moon_cx) ** 2 + (y - moon_cy) ** 2 <= (moon_r + 1) ** 2:
                if tile.get(x, y) in (STAR_DIM, STAR_BRIGHT):
                    tile.put(x, y, sky_band_colour(y))

    # The moon, at x 164..188 and y 22..46, so it is plain at 1x.
    tile.disc(moon_cx, moon_cy, moon_r, STAR_BRIGHT)
    for dx, dy, radius in ((4, -3, 3), (-3, 2, 2), (1, 5, 2)):
        tile.disc(moon_cx + dx, moon_cy + dy, radius, STAR_DIM)
    for y in range(moon_cy - moon_r, moon_cy + moon_r + 1):
        for x in range(moon_cx, moon_cx + moon_r + 1):
            if (x - moon_cx) ** 2 + (y - moon_cy) ** 2 > (moon_r - 2) ** 2:
                if (x - moon_cx) ** 2 + (y - moon_cy) ** 2 <= moon_r * moon_r:
                    tile.put(x, y, STAR_DIM)
    # A dark bite out of the lower left rim, so the moon is a crescent lit
    # from the upper right and reads as a shape rather than a pale blob.
    for y in range(moon_cy - moon_r + 3, moon_cy + moon_r - 1):
        for x in range(moon_cx - moon_r + 3, moon_cx):
            if (x - moon_cx) ** 2 + (y - moon_cy) ** 2 <= (moon_r - 3) ** 2:
                tile.put(x, y, sky_band_colour(y))

    # Frame 1 is the twinkle: a deterministic subset of the near stars change
    # level. The moon does not move.
    frame_one = Tile(W, 120)
    frame_one.px[:] = tile.px
    for index, (x, y) in enumerate(twinklers):
        current = frame_one.get(x, y)
        if current == STAR_BRIGHT:
            new = STAR_DIM
        elif index % 3 == 0:
            new = STAR_DIM
        else:
            new = STAR_BRIGHT
        frame_one.put(x, y, new)
        if index % 4 == 0:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if frame_one.get(x + dx, y + dy) == STAR_DIM:
                    frame_one.put(x + dx, y + dy, sky_band_colour(y + dy))
    return [tile, frame_one]


# ------------------------------------------------------------- clouds (L2)

def build_clouds():
    """Thin night cloud bands. Every cloud sits fully inside the tile, and the
    moon keeps its own sky clear, so the tile repeats without cutting a cloud
    on the wrap edge."""
    tile = Tile(W, 120)
    clouds = [
        (56, 20, 46, 6),
        (150, 62, 40, 5),
        (232, 16, 58, 7),
        (330, 70, 44, 5),
        (398, 30, 50, 6),
        (470, 66, 38, 5),
    ]
    for cx, cy, half, thick in clouds:
        for step in range(-half, half + 1):
            frac = 1.0 - abs(step) / float(half)
            height = int(round(thick * math.sqrt(max(0.0, frac))))
            if height <= 0:
                continue
            x = cx + step
            for dy in range(height):
                y = cy - height // 2 + dy
                tile.put(x, y, SKY_ZENITH)
            tile.put(x, cy - height // 2, SKY_NAVY)
            if step % 7 == 0:
                tile.put(x, cy - height // 2 - 1, STAR_DIM)
            tile.put(x, cy + height // 2, SKY_NAVY)
    return [tile]


# -------------------------------------------------------------- downs (L3)

CHALK_HORSE = [
    "            ###   ",
    "           ## #   ",
    "          ##  ##  ",
    "  #####  ##      ",
    " ###########      ",
    "############      ",
    "###########  #    ",
    " ####  ####       ",
    "  ##    ##       ",
    " ##      ##      ",
    "###       ##     ",
]


def build_downs():
    """The far chalk downs, with the white chalk horse and the church spire.

    The whole layer is 48 px tall and it is drawn at screen y 92, so the ridge
    line sits at screen y 100..110 and the horse and the spire both stand
    clear of the field band that starts at y 128.
    """
    tile = Tile(W, 48)

    def ridge(x):
        return 14 + 3 * math.sin(2.0 * math.pi * x / float(W)) \
                 + 2 * math.sin(2.0 * math.pi * 2 * x / float(W) + 1.1)

    tops = [int(round(ridge(x))) for x in range(W)]
    for x in range(W):
        tile.column(x, tops[x], 47, SKY_NAVY)
        # Moonlit crest line along the skyline.
        tile.put(x, tops[x], STAR_DIM)
        if x % 3 == 0:
            tile.put(x, tops[x] - 1, SKY_BLUE)
        # A darker blue toward the foot of the down, so the far layer is
        # clearly the darkest and the bluest band in the scene.
        if tops[x] + 12 < 47:
            tile.put(x, tops[x] + 12, SKY_ZENITH)
        if tops[x] + 24 < 47:
            tile.put(x, tops[x] + 24, SKY_ZENITH)

    # The white chalk horse, cut into the face of the down, at x 148..162.
    horse_x = 148
    horse_top = max(tops[horse_x + column] for column in range(15)) + 1
    tile.patch(horse_x, horse_top, CHALK_HORSE, {"#": STAR_BRIGHT, " ": None})
    for column in range(15):
        x = horse_x + column
        for y in range(horse_top, 47):
            if tile.get(x, y) == STAR_BRIGHT:
                tile.put(x, y + 1, STAR_DIM)
                break

    # The church spire, at x 58..70, standing against the low sky. It is
    # drawn in mid stone with a dark edge so it reads against the dark sky.
    spire_x = 58
    base = max(tops[spire_x + column] for column in range(13)) + 1
    tile.rect(spire_x + 3, base - 9, spire_x + 9, base + 3, STONE_MID)
    tile.poly([(spire_x + 2, base - 9), (spire_x + 10, base - 9),
               (spire_x + 6, base - 20)], STONE_MID)
    tile.put(spire_x + 6, base - 21, STONE_MID)
    tile.put(spire_x + 6, base - 22, STONE_MID)
    # A lit church window, so the spire reads at 1x, and a moonlit edge.
    tile.rect(spire_x + 5, base - 5, spire_x + 6, base - 3, GOLD)
    for y in range(base - 9, base + 4):
        tile.put(spire_x + 9, y, STONE_DEEP)
    for y in range(base - 20, base - 9):
        tile.put(spire_x + 2, y, STONE_DEEP)
    # The nave under the spire, so it reads as a church and not a post.
    tile.rect(spire_x - 4, base - 3, spire_x + 1, base + 3, STONE_MID)
    tile.rect(spire_x - 5, base - 4, spire_x + 1, base - 3, STONE_DEEP)
    return [tile]


# ------------------------------------------------------------- fields (L4)

FIELD_BOUNDARIES = [0, 46, 92, 138, 184, 230, 276, 322, 368, 414, 460, 512]
FIELD_COLOURS = [GREEN_LIGHT, GREEN_MID, GREEN_DEEP, GREEN_LIGHT, GREEN_MID,
                 GREEN_DEEP, GREEN_LIGHT, GREEN_MID, GREEN_DEEP, GREEN_LIGHT,
                 GREEN_MID]
FIELD_OFFSETS = [0, 3, 6, 2, 5, 8, 1, 4, 7, 9, 3]


def field_top(x, index):
    """Top edge of field shape `index` at column x.

    Each parcel gets its own phase and its own two harmonics, so no two
    tops run parallel and the band reads as a patchwork of fields rather
    than a row of flat slabs. The wave is periodic in 512, so the wrap edge
    looks like any other boundary.
    """
    offset = FIELD_OFFSETS[index % len(FIELD_OFFSETS)]
    phase = 0.7 * index
    wave = (2.0 * math.sin(2.0 * math.pi * x / float(W) + phase)
            + 1.4 * math.sin(2.0 * math.pi * 2 * x / float(W) + phase * 1.7)
            + 0.9 * math.sin(2.0 * math.pi * 3 * x / float(W) + phase * 0.6))
    return max(0, min(24, int(round(3 + offset * 0.7 + wave))))


def field_side(index, which):
    """Left and right column of a parcel, each leaning a little, so the
    hedgerow between two fields is not a perfectly vertical line."""
    x0 = FIELD_BOUNDARIES[index]
    x1 = FIELD_BOUNDARIES[index + 1]
    lean = ((index * 7) % 5) - 2
    if which == "left":
        return x0 + lean
    return x1 - ((index * 5) % 5) + 2


def build_fields():
    """Patchwork fields: eleven irregular parcels in three greens, dark
    hedgerow lines between them, and furrow dither rows inside each parcel.
    The layer is 56 px tall and drawn at screen y 128, so everything worth
    seeing sits in rows 0..30 of the tile."""
    tile = Tile(W, 56)
    tile.rect(0, 0, W - 1, 55, GREEN_DEEP)

    for index in range(len(FIELD_COLOURS)):
        colour = FIELD_COLOURS[index]
        furrow = GREEN_MID if colour == GREEN_LIGHT else (
            GREEN_DEEP if colour == GREEN_MID else GREEN_MID)
        left = field_side(index, "left")
        right = field_side(index, "right")
        for x in range(left, right):
            top = field_top(x, index)
            for y in range(top, 32):
                tile.put(x, y, colour)
            # Dark hedgerow along the top edge of every parcel.
            tile.put(x, top, INK)
            tile.put(x, top + 1, INK)
            # Furrow rows: a 50 percent dither of the neighbouring green.
            for y in range(top + 3, 32, 4):
                if (x + y) % 2 == 0:
                    if tile.get(x, y) == colour:
                        tile.put(x, y, furrow)

    # Dark hedgerow lines between the parcels, including across the wrap
    # edge, so the tile seam carries a hedgerow like any other boundary.
    for index in range(1, len(FIELD_BOUNDARIES) - 1):
        x = FIELD_BOUNDARIES[index]
        for y in range(2, 32):
            tile.put(x, y, INK)
            tile.put(x - 1, y, INK)
    for y in range(2, 32):
        tile.put(0, y, INK)
        tile.put(W - 1, y, INK)

    # Two oaks, standing in the fields.
    for ox in (100, 352):
        tile.rect(ox, 18, ox + 1, 31, STONE_MID)
        tile.disc(ox, 14, 6, GREEN_DEEP)
        tile.disc(ox - 4, 17, 4, GREEN_DEEP)
        tile.disc(ox + 4, 17, 4, GREEN_DEEP)
        for dx in range(-6, 7):
            tile.put(ox + dx, 9 + abs(dx) // 3, GREEN_DEEP)
        for dx in range(-3, 4):
            tile.put(ox + dx, 11 + abs(dx) // 2, GREEN_MID)

    # The stone farmhouse with one lit window, at x 190..214. The roof is a
    # dark silhouette, which reads well against the night sky.
    fx = 190
    tile.rect(fx, 16, fx + 24, 31, STONE_MID)
    tile.poly([(fx - 2, 16), (fx + 26, 16), (fx + 20, 9), (fx + 4, 9)], INK)
    tile.rect(fx + 9, 20, fx + 12, 24, GOLD)
    tile.rect(fx + 8, 19, fx + 13, 25, INK)
    tile.rect(fx + 9, 20, fx + 12, 24, GOLD)
    tile.rect(fx + 17, 25, fx + 19, 31, INK)
    for x in range(fx, fx + 25, 4):
        tile.put(x, 14, INK)
    return [tile]


# -------------------------------------------------------------- verge (L5)

SIGN_W = 89
SIGN_H = 16
SIGN_X = 30
SIGN_Y = 30


def sign_plate(text):
    """One road sign: a dark border, a dark face, bright text.

    The face is dark stone rather than green, because the sign stands in
    front of a green hedge and a green face would vanish into it. The text
    is the brightest thing on the sign, so it reads at 1x.
    """
    tile = Tile(SIGN_W, SIGN_H)
    tile.rect(0, 0, SIGN_W - 1, SIGN_H - 1, INK)
    tile.rect(1, 1, SIGN_W - 2, SIGN_H - 2, STONE_DEEP)
    tile.rect(1, 1, SIGN_W - 2, 1, GREEN_MID)
    tile.text((SIGN_W - text_width(text)) // 2, 4, text, STAR_BRIGHT)
    return tile


def build_verge():
    """The near verge: hedge, dry stone wall, telegraph poles, the red phone
    box and the road sign. It is 92 px tall and drawn at screen y 120, so the
    hedge crest lands at screen y 160, the wall at 180..190, and the sign
    plate stands against the dark downs at screen y 120..136."""
    tile = Tile(W, 92)

    def hedge_top(x):
        return 40 + 3 * math.sin(2.0 * math.pi * x / float(W)) \
                    + 2 * math.sin(2.0 * math.pi * 2 * x / float(W) + 0.7)

    for x in range(W):
        top = int(round(hedge_top(x)))
        tile.column(x, top, 59, GREEN_MID)
        tile.put(x, top, GREEN_LIGHT)
        if x % 4 == 0:
            tile.put(x, top + 1, GREEN_LIGHT)
        for y in range(top + 2, 60):
            if (x + y) % 7 == 0:
                tile.put(x, y, GREEN_DEEP)

    # Verge grass between the wall and the road. This is the nearest band,
    # so it is the brightest green in the scene, which is what makes the
    # depth read at a glance.
    tile.rect(0, 60, W - 1, 91, GREEN_PALE)
    for x in range(0, W, 3):
        tile.put(x, 61 + (x % 5), GREEN_LIGHT)
        tile.put(x + 1, 64 + (x % 4), GREEN_MID)
    for x in range(0, W, 7):
        tile.put(x, 68 + (x % 3), GREEN_LIGHT)

    # Dry stone wall: staggered blocks, a moonlit top course, dark mortar.
    for block in range(4):
        rng = random.Random(5505 + block)
        x = block * 128
        while x < (block + 1) * 128:
            width = rng.choice([10, 12, 14])
            colour = STONE_MID if rng.random() < 0.6 else STONE_DEEP
            tile.rect(x, 60, x + width - 1, 63, colour)
            x += width
        x = block * 128 - 6
        while x < (block + 1) * 128:
            width = rng.choice([11, 13])
            colour = STONE_MID if rng.random() < 0.6 else STONE_DEEP
            tile.rect(x, 64, x + width - 1, 68, colour)
            x += width
    for x in range(0, W, 11):
        tile.put(x, 60 + (x % 3), INK)
        tile.put(x, 64 + (x % 3), INK)
    tile.hline(0, W - 1, 59, STONE_MID)
    tile.hline(0, W - 1, 69, INK)

    # Telegraph poles, two per tile, in front of the hedge.
    for pole_x in (60, 236):
        tile.rect(pole_x, 0, pole_x + 2, 74, STONE_DEEP)
        tile.rect(pole_x - 5, 2, pole_x + 7, 3, STONE_DEEP)
        tile.rect(pole_x - 5, 6, pole_x + 7, 7, STONE_DEEP)
        for x in range(pole_x - 5, pole_x + 8):
            tile.put(x, 1, STAR_DIM)
            tile.put(x, 5, STAR_DIM)
        tile.put(pole_x + 2, 20, STAR_DIM)
        tile.put(pole_x + 2, 44, STAR_DIM)

    # The red phone box, standing on the verge in front of the wall.
    bx, by = 14, 50
    tile.rect(bx, by, bx + 11, by + 21, RED)
    tile.rect(bx, by, bx + 11, by, INK)
    tile.rect(bx, by + 21, bx + 11, by + 21, INK)
    tile.rect(bx, by, bx, by + 21, INK)
    tile.rect(bx + 11, by, bx + 11, by + 21, INK)
    tile.rect(bx + 1, by + 1, bx + 10, by + 2, STONE_DEEP)
    for gx in (bx + 2, bx + 6):
        tile.rect(gx, by + 4, gx + 2, by + 8, STAR_BRIGHT)
    tile.rect(bx + 2, by + 12, bx + 9, by + 13, STONE_DEEP)
    tile.rect(bx + 4, by + 15, bx + 7, by + 20, STONE_DEEP)
    tile.put(bx + 5, by + 17, GOLD)

    # The road sign: two posts and the plate.
    plate = sign_plate("SOUTHAMPTON 74")
    tile.paste(plate, SIGN_X, SIGN_Y)
    post_top = SIGN_Y + SIGN_H
    tile.rect(SIGN_X + 6, post_top, SIGN_X + 7, 74, STONE_DEEP)
    tile.rect(SIGN_X + SIGN_W - 10, post_top, SIGN_X + SIGN_W - 9, 74, STONE_DEEP)
    return [tile]


# --------------------------------------------------------------- road (L6)

def build_road():
    """A two lane country road. The asphalt grain repeats with a 32 px period,
    which divides 512, so the tile wraps with no cut texture."""
    tile = Tile(W, 44)
    tile.rect(0, 0, W - 1, 2, GREEN_MID)
    tile.hline(0, W - 1, 3, INK)
    tile.rect(0, 4, W - 1, 40, ASPHALT)
    for y in range(4, 41):
        for x in range(W):
            if ((x % 32) + 2 * (y % 8)) % 11 == 0:
                tile.put(x, y, INK)
    # Dashed centre line, worn white.
    for x in range(0, W, 18):
        tile.rect(x, 10, x + 8, 11, STAR_DIM)
    tile.hline(0, W - 1, 41, INK)
    tile.rect(0, 42, W - 1, 43, GREEN_DEEP)
    return [tile]


# ----------------------------------------------------------------- fg (L7)

def build_fg():
    """Foreground grass and fence posts. The layer is transparent above the
    grass line, so only the near stuff is drawn, and it passes in front of the
    car."""
    tile = Tile(W, 44)
    for block in range(4):
        rng = random.Random(6606 + block)
        for _ in range(6):
            x = block * 128 + rng.randrange(128)
            blades = rng.randrange(3, 7)
            for blade in range(blades):
                bx = x + blade * 2 - blades
                height = rng.randrange(6, 13)
                for dy in range(height):
                    tile.put(bx + dy // 4, 43 - dy, INK)
            tile.put(x, 40, GREEN_DEEP)

    for px in (36, 164, 292, 420):
        tile.rect(px, 8, px + 3, 43, INK)
        tile.put(px + 3, 8, STONE_DEEP)
        tile.put(px + 3, 20, STONE_DEEP)
        tile.put(px + 3, 34, STONE_DEEP)
    tile.rect(0, 42, W - 1, 43, INK)
    return [tile]


# ------------------------------------------------------- headlight cone

CONE_W = 90
CONE_H = 40


def build_cone():
    """The headlight cone, an overlay the game draws at the car x. The beam
    starts narrow at the lamp and opens onto the road ahead. The dither is
    dense enough that the lit road reads clearly at 1x, and the road texture
    still shows through it."""
    tile = Tile(CONE_W, CONE_H)
    for x in range(CONE_W):
        spread = 1 + int((x * 15) / float(CONE_W))
        centre = 18 + int((x * 9) / float(CONE_W))
        for y in range(centre - spread, centre + spread + 1):
            if not (0 <= y < CONE_H):
                continue
            # The core of the beam is solid, the edges are a 50 percent
            # dither, so the beam has a soft edge without a blend.
            if abs(y - centre) <= max(1, spread - 4):
                tile.put(x, y, STAR_DIM)
            elif (x + y) % 2 == 0:
                tile.put(x, y, STAR_DIM)
    # Hot spot just in front of the lamp, and the bright heart of the beam
    # where the road is closest to the car.
    tile.disc(4, 18, 4, STAR_BRIGHT)
    tile.disc(4, 18, 3, STAR_DIM)
    for x in range(6, 22):
        spread = 1 + int((x * 15) / float(CONE_W))
        centre = 18 + int((x * 9) / float(CONE_W))
        for y in range(centre - spread, centre + spread + 1):
            if 0 <= y < CONE_H and abs(y - centre) <= max(1, spread - 5):
                tile.put(x, y, STAR_BRIGHT)
    return [tile]


# ------------------------------------------------------------------- signs

SIGN_TEXTS = ["SOUTHAMPTON 74", "SOUTHAMPTON 52", "SOUTHAMPTON 31", "SOUTHAMPTON 9"]


def build_signs():
    tiles = [sign_plate(text) for text in SIGN_TEXTS]
    return tiles, SIGN_W, SIGN_H


# --------------------------------------------------------------- assembly

LAYERS = [
    {"name": "title_L1_sky", "builder": build_sky, "height": 120, "fps": 2, "y": 0, "speed": 0.0},
    {"name": "title_L2_clouds", "builder": build_clouds, "height": 120, "fps": 0, "y": 0, "speed": 0.05},
    {"name": "title_L3_downs", "builder": build_downs, "height": 48, "fps": 0, "y": 92, "speed": 0.15},
    {"name": "title_L4_fields", "builder": build_fields, "height": 56, "fps": 0, "y": 128, "speed": 0.35},
    {"name": "title_L5_verge", "builder": build_verge, "height": 92, "fps": 0, "y": 120, "speed": 0.7},
    {"name": "title_L6_road", "builder": build_road, "height": 44, "fps": 0, "y": 196, "speed": 1.0},
    {"name": "title_L7_fg", "builder": build_fg, "height": 44, "fps": 0, "y": 196, "speed": 1.3},
]


def strip_image(tiles):
    width = tiles[0].w
    height = tiles[0].h
    strip = Image.new("RGBA", (width * len(tiles), height), (0, 0, 0, 0))
    for index, tile in enumerate(tiles):
        strip.paste(tile.image(), (index * width, 0))
    return strip


def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False)


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seam_metric(tile):
    """Outlier test for the wrap edge. A tile is seamless when the step from
    its last column back to its first is no worse than the sharpest step the
    tile already contains internally."""
    def delta(a, b):
        if a == TRANSPARENT and b == TRANSPARENT:
            return 0
        if a == TRANSPARENT or b == TRANSPARENT:
            return 255
        ra, ga, ba = PALETTE[a]
        rb, gb, bb = PALETTE[b]
        return max(abs(ra - rb), abs(ga - gb), abs(ba - bb))

    interior_max = 0
    for x in range(tile.w - 1):
        for y in range(tile.h):
            interior_max = max(interior_max, delta(tile.get(x, y), tile.get(x + 1, y)))

    wrap_max = 0
    for y in range(tile.h):
        wrap_max = max(wrap_max, delta(tile.get(tile.w - 1, y), tile.get(0, y)))
    return wrap_max, interior_max


def compose(frames, camera_x, cone_at=None, cone_image=None):
    """One 256x240 frame; each layer shifted by its own scroll speed."""
    frame = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 255))
    for spec in LAYERS:
        image = frames[spec["name"]][0]
        offset = int(round(camera_x * spec["speed"])) % W
        strip = Image.new("RGBA", (W * 2, image.height), (0, 0, 0, 0))
        strip.paste(image, (0, 0))
        strip.paste(image, (W, 0))
        window = strip.crop((offset, 0, offset + SCREEN_W, image.height))
        frame.alpha_composite(window, (0, spec["y"]))
    if cone_at is not None and cone_image is not None:
        frame.alpha_composite(cone_image, (cone_at, 200))
    return frame


def label_band(width, height, text, colour_index=STAR_BRIGHT):
    tile = Tile(width, height, fill=INK)
    tile.text(4, max(0, (height - GLYPH_H) // 2), text, colour_index)
    return tile.image()


def contact_sheet(all_frames):
    gutter = 150
    rows = [(spec, all_frames[spec["name"]][0]) for spec in LAYERS]
    total_h = sum(image.height + 4 for _, image in rows) + 4
    sheet = Image.new("RGBA", (gutter + W, total_h), (10, 10, 15, 255))
    y = 2
    for spec, image in rows:
        sheet.alpha_composite(label_band(gutter - 2, image.height, spec["name"].replace("title_", "")), (2, y))
        sheet.alpha_composite(image, (gutter, y))
        y += image.height + 4
    return sheet


def seam_sheet(all_frames):
    gutter = 150
    total_h = sum(all_frames[spec["name"]][0].height + 6 for spec in LAYERS) + 6
    sheet = Image.new("RGBA", (gutter + W * 2, total_h), (10, 10, 15, 255))
    y = 3
    for spec in LAYERS:
        image = all_frames[spec["name"]][0]
        sheet.alpha_composite(label_band(gutter - 2, image.height, "%s x2" % spec["name"].replace("title_", "")), (2, y))
        sheet.alpha_composite(image, (gutter, y))
        sheet.alpha_composite(image, (gutter + W, y))
        for tick in range(4):
            sheet.putpixel((gutter + W - 1, y + tick), (200, 60, 60, 255))
            sheet.putpixel((gutter + W, y + tick), (200, 60, 60, 255))
        y += image.height + 6
    return sheet


def main():
    records = []
    all_frames = {}
    colours_report = []
    seam_report = []

    for spec in LAYERS:
        tiles = spec["builder"]()
        for tile in tiles:
            if tile.w != W:
                raise SystemExit("%s: width %d, expected %d" % (spec["name"], tile.w, W))
            if tile.h != spec["height"]:
                raise SystemExit("%s: height %d, expected %d" % (spec["name"], tile.h, spec["height"]))
        strip = strip_image(tiles)
        path = SPRITE_DIR / (spec["name"] + ".png")
        save_png(strip, path)
        save_json(SPRITE_DIR / (spec["name"] + ".json"), {
            "name": spec["name"],
            "frame_w": W,
            "frame_h": spec["height"],
            "frames": len(tiles),
            "fps": spec["fps"],
        })
        used = sorted(set(i for tile in tiles for i in tile.colours_used()))
        all_frames[spec["name"]] = [tile.image() for tile in tiles]
        colours_report.append((spec["name"], used))
        seam_report.append((spec["name"],) + seam_metric(tiles[0]))
        records.append(path)

    sign_tiles, sign_w, sign_h = build_signs()
    sign_path = SPRITE_DIR / "spr_title_sign.png"
    save_png(strip_image(sign_tiles), sign_path)
    save_json(SPRITE_DIR / "spr_title_sign.json", {
        "name": "spr_title_sign",
        "frame_w": sign_w,
        "frame_h": sign_h,
        "frames": len(sign_tiles),
        "fps": 0,
    })
    colours_report.append(("spr_title_sign", sorted(set(i for t in sign_tiles for i in t.colours_used()))))
    records.append(sign_path)

    cone_tiles = build_cone()
    cone_path = SPRITE_DIR / "spr_title_cone.png"
    save_png(strip_image(cone_tiles), cone_path)
    save_json(SPRITE_DIR / "spr_title_cone.json", {
        "name": "spr_title_cone",
        "frame_w": CONE_W,
        "frame_h": CONE_H,
        "frames": len(cone_tiles),
        "fps": 0,
    })
    colours_report.append(("spr_title_cone", sorted(set(i for t in cone_tiles for i in t.colours_used()))))
    records.append(cone_path)

    # Previews. The cone sits at x 140..230, the lit road ahead of the car.
    preview = compose(all_frames, camera_x=0.0, cone_at=140, cone_image=cone_tiles[0].image())
    preview_path = OUT_DIR / "title_world_preview.png"
    save_png(preview.resize((SCREEN_W * 3, SCREEN_H * 3), Image.NEAREST), preview_path)
    records.append(preview_path)

    scroll = compose(all_frames, camera_x=137.0, cone_at=140, cone_image=cone_tiles[0].image())
    scroll_path = OUT_DIR / "title_world_scroll.png"
    save_png(scroll.resize((SCREEN_W * 3, SCREEN_H * 3), Image.NEAREST), scroll_path)
    records.append(scroll_path)

    contact_path = OUT_DIR / "title_world_contact.png"
    save_png(contact_sheet(all_frames), contact_path)
    records.append(contact_path)

    seams_path = OUT_DIR / "title_world_seams.png"
    save_png(seam_sheet(all_frames), seams_path)
    records.append(seams_path)

    # Checks.
    problems = []
    room_colours = set()
    for name, used in colours_report:
        room_colours.update(used)
        if len(used) > 16:
            problems.append("%s uses %d colours, the limit is 16" % (name, len(used)))
        for index in used:
            if index >= len(PALETTE):
                problems.append("%s uses index %d, outside data/palette.json" % (name, index))
    if len(room_colours) > 16:
        problems.append("the title room uses %d colours, the limit is 16" % len(room_colours))
    for name, wrap_max, interior_max in seam_report:
        if wrap_max > interior_max:
            problems.append("%s wrap step %d is sharper than its own interior max %d"
                            % (name, wrap_max, interior_max))

    manifest = {
        "spec": "specs/14-title-screen-drive.md night addendum, TITLE-COORD.md",
        "generator": "tools/art/make_title_world.py",
        "font_source": FONT_SOURCE,
        "frame": [SCREEN_W, SCREEN_H],
        "car_x": [76, 140],
        "cone_at": 140,
        "room_colours": sorted(room_colours),
        "compose": [{"name": spec["name"], "y": spec["y"], "height": spec["height"],
                     "speed": spec["speed"]} for spec in LAYERS],
        "files": [],
    }
    for path in records:
        manifest["files"].append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    manifest_path = OUT_DIR / "title_world_manifest.json"
    save_json(manifest_path, manifest)

    print("TS-B night title world")
    print("font source: %s" % FONT_SOURCE)
    for name, used in colours_report:
        print("  %-18s %2d palette colours: %s" % (name, len(used), used))
    print("title room colours: %d of 16" % len(room_colours))
    print("seam check (wrap max step, interior max step):")
    for name, wrap_max, interior_max in seam_report:
        print("  %-18s %4d %4d" % (name, wrap_max, interior_max))
    print("files:")
    for path in records + [manifest_path]:
        print("  %s  %s  %d bytes" % (sha256(path)[:16], path.relative_to(ROOT), path.stat().st_size))
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("checks: colour budget ok, seam ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
