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

/// Build pages from a dialogue record. One source line is one page (a source line break waits for confirm, rule 2),
/// and a page holds at most PP_TEXT_ROWS rows.
function pp_dialogue_build(_row) {
    var _pages = [];
    var _lines = _row.lines;
    var _i = 0;
    while (_i < array_length(_lines)) {
        var _rows = pp_dialogue_rows(_lines[_i]);
        var _start = 0;
        while (_start < array_length(_rows)) {
            var _page_rows = [];
            var _r = _start;
            while (_r < array_length(_rows) && _r < _start + PP_TEXT_ROWS) {
                array_push(_page_rows, _rows[_r]);
                _r += 1;
            }
            array_push(_pages, _page_rows);
            _start += PP_TEXT_ROWS;
        }
        _i += 1;
    }
    return _pages;
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

/// Open a dialogue by id: {id, speaker, pages, reveal, closed}. The reveal is the one in pp_text; this module holds no
/// cursor, no hold and no step count of its own.
function pp_dialogue_open(_dialogue_id) {
    var _row = pp_data_find(global.pp_data.dialogue.dialogue, _dialogue_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no dialogue with id " + string(_dialogue_id));
        return undefined;
    }
    var _pages = pp_dialogue_build(_row);
    if (array_length(_pages) == 0) return undefined;

    var _units = [];
    var _p = 0;
    while (_p < array_length(_pages)) {
        array_push(_units, pp_dialogue_page_unit(_pages[_p]));
        _p += 1;
    }

    // The box waits for confirm at the end of a page, so the machine advances only when this layout says so.
    return {
        id: _row.id,
        speaker: _row.speaker,
        pages: _pages,
        reveal: pp_text_reveal_begin(_units, _row.speaker, false),
        closed: false
    };
}

/// One step of the box: the machine types, the box draws whatever it has revealed.
function pp_dialogue_step(_d) {
    if (is_undefined(_d) || _d.closed) return;
    pp_text_reveal_step(_d.reveal, pp_action("confirm"));
}

/// Confirm: complete the page if it is still typing, otherwise turn the page or close. Returns true when it closed.
function pp_dialogue_advance(_d) {
    if (is_undefined(_d) || _d.closed) return true;
    if (_d.reveal.revealed < pp_text_unit_length(_d.reveal)) {
        pp_text_reveal_complete(_d.reveal);
        return false;
    }
    if (pp_text_reveal_next(_d.reveal)) {
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

    if (_d.speaker != "narrator" && _d.speaker != "") {
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(PP_BOX_X + 4, PP_BOX_Y - 6, PP_BOX_X + 68, PP_BOX_Y + 6, false);
        draw_set_colour(pp_role_colour("accent"));
        draw_text(PP_BOX_X + 8, PP_BOX_Y - 4, string_upper(_d.speaker));
    }

    var _page = _d.reveal.unit;
    var _rows = _d.pages[_page];
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

    var _phase = _d.reveal.steps mod (PP_ARROW_ON + PP_ARROW_OFF);
    if (_phase < PP_ARROW_ON) {
        draw_set_colour(pp_role_colour("accent"));
        draw_rectangle(236, 222, 241, 227, false);
        if (_page + 1 < array_length(_d.pages)) {
            draw_rectangle(230, 222, 235, 227, false);
        }
    }
}
