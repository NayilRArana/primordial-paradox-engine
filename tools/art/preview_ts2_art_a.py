#!/usr/bin/env python3
"""The TS2-ART-A review sheet: the v2 logo and the v2 car at 3x, for the manager's eyes.

Why this file exists: the worker lane cannot see images, so every visual card hands the manager one 3x preview
PNG and a set of numbers. The 3x is exact (each source pixel becomes a 3x3 block), so a reviewer sees the art as
the game draws it on a 256x240 screen without any resampling blur.

The sheet, top to bottom, on the NES backdrop colour:
    row 1  spr_pp_title_logo frame 0, the normal logo
    row 2  spr_pp_title_logo frame 1, the gold shimmer
    row 3  spr_title_car frames 0, 1, 2 side by side, the wheels rolling

Clean room: the sheet holds only the two sprites our own scripts drew, composited with plain geometry. Nothing
is imported from any existing game.

Usage:
    python tools\\art\\preview_ts2_art_a.py

Output:
    output\ts2_art_a_preview.png    672x504, black backdrop, every pixel a 3x3 block
    output\ts2_art_a_preview.json   the measured checks: sizes, colours, frame counts

Exit codes:
    0  the sheet was written and every measured check passed
    1  a sprite is missing, or a measured check failed
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCALE = 3
BACKDROP = (0, 0, 0, 255)   # $0F, the NES backdrop
GAP = 4                     # sheet pixels between two rows, before scaling

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPRITE_DIR = os.path.join(ROOT, "game", "sprites_src", "title")
OUT_DIR = os.path.join(ROOT, "output")

LOGO = ("spr_pp_title_logo", 224, 64, 2)
CAR = ("spr_title_car", 64, 32, 3)


def load(name: str, frame_w: int, frame_h: int, frames: int) -> Image.Image:
    """The sheet as one image, with the contract's shape checked before anything is drawn."""
    path = os.path.join(SPRITE_DIR, name + ".png")
    if not os.path.isfile(path):
        raise SystemExit("preview: %s is missing" % path)
    image = Image.open(path).convert("RGBA")
    want = (frame_w * frames, frame_h)
    if image.size != want:
        raise SystemExit("preview: %s is %dx%d, the contract says %dx%d"
                         % (name, image.width, image.height, want[0], want[1]))
    return image


def frame_at(image: Image.Image, frame_w: int, frame_h: int, index: int) -> Image.Image:
    return image.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h))


def main() -> int:
    logo = load(*LOGO)
    car = load(*CAR)

    logo_w, logo_h, logo_frames = LOGO[1], LOGO[2], LOGO[3]
    car_w, car_h, car_frames = CAR[1], CAR[2], CAR[3]

    row1_h = logo_h
    row2_h = logo_h
    row3_h = car_h
    width = max(logo_w, car_w * car_frames)
    height = row1_h + GAP + row2_h + GAP + row3_h

    sheet = Image.new("RGBA", (width, height), BACKDROP)
    sheet.alpha_composite(frame_at(logo, logo_w, logo_h, 0), (0, 0))
    sheet.alpha_composite(frame_at(logo, logo_w, logo_h, 1), (0, row1_h + GAP))
    car_top = row1_h + GAP + row2_h + GAP
    for index in range(car_frames):
        sheet.alpha_composite(frame_at(car, car_w, car_h, index),
                              (index * car_w, car_top))

    big = sheet.resize((width * SCALE, height * SCALE), Image.NEAREST)

    # The 3x is proved, not assumed: every 3x3 block must be one colour.
    broken = 0
    for by in range(height):
        for bx in range(width):
            block = {big.getpixel((bx * SCALE + dx, by * SCALE + dy))
                     for dy in range(SCALE) for dx in range(SCALE)}
            if len(block) != 1:
                broken += 1
    if broken:
        print("preview: %d blocks are not flat, the scale is not exact NEAREST" % broken)
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    png_path = os.path.join(OUT_DIR, "ts2_art_a_preview.png")
    big.save(png_path, "PNG")

    def colours_of(image: Image.Image) -> int:
        return len({p[:3] for p in image.getdata() if p[3] != 0})

    report = {
        "scale": SCALE,
        "sheet": [big.width, big.height],
        "backdrop": "#000000",
        "blocks_flat": True,
        "logo": {"size": [logo_w * SCALE, logo_h * SCALE], "frames": logo_frames,
                 "colours": colours_of(logo)},
        "car": {"size": [car_w * SCALE, car_h * SCALE], "frames": car_frames,
                "colours": colours_of(car)},
    }
    json_path = os.path.join(OUT_DIR, "ts2_art_a_preview.json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("  %-34s %dx%d  logo %d frames %d colours  car %d frames %d colours  3x exact"
          % (png_path, big.width, big.height, logo_frames, report["logo"]["colours"],
             car_frames, report["car"]["colours"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
