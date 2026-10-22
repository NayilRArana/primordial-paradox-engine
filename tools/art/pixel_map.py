#!/usr/bin/env python3
"""Print a region of a sprite sheet as text with the palette index of every pixel, so a tile rule
failure can be read. Debug helper for the title art lane.

Usage:
    python tools/art/pixel_map.py <png path> <x0> <y0> <x1> <y1>
"""

from __future__ import annotations

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nes_tile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    path = sys.argv[1]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
    colours, index_of = nes_tile.load_palette(ROOT)
    image = Image.open(path).convert("RGBA")
    names = {0: "ink", 3: "d3", 4: "d4", 5: "cap", 35: "bas", 41: "gld"}
    for y in range(y0, y1):
        line = ""
        for x in range(x0, x1):
            pixel = image.getpixel((x, y))
            if pixel[3] == 0:
                line += " .."
                continue
            index = index_of.get(pixel[:3], -1)
            line += " %s" % names.get(index, str(index))
        print("%3d %s" % (y, line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
