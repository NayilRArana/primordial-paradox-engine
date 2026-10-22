#!/usr/bin/env python3
"""Cut the game surface out of the two captured title frames and write one 3x preview sheet.

Why this file exists: Hermes workers cannot see images, so every visual card delivers a preview PNG that a human or a
vision model reviews. tools/capture_title.py copies the whole window rectangle (title bar and borders included), and the
game inside it is already drawn at 3x of the 256x240 frame. The job here is therefore small and mechanical: find where
the game surface starts inside the capture, prove the crop is really the game at 3x, then lay the two frames side by
side so the reviewer sees the screen before and after one Enter.

The offset is not guessed. The game scales 256x240 by a whole 3, so every 3x3 block of the surface holds one colour; a
window border, a title bar, a wallpaper or a foreign window does not. The script tries every offset a 16 px border and
a 40 px title bar can produce and keeps the one whose 768x720 crop is almost entirely made of flat 3x3 blocks.

Usage:
    python tools/title_preview_3x.py
    python tools/title_preview_3x.py --frame1 output/title_run_1.png --frame2 output/title_run_2.png

Output:
    output/title_preview_3x.png   1536x720, frame 1 left and frame 2 right, at the native 3x the game draws
    output/title_preview_3x.json  the measured offsets and block scores

Exit codes:
    0  both frames were found, cropped and written
    1  a capture is missing, or no 3x-aligned crop was found (the capture is not the game at 3x)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
OUTPUT_DIR = os.path.join(ROOT, "output")

FRAME_W = 256
FRAME_H = 240
SCALE = 3
SURFACE_W = FRAME_W * SCALE
SURFACE_H = FRAME_H * SCALE
# A capture is a window rectangle: at most this much border on each side and this much title bar on top.
MAX_BORDER_X = 24
MAX_BORDER_Y = 64
# The share of 3x3 blocks that must be flat for a crop to count as the game surface. The pixel art is blocky by
# construction, so a real crop scores at or near 1.0; a title bar or a wallpaper scores far lower.
MIN_FLAT_SHARE = 0.99
PREVIEW_SHEET = os.path.join(OUTPUT_DIR, "title_preview_3x.png")
PREVIEW_JSON = os.path.join(OUTPUT_DIR, "title_preview_3x.json")


def flat_block_share(img: Image.Image, ox: int, oy: int) -> float:
    """Share of non overlapping 3x3 blocks in the crop at (ox, oy) that hold a single colour."""
    pixels = img.load()
    flat = 0
    total = 0
    for by in range(0, SURFACE_H, SCALE):
        for bx in range(0, SURFACE_W, SCALE):
            first = pixels[ox + bx, oy + by]
            same = True
            for dy in range(SCALE):
                for dx in range(SCALE):
                    if pixels[ox + bx + dx, oy + by + dy] != first:
                        same = False
                        break
                if not same:
                    break
            total += 1
            if same:
                flat += 1
    return flat / total if total else 0.0


def find_surface(img: Image.Image) -> tuple[int, int, float]:
    """The offset whose crop is the flattest at 3x, with its share. (-1, -1, share) when none passes."""
    best = (-1, -1, 0.0)
    for oy in range(0, min(MAX_BORDER_Y, img.height - SURFACE_H) + 1):
        for ox in range(0, min(MAX_BORDER_X, img.width - SURFACE_W) + 1):
            share = flat_block_share(img, ox, oy)
            if share > best[2]:
                best = (ox, oy, share)
    if best[2] < MIN_FLAT_SHARE:
        return -1, -1, best[2]
    return best


def load_frame(path: str) -> Image.Image:
    if not os.path.isfile(path):
        raise SystemExit("title_preview_3x: no capture at %s" % path)
    return Image.open(path).convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame1", default=os.path.join(OUTPUT_DIR, "title_run_1.png"))
    parser.add_argument("--frame2", default=os.path.join(OUTPUT_DIR, "title_run_2.png"))
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    crops = []
    report = {"scale": SCALE, "surface": [SURFACE_W, SURFACE_H], "frames": []}
    for index, path in enumerate((args.frame1, args.frame2), start=1):
        img = load_frame(path)
        ox, oy, share = find_surface(img)
        if ox < 0:
            print("title_preview_3x: frame %d (%s) is not the game at %dx: best flat block share %.3f, need %.2f"
                  % (index, os.path.basename(path), SCALE, share, MIN_FLAT_SHARE))
            return 1
        crop = img.crop((ox, oy, ox + SURFACE_W, oy + SURFACE_H))
        crops.append(crop)
        report["frames"].append({
            "file": os.path.basename(path),
            "capture": [img.width, img.height],
            "offset": [ox, oy],
            "flat_block_share": round(share, 4),
        })
        print("frame %d: %s %dx%d, game surface at (%d, %d), flat 3x3 blocks %.3f"
              % (index, os.path.basename(path), img.width, img.height, ox, oy, share))

    sheet = Image.new("RGB", (SURFACE_W * 2, SURFACE_H), (0, 0, 0))
    sheet.paste(crops[0], (0, 0))
    sheet.paste(crops[1], (SURFACE_W, 0))
    sheet.save(PREVIEW_SHEET)
    report["sheet"] = os.path.basename(PREVIEW_SHEET)
    report["sheet_size"] = [sheet.width, sheet.height]
    with open(PREVIEW_JSON, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("wrote %s %dx%d" % (PREVIEW_SHEET, sheet.width, sheet.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
