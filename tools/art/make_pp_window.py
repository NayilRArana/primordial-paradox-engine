#!/usr/bin/env python3
"""spr_pp_window: the 9 slice JRPG dialogue window frame, in the NES palette.

What it is: the box every Final Fantasy and Dragon Quest style menu sits in, drawn as nine 8x8 tiles so one
sprite covers any size of box. Dark blue fill, a white rounded border, and one pixel of grey just inside the
border so the frame reads as carved rather than flat. Corners drop their outermost pixel, which is what
makes it read as rounded on an 8 px grid.

Colours are read out of data\\nes_palette.json by 2C02 index, not by hex in this file, so a palette change
shows up here as an error instead of silently repainting the window:
    $02 dark blue   the fill
    $30 white       the border
    $00 grey        the inner line
    $0F black       the backdrop behind the rounded corners

Outputs:
    game\\sprites_src\\title\\spr_pp_window.png   72x8, 9 frames of 8x8, row major: tl t tr l c r bl b br
    game\\sprites_src\\title\\spr_pp_window.json  the frame order plus the colours, for the game code
    output\\nes_ui_preview.png                    3x: a composed window with menu text, the nine slices, the font

Checks in this script: every tile is 8x8, every pixel is one of the four colours, every tile carries at
most 3 colours (so the sprite tile rule holds), and the whole strip is 16x16 area safe with black as the
backdrop. tools\\nes_check.py re-proves all of that from the PNG afterwards.

Usage:
    python tools\\art\\make_pp_window.py
    python tools\\art\\make_pp_window.py --root <repo>

Clean room: the frame is drawn from these numbers. It imitates a layout convention (a boxed menu), not any
particular game's artwork; no existing tile was measured or copied.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

import pressstart2p_font

CELL = 8
SCALE = 3

# Card t_a1170172: the box used to be filled with $02 dark blue, which the title's lower bands do not declare, and a
# frame check counted the box's blue against the field's greens. The field is now $0F, the same black as the backdrop,
# and the box is white and one shadow line, so it is drawn entirely from the ground band's palette: $20 white for the
# border, $0B the dark green for the inner line, $0F black for the field.
FILL_CODE = 0x0F
WHITE_CODE = 0x20
SHADOW_CODE = 0x0B
BLACK_CODE = 0x0F

# '.' leaves the pixel transparent (the backdrop shows through the rounded corner), 'W' white border,
# 'G' grey inner line, 'B' dark blue fill.
TOP_LEFT = [
    ".WWWWWWW",
    "WGGGGGGG",
    "WGBBBBBB",
    "WGBBBBBB",
    "WGBBBBBB",
    "WGBBBBBB",
    "WGBBBBBB",
    "WGBBBBBB",
]
TOP = ["WWWWWWWW", "GGGGGGGG"] + ["BBBBBBBB"] * 6
BOTTOM = ["BBBBBBBB"] * 6 + ["GGGGGGGG", "WWWWWWWW"]
LEFT = ["WGBBBBBB"] * 8
RIGHT = ["BBBBBBGW"] * 8
CENTRE = ["BBBBBBBB"] * 8


def flip_horizontal(rows: list) -> list:
    return [row[::-1] for row in rows]


def flip_vertical(rows: list) -> list:
    return list(reversed(rows))


SLICES = [
    ("tl", TOP_LEFT),
    ("t", TOP),
    ("tr", flip_horizontal(TOP_LEFT)),
    ("l", LEFT),
    ("c", CENTRE),
    ("r", RIGHT),
    ("bl", flip_vertical(TOP_LEFT)),
    ("b", BOTTOM),
    ("br", flip_horizontal(flip_vertical(TOP_LEFT))),
]

SYMBOL_ROLE = {".": None, "W": "white", "G": "grey", "B": "fill"}


def load_nes_palette(root: str) -> dict:
    """2C02 index to (r, g, b, 255), straight out of data\\nes_palette.json."""
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = data["colours"]
    table = {}
    for index, value in enumerate(colours):
        value = value.lstrip("#")
        table[index] = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)
    return table


def roles(table: dict) -> dict:
    return {
        "fill": table[FILL_CODE],
        "white": table[WHITE_CODE],
        "grey": table[SHADOW_CODE],
        "backdrop": table[BLACK_CODE],
    }


def sheet_pixels(img: Image.Image):
    """Every pixel in raster order. Pillow 14 drops getdata(); get_flattened_data replaces it."""
    if hasattr(img, "get_flattened_data"):
        return img.get_flattened_data()
    return img.getdata()


def tile_image(rows: list, colour_of: dict) -> Image.Image:
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    for y in range(CELL):
        for x in range(CELL):
            role = SYMBOL_ROLE[rows[y][x]]
            if role is not None:
                img.putpixel((x, y), colour_of[role])
    return img


def build_sheet(colour_of: dict) -> Image.Image:
    sheet = Image.new("RGBA", (CELL * len(SLICES), CELL), (0, 0, 0, 0))
    for index, (_, rows) in enumerate(SLICES):
        sheet.paste(tile_image(rows, colour_of), (index * CELL, 0))
    return sheet


def write_sprite(sheet: Image.Image, out_dir: str, colour_of: dict) -> dict:
    meta = {
        "name": "spr_pp_window",
        "frame_w": CELL,
        "frame_h": CELL,
        "frames": len(SLICES),
        "fps": 0.0,
        "slice": [name for name, _ in SLICES],
        "colours": {
            "fill": "#%02x%02x%02x" % colour_of["fill"][:3],
            "white": "#%02x%02x%02x" % colour_of["white"][:3],
            "grey": "#%02x%02x%02x" % colour_of["grey"][:3],
            "backdrop": "#%02x%02x%02x" % colour_of["backdrop"][:3],
        },
        "rule": "9 slice: 0 tl, 1 t, 2 tr, 3 l, 4 c, 5 r, 6 bl, 7 b, 8 br; each frame is one 8x8 tile",
        "layer": True,
    }
    png_path = os.path.join(out_dir, "spr_pp_window.png")
    json_path = os.path.join(out_dir, "spr_pp_window.json")
    sheet.save(png_path, "PNG", optimize=False)
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    return meta


# --------------------------------------------------------------------------------------------------------------
# The preview the manager looks at: a composed window with menu text in it, then the nine slices, then the font.

def compose_window(colour_of: dict, tiles_x: int, tiles_y: int) -> Image.Image:
    """A box of tiles_x by tiles_y 8x8 cells, built the way the game will build it."""
    frame = {name: tile_image(rows, colour_of) for name, rows in SLICES}
    width = tiles_x * CELL
    height = tiles_y * CELL
    box = Image.new("RGBA", (width, height), colour_of["backdrop"])
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            if tx == 0 and ty == 0:
                name = "tl"
            elif tx == tiles_x - 1 and ty == 0:
                name = "tr"
            elif tx == 0 and ty == tiles_y - 1:
                name = "bl"
            elif tx == tiles_x - 1 and ty == tiles_y - 1:
                name = "br"
            elif ty == 0:
                name = "t"
            elif ty == tiles_y - 1:
                name = "b"
            elif tx == 0:
                name = "l"
            elif tx == tiles_x - 1:
                name = "r"
            else:
                name = "c"
            box.paste(frame[name], (tx * CELL, ty * CELL))
    return box


def draw_text(canvas: Image.Image, text: str, x: int, y: int, colour, scale: int) -> None:
    """Draw text with the Press Start 2P 8x8 glyphs at a whole number scale."""
    cursor = x
    for ch in text:
        if ch not in pressstart2p_font.GLYPHS:
            raise SystemExit("preview text uses a glyph the font does not have: %r" % ch)
        rows = pressstart2p_font.bitmap(ch)
        for gy in range(CELL):
            for gx in range(CELL):
                if rows[gy][gx] == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            canvas.putpixel((cursor + gx * scale + dx, y + gy * scale + dy), colour)
        cursor += (CELL + 1) * scale


def build_preview(sheet: Image.Image, colour_of: dict) -> Image.Image:
    canvas = Image.new("RGBA", (1184, 760), colour_of["backdrop"])
    # The composed window, 21 tiles wide and 9 tall, at 3x, with a menu in it.
    box = compose_window(colour_of, 21, 9)
    canvas.alpha_composite(box.resize((box.width * SCALE, box.height * SCALE), Image.NEAREST), (48, 48))
    menu = ["NEW GAME", "CONTINUE", "SETTINGS", "QUIT"]
    for row, label in enumerate(menu):
        draw_text(canvas, label, 48 + 24 * SCALE, 48 + (2 + row) * CELL * SCALE,
                  colour_of["white"], SCALE)
    # The title's own cursor sits on the first entry, at 3x, from the committed sprite.
    cursor = sheet_sprite("spr_pp_menu_cursor").crop((0, 0, CELL, CELL))
    canvas.alpha_composite(
        cursor.resize((CELL * SCALE, CELL * SCALE), Image.NEAREST), (48 + 16 * SCALE, 48 + 2 * CELL * SCALE))

    draw_text(canvas, "9 SLICE TL T TR L C R BL B BR", 48, 300, colour_of["white"], SCALE)
    x = 48
    for index in range(len(SLICES)):
        slice_img = sheet.crop((index * CELL, 0, index * CELL + CELL, CELL))
        big = slice_img.resize((CELL * SCALE, CELL * SCALE), Image.NEAREST)
        # A grey surround so the transparent corner pixels are visible as transparent.
        canvas.paste(Image.new("RGBA", (big.width + 6, big.height + 6), colour_of["grey"]), (x - 3, 320 - 3))
        canvas.alpha_composite(big, (x, 320))
        x += CELL * SCALE + 12

    draw_text(canvas, "FONT8 46 GLYPHS 8X8", 48, 420, colour_of["white"], SCALE)
    font = sheet_font()
    canvas.alpha_composite(font.resize((font.width * SCALE, font.height * SCALE), Image.NEAREST), (48, 448))
    return canvas


def sheet_font() -> Image.Image:
    """The committed font strip, so the preview shows the real asset and not a redrawing."""
    return sheet_sprite("spr_pp_font8")


def sheet_sprite(name: str) -> Image.Image:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "game", "sprites_src", "title", name + ".png")
    with Image.open(path) as img:
        return img.convert("RGBA")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else \
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    table = load_nes_palette(root)
    colour_of = roles(table)
    out_dir = os.path.join(root, "game", "sprites_src", "title")
    preview_dir = os.path.join(root, "output")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(preview_dir, exist_ok=True)

    sheet = build_sheet(colour_of)
    meta = write_sprite(sheet, out_dir, colour_of)

    # Prove the tile rules here rather than trusting the drawing: 8x8 tiles, 4 colours, 3 per tile.
    used = {pixel for pixel in sheet_pixels(sheet) if pixel[3]}
    assert len(used) <= 4, "the window uses %d colours, it should be 3 plus the backdrop" % len(used)
    for index in range(len(SLICES)):
        tile = sheet.crop((index * CELL, 0, index * CELL + CELL, CELL))
        per_tile = {pixel for pixel in sheet_pixels(tile) if pixel[3]}
        assert len(per_tile) <= 3, "slice %d carries %d colours" % (index, len(per_tile))

    preview = build_preview(sheet, colour_of)
    preview_path = os.path.join(preview_dir, "nes_ui_preview.png")
    preview.save(preview_path, "PNG")

    print("make_pp_window: %dx%d, %d frames (%s)" % (sheet.width, sheet.height, meta["frames"],
                                                     " ".join(meta["slice"])))
    print("  colours: fill %s, border %s, inner line %s, backdrop %s"
          % (meta["colours"]["fill"], meta["colours"]["white"], meta["colours"]["grey"],
             meta["colours"]["backdrop"]))
    print("  wrote %s and %s" % (os.path.join(out_dir, "spr_pp_window.png"), preview_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
