"""Measure the composed 256x240 title frame against the screen-wide NES background rule.

Not part of the suite: a probe the art lane runs to see what the whole screen does, not only the
layers one at a time. A real cartridge has ONE universal backdrop and 16x16 attribute areas of three
colours, so an honest composite check is: how many colours does the worst 16x16 screen area carry,
and is one colour common enough to be the universal backdrop?

Usage:
    python tools/art/measure_compose_areas.py [layer height]
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPRITES = os.path.join(ROOT, "game", "sprites_src", "title")
AREA = 16


def main() -> int:
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        values = json.load(handle)["colours"]
    index_of = {}
    for index, value in enumerate(values):
        value = value.lstrip("#")
        index_of[(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))] = index

    with open(os.path.join(ROOT, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)

    frame = Image.new("RGBA", (256, 240), (0, 0, 0, 255))
    for row in table["layers"]:
        with open(os.path.join(SPRITES, row["name"] + ".json"), "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        with Image.open(os.path.join(SPRITES, row["name"] + ".png")) as handle:
            strip = handle.convert("RGBA")
        one = strip.crop((0, 0, meta["frame_w"], meta["frame_h"]))
        frame.alpha_composite(one, (0, row["y"]))

    pixels = frame.load()
    counts = Counter()
    worst = []
    for cy in range(240 // AREA):
        for cx in range(256 // AREA):
            seen = Counter()
            for y in range(cy * AREA, cy * AREA + AREA):
                for x in range(cx * AREA, cx * AREA + AREA):
                    seen[index_of.get(pixels[x, y][:3], -1)] += 1
            counts[len(seen)] += 1
            worst.append((len(seen), cx, cy, sorted(seen)))
    worst.sort(reverse=True)
    print("composed frame: colours per 16x16 screen area")
    for size in sorted(counts):
        print("  %d colours: %d areas" % (size, counts[size]))
    print("worst areas:")
    for size, cx, cy, colours in worst[:8]:
        print("  %d,%d  %d colours  %s" % (cx, cy, size, colours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
