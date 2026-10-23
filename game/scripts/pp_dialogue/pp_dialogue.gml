/// pp_dialogue: the text box layout (spec 05) over the one reveal machine in pp_text.
/// This module owns the words' shape and place: word wrap, pages, the box, the portrait frame, the name plate and the
/// page arrow. It owns no reveal: the character timing, the holds, the punctuation pauses, the blip and the done
/// predicate belong to pp_text (law 8, one renderer per thing).
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
/// A choice list is 1 to 3 items: a label (12 characters, the panel column), the flags it sets, and an optional `goto`.
/// The flag names are data (data/flags.json) and the ledger owns them; this module only applies them, in one place.
/// No closures: the loops are written out for the same reason the rest of this file writes them out.
#macro PP_CHOICE_PANEL_W 96
#macro PP_CHOICE_ARROW_W 6
#macro PP_CHOICE_GAP 4

/// Build pages from a dialogue record. In the shorthand one source line is one page (a source line break waits for
/// confirm, rule 2) and a page holds at most PP_TEXT_ROWS rows; in the `pages` shape the data has already decided the
/// page breaks, so each page is taken as written and only re-paged if wrapping made it taller than the box.
function pp_dialogue_pages(_row) {
    var _pages = [];
    if (variable_struct_exists(_row, "pages") && is_array(_row.pages)) {
        var _p = 0;
        while (_p < array_length(_row.pages)) {
            var _page = _row.pages[_p];
            var _speaker = _row.speaker;
            if (variable_struct_exists(_page, "speaker")) _speaker = _page.speaker;
            pp_dialogue_push_page(_pages, _page.lines, _speaker);
            _p += 1;
        }
    } else {
        pp_dialogue_push_page(_pages, _row.lines, _row.speaker);
    }
    return _pages;
}

/// Wrap one run of source lines into pages of at most PP_TEXT_ROWS rows, each page carrying the speaker it is shown
/// under. A source line that wraps past the box becomes another page rather than a shorter box (rule 4).
function pp_dialogue_push_page(_pages, _lines, _speaker) {
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
            array_push(_pages, { speaker: _speaker, rows: _chunk });
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
    return {
        id: _row.id,
        speaker: _row.speaker,
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

/// Draw the box, the name plate, the visible rows and the arrow. Two inks only: text and highlight (rule 6).
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

    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(PP_PORTRAIT_X, PP_PORTRAIT_Y, PP_PORTRAIT_X + PP_PORTRAIT_SIZE - 1,
        PP_PORTRAIT_Y + PP_PORTRAIT_SIZE - 1, true);

    if (is_undefined(_d) || _d.closed) return;

    var _page = _d.reveal.unit;
    var _page_data = _d.pages[_page];
    var _rows = _page_data.rows;
    var _plate = _page_data.speaker;

    if (_plate != "narrator" && _plate != "") {
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(PP_BOX_X + 4, PP_BOX_Y - 6, PP_BOX_X + 68, PP_BOX_Y + 6, false);
        draw_set_colour(pp_role_colour("accent"));
        draw_text(PP_BOX_X + 8, PP_BOX_Y - 4, string_upper(_plate));
    }

    var _budget = _d.reveal.revealed;
    var _r = 0;
    draw_set_colour(pp_role_colour("ink"));
    while (_r < array_length(_rows)) {
        var _text = pp_text_visible(_rows[_r], _budget);
        draw_text(PP_TEXT_X, PP_TEXT_Y + _r * PP_TEXT_LINE_H, _text);
        _budget -= array_length(_rows[_r]);
        if (_budget < 0) _budget = 0;
        _r += 1;
    }

    // The choice panel: 96 pixels, right aligned inside the text area, one 6 pixel arrow, arrows wrap (spec 05).
    if (pp_dialogue_on_choice_page(_d) && _budget == 0) {
        var _panel_x = PP_TEXT_RIGHT - PP_CHOICE_PANEL_W;
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(_panel_x - PP_CHOICE_GAP, PP_TEXT_Y - 2,
            PP_TEXT_RIGHT, PP_TEXT_Y + array_length(_d.choices) * PP_TEXT_LINE_H, false);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(_panel_x - PP_CHOICE_GAP, PP_TEXT_Y - 2,
            PP_TEXT_RIGHT, PP_TEXT_Y + array_length(_d.choices) * PP_TEXT_LINE_H, true);
        var _c = 0;
        while (_c < array_length(_d.choices)) {
            var _choice_y = PP_TEXT_Y + _c * PP_TEXT_LINE_H;
            if (_c == _d.cursor) {
                draw_set_colour(pp_role_colour("accent"));
                draw_rectangle(_panel_x - PP_CHOICE_GAP - PP_CHOICE_ARROW_W - 1, _choice_y,
                    _panel_x - PP_CHOICE_GAP - 2, _choice_y + PP_CHOICE_ARROW_W - 1, false);
            }
            draw_set_colour(pp_role_colour("ink"));
            draw_text(_panel_x, _choice_y, _d.choices[_c].label);
            _c += 1;
        }
        return;
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
