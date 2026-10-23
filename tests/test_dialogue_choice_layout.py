"""The choice rows (card t_01432e14): a choice page replaces its rows, and the layout cannot cover them.

Card t_01432e14. The dialogue box was correct on a plain page and wrong on a page that offered choices: the 96 pixel
panel sat at x 140..240 over prompt rows whose ink ran to x 191, so 3 to 6 characters of every row were covered and a
row was cut mid phrase. There are only 8 pixels between the third row's cell and the box's bottom edge and the panel
needs 3 rows of 10, so this was a layout ruling, not a nudge. Spec 05 now rules option (a): the choice labels take the
rows' place, and the three things below are what keep that ruling true.

  1. GEOMETRY. The choice rows use the text area's own three rows: the 6 pixel cursor in column 0, the label in column
     1, and the label starts at x 24 with room for 27 columns to x 240. Every number is read from pp_config, so a moved
     macro fails here instead of on a screen.
  2. THE ENGINE. `pp_dialogue_draw` returns from the choice branch before the row loop, so no page ever draws a row and
     a label into the same cell. pytest cannot run GML, so this is pinned as the order of the draw function's own body.
  3. THE PIXELS. `tools/preview_dialogue_box.py` composes the real gate page through the same numbers and measures the
     ink. Its overlap test (`layout_conflicts`) is exercised here with a fabricated pair, so "nothing overlaps" is a
     check with a failing case, not a hope: hand it a row and a label in the same cell and it must refuse.
"""

from __future__ import annotations

import os
import re

import check_data
import preview_dialogue_box as preview

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
DIALOGUE_GML = os.path.join(ROOT, "game", "scripts", "pp_dialogue", "pp_dialogue.gml")


def code_of(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def function_body(text, name):
    """The brace balanced body of `function name(...)`, read as text the way the other dialogue tests do it."""
    start = text.index("function %s(" % name)
    open_brace = text.index("{", start)
    depth = 0
    index = open_brace
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
        index += 1
    raise AssertionError("function %s is not brace balanced" % name)


def macros():
    return preview.read_macros(ROOT)


# ---------------------------------------------------------------------------------------------------------------
# 1. The geometry, read from the engine's own numbers.


def test_the_choice_rows_fit_the_text_area():
    config = macros()
    for need in ("PP_TEXT_X", "PP_TEXT_Y", "PP_TEXT_RIGHT", "PP_TEXT_LINE_H", "PP_TEXT_ROWS",
                 "PP_CHOICE_ARROW_X", "PP_CHOICE_ARROW_W", "PP_CHOICE_LABEL_X"):
        assert need in config, "%s must be a literal #macro so the preview and this test can read it" % need

    # The cursor sits in the first cell of the text area and the label starts in the second: neither can reach the other.
    assert config["PP_CHOICE_ARROW_X"] == config["PP_TEXT_X"]
    assert config["PP_CHOICE_ARROW_X"] + config["PP_CHOICE_ARROW_W"] <= config["PP_CHOICE_LABEL_X"]

    # The label column is a whole number of 8 pixel cells from column 1 to the text area's own right edge.
    room = config["PP_TEXT_RIGHT"] - config["PP_CHOICE_LABEL_X"]
    assert room % 8 == 0, "a label column must be whole glyph cells: %d pixels" % room
    assert room // 8 == 27, "24 + 27 * 8 = 240, the text area's right edge"

    # The authored label limit is well inside what the row can hold, which is what makes 12 a decision and not geometry.
    assert check_data.CHOICE_LABEL_CHARS * 8 <= room


def test_the_covered_panel_is_gone_from_the_numbers():
    config = macros()
    assert "PP_CHOICE_PANEL_W" not in config, "the 96 pixel panel is what the card removed"
    assert "PP_CHOICE_GAP" not in config, "the panel's gap went with the panel"


def test_the_portrait_promise_and_the_code_agree():
    """Card t_01432e14: spec 05 promised a 48x48 bust at (16,120) that no code path drew, and pp_config defined three
    macros for it. The ruling is the other branch: the slice has no portrait, and the spec says so."""
    config = macros()
    source = code_of(CONFIG_GML)
    assert not re.search(r"#macro\s+PP_PORTRAIT_", source), "the portrait macros must go with the portrait"
    assert "PP_PORTRAIT" not in config

    draw = function_body(code_of(DIALOGUE_GML), "pp_dialogue_draw")
    assert "portrait" not in draw.lower(), "the box draws no portrait frame, because it has none to draw"

    with open(os.path.join(ROOT, "specs", "05-dialogue.md"), "r", encoding="utf-8") as handle:
        spec = handle.read()
    assert "Portrait: none." in spec, "the spec must state that this slice draws no portrait"
    assert "PP_PORTRAIT" not in spec, "the spec must not name geometry the code does not define"


# ---------------------------------------------------------------------------------------------------------------
# 2. The engine draws one or the other, never both.


def test_a_choice_page_returns_before_it_draws_a_row():
    draw = function_body(code_of(DIALOGUE_GML), "pp_dialogue_draw")
    assert "PP_CHOICE_LABEL_X" in draw, "the labels must be drawn at the choice column"
    assert "PP_CHOICE_ARROW_X" in draw, "the cursor must be drawn in the first text column"

    choice = draw.index("PP_CHOICE_LABEL_X")
    rows = draw.index("pp_text_visible(")
    assert choice < rows, "the choice branch must come before the rows, so the rows can be skipped"
    between = draw[choice:rows]
    assert "return;" in between, "the choice branch returns: the rows are not drawn first and painted over"


# ---------------------------------------------------------------------------------------------------------------
# 3. The pixels: the real page composes clean, and the overlap test has a failing case.


def test_the_gate_choice_page_composes_with_the_rows_replaced():
    config = macros()
    frame, report = preview.compose(ROOT, "quay_gate_choice", 0, config)
    assert frame.size == (config["PP_FRAME_W"], config["PP_FRAME_H"])
    assert report["rows"] == [], "a choice page draws no dialogue row"
    assert report["menu"] is not None
    assert len(report["menu"]["labels"]) == 3
    assert len(report["menu"]["rows_replaced"]) == 3, "the prompt is replaced, not lost by accident"
    assert preview.check(report, config) == []


def test_the_overlap_this_card_fixed_is_now_a_failure():
    config = macros()
    row = {"text": '* "No pass, no gate."', "x0": config["PP_TEXT_X"], "x1": 192,
           "y0": config["PP_TEXT_Y"], "y1": config["PP_TEXT_Y"] + config["PP_TEXT_LINE_H"]}
    label = {"label": "No pass.", "x0": 140, "x1": 140 + 8 * 8,
             "y0": config["PP_TEXT_Y"], "y1": config["PP_TEXT_Y"] + config["PP_TEXT_LINE_H"]}
    errors = preview.layout_conflicts("quay_gate_choice", 0, [row], [label], None)
    assert errors, "a label at x 140 over a row that reaches x 191 is exactly the fault this card fixed"
    assert "choice label" in errors[0]

    # The cursor counts too: it shares the first cell with the row's first character.
    cursor = {"x0": config["PP_CHOICE_ARROW_X"], "y0": config["PP_TEXT_Y"] + 1,
              "x1": config["PP_CHOICE_ARROW_X"] + config["PP_CHOICE_ARROW_W"],
              "y1": config["PP_TEXT_Y"] + 1 + config["PP_CHOICE_ARROW_W"]}
    assert preview.layout_conflicts("quay_gate_choice", 0, [row], [], cursor)
    # A row in another band, or a label to the right of the row's ink, is not an overlap.
    assert preview.layout_conflicts("quay_gate_choice", 0, [row], [], None) == []
    assert preview.layout_conflicts("quay_gate_choice", 0, [], [label], None) == []
