/// pp_font: the 8x8 bitmap font, drawn from the spr_pp_font8 sprite sheet.
/// This is the game's only letters. Every screen that draws with it goes through pp_font_draw, so the letters are the
/// same pixels everywhere (spec 13, font and UI): the title screen, the drive scene, the dialogue box's rows, name
/// plate and choice labels (card t_1d828fcd), and since card BATTLE-FONT-WIRE the boot card, the battle board, the
/// save panel, the dodge arena and the overworld hint line.
/// Card BATTLE-FONT-WIRE moved the last 34 call sites off the GameMaker default font, and since that card the tree
/// holds no text call outside a comment: this module is the one place a glyph becomes pixels, and a screen that prints
/// words without asking it is the bug the header of this file exists to warn about.
/// A screen whose line has to break needs pp_font_wrap (a column count, not a pixel width), because the sheet draws
/// every glyph in the same 8 pixel cell; a row that has to be marked as refused is ruled through by
/// pp_font_draw_struck, and a line that has to read over sprite art sits on pp_font_draw_plated_centre's plate. None
/// of the four wraps, rules or plates tints a glyph: the sheet is one ink (rule 6 of the font contract).
/// The sheet holds one frame per glyph in ASCII order, so a glyph is found by its position in the ASCII set
/// rather than by a table of offsets.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\13-8bit-look.md and the art lane's contract in TITLE-COORD.md.

/// The glyph set of spr_pp_font8, in the ASCII order the art lane uses: one frame per character.
/// The set is the characters the game can write, and the sheet has exactly one frame for each of them.
/// 77 glyphs: space, the twelve marks `!"'()*,-./:?`, the ten digits, the 26 capitals, the two brackets `[]` and the
/// 26 lowercase letters. The three brackets and the slash were added by card t_f476435e (decision D13): the battle HP
/// line reads `HP 12/12` and the drive caption draws `[1]`, and until the sheet carried them pp_font_draw left a space
/// where each one stood. ASCII order places them, so no other frame moves: `/` sits between `.` and `0`, `[` and `]`
/// between `Z` and `a`.
/// Three groups were added by card t_41c97c88 because the slice prints them and the 46 glyph sheet did not have
/// them: `*` is the narration marker the dialogue data carries on every line (spec 19 Q6/D6), `"` is the quote the
/// arrival and gate lines wrap speech in, and the lowercase letters are the sentence case the authored dialogue is
/// written in (`* The deck tilts.`), which a capitals only sheet drew as spaces. The logo keeps its own 5x7
/// capitals grid in tools/art/make_title_ui.py; this sheet is the text alphabet.
/// tools/check_font_coverage.py reads this string, proves the sheet matches it frame by frame, and refuses the
/// build when a data file prints a character that is not in it.
function pp_font_glyphs() {
    return " !\"'()*,-./0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ[]abcdefghijklmnopqrstuvwxyz";
}

/// The frame number of one character, or -1 when the character is not in the sheet.
function pp_font_glyph_index(_char) {
    var _set = pp_font_glyphs();
    var _pos = string_pos(_char, _set);
    if (_pos <= 0) return -1;
    return _pos - 1;
}

/// The width in pixels of a string at the 8x8 font.
function pp_font_width(_text) {
    return string_length(_text) * 8;
}

/// Draw one line of text with the 8x8 font, left aligned, at an alpha. Returns the width drawn.
/// A character the sheet does not have is drawn as a space, so a stray character never breaks the layout.
///
/// The sheet is one row of 8x8 frames in one ink, 2C02 $20 white. There is no second weight and there is no tint. That
/// is deliberate (card t_a1170172): a tint is a multiply, and multiplying the sheet's white by the grey a
/// disabled label used to ask for produced #7b7b7b, a value no PPU can output, which is what
/// tools/nes_composite_check.py refused in the composited title frame. An "off" row is marked by a rule drawn
/// through it in the ground band's own dark green instead; see pp_title_draw_disabled.
function pp_font_draw(_text, _x, _y, _alpha) {
    var _info = pp_art_info("spr_pp_font8");
    if (is_undefined(_info)) return 0;
    var _cx = _x;
    for (var i = 0; i < string_length(_text); i += 1) {
        var _ch = string_char_at(_text, i + 1);
        var _g = pp_font_glyph_index(_ch);
        if (_g >= 0) {
            draw_sprite_part_ext(_info.sprite, 0, _g * 8, 0, 8, 8, _cx, _y, 1, 1, PP_UNTINTED, _alpha);
        }
        _cx += 8;
    }
    return _cx - _x;
}

/// Draw one line of text centred on a point.
function pp_font_draw_centre(_text, _centre_x, _y, _alpha) {
    var _w = pp_font_width(_text);
    return pp_font_draw(_text, _centre_x - floor(_w / 2), _y, _alpha);
}

// ---------------------------------------------------------------------------------------------------------------
// Wrapping, rules and plates: the three shapes the rest of the screen needed once it moved onto the sheet
//
// The default font is proportional and could be wrapped at a pixel width. The sheet draws every glyph in the same 8
// pixel cell, so a row is a column count: _columns characters at 8 px are _columns * 8 pixels. These helpers live here,
// once, so a battle label, a game over note, an error sentence and a save panel line cannot disagree about where a
// word breaks, and no screen grows its own wrap (card BATTLE-FONT-WIRE).

/// The number of 8 pixel glyph cells that fit in a pixel width. 224 px is 28 characters, the dialogue box's row.
function pp_font_cols(_pixels) {
    return max(1, floor(_pixels / 8));
}

/// One line of text as rows of at most _columns glyphs, by word. Same greedy rule the dialogue box uses: a word that
/// does not fit moves whole to the next row, and a word that cannot fit on a row at all is split and reported, because
/// dropping it is worse than breaking it.
function pp_font_wrap(_text, _columns) {
    var _cols = max(1, floor(_columns));
    var _text_len = string_length(_text);
    var _rows = [];
    if (_text_len == 0) return [""];

    var _row = "";
    var _pos = 1;
    while (_pos <= _text_len) {
        // One word: the run of non space characters under the cursor.
        var _word = "";
        while (_pos <= _text_len && string_char_at(_text, _pos) != " ") {
            _word += string_char_at(_text, _pos);
            _pos += 1;
        }
        // The run of spaces after it is the break itself, not part of the word.
        while (_pos <= _text_len && string_char_at(_text, _pos) == " ") {
            _pos += 1;
        }
        if (_word == "") break;

        var _word_len = string_length(_word);
        if (_word_len > _cols) {
            show_debug_message("PP: pp_font_wrap split a word longer than a row");
            if (_row != "") {
                array_push(_rows, _row);
                _row = "";
            }
            var _slice = 1;
            while (_slice + _cols <= _word_len) {
                array_push(_rows, string_copy(_word, _slice, _cols));
                _slice += _cols;
            }
            _row = string_copy(_word, _slice, _word_len - _slice + 1);
        } else if (_row == "") {
            _row = _word;
        } else if (string_length(_row) + 1 + _word_len <= _cols) {
            _row = _row + " " + _word;
        } else {
            array_push(_rows, _row);
            _row = _word;
        }
    }

    if (_row != "") array_push(_rows, _row);
    if (array_length(_rows) == 0) array_push(_rows, "");
    return _rows;
}

/// Draw one line word wrapped to _columns, left aligned at _x, one row every _line_h pixels. Returns the rows drawn,
/// so a caller stacking blocks can advance by what was actually drawn rather than by what it hoped.
function pp_font_draw_wrapped(_text, _x, _y, _columns, _line_h, _alpha) {
    var _rows = pp_font_wrap(_text, _columns);
    var _i = 0;
    while (_i < array_length(_rows)) {
        pp_font_draw(_rows[_i], _x, _y + _i * _line_h, _alpha);
        _i += 1;
    }
    return array_length(_rows);
}

/// Draw one line word wrapped to _columns, each row centred on _centre_x.
function pp_font_draw_wrapped_centre(_text, _centre_x, _y, _columns, _line_h, _alpha) {
    var _rows = pp_font_wrap(_text, _columns);
    var _i = 0;
    while (_i < array_length(_rows)) {
        pp_font_draw_centre(_rows[_i], _centre_x, _y + _i * _line_h, _alpha);
        _i += 1;
    }
    return array_length(_rows);
}

/// Draw one line and rule a 1 pixel line through it, which is how a row that cannot be picked is marked now that
/// there is no second ink to spend (rule 6). The title screen's pp_title_draw_disabled does the same in its own
/// palette; a battle menu row and a game over row ask for this one.
function pp_font_draw_struck(_text, _x, _y, _alpha) {
    var _w = pp_font_draw(_text, _x, _y, _alpha);
    draw_set_colour(pp_role_colour("dim"));
    draw_line_width(_x, _y + 4, _x + _w - 1, _y + 4, 1);
    return _w;
}

/// pp_font_draw_struck, centred on a point.
function pp_font_draw_centre_struck(_text, _centre_x, _y, _alpha) {
    return pp_font_draw_struck(_text, _centre_x - floor(pp_font_width(_text) / 2), _y, _alpha);
}

/// Draw one short line centred on a filled plate of the room's own ink role. The glyphs stay the sheet's one ink; the
/// plate is a background shape, which is what keeps a damage number legible over the light enemy block and keeps the
/// arena's "clear" legible over the baked field strip. A tint would have been a multiply and no PPU can output it.
function pp_font_draw_plated_centre(_text, _centre_x, _y, _alpha) {
    var _w = pp_font_width(_text);
    var _x = _centre_x - floor(_w / 2);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(_x - 3, _y - 2, _x + _w + 2, _y + 9, false);
    return pp_font_draw(_text, _x, _y, _alpha);
}
