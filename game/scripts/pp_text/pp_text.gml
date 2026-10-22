/// pp_text: the one character reveal machine (FOX-STYLE section 7, law 8: one renderer per thing).
/// Everything that decides WHEN a character appears lives here: the item list a source line becomes, the hold value,
/// the speed, the punctuation pauses, the skip and the done predicate. A layout decides WHERE text is drawn and what
/// one unit of text looks like: pp_dialogue is a page with a portrait, pp_battle_text is a board with several lines
/// showing at once. Two layouts, one revealer.
/// Provenance: knowledge\PROVENANCE.md, entry "text reveal machine: one implementation, two layouts". The mechanism is
/// spec 05 rules 1, 2, 3 and 5. No expression from a decompilation is used or needed for it.
/// No closures: every loop is written out, because a closure that reassigns an outer var is the kind of thing that
/// behaves differently between runtimes and cannot be tested on this PC.

/// Split one source line into items: {ch, wait, speed}. A control code becomes either a hold only item or a speed
/// change for everything after it, so the revealer can honour it without the caller knowing the codes exist.
function pp_text_items(_text) {
    var _items = [];
    var _len = string_length(_text);
    var _i = 1;
    var _speed = -1;
    while (_i <= _len) {
        var _ch = string_char_at(_text, _i);
        if (_ch == "{") {
            var _close = -1;
            var _scan = _i + 1;
            while (_scan <= _len) {
                if (string_char_at(_text, _scan) == "}") {
                    _close = _scan;
                    break;
                }
                _scan += 1;
            }
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

/// The visible text of an item list, cut to the first _budget items. A control code carries no character, so a code
/// never reaches the screen and never changes how many characters a row holds.
function pp_text_visible(_items, _budget) {
    if (is_undefined(_items)) return "";
    var _text = "";
    var _i = 0;
    while (_i < array_length(_items) && _i < _budget) {
        if (_items[_i].ch != "") _text += _items[_i].ch;
        _i += 1;
    }
    return _text;
}

/// How many items the current unit holds. Zero when the reveal is finished or missing, so a caller that reads it after
/// the end gets a number rather than an error.
function pp_text_unit_length(_rv) {
    if (is_undefined(_rv) || _rv.done) return 0;
    return array_length(_rv.units[_rv.unit]);
}

/// Begin a reveal over _units: an array of units, each unit a flat item list from pp_text_items. A unit is one
/// dialogue page or one board line; the machine never needs to know which.
/// _speaker pitches the blip and is "" for a layout that does not blip. _auto says whether the end of a unit advances
/// by itself after one punctuation sized hold, or waits for the layout to advance it. Both are layout settings, and
/// neither one is a reveal of its own.
function pp_text_reveal_begin(_units, _speaker, _auto) {
    return {
        units: _units,
        unit: 0,
        revealed: 0,
        acc: 0,
        wait: 0,
        steps: 0,
        blips: 0,
        speaker: _speaker,
        gap: PP_TEXT_PAUSE_STOP,
        auto: _auto,
        done: (array_length(_units) == 0)
    };
}

function pp_text_reveal_done(_rv) {
    if (is_undefined(_rv)) return true;
    return _rv.done;
}

/// One step of the reveal: the speed, the holds, the punctuation pauses, the blip, and the end of a unit.
/// Speed comes from PP_TEXT_STEPS_SLOW, or PP_TEXT_STEPS_FAST while the caller says the player is holding confirm
/// (spec 05 rule 1), or from a {speed:N} code already seen in the text.
function pp_text_reveal_step(_rv, _fast) {
    if (is_undefined(_rv) || _rv.done) return;
    _rv.steps += 1;
    if (_rv.wait > 0) {
        _rv.wait -= 1;
        return;
    }
    if (_rv.revealed >= pp_text_unit_length(_rv)) return;

    var _items = _rv.units[_rv.unit];
    var _item = _items[_rv.revealed];

    var _steps_per_char = PP_TEXT_STEPS_SLOW;
    if (_fast) _steps_per_char = PP_TEXT_STEPS_FAST;
    if (!_fast && _item.speed > 0) _steps_per_char = max(PP_TEXT_STEPS_FAST, _item.speed);
    _rv.acc += 1;
    if (_rv.acc < _steps_per_char) return;
    _rv.acc = 0;

    _rv.revealed += 1;
    if (_item.wait > 0) {
        _rv.wait += _item.wait;
        return;
    }
    if (_item.ch == "." || _item.ch == "!" || _item.ch == "?") {
        _rv.wait += PP_TEXT_PAUSE_STOP;
    } else if (_item.ch == ",") {
        _rv.wait += PP_TEXT_PAUSE_COMMA;
    }
    if (_item.ch != " " && _rv.speaker != "" && _rv.revealed mod PP_TEXT_BLIP_EVERY == 0) {
        _rv.blips += 1;
        // One blip every three revealed characters, never on a space, pitched by speaker (spec 05 rule 3).
        pp_audio_play(pp_audio_blip_cue(_rv.speaker));
    }

    // The end of a unit. A layout that advances by itself moves on after its own hold, which is a setting and not a
    // second revealer. A layout that waits for confirm leaves the unit filled until it calls pp_text_reveal_next.
    if (_rv.revealed >= pp_text_unit_length(_rv)) {
        if (_rv.unit + 1 >= array_length(_rv.units)) {
            _rv.done = true;
        } else if (_rv.auto) {
            _rv.unit += 1;
            _rv.revealed = 0;
            _rv.acc = 0;
            _rv.wait = max(_rv.wait, _rv.gap);
        }
    }
}

/// Reveal the rest of the current unit at once and drop any hold, which is what a confirm mid line does (spec 05
/// rule 2: it completes the line and does not advance twice).
function pp_text_reveal_complete(_rv) {
    if (is_undefined(_rv) || _rv.done) return;
    _rv.revealed = pp_text_unit_length(_rv);
    _rv.acc = 0;
    _rv.wait = 0;
}

/// Move on to the next unit and start it empty. Returns true when there is no next unit, which is the end of the text.
function pp_text_reveal_next(_rv) {
    if (is_undefined(_rv) || _rv.done) return true;
    if (_rv.unit + 1 >= array_length(_rv.units)) {
        _rv.done = true;
        return true;
    }
    _rv.unit += 1;
    _rv.revealed = 0;
    _rv.acc = 0;
    _rv.wait = 0;
    return false;
}
