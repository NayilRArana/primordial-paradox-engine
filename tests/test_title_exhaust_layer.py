"""Pins for the exhaust puff: a tiled layer, drawn once, in the two entries the title's road band carries.

Card t_474cde50 (gamedev). The queue row `spr_title_exhaust` could not pass as a figure and could not be fixed by
a better drawing, so the ruling was that it is a tiled layer and that the pairing question it was being asked has
no answer on a ground that spans four colours and 2C02 luminance rows 0 and 2.

These tests hold the three things the ruling rests on, from the pixels rather than from the ruling's own prose:

1. the arithmetic that makes any single-body reading impossible on that ground. Every usable 2C02 entry is
   measured against `$0B` (luminance 0.0698) and `$20` (0.9387), the two ends of the ground, and none clears the
   3:1 floor on both. If a future palette change ever makes one clear both, the puff could be a figure and this
   test says so.
2. the declaration is a decision the tree carries and a regeneration cannot drop: the sidecar says `"layer": true`
   and the generator that owns the sheet lists it in `LAYER_SHEETS`.
3. one drawing, two writers. The four cells live in tools/art/make_title_exhaust_v2.py, the generator that owns
   game/sprites_src/title/spr_title_exhaust.png asks for them, and the shipped sheet is that drawing in `$20` and
   `$0C`. A redraw that ships different pixels from what the generator would write is the drift this pins out.

Nothing here trusts a report: every assertion reads the committed PNG, the committed sidecar, or the scene file.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "art"))

import contrast_check  # noqa: E402
import make_title_car  # noqa: E402
import make_title_exhaust_v2  # noqa: E402

TITLE = os.path.join(ROOT, "game", "sprites_src", "title")
SHEET = os.path.join(TITLE, "spr_title_exhaust.png")
SIDECAR = os.path.join(TITLE, "spr_title_exhaust.json")
SCENE_PATH = os.path.join(ROOT, "data", "palettes", "scene_title.json")

FRAME = 16
BODY = "#f8f8f8"   # $20, the body the road band can carry
INK = "#004058"    # $0C, the 1 px outline
# The two ends of the ground the puff is drawn over, measured over a full scroll in the ruling's section 1:
# $0B green at luminance 0.0698 (15.4 percent of the window) and $20 white at 0.9387 (5.9 percent).
GROUND_END_DARK = "#005800"
GROUND_END_LIGHT = "#f8f8f8"
FLOOR = 3.0


def sheet():
    with Image.open(SHEET) as image:
        return image.convert("RGBA")


def frames_of(image):
    return [image.crop((index * FRAME, 0, (index + 1) * FRAME, FRAME))
            for index in range(image.width // FRAME)]


def opaque(frame):
    return [(x, y, pixel[:3])
            for y in range(FRAME) for x in range(FRAME)
            for pixel in [frame.getpixel((x, y))] if pixel[3]]


def scene():
    with open(SCENE_PATH, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------------------------------
# 1. Why the figure reading has no answer on this ground.
# ---------------------------------------------------------------------------------------------------

def test_no_usable_2c02_entry_reads_on_both_ends_of_the_puff_ground():
    """The arithmetic the ruling stands on: the window between the two ends is empty."""
    dark = contrast_check.luminance(contrast_check.hex_to_rgb(GROUND_END_DARK))
    light = contrast_check.luminance(contrast_check.hex_to_rgb(GROUND_END_LIGHT))
    usable = []
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    for entry in table["entries"]:
        if not entry.get("usable", True):
            continue
        luma = contrast_check.luminance(contrast_check.hex_to_rgb(entry["hex"]))
        if (contrast_check.contrast(luma, dark) >= FLOOR
                and contrast_check.contrast(luma, light) >= FLOOR):
            usable.append(entry["code"])
    assert usable == [], "these entries read on both ends of the ground, so the puff could be drawn as a figure: %s" % usable


def test_the_two_shipped_entries_carry_the_ground_at_either_end():
    """And the layer reading is not a loophole: one of the two clears each end by a wide margin."""
    body = contrast_check.luminance(contrast_check.hex_to_rgb(BODY))
    ink = contrast_check.luminance(contrast_check.hex_to_rgb(INK))
    dark = contrast_check.luminance(contrast_check.hex_to_rgb(GROUND_END_DARK))
    light = contrast_check.luminance(contrast_check.hex_to_rgb(GROUND_END_LIGHT))
    assert contrast_check.contrast(body, dark) >= FLOOR
    assert contrast_check.contrast(ink, light) >= FLOOR
    # The one thing the layer instrument must still refuse: both colours lost on the same ground.
    for ground in (dark, light):
        assert contrast_check.contrast(body, ground) >= FLOOR or contrast_check.contrast(ink, ground) >= FLOOR


# ---------------------------------------------------------------------------------------------------
# 2. The declaration is carried by the tree, and a regeneration cannot drop it.
# ---------------------------------------------------------------------------------------------------

def test_the_sidecar_declares_a_tiled_layer_of_four_16x16_frames():
    with open(SIDECAR, "r", encoding="utf-8-sig") as handle:
        sidecar = json.load(handle)
    assert sidecar["layer"] is True, "the puff is ruled a tiled layer; palette_synergy reads this flag"
    assert (sidecar["frame_w"], sidecar["frame_h"]) == (FRAME, FRAME)
    assert sidecar["frames"] == 4
    assert sidecar["name"] == "spr_title_exhaust"


def test_the_generator_that_owns_the_sheet_declares_it_so_a_rerun_keeps_the_flag():
    assert "spr_title_exhaust" in make_title_car.LAYER_SHEETS
    # The body is drawn in the chip table, not the retired project palette, and the colour count guard has to
    # know that or a rerun exits on a colour it thinks is off palette.
    assert "spr_title_exhaust" in make_title_car.CHIP_DRAWN_SHEETS


# ---------------------------------------------------------------------------------------------------
# 3. One drawing, two writers: the shipped sheet is the shared cells in the pair bg3 carries.
# ---------------------------------------------------------------------------------------------------

def test_the_shipped_sheet_spends_exactly_the_two_entries_the_band_carries():
    bands = scene()["band_sprites"]
    assert bands["spr_title_exhaust"] == "bg3"
    ground_band = next(row for row in scene()["background"] if row["name"] == "bg3")
    carried = {tuple(contrast_check.hex_to_rgb(value)) for value in ground_band["hex"]}
    spent = {rgb for frame in frames_of(sheet()) for _, _, rgb in opaque(frame)}
    assert spent == {contrast_check.hex_to_rgb(BODY), contrast_check.hex_to_rgb(INK)}
    assert spent <= carried, "the puff may only spend entries bg3 paints its band with: %s vs %s" % (spent, carried)


def test_the_shipped_sheet_is_what_the_shared_drawing_produces():
    drawn = make_title_exhaust_v2.build_frames(BODY, INK)
    shipped = frames_of(sheet())
    assert len(drawn) == len(shipped) == 4
    for index, (want, got) in enumerate(zip(drawn, shipped)):
        assert list(want.getdata()) == list(got.getdata()), "frame %d differs from the shared drawing" % index


def test_the_generator_would_write_the_same_pixels_again():
    """A rerun of tools/art/make_title_car.py must not move the sheet, so the preview cannot become a lie."""
    would_write = make_title_car.build_exhaust_frames()
    shipped = frames_of(sheet())
    assert len(would_write) == len(shipped) == 4
    for index, (want, got) in enumerate(zip(would_write, shipped)):
        assert list(want.getdata()) == list(got.getdata()), "frame %d the generator would rewrite" % index


def test_the_four_frames_grow_and_every_one_carries_an_outline():
    """SP-046: a four frame effect changes size, not just position. And no frame is a single flat blob."""
    shipped = frames_of(sheet())
    drawn = [len(opaque(frame)) for frame in shipped]
    assert drawn == sorted(drawn) and len(set(drawn)) == 4, "the frames must grow, not pulse: %s" % drawn
    for index, frame in enumerate(shipped):
        pixels = opaque(frame)
        inks = [rgb for _, _, rgb in pixels if rgb == contrast_check.hex_to_rgb(INK)]
        bodies = [rgb for _, _, rgb in pixels if rgb == contrast_check.hex_to_rgb(BODY)]
        assert inks, "frame %d has no ink, so it has no edge on a light ground" % index
        assert bodies, "frame %d has no body, so it has no edge on a dark ground" % index
