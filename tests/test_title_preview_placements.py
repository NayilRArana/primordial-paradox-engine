"""Pins for the title preview composer: its placements are the game's placements.

Card t_2a34652e (gamedev). compose_title_preview.py is the picture the eye rounds judge,
and it used to carry hand-kept numbers the shipping screen had moved away from: a CAR_Y
of 186 where pp_title.gml draws PP_TITLE_CAR_Y 193, a wheel sprite pasted over a v2 car
that bakes its own wheels, and busts drawn over a title that shows the car's exterior
only. The preview and the frame that reaches a screen were two different pictures.

The fix is structural, and so are these pins:

1. the composer reads the placements out of the game's own file (read_game_macros), so
   there is nothing left to keep in step by hand. This test asserts the two agree and
   names the drift if they ever disagree again, the same cross-read style
   tests/test_title_bands.py uses on the layer table.
2. the composer reads the layer table from data/title.json, the file the game itself
   loads, not from the world generator's manifest (which carried the pre-I32 layer
   drift: downs at 92 and the road at 196 where the game reads 96 and 192).
3. the composer pastes no sprite the shipping title does not draw: no separate wheel,
   no bust, no bubble over the car.

Nothing here trusts a report: every assertion reads the .gml text, the JSON, and the
composer's own source.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import compose_title_preview as composer  # noqa: E402

GML = os.path.join(ROOT, "game", "scripts", "pp_title", "pp_title.gml")
TABLE_PATH = os.path.join(ROOT, "data", "title.json")
COMPOSER_PATH = os.path.join(ROOT, "tools", "art", "compose_title_preview.py")


def gml_macro(name: str) -> int:
    with open(GML, "r", encoding="utf-8") as handle:
        source = handle.read()
    match = re.search(r"#macro\s+%s\s+(-?\d+)\b" % re.escape(name), source)
    assert match, "no #macro %s in %s" % (name, GML)
    return int(match.group(1))


def composer_source() -> str:
    with open(COMPOSER_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_read_game_macros_matches_the_gml():
    """The function the composer uses actually finds what the .gml declares."""
    found = composer.read_game_macros(ROOT)
    for name in composer.MACRO_NAMES:
        assert found[name] == gml_macro(name), name


def test_the_composers_car_sits_where_the_game_draws_it():
    """The 7 px drift, pinned. CAR_Y was 186 where PP_TITLE_CAR_Y is 193."""
    art = composer.TitleArt(os.path.join(ROOT, "game", "sprites_src", "title"))
    scene = composer.Scene(art, ROOT)
    assert scene.car_x == gml_macro("PP_TITLE_CAR_X")
    assert scene.car_y == gml_macro("PP_TITLE_CAR_Y")
    assert scene.cone_x == gml_macro("PP_TITLE_CONE_X")
    assert scene.cone_y == gml_macro("PP_TITLE_CONE_Y")
    assert scene.sign_x == gml_macro("PP_TITLE_SIGN_X")
    assert scene.sign_y == gml_macro("PP_TITLE_SIGN_Y")
    assert scene.logo_x == gml_macro("PP_TITLE_LOGO_X")
    assert scene.logo_y == gml_macro("PP_TITLE_LOGO_Y")
    # And the same pairing tests/test_title_bands.py already pins for the game.
    assert (scene.car_x, scene.car_y) == (76, 193)


def test_the_composer_no_longer_hard_keeps_a_car_y():
    """The stale hand-kept number is gone from the file, not just unused.

    A module-level CAR_Y = 186 is exactly the shape that drifted; the pin refuses any
    module-level CAR_Y at all, so the only way to place the car is through the game.
    """
    assert not re.search(r"^CAR_Y\s*=", composer_source(), re.M), \
        "the composer must not carry its own CAR_Y, read it from the game"
    assert not re.search(r"^FALLBACK_CAR_X\s*=|^FALLBACK_CONE_X\s*=", composer_source(), re.M), \
        "same for the fallback x placements"


def test_the_layer_table_comes_from_the_file_the_game_loads():
    """The composer reads data/title.json, not the world manifest, and takes its y/speed from it."""
    with open(TABLE_PATH, "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    art = composer.TitleArt(os.path.join(ROOT, "game", "sprites_src", "title"))
    scene = composer.Scene(art, ROOT)
    by_name = {row["name"]: row for row in table["layers"]}
    assert [layer["name"] for layer in scene.layers] == [row["name"] for row in table["layers"]]
    for layer in scene.layers:
        row = by_name[layer["name"]]
        assert layer["y"] == row["y"], layer["name"]
        assert layer["speed"] == row["speed"], layer["name"]
    # The pre-I32 manifest drift can come back only if it comes back through the game's file.
    downs = next(layer for layer in scene.layers if layer["name"] == "title_L3_downs")
    road = next(layer for layer in scene.layers if layer["name"] == "title_L6_road")
    assert downs["y"] == 96 and road["y"] == 192


def test_the_fallback_table_is_the_games_own_defaults():
    """The fallback is pp_title_defaults() from the .gml, asserted against the script text."""
    with open(GML, "r", encoding="utf-8") as handle:
        source = handle.read()
    block = source[source.index("function pp_title_defaults()"):]
    block = block[:block.index("car_x:")]
    for name, y, speed in [(row["name"], row["y"], row["speed"]) for row in composer.FALLBACK_LAYERS]:
        pattern = r'name:\s*"%s",\s*y:\s*%d,\s*speed:\s*%s' % (re.escape(name), y,
                                                               str(speed).rstrip("0").rstrip("."))
        assert re.search(pattern, block), "fallback row %s is not the default in the .gml" % name


def test_the_composer_pastes_no_wheel_bust_or_bubble():
    """The shipping title (pp_title_draw_car) draws exhaust, body, nothing else over the car."""
    source = composer_source()
    start = source.index("def compose_frame")
    end = source.index("# The contact sheet", start)
    body = source[start:end]
    # A paste, not a mention: the docstring and the .gml comments name the retired strips on purpose.
    for name in ("spr_title_wheel", "spr_title_konrad", "spr_title_zander", "spr_title_bubble"):
        assert 'frame("%s"' % name not in body and '("%s",' % name not in body, \
            "compose_frame must not draw %s; the title does not" % name
    with open(GML, "r", encoding="utf-8") as handle:
        gml = handle.read()
    draw_car = gml[gml.index("function pp_title_draw_car"):gml.index("function pp_title_draw_cloud")]
    for name in ("spr_title_wheel", "spr_title_konrad", "spr_title_zander", "spr_title_bubble"):
        assert 'pp_art_draw("%s"' % name not in draw_car, \
            "%s moved into pp_title_draw_car; the pin needs a look" % name
