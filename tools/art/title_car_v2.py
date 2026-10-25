#!/usr/bin/env python3
"""The v2 title car: the battered hatchback, seen from the side, exterior only.

This supersedes the body and the wheels of tools/art/make_title_car.py. What changed, and why:
  - the glass is one dark tint with a single diagonal moonlight glint, so the car reads as a closed
    shell on a night road instead of a lit room with people in it;
  - no faces, no busts, no steering wheel: the card says the car shows its exterior only, and the
    cast sprites (spr_title_konrad, spr_title_zander, spr_title_bubble) are moved out of the title;
  - the wheels are baked into the car sprite, so a wheel always sits in its arch band and cannot drift.

Clean room: every shape is a row table or a distance function written in this file. Nothing is traced,
copied or imported from any existing game, and no external image is read.

THE TILE RULE IS THE CONSTRAINT. A sprite tile is 8x8 and may carry 3 colours plus transparency, and the car's
own sprite palette title sp3 is ($0C $0B $20), so the whole sheet is drawn on those three entries and nothing
else. The car is 64 wide and 32 tall, which is eight tiles across and four down, and the layout is chosen band
by band:
  band 0 (rows  0 to  7)  the roof rack, the suitcase, the light roof edge
  band 1 (rows  8 to 15)  the side glass, the pillars, the moonlight glint
  band 2 (rows 16 to 23)  the body, the tail light, the headlight, the door shut line, the shadow side
  band 3 (rows 24 to 31)  the sill, the wheel arches, the wheels
The colours, and where each one is allowed to appear (knowledge/PALETTE-RULINGS-2026-10-24.md section 11 Q2,
card t_1738de73: the car's LARGEST FILL is the near white, because a layer is judged by RULE 0 point 2 on the
ink OR the body and both of this car's colours used to be dark):
  BODY    the near white $20: the body, the largest fill, the lit roof
  SHADOW  the racing green $0B: the shadow side along the bottom of the body, the sill, the arches, the tyres,
          the roof rack and the suitcase
  DARK    the blue-teal $0C, the darkest entry on the sheet: the glass, the shut line, the lamps, the straps
The tyres stay on the shadow rather than on the dark: three entries only go so far, and a dark tyre would lift
$0C past $20 and make the darkest entry the biggest fill again.

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

# THE SHEET SHIPS ON THREE ENTRIES, AND IT IS DRAWN ON THEM DIRECTLY.
#
# title sp3 is ($0C $0B $20) and the road band bg3 is the same three entries, so the car can only ever show those
# three and there is no fourth role to spend. The generator paints them itself: scene_palette.enforce_sprites and
# title_bands.paint_sheet below both find nothing to move, so what this file draws is what ships.
#
# Which entry carries which part is the ruling in knowledge/PALETTE-RULINGS-2026-10-24.md section 11 Q2 (card
# t_1738de73). RULE 0 point 2 asks a tiled layer to clear 3:1 with its ink OR its body on every ground under it,
# and the old car failed both readings: $0B is 2.40:1 against black and 1.00:1 against itself.
#   BODY    the near white $20, the LARGEST FILL. It is the reading that clears every ground the title draws,
#           because a light body is far from a dark road (9.0:1 on the road's $0B, 8.6:1 on its white marking).
#   SHADOW  the racing green $0B, the racing green stays on the car as its shadow side: the bottom of the body,
#           the sill, the arches, the tyres and the roof rack.
#   DARK    the blue-teal $0C, which stays the darkest entry, so the tool reads the ink as $0C: the glass, the
#           shut line, the lamps, the suitcase straps and the scuffs. Nothing here is darker than $0C.
#
# The tyres sit on the shadow and not on $0C, which is a budget decision and is measured: a $0C tyre lifts $0C
# past $20 and makes the darkest entry the biggest fill, which is the reading this repaint moves away from.
BODY = 0x20      # #f8f8f8  $20  the body: the largest fill, and what makes the car read on the road
SHADOW = 0x0B    # #005800  $0B  the racing green: the shadow side, the sill, the arches, the tyres, the rack
DARK = 0x0C      # #004058  $0C  the darkest entry: the glass, the shut line, the lamps, the straps

# The sheet must not carry anything darker than DARK, or the tool's ink reading ($0C) moves. This is the guard for
# that: the entry numbers of the two colours that used to be drawn and must not come back.
BLACK_GUARD = (0x0F, 0x00)

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
# lands in the body band (rows 16 to 23), which already carries the body, the shadow, the lights and the
# shut line. The frame animation is the wheels rolling, one spoke step per frame, which happens entirely
# inside the bottom tile row band (rows 24 to 31). No tile changes the set of colours it carries between
# frames.
GLASS_TOP = 8
GLASS_BOTTOM = 14

# The shadow side: the bottom rows of the body, from here down to the sill, are the racing green. Row 22 is
# two rows above the sill and the same two rows the arch tops reach into, so the green reads as one mass
# under the body rather than as a stripe across it.
SHADOW_TOP = 22

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

# The roof rack and the suitcase. The lit roof edge that used to be a separate role is gone with the repaint:
# the body is the light entry now, so the roof edge is the body and there is nothing to light.
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

    # The body itself, light, row by row, with the shadow side along its bottom edge.
    for y, (x0, x1) in BODY_ROWS.items():
        for x in range(x0, x1 + 1):
            put(x, y, BODY if y < SHADOW_TOP else SHADOW)

    # The side glass, a dark tint from the hatch back to the A pillar.
    for y in range(8, 16):
        for x in range(BODY_ROWS[y][0] + 1, a_pillar_x(y) - 1):
            put(x, y, DARK)

    # The B pillar, in body colour.
    for y in range(8, 16):
        for x in range(B_PILLAR[0], B_PILLAR[1] + 1):
            put(x, y, BODY)

    # The windscreen, the dark tint beyond the raked A pillar.
    for y in range(8, 16):
        for x in range(a_pillar_x(y) + 1, BODY_ROWS[y][1] + 1):
            put(x, y, DARK)

    # The A pillar itself, in body colour.
    for y in range(7, 17):
        put(a_pillar_x(y), y, BODY)

    # The single diagonal moonlight glint, across the side glass. It is the body's own light entry, because the
    # glass is the darkest entry on the sheet and the moonlight has to be something brighter than it.
    for x, y in nes_tile.thick_line([GLINT_FROM, GLINT_TO], 1):
        put(x, y, BODY)

    # The shut line of the front door, and its handle.
    for y in range(17, 24):
        put(DOOR_SHUT, y, DARK)
    for x in DOOR_HANDLE:
        put(x, 19, DARK)

    # The sill, on the shadow side, so the bottom edge reads as one straight mass under the body.
    for y in (24, 25):
        for x in range(8, 56):
            put(x, y, SHADOW)

    # The wheel arches: a half circle painted into the bottom of the body above each tyre. The body is
    # not cut through: the tyre and the arch are both the shadow side, so the shape reads as an arch around
    # the wheel, which is why the tyres are not on the dark entry.
    for cx, radius in ARCHES:
        for x in range(cx - radius, cx + radius + 1):
            top = arch_top(cx, radius, x)
            for y in range(int(math.ceil(top)), 26):
                put(x, y, SHADOW)

    # The headlight and the tail light, in the dark entry: the body is the light one now, so a lamp reads as a
    # dark lens on it rather than as a light. The beam is the separate headlight cone sprite, not this sheet.
    for x in range(HEADLIGHT[0], HEADLIGHT[1] + 1):
        put(x, 18, DARK)
        put(x, 19, DARK)
    for x in range(TAILLIGHT[0], TAILLIGHT[1] + 1):
        put(x, 18, DARK)
        put(x, 19, DARK)

    # The roof rack: the rails on the shadow side, and the suitcase on top of them, green with dark straps.
    for x in range(RAIL[0], RAIL[1] + 1):
        put(x, 5, SHADOW)
    for y in range(2, 4):
        for x in range(SUITCASE[0], SUITCASE[1] + 1):
            put(x, y, SHADOW)
    for x in range(SUITCASE[0], SUITCASE[1] + 1):
        put(x, 1, DARK)
        put(x, 4, DARK)
    for x in (27, 33):
        for y in range(2, 4):
            put(x, y, DARK)

    # A few scuffs, because the car is a battered old thing.
    for x, y in [(22, 22), (23, 22), (41, 21), (42, 21)]:
        put(x, y, DARK)

    return image


def build_wheel(colours, phase: int = 0) -> Image.Image:
    """A wheel seen from the side: a green tyre with light spokes and a light hub.

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
                put(x, y, SHADOW)
    # The spokes, four of them, and the hub.
    for spoke in range(4):
        angle = spoke * math.pi / 2 + phase * math.pi / 6
        dx = math.cos(angle)
        dy = math.sin(angle)
        for step in range(1, 4):
            put(int(round(4.5 + dx * step)), int(round(4.5 + dy * step)), BODY)
    for x, y in [(4, 4), (5, 4), (4, 5), (5, 5)]:
        put(x, y, BODY)
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
    symbols = {BODY: ".", SHADOW: "G", DARK: "w"}
    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            if pixel[3] == 0:
                line += " "
                continue
            line += symbols.get(index_of.get(pixel[:3]), "?")
        print("%2d %s" % (y, line))


def fills(image: Image.Image, index_of) -> dict:
    """{entry: pixel count} over the drawn sheet, so the fill rule can be proved instead of described."""
    counts = {}
    for pixel in image.getdata():
        if pixel[3] == 0:
            continue
        entry = index_of.get(pixel[:3])
        counts[entry] = counts.get(entry, 0) + 1
    return counts


def check_fills(image: Image.Image, index_of) -> None:
    """Refuse to write a sheet whose largest fill is not BODY, or that carries something darker than DARK.

    Card t_1738de73. tools/palette_synergy.py reads a tiled layer's ink as the frame's DARKEST colour and its
    body as the largest fill that is not that ink, so both readings are decided by these counts, and neither is
    visible in a colour count smaller than this one. A body that is not the light entry is a car that cannot
    clear RULE 0 point 2 on a dark road, and an entry darker than $0C moves the ink reading without changing the
    picture much. Both are arithmetic, so they are checked here rather than looked at afterwards.
    """
    counts = fills(image, index_of)
    darker = [entry for entry in counts if entry in BLACK_GUARD]
    if darker:
        raise SystemExit("car: the sheet carries %s, which is darker than the ink $0C"
                         % ", ".join("$%02X" % entry for entry in sorted(darker)))
    largest = max(counts, key=lambda entry: counts[entry])
    if largest != BODY:
        raise SystemExit("car: the largest fill is $%02X at %d px and the body has to be $%02X: palette_synergy "
                         "reads the largest fill that is not the darkest colour as the body"
                         % (largest, counts[largest], BODY))


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
        names = {BODY: "body", SHADOW: "shadow", DARK: "dark"}
        for entry in bad[:24]:
            frame, tx, ty, count = entry
            seen = per_tile[(frame, tx, ty)]
            print("      frame %d tile %d,%d has %d colours: %s"
                  % (frame, tx, ty, count, [names.get(i, i) for i in sorted(seen)]))
        raise SystemExit("car: %d tiles break the 3 colour rule, wrote %s" % (len(bad), debug_path))

    # Card t_1738de73: the fill rule the repaint is for, checked before the sheet is written. Per frame,
    # because that is the unit tools/palette_synergy.py judges.
    for frame in frames:
        check_fills(frame, index_of)

    png_path = os.path.join(sprite_dir, CAR_NAME + ".png")
    sheet.save(png_path, "PNG")
    meta = {"name": CAR_NAME, "frame_w": CAR_W, "frame_h": CAR_H, "frames": len(frames), "fps": 15.0,
            "layer": True}
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
    counts = fills(frames[0], index_of)
    print("  %-20s fills: $20 %d px, $0B %d px, $0C %d px, largest $%02X"
          % (CAR_NAME, counts.get(BODY, 0), counts.get(SHADOW, 0), counts.get(DARK, 0),
             max(counts, key=lambda entry: counts[entry])))

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
