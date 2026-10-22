/// pp_ledger: the route ledger (spec 10). Two records, one door each. The counters are cumulative and the route is
/// derived on read and never stored, because two stored copies of one fact drift and then the save lies. The exit rows
/// are the last fight exactly as it happened, one row per enemy, and the fight verdict is a function of those rows.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. Counters, flags and a route derived on
/// read are spec 10. The exit rows and the verdict are spec 10 rule 6, added by card t_48020b30 from
/// knowledge\FOX-STYLE.md section 2.

/// A fresh ledger at the start of a run. No fight has been fought, so no rows and a quiet verdict.
function pp_ledger_new() {
    return {
        counters: {
            bosses_killed: 0,
            bosses_spared: 0,
            regulars_killed: 0,
            regulars_spared: 0
        },
        flags: {},
        stage: 0,
        exits: [],
        verdict: PPFightVerdict.quiet
    };
}

// ---------------------------------------------------------------------------------------------------------------
// The per-fight record (spec 10 rule 6)

/// Start a fight with a clean record. The counters above are the run's history and stay; only the last fight's rows
/// and its verdict are cleared, so the F3 view shows the fight the player just walked out of.
function pp_ledger_begin_fight(_ledger) {
    _ledger.exits = [];
    _ledger.verdict = PPFightVerdict.quiet;
    return _ledger;
}

/// One result enum as one of the three exit states, or -1 for a result that leaves no row (none, or a defeat, which is
/// the party leaving the field rather than the enemy). The three names are the doctrine's, and this is the only place
/// the two vocabularies meet.
function pp_ledger_exit_of_result(_result) {
    switch (_result) {
        case PPResult.kill: return PPExit.down;
        case PPResult.spare: return PPExit.spared;
        case PPResult.interrupt: return PPExit.turned;
    }
    return -1;
}

/// The only door that records an enemy leaving a fight (spec 10 rule 1). It writes the row, then recomputes the
/// verdict from the rows, then increments the counter, in that order and in this one call, so a caller cannot write a
/// row without the counter or a counter without the row. Nothing else in the tree touches a counter.
///
/// kind is "boss" or "regular" and decides which counter moves. A turned enemy is neither a kill nor a spare, so it
/// moves no counter and still gets its row: the record stays exact where the counters are deliberately coarse.
function pp_ledger_record_exit(_ledger, _enemy_id, _kind, _result, _round) {
    var _exit = pp_ledger_exit_of_result(_result);
    if (_exit < 0) return _ledger;

    array_push(_ledger.exits, { id: _enemy_id, exit: _exit, round: _round });
    _ledger.verdict = pp_ledger_verdict_of(_ledger.exits);

    if (_exit == PPExit.down) {
        if (_kind == "boss") _ledger.counters.bosses_killed += 1;
        else _ledger.counters.regulars_killed += 1;
    } else if (_exit == PPExit.spared) {
        if (_kind == "boss") _ledger.counters.bosses_spared += 1;
        else _ledger.counters.regulars_spared += 1;
    }
    return _ledger;
}

/// The verdict a set of rows earns. Generous on purpose and in this order: any enemy who left without being put down
/// lifts the fight out of violent, and a fight with no down at all reads quiet. The rows underneath stay exact, so the
/// soft word never hides what happened.
function pp_ledger_verdict_of(_rows) {
    var _down = 0;
    var _soft = 0;
    for (var i = 0; i < array_length(_rows); i++) {
        if (_rows[i].exit == PPExit.down) _down += 1;
        else _soft += 1;
    }
    if (_down == 0) return PPFightVerdict.quiet;
    if (_soft > 0) return PPFightVerdict.mixed;
    return PPFightVerdict.violent;
}

/// How many rows ended one way. The debug view and the tests read the record through this rather than by walking it.
function pp_ledger_exit_count(_ledger, _exit) {
    var _n = 0;
    for (var i = 0; i < array_length(_ledger.exits); i++) {
        if (_ledger.exits[i].exit == _exit) _n += 1;
    }
    return _n;
}

function pp_ledger_exit_name(_exit) {
    switch (_exit) {
        case PPExit.down: return "down";
        case PPExit.spared: return "spared";
        case PPExit.turned: return "turned";
    }
    return "unknown";
}

function pp_ledger_verdict_name(_verdict) {
    switch (_verdict) {
        case PPFightVerdict.quiet: return "quiet";
        case PPFightVerdict.mixed: return "mixed";
        case PPFightVerdict.violent: return "violent";
    }
    return "quiet";
}

// ---------------------------------------------------------------------------------------------------------------
// The run's counters and flags (spec 10 rules 1 to 4)

/// Total kills, which is what the route and the NPC line variants read.
function pp_ledger_kills(_ledger) {
    return _ledger.counters.bosses_killed + _ledger.counters.regulars_killed;
}

function pp_ledger_spares(_ledger) {
    return _ledger.counters.bosses_spared + _ledger.counters.regulars_spared;
}

/// Flags are named booleans from data. An unknown name is created on first set, so a checker is what catches typos.
function pp_ledger_flag(_ledger, _name) {
    if (variable_struct_exists(_ledger.flags, _name)) return _ledger.flags[$ _name];
    return false;
}

function pp_ledger_set_flag(_ledger, _name, _value) {
    _ledger.flags[$ _name] = _value;
    return _ledger;
}

/// Derived route (spec 10 table, delta T12): counters first, then the story stage for the undecided case.
/// prison_stage comes from data\project.json, so the story can move the boundary without touching code.
function pp_ledger_route(_ledger, _prison_stage) {
    if (_ledger.counters.bosses_killed > 0) return PPRoute.genocide;
    if (_ledger.counters.regulars_killed > 0) return PPRoute.blooded;
    if (_ledger.stage >= _prison_stage) return PPRoute.mercy;
    return PPRoute.undecided;
}

function pp_ledger_route_name(_route) {
    switch (_route) {
        case PPRoute.mercy: return "mercy";
        case PPRoute.blooded: return "blooded";
        case PPRoute.genocide: return "genocide";
    }
    return "undecided";
}

/// Advance the story stage. Only ever forward, so a scene replay cannot rewind the route.
function pp_ledger_advance_stage(_ledger, _stage) {
    if (_stage > _ledger.stage) _ledger.stage = _stage;
    return _ledger;
}

/// Plain multi line dump for the F3 debug view (spec 10 rule 5). The last fight's rows are one line each, so a tester
/// can see that the counters and the record agree without reading the save file.
function pp_ledger_debug_text(_ledger, _prison_stage) {
    var _t = "kills " + string(pp_ledger_kills(_ledger)) + "  spares " + string(pp_ledger_spares(_ledger))
        + "  stage " + string(_ledger.stage) + "\n"
        + "route " + pp_ledger_route_name(pp_ledger_route(_ledger, _prison_stage))
        + "  fight " + pp_ledger_verdict_name(_ledger.verdict);
    for (var i = 0; i < array_length(_ledger.exits); i++) {
        var _row = _ledger.exits[i];
        _t += "\n" + string(i + 1) + " " + string(_row.id) + " " + pp_ledger_exit_name(_row.exit)
            + " r" + string(_row.round);
    }
    var _flags = pp_ledger_flag_text(_ledger);
    if (_flags != "") _t += "\n" + _flags;
    return _t;
}

/// The set flags on one line, or "" when none is set. Shared with the line count below so the F3 box cannot disagree
/// with the text it draws.
function pp_ledger_flag_text(_ledger) {
    var _names = variable_struct_get_names(_ledger.flags);
    var _t = "";
    for (var i = 0; i < array_length(_names); i++) {
        if (_ledger.flags[$ _names[i]]) _t += "  " + _names[i];
    }
    if (_t == "") return "";
    return "flags" + _t;
}

/// How many lines pp_ledger_debug_text will draw, so the F3 box can size itself and never clip a row.
function pp_ledger_debug_lines(_ledger) {
    var _n = 2 + array_length(_ledger.exits);
    if (pp_ledger_flag_text(_ledger) != "") _n += 1;
    return _n;
}
