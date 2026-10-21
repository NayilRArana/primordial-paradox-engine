#!/usr/bin/env python3
"""pixel_dump.py: print a region of a PNG as pixel art, one character per pixel.

Why: the region report says which colours are on the screen but not their shape. A pixel dump shows the
shape directly, so a rectangle, a line of letters and a tile grid are told apart without guessing.

Usage:
    python tools/pixel_dump.py output\\_inspect_frame.png 0 0 128 60
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
    roles = {}
    for name, index in data.get("roles", {}).items():
        roles.setdefault(index, name)
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
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    path = sys.argv[1]
    x0, y0, w, h = (int(v) for v in sys.argv[2:6])
    colours, roles = load_palette()
    img = Image.open(path).convert("RGB")
    px = img.load()
    print("+ legend: one character per pixel, grouped by palette entry")
    for index in sorted(roles):
        r, g, b = colours[index]
        print("   %s = #%02x%02x%02x %s" % (chr(65 + index % 26), r, g, b, roles[index]))
    print("   other entries are printed as their index in base 26, lower case")
    for y in range(y0, min(y0 + h, img.size[1])):
        row = ""
        for x in range(x0, min(x0 + w, img.size[0])):
            index, distance = nearest(colours, px[x, y])
            if index in roles:
                row += chr(65 + index % 26)
            else:
                row += chr(97 + index % 26)
        print("%3d|%s" % (y, row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
