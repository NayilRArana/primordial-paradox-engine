#!/usr/bin/env python3
"""make_redraw_rows.py: the three rows the demo shows longest, redrawn in 2C02 colours.

Card t_17db999b, SPRITE-REDRAW-ROWS. The queue in data/sprite_redraw_queue.json names one row per
title scene sprite; this script draws the three rows that spend the most time on screen:

  the player      output/redraws/spr_player_ow.png       16 x 16, 8 frames   Zander Skye, 19
  the car         output/redraws/spr_title_car.png       64 x 32, 3 frames   the hatchback, redrawn in place
  the gate sentry output/redraws/spr_gate_sentry_ow.png  16 x 16, 8 frames   Morgan, a Navy rating

Why these three and not the rest: the player is on screen for the whole run, the car and its two
busts hold the title, and Morgan is the one person the demo talks to twice (ARRIVAL-CONTENT 4.1).
The player and the sentry are new files beside the mirror, because no such sprite existed: the
mirror only ever held the title cast. The car keeps its exact 64 x 32 x 3 geometry, so the runtime's
frame count and the wheel positions in tools/art/make_title_car.py do not move.

Palette discipline (ART-BIBLE 1.3 and RULE 0): every pixel is a data/nes_palette.json entry, every
8 x 8 tile carries at most 3 opaque colours, and no sheet shows more than 25 colours. Each sprite
names the scene sprite palette it is drawn to sit in:

  the player      title sp1 [$09, $00, $20] plus the hero blue ($21, $31) that ART-BIBLE RULE 0
                  point 3 reserves for him, and skin $36
  the car         title sp1 [$09 green, $00 grey, $20 white] plus $0B (title sp3), $28 headlight,
                  $16 tail light, $10 chrome, $08 suitcase, $36 beige door
  the sentry      ship sp0 [$00, $0F, $10] and sp1 [$02, $12, $30]; he is drawn in $0F, $02, $30, $36

Deterministic: no clock, no randomness, no window, no network. Writes three PNGs and one contact
sheet. Run from the repo root:

    python tools/art/make_redraw_rows.py
"""

from __future__ import annotations

import os
import shutil

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2C02 entries used here, by name, so a reader never has to decode a hex twice.
II = {
    "ink": (0x00, 0x00, 0x00),      # $0F
    "grey": (0x7C, 0x7C, 0x7C),     # $00
    "light": (0xBC, 0xBC, 0xBC),    # $10
    "white": (0xFC, 0xFC, 0xFC),    # $30
    "cream": (0xF8, 0xF8, 0xF8),    # $20
    "green": (0x00, 0x78, 0x00),    # $09 racing green
    "dgrey": (0x00, 0x58, 0x00),    # $0B dark green
    "navy": (0x00, 0x00, 0xBC),     # $02
    "blue": (0x00, 0x58, 0xF8),     # $12
    "sky": (0x3C, 0xBC, 0xFC),      # $21
    "pale": (0xA4, 0xE4, 0xFC),     # $31
    "skin": (0xF0, 0xD0, 0xB0),     # $36
    "gold": (0xF8, 0xB8, 0x00),     # $28
    "red": (0xF8, 0x38, 0x00),      # $16
    "brown": (0x88, 0x14, 0x00),    # $07
}
CLEAR = (0, 0, 0, 0)


def rgba(rgb):
    return (rgb[0], rgb[1], rgb[2], 255)


# --------------------------------------------------------------------------------------------------------------
# The player: Zander Skye, 19, blond, bomber jacket. One 16 x 16 cell, head 8 rows, body 8 rows, ink on every row.

def player_frame(pose: int) -> Image.Image:
    im = Image.new("RGBA", (16, 16), CLEAR)
    px = im.load()

    def put(x, y, key):
        if 0 <= x < 16 and 0 <= y < 16:
            px[x, y] = rgba(II[key])

    # head: outline on rows 0 to 6, hair on rows 1 to 3, face 3 to 6
    for x in range(3, 13):
        put(x, 0, "ink")
    for y in range(1, 4):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "hair" if "hair" in II else "gold")
    for y in range(4, 7):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "skin")
    # hairline: the fringe line that gives the head an interior dark row
    for x in range(4, 12):
        put(x, 3, "gold")
    put(4, 4, "gold")
    put(11, 4, "gold")
    # eyes, 2 px each (SP-012)
    for x in (5, 6, 9, 10):
        put(x, 5, "ink")
    # jaw line
    for x in range(4, 12):
        put(x, 7, "ink")

    # body: bomber jacket, open collar in pale blue, dark trousers
    for y in range(8, 13):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "sky")
    for y in (8, 9):
        for x in range(6, 10):
            put(x, y, "pale")
    for y in (10, 11):
        put(7, y, "pale")
        put(8, y, "pale")
    for x in range(4, 12):
        put(x, 12, "ink")          # hem

    # legs: three stride poses, 2 to 4 px of change, never the torso
    legs = {
        0: [(4, 5), (10, 11)],
        1: [(3, 4), (11, 12)],
        2: [(5, 6), (9, 10)],
    }
    for (a, b) in legs[pose % 3]:
        for x in range(a, b + 1):
            put(x, 13, "ink")
            put(x, 14, "ink")
        for x in range(a, b + 1):
            put(x, 15, "ink")
    return im


# --------------------------------------------------------------------------------------------------------------
# The gate sentry: Morgan, a Navy rating. Cap honour, horizontal collar band, black silk. Ink on every row.

def sentry_frame(pose: int) -> Image.Image:
    im = Image.new("RGBA", (16, 16), CLEAR)
    px = im.load()

    def put(x, y, key):
        if 0 <= x < 16 and 0 <= y < 16:
            px[x, y] = rgba(II[key])

    # cap: navy cover, ink top and sides, ink peak on row 3
    for x in range(3, 13):
        put(x, 0, "ink")
    for y in (1, 2):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "navy")
    for x in range(2, 14):
        put(x, 3, "ink")            # the peak, wider than the head
    # face
    for y in (4, 5, 6):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "skin")
    for x in (5, 6, 9, 10):
        put(x, 5, "ink")            # 2 px eyes
    # the rating's tell: a horizontal collar band across the chest, not the officer's V
    for x in range(3, 13):
        put(x, 7, "ink")
    # shirt: white, with the black silk knot
    for y in range(8, 12):
        put(3, y, "ink")
        put(12, y, "ink")
        for x in range(4, 12):
            put(x, y, "white")
    put(8, 9, "ink")
    put(8, 10, "ink")
    for x in range(4, 12):
        put(x, 12, "ink")           # shirt hem
    for y in (8, 11):
        put(4, y, "navy")
        put(11, y, "navy")          # dark cuffs, so the sleeve is not a white slab

    legs = {
        0: [(4, 5), (10, 11)],
        1: [(3, 4), (11, 12)],
        2: [(5, 6), (9, 10)],
    }
    for (a, b) in legs[pose % 3]:
        for y in (13, 14, 15):
            for x in range(a, b + 1):
                put(x, y, "ink")
    return im


# --------------------------------------------------------------------------------------------------------------
# The car: 64 x 32, side view, facing right, the geometry the manager fixed on 2026-10-20.

CAR_W, CAR_H = 64, 32


def car_body(bob: int) -> Image.Image:
    im = Image.new("RGBA", (CAR_W, CAR_H), CLEAR)
    d = ImageDraw.Draw(im)

    def oy(y):
        return y + bob

    body = [
        (6, 25), (6, 20), (8, 20), (10, 8), (13, 6), (44, 6), (52, 17), (56, 17),
        (56, 25), (48, 25), (44, 25), (40, 25), (36, 25), (32, 25), (28, 25),
        (24, 25), (20, 25), (16, 25), (12, 25), (8, 25),
    ]
    moved = [(x, oy(y)) for (x, y) in body]
    d.polygon(moved, fill=rgba(II["green"]))

    # wheel arches: a 10 x 10 wheel sits in each, centred at x 14 and x 46, so cut a radius 6 arch
    for cx in (14, 46):
        d.ellipse([cx - 6, oy(25) - 6, cx + 6, oy(25) + 6], fill=CLEAR)

    # the bottom edge is the second tone, but it stops either side of the beige door, so no 8 x 8
    # tile carries green, dark green, beige and ink at once
    d.rectangle([11, oy(24), 23, oy(25)], fill=rgba(II["dgrey"]))
    d.rectangle([40, oy(24), 55, oy(25)], fill=rgba(II["dgrey"]))

    # window band, rows 8 to 15, with the A pillar and the B pillar left green
    d.rectangle([13, oy(9), 45, oy(15)], fill=rgba(II["ink"]))
    d.rectangle([30, oy(9), 31, oy(15)], fill=rgba(II["green"]))   # B pillar
    d.rectangle([44, oy(9), 45, oy(15)], fill=rgba(II["green"]))   # A pillar

    # the mismatched beige front door, x 28 to 38
    d.rectangle([28, oy(16), 38, oy(23)], fill=rgba(II["skin"]))

    # roof rack and the brown suitcase
    for x in (20, 40):
        d.rectangle([x, oy(5), x, oy(6)], fill=rgba(II["ink"]))
    d.rectangle([21, oy(3), 39, oy(4)], fill=rgba(II["ink"]))
    d.rectangle([22, oy(1), 38, oy(3)], fill=rgba(II["brown"]))
    d.rectangle([22, oy(1), 38, oy(1)], fill=rgba(II["ink"]))

    # lights and bumpers: the ends are chrome, so no green reaches them
    d.rectangle([6, oy(18), 7, oy(19)], fill=rgba(II["red"]))       # tail light
    d.rectangle([57, oy(18), 58, oy(19)], fill=rgba(II["gold"]))    # headlight
    d.rectangle([8, oy(21), 12, oy(23)], fill=rgba(II["light"]))    # rear bumper
    d.rectangle([56, oy(21), 63, oy(23)], fill=rgba(II["light"]))   # front bumper

    # a 1 px ink outline on the silhouette, so the car separates from the road at 3x
    mask = im.split()[3].load()
    edge = []
    for y in range(CAR_H):
        for x in range(CAR_W):
            if mask[x, y] < 128:
                continue
            near_clear = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < CAR_W and 0 <= ny < CAR_H) or mask[nx, ny] < 128:
                    near_clear = True
                    break
            if near_clear:
                edge.append((x, y))
    for (x, y) in edge:
        im.putpixel((x, y), rgba(II["ink"]))

    # the roof line is a dark read at 3x, not a flat green top
    d.rectangle([14, oy(6), 44, oy(6)], fill=rgba(II["ink"]))
    return im


def main() -> int:
    # The card names game\art, and that is where the sprites go. game\datafiles\art is the folder the
    # runtime reads, but it is a generated mirror: tools/sync_art.py copies game\sprites_src into it, and
    # a run of that tool was measured putting the old car back inside two minutes on 2026-10-23 03:36.
    # Hand drawn art left in the mirror would be a second, silent source of truth, so this script does
    # not write there. The redraw reaches the running game when the generator that owns each sheet
    # (tools/art/title_car_v2.py for the car) carries it, which is a question for gamedev.
    #
    # Since card t_4e54cc9e the folder is output\redraws instead of game\art: game\art was untracked,
    # gitignored and read by nothing, and the queue now measures game\sprites_src, so a redraw goes to
    # scratch and only an owning generator writes the shipped sheet.
    out_dirs = [os.path.join(ROOT, "output", "redraws")]
    out = out_dirs[0]
    os.makedirs(out, exist_ok=True)

    # the player, 8 frames: three strides, cycled
    player = [player_frame(i % 3) for i in range(8)]
    sheet = Image.new("RGBA", (16 * 8, 16), CLEAR)
    for i, fr in enumerate(player):
        sheet.alpha_composite(fr, (16 * i, 0))
    sheet.save(os.path.join(out, "spr_player_ow.png"))

    # the sentry, 8 frames
    sentry = [sentry_frame(i % 3) for i in range(8)]
    sheet = Image.new("RGBA", (16 * 8, 16), CLEAR)
    for i, fr in enumerate(sentry):
        sheet.alpha_composite(fr, (16 * i, 0))
    sheet.save(os.path.join(out, "spr_gate_sentry_ow.png"))

    # the car, 3 frames, a 1 px vertical bob
    bodies = [car_body(0), car_body(1), car_body(0)]
    sheet = Image.new("RGBA", (CAR_W * 3, CAR_H), CLEAR)
    for i, fr in enumerate(bodies):
        sheet.alpha_composite(fr, (CAR_W * i, 0))
    sheet.save(os.path.join(out, "spr_title_car.png"))

    # the contact sheet: 4x, one labelled band per sprite, on the deck grey so the outline is judged
    scale = 4
    pad = 8
    label_h = 12
    deck = (0x7C, 0x7C, 0x7C)
    bands = [
        ("THE PLAYER  ZANDER SKYE  16x16  8 FRAMES", player, deck),
        ("THE CAR  SPR_TITLE_CAR  64x32  3 FRAMES", bodies, deck),
        ("THE GATE SENTRY  MORGAN  16x16  8 FRAMES", sentry, deck),
    ]
    widths = [len(frames) * frames[0].width * scale for _, frames, _ in bands]
    total_w = max(widths) + pad * 2
    total_h = pad
    for _, frames, _ in bands:
        total_h += label_h + frames[0].height * scale + pad
    contact = Image.new("RGBA", (total_w, total_h), rgba(deck))
    d = ImageDraw.Draw(contact)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    y = pad
    for label, frames, ground in bands:
        d.rectangle([pad, y, total_w - pad - 1, y + label_h - 1], fill=rgba((0x00, 0x00, 0x00)))
        # the label is drawn as a 1 bit mask so the sheet keeps a countable palette: a grey
        # antialiased ramp would put 200 entries into a file whose whole point is a colour count
        mask = Image.new("L", (total_w, label_h), 0)
        if font is not None:
            ImageDraw.Draw(mask).text((2, 0), label, fill=255, font=font)
        mask = mask.point(lambda v: 255 if v > 96 else 0)
        contact.paste(Image.new("RGBA", mask.size, rgba(II["white"])), (pad, y), mask)
        y += label_h
        x = pad
        for fr in frames:
            big = fr.resize((fr.width * scale, fr.height * scale), Image.NEAREST)
            contact.alpha_composite(big, (x, y))
            x += fr.width * scale
        y += frames[0].height * scale + pad
    contact_path = os.path.join(ROOT, "output", "chars_contact_after.png")
    os.makedirs(os.path.dirname(contact_path), exist_ok=True)
    contact.convert("RGB").save(contact_path)

    for p in ("spr_player_ow.png", "spr_gate_sentry_ow.png", "spr_title_car.png"):
        src = os.path.join(out_dirs[0], p)
        for extra in out_dirs[1:]:
            shutil.copyfile(src, os.path.join(extra, p))
        im = Image.open(src)
        print("wrote %-26s %dx%d  -> %s" % (p, im.width, im.height, ", ".join(
            os.path.relpath(d, ROOT) for d in out_dirs)))
    print("wrote output/chars_contact_after.png %dx%d" % (contact.width, contact.height))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
