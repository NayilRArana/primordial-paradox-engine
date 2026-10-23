#!/usr/bin/env python3
"""make_quay_tiles.py: the exterior tile set for the quay block and the dock office (card R46, t_abfb6024).

What this draws, and to which rules:

1. Nineteen 16x16 tiles that read as a south coast quay after dark, plus the office floor and desk the interior
   scene stands on: wet quay paving, a puddle, the quay edge, two water frames, an iron bollard, a chain, a steel
   barrier, a brick wall, a damp brick wall, the one door that opens, a shut door, a lit window, a dark window,
   a lamp post base, a sign board, office boards and an office desk.
2. Every pixel is an output of the Ricoh 2C02. The sheet is drawn through the four background palettes the quay
   night set spends, one palette per tile, three colours per palette plus the shared backdrop $0F black, so no
   16x16 area carries more than three colours besides the backdrop. That is the same budget `tools/nes_check.py`
   and `tools/nes_composite_check.py` measure, so the audit is the check and not the opinion.
3. Colours are named as ROLES, not hex. The role names are the ones in `data/palette.json` (`grey_4`, `sea_1`,
   `blood_3`, `gold_5` and so on). That file names a 54 colour design palette whose hex values are not 2C02
   outputs, so this tool carries the bridge: ROLE_ENTRY resolves each role to the PPU entry that reads as it,
   and the bridge is written into the manifest so a reader can audit the mapping instead of trusting it.
4. No anti aliasing: every pixel is a palette entry, drawn on the 16x16 cell, with no blended or intermediate
   tone anywhere. There is no outline outside the cell, because a background tile is a full cell: the tile edge
   is the tile edge.
5. The blob test of `knowledge/SPRITE-CRAFT.md` section 8.5 is applied per tile: the share of the lightest tone,
   the rows with no dark pixel, the horizontal dark runs, and the dark pixels inside the silhouette. The numbers
   are written into the manifest for every tile. Object tiles are gated on it; pattern tiles (paving, water,
   brick) and the three light source tiles (lit window, lamp, sign) are reported and their waivers are named,
   because the rule was written for a 14x15 character silhouette and a wall is structure by repetition.

Outputs:
    game/sprites_src/env/quay/quay_tiles.png          the sheet, 8 by 3 cells of 16x16, 19 tiles used
    game/sprites_src/env/quay/quay_tiles.json         the tileset manifest: palettes, roles, tiles, blob numbers
    game/sprites_src/env/quay/TILES.md                the tile table the map wiring reads (name, character, roles)
    output/quay_tiles_3x.png                          3x contact sheet to look at
    output/quay_block_preview.png                     256x240 mock of the block, composed from the sheet
    output/quay_block_preview.json                    its declared backdrop, so the frame audit reads it right
    output/quay_office_preview.png                    256x240 mock of the dock office, composed from the sheet
    output/quay_office_preview.json                   its declared backdrop

The art root is `game/sprites_src/env/`, where every tileset in this project lives and where
`tools/nes_audit_all.py` and `tools/sync_art.py` look; the card's `assets/tiles/quay/` names the same folder and
the handoff notes the difference.

Usage:
    python tools/art/make_quay_tiles.py
    python tools/art/make_quay_tiles.py --check        # write nothing, exit 1 if the PNG on disk is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "game", "sprites_src", "env", "quay")
SHEET_PNG = os.path.join(OUT_DIR, "quay_tiles.png")
SHEET_JSON = os.path.join(OUT_DIR, "quay_tiles.json")
TILES_MD = os.path.join(OUT_DIR, "TILES.md")
OUTPUT = os.path.join(ROOT, "output")

TILE = 16
COLUMNS = 8
BACKDROP_ROLE = "ink"

# -----------------------------------------------------------------------------------------------------------------
# The palette bridge: role name -> the 2C02 entry that reads as that role.
#
# data/palette.json names 54 design colours by hue family and level (grey_0 to blood_5) and by role (ink, window,
# accent). Its hex values are not 2C02 outputs, and the audit's authority on a colour is data/nes_palette.json, so
# each role this set uses is resolved here to one entry, chosen as the nearest output in the role's own family at
# the value the art needs. The reason column is why that entry and not another one.

ROLE_ENTRY = {
    "ink": (15, "the canonical black $0F, the shared backdrop of every area in both sets"),
    "grey_4": (0, "$00 #7c7c7c is the one neutral mid grey in the 2C02 and it is the wet quay stone"),
    "grey_5": (16, "$10 #bcbcbc is the lighter neutral, the sheen a wet slab keeps on its lit edge"),
    "sea_1": (12, "$0C #004058 is the darkest cool output, the wet shadow in a joint and the deep water"),
    "sea_2": (28, "$1C #008888 is the harbour's mid swell, one step above the deep water"),
    "sea_4": (44, "$2C #00e8d8 is the brightest teal, a two pixel glint on a swell and nothing more"),
    "blood_3": (7, "$07 #881400 is the dark brick face and the lit edge of iron after dark"),
    "stone_2": (8, "$08 #503000 is the brown one step under the brick, mortar and the iron body"),
    "blood_4": (23, "$17 #e45c10 is the brick face under the lamp and the paint on the barrier rail"),
    "gold_4": (40, "$28 #f8b800 is lamp glass and the lit window's fill"),
    "gold_5": (56, "$38 #f8d878 is the hot core of a window and the lettering on the sign"),
}

# The two room palette sets this card exists to serve. Both are inside the 16 role cap of
# data/room_palettes.json. ARRIVAL-MAP-2 (t_db2995d7) appends them to that file; this card may not edit data.
SETS = {
    "quay_night": ["ink", "grey_4", "grey_5", "sea_1", "sea_2", "sea_4", "blood_3", "stone_2", "blood_4",
                   "gold_4", "gold_5"],
    "office_night": ["ink", "grey_4", "grey_5", "sea_1", "sea_2", "blood_3", "stone_2", "blood_4",
                     "gold_4", "gold_5"],
}

# The four background palettes of the quay night set: three roles each, one shared backdrop. A tile draws from
# exactly one of them, so a 16x16 area can never carry a fourth colour.
BG_PALETTES = [
    ("bg0_quay_stone", ["grey_4", "grey_5", "sea_1"],
     "wet paving, the coping and the iron that stands on the stone, drawn in the stone's own ramp"),
    ("bg1_harbour_water", ["sea_1", "sea_2", "sea_4"],
     "the harbour: deep water, one step of swell, a glint"),
    ("bg2_brick_iron", ["blood_3", "stone_2", "blood_4"],
     "the brick frontage, its mortar, and the doors and wood in the same warm ramp"),
    ("bg3_lamp_glass", ["gold_4", "gold_5", "stone_2"],
     "the light sources: a lit window, the lamp, the sign, with the dark brown that frames them"),
]

PALETTE_OF_ROLE = {}
for _name, _roles, _note in BG_PALETTES:
    for _role in _roles:
        PALETTE_OF_ROLE[_role] = _name


# -----------------------------------------------------------------------------------------------------------------
# A 16x16 canvas of role names. None is the backdrop.

class Canvas:
    def __init__(self):
        self.px = [[None] * TILE for _ in range(TILE)]

    def fill(self, role):
        for y in range(TILE):
            for x in range(TILE):
                self.px[y][x] = role

    def rect(self, x0, y0, w, h, role):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if 0 <= x < TILE and 0 <= y < TILE:
                    self.px[y][x] = role

    def put(self, x, y, role):
        if 0 <= x < TILE and 0 <= y < TILE:
            self.px[y][x] = role

    def hline(self, y, x0, x1, role):
        for x in range(x0, x1 + 1):
            self.put(x, y, role)

    def vline(self, x, y0, y1, role):
        for y in range(y0, y1 + 1):
            self.put(x, y, role)

    def rows(self):
        return self.px


# -----------------------------------------------------------------------------------------------------------------
# Grounds.

def paving(c, sheen="grey_5"):
    """Wet flagstones: joints in the darkest stone tone, a lit course on the top of every slab."""
    c.fill("grey_4")
    for y in (0, 8):
        c.hline(y, 0, 15, "sea_1")
    for x in (0, 8):
        c.vline(x, 0, 15, "sea_1")
    # the sheen runs course by course but never over a joint, so no row loses its dark pixel: the
    # blob test in SPRITE-CRAFT section 8.5 asks for zero rows without one
    for y in (1, 9):
        for x in range(0, 16):
            if x not in (0, 8):
                c.put(x, y, sheen)
    for (sx, sy) in ((1, 2), (9, 2), (1, 10), (9, 10)):
        c.vline(sx, sy, sy + 4, sheen)


def brick_course(c, top, offset_start, lit=True):
    """One 8 row course: a 1 px mortar line, then bricks with a lit top edge."""
    c.hline(top, 0, 15, "stone_2")
    if lit:
        c.hline(top + 1, 0, 15, "blood_4")
    for y in range(top + 2, top + 8):
        pass
    c.rect(0, top + 2, 16, 5, "blood_3")
    if lit:
        c.hline(top + 2, 0, 15, "blood_4")
    for x in offset_start:
        c.vline(x, top + 1, top + 7, "stone_2")


# -----------------------------------------------------------------------------------------------------------------
# The nineteen tiles.

def t_quay_paving(c):
    paving(c)


def t_quay_paving_worn(c):
    paving(c)
    # a crack that steps one pixel at a time, the pattern the craft file asks for instead of a jaggy
    for (x, y) in ((3, 2), (4, 3), (4, 4), (5, 4), (5, 5), (6, 5), (6, 6), (7, 6)):
        c.put(x, y, "sea_1")
    c.put(13, 11, "sea_1")
    c.put(14, 11, "sea_1")
    c.put(13, 12, "sea_1")


def t_quay_puddle(c):
    paving(c)
    # standing water in the low corner of a slab: dark, with the lamp path across it in two glints
    for y in range(6, 10):
        for x in range(2, 14):
            if y in (6, 9) and x in (2, 13):
                continue
            c.put(x, y, "sea_1")
    c.hline(7, 5, 7, "grey_5")
    c.hline(8, 9, 10, "grey_5")
    c.put(3, 7, "grey_5")
    c.put(12, 8, "grey_5")


def t_quay_edge(c):
    """The coping stone at the water: paving above, a lit wet lip, then the drop into black water."""
    paving(c)
    c.hline(11, 0, 15, "grey_5")
    c.hline(12, 0, 15, "grey_4")
    c.rect(0, 13, 16, 3, "sea_1")
    for x in range(0, 16, 3):
        c.put(x, 13, "grey_4")


def t_water_deep(c):
    c.fill("sea_1")
    for (y, x0) in ((2, 2), (2, 11), (5, 1), (5, 10), (8, 4), (8, 12), (13, 3), (13, 10)):
        c.hline(y, x0, x0 + 1, "sea_2")
    for (y, x0) in ((3, 3), (10, 5), (14, 11)):
        c.hline(y, x0, x0 + 1, "sea_4")
    c.hline(1, 6, 8, "sea_2")


def t_water_ripple(c):
    c.fill("sea_1")
    for (y, x0) in ((2, 5), (2, 13), (5, 4), (5, 11), (9, 2), (9, 9), (13, 6), (13, 14)):
        c.hline(y, x0, x0 + 1, "sea_2")
    for (y, x0) in ((4, 7), (11, 12), (14, 3)):
        c.hline(y, x0, x0 + 1, "sea_4")
    c.hline(7, 3, 4, "sea_2")


def t_bollard(c):
    """An iron bollard on wet stone: a wide base, a shaft, one lit edge where the lamp reaches it."""
    paving(c)
    c.rect(3, 12, 10, 3, "sea_1")
    c.hline(12, 3, 12, "grey_5")
    c.rect(5, 2, 6, 2, "sea_1")
    c.put(5, 2, "grey_5")
    c.put(6, 2, "grey_5")
    c.rect(6, 4, 4, 8, "sea_1")
    c.vline(6, 4, 11, "grey_5")
    c.put(9, 8, "grey_5")


def t_chain(c):
    """A chain draped between two bollards: one arc that meets the tile edge at both ends."""
    paving(c)
    drape = [6, 7, 7, 8, 8, 8, 9, 9, 9, 8, 8, 8, 7, 7, 6, 6]
    for x, y in enumerate(drape):
        c.put(x, y, "sea_1")
    for x in (1, 4, 7, 10, 13):
        c.put(x, drape[x] + 1, "sea_1")
    for x in (2, 5, 8, 11, 14):
        c.put(x, drape[x] - 1, "grey_5")
    c.put(8, 10, "sea_1")


def t_barrier(c):
    """A steel barrier on the quay: a painted rail, two posts, the gap under it in shadow."""
    paving(c)
    c.rect(0, 4, 16, 3, "grey_4")
    c.hline(4, 0, 15, "grey_4")
    c.hline(5, 0, 15, "grey_5")
    c.hline(6, 0, 15, "sea_1")
    c.put(0, 4, "sea_1")
    c.put(8, 4, "sea_1")
    c.put(0, 5, "sea_1")
    c.put(8, 5, "sea_1")
    for x in (2, 3, 12, 13):
        c.vline(x, 4, 13, "grey_4")
    c.vline(2, 4, 13, "grey_5")
    c.vline(12, 4, 13, "grey_5")
    c.hline(13, 2, 3, "sea_1")
    c.hline(13, 12, 13, "sea_1")
    c.put(7, 5, "grey_5")
    c.put(8, 5, "sea_1")


def t_brick_wall(c):
    c.fill("blood_3")
    c.hline(0, 0, 15, "stone_2")
    c.hline(1, 0, 15, "blood_4")
    c.rect(0, 2, 16, 5, "blood_3")
    c.hline(2, 0, 15, "blood_4")
    for x in (0, 8):
        c.vline(x, 1, 7, "stone_2")
    c.hline(4, 0, 15, "blood_3")
    c.hline(8, 0, 15, "stone_2")
    c.hline(9, 0, 15, "blood_4")
    c.rect(0, 10, 16, 5, "blood_3")
    c.hline(10, 0, 15, "blood_4")
    for x in (4, 12):
        c.vline(x, 9, 15, "stone_2")
    c.hline(12, 0, 15, "blood_3")


def t_brick_wall_damp(c):
    t_brick_wall(c)
    # damp: two bricks gone dark where the rain runs, and one lit brick lost its edge
    c.rect(2, 10, 2, 5, "stone_2")
    c.rect(3, 12, 1, 3, "stone_2")
    c.rect(10, 2, 2, 3, "stone_2")
    c.put(5, 2, "blood_3")
    c.put(6, 2, "blood_3")
    c.put(13, 13, "stone_2")


def t_door_office(c):
    """The one door in the block that opens: shut, so it is the handle and the frame that say door."""
    c.fill("blood_3")
    c.hline(0, 0, 15, "stone_2")
    c.hline(1, 0, 15, "blood_4")
    c.rect(2, 2, 12, 12, "stone_2")
    c.rect(3, 3, 10, 10, "blood_3")
    c.vline(3, 3, 12, "blood_4")
    c.hline(3, 3, 12, "blood_4")
    c.hline(7, 5, 10, "stone_2")
    c.hline(10, 5, 10, "stone_2")
    c.put(11, 8, "blood_4")
    c.put(11, 9, "blood_4")
    c.hline(14, 2, 13, "stone_2")
    c.hline(15, 0, 15, "ink")
    c.put(0, 1, "stone_2")
    c.put(15, 1, "stone_2")


def t_door_shut(c):
    """A shut door: same frame, boarded across, no handle light."""
    c.fill("blood_3")
    c.hline(0, 0, 15, "stone_2")
    c.hline(1, 0, 15, "blood_4")
    c.rect(2, 2, 12, 12, "stone_2")
    c.rect(3, 3, 10, 10, "blood_3")
    c.vline(3, 3, 12, "stone_2")
    c.vline(12, 3, 12, "stone_2")
    c.hline(5, 3, 12, "stone_2")
    c.hline(9, 3, 12, "stone_2")
    c.hline(6, 4, 11, "blood_4")
    c.hline(10, 4, 11, "blood_4")
    c.hline(14, 2, 13, "stone_2")
    c.hline(15, 0, 15, "ink")
    c.put(0, 1, "stone_2")
    c.put(15, 1, "stone_2")


def t_window_lit(c):
    """A lit window: the room in gold, the hot core top left, the frame in the set's dark brown."""
    c.fill("stone_2")
    c.rect(2, 2, 12, 11, "gold_4")
    c.rect(3, 3, 6, 4, "gold_5")
    c.vline(8, 2, 12, "stone_2")
    c.hline(7, 2, 13, "stone_2")
    c.put(11, 9, "gold_5")
    c.put(4, 10, "gold_5")
    c.hline(0, 0, 15, "ink")
    c.hline(13, 1, 14, "stone_2")
    c.hline(14, 1, 14, "ink")
    c.hline(15, 0, 15, "ink")


def t_window_dark(c):
    """The same window with nobody home: glass in the dark ramp, one grudging sheen."""
    c.fill("stone_2")
    c.rect(2, 2, 12, 11, "blood_3")
    c.vline(8, 2, 12, "stone_2")
    c.hline(7, 2, 13, "stone_2")
    c.put(4, 4, "blood_4")
    c.hline(0, 0, 15, "ink")
    c.hline(13, 1, 14, "stone_2")
    c.hline(14, 1, 14, "blood_3")
    c.hline(15, 0, 15, "ink")


def t_lamp_base(c):
    """A lamp post and the pool it throws: the only tile whose bright fill is the point."""
    c.fill("ink")
    c.rect(7, 0, 2, 8, "stone_2")
    c.vline(7, 1, 7, "gold_4")
    c.rect(6, 8, 4, 3, "stone_2")
    c.hline(8, 6, 9, "gold_4")
    for x in range(1, 15):
        c.put(x, 11, "gold_4")
    for x in range(3, 13):
        c.put(x, 12, "gold_4")
    for x in range(5, 11):
        c.put(x, 13, "gold_5")
    c.hline(14, 6, 9, "gold_4")
    c.put(2, 12, "gold_5")
    c.put(13, 12, "gold_5")
    c.put(6, 10, "gold_4")
    c.put(9, 10, "gold_4")


def t_water_reflection(c):
    """What a lamp does to harbour water: a broken vertical glint path, nothing else."""
    c.fill("sea_1")
    for y in range(1, 15):
        c.put(7, y, "sea_2")
    for y in (2, 5, 8, 11, 14):
        c.put(7, y, "sea_4")
        c.put(8, y, "sea_4")
    for y in (4, 7, 10, 13):
        c.put(6, y, "sea_2")
        c.put(9, y, "sea_2")
    c.put(11, 6, "sea_4")
    c.put(4, 9, "sea_4")


def t_sign_board(c):
    """A harbour sign: dark board, gold face, two rows of lettering. No words at 16 px, only dashes."""
    c.fill("ink")
    c.rect(1, 2, 14, 10, "stone_2")
    c.rect(2, 3, 12, 8, "gold_4")
    for x in (4, 6, 8, 10):
        c.put(x, 5, "gold_5")
    for x in (4, 6, 8):
        c.put(x, 8, "gold_5")
    c.put(10, 8, "gold_5")
    c.hline(0, 4, 11, "ink")
    c.rect(4, 12, 1, 3, "stone_2")
    c.rect(11, 12, 1, 3, "stone_2")


def t_office_floor(c):
    """Boards: a lit top edge, a dark joint, nail heads where the joist is."""
    c.fill("blood_3")
    for y in (0, 4, 8, 12):
        c.hline(y, 0, 15, "blood_4")
        c.put(0, y, "stone_2")
        c.put(15, y, "stone_2")
    for y in (3, 7, 11, 15):
        c.hline(y, 0, 15, "stone_2")
    # a nail head on every board row, so a row of plain board still has its dark pixel
    for y, x in ((1, 5), (2, 12), (5, 8), (6, 2), (9, 10), (10, 6), (13, 3), (14, 13)):
        c.put(x, y, "stone_2")


def t_office_desk(c):
    """A desk on boards, seen from the front: a lit top, a dark panel, a drawer, legs in shadow."""
    t_office_floor(c)
    c.hline(3, 1, 14, "stone_2")
    c.rect(2, 4, 12, 2, "blood_4")
    c.put(1, 4, "stone_2")
    c.put(14, 4, "stone_2")
    c.put(1, 5, "stone_2")
    c.put(14, 5, "stone_2")
    c.hline(6, 1, 14, "stone_2")
    c.rect(3, 6, 10, 5, "blood_3")
    c.hline(7, 4, 11, "stone_2")
    c.hline(9, 6, 9, "stone_2")
    c.rect(1, 6, 2, 8, "stone_2")
    c.rect(13, 6, 2, 8, "stone_2")
    c.put(4, 8, "blood_4")
    c.put(11, 8, "blood_4")


# name, character for the map, palette, painter, gate on the blob test, note
TILES = [
    ("quay_paving", ".", "bg0_quay_stone", t_quay_paving, False,
     "wet flagstone, the ground of every walk on the quay"),
    ("quay_paving_worn", ",", "bg0_quay_stone", t_quay_paving_worn, False,
     "the same stone with a stepped crack, so a long walk is not one tile repeated"),
    ("quay_puddle", "~", "bg0_quay_stone", t_quay_puddle, False,
     "standing water in a low slab, two glints to say the lamp is behind it"),
    ("quay_edge", "q", "bg0_quay_stone", t_quay_edge, False,
     "the coping at the water, the one tile that lets the map end the stone honestly"),
    ("water_deep", "w", "bg1_harbour_water", t_water_deep, False,
     "harbour water, frame 1 of 2"),
    ("water_ripple", "W", "bg1_harbour_water", t_water_ripple, False,
     "harbour water, frame 2 of 2: the swell moves two pixels and the glints swap sides"),
    ("water_reflection", "R", "bg1_harbour_water", t_water_reflection, False,
     "the lamp's glint path on the water: a broken vertical line, so the water answers the light"),
    ("bollard", "B", "bg0_quay_stone", t_bollard, True,
     "iron bollard on wet stone, lit on one edge only"),
    ("chain", "c", "bg0_quay_stone", t_chain, True,
     "a chain draped between two bollards: one arc, links as alternating dark and lit clusters"),
    ("barrier", "b", "bg0_quay_stone", t_barrier, True,
     "steel barrier across the quay mouth"),
    ("brick_wall", "#", "bg2_brick_iron", t_brick_wall, False,
     "the office frontage: two courses, mortar, a lit top edge per brick"),
    ("brick_wall_damp", "=", "bg2_brick_iron", t_brick_wall_damp, False,
     "the same wall with two bricks gone dark where the rain runs"),
    ("door_office", "D", "bg2_brick_iron", t_door_office, True,
     "the one door in the block that opens: handle catching the lamp"),
    ("door_shut", "d", "bg2_brick_iron", t_door_shut, True,
     "a shut door, boarded, no handle light: seven of these teach the rule"),
    ("window_lit", "o", "bg3_lamp_glass", t_window_lit, False,
     "a lit window: the room in gold with a hot core, waived from the light share rule because it is a light"),
    ("window_dark", "O", "bg2_brick_iron", t_window_dark, True,
     "the same window with nobody home, glass in the dark ramp"),
    ("lamp_base", "L", "bg3_lamp_glass", t_lamp_base, False,
     "a lamp post and the pool it throws on the stone, waived: it is a light"),
    ("sign_board", "S", "bg3_lamp_glass", t_sign_board, False,
     "a harbour sign board, lettering as dashes, waived: it is a light"),
    ("office_floor", "f", "bg2_brick_iron", t_office_floor, False,
     "the dock office boards, lit edge and dark joint"),
    ("office_desk", "k", "bg2_brick_iron", t_office_desk, True,
     "the office desk Nye works behind, drawn on its own boards"),
]


# The role that carries a tile's structure, named per tile rather than guessed: the blob test asks for a "dark"
# tone, and on a tile that tone is the material's darkest role (iron, frame, joint), with the backdrop counted as
# dark too because a background tile's black is the same black the outline rule means.
DARK_ROLE = {
    "bollard": "sea_1",
    "chain": "sea_1",
    "barrier": "sea_1",
    "door_office": "stone_2",
    "door_shut": "stone_2",
    "window_dark": "stone_2",
    "office_desk": "stone_2",
}


# -----------------------------------------------------------------------------------------------------------------
# The mocks: 256x240 composed only from tiles in this sheet.

BLOCK = {
    "default": ["#", "#", "#", "#", "#", "#", ".", ".", ".", ".", "q", "w", "w", "w", "w"],
    "cells": {
        (2, 1): "o", (9, 1): "o", (13, 1): "O",
        (1, 3): "O", (4, 3): "S", (12, 2): "=", (12, 3): "O",
        (3, 5): "d", (7, 5): "D", (11, 5): "O",
        (6, 6): "~", (13, 6): "L",
        (3, 7): "B", (10, 7): "B", (1, 7): ",",
        (6, 8): "b", (2, 9): "~",
        (3, 12): "W", (8, 11): "W", (12, 13): "W", (6, 13): "W",
        (13, 11): "R", (13, 12): "R", (14, 13): "R",
    },
    "row_cells": {7: [(x, "c") for x in range(4, 10)]},
}

OFFICE = {
    "default": ["f"] * 15,
    "cells": {
        (3, 3): "k", (4, 3): "k", (5, 3): "k",
        (10, 8): "k", (11, 8): "k",
        (13, 1): "L", (1, 10): "D", (8, 12): "O",
        (6, 5): "k",
    },
    "row_cells": {},
}


def compose(layout):
    sheet = Image.new("RGBA", (256, 240), (0, 0, 0, 255))
    by_char = {char: painter for (name, char, _p, painter, _g, _n) in TILES}
    for y in range(15):
        for x in range(16):
            name_key = layout["cells"].get((x, y))
            if name_key is None:
                for (cx, cval) in layout["row_cells"].get(y, []):
                    if cx == x:
                        name_key = cval
            if name_key is None:
                name_key = layout["default"][y]
            tile = render_tile(by_char[name_key])
            sheet.paste(tile, (x * TILE, y * TILE))
    return sheet


# -----------------------------------------------------------------------------------------------------------------
# Render and measure.

def load_colours():
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        nes = json.load(handle)
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        design = json.load(handle)
    entries = {item["index"]: item for item in nes["entries"]}
    ppu_hex = {item["hex"].lower() for item in nes["entries"] if item.get("usable")}
    for role, (index, _why) in ROLE_ENTRY.items():
        if role not in design["roles"]:
            raise SystemExit("%s is not a role in data/palette.json" % role)
        entry = entries[index]
        if not entry.get("usable"):
            raise SystemExit("%s resolves to %s, which is not a usable entry" % (role, entry["code"]))
        if entry["hex"].lower() not in ppu_hex:
            raise SystemExit("%s resolves to %s, which is not a 2C02 output" % (role, entry["hex"]))
    return design, entries


COLOUR = {}


def build_colour_map(entries):
    for role, (index, _why) in ROLE_ENTRY.items():
        hex_value = entries[index]["hex"].lower()
        text = hex_value.lstrip("#")
        COLOUR[role] = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), 255)


def render_tile(painter_or_name):
    if isinstance(painter_or_name, Image.Image):
        return painter_or_name
    canvas = Canvas()
    canvas.fill(BACKDROP_ROLE)
    painter_or_name(canvas)
    image = Image.new("RGBA", (TILE, TILE), COLOUR[BACKDROP_ROLE])
    pixels = image.load()
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x] or BACKDROP_ROLE
            pixels[x, y] = COLOUR[role]
    return image


def luminance(rgb):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def blob_numbers(canvas, dark_roles=None):
    """The four numbers of SPRITE-CRAFT section 8.5, measured on the tile."""
    used = {}
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x] or BACKDROP_ROLE
            used[role] = used.get(role, 0) + 1
    drawn = sum(used.values())
    ordered = sorted(used, key=lambda role: luminance(COLOUR[role]))
    light = ordered[-1]
    dark_roles = set(dark_roles or ()) | {ordered[0], BACKDROP_ROLE}

    def is_dark(role):
        return role in dark_roles

    light_share = round(100.0 * used[light] / drawn, 1) if drawn else 0.0
    rows_without_dark = 0
    for y in range(TILE):
        if all(not is_dark(canvas.rows()[y][x] or BACKDROP_ROLE) for x in range(TILE)):
            rows_without_dark += 1
    runs = 0
    for y in range(TILE):
        inside = False
        for x in range(TILE):
            here = is_dark(canvas.rows()[y][x] or BACKDROP_ROLE)
            if here and not inside:
                runs += 1
            inside = here
    interior = 0
    for y in range(1, TILE - 1):
        for x in range(1, TILE - 1):
            if is_dark(canvas.rows()[y][x] or BACKDROP_ROLE):
                interior += 1
    return {
        "colours": len(used),
        "roles": sorted(used),
        "dark_roles": sorted(dark_roles),
        "lightest_role": light,
        "lightest_share_percent": light_share,
        "rows_without_dark": rows_without_dark,
        "horizontal_dark_runs": runs,
        "interior_dark_pixels": interior,
    }


def blob_verdict(numbers, gated):
    if not gated:
        return "reported only: a pattern or a light source, not a character silhouette"
    failures = []
    if numbers["lightest_share_percent"] >= 30.0:
        failures.append("lightest tone is %.1f percent, the ceiling is 30" % numbers["lightest_share_percent"])
    if numbers["rows_without_dark"] != 0:
        failures.append("%d row(s) carry no dark pixel" % numbers["rows_without_dark"])
    if numbers["horizontal_dark_runs"] < 3:
        failures.append("%d horizontal dark run(s), the floor is 3" % numbers["horizontal_dark_runs"])
    if numbers["interior_dark_pixels"] < 8:
        failures.append("%d interior dark pixel(s), the floor is 8" % numbers["interior_dark_pixels"])
    return "pass" if not failures else "FAIL: " + "; ".join(failures)


# -----------------------------------------------------------------------------------------------------------------

def build():
    design, entries = load_colours()
    build_colour_map(entries)

    rendered = []
    for (name, char, palette, painter, gated, note) in TILES:
        canvas = Canvas()
        canvas.fill(BACKDROP_ROLE)
        painter(canvas)
        roles = sorted({role for row in canvas.rows() for role in row if role})
        allowed = {role for (pname, proles, _n) in BG_PALETTES if pname == palette for role in proles}
        outside = [role for role in roles if role not in allowed and role != BACKDROP_ROLE]
        if outside:
            raise SystemExit("%s draws %s outside %s" % (name, outside, palette))
        numbers = blob_numbers(canvas, [DARK_ROLE[name]] if name in DARK_ROLE else None)
        rendered.append({
            "name": name,
            "character": char,
            "palette": palette,
            "roles": roles,
            "note": note,
            "blob": numbers,
            "blob_verdict": blob_verdict(numbers, gated),
            "blob_gated": gated,
            "image": render_tile(painter),
            "canvas": canvas,
        })

    sheet = Image.new("RGBA", (COLUMNS * TILE, ((len(rendered) + COLUMNS - 1) // COLUMNS) * TILE),
                      COLOUR[BACKDROP_ROLE])
    for position, tile in enumerate(rendered):
        sheet.paste(tile["image"], ((position % COLUMNS) * TILE, (position // COLUMNS) * TILE))
    return rendered, sheet


SUM_OK = set()


def palette_json():
    return [
        {
            "name": name,
            "roles": roles,
            "entries": [ROLE_ENTRY[role][0] for role in roles],
            "hex": [None for _ in roles],
            "note": note,
        }
        for (name, roles, note) in BG_PALETTES
    ]


def manifest(rendered, sheet):
    palettes = palette_json()
    for palette in palettes:
        palette["hex"] = ["#%02x%02x%02x" % COLOUR[role][:3] for role in palette["roles"]]
    return {
        "format": 1,
        "kind": "tileset",
        "name": "quay_tiles",
        "image": "quay_tiles.png",
        "card": "R46 QUAY-TILES (t_abfb6024)",
        "columns": COLUMNS,
        "rows": (len(rendered) + COLUMNS - 1) // COLUMNS,
        "frames": len(rendered),
        "frame_w": TILE,
        "frame_h": TILE,
        "imagewidth": sheet.width,
        "imageheight": sheet.height,
        "tilecount": len(rendered),
        "tile_size": TILE,
        "margin": 0,
        "spacing": 0,
        "backdrop": {"entry": ROLE_ENTRY["ink"][0], "hex": "#000000"},
        "rule": ("NES: 1 shared backdrop $0F, 4 background palettes of 3 entries, a 16x16 area carries at most 3 "
                 "colours besides the backdrop, at most 25 colours on screen; every pixel is a 2C02 output"),
        "roles": {
            role: {"entry": entry, "hex": "#%02x%02x%02x" % COLOUR[role][:3], "why": why,
                   "palette_json_index": None}
            for role, (entry, why) in sorted(ROLE_ENTRY.items())
        },
        "sets": {
            name: {"roles": roles, "note": "append to data/room_palettes.json as a set with this id; "
                                          "ARRIVAL-MAP-2 owns that file"}
            for name, roles in SETS.items()
        },
        "palettes": palettes,
        "tiles": [
            {
                "index": position,
                "name": tile["name"],
                "character": tile["character"],
                "palette": tile["palette"],
                "roles": tile["roles"],
                "note": tile["note"],
                "blob": tile["blob"],
                "blob_gated": tile["blob_gated"],
                "blob_verdict": tile["blob_verdict"],
            }
            for position, tile in enumerate(rendered)
        ],
        "animation": [
            {"name": "water", "frames": ["water_deep", "water_ripple"], "hold_frames": 24,
             "note": "the sea is the only thing on the quay that moves; two frames, one step of swell"}
        ],
        "mocks": ["output/quay_block_preview.png", "output/quay_office_preview.png"],
    }


def tiles_markdown(rendered, manifest_data):
    lines = []
    add = lines.append
    add("# QUAY TILES: the tile table the map wiring reads")
    add("")
    add("Drawn by `tools/art/make_quay_tiles.py` for card R46 (t_abfb6024). Do not edit by hand: rerun the tool.")
    add("")
    add("The sheet is `quay_tiles.png`, %d by %d, %d cells of 16 x 16, %d tiles used. The manifest beside it "
        "(`quay_tiles.json`) is the machine readable copy of this table."
        % (manifest_data["imagewidth"], manifest_data["imageheight"], manifest_data["columns"] * manifest_data["rows"],
           manifest_data["frames"]))
    add("")
    add("Colours are ROLES from `data/palette.json`, not hex. The role resolves to one Ricoh 2C02 entry, because "
        "the audit's authority on a colour is `data/nes_palette.json` and the design palette's hexes are not 2C02 "
        "outputs. The bridge is the table below, and it is written in the manifest too.")
    add("")
    add("| role | 2C02 entry | hex | why that entry |")
    add("|---|---|---|---|")
    for role, (entry, why) in sorted(ROLE_ENTRY.items(), key=lambda item: ROLE_ENTRY[item[0]][0]):
        add("| `%s` | $%02X | %s | %s |" % (role, entry, "#%02x%02x%02x" % COLOUR[role][:3], why))
    add("")
    add("## The two room palette sets")
    add("")
    for name, roles in SETS.items():
        add("- **%s** (%d roles, cap 16): %s" % (name, len(roles), ", ".join("`%s`" % role for role in roles)))
    add("")
    add("ARRIVAL-MAP-2 (t_db2995d7) appends both to `data/room_palettes.json`; this card may not edit data files.")
    add("")
    add("## The four background palettes")
    add("")
    add("| palette | roles | 2C02 entries | what it draws |")
    add("|---|---|---|---|")
    for (name, roles, note) in BG_PALETTES:
        add("| `%s` | %s | %s | %s |" % (name, ", ".join("`%s`" % role for role in roles),
                                         ", ".join("$%02X" % ROLE_ENTRY[role][0] for role in roles), note))
    add("")
    add("## The tiles")
    add("")
    add("| # | name | char | palette | roles | blob test | what it is |")
    add("|---|---|---|---|---|---|---|")
    for position, tile in enumerate(rendered):
        numbers = tile["blob"]
        add("| %d | `%s` | `%s` | `%s` | %s | %s | %s |"
            % (position, tile["name"], tile["character"], tile["palette"],
               " ".join("`%s`" % role for role in tile["roles"]),
               ("%s (light %.0f%%, %d rows no dark, %d runs, %d inner dark)"
                % ("PASS" if tile["blob_verdict"] == "pass" else
                   ("n/a" if not tile["blob_gated"] else "FAIL"),
                   numbers["lightest_share_percent"], numbers["rows_without_dark"],
                   numbers["horizontal_dark_runs"], numbers["interior_dark_pixels"])),
               tile["note"]))
    add("")
    add("## How to wire it")
    add("")
    add("1. Every tile is 16 x 16 and index i in the sheet is `floor(i / 8)` rows down and `i % 8` cells across.")
    add("2. A tile draws from exactly one background palette, so a 16 x 16 attribute area can never carry a "
        "fourth colour. Give the area the palette named in the table and no other.")
    add("3. `water_deep` and `water_ripple` are the two frames of one animation; hold each for about 24 game "
        "frames, which is the slow swell the night quay wants and not a flicker.")
    add("4. Objects stand ON their own ground: `bollard`, `chain` and `barrier` include the paving they sit on, "
        "and `door_office`, `door_shut` and the windows include the brick around them, so a map can place them "
        "without a transparent layer.")
    add("5. The office pair (`office_floor`, `office_desk`) is the same warm ramp, so the interior scene uses the "
        "office night set and needs no fifth palette.")
    add("")
    add("## What this set does not do")
    add("")
    add("1. **The light does not spill across tile edges.** A tile carries three colours plus the backdrop, so the "
        "lamp's pool is inside its own cell; making it spill means a second lit-paving tile in the lamp palette, "
        "which the 4 palette budget cannot buy until ARRIVAL-MAP-2 says which palettes the quay scene can spare.")
    add("2. **There is no building wall above three courses.** The block's upper floors are the same brick tile "
        "repeated; a window sill course and a roofline are the next two tiles this set needs, and neither is in "
        "the card.")
    add("3. **Nothing here is a sprite.** These are background tiles on the 16 x 16 attribute grid: characters, "
        "the clerk and the sailor stand on them and obey the sprite rules in SPRITE-CRAFT, not these.")
    add("4. **The water is two frames, not four.** Two frames held 24 game frames each is the slow swell the night "
        "quay wants; a third frame buys a crest breaking at the quay edge and nothing else at this size.")
    add("5. **The sheet is not mirrored into `game/datafiles/art/`.** `tools/sync_art.py` does that and adds the "
        "entry to `title_manifest.json`; R28 (the map wiring) owns that step, so this card did not run it.")
    add("")
    return "\n".join(lines)


def write_png(path, image):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def contact_sheet(sheet):
    resample = getattr(Image, "NEAREST", None) or Image.Resampling.NEAREST
    return sheet.resize((sheet.width * 3, sheet.height * 3), resample)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw the quay tile set.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if the PNG on disk is stale")
    args = parser.parse_args(argv)

    rendered, sheet = build()
    payload = manifest(rendered, sheet)
    text = tiles_markdown(rendered, payload)

    if args.check:
        if not os.path.isfile(SHEET_PNG):
            print("make_quay_tiles: no sheet on disk")
            return 1
        with open(SHEET_PNG, "rb") as handle:
            on_disk = hashlib.sha256(handle.read()).hexdigest()
        buffer = os.path.join(OUTPUT, "_quay_tiles_stale_probe.png")
        os.makedirs(OUTPUT, exist_ok=True)
        sheet.save(buffer)
        with open(buffer, "rb") as handle:
            fresh = hashlib.sha256(handle.read()).hexdigest()
        os.remove(buffer)
        print("make_quay_tiles: %s" % ("fresh" if on_disk == fresh else "STALE"))
        return 0 if on_disk == fresh else 1

    write_png(SHEET_PNG, sheet)
    write_json(SHEET_JSON, payload)
    write_text(TILES_MD, text + "\n")
    write_png(os.path.join(OUTPUT, "quay_tiles_3x.png"), contact_sheet(sheet))

    for name, layout in (("quay_block", BLOCK), ("quay_office", OFFICE)):
        frame = compose(layout)
        write_png(os.path.join(OUTPUT, "%s_preview.png" % name), frame)
        write_json(os.path.join(OUTPUT, "%s_preview.json" % name), {
            "format": 1,
            "kind": "frame_note",
            "frame": "%s_preview.png" % name,
            "card": "R46 QUAY-TILES (t_abfb6024)",
            "backdrop": {"entry": ROLE_ENTRY["ink"][0], "hex": "#000000"},
            "note": ("a 256x240 mock composed only from the quay tile sheet, so the frame audit measures the "
                     "same art the map will use"),
        })

    colours = len({COLOUR[role] for role in ROLE_ENTRY})
    print("make_quay_tiles: %d tiles, %d colours, sheet %dx%d" % (len(rendered), colours, sheet.width, sheet.height))
    gated = [tile for tile in rendered if tile["blob_gated"]]
    failing = [tile for tile in gated if tile["blob_verdict"] != "pass"]
    print("  blob test: %d gated tile(s), %d pass, %d fail" % (len(gated), len(gated) - len(failing), len(failing)))
    for tile in failing:
        print("    FAIL %s: %s" % (tile["name"], tile["blob_verdict"]))
    print("  sheet: %s" % os.path.relpath(SHEET_PNG, ROOT).replace(os.sep, "/"))
    print("  table: %s" % os.path.relpath(TILES_MD, ROOT).replace(os.sep, "/"))
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
