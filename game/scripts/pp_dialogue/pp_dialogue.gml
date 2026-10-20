/// pp_dialogue: the text box (spec 05). Word wrap, a typewriter at 2 steps per character, confirm completes the line
/// then advances, and holding confirm runs at 1 step per character. No portraits exist yet, so the portrait frame
/// draws empty; the geometry is already the spec's.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The page and beat model is spec 05.
/// No closures: every loop is written out, because a closure that reassigns an outer var is the kind of thing that
/// behaves differently between runtimes and cannot be tested on this PC.

/// Split one source line into items: {ch, wait, speed}. A control code becomes either a wait only item or a speed
/// change, so the revealer can honour it without the wrapper knowing the codes exist.
function pp_dialogue_items(_text) {
    var _items = [];
    var _len = string_length(_text);
    var _i = 1;
    var _speed = -1;
    while (_i <= _len) {
        var _ch = string_char_at(_text, _i);
        if (_ch == "{") {
            var _close = string_pos("}", _text, _i);
            if (_close > _i) {
                var _body = string_copy(_text, _i + 1, _close - _i - 1);
                if (string_copy(_body, 1, 6) == "pause:") {
                    array_push(_items, { ch: "", wait: real(string_delete(_body, 1, 6)), speed: -1 });
                } else if (string_copy(_body, 1, 6) == "speed:") {
                    _speed = real(string_delete(_body, 1, 6));
                } else {
                    show_debug_message("PP: unknown dialogue control code " + _body);
                }
                _i = _close + 1;
                continue;
            }
        }
        array_push(_items, { ch: _ch, wait: 0, speed: _speed });
        _i += 1;
    }
    return _items;
}

/// Wrap one source line into rows of at most PP_TEXT_CHARS characters, by word. A word that does not fit moves whole
/// to the next row; a word that cannot fit in a row at all is split and reported, because dropping it is worse.
function pp_dialogue_rows(_text) {
    var _items = pp_dialogue_items(_text);

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

function pp_dialogue_page_length(_rows) {
    var _n = 0;
    var _i = 0;
    while (_i < array_length(_rows)) {
        _n += array_length(_rows[_i]);
        _i += 1;
    }
    return _n;
}

/// The item at a flat index on a page, or undefined past the end.
function pp_dialogue_item_at(_rows, _index) {
    var _seen = 0;
    var _r = 0;
    while (_r < array_length(_rows)) {
        var _row_items = _rows[_r];
        var _c = 0;
        while (_c < array_length(_row_items)) {
            if (_seen == _index) return _row_items[_c];
            _seen += 1;
            _c += 1;
        }
        _r += 1;
    }
    return undefined;
}

/// Open a dialogue by id: {id, speaker, pages, page, revealed, total, acc, wait, steps, blips, closed}.
function pp_dialogue_open(_dialogue_id) {
    var _row = pp_data_find(global.pp_data.dialogue.dialogue, _dialogue_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no dialogue with id " + string(_dialogue_id));
        return undefined;
    }
    var _pages = pp_dialogue_build(_row);
    if (array_length(_pages) == 0) return undefined;

    return {
        id: _row.id,
        speaker: _row.speaker,
        pages: _pages,
        page: 0,
        revealed: 0,
        total: pp_dialogue_page_length(_pages[0]),
        acc: 0,
        wait: 0,
        steps: 0,
        blips: 0,
        closed: false
    };
}

/// One step: the typewriter, the punctuation pauses, the {pause:N} and {speed:N} codes, and the blink clock.
function pp_dialogue_step(_d) {
    if (is_undefined(_d) || _d.closed) return;
    _d.steps += 1;
    if (_d.wait > 0) {
        _d.wait -= 1;
        return;
    }
    if (_d.revealed >= _d.total) return;

    var _rows = _d.pages[_d.page];
    var _item = pp_dialogue_item_at(_rows, _d.revealed);

    var _steps_per_char = pp_action("confirm") ? PP_TEXT_STEPS_FAST : PP_TEXT_STEPS_SLOW;
    if (!is_undefined(_item) && _item.speed > 0 && !pp_action("confirm")) {
        _steps_per_char = max(PP_TEXT_STEPS_FAST, _item.speed);
    }
    _d.acc += 1;
    if (_d.acc < _steps_per_char) return;
    _d.acc = 0;

    _d.revealed += 1;
    if (is_undefined(_item)) return;
    if (_item.wait > 0) {
        _d.wait += _item.wait;
        return;
    }
    if (_item.ch == "." || _item.ch == "!" || _item.ch == "?") {
        _d.wait += PP_TEXT_PAUSE_STOP;
    } else if (_item.ch == ",") {
        _d.wait += PP_TEXT_PAUSE_COMMA;
    }
    if (_item.ch != " " && _d.revealed mod PP_TEXT_BLIP_EVERY == 0) _d.blips += 1;
}

/// Confirm: complete the page if it is still typing, otherwise turn the page or close. Returns true when it closed.
function pp_dialogue_advance(_d) {
    if (is_undefined(_d) || _d.closed) return true;
    if (_d.revealed < _d.total) {
        _d.revealed = _d.total;
        _d.wait = 0;
        return false;
    }
    _d.page += 1;
    if (_d.page >= array_length(_d.pages)) {
        _d.closed = true;
        return true;
    }
    _d.revealed = 0;
    _d.total = pp_dialogue_page_length(_d.pages[_d.page]);
    _d.acc = 0;
    _d.wait = 0;
    return false;
}

function pp_dialogue_closed(_d) {
    if (is_undefined(_d)) return true;
    return _d.closed;
}

/// Build the visible string for a row given how many of its items are revealed.
function pp_dialogue_row_text(_row_items, _budget) {
    var _text = "";
    var _i = 0;
    while (_i < array_length(_row_items) && _i < _budget) {
        if (_row_items[_i].ch != "") _text += _row_items[_i].ch;
        _i += 1;
    }
    return _text;
}

/// Draw the box, the name plate, the visible rows and the arrow. Two inks only: text and highlight (rule 6).
function pp_dialogue_draw(_d) {
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(PP_BOX_X, PP_BOX_Y, PP_BOX_X + PP_BOX_W - 1, PP_BOX_Y + PP_BOX_H - 1, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(PP_BOX_X, PP_BOX_Y, PP_BOX_X + PP_BOX_W - 1, PP_BOX_Y + PP_BOX_H - 1, true);
    draw_rectangle(PP_BOX_X + 1, PP_BOX_Y + 1, PP_BOX_X + PP_BOX_W - 2, PP_BOX_Y + PP_BOX_H - 2, true);

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

    var _rows = _d.pages[_d.page];
    var _budget = _d.revealed;
    var _r = 0;
    draw_set_colour(pp_role_colour("ink"));
    while (_r < array_length(_rows)) {
        var _text = pp_dialogue_row_text(_rows[_r], _budget);
        draw_text(PP_TEXT_X, PP_TEXT_Y + _r * PP_TEXT_LINE_H, _text);
        _budget -= array_length(_rows[_r]);
        if (_budget < 0) _budget = 0;
        _r += 1;
    }

    var _phase = _d.steps mod (PP_ARROW_ON + PP_ARROW_OFF);
    if (_phase < PP_ARROW_ON) {
        draw_set_colour(pp_role_colour("accent"));
        draw_rectangle(236, 222, 241, 227, false);
        if (_d.page + 1 < array_length(_d.pages)) {
            draw_rectangle(230, 222, 235, 227, false);
        }
    }
}
