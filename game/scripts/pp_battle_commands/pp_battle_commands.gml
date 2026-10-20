/// pp_battle_commands: the five entry battle menu (spec 07 table and rule 1).
/// An entry is a record with an id, a label and an enabled test that returns the reason it is refused. The menu draws
/// the reason, so a disabled entry never silently does nothing.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The table is spec 07's five entries; the
/// enable test that returns a reason string is our own shape.

/// The command list, in cursor order.
function pp_command_table() {
    return [
        { id: PPCommand.fight, key: "fight", label: "FIGHT" },
        { id: PPCommand.power, key: "power", label: "POWER" },
        { id: PPCommand.talk,  key: "talk",  label: "TALK"  },
        { id: PPCommand.spare, key: "spare", label: "SPARE" },
        { id: PPCommand.item,  key: "item",  label: "ITEM"  }
    ];
}

/// Enabled test. Returns {enabled, reason}. reason is drawn in the second ink when enabled is false.
function pp_command_state(_battle, _cmd) {
    var _reason = "";

    switch (_cmd) {
        case PPCommand.fight:
            return { enabled: true, reason: "" };

        case PPCommand.power:
            if (array_length(_battle.actor.powers) == 0) _reason = "no power taken yet";
            else if (_battle.actor.will <= 0) _reason = "no will";
            if (_reason != "") return { enabled: false, reason: _reason };
            return { enabled: true, reason: "" };

        case PPCommand.talk:
            if (!pp_battle_has_talk(_battle)) _reason = "nothing to say to this one";
            if (_reason != "") return { enabled: false, reason: _reason };
            return { enabled: true, reason: "" };

        case PPCommand.spare:
            if (!pp_battle_spare_allowed(_battle)) _reason = "not ready to end it";
            if (_reason != "") return { enabled: false, reason: _reason };
            return { enabled: true, reason: "" };

        case PPCommand.item:
            if (pp_battle_usable_item_count(_battle) <= 0) _reason = "no item";
            if (_reason != "") return { enabled: false, reason: _reason };
            return { enabled: true, reason: "" };
    }
    return { enabled: false, reason: "unknown" };
}

/// Move the cursor by one and wrap. Disabled entries are not skipped: the player must be able to see why (spec 07
/// rule 1), so only the reason is drawn, and the cursor still lands on them.
function pp_command_move(_battle, _dir) {
    var _n = array_length(pp_command_table());
    _battle.cursor = ((_battle.cursor + _dir) mod _n + _n) mod _n;
    _battle.cursor_note = "";
    return _battle.cursor;
}

/// The entry under the cursor.
function pp_command_current(_battle) {
    var _t = pp_command_table();
    return _t[_battle.cursor];
}

/// The label plus, when refused, a short plain note. Used by the director's menu drawing.
function pp_command_label(_battle, _entry) {
    var _state = pp_command_state(_battle, _entry.id);
    if (_state.enabled) return _entry.label;
    return _entry.label + "  (" + _state.reason + ")";
}
