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
        // Spec 18 section 1: the enemy's phases are the fight's shape, and they are data. The pool, the attack range
        // and the TALK set start from the enemy row and only ever change through pp_battle_enemy_phase_sync, which
        // reads a row's fields and nothing else. No field here is chosen by the enemy's id: an enemy with no phases
        // list keeps its own patterns, attack and talk dialogue for the whole fight, and a boss with four rows gets
        // four crossings from the same code.
        enemy_phase: 0,
        pattern_pool: pp_battle_pattern_pool(_enemy),
        attack_range: _enemy.attack,
        talk_set: "",
        // Card R30 (spec 19 sections 2 to 11): the baked talk of this fight. talk_mercy is the meter the effect enum
        // moves; talk_stage is "" or "options", the panel the menu phase draws instead of the command list; talk_hint
        // is the line under the box that Q9 puts there. trust above stays the spare gate spec 07 defines and this
        // card does not change it: three talks still reach SPARE whether the bake answers or the card pool does.
        talk_mercy: 0,
        talk_stage: "",
        talk_options: [],
        talk_cursor: 0,
        talk_delta: 0,
        talk_effect: "none",
        talk_mood: "guarded",
        talk_hint: "",
        talk_reply: false,
        talk_last_effect: "none",
        phase_line: "",
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
        // Card R48: the strip this fight draws on, resolved once at build time by pp_battle_bg_name, and a flag so
        // a build that is missing the art says so once instead of every step.
        bg_name: "",
        bg_missing_said: false,
        // Card t_4275136f: the same courtesy for the enemy's own sheet, which is looked up in the art index by the
        // enemy row's id at draw time rather than cached here, because the index is the build's, not the fight's.
        enemy_art_said: false,
        rng: pp_rng_new(_encounter.seed)
    };

    _battle.bg_name = pp_battle_bg_name(_battle);
    if (variable_struct_exists(_enemy, "talk_dialogue")) _battle.talk_set = _enemy.talk_dialogue;

    pp_battle_phase_set(_battle, PPBattlePhase.intro);
    return _battle;
}

/// The enemy's own patterns list is phase 1's pool (spec 18 section 1). A crossing appends to this copy, never to the
/// data row, so a second fight against the same enemy starts from the same pool.
function pp_battle_pattern_pool(_enemy) {
    var _out = [];
    if (!variable_struct_exists(_enemy, "patterns") || !is_array(_enemy.patterns)) return _out;
    for (var i = 0; i < array_length(_enemy.patterns); i++) array_push(_out, _enemy.patterns[i]);
    return _out;
}

/// The phase rows, or an empty list. At most four by the checker (PHASE_ROWS_MAX). Nothing here reads an enemy id.
function pp_battle_enemy_phases(_enemy) {
    if (variable_struct_exists(_enemy, "phases") && is_array(_enemy.phases)) return _enemy.phases;
    return [];
}

/// Spec 18 section 1: a row is entered when hp * 100 <= hp_at_or_below * max_hp, in integers only, so the crossing
/// lands on the same hp on every machine and halving max_hp in data moves every band with it. This is the only
/// threshold comparison in the director.
function pp_battle_enemy_phase_reached(_battle, _row) {
    return (_battle.enemy_hp * 100 <= _row.hp_at_or_below * _battle.enemy.max_hp);
}

/// Apply every crossing the current hp has reached, in data order, once each. The pool only grows, the attack only
/// moves to the row's own range, the TALK set only changes when the row names one, and the row's line is queued for
/// pp_battle_after_message to play once before the enemy's turn. Called from pp_battle_hurt_enemy, which is the only
/// place enemy hp moves.
function pp_battle_enemy_phase_sync(_battle) {
    var _rows = pp_battle_enemy_phases(_battle.enemy);
    while (_battle.enemy_phase < array_length(_rows)) {
        var _row = _rows[_battle.enemy_phase];
        if (!pp_battle_enemy_phase_reached(_battle, _row)) break;
        _battle.enemy_phase += 1;
        array_push(_battle.pattern_pool, _row.pattern_id);
        if (variable_struct_exists(_row, "attack")) _battle.attack_range = _row.attack;
        if (variable_struct_exists(_row, "talk_set")) _battle.talk_set = _row.talk_set;
        if (variable_struct_exists(_row, "line_id")) _battle.phase_line = _row.line_id;
    }
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
    // Card t_27aa179e: the command list says once per entry that it is live, with the cursor it opened on. A driver
    // outside the game (tools\capture_talk_fight.py) needs to know when a press will land on the list and not on a
    // board, a telegraph or a dodge, and a log after the run needs to say which cursor a key was read against. Once
    // per phase entry, so a fight writes one line per turn and not one per step.
    if (_battle.phase_steps == 1) {
        show_debug_message("PP: battle menu, turn " + string(_battle.turn) + ", cursor " + string(_battle.cursor)
            + ", enemy hp " + string(_battle.enemy_hp) + "/" + string(_battle.enemy.max_hp));
    }

    // Card R30: an open talk owns the menu while it runs. The panel is the menu phase's second shape, not a new
    // phase, so the turn loop above is untouched and the panel's pick hands its reply to the same board (pp_talk_step).
    if (_battle.talk_stage != "") {
        pp_talk_step(_battle);
        return;
    }

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
    // Card R30: the hint under the box and the reply flag last only until the player's next command, which is what
    // "cleared on the next confirm" means once the box has finished typing (spec 19 section 5, Q9).
    _battle.talk_hint = "";
    _battle.talk_reply = false;

    // Card t_27aa179e: one line per command, naming the command the player actually chose. `PP: battle start` says a
    // fight began and cannot say whether it was fought or talked through, which is the claim the hackathon evidence
    // has to support; this line is the one that can. The key comes off the same table the menu draws. It is written
    // before the command's own body, so a spare's line carries the enemy's bar as the press found it, full or not,
    // which is what separates a spare earned by trust from one earned by health.
    var _key = "unknown";
    var _table = pp_command_table();
    for (var i = 0; i < array_length(_table); i++) {
        if (_table[i].id == _battle.action) _key = _table[i].key;
    }
    show_debug_message("PP: command " + _key + ", turn " + string(_battle.turn) + ", enemy "
        + string(_battle.enemy.id) + ", enemy hp " + string(_battle.enemy_hp)
        + ", party hp " + string(_battle.actor.hp));

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
            // Card R30 (spec 19 sections 2 to 11): TALK opens the option panel. The three options, their reply text,
            // their hint and the mercy each one moves all come from data/meta_bake.json through pp_talk_begin, with the
            // card's own pool as the fallback; this case keeps the trust row spec 07 defines and nothing else, so the
            // SPARE gate still opens after three talks with no model in the build at all.
            pp_talk_begin(_battle);
            break;

        case PPCommand.spare:
            // Card t_905a18ce (F4): a route may refuse this entry, and the menu refuses it before the press arrives
            // (pp_battle_spare_route_refused). The same read guards the action, so a caller that bypasses the menu
            // cannot turn a refusal the data wrote into a spare.
            if (pp_battle_spare_allowed(_battle) && !pp_battle_spare_route_refused(_battle)) {
                _battle.result = PPResult.spare;
                _battle.enemy_hp = 0;
                pp_battle_enter_result(_battle);
            } else if (pp_battle_interrupt_ready(_battle)) {
                // Spec 18 section 4 rule 4: a refused SPARE at or below the enemy's interrupt threshold is the story
                // exit. The enemy is not killed and the party is not beaten, no counters move, and the turn is not
                // spent (spec 07 acceptance 3), so the player who asks for mercy pays nothing for asking.
                _battle.result = PPResult.interrupt;
                pp_battle_enter_interrupt(_battle);
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
    // Spec 18 section 1: rule 3 (the kill) beats rule 5 (a crossing), so a blow that ends the fight crosses nothing.
    if (_battle.enemy_hp > 0) pp_battle_enemy_phase_sync(_battle);
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
        // Spec 18 section 1: a crossing says its line once, before the enemy's turn. The id is taken and cleared
        // before the board opens, so a skipped or fast read of the board cannot play it twice.
        if (_battle.phase_line != "") {
            var _line_id = _battle.phase_line;
            _battle.phase_line = "";
            pp_battle_say(_battle, pp_battle_dialogue_lines(_line_id), "enemy_turn");
            return;
        }
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
    // Spec 18 section 1: the pool is the enemy's own patterns plus every pattern_id a crossing has added, in data
    // order. Reading _battle.pattern_pool instead of the enemy row is what keeps a phase's pattern reachable.
    var _ids = _battle.pattern_pool;
    if (!is_array(_ids) || array_length(_ids) == 0) return undefined;
    var _id = _ids[pp_rng_int(_battle.rng, 0, array_length(_ids) - 1)];
    var _pattern = pp_data_find(global.pp_data.patterns.patterns, _id);
    if (!is_undefined(_pattern)) return _pattern;
    if (array_length(global.pp_data.patterns.patterns) > 0) return global.pp_data.patterns.patterns[0];
    return undefined;
}

function pp_battle_roll_attack(_battle) {
    // Spec 18 section 6 consequence 1: a phase row may raise the attack inside the enemy's own band, so the roll
    // reads the range the current phase put in force and never the enemy row directly.
    var _atk = _battle.attack_range;
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

    // Card t_27aa179e: the result names the outcome word the panel prints, so a capture can tie the picture on the
    // panel to a line the game wrote. The word and the enemy are the two facts a reader cannot get from the frames:
    // `spare` and `kill` are both a result panel, and only this line says which one the game chose. The hp here is
    // the bar the word left behind (a spare sets it to 0 through the same door), so the line a full health spare is
    // proved on is the command line, which the director writes before the spare's own body runs.
    show_debug_message("PP: fight result " + pp_battle_outcome(_battle) + ", turn " + string(_battle.turn)
        + ", enemy " + string(_battle.enemy.id) + ", enemy hp " + string(_battle.enemy_hp)
        + "/" + string(_battle.enemy.max_hp));

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
    // Spec 18 section 4: the fourth ending a fight can have, no victory and no defeat. The card and the overworld
    // read this word, and the scene the fight hands over to comes from pp_battle_interrupt_scene.
    if (_battle.result == PPResult.interrupt) return "interrupted";
    if (_battle.result == PPResult.spare) return "spare";
    if (_battle.result == PPResult.kill) return "kill";
    return "unresolved";
}

function pp_battle_has_talk(_battle) {
    return is_string(_battle.talk_set) && _battle.talk_set != ""
        && !is_undefined(pp_data_find(global.pp_data.dialogue.dialogue, _battle.talk_set));
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

// ---------------------------------------------------------------------------------------------------------------
// The interruption (spec 18 section 4, card t_e5fa86d3)
//
// A fight can stop without a victory and without a defeat, and a scene does the story work. The enemy row's
// `interrupt` block says so, and the trigger is a SPARE press the enemy refuses at or below the block's threshold:
// NOT an hp crossing. Spec 18 section 8 A18-1 is the reason and it is arithmetic, not taste: rule 3 (a killing blow)
// only wins when one blow takes the bar from above the threshold all the way to 0, and the biggest legal blow is 12
// (18 with tide_step), so a crossing trigger above 11 hp of 120 (17 with the power) makes the boss unkillable on every
// route. Nothing in this section names an enemy, a scene or a route: the block comes off the row the way the phases do.

/// The enemy's interrupt block, or undefined. At most one per enemy, and the checker refuses the second (spec 18
/// section 7 refusal 7).
function pp_battle_interrupt_block(_enemy) {
    if (variable_struct_exists(_enemy, "interrupt") && is_struct(_enemy.interrupt)) return _enemy.interrupt;
    return undefined;
}

/// Does this SPARE press stop the fight instead of being refused? The order the spec writes is the order here: a dead
/// enemy is a kill, an accepted spare is a spare, and only then may the interrupt fire. The threshold is the gate on
/// the REQUEST, compared in integers exactly like a phase crossing, so no float and no rounding can move it.
function pp_battle_interrupt_ready(_battle) {
    if (_battle.enemy_hp <= 0) return false;
    if (pp_battle_spare_allowed(_battle)) return false;
    var _block = pp_battle_interrupt_block(_battle.enemy);
    if (is_undefined(_block)) return false;
    if (!variable_struct_exists(_block, "on") || _block.on != "spare_refused") return false;
    // A story beat that already happened does not happen twice. The flag is optional, and the checker proves it names
    // a real flag in data\flags.json.
    if (variable_struct_exists(_block, "unless_flag")) {
        if (pp_ledger_flag(_battle.ledger, _block.unless_flag)) return false;
    }
    if (!variable_struct_exists(_block, "hp_at_or_below")) return false;
    return (_battle.enemy_hp * 100 <= _block.hp_at_or_below * _battle.enemy.max_hp);
}

/// The route this fight is on, derived on read from the counters and the stage the way spec 10 asks (never stored).
/// `prison_stage` is the story's own boundary and lives in data\project.json, so a route key in a data row is compared
/// against a route nothing has written down (A18-4).
function pp_battle_route_name(_battle) {
    var _stage = 3;
    if (is_struct(global.pp_data.project) && variable_struct_exists(global.pp_data.project, "prison_stage")) {
        _stage = global.pp_data.project.prison_stage;
    }
    return pp_ledger_route_name(pp_ledger_route(_battle.ledger, _stage));
}

/// True when the encounter row refuses SPARE on the route this run is on. `spare_refuses_on_route` names a route key
/// (spec 07 line 33, spec 10's genocide row: the opposite entry is refused visibly). It is read in pp_command_state,
/// where every other refusal is read, because a field no code reads is a claim and not a rule (card t_905a18ce F4).
/// An empty or absent field refuses nothing: the demo's default is that mercy is always available.
function pp_battle_spare_route_refused(_battle) {
    var _enc = _battle.encounter;
    if (!is_struct(_enc)) return false;
    if (!variable_struct_exists(_enc, "spare_refuses_on_route")) return false;
    var _route = _enc.spare_refuses_on_route;
    if (!is_string(_route) || _route == "") return false;
    return (pp_battle_route_name(_battle) == _route);
}

/// The scene a finished fight hands its caller, or "" when it hands nothing over (spec 18 section 4 steps 4 and 6).
/// The caller takes this id BEFORE it clears the battle, because the row it is read from belongs to the fight.
function pp_battle_handoff_scene(_battle) {
    if (_battle.result == PPResult.interrupt) return pp_battle_interrupt_scene(_battle);
    return "";
}

/// The scene the interruption hands the fight to. One id, or the id under the route this run is on. The route is
/// derived HERE, from the counters and the exit row the fight has already written, because spec 10 recomputes the
/// route per read and never stores it: that is how a per route scene id exists without a stored route (A18-4).
/// Returns "" when the block names no scene, and the checker refuses that before the build can.
function pp_battle_interrupt_scene(_battle) {
    var _block = pp_battle_interrupt_block(_battle.enemy);
    if (is_undefined(_block) || !variable_struct_exists(_block, "scene")) return "";
    if (is_string(_block.scene)) return _block.scene;
    if (!is_struct(_block.scene)) return "";

    var _key = pp_battle_route_name(_battle);
    if (variable_struct_exists(_block.scene, _key)) return _block.scene[$ _key];
    return "";
}

/// Record the exit row and go straight to the result beat. An interruption opens no closing board: the scene that
/// takes over is where the story text lives, and spec 18 section 4 step 4 says the caller continues with no press.
/// The exit row is `turned` (PPResult.interrupt through pp_ledger_exit_of_result), which counts nothing and keeps the
/// row, so F3 shows the fight stopped rather than won or lost.
function pp_battle_enter_interrupt(_battle) {
    if (!_battle.recorded) pp_battle_record(_battle);
    _battle.messages = undefined;
    _battle.after_message = "";
    pp_battle_phase_set(_battle, PPBattlePhase.result);
    show_debug_message("PP: fight interrupted, scene " + pp_battle_interrupt_scene(_battle));
    return _battle;
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
// The battle background (card R48, spec 07's field)
//
// Card BG-BATTLE baked four 256x112 strips: corridor, wardroom, deck_night, quay_dusk. Each is drawn on the 16x16
// attribute grid as 16 by 7 cells, every cell painted from one of that scene's four background palettes, which is
// what lets it sit behind the arena without breaking the NES rules. This section puts one of them on screen.
//
// The origin is (0, 0) and it is not adjustable. The strip is exactly 7 cells tall and 16 cells wide, so its own
// attribute areas only land on the screen's 16 pixel grid when its top edge and left edge are on that grid: 0 is
// the only origin that keeps every cell boundary a multiple of 16, and the art lane's own sidecar already writes
// "strip_y": 0 for the frame it previews. The field runs to PP_MENU_TOP (168, spec 07's lower third), so the
// strip covers rows 0 to 112 and the ground band under it covers 112 to 168 in one palette role.
//
// The strip is chosen by the encounter row first and the map row second, so a fight that has been given its own
// backdrop keeps it on any map, and a fight on a map keeps the map's room. A fight that names neither draws the
// corridor strip and says nothing in play: R48's check 4, silent because a fallback is not something a player can
// act on.

/// The four strips, spelled the way the art lane's own files and the scene palette sets spell them.
function pp_battle_bg_strips() {
    return ["corridor", "wardroom", "deck_night", "quay_dusk"];
}

/// The field origin. One function so the probe and the draw cannot disagree about it.
function pp_battle_bg_x() { return 0; }
function pp_battle_bg_y() { return 0; }
function pp_battle_bg_w() { return 256; }
function pp_battle_bg_h() { return 112; }

/// The message window over the field: whole 16 pixel cells from the top (0 to 48), full width, which is 48 pixels
/// of text area for the four lines a spec 05 page holds at the 8 pixel pitch of Q2 in the 2026-10-22 decisions.
/// It is cell aligned on purpose: a window that sits on whole attribute areas shares no 16x16 cell with the strip,
/// so the frame stays inside the NES rule of 3 background colours plus the backdrop per area even while a message
/// covers the top of the field. Neither "text box" is drawn over the strip's art in any other sense: the window is
/// opaque and the strip simply stops being visible behind it.
function pp_battle_text_box_x1() { return 0; }
function pp_battle_text_box_y1() { return 0; }
function pp_battle_text_box_x2() { return 256; }
function pp_battle_text_box_y2() { return 48; }

/// A strip name from data, normalised: "corridor", "bg_battle_corridor", "battle_corridor" and "BG-BATTLE corridor"
/// all resolve to a strip that exists, and anything else resolves to "" so the caller falls back. Case and spaces
/// are folded because the name is written by a person in a data row, and a strip id is not a place to be strict.
function pp_battle_bg_clean(_raw) {
    if (!is_string(_raw)) return "";
    var _s = string_lower(string_replace_all(string_replace_all(_raw, " ", "_"), "-", "_"));
    if (string_length(_s) >= 10 && string_copy(_s, 1, 10) == "bg_battle_") _s = string_delete(_s, 1, 10);
    else if (string_length(_s) >= 7 && string_copy(_s, 1, 7) == "battle_") _s = string_delete(_s, 1, 7);
    var _names = pp_battle_bg_strips();
    for (var i = 0; i < array_length(_names); i++) {
        if (_names[i] == _s) return _s;
    }
    return "";
}

/// The strip a room palette set draws on. Three of the four sets are ship rooms and each has a matching baked
/// strip; the ui set is not a room at all, so it names none and the caller keeps its fallback. deck_day draws the
/// deck at night because that is the only open deck strip that exists, and a day deck strip is not this card's art.
function pp_battle_bg_for_room(_set) {
    switch (string(_set)) {
        case "lower_deck": return "corridor";
        case "ship_cabin": return "wardroom";
        case "deck_day": return "deck_night";
    }
    return "";
}

/// The room palette set the map the player is standing on declared, or "" when no world is loaded.
function pp_battle_bg_room_set() {
    if (!variable_global_exists("pp")) return "";
    if (!is_struct(global.pp)) return "";
    if (!variable_struct_exists(global.pp, "world")) return "";
    var _world = global.pp.world;
    if (!is_struct(_world)) return "";
    if (!variable_struct_exists(_world, "map")) return "";
    var _map = _world.map;
    if (!is_struct(_map)) return "";
    if (!variable_struct_exists(_map, "room_palette")) return "";
    return string(_map.room_palette);
}

/// The strip this fight draws on. Encounter row first, map row second, corridor last, and the last one is silent.
function pp_battle_bg_name(_battle) {
    if (is_struct(_battle) && variable_struct_exists(_battle, "encounter") && is_struct(_battle.encounter)) {
        var _enc = _battle.encounter;
        if (variable_struct_exists(_enc, "bg_battle")) {
            var _own = pp_battle_bg_clean(_enc.bg_battle);
            if (_own != "") return _own;
        }
        if (variable_struct_exists(_enc, "background")) {
            var _bg = pp_battle_bg_clean(_enc.background);
            if (_bg != "") return _bg;
        }
    }

    var _from_room = pp_battle_bg_for_room(pp_battle_bg_room_set());
    if (_from_room != "") return _from_room;

    return "corridor";
}

/// The art index name of a strip: the mirror writes one row per PNG, so the name is the file's stem.
function pp_battle_bg_sprite(_name) {
    return "bg_battle_" + string(_name);
}

/// Draw the field: the ground band, then the strip at the spec 07 origin. Returns the strip that was asked for, so
/// the probe can prove the row really chose it.
function pp_battle_draw_field(_battle) {
    var _name = _battle.bg_name;
    if (_name == "") _name = pp_battle_bg_name(_battle);

    // The ground band, 112 to the menu band in one role. dim is one of the four roles every set in
    // data\room_palettes.json carries (the same four the game over card spends), so RULE 0 holds in every room and
    // the band can never fall through to PP_COLOUR_MISSING.
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(pp_battle_bg_x(), pp_battle_bg_h(), pp_battle_bg_x() + pp_battle_bg_w() - 1, PP_MENU_TOP - 1, false);

    var _sprite = pp_battle_bg_sprite(_name);
    if (pp_art_has(_sprite)) {
        pp_art_draw(_sprite, 0, pp_battle_bg_x(), pp_battle_bg_y(), PP_UNTINTED, 1);
        return _name;
    }

    // Card t_4275136f: the strip reaches the build now. tools\sync_art.py mirrors game\sprites_src\bg\ (and the enemy
    // sheets) into game\datafiles\art, so this branch is the build that is missing the file rather than every build.
    // A missing strip is a field with no picture and never an error, and it is said once rather than every step.
    if (!_battle.bg_missing_said) {
        _battle.bg_missing_said = true;
        show_debug_message("PP battle: " + _sprite + " is not in the art index, the field draws without its strip");
    }
    return _name;
}

// ---------------------------------------------------------------------------------------------------------------
// The actors: the enemy sheet and the party's sheets (card t_4275136f)
//
// Ruling 7.5 of knowledge\PALETTE-RULINGS-2026-10-25.md: on a battle strip that draws all four heroes the enemy is
// BACKGROUND art, and the four sprite palettes are the party's. The two draws below are not interchangeable. The
// party's sheets cost one sprite triple each, which are the four reserved hero triples (ruling 7.2, the paint landed
// on card t_d5483a88); the enemy's sheet costs no sprite palette at all, because its three colours are already
// carried by the background triple of the area it stands on plus the scene's one shared backdrop. On the deck that
// is bg2 $00 $30 $02 plus $0F, which carries the sailor's sheet ($02 $0F $30) whole (rulings 15.3 and 15.4, card
// t_34b1d96a). That is why the enemy is drawn with PP_UNTINTED: it is background art standing in the background's
// own colours, not a sprite that needs a row.
//
// Every number here is the battle screen's own row in data\ui_layouts.json, read at run time instead of restated in
// code: the enemy's slot is that row's first `enemies` entry (tile 3,8 at 32x32) and the party column is its `party`
// array (four 24x32 slots at tile x 28, tile y 4, 8, 12 and 16), whose `member` names are the ids the sheets are
// named after. No hero and no enemy is named in this file, because a table in code is a second place to disagree
// with the art lane; tests\test_enemy_phases.py and tests\test_prometheus_interrupt.py already refuse an enemy name
// here for the same reason, and tests\test_battle_draw.py holds these readers to the file's own members and tiles.

/// The battle screen's row in data\ui_layouts.json, or undefined when the bundle has none. One reader, so the slots
/// below cannot disagree with each other or with the file.
function pp_battle_layout() {
    if (!is_struct(global.pp_data)) return undefined;
    if (!variable_struct_exists(global.pp_data, "ui_layouts")) return undefined;
    var _file = global.pp_data.ui_layouts;
    if (!is_struct(_file) || !is_array(_file.screens)) return undefined;
    for (var i = 0; i < array_length(_file.screens); i++) {
        if (string(_file.screens[i].name) == "battle") return _file.screens[i];
    }
    return undefined;
}

/// "24x32" as [24, 32]. A layout row states a tile rect and the pixel size a sheet is, and the pixel size is what a
/// draw call needs; the tile rect is what the tests check the pixel size against.
function pp_battle_pixels(_text) {
    var _parts = string_split(string(_text), "x");
    if (array_length(_parts) < 2) return [0, 0];
    return [real(_parts[0]), real(_parts[1])];
}

/// The battle screen's first enemy slot, in pixels: the layout's tile rect times 8, and the size its row states.
/// Undefined when there is no layout, which is a bundle the boot card has already complained about.
function pp_battle_enemy_slot() {
    var _screen = pp_battle_layout();
    if (is_undefined(_screen)) return undefined;
    if (!is_array(_screen.enemies) || array_length(_screen.enemies) == 0) return undefined;
    var _row = _screen.enemies[0];
    var _size = pp_battle_pixels(_row.pixels);
    return { x: _row.x * 8, y: _row.y * 8, w: _size[0], h: _size[1] };
}

/// The party column: one slot per member the layout names, in the file's own order, top slot first. The id is the
/// member name lowered, because the sheets are named after the hero (game\sprites_src\chars\<id>_battle.png).
function pp_battle_party_slots() {
    var _out = [];
    var _screen = pp_battle_layout();
    if (is_undefined(_screen)) return _out;
    if (!is_array(_screen.party)) return _out;
    for (var i = 0; i < array_length(_screen.party); i++) {
        var _row = _screen.party[i];
        var _size = pp_battle_pixels(_row.pixels);
        array_push(_out, { id: string_lower(string(_row.member)),
                           x: _row.x * 8, y: _row.y * 8, w: _size[0], h: _size[1] });
    }
    return _out;
}

/// The art index name of a hero's battle sheet: the hero id and "_battle". tools\sync_art.py has mirrored that
/// folder since card ASSEMBLE, so the sheets were in the index before anything drew them.
function pp_battle_party_sprite(_id) {
    return string(_id) + "_battle";
}

/// The art index name of the enemy's sheet, or "" when this build has none. game\sprites_src\enemies\ holds one
/// sheet per enemy id that has art, which is why the id is the name: no table maps an enemy to a file, and a second
/// table would be a second place to disagree with the art lane. An enemy with no sheet returns "" and draws a block.
function pp_battle_enemy_sprite(_battle) {
    if (!is_struct(_battle) || !is_struct(_battle.enemy)) return "";
    if (!variable_struct_exists(_battle.enemy, "id")) return "";
    var _name = string(_battle.enemy.id);
    if (_name == "") return "";
    if (!pp_art_has(_name)) return "";
    return _name;
}

/// The frame an actor's sheet is on. The sheets are 8 fps strips (frames 0 and 1 are the idle pair and the last is
/// the hit frame), so the frame comes off the fight's own counters: the turn, at 120 steps, plus the steps since the
/// phase began. pp_art_frame_at does the wrap, so a sheet with one frame is always frame 0.
function pp_battle_actor_frame(_battle, _name) {
    return pp_art_frame_at(_name, _battle.turn * 120 + _battle.phase_steps);
}

/// The enemy, as background art in the battle screen's own enemy slot. PP_UNTINTED is the whole palette argument this
/// call makes: the sheet is drawn exactly as authored, in the three colours its sidecar names ($0F $02 $30), so no
/// sprite palette is spent on it and the strip keeps its four for the party.
function pp_battle_draw_enemy(_battle, _slot) {
    if (is_undefined(_slot)) return false;

    var _name = pp_battle_enemy_sprite(_battle);
    if (_name != "") {
        pp_art_draw(_name, pp_battle_actor_frame(_battle, _name), _slot.x, _slot.y, PP_UNTINTED, 1);
        return true;
    }

    // No sheet in the index for this enemy: the flat block the screen drew before the art landed, in the same slot,
    // so a fight still shows an enemy standing there. Said once per fight, not once per step.
    if (!_battle.enemy_art_said) {
        _battle.enemy_art_said = true;
        show_debug_message("PP battle: no sheet for enemy " + string(_battle.enemy.id)
            + " in the art index, the slot draws a block");
    }
    draw_set_colour(pp_role_colour("text"));
    draw_rectangle(_slot.x, _slot.y, _slot.x + _slot.w - 1, _slot.y + _slot.h - 1, false);
    return false;
}

/// The party: one battle sheet per slot the layout names, in the reserved hero triples the sheets are painted on. A
/// slot whose sheet is not in the build is skipped and the rest still draw, because one missing sheet must not empty
/// the block. Returns how many were drawn, which is the number the test and the capture both read.
function pp_battle_draw_party(_battle) {
    var _slots = pp_battle_party_slots();
    var _drawn = 0;
    for (var i = 0; i < array_length(_slots); i++) {
        var _slot = _slots[i];
        var _name = pp_battle_party_sprite(_slot.id);
        if (!pp_art_has(_name)) continue;
        pp_art_draw(_name, pp_battle_actor_frame(_battle, _name), _slot.x, _slot.y, PP_UNTINTED, 1);
        _drawn += 1;
    }
    return _drawn;
}

// ---------------------------------------------------------------------------------------------------------------
// Drawing. The field is a baked strip, the enemy and the party are their own sheets, and every other mark is a flat
// rectangle or a glyph in a palette role (spec 13 owns the final art).
//
// RULE 0 first (card R48): the battle screen spends four roles and no others, ink, paper, dim and text, the only
// four every set in data\room_palettes.json carries. The field used to ask for hazard, accent and warn, and a fight
// on the small ship's deck (ship_small, room_palette deck_day) declares none of the three, so the enemy body, the
// health bar, the cursor, the damage popup, the timing bar and the telegraph line all drew as
// PP_COLOUR_MISSING (255, 0, 255) in the one room the demo fights in. A role a set does not carry is not a colour
// the map's room palette holds, which is exactly what R48's check refuses.

function pp_battle_draw(_battle) {
    draw_set_alpha(1);
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    // Card R48: the baked strip is the field, drawn first so every actor, the arena and every window sit on top of
    // it (knowledge\SPEC-DELTAS.md T1's draw order: map, dimmer, battle field, GUI).
    pp_battle_draw_field(_battle);

    // Card t_4275136f: the actors. The enemy stands in the battle screen's own enemy slot as background art and the
    // party's sheets fill the slots its `party` array names, both read from data\ui_layouts.json. The two flat
    // rectangles that used to be here (a hero at 40,96 and an enemy block at 176,72) were the pre art stand-ins and
    // they are gone, because a placeholder left on screen beside the real draws would read as a second enemy. The
    // enemy's name, its health bar and the damage popup follow it to the left half for the same reason.
    var _enemy_slot = pp_battle_enemy_slot();
    pp_battle_draw_enemy(_battle, _enemy_slot);
    pp_battle_draw_party(_battle);

    if (!is_undefined(_enemy_slot)) {
        // Card BATTLE-FONT-WIRE: the enemy's name is the sheet's glyphs, over the slot the enemy stands in. The names
        // in data/enemies/all.json run to 11 characters (88 px) and the slot's centre would put the first glyph
        // outside the frame, so the name is centred on x 48, the nearest 8 px cell boundary that holds the longest
        // name whole (x 4 to x 92) and still reads as the enemy's own label.
        pp_font_draw_centre(_battle.enemy.name, 48, 56, 1);

        // Enemy health bar, twice the slot's width, under the enemy's own body: on the deck that is x 8 to 71,
        // y 100 to 103, inside the strip's lower band and clear of the party column.
        var _bar_w = _enemy_slot.w * 2;
        var _bar_x = _enemy_slot.x - 16;
        var _bar_y = _enemy_slot.y + _enemy_slot.h + 4;
        var _hp_frac = _battle.enemy_hp / max(1, _battle.enemy.max_hp);
        draw_set_colour(pp_role_colour("dim"));
        draw_rectangle(_bar_x, _bar_y, _bar_x + _bar_w - 1, _bar_y + 3, false);
        draw_set_colour(pp_role_colour("text"));
        draw_rectangle(_bar_x, _bar_y, _bar_x + floor(_bar_w * _hp_frac), _bar_y + 3, false);
    }

    // Player health and will. Card BATTLE-FONT-WIRE wrote this as `HP 12 OF 12` because the sheet had no slash;
    // card SHEET-GLYPH-GAP (t_f476435e, decision D13) grew the sheet a slash and the two brackets, so the line now
    // reads the way the rest of the idiom writes it. 22 characters at the slice's numbers, x 16 to x 192, inside the
    // frame.
    pp_font_draw("HP " + string(_battle.actor.hp) + "/" + string(_battle.actor.max_hp)
        + "   WILL " + string(_battle.actor.will) + "/" + string(_battle.actor.will_max), 16, 156, 1);

    if (_battle.phase == PPBattlePhase.intro) {
        if (_battle.phase_steps < PP_INTRO_FLASH_STEPS && (_battle.phase_steps div 4) mod 2 == 0) {
            draw_set_alpha(0.7);
            draw_set_colour(pp_role_colour("text"));
            draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
            draw_set_alpha(1);
        }
    }

    // Card R48: the arena draws before the menu band, because spec 08 dims "the rest of the field" and spec 07's
    // command band is not field: the box frame reaches row 170, and with the band drawn first those 2 pixels would be
    // painted over the command window's top border. Drawing the band last keeps the overhang inside the field.
    if (_battle.phase == PPBattlePhase.dodge && !is_undefined(_battle.arena)) {
        pp_arena_draw(_battle.arena);
    }

    if (_battle.phase == PPBattlePhase.menu || _battle.phase == PPBattlePhase.resolve) {
        // Card R30: while a talk is open the band draws its three options instead of the command list, and the prompt
        // takes the message window. Both shapes are spec 16 section 1: the options are the enemy's own three lines.
        if (_battle.talk_stage != "") pp_talk_draw_options(_battle);
        else pp_battle_draw_menu(_battle);
    }

    if (_battle.phase == PPBattlePhase.resolve) {
        pp_battle_draw_bar(_battle);
    }

    // Card R48: the message window sits on whole 16 pixel cells so it shares no attribute area with the strip.
    if (!is_undefined(_battle.messages)) {
        draw_set_colour(pp_role_colour("paper"));
        draw_rectangle(pp_battle_text_box_x1(), pp_battle_text_box_y1(),
                       pp_battle_text_box_x2() - 1, pp_battle_text_box_y2() - 1, false);
        draw_set_colour(pp_role_colour("dim"));
        draw_rectangle(pp_battle_text_box_x1(), pp_battle_text_box_y1(),
                       pp_battle_text_box_x2() - 1, pp_battle_text_box_y2() - 1, true);
        // Card R30: a baked reply draws at spec 19's 8 pixel pitch with the hint on the row under it (Q2 and Q9), and
        // every other line keeps spec 05's pitch. The window does not grow for either.
        if (_battle.talk_reply) {
            pp_talk_board_draw(_battle.messages, pp_talk_text_x(), pp_talk_text_y());
            pp_talk_hint_draw(_battle.talk_hint);
        } else {
            pp_text_board_draw(_battle.messages, 16, 16);
        }
    }

    if (_battle.popup_steps > 0 && !is_undefined(_enemy_slot)) {
        // Card BATTLE-FONT-WIRE: the number is the sheet's glyphs on a plate of the room's ink, because it rises over
        // the enemy's sheet, and white on a light body is not a number a player can read. Card t_4275136f moves it
        // from x 200 to the enemy's own slot centre with the enemy it belongs to.
        pp_font_draw_plated_centre(string(_battle.popup_value), _enemy_slot.x + _enemy_slot.w * 0.5,
                                   120 - (PP_DAMAGE_POPUP_STEPS - _battle.popup_steps), 1);
    }

    if (_battle.phase == PPBattlePhase.telegraph) {
        pp_font_draw_centre("here it comes", PP_FRAME_W * 0.5, 96, 1);
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

    // Card BATTLE-FONT-WIRE: the card's title, its rule and every row are the sheet's glyphs now. The card's inner
    // ink area is x 66 to x 190, 124 px, which is 15 glyphs a row: a sentence wraps there at the sheet's 8 px pitch
    // and the two rows it can take land inside the card's bottom edge at y 174.
    var _card_cols = pp_font_cols(124);
    pp_font_draw_centre("GAME OVER", PP_FRAME_W * 0.5, 78, 1);

    // The rule under the title: 2 pixels, dim, no gradient and no shadow (spec 13 line and shape).
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(96, 94, 160, 96, false);

    // The enemy is named on the card, because this screen is the only place the run says what took the player down.
    // No asterisk: the 8x8 sheet carries no glyph for one, and this is a card and not a dialogue line (spec 05).
    pp_font_draw_wrapped_centre(string(_battle.enemy.name) + " stands over you.",
        PP_FRAME_W * 0.5, 102, _card_cols, 8, 1);

    var _rows = pp_battle_gameover_rows();
    var _can_continue = pp_battle_gameover_can_continue();
    for (var i = 0; i < array_length(_rows); i++) {
        var _label = _rows[i];
        var _enabled = (i != 0) || _can_continue;
        var _y = 132 + i * 16;
        var _w = pp_font_width(_label);
        var _x = floor(PP_FRAME_W * 0.5 - _w * 0.5);

        // One ink (rule 6): a row that cannot be picked is ruled through rather than greyed, and the row the cursor is
        // on carries a 2 px rule under it rather than a lighter label. The old frame spent three roles on three states
        // of the same nine glyphs, which the sheet cannot do without a multiply no PPU can output.
        if (!_enabled) pp_font_draw_centre_struck(_label, PP_FRAME_W * 0.5, _y, 1);
        else pp_font_draw_centre(_label, PP_FRAME_W * 0.5, _y, 1);

        if (i == _battle.gameover_cursor && _enabled && ((_battle.phase_steps div 15) mod 2 == 0)) {
            draw_set_colour(pp_role_colour("text"));
            draw_rectangle(_x, _y + 9, _x + _w - 1, _y + 10, false);
        }
    }

    // The card has no room left for a sentence once its rows and its cursor rule are drawn: 8 px cells are 2.6 times
    // the width of the old default font, and the two row notes here are 27 and 30 characters. So the sentence sits
    // on the black band under the card, one full width row at 30 columns, which is inside the frame and clear of the
    // card's bottom edge at y 177. It is the same sentence in the same place in the flow: it appears when a row is
    // refused and lasts 90 steps.
    var _note_cols = pp_font_cols(PP_FRAME_W - 16);
    if (_battle.gameover_choice == "wait") {
        pp_font_draw_wrapped_centre("reading the last save", PP_FRAME_W * 0.5, 182, _note_cols, 8, 1);
    } else if (_battle.gameover_note_steps > 0 && _battle.gameover_note != "") {
        pp_font_draw_wrapped_centre(_battle.gameover_note, PP_FRAME_W * 0.5, 182, _note_cols, 8, 1);
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
        // Card BATTLE-FONT-WIRE: the label is the sheet's glyphs in the sheet's one ink. A refused entry used to be
        // drawn in the dim role, which the sheet cannot do without a multiply no PPU can output, so it is ruled
        // through instead (rule 6); the cursor arrow still marks the row the player is on.
        if (_state.enabled) pp_font_draw(_entry.label, _x, _yy, 1);
        else pp_font_draw_struck(_entry.label, _x, _yy, 1);
        if (i == _battle.cursor) {
            draw_set_colour(pp_role_colour("text"));
            draw_triangle(_x - 10, _yy, _x - 10, _yy + 8, _x - 4, _yy + 4, false);
        }
    }

    if (_battle.cursor_note_steps > 0 && _battle.cursor_note != "") {
        // The reason a row is refused, one row on the band's bottom line at 28 columns. It sat at PP_FRAME_H - 20
        // before, which crosses the third label row at 216 once a glyph is 8 px tall; at PP_FRAME_H - 16 its 8 px
        // clear the labels' bottom edge at 224 and the band's own border at 232.
        pp_font_draw_wrapped(_battle.cursor_note, 16, PP_FRAME_H - 16, pp_font_cols(PP_FRAME_W - 32), 8, 1);
    }
}

function pp_battle_draw_bar(_battle) {
    var _y = 120;
    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(48, _y, 208, _y + 6, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(126, _y - 2, 130, _y + 8, false);
    draw_set_colour(pp_role_colour("text"));
    draw_rectangle(48 + floor(1.6 * _battle.bar_pos) - 1, _y - 4, 48 + floor(1.6 * _battle.bar_pos) + 1, _y + 10, false);
    pp_font_draw("Z", 48, _y + 12, 1);
}
