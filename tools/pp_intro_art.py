#!/usr/bin/env python3
"""pp_intro_art.py: the two pieces of art the intro's NES fade and star field need.

Why this file exists: the intro after NEW GAME (card INTRO-1) pans up out of the road, fades the
world to black, then fades the sky to black except for the stars. A real NES fade is not a wash of
alpha over the picture: the PPU holds 64 colour entries as four brightness rows of sixteen hues
(ART-BIBLE.md section 1.3, data/nes_palette.json), and a fade step replaces every entry with the
entry sixteen below it, which is one row darker, while row zero drops to the black entry $0F. That
one substitution is what makes a NES fade read as steps rather than as a video dissolve.

The engine draws its world from PNG strips, so the substitution is done here, once, and written out
as `<name>_fade1.png` ... `<name>_fade4.png` beside each strip. The runtime then picks the strip by
name, exactly as it already picks the `_flash` twins for lightning (pp_title_flash_name).

This file also draws the star twinkle strip, spr_title_star: three frames of a single star, a
one pixel dot, a 3x3 plus, and a wider cross, which the intro staggers across the beats of the
theme.

Nothing here is traced, sampled or copied from any published game: the fade rule is the hardware
rule from ART-BIBLE.md, and the star is drawn from its own three shapes in this file.

Usage:
    python tools/pp_intro_art.py            write the stars and every fade strip
    python tools/pp_intro_art.py --check    exit 1 when any of them is missing or out of date

Exit codes:
    0  everything is on disk (and up to date for --check)
    1  --check found a missing or stale file, or the palette cannot be read
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE_SRC = os.path.join(ROOT, "game", "sprites_src", "title")
PALETTE_PATH = os.path.join(ROOT, "data", "nes_palette.json")

# The black the PPU really has, and the forbidden entry that also decodes to black ($0D).
BLACK_ENTRY = 0x0F
FORBIDDEN_ENTRY = 0x0D
ROW_SIZE = 16
FADE_STEPS = 4

# Every animation the intro draws over the world, and how many fade copies it gets. The name is the
# animation's own name in game\sprites_src\title; the strip beside it is <name>.png and its sidecar
# <name>.json says the frame size and count, so this list carries no numbers that could go stale.
FADED_ANIMATIONS = (
    "title_L1_sky",
    "title_L2_clouds",
    "title_L3_downs",
    "title_L4_fields",
    "title_L5_verge",
    "title_L6_road",
    "title_L7_fg",
    "spr_title_cone",
    "spr_title_cloud",
    "spr_title_exhaust",
    "spr_title_car",
    "spr_title_sign",
)

STAR_NAME = "spr_title_star"
STAR_FRAME = 5
STAR_FRAMES = 3
STAR_FPS = 6
# 3 x 3 and 5 x 5, one bright colour and one dim one, which is two of a sprite palette's three
# colours plus transparency (ART-BIBLE.md 1.2).
STAR_BRIGHT = 0x30
STAR_DIM = 0x10


def load_palette() -> list[tuple[int, int, int]]:
    """The 64 entries of the 2C02 palette as RGB, in entry order."""
    if not os.path.isfile(PALETTE_PATH):
        raise SystemExit("pp_intro_art: no palette at %s" % PALETTE_PATH)
    with open(PALETTE_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    colours = []
    for value in payload["colours"]:
        text = value.lstrip("#")
        colours.append((int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)))
    if len(colours) != 64:
        raise SystemExit("pp_intro_art: the palette has %d entries, not 64" % len(colours))
    return colours


def nearest_entry(rgb, palette) -> int:
    """The palette entry closest to an RGB triple, by squared distance."""
    best = BLACK_ENTRY
    best_d = None
    for index, entry in enumerate(palette):
        if index == FORBIDDEN_ENTRY:
            continue
        d = (rgb[0] - entry[0]) ** 2 + (rgb[1] - entry[1]) ** 2 + (rgb[2] - entry[2]) ** 2
        if best_d is None or d < best_d:
            best_d = d
            best = index
    return best


def darker_entry(entry: int, steps: int = 1) -> int:
    """The entry this many brightness rows below the given one, and black past the bottom row.

    The palette is four rows of sixteen hues (row 3 brightest, row 0 the dark version of each hue),
    so one row darker is sixteen entries lower. A step that would leave the bottom row lands on
    black, which is what the PPU shows when a game fades a colour past its darkest row. Without
    that, a blue at row 1 sat at its dark hue for every later step and the sky never went black.
    """
    row = entry // ROW_SIZE
    if row - steps < 0:
        return BLACK_ENTRY
    return entry - steps * ROW_SIZE


def fade_image(image: Image.Image, steps: int, palette) -> Image.Image:
    """One fade step applied to every opaque pixel of an image, alpha untouched."""
    source = image.convert("RGBA")
    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    cache: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    pixels = list(source.getdata())
    mapped = []
    for pixel in pixels:
        if pixel[3] == 0:
            mapped.append((0, 0, 0, 0))
            continue
        key = (pixel[0], pixel[1], pixel[2])
        hit = cache.get(key)
        if hit is None:
            entry = darker_entry(nearest_entry(key, palette), steps)
            hit = (palette[entry][0], palette[entry][1], palette[entry][2], pixel[3])
            cache[key] = hit
        mapped.append(hit)
    out.putdata(mapped)
    return out


def write_star_sprite(palette) -> int:
    """Write spr_title_star.png and its sidecar. Returns 0 on success."""
    bright = palette[STAR_BRIGHT]
    dim = palette[STAR_DIM]
    size = STAR_FRAME * STAR_FRAMES
    strip = Image.new("RGBA", (size, STAR_FRAME), (0, 0, 0, 0))
    offset = STAR_FRAME // 2
    # Frame 0: the star at rest, one pixel.
    strip.putpixel((offset, offset), bright + (255,))
    # Frame 1: a 3x3 plus.
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        strip.putpixel((STAR_FRAME + offset + dx, offset + dy), bright + (255,))
    # Frame 2: the wider cross, the dim colour with a bright centre, so the twinkle grows.
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
        strip.putpixel((STAR_FRAME * 2 + offset + dx, offset + dy), dim + (255,))
    strip.putpixel((STAR_FRAME * 2 + offset, offset), bright + (255,))
    png = os.path.join(TITLE_SRC, STAR_NAME + ".png")
    strip.save(png)
    sidecar = {"name": STAR_NAME, "frame_w": STAR_FRAME, "frame_h": STAR_FRAME,
               "frames": STAR_FRAMES, "fps": STAR_FPS}
    path = os.path.join(TITLE_SRC, STAR_NAME + ".json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(sidecar, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print("stars: %s (%dx%d, %d frames)" % (png, size, STAR_FRAME, STAR_FRAMES))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write the NES fade strips and the star sprite.")
    parser.add_argument("--check", action="store_true",
                        help="report what is missing or out of date instead of writing it")
    parser.add_argument("--stars-only", action="store_true", help="write only the star sprite")
    args = parser.parse_args(argv)
    palette = load_palette()

    if args.check:
        stale = 0
        star_png = os.path.join(TITLE_SRC, STAR_NAME + ".png")
        if not os.path.isfile(star_png):
            print("STALE: %s is missing" % star_png)
            stale += 1
        for name in FADED_ANIMATIONS:
            for step in range(1, FADE_STEPS + 1):
                path = os.path.join(TITLE_SRC, "%s_fade%d.png" % (name, step))
                if not os.path.isfile(path):
                    print("STALE: %s is missing" % path)
                    stale += 1
        return 1 if stale else 0

    write_star_sprite(palette)
    if args.stars_only:
        return 0

    written = 0
    for name in FADED_ANIMATIONS:
        png = os.path.join(TITLE_SRC, name + ".png")
        sidecar_path = os.path.join(TITLE_SRC, name + ".json")
        if not os.path.isfile(png) or not os.path.isfile(sidecar_path):
            print("skip: %s has no strip or sidecar yet" % name)
            continue
        with open(sidecar_path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
        with Image.open(png) as source:
            base = source.convert("RGBA")
        for step in range(1, FADE_STEPS + 1):
            faded = fade_image(base, step, palette)
            out_png = os.path.join(TITLE_SRC, "%s_fade%d.png" % (name, step))
            faded.save(out_png)
            child = dict(sidecar)
            child["name"] = "%s_fade%d" % (name, step)
            child["note"] = ("one NES brightness row darker per step, written by tools/pp_intro_art.py")
            out_json = os.path.join(TITLE_SRC, "%s_fade%d.json" % (name, step))
            with open(out_json, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(child, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            written += 1
    print("fades: %d strips written for %d animations" % (written, len(FADED_ANIMATIONS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
