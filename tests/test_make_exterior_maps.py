"""Tests for tools/art/make_exterior_maps.py (card t_dec4e92c).

Why this file exists: the generator wrote each town's scene palette file WHOLE, so a card that solved that
scene's sprite half or wrote a judged row lost both on the next run. That is the same defect card t_5802ecdb
closed on tools/art/make_battle_bg.py, and it matters here because card t_dec4e92c solved the three towns for
the party's four walking sheets and put a judged row in each of the three files.

Three behaviours, held by arithmetic rather than by eye:
  - a fresh file gets the PLACEHOLDER sprite half, and no judged key, because there is nothing to carry;
  - a file whose sprite half differs from the placeholder keeps it, verbatim;
  - a file with a judged row keeps the row, verbatim, whatever this generator thinks of it.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import make_exterior_maps  # noqa: E402

PLACE = {
    "id": "southampton_sample",
    "osm": "southampton_town_quay",
    "name": "Southampton, Town Quay",
    "scene": "southampton",
    "landmark": None,
    "want_water": True,
    "allowed_palettes": ["bg0_stone", "bg1_brick", "bg2_green", "bg3_water"],
    "notes": "quay stone, railings along the water, open water on two animation frames, brick sheds",
}

JUDGED = [{
    "background": "output/southampton_sample_frame.png",
    "at": [128, 112],
    "sprites": ["game/sprites_src/chars/percy_ow_v2.png"],
    "note": "a row a card wrote, which this generator has no opinion about and must not delete",
}]

SOLVED = [
    {"name": "sp0", "colours": [0, 15, 48], "hex": ["#7c7c7c", "#000000", "#fcfcfc"]},
    {"name": "sp1", "colours": [7, 23, 40], "hex": ["#881400", "#e45c10", "#f8b800"]},
    {"name": "sp2", "colours": [1, 17, 49], "hex": ["#0000fc", "#0078f8", "#a4e4fc"]},
    {"name": "sp3", "colours": [2, 18, 48], "hex": ["#0000bc", "#0058f8", "#fcfcfc"]},
]


def ts_meta():
    with open(os.path.join(ROOT, "game", "sprites_src", "env", "ts_exterior.json"),
              encoding="utf-8-sig") as handle:
        return json.load(handle)


def temp_root(tmp_path):
    """A root the writer can work in: it reads data/nes_palette.json and writes data/palettes/."""
    os.makedirs(os.path.join(tmp_path, "data", "palettes"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "nes_palette.json"), encoding="utf-8") as handle:
        master = handle.read()
    with open(os.path.join(tmp_path, "data", "nes_palette.json"), "w", encoding="utf-8") as handle:
        handle.write(master)
    return str(tmp_path)


def scene_path(root):
    return os.path.join(root, "data", "palettes", "scene_southampton.json")


def test_a_fresh_file_gets_the_placeholder_half_and_no_judged_key(tmp_path):
    root = temp_root(tmp_path)
    make_exterior_maps.write_scene_palette(root, PLACE, None, ts_meta())
    payload = json.load(open(scene_path(root), encoding="utf-8"))
    assert [row["colours"] for row in payload["sprites"]] == [[0, 15, 16], [7, 23, 40], [9, 10, 42], [2, 18, 48]]
    assert "judged" not in payload
    assert payload["scene"] == "southampton"
    assert [row["palette"] for row in payload["background"]] == PLACE["allowed_palettes"]


def test_a_solved_sprite_half_is_carried_forward(tmp_path):
    """Card t_dec4e92c: the towns' rows are the party's four walking triples, and this is why they survive."""
    root = temp_root(tmp_path)
    with open(scene_path(root), "w", encoding="utf-8") as handle:
        json.dump({"format": 1, "kind": "scene_palette", "scene": "southampton", "backdrop": 15,
                   "background": [], "sprites": SOLVED, "notes": []}, handle, indent=2)
    make_exterior_maps.write_scene_palette(root, PLACE, None, ts_meta())
    payload = json.load(open(scene_path(root), encoding="utf-8"))
    assert payload["sprites"] == SOLVED, payload["sprites"]


def test_a_judged_row_is_carried_forward_verbatim(tmp_path):
    root = temp_root(tmp_path)
    with open(scene_path(root), "w", encoding="utf-8") as handle:
        json.dump({"format": 1, "kind": "scene_palette", "scene": "southampton", "backdrop": 15,
                   "background": [], "sprites": [], "notes": [], "judged": JUDGED}, handle, indent=2)
    make_exterior_maps.write_scene_palette(root, PLACE, None, ts_meta())
    payload = json.load(open(scene_path(root), encoding="utf-8"))
    assert payload["judged"] == JUDGED, payload["judged"]


def test_the_placeholder_half_is_not_carried_because_the_generator_reproduces_it(tmp_path):
    """A half identical to the placeholder needs no carrying, so a later background change is not fought."""
    first = temp_root(tmp_path / "first")
    make_exterior_maps.write_scene_palette(first, PLACE, None, ts_meta())
    placeholder = json.load(open(scene_path(first), encoding="utf-8"))["sprites"]

    root = temp_root(tmp_path / "second")
    with open(scene_path(root), "w", encoding="utf-8") as handle:
        json.dump({"format": 1, "kind": "scene_palette", "scene": "southampton", "backdrop": 15,
                   "background": [], "sprites": placeholder, "notes": []}, handle, indent=2)
    make_exterior_maps.write_scene_palette(root, PLACE, None, ts_meta())
    payload = json.load(open(scene_path(root), encoding="utf-8"))
    assert payload["sprites"] == placeholder, "the placeholder is a copy of the background groups, so it is rebuilt"
    assert all("hex" in row for row in payload["sprites"])


def test_the_three_shipped_town_files_are_what_the_generator_writes(tmp_path):
    """The shipped files are generator output plus the rows cards wrote, not hand assembled files.

    Each shipped file is copied into a scratch root, the generator runs there, and the bytes are compared, so
    the sprite half and the judged rows have one owner and the test never writes into the repo.
    """
    meta = ts_meta()
    for index, place in enumerate(make_exterior_maps.PLACES):
        root = temp_root(tmp_path / ("place%d" % index))
        shipped = os.path.join(ROOT, "data", "palettes", "scene_%s.json" % place["scene"])
        with open(shipped, "rb") as handle:
            before = handle.read()
        with open(scene_path(root), "wb") as handle:
            handle.write(before)
        make_exterior_maps.write_scene_palette(root, place, None, meta)
        with open(scene_path(root), "rb") as handle:
            after = handle.read()
        assert after == before, ("tools/art/make_exterior_maps.py no longer reproduces scene_%s.json, so the file "
                                 "has a second owner. Lines the generator adds or drops: %s"
                                 % (place["scene"],
                                    [line for line in after.decode().splitlines()
                                     if line not in before.decode().splitlines()][:5]))
