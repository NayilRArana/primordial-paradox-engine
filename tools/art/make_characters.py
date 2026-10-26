#!/usr/bin/env python3
"""make_characters.py: draw the SPRITE-1 cast as NES sprites, from parts, from numbers in this file.

Contract: knowledge/CHARACTER-BIBLE.md (REVISION 2 overrides everything above it) and
PLAN-V2-2026-10-21.md section 0 (original work only, no copying or tracing of any game's art).

What is drawn here, and how it stays inside the chip:
- Overworld sheets are 16x16 frames, 4 directions with 2 walk frames each. The left facing frames are the
  right facing frames mirrored, so a walk cycle cannot drift between the two.
- Battle sheets are 24x32 frames, side view facing right: idle 2, attack 3, hurt 1, down 1.
- Every frame is built from named parts (skin, hair, beard, clothing layer, accessory, weapon) instead of one
  big literal, so a character is a palette plus a list of parts.
- Every colour is one of the 64 outputs of the 2C02 (data/nes_palette.json). A sprite tile may carry 3 opaque
  colours plus transparent, so after a frame is drawn, each 8x8 tile that ended up with more colours is
  resolved by a deterministic solver: it keeps ink (the silhouette) and the two most used colours and
  recolours the rest to the nearest kept one in RGB. The solver reports what it changed, per sheet.
- tools/nes_check.py is the judge, imported here so a bad sheet stops the build instead of reaching the game.

Clean room: no image, font atlas or sprite from any game is read. The only outside file read is
data/nes_palette.json, this project's own table of the chip's outputs, and assets/fonts/PressStart2P for the
contact sheet labels (SIL OFL 1.1, notice in knowledge/licences/).

Outputs (game/sprites_src/chars/, one PNG plus one JSON each):
    <name>_ow.png          128x16, 8 frames: down 0, down 1, up 0, up 1, right 0, right 1, left 0, left 1
    <name>_battle.png      168x32, 7 frames: idle 0, idle 1, attack 0, attack 1, attack 2, hurt, down
    <name>_god_battle.png  168x32, the same 7 frames with the god form weapon (Percy, Konrad, Zander, Hadrian)
Preview: output/chars_contact.png at 4x with labels, output/chars_preview_3x.png at 3x.

The four party battle sheets are drawn in ONE reserved hero triple each (card t_d5483a88, decision of record
knowledge/PALETTE-RULINGS-2026-10-25.md sections 7 to 7.6). A NES frame has four sprite palettes of three
entries plus transparent, and the four reserved hero palettes in data/scene_palettes.json "hero_palettes" ARE
a battle strip's four sprite palettes, so each party sheet is exactly three opaque colours: the ink $0F, the
hero's body entry (the LIGHT entry of the triple, because the body is what RULE 0 point 2 judges and the party
block's floor is $0F) and the hero's accent. The drawing is the reviewed battle silhouette read through three
roles instead of fourteen codes, and every inked 8x8 tile has to carry all three, so the sheet is provably one
palette rather than three colours that happen to fit one. See PARTY_TRIPLES and party_battle_grid().

Provenance (card t_d5483a88): studied this repository's own sheets and palettes; copied expression: none.

Determinism: no clock, no randomness, no dict iteration order dependence (every set is sorted before use),
PNG carries no timestamp, JSON is written with LF endings. Run twice, the sha256 of every output is equal.

Usage:
    python tools/art/make_characters.py
    python tools/art/make_characters.py --root <repo> --dump    # --dump prints frames as text
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

import pressstart2p_font  # noqa: E402  (sits beside this file)

TILE = 8
OW_W, OW_H = 16, 16
BATTLE_W, BATTLE_H = 24, 32
OW_FPS = 6.0
BATTLE_FPS = 8.0

# ----------------------------------------------------------------------------------------------------------------
# Palette. Every value is an output of the 2C02; load_palette() below refuses to draw with anything else.
# ----------------------------------------------------------------------------------------------------------------
INK = "#000000"        # the silhouette line, and every dark shade that has no darker tone in the 55 colours
BLACK = "#000000"
GREY = "#7c7c7c"       # charcoal and steel mid tone
GREY_D = "#787878"
GREY_L = "#bcbcbc"     # pale skin shadow, steel highlight, white and grey hair streak
WHITE = "#fcfcfc"
OFFWHITE = "#f8f8f8"
SKIN = "#f0d0b0"       # light skin
SKIN_S = "#fca044"     # skin shadow
SKIN_D = "#e45c10"     # deep shadow and ginger hair
PALE = "#fcfcfc"       # Hadrian, who has not seen sunlight
BLOND_L = "#fce0a8"    # hair shine and the thunderbolt core
BLOND = "#f8d878"
BLOND_D = "#ac7c00"    # Konrad and Percy beard, dark blond
HAIR_D = "#503000"     # dark brown hair shadow
GINGER_D = "#881400"   # Percy beard and ginger shadow
BLUE_L = "#3cbcfc"     # Zander's light blue bomber
SKY = "#a4e4fc"        # its lit edge
BLUE = "#0078f8"
NAVY = "#0000bc"       # Royal Navy jacket, sailor trim
NAVY_L = "#0058f8"     # its lit edge
GOLD = "#f8b800"       # Percy's sleeve stripes
TEAL = "#00e8d8"       # sea aura and spray
TEAL_D = "#008888"
PURPLE = "#6844fc"     # Hadrian's gems
PURPLE_L = "#9878f8"
PINK = "#f8b8f8"       # the gem sparkle pixel
STEEL = "#bcbcbc"      # blades
STEEL_W = "#fcfcfc"    # blade glint

# ----------------------------------------------------------------------------------------------------------------
# Overworld templates. One character is 16 rows of 16 columns. Codes:
#   .  transparent     k  ink (outline, eye, boot)
#   s  skin            S  skin shadow
#   h  hair            H  hair shine     j  beard or dark hair
#   c  cloth           C  cloth light    d  cloth dark
#   w  white cloth     a  accent (gold stripe, gem, lanyard)   m  metal
# The last two rows are the walk cycle: stand puts the feet together, walk puts them apart.
# ----------------------------------------------------------------------------------------------------------------
OW_DOWN_HEAD = [
    ".....hhhhhh.....",
    "....hhhhhhhh....",
    "....hssssssh....",
    "....hssssssh....",
    "....hskssksh....",
    "....hssssssh....",
    "....hssSSssh....",
    ".....kssssk.....",
]
OW_UP_HEAD = [
    ".....hhhhhh.....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    "....hhhhhhhh....",
    ".....hhhhhh.....",
]
OW_SIDE_HEAD = [
    ".....hhhhh......",
    "....hhhhhhh.....",
    "....hhhsssss....",
    "....hhhsskss....",
    "....hhhsssss....",
    "....hhhssss.....",
    "....hhhSSSs.....",
    ".....hhssss.....",
]
OW_NECK = [
    "......ssss......",
]
OW_TORSO = [
    ".....cccccc.....",
    "....cccccccc....",
    "....cccccccc....",
    "....cccccccc....",
    "......cccc......",
]
OW_LEGS_STAND = [
    ".....cc..cc.....",
    ".....dd..dd.....",
]
OW_LEGS_WALK = [
    "....cc....cc....",
    "....dd....dd....",
]
OW_SIDE_NECK = ["......ssss......"]
OW_SIDE_TORSO = [
    ".....cccccc.....",
    ".....cccccc.....",
    ".....cccccc.....",
    ".....cccccc.....",
    "......cccc......",
]
OW_SIDE_LEGS_STAND = ["......c..c......", "......d..d......"]
OW_SIDE_LEGS_WALK = [".....c....c.....", ".....d....d....."]

# ----------------------------------------------------------------------------------------------------------------
# A pixel grid of codes. Nothing here touches PIL until to_image(); that keeps the drawing code readable and
# lets --dump show a frame as text, which is how a worker with no eyes checks a silhouette.
# ----------------------------------------------------------------------------------------------------------------
class Grid:
    __slots__ = ("w", "h", "px")

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = {}

    def put(self, x, y, code):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(int(x), int(y))] = code

    def get(self, x, y):
        return self.px.get((int(x), int(y)))

    def fill(self, x0, y0, x1, y1, code):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, code)

    def text(self, y, row, start=0):
        for i, ch in enumerate(row):
            if ch != ".":
                self.put(start + i, y, ch)

    def stroke(self, x0, y0, x1, y1, code, width=2):
        """A thick straight line: the brush a limb is drawn with."""
        steps = max(abs(x1 - x0), abs(y1 - y0))
        half = (width - 1) // 2
        for step in range(steps + 1):
            t = step / steps if steps else 0.0
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            for dy in range(-half, width - half):
                for dx in range(-half, width - half):
                    self.put(x + dx, y + dy, code)

    def overlay(self, other):
        for (x, y), code in other.px.items():
            self.put(x, y, code)

    def mirrored(self):
        out = Grid(self.w, self.h)
        for (x, y), code in self.px.items():
            out.put(self.w - 1 - x, y, code)
        return out

    def outline(self, code="k"):
        """Every empty pixel touching a drawn one becomes the silhouette line: one pass, 4 neighbours."""
        edge = []
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in self.px:
                    continue
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if (nx, ny) in self.px:
                        edge.append((x, y))
                        break
        for x, y in edge:
            self.put(x, y, code)

    def to_image(self, hexes):
        image = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        pixels = image.load()
        for (x, y), code in sorted(self.px.items()):
            value = hexes.get(code)
            if value is None:
                raise SystemExit("frame uses code %r, which the character does not define" % code)
            pixels[x, y] = (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 255)
        return image

    def dump(self):
        return ["".join(self.get(x, y) or "." for x in range(self.w)) for y in range(self.h)]


# ----------------------------------------------------------------------------------------------------------------
# Characters. Each one is a palette (code to NES colour) plus the parts it wears.
# ----------------------------------------------------------------------------------------------------------------
def character_specs():
    return [
        {
            "name": "konrad",
            "label": "KONRAD",
            "skin": SKIN,
            "skin_s": SKIN_S,
            "hair": BLOND,
            "hair_l": BLOND_L,
            "beard": BLOND_D,
            "beard_l": GREY_L,
            "cloth": BLACK,
            "cloth_l": GREY,
            "cloth_d": BLACK,
            "accent": BLUE_L,
            "ow_parts": ["long_hair", "streaks", "close_beard", "lanyard", "watch"],
            "battle": {"hair_back": 6, "beard": True, "collar": "shirt", "weapon": "sickle",
                       "weapon_in_normal": False, "gem": None},
        },
        {
            "name": "zander",
            "label": "ZANDER",
            "skin": SKIN,
            "skin_s": SKIN_S,
            "hair": BLOND,
            "hair_l": BLOND_L,
            "beard": None,
            "beard_l": None,
            "cloth": BLUE_L,
            "cloth_l": SKY,
            "cloth_d": BLUE,
            "accent": WHITE,
            "ow_parts": ["messy_hair", "bomber", "earbuds"],
            "battle": {"hair_back": 4, "beard": False, "collar": "bomber", "weapon": "bolt",
                       "weapon_in_normal": False, "gem": None},
        },
        {
            "name": "percy",
            "label": "PERCY",
            "skin": SKIN,
            "skin_s": SKIN_S,
            "hair": SKIN_D,
            "hair_l": "#f87858",
            "beard": GINGER_D,
            "beard_l": SKIN_D,
            "cloth": NAVY,
            "cloth_l": NAVY_L,
            "cloth_d": BLACK,
            "accent": GOLD,
            "ow_parts": ["stocky", "full_beard", "sleeve_stripes"],
            "battle": {"hair_back": 4, "beard": True, "collar": "navy", "weapon": "trident",
                       "weapon_in_normal": True, "gem": None, "stocky": True},
        },
        {
            "name": "hadrian",
            "label": "HADRIAN",
            "skin": PALE,
            "skin_s": GREY_L,
            "hair": BLACK,
            "hair_l": GREY,
            "beard": None,
            "beard_l": None,
            "cloth": BLACK,
            "cloth_l": GREY_D,
            "cloth_d": BLACK,
            "accent": PURPLE,
            "ow_parts": ["sleek_hair", "gems", "dark_circles"],
            "battle": {"hair_back": 5, "beard": False, "collar": "shirt", "weapon": "bident",
                       "weapon_in_normal": False, "gem": PURPLE, "helm": True},
        },
        {
            "name": "sailor",
            "label": "SAILOR",
            "skin": SKIN,
            "skin_s": SKIN_S,
            "hair": HAIR_D,
            "hair_l": GREY_D,
            "beard": None,
            "beard_l": None,
            "cloth": WHITE,
            "cloth_l": OFFWHITE,
            "cloth_d": NAVY,
            "accent": NAVY,
            "ow_parts": ["cap", "sailor_uniform"],
            "battle": {"hair_back": 3, "beard": False, "collar": "sailor", "weapon": None,
                       "weapon_in_normal": False, "gem": None},
        },
    ]


def code_map(spec):
    """The seven codes a template may use, mapped to this character's NES colours."""
    return {
        "k": INK,
        "s": spec["skin"],
        "S": spec["skin_s"],
        "h": spec["hair"],
        "H": spec["hair_l"],
        "j": spec["beard"] or spec["hair"],
        "c": spec["cloth"],
        "C": spec["cloth_l"],
        "d": spec["cloth_d"],
        "w": WHITE,
        "a": spec["accent"],
        "m": STEEL,
        "M": STEEL_W,
        "t": TEAL,
    }


# ----------------------------------------------------------------------------------------------------------------
# Overworld frames.
# ----------------------------------------------------------------------------------------------------------------
def ow_frame(spec, direction, walk):
    """One 16x16 overworld frame. direction is 'down', 'up' or 'right'; left is mirrored later."""
    grid = Grid(OW_W, OW_H)
    if direction == "down":
        head, neck, torso = OW_DOWN_HEAD, OW_NECK, OW_TORSO
        legs = OW_LEGS_WALK if walk else OW_LEGS_STAND
    elif direction == "up":
        head, neck, torso = OW_UP_HEAD, OW_NECK, OW_TORSO
        legs = OW_LEGS_WALK if walk else OW_LEGS_STAND
    else:
        head, neck, torso = OW_SIDE_HEAD, OW_SIDE_NECK, OW_SIDE_TORSO
        legs = OW_SIDE_LEGS_WALK if walk else OW_SIDE_LEGS_STAND
    rows = head + neck + torso + legs
    for y, row in enumerate(rows):
        grid.text(y, row)
    decorate_ow(spec, grid, direction, walk)
    if direction == "up":
        # A character seen from behind has no face: the eyes the down template carries are hair here.
        for x in range(OW_W):
            for y in range(0, 6):
                if grid.get(x, y) == "k":
                    grid.put(x, y, "h")
    return grid


def decorate_ow(spec, grid, direction, walk):
    parts = spec["ow_parts"]
    back = direction == "up"
    side = direction == "right"

    if "long_hair" in parts:
        # Hair past the jaw to the shoulder blades, with the grey streaks that Konrad's age shows in.
        for y in range(6, 13):
            grid.put(4, y, "h")
            grid.put(11, y, "h")
        for y in range(6, 10):
            grid.put(3, y, "h")
            grid.put(12, y, "h")
        for x, y in ((3, 7), (12, 8), (4, 11), (11, 12)):
            grid.put(x, y, "H")
    if "streaks" in parts:
        grid.put(5, 1, "H")
        grid.put(9, 2, "H")
        if back:
            grid.put(7, 4, "H")
            grid.put(9, 6, "H")
    if "messy_hair" in parts:
        # Two tufts above the skull line, one hanging over the brow.
        grid.put(5, 0, "h")
        grid.put(10, 1, "h")
        grid.put(11, 1, "h")
        grid.put(4, 2, "h")
        if not back:
            grid.put(6, 3, "h")
    if "sleek_hair" in parts:
        grid.put(4, 2, "H")
        grid.put(11, 2, "H")
        if back:
            grid.put(7, 3, "H")
            grid.put(8, 3, "H")
    if "close_beard" in parts and not back:
        grid.text(7, ".....jjjjjj.....")
        for x in (6, 7, 8, 9):
            grid.put(x, 6, "j")
            grid.put(x, 8, "j")
    if "full_beard" in parts and not back:
        grid.text(6, "....jssssssj....")
        grid.text(7, ".....jjjjjj.....")
        grid.text(8, "......jjjj......")
        grid.put(7, 6, "j")
        grid.put(8, 6, "j")
    if "dark_circles" in parts and not back:
        grid.put(5, 5, "S")
        grid.put(10, 5, "S")
    if "gems" in parts:
        grid.put(8, 10, "a")
        grid.put(4, 12, "a")
        grid.put(11, 12, "a")
        if back:
            grid.put(8, 9, "H")
    if "lanyard" in parts and not back:
        for x, y in ((7, 10), (8, 11), (8, 12)):
            grid.put(x, y, "a")
        grid.put(9, 12, "C")
    if "watch" in parts:
        grid.put(4, 12, "m")
    if "earbuds" in parts and not back:
        grid.put(3, 4, "w")
        grid.put(12, 4, "w")
        if not side:
            grid.put(3, 5, "w")
    if "bomber" in parts:
        # Oversized collar and a zip, in the lit blue.
        grid.text(9, "....CccccccC....")
        grid.put(7, 11, "C")
        grid.put(7, 12, "C")
        grid.text(13, ".....CC..CC.....")
    if "stocky" in parts:
        for y in (10, 11, 12):
            grid.text(y, "...cccccccccc...")
        grid.text(13, ".....cccccc.....")
    if "sleeve_stripes" in parts:
        for y in (11, 12):
            grid.put(3, y, "a")
            grid.put(12, y, "a")
    if "sailor_uniform" in parts:
        grid.text(9, ".....cwwwwc.....")
        grid.put(6, 11, "c")
        grid.put(9, 11, "c")
        grid.text(13, ".....cwwwwc.....")
        grid.put(4, 12, "c")
        grid.put(11, 12, "c")
    if "cap" in parts:
        grid.text(0, ".....wwwwww.....")
        grid.text(1, "....cwwwwwwc....")
        if back:
            grid.text(2, "....cwwwwwwc....")
    return grid


def ow_sheet(spec):
    frames = []
    for direction in ("down", "up", "right"):
        for walk in (False, True):
            frames.append(ow_frame(spec, direction, walk))
    right_a, right_b = frames[4], frames[5]
    frames.append(right_a.mirrored())
    frames.append(right_b.mirrored())
    return frames


# ----------------------------------------------------------------------------------------------------------------
# Battle frames: side view, facing right, 24x32, drawn from a skeleton so a pose is six numbers.
# ----------------------------------------------------------------------------------------------------------------
POSES = [
    ("idle", {"hand": (18, 21), "lean": 0, "head_dy": 0}),
    ("idle", {"hand": (18, 20), "lean": 0, "head_dy": -1}),
    ("attack", {"hand": (16, 9), "lean": -1, "head_dy": 0, "weapon_raise": True}),
    ("attack", {"hand": (22, 15), "lean": 2, "head_dy": 0, "weapon_forward": True}),
    ("attack", {"hand": (20, 20), "lean": 1, "head_dy": 0}),
    ("hurt", {"hand": (14, 17), "lean": -3, "head_dy": 1, "hurt": True}),
    ("down", None),
]
POSE_LABELS = ["idle 0", "idle 1", "attack 0", "attack 1", "attack 2", "hurt", "down"]


def battle_frame(spec, pose, god):
    if pose is None:
        grid = Grid(BATTLE_W, BATTLE_H)
        draw_down(spec, grid, god)
        return grid
    grid = Grid(BATTLE_W, BATTLE_H)
    lean = pose["lean"]
    head_dy = pose["head_dy"]
    hand = pose["hand"]
    stocky = spec["battle"].get("stocky", False)
    cloth = "c"

    # Legs first, the far one darker, so the near leg and the jacket read in front of it.
    hip_x = 11 + lean // 2
    near_foot = (15, 27)
    far_foot = (7, 27)
    if pose.get("hurt"):
        near_foot, far_foot = (16, 27), (6, 27)
    grid.stroke(hip_x - 1, 22, far_foot[0], far_foot[1], "d", 3)
    grid.fill(far_foot[0] - 1, far_foot[1] + 2, far_foot[0] + 1, BATTLE_H - 1, "k")
    grid.stroke(hip_x + 1, 22, near_foot[0], near_foot[1], cloth, 3)
    grid.fill(near_foot[0] - 1, near_foot[1] + 2, near_foot[0] + 1, BATTLE_H - 1, "k")

    # Torso: a slanted column from shoulder to hip, wider at the chest, with a waist so it is not a slab.
    top, bottom = 12, 23
    chest = 5 if stocky else 4
    for y in range(top, bottom + 1):
        t = (y - top) / (bottom - top)
        cx = round(11 + lean * (1 - t))
        half = chest if t < 0.45 else chest - 1
        grid.fill(cx - half, y, cx + half, y, cloth)
    grid.fill(11 + lean - chest, top, 11 + lean + chest - 1, top, "C")
    # Collar and shirt front.
    collar = spec["battle"]["collar"]
    cx_top = 11 + lean
    if collar == "shirt":
        grid.fill(cx_top + 1, 12, cx_top + 2, 12, "w")
        grid.fill(cx_top + 1, 13, cx_top + 2, 14, "w")
        grid.put(cx_top + 3, 15, "a")
    elif collar == "navy":
        grid.fill(cx_top + 1, 12, cx_top + 3, 12, "C")
        grid.fill(cx_top + 1, 13, cx_top + 2, 13, "w")
    elif collar == "bomber":
        grid.fill(cx_top - 2, 12, cx_top + 3, 12, "C")
        grid.fill(cx_top + 2, 13, cx_top + 3, 18, "C")
    elif collar == "sailor":
        grid.fill(cx_top - 1, 12, cx_top + 3, 12, "d")
        grid.fill(cx_top + 1, 13, cx_top + 2, 14, "w")

    # Near arm, from the shoulder to wherever the pose puts the hand, then the hand itself.
    shoulder = (11 + lean, 14)
    grid.stroke(shoulder[0], shoulder[1], hand[0], hand[1], cloth, 3)
    grid.fill(hand[0] - 1, hand[1] - 1, hand[0] + 1, hand[1] + 1, "s")

    draw_head(spec, grid, lean, head_dy, pose)

    # Weapon and god form kit go on before the outline so the outline wraps them too.
    weapon = None
    if god:
        weapon = spec["battle"]["weapon"]
    elif spec["battle"].get("weapon_in_normal"):
        weapon = spec["battle"]["weapon"]
    if god and spec["battle"].get("helm"):
        draw_helm(grid, lean, head_dy)
    grid.outline("k")
    if weapon:
        draw_weapon(spec, grid, weapon, pose, hand, god)
    # Details last: they are on the near face of the figure, so nothing may paint over them.
    draw_battle_details(spec, grid, lean, head_dy, pose, god)
    return grid


def draw_head(spec, grid, lean, head_dy, pose):
    hx = 15 + lean
    hy = 6 + head_dy
    skin = "s"
    # Skull: 9 wide by 9 tall, the face on the +x side because the figure faces right.
    grid.fill(hx - 4, hy - 3, hx + 4, hy + 4, skin)
    # Hair: a cap over the top, a fringe over the brow, and a mass down the back of the head.
    back = spec["battle"]["hair_back"]
    grid.fill(hx - 5, hy - 4, hx + 4, hy - 2, "h")
    grid.fill(hx - 5, hy - 4, hx - 1, hy + back - 3, "h")
    grid.fill(hx + 1, hy - 3, hx + 3, hy - 3, "h")
    grid.put(hx - 4, hy - 4, "H")
    grid.put(hx - 3, hy - 4, "H")
    if pose.get("hurt"):
        grid.fill(hx + 3, hy - 3, hx + 5, hy - 1, "h")
    # Nose: two pixels past the face, the only profile the 24 px width allows.
    grid.fill(hx + 5, hy, hx + 6, hy, skin)
    grid.put(hx + 5, hy + 1, "S")
    # Beard, one row lower than the jaw so the face keeps four rows to read in.
    if spec["battle"]["beard"]:
        grid.fill(hx + 1, hy + 3, hx + 5, hy + 5, "j")
        grid.fill(hx - 1, hy + 4, hx + 4, hy + 5, "j")
        if spec["beard_l"]:
            grid.put(hx + 2, hy + 4, "j")
    # Neck, kept above the shoulder row so it does not eat the jacket.
    grid.fill(hx - 1, hy + 4, hx + 2, hy + 5, "S")
    # Jaw shadow: a chin is not a flat slab of skin.
    grid.fill(hx + 1, hy + 3, hx + 4, hy + 3, "S")


def draw_helm(grid, lean, head_dy):
    hx = 15 + lean
    hy = 6 + head_dy
    # A plain dark ancient helm worn over the suit: dome, brow band, nose guard. No crest, no skull.
    grid.fill(hx - 5, hy - 5, hx + 4, hy - 2, "k")
    grid.fill(hx - 6, hy - 1, hx + 5, hy + 1, "k")
    grid.fill(hx + 2, hy, hx + 4, hy + 3, "k")
    grid.fill(hx - 5, hy - 5, hx + 3, hy - 3, "d")
    grid.put(hx - 4, hy - 4, "C")
    grid.put(hx + 1, hy - 2, "C")


def draw_weapon(spec, grid, weapon, pose, hand, god):
    hx, hy = hand

    def pole(prongs, shaft_code, prong_code, tip_code):
        """A long weapon held in the fist: the shaft leans out past the profile, the head is at the tip."""
        base = (min(BATTLE_W - 3, hx + 1), min(BATTLE_H - 1, hy + 8))
        tip = (min(BATTLE_W - 2, hx + 5), max(1, hy - 15))
        grid.stroke(base[0], base[1], tip[0], tip[1], shaft_code, 2)
        tx, ty = tip
        half = 1 if prongs == 3 else 2
        grid.fill(tx - half, ty, tx + half, ty, prong_code)
        if prongs == 3:
            xs = (tx - 1, tx, tx + 1)
        else:
            xs = (tx - 2, tx + 2)
        for x in xs:
            grid.fill(x, max(0, ty - 4), x, ty - 1, prong_code)
            grid.put(x, max(0, ty - 4), tip_code)
        return tip

    if weapon == "trident":
        tip = pole(3, "m", "M", "m")
        if god:
            # A hint of sea spray only: the bible keeps god forms to the normal outfit plus the weapon.
            for dx, dy in ((-2, 3), (3, 2), (4, -2), (-3, 6)):
                grid.put(min(BATTLE_W - 1, max(0, tip[0] + dx)),
                         min(BATTLE_H - 1, max(0, tip[1] + dy)), "t")
    elif weapon == "bident":
        tip = pole(2, "k", "k", "d")
        grid.put(tip[0], tip[1] - 1, "a")
    elif weapon == "sickle":
        # A curved blade: the arc of a circle of radius 5 above the fist, then a short handle.
        cx, cy = hx, hy - 5
        for step in range(8):
            angle = 3.14159 * (0.10 + 0.11 * step)
            x = round(cx - 5 * _cos(angle))
            y = round(cy - 5 * _sin(angle))
            grid.put(x, y, "M")
            grid.put(x + 1, y + 1, "m")
        grid.stroke(hx, hy, cx, cy, "m", 1)
    elif weapon == "bolt":
        # A zigzag, four segments, thicker than a line so it reads at 24 px.
        points = [(hx, hy - 9), (hx + 4, hy - 5), (hx - 1, hy - 2), (hx + 3, hy + 2)]
        for i in range(len(points) - 1):
            grid.stroke(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], "a", 2)
        grid.stroke(points[0][0], points[0][1], points[1][0], points[1][1], "M", 1)


def _cos(a):
    import math
    return math.cos(a)


def _sin(a):
    import math
    return math.sin(a)


def draw_battle_details(spec, grid, lean, head_dy, pose, god):
    hx = 15 + lean
    hy = 6 + head_dy
    if not pose.get("hurt"):
        grid.put(hx + 3, hy - 1, "k")   # the eye, one pixel, on the profile
        grid.put(hx + 3, hy - 2, "j")   # brow
        if not spec["battle"]["beard"]:
            grid.put(hx + 4, hy + 3, "k")   # mouth, where the beard would be
    if spec["battle"].get("gem"):
        grid.put(13 + lean, 16, "a")
        grid.put(13 + lean, 17, "a")
        grid.put(10 + lean, 19, "a")
        if god:
            grid.put(16 + lean, 15, "H")
            grid.put(9 + lean, 20, "H")
    if spec["ow_parts"] and "sleeve_stripes" in spec["ow_parts"]:
        hand = pose["hand"]
        grid.put(hand[0] - 1, hand[1] - 3, "a")
        grid.put(hand[0], hand[1] - 4, "a")
    if "earbuds" in spec["ow_parts"]:
        grid.put(hx - 4, hy, "w")
        grid.put(hx - 6, hy + 3, "w")
    if god and spec["name"] == "percy":
        grid.put(23, 4, "t")
        grid.put(2, 12, "t")
    if god and spec["name"] == "zander":
        grid.put(hx - 6, hy - 5, "M")
        grid.put(hx + 6, hy - 3, "M")
    if god and spec["name"] == "konrad":
        grid.put(3, 26, "H")


def draw_down(spec, grid, god):
    """The down pose: on the back, head to the left, feet to the right, all inside 24x32."""
    cloth = "c"
    # Torso lying: a 12 px slab.
    grid.fill(8, 24, 19, 29, cloth)
    # Head at the left end, hair behind it on the floor.
    grid.fill(2, 22, 9, 29, "s")
    grid.fill(1, 21, 7, 23, "h")
    grid.fill(6, 22, 8, 24, "h")
    # Legs to the right.
    grid.stroke(19, 26, 22, 24, cloth, 3)
    grid.stroke(19, 28, 22, 29, "d", 3)
    grid.fill(21, 22, 23, 24, "k")
    grid.fill(21, 27, 23, 29, "k")
    # Arm flung out.
    grid.stroke(12, 24, 9, 20, cloth, 3)
    grid.fill(8, 18, 10, 20, "s")
    grid.outline("k")
    grid.put(7, 25, "k")
    grid.put(6, 26, "S")
    if spec["battle"]["beard"]:
        grid.fill(6, 27, 9, 29, "j")
    if god and spec["battle"]["weapon"]:
        draw_weapon(spec, grid, spec["battle"]["weapon"], {"hand": (20, 20)}, (20, 20), god)
    if spec["battle"].get("gem"):
        grid.put(14, 27, "a")
    if god and spec["battle"].get("helm"):
        grid.fill(2, 20, 8, 22, "k")
        grid.put(4, 21, "C")
    return grid


def battle_sheet(spec, god):
    frames = []
    for _label, pose in POSES:
        frames.append(battle_frame(spec, pose, god))
    return frames


# ----------------------------------------------------------------------------------------------------------------
# The party battle sheets: one reserved hero triple each (card t_d5483a88, PALETTE-RULINGS-2026-10-25 7 to 7.6).
#
# The four triples are already written in data/scene_palettes.json "hero_palettes" with "fixed": true, and on a
# battle strip they ARE the strip's four sprite palettes, so nothing here invents a colour. The body role is the
# LIGHT entry of the triple (Percy $12, Hadrian $23, Konrad $27, Zander $21) and the ink is $0F, because the
# party block is drawn on the $0F floor of every battle strip and RULE 0 point 2 judges the body against it:
# on $0F those four read 3.75, 6.38, 10.25 and 9.79 to 1. The third entry is the accent, and the ruling's named
# cost stands: the ink $0F equals the floor, so the outline merges into it and the body carries the edge.
# ----------------------------------------------------------------------------------------------------------------
PARTY_INK = 0x0F
PARTY_TRIPLES = {
    "percy": {"body": 0x12, "accent": 0x28},
    "hadrian": {"body": 0x23, "accent": 0x03},
    "zander": {"body": 0x21, "accent": 0x31},
    "konrad": {"body": 0x27, "accent": 0x00},
}

# Card t_0b9c2faf: a character with no battle slot does not get a battle sheet written, so the retired sheet
# cannot reappear on disk every time this generator runs. The sailor is the one character this applies to: he is
# an actor who walks the ship's lower deck (pp_overworld's pp_sailor_sheet, sailor_ow_v2), the tutorial fight's
# enemy figure is game/sprites_src/enemies/navy_sailor.png drawn as background art in the battle screen's own
# 32x32 enemy slot, and the only 24x32 slots in the game are the four party slots data/ui_layouts.json names for
# the four heroes. His committed game/sprites_src/chars/sailor_battle.png is left on disk untouched, because
# deleting art and dropping an Included File is a build input change with its own rebuild; this generator simply
# stops producing it. The measurement behind the verdict is in knowledge/PALETTE-RULINGS-2026-10-25.md section 19.
BATTLE_RETIRED = {"sailor"}


def writes_battle_sheet(name):
    """Whether this character has a battle slot to stand in. False for a retired sheet (card t_0b9c2faf)."""
    return name not in BATTLE_RETIRED

# The reviewed battle drawing speaks in fourteen codes; on a party sheet each one is read as one of three roles.
# The mass of the figure is the body. The hair, the beard, the collar and the cloth highlight are the accent,
# which is what gives a two-tone figure at three entries. The ink is the silhouette and every interior line.
PARTY_ROLE = {
    "k": "k",   # ink: outline, eye, mouth, boot
    "c": "b",   # cloth: the mass of the figure
    "s": "b",   # skin
    "S": "b",   # skin shadow
    "d": "a",   # the far leg and every dark cloth: the shadow side is the accent
    "C": "a",   # cloth highlight: the lit shoulder line
    "h": "a",   # hair
    "H": "a",   # hair shine
    "j": "a",   # beard
    "w": "a",   # shirt front and collar
    "a": "a",   # the character's own accent
    "m": "a",   # weapon shaft: one solid object with its head, so the shaft reads against the body
    "M": "a",   # weapon head
    "t": "a",   # god form spray (never on a party sheet, mapped so no code is missing)
}
PARTY_CODES = ("k", "b", "a")


def party_hexes(palette, name):
    """The three colours of one party sheet, read out of data/nes_palette.json by entry number."""
    triple = PARTY_TRIPLES[name]
    colours = palette["colours"]
    return {"k": colours[PARTY_INK], "b": colours[triple["body"]], "a": colours[triple["accent"]]}


def party_trim(grid, spec, pose):
    """The three details the repaint adds, each one earning its place in the drawing as well as in the budget.

    A three entry sheet is only worth having if a tile looks like the figure everywhere, so the drawing gains
    the marks the recolour would otherwise lose and they read as the clothes they are: a belt across the waist,
    a shin rather than a shadow on the far leg, and a cuff at the top of each boot.
    """
    # Belt: two rows across the waist, over cloth only, so the arm and the shirt front keep their own line.
    for y in (16, 17):
        for x in range(5, 18):
            if grid.get(x, y) in ("c", "C"):
                grid.put(x, y, "a")
    # The far leg's shin is cloth: the shadow is the thigh, not the whole limb.
    for y in range(26, 29):
        for x in range(5, 13):
            if grid.get(x, y) == "d":
                grid.put(x, y, "c")
    # Boot cuffs.
    for x in list(range(5, 10)) + list(range(13, 18)):
        if grid.get(x, 28) in ("c", "d"):
            grid.put(x, 28, "a")
    # A grip on the shaft where the fist closes on it.
    if pose is not None and spec["battle"].get("weapon_in_normal"):
        hand_x, hand_y = pose["hand"]
        for y in (hand_y, hand_y + 1):
            for x in range(hand_x + 1, min(BATTLE_W, hand_x + 5)):
                if grid.get(x, y) == "m":
                    grid.put(x, y, "a")


def tile_roles(grid):
    """Per 8x8 tile, the set of roles it carries. Empty tiles are not tiles of the figure."""
    found = {}
    for ty in range(BATTLE_H // TILE):
        for tx in range(BATTLE_W // TILE):
            roles = set()
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    code = grid.get(x, y)
                    if code:
                        roles.add(code)
            if roles:
                found[(tx, ty)] = roles
    return found


def carry_tiles(grid):
    """Give every inked tile the roles it is short of, in the drawing's own terms.

    The accent is the top edge of a mass (the light falls on it) and the body is the lit face under that edge,
    so a tile short of an accent takes one of its body pixels, a tile short of a body takes one of its accent
    pixels, and a tile short of a line takes an edge pixel. Pixels with filled neighbours are preferred, so the
    mark lands inside a mass where it reads as the fold it is; a tile too thin to give one up (a lone outline
    pixel) has its neighbour grown instead, and the build prints how many tiles that was. Returns the tiles it
    touched, so the count is reported rather than hidden.
    """
    touched = []
    for (tx, ty), roles in sorted(tile_roles(grid).items()):
        if roles == set(PARTY_CODES):
            continue
        x0, x1 = tx * TILE, tx * TILE + TILE - 1
        y0, y1 = ty * TILE, ty * TILE + TILE - 1
        box = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
        changed = False
        for missing in ("a", "b", "k"):
            if missing in roles:
                continue
            source = {"a": "b", "b": "a", "k": "b"}[missing]
            held = [p for p in box if grid.get(p[0], p[1]) == source]
            if missing == "k":
                candidates = [p for p in box if grid.get(p[0], p[1]) in ("a", "b")
                              and any(not grid.get(nx, ny) for nx, ny in
                                      ((p[0] - 1, p[1]), (p[0] + 1, p[1]), (p[0], p[1] - 1), (p[0], p[1] + 1)))]
                if not candidates:
                    candidates = [p for p in box if grid.get(p[0], p[1]) in ("a", "b")]
            elif missing == "a":
                # The light falls on the top of a mass: a body pixel whose own top edge is bare.
                candidates = [p for p in held if grid.get(p[0], p[1] - 1) in (None, "k")] or held
            else:
                # The body is the lit face: the accent pixel under a top edge is the one that goes body.
                candidates = [p for p in held if grid.get(p[0], p[1] - 1) == "a"] or held
            if missing != "k" and len(held) < 2:
                # Taking the only pixel of that role would cost the tile the role it already has.
                candidates = []

            def buried(pixel):
                x, y = pixel
                return -sum(1 for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                            if grid.get(nx, ny))

            if candidates:
                candidates.sort(key=lambda p: (buried(p), p))
                x, y = candidates[0]
                grid.put(x, y, missing)
                roles = roles | {missing}
                changed = True
                continue
            # Nothing to give up: grow one of the tile's pixels into an empty neighbour inside the tile.
            filled = [(x, y) for x, y in box if grid.get(x, y)]
            if not filled:
                continue
            filled.sort(key=lambda p: (buried(p), p))
            for x, y in filled:
                grown = False
                for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if x0 <= nx <= x1 and y0 <= ny <= y1 and not grid.get(nx, ny):
                        grid.put(nx, ny, missing)
                        roles = roles | {missing}
                        changed = True
                        grown = True
                        break
                if grown:
                    break
        if changed:
            touched.append((tx, ty))
    return touched


def party_battle_grid(spec, pose):
    """One party battle frame, as three roles, with the token that keeps every tile a carrier."""
    review = battle_frame(spec, pose, False)
    party_trim(review, spec, pose)
    grid = Grid(BATTLE_W, BATTLE_H)
    for (x, y), code in review.px.items():
        grid.put(x, y, PARTY_ROLE[code])
    touched = carry_tiles(grid)
    return grid, touched


def party_battle_sheet(spec):
    frames = []
    touched = []
    for index, (_label, pose) in enumerate(POSES):
        grid, carried = party_battle_grid(spec, pose)
        frames.append(grid)
        touched.extend((index, tile) for tile in carried)
    return frames, touched


def check_party_triple(image, name):
    """Refuse a party sheet that is not exactly three colours in every inked 8x8 tile."""
    colours = set()
    pixels = image.load()
    tile_sets = set()
    for ty in range(image.height // TILE):
        for tx in range(image.width // TILE):
            found = set()
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    value = pixels[x, y]
                    if value[3]:
                        found.add(value[:3])
                        colours.add(value[:3])
            if found:
                tile_sets.add(frozenset(found))
    if len(colours) != 3 or len(tile_sets) != 1:
        raise SystemExit("%s: %d colours and %d distinct per-tile colour sets, expected 3 and 1"
                         % (name, len(colours), len(tile_sets)))
    return sorted(colours), len(tile_sets)


# ----------------------------------------------------------------------------------------------------------------
# The per tile colour solver. A sprite tile holds 3 opaque colours plus transparent; a frame drawn from parts
# can exceed that, so the excess is recoloured to the nearest colour the tile already keeps.
# ----------------------------------------------------------------------------------------------------------------
def rgb(hex_value):
    return (int(hex_value[1:3], 16), int(hex_value[3:5], 16), int(hex_value[5:7], 16))


def distance(a, b):
    # Red mean weighted distance: closer to how the eye separates two skin tones than plain RGB.
    rmean = (a[0] + b[0]) / 2.0
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((512 + rmean) * dr * dr / 256.0) + 4.0 * dg * dg + ((767 - rmean) * db * db / 256.0)


def solve_tiles(image):
    """Return (image, tiles_changed, pixels_recoloured). Mutates a copy, never the input."""
    image = image.copy()
    pixels = image.load()
    changed_tiles = 0
    recoloured = 0
    for ty in range(image.height // TILE):
        for tx in range(image.width // TILE):
            counts = {}
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    r, g, b, a = pixels[x, y]
                    if a:
                        counts[(r, g, b)] = counts.get((r, g, b), 0) + 1
            if len(counts) <= 3:
                continue
            changed_tiles += 1
            ink = rgb(INK)
            keep = []
            if ink in counts:
                keep.append(ink)
            rest = sorted(
                ((colour, count) for colour, count in counts.items() if colour not in keep),
                key=lambda item: (-item[1], item[0]))
            for colour, _count in rest:
                if len(keep) >= 3:
                    break
                keep.append(colour)
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    r, g, b, a = pixels[x, y]
                    if not a:
                        continue
                    colour = (r, g, b)
                    if colour in keep:
                        continue
                    target = min(keep, key=lambda kept: (distance(colour, kept), kept))
                    pixels[x, y] = (target[0], target[1], target[2], 255)
                    recoloured += 1
    return image, changed_tiles, recoloured


def sheet_image(frames, hexes, frame_w, frame_h):
    image = Image.new("RGBA", (frame_w * len(frames), frame_h), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        image.alpha_composite(frame.to_image(hexes), (index * frame_w, 0))
    return image


def check_with_nes_check(image, label):
    import nes_check

    palette = nes_check.load_palette(os.path.join(REPO_ROOT, "data", "nes_palette.json"))
    report = nes_check.check(image, "sprite", palette)
    if not report["ok"]:
        lines = ["%s fails the NES rules:" % label] + nes_check.describe(report, label)
        raise SystemExit("\n".join(lines))
    return report


# ----------------------------------------------------------------------------------------------------------------
# Outputs.
# ----------------------------------------------------------------------------------------------------------------
def write_sheet(directory, name, image, frame_w, frame_h, fps, notes):
    png_path = os.path.join(directory, name + ".png")
    json_path = os.path.join(directory, name + ".json")
    image.save(png_path, "PNG")
    meta = {
        "name": name,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "frames": image.width // frame_w,
        "fps": fps,
    }
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    digest = hashlib.sha256(open(png_path, "rb").read()).hexdigest()
    notes.append((name, image.width, image.height, meta["frames"], digest[:16]))
    return png_path, meta


def label_text(draw, text, x, y, scale, colour, shadow=True):
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
                if shadow:
                    draw.rectangle([px + scale, py + scale, px + scale * 2 - 1, py + scale * 2 - 1],
                                   fill=rgb(GREY))
                draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=colour)


def contact_sheet(rows, scale, width, background_index):
    """rows: [(label, list of (image, label2))]. Everything is drawn at one whole number scale."""
    height = 0
    plan = []
    for label, entries in rows:
        height += 14 * scale + 6 * scale
        plan.append((label, entries))
        for _entry_label, image in entries:
            height += image.height * scale + 16 * scale
    canvas = Image.new("RGBA", (width, height), rgb("#000000") + (255,))
    draw_image = ImageDraw.Draw(canvas)
    y = 6 * scale
    for label, entries in plan:
        label_text(draw_image, label, 8 * scale, y, scale, rgb(WHITE))
        y += 14 * scale
        for entry_label, image in entries:
            big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
            canvas.alpha_composite(big, (8 * scale, y))
            label_text(draw_image, entry_label, 8 * scale, y + image.height * scale + 3 * scale,
                       scale, rgb(GREY_L))
            y += image.height * scale + 16 * scale
    return canvas


def build(root):
    global REPO_ROOT
    REPO_ROOT = root
    palette_path = os.path.join(root, "data", "nes_palette.json")
    with open(palette_path, "r", encoding="utf-8") as handle:
        palette = json.load(handle)
    allowed = {value.strip().lower() for value in palette["colours"]}

    out_dir = os.path.join(root, "game", "sprites_src", "chars")
    os.makedirs(out_dir, exist_ok=True)
    preview_dir = os.path.join(root, "output")
    os.makedirs(preview_dir, exist_ok=True)

    notes = []
    solved = []
    contact_rows = []
    party_carried = []
    for spec in character_specs():
        hexes = code_map(spec)
        for code, value in sorted(hexes.items()):
            if value.lower() not in allowed:
                raise SystemExit("%s: code %r is %s, which is not a 2C02 output" % (spec["name"], code, value))

        ow = sheet_image(ow_sheet(spec), hexes, OW_W, OW_H)
        ow, tiles_changed, recoloured = solve_tiles(ow)
        check_with_nes_check(ow, spec["name"] + "_ow")
        write_sheet(out_dir, spec["name"] + "_ow", ow, OW_W, OW_H, OW_FPS, notes)
        solved.append((spec["name"] + "_ow", tiles_changed, recoloured))

        battle = None
        if writes_battle_sheet(spec["name"]):
            if spec["name"] in PARTY_TRIPLES:
                # One reserved hero triple, one palette per figure (card t_d5483a88). No solver: the drawing is
                # already three colours, and check_party_triple refuses a sheet where a single tile carries fewer.
                party_frames, carried = party_battle_sheet(spec)
                battle = sheet_image(party_frames, party_hexes(palette, spec["name"]), BATTLE_W, BATTLE_H)
                tiles_changed, recoloured = 0, 0
                party_carried.append((spec["name"], carried))
            else:
                battle = sheet_image(battle_sheet(spec, False), hexes, BATTLE_W, BATTLE_H)
                battle, tiles_changed, recoloured = solve_tiles(battle)
        entries = [("OVERWORLD 8 FRAMES 16X16", ow)]
        if battle is not None:
            check_with_nes_check(battle, spec["name"] + "_battle")
            if spec["name"] in PARTY_TRIPLES:
                check_party_triple(battle, spec["name"] + "_battle")
            write_sheet(out_dir, spec["name"] + "_battle", battle, BATTLE_W, BATTLE_H, BATTLE_FPS, notes)
            solved.append((spec["name"] + "_battle", tiles_changed, recoloured))
            entries.append(("BATTLE 7 FRAMES 24X32", battle))

        if spec["battle"]["weapon"] and spec["name"] != "sailor":
            god = sheet_image(battle_sheet(spec, True), hexes, BATTLE_W, BATTLE_H)
            god, tiles_changed, recoloured = solve_tiles(god)
            check_with_nes_check(god, spec["name"] + "_god_battle")
            write_sheet(out_dir, spec["name"] + "_god_battle", god, BATTLE_W, BATTLE_H, BATTLE_FPS, notes)
            solved.append((spec["name"] + "_god_battle", tiles_changed, recoloured))
            entries.append(("GOD FORM 7 FRAMES 24X32", god))
        contact_rows.append((spec["label"], entries))

    width = 8 * 4 + max(image.width for _l, entries in contact_rows for _e, image in entries) * 4 + 8 * 4
    contact = contact_sheet(contact_rows, 4, width, None)
    contact_path = os.path.join(preview_dir, "chars_contact.png")
    contact.save(contact_path, "PNG")

    width3 = 8 * 3 + max(image.width for _l, entries in contact_rows for _e, image in entries) * 3 + 8 * 3
    preview3 = contact_sheet(contact_rows, 3, width3, None)
    preview3_path = os.path.join(preview_dir, "chars_preview_3x.png")
    preview3.save(preview3_path, "PNG")

    return notes, solved, contact_path, preview3_path, party_carried


REPO_ROOT = os.path.dirname(os.path.dirname(HERE))


def dump_frames(root):
    """Text rendering of a few frames: the only way a worker without vision can check a silhouette."""
    for spec in character_specs():
        print("=== %s overworld, facing down, standing ===" % spec["name"])
        for line in ow_frame(spec, "down", False).dump():
            print("  " + line)
        print("=== %s battle, idle 0 ===" % spec["name"])
        for line in battle_frame(spec, POSES[0][1], False).dump():
            print("  " + line)
        print()


def main(argv=None):
    global REPO_ROOT
    parser = argparse.ArgumentParser(description="Draw the SPRITE-1 cast as NES sprites.")
    parser.add_argument("--root", default=None, help="repository root; default is two levels above this file")
    parser.add_argument("--dump", action="store_true", help="print frames as text instead of writing PNGs")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else REPO_ROOT
    REPO_ROOT = root
    if args.dump:
        dump_frames(root)
        return 0
    notes, solved, contact_path, preview3_path, party_carried = build(root)
    # NES-PALETTES: the ship scene owns four sprite palettes of three entries, and they are the party's four
    # walking triples (ruling section 17, card t_a6a7a436), so the walking sailor is enforced to them here, at the
    # end of the build, so a regeneration cannot put a fourth colour back into an 8x16 group.
    # data/palettes/scene_ship.json is the budget; tools/check_scene_palettes.py is the judge.
    # sailor_battle.png is NOT in this pass any more: it is a 168x32 battle sheet, the ship's rows no longer carry
    # it, and enforcing it would repaint 621 of its 2398 opaque pixels into the party's triples (measured on card
    # t_a6a7a436). Its ground is card t_0b9c2faf.
    for name in ("sailor_ow",):
        try:
            sys.path.insert(0, HERE)
            import scene_palette
            scene = scene_palette.load_scene(root, "ship")
            image, meta = scene_palette.load_cast(root, name)
            stats = scene_palette.enforce_sprites(image, scene, meta["frame_w"], meta["frame_h"])
            image.save(os.path.join(root, "game", "sprites_src", "chars", name + ".png"), "PNG")
            print("  %-22s scene ship sprites: %d tiles, %d pixels rewritten, worst %d colours"
                  % (name, stats["tiles"], stats["pixels_moved"], stats["worst_colours"]))
        except Exception as exc:
            print("  %-22s scene palette pass skipped (%s)" % (name, exc))
    print("sheets written to game/sprites_src/chars:")
    for name, width, height, frames, digest in notes:
        print("  %-22s %3dx%-3d %d frames  sha256=%s" % (name, width, height, frames, digest))
    print("tile solver (colours above 3 in an 8x8 tile, recoloured to the nearest kept colour):")
    for name, tiles, pixels in solved:
        print("  %-22s %d tiles, %d pixels" % (name, tiles, pixels))
    print("party battle sheets (one reserved hero triple each, every inked tile carries all three):")
    for name, carried in party_carried:
        tiles = sorted(set(tile for _frame, tile in carried))
        print("  %-22s %d tile(s) given back a role%s"
              % (name, len(tiles),
                 (": " + " ".join("(%d,%d)" % t for t in tiles)) if tiles else ""))
    print("previews:")
    print("  " + contact_path)
    print("  " + preview3_path)
    return 0


if __name__ == "__main__":
    from PIL import ImageDraw  # noqa: F401  (used by the contact sheet)

    sys.exit(main())
