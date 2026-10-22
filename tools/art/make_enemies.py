#!/usr/bin/env python3
"""make_enemies.py: draw the ENEMIES-1 cast as NES battle sprites, part based, from numbers in this file.

Contract: knowledge/ART-BIBLE.md (NES limits), knowledge/CHARACTER-BIBLE.md REVISION 2 (setting),
PLAN-V2-2026-10-21.md section 0 (original work only) and specs/16-talk-command.md (the TALK card fields).

What is drawn, and how it stays inside the chip:
- Each enemy is 32x32, built from named parts (cap, head, torso, arm, leg, weapon, wing, loop, drip) plus
  a small deterministic shape kit (rect, ellipse, ring, line). A part is an ASCII block of palette codes,
  so a character is a palette plus a list of parts, the same rule tools/art/make_characters.py follows.
- Each enemy sheet is 96x32: frame 0 idle, frame 1 idle (the breathing frame), frame 2 the hit flash.
  The hit frame recolours the mid tone to the light tone, so it still uses the enemy's own 3 colours and
  the game does not need a fourth sprite palette to flash it.
- Every colour is one of the outputs of the 2C02 (data/nes_palette.json), and each enemy is assigned
  exactly one of the four sprite palettes of the sea battle scene (data/palettes/scene_sea.json):
  three opaque colours plus transparency. Four palettes cover seven enemies because a battle frame draws
  one enemy, and NES enemies share sprite palettes (ART-BIBLE 2.4, Castlevania, S12).
- tools/nes_check.py is imported as the judge, so a bad sheet stops the build instead of reaching the game.

Outputs:
    game/sprites_src/enemies/<name>.png    96x32, 3 frames, 32x32 each
    game/sprites_src/enemies/<name>.json   sheet metadata (same shape as the char sidecars)
    data/enemies/roster.json               palette, hp, voice, weak and strong topics, personality line
    output/enemies_preview.png             contact sheet at 4x with labels
    output/enemies_preview_3x.png          the same at 3x
    output/enemies_battle_frame.png        one 256x240 sea battle frame, enemy in place, for the frame check
    output/enemies_battle_sprites.json     the sprite rectangles of that frame (8x16 hardware sprites)
    output/enemies_report.json             every measurement this script took

Determinism: no clock, no randomness, no set iteration in drawing order. Run twice, same sha256.

Usage:
    python tools/art/make_enemies.py
    python tools/art/make_enemies.py --dump     # print the frames as ASCII and exit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import pressstart2p_font  # noqa: E402

W = H = 32
FRAME_NAMES = ("idle0", "idle1", "hit")
FPS = 8.0
SPRITE_HEIGHT = 16
# specs/16-talk-command.md section 2: trust = floor(mercy / 20), and trust_to_spare 3 is the demo value, so
# mercy_to_spare is 60 for every enemy on this card. The talk card card may move a single enemy later.
TRUST_TO_SPARE = 3

# ----------------------------------------------------------------------------------------------------------------
# Palettes. Entry numbers into data/nes_palette.json, and the hex each entry must carry. The script refuses to
# draw if a number and its hex disagree, so the palette cannot drift out from under the art.
# codes: k = ink / outline, m = mid tone, l = light tone, . = transparent
# ----------------------------------------------------------------------------------------------------------------
PALETTES = {
    "sp0_navy_white": {
        "entries": [15, 2, 48],
        "hex": {"k": "#000000", "m": "#0000bc", "l": "#fcfcfc"},
        "role": "black outline, Royal Navy blue, white shirt and cap",
    },
    "sp1_brown_gold": {
        "entries": [15, 7, 40],
        "hex": {"k": "#000000", "m": "#881400", "l": "#f8b800"},
        "role": "black outline, brown fur and rope, amber light",
    },
    "sp2_green": {
        "entries": [15, 26, 42],
        "hex": {"k": "#000000", "m": "#00a800", "l": "#58d854"},
        "role": "black outline, bilge green, lit green",
    },
    "sp3_sea": {
        "entries": [2, 33, 48],
        "hex": {"k": "#0000bc", "m": "#3cbcfc", "l": "#fcfcfc"},
        "role": "navy outline, sea cyan, white foam and gull body",
    },
}

# ----------------------------------------------------------------------------------------------------------------
# Parts. Every row of every part is the same width; stamp() enforces it, so a typo stops the build.
# ----------------------------------------------------------------------------------------------------------------
CAP_WHITE = [
    "...llllll...",
    "..llllllll..",
    ".llllllllll.",
    "mmmmmmmmmmmm",
]
CAP_PEAKED = [
    "...llllllll...",
    "..llllllllll..",
    ".llllllllllll.",
    "mmmmmmmmmmmmmm",
    "...mmmmmm.....",
]
HEAD = [
    "..kkkkkk..",
    ".kllllllk.",
    ".kllllllk.",
    ".kllllllk.",
    ".kllllklk.",
    ".kllllllk.",
    "..kllllk..",
    "...kkkk...",
]
BEARD = [
    "..kkkk..",
    ".kkkkkk.",
    ".kkkkkk.",
    "..kkkk..",
]
TORSO_JACKET = [
    "...kkkkkkkk...",
    "..kmmmmmmmmk..",
    "..kmmllllmmk..",
    "..kmmllllmmk..",
    "..kmmmmmmmmk..",
    "..kmmkmmmmmk..",
    "..kmmmmmmmmk..",
    "..kmmkmmmmmk..",
    "..kkkkkkkkkk..",
]
ARM = [
    ".kk",
    "kmm",
    "kmm",
    "kmm",
    "kmm",
    "kmm",
    "kll",
    ".kk",
]
LEG = [
    ".kkk.",
    "kmmmk",
    "kmmmk",
    "kmmmk",
    "kmmmk",
    ".kkk.",
    "klllk",
    "kkkkk",
]
CLIPBOARD = [
    "llll",
    "lmmk",
    "lmmk",
    "lmmk",
    "lmmk",
    "llll",
    "kkkk",
]
WING_SPREAD = [
    "llllllllllll",
    "llllllllll..",
    ".mmmmmmmmm..",
    "..mmmmmmm...",
    "...mmmmm....",
    "....mmm.....",
    ".....m......",
]
WING_FOLDED = [
    ".....m......",
    "....mml.....",
    "...mmll.....",
    "..mmlll.....",
    ".mmllll.....",
    "mllllll.....",
    "mmmmmmm.....",
]


def mirrored(rows):
    """A part flipped horizontally, for the right hand and the far wing."""
    return [row[::-1] for row in rows]


class Grid:
    """A 32x32 grid of palette codes. Drawing is plain deterministic arithmetic, no randomness."""

    def __init__(self):
        self.cells = [["." for _ in range(W)] for _ in range(H)]

    def get(self, x, y):
        if 0 <= x < W and 0 <= y < H:
            return self.cells[y][x]
        return "."

    def set(self, x, y, code):
        if 0 <= x < W and 0 <= y < H:
            self.cells[y][x] = code

    def rect(self, x0, y0, x1, y1, code):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.set(x, y, code)

    def hline(self, x0, x1, y, code):
        self.rect(x0, y, x1, y, code)

    def vline(self, x, y0, y1, code):
        self.rect(x, y0, x, y1, code)

    def ellipse(self, cx, cy, rx, ry, code):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                dx = (x - cx) / float(rx)
                dy = (y - cy) / float(ry)
                if dx * dx + dy * dy <= 1.0:
                    self.set(x, y, code)

    def carve(self, cx, cy, rx, ry):
        """Set an ellipse back to transparent, which is how a wave gets its curl."""
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                dx = (x - cx) / float(rx)
                dy = (y - cy) / float(ry)
                if dx * dx + dy * dy <= 1.0:
                    self.set(x, y, ".")

    def ring(self, cx, cy, rx, ry, code, thickness=1):
        outer = Grid()
        outer.ellipse(cx, cy, rx, ry, code)
        inner = Grid()
        inner.ellipse(cx, cy, max(0.5, rx - thickness), max(0.5, ry - thickness), code)
        for y in range(H):
            for x in range(W):
                if outer.cells[y][x] == code and inner.cells[y][x] != code:
                    self.set(x, y, code)

    def line(self, x0, y0, x1, y1, code):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, code)
            if x0 == x1 and y0 == y1:
                break
            err2 = 2 * err
            if err2 >= dy:
                err += dy
                x0 += sx
            if err2 <= dx:
                err += dx
                y0 += sy

    def blob(self, cx, cy, r, code):
        self.ellipse(cx, cy, r, r, code)

    def stamp(self, rows, x, y, code_map=None):
        width = len(rows[0])
        for index, row in enumerate(rows):
            if len(row) != width:
                raise SystemExit("part row %d is %d wide, the block is %d: %r" % (index, len(row), width, row))
            for offset, char in enumerate(row):
                if char == ".":
                    continue
                self.set(x + offset, y + index, char if code_map is None else code_map.get(char, char))

    def outline(self, code="k"):
        """One pixel of ink around every opaque shape, including inside holes between limbs."""
        opaque = {(x, y) for y in range(H) for x in range(W) if self.cells[y][x] != "."}
        additions = set()
        for x, y in sorted(opaque):
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    nx, ny = x + ox, y + oy
                    if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in opaque:
                        additions.add((nx, ny))
        for x, y in sorted(additions):
            self.cells[y][x] = code

    def recolour(self, mapping):
        for y in range(H):
            for x in range(W):
                code = self.cells[y][x]
                if code in mapping:
                    self.cells[y][x] = mapping[code]

    def opaque_count(self):
        return sum(1 for y in range(H) for x in range(W) if self.cells[y][x] != ".")

    def ascii(self):
        return "\n".join("".join(row) for row in self.cells)

    def to_image(self, hexes):
        image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pixels = image.load()
        for y in range(H):
            for x in range(W):
                code = self.cells[y][x]
                if code == ".":
                    continue
                value = hexes[code].lstrip("#")
                pixels[x, y] = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)
        return image


# ----------------------------------------------------------------------------------------------------------------
# The cast. One draw function per enemy, taking the frame index, so the idle frame is a real second pose.
# ----------------------------------------------------------------------------------------------------------------
def draw_sailor(frame):
    grid = Grid()
    dy = 1 if frame == 1 else 0
    grid.stamp(CAP_WHITE, 10, 1 + dy)
    grid.stamp(HEAD, 11, 5 + dy)
    grid.stamp(TORSO_JACKET, 9, 13 + dy)
    grid.stamp(ARM, 7, 15 + dy)
    grid.stamp(mirrored(ARM), 22, 15 + dy)
    grid.stamp(LEG, 11, 22)
    grid.stamp(LEG, 17, 22)
    # the mop: pole in the right hand, head on the deck
    grid.vline(25, 10 + dy, 25, "k")
    grid.rect(23, 25, 27, 29, "l")
    grid.vline(25, 24, 29, "m")
    for x in (23, 27):
        grid.vline(x, 27, 29, "m")
    grid.set(24, 26, "k")
    grid.set(26, 28, "k")
    return grid


def draw_officer(frame):
    grid = Grid()
    dy = 1 if frame == 1 else 0
    grid.stamp(CAP_PEAKED, 9, 0 + dy)
    grid.stamp(HEAD, 11, 5 + dy)
    grid.stamp(BEARD, 13, 9 + dy)
    grid.stamp(TORSO_JACKET, 9, 13 + dy)
    grid.stamp(ARM, 7, 15 + dy)
    grid.stamp(mirrored(ARM), 22, 15 + dy)
    grid.stamp(LEG, 11, 22)
    grid.stamp(LEG, 17, 22)
    # rank stripes on both sleeves: the white bands that say "tougher than the sailor"
    for x0, x1 in ((7, 9), (22, 24)):
        grid.hline(x0, x1, 17 + dy, "l")
        grid.hline(x0, x1, 19 + dy, "l")
    # the clipboard he inspects the deck with, held low in the right hand
    grid.stamp(CLIPBOARD, 25, 17)
    return grid


def draw_rat(frame):
    grid = Grid()
    dy = 1 if frame == 1 else 0
    # tail first, curling up behind the body
    grid.line(8, 23, 4, 21, "m")
    grid.line(4, 21, 2, 17, "m")
    grid.line(2, 17, 3, 12, "m")
    grid.line(3, 12, 6, 9, "m")
    grid.set(5, 9, "l")
    # feet
    for x in (9, 13, 17, 21):
        grid.rect(x, 26, x + 2, 28, "m")
    grid.ellipse(14, 20 - dy, 10, 6, "m")
    grid.ellipse(13, 23 - dy, 6, 3, "l")
    grid.ellipse(24, 16 + dy, 5, 4, "m")
    grid.rect(27, 17 + dy, 29, 19 + dy, "m")
    grid.ellipse(23, 10 + dy, 3, 3, "m")
    grid.ellipse(23, 10 + dy, 1, 1, "l")
    grid.outline()
    # face, after the outline so the eye is not eaten by it
    grid.rect(24, 14 + dy, 25, 15 + dy, "k")
    grid.set(29, 18 + dy, "k")
    grid.set(28, 21 + dy, "l")
    grid.set(30, 17 + dy, "k")
    grid.set(30, 20 + dy, "k")
    return grid


def draw_gull(frame):
    grid = Grid()
    folded = frame == 1
    wing = WING_FOLDED if folded else WING_SPREAD
    # body dives from the upper left to the lower right
    for step in range(0, 11):
        x = 9 + step
        y = 8 + step
        grid.blob(x, y, 3 if step < 8 else 2, "l")
    # head and the dark beak pointing down
    grid.ellipse(22, 21, 3, 3, "l")
    grid.rect(24, 22, 26, 23, "k")
    grid.set(27, 24, "k")
    # tail feathers
    grid.rect(6, 6, 9, 8, "l")
    grid.set(7, 5, "m")
    grid.set(8, 5, "m")
    # wings: the far one up and left, the near one swept back
    grid.stamp(wing, 2, 12 if not folded else 14)
    grid.stamp(mirrored(wing), 16, 2 if not folded else 4)
    grid.outline()
    grid.rect(22, 20, 22, 21, "k")
    return grid


def draw_wave(frame):
    grid = Grid()
    # the swell: frame 1 lifts the whole body one pixel and throws a different spray, so the silhouette moves
    # across its whole width instead of only at the crest points
    rise = 0 if frame == 0 else 1
    dy = rise
    grid.ellipse(14, 24 - rise, 14, 8, "m")
    grid.ellipse(14, 18 - rise, 12, 9, "m")
    grid.carve(25, 13 - rise, 8, 6)
    grid.ring(20, 15 - rise, 8, 6, "m", thickness=2)
    # foam along the crest
    for x, y in ((3, 17), (4, 15), (6, 13), (8, 12), (10, 11), (12, 10 + dy), (14, 10 + dy),
                 (16, 11 + dy), (18, 12 + dy), (20, 14 + dy), (21, 17 + dy)):
        grid.set(x, y, "l")
        grid.set(x, y + 1, "l")
    # spray thrown off the top, a different cast each frame
    spray0 = ((2, 8), (5, 5), (9, 3), (24, 6), (27, 9), (29, 12), (26, 4))
    spray1 = ((1, 7), (4, 4), (8, 2), (25, 5), (28, 8), (30, 11), (27, 3))
    for x, y in (spray0 if frame == 0 else spray1):
        grid.set(x, y, "l")
    # foam band on the deck at the bottom, which the body lifts away from
    for x in range(3, 30, 4):
        grid.rect(x, 29, x + 2, 30, "l")
    grid.outline()
    # the eyes, two blocks with a navy pupil, the thing that makes it alive
    grid.rect(10, 19, 13, 21, "l")
    grid.rect(17, 19, 20, 21, "l")
    grid.rect(12, 20, 12, 21, "k")
    grid.rect(19, 20, 19, 21, "k")
    # a mouth of foam under the eyes
    for x in range(12, 19):
        grid.set(x, 24, "k")
    return grid


def draw_rope(frame):
    grid = Grid()
    # frame 1 tightens: the whole knot sits one pixel higher and the loose end flicks the other way
    dy = 0 if frame == 0 else 1
    grid.ring(10, 19 - dy, 6, 6, "m", thickness=2)
    grid.ring(21, 19 - dy, 6, 6, "m", thickness=2)
    grid.ring(15, 12 - dy, 6, 5, "m", thickness=2)
    grid.outline()
    # the twist of the rope: light dashes around each loop
    for index in range(0, 12, 3):
        grid.set(4 + index % 4, 15 - dy + index // 4, "l")
        grid.set(17 + index % 4, 15 - dy + index // 4, "l")
        grid.set(10 + index % 5, 8 - dy + index // 5, "l")
    # the knot core, with the two eyes buried in it
    grid.ellipse(15, 19 - dy, 4, 4, "m")
    grid.outline()
    grid.set(13, 18 - dy, "k")
    grid.set(17, 18 - dy, "k")
    grid.set(13, 20 - dy, "l")
    grid.set(17, 20 - dy, "l")
    # loose end: frame 1 flicks it the other way, which is the whole idle
    if frame == 1:
        grid.line(23, 24, 30, 27, "m")
        grid.set(30, 28, "l")
        grid.set(31, 27, "l")
    else:
        grid.line(23, 25, 28, 30, "m")
        grid.set(29, 30, "l")
        grid.set(30, 29, "l")
    return grid


def draw_slime(frame):
    grid = Grid()
    dy = 1 if frame == 1 else 0
    grid.ellipse(16, 25, 12, 5, "m")
    grid.ellipse(16, 18 - dy, 10, 8, "m")
    grid.ellipse(7, 27 + dy, 2, 2 + dy, "m")
    grid.ellipse(25, 27 + dy, 2, 3 + dy, "m")
    grid.ellipse(16, 30, 13, 2, "m")
    grid.outline()
    # wet highlight, then the face
    for x, y in ((11, 13), (12, 12), (13, 12), (14, 13), (11, 14)):
        grid.set(x, y - dy, "l")
    grid.rect(12, 16, 14, 18, "l")
    grid.rect(19, 16, 21, 18, "l")
    grid.rect(13, 17, 13, 18, "k")
    grid.rect(20, 17, 20, 18, "k")
    for x, y in ((14, 21), (15, 22), (16, 22), (17, 22), (18, 21)):
        grid.set(x, y, "k")
    return grid


# name, palette, drawer, sprite resource, hp, voice, wants, fears, weak topics, strong topics, personality line
CAST = [
    {
        "id": "navy_sailor",
        "name": "Navy Sailor",
        "file": "navy_sailor",
        "sprite": "spr_pp_sailor",
        "palette": "sp0_navy_white",
        "draw": draw_sailor,
        "hp": 15,
        "role": "tutorial enemy",
        "personality": "Two years of night watches and a mop he treats like a rifle: tired, decent, and not paid enough to care who you are.",
        "voice": "Lower deck watch keeper, tired, clipped, short flat sentences, no poetry, nothing warmer than dry.",
        "wants": ["the watch to end", "a smoke", "not to be reported", "to be asked his name"],
        "fears": ["the bridge", "being the one who let a stowaway through"],
        "weak_topics": [
            {"topic": "the long watch", "keywords": ["watch", "hours", "standing", "shift"], "examples": ["how long have you been out here"]},
            {"topic": "tiredness", "keywords": ["tired", "sleep", "rest", "wrecked", "exhausted"], "examples": ["you look wrecked"]},
            {"topic": "weather and sea", "keywords": ["sea", "weather", "swell", "storm", "rain", "salt"], "examples": ["rough night"]},
            {"topic": "home port", "keywords": ["home", "port", "family", "where are you from"], "examples": ["where are you from"]},
            {"topic": "a smoke", "keywords": ["smoke", "cigarette", "break", "fag"], "examples": ["want a smoke"]},
        ],
        "strong_topics": [
            {"topic": "the bridge", "keywords": ["bridge", "captain", "officer", "radio"], "examples": ["the bridge will hear about this"]},
            {"topic": "orders and the list", "keywords": ["orders", "the list", "allowed", "permission", "rules"], "examples": ["you are not on the list"]},
            {"topic": "threats", "keywords": ["move", "hurt", "kill", "shoot", "push", "force"], "examples": ["move or I move you"]},
            {"topic": "his watch being pointless", "keywords": ["pointless", "waste", "useless", "nobody cares"], "examples": ["this is a waste of time"]},
        ],
    },
    {
        "id": "petty_officer",
        "name": "Petty Officer",
        "file": "petty_officer",
        "sprite": "spr_pp_petty_officer",
        "palette": "sp0_navy_white",
        "draw": draw_officer,
        "hp": 28,
        "role": "tougher regular enemy",
        "personality": "A clipboard with a man attached: he has written your name down already and he is disappointed in the handwriting.",
        "voice": "Brisk, clipped, faintly bored authority; short sentences.",
        "wants": ["a deck that passes inspection", "the paperwork to be correct the first time"],
        "fears": ["the captain walking past during an inspection", "an untidy ledger"],
        "weak_topics": [
            {"topic": "the paperwork", "keywords": ["form", "paper", "ledger", "sign", "stamp"], "examples": ["May I see the form"]},
            {"topic": "the young crew", "keywords": ["lad", "kid", "training", "recruit", "teach"], "examples": ["They are still learning"]},
        ],
        "strong_topics": [
            {"topic": "rank and respect", "keywords": ["sir", "rank", "salute", "officer", "respect"], "examples": ["Show some respect"]},
            {"topic": "shirking", "keywords": ["skip", "lazy", "later", "tomorrow", "slack"], "examples": ["We will do it tomorrow"]},
        ],
    },
    {
        "id": "deck_rat",
        "name": "Deck Rat",
        "file": "deck_rat",
        "sprite": "spr_pp_deck_rat",
        "palette": "sp1_brown_gold",
        "draw": draw_rat,
        "hp": 12,
        "role": "regular enemy",
        "personality": "Has eaten better than the crew for three years and knows exactly which stores hatch is loose.",
        "voice": "Fast, greedy, unbothered; talks about food and escape routes.",
        "wants": ["biscuits", "the loose hatch left open"],
        "fears": ["the ship's cat", "traps"],
        "weak_topics": [
            {"topic": "food", "keywords": ["food", "biscuit", "cheese", "eat", "ration"], "examples": ["I brought biscuits"]},
            {"topic": "escape routes", "keywords": ["hatch", "hole", "gap", "vent", "way out"], "examples": ["That hatch looks loose"]},
        ],
        "strong_topics": [
            {"topic": "cats", "keywords": ["cat", "mouser", "paws", "whiskers"], "examples": ["Here kitty"]},
            {"topic": "traps and poison", "keywords": ["trap", "poison", "snap", "kill"], "examples": ["I set a trap"]},
        ],
    },
    {
        "id": "gull",
        "name": "Gull",
        "file": "gull",
        "sprite": "spr_pp_gull",
        "palette": "sp3_sea",
        "draw": draw_gull,
        "hp": 10,
        "role": "regular enemy",
        "personality": "Screaming, thieving, entirely convinced the ship was built as a restaurant for one.",
        "voice": "Loud, rude, gleeful; short bursts, food obsessed.",
        "wants": ["chips", "the bin bag on the aft deck"],
        "fears": ["a closed bin lid", "the ship's cat"],
        "weak_topics": [
            {"topic": "chips and scraps", "keywords": ["chips", "food", "scraps", "bread", "bin"], "examples": ["Want a chip"]},
            {"topic": "flying and the wind", "keywords": ["fly", "wind", "sky", "updraft", "wing"], "examples": ["Good wind today"]},
        ],
        "strong_topics": [
            {"topic": "being shooed", "keywords": ["shoo", "go away", "pest", "vermin"], "examples": ["Shoo, pest"]},
            {"topic": "the cat", "keywords": ["cat", "paws", "teeth"], "examples": ["The cat is coming"]},
        ],
    },
    {
        "id": "rogue_wave",
        "name": "Rogue Wave",
        "file": "rogue_wave",
        "sprite": "spr_pp_rogue_wave",
        "palette": "sp3_sea",
        "draw": draw_wave,
        "hp": 40,
        "role": "minion in the Percy fight",
        "personality": "The sea got tired of being told what to do and grew eyes about it.",
        "voice": "Slow, swelling, ancient; speaks in tide and weather, never in names.",
        "wants": ["to reach the deck", "to be left to rise"],
        "fears": ["the wind dropping", "being named and bounded"],
        "weak_topics": [
            {"topic": "the tide and the moon", "keywords": ["tide", "moon", "pull", "rise", "swell"], "examples": ["The moon is pulling you"]},
            {"topic": "open water", "keywords": ["ocean", "deep", "horizon", "open", "far"], "examples": ["Out past the horizon you are free"]},
        ],
        "strong_topics": [
            {"topic": "being named and bound", "keywords": ["name", "bound", "command", "obey", "order"], "examples": ["I name you"]},
            {"topic": "the ship and its steel", "keywords": ["ship", "steel", "hull", "deck", "boat"], "examples": ["This ship stops you"]},
        ],
    },
    {
        "id": "rope_knot",
        "name": "Rope Knot",
        "file": "rope_knot",
        "sprite": "spr_pp_rope_knot",
        "palette": "sp1_brown_gold",
        "draw": draw_rope,
        "hp": 22,
        "role": "regular enemy",
        "personality": "Nobody tied it and nobody can untie it, and it has opinions about both facts.",
        "voice": "Tight, tangled, grumbling; repeats itself, corrects itself.",
        "wants": ["to be left alone", "someone to try and fail to untie it"],
        "fears": ["a sharp knife", "being pulled apart"],
        "weak_topics": [
            {"topic": "untangling", "keywords": ["untie", "loose", "pull", "end", "free"], "examples": ["Let me find the end"]},
            {"topic": "being useful", "keywords": ["useful", "hold", "moor", "tie", "job"], "examples": ["The ship still needs a line"]},
        ],
        "strong_topics": [
            {"topic": "cutting", "keywords": ["cut", "knife", "slice", "burn"], "examples": ["I will cut you"]},
            {"topic": "who tied it", "keywords": ["who", "tied", "your fault", "blame"], "examples": ["Who tied you"]},
        ],
    },
    {
        "id": "bilge_slime",
        "name": "Bilge Slime",
        "file": "bilge_slime",
        "sprite": "spr_pp_bilge_slime",
        "palette": "sp2_green",
        "draw": draw_slime,
        "hp": 18,
        "role": "regular enemy",
        "personality": "The bottom of the ship learned to want things: warmth, a biscuit, and the sound of someone saying its name.",
        "voice": "Slow, bubbling, friendly, slightly sad; asks small questions.",
        "wants": ["a warm pipe", "someone to talk to down here"],
        "fears": ["the pumps", "being pumped overboard"],
        "weak_topics": [
            {"topic": "loneliness", "keywords": ["alone", "friend", "talk", "stay", "company"], "examples": ["It must be quiet down here"]},
            {"topic": "warmth", "keywords": ["warm", "pipe", "heat", "cosy"], "examples": ["That pipe is warm"]},
        ],
        "strong_topics": [
            {"topic": "the pumps", "keywords": ["pump", "drain", "flush", "empty"], "examples": ["Turn on the pump"]},
            {"topic": "being called filth", "keywords": ["filth", "dirty", "disgusting", "sludge", "gross"], "examples": ["You are filth"]},
        ],
    },
]


def enemy_frames(spec):
    frames = [spec["draw"](0), spec["draw"](1)]
    hit = spec["draw"](0)
    hit.recolour({"m": "l"})
    frames.append(hit)
    return frames


# ----------------------------------------------------------------------------------------------------------------
# Palette loading and the gate.
# ----------------------------------------------------------------------------------------------------------------
def load_master(root):
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = [value.strip().lower() for value in data["colours"]]
    usable = [True] * len(colours)
    for row in data.get("entries", []):
        index = int(row.get("index", row.get("entry", -1)))
        if 0 <= index < len(usable):
            usable[index] = bool(row.get("usable", True))
    return colours, usable


def palette_hexes(root, name):
    colours, usable = load_master(root)
    spec = PALETTES[name]
    hexes = {}
    for code, value in spec["hex"].items():
        hexes[code] = value
    for entry in spec["entries"]:
        if not 0 <= entry < len(colours):
            raise SystemExit("%s: entry %d is outside the 2C02 palette" % (name, entry))
        if not usable[entry]:
            raise SystemExit("%s: entry $%02X is forbidden" % (name, entry))
        if colours[entry] not in [value.lower() for value in hexes.values()]:
            raise SystemExit("%s: entry $%02X is %s, which is not one of %s"
                             % (name, entry, colours[entry], sorted(hexes.values())))
    return hexes


def sheet_image(frames, hexes):
    image = Image.new("RGBA", (W * len(frames), H), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        image.alpha_composite(frame.to_image(hexes), (index * W, 0))
    return image


def check_sheet(root, image, label):
    import nes_check

    palette = nes_check.load_palette(os.path.join(root, "data", "nes_palette.json"))
    report = nes_check.check(image, "sprite", palette)
    if not report["ok"]:
        raise SystemExit("%s fails nes_check.py:\n%s" % (label, "\n".join(nes_check.describe(report, label))))
    return report


# ----------------------------------------------------------------------------------------------------------------
# The sea battle scene palette, written here so the scene and the cast cannot disagree.
# ----------------------------------------------------------------------------------------------------------------
SCENE_SEA = {
    "format": 1,
    "kind": "scene_palette",
    "scene": "sea",
    "backdrop": 15,
    "rule": "NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, "
            "4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is a "
            "data/nes_palette.json entry number",
    "background": [
        {"name": "bg0", "colours": [0, 16, 48], "hex": ["#7c7c7c", "#bcbcbc", "#fcfcfc"]},
        {"name": "bg1", "colours": [2, 18, 33], "hex": ["#0000bc", "#0058f8", "#3cbcfc"]},
        {"name": "bg2", "colours": [7, 23, 40], "hex": ["#881400", "#e45c10", "#f8b800"]},
        {"name": "bg3", "colours": [12, 2, 18], "hex": ["#004058", "#0000bc", "#0058f8"]},
    ],
    "sprites": [
        {"name": name, "colours": PALETTES[name]["entries"],
         "hex": [PALETTES[name]["hex"][code] for code in ("k", "m", "l")]}
        for name in ("sp0_navy_white", "sp1_brown_gold", "sp2_green", "sp3_sea")
    ],
    "notes": [
        "backdrop $0F black is the hull shadow and the night sea",
        "bg0 steel deck and bulkhead, bg1 open sea, bg2 rust and hazard, bg3 night water",
        "four sprite palettes cover the seven enemies: a battle frame draws one enemy plus the player, "
        "so at most two of the four are on screen at once, which is inside the hardware ceiling",
        "written by tools/art/make_enemies.py; it is not yet wired into tools/check_scene_palettes.py, "
        "whose SCENE_NAMES list still names title and ship",
    ],
}


def write_scene(root, hexes_by_palette, report):
    colours, usable = load_master(root)
    for row in SCENE_SEA["background"] + SCENE_SEA["sprites"]:
        for entry, value in zip(row["colours"], row["hex"]):
            if not 0 <= entry < len(colours):
                raise SystemExit("scene_sea: $%02X is outside the palette" % entry)
            if not usable[entry]:
                raise SystemExit("scene_sea: $%02X is forbidden" % entry)
            if colours[entry] != value.lower():
                raise SystemExit("scene_sea: entry $%02X is %s, the row says %s"
                                 % (entry, colours[entry], value))
    path = os.path.join(root, "data", "palettes", "scene_sea.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(SCENE_SEA, handle, indent=2, sort_keys=True)
        handle.write("\n")
    background = set()
    for row in SCENE_SEA["background"]:
        background.update(row["colours"])
    sprites = set()
    for row in SCENE_SEA["sprites"]:
        sprites.update(row["colours"])
    report["scene"] = {
        "path": "data/palettes/scene_sea.json",
        "backdrop": SCENE_SEA["backdrop"],
        "background_palettes": 4,
        "sprite_palettes": 4,
        "background_colours": len(background),
        "sprite_colours": len(sprites),
        "distinct_colours": len(background | sprites | {SCENE_SEA["backdrop"]}),
        "limit": 25,
    }
    return path


# ----------------------------------------------------------------------------------------------------------------
# The composed battle frame: a 256x240 sea and steel backdrop with one enemy standing on it.
# ----------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------
# The composed battle frame: 16 tile columns x 15 tile rows = 256x240.
# Rows 0..1 sky (bg3), rows 2..3 sea texture (bg1), rows 4..7 flat navy sea (bg1 entry $02),
# rows 8..14 steel deck (bg0). The enemy's feet rest on the deck line at y=128.
# The four attribute blocks the enemy covers sit over the flat navy band, and navy is also one of the enemy's
# three sprite colours, so those blocks carry exactly three colours: navy, black, white. That is the NES habit
# from the card comment (transparent pixels count as an apparent colour), used here to stay inside an
# attribute area without inventing a fifth background palette.
# ----------------------------------------------------------------------------------------------------------------
FRAME_W = 256
FRAME_H = 240
TILE = 16
STARS = ((6, 4), (19, 2), (33, 9), (48, 5), (61, 11), (77, 3), (92, 8), (108, 2), (121, 12), (137, 6),
         (151, 3), (166, 10), (181, 7), (196, 2), (211, 12), (227, 5), (241, 9), (14, 14), (86, 15),
         (155, 14), (203, 15), (236, 14))
ENEMY_X = 112
ENEMY_Y = 96


def bg_entry(x, y):
    """One pixel of the battle background, as a data/nes_palette.json entry number.

    Flat bands, one shared backdrop, and dithering only where two bands meet: a 2 pixel checker, which is the
    only texture the art bible allows. No gradients, no anti aliasing.
    """
    if y < 32:                                     # sky, bg3 = $0C $02 $12
        if (x, y) in STARS:
            return 18
        if y >= 26:                                # the horizon edge, a 2 pixel checker into the sea band
            return 2 if ((x // 2 + y // 2) % 2 == 0) else 12
        return 12
    if y < 64:                                     # sea texture, bg1 = $02 $12 $21
        ry = y % 8
        if ry in (4, 5):
            return 18
        if ry == 6:
            return 18 if (x // 2) % 2 == 0 else 2
        if ry == 0 and (x // 2) % 2 == 1:
            return 33
        return 2
    if y < 128:                                    # flat middle sea: one colour, so the enemy blocks stay at 3
        return 2
    if y == 128:                                   # deck edge highlight, bg0 = $00 $10 $30
        return 48
    if y == 129:
        return 16
    if y in (150, 151):                            # a plank edge, dithered
        return 16 if (x // 2) % 2 == 0 else 0
    if y % 16 == 0:
        return 16
    if (y % 16 == 8) and (x % 32 == 8):
        return 48
    return 0


def build_battle_frame(root, enemy_image):
    colours, _usable = load_master(root)
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 255))
    pixels = frame.load()
    for y in range(FRAME_H):
        for x in range(FRAME_W):
            value = colours[bg_entry(x, y)].lstrip("#")
            pixels[x, y] = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)
    frame.alpha_composite(enemy_image, (ENEMY_X, ENEMY_Y))
    mask = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    mask.paste(enemy_image, (ENEMY_X, ENEMY_Y))
    return frame, mask


def composite_check(root, frame, mask_path, out_dir):
    """Ask tools/nes_composite_check.py to judge the finished frame, background and sprite together."""
    import nes_composite_check as ncc

    palette = ncc.load_palette(os.path.join(root, "data", "nes_palette.json"))
    sprite_data = ncc.load_sprites(frame, mask_path, None, SPRITE_HEIGHT)
    result = ncc.check_frame(frame, palette, (0, 0, 0), sprite_data["sprites"])
    json_path = os.path.join(out_dir, "enemies_composite.json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, default=str)
        handle.write("\n")
    background = result["background"]
    sprite = result["sprite"]
    return {
        "tool": "tools/nes_composite_check.py check_frame()",
        "json": "output/enemies_composite.json",
        "ok": result["ok"],
        "problems": [problem["rule"] for problem in result["problems"]],
        "problem_count": len(result["problems"]),
        "backdrop": result["backdrop"],
        "backdrop_from": result["backdrop_from"],
        "colours_on_screen": result["screen"]["colours"],
        "colours_limit": 25,
        "background_blocks": background["blocks"],
        "background_palette_count": background["palette_count"],
        "background_palettes": background["palettes"],
        "background_offending_blocks": len(background["offending_blocks"]),
        "sprites": sprite["count"],
        "sprite_palette_count": sprite["palette_count"],
        "sprite_palettes": sprite["palettes"],
        "busiest_scanline": sprite["busiest_line"],
        "sprites_on_busiest_scanline": sprite["max_per_line"],
        "sprites_per_scanline_limit": 8,
    }


def sprite_boxes(x, y):
    boxes = []
    for row in range(2):
        for col in range(4):
            boxes.append({"x": x + col * 8, "y": y + row * 16, "w": 8, "h": 16})
    return boxes


# ----------------------------------------------------------------------------------------------------------------
# Contact sheet.
# ----------------------------------------------------------------------------------------------------------------
def rgb(value):
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def label_text(draw, text, x, y, scale, colour):
    for index, ch in enumerate(text.upper()):
        if ch == " ":
            continue
        rows = pressstart2p_font.bitmap(ch)
        for gy, row in enumerate(rows):
            for gx, lit in enumerate(row):
                if lit != "#":
                    continue
                px = x + (index * 8 + gx) * scale
                py = y + gy * scale
                draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=colour)


def contact_sheet(rows, scale):
    """rows: [(label, image)]. One enemy per row, three 32x32 frames side by side, name on the right."""
    margin = 8
    label_w = 150
    cell_w = W * scale + 6
    width = margin + 3 * cell_w + label_w
    height = margin + len(rows) * (H * scale + 12) + margin
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    y = margin
    for label, image in rows:
        big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
        canvas.alpha_composite(big, (margin, y))
        label_text(draw, label, margin + 3 * cell_w + 4, y + 4, scale, rgb("#fcfcfc"))
        label_text(draw, FRAME_NAMES[0], margin + 2, y + H * scale + 1, max(1, scale // 2), rgb("#7c7c7c"))
        label_text(draw, FRAME_NAMES[1], margin + cell_w + 2, y + H * scale + 1, max(1, scale // 2), rgb("#7c7c7c"))
        label_text(draw, FRAME_NAMES[2], margin + 2 * cell_w + 2, y + H * scale + 1, max(1, scale // 2), rgb("#7c7c7c"))
        y += H * scale + 12
    return canvas


def preserved_rows(root, drawn_ids):
    """Roster rows this tool does not draw, read back out of the roster the last run left behind.

    CAST is the complete list of enemies this tool draws a sheet for, and it writes the roster from that list alone.
    deck_hound is the first fight (S6, R05) and has no drawn sheet yet, so its row is hand written in
    data/enemies/roster.json; a plain rebuild would silently delete a row that data/talk_cards.json and the S6
    encounter both name. So any row whose id is not in drawn_ids is carried over verbatim, and the roster's own notes
    say which ones were. Giving the hound a CAST spec and a drawn sheet belongs to the art pass; until then this
    keeps the hand written row instead of forgetting it.
    """
    path = os.path.join(root, "data", "enemies", "roster.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            previous = json.load(handle)
    except (OSError, ValueError):
        return []
    rows = previous.get("enemies") if isinstance(previous, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("id") not in drawn_ids]


# ----------------------------------------------------------------------------------------------------------------
# Build.
# ----------------------------------------------------------------------------------------------------------------
def build(root, dump=False):
    out_dir = os.path.join(root, "game", "sprites_src", "enemies")
    out_preview = os.path.join(root, "output")
    data_dir = os.path.join(root, "data", "enemies")
    for path in (out_dir, out_preview, data_dir):
        os.makedirs(path, exist_ok=True)

    report = {"format": 1, "kind": "enemies_report", "rule": "ART-BIBLE.md section 1, PLAN-V2 section 0",
              "frames": list(FRAME_NAMES), "frame_w": W, "frame_h": H, "fps": FPS,
              "palettes": {}, "enemies": [], "warnings": []}
    hexes_by_palette = {}
    for name in sorted(PALETTES):
        hexes_by_palette[name] = palette_hexes(root, name)
        report["palettes"][name] = {"entries": PALETTES[name]["entries"], "hex": PALETTES[name]["hex"],
                                    "role": PALETTES[name]["role"]}

    if dump:
        for spec in CAST:
            print("== %s (%s)" % (spec["name"], spec["palette"]))
            for frame in enemy_frames(spec):
                print(frame.ascii())
                print()
        return report

    scene_path = write_scene(root, hexes_by_palette, report)
    report["scene"]["file"] = os.path.relpath(scene_path, root).replace(os.sep, "/")

    rows = []
    roster = {"format": 1, "kind": "enemy_roster",
              "rule": "specs/16-talk-command.md card fields; hp here is the battle value, not the final balance table",
              "notes": [
                  "the Navy Sailor card copies the approved card in specs/16-talk-command.md section 10 word for word, "
                  "so the roster cannot contradict the decided spec",
                  "the other six enemies are new here: their voice, wants, fears, weak and strong topics are new data "
                  "and the TALK-CARDS card should turn each one into a full talk card with pools and lines",
                  "mercy_to_spare is trust_to_spare x 20 per specs/16-talk-command.md section 2",
                  "sprite is the GameMaker resource name; for navy_sailor it matches the id already in "
                  "data/enemies/all.json (spr_pp_sailor), so the battle director needs no name change",
              ],
              "sprite_palettes": report["palettes"], "enemies": []}
    battle_frame_drawn = False
    for spec in CAST:
        hexes = hexes_by_palette[spec["palette"]]
        frames = enemy_frames(spec)
        image = sheet_image(frames, hexes)
        check = check_sheet(root, image, spec["file"])
        png_path = os.path.join(out_dir, spec["file"] + ".png")
        image.save(png_path, "PNG")
        meta = {"name": spec["file"], "frame_w": W, "frame_h": H, "frames": len(frames), "fps": FPS,
                "frame_names": list(FRAME_NAMES), "hit_frame": FRAME_NAMES.index("hit"),
                "palette": spec["palette"], "palette_entries": PALETTES[spec["palette"]]["entries"],
                "sprite": spec["sprite"],
                "note": "3 frames left to right: idle0, idle1, hit flash; transparent background"}
        with open(os.path.join(out_dir, spec["file"] + ".json"), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(meta, handle, indent=2)
            handle.write("\n")
        digest = hashlib.sha256(open(png_path, "rb").read()).hexdigest()
        entry = {
            "id": spec["id"], "name": spec["name"], "sprite": spec["sprite"],
            "sheet": "game/sprites_src/enemies/%s.png" % spec["file"],
            "frame_w": W, "frame_h": H, "frames": list(FRAME_NAMES), "fps": FPS,
            "palette": spec["palette"], "palette_entries": PALETTES[spec["palette"]]["entries"],
            "colours": PALETTES[spec["palette"]]["hex"],
            "sha256": digest,
            "nes_check": {"ok": check["ok"], "colours": check.get("colours"), "tiles": check.get("tiles")},
            "hp": spec["hp"], "max_hp": spec["hp"], "role": spec["role"],
            "phase_note": "",
            "trust_to_spare": TRUST_TO_SPARE, "mercy_to_spare": TRUST_TO_SPARE * 20,
            "personality": spec["personality"], "voice": spec["voice"],
            "wants": spec["wants"], "fears": spec["fears"],
            "weak_topics": spec["weak_topics"], "strong_topics": spec["strong_topics"],
        }
        report["enemies"].append(entry)
        roster["enemies"].append({key: entry[key] for key in
                                  ("id", "name", "sprite", "sheet", "palette", "palette_entries",
                                   "colours", "max_hp", "hp", "role", "phase_note", "trust_to_spare",
                                   "mercy_to_spare", "personality", "voice", "wants",
                                   "fears", "weak_topics", "strong_topics")})
        rows.append(("%s  %s" % (spec["name"].upper(), spec["palette"]), image))
        if not battle_frame_drawn:
            frame, mask = build_battle_frame(root, frames[0].to_image(hexes))
            frame_path = os.path.join(out_preview, "enemies_battle_frame.png")
            frame.save(frame_path, "PNG")
            mask_path = os.path.join(out_preview, "enemies_battle_mask.png")
            mask.save(mask_path, "PNG")
            boxes = sprite_boxes(ENEMY_X, ENEMY_Y)
            boxes_path = os.path.join(out_preview, "enemies_battle_sprites.json")
            with open(boxes_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump({"sprites": boxes, "enemy": spec["file"], "note":
                           "8x16 hardware sprites: 4 columns by 2 rows, 4 objects on any scanline"}, handle, indent=2)
                handle.write("\n")
            composite = composite_check(root, frame, mask_path, out_preview)
            report["battle_frame"] = {"file": "output/enemies_battle_frame.png", "enemy": spec["file"],
                                      "mask": "output/enemies_battle_mask.png",
                                      "enemy_origin": [ENEMY_X, ENEMY_Y], "tile_rows": FRAME_H // TILE,
                                      "sprite_boxes": boxes_path, "sprites": len(boxes),
                                      "sprites_per_scanline": 4}
            report["composite"] = composite
            battle_frame_drawn = True

    # Rows this tool draws no sheet for, chiefly deck_hound, are carried over instead of being dropped. See
    # preserved_rows for why that matters, and note that the note names them so a reader can see what is hand kept.
    kept = preserved_rows(root, {spec["id"] for spec in CAST})
    roster["enemies"].extend(kept)
    if kept:
        roster["notes"].append(
            "hand maintained rows, which this tool draws no sheet for, are carried over verbatim from the roster on "
            "disk so a rebuild cannot drop them: %s"
            % ", ".join("%s (%s)" % (row.get("id"), row.get("role", "no role given")) for row in kept))

    with open(os.path.join(data_dir, "roster.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(roster, handle, indent=2)
        handle.write("\n")

    contact4 = contact_sheet(rows, 4)
    contact4_path = os.path.join(out_preview, "enemies_preview.png")
    contact4.save(contact4_path, "PNG")
    contact3 = contact_sheet(rows, 3)
    contact3_path = os.path.join(out_preview, "enemies_preview_3x.png")
    contact3.save(contact3_path, "PNG")
    report["preview"] = {"file_4x": "output/enemies_preview.png", "size_4x": list(contact4.size),
                         "file_3x": "output/enemies_preview_3x.png", "size_3x": list(contact3.size)}
    with open(os.path.join(out_preview, "enemies_report.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="draw the ENEMIES-1 NES battle sprites")
    parser.add_argument("--root", default=os.path.dirname(TOOLS))
    parser.add_argument("--dump", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    report = build(root, dump=args.dump)
    if args.dump:
        return 0
    print("enemies: %d sheets, %d frames each, %dx%d" % (len(report["enemies"]), len(FRAME_NAMES), W, H))
    for entry in report["enemies"]:
        print("  %-14s %-16s hp %-3d %s %s" % (entry["id"], entry["palette"], entry["hp"],
                                               entry["sha256"][:16], "nes_check ok" if entry["nes_check"]["ok"] else "FAIL"))
    scene = report["scene"]
    print("scene: backdrop $%02X, %d background colours + %d sprite colours + 1 = %d of %d"
          % (scene["backdrop"], scene["background_colours"], scene["sprite_colours"],
             scene["distinct_colours"], scene["limit"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
