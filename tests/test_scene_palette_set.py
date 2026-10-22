"""Tests for tools/scene_palette_set.py (card PAL-SYSTEM, 2026-10-22).

Why this file exists: ART-BIBLE RULE 0 makes a scene's palette set an input to the art, not a report on it.
That only holds if the file is real, complete for every scene, and derived from the per scene files that the
art lane already solved. The strongest test here is the regeneration test: `build()` must reproduce the file
that is on disk byte for byte, so a hand edit that drifts from the measured art fails the suite.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import scene_palette_set  # noqa: E402


def data():
    return scene_palette_set.load(ROOT)


def test_file_is_there_and_is_the_right_kind():
    payload = data()
    assert payload["kind"] == "scene_palettes"
    assert payload["format"] == 1
    assert payload["master"] == "data/nes_palette.json"


def test_every_scene_file_the_art_lane_solved_is_in_the_set():
    listed = set(scene_palette_set.scene_ids(data()))
    on_disk = {os.path.basename(path)[len("scene_"):-len(".json")]
               for path in scene_palette_set.source_files(ROOT)}
    assert on_disk <= listed, "a scene file on disk is not in the palette set"
    assert len(listed) == len(on_disk)


def test_every_scene_is_one_backdrop_four_plus_four_of_three():
    colours, usable, _ = scene_palette_set.load_master(ROOT)
    for entry in data()["scenes"]:
        assert usable[entry["backdrop"]], entry["id"]
        assert 0 <= entry["backdrop"] < len(colours)
        for key in ("background", "sprites"):
            rows = entry[key]
            assert len(rows) == 4, "%s has %d %s palettes" % (entry["id"], len(rows), key)
            for row in rows:
                assert len(row["colours"]) == 3, (entry["id"], key, row)
                assert len(set(row["colours"])) == 3, (entry["id"], key, row)
                for value in row["colours"]:
                    assert usable[value], "%s uses forbidden entry $%02X" % (entry["id"], value)


def test_the_four_hero_palettes_are_fixed_and_dark_to_light():
    payload = data()
    assert sorted(payload["hero_palettes"]) == sorted(scene_palette_set.HEROES)
    for name, palette in payload["hero_palettes"].items():
        entries = palette["colours"]
        assert palette["fixed"] is True, name
        assert len(entries) == 3 and len(set(entries)) == 3, name
        rows = [scene_palette_set.row_of(value) for value in entries]
        assert rows == sorted(rows), "%s is not outline, body, accent: %s" % (name, rows)
    # RULE 0 point 3 names the colours in words; the entries are what the tools read.
    assert payload["hero_palettes"]["percy"]["colours"] == [15, 18, 40]
    assert payload["hero_palettes"]["hadrian"]["colours"] == [15, 3, 35]
    assert payload["hero_palettes"]["zander"]["colours"] == [15, 33, 49]
    assert payload["hero_palettes"]["konrad"]["colours"] == [15, 0, 39]


def test_a_scene_can_be_loaded_as_the_art_lanes_own_scene_object():
    scene = scene_palette_set.scene(ROOT, "title")
    assert scene.name == "title"
    assert len(scene.background) == 4 and len(scene.sprites) == 4
    assert len(scene.bg_sets()[0]) == 4  # three entries plus the shared backdrop
    assert scene.rgb(scene.backdrop) == (0, 0, 0)


def test_every_entry_of_the_set_is_a_usable_master_entry():
    payload = data()
    entries = scene_palette_set.scene_entries(payload, "title")
    _, usable, _ = scene_palette_set.load_master(ROOT)
    assert entries, "title has no entries"
    for entry in entries:
        assert usable[entry], "$%02X is not usable" % entry


def test_validate_passes_on_the_shipped_file():
    assert scene_palette_set.validate(ROOT) == []


def test_validate_catches_a_broken_scene():
    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["background"] = payload["scenes"][0]["background"][:3]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("background palettes" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["hero_palettes"]["percy"]["colours"] = [15, 18]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("percy" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["backdrop"] = 13  # $0D, the entry the art bible forbids
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("forbidden" in problem for problem in problems), problems


def test_build_reproduces_the_file_on_disk():
    """The file must be derived, not hand written: a regeneration either changes nothing or the art changed."""
    rebuilt = json.loads(json.dumps(scene_palette_set.build(ROOT)))
    shipped = data()
    assert rebuilt["scenes"] == shipped["scenes"]
    assert rebuilt["hero_palettes"] == shipped["hero_palettes"]
    assert rebuilt["rule"] == shipped["rule"]


def test_cli_validate_and_list(capsys):
    assert scene_palette_set.main(["validate"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert scene_palette_set.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "title" in out and "ship" in out


def test_cli_show_names_the_palettes(capsys):
    assert scene_palette_set.main(["show", "--scene", "title"]) == 0
    out = capsys.readouterr().out
    assert "$0F" in out and "percy" in out
