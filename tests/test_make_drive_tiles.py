"""Tests for tools/art/make_drive_tiles.py (DRIVE-TILES, card t_d0e73725).

What these pin, and why each one is a measurement rather than a matter of taste:

1. The sheet is 24 tiles of 16 x 16 laid out 8 across, so a cell index is `floor(i / 8)` down and `i % 8`
   across, which is what the map wiring has to read.
2. Every pixel is a usable Ricoh 2C02 output, and the whole set spends 9 of the 16 colours the card allows.
3. Every colour is a ROLE in data/palette.json and resolves to the entry tools/art/nes_snap.py's NIGHT_TABLE
   names, so this set can never drift from the drive layers that use the same bridge.
4. Each tile draws from exactly one background palette, so no 16 x 16 area carries a fourth colour besides the
   shared backdrop. That is the budget tools/nes_check.py measures.
5. The blob test of knowledge/SPRITE-CRAFT.md section 8.5 passes on every gated tile, and the numbers are in
   the manifest for every tile, gated or not.
6. The committed sheet, manifest, table and class file are what the generator writes today, so the repository
   cannot drift from the code that made it. The class file classifies every tile and carries the ODbL line.
7. The project's own checker agrees: tools/nes_check.py passes the sheet as a background with the declared
   backdrop, which is the card's "the existing NES tile check passes on it".

The suite builds the sheet once per module, so it stays inside a normal pass.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def md():
    return load("make_drive_tiles_under_test", os.path.join(ROOT, "tools", "art", "make_drive_tiles.py"))


@pytest.fixture(scope="module")
def built(md):
    rendered, sheet = md.build()
    return rendered, sheet


def test_sheet_is_twenty_four_cells_of_sixteen(md, built):
    rendered, sheet = built
    assert len(rendered) == 24, "eight surface, eight roadside, eight gantry and barrier"
    assert sheet.size == (md.COLUMNS * 16, 3 * 16), "8 columns by 3 rows of 16 x 16 cells"
    for tile in rendered:
        assert tile["image"].size == (16, 16), tile["name"]
        assert len(tile["canvas"].rows()) == 16 and len(tile["canvas"].rows()[0]) == 16


def test_every_pixel_is_a_2c02_output(md, built):
    _rendered, sheet = built
    allowed = set(md.COLOUR.values())
    seen = {pixel for pixel in sheet.convert("RGBA").getdata()}
    assert seen <= allowed, "off palette colours: %s" % sorted(seen - allowed)
    assert len({pixel[:3] for pixel in seen}) == 9, "the set spends 9 of the 16 colours the card allows"


def test_every_colour_is_a_role_that_nes_snap_names(md, built):
    design = json.load(open(os.path.join(ROOT, "data", "palette.json"), encoding="utf-8-sig"))
    nes = json.load(open(os.path.join(ROOT, "data", "nes_palette.json"), encoding="utf-8-sig"))
    entries = {entry["index"]: entry for entry in nes["entries"]}
    for key, (role_name, index, _why) in md.ROLE.items():
        assert role_name in design["roles"], "%s is not a role in data/palette.json" % role_name
        assert design["roles"][role_name] == index, "%s moved in data/palette.json" % role_name
        assert md.ENTRY_OF_ROLE[key] == md.nes_snap.NIGHT_TABLE[index], (
            "%s does not resolve through nes_snap's bridge" % key)
        entry = entries[md.ENTRY_OF_ROLE[key]]
        assert entry["usable"], "%s resolves to %s, which the art bible flags" % (key, entry["code"])
        assert entry["hex"].lower() == "#%02x%02x%02x" % md.COLOUR[key][:3], (
            "%s no longer resolves to the output it names" % key)


def test_a_tile_never_leaves_its_palette(md, built):
    rendered, sheet = built
    facts, failures = md.measure_sheet(sheet, rendered)
    assert not failures, failures
    assert facts["worst_area_colours"] <= 3, facts["worst_area_colours"]


def test_the_blob_test_passes_on_every_gated_tile(built):
    rendered, _sheet = built
    gated = [tile for tile in rendered if tile["blob_gated"]]
    assert len(gated) == 4, "four tiles draw an object with a silhouette of its own"
    for tile in gated:
        assert tile["blob_verdict"] == "pass", "%s: %s" % (tile["name"], tile["blob_verdict"])


def test_committed_art_matches_a_fresh_build(built):
    rendered, sheet = built
    out = os.path.join(ROOT, "assets", "tiles", "drive")
    committed = Image.open(os.path.join(out, "drive_tiles.png"))
    assert committed.size == sheet.size
    assert list(committed.convert("RGBA").getdata()) == list(sheet.convert("RGBA").getdata()), (
        "the committed sheet is not what the generator writes: rerun tools/art/make_drive_tiles.py")
    manifest = json.load(open(os.path.join(out, "drive_tiles.json"), encoding="utf-8-sig"))
    assert manifest["frames"] == len(rendered)
    assert [entry["name"] for entry in manifest["tiles"]] == [tile["name"] for tile in rendered]
    assert len({entry["character"] for entry in manifest["tiles"]}) == len(rendered), "characters are unique"
    assert os.path.isfile(os.path.join(out, "TILES.md"))


def test_the_class_file_classifies_every_tile_and_carries_the_odbl_line(md, built):
    rendered, _sheet = built
    odbl = ("(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, "
            "https://www.openstreetmap.org/copyright")
    path = os.path.join(ROOT, "data", "tile_classes_drive.json")
    raw = open(path, encoding="utf-8").read()
    assert raw.index(odbl) < raw.index('"tiles"'), "the ODbL line belongs in the header, above the tile list"
    classes = json.loads(raw)
    assert [tile["name"] for tile in classes["tiles"]] == [tile["name"] for tile in rendered]
    for entry in classes["tiles"]:
        assert isinstance(entry["walkable"], bool), entry["name"]
        assert entry["reason"], "%s has no reason for its class" % entry["name"]
    assert classes["counts"]["walkable"] + classes["counts"]["not_walkable"] == len(rendered)


def test_the_project_checker_passes_the_sheet(md, built):
    _rendered, sheet = built
    nes_check = load("drive_nes_check", os.path.join(ROOT, "tools", "nes_check.py"))
    palette_path, _why = nes_check.palette_path(ROOT)
    palette = nes_check.load_palette(palette_path)
    report = nes_check.check(sheet, "background", palette, (0, 0, 0))
    assert report["ok"], report["problems"]
