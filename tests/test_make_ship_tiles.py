"""Tests for tools/art/make_ship_tiles.py (SHIP-TILES, card t_a0c1bccf).

What these pin, and why each one is a measurement rather than a matter of taste:

1. The sheet is 24 tiles of 16 x 16 laid out 8 across, so a cell index is `floor(i / 8)` down and `i % 8`
   across, which is what the map wiring has to read.
2. Every pixel is a usable Ricoh 2C02 output, and the whole set spends 10 of the 16 colours the card allows.
3. Every colour is the entry the ship's own background strip uses (tools/art/make_env_ship.py PALETTE), so the
   deck tiles and the battle strip behind them cannot drift apart.
4. Each tile draws from exactly one of the four background palettes, so no 16 x 16 area carries a fourth colour
   besides the shared backdrop. That is the budget tools/nes_check.py measures.
5. The card's six families are all in the sheet, and the hatch and the rail are marked in the class file by
   name, with the hatch's story flag.
6. The committed sheet, manifest, table and class file are what the generator writes today, so the repository
   cannot drift from the code that made it.
7. The project's own checker agrees: tools/nes_check.py passes the sheet as a background with the declared
   backdrop, which is the card's "the NES tile check passes".

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
def ms():
    return load("make_ship_tiles_under_test", os.path.join(ROOT, "tools", "art", "make_ship_tiles.py"))


@pytest.fixture(scope="module")
def built(ms):
    rendered, sheet = ms.build()
    return rendered, sheet


def test_sheet_is_twenty_four_cells_of_sixteen(ms, built):
    rendered, sheet = built
    assert len(rendered) == 24, "the card's six families plus the fittings they need"
    assert sheet.size == (ms.COLUMNS * 16, 3 * 16), "8 columns by 3 rows of 16 x 16 cells"
    for tile in rendered:
        assert tile["image"].size == (16, 16), tile["name"]


def test_every_pixel_is_a_2c02_output(ms, built):
    _rendered, sheet = built
    allowed = set(ms.COLOUR.values())
    seen = set(sheet.convert("RGBA").getdata())
    assert seen <= allowed, "off palette colours: %s" % sorted(seen - allowed)
    assert len({pixel[:3] for pixel in seen}) == 10, "the set spends 10 of the 16 colours the card allows"


def test_the_palette_is_the_ships_own_strip_palette(ms):
    env_ship = load("make_env_ship_under_test", os.path.join(ROOT, "tools", "art", "make_env_ship.py"))
    strip = {entry for _key, entry, _hex, _use in env_ship.PALETTE}
    deck = {entry for _key, entry, _hex, _use in ms.PALETTE}
    assert deck <= strip, "these entries are not in the ship strip's palette: %s" % sorted(deck - strip)


def test_every_colour_is_a_usable_nes_palette_entry(ms):
    nes = json.load(open(os.path.join(ROOT, "data", "nes_palette.json"), encoding="utf-8-sig"))
    entries = {entry["index"]: entry for entry in nes["entries"]}
    for key, _entry, _hex, _why in ms.PALETTE:
        entry = entries[ms.ENTRY_OF_ROLE[key]]
        assert entry["usable"], "%s resolves to %s, which the art bible flags" % (key, entry["code"])
        assert entry["hex"].lower() == "#%02x%02x%02x" % ms.COLOUR[key][:3], (
            "%s no longer resolves to the output it names" % key)


def test_a_tile_never_leaves_its_palette(ms, built):
    rendered, sheet = built
    facts, failures = ms.measure_sheet(sheet, rendered)
    assert not failures, failures
    assert facts["worst_area_colours"] <= 3, facts["worst_area_colours"]
    assert facts["size_sixteen"], "every tile must be 16 x 16"


def test_the_card_six_families_are_all_in_the_sheet(built):
    rendered, _sheet = built
    names = {tile["name"] for tile in rendered}
    families = {
        "plate steel": {"deck_plate", "deck_plate_worn"},
        "grating": {"deck_grating", "deck_grating_cross"},
        "hatch": {"hatch_closed", "hatch_open"},
        "bulkhead": {"bulkhead_rivet", "bulkhead_plain", "bulkhead_light"},
        "log terminal": {"log_terminal"},
        "water under the rail": {"water_deep", "water_swell", "water_edge"},
    }
    for family, wanted in families.items():
        assert wanted <= names, "the sheet has no tile for %s" % family


def test_committed_art_matches_a_fresh_build(ms, built):
    rendered, sheet = built
    out = os.path.join(ROOT, "assets", "tiles", "ship")
    committed = Image.open(os.path.join(out, "ship_tiles.png"))
    assert committed.size == sheet.size
    assert list(committed.convert("RGBA").getdata()) == list(sheet.convert("RGBA").getdata()), (
        "the committed sheet is not what the generator writes: rerun tools/art/make_ship_tiles.py")
    manifest = json.load(open(os.path.join(out, "ship_tiles.json"), encoding="utf-8-sig"))
    assert manifest["frames"] == len(rendered)
    assert [entry["name"] for entry in manifest["tiles"]] == [tile["name"] for tile in rendered]
    assert len({entry["character"] for entry in manifest["tiles"]}) == len(rendered), "characters are unique"
    assert manifest["animation"][0]["a"] == "water_deep"
    assert manifest["animation"][0]["b"] == "water_swell"
    assert os.path.isfile(os.path.join(out, "TILES.md"))


def test_the_class_file_marks_the_hatch_and_the_rail(ms, built):
    rendered, _sheet = built
    path = os.path.join(ROOT, "data", "tile_classes_ship.json")
    classes = json.load(open(path, encoding="utf-8-sig"))
    assert [tile["name"] for tile in classes["tiles"]] == [tile["name"] for tile in rendered]
    for entry in classes["tiles"]:
        assert isinstance(entry["walkable"], bool), entry["name"]
        assert entry["reason"], "%s has no reason for its class" % entry["name"]
    assert classes["counts"]["walkable"] + classes["counts"]["not_walkable"] == len(rendered)

    by_name = {entry["name"]: entry for entry in classes["tiles"]}
    assert by_name["hatch_closed"]["walkable"] is False, "a shut hatch is a solid"
    assert by_name["hatch_open"]["walkable"] is True, "an open hatch is the way down"
    assert by_name["hatch_open"]["climbable"] is True
    assert by_name["rail_bar"]["walkable"] is False, "the rail is the edge of the ship"
    assert by_name["rail_post"]["walkable"] is False
    for name in ("water_deep", "water_swell", "water_edge"):
        assert by_name[name]["walkable"] is False, "you cannot walk on the sea"

    marks = classes["marks"]
    assert classes["tiles"][marks["hatch"]["closed"]]["name"] == "hatch_closed"
    assert classes["tiles"][marks["hatch"]["open"]]["name"] == "hatch_open"
    assert marks["hatch"]["flag"] == "ship_door_open"
    assert classes["tiles"][marks["rail"]["post"]]["name"] == "rail_post"
    assert classes["tiles"][marks["rail"]["bar"]]["name"] == "rail_bar"
    for index in marks["rail"]["water_below"]:
        assert classes["tiles"][index]["name"].startswith("water_")


def test_the_project_checker_passes_the_sheet(built):
    _rendered, sheet = built
    nes_check = load("ship_nes_check", os.path.join(ROOT, "tools", "nes_check.py"))
    palette_path, _why = nes_check.palette_path(ROOT)
    palette = nes_check.load_palette(palette_path)
    report = nes_check.check(sheet, "background", palette, (0, 0, 0))
    assert report["ok"], report["problems"]
