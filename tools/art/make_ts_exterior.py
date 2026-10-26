#!/usr/bin/env python3
"""make_ts_exterior.py: paint ts_exterior.png, the 16x16 NES exterior tileset for modern Britain.

Why the art is written as characters per tile rather than as a pixel loop with magic numbers: a reviewer can
read one tile and see exactly which palette entry every pixel uses, and the palette key map below turns those
characters into data/nes_palette.json entries by number, so no colour can drift into "nearly NES" without a
KeyError here.

Rules this file obeys; tools/check_ts_exterior.py measures them:
  * every opaque pixel is one of the 5 background palettes below or the shared black backdrop ($0F, entry 15);
  * every 16x16 tile carries at most 3 colours besides the backdrop (one NES attribute area);
  * every 8x8 quarter of a tile carries at most 3 colours (the sprite tile limit);
  * the whole sheet carries 14 distinct colours, under the 25 a frame may show;
  * flat colour bands only; the only dithering is the 2 pixel checker where two entries meet.

THE WALKABLE BAND IS DARK, AND THAT IS MEASURED RATHER THAN FELT (card t_454c1876, 2026-10-25). The party's
four walking sheets carry near white bodies, $30 #fcfcfc (percy, hadrian), $31 #a4e4fc (zander) and $28 #f8b800
(konrad), and ART-BIBLE RULE 0 point 2 refuses a near white body (luminance 0.60 or more) on a light ground
(0.25 or more). So the ground under them has to sit below 0.25 luminance, and this street group has exactly two
entries that do: M $00 #7c7c7c at 0.202 and the shared backdrop $0F at 0.000. L $10 #bcbcbc measures 0.503 and
W $30 0.973, so both are ARCHITECTURE ONLY: roofs, tower and cathedral stone, benches, railings, lamps and signs.
No tile a player can walk on draws either of them, and tools/check_ts_exterior.py check 13 holds that tile by
tile. The three towns' spawn frames measured 36, 88 and 32 pair failures before this and 0 after
(knowledge/PALETTE-RULINGS-2026-10-25.md section 20).

THE PARK IS IN THE SAME BAND NOW, BY THE SAME MEASUREMENT (card t_b01c88ff, 2026-10-25). The park's three
walkable tiles were the last exemption check 13 carried, because they filled with H $2A #58d854 at 0.518: a $30
body on it measures white_blob and $28 measures body_ground. H is now off every walkable grass tile and stays
only on the SOLID planting and the green awning, so bg2_green's three entries, every scene palette and every
area budget are untouched. What is left under a player's feet is G $09 #007800 (0.134) as the field and D $0A
#006800 (0.099) as its shade, with the shared backdrop $0F (0.000) taking over the role H played: the light
accent became the dark accent, in the same shapes, so a tuft still reads at 3.68:1 against the field instead of
3.09:1. Measured on the frame tools/art/make_exterior_maps.py composes for Westminster, at the park cell the
party can reach, in knowledge/PALETTE-RULINGS-2026-10-25.md section 22.

Background tiles on a NES are opaque: the PPU has no transparency on the background layer, so every street
object here is drawn on its own ground (pavement grey under the phone box and the lamp, grass green under the
tree and the hedge). That is also why a prop tile spends one of its 3 colours on its shadow ring.

Tiles are original work drawn for this project. No game art was copied, traced or sampled
(PLAN-V2-2026-10-21.md section 0).

Usage:
    python tools/art/make_ts_exterior.py --root <repo>
"""

from __future__ import annotations

import argparse
import json
import os

from PIL import Image

TILE = 16
COLUMNS = 16
ROWS = 4
SHEET_W = TILE * COLUMNS
SHEET_H = TILE * ROWS

# NES background palettes: 3 entries each plus the one shared backdrop.
# Characters used by the tile art. 'k' is the backdrop, so it is free; it is not one of the 3.
PALETTES = {
    # M and k are the walkable band and L and W are architecture only: see the note at the top of this file.
    "bg0_stone": {"M": 0, "L": 16, "W": 48},      # $00 #7c7c7c, $10 #bcbcbc, $30 #fcfcfc
    "bg1_brick": {"A": 7, "B": 23, "C": 40},      # $07 #881400, $17 #e45c10, $28 #f8b800
    "bg2_green": {"G": 9, "D": 10, "H": 42},      # $09 #007800, $0A #006800, $2A #58d854
    "bg3_water": {"N": 2, "O": 18, "P": 48},      # $02 #0000bc, $12 #0058f8, $30 #fcfcfc
    "bg4_red":   {"M": 0, "S": 22, "W": 48},      # $00 #7c7c7c (shared with stone), $16 #f83800, $30 #fcfcfc
    "bg5_plant": {"G": 9, "A": 7, "M": 0},        # $09 #007800, $07 #881400, $00 #7c7c7c (bark on grass)
}
# bg2_green's H is SOLID ONLY since card t_b01c88ff: the tree canopies, the hedges and the green awning keep it,
# and no walkable grass tile draws it any more, because 0.518 is a light ground under RULE 0 point 2.
BACKDROP_ENTRY = 15
BACKDROP_HEX = "#000000"


class Grid:
    """A 16x16 character grid; 'k' is the shared backdrop."""

    def __init__(self) -> None:
        self.p = [["k" for _ in range(TILE)] for _ in range(TILE)]

    def px(self, x: int, y: int, c: str) -> None:
        if 0 <= x < TILE and 0 <= y < TILE:
            self.p[y][x] = c

    def rect(self, x0: int, y0: int, x1: int, y1: int, c: str) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def hl(self, y: int, x0: int, x1: int, c: str) -> None:
        self.rect(x0, y, x1, y, c)

    def vl(self, x: int, y0: int, y1: int, c: str) -> None:
        self.rect(x, y0, x, y1, c)

    def fill(self, c: str) -> None:
        self.rect(0, 0, TILE - 1, TILE - 1, c)

    def checker(self, c: str, phase: int = 0, step: int = 2) -> None:
        """2 pixel checker: the only dithering this project allows."""
        for y in range(TILE):
            for x in range(TILE):
                if ((x // step) + (y // step) + phase) % 2 == 0:
                    self.px(x, y, c)

    def disc(self, cx: float, cy: float, r: float, c: str) -> None:
        for y in range(TILE):
            for x in range(TILE):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.px(x, y, c)

    def lines(self) -> list[str]:
        return ["".join(row) for row in self.p]


# ----------------------------------------------------------------------------------------------------
# Ground and terrain

def road(variant: int):
    def build(g: Grid) -> None:
        g.fill("M")
        dots = [(2, 2), (9, 5), (5, 11), (13, 13)] if variant == 0 else [(4, 1), (11, 3), (7, 8), (1, 14), (14, 10)]
        for x, y in dots:
            g.rect(x, y, x + 1, y + 1, "k")
        if variant == 1:
            # A worn patch in the asphalt. It used to be L, the only light block on a walkable tile.
            g.rect(6, 6, 8, 7, "k")
    return build


def road_line_v(g: Grid) -> None:
    """Vertical road, broken centre line: 10 px dash, 6 px gap, continuous across tile edges.

    The line is the shared black, not W: a centre line in white is a light ground the party walks on, and a
    white line under a white body is the white blob RULE 0 point 2 refuses. Black on the asphalt's M reads
    at 5.03:1.
    """
    road(0)(g)
    g.rect(7, 0, 8, 9, "k")


def road_line_h(g: Grid) -> None:
    """Horizontal road, the same dash rotated, and the same black line (see road_line_v)."""
    road(1)(g)
    g.rect(0, 7, 9, 8, "k")


def crosswalk(g: Grid) -> None:
    """Zebra bars in the shared black: a crossing is walked, so its bars cannot be W either."""
    g.fill("M")
    for y in (0, 1, 4, 5, 8, 9, 12, 13):
        g.hl(y, 0, TILE - 1, "k")


def kerb(west: bool):
    """The raised edge: a black gutter on the road side, the grey kerbstone, a black shadow, then pavement.

    This tile used to spend all three entries (M, L and W) on an edge, and the party spawns ON a kerb in
    Westminster (tile 16,20 of westminster_sample.json), so it was the single largest light ground in the
    three towns: 80 pixels of $10 and 42 of $30 inside the sprite's own 16x16 box. A grey stone against a
    black gutter reads the same edge without a light entry at all.
    """

    def build(g: Grid) -> None:
        g.fill("M")
        if west:
            g.rect(0, 0, 2, 15, "k")
            g.vl(8, 0, 15, "k")
        else:
            g.rect(13, 0, 15, 15, "k")
            g.vl(7, 0, 15, "k")
    return build


def pavement(variant: int):
    """Flagstones: M slabs with the shared black between them, where the tile used to be one flat L field.

    The old geometry covered all 16x16 with slabs, so both pavement tiles were a single colour with no joint
    at all, and Winchester's spawn tile (pavement_b at 16,19) had a 16x16 box of 256 pixels of one entry, $10.
    A one pixel joint of the shared backdrop costs nothing and gives the surface its texture back.
    """
    bands = [(0, 6), (8, 14)] if variant == 0 else [(0, 4), (6, 10), (12, 14)]

    def build(g: Grid) -> None:
        g.fill("k")
        for x0, x1 in bands:
            for y0, y1 in bands:
                g.rect(x0, y0, x1, y1, "M")
    return build


def pavement_grate(g: Grid) -> None:
    """A drain in the flags: a black opening with grey bars."""
    pavement(0)(g)
    g.rect(3, 4, 12, 11, "k")
    for x in range(4, 12, 2):
        g.vl(x, 5, 10, "M")


def cobbles(pattern: int):
    """Cobbles: M stones with the shared black in the gaps. It used to be M gaps and L stones."""

    def build(g: Grid) -> None:
        g.fill("k")
        if pattern == 0:
            stones = [(1, 1, 3, 2), (5, 1, 3, 2), (9, 1, 3, 2), (13, 1, 2, 2),
                      (1, 4, 3, 2), (5, 4, 3, 2), (9, 4, 3, 2), (13, 4, 2, 2),
                      (1, 7, 3, 2), (5, 7, 3, 2), (9, 7, 3, 2), (13, 7, 2, 2),
                      (1, 10, 3, 2), (5, 10, 3, 2), (9, 10, 3, 2), (13, 10, 2, 2),
                      (1, 13, 3, 2), (5, 13, 3, 2), (9, 13, 3, 2), (13, 13, 2, 2)]
        elif pattern == 1:
            stones = [(2, 2, 3, 2), (7, 2, 3, 2), (12, 2, 3, 2),
                      (0, 5, 3, 2), (4, 5, 3, 2), (9, 5, 3, 2), (14, 5, 1, 2),
                      (2, 8, 3, 2), (7, 8, 3, 2), (12, 8, 3, 2),
                      (0, 11, 3, 2), (4, 11, 3, 2), (9, 11, 4, 2),
                      (2, 14, 3, 1), (7, 14, 3, 1), (12, 14, 3, 1)]
        else:
            stones = [(1, 1, 5, 3), (7, 1, 5, 3), (12, 1, 3, 3),
                      (1, 6, 5, 3), (7, 6, 8, 3),
                      (1, 11, 5, 3), (7, 11, 5, 3), (12, 11, 3, 3)]
        for x, y, w, h in stones:
            g.rect(x, y, x + w - 1, y + h - 1, "M")
    return build


def grass(variant: int):
    """The park's walkable ground: G field, D shade, and the backdrop where the light accent used to be.

    Card t_b01c88ff, 2026-10-25: these three tiles were check 13's only exemption because they drew H $2A at
    0.518, a light ground under RULE 0 point 2, and the party walks in $30, $31 and $28. H is off every walkable
    grass tile now and stays on the SOLID planting (tree canopies, hedges) and the green awning, so the shapes
    below are the ones they always were with the LIGHT accent read as the DARK accent: the backdrop $0F at
    0.000 where H was, at 3.68:1 against the field, and D $0A left holding the mid shade. Two greens 1.23:1
    apart would have been a flat field, which is why the accent moved to black rather than to the shade.
    """
    def build(g: Grid) -> None:
        g.fill("G")
        if variant == 0:
            for y in (0, 4, 8, 12):
                for x in (0, 6, 12):
                    g.rect(x, y, x + 1, y + 1, "D")
            for x, y in [(3, 7), (11, 3), (7, 13), (14, 10)]:
                g.px(x, y, "k")
        elif variant == 1:
            for x, y in [(2, 2), (9, 2), (14, 6), (5, 8), (11, 11), (3, 14)]:
                g.rect(x, y, x + 1, y + 1, "k")
            for x, y in [(6, 4), (0, 10), (13, 15)]:
                g.rect(x, y, x + 1, y + 1, "D")
        else:
            g.checker("D", phase=1, step=2)
            for x, y in [(1, 1), (8, 5), (4, 12), (12, 14)]:
                g.px(x, y, "k")
    return build


def quay(variant: int):
    """Quay stone: M flags with the shared black between them (it used to be M gaps and L flags)."""

    def build(g: Grid) -> None:
        g.fill("k")
        if variant == 0:
            for y in range(0, 16, 5):
                for x in range(0, 16, 8):
                    g.rect(x + 1, y, x + 7, y + 3, "M")
        else:
            for y in range(0, 16, 6):
                for x in range(0, 16, 6):
                    g.rect(x + 1, y + 1, x + 4, y + 4, "M")
    return build


# ----------------------------------------------------------------------------------------------------
# Water and buildings

def water(variant: int):
    def build(g: Grid) -> None:
        g.fill("N")
        shift = 0 if variant == 0 else 3
        if variant == 2:
            for x, y in [(2, 3), (8, 6), (12, 1), (5, 10), (14, 12)]:
                g.rect(x, y, x + 1, y, "O")
            for x, y in [(4, 8), (10, 14)]:
                g.px(x, y, "P")
            return
        for base in (2, 7, 12):
            for start in (1, 9):
                x0 = (start + shift) % 16
                g.rect(x0, base, min(15, x0 + 4), base + 1, "O")
        for x, y in [(5, 2), (13, 7), (2, 12)]:
            px = (x + shift) % 16
            g.px(px, y, "P")
            g.px((px + 1) % 16, y, "P")
    return build


def shore_stone(g: Grid) -> None:
    g.fill("M")
    for cx, cy, r in [(3, 3, 2.2), (10, 2, 2.0), (13, 8, 2.2), (4, 9, 2.4), (9, 12, 2.2)]:
        g.disc(cx, cy, r, "L")
    g.hl(15, 0, 15, "k")


def brick(variant: int):
    def build(g: Grid) -> None:
        g.fill("A")
        course = 4 if variant != 2 else 3
        brick_w = 8 if variant != 2 else 5
        for row, y in enumerate(range(0, 16, course)):
            offset = 0 if row % 2 == 0 else brick_w // 2
            for x in range(-brick_w, 16 + brick_w, brick_w):
                x0 = x + offset
                g.rect(x0, y, x0 + brick_w - 2, y + course - 2, "B")
                if variant == 1:
                    g.hl(y, x0, x0 + brick_w - 2, "C")
                elif variant == 2:
                    g.px(x0 + 1, y, "C")
    return build


def brick_cornice(g: Grid) -> None:
    g.rect(0, 0, 15, 3, "C")
    g.hl(4, 0, 15, "A")
    g.hl(5, 0, 15, "k")
    for row, y in enumerate(range(6, 16, 5)):
        offset = 0 if row % 2 == 0 else 4
        for x in range(-8, 24, 8):
            g.rect(x + offset, y, x + offset + 6, y + 3, "B")


def shop_front(g: Grid) -> None:
    g.fill("A")
    g.rect(2, 2, 13, 11, "k")
    g.rect(3, 3, 4, 10, "C")
    g.rect(9, 6, 10, 9, "C")
    g.rect(1, 12, 14, 15, "B")
    g.hl(12, 1, 14, "A")
    g.hl(14, 1, 14, "A")


def shop_door(g: Grid) -> None:
    g.fill("A")
    g.rect(3, 2, 12, 8, "k")
    g.rect(4, 3, 5, 5, "C")
    g.rect(3, 9, 12, 14, "B")
    g.hl(11, 3, 12, "A")
    g.rect(11, 9, 12, 10, "C")


def window(lit: bool):
    def build(g: Grid) -> None:
        g.fill("A")
        if lit:
            g.rect(2, 2, 13, 12, "C")
            g.vl(8, 2, 12, "k")
            g.hl(6, 2, 13, "k")
            g.hl(13, 1, 14, "k")
        else:
            g.rect(2, 2, 13, 12, "k")
            g.rect(4, 3, 5, 10, "B")
            g.vl(8, 2, 12, "A")
            g.hl(6, 2, 13, "A")
            g.hl(13, 1, 14, "A")
    return build


def awning(red: bool):
    def build(g: Grid) -> None:
        light, dark = ("W", "S") if red else ("H", "G")
        shadow = "M" if red else "D"
        g.rect(0, 0, 15, 12, light)
        for x in range(0, 16, 4):
            g.rect(x, 0, x + 1, 12, dark)
        for x in range(0, 16, 2):
            g.rect(x, 13, x + 1, 14, dark if (x // 2) % 2 == 0 else light)
        g.hl(15, 0, 15, shadow)
    return build


def door(variant: int):
    def build(g: Grid) -> None:
        g.fill("A")
        g.rect(2, 2, 13, 14, "B")
        if variant == 0:
            for x in (5, 8, 11):
                g.vl(x, 3, 13, "A")
            g.rect(11, 7, 12, 8, "C")
        else:
            g.rect(2, 0, 13, 2, "k")
            g.rect(2, 3, 13, 4, "k")
            g.rect(6, 7, 9, 8, "C")
        g.hl(15, 2, 13, "k")
    return build


def roof_slate(g: Grid) -> None:
    g.fill("M")
    for row, y in enumerate(range(0, 16, 4)):
        offset = 0 if row % 2 == 0 else 4
        for x in range(-8, 24, 8):
            g.rect(x + offset, y, x + offset + 6, y, "L")
            g.hl(y + 3, x + offset, x + offset + 6, "k")


# ----------------------------------------------------------------------------------------------------
# Street furniture and planting. Every one is drawn on its own ground: M pavement, G grass.

def phone_box_top(g: Grid) -> None:
    g.fill("M")
    g.rect(2, 0, 13, 15, "k")
    g.rect(3, 0, 12, 3, "S")
    g.rect(3, 5, 12, 9, "W")
    for x, y in [(4, 6), (5, 6), (6, 6), (8, 6), (9, 6), (11, 6),
                 (4, 8), (6, 8), (8, 8), (11, 8)]:
        g.px(x, y, "S")
    g.rect(3, 10, 12, 15, "S")
    g.vl(3, 10, 15, "k")


def phone_box_body(g: Grid) -> None:
    g.fill("M")
    g.rect(2, 0, 13, 15, "k")
    g.rect(3, 0, 12, 12, "S")
    for y in (1, 5, 9):
        for x in (4, 7, 10):
            g.rect(x, y, x + 1, y + 2, "k")
    g.rect(3, 13, 12, 15, "S")
    g.hl(13, 3, 12, "k")


def post_box(g: Grid) -> None:
    g.fill("M")
    g.rect(3, 1, 12, 15, "k")
    g.rect(4, 2, 11, 14, "S")
    g.rect(6, 4, 9, 5, "k")
    g.hl(8, 5, 10, "k")
    g.rect(6, 11, 9, 12, "W")


def lamp_head(g: Grid) -> None:
    g.fill("M")
    g.rect(4, 0, 11, 15, "k")
    g.rect(5, 1, 10, 5, "L")
    g.rect(6, 6, 9, 9, "W")
    g.rect(6, 10, 9, 15, "L")


def lamp_post(g: Grid) -> None:
    g.fill("M")
    g.rect(5, 0, 10, 15, "k")
    g.rect(6, 0, 9, 14, "L")
    g.vl(7, 0, 14, "W")
    g.rect(4, 14, 11, 15, "L")


def bollard(g: Grid) -> None:
    g.fill("M")
    g.rect(4, 1, 11, 14, "k")
    g.rect(5, 2, 10, 13, "L")
    g.rect(5, 0, 10, 0, "W")


def bench(g: Grid) -> None:
    g.fill("M")
    g.rect(0, 1, 15, 3, "L")
    g.hl(2, 0, 15, "k")
    g.rect(0, 5, 15, 7, "L")
    g.hl(6, 0, 15, "k")
    for x in (2, 12):
        g.rect(x, 8, x + 1, 14, "L")
    g.hl(15, 1, 14, "k")


def railing(gate: bool):
    def build(g: Grid) -> None:
        g.fill("M")
        g.rect(0, 0, 15, 1, "L")
        for x in range(1, 16, 4):
            g.vl(x, 2, 14, "k")
        g.hl(5, 0, 15, "L")
        g.hl(10, 0, 15, "L")
        if gate:
            g.rect(0, 0, 6, 15, "L")
            g.rect(1, 2, 5, 13, "k")
            g.vl(3, 2, 13, "L")
    return build


def traffic_top(g: Grid) -> None:
    g.fill("M")
    g.rect(3, 0, 12, 15, "k")
    g.rect(4, 1, 11, 14, "S")
    g.rect(5, 2, 10, 6, "W")
    g.rect(5, 7, 10, 10, "k")
    g.rect(5, 11, 10, 14, "k")


def traffic_body(g: Grid) -> None:
    g.fill("M")
    g.rect(3, 0, 12, 15, "k")
    g.rect(4, 1, 11, 12, "S")
    g.rect(5, 2, 10, 5, "k")
    g.rect(5, 7, 10, 10, "k")
    g.vl(5, 1, 12, "W")


def tree_canopy(variant: int):
    def build(g: Grid) -> None:
        g.fill("G")
        for y in range(TILE):
            for x in range(TILE):
                dx = (x - 7.5) / 7.4
                dy = (y - 7.0) / 5.6
                if dx * dx + dy * dy > 1.0:
                    continue
                if dx * dx + dy * dy > 0.74:
                    g.px(x, y, "k")
                else:
                    g.px(x, y, "D" if (x + y) % 7 else "G")
        for y in range(2, 6):
            for x in range(3, 13):
                dx = (x - 7.5) / 7.4
                dy = (y - 7.0) / 5.6
                if dx * dx + dy * dy < 0.6:
                    g.px(x, y, "H")
        for x, y in ([(2, 9), (13, 8)] if variant == 0 else [(4, 10), (11, 10), (7, 4)]):
            g.rect(x, y, x + 1, y + 1, "H")
    return build


def tree_trunk(g: Grid) -> None:
    g.fill("G")
    g.rect(5, 0, 10, 15, "k")
    g.rect(6, 0, 9, 15, "A")
    g.vl(7, 0, 15, "M")


def hedge(variant: int):
    def build(g: Grid) -> None:
        g.fill("G")
        g.hl(0, 0, 15, "k")
        g.hl(1, 0, 15, "k")
        if variant == 0:
            for y in range(2, 16, 3):
                for x in (1, 7, 13):
                    g.rect(x, y, x + 1, y + 1, "D")
            for x in (3, 10, 14):
                g.px(x, 3, "H")
        else:
            for y in (3, 8, 13):
                g.hl(y, 0, 15, "D")
            for x in (2, 6, 11, 15):
                g.rect(x, 5, x, 6, "H")
    return build


# ----------------------------------------------------------------------------------------------------
# Landmarks and dressing

def tower_base(g: Grid) -> None:
    g.fill("L")
    for y in range(0, 16, 5):
        g.hl(y, 0, 15, "M")
        offset = 0 if (y // 5) % 2 == 0 else 4
        for x in range(offset, 16, 8):
            g.vl(x, y, y + 4, "M")
    g.rect(5, 9, 10, 15, "k")
    g.rect(6, 7, 9, 8, "k")
    g.rect(7, 6, 8, 6, "k")
    g.vl(4, 9, 15, "M")
    g.vl(11, 9, 15, "M")


def tower_mid(g: Grid) -> None:
    g.fill("L")
    for x in (2, 7, 12):
        g.vl(x, 0, 15, "M")
        g.vl(x + 1, 0, 15, "W")
    for x in (4, 9):
        g.rect(x, 3, x + 1, 8, "k")
    g.hl(0, 0, 15, "M")
    g.hl(15, 0, 15, "M")


def tower_clock(g: Grid) -> None:
    g.fill("M")
    g.disc(7.5, 7.5, 7.4, "L")
    g.disc(7.5, 7.5, 6.2, "W")
    for x, y in [(7, 2), (8, 2), (2, 7), (2, 8), (13, 7), (13, 8), (7, 13), (8, 13)]:
        g.rect(x, y, x + 1, y + 1, "k")
    g.rect(7, 4, 8, 8, "k")
    g.rect(8, 7, 11, 8, "k")


def tower_roof(g: Grid) -> None:
    g.fill("k")
    for y in range(0, 16):
        half = min(7, 1 + y // 2)
        if y < 6:
            g.rect(7 - half, y, 8 + half, y, "L")
        else:
            g.rect(1, y, 14, y, "M" if y % 4 else "L")
    g.hl(6, 0, 15, "M")
    g.hl(0, 7, 8, "W")


def cath_wall(g: Grid) -> None:
    g.fill("L")
    for y in range(0, 16, 4):
        g.hl(y, 0, 15, "M")
        offset = 0 if (y // 4) % 2 == 0 else 5
        for x in range(offset, 16, 10):
            g.vl(x, y, y + 3, "M")
    for x, y in [(3, 2), (11, 6), (6, 10), (14, 14)]:
        g.px(x, y, "W")


def cath_window(g: Grid) -> None:
    g.fill("L")
    g.rect(4, 6, 11, 14, "k")
    g.rect(5, 5, 10, 5, "k")
    g.rect(6, 3, 9, 4, "k")
    g.vl(7, 6, 14, "M")
    g.vl(8, 6, 14, "M")
    g.hl(10, 4, 6, "M")
    g.hl(10, 9, 11, "M")
    g.hl(1, 3, 12, "W")


def cath_buttress(g: Grid) -> None:
    g.fill("L")
    for x in (2, 10):
        g.rect(x, 0, x + 3, 15, "M")
        g.rect(x + 1, 0, x + 2, 15, "W")
    g.hl(6, 0, 15, "M")


def cath_door(g: Grid) -> None:
    g.fill("L")
    g.rect(3, 7, 12, 15, "k")
    g.rect(4, 5, 11, 6, "k")
    g.rect(6, 3, 9, 4, "k")
    g.vl(7, 7, 15, "M")
    g.vl(8, 7, 15, "M")
    g.rect(6, 9, 9, 10, "M")


def wall_top(g: Grid) -> None:
    g.rect(0, 0, 15, 3, "C")
    g.hl(4, 0, 15, "A")
    g.hl(5, 0, 15, "k")
    for row, y in enumerate(range(6, 16, 5)):
        offset = 0 if row % 2 == 0 else 4
        for x in range(-8, 24, 8):
            g.rect(x + offset, y, x + offset + 6, y + 3, "B")


def gutter(g: Grid) -> None:
    """A drainage channel in the street: a black run with two M cross bars. It used to spend L on the lips."""
    g.fill("M")
    g.rect(4, 0, 11, 15, "k")
    for y in (3, 11):
        g.hl(y, 4, 11, "M")


def sign_street(g: Grid) -> None:
    g.fill("M")
    g.rect(1, 4, 14, 11, "k")
    g.rect(2, 5, 13, 10, "W")
    for x in (3, 7, 11):
        g.rect(x, 6, x + 1, 6, "M")
    g.rect(3, 9, 9, 9, "M")
    g.rect(1, 12, 2, 15, "L")
    g.rect(13, 12, 14, 15, "L")


def blank(g: Grid) -> None:
    g.fill("k")


def tree_canopy_c(g: Grid) -> None:
    tree_canopy(0)(g)
    g.rect(0, 14, 15, 15, "G")


TILES = [
    # ground and terrain
    ("road_a", "bg0_stone", road(0)),
    ("road_b", "bg0_stone", road(1)),
    ("road_line", "bg0_stone", road_line_v),
    ("road_line_h", "bg0_stone", road_line_h),
    ("crosswalk", "bg0_stone", crosswalk),
    ("kerb_w", "bg0_stone", kerb(True)),
    ("kerb_e", "bg0_stone", kerb(False)),
    ("pavement_a", "bg0_stone", pavement(0)),
    ("pavement_b", "bg0_stone", pavement(1)),
    ("pavement_grate", "bg0_stone", pavement_grate),
    ("cobble_a", "bg0_stone", cobbles(0)),
    ("cobble_b", "bg0_stone", cobbles(1)),
    ("cobble_c", "bg0_stone", cobbles(2)),
    ("grass_a", "bg2_green", grass(0)),
    ("grass_b", "bg2_green", grass(1)),
    ("quay_stone", "bg0_stone", quay(0)),
    # water and buildings
    ("water_a", "bg3_water", water(0)),
    ("water_b", "bg3_water", water(1)),
    ("water_deep", "bg3_water", water(2)),
    ("shore_stone", "bg0_stone", shore_stone),
    ("quay_flag", "bg0_stone", quay(1)),
    ("brick_a", "bg1_brick", brick(0)),
    ("brick_b", "bg1_brick", brick(1)),
    ("brick_c", "bg1_brick", brick(2)),
    ("brick_cornice", "bg1_brick", brick_cornice),
    ("shop_front", "bg1_brick", shop_front),
    ("shop_door", "bg1_brick", shop_door),
    ("window_lit", "bg1_brick", window(True)),
    ("window_dark", "bg1_brick", window(False)),
    ("awning", "bg4_red", awning(True)),
    ("door_a", "bg1_brick", door(0)),
    # street furniture and planting
    ("door_b", "bg1_brick", door(1)),
    ("roof_slate", "bg0_stone", roof_slate),
    ("phone_box_top", "bg4_red", phone_box_top),
    ("phone_box_body", "bg4_red", phone_box_body),
    ("post_box", "bg4_red", post_box),
    ("lamp_head", "bg0_stone", lamp_head),
    ("lamp_post", "bg0_stone", lamp_post),
    ("bollard", "bg0_stone", bollard),
    ("bench", "bg0_stone", bench),
    ("railing_a", "bg0_stone", railing(False)),
    ("railing_b", "bg0_stone", railing(True)),
    ("traffic_top", "bg4_red", traffic_top),
    ("traffic_body", "bg4_red", traffic_body),
    ("tree_canopy_a", "bg2_green", tree_canopy(0)),
    ("tree_canopy_b", "bg2_green", tree_canopy(1)),
    ("tree_trunk", "bg5_plant", tree_trunk),
    # landmarks and dressing
    ("hedge_a", "bg2_green", hedge(0)),
    ("hedge_b", "bg2_green", hedge(1)),
    ("tower_base", "bg0_stone", tower_base),
    ("tower_mid", "bg0_stone", tower_mid),
    ("tower_clock", "bg0_stone", tower_clock),
    ("tower_roof", "bg0_stone", tower_roof),
    ("cath_wall", "bg0_stone", cath_wall),
    ("cath_window", "bg0_stone", cath_window),
    ("cath_buttress", "bg0_stone", cath_buttress),
    ("cath_door", "bg0_stone", cath_door),
    ("wall_top", "bg1_brick", wall_top),
    ("gutter", "bg0_stone", gutter),
    ("sign_street", "bg0_stone", sign_street),
    ("blank", "bg0_stone", blank),
    ("tree_canopy_c", "bg2_green", tree_canopy_c),
    ("grass_c", "bg2_green", grass(2)),
    ("awning_green", "bg2_green", awning(False)),
]

# Tiles a player cannot walk through.
SOLID = {
    "phone_box_top", "phone_box_body", "post_box", "lamp_head", "lamp_post", "bollard", "bench",
    "railing_a", "railing_b", "traffic_top", "traffic_body", "tree_canopy_a", "tree_canopy_b",
    "tree_canopy_c", "tree_trunk", "hedge_a", "hedge_b", "tower_base", "tower_mid", "tower_clock",
    "tower_roof", "cath_wall", "cath_window", "cath_buttress", "cath_door", "wall_top", "sign_street",
    "brick_a", "brick_b", "brick_c", "brick_cornice", "shop_front", "shop_door", "window_lit",
    "window_dark", "awning", "awning_green", "door_a", "door_b", "roof_slate", "water_a", "water_b",
    "water_deep", "shore_stone",
}
ANIMATIONS = {"water": ["water_a", "water_b"]}
FEATURES = {
    # The card that asked for this tileset named the marking in white; card t_454c1876 moved the marking to
    # the shared black because a walkable tile cannot carry a light entry (see the walkable band note above),
    # so the key names what the tiles now draw. tools/check_ts_exterior.py requires this exact string.
    "road with centre line": ["road_a", "road_b", "road_line", "road_line_h"],
    "kerb": ["kerb_w", "kerb_e"],
    "pavement": ["pavement_a", "pavement_b", "pavement_grate"],
    "cobbles": ["cobble_a", "cobble_b", "cobble_c"],
    "brick building walls (3 variants)": ["brick_a", "brick_b", "brick_c"],
    "shop front with awning": ["shop_front", "shop_door", "awning", "awning_green"],
    "doors": ["door_a", "door_b"],
    "windows with light": ["window_lit", "window_dark"],
    "red phone box": ["phone_box_top", "phone_box_body"],
    "post box": ["post_box"],
    "hedge": ["hedge_a", "hedge_b"],
    "tree": ["tree_trunk", "tree_canopy_a", "tree_canopy_b", "tree_canopy_c"],
    "lamp post": ["lamp_post", "lamp_head"],
    "bollard": ["bollard"],
    "quay stone": ["quay_stone", "quay_flag", "shore_stone"],
    "water (2 frames)": ["water_a", "water_b"],
    "railing": ["railing_a", "railing_b"],
    "bench": ["bench"],
    "traffic light": ["traffic_top", "traffic_body"],
    "crosswalk": ["crosswalk"],
    "Big Ben tower pieces (4 tiles tall)": ["tower_base", "tower_mid", "tower_clock", "tower_roof"],
    "cathedral wall pieces": ["cath_wall", "cath_window", "cath_buttress", "cath_door"],
}


def repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def load_palette(root: str) -> dict:
    with open(os.path.join(root, "data", "nes_palette.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    return {entry["index"]: entry for entry in data["entries"]}


def build_sheet(root: str):
    entries = load_palette(root)
    sheet = Image.new("RGBA", (SHEET_W, SHEET_H), (0, 0, 0, 0))
    pixels = sheet.load()
    records = []
    for index, (name, palette_name, builder) in enumerate(TILES):
        grid = Grid()
        builder(grid)
        keys = PALETTES[palette_name]
        cx = (index % COLUMNS) * TILE
        cy = (index // COLUMNS) * TILE
        used = set()
        for y, row in enumerate(grid.lines()):
            for x, ch in enumerate(row):
                if ch == "k":
                    entry = BACKDROP_ENTRY
                else:
                    if ch not in keys:
                        raise KeyError("%s uses %r, palette %s has no such key" % (name, ch, palette_name))
                    entry = keys[ch]
                colour = entries[entry]["hex"]
                rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
                pixels[cx + x, cy + y] = rgb + (255,)
                used.add(entry)
        records.append({
            "index": index,
            "name": name,
            "palette": palette_name,
            "entries": sorted(used),
            "hex": sorted({entries[e]["hex"] for e in used}),
            "solid": name in SOLID,
        })
    return sheet, records


def build_metadata(records: list, entries: dict) -> dict:
    palettes = {
        name: [{"key": key, "entry": entry, "hex": entries[entry]["hex"]}
               for key, entry in sorted(keys.items(), key=lambda kv: kv[1])]
        for name, keys in PALETTES.items()
    }
    return {
        "format": 1,
        "kind": "tileset",
        "name": "ts_exterior",
        "image": "ts_exterior.png",
        "columns": COLUMNS,
        "rows": ROWS,
        "frames": len(TILES),
        "frame_w": TILE,
        "frame_h": TILE,
        "imagewidth": SHEET_W,
        "imageheight": SHEET_H,
        "tilecount": len(TILES),
        "tile_size": TILE,
        "margin": 0,
        "spacing": 0,
        "backdrop": {"entry": BACKDROP_ENTRY, "hex": BACKDROP_HEX},
        "rule": "NES: 5 background palettes of 3 entries, a scene spends at most 4 of them, a 16x16 tile "
                "carries at most 3 colours besides the shared backdrop $0F",
        "palettes": palettes,
        "animations": ANIMATIONS,
        "features": FEATURES,
        "tiles": records,
        "provenance": "original art drawn by tools/art/make_ts_exterior.py; no reference asset copied "
                      "(PLAN-V2-2026-10-21.md section 0)",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = args.root or repo_root()
    entries = load_palette(root)
    sheet, records = build_sheet(root)
    out_dir = os.path.join(root, "game", "sprites_src", "env")
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, "ts_exterior.png")
    sheet.save(out_png)
    meta = build_metadata(records, entries)
    with open(os.path.join(out_dir, "ts_exterior.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")

    tiled = {k: v for k, v in meta.items() if k not in ("tiles", "palettes", "features")}
    tiled["palette"] = [{"entry": entry, "hex": entries[entry]["hex"], "key": key, "palette": name}
                        for name, keys in PALETTES.items() for key, entry in keys.items()]
    with open(os.path.join(out_dir, "ts_exterior_tiled.json"), "w", encoding="utf-8") as handle:
        json.dump(tiled, handle, indent=2)
        handle.write("\n")

    os.makedirs(os.path.join(root, "output"), exist_ok=True)
    sheet.resize((SHEET_W * 3, SHEET_H * 3), Image.NEAREST).save(
        os.path.join(root, "output", "ts_exterior_preview_3x.png"))
    print("wrote %s (%dx%d, %d tiles)" % (out_png, SHEET_W, SHEET_H, len(TILES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
