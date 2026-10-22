"""Tests for the scene palettes (card NES-PALETTES, 2026-10-22).

Why this file exists: the palette rule was enforced by a manual step (`scene_palette.py apply`) that ran
once and was then silently undone by the next regeneration of the art, because the test suite itself runs
tools/art/title_car_v2.py and title_logo_v2.py. A rule that a rerun can erase is not a rule, so this test
asks the checker rather than trusting a comment: tools/check_scene_palettes.py measures the art on disk and
fails the suite when a scene stops fitting its declared palettes.

What is pinned, in order of how the tree fails:
  1. Both scene files exist, declare one backdrop, four background palettes of three, four sprite palettes
     of three, and every entry is a legal 2C02 entry from data/nes_palette.json.
  2. The check passes on the current art: the composed title frame, the car frame and the ship stack all
     satisfy tools/nes_composite_check.py, no 8x16 sprite group carries more than three colours, and every
     group fits one of the four sprite palettes.
  3. The budget stays honest: 25 colours on screen at most, counted the way the PPU counts them.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import check_scene_palettes  # noqa: E402
import scene_palette  # noqa: E402


def test_both_scene_files_declare_the_nes_budget():
    for name in ("title", "ship"):
        scene = scene_palette.load_scene(ROOT, name)
        assert len(scene.background) == 4, name
        assert len(scene.sprites) == 4, name
        for row in scene.background + scene.sprites:
            assert len(row) == 3, (name, row)
            for entry in row:
                assert scene.usable[entry], (name, entry)
        assert scene.usable[scene.backdrop], name
        assert scene.backdrop not in scene.bg_colours(), "%s spends the backdrop as a palette colour" % name


def test_the_art_on_disk_fits_the_scenes():
    report = {"scenes": {}, "failures": []}
    failures = check_scene_palettes.check_title(ROOT, report) + check_scene_palettes.check_ship(ROOT, report)
    assert not failures, "\n".join(failures)
    for key in ("title_frame", "title_car_frame", "ship_frame"):
        assert report[key]["exit"] == 0, (key, report[key]["report"])
    for name, asset in report["title_sprites"].items():
        assert asset["groups_over_three"] == 0, (name, asset)
        assert asset["groups_outside_a_palette"] == 0, (name, asset)
    for name, asset in report["ship_sprites"].items():
        assert asset["groups_over_three"] == 0, (name, asset)
        assert asset["groups_outside_a_palette"] == 0, (name, asset)


def test_the_scenes_stay_inside_the_colour_cap():
    for name in ("title", "ship"):
        budget = check_scene_palettes.scene_budget(scene_palette.load_scene(ROOT, name))
        assert budget["distinct_colours"] <= budget["limit"], name
        assert budget["background_colours"] <= 12, name
        assert budget["sprite_colours"] <= 12, name


def test_the_check_reports_its_numbers_so_a_reviewer_can_read_them():
    """The card asks for the palette sets and the check output, so the report carries both as data."""
    path = os.path.join(ROOT, "output", "scene_palettes.json")
    code = check_scene_palettes.main(["--json", path, "--quiet"])
    assert code == 0, code
    with open(path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["failures"] == []
    assert set(saved["scenes"]) == {"title", "ship"}
