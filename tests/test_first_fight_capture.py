"""Tests for the first fight capture's frame reader (tools/capture_first_fight.py).

Card t_da94341c. The tool had been unable to score a frame for three unrelated reasons, and none of them was covered by
a test, so it rotted silently while the suite stayed green:

    * its geometry guards still named the pre BATTLE-FONT-WIRE draw call, so the first frame check raised SystemExit;
    * its frame reader demanded exact palette pixels on frames it cuts from an h264 recording itself, so every frame it
      produced was refused;
    * its press schedule stopped one turn short of the result panel.

The reader and the FIGHT label measure are pinned here. The schedule is a number in the file, not a function, and the
run that proves it is the muted capture itself.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PIL")

# Card TEST-CLASSIFY-33, applied at the 2026-10-23 10:35 gate (card t_37657207): load_tool() imports
# tools/capture_first_fight.py, which imports capture_title and play_demo at module level, and
# capture_title binds ctypes.windll.user32 at line 128. On the Pine Linux hosts that import raises
# AttributeError before a line of any test here runs, which is the same class as tests/test_capture_title.py.
# The marker is a skip off Windows, never a pass: these seven rows run on the Windows suite.
pytestmark = pytest.mark.windows_only

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "capture_first_fight.py")


def load_tool():
    """The tool, imported by name from tools/ (tests/conftest.py puts that directory on sys.path).

    Card t_87ee4228: this used to load the file through importlib by path, and the commit gate maps a tool to
    the tests that import it BY NAME, so the gate refused the tool as "UNMAPPED, no test maps to" while these
    five tests were exercising it. Importing the module is also what tests/conftest.py documents: a worktree run
    imports the worktree's tools, never the live tree's.
    """
    import capture_first_fight

    assert os.path.isfile(TOOL), "tools/capture_first_fight.py is missing"
    return capture_first_fight


def test_a_battle_frame_colour_snaps_onto_the_game_palette():
    """The measured battle frame carries (27, 27, 35) where the game drew paper (28, 28, 36)."""
    from PIL import Image

    tool = load_tool()
    image = Image.new("RGB", (4, 4), (27, 27, 35))
    snapped, share = tool.snap_to_palette(image, tool.game_palette())
    assert share == 1.0
    assert snapped.getpixel((0, 0)) == (28, 28, 36)


def test_a_frame_that_is_not_the_game_is_refused(tmp_path):
    """A picture full of colours the game never draws must not be measured as if it were the game's screen."""
    from PIL import Image

    tool = load_tool()
    path = tmp_path / "not_the_game.png"
    image = Image.new("RGB", (tool.SCREEN_W * tool.SCALE, tool.SCREEN_H * tool.SCALE))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            # Green and red ramps: no game colour is within twelve of these.
            pixels[x, y] = (x % 256, 200, y % 256)
    image.save(path)
    got, why = tool.load_screen_pixels(str(path))
    assert got is None
    assert "not the game" in why


def test_the_fight_label_is_measured_by_its_span_not_by_its_runs():
    """The sheet's glyphs have internal gaps: a real FIGHT label counts 9 ink runs across a 41 px span."""
    tool = load_tool()
    scores = {
        "battle_box_paper": 0.93,
        "battle_box_border": 0.71,
        "cells": {"FIGHT": {"clusters": 9, "bbox_width": 41, "ink_pixels": 85}},
    }
    assert tool.is_menu_frame(scores)


def test_a_scatter_of_ink_does_not_count_as_the_fight_label():
    tool = load_tool()
    scores = {
        "battle_box_paper": 0.93,
        "battle_box_border": 0.71,
        "cells": {"FIGHT": {"clusters": 5, "bbox_width": 8, "ink_pixels": 25}},
    }
    assert not tool.is_menu_frame(scores)


def test_the_label_cell_geometry_still_matches_the_director():
    """The guards exist so the checks never measure a rectangle the game stopped drawing."""
    tool = load_tool()
    geom = tool.menu_geometry()
    assert geom["box"] == (8, 168, 248, 232)
    assert geom["label_x"] == (24, 128)
    assert geom["glyph"] == 8


def test_the_picture_gate_uses_the_same_number_as_the_frame_reader():
    """Card t_87ee4228: one question ("is this the game's picture"), one number.

    The recording gate is taken over the union of data/palette.json and data/nes_palette.json, because the game's
    screens do not all draw from one set; if the two numbers drift apart, a frame the reader accepts could still
    fail the recording gate on the same picture.
    """
    tool = load_tool()
    assert tool.VIDEO_PICTURE_MIN == tool.PALETTE_SNAP_MIN


def test_the_other_lanes_measures_never_gate_this_capture():
    """The NES colour rule and the TALK leg are reported, not folded into `ok` (card t_87ee4228)."""
    tool = load_tool()
    video = {"nes_palette_ok": False, "samples": []}
    assert tool.look_rule(video)["gates_this_card"] is False
    talk = tool.talk_leg()
    assert talk["gates_this_card"] is False
    # A three TALK spare needs an encounter with talks_to_spare 3 on a battle trigger, and the deck has one.
    assert any(f["encounter"] == "tutorial_sailors" for f in talk["reachable_talk_fights"])
