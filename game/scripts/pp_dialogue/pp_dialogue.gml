/// pp_dialogue: the text box layout (spec 05) over the one reveal machine in pp_text.
/// This module owns the words' shape and place: word wrap, pages, the box, the name plate, the portrait bust, the page
/// arrow and the choice rows, and it draws every one of them through pp_font_draw and pp_art_info, the one text path
/// and the one sheet path in the game. It owns no reveal: the character timing, the holds, the punctuation pauses, the
/// blip and the done predicate belong to pp_text (law 8, one renderer per thing).
/// The portrait is a 48x48 bust above the box (spec 05 Geometry, card t_4d6b0f4b): a page carries a `portrait` name the
/// same way it carries a `speaker`, the sheet is spr_pp_portrait_<name> on the same one-sheet index as the window and
/// the font, and a page with no portrait draws none. Nothing is reserved for it inside the box: the text area keeps all
/// 28 columns and the bust stands on the box's top edge.
/// Provenance: knowledge\PROVENANCE.md, entry "text reveal machine: one implementation, two layouts", and the older
/// entry "battle state machine and turn loop". The page and beat model is spec 05.
/// No closures: every loop is written out, because a closure that reassigns an outer var is the kind of thing that
/// behaves differently between runtimes and cannot be tested on this PC.

/// Wrap one source line into rows of at most PP_TEXT_CHARS characters, by word. A word that does not fit moves whole
/// to the next row; a word that cannot fit in a row at all is split and reported, because dropping it is worse.
function pp_dialogue_rows(_text) {
    var _items = pp_text_items(_text);

    // First pass: group items into words, remembering a pause that followed each word.
    var _words = [];
    var _current = [];
    var _i = 0;
    var _count = array_length(_items);
    while (_i < _count) {
        var _item = _items[_i];
        if (_item.ch == " ") {
            if (array_length(_current) > 0) {
                array_push(_words, { items: _current, after: _item.wait });
                _current = [];
            } else if (_item.wait > 0) {
                array_push(_words, { items: [], after: _item.wait });
            }
        } else {
            array_push(_current, _item);
        }
        _i += 1;
    }
    if (array_length(_current) > 0) array_push(_words, { items: _current, after: 0 });

    // Second pass: greedy fill.
    var _rows = [];
    var _row = [];
    var _w = 0;
    while (_w < array_length(_words)) {
        var _word = _words[_w].items;
        var _wlen = array_length(_word);
        if (_wlen > PP_TEXT_CHARS) {
            show_debug_message("PP: a word longer than a row was split");
            var _pos = 0;
            while (_pos < _wlen) {
                var _room = PP_TEXT_CHARS - array_length(_row);
                if (_room <= 0) {
                    array_push(_rows, _row);
                    _row = [];
                    _room = PP_TEXT_CHARS;
                }
                while (_pos < _wlen && _room > 0) {
                    array_push(_row, _word[_pos]);
                    _pos += 1;
                    _room -= 1;
                }
            }
        } else {
            if (array_length(_row) > 0 && array_length(_row) + _wlen > PP_TEXT_CHARS) {
                array_push(_rows, _row);
                _row = [];
            }
            var _j = 0;
            while (_j < _wlen) {
                array_push(_row, _word[_j]);
                _j += 1;
            }
        }
        if (_words[_w].after > 0) array_push(_row, { ch: "", wait: _words[_w].after, speed: -1 });
        _w += 1;
    }
    if (array_length(_row) > 0 || array_length(_rows) == 0) array_push(_rows, _row);
    return _rows;
}

/// --- Dialogue v2 (decision D2, 2026-10-22) --------------------------------------------------------------------
/// An entry carries id, speaker and exactly one of `lines` or `pages`. `pages` is the box's own shape: 1 to 3 pages of
/// 1 to 3 lines, each line already 30 characters or fewer. A page may name its own speaker, which is how a scene where
/// the narrator and a sentry trade pages keeps the right name plate without becoming two entries.
/// A choice list is 1 to 3 items: a label (12 characters), the flags it sets, and an optional `goto`.
/// The flag names are data (data/flags.json) and the ledger owns them; this module only applies them, in one place.
/// No closures: the loops are written out for the same reason the rest of this file writes them out.
/// The choice rows' numbers are PP_CHOICE_ARROW_X, PP_CHOICE_ARROW_W and PP_CHOICE_LABEL_X, in pp_config beside the
/// text area they share (card t_01432e14).

/// Build pages from a dialogue record. In the shorthand one source line is one page (a source line break waits for
/// confirm, rule 2) and a page holds at most PP_TEXT_ROWS rows; in the `pages` shape the data has already decided the
/// page breaks, so each page is taken as written and only re-paged if wrapping made it taller than the box.
function pp_dialogue_pages(_row) {
    var _pages = [];
    // The bust this entry carries, if any, and a page may name its own the way it names its own speaker: an entry
    // whose pages change speaker needs its portrait to change with the plate, and the empty string is how a page says
    // "nobody" rather than leaving the entry's bust up (card t_4d6b0f4b).
    var _portrait = "";
    if (variable_struct_exists(_row, "portrait")) _portrait = _row.portrait;
    if (variable_struct_exists(_row, "pages") && is_array(_row.pages)) {
        var _p = 0;
        while (_p < array_length(_row.pages)) {
            var _page = _row.pages[_p];
            var _speaker = _row.speaker;
            if (variable_struct_exists(_page, "speaker")) _speaker = _page.speaker;
            var _page_portrait = _portrait;
            if (variable_struct_exists(_page, "portrait")) _page_portrait = _page.portrait;
            pp_dialogue_push_page(_pages, _page.lines, _speaker, _page_portrait);
            _p += 1;
        }
    } else {
        pp_dialogue_push_page(_pages, _row.lines, _row.speaker, _portrait);
    }
    return _pages;
}

/// Wrap one run of source lines into pages of at most PP_TEXT_ROWS rows, each page carrying the speaker and the bust
/// it is shown with. A source line that wraps past the box becomes another page rather than a shorter box (rule 4).
function pp_dialogue_push_page(_pages, _lines, _speaker, _portrait) {
    var _i = 0;
    while (_i < array_length(_lines)) {
        var _rows = pp_dialogue_rows(_lines[_i]);
        var _start = 0;
        while (_start < array_length(_rows)) {
            var _chunk = [];
            var _r = _start;
            while (_r < array_length(_rows) && _r < _start + PP_TEXT_ROWS) {
                array_push(_chunk, _rows[_r]);
                _r += 1;
            }
            array_push(_pages, { speaker: _speaker, portrait: _portrait, rows: _chunk });
            _start += PP_TEXT_ROWS;
        }
        _i += 1;
    }
    return _pages;
}

/// The page rows alone, for a caller that does not draw the name plate.
function pp_dialogue_build(_row) {
    var _pages = pp_dialogue_pages(_row);
    var _out = [];
    var _i = 0;
    while (_i < array_length(_pages)) {
        array_push(_out, _pages[_i].rows);
        _i += 1;
    }
    return _out;
}

/// One page's rows as the single item list the reveal machine advances through. The rows stay separate because the box
/// draws them at their own y, but the reveal walks the page as one run of characters, which is what a page is.
function pp_dialogue_page_unit(_rows) {
    var _unit = [];
    var _r = 0;
    while (_r < array_length(_rows)) {
        var _row = _rows[_r];
        var _c = 0;
        while (_c < array_length(_row)) {
            array_push(_unit, _row[_c]);
            _c += 1;
        }
        _r += 1;
    }
    return _unit;
}

/// A flag list off a data row, copied so the runtime never edits the loaded data by accident.
function pp_dialogue_flag_list(_row, _field) {
    var _out = [];
    if (!variable_struct_exists(_row, _field)) return _out;
    var _names = _row[$ _field];
    if (!is_array(_names)) return _out;
    var _i = 0;
    while (_i < array_length(_names)) {
        array_push(_out, _names[_i]);
        _i += 1;
    }
    return _out;
}

/// The choice list off a data row: label, the flags it sets, and the dialogue it goes to ("" for close).
function pp_dialogue_choice_list(_row) {
    var _out = [];
    if (!variable_struct_exists(_row, "choices") || !is_array(_row.choices)) return _out;
    var _i = 0;
    while (_i < array_length(_row.choices)) {
        var _choice = _row.choices[_i];
        var _goto = "";
        if (variable_struct_exists(_choice, "goto")) _goto = _choice.goto;
        array_push(_out, {
            label: _choice.label,
            sets: pp_dialogue_flag_list(_choice, "sets"),
            goto: _goto
        });
        _i += 1;
    }
    return _out;
}

/// Apply every flag in a data list. One writer for the ledger: pp_ledger owns flags, this module owns the box.
/// Called before the box closes (D2.6) and before a `goto` opens the next entry, so a reply scene sees the flag.
function pp_dialogue_apply_flags(_names) {
    if (is_undefined(_names)) return;
    var _i = 0;
    while (_i < array_length(_names)) {
        pp_ledger_set_flag(global.pp_ledger, _names[_i], true);
        _i += 1;
    }
}

/// Open a dialogue by id: {id, speaker, pages, sets, choices, cursor, reveal, closed}. The reveal is the one in
/// pp_text; this module holds no cursor of its own for the typing, only the choice cursor.
function pp_dialogue_open(_dialogue_id) {
    var _row = pp_data_find(global.pp_data.dialogue.dialogue, _dialogue_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no dialogue with id " + string(_dialogue_id));
        return undefined;
    }
    var _pages = pp_dialogue_pages(_row);
    if (array_length(_pages) == 0) return undefined;

    var _units = [];
    var _p = 0;
    while (_p < array_length(_pages)) {
        array_push(_units, pp_dialogue_page_unit(_pages[_p].rows));
        _p += 1;
    }

    // The box waits for confirm at the end of a page, so the machine advances only when this layout says so.
    var _portrait = "";
    if (variable_struct_exists(_row, "portrait")) _portrait = _row.portrait;
    return {
        id: _row.id,
        speaker: _row.speaker,
        portrait: _portrait,
        pages: _pages,
        sets: pp_dialogue_flag_list(_row, "sets"),
        choices: pp_dialogue_choice_list(_row),
        cursor: 0,
        reveal: pp_text_reveal_begin(_units, _row.speaker, false),
        closed: false
    };
}

/// True when the box is on its last page and that page offers a choice: the page then waits for a pick, not a turn.
function pp_dialogue_on_choice_page(_d) {
    if (is_undefined(_d) || _d.closed) return false;
    if (array_length(_d.choices) == 0) return false;
    return (_d.reveal.unit + 1 >= array_length(_d.reveal.units));
}

/// Move the choice cursor one item, wrapping, which is spec 05's rule for the panel.
function pp_dialogue_move_cursor(_d, _delta) {
    if (is_undefined(_d) || _d.closed) return _d;
    var _count = array_length(_d.choices);
    if (_count == 0) return _d;
    _d.cursor = (_d.cursor + _delta + _count) mod _count;
    return _d;
}

/// Pick one choice: every flag in its `sets` is applied, then the box either continues at `goto` or closes (D2.3).
/// Returns true when the box closed. A `goto` loads into the same struct, so a caller holding the box keeps its handle.
function pp_dialogue_pick(_d, _index) {
    if (is_undefined(_d) || _d.closed) return false;
    if (!pp_dialogue_on_choice_page(_d)) return false;
    if (_index < 0 || _index >= array_length(_d.choices)) return false;

    var _choice = _d.choices[_index];
    pp_dialogue_apply_flags(_choice.sets);
    pp_dialogue_apply_flags(_d.sets);

    if (_choice.goto != "") {
        var _next = pp_dialogue_open(_choice.goto);
        if (!is_undefined(_next)) {
            _d.id = _next.id;
            _d.speaker = _next.speaker;
            _d.portrait = _next.portrait;
            _d.pages = _next.pages;
            _d.sets = _next.sets;
            _d.choices = _next.choices;
            _d.cursor = 0;
            _d.reveal = _next.reveal;
            _d.closed = false;
            return false;
        }
        show_debug_message("PP: a choice goes to no dialogue " + string(_choice.goto));
    }

    _d.closed = true;
    return true;
}

/// One step of the box: the machine types, the box draws whatever it has revealed. On the page that offers a choice
/// this is also where the panel listens, because the pick is the box's business and no scene command knows about it
/// (D2.4). A pick that loads another entry continues in the same box, so the caller's handle stays good.
function pp_dialogue_step(_d) {
    if (is_undefined(_d) || _d.closed) return;
    pp_text_reveal_step(_d.reveal, pp_action("confirm"));
    if (!pp_dialogue_on_choice_page(_d)) return;
    if (_d.reveal.revealed < pp_text_unit_length(_d.reveal)) return;
    if (pp_pressed("up")) pp_dialogue_move_cursor(_d, -1);
    if (pp_pressed("down")) pp_dialogue_move_cursor(_d, 1);
    if (pp_pressed("confirm")) pp_dialogue_pick(_d, _d.cursor);
}

/// Confirm: complete the page if it is still typing, otherwise turn the page or close. Returns true when it closed.
/// A page that offers a choice does not turn on confirm: the pick decides where the box goes next.
function pp_dialogue_advance(_d) {
    if (is_undefined(_d) || _d.closed) return true;
    if (_d.reveal.revealed < pp_text_unit_length(_d.reveal)) {
        pp_text_reveal_complete(_d.reveal);
        return false;
    }
    if (pp_dialogue_on_choice_page(_d)) return false;
    if (pp_text_reveal_next(_d.reveal)) {
        pp_dialogue_apply_flags(_d.sets);
        _d.closed = true;
        return true;
    }
    return false;
}

function pp_dialogue_closed(_d) {
    if (is_undefined(_d)) return true;
    return _d.closed;
}

/// Draw the box, the name plate, the visible rows, the choice rows and the arrow. One ink: the font sheet's own
/// (rule 6).
///
/// Every piece of text here goes through pp_font_draw, never draw_text (card t_1d828fcd). The box used to draw its
/// rows, its name plate and its choice labels with draw_text, and the project has no font resource, so the dialogue
/// printed in the GameMaker default font while the rest of the game printed the 8x8 sheet: the box was the one place
/// the art lane's font never reached. pp_font_draw is the only text path in this module now.
///
/// There is no colour argument to give it, and that is deliberate. The sheet is one ink, #f8f8f8, and the window's
/// fill is #000000, so the text is the sheet's white on the window's black without a tint. A tint is a multiply, and
/// multiplying that white by a role colour produces values no PPU can output (card t_a1170172, the same reason the
/// title marks a disabled row with a rule instead of a grey label). The set_colour calls below therefore colour the
/// rectangles only, and pp_font_draw draws the letters exactly as the art lane authored them.
function pp_dialogue_draw(_d) {
    // The classic NES window frame from the art lane, nine sliced on the 8x8 tile grid. Drawn rectangles
    // remain as the fallback for a build without spr_pp_window.
    if (!pp_window_draw(PP_BOX_X, PP_BOX_Y, 30, 8, 1)) {
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(PP_BOX_X, PP_BOX_Y, PP_BOX_X + PP_BOX_W - 1, PP_BOX_Y + PP_BOX_H - 1, false);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(PP_BOX_X, PP_BOX_Y, PP_BOX_X + PP_BOX_W - 1, PP_BOX_Y + PP_BOX_H - 1, true);
        draw_rectangle(PP_BOX_X + 1, PP_BOX_Y + 1, PP_BOX_X + PP_BOX_W - 2, PP_BOX_Y + PP_BOX_H - 2, true);
    }

    if (is_undefined(_d) || _d.closed) return;

    var _page = _d.reveal.unit;
    var _page_data = _d.pages[_page];
    var _rows = _page_data.rows;
    var _plate = _page_data.speaker;
    var _bust = _page_data.portrait;

    // The portrait (spec 05 Geometry, card t_4d6b0f4b): a 48x48 bust standing on the box's top edge at (16, 120), so
    // it ends one pixel above the box and covers none of it, and the text area keeps all 28 of its columns. The sheet
    // is spr_pp_portrait_<name> on the same one-sheet index as the window and the font, so this is the same path the
    // rest of the box draws through. A page that names no bust draws none, and a page that names one the index does
    // not carry draws nothing and says so: a frame with nothing in it is the defect card t_01432e14 removed.
    if (_bust != "") {
        var _portrait = pp_art_info("spr_pp_portrait_" + _bust);
        if (is_undefined(_portrait)) {
            show_debug_message("PP: no portrait sheet for " + string(_bust));
        } else {
            draw_sprite_ext(_portrait.sprite, 0, PP_PORTRAIT_X, PP_PORTRAIT_Y, 1, 1, 0, PP_UNTINTED, 1);
        }
    }

    if (_plate != "narrator" && _plate != "") {
        // The plate is 64 wide and sits over the left of the top border. With a bust on the page it starts where the
        // bust ends (48 pixels from x 16 is x 63), so the two never share a pixel; without one it keeps its old inset.
        var _plate_x = PP_PLATE_X;
        if (_bust != "") _plate_x = PP_PLATE_BUST_X;
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(_plate_x, PP_BOX_Y - 6, _plate_x + PP_PLATE_W, PP_BOX_Y + 6, false);
        pp_font_draw(string_upper(_plate), _plate_x + 4, PP_BOX_Y - 4, 1);
    }

    // A page that offers choices does not share its three rows with the labels (spec 05, card t_01432e14): once the
    // last page has finished typing, its rows are replaced by one row per choice. The cursor is a 6x6 block in column
    // 0 of the text area and the label starts in column 1, so a choice glyph cannot land on a line of dialogue and the
    // box never has to cover its own text. The rows are not drawn first and painted over: they are not drawn at all.
    if (pp_dialogue_on_choice_page(_d) && _d.reveal.revealed >= pp_text_unit_length(_d.reveal)) {
        var _c = 0;
        while (_c < array_length(_d.choices)) {
            var _choice_y = PP_TEXT_Y + _c * PP_TEXT_LINE_H;
            if (_c == _d.cursor) {
                draw_set_colour(pp_role_colour("accent"));
                draw_rectangle(PP_CHOICE_ARROW_X, _choice_y + 1,
                    PP_CHOICE_ARROW_X + PP_CHOICE_ARROW_W - 1, _choice_y + PP_CHOICE_ARROW_W, false);
            }
            draw_set_colour(pp_role_colour("ink"));
            pp_font_draw(_d.choices[_c].label, PP_CHOICE_LABEL_X, _choice_y, 1);
            _c += 1;
        }
        return;
    }

    var _budget = _d.reveal.revealed;
    var _r = 0;
    while (_r < array_length(_rows)) {
        var _text = pp_text_visible(_rows[_r], _budget);
        pp_font_draw(_text, PP_TEXT_X, PP_TEXT_Y + _r * PP_TEXT_LINE_H, 1);
        _budget -= array_length(_rows[_r]);
        if (_budget < 0) _budget = 0;
        _r += 1;
    }

    var _phase = _d.reveal.steps mod (PP_ARROW_ON + PP_ARROW_OFF);
    if (_phase < PP_ARROW_ON) {
        draw_set_colour(pp_role_colour("accent"));
        draw_rectangle(236, 222, 241, 227, false);
        if (_page + 1 < array_length(_d.pages)) {
            draw_rectangle(230, 222, 235, 227, false);
        }
    }
}
