#!/usr/bin/env python3
"""make_ui_nes.py: the static NES JRPG user interface, drawn as reusable 8x8 window tiles.

What it makes, all deterministic, no randomness, no image inputs beyond the existing font sheet
(game\\sprites_src\\title\\spr_pp_font8.png) so a rerun produces the same bytes:

    game\\sprites_src\\ui\\spr_pp_ui_window.png    72x8   9 slices: tl t tr l c r bl b br (dark blue fill,
                                                          2 px white border)
    game\\sprites_src\\ui\\spr_pp_ui_tab.png       72x8   9 slices, the same window in the accent colour, for
                                                          the dialogue name tab
    game\\sprites_src\\ui\\spr_pp_ui_cursor.png    16x8   2 frames: the 8x8 gold arrow, then the blank frame the
                                                          blink shows
    game\\sprites_src\\ui\\spr_pp_ui_party.png     24x32  1 frame: the party placeholder block (FF1 party size)
    game\\sprites_src\\ui\\spr_pp_ui_enemy.png     32x32  1 frame: the enemy placeholder block
    game\\sprites_src\\ui\\screens\\*.png          256x240  the three screens at 1x, with a sidecar json
    data\\ui_layouts.json                                window rectangles in tiles for each screen, the text,
                                                          the sprite rectangles, the palettes used
    data\\palettes\\scene_ui.json                        the scene palette in the same format as the other
                                                          scene_*.json files (this card owns it)
    output\\ui_battle_preview.png                       3x previews for the manager
    output\\ui_dialogue_preview.png
    output\\ui_menu_preview.png

Why tiles: a NES background is 8x8 tiles plus a 16x16 attribute area, so a window must be cut on that grid.
Nine slices (corner, edge, fill) let the game size a window to any whole number of tiles; the companion
tools\\pp_ui_window.gml or the layouts json drives the placement.

The colours, by 2C02 index read from data\\nes_palette.json (never hex literals baked into the art):
    $02 dark blue   window fill                     (ART-BIBLE section 2.5, PLAN-V2 section 2)
    $30 white       window border and text
    $00 grey        the ground band and the placeholder body; deliberately kept off the window border,
                     because a gold accent pixel and a grey pixel in one 16x16 area is a 4th colour
    $28 gold        the single accent: cursor, name tab border, menu heading, enemy fill
    $0F black       backdrop (the shared backdrop colour of the scene)

NES rules this file respects and the checker proves afterwards (tools\\nes_check.py, tools\\nes_composite_check.py):
    - at most 3 colours in any 16x16 background area besides the shared backdrop $0F
    - at most 3 colours on any 8x8 sprite tile besides transparency
    - 4 background palettes and 4 sprite palettes at most (this screen set uses 3 and 3)
    - 5 distinct colours on screen (ceiling 25)
    - no gradient, no anti aliasing: every shape is flat fill, the only texture is a 2 px checker at a
      palette edge (the horizon line on the field screen)

Clean room (PLAN-V2 section 0): the window is the JRPG furniture both studied series use, described in the
art bible from published analyses. Nothing was downloaded, ripped or traced; every tile here is written as
text in this file.

Usage:
    python tools\\art\\make_ui_nes.py
    python tools\\art\\make_ui_nes.py --root <repo>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

CELL = 8
FRAME_W = 256
FRAME_H = 240
SCALE = 3
COLS = FRAME_W // CELL   # 32 tile columns
ROWS = FRAME_H // CELL   # 30 tile rows

FILL = 0x02
WHITE = 0x30
GREY = 0x00
GOLD = 0x28
BLACK = 0x0F

# The sheet's frame order, read as ASCII order. Card t_f476435e (decision D13) grew it to 77 with `/`, `[` and `]`;
# tools/check_font_coverage.py refuses a run where this copy, the rasteriser's and pp_font_glyphs() disagree.
GLYPHS = sorted(" !\"'()*,-./0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ[]abcdefghijklmnopqrstuvwxyz", key=ord)
NEAREST = getattr(Image, "Resampling", Image).NEAREST

# ---------------------------------------------------------------------------------------------------------------
# Palettes.


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_nes_palette(root: str) -> dict:
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    table = {}
    for index, value in enumerate(data["colours"]):
        value = value.lstrip("#")
        table[index] = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)
    return table


# ---------------------------------------------------------------------------------------------------------------
# Nine slice window tiles. '.' is transparent so the backdrop shows through the rounded corner; the corner
# drops exactly one pixel, which is what reads as "rounded" on an 8 px grid.

WINDOW_SLICES = {
    "tl": [
        ".WWWWWWW",
        "WWWWWWWW",
        "WWBBBBBB",
        "WWBBBBBB",
        "WWBBBBBB",
        "WWBBBBBB",
        "WWBBBBBB",
        "WWBBBBBB",
    ],
    "t": ["WWWWWWWW", "WWWWWWWW"] + ["BBBBBBBB"] * 6,
    "l": ["WWBBBBBB"] * 8,
    "c": ["BBBBBBBB"] * 8,
    "b": ["BBBBBBBB"] * 6 + ["WWWWWWWW", "WWWWWWWW"],
    "r": ["BBBBBBWW"] * 8,
}
WINDOW_ORDER = ["tl", "t", "tr", "l", "c", "r", "bl", "b", "br"]

# The name tab uses the same nine slices with the border in the accent colour, so a tab and a window share
# one shape. One tile set, two colour maps: that is how the game gets both without a second sprite sheet.
TAB_ORDER = WINDOW_ORDER

ARROW = [
    ".B......",
    ".BB.....",
    ".BBB....",
    ".BBBB...",
    ".BBBBB..",
    ".BBBB...",
    ".BBB....",
    ".BB.....",
]


def flip_horizontal(rows: list) -> list:
    return [row[::-1] for row in rows]


def flip_vertical(rows: list) -> list:
    return list(reversed(rows))


def build_slices(base: dict, order: list) -> list:
    """Expand the six authored tiles into the nine slices, flipping the corners and edges."""
    out = []
    for name in order:
        if name == "tr":
            rows = flip_horizontal(base["tl"])
        elif name == "bl":
            rows = flip_vertical(base["tl"])
        elif name == "br":
            rows = flip_horizontal(flip_vertical(base["tl"]))
        else:
            rows = base[name]
        out.append((name, rows))
    return out


def render_tile(rows: list, colour_of: dict) -> Image.Image:
    tile = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    pixels = tile.load()
    for y in range(CELL):
        for x in range(CELL):
            role = rows[y][x]
            if role == ".":
                continue
            pixels[x, y] = colour_of[role]
    return tile


def build_sheet(slices: list, colour_of: dict) -> Image.Image:
    sheet = Image.new("RGBA", (CELL * len(slices), CELL), (0, 0, 0, 0))
    for index, (_, rows) in enumerate(slices):
        sheet.paste(render_tile(rows, colour_of), (index * CELL, 0))
    return sheet


# ---------------------------------------------------------------------------------------------------------------
# Canvas helpers. Everything is drawn at 1x on a 256x240 RGBA frame; the checker reads that frame.


def new_frame(colour: tuple) -> Image.Image:
    return Image.new("RGBA", (FRAME_W, FRAME_H), colour)


def blit_tile(canvas: Image.Image, tile: Image.Image, tx: int, ty: int) -> None:
    """Paste one 8x8 tile at tile coordinates; transparent pixels leave the canvas alone."""
    src = tile.load()
    dst = canvas.load()
    for y in range(CELL):
        for x in range(CELL):
            px, py = tx * CELL + x, ty * CELL + y
            if 0 <= px < FRAME_W and 0 <= py < FRAME_H:
                r, g, b, a = src[x, y]
                if a:
                    dst[px, py] = (r, g, b, 255)


def fill_rect(canvas: Image.Image, tx: int, ty: int, tw: int, th: int, colour: tuple) -> None:
    dst = canvas.load()
    for y in range(ty * CELL, min(FRAME_H, (ty + th) * CELL)):
        for x in range(tx * CELL, min(FRAME_W, (tx + tw) * CELL)):
            dst[x, y] = colour


def fill_pixels(canvas: Image.Image, x0: int, y0: int, x1: int, y1: int, colour: tuple) -> None:
    dst = canvas.load()
    for y in range(max(0, y0), min(FRAME_H, y1)):
        for x in range(max(0, x0), min(FRAME_W, x1)):
            dst[x, y] = colour


def dither_row(canvas: Image.Image, y_px: int, x0_px: int, x1_px: int, a: tuple, b: tuple,
               height: int = 2) -> None:
    """The only texture the rules allow: a 2 px checker at a palette edge, here the field horizon."""
    dst = canvas.load()
    for y in range(y_px, min(FRAME_H, y_px + height)):
        for x in range(max(0, x0_px), min(FRAME_W, x1_px)):
            dst[x, y] = a if ((x // 2) + (y // 2)) % 2 == 0 else b


def draw_window(canvas: Image.Image, tiles: dict, tx: int, ty: int, tw: int, th: int) -> None:
    """A window of tw x th tiles, drawn from the nine slices so any size works."""
    for row in range(th):
        for col in range(tw):
            if row == 0 and col == 0:
                name = "tl"
            elif row == 0 and col == tw - 1:
                name = "tr"
            elif row == th - 1 and col == 0:
                name = "bl"
            elif row == th - 1 and col == tw - 1:
                name = "br"
            elif row == 0:
                name = "t"
            elif row == th - 1:
                name = "b"
            elif col == 0:
                name = "l"
            elif col == tw - 1:
                name = "r"
            else:
                name = "c"
            blit_tile(canvas, tiles[name], tx + col, ty + row)


# ---------------------------------------------------------------------------------------------------------------
# Font: the existing 8x8 sheet, one glyph per 8 px column, in GLYPHS order.


class Font:
    def __init__(self, root: str):
        path = os.path.join(root, "game", "sprites_src", "title", "spr_pp_font8.png")
        with Image.open(path) as sheet:
            self.sheet = sheet.convert("RGBA").copy()
        if self.sheet.height != CELL or self.sheet.width % CELL:
            raise SystemExit("spr_pp_font8.png is %dx%d; expected one 8 px row of 8x8 glyphs"
                             % (self.sheet.width, self.sheet.height))
        columns = self.sheet.width // CELL
        if columns < len(GLYPHS):
            raise SystemExit("spr_pp_font8.png holds %d glyphs, the contract is %d" % (columns, len(GLYPHS)))
        self.masks = {}
        pixels = self.sheet.load()
        for index, ch in enumerate(GLYPHS):
            lit = [(x, y) for y in range(CELL) for x in range(CELL)
                   if pixels[index * CELL + x, y][3] > 0]
            self.masks[ch] = lit

    def draw(self, canvas: Image.Image, tx: int, ty: int, text: str, colour: tuple) -> int:
        """Draw text on the 8x8 grid starting at tile tx, ty. Returns the next free tile column."""
        dst = canvas.load()
        col = tx
        for ch in text.upper():
            if ch not in self.masks:
                raise SystemExit("glyph %r is not in the 8x8 font (contract: %s)" % (ch, "".join(GLYPHS)))
            for gx, gy in self.masks[ch]:
                px, py = col * CELL + gx, ty * CELL + gy
                if 0 <= px < FRAME_W and 0 <= py < FRAME_H:
                    dst[px, py] = colour
            col += 1
        return col

    def width(self, text: str) -> int:
        return len(text)


# ---------------------------------------------------------------------------------------------------------------
# Placeholder blocks. The card asks for 24x32 party blocks; the enemy block is 32x32 so an encounter of two
# reads as two different sizes. Flat fills only: white 1 px outline, grey body, one 4x4 accent marker.


def placeholder(canvas: Image.Image, px: int, py: int, w: int, h: int, body: tuple, edge: tuple,
                mark: tuple | None = None, mark_size: int = 4) -> None:
    fill_pixels(canvas, px, py, px + w, py + h, body)
    fill_pixels(canvas, px, py, px + w, py + 1, edge)
    fill_pixels(canvas, px, py + h - 1, px + w, py + h, edge)
    fill_pixels(canvas, px, py, px + 1, py + h, edge)
    fill_pixels(canvas, px + w - 1, py, px + w, py + h, edge)
    if mark is not None:
        mx, my = px + 4, py + 5
        fill_pixels(canvas, mx, my, mx + mark_size, my + mark_size, mark)


def placeholder_sprite(w: int, h: int, body: tuple, edge: tuple, mark: tuple | None) -> Image.Image:
    sprite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    placeholder(sprite, 0, 0, w, h, body, edge, mark)
    return sprite


# ---------------------------------------------------------------------------------------------------------------
# The three screens. Every window is in tiles; the same numbers go into data\\ui_layouts.json.


def screen_battle(canvas, palette, font, tiles, tab_tiles) -> dict:
    fill_rect(canvas, 0, 0, COLS, ROWS, palette[BLACK])

    # Battle background strip: the encounter terrain, flat bands only. Sky is the backdrop, ground is grey.
    fill_rect(canvas, 0, 12, COLS, 9, palette[GREY])
    dither_row(canvas, 12 * CELL, 0, FRAME_W, palette[BLACK], palette[GREY], height=2)

    msg = {"x": 0, "y": 0, "w": 32, "h": 4}
    cmd = {"x": 0, "y": 21, "w": 10, "h": 9}
    status = {"x": 11, "y": 21, "w": 21, "h": 9}
    for rect in (msg, cmd, status):
        draw_window(canvas, tiles, rect["x"], rect["y"], rect["w"], rect["h"])

    # Enemies: placeholder blocks on the left, over the strip.
    enemies = [
        {"x": 3, "y": 8, "w": 4, "h": 4},
        {"x": 12, "y": 11, "w": 4, "h": 4},
    ]
    for box in enemies:
        placeholder(canvas, box["x"] * CELL, box["y"] * CELL, box["w"] * CELL, box["h"] * CELL,
                    palette[GOLD], palette[WHITE])

    # Party: four 24x32 blocks stacked down the right edge, FF1 side view.
    party = [{"x": 28, "y": 4 + index * 4, "w": 3, "h": 4} for index in range(4)]
    for index, box in enumerate(party):
        placeholder(canvas, box["x"] * CELL, box["y"] * CELL, box["w"] * CELL, box["h"] * CELL,
                    palette[GREY], palette[WHITE], palette[GOLD])

    message = ["A STORM CLOUD BLOCKS THE ROAD.", "PERCY RAISES THE TRIDENT."]
    for index, line in enumerate(message):
        font.draw(canvas, msg["x"] + 1, msg["y"] + 1 + index, line, palette[WHITE])

    commands = ["FIGHT", "POWER", "TALK", "SPARE", "ITEM"]
    for index, label in enumerate(commands):
        font.draw(canvas, cmd["x"] + 3, cmd["y"] + 1 + index, label, palette[WHITE])
    cursor = {"x": cmd["x"] + 1, "y": cmd["y"] + 1}
    blit_tile(canvas, render_tile(ARROW, {"B": palette[GOLD]}), cursor["x"], cursor["y"])

    font.draw(canvas, status["x"] + 1, status["y"] + 1, "NAME      HP", palette[GOLD])
    for index, (name, hp) in enumerate((("KONRAD", 24), ("ZANDER", 18), ("PERCY", 31), ("HADRIAN", 21))):
        font.draw(canvas, status["x"] + 1, status["y"] + 2 + index, "%-7s HP %2d" % (name, hp), palette[WHITE])

    sprites = []
    sprites.extend({"x": b["x"] * CELL, "y": b["y"] * CELL, "w": b["w"] * CELL, "h": b["h"] * CELL,
                    "role": "party"} for b in party)
    sprites.extend({"x": b["x"] * CELL, "y": b["y"] * CELL, "w": b["w"] * CELL, "h": b["h"] * CELL,
                    "role": "enemy"} for b in enemies)
    sprites.append({"x": cursor["x"] * CELL, "y": cursor["y"] * CELL, "w": CELL, "h": CELL,
                    "role": "cursor", "transparent": "#0000bc"})

    return {
        "name": "battle",
        "windows": [
            {"name": "message", "x": msg["x"], "y": msg["y"], "w": msg["w"], "h": msg["h"], "style": "window"},
            {"name": "command", "x": cmd["x"], "y": cmd["y"], "w": cmd["w"], "h": cmd["h"], "style": "window"},
            {"name": "status", "x": status["x"], "y": status["y"], "w": status["w"], "h": status["h"],
             "style": "window"},
        ],
        "bands": [
            {"name": "sky", "x": 0, "y": 0, "w": 32, "h": 12, "colour": BLACK},
            {"name": "ground", "x": 0, "y": 12, "w": 32, "h": 9, "colour": GREY, "edge": "dither2"},
        ],
        "enemies": [{"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "pixels": "32x32"} for b in enemies],
        "party": [{"member": m, "x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "pixels": "24x32"}
                  for m, b in zip(("KONRAD", "ZANDER", "PERCY", "HADRIAN"), party)],
        "text": {
            "message": message,
            "commands": commands,
            "status_header": "NAME      HP",
            "status_rows": ["%-7s HP %2d" % (n, h) for n, h in
                            (("KONRAD", 24), ("ZANDER", 18), ("PERCY", 31), ("HADRIAN", 21))],
        },
        "cursors": [{"name": "command", "x": cursor["x"], "y": cursor["y"], "sprite": "spr_pp_ui_cursor"}],
        "sprites": sprites,
    }


def screen_dialogue(canvas, palette, font, tiles, tab_tiles) -> dict:
    fill_rect(canvas, 0, 0, COLS, ROWS, palette[BLACK])

    # Field: a grey ground band with a 2 px checker horizon. Flat bands only. The band stops one tile above
    # the dialogue window so it never shares a 16x16 area with the gold name tab (gold + grey would be a
    # fourth colour in that area).
    fill_rect(canvas, 0, 15, COLS, 3, palette[GREY])
    dither_row(canvas, 15 * CELL, 0, FRAME_W, palette[BLACK], palette[GREY], height=2)
    # A flat white path stone line inside the band, so the field is not an empty stripe.
    fill_pixels(canvas, 4 * CELL, 16 * CELL, 20 * CELL, 16 * CELL + 2, palette[WHITE])

    hero = {"x": 6, "y": 12, "w": 3, "h": 4}
    placeholder(canvas, hero["x"] * CELL, hero["y"] * CELL, hero["w"] * CELL, hero["h"] * CELL,
                palette[GREY], palette[WHITE], palette[GOLD])

    box = {"x": 0, "y": 21, "w": 32, "h": 9}
    draw_window(canvas, tiles, box["x"], box["y"], box["w"], box["h"])

    tab = {"x": 2, "y": 18, "w": 8, "h": 3}
    draw_window(canvas, tab_tiles, tab["x"], tab["y"], tab["w"], tab["h"])
    font.draw(canvas, tab["x"] + 1, tab["y"] + 1, "KONRAD", palette[WHITE])

    lines = ["THE TIDE IS TURNING, PERCY.", "DO YOU TRUST THE CLOUD?"]
    for index, line in enumerate(lines):
        font.draw(canvas, box["x"] + 1, box["y"] + 1 + index, line, palette[WHITE])

    arrow = {"x": 29, "y": 27}
    blit_tile(canvas, render_tile(ARROW, {"B": palette[GOLD]}), arrow["x"], arrow["y"])

    sprites = [
        {"x": hero["x"] * CELL, "y": hero["y"] * CELL, "w": hero["w"] * CELL, "h": hero["h"] * CELL,
         "role": "party"},
        {"x": arrow["x"] * CELL, "y": arrow["y"] * CELL, "w": CELL, "h": CELL, "role": "cursor",
         "transparent": "#0000bc"},
    ]
    return {
        "name": "dialogue",
        "windows": [
            {"name": "dialogue", "x": box["x"], "y": box["y"], "w": box["w"], "h": box["h"], "style": "window"},
            {"name": "nametab", "x": tab["x"], "y": tab["y"], "w": tab["w"], "h": tab["h"], "style": "tab"},
        ],
        "bands": [
            {"name": "sky", "x": 0, "y": 0, "w": 32, "h": 15, "colour": BLACK},
            {"name": "ground", "x": 0, "y": 15, "w": 32, "h": 3, "colour": GREY, "edge": "dither2"},
        ],
        "text": {"name": "KONRAD", "lines": lines},
        "cursors": [{"name": "continue", "x": arrow["x"], "y": arrow["y"], "blink": {"on_frames": 30,
                                                                                    "off_frames": 15}}],
        "sprites": sprites,
    }


def screen_menu(canvas, palette, font, tiles, tab_tiles) -> dict:
    fill_rect(canvas, 0, 0, COLS, ROWS, palette[BLACK])

    header = {"x": 0, "y": 0, "w": 32, "h": 3}
    party = {"x": 0, "y": 3, "w": 15, "h": 17}
    items = {"x": 16, "y": 3, "w": 16, "h": 17}
    save = {"x": 0, "y": 20, "w": 32, "h": 10}
    for rect in (header, party, items, save):
        draw_window(canvas, tiles, rect["x"], rect["y"], rect["w"], rect["h"])

    font.draw(canvas, header["x"] + 2, header["y"] + 1, "MENU", palette[GOLD])

    font.draw(canvas, party["x"] + 1, party["y"] + 1, "PARTY", palette[GOLD])
    members = [("KONRAD", 7, 24), ("ZANDER", 5, 18), ("PERCY", 6, 31), ("HADRIAN", 8, 21)]
    for index, (name, level, hp) in enumerate(members):
        font.draw(canvas, party["x"] + 1, party["y"] + 3 + index * 2,
                  "%-7s L%d" % (name, level), palette[WHITE])
        font.draw(canvas, party["x"] + 1, party["y"] + 4 + index * 2, "HP %2d" % hp, palette[WHITE])

    font.draw(canvas, items["x"] + 1, items["y"] + 1, "ITEMS", palette[GOLD])
    inventory = ["POTION   3", "ETHER    2", "SICKLE   1", "TRIDENT  1", "MAP      1"]
    for index, line in enumerate(inventory):
        font.draw(canvas, items["x"] + 2, items["y"] + 3 + index, line, palette[WHITE])

    font.draw(canvas, save["x"] + 1, save["y"] + 1, "SAVE GAME?", palette[WHITE])
    font.draw(canvas, save["x"] + 4, save["y"] + 4, "YES", palette[WHITE])
    font.draw(canvas, save["x"] + 12, save["y"] + 4, "NO", palette[WHITE])
    cursor = {"x": save["x"] + 2, "y": save["y"] + 4}
    blit_tile(canvas, render_tile(ARROW, {"B": palette[GOLD]}), cursor["x"], cursor["y"])

    sprites = [{"x": cursor["x"] * CELL, "y": cursor["y"] * CELL, "w": CELL, "h": CELL, "role": "cursor",
                "transparent": "#0000bc"}]
    return {
        "name": "menu",
        "windows": [
            {"name": "header", "x": header["x"], "y": header["y"], "w": header["w"], "h": header["h"],
             "style": "window"},
            {"name": "party", "x": party["x"], "y": party["y"], "w": party["w"], "h": party["h"],
             "style": "window"},
            {"name": "items", "x": items["x"], "y": items["y"], "w": items["w"], "h": items["h"],
             "style": "window"},
            {"name": "save", "x": save["x"], "y": save["y"], "w": save["w"], "h": save["h"], "style": "window"},
        ],
        "bands": [],
        "text": {
            "header": "MENU",
            "party": ["%-7s L%d" % (n, l) for n, l, _ in members],
            "party_hp": ["HP %2d" % h for _, _, h in members],
            "items": inventory,
            "save": ["SAVE GAME?", "YES", "NO"],
        },
        "cursors": [{"name": "save_yes", "x": cursor["x"], "y": cursor["y"]}],
        "sprites": sprites,
    }


def validate_layout(layout: dict) -> list:
    """Numbers a reviewer can check without seeing the screen: windows on the frame, text inside the interior."""
    problems = []
    for window in layout["windows"]:
        if window["x"] < 0 or window["y"] < 0:
            problems.append("%s starts off frame" % window["name"])
        if window["x"] + window["w"] > COLS or window["y"] + window["h"] > ROWS:
            problems.append("%s runs off frame: %d,%d %dx%d" % (window["name"], window["x"], window["y"],
                                                                window["w"], window["h"]))
        if window["w"] < 3 or window["h"] < 3:
            problems.append("%s is smaller than its own border" % window["name"])
    text = layout.get("text", {})
    boxes = {window["name"]: window for window in layout["windows"]}
    limits = []
    if layout["name"] == "battle":
        limits.append((boxes["message"], text["message"], 1))
        limits.append((boxes["command"], text["commands"], 3))
        limits.append((boxes["status"], text["status_rows"] + [text["status_header"]], 1))
    elif layout["name"] == "dialogue":
        limits.append((boxes["dialogue"], text["lines"], 1))
        limits.append((boxes["nametab"], [text["name"]], 1))
    elif layout["name"] == "menu":
        limits.append((boxes["party"], text["party"] + text["party_hp"] + ["PARTY"], 1))
        limits.append((boxes["items"], text["items"] + ["ITEMS"], 2))
        limits.append((boxes["save"], text["save"], 4))
    for box, lines, indent in limits:
        for line in lines:
            if len(line) + indent > box["w"] - 1:
                problems.append("%s: %r needs %d tiles, the interior is %d"
                                % (box["name"], line, len(line) + indent, box["w"] - 2))
        if len(lines) + 2 > box["h"]:
            problems.append("%s: %d text rows do not fit an interior of %d rows"
                            % (box["name"], len(lines), box["h"] - 2))
    return problems


def ascii_map(canvas: Image.Image, palette: dict) -> str:
    """One character per tile: the frame as text, for an author or reviewer who cannot see the PNG.

    '#' window fill, 'W' white ink (border, text), '*' the accent (cursor, heading, name tab, marker),
    '.' grey band, ' ' backdrop. A tile that holds any accent reads '*', a tile with 8 or more white
    pixels reads 'W', otherwise the tile reads as its most common colour. The gold marker on a grey
    party block and the white glyph on a blue interior both show up this way.
    """
    symbols = {palette[FILL][:3]: "#", palette[WHITE][:3]: "W", palette[GREY][:3]: ".",
               palette[GOLD][:3]: "*", palette[BLACK][:3]: " "}
    pixels = canvas.load()
    rows = []
    for ty in range(ROWS):
        line = []
        for tx in range(COLS):
            counts = {}
            for y in range(ty * CELL, ty * CELL + CELL):
                for x in range(tx * CELL, tx * CELL + CELL):
                    rgb = pixels[x, y][:3]
                    symbol = symbols.get(rgb, "?")
                    counts[symbol] = counts.get(symbol, 0) + 1
            if counts.get("*"):
                line.append("*")
            elif counts.get("W", 0) >= 8:
                line.append("W")
            else:
                line.append(max(counts.items(), key=lambda item: (item[1], item[0]))[0])
        rows.append("".join(line))
    return "\n".join(rows)


# ---------------------------------------------------------------------------------------------------------------
# Output.


def save_sheet(image: Image.Image, out_dir: str, name: str, extra: dict) -> tuple:
    path = os.path.join(out_dir, name + ".png")
    image.save(path)
    payload = {"name": name, "frame_w": image.width, "frame_h": image.height,
               "frames": max(1, image.width // image.height)}
    payload.update(extra)
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return path, payload


def save_frame(canvas: Image.Image, root: str, layout: dict) -> tuple:
    screens_dir = os.path.join(root, "game", "sprites_src", "ui", "screens")
    os.makedirs(screens_dir, exist_ok=True)
    base = "ui_" + layout["name"]
    png = os.path.join(screens_dir, base + ".png")
    canvas.save(png)
    with open(os.path.join(screens_dir, base + ".json"), "w", encoding="utf-8") as handle:
        json.dump(layout, handle, indent=2)
        handle.write("\n")
    with open(os.path.join(screens_dir, base + "_sprites.json"), "w", encoding="utf-8") as handle:
        json.dump({"sprites": layout["sprites"]}, handle, indent=2)
        handle.write("\n")
    preview_dir = os.path.join(root, "output")
    os.makedirs(preview_dir, exist_ok=True)
    preview = os.path.join(preview_dir, base + "_preview.png")
    canvas.resize((FRAME_W * SCALE, FRAME_H * SCALE), NEAREST).save(preview)
    return png, preview


def scene_palette(table: dict) -> dict:
    def rgb(code):
        r, g, b, _ = table[code]
        return "#%02x%02x%02x" % (r, g, b)

    def group(name, codes):
        return {"name": name, "colours": codes, "hex": [rgb(c) for c in codes]}

    return {
        "format": 1,
        "kind": "scene_palette",
        "scene": "ui",
        "backdrop": BLACK,
        "rule": ("NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, "
                 "4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is a "
                 "data/nes_palette.json entry number"),
        "notes": [
            "written by tools/art/make_ui_nes.py for the UI-NES card; the card that asked for the screens owns this file",
            "backdrop $0F black is the shared backdrop of all three screens",
            "bg0 is the window itself: the fill $02 and a 2 px border plus the text in $30",
            "bg1 is the accent: gold $28 with the blue fill and the white text (name tab, gold headings)",
            "bg2 is the placeholder blocks: white edge, grey body, gold marker",
            "bg3 is spare and unused; the screens need 3 background palettes",
            "sp0 covers the cursor and the enemy block (black $0F, gold $28, white $30)",
            "sp1 covers the party block (grey $00, white $30, gold $28)",
            "sp2 and sp3 are spare; the screens need 2 sprite palettes",
        ],
        "background": [
            group("bg0", [FILL, WHITE, GREY]),
            group("bg1", [FILL, WHITE, GOLD]),
            group("bg2", [WHITE, GREY, GOLD]),
            group("bg3", [FILL, GREY, GOLD]),
        ],
        "sprites": [
            group("sp0", [BLACK, GOLD, WHITE]),
            group("sp1", [GREY, WHITE, GOLD]),
            group("sp2", [FILL, WHITE, GOLD]),
            group("sp3", [FILL, GREY, WHITE]),
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="draw the NES JRPG UI: window tiles, three screens, layouts")
    parser.add_argument("--root", default=None, help="repository root; default is the parent of tools")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root) if args.root else repo_root()
    table = load_nes_palette(root)
    palette = {code: table[code] for code in (FILL, WHITE, GREY, GOLD, BLACK)}
    palette[BLACK] = (palette[BLACK][0], palette[BLACK][1], palette[BLACK][2], 255)

    out_dir = os.path.join(root, "game", "sprites_src", "ui")
    os.makedirs(out_dir, exist_ok=True)

    window_colours = {"W": palette[WHITE], "G": palette[GREY], "B": palette[FILL]}
    tab_colours = {"W": palette[GOLD], "G": palette[GOLD], "B": palette[FILL]}

    window_slices = build_slices(WINDOW_SLICES, WINDOW_ORDER)
    tab_slices = build_slices(WINDOW_SLICES, TAB_ORDER)

    window_sheet = build_sheet(window_slices, window_colours)
    tab_sheet = build_sheet(tab_slices, tab_colours)

    cursor_sheet = Image.new("RGBA", (CELL * 2, CELL), (0, 0, 0, 0))
    cursor_sheet.paste(render_tile(ARROW, {"B": palette[GOLD]}), (0, 0))

    party_sheet = placeholder_sprite(24, 32, palette[GREY], palette[WHITE], palette[GOLD])
    enemy_sheet = placeholder_sprite(32, 32, palette[GOLD], palette[WHITE], None)

    slices_json = {"tiles": WINDOW_ORDER,
                   "tile_size": CELL,
                   "layout": "row major: tl t tr l c r bl b br, 8x8 each",
                   "nine_slice": {"corner": ["tl", "tr", "bl", "br"], "edge": ["t", "b", "l", "r"],
                                  "fill": ["c"]}}
    save_sheet(window_sheet, out_dir, "spr_pp_ui_window",
               dict(slices_json, role="menu, dialogue, command and status window",
                    colours={"border": WHITE, "fill": FILL},
                    rule="3 colours per 8x8 tile, transparent corner pixel"))
    save_sheet(tab_sheet, out_dir, "spr_pp_ui_tab",
               dict(slices_json, role="dialogue name tab, same nine slices in the accent colour",
                    colours={"border": GOLD, "inner": GOLD, "fill": FILL},
                    rule="3 colours per 8x8 tile, transparent corner pixel"))
    save_sheet(cursor_sheet, out_dir, "spr_pp_ui_cursor",
               {"frames_detail": ["arrow", "blank (the off phase of the blink)"], "fps": 2.0,
                "colours": {"arrow": GOLD}, "rule": "one colour plus transparency; 1 sprite per scanline"})
    save_sheet(party_sheet, out_dir, "spr_pp_ui_party",
               {"frames_detail": ["idle placeholder"], "pixels": "24x32",
                "colours": {"edge": WHITE, "body": GREY, "marker": GOLD},
                "rule": "24x32 is 3x4 tiles, 3 sprites wide by 4 tall; 3 colours per tile"})
    save_sheet(enemy_sheet, out_dir, "spr_pp_ui_enemy",
               {"frames_detail": ["idle placeholder"], "pixels": "32x32",
                "colours": {"edge": WHITE, "body": GOLD}, "rule": "32x32 is 4x4 tiles; 2 colours per tile"})

    font = Font(root)
    tiles = {name: render_tile(rows, window_colours) for name, rows in window_slices}
    tab_tiles = {name: render_tile(rows, tab_colours) for name, rows in tab_slices}

    layouts = {"format": 1, "kind": "ui_layouts", "frame": {"w": FRAME_W, "h": FRAME_H, "tile": CELL,
                                                            "cols": COLS, "rows": ROWS},
               "grid": "tile coordinates: x, y, w, h are whole 8x8 tiles",
               "nine_slice": {
                   "sheet": "game/sprites_src/ui/spr_pp_ui_window.png",
                   "tile_order": "tl t tr l c r bl b br, 8x8 each, row major",
                   "corner": ["tl", "tr", "bl", "br"],
                   "edge": ["t", "b", "l", "r"],
                   "fill": ["c"],
                   "border_ring_tiles": 1,
                   "border_line_px": 2,
                   "note": ("the border ring is one whole 8x8 tile on every side; the 2 px white line is drawn on the "
                            "outer edge of that ring and the rest of the ring is the fill colour, so the text interior "
                            "is exactly (w-2) x (h-2) whole tiles and text starts at tile x+1, y+1. Any w>=3, h>=3 "
                            "works: corners, edges and fill are independent tiles"),
                   "tab": "game/sprites_src/ui/spr_pp_ui_tab.png, the same nine slices with the border in the accent",
               },
               "safe_area": {
                   "overscan_px": 8,
                   "text_inset": ("no glyph falls in the outer 8 px of the top or bottom: the lowest text row is tile 25 "
                                  "(y 200..208) and the highest is tile 1 (y 8..16). Window borders do reach the frame "
                                  "edge, which is what FF1's edge to edge message box does"),
               },
               "checks": {
                   "hardware": "tools/nes_check.py --type background (16x16 areas, 3 colours plus backdrop) and --type sprite (8x8 tiles, 3 colours plus transparent)",
                   "frame": "tools/nes_composite_check.py <frame.png> --sprites <frame_sprites.json> --backdrop 15 (background palettes, sprite palettes, sprites per scanline)",
                   "levels": "output/ui_checks/<screen>_bg.json, <screen>_composite.json",
                   "art_bible": "C1 to C6 by tool; C7 C12 C13 by this nine_slice contract; C11 one backdrop ($0F); C15 party block palette (grey, white, gold) differs from enemy (gold, white)",
               },
               "font": {"name": "spr_pp_font8", "cell": "8x8",
                        "glyphs": "".join(GLYPHS), "path": "game/sprites_src/title/spr_pp_font8.png"},
               "colours": {"fill": FILL, "border": WHITE, "text": WHITE, "accent": GOLD,
                           "backdrop": BLACK},
               "palettes": "data/palettes/scene_ui.json",
               "windows": {name: os.path.join("game", "sprites_src", "ui", name + ".png")
                           for name in ("spr_pp_ui_window", "spr_pp_ui_tab")},
               "sprites": {name: os.path.join("game", "sprites_src", "ui", name + ".png")
                           for name in ("spr_pp_ui_cursor", "spr_pp_ui_party", "spr_pp_ui_enemy")},
               "screens": []}

    builders = (("battle", screen_battle), ("dialogue", screen_dialogue), ("menu", screen_menu))
    problems = []
    for name, builder in builders:
        canvas = new_frame(palette[BLACK])
        layout = builder(canvas, palette, font, tiles, tab_tiles)
        problems.extend("%s: %s" % (name, line) for line in validate_layout(layout))
        png, preview = save_frame(canvas, root, layout)
        layout["frame_png"] = os.path.relpath(png, root).replace("\\", "/")
        layout["preview_png"] = os.path.relpath(preview, root).replace("\\", "/")
        layout["preview_scale"] = SCALE
        layouts["screens"].append(layout)
        tiles_path = os.path.join(root, "output", "ui_%s_tiles.txt" % name)
        with open(tiles_path, "w", encoding="utf-8") as handle:
            handle.write(ascii_map(canvas, palette) + "\n")
        print("screen %-9s windows %d sprites %d colours %d -> %s"
              % (name, len(layout["windows"]), len(layout["sprites"]),
                 len({canvas.getpixel((x, y))[:3] for y in range(0, FRAME_H, 3) for x in range(0, FRAME_W, 3)}),
                 os.path.relpath(png, root)))

    if problems:
        for line in problems:
            print("LAYOUT PROBLEM " + line)
        return 1

    with open(os.path.join(root, "data", "ui_layouts.json"), "w", encoding="utf-8") as handle:
        json.dump(layouts, handle, indent=2)
        handle.write("\n")

    palettes_dir = os.path.join(root, "data", "palettes")
    os.makedirs(palettes_dir, exist_ok=True)
    with open(os.path.join(palettes_dir, "scene_ui.json"), "w", encoding="utf-8") as handle:
        json.dump(scene_palette(table), handle, indent=2)
        handle.write("\n")

    print("wrote game/sprites_src/ui/ (5 sheets + screens), data/ui_layouts.json, data/palettes/scene_ui.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
