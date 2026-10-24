"""SPRITE-REDRAW-1: the v2 overworld sprites are legal on the chip and are not a white blob.

The card's check has two halves and both are measured here rather than described:

1. Hardware (ART-BIBLE section 1, rule C6): a 16x16 figure is four 8x8 tiles and an 8x8 sprite tile carries
   3 opaque colours plus transparency. Every tile of every frame of every character is measured.
2. The blob test (SPRITE-CRAFT section 8.5), four numbers on the sailor, the sheet Nayil called a white
   blob. On disk the v1 sheet carried 2 colours (white and navy, no ink, no skin), so the regression this
   test locks down is real and was measured before the redraw.
3. The blob floor is read on a THREE entry sheet, by gamedev ruling on card t_a44ae3db (2026-10-24). A 16x16
   cell spends one sprite palette of three (ART-BIBLE RULE 0 point 3, hardware rule 16), so the entry count
   is exact at 3 and never a floor of four: the sheet had four entries and needed two sprite palettes before
   card t_bd5cfad5, and that is the palette first defect, not a blob. The lightest share ceiling moves with
   it, from the four entry margin of 30 percent to 8.5's own blob line of 45 percent, and the dark share
   floor of 30 percent takes over the job the ceiling was doing. Measured on the down idle frame: 3 entries,
   white 57 of 152 drawn (37.5 percent), navy 62 (40.8 percent). The v1 blob was 75.7 percent white and
   24.3 percent navy, so both numbers still refuse it.

The committed PNGs are also checked against the generator's own output, so a hand edited PNG fails.
"""

from __future__ import annotations

import os
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import make_characters_v2 as v2  # noqa: E402

CHAR_DIR = os.path.join(ROOT, "game", "sprites_src", "chars")
NAMES = ["sailor", "percy", "konrad", "zander", "hadrian"]


def test_every_tile_of_every_frame_carries_at_most_three_opaque_colours():
    worst = {}
    for spec in v2.cast():
        for view in ("down", "up", "right"):
            for walk in (False, True):
                count, at, codes = v2.tile_audit(v2.frame(spec, view, walk))
                assert count <= 3, "%s %s walk=%s has %d colours at %s (%s)" % (
                    spec["name"], view, walk, count, at, codes)
                worst[spec["name"]] = max(worst.get(spec["name"], 0), count)
    assert worst == {name: 3 for name in NAMES}, worst


def test_sailor_is_not_a_white_blob():
    spec = [s for s in v2.cast() if s["name"] == "sailor"][0]
    grid = v2.frame(spec, "down", False)
    pixels = {}
    for y in range(v2.OW_H):
        for x in range(v2.OW_W):
            code = grid.get(x, y)
            if code:
                pixels.setdefault(spec["palette"][code].lower(), 0)
                pixels[spec["palette"][code].lower()] += 1
    drawn = sum(pixels.values())
    # Exact, not a floor: one sprite palette carries three opaque entries (hardware rule 16) and a legal cell
    # spends all three. Two entries is the v1 white blob (white and navy only); four is a sheet that needs a
    # second sprite palette, which is the defect card t_bd5cfad5 removed.
    assert len(pixels) == 3, pixels
    lightest = "#fcfcfc"
    share = 100.0 * pixels[lightest] / drawn
    assert share < 45.0, "lightest tone is %.1f percent of %d drawn pixels, the blob line is 45" % (
        share, drawn)
    # The counterweight, and the number the v1 blob actually failed: the dark entry has to own at least a
    # third of the figure, because on a three entry sheet the outline, collar and belt carry the silhouette.
    dark_share = 100.0 * pixels[spec["palette"]["k"].lower()] / drawn
    assert dark_share >= 30.0, "the dark entry is %.1f percent of %d drawn pixels, the floor is 30" % (
        dark_share, drawn)
    # The body band must carry ink plus at least two palette steps, or the uniform is a single fill.
    body = v2.band_colours(grid, 8, 16)
    assert "k" in body and len([c for c in body if c != "k"]) >= 2, body
    # No row may be free of a dark pixel: that row has no structure at all.
    for y in range(v2.OW_H):
        row = [grid.get(x, y) for x in range(v2.OW_W)]
        assert any(code == "k" for code in row), "row %d has no dark pixel" % y
    # Interior dark pixels, the lines that stop a silhouette reading as a blob.
    interior = 0
    for y in range(8, 16):
        for x in range(v2.OW_W):
            if grid.get(x, y) != "k":
                continue
            edge = any(
                not (0 <= x + dx < v2.OW_W and 0 <= y + dy < v2.OW_H) or grid.get(x + dx, y + dy) is None
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
            if not edge:
                interior += 1
    assert interior >= 8, "only %d interior dark pixels in the body block" % interior
    # 8.5 point 3, which this test skipped until the ruling on card t_a44ae3db: distinct vertical runs of
    # dark read down the midline of the body block (collar, belt, trouser break). The doc asks for at least
    # 3 and this sheet measures exactly 3 on all six frames; the per column spread on the down idle frame is
    # [1, 3, 1, 1, 2, 3, 3, 2, 1, 1, 3, 1] over the twelve body columns.
    runs = []
    inside = False
    for y in range(8, 16):
        dark = grid.get(8, y) == "k"
        if dark and not inside:
            runs.append(y)
        inside = dark
    assert len(runs) >= 3, "the body midline crosses only %d dark bands at rows %s" % (len(runs), runs)


@pytest.mark.parametrize("name", NAMES)
def test_committed_sheet_is_the_generator_output(name):
    spec = [s for s in v2.cast() if s["name"] == name][0]
    expected = v2.image_of(v2.sheet_frames(spec), spec["palette"])
    path = os.path.join(CHAR_DIR, name + "_ow_v2.png")
    assert os.path.isfile(path), path
    with Image.open(path) as committed:
        assert committed.size == (v2.OW_W * 8, v2.OW_H)
        assert committed.convert("RGBA").tobytes() == expected.tobytes()


@pytest.mark.parametrize("name", NAMES)
def test_sheet_metadata_matches_the_contract_the_game_reads(name):
    import json

    path = os.path.join(CHAR_DIR, name + "_ow_v2.json")
    with open(path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta == {"name": name + "_ow_v2", "frame_w": 16, "frame_h": 16, "frames": 8, "fps": v2.OW_FPS}
