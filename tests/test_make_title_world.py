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


def test_the_flash_table_reads_off_the_strips_and_every_twin_stays_inside_its_band():
    """The flash is a real palette swap inside the band plan, the table is measured off the strips, and every twin
    stays legal.

    Card t_a1170172 replaced the one rung up the whole 2C02 ladder with the one rung up the band palette the strip is
    drawn in. A title frame may only spend the three entries of the palette its 16 px band declares, so a flash that
    lifted $09 to a colour outside that palette would be a frame the chip cannot show.

    The lift is per band, so one source entry can lift to different targets in different strips: $00 is $28 in the
    sky's band and $20 in the cloud's. That is why this table carries `by_layer` and no longer claims a single global
    entry map, and why the pin below recomputes the pairs from the two sheets on disk instead of applying one map to
    everything. It replaced an identity (`flash == map(base)`) that a per band lift cannot satisfy, which is what made
    the old pin red while the art was correct.
    """
    table = _flash_table()
    assert table["frames"] == 2
    chip_colours, rgb_to_entry = nes_bg.load_chip_palette(ROOT)
    mapping = {int(key): value for key, value in table["palette"].items()}
    assert mapping, "the flash palette summary is empty"
    by_layer = {name: {int(source): target for source, target in pairs.items()}
                for name, pairs in table["by_layer"].items()}
    scene = json.loads(open(os.path.join(ROOT, "data", "palettes", "scene_title.json"), "r",
                            encoding="utf-8-sig").read())
    declared = {int(entry) for row in scene["background"] for entry in row["colours"]}
    # Card t_a1170172: the flash pairs are read off every strip the title draws, and the logo and the car are sprites,
    # so their entries come from the scene's sprite palettes rather than the background bands.
    declared |= {int(entry) for row in scene.get("sprites", []) for entry in row.get("colours", [])}
    for source, target in mapping.items():
        assert target < len(chip_colours), f"${source:02X} lifts to ${target:02X}, outside the 2C02 palette"

    held = set()
    moved_somewhere = False
    for flash_name in table["layers"]:
        assert flash_name.endswith("_flash"), f"{flash_name} is not a flash strip"
        name = flash_name[:-len("_flash")]
        assert flash_name in by_layer, f"{flash_name} is not in the table's by_layer map"
        frames, _meta = _frames(name)
        flash, _meta = _frames(flash_name)
        assert len(frames) == len(flash)
        seen = set()
        flash_seen = set()
        measured = {}
        for index, (base_frame, twin_frame) in enumerate(zip(frames, flash)):
            base_px = base_frame.load()
            twin_px = twin_frame.load()
            for y in range(base_frame.height):
                for x in range(base_frame.width):
                    r, g, b, a = base_px[x, y]
                    if a:
                        seen.add(rgb_to_entry.get((r, g, b), -1))
                    fr, fg, fb, fa = twin_px[x, y]
                    if fa:
                        flash_seen.add(rgb_to_entry.get((fr, fg, fb), -1))
                    if not a:
                        continue
                    source = rgb_to_entry.get((r, g, b), -1)
                    target = rgb_to_entry.get((fr, fg, fb), -1) if fa else -1
                    assert source != -1 and target != -1, f"{name} has a pixel that is not a 2C02 entry"
                    # $0F the backdrop is never swapped and is never a palette entry of its own.
                    if source == 15:
                        continue
                    measured.setdefault(source, set()).add(target)
        assert -1 not in seen and -1 not in flash_seen, f"{name} has a pixel that is not a 2C02 entry"
        assert flash_seen - {15} <= declared, \
            f"{name}_flash draws {sorted(flash_seen)}, and no band of the title declares all of them"
        drawn = set()
        for source, targets in measured.items():
            listed = by_layer[flash_name].get(source)
            assert listed is not None, f"{name}: the table has no entry for ${source:02X}"
            assert targets <= set(listed), \
                f"{name}: ${source:02X} lifts to {sorted(targets)} on disk, the table lists {listed}"
            drawn |= targets
            if targets - {source}:
                moved_somewhere = True
        # Every target the table lists is a colour the twin really draws, and every source it names is drawn.
        for source, listed in by_layer[flash_name].items():
            assert set(listed) <= drawn, \
                f"{name}: the table lists ${sorted(set(listed) - drawn)} that the twin never draws"
        assert set(by_layer[flash_name]) <= seen, "the table names entries the strip never draws"
        held |= seen
    assert moved_somewhere, "the flash swaps nothing, so it is not a flash"
    assert set(mapping) & held, "the flash palette names no entry a layer draws"


@pytest.mark.parametrize("name,size", [("ts2_world_preview.png", (768, 720)),
                                       ("ts2_bigben_preview.png", (768, 720))])
def test_the_3x_previews_exist_at_three_times_the_screen(name, size):
    path = os.path.join(OUT, name)
    assert os.path.isfile(path), f"{name} is the picture the manager reviews; it is missing"
    with Image.open(path) as image:
        assert image.size == size
