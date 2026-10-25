#!/usr/bin/env python3
"""make_title_rows_v2.py: the two P0 title rows that were absent or off the tile grid, redrawn.

Card t_265cabb7 (AUTO-SPRITE-NEXT). The queue at data/sprite_redraw_queue.json names one row per
sprite the game asks for by name. Two P0 rows were still open and both are title props, not figures:

  spr_pp_window    output/redraws/spr_pp_window.png   72 x 8, nine frames of 8x8   was ABSENT
  spr_title_bubble output/redraws/spr_title_bubble.png 48 x 16, three frames of 16x16  was 42 x 10, off the grid

Every cell below is written out by hand as a character grid, the way tools/art/make_characters_v2.py
draws the cast: one letter per pixel, "." for transparent, and the letters are looked up in a palette
of data/nes_palette.json entries only. Nothing is scaled, recoloured or traced.

What decides each row (ART-BIBLE RULE 0, palette first):

  the window   a nine slice of 8x8 tiles: a 1 px white line ($20) on the outside, a 1 px dark green
               line ($0B) inside it, and an ink ($0F) fill. tool frame order is row major, so frame 0
               is the top left corner, 4 is the centre fill and 8 the bottom right corner.
               Source of the design: data/ui_layouts.json, the nine_slice contract.
  the bubble   $10 light grey body with a $0C dark teal outline and dots, on the title sky. Its frame
               is a whole 16x16 cell with the 10 x 12 art centred, so the PPU can fetch it.

Both sheets are written to output/redraws, the scratch folder a redraw goes in since game/art retired
(card t_4e54cc9e, ruling 3 of knowledge/PALETTE-RULINGS-2026-10-23.md). Nothing here writes the shipped
tree: game/sprites_src/{title,env,chars} is authored by the generator that owns each name, and
game/datafiles/art, which the runtime reads, is rebuilt from it by tools/sync_art.py. This tool draws the
rows the queue lists, measured at the path the row names, in the entries their own scene palettes carry.

The wordmark row is the exception to the hand drawn cells: spr_pp_title_logo belongs to
tools/art/title_logo_v2.py, which owns the name and now draws spec 14's crack through the O as well, so
logo_frames() calls that generator with the row's three entries instead of drawing a second copy. This
file builds the row and puts it on the contact sheet.

Usage:
    python tools/art/make_title_rows_v2.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from make_characters import Grid  # noqa: E402  (the grid type and its to_image)
import make_characters_v2 as cast  # noqa: E402  (the cast bands and the label letterer)
import title_logo_v2 as wordmark  # noqa: E402  (the project's own letterforms and the emblem geometry)

ROOT = os.path.dirname(os.path.dirname(HERE))
CLEAR = (0, 0, 0, 0)

# 2C02 entries, named, so no reader has to decode a hex twice.
WHITE = "#f8f8f8"   # $20
DGREEN = "#005800"  # $0B dark green
INK = "#000000"     # $0F
GREY_L = "#bcbcbc"  # $10 light grey
TEAL = "#004058"    # $0C dark teal


# ---------------------------------------------------------------------------------------------------------------
# The window, nine 8x8 tiles, row major: corners, edges, fill. A white outer line, a dark green inner line, an ink
# fill, which is the dialogue ground the 8x8 font is drawn in white on.
WINDOW_TILES = [
    # 0 top left corner
    [".AAAAAAA",
     "ABBBBBBB",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC"],
    # 1 top edge
    ["AAAAAAAA",
     "BBBBBBBB",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC"],
    # 2 top right corner
    ["AAAAAAA.",
     "BBBBBBBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA"],
    # 3 left edge
    ["ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC"],
    # 4 centre fill, the tile the text sits on
    ["CCCCCCCC"] * 8,
    # 5 right edge
    ["CCCCCCBA"] * 8,
    # 6 bottom left corner
    ["ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABCCCCCC",
     "ABBBBBBB",
     ".AAAAAAA"],
    # 7 bottom edge
    ["CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "CCCCCCCC",
     "BBBBBBBB",
     "AAAAAAAA"],
    # 8 bottom right corner
    ["CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "CCCCCCBA",
     "BBBBBBBA",
     "AAAAAAA."],
]
WINDOW_PALETTE = {"A": WHITE, "B": DGREEN, "C": INK}

# ---------------------------------------------------------------------------------------------------------------
# The bubble: three frames, one dot more each, so the ellipsis grows instead of pulsing. A 16x16 cell with the
# 12 x 10 body centred and a 2 px tail, which is what makes the frame fetchable by the PPU.
BUBBLE_HEAD = [
    "................",
    "................",
    "................",
    "...DDDDDDDDDD...",
    "..DEEEEEEEEEED..",
    ".DEEEEEEEEEEEED.",
]
BUBBLE_MID = [
    ".DEEEEEEEEEEEED.",
    ".DEEEEEEEEEEEED.",
    "..DEEEEEEEEEED..",
    "...DEEEDDDDDD...",
    "....E...........",
    "................",
    "................",
    "................",
    "................",
    "................",
]
BUBBLE_DOTS = {
    0: [".DEEEDDEEEEEEED.", ".DEEEDDEEEEEEED."],
    1: [".DEEEDDEDDEEEED.", ".DEEEDDEDDEEEED."],
    2: [".DEEEDDEDDEDDED.", ".DEEEDDEDDEDDED."],
}
BUBBLE_PALETTE = {"D": TEAL, "E": GREY_L}


# ---------------------------------------------------------------------------------------------------------------
# The wordmark: PRIMORDIAL PARADOX, two lines of the project's own slab serif capitals, spent from the three entries
# the title scene gives it (data/palettes/scene_title.json, sprite palette sp0 = $0F ink, $00 stone, $28 gold; the
# logo is band painted with bg0, which carries the same three plus the shared backdrop).
#
# Spec 14-8bit-look fixes the design: weathered stone letters, a thin gold inlay, a small lightning crack through the
# second O of PARADOX, a 1 px dark outline, and a 2 frame gold shimmer.
#
# The drawing does not live here. tools/art/title_logo_v2.py owns the sprite name spr_pp_title_logo (ruling 2 of
# knowledge/PALETTE-RULINGS-2026-10-23.md, and tested in tests/test_make_title_ui.py because a second writer put the
# v1 art back over the v2 sheet once already), and it now draws the crack as well, so this file holds no copy of the
# letterforms, the emblem or the crack: logo_frames() calls the owner. The one thing this file decides is the
# palette: it names the three entries once and passes stone where the owner draws its lit cap in $10 light grey,
# which is not one of the wordmark's three and which the title band pass repainted to stone anyway.
LOGO_INK = "#000000"     # $0F the 1 px outline and the drop shadow
LOGO_STONE = "#7c7c7c"   # $00 the weathered stone body of the letters
LOGO_GOLD = "#f8b800"    # $28 the thin inlay at the foot of every capital, the emblem bolt, and the crack


def _rgb(name):
    return tuple(int(name[i:i + 2], 16) for i in (1, 3, 5))


def logo_frames():
    """The wordmark's two frames, drawn by the generator that owns the sprite name.

    title_logo_v2.logo_frame already takes its colours by role, so the three entries are named once here
    and $10 light grey, which is not one of the wordmark's three, is never passed. Ruling 2 on card
    t_1c04d011: title_logo_v2.py keeps the name spr_pp_title_logo, this file builds the row and the
    contact sheet, and passing stone for HIGHLIGHT gives the shipped three entries with no band pass
    needed and no second band implementation.
    """
    ink = _rgb(LOGO_INK) + (255,)
    stone = _rgb(LOGO_STONE) + (255,)
    gold = _rgb(LOGO_GOLD) + (255,)
    return [wordmark.logo_frame(index, {wordmark.INK: ink, wordmark.BASE: stone,
                                        wordmark.HIGHLIGHT: stone, wordmark.GOLD: gold})
            for index in (0, 1)]



def window_frames():
    frames = []
    for rows in WINDOW_TILES:
        grid = Grid(8, 8)
        for y, row in enumerate(rows):
            grid.text(y, row)
        frames.append(grid)
    return frames


def bubble_frame(index):
    grid = Grid(16, 16)
    rows = BUBBLE_HEAD + BUBBLE_DOTS[index] + BUBBLE_MID
    for y, row in enumerate(rows):
        grid.text(y, row)
    return grid


def strip(images):
    width = sum(image.width for image in images)
    height = max(image.height for image in images)
    out = Image.new("RGBA", (width, height), CLEAR)
    x = 0
    for image in images:
        out.alpha_composite(image, (x, 0))
        x += image.width
    return out


# ---------------------------------------------------------------------------------------------------------------
# The font row: 77 glyphs of 8x8 in one ink, and a line of text cut out of the same sheet, so the contact sheet
# shows both the whole set and what a sentence looks like at 3x. The glyph order is the game's (pp_font_glyphs,
# ASCII order); a character that is not in the sheet is an error here, never a silent blank.
FONT_GLYPHS = " !\"'()*,-./0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ[]abcdefghijklmnopqrstuvwxyz"
FONT_SAMPLE = "The deck tilts. HP 12/12"


def font_sample_line(sheet):
    """One line of text, one 8x8 cell per character, cut from the font sheet itself."""
    cells = []
    for ch in FONT_SAMPLE:
        index = FONT_GLYPHS.find(ch)
        if index < 0:
            raise SystemExit("the sample line uses %r, which the font sheet does not have" % ch)
        cells.append(sheet.crop((index * 8, 0, index * 8 + 8, 8)))
    return strip(cells)



def audit(frames, name):
    """The row's own check, in words: distinct colours, and the worst 8x8 tile."""
    worst = 0
    worst_at = None
    for index, image in enumerate(frames):
        pixels = image.load()
        for ty in range(0, image.height, 8):
            for tx in range(0, image.width, 8):
                seen = set()
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        r, g, b, a = pixels[x, y]
                        if a:
                            seen.add((r, g, b))
                if len(seen) > worst:
                    worst, worst_at = len(seen), (index, tx // 8, ty // 8)
    print("  %-18s %d frames, worst tile %d opaque colours %s" % (name, len(frames), worst, worst_at))
    return worst


def cloud_over_ground(sheet, frame_w, frame_h):
    """The cloud frames drawn on the sky band they are actually drawn over, so the sheet proves the reading.

    The ground is output/cloud_sky_ground.png, the 48 x 16 crop of the title's own sky and parallax cloud
    layers under the sprite's placement (y 80, tools/art/compose_title_preview.py CLOUD_DY). It is tiled
    along x to the width of the strip, exactly as the title tiles its layers.
    """
    ground_path = os.path.join(ROOT, "output", "cloud_sky_ground.png")
    if not os.path.isfile(ground_path):
        raise SystemExit("the cloud ground is missing, build output/cloud_sky_ground.png first: %s" % ground_path)
    with Image.open(ground_path) as image:
        ground = image.convert("RGBA")
    frames = sheet.width // frame_w
    sky = Image.new("RGBA", (sheet.width, frame_h), (0, 0, 0, 255))
    for x in range(0, sheet.width, ground.width):
        sky.alpha_composite(ground.crop((0, 0, min(ground.width, sheet.width - x), frame_h)), (x, 0))
    for index in range(frames):
        sky.alpha_composite(sheet.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h)),
                            (index * frame_w, 0))
    return sky


def enemy_over_ground(sheet, frame_w, frame_h):
    """The enemy frames drawn on the sea band the battle puts under them.

    The ground is output/enemies_sea_ground.png, the 32 x 32 patch of the battle background at the
    enemy's own placement (tools/art/make_enemies.py ENEMY_X, ENEMY_Y, rebuilt with nothing drawn on
    it), so the band shows the figure against the pixels it is read on, not against black.
    """
    ground_path = os.path.join(ROOT, "output", "enemies_sea_ground.png")
    if not os.path.isfile(ground_path):
        raise SystemExit("the enemy ground is missing, build output/enemies_sea_ground.png first: %s" % ground_path)
    with Image.open(ground_path) as image:
        ground = image.convert("RGBA")
    frames = sheet.width // frame_w
    sea = Image.new("RGBA", (sheet.width, frame_h), (0, 0, 0, 255))
    for x in range(0, sheet.width, ground.width):
        sea.alpha_composite(ground.crop((0, 0, min(ground.width, sheet.width - x), frame_h)), (x, 0))
    for index in range(frames):
        sea.alpha_composite(sheet.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h)),
                            (index * frame_w, 0))
    return sea


def cursor_over_ground(sheet, frame_w, frame_h):
    """The menu cursor frames drawn on the band they are actually drawn over.

    The ground is output/cursor_menu_ground.png, the 8 x 8 cell of the composed title under
    CURSOR_X, CURSOR_Y (6, 66) with this sprite removed, which is 64 pixels of $11 #0078f8: band 4 of the
    title, painted bg1, the sky. Card t_ae4bbd15 measured it after finding that this cell is not one of
    the ground bands data/palettes/scene_title.json's band_sprites names for the cursor.
    """
    ground_path = os.path.join(ROOT, "output", "cursor_menu_ground.png")
    if not os.path.isfile(ground_path):
        raise SystemExit("the cursor ground is missing, build output/cursor_menu_ground.png first: %s" % ground_path)
    with Image.open(ground_path) as image:
        ground = image.convert("RGBA")
    frames = sheet.width // frame_w
    sky = Image.new("RGBA", (sheet.width, frame_h), (0, 0, 0, 255))
    for x in range(0, sheet.width, ground.width):
        sky.alpha_composite(ground.crop((0, 0, min(ground.width, sheet.width - x), frame_h)), (x, 0))
    for index in range(frames):
        sky.alpha_composite(sheet.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h)),
                            (index * frame_w, 0))
    return sky


def contact(path, window_strip, bubble_strip, font_strip, font_line, logo_strip,
            cloud_strip=None, cloud_ground=None, enemy_strips=None, enemy_ground=None,
            cursor_strip=None, cursor_ground=None, scale=4):
    """Every redrawn row at 4x, under the cast bands, on the black backdrop the game uses.

    A band may carry its own scale: the font strip is 616 px wide and at 4x it would be 2464 px, wider
    than every other band put together, so the strip is drawn at 1x and the sample line at 3x while the
    figures and the props stay at 4x. The wordmark is 448 px wide, so it is drawn at 1x and at 2x.
    """
    bands = [(label, image, scale) for label, image in
             [(spec["label"], cast.image_of(cast.sheet_frames(spec), spec["palette"])) for spec in cast.cast()]]
    bands.append(("THE WINDOW  SPR_PP_WINDOW  72x8  9 FRAMES", window_strip, scale))
    bands.append(("THE BUBBLE  SPR_TITLE_BUBBLE  48x16  3 FRAMES", bubble_strip, scale))
    if cloud_strip is not None:
        bands.append(("STORM CLOUD  SPR_TITLE_CLOUD  72x16  3 FRAMES  2x", cloud_strip, 2))
    if cloud_ground is not None:
        bands.append(("STORM CLOUD AT 2x ON THE SKY BAND IT STANDS IN", cloud_ground, 2))
    for label, image in (enemy_strips or []):
        bands.append((label, image, 3))
    if enemy_ground is not None:
        bands.append(("NAVY SAILOR AT 3x ON THE SEA IT IS READ ON, IDLE, IDLE, HIT", enemy_ground, 3))
    if cursor_strip is not None:
        bands.append(("THE MENU CURSOR  SPR_PP_MENU_CURSOR  16x8  2 FRAMES  LIT, UNLIT", cursor_strip, 4))
    if cursor_ground is not None:
        bands.append(("THE MENU CURSOR AT 4x ON THE SKY BAND IT IS DRAWN ON", cursor_ground, 4))
    bands.append(("THE FONT  SPR_PP_FONT8  616x8  77 FRAMES  ONE INK $30", font_strip, 1))
    bands.append(("THE FONT AT 3x  \"%s\"" % FONT_SAMPLE, font_line, 3))
    bands.append(("WORDMARK  SPR_PP_TITLE_LOGO  448x64  2 FRAMES  1x", logo_strip, 1))
    bands.append(("WORDMARK AT 2x  THE GOLD INLAY AND THE O CRACK", logo_strip, 2))
    widest = max(image.width * band_scale for _, image, band_scale in bands)
    width = 16 * scale + widest + 16 * scale
    height = 8 * scale
    for _label, image, band_scale in bands:
        height += 10 * scale + image.height * band_scale + 14 * scale
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    y = 8 * scale
    for label, image, band_scale in bands:
        cast.label_text(draw, label, 8 * scale, y, scale, (252, 252, 252))
        y += 10 * scale
        big = image.resize((image.width * band_scale, image.height * band_scale), Image.NEAREST)
        canvas.alpha_composite(big, (8 * scale, y))
        y += image.height * band_scale + 14 * scale
    canvas.save(path, "PNG")
    return canvas


def main() -> int:
    # Scratch output, not the tree: game/art retired on 2026-10-23 (card t_4e54cc9e). The shipped
    # sheets in game/sprites_src/title belong to the generators that own each name.
    out = os.path.join(ROOT, "output", "redraws")
    os.makedirs(out, exist_ok=True)

    window = window_frames()
    window_strip = strip([grid.to_image(WINDOW_PALETTE) for grid in window])
    window_strip.save(os.path.join(out, "spr_pp_window.png"))

    bubble = [bubble_frame(index).to_image(BUBBLE_PALETTE) for index in range(3)]
    bubble_strip = strip(bubble)
    bubble_strip.save(os.path.join(out, "spr_title_bubble.png"))

    logo = logo_frames()
    logo_strip = strip(logo)
    logo_strip.save(os.path.join(out, "spr_pp_title_logo.png"))

    # The font row is drawn by its own tool (tools/art/make_font_row_v2.py) from the licensed
    # rasteriser; this sheet reads the file it wrote, so the contact sheet cannot disagree with it.
    font_path = os.path.join(out, "spr_pp_font8.png")
    if not os.path.isfile(font_path):
        raise SystemExit("the font row is missing, run tools/art/make_font_row_v2.py first: %s" % font_path)
    font_sheet = Image.open(font_path).convert("RGBA")
    font_line = font_sample_line(font_sheet)

    audit([grid.to_image(WINDOW_PALETTE) for grid in window], "spr_pp_window")
    audit(bubble, "spr_title_bubble")
    audit(logo, "spr_pp_title_logo")

    # The storm cloud band is read from the SHIPPED sheet, not drawn a second time here: make_title_car.py
    # owns that name (card t_b08c01d5), so the band on the sheet is the file the game draws, and this sheet
    # cannot disagree with the row it is proving. The second cloud band puts the same frames on the sky band
    # the title draws them over, so the sheet shows the reading as well as the strip.
    cloud_path = os.path.join(ROOT, "game", "sprites_src", "title", "spr_title_cloud.png")
    with Image.open(cloud_path) as image:
        cloud_sheet = image.convert("RGBA")
    cloud_ground = cloud_over_ground(cloud_sheet, 24, 16)
    print("  storm cloud band read from %s, %dx%d" % (os.path.relpath(cloud_path, ROOT).replace(os.sep, "/"),
                                                     cloud_sheet.width, cloud_sheet.height))

    sheet = os.path.join(ROOT, "output", "sprites_v2_sheet.png")
    os.makedirs(os.path.dirname(sheet), exist_ok=True)
    # The two redrawn enemies are read from the SHIPPED sheets for the same reason the cloud is: the
    # generator that owns each name writes them, so a band cannot disagree with the row it proves.
    enemy_strips = []
    for label, name in (("NAVY SAILOR  SPR_PP_SAILOR  96x32  3 FRAMES  IDLE, IDLE, HIT  3x", "navy_sailor"),
                        ("PETTY OFFICER  SPR_PP_PETTY_OFFICER  96x32  3 FRAMES  IDLE, IDLE, HIT  3x", "petty_officer"),
                        ("GULL  SPR_PP_GULL  96x32  3 FRAMES  IDLE, IDLE, HIT  3x", "gull")):
        enemy_path = os.path.join(ROOT, "game", "sprites_src", "enemies", name + ".png")
        with Image.open(enemy_path) as image:
            enemy_strips.append((label, image.convert("RGBA").copy()))
        print("  enemy band read from %s" % os.path.relpath(enemy_path, ROOT).replace(os.sep, "/"))
    enemy_ground = enemy_over_ground(enemy_strips[0][1], 32, 32)
    # The cursor is read from the SHIPPED sheet for the same reason the cloud and the enemies are: the
    # generator that owns the name writes it, so this band cannot disagree with the row it proves.
    cursor_path = os.path.join(ROOT, "game", "sprites_src", "title", "spr_pp_menu_cursor.png")
    with Image.open(cursor_path) as image:
        cursor_strip = image.convert("RGBA").copy()
    print("  cursor band read from %s" % os.path.relpath(cursor_path, ROOT).replace(os.sep, "/"))
    cursor_ground = cursor_over_ground(cursor_strip, 8, 8)
    canvas = contact(sheet, window_strip, bubble_strip, font_sheet, font_line, logo_strip,
                     cloud_strip=cloud_sheet, cloud_ground=cloud_ground,
                     enemy_strips=enemy_strips, enemy_ground=enemy_ground,
                     cursor_strip=cursor_strip, cursor_ground=cursor_ground)
    print("  output/sprites_v2_sheet.png %dx%d" % (canvas.width, canvas.height))
    return 0



if __name__ == "__main__":
    sys.exit(main())
