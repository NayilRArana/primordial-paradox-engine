"""Tests for tools/check_ts_exterior.py check 13, the walkable band (card t_b01c88ff).

Why this file exists: check 13 refuses a ground at or above RULE 0 point 2's 0.25 light line under the party,
whose four walking sheets carry near white bodies. Its only exemption was the park's grass, which drew H $2A
#58d854 at 0.518. Card t_b01c88ff darkened the tile instead of weakening the check, so three things have to hold
afterwards and each is arithmetic rather than a look:

  - the exemption list is EMPTY, because a list with the park in it after the fix would permit exactly the thing
    the check exists to stop;
  - no walkable tile on ts_exterior.png draws an entry at or above 0.25 luminance, measured through the check's
    own function and its own palette table;
  - the ground under the judged park row on the composed Westminster frame is the two dark greens and the shared
    backdrop, and nothing else, so the row that says "0 failing pairs" is measuring the park.

Nothing in the suite ran check 13 before this file: the tool existed and was green, but a regeneration that put
$2A back on the grass would have been caught only by whoever remembered to run it.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import check_ts_exterior  # noqa: E402
import contrast_check  # noqa: E402

LIGHT_GROUND = 0.25
PARK_CARD = "card t_b01c88ff"


def tileset_meta() -> dict:
    with open(os.path.join(ROOT, "game", "sprites_src", "env", "ts_exterior.json"),
              encoding="utf-8-sig") as handle:
        return json.load(handle)


def park_row() -> dict:
    """The judged row card t_b01c88ff wrote in westminster's scene file."""
    with open(os.path.join(ROOT, "data", "palettes", "scene_westminster.json"),
              encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    rows = [row for row in payload.get("judged", []) if str(row.get("note", "")).startswith(PARK_CARD)]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_walkable_band_exemption_list_is_empty():
    """The park was the last exemption. A new one has to be a decision in a diff, so this pins the list empty."""
    assert check_ts_exterior.WALKABLE_LIGHT_EXEMPT == {}, (
        "check 13 exempts %s; card t_b01c88ff closed the park and the list is meant to be empty"
        % sorted(check_ts_exterior.WALKABLE_LIGHT_EXEMPT))


def test_no_walkable_tile_draws_an_entry_at_or_above_the_light_line():
    rep = check_ts_exterior.Report()
    check_ts_exterior.check_walkable_band(ROOT, tileset_meta(), rep)
    assert rep.fails == [], rep.fails
    assert rep.lines and rep.lines[0].startswith("PASS"), rep.lines


def test_the_park_ground_on_the_composed_frame_is_the_two_dark_greens():
    row = park_row()
    background = row["background"]
    at = row["at"]
    image = Image.open(os.path.join(ROOT, background.replace("/", os.sep))).convert("RGB")
    box = (at[0], at[1], at[0] + 16, at[1] + 16)
    colours = {"#%02x%02x%02x" % px for px in image.crop(box).getdata()}
    assert colours <= {"#007800", "#006800", "#000000"}, (
        "%s at %s carries %s; the walkable park is G $09, D $0A and the shared backdrop only"
        % (background, at, sorted(colours)))
    for hex_code in colours:
        rgb = tuple(int(hex_code[i:i + 2], 16) for i in (1, 3, 5))
        assert contrast_check.luminance(rgb) < LIGHT_GROUND, (hex_code, contrast_check.luminance(rgb))
