#!/usr/bin/env python3
"""Generate the Map 2 tileset: the small Royal Navy ship interior, plus a harbour edge strip.

Contract: the ENV-TILES card (t_4f58c88d), PLAN-V2-2026-10-21 section 0 (reference rule: study by looking,
never copy or trace; our output is original) and knowledge/CHARACTER-BIBLE.md REVISION 2 (Percy is a 23 year old
Royal Navy officer, so the ship interior is a real small warship: steel decks, riveted bulkheads, hatches,
a wardroom in dark wood, an officer cabin with a bunk).

Clean room: every shape below is drawn from numbers in this file with plain geometry (rectangles, lines, circles
by squared distance, diagonal hatching). No sprite, tile, texture, palette swatch or layout from any published
game is read, traced, sampled or reproduced. The ship layout is invented here.

Colour rule, and why this file is short on colours: the game must run on a stock NES, so the art obeys the
Ricoh 2C02. Each 8x8 tile may carry 3 colours plus transparent, and a background 16x16 attribute area picks 3
colours plus the one shared backdrop. The whole scene therefore uses 10 colours: black as the backdrop, the steel
pair and white paint, the sea's three tones, and rust with brass. The four background rows of
data/palettes/scene_ship.json group them as steel-and-white, steel-and-brass, rust-and-brass and sea, and every
16x16 tile here is drawn inside one of those groups, so the scene palette pass repaints nothing it cannot carry.
Every 16x16 tile carries at most 3 non-backdrop colours, and tools/check_env_tiles.py proves it plus runs
tools/nes_check.py over the sheet.

Palette entries are the 2C02 system numbers from data/nes_palette.json (built and cited by
tools/art/nes_palette_build.py), so the sheet passes tools/nes_check.py with its default palette.

Outputs, all deterministic (no clock, no unseeded randomness, LF endings, sorted JSON keys):
    game/sprites_src/env/ts_ship.png             256x48, 16 columns of 16x16 tiles, 48 tiles
    game/sprites_src/env/ts_ship.json            the animation contract beside the PNG (name, frame_w,
                                                 frame_h, frames, fps) like the title art
    game/sprites_src/env/ts_ship_tiled.json      the same tiles as a Tiled tileset: names, solid flags,
                                                 per tile colours, water and porthole animation
    data/maps/ship_sample_tiled.json             a Tiled map, 20x15: corridor, two rooms, a ladder, a hatch
                                                 out to Percy's wardroom, and a collision layer
    output/env_ship_preview.png                  3x: the tile sheet with index labels, the map, and the
                                                 harbour strip in both water frames

One path rule, because two cards wanted the same file on 2026-10-21: the map is written to
data/maps/ship_sample.json when that name is free or already holds this generator's own Tiled map (a file whose
"kind" is "map"), and to data/maps/ship_sample_tiled.json when another lane's map holds the plain name. A foreign
map is never overwritten, and the run prints which path it used. tools/check_env_tiles.py applies the same rule.

Usage:
    python tools/art/make_env_ship.py
    python tools/art/make_env_ship.py --root <repo>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

TILE = 16
COLUMNS = 16
TILE_COUNT = 48
SCALE = 3

# -----------------------------------------------------------------------------------------------------------------
# The 10 colours of this scene. Key, 2C02 entry, hex, what it is for.
# Nothing else may appear in the sheet: check_env_tiles.py compares every opaque pixel against this table.

PALETTE = [
    ("k", 0x0F, "#000000", "backdrop: hull shadow, seams, hatch void"),
    ("m", 0x00, "#7c7c7c", "steel mid: deck plates, lower bulkhead, stone"),
    ("l", 0x10, "#bcbcbc", "steel light: upper bulkhead, rivets, fittings, porthole glass"),
    ("w", 0x30, "#fcfcfc", "white paint: corridor lines, rim light, porthole glare"),
    ("a", 0x02, "#0000bc", "sea deep: troughs under a crest, deep water"),
    ("b", 0x12, "#0058f8", "sea mid: the body of the water"),
    ("c", 0x21, "#3cbcfc", "sea crest: wave light and foam (the water family's light tone)"),
    ("r", 0x07, "#881400", "rust dark, wardroom wood dark"),
    ("o", 0x17, "#e45c10", "rust, wardroom wood grain"),
    ("y", 0x28, "#f8b800", "brass, hazard yellow"),
]

BACKDROP = "k"
KEY_TO_RGBA = {}
for _key, _entry, _hex, _use in PALETTE:
    _v = _hex.lstrip("#")
    KEY_TO_RGBA[_key] = (int(_v[0:2], 16), int(_v[2:4], 16), int(_v[4:6], 16), 255)


# -----------------------------------------------------------------------------------------------------------------
# A tile is a 16x16 grid of palette keys. Primitives only: no bitmap blobs, so the source stays reviewable.


class Cell:
    """One 16x16 tile as palette keys, with the drawing primitives the tiles are composed from."""

    def __init__(self) -> None:
        self.px = [[BACKDROP] * TILE for _ in range(TILE)]

    def set(self, x: int, y: int, key: str) -> None:
        if 0 <= x < TILE and 0 <= y < TILE:
            self.px[y][x] = key

    def get(self, x: int, y: int) -> str:
        return self.px[y][x]

    def fill(self, key: str) -> None:
        for y in range(TILE):
            for x in range(TILE):
                self.px[y][x] = key

    def rect(self, x0: int, y0: int, x1: int, y1: int, key: str) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.set(x, y, key)

    def frame(self, x0: int, y0: int, x1: int, y1: int, key: str) -> None:
        self.hline(y0, x0, x1, key)
        self.hline(y1, x0, x1, key)
        self.vline(x0, y0, y1, key)
        self.vline(x1, y0, y1, key)

    def hline(self, y: int, x0: int, x1: int, key: str) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.set(x, y, key)

    def vline(self, x: int, y0: int, y1: int, key: str) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.set(x, y, key)

    def annulus(self, cx: float, cy: float, r_out: float, r_in: float, key: str) -> None:
        """A ring by squared distance, so the curve is the same every run on every platform."""
        for y in range(TILE):
            for x in range(TILE):
                dx = x - cx
                dy = y - cy
                d2 = dx * dx + dy * dy
                if r_in * r_in <= d2 <= r_out * r_out:
                    self.px[y][x] = key

    def disc(self, cx: float, cy: float, radius: float, key: str) -> None:
        for y in range(TILE):
            for x in range(TILE):
                dx = x - cx
                dy = y - cy
                if dx * dx + dy * dy <= radius * radius:
                    self.px[y][x] = key

    def hazard(self, period: int, width: int, key: str) -> None:
        """Diagonal stripes, the way painted hazard tape reads at 16 px."""
        for y in range(TILE):
            for x in range(TILE):
                if (x + y) % period < width:
                    self.px[y][x] = key

    def checker(self, step: int, a: str, b: str) -> None:
        for y in range(TILE):
            for x in range(TILE):
                self.px[y][x] = a if ((x // step) + (y // step)) % 2 == 0 else b


# -----------------------------------------------------------------------------------------------------------------
# The tiles. Each function paints one 16x16 tile from the palette keys above.
# Colours per tile are chosen to stay at 3 non-backdrop keys, and mostly at 2, so a NES attribute area can hold it.

C = 7.5  # the centre of a 16 px tile in pixel coordinates


def deck_a(c: Cell) -> None:
    """Steel deck plate, seam on the top and left edges, one pixel bevel inside."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.hline(1, 1, 14, "l")
    c.vline(1, 1, 14, "l")
    c.hline(6, 5, 7, "k")
    c.hline(11, 10, 11, "k")


def deck_b(c: Cell) -> None:
    """Steel deck plate, second variant: seam bottom and right, raised non slip treads."""
    c.fill("m")
    c.hline(15, 0, 15, "k")
    c.vline(15, 0, 15, "k")
    c.hline(14, 1, 14, "l")
    c.vline(14, 1, 14, "l")
    for y in (6, 10):
        for x0 in (2, 7, 12):
            c.hline(y, x0, x0 + 1, "l")


def deck_plain(c: Cell) -> None:
    """Flat steel, for long runs where a seam grid would read as noise."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.set(4, 5, "l")
    c.set(11, 9, "l")


def deck_grate(c: Cell) -> None:
    """Walkable grating: dark gaps between raised bars."""
    c.fill("k")
    for x in (2, 6, 10, 14):
        c.rect(x, 1, x + 1, 14, "m")
        c.vline(x, 1, 14, "l")
    c.hline(0, 0, 15, "l")
    c.hline(15, 0, 15, "l")


def deck_rivets(c: Cell) -> None:
    """Deck plate with rivet heads, for the plates that take the load."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    for x, y in ((3, 3), (11, 3), (3, 11), (11, 11)):
        c.rect(x, y, x + 1, y + 1, "l")
        c.hline(y + 2, x, x + 1, "k")


def deck_line_h(c: Cell) -> None:
    """Deck with the grey painted corridor line running left to right."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.rect(1, 6, 15, 8, "w")
    c.set(6, 7, "m")


def deck_line_v(c: Cell) -> None:
    """Deck with the painted line running up and down."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.rect(6, 1, 8, 15, "w")
    c.set(7, 6, "m")


def deck_line_corner(c: Cell) -> None:
    """Where the painted line turns, so a corridor corner is not two lines crossing."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.vline(0, 0, 15, "k")
    c.rect(10, 10, 15, 12, "w")
    c.rect(10, 10, 12, 15, "w")
    c.set(12, 11, "m")


def bulkhead(c: Cell) -> None:
    """Riveted bulkhead: light upper panel, mid lower panel, rivets on both."""
    c.fill("l")
    c.rect(0, 9, 15, 15, "m")
    c.hline(0, 0, 15, "k")
    c.hline(9, 0, 15, "k")
    for x in (3, 12):
        c.rect(x, 4, x + 1, 5, "k")
        c.rect(x, 12, x + 1, 13, "l")


def bulkhead_plain(c: Cell) -> None:
    """Bulkhead without rivets, for the long outer hull."""
    c.fill("l")
    c.rect(0, 9, 15, 15, "m")
    c.hline(0, 0, 15, "k")
    c.hline(9, 0, 15, "k")


def bulkhead_vent(c: Cell) -> None:
    """Bulkhead with a vent grille: the engine room breathes through these."""
    c.fill("l")
    c.rect(0, 7, 15, 15, "m")
    c.hline(0, 0, 15, "k")
    c.hline(7, 0, 15, "k")
    c.frame(3, 8, 12, 14, "k")
    for y in (9, 11, 13):
        c.hline(y, 4, 11, "k")


def bulkhead_light(c: Cell) -> None:
    """Bulkhead with a brass bulkhead lamp on the lower panel."""
    c.fill("l")
    c.rect(0, 7, 15, 15, "m")
    c.hline(0, 0, 15, "k")
    c.hline(7, 0, 15, "k")
    c.frame(4, 9, 11, 14, "k")
    c.rect(5, 10, 10, 13, "y")
    c.rect(6, 11, 9, 12, "l")


def hatch_closed(c: Cell) -> None:
    """A shut hatch: steel frame, door leaf, brass dogs around the wheel."""
    c.fill("k")
    c.rect(1, 1, 14, 14, "l")
    c.rect(2, 2, 13, 13, "m")
    c.frame(2, 2, 13, 13, "k")
    c.annulus(C, C, 4.2, 2.6, "y")
    c.hline(8, 4, 11, "y")
    c.vline(8, 4, 11, "y")
    c.rect(1, 4, 2, 5, "m")
    c.rect(1, 10, 2, 11, "m")


def hatch_open(c: Cell) -> None:
    """The same hatch open: dark void, jambs, and a sill you can walk over."""
    c.fill("k")
    c.rect(1, 1, 14, 14, "l")
    c.rect(2, 2, 13, 14, "k")
    c.vline(2, 2, 14, "m")
    c.vline(13, 2, 14, "m")
    c.rect(3, 13, 12, 14, "m")
    c.hline(13, 3, 12, "l")


def deck_sill(c: Cell) -> None:
    """A threshold strip: walkable, marks the line of a doorway in the floor."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(15, 0, 15, "k")
    c.rect(0, 6, 15, 9, "l")
    c.hline(6, 0, 15, "w")


def ladder(c: Cell) -> None:
    """A vertical ladder in a dark trunk: two rails, rungs every four pixels."""
    c.fill("k")
    c.rect(3, 0, 4, 15, "w")
    c.rect(11, 0, 12, 15, "w")
    for y in (2, 6, 10, 14):
        c.hline(y, 5, 10, "l")
        c.set(4, y, "k")
        c.set(11, y, "k")


def stairs_up(c: Cell) -> None:
    """Stairs climbing away from the viewer: light nosing on every tread."""
    c.fill("k")
    for i in range(4):
        y0 = 12 - i * 3
        c.rect(1, y0, 14, y0 + 2, "m")
        c.hline(y0, 1, 14, "l")


def stairs_down(c: Cell) -> None:
    """Stairs dropping away: the nosing is on the near edge instead."""
    c.fill("k")
    for i in range(4):
        y0 = 1 + i * 3
        c.rect(1, y0, 14, y0 + 2, "m")
        c.hline(y0 + 2, 1, 14, "l")


def pipes(c: Cell) -> None:
    """Two horizontal pipe runs with brass clamps, seen against shadow."""
    c.fill("k")
    c.rect(0, 2, 15, 6, "m")
    c.hline(2, 0, 15, "l")
    c.rect(0, 9, 15, 12, "l")
    c.hline(12, 0, 15, "m")
    c.rect(6, 1, 7, 6, "y")
    c.rect(6, 9, 7, 13, "y")


def pipe_vert(c: Cell) -> None:
    """The same pipe run going up a wall."""
    c.fill("k")
    c.rect(5, 0, 10, 15, "l")
    c.vline(10, 0, 15, "m")
    c.rect(4, 6, 11, 7, "y")


def cable_run(c: Cell) -> None:
    """Cable runs: three strapped bundles with a brass clamp."""
    c.fill("k")
    for base, key in ((3, "l"), (7, "m"), (11, "l")):
        for x in range(0, 16):
            y = base if x < 8 else base + 1
            c.set(x, y, key)
            c.set(x, y + 1, key)
    c.rect(1, 2, 2, 13, "y")


def crate(c: Cell) -> None:
    """A wooden crate: rust brown planks, brass corners."""
    c.fill("o")
    c.frame(0, 0, 15, 15, "r")
    c.hline(5, 0, 15, "r")
    c.hline(10, 0, 15, "r")
    for x, y in ((0, 0), (13, 0), (0, 13), (13, 13)):
        c.rect(x, y, x + 2, y + 2, "y")


def crate_stack(c: Cell) -> None:
    """Two crates stacked so a hold does not read as a grid."""
    c.fill("k")
    c.rect(1, 2, 9, 10, "o")
    c.frame(1, 2, 9, 10, "r")
    c.hline(6, 1, 9, "r")
    c.rect(6, 6, 14, 14, "o")
    c.frame(6, 6, 14, 14, "r")
    c.hline(10, 6, 14, "r")
    c.rect(1, 2, 2, 3, "y")
    c.rect(13, 6, 14, 7, "y")
    c.rect(6, 13, 7, 14, "y")


def barrel(c: Cell) -> None:
    """A staved barrel with two brass bands."""
    c.fill("k")
    c.rect(3, 2, 12, 14, "o")
    c.vline(3, 2, 14, "r")
    c.vline(12, 2, 14, "r")
    c.hline(2, 3, 12, "r")
    c.hline(14, 3, 12, "r")
    c.hline(5, 3, 12, "y")
    c.hline(11, 3, 12, "y")


def lifebuoy(c: Cell) -> None:
    """A lifebuoy on its bracket: white ring, four orange bands, dark centre."""
    c.fill("k")
    c.annulus(C, C, 6.4, 3.6, "w")
    for dx, dy in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
        c.rect(int(C + dx), int(C + dy), int(C + dx) + 1, int(C + dy) + 1, "o")
    c.rect(0, 7, 0, 8, "l")
    c.rect(15, 7, 15, 8, "l")


def warning(c: Cell) -> None:
    """Painted hazard stripes on the deck."""
    c.fill("k")
    c.hazard(8, 4, "y")


def locker(c: Cell) -> None:
    """A steel locker, two doors, brass handle, vent slots."""
    c.fill("k")
    c.rect(1, 1, 14, 14, "l")
    c.vline(8, 2, 13, "m")
    c.rect(3, 3, 6, 4, "k")
    c.rect(9, 3, 12, 4, "k")
    c.rect(6, 7, 7, 9, "y")
    c.rect(9, 7, 10, 9, "y")


def porthole_a(c: Cell) -> None:
    """A porthole in a bulkhead, frame one: pale glass with a white glare, one scratch across it."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(15, 0, 15, "k")
    c.annulus(C, C, 7.4, 5.8, "l")
    # The glass is steel light, not sea blue: a three tone sea and a steel frame are four colours in one
    # attribute area, and the frame is the part that has to stay metal. Pale glass with a white glare reads as
    # daylight through a window and fits the steel-and-white row (ruling section 21.7).
    c.disc(C, C, 5.2, "l")
    c.hline(6, 5, 10, "w")
    c.set(4, 9, "w")
    c.set(11, 10, "w")


def porthole_b(c: Cell) -> None:
    """Glass frame two: the glare has moved, so the portholes live."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(15, 0, 15, "k")
    c.annulus(C, C, 7.4, 5.8, "l")
    c.disc(C, C, 5.2, "l")
    c.hline(9, 5, 10, "w")
    c.set(7, 5, "w")
    c.set(3, 10, "w")


def sign_wardroom(c: Cell) -> None:
    """A painted plate on the bulkhead: three label lines and an arrow, wardroom."""
    c.fill("m")
    c.rect(1, 2, 14, 13, "l")
    c.frame(1, 2, 14, 13, "k")
    for y in (5, 8):
        c.hline(y, 3, 9, "k")
    c.rect(11, 8, 12, 10, "w")
    c.hline(10, 11, 12, "w")


def sign_machinery(c: Cell) -> None:
    """A sign for the machinery space: a cog cross in white paint."""
    c.fill("m")
    c.rect(1, 2, 14, 13, "l")
    c.frame(1, 2, 14, 13, "k")
    c.rect(7, 4, 8, 11, "w")
    c.rect(4, 7, 11, 8, "w")
    c.set(5, 5, "w")
    c.set(10, 5, "w")
    c.set(5, 10, "w")
    c.set(10, 10, "w")


def sign_bridge(c: Cell) -> None:
    """A sign for the bridge: a white chevron pointing forward."""
    c.fill("m")
    c.rect(1, 2, 14, 13, "l")
    c.frame(1, 2, 14, 13, "k")
    for i in range(5):
        c.hline(4 + i, 7 - i, 8 + i, "w")
    c.hline(10, 7, 8, "w")


def wood_floor_a(c: Cell) -> None:
    """Wardroom deck: dark wood planks with a lighter grain line."""
    c.fill("r")
    c.hline(5, 0, 15, "o")
    c.hline(11, 0, 15, "o")
    c.vline(4, 0, 4, "k")
    c.vline(12, 6, 10, "k")


def wood_floor_b(c: Cell) -> None:
    """The same planks offset, so a floor does not tile as a grid."""
    c.fill("r")
    c.hline(3, 0, 15, "o")
    c.hline(9, 0, 15, "o")
    c.hline(14, 0, 15, "o")
    c.vline(8, 0, 2, "k")
    c.vline(2, 10, 13, "k")


def table(c: Cell) -> None:
    """The wardroom table: wood top, brass edge, shadow beneath."""
    c.fill("r")
    c.rect(1, 2, 14, 11, "o")
    c.frame(1, 2, 14, 11, "r")
    c.hline(2, 2, 13, "y")
    c.rect(1, 12, 14, 14, "k")
    c.rect(2, 5, 13, 8, "r")


def bunk(c: Cell) -> None:
    """An officer's bunk: steel frame, mattress, folded blanket at the head."""
    c.fill("r")
    c.rect(1, 1, 14, 14, "k")
    c.rect(2, 2, 13, 13, "l")
    c.rect(2, 2, 13, 5, "m")
    c.hline(6, 2, 13, "k")
    c.rect(2, 2, 3, 13, "m")


def quay_stone_a(c: Cell) -> None:
    """Quay stone: two courses of blocks with dark mortar."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(8, 0, 15, "k")
    c.vline(10, 0, 7, "k")
    c.vline(5, 8, 15, "k")
    c.hline(1, 1, 9, "l")
    c.hline(9, 6, 15, "l")
    c.vline(0, 0, 7, "k")


def quay_stone_b(c: Cell) -> None:
    """The same stonework offset by half a block."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(8, 0, 15, "k")
    c.vline(4, 0, 7, "k")
    c.vline(12, 8, 15, "k")
    c.hline(1, 5, 15, "l")
    c.hline(9, 1, 11, "l")
    c.vline(15, 0, 15, "k")


def quay_dark(c: Cell) -> None:
    """Quay stone in shadow, for the water line."""
    c.fill("m")
    c.hline(0, 0, 15, "k")
    c.hline(5, 0, 15, "k")
    c.hline(11, 0, 15, "k")
    c.vline(5, 0, 4, "k")
    c.vline(11, 6, 10, "k")
    c.vline(3, 12, 15, "k")


def quay_cap(c: Cell) -> None:
    """The walkable top of the quay: light coping over a dark face."""
    c.fill("l")
    c.hline(0, 0, 15, "k")
    c.rect(0, 11, 15, 15, "m")
    c.hline(11, 0, 15, "k")


def bollard(c: Cell) -> None:
    """A brass bollard with a rusted base plate."""
    c.fill("k")
    c.rect(4, 12, 11, 15, "r")
    c.rect(5, 3, 10, 12, "y")
    c.rect(3, 1, 12, 3, "y")
    c.hline(3, 4, 11, "r")
    c.vline(10, 4, 12, "r")


def rail_post(c: Cell) -> None:
    """A stanchion for the harbour railing."""
    c.fill("k")
    c.rect(6, 0, 9, 15, "l")
    c.vline(9, 0, 15, "m")
    c.rect(4, 13, 11, 15, "m")


def rail_bar(c: Cell) -> None:
    """The railing bar itself, running left to right."""
    c.fill("k")
    c.rect(0, 5, 15, 8, "l")
    c.hline(8, 0, 15, "m")


# -----------------------------------------------------------------------------------------------------------------
# The sea. Five tiles on three tones: sea mid $12 is the body, sea crest $21 is the light on a wave and the foam,
# sea deep $02 is the trough under a crest and the whole of the deep water. Nothing here is white: white is the
# ship's paint, and a row that carries white cannot also carry the crest (ruling section 21.7).


def crest(c: Cell, y: int, x0: int, length: int) -> None:
    """One wave light: a dash of crest on row y with its trough one pixel right and one below.

    Both are wrapped at the tile edge so the water tiles horizontally without a seam, and the trough is a pixel
    shorter than the light so a crest reads as a lit edge over a shadow instead of a stripe.
    """
    for i in range(length):
        c.set((x0 + i) % TILE, y % TILE, "c")
    for i in range(max(1, length - 1)):
        c.set((x0 + 1 + i) % TILE, (y + 1) % TILE, "a")


def swell(c: Cell, drift: int, rising: bool = False) -> None:
    """The open sea: four crests on an uneven pitch, so the tile repeats without reading as a grid."""
    c.fill("b")
    for index, (y, x0, length) in enumerate(((2, 2, 4), (7, 9, 3), (12, 5, 5), (15, 13, 3))):
        if rising and index == 2:
            length += 1          # the big crest grows a pixel, so the pair reads as a swell and not a slide
        crest(c, y, x0 + drift, length)


def water_a(c: Cell) -> None:
    """Open sea, frame one: the swell at rest."""
    swell(c, 0)


def water_b(c: Cell) -> None:
    """Open sea, frame two: every crest has drifted three pixels and one has grown, at 2 fps."""
    swell(c, 3, rising=True)


def water_edge(c: Cell) -> None:
    """The water line against the quay: ragged foam at the top, its trough under it, then sea."""
    c.fill("b")
    for y, x0, length in ((0, 0, 5), (0, 6, 3), (0, 10, 5), (1, 1, 3), (1, 7, 2), (1, 11, 3)):
        for i in range(length):
            c.set((x0 + i) % TILE, y, "c")
    for x0, length in ((2, 4), (8, 3), (12, 3)):
        for i in range(length):
            c.set((x0 + i) % TILE, 2, "a")
    for y, x0, length in ((6, 11, 3), (11, 2, 4)):
        crest(c, y, x0, length)


def water_deep(c: Cell) -> None:
    """Deep water: navy body, a low swell catching the light, and one glint on each crest."""
    c.fill("a")
    for y, x0, length in ((3, 6, 4), (9, 12, 3), (13, 1, 3)):
        for i in range(length):
            c.set((x0 + i) % TILE, y, "b")
    c.set(6, 3, "c")
    c.set(12, 9, "c")


def water_foam(c: Cell) -> None:
    """Breaking water: a mass of foam on the water, with holes and a trough under its near edge.

    A foam tile that carries the same two dashes as the calm sea reads as busier water, not as breaking water: at
    16 px the thing that says foam is how MUCH of the tile is the light tone. So this one is mostly crest with the
    body showing through it, where water_a is mostly body with crest dashes on it.
    """
    c.fill("b")
    for y, x0, length in ((2, 5, 7), (3, 3, 10), (4, 2, 12), (5, 2, 12), (6, 2, 12),
                          (7, 2, 12), (8, 3, 11), (9, 3, 10), (10, 4, 9), (11, 5, 8), (12, 6, 5)):
        for i in range(length):
            c.set(x0 + i, y, "c")
    # Holes and undercuts, so the mass reads as broken water and not as a flat patch.
    for x, y in ((5, 4), (6, 4), (10, 6), (11, 6), (4, 7), (9, 9), (8, 10), (7, 9), (11, 5)):
        c.set(x, y, "a")
    # The trough under the near edge, and three specks of spray thrown clear of the mass.
    for x, y in ((5, 13), (6, 13), (7, 13), (8, 13), (9, 12), (10, 12)):
        c.set(x, y, "a")
    for x, y in ((13, 3), (14, 6), (12, 10)):
        c.set(x, y, "c")


# -----------------------------------------------------------------------------------------------------------------
# The tile table. id order is the order in the PNG, row major with 16 tiles per row.
# kind is what the map layer means by it; solid is the collision rule; climb marks a ladder, stairs or hatch.

TILES = [
    (0, "deck_a", "floor", False, False, "steel"),
    (1, "deck_b", "floor", False, False, "steel"),
    (2, "deck_plain", "floor", False, False, "steel"),
    (3, "deck_grate", "floor", False, False, "steel"),
    (4, "deck_rivets", "floor", False, False, "steel"),
    (5, "deck_line_h", "floor", False, False, "steel"),
    (6, "deck_line_v", "floor", False, False, "steel"),
    (7, "deck_line_corner", "floor", False, False, "steel"),
    (8, "bulkhead", "wall", True, False, "steel"),
    (9, "bulkhead_plain", "wall", True, False, "steel"),
    (10, "bulkhead_vent", "wall", True, False, "steel"),
    (11, "bulkhead_light", "wall", True, False, "steel"),
    (12, "hatch_closed", "door", True, False, "steel"),
    (13, "hatch_open", "door", False, False, "steel"),
    (14, "deck_sill", "floor", False, False, "steel"),
    (15, "ladder", "climb", False, True, "steel"),
    (16, "stairs_up", "climb", False, True, "steel"),
    (17, "stairs_down", "climb", False, True, "steel"),
    (18, "pipes", "prop", True, False, "steel"),
    (19, "pipe_vert", "prop", True, False, "steel"),
    (20, "cable_run", "prop", True, False, "steel"),
    (21, "crate", "prop", True, False, "rust"),
    (22, "crate_stack", "prop", True, False, "rust"),
    (23, "barrel", "prop", True, False, "rust"),
    (24, "lifebuoy", "prop", True, False, "steel"),
    (25, "warning", "floor", False, False, "rust"),
    (26, "locker", "prop", True, False, "steel"),
    (27, "porthole_a", "wall", True, False, "steel"),
    (28, "porthole_b", "wall", True, False, "steel"),
    (29, "sign_wardroom", "wall", True, False, "steel"),
    (30, "sign_machinery", "wall", True, False, "steel"),
    (31, "sign_bridge", "wall", True, False, "steel"),
    (32, "wood_floor_a", "floor", False, False, "rust"),
    (33, "wood_floor_b", "floor", False, False, "rust"),
    (34, "table", "prop", True, False, "rust"),
    (35, "bunk", "prop", True, False, "steel"),
    (36, "quay_stone_a", "wall", True, False, "steel"),
    (37, "quay_stone_b", "wall", True, False, "steel"),
    (38, "quay_dark", "wall", True, False, "steel"),
    (39, "quay_cap", "floor", False, False, "steel"),
    (40, "bollard", "prop", True, False, "rust"),
    (41, "rail_post", "prop", True, False, "steel"),
    (42, "rail_bar", "prop", True, False, "steel"),
    (43, "water_a", "water", True, False, "sea"),
    (44, "water_b", "water", True, False, "sea"),
    (45, "water_edge", "water", True, False, "sea"),
    (46, "water_deep", "water", True, False, "sea"),
    (47, "water_foam", "water", True, False, "sea"),
]

DRAW = {
    "deck_a": deck_a,
    "deck_b": deck_b,
    "deck_plain": deck_plain,
    "deck_grate": deck_grate,
    "deck_rivets": deck_rivets,
    "deck_line_h": deck_line_h,
    "deck_line_v": deck_line_v,
    "deck_line_corner": deck_line_corner,
    "bulkhead": bulkhead,
    "bulkhead_plain": bulkhead_plain,
    "bulkhead_vent": bulkhead_vent,
    "bulkhead_light": bulkhead_light,
    "hatch_closed": hatch_closed,
    "hatch_open": hatch_open,
    "deck_sill": deck_sill,
    "ladder": ladder,
    "stairs_up": stairs_up,
    "stairs_down": stairs_down,
    "pipes": pipes,
    "pipe_vert": pipe_vert,
    "cable_run": cable_run,
    "crate": crate,
    "crate_stack": crate_stack,
    "barrel": barrel,
    "lifebuoy": lifebuoy,
    "warning": warning,
    "locker": locker,
    "porthole_a": porthole_a,
    "porthole_b": porthole_b,
    "sign_wardroom": sign_wardroom,
    "sign_machinery": sign_machinery,
    "sign_bridge": sign_bridge,
    "wood_floor_a": wood_floor_a,
    "wood_floor_b": wood_floor_b,
    "table": table,
    "bunk": bunk,
    "quay_stone_a": quay_stone_a,
    "quay_stone_b": quay_stone_b,
    "quay_dark": quay_dark,
    "quay_cap": quay_cap,
    "bollard": bollard,
    "rail_post": rail_post,
    "rail_bar": rail_bar,
    "water_a": water_a,
    "water_b": water_b,
    "water_edge": water_edge,
    "water_deep": water_deep,
    "water_foam": water_foam,
}

# Animated pairs: the first tile is what the map stores, the second is its next frame.
ANIMATIONS = {"water_a": "water_b", "porthole_a": "porthole_b"}
ANIM_FPS = 2.0

BY_NAME = {name: (tid, kind, solid, climb, group) for tid, name, kind, solid, climb, group in TILES}


# -----------------------------------------------------------------------------------------------------------------
# The sheet.


def render_sheet() -> Image.Image:
    rows = (TILE_COUNT + COLUMNS - 1) // COLUMNS
    image = Image.new("RGBA", (COLUMNS * TILE, rows * TILE), (0, 0, 0, 0))
    for tid, name, _kind, _solid, _climb, _group in TILES:
        cell = Cell()
        DRAW[name](cell)
        ox = (tid % COLUMNS) * TILE
        oy = (tid // COLUMNS) * TILE
        for y in range(TILE):
            for x in range(TILE):
                image.putpixel((ox + x, oy + y), KEY_TO_RGBA[cell.get(x, y)])
    return image


def tile_colours(cell: Cell) -> list:
    """The non backdrop keys a tile carries, in palette order."""
    keys = {cell.get(x, y) for y in range(TILE) for x in range(TILE)}
    keys.discard(BACKDROP)
    return [key for key, _entry, _hex, _use in PALETTE if key in keys]


# -----------------------------------------------------------------------------------------------------------------
# The sample map, 20x15. Built by coordinates rather than by hand aligned text, so the intent is readable and the
# checker proves the rows are consistent.

MAP_W = 20
MAP_H = 15

LEGEND = {
    "#": "bulkhead",
    "B": "bulkhead_plain",
    "=": "bulkhead_vent",
    "L": "bulkhead_light",
    "P": "porthole_a",
    ".": "deck_a",
    ",": "deck_b",
    "^": "deck_plain",
    "g": "deck_grate",
    "r": "deck_rivets",
    "-": "deck_line_h",
    "|": "deck_line_v",
    "n": "deck_sill",
    "h": "hatch_open",
    "H": "hatch_closed",
    "/": "ladder",
    "s": "stairs_up",
    "d": "stairs_down",
    "i": "pipes",
    "v": "pipe_vert",
    "c": "cable_run",
    "C": "crate",
    "S": "crate_stack",
    "O": "barrel",
    "Y": "lifebuoy",
    "!": "warning",
    "X": "locker",
    "1": "sign_wardroom",
    "2": "sign_machinery",
    "3": "sign_bridge",
    "W": "wood_floor_a",
    "w": "wood_floor_b",
    "T": "table",
    "K": "bunk",
}


def build_map():
    """Return (grid of tile names, spawns, triggers) for the sample map.

    The plan, in words, so a human can check the picture against the intent:

      rows 2 to 6   the officer cabin (columns 2 to 6, wood deck, bunk, locker, one crate),
                    the wardroom to its right (columns 9 to 13, wood deck, table, barrel, lifebuoy
                    on the bulkhead) and the engine space beyond the divider (columns 16 to 18,
                    grating, pipes and cables on the hull, hazard paint along the floor edge);
      row 7         the bulkhead between the rooms and the corridor, with three ways through:
                    an open hatch into the cabin, an open hatch into the wardroom, and a sill
                    into the engine space;
      rows 8 and 9  the corridor: deck plates and rivets, the painted line down row 9, a lifebuoy
                    on the port hull, and the closed hatch in the starboard hull at row 8 which is
                    the way out to Percy's wardroom;
      row 10        the bulkhead between the corridor and the hold, broken by a two tile sill;
      rows 11 to 13 the hold: crates, a barrel, hazard paint in front of the stairs, stairs up at
                    the starboard end and a ladder down beside them.
    """
    grid = [[("bulkhead" if (x in (0, MAP_W - 1) or y in (0, MAP_H - 1)) else "bulkhead_plain")
             for x in range(MAP_W)] for y in range(MAP_H)]

    def put(x, y, name):
        grid[y][x] = name

    # Officer cabin and wardroom: dark wood deck, two plank variants.
    for y in range(2, 7):
        for x in range(2, 7):
            put(x, y, "wood_floor_a" if (x + y) % 3 else "wood_floor_b")
        for x in range(9, 14):
            put(x, y, "wood_floor_a" if (x + y) % 2 else "wood_floor_b")

    # Engine space: walkable grating with plate around it.
    for y in range(2, 7):
        for x in range(16, 19):
            put(x, y, "deck_grate" if (y in (4, 5) and x in (17, 18)) else "deck_plain")

    # Row 7, the wall between rooms and corridor, with its three ways through.
    for x in range(1, MAP_W - 1):
        put(x, 7, "bulkhead")
    put(4, 7, "hatch_open")
    put(11, 7, "hatch_open")
    put(17, 7, "deck_sill")

    # Corridor rows 8 and 9.
    for x in range(1, MAP_W - 1):
        put(x, 8, "deck_a" if (x % 5) else "deck_b")
        put(x, 9, "deck_line_h")
    put(3, 8, "deck_rivets")
    put(16, 8, "deck_rivets")

    # Row 10, the wall to the hold, with a two tile sill.
    for x in range(1, MAP_W - 1):
        put(x, 10, "bulkhead")
    put(9, 10, "deck_sill")
    put(10, 10, "deck_sill")

    # The hold, rows 11 to 13.
    for y in range(11, 14):
        for x in range(1, MAP_W - 1):
            put(x, y, "deck_plain" if (x + y) % 4 else "deck_a")
    put(2, 11, "crate")
    put(3, 11, "crate_stack")
    put(2, 12, "crate")
    put(4, 12, "barrel")
    put(15, 11, "warning")
    put(15, 12, "warning")
    put(17, 11, "stairs_up")
    put(18, 11, "stairs_up")
    put(17, 12, "ladder")
    put(17, 13, "deck_sill")

    # Fittings on the hull and on the walls.
    put(2, 1, "bulkhead_light")
    put(4, 1, "porthole_a")
    put(7, 1, "bulkhead_vent")
    put(11, 1, "sign_wardroom")
    put(13, 1, "porthole_a")
    put(16, 1, "bulkhead_light")
    put(18, 1, "sign_machinery")
    put(2, 2, "bunk")
    put(3, 2, "bunk")
    put(6, 2, "locker")
    put(6, 5, "crate")
    put(12, 4, "table")
    put(13, 4, "table")
    put(13, 6, "barrel")
    put(9, 2, "lifebuoy")
    put(19, 3, "pipes")
    put(19, 4, "pipes")
    put(19, 5, "cable_run")
    put(19, 6, "cable_run")
    put(0, 3, "pipes")
    put(0, 4, "pipe_vert")
    put(0, 6, "cable_run")
    put(0, 8, "lifebuoy")
    put(0, 11, "sign_bridge")

    # The way out to Percy's wardroom, in the starboard hull at the corridor's end.
    put(19, 8, "hatch_closed")

    spawns = {"player_start": (2, 8), "from_percy": (18, 8), "from_lower_deck": (17, 12)}
    triggers = [
        {"name": "hatch_percy", "type": "map_exit", "x": 19, "y": 8,
         "target_map": "percy_wardroom", "target_spawn": "from_ship", "flag": "ship_hatch_open"},
        {"name": "ladder_down", "type": "map_exit", "x": 17, "y": 12,
         "target_map": "ship_lower_deck", "target_spawn": "from_hold", "flag": ""},
        {"name": "stairs_up", "type": "map_exit", "x": 17, "y": 11,
         "target_map": "ship_weather_deck", "target_spawn": "from_hold", "flag": ""},
    ]
    return grid, spawns, triggers


def char_for(name: str) -> str:
    for char, tile_name in LEGEND.items():
        if tile_name == name:
            return char
    raise SystemExit("make_env_ship: no legend character for %s" % name)


# -----------------------------------------------------------------------------------------------------------------
# Output writers.


def tileset_json(sheet_png: str) -> dict:
    tiles = []
    for tid, name, kind, solid, climb, group in TILES:
        cell = Cell()
        DRAW[name](cell)
        colours = tile_colours(cell)
        entry = {
            "id": tid,
            "type": kind,
            "properties": [
                {"name": "tile_name", "type": "string", "value": name},
                {"name": "solid", "type": "bool", "value": solid},
                {"name": "climb", "type": "bool", "value": climb},
                {"name": "palette_group", "type": "string", "value": group},
                {"name": "colours", "type": "string", "value": ",".join(colours)},
            ],
        }
        if name in ANIMATIONS:
            entry["animation"] = [{"tileid": BY_NAME[ANIMATIONS[name]][0], "duration": int(1000 / ANIM_FPS)}]
        tiles.append(entry)
    return {
        "format": 1,
        "kind": "tileset",
        "name": "ts_ship",
        "image": sheet_png,
        "imagewidth": COLUMNS * TILE,
        "imageheight": ((TILE_COUNT + COLUMNS - 1) // COLUMNS) * TILE,
        "tilewidth": TILE,
        "tileheight": TILE,
        "tilecount": TILE_COUNT,
        "columns": COLUMNS,
        "margin": 0,
        "spacing": 0,
        "tiledversion": "1.11.0",
        "type": "tileset",
        "properties": [
            {"name": "scene", "type": "string", "value": "map2_royal_navy_ship"},
            {"name": "palette_source", "type": "string",
             "value": "data/nes_palette.json (Ricoh 2C02), 10 colours: black backdrop plus steel, sea, rust groups"},
            {"name": "colour_budget", "type": "string",
             "value": "3 non backdrop colours per 16x16 tile, 10 in the scene"},
        ],
        "palette": [{"key": key, "entry": entry, "hex": hexv, "use": use}
                    for key, entry, hexv, use in PALETTE],
        "tiles": tiles,
    }


def map_json(grid, spawns, triggers) -> dict:
    rows = len(grid)
    width = len(grid[0])
    collision_rows = []
    for y in range(rows):
        collision_rows.append("".join("1" if BY_NAME[grid[y][x]][2] else "0" for x in range(width)))

    ground_data = []
    collision_data = []
    for y in range(rows):
        for x in range(width):
            name = grid[y][x]
            ground_data.append(BY_NAME[name][0] + 1)
            collision_data.append(1 if BY_NAME[name][2] else 0)

    objects = []
    for name, (x, y) in sorted(spawns.items()):
        objects.append({
            "id": len(objects) + 1,
            "name": name,
            "type": "spawn",
            "shape": "point",
            "x": x * TILE,
            "y": y * TILE,
            "width": 0,
            "height": 0,
            "point": True,
            "visible": True,
            "rotation": 0,
        })
    for trig in triggers:
        objects.append({
            "id": len(objects) + 1,
            "name": trig["name"],
            "type": trig["type"],
            "shape": "rectangle",
            "x": trig["x"] * TILE,
            "y": trig["y"] * TILE,
            "width": TILE,
            "height": TILE,
            "visible": True,
            "rotation": 0,
            "properties": [
                {"name": "target_map", "type": "string", "value": trig["target_map"]},
                {"name": "target_spawn", "type": "string", "value": trig["target_spawn"]},
                {"name": "flag", "type": "string", "value": trig["flag"]},
            ],
        })

    return {
        "format": 1,
        "kind": "map",
        "name": "Ship sample, Map 2",
        "class": "map",
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "infinite": False,
        "compressionlevel": -1,
        "width": width,
        "height": rows,
        "tilewidth": TILE,
        "tileheight": TILE,
        "nextlayerid": 4,
        "nextobjectid": len(objects) + 1,
        "tiledversion": "1.11.0",
        "tilesets": [{"firstgid": 1, "source": "../../game/sprites_src/env/ts_ship_tiled.json"}],
        "properties": [
            {"name": "map_id", "type": "string", "value": "ship_sample"},
            {"name": "collision_semantics", "type": "string",
             "value": "0 walkable, 1 blocked, 2 blocked until a story flag clears it (data/maps/all.json convention)"},
            {"name": "palette_source", "type": "string", "value": "data/nes_palette.json, 10 colours"},
        ],
        "tile_legend": {char_for(name): name for name in sorted(set(tile for row in grid for tile in row))},
        "spawns": {name: {"x": xy[0], "y": xy[1]} for name, xy in sorted(spawns.items())},
        "layers": [
            {
                "id": 1,
                "name": "ground",
                "type": "tilelayer",
                "width": width,
                "height": rows,
                "x": 0,
                "y": 0,
                "opacity": 1,
                "visible": True,
                "data": ground_data,
            },
            {
                "id": 2,
                "name": "collision",
                "type": "tilelayer",
                "width": width,
                "height": rows,
                "x": 0,
                "y": 0,
                "opacity": 1,
                "visible": False,
                "properties": [
                    {"name": "semantics", "type": "string",
                     "value": "0 walkable, 1 blocked, 2 blocked until a story flag clears it"},
                ],
                "data": collision_data,
            },
            {
                "id": 3,
                "name": "objects",
                "type": "objectgroup",
                "opacity": 1,
                "visible": True,
                "x": 0,
                "y": 0,
                "objects": objects,
            },
        ],
        "collision_rows": collision_rows,
    }


# -----------------------------------------------------------------------------------------------------------------
# The preview: the sheet at 3x with tile index labels, the map at 3x, and the harbour strip in both water frames.

DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "010", "010", "010", "010"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}
LABEL_INK = (252, 252, 252, 255)


def draw_number(canvas, x: int, y: int, value: int, scale: int = 2) -> int:
    text = str(value)
    for index, char in enumerate(text):
        glyph = DIGITS[char]
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            canvas.putpixel((x + index * (4 * scale) + col * scale + dx,
                                             y + row * scale + dy), LABEL_INK)
    return len(text) * 4 * scale


def paste_tile(canvas, sheet, tid, x: int, y: int, scale: int) -> None:
    sx = (tid % COLUMNS) * TILE
    sy = (tid // COLUMNS) * TILE
    block = sheet.crop((sx, sy, sx + TILE, sy + TILE)).resize((TILE * scale, TILE * scale),
                                                             Image.Resampling.NEAREST)
    canvas.alpha_composite(block, (x, y))


def paste_named(canvas, sheet, name, x, y, scale) -> None:
    paste_tile(canvas, sheet, BY_NAME[name][0], x, y, scale)


def render_preview(sheet: Image.Image, grid) -> Image.Image:
    pad = 12
    rows = (TILE_COUNT + COLUMNS - 1) // COLUMNS
    cell = TILE * SCALE
    label_h = 12
    sheet_w = COLUMNS * cell
    sheet_h = rows * (cell + label_h)
    map_w = MAP_W * cell
    map_h = MAP_H * cell
    strip_w = 10 * cell
    strip_h = 3 * cell
    width = pad + max(sheet_w, map_w, strip_w * 2 + pad) + pad
    height = pad + sheet_h + pad + map_h + pad + strip_h + pad
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    # The sheet, labelled with the tile id the map stores.
    for tid in range(TILE_COUNT):
        x = pad + (tid % COLUMNS) * cell
        y = pad + (tid // COLUMNS) * (cell + label_h)
        paste_tile(canvas, sheet, tid, x, y, SCALE)
        draw_number(canvas, x + 4, y + cell + 1, tid)

    # The map, rendered from the map data so the preview cannot drift from the file.
    map_top = pad + sheet_h + pad
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            paste_named(canvas, sheet, grid[y][x], pad + x * cell, map_top + y * cell, SCALE)

    # The harbour strip: quay, bollards and railing above the water, drawn in both water frames.
    strip_top = map_top + map_h + pad
    for frame, water in enumerate(("water_a", "water_b")):
        origin_x = pad + frame * (strip_w + pad)
        for row, tiles in enumerate((
            ("quay_cap", "quay_cap", "quay_cap", "quay_cap", "quay_cap",
             "quay_cap", "quay_cap", "quay_cap", "quay_cap", "quay_cap"),
            ("rail_post", "quay_stone_b", "rail_post", "quay_stone_b", "rail_post",
             "quay_stone_b", "rail_post", "quay_stone_b", "rail_post", "quay_stone_b"),
            ("water_edge", "water_edge", water, water, water,
             water, water, water, water, water),
        )):
            for col, name in enumerate(tiles):
                paste_named(canvas, sheet, name, origin_x + col * cell, strip_top + row * cell, SCALE)
    # A bollard standing on the quay, so the prop lands in context.
    paste_named(canvas, sheet, "bollard", pad + 2 * cell, strip_top, SCALE)
    paste_named(canvas, sheet, "bollard", pad + 6 * cell, strip_top, SCALE)

    return canvas


# -----------------------------------------------------------------------------------------------------------------
# Main.


def map_output_path(root: str) -> str:
    """data/maps/ship_sample.json, unless another lane's map already holds that name.

    Two cards asked for data/maps/ship_sample.json on 2026-10-21. This generator will not overwrite a map it did
    not write, so when the plain name holds a file whose "kind" is not "map" (this generator's Tiled map), the
    output moves to ship_sample_tiled.json and the run says so. check_env_tiles.py resolves the path the same way.
    """
    plain = os.path.join(root, "data", "maps", "ship_sample.json")
    if not os.path.isfile(plain):
        return plain
    try:
        with open(plain, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return os.path.join(root, "data", "maps", "ship_sample_tiled.json")
    if isinstance(payload, dict) and payload.get("kind") == "map":
        return plain
    return os.path.join(root, "data", "maps", "ship_sample_tiled.json")


def write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build(root: str) -> dict:
    """Write every output under root and return the paths that were written."""
    env_dir = os.path.join(root, "game", "sprites_src", "env")
    out_dir = os.path.join(root, "output")
    map_dir = os.path.join(root, "data", "maps")
    for path in (env_dir, out_dir, map_dir):
        os.makedirs(path, exist_ok=True)

    sheet = render_sheet()
    # The scene palette pass: every 16x16 tile into one of the four background palettes of
    # data/palettes/scene_ship.json, which also bounds the sheet to 12 drawable colours plus the
    # backdrop instead of the ten it used to spend freely. It runs on the in-memory sheet so the JSON,
    # the preview and the pixels stay the same picture.
    try:
        import scene_palette
        scene = scene_palette.load_scene(root, "ship")
        sheet = sheet.convert("RGBA")
        stats = scene_palette.enforce_ship_sheet(sheet, scene)
        print("scene palettes: ts_ship %d tiles, %d pixels rewritten"
              % (stats["tiles"], stats["pixels_moved"]))
    except (ImportError, FileNotFoundError) as exc:
        print("scene palettes: skipped (%s)" % exc)
    sheet_path = os.path.join(env_dir, "ts_ship.png")
    sheet.save(sheet_path, optimize=False)

    write_json(os.path.join(env_dir, "ts_ship.json"), {
        "name": "ts_ship",
        "frame_w": TILE,
        "frame_h": TILE,
        "frames": TILE_COUNT,
        "fps": 0.0,
        "kind": "tileset",
        "columns": COLUMNS,
        "rows": (TILE_COUNT + COLUMNS - 1) // COLUMNS,
    })
    write_json(os.path.join(env_dir, "ts_ship_tiled.json"), tileset_json("ts_ship.png"))

    grid, spawns, triggers = build_map()
    map_path = map_output_path(root)
    write_json(map_path, map_json(grid, spawns, triggers))

    render_preview(sheet, grid).save(os.path.join(out_dir, "env_ship_preview.png"), optimize=False)

    return {
        "sheet": sheet_path,
        "meta": os.path.join(env_dir, "ts_ship.json"),
        "tileset": os.path.join(env_dir, "ts_ship_tiled.json"),
        "map": map_path,
        "preview": os.path.join(out_dir, "env_ship_preview.png"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Map 2 ship tileset, sample map and preview.")
    parser.add_argument("--root", default=None, help="repo root; default is the parent of tools")
    args = parser.parse_args(argv)
    root = args.root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    paths = build(root)
    print("ts_ship: %d tiles, %dx%d, %d colours" % (TILE_COUNT, COLUMNS * TILE,
                                                    ((TILE_COUNT + COLUMNS - 1) // COLUMNS) * TILE, len(PALETTE)))
    if os.path.basename(paths["map"]) != "ship_sample.json":
        print("  note: data/maps/ship_sample.json holds another lane's map, so this map is ship_sample_tiled.json")
    for name in ("sheet", "meta", "tileset", "map", "preview"):
        print("  %-8s %s" % (name, paths[name]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
