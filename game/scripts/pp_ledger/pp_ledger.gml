/// pp_ledger: the route ledger (spec 10). Counters and flags are the only record; the route is derived on read and
/// never stored, because two stored copies of one fact drift and then the save lies.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. Counters, flags and a route derived on
/// read are spec 10.

/// A fresh ledger at the start of a run.
function pp_ledger_new() {
    return {
        counters: {
            bosses_killed: 0,
            bosses_spared: 0,
            regulars_killed: 0,
            regulars_spared: 0
        },
        flags: {},
        stage: 0
    };
}

/// The single door for a battle outcome (spec 10 rule 1). kind is "boss" or "regular".
function pp_ledger_record_result(_ledger, _kind, _result) {
    if (_result == PPResult.kill) {
        if (_kind == "boss") _ledger.counters.bosses_killed += 1;
        else _ledger.counters.regulars_killed += 1;
    } else if (_result == PPResult.spare) {
        if (_kind == "boss") _ledger.counters.bosses_spared += 1;
        else _ledger.counters.regulars_spared += 1;
    }
    return _ledger;
}

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

/// Plain multi line dump for the F3 debug view (spec 10 rule 5).
function pp_ledger_debug_text(_ledger, _prison_stage) {
    var _t = "kills " + string(pp_ledger_kills(_ledger)) + "  spares " + string(pp_ledger_spares(_ledger))
        + "  stage " + string(_ledger.stage) + "\n"
        + "route " + pp_ledger_route_name(pp_ledger_route(_ledger, _prison_stage));
    var _names = variable_struct_get_names(_ledger.flags);
    for (var i = 0; i < array_length(_names); i++) {
        if (_ledger.flags[$ _names[i]]) _t += "  " + _names[i];
    }
    return _t;
}
