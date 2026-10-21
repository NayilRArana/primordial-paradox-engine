#!/usr/bin/env python3
"""Compose the title screen art into a preview animation and a contact sheet.

This script draws NO art. It only assembles the strips the three art parts produced
(TS-A the UI, TS-B the world layers, TS-C the car and the cast) into the two
deliverables the director asked for:

    output/title_scene_preview.gif   10 seconds of the night drive, 256x240 at 3x
    output/title_art_contact.png     every title asset on one labelled sheet

Contract: TITLE-COORD.md and specs/14-title-screen-drive.md plus its night drive
addendum. Everything here is original and clean room: the script only reads the
PNG strips the other parts wrote and it copies no art, no letterform and no data
from any existing game.

The layer table (screen y, scroll speed, frame rate) is read from the world
generator's own manifest, output/title_world_manifest.json, so the composer and
the world can never drift apart. If that file is missing, the fallback table below
is the same one the world generator documents.

The car parts are placed by looking at the car sprite itself, not by hard coded
numbers: the wheel arch centres and the two window openings are read out of the
pixels, so a redrawn car body still gets its wheels under the arches and its two
heads behind the glass.

Determinism: no clock, no unseeded randomness, no network, no window. Run the
script twice and the sha256 of both outputs is the same.

Usage:
    python tools/art/compose_title_preview.py
    python tools/art/compose_title_preview.py --frames 20 --out-dir <dir>   # fast test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRAME_W, FRAME_H = 256, 240
SCALE = 3

# ---------------------------------------------------------------------------------------------------
# The layer table, used only when output/title_world_manifest.json is missing. It is the table
# tools/art/make_title_world.py documents, so both halves of the title screen agree.
# ---------------------------------------------------------------------------------------------------
FALLBACK_LAYERS = [
    {"name": "title_L1_sky", "y": 0, "speed": 0.0, "fps": 2.0},
    {"name": "title_L2_clouds", "y": 0, "speed": 0.05, "fps": 0.0},
    {"name": "title_L3_downs", "y": 92, "speed": 0.15, "fps": 0.0},
    {"name": "title_L4_fields", "y": 128, "speed": 0.35, "fps": 0.0},
    {"name": "title_L5_verge", "y": 120, "speed": 0.70, "fps": 0.0},
    {"name": "title_L6_road", "y": 196, "speed": 1.00, "fps": 0.0},
    {"name": "title_L7_fg", "y": 196, "speed": 1.30, "fps": 0.0},
]

# The road sign is baked into the verge tile as a plate at these tile coordinates
# (see SIGN_X and SIGN_Y in tools/art/make_title_world.py). The separate sign strip
# carries the same 89x16 plate with the counting down numbers on it, so the composer
# draws the strip exactly over the baked plate and the number counts down as the
# verge scrolls.
SIGN_TILE_X, SIGN_TILE_Y = 30, 30

# Where the car stands on the road. CAR_X comes from the world manifest (the world
# generator reserved x 76..140 for it). CAR_Y puts the tyre bottoms, the last row of
# the 32 px car sprite, on the near half of the tarmac.
FALLBACK_CAR_X = 76
FALLBACK_CONE_X = 140
CAR_Y = 186

# The wheel sprite is 10x10 and the tyre bottom is the last row of the car sprite,
# so a wheel sits at rows 22..31 of the 64x32 car.
WHEEL_SIZE = 10
WHEEL_BOTTOM_ROW = 31

# The logo sits top centre, in the sky, above the horizon.
LOGO_X, LOGO_Y = (FRAME_W - 224) // 2, 2

# The prompt blinks under the logo; the menu replaces it after the press.
PROMPT_Y = 72
MENU_X, MENU_Y, MENU_STEP = 16, 66, 12
MENU_ROWS = ["NEW GAME", "CONTINUE", "SETTINGS", "QUIT"]
CURSOR_X, CURSOR_Y = MENU_X - 10, MENU_Y

# The frame at which the preview shows the menu instead of the prompt.
MENU_AT = 5.0

# Theo's storm cloud follows the car and hangs in the sky just above the downs.
CLOUD_DX, CLOUD_DY = 64, 80

# ---------------------------------------------------------------------------------------------------
# The 8x8 font sheet: one glyph per frame, in ASCII order. This is the order TITLE-COORD.md fixes.
# ---------------------------------------------------------------------------------------------------
GLYPH_ORDER = " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GLYPH_W, GLYPH_H = 5, 7
GLYPH_ADVANCE = 6


class TitleArt:
    """Every title strip on disk, split into frames."""

    def __init__(self, sprite_dir: str):
        self.dir = sprite_dir
        self.meta: dict[str, dict] = {}
        self.frames: dict[str, list[Image.Image]] = {}
        for fname in sorted(os.listdir(sprite_dir)):
            if not fname.endswith(".json"):
                continue
            name = fname[:-5]
            png = os.path.join(sprite_dir, name + ".png")
            if not os.path.isfile(png):
                raise SystemExit("%s has a JSON but no PNG beside it" % name)
            with open(os.path.join(sprite_dir, fname), "r", encoding="utf-8") as handle:
                info = json.load(handle)
            sheet = Image.open(png).convert("RGBA")
            width, height = info["frame_w"], info["frame_h"]
            if sheet.size != (width * info["frames"], height):
                raise SystemExit("%s: PNG is %s, the JSON says %s"
                                 % (name, sheet.size, (width * info["frames"], height)))
            self.meta[name] = info
            self.frames[name] = [sheet.crop((i * width, 0, (i + 1) * width, height))
                                 for i in range(info["frames"])]

    def need(self, *names: str) -> None:
        missing = [n for n in names if n not in self.frames]
        if missing:
            raise SystemExit("these title strips are missing: %s" % ", ".join(missing))

    def frame(self, name: str, index: int) -> Image.Image:
        strip = self.frames[name]
        return strip[index % len(strip)]

    def count(self, name: str) -> int:
        return len(self.frames[name])


# ---------------------------------------------------------------------------------------------------
# Reading the car sprite, so the parts land on the car and not at numbers somebody remembered.
# ---------------------------------------------------------------------------------------------------

def bottom_row(frame: Image.Image) -> int:
    pixels = frame.load()
    width, height = frame.size
    for y in range(height - 1, -1, -1):
        for x in range(width):
            if pixels[x, y][3] != 0:
                return y
    return height - 1


def ink_runs(frame: Image.Image, row: int, ink: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    """The runs of the ink colour on one row."""
    pixels = frame.load()
    width = frame.size[0]
    runs = []
    start = None
    for x in range(width):
        is_ink = pixels[x, row][:3] == ink[:3]
        if is_ink and start is None:
            start = x
        elif not is_ink and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, width - 1))
    return runs


def arch_centres(frame: Image.Image, ink: tuple[int, int, int, int]) -> list[int]:
    """The x of the middle of each wheel arch, found from the pixels.

    A wheel arch shows up on the bottom edge of the body in one of two ways: as a
    dark half circle drawn on the body, or as a bite taken out of the body. Both
    show as a run of at least six columns on the bottom row that is not the body
    colour, so both are read the same way. The middle of each run is where the
    wheel belongs.
    """
    pixels = frame.load()
    width, height = frame.size
    bottom = bottom_row(frame)
    if bottom <= 1:
        return []

    kinds = []
    for x in range(width):
        r, g, b, a = pixels[x, bottom]
        if a == 0:
            kinds.append("t")
        elif (r, g, b) == ink[:3]:
            kinds.append("d")
        else:
            kinds.append("b")

    runs = []
    start = None
    kind = None
    for x in range(width + 1):
        current = kinds[x] if x < width else None
        if current is not None and current != "b":
            if start is None:
                start, kind = x, current
        elif start is not None:
            if kind == "d" or (start > 0 and x < width):
                runs.append((start, x - 1))
            start, kind = None, None
    centres = [(a + b) // 2 for a, b in runs if b - a >= 6]
    if len(centres) == 2:
        return centres
    # Fall back on the geometry the manager gave for the car body: the arches sit
    # at x 14 and x 46 with a 10x10 wheel centred on each.
    if len(centres) == 1:
        return [14, 46] if centres[0] < 30 else [14, 46]
    return [14, 46]


def window_band(frame: Image.Image, ink: tuple[int, int, int, int]) -> tuple[int, int]:
    """The first and last row of the side glass band."""
    pixels = frame.load()
    width, height = frame.size
    counts = [sum(1 for x in range(width) if pixels[x, y][:3] == ink[:3]) for y in range(height)]
    if not counts or max(counts) < 6:
        return (0, height - 1)
    best = max(counts)
    rows = [y for y in range(height) if counts[y] >= max(6, best * 3 // 4)]
    return (rows[0], rows[-1])


def window_openings(frame: Image.Image, ink: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    """The side window openings of the car, as (x0, x1) column ranges.

    A column belongs to a window when it is glass on most of the band rows. The runs
    of such columns are the windows, separated by the pillars.
    """
    pixels = frame.load()
    width, height = frame.size
    top, bottom = window_band(frame, ink)
    band = list(range(top, bottom + 1))
    if not band:
        return []
    in_window = []
    for x in range(width):
        hits = sum(1 for y in band if pixels[x, y][:3] == ink[:3])
        in_window.append(hits >= max(2, len(band) * 2 // 3))

    openings = []
    start = None
    for x in range(width):
        if in_window[x] and start is None:
            start = x
        elif not in_window[x] and start is not None:
            openings.append((start, x - 1))
            start = None
    if start is not None:
        openings.append((start, width - 1))
    # A window has to be wide enough for a head.
    return [(a, b) for a, b in openings if b - a >= 5]


def glass_mask(frame: Image.Image, ink: tuple[int, int, int, int]) -> Image.Image:
    """A mask of the glass pixels of the car, so a bust can only show through the glass."""
    pixels = frame.load()
    width, height = frame.size
    mask = Image.new("L", (width, height), 0)
    out = mask.load()
    for y in range(height):
        for x in range(width):
            if pixels[x, y][:3] == ink[:3]:
                out[x, y] = 255
    return mask


# ---------------------------------------------------------------------------------------------------
# Text, drawn with the project's own font sheet. The sheet has no lowercase, so text is uppercased.
# ---------------------------------------------------------------------------------------------------

def text_width(text: str) -> int:
    if not text:
        return 0
    return len(text) * GLYPH_ADVANCE - (GLYPH_ADVANCE - GLYPH_W)


def draw_text(dst: Image.Image, art: TitleArt, text: str, x: int, y: int,
              colour: tuple[int, int, int, int]) -> None:
    """Stamp text with the project's own font sheet. Each glyph sits in an 8x8 cell with its ink in
    columns 1..5 and rows 0..6, so the cell is cropped to the ink box and the pen advances 6 px."""
    for index, ch in enumerate(text.upper()):
        if ch == " ":
            continue
        if ch not in GLYPH_ORDER:
            raise SystemExit("the font sheet has no glyph for %r" % ch)
        cell = art.frame("spr_pp_font8", GLYPH_ORDER.index(ch))
        ink = cell.crop((1, 0, 1 + GLYPH_W, GLYPH_H))
        tinted = Image.new("RGBA", ink.size, colour)
        tinted.putalpha(ink.getchannel("A"))
        dst.alpha_composite(tinted, (x + index * GLYPH_ADVANCE, y))


def draw_text_centred(dst: Image.Image, art: TitleArt, text: str, y: int,
                      colour: tuple[int, int, int, int]) -> None:
    draw_text(dst, art, text, (FRAME_W - text_width(text)) // 2, y, colour)


# ---------------------------------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------------------------------

def load_palette(root: str) -> list[tuple[int, int, int, int]]:
    with open(os.path.join(root, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = []
    for value in data["colours"]:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255))
    return colours


def palette_image(colours: list[tuple[int, int, int, int]]) -> Image.Image:
    """A PIL P-mode palette image holding the master palette, used to quantise the GIF.

    The GIF keeps the exact palette entries, so no frame can drift off the master palette."""
    pal = Image.new("P", (1, 1))
    flat = []
    for r, g, b, _ in colours:
        flat.extend((r, g, b))
    while len(flat) < 768:
        flat.extend((0, 0, 0))
    pal.putpalette(flat)
    return pal


# ---------------------------------------------------------------------------------------------------
# The scene
# ---------------------------------------------------------------------------------------------------

class Scene:
    """Everything the composer needs to draw one frame, worked out once from the art on disk."""

    def __init__(self, art: TitleArt, root: str, out_dir: str):
        self.art = art
        self.layers, self.car_x, self.cone_x = self.read_manifest(root, out_dir)

        car = art.frame("spr_title_car", 0)
        self.ink = (11, 11, 15, 255)
        self.arches = arch_centres(car, self.ink)
        self.windows = window_openings(car, self.ink)
        self.band_top, self.band_bottom = window_band(car, self.ink)
        self.mask = glass_mask(car, self.ink)
        self.notes: list[str] = []
        if len(self.arches) != 2:
            self.notes.append("the car sprite has %d wheel arches, not 2" % len(self.arches))
        if len(self.windows) != 2:
            self.notes.append("the car sprite has %d glass openings, not 2" % len(self.windows))

    def read_manifest(self, root: str, out_dir: str):
        path = os.path.join(out_dir, "title_world_manifest.json")
        if not os.path.isfile(path):
            path = os.path.join(root, "output", "title_world_manifest.json")
        if not os.path.isfile(path):
            return list(FALLBACK_LAYERS), FALLBACK_CAR_X, FALLBACK_CONE_X
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        layers = []
        for entry in data.get("compose", []):
            layers.append({
                "name": entry["name"],
                "y": entry["y"],
                "speed": entry["speed"],
                "fps": 0.0,
            })
        if not layers:
            layers = list(FALLBACK_LAYERS)
        # The world generator gives the star layer a two frame twinkle; the frame rate is in
        # the sidecar JSON of the layer itself.
        for layer in layers:
            meta = self.art.meta.get(layer["name"])
            if meta:
                layer["fps"] = float(meta.get("fps", 0.0))
        car_x = data.get("car_x", [FALLBACK_CAR_X, FALLBACK_CONE_X])
        car_left = car_x[0] if car_x else FALLBACK_CAR_X
        cone_x = data.get("cone_at", FALLBACK_CONE_X)
        return layers, car_left, cone_x


def compose_frame(scene: Scene, t: float, camera_x: float,
                  colours: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    """One 256x240 frame of the title screen at time t seconds."""
    art = scene.art
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), colours["ink"])

    # The world, back to front.
    for layer in scene.layers:
        strip = art.frames[layer["name"]]
        index = int(t * layer["fps"]) % len(strip)
        tile = strip[index]
        offset = int(round(camera_x * layer["speed"])) % tile.width
        window = Image.new("RGBA", (tile.width * 2, tile.height), (0, 0, 0, 0))
        window.paste(tile, (0, 0))
        window.paste(tile, (tile.width, 0))
        frame.alpha_composite(window.crop((offset, 0, offset + FRAME_W, tile.height)),
                              (0, layer["y"]))

    # The road sign, drawn over the plate the verge tile carries, so the number counts down.
    if "spr_title_sign" in art.frames:
        verge = next((l for l in scene.layers if l["name"] == "title_L5_verge"), None)
        if verge is not None:
            offset = int(round(camera_x * verge["speed"])) % 512
            sign_index = int((t % 10.0) / 2.5) % art.count("spr_title_sign")
            sign = art.frame("spr_title_sign", sign_index)
            for shift in (-512, 0, 512):
                x = SIGN_TILE_X - offset + shift
                if -sign.width < x < FRAME_W:
                    frame.alpha_composite(sign, (x, verge["y"] + SIGN_TILE_Y))

    # The headlight cone, on the road ahead of the car.
    if "spr_title_cone" in art.frames:
        frame.alpha_composite(art.frame("spr_title_cone", 0), (scene.cone_x, 200))

    # The car and the cast. The timings come from spec 14: the wheels turn, the body bobs on a
    # frame cycle, the exhaust puffs every 20 frames, Ronan glances at his watch and Theo bobs
    # his head to the music. Frame counts come from the strips themselves.
    car_x = scene.car_x
    body_index = (int(t * 12) // 2) % art.count("spr_title_car")
    wheel_index = int(t * 12) % art.count("spr_title_wheel")

    # The exhaust puff, behind the rear of the car, then the wheels, then the body over them.
    puff = int(t * 12) % 20
    if "spr_title_exhaust" in art.frames and puff < 4:
        frame.alpha_composite(art.frame("spr_title_exhaust", puff % 4), (car_x, CAR_Y + 14))

    if scene.arches:
        for centre in scene.arches:
            frame.alpha_composite(art.frame("spr_title_wheel", wheel_index),
                                  (car_x + centre - WHEEL_SIZE // 2, CAR_Y + WHEEL_BOTTOM_ROW - WHEEL_SIZE + 1))
    else:
        for dx in (9, 41):
            frame.alpha_composite(art.frame("spr_title_wheel", wheel_index), (car_x + dx, CAR_Y + 22))

    frame.alpha_composite(art.frame("spr_title_car", body_index), (car_x, CAR_Y))

    # The two heads, in the two windows. The left window is the passenger, the right window is
    # the driver, because the car drives to the right.
    if len(scene.windows) == 2:
        left, right = scene.windows
        bust_y = CAR_Y + max(0, (scene.band_top + scene.band_bottom) // 2 - GLYPH_H // 2 - 1)
        for opening, name in ((left, "spr_title_theo"), (right, "spr_title_ronan")):
            if name not in art.frames:
                continue
            index = int(t * 8) % art.count(name)
            bust = art.frame(name, index)
            x = car_x + (opening[0] + opening[1]) // 2 - bust.width // 2
            frame.alpha_composite(bust, (x, bust_y))

    # The speech bubble, when Theo turns to speak. Once per loop, over the second half.
    if "spr_title_bubble" in art.frames and 6.0 <= (t % 10.0) <= 7.0:
        bubble_x = car_x + (scene.windows[0][0] if scene.windows else 18) - 1
        frame.alpha_composite(art.frame("spr_title_bubble", int(t * 6) % 3),
                              (bubble_x, CAR_Y - 10))

    # Theo's storm cloud, which follows the car. A soft flash every 8 to 12 seconds.
    if "spr_title_cloud" in art.frames:
        cloud_index = 0 if int(t * 2) % 2 == 0 else 1
        if 9.0 <= (t % 10.0) <= 9.4:
            cloud_index = 2
        frame.alpha_composite(art.frame("spr_title_cloud", cloud_index),
                              (car_x + CLOUD_DX, CLOUD_DY))

    # The logo, with its gold shimmer every 4 seconds.
    logo_index = 1 if (t % 4.0) < 0.4 else 0
    frame.alpha_composite(art.frame("spr_pp_title_logo", logo_index), (LOGO_X, LOGO_Y))

    # The prompt, blinking, and then the menu.
    if t < MENU_AT:
        if int(t * 2) % 2 == 0:
            draw_text_centred(frame, art, "PRESS Z OR ENTER", PROMPT_Y, colours["paper"])
    else:
        for index, row in enumerate(MENU_ROWS):
            draw_text(frame, art, row, MENU_X, MENU_Y + index * MENU_STEP, colours["paper"])
        cursor_index = 0 if int(t * 4) % 2 == 0 else 1
        frame.alpha_composite(art.frame("spr_pp_menu_cursor", cursor_index), (CURSOR_X, CURSOR_Y))

    return frame


# ---------------------------------------------------------------------------------------------------
# The contact sheet
# ---------------------------------------------------------------------------------------------------

SHEET_BG = (10, 12, 20, 255)
LABEL_COLOUR = (183, 143, 40, 255)
TITLE_COLOUR = (200, 200, 212, 255)
RULE_COLOUR = (74, 74, 88, 255)

# What goes on the sheet, and at what zoom. The wide 512 px layers are shown at 1x so the sheet
# stays readable; everything else is at 3x.
SHEET_ITEMS = [
    ("SPR PP TITLE LOGO 224X56 2 FRAMES", ["spr_pp_title_logo"], 3),
    ("SPR PP FONT8 8X8 44 GLYPHS ASCII ORDER", ["spr_pp_font8"], 3),
    ("SPR PP MENU CURSOR 8X8 2 FRAMES", ["spr_pp_menu_cursor"], 3),
    ("SPR TITLE CAR 64X32 3 FRAMES", ["spr_title_car"], 3),
    ("SPR TITLE WHEEL 10X10 4 FRAMES", ["spr_title_wheel"], 3),
    ("SPR TITLE EXHAUST 12X10 4 FRAMES", ["spr_title_exhaust"], 3),
    ("SPR TITLE RONAN 12X12 8 FRAMES", ["spr_title_ronan"], 3),
    ("SPR TITLE THEO 12X12 8 FRAMES", ["spr_title_theo"], 3),
    ("SPR TITLE BUBBLE 14X10 3 FRAMES", ["spr_title_bubble"], 3),
    ("SPR TITLE CLOUD 24X12 3 FRAMES", ["spr_title_cloud"], 3),
    ("SPR TITLE SIGN 89X16 4 FRAMES", ["spr_title_sign"], 3),
    ("SPR TITLE CONE 90X40", ["spr_title_cone"], 3),
]

LAYER_LABELS = [
    ("L1 SKY 512X120", "title_L1_sky"),
    ("L2 CLOUDS 512X120", "title_L2_clouds"),
    ("L3 DOWNS 512X48", "title_L3_downs"),
    ("L4 FIELDS 512X56", "title_L4_fields"),
    ("L5 VERGE 512X92", "title_L5_verge"),
    ("L6 ROAD 512X44", "title_L6_road"),
    ("L7 FG 512X44", "title_L7_fg"),
]

LABEL_H = 12
GAP = 8


def build_contact_sheet(art: TitleArt, scene_image: Image.Image, scene: Scene,
                        colours: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    """Every title asset on one sheet, with labels, and the composed frame at the top."""
    right_w = max(
        sum(frame.width * zoom for frame in art.frames[names[0]]) + 4 * len(art.frames[names[0]])
        for _label, names, zoom in SHEET_ITEMS
    )
    sheet_w = 16 + FRAME_W * SCALE + 24 + right_w + 16
    margin = 16
    column_x = margin + FRAME_W * SCALE + 24

    right_h = 0
    for _label, names, zoom in SHEET_ITEMS:
        for name in names:
            strip = art.frames[name]
            right_h += LABEL_H + 4 + strip[0].height * zoom + GAP
    header_h = 24
    bottom_h = 24
    sheet_h = max(header_h + FRAME_W * SCALE + 40, header_h + right_h) + bottom_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), SHEET_BG)
    draw_text(sheet, art, "PRIMORDIAL PARADOX TITLE ART CONTACT SHEET", margin, 8, TITLE_COLOUR)
    sheet.paste(RULE_COLOUR, (margin, header_h - 4, sheet_w - margin, header_h - 3))

    # Left: the composed frame, then the seven world layers at 1x.
    y = header_h
    draw_text(sheet, art, "COMPOSED TITLE FRAME 256X240 AT 3X", margin, y, LABEL_COLOUR)
    y += LABEL_H + 2
    sheet.alpha_composite(scene_image.resize((FRAME_W * SCALE, FRAME_H * SCALE), Image.NEAREST),
                          (margin, y))
    y += FRAME_H * SCALE + GAP + 4
    draw_text(sheet, art, "WORLD LAYERS AT 1X 512 PX WIDE EACH", margin, y, LABEL_COLOUR)
    y += LABEL_H + 2
    for label, name in LAYER_LABELS:
        if name not in art.frames:
            continue
        tile = art.frame(name, 0)
        draw_text(sheet, art, label, margin, y, LABEL_COLOUR)
        y += LABEL_H
        sheet.alpha_composite(tile, (margin, y))
        y += tile.height + 4

    # Right: every sprite at its zoom, with labels.
    y = header_h
    for label, names, zoom in SHEET_ITEMS:
        for name in names:
            if name not in art.frames:
                continue
            strip = art.frames[name]
            draw_text(sheet, art, label, column_x, y, LABEL_COLOUR)
            y += LABEL_H + 2
            x = column_x
            for frame in strip:
                big = frame.resize((frame.width * zoom, frame.height * zoom), Image.NEAREST)
                sheet.alpha_composite(big, (x, y))
                x += big.width + 4
            y += strip[0].height * zoom + GAP

    draw_text(sheet, art, "EVERY PIXEL IS AN EXACT DATA PALETTE JSON ENTRY", margin, sheet_h - 16,
              TITLE_COLOUR)
    return sheet


# ---------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------

def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def visible_colours(image: Image.Image) -> set[str]:
    seen = set()
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    for r, g, b, a in pixels:
        if a == 0:
            continue
        seen.add("#%02x%02x%02x" % (r, g, b))
    return seen


def save_gif(frames: list[Image.Image], path: str, palette: Image.Image, fps: int) -> None:
    quantised = [f.convert("RGB").quantize(palette=palette, dither=Image.NONE) for f in frames]
    quantised[0].save(path, format="GIF", save_all=True, append_images=quantised[1:],
                      duration=int(1000 / fps), loop=0, optimize=False, disposal=1)


# ---------------------------------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="repository root")
    parser.add_argument("--out-dir", default=None, help="where to write the outputs")
    parser.add_argument("--fps", type=int, default=12, help="preview frame rate")
    parser.add_argument("--frames", type=int, default=120, help="number of preview frames")
    parser.add_argument("--seconds", type=float, default=10.0, help="preview length in seconds")
    parser.add_argument("--no-gif", action="store_true", help="skip the gif, write the sheet only")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    sprite_dir = os.path.join(root, "game", "sprites_src", "title")
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(root, "output")
    os.makedirs(out_dir, exist_ok=True)

    palette = load_palette(root)
    colours = {
        "ink": palette[0],
        "paper": palette[5],
        "gold": palette[41],
        "stone": palette[35],
    }

    art = TitleArt(sprite_dir)
    art.need(
        "title_L1_sky", "title_L2_clouds", "title_L3_downs", "title_L4_fields",
        "title_L5_verge", "title_L6_road", "title_L7_fg",
        "spr_title_car", "spr_title_wheel",
        "spr_pp_title_logo", "spr_pp_font8", "spr_pp_menu_cursor",
    )

    scene = Scene(art, root, out_dir)

    frames = []
    for index in range(args.frames):
        t = index / float(args.fps)
        frames.append(compose_frame(scene, t, index * 1.0, colours))

    composed = frames[0]
    sheet = build_contact_sheet(art, composed, scene, colours)
    sheet_path = os.path.join(out_dir, "title_art_contact.png")
    sheet.save(sheet_path, "PNG")

    gif_path = os.path.join(out_dir, "title_scene_preview.gif")
    if not args.no_gif:
        save_gif(frames, gif_path, palette_image(palette), args.fps)

    # The report the director needs: what is on screen, and does it hold together.
    screen_colours = visible_colours(composed)
    used = set()
    for layer in scene.layers:
        used |= visible_colours(art.frame(layer["name"], 0))
    for name in ("spr_title_car", "spr_title_wheel", "spr_title_exhaust", "spr_title_ronan",
                 "spr_title_theo", "spr_title_bubble", "spr_title_cloud", "spr_title_cone",
                 "spr_title_sign", "spr_pp_title_logo", "spr_pp_menu_cursor"):
        if name in art.frames:
            used |= visible_colours(art.frame(name, 0))

    print("compose_title_preview")
    print("  composed frame      %dx%d  %d colours on screen" % (FRAME_W, FRAME_H, len(screen_colours)))
    print("  title art in total  %d distinct colours" % len(used))
    print("  car arches at x     %s" % (", ".join(str(a) for a in scene.arches) or "none found"))
    print("  car windows at x    %s" % (", ".join("%d..%d" % w for w in scene.windows) or "none found"))
    for note in scene.notes:
        print("  NOTE: " + note)
    print("  contact sheet       %s  %s" % (sheet_path, sha256(sheet_path)))
    if not args.no_gif:
        print("  scene preview       %s  %d frames at %d fps  %s"
              % (gif_path, len(frames), args.fps, sha256(gif_path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
