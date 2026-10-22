"""nes_composite_check.py: does this whole frame obey the NES drawing rules, background and sprites together?

nes_check.py checks a single sprite sheet or a single background image. This tool checks one finished frame,
the thing the player actually sees, and it checks the two layers against each other, because a frame can pass
each layer alone and still be impossible on a NES: five background palettes, a sprite drawn in its own private
colours, nine sprites stacked on one scanline.

The rules, and where each comes from (NESdev wiki, read 2026-10-21):

1. Palette membership (wiki, "PPU palettes", https://www.nesdev.org/wiki/PPU_palettes). Every visible pixel is
   one of the PPU's 64 outputs, $00 to $3F. The list is data\\nes_palette.json, built and cited by
   tools\\art\\nes_palette_build.py; entries flagged usable false (the forbidden $0D and the duplicate blacks
   other than $0F) are refused, because a frame drawn with them is not reproducible on the chip.
2. Background palette groups (wiki, "PPU palettes": background palette RAM is 4 groups of 3 colours plus the
   universal backdrop colour at $3F00). Each 16x16 attribute area may use at most 3 colours besides the one
   backdrop colour shared by the whole frame.
3. Background palette count. There are 4 background groups, so the whole frame may need at most 4 distinct
   palettes, a palette being a set of 3 colours. A block that uses 2 colours is compatible with any group that
   contains them, so the check is a set cover: can 4 groups of 3 cover every block? A frame with 5 unrelated
   colour sets fails even though every block is small.
4. Sprite tile colours (wiki, "PPU OAM" and "PPU palettes": a sprite pixel selects one of 4 entries in one of
   4 sprite groups, entry 0 is transparent). One sprite carries at most 3 opaque colours plus transparency.
   Checked only when a sprite mask or a sprite list is given, because a photograph of a frame cannot say which
   pixel belongs to which sprite.
5. Sprite palette count. Four sprite groups, so at most 4 distinct sprite palettes in the frame, same set cover
   as the background.
6. Sprites per scanline and in total (wiki, "PPU OAM": 64 bytes of OAM, 8 sprites per scanline, the rest are
   dropped and the line flickers). At most 8 sprites cover any one of the 240 scanlines and at most 64 in the
   frame. An 8x16 sprite is one sprite, not two, because it is one OAM entry.
7. Colours on screen. 4 background palettes of 3 plus 4 sprite palettes of 3 plus the one backdrop is 25, which
   is the ceiling a NES frame can show.

Input. A frame PNG at 256x240 (scale 1), a 768x720 capture (scale 3, downsampled by nearest), or any window
screenshot that contains a 3x viewport somewhere inside it: --crop auto finds the viewport by asking which
offset makes the pixels legal PPU colours, then downsamples that. An animated GIF is read one frame at a time
(--frame).

Output. A text report naming every offending block or sprite with its coordinates, an optional JSON report,
and an overlay PNG that marks them (--overlay out.png, drawn at 3x so the marks are visible). Exit 0 when the
frame is legal, 1 when it is not, 2 when the input cannot be read at all. A failing run is the point of the
tool: read the list, repaint those blocks, run it again.

Usage:
    python tools\\nes_composite_check.py output\\title_run_1.png --crop auto --overlay output\\_frame_overlay.png
    python tools\\nes_composite_check.py frame.png --sprite-mask mask.png --sprite-height 16 --json r.json
    python tools\\nes_composite_check.py frame.png --sprites sprites.json --backdrop "#000000"
    python tools\\nes_composite_check.py output\\title_scene_preview.gif --frame 0

What this tool does not do: it does not judge the art, and it cannot tell which sprite owns which pixel unless
you pass a mask or a list. tools\\nes_enforce.py takes a frame that fails these rules and rewrites it into one
that passes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image

FRAME_W = 256
FRAME_H = 240
AREA = 16
TILE = 8
MAX_BG_PALETTES = 4
MAX_SPRITE_PALETTES = 4
MAX_SPRITES_PER_LINE = 8
MAX_SPRITES = 64
MAX_COLOURS_ON_SCREEN = 25
SCANLINES = FRAME_H

OVERLAY_SCALE = 3
MARK_BACKGROUND = (255, 0, 0, 255)     # a 2 pixel red frame around a bad 16x16 block
MARK_SPRITE = (255, 255, 0, 255)       # a yellow frame around a bad sprite
MARK_PALETTE = (255, 0, 255, 255)      # magenta dot: three or more blocks disagree about the palette budget


# -----------------------------------------------------------------------------------------------------------------
# Palette and colour helpers.

def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_palette_path(root: str) -> str:
    """The art bible wins when it exists, because it is the project's chosen working subset."""
    bible = os.path.join(root, "data", "art_bible.json")
    if os.path.isfile(bible):
        return bible
    return os.path.join(root, "data", "nes_palette.json")


def load_palette(path: str) -> dict:
    """Read a palette file into {"allowed": {rgb: (index, "#rrggbb")}, "count": n, "refused": {rgb: why}}."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = data.get("colours") or data.get("palette")
    if not isinstance(colours, list) or not colours:
        raise ValueError("%s has no colours list" % path)
    entries = data.get("entries")
    if isinstance(entries, list) and len(entries) == len(colours):
        usable_flags = [bool(entry.get("usable", True)) if isinstance(entry, dict) else True for entry in entries]
    else:
        usable_flags = [True] * len(colours)
    allowed = {}
    refused = {}
    for index, value in enumerate(colours):
        rgb = hex_to_rgb(value)
        if usable_flags[index]:
            allowed.setdefault(rgb, (index, "#%02x%02x%02x" % rgb))
        else:
            refused.setdefault(rgb, "entry $%02X is flagged unusable in %s" % (index, os.path.basename(path)))
    if not allowed:
        raise ValueError("%s has no usable colours" % path)
    return {"allowed": allowed, "refused": refused, "count": len(allowed), "raw_count": len(colours), "path": path}


def hex_to_rgb(value: str) -> tuple:
    text = value.strip().lower().lstrip("#")
    if len(text) != 6:
        raise ValueError("%r is not a #RRGGBB colour" % value)
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def parse_colour(text: str, palette: dict) -> tuple:
    """A colour given as #RRGGBB, RRGGBB, or an entry number as $0F or 15."""
    value = text.strip().lower()
    if value.startswith("$") or value.isdigit():
        index = int(value.lstrip("$"), 16 if value.startswith("$") else 10)
        entries = palette.get("entries")
        if isinstance(entries, list) and 0 <= index < len(entries):
            entry = entries[index]
            return hex_to_rgb(entry["hex"] if isinstance(entry, dict) else entry)
        raise ValueError("entry %s is not in the palette file" % text)
    return hex_to_rgb(value)


def rgb_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(rgb[:3])


def nearest(rgb, choices) -> tuple:
    """The closest colour in choices by squared RGB distance; ties go to the lower colour value."""
    best = None
    best_distance = None
    for choice in choices:
        distance = sum((int(a) - int(b)) ** 2 for a, b in zip(rgb[:3], choice[:3]))
        if best_distance is None or distance < best_distance or (distance == best_distance and choice < best):
            best, best_distance = choice, distance
    return best


# -----------------------------------------------------------------------------------------------------------------
# Loading a frame at 256x240, scale 1.

def find_viewport(image: Image.Image, allowed, width: int = FRAME_W, height: int = FRAME_H,
                  scale: int = 3, threshold: float = 0.90) -> dict:
    """Locate a width*scale by height*scale viewport inside a window screenshot.

    A window capture carries its own chrome: title bar, borders, maybe desktop. The game viewport is the box whose
    pixels are PPU colours, so the search is over offsets and the score is 'what fraction of this box is legal
    colour'. The score is exact, every pixel in the candidate box, computed for every offset from one summed-area
    table of 'illegal pixel' counts, because a sampled score is noise dominated: 7 columns of window border are
    only 2 samples out of 85 at a stride of 3, so a misaligned crop can outscore the aligned one.
    Returns {"box": (ox, oy, w, h), "score": float, "legal": float}. Raises ValueError when nothing scores above
    the threshold, which means the capture is not a frame of this game and guessing would be worse than failing.
    """
    pixels = image.load()
    span_x = image.width - width * scale
    span_y = image.height - height * scale
    if span_x < 0 or span_y < 0:
        raise ValueError("image %dx%d is smaller than the %dx viewport %dx%d"
                         % (image.width, image.height, scale, width * scale, height * scale))
    columns = image.width + 1
    sums = [0] * (columns * (image.height + 1))
    for y in range(image.height):
        row_before = 0
        base = (y + 1) * columns
        previous = y * columns
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            row_before += 0 if ((r, g, b) in allowed or a == 0) else 1
            sums[base + x + 1] = sums[previous + x + 1] + row_before

    def illegal_in(ox, oy, w, h):
        x1, y1 = ox + w, oy + h
        return (sums[y1 * columns + x1] - sums[oy * columns + x1]
                - sums[y1 * columns + ox] + sums[oy * columns + ox])

    area = width * scale * height * scale
    best = None
    for oy in range(0, span_y + 1):
        for ox in range(0, span_x + 1):
            bad = illegal_in(ox, oy, width * scale, height * scale)
            if best is None or bad < best[0]:
                best = (bad, ox, oy)
    bad, ox, oy = best
    legal = 1.0 - bad / area
    if legal < threshold:
        raise ValueError("no %dx viewport found inside %dx%d (best offset %d,%d is %.3f legal colours, need %.2f); "
                         "pass --crop x,y or --crop 1" % (scale, image.width, image.height, ox, oy, legal, threshold))
    return {"box": (ox, oy, width * scale, height * scale), "score": round(legal, 6), "legal": legal}


def downsample(image: Image.Image, box, scale: int, width: int = FRAME_W, height: int = FRAME_H) -> Image.Image:
    """Nearest neighbour: take the centre pixel of each scale x scale cell, never blend, because blending invents
    colours that are not on the chip."""
    if scale == 1 and box[0] == 0 and box[1] == 0 and image.size == (width, height):
        return image.copy()
    source = image.load()
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    target = out.load()
    off = scale // 2
    for y in range(height):
        for x in range(width):
            target[x, y] = source[box[0] + x * scale + off, box[1] + y * scale + off]
    return out


def load_frame(path: str, allowed, crop: str = "auto", frame_index: int | None = None) -> tuple:
    """Read a frame at 256x240 scale 1, plus a note saying how it was found."""
    if not os.path.isfile(path):
        raise ValueError("%s does not exist" % path)
    with Image.open(path) as handle:
        info = {"path": os.path.abspath(path), "source_size": list(handle.size), "format": handle.format}
        frames = getattr(handle, "n_frames", 1)
        info["frames"] = frames
        if frames > 1:
            index = 0 if frame_index is None else frame_index
            if index >= frames:
                raise ValueError("%s has %d frames, so frame %d does not exist" % (path, frames, index))
            handle.seek(index)
            info["frame"] = index
        image = handle.convert("RGBA")

    if crop not in ("auto", None):
        text = str(crop).strip().lower()
        if text == "1":
            if image.width < FRAME_W or image.height < FRAME_H:
                raise ValueError("%s is %dx%d, smaller than one frame" % (path, image.width, image.height))
            frame = downsample(image, (0, 0, FRAME_W, FRAME_H), 1)
            info.update({"scale": 1, "crop": [0, 0, FRAME_W, FRAME_H], "crop_how": "--crop 1"})
            return frame, info
        if text == "3":
            if image.width < FRAME_W * 3 or image.height < FRAME_H * 3:
                raise ValueError("%s is %dx%d, smaller than a 3x frame" % (path, image.width, image.height))
            frame = downsample(image, (0, 0, FRAME_W * 3, FRAME_H * 3), 3)
            info.update({"scale": 3, "crop": [0, 0, FRAME_W * 3, FRAME_H * 3], "crop_how": "--crop 3"})
            return frame, info
        try:
            ox, oy = [int(part) for part in text.replace(" ", "").split(",")]
        except ValueError:
            raise ValueError("--crop takes auto, 1, 3 or x,y; got %r" % crop) from None
        found = {"box": (ox, oy, FRAME_W * 3, FRAME_H * 3), "score": None}
        scale = 3
    elif image.size == (FRAME_W, FRAME_H):
        frame = downsample(image, (0, 0, FRAME_W, FRAME_H), 1)
        info.update({"scale": 1, "crop": [0, 0, FRAME_W, FRAME_H], "crop_how": "already 256x240"})
        return frame, info
    elif image.size == (FRAME_W * 3, FRAME_H * 3):
        frame = downsample(image, (0, 0, FRAME_W * 3, FRAME_H * 3), 3)
        info.update({"scale": 3, "crop": [0, 0, FRAME_W * 3, FRAME_H * 3], "crop_how": "already 768x720"})
        return frame, info
    else:
        found = find_viewport(image, allowed)
        scale = 3

    box = found["box"]
    if box[0] + box[2] > image.width or box[1] + box[3] > image.height:
        raise ValueError("crop box %s does not fit inside %dx%d" % (list(box), image.width, image.height))
    frame = downsample(image, box, scale)
    info.update({"scale": scale, "crop": list(box), "crop_how": "viewport search" if found["score"] is not None
                 else "given"})
    if found["score"] is not None:
        info["crop_score"] = round(found["score"], 4)
    return frame, info


# -----------------------------------------------------------------------------------------------------------------
# Reading the frame.

def frame_pixels(image: Image.Image) -> list:
    """Pixels in raster order, flattened so the rule loops run over ints instead of tuples."""
    return [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]


def block_colours(image: Image.Image) -> dict:
    """{(bx, by): Counter{rgb: pixels}} for every 16x16 attribute area."""
    pixels = image.load()
    blocks = {}
    for by in range(0, image.height, AREA):
        for bx in range(0, image.width, AREA):
            counter = Counter()
            for y in range(by, min(by + AREA, image.height)):
                for x in range(bx, min(bx + AREA, image.width)):
                    r, g, b, a = pixels[x, y]
                    if a:
                        counter[(r, g, b)] += 1
            blocks[(bx, by)] = counter
    return blocks


def choose_backdrop(frame: Image.Image, blocks: dict, declared=None) -> tuple:
    """The frame wide backdrop colour.

    A picture cannot say which colour sits in $3F00: the PPU draws the backdrop where no tile or sprite covers a
    pixel, so the honest question is whether SOME choice of backdrop makes the frame legal. The most common colour
    is the usual answer and the right one for a painted scene, but not always: a palette can be full of a colour
    that outscores the true backdrop by pixel count. So the candidates are the eight most common colours and a
    declared one wins outright; the winner is the one with the fewest offending blocks, ties going to the colour
    that covers more pixels.
    """
    if declared is not None:
        return tuple(declared), "declared"
    counts = Counter()
    pixels = frame.load()
    for y in range(frame.height):
        for x in range(frame.width):
            r, g, b, a = pixels[x, y]
            if a:
                counts[(r, g, b)] += 1
    if not counts:
        return None, "the frame is empty"
    best = None
    for rank, (colour, count) in enumerate(counts.most_common(8)):
        result = check_background_blocks(blocks, colour)
        palette_bad = sum(1 for problem in result["problems"] if problem["rule"] == "background_palettes")
        score = (len(result["offending_blocks"]) + 10 * palette_bad, -count)
        if best is None or score < best[0]:
            best = (score, colour, rank)
    _, colour, rank = best
    how = "the most common colour in the frame" if rank == 0 else \
        "the %s most common colour, chosen because it leaves fewer blocks offending" % ("2nd" if rank == 1 else
                                                                                        "%dth" % (rank + 1))
    return colour, how


def cover_sets(sets, limit: int) -> dict:
    """Can at most `limit` palettes of at most 3 colours cover every set of block colours?

    Exact, not greedy: pick the first uncovered set, branch over every candidate palette that contains it,
    recurse to depth limit. Frames have few distinct colour sets, so this is cheap, and an exact answer matters
    because a false failure sends a person to repaint blocks that were legal.
    """
    wanted = sorted({frozenset(s) for s in sets if s}, key=lambda item: (-len(item), sorted(item)))
    empty = [frozenset()]
    if not wanted:
        return {"ok": True, "palettes": [], "distinct_sets": 0, "wanted": []}
    if any(len(item) > 3 for item in wanted):
        over = [sorted(rgb_hex(c) for c in item) for item in wanted if len(item) > 3]
        return {"ok": False, "palettes": [], "distinct_sets": len(wanted), "wanted": wanted,
                "reason": "%d block(s) already carry more than 3 colours: %s" % (len(over), over[:4])}

    universe = sorted({colour for item in wanted for colour in item})
    candidates = []
    seen = set()
    for item in wanted:
        for extra in [frozenset()] + [frozenset([c]) for c in universe if c not in item]:
            candidate = frozenset(item | extra)
            if len(candidate) <= 3 and candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
    # A palette that is a strict subset of another one with the same reach is redundant.
    reach = {candidate: frozenset(i for i, item in enumerate(wanted) if item <= candidate) for candidate in candidates}
    maximal = [c for c in candidates
               if not any(reach[c] < reach[other] and c < other for other in candidates)]

    best = {"found": None}

    def search(chosen, covered, remaining):
        if best["found"] is not None and len(chosen) >= len(best["found"]):
            return
        if len(covered) == len(wanted):
            best["found"] = list(chosen)
            return
        if len(chosen) == limit:
            return
        first = next(index for index in range(len(wanted)) if index not in covered)
        for candidate in maximal:
            if first not in reach[candidate]:
                continue
            if candidate in chosen:
                continue
            chosen.append(candidate)
            search(chosen, covered | reach[candidate], remaining)
            chosen.pop()

    search([], frozenset(), None)
    if best["found"] is None:
        return {"ok": False, "palettes": [], "distinct_sets": len(wanted), "wanted": wanted,
                "reason": "no %d palettes of 3 colours cover %d distinct colour sets" % (limit, len(wanted))}
    palettes = [sorted(item) for item in best["found"]]
    return {"ok": True, "palettes": palettes, "distinct_sets": len(wanted), "wanted": wanted, "empty": empty}


# -----------------------------------------------------------------------------------------------------------------
# The rules.

def check_palette_membership(image: Image.Image, palette: dict) -> dict:
    """Rule 1: every visible pixel is a usable PPU colour. Reports counts per offending colour and the pixels."""
    allowed = palette["allowed"]
    refused = palette.get("refused", {})
    counts = Counter()
    samples = {}
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            rgb = (r, g, b)
            if rgb in allowed:
                continue
            counts[rgb] += 1
            samples.setdefault(rgb, (x, y))
    problems = []
    for rgb, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        problems.append({
            "rule": "palette",
            "colour": rgb_hex(rgb),
            "pixels": count,
            "at": list(samples[rgb]),
            "detail": "%s is not a usable PPU colour%s" % (rgb_hex(rgb), ("; " + refused[rgb]) if rgb in refused else ""),
        })
    return {"problems": problems, "off_palette_pixels": sum(counts.values()), "off_palette_colours": len(counts)}


def check_background_blocks(blocks: dict, backdrop) -> dict:
    """Rules 2 and 3: at most 3 colours besides the backdrop per block, at most 4 palettes in the frame."""
    shade = tuple(backdrop) if backdrop is not None else None
    problems = []
    sets = []
    for (bx, by), counter in sorted(blocks.items()):
        colours = set(counter)
        if shade is not None:
            colours.discard(shade)
        sets.append(colours)
        if len(colours) > 3:
            ordered = sorted(colours, key=lambda c: (-counter[c], c))
            problems.append({
                "rule": "background_area",
                "block": [bx, by],
                "colours": [rgb_hex(c) for c in ordered],
                "detail": "16x16 block at %d,%d carries %d colours besides the backdrop, the limit is 3"
                          % (bx, by, len(colours)),
            })
    cover = cover_sets(sets, MAX_BG_PALETTES)
    over_limit = any(len(s) > 3 for s in sets)
    if not cover["ok"] and not over_limit:
        # The blocks are individually legal but the frame still needs more than 4 groups of 3 colours.
        problems.append({
            "rule": "background_palettes",
            "blocks": [],
            "detail": cover.get("reason", "the frame needs more than %d background palettes" % MAX_BG_PALETTES),
            "palettes": [[rgb_hex(c) for c in sorted(item)] for item in cover["wanted"]],
        })
    offending_blocks = sorted({tuple(p["block"]) for p in problems if "block" in p})
    return {
        "problems": problems,
        "blocks": len(blocks),
        "offending_blocks": offending_blocks,
        "palettes": [[rgb_hex(c) for c in palette] for palette in cover["palettes"]],
        "palette_count": len(cover["palettes"]),
        "distinct_colour_sets": cover["distinct_sets"],
        "all_blocks_palette_legal": all(len(s) <= 3 for s in sets),
    }


def load_sprites(frame: Image.Image, mask_path: str | None, list_path: str | None, sprite_height: int,
                 crop: dict | None = None) -> dict:
    """Sprite rectangles for the frame.

    Two ways in, because a mask is what a renderer can produce and a list is what a hand written scene has:
      - a sprite list JSON: [{"x": 12, "y": 40, "w": 8, "h": 16}, ...], or {"sprites": [...]}, with an optional
        per sprite "transparent": "#000000" naming the colour that means "no pixel here";
      - a mask PNG: any pixel with alpha 0 is not part of a sprite, so the marked pixels are grouped into
        connected 8x8 tiles and stacked into sprites at most 8 wide and sprite_height tall, which is the shape
        an OAM entry holds. The mask must be 256x240 scale 1, or the same size as the capture the frame came
        from, in which case it is cropped and downsampled exactly as the frame was.
    """
    sprites = []
    if list_path:
        with open(list_path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data = data.get("sprites") or []
        if not isinstance(data, list):
            raise ValueError("%s must hold a list of sprite rectangles" % list_path)
        for position, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValueError("sprite %d in %s is not an object" % (position, list_path))
            sprite = {
                "box": [int(entry.get("x", 0)), int(entry.get("y", 0)),
                        int(entry.get("w", entry.get("width", TILE))),
                        int(entry.get("h", entry.get("height", sprite_height)))],
                "source": "list",
                "index": position,
            }
            if entry.get("transparent") is not None:
                sprite["transparent"] = hex_to_rgb(str(entry["transparent"]))
            sprites.append(sprite)
    if mask_path:
        if not os.path.isfile(mask_path):
            raise ValueError("sprite mask %s does not exist" % mask_path)
        with Image.open(mask_path) as handle:
            mask_image = handle.convert("RGBA")
        if mask_image.size != (FRAME_W, FRAME_H):
            scale = int((crop or {}).get("scale", 1))
            box = tuple((crop or {}).get("crop", (0, 0, FRAME_W, FRAME_H)))
            if scale > 1 and mask_image.size == tuple((crop or {}).get("source_size", mask_image.size)):
                mask_image = downsample(mask_image, box, scale)
            else:
                raise ValueError("sprite mask %s is %dx%d; make it 256x240, or the same size as the capture"
                                 % (mask_path, mask_image.width, mask_image.height))
        pixels = mask_image.load()
        marked = {(x, y) for y in range(FRAME_H) for x in range(FRAME_W) if pixels[x, y][3] != 0}
        for box, members in group_sprites(marked, sprite_height):
            sprites.append({"box": box, "source": "mask", "members": members})
    source = frame.load()
    for sprite in sprites:
        x0, y0, w, h = sprite["box"]
        member_marks = sprite.get("members")
        members = []
        for y in range(max(0, y0), min(y0 + h, FRAME_H)):
            for x in range(max(0, x0), min(x0 + w, FRAME_W)):
                if member_marks is not None and (x, y) not in member_marks:
                    continue
                r, g, b, a = source[x, y]
                if a == 0:
                    continue
                if "transparent" in sprite and (r, g, b) == sprite["transparent"]:
                    continue
                members.append((x, y, (r, g, b)))
        sprite["pixels"] = members
        sprite["colours"] = sorted({rgb for _, _, rgb in members})
    return {"sprites": sprites}


def group_sprites(marked: set, sprite_height: int) -> list:
    """Turn a set of marked pixels into OAM shaped sprites: runs of 8x8 tiles stacked to sprite_height."""
    cells = {(x // TILE, y // TILE) for x, y in marked}
    if not cells:
        return []
    # Union tiles that touch (4 or 8 neighbour), so one character becomes one blob.
    blobs = []
    remaining = set(cells)
    while remaining:
        start = min(remaining)
        remaining.discard(start)
        stack = [start]
        blob = {start}
        while stack:
            cx, cy = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbour = (cx + dx, cy + dy)
                    if neighbour in remaining:
                        remaining.discard(neighbour)
                        blob.add(neighbour)
                        stack.append(neighbour)
        blobs.append(blob)
    out = []
    rows = max(1, sprite_height // TILE)
    for blob in blobs:
        xs = sorted({cx for cx, _ in blob})
        ys = sorted({cy for _, cy in blob})
        # Split a blob that is wider than 8 tiles into columns of one tile and rows of `rows` tiles.
        for column in range(min(xs), max(xs) + 1):
            for row_start in range(min(ys), max(ys) + 1, rows):
                members = {(x, y) for x, y in marked
                           if x // TILE == column and row_start <= y // TILE < row_start + rows}
                if not members:
                    continue
                out.append(([column * TILE, row_start * TILE, TILE, rows * TILE], members))
    return out


def check_sprites(sprites: list) -> dict:
    """Rules 4, 5 and 6: 3 colours per sprite, 4 sprite palettes, 8 per scanline, 64 in total."""
    problems = []
    line_counts = Counter()
    sets = []
    offending = []
    for position, sprite in enumerate(sprites):
        colours = set(sprite["colours"])
        sets.append(colours)
        if len(colours) > 3:
            problems.append({
                "rule": "sprite_colours",
                "sprite": position,
                "box": sprite["box"],
                "colours": [rgb_hex(c) for c in sorted(colours)],
                "detail": "sprite %d at %d,%d carries %d colours, a sprite has 3 plus transparency"
                          % (position, sprite["box"][0], sprite["box"][1], len(colours)),
            })
            offending.append(sprite["box"])
        x0, y0, w, h = sprite["box"]
        for y in range(max(0, y0), min(FRAME_H, y0 + h)):
            line_counts[y] += 1
    cover = cover_sets(sets, MAX_SPRITE_PALETTES)
    if not cover["ok"]:
        problems.append({
            "rule": "sprite_palettes",
            "detail": cover.get("reason", "the frame needs more than %d sprite palettes" % MAX_SPRITE_PALETTES),
            "palettes": [[rgb_hex(c) for c in sorted(item)] for item in cover["wanted"]],
        })
        offending.extend(sprite["box"] for sprite in sprites)
    crowded = sorted(line for line, count in line_counts.items() if count > MAX_SPRITES_PER_LINE)
    if crowded:
        worst = max(crowded, key=lambda line: (line_counts[line], -line))
        problems.append({
            "rule": "sprites_per_scanline",
            "lines": crowded,
            "detail": "%d scanlines carry more than %d sprites (the first crowded line, %d, carries %d); OAM drops "
                      "the rest" % (len(crowded), MAX_SPRITES_PER_LINE, worst, line_counts[worst]),
        })
    if len(sprites) > MAX_SPRITES:
        problems.append({
            "rule": "sprite_count",
            "detail": "%d sprites in the frame, OAM holds %d" % (len(sprites), MAX_SPRITES),
        })
    return {
        "problems": problems,
        "count": len(sprites),
        "offending_boxes": offending,
        "palettes": [[rgb_hex(c) for c in palette] for palette in cover["palettes"]],
        "palette_count": len(cover["palettes"]),
        "max_per_line": max(line_counts.values()) if line_counts else 0,
        "busiest_line": max(line_counts.items(), key=lambda item: (item[1], item[0]))[0] if line_counts else None,
    }


def check_screen_colours(image: Image.Image) -> dict:
    """Rule 7: at most 25 colours on screen, which is 4 background palettes, 4 sprite palettes and the backdrop."""
    seen = Counter()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a:
                seen[(r, g, b)] += 1
    problems = []
    if len(seen) > MAX_COLOURS_ON_SCREEN:
        problems.append({
            "rule": "screen_colours",
            "colours": [rgb_hex(c) for c in sorted(seen)],
            "detail": "%d colours in the frame, a NES can show %d" % (len(seen), MAX_COLOURS_ON_SCREEN),
        })
    return {"problems": problems, "colours": len(seen), "top": [(rgb_hex(c), n) for c, n in seen.most_common(5)]}


# -----------------------------------------------------------------------------------------------------------------
# Report and overlay.

def check_frame(frame: Image.Image, palette: dict, backdrop=None, sprites: list | None = None) -> dict:
    """Every rule, in the order a person would fix them."""
    blocks = block_colours(frame)
    shade, how = choose_backdrop(frame, blocks, backdrop)
    report = {
        "size": [frame.width, frame.height],
        "palette_count_allowed": palette["count"],
        "backdrop": rgb_hex(shade) if shade else None,
        "backdrop_from": how,
        "palette": check_palette_membership(frame, palette),
        "background": check_background_blocks(blocks, shade),
        "screen": check_screen_colours(frame),
    }
    problems = []
    problems += report["palette"]["problems"]
    problems += report["background"]["problems"]
    problems += report["screen"]["problems"]
    if sprites is not None:
        report["sprite"] = check_sprites(sprites)
        problems += report["sprite"]["problems"]
    report["problems"] = problems
    report["ok"] = not problems
    return report


def describe(report: dict, info: dict) -> list:
    lines = []
    how = info.get("crop_how", "?")
    scale = info.get("scale", 1)
    extra = ""
    if "crop_score" in info:
        extra = ", viewport score %.3f" % info["crop_score"]
    lines.append("%s  %s  frame %dx%d  read at scale %d from %dx%d (%s, crop %s%s)%s"
                 % (os.path.basename(info.get("path", "frame")), "[frame %d]" % info["frame"] if "frame" in info else "",
                    report["size"][0], report["size"][1], scale,
                    info["source_size"][0], info["source_size"][1], how, info.get("crop"), extra,
                    "" if report["ok"] else "  FAIL %d problem(s)" % len(report["problems"])))
    lines.append("  colours: %d in the frame, %d allowed; backdrop %s (%s)"
                 % (report["screen"]["colours"], MAX_COLOURS_ON_SCREEN, report["backdrop"], report["backdrop_from"]))
    background = report["background"]
    cover_text = ("%d palette(s) cover them, %d allowed" % (background["palette_count"], MAX_BG_PALETTES)
                  if background["all_blocks_palette_legal"]
                  else "no palette covers them: blocks carry more than 3 colours")
    lines.append("  background: %d blocks, %d distinct colour sets, %s"
                 % (background["blocks"], background["distinct_colour_sets"], cover_text))
    for palette in background["palettes"]:
        lines.append("    palette %s" % " ".join(palette))
    if "sprite" in report:
        sprite = report["sprite"]
        lines.append("  sprites: %d, %d palette(s), busiest scanline %s carries %d, %d per line and %d total allowed"
                     % (sprite["count"], sprite["palette_count"], sprite["busiest_line"], sprite["max_per_line"],
                        MAX_SPRITES_PER_LINE, MAX_SPRITES))
        for palette in sprite["palettes"]:
            lines.append("    sprite palette %s" % " ".join(palette))
    else:
        lines.append("  sprites: not checked (no --sprite-mask and no --sprites)")
    bad = report["palette"]["off_palette_pixels"]
    if bad:
        lines.append("  off palette: %d pixels in %d colours" % (bad, report["palette"]["off_palette_colours"]))
    for problem in report["problems"]:
        where = ""
        if "block" in problem:
            where = " block %d,%d" % tuple(problem["block"])
        elif "box" in problem:
            where = " sprite at %d,%d" % tuple(problem["box"][:2])
        elif "at" in problem:
            where = " first at %d,%d" % tuple(problem["at"])
        lines.append("  [%s]%s %s" % (problem["rule"], where, problem["detail"]))
        if problem.get("colours"):
            lines.append("    colours: %s" % " ".join(problem["colours"]))
        if problem.get("palettes"):
            for palette in problem["palettes"][:8]:
                lines.append("    needed palette %s" % " ".join(palette))
    offending_blocks = report["background"]["offending_blocks"]
    lines.append("  %s: %d block(s) violate the background rules, %d sprite(s) violate the sprite rules"
                 % ("PASS" if report["ok"] else "FAIL",
                    len(offending_blocks),
                    len(report.get("sprite", {}).get("offending_boxes", []))))
    return lines


def write_overlay(frame: Image.Image, report: dict, path: str, scale: int = OVERLAY_SCALE) -> str:
    """The frame at `scale`, with every offending block and sprite boxed, so a person can see what to fix."""
    image = frame.convert("RGBA").resize((frame.width * scale, frame.height * scale), Image.NEAREST)
    pixels = image.load()

    def line(x0, y0, x1, y1, colour):
        for x in range(max(0, x0), min(image.width, x1)):
            for y in (y0, y1 - 1):
                if 0 <= y < image.height:
                    pixels[x, y] = colour
        for y in range(max(0, y0), min(image.height, y1)):
            for x in (x0, x1 - 1):
                if 0 <= x < image.width:
                    pixels[x, y] = colour

    for bx, by in report["background"]["offending_blocks"]:
        line(bx * scale, by * scale, (bx + AREA) * scale, (by + AREA) * scale, MARK_BACKGROUND)
    for box in report.get("sprite", {}).get("offending_boxes", []):
        x, y, w, h = box
        line(x * scale, y * scale, (x + w) * scale, (y + h) * scale, MARK_SPRITE)
    for problem in report["problems"]:
        if problem["rule"] == "background_palettes":
            # Every block is suspect when the frame needs too many palettes: dot their top left corners.
            for by in range(0, frame.height, AREA):
                for bx in range(0, frame.width, AREA):
                    for dy in range(3):
                        for dx in range(3):
                            x, y = bx * scale + dx, by * scale + dy
                            if 0 <= x < image.width and 0 <= y < image.height:
                                pixels[x, y] = MARK_PALETTE
    image.save(path, "PNG")
    return os.path.abspath(path)


# -----------------------------------------------------------------------------------------------------------------
# The run.

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check one NES frame against the PPU rules, background and sprites.")
    parser.add_argument("frame", help="the frame: a 256x240 PNG, a 3x capture, or a window screenshot with a 3x viewport")
    parser.add_argument("--palette", default=None, help="palette file; default data\\nes_palette.json, or the art bible")
    parser.add_argument("--crop", default="auto", help="auto, 1, 3, or x,y: where the viewport is inside a capture")
    parser.add_argument("--frame", dest="frame_index", type=int, default=None, help="frame number in an animated GIF")
    parser.add_argument("--backdrop", default=None, help="the shared backdrop colour, #RRGGBB or $0F or 15")
    parser.add_argument("--sprite-mask", default=None, help="PNG whose non transparent pixels belong to sprites")
    parser.add_argument("--sprites", dest="sprite_list", default=None,
                        help="JSON list of sprite rectangles: [{\"x\":0,\"y\":0,\"w\":8,\"h\":16}]")
    parser.add_argument("--sprite-height", type=int, default=16, choices=(8, 16),
                        help="sprite height for mask grouping; 8x16 is one OAM entry, not two")
    parser.add_argument("--overlay", default=None, help="write a PNG at 3x with the offending blocks marked")
    parser.add_argument("--json", dest="json_path", default=None, help="write the report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    root = repo_root()
    palette_path = os.path.abspath(args.palette) if args.palette else default_palette_path(root)
    try:
        palette = load_palette(palette_path)
        with open(palette_path, "r", encoding="utf-8-sig") as handle:
            palette["entries"] = json.load(handle).get("entries")
        frame, info = load_frame(args.frame, palette["allowed"], args.crop, args.frame_index)
        backdrop = parse_colour(args.backdrop, palette) if args.backdrop else None
        sprite_data = load_sprites(frame, args.sprite_mask, args.sprite_list, args.sprite_height,
                                   crop=info) if (args.sprite_mask or args.sprite_list) else None
    except (ValueError, OSError) as error:
        print("cannot check this frame: %s" % error, file=sys.stderr)
        return 2

    sprites = sprite_data["sprites"] if sprite_data else None
    report = check_frame(frame, palette, backdrop, sprites)
    report["frame"] = info
    report["palette_path"] = palette_path
    report["palette_usable"] = palette["count"]
    report["palette_entries"] = palette["raw_count"]

    lines = describe(report, info)
    lines.append("  palette: %s (%d usable of %d entries)"
                 % (os.path.relpath(palette_path, root) if palette_path.startswith(root) else palette_path,
                    palette["count"], palette["raw_count"]))
    if not args.quiet or not report["ok"]:
        for line in lines:
            print(line)
    if args.overlay:
        print("  overlay: %s" % write_overlay(frame, report, args.overlay))
        report["overlay"] = os.path.abspath(args.overlay)
    if args.json_path:
        serialisable = dict(report)
        serialisable["problems"] = report["problems"]
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(serialisable, handle, indent=2, default=str)
            handle.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
