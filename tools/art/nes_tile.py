#!/usr/bin/env python3
"""Shared helpers for the title art lane: the master palette, the NES tile rule and some pixel primitives.

Clean room: every shape here is generated from numbers in this repository. Nothing is imported from, traced
out of, or copied from any existing game. The primitives are plain geometry (distance fields, Bresenham style
thick lines, annulus sectors) written for this project.

The NES tile rule, as the plan states it: a sprite tile is 8x8 and may carry at most 3 colours plus
transparency. A sprite may use more than 3 colours overall, but no single 8x8 tile may exceed 3. That is what
tile_reduce() enforces, deterministically, with a per sprite priority list, so a drawing that is a little too
busy still lands on the cartridge limit.

Usage:
    python tools/art/nes_tile.py <repo root> [sprite name ...]
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import deque

from PIL import Image


def load_palette(root: str):
    """Return (colours, index_of) where colours is a list of (r, g, b, a) and index_of maps rgb to the index."""
    path = os.path.join(root, "data", "palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    hexes = data["colours"]
    colours = []
    index_of = {}
    for index, value in enumerate(hexes):
        value = value.lstrip("#")
        rgb = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
        colours.append(rgb + (255,))
        index_of[rgb] = index
    return colours, index_of


def load_nes_palette(root: str):
    """Return (colours, index_of) for the real 2C02 palette, indexed by PPU entry number ($00 to $3F).

    This is the palette the cartridge can actually output, and the one tools\\nes_check.py validates against
    (data\\nes_palette.json). The older load_palette() above reads data\\palette.json, the project's own working
    palette; new art should use this one so a sprite passes the validator as drawn.
    """
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = []
    for value in data["colours"]:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255))
    index_of = {}
    for entry in data.get("entries", []):
        if not entry.get("usable"):
            continue
        value = entry["hex"].lstrip("#")
        index_of[(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))] = entry["index"]
    return colours, index_of


# -----------------------------------------------------------------------------------------------------------------
# The tile rule.

def tile_colours(image: Image.Image, frame_w: int, frame_h: int, index_of) -> dict:
    """Every 8x8 tile of every frame, with the palette indices it carries. Key: (frame, tx, ty)."""
    out = {}
    frames = image.width // frame_w
    for frame in range(frames):
        for ty in range(frame_h // 8):
            for tx in range(frame_w // 8):
                seen = set()
                for y in range(ty * 8, ty * 8 + 8):
                    for x in range(tx * 8, tx * 8 + 8):
                        pixel = image.getpixel((frame * frame_w + x, y))
                        if pixel[3] == 0:
                            continue
                        seen.add(index_of.get(pixel[:3]))
                if seen:
                    out[(frame, tx, ty)] = seen
    return out


def tile_reduce(image: Image.Image, frame_w: int, frame_h: int, index_of, colours, priority) -> tuple:
    """Force every 8x8 tile down to 3 colours, keeping the ones the priority list names first.

    The colours a tile drops are remapped to the nearest colour the tile kept, in RGB distance, so the drawing
    stays readable. Deterministic: the priority list is fixed and the nearest colour is unique unless two kept
    colours are exactly the same distance, in which case the lower index wins.

    Returns (new image, number of pixels changed).
    """
    rgb_of = {index: colours[index][:3] for index in range(len(colours))}
    rank = {index: order for order, index in enumerate(priority)}
    pixels = image.load()
    changed = 0
    frames = image.width // frame_w
    for frame in range(frames):
        for ty in range(frame_h // 8):
            for tx in range(frame_w // 8):
                seen = set()
                for y in range(ty * 8, ty * 8 + 8):
                    for x in range(tx * 8, tx * 8 + 8):
                        pixel = pixels[frame * frame_w + x, y]
                        if pixel[3] == 0:
                            continue
                        seen.add(index_of.get(pixel[:3]))
                if len(seen) <= 3 or not seen:
                    continue
                keep = sorted(seen, key=lambda index: (rank.get(index, 99), index))[:3]
                keep_rgb = {index: rgb_of[index] for index in keep}
                for y in range(ty * 8, ty * 8 + 8):
                    for x in range(tx * 8, tx * 8 + 8):
                        pixel = pixels[frame * frame_w + x, y]
                        if pixel[3] == 0:
                            continue
                        index = index_of.get(pixel[:3])
                        if index in keep:
                            continue
                        best = min(keep, key=lambda k: (
                            sum((a - b) ** 2 for a, b in zip(rgb_of[index], keep_rgb[k])), k))
                        pixels[frame * frame_w + x, y] = colours[best]
                        changed += 1
    return image, changed


def over_limit(image: Image.Image, frame_w: int, frame_h: int, index_of, limit: int = 3) -> list:
    """The tiles that carry more than limit colours. Each entry is (frame, tx, ty, count)."""
    bad = []
    for (frame, tx, ty), seen in tile_colours(image, frame_w, frame_h, index_of).items():
        if len(seen) > limit:
            bad.append((frame, tx, ty, len(seen)))
    return bad


def solid_alpha(image: Image.Image) -> Image.Image:
    """Turn every partial alpha pixel into a pixel the PPU can draw.

    A NES sprite pixel is on or off: there is no 110/255. The art uses partial alpha for two honest reasons (a
    puff thinning as it leaves the pipe, a cloud dissolving as it fades), and the hardware way to say "half
    covered" is a one pixel checker, so that is what this does:

        alpha 192 and up   solid, it was meant to be opaque
        alpha 96 to 191    a 2 pixel checker: solid where (x + y) is even, transparent elsewhere
        alpha under 96     transparent, it was meant to be gone

    A checker spends no colour the palette does not have, so a fade still reads as a fade; what stops is shipping
    pixels the chip cannot output. tools\\nes_check.py refuses any pixel whose alpha is not 0 or 255, so a strip
    with a half transparent pixel in it fails the palette rule, which is how these files were measured.
    """
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a == 0 or a == 255:
                continue
            if a >= 192:
                pixels[x, y] = (r, g, b, 255)
            elif a < 96 or (x + y) % 2:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (r, g, b, 255)
    return out


# -----------------------------------------------------------------------------------------------------------------
# Pixel primitives.

def thick_line(points, width: int) -> set:
    """A line of the given width through the points, as a set of pixels."""
    radius = max(0, width // 2)
    out = set()
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0))
        if steps == 0:
            steps = 1
        for step in range(steps + 1):
            px = x0 + (x1 - x0) * step // steps
            py = y0 + (y1 - y0) * step // steps
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    out.add((px + dx, py + dy))
    return out


def arc_band(cx: float, cy: float, r_out: float, r_in: float, a0: float, a1: float) -> set:
    """An annulus sector, angles in degrees, screen coordinates with y pointing down."""
    out = set()
    for y in range(int(cy - r_out) - 1, int(cy + r_out) + 2):
        for x in range(int(cx - r_out) - 1, int(cx + r_out) + 2):
            dx = x - cx
            dy = y - cy
            radius = math.hypot(dx, dy)
            if not (r_in <= radius <= r_out):
                continue
            angle = math.degrees(math.atan2(dy, dx)) % 360.0
            low, high = (a0, a1) if a0 <= a1 else (a1, a0)
            inside = low <= angle <= high if a0 <= a1 else (angle >= low or angle <= high)
            if inside:
                out.add((x, y))
    return out


def outline_of(mask: set) -> set:
    """The 8 neighbour ring around a set of pixels."""
    ring = set()
    for x, y in mask:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                point = (x + dx, y + dy)
                if point not in mask:
                    ring.add(point)
    return ring


def thin_to_skeleton(mask: set) -> set:
    """Zhang-Suen thinning: reduce a set of pixels to its 1 px wide medial line. Deterministic."""
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


def depth_map(mask: set) -> dict:
    """Distance in 4 neighbour steps from the outside of the shape. 1 is the outer ring."""
    depth = {}
    queue = deque()
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


def sha256(path: str) -> str:
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root = os.path.abspath(root)
    colours, index_of = load_palette(root)
    names = sys.argv[2:]
    if not names:
        sprite_dir = os.path.join(root, "game", "sprites_src", "title")
        names = sorted(
            os.path.splitext(f)[0] for f in os.listdir(sprite_dir)
            if f.endswith(".png"))
    failures = 0
    for name in names:
        png_path = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        json_path = png_path[:-4] + ".json"
        if not os.path.isfile(png_path):
            print("%-24s MISSING" % name)
            failures += 1
            continue
        with open(json_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        with Image.open(png_path) as img:
            sheet = img.convert("RGBA")
        bad = over_limit(sheet, meta["frame_w"], meta["frame_h"], index_of)
        status = "OK" if not bad else "FAIL %d tiles over 3 colours (max %d)" % (
            len(bad), max(b[3] for b in bad))
        print("%-24s %3dx%-3d %2d frames  %s" % (name, meta["frame_w"], meta["frame_h"], meta["frames"], status))
        for entry in bad[:8]:
            print("      frame %d tile %d,%d has %d colours" % entry)
        if bad:
            failures += 1
    if failures:
        print("\n%d sprite(s) break the 8x8 tile rule" % failures)
        return 1
    print("\nevery sprite keeps 3 colours plus transparency in every 8x8 tile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
