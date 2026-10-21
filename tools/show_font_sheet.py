#!/usr/bin/env python3
"""show_font_sheet.py: print the 8x8 font sheet as pixel art, so the glyphs can be read.

Why: the first screen needs legible letters, and the sheet is the project's own art. A print of the
sheet says what the letters look like before the game ever draws them.

Usage:
    python tools/show_font_sheet.py
    python tools/show_font_sheet.py 0 12      # a range of frames
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(ROOT, "game", "sprites_src", "title", "spr_pp_font8.png")
META = os.path.join(ROOT, "game", "sprites_src", "title", "spr_pp_font8.json")
GLYPHS = " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def main():
    with open(META, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    frame_w = meta["frame_w"]
    frame_h = meta["frame_h"]
    frames = meta["frames"]
    img = Image.open(SHEET).convert("RGBA")
    print("sheet %dx%d, %d frames of %dx%d" % (img.size[0], img.size[1], frames, frame_w, frame_h))
    print("glyph order used by pp_font.gml: %r" % GLYPHS)
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else frames
    px = img.load()
    for frame in range(start, min(end, frames)):
        label = GLYPHS[frame] if frame < len(GLYPHS) else "?"
        print("--- frame %d %r" % (frame, label))
        for row in range(frame_h):
            line = ""
            for col in range(frame_w):
                r, g, b, a = px[frame * frame_w + col, row]
                line += "#" if a > 127 else "."
            print("   " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
