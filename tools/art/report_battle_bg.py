#!/usr/bin/env python3
"""report_battle_bg.py: numbers about the four battle strips, for a reviewer who can see them.

The card says the worker cannot see and the manager reviews visuals, so this tool says, in numbers, what
the strips contain: colour coverage, how busy each 16 pixel band is, and whether any attribute area is a
flat single colour (which would mean a hole in the design rather than a decision).

Usage
    python tools\\art\\report_battle_bg.py
    python tools\\art\\report_battle_bg.py --json output\\bg_battle_report.json
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter

from PIL import Image

CELL = 16
TILE = 8
NAMES = ["corridor", "wardroom", "deck_night", "quay_dusk"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report numbers about the battle background strips.")
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    report = {}
    for name in NAMES:
        path = os.path.join(root, "game", "sprites_src", "bg", "bg_battle_%s.png" % name)
        image = Image.open(path).convert("RGB")
        width, height = image.size
        counts = Counter(image.getpixel((x, y)) for y in range(height) for x in range(width))
        bands = []
        for band in range(height // CELL):
            rows = Counter()
            for y in range(band * CELL, (band + 1) * CELL):
                for x in range(width):
                    rows[image.getpixel((x, y))] += 1
            top_colour, top_count = rows.most_common(1)[0]
            bands.append(
                {
                    "band": band,
                    "y": band * CELL,
                    "median_colour": "#%02x%02x%02x" % top_colour,
                    "median_share": round(top_count / (CELL * width), 3),
                    "colours_in_band": len(rows),
                }
            )
        flat = 0
        two = 0
        three = 0
        for ay in range(height // CELL):
            for ax in range(width // CELL):
                seen = set()
                for y in range(ay * CELL, (ay + 1) * CELL):
                    for x in range(ax * CELL, (ax + 1) * CELL):
                        seen.add(image.getpixel((x, y)))
                if len(seen) == 1:
                    flat += 1
                elif len(seen) == 2:
                    two += 1
                else:
                    three += 1
        report[name] = {
            "size": [width, height],
            "colours": len(counts),
            "coverage": [
                {"hex": "#%02x%02x%02x" % colour, "share": round(count / (width * height), 3)}
                for colour, count in counts.most_common()
            ],
            "bands": bands,
            "areas": {
                "flat_one_colour": flat,
                "two_colours": two,
                "three_or_more": three,
                "total": (width // CELL) * (height // CELL),
            },
        }
        worst = max(bands, key=lambda band: band["median_share"])
        top = report[name]["coverage"][0]
        print(
            "%-11s %dx%d  colours %2d  largest colour %s at %.1f%%  flattest band y=%d (%.0f%% one colour)  "
            "areas: %d flat, %d two, %d three"
            % (
                name,
                width,
                height,
                len(counts),
                top["hex"],
                top["share"] * 100,
                worst["y"],
                worst["median_share"] * 100,
                flat,
                two,
                three,
            )
        )

    if args.json_path:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_path)), exist_ok=True)
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print("wrote %s" % args.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
