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
import sys

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


def test_the_bust_geometry_and_the_art_agree():
    """Card t_4d6b0f4b: the bust is real now, and the spec, the numbers, the sheets and the data all say the same thing.

    The parent card t_01432e14 removed a portrait the code promised and never drew, and this card is where it came back
    with art behind it. So the assertion is no longer "the spec says none": it is that the spec's numbers are the
    macros' numbers, that the sheets match those numbers, and that every portrait in the data names a sheet that exists.
    """
    config = macros()
    for need in ("PP_PORTRAIT_X", "PP_PORTRAIT_Y", "PP_PORTRAIT_SIZE", "PP_PLATE_X", "PP_PLATE_W", "PP_PLATE_BUST_X"):
        assert need in config, "%s must be a literal #macro so the preview and this test can read it" % need

    # 120 + 48 = 168: the bust's last row is the pixel above the box's top edge, and it never enters the box.
    assert config["PP_PORTRAIT_Y"] + config["PP_PORTRAIT_SIZE"] == config["PP_BOX_Y"]
    # The bust starts on the text area's own inset, so the two share one left margin without sharing a pixel.
    assert config["PP_PORTRAIT_X"] == config["PP_TEXT_X"]
    # The plate starts where the bust ends, so the one other thing on the box's top border cannot overlap it.
    assert config["PP_PLATE_BUST_X"] >= config["PP_PORTRAIT_X"] + config["PP_PORTRAIT_SIZE"]

    draw = function_body(code_of(DIALOGUE_GML), "pp_dialogue_draw")
    assert "spr_pp_portrait_" in draw, "the box must draw the bust through the one sheet index"
    assert "pp_art_info(" in draw, "the bust goes through pp_art_info, the same path as the window and the font"
    assert "_page_data.portrait" in draw, "the bust is the page's, so a page that names none draws none"
    assert draw.index("spr_pp_portrait_") < draw.index("PP_PLATE_BUST_X"), \
        "the bust is drawn first and the plate moves out of its way"
    assert "draw_rectangle(PP_PORTRAIT" not in draw, \
        "no rectangle stands in for a bust: an empty frame is the defect the parent card removed"

    with open(os.path.join(ROOT, "specs", "05-dialogue.md"), "r", encoding="utf-8") as handle:
        spec = handle.read()
    assert "Portrait: none." not in spec, "the spec states the bust's real numbers now"
    assert "48x48 bust at (16, 120)" in spec
    # The spec names the numbers, the macros define them: the two must not drift, so the spec's own plate x is here.
    assert "at x %d with one" % config["PP_PLATE_BUST_X"] in spec
    assert "the box's own top edge" in spec


def test_every_bust_sheet_is_the_geometry_and_the_palette():
    """Each sheet on disk: 48x48, one frame, a 1 pixel frame ring, 4 entries, and 3 colours in any 8x8 tile."""
    import json
    from PIL import Image

    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        legal = {entry["hex"].lower() for entry in json.load(handle)["entries"]}

    chars = os.path.join(ROOT, "game", "sprites_src", "chars")
    sheets = sorted(name for name in os.listdir(chars)
                    if name.startswith("spr_pp_portrait_") and name.endswith(".png"))
    assert len(sheets) >= 3, "the three speakers with a bust have a sheet each"

    for name in sheets:
        path = os.path.join(chars, name)
        image = Image.open(path).convert("RGBA")
        assert image.size == (48, 48), "%s is %s, the geometry is 48x48" % (name, image.size)
        sidecar = json.load(open(path[:-4] + ".json", encoding="utf-8"))
        assert sidecar["name"] == name[:-4]
        assert (sidecar["frame_w"], sidecar["frame_h"], sidecar["frames"]) == (48, 48, 1)

        pixels = image.load()
        # The 1 pixel frame is drawn into the sheet, and it is one entry all the way round.
        ring = set()
        for index in range(48):
            ring.add(pixels[index, 0])
            ring.add(pixels[index, 47])
            ring.add(pixels[0, index])
            ring.add(pixels[47, index])
        assert len(ring) == 1, "%s's frame ring is not one colour: %r" % (name, ring)
        assert all(pixel[3] == 255 for pixel in ring), "the frame ring is opaque"

        # Nothing transparent inside the frame: a framed portrait, not a hole in the level.
        inside = {pixels[x, y] for y in range(1, 47) for x in range(1, 47)}
        assert all(pixel[3] == 255 for pixel in inside), "%s leaves the level visible through its own frame" % name

        colours = {pixel[:3] for pixel in inside}
        assert len(colours) <= 4, "%s spends %d colours, a bust may spend 4" % (name, len(colours))
        for colour in colours:
            hexed = "#%02x%02x%02x" % colour
            assert hexed in legal, "%s carries %s, which is not a data/nes_palette.json entry" % (name, hexed)

        # The tile budget: a sprite tile is 3 opaque colours plus transparency.
        for ty in range(6):
            for tx in range(6):
                seen = {pixels[x, y][:3] for y in range(ty * 8, ty * 8 + 8) for x in range(tx * 8, tx * 8 + 8)}
                assert len(seen) <= 3, "%s tile %d,%d carries %d colours" % (name, tx, ty, len(seen))

    # And every portrait the data names resolves to one of those sheets.
    with open(os.path.join(ROOT, "data", "dialogue", "all.json"), "r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    named = set()
    for row in document["dialogue"]:
        if row.get("portrait"):
            named.add(row["portrait"])
        for page in row.get("pages", []):
            if page.get("portrait"):
                named.add(page["portrait"])
    assert named, "the slice's three portrait speakers carry a bust"
    assert named <= {name[len("spr_pp_portrait_"):-4] for name in sheets}, \
        "every named bust has a sheet: %r" % sorted(named)


def test_the_checker_refuses_a_bust_that_is_not_there():
    """The data half of the same rule: a name with no sheet, and a narrator with a bust, are data errors."""
    checker = check_data.Checker(ROOT)
    checker.check_dialogue_portrait({"speaker": "guard", "portrait": "nobody"}, "dialogue[0]", "data/dialogue/all.json")
    assert checker.errors, "a portrait with no sheet must be refused"
    assert "spr_pp_portrait_nobody.png" in checker.errors[0]

    narrator = check_data.Checker(ROOT)
    narrator.check_dialogue_portrait({"speaker": "narrator", "portrait": "guard"}, "dialogue[0]",
                                     "data/dialogue/all.json")
    assert narrator.errors and "narrator" in narrator.errors[0]

    real = check_data.Checker(ROOT)
    real.check_dialogue_portrait({"speaker": "guard", "portrait": "guard"}, "dialogue[0]", "data/dialogue/all.json")
    empty = check_data.Checker(ROOT)
    empty.check_dialogue_portrait({"speaker": "guard", "portrait": ""}, "dialogue[0]", "data/dialogue/all.json")
    assert real.errors == [] and empty.errors == [], "a real bust and an explicit nobody are both legal"


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


# ---------------------------------------------------------------------------------------------------------------
# 4. The bust: the page that carries one composes it, and the geometry that keeps it off the text has a failing case.


def test_the_gate_choice_page_composes_with_its_bust():
    """quay_gate_choice is the guard's page, so the composed frame carries his bust AND his plate, and no overlap."""
    config = macros()
    frame, report = preview.compose(ROOT, "quay_gate_choice", 0, config)
    bust = report["portrait"]
    assert bust is not None, "the guard's page carries a bust"
    assert (bust["x0"], bust["y0"], bust["w"], bust["h"]) == (config["PP_PORTRAIT_X"], config["PP_PORTRAIT_Y"], 48, 48)
    assert bust["y1"] == config["PP_BOX_Y"], "the bust's last row is the pixel above the box"
    plate = report["plate"]
    assert plate is not None and plate["x0"] >= bust["x1"], "the plate starts where the bust ends"
    assert preview.check(report, config) == []

    # And the pixels really are there, in the NES entries the guard's sheet is drawn from.
    pixels = frame.load()
    assert pixels[config["PP_PORTRAIT_X"], config["PP_PORTRAIT_Y"]][3] == 255, "the bust's own top left pixel is drawn"
    assert pixels[config["PP_PORTRAIT_X"] + 1, config["PP_PORTRAIT_Y"] + 1][3] == 255, "the bust is opaque inside its frame"


def test_a_page_with_no_bust_draws_none():
    """quay_gate_checkpoint is a narrator entry whose second page is the guard: page 0 has no bust, and no plate shift."""
    config = macros()
    frame, report = preview.compose(ROOT, "quay_gate_checkpoint", 0, config)
    assert report["portrait"] is None, "the narrator's page draws no bust"
    assert preview.check(report, config) == []


def test_a_bust_drawn_over_the_text_area_is_a_failure():
    """The geometry rule has a failing case: move the bust into the box and the same check must refuse it."""
    config = macros()
    frame, report = preview.compose(ROOT, "quay_gate_choice", 0, config)
    inside = dict(report["portrait"])
    inside["y0"] = config["PP_TEXT_Y"]
    inside["y1"] = config["PP_TEXT_Y"] + config["PP_PORTRAIT_SIZE"]
    broken = dict(report)
    broken["portrait"] = inside
    errors = preview.check(broken, config)
    assert errors, "a bust that starts inside the text area must be refused"
    assert any("top edge" in error or "bust over" in error for error in errors), errors
