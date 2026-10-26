#!/usr/bin/env python3
"""make_characters_v2.py: redraw the overworld cast as 16x16 hand authored NES sprites.

Card SPRITE-REDRAW-1 (Nayil, 2026-10-22): the v1 overworld sprites read as "janky and cutesy" and the
sailor, measured on disk, was TWO colours (white #fcfcfc and navy #0000bc, 624 and 200 opaque pixels, no
ink and no skin): a white blob. This file replaces the overworld figures with hand drawn pixel grids and
follows knowledge/ART-BIBLE.md and knowledge/CHARACTER-BIBLE.md REVISION 2.

Why the palette structure changed
---------------------------------
Hardware (ART-BIBLE section 1): one 8x8 sprite tile carries 3 opaque colours plus transparency. A 16x16
figure is four 8x8 tiles, two bands of two. So a figure has room for exactly three colours per band, and a
real NES figure spends them the way FF1, Dragon Quest and Mother do:

    head band (rows 0 to 7):  ink, skin, hair
    body band (rows 8 to 15): ink, cloth tone A, cloth tone B

Ink is not decoration. It is the silhouette, the eye, the mouth, the line between arm and torso, the belt,
the gap between the legs and the boot. Those interior ink lines are what makes a 3 colour sprite read as a
person instead of a blob, and they cost nothing because ink is already one of the three.

v1 instead let a solver RECOLOUR any tile that overflowed 3 colours ("nearest kept colour"), which quietly
flattened the figure: that is where the blob came from. v2 refuses: an overflowing tile raises, so the art
has to be drawn legal in the first place.

Geometry (the "janky and cutesy" fix)
-------------------------------------
- Head 6 px wide (cols 5 to 10), 7 rows tall, over a neck at rows 7, shoulders 8 px wide (cols 4 to 11),
  so the shoulders are wider than the head. v1 drew an 8 px head on an 8 px torso: a snowman.
- Torso 5 rows, legs 2 rows plus a boot row, two 2 px legs with a 2 px ink gap.
- Both walk frames are drawn (not just a shifted copy), mirrored for the left facing pair.

Views: down (face), up (back of the head, no face), right (profile) and left = right mirrored, 2 frames each
= 8 frames in one 128x16 strip, the frame order tools/sync_art.py and pp_world_sheet_frame already expect
(down 0, down 1, up 0, up 1, right 0, right 1, left 0, left 1).

Reference rule (PLAN-V2 section 0): nothing was traced, ripped or copied. The proportions and the palette
split above are described in words and numbers from ART-BIBLE.md.

Usage:
    python tools/art/make_characters_v2.py             # build sheets, sheet, frames
    python tools/art/make_characters_v2.py --dump      # print every frame as text
    python tools/art/make_characters_v2.py --audit     # build, then print the per tile colour audit only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import pressstart2p_font  # noqa: E402  (beside this file, SIL OFL, for the contact sheet labels)
from make_characters import Grid  # noqa: E402  (the same grid type and outline pass as v1)

TILE = 8
OW_W, OW_H = 16, 16
OW_FPS = 6.0

# ----------------------------------------------------------------------------------------------------------------
# NES colours, all outputs of the 2C02 (data/nes_palette.json is the judge).
# ----------------------------------------------------------------------------------------------------------------
INK = "#000000"
SKIN = "#f0d0b0"
BLOND = "#f8d878"
GINGER = "#e45c10"
WHITE = "#fcfcfc"
NAVY = "#0000bc"
BLUE = "#0058f8"
SKY = "#3cbcfc"
GREY = "#7c7c7c"
GREY_L = "#bcbcbc"
GOLD = "#f8b800"
PALE = "#fcfcfc"
# Card t_980388cf: the light blue of deck_night sp3, so Zander's sheet can be one sprite palette.
SKY_L = "#a4e4fc"
BROWN_D = "#881400"
ORANGE = "#e45c10"
BLUE_D = "#0000fc"
BLUE_M = "#0078f8"

# ----------------------------------------------------------------------------------------------------------------
# The grids. Codes: k ink, s skin, h hair, a cloth tone A, b cloth tone B, . transparent.
#
# Reading the numbers: cols 0 to 15, rows 0 to 15. The head is cols 5 to 10 on rows 0 to 6, the neck is rows 7,
# the shoulders are cols 4 to 11 on row 8, the arms are cols 3 and 12, the two legs are cols 5 to 6 and 9 to 10.
# ----------------------------------------------------------------------------------------------------------------
DOWN = [
    ".....hhhhhh.....",
    "....hhhhhhhh....",
    "....hssssssh....",
    "....hskssksh....",
    "....hssssssh....",
    ".....ssssss.....",
    "......ssss......",
    ".......ss.......",
    "....aaaaaaaa....",
    "...aaaaaaaaaa...",
    "...aaaaaaaaaa...",
    "...aaaaaaaaaa...",
    "....aaaaaaaa....",
]
DOWN_LEGS_STAND = [
    ".....aa..aa.....",
    ".....aa..aa.....",
    "....kkk..kkk....",
]
DOWN_LEGS_WALK = [
    ".....aa..aa.....",
    "....aa....aa....",
    "...kkk....kkk...",
]

UP = [
    ".....hhhhhh.....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    ".....hhhhhh.....",
    ".....hhhhhh.....",
    ".......ss.......",
    "....aaaaaaaa....",
    "...aaaaaaaaaa...",
    "...aaaaaaaaaa...",
    "...aaaaaaaaaa...",
    "....aaaaaaaa....",
]
UP_LEGS_STAND = DOWN_LEGS_STAND
UP_LEGS_WALK = DOWN_LEGS_WALK

# Profile: facing right. The face occupies cols 7 to 10, the back of the head cols 4 to 6, so the nose side is
# the leading edge and the figure reads as a profile at 3x. Body cols 4 to 9, arm on the near side col 9.
RIGHT = [
    ".....hhhhh......",
    "....hhhhhhh.....",
    "....hhhssss.....",
    "....hhhskss.....",
    "....hhhssss.....",
    ".....hhsss......",
    ".....hsss.......",
    "......sss.......",
    ".....aaaaaa.....",
    "....aaaaaaa.....",
    "....aaaaaaa.....",
    "....aaaaaaa.....",
    ".....aaaaa......",
]
RIGHT_LEGS_STAND = [
    ".....aa.aa......",
    ".....aa.aa......",
    "....kkk.kkk.....",
]
RIGHT_LEGS_WALK = [
    "......aaaa......",
    ".....aa.aa......",
    "....kkk.kkk.....",
]


# ----------------------------------------------------------------------------------------------------------------
# The cast. palette: the five codes. decor: the named details drawn over the base body.
# ----------------------------------------------------------------------------------------------------------------
def cast():
    """Sailor and Percy first: the card's order, and the sailor is the sheet the ship room draws."""
    return [
        {
            "name": "sailor",
            "label": "SAILOR",
            # Card t_bd5cfad5 (sailor_ow_v2, eye round 8): the sheet spent four entries in every cell
            # (ink, white, navy, skin) and the four 8x8 tiles of one 16x16 cell share ONE sprite palette
            # of three, so the sailor claimed two of the four palettes on a scanline. Fixed palette
            # first, the way Percy's, Konrad's and Zander's were: the three entries are
            # data/palettes/scene_battle_deck_night.json sp2 {2, 18, 48} = $02 #0000bc, $12 #0058f8,
            # $30 #fcfcfc, which is also ship sp1, so the sheet is legal on both grounds the crew stands
            # on. $30 white is row 3 and carries the jumper, the cap crown and the face, which clears the
            # deck's $0F backdrop by three rows; $02 navy is the outline, the square collar, the cuffs and
            # the belt; $12 blue is the trousers and the shade plane. Skin is the entry this costs, the
            # way Konrad's grey and Zander's blond were, and it is posted as Q5 on the queue row.
            # 2026-10-24 (card t_cc0c5bd5, ruling knowledge/PALETTE-RULINGS-2026-10-24.md): the sentence above
            # is the record of the state it was written in and is not overwritten. Re-measured after the deck's
            # four sprite palettes were re-solved for the fight cast: deck sp2 is now {7, 23, 54} = $07 $17 $36,
            # so these three entries are NOT carried by battle_deck_night any more. In the twelve sets
            # {$02,$12,$30} now sits at ship sp1 and at sp3 of southampton, westminster and winchester (the same
            # three entries, a different slot), and in no battle strip. The sailor walks the ship, so the sheet
            # stays legal on the ground it is drawn on and this comment changes no pixel of it.
            "palette": {"k": NAVY, "s": WHITE, "h": NAVY, "a": WHITE, "b": BLUE},
            "decor": ["cap", "collar_flap", "cuffs", "belt", "trousers"],
        },
        {
            "name": "percy",
            "label": "PERCY",
            # RULE 0, palette first (sprite_percy_ow_v2): the finished frame has to fit ONE of the deck's four
            # sprite palettes, not five loose colours (palette_synergy R6/R7 failed 4 of 4 pairs at 08:36).
            # $02 navy, $12 blue, $30 white is data/scene_palettes.json battle_deck_night sp2, and it is also
            # ship sp1, so the same sheet is legal on both grounds the overworld cast stands on. Navy is ink,
            # hair and the trident socket; white is face and shirt (the largest fill, which clears the deck by
            # three luminance rows); blue is the rank slide and the shade plane. Gold is not in either palette.
            # 2026-10-24 (card t_cc0c5bd5): the sentence above is kept as written. Re-measured after the deck's
            # four sprite palettes were re-solved for the fight cast, deck sp2 is {7, 23, 54} = $07 $17 $36, so
            # {$02,$12,$30} is no longer a deck palette: it is ship sp1 and sp3 of the three towns. Percy stands
            # on the ship, which is the ground this sheet is built to, so he is legal where he is drawn and stays
            # off the deck strip. No pixel of the sheet changes.
            "palette": {"k": NAVY, "s": WHITE, "h": NAVY, "a": WHITE, "b": BLUE},
            "decor": ["beard", "stocky", "rank_stripes", "trident"],
        },
        {
            "name": "konrad",
            "label": "KONRAD",
            # Card t_980388cf (konrad_ow_v2, eye round 8): the sheet spent five entries (ink, skin, blond,
            # grey, light grey), and on hardware the four 8x8 tiles of one 16x16 cell share ONE sprite
            # palette of three, so Konrad claimed two of the four palettes on a scanline. Fixed palette
            # first, the way Percy's was: the three entries are data/palettes/scene_battle_deck_night.json
            # sp1 {7, 23, 40} = $07 #881400, $17 #e45c10, $28 #f8b800, which is the same sp1 in all four
            # battle strips and in the three towns, so the same sheet is legal on both kinds of ground.
            # $28 gold is row 2 and is the body, which is what clears the deck's $0F backdrop by two rows
            # (palette_synergy body_ground needs the body two luminance rows above the ground); $07 is the
            # outline, the hair and the seams; $17 is the lapel and collar accent. Konrad is grey and
            # amber in RULE 0 point 3 and no grey sprite palette in the project has a body above row 1
            # (deck sp0's lightest, $10, is row 1), so the amber half carries the figure and the grey is
            # posted to gamedev as Q2 on the row.
            # 2026-10-24 (card t_cc0c5bd5): the record above is kept. Re-measured after the deck's four sprite
            # palettes were re-solved for the fight cast, deck sp1 is now {2, 15, 48} = $02 $0F $30, so
            # {7, 23, 40} is no longer on the deck. It is still sp1 of the other three battle strips
            # (battle_corridor, battle_quay_dusk, battle_wardroom) and of the three towns (southampton,
            # westminster, winchester), which is where Konrad walks, so the sheet is legal on every ground he is
            # drawn on. No pixel of the sheet changes.
            "palette": {"k": BROWN_D, "s": GOLD, "h": BROWN_D, "a": GOLD, "b": ORANGE},
            "decor": ["long_hair", "beard", "lapels"],
        },
        {
            "name": "zander",
            "label": "ZANDER",
            # Card t_980388cf (zander_ow_v2): same defect and same fix. The sheet spent ink, skin, blond,
            # blue and sky, five entries in every cell, so the player cost two sprite palettes to draw.
            # The three entries are scene_battle_deck_night.json sp3 {1, 17, 49} = $01 #0000fc,
            # $11 #0078f8, $31 #a4e4fc, which is the deck's light blue palette and the only one in the
            # project that carries Zander's light blue (RULE 0 point 3). $31 pale blue is row 3 and is
            # the body and the face, the same trick Percy's white plays; $01 is the outline and the messy
            # hair; $11 is the bomber's zip and collar. His blond is one of the two entries this costs,
            # posted with Konrad's as Q2 on the row.
            # 2026-10-24 (card t_cc0c5bd5): the record above is kept, and this is the sharp end of the ruling.
            # The deck's sp3 was re-solved to {8, 39, 40} = $08 $27 $28, so {1, 17, 49} is carried by NO ground
            # in the twelve sets any more: measured over data/palettes/scene_*.json on 2026-10-24, no sprite
            # palette holds all three of $01 $11 $31. The deck is the battle strip and draws its fight cast
            # (zander_battle.png), so Zander's walking triple is bought back on a ground he walks on, not here.
            # Written down rather than dropped: the sheet keeps its three entries and no pixel changes.
            "palette": {"k": BLUE_D, "s": SKY_L, "h": BLUE_D, "a": SKY_L, "b": BLUE_M},
            "decor": ["spiky_hair", "bomber"],
        },
        {
            "name": "hadrian",
            "label": "HADRIAN",
            # Card t_bd32a72e (hadrian_ow_v2): the shipped sheet spent ink as the suit AND as the outline,
            # so 1010 of its 1186 opaque pixels were one entry (#000000, 85.2 percent) and the walk read as a
            # black mass. ART-BIBLE RULE 0 point 3 asks a sprite for 1 dark outline, 1 mid body and 1 accent,
            # so grey moves from the accent to the mid body: ink is the outline, the seams and the sleek hair;
            # grey $00 is the suit; pale $30 is the face and the lit rim. The three entries are the ones the
            # shipped sheet already spent, so this redraw adds no colour and takes no palette decision.
            # 2026-10-25 (card t_454c1876, ruling knowledge/PALETTE-RULINGS-2026-10-25.md section 20): the record
            # above is kept as written and the suit moves from grey $00 to pale $30. Measured, not chosen: the
            # tool measures a frame's body as its largest fill that is not the outline, and a body of $00 grey
            # clears NO ground the party walks on. Against the towns' street $00 #7c7c7c it is `invisible`
            # (identical) and against a black $0F joint it is `same_hue_row` (grey on grey, both row 0); every
            # other row 0 entry is under 3:1 from $00 as well, so no dark street can carry a row 0 grey body.
            # With the suit pale, $30 is the largest fill in all eight frames (24 + 40 pixels in the two frames
            # where the arms cover the shirt) and the body reads 3 luminance rows above both street entries.
            # Grey is not spent and not dropped, it changes job: it is the shaded rim the "rim" part already
            # draws on the shoulders and sleeves (8 pixels), so the sheet still spends all three of sp0's
            # entries, $00 $0F $30, and RULE 0 point 3 still gets an outline, a body and a third tone. A pale
            # suit with a mid grey edge is also the reading the rim was written for: it used to light a black
            # suit's edge, and now it shades a white one's.
            "palette": {"k": INK, "s": PALE, "h": INK, "a": PALE, "b": GREY},
            "decor": ["sleek_hair", "rim", "bident"],
        },
    ]


def base_grid(view, walk):
    """The shared 16x16 body: head band, neck, torso, then the leg pair of the view and frame."""
    rows, legs = {
        "down": (DOWN, DOWN_LEGS_WALK if walk else DOWN_LEGS_STAND),
        "up": (UP, UP_LEGS_WALK if walk else UP_LEGS_STAND),
        "right": (RIGHT, RIGHT_LEGS_WALK if walk else RIGHT_LEGS_STAND),
    }[view]
    grid = Grid(OW_W, OW_H)
    for y, row in enumerate(list(rows) + list(legs)):
        grid.text(y, row)
    return grid


def decorate(spec, grid, view, walk):
    parts = spec["decor"]
    back = view == "up"
    side = view == "right"

    if "cap" in parts:
        # A sailor cap: white crown over the hair band (1 px wider than the head), an ink band, and the cap
        # sides take the three hair columns, so the head band spends exactly ink, skin and cap rather than
        # four colours. A cap covers the hair; that is what makes it read as a cap and not a hat on hair.
        grid.text(0, ".....aaaaaa.....")
        grid.text(1, "....aaaaaaaa....")
        grid.text(2, "....akkkkkka....")
        for y in range(3, 7):
            for x in range(OW_W):
                if grid.get(x, y) == "h":
                    grid.put(x, y, "a")
        if back:
            grid.text(4, "....aaaaaaaa....")
            grid.text(5, ".....aaaaaa.....")
    if "beard" in parts:
        if back:
            pass
        elif side:
            grid.text(5, ".....hhsss......")
            grid.text(6, ".....hhhh.......")
        else:
            grid.text(5, ".....hhhhhh.....")
            grid.text(6, "......hhhh......")
    if "long_hair" in parts:
        # Past the jaw to the shoulders. Cols 4 and 11 only, so the face stays 4 px wide and readable.
        for y in range(5, 8):
            grid.put(4, y, "h")
            grid.put(11, y, "h")
        if back:
            grid.text(7, ".......hh.......")
    if "spiky_hair" in parts:
        if not back:
            grid.put(4, 0, "h")
            grid.put(6, 0, "h")
            grid.put(9, 0, "h")
            grid.put(11, 0, "h")
            grid.put(5, 1, "h")
            grid.put(10, 1, "h")
    if "sleek_hair" in parts:
        # A low hairline and a straight side: the pale face carries the figure, the hair is pure ink.
        if not back:
            grid.text(2, "....hhhhhhhh....")
            grid.put(4, 3, "h")
            grid.put(11, 3, "h")
    if "collar_flap" in parts:
        # The navy square collar of a sailor's jumper: a band across the shoulders and a flap at the back.
        grid.text(8, "....bbbbbbbb....")
        if back:
            grid.text(9, "...bbaaaaaabb...")
            grid.text(10, "...b..aaaa..b...")
        else:
            grid.text(9, "...baaaaaaab....")
            grid.put(4, 9, "b")
            grid.put(11, 9, "b")
            grid.text(10, "......bb........")
    if "cuffs" in parts:
        for y in (10, 11):
            grid.put(3, y, "b")
            grid.put(12, y, "b")
    if "belt" in parts:
        grid.text(12, "....bbbbbbbb....")
    if "trousers" in parts:
        for y in (13, 14):
            for x in (5, 6, 9, 10):
                if grid.get(x, y) == "a":
                    grid.put(x, y, "b")
        if walk:
            for x in (4, 11):
                if grid.get(x, 14) == "a":
                    grid.put(x, 14, "b")
    if "stocky" in parts:
        # Percy is the broad one: one column wider each side on rows 9 to 11, and a wider waist.
        for y in (9, 10, 11):
            grid.put(2, y, "a")
            grid.put(13, y, "a")
        grid.text(12, "...aaaaaaaaaa...")
    if "rank_stripes" in parts:
        # Two gold stripes on the outer sleeve: the Royal Navy lieutenant's rank, visible at 3x.
        for y in (9, 10):
            grid.put(2, y, "b")
            grid.put(13, y, "b")
    if "trident" in parts:
        # Three prongs on top of the shaft, the eye's rank 2 fix on the 2026-10-22 sheet ("Percy holds a
        # featureless yellow cane instead of a trident"). Everything is inside the two right hand tiles: the
        # head band tile (cols 8 to 15, rows 0 to 7) spends navy and white only, the body band tile spends
        # navy, white and blue, so the trident costs no fourth colour. The prongs are white because white is
        # the one colour in the frame that clears the deck (3.00 : 1) and the night road (8.74 : 1); the
        # socket and the grip are navy so the weapon separates from the white sleeve it passes.
        # The head of the trident stands above the right shoulder, in the three columns and three rows that
        # are empty there, and the shaft runs down col 14 from row 6 to row 14. Two attempts before this one
        # failed for a measured reason: a 1 px head inside the shoulder line, and a navy shaft on the body's
        # own ink edge, both read as "no weapon" at 12x. The prongs are the skin code and the socket the ink
        # code because those two tiles have already spent their three codes.
        grid.put(13, 3, "s")
        grid.put(15, 3, "s")
        grid.put(13, 4, "s")
        grid.put(14, 4, "s")
        grid.put(15, 4, "s")
        grid.put(13, 5, "k")
        grid.put(14, 5, "k")
        grid.put(15, 5, "k")
        for y in range(6, 8):
            grid.put(14, y, "s")
        for y in range(8, 15):
            grid.put(14, y, "a")
        grid.put(13, 13, "k")
    if "bident" in parts:
        # Hadrian's weapon is the two pronged bident (CHARACTER-BIBLE: "Hadrian the BIDENT (two pronged)"),
        # drawn with Percy's trident construction so it costs no fourth colour: the prongs are the accent
        # code inside the head band tile, which has already spent ink and skin, and the shaft runs down col
        # 14 in the same accent over the grey suit. The prongs are pale because a pale prong clears the night
        # deck (3.00 : 1) and an ink one would land on the ink outline and read as no weapon at all, which
        # is the failure Percy's trident notes record. Two prongs, not three: this is the bident.
        # Two prongs, not three: this is the bident. The prongs take the skin code and the socket the ink
        # code for the same reason Percy's do: the head band tile has already spent exactly those three
        # codes, and make_characters_v2 refuses an overflow rather than recolouring one.
        grid.put(13, 3, "s")
        grid.put(15, 3, "s")
        grid.put(13, 4, "s")
        grid.put(15, 4, "s")
        grid.put(14, 4, "k")
        for y in range(5, 8):
            grid.put(14, y, "s")
        for y in range(8, 15):
            grid.put(14, y, "b")
        grid.put(13, 13, "k")
    if "lapels" in parts:
        # Open blazer: two lit lapel columns, the dark shirt between them.
        for y in (8, 9, 10):
            grid.put(5, y, "k")
            grid.put(10, y, "k")
        grid.put(4, 8, "b")
        grid.put(11, 8, "b")
        grid.put(7, 9, "b")
        grid.put(8, 9, "b")
    if "bomber" in parts:
        # Oversized light blue collar and the zip line down the middle.
        grid.text(8, "....bbbbbbbb....")
        for y in range(9, 12):
            grid.put(7, y, "b")
    if "rim" in parts:
        # A black suit needs its edge lit or it is a hole in the frame: grey rim on shoulders and sleeves.
        grid.put(4, 8, "b")
        grid.put(11, 8, "b")
        for y in (9, 10, 11):
            grid.put(3, y, "b")
            grid.put(12, y, "b")
        grid.put(7, 9, "b")
        grid.put(8, 9, "b")
    return grid


def seams(grid):
    """Interior ink: the lines that stop a 3 colour figure reading as a blob.

    SPRITE-CRAFT section 8.5 tests the body block for at least 8 dark pixels that are NOT on the outer edge,
    because an edge is already dark from the outline and tells the eye nothing. These two lines are the
    collar knot (row 9) and the jumper hem or jacket waist (row 11); they are ink, which the body band has
    already spent, so they cost no colour.
    """
    for x in (7, 8):
        if grid.get(x, 9) in ("a", "b"):
            grid.put(x, 9, "k")
    for x in (6, 7, 8, 9):
        if grid.get(x, 11) in ("a", "b"):
            grid.put(x, 11, "k")
    return grid


def frame(spec, view, walk):
    grid = base_grid(view, walk)
    decorate(spec, grid, view, walk)
    seams(grid)
    grid.outline("k")
    return grid


def sheet_frames(spec):
    """8 frames, the order sync_art.py and pp_world_sheet_frame use: down 0/1, up 0/1, right 0/1, left 0/1."""
    frames = []
    for view in ("down", "up", "right"):
        for walk in (False, True):
            frames.append(frame(spec, view, walk))
    frames.append(frames[4].mirrored())
    frames.append(frames[5].mirrored())
    return frames


# ----------------------------------------------------------------------------------------------------------------
# Measurements: the checks this card asks for, computed from the art on disk.
# ----------------------------------------------------------------------------------------------------------------
def tile_audit(grid):
    """The worst 8x8 tile of one frame: its distinct opaque colours, and the codes in it."""
    worst = (0, None, "")
    for ty in range(0, OW_H, TILE):
        for tx in range(0, OW_W, TILE):
            codes = set()
            for y in range(ty, ty + TILE):
                for x in range(tx, tx + TILE):
                    code = grid.get(x, y)
                    if code:
                        codes.add(code)
            if len(codes) > worst[0]:
                worst = (len(codes), (tx, ty), "".join(sorted(codes)))
    return worst


def band_colours(grid, y0, y1):
    codes = set()
    for y in range(y0, y1):
        for x in range(OW_W):
            code = grid.get(x, y)
            if code:
                codes.add(code)
    return codes


def image_of(frames, palette):
    sheet = Image.new("RGBA", (OW_W * len(frames), OW_H), (0, 0, 0, 0))
    for index, grid in enumerate(frames):
        sheet.alpha_composite(grid.to_image(palette), (index * OW_W, 0))
    return sheet


def colours_in(image):
    pixels = image.convert("RGBA").load()
    found = {}
    for y in range(image.height):
        for x in range(image.width):
            value = pixels[x, y]
            if value[3]:
                found[value] = found.get(value, 0) + 1
    return found


def make_frame_with_background(sprite_sheet, backdrop_path, out_dir, name):
    """One 256x240 frame: the ship's own tileset as the background, the sprite standing on the deck line.

    The mask is written beside the frame so tools/nes_composite_check.py can tell which pixels are sprites:
    without it the checker reads the figure's skin and navy as background colours and fails blocks that the
    sprite merely stands on, which is a property of the test frame, not of the art.
    """
    background = Image.open(backdrop_path).convert("RGBA")
    frame_image = Image.new("RGBA", (256, 240), (0, 0, 0, 0))
    for ty in range(0, 240, background.height):
        for tx in range(0, 256, background.width):
            frame_image.alpha_composite(background, (tx, ty))
    standing = sprite_sheet.crop((0, 0, OW_W, OW_H))
    frame_image.alpha_composite(standing, (120, 120))
    mask = Image.new("RGBA", (256, 240), (0, 0, 0, 0))
    mask.alpha_composite(Image.new("RGBA", (OW_W, OW_H), (255, 255, 255, 255)), (120, 120))
    pixels = standing.load()
    for y in range(OW_H):
        for x in range(OW_W):
            if not pixels[x, y][3]:
                mask.putpixel((120 + x, 120 + y), (0, 0, 0, 0))
    one_x = os.path.join(out_dir, name + "_1x.png")
    three_x = os.path.join(out_dir, name + "_3x.png")
    mask_p = os.path.join(out_dir, name + "_mask.png")
    bg_only = os.path.join(out_dir, "ship_background_1x.png")
    frame_image.save(one_x, "PNG")
    frame_image.resize((768, 720), Image.NEAREST).save(three_x, "PNG")
    mask.save(mask_p, "PNG")
    if not os.path.isfile(bg_only):
        # The background layer on its own: nes_composite_check counts sprite pixels as background colours
        # (the two layers have separate palette RAM on the chip), so the background rule is proved here and
        # the sprite rule is proved on the composed frame.
        clean = Image.new("RGBA", (256, 240), (0, 0, 0, 0))
        for ty in range(0, 240, background.height):
            for tx in range(0, 256, background.width):
                clean.alpha_composite(background, (tx, ty))
        clean.save(bg_only, "PNG")
    return one_x, three_x, mask_p


def contact_sheet(entries, scale, path):
    """Every frame at 4x, one row per character, on the black backdrop the game uses.

    The canvas is sized from the drawing pitch, not guessed: each row spends a 10 px label line, the 16 px
    sprite and a 14 px gap, so five rows need 8 + 5 * (10 + 16 + 14) = 208 units. The old formula left out
    the label line and cut the sheet at 162 units, which is why the eye's round 2 found HADRIAN missing
    (measured: canvas 648 px tall, about 784 needed).
    """
    rows = len(entries)
    width = 16 * scale + OW_W * 8 * scale + 16 * scale
    height = 8 * scale + rows * (10 * scale + OW_H * scale + 14 * scale)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    y = 8 * scale
    for label, image in entries:
        label_text(draw, label, 8 * scale, y, scale, (252, 252, 252))
        y += 10 * scale
        big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
        canvas.alpha_composite(big, (8 * scale, y))
        y += OW_H * scale + 14 * scale
    canvas.save(path, "PNG")
    return path


def label_text(draw, text, x, y, scale, colour):
    for index, ch in enumerate(text):
        if ch == " ":
            continue
        rows = pressstart2p_font.bitmap(ch)
        for gy, row in enumerate(rows):
            for gx, lit in enumerate(row):
                if lit != "#":
                    continue
                px = x + (index * 8 + gx) * scale
                py = y + gy * scale
                draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=colour + (255,))


# ----------------------------------------------------------------------------------------------------------------
# Build.
# ----------------------------------------------------------------------------------------------------------------
def build(root):
    palette_file = os.path.join(root, "data", "nes_palette.json")
    with open(palette_file, "r", encoding="utf-8") as handle:
        allowed = {value.strip().lower() for value in json.load(handle)["colours"]}

    out_dir = os.path.join(root, "game", "sprites_src", "chars")
    os.makedirs(out_dir, exist_ok=True)
    frames_dir = os.path.join(root, "output", "sprite_v2_frames")
    os.makedirs(frames_dir, exist_ok=True)
    bg = os.path.join(root, "game", "sprites_src", "env", "ts_ship.png")

    report = {"sprites": [], "backdrop": "ts_ship.png", "frame_size": [256, 240]}
    sheet_rows = []
    for spec in cast():
        for code, value in sorted(spec["palette"].items()):
            if value.lower() not in allowed:
                raise SystemExit("%s: code %r is %s, not a 2C02 output" % (spec["name"], code, value))
        frames = sheet_frames(spec)
        worst = 0
        worst_at = None
        for grid in frames:
            count, at, codes = tile_audit(grid)
            if count > worst:
                worst, worst_at = count, (at, codes)
            if count > 3:
                raise SystemExit("%s: an 8x8 tile carries %d opaque colours at %s (%s); a sprite tile holds 3"
                                 % (spec["name"], count, at, codes))
        sheet = image_of(frames, spec["palette"])
        name = spec["name"] + "_ow_v2"
        png = os.path.join(out_dir, name + ".png")
        sheet.save(png, "PNG")
        meta = {"name": name, "frame_w": OW_W, "frame_h": OW_H, "frames": len(frames), "fps": OW_FPS}
        with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(meta, handle, indent=2)
            handle.write("\n")

        found = colours_in(sheet)
        head_band = band_colours(frames[0], 0, 8)
        body_band = band_colours(frames[0], 8, 16)
        hexes = {}
        for code, value in spec["palette"].items():
            hexes[value] = hexes.get(value, 0) + 1
        entry = {
            "name": name,
            "sha256": hashlib.sha256(open(png, "rb").read()).hexdigest()[:16],
            "distinct_colours": len(found),
            "colours": ["#%02x%02x%02x" % (key[0], key[1], key[2]) for key, _n in
                        sorted(found.items(), key=lambda kv: -kv[1])],
            "worst_tile_colours": worst,
            "worst_tile_at": worst_at,
            "head_band_codes": "".join(sorted(head_band)),
            "body_band_codes": "".join(sorted(body_band)),
            "body_band_colour_count_excluding_ink": len([code for code in body_band if code != "k"]),
        }
        one_x, three_x, mask_p = make_frame_with_background(sheet, bg, frames_dir, name)
        entry["frame_1x"] = os.path.relpath(one_x, root)
        entry["frame_3x"] = os.path.relpath(three_x, root)
        entry["frame_mask"] = os.path.relpath(mask_p, root)
        report["sprites"].append(entry)
        sheet_rows.append((spec["label"], sheet))

    sheet_path = os.path.join(root, "output", "sprites_v2_sheet.png")
    contact_sheet(sheet_rows, 4, sheet_path)
    report["contact_sheet"] = os.path.relpath(sheet_path, root)
    with open(os.path.join(root, "output", "_sprite_v2_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report, sheet_path


def dump():
    for spec in cast():
        print("=== %s  palette %s" % (spec["name"], spec["palette"]))
        for label, grid in zip(("down 0", "down 1", "up 0", "up 1", "right 0", "right 1"), sheet_frames(spec)):
            count, at, codes = tile_audit(grid)
            print("--- %s  worst tile %d colours %s" % (label, count, at))
            for line in grid.dump():
                print("  " + line)
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Redraw the overworld cast as NES sprites (SPRITE-REDRAW-1).")
    parser.add_argument("--root", default=None)
    parser.add_argument("--dump", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else os.path.dirname(os.path.dirname(HERE))
    if args.dump:
        dump()
        return 0
    report, sheet_path = build(root)
    for entry in report["sprites"]:
        print("  %-14s %d colours  worst tile %d/3  head[%s] body[%s]  body steps ex-ink %d"
              % (entry["name"], entry["distinct_colours"], entry["worst_tile_colours"],
                 entry["head_band_codes"], entry["body_band_codes"],
                 entry["body_band_colour_count_excluding_ink"]))
    print("contact sheet 4x: " + sheet_path)
    print("frames: output/sprite_v2_frames/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
