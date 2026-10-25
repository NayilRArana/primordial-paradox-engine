#!/usr/bin/env python3
"""make_drive_tiles.py: the drive's road, gantry and barrier tile set (card t_d0e73725, DRIVE-TILES).

What this draws, and to which rules:

1. Twenty four 16x16 tiles that read as the M3 corridor at night from the side: eight road surface tiles,
   eight night roadside tiles, and eight gantry and barrier tiles. The card names four things (the corridor
   surface, the gantry sign, the barrier, the night roadside) and this sheet carries all four, plus the
   shoulder and the lane markings they imply.
2. The geometry is derived from THIS repo's OSM extract, at the repo's own tile scale. tools/osm_to_map.py
   fixes 8 m to a 16 px tile, so one pixel is 0.5 m, and every number below follows from that and from tags
   that are in data/osm_cache/:
     - the carriageway is 2 tiles wide because osm_to_map.py paints a road_major 2 tiles wide, which at
       8 m a tile is 16 m: three 3.65 m lanes plus a 3.3 m hard shoulder is 14.3 m, so it fits and a
       single tile could not hold it;
     - the lane line is a 2 m mark and a 6 m gap (4 px on, 12 px off), which is exactly one 8 m tile. The
       motorway's own 2 m mark and 7 m gap is a 9 m cycle and would need a 3 tile repeat, which this sheet
       does not guarantee, so the tile carries the 8 m cycle and says so;
     - a 3.65 m lane is 7 px, the 7 m width tagged on A3211 Victoria Embankment is 14 px of the 16 px tile,
       and a 1 px line is 0.5 m, thicker than the 0.15 m paint on the road, because the pixel is the
       narrowest thing the PPU draws.
3. Colours are ROLES from data/palette.json, and each role resolves to a Ricoh 2C02 entry through
   tools/art/nes_snap.py's NIGHT_TABLE, which is the same bridge the drive layers already use. That means
   this sheet carries exactly the entries tools/nes_check.py and the runtime see, and no pixel is an
   approximation of a 2C02 output. Nine roles, nine distinct entries, against the card's ceiling of 16.
4. Every tile draws from one of four background palettes of three roles plus the shared backdrop $0F, so
   no 16x16 attribute area can carry a fourth colour. That is the rule tools/nes_check.py measures.
5. The blob test of knowledge/SPRITE-CRAFT.md section 8.5 is measured per tile and written into the
   manifest. The four object tiles are gated on it; the pattern tiles (road, verge, hedge) and the two
   light tiles are reported with their waivers named, because the test was written for a character
   silhouette and paving is structure by repetition.

Outputs:
    assets/tiles/drive/drive_tiles.png          the sheet, 8 by 3 cells of 16x16, 24 tiles
    assets/tiles/drive/drive_tiles.json         the tileset manifest: palettes, roles, tiles, blob numbers
    assets/tiles/drive/TILES.md                 the tile table the map wiring reads
    data/tile_classes_drive.json                every tile walkable or not, with the ODbL line in its header
    output/drive_tiles_3x.png                   3x contact sheet
    output/drive_corridor_preview.png           256x240 mock of the corridor, composed from the sheet
    output/drive_gantry_preview.png             256x240 mock of the gantry and barrier, same sheet

Usage:
    python tools/art/make_drive_tiles.py
    python tools/art/make_drive_tiles.py --check      # write nothing, exit 1 if the PNG on disk is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "assets", "tiles", "drive")
SHEET_PNG = os.path.join(OUT_DIR, "drive_tiles.png")
SHEET_JSON = os.path.join(OUT_DIR, "drive_tiles.json")
TILES_MD = os.path.join(OUT_DIR, "TILES.md")
CLASS_JSON = os.path.join(ROOT, "data", "tile_classes_drive.json")
OUTPUT = os.path.join(ROOT, "output")

TILE = 16
COLUMNS = 8
BACKDROP_ROLE = "grey_0"

sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
import nes_snap  # noqa: E402  the project's curated project palette to 2C02 bridge

ODBL = ("(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, "
        "https://www.openstreetmap.org/copyright")

# -----------------------------------------------------------------------------------------------------------------
# The scale, derived rather than chosen. tools/osm_to_map.py: METRES_PER_TILE = 8.0 at TILE_PX = 16, so one pixel
# is 0.5 m and every figure in this file can be re-derived from that one line.

METRES_PER_TILE = 8.0
METRES_PER_PIXEL = METRES_PER_TILE / TILE
LANE_METRES = 3.65                      # a UK motorway lane, 7 px at this scale
LANE_PIXELS = int(round(LANE_METRES / METRES_PER_PIXEL))
CORRIDOR_TILES = 2                      # osm_to_map.py paints road_major 2 tiles wide
SHOULDER_METRES = 3.3                   # hard shoulder, 7 px
EDGE_LINE_PIXELS = 1                    # 0.5 m: the narrowest line the PPU can draw
DASH_PIXELS = 4                         # 2 m mark
GAP_PIXELS = 12                         # 6 m gap, so the 8 m tile is exactly one cycle

# -----------------------------------------------------------------------------------------------------------------
# The role to 2C02 entry bridge. The role is a name in data/palette.json, the index is that role's position in the
# file, and the entry is what tools/art/nes_snap.py's NIGHT_TABLE turns it into. The table is imported, not copied,
# so this set can never drift from the drive layers.

ROLE = {
    "asphalt": ("grey_1", 1, "the tarmac, and the steel of the gantry in the dark"),
    "dim": ("grey_3", 3, "road grain, the shade under a line, the barrier face"),
    "bright": ("grey_5", 5, "lane paint, the sign border, the lit rail edge"),
    "green_deep": ("moss_1", 25, "the verge floor and the mass of the hedge"),
    "green_mid": ("moss_2", 26, "the grass blades and the kerb's grass above it"),
    "green_lit": ("moss_3", 27, "the gantry sign's face, as the drive's own sign uses it"),
    "green_pale": ("moss_5", 29, "the moonlit tips of the grass and the hedge's top edge"),
    "stone_mid": ("stone_2", 32, "the kerb face, the marker post, the lamp column"),
    "gold": ("gold_5", 41, "the sodium lamp head and the marker's reflector"),
}

# The four background palettes. A tile draws from exactly one of them, three roles plus the shared backdrop.
BG_PALETTES = [
    ("bg0_asphalt", ["asphalt", "dim", "bright"],
     "the corridor: tarmac, the shade under a line, the paint"),
    ("bg1_verge", ["green_deep", "green_mid", "green_pale"],
     "the night verge: the floor, the blades, the moonlit tips"),
    ("bg2_sign", ["green_lit", "green_mid", "bright"],
     "the gantry's sign face, its dark rear, and the lit border"),
    ("bg3_lamp", ["gold", "stone_mid", "green_mid"],
     "the roadside fittings: the sodium head, the stone, the grass at their feet"),
]

# Which fact in the extract each tile leans on. Every one of these is a real element or tag count in
# data/osm_cache/, except the three marked SPEC, which are the motorway features the extracts do not contain.
SRC = {
    "a33_lanes": "A33 Town Quay way/8150576, highway=primary, lanes=3, surface=asphalt, lit=yes, oneway=yes, 30 mph (data/osm_cache/southampton_town_quay.json)",
    "a33_lanes4": "A33 way/24594762, highway=primary, lanes=4, surface=asphalt, lit=yes (data/osm_cache/southampton_town_quay.json)",
    "width7": "A3211 Victoria Embankment way/236139546, width=7, lane_markings=no, oneway=yes, lit=yes (data/osm_cache/westminster_big_ben.json)",
    "lit": "lit=yes is tagged on 125 of the 237 highway ways in data/osm_cache/southampton_town_quay.json",
    "dest": "Bridge Street way/406370787, destination:lanes:backward=A3211|A23: a sign that names the destination of the lanes under it (data/osm_cache/westminster_big_ben.json)",
    "shoulder_no": "shoulder=no is tagged on 9 primary ways in data/osm_cache/westminster_big_ben.json (Parliament Square, Westminster Bridge, Broad Sanctuary), so a hard shoulder is not in the extract",
    "barrier_none": "the extracts carry barrier= only 4 times (city_wall twice, wall twice) and no safety barrier, so the motorway barrier is not in the extract",
    "motorway_spec": "SPEC: the M3 is a motorway, so the corridor has a hard shoulder and a safety barrier; the drive shot list puts a gantry over it (knowledge/DRIVE-SHOT-LIST.md sections 3 and 5)",
}

# name, char, palette, painter, gated on the blob test, note, source key, walkable, why that class
TILES = []


def tile(name, char, palette, painter, gated, note, source, walkable, walk_why):
    TILES.append({"name": name, "char": char, "palette": palette, "painter": painter, "gated": gated,
                  "note": note, "source": source, "walkable": walkable, "walk_why": walk_why})


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
# Grounds.

def grain(c, seed, count=24, top=0, bottom=15, role="dim", cover="asphalt"):
    """Tarmac grain: a fixed irregular scatter, not a rule, so the seam of the tile never marches.

    A modulo rule draws one pixel a row and the eye locks onto the diagonal: that is the difference between
    grit and a dotted line, and it is the only reason this is random with a fixed seed per tile. `cover` is the
    tone the grain is allowed to replace, so a pass never eats a line that was already drawn.
    """
    rng = random.Random(seed * 7919 + 13)
    placed = 0
    guard = 0
    while placed < count and guard < 600:
        guard += 1
        x = rng.randrange(TILE)
        y = rng.randrange(top, bottom + 1)
        if c.rows()[y][x] in (None, cover):
            c.put(x, y, role)
            placed += 1


def road(c, seed=1):
    c.fill("asphalt")
    grain(c, seed)


def grass_blades(c, strokes, floor=15, tip="green_pale"):
    """Vertical blades rising from the tile's floor; the tall ones catch the moon at the top."""
    for x, height in strokes:
        for y in range(floor - height + 1, floor + 1):
            c.put(x, y, "green_mid")
        if height >= 5:
            c.put(x, floor - height + 1, tip)


# -----------------------------------------------------------------------------------------------------------------
# Row 1: the corridor surface, eight tiles, all in bg0_asphalt.

def t_road_surface(c):
    road(c, 1)


def t_road_surface_worn(c):
    road(c, 2)
    # A reinstatement seam: 0.5 m of new tarmac, one pixel, stepping once so it does not read as a ruled line.
    c.hline(9, 0, 6, "dim")
    c.hline(10, 7, 12, "dim")
    c.hline(9, 13, 15, "dim")
    c.put(4, 11, "dim")
    c.put(5, 11, "dim")


def t_road_lane_dash(c):
    road(c, 3)
    # 2 m of paint at 4 px, then 12 px of tarmac: one 8 m tile is one cycle.
    c.hline(7, 0, DASH_PIXELS - 1, "bright")
    c.hline(8, 0, DASH_PIXELS, "dim")


def t_road_edge_line(c):
    road(c, 4)
    c.hline(7, 0, 15, "bright")
    c.hline(8, 0, 15, "dim")


def t_road_shoulder(c):
    road(c, 5)
    # The hard shoulder: a continuous white line, then a rougher, darker 3.3 m of tarmac.
    c.hline(9, 0, 15, "bright")
    c.rect(0, 10, 16, 6, "dim")
    grain(c, 55, count=14, top=10, bottom=15, role="asphalt", cover="dim")


def t_road_wet(c):
    road(c, 6)
    # Rain on the surface: the sheen is a dim streak, and the glints are single pixels of paint white.
    for (y, x0, x1) in ((3, 2, 9), (6, 5, 13), (11, 0, 6), (13, 8, 14)):
        c.hline(y, x0, x1, "dim")
    for (x, y) in ((4, 3), (10, 3), (7, 6), (12, 11), (2, 11), (14, 13)):
        c.put(x, y, "bright")


def t_road_stud(c):
    road(c, 7)
    # A cat's eye: 0.5 m of reflector in a 1 m casing, so 2 px in a 4 px shadow.
    c.rect(7, 6, 2, 2, "bright")
    c.hline(9, 6, 9, "dim")


def t_road_single_lane(c):
    road(c, 8)
    # The slip road narrowing: both edges painted, 7 px of lane between them.
    c.hline(4, 0, 15, "bright")
    c.hline(5, 0, 15, "dim")
    c.hline(11, 0, 15, "bright")
    c.hline(12, 0, 15, "dim")


# -----------------------------------------------------------------------------------------------------------------
# Row 2: the night roadside, four tiles in bg1_verge and four in bg3_lamp.

def t_verge_grass(c):
    c.fill("green_deep")
    # Two passes: the far grass is short, so the tile is a bank and not a flat slab with a fringe.
    grass_blades(c, [(2, 4), (6, 3), (11, 4), (14, 3)], floor=8)
    grass_blades(c, [(1, 5), (3, 3), (5, 6), (7, 4), (9, 7), (11, 3), (13, 5), (15, 4)])


def t_verge_tuft(c):
    c.fill("green_deep")
    grass_blades(c, [(3, 8), (4, 10), (5, 7), (6, 9), (7, 6), (8, 8), (10, 5), (12, 4)])
    # One blade leans, so the clump is not a comb.
    c.put(9, 6, "green_mid")
    c.put(9, 7, "green_mid")


def t_hedge_night(c):
    c.fill("green_deep")
    c.rect(0, 3, 16, 13, "green_mid")
    # The top of the hedge is the only edge the moon reaches.
    for x in range(0, 16, 2):
        c.put(x, 3, "green_pale")
    c.put(1, 2, "green_pale")
    c.put(9, 2, "green_pale")
    for (x0, y0, w, h) in ((2, 6, 2, 3), (9, 9, 3, 2), (13, 5, 2, 4), (5, 12, 2, 3)):
        c.rect(x0, y0, w, h, "green_deep")


def t_verge_shadow(c):
    c.fill("green_deep")
    c.rect(0, 0, 16, 5, "green_mid")
    for (x, y) in ((3, 9), (9, 12), (13, 10), (6, 14)):
        c.put(x, y, "green_mid")


def t_kerb(c):
    c.rect(0, 0, 16, 6, "green_mid")
    c.rect(0, 6, 16, 10, "stone_mid")
    # Kerb joints are shadow, so they are the backdrop and not a fourth colour.
    c.vline(0, 6, 15, None)
    c.vline(8, 6, 15, None)


def t_marker_post(c):
    c.rect(0, 13, 16, 3, "green_mid")
    c.rect(6, 2, 2, 12, "stone_mid")
    c.vline(8, 2, 13, None)
    # The reflector: 1 m of amber, which is what a driver's headlights pick up first.
    c.rect(6, 5, 2, 2, "gold")
    # The shadow the post throws at its foot, so the silhouette meets the grass with a dark line.
    c.hline(14, 5, 11, None)
    c.hline(15, 4, 12, None)


def t_lamp_post(c):
    c.rect(0, 14, 16, 2, "green_mid")
    c.rect(7, 0, 2, 14, "stone_mid")
    c.rect(5, 13, 6, 2, "stone_mid")
    c.vline(9, 0, 12, None)
    c.hline(15, 4, 12, None)


def t_lamp_head(c):
    c.rect(4, 0, 9, 3, "stone_mid")
    c.rect(4, 3, 9, 4, "gold")
    c.hline(3, 4, 12, "gold")
    # The cone of light the head throws, four rows of falling density.
    for (y, xs) in ((7, (5, 7, 9, 11)), (8, (4, 6, 8, 10, 12)), (9, (5, 7, 9, 11)), (10, (7, 9))):
        for x in xs:
            c.put(x, y, "gold")


# -----------------------------------------------------------------------------------------------------------------
# Row 3: the gantry and the barrier, five tiles in bg0_asphalt and three in bg2_sign.

def t_gantry_beam(c):
    c.fill("asphalt")
    c.hline(1, 0, 15, "dim")
    c.hline(14, 0, 15, "dim")
    # Two chords and a zigzag between them: a lattice at 16 px, not a solid bar.
    for x in range(0, 16, 4):
        c.put(x, 1, "bright")
        c.put(x + 2, 14, "bright")
    for k in range(8):
        c.put(1 + 2 * k, 2 + k, "dim")
        c.put(2 + 2 * k, 13 - k, "dim")


def t_gantry_leg(c):
    c.fill("asphalt")
    c.vline(2, 0, 15, "dim")
    c.vline(13, 0, 15, "dim")
    for y in (0, 5, 10, 15):
        c.put(2, y, "bright")
    for y in (3, 8, 13):
        c.put(13, y, "bright")
    for k in range(8):
        c.put(3 + k, 1 + 2 * k, "dim")
        c.put(12 - k, 2 + 2 * k, "dim")


def t_gantry_sign_panel(c):
    c.fill("green_lit")
    c.hline(1, 0, 15, "bright")
    c.hline(14, 0, 15, "bright")
    c.vline(0, 1, 14, "bright")
    c.vline(15, 1, 14, "bright")
    # The panel's own lower shadow, so the sign does not float over the beam behind it.
    c.hline(15, 0, 15, "green_mid")


def t_gantry_sign_edge(c):
    c.fill("green_lit")
    c.hline(0, 0, 15, "bright")
    for x in range(0, 16, 2):
        c.put(x, 1, "bright")
    c.hline(14, 0, 15, "green_mid")
    c.hline(15, 0, 15, None)


def t_gantry_sign_back(c):
    c.fill("green_mid")
    for (x, y) in ((1, 1), (5, 3), (9, 1), (13, 4), (3, 7), (11, 9), (6, 12), (14, 13)):
        c.put(x, y, "green_lit")
    c.hline(0, 0, 15, "bright")
    c.hline(15, 0, 15, None)


def t_barrier_rail(c):
    c.fill("asphalt")
    # A steel safety barrier in two bands, each with the lit top edge a passing lamp finds.
    c.rect(0, 4, 16, 2, "dim")
    c.hline(4, 0, 15, "bright")
    c.rect(0, 9, 16, 2, "dim")
    c.hline(9, 0, 15, "bright")
    for x in range(0, 16, 3):
        c.put(x, 6, "dim")
        c.put(x + 1, 11, "dim")


def t_barrier_post(c):
    c.fill("asphalt")
    c.rect(6, 0, 3, 16, "dim")
    c.put(6, 2, "bright")
    c.put(6, 13, "bright")
    c.vline(9, 0, 15, None)


def t_barrier_end(c):
    c.fill("asphalt")
    for i in range(11):
        c.put(2 + i, 15 - i, "dim")
        c.put(3 + i, 15 - i, "dim")
    c.put(13, 4, "bright")
    c.put(14, 3, "bright")
    c.rect(1, 14, 6, 2, "dim")


# -----------------------------------------------------------------------------------------------------------------
# The table. Two and a half dozen tiles, named for what the map wiring asks for.

P = {"asphalt": "bg0_asphalt", "verge": "bg1_verge", "sign": "bg2_sign", "lamp": "bg3_lamp"}
WALK_ROAD = ("walkable", "a road surface: the corridor is driven and walked across")
WALK_VERGE = ("walkable", "open grass: low, and the drive lets you stand on it")
SOLID_FURNITURE = ("not walkable", "a fitting on the verge: a post is a solid")
SOLID_OVERHEAD = ("not walkable", "overhead structure: it blocks the lane it crosses when placed in the ground layer")

tile("road_surface", "a", P["asphalt"], t_road_surface, False,
     "the carriageway between the lines", "a33_lanes", *WALK_ROAD)
tile("road_surface_worn", "b", P["asphalt"], t_road_surface_worn, False,
     "the same tarmac with a reinstatement seam across it", "a33_lanes", *WALK_ROAD)
tile("road_lane_dash", "c", P["asphalt"], t_road_lane_dash, False,
     "the lane line: 2 m of paint in a 6 m gap, one 8 m tile", "a33_lanes4", *WALK_ROAD)
tile("road_edge_line", "d", P["asphalt"], t_road_edge_line, False,
     "the continuous edge line at the outside of the corridor", "a33_lanes", *WALK_ROAD)
tile("road_shoulder", "e", P["asphalt"], t_road_shoulder, False,
     "the hard shoulder, 3.3 m, inside its own white line", "motorway_spec", *WALK_ROAD)
tile("road_wet", "f", P["asphalt"], t_road_wet, False,
     "the surface in rain: the sheen and the glints of shot 4", "a33_lanes", *WALK_ROAD)
tile("road_stud", "g", P["asphalt"], t_road_stud, False,
     "a cat's eye in the lane line, the one thing on the road that reflects", "lit", *WALK_ROAD)
tile("road_single_lane", "h", P["asphalt"], t_road_single_lane, False,
     "the slip road narrowing to one lane, both edges painted", "width7", *WALK_ROAD)
tile("verge_grass", "i", P["verge"], t_verge_grass, False,
     "the night verge: blades on a dark floor, tips catching the moon", "lit", *WALK_VERGE)
tile("verge_tuft", "j", P["verge"], t_verge_tuft, False,
     "a denser clump for the verges between the posts", "lit", *WALK_VERGE)
tile("hedge_night", "k", P["verge"], t_hedge_night, False,
     "the hedge mass that closes the far side of the roadside", "lit",
     "not walkable", "a hedge is a wall of growth: the map treats it as a solid")
tile("verge_shadow", "l", P["verge"], t_verge_shadow, False,
     "the dark band under the hedge, so its foot does not float", "lit", *WALK_VERGE)
tile("kerb", "m", P["lamp"], t_kerb, False,
     "the kerb between verge and tarmac, 3 m of stone across the tile", "width7",
     "walkable", "a kerb is a step of one pixel: crossable, so the map does not block it")
tile("marker_post", "n", P["lamp"], t_marker_post, True,
     "the roadside marker post with its amber reflector", "lit", *SOLID_FURNITURE)
tile("lamp_post", "o", P["lamp"], t_lamp_post, True,
     "the lamp column: sodium lighting is why the extract is tagged lit=yes", "lit", *SOLID_FURNITURE)
tile("lamp_head", "p", P["lamp"], t_lamp_head, True,
     "the sodium head and the first rows of its cone", "lit", *SOLID_OVERHEAD)
tile("gantry_beam", "q", P["asphalt"], t_gantry_beam, False,
     "the gantry's horizontal lattice member", "dest",
     "not walkable", "overhead structure: a beam is not ground")
tile("gantry_leg", "r", P["asphalt"], t_gantry_leg, False,
     "the gantry's upright lattice leg, standing on the verge", "dest", *SOLID_FURNITURE)
tile("gantry_sign_panel", "s", P["sign"], t_gantry_sign_panel, False,
     "the green sign face; the miles come from spr_title_sign, not from this tile", "dest", *SOLID_OVERHEAD)
tile("gantry_sign_edge", "t", P["sign"], t_gantry_sign_edge, False,
     "the panel's lit top rim, for the top row of a two tile sign", "dest", *SOLID_OVERHEAD)
tile("gantry_sign_back", "u", P["sign"], t_gantry_sign_back, False,
     "the rear of the sign, which is what the car sees after it has passed", "dest", *SOLID_OVERHEAD)
tile("barrier_rail", "v", P["asphalt"], t_barrier_rail, False,
     "the steel safety barrier in its two bands", "motorway_spec", *SOLID_FURNITURE)
tile("barrier_post", "w", P["asphalt"], t_barrier_post, False,
     "the post the barrier rail hangs on", "motorway_spec", *SOLID_FURNITURE)
tile("barrier_end", "x", P["asphalt"], t_barrier_end, True,
     "the terminal where a barrier run ramps down into the ground", "motorway_spec", *SOLID_FURNITURE)

PALETTE_OF_ROLE = {}
for _name, _roles, _note in BG_PALETTES:
    for _role in _roles:
        PALETTE_OF_ROLE[_role] = _name

# The dark roles the blob test reads as "dark" on a tile, where the tile's own darkest tone is not the backdrop.
DARK_ROLE = {
    "marker_post": ["stone_mid"],
    "lamp_post": ["stone_mid"],
    "lamp_head": ["stone_mid"],
    "barrier_end": ["dim"],
}


# -----------------------------------------------------------------------------------------------------------------
# Render and measure.

COLOUR = {}
ENTRY_OF_ROLE = {}
HEX_OF_ROLE = {}
WHY_OF_ROLE = {}


def load_colours():
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        nes = json.load(handle)
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        design = json.load(handle)
    entries = {item["index"]: item for item in nes["entries"]}
    outputs = {item["hex"].lower() for item in nes["entries"] if item.get("usable")}
    for key, (role_name, index, why) in ROLE.items():
        if role_name not in design["roles"]:
            raise SystemExit("%s is not a role in data/palette.json" % role_name)
        if design["roles"][role_name] != index:
            raise SystemExit("%s is at index %d in data/palette.json, not %d"
                             % (role_name, design["roles"][role_name], index))
        entry_index = nes_snap.NIGHT_TABLE.get(index)
        if entry_index is None:
            raise SystemExit("%s (index %d) is not in nes_snap's NIGHT_TABLE" % (role_name, index))
        entry = entries[entry_index]
        if not entry.get("usable"):
            raise SystemExit("%s resolves to %s, which the art bible flags unusable" % (role_name, entry["code"]))
        if entry["hex"].lower() not in outputs:
            raise SystemExit("%s resolves to %s, which is not a 2C02 output" % (role_name, entry["code"]))
        ENTRY_OF_ROLE[key] = entry_index
        HEX_OF_ROLE[key] = entry["hex"].lower()
        WHY_OF_ROLE[key] = why
        text = entry["hex"].lower().lstrip("#")
        COLOUR[key] = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), 255)
    # The shared backdrop is $0F black, which is also where the tarmac goes, so a corridor tile spends two
    # non backdrop colours rather than three.
    COLOUR[BACKDROP_ROLE] = (0, 0, 0, 255)


def render_tile(painter):
    canvas = Canvas()
    canvas.fill(None)
    painter(canvas)
    image = Image.new("RGBA", (TILE, TILE), COLOUR[BACKDROP_ROLE])
    pixels = image.load()
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x]
            pixels[x, y] = COLOUR[BACKDROP_ROLE] if role is None else COLOUR[role]
    return image


def luminance(rgb):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def blob_numbers(canvas, extra_dark=None):
    used = {}
    for y in range(TILE):
        for x in range(TILE):
            role = canvas.rows()[y][x]
            key = BACKDROP_ROLE if role is None else role
            used[key] = used.get(key, 0) + 1
    drawn = sum(used.values())
    ordered = sorted(used, key=lambda role: luminance(COLOUR[role]))
    light = ordered[-1]
    dark_roles = set(extra_dark or ()) | {ordered[0], BACKDROP_ROLE}

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
    return {"colours": len(used), "roles": sorted(used), "dark_roles": sorted(dark_roles),
            "lightest_role": light, "lightest_share_percent": light_share,
            "rows_without_dark": rows_without_dark, "horizontal_dark_runs": runs,
            "interior_dark_pixels": interior}


def blob_verdict(numbers, gated):
    if not gated:
        return "reported only: a pattern, a structure or a light source, not a character silhouette"
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


def build():
    load_colours()
    rendered = []
    for entry in TILES:
        canvas = Canvas()
        canvas.fill(None)
        entry["painter"](canvas)
        roles = sorted({role for row in canvas.rows() for role in row if role})
        allowed = {role for (pname, proles, _n) in BG_PALETTES if pname == entry["palette"] for role in proles}
        outside = [role for role in roles if role not in allowed]
        if outside:
            raise SystemExit("%s draws %s outside %s" % (entry["name"], outside, entry["palette"]))
        numbers = blob_numbers(canvas, DARK_ROLE.get(entry["name"]))
        rendered.append({
            "name": entry["name"], "character": entry["char"], "palette": entry["palette"],
            "roles": roles, "note": entry["note"], "source": entry["source"],
            "walkable": entry["walkable"], "walk_why": entry["walk_why"],
            "blob": numbers, "blob_verdict": blob_verdict(numbers, entry["gated"]),
            "blob_gated": entry["gated"], "image": render_tile(entry["painter"]), "canvas": canvas,
        })

    sheet = Image.new("RGBA", (COLUMNS * TILE, ((len(rendered) + COLUMNS - 1) // COLUMNS) * TILE),
                      COLOUR[BACKDROP_ROLE])
    for position, item in enumerate(rendered):
        sheet.paste(item["image"], ((position % COLUMNS) * TILE, (position // COLUMNS) * TILE))
    return rendered, sheet


def measure_sheet(sheet, rendered):
    """The card's three numbers, measured on the written PNG rather than promised."""
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
    backdrop = COLOUR[BACKDROP_ROLE][:3]
    worst = 0
    for position, item in enumerate(rendered):
        tx, ty = position % COLUMNS, position // COLUMNS
        area = set()
        for y in range(TILE):
            for x in range(TILE):
                area.add(sheet.getpixel((tx * TILE + x, ty * TILE + y))[:3])
        count = len(area - {backdrop})
        worst = max(worst, count)
        if count > 3:
            failures.append("tile %d (%s) carries %d non backdrop colours, the NES allows 3"
                            % (position, item["name"], count))
    facts = {"sheet": [sheet.width, sheet.height], "colours": len(used),
             "worst_area_colours": worst, "tiles": len(rendered),
             "walkable": sum(1 for item in rendered if item["walkable"] == "walkable"),
             "not_walkable": sum(1 for item in rendered if item["walkable"] != "walkable")}
    return facts, failures


# -----------------------------------------------------------------------------------------------------------------
# The two mocks. They are composed only from the sheet, so a person looking at them is looking at the tiles.

CORRIDOR = {
    "backdrop": "#000000",
    "note": ("the M3 corridor at night, bands top to bottom: hedge, shadow, grass, tuft, kerb, shoulder, worn surface "
             "with two cat's eyes, the lane line, the wet surface, the edge line, the single lane. The black band "
             "above is the backdrop: sky is a scrolling layer (title_L1_sky), not a tile, and is out of this card."),
    "rows": [
        (96, "hedge_night"), (112, "verge_shadow"), (128, "verge_grass"), (144, "verge_tuft"),
        (160, "kerb"), (176, "road_shoulder"), (192, "road_surface_worn"), (208, "road_lane_dash"),
        (224, "road_wet"),
    ],
    "objects": [
        ("marker_post", 32, 128), ("lamp_post", 208, 112), ("lamp_head", 208, 96), ("road_stud", 80, 192),
        ("road_stud", 208, 192), ("barrier_rail", 0, 144), ("barrier_post", 0, 144),
    ],
}

GANTRY = {
    "backdrop": "#000000",
    "note": ("the gantry over the corridor and a barrier run on the verge, assembled from the same sheet: legs, "
             "beam, sign edge over panel over rear, barrier rail with its posts and its terminal."),
    "rows": [
        (160, "verge_grass"), (176, "verge_shadow"), (192, "road_surface"), (208, "road_edge_line"),
        (224, "road_lane_dash"),
    ],
    "objects": [
        ("barrier_rail", 0, 176), ("barrier_post", 48, 176), ("barrier_post", 112, 176),
        ("barrier_post", 176, 176), ("barrier_end", 232, 176),
        ("gantry_leg", 0, 96), ("gantry_leg", 0, 112), ("gantry_leg", 0, 128), ("gantry_leg", 0, 144),
        ("gantry_leg", 240, 96), ("gantry_leg", 240, 112), ("gantry_leg", 240, 128), ("gantry_leg", 240, 144),
        ("gantry_beam", 16, 96), ("gantry_beam", 32, 96), ("gantry_beam", 48, 96), ("gantry_beam", 64, 96),
        ("gantry_beam", 80, 96), ("gantry_beam", 96, 96), ("gantry_beam", 112, 96), ("gantry_beam", 128, 96),
        ("gantry_beam", 144, 96), ("gantry_beam", 160, 96), ("gantry_beam", 176, 96), ("gantry_beam", 192, 96),
        ("gantry_beam", 208, 96), ("gantry_beam", 224, 96),
        ("gantry_sign_edge", 48, 112), ("gantry_sign_edge", 64, 112), ("gantry_sign_edge", 80, 112),
        ("gantry_sign_edge", 96, 112), ("gantry_sign_edge", 112, 112), ("gantry_sign_edge", 128, 112),
        ("gantry_sign_edge", 144, 112), ("gantry_sign_edge", 160, 112), ("gantry_sign_edge", 176, 112),
        ("gantry_sign_edge", 192, 112),
        ("gantry_sign_panel", 48, 128), ("gantry_sign_panel", 64, 128), ("gantry_sign_panel", 80, 128),
        ("gantry_sign_panel", 96, 128), ("gantry_sign_panel", 112, 128), ("gantry_sign_panel", 128, 128),
        ("gantry_sign_panel", 144, 128), ("gantry_sign_panel", 160, 128), ("gantry_sign_panel", 176, 128),
        ("gantry_sign_panel", 192, 128),
        ("gantry_sign_back", 48, 144), ("gantry_sign_back", 64, 144), ("gantry_sign_back", 80, 144),
        ("gantry_sign_back", 96, 144), ("gantry_sign_back", 112, 144), ("gantry_sign_back", 128, 144),
        ("gantry_sign_back", 144, 144), ("gantry_sign_back", 160, 144), ("gantry_sign_back", 176, 144),
        ("gantry_sign_back", 192, 144),
    ],
}


def compose(layout, by_name):
    frame = Image.new("RGBA", (256, 240), (0, 0, 0, 255))
    for y, name in layout["rows"]:
        tile_image = by_name[name]
        for cell in range(0, 256, TILE):
            frame.paste(tile_image, (cell, y))
    for name, x, y in layout["objects"]:
        frame.paste(by_name[name], (x, y))
    return frame


# -----------------------------------------------------------------------------------------------------------------
# Writers.

def palette_json():
    return [{"name": name, "roles": roles,
             "entries": [ENTRY_OF_ROLE[role] for role in roles],
             "hex": [HEX_OF_ROLE[role] for role in roles], "note": note}
            for (name, roles, note) in BG_PALETTES]


def manifest(rendered, sheet, facts):
    return {
        "format": 1,
        "kind": "tileset",
        "name": "drive_tiles",
        "image": "drive_tiles.png",
        "card": "DRIVE-TILES (t_d0e73725)",
        "odbl": ODBL,
        "odbl_note": ("the corridor's proportions are derived from the OSM extracts in data/osm_cache/, so the derived "
                      "map data this set belongs to carries the ODbL line verbatim; the game's own art and story do not"),
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
        "backdrop": {"entry": ENTRY_OF_ROLE["asphalt"], "hex": "#000000"},
        "rule": ("NES: 1 shared backdrop $0F, 4 background palettes of 3 entries, a 16x16 area carries at most 3 "
                 "colours besides the backdrop, at most 25 colours on screen; every pixel is a 2C02 output"),
        "scale": {
            "metres_per_tile": METRES_PER_TILE,
            "metres_per_pixel": METRES_PER_PIXEL,
            "source": "tools/osm_to_map.py METRES_PER_TILE = 8.0 at TILE_PX = 16",
            "corridor_tiles": CORRIDOR_TILES,
            "lane_pixels": LANE_PIXELS,
            "lane_metres": LANE_METRES,
            "shoulder_metres": SHOULDER_METRES,
            "dash_pixels": DASH_PIXELS, "gap_pixels": GAP_PIXELS,
            "dash_note": ("2 m mark and 6 m gap is one 8 m tile exactly; the motorway's own 2 m mark and 7 m gap is a "
                          "9 m cycle and would need a 3 tile repeat, which this sheet does not guarantee"),
        },
        "sources": SRC,
        "roles": {key: {"role": ROLE[key][0], "palette_json_index": ROLE[key][1],
                        "entry": ENTRY_OF_ROLE[key], "hex": HEX_OF_ROLE[key], "why": WHY_OF_ROLE[key]}
                  for key in sorted(ROLE)},
        "palettes": palette_json(),
        "tiles": [{"index": position, "name": item["name"], "character": item["character"],
                   "palette": item["palette"], "roles": item["roles"], "note": item["note"],
                   "source": item["source"], "walkable": item["walkable"] == "walkable",
                   "walk_reason": item["walk_why"], "blob": item["blob"],
                   "blob_gated": item["blob_gated"], "blob_verdict": item["blob_verdict"]}
                  for position, item in enumerate(rendered)],
        "animation": [],
        "mocks": ["output/drive_corridor_preview.png", "output/drive_gantry_preview.png"],
        "measured": facts,
    }


def class_json(rendered):
    return {
        "format": 1,
        "kind": "tile_classes",
        "name": "drive",
        "card": "DRIVE-TILES (t_d0e73725)",
        "odbl": ODBL,
        "sources": {
            "extracts": [
                {"file": "data/osm_cache/southampton_town_quay.json",
                 "fetched": "2026-10-22T04:05:03+00:00",
                 "used for": "A33 Town Quay way/8150576 lanes=3 asphalt lit=yes; way/24594762 lanes=4; lit=yes on 125 ways"},
                {"file": "data/osm_cache/westminster_big_ben.json",
                 "fetched": "2026-10-21T20:24:00+00:00",
                 "used for": "A3211 Victoria Embankment way/236139546 width=7; Bridge Street way/406370787 destination:lanes:backward; shoulder=no on 9 primary ways"},
                {"file": "data/osm_cache/winchester_high_street.json",
                 "fetched": "2026-10-21T20:24:00+00:00",
                 "used for": "read for lane and surface tags; nothing in this sheet depends on it alone"},
            ],
            "tile_scale": "8 m to a 16 px tile, from tools/osm_to_map.py METRES_PER_TILE",
            "odbl_line_written_by": "this file's own odbl key, above, verbatim",
        },
        "odbl_note": ("the tile geometry (corridor width, lane width, line and dash lengths) is derived from those "
                      "extracts at 8 m per tile, so the class file and the map built from it carry the line above "
                      "verbatim; the game's own art and story do not"),
        "rule": ("every tile in assets/tiles/drive/drive_tiles.png appears here once, by index and by name, with "
                 "walkable true or false and the reason; a tile missing from this file cannot be placed by the map "
                 "wiring"),
        "tile_size": TILE,
        "tilecount": len(rendered),
        "backdrop": {"entry": ENTRY_OF_ROLE["asphalt"], "hex": "#000000"},
        "not_walkable_rule": ("a tile is not walkable when it is a solid (a post, a barrier, a hedge) or when it is "
                              "ground you cannot stand on because something is over it (a sign, a beam)"),
        "tiles": [{"index": position, "name": item["name"], "walkable": item["walkable"] == "walkable",
                   "class": item["walkable"], "reason": item["walk_why"]}
                  for position, item in enumerate(rendered)],
        "counts": {
            "walkable": sum(1 for item in rendered if item["walkable"] == "walkable"),
            "not_walkable": sum(1 for item in rendered if item["walkable"] != "walkable"),
        },
    }


def tiles_markdown(rendered, data):
    lines = []
    add = lines.append
    add("# DRIVE TILES: the tile table the map wiring reads")
    add("")
    add("Drawn by `tools/art/make_drive_tiles.py` for card t_d0e73725. Do not edit by hand: rerun the tool.")
    add("")
    add("The sheet is `drive_tiles.png`, %d by %d, %d cells of 16 x 16, %d tiles used. The manifest beside it "
        "(`drive_tiles.json`) is the machine readable copy of this table, and `data/tile_classes_drive.json` is the "
        "walkable classification the map reads."
        % (data["imagewidth"], data["imageheight"], data["columns"] * data["rows"], data["frames"]))
    add("")
    add("The art root here is the card's `assets/tiles/drive/`, not `game/sprites_src/env/`. R46 QUAY-TILES put its "
        "sheet in the second place while the roadmap declared the first, which the cleanroom recheck recorded as "
        "catalog drift (`knowledge/CLEANROOM-RECHECK-2026-10-24.md`, R46 row). This sheet sits where the card says, "
        "so `tools/sync_art.py` and the map wiring must look here for it. That is a note for the wiring card, not a "
        "change this card makes.")
    add("")
    add("## The scale, and where every number comes from")
    add("")
    add("| fact | value | source |")
    add("|---|---|---|")
    add("| metres per tile | %s | `tools/osm_to_map.py` `METRES_PER_TILE` at `TILE_PX` 16 |" % METRES_PER_TILE)
    add("| metres per pixel | %s | derived: 8 m / 16 px |" % METRES_PER_PIXEL)
    add("| corridor width | %d tiles = 16 m | `tools/osm_to_map.py` paints `road_major` 2 tiles wide; 3 lanes at "
        "3.65 m plus a 3.3 m shoulder is 14.3 m, so one tile cannot hold it |" % CORRIDOR_TILES)
    add("| lane width | %d px = 3.5 m | 3.65 m a lane, rounded to the pixel |" % LANE_PIXELS)
    add("| line paint | %d px = 0.5 m | the narrowest thing the PPU draws; the paint is 0.15 m in life |"
        % EDGE_LINE_PIXELS)
    add("| lane line cycle | %d px on, %d px off = one tile | 2 m mark, 6 m gap: the tile is exactly one cycle |"
        % (DASH_PIXELS, GAP_PIXELS))
    add("")
    add("## The four background palettes")
    add("")
    add("| palette | roles | 2C02 entries | what it draws |")
    add("|---|---|---|---|")
    for (name, roles, note) in BG_PALETTES:
        add("| `%s` | %s | %s | %s |" % (name, ", ".join("`%s`" % role for role in roles),
                                         ", ".join("$%02X" % ENTRY_OF_ROLE[role] for role in roles), note))
    add("")
    add("## The colours")
    add("")
    add("| role | role in data/palette.json | 2C02 entry | hex | why that entry |")
    add("|---|---|---|---|---|")
    for key in sorted(ROLE, key=lambda k: ENTRY_OF_ROLE[k]):
        add("| `%s` | `%s`, index %d | $%02X | `%s` | %s |"
            % (key, ROLE[key][0], ROLE[key][1], ENTRY_OF_ROLE[key], HEX_OF_ROLE[key], WHY_OF_ROLE[key]))
    add("")
    add("%d roles, %d distinct colours on the sheet, against the card's ceiling of 16."
        % (len(ROLE), data["measured"]["colours"]))
    add("")
    add("## The tiles")
    add("")
    add("| # | name | char | palette | walkable | blob test | what it is |")
    add("|---|---|---|---|---|---|---|")
    for position, item in enumerate(rendered):
        numbers = item["blob"]
        add("| %d | `%s` | `%s` | `%s` | %s | %s | %s |"
            % (position, item["name"], item["character"], item["palette"],
               "yes" if item["walkable"] == "walkable" else "no",
               ("%s (light %.0f%%, %d rows no dark, %d runs, %d inner dark)"
                % ("PASS" if item["blob_verdict"] == "pass" else
                   ("n/a" if not item["blob_gated"] else "FAIL"),
                   numbers["lightest_share_percent"], numbers["rows_without_dark"],
                   numbers["horizontal_dark_runs"], numbers["interior_dark_pixels"])),
               item["note"]))
    add("")
    add("## Where each tile's shape comes from")
    add("")
    for key in sorted(SRC):
        add("- **%s**: %s" % (key, SRC[key]))
    add("")
    add("## How to wire it")
    add("")
    add("1. Every tile is 16 x 16, and index i in the sheet is `floor(i / 8)` rows down and `i % 8` cells across.")
    add("2. A tile draws from exactly one background palette, so a 16 x 16 attribute area can never carry a fourth "
        "colour. Give the area the palette named in the table and no other.")
    add("3. The corridor is two tiles wide. Put `road_shoulder` on the outside and `road_lane_dash` between the two "
        "lanes; `road_edge_line` closes the inner edge.")
    add("4. `road_lane_dash` tiles horizontally: 4 px of paint, 12 px of tarmac, one 8 m cycle. Do not scale it.")
    add("5. Objects sit on the ground they stand on: `marker_post`, `lamp_post` and `barrier_end` include the grass "
        "or tarmac at their feet, so a map can place them without a transparency pass.")
    add("6. The sign face carries no lettering. The miles come from `spr_title_sign`'s four frames, which the drive "
        "draws over this panel; a tile that baked in SOUTHAMPTON 55 would freeze one sign into the map.")
    add("7. `data/tile_classes_drive.json` is the walkable answer for every tile and is the file the collision layer "
        "should read; it carries the ODbL line in its header because the geometry is derived OSM data.")
    add("")
    add("## What this set does not do")
    add("")
    add("1. **It is not the whole picture.** Sky, clouds, the downs and the chalk cutting are scrolling layers in "
        "`game/sprites_src/title/`, not tiles; this set is the corridor floor and its fittings.")
    add("2. **There is no hard shoulder source in the extract.** `shoulder=no` is tagged on the Westminster primary "
        "roads, so the shoulder, the safety barrier and the gantry are drawn from the drive's own facts (the M3 is a "
        "motorway) and are marked SPEC in the source table above.")
    add("3. **The lane line is the 8 m cycle, not the 9 m motorway one.** A 2 m mark and a 7 m gap is 9 m and would "
        "need a 3 tile repeat, so this sheet uses the cycle that fits the tile and says so.")
    add("4. **There is no lighting spill across tile edges.** Three colours and the backdrop per area means the "
        "lamp's cone stops at the tile; a spill needs a second lit-surface tile in the lamp palette, which the four "
        "palette budget cannot buy until the wiring card says which palette the scene can spare.")
    add("5. **No cat's eye in amber.** The stud is drawn in paint white because amber lives in the lamp palette and "
        "the corridor palette has no room for it; the amber reflector is on `marker_post` instead.")
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
    parser = argparse.ArgumentParser(description="Draw the drive tile set.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if the PNG on disk is stale")
    args = parser.parse_args(argv)

    rendered, sheet = build()
    by_name = {item["name"]: item["image"] for item in rendered}
    facts, failures = measure_sheet(sheet, rendered)
    data = manifest(rendered, sheet, facts)
    classes = class_json(rendered)
    text = tiles_markdown(rendered, data)

    if args.check:
        if not os.path.isfile(SHEET_PNG):
            print("make_drive_tiles: no sheet on disk")
            return 1
        with open(SHEET_PNG, "rb") as handle:
            on_disk = hashlib.sha256(handle.read()).hexdigest()
        buffer = os.path.join(OUTPUT, "_drive_tiles_stale_probe.png")
        os.makedirs(OUTPUT, exist_ok=True)
        sheet.save(buffer)
        with open(buffer, "rb") as handle:
            fresh = hashlib.sha256(handle.read()).hexdigest()
        os.remove(buffer)
        print("make_drive_tiles: %s" % ("fresh" if on_disk == fresh else "STALE"))
        return 0 if on_disk == fresh else 1

    write_png(SHEET_PNG, sheet)
    write_json(SHEET_JSON, data)
    write_text(TILES_MD, text + "\n")
    write_json(CLASS_JSON, classes)
    write_png(os.path.join(OUTPUT, "drive_tiles_3x.png"), contact_sheet(sheet))

    for name, layout in (("drive_corridor", CORRIDOR), ("drive_gantry", GANTRY)):
        frame = compose(layout, by_name)
        write_png(os.path.join(OUTPUT, "%s_preview.png" % name), frame)
        write_json(os.path.join(OUTPUT, "%s_preview.json" % name), {
            "format": 1, "kind": "frame_note", "frame": "%s_preview.png" % name,
            "card": "DRIVE-TILES (t_d0e73725)",
            "backdrop": {"entry": ENTRY_OF_ROLE["asphalt"], "hex": "#000000"},
            "note": layout["note"],
            "odbl": ODBL,
        })

    print("make_drive_tiles: %d tiles, %d colours, sheet %dx%d"
          % (len(rendered), facts["colours"], sheet.width, sheet.height))
    print("  scale: %.1f m a tile, %.2f m a pixel, lane %d px, dash %d on %d off"
          % (METRES_PER_TILE, METRES_PER_PIXEL, LANE_PIXELS, DASH_PIXELS, GAP_PIXELS))
    print("  worst 16x16 area: %d non backdrop colours (limit 3)" % facts["worst_area_colours"])
    print("  classes: %d walkable, %d not walkable" % (facts["walkable"], facts["not_walkable"]))
    gated = [item for item in rendered if item["blob_gated"]]
    failing = [item for item in gated if item["blob_verdict"] != "pass"]
    print("  blob test: %d gated tile(s), %d pass, %d fail" % (len(gated), len(gated) - len(failing), len(failing)))
    for item in failing:
        print("    FAIL %s: %s" % (item["name"], item["blob_verdict"]))
    for line in failures:
        print("  FAIL %s" % line)
    print("  sheet: %s" % os.path.relpath(SHEET_PNG, ROOT).replace(os.sep, "/"))
    print("  classes: %s" % os.path.relpath(CLASS_JSON, ROOT).replace(os.sep, "/"))
    return 1 if (failures or failing) else 0


if __name__ == "__main__":
    sys.exit(main())
