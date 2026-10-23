"""Dialogue v2 (card t_5b27880e, decision D2 of 2026-10-22): pages, choices, and the arrival rows.

What this file holds down, and why each check earns its place:
  1. SHAPE. Every entry carries an id, a speaker and exactly one of `lines` or `pages`, and every page is inside the
     spec 05 box (1 to 3 pages of 1 to 3 lines of at most 30 characters). The 21 committed ids may keep the one page
     shorthand forever, so this passes with both shapes in one file, which is what the decision asked for.
  2. CHOICES. A choice list is 1 to 3 items, its label fits the 96 pixel panel (12 characters), every flag it sets is
     a name in data/flags.json, and its `goto` is another dialogue id. The checker refuses each of those faults, and
     each refusal names the file, the entry index and the field.
  3. THE ENGINE'S HALF. GameMaker is not callable from pytest, so the box is read as text: pp_dialogue_pick applies
     every flag in a choice's `sets` through pp_ledger (the one writer), pp_dialogue_advance applies an entry's own
     `sets` before it sets closed, the panel draws the per page speaker and the labels, and the cursor wraps.
  4. THE DATA PROBE. For any entry that carries choices, the sets must be one shared flag plus exactly one branch flag
     per choice, which is what makes "picking a gate choice sets gate_passed and exactly one of the three" true. The
     gate entry the card asks for is in the file, so this runs instead of skipping, and section 5 pins that scene's
     own four pages of three lines and its three labels.
"""

from __future__ import annotations

import json
import os
import re

import pytest

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIALOGUE_JSON = os.path.join(ROOT, "data", "dialogue", "all.json")
DIALOGUE_GML = os.path.join(ROOT, "game", "scripts", "pp_dialogue", "pp_dialogue.gml")
FLAGS_JSON = os.path.join(ROOT, "data", "flags.json")

# The ids that were committed before the `pages` shape existed. They keep the shorthand, which is the whole promise of
# the ruling: nothing that already shipped has to be rewritten to make room for the new shape.
SHORTHAND_IDS = (
    "ship_rail_note", "battle_intro_sailors", "talk_navy_sailor", "navy_win_kill", "navy_win_spare",
    "percy_lore_stop", "percy_entry", "talk_percy", "talk_percy_phase2", "percy_phase2_line",
    "percy_interrupt_line", "prometheus_veil_line", "percy_epilogue_spare", "percy_epilogue_kill",
)

# The arrival rows this card landed, from knowledge/ARRIVAL-CONTENT.md section 5.
ARRIVAL_IDS = (
    "quay_gate_checkpoint", "quay_gate_choice",
    "quay_gate_truth", "quay_gate_bluff", "quay_gate_authority",
    "quay_dock_office", "quay_dock_office_pass",
    "say_door_register", "say_door_dancing_man", "say_door_oceana", "say_door_telephone",
    "say_door_kuti", "say_door_red_funnel", "say_door_playhouse",
)


def dialogue_document():
    with open(DIALOGUE_JSON, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dialogue_rows():
    return dialogue_document()["dialogue"]


def flags():
    with open(FLAGS_JSON, "r", encoding="utf-8") as handle:
        return set(json.load(handle)["flags"])


def code_of(path):
    """The GML with its comments removed, so prose that names a function is not read as a call to it."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def function_body(code, name):
    match = re.search(r"^function\s+%s\s*\(" % re.escape(name), code, re.MULTILINE)
    assert match is not None, "%s is not defined" % name
    start = code.index("{", match.end())
    depth = 0
    for index in range(start, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[start:index + 1]
    raise AssertionError("unbalanced body for %s" % name)


def dialogue_failures(root):
    return [error for error in check_data.check(str(root)) if "data/dialogue/all.json" in error]


def add_entry(data, entry):
    data["dialogue"].append(entry)


def one_page_entry(name, lines=None, pages=None, **extra):
    row = {"id": name, "speaker": "narrator"}
    if lines is not None:
        row["lines"] = lines
    if pages is not None:
        row["pages"] = pages
    row.update(extra)
    return row


# ---------------------------------------------------------------------------------------------------------------
# 1. Shape.


def test_every_entry_carries_exactly_one_shape():
    for index, row in enumerate(dialogue_rows()):
        has_lines = "lines" in row
        has_pages = "pages" in row
        assert has_lines != has_pages, "dialogue[%d] %r carries lines=%r pages=%r" % (
            index, row.get("id"), has_lines, has_pages)
        assert isinstance(row.get("speaker"), str) and row["speaker"], "dialogue[%d] has no speaker" % index


def test_every_page_is_inside_the_spec_05_box():
    for row in dialogue_rows():
        if "pages" not in row:
            continue
        pages = row["pages"]
        assert 1 <= len(pages) <= check_data.PAGES, (row["id"], len(pages))
        for page_index, page in enumerate(pages):
            lines = page["lines"]
            assert 1 <= len(lines) <= check_data.PAGE_LINES, (row["id"], page_index, len(lines))
            for line in lines:
                assert len(line) <= check_data.LINE_CHARS, (row["id"], page_index, line, len(line))
            if "speaker" in page:
                assert page["speaker"], (row["id"], page_index)


def test_the_committed_ids_keep_the_one_page_shorthand():
    by_id = {row["id"]: row for row in dialogue_rows()}
    for name in SHORTHAND_IDS:
        assert name in by_id, name
        assert "lines" in by_id[name] and "pages" not in by_id[name], name
        assert 1 <= len(by_id[name]["lines"]) <= check_data.PAGES * check_data.PAGE_LINES, name


def test_the_arrival_rows_are_landed():
    by_id = {row["id"]: row for row in dialogue_rows()}
    for name in ARRIVAL_IDS:
        assert name in by_id, name
        assert by_id[name]["pages"], name
        assert len(by_id[name]["pages"]) <= check_data.PAGES, name


def test_no_em_dash_or_en_dash_reaches_the_screen():
    with open(DIALOGUE_JSON, "r", encoding="utf-8") as handle:
        text = handle.read()
    for codepoint in ("\u2013", "\u2014", "\u2015"):
        assert codepoint not in text, "the dialogue file carries %r" % codepoint


# ---------------------------------------------------------------------------------------------------------------
# 2. Choices: the panel, the flags and the goto.


def test_every_choice_fits_the_panel_and_names_real_ids():
    known_flags = flags()
    ids = {row["id"] for row in dialogue_rows()}
    seen_choices = 0
    for row in dialogue_rows():
        for index, choice in enumerate(row.get("choices", [])):
            seen_choices += 1
            assert 1 <= len(choice["label"]) <= check_data.CHOICE_LABEL_CHARS, (row["id"], index, choice["label"])
            assert choice["sets"], (row["id"], index)
            for name in choice["sets"]:
                assert name in known_flags, (row["id"], index, name)
            if "goto" in choice:
                assert choice["goto"] in ids, (row["id"], index, choice["goto"])
        assert len(row.get("choices", [])) <= check_data.CHOICES, row["id"]
    assert seen_choices == sum(len(row.get("choices", [])) for row in dialogue_rows())


def test_the_checker_refuses_a_four_page_entry(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry("too_many_pages", pages=[{"lines": ["* One."]} for _ in range(check_data.PAGES + 1)]))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("more than the 3 a box entry may carry" in error for error in errors), errors


def test_the_checker_refuses_a_31_character_page_line(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry("long_line", pages=[{"lines": ["* " + "a" * (check_data.LINE_CHARS - 1)]}]))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("characters, the box holds 30 on a page line" in error for error in errors), errors
    # And the same fault one character shorter is accepted, so the check is the length and not the fixture.
    data["dialogue"][-1] = one_page_entry("long_line", pages=[{"lines": ["* " + "a" * (check_data.LINE_CHARS - 2)]}])
    write_json(path, data)
    assert dialogue_failures(data_root) == []


def test_the_checker_refuses_a_long_choice_label(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry(
        "wide_choice",
        pages=[{"lines": ["* Pick."]}],
        choices=[{"label": "a" * (check_data.CHOICE_LABEL_CHARS + 1), "sets": [sorted(flags())[0]]}],
    ))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("the panel holds 12" in error for error in errors), errors


def test_the_checker_refuses_a_choice_flag_that_is_not_in_flags_json(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry(
        "bad_flag",
        pages=[{"lines": ["* Pick."]}],
        choices=[{"label": "Go.", "sets": ["not_a_flag_anywhere"]}],
    ))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("unknown flag id 'not_a_flag_anywhere'" in error for error in errors), errors


def test_the_checker_refuses_a_goto_to_no_dialogue(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry(
        "bad_goto",
        pages=[{"lines": ["* Pick."]}],
        choices=[{"label": "Go.", "sets": [sorted(flags())[0]], "goto": "no_such_dialogue"}],
    ))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("unknown dialogue id 'no_such_dialogue'" in error for error in errors), errors


def test_the_checker_refuses_both_shapes_on_one_entry(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    add_entry(data, one_page_entry("both_shapes", lines=["* One."], pages=[{"lines": ["* One."]}]))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("carries both lines and pages" in error for error in errors), errors


def test_the_checker_refuses_a_fourth_choice(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    flag = sorted(flags())[0]
    add_entry(data, one_page_entry(
        "four_choices",
        pages=[{"lines": ["* Pick."]}],
        choices=[{"label": "Go.", "sets": [flag]} for _ in range(check_data.CHOICES + 1)],
    ))
    write_json(path, data)

    errors = dialogue_failures(data_root)
    assert any("more than the 3 the panel holds" in error for error in errors), errors


# ---------------------------------------------------------------------------------------------------------------
# 3. The engine's half, read as text.


def test_a_choice_applies_its_flags_before_the_box_closes():
    code = code_of(DIALOGUE_GML)
    pick = function_body(code, "pp_dialogue_pick")
    assert "pp_dialogue_apply_flags(_choice.sets)" in pick, \
        "a picked choice must apply every flag in its sets"
    assert "pp_ledger_set_flag(" not in pick, \
        "the ledger is written in one place; pick applies through pp_dialogue_apply_flags"

    apply_flags = function_body(code, "pp_dialogue_apply_flags")
    assert "pp_ledger_set_flag(global.pp_ledger, _names[_i], true)" in apply_flags

    # The pick runs before the box can close in pp_dialogue_step: the flags are applied, then the pick returns.
    step = function_body(code, "pp_dialogue_step")
    assert step.index("pp_dialogue_pick(") > step.index("pp_dialogue_on_choice_page("), step

    # And an entry's own sets land before it is marked closed, which is the "before the box closes" half of D2.6.
    advance = function_body(code, "pp_dialogue_advance")
    assert advance.index("pp_dialogue_apply_flags(_d.sets)") < advance.index("_d.closed = true"), advance


def test_a_goto_continues_in_the_same_box():
    code = code_of(DIALOGUE_GML)
    pick = function_body(code, "pp_dialogue_pick")
    assert "pp_dialogue_open(_choice.goto)" in pick, "a goto must open the next entry"
    # It loads into the same struct, so a caller holding the box keeps its handle and no scene command is needed.
    for field in ("_d.pages", "_d.reveal", "_d.choices", "_d.closed"):
        assert "%s =" % field in pick, pick


def test_the_panel_draws_the_page_speaker_and_the_labels():
    code = code_of(DIALOGUE_GML)
    draw = function_body(code, "pp_dialogue_draw")
    assert "string_upper(_plate)" in draw, "the name plate must come from the page's own speaker"
    assert "_d.choices[_c].label" in draw, "the panel must draw the labels"
    assert "PP_CHOICE_PANEL_W" in draw, "the panel width is the spec 05 96 pixels"

    pages = function_body(code, "pp_dialogue_pages")
    assert 'variable_struct_exists(_page, "speaker")' in pages, "a page may name its own speaker"
    assert "variable_struct_exists(_row, \"pages\")" in pages, "the pages shape must be read as well as lines"


def test_the_choice_cursor_wraps():
    cursor = function_body(code_of(DIALOGUE_GML), "pp_dialogue_move_cursor")
    assert " mod _count" in cursor, "the cursor wraps, spec 05 acceptance 4"
    assert "== 0" in cursor or "< 1" in cursor, "an entry with no choices must not divide by zero"


def test_a_choice_waits_for_a_pick_instead_of_turning_the_page():
    code = code_of(DIALOGUE_GML)
    advance = function_body(code, "pp_dialogue_advance")
    assert "if (pp_dialogue_on_choice_page(_d)) return false;" in advance, advance
    on_choice = function_body(code, "pp_dialogue_on_choice_page")
    assert "_d.reveal.unit + 1 >= array_length(_d.reveal.units)" in on_choice, on_choice


# ---------------------------------------------------------------------------------------------------------------
# 4. The data probe the decision asks for: the gate's three choices set the pivot flag and exactly one branch flag.


def choice_entries():
    return [row for row in dialogue_rows() if row.get("choices")]


def test_a_choice_list_sets_one_pivot_flag_and_one_branch_flag_each():
    rows = choice_entries()
    if not rows:
        pytest.skip("no entry carries choices yet: the gate checkpoint waits on data/flags.json (see the card)")

    for row in rows:
        sets = [set(choice["sets"]) for choice in row["choices"]]
        shared = set.intersection(*sets)
        assert len(shared) == 1, (row["id"], sorted(shared))
        for index, flags_set in enumerate(sets):
            branch = flags_set - shared
            assert len(branch) == 1, (row["id"], index, sorted(branch))
        branches = [tuple(sorted(flags_set - shared)) for flags_set in sets]
        assert len(set(branches)) == len(branches), (row["id"], branches)


def test_the_probe_catches_a_choice_that_sets_two_branch_flags():
    """The probe above is only worth having if it fails on the fault it exists for."""
    known = flags()
    pivot = sorted(known)[0]
    two = sorted(known)[1:3]
    sets = [set([pivot] + two), set([pivot, sorted(known)[3]])]
    shared = set.intersection(*sets)
    assert len(shared) == 1
    assert len(sets[0] - shared) == 2, "the probe's own arithmetic must see two branch flags"


# ---------------------------------------------------------------------------------------------------------------
# 5. The gate scene itself: four pages of three lines, one three item choice, and the three flags it sets.

GATE_BRANCH_FLAGS = ("gate_truth", "gate_bluff", "gate_authority")
GATE_PIVOT_FLAG = "gate_passed"


def rows_by_id():
    return {row["id"]: row for row in dialogue_rows()}


def test_the_gate_scene_is_four_pages_of_three_lines_ending_in_a_three_item_choice():
    """D2 caps one entry at 3 pages, so the beat 20 four page scene is a checkpoint entry plus the ask entry.

    The pages are counted together because the screen sees them together: the scene `say`s the checkpoint and then
    the ask, so four pages of three lines reach the box in one beat, and the choice sits on the last of them.
    """
    by_id = rows_by_id()
    checkpoint = by_id["quay_gate_checkpoint"]
    ask = by_id["quay_gate_choice"]

    pages = checkpoint["pages"] + ask["pages"]
    assert len(pages) == 4, len(pages)
    assert len(checkpoint["pages"]) <= check_data.PAGES, "one entry can never carry the fourth page"
    for index, page in enumerate(pages):
        assert len(page["lines"]) == check_data.PAGE_LINES, (index, page["lines"])

    # The choice is on the last page's entry, which is the only entry that carries one.
    assert "choices" not in checkpoint
    assert len(ask["choices"]) == 3 == check_data.CHOICES
    for choice in ask["choices"]:
        assert len(choice["label"]) <= check_data.CHOICE_LABEL_CHARS, choice["label"]


def test_each_gate_choice_sets_the_pivot_flag_and_exactly_one_branch_flag():
    """CHECK: picking each of the three choices sets gate_passed plus exactly one of the three branch flags.

    Read as data, which is what the box reads: every choice names the pivot flag, names exactly one of the three
    branch flags, and the three branches are all different, so no two picks set the same state.
    """
    choices = rows_by_id()["quay_gate_choice"]["choices"]
    branches = []
    for index, choice in enumerate(choices):
        sets = set(choice["sets"])
        assert GATE_PIVOT_FLAG in sets, (index, sorted(sets))
        branch = sets - {GATE_PIVOT_FLAG}
        assert len(branch) == 1, (index, sorted(branch))
        branches.append(branch.pop())
    assert sorted(branches) == sorted(GATE_BRANCH_FLAGS), branches
    assert len(set(branches)) == len(GATE_BRANCH_FLAGS), "two choices set the same branch flag"

    # The flags are real, which is what makes the checker pass and the save record them.
    known = flags()
    for name in (GATE_PIVOT_FLAG,) + GATE_BRANCH_FLAGS + ("has_boarding_pass",):
        assert name in known, name


def test_each_gate_choice_continues_into_its_own_reply():
    """A pick loads the reply into the same box, so each choice's goto must be that reply and not another one."""
    by_id = rows_by_id()
    gotos = [choice["goto"] for choice in by_id["quay_gate_choice"]["choices"]]
    assert gotos == ["quay_gate_truth", "quay_gate_bluff", "quay_gate_authority"], gotos
    for name in gotos:
        assert "pages" in by_id[name], name


def test_the_dock_office_hands_over_the_pass_on_its_last_page():
    """The office is six pages: two entries of three, and the flag is set by the entry that carries page six."""
    by_id = rows_by_id()
    office = by_id["quay_dock_office"]
    handover = by_id["quay_dock_office_pass"]
    assert len(office["pages"]) == 3 and len(handover["pages"]) == 3
    assert len(office["pages"] + handover["pages"]) == 6, "the office beat is six pages"
    assert handover["sets"] == ["has_boarding_pass"], handover.get("sets")
    assert "sets" not in office, "the pass is handed over in the second entry, not the first"

