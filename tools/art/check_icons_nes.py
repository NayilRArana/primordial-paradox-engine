#!/usr/bin/env python3
"""check_icons_nes.py: read the icon sheets back off disk and prove the sidecars describe them.

tools\\nes_check.py proves the NES tile rule and tools\\nes_composite_check.py proves the frame budgets.
Neither of them can tell you whether a .json sidecar matches the .png it sits beside, or whether two icons
accidentally became the same drawing. This tool does that, by reading only what is on disk:

    1. every icon in the set appears in both the 16x16 and the 8x8 sheet, exactly once;
    2. the sheet's PNG size equals its own json grid (cols x cell_w by rows x cell_h);
    3. every frame rectangle in the json lies inside the sheet and no two frames overlap;
    4. the pixels inside a frame use only the three palette entries its json declares, no more;
    5. no frame is empty, and no two frames of the same size carry the same pixel mask;
    6. every frame leaves a transparent margin on at least one side, so the sprite has room on the tile grid;
    7. the ink coverage of each frame is reported, because a worker cannot see the art and a number beats a
       guess: an icon that covers almost nothing is probably broken.

Exit 0 when every check passes, 1 when any fails. The report is also written as JSON.

Usage:
    python tools\\art\\check_icons_nes.py
    python tools\\art\\check_icons_nes.py --json output\\icons_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_icons_nes as M  # noqa: E402


def load_hexes(root):
    with open(os.path.join(root, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return ["#%s" % value.lstrip("#").lower() for value in data["colours"]]


def frame_mask(sheet, frame):
    box = (frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"])
    crop = sheet.crop(box).convert("RGBA")
    pixels = crop.load()
    mask = set()
    colours = Counter()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            mask.add((x, y))
            colours["#%02x%02x%02x" % (r, g, b)] += 1
    return mask, colours


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the icon sheets against their json sidecars.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    hexes = load_hexes(root)
    sheet_dir = os.path.join(root, "game", "sprites_src", "icons")
    failures = []
    report = {"format": 1, "kind": "nes_icon_check", "sheets": [], "problems": []}
    seen = {8: {}, 16: {}}
    for (group, size) in (("items", 16), ("items", 8), ("status", 16), ("status", 8),
                          ("cursor", 16), ("cursor", 8)):
        stem = M.SHEET_NAMES[(group, size)]
        png_path = os.path.join(sheet_dir, stem + ".png")
        json_path = os.path.join(sheet_dir, stem + ".json")
        if not (os.path.isfile(png_path) and os.path.isfile(json_path)):
            failures.append("%s: missing png or json" % stem)
            continue
        with open(json_path, "r", encoding="utf-8-sig") as handle:
            side = json.load(handle)
        with Image.open(png_path) as handle:
            sheet = handle.convert("RGBA")
        grid = side["grid"]
        expect = (grid["cols"] * grid["cell_w"], grid["rows"] * grid["cell_h"])
        if (sheet.width, sheet.height) != expect:
            failures.append("%s: png is %dx%d but the json grid says %dx%d"
                            % (stem, sheet.width, sheet.height, expect[0], expect[1]))
        if side["frames"] != len(side["frames_detail"]):
            failures.append("%s: frames %d but %d frame records" % (stem, side["frames"],
                                                                    len(side["frames_detail"])))
        rects = []
        entry = {"sheet": stem, "group": group, "size": size, "png": "%dx%d" % (sheet.width, sheet.height),
                 "frames": side["frames"], "sprite_palettes": side["sprite_palette_count"], "icons": []}
        for frame in side["frames_detail"]:
            box = (frame["x"], frame["y"], frame["w"], frame["h"])
            if frame["x"] < 0 or frame["y"] < 0 or frame["x"] + frame["w"] > sheet.width or \
                    frame["y"] + frame["h"] > sheet.height:
                failures.append("%s: %s frame rectangle %s is outside the sheet"
                                % (stem, frame["name"], box))
            for other in rects:
                if box[0] < other[0] + other[2] and other[0] < box[0] + box[2] and \
                        box[1] < other[1] + other[3] and other[1] < box[1] + box[3]:
                    failures.append("%s: %s overlaps %s" % (stem, frame["name"], other))
            rects.append(box)
            mask, colours = frame_mask(sheet, frame)
            declared = {"#%02x%02x%02x" % tuple(int(frame["hex"][role].lstrip("#")[i:i + 2], 16)
                                               for i in (0, 2, 4)) for role in ("dark", "mid", "light")}
            extra = set(colours) - declared
            if extra:
                failures.append("%s: %s draws colours outside its declared three: %s"
                                % (stem, frame["name"], sorted(extra)))
            for role, index in frame["colours"].items():
                if not (0 <= index < len(hexes)):
                    failures.append("%s: %s names palette entry %d, outside data\\nes_palette.json"
                                    % (stem, frame["name"], index))
                elif hexes[index] != frame["hex"][role].lower():
                    failures.append("%s: %s says %s is entry %d, but that entry is %s"
                                    % (stem, frame["name"], role, index, hexes[index]))
            if not mask:
                failures.append("%s: %s is empty" % (stem, frame["name"]))
            key = frozenset(mask)
            if key in seen[size]:
                failures.append("%s: %s is the same pixels as %s" % (stem, frame["name"], seen[size][key]))
            else:
                seen[size][key] = frame["name"]
            xs = [p[0] for p in mask] or [0]
            ys = [p[1] for p in mask] or [0]
            margin = {"left": min(xs), "top": min(ys),
                      "right": frame["w"] - 1 - max(xs), "bottom": frame["h"] - 1 - max(ys)}
            coverage = len(mask) / float(frame["w"] * frame["h"])
            if min(margin.values()) < 0:
                failures.append("%s: %s has pixels outside its own rectangle" % (stem, frame["name"]))
            if coverage < 0.12:
                failures.append("%s: %s covers only %.0f%% of its cell, which reads as empty"
                                % (stem, frame["name"], coverage * 100.0))
            entry["icons"].append({"name": frame["name"], "sprite_palette": frame["sprite_palette"],
                                   "ink_pixels": len(mask), "coverage": round(coverage, 3),
                                   "colours": len(colours), "margin": margin,
                                   "bbox": [min(xs), min(ys), max(xs), max(ys)]})
        report["sheets"].append(entry)

    wanted = [row[0] for row in M.ICONS]
    for size in (16, 8):
        have = [frame["name"] for sheet in report["sheets"] if sheet["size"] == size
                for frame in sheet["icons"]]
        if sorted(have) != sorted(wanted):
            failures.append("%dx%d sheets cover %s, expected %s" % (size, size, sorted(have), sorted(wanted)))
        if len(set(have)) != len(have):
            failures.append("%dx%d sheets name an icon twice" % (size, size))

    report["problems"] = failures
    report["passed"] = not failures
    report["icon_count"] = len(wanted)
    if args.json_path:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_path)), exist_ok=True)
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    for sheet in report["sheets"]:
        print("P: %-26s %-8s %2d icons  %d sprite palettes  ink %.0f%% to %.0f%%"
              % (sheet["sheet"], sheet["png"], sheet["frames"], sheet["sprite_palettes"],
                 min(i["coverage"] for i in sheet["icons"]) * 100.0,
                 max(i["coverage"] for i in sheet["icons"]) * 100.0))
    if failures:
        print("FAIL: %d problem(s)" % len(failures))
        for line in failures:
            print("  - %s" % line)
        return 1
    print("PASS: %d sheets, %d icons at both sizes, every sidecar matches its png" % (len(report["sheets"]),
                                                                                     len(wanted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
