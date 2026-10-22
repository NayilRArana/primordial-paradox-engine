#!/usr/bin/env python3
"""quantize_concept.py: quantise one concept art PNG to a scene's palette set, and say what the art lost.

Why this exists
---------------
ART-BIBLE.md RULE 0 point 5: concept art (Kaggle, Gemini) is only accepted after it is quantised to the
scene's palette set and passes tools\\palette_synergy.py. A pretty image that does not survive quantisation is
rejected, not patched later. This tool is the quantisation step, and it is deliberately blunt:

  1. Every opaque pixel is mapped to the nearest usable 2C02 entry (the master palette, 64 outputs), then, if
     that entry is not in the scene's set, to the nearest entry that IS in the set. No ordered dither by
     default, because the NES has none: dithering a concept image makes a picture that looks fine at 100
     percent and turns into a checkerboard at 3x on a television. `--dither ordered` exists for a test, and
     the report says so when it is used.
  2. The result is written next to the original with the suffix `_nes.png`, and a before and after sheet next
     to that with `_nes_sheet.png`, so a person can look at the loss instead of reading a number.
  3. The colour loss is reported as the mean CIE76 delta E over the opaque pixels, plus the worst pixel and
     the number of distinct colours before and after. A mean delta E above --max-delta-e (default 10, gamedev
     may move it) exits 1: that image is not concept art for this scene, it is a different picture, and
     repainting it into the set later costs more than asking for it again.

The palette arithmetic is tools\\art\\scene_palette.py (the Scene object: nearest_master, nearest_in, the usable
entry table) and the set itself is tools\\scene_palette_set.py. Nothing about the 2C02 is restated here.

Usage:
    python tools\\quantize_concept.py output\\concept\\thames.png --scene southampton
    python tools\\quantize_concept.py output\\concept\\thames.png --scene southampton --json out.json
    python tools\\quantize_concept.py output\\concept --scene westminster        (every PNG in the folder)
    python tools\\quantize_concept.py --selftest

Exit code 0 when every image is inside the threshold, 1 when any image loses too much colour, 2 on a bad
argument. The source PNG is never modified: the output always carries a suffix.
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
    """(quantised image, per pixel stats). Every opaque pixel lands on an entry in `allowed`."""
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
            max_delta_e: float = DEFAULT_MAX_DELTA_E) -> dict:
    scene = scene_palette_set.scene(root, scene_id)
    with Image.open(path) as handle:
        before = handle.convert("RGBA")
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
    lines.append("  mean delta E %.2f (limit %.2f), worst %.2f, %.2f%% of pixels moved, colours %d -> %d, "
                 "%d entries allowed%s"
                 % (stats["mean_delta_e"], stats["max_delta_e_allowed"], stats["max_delta_e"],
                    stats["changed_percent"], stats["colours_before"], stats["colours_after"],
                    stats["allowed_entries"], ", ordered dither ON (not a proposed NES frame)" if stats["dither"] else ""))
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
    # delta E is zero for a colour against itself and grows with distance.
    assert delta_e((10, 10, 10), (10, 10, 10)) == 0.0
    assert delta_e((0, 0, 0), (255, 255, 255)) > delta_e((0, 0, 0), (40, 40, 40))
    print("quantize_concept selftest: 5 check(s) PASS")
    return 0


# -----------------------------------------------------------------------------------------------------------------
# CLI.

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Quantise concept art to a scene's palette set.")
    parser.add_argument("target", nargs="?", help="a concept art PNG, or a folder of them")
    parser.add_argument("--scene", default=None)
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
    for path in sprite_targets(root, args.target):
        results.append(convert(root, path, args.scene, dither=args.dither == "ordered",
                               max_delta_e=args.max_delta_e))
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
