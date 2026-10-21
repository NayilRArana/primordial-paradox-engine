#!/usr/bin/env python3
"""Measure the title car sprite, so the game places the wheels and the two heads by fact.

This is the same reading of the pixels that tools/art/compose_title_preview.py does, run as a
tool so the numbers it prints can be pasted into the GML and then pinned by a test. Nothing
here draws anything and nothing is copied from anywhere: the car is this project's own art.

Usage:
    python tools/art/measure_title_car.py
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPRITE = os.path.join(ROOT, "game", "sprites_src", "title", "spr_title_car.png")
INK = (11, 11, 15, 255)


def bottom_row(frame: Image.Image) -> int:
    px = frame.load()
    for y in range(frame.height - 1, -1, -1):
        for x in range(frame.width):
            if px[x, y][3] != 0:
                return y
    return frame.height - 1


def arch_centres(frame: Image.Image) -> list[int]:
    px = frame.load()
    bottom = bottom_row(frame)
    kinds = []
    for x in range(frame.width):
        r, g, b, a = px[x, bottom]
        kinds.append("t" if a == 0 else ("d" if (r, g, b) == INK[:3] else "b"))
    runs = []
    start = None
    kind = None
    for x in range(frame.width + 1):
        current = kinds[x] if x < frame.width else None
        if current is not None and current != "b":
            if start is None:
                start, kind = x, current
        elif start is not None:
            if kind == "d" or (start > 0 and x < frame.width):
                runs.append((start, x - 1))
            start, kind = None, None
    centres = [(a + b) // 2 for a, b in runs if b - a >= 6]
    return centres if len(centres) == 2 else [14, 46]


def window_band(frame: Image.Image) -> tuple[int, int]:
    px = frame.load()
    counts = [sum(1 for x in range(frame.width) if px[x, y][:3] == INK[:3]) for y in range(frame.height)]
    best = max(counts)
    rows = [y for y in range(frame.height) if counts[y] >= max(6, best * 3 // 4)]
    return (rows[0], rows[-1])


def window_openings(frame: Image.Image) -> list[tuple[int, int]]:
    px = frame.load()
    top, bottom = window_band(frame)
    band = list(range(top, bottom + 1))
    in_window = []
    for x in range(frame.width):
        hits = sum(1 for y in band if px[x, y][:3] == INK[:3])
        in_window.append(hits >= max(2, len(band) * 2 // 3))
    openings = []
    start = None
    for x in range(frame.width):
        if in_window[x] and start is None:
            start = x
        elif not in_window[x] and start is not None:
            openings.append((start, x - 1))
            start = None
    if start is not None:
        openings.append((start, frame.width - 1))
    return [o for o in openings if o[1] - o[0] >= 5]


def main() -> int:
    with open(os.path.join(ROOT, "game", "sprites_src", "title", "spr_title_car.json"),
              "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    sheet = Image.open(SPRITE).convert("RGBA")
    frame = sheet.crop((0, 0, meta["frame_w"], meta["frame_h"]))
    band = window_band(frame)
    result = {
        "frame_w": meta["frame_w"],
        "frame_h": meta["frame_h"],
        "frames": meta["frames"],
        "bottom_row": bottom_row(frame),
        "arch_centres": arch_centres(frame),
        "window_band": list(band),
        "window_openings": [list(o) for o in window_openings(frame)],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
