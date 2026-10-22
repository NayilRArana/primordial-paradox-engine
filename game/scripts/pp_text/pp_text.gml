/// pp_text: the one character reveal machine (FOX-STYLE section 7, law 8: one renderer per thing).
/// Everything that decides WHEN a character appears lives here: the item list a source line becomes, the hold value,
/// the speed, the punctuation pauses, the skip and the done predicate. A layout decides WHERE text is drawn and what
/// one unit of text looks like: pp_dialogue is a page with a portrait, pp_battle_text is a board with several lines
/// showing at once, and pp_title is the intro crawl, where one beat of the music is one unit and its rows stack
/// upward from the bottom of the frame. Three layouts, one revealer.
/// Provenance: knowledge\PROVENANCE.md, entries "text reveal machine: one implementation, two layouts" and "the title
/// crawl is a layout over the one reveal machine". The mechanism is spec 05 rules 1, 2, 3 and 5, plus the crawl
/// addendum of spec 14. No expression from a decompilation is used or needed for it.
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
/// dialogue page, one board line or one beat of the intro crawl; the machine never needs to know which.
/// _speaker pitches the blip and is "" for a layout that does not blip. _auto says whether the end of a unit advances
/// by itself after the gap, or waits for the layout to advance it. Both are layout settings, and neither one is a
/// reveal of its own. The three timings (speed, gap, blip interval) start on the spec 05 numbers and a layout with its
/// own passes them through pp_text_reveal_timing.
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
        speed: PP_TEXT_STEPS_SLOW,
        gap: PP_TEXT_PAUSE_STOP,
        blip: PP_TEXT_BLIP_EVERY,
        auto: _auto,
        done: (array_length(_units) == 0)
    };
}

/// Hand the machine a layout's own timings: steps per character, the gap at a unit end, and the blip interval. A
/// layout that passes nothing keeps the spec 05 numbers, which is what the box and the board want. The crawl passes
/// its own, because its speed is measured against the music (data\title_timing.json) and its gap is one beat of it.
/// These are three numbers on one machine, not a second reveal: nothing here decides WHEN a character appears except
/// by changing the number the one stepper already uses.
function pp_text_reveal_timing(_rv, _speed, _gap, _blip) {
    if (is_undefined(_rv)) return _rv;
    if (_speed > 0) _rv.speed = _speed;
    if (_gap >= 0) _rv.gap = _gap;
    if (_blip > 0) _rv.blip = _blip;
    return _rv;
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

    var _steps_per_char = _rv.speed;
    if (_fast) _steps_per_char = PP_TEXT_STEPS_FAST;
    if (!_fast && _item.speed > 0) _steps_per_char = max(PP_TEXT_STEPS_FAST, _item.speed);
    _rv.acc += 1;
    if (_rv.acc < _steps_per_char) return;
    // The remainder is carried, not dropped. At a whole number of steps a character (the box's 2, the fast 1) this
    // lands on zero and behaves exactly as a reset always did; at a fraction, which is what a speed measured against
    // the music gives (the crawl runs at 60 / 18 steps a character), dropping it would round every character up to
    // the next step and slow the text by a fifth.
    _rv.acc -= _steps_per_char;
    if (_rv.acc < 0) _rv.acc = 0;

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
    if (_item.ch != " " && _rv.speaker != "" && _rv.blip > 0 && _rv.revealed mod _rv.blip == 0) {
        _rv.blips += 1;
        // One blip every _rv.blip revealed characters (three, spec 05 rule 3), never on a space and pitched by
        // speaker. The interval is a field so a layout timed against the music can set its own; it is the same blip.
        // The call goes through pp_audio_blip, not pp_audio_play: the blip is a UI sound at priority 4 and 0.5 of the
        // effect level (spec 12 rules 2 and 6), and pp_audio_blip is the one place those two numbers live.
        pp_audio_blip(_rv.speaker);
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

/// Jump to the end: the last unit shown whole and the reveal done, with no hold left. This is the skip of a scene the
/// player may not want to sit through (the title crawl's start key), and it is the machine's own jump, so a layout
/// never walks the item list to finish it.
function pp_text_reveal_finish(_rv) {
    if (is_undefined(_rv)) return;
    var _last = array_length(_rv.units) - 1;
    if (_last < 0) {
        _rv.done = true;
        return;
    }
    _rv.unit = _last;
    _rv.revealed = array_length(_rv.units[_last]);
    _rv.acc = 0;
    _rv.wait = 0;
    _rv.done = true;
}
