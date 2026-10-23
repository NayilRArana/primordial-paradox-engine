/// pp_app: the application mode machine (spec 01). One persistent owner, one door for every swap, one fade.
/// A mode is a struct with enter, step and draw. A request names a mode and parameters; a missing mode fails loudly at
/// boot rather than mid scene. No other module sets the mode.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The structure is spec 01: a registry, a
/// single request door and one fade, with no phase number shared between modules.

// The demo's route (card R24). data\slice.json carries the ordered route the demo follows, and this file walks it. The
// kinds below are the seven a route row may name; a row naming anything else stops the walk where it stands.
enum PPSliceKind {
    title = 0,
    crawl = 1,
    scene = 2,
    map = 3,
    battle = 4,
    save = 5,
    branch = 6
}

// The environment variable the walk reads. It is split so the literal in the macro is not itself a use of the name, the
// same way pp_config writes the title and ship capture names. Unset in every real launch, the walk costs one
// environment read at boot and nothing per frame.
#macro PP_SLICE "PP_" + "SLICE"
// The log the walk writes beside the save, so a run that opened a window can be read afterwards without a console.
#macro PP_SLICE_LOG "pp_slice_run.log"
// A route is nine rows long and a branch may lead back to the title, so the walk stop after this many steps keeps a
// mistyped `to` from looping forever. It is a bound on a bad row, never on the demo.
#macro PP_SLICE_MAX_STEPS 64
// The quiet switch (card CAPTURE-QUIET, Nayil 2026-10-22). An automatic capture, a probe or a demo starts the game with
// PP_MUTE=1, and pp_app_mute_from_env below takes the master bus to 0 at boot, so a proof run is silent while a real
// player's launch is not. It lives here beside PP_SLICE rather than in pp_config because the only code that reads it is
// in this file, and it is split the same way so the macro's own definition is not a use of the name.
#macro PP_MUTE "PP_" + "MUTE"

/// The quiet switch (card CAPTURE-QUIET, Nayil 2026-10-22). An automatic capture, a probe or a scripted demo starts the
/// game with PP_MUTE=1 in its environment, and this takes the master bus to 0 before anything can ask for a sound, so a
/// run that opens a window for a proof is silent. audio_master_gain scales every sound the game makes (music, effects
/// and blips alike), so one call here is the whole change and no audio module has to know the variable exists. A real
/// player's launch leaves PP_MUTE unset and the game sounds exactly as built.
/// Returns true when this run is muted, which is also what the log line says, so a capture log answers "was it quiet".
function pp_app_mute_from_env() {
    if (environment_get_variable(PP_MUTE) != "1") return false;
    audio_master_gain(0);
    show_debug_message("PP: muted, PP_MUTE=1 in the environment, so the master gain is 0 for this run");
    return true;
}

/// Create the game frame, load data, register the modes that exist, and enter boot.
/// Called once from obj_pp_game's Create event.
function pp_app_boot() {
    // Card CAPTURE-QUIET: the mute is decided before anything can play, and before a mode is entered.
    pp_app_mute_from_env();
    global.pp = {
        data: undefined,
        input: undefined,
        camera: undefined,
        ledger: undefined,
        app: undefined
    };

    global.pp_input = pp_input_init();
    global.pp_data = pp_data_load();
    // The look is built before the camera and before any mode can draw, because it owns the frame and the palette set
    // that every draw call resolves a role through (spec 13).
    global.pp_look = pp_look_init();
    global.pp_camera = pp_camera_init();
    global.pp_ledger = pp_ledger_new();
    pp_save_init();

    var _app = {
        mode: -1,
        mode_params: {},
        modes: {},
        fade_alpha: 0,
        fade_dir: 0,
        fade_steps: 0,
        pending: undefined,
        last_outcome: "",
        // The demo walk (card R24): which route step is current, whether its handoff has been taken, whether its target
        // has been seen on screen, whether the fight that just ended was lost, and how many steps have been walked.
        slice_walk: false,
        slice_step: "",
        slice_taken: false,
        slice_seen: false,
        slice_lose: false,
        slice_walked: 0
    };
    global.pp.app = _app;

    pp_app_register(PPMode.boot, pp_mode_boot());
    pp_app_register(PPMode.title, pp_title_mode());
    pp_app_register(PPMode.overworld, pp_mode_overworld());
    pp_app_register(PPMode.battle, pp_mode_battle());

    // The title screen is the first thing the player sees. Since card W1 it owns a room: the frame sets the mode,
    // moves to rm_pp_title, and the room's own object enters the screen, so the screen is entered exactly once.
    // The screen object is not in the boot room, so nothing here runs the title before the room exists.
    // A data problem still lands on the boot card, which says it in words, and that card is drawn by this object.
    // Card R24: which screen is first is the slice route's first step now, not a room name written here.
    if (pp_data_ok()) {
        pp_slice_start();
    } else {
        pp_app_enter(PPMode.boot, {});
    }
    return _app;
}

/// Begin the run from data\slice.json (card R24). The route's first step names the screen the game opens on; when that
/// step is missing the fallback is rm_pp_title, which is exactly what this file did before the route existed. A run
/// whose environment names PP_SLICE walks the route from here; every other run simply opens on the first step.
function pp_slice_start() {
    var _row = pp_slice_route_row(pp_slice_route_first());
    var _kind = pp_slice_kind(_row);
    var _room = rm_pp_title;
    if (_kind == PPSliceKind.title && variable_struct_exists(_row, "room")) {
        var _named = asset_get_index(string(_row.room));
        if (_named >= 0) _room = _named;
    }

    if (pp_slice_walk_enabled()) {
        pp_slice_walk_start();
    }
    pp_app_enter_room(PPMode.title, {}, _room);
    return true;
}

/// Jump with no fade into a mode that owns its own room (card W1). The mode is set and the move to the room is asked
/// for here, and the room's own object is what enters, steps and draws the screen. That is why this door does not call
/// the mode's enter: one owner per frame, and one entry per screen.
function pp_app_enter_room(_mode, _params, _room) {
    var _app = global.pp.app;
    if (!variable_struct_exists(_app.modes, string(_mode))) {
        show_debug_message("PP: enter for unregistered mode " + string(_mode));
        return false;
    }
    _app.mode = _mode;
    _app.mode_params = _params;
    if (room != _room) room_goto(_room);
    pp_input_lock(PP_INPUT_LOCK_STEPS);
    return true;
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

    // Play time counts overworld and battle steps only (spec 11 numbers: never paused time, and the title is not play).
    if (_app.mode == PPMode.overworld || _app.mode == PPMode.battle) {
        if (is_struct(global.pp.save)) global.pp.save.ticks += 1;
    }
    pp_save_panel_step();

    var _mode = _app.modes[$ string(_app.mode)];
    if (!is_undefined(_mode) && variable_struct_exists(_mode, "step")) {
        _mode.step(_app.mode_params);
    }

    // Card R24: the demo walk, one route step at a time. Dead unless the environment names PP_SLICE, so a real launch
    // still goes wherever the player takes it.
    pp_slice_walk_step();

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
    // The save panel sits over the mode and under the fade, so a save never flashes through a transition (spec 11).
    pp_save_draw_panel();
    if (_app.fade_alpha > 0) {
        draw_set_alpha(_app.fade_alpha);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
    }
}

function pp_app_mode() {
    return global.pp.app.mode;
}

// ---------------------------------------------------------------------------------------------------------------
// Mode: boot. The title card, the save line and any data problem in plain words. A save that read back cleanly
// continues with Z and starts a new run with X; with no save the slice starts on its own timer, as it always has.

function pp_mode_boot() {
    return {
        enter: function(_params) {
            global.pp.app.boot_steps = 0;
            global.pp.app.boot_message = "";
            if (is_struct(_params) && variable_struct_exists(_params, "message")) {
                global.pp.app.boot_message = _params.message;
            }
            // The slot is asked once, when the title appears (spec 11 goal: the title says where the player is). It is
            // only asked when the data loaded, because validation needs the map, item, power and flag lists.
            if (pp_data_ok()) pp_save_title_start();
        },
        step: function(_params) {
            var _app = global.pp.app;
            _app.boot_steps += 1;
            if (!pp_data_ok()) return;

            // A mode swap is under way: the title is leaving, so it must not start a second run on the way out.
            if (_app.fade_dir != 0 || !is_undefined(_app.pending)) return;

            // Nothing is decided until the asynchronous read answers.
            if (pp_save_busy()) return;
            if (pp_save_ready()) {
                if (pp_pressed("confirm")) {
                    pp_save_apply();
                    return;
                }
                if (pp_pressed("cancel")) {
                    pp_audio_play("menu_cancel");
                    pp_save_new_game();
                    return;
                }
                return;
            }

            // No usable save. The slice still starts by itself, except after a refused file: that one waits for the
            // player to read the sentence and press a key (spec 11 rule 3, acceptance 3).
            var _refused = (global.pp.save.state == PPSaveState.failed);
            if (pp_pressed("confirm") || (!_refused && _app.boot_steps > 60)) pp_save_new_game();
        },
        draw: function(_params) {
            draw_set_colour(pp_role_colour("paper"));
            draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
            // Card BATTLE-FONT-WIRE: every word on this card goes through pp_font, the game's one text path. The boot
            // card, the data error sentence and the battle outcome used the GameMaker default font because no font
            // resource exists; they print the 8x8 sheet now. A sentence that does not fit is word wrapped at a column
            // count, which is what the 8 pixel cell makes of the old draw_text_ext width of PP_FRAME_W - 32: the row
            // is 28 characters, x 16 to x 240, and 10 px between rows as before.
            var _cols = pp_font_cols(PP_FRAME_W - 32);
            pp_font_draw_centre("PRIMORDIAL PARADOX", PP_FRAME_W * 0.5, 84, 1);

            if (!pp_data_ok()) {
                pp_font_draw_wrapped(pp_data_error_text(), 16, 112, _cols, 10, 1);
            } else {
                var _save_line = pp_save_status_line();
                var _note = pp_save_title_note();
                if (_save_line != "") {
                    pp_font_draw_wrapped(_save_line, 16, 116, _cols, 10, 1);
                }
                if (_note != "") {
                    pp_font_draw_wrapped(_note, 16, 134, _cols, 10, 1);
                }
                if (pp_save_ready()) {
                    pp_font_draw("Z continue     X new game", 16, 160, 1);
                } else if (!pp_save_busy()) {
                    pp_font_draw("Z start", 16, 160, 1);
                }
                if (global.pp.app.boot_message != "") {
                    pp_font_draw_wrapped(global.pp.app.boot_message, 16, 178, _cols, 10, 1);
                }
            }

            if (PP_DEBUG) {
                pp_font_draw_wrapped("debug build  mode " + string(pp_app_mode()), 8, PP_FRAME_H - 16,
                    pp_font_cols(PP_FRAME_W - 16), 10, 1);
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
            // Card SFX-WIRE: the fight opens with the swoosh, whether or not the encounter data was found.
            pp_audio_play("encounter_swoosh");
        },
        step: function(_params) {
            var _battle = global.pp.battle;
            if (is_undefined(_battle)) return;

            if (pp_battle_finished(_battle)) {
                // Card t_905a18ce (F2): spec 18 section 4 step 4. A fight can hand its caller a scene id, and when it
                // does the caller continues with NO press. The id is taken from the fight before anything is cleared,
                // because the row it comes from belongs to the battle object below. A fight that hands nothing over
                // keeps the old confirm door, so a kill and a spare still end on the player's own press.
                var _handoff = pp_battle_handoff_scene(_battle);
                if (pp_pressed("confirm") || _handoff != "") {
                    // The ledger was written inside the battle; the overworld only takes the result and the flags.
                    // Defeat returns to the overworld with the party restored, which is the decision recorded as C7 in
                    // knowledge\SPEC-DELTAS.md, because the title and save modes that spec 01 rule 6 names do not exist.
                    var _outcome = pp_battle_outcome(_battle);
                    var _enc_id = global.pp.battle_encounter;
                    global.pp.battle = undefined;
                    pp_overworld_battle_finished(global.pp.world, _enc_id, _outcome, _handoff);
                    pp_app_request(PPMode.overworld, { resumed: true });
                }
                return;
            }
            pp_battle_step(_battle);
        },
        draw: function(_params) {
            var _battle = global.pp.battle;
            if (is_undefined(_battle)) {
                draw_set_colour(pp_role_colour("ink"));
                draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
                return;
            }
            pp_battle_draw(_battle);

            // Card t_905a18ce (F2): a fight that hands a scene over is never waited on, so it never shows the "press Z"
            // panel either. The prompt and the outcome word are the old door for a kill and a spare, which still end
            // on the player's own press.
            if (pp_battle_finished(_battle) && pp_battle_handoff_scene(_battle) == "") {
                draw_set_colour(pp_role_colour("paper"));
                draw_rectangle(40, 100, PP_FRAME_W - 40, 140, false);
                // Card BATTLE-FONT-WIRE: the outcome word and the prompt are the sheet's glyphs, centred and word
                // wrapped to the panel's own 176 px inside (40 to 216), which is 22 characters.
                var _outcome_cols = pp_font_cols(PP_FRAME_W - 80);
                pp_font_draw_wrapped_centre(pp_battle_outcome(_battle), PP_FRAME_W * 0.5, 112, _outcome_cols, 10, 1);
                pp_font_draw_centre("press Z", PP_FRAME_W * 0.5, 126, 1);
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

// ---------------------------------------------------------------------------------------------------------------
// The demo's route (card R24). data/slice.json carries one row per step: the id of the step, the kind of handoff it
// names, the scene, map, encounter or room id that handoff goes to, and the id of the step it hands to next. The route
// is read once, indexed by id, and walked by id, never by array position. That is what makes a row that is missing
// from the file a stop at the step before it instead of a crash: the step before names an id nobody has.

/// The slice route, read once from data/slice.json and indexed by step id. undefined when the file carries no route,
/// which is the state a build with the old five key slice.json is in.
function pp_slice_route() {
    if (variable_global_exists("pp_slice_route_cache")) return global.pp_slice_route_cache;

    var _route = undefined;
    if (is_struct(global.pp_data) && is_struct(global.pp_data.slice)
        && variable_struct_exists(global.pp_data.slice, "route")) {
        var _raw = global.pp_data.slice.route;
        if (is_struct(_raw) && is_array(_raw.steps)) {
            var _by_id = {};
            var _i = 0;
            while (_i < array_length(_raw.steps)) {
                var _row = _raw.steps[_i];
                if (is_struct(_row) && variable_struct_exists(_row, "id")) _by_id[$ string(_row.id)] = _row;
                _i += 1;
            }
            _route = {
                first: (variable_struct_exists(_raw, "first") ? string(_raw.first) : ""),
                steps: _raw.steps,
                by_id: _by_id
            };
        }
    }
    global.pp_slice_route_cache = _route;
    return _route;
}

/// The id of the route's first step, or "" when there is no route.
function pp_slice_route_first() {
    var _route = pp_slice_route();
    if (is_undefined(_route)) return "";
    return _route.first;
}

/// One route row by id, or undefined when the route has no such step. This is the only lookup the walk uses.
function pp_slice_route_row(_id) {
    var _route = pp_slice_route();
    if (is_undefined(_route) || string(_id) == "") return undefined;
    if (!variable_struct_exists(_route.by_id, string(_id))) return undefined;
    return _route.by_id[$ string(_id)];
}

/// How many steps the route has, for the printed line.
function pp_slice_route_count() {
    var _route = pp_slice_route();
    if (is_undefined(_route)) return 0;
    return array_length(_route.steps);
}

/// The one based position of a step in the authored order, for the printed line. 0 when the id is not in the route.
function pp_slice_route_index(_id) {
    var _route = pp_slice_route();
    if (is_undefined(_route)) return 0;
    var _i = 0;
    while (_i < array_length(_route.steps)) {
        var _row = _route.steps[_i];
        if (is_struct(_row) && variable_struct_exists(_row, "id") && string(_row.id) == string(_id)) return _i + 1;
        _i += 1;
    }
    return 0;
}

/// The kind enum a row names, or undefined when the word is not one of the seven. A row with an unknown kind is a stop
/// in the walk, and the stop line says which word it read.
function pp_slice_kind(_row) {
    if (!is_struct(_row) || !variable_struct_exists(_row, "kind")) return undefined;
    switch (string(_row.kind)) {
        case "title": return PPSliceKind.title;
        case "crawl": return PPSliceKind.crawl;
        case "scene": return PPSliceKind.scene;
        case "map": return PPSliceKind.map;
        case "battle": return PPSliceKind.battle;
        case "save": return PPSliceKind.save;
        case "branch": return PPSliceKind.branch;
    }
    return undefined;
}

/// A row's own label, or its id when the row carries no label. Labels are words for the printed line and nothing else.
function pp_slice_label(_row) {
    if (is_struct(_row) && variable_struct_exists(_row, "label")) return string(_row.label);
    if (is_struct(_row) && variable_struct_exists(_row, "id")) return string(_row.id);
    return "?";
}

/// Does one file of data make it into the build? The crawl is pp_title's own phase and reads data/intro_text.json
/// directly, so a route step that names it is checked this way and not through a loaded bundle.
function pp_slice_file_exists(_name) {
    var _paths = pp_data_paths(_name);
    var _i = 0;
    while (_i < array_length(_paths)) {
        if (file_exists(_paths[_i])) return true;
        _i += 1;
    }
    return false;
}

/// The spawn a map or scene step hands to: the row's own spawn when the map has it, otherwise the map's "start",
/// otherwise its first spawn alphabetically, the same order the scene self test uses. Nothing invents a spawn name.
function pp_slice_spawn(_map_id, _row) {
    var _named = "";
    if (is_struct(_row) && variable_struct_exists(_row, "spawn")) _named = string(_row.spawn);
    var _map_row = pp_data_find(global.pp_data.maps.maps, _map_id);
    if (is_undefined(_map_row) || !variable_struct_exists(_map_row, "spawns")) {
        return ((_named != "") ? _named : "start");
    }
    var _spawns = _map_row.spawns;
    if (_named != "" && variable_struct_exists(_spawns, _named)) return _named;
    if (variable_struct_exists(_spawns, "start")) return "start";
    var _names = variable_struct_get_names(_spawns);
    if (array_length(_names) == 0) return "start";
    var _first = _names[0];
    var _i = 1;
    while (_i < array_length(_names)) {
        if (_names[_i] < _first) _first = _names[_i];
        _i += 1;
    }
    return _first;
}

/// The line that says what one step hands to. It is printed once per step, before the handoff is taken.
function pp_slice_handoff_text(_row) {
    switch (pp_slice_kind(_row)) {
        case PPSliceKind.title: return "enter the room " + string(_row.room);
        case PPSliceKind.crawl: return "the crawl plays inside the title screen from " + string(_row.text);
        case PPSliceKind.scene: return "enter the scene " + string(_row.scene);
        case PPSliceKind.map: return "enter the map " + string(_row.map);
        case PPSliceKind.battle: return "enter the fight " + string(_row.encounter);
        case PPSliceKind.save: return "the ship's log writes the save here";
        case PPSliceKind.branch: return "hand back to the step " + string(_row.to);
    }
    return "kind " + string(_row.kind);
}

/// Take one step's handoff. Returns "" when it was taken, otherwise the reason it was not, which the walk prints
/// before it stops. Every reason names the id it could not find and the data file it looked in.
function pp_slice_handoff(_row) {
    var _kind = pp_slice_kind(_row);
    if (is_undefined(_kind)) return "the kind " + string(_row.kind) + " is not one of the seven step kinds";

    switch (_kind) {
        case PPSliceKind.title:
            if (pp_app_mode() == PPMode.title) return "";
            if (!variable_struct_exists(_row, "room")) return "the row names no room";
            var _room = asset_get_index(string(_row.room));
            if (_room < 0) return "the room " + string(_row.room) + " is not in the project";
            if (!pp_app_enter_room(PPMode.title, {}, _room)) return "the title mode is not registered";
            return "";

        case PPSliceKind.crawl:
            // The crawl is a phase of the title screen and not a mode of its own: pp_title plays it from
            // data/intro_text.json before the run starts. The step exists so the route says when the crawl is.
            var _text = (variable_struct_exists(_row, "text") ? string(_row.text) : "intro_text");
            if (!pp_slice_file_exists(_text + ".json")) return "data/" + _text + ".json is not in the build";
            return "";

        case PPSliceKind.scene:
            if (!variable_struct_exists(_row, "scene")) return "the row names no scene";
            var _scene_id = string(_row.scene);
            var _scene_row = pp_data_find(global.pp_data.scenes.scenes, _scene_id);
            if (is_undefined(_scene_row)) return "the scene " + _scene_id + " is not in data/scenes/all.json";
            var _scene_map = (variable_struct_exists(_scene_row, "map") ? string(_scene_row.map) : "");
            if (is_undefined(pp_data_find(global.pp_data.maps.maps, _scene_map))) {
                return "the scene " + _scene_id + " names the map " + _scene_map + ", which is not in data/maps/all.json";
            }
            // The overworld's own enter creates the world and starts the scene named in the request, which is the
            // handoff card R23 left in place: a scene loads its own map and start tile and nothing here duplicates it.
            pp_app_request(PPMode.overworld, { map_id: _scene_map, spawn: pp_slice_spawn(_scene_map, _row), scene: _scene_id });
            return "";

        case PPSliceKind.map:
            if (!variable_struct_exists(_row, "map")) return "the row names no map";
            var _map_id = string(_row.map);
            if (is_undefined(pp_data_find(global.pp_data.maps.maps, _map_id))) {
                return "the map " + _map_id + " is not in data/maps/all.json";
            }
            pp_app_request(PPMode.overworld, { map_id: _map_id, spawn: pp_slice_spawn(_map_id, _row), scene: "" });
            return "";

        case PPSliceKind.battle:
            if (!variable_struct_exists(_row, "encounter")) return "the row names no encounter";
            var _enc_id = string(_row.encounter);
            if (is_undefined(pp_data_find(global.pp_data.encounters.encounters, _enc_id))) {
                return "the encounter " + _enc_id + " is not in data/encounters/all.json";
            }
            pp_app_request(PPMode.battle, { encounter_id: _enc_id, from_world: true });
            return "";

        case PPSliceKind.save:
            // The writer is card R26's (autosave on entry plus the log terminal). The route's job is to say where the
            // save sits in the demo, so nothing is handed to a mode here and the walk reads the step as taken.
            return "";

        case PPSliceKind.branch:
            return "";
    }
    return "the kind " + string(_row.kind) + " is not one of the seven step kinds";
}

/// Is the step's target up yet? The walk prints a step's line, takes its handoff, and then waits here, so a handoff
/// that fades in over twelve steps is never mistaken for a step that has already happened.
function pp_slice_on_screen(_row) {
    switch (pp_slice_kind(_row)) {
        case PPSliceKind.title:
            return (pp_app_mode() == PPMode.title);

        case PPSliceKind.crawl:
            // The crawl lives inside the title screen, so it is on screen whenever the title screen is, and it has
            // already happened when the title has been left. Either way this step is never a wait of its own.
            return true;

        case PPSliceKind.scene:
            if (pp_app_mode() != PPMode.overworld) return false;
            if (!is_struct(global.pp.world) || !is_struct(global.pp.world.scene)) return false;
            return (string(global.pp.world.scene.id) == string(_row.scene));

        case PPSliceKind.map:
            if (pp_app_mode() != PPMode.overworld) return false;
            if (!is_struct(global.pp.world) || !is_struct(global.pp.world.map)) return false;
            return (string(global.pp.world.map.id) == string(_row.map));

        case PPSliceKind.battle:
            return (pp_app_mode() == PPMode.battle && is_struct(global.pp.battle));

        case PPSliceKind.save:
        case PPSliceKind.branch:
            return true;
    }
    return false;
}

/// Is the step over? Called only once its target has been on screen.
function pp_slice_done(_row) {
    switch (pp_slice_kind(_row)) {
        case PPSliceKind.title:
            // The title screen is up, so the route hands straight to the crawl, which is what plays on it next.
            return true;

        case PPSliceKind.crawl:
            // The crawl is done when the player leaves the title screen, which is the moment the run starts.
            return (pp_app_mode() != PPMode.title);

        case PPSliceKind.scene:
            if (pp_app_mode() != PPMode.overworld) return false;
            if (!is_struct(global.pp.world)) return false;
            return !pp_scene_running(global.pp.world.scene);

        case PPSliceKind.map:
            // The map is up and the walker has control. What happens on it is the next step's business.
            return true;

        case PPSliceKind.battle:
            // The fight owns the mode until its result is confirmed, and that confirm is what hands back to the map.
            return (pp_app_mode() != PPMode.battle);

        case PPSliceKind.save:
        case PPSliceKind.branch:
            return true;
    }
    return false;
}

/// The id a step hands to: a branch's `to` always, a lost fight's `lose` when the row has one, otherwise `next`.
function pp_slice_next_id(_row, _lost) {
    if (pp_slice_kind(_row) == PPSliceKind.branch) {
        return (variable_struct_exists(_row, "to") ? string(_row.to) : "");
    }
    if (_lost && variable_struct_exists(_row, "lose")) return string(_row.lose);
    return (variable_struct_exists(_row, "next") ? string(_row.next) : "");
}

/// Is the walk switched on? Unset in every real launch, so this is one environment read at boot and nothing per frame.
function pp_slice_walk_enabled() {
    return (environment_get_variable(PP_SLICE) != "");
}

/// Say one walk line twice: to the debug console, and to pp_slice_run.log beside the save, because a run started from
/// the run script has no console a person can read afterwards, so the log is what the check can be read from.
function pp_slice_note(_line) {
    show_debug_message(_line);
    var _f = file_text_open_append(PP_SLICE_LOG);
    if (_f < 0) return false;
    file_text_write_string(_f, _line);
    file_text_writeln(_f);
    file_text_close(_f);
    return true;
}

/// Empty the walk's log before the first line of a walk, so a second run answers for itself and not for the first.
function pp_slice_log_start() {
    var _f = file_text_open_write(PP_SLICE_LOG);
    if (_f < 0) return false;
    file_text_write_string(_f, "PP slice walk, PP_SLICE set");
    file_text_writeln(_f);
    file_text_close(_f);
    return true;
}

/// Put the walk at the route's first step. Called from pp_slice_start before the first screen is entered.
function pp_slice_walk_start() {
    var _app = global.pp.app;
    _app.slice_step = pp_slice_route_first();
    _app.slice_taken = false;
    _app.slice_seen = false;
    _app.slice_lose = false;
    _app.slice_walked = 0;
    _app.slice_walk = (_app.slice_step != "" && pp_slice_route_count() > 0);
    pp_slice_log_start();
    if (!_app.slice_walk) {
        pp_slice_note("PP slice: data/slice.json has no route, the walk is not started");
    }
    return _app.slice_walk;
}

/// Stop the walk where it stands and say why in one line. The reason always comes from the row the walk was on.
function pp_slice_walk_stop(_reason) {
    var _app = global.pp.app;
    var _row = pp_slice_route_row(_app.slice_step);
    pp_slice_note("PP slice: stopped at step " + string(pp_slice_route_index(_app.slice_step)) + " of "
                  + string(pp_slice_route_count()) + " " + string(_app.slice_step) + " ("
                  + pp_slice_label(_row) + "): " + string(_reason));
    _app.slice_walk = false;
    return false;
}

/// One step of the demo walk. It prints one line per route step, takes that step's handoff, watches until the target is
/// up, and moves to the step the row itself names. A row naming a step that is not in the file, or content that is not
/// in data, stops the walk where it stands with the reason printed, which is card R24's check for a removed step.
function pp_slice_walk_step() {
    var _app = global.pp.app;
    if (!_app.slice_walk) return false;

    var _row = pp_slice_route_row(_app.slice_step);
    if (is_undefined(_row)) {
        return pp_slice_walk_stop("the route has no step with this id");
    }
    if (_app.slice_walked >= PP_SLICE_MAX_STEPS) {
        return pp_slice_walk_stop("the walk passed its step bound, so a row leads in a circle");
    }

    // First frame on this step: say what it hands to, then take the handoff.
    if (!_app.slice_taken) {
        pp_slice_note("PP slice: step " + string(pp_slice_route_index(_app.slice_step)) + " of "
                      + string(pp_slice_route_count()) + " " + string(_row.id) + " ("
                      + pp_slice_label(_row) + "): " + pp_slice_handoff_text(_row));
        var _why = pp_slice_handoff(_row);
        if (_why != "") return pp_slice_walk_stop(_why);
        _app.slice_taken = true;
        _app.slice_seen = false;
        _app.slice_walked += 1;
        return true;
    }

    // Then watch. A fight that ends in a defeat is noted here, because the battle mode is the only thing that knows,
    // and the row's `lose` edge is what takes the demo to the game over screen instead of the next step.
    if (!_app.slice_seen) {
        if (pp_slice_on_screen(_row)) _app.slice_seen = true;
        if (pp_slice_kind(_row) == PPSliceKind.battle && is_struct(global.pp.battle)
            && pp_battle_finished(global.pp.battle) && pp_battle_outcome(global.pp.battle) == "defeat") {
            _app.slice_lose = true;
        }
        return true;
    }

    if (!pp_slice_done(_row)) return true;

    var _next = pp_slice_next_id(_row, _app.slice_lose);
    if (_next == "") {
        _app.slice_walk = false;
        pp_slice_note("PP slice: the route ends after step " + string(pp_slice_route_index(_app.slice_step))
                      + " of " + string(pp_slice_route_count()) + " " + string(_row.id) + ", "
                      + string(_app.slice_walked) + " steps walked");
        return true;
    }
    if (is_undefined(pp_slice_route_row(_next))) {
        return pp_slice_walk_stop("the step it hands to, " + string(_next) + ", is not in the route");
    }
    _app.slice_step = _next;
    _app.slice_taken = false;
    _app.slice_seen = false;
    _app.slice_lose = false;
    return true;
}
