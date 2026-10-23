#!/usr/bin/env python3
"""quantize_concept.py: quantise one concept art PNG to a scene's palette set, and say what the art lost.

Why this exists
---------------
ART-BIBLE.md RULE 0 point 5: concept art (Kaggle, Gemini) is only accepted after it is quantised to the
scene's palette set and passes tools\\palette_synergy.py. A pretty image that does not survive quantisation is
rejected, not patched later. This tool is the quantisation step, and it is deliberately blunt:

  1. Every opaque pixel is mapped onto the scene's palette set. The NES cannot draw a background any way it
     likes: per 16x16 attribute area it shows ONE of the 4 background palettes, each being 3 entries plus the
     shared backdrop (RULE 0 point 4). So the mapping is per area by default (`--map areas`): each 16x16 area
     picks the background palette that represents it best, and every pixel in that area lands on the nearest
     entry of THAT palette. A frame mapped this way carries at most 3 colours besides the backdrop in any one
     area and spends at most the scene's 4 written background palettes, which is what tools\\palette_synergy.py
     asks for, by construction rather than by luck.
     `--map free` is the older mapping: every pixel to the nearest entry in the union of the whole set, with no
     area ownership. It is kept because it is the honest "what does flattening to this set cost" number, and
     because a frame that maps well this way and badly the other way is a picture whose colour crosses area
     boundaries, which is a composition problem and not a palette problem. It is NOT a frame a NES can draw,
     and it is not the default for that reason.
     No ordered dither by default, because the NES has none: dithering a concept image makes a picture that
     looks fine at 100 percent and turns into a checkerboard at 3x on a television. `--dither ordered` exists
     for a test, implies `--map free` (a dither is a per pixel nudge, so it cannot honour area ownership), and
     the report says so when it is used.
  2. The result is written next to the original with the suffix `_nes.png`, and a before and after sheet next
     to that with `_nes_sheet.png`, so a person can look at the loss instead of reading a number.
  3. The colour loss is reported as the mean CIE76 delta E over the opaque pixels of the frame that ships, plus
     the same number for the free mapping for comparison, the worst pixel, and the number of distinct colours
     before and after. A mean delta E above --max-delta-e (default 10, gamedev may move it) exits 1: that image
     is not concept art for this scene, it is a different picture, and repainting it into the set later costs
     more than asking for it again.

What this tool is not: tools\\nes_enforce.py turns a frame with NO written palette set (a capture, a title
render, a Gemini image) into a legal NES frame by inventing 4 palettes with k means over 16x16 blocks. This tool
is the other case: the set is already written down in data\\scene_palettes.json and the frame must spend that
set, so there is nothing to invent and nothing to iterate.


The palette arithmetic is tools\\art\\scene_palette.py (the Scene object: nearest_master, nearest_in, the usable
entry table) and the set itself is tools\\scene_palette_set.py. Nothing about the 2C02 is restated here.

Usage:
    python tools\\quantize_concept.py output\\concept\\thames.png --scene southampton
    python tools\\quantize_concept.py output\\concept\\thames.png --scene southampton --json out.json
    python tools\\quantize_concept.py output\\concept\\thames.png --scene southampton --map free
    python tools\\quantize_concept.py output\\concept --scene westminster        (every PNG in the folder)
    python tools\\quantize_concept.py --selftest

Exit code 0 when every image is inside the threshold, 1 when any image loses too much colour, 2 on a bad
argument. The source PNG is never modified: the output always carries a suffix.

Why the default changed (card t_4bafb4a1, 2026-10-22): round R8 of the Kaggle concept art measured a frame at
mean delta E 7.35 under the free mapping, inside the 10.0 limit, that still failed tools\\palette_synergy.py 203
times on background_area and palette_count. That was not a colour result: the free mapping spends the whole set
per pixel, so colours from several palettes land inside one 16x16 area and the two area rules fail whatever the
painting is. The same frame through the per area mapping costs 7.83, still inside the limit, and fails the area
rules 0 times. The acceptance number is now the number of the frame that can actually ship.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))

import scene_palette_set  # noqa: E402  (the set, the Scene object and the master palette, all reused)

SUFFIX = "_nes"
SHEET_SUFFIX = "_nes_sheet"
DEFAULT_MAX_DELTA_E = 10.0
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


# -----------------------------------------------------------------------------------------------------------------
# CIE76 delta E. sRGB, then linear, then XYZ (D65), then Lab. The only arithmetic in this file that is not the
# project's, and it is here because "colour loss" needs a number that is not a guess.

def srgb_to_linear(value: float) -> float:
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def to_lab(rgb) -> tuple:
    r, g, b = (srgb_to_linear(channel) for channel in rgb[:3])
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(value):
        return value ** (1.0 / 3.0) if value > 0.008856 else (7.787 * value) + (16.0 / 116.0)

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e(first, second) -> float:
    a, b = to_lab(first), to_lab(second)
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


# -----------------------------------------------------------------------------------------------------------------
# Quantisation.

def dither_target(image: Image.Image, x: int, y: int, target) -> tuple:
    """Ordered dither on the 4x4 Bayer matrix: push the target a little towards the next entry, then quantise.

    Only used when the caller asks for it. The NES has no dithering: this exists so a test can prove the
    option is honoured, and the report states that a dithered result is not a proposed NES frame.
    """
    threshold = (BAYER[y % 4][x % 4] + 0.5) / 16.0 - 0.5
    step = 24.0
    return tuple(max(0, min(255, int(round(channel + threshold * step)))) for channel in target)


def shown(root: str, path: str) -> str:
    """The path as the report prints it: relative to the repo when it can be, absolute on another drive."""
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def colour_count(image: Image.Image) -> int:
    """Distinct opaque RGB colours, counted without Image.getdata (deprecated in Pillow 12)."""
    counts = image.convert("RGBA").getcolors(maxcolors=1 << 24) or []
    return sum(1 for count, colour in counts if count and colour[3])


def quantise(image: Image.Image, scene, dither: bool = False, allowed=None) -> tuple:
    """(quantised image, per pixel stats). Every opaque pixel lands on an entry in `allowed`.

    This is the FREE mapping: the union of the set, nearest entry per pixel, no area ownership. It is the number
    for "what does flattening to this set cost", not a frame a NES can draw. quantise_areas() is that.
    """
    allowed = sorted(scene.bg_colours() | scene.sprite_colours() | {scene.backdrop} if allowed is None else allowed)
    source = image.convert("RGBA")
    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    src, dst = source.load(), out.load()
    deltas = []
    changed = 0
    cache = {}
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = src[x, y]
            if not a:
                continue
            key = (r, g, b)
            if dither:
                entry = scene.nearest_master(dither_target(source, x, y, (r, g, b)))
                if entry not in allowed:
                    entry = scene.nearest_in(entry, allowed)
                mapped = scene.rgb(entry)
            else:
                mapped = cache.get(key)
                if mapped is None:
                    entry = scene.nearest_master((r, g, b))
                    if entry not in allowed:
                        entry = scene.nearest_in(entry, allowed)
                    mapped = scene.rgb(entry)
                    cache[key] = mapped
            dst[x, y] = mapped + (a,)
            deltas.append(delta_e((r, g, b), mapped))
            if mapped != (r, g, b):
                changed += 1
    total = max(1, len(deltas))
    stats = {
        "pixels": total,
        "changed": changed,
        "changed_percent": round(100.0 * changed / total, 2),
        "mean_delta_e": round(sum(deltas) / total, 2) if deltas else 0.0,
        "max_delta_e": round(max(deltas), 2) if deltas else 0.0,
        "colours_before": colour_count(source),
        "colours_after": colour_count(out),
        "allowed_entries": len(allowed),
        "dither": bool(dither),
        "mapping": "free",
    }
    return out, stats


def area_palettes(scene) -> list:
    """The scene's four written background palettes as RGB tuples, each with the shared backdrop.

    Ordered, deduplicated inside a palette, and the backdrop is added because the PPU shows it in every area. A
    background area may only spend one of these four rows: that is RULE 0 point 4, and it is why this list and not
    the union of the set is the vocabulary of the per area mapping.
    """
    rows = []
    for row in scene.background:
        entries = sorted(set(row) | {scene.backdrop})
        rows.append(tuple(scene.rgb(entry) for entry in entries))
    return rows


def quantise_areas(image: Image.Image, scene, area: int = 16) -> tuple:
    """(quantised image, per pixel stats) with one background palette per 16x16 attribute area.

    For each area the four written palettes are scored by the summed CIE76 delta E of that area's pixels against
    their nearest colour inside the palette, the cheapest wins, and every pixel is painted through the winner. The
    area rules tools\\palette_synergy.py measures (at most 3 colours besides the backdrop per area, at most 4
    background palettes per frame) therefore hold by construction: the frame spends 4 written palettes and nothing
    else.
    """
    source = image.convert("RGBA")
    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    src, dst = source.load(), out.load()
    palettes = area_palettes(scene)
    allowed = {colour for palette in palettes for colour in palette}
    nearest_cache = {}
    deltas = []
    changed = 0
    picks = [0] * len(palettes)
    areas = 0

    def mapped(colour, palette):
        key = (colour, palette)
        got = nearest_cache.get(key)
        if got is None:
            chosen = min(palette, key=lambda option: delta_e(colour, option))
            got = (chosen, delta_e(colour, chosen))
            nearest_cache[key] = got
        return got

    for top in range(0, source.height, area):
        for left in range(0, source.width, area):
            cells = [(x, y, src[x, y][:3])
                     for y in range(top, min(top + area, source.height))
                     for x in range(left, min(left + area, source.width))
                     if src[x, y][3]]
            if not cells:
                continue
            areas += 1
            costs = [sum(mapped(colour, palette)[1] for _, _, colour in cells) for palette in palettes]
            best = min(range(len(palettes)), key=lambda index: (costs[index], index))
            picks[best] += 1
            palette = palettes[best]
            for x, y, colour in cells:
                rgba = src[x, y]
                chosen, distance = mapped(colour, palette)
                dst[x, y] = tuple(chosen) + (rgba[3],)
                deltas.append(distance)
                if tuple(chosen) != colour:
                    changed += 1
    total = max(1, len(deltas))
    stats = {
        "pixels": total,
        "changed": changed,
        "changed_percent": round(100.0 * changed / total, 2),
        "mean_delta_e": round(sum(deltas) / total, 2) if deltas else 0.0,
        "max_delta_e": round(max(deltas), 2) if deltas else 0.0,
        "colours_before": colour_count(source),
        "colours_after": colour_count(out),
        "allowed_entries": len(allowed),
        "dither": False,
        "mapping": "areas",
        "area_pixels": area,
        "areas": areas,
        "palettes_used": sum(1 for count in picks if count),
        "areas_per_palette": picks,
    }
    return out, stats


# -----------------------------------------------------------------------------------------------------------------
# The before and after sheet.

def label_font():
    try:
        return ImageFont.load_default()
    except Exception:      # pragma: no cover - the default font is always there on CPython's Pillow
        return None


def write_sheet(before: Image.Image, after: Image.Image, path: str, title: str) -> str:
    scale = max(1, min(3, 480 // max(1, before.width)))
    panels = []
    for image in (before.convert("RGBA"), after.convert("RGBA")):
        big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
        canvas = Image.new("RGB", (big.width, big.height), (24, 24, 28))
        canvas.paste(big, (0, 0), big)
        panels.append(canvas)
    band = 18
    gap = 8
    sheet = Image.new("RGB", (panels[0].width + panels[1].width + gap, panels[0].height + band), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    font = label_font()
    draw.text((4, 4), "%s  before" % title, fill=(230, 230, 230), font=font)
    draw.text((panels[0].width + gap + 4, 4), "after (scene set, %dx)" % scale, fill=(230, 230, 230), font=font)
    sheet.paste(panels[0], (0, band))
    sheet.paste(panels[1], (panels[0].width + gap, band))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sheet.save(path, "PNG")
    return path


# -----------------------------------------------------------------------------------------------------------------
# One image, or a folder.

def output_paths(path: str) -> tuple:
    stem, _ = os.path.splitext(path)
    return stem + SUFFIX + ".png", stem + SUFFIX + "_sheet.png"


def convert(root: str, path: str, scene_id: str, dither: bool = False,
            max_delta_e: float = DEFAULT_MAX_DELTA_E, mapping: str = "areas") -> dict:
    """Quantise one PNG. `mapping` is "areas" (a frame a NES can draw, the default) or "free".

    Both numbers are always reported, so the acceptance verdict is never the only thing on the record: a frame
    that costs 7.9 per area and 7.4 free is a colour result, and a frame that costs 20 per area and 7 free is a
    picture whose colour crosses attribute boundaries.
    """
    scene = scene_palette_set.scene(root, scene_id)
    with Image.open(path) as handle:
        before = handle.convert("RGBA")
    if dither:
        # A dither is a per pixel nudge, so it cannot honour which palette owns the area. Same rule as the CLI.
        mapping = "free"
    if mapping == "areas":
        after, stats = quantise_areas(before, scene)
        _, free = quantise(before, scene)
        stats["free_mean_delta_e"] = free["mean_delta_e"]
        stats["free_max_delta_e"] = free["max_delta_e"]
        stats["free_colours_after"] = free["colours_after"]
    else:
        after, stats = quantise(before, scene, dither=dither)
    png, sheet = output_paths(path)
    after.save(png, "PNG")
    write_sheet(before, after, sheet, os.path.basename(path))
    stats.update({
        "source": shown(root, path),
        "out": shown(root, png),
        "sheet": shown(root, sheet),
        "scene": scene_id,
        "max_delta_e_allowed": max_delta_e,
        "accepted": stats["mean_delta_e"] <= max_delta_e,
    })
    return stats


def sprite_targets(root: str, target: str) -> list:
    full = target if os.path.isabs(target) else os.path.join(root, target)
    if os.path.isdir(full):
        return sorted(path for path in glob.glob(os.path.join(full, "*.png"))
                      if SUFFIX not in os.path.basename(path))
    if os.path.isfile(full):
        return [full]
    raise SystemExit("quantize_concept: %s does not exist" % target)


def describe(stats: dict) -> list:
    lines = ["%s -> %s  scene %s: %s"
             % (stats["source"], stats["out"], stats["scene"], "ACCEPT" if stats["accepted"] else "REJECT")]
    detail = ("  mean delta E %.2f (limit %.2f), worst %.2f, %.2f%% of pixels moved, colours %d -> %d, "
              "%d entries allowed"
              % (stats["mean_delta_e"], stats["max_delta_e_allowed"], stats["max_delta_e"],
                 stats["changed_percent"], stats["colours_before"], stats["colours_after"],
                 stats["allowed_entries"]))
    if stats.get("mapping") == "areas":
        detail += ", per %d px area, %d of %d palettes used %s" % (
            stats["area_pixels"], stats["palettes_used"], len(stats["areas_per_palette"]),
            stats["areas_per_palette"])
        detail += ", free mapping %.2f" % stats["free_mean_delta_e"]
    elif stats["dither"]:
        detail += ", ordered dither ON (not a proposed NES frame)"
    lines.append(detail)
    lines.append("  sheet: %s" % stats["sheet"])
    return lines


# -----------------------------------------------------------------------------------------------------------------
# Selftest: a flat colour inside the set must survive with delta E 0, and one outside must move.

def selftest(root: str = ROOT) -> int:
    scene = scene_palette_set.scene(root, "title")
    inside = scene.rgb(int(scene.background[0][0]))
    image = Image.new("RGBA", (8, 8), inside + (255,))
    after, stats = quantise(image, scene)
    assert stats["mean_delta_e"] == 0.0, stats
    assert after.getpixel((0, 0))[:3] == inside, after.getpixel((0, 0))
    # A colour that is not in the set must move, and every resulting pixel must be in the set.
    allowed = scene.bg_colours() | scene.sprite_colours() | {scene.backdrop}
    image = Image.new("RGBA", (8, 8), (200, 30, 200, 255))
    after, stats = quantise(image, scene)
    assert stats["mean_delta_e"] > 0.0, stats
    assert scene.entry_of(after.getpixel((0, 0))[:3]) in allowed, after.getpixel((0, 0))
    # The per area mapping spends one written background palette per 16x16 area and nothing else: an area may
    # carry at most 3 colours besides the backdrop, and the frame at most the scene's 4 rows.
    rows = area_palettes(scene)
    assert len(rows) == 4, rows
    palette_rgbs = {colour for row in rows for colour in row}
    pick = sorted(palette_rgbs)[:6]
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for index, colour in enumerate(pick):
        image.putpixel((index * 5, 0), tuple(colour) + (255,))
        image.putpixel((index * 5, 20), tuple(colour) + (255,))
    after, stats = quantise_areas(image, scene)
    assert stats["mapping"] == "areas", stats
    assert stats["palettes_used"] <= 4, stats
    assert sum(stats["areas_per_palette"]) == stats["areas"] == 4, stats
    for y in range(0, 32, 16):
        for x in range(0, 32, 16):
            seen = {after.getpixel((px, py))[:3] for py in range(y, y + 16)
                    for px in range(x, x + 16) if after.getpixel((px, py))[3]}
            assert seen <= palette_rgbs, (x, y, seen)
            assert len(seen) <= 4, (x, y, seen)
    # delta E is zero for a colour against itself and grows with distance.
    assert delta_e((10, 10, 10), (10, 10, 10)) == 0.0
    assert delta_e((0, 0, 0), (255, 255, 255)) > delta_e((0, 0, 0), (40, 40, 40))
    print("quantize_concept selftest: 8 check(s) PASS")
    return 0


# -----------------------------------------------------------------------------------------------------------------
# CLI.

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Quantise concept art to a scene's palette set.")
    parser.add_argument("target", nargs="?", help="a concept art PNG, or a folder of them")
    parser.add_argument("--scene", default=None)
    parser.add_argument("--map", choices=["areas", "free"], default="areas",
                        help="areas (default): one written background palette per 16x16 area, a frame a NES "
                             "can draw. free: nearest entry in the whole set per pixel, the colour loss number.")
    parser.add_argument("--dither", choices=["none", "ordered"], default="none")
    parser.add_argument("--max-delta-e", type=float, default=DEFAULT_MAX_DELTA_E)
    parser.add_argument("--json", default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.selftest:
        return selftest(root)
    if not (args.target and args.scene):
        parser.error("give a PNG or folder and --scene, or use --selftest")

    results = []
    mapping = args.map
    if args.dither == "ordered" and mapping == "areas":
        # A dither is a per pixel nudge, which cannot honour who owns the area. Say so, then do the free mapping.
        print("quantize_concept: --dither ordered implies --map free (a dither cannot honour area ownership)")
        mapping = "free"
    for path in sprite_targets(root, args.target):
        results.append(convert(root, path, args.scene, dither=args.dither == "ordered",
                               max_delta_e=args.max_delta_e, mapping=mapping))
    if args.json:
        out = args.json if os.path.isabs(args.json) else os.path.join(root, args.json)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"tool": "quantize_concept", "scene": args.scene, "results": results}, handle,
                      indent=2, sort_keys=True)
            handle.write("\n")
    if not args.quiet:
        for stats in results:
            for line in describe(stats):
                print(line)
    rejected = [stats for stats in results if not stats["accepted"]]
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
