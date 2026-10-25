#!/usr/bin/env python3
"""make_font_row_v2.py: the 8x8 text font row, drawn to the UI palette rules.

Card t_ac9768da (AUTO-SPRITE-NEXT). The queue row is spr_pp_font8, the first P0 row that was not
done: game/art/spr_pp_font8.png measured 352 x 8, 44 frames, ONE colour, and that colour was
#c8c8d4, which is not a 2C02 output, so 564 of 564 drawn pixels were off the palette.

What decides this row
---------------------
1. ART-BIBLE RULE 0 (palette first) and the row's own palette_roles: the glyph is $30 white. The ui
   scene (data/scene_palettes.json, id "ui") carries $30 (48, #fcfcfc) in ALL FOUR of its sprite
   palettes (sp0 15/40/48, sp1 0/48/40, sp2 2/48/40, sp3 2/0/48), so one ink at $30 lets the same
   frame be drawn by any of them. The committed sheet in game/sprites_src/title uses $20 (#f8f8f8),
   and $20 sits in NO ui sprite palette, so the shipped sheet spends a colour the UI set cannot
   carry. That is a palette_synergy set_member failure on every glyph, and it is the reason this
   row's ink is $30 and not the $20 the live copy uses.
2. The font contract (game/scripts/pp_font/pp_font.gml, rule 6; knowledge/FONT-CONTRACT-AUDIT-2026-10-23.md
   row A1) says the sheet holds ONE ink. The queue row also lists "$02 navy shadow at 1 px". Those
   two disagree. Gamedev owns the font contract, so this tool draws the one ink and the shadow is
   posted as a Q: instead of being coded. A second tone would also break the frame by frame pixel
   identity to pressstart2p_font.bitmap that tests/test_make_title_ui.py asserts.
3. The glyphs are the licensed Press Start 2P rasterisation the project already ships, one 8x8 cell
   per glyph in ASCII order (pressstart2p_font.GLYPHS, 77 glyphs). Nothing here invents a letterform:
   hand drawing 77 letters would be a second font and would override that decision. What is authored
   by hand is the colour structure: one ink, transparent elsewhere, no antialiasing, no scaling.

The ground
----------
output/font_window_ground.png is the ground a glyph stands on: a 256 x 240 frame of the dialogue box's
$0F ink fill. It is the fill alone, not the nine slice, because palette_synergy measures one sprite
layer against one background layer and the box is a sprite: its $20 and $0B lines are in no ui
BACKGROUND palette, and tiling the window in as a background failed background_area on 58 of the 77
frames when it was tried. With the fill as the ground, the pairing measured is the one that happens on
screen: a $30 glyph on ink, inside the ui palette set.

Usage:
    python tools/art/make_font_row_v2.py
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import pressstart2p_font  # noqa: E402  (the licensed rasteriser, one 8x8 cell per glyph)

ROOT = os.path.dirname(os.path.dirname(HERE))
CELL = 8
CLEAR = (0, 0, 0, 0)

# 2C02 entries this row spends, named so no reader has to decode a hex twice.
GLYPH = "#fcfcfc"  # $30, carried by all four ui sprite palettes
BOX_FILL = "#000000"  # $0F ink fill, the ground the glyphs stand on


def glyph_frames(ink: str | None = None):
    """One 8x8 frame per glyph, in the ASCII order the game indexes by.

    `ink` defaults to GLYPH ($30). The shipped sheet spends $20, and which of the two ships is
    gamedev's call (the font row's Q2), so a reader that has to compare against the shipped sheet
    passes its ink in rather than this tool guessing.
    """
    frames = []
    colour = (ink or GLYPH)
    pen = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    for ch in pressstart2p_font.GLYPHS:
        image = Image.new("RGBA", (CELL, CELL), CLEAR)
        rows = pressstart2p_font.bitmap(ch)
        for y in range(CELL):
            for x in range(CELL):
                if rows[y][x] == "#":
                    image.putpixel((x, y), pen)
        frames.append((ch, image))
    return frames


def strip(frames):
    sheet = Image.new("RGBA", (CELL * len(frames), CELL), CLEAR)
    for index, (_ch, image) in enumerate(frames):
        sheet.alpha_composite(image, (index * CELL, 0))
    return sheet


def window_ground():
    """The ground the font is drawn on: a 256 x 240 frame of the dialogue box's $0F ink fill.

    Why the fill alone. palette_synergy measures ONE sprite layer against ONE background layer, and the
    dialogue box is not a background: game/sprites_src/title/spr_pp_window.png is a sprite sheet whose lines are $20
    and $0B, and the ui scene's four BACKGROUND palettes carry none of $20, $0B or $0F (they are
    02/30/00, 02/30/28, 30/00/28, 02/00/28). Tiling the window in as a background therefore failed the
    background_area rule on 58 of the font's 77 frames when it was measured, which is a fact about the
    layer the box is drawn in, not about a glyph. What a glyph actually stands on is the fill the box
    supplies, and that fill is $0F ink. So the probe ground is that fill and nothing else.
    """
    ink = tuple(int(BOX_FILL[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    return Image.new("RGBA", (256, 240), ink)



def audit(sheet, frames):
    """The numbers the queue row stores: size, frames, colours, worst tile, off palette pixels."""
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8") as handle:
        allowed = {value.strip().lower() for value in json.load(handle)["colours"]}
    pixels = sheet.load()
    found = {}
    off = 0
    for y in range(sheet.height):
        for x in range(sheet.width):
            r, g, b, a = pixels[x, y]
            if not a:
                continue
            hexed = "#%02x%02x%02x" % (r, g, b)
            found[hexed] = found.get(hexed, 0) + 1
            if hexed not in allowed:
                off += 1
    worst = 0
    worst_at = None
    for index, (_ch, image) in enumerate(frames):
        px = image.load()
        seen = set()
        for y in range(CELL):
            for x in range(CELL):
                r, g, b, a = px[x, y]
                if a:
                    seen.add((r, g, b))
        if len(seen) > worst:
            worst, worst_at = len(seen), index
    blank = [ch for ch, image in frames if image.getbbox() is None and ch != " "]
    return {
        "sheet_px": [sheet.width, sheet.height],
        "frames": len(frames),
        "frame_px": [CELL, CELL],
        "colours": len(found),
        "entries": sorted(found),
        "drawn_px": sum(found.values()),
        "off_palette_px": off,
        "worst_tile_opaque": worst,
        "worst_tile_at_frame": worst_at,
        "blank_frames_excluding_space": blank,
    }


def main() -> int:
    frames = glyph_frames()
    sheet = strip(frames)
    # The redraw goes to output/redraws/, not into the tree: game/art retired on 2026-10-23 (card
    # t_4e54cc9e) and game/sprites_src/title/spr_pp_font8.png belongs to tools/art/make_title_ui.py.
    art = os.path.join(ROOT, "output", "redraws")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, "spr_pp_font8.png")
    sheet.save(path, "PNG")

    ground = window_ground()
    out = os.path.join(ROOT, "output")
    os.makedirs(out, exist_ok=True)
    ground_path = os.path.join(out, "font_window_ground.png")
    ground.save(ground_path, "PNG")

    numbers = audit(sheet, frames)
    print("spr_pp_font8  %dx%d  %d frames  %d colours  off palette %d"
          % (numbers["sheet_px"][0], numbers["sheet_px"][1], numbers["frames"],
             numbers["colours"], numbers["off_palette_px"]))
    print("  entries: %s" % ", ".join(numbers["entries"]))
    print("  worst tile %d opaque colours at frame %d; blank frames (other than space): %s"
          % (numbers["worst_tile_opaque"], numbers["worst_tile_at_frame"],
             numbers["blank_frames_excluding_space"] or "none"))
    print("  ground: %s 256x240" % os.path.relpath(ground_path, ROOT).replace(os.sep, "/"))
    with open(os.path.join(ROOT, "output", "_font_row_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(numbers, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
