/// pp_battle_text: the battle message board layout (spec 07 rule 6, spec 05 typing rules) over the one reveal machine
/// in pp_text. This module owns the board's shape: which lines show at once, where they sit, and how they wrap. The
/// character timing, the holds, the punctuation pauses, the blip and the done predicate belong to pp_text (law 8, one
/// renderer per thing).
/// The one policy difference from the dialogue box is that the board advances by itself at the end of a line. That is
/// a setting the layout passes to the machine (auto, with a gap of PP_TEXT_PAUSE_STOP), not a second revealer.
/// No portraits and no choices here: those are spec 05 and belong to pp_dialogue.

/// Build a board from an array of lines. One line is one unit of the reveal, so the same text typed into the board and
/// into the box reveals in the same order with the same pauses, because pp_text_items builds both item lists.
function pp_text_board(_lines) {
    var _copy = [];
    var _units = [];
    for (var i = 0; i < array_length(_lines); i++) {
        array_push(_copy, _lines[i]);
        array_push(_units, pp_text_items(_lines[i]));
    }
    return {
        lines: _copy,
        reveal: pp_text_reveal_begin(_units, "", true)
    };
}

/// One step of typing. Stops at the end of the last line and stays there until the caller reads done.
function pp_text_board_step(_board, _fast) {
    if (is_undefined(_board)) return _board;
    pp_text_reveal_step(_board.reveal, _fast);
    return _board;
}

/// Complete the current line at once, which is what a first confirm does (spec 05 rule 2), then move to the next one.
function pp_text_board_skip_line(_board) {
    if (is_undefined(_board)) return _board;
    pp_text_reveal_complete(_board.reveal);
    pp_text_reveal_next(_board.reveal);
    return _board;
}

function pp_text_board_done(_board) {
    if (is_undefined(_board)) return true;
    return pp_text_reveal_done(_board.reveal);
}

/// Draw the lines that have been revealed so far. Wrapping is left to draw_text_ext so a data line never truncates
/// silently, and the checker is the place that refuses an over long line before it ships.
function pp_text_board_draw(_board, _x, _y, _colour) {
    draw_set_colour(_colour);
    draw_set_halign(fa_left);
    var _shown = 0;
    var _units = _board.reveal.units;
    var _unit = _board.reveal.unit;
    for (var i = 0; i <= _unit && i < array_length(_units); i++) {
        var _text = pp_text_visible(_units[i], array_length(_units[i]));
        if (i == _unit) _text = pp_text_visible(_units[i], _board.reveal.revealed);
        if (_text != "") {
            draw_text_ext(_x, _y + _shown * 10, _text, 10, PP_FRAME_W - 32);
            _shown += 1;
        }
    }
}
