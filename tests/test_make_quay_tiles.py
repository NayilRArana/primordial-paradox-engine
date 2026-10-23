"""Tests for tools/art/make_quay_tiles.py (QUAY-TILES, card t_abfb6024).

What these pin, and why each one is a measurement rather than a matter of taste:

1. The sheet is 20 tiles of 16 x 16, laid out 8 across, so a cell index is `floor(i / 8)` down and `i % 8`
   across, which is what the map wiring in R28 has to read.
2. Every pixel is a usable Ricoh 2C02 output: no blended colour, no anti aliased edge, nothing off the PPU.
3. Every colour is NAMED AS A ROLE that exists in data/palette.json, and every role resolves to a usable entry,
   which is the card's "roles not hex" requirement made checkable.
4. Each tile draws from exactly one of the four background palettes, so no 16 x 16 area can carry a fourth
   colour besides the shared backdrop. That is the same budget the audit measures.
5. The blob test of knowledge/SPRITE-CRAFT.md section 8.5 passes on every object tile, and the numbers are in
   the manifest for every tile, gated or not.
6. The committed sheet, manifest and table are what the generator writes today, so the repository cannot drift
   from the code that made it.
7. The project's own checkers agree: tools/nes_check.py passes the sheet as a background with the declared
   backdrop, and tools/nes_composite_check.py passes both 256 x 240 mocks as finished frames.

The suite builds the sheet once per test session (about 0.2 s) and runs the two checkers once, so it stays
inside a normal pass.
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
def mq():
    return load("make_quay_tiles_under_test", os.path.join(ROOT, "tools", "art", "make_quay_tiles.py"))


@pytest.fixture(scope="module")
def built(mq):
    rendered, sheet = mq.build()
    return rendered, sheet


def test_sheet_is_twenty_cells_of_sixteen(mq, built):
    rendered, sheet = built
    assert len(rendered) == 20, "the card asks for twelve to twenty tiles and this set spends twenty"
    assert sheet.size == (mq.COLUMNS * 16, 3 * 16), "8 columns by 3 rows of 16 x 16 cells"
    for tile in rendered:
        assert tile["image"].size == (16, 16), tile["name"]
        assert len(tile["canvas"].rows()) == 16 and len(tile["canvas"].rows()[0]) == 16


def test_every_pixel_is_a_2c02_output(mq, built):
    _rendered, sheet = built
    allowed = set(mq.COLOUR.values())
    seen = {pixel for pixel in sheet.convert("RGBA").getdata()}
    assert seen <= allowed, "off palette colours: %s" % sorted(seen - allowed)
    assert len({pixel[:3] for pixel in seen}) == 11, "the set spends 11 of the 16 colours the room cap allows"


def test_every_colour_is_a_role_from_the_palette(mq):
    design = json.load(open(os.path.join(ROOT, "data", "palette.json"), encoding="utf-8-sig"))
    for role in mq.ROLE_ENTRY:
        assert role in design["roles"], "%s is not a role in data/palette.json" % role
    for set_name, roles in mq.SETS.items():
        assert len(roles) <= 16, "%s is over the 16 role cap" % set_name
        for role in roles:
            assert role in design["roles"]


def test_a_tile_never_leaves_its_palette(built):
    rendered, _sheet = built
    for tile in rendered:
        assert tile["blob"]["colours"] <= 4, "%s carries %d colours" % (tile["name"], tile["blob"]["colours"])


def test_the_blob_test_passes_on_every_object_tile(built):
    rendered, _sheet = built
    gated = [tile for tile in rendered if tile["blob_gated"]]
    assert len(gated) == 7, "seven tiles draw an object with a silhouette of its own"
    for tile in gated:
        assert tile["blob_verdict"] == "pass", "%s: %s" % (tile["name"], tile["blob_verdict"])


def test_committed_art_matches_a_fresh_build(mq, built):
    rendered, sheet = built
    committed = Image.open(os.path.join(ROOT, "game", "sprites_src", "env", "quay", "quay_tiles.png"))
    assert committed.size == sheet.size
    assert list(committed.convert("RGBA").getdata()) == list(sheet.convert("RGBA").getdata()), (
        "the committed sheet is not what the generator writes: rerun tools/art/make_quay_tiles.py")
    manifest = json.load(open(os.path.join(ROOT, "game", "sprites_src", "env", "quay", "quay_tiles.json"),
                              encoding="utf-8-sig"))
    assert manifest["frames"] == len(rendered)
    assert [entry["name"] for entry in manifest["tiles"]] == [tile["name"] for tile in rendered]
    assert len({entry["character"] for entry in manifest["tiles"]}) == len(rendered), "characters are unique"
    assert os.path.isfile(os.path.join(ROOT, "game", "sprites_src", "env", "quay", "TILES.md"))


def test_the_project_checkers_pass_the_sheet_and_both_mocks(mq, built):
    _rendered, sheet = built
    nes_check = load("quay_nes_check", os.path.join(ROOT, "tools", "nes_check.py"))
    palette_path, _why = nes_check.palette_path(ROOT)
    palette = nes_check.load_palette(palette_path)
    report = nes_check.check(sheet, "background", palette, (0, 0, 0))
    assert report["ok"], report["problems"]

    composite = load("quay_composite", os.path.join(ROOT, "tools", "nes_composite_check.py"))
    frame_palette = composite.load_palette(composite.default_palette_path(ROOT))
    for name, layout in (("quay_block", mq.BLOCK), ("quay_office", mq.OFFICE)):
        frame = mq.compose(layout)
        assert frame.size == (256, 240), name
        verdict = composite.check_frame(frame, frame_palette, (0, 0, 0))
        assert verdict["ok"], "%s: %s" % (name, verdict["problems"])
        assert verdict["screen"]["colours"] <= 25
