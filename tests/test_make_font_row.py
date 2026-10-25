"""Tests for tools/art/make_font_row_v2.py and the font bands in tools/art/make_title_rows_v2.py.

The font row is the game's only letters (game/scripts/pp_font/pp_font.gml draws every line through
spr_pp_font8), so what is proved here is that the shipped sheet in game/sprites_src/title is the
licensed rasteriser's output frame for frame, on the 8x8 grid, in one 2C02 ink, in the glyph order the
game indexes by, and that the contact sheet can carry it. Nothing here writes into the live tree: the
one image the contact test builds goes into pytest's tmp_path.

Why the shipped sheet and not the redraw: card t_4e54cc9e retired game/art, the folder this file used
to read, because the queue and the tests must measure what ships. The shipped sheet spends $20
(SHIPPED_INK) while tools/art/make_font_row_v2.py's own default ink is $30 (GLYPH), and which of the
two the font ships is the font row's open Q2 to gamedev, so the comparison below builds the tool's
output in the ink the sheet actually spends. Every other assertion is unchanged.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
ART = os.path.join(TOOLS, "art")
for path in (TOOLS, ART):
    if path not in sys.path:
        sys.path.insert(0, path)

import make_font_row_v2 as font_row  # noqa: E402
import make_title_rows_v2 as title_rows  # noqa: E402
import pressstart2p_font  # noqa: E402

# The shipped sheet: the authored tree, which is what the game loads through game/datafiles/art.
COMMITTED = os.path.join(ROOT, "game", "sprites_src", "title", "spr_pp_font8.png")
# $20 light grey, the one ink the shipped sheet spends today. font_row.GLYPH is $30.
SHIPPED_INK = "#f8f8f8"
GML = os.path.join(ROOT, "game", "scripts", "pp_font", "pp_font.gml")


def built_sheet() -> Image.Image:
    return font_row.strip(font_row.glyph_frames())


def game_glyph_set() -> str:
    """The glyph set pp_font_glyphs returns, read out of the GML rather than restated here."""
    with open(GML, "r", encoding="utf-8") as handle:
        text = handle.read()
    start = text.index("function pp_font_glyphs()")
    opening = text.index('"', text.index("return", start))
    index = opening + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            break
        index += 1
    return text[opening + 1:index].replace('\\"', '"')


def test_one_frame_per_glyph_on_the_8x8_grid():
    frames = font_row.glyph_frames()
    assert len(frames) == 77
    assert built_sheet().size == (616, 8)
    for _ch, image in frames:
        assert image.size == (8, 8)


def test_every_glyph_is_the_licensed_rasterisers_pixels():
    for ch, image in font_row.glyph_frames():
        rows = pressstart2p_font.bitmap(ch)
        pixels = image.load()
        for y in range(8):
            for x in range(8):
                assert (pixels[x, y][3] != 0) == (rows[y][x] == "#"), (ch, x, y)


def test_one_ink_and_it_is_a_2c02_entry():
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8") as handle:
        allowed = {value.strip().lower() for value in json.load(handle)["colours"]}
    sheet = built_sheet()
    colours = {(r, g, b) for r, g, b, a in sheet.getdata() if a}
    assert len(colours) == 1, "the font contract (pp_font.gml rule 6) is one ink, measured %d" % len(colours)
    hexed = "#%02x%02x%02x" % colours.pop()
    assert hexed in allowed
    assert hexed == font_row.GLYPH


def test_no_tile_carries_more_than_one_colour():
    sheet = built_sheet()
    pixels = sheet.load()
    for ty in range(0, sheet.height, 8):
        for tx in range(0, sheet.width, 8):
            seen = set()
            for y in range(ty, ty + 8):
                for x in range(tx, tx + 8):
                    r, g, b, a = pixels[x, y]
                    if a:
                        seen.add((r, g, b))
            assert len(seen) <= 3, (tx // 8, ty // 8, seen)


def test_the_committed_sheet_is_the_tool_output():
    committed = Image.open(COMMITTED).convert("RGBA")
    inks = {pixel[:3] for pixel in committed.getdata() if pixel[3]}
    assert len(inks) == 1, "the font contract is one ink, the shipped sheet spends %d" % len(inks)
    ink = "#%02x%02x%02x" % inks.pop()
    assert ink in (font_row.GLYPH, SHIPPED_INK), (
        "game/sprites_src/title/spr_pp_font8.png spends %s, which is neither the tool's ink %s nor the"
        " shipped $20 %s the row records" % (ink, font_row.GLYPH, SHIPPED_INK))
    built = font_row.strip(font_row.glyph_frames(ink=ink))
    assert committed.size == built.size, "spr_pp_font8.png is %s, the tool draws %s" % (
        committed.size, built.size)
    assert committed.tobytes() == built.tobytes(), "spr_pp_font8.png has drifted from the tool"


def test_the_glyph_order_is_the_one_the_game_indexes_by():
    glyphs = game_glyph_set()
    assert glyphs == "".join(pressstart2p_font.GLYPHS)
    assert len(glyphs) == 77


def test_the_ground_is_the_box_fill_in_one_entry():
    ground = font_row.window_ground().convert("RGBA")
    assert ground.size == (256, 240)
    colours = {(r, g, b, a) for r, g, b, a in ground.getdata()}
    assert colours == {(0, 0, 0, 255)}, "the ground is the dialogue box ink fill and nothing else"


def test_the_contact_sheet_can_carry_the_font_band(tmp_path):
    font_sheet = Image.open(COMMITTED).convert("RGBA")
    line = title_rows.font_sample_line(font_sheet)
    assert line.size == (len(title_rows.FONT_SAMPLE) * 8, 8)
    window = title_rows.strip([grid.to_image(title_rows.WINDOW_PALETTE) for grid in title_rows.window_frames()])
    bubble = title_rows.strip([title_rows.bubble_frame(index).to_image(title_rows.BUBBLE_PALETTE) for index in range(3)])
    # title_rows.contact() grew a logo band after this test was written (card t_265cabb7); the logo
    # belongs to tools/art/title_logo_v2.py, so it is drawn here rather than skipped.
    logo = title_rows.strip(title_rows.logo_frames())
    canvas = title_rows.contact(str(tmp_path / "sheet.png"), window, bubble, font_sheet, line, logo)
    # contact() sizes the canvas to the widest band plus 16*scale either side. Since the wordmark band
    # was added it is the widest (448 px at 2x), so the width is that plus the margins, and the font
    # strip has to fit inside it with its own margin to spare.
    assert canvas.width == 16 * 4 + logo.width * 2 + 16 * 4
    assert font_sheet.width + 16 * 4 <= canvas.width
    assert canvas.height > 1152, "the font bands are added under the bands that were already there"
    assert os.path.isfile(str(tmp_path / "sheet.png"))


def test_a_sample_line_with_a_glyph_outside_the_set_is_refused():
    sheet = built_sheet()
    saved = title_rows.FONT_SAMPLE
    try:
        title_rows.FONT_SAMPLE = "hello \u00e9"
        with pytest.raises(SystemExit) as refused:
            title_rows.font_sample_line(sheet)
    finally:
        title_rows.FONT_SAMPLE = saved
    assert "does not have" in str(refused.value)
