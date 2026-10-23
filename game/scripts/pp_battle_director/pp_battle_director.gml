/// pp_battle_director: one turn based fight as an explicit state machine (spec 07).
/// All numbers come from data\ or pp_config. The director never spawns hazards itself: it hands the pattern to
/// pp_dodge_arena and waits (spec 07 rule 7).
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop".

/// Build a fight. party is one character entry from data\characters\party.json, enemy and encounter are data entries.
function pp_battle_new(_encounter, _enemy, _party, _ledger) {
    var _hp = _party.max_hp;
    if (variable_struct_exists(_ledger, "hp")) _hp = _ledger.hp;

    // A new fight starts with a clean exit record (spec 10 rule 6). The run's counters above it are untouched.
    pp_ledger_begin_fight(_ledger);

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
        // Card R27 (spec 07 acceptance 4, spec 11 rule 5): the game over. A defeat never becomes PPBattlePhase.ended
        // by itself. The result phase holds the fade to black, then the game over frame, then the two ways out.
        // gameover_choice is "" while the screen waits, "wait" while the save read is in flight, "continue" once the
        // save has been put back, and "title" once the room move has been asked for. A choice that is already made
        // is never taken again, which is what keeps the screen still during the app's own fade.
        gameover_cursor: 0,
        gameover_choice: "",
        gameover_note: "",
        gameover_note_steps: 0,
        gameover_pixel_rows: 0,
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
    // One call, one door (spec 10 rule 1): the ledger writes the enemy's exit row, settles the fight verdict and
    // moves the counter itself. Nothing here reads or writes a counter, so the row and the counter cannot disagree.
    if (!_battle.defeated) {
        pp_ledger_record_exit(_battle.ledger, _battle.enemy.id, _kind, _battle.result, _battle.turn);
    }

    // A defeat is an explicit decision, not a side effect (knowledge\SPEC-DELTAS.md, C7). Card R27 replaces the
    // stand in that used to send the party back to the map at full health: a lost fight now hands the screen to the
    // game over, and the only honest health a run has after a defeat is the one in the save, put back by
    // pp_battle_continue. So the fight's own actor is still put back to full, because nothing downstream of a fight
    // may read a 0 that no one restores, but the run's ledger is left alone on a defeat instead of being written
    // with either the 0 the fight ended on or a full bar the player did not earn.
    if (_battle.defeated) {
        _battle.actor.hp = _battle.actor.max_hp;
    }
    if (!_battle.defeated) {
        _battle.ledger.hp = _battle.actor.hp;
    }
    _battle.recorded = true;
    return _battle;
}

// ---------------------------------------------------------------------------------------------------------------
// The game over screen (spec 07 acceptance 4, spec 11 rule 5, spec 13 look)
//
// A defeat runs here instead of the 30 step result beat: a 12 step fade over the last fight frame, then a static
// frame with CONTINUE and RETURN TO TITLE. Nothing about the fight is written to the run, so the screen has one
// source of truth for what to restore and it is the save on disk, never a copy kept in memory (spec 11 rule 5).

/// How many steps the frame spends fading out before the game over screen appears. It is the app's own fade number
/// (spec 01, PP_FADE_STEPS 12) so a player never learns two different fade speeds.
function pp_battle_gameover_fade_steps() {
    return PP_FADE_STEPS;
}

/// True once the fade is done and the frame, not the fight, owns the screen. Input is refused before this, so a
/// player holding the confirm key cannot skip the fade or pick a row they never saw.
function pp_battle_gameover_clear(_battle) {
    return _battle.phase_steps > pp_battle_gameover_fade_steps();
}

/// The two rows, in cursor order. CONTINUE is refused, visibly and audibly, when the slot holds nothing to load
/// (spec 07 rule 1: a disabled entry is drawn in the second ink, makes a low blip and never advances).
function pp_battle_gameover_rows() {
    return ["CONTINUE", "RETURN TO TITLE"];
}

/// Is CONTINUE usable right now. The slot is the only answer: a run that never wrote a save has no earlier state for
/// the player to return to, and the row says so instead of loading something else.
function pp_battle_gameover_can_continue() {
    if (pp_save_ready()) return true;
    if (pp_save_busy()) return false;
    if (!is_struct(global.pp.save)) return false;
    // A slot that has been read and refused, and a slot that is not there, both mean no. A slot nobody has asked
    // about yet is asked here, once, which is the read pp_battle_continue starts on the player's own press.
    return (global.pp.save.state != PPSaveState.absent && global.pp.save.state != PPSaveState.failed);
}

function pp_battle_step_gameover(_battle) {
    if (_battle.gameover_note_steps > 0) _battle.gameover_note_steps -= 1;

    // A read that is in flight settles here. The screen keeps drawing the frame while it lands, so the pause is a
    // "Loading" panel over the game over screen and never a black window (spec 11 numbers).
    if (_battle.gameover_choice == "wait") {
        if (pp_save_busy()) return;
        if (pp_save_ready()) {
            pp_battle_continue(_battle);
            return;
        }
        // The file was not there or did not validate. The row goes back to refused and says why, in words, instead
        // of a screen that looks like the key did nothing.
        _battle.gameover_choice = "";
        if (global.pp.save.state == PPSaveState.absent) _battle.gameover_note = "there is no save to continue";
        else _battle.gameover_note = "the save could not be read";
        _battle.gameover_note_steps = 90;
        pp_audio_play("menu_cancel");
        return;
    }
    if (_battle.gameover_choice != "") return;
    if (!pp_battle_gameover_clear(_battle)) return;

    var _rows = pp_battle_gameover_rows();
    var _dir = pp_menu_axis("up", "down");
    if (_dir != 0) {
        _battle.gameover_cursor = (_battle.gameover_cursor + _dir + array_length(_rows)) mod array_length(_rows);
        pp_audio_play("menu_move");
        _battle.gameover_note = "";
        _battle.gameover_note_steps = 0;
    }

    if (!pp_pressed("confirm")) return;

    if (_battle.gameover_cursor == 0) {
        // CONTINUE: the slot is read again before it is applied, because the save this run read at the title was
        // consumed when the run started. A save that is already in memory is applied at once.
        if (pp_save_ready()) {
            pp_battle_continue(_battle);
            return;
        }
        if (pp_save_busy()) {
            _battle.gameover_choice = "wait";
            return;
        }
        if (!pp_battle_gameover_can_continue()) {
            _battle.gameover_note = "there is no save to continue";
            _battle.gameover_note_steps = 90;
            pp_audio_play("menu_cancel");
            return;
        }
        pp_audio_play("menu_select");
        _battle.gameover_choice = "wait";
        // The purpose is a label only: it is what the save module prints beside the read, so a run log says which
        // screen asked for the slot.
        pp_save_read("game over continue");
        return;
    }

    // RETURN TO TITLE: the title owns its own room (card W1), so the move is asked for through the one room door and
    // the room's own object enters the screen. Every pixel behind this is already black, so the change is invisible.
    pp_audio_play("menu_select");
    _battle.gameover_choice = "title";
    global.pp.battle = undefined;
    pp_app_enter_room(PPMode.title, {}, rm_pp_title);
}

/// Put the last save back and hand control to the overworld. pp_save_apply is the only door that restores a run
/// (spec 11 rule 5), so the map, the tile, the health, the flag block, the counters, the items, the powers and the
/// music all come back through it and this card adds no second restorer.
function pp_battle_continue(_battle) {
    _battle.gameover_choice = "continue";
    if (!pp_save_apply()) {
        _battle.gameover_choice = "";
        _battle.gameover_note = "the save could not be put back";
        _battle.gameover_note_steps = 90;
        show_debug_message("PP: game over, CONTINUE failed, nothing was restored");
        return;
    }
    show_debug_message("PP: game over, CONTINUE restored the last save");
    return;
}


function pp_battle_step_result(_battle) {
    // Card R27: a defeat holds the result phase for the game over screen, so it never reaches PPBattlePhase.ended on
    // its own, and pp_battle_finished keeps the old "press Z, go back to the map" door shut for a lost fight. A win
    // and a spare keep the 30 step beat that already returned control to the caller.
    if (_battle.defeated) {
        pp_battle_step_gameover(_battle);
        return;
    }
    if (_battle.phase_steps >= PP_RESULT_STEPS) {
        pp_battle_phase_set(_battle, PPBattlePhase.ended);
    }
}

function pp_battle_finished(_battle) {
    return _battle.phase == PPBattlePhase.ended;
}

/// True from the moment the player's health reaches 0, for as long as the game over screen owns the frame (card R27).
/// It is deliberately not pp_battle_finished: a lost fight hands the screen to the game over card instead of setting
/// the 30 step result beat to ended, because that beat is the door back to the map and a defeat has no road back to
/// the map that is not CONTINUE or RETURN TO TITLE. Anything that needs to know a fight was lost, without taking the
/// door, asks this one. Two callers today: the card, and the demo walk's lose edge, which still reads
/// pp_battle_finished and so no longer sees a defeat (recorded as an ordering dependency on the R24 lane).
function pp_battle_lost(_battle) {
    return _battle.defeated;
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

    // Card R27: a lost fight fades out here and the game over frame takes the screen.
    if (_battle.defeated && _battle.phase == PPBattlePhase.result) {
        pp_battle_draw_gameover(_battle);
    }
}

/// The game over screen (spec 07 acceptance 4, spec 13 look). Two parts and both are whole pixels: the 12 step fade
/// over the last fight frame, then a static card.
///
/// RULE 0 first (knowledge\ART-BIBLE.md line 283): the frame invents no colour and no role. It spends four roles,
/// ink, paper, dim and text, which are the only four every palette set in data\room_palettes.json carries (the deck,
/// the cabin, the lower deck and the ui set all name them, while hazard and warn are in some and not others), so the
/// screen reads the same in every room and no role can fall through to PP_COLOUR_MISSING. Four of the 16 colours
/// spec 13 allows, and none of them blended: the fade is one rectangle over the whole frame whose alpha steps in
/// twelfths, and a blended pixel there is the app's own fade, not part of the card.
///
/// The card carries no asterisk, because the 8x8 sheet has no glyph for one and a missing glyph is a box on screen.
function pp_battle_draw_gameover(_battle) {
    var _fade = pp_battle_gameover_fade_steps();

    // The fade out. Nothing else is drawn over it, so the last fight frame is what the player sees go dark.
    if (_battle.phase_steps <= _fade) {
        draw_set_alpha(_battle.phase_steps / _fade);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
        return;
    }

    if (_battle.gameover_pixel_rows == 0) {
        _battle.gameover_pixel_rows = 1;
        show_debug_message("PP: game over frame, " + string(_fade) + " step fade, 4 roles (ink, paper, dim, text)");
    }

    // Black card, then the 1 pixel outer line of spec 05 and the 2 pixel frame it sits inside (spec 13 font and UI).
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(63, 63, 193, 177, false);
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(64, 64, 192, 176, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(66, 66, 190, 174, false);

    draw_set_halign(fa_center);
    draw_set_colour(pp_role_colour("paper"));
    draw_text(PP_FRAME_W * 0.5, 78, "GAME OVER");

    // The rule under the title: 2 pixels, dim, no gradient and no shadow (spec 13 line and shape).
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(96, 94, 160, 96, false);

    // The enemy is named on the card, because this screen is the only place the run says what took the player down.
    // No asterisk: the 8x8 sheet carries no glyph for one, and this is a card and not a dialogue line (spec 05).
    draw_set_colour(pp_role_colour("text"));
    draw_text_ext(PP_FRAME_W * 0.5, 102, string(_battle.enemy.name) + " stands over you.", 10, PP_FRAME_W - 146);

    var _rows = pp_battle_gameover_rows();
    var _can_continue = pp_battle_gameover_can_continue();
    for (var i = 0; i < array_length(_rows); i++) {
        var _label = _rows[i];
        var _enabled = (i != 0) || _can_continue;
        var _y = 132 + i * 16;
        var _w = string_width(_label);
        var _x = floor(PP_FRAME_W * 0.5 - _w * 0.5);

        if (!_enabled) draw_set_colour(pp_role_colour("dim"));
        else if (i == _battle.gameover_cursor) draw_set_colour(pp_role_colour("paper"));
        else draw_set_colour(pp_role_colour("text"));
        draw_text(_x, _y, _label);

        // The cursor is the 6 pixel arrow of spec 13, blinking 15 steps on and 15 off, drawn only on a row that can
        // be picked so a refused row never carries a cursor that says it can.
        if (i == _battle.gameover_cursor && _enabled && ((_battle.phase_steps div 15) mod 2 == 0)) {
            draw_set_colour(pp_role_colour("paper"));
            draw_triangle(_x - 12, _y, _x - 12, _y + 8, _x - 6, _y + 4, false);
        }
    }

    if (_battle.gameover_choice == "wait") {
        draw_set_colour(pp_role_colour("text"));
        draw_text_ext(PP_FRAME_W * 0.5, 168, "reading the last save", 10, PP_FRAME_W - 146);
    } else if (_battle.gameover_note_steps > 0 && _battle.gameover_note != "") {
        draw_set_colour(pp_role_colour("text"));
        draw_text_ext(PP_FRAME_W * 0.5, 168, _battle.gameover_note, 10, PP_FRAME_W - 146);
    }

    draw_set_halign(fa_left);
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
