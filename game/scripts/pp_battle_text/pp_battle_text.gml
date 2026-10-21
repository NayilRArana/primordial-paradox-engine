/// pp_battle_text: the message board used by the battle director (spec 07 rule 6, spec 05 typing rules).
/// This is the battle subset only: typewriter, hold prompt, no portraits and no choices. The full dialogue system
/// with portraits and choice panels is spec 05 and is not in this pass.

#macro PP_TEXT_STEPS_PER_CHAR 2
// PP_TEXT_PAUSE_STOP and PP_TEXT_PAUSE_COMMA are defined in pp_config. Macros are global, so a second
// definition here is a compile error.

/// Build a board from an array of lines.
function pp_text_board(_lines) {
    var _copy = [];
    for (var i = 0; i < array_length(_lines); i++) array_push(_copy, _lines[i]);
    return {
        lines: _copy,
        index: 0,
        revealed: 0,
        timer: 0,
        pause: 0,
        done: (array_length(_copy) == 0)
    };
}

/// One step of typing. Stops at the end of the last line and stays there until the caller reads done.
function pp_text_board_step(_board, _fast) {
    if (_board.done) return _board;
    if (_board.index >= array_length(_board.lines)) {
        _board.done = true;
        return _board;
    }

    var _line = _board.lines[_board.index];
    if (_board.pause > 0) {
        _board.pause -= 1;
        return _board;
    }

    _board.timer += 1;
    var _need = _fast ? 1 : PP_TEXT_STEPS_PER_CHAR;
    if (_board.timer >= _need) {
        _board.timer = 0;
        _board.revealed += 1;
        if (_board.revealed > string_length(_line)) {
            _board.revealed = string_length(_line);
        }
        var _last = string_char_at(_line, _board.revealed);
        if (_last == "." || _last == "!" || _last == "?") _board.pause = PP_TEXT_PAUSE_STOP;
        else if (_last == ",") _board.pause = PP_TEXT_PAUSE_COMMA;

        if (_board.revealed >= string_length(_line)) {
            if (_board.index < array_length(_board.lines) - 1) {
                _board.index += 1;
                _board.revealed = 0;
                _board.timer = 0;
                _board.pause = PP_TEXT_PAUSE_STOP;
            } else {
                _board.done = true;
            }
        }
    }
    return _board;
}

/// Complete the current line at once, which is what a first confirm does (spec 05 rule 2).
function pp_text_board_skip_line(_board) {
    if (_board.done) return _board;
    var _line = _board.lines[_board.index];
    _board.revealed = string_length(_line);
    _board.timer = 0;
    _board.pause = 0;
    if (_board.index < array_length(_board.lines) - 1) {
        _board.index += 1;
        _board.revealed = 0;
    } else {
        _board.done = true;
    }
    return _board;
}

function pp_text_board_done(_board) {
    return _board.done;
}

/// Draw the lines that have been revealed so far. Wrapping is left to draw_text_ext so a data line never truncates
/// silently, and the checker is the place that refuses an over long line before it ships.
function pp_text_board_draw(_board, _x, _y, _colour) {
    draw_set_colour(_colour);
    draw_set_halign(fa_left);
    var _shown = 0;
    for (var i = 0; i <= _board.index && i < array_length(_board.lines); i++) {
        var _text = _board.lines[i];
        if (i == _board.index) _text = string_copy(_text, 1, _board.revealed);
        if (_text != "") {
            draw_text_ext(_x, _y + _shown * 10, _text, 10, PP_FRAME_W - 32);
            _shown += 1;
        }
    }
}
