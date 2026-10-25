#!/usr/bin/env python3
"""make_ship_tiles.py: the ship interior tile set (card t_a0c1bccf, SHIP-TILES).

What this draws, and to which rules:

1. Twenty four 16x16 tiles of the ship's own interior: plate steel, grating, the closed and the open
   hatch, two bulkheads, the log terminal face, and the water that lies under the rail, plus the rail,
   the ladder, the stairs, the pipes, the fittings and the deck paint they need to be placeable.
   The card names six families and this sheet carries all six.
2. Every colour is a Ricoh 2C02 output named by ROLE, with the entry written down beside the role, and
   the palette is the one the ship's own background strip already draws from (tools/art/make_env_ship.py,
   PALETTE lines 61 to 72): black, two steel greys, white paint, three sea blues, two rusts and brass.
   Ten colours, against the card's ceiling of 16, and no pixel is an approximation of a 2C02 output.
3. Each tile draws from exactly one of four background palettes of three roles plus the shared backdrop
   $0F, so no 16x16 attribute area can carry a fourth colour. That is the rule tools/nes_check.py
   measures, and main() runs that tool on the written PNG rather than promising it.
4. The geometry is generated, not sampled. There is no OSM extract for a ship and the card forbids one,
   so every dimension below is a named decision with the reason beside it (see GEOMETRY).
5. The hatch and the rail are marked in data/tile_classes_ship.json: which index is which, whether it is
   walkable, what blocks it, and, for the hatch, the story flag that opens it.

Outputs:
    assets/tiles/ship/ship_tiles.png            the sheet, 8 by 3 cells of 16x16, 24 tiles
    assets/tiles/ship/ship_tiles.json           the tileset manifest: palettes, roles, tiles, measured
    assets/tiles/ship/TILES.md                  the tile table the map wiring reads
    data/tile_classes_ship.json                 every tile walkable or not, with the hatch and the rail marked
    output/ship_tiles_3x.png                    3x contact sheet
    output/ship_deck_preview.png                256x240 mock of the deck, the rail and the water below it

Usage:
    python tools/art/make_ship_tiles.py
    python tools/art/make_ship_tiles.py --check      # write nothing, exit 1 if the PNG on disk is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "assets", "tiles", "ship")
SHEET_PNG = os.path.join(OUT_DIR, "ship_tiles.png")
SHEET_JSON = os.path.join(OUT_DIR, "ship_tiles.json")
TILES_MD = os.path.join(OUT_DIR, "TILES.md")
CLASS_JSON = os.path.join(ROOT, "data", "tile_classes_ship.json")
OUTPUT = os.path.join(ROOT, "output")
NES_CHECK = os.path.join(ROOT, "tools", "nes_check.py")

TILE = 16
COLUMNS = 8
BACKDROP = "k"
CARD = "SHIP-TILES (t_a0c1bccf)"

# -----------------------------------------------------------------------------------------------------------------
# The ten colours. Key, 2C02 entry, hex, what it is for. Entries and hexes are the values in
# tools/art/make_env_ship.py's PALETTE, so the deck tiles and the ship battle strip cannot drift apart.

PALETTE = [
    ("k", 0x0F, "#000000", "backdrop: the hatch void, seams, the drop beyond the rail"),
    ("m", 0x00, "#7c7c7c", "steel mid: deck plates, the bulkhead face, the opening in a plate"),
    ("l", 0x10, "#bcbcbc", "steel light: lit plate edges, rails, rivets, ladder stringers"),
    ("w", 0x30, "#fcfcfc", "white paint: the walkway line, lamp glass, foam on a crest"),
    ("a", 0x02, "#0000bc", "sea deep: the water under the rail"),
    ("b", 0x12, "#0058f8", "sea mid: one step of swell above the deep"),
    ("c", 0x21, "#3cbcfc", "sea crest and the terminal's screen"),
    ("r", 0x07, "#881400", "rust dark: the shadow under a bar, risers, the warm dark in a joint"),
    ("o", 0x17, "#e45c10", "rust: pipe bodies, the terminal bezel, the dark side of the brass"),
    ("y", 0x28, "#f8b800", "brass and hazard yellow: the porthole ring, the keypad, the stripes"),
]

# The four background palettes. A tile draws from exactly one, three roles plus the shared backdrop.
# Four is the hardware's own number: a 256x240 screen shows four background palettes at once, so this set
# can be spent by a room without a fifth choice anywhere.
BG_PALETTES = [
    ("bg0_deck", ["m", "l", "w"],
     "the deck itself and everything painted on it: plate, line, hatch, sill, lamp"),
    ("bg1_hold", ["m", "r", "l"],
     "the hold's ironwork: grating, bulkhead, ladder, stairs, pipes, locker, crate, the rail"),
    ("bg2_sea", ["a", "b", "c"],
     "the water under the rail: deep, swell, the crest and the foam at the hull"),
    ("bg3_fixture", ["y", "o", "c"],
     "the things that are read rather than walked on: hazard paint, the porthole, the log terminal"),
]

# name, char, palette, painter, note, source, walkable or not, why that class, climbable
TILES = []


def tile(name, char, palette, painter, note, source, walkable, walk_why, climbable=False, marked=None):
    TILES.append({"name": name, "char": char, "palette": palette, "painter": painter, "note": note,
                  "source": source, "walkable": walkable, "walk_why": walk_why, "climbable": climbable,
                  "marked": marked or {}})


# -----------------------------------------------------------------------------------------------------------------
# The geometry, as decisions with their reasons. Nothing here is measured off anything: the card says no OSM
# for a ship, and a 16 px tile is the unit, so these are the drawing's own facts.

GEOMETRY = {
    "tile": "16 x 16 px, the NES attribute area exactly, so one tile is one palette choice and the art cuts "
            "into four 8 x 8 pattern tiles without a repaint",
    "plate_pitch": "one plate per tile: a 1 px seam on the top and left edge means the seams line up across "
                   "a run and the deck reads as plates rather than as a flat grey field",
    "rivet_pitch": "4 px between rivets, so a plate shows four rivets a side at this size and no more; a "
                   "real rivet pitch of 75 mm would be a third of a pixel",
    "grating_pitch": "5 px: a 2 px bar and a 3 px hole, which is the smallest mesh that still reads as a "
                     "hole at 16 px and keeps the holes square",
    "bar_width": "2 px: one pixel of bar is a hairline at 3x and closes up on a TV; three pixels turns the "
                 "grating into a solid plate",
    "step": "3 px a step, four steps a tile: an adult's step is about 180 mm, so a 16 px tile is a little "
            "over two and a half metres of stair, and the tile is one storey-to-half-storey flight",
    "ladder": "rungs every 3 px, rails 2 px, which is the same rung pitch the stairs use so a climb looks "
              "like one piece of geometry seen two ways",
    "hatch": "a 14 px frame and a 10 px face: 2 px of frame is the only width at which a recess reads as a "
             "recess at this size, and the wheel is a 6 px cross so it is not mistaken for a bolt",
    "rail": "a 2 px bar and a 4 px post, both standing on the deck plate they guard: the rail is the edge of "
            "the ship, so the row below it is water and the class file says you cannot walk past it",
    "water": "a swell every 5 px and a glint every 6 px, offset 2 px between the two frames, so the sea moves "
             "without the pattern visibly scrolling",
    "terminal": "a 12 by 8 px screen with five text rows at 2 px pitch, and a 3 by 3 keypad: the row pitch is "
                "the smallest that draws a line of text as a line rather than as a smear",
}

SRC = {
    "card": "the card's six families: plate steel, grating, hatch, bulkhead, the log terminal face, the water "
            "under the rail",
    "ship_row": "data/maps/all.json, the ship_small row: 20 by 15 cells, tile_legend # wall, . floor, D door, "
                "H hatch, room_palette deck_day, story_flag ship_door_open (read only for this card)",
    "cabin_row": "data/maps/all.json, the ship_cabin row: the wardroom door and the Percy battle, which is why "
                 "the log terminal and the porthole have a face of their own",
    "spec": "specs/15-env-tiles-ship.md: ten colours, three non backdrop colours per 16x16 area, water and "
            "porthole animated, the hatch open and closed told apart at a glance, solids on the tile",
    "palette": "tools/art/make_env_ship.py PALETTE, lines 61 to 72: the ship strip's own ten 2C02 entries",
    "quay": "game/sprites_src/env/quay/TILES.md: the exterior set the player walks in from, so the sea and "
            "the stone are the ones this deck is moored beside",
    "geometry": "generated: no extract, no sample, no trace; every number is in GEOMETRY above",
}


# -----------------------------------------------------------------------------------------------------------------
# A 16x16 canvas of role keys. None is the backdrop.


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
                self.put(x, y, role)

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
# Grounds and structures.

def grain(c, seed, count=18, role_put="l", cover="m"):
    """A fixed scatter, not a rule: a modulo pattern reads as a dotted line, grit does not."""
    rng = random.Random(seed * 7919 + 13)
    placed = 0
    guard = 0
    while placed < count and guard < 400:
        guard += 1
        x = rng.randrange(TILE)
        y = rng.randrange(TILE)
        if c.rows()[y][x] in (None, cover):
            c.put(x, y, role_put)
            placed += 1


def plate(c, seed=1, worn=False):
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    for x in range(1, 15, 4):
        c.put(x, 1, "l")
    for (x, y) in ((3, 3), (12, 3), (3, 12), (12, 12)):
        c.put(x, y, "l")
        c.put(x + 1, y, "l")
        c.put(x, y + 1, "l")
    if worn:
        for (x0, x1, y) in ((4, 8, 6), (9, 13, 10), (2, 5, 14)):
            c.hline(y, x0, x1, "l")
        for (x0, x1, y) in ((5, 7, 7), (10, 12, 11)):
            c.hline(y, x0, x1, "k")
        c.put(2, 6, "m")
        c.put(3, 7, "m")
    grain(c, seed, count=10 if worn else 6)


def t_deck_plate(c):
    plate(c, 1)


def t_deck_plate_worn(c):
    plate(c, 2, worn=True)


def t_deck_line(c):
    plate(c, 3)
    c.hline(7, 0, 15, "w")
    c.hline(8, 0, 15, "w")
    c.vline(0, 0, 15, "k")


def grating(c, cross=False):
    c.fill("k")
    for y in (0, 5, 10):
        c.hline(y, 0, 15, "l")
        c.hline(y + 1, 0, 15, "m")
        c.hline(y + 4, 0, 15, "r")
    for x in (0, 5, 10):
        c.vline(x, 0, 15, "l")
        c.vline(x + 1, 0, 15, "m")
    if cross:
        c.vline(7, 0, 15, "l")
        c.vline(8, 0, 15, "m")
        c.vline(9, 0, 15, "r")


def t_deck_grating(c):
    grating(c, False)


def t_deck_grating_cross(c):
    grating(c, True)


def t_hatch_closed(c):
    c.fill("m")
    c.rect(0, 0, 16, 2, "l")
    c.rect(0, 14, 16, 2, "l")
    c.rect(0, 0, 2, 16, "l")
    c.rect(14, 0, 2, 16, "l")
    c.rect(2, 2, 12, 12, "k")
    c.rect(3, 3, 10, 10, "m")
    c.hline(8, 5, 10, "l")
    c.vline(8, 5, 10, "l")
    for (x, y) in ((5, 5), (10, 5), (5, 10), (10, 10)):
        c.put(x, y, "l")
    c.put(8, 8, "k")


def t_hatch_open(c):
    c.fill("m")
    c.rect(0, 0, 16, 2, "l")
    c.rect(0, 14, 16, 2, "l")
    c.rect(0, 0, 2, 16, "l")
    c.rect(14, 0, 2, 16, "l")
    c.rect(2, 2, 12, 12, "k")
    c.rect(2, 2, 12, 1, "m")
    c.rect(2, 2, 1, 12, "m")
    c.vline(5, 3, 14, "m")
    c.vline(10, 3, 14, "m")
    for y in (5, 7, 9, 11, 13):
        c.hline(y, 5, 10, "l")


def t_door_sill(c):
    plate(c, 7)
    c.hline(6, 0, 15, "l")
    c.hline(7, 0, 15, "w")
    c.hline(8, 0, 15, "l")
    c.hline(9, 0, 15, "k")
    c.put(5, 7, "l")
    c.put(10, 7, "l")
    for (x, y) in ((3, 12), (12, 12)):
        c.put(x, y, "l")
        c.put(x + 1, y, "l")


def t_bulkhead_rivet(c):
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.hline(15, 0, 15, "r")
    for y in (2, 6, 10, 14):
        for x in (2, 6, 10, 14):
            c.put(x, y, "l")
            c.put(x, y + 1, "r")


def t_bulkhead_plain(c):
    c.fill("m")
    c.hline(0, 0, 15, "l")
    c.hline(1, 0, 15, "m")
    c.hline(15, 0, 15, "r")
    c.vline(0, 0, 15, "k")
    c.put(0, 0, "k")


def t_bulkhead_light(c):
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.rect(5, 3, 6, 5, "l")
    c.rect(6, 4, 4, 3, "w")
    c.put(7, 2, "l")
    c.put(8, 2, "l")
    for (x, y) in ((5, 9), (6, 10), (7, 11), (8, 11), (9, 10), (10, 9)):
        c.put(x, y, "w")


def t_ladder(c):
    c.fill("k")
    c.rect(3, 0, 2, 16, "l")
    c.rect(11, 0, 2, 16, "l")
    c.vline(4, 0, 15, "m")
    c.vline(12, 0, 15, "m")
    for y in (2, 5, 8, 11, 14):
        c.hline(y, 3, 12, "m")
        c.put(3, y, "l")
        c.hline(y + 1, 3, 12, "r")


def t_stairs_up(c):
    c.fill("k")
    for i in range(4):
        y = 13 - i * 3
        x0 = i * 4
        c.hline(y, x0, 15, "l")
        c.rect(x0, y + 1, 16 - x0, 2, "m")
        c.hline(y + 3, x0, 15, "r")


def t_pipe_run(c):
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.hline(4, 0, 15, "l")
    c.rect(0, 5, 16, 4, "m")
    c.hline(9, 0, 15, "r")
    c.rect(2, 3, 2, 8, "l")
    c.rect(12, 3, 2, 8, "l")
    c.hline(13, 0, 15, "l")
    c.hline(14, 0, 15, "r")


def t_locker(c):
    c.fill("m")
    c.rect(1, 1, 14, 14, "l")
    c.rect(2, 2, 12, 12, "m")
    for y in (4, 6, 8):
        c.hline(y, 4, 11, "r")
    c.rect(11, 10, 2, 2, "l")
    c.hline(14, 2, 13, "r")


def t_crate(c):
    c.fill("k")
    c.rect(1, 1, 14, 14, "l")
    c.rect(2, 2, 12, 12, "m")
    for i in range(10):
        c.put(2 + i, 2 + i, "r")
        c.put(13 - i, 2 + i, "r")
    c.hline(7, 2, 13, "l")
    c.vline(7, 2, 13, "l")
    for (x, y) in ((2, 2), (13, 2), (2, 13), (13, 13)):
        c.put(x, y, "m")


def t_hazard_stripes(c):
    c.fill("y")
    for y in range(TILE):
        for x in range(TILE):
            if ((x + y) // 3) % 2 == 0:
                c.put(x, y, "k")
    c.hline(15, 0, 15, "o")
    c.vline(0, 0, 15, "k")


def t_rail_post(c):
    plate(c, 11)
    c.rect(6, 0, 4, 16, "m")
    c.rect(6, 0, 2, 16, "l")
    c.rect(4, 1, 8, 2, "m")
    c.hline(1, 4, 11, "l")
    c.hline(15, 4, 11, "r")


def t_rail_bar(c):
    plate(c, 12)
    c.hline(2, 0, 15, "l")
    c.hline(3, 0, 15, "l")
    c.hline(4, 0, 15, "m")
    c.hline(5, 0, 15, "r")


def t_porthole(c):
    c.fill("o")
    c.rect(1, 1, 14, 14, "y")
    c.rect(2, 2, 12, 12, "k")
    c.rect(3, 3, 10, 10, "c")
    c.hline(3, 3, 12, "y")
    c.vline(3, 3, 12, "y")
    c.hline(12, 3, 12, "o")
    c.vline(12, 3, 12, "o")
    for (x, y) in ((5, 5), (6, 5), (5, 6), (9, 8), (10, 8), (9, 9)):
        c.put(x, y, "y")
    c.rect(0, 0, 16, 1, "o")
    c.rect(0, 15, 16, 1, "o")


def t_log_terminal(c):
    c.fill("o")
    c.rect(1, 0, 14, 1, "y")
    c.rect(1, 1, 14, 11, "k")
    c.rect(2, 2, 12, 9, "c")
    for y in (4, 6, 8):
        c.hline(y, 3, 10, "k")
    for x in range(3, 11, 2):
        c.put(x, 6, "k")
    c.put(11, 4, "k")
    c.rect(2, 13, 12, 3, "k")
    for x in (3, 6, 9):
        c.rect(x, 13, 2, 3, "y")
    c.put(13, 14, "c")


def t_water_deep(c):
    c.fill("a")
    for y in (3, 8, 13):
        c.hline(y, 2, 7, "b")
        c.hline(y, 11, 14, "b")
    for (x, y) in ((5, 4), (12, 9), (3, 14)):
        c.put(x, y, "c")


def t_water_swell(c):
    c.fill("a")
    for y in (1, 6, 11):
        c.hline(y, 4, 9, "b")
        c.hline(y, 0, 2, "b")
    for (x, y) in ((7, 2), (2, 7), (10, 12)):
        c.put(x, y, "c")


def t_water_edge(c):
    c.fill("a")
    c.hline(0, 0, 15, "c")
    c.hline(1, 0, 15, "c")
    for x in range(0, 16, 3):
        c.put(x, 2, "c")
    c.hline(2, 0, 15, "b")
    c.hline(3, 0, 15, "b")
    c.put(6, 1, "b")
    c.put(12, 0, "b")
    for y in (6, 11):
        c.hline(y, 3, 9, "b")
    c.put(4, 7, "c")
    c.put(14, 12, "c")


# -----------------------------------------------------------------------------------------------------------------
# The tile table. Index is the position in the sheet.

tile("deck_plate", ".", "bg0_deck", t_deck_plate,
     "a plate of the deck: one plate a tile, seam on two edges, four rivets", "geometry",
     "walkable", "a deck plate is the floor the fight happens on")
tile("deck_plate_worn", ",", "bg0_deck", t_deck_plate_worn,
     "the same plate with tread scuffs, so a long deck is not one tile repeated", "geometry",
     "walkable", "a deck plate is the floor the fight happens on")
tile("deck_line", "=", "bg0_deck", t_deck_line,
     "the painted walkway line, two pixels wide, along the plate", "spec",
     "walkable", "paint on a deck plate: it does not stop a step")
tile("deck_grating", "g", "bg1_hold", t_deck_grating,
     "open steel grating: a two pixel bar and a three pixel hole", "geometry",
     "walkable", "grating is walked on; the engine space and the catwalk are laid in it")
tile("deck_grating_cross", "G", "bg1_hold", t_deck_grating_cross,
     "the grating with a raised centre member over it", "geometry",
     "walkable", "grating is walked on, and the member is flush enough to step over")
tile("hatch_closed", "H", "bg0_deck", t_hatch_closed,
     "a closed deck hatch: frame, recessed face, the wheel", "ship_row",
     "not walkable", "a shut hatch is a solid: the map blocks it, and it is the blocked until story flag cell",
     marked={"hatch": "closed", "flag": "ship_door_open"})
tile("hatch_open", "h", "bg0_deck", t_hatch_open,
     "the same hatch swung open: the void below and the tops of its ladder", "ship_row",
     "walkable", "an open hatch is the way down: walkable, and it is the cell the ladder_down trigger sits on",
     climbable=True, marked={"hatch": "open", "flag": ""})
tile("door_sill", "s", "bg0_deck", t_door_sill,
     "the sill across a watertight doorway, worn to the steel", "spec",
     "walkable", "a sill is a step of two pixels: crossable, so the map does not block it")
tile("bulkhead_rivet", "#", "bg1_hold", t_bulkhead_rivet,
     "a riveted bulkhead: plate seam, a four by four rivet grid, dark base course", "spec",
     "not walkable", "a bulkhead is a wall")
tile("bulkhead_plain", "B", "bg1_hold", t_bulkhead_plain,
     "the same bulkhead with no rivets, lit along its top edge", "spec",
     "not walkable", "a bulkhead is a wall")
tile("bulkhead_light", "i", "bg0_deck", t_bulkhead_light,
     "a bulkhead lamp and the first row of its spill", "spec",
     "not walkable", "a fitting on a wall: it is not ground")
tile("ladder", "L", "bg1_hold", t_ladder,
     "a vertical ladder: two stringers, rungs every three pixels", "spec",
     "walkable", "a ladder is climbed, not walked around; the map lets a step onto it",
     climbable=True)
tile("stairs_up", "U", "bg1_hold", t_stairs_up,
     "a short stair up to the weather deck, four treads", "spec",
     "walkable", "a stair is climbed, so it is not a solid", climbable=True)
tile("pipe_run", "p", "bg1_hold", t_pipe_run,
     "a pipe run along a bulkhead, with two flanges and a lagging line", "spec",
     "not walkable", "a pipe run stands proud of the wall: a solid")
tile("locker", "K", "bg1_hold", t_locker,
     "a steel locker: louvred door, handle, dark base", "spec",
     "not walkable", "a locker is furniture: a solid")
tile("crate", "C", "bg1_hold", t_crate,
     "a crate in the hold, banded with a diagonal brace", "spec",
     "not walkable", "a crate is a solid the hold is furnished with")
tile("hazard_stripes", "!", "bg3_fixture", t_hazard_stripes,
     "hazard paint: a yellow field, black diagonal stripes, rust at its edge", "spec",
     "walkable", "paint on a deck: it marks a hazard, it is not one")
tile("rail_post", "|", "bg1_hold", t_rail_post,
     "a rail stanchion standing on the deck plate it guards", "card",
     "not walkable", "the rail is the edge of the ship: a solid, and the deck ends at it",
     marked={"rail": True})
tile("rail_bar", "-", "bg1_hold", t_rail_bar,
     "the rail bar and its shadow, on the deck plate at the ship's edge, with the water beyond", "card",
     "not walkable", "the rail is the edge of the ship: a solid, and the water is under it",
     marked={"rail": True})
tile("porthole", "O", "bg3_fixture", t_porthole,
     "a brass porthole: ring, glass, the harbour showing through it", "spec",
     "not walkable", "a porthole is set in a bulkhead: a solid")
tile("log_terminal", "T", "bg3_fixture", t_log_terminal,
     "the log terminal face: screen with five text rows, keypad, one live indicator", "card",
     "not walkable", "a terminal is mounted on a wall: it is the save point, not ground")
tile("water_deep", "~", "bg2_sea", t_water_deep,
     "the water under the rail, frame 1 of 2: deep blue, two swells, three glints", "card",
     "not walkable", "you cannot walk on the sea")
tile("water_swell", "w", "bg2_sea", t_water_swell,
     "the water under the rail, frame 2 of 2: the swell moves two pixels and the glints swap", "card",
     "not walkable", "you cannot walk on the sea")
tile("water_edge", "W", "bg2_sea", t_water_edge,
     "the waterline at the hull: crest against the steel, foam breaking", "card",
     "not walkable", "the waterline is water: the hull beside it is a solid too")

assert len(TILES) == 24, "the sheet is 8 by 3, so 24 tiles"

PALETTE_OF_ROLE = {}
for _name, _roles, _note in BG_PALETTES:
    for _role in _roles:
        PALETTE_OF_ROLE[_role] = _name


# -----------------------------------------------------------------------------------------------------------------
# Render and measure.

COLOUR = {}
ENTRY_OF_ROLE = {}
HEX_OF_ROLE = {}
WHY_OF_ROLE = {}


def load_colours():
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        nes = json.load(handle)
    entries = {item["index"]: item for item in nes["entries"]}
    outputs = {item["hex"].lower() for item in nes["entries"] if item.get("usable")}
    for key, entry_index, hexv, why in PALETTE:
        entry = entries[entry_index]
        if entry["hex"].lower() != hexv.lower():
            raise SystemExit("%s names %s for $%02X but data/nes_palette.json has %s"
                             % (key, hexv, entry_index, entry["hex"]))
        if not entry.get("usable"):
            raise SystemExit("$%02X is flagged unusable by the art bible" % entry_index)
        if entry["hex"].lower() not in outputs:
            raise SystemExit("$%02X is not a 2C02 output" % entry_index)
        ENTRY_OF_ROLE[key] = entry_index
        HEX_OF_ROLE[key] = entry["hex"].lower()
        WHY_OF_ROLE[key] = why
        text = entry["hex"].lower().lstrip("#")
        COLOUR[key] = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), 255)


def render_tile(painter):
    canvas = Canvas()
    canvas.fill(None)
    painter(canvas)
    image = Image.new("RGBA", (TILE, TILE), COLOUR[BACKDROP])
    pixels = image.load()
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x]
            pixels[x, y] = COLOUR[BACKDROP] if role is None else COLOUR[role]
    return image


def luminance(rgb):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def blob_numbers(canvas):
    """knowledge/SPRITE-CRAFT.md section 8.5, reported per tile. This set is structure, not a silhouette."""
    used = {}
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x]
            key = BACKDROP if role is None else role
            used[key] = used.get(key, 0) + 1
    drawn = sum(used.values())
    ordered = sorted(used, key=lambda role: luminance(COLOUR[role]))
    light = ordered[-1]
    dark_roles = {ordered[0], BACKDROP}
    light_share = round(100.0 * used[light] / drawn, 1) if drawn else 0.0

    def is_dark(role):
        return role in dark_roles

    rows_without_dark = 0
    for y in range(TILE):
        if all(not is_dark(canvas.rows()[y][x] or BACKDROP) for x in range(TILE)):
            rows_without_dark += 1
    runs = 0
    for y in range(TILE):
        inside = False
        for x in range(TILE):
            here = is_dark(canvas.rows()[y][x] or BACKDROP)
            if here and not inside:
                runs += 1
            inside = here
    interior = 0
    for y in range(1, TILE - 1):
        for x in range(1, TILE - 1):
            if is_dark(canvas.rows()[y][x] or BACKDROP):
                interior += 1
    return {"colours": len(used), "roles": sorted(used), "lightest_role": light,
            "lightest_share_percent": light_share, "rows_without_dark": rows_without_dark,
            "horizontal_dark_runs": runs, "interior_dark_pixels": interior}


def build():
    load_colours()
    rendered = []
    for entry in TILES:
        canvas = Canvas()
        canvas.fill(None)
        entry["painter"](canvas)
        roles = sorted({role for row in canvas.rows() for role in row if role})
        allowed = {role for (pname, proles, _n) in BG_PALETTES if pname == entry["palette"] for role in proles}
        outside = [role for role in roles if role not in allowed and role != BACKDROP]
        if outside:
            raise SystemExit("%s draws %s outside %s" % (entry["name"], outside, entry["palette"]))
        entry["roles"] = roles
        entry["blob"] = blob_numbers(canvas)
        entry["image"] = render_tile(entry["painter"])
        rendered.append(entry)

    sheet = Image.new("RGBA", (COLUMNS * TILE, ((len(rendered) + COLUMNS - 1) // COLUMNS) * TILE),
                      COLOUR[BACKDROP])
    for position, item in enumerate(rendered):
        sheet.paste(item["image"], ((position % COLUMNS) * TILE, (position // COLUMNS) * TILE))
    return rendered, sheet


def measure_sheet(sheet, rendered):
    failures = []
    used = {}
    for y in range(sheet.height):
        for x in range(sheet.width):
            r, g, b, a = sheet.getpixel((x, y))
            if a != 255:
                failures.append("transparent pixel at %d,%d: the sheet must be opaque" % (x, y))
                break
            used[(r, g, b)] = used.get((r, g, b), 0) + 1
    if len(used) > 16:
        failures.append("the sheet uses %d colours, the card allows 16" % len(used))
    backdrop = COLOUR[BACKDROP][:3]
    off_palette = sorted(hex_of(rgb) for rgb in used if rgb not in {COLOUR[key][:3] for key in COLOUR})
    if off_palette:
        failures.append("colours outside the ten roles: %s" % ", ".join(off_palette))
    worst = 0
    worst_name = ""
    for position, item in enumerate(rendered):
        tx, ty = position % COLUMNS, position // COLUMNS
        area = set()
        for y in range(TILE):
            for x in range(TILE):
                area.add(sheet.getpixel((tx * TILE + x, ty * TILE + y))[:3])
        count = len(area - {backdrop})
        if count > worst:
            worst, worst_name = count, item["name"]
        if count > 3:
            failures.append("tile %d (%s) carries %d non backdrop colours, the NES allows 3"
                            % (position, item["name"], count))
    facts = {
        "sheet": [sheet.width, sheet.height], "colours": len(used), "worst_area_colours": worst,
        "worst_area_tile": worst_name, "tiles": len(rendered),
        "walkable": sum(1 for item in rendered if item["walkable"] == "walkable"),
        "not_walkable": sum(1 for item in rendered if item["walkable"] != "walkable"),
        "climbable": sum(1 for item in rendered if item["climbable"]),
        "size_sixteen": all(item["image"].size == (TILE, TILE) for item in rendered),
    }
    return facts, failures


def hex_of(rgb):
    return "#%02x%02x%02x" % rgb[:3]


def run_nes_check():
    command = [sys.executable, NES_CHECK, os.path.relpath(SHEET_PNG, ROOT), "--type", "background",
               "--backdrop", "#000000"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


# -----------------------------------------------------------------------------------------------------------------
# Writers.

def palette_json():
    return [{"name": name, "roles": roles, "entries": [ENTRY_OF_ROLE[role] for role in roles],
             "hex": [HEX_OF_ROLE[role] for role in roles], "note": note}
            for (name, roles, note) in BG_PALETTES]


def manifest(rendered, sheet, facts, nes):
    return {
        "format": 1,
        "kind": "tileset",
        "name": "ship_tiles",
        "image": "ship_tiles.png",
        "card": CARD,
        "licence": "the project's own generated geometry: no extract, no sample, no trace, no ODbL",
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
        "backdrop": {"entry": ENTRY_OF_ROLE[BACKDROP], "hex": HEX_OF_ROLE[BACKDROP]},
        "rule": ("NES: 1 shared backdrop $0F, 4 background palettes of 3 entries, a 16x16 "
                 "area carries at most 3 colours besides the backdrop, ten colours in the set; every pixel is "
                 "a 2C02 output"),
        "geometry": GEOMETRY,
        "sources": SRC,
        "roles": {key: {"role": key, "palette_json_index": None, "entry": ENTRY_OF_ROLE[key],
                        "hex": HEX_OF_ROLE[key], "why": WHY_OF_ROLE[key]}
                  for (key, _e, _h, _w) in PALETTE},
        "palettes": palette_json(),
        "tiles": [{"index": position, "name": item["name"], "character": item["char"],
                   "palette": item["palette"], "roles": item["roles"], "note": item["note"],
                   "source": item["source"], "walkable": item["walkable"] == "walkable",
                   "climbable": item["climbable"], "walk_reason": item["walk_why"],
                   "marked": item["marked"], "blob": item["blob"]}
                  for position, item in enumerate(rendered)],
        "animation": [{"a": "water_deep", "b": "water_swell", "fps": 2,
                       "note": "the sea under the rail: two frames, the swell moves two pixels"}],
        "marks": marks(rendered),
        "nes_check": nes,
        "mocks": ["output/ship_tiles_3x.png", "output/ship_deck_preview.png"],
        "measured": facts,
    }


def marks(rendered):
    by_name = {item["name"]: position for position, item in enumerate(rendered)}
    return {
        "hatch": {"closed": by_name["hatch_closed"], "open": by_name["hatch_open"],
                  "flag": "ship_door_open",
                  "rule": ("the closed hatch is not walkable and is the flag gated cell (collision 2 in the "
                           "data/maps/all.json convention); the open hatch is walkable and carries the "
                           "ladder_down trigger")},
        "rail": {"bar": by_name["rail_bar"], "post": by_name["rail_post"],
                 "water_below": [by_name["water_deep"], by_name["water_swell"], by_name["water_edge"]],
                 "rule": ("the rail is the edge of the ship: not walkable, stood on the deck plate it guards, "
                          "with the water in the next row below it")},
    }


def class_json(rendered):
    return {
        "format": 1,
        "kind": "tile_classes",
        "name": "ship",
        "card": CARD,
        "licence": ("the project's own generated geometry: no extract, no sample, no trace, so unlike the drive "
                    "and quay class files this one carries no ODbL line"),
        "source_map": "data/maps/all.json, the ship_small and ship_cabin rows, read only",
        "rule": ("every tile in assets/tiles/ship/ship_tiles.png appears here once, by index and by name, with "
                 "walkable true or false and the reason, and the hatch and the rail are marked by name; a tile "
                 "missing from this file cannot be placed by the map wiring"),
        "tile_size": TILE,
        "tilecount": len(rendered),
        "backdrop": {"entry": ENTRY_OF_ROLE[BACKDROP], "hex": HEX_OF_ROLE[BACKDROP]},
        "not_walkable_rule": ("a tile is not walkable when it is a wall, a fitting or furniture, when it is the "
                              "edge of the ship, or when it is water"),
        "marks": marks(rendered),
        "tiles": [{"index": position, "name": item["name"], "walkable": item["walkable"] == "walkable",
                   "class": item["walkable"], "climbable": item["climbable"], "marked": item["marked"],
                   "reason": item["walk_why"]}
                  for position, item in enumerate(rendered)],
        "counts": {
            "walkable": sum(1 for item in rendered if item["walkable"] == "walkable"),
            "not_walkable": sum(1 for item in rendered if item["walkable"] != "walkable"),
            "climbable": sum(1 for item in rendered if item["climbable"]),
        },
    }


def tiles_markdown(rendered, data):
    lines = []
    add = lines.append
    add("# SHIP TILES: the tile table the map wiring reads")
    add("")
    add("Drawn by `tools/art/make_ship_tiles.py` for card t_a0c1bccf. Do not edit by hand: rerun the tool.")
    add("")
    add("The sheet is `ship_tiles.png`, %d by %d, %d cells of 16 x 16, %d tiles used. The manifest beside it "
        "(`ship_tiles.json`) is the machine readable copy of this table, and `data/tile_classes_ship.json` is the "
        "walkable classification the map reads, with the hatch and the rail marked by name."
        % (data["imagewidth"], data["imageheight"], data["columns"] * data["rows"], data["frames"]))
    add("")
    add("Colours are ROLES with their 2C02 entry written down. The ten entries are the ones the ship's own "
        "background strip draws from (`tools/art/make_env_ship.py` PALETTE, lines 61 to 72), so the deck tiles and "
        "the ship battle strip cannot drift apart. Ten colours against the card's ceiling of 16.")
    add("")
    add("## The colours")
    add("")
    add("| role | 2C02 entry | hex | why that entry |")
    add("|---|---|---|---|")
    for key, entry_index, hexv, why in sorted(PALETTE, key=lambda row: row[1]):
        add("| `%s` | $%02X | `%s` | %s |" % (key, entry_index, hexv, why))
    add("")
    add("## The four background palettes")
    add("")
    add("| palette | roles | 2C02 entries | what it draws |")
    add("|---|---|---|---|")
    for (name, roles, note) in BG_PALETTES:
        add("| `%s` | %s | %s | %s |" % (name, ", ".join("`%s`" % role for role in roles),
                                         ", ".join("$%02X" % ENTRY_OF_ROLE[role] for role in roles), note))
    add("")
    add("A 256 x 240 screen shows four background palettes at once, which is the whole set: the deck spends "
        "`bg0_deck` on its plates and paint, `bg1_hold` on the ironwork and the rail, `bg2_sea` on the water "
        "under the rail, and `bg3_fixture` on the hazard paint, the porthole and the terminal. No room needs a "
        "fifth choice, and no tile spends two.")
    add("")
    add("## The tiles")
    add("")
    add("| # | name | char | palette | walkable | climbable | marked | what it is |")
    add("|---|---|---|---|---|---|---|---|")
    for position, item in enumerate(rendered):
        mark = ", ".join("%s=%s" % (key, value) for key, value in sorted(item["marked"].items()) if value) or ""
        add("| %d | `%s` | `%s` | `%s` | %s | %s | %s | %s |"
            % (position, item["name"], item["char"], item["palette"],
               "yes" if item["walkable"] == "walkable" else "no",
               "yes" if item["climbable"] else "", mark, item["note"]))
    add("")
    add("## The hatch and the rail, as the class file marks them")
    add("")
    add("- **The hatch.** `hatch_closed` at index %d is not walkable: a shut hatch is a solid, and it is the cell "
        "the map blocks until the story flag `ship_door_open` clears (collision 2 in the `data/maps/all.json` "
        "convention). `hatch_open` at index %d is walkable and climbable, and it is the cell the `ladder_down` "
        "trigger sits on." % (data["marks"]["hatch"]["closed"], data["marks"]["hatch"]["open"]))
    add("- **The rail.** `rail_post` at index %d and `rail_bar` at index %d are not walkable: the rail is the edge "
        "of the ship, and the water at index %d to %d is under it. Both stand on the deck plate they guard, so a "
        "map places them on the ground layer in the row above the water."
        % (data["marks"]["rail"]["post"], data["marks"]["rail"]["bar"],
           data["marks"]["rail"]["water_below"][0], data["marks"]["rail"]["water_below"][-1]))
    add("")
    add("## The geometry, as decisions with their reasons")
    add("")
    for key in ("tile", "plate_pitch", "rivet_pitch", "grating_pitch", "bar_width", "step", "ladder", "hatch",
                "rail", "water", "terminal"):
        add("- **%s**: %s" % (key, GEOMETRY[key]))
    add("")
    add("## How to wire it")
    add("")
    add("1. Every tile is 16 x 16, and index i in the sheet is `floor(i / 8)` rows down and `i % 8` cells across.")
    add("2. A tile draws from exactly one background palette, so a 16 x 16 attribute area can never carry a fourth "
        "colour. Give the area the palette named in the table and no other.")
    add("3. `water_deep` and `water_swell` are one animation at 2 frames a second: hold each for about 30 game "
        "frames, which is a swell and not a flicker. `water_edge` is the static waterline tile at the hull.")
    add("4. The deck objects (`hatch_closed`, `hatch_open`, `rail_post`, `rail_bar`, `bulkhead_light`, `locker`, "
        "`crate`) draw their own steel around them, so a map places them on the ground layer without a "
        "transparency pass.")
    add("5. The bulkhead pair `bulkhead_rivet` and `bulkhead_plain` tiles horizontally and vertically: both carry "
        "the seam on the top and left edge and the dark base course on the bottom row.")
    add("6. `data/tile_classes_ship.json` is the walkable answer for every tile and is the file the collision "
        "layer should read. It marks the hatch and the rail by name, and it carries the flag that opens the hatch.")
    add("")
    add("## What this set does not do")
    add("")
    add("1. **It does not repaint the ship's ten colours.** The palette is the one `make_env_ship.py` already "
        "uses for the ship battle strip, so the deck and the fight behind it are the same steel.")
    add("2. **It is not the wardroom.** The wooden wardroom floor, the table and the bunk are Percy's room and the "
        "wooded tiles in `make_env_ship.py`; this card is the steel the fight starts on.")
    add("3. **It carries no lettering.** The terminal's text rows are the rows, not words: a tile that baked in a "
        "line of log text would freeze one frame of dialogue into the map. The words come from the dialogue layer.")
    add("4. **It does not edit `data/maps/all.json`.** That row is read only for this card. Its `H` cell is "
        "written as walkable (collision 0) and gated by `story_flag`; if the wiring moves to this class file the "
        "closed hatch cell should become collision 2, and that is a change for the wiring card, not this one.")
    add("5. **It does not light the deck.** A lamp pool on a wet plate needs a lit-plate tile in a fifth palette, "
        "and four is all a screen has; the bulkhead lamp's spill stops at its own tile, which is the same "
        "limitation the drive set recorded.")
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


DECK = {
    "note": ("the ship's deck at the rail, assembled only from this sheet: plates with the walkway line, "
             "grating and hazard paint at the engine space, the closed hatch and the open one beside it, the "
             "bulkhead and its lamp, the rail above the water, and the log terminal on the wall behind. The "
             "black at the top is the backdrop, which the rail sits against."),
    "rows": [
        (64, "bulkhead_rivet"),
        (80, "deck_plate"),
        (96, "deck_plate"),
        (112, "deck_line"),
        (128, "deck_plate"),
        (144, "deck_plate_worn"),
        (160, "deck_plate"),
    ],
    "water_rows": [(176, "water_edge"), (192, "water_swell"), (208, "water_deep"), (224, "water_swell")],
    "objects": [
        ("log_terminal", 16, 64), ("bulkhead_light", 48, 64), ("log_terminal", 80, 64),
        ("bulkhead_rivet", 112, 64), ("porthole", 144, 64), ("bulkhead_light", 176, 64),
        ("bulkhead_rivet", 208, 64),
        ("hatch_closed", 64, 128), ("hatch_open", 96, 128), ("crate", 16, 144),
        ("locker", 32, 144), ("pipe_run", 208, 112), ("hazard_stripes", 176, 144),
        ("deck_grating", 176, 80), ("deck_grating_cross", 192, 80),
        ("deck_grating_cross", 176, 96), ("deck_grating", 192, 96),
        ("deck_grating", 208, 80), ("deck_grating_cross", 224, 80),
        ("deck_grating_cross", 208, 96), ("deck_grating", 224, 96),
    ],
    "rail_rows": [(160, "rail_bar")],
    "rail_posts": [("rail_post", 0, 160), ("rail_post", 96, 160), ("rail_post", 192, 160)],
}


def compose_deck(by_name):
    frame = Image.new("RGBA", (256, 240), COLOUR[BACKDROP])
    for y, name in DECK["rows"]:
        for cell in range(0, 256, TILE):
            frame.paste(by_name[name], (cell, y))
    for y, name in DECK["water_rows"]:
        for cell in range(0, 256, TILE):
            frame.paste(by_name[name], (cell, y))
    for name, x, y in DECK["objects"]:
        frame.paste(by_name[name], (x, y))
    for y, name in DECK["rail_rows"]:
        for cell in range(0, 256, TILE):
            frame.paste(by_name[name], (cell, y))
    for name, x, y in DECK["rail_posts"]:
        frame.paste(by_name[name], (x, y))
    return frame


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw the ship interior tile set.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if the PNG on disk is stale")
    args = parser.parse_args(argv)

    rendered, sheet = build()
    facts, failures = measure_sheet(sheet, rendered)

    if args.check:
        if not os.path.isfile(SHEET_PNG):
            print("make_ship_tiles: no sheet on disk")
            return 1
        with open(SHEET_PNG, "rb") as handle:
            on_disk = hashlib.sha256(handle.read()).hexdigest()
        buffer = os.path.join(OUTPUT, "_ship_tiles_stale_probe.png")
        os.makedirs(OUTPUT, exist_ok=True)
        sheet.save(buffer)
        with open(buffer, "rb") as handle:
            fresh = hashlib.sha256(handle.read()).hexdigest()
        os.remove(buffer)
        print("make_ship_tiles: %s" % ("fresh" if on_disk == fresh else "STALE"))
        return 0 if on_disk == fresh else 1

    by_name = {item["name"]: item["image"] for item in rendered}
    write_png(SHEET_PNG, sheet)
    write_png(os.path.join(OUTPUT, "ship_tiles_3x.png"), contact_sheet(sheet))
    write_png(os.path.join(OUTPUT, "ship_deck_preview.png"), compose_deck(by_name))
    write_json(os.path.join(OUTPUT, "ship_deck_preview.json"), {
        "format": 1, "kind": "frame_note", "frame": "ship_deck_preview.png", "card": CARD,
        "backdrop": {"entry": ENTRY_OF_ROLE[BACKDROP], "hex": HEX_OF_ROLE[BACKDROP]},
        "note": DECK["note"],
    })

    code, output = run_nes_check()
    nes = {"tool": "tools/nes_check.py", "args": "--type background --backdrop #000000",
           "exit": code, "pass": code == 0, "output": output}
    if code != 0:
        failures.append("the NES tile check failed (exit %d)" % code)

    data = manifest(rendered, sheet, facts, nes)
    write_json(SHEET_JSON, data)
    write_json(CLASS_JSON, class_json(rendered))
    write_text(TILES_MD, tiles_markdown(rendered, data) + "\n")

    print("make_ship_tiles: %d tiles, %d colours, sheet %dx%d"
          % (len(rendered), facts["colours"], sheet.width, sheet.height))
    print("  worst 16x16 area: %d non backdrop colours (%s), the NES allows 3"
          % (facts["worst_area_colours"], facts["worst_area_tile"]))
    print("  every tile 16x16: %s" % ("yes" if facts["size_sixteen"] else "NO"))
    print("  classes: %d walkable, %d not walkable, %d climbable"
          % (facts["walkable"], facts["not_walkable"], facts["climbable"]))
    print("  marks: hatch closed %d open %d, rail post %d bar %d"
          % (data["marks"]["hatch"]["closed"], data["marks"]["hatch"]["open"],
             data["marks"]["rail"]["post"], data["marks"]["rail"]["bar"]))
    print("  nes_check: exit %d" % code)
    for line in output.splitlines():
        print("    %s" % line)
    for line in failures:
        print("  FAIL %s" % line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
