"""contrast_check.py: does this sprite sheet read on the ground it stands on?

The redraw queue (data\\sprite_redraw_queue.json) names this tool in every check block and states the
numbers it must measure. This file is that measurement, nothing more: one PNG sheet plus a declared
ground, every opaque colour compared with that ground, then the blob test.

The rules, and where each one comes from:

1. Contrast floor. SPRITE-CRAFT 12.1 and SPRITE-CRITIQUE section 6: the figure's outline against the
   ground must be at least 3.0 : 1, and its largest fill at least 2.0 : 1. Contrast is the WCAG ratio
   on relative luminance, (Llight + 0.05) / (Ldark + 0.05), which is the arithmetic that produced every
   number already written into the queue (it reproduces 1.73 for $0F on $02, 6.41 for $10 on $02 and
   5.03 for $0F on $00 to the printed digit).
2. No invisible colour. A fill whose contrast with the ground is 1.00 is the ground, so the figure has
   no edge there. The declaration is measured against every opaque colour, because a colour equal to
   the ground is invisible whether it is read as the outline or as a fill. A ratio that rounds to 1.00
   counts as 1.00: two entries can share a luminance ($31 and $38 both measure 0.704) without being
   the same colour, and either of them on the other is still an invisible edge.
3. Grid steps. SPRITE-CRITIQUE section 6: on the 2C02 grid (4 brightness rows by 16 hue columns) two
   palette steps means |drow| + |dcol| >= 2 from the ground's own entry. An entry that appears at
   several indices (the ten blacks decode to the same #000000) is scored at its closest legal index,
   because the PNG cannot say which index the artist meant; the dark entries are one family on this
   grid and the queue's own numbers treat them as one.
4. The blob test, SPRITE-CRAFT 8.5, four numbers per frame:
   a. the lightest single entry is under 30 percent of the drawn pixels;
   b. no drawn row is without a dark pixel (0 rows);
   c. at least 3 dark runs in the body block;
   d. at least 8 interior dark pixels in the body block.
   Where this tool fixes a term the document leaves loose, it says so and it prints the number:
   - the dark tone is the sheet's darkest opaque colour, the same tone rule 1 measures as the outline.
     SPRITE-CRAFT 5.2 is why it is not a fixed black: the correct outline on the night road is $10,
     which is a light grey, and a test pinned to black would fail every correct road sprite.
   - a drawn row is a row inside the frame with at least one opaque pixel.
   - the body block is the lower half of the frame's drawn bounding box, which is the rows 8 to 15 of
     a full 16 x 16 cell, the split the queue already uses in its palette plans.
   - a dark run is one 4-connected region of dark pixels inside the body block, so a collar band, a
     belt and a trouser break count 3, and the outline ring counts 1.
   - an interior dark pixel is a dark pixel with all four neighbours opaque and at least one of them
     not dark: that is a dark line inside the figure, not the silhouette edge and not a solid mass.
   - every one of the four numbers is measured frame by frame and the worst frame is the one reported,
     because one bad frame is on screen for as long as the good ones. The queue's own snapshot used
     frame 0, so the two agree on frame 0 and this tool reports a later frame when it is worse; the
     line names the frame, which is the reconciliation.
5. Frame geometry. --frame-w and --frame-h override everything. Then the queue
   (data\\sprite_redraw_queue.json) states frame_w, frame_h and frames for the sheets it lists. Then the
   sheet's OWN sidecar beside the PNG (spr_foo.png -> spr_foo.json) states frame_w and frame_h, which is
   how every sheet the art lane wrote in v2 is defined: a 168x32 battle sheet is seven frames of 24x32,
   not one 168x32 frame. A sheet with neither falls back to one frame the size of the image, or to square
   frames when the width divides evenly by the height. The sidecar may also carry "layer": true, which
   declares the sheet a tiled layer rather than a figure; palette_synergy.py reads that through here and
   does not infer it from the width (gamedev ruling, PALETTE-RULINGS-2026-10-24.md section 7).

The grounds are the two the queue declares, deck ($00, luminance 0.202) and night_road ($02, 0.036),
and any other colour may be passed as $0F or #rrggbb. The luminances are computed from
data\\nes_palette.json (built and cited by tools\\art\\nes_palette_build.py) and cross checked against
the values the queue declares, so a palette change cannot silently move a floor.

Usage:
    python tools\\art\\contrast_check.py game\\sprites_src\\chars\\percy_ow.png --ground deck --ground night_road
    python tools\\art\\contrast_check.py game\\sprites_src\\chars\\sailor_ow_v2.png --ground night_road --json out.json
    python tools\\art\\contrast_check.py game\\sprites_src\\chars\\percy_ow.png            (both grounds)
    python tools\\art\\contrast_check.py --selftest

Exit code 0 when every rule passes on every stated ground, 1 when any rule fails.

What it deliberately does not do: it does not judge whether the figure reads as the character, it does
not composite the sheet onto a real frame (that is nes_composite_check.py), and it does not redraw
anything. It measures, it prints the number, and it says PASS or FAIL.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import Counter

from PIL import Image

# -----------------------------------------------------------------------------------------------------------------
# The numbers the queue and SPRITE-CRAFT state. None of these may drift without a spec change.

OUTLINE_FLOOR = 3.0          # SPRITE-CRAFT 12.1: outline against the ground
FILL_FLOOR = 2.0             # SPRITE-CRAFT 12.1: largest fill against the ground
INVISIBLE_RATIO = 1.00       # a fill equal to a declared background entry
GRID_FLOOR = 2               # 2C02 grid: |drow| + |dcol| >= 2 from the ground entry

BLOB_LIGHT_CEILING_PC = 30.0  # SPRITE-CRAFT 8.5.1: lightest entry under 30 percent of drawn pixels
BLOB_ROWS_WITHOUT_DARK = 0    # SPRITE-CRAFT 8.5.2
BLOB_DARK_RUNS = 3            # SPRITE-CRAFT 8.5.3
BLOB_INTERIOR_DARK = 8        # SPRITE-CRAFT 8.5.4

GROUNDS = {
    "deck": {"code": "$00", "declared": 0.202},
    "night_road": {"code": "$02", "declared": 0.036},
}

GROUND_ALIASES = {
    "deck": "deck",
    "ship_deck": "deck",
    "deck_night": "deck",
    "bg_battle_deck_night": "deck",
    "night_road": "night_road",
    "road": "night_road",
    "nightroad": "night_road",
    "night": "night_road",
}

# The thirteen entries the queue's check blocks declare, and the six ratios SPRITE-CRAFT 12.1 prints.
# The selftest re-derives both from the palette file, which is how the tool proves its arithmetic.
QUEUE_LUMINANCE = {
    "$0F": 0.0, "$02": 0.036, "$01": 0.07, "$12": 0.138, "$00": 0.202, "$17": 0.242, "$21": 0.44,
    "$10": 0.503, "$28": 0.542, "$36": 0.668, "$31": 0.704, "$38": 0.704, "$30": 0.973,
}

PUBLISHED_RATIOS = [
    ("$0F", "night_road", 1.73),
    ("$10", "night_road", 6.41),
    ("$00", "night_road", 2.91),
    ("$0F", "deck", 5.03),
    ("$30", "deck", 4.07),
    ("$30", "night_road", 11.86),
    ("$31", "deck", 3.00),
]


def repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


# -----------------------------------------------------------------------------------------------------------------
# Luminance and contrast.

def srgb_to_linear(value: float) -> float:
    value = value / 255.0
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    """WCAG relative luminance of an 8 bit sRGB colour. This is the arithmetic behind every queue number."""
    return (0.2126 * srgb_to_linear(rgb[0])
            + 0.7152 * srgb_to_linear(rgb[1])
            + 0.0722 * srgb_to_linear(rgb[2]))


def contrast(first: float, second: float) -> float:
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def rgb_hex(rgb) -> str:
    return "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])


def hex_to_rgb(value: str) -> tuple:
    value = value.strip().lower().lstrip("#")
    if len(value) != 6:
        raise SystemExit("%r is not a #RRGGBB colour" % value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


# -----------------------------------------------------------------------------------------------------------------
# Palette.

def load_palette(root: str) -> dict:
    """data\\nes_palette.json: index, code and hex for the 64 outputs of the 2C02."""
    path = os.path.join(root, "data", "nes_palette.json")
    if not os.path.isfile(path):
        raise SystemExit("%s does not exist; the luminance table lives there" % path)
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("%s has no entries list" % path)
    by_code = {}
    index_of = {}
    codes_of_rgb = {}
    for entry in entries:
        code = entry["code"]
        rgb = hex_to_rgb(entry["hex"])
        by_code[code] = rgb
        index_of[code] = int(entry["index"])
        codes_of_rgb.setdefault(rgb, []).append(code)
    return {
        "path": path,
        "by_code": by_code,
        "index_of": index_of,
        "codes_of_rgb": codes_of_rgb,
        "luminance": {code: luminance(rgb) for code, rgb in by_code.items()},
    }


def codes_for(palette: dict, rgb) -> list:
    return palette["codes_of_rgb"].get(tuple(rgb), [])


def describe_colour(palette: dict, rgb) -> str:
    codes = codes_for(palette, rgb)
    if not codes:
        return "%s off palette" % rgb_hex(rgb)
    return "%s %s" % (rgb_hex(rgb), "/".join(codes))


# -----------------------------------------------------------------------------------------------------------------
# The sheet and its frames.

def load_sheet(path: str) -> Image.Image:
    if not os.path.isfile(path):
        raise SystemExit("%s does not exist" % path)
    with Image.open(path) as image:
        sheet = image.convert("RGBA")
    return sheet


def queue_entry(root: str, png_path: str):
    """The queue entry for this sheet, if the queue lists it. It carries the frame geometry."""
    path = os.path.join(root, "data", "sprite_redraw_queue.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8-sig") as handle:
        queue = json.load(handle)
    target = os.path.normcase(os.path.abspath(png_path)).replace("\\", "/")
    for entry in queue.get("entries", []):
        known = str(entry.get("path", "")).strip()
        if not known:
            continue
        candidate = os.path.normcase(os.path.abspath(os.path.join(root, known))).replace("\\", "/")
        if candidate == target:
            return entry
    return None


def sidecar_entry(png_path: str):
    """The sheet's own sidecar beside the PNG (spr_foo.png -> spr_foo.json), or None.

    This is the declaration the art lane writes for every sheet: frame_w, frame_h, frames, and optionally
    "layer": true for a tiled layer. It is read before any size is guessed from the image, because guessing
    turned every 168x32 battle sheet into one 168x32 frame (PALETTE-RULINGS-2026-10-24.md section 7).
    """
    path = os.path.splitext(png_path)[0] + ".json"
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def geometry(root: str, png_path: str, image: Image.Image, frame_w, frame_h) -> dict:
    """(frame width, frame height, how it was decided) plus the sheet's layer declaration."""
    declared = sidecar_entry(png_path)
    declared_layer = bool(declared.get("layer")) if declared else False
    if frame_w and frame_h:
        return {"frame_w": frame_w, "frame_h": frame_h,
                "how": "the size given with --frame-w and --frame-h", "queue_id": None, "queue_frames": None,
                "declared_layer": declared_layer}
    entry = queue_entry(root, png_path)
    if entry and entry.get("frame_w") and entry.get("frame_h"):
        return {"frame_w": int(entry["frame_w"]), "frame_h": int(entry["frame_h"]),
                "how": "data\\sprite_redraw_queue.json (%s)" % entry.get("id", "no id"),
                "queue_id": entry.get("id"), "queue_frames": entry.get("frames"),
                "declared_layer": bool(entry.get("layer", declared_layer))}
    if declared and declared.get("frame_w") and declared.get("frame_h"):
        return {"frame_w": int(declared["frame_w"]), "frame_h": int(declared["frame_h"]),
                "how": "the sheet's own sidecar (%s.json)" % os.path.basename(os.path.splitext(png_path)[0]),
                "queue_id": None, "queue_frames": declared.get("frames"),
                "declared_layer": declared_layer}
    height = image.height
    if height and image.width % height == 0:
        return {"frame_w": height, "frame_h": height,
                "how": "square frames, because the width divides evenly by the height",
                "queue_id": None, "queue_frames": None, "declared_layer": declared_layer}
    return {"frame_w": image.width, "frame_h": image.height,
            "how": "one frame the size of the image; pass --frame-w and --frame-h for a sheet the queue does not list",
            "queue_id": None, "queue_frames": None, "declared_layer": declared_layer}


def frames_of(image: Image.Image, frame_w: int, frame_h: int) -> list:
    """Every frame as (left, top, width, height), left to right then top to bottom."""
    out = []
    for top in range(0, image.height - frame_h + 1, frame_h):
        for left in range(0, image.width - frame_w + 1, frame_w):
            out.append((left, top, frame_w, frame_h))
    return out


def frame_pixels(image: Image.Image, box) -> list:
    left, top, width, height = box
    pixels = image.load()
    rows = []
    for y in range(top, top + height):
        rows.append([pixels[x, y] for x in range(left, left + width)])
    return rows


# -----------------------------------------------------------------------------------------------------------------
# Measurement.

def sheet_colours(image: Image.Image) -> Counter:
    counts = Counter()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a:
                counts[(r, g, b)] += 1
    return counts


def darkest_tone(counts: Counter) -> tuple:
    """The sheet's darkest opaque colour: the outline tone. Ties go to the colour with more pixels."""
    return min(counts, key=lambda rgb: (luminance(rgb), -counts[rgb], rgb))


def lightest_tone(counts: Counter) -> tuple:
    return max(counts, key=lambda rgb: (luminance(rgb), counts[rgb], rgb))


def grid_steps(palette: dict, rgb, ground_index: int):
    """Best (largest) |drow| + |dcol| from the ground entry, or None when the colour is off palette."""
    codes = codes_for(palette, rgb)
    if not codes:
        return None
    best = None
    for code in codes:
        index = palette["index_of"][code]
        steps = abs((index >> 4) - (ground_index >> 4)) + abs((index & 0x0F) - (ground_index & 0x0F))
        best = steps if best is None else max(best, steps)
    return best


def rule(rule_id: str, ok: bool, measured: str, detail: str) -> dict:
    return {"rule": rule_id, "ok": bool(ok), "measured": measured, "detail": detail}


def contrast_rules(counts: Counter, palette: dict, ground: dict) -> list:
    """The four contrast rules for one ground. ground: name, code, rgb, luminance, declared."""
    total = sum(counts.values())
    floor = ground["luminance"]
    rules = []

    tone = darkest_tone(counts)
    ratio = contrast(luminance(tone), floor)
    rules.append(rule(
        "outline",
        ratio >= OUTLINE_FLOOR,
        "%.2f : 1" % ratio,
        "%s darkest tone, %d px   floor %.2f" % (describe_colour(palette, tone), counts[tone], OUTLINE_FLOOR),
    ))

    fills = [rgb for rgb in counts if rgb != tone] or [tone]
    largest = max(fills, key=lambda rgb: (counts[rgb], -luminance(rgb)))
    fill_ratio = contrast(luminance(largest), floor)
    rules.append(rule(
        "largest fill",
        fill_ratio >= FILL_FLOOR,
        "%.2f : 1" % fill_ratio,
        "%s %d px %.1f%%   floor %.2f"
        % (describe_colour(palette, largest), counts[largest], 100.0 * counts[largest] / total, FILL_FLOOR),
    ))

    invisible = sorted((rgb for rgb in counts if round(contrast(luminance(rgb), floor), 2) == INVISIBLE_RATIO),
                       key=lambda rgb: -counts[rgb])
    names = ", ".join("%s %d px" % (describe_colour(palette, rgb), counts[rgb]) for rgb in invisible)
    rules.append(rule(
        "background entry",
        not invisible,
        "%d colour%s at 1.00" % (len(invisible), "" if len(invisible) == 1 else "s"),
        (names + "   limit 0") if invisible else "no opaque colour equals this ground",
    ))

    if ground.get("index") is None:
        steps_line = None
    else:
        measured = [(grid_steps(palette, rgb, ground["index"]), rgb) for rgb in counts]
        off = [rgb for steps, rgb in measured if steps is None]
        known = [(steps, rgb) for steps, rgb in measured if steps is not None]
        if not known:
            steps_line = None
        else:
            worst = min(known, key=lambda item: (item[0], -counts[item[1]]))
            steps_line = rule(
                "grid steps",
                worst[0] >= GRID_FLOOR,
                "%d" % worst[0],
                "%s, worst of %d colour%s%s   floor %d"
                % (describe_colour(palette, worst[1]), len(known), "" if len(known) == 1 else "s",
                   (", %d off palette" % len(off)) if off else "", GRID_FLOOR),
            )
    if steps_line is not None:
        rules.append(steps_line)
    return rules


def body_block(rows: list):
    """(top, bottom) of the body block: the lower half of the frame's drawn bounding box."""
    drawn = [y for y, row in enumerate(rows) if any(px[3] for px in row)]
    if not drawn:
        return None
    top, bottom = drawn[0], drawn[-1]
    height = bottom - top + 1
    return (top + (height + 1) // 2, bottom)


def is_dark(px, dark) -> bool:
    return px[3] > 0 and (px[0], px[1], px[2]) == dark


def blob_measures(rows: list, dark) -> dict:
    """The four SPRITE-CRAFT 8.5 numbers for one frame."""
    height = len(rows)
    width = len(rows[0]) if height else 0
    counts = Counter()
    for row in rows:
        for px in row:
            if px[3]:
                counts[(px[0], px[1], px[2])] += 1
    drawn = sum(counts.values())
    if not drawn:
        return {"empty": True}
    lightest = lightest_tone(counts)
    light_share = 100.0 * counts[lightest] / drawn

    without_dark = []
    for y in range(height):
        if not any(px[3] for px in rows[y]):
            continue
        if not any(is_dark(px, dark) for px in rows[y]):
            without_dark.append(y)

    block = body_block(rows)
    dark_runs = 0
    interior = 0
    if block is not None:
        top, bottom = block
        seen = set()
        for y in range(top, bottom + 1):
            for x in range(width):
                if not is_dark(rows[y][x], dark) or (x, y) in seen:
                    continue
                dark_runs += 1
                stack = [(x, y)]
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if nx < 0 or ny < 0 or nx >= width or ny < top or ny > bottom:
                            continue
                        if (nx, ny) in seen or not is_dark(rows[ny][nx], dark):
                            continue
                        seen.add((nx, ny))
                        stack.append((nx, ny))
        for y in range(top, bottom + 1):
            for x in range(width):
                if not is_dark(rows[y][x], dark):
                    continue
                neighbours = []
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        neighbours.append(None)
                    else:
                        neighbours.append(rows[ny][nx])
                if any(px is None or px[3] == 0 for px in neighbours):
                    continue
                if any(not is_dark(px, dark) for px in neighbours):
                    interior += 1

    return {
        "empty": False,
        "drawn": drawn,
        "lightest": lightest,
        "light_share": light_share,
        "rows_without_dark": without_dark,
        "dark_runs": dark_runs,
        "interior_dark": interior,
        "body_block": block,
        "counts": counts,
    }


def blob_rules(image: Image.Image, frames: list, palette: dict, dark) -> dict:
    """The blob test over every frame, worst frame reported for each of the four numbers."""
    per_frame = []
    for number, box in enumerate(frames):
        measured = blob_measures(frame_pixels(image, box), dark)
        measured["frame"] = number
        measured["box"] = box
        per_frame.append(measured)
    live = [item for item in per_frame if not item["empty"]]
    if not live:
        return {"ok": False, "rules": [rule("blob", False, "no drawn pixels", "the sheet is empty")], "frames": per_frame}

    worst_light = max(live, key=lambda item: item["light_share"])
    worst_rows = max(live, key=lambda item: (len(item["rows_without_dark"]), -item["frame"]))
    worst_runs = min(live, key=lambda item: (item["dark_runs"], item["frame"]))
    worst_interior = min(live, key=lambda item: (item["interior_dark"], item["frame"]))

    rules = [
        rule("blob lightest entry",
             worst_light["light_share"] < BLOB_LIGHT_CEILING_PC,
             "%.1f%% of drawn pixels" % worst_light["light_share"],
             "%s frame %d   ceiling %.0f%%"
             % (describe_colour(palette, worst_light["lightest"]), worst_light["frame"], BLOB_LIGHT_CEILING_PC)),
        rule("blob rows without dark",
             len(worst_rows["rows_without_dark"]) == BLOB_ROWS_WITHOUT_DARK,
             "%d row%s" % (len(worst_rows["rows_without_dark"]),
                           "" if len(worst_rows["rows_without_dark"]) == 1 else "s"),
             "frame %d rows %s   limit %d"
             % (worst_rows["frame"],
                ", ".join(str(y) for y in worst_rows["rows_without_dark"]) or "none",
                BLOB_ROWS_WITHOUT_DARK)),
        rule("blob dark runs",
             worst_runs["dark_runs"] >= BLOB_DARK_RUNS,
             "%d in the body block" % worst_runs["dark_runs"],
             "frame %d, body rows %s   floor %d"
             % (worst_runs["frame"],
                ("%d to %d" % worst_runs["body_block"]) if worst_runs["body_block"] else "none",
                BLOB_DARK_RUNS)),
        rule("blob interior dark",
             worst_interior["interior_dark"] >= BLOB_INTERIOR_DARK,
             "%d px" % worst_interior["interior_dark"],
             "frame %d   floor %d" % (worst_interior["frame"], BLOB_INTERIOR_DARK)),
    ]
    return {"ok": all(item["ok"] for item in rules), "rules": rules, "frames": per_frame}


# -----------------------------------------------------------------------------------------------------------------
# The run.

def analyse(image: Image.Image, geometry_info: dict, palette: dict, grounds: list) -> dict:
    counts = sheet_colours(image)
    if not counts:
        raise SystemExit("the sheet has no opaque pixels")
    dark = darkest_tone(counts)
    frames = frames_of(image, geometry_info["frame_w"], geometry_info["frame_h"])
    ground_reports = []
    for ground in grounds:
        ground_reports.append({"ground": ground, "rules": contrast_rules(counts, palette, ground)})
    blob = blob_rules(image, frames, palette, dark)
    return {
        "size": [image.width, image.height],
        "geometry": geometry_info,
        "colours": counts,
        "dark": dark,
        "frames": frames,
        "grounds": ground_reports,
        "blob": blob,
    }


def all_rules(report: dict) -> list:
    rules = []
    for ground in report["grounds"]:
        rules += ground["rules"]
    rules += report["blob"]["rules"]
    return rules


def describe(report: dict, path: str, palette: dict, quiet: bool = False) -> list:
    problems = [item for item in all_rules(report) if not item["ok"]]
    total = sum(report["colours"].values())
    frames = report["geometry"]
    lines = []
    lines.append("%s  %dx%d  %d frame%s of %dx%d  %d colour%s  %s"
                 % (path, report["size"][0], report["size"][1],
                    len(report["frames"]), "" if len(report["frames"]) == 1 else "s",
                    frames["frame_w"], frames["frame_h"],
                    len(report["colours"]), "" if len(report["colours"]) == 1 else "s",
                    "PASS" if not problems else "FAIL %d problem(s)" % len(problems)))
    lines.append("  frame size: %s" % frames["how"])
    ordered = sorted(report["colours"].items(), key=lambda item: (-item[1], luminance(item[0])))
    table = " | ".join("%s %d px %.1f%% L%.3f"
                       % (describe_colour(palette, rgb), count, 100.0 * count / total, luminance(rgb))
                       for rgb, count in ordered)
    lines.append("  colours: %s" % table)
    lines.append("  dark tone: %s" % describe_colour(palette, report["dark"]))
    for ground_report in report["grounds"]:
        ground = ground_report["ground"]
        lines.append("  ground %s (%s), luminance %.3f, declared %.3f"
                     % (ground["name"], describe_colour(palette, ground["rgb"]), ground["luminance"], ground["declared"]))
        for item in ground_report["rules"]:
            if quiet and item["ok"]:
                continue
            lines.append("    %-4s %-18s %-20s %s"
                         % ("PASS" if item["ok"] else "FAIL", item["rule"], item["measured"], item["detail"]))
    lines.append("  blob test, SPRITE-CRAFT 8.5, dark tone %s" % describe_colour(palette, report["dark"]))
    for item in report["blob"]["rules"]:
        if quiet and item["ok"]:
            continue
        lines.append("    %-4s %-24s %-22s %s"
                     % ("PASS" if item["ok"] else "FAIL", item["rule"], item["measured"], item["detail"]))
    lines.append("  RESULT: %s" % ("PASS" if not problems else "FAIL %d problem(s)" % len(problems)))
    return lines


# -----------------------------------------------------------------------------------------------------------------
# Grounds.

def parse_ground(text: str, palette: dict) -> dict:
    """deck, night_road, $0F or #rrggbb, with the luminance computed from the palette."""
    key = text.strip().lower().replace("-", "_").replace(" ", "_")
    if key in GROUND_ALIASES:
        name = GROUND_ALIASES[key]
        code = GROUNDS[name]["code"]
        rgb = palette["by_code"][code]
        return {"name": name, "code": code, "rgb": rgb, "luminance": luminance(rgb),
                "index": palette["index_of"][code], "declared": GROUNDS[name]["declared"]}
    if text.strip().startswith("$"):
        code = "$" + text.strip().lstrip("$").upper()
        if code not in palette["by_code"]:
            raise SystemExit("%s is not an entry in the 2C02 palette" % code)
        rgb = palette["by_code"][code]
        return {"name": code, "code": code, "rgb": rgb, "luminance": luminance(rgb),
                "index": palette["index_of"][code], "declared": luminance(rgb)}
    rgb = hex_to_rgb(text)
    codes = codes_for(palette, rgb)
    index = min(palette["index_of"][code] for code in codes) if codes else None
    return {"name": rgb_hex(rgb), "code": codes[0] if codes else None, "rgb": rgb,
            "luminance": luminance(rgb), "index": index, "declared": luminance(rgb)}


# -----------------------------------------------------------------------------------------------------------------
# Selftest: the arithmetic against the queue, and a generated image per outcome.

def selftest(palette: dict) -> int:
    results = []

    for code, declared in sorted(QUEUE_LUMINANCE.items(), key=lambda item: item[1]):
        measured = palette["luminance"][code]
        results.append(("queue luminance %s" % code, abs(measured - declared) <= 0.001,
                        "%.3f, the queue declares %.3f" % (measured, declared)))
    for code, ground_name, published in PUBLISHED_RATIOS:
        ground = parse_ground(ground_name, palette)
        measured = contrast(palette["luminance"][code], ground["luminance"])
        results.append(("published ratio %s on %s" % (code, ground_name), abs(measured - published) <= 0.005,
                        "%.2f, SPRITE-CRAFT 12.1 prints %.2f" % (measured, published)))

    night_road = parse_ground("night_road", palette)
    deck = parse_ground("deck", palette)

    def painted(pixels) -> Image.Image:
        image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        load = image.load()
        for (x, y), rgb in pixels.items():
            load[x, y] = (rgb[0], rgb[1], rgb[2], 255)
        return image

    outline = palette["by_code"]["$10"]          # 6.41 : 1 on the night road, the SPRITE-CRAFT answer
    fill = palette["by_code"]["$36"]             # 8.32 : 1 on the night road
    highlight = palette["by_code"]["$30"]        # 11.86 : 1 on the night road

    def figure(body_rgb, line_rgb=None) -> dict:
        line = outline if line_rgb is None else line_rgb
        pixels = {}
        for x in range(5, 11):
            pixels[(x, 1)] = line
        for y in range(2, 6):
            for x in range(5, 11):
                pixels[(x, y)] = body_rgb
            pixels[(5, y)] = line
            pixels[(10, y)] = line
        for x in range(5, 11):
            pixels[(x, 6)] = line
        pixels[(6, 2)] = highlight
        pixels[(7, 2)] = highlight
        for x in range(3, 13):
            pixels[(x, 7)] = line
        for y in range(8, 14):
            for x in range(3, 13):
                pixels[(x, y)] = body_rgb
            pixels[(3, y)] = line
            pixels[(12, y)] = line
        for x in range(3, 13):
            pixels[(x, 14)] = line
        for x in range(6, 9):
            pixels[(x, 9)] = line          # collar, 1 px of fill either side
        for x in range(6, 9):
            pixels[(x, 11)] = line         # belt
        for x in range(8, 11):
            pixels[(x, 13)] = line         # trouser break
        return pixels

    scratch = tempfile.mkdtemp(prefix="contrast_check_selftest_")

    def sheet(name: str, body_rgb, line_rgb=None):
        path = os.path.join(scratch, name)
        painted(figure(body_rgb, line_rgb)).save(path)
        return load_sheet(path), path

    here = {"frame_w": 16, "frame_h": 16, "how": "the selftest's generated 16 x 16 sheet",
            "queue_id": None, "queue_frames": None}

    clean_image, clean_path = sheet("clean_night_road.png", fill)
    clean = analyse(clean_image, dict(here), palette, [night_road])
    clean_rules = all_rules(clean)
    clean_failed = [item for item in clean_rules if not item["ok"]]
    results.append(("a correct figure passes on the night road", not clean_failed,
                    "%d rules, %d failed%s" % (len(clean_rules), len(clean_failed),
                                               (": " + "; ".join(item["rule"] for item in clean_failed)) if clean_failed else "")))

    # One fill equal to the ground: the deck grey $00 in a figure that keeps its black outline, so the
    # the invisible fill stays a fill and not the tone the outline rule measures (black outline $0F).
    invisible = palette["by_code"]["$00"]
    dirty_image, dirty_path = sheet("ground_equal_fill.png", invisible, palette["by_code"]["$0F"])
    dirty = analyse(dirty_image, dict(here), palette, [deck])
    dirty_rules = {item["rule"]: item for item in all_rules(dirty)}
    background = dirty_rules["background entry"]
    largest = dirty_rules["largest fill"]
    printed = [item for item in all_rules(dirty) if not item["ok"]]
    results.append(("a fill equal to the ground fails the background rule", not background["ok"],
                    "%s, measured %s" % (background["detail"], background["measured"])))
    results.append(("that same fill fails the largest fill rule", not largest["ok"],
                    "measured %s" % largest["measured"]))
    results.append(("the failing image prints FAIL", bool(printed),
                    "%d FAIL line(s), first: %s" % (len(printed), printed[0]["rule"] if printed else "none")))

    print("selftest: tools/art/contrast_check.py")
    failures = 0
    for label, ok, detail in results:
        if not ok:
            failures += 1
        print("  %-4s %-46s %s" % ("PASS" if ok else "FAIL", label, detail))
    print("  --- generated image with one fill equal to the deck ground ---")
    for line in describe(dirty, dirty_path, palette, quiet=True):
        print("  " + line)
    shutil.rmtree(scratch, ignore_errors=True)
    print("  RESULT: %s" % ("PASS" if not failures else "FAIL %d selftest check(s)" % failures))
    return 0 if not failures else 1


# -----------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a sprite sheet against the SPRITE-CRAFT 12.1 contrast floor and the 8.5 blob test.")
    parser.add_argument("png", nargs="?", help="the sprite sheet to check")
    parser.add_argument("--ground", action="append", default=None,
                        help="deck, night_road, $0F or #rrggbb. Repeatable. Default: deck and night_road")
    parser.add_argument("--frame-w", type=int, default=None, help="frame width in px; default from the queue, else the image")
    parser.add_argument("--frame-h", type=int, default=None, help="frame height in px; default from the queue, else the image")
    parser.add_argument("--json", dest="json_path", default=None, help="write the report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    parser.add_argument("--selftest", action="store_true", help="prove the arithmetic and prove the tool can fail")
    args = parser.parse_args(argv)

    root = repo_root()
    palette = load_palette(root)
    if args.selftest:
        return selftest(palette)
    if not args.png:
        parser.error("a png is required unless --selftest is given")

    ground_texts = args.ground or ["deck", "night_road"]
    grounds = [parse_ground(text, palette) for text in ground_texts]
    if bool(args.frame_w) != bool(args.frame_h):
        parser.error("--frame-w and --frame-h go together")
    image = load_sheet(args.png)
    geometry_info = geometry(root, args.png, image, args.frame_w, args.frame_h)
    report = analyse(image, geometry_info, palette, grounds)
    problems = [item for item in all_rules(report) if not item["ok"]]

    path = os.path.abspath(args.png)
    for line in describe(report, path, palette, args.quiet):
        print(line)

    if args.json_path:
        stored = {
            "png": path,
            "size": report["size"],
            "frame": {"w": geometry_info["frame_w"], "h": geometry_info["frame_h"],
                      "frames": len(report["frames"]), "how": geometry_info["how"],
                      "queue_id": geometry_info["queue_id"]},
            "palette": palette["path"],
            "dark_tone": describe_colour(palette, report["dark"]),
            "colours": [{"hex": rgb_hex(rgb), "codes": codes_for(palette, rgb), "px": count,
                         "share_pc": round(100.0 * count / sum(report["colours"].values()), 2),
                         "luminance": round(luminance(rgb), 4)}
                        for rgb, count in sorted(report["colours"].items(), key=lambda item: -item[1])],
            "grounds": [{"name": item["ground"]["name"],
                         "rgb": rgb_hex(item["ground"]["rgb"]),
                         "luminance": round(item["ground"]["luminance"], 4),
                         "declared": item["ground"]["declared"],
                         "rules": item["rules"]} for item in report["grounds"]],
            "blob": {"rules": report["blob"]["rules"],
                     "frames": [{"frame": frame["frame"],
                                 "drawn": frame.get("drawn"),
                                 "lightest": describe_colour(palette, frame["lightest"]) if not frame["empty"] else None,
                                 "light_share_pc": round(frame.get("light_share", 0.0), 2),
                                 "rows_without_dark": frame.get("rows_without_dark", []),
                                 "dark_runs": frame.get("dark_runs"),
                                 "interior_dark": frame.get("interior_dark"),
                                 "body_block": frame.get("body_block")} for frame in report["blob"]["frames"]]},
            "ok": not problems,
            "problem_count": len(problems),
        }
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(stored, handle, indent=2)
            handle.write("\n")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
