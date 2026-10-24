"""Tests for the talk fight capture (tools/capture_talk_fight.py).

Card t_27aa179e. The parent card's capture proved a fight was FOUGHT and could not prove one was TALKED THROUGH, so
this tool walks the same deck trigger a second time, presses TALK three times and then SPARE, and measures what the
game drew and what the game wrote. Nothing here launches the game: the run is a muted capture, and what a test can
hold down is the reading half, which is the half that rots silently when a draw call moves.

Five things are pinned:
  * the log parsers, against the exact line shapes the director and the talk module now write;
  * the three frame predicates, each with a positive row taken from the measured numbers of the FIGHT capture and a
    negative row that must not pass (ink scattered, the cursor somewhere else, a four glyph word on the result panel);
  * the option labels, read from the encounter's own talk dialogue, so the panel is measured against the words the
    data names;
  * the two geometry guards, so a check can never sample a rectangle the game stopped drawing;
  * the launch policy, so the new launch site goes through pp_launch and the idle gate like every other one.

Run: python -m pytest tests/test_talk_fight_capture.py -q
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PIL")

# The tool imports capture_title at module level, which binds ctypes.windll.user32 there, so this file is Windows only
# for the same reason tests/test_first_fight_capture.py is (card TEST-CLASSIFY-33). A skip off Windows is never a pass.
pytestmark = pytest.mark.windows_only

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "capture_talk_fight.py")


def load_tool():
    """The tool, imported by name from tools/ (tests/conftest.py puts that directory on sys.path).

    The commit gate maps a tool to the tests that import it BY NAME, so this has to be an import and not a load by path.
    """
    import capture_talk_fight

    assert os.path.isfile(TOOL), "tools/capture_talk_fight.py is missing"
    return capture_talk_fight


# ---------------------------------------------------------------------------------------------------------------------
# 1: the lines the game writes, parsed

def test_the_command_line_names_the_command_the_player_chose():
    tool = load_tool()
    got = tool.parse_command("PP: command talk, turn 2, enemy navy_sailor, enemy hp 15, party hp 18")
    assert got == {"key": "talk", "turn": 2, "enemy": "navy_sailor", "enemy_hp": 15, "party_hp": 18}


def test_the_command_line_the_log_carries_before_this_card_is_not_read_as_a_command():
    """`PP: battle start` and the boot lines must not parse as commands, or the count of talks would be wrong."""
    tool = load_tool()
    assert tool.parse_command("PP: battle start tutorial_sailors on ship_small 4,7") is None
    assert tool.parse_command("PP: battle menu, turn 0, cursor 0, enemy hp 15/15") is None
    assert tool.parse_menu("PP: command talk, turn 1, enemy navy_sailor, enemy hp 15, party hp 20") is None


def test_the_menu_line_carries_the_cursor_the_driver_moves_from():
    tool = load_tool()
    got = tool.parse_menu("PP: battle menu, turn 3, cursor 2, enemy hp 15/15")
    assert got == {"turn": 3, "cursor": 2, "enemy_hp": 15, "enemy_max": 15}


def test_the_talk_panel_lines_carry_the_meter_the_three_talks_move():
    tool = load_tool()
    assert tool.parse_open("PP: talk open, 3 options, mercy 20, trust 2") == \
        {"options": 3, "mercy": 20, "trust": 2}
    assert tool.parse_pick("PP: talk pick, option 0, effect soften, mercy 60, trust 3") == \
        {"option": 0, "effect": "soften", "mercy": 60, "trust": 3}


def test_the_result_line_names_the_outcome_word_the_panel_prints():
    tool = load_tool()
    assert tool.parse_result("PP: fight result spare, turn 4, enemy navy_sailor, enemy hp 0/15") == \
        {"outcome": "spare", "turn": 4, "enemy": "navy_sailor", "enemy_hp": 0, "enemy_max": 15}


def test_a_black_frame_is_not_a_talk_frame():
    """A fade to black reads as ink everywhere, which is how this tool first scored a black frame as the TALK list.

    Measured on output/first_fight_talk_frames/t_0054.png from the first run: 546148 of its 552960 pixels are the ink
    role, so every ink count on it is trivially large. The guard is the window: no paper, no command list.
    """
    tool = load_tool()
    assert tool.box_drawn(talk_scores([0, 21, 0], box=0.0)) is False
    assert tool.is_talk_frame(talk_scores([0, 21, 0], box=0.0)) is False


def test_the_talk_cursor_needs_its_own_mark():
    """The label ink alone is the FIGHT claim. TALK has to show the text role triangle too, or the press is elsewhere."""
    tool = load_tool()
    assert tool.box_drawn(talk_scores([0, 21, 0])) is True
    assert tool.is_talk_frame(talk_scores([0, 0, 0])) is False
    assert tool.is_talk_frame(talk_scores([0, 8, 0])) is True


def test_the_sheet_ink_is_the_colour_the_frames_carry():
    """The sheet paints (248,248,248) and this run's frames carry it as (232,231,236), which is 16 apart."""
    tool = load_tool()
    ink = tool.sheet_ink()
    assert min(ink) >= 200
    assert max(abs(ink[0] - 232), abs(ink[1] - 231), abs(ink[2] - 236)) <= tool.GLYPH_TOLERANCE


def test_a_log_tail_reads_only_what_is_new_and_waits_for_a_whole_line(tmp_path):
    """The driver presses on the strength of these lines, so a half written line must not count as an arrival."""
    tool = load_tool()
    path = tmp_path / "game.log"
    path.write_text("PP: muted\n", encoding="utf-8")
    tail = tool.LogTail(str(path))
    assert tail.pump() == ["PP: muted"]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("PP: battle start tutorial_sailors on ship_small 4,7")
    assert tail.pump() == []
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\nPP: battle menu, turn 0, cursor 0, enemy hp 15/15\n")
    new = tail.pump()
    assert new[0] == "PP: battle start tutorial_sailors on ship_small 4,7"
    assert any("PP: battle menu" in line for line in new)


def test_one_wait_does_not_swallow_the_line_the_next_wait_wants(tmp_path):
    """Two lines written between two polls arrive in one chunk, and the driver needs both of them in order."""
    tool = load_tool()
    path = tmp_path / "game.log"
    path.write_text("PP: talk open, 3 options, mercy 20, trust 1\nPP: talk pick, option 0, effect soften, "
                    "mercy 20, trust 1\n", encoding="utf-8")
    tail = tool.LogTail(str(path))
    opened, _waited = tail.wait(lambda line: line.startswith("PP: talk open"), 1.0)
    picked, _waited = tail.wait(lambda line: line.startswith("PP: talk pick"), 1.0)
    assert opened.startswith("PP: talk open")
    assert picked.startswith("PP: talk pick")


# ---------------------------------------------------------------------------------------------------------------------
# 2: the frame predicates

def talk_scores(triangles, span=30, ink=97, box=0.93, options=None):
    """A frame's scores with the text bands a drawn window leaves, in the order they appear top to bottom.

    Each entry in `triangles` is the cursor mark on one band: a band of 8 px text with a 6 x 8 triangle beside it is
    what both the command list and the option panel draw, and the triangle is the only thing that says which row the
    player is on. The measured rows are 176, 196 and 216 on this scene (pitch 20), which the checks FIND rather than
    place, so the tops here are only used to tell the bands apart.
    """
    bands = [{"top": 176 + 20 * index, "bottom": 183 + 20 * index, "ink": 60, "triangle": triangles[index]}
             for index in range(len(triangles))]
    return {
        "battle_box_paper": box,
        "battle_box_border": 0.67,
        "cells": {},
        "bands": bands,
        "talk_cell": {"rect": None, "ink_pixels": ink, "bbox_width": span},
        "options": options or [],
        "message_box_paper": 0.0,
        "message_text_rows": 0,
        "victory_panel_paper": 0.0,
        "victory_word_width": 0,
        "victory_press_width": 0,
    }


def test_the_talk_cell_is_measured_by_its_span_and_the_cursor_beside_it():
    """Measured on this run's frame t_0025: three bands, TALK ink 97 px across 30, and the triangle on the middle one.

    TALK is the third entry of the command table, and the list draws entries 2 and 3 on its second row, so the mark
    that means "the player is on TALK" is on band index 1.
    """
    tool = load_tool()
    assert tool.is_talk_frame(talk_scores([0, 21, 0]))


def test_a_command_list_with_the_cursor_elsewhere_is_not_a_talk_frame():
    """The cursor mark is what separates "TALK is on the list" from "the player chose TALK"."""
    tool = load_tool()
    assert not tool.is_talk_frame(talk_scores([21, 0, 0]))
    assert not tool.is_talk_frame(talk_scores([0, 0, 21]))
    assert not tool.is_talk_frame(talk_scores([0, 21, 0], span=26))
    assert not tool.is_talk_frame(talk_scores([0, 21, 0], ink=20))


def test_the_option_panel_needs_all_three_authored_rows():
    tool = load_tool()
    labels = tool.option_labels()
    assert len(labels) == 3
    rows = [{"label": label, "ink_pixels": 60, "bbox_width": 8 * len(label) - 3, "expected_width": 8 * len(label)}
            for label in labels]
    assert tool.is_option_frame(talk_scores([0, 21, 0], options=rows))
    # One row short is not the panel.
    assert not tool.is_option_frame(talk_scores([0, 21, 0], options=rows[:2]))
    # A row of ink that is the wrong width is not the word the data names.
    narrow = [dict(rows[0], bbox_width=40), rows[1], rows[2]]
    assert not tool.is_option_frame(talk_scores([0, 21, 0], options=narrow))
    # No window on screen is not the panel, however wide the ink in the band happens to be.
    assert not tool.is_option_frame(talk_scores([0, 21, 0], box=0.0, options=rows))


def test_the_reply_board_is_a_message_window_without_a_command_list():
    tool = load_tool()
    scores = talk_scores([])
    scores["message_box_paper"] = 0.94
    scores["message_text_rows"] = 3
    assert tool.is_reply_frame(scores)
    # The command list on screen means this is the menu, not a reply.
    menu = talk_scores([])
    menu["message_box_paper"] = 0.94
    menu["message_text_rows"] = 3
    menu["cells"] = {"TALK": {"bbox_width": 30, "ink_pixels": 48}}
    assert not tool.is_reply_frame(menu)


def test_the_spare_word_is_wider_than_kill_and_no_wider_than_five_glyphs():
    """`kill` measured 31 px on the FIGHT capture; five glyphs at the 8 px pitch is 40 px of cell."""
    tool = load_tool()
    base = talk_scores([])
    spare = dict(base, victory_panel_paper=0.96, victory_word_width=36, victory_press_width=49)
    kill = dict(base, victory_panel_paper=0.96, victory_word_width=31, victory_press_width=49)
    assert tool.is_spare_frame(spare)
    assert not tool.is_spare_frame(kill)
    assert not tool.is_spare_frame(dict(spare, victory_word_width=52))


# ---------------------------------------------------------------------------------------------------------------------
# 3: the data the checks read

def test_the_option_labels_are_the_lines_the_talk_dialogue_authors():
    tool = load_tool()
    labels = tool.option_labels()
    assert labels == ["You are not on the list.", "The bridge sees all.", "Go on. I hate the watch."]


def test_the_encounter_is_the_one_with_three_talks_to_a_spare():
    tool = load_tool()
    encounter = tool.talk_encounter()
    assert encounter["id"] == "tutorial_sailors"
    talk = encounter["talk"]
    assert talk["talks_to_spare"] == 3
    assert talk["mercy_per_option"] * talk["talks_to_spare"] == talk["mercy_to_spare"]


# ---------------------------------------------------------------------------------------------------------------------
# 4: the guards that keep a check off a rectangle the game stopped drawing

def test_the_option_geometry_guard_reads_the_live_draw_call():
    tool = load_tool()
    geom = tool.talk_geometry()
    assert geom["label_x"] == 24
    assert geom["cursor_x"] == (14, 20)
    assert geom["source"].endswith("pp_talk_draw_options")


def test_the_cursor_role_is_not_one_of_the_glyph_roles():
    tool = load_tool()
    roles = tool.roles_all()
    assert roles["text"] not in (roles["ink"], roles["paper"], roles["dim"])


# ---------------------------------------------------------------------------------------------------------------------
# 5: the launch site

def test_the_new_launch_goes_through_the_policy_and_the_idle_gate():
    with open(TOOL, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "import pp_launch" in text
    assert 'policy.gate("talk fight capture")' in text
    assert "pp_launch.start_game(" in text
    assert "policy.min_idle = 120.0" in text
    # The game is never started with a bare Popen: the helper owns the mute, the console flag and the muted line.
    assert "subprocess.Popen([exe_path" not in text


def test_the_tool_owns_its_own_three_paths():
    """A second run must not be able to replace the FIGHT capture's files, which another card signed off."""
    tool = load_tool()
    assert tool.MP4_PATH.endswith("first_fight_talk_capture.mp4")
    assert tool.VERIFY_PATH.endswith("first_fight_talk_verify.json")
    assert tool.FRAME_DIR.endswith("first_fight_talk_frames")
    assert tool.GAME_LOG.endswith("first_fight_talk_game.log")
    import capture_first_fight

    assert tool.MP4_PATH != capture_first_fight.MP4_PATH
    assert tool.VERIFY_PATH != capture_first_fight.VERIFY_PATH
    assert tool.FRAME_DIR != capture_first_fight.FRAME_DIR
    assert tool.GAME_LOG != capture_first_fight.GAME_LOG


def test_neither_this_file_nor_the_tool_carries_a_long_dash():
    """Nayil's standing rule, checked on the two artifacts this card adds."""
    for path in (TOOL, os.path.abspath(__file__)):
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        for dash in ("\u2014", "\u2013", "\u2012", "\u2015"):
            assert dash not in text, "%s carries a long dash (%r)" % (os.path.basename(path), dash)
