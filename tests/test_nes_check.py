"""Tests for tools/nes_check.py: one passing and one failing case for each NES drawing rule.

Every fixture is a real PNG written into tmp_path and pushed through the same path a person uses, so the test
proves the file reading, the rule, and the exit code, not just a helper function. The palette under test is
data\\nes_palette.json (no data\\art_bible.json exists yet, which is the tool's documented order).

The five rules, from NESdev wiki "PPU palettes" and "PPU pattern tables":
  - grid: the PPU draws 8x8 tiles, so both edges are multiples of 8;
  - palette: a visible pixel is one of the 64 2C02 outputs;
  - sprite_tile: a sprite tile carries 3 colours plus transparent;
  - background_area: a 16x16 attribute area carries 3 colours plus the one shared backdrop;
  - screen_colours: at most 25 colours on screen in one frame.
"""

from __future__ import annotations

import json
import os

import pytest
from PIL import Image

import nes_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES = os.path.join(ROOT, "game", "sprites_src", "title")

WHITE = (0xfc, 0xfc, 0xfc)
RED = (0xf8, 0x38, 0x00)
GREEN = (0x00, 0xa8, 0x00)
BLUE = (0x00, 0x58, 0xf8)
GREY = (0x7c, 0x7c, 0x7c)
BLACK = (0x00, 0x00, 0x00)
OFF_PALETTE = (0xc8, 0xc8, 0xd4)   # the old project paper colour: legal in data/palette.json, not in 2C02


def make_png(path, size, blocks):
    """A transparent RGBA PNG with each block pasted as a solid rectangle. blocks: [(x, y, w, h, rgb)]."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x0, y0, w, h, rgb in blocks:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                img.putpixel((x, y), tuple(rgb) + (255,))
    img.save(path, "PNG")
    return str(path)


def rules(report):
    return [problem["rule"] for problem in report["problems"]]


def run(png, kind, *extra):
    """Run the command line exactly as a person would, and return (exit code, stdout)."""
    import io
    from contextlib import redirect_stdout

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = nes_check.main([png, "--type", kind] + list(extra))
    return code, buffer.getvalue()


# ---------------------------------------------------------------------------------------------------------------
# Rule 1, the grid.

def test_grid_multiple_of_8_passes(tmp_path):
    png = make_png(tmp_path / "grid_ok.png", (16, 8), [(0, 0, 8, 8, WHITE)])
    code, out = run(png, "sprite")
    assert code == 0, out
    assert "PASS" in out


def test_grid_not_multiple_of_8_fails(tmp_path):
    png = make_png(tmp_path / "grid_bad.png", (10, 8), [(0, 0, 8, 8, WHITE)])
    code, out = run(png, "sprite")
    assert code == 1, out
    assert "width 10 is not a multiple of 8" in out


# ---------------------------------------------------------------------------------------------------------------
# Rule 2, the palette.

def test_palette_colour_from_the_2c02_passes(tmp_path):
    png = make_png(tmp_path / "pal_ok.png", (8, 8), [(0, 0, 8, 8, RED)])
    code, out = run(png, "sprite")
    assert code == 0, out


def test_palette_colour_outside_the_2c02_fails(tmp_path):
    png = make_png(tmp_path / "pal_bad.png", (8, 8), [(0, 0, 8, 8, OFF_PALETTE)])
    code, out = run(png, "sprite")
    assert code == 1, out
    assert "#c8c8d4" in out and "off palette" in out


# ---------------------------------------------------------------------------------------------------------------
# Rule 3, sprite tiles: 3 colours plus transparent.

def test_sprite_tile_with_three_colours_passes(tmp_path):
    png = make_png(tmp_path / "tile_ok.png", (8, 8), [
        (0, 0, 4, 8, WHITE), (4, 0, 2, 8, RED), (6, 0, 2, 8, GREEN)])
    code, out = run(png, "sprite")
    assert code == 0, out


def test_sprite_tile_with_four_colours_fails_and_names_the_tile(tmp_path):
    png = make_png(tmp_path / "tile_bad.png", (16, 8), [
        (0, 0, 8, 8, WHITE), (0, 0, 8, 4, RED), (0, 0, 4, 8, GREEN), (0, 0, 2, 8, BLUE)])
    code, out = run(png, "sprite")
    assert code == 1, out
    assert "tile 0,0" in out and "sprite_tile" in out


def test_sprite_rule_is_not_applied_to_backgrounds(tmp_path):
    """A background is judged per 16x16 area against the shared backdrop, so a tile holding the backdrop plus
    three colours is legal there even though the same tile would fail as a sprite."""
    png = make_png(tmp_path / "bg_four_in_a_tile.png", (16, 16), [
        (0, 0, 16, 16, BLACK), (0, 0, 4, 8, WHITE), (4, 0, 2, 8, RED), (6, 0, 2, 8, GREEN)])
    code, out = run(png, "background", "--backdrop", "#000000")
    assert code == 0, out


# ---------------------------------------------------------------------------------------------------------------
# Rule 4, background areas: 3 colours plus one shared backdrop.

def test_background_area_with_three_colours_and_a_backdrop_passes(tmp_path):
    png = make_png(tmp_path / "area_ok.png", (16, 16), [
        (0, 0, 8, 16, BLACK), (8, 0, 8, 16, WHITE), (8, 0, 4, 16, RED), (8, 0, 2, 16, GREEN)])
    code, out = run(png, "background", "--backdrop", "#000000")
    assert code == 0, out


def test_background_area_with_four_colours_besides_the_backdrop_fails(tmp_path):
    png = make_png(tmp_path / "area_bad.png", (16, 16), [
        (0, 0, 16, 16, BLACK), (0, 0, 16, 4, WHITE), (0, 4, 16, 4, RED),
        (0, 8, 16, 4, GREEN), (0, 12, 16, 4, BLUE)])
    code, out = run(png, "background", "--backdrop", "#000000")
    assert code == 1, out
    assert "area 0,0" in out and "background_area" in out


def test_the_backdrop_is_shared_across_areas_when_not_declared(tmp_path):
    """With no --backdrop the tool takes the most common colour, and the same shade is exempt in every area."""
    png = make_png(tmp_path / "area_infer.png", (16, 16), [
        (0, 0, 16, 16, BLACK), (0, 0, 4, 4, RED), (4, 0, 4, 4, GREEN)])
    code, out = run(png, "background")
    assert code == 0, out
    assert "backdrop #000000 (the most common colour in the image)" in out


# ---------------------------------------------------------------------------------------------------------------
# Rule 5, colours on screen: 25 for a frame, and the limit can be lowered.

def nes_colours(limit=40):
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        raw = json.load(handle)["colours"]
    out = []
    for value in raw:
        rgb = tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        if rgb not in out:
            out.append(rgb)
    return out[:limit]


def test_twenty_five_colours_on_screen_passes_the_screen_rule(tmp_path):
    colours = nes_colours(25)
    blocks = [(index * 8, 0, 8, 8, colour) for index, colour in enumerate(colours)]
    png = make_png(tmp_path / "screen_ok.png", (25 * 8, 8), blocks)
    report = nes_check.check(nes_check.load_image(png), "sprite",
                             nes_check.load_palette(os.path.join(ROOT, "data", "nes_palette.json")))
    assert "screen_colours" not in rules(report), report["problems"]


def test_twenty_six_colours_on_screen_fails_the_screen_rule(tmp_path):
    colours = nes_colours(26)
    blocks = [(index * 8, 0, 8, 8, colour) for index, colour in enumerate(colours)]
    png = make_png(tmp_path / "screen_bad.png", (26 * 8, 8), blocks)
    report = nes_check.check(nes_check.load_image(png), "sprite",
                             nes_check.load_palette(os.path.join(ROOT, "data", "nes_palette.json")))
    assert "screen_colours" in rules(report), report["problems"]
    detail = [p for p in report["problems"] if p["rule"] == "screen_colours"][0]
    assert "26 colours" in detail["detail"] and "may show 25" in detail["detail"]


def test_max_colours_lowers_the_screen_limit(tmp_path):
    colours = nes_colours(3)
    blocks = [(index * 8, 0, 8, 8, colour) for index, colour in enumerate(colours)]
    png = make_png(tmp_path / "screen_limit.png", (3 * 8, 8), blocks)
    code, out = run(png, "sprite", "--max-colours", "2")
    assert code == 1, out
    assert "may show 2" in out


# ---------------------------------------------------------------------------------------------------------------
# The command line itself: exit codes, the JSON report and the offending tile list.

def test_json_report_records_the_failure(tmp_path):
    png = make_png(tmp_path / "report.png", (8, 8), [
        (0, 0, 8, 8, WHITE), (0, 0, 8, 4, RED), (0, 0, 4, 8, GREEN), (0, 0, 2, 8, BLUE)])
    out_json = tmp_path / "report.json"
    code, out = run(png, "sprite", "--json", str(out_json))
    assert code == 1, out
    with open(out_json, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["ok"] is False
    assert report["size"] == [8, 8] and report["tiles"] == [1, 1]
    assert any(p["rule"] == "sprite_tile" and p["tile"] == [0, 0] for p in report["problems"])
    assert report["palette_source"].startswith("data\\nes_palette.json")


def test_a_missing_file_is_an_error_not_a_pass(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        run(str(tmp_path / "nope.png"), "sprite")
    assert "does not exist" in str(excinfo.value)


# ---------------------------------------------------------------------------------------------------------------
# The committed assets this card produced.

def test_the_committed_font_passes_as_a_sprite():
    code, out = run(os.path.join(SPRITES, "spr_pp_font8.png"), "sprite")
    assert code == 0, out
    assert "368x8" in out and "46 tiles" in out and "1 colours" in out


def test_the_committed_window_passes_as_a_sprite():
    code, out = run(os.path.join(SPRITES, "spr_pp_window.png"), "sprite")
    assert code == 0, out
    assert "72x8" in out and "9 tiles" in out


def test_the_window_json_names_the_nine_slices_in_frame_order():
    with open(os.path.join(SPRITES, "spr_pp_window.json"), "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["frame_w"] == meta["frame_h"] == 8
    assert meta["frames"] == 9
    assert meta["slice"] == ["tl", "t", "tr", "l", "c", "r", "bl", "b", "br"], meta["slice"]
    assert meta["colours"] == {"fill": "#0000bc", "white": "#fcfcfc", "grey": "#7c7c7c", "backdrop": "#000000"}


def test_the_window_pixels_are_the_slices_the_json_promises():
    """Frame by frame: the centre is all fill, the left edge is border then inner line then fill, and the
    top left corner drops its outermost pixel so the box reads as rounded."""
    with open(os.path.join(SPRITES, "spr_pp_window.json"), "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    fill = tuple(int(meta["colours"]["fill"][i:i + 2], 16) for i in (1, 3, 5))
    white = tuple(int(meta["colours"]["white"][i:i + 2], 16) for i in (1, 3, 5))
    grey = tuple(int(meta["colours"]["grey"][i:i + 2], 16) for i in (1, 3, 5))
    with Image.open(os.path.join(SPRITES, "spr_pp_window.png")) as img:
        sheet = img.convert("RGBA")

    def frame(name):
        return sheet.crop((meta["slice"].index(name) * 8, 0, meta["slice"].index(name) * 8 + 8, 8))

    centre = frame("c")
    for y in range(8):
        for x in range(8):
            assert centre.getpixel((x, y)) == fill + (255,), "centre %d,%d is not fill" % (x, y)

    top_left = frame("tl")
    assert top_left.getpixel((0, 0))[3] == 0, "the top left corner pixel is not transparent"
    assert top_left.getpixel((1, 0))[:3] == white
    assert top_left.getpixel((1, 1))[:3] == grey
    assert top_left.getpixel((2, 2))[:3] == fill

    left = frame("l")
    assert [left.getpixel((x, 0))[:3] for x in (0, 1, 2)] == [white, grey, fill]

    top = frame("t")
    assert [top.getpixel((0, y))[:3] for y in (0, 1, 2)] == [white, grey, fill]

    for name in ("tr", "br"):
        assert frame(name).getpixel((7, 0))[3] == 0 or frame(name).getpixel((7, 7))[3] == 0, name


# ---------------------------------------------------------------------------------------------------------------
# The 3x preview the manager looks at, because a worker cannot see images.

def test_the_3x_preview_exists_and_shows_the_window_at_three_times(tmp_path):
    path = os.path.join(ROOT, "output", "nes_ui_preview.png")
    assert os.path.isfile(path), "run tools\\art\\make_pp_window.py to build the preview"
    with Image.open(path) as img:
        preview = img.convert("RGBA")
    assert preview.size == (1184, 760), "the preview canvas changed size: %s" % (preview.size,)

    # The composed 21x9 window sits at (48, 48) and every tile is drawn at 3x, so the centre tile's fill
    # reaches these points and the border row above it is white. Sampling proves the drawing, not a label.
    fill = (0x00, 0x00, 0xbc, 255)
    white = (0xfc, 0xfc, 0xfc, 255)
    assert preview.getpixel((48 + 10 * 24 + 3, 48 + 4 * 24 + 3)) == fill
    assert preview.getpixel((48 + 10 * 24, 48)) == white, "the top edge at 3x is not the white border"
    # The menu text is drawn in the font, so the preview must carry white text pixels inside the box.
    text_white = sum(
        1
        for y in range(48 + 48, 48 + 48 + 4 * 24)
        for x in range(48 + 72, 48 + 20 * 24)
        if preview.getpixel((x, y)) == white
    )
    assert text_white > 200, "the preview carries %d text pixels, too few to read" % text_white
