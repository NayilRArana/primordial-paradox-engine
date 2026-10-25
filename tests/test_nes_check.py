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
import check_ui_nes

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
    assert "616x8" in out and "77 tiles" in out and "1 colours" in out


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
    assert meta["colours"] == {"fill": "#000000", "white": "#f8f8f8", "grey": "#005800", "backdrop": "#000000"}
    # Card t_a1170172: the box used to be $02 dark blue filled with $30 and $00 borders, three entries the title's
    # ground bands do not declare. It is now the ground band's own three: $0F black field (the backdrop), $20 white
    # border and $0B dark green inner line, which are exactly what data/palettes/scene_title.json gives bands 8-14.


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
    # Card t_a1170172 moved the field from $02 dark blue (#0000bc) to $0F black and the border from $30 to $20:
    # those are the entries the title's ground bands declare, and the preview shows the box the game draws.
    fill = (0x00, 0x00, 0x00, 255)
    white = (0xf8, 0xf8, 0xf8, 255)
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


# ---------------------------------------------------------------------------------------------------------------
# The three UI windows, proved on data\ui_layouts.json and the 3x previews rather than on a promise.
# Card t_852f3689: the audit's three reds were the window json and the preview tests above, which card
# t_a1170172 made green by repainting the window; these tests are the part that did not exist, so a window
# could drift off the 8x8 grid or a committed report could describe an older frame and nothing would say so.

UI_SCREENS = ("battle", "dialogue", "menu")


def ui_copies(tmp_path):
    """A throwaway root holding only the files the UI gate reads, so a test can break a copy."""
    import shutil

    for relative in ("data/ui_layouts.json", "data/nes_palette.json"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.join(ROOT, *relative.split("/")), target)
    for screen in UI_SCREENS:
        for relative in ("game/sprites_src/ui/screens/ui_%s.png" % screen,
                         "game/sprites_src/ui/screens/ui_%s_sprites.json" % screen,
                         "output/ui_%s_preview.png" % screen,
                         "output/ui_%s_nes_report.json" % screen):
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(os.path.join(ROOT, *relative.split("/")), target)
    return str(tmp_path)


def run_ui_gate(root, *extra):
    import io
    from contextlib import redirect_stdout

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = check_ui_nes.main(["--root", root] + list(extra))
    return code, buffer.getvalue()


def test_the_three_ui_screens_pass_the_ui_gate_on_the_real_files():
    """data\\ui_layouts.json rectangles on whole 8x8 tiles, the previews are the frames, the reports agree."""
    code, out = run_ui_gate(ROOT)
    assert code == 0, out
    for screen in UI_SCREENS:
        assert "%s: " % screen in out, out
    assert "0 attribute area violations" in out, out


def test_every_ui_window_is_whole_tiles_and_holds_its_own_border():
    with open(os.path.join(ROOT, "data", "ui_layouts.json"), "r", encoding="utf-8-sig") as handle:
        layouts = json.load(handle)
    assert layouts["kind"] == "ui_layouts"
    assert layouts["frame"] == {"w": 256, "h": 240, "tile": 8, "cols": 32, "rows": 30}
    assert [screen["name"] for screen in layouts["screens"]] == list(UI_SCREENS)
    for screen in layouts["screens"]:
        for window in screen["windows"]:
            assert check_ui_nes.tile_rect(window, window["name"]) == [], window
            # One tile border on every side, so the interior is (w-2) x (h-2) whole tiles and text starts at x+1.
            assert window["w"] >= 3 and window["h"] >= 3, window
            assert window["x"] + window["w"] <= 32 and window["y"] + window["h"] <= 30, window
        for sprite in screen["sprites"]:
            assert check_ui_nes.px_rect(sprite, sprite.get("role", "")) == [], sprite


def test_each_ui_preview_is_its_frame_at_three_times():
    with open(os.path.join(ROOT, "data", "ui_layouts.json"), "r", encoding="utf-8-sig") as handle:
        layouts = json.load(handle)
    for screen in layouts["screens"]:
        frame = os.path.join(ROOT, screen["frame_png"].replace("/", os.sep))
        preview = os.path.join(ROOT, screen["preview_png"].replace("/", os.sep))
        assert screen["preview_scale"] == 3, screen["name"]
        assert check_ui_nes.preview_is_the_frame(frame, preview) == [], (
            "%s: the 3x preview is not the frame it claims to show" % screen["name"])
        with Image.open(preview) as img:
            assert img.size == (768, 720), (screen["name"], img.size)


def test_each_ui_report_states_zero_area_violations_and_sixteen_colours_at_most():
    """The three lines this card quotes come from here: 0 attribute area violations, 16 colours or fewer."""
    lines = []
    for screen in UI_SCREENS:
        path = os.path.join(ROOT, "output", "ui_%s_nes_report.json" % screen)
        with open(path, "r", encoding="utf-8") as handle:
            report = json.load(handle)
        background = report["background"]
        assert report["ok"] is True, (screen, report["problems"])
        assert background["problems"] == [], (screen, background["problems"])
        assert background["offending_blocks"] == [], (screen, background["offending_blocks"])
        assert background["blocks"] == 240, (screen, background["blocks"])
        assert report["screen"]["problems"] == [], (screen, report["screen"]["problems"])
        assert report["screen"]["colours"] <= 16, (screen, report["screen"]["colours"])
        assert background["distinct_colour_sets"] <= 16, (screen, background["distinct_colour_sets"])
        assert report["backdrop"] == "#000000", (screen, report["backdrop"])
        lines.append("%s: 0 attribute area violations, %d colours on screen, %d colour sets, %d palettes"
                     % (screen, report["screen"]["colours"], background["distinct_colour_sets"],
                        background["palette_count"]))
    assert len(lines) == 3


def test_the_ui_gate_refuses_a_report_that_describes_an_older_frame(tmp_path):
    """The defect this card found: reports dated 00:00 beside frames rewritten at 22:47, nothing noticing."""
    root = ui_copies(tmp_path)
    path = os.path.join(root, "output", "ui_battle_nes_report.json")
    with open(path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    report["screen"]["colours"] += 1
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    code, out = run_ui_gate(root)
    assert code == 1, out
    assert "battle: the report says" in out and "regenerate the report" in out, out


def test_the_ui_gate_refuses_a_sprite_off_the_8x8_grid(tmp_path):
    root = ui_copies(tmp_path)
    path = os.path.join(root, "data", "ui_layouts.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        layouts = json.load(handle)
    layouts["screens"][2]["sprites"][0]["x"] = 17   # menu cursor, 17 px is not a multiple of 8
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(layouts, handle, indent=2)
    code, out = run_ui_gate(root)
    assert code == 1, out
    assert "menu.sprites[0]" in out and "not a multiple of 8" in out, out
