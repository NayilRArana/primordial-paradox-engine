#!/usr/bin/env python3
"""Print the palette indices found in each 8x8 tile of a sprite strip, so a tile rule failure can be
read rather than guessed. Debug helper for the title art lane.

Usage:
    python tools/art/tile_report.py <sprite name> [frame index]
"""

from __future__ import annotations

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nes_tile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    name = sys.argv[1]
    frame = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    colours, index_of = nes_tile.load_palette(ROOT)
    path = os.path.join(ROOT, "game", "sprites_src", "title", name + ".png")
    import json
    with open(path[:-4] + ".json", "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    sheet = Image.open(path).convert("RGBA")
    for (f, tx, ty), seen in sorted(nes_tile.tile_colours(sheet, meta["frame_w"], meta["frame_h"], index_of).items()):
        if f != frame or len(seen) <= 3:
            continue
        print("tile %d,%d frame %d: %s" % (tx, ty, f, sorted(seen)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
