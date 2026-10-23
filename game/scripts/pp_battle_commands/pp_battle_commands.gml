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
            // Card t_905a18ce (F1): a SPARE the enemy refuses inside its interrupt gate is the story exit (spec 18
            // section 4 rule 4), so the press has to LIVE in that window. Disabling the entry on the spare gate alone
            // made every hp from the interrupt threshold down to the spare line a press that never arrived: spare is
            // accepted at 25 percent of 120 (30 hp) and the gate is 40 percent (48 hp), so 31 hp to 48 hp was dead.
            if (pp_battle_interrupt_ready(_battle)) return { enabled: true, reason: "" };

            // Card t_905a18ce (F4): the encounter row may refuse this entry on a route (`spare_refuses_on_route`,
            // spec 07 line 33 and spec 10's genocide row). The field is read HERE, where every other refusal is read,
            // so the menu draws the reason and the director never has to answer a press the data refused. The route
            // itself is derived, never stored (spec 10 rule 7, pp_battle_route_name).
            if (pp_battle_spare_route_refused(_battle)) _reason = "no mercy left on this route";
            else if (!pp_battle_spare_allowed(_battle)) _reason = "not ready to end it";
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
