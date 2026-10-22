"""Tests for tools/palette_synergy.py (card PAL-SYSTEM, 2026-10-22).

The rules in ART-BIBLE RULE 0 point 2 are arithmetic on the 2C02 grid, so every case here is a picture whose
verdict is decided before the tool runs: a body two rows from the ground passes and one row fails, white on
white fails, a colour outside the scene's set fails, a four colour tile fails. The last test runs the tool on
the frames that ship today, which is the answer the card actually asked for.
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


def analyse(tmp_path, background_pixels, sprite_pixels, size=(16, 16), background=None):
    background = write_png(tmp_path / "bg.png", background_pixels, size=(256, 240),
                           background=background or BLACK)
    sprite = write_png(tmp_path / "spr.png", sprite_pixels, size=size)
    return palette_synergy.analyse(ROOT, BASE["scene"], background, [sprite])


def test_selftest_passes():
    assert palette_synergy.selftest(ROOT) == 0


def test_a_body_two_rows_off_the_ground_passes_body_ground(tmp_path):
    # $20 is row 2 (#f8f8f8); the backdrop $0F is row 0, so the gap is 2 and RULE 0 point 2 is met.
    body = COLOURS[0x20]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
    assert "body_ground" not in rules_of(result), result["problems"]
    assert "white_blob" not in rules_of(result), result["problems"]


def test_a_body_one_row_off_the_ground_fails_body_ground(tmp_path):
    # $10 is row 1 (#bcbcbc) on the row 0 backdrop: one row apart, and the rule asks for two.
    body = COLOURS[0x10]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
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


def test_cli_writes_a_json_report_and_sets_the_exit_code(tmp_path):
    sprite = write_png(tmp_path / "spr.png", {(x, y): COLOURS[0x10] for x in range(16) for y in range(16)})
    background = write_png(tmp_path / "bg.png", {}, size=(256, 240), background=BLACK)
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
