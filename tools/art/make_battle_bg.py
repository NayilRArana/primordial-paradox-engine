#!/usr/bin/env python3
"""make_battle_bg.py: draw the four NES battle background strips, deterministically.

Card t_1c5a8599 (BG-BATTLE). Four 256x112 strips:

    corridor    ship corridor: steel bulkheads, a pipe run, a red hatch
    wardroom    wood panelling, portholes, a long table under ceiling lamps
    deck_night  open deck at night: rigging, sea horizon, railing, deck plates
    quay_dusk   Southampton quay at dusk: bollards, a crane silhouette, water

How the NES rules are kept, by construction rather than by hope
--------------------------------------------------------------
1. The picture is drawn on the attribute grid. Each strip is 16 by 7 cells of 16x16 pixels, and every
   cell is painted from ONE of the scene's four background palettes and only from that palette's three
   colours plus the scene's one shared backdrop. So every 16x16 attribute area holds at most 3 colours
   plus the backdrop, and every colour change falls on a 16 pixel boundary (ART-BIBLE 1.1 rule 8).
2. Every colour is an entry of data\\nes_palette.json, named by its number in the scene palette file.
   The script refuses to write a pixel that is not one of those entries, so no off palette colour can
   reach the PNG by accident.
3. Flat bands and 2 pixel checkers only. Dither is the 2x2 checker produced by checker(); there is no
   gradient, no blend and no anti aliasing anywhere in this file, because nothing is resampled: pixels
   are written one at a time and the 3x preview is a nearest neighbour zoom.
4. Tiles repeat. The layout is a grid of cell letters, so the same 8x8 tile bitmap is reused wherever a
   letter repeats, the way a real NES background is built. The script counts the distinct 8x8 tiles and
   writes the count into the JSON beside each PNG (budget: 128).
5. The floor under the party block is the shared backdrop on the strips that declare `party_floor`, which is all
   four of them. The block's placement is not typed here: it is read from data\\ui_layouts.json, the battle
   screen's four sprites with role `party`, so a layout move moves the floor with it. The party bodies are the
   light entry of each hero triple and those four clear RULE 0 point 2 on the backdrop $0F and not on the mixed
   floors the corridor, the deck and the quay carried, so a strip that declares it paints role 3 (the backdrop)
   over the block and leaves every other pixel of the strip alone. The corridor and the wardroom were landed by
   card t_d64eb2a9 (section 7.4 point 2); the deck night and the quay dusk were scoped out of that card and were
   ruled in by card t_0949bd4e, so the four strips cannot disagree (section 12 point 2, drawn by card
   t_12c9b18f).

6. The scene palette file keeps the audit rows it already carries. `data\\palettes\\scene_battle_<name>.json` is
   written whole, and the `judged` list in it is a cast decision plus the row that measures it (cards t_4f18c0ac
   and t_0949bd4e), so a regeneration used to delete a ruling without failing anything. The writer now carries
   that one key forward unchanged, in the position it already holds, and refuses a file that is not a scene
   palette for the same scene rather than overwriting it. Every palette, note and hex still comes from this
   file, so the scene file keeps one owner for its numbers.

7. The `notes` list is this script's as well (card t_8ebcb489). `judged` is a whole key only a card writes, so it
   can be carried forward by key; `notes` is generator text that hand edits had been appending to, and a carry
   rule for it would need a marker telling generator lines from hand lines. So there is no carry rule: the writer
   emits `notes` whole, and a note that has to survive a regeneration is a line in the SCENES table below. Two
   notes that lived only in a written file now live there, and the two hand edited files reproduce byte for byte.

Outputs
-------
    game\\sprites_src\\bg\\bg_battle_<name>.png        the strip
    game\\sprites_src\\bg\\bg_battle_<name>.json       sizes, palettes, tile count, cell layout
    data\\palettes\\scene_battle_<name>.json           the scene palette set (NES-PALETTES format)
    output\\bg_battle_preview.png                     2x2 contact sheet at 3x

Usage
    python tools\\art\\make_battle_bg.py
    python tools\\art\\make_battle_bg.py --root <repo> --preview <path>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

TILE = 8
CELL = 16
W = 256
H = 112
COLS = 16
ROWS = 7
SCALE = 3

BACKDROP = 0x0F  # the canonical black, ART-BIBLE 1.3


# -----------------------------------------------------------------------------------------------------------------
# Cell painting. A cell is 16 rows of 16 role numbers: 0, 1, 2 select one of the palette's three colours and
# 3 selects the shared backdrop. Nothing else can be written, which is what keeps the attribute rule true.


def blank() -> list:
    return [[0] * CELL for _ in range(CELL)]


def fill(c, role: int) -> None:
    for y in range(CELL):
        row = c[y]
        for x in range(CELL):
            row[x] = role


def rect(c, x0: int, y0: int, x1: int, y1: int, role: int) -> None:
    for y in range(max(0, y0), min(CELL - 1, y1) + 1):
        row = c[y]
        for x in range(max(0, x0), min(CELL - 1, x1) + 1):
            row[x] = role


def hline(c, y: int, x0: int, x1: int, role: int) -> None:
    if 0 <= y < CELL:
        for x in range(max(0, x0), min(CELL - 1, x1) + 1):
            c[y][x] = role


def vline(c, x: int, y0: int, y1: int, role: int) -> None:
    if 0 <= x < CELL:
        for y in range(max(0, y0), min(CELL - 1, y1) + 1):
            c[y][x] = role


def dots(c, points, role: int) -> None:
    for x, y in points:
        if 0 <= x < CELL and 0 <= y < CELL:
            c[y][x] = role


def checker(c, x0: int, y0: int, x1: int, y1: int, a: int, b: int) -> None:
    """A 2 pixel checker, the only dither this project allows (ART-BIBLE: flat bands, no gradients)."""
    for y in range(max(0, y0), min(CELL - 1, y1) + 1):
        for x in range(max(0, x0), min(CELL - 1, x1) + 1):
            c[y][x] = a if (((x - x0) // 2) + ((y - y0) // 2)) % 2 == 0 else b


def disc(c, cx: float, cy: float, r_in: float, r_out: float, role_in, role_ring) -> None:
    for y in range(CELL):
        for x in range(CELL):
            d = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
            if d <= r_in:
                c[y][x] = role_in
            elif d <= r_out:
                c[y][x] = role_ring


# -----------------------------------------------------------------------------------------------------------------
# Ship corridor. bg0 steel panel, bg1 dark steel, bg2 red hatch, bg3 pipes.


def cor_ceil(c) -> None:
    fill(c, 0)
    rect(c, 0, 0, 15, 1, 2)
    hline(c, 2, 0, 15, 2)
    rect(c, 0, 12, 15, 13, 1)
    hline(c, 14, 0, 15, 2)
    dots(c, [(2, 6), (13, 6), (2, 9), (13, 9)], 1)


def cor_bulk(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 1)
    hline(c, 15, 0, 15, 2)
    vline(c, 0, 0, 15, 2)
    dots(c, [(2, 3), (13, 3), (2, 12), (13, 12)], 1)


def cor_bulk_rib(c) -> None:
    cor_bulk(c)
    rect(c, 7, 1, 8, 14, 1)
    vline(c, 6, 1, 14, 2)
    vline(c, 9, 1, 14, 2)


def cor_floor(c) -> None:
    fill(c, 0)
    for x in range(0, CELL, 2):
        vline(c, x, 0, 15, 1)
    hline(c, 7, 0, 15, 2)
    hline(c, 15, 0, 15, 2)


def cor_pipe(c) -> None:
    fill(c, 3)
    for top in (1, 9):
        rect(c, 0, top, 15, top + 5, 0)
        hline(c, top, 0, 15, 1)
        hline(c, top + 5, 0, 15, 2)
    vline(c, 0, 1, 6, 2)
    vline(c, 0, 9, 14, 2)


def cor_valve(c) -> None:
    cor_pipe(c)
    for y in range(CELL):
        for x in range(CELL):
            d = ((x + 0.5 - 8) ** 2 + (y + 0.5 - 4) ** 2) ** 0.5
            if 4.0 < d <= 5.4:
                c[y][x] = 1
            elif d <= 1.6:
                c[y][x] = 1
            elif d <= 5.4 and (abs(x + 0.5 - 8) < 1.0 or abs(y + 0.5 - 4) < 1.0):
                c[y][x] = 1


def cor_hatch(c, tx: int, ty: int) -> None:
    """One quadrant of a 32x48 hatch: frame, bevel, wheel, bolts. Drawn in block coordinates."""
    fill(c, 1)
    for y in range(CELL):
        for x in range(CELL):
            X = tx * CELL + x
            Y = ty * CELL + y
            if X < 2 or X > 29 or Y < 2 or Y > 45:
                c[y][x] = 0
            elif X < 4 or X > 27 or Y < 4 or Y > 43:
                c[y][x] = 2
            for bx, by in ((6, 9), (25, 9), (6, 38), (25, 38)):
                if abs(X - bx) <= 1 and abs(Y - by) <= 1:
                    c[y][x] = 2
            dx = X + 0.5 - 16.0
            dy = Y + 0.5 - 24.0
            d = (dx * dx + dy * dy) ** 0.5
            if 6.4 < d <= 8.0:
                c[y][x] = 2
            elif d <= 1.8:
                c[y][x] = 2
            elif d <= 8.0 and (abs(dx) < 1.0 or abs(dy) < 1.0 or abs(abs(dx) - abs(dy)) < 1.0):
                c[y][x] = 2


# -----------------------------------------------------------------------------------------------------------------
# Wardroom. bg0 wood, bg1 dark wood, bg2 porthole at night, bg3 linen and brass.


def war_panel(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 1)
    hline(c, 15, 0, 15, 1)
    vline(c, 0, 0, 15, 1)
    hline(c, 1, 0, 15, 2)
    for x in range(2, 14, 4):
        hline(c, 6, x, x + 1, 1)
    dots(c, [(3, 11), (12, 11)], 2)


def war_panel_head(c) -> None:
    war_panel(c)
    rect(c, 4, 9, 11, 11, 1)
    hline(c, 9, 4, 11, 2)


def war_beam(c) -> None:
    fill(c, 0)
    rect(c, 0, 4, 15, 11, 1)
    hline(c, 4, 0, 15, 2)
    hline(c, 11, 0, 15, 2)
    hline(c, 0, 0, 15, 0)


def war_lamp(c) -> None:
    """A shaded lamp under the beam: the cell keeps the beam colour so the ceiling stays one surface."""
    fill(c, 0)
    vline(c, 7, 0, 3, 1)
    vline(c, 8, 0, 3, 1)
    rect(c, 5, 4, 10, 6, 1)
    hline(c, 6, 5, 10, 2)
    disc(c, 8.0, 9.0, 2.2, 3.2, 2, 1)
    hline(c, 13, 5, 10, 1)


def war_porthole(c) -> None:
    fill(c, 0)
    disc(c, 8.0, 8.0, 6.8, 7.8, 1, 2)
    hline(c, 12, 3, 12, 0)
    dots(c, [(5, 4), (10, 5), (6, 9)], 2)


def war_chair(c) -> None:
    fill(c, 0)
    rect(c, 3, 1, 12, 10, 1)
    hline(c, 1, 3, 12, 2)
    vline(c, 3, 1, 15, 1)
    vline(c, 12, 1, 15, 1)
    hline(c, 15, 3, 12, 2)


def war_table(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 2)
    hline(c, 15, 0, 15, 1)
    disc(c, 4.5, 6.5, 2.6, 3.4, 1, 2)
    disc(c, 11.5, 6.5, 2.6, 3.4, 1, 2)
    dots(c, [(7, 11), (8, 11)], 2)


def war_apron(c) -> None:
    fill(c, 1)
    hline(c, 0, 0, 15, 2)
    hline(c, 13, 0, 15, 0)
    hline(c, 14, 0, 15, 0)
    vline(c, 3, 2, 12, 0)
    vline(c, 12, 2, 12, 0)


def war_floor(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 1)
    hline(c, 8, 0, 15, 1)
    vline(c, 3, 0, 7, 1)
    vline(c, 11, 8, 15, 1)
    dots(c, [(7, 3), (15, 11)], 2)


# -----------------------------------------------------------------------------------------------------------------
# Deck at night. bg0 sky, bg1 sea, bg2 deck steel, bg3 rigging silhouette.


def deck_sky(c) -> None:
    fill(c, 0)
    dots(c, [(2, 3), (7, 6), (12, 2), (4, 11), (10, 12), (14, 8)], 2)


def deck_sky_low(c) -> None:
    fill(c, 0)
    checker(c, 0, 10, 15, 15, 0, 1)
    dots(c, [(3, 4), (9, 2), (13, 6)], 2)


def deck_moon(c) -> None:
    fill(c, 0)
    disc(c, 8.0, 6.0, 4.2, 4.6, 2, 2)
    dots(c, [(6, 5), (9, 7), (7, 8)], 1)


def deck_horizon(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 2)
    hline(c, 1, 0, 15, 2)
    hline(c, 6, 0, 15, 1)
    dots(c, [(3, 6), (11, 6)], 2)
    hline(c, 14, 0, 15, 1)


def deck_sea(c) -> None:
    fill(c, 0)
    hline(c, 3, 0, 15, 1)
    hline(c, 12, 0, 15, 1)
    dots(c, [(2, 3), (9, 3), (13, 3), (5, 12), (11, 12)], 2)


def deck_plate(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 2)
    hline(c, 15, 0, 15, 2)
    dots(c, [(2, 2), (13, 2), (2, 13), (13, 13)], 1)
    hline(c, 7, 0, 15, 2)


def deck_rail(c) -> None:
    deck_plate(c)
    rect(c, 0, 1, 15, 3, 1)
    rect(c, 0, 9, 15, 11, 1)
    vline(c, 5, 0, 15, 1)
    vline(c, 6, 0, 15, 1)


def deck_shroud(c) -> None:
    fill(c, 3)
    vline(c, 2, 0, 15, 2)
    vline(c, 9, 0, 15, 2)
    for y in (1, 6, 11):
        hline(c, y, 2, 9, 1)


# -----------------------------------------------------------------------------------------------------------------
# Quay at dusk. bg0 dusk sky, bg1 quay stone, bg2 water, bg3 silhouette.


def quay_sky_high(c) -> None:
    fill(c, 0)
    checker(c, 0, 12, 15, 15, 0, 1)


def quay_sky_low(c) -> None:
    fill(c, 1)
    checker(c, 0, 10, 15, 15, 1, 2)
    hline(c, 0, 0, 15, 0)


def quay_sky_gold(c) -> None:
    fill(c, 2)
    checker(c, 0, 0, 15, 3, 2, 1)


def quay_building(c) -> None:
    fill(c, 2)
    rect(c, 0, 5, 15, 15, 0)
    hline(c, 5, 0, 15, 0)
    for x in (3, 8, 13):
        rect(c, x, 8, x + 1, 10, 1)
    for x in (5, 10, 15):
        rect(c, x, 12, x, 13, 1)


def quay_stone(c) -> None:
    fill(c, 0)
    hline(c, 0, 0, 15, 1)
    hline(c, 7, 0, 15, 2)
    hline(c, 15, 0, 15, 2)
    vline(c, 0, 0, 15, 2)
    vline(c, 8, 8, 15, 2)


def quay_bollard(c) -> None:
    quay_stone(c)
    rect(c, 5, 4, 10, 15, 2)
    rect(c, 4, 3, 11, 5, 2)
    hline(c, 3, 4, 11, 1)
    vline(c, 5, 4, 15, 1)


def quay_water(c) -> None:
    fill(c, 0)
    hline(c, 3, 0, 15, 1)
    hline(c, 11, 0, 15, 1)
    dots(c, [(2, 6), (7, 7), (12, 6), (5, 14), (10, 14)], 2)


def quay_water_near(c) -> None:
    fill(c, 0)
    checker(c, 0, 0, 15, 7, 0, 1)
    hline(c, 12, 0, 15, 1)
    dots(c, [(4, 10), (11, 11)], 2)


def quay_crane(c, tx: int, ty: int) -> None:
    """One quadrant of a 64x32 crane silhouette: sky in palette role 2, steel in role 0, lattice role 1."""
    fill(c, 2)
    for y in range(CELL):
        for x in range(CELL):
            X = tx * CELL + x
            Y = ty * CELL + y
            steel = False
            if 4 <= Y <= 7:
                steel = True
            if 26 <= X <= 33 and 4 <= Y <= 31:
                steel = True
            if 44 <= X <= 47 and 8 <= Y <= 22:
                steel = (X in (45, 46))
            if 40 <= X <= 51 and 22 <= Y <= 26:
                steel = True
            if steel:
                c[y][x] = 0
                if ((X + Y) % 4 == 0) or ((X * 3 + Y) % 7 == 0):
                    c[y][x] = 1


# -----------------------------------------------------------------------------------------------------------------
# The scenes. Palettes are entry numbers from data\\nes_palette.json, so nothing is guessed.


SCENES = [
    {
        "name": "corridor",
        "title": "ship corridor",
        "cell_count": 13,
        "party_floor": True,
        "notes": [
            "grey steel bulkheads with a rivet seam, a pipe run under the deckhead, a red access hatch",
            "bg0 the bulkhead plate and the deckhead, bg1 the deck floor grating, bg2 the hatch, bg3 the pipes",
            "the hatch is a 32x48 block, so its cells are quadrants of one shape rather than four shapes",
        ],
        "background": [
            ("bg0", [0x00, 0x10, 0x02]),
            ("bg1", [0x02, 0x00, 0x12]),
            ("bg2", [0x16, 0x06, 0x26]),
            ("bg3", [0x10, 0x30, 0x12]),
        ],
        "sprites": [
            ("sp0", [0x00, 0x10, 0x0F]),
            ("sp1", [0x07, 0x17, 0x28]),
            ("sp2", [0x02, 0x12, 0x30]),
            ("sp3", [0x16, 0x26, 0x30]),
        ],
        "layout": [
            "cccccccccccccccc",
            "pppvppppppppvppp",
            "bbbbrbbbbbABbbbb",
            "bbbbrbbbbbCDbbbb",
            "bbbbrbbbbbEFbbbb",
            "..r...r....r...r",
            "ffffffffffffffff",
        ],
        "cells": {
            "c": (cor_ceil, "bg0"),
            "p": (cor_pipe, "bg3"),
            "v": (cor_valve, "bg3"),
            "b": (cor_bulk, "bg0"),
            "r": (cor_bulk_rib, "bg0"),
            ".": (cor_bulk, "bg1"),
            "f": (cor_floor, "bg1"),
            "A": (lambda c: cor_hatch(c, 0, 0), "bg2"),
            "B": (lambda c: cor_hatch(c, 1, 0), "bg2"),
            "C": (lambda c: cor_hatch(c, 0, 1), "bg2"),
            "D": (lambda c: cor_hatch(c, 1, 1), "bg2"),
            "E": (lambda c: cor_hatch(c, 0, 2), "bg2"),
            "F": (lambda c: cor_hatch(c, 1, 2), "bg2"),
        },
    },
    {
        "name": "wardroom",
        "title": "wardroom",
        "cell_count": 9,
        "party_floor": True,
        "notes": [
            "wood panelling under a beamed deckhead with two lamps, three portholes, a laid table",
            "bg0 the panelling, bg1 the beams, chairs and deck, bg2 the portholes at night, bg3 the linen and brass",
            "the table is two rows: linen on top, the wooden apron in front, so it reads as a long table in perspective",
        ],
        "background": [
            ("bg0", [0x17, 0x07, 0x28]),
            ("bg1", [0x08, 0x07, 0x17]),
            ("bg2", [0x02, 0x01, 0x30]),
            ("bg3", [0x30, 0x10, 0x28]),
        ],
        "sprites": [
            ("sp0", [0x00, 0x10, 0x0F]),
            ("sp1", [0x07, 0x17, 0x28]),
            ("sp2", [0x02, 0x12, 0x30]),
            ("sp3", [0x08, 0x17, 0x30]),
        ],
        "layout": [
            "LLLLoLLLLLoLLLLL",
            "wwOwwwwwOwwwwOww",
            "wwkwwwwkwwwwwkww",
            "hhTTTTTTTTTTTThh",
            "wwttttttttttttww",
            "FFFFFFFFFFFFFFFF",
            "FFFFFFFFFFFFFFFF",
        ],
        "cells": {
            "L": (war_beam, "bg1"),
            "o": (war_lamp, "bg1"),
            "w": (war_panel, "bg0"),
            "h": (war_panel_head, "bg0"),
            "O": (war_porthole, "bg2"),
            "k": (war_chair, "bg1"),
            "T": (war_table, "bg3"),
            "t": (war_apron, "bg1"),
            "F": (war_floor, "bg1"),
        },
    },
    {
        "name": "deck_night",
        "title": "open deck at night",
        "cell_count": 8,
        "party_floor": True,
        # The deck was scoped out of card t_d64eb2a9 and its floor was measured as not $0F; card t_0949bd4e ruled
        # it in so the four strips cannot disagree (knowledge/PALETTE-RULINGS-2026-10-25.md section 12 point 2).
        "party_floor_ruling": (
            "this strip was scoped out of card t_d64eb2a9 and its block floor measured as not $0F under the hero "
            "four; card t_0949bd4e ruled it in with the corridor and the wardroom so the four strips cannot "
            "disagree, and card t_12c9b18f drew it"
        ),
        "notes": [
            "night sky with stars and a moon, a sea horizon, rigging and a railing, steel deck plates",
            "bg0 the sky, bg1 the sea, bg2 the deck and railing, bg3 the rigging, which is why the rigging cells are black",
            "the sea horizon is one flat row of tiles so the far water stays a straight band, as it must at 256 px",
            "bg2 $00 $30 $02 is also the triple the enemy is drawn from: both enemy slots in data/ui_layouts.json (tile 3,8 and 12,11, 32x32) fall on bg2 cells, and the third entry is $30 rather than $10 so navy_sailor.png's own triple $02 $0F $30 fits whole, $0F coming from the shared backdrop (knowledge/PALETTE-RULINGS-2026-10-25.md section 15, card t_34b1d96a)",
            # Written into data/palettes/scene_battle_deck_night.json by card t_cc0c5bd5 as a hand typed line and moved
            # here by card t_8ebcb489, because the writer owns the notes list whole (this file's point 7).
            "sprite palettes are declared for the battle cast the scene draws: solved 2026-10-24 (card t_cc0c5bd5, ruling knowledge/PALETTE-RULINGS-2026-10-24.md) against sailor_battle.png (168x32, seven 24x32 frames) and navy_sailor.png (96x32, three 32x32 frames), the strip's fight cast; the walking cast keeps its own grounds (ship sp1 for sailor and percy, sp1 of the other three battle strips and the three towns for konrad), so those 16x16 sheets are not carried here and are not judged here; since card t_0949bd4e this strip is party_cast, so these four rows are the declaration and not the spend (tools/scene_palette_set.py allowed_sprite_rows returns the four reserved hero triples for this scene, and the rows are spent on nothing but the scene's own 25 colour count), kept because they are the only set ever measured for this strip's own slots: a deck that stops being party_cast re-measures them rather than resurrects them (card t_8ebcb489)",
        ],
        "background": [
            ("bg0", [0x02, 0x01, 0x30]),
            ("bg1", [0x01, 0x11, 0x21]),
            ("bg2", [0x00, 0x30, 0x02]),
            ("bg3", [0x0F, 0x02, 0x00]),
        ],
        "sprites": [
            # The four rows card t_cc0c5bd5 solved and wrote into data/palettes/scene_battle_deck_night.json, which were
            # the corridor's boilerplate rows here until card t_8ebcb489. A file and its generator that disagree is a
            # regeneration reverting a measured decision, so the table follows the file.
            ("sp0", [0x00, 0x0F, 0x10]),
            ("sp1", [0x02, 0x0F, 0x30]),
            ("sp2", [0x07, 0x17, 0x36]),
            ("sp3", [0x08, 0x27, 0x28]),
        ],
        "layout": [
            "sssssssssssssmss",
            "ySyyySyyyyySyySy",
            "hhhhhhhhhhhhhhhh",
            "eeeeeeeeeeeeeeee",
            "RRRRRRRRRRRRRRRR",
            "DDDDDDDDDDDDDDDD",
            "DDDDDDDDDDDDDDDD",
        ],
        "cells": {
            "s": (deck_sky, "bg0"),
            "y": (deck_sky_low, "bg0"),
            "m": (deck_moon, "bg0"),
            "S": (deck_shroud, "bg3"),
            "h": (deck_horizon, "bg1"),
            "e": (deck_sea, "bg1"),
            "R": (deck_rail, "bg2"),
            "D": (deck_plate, "bg2"),
        },
    },
    {
        "name": "quay_dusk",
        "title": "Southampton quay at dusk",
        "cell_count": 16,
        "party_floor": True,
        # Same ruling as the deck: card t_d64eb2a9 left this floor alone and card t_0949bd4e ruled both in, so one
        # of the four strips cannot carry a different party floor from the other three (section 12 point 2).
        "party_floor_ruling": (
            "this strip was scoped out of card t_d64eb2a9 and its block floor measured as not $0F under the hero "
            "four; card t_0949bd4e ruled it in with the deck so the four strips cannot disagree, and card "
            "t_12c9b18f drew it"
        ),
        "notes": [
            "dusk sky in flat bands with a 2 px checker at each band edge, the town roofline, a crane silhouette, water, granite quay with bollards",
            "bg0 the sky, bg1 the quay stone, bg2 the water, bg3 the silhouettes, which put the sky colour in role 2 so the crane reads as a hole in the sky",
            "the crane is a 64x32 block, so its four cells are quadrants of one shape",
            # The ruling that nothing draws this strip. It was a hand typed line in data/palettes/scene_battle_quay_dusk.json
            # until card t_8ebcb489, which is one regeneration away from gone: the writer owns the notes list whole (this
            # file's point 7), so a note that has to survive is a line here. Text unchanged from the written file.
            "NO cast and NO judged row, by gamedev ruling on card t_4f18c0ac (knowledge/PALETTE-RULINGS-2026-10-24.md): nothing in play draws this strip. No encounter row names it (no bg_battle or background key exists in data/encounters/all.json), pp_battle_bg_for_room in game/scripts/pp_battle_director/pp_battle_director.gml maps only lower_deck, ship_cabin and deck_day, so a fight on southampton_town_quay (room_palette quay_night) falls back to the corridor strip, and the slice's two fights are both on the ship. The pier cast lands with the card that authorises a pier fight, and it is the Navy pair: navy_sailor plus petty_officer, which both need $02 $0F $30, so that card moves sp2's $12 to $0F (the same move the deck made on 2026-10-24) and adds the judged row in the same edit",
        ],
        "background": [
            ("bg0", [0x26, 0x16, 0x28]),
            ("bg1", [0x00, 0x10, 0x02]),
            ("bg2", [0x01, 0x11, 0x26]),
            ("bg3", [0x0F, 0x02, 0x26]),
        ],
        "sprites": [
            ("sp0", [0x00, 0x10, 0x0F]),
            ("sp1", [0x07, 0x17, 0x28]),
            ("sp2", [0x02, 0x12, 0x30]),
            ("sp3", [0x16, 0x26, 0x28]),
        ],
        "layout": [
            "aaaaaaaaaaaaaaaa",
            "yyyyyGHIJyyyyccc",
            "BBBBBKLMNwwwwwww",
            "wwwwwwwwwwwwwwww",
            "nnnnnnnnnnnnnnnn",
            "ssbsssssbssssbss",
            "ssssssssssssssss",
        ],
        "cells": {
            "a": (quay_sky_high, "bg0"),
            "y": (quay_sky_low, "bg0"),
            "c": (quay_sky_gold, "bg0"),
            "B": (quay_building, "bg3"),
            "G": (lambda c: quay_crane(c, 0, 0), "bg3"),
            "H": (lambda c: quay_crane(c, 1, 0), "bg3"),
            "I": (lambda c: quay_crane(c, 2, 0), "bg3"),
            "J": (lambda c: quay_crane(c, 3, 0), "bg3"),
            "K": (lambda c: quay_crane(c, 0, 1), "bg3"),
            "L": (lambda c: quay_crane(c, 1, 1), "bg3"),
            "M": (lambda c: quay_crane(c, 2, 1), "bg3"),
            "N": (lambda c: quay_crane(c, 3, 1), "bg3"),
            "w": (quay_water, "bg2"),
            "n": (quay_water_near, "bg2"),
            "s": (quay_stone, "bg1"),
            "b": (quay_bollard, "bg1"),
        },
    },
]


# -----------------------------------------------------------------------------------------------------------------
# Rendering.


def load_party_block(root: str) -> tuple:
    """The party block's pixel rects, read from data/ui_layouts.json.

    The battle screen's `sprites` list gives four slots at x 224, y 32, 64, 96, 128, each 24x32, already in
    pixels (its `party` list carries the same four slots in tile coordinates, x 28, y 4, 8, 12, 16 at 8 px
    tiles). Reading the layout file rather than copying those numbers means the floor follows the block if
    the block ever moves (PALETTE-RULINGS-2026-10-25.md section 7.4 point 2).
    """
    path = os.path.join(root, "data", "ui_layouts.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    for screen in data["screens"]:
        if screen["name"] != "battle":
            continue
        rects = []
        for sprite in screen.get("sprites", []):
            if sprite.get("role") != "party":
                continue
            rects.append((sprite["x"], sprite["y"], sprite["w"], sprite["h"]))
        if not rects:
            raise SystemExit("%s battle screen names no party sprite to floor" % path)
        party_tiles = [(slot["x"], slot["y"]) for slot in screen.get("party", [])]
        if len(party_tiles) != len(rects):
            raise SystemExit(
                "%s battle screen has %d party sprites and %d party slots: fix the layout before drawing"
                % (path, len(rects), len(party_tiles))
            )
        # The `party` list is in tiles and the `sprites` list in pixels, which is the one place this file
        # could silently read the wrong unit (it did once). The two lists have to agree, so say so.
        tile_px = data["frame"]["tile"]
        for slot, rect in zip(party_tiles, rects):
            if (slot[0] * tile_px, slot[1] * tile_px) != (rect[0], rect[1]):
                raise SystemExit(
                    "%s battle screen: party slot at tile %s is not the sprite at pixel %s"
                    % (path, slot, (rect[0], rect[1]))
                )
        return rects, path
    raise SystemExit("%s has no battle screen to read the party block from" % path)


def load_palette(root: str) -> tuple:
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = [value.strip().lower() for value in data["colours"]]
    if len(colours) != 64:
        raise SystemExit("%s holds %d entries, expected 64" % (path, len(colours)))
    return colours, path


def build_scene(scene: dict, entries: list, party_rects=None) -> dict:
    names = [name for name, _ in scene["background"]]
    palettes = {
        name: [(index, entries[index]) for index in numbers] for name, numbers in scene["background"]
    }
    backdrop_hex = entries[BACKDROP]

    # Guard against the bug this card already hit once: two cells sharing a letter in the dict, so the
    # second silently replaces the first and a row is painted with the wrong palette (the quay sky row
    # came out as stone that way). A dict cannot hold two keys, so the count is the tell: the scene
    # declares how many cell letters it should have and a shadowed letter makes the dict one short.
    used_letters = {letter for row in scene["layout"] for letter in row}
    unused_letters = sorted(set(scene["cells"]) - used_letters)
    if unused_letters:
        raise SystemExit("scene %s defines cells no layout row uses: %s" % (scene["name"], unused_letters))
    if len(scene["cells"]) != scene["cell_count"]:
        raise SystemExit(
            "scene %s has %d cell letters, expected %d: a duplicate letter is shadowing another cell"
            % (scene["name"], len(scene["cells"]), scene["cell_count"])
        )

    roles = [[3] * W for _ in range(H)]
    used = set()
    cell_names = []
    for row_index, row in enumerate(scene["layout"]):
        if len(row) != COLS:
            raise SystemExit("scene %s row %d is %d cells, expected %d" % (scene["name"], row_index, len(row), COLS))
        line = []
        for col_index, letter in enumerate(row):
            if letter not in scene["cells"]:
                raise SystemExit("scene %s has no cell for %r" % (scene["name"], letter))
            painter, palette_name = scene["cells"][letter]
            if palette_name not in palettes:
                raise SystemExit("scene %s cell %r names palette %r" % (scene["name"], letter, palette_name))
            cell = blank()
            painter(cell)
            line.append("%s/%s" % (letter, palette_name))
            for y in range(CELL):
                target = roles[row_index * CELL + y]
                for x in range(CELL):
                    role = cell[y][x]
                    if role not in (0, 1, 2, 3):
                        raise SystemExit("role %r out of range in %s" % (role, scene["name"]))
                    target[col_index * CELL + x] = role
        cell_names.append(line)

    # The party block's floor, on the strips that declare it: role 3 is the shared backdrop, which every
    # attribute area may use, so this paints nothing the palettes do not already carry. It runs BEFORE the
    # pixel resolve and the tile count, so the tiles, the colour list and the sidecar all describe what
    # ships rather than what was drawn first.
    party_floor = None
    if scene.get("party_floor"):
        if not party_rects:
            raise SystemExit("scene %s asks for the party floor but no placement was read" % scene["name"])
        painted = []
        count = 0
        for x, y, w, h in party_rects:
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(W, x + w), min(H, y + h)
            if x1 <= x0 or y1 <= y0:
                continue
            for py in range(y0, y1):
                row = roles[py]
                for px in range(x0, x1):
                    row[px] = 3
                    count += 1
            painted.append([x0, y0, x1 - x0, y1 - y0])
        party_floor = {"rects": painted, "pixels": count}

    # resolve every pixel through its attribute area, so a pixel can never borrow another area's palette
    pixels = [[backdrop_hex] * W for _ in range(H)]
    palette_of_area = []
    for row in range(ROWS):
        palette_of_area.append([scene["cells"][letter][1] for letter in scene["layout"][row]])
    for y in range(H):
        for x in range(W):
            role = roles[y][x]
            if role == 3:
                pixels[y][x] = backdrop_hex
                used.add(backdrop_hex)
            else:
                palette_name = palette_of_area[y // CELL][x // CELL]
                number, colour = palettes[palette_name][role]
                pixels[y][x] = colour
                used.add(colour)

    allowed = {backdrop_hex}
    for name, numbers in scene["background"]:
        for index in numbers:
            allowed.add(entries[index])
    stray = used - allowed
    if stray:
        raise SystemExit("scene %s wrote colours outside its four palettes: %s" % (scene["name"], sorted(stray)))

    tiles = {}
    for ty in range(H // TILE):
        for tx in range(W // TILE):
            block = tuple(
                pixels[ty * TILE + y][tx * TILE + x] for y in range(TILE) for x in range(TILE)
            )
            tiles.setdefault(block, []).append((tx, ty))

    # a tile is judged the way the NES fetches it: 3 colours plus transparency, so re-read the blocks
    return {
        "pixels": pixels,
        "roles": roles,
        "cell_names": cell_names,
        "palettes": palettes,
        "used": used,
        "tiles": tiles,
        "palette_of_area": palette_of_area,
        "party_floor": party_floor,
    }


def write_png(pixels: list, path: str) -> None:
    image = Image.new("RGB", (W, H))
    image.putdata([tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5)) for row in pixels for colour in row])
    image.save(path)


def write_frame(pixels: list, path: str, backdrop_hex: str) -> None:
    """The strip inside a 256x240 frame, so tools\\nes_composite_check.py can judge the whole picture.

    The battle screen puts this strip at the top and draws the command window below it; the rest of the
    frame here is the shared backdrop, which is what the window sits on.
    """
    image = Image.new("RGB", (256, 240), tuple(int(backdrop_hex[i:i + 2], 16) for i in (1, 3, 5)))
    strip = Image.new("RGB", (W, H))
    strip.putdata([tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5)) for row in pixels for colour in row])
    image.paste(strip, (0, 0))
    image.save(path)


def scene_json(scene: dict, built: dict, entries: list, png_name: str, palette_file: str) -> dict:
    tile_list = built["tiles"]
    meta = {
        "format": 1,
        "kind": "battle_background",
        "name": "bg_battle_%s" % scene["name"],
        "title": scene["title"],
        "png": png_name,
        "width": W,
        "height": H,
        "tile_size": TILE,
        "attribute_area": CELL,
        "grid": {"columns": COLS, "rows": ROWS},
        "frame": {"width": 256, "height": 240, "strip_y": 0, "note": "strip sits at the top of the 256x240 frame; the command window draws below it on black"},
        "palette_source": "data/nes_palette.json",
        "scene_palette": palette_file,
        "backdrop": {"index": BACKDROP, "hex": entries[BACKDROP]},
        "background_palettes": [
            {
                "name": name,
                "colours": numbers,
                "hex": [entries[index] for index in numbers],
                "areas": sum(
                    1
                    for row in built["palette_of_area"]
                    for cell in row
                    if cell == name
                ),
            }
            for name, numbers in scene["background"]
        ],
        "sprite_palettes": [
            {"name": name, "colours": numbers, "hex": [entries[index] for index in numbers]}
            for name, numbers in scene["sprites"]
        ],
        "unique_tiles": len(tile_list),
        "unique_tile_budget": 128,
        "tiles_used_once": sum(1 for spots in tile_list.values() if len(spots) == 1),
        "tile_reuse": {
            "max_times_a_tile_repeats": max(len(spots) for spots in tile_list.values()),
            "total_tile_slots": (H // TILE) * (W // TILE),
        },
        "colours_used": sorted(built["used"]),
        "colour_count": len(built["used"]),
        "colour_budget": 25,
        "attributes": {
            "rule": "one background palette per 16x16 area, 3 colours plus the shared backdrop",
            "grid": [
                [cell for cell in row] for row in built["cell_names"]
            ],
        },
        "dithering": "2x2 checker only, at palette band edges; no gradients, no rescaling, no anti aliasing",
        "generator": "tools/art/make_battle_bg.py",
        "notes": scene["notes"],
    }
    if built["party_floor"]:
        # Named in the sidecar rather than only in the pixels: the block's floor is a decision, and a
        # reader of this file should not have to diff the strip to learn what the right hand column does.
        reason = (
            "the four party bodies are the light entry of each hero triple and clear RULE 0 point 2 on "
            "the backdrop and not on this strip's mixed floor; PALETTE-RULINGS-2026-10-25.md section 7.4 "
            "point 2, card t_d64eb2a9"
        )
        # A strip that was scoped out of that card says so in its own record, so this file names the card that
        # actually ruled ITS floor rather than only the one that ruled the first two (card t_12c9b18f).
        if scene.get("party_floor_ruling"):
            reason = "%s; %s" % (reason, scene["party_floor_ruling"])
        meta["party_floor"] = {
            "role": "3 (the shared backdrop)",
            "hex": entries[BACKDROP],
            "source": "data/ui_layouts.json, the battle screen's sprites with role party",
            "rects": built["party_floor"]["rects"],
            "pixels": built["party_floor"]["pixels"],
            "reason": reason,
        }
    return meta


def scene_palette_json(scene: dict, entries: list) -> dict:
    rule = (
        "NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, "
        "4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is a "
        "data/nes_palette.json entry number"
    )
    return {
        "format": 1,
        "kind": "scene_palette",
        "scene": "battle_%s" % scene["name"],
        "backdrop": BACKDROP,
        "rule": rule,
        "notes": [
            "written by tools/art/make_battle_bg.py for the BG-BATTLE card (t_1c5a8599); no scene_battle_*.json "
            "existed before this card, so this file defines the set in the format scene_ship.json uses",
            "backdrop $0F black is the shared backdrop of all four battle strips",
            "background palettes cover the 16x7 attribute cells of the strip, one palette per cell",
        ] + scene["notes"] + [
            "sprite palettes are declared for the battle cast the scene draws; the strip itself draws no sprites",
        ],
        "background": [
            {"name": name, "colours": numbers, "hex": [entries[index] for index in numbers]}
            for name, numbers in scene["background"]
        ],
        "sprites": [
            {"name": name, "colours": numbers, "hex": [entries[index] for index in numbers]}
            for name, numbers in scene["sprites"]
        ],
    }


# The audit rows a scene palette file carries beside its palettes: a cast decision and the row that measures it.
# tools/scene_palette_set.py reads the same key out of the same files (JUDGED_KEY there), which is why this script
# must not drop it: cards t_4f18c0ac and t_0949bd4e wrote rows into files this generator owns.
JUDGED_KEY = "judged"


def read_existing_scene_palette(palette_file: str, scene_name: str):
    """The scene palette already at `palette_file`, or None when there is none.

    Refuses rather than guesses: the file is about to be replaced whole, so a file that is not a scene palette
    for THIS scene is not this script's to overwrite.
    """
    if not os.path.isfile(palette_file):
        return None
    with open(palette_file, "r", encoding="utf-8-sig") as handle:
        try:
            existing = json.load(handle)
        except ValueError as error:
            raise SystemExit(
                "%s is not readable JSON (%s): refusing to regenerate a scene palette over it"
                % (palette_file, error)
            )
    if not isinstance(existing, dict):
        raise SystemExit(
            "%s holds a %s, not a scene palette object: refusing to regenerate over it"
            % (palette_file, type(existing).__name__)
        )
    expected = "battle_%s" % scene_name
    if existing.get("kind") != "scene_palette" or existing.get("scene") != expected:
        raise SystemExit(
            "%s is not a scene palette for %s (kind %r, scene %r): refusing to regenerate over it"
            % (palette_file, expected, existing.get("kind"), existing.get("scene"))
        )
    return existing


def carry_judged(payload: dict, existing: dict) -> dict:
    """`payload` plus the `judged` list `existing` carries, put back in the position that file keeps it in.

    Only that key is carried. Every palette, note and hex stays derived from this script, so the file keeps one
    owner for its numbers and the hand written rows keep their own content untouched.
    """
    if JUDGED_KEY not in existing:
        return payload
    keys = list(existing.keys())
    anchor = None
    for key in reversed(keys[:keys.index(JUDGED_KEY)]):
        if key in payload:
            anchor = key
            break
    out = {}
    for key, value in payload.items():
        out[key] = value
        if key == anchor:
            out[JUDGED_KEY] = existing[JUDGED_KEY]
    if anchor is None:
        out[JUDGED_KEY] = existing[JUDGED_KEY]
    return out


def write_scene_palette(root: str, scene: dict, entries: list) -> tuple:
    """Write data/palettes/scene_battle_<name>.json whole, carrying its `judged` rows forward (card t_5802ecdb).

    Returns (path, rows kept). A fresh tree has no file, so it keeps no rows and the file is written without a
    `judged` key at all.
    """
    palette_dir = os.path.join(root, "data", "palettes")
    os.makedirs(palette_dir, exist_ok=True)
    palette_file = os.path.join(palette_dir, "scene_battle_%s.json" % scene["name"])
    payload = scene_palette_json(scene, entries)
    existing = read_existing_scene_palette(palette_file, scene["name"])
    kept = 0
    if existing is not None:
        payload = carry_judged(payload, existing)
        kept = len(payload.get(JUDGED_KEY, []))
    with open(palette_file, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return palette_file, kept


def write_preview(images: list, path: str) -> tuple:
    gap = 8
    width = COLS * CELL
    height = ROWS * CELL
    sheet = Image.new("RGB", (width * 2 + gap, height * 2 + gap), (0, 0, 0))
    for index, image in enumerate(images):
        x = (index % 2) * (width + gap)
        y = (index // 2) * (height + gap)
        sheet.paste(image, (x, y))
    big = sheet.resize((sheet.width * SCALE, sheet.height * SCALE), Image.NEAREST)
    big.save(path)
    return sheet.size, big.size


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Draw the four NES battle background strips.")
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    parser.add_argument("--preview", default=None)
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    entries, palette_path = load_palette(root)
    party_rects, party_path = load_party_block(root)
    out_dir = os.path.join(root, "game", "sprites_src", "bg")
    palette_dir = os.path.join(root, "data", "palettes")
    preview_path = args.preview or os.path.join(root, "output", "bg_battle_preview.png")
    for directory in (out_dir, palette_dir, os.path.dirname(preview_path)):
        os.makedirs(directory, exist_ok=True)

    images = []
    print("palette: %s (64 entries, backdrop $%02X %s)" % (os.path.relpath(palette_path, root), BACKDROP, entries[BACKDROP]))
    print(
        "party block: %s, %d slot(s) %s"
        % (
            os.path.relpath(party_path, root),
            len(party_rects),
            " ".join("%dx%d at %d,%d" % (w, h, x, y) for x, y, w, h in party_rects),
        )
    )
    for scene in SCENES:
        built = build_scene(scene, entries, party_rects)
        png_path = os.path.join(out_dir, "bg_battle_%s.png" % scene["name"])
        write_png(built["pixels"], png_path)
        images.append(Image.open(png_path).convert("RGB"))
        frame_path = os.path.join(os.path.dirname(preview_path), "bg_battle_%s_frame.png" % scene["name"])
        write_frame(built["pixels"], frame_path, entries[BACKDROP])

        palette_file, judged_kept = write_scene_palette(root, scene, entries)

        meta = scene_json(scene, built, entries, os.path.basename(png_path), os.path.relpath(palette_file, root).replace(os.sep, "/"))
        with open(os.path.join(out_dir, "bg_battle_%s.json" % scene["name"]), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(meta, handle, indent=2)
            handle.write("\n")

        print(
            "%s: %dx%d, unique tiles %d/128, colours %d/25, cells %d types%s%s"
            % (
                scene["name"],
                W,
                H,
                len(built["tiles"]),
                len(built["used"]),
                len(scene["cells"]),
                ""
                if not built["party_floor"]
                else ", party floor %d px on $%02X" % (built["party_floor"]["pixels"], BACKDROP),
                ""
                if not judged_kept
                else ", judged rows kept %d" % judged_kept,
            )
        )

    sheet_size, big_size = write_preview(images, preview_path)
    print("preview: %s %dx%d at %dx (%dx%d)" % (os.path.relpath(preview_path, root), sheet_size[0], sheet_size[1], SCALE, big_size[0], big_size[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
