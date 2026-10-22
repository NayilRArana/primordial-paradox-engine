"""TEXT-REVEAL-1: prove the character reveal has exactly one implementation and that both layouts use it.

What this file can honestly prove from pytest: the source text. GameMaker is not callable from the Python suite, so
this file does not pretend to run the machine. It proves the property the card is about at the level where a second
implementation would appear, which is the level where the defect lived in the first place (two modules, two loops).

1. TIMING FINGERPRINT. Everything that decides WHEN a character appears (a per character step count, a punctuation
   hold, the blip interval) is named in exactly one module: game/scripts/pp_text/pp_text.gml. If a layout grows its own
   reveal again, its file names one of those tokens and this file fails with the file named.
2. WIRING. Both layouts hand their reveal to the one machine: pp_dialogue_step and pp_text_board_step call
   pp_text_reveal_step, both build their items with pp_text_items (so the same input is parsed once, in one order, with
   one pause table), and neither keeps reveal state of its own.
3. SELF CHECK. The auditor is run over a synthetic second reveal, so a broken auditor cannot pass this file silently.
4. THE CRAWL (card TEXT-REVEAL-2). pp_title is the third layout, not a third revealer: its crawl is audited by name
   for the same timing tokens, it hands the machine its own numbers (speed, gap, blip interval) as settings, and the
   beat pause is the machine's gap at a unit end, never an item hold.
"""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = "game/scripts/pp_text/pp_text.gml"
DIALOGUE = "game/scripts/pp_dialogue/pp_dialogue.gml"
BATTLE = "game/scripts/pp_battle_text/pp_battle_text.gml"
TITLE = "game/scripts/pp_title/pp_title.gml"
# Every layout the audit speaks for, by name, so a renamed or deleted layout fails here instead of quietly leaving the
# audit with one less module to read.
AUDITED_LAYOUTS = (DIALOGUE, BATTLE, TITLE)

# A token here means: this module decides when a character appears. pp_config defines the pause macros as values, which
# is content, so a #macro line is not counted as reveal logic.
TIMING_TOKENS = {
    "PP_TEXT_STEPS_SLOW": "a slow per character step count",
    "PP_TEXT_STEPS_FAST": "a fast per character step count",
    "PP_TEXT_PAUSE_STOP": "a full stop, question or exclamation hold",
    "PP_TEXT_PAUSE_COMMA": "a comma hold",
    "PP_TEXT_BLIP_EVERY": "a blip interval",
    "PP_TEXT_STEPS_PER_CHAR": "a per character step count of its own",
}

REVEAL_FIELDS = ("revealed", "acc", "wait", "steps")
# The fields the old crawl kept for itself: a per line character count, a per character timer, its own pause, and its
# own blip count. A layout may read the machine's `revealed`, `acc` and `wait`; it may not own a counter of its own.
CRAWL_FIELDS = ("chars", "timer", "pause", "line_steps", "blips", "revealed", "acc")
CRAWL_ASSIGN = re.compile(r"\.\s*(%s)\s*(=|\+=|-=)" % "|".join(CRAWL_FIELDS))


def gml_files():
    found = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
        for name in filenames:
            if name.endswith(".gml"):
                found.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/"))
    return sorted(found)


def code_of(path):
    """The file with its comments removed, so prose that names a macro is not read as a use of it."""
    with open(os.path.join(ROOT, path), "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        code = line if cut == -1 else line[:cut]
        if code.strip().startswith("#macro"):
            code = ""
        lines.append(code)
    return "\n".join(lines)


def timing_logic(code):
    """The timing tokens a piece of GML decides with, as (token, why) pairs."""
    return [(token, why) for token, why in TIMING_TOKENS.items() if token in code]


def function_body(code, name):
    """The brace balanced body of one function, or an empty string when it is not defined here."""
    match = re.search(r"^function\s+%s\s*\(" % re.escape(name), code, re.MULTILINE)
    if match is None:
        return ""
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


def test_the_reveal_timing_exists_in_one_module_only():
    """One revealer for the game. A second one fails here, by file name and token."""
    offenders = []
    for path in gml_files():
        if path == OWNER:
            continue
        for token, why in timing_logic(code_of(path)):
            offenders.append("%s decides %s (%s)" % (path, why, token))
    assert offenders == [], "a second reveal implementation: %s" % offenders


def test_the_auditor_catches_a_second_reveal():
    """The audit above must fail on the defect it exists for, not pass because it reads nothing."""
    second_reveal = "\n".join([
        "function pp_text_board_step(_board, _fast) {",
        "    _board.timer += 1;",
        "    if (_board.timer >= PP_TEXT_STEPS_PER_CHAR) {",
        "        _board.revealed += 1;",
        "        if (_board.lines[_board.index] == \".\") _board.pause = PP_TEXT_PAUSE_STOP;",
        "    }",
        "}",
    ])
    found = [token for token, _why in timing_logic(second_reveal)]
    assert "PP_TEXT_STEPS_PER_CHAR" in found
    assert "PP_TEXT_PAUSE_STOP" in found

    one_machine = "\n".join([
        "function pp_dialogue_step(_d) {",
        "    pp_text_reveal_step(_d.reveal, pp_action(\"confirm\"));",
        "}",
    ])
    assert timing_logic(one_machine) == []

    # The same self check for the crawl audit: a crawl that counts characters and holds its own pause is caught by
    # the field scan, and a crawl that only reads the machine's count is not.
    counting = "    _s.crawl.chars += 1;\n    _c.timer = 0;\n    _c.pause = 72;"
    assert CRAWL_ASSIGN.search(counting), "the crawl counter scan must catch a layout counting its own characters"
    assert not CRAWL_ASSIGN.search("    var _budget = _c.reveal.revealed;"), \
        "reading the machine's revealed count is not owning a reveal"


def test_both_layouts_step_the_one_machine():
    """Each layout's step, skip and done must be a call into pp_text, not a loop of its own."""
    dialogue = function_body(code_of("game/scripts/pp_dialogue/pp_dialogue.gml"), "pp_dialogue_step")
    battle = function_body(code_of("game/scripts/pp_battle_text/pp_battle_text.gml"), "pp_text_board_step")
    assert "pp_text_reveal_step(" in dialogue, "the dialogue box must step the shared reveal"
    assert "pp_text_reveal_step(" in battle, "the battle board must step the shared reveal"

    skip = function_body(code_of("game/scripts/pp_battle_text/pp_battle_text.gml"), "pp_text_board_skip_line")
    assert "pp_text_reveal_complete(" in skip and "pp_text_reveal_next(" in skip

    advance = function_body(code_of("game/scripts/pp_dialogue/pp_dialogue.gml"), "pp_dialogue_advance")
    assert "pp_text_reveal_complete(" in advance and "pp_text_reveal_next(" in advance

    done = function_body(code_of("game/scripts/pp_battle_text/pp_battle_text.gml"), "pp_text_board_done")
    assert "pp_text_reveal_done(" in done


def test_neither_layout_keeps_reveal_state_of_its_own():
    """A layout may read the machine's fields to draw. It may not own a reveal counter, a hold or an accumulator."""
    assignments = re.compile(r"\.\s*(%s)\s*(=|\+=|-=)" % "|".join(REVEAL_FIELDS))
    offenders = []
    for path in ("game/scripts/pp_dialogue/pp_dialogue.gml", "game/scripts/pp_battle_text/pp_battle_text.gml"):
        for line_number, line in enumerate(code_of(path).split("\n"), start=1):
            if assignments.search(line):
                offenders.append("%s:%d %s" % (path, line_number, line.strip()))
    assert offenders == [], "a layout is running its own reveal: %s" % offenders


def test_both_layouts_build_their_items_with_the_one_parser():
    """Same input, same order: one item parser, so a pause lands at the same item in either layout."""
    parser_owners = []
    for path in gml_files():
        if "function pp_text_items(" in code_of(path):
            parser_owners.append(path)
    assert parser_owners == [OWNER], "one item parser, not %s" % parser_owners

    rows = function_body(code_of("game/scripts/pp_dialogue/pp_dialogue.gml"), "pp_dialogue_rows")
    board = function_body(code_of("game/scripts/pp_battle_text/pp_battle_text.gml"), "pp_text_board")
    assert "pp_text_items(" in rows, "the dialogue box must parse its text with the shared parser"
    assert "pp_text_items(" in board, "the battle board must parse its text with the shared parser"


def test_both_layouts_begin_the_same_machine():
    """The reveal struct has exactly one constructor, and both layouts call it."""
    owners = [path for path in gml_files() if "function pp_text_reveal_begin(" in code_of(path)]
    assert owners == [OWNER], "one reveal constructor, not %s" % owners

    open_body = function_body(code_of("game/scripts/pp_dialogue/pp_dialogue.gml"), "pp_dialogue_open")
    board_body = function_body(code_of("game/scripts/pp_battle_text/pp_battle_text.gml"), "pp_text_board")
    assert "pp_text_reveal_begin(" in open_body
    assert "pp_text_reveal_begin(" in board_body


def test_punctuation_pauses_are_the_spec_numbers_and_live_in_config():
    """Spec 05 rule 2: 8 steps after a full stop, question or exclamation, 3 after a comma. One definition, unchanged."""
    config = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
    with open(config, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    values = dict(re.findall(r"#macro\s+(PP_TEXT_PAUSE_[A-Z]+)\s+(\d+)", text))
    assert values == {"PP_TEXT_PAUSE_STOP": "8", "PP_TEXT_PAUSE_COMMA": "3"}, values


def test_the_crawl_is_audited_by_name():
    """The third layout is pp_title, and the audit speaks for it by name rather than by whatever the walk finds."""
    files = gml_files()
    for path in AUDITED_LAYOUTS:
        assert path in files, "%s is audited by name but is not a GML file under game/" % path
        found = timing_logic(code_of(path))
        assert found == [], "%s decides a reveal timing of its own: %s" % (path, found)


def test_the_crawl_steps_the_one_machine_and_keeps_no_counter():
    """The crawl is a layout: it steps, skips and asks done of pp_text, and owns no character, timer, pause or blip."""
    crawl = code_of(TITLE)
    step = function_body(crawl, "pp_title_crawl_step")
    assert "pp_text_reveal_step(" in step, "the crawl must step the shared reveal"

    new = function_body(crawl, "pp_title_crawl_new")
    assert "pp_text_reveal_begin(" in new, "the crawl must begin the shared reveal"
    assert "pp_text_items(" in new, "the crawl must parse its rows with the shared parser"

    finish = function_body(crawl, "pp_title_crawl_finish")
    assert "pp_text_reveal_finish(" in finish, "the skip must be the machine's own jump to the end"

    done = function_body(crawl, "pp_title_crawl_done")
    assert "pp_text_reveal_done(" in done, "the crawl must ask the machine whether it is finished"

    intro = function_body(crawl, "pp_title_step_intro")
    assert "pp_title_crawl_step(" in intro and "pp_title_crawl_finish(" in intro

    offenders = []
    for line_number, line in enumerate(crawl.split("\n"), start=1):
        if CRAWL_ASSIGN.search(line):
            offenders.append("%s:%d %s" % (TITLE, line_number, line.strip()))
    assert offenders == [], "the crawl is running its own reveal: %s" % offenders


def test_the_beat_pause_is_the_machines_gap_and_the_blip_is_a_setting():
    """A beat is a unit, so its pause is the gap; the three timings are fields the layout sets, not macros it reads."""
    machine = code_of(OWNER)
    begin = function_body(machine, "pp_text_reveal_begin")
    for field in ("speed:", "gap:", "blip:"):
        assert field in begin, "the reveal struct has no %s to set" % field

    timing = function_body(machine, "pp_text_reveal_timing")
    for field in ("_rv.speed", "_rv.gap", "_rv.blip"):
        assert field in timing, "the timing setter does not carry %s" % field

    step = function_body(machine, "pp_text_reveal_step")
    assert "max(_rv.wait, _rv.gap)" in step, "the gap must be the hold taken at the end of a unit"
    assert "_rv.revealed mod _rv.blip" in step, "the blip interval must be read from the struct"

    crawl = code_of(TITLE)
    assert "{pause:" not in crawl, "the beat pause must be the machine's gap, not a {pause:N} item hold"
    assert "blip_every_chars" in crawl, "the blip interval must still come from data/title_timing.json"
    assert "pp_text_reveal_timing(" in function_body(crawl, "pp_title_crawl_new"), \
        "the crawl must hand its own speed, gap and blip interval to the machine"
