#!/usr/bin/env python3
"""frame_regions.py: describe a captured frame as colour regions instead of characters.

A 256x240 frame read as text is hard to judge. This prints, for every colour used, the bounding box of the
pixels of that colour and how many pixels it covers, so a flat area, a border and a line of text are told
apart by shape rather than by guessing from a thumbnail.

Usage:
    python tools/frame_regions.py output\\_inspect_frame.png
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_palette():
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    colours = []
    for value in data["colours"]:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
    roles = {name: index for name, index in data.get("roles", {}).items()}
    return colours, roles


def nearest(colours, pixel):
    best = 0
    best_d = 1 << 30
    for index, colour in enumerate(colours):
        dr = pixel[0] - colour[0]
        dg = pixel[1] - colour[1]
        db = pixel[2] - colour[2]
        d = dr * dr + dg * dg + db * db
        if d < best_d:
            best_d = d
            best = index
    return best, best_d


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    colours, roles = load_palette()
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()

    boxes = {}
    for y in range(h):
        for x in range(w):
            index, distance = nearest(colours, px[x, y])
            if distance > 9000:
                index = -1
            entry = boxes.get(index)
            if entry is None:
                boxes[index] = [x, y, x, y, 0]
            else:
                entry[0] = min(entry[0], x)
                entry[1] = min(entry[1], y)
                entry[2] = max(entry[2], x)
                entry[3] = max(entry[3], y)
                entry[4] += 1

    print("frame %dx%d" % (w, h))
    for index in sorted(boxes, key=lambda i: -boxes[i][4]):
        x0, y0, x1, y1, count = boxes[index]
        if index < 0:
            name = "off-palette"
        else:
            r, g, b = colours[index]
            name = "#%02x%02x%02x %s" % (r, g, b, roles.get(index, "role?"))
        print("  %-24s box x %3d..%3d  y %3d..%3d  %6d px" % (name, x0, x1, y0, y1, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
