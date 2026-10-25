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

Where this tool sits in the art order
-------------------------------------
The fade strips are derived art: they are a picture of a base strip that something else draws. So they are
written LAST, after every pass that can rewrite a base, which today is a generator (tools/art/make_title_*.py,
tools/art/title_car_v2.py, ...) and then tools/art/scene_palette.py `apply` and its band pass. Rebuilding them
earlier is what card t_cd6a0d24 measured: 13 committed fades were the fades of bases the game no longer draws.
Two things hold the order down, and neither one is a convention:

  * tools/art/scene_palette.py apply_title ends by calling write_fades() here, the same way it already ends by
    rebuilding the flash strips, so the art pass that runs last also leaves the fades agreeing with it;
  * tests/test_intro.py pins every committed fade to the fade of the base strip beside it, so a lane that
    repaints a base and skips the fades gets a red test instead of a stale picture.

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
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import nes_tile  # noqa: E402  (the one place the alpha rule is written; the art lane shares it)

solid_alpha = nes_tile.solid_alpha

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
# A star frame is one 8x8 pattern tile, because the star is drawn as a sprite and a sheet has to cut into whole
# tiles. The drawing inside it is still the 1, 3x3 and 5x5 shapes below; only the frame around them is a tile.
STAR_FRAME = 8
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
    """One fade step applied to every opaque pixel of an image, with the alpha made solid.

    The colour still moves down a brightness row; the alpha is made into the two states the PPU has, because a
    fade strip with alpha 110 in it is refused by tools\\nes_check.py (and would be refused by the chip).
    """
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
    return solid_alpha(out)


def enforce_star_palette(strip: Image.Image) -> Image.Image:
    """Repaint the star into the title's sprite palettes before it is written.

    The star is drawn from two 2C02 entries, and which two the title's sprite palettes actually carry is decided
    by data/palettes/scene_title.json. Writing the raw entries and letting tools/art/scene_palette.py repaint them
    afterwards means the file on disk is not what this generator draws, so a re-run of the generator rewrites it
    differently and tests/test_intro.py's "the generator rewrites the committed sprite" pin fails against art the
    palette pass produced. Repainting here makes the two agree: the generator's output is already the shipped one.
    """
    art_dir = os.path.join(ROOT, "tools", "art")
    if art_dir not in sys.path:
        sys.path.insert(0, art_dir)
    import scene_palette

    scene = scene_palette.load_scene(ROOT, "title")
    frame = STAR_FRAME
    frames = []
    for index in range(STAR_FRAMES):
        one = strip.crop((index * frame, 0, index * frame + frame, frame))
        scene_palette.enforce_sprites(one, scene, frame, frame, sprite_height=frame)
        frames.append(one)
    out = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    for index, one in enumerate(frames):
        out.paste(one, (index * frame, 0))
    return out


def write_star_sprite(palette) -> int:
    """Write spr_title_star.png and its sidecar. Returns 0 on success."""
    bright = palette[STAR_BRIGHT]
    dim = palette[STAR_DIM]
    size = STAR_FRAME * STAR_FRAMES
    strip = Image.new("RGBA", (size, STAR_FRAME), (0, 0, 0, 0))
    # The 5x5 cross is the widest shape, so it is centred in the 8x8 frame: offset 3 holds columns 1 to 5.
    offset = STAR_FRAME // 2 - 1
    # Frame 0: the star at rest, one pixel.
    strip.putpixel((offset, offset), bright + (255,))
    # Frame 1: a 3x3 plus.
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        strip.putpixel((STAR_FRAME + offset + dx, offset + dy), bright + (255,))
    # Frame 2: the wider cross, the dim colour with a bright centre, so the twinkle grows.
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
        strip.putpixel((STAR_FRAME * 2 + offset + dx, offset + dy), dim + (255,))
    strip.putpixel((STAR_FRAME * 2 + offset, offset), bright + (255,))
    strip = enforce_star_palette(strip)
    png = os.path.join(TITLE_SRC, STAR_NAME + ".png")
    strip.save(png)
    sidecar = {"name": STAR_NAME, "frame_w": STAR_FRAME, "frame_h": STAR_FRAME,
               "frames": STAR_FRAMES, "fps": STAR_FPS}
    path = os.path.join(TITLE_SRC, STAR_NAME + ".json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(sidecar, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print("stars: %s (%dx%d, %d frames)" % (png, size, STAR_FRAME, STAR_FRAMES))
    return 0


def fade_rule(root: str):
    """What the scene's sprite pass owns, so a fade twin here is written the way that pass would leave it.

    tools/art/scene_palette.py apply_title repaints every sheet in its TITLE_SPRITES list, except the ones the
    band plan paints afterwards. The cloud's and the exhaust's fade twins are in that list, so that pass used to
    repaint a file this tool had just written, and the two disagreed: the shipped cloud fade spent $00 and $28
    while this tool drew $0D and $10, and a rerun of the generator quietly undid the enforcement (card
    t_cd6a0d24, measured on the tree as committed). The star already had this fix; the fades get the same one.

    Returns (owned names, scene or None). The scene is loaded once here instead of once per strip.
    """
    art_dir = os.path.join(root, "tools", "art")
    if art_dir not in sys.path:
        sys.path.insert(0, art_dir)
    import scene_palette

    scene = scene_palette.load_scene(root, "title")
    band_painted = {name for name in (scene.payload.get("band_sprites") or {})
                    if not name.startswith("_")}
    owned = frozenset(name for name in scene_palette.TITLE_SPRITES if name not in band_painted)
    return owned, scene


def fade_for(twin: str, base: Image.Image, meta: dict, steps: int, palette, rule) -> Image.Image:
    """The fade strip that ships: one brightness row darker, then inside the scene palette when that pass owns it."""
    faded = fade_image(base, steps, palette)
    owned, scene = rule
    if twin not in owned or scene is None:
        return faded
    import scene_palette

    frame_w = meta.get("frame_w", faded.width)
    frame_h = meta.get("frame_h", faded.height)
    scene_palette.enforce_sprites(faded, scene, frame_w, frame_h, sprite_height=min(16, frame_h))
    return faded


def fade_sidecar(sidecar: dict, twin: str) -> dict:
    """The fade's own sidecar: the base's frame geometry, its own name, and the note that says where it came from."""
    child = dict(sidecar)
    child["name"] = twin
    child["note"] = "one NES brightness row darker per step, written by tools/pp_intro_art.py"
    return child


def write_fades(root: str | None = None, palette=None) -> int:
    """Write every fade strip and its sidecar from the base strips as they are on disk right now.

    Callable from tools/art/scene_palette.py, which is the pass that runs last: reading the base back off disk
    is what makes the order of the art passes stop mattering (see the flash strips in that file, same rule).
    Returns the number of strips written.
    """
    root = root or ROOT
    palette = palette or load_palette()
    src = os.path.join(root, "game", "sprites_src", "title")
    rule = fade_rule(root)
    written = 0
    for name in FADED_ANIMATIONS:
        png = os.path.join(src, name + ".png")
        sidecar_path = os.path.join(src, name + ".json")
        if not os.path.isfile(png) or not os.path.isfile(sidecar_path):
            print("skip: %s has no strip or sidecar yet" % name)
            continue
        with open(sidecar_path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
        with Image.open(png) as source:
            base = source.convert("RGBA")
        for steps in range(1, FADE_STEPS + 1):
            twin = "%s_fade%d" % (name, steps)
            faded = fade_for(twin, base, sidecar, steps, palette, rule)
            faded.save(os.path.join(src, twin + ".png"))
            with open(os.path.join(src, twin + ".json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(fade_sidecar(sidecar, twin), indent=2, sort_keys=True,
                                        ensure_ascii=False) + "\n")
            written += 1
    return written


def check_fades(root: str | None = None, palette=None) -> list[str]:
    """Every fade strip that is missing or not the fade of the base beside it, as lines to print.

    The comparison is on pixels and on the sidecar's own fields, not on PNG bytes: the pixels are the picture and
    the encoder is not (tests/conftest.py, host_png_bytes). Until card t_cd6a0d24 this function did not exist and
    --check only asked whether the file was there, so five animations could sit behind their bases for days and
    the tool that was supposed to notice said nothing.
    """
    root = root or ROOT
    palette = palette or load_palette()
    src = os.path.join(root, "game", "sprites_src", "title")
    rule = fade_rule(root)
    stale = []
    for name in FADED_ANIMATIONS:
        png = os.path.join(src, name + ".png")
        sidecar_path = os.path.join(src, name + ".json")
        if not os.path.isfile(png) or not os.path.isfile(sidecar_path):
            continue
        with open(sidecar_path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
        with Image.open(png) as source:
            base = source.convert("RGBA")
        for steps in range(1, FADE_STEPS + 1):
            twin = "%s_fade%d" % (name, steps)
            want = fade_for(twin, base, sidecar, steps, palette, rule)
            path = os.path.join(src, twin + ".png")
            if not os.path.isfile(path):
                stale.append("STALE: %s is missing" % path)
                continue
            with Image.open(path) as handle:
                have = handle.convert("RGBA")
            if have.size != want.size:
                stale.append("STALE: %s is %dx%d, and the base beside it fades to %dx%d"
                             % (path, have.width, have.height, want.width, want.height))
                continue
            if have.tobytes() != want.tobytes():
                differing = sum(1 for a, b in zip(have.getdata(), want.getdata()) if a != b)
                stale.append("STALE: %s is not the fade of %s (%d pixel(s) differ)"
                             % (path, os.path.basename(png), differing))
            sidecar_out = os.path.join(src, twin + ".json")
            if not os.path.isfile(sidecar_out):
                stale.append("STALE: %s is missing" % sidecar_out)
                continue
            with open(sidecar_out, "r", encoding="utf-8") as handle:
                have_sidecar = json.load(handle)
            if have_sidecar != fade_sidecar(sidecar, twin):
                stale.append("STALE: %s does not carry the base's frame geometry" % sidecar_out)
    return stale


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write the NES fade strips and the star sprite.")
    parser.add_argument("--check", action="store_true",
                        help="report what is missing or out of date instead of writing it")
    parser.add_argument("--stars-only", action="store_true", help="write only the star sprite")
    args = parser.parse_args(argv)
    palette = load_palette()

    if args.check:
        stale = []
        star_png = os.path.join(TITLE_SRC, STAR_NAME + ".png")
        if not os.path.isfile(star_png):
            stale.append("STALE: %s is missing" % star_png)
        stale.extend(check_fades(ROOT, palette))
        for line in stale:
            print(line)
        return 1 if stale else 0

    write_star_sprite(palette)
    if args.stars_only:
        return 0

    written = write_fades(ROOT, palette)
    print("fades: %d strips written for %d animations" % (written, len(FADED_ANIMATIONS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
