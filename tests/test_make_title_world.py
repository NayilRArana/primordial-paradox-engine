"""TS2-ART-B: the measured checks on the v2 night title art.

The card asks for three things that a person cannot eyeball in a diff: every layer holds the NES
background rule, every strip's wrap edge is no worse than its own interior, and the two 3x previews
exist at the size the manager reviews. These tests pin those three so a later redraw cannot quietly
drop one.

The files themselves are written by tools\\art\\make_title_world.py; this suite does not run the
generator (it is deterministic, so the committed art is the measurement). The checker used here is
tools\\art\\nes_bg.py, which counts colours per 16x16 area and never looks at how the drawing was made.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools", "art"))

import nes_bg  # noqa: E402
import nes_snap  # noqa: E402
import make_title_world  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES = os.path.join(ROOT, "game", "sprites_src", "title")
OUT = os.path.join(ROOT, "output")


def _table():
    with open(os.path.join(ROOT, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _flash_table():
    with open(os.path.join(ROOT, "data", "title_flash.json"), "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _frames(name):
    """Every frame of one strip, as RGBA images, with its sidecar."""
    with open(os.path.join(SPRITES, name + ".json"), "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    sheet = Image.open(os.path.join(SPRITES, name + ".png")).convert("RGBA")
    count = sheet.width // meta["frame_w"]
    return [sheet.crop((i * meta["frame_w"], 0, (i + 1) * meta["frame_w"], meta["frame_h"]))
            for i in range(count)], meta


def test_the_table_names_the_seven_drive_layers_and_the_one_still_background():
    table = _table()
    names = [row["name"] for row in table["layers"]]
    assert names == ["title_L1_sky", "title_L2_clouds", "title_L3_downs", "title_L4_fields",
                     "title_L5_verge", "title_L6_road", "title_L7_fg"]
    assert [row["name"] for row in table["backgrounds"]] == ["title_BG_bigben"]
    assert table["opening"]["name"] not in names, \
        "the opening shot must not also be a scrolling layer, or the screen draws it over the drive"


def test_every_layer_holds_the_nes_background_rule():
    """The checker, not the solver: 3 colours plus the shared backdrop in every 16x16 area."""
    assert nes_bg.check(ROOT) == 0


@pytest.mark.parametrize("name", ["title_L1_sky", "title_L2_clouds", "title_L3_downs",
                                  "title_L4_fields", "title_L5_verge", "title_L6_road",
                                  "title_L7_fg", "title_BG_bigben"])
def test_each_layer_is_the_size_the_generator_declares(name):
    """The strip on disk must be the size the layer table promises, or the runtime cuts it wrong."""
    declared = next(spec for spec in make_title_world.LAYERS if spec["name"] == name)
    frames, meta = _frames(name)
    assert (meta["frame_w"], meta["frame_h"]) == (declared["width"], declared["height"])
    assert len(frames) == declared["frames"], "the frame count changed without the table knowing"
    # A scrolling layer has to be wider than the view, or the wrap would show the same pixels twice.
    if name != make_title_world.OPENING_NAME:
        assert meta["frame_w"] == 512 > 256


@pytest.mark.parametrize("name", ["title_L1_sky", "title_L2_clouds", "title_L3_downs",
                                  "title_L4_fields", "title_L5_verge", "title_L6_road",
                                  "title_L7_fg"])
def test_every_drive_layer_wraps_without_a_sharper_seam(name):
    """The wrap edge must be no sharper than the sharpest step the strip already contains."""
    frames, _meta = _frames(name)
    wrap_max, interior_max = make_title_world.seam_metric(frames[0])
    assert wrap_max <= interior_max, f"{name}: wrap step {wrap_max} sharper than interior {interior_max}"


def test_the_big_ben_opening_shot_is_one_screen():
    frames, meta = _frames("title_BG_bigben")
    assert len(frames) == 1
    assert (meta["frame_w"], meta["frame_h"]) == (256, 240)


def test_the_sign_carries_the_four_countdowns():
    frames, meta = _frames("spr_title_sign")
    assert len(frames) == 4, "the sign needs one frame per countdown"
    # Each sign is fixed; the Southampton line falls as the drive goes on: 55, 43, 30, 20 miles (real OSRM route, 84.7 mi).
    assert [bottom[1] for _top, bottom in make_title_world.SIGN_TEXTS] == ["55", "43", "30", "20"]
    assert all(bottom[0] == "SOUTHAMPTON" for _top, bottom in make_title_world.SIGN_TEXTS)
    # Four different pictures: if two frames were identical the countdown would not read.
    assert len({frame.tobytes() for frame in frames}) == 4


def test_the_flash_palette_lifts_every_colour_one_rung_and_keeps_the_two_frame_data():
    """The flash is a real palette swap: each colour the night strips use moves one rung up the 2C02's own
    ladder (nes_snap.flash_step), the flash strips on disk draw exactly those lifted entries, and no strip
    carries a pixel the chip cannot show."""
    table = _flash_table()
    assert table["frames"] == 2
    # The same 2C02 lookup the checker uses: black repeats in the master palette and only $0F is drawable,
    # so a naive rgb-to-entry table would file it under $3F and invent a colour the flash never lifts.
    chip_colours, rgb_to_entry = nes_bg.load_chip_palette(ROOT)
    mapping = {int(key): value for key, value in table["palette"].items()}
    assert mapping, "the flash palette is empty"
    for source, target in mapping.items():
        assert target < len(chip_colours), f"${source:02X} lifts to ${target:02X}, outside the 2C02 palette"
        # One rung up the chip's ladder, or pinned where the ladder has no higher rung.
        assert target == nes_snap.flash_step(source), \
            f"${source:02X} -> ${target:02X} is not the one rung the flash palette promises"

    held = set()
    for flash_name in table["layers"]:
        assert flash_name.endswith("_flash"), f"{flash_name} is not a flash strip"
        name = flash_name[:-len("_flash")]
        frames, _meta = _frames(name)
        seen = set()
        for frame in frames:
            pixels = frame.load()
            for y in range(frame.height):
                for x in range(frame.width):
                    r, g, b, a = pixels[x, y]
                    if a:
                        seen.add(rgb_to_entry.get((r, g, b), -1))
        assert -1 not in seen, f"{name} has a pixel that is not a 2C02 entry"
        # Every colour the night frame draws is in the flash table, so the swap cannot leave a pixel behind.
        assert seen <= set(mapping), f"{name} draws {sorted(seen)} outside the flash palette"
        held |= seen
        flash, _meta = _frames(flash_name)
        flash_seen = set()
        for frame in flash:
            pixels = frame.load()
            for y in range(frame.height):
                for x in range(frame.width):
                    r, g, b, a = pixels[x, y]
                    if a:
                        flash_seen.add(rgb_to_entry.get((r, g, b), -1))
        assert flash_seen == {mapping[index] for index in seen}, \
            f"{name}_flash draws {sorted(flash_seen)}, not the lifted night entries"
    # The table is not padded: it names exactly the colours the night scene uses.
    assert set(mapping) == held, f"the flash palette names {sorted(set(mapping) - held)} that no layer draws"


@pytest.mark.parametrize("name,size", [("ts2_world_preview.png", (768, 720)),
                                       ("ts2_bigben_preview.png", (768, 720))])
def test_the_3x_previews_exist_at_three_times_the_screen(name, size):
    path = os.path.join(OUT, name)
    assert os.path.isfile(path), f"{name} is the picture the manager reviews; it is missing"
    with Image.open(path) as image:
        assert image.size == size
