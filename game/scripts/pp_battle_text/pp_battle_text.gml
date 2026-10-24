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

/// Draw the lines that have been revealed so far.
/// Card BATTLE-FONT-WIRE: the words are the sheet's glyphs, and the wrap is a column count rather than a pixel width,
/// because every glyph in the sheet is 8 px wide. A line that wraps to two rows pushes the next line down by the rows
/// it actually took, so two long lines cannot print over each other. 28 columns is the window's 224 px inside
/// (PP_FRAME_W - 32); the checker is still the place that refuses a line the sheet cannot draw.
function pp_text_board_draw(_board, _x, _y) {
    var _cols = pp_font_cols(PP_FRAME_W - 32);
    var _shown = 0;
    var _units = _board.reveal.units;
    var _unit = _board.reveal.unit;
    for (var i = 0; i <= _unit && i < array_length(_units); i++) {
        var _text = pp_text_visible(_units[i], array_length(_units[i]));
        if (i == _unit) _text = pp_text_visible(_units[i], _board.reveal.revealed);
        if (_text != "") {
            _shown += pp_font_draw_wrapped(_text, _x, _y + _shown * 10, _cols, 10, 1);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The baked talk path (card R30, spec 19 sections 4 to 11, D5, D6 Q1 to Q10)
//
// The shipped game reads its talk words from data/meta_bake.json and from nothing else. This module owns that read:
// the load and its validation (spec 19 section 4 and layer B), the five effect enum and the mercy arithmetic the game
// does itself (section 6), the option list a fight draws (section 2's first two rows), the reply block of four lines
// of 28 at an 8 pixel pitch with the hint under them (section 5, Q2 and Q9), and the two NPC voices (Q5 and Q10).
//
// It makes no request and holds no endpoint: the bake tool is the only thing that ever calls, and this file reads one
// local data file through pp_data_json, the same door every other data file comes through. tools/check_data.py and
// tests/test_talk_baked.py refuse a network function or an address anywhere under game/.
//
// The fallback ladder is spec 19 section 8 and it is built in here, not bolted on: a bake row, then the card's own
// pools in data/talk_cards.json, then the encounter's talk row. An enemy with no baked row keeps its canned card, so
// the fight is winnable with any model or none (section 11).

/// The five effects and the five moods, spelled the way section 4 and data/meta_bake.json spell them.
function pp_talk_effects() { return ["none", "nudge", "soften", "setback", "end"]; }
function pp_talk_moods() { return ["calm", "guarded", "rattled", "warm", "angry"]; }

/// Which effects are legal in which scene (section 6 rule 2: soften, nudge and setback are refused in the npc scene).
function pp_talk_fight_effects() { return ["none", "nudge", "soften", "setback"]; }
function pp_talk_npc_effects() { return ["none", "end"]; }

function pp_talk_effect_legal(_effect, _scene) {
    var _set = (_scene == "npc") ? pp_talk_npc_effects() : pp_talk_fight_effects();
    for (var i = 0; i < array_length(_set); i++) {
        if (_set[i] == _effect) return true;
    }
    return false;
}

function pp_talk_mood_legal(_mood) {
    var _set = pp_talk_moods();
    for (var i = 0; i < array_length(_set); i++) {
        if (_set[i] == _mood) return true;
    }
    return false;
}

/// Spec 19 section 4: on a missing or unknown mood the game derives one from the effect, and section 6 owns the table.
function pp_talk_effect_mood(_effect) {
    switch (_effect) {
        case "soften": return "warm";
        case "nudge":  return "calm";
        case "setback": return "angry";
        case "end":    return "calm";
    }
    return "guarded";
}

/// The effect table of spec 19 section 6, in the game and not in a reply. The model never sends a number, so this is
/// the only place a talk turn's mercy change is computed.
/// soften reads the encounter's own talk.mercy_per_option, because spec 19 check 3 requires the two to be equal and a
/// second copy of 20 would be a second source. nudge, none and setback are spec 16 section 2's rows: +5, 0 and -10.
function pp_talk_effect_delta(_effect, _battle) {
    switch (_effect) {
        case "soften":
            if (is_struct(_battle) && variable_struct_exists(_battle, "encounter")
                && is_struct(_battle.encounter) && variable_struct_exists(_battle.encounter, "talk")
                && is_struct(_battle.encounter.talk)
                && variable_struct_exists(_battle.encounter.talk, "mercy_per_option")) {
                return _battle.encounter.talk.mercy_per_option;
            }
            return 20;
        case "nudge":   return 5;
        case "setback": return -10;
    }
    return 0;
}

/// One character the sheet cannot draw is a reply the game would render as a hole, so it is refused at the load
/// instead (section 4: the alphabet is the font's own). pp_font_glyphs is the one list of what the font has.
function pp_talk_line_drawable(_text) {
    for (var i = 1; i <= string_length(_text); i++) {
        if (pp_font_glyph_index(string_char_at(_text, i)) < 0) return false;
    }
    return true;
}

/// Cut a line to a column count at its last space, so a word is never split (section 4, "cut at the last space").
function pp_talk_cut(_text, _cols) {
    if (string_length(_text) <= _cols) return _text;
    var _cut = string_copy(_text, 1, _cols);
    var _space = 0;
    for (var i = _cols; i >= 1; i -= 1) {
        if (string_char_at(_cut, i) == " ") { _space = i; break; }
    }
    if (_space > 1) return string_copy(_cut, 1, _space - 1);
    return _cut;
}

/// Validate one baked row exactly as the spec 19 section 4 table says, and return the four fields the game uses.
/// Undefined means the whole reply is refused: no state change, and the card pool answers that turn instead.
function pp_talk_reply_clean(_row, _scene) {
    if (!is_struct(_row)) return undefined;
    if (!variable_struct_exists(_row, "text") || !is_array(_row.text)) return undefined;
    if (array_length(_row.text) == 0) return undefined;

    var _lines = [];
    var _repaired = false;
    for (var i = 0; i < array_length(_row.text); i++) {
        if (i >= 4) { _repaired = true; break; }
        var _line = string(_row.text[i]);
        if (_line == "") { _repaired = true; continue; }
        if (!pp_talk_line_drawable(_line)) return undefined;
        if (string_length(_line) > 28) {
            _line = pp_talk_cut(_line, 28);
            _repaired = true;
        }
        array_push(_lines, _line);
    }
    if (array_length(_lines) == 0) return undefined;

    var _effect = "none";
    if (variable_struct_exists(_row, "effect") && is_string(_row.effect)) _effect = _row.effect;
    if (!pp_talk_effect_legal(_effect, _scene)) {
        _effect = "none";
        _repaired = true;
    }

    var _mood = pp_talk_effect_mood(_effect);
    if (variable_struct_exists(_row, "mood") && is_string(_row.mood) && pp_talk_mood_legal(_row.mood)) {
        _mood = _row.mood;
    } else {
        _repaired = true;
    }

    var _hint = "";
    if (variable_struct_exists(_row, "hint") && is_string(_row.hint)) {
        _hint = _row.hint;
        if (!pp_talk_line_drawable(_hint)) _hint = "";
        if (string_length(_hint) > 28) {
            _hint = pp_talk_cut(_hint, 28);
            _repaired = true;
        }
    }
    return { text: _lines, mood: _mood, effect: _effect, hint: _hint, repaired: _repaired };
}

/// Load and validate data/meta_bake.json once, at the first talk, and keep it in global.pp_talk_bake.
/// Fight rows are keyed card plus phase (the two names spec 16 section 10 decided) and stored by option, NPC rows are
/// keyed by npc and stored by turn. The request hash is an audit field: recomputing it needs the whole prompt, and an
/// address is not a thing this game holds (knowledge/REVIEW-META-BAKE-2026-10-23.md Q1 and Q2).
/// A missing file, an unreadable one, or a row off contract leaves an empty map and the ladder falls to the pools.
function pp_talk_bake() {
    // Card t_27aa179e: the table lives under global.pp_talk_bake_table and NOT under the function's own name. A
    // script function is itself a global variable in GMS2.3+, so the old guard `variable_global_exists("pp_talk_bake")
    // && is_struct(global.pp_talk_bake)` was true before the first call ever ran: the function answered with itself,
    // the table was never built, and reading `.fight` off a function killed the game the first time anyone pressed
    // TALK in a release build (`Variable <unknown_object>.fight not set before reading it`). The name is now distinct
    // from every function in the project, which is the only thing that makes this cache a cache.
    if (variable_global_exists("pp_talk_bake_table") && is_struct(global.pp_talk_bake_table)) return global.pp_talk_bake_table;

    var _bake = { loaded: false, rows: 0, refused: 0, fight: {}, npc: {} };
    var _doc = pp_data_json("meta_bake.json");
    if (is_struct(_doc) && is_array(_doc.rows)) {
        _bake.loaded = true;
        for (var i = 0; i < array_length(_doc.rows); i++) {
            var _row = _doc.rows[i];
            if (!is_struct(_row) || !variable_struct_exists(_row, "scene")) {
                _bake.refused += 1;
                continue;
            }
            var _reply = pp_talk_reply_clean(_row, string(_row.scene));
            if (is_undefined(_reply)) {
                _bake.refused += 1;
                continue;
            }

            if (_row.scene == "fight") {
                var _card = "";
                if (variable_struct_exists(_row, "card")) _card = string(_row.card);
                if (_card == "") { _bake.refused += 1; continue; }
                var _phase = "";
                if (variable_struct_exists(_row, "phase")) _phase = string(_row.phase);
                var _key = _card + "|" + _phase;
                var _option = 1;
                if (variable_struct_exists(_row, "option")) _option = max(1, floor(_row.option));
                if (!variable_struct_exists(_bake.fight, _key)) _bake.fight[$ _key] = [];
                var _list = _bake.fight[$ _key];
                while (array_length(_list) < _option) array_push(_list, undefined);
                _list[_option - 1] = _reply;
                _bake.fight[$ _key] = _list;
            } else if (_row.scene == "npc") {
                var _npc = "";
                if (variable_struct_exists(_row, "npc")) _npc = string(_row.npc);
                if (_npc == "") { _bake.refused += 1; continue; }
                var _turn = 1;
                if (variable_struct_exists(_row, "turn")) _turn = max(1, floor(_row.turn));
                if (!variable_struct_exists(_bake.npc, _npc)) _bake.npc[$ _npc] = [];
                var _turns = _bake.npc[$ _npc];
                while (array_length(_turns) < _turn) array_push(_turns, undefined);
                _turns[_turn - 1] = _reply;
                _bake.npc[$ _npc] = _turns;
            } else {
                _bake.refused += 1;
                continue;
            }
            _bake.rows += 1;
        }
    }
    global.pp_talk_bake_table = _bake;
    show_debug_message("PP: talk bake, " + string(_bake.rows) + " rows kept of "
        + string(_bake.rows + _bake.refused) + " read, " + string(array_length(variable_struct_get_names(_bake.fight)))
        + " fight keys, " + string(array_length(variable_struct_get_names(_bake.npc))) + " npc keys");
    return _bake;
}

/// The bake's fight table, or an empty one. ONE guarded read, because a fight must not die on a member lookup.
///
/// Card t_27aa179e. Reading `_bake.fight` straight off the return of pp_talk_bake killed the game on the first TALK
/// ever pressed in a release build: `PP CRASH: Variable <unknown_object>.fight not set before reading it` at
/// pp_talk_options. Whatever the bake turns out to be (an older shape, a refused load, or a value that is not the
/// struct this file builds), a data read that can end the fight is a bug on its own, so every caller asks here and a
/// table that is not there is an empty table. The ladder then falls to the card pools, which is the behaviour the
/// file's own header already promises for a missing file.
function pp_talk_bake_fight() {
    var _bake = pp_talk_bake();
    if (!is_struct(_bake) || !variable_struct_exists(_bake, "fight") || !is_struct(_bake.fight)) {
        show_debug_message("PP: talk bake has no fight table, the card pools answer this fight");
        return {};
    }
    return _bake.fight;
}

/// The bake's npc table, or an empty one, through the same guarded read.
function pp_talk_bake_npc() {
    var _bake = pp_talk_bake();
    if (!is_struct(_bake) || !variable_struct_exists(_bake, "npc") || !is_struct(_bake.npc)) {
        show_debug_message("PP: talk bake has no npc table, the card pools answer these voices");
        return {};
    }
    return _bake.npc;
}

/// Drop the loaded table, so a scene reload or a test reads the file again.
function pp_talk_bake_forget() {
    global.pp_talk_bake_table = undefined;
}

/// The card and phase of the talk card this fight is using, spelled the way the bake keys its rows.
/// The phase comes off the enemy's own phase row (spec 16 section 10: the row's talk_phase names the card's phase),
/// never off the enemy's id, so no branch in this file tests a name.
function pp_talk_bake_key(_battle) {
    var _card = "";
    if (is_struct(_battle) && variable_struct_exists(_battle, "encounter") && is_struct(_battle.encounter)
        && variable_struct_exists(_battle.encounter, "talk") && is_struct(_battle.encounter.talk)
        && variable_struct_exists(_battle.encounter.talk, "card")) {
        _card = string(_battle.encounter.talk.card);
    }
    if (_card == "") return "";

    var _phase = "";
    var _rows = pp_battle_enemy_phases(_battle.enemy);
    if (_battle.enemy_phase > 0 && _battle.enemy_phase <= array_length(_rows)) {
        var _row = _rows[_battle.enemy_phase - 1];
        if (variable_struct_exists(_row, "talk_phase") && is_string(_row.talk_phase)) _phase = _row.talk_phase;
    }
    return _card + "|" + _phase;
}

// ---------------------------------------------------------------------------------------------------------------
// The card pools, the second rung (spec 19 section 8 rung 2, spec 16 section 9 step 5)

/// data/talk_cards.json, parsed once. This is a read of a local file through the same door as every other data file.
function pp_talk_cards() {
    if (variable_global_exists("pp_talk_cards") && is_struct(global.pp_talk_cards)) return global.pp_talk_cards;
    var _doc = pp_data_json("talk_cards.json");
    var _index = {};
    if (is_struct(_doc) && is_array(_doc.cards)) {
        for (var i = 0; i < array_length(_doc.cards); i++) {
            var _card = _doc.cards[i];
            if (!is_struct(_card) || !variable_struct_exists(_card, "id")) continue;
            var _phase = "";
            if (variable_struct_exists(_card, "phase")) _phase = string(_card.phase);
            _index[$ string(_card.id) + "|" + _phase] = _card;
        }
    }
    global.pp_talk_cards = _index;
    return _index;
}

/// The card this fight talks to, or undefined. Card first, then the enemy id, because a row may name either.
function pp_talk_card_row(_battle) {
    var _index = pp_talk_cards();
    var _key = pp_talk_bake_key(_battle);
    if (_key != "" && variable_struct_exists(_index, _key)) return _index[$ _key];
    if (is_struct(_battle.enemy) && variable_struct_exists(_battle.enemy, "id")) {
        var _fallback = string(_battle.enemy.id) + "|";
        if (variable_struct_exists(_index, _fallback)) return _index[$ _fallback];
    }
    return undefined;
}

/// The mercy band a pool is picked in: low 0 to 19, mid 20 to 59, high 60 to 100 (spec 16 section 9 step 5).
function pp_talk_band(_mercy) {
    if (_mercy >= 60) return "high";
    if (_mercy >= 20) return "mid";
    return "low";
}

/// One pool of a card as a flat array, whether the data wrote it as a plain list or as the three buckets.
function pp_talk_pool(_card, _class, _mercy) {
    if (!is_struct(_card) || !variable_struct_exists(_card, "pools")) return [];
    var _pools = _card.pools;
    if (!variable_struct_exists(_pools, _class)) return [];
    var _pool = _pools[$ _class];
    if (is_array(_pool)) return _pool;
    if (is_struct(_pool) && variable_struct_exists(_pool, pp_talk_band(_mercy))) {
        return _pool[$ pp_talk_band(_mercy)];
    }
    if (is_struct(_pool) && variable_struct_exists(_pool, "mid")) return _pool.mid;
    return [];
}

/// A stable hash of one line, for the pool index. It is a hash of our own (31 and a large prime) rather than the
/// 32 bit FNV of the spec, because a GameMaker number is a double and the low bits of a 32 bit multiply past 2^53 are
/// gone: a hash whose low bits drift is not deterministic, and determinism is the whole point of the rung.
/// No RNG anywhere, so a replay of the same talk says the same words (spec 19 check 12.3).
function pp_talk_hash(_text) {
    var _h = 7;
    for (var i = 1; i <= string_length(_text); i++) {
        _h = (_h * 31 + ord(string_char_at(_text, i))) mod 1000000007;
    }
    return _h;
}

/// The normalised line the index hashes: lower case, single spaces, no surrounding punctuation (spec 16 section 8).
function pp_talk_normalise(_text) {
    var _out = string_lower(string_trim(_text));
    while (string_pos("  ", _out) > 0) _out = string_replace_all(_out, "  ", " ");
    while (string_length(_out) > 0) {
        var _first = string_char_at(_out, 1);
        if (string_pos(_first, " .,:;!?'\"*") > 0) _out = string_delete(_out, 1, 1);
        else break;
    }
    return _out;
}

/// Wrap a hand written line into rows of at most _cols at a word break, at most four rows, no word split.
/// This is for the card's own rows and never for a model line: spec 19 check 5 says the pool strings are the ones the
/// game wraps, because a model line already carries the breaks its own writer chose (Q1) and is never re-flowed.
function pp_talk_wrap(_text, _cols) {
    var _out = [];
    var _words = string_split(string_trim(string(_text)), " ");
    var _row = "";
    for (var i = 0; i < array_length(_words); i++) {
        var _word = _words[i];
        if (_word == "") continue;
        var _try = (_row == "") ? _word : _row + " " + _word;
        if (string_length(_try) <= _cols) {
            _row = _try;
            continue;
        }
        if (_row != "") array_push(_out, _row);
        _row = pp_talk_cut(_word, _cols);
    }
    if (_row != "") array_push(_out, _row);
    while (array_length(_out) > pp_talk_lines_max()) array_delete(_out, array_length(_out) - 1, 1);
    return _out;
}

/// Pick one line out of a card's pool: index = (hash(normalised line) + mercy) modulo the pool length.
function pp_talk_pool_line(_battle, _class, _seed_text) {
    var _card = pp_talk_card_row(_battle);
    var _pool = pp_talk_pool(_card, _class, _battle.talk_mercy);
    if (array_length(_pool) == 0) return [];
    var _index = (pp_talk_hash(pp_talk_normalise(_seed_text)) + _battle.talk_mercy) mod array_length(_pool);
    var _line = string(_pool[_index]);
    if (!pp_talk_line_drawable(_line)) return [];
    return pp_talk_wrap(_line, 28);
}

// ---------------------------------------------------------------------------------------------------------------
// The option list (spec 19 section 2, spec 16 section 1 step 1)

/// The dialogue id the option labels come from: the encounter's talk row first, the enemy's own row second.
function pp_talk_options_dialogue(_battle) {
    if (is_struct(_battle) && variable_struct_exists(_battle, "encounter") && is_struct(_battle.encounter)
        && variable_struct_exists(_battle.encounter, "talk") && is_struct(_battle.encounter.talk)
        && variable_struct_exists(_battle.encounter.talk, "options_dialogue")) {
        return string(_battle.encounter.talk.options_dialogue);
    }
    if (is_struct(_battle.enemy) && variable_struct_exists(_battle.enemy, "talk_dialogue")) {
        return string(_battle.enemy.talk_dialogue);
    }
    return "";
}

/// A dialogue line as a panel label: the narration marker and the speech quotes are not part of what the player picks.
function pp_talk_option_label(_line) {
    var _text = string_trim(string(_line));
    if (string_length(_text) >= 2 && string_copy(_text, 1, 2) == "* ") _text = string_delete(_text, 1, 2);
    if (string_length(_text) >= 2) {
        if (string_char_at(_text, 1) == "\"" && string_char_at(_text, string_length(_text)) == "\"") {
            _text = string_delete(_text, 1, 1);
            _text = string_delete(_text, string_length(_text), 1);
        }
    }
    return pp_talk_cut(string_trim(_text), 28);
}

/// Code prepends the marker, never the model and never the data (D6 Q6): a baked fight line is narration and is drawn
/// with the same `* ` run a hand written dialogue line carries, and `* ` plus 28 is exactly spec 05's 30 columns.
function pp_talk_narration(_lines) {
    var _out = [];
    for (var i = 0; i < array_length(_lines); i++) array_push(_out, "* " + string(_lines[i]));
    return _out;
}

/// The three options of this turn. Each is a record the step and the draw both read:
///   label   what the panel shows          source  the authored dialogue line it came from
///   effect  the effect enum, or none      delta   the row's mercy number, computed here and never in a reply
///   lines   what the box plays            hint    the line under the box, "" when the row carries none
///   baked   true when this came from data/meta_bake.json, false when the card pool answered
function pp_talk_options(_battle) {
    var _out = [];
    var _lines = pp_battle_dialogue(pp_talk_options_dialogue(_battle));
    if (!is_array(_lines)) return _out;

    var _count = array_length(_lines);
    if (is_struct(_battle.encounter) && variable_struct_exists(_battle.encounter, "talk")
        && is_struct(_battle.encounter.talk) && variable_struct_exists(_battle.encounter.talk, "option_count")) {
        _count = min(_count, _battle.encounter.talk.option_count);
    }

    var _bake_fight = pp_talk_bake_fight();
    var _key = pp_talk_bake_key(_battle);
    var _baked = [];
    if (_key != "" && variable_struct_exists(_bake_fight, _key)) _baked = _bake_fight[$ _key];
    if (is_undefined(_baked)) _baked = [];

    for (var i = 0; i < _count; i++) {
        var _reply = undefined;
        if (i < array_length(_baked)) _reply = _baked[i];

        var _record = {
            label: pp_talk_option_label(_lines[i]),
            source: _lines[i],
            baked: false,
            effect: "none",
            mood: "guarded",
            delta: 0,
            lines: [],
            hint: ""
        };

        if (!is_undefined(_reply)) {
            _record.baked = true;
            _record.effect = _reply.effect;
            _record.mood = _reply.mood;
            _record.delta = pp_talk_effect_delta(_reply.effect, _battle);
            _record.lines = pp_talk_narration(_reply.text);
            _record.hint = _reply.hint;
        } else {
            // Rung 2 and 3 (spec 19 section 8): the card's own pool answers, and the authored context option keeps its
            // spec 16 section 2 row of +20, which is what makes three options reach the threshold with no model at all.
            _record.delta = pp_talk_effect_delta("soften", _battle);
            _record.effect = "none";
            _record.lines = pp_talk_pool_line(_battle, "neutral", _lines[i]);
            if (array_length(_record.lines) == 0) _record.lines = [pp_talk_cut(string(_lines[i]), 28)];
        }
        array_push(_out, _record);
    }
    return _out;
}

// ---------------------------------------------------------------------------------------------------------------
// The turn: apply the effect, then play the reply

/// Applies one option's row to the meter and returns the change that actually landed.
/// Spec 19 section 6 rule 1 and 5: exactly one effect a turn, exactly one mercy change, clamped to the row's own
/// number and then to 0..100, so a row can never move the meter by more than it says (layer C, the state lock).
function pp_talk_apply(_battle, _record) {
    var _before = _battle.talk_mercy;
    var _delta = clamp(_record.delta, -20, 20);
    _battle.talk_mercy = clamp(_before + _delta, 0, 100);
    _battle.talk_effect = _record.effect;
    _battle.talk_mood = _record.mood;
    _battle.talk_delta = _battle.talk_mercy - _before;
    return _battle.talk_delta;
}

/// Open the option panel for this turn. The battle stays in the menu phase: the panel is the menu's own second shape,
/// not a new phase, so nothing else in the turn loop moves.
function pp_talk_begin(_battle) {
    if (!variable_struct_exists(_battle, "talk_mercy")) _battle.talk_mercy = 0;
    _battle.talk_options = pp_talk_options(_battle);
    _battle.talk_cursor = 0;
    _battle.talk_stage = (array_length(_battle.talk_options) > 0) ? "options" : "";
    _battle.talk_hint = "";
    _battle.talk_reply = false;
    // Card t_27aa179e: the panel says it is open, with how many options it drew and the meter it opened on. A press
    // sent at the option list is a press the game can be held to, and a run that never opened the list cannot show
    // this line at all.
    show_debug_message("PP: talk open, " + string(array_length(_battle.talk_options)) + " options, mercy "
        + string(_battle.talk_mercy) + ", trust " + string(_battle.trust));
    return _battle;
}

/// One step of the panel. A pick applies its row and hands the reply to the board, with the same after message every
/// other action uses, so the enemy's turn follows the words exactly as it follows a FIGHT.
function pp_talk_step(_battle) {
    if (_battle.talk_stage != "options") return;

    var _count = array_length(_battle.talk_options);
    if (_count == 0) {
        _battle.talk_stage = "";
        return;
    }

    var _dir = pp_menu_axis("up", "down");
    if (_dir != 0) {
        _battle.talk_cursor = ((_battle.talk_cursor + _dir) mod _count + _count) mod _count;
        pp_audio_play("menu_move");
    }
    if (!pp_pressed("confirm")) return;

    var _record = _battle.talk_options[_battle.talk_cursor];
    pp_talk_apply(_battle, _record);
    // Card t_27aa179e: the pick names the option, the effect and the meter it moved to. This is the line a capture
    // reads to prove the mercy the three talks earned, instead of inferring it from the spare happening at all.
    show_debug_message("PP: talk pick, option " + string(_battle.talk_cursor) + ", effect " + string(_record.effect)
        + ", mercy " + string(_battle.talk_mercy) + ", trust " + string(_battle.trust));
    _battle.talk_stage = "";
    _battle.talk_hint = _record.hint;
    _battle.talk_reply = true;
    _battle.talk_last_effect = _record.effect;
    pp_audio_play("menu_select");
    pp_battle_say(_battle, _record.lines, "enemy_turn");
}

// ---------------------------------------------------------------------------------------------------------------
// The reply block: four lines of 28 at an 8 pixel pitch, and the hint under them (spec 19 section 5, Q2 and Q9)
//
// These five numbers are geometry inside the battle's own window, which is 48 pixels tall (pp_battle_text_box_y2).
// 8 + 4 * 8 = 40 for the fourth line, and the hint on the next 8 pixel row lands exactly on 48, the window's last
// pixel row: nothing grows and no layout, capture region or arena origin moves.

function pp_talk_line_pitch() { return 8; }
function pp_talk_lines_max() { return 4; }
function pp_talk_text_x() { return 16; }
function pp_talk_text_y() { return 8; }
function pp_talk_hint_y() { return 40; }
#macro PP_TALK_PROMPT "WHAT DO YOU SAY?"

/// Draw a talk board: the model's own line breaks, one line per row at the 8 pixel pitch, all four inside the window.
/// No wrap and no hyphenation, because a line over 28 was cut at the load and a fifth line was dropped there.
/// Card BATTLE-FONT-WIRE: the line is the sheet's glyphs at the sheet's own 8 px pitch, which is the number this
/// function already promised; there is no colour argument because the sheet has one ink.
function pp_talk_board_draw(_board, _x, _y) {
    if (is_undefined(_board)) return 0;
    var _shown = 0;
    var _units = _board.reveal.units;
    var _unit = _board.reveal.unit;
    for (var i = 0; i <= _unit && i < array_length(_units); i++) {
        var _text = pp_text_visible(_units[i], array_length(_units[i]));
        if (i == _unit) _text = pp_text_visible(_units[i], _board.reveal.revealed);
        if (_text != "" && _shown < pp_talk_lines_max()) {
            pp_font_draw(_text, _x, _y + _shown * pp_talk_line_pitch(), 1);
            _shown += 1;
        }
    }
    return _shown;
}

/// The hint, on the row under the last reply line and inside the same window (Q9).
/// Card BATTLE-FONT-WIRE: it used to be drawn in the second role colour, and the sheet cannot be tinted (rule 6), so
/// what marks it out now is where it is: its own row under the block, at pp_talk_hint_y. The words are the sheet's.
function pp_talk_hint_draw(_hint) {
    if (!is_string(_hint) || _hint == "") return false;
    pp_font_draw(_hint, pp_talk_text_x(), pp_talk_hint_y(), 1);
    return true;
}

/// The prompt window and the three option labels, drawn in the command band while a talk is open.
function pp_talk_draw_options(_battle) {
    // The prompt sits in the message window, so the player sees that a talk is open before the list.
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(pp_battle_text_box_x1(), pp_battle_text_box_y1(),
                   pp_battle_text_box_x2() - 1, pp_battle_text_box_y2() - 1, false);
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(pp_battle_text_box_x1(), pp_battle_text_box_y1(),
                   pp_battle_text_box_x2() - 1, pp_battle_text_box_y2() - 1, true);
    // Card BATTLE-FONT-WIRE: the prompt and the three labels are the sheet's glyphs. The labels are 26 characters at
    // the longest (a dialogue line's 28 less the `* ` marker), which is x 24 to x 232 inside the band at x 248.
    pp_font_draw("* " + PP_TALK_PROMPT, pp_talk_text_x(), pp_talk_text_y() + pp_talk_line_pitch(), 1);

    // The three options, in the band, at the 16 pixel pitch the command menu already uses.
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(8, PP_MENU_TOP, PP_FRAME_W - 8, PP_FRAME_H - 8, false);
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(8, PP_MENU_TOP, PP_FRAME_W - 8, PP_FRAME_H - 8, true);

    var _count = array_length(_battle.talk_options);
    for (var i = 0; i < _count; i++) {
        var _y = PP_MENU_TOP + 10 + i * 16;
        pp_font_draw(_battle.talk_options[i].label, 24, _y, 1);
        if (i == _battle.talk_cursor) {
            draw_set_colour(pp_role_colour("text"));
            draw_triangle(14, _y, 14, _y + 8, 20, _y + 4, false);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The two NPC voices (Q5 and Q10): Morgan at the gate, Nye at the dock office, both read from the bake and both
// opened as a dialogue box, because the box is spec 05's and this module does not own a second one.

/// True when the bake carries any turn for this npc id.
function pp_talk_npc_baked(_npc_id) {
    var _bake_npc = pp_talk_bake_npc();
    return variable_struct_exists(_bake_npc, string(_npc_id));
}

/// The baked turns of one npc, in order, with no gaps. Undefined entries are dropped so a missing turn 2 does not
/// shift turn 3 into its place.
function pp_talk_npc_rows(_npc_id) {
    var _out = [];
    var _bake_npc = pp_talk_bake_npc();
    var _id = string(_npc_id);
    if (!variable_struct_exists(_bake_npc, _id)) return _out;
    var _turns = _bake_npc[$ _id];
    for (var i = 0; i < array_length(_turns); i++) {
        if (is_undefined(_turns[i])) continue;
        array_push(_out, _turns[i]);
    }
    return _out;
}

/// Open the baked conversation for one npc as a box in the shape pp_dialogue draws, so pp_overworld_step's existing
/// dialogue branch drives it with no second stepper and no second box. One page per baked turn, one hint per page.
/// Returns undefined when this npc has no baked row, which is how the actor's own authored dialogue keeps the floor.
function pp_talk_npc_open(_npc_id, _name) {
    var _rows = pp_talk_npc_rows(_npc_id);
    if (array_length(_rows) == 0) return undefined;

    var _pages = [];
    var _units = [];
    var _hints = [];
    var _speaker = string_lower(string(_name));
    for (var i = 0; i < array_length(_rows); i++) {
        var _lines = pp_talk_narration(_rows[i].text);
        var _rowset = [];
        for (var j = 0; j < array_length(_lines); j++) {
            var _wrapped = pp_dialogue_rows(_lines[j]);
            for (var w = 0; w < array_length(_wrapped); w++) array_push(_rowset, _wrapped[w]);
        }
        array_push(_pages, { speaker: _speaker, rows: _rowset });
        array_push(_units, pp_dialogue_page_unit(_rowset));
        array_push(_hints, _rows[i].hint);
    }

    return {
        id: "meta_bake:npc/" + string(_npc_id),
        speaker: _speaker,
        pages: _pages,
        sets: [],
        choices: [],
        cursor: 0,
        reveal: pp_text_reveal_begin(_units, _speaker, false),
        closed: false,
        hints: _hints,
        baked: true
    };
}

/// The hint of the page a baked box is on, or "" for a box that carries none.
function pp_talk_npc_hint(_d) {
    if (is_undefined(_d) || !is_struct(_d)) return "";
    if (!variable_struct_exists(_d, "hints") || !is_array(_d.hints)) return "";
    var _page = _d.reveal.unit;
    if (_page < 0 || _page >= array_length(_d.hints)) return "";
    return _d.hints[_page];
}

/// The open talk target for one actor: the bake when it has a row for this npc, the actor's own dialogue otherwise.
/// The caller passes the actor and the map id, so the same npc can read differently in two rooms once the bake grows
/// a place key; today the bake carries one voice per npc and the place is an audit field on the row.
function pp_talk_actor_open(_actor, _world) {
    var _id = "";
    if (is_struct(_actor) && variable_struct_exists(_actor, "name")) _id = string(_actor.name);
    if (_id != "") {
        var _baked = pp_talk_npc_open(_id, _id);
        if (!is_undefined(_baked)) return _baked;
    }
    if (is_struct(_actor) && variable_struct_exists(_actor, "dialogue") && string(_actor.dialogue) != "") {
        return pp_dialogue_open(_actor.dialogue);
    }
    return undefined;
}
