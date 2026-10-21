#!/usr/bin/env python3
"""Generate the title screen UI art: the logo, the 8x8 font and the menu cursor.

Contract: TITLE-COORD.md (the UI line of the interface contract) and specs/14-title-screen-drive.md, logo
paragraph, night drive addendum. Colours, frame rules, the 1 px outline and the detail budget come from
specs/13-8bit-look.md.

Clean room: every letterform in FONT is drawn here as a 5x7 grid of characters, and the logo is that same grid scaled
by whole numbers and weathered by code in this file. The cursor and the lightning crack are defined here as pixel
sets. Nothing is copied, traced or imported from any commercial game, and nothing outside this repository is read.

Outputs, one horizontal strip plus one JSON per animation, in game/sprites_src/title/:
    spr_pp_title_logo.png    224x56, 2 frames: frame 0 normal, frame 1 gold shimmer
    spr_pp_font8.png         8x8, 44 frames in ASCII order: space ! ' , - . 0-9 : ? A-Z
    spr_pp_menu_cursor.png   8x8, 2 frames: frame 0 lit, frame 1 unlit
Preview: output/title_ui_preview.png, everything at 3x, the logo and the cursor and the font strip alike.

The second O of the logo: PRIMORDIAL holds the first O and PARADOX the second, so the crack is carved across the O of
PARADOX, which is the only reading in which that letter exists.

Determinism: no clock, no unseeded randomness, PNG carries no timestamp, JSON is written with LF endings. Run the
script twice and the sha256 of every file is the same.

Usage:
    python tools/art/make_title_ui.py
    python tools/art/make_title_ui.py --root <repo>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import deque

from PIL import Image

# --------------------------------------------------------------------------------------------------------------
# Palette. Indices into data/palette.json, with the hex each index must hold. If the master palette ever shifts,
# this script stops instead of silently recolouring the art.
# --------------------------------------------------------------------------------------------------------------
INK = 0         # #0b0b0f  the 1 px dark outline and the crack
DIM = 2         # #2e2e3a  the cursor in its unlit frame, preview separators
PAPER = 5       # #c8c8d4  the 8x8 font
STONE = 34      # #75634c  letter body
STONE_LIT = 35  # #a6957c  the lit edge of the stone
GOLD = 40       # #b38f28  the thin gold inlay and the shimmer band

EXPECTED_HEX = {
    INK: "#0b0b0f",
    DIM: "#2e2e3a",
    PAPER: "#c8c8d4",
    STONE: "#75634c",
    STONE_LIT: "#a6957c",
    GOLD: "#b38f28",
}

# --------------------------------------------------------------------------------------------------------------
# The font. 5 wide by 7 tall, '#' is ink, '.' is empty. The cell is 8x8: the glyph sits at column 1, row 0, so every
# cell has a 1 px left margin, a 2 px right margin and a 1 px descender row at the bottom. No glyph touches its cell.
# --------------------------------------------------------------------------------------------------------------
FONT = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
    ",": [".....", ".....", ".....", ".....", ".....", "..#..", ".#..."],
    "-": [".....", ".....", ".....", ".###.", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", "..#.."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    ":": [".....", "..#..", ".....", ".....", ".....", "..#..", "....."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
}

# The contract fixes the frame order: ASCII order, one frame per glyph.
GLYPH_ORDER = sorted(FONT.keys(), key=ord)

GLYPH_W = 5
GLYPH_H = 7
CELL = 8

# --------------------------------------------------------------------------------------------------------------
# Logo. Two lines, each a run of the same 5x7 letters scaled by whole numbers, so a stroke is 4 or 5 px wide and the
# result reads as carved stone rather than as a stretched font.
# --------------------------------------------------------------------------------------------------------------
LOGO_W = 224
LOGO_H = 56

# (text, scale x, scale y, gap between letters, top of the line, tag)
LOGO_LINES = [
    ("PRIMORDIAL", 4, 3, 4, 5, "primordial"),
    ("PARADOX", 5, 3, 6, 30, "paradox"),
]


# --------------------------------------------------------------------------------------------------------------
# Deterministic helpers. String hashing must not use hash(), which is salted per process.
# --------------------------------------------------------------------------------------------------------------
def _digest(*parts) -> int:
    joined = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(joined).digest()[:8], "big")


def load_palette(root: str) -> list[tuple[int, int, int, int]]:
    path = os.path.join(root, "data", "palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    hexes = data["colours"]
    if len(hexes) != 54:
        raise SystemExit("data/palette.json: expected 54 colours, found %d" % len(hexes))
    for index, expected in EXPECTED_HEX.items():
        if hexes[index].lower() != expected:
            raise SystemExit(
                "data/palette.json: index %d is %s, this script draws with %s"
                % (index, hexes[index], expected)
            )
    colours = []
    for value in hexes:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255))
    return colours


# --------------------------------------------------------------------------------------------------------------
# Letters. Scaled per glyph, with the empty columns of a glyph trimmed so the logo is proportional while every
# letter keeps the same 7 row baseline.
# --------------------------------------------------------------------------------------------------------------
def letter_mask(text: str, sx: int, sy: int, gutter: int):
    """Return (mask, total width, [(char, index, x, width)]) for one line of the logo."""
    mask: set[tuple[int, int]] = set()
    pen = 0
    placed: list[tuple[str, int, int, int]] = []
    for index, ch in enumerate(text):
        rows = FONT[ch]
        used = [x for x in range(GLYPH_W) if any(rows[y][x] == "#" for y in range(GLYPH_H))]
        if not used:
            raise SystemExit("glyph %r has no ink, it cannot be drawn in the logo" % ch)
        x0, x1 = used[0], used[-1]
        for y in range(GLYPH_H):
            for x in range(x0, x1 + 1):
                if rows[y][x] != "#":
                    continue
                for dy in range(sy):
                    for dx in range(sx):
                        mask.add((pen + (x - x0) * sx + dx, y * sy + dy))
        width = (x1 - x0 + 1) * sx
        placed.append((ch, index, pen, width))
        pen += width + gutter
    return mask, pen - gutter, placed


def weathered(mask: set[tuple[int, int]], placed: list[tuple[str, int, int, int]], tag: str) -> set[tuple[int, int]]:
    """Chip 2 to 4 px off each letter outline so the stone looks old. Deterministic per letter."""
    out = set(mask)
    for ch, index, x0, width in placed:
        hi = x0 + width - 1
        own = {p for p in out if x0 <= p[0] <= hi}
        if not own:
            continue
        boundary = sorted(
            p for p in own
            if any(
                (p[0] + dx, p[1] + dy) not in own
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                if (dx, dy) != (0, 0)
            )
        )
        rng = random.Random(_digest("chip", tag, ch, index))
        chips = 2 + (index % 3)
        for _ in range(chips):
            if not boundary:
                break
            point = boundary[rng.randrange(len(boundary))]
            out.discard(point)
            neighbour = (point[0] + 1, point[1])
            if neighbour in out and neighbour[0] <= hi:
                out.discard(neighbour)
    return out


def outline_pixels(mask: set[tuple[int, int]]) -> set[tuple[int, int]]:
    ring: set[tuple[int, int]] = set()
    for x, y in mask:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                point = (x + dx, y + dy)
                if point not in mask:
                    ring.add(point)
    return ring


def depth_map(mask: set[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """Distance in 4-neighbour steps from the outside of the letter. 0 is outside, 1 is the outer ring."""
    depth: dict[tuple[int, int], int] = {}
    queue: deque[tuple[int, int]] = deque()
    for x, y in mask:
        if any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            depth[(x, y)] = 1
            queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            point = (x + dx, y + dy)
            if point in mask and point not in depth:
                depth[point] = depth[(x, y)] + 1
                queue.append(point)
    return depth


def thin_to_skeleton(mask: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Zhang-Suen thinning: reduce a set of pixels to its 1 px wide medial line.

    The gold inlay is this line, so it is exactly 1 px wide on every stroke of every letter, at any scale. The
    algorithm is deterministic: it removes pixels in a fixed order until the set stops changing.
    """
    pixels = set(mask)
    if not pixels:
        return pixels
    min_x = min(x for x, _ in pixels)
    max_x = max(x for x, _ in pixels)
    min_y = min(y for _, y in pixels)
    max_y = max(y for _, y in pixels)
    grid = [[0] * (max_x - min_x + 3) for _ in range(max_y - min_y + 3)]
    for x, y in pixels:
        grid[y - min_y + 1][x - min_x + 1] = 1

    def ring(x: int, y: int):
        """The 8 neighbours in order p2..p9, starting north and going clockwise."""
        return (
            grid[y - 1][x], grid[y - 1][x + 1], grid[y][x + 1], grid[y + 1][x + 1],
            grid[y + 1][x], grid[y + 1][x - 1], grid[y][x - 1], grid[y - 1][x - 1],
        )

    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            removals = []
            for row in range(1, len(grid) - 1):
                for col in range(1, len(grid[0]) - 1):
                    if not grid[row][col]:
                        continue
                    p2, p3, p4, p5, p6, p7, p8, p9 = ring(col, row)
                    if not 2 <= p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9 <= 6:
                        continue
                    transitions = 0
                    seq = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
                    for first, second in zip(seq, seq[1:]):
                        if first == 0 and second == 1:
                            transitions += 1
                    if transitions != 1:
                        continue
                    if step == 0:
                        if p2 * p4 * p6 != 0 or p4 * p6 * p8 != 0:
                            continue
                    else:
                        if p2 * p4 * p8 != 0 or p2 * p6 * p8 != 0:
                            continue
                    removals.append((row, col))
            for row, col in removals:
                grid[row][col] = 0
                changed = True
    return {
        (min_x + col - 1, min_y + row - 1)
        for row in range(1, len(grid) - 1)
        for col in range(1, len(grid[0]) - 1)
        if grid[row][col]
    }


def paint_stone(mask: set[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """Stone body, a 1 px lit edge on the outer ring, and a 1 px gold inlay along the middle of every stroke.

    The inlay is the medial line of the letter, so it is exactly 1 px wide on a 4 px stroke and on a 5 px stroke
    alike, which is what "thin gold inlay" asks for.
    """
    depth = depth_map(mask)
    pixels = {p: STONE for p in mask}
    for point, value in depth.items():
        if value == 1:
            pixels[point] = STONE_LIT
    for point in thin_to_skeleton(mask):
        if point in pixels:
            pixels[point] = GOLD
    return pixels


def carve_crack(img: Image.Image, placed: list[tuple[str, int, int, int]], y_offset: int, inlay: int,
                painted: dict[tuple[int, int], int], colours) -> None:
    """A lightning crack across the O of PARADOX.

    The bolt starts in the top bar of the O, breaks out of it, zigzags down across the counter of the letter and
    breaks the bottom bar, so the O reads as split rather than decorated. A gold glint sits in the widest part of
    the break, where a splinter of stone would catch the light.
    """
    targets = [p for p in placed if p[0] == "O"]
    if not targets:
        raise SystemExit("LOGO_LINES no longer contains an O, so the crack has nowhere to go")
    ch, index, x0, width = targets[-1]
    height = GLYPH_H * 3

    # The bolt, in hundredths of the letter box, as (x, y) points. y runs from just above the top bar to just
    # below the bottom bar, x stays inside the width of the O.
    points = [(12, -8), (22, 4), (14, 12), (38, 22), (28, 32), (52, 42),
              (42, 52), (60, 60), (54, 68), (70, 78), (62, 90), (76, 100), (70, 108)]
    path: list[tuple[int, int]] = []
    for (fx, fy), (tx, ty) in zip(points, points[1:]):
        steps = max(abs(tx - fx), abs(ty - fy))
        for step in range(steps + 1):
            path.append((
                x0 + (fx * (width - 1)) // 100 + ((tx - fx) * (width - 1) * step) // (100 * steps),
                y_offset + (fy * height) // 100 + ((ty - fy) * height * step) // (100 * steps),
            ))
    for px, py in path:
        if 0 <= px < LOGO_W and 0 <= py < LOGO_H:
            img.putpixel((px, py), colours[INK])
    # Splinter: a 1 px shard of stone pushed aside by the break, lit gold on its inner face. It only appears where
    # the break runs through solid stone, never in the open counter of the O.
    stone = set()
    for point, colour in painted.items():
        if colour in (STONE, STONE_LIT, GOLD):
            stone.add(point)
    for step in (len(path) // 3, len(path) // 2, (len(path) * 2) // 3):
        px, py = path[step]
        for shard in ((px + 1, py), (px - 1, py), (px, py - 1)):
            if shard in stone:
                img.putpixel(shard, colours[inlay])
                break


def logo_frame(index: int, colours) -> Image.Image:
    img = Image.new("RGBA", (LOGO_W, LOGO_H), (0, 0, 0, 0))
    for text, sx, sy, gutter, top, tag in LOGO_LINES:
        mask, width, placed = letter_mask(text, sx, sy, gutter)
        mask = weathered(mask, placed, tag)
        x_offset = (LOGO_W - width) // 2
        shifted = {(x + x_offset, y + top) for x, y in mask}
        placed = [(ch, i, x_offset + x0, w) for ch, i, x0, w in placed]
        for x, y in outline_pixels(shifted):
            if 0 <= x < LOGO_W and 0 <= y < LOGO_H:
                img.putpixel((x, y), colours[INK])
        painted = paint_stone(shifted)
        for point, colour in painted.items():
            x, y = point
            if 0 <= x < LOGO_W and 0 <= y < LOGO_H:
                img.putpixel((x, y), colours[colour])
        if tag == "paradox":
            carve_crack(img, placed, top, GOLD, painted, colours)
    if index:
        # Shimmer: one diagonal band of light sweeps the stone and turns it to gold. The band is a single stripe
        # across the whole logo, not a repeating pattern, so it reads as a pass of light.
        pixels = img.load()
        for y in range(LOGO_H):
            for x in range(LOGO_W):
                if pixels[x, y][3] == 0 or pixels[x, y] == colours[INK]:
                    continue
                if 96 <= x + y <= 108:
                    pixels[x, y] = colours[GOLD]
    return img


# --------------------------------------------------------------------------------------------------------------
# Font strip and cursor.
# --------------------------------------------------------------------------------------------------------------
def glyph_frame(ch: str, colours) -> Image.Image:
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    rows = FONT[ch]
    for y in range(GLYPH_H):
        for x in range(GLYPH_W):
            if rows[y][x] == "#":
                img.putpixel((1 + x, y), colours[PAPER])
    return img


# Cursor: an original solid arrowhead pointed right, 6 px wide and 6 rows tall, 1 px dark outline all round, so the
# body sits inside the 8x8 cell with the outline on the last row and column. Blink 15 steps on, 15 off (spec 13),
# so the two frames are the lit and the unlit state.
CURSOR_BODY = [(1, 1), (2, 1),
               (1, 2), (2, 2), (3, 2),
               (1, 3), (2, 3), (3, 3), (4, 3),
               (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
               (1, 5), (2, 5), (3, 5), (4, 5),
               (1, 6), (2, 6), (3, 6)]


def cursor_frame(index: int, colours) -> Image.Image:
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    body = set(CURSOR_BODY)
    for x, y in body:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                point = (x + dx, y + dy)
                if point in body:
                    continue
                if 0 <= point[0] < CELL and 0 <= point[1] < CELL:
                    img.putpixel(point, colours[INK])
    fill = GOLD if index == 0 else DIM
    for x, y in body:
        img.putpixel((x, y), colours[fill])
    return img


def strip(frames: list[Image.Image]) -> Image.Image:
    width, height = frames[0].size
    out = Image.new("RGBA", (width * len(frames), height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        out.paste(frame, (index * width, 0))
    return out


# --------------------------------------------------------------------------------------------------------------
# Preview: everything at 3x on the night sky colour, labelled in our own font so the director can judge it.
# --------------------------------------------------------------------------------------------------------------
def draw_text(dst: Image.Image, text: str, x: int, y: int, scale: int, colour) -> None:
    for index, ch in enumerate(text.upper()):
        rows = FONT.get(ch)
        if rows is None:
            raise SystemExit("preview text uses a glyph the font does not have: %r" % ch)
        for gy in range(GLYPH_H):
            for gx in range(GLYPH_W):
                if rows[gy][gx] != "#":
                    continue
                left = x + (index * (GLYPH_W + 1) + gx) * scale
                top = y + gy * scale
                dst.paste(colour, (left, top, left + scale, top + scale))


def upscale(img: Image.Image, factor: int) -> Image.Image:
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def build_preview(logo: list[Image.Image], font_sheet: Image.Image, cursor: list[Image.Image],
                  colours) -> Image.Image:
    canvas = Image.new("RGBA", (1152, 784), colours[6])
    draw_text(canvas, "PRIMORDIAL PARADOX TITLE UI TS-A AT 3X", 24, 16, 2, colours[PAPER])
    canvas.paste(colours[DIM], (24, 44, 1128, 45))
    draw_text(canvas, "SPR PP TITLE LOGO 224X56 FRAME 0 NORMAL", 24, 54, 2, colours[GOLD])
    canvas.alpha_composite(upscale(logo[0], 3), (48, 76))
    draw_text(canvas, "FRAME 1 GOLD SHIMMER", 24, 248, 2, colours[GOLD])
    canvas.alpha_composite(upscale(logo[1], 3), (48, 268))
    canvas.paste(colours[DIM], (24, 444, 1128, 445))
    draw_text(canvas, "SPR PP FONT8 8X8 44 GLYPHS ASCII ORDER AT 3X", 24, 454, 2, colours[GOLD])
    canvas.alpha_composite(upscale(font_sheet, 3), (48, 474))
    draw_text(canvas, "PRESS Z OR ENTER", 48, 512, 2, colours[PAPER])
    draw_text(canvas, "SPR PP MENU CURSOR 8X8 BY 2 FRAME 0 AND 1 AT 3X", 24, 540, 2, colours[GOLD])
    canvas.alpha_composite(upscale(cursor[0], 3), (48, 560))
    canvas.alpha_composite(upscale(cursor[1], 3), (88, 560))
    cursor_big = upscale(cursor[0], 2)
    rows = ["NEW GAME", "CONTINUE", "SETTINGS", "QUIT"]
    for index, row in enumerate(rows):
        top = 560 + index * 26
        if index == 0:
            canvas.alpha_composite(cursor_big, (136, top))
        draw_text(canvas, row, 162, top + 2, 2, colours[PAPER])
    draw_text(canvas, "ALL COLOURS FROM DATA PALETTE JSON MAX 16 PER SPRITE", 24, 736, 2, colours[STONE_LIT])
    draw_text(canvas, "TWO RUNS SAME HASHES", 24, 760, 2, colours[STONE_LIT])
    return canvas


# --------------------------------------------------------------------------------------------------------------
# Writing and checking.
# --------------------------------------------------------------------------------------------------------------
def write_sprite(out_dir: str, name: str, frames: list[Image.Image], fps: float) -> dict:
    frame_w, frame_h = frames[0].size
    sheet = strip(frames)
    png_path = os.path.join(out_dir, name + ".png")
    json_path = os.path.join(out_dir, name + ".json")
    sheet.save(png_path, "PNG")
    meta = {
        "name": name,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "frames": len(frames),
        "fps": fps,
    }
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    return meta


def check_sprite(png_path: str, meta: dict, palette_hex: set[str]) -> int:
    """Reopen the strip: every visible pixel must be an exact master palette colour, and the count must be small."""
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
    expected = (meta["frame_w"] * meta["frames"], meta["frame_h"])
    if sheet.size != expected:
        raise SystemExit("%s: size %s, contract expects %s" % (png_path, sheet.size, expected))
    seen: set[str] = set()
    # Pillow 14 drops getdata(); get_flattened_data is the replacement, with the old call as a fallback.
    if hasattr(sheet, "get_flattened_data"):
        pixels = sheet.get_flattened_data()
    else:
        pixels = sheet.getdata()
    for r, g, b, a in pixels:
        if a == 0:
            continue
        value = "#%02x%02x%02x" % (r, g, b)
        if value not in palette_hex:
            raise SystemExit("%s: pixel %s is not in data/palette.json" % (png_path, value))
        seen.add(value)
    if len(seen) > 16:
        raise SystemExit("%s: %d colours, the room cap is 16" % (png_path, len(seen)))
    return len(seen)


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def generate(root: str) -> int:
    """Write the title art into a repository root and check it. Returns 0 when every sprite passes.

    This is the whole job, separated from the command line so that a caller can run it in process. The test suite
    calls this directly, because a child process spawn is the one step that can fail for reasons that have nothing to
    do with the art: a Windows spawn can fail with "The request is not supported" (WinError 50) when another test has
    left the process in an odd state, and the failure then looks like a fault in the art when it is a fault in the
    harness.
    """
    root = os.path.abspath(root)

    colours = load_palette(root)
    palette_hex = {"#%02x%02x%02x" % (r, g, b) for r, g, b, _ in colours}

    out_dir = os.path.join(root, "game", "sprites_src", "title")
    preview_dir = os.path.join(root, "output")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(preview_dir, exist_ok=True)

    logo = [logo_frame(0, colours), logo_frame(1, colours)]
    font_frames = [glyph_frame(ch, colours) for ch in GLYPH_ORDER]
    cursor = [cursor_frame(0, colours), cursor_frame(1, colours)]

    if logo[0].size != (LOGO_W, LOGO_H):
        raise SystemExit("logo frame is %s, contract says 224x56" % (logo[0].size,))

    written = [
        write_sprite(out_dir, "spr_pp_title_logo", logo, 0.25),
        write_sprite(out_dir, "spr_pp_font8", font_frames, 0.0),
        write_sprite(out_dir, "spr_pp_menu_cursor", cursor, 4.0),
    ]

    font_sheet = strip(font_frames)
    preview = build_preview(logo, font_sheet, cursor, colours)
    preview_path = os.path.join(preview_dir, "title_ui_preview.png")
    preview.save(preview_path, "PNG")

    print("make_title_ui: %d glyphs in ASCII order: %s" % (len(GLYPH_ORDER), "".join(GLYPH_ORDER)))
    failures = 0
    for meta in written:
        png_path = os.path.join(out_dir, meta["name"] + ".png")
        try:
            count = check_sprite(png_path, meta, palette_hex)
        except SystemExit as exc:
            print("FAIL %s" % exc)
            failures += 1
            continue
        print(
            "  %-22s %3dx%-3d %2d frames  %2d colours  %s"
            % (meta["name"], meta["frame_w"], meta["frame_h"], meta["frames"], count, sha256(png_path))
        )
    print("  preview                %3dx%-3d 3x    %s" % (preview.width, preview.height, sha256(preview_path)))

    if failures:
        print("\n%d sprite(s) failed the palette check" % failures)
        return 1
    print("\nevery sprite uses at most 16 colours and every colour is an exact data/palette.json entry")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--root", default=default_root, help="repository root (default: two levels above this file)")
    args = parser.parse_args()
    return generate(args.root)


if __name__ == "__main__":
    sys.exit(main())
