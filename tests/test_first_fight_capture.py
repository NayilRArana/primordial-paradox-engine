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


# Card t_239422fe. Two measures in this tool were scoring something other than what their names claim, and neither was
# covered here, so both stayed green in the suite while being wrong on a real first fight (117 frame recording of
# 2026-10-26, resume_probe/first_fight_resume_capture.mp4):
#
#   * the FIGHT cell was masked by exact equality with the ink role #0b0b0f, which appears 0 times in the cell on a
#     frame whose label is legible: the sheet paints a 2C02 white and the encoder spreads it over near-white values;
#   * battle_box_border was the share of the three rows above the window that are not paper, which is 1.0000 on any
#     screen that is not paper: it read 1.0000 on 123 of 123 frames of a recording with no battle in it.
#
# The four rows below pin the corrected claims on synthetic screens, so they run without a capture. The numbers they
# stand for were measured on the recording: FIGHT cell 121 px over a 39 px span in 5 runs, border 1.0000 on all 42
# command window frames and 0.0000 on every frame without a window.


class _Screen(dict):
    """A frame as score_frame reads it: pixels[x, y], with every unpainted pixel the given colour."""

    def __init__(self, fill):
        super().__init__()
        self.fill = fill

    def __missing__(self, key):
        return self.fill


def _window_screen(tool, roles, geom, label_strokes=False):
    """The command window on a paper fill, the picture above it in the dim role, optionally the FIGHT label on it."""
    screen = _Screen(roles["paper"])
    bx1, by1, bx2, by2 = geom["box"]
    for y in range(max(0, by1 - 3), by1):
        for x in range(0, tool.SCREEN_W):
            screen[(x, y)] = roles["dim"]
    for y in range(by1, by2 + 1):
        for x in (bx1, bx2):
            screen[(x, y)] = roles["dim"]
    if label_strokes:
        # Five 4 px strokes in the FIGHT cell's 8 px glyph cells, on rows 176 to 181, in the near white the recorded
        # label actually carries (248,247,252), which is 219 from the paper in the red channel.
        cx = geom["label_x"][0]
        for glyph in range(5):
            for x in range(cx + glyph * 8, cx + glyph * 8 + 4):
                for y in range(176, 182):
                    screen[(x, y)] = (248, 247, 252)
    return screen


def test_the_fight_label_is_measured_against_the_paper_not_for_a_role_colour():
    """A near white FIGHT label on paper is the FIGHT label, even though no palette colour is on its strokes."""
    tool = load_tool()
    roles = tool.role_colours()
    geom = tool.menu_geometry()
    labels = tool.command_labels()
    pixels = _window_screen(tool, roles, geom, label_strokes=True)
    scores = tool.score_frame(pixels, roles, geom, labels)
    fight = scores["cells"]["FIGHT"]
    assert fight["ink_pixels"] >= tool.FIGHT_INK_MIN
    assert fight["bbox_width"] >= tool.FIGHT_SPAN_MIN
    assert fight["clusters"] == tool.FIGHT_CLUSTERS
    assert tool.is_menu_frame(scores)
    # The measure this replaced: the same cell masked by exact equality with the ink role, which is what the recorded
    # frame carried none of.
    assert tool.ink_mask(pixels, fight["rect"], (roles["ink"],)) == {}


def test_a_paper_window_with_no_label_on_it_is_not_a_fight_command():
    """The window is up and bounded, so it is a battle frame, but an empty cell is not the FIGHT command."""
    tool = load_tool()
    roles = tool.role_colours()
    geom = tool.menu_geometry()
    labels = tool.command_labels()
    pixels = _window_screen(tool, roles, geom, label_strokes=False)
    scores = tool.score_frame(pixels, roles, geom, labels)
    assert tool.is_battle_frame(scores)
    assert scores["cells"]["FIGHT"]["ink_pixels"] == 0
    assert not tool.is_menu_frame(scores)


def test_the_border_step_is_zero_on_a_screen_with_no_window():
    """The no-battle recording: a screen that is not paper anywhere, where the old measure read exactly 1.0000."""
    tool = load_tool()
    roles = tool.role_colours()
    geom = tool.menu_geometry()
    labels = tool.command_labels()
    pixels = _Screen((6, 5, 108))
    scores = tool.score_frame(pixels, roles, geom, labels)
    assert scores["battle_box_paper"] == 0.0
    assert scores["battle_box_border"] == 0.0
    assert not tool.is_battle_frame(scores)


def test_the_border_step_needs_paper_inside_the_window_not_only_picture_above_it():
    """A screen that is paper everywhere has no boundary: the outside rows are paper too, so the step is zero."""
    tool = load_tool()
    roles = tool.role_colours()
    geom = tool.menu_geometry()
    labels = tool.command_labels()
    pixels = _Screen(roles["paper"])
    scores = tool.score_frame(pixels, roles, geom, labels)
    assert scores["battle_box_paper"] == 1.0
    assert scores["battle_box_border"] == 0.0
    assert not tool.is_battle_frame(scores)

