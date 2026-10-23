#!/usr/bin/env python3
"""Card BATTLE-FONT-WIRE: the battle and app screens print the 8x8 sheet, and nothing else prints at all.

The card moved 34 call sites onto pp_font_draw: the boot card and the battle outcome (pp_app), the field, the menu
band and the game over card (pp_battle_director), the message board, the talk board and its hint (pp_battle_text),
the arena's clear line and debug line (pp_dodge_arena), the overworld hint (pp_overworld) and the save panel
(pp_save). These tests pin what that means, in the terms the font contract in
knowledge/FONT-CONTRACT-AUDIT-2026-10-23.md uses:

  1. one text path, and no draw_text left on a screen the player sees;
  2. a row is a column count, because the sheet's cell is 8 px, and the wrap lives once in pp_font;
  3. one ink: a refused or selected row is marked by a rule or by where it sits, never by a tint of the glyph;
  4. every character the battle screens print is a frame of the sheet, so nothing draws as a silent space.

Since card SHEET-GLYPH-GAP (t_f476435e, decision D13) the sheet carries 77 frames: it grew `/`, `[` and `]`, the HP
line joins its numbers with a slash again, and the drive caption's `[1]` draws its brackets. Two tests below read the
two sites that compose their strings at run time, because the inventory cannot see a string that is built by +.

What these tests cannot do is run GML. They read the source and the data, which is the same footing the rest of the
suite stands on; the pixels are tools/preview_battle_font.py's job and tools/check_font_coverage.py's.

No em dash or en dash anywhere in this file: the project refuses them at the door (tests/test_project.py).
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP = os.path.join("game", "scripts", "pp_app", "pp_app.gml")
DIRECTOR = os.path.join("game", "scripts", "pp_battle_director", "pp_battle_director.gml")
BATTLE_TEXT = os.path.join("game", "scripts", "pp_battle_text", "pp_battle_text.gml")
DODGE_ARENA = os.path.join("game", "scripts", "pp_dodge_arena", "pp_dodge_arena.gml")
OVERWORLD = os.path.join("game", "scripts", "pp_overworld", "pp_overworld.gml")
SAVE = os.path.join("game", "scripts", "pp_save", "pp_save.gml")
DRIVE = os.path.join("game", "scripts", "pp_drive", "pp_drive.gml")
FONT = os.path.join("game", "scripts", "pp_font", "pp_font.gml")
COMMANDS = os.path.join("game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")
CONFIG = os.path.join("game", "scripts", "pp_config", "pp_config.gml")
DEBUG_OVERLAY = os.path.join("game", "objects", "obj_pp_debug_overlay", "Draw_64.gml")

# The screens this card wired. pp_font is the renderer itself, checked by its own assertions below.
SCREENS = (APP, DIRECTOR, BATTLE_TEXT, DODGE_ARENA, OVERWORLD, SAVE)


def read(relative):
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8-sig") as handle:
        return handle.read()


def code_only(text):
    """Drop // and /// comments: the audits below read code, and the headers of these files name draw_text in prose."""
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def function_body(text, name):
    """The body of `function name(` up to the line that closes it, matched at column zero."""
    match = re.search(r"function\s+%s\s*\([^)]*\)\s*\{(.*?)\n\}" % re.escape(name), text, re.S)
    assert match is not None, "no function %s in the file" % name
    return match.group(1)


def font_glyphs():
    """The characters pp_font_glyphs() returns, which is what pp_font_draw can draw."""
    body = function_body(read(FONT), "pp_font_glyphs")
    literal = re.search(r'return\s+"((?:[^"\\]|\\.)*)"\s*;', body)
    assert literal is not None, "pp_font_glyphs does not return a string literal"
    raw = literal.group(1)
    out = []
    index = 0
    while index < len(raw):
        if raw[index] == "\\" and index + 1 < len(raw):
            out.append(raw[index + 1])
            index += 2
            continue
        out.append(raw[index])
        index += 1
    return out


def macros():
    out = {}
    for match in re.finditer(r"^#macro\s+(PP_[A-Z0-9_]+)\s+(-?\d+)\s*$", read(CONFIG), re.MULTILINE):
        out[match.group(1)] = int(match.group(2))
    return out


def gml_files():
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in sorted(filenames):
            if name.endswith(".gml"):
                path = os.path.join(dirpath, name)
                yield os.path.relpath(path, ROOT).replace("\\", "/"), path


# ---------------------------------------------------------------------------------------------------------------
# 1. One text path.
def test_no_screen_in_the_game_still_prints_with_the_default_font():
    """The card's premise: the project holds no font resource, so a draw_text is a line in GameMaker's own font."""
    offenders = []
    for relative, path in gml_files():
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = code_only(handle.read())
        if re.search(r"\bdraw_text", text):
            offenders.append(relative)
    # The one site left is the developer overlay, drawn in Draw GUI space: it prints a multi line ledger dump at the
    # window's own scale, it is not a screen a player sees, and pp_ledger_debug_lines already lays it out. It is
    # listed here by name so the gap is a recorded decision rather than an accident, and so converting it turns this
    # test red on purpose.
    assert offenders == ["game/objects/obj_pp_debug_overlay/Draw_64.gml"], \
        "a screen prints with draw_text again: %s" % offenders


def test_every_screen_this_card_wired_draws_through_pp_font():
    for relative in SCREENS:
        code = code_only(read(relative))
        assert "pp_font_draw" in code, "%s prints text but never asks pp_font" % relative
        assert "draw_text" not in code, "%s still draws with the default font" % relative


def test_the_text_board_no_longer_takes_a_colour():
    """One ink: a colour argument is the shape of a tint, and the sheet has no second ink to spend."""
    assert "function pp_text_board_draw(_board, _x, _y)" in read(BATTLE_TEXT)
    assert "function pp_talk_board_draw(_board, _x, _y)" in read(BATTLE_TEXT)
    assert "function pp_talk_hint_draw(_hint)" in read(BATTLE_TEXT)
    wired = function_body(read(DIRECTOR), "pp_battle_draw")
    assert "pp_text_board_draw(_battle.messages, 16, 16)" in wired, wired
    assert "pp_talk_board_draw(_battle.messages, pp_talk_text_x(), pp_talk_text_y())" in wired, wired


# ---------------------------------------------------------------------------------------------------------------
# 2. A row is a column count.
def test_the_wrap_lives_once_in_pp_font_and_the_screens_ask_it():
    font = code_only(read(FONT))
    for name in ("pp_font_cols", "pp_font_wrap", "pp_font_draw_wrapped", "pp_font_draw_wrapped_centre",
                 "pp_font_draw_struck", "pp_font_draw_plated_centre"):
        assert "function %s(" % name in font, "pp_font has no %s" % name

    # No screen grew a wrap of its own. Two modules define one: pp_font's is this card's, and pp_battle_text's
    # pp_talk_wrap is older than the card and is the talk loader's own step (it wraps a card pool line into at most
    # four rows through pp_talk_cut, which is the "cut at the last space" of spec 19 section 4). Unifying the two is a
    # follow up, not a change this card can make without altering what the talk loader accepts.
    owners = []
    for relative, path in gml_files():
        with open(path, "r", encoding="utf-8-sig") as handle:
            code = code_only(handle.read())
        if re.search(r"^function\s+\w*wrap\w*\s*\(", code, re.MULTILINE):
            owners.append(relative)
    assert owners == ["game/scripts/pp_battle_text/pp_battle_text.gml", "game/scripts/pp_font/pp_font.gml"], owners


def test_a_pixel_width_is_never_handed_to_a_font_draw():
    """The old draw_text_ext took a pixel width and a line height. pp_font draws in 8 px cells, so a width is columns."""
    for relative in (APP, DIRECTOR, BATTLE_TEXT, SAVE, DODGE_ARENA, OVERWORLD):
        code = code_only(read(relative))
        assert "pp_font_cols(" in code, "%s wraps nothing, so a long line cannot be measured" % relative
        assert not re.search(r",\s*10\s*,\s*PP_FRAME_W", code), \
            "%s still hands draw_text_ext's pixel width to a draw" % relative


def test_the_battle_band_and_the_card_are_measured_in_cells():
    # The message window is 224 px inside (PP_FRAME_W - 32), which is 28 characters at 8 px a cell.
    band = function_body(read(BATTLE_TEXT), "pp_text_board_draw")
    assert "pp_font_cols(PP_FRAME_W - 32)" in band, band
    # The game over card's inner rectangle is x 66 to x 190, 124 px: 15 cells, and the fallback path in pp_app takes
    # the outcome word at the same kind of count (176 px inside its panel).
    card = function_body(read(DIRECTOR), "pp_battle_draw_gameover")
    assert "draw_rectangle(66, 66, 190, 174, false)" in card, card
    assert "pp_font_cols(124)" in card, card
    assert "pp_font_cols(PP_FRAME_W - 80)" in read(APP)


# ---------------------------------------------------------------------------------------------------------------
# 3. One ink: a mark is a shape or a position, never a tint.
def test_a_refused_row_is_ruled_through_and_a_selected_row_is_marked_by_position():
    director = read(DIRECTOR)
    menu = function_body(director, "pp_battle_draw_menu")
    assert "pp_font_draw_struck(_entry.label" in menu, menu
    assert "pp_font_draw(_entry.label" in menu, menu
    card = function_body(director, "pp_battle_draw_gameover")
    assert "pp_font_draw_centre_struck(_label" in card, card
    assert "draw_rectangle(_x, _y + 9, _x + _w - 1, _y + 10, false)" in card, \
        "the selected row's 2 px rule is gone, so selection has no marker at all"


def test_a_number_over_the_light_block_sits_on_a_plate():
    """The damage popup used to be the light role on a light block; the glyphs cannot be tinted, so the plate does it."""
    field = function_body(read(DIRECTOR), "pp_battle_draw")
    assert "pp_font_draw_plated_centre(string(_battle.popup_value)" in field, field
    assert "pp_font_draw_plated_centre(\"clear\"" in read(DODGE_ARENA)


# ---------------------------------------------------------------------------------------------------------------
# 4. Every character the battle screens print is a frame of the sheet.
def test_the_battle_screens_print_no_character_the_sheet_lacks():
    glyphs = set(font_glyphs())
    director = read(DIRECTOR)
    commands = read(COMMANDS)

    printed = [
        "PRIMORDIAL PARADOX", "Z continue     X new game", "Z start", "debug build  mode ", "press Z",
        "here it comes", "GAME OVER", " stands over you.", "reading the last save", "clear", "Z",
        "* " + (_macro_string("PP_TALK_PROMPT") or ""),
    ]
    printed += re.findall(r'label:\s*"([^"]+)"', commands)
    rows = re.search(r"function\s+pp_battle_gameover_rows\s*\(\s*\)\s*\{(.*?)\n\}", director, re.S)
    assert rows is not None
    printed += re.findall(r'"([^"]+)"', rows.group(1))
    printed += re.findall(r'_battle\.gameover_note = "([^"]+)"', director)
    printed += re.findall(r'_reason = "([^"]+)"', commands)

    missing = sorted({char for text in printed for char in text if char not in glyphs})
    assert missing == [], "the battle screens print %s, which the sheet cannot draw" % missing


def _macro_string(name):
    match = re.search(r'^#macro\s+%s\s+"([^"]*)"\s*$' % re.escape(name), read(CONFIG), re.MULTILINE)
    return match.group(1) if match else None


def test_the_hp_line_joins_its_numbers_with_the_slash_the_sheet_now_carries():
    """Card t_f476435e (D13): the sheet grew `/`, `[` and `]`, so the HP line reads `HP 12/12` again.

    Card BATTLE-FONT-WIRE wrote it as `OF` because the sheet had no slash and a screen card could not grow an art
    asset. The slash exists now, so the reason for the words is gone and keeping them would be drift.
    """
    glyphs = set(font_glyphs())
    field = function_body(read(DIRECTOR), "pp_battle_draw")
    hp = [line for line in field.split("\n") if '"HP "' in line or '"/"' in line or '"   WILL "' in line]
    assert hp, "the HP and WILL line is gone"
    joined = " ".join(hp)
    assert '"/"' in joined, "the HP line does not join its numbers with a slash"
    assert " OF " not in joined, "the HP line still spells out OF between the numbers"
    assert "/" in glyphs, "the HP line draws a slash the sheet does not have"


def test_the_two_sites_this_card_fixed_ask_only_for_glyphs_the_sheet_carries():
    """The HP line and the drive caption compose their strings at run time, so the inventory above cannot see them.

    Both were drawing a space where a character they ask for should be: the slash in `HP 12/12` was written as OF to
    avoid the hole, and the caption's `[1]` lost both brackets. Read here by name, from the two functions that draw
    them; the digits come from `string()` at run time and are covered by the sheet's ten digits.
    """
    glyphs = set(font_glyphs())
    sources = (
        (DIRECTOR, "pp_battle_draw", "the HP and WILL line"),
        (DRIVE, "pp_drive_draw_caption", "the drive caption"),
    )
    for relative, name, what in sources:
        body = function_body(read(relative), name)
        drawn = [line for line in body.split("\n") if "pp_font_draw" in line]
        assert drawn, "%s draws nothing" % what
        literals = [literal for line in drawn for literal in re.findall(r'"((?:[^"\\]|\\.)*)"', line)]
        assert literals, "%s carries no string literal to check" % what
        # string() of a number can print any digit, so the digits count as asked for by both sites.
        missing = sorted({char for text in literals + ["0123456789"] for char in text} - glyphs)
        assert missing == [], "%s asks for %s, which the sheet cannot draw" % (what, missing)
    caption = " ".join(literal for line in function_body(read(DRIVE), "pp_drive_draw_caption").split("\n")
                       if "pp_font_draw" in line for literal in re.findall(r'"((?:[^"\\]|\\.)*)"', line))
    assert "[" in caption and "]" in caption, "the drive caption no longer brackets its page number"


def test_the_game_over_card_holds_its_longest_row_in_eight_pixel_cells():
    # The card's inner rectangle is x 66 to x 190: 124 px, which is 15 cells with 4 px to spare, and the rows are
    # centred on the frame, so the widest one decides whether it fits.
    rows = re.findall(r'"(CONTINUE|RETURN TO TITLE)"', read(DIRECTOR))
    assert rows == ["CONTINUE", "RETURN TO TITLE"], rows
    assert max(len(row) for row in rows) * 8 <= 190 - 66, "the widest row leaves the card"


def test_the_refusal_note_clears_the_third_command_row():
    config = macros()
    # The band's third label row sits at PP_MENU_TOP + 8 + 2 * 20 and is one 8 px cell tall; the note is drawn at
    # PP_FRAME_H - 16, so its first pixel row is the label row's last pixel row plus one.
    third_row_bottom = config["PP_MENU_TOP"] + 8 + 2 * 20 + 8 - 1
    assert config["PP_FRAME_H"] - 16 > third_row_bottom
    assert config["PP_FRAME_H"] - 16 + 8 - 1 <= config["PP_FRAME_H"] - 8
    menu = function_body(read(DIRECTOR), "pp_battle_draw_menu")
    assert "PP_FRAME_H - 16" in menu, menu


def test_the_preview_tool_that_shows_these_frames_exists_and_is_readable():
    path = os.path.join(ROOT, "tools", "preview_battle_font.py")
    assert os.path.isfile(path), "the card's 3x preview tool is missing"
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "pp_battle_draw_gameover" in source and "PP_MENU_TOP" in source, \
        "the preview does not read the geometry it claims to compose"
