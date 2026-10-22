#!/usr/bin/env python3
"""make_icons_nes.py: the NES item, weapon, status and cursor icon set, drawn from numbers in this file.

What it makes, all deterministic (no randomness, no image inputs, so a rerun writes the same bytes):

    game\\sprites_src\\icons\\spr_pp_icon_items_16.png   96x48   18 icons at 16x16, 6 columns
    game\\sprites_src\\icons\\spr_pp_icon_items_8.png    72x16   18 icons at 8x8, 9 columns
    game\\sprites_src\\icons\\spr_pp_icon_status_16.png  80x16   5 status icons at 16x16
    game\\sprites_src\\icons\\spr_pp_icon_status_8.png   40x8    5 status icons at 8x8
    game\\sprites_src\\icons\\spr_pp_icon_cursor_16.png  32x16   2 menu cursors at 16x16
    game\\sprites_src\\icons\\spr_pp_icon_cursor_8.png   16x8    2 menu cursors at 8x8
    a sidecar .json beside every sheet: grid, frame rectangle per icon, its sprite palette and its three
    palette entries with hex
    data\\palettes\\scene_icons.json    the scene palette in the same format as data\\palettes\\scene_ui.json
    output\\icons_preview.png          every icon at 4x with its name beside it, for the manager
    output\\icons_<sheet>_3x.png       one 3x preview per sheet
    output\\icons_demo_1.png, icons_demo_2.png   two 256x240 menu frames that place the whole set as
                                       sprites, so tools\\nes_composite_check.py can test the real budgets
    output\\icons_demo_1_3x.png, icons_demo_2_3x.png

The NES rules this file respects, and the reason the shapes look the way they do (ART-BIBLE section 1,
NESdev wiki "PPU palettes" and "PPU OAM", read 2026-10-21):

    - a sprite tile is 8x8 and selects one of 4 sprite palettes of 3 colours, entry 0 transparent, so a
      tile carries at most 3 opaque colours plus transparency;
    - there are 4 sprite palettes in a scene, so the whole set is painted from 4 triples, and an icon's
      identity comes from which triple it wears. That is how a NES inventory gets 25 icons out of 12
      colours: the same drawing language, different palette;
    - black is $0F only (the canonical black), never the forbidden $0D or a duplicate black;
    - flat colour: one dark rim, one mid tone, one light tone. No gradient, no anti aliasing, no
      dithering at all here, because at 8x8 and 16x16 a 2 px checker would read as noise. The rim is
      what makes the shape survive on any backdrop, exactly as the art bible asks for sprite art.

Every icon is drawn in a 16 unit design space and rasterised at 16 or at 8 with the same coordinates, so
the 8x8 version is the same object seen smaller, not a different asset. Rasterising samples the pixel
centre, then a one pixel dark rim is added outside the silhouette, which is why every drawing is kept
inside 1.4 to 14.6 design units.

Clean room (PLAN-V2 section 0): every shape here is a primitive written in this file (rectangle, disc,
ring, polygon, arc band, thick segment). No game art was downloaded, ripped, traced or measured; the only
references are the art bible's hardware rules and the character bible's description of the weapons.

Usage:
    python tools\\art\\make_icons_nes.py
    python tools\\art\\make_icons_nes.py --root <repo>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

DESIGN = 16.0
PREVIEW_SCALE = 4
THREE_X = 3
NEAREST = getattr(Image, "Resampling", Image).NEAREST
FRAME_W = 256
FRAME_H = 240
BACKDROP = 15

# 2C02 entry numbers, read from data\nes_palette.json. Never hex literals in the drawing code.
BLACK = 15    # $0F, the canonical black
GREY = 0      # $00
BLUE_DARK = 2  # $02, the window fill used by the UI card
GOLD = 40     # $28
WHITE = 48    # $30
RED = 22      # $16
GREEN = 26    # $1A
BLUE = 18     # $12

# Four sprite palettes of three colours: the scene budget. Every icon wears exactly one of them.
SPRITE_PALETTES = [
    {"name": "sp0", "colours": [BLACK, GOLD, WHITE]},
    {"name": "sp1", "colours": [BLACK, RED, WHITE]},
    {"name": "sp2", "colours": [BLACK, GREEN, WHITE]},
    {"name": "sp3", "colours": [BLACK, BLUE, WHITE]},
]

# One background palette: the menu window the icons sit on. Same entries as scene_ui.json bg0.
BACKGROUND_PALETTES = [
    {"name": "bg0", "colours": [BLUE_DARK, WHITE, GREY]},
]


# ---------------------------------------------------------------------------------------------------------
# Rasterising primitives. Every predicate answers "is the centre of this pixel inside the shape".
# Coordinates are design units, 0 at the left or top edge of the icon and 16 at the right or bottom.

def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1


def disc(cx, cy, r):
    rr = r * r
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= rr


def ellipse(cx, cy, rx, ry):
    return lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


def ring(cx, cy, r_out, r_in):
    ro = r_out * r_out
    ri = r_in * r_in
    return lambda x, y: ri <= (x - cx) ** 2 + (y - cy) ** 2 <= ro


def poly(points):
    def inside(x, y):
        hit = False
        count = len(points)
        j = count - 1
        for i in range(count):
            xi, yi = points[i]
            xj, yj = points[j]
            if (yi > y) != (yj > y):
                if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    hit = not hit
            j = i
        return hit
    return inside


def band(cx, cy, r_out, r_in, a0, a1):
    ro = r_out * r_out
    ri = r_in * r_in
    start = a0 % 360.0
    span = (a1 - a0) % 360.0

    def inside(x, y):
        dx, dy = x - cx, y - cy
        d2 = dx * dx + dy * dy
        if not (ri <= d2 <= ro):
            return False
        angle = math.degrees(math.atan2(dy, dx)) % 360.0
        return ((angle - start) % 360.0) <= span
    return inside


def seg(x0, y0, x1, y1, width):
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    half = (width / 2.0) ** 2

    def inside(x, y):
        if length2 == 0:
            return (x - x0) ** 2 + (y - y0) ** 2 <= half
        t = ((x - x0) * dx + (y - y0) * dy) / length2
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        px, py = x0 + t * dx, y0 + t * dy
        return (x - px) ** 2 + (y - py) ** 2 <= half
    return inside


def union(*preds):
    return lambda x, y: any(p(x, y) for p in preds)


def both(a, b):
    return lambda x, y: a(x, y) and b(x, y)


def minus(a, b):
    return lambda x, y: a(x, y) and not b(x, y)


class Art:
    """One icon being drawn: a mid tone body, a light tone detail, and explicit dark marks."""

    def __init__(self, size):
        self.size = size
        self.scale = size / DESIGN
        self.body = set()
        self.light = set()
        self.mark = set()

    def paint(self, target, pred):
        size = self.size
        scale = self.scale
        for py in range(size):
            cy = (py + 0.5) / scale
            for px in range(size):
                cx = (px + 0.5) / scale
                if pred(cx, cy):
                    target.add((px, py))

    def compose(self, dark, mid, light):
        """Body in mid, detail in light, marks in dark, then a one pixel dark rim outside the silhouette."""
        silhouette = self.body | self.light | self.mark
        rim = set()
        for (x, y) in silhouette:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbour = (x + dx, y + dy)
                if neighbour in silhouette:
                    continue
                if 0 <= neighbour[0] < self.size and 0 <= neighbour[1] < self.size:
                    rim.add(neighbour)
        pixels = {}
        for point in self.body:
            pixels[point] = mid
        for point in self.light:
            pixels[point] = light
        for point in self.mark:
            pixels[point] = dark
        for point in rim:
            pixels[point] = dark
        return pixels


# ---------------------------------------------------------------------------------------------------------
# The drawings. Each one paints body, light detail and dark marks in the 16 unit design space.

def draw_potion(a):
    a.paint(a.body, ellipse(8.0, 10.4, 4.9, 4.6))
    a.paint(a.body, rect(6.5, 4.2, 9.5, 6.6))
    a.paint(a.light, rect(6.1, 2.0, 9.9, 3.7))
    a.paint(a.light, disc(6.1, 9.4, 1.4))


def draw_ration(a):
    dome = both(ellipse(8.0, 6.2, 4.8, 4.8), lambda x, y: y <= 6.3)
    a.paint(a.body, union(rect(3.2, 6.0, 12.8, 12.4), dome))
    a.paint(a.light, both(ellipse(8.0, 6.2, 4.8, 4.8), lambda x, y: 4.0 <= y <= 5.4))
    a.paint(a.mark, seg(5.6, 7.8, 7.4, 10.8, 1.0))
    a.paint(a.mark, seg(8.1, 7.8, 9.9, 10.8, 1.0))


def draw_tea(a):
    cup = poly([(4.9, 6.2), (11.1, 6.2), (10.2, 12.0), (5.8, 12.0)])
    a.paint(a.body, cup)
    a.paint(a.body, band(11.2, 8.9, 2.5, 1.2, -70.0, 70.0))
    a.paint(a.light, rect(4.6, 5.2, 11.4, 6.3))
    a.paint(a.light, rect(2.8, 12.4, 13.2, 13.6))
    a.paint(a.mark, rect(6.2, 3.0, 7.0, 4.4))


def draw_key(a):
    if a.size <= 8:
        a.paint(a.body, ring(2.0, 4.0, 1.6, 0.6))
        a.paint(a.body, rect(3.0, 3.0, 15.0, 5.0))
        a.paint(a.body, rect(11.0, 5.0, 13.0, 9.0))
        return
    a.paint(a.body, ring(5.2, 8.0, 3.2, 1.6))
    a.paint(a.body, rect(7.6, 7.4, 14.2, 8.6))
    a.paint(a.body, rect(11.8, 8.6, 12.8, 10.9))
    a.paint(a.body, rect(13.6, 8.6, 14.6, 10.2))
    a.paint(a.light, rect(8.6, 7.0, 10.4, 8.2))


def draw_map(a):
    sheet = poly([(2.6, 4.6), (13.4, 3.4), (13.4, 11.4), (2.6, 12.6)])
    a.paint(a.body, sheet)
    a.paint(a.light, both(sheet, union(rect(6.2, 3.9, 7.0, 12.0), rect(9.8, 3.6, 10.6, 11.7))))
    a.paint(a.mark, seg(4.0, 9.8, 6.0, 7.4, 0.9))
    a.paint(a.mark, seg(7.4, 6.6, 9.0, 6.2, 0.9))
    a.paint(a.mark, seg(10.6, 7.4, 12.2, 9.4, 0.9))


def draw_phone(a):
    a.paint(a.body, rect(4.8, 1.8, 11.2, 14.2))
    a.paint(a.light, rect(5.9, 3.4, 10.1, 10.6))
    a.paint(a.mark, rect(6.9, 2.3, 9.1, 3.0))
    a.paint(a.mark, disc(8.0, 12.6, 0.9))


def draw_trident(a):
    if a.size <= 8:
        a.paint(a.body, rect(6.0, 7.0, 10.0, 15.0))
        a.paint(a.body, rect(1.0, 6.0, 15.0, 8.0))
        a.paint(a.body, union(rect(1.0, 1.0, 3.0, 7.0), rect(6.0, 1.0, 10.0, 7.0), rect(13.0, 1.0, 15.0, 7.0)))
        a.paint(a.light, union(rect(1.0, 1.0, 3.0, 3.0), rect(6.0, 1.0, 10.0, 3.0), rect(13.0, 1.0, 15.0, 3.0)))
        return
    a.paint(a.body, rect(7.2, 6.0, 8.8, 14.8))
    a.paint(a.body, rect(3.6, 5.8, 12.4, 7.2))
    a.paint(a.body, rect(3.6, 1.8, 5.6, 6.2))
    a.paint(a.body, rect(7.2, 1.4, 8.8, 6.2))
    a.paint(a.body, rect(10.4, 1.8, 12.4, 6.2))
    a.paint(a.light, union(rect(3.6, 1.8, 5.6, 3.0), rect(7.2, 1.4, 8.8, 2.6), rect(10.4, 1.8, 12.4, 3.0)))


def draw_bident(a):
    if a.size <= 8:
        a.paint(a.body, rect(6.0, 7.0, 10.0, 15.0))
        a.paint(a.body, rect(2.0, 6.0, 14.0, 8.0))
        a.paint(a.body, union(rect(2.0, 1.0, 5.0, 7.0), rect(11.0, 1.0, 14.0, 7.0)))
        a.paint(a.light, union(rect(2.0, 1.0, 5.0, 3.0), rect(11.0, 1.0, 14.0, 3.0)))
        return
    a.paint(a.body, rect(7.2, 6.0, 8.8, 14.8))
    a.paint(a.body, rect(4.6, 5.8, 11.4, 7.2))
    a.paint(a.body, rect(4.6, 1.8, 6.6, 6.2))
    a.paint(a.body, rect(9.4, 1.8, 11.4, 6.2))
    a.paint(a.light, union(rect(4.6, 1.8, 6.6, 3.0), rect(9.4, 1.8, 11.4, 3.0)))



def draw_sickle(a):
    a.paint(a.body, band(8.0, 7.6, 6.0, 4.2, 200.0, 345.0))
    a.paint(a.body, seg(13.0, 7.0, 11.4, 13.6, 2.0))
    a.paint(a.light, seg(12.6, 7.4, 11.2, 13.2, 1.0))
    a.paint(a.light, band(8.0, 7.6, 6.0, 5.4, 245.0, 310.0))


def draw_thunderbolt(a):
    bolt = poly([(9.6, 1.4), (4.4, 8.6), (7.6, 8.6), (6.2, 14.6), (11.8, 6.8), (8.6, 6.8)])
    a.paint(a.body, bolt)
    a.paint(a.light, both(bolt, poly([(9.0, 2.2), (5.8, 8.0), (6.8, 8.0)])))


def draw_helm(a):
    dome = both(ellipse(8.0, 8.0, 5.2, 5.2), lambda x, y: y <= 8.2)
    a.paint(a.body, union(dome, rect(2.9, 8.0, 13.1, 10.6)))
    a.paint(a.light, rect(3.6, 8.4, 12.4, 9.6))
    a.paint(a.light, rect(7.0, 2.8, 9.0, 4.2))
    a.paint(a.mark, rect(4.8, 5.8, 11.2, 7.4))
    a.paint(a.mark, rect(7.2, 7.4, 8.8, 10.4))


def draw_wristwatch(a):
    a.paint(a.body, rect(6.2, 1.6, 9.8, 4.4))
    a.paint(a.body, rect(6.2, 11.6, 9.8, 14.4))
    a.paint(a.body, disc(8.0, 8.0, 4.8))
    a.paint(a.light, disc(8.0, 8.0, 3.3))
    a.paint(a.mark, seg(8.0, 8.0, 8.0, 5.6, 0.9))
    a.paint(a.mark, seg(8.0, 8.0, 10.0, 8.8, 0.9))


def draw_badge(a):
    a.paint(a.body, seg(5.2, 5.4, 8.0, 1.8, 1.1))
    a.paint(a.body, seg(10.8, 5.4, 8.0, 1.8, 1.1))
    a.paint(a.body, rect(3.6, 5.2, 12.4, 13.6))
    a.paint(a.light, rect(4.8, 6.2, 11.2, 12.6))
    a.paint(a.mark, rect(5.8, 7.4, 10.2, 8.2))
    a.paint(a.mark, rect(5.8, 9.2, 9.4, 10.0))
    a.paint(a.mark, rect(5.8, 11.0, 8.2, 11.8))


def draw_tablet(a):
    a.paint(a.body, rect(2.6, 3.0, 13.4, 13.0))
    a.paint(a.light, rect(4.0, 4.4, 12.0, 10.6))
    a.paint(a.mark, disc(8.0, 11.8, 0.9))


def draw_sword(a):
    blade = poly([(12.4, 1.4), (13.8, 2.6), (11.6, 7.2), (8.4, 10.6), (7.0, 9.2), (10.0, 5.8), (12.0, 2.4)])
    a.paint(a.body, blade)
    a.paint(a.body, rect(5.2, 10.2, 8.4, 11.4))
    a.paint(a.body, rect(4.4, 12.0, 6.2, 14.6))
    a.paint(a.light, both(blade, poly([(13.0, 2.3), (10.6, 6.4), (11.4, 7.2)])))
    a.paint(a.light, rect(5.2, 10.2, 8.0, 11.2))


def draw_shield(a):
    plate = poly([(8.0, 1.8), (13.4, 4.0), (13.4, 9.0), (8.0, 14.4), (2.6, 9.0), (2.6, 4.0)])
    a.paint(a.body, plate)
    a.paint(a.light, poly([(8.0, 3.6), (11.8, 5.2), (11.8, 8.4), (8.0, 12.2), (4.2, 8.4), (4.2, 5.2)]))
    a.paint(a.mark, disc(8.0, 7.8, 1.8))


def draw_gem(a):
    stone = poly([(8.0, 1.6), (13.4, 6.2), (8.0, 14.2), (2.6, 6.2)])
    a.paint(a.body, stone)
    a.paint(a.light, poly([(8.0, 1.6), (10.8, 6.2), (8.0, 6.2)]))
    a.paint(a.light, poly([(8.0, 6.2), (11.2, 6.2), (8.0, 11.6)]))
    a.paint(a.light, seg(3.2, 6.4, 12.8, 6.4, 1.2))


def draw_coin(a):
    a.paint(a.body, disc(8.0, 8.0, 5.6))
    a.paint(a.light, ring(8.0, 8.0, 4.6, 3.9))
    a.paint(a.mark, rect(7.4, 5.2, 8.6, 10.8))
    a.paint(a.mark, rect(5.8, 6.6, 10.2, 7.8))
    a.paint(a.mark, rect(5.8, 8.6, 10.2, 9.8))


def draw_poison(a):
    if a.size <= 8:
        a.paint(a.body, disc(8.0, 6.5, 5.0))
        a.paint(a.body, rect(5.0, 10.0, 11.0, 13.5))
        a.paint(a.mark, rect(2.5, 4.0, 6.0, 7.0))
        a.paint(a.mark, rect(10.0, 4.0, 13.5, 7.0))
        a.paint(a.mark, rect(6.0, 10.5, 10.0, 12.5))
        return
    a.paint(a.body, disc(8.0, 6.9, 4.4))
    a.paint(a.body, rect(5.7, 10.2, 10.3, 13.0))
    a.paint(a.mark, rect(5.3, 5.9, 6.9, 7.9))
    a.paint(a.mark, rect(9.1, 5.9, 10.7, 7.9))
    a.paint(a.mark, rect(6.6, 10.8, 9.4, 11.8))
    a.paint(a.mark, rect(7.4, 8.6, 8.6, 9.6))


def draw_sleep(a):
    a.paint(a.body, rect(3.8, 2.6, 12.2, 4.6))
    a.paint(a.body, rect(3.8, 11.0, 12.2, 13.0))
    a.paint(a.body, seg(11.4, 4.2, 4.6, 11.4, 1.9))
    a.paint(a.light, rect(3.8, 2.4, 12.2, 3.6))


def draw_wet(a):
    drop = poly([(8.0, 1.4), (11.8, 8.0), (11.8, 10.2), (8.0, 14.2), (4.2, 10.2), (4.2, 8.0)])
    a.paint(a.body, drop)
    a.paint(a.light, disc(6.4, 8.6, 1.3))


def draw_charged(a):
    a.paint(a.body, poly([(8.0, 1.4), (9.4, 6.6), (14.6, 8.0), (9.4, 9.4), (8.0, 14.6),
                          (6.6, 9.4), (1.4, 8.0), (6.6, 6.6)]))
    a.paint(a.light, poly([(8.0, 5.4), (8.9, 7.1), (10.6, 8.0), (8.9, 8.9), (8.0, 10.6),
                           (7.1, 8.9), (5.4, 8.0), (7.1, 7.1)]))


def draw_shadow(a):
    if a.size <= 8:
        a.paint(a.body, disc(8.0, 4.0, 4.0))
        a.paint(a.body, poly([(2.0, 15.0), (4.0, 7.0), (12.0, 7.0), (14.0, 15.0)]))
        a.paint(a.light, rect(4.0, 2.0, 6.0, 4.0))
        a.paint(a.light, rect(10.0, 2.0, 12.0, 4.0))
        return
    a.paint(a.body, disc(8.0, 4.8, 2.9))
    a.paint(a.body, poly([(3.6, 14.6), (5.0, 7.6), (11.0, 7.6), (12.4, 14.6)]))
    a.paint(a.light, rect(6.1, 4.0, 6.9, 4.9))
    a.paint(a.light, rect(9.1, 4.0, 9.9, 4.9))
    a.paint(a.light, seg(12.0, 8.4, 12.6, 13.6, 0.9))


def draw_hand(a):
    a.paint(a.body, rect(1.4, 4.4, 5.6, 13.4))
    a.paint(a.body, rect(5.0, 6.0, 11.8, 8.0))
    a.paint(a.body, rect(4.0, 2.6, 6.2, 5.4))
    a.paint(a.light, rect(2.0, 5.2, 3.0, 12.6))
    a.paint(a.mark, seg(2.2, 10.0, 5.2, 10.0, 1.0))


def draw_arrow(a):
    a.paint(a.body, poly([(1.8, 1.2), (1.8, 11.2), (9.6, 6.2)]))
    a.paint(a.light, poly([(2.8, 3.0), (2.8, 9.4), (6.6, 6.2)]))


# ---------------------------------------------------------------------------------------------------------
# The icon table.
#   palette: which of the four sprite palettes the icon wears (the scene budget)
#   mid / light: the two roles used, as 2C02 entries; dark is always $0F
#   draw: the function above

ICONS = [
    # name, palette, mid, light, draw, note
    ("potion", "sp1", RED, WHITE, draw_potion, "round flask, cork, one glint"),
    ("ration", "sp0", GOLD, WHITE, draw_ration, "loaf with two crust cuts"),
    ("tea", "sp0", WHITE, GOLD, draw_tea, "cup with a handle and a saucer"),
    ("key", "sp0", GOLD, WHITE, draw_key, "ring, shaft, two teeth; Konrad's keyring shape"),
    ("map", "sp0", WHITE, GOLD, draw_map, "folded sheet, two folds, a plotted route"),
    ("phone", "sp3", BLUE, WHITE, draw_phone, "slab, screen, speaker, home button"),
    ("trident", "sp0", GOLD, WHITE, draw_trident, "three prongs; Percy"),
    ("bident", "sp3", BLUE, WHITE, draw_bident, "two prongs; Hadrian"),
    ("sickle", "sp0", GOLD, WHITE, draw_sickle, "crescent blade and a short handle; Konrad"),
    ("thunderbolt", "sp3", BLUE, WHITE, draw_thunderbolt, "zigzag bolt; Zander"),
    ("helm", "sp0", GOLD, WHITE, draw_helm, "dome, brow band, eye slit; Hadrian's helm"),
    ("wristwatch", "sp0", GOLD, WHITE, draw_wristwatch, "round face on a strap; Konrad's tell"),
    ("badge", "sp0", WHITE, GOLD, draw_badge, "lanyard cord, card, three text lines"),
    ("tablet", "sp3", BLUE, WHITE, draw_tablet, "slab, screen, one button"),
    ("sword", "sp3", BLUE, WHITE, draw_sword, "modern cutlass: curved blade, guard, grip"),
    ("shield", "sp0", GOLD, WHITE, draw_shield, "heater shield, inset field, boss"),
    ("gem", "sp1", RED, WHITE, draw_gem, "faceted stone, setting line"),
    ("coin", "sp0", GOLD, WHITE, draw_coin, "disc, inner ring, a struck mark"),
    ("poison", "sp2", GREEN, WHITE, draw_poison, "skull, two sockets, jaw"),
    ("sleep", "sp3", BLUE, WHITE, draw_sleep, "Z, two bars and a diagonal"),
    ("wet", "sp3", BLUE, WHITE, draw_wet, "drop with one glint"),
    ("charged", "sp3", BLUE, WHITE, draw_charged, "four point spark"),
    ("shadow", "sp0", BLACK, WHITE, draw_shadow, "black silhouette, white eyes, white rim"),
    ("hand", "sp0", GOLD, WHITE, draw_hand, "menu cursor: pointing hand"),
    ("arrow", "sp0", GOLD, WHITE, draw_arrow, "menu cursor: solid arrow"),
]

ITEM_NAMES = [name for (name, *_rest) in ICONS[:18]]
STATUS_NAMES = [name for (name, *_rest) in ICONS[18:23]]
CURSOR_NAMES = [name for (name, *_rest) in ICONS[23:]]

GROUP_NAMES = {"items": ITEM_NAMES, "status": STATUS_NAMES, "cursor": CURSOR_NAMES}

# Icons whose 8x8 art is a separate, chunkier drawing rather than the 16x16 drawing seen smaller, because at
# 8x8 one pixel is 2 design units and their 16x16 features would vanish.
TINY_VARIANTS = ("key", "trident", "bident", "poison", "shadow")

# Group, size -> column count and the heading the preview prints. Rows follow from the icon count.
SHEET_LAYOUT = {
    ("items", 16): {"cols": 6, "title": "items and weapons, 16x16"},
    ("items", 8): {"cols": 9, "title": "items and weapons, 8x8"},
    ("status", 16): {"cols": 5, "title": "status effects, 16x16"},
    ("status", 8): {"cols": 5, "title": "status effects, 8x8"},
    ("cursor", 16): {"cols": 2, "title": "menu cursors, 16x16"},
    ("cursor", 8): {"cols": 2, "title": "menu cursors, 8x8"},
}


SHEET_NAMES = {
    ("items", 16): "spr_pp_icon_items_16",
    ("items", 8): "spr_pp_icon_items_8",
    ("status", 16): "spr_pp_icon_status_16",
    ("status", 8): "spr_pp_icon_status_8",
    ("cursor", 16): "spr_pp_icon_cursor_16",
    ("cursor", 8): "spr_pp_icon_cursor_8",
}


def icon_by_name(name):
    for row in ICONS:
        if row[0] == name:
            return row
    raise KeyError(name)


# ---------------------------------------------------------------------------------------------------------
# Palette reading.

def load_nes_entries(root):
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = data["colours"]
    entries = {}
    for entry in data.get("entries", []):
        entries[int(entry["index"])] = {"hex": entry["hex"].lower(), "usable": bool(entry.get("usable")),
                                       "hue": entry.get("hue", "")}
    out = {}
    for index in range(len(colours)):
        value = colours[index].lstrip("#").lower()
        record = entries.get(index, {})
        out[index] = {
            "index": index,
            "hex": "#" + value,
            "usable": record.get("usable", True),
            "hue": record.get("hue", ""),
        }
    return out


def entry_or_die(entries, index, where):
    if index not in entries:
        raise SystemExit("%s uses palette entry %d, which is not in data\\nes_palette.json" % (where, index))
    if not entries[index]["usable"]:
        raise SystemExit("%s uses palette entry %d ($%02X), which the palette file marks unusable"
                         % (where, index, index))
    return entries[index]


# ---------------------------------------------------------------------------------------------------------
# Building.

def render_icon(name, size, entries):
    row = icon_by_name(name)
    _, palette_name, mid, light, draw, _note = row
    entry_or_die(entries, mid, name)
    entry_or_die(entries, light, name)
    entry_or_die(entries, BLACK, name)
    art = Art(size)
    draw(art)
    pixels = art.compose(BLACK, mid, light)
    palette = next(p for p in SPRITE_PALETTES if p["name"] == palette_name)
    for index in (mid, light, BLACK):
        if index not in palette["colours"]:
            raise SystemExit("%s wants entry %d, which sprite palette %s does not hold"
                             % (name, index, palette_name))
    opaque = set(pixels.values())
    return {"pixels": pixels, "opaque": opaque, "palette": palette_name,
            "roles": {"dark": BLACK, "mid": mid, "light": light}}


def build_sheet(root, group_key, size, entries):
    layout = SHEET_LAYOUT[(group_key, size)]
    cols = layout["cols"]
    names = GROUP_NAMES[group_key]
    rows = (len(names) + cols - 1) // cols
    width = cols * size
    height = rows * size
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels_out = sheet.load()
    frames = []
    for position, name in enumerate(names):
        col = position % cols
        row = position // cols
        x0 = col * size
        y0 = row * size
        drawn = render_icon(name, size, entries)
        for (x, y), index in drawn["pixels"].items():
            px, py = x0 + x, y0 + y
            if not (0 <= px < width and 0 <= py < height):
                raise SystemExit("%s pixel (%d,%d) falls outside the sheet" % (name, px, py))
            rgb = entries[index]["hex"].lstrip("#")
            pixels_out[px, py] = (int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16), 255)
        frames.append({
            "index": position,
            "name": name,
            "x": x0,
            "y": y0,
            "w": size,
            "h": size,
            "tiles_w": size // 8,
            "tiles_h": size // 8,
            "sprite_objects": (size // 8) * (size // 8),
            "sprite_palette": drawn["palette"],
            "colours": drawn["roles"],
            "hex": {role: entries[index]["hex"] for role, index in drawn["roles"].items()},
            "note": icon_by_name(name)[5],
        })
    return sheet, frames, width, height


def write_sheet(root, group_key, size, entries, out_dir):
    sheet, frames, width, height = build_sheet(root, group_key, size, entries)
    stem = SHEET_NAMES[(group_key, size)]
    png_path = os.path.join(out_dir, stem + ".png")
    sheet.save(png_path)
    used = sorted({index for frame in frames for index in frame["colours"].values()})
    palette_names = sorted({frame["sprite_palette"] for frame in frames})
    layout = SHEET_LAYOUT[(group_key, size)]
    rows = (len(frames) + layout["cols"] - 1) // layout["cols"]
    payload = {
        "format": 1,
        "kind": "nes_icon_sheet",
        "name": stem,
        "size": "%dx%d" % (width, height),
        "frame_w": size,
        "frame_h": size,
        "frames": len(frames),
        "grid": {"cols": layout["cols"], "rows": rows,
                 "cell_w": size, "cell_h": size, "sheet_w": width, "sheet_h": height},
        "group": group_key,
        "title": layout["title"],
        "transparent": True,
        "sprite_palettes_used": palette_names,
        "sprite_palette_count": len(palette_names),
        "sprite_objects_per_frame": (size // 8) * (size // 8),
        "max_sprite_objects_if_all_frames_on_screen": sum(f["sprite_objects"] for f in frames),
        "colours_used": [
            {"index": index, "hex": entries[index]["hex"], "hue": entries[index]["hue"], "usable": True}
            for index in used
        ],
        "colour_count": len(used),
        "rule": ("sprite art: at most 3 opaque colours plus transparency on any 8x8 tile; entry 0 of a sprite "
                 "palette is transparency; black is $0F; no gradient, no anti aliasing, no dithering; "
                 "each icon wears one of the four sprite palettes in data\\palettes\\scene_icons.json"),
        "size_variants": ([name for name in TINY_VARIANTS if name in [f["name"] for f in frames]]
                          if size <= 8 else []),
        "size_variant_note": ("these five are simplified drawings made for 8x8, not the 16x16 art seen smaller: "
                              "at 8x8 one pixel is 2 design units, so their 16x16 features would vanish"
                              if size <= 8 else ""),
        "palette_file": "data\\palettes\\scene_icons.json",
        "built_by": "tools\\art\\make_icons_nes.py",
        "frames_detail": frames,
    }
    json_path = os.path.join(out_dir, stem + ".json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return {"stem": stem, "png": png_path, "json": json_path, "sheet": sheet, "frames": frames,
            "width": width, "height": height, "group": group_key, "size": size,
            "palettes": len(palette_names), "colours": len(used)}


# ---------------------------------------------------------------------------------------------------------
# Scene palette.

def write_scene_palette(root, entries):
    path = os.path.join(root, "data", "palettes", "scene_icons.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "format": 1,
        "kind": "scene_palette",
        "scene": "icons",
        "backdrop": BACKDROP,
        "rule": ("NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, "
                 "4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is a "
                 "data/nes_palette.json entry number"),
        "notes": [
            "written by tools/art/make_icons_nes.py for the ICONS-NES card; no scene_icons.json existed, "
            "so this card defines it in the same format as scene_ui.json, as the card allows",
            "backdrop $0F black is the shared backdrop, the same choice as scene_ui.json and scene_title.json",
            "bg0 is the menu window from scene_ui.json bg0: fill $02, border and labels $30, ground band $00",
            "sp0 gold: metal, currency, food, the two cursors",
            "sp1 red: the potion and the gem",
            "sp2 green: poison",
            "sp3 blue: the electronics (phone, tablet), the two prongs of steel (bident, cutlass), sleep, wet "
            "and charged",
            "every icon uses 3 entries or fewer of its triple; the shadow icon uses 2 (black silhouette, "
            "white eyes) because a shadow is an absence of light",
            "scene_ui.json already draws a menu cursor in sp0 [15,40,48]; the cursor icons here wear the "
            "same triple, so either art can replace the other without a palette change",
            "a battle scene that shows an item icon must be checked against its own sprite palettes "
            "(data/palettes/scene_battle_*.json hold the battle cast); an icon is recoloured to the nearest "
            "of that scene's four triples, the drawing does not change",
        ],
        "background": [],
        "sprites": [],
    }
    for group in BACKGROUND_PALETTES:
        payload["background"].append({
            "name": group["name"],
            "colours": group["colours"],
            "hex": [entries[index]["hex"] for index in group["colours"]],
        })
    while len(payload["background"]) < 4:
        spare = BACKGROUND_PALETTES[0]["colours"]
        payload["background"].append({
            "name": "bg%d" % len(payload["background"]),
            "colours": spare,
            "hex": [entries[index]["hex"] for index in spare],
            "spare": True,
        })
    for group in SPRITE_PALETTES:
        payload["sprites"].append({
            "name": group["name"],
            "colours": group["colours"],
            "hex": [entries[index]["hex"] for index in group["colours"]],
        })
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return path


# ---------------------------------------------------------------------------------------------------------
# Previews.

def load_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def text_size(draw, text, font):
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0], box[3] - box[1]
    except AttributeError:
        return draw.textsize(text, font=font)


def three_x(sheet, path):
    width = sheet.width * THREE_X
    height = sheet.height * THREE_X
    out = Image.new("RGBA", (width, height), (124, 124, 124, 255))
    scaled = sheet.resize((width, height), NEAREST)
    out.alpha_composite(scaled)
    out.convert("RGB").save(path)
    return path


def labelled_preview(sheets, path, entries):
    scale = PREVIEW_SCALE
    font = load_font(11)
    heading_font = load_font(14)
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    pad = 10
    gap = 8
    sections = []
    for sheet in sheets:
        frames = sheet["frames"]
        cols = SHEET_LAYOUT[(sheet["group"], sheet["size"])]["cols"]
        rows = (len(frames) + cols - 1) // cols
        cell_w = max(sheet["size"] * scale, 96)
        cell_h = sheet["size"] * scale + 16
        sections.append({"sheet": sheet, "cols": cols, "rows": rows, "cell_w": cell_w, "cell_h": cell_h})
    total_w = max(sec["cols"] * sec["cell_w"] for sec in sections) + pad * 2
    total_h = pad
    for sec in sections:
        total_h += 24 + sec["rows"] * sec["cell_h"] + gap
    total_h += pad
    canvas = Image.new("RGBA", (total_w, total_h), (28, 28, 40, 255))
    draw = ImageDraw.Draw(canvas)
    y = pad
    for sec in sections:
        sheet = sec["sheet"]
        title = "%s   %dx%d   %d icons   %d sprite palettes   %d colours" % (
            sheet["stem"], sheet["width"], sheet["height"], len(sheet["frames"]), sheet["palettes"],
            sheet["colours"])
        draw.text((pad, y), title, font=heading_font, fill=(248, 248, 248))
        y += 24
        for position, frame in enumerate(sheet["frames"]):
            col = position % sec["cols"]
            row = position // sec["cols"]
            x = pad + col * sec["cell_w"]
            cell_y = y + row * sec["cell_h"]
            box = (frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"])
            art = sheet["sheet"].crop(box)
            art = art.resize((frame["w"] * scale, frame["h"] * scale), Image.NEAREST)
            draw.rectangle([x, cell_y, x + frame["w"] * scale, cell_y + frame["h"] * scale],
                           fill=(124, 124, 124, 255))
            canvas.alpha_composite(art, (x, cell_y))
            label = frame["name"]
            tw, _th = text_size(draw, label, font)
            draw.text((x, cell_y + frame["h"] * scale + 2), label, font=font, fill=(216, 216, 216))
            sub = frame["sprite_palette"]
            draw.text((x + tw + 4, cell_y + frame["h"] * scale + 2), sub, font=font, fill=(160, 160, 160))
        y += sec["rows"] * sec["cell_h"] + gap
    canvas.convert("RGB").save(path)
    return path


# ---------------------------------------------------------------------------------------------------------
# Demo frames: the whole set placed as sprites on a menu screen, so the composite checker can test budgets.

def build_demo_frame(root, entries, icons, placements, out_png, out_json, label):
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 255))
    mask = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    fill_hex = entries[BLUE_DARK]["hex"].lstrip("#")
    border_hex = entries[WHITE]["hex"].lstrip("#")
    fill_rgb = tuple(int(fill_hex[i:i + 2], 16) for i in (0, 2, 4))
    border_rgb = tuple(int(border_hex[i:i + 2], 16) for i in (0, 2, 4))
    draw.rectangle([0, 0, FRAME_W, FRAME_H], fill=fill_rgb + (255,))
    draw.rectangle([8, 8, FRAME_W - 9, FRAME_H - 9], outline=border_rgb + (255,), width=2)
    sprites = []
    for entry in placements:
        stem, size, x, y = entry
        art = render_icon(stem, size, entries)
        for (px, py), index in art["pixels"].items():
            rgb = entries[index]["hex"].lstrip("#")
            frame.putpixel((x + px, y + py), (int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16), 255))
            mask.putpixel((x + px, y + py), (255, 255, 255, 255))
        for tile_y in range(size // 8):
            for tile_x in range(size // 8):
                sprites.append({"x": x + tile_x * 8, "y": y + tile_y * 8, "w": 8, "h": 8, "icon": stem})
    frame.convert("RGB").save(out_png)
    mask_path = out_json.replace("_sprites.json", "_mask.png")
    mask.save(mask_path)
    with open(out_json, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"format": 1, "kind": "nes_sprite_list", "frame": os.path.basename(out_png),
                   "label": label, "backdrop": entries[BACKDROP]["hex"],
                   "sprite_height": 8, "mask": os.path.basename(mask_path), "sprites": sprites},
                  handle, indent=2)
        handle.write("\n")
    return out_png, out_json, sprites



def demo_placements():
    items16 = [name for (name, *_r) in ICONS[:18]]
    status = [name for (name, *_r) in ICONS[18:23]]
    cursors = [name for (name, *_r) in ICONS[23:]]
    first = items16[:9]
    second = items16[9:]
    layouts = []
    for group in (first, second):
        placements = []
        for position, name in enumerate(group):
            col = position % 4
            row = position // 4
            placements.append((name, 16, 16 + col * 56, 16 + row * 32))
        for position, name in enumerate(status):
            placements.append((name, 8, 16 + position * 24, 136))
        for position, name in enumerate(cursors):
            placements.append((name, 8, 16 + position * 24, 168))
        layouts.append(placements)
    return layouts


# ---------------------------------------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw the NES icon set and its sheets.")
    parser.add_argument("--root", default=None, help="repository root; default is two levels above this file")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    entries = load_nes_entries(root)
    out_dir = os.path.join(root, "game", "sprites_src", "icons")
    os.makedirs(out_dir, exist_ok=True)
    output_dir = os.path.join(root, "output")
    os.makedirs(output_dir, exist_ok=True)

    built = []
    for (group_key, size) in (("items", 16), ("items", 8), ("status", 16), ("status", 8),
                              ("cursor", 16), ("cursor", 8)):
        info = write_sheet(root, group_key, size, entries, out_dir)
        built.append(info)
        preview = three_x(info["sheet"], os.path.join(output_dir, info["stem"] + "_3x.png"))
        print("P: %-26s %3dx%-3d %2d icons  %d sprite palettes  %d colours  -> %s"
              % (info["stem"], info["width"], info["height"], len(info["frames"]), info["palettes"],
                 info["colours"], os.path.basename(info["png"])))

    scene_path = write_scene_palette(root, entries)
    print("P: scene palette -> %s" % os.path.relpath(scene_path, root).replace("\\", "\\"))

    preview_path = labelled_preview(built, os.path.join(output_dir, "icons_preview.png"), entries)
    print("P: labelled %dx preview -> %s" % (PREVIEW_SCALE, os.path.basename(preview_path)))

    layouts = demo_placements()
    for number, placements in enumerate(layouts, start=1):
        png = os.path.join(output_dir, "icons_demo_%d.png" % number)
        json_path = os.path.join(output_dir, "icons_demo_%d_sprites.json" % number)
        build_demo_frame(root, entries, ICONS, placements, png, json_path,
                         "ICONS-NES demo frame %d: items, status and cursors placed as sprites" % number)
        three_x(Image.open(png).convert("RGBA"), os.path.join(output_dir, "icons_demo_%d_3x.png" % number))
        print("P: demo frame %d: %d icons, %d sprite objects 8x8 -> %s"
              % (number, len(placements), sum((s // 8) * (s // 8) for (_n, s, _x, _y) in placements),
                 os.path.basename(png)))

    print("done: %d sheets, %d icons, 4 sprite palettes, backdrop $0F" % (len(built), len(ICONS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
