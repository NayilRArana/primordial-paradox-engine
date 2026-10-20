/// pp_app: the application mode machine (spec 01). One persistent owner, one door for every swap, one fade.
/// A mode is a struct with enter, step and draw. A request names a mode and parameters; a missing mode fails loudly at
/// boot rather than mid scene. No other module sets the mode.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The structure is spec 01: a registry, a
/// single request door and one fade, with no phase number shared between modules.

/// Create the game frame, load data, register the modes that exist, and enter boot.
/// Called once from obj_pp_game's Create event.
function pp_app_boot() {
    global.pp = {
        data: undefined,
        input: undefined,
        camera: undefined,
        ledger: undefined,
        app: undefined
    };

    global.pp_input = pp_input_init();
    global.pp_camera = pp_camera_init();
    global.pp_data = pp_data_load();
    global.pp_ledger = pp_ledger_new();

    var _app = {
        mode: -1,
        mode_params: {},
        modes: {},
        fade_alpha: 0,
        fade_dir: 0,
        fade_steps: 0,
        pending: undefined,
        last_outcome: ""
    };
    global.pp.app = _app;

    pp_app_register(PPMode.boot, pp_mode_boot());
    pp_app_register(PPMode.overworld, pp_mode_overworld());
    pp_app_register(PPMode.battle, pp_mode_battle());

    pp_app_enter(PPMode.boot, {});
    return _app;
}

/// Register one mode. Registering twice is a programming error and is reported once.
function pp_app_register(_mode, _handlers) {
    var _app = global.pp.app;
    if (variable_struct_exists(_app.modes, string(_mode))) {
        if (PP_DEBUG) show_debug_message("mode registered twice: " + string(_mode));
    }
    _app.modes[$ string(_mode)] = _handlers;
    return _handlers;
}

/// The only door for a mode swap. During a fade the newest request replaces the older one (spec 01 rule 2).
function pp_app_request(_mode, _params) {
    var _app = global.pp.app;
    if (!variable_struct_exists(_app.modes, string(_mode))) {
        // A mode that was never registered must fail where it is seen, not be silently ignored.
        show_debug_message("PP: request for unregistered mode " + string(_mode));
        return false;
    }
    if (_app.fade_dir != 0) {
        _app.pending = { mode: _mode, params: _params };
        return true;
    }
    _app.pending = { mode: _mode, params: _params };
    pp_app_fade_out();
    return true;
}

/// Jump with no fade, for boot only.
function pp_app_enter(_mode, _params) {
    var _app = global.pp.app;
    if (!variable_struct_exists(_app.modes, string(_mode))) {
        show_debug_message("PP: enter for unregistered mode " + string(_mode));
        return false;
    }
    _app.mode = _mode;
    _app.mode_params = _params;
    var _mode_struct = _app.modes[$ string(_mode)];
    if (variable_struct_exists(_mode_struct, "enter")) {
        _mode_struct.enter(_params);
    }
    pp_input_lock(PP_INPUT_LOCK_STEPS);
    return true;
}

function pp_app_fade_out() {
    var _app = global.pp.app;
    _app.fade_alpha = 0;
    _app.fade_dir = 1;
    _app.fade_steps = 0;
}

function pp_app_fade_in() {
    var _app = global.pp.app;
    _app.fade_alpha = 1;
    _app.fade_dir = -1;
    _app.fade_steps = 0;
}

/// One step: advance the fade, swap at the black frame, then step the mode.
function pp_app_step() {
    var _app = global.pp.app;

    if (_app.fade_dir != 0) {
        _app.fade_steps += 1;
        _app.fade_alpha += _app.fade_dir * (1 / PP_FADE_STEPS);
        if (_app.fade_dir > 0 && _app.fade_alpha >= 1) {
            _app.fade_alpha = 1;
            if (!is_undefined(_app.pending)) {
                var _p = _app.pending;
                _app.pending = undefined;
                pp_app_enter(_p.mode, _p.params);
            }
            pp_app_fade_in();
        } else if (_app.fade_dir < 0 && _app.fade_alpha <= 0) {
            _app.fade_alpha = 0;
            _app.fade_dir = 0;
        }
    }

    var _mode = _app.modes[$ string(_app.mode)];
    if (!is_undefined(_mode) && variable_struct_exists(_mode, "step")) {
        _mode.step(_app.mode_params);
    }

    // A request that arrived while a fade was running is kept in pending; once the screen is settled its own fade out
    // starts here, otherwise the newest request would be silently dropped (spec 01 rule 2).
    if (_app.fade_dir == 0 && !is_undefined(_app.pending)) {
        pp_app_fade_out();
    }
    return _app;
}

/// Draw the mode, then the fade rectangle over it.
function pp_app_draw() {
    var _app = global.pp.app;
    var _mode = _app.modes[$ string(_app.mode)];
    if (!is_undefined(_mode) && variable_struct_exists(_mode, "draw")) {
        _mode.draw(_app.mode_params);
    }
    if (_app.fade_alpha > 0) {
        draw_set_alpha(_app.fade_alpha);
        draw_set_colour(c_black);
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
    }
}

function pp_app_mode() {
    return global.pp.app.mode;
}

// ---------------------------------------------------------------------------------------------------------------
// Mode: boot. Shows the title card and any data problem in plain words, then enters the slice encounter.

function pp_mode_boot() {
    return {
        enter: function(_params) {
            global.pp.app.boot_steps = 0;
            global.pp.app.boot_message = "";
            if (is_struct(_params) && variable_struct_exists(_params, "message")) {
                global.pp.app.boot_message = _params.message;
            }
        },
        step: function(_params) {
            var _app = global.pp.app;
            _app.boot_steps += 1;
            if (!pp_data_ok()) return;
            if (_app.boot_steps > 60 || pp_pressed("confirm")) {
                var _slice = global.pp_data.slice;
                pp_app_request(PPMode.overworld, { map_id: _slice.map, spawn: _slice.spawn, scene: _slice.scene });
            }
        },
        draw: function(_params) {
            draw_set_colour(pp_role_colour("paper"));
            draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
            draw_set_colour(pp_role_colour("ink"));
            draw_set_halign(fa_center);
            draw_text(PP_FRAME_W * 0.5, 100, "PRIMORDIAL PARADOX");
            draw_set_halign(fa_left);

            if (!pp_data_ok()) {
                draw_set_colour(pp_role_colour("hazard"));
                draw_text_ext(16, 128, pp_data_error_text(), 10, PP_FRAME_W - 32);
            } else if (global.pp.app.boot_message != "") {
                draw_set_colour(pp_role_colour("accent"));
                draw_text(16, 128, global.pp.app.boot_message);
            }

            if (PP_DEBUG) {
                draw_set_colour(pp_role_colour("dim"));
                draw_text(8, PP_FRAME_H - 16, "debug build  mode " + string(pp_app_mode()));
            }
        }
    };
}

// ---------------------------------------------------------------------------------------------------------------
// Mode: battle. Owns one fight; when the fight ends and the player confirms, it returns to boot with the outcome.

function pp_mode_battle() {
    return {
        enter: function(_params) {
            var _battle = undefined;
            global.pp.battle_encounter = "";
            var _enc = pp_data_find(global.pp_data.encounters.encounters, _params.encounter_id);
            if (!is_undefined(_enc)) {
                global.pp.battle_encounter = _enc.id;
                var _enemy_id = _enc.enemies[0];
                var _enemy = pp_data_find(global.pp_data.enemies.enemies, _enemy_id);
                var _party = global.pp_data.party.characters[0];
                if (!is_undefined(_enemy) && !is_undefined(_party)) {
                    _battle = pp_battle_new(_enc, _enemy, _party, global.pp_ledger);
                }
            }
            global.pp.battle = _battle;
        },
        step: function(_params) {
            var _battle = global.pp.battle;
            if (is_undefined(_battle)) return;

            if (pp_battle_finished(_battle)) {
                if (pp_pressed("confirm")) {
                    // The ledger was written inside the battle; the overworld only takes the result and the flags.
                    var _outcome = pp_battle_outcome(_battle);
                    var _enc_id = global.pp.battle_encounter;
                    global.pp.battle = undefined;
                    pp_overworld_battle_finished(global.pp.world, _enc_id, _outcome);
                    pp_app_request(PPMode.overworld, { resumed: true });
                }
                return;
            }
            pp_battle_step(_battle);
        },
        draw: function(_params) {
            var _battle = global.pp.battle;
            if (is_undefined(_battle)) {
                draw_set_colour(c_black);
                draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
                return;
            }
            pp_battle_draw(_battle);

            if (pp_battle_finished(_battle)) {
                draw_set_colour(pp_role_colour("paper"));
                draw_rectangle(40, 100, PP_FRAME_W - 40, 140, false);
                draw_set_colour(pp_role_colour("ink"));
                draw_set_halign(fa_center);
                draw_text(PP_FRAME_W * 0.5, 112, pp_battle_outcome(_battle));
                draw_text(PP_FRAME_W * 0.5, 126, "press Z");
                draw_set_halign(fa_left);
            }
        }
    };
}

// ---------------------------------------------------------------------------------------------------------------
// Mode: overworld. The map, the walker, the scene over it and the dialogue box. A battle is requested from here and
// hands control back here, which is what makes the slice a loop rather than a one way trip.

function pp_mode_overworld() {
    return {
        enter: function(_params) {
            var _resumed = is_struct(_params) && variable_struct_exists(_params, "resumed") && _params.resumed;
            if (_resumed && !is_undefined(global.pp.world)) return;

            var _slice = global.pp_data.slice;
            var _map_id = _slice.map;
            var _spawn = _slice.spawn;
            if (is_struct(_params) && variable_struct_exists(_params, "map_id")) {
                _map_id = _params.map_id;
                _spawn = _params.spawn;
            }
            global.pp.world = pp_overworld_new(_map_id, _spawn);
            if (is_undefined(global.pp.world)) {
                show_debug_message("PP: the slice names a map that does not load, staying in boot");
                pp_app_request(PPMode.boot, { message: "map did not load: " + string(_map_id) });
                return;
            }

            // The slice's opening scene plays once, then the player walks.
            var _scene_id = "";
            if (is_struct(_params) && variable_struct_exists(_params, "scene")) {
                _scene_id = _params.scene;
            } else if (variable_struct_exists(_slice, "scene")) {
                _scene_id = _slice.scene;
            }
            if (_scene_id != "" && !_resumed) {
                var _flag = "scene_" + string(_scene_id);
                if (!pp_ledger_flag(global.pp_ledger, _flag)) {
                    pp_overworld_start_scene(global.pp.world, _scene_id);
                    pp_ledger_set_flag(global.pp_ledger, _flag, true);
                }
            }
        },
        step: function(_params) {
            pp_overworld_step(global.pp.world);
        },
        draw: function(_params) {
            pp_overworld_draw(global.pp.world);
        }
    };
}
