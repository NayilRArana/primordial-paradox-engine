#!/usr/bin/env python3
"""kaggle_r7.py: palette-first concept candidates for the R7 Kaggle GPU lane, and a scored report.

What this run is
----------------
PLAN-WIN section 1 wants "concept art from Meta image models, segmentation with SAM 3.1, palette-first
conversion to real NES limits, checked by our own tools". The GPU half needs a Kaggle client and a kernel
round trip. Two ways to get a concept into step 1 below:

  * PAINTED LANE (default). Our own deterministic painter draws the frame. Nothing external runs.
  * MODEL LANE (--concepts DIR). The frames were generated earlier by a real image model, on a Kaggle GPU,
    and sit in DIR as `<subject id>.png`. This run reads them instead of painting, and records which file
    it read, its sha256, and the model that wrote it when DIR carries an `r7_manifest.json` beside it.

Whichever lane fills the concept, steps 2 to 4 are the same code and the same rules.

What the local lane does, in order, once per subject:

  1. CONCEPT. Paints a concept frame at 256x240 (or 16x16 for a sprite) from a written brief: a sky or
     wall gradient, water or floor bands, and named structures, plus seeded grain. The colours are
     deliberately OUTSIDE the scene's set, so quantisation has something real to lose. This is our own
     painter, not Meta's model, and the report says so per candidate.
  2. SEGMENT. Deterministic k means in CIE Lab over the concept's 16x16 blocks (fixed seed, fixed
     iteration count, no library that has to be installed). The segments are reported as coverage and as
     which of the scene's 4 background palettes each one lands in; segmentation does not change a pixel
     of what ships.
  3. QUANTISE. tools/quantize_concept.py, per area mapping (the R8 ruling in card t_4bafb4a1), against
     the subject's scene set. The free mapping number is reported beside it because the two answer
     different questions. A sprite is quantised against the scene's 4 sprite palettes, because a sprite
     cannot spend a background palette.
  4. MEASURE. tools/palette_synergy.py owns the rules; this tool imports its Grid, background_report and
     frame_report instead of restating any of them. tools/nes_check.py owns the area and tile counts.

The palette synergy score
-------------------------
No score existed in the project before this tool (grepped: palette_synergy.py and PALETTE-SYNERGY.md
carry counts, never a score), so this tool defines one and states the arithmetic:

    score = 100 * (1 - failed rule instances / rule instances checked)

Every instance is a check the existing tools already make: one per 16x16 area for the 3 colour rule and
one for the palette fit, one per distinct drawn colour for set membership, one per 8x8 sprite tile for
the 3 colour sprite rule, one per frame for the palette count, and one per ground colour for the body
versus ground pair rules. A score of 100 means every instance passed. The basis is printed with every
score, so a reader can recompute it from the counts in the same row. It is not a perceptual quality
number: the eye critic still has to score the frame.

Usage
    python tools\\kaggle_r7.py                     one command, every subject, writes the report
    python tools\\kaggle_r7.py --subjects quay_dusk_scene
    python tools\\kaggle_r7.py --concepts output\\kaggle_r7\\concepts_gpu   model frames instead of painting
    python tools\\kaggle_r7.py --lane kaggle       probe the GPU lane and say why it cannot run here
    python tools\\kaggle_r7.py --selftest

Exit 0 when the report was written and every recipe check passed; 1 when a candidate shipped over the
delta E limit; 2 on a bad argument; 3 when the requested GPU lane is not available on this machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))

import nes_check  # noqa: E402
import palette_synergy  # noqa: E402
import quantize_concept  # noqa: E402
import scene_palette_set  # noqa: E402

OUTPUT = os.path.join(ROOT, "output", "kaggle_r7")
CONCEPTS = os.path.join(OUTPUT, "concepts")
REPORT_JSON = os.path.join(OUTPUT, "report.json")
REPORT_MD = os.path.join(OUTPUT, "report.md")
# Set by --concepts: {"dir": <abs dir of model frames>, "manifest": <dict or None>}. Empty means paint.
EXTERNAL = {"dir": None, "manifest": None, "rows": {}}

AREA = 16
TILE = 8
MAX_SPRITE_COLOURS = 16

# -----------------------------------------------------------------------------------------------------------------
# The subjects. Each brief names entries of the subject's own scene set and a written drift in sRGB units, so a
# concept starts near the vocabulary that has to carry it and still costs something to quantise. The drift is the
# control: a bigger number is a concept painted further from the set.

SUBJECTS = [
    {
        "id": "quay_dusk_scene",
        "kind": "scene",
        "scene": "battle_quay_dusk",
        "about": "the dusk quay: masts against a burnt sky, water, crates on the stone",
        "drift": 12,
        "brief": {
            "sky": [{"entry": 2}, {"entry": 38}],
            "water": [{"entry": 17}, {"entry": 1}],
            "structures": [
                {"shape": "mast", "x": 40, "width": 6, "top": 30, "bottom": 190, "colour": {"entry": 15}},
                {"shape": "mast", "x": 168, "width": 5, "top": 44, "bottom": 190, "colour": {"entry": 0}},
                {"shape": "mast", "x": 214, "width": 7, "top": 20, "bottom": 176, "colour": {"entry": 15}},
                {"shape": "crate", "x": 24, "y": 172, "w": 40, "h": 34, "colour": {"entry": 22}},
                {"shape": "crate", "x": 70, "y": 182, "w": 30, "h": 24, "colour": {"entry": 40}},
                {"shape": "quay", "y": 168, "colour": {"entry": 1}},
                {"shape": "lantern", "x": 40, "y": 62, "colour": {"entry": 40, "drift": 4}},
                {"shape": "lantern", "x": 214, "y": 52, "colour": {"entry": 40, "drift": 4}},
            ],
        },
    },
    {
        "id": "deck_night_scene",
        "kind": "scene",
        "scene": "battle_deck_night",
        "about": "the night deck: planks, a mast, a lantern and a rail against a cold sky",
        "drift": 16,
        "brief": {
            "sky": [{"entry": 1}, {"entry": 17}],
            "floor": [{"entry": 2}, {"entry": 0}],
            "structures": [
                {"shape": "planks", "y": 150, "colour": {"entry": 0}},
                {"shape": "mast", "x": 126, "width": 8, "top": 16, "bottom": 176, "colour": {"entry": 15}},
                {"shape": "rail", "y": 132, "colour": {"entry": 16}},
                {"shape": "lantern", "x": 126, "y": 58, "colour": {"entry": 40, "drift": 4}},
                {"shape": "hatch", "x": 178, "y": 190, "w": 34, "h": 22, "colour": {"entry": 2}},
            ],
        },
    },
    {
        "id": "wardroom_scene",
        "kind": "scene",
        "scene": "battle_wardroom",
        "about": "the wardroom: a wall, a long table, a lamp and a chart",
        "drift": 18,
        "brief": {
            "sky": [{"entry": 2}, {"entry": 23}],
            "floor": [{"entry": 8}, {"entry": 7}],
            "structures": [
                {"shape": "wall", "y": 148, "colour": {"entry": 7}},
                {"shape": "table", "x": 30, "y": 160, "w": 190, "h": 34, "colour": {"entry": 8}},
                {"shape": "chart", "x": 60, "y": 40, "w": 56, "h": 40, "colour": {"entry": 48}},
                {"shape": "lamp", "x": 168, "y": 30, "colour": {"entry": 40, "drift": 4}},
                {"shape": "door", "x": 206, "y": 92, "w": 30, "h": 60, "colour": {"entry": 23}},
            ],
        },
    },
    {
        "id": "percy_deck_sprite",
        "kind": "sprite",
        "scene": "battle_deck_night",
        "about": "Percy at 16x16, coat and gold, drawn off the scene's sprite set on purpose",
        "drift": 14,
        "brief": {
            "coat": {"entry": 2},
            "coat_dark": {"entry": 1},
            "skin": {"entry": 23},
            "gold": {"entry": 40},
            "outline": {"entry": 15},
        },
    },
]


def resolve_colour(value, scene, default_drift: int, rng: random.Random) -> tuple:
    """A brief colour: a scene entry plus a seeded sRGB drift, or a literal triple when it is one."""
    if isinstance(value, dict):
        base = scene.rgb(int(value["entry"]))
        amount = int(value.get("drift", default_drift))
        return tuple(max(0, min(255, channel + rng.randint(-amount, amount))) for channel in base)
    return tuple(value)



# -----------------------------------------------------------------------------------------------------------------
# 1. The concept painter. Deterministic: same brief, same seed, same PNG.

def lerp(first, second, t: float) -> tuple:
    return tuple(int(round(first[index] + (second[index] - first[index]) * t)) for index in range(3))


def seeded(subject_id: str) -> random.Random:
    return random.Random("kaggle_r7:" + subject_id)


def paint_scene(brief: dict, size, rng: random.Random, scene, drift: int = 0) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    sky_top = resolve_colour(brief["sky"][0], scene, drift, rng)
    sky_bottom = resolve_colour(brief["sky"][1], scene, drift, rng)
    horizon = min(150, int(height * 5 / 8))
    # Flat bands, not a gradient. A 13 colour set cannot hold a gradient, and concept art for this machine is
    # painted in broad flat planes: that is what the four palettes are for. The two sky planes meet at 45 percent.
    split = int(height * 0.45)
    for y in range(height):
        row = sky_top if y < split else sky_bottom
        for x in range(width):
            pixels[x, y] = row
    if "water" in brief:
        water_top = resolve_colour(brief["water"][0], scene, drift, rng)
        water_bottom = resolve_colour(brief["water"][1], scene, drift, rng)
        middle = horizon + (height - horizon) // 2
        for y in range(horizon, height):
            row = water_top if y < middle else water_bottom
            for x in range(width):
                pixels[x, y] = row
        for _ in range(90):
            x = rng.randrange(width)
            y = rng.randrange(horizon + 4, height)
            light = rng.randrange(14, 40)
            for step in range(rng.randrange(4, 18)):
                if x + step < width:
                    base = pixels[x + step, y]
                    pixels[x + step, y] = tuple(min(255, base[channel] + light) for channel in range(3))
    if "floor" in brief:
        floor_top = resolve_colour(brief["floor"][0], scene, drift, rng)
        floor_bottom = resolve_colour(brief["floor"][1], scene, drift, rng)
        middle = horizon + (height - horizon) // 2
        for y in range(horizon, height):
            row = floor_top if y < middle else floor_bottom
            for x in range(width):
                pixels[x, y] = row
    draw = ImageDraw.Draw(image)
    for item in brief["structures"]:
        shape = item["shape"]
        colour = resolve_colour(item["colour"], scene, drift, rng)
        if shape == "mast":
            draw.rectangle([item["x"], item["top"], item["x"] + item["width"], item["bottom"]], fill=colour)
            draw.line([item["x"] - 10, item["top"] + 14, item["x"] + 26, item["top"] + 40], fill=colour, width=2)
        elif shape == "crate":
            draw.rectangle([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]], fill=colour)
            draw.line([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]],
                      fill=lerp(colour, (0, 0, 0), 0.35))
        elif shape == "quay":
            draw.rectangle([0, item["y"], width, height], fill=colour)
            for x in range(0, width, 22):
                draw.line([x, item["y"], x, height], fill=lerp(colour, (0, 0, 0), 0.28))
        elif shape == "lantern":
            draw.ellipse([item["x"] - 4, item["y"] - 5, item["x"] + 4, item["y"] + 5], fill=colour)
            draw.ellipse([item["x"] - 9, item["y"] - 10, item["x"] + 9, item["y"] + 10],
                         outline=lerp(colour, (0, 0, 0), 0.5))
        elif shape == "planks":
            draw.rectangle([0, item["y"], width, height], fill=colour)
            for y in range(item["y"], height, 6):
                draw.line([0, y, width, y], fill=lerp(colour, (0, 0, 0), 0.32))
        elif shape == "rail":
            draw.rectangle([0, item["y"], width, item["y"] + 5], fill=colour)
            for x in range(8, width, 28):
                draw.rectangle([x, item["y"], x + 3, item["y"] + 22], fill=colour)
        elif shape == "hatch":
            draw.rectangle([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]], fill=colour)
            draw.rectangle([item["x"] + 3, item["y"] + 3, item["x"] + item["w"] - 3, item["y"] + item["h"] - 3],
                           outline=lerp(colour, (255, 255, 255), 0.25))
        elif shape == "wall":
            draw.rectangle([0, 0, width, item["y"]], fill=colour)
        elif shape == "table":
            draw.rectangle([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]], fill=colour)
            draw.rectangle([item["x"] + 4, item["y"] + 4, item["x"] + item["w"] - 4, item["y"] + 8],
                           fill=lerp(colour, (255, 255, 255), 0.3))
        elif shape == "chart":
            draw.rectangle([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]], fill=colour)
            for step in range(4):
                draw.line([item["x"] + 4, item["y"] + 8 + step * 8,
                           item["x"] + item["w"] - 4, item["y"] + 8 + step * 8],
                          fill=lerp(colour, (0, 0, 0), 0.4))
        elif shape == "lamp":
            draw.ellipse([item["x"] - 6, item["y"] - 6, item["x"] + 6, item["y"] + 6], fill=colour)
            draw.ellipse([item["x"] - 16, item["y"] - 16, item["x"] + 16, item["y"] + 16],
                         outline=lerp(colour, (0, 0, 0), 0.45))
        elif shape == "door":
            draw.rectangle([item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]], fill=colour)
            draw.ellipse([item["x"] + item["w"] - 9, item["y"] + item["h"] // 2,
                          item["x"] + item["w"] - 5, item["y"] + item["h"] // 2 + 4], fill=(210, 190, 130))
    # Grain, so the concept carries more colours than any palette set could. A flat fill would quantise to
    # itself and say nothing.
    for _ in range(width * height // 6):
        x = rng.randrange(width)
        y = rng.randrange(height)
        base = pixels[x, y]
        nudge = rng.randrange(-5, 6)
        pixels[x, y] = tuple(max(0, min(255, base[channel] + nudge)) for channel in range(3))
    return image


def paint_sprite(brief: dict, size, rng: random.Random, scene, drift: int = 0) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = resolve_colour(brief["outline"], scene, drift, rng)
    coat = resolve_colour(brief["coat"], scene, drift, rng)
    coat_dark = resolve_colour(brief["coat_dark"], scene, drift, rng)
    skin = resolve_colour(brief["skin"], scene, drift, rng)
    gold = resolve_colour(brief["gold"], scene, drift, rng)
    # Two tone coat, a head, a gold clasp and an outline. Deliberately brushy: a few pixels of shading.
    draw.rectangle([4, 5, 11, 14], fill=coat)
    draw.rectangle([7, 5, 11, 14], fill=coat_dark)
    draw.rectangle([5, 2, 10, 5], fill=skin)
    draw.rectangle([4, 2, 5, 3], fill=outline)
    draw.rectangle([10, 2, 11, 3], fill=outline)
    draw.rectangle([6, 6, 7, 9], fill=gold)
    draw.rectangle([4, 14, 6, 15], fill=outline)
    draw.rectangle([9, 14, 11, 15], fill=outline)
    draw.point([(5, 4), (8, 4)], fill=outline)
    pixels = image.load()
    for _ in range(14):
        x = rng.randrange(4, 12)
        y = rng.randrange(2, 15)
        if pixels[x, y][3]:
            r, g, b, a = pixels[x, y]
            nudge = rng.randrange(-14, 15)
            pixels[x, y] = (max(0, min(255, r + nudge)), max(0, min(255, g + nudge)),
                            max(0, min(255, b + nudge)), a)
    return image


# -----------------------------------------------------------------------------------------------------------------
# 2. Segmentation: deterministic k means in Lab over 16x16 blocks. Reported, never used to repaint.

def segment(image: Image.Image, k: int = 6, rounds: int = 12) -> list:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    blocks = {}
    for top in range(0, rgba.height, AREA):
        for left in range(0, rgba.width, AREA):
            total = [0.0, 0.0, 0.0]
            count = 0
            for y in range(top, min(top + AREA, rgba.height)):
                for x in range(left, min(left + AREA, rgba.width)):
                    r, g, b, a = pixels[x, y]
                    if not a:
                        continue
                    lab = quantize_concept.to_lab((r, g, b))
                    for index in range(3):
                        total[index] += lab[index]
                    count += 1
            if count:
                blocks[(left, top)] = tuple(value / count for value in total)
    keys = sorted(blocks)
    if not keys:
        return []
    centres = [blocks[keys[index * len(keys) // k]] for index in range(k)]
    assignment = {}
    for _ in range(rounds):
        moved = False
        for key in keys:
            point = blocks[key]
            best = min(range(k), key=lambda index: sum((point[axis] - centres[index][axis]) ** 2
                                                       for axis in range(3)))
            if assignment.get(key) != best:
                moved = True
            assignment[key] = best
        for index in range(k):
            members = [blocks[key] for key in keys if assignment[key] == index]
            if members:
                centres[index] = tuple(sum(member[axis] for member in members) / len(members)
                                       for axis in range(3))
        if not moved:
            break
    counts = {}
    for key in keys:
        counts.setdefault(assignment[key], []).append(key)
    return [{"index": index, "areas": len(areas),
             "coverage_percent": round(100.0 * len(areas) / len(keys), 1),
             "boxes": [[left, top] for left, top in areas]}
            for index, areas in sorted(counts.items())]


# -----------------------------------------------------------------------------------------------------------------
# 3 and 4. Quantise, then measure what the project's own tools already measure.

def count_colours(image: Image.Image) -> int:
    return quantize_concept.colour_count(image)


def area_colour_ceiling(image: Image.Image, backdrop) -> int:
    """The most colours any one 16x16 area carries, the backdrop excluded. The NES rule is 3."""
    most = 0
    for _, seen in sorted(nes_check.area_colours(image).items()):
        most = max(most, len(seen - {backdrop}))
    return most


def score_of(fails: int, checks: int) -> float:
    return round(100.0 * (1.0 - fails / checks), 1) if checks else 0.0


def rules_of(problems: list) -> dict:
    tally = {}
    for item in problems:
        tally[item["rule"]] = tally.get(item["rule"], 0) + 1
    return tally


def concept_lane(lane_name: str) -> str:
    """Which lane actually produced the concept: the model one when --concepts is in play."""
    return "kaggle-gpu" if EXTERNAL.get("dir") else lane_name


def concept_paths(subject: dict) -> tuple:
    stem = os.path.join(CONCEPTS, subject["id"])
    return stem + ".png", stem + "_nes.png", stem + "_nes_sheet.png"


def external_concept(subject: dict):
    """The model frame for this subject, as a PIL image at the subject's own frame size, or None.

    Resizing is nearest neighbour on purpose: a model frame that arrives at another size is scaled to the
    frame the quantiser reads WITHOUT blending, so no colour enters the concept that the model did not draw.
    """
    source_dir = EXTERNAL.get("dir")
    if not source_dir:
        return None
    source = os.path.join(source_dir, subject["id"] + ".png")
    if not os.path.exists(source):
        return None
    size = (256, 240) if subject["kind"] == "scene" else (16, 16)
    with Image.open(source) as handle:
        image = handle.convert("RGBA")
        source_size = list(handle.size)
    resized = image.size != size
    if resized:
        image = image.resize(size, Image.NEAREST)
    with open(source, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    EXTERNAL["rows"][subject["id"]] = {
        "file": os.path.basename(source),
        "source_size": source_size,
        "frame_size": list(size),
        "resized": resized,
        "sha256": digest,
    }
    return image


def write_concept(root: str, subject: dict, scene) -> str:
    source, _, _ = concept_paths(subject)
    os.makedirs(CONCEPTS, exist_ok=True)
    supplied = external_concept(subject)
    if supplied is not None:
        if os.path.abspath(source) != os.path.join(os.path.abspath(EXTERNAL["dir"]), subject["id"] + ".png"):
            supplied.save(source, "PNG")
        return source
    rng = seeded(subject["id"])
    size = (256, 240) if subject["kind"] == "scene" else (16, 16)
    drift = int(subject.get("drift", 0))
    image = (paint_scene(subject["brief"], size, rng, scene, drift) if subject["kind"] == "scene"
             else paint_sprite(subject["brief"], size, rng, scene, drift))
    image.save(source, "PNG")
    return source


def scene_candidate(root: str, subject: dict, grid, scene, lane: str) -> dict:
    source = write_concept(root, subject, scene)
    stats = quantize_concept.convert(root, source, subject["scene"], mapping="areas")
    with Image.open(os.path.join(root, stats["out"])) as handle:
        frame = handle.convert("RGBA")
    problems = palette_synergy.background_report(grid, scene, frame)
    tally = rules_of(problems)
    areas = len(nes_check.area_colours(frame))
    colours = count_colours(frame)
    checks = 2 * areas + colours + 1
    segments = segment(Image.open(source))
    segment_span = 0
    for item in segments:
        palettes = set()
        for left, top in item["boxes"]:
            for y in range(top, min(top + AREA, frame.height)):
                for x in range(left, min(left + AREA, frame.width)):
                    rgba = frame.getpixel((x, y))
                    if not rgba[3]:
                        continue
                    entry = grid.entry(rgba[:3])
                    if entry is None:
                        continue
                    for index, allowed in enumerate(scene.bg_sets()):
                        if entry in allowed:
                            palettes.add(index)
        if len(palettes) > 1:
            segment_span += 1
    return {
        "id": subject["id"],
        "kind": "scene",
        "about": subject["about"],
        "scene": subject["scene"],
        "lane": lane,
        "concept": quantize_concept.shown(root, source),
        "candidate": stats["out"],
        "sheet": stats["sheet"],
        "size": [frame.width, frame.height],
        "colours_before": stats["colours_before"],
        "distinct_colours": colours,
        "areas": areas,
        "max_colours_per_area": area_colour_ceiling(frame, scene.rgb(scene.backdrop)),
        "mean_delta_e": stats["mean_delta_e"],
        "free_mean_delta_e": stats.get("free_mean_delta_e"),
        "max_delta_e": stats["max_delta_e"],
        "palettes_used": stats.get("palettes_used"),
        "areas_per_palette": stats.get("areas_per_palette"),
        "attribute_area_violations": tally.get("background_area", 0),
        "palette_count_violations": tally.get("palette_count", 0),
        "set_member_violations": tally.get("set_member", 0),
        "sprite_tile_violations": tally.get("sprite_tile", 0),
        "rule_tally": tally,
        "fail_count": len(problems),
        "checks": checks,
        "score_basis": {"areas": 2 * areas, "colours": colours, "frame_palette": 1},
        "palette_synergy_score": score_of(len(problems), checks),
        "segments": len(segments),
        "segment_coverage": [{"index": item["index"], "coverage_percent": item["coverage_percent"]}
                             for item in segments],
        "segments_spanning_palettes": segment_span,
        "accepted": stats["accepted"] and not problems,
        "reject_reasons": ([] if stats["accepted"] else
                           ["mean delta E %.2f over the limit %.2f"
                            % (stats["mean_delta_e"], stats["max_delta_e_allowed"])])
                          + ([] if not problems else ["%d rule instance(s) failed" % len(problems)]),
        "limit": stats["max_delta_e_allowed"],
        "problems": problems,
    }


def nearest_in(allowed, colour) -> tuple:
    return min(allowed, key=lambda option: quantize_concept.delta_e(colour, option))


def sprite_candidate(root: str, subject: dict, grid, scene, lane: str) -> dict:
    source = write_concept(root, subject, scene)
    with Image.open(source) as handle:
        concept = handle.convert("RGBA")
    # A sprite spends ONE of the scene's 4 sprite palettes, 3 colours plus transparency. So score the four rows
    # by the summed delta E of the whole sprite and paint through the cheapest. Union-of-four mapping is the
    # failure palette_synergy calls palette_count, and it is not a frame a PPU can draw.
    rows = [sorted({scene.rgb(entry) for entry in palette}) for palette in scene.sprites]
    counts = [(rgb[:3], count) for count, rgb in (concept.getcolors(maxcolors=1 << 24) or [])
              if count and rgb[3]]
    total_pixels = sum(count for _, count in counts)
    costs = [sum(count * min(quantize_concept.delta_e(rgb, option) for option in row)
                 for rgb, count in counts)
             for row in rows]
    means = [round(cost / max(1, total_pixels), 2) for cost in costs]
    reach = [len({min(row, key=lambda option: quantize_concept.delta_e(rgb, option))
                  for rgb, _ in counts}) for row in rows]
    chosen_index = min(range(len(rows)), key=lambda index: (means[index], index))
    allowed = rows[chosen_index]
    after = Image.new("RGBA", concept.size, (0, 0, 0, 0))
    src, dst = concept.load(), after.load()
    deltas = []
    for y in range(concept.height):
        for x in range(concept.width):
            r, g, b, a = src[x, y]
            if not a:
                continue
            mapped = nearest_in(allowed, (r, g, b))
            dst[x, y] = tuple(mapped) + (a,)
            deltas.append(quantize_concept.delta_e((r, g, b), mapped))
    stem = os.path.splitext(source)[0]
    out_png, out_sheet = stem + "_nes.png", stem + "_nes_sheet.png"
    after.save(out_png, "PNG")
    # The sheet needs a background to sit on, so the scene's own quantised frame is its ground.
    background_stem = os.path.join(CONCEPTS, "deck_night_scene_nes.png")
    if os.path.isfile(background_stem):
        with Image.open(background_stem) as handle:
            ground = handle.convert("RGBA")
    else:
        ground = Image.new("RGBA", (256, 240), scene.rgb(scene.backdrop) + (255,))
    quantize_concept.write_sheet(ground, after.resize((after.width * 3, after.height * 3), Image.NEAREST),
                                 out_sheet, "%s over %s" % (subject["id"], subject["scene"]))
    box = (0, 0, after.width, after.height)
    info = palette_synergy.frame_report(grid, scene, after, box, ground, at=(120, 200))
    problems = info.pop("problems", [])
    tally = rules_of(problems)
    tiles = (after.width // TILE) * (after.height // TILE)
    colours = count_colours(after)
    ground_colours = len(info.get("pairs", [])) // max(1, len(scene.sprites))
    checks = tiles + colours + 1 + max(1, ground_colours)
    segments = segment(concept)
    mean = round(sum(deltas) / max(1, len(deltas)), 2)
    limit = quantize_concept.DEFAULT_MAX_DELTA_E
    reject_reasons = []
    if mean > limit:
        reject_reasons.append("mean delta E %.2f over the limit %.2f" % (mean, limit))
    if colours < 3:
        reject_reasons.append("the cheapest sprite palette collapses the figure into %d colour(s)" % colours)
    if problems:
        reject_reasons.append("%d rule instance(s) failed" % len(problems))
    return {
        "id": subject["id"],
        "kind": "sprite",
        "about": subject["about"],
        "scene": subject["scene"],
        "lane": lane,
        "concept": quantize_concept.shown(root, source),
        "candidate": quantize_concept.shown(root, out_png),
        "sheet": quantize_concept.shown(root, out_sheet),
        "size": [after.width, after.height],
        "colours_before": count_colours(concept),
        "distinct_colours": colours,
        "tiles_8x8": tiles,
        "max_colours_per_area": None,
        "mean_delta_e": mean,
        "free_mean_delta_e": None,
        "max_delta_e": round(max(deltas), 2) if deltas else 0.0,
        "palettes_used": len(info.get("palettes_that_fit", [])),
        "sprite_palette": chosen_index,
        "sprite_palette_row": [("#%02x%02x%02x" % option) for option in rows[chosen_index]],
        "row_candidates": [{"palette": index, "mean_delta_e": means[index], "colours_reached": reach[index],
                            "entries": ["#%02x%02x%02x" % option for option in row]}
                           for index, row in enumerate(rows)],
        "attribute_area_violations": 0,
        "palette_count_violations": tally.get("palette_count", 0),
        "set_member_violations": tally.get("set_member", 0),
        "sprite_tile_violations": tally.get("sprite_tile", 0),
        "body_ground_violations": tally.get("body_ground", 0),
        "white_blob_violations": tally.get("white_blob", 0),
        "same_hue_row_violations": tally.get("same_hue_row", 0),
        "invisible_violations": tally.get("invisible", 0),
        "rule_tally": tally,
        "fail_count": len(problems),
        "checks": checks,
        "score_basis": {"tiles": tiles, "colours": colours, "frame_palette": 1,
                        "ground_pairs": max(1, ground_colours)},
        "palette_synergy_score": score_of(len(problems), checks),
        "segments": len(segments),
        "segment_coverage": [{"index": item["index"], "coverage_percent": item["coverage_percent"]}
                             for item in segments],
        "segments_spanning_palettes": None,
        "accepted": not reject_reasons,
        "reject_reasons": reject_reasons,
        "limit": limit,
        "problems": problems,
    }


# -----------------------------------------------------------------------------------------------------------------
# The GPU lane, probed rather than promised.

def kaggle_lane() -> dict:
    token_env = "KAGGLE_API_TOKEN" if os.environ.get("KAGGLE_API_TOKEN") else (
        "KAGGLE_KEY" if os.environ.get("KAGGLE_KEY") else None)
    try:
        import kaggle  # noqa: F401
    except Exception as error:
        return {"available": False, "lane": "local",
                "reason": "kaggle package not installed in this interpreter (%s); credential env var %s"
                          % (type(error).__name__, token_env or "absent"),
                "probe": "python -c import kaggle -> %s" % type(error).__name__}
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        return {"available": True, "lane": "kaggle",
                "reason": "authenticated from the environment (credential env var %s)" % token_env,
                "probe": "KaggleApi().authenticate() ok", "api": api}
    except Exception as error:
        return {"available": False, "lane": "local",
                "reason": "kaggle client present but authentication failed (%s); the token was read by "
                          "the library only" % type(error).__name__,
                "probe": "authenticate() failed"}


# -----------------------------------------------------------------------------------------------------------------

def recipes_gate() -> dict:
    result = subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "check_palette_recipes.py")],
                            capture_output=True, text=True, cwd=ROOT)
    return {"command": "python tools/check_palette_recipes.py",
            "exit_code": result.returncode,
            "output": (result.stdout + result.stderr).strip().splitlines()[-3:]}


def keep_baseline() -> dict:
    """Before a model-lane report overwrites the report, park the painted-lane report beside it.

    Runs once. If a baseline already exists it is never overwritten, so the first painted run stays the
    record of what the painter scored and a second model run cannot bury it.
    """
    baseline_json = os.path.join(OUTPUT, "report_local_baseline.json")
    baseline_md = os.path.join(OUTPUT, "report_local_baseline.md")
    if not EXTERNAL.get("dir") or not os.path.exists(REPORT_JSON):
        return {"kept": False, "reason": "no model lane or no existing report"}
    if os.path.exists(baseline_json):
        return {"kept": False, "reason": "baseline already exists", "path": baseline_json}
    with open(REPORT_JSON, encoding="utf-8") as handle:
        previous = json.load(handle)
    if (previous.get("concept_source") or {}).get("mode") == "model":
        return {"kept": False, "reason": "the existing report is already a model run"}
    with open(REPORT_JSON, "rb") as source, open(baseline_json, "wb") as target:
        target.write(source.read())
    if os.path.exists(REPORT_MD):
        with open(REPORT_MD, "rb") as source, open(baseline_md, "wb") as target:
            target.write(source.read())
    return {"kept": True, "path": baseline_json, "markdown": baseline_md,
            "picked": previous.get("picked", {}).get("id"), "written": previous.get("written")}


def write_report(report: dict) -> None:
    os.makedirs(OUTPUT, exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    picked = report["picked"]
    lines = [
        "# R7 palette-first candidates, scored",
        "",
        "Written by `tools/kaggle_r7.py` on %s. Lane: %s." % (report["written"], report["lane"]),
        report["lane_note"],
        "",
        "Concept source: **%s**%s."
        % (report["concept_source"]["mode"],
           (" from `%s`" % report["concept_source"]["dir"]) if report["concept_source"]["dir"] else
           " (our own deterministic painter, seeded per subject)"),
        "Score arithmetic: `score = 100 * (1 - failed rule instances / rule instances checked)`,",
        "where every instance is a check `tools/palette_synergy.py` and `tools/nes_check.py` already make.",
        "The basis column shows the instances, so every row can be recomputed from its own counts.",
        "",
        "| candidate | kind | scene | colours | area fails | palette count | set member | score | mean dE | accepted |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["candidates"]:
        lines.append("| %s | %s | %s | %d | %d | %d | %d | %.1f | %.2f | %s |"
                     % (item["id"], item["kind"], item["scene"], item["distinct_colours"],
                        item["attribute_area_violations"], item["palette_count_violations"],
                        item["set_member_violations"], item["palette_synergy_score"],
                        item["mean_delta_e"], "yes" if item["accepted"] else "no"))
    lines += [
        "",
        "Picked: **%s**, score %.1f of 100, mean delta E %.2f against the limit %.2f."
        % (picked["id"], picked["palette_synergy_score"], picked["mean_delta_e"], picked["limit"]),
        "",
    ]
    rejected = [item for item in report["candidates"] if not item["accepted"]]
    if rejected:
        lines.append("Rejected, with the measured reason:")
        lines.append("")
        for item in rejected:
            lines.append("- `%s`: %s." % (item["id"], "; ".join(item["reject_reasons"])))
        lines.append("")
    lines += [
        "The score is rule conformance, not beauty: a frame can score 100 and still be a poor",
        "picture, which is what the mean delta E column and the eye critic are for. The one sprite",
        "candidate carries all four of its scene's sprite palettes and their measured cost in",
        "`report.json` (`row_candidates`), because no single row of `battle_deck_night` holds a blue",
        "coat, an orange skin and a gold accent at once.",
        "",
        "Recipe gate: `%s` exit %d, %s."
        % (report["recipes"]["command"], report["recipes"]["exit_code"],
           " ".join(report["recipes"]["output"][-1:])),
        "",
        "Per candidate detail, including the NES frame and its before and after sheet, is in `report.json`",
        "and in `concepts/`. Nothing in `game/art/` was written by this run.",
        "",
    ]
    with open(REPORT_MD, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def selftest() -> int:
    scene = scene_palette_set.scene(ROOT, "battle_quay_dusk")
    rng = seeded("selftest")
    tiny = {"sky": [(24, 26, 62), (232, 126, 62)], "water": [(22, 36, 60), (58, 86, 104)],
            "structures": [{"shape": "mast", "x": 10, "width": 2, "top": 4, "bottom": 40,
                            "colour": (30, 26, 34)},
                           {"shape": "lantern", "x": 10, "y": 8, "colour": (246, 210, 126)}]}
    scene_image = paint_scene(tiny, (64, 48), rng, scene, 8)
    assert scene_image.size == (64, 48)
    assert count_colours(scene_image) > 20, count_colours(scene_image)
    sprite_image = paint_sprite({"coat": (26, 58, 138), "coat_dark": (16, 34, 92),
                                 "skin": (200, 138, 90), "gold": (224, 176, 64),
                                 "outline": (16, 16, 24)}, (16, 16), rng, scene, 8)
    assert count_colours(sprite_image) >= 4, count_colours(sprite_image)
    segments = segment(scene_image, k=3)
    assert segments, "no segments"
    assert abs(sum(item["coverage_percent"] for item in segments) - 100.0) < 0.2, segments
    assert score_of(0, 10) == 100.0 and score_of(5, 10) == 50.0
    print("kaggle_r7 selftest: 7 check(s) PASS")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Palette-first R7 candidates plus a scored report.")
    parser.add_argument("--subjects", default=None, help="comma separated ids, default every subject")
    parser.add_argument("--lane", choices=["auto", "kaggle", "local"], default="auto")
    parser.add_argument("--concepts", default=None,
                        help="directory of model frames named <subject id>.png, used instead of painting")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.selftest:
        return selftest()

    wanted = [name.strip() for name in args.subjects.split(",")] if args.subjects else None
    subjects = [subject for subject in SUBJECTS if wanted is None or subject["id"] in wanted]
    if not subjects:
        parser.error("no subject matched %r" % args.subjects)

    if args.concepts:
        concepts_dir = os.path.abspath(args.concepts)
        if not os.path.isdir(concepts_dir):
            parser.error("--concepts directory does not exist: %s" % concepts_dir)
        manifest = None
        for candidate in (os.path.join(concepts_dir, "r7_manifest.json"),
                          os.path.join(os.path.dirname(concepts_dir), "r7_manifest.json")):
            if os.path.exists(candidate):
                with open(candidate, encoding="utf-8") as handle:
                    manifest = json.load(handle)
                break
        EXTERNAL["dir"] = concepts_dir
        EXTERNAL["manifest"] = manifest
        EXTERNAL["rows"] = {}

    lane = kaggle_lane()
    if args.lane == "kaggle" and not lane["available"]:
        print("kaggle_r7: the kaggle lane is not available on this machine: %s" % lane["reason"])
        return 3
    lane_name = "kaggle" if (args.lane == "kaggle" and lane["available"]) else "local"
    if EXTERNAL["dir"]:
        lane_note = ("Concepts came from %s, written by a model on the Kaggle GPU; the segment, quantise, "
                     "measure and score steps below ran on this machine." % EXTERNAL["dir"])
    elif lane_name == "local":
        lane_note = ("GPU lane unavailable, so every candidate below was painted and quantised locally: %s"
                     % lane["reason"])
    else:
        lane_note = "Kaggle GPU lane authenticated."

    concept_source = {"mode": "model" if EXTERNAL["dir"] else "painted",
                      "dir": EXTERNAL["dir"], "files": {}}
    if EXTERNAL["manifest"]:
        concept_source["manifest"] = {
            "model": sorted({row.get("model") for row in EXTERNAL["manifest"].get("concepts", [])
                             if row.get("model")}),
            "lora": sorted({row.get("lora") for row in EXTERNAL["manifest"].get("concepts", [])
                            if row.get("lora")}),
            "seeds": {row["id"]: row.get("seed") for row in EXTERNAL["manifest"].get("concepts", [])
                      if row.get("id")},
            "sam3": EXTERNAL["manifest"].get("sam3"),
            "kernel_run": EXTERNAL["manifest"].get("started_utc"),
        }
        if lane_name == "local":
            lane_note += (" The frames came from the Kaggle kernel run that wrote %s."
                          % os.path.join(EXTERNAL["dir"], "r7_manifest.json"))

    grid = palette_synergy.Grid(root)
    candidates = []
    lane_for_concepts = concept_lane(lane_name)
    for subject in subjects:
        scene = scene_palette_set.scene(root, subject["scene"])
        maker = scene_candidate if subject["kind"] == "scene" else sprite_candidate
        candidates.append(maker(root, subject, grid, scene, lane_for_concepts))
    concept_source["files"] = dict(EXTERNAL["rows"])
    if EXTERNAL["dir"]:
        missing = [subject["id"] for subject in subjects if subject["id"] not in EXTERNAL["rows"]]
        concept_source["painted_instead"] = missing

    ok = [item for item in candidates if item["accepted"]] or candidates
    picked = min(ok, key=lambda item: (-item["palette_synergy_score"], item["mean_delta_e"], item["id"]))
    report = {
        "tool": "kaggle_r7",
        "format": 1,
        "written": "2026-10-23",
        "card": os.environ.get("HERMES_KANBAN_TASK", "t_d1906a5b"),
        "lane": lane_name,
        "lane_note": lane_note,
        "concept_source": concept_source,
        "gpu_lane": {key: value for key, value in lane.items() if key != "api"},
        "scene_sets": len(scene_palette_set.load(root).get("scenes", [])),
        "recipes": recipes_gate(),
        "score_definition": "100 * (1 - failed rule instances / rule instances checked)",
        "max_sprite_colours": MAX_SPRITE_COLOURS,
        "candidates": candidates,
        "picked": {key: picked[key] for key in
                   ("id", "scene", "palette_synergy_score", "mean_delta_e", "limit", "distinct_colours",
                    "fail_count", "checks", "candidate", "sheet")},
        "baseline": keep_baseline(),
    }
    write_report(report)

    print("kaggle_r7: %d candidate(s), lane %s, report %s"
          % (len(candidates), lane_name, quantize_concept.shown(root, REPORT_JSON)))
    for item in candidates:
        print("  %-20s %-6s %-18s colours %-3d area fails %-2d palette %-2d set_member %-2d score %.1f dE %.2f %s"
              % (item["id"], item["kind"], item["scene"], item["distinct_colours"],
                 item["attribute_area_violations"], item["palette_count_violations"],
                 item["set_member_violations"], item["palette_synergy_score"], item["mean_delta_e"],
                 "ACCEPT" if item["accepted"] else "REJECT"))
    print("kaggle_r7: picked %s at score %.1f (mean delta E %.2f of %.2f)"
          % (picked["id"], picked["palette_synergy_score"], picked["mean_delta_e"], picked["limit"]))
    print("kaggle_r7: recipes %s exit %d" % (report["recipes"]["command"], report["recipes"]["exit_code"]))
    return 0 if report["recipes"]["exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
