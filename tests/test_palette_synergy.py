"""Tests for tools/palette_synergy.py (card PAL-SYSTEM, 2026-10-22).

The rules in ART-BIBLE RULE 0 point 2 are arithmetic on the 2C02 grid, so every case here is a picture whose
verdict is decided before the tool runs: a body two rows from the ground passes, a body one row away passes only
when it clears 3:1 contrast as well, white on white fails, a colour outside the scene's set fails, a four colour
tile fails. The last test runs the tool on the frames that ship today, which is the answer the card actually
asked for.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import palette_synergy  # noqa: E402
import scene_palette_set  # noqa: E402

COLOURS, USABLE, _ = scene_palette_set.load_master(ROOT)
BLACK = COLOURS[15]


def write_png(path, pixels, size=(16, 16), background=None):
    image = Image.new("RGBA", size, (background or (0, 0, 0, 0)))
    for (x, y), rgb in pixels.items():
        image.putpixel((x, y), tuple(rgb) + (255,) if len(rgb) == 3 else tuple(rgb))
    image.save(path)
    return path


def rules_of(result):
    return {problem["rule"] for problem in result["problems"]}


BASE = {"scene": "title"}


def analyse(tmp_path, background_pixels, sprite_pixels, size=(16, 16), background=None, sidecar=None):
    background = write_png(tmp_path / "bg.png", background_pixels, size=(256, 240),
                           background=background or BLACK)
    sprite = write_png(tmp_path / "spr.png", sprite_pixels, size=size)
    if sidecar is not None:
        (tmp_path / "spr.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return palette_synergy.analyse(ROOT, BASE["scene"], background, [sprite])


def test_selftest_passes():
    assert palette_synergy.selftest(ROOT) == 0


def test_a_body_two_rows_off_the_ground_passes_body_ground(tmp_path):
    # $20 is row 2 (#f8f8f8); the backdrop $0F is row 0, so the gap is 2 and RULE 0 point 2 is met.
    body = COLOURS[0x20]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
    assert "body_ground" not in rules_of(result), result["problems"]
    assert "white_blob" not in rules_of(result), result["problems"]


def test_a_body_one_row_off_a_black_ground_passes_on_contrast(tmp_path):
    # $10 is row 1 (#bcbcbc, luminance 0.503) on the row 0 backdrop $0F (0.000): one row apart, 11.06:1.
    # The row is a coarse band, not a luminance, so R1 asks separation two ways and either clears it
    # (gamedev ruling, card t_50193088: this is sailor_battle.png frame 2 on battle_deck_night).
    body = COLOURS[0x10]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
    assert "body_ground" not in rules_of(result), result["problems"]
    assert result["exit_code"] == 0


def test_a_body_one_row_off_a_same_luminance_ground_fails_body_ground(tmp_path):
    # $00 is row 0 (#7c7c7c, 0.202) on $11 row 1 (#4478bc, 0.202): one row apart at 1.00:1, so BOTH
    # instruments are short and the pair is refused. This is the check that keeps the second instrument
    # from becoming a rubber stamp.
    result = analyse(tmp_path, {}, {(x, y): COLOURS[0x00] for x in range(16) for y in range(16)},
                     background=COLOURS[0x11])
    body_ground = [problem for problem in result["problems"] if problem["rule"] == "body_ground"]
    assert body_ground, result["problems"]
    assert body_ground[0]["rows"] == 1
    assert result["exit_code"] == 1


def test_white_on_a_light_ground_fails_white_blob(tmp_path):
    body = COLOURS[0x30]
    result = analyse(tmp_path, {(x, y): body for x in range(256) for y in range(240)}, {(x, y): body for x in range(16) for y in range(16)})
    assert "white_blob" in rules_of(result), result["problems"]


def test_a_colour_outside_the_scene_set_fails_set_member(tmp_path):
    # #ff00ff is not a 2C02 colour at all.
    result = analyse(tmp_path, {}, {(x, y): (255, 0, 255) for x in range(16) for y in range(16)})
    assert "set_member" in rules_of(result), result["problems"]


def test_four_colours_in_one_frame_fails_sprite_tile(tmp_path):
    entries = [0x20, 0x30, 0x28, 0x16]
    pixels = {}
    for index, entry in enumerate(entries):
        for x in range(index * 4, index * 4 + 4):
            for y in range(16):
                pixels[(x, y)] = COLOURS[entry]
    result = analyse(tmp_path, {}, pixels)
    assert "sprite_tile" in rules_of(result), result["problems"]
    assert "palette_count" in rules_of(result), result["problems"]


def test_the_pair_table_covers_every_sprite_palette(tmp_path):
    result = analyse(tmp_path, {}, {(x, y): COLOURS[0x20] for x in range(16) for y in range(16)})
    frame = result["sprites"][0]["frames"][0]
    assert [pair["sprite_palette"] for pair in frame["pairs"]] == [0, 1, 2, 3]
    for pair in frame["pairs"]:
        assert set(pair) >= {"sprite_palette", "body", "ground", "rows_apart", "contrast", "ok", "fails"}


def test_a_24x32_battle_figure_is_judged_as_a_figure(tmp_path):
    """Card t_c498add9: a 24x32 or 32x32 battle figure is a FIGURE, not a tiled layer.

    The same pixels are judged twice below, once undeclared and once declared a layer. Stone $00 on the $02 night
    is row 0 on row 0 at 2.91:1, so both of R1's instruments are short and it refuses; as a layer it would be
    refused by R1b instead (body 2.91:1, ink 1.73:1 against the same ground). So the rule NAME the tool reports is
    the whole proof of which branch it took.
    """
    pixels = {}
    for y in range(32):
        for x in range(24):
            pixels[(x, y)] = COLOURS[0x00] if (x + y) % 3 else COLOURS[0x0F]
    result = analyse(tmp_path, {}, pixels, size=(24, 32), background=COLOURS[0x02])
    sprite = result["sprites"][0]
    assert sprite["frame"] == [24, 32], sprite["frame"]
    assert sprite["figure"] is True and sprite["declared_layer"] is False, sprite
    assert sprite["frames"][0]["layer"] is False
    assert "body_ground" in rules_of(result), result["problems"]
    assert "overlay_contrast" not in rules_of(result), result["problems"]


def test_a_sheet_that_declares_itself_a_layer_is_judged_as_a_layer(tmp_path):
    """The declaration outranks the size: the same 24x32 pixels with "layer": true get R1b, not R1."""
    pixels = {}
    for y in range(32):
        for x in range(24):
            pixels[(x, y)] = COLOURS[0x00] if (x + y) % 3 else COLOURS[0x0F]
    result = analyse(tmp_path, {}, pixels, size=(24, 32), background=COLOURS[0x02],
                     sidecar={"frame_w": 24, "frame_h": 32, "frames": 1, "layer": True})
    sprite = result["sprites"][0]
    assert sprite["declared_layer"] is True and sprite["figure"] is False, sprite
    assert sprite["frames"][0]["layer"] is True
    assert "body_ground" not in rules_of(result), result["problems"]
    assert "overlay_contrast" in rules_of(result), result["problems"]


def test_r6_for_a_multi_tile_figure_is_asked_per_8x8_tile(tmp_path):
    """Every 8x8 tile of a figure must fit one sprite palette of the scene, and an uncovered tile is named."""
    pixels = {}
    for top in range(0, 32, 8):
        for left in range(0, 24, 8):
            pair = (0x0F, 0x0C) if (left, top) == (16, 8) else (0x0F, 0x00)
            for y in range(top, top + 8):
                for x in range(left, left + 8):
                    pixels[(x, y)] = COLOURS[pair[(x + y) % 2]]
    result = analyse(tmp_path, {}, pixels, size=(24, 32),
                     sidecar={"frame_w": 24, "frame_h": 32, "frames": 1})
    sprite = result["sprites"][0]
    assert sprite["tiles"] == {"inked": 12, "uncovered": 1}, sprite["tiles"]
    palette_count = [problem for problem in result["problems"] if problem["rule"] == "palette_count"]
    assert len(palette_count) == 1, palette_count
    assert palette_count[0]["tile"] == [16, 8], palette_count[0]
    assert palette_count[0]["colours"] == "$0C $0F", palette_count[0]
    assert "set_member" not in rules_of(result), result["problems"]


def test_the_shipped_battle_sheet_is_seven_declared_24x32_frames():
    """The real sheet: 168x32 is seven frames of 24x32 as its own sidecar declares, and the ship set carries it.

    Card t_dc6305d6: the background is a capture, and it is a tracked input. `output/` is ignored at
    `.gitignore` line 28, but nine captures under it are committed on purpose because tests read them by path,
    and this one is now the tenth: it is listed in `tools/check_test_inputs.py` FIXTURES so a HEAD worktree
    cannot lack it. Before that it existed only on the machine that ran the capture, and the red it raised read
    as an art failure instead of a missing file.
    """
    background = os.path.join(ROOT, "output", "ship_dialogue.png")
    assert os.path.isfile(background), (
        "%s is a tracked fixture and must be in the checkout; if it is gone, the commit that removed it is "
        "the defect, not this test" % background)
    result = palette_synergy.analyse(ROOT, "ship", background, ["game/sprites_src/chars/sailor_battle.png"])
    sprite = result["sprites"][0]
    assert sprite["frame"] == [24, 32], sprite["frame"]
    assert len(sprite["frames"]) == 7, len(sprite["frames"])
    assert sprite["figure"] is True, sprite
    assert sprite["tiles"] == {"inked": 72, "uncovered": 0}, sprite["tiles"]


def test_cli_writes_a_json_report_and_sets_the_exit_code(tmp_path):
    # $00 grey on the $11 ground at the same luminance: one row apart at 1.00:1, refused by both instruments.
    sprite = write_png(tmp_path / "spr.png", {(x, y): COLOURS[0x00] for x in range(16) for y in range(16)})
    background = write_png(tmp_path / "bg.png", {}, size=(256, 240), background=COLOURS[0x11])
    out = tmp_path / "report.json"
    code = palette_synergy.main(["--scene", "title", "--background", str(background),
                                 "--sprite", str(sprite), "--json", str(out), "--quiet"])
    assert code == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool"] == "palette_synergy"
    assert payload["scene"] == "title"
    assert payload["ok"] is False
    assert payload["fail_count"] >= 1


def test_cli_passes_a_clean_sprite(tmp_path):
    sprite = write_png(tmp_path / "spr.png", {(x, y): COLOURS[0x20] for x in range(16) for y in range(16)})
    background = write_png(tmp_path / "bg.png", {}, size=(256, 240), background=BLACK)
    code = palette_synergy.main(["--scene", "title", "--background", str(background),
                                 "--sprite", str(sprite), "--quiet"])
    assert code == 0


@pytest.mark.parametrize("frame", ["output/nes_title_frame.png"])
def test_the_shipped_title_frame_reports_its_pairs(frame):
    """Not an assertion that it passes: it fails today, and that failing list is what the card asked for. What is
    pinned is that the tool runs on the real frame and produces the pair table instead of crashing."""
    path = os.path.join(ROOT, frame)
    # No skip here. A skip on a missing input is how this test reported healthy while it measured
    # nothing, and tests/test_test_inputs.py exists to forbid it; the frame is committed instead.
    assert os.path.isfile(path), (
        "%s is not on disk; it is committed, so a checkout without it is a broken checkout "
        "(regenerate with tools/art/scene_palette.py)" % frame)
    result = palette_synergy.analyse(ROOT, "title", path, ["game/sprites_src/chars/percy_ow_v2.png"])
    assert result["sprites"], "no sprite was measured"
    assert result["sprites"][0]["frames"], "no frame was measured"
    assert result["fail_count"] == len(result["problems"])
    assert result["exit_code"] == (0 if result["ok"] else 1)
