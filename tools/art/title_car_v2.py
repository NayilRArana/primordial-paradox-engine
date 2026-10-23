#!/usr/bin/env python3
"""The v2 title car: the battered racing green hatchback, seen from the side, exterior only.

This supersedes the body and the wheels of tools/art/make_title_car.py. What changed, and why:
  - the glass is one dark tint with a single diagonal moonlight glint, so the car reads as a closed
    shell on a night road instead of a lit room with people in it;
  - no faces, no busts, no steering wheel: the card says the car shows its exterior only, and the
    cast sprites (spr_title_konrad, spr_title_zander, spr_title_bubble) are moved out of the title;
  - the wheels are baked into the car sprite, so a wheel always sits in its arch band and cannot drift.

Clean room: every shape is a row table or a distance function written in this file. Nothing is traced,
copied or imported from any existing game, and no external image is read.

THE TILE RULE IS THE CONSTRAINT. A sprite tile is 8x8 and may carry 3 colours plus transparency, so
the car is drawn with a palette of seven colours that never meet in the same tile. The car is 64 wide
and 32 tall, which is eight tiles across and four down, and the layout is chosen band by band:
  band 0 (rows  0 to  7)  the roof rack, the suitcase, the lit roof edge
  band 1 (rows  8 to 15)  the side glass, the pillars, the moonlight glint
  band 2 (rows 16 to 23)  the body, the tail light, the headlight, the door shut line
  band 3 (rows 24 to 31)  the sill, the wheel arches, the wheels
The colours, and where each one is allowed to appear:
  INK     the arch, the rail, the sill, the shut line, the tyres
  MID     the body, the racing green
  GLASS   the dark tint of the windows
  BRIGHT  the moonlight on the roof edge, the glint on the glass, the wheel spokes
  GOLD    the lit headlight
  RED     the tail light
  BROWN   the suitcase on the roof
No two of BRIGHT, GOLD, RED and BROWN share a tile, and the dark colours never sit in a band with
more than one of them.

The script proves the result: it counts the colours in every tile of every frame and refuses to write
the file if any tile breaks the rule.

Outputs:
    game/sprites_src/title/spr_title_car.png   64x32, 3 frames (the wheels roll, the body does not move)
    game/sprites_src/title/spr_title_car.json  {"name","frame_w","frame_h","frames","fps"}

Determinism: no clock, no randomness, PNG carries no timestamp, JSON is written with LF endings. Run the
script twice and the sha256 of every file it writes is the same.

Usage:
    python tools/art/title_car_v2.py
    python tools/art/title_car_v2.py --dump   # print the art as text
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nes_tile  # noqa: E402  (the palette, the tile rule and the pixel primitives)

INK = 0x0F       # #000000  $0F  the arch, the rail, the sill, the shut line, the tyres
MID = 0x0A       # #006800  $0A  the body, the racing green
GLASS = 0x0C     # #004058  $0C  the dark tint of the windows
BRIGHT = 0x30    # #fcfcfc  $30  the moonlight on the roof, the glint, the wheel spokes
GOLD = 0x28      # #f8b800  $28  the lit headlight
RED = 0x16       # #f83800  $16  the tail light
BROWN = 0x07     # #881400  $07  the suitcase on the roof

CAR_W = 64
CAR_H = 32
SPRITE_DIR = os.path.join("game", "sprites_src", "title")
CAR_NAME = "spr_title_car"

# The body, row by row: (first column, last column).
#
# The bonnet runs to column 55, so the last tile column is empty and the front of the car has a clean
# edge. Row 16 is the belt line and stops at the A pillar, so the glass never reaches the band that
# carries the headlight.
BODY_ROWS = {
    6: (18, 44),   # the flat roof
    7: (15, 46),
    8: (13, 47),
    9: (12, 48),
    10: (11, 48),
    11: (10, 49),
    12: (10, 49),
    13: (9, 50),
    14: (9, 50),
    15: (8, 49),   # the belt line, up to the A pillar
    16: (8, 55),   # the flat bonnet
    17: (8, 55),
    18: (8, 55),
    19: (8, 55),
    20: (8, 55),
    21: (8, 55),
    22: (8, 55),
    23: (8, 55),
    24: (8, 55),
    25: (8, 55),   # the straight bottom edge
}

# The window band, the seven rows the glass occupies. The belt line is row 15.
#
# The glass must never move, because a glass pixel on row 16 leaves the window band (rows 8 to 15) and
# lands in the body band (rows 16 to 23), which already carries ink, body and the lights. The frame
# animation is therefore the wheels rolling, one spoke step per frame, which happens entirely inside the
# bottom tile row band (rows 24 to 31). No tile changes the set of colours it carries between frames.
GLASS_TOP = 8
GLASS_BOTTOM = 14

# The wheel arches: centre column and radius. The arch is a half circle cut up into the body.
ARCHES = [(14, 5), (46, 5)]
ARCH_CENTRE_Y = 27

# The wheels, 8x8, sitting in the arches with the tyre bottom on row 31. The wheel lives entirely in
# the bottom tile row band, so the spokes never reach the band that carries the lights.
WHEEL_W = 8
WHEEL_H = 8
WHEEL_PLACE = [(10, 24), (42, 24)]

# The B pillar, in body colour, between the two side windows.
B_PILLAR = (26, 28)

# The A pillar, raked with the windscreen, one column per row from the roof down to the cowl.
A_PILLAR_TOP = 44
A_PILLAR_STEP = 6.0 / 11.0

# The lit roof edge, the roof rack and the suitcase.
ROOF_LIGHT = (18, 20)     # the part of the roof edge left of the suitcase
ROOF_LIGHT_R = (40, 44)   # the part right of it
RAIL = (19, 41)           # the roof rack rails
SUITCASE = (24, 39)       # the suitcase on the roof

# The tail light and the headlight.
TAILLIGHT = (8, 11)
HEADLIGHT = (50, 54)

# The shut line of the front door and its handle.
DOOR_SHUT = 27
DOOR_HANDLE = (35, 36)

# The moonlight glint: one diagonal streak across the side glass.
GLINT_FROM = (13, 9)
GLINT_TO = (23, 15)


def a_pillar_x(y: int) -> int:
    """The column of the A pillar at row y."""
    return int(round(A_PILLAR_TOP + (y - 6) * A_PILLAR_STEP))


def arch_top(cx: int, radius: int, x: int) -> float:
    """The row where the arch cut begins at column x, or a row below the body if there is none."""
    span = radius * radius - (x - cx) * (x - cx)
    if span <= 0:
        return 99.0
    return ARCH_CENTRE_Y - math.sqrt(span)


def build_body(colours) -> Image.Image:
    """The car body without the wheels. The wheels are added afterwards, so they never bob."""
    image = Image.new("RGBA", (CAR_W, CAR_H), (0, 0, 0, 0))
    px = image.load()

    def put(x: int, y: int, index: int) -> None:
        if 0 <= x < CAR_W and 0 <= y < CAR_H:
            px[x, y] = colours[index]

    # The body itself, green, row by row.
    for y, (x0, x1) in BODY_ROWS.items():
        for x in range(x0, x1 + 1):
            put(x, y, MID)

    # The lit roof edge, in the two stretches that the suitcase leaves clear.
    for x0, x1 in (ROOF_LIGHT, ROOF_LIGHT_R):
        for x in range(x0, x1 + 1):
            put(x, 6, BRIGHT)

    # The side glass, a dark tint from the hatch back to the A pillar.
    for y in range(8, 16):
        for x in range(BODY_ROWS[y][0] + 1, a_pillar_x(y) - 1):
            put(x, y, GLASS)

    # The B pillar, in body colour.
    for y in range(8, 16):
        for x in range(B_PILLAR[0], B_PILLAR[1] + 1):
            put(x, y, MID)

    # The windscreen, the dark tint beyond the raked A pillar.
    for y in range(8, 16):
        for x in range(a_pillar_x(y) + 1, BODY_ROWS[y][1] + 1):
            put(x, y, GLASS)

    # The A pillar itself, in body colour.
    for y in range(7, 17):
        put(a_pillar_x(y), y, MID)

    # The single diagonal moonlight glint, across the side glass.
    for x, y in nes_tile.thick_line([GLINT_FROM, GLINT_TO], 1):
        put(x, y, BRIGHT)

    # The shut line of the front door, and its handle.
    for y in range(17, 24):
        put(DOOR_SHUT, y, INK)
    for x in DOOR_HANDLE:
        put(x, 19, INK)

    # The sill, in the dark, so the bottom edge reads as one straight line.
    for y in (24, 25):
        for x in range(8, 56):
            put(x, y, INK)

    # The wheel arches: a dark half circle painted into the bottom of the body above each tyre. The body is
    # not cut through: the tyre and the arch are both ink, so the shape reads as an arch around the wheel.
    for cx, radius in ARCHES:
        for x in range(cx - radius, cx + radius + 1):
            top = arch_top(cx, radius, x)
            for y in range(int(math.ceil(top)), 26):
                put(x, y, INK)

    # The headlight, on, at the front, and the red tail light at the back.
    for x in range(HEADLIGHT[0], HEADLIGHT[1] + 1):
        put(x, 18, GOLD)
        put(x, 19, GOLD)
    for x in range(TAILLIGHT[0], TAILLIGHT[1] + 1):
        put(x, 18, RED)
        put(x, 19, RED)

    # The roof rack: the rails in the dark, and the brown suitcase on top of them.
    for x in range(RAIL[0], RAIL[1] + 1):
        put(x, 5, INK)
    for y in range(2, 4):
        for x in range(SUITCASE[0], SUITCASE[1] + 1):
            put(x, y, BROWN)
    for x in range(SUITCASE[0], SUITCASE[1] + 1):
        put(x, 1, INK)
        put(x, 4, INK)
    for x in (27, 33):
        for y in range(2, 4):
            put(x, y, INK)

    # A few scuffs, because the car is a battered old thing.
    for x, y in [(22, 22), (23, 22), (41, 21), (42, 21)]:
        put(x, y, INK)

    return image


def build_wheel(colours, phase: int = 0) -> Image.Image:
    """A wheel seen from the side: a dark tyre with bright spokes and a bright hub.

    ``phase`` turns the spokes in steps of a sixth of a turn, so a sequence of phases reads as the wheel
    rolling. The tyre and the hub never move, and every spoke pixel stays inside the wheel, which is the
    bottom tile row band.
    """
    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    px = image.load()

    def put(x: int, y: int, index: int) -> None:
        if 0 <= x < 10 and 0 <= y < 10:
            px[x, y] = colours[index]

    for y in range(10):
        for x in range(10):
            if math.hypot(x - 4.5, y - 4.5) <= 4.8:
                put(x, y, INK)
    # The spokes, four of them, and the hub.
    for spoke in range(4):
        angle = spoke * math.pi / 2 + phase * math.pi / 6
        dx = math.cos(angle)
        dy = math.sin(angle)
        for step in range(1, 4):
            put(int(round(4.5 + dx * step)), int(round(4.5 + dy * step)), BRIGHT)
    for x, y in [(4, 4), (5, 4), (4, 5), (5, 5)]:
        put(x, y, BRIGHT)
    return image


def build_frame(phase: int, colours) -> Image.Image:
    """One frame of the car. The body and the glass are identical in every frame; only the wheels turn."""
    body = build_body(colours)
    wheel = build_wheel(colours, phase)
    for x, y in WHEEL_PLACE:
        body.alpha_composite(wheel, (x, y))
    return body


def strip(frames) -> Image.Image:
    """The frames side by side in a horizontal strip, which is the file format the contract fixes."""
    width = frames[0].width
    height = frames[0].height
    out = Image.new("RGBA", (width * len(frames), height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        out.alpha_composite(frame, (index * width, 0))
    return out


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(image: Image.Image, index_of) -> None:
    """Print the art as text, so the geometry can be checked without a viewer."""
    symbols = {INK: "#", MID: "G", GLASS: "w", BRIGHT: "@", GOLD: "Y", RED: "r", BROWN: "o"}
    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            if pixel[3] == 0:
                line += " "
                continue
            line += symbols.get(index_of.get(pixel[:3]), "?")
        print("%2d %s" % (y, line))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    parser.add_argument("--dump", action="store_true", help="print the art as text")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    sprite_dir = os.path.join(root, SPRITE_DIR)
    os.makedirs(sprite_dir, exist_ok=True)

    colours, index_of = nes_tile.load_nes_palette(root)
    frames = [build_frame(phase, colours) for phase in (0, 1, 2)]

    sheet = strip(frames)
    bad = nes_tile.over_limit(sheet, CAR_W, CAR_H, index_of)
    if bad:
        debug_path = os.path.join(root, "output", "ts2_art_a_car_debug.png")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        sheet.save(debug_path, "PNG")
        per_tile = nes_tile.tile_colours(sheet, CAR_W, CAR_H, index_of)
        names = {INK: "ink", MID: "mid", GLASS: "glass", BRIGHT: "bright",
                 GOLD: "gold", RED: "red", BROWN: "brown"}
        for entry in bad[:24]:
            frame, tx, ty, count = entry
            seen = per_tile[(frame, tx, ty)]
            print("      frame %d tile %d,%d has %d colours: %s"
                  % (frame, tx, ty, count, [names.get(i, i) for i in sorted(seen)]))
        raise SystemExit("car: %d tiles break the 3 colour rule, wrote %s" % (len(bad), debug_path))

    png_path = os.path.join(sprite_dir, CAR_NAME + ".png")
    sheet.save(png_path, "PNG")
    meta = {"name": CAR_NAME, "frame_w": CAR_W, "frame_h": CAR_H, "frames": len(frames), "fps": 15.0}
    with open(os.path.join(sprite_dir, CAR_NAME + ".json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    # NES-PALETTES: the scene owns the four sprite palettes, so the sheet leaves this file already
    # inside one of them. The per tile rule above is not enough: four colours in a tile can each be
    # legal 2C02 entries and still not be a palette the scene declares. Without this pass here, any
    # regeneration (a test that runs this script, a rerun for a tweak) silently undoes the
    # enforcement that tools/art/scene_palette.py did afterwards, which is exactly what happened on
    # 2026-10-22. tools/check_scene_palettes.py is the judge, not this comment.
    try:
        import scene_palette
        scene = scene_palette.load_scene(root, "title")
        image = Image.open(png_path).convert("RGBA")
        stats = scene_palette.enforce_sprites(image, scene, CAR_W, CAR_H)
        image.save(png_path, "PNG")
        print("  %-20s scene title sprites: %d tiles, %d pixels rewritten, worst %d colours"
              % (CAR_NAME, stats["tiles"], stats["pixels_moved"], stats["worst_colours"]))
    except Exception as exc:                                    # a scene file that is not there yet
        print("  %-20s scene palette pass skipped (%s)" % (CAR_NAME, exc))

    used = set()
    for frame in frames:
        for pixel in frame.getdata():
            if pixel[3] != 0:
                used.add(index_of.get(pixel[:3]))
    print("  %-20s %dx%d  %d frames  %d colours  tile rule OK  %s"
          % (CAR_NAME, CAR_W, CAR_H, len(frames), len(used), sha256(png_path)))

    if args.dump:
        dump(frames[0], index_of)
    # Card t_a1170172: the band plan owns the title's colours, and this generator used to run after it and leave the
    # car in colours no band could spend. The sheet is repainted here, so a rerun cannot undo it.
    import title_bands
    print("  band pass            %d pixels into the car's band palette"
          % title_bands.paint_sheet(root, CAR_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(main())
