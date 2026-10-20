/// pp_battle_director: one turn based fight as an explicit state machine (spec 07).
/// All numbers come from data\ or pp_config. The director never spawns hazards itself: it hands the pattern to
/// pp_dodge_arena and waits (spec 07 rule 7).
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop".

/// Build a fight. party is one character entry from data\characters\party.json, enemy and encounter are data entries.
function pp_battle_new(_encounter, _enemy, _party, _ledger) {
    var _hp = _party.max_hp;
    if (variable_struct_exists(_ledger, "hp")) _hp = _ledger.hp;

    var _battle = {
        encounter: _encounter,
        enemy: _enemy,
        actor: {
            id: _party.id,
            name: _party.name,
            hp: _hp,
            max_hp: _party.max_hp,
            power_multiplier: _party.power_multiplier,
            will: _party.will_max,
            will_max: _party.will_max,
            powers: pp_battle_saved_powers(_ledger),
            items: pp_battle_start_items(_party, _ledger)
        },
        ledger: _ledger,
        phase: PPBattlePhase.intro,
        phase_steps: 0,
        turn: 0,
        cursor: PPCommand.fight,
        cursor_note: "",
        cursor_note_steps: 0,
        action: PPCommand.fight,
        bar_pos: 0,
        bar_dir: 1,
        bar_steps: 0,
        power: 0,
        messages: undefined,
        after_message: "",
        trust: 0,
        enemy_hp: _enemy.max_hp,
        arena: undefined,
        attack_value: 0,
        popup_value: 0,
        popup_steps: 0,
        result: PPResult.none,
        recorded: false,
        defeated: false,
        rng: pp_rng_new(_encounter.seed)
    };

    pp_battle_phase_set(_battle, PPBattlePhase.intro);
    return _battle;
}

/// Powers carry over from the ledger once they are earned.
function pp_battle_saved_powers(_ledger) {
    if (variable_struct_exists(_ledger, "powers")) return _ledger.powers;
    return [];
}

/// Starting items come from party data, expanded to one record per copy so using one is one array delete.
function pp_battle_start_items(_party, _ledger) {
    var _out = [];
    if (variable_struct_exists(_ledger, "items") && array_length(_ledger.items) > 0) return _ledger.items;
    if (!variable_struct_exists(_party, "starting_items")) return _out;

    var _start = _party.starting_items;
    for (var i = 0; i < array_length(_start); i++) {
        var _ref = _start[i];
        var _item = pp_data_find(global.pp_data.items.items, _ref.id);
        if (is_undefined(_item)) continue;
        for (var n = 0; n < _ref.count; n++) {
            array_push(_out, { id: _item.id, name: _item.name, heal: _item.heal });
        }
    }
    return _out;
}

/// Every phase change goes through here, which is what makes the debug print and the step counter trustworthy.
function pp_battle_phase_set(_battle, _phase) {
    _battle.phase = _phase;
    _battle.phase_steps = 0;
    if (PP_DEBUG) {
        show_debug_message("battle phase " + string(_phase) + " turn " + string(_battle.turn));
    }
    return _battle;
}

/// One step of the fight. Called from obj_pp_game's Step event through pp_app.
function pp_battle_step(_battle) {
    _battle.phase_steps += 1;
    if (_battle.popup_steps > 0) _battle.popup_steps -= 1;
    if (_battle.cursor_note_steps > 0) _battle.cursor_note_steps -= 1;

    switch (_battle.phase) {
        case PPBattlePhase.intro: pp_battle_step_intro(_battle); break;
        case PPBattlePhase.menu: pp_battle_step_menu(_battle); break;
        case PPBattlePhase.resolve: pp_battle_step_resolve(_battle); break;
        case PPBattlePhase.message: pp_battle_step_message(_battle); break;
        case PPBattlePhase.telegraph: pp_battle_step_telegraph(_battle); break;
        case PPBattlePhase.dodge: pp_battle_step_dodge(_battle); break;
        case PPBattlePhase.result: pp_battle_step_result(_battle); break;
        case PPBattlePhase.ended: break;
    }
    return _battle;
}

function pp_battle_step_intro(_battle) {
    if (_battle.phase_steps == PP_INTRO_FLASH_STEPS + PP_FRAME_SLIDE_STEPS) {
        var _intro = pp_battle_dialogue(_battle.encounter.intro_dialogue);
        if (is_array(_intro)) pp_battle_say(_battle, _intro, "menu");
        else pp_battle_phase_set(_battle, PPBattlePhase.menu);
    }
}

function pp_battle_step_menu(_battle) {
    var _dir = pp_menu_axis("up", "down");
    if (_dir != 0) pp_command_move(_battle, _dir);

    if (pp_pressed("confirm")) {
        var _entry = pp_command_current(_battle);
        var _state = pp_command_state(_battle, _entry.id);
        if (!_state.enabled) {
            // Spec 07 rule 1: a refused entry is visible and audible and never advances the turn.
            _battle.cursor_note = _state.reason;
            _battle.cursor_note_steps = 30;
            return;
        }
        _battle.action = _entry.id;
        _battle.turn += 1;
        pp_battle_begin_action(_battle);
    }
}

/// Start the chosen command. FIGHT opens the timing bar, the rest resolve at once.
function pp_battle_begin_action(_battle) {
    switch (_battle.action) {
        case PPCommand.fight:
            _battle.bar_pos = 0;
            _battle.bar_dir = 1;
            _battle.bar_steps = 0;
            pp_battle_phase_set(_battle, PPBattlePhase.resolve);
            break;

        case PPCommand.power:
            var _power = _battle.actor.powers[0];
            if (is_undefined(_power)) break;
            _battle.actor.will = max(0, _battle.actor.will - _power.cost);
            pp_battle_hurt_enemy(_battle, _power.power);
            pp_battle_say(_battle, ["* " + _power.name + " lands for " + string(_power.power) + "."], "enemy_turn");
            break;

        case PPCommand.talk:
            _battle.trust += _battle.encounter.trust_per_talk;
            var _talk = pp_battle_dialogue(_battle.enemy.talk_dialogue);
            var _line = "* You speak. Trust " + string(_battle.trust) + " of " + string(_battle.enemy.trust_to_spare) + ".";
            if (is_array(_talk)) {
                var _idx = min(_battle.trust - 1, array_length(_talk) - 1);
                if (_idx >= 0) _line = _talk[_idx];
            }
            pp_battle_say(_battle, [_line], "enemy_turn");
            break;

        case PPCommand.spare:
            if (pp_battle_spare_allowed(_battle)) {
                _battle.result = PPResult.spare;
                _battle.enemy_hp = 0;
                pp_battle_enter_result(_battle);
            }
            break;

        case PPCommand.item:
            var _item = _battle.actor.items[0];
            if (!is_undefined(_item)) {
                _battle.actor.hp = min(_battle.actor.max_hp, _battle.actor.hp + _item.heal);
                array_delete(_battle.actor.items, 0, 1);
                pp_battle_say(_battle, ["* " + _item.name + " restores " + string(_item.heal) + "."], "enemy_turn");
            }
            break;
    }
    return _battle;
}

/// The timing bar: 0 to 100 then back, 100/60 per step. Confirm anywhere; power is best at the middle.
function pp_battle_step_resolve(_battle) {
    _battle.bar_steps += 1;
    _battle.bar_pos += _battle.bar_dir * (100 / PP_FIGHT_SWEEP_STEPS);
    if (_battle.bar_pos >= 100) {
        _battle.bar_pos = 100;
        _battle.bar_dir = -1;
    } else if (_battle.bar_pos <= 0) {
        _battle.bar_pos = 0;
        _battle.bar_dir = 1;
    }

    if (pp_pressed("confirm") || _battle.bar_steps >= PP_FIGHT_SWEEP_STEPS * 2) {
        _battle.power = round(100 - abs(_battle.bar_pos - 50) * 2);
        var _damage = pp_battle_fight_damage(_battle, _battle.power);
        pp_battle_hurt_enemy(_battle, _damage);
        pp_battle_say(_battle, ["* You strike for " + string(_damage) + "."], "enemy_turn");
    }
}

/// Damage from the bar (spec delta T7): 2 to 12 scaled by power, then the actor's multiplier, never below 1.
function pp_battle_fight_damage(_battle, _power) {
    var _p = clamp(_power, 0, 100);
    var _raw = PP_FIGHT_DAMAGE_MIN + (PP_FIGHT_DAMAGE_MAX - PP_FIGHT_DAMAGE_MIN) * (_p / 100);
    return max(1, round(_raw * _battle.actor.power_multiplier));
}

function pp_battle_hurt_enemy(_battle, _damage) {
    _battle.enemy_hp = max(0, _battle.enemy_hp - _damage);
    _battle.popup_value = _damage;
    _battle.popup_steps = PP_DAMAGE_POPUP_STEPS;
    if (_battle.enemy_hp <= 0 && _battle.result == PPResult.none) _battle.result = PPResult.kill;
    return _battle.enemy_hp;
}

/// Open a message board and remember what to do when it closes.
function pp_battle_say(_battle, _lines, _after) {
    _battle.messages = pp_text_board(_lines);
    _battle.after_message = _after;
    pp_battle_phase_set(_battle, PPBattlePhase.message);
    return _battle;
}

function pp_battle_step_message(_battle) {
    if (is_undefined(_battle.messages)) {
        pp_battle_after_message(_battle);
        return;
    }
    var _fast = pp_action("confirm");
    pp_text_board_step(_battle.messages, _fast);

    if (pp_pressed("confirm") && !pp_text_board_done(_battle.messages)) {
        pp_text_board_skip_line(_battle.messages);
    } else if (pp_text_board_done(_battle.messages)) {
        pp_battle_after_message(_battle);
    }
}

function pp_battle_after_message(_battle) {
    _battle.messages = undefined;
    var _after = _battle.after_message;
    _battle.after_message = "";

    // The closing board always ends the fight, so it is checked first and cannot re-enter itself.
    if (_after == "_closing") {
        pp_battle_phase_set(_battle, PPBattlePhase.result);
        return;
    }
    if (_after == "result") {
        pp_battle_enter_result(_battle);
        return;
    }
    if (_battle.defeated || _battle.result != PPResult.none) {
        pp_battle_enter_result(_battle);
        return;
    }
    if (_after == "enemy_turn") {
        _battle.attack_value = pp_battle_roll_attack(_battle);
        pp_battle_phase_set(_battle, PPBattlePhase.telegraph);
        return;
    }
    if (_after == "menu") {
        pp_battle_phase_set(_battle, PPBattlePhase.menu);
        return;
    }
    pp_battle_phase_set(_battle, PPBattlePhase.menu);
}

/// The enemy answer: telegraph, then a data pattern in the arena for as long as the recipe says.
function pp_battle_step_telegraph(_battle) {
    if (_battle.phase_steps >= PP_TELEGRAPH_STEPS) {
        var _pattern = pp_battle_pick_pattern(_battle);
        if (is_undefined(_pattern)) {
            pp_battle_phase_set(_battle, PPBattlePhase.menu);
            return;
        }
        _battle.arena = pp_arena_new(_pattern, floor(_battle.rng.state), _battle.attack_value);
        pp_battle_phase_set(_battle, PPBattlePhase.dodge);
    }
}

function pp_battle_pick_pattern(_battle) {
    var _ids = _battle.enemy.patterns;
    if (!is_array(_ids) || array_length(_ids) == 0) return undefined;
    var _id = _ids[pp_rng_int(_battle.rng, 0, array_length(_ids) - 1)];
    var _pattern = pp_data_find(global.pp_data.patterns.patterns, _id);
    if (!is_undefined(_pattern)) return _pattern;
    if (array_length(global.pp_data.patterns.patterns) > 0) return global.pp_data.patterns.patterns[0];
    return undefined;
}

function pp_battle_roll_attack(_battle) {
    var _atk = _battle.enemy.attack;
    return pp_rng_int(_battle.rng, _atk.min, _atk.max);
}

function pp_battle_step_dodge(_battle) {
    var _in = global.pp_input;
    var _ev = pp_arena_step(_battle.arena, _in.vec_x, _in.vec_y);
    if (_ev.hit) {
        _battle.actor.hp = max(0, _battle.actor.hp - _battle.arena.attack);
        _battle.popup_value = _battle.arena.attack;
        _battle.popup_steps = PP_DAMAGE_POPUP_STEPS;
    }
    if (_ev.ended) {
        _battle.arena = undefined;
        if (_battle.actor.hp <= 0) {
            _battle.defeated = true;
            pp_battle_enter_result(_battle);
            return;
        }
        pp_battle_phase_set(_battle, PPBattlePhase.menu);
    }
}

/// Build the closing board (spec delta M5) and record the outcome exactly once through the ledger's single door.
function pp_battle_enter_result(_battle) {
    if (!_battle.recorded) pp_battle_record(_battle);

    var _lines;
    if (_battle.defeated) _lines = pp_battle_dialogue_lines(_battle.encounter.lose_dialogue);
    else if (_battle.result == PPResult.spare) _lines = pp_battle_dialogue_lines(_battle.encounter.win_dialogue_spare);
    else if (_battle.result == PPResult.kill) _lines = pp_battle_dialogue_lines(_battle.encounter.win_dialogue_kill);
    else _lines = ["* The fight ends."];

    pp_battle_say(_battle, _lines, "_closing");
}

function pp_battle_record(_battle) {
    var _kind = "regular";
    if (variable_struct_exists(_battle.enemy, "route_kind")) _kind = _battle.enemy.route_kind;
    if (!_battle.defeated) pp_ledger_record_result(_battle.ledger, _kind, _battle.result);
    _battle.ledger.hp = _battle.actor.hp;
    _battle.recorded = true;
    return _battle;
}

function pp_battle_step_result(_battle) {
    if (_battle.phase_steps >= PP_RESULT_STEPS) {
        pp_battle_phase_set(_battle, PPBattlePhase.ended);
    }
}

function pp_battle_finished(_battle) {
    return _battle.phase == PPBattlePhase.ended;
}

function pp_battle_outcome(_battle) {
    if (_battle.defeated) return "defeat";
    if (_battle.result == PPResult.spare) return "spare";
    if (_battle.result == PPResult.kill) return "kill";
    return "unresolved";
}

function pp_battle_has_talk(_battle) {
    return is_string(_battle.enemy.talk_dialogue) && _battle.enemy.talk_dialogue != ""
        && !is_undefined(pp_data_find(global.pp_data.dialogue.dialogue, _battle.enemy.talk_dialogue));
}

function pp_battle_usable_item_count(_battle) {
    return array_length(_battle.actor.items);
}

/// Spec 07: spare is allowed once trust reaches the enemy's threshold, or its health is at or below its percentage.
function pp_battle_spare_allowed(_battle) {
    if (_battle.enemy_hp <= 0) return false;
    if (_battle.trust >= _battle.enemy.trust_to_spare) return true;
    return (_battle.enemy_hp <= (_battle.enemy.max_hp * _battle.enemy.spare_hp_percent / 100));
}

/// Dialogue lines by id, or undefined. The checker proves every id exists before this can miss.
function pp_battle_dialogue(_id) {
    var _d = pp_data_find(global.pp_data.dialogue.dialogue, _id);
    if (is_undefined(_d)) return undefined;
    return _d.lines;
}

function pp_battle_dialogue_lines(_id) {
    var _lines = pp_battle_dialogue(_id);
    if (is_undefined(_lines)) return ["* ..."];
    return _lines;
}

// ---------------------------------------------------------------------------------------------------------------
// Drawing. No sprites yet, so every actor is a flat rectangle in a palette role; spec 13 owns the final art.

function pp_battle_draw(_battle) {
    draw_set_alpha(1);
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    // The field: the hero on the left, the enemy on the right, both above the menu band.
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(40, 96, 72, 144, false);

    draw_set_colour(pp_role_colour("hazard"));
    draw_rectangle(176, 72, 224, 136, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_set_halign(fa_center);
    draw_text(200, 56, _battle.enemy.name);

    // Enemy health bar, 64 px wide.
    var _hp_frac = _battle.enemy_hp / max(1, _battle.enemy.max_hp);
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(168, 144, 232, 148, false);
    draw_set_colour(pp_role_colour("accent"));
    draw_rectangle(168, 144, 168 + floor(64 * _hp_frac), 148, false);

    // Player health and will.
    draw_set_colour(pp_role_colour("ink"));
    draw_set_halign(fa_left);
    draw_text(16, 156, "HP " + string(_battle.actor.hp) + "/" + string(_battle.actor.max_hp)
        + "   WILL " + string(_battle.actor.will) + "/" + string(_battle.actor.will_max));

    if (_battle.phase == PPBattlePhase.intro) {
        if (_battle.phase_steps < PP_INTRO_FLASH_STEPS && (_battle.phase_steps div 4) mod 2 == 0) {
            draw_set_alpha(0.7);
            draw_set_colour(pp_role_colour("accent"));
            draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
            draw_set_alpha(1);
        }
    }

    if (_battle.phase == PPBattlePhase.menu || _battle.phase == PPBattlePhase.resolve) {
        pp_battle_draw_menu(_battle);
    }

    if (_battle.phase == PPBattlePhase.resolve) {
        pp_battle_draw_bar(_battle);
    }

    if (_battle.phase == PPBattlePhase.dodge && !is_undefined(_battle.arena)) {
        pp_arena_draw(_battle.arena);
    }

    if (!is_undefined(_battle.messages)) {
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(8, 8, PP_FRAME_W - 8, 60, false);
        draw_set_colour(pp_role_colour("dim"));
        draw_rectangle(8, 8, PP_FRAME_W - 8, 60, true);
        pp_text_board_draw(_battle.messages, 16, 16, pp_role_colour("ink"));
    }

    if (_battle.popup_steps > 0) {
        draw_set_colour(pp_role_colour("accent"));
        draw_set_halign(fa_center);
        draw_text(200, 120 - (PP_DAMAGE_POPUP_STEPS - _battle.popup_steps), string(_battle.popup_value));
        draw_set_halign(fa_left);
    }

    if (_battle.phase == PPBattlePhase.telegraph) {
        draw_set_colour(pp_role_colour("warn"));
        draw_set_halign(fa_center);
        draw_text(PP_FRAME_W * 0.5, 96, "here it comes");
        draw_set_halign(fa_left);
    }
}

function pp_battle_draw_menu(_battle) {
    var _y = PP_MENU_TOP + 8;
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(8, PP_MENU_TOP, PP_FRAME_W - 8, PP_FRAME_H - 8, false);
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(8, PP_MENU_TOP, PP_FRAME_W - 8, PP_FRAME_H - 8, true);

    var _table = pp_command_table();
    for (var i = 0; i < array_length(_table); i++) {
        var _entry = _table[i];
        var _state = pp_command_state(_battle, _entry.id);
        var _x = 24 + (i mod 2) * 104;
        var _yy = _y + (i div 2) * 20;
        draw_set_colour(_state.enabled ? pp_role_colour("ink") : pp_role_colour("dim"));
        draw_text(_x, _yy, _entry.label);
        if (i == _battle.cursor) {
            draw_set_colour(pp_role_colour("accent"));
            draw_triangle(_x - 10, _yy, _x - 10, _yy + 8, _x - 4, _yy + 4, false);
        }
    }

    if (_battle.cursor_note_steps > 0 && _battle.cursor_note != "") {
        draw_set_colour(pp_role_colour("warn"));
        draw_text(16, PP_FRAME_H - 20, _battle.cursor_note);
    }
}

function pp_battle_draw_bar(_battle) {
    var _y = 120;
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(48, _y, 208, _y + 6, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(126, _y - 2, 130, _y + 8, false);
    draw_set_colour(pp_role_colour("accent"));
    draw_rectangle(48 + floor(1.6 * _battle.bar_pos) - 1, _y - 4, 48 + floor(1.6 * _battle.bar_pos) + 1, _y + 10, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_text(48, _y + 12, "Z");
}
