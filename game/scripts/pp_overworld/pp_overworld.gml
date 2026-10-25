/// pp_overworld: the walker, the triggers, the markers and the scene that plays over the map (spec 04).
/// One tile per press, always centred; rail walk at 8 steps per tile, free walk at 12; triggers inert for 20 steps after
/// a scene or battle; story blocked tiles open with a flag. Nothing here reads a key directly, only pp_input.
/// Saving is here in two shapes (spec 11 rule 4): every map entry arms one silent autosave, which pp_overworld_step
/// releases once the fade is done and no scene owns the screen, and a trigger of kind `save` writes at a save point
/// the player confirms, printing the ship's log line that names the point.
/// Provenance: knowledge\PROVENANCE.md, entry "room and object conventions across a whole game", written before the
/// notice of 2026-10-19 and re-confirmed by the clean-room re-review of the same date. One map state carries the
/// walker, the scene and the fade; a battle is a mode swap asked for here and performed by pp_app (specs 01 and 04).

/// A fresh overworld on a map and spawn point.
function pp_overworld_new(_map_id, _spawn_name) {
    var _map = pp_map_load(_map_id);
    if (is_undefined(_map)) return undefined;
    var _spawn = pp_map_spawn_point(_map, _spawn_name);

    var _world = {
        map: _map,
        hero: pp_overworld_hero(_spawn.x, _spawn.y),
        actors: {},
        scene: undefined,
        dialogue: undefined,
        trigger_lock: PP_TRIGGER_LOCK_STEPS,
        marker_off: {},
        cam_x: 0,
        cam_y: 0,
        camera_follow: true,
        cam_pan: undefined,
        fade: undefined,
        // The world's own frame clock, counted by pp_overworld_step and handed to pp_map_draw, which reads it for the
        // animated tiles. It is declared here because the first draw of any overworld reads it: a missing key ends the
        // game on the first frame (card FIRST-FIGHT-WIRE, measured in build/first_fight_game.log at pp_overworld_draw 478).
        steps: 0,
        shake_steps: 0,
        shake_strength: 0,
        // The whole screen flash a scene's `flash` command asks for (card t_531bc76c): frames left to draw and the
        // role the frame is flooded with. Declared here for the same reason `steps` is: the first draw of any overworld
        // reads its keys, and a missing one ends the game on that frame.
        flash_steps: 0,
        flash_role: "paper",
        music: "",
        sfx: "",
        battle_request: "",
        battle_done: "",
        spawn_name: _spawn_name,
        map_changes: 0
    };
    pp_overworld_camera_follow(_world);

    // Spec 11 rule 4: entering a map saves once, silently, after the fade in. The arm carries the map the player
    // actually stands on; pp_save_autosave_step waits for the fade, and for any scene that opens here to finish.
    pp_save_autosave_arm(_map.id);

    // Story actors placed by the map data (card ASSEMBLE). One sailor on the lower deck is the first of them.
    // They are read from the map, never hardcoded here, so a new NPC is a data edit and not a code edit.
    if (is_array(_map.actors)) {
        for (var _i = 0; _i < array_length(_map.actors); _i += 1) {
            var _a = _map.actors[_i];
            _world.actors[$ string(_a.id)] = {
                name: _a.id,
                kind: _a.kind,
                dialogue: _a.dialogue,
                facing: _a.facing,
                tx: _a.x,
                ty: _a.y,
                px: _a.x * PP_TILE,
                py: _a.y * PP_TILE,
                walk: 0
            };
        }
    }
    return _world;
}

function pp_overworld_hero(_tx, _ty) {
    return {
        tx: _tx,
        ty: _ty,
        px: _tx * PP_TILE,
        py: _ty * PP_TILE,
        facing: "down",
        moving: false,
        from_x: _tx * PP_TILE,
        from_y: _ty * PP_TILE,
        to_x: _tx * PP_TILE,
        to_y: _ty * PP_TILE,
        steps: 0,
        total: 1
    };
}

/// Direction name to a unit vector. An unknown name is a stop, not a guess.
function pp_world_dir_vector(_dir) {
    switch (_dir) {
        case "up":    return { x: 0, y: -1 };
        case "down":  return { x: 0, y: 1 };
        case "left":  return { x: -1, y: 0 };
        case "right": return { x: 1, y: 0 };
    }
    show_debug_message("PP: unknown direction " + string(_dir));
    return { x: 0, y: 0 };
}

/// Start a scripted or free move to a tile. A blocked tile stops the move where it is, and says so once.
function pp_world_start_move(_world, _tx, _ty, _steps_per_tile) {
    var _hero = _world.hero;
    if (_hero.moving) return false;
    var _sx = sign(_tx - _hero.tx);
    var _sy = sign(_ty - _hero.ty);
    if (_tx != _hero.tx && _ty != _hero.ty) {
        show_debug_message("PP: no diagonal moves");
        return false;
    }
    // Every tile on the way must be walkable, so a rail cannot end inside a wall.
    var _cx = _hero.tx;
    var _cy = _hero.ty;
    var _guard = 0;
    while ((_cx != _tx || _cy != _ty) && _guard < 128) {
        _cx += _sx;
        _cy += _sy;
        if (!pp_map_walkable(_world.map, _cx, _cy)) {
            show_debug_message("PP: blocked move to " + string(_tx) + "," + string(_ty));
            return false;
        }
        _guard += 1;
    }
    _hero.moving = true;
    // Card SFX-WIRE: a tile move shows two walk frames, so one footstep per move is one every second frame.
    pp_audio_play("footstep");
    _hero.from_x = _hero.px;
    _hero.from_y = _hero.py;
    _hero.to_x = _tx * PP_TILE;
    _hero.to_y = _ty * PP_TILE;
    _hero.tx = _tx;
    _hero.ty = _ty;
    _hero.steps = 0;
    var _dist = abs(_tx * PP_TILE - _hero.from_x) + abs(_ty * PP_TILE - _hero.from_y);
    _hero.total = max(1, (_dist / PP_TILE) * _steps_per_tile);
    return true;
}

/// One step of the current move; the walker stays whole pixel and finishes the tile.
function pp_world_move_step(_world) {
    var _hero = _world.hero;
    if (!_hero.moving) return;
    _hero.steps += 1;
    var _t = _hero.steps / _hero.total;
    if (_t >= 1) {
        _hero.px = _hero.to_x;
        _hero.py = _hero.to_y;
        _hero.moving = false;
        _hero.steps = _hero.total;
        // Card SFX-WIRE: a hatch is a tile, not a trigger, so the sound fires when the hero lands on one.
        var _kind = pp_map_tile_kind(_world.map, _hero.tx, _hero.ty);
        if (string_pos("hatch", _kind) > 0) pp_audio_play("door_hatch");
        return;
    }
    _hero.px = floor(lerp(_hero.from_x, _hero.to_x, _t));
    _hero.py = floor(lerp(_hero.from_y, _hero.to_y, _t));
}

/// Ask for a whole screen flash (card t_531bc76c): N frames of the frame flooded in one role the room's palette set
/// declares. It spends no steps of the scene, because the world's own clock counts it down in pp_overworld_step; a
/// step count of zero or less asks for nothing rather than for a flash nobody can see.
function pp_world_flash(_world, _steps, _role) {
    if (!is_struct(_world)) return false;
    var _frames = round(_steps);
    if (_frames <= 0) return false;
    _world.flash_steps = min(_frames, PP_FLASH_MAX_STEPS);
    if (is_string(_role) && _role != "") _world.flash_role = _role;
    return true;
}

function pp_world_spawn_actor(_world, _name, _tx, _ty) {
    _world.actors[$ string(_name)] = { name: _name, tx: _tx, ty: _ty, px: _tx * PP_TILE, py: _ty * PP_TILE };
}

function pp_world_destroy_actor(_world, _name) {
    if (variable_struct_exists(_world.actors, string(_name))) {
        variable_struct_remove(_world.actors, string(_name));
    }
}

/// Follow the hero, clamped so the view never shows outside the map.
function pp_overworld_camera_follow(_world) {
    var _map = _world.map;
    var _full = pp_map_pixel_size(_map);
    _world.cam_x = clamp(_world.hero.px + PP_TILE * 0.5 - PP_FRAME_W * 0.5, 0, max(0, _full.w - PP_FRAME_W));
    _world.cam_y = clamp(_world.hero.py + PP_TILE * 0.5 - PP_FRAME_H * 0.5, 0, max(0, _full.h - PP_FRAME_H));
}

/// Start a scene over the current map.
function pp_overworld_start_scene(_world, _scene_id) {
    _world.scene = pp_scene_new(_scene_id, _world);
    return _world.scene;
}

/// Start an encounter: the app owns the mode swap, the world only asks.
function pp_overworld_start_encounter(_world, _encounter_id) {
    if (_world.battle_request != "") return false;
    _world.battle_request = _encounter_id;
    // The proof line FIRST-FIGHT-WIRE asks for: one unconditional line naming the encounter, the map and the tile the
    // hero stood on when the trigger fired, so a run that reached the fight and a run that never did can be told apart
    // from the log alone. It is deliberately not behind PP_DEBUG, because the release build is where that proof is wanted.
    show_debug_message("PP: battle start " + string(_encounter_id) + " on " + string(_world.map.id)
        + " " + string(_world.hero.tx) + "," + string(_world.hero.ty));
    return true;
}

/// Called by the battle mode when it hands control back. `_handoff_scene` is the scene id the fight handed over, or ""
/// when it handed nothing over; a caller that passes three arguments passes none.
///
/// Card t_905a18ce (F2): an interrupted fight names a scene, and spec 18 section 4 step 4 says the caller continues
/// with no press, so the scene is started HERE, through the one scene door, in the same call that takes the outcome.
/// That is what makes the caller the owner of the handover instead of the fight: the battle mode clears the battle and
/// hands two values over, and this door is the only place a world's scene is replaced. The scene launched path is the
/// same door, so a scene that ran a fight gets the interruption scene in place of the runner that waited for it, which
/// is what spec 18 section 4 step 6 asks for: the fight is not resumed, and control returns to the map when the
/// interruption scene ends. Kill and spare hand nothing over, so `battle_done` still carries the word a waiting scene
/// advances on (pp_scene's `battle` state).
function pp_overworld_battle_finished(_world, _encounter_id, _outcome, _handoff_scene) {
    if (is_undefined(_world)) return;
    var _enc = pp_data_find(global.pp_data.encounters.encounters, _encounter_id);
    if (!is_undefined(_enc)) {
        var _flags = [];
        if (_outcome == "spare" && variable_struct_exists(_enc, "flags_on_spare")) _flags = _enc.flags_on_spare;
        if (_outcome == "kill" && variable_struct_exists(_enc, "flags_on_kill")) _flags = _enc.flags_on_kill;
        var _i = 0;
        while (_i < array_length(_flags)) {
            pp_ledger_set_flag(global.pp_ledger, _flags[_i], true);
            _i += 1;
        }
    }
    _world.trigger_lock = PP_TRIGGER_LOCK_STEPS;

    if (!is_string(_handoff_scene) || _handoff_scene == "") {
        _world.battle_done = _outcome;
        return;
    }

    // battle_done stays empty: the outcome travelled as the scene id, and a scene still waiting on a fight must not
    // read this handover as its own result and step past the story that was just started over it.
    _world.battle_done = "";
    pp_overworld_start_scene(_world, _handoff_scene);
    // One unconditional line, like the battle start line: a run that played the middle act and a run that never did
    // can be told apart from the log alone (the same reason FIRST-FIGHT-WIRE gives).
    show_debug_message("PP: fight handed over to scene " + string(_handoff_scene) + " with no press");
}

/// A once trigger is remembered in the ledger so a door stays open across a save and load (spec 04 rule 3).
function pp_overworld_trigger_seen(_world, _trigger) {
    return pp_ledger_flag(global.pp_ledger, pp_overworld_trigger_flag(_world, _trigger));
}

function pp_overworld_trigger_flag(_world, _trigger) {
    return "trig_" + string(_world.map.id) + "_" + string(_trigger.x) + "_" + string(_trigger.y);
}

/// Fire one trigger. Unknown kinds are reported and skipped rather than silently ignored.
function pp_overworld_fire(_world, _trigger) {
    if (is_undefined(_trigger)) return;
    if (_trigger.once && pp_overworld_trigger_seen(_world, _trigger)) return;
    if (_trigger.condition != "" && !pp_ledger_flag(global.pp_ledger, _trigger.condition)) return;

    switch (_trigger.kind) {
        case "say":
            if (!pp_dialogue_closed(_world.dialogue)) return;
            _world.dialogue = pp_dialogue_open(_trigger.id);
            break;

        case "battle":
            pp_overworld_start_encounter(_world, _trigger.id);
            break;

        case "scene":
            pp_overworld_start_scene(_world, _trigger.id);
            break;

        case "map":
            var _spawn = "start";
            if (variable_struct_exists(_trigger, "spawn")) _spawn = _trigger.spawn;
            // Card SFX-WIRE: a door between maps is a hatch in the story, so it gets the hatch sound.
            pp_audio_play("door_hatch");
            pp_overworld_change_map(_world, _trigger.id, _spawn);
            break;

        case "flag":
            pp_ledger_set_flag(global.pp_ledger, _trigger.id, true);
            break;

        // A save point (spec 11 rule 4). The row's id is a label for the player's sake, not a row in any table
        // (tools/check_data.py says so where it leaves "save" out of the id tables), so it names the point in the
        // logged line and travels no further. pp_save refuses everything but a settled overworld, so a save can
        // never land mid battle, mid scene or mid dialogue, and it says so in one line when it refuses.
        case "save":
            var _label = "save";
            if (is_string(_trigger.id) && _trigger.id != "") _label = _trigger.id;
            if (pp_save_write(_label, false)) {
                // The ship's log line. One line, and it names the point, the map and the tile, so a run that saved
                // and a run that never asked can be told apart from the log alone.
                show_debug_message("PP: ship's log, " + string(_label) + ", saved on " + string(_world.map.id)
                    + " " + string(_world.hero.tx) + "," + string(_world.hero.ty));
            }
            break;

        case "marker":
            pp_overworld_start_encounter(_world, _trigger.id);
            break;

        default:
            show_debug_message("PP: unknown trigger kind " + string(_trigger.kind));
            return;
    }

    if (_trigger.once) pp_ledger_set_flag(global.pp_ledger, pp_overworld_trigger_flag(_world, _trigger), true);
    _world.trigger_lock = PP_TRIGGER_LOCK_STEPS;
}

/// Swap maps behind the app's fade, so the walker never sees the swap.
function pp_overworld_change_map(_world, _map_id, _spawn_name) {
    var _map = pp_map_load(_map_id);
    if (is_undefined(_map)) return false;
    _world.map = _map;
    var _spawn = pp_map_spawn_point(_map, _spawn_name);
    _world.hero = pp_overworld_hero(_spawn.x, _spawn.y);
    _world.spawn_name = _spawn_name;
    _world.actors = {};
    _world.scene = undefined;
    _world.cam_pan = undefined;
    _world.camera_follow = true;
    _world.map_changes += 1;
    pp_overworld_camera_follow(_world);
    pp_app_fade_in();
    // The new map is an entry too (spec 11 rule 4), so it arms its own silent save. Like the first entry, the write
    // waits for the fade this call just started.
    pp_save_autosave_arm(_map.id);
    return true;
}

/// The trigger the hero would fire with confirm: the tile ahead first, then the tile underfoot.
function pp_overworld_confirm_target(_world) {
    var _d = pp_world_dir_vector(_world.hero.facing);
    var _ahead = pp_map_trigger_at(_world.map, _world.hero.tx + _d.x, _world.hero.ty + _d.y);
    if (!is_undefined(_ahead)) return _ahead;
    return pp_map_trigger_at(_world.map, _world.hero.tx, _world.hero.ty);
}

/// The actor standing on one tile, or undefined. Used for talk and for blocking a walk into somebody.
function pp_overworld_actor_at(_world, _tx, _ty) {
    var _names = variable_struct_get_names(_world.actors);
    for (var _i = 0; _i < array_length(_names); _i += 1) {
        var _a = _world.actors[$ _names[_i]];
        if (_a.tx == _tx && _a.ty == _ty) return _a;
    }
    return undefined;
}

/// The actor the hero is facing, or undefined. Talk is confirm on the tile ahead, so the same key that reads a
/// sign reads a sailor.
function pp_overworld_actor_ahead(_world) {
    var _d = pp_world_dir_vector(_world.hero.facing);
    return pp_overworld_actor_at(_world, _world.hero.tx + _d.x, _world.hero.ty + _d.y);
}

/// Step the overworld: clocks, scene, dialogue, walking, triggers.
function pp_overworld_step(_world) {
    if (is_undefined(_world)) return;

    // Clocks that run whether or not anything else does. The world clock climbs every step so the animated tiles keep
    // moving through a scene, a dialogue or a walk; pp_map_draw reads it on the same frame it is drawn.
    _world.steps += 1;
    if (_world.shake_steps > 0) _world.shake_steps -= 1;
    // The flash counts down here, at the top of the step, exactly as the shake does, so the frame that asked for it
    // draws it: N on the step it is set, N-1 on the next, and off when it reaches zero. A `flash` command spends no
    // steps of its own, so this is the only clock it has (card t_531bc76c, spec 06).
    if (_world.flash_steps > 0) _world.flash_steps -= 1;
    if (_world.trigger_lock > 0) _world.trigger_lock -= 1;

    // The entry autosave (spec 11 rule 4) is asked every step and fires exactly once per entry, on a settled screen.
    // It sits before the scene branch below, because that branch returns; the save itself refuses while a scene runs.
    pp_save_autosave_step(_world);

    // A scene owns the screen while it runs.
    if (pp_scene_running(_world.scene)) {
        pp_scene_step(_world.scene, _world);
        pp_world_move_step(_world);
        pp_overworld_clock_step(_world);

        // A scene command can ask for a fight, and the scene then waits for battle_done. The request has to be drained
        // here, inside the scene branch: the app is the only thing that swaps modes, and the older drain below is
        // unreachable while a scene runs, which would leave the scene waiting for a battle nobody starts.
        if (_world.battle_request != "") {
            var _scene_battle = _world.battle_request;
            _world.battle_request = "";
            pp_app_request(PPMode.battle, { encounter_id: _scene_battle, from_world: true });
            return;
        }

        if (!pp_scene_running(_world.scene)) {
            _world.scene = undefined;
            _world.trigger_lock = PP_TRIGGER_LOCK_STEPS;
        }
        return;
    }
    _world.scene = undefined;

    // A dialogue opened by a `say` trigger owns the screen too.
    if (!pp_dialogue_closed(_world.dialogue)) {
        if (pp_pressed("confirm")) pp_dialogue_advance(_world.dialogue);
        pp_dialogue_step(_world.dialogue);
        if (pp_dialogue_closed(_world.dialogue)) _world.dialogue = undefined;
        pp_overworld_clock_step(_world);
        return;
    }
    _world.dialogue = undefined;

    // Ask for the battle once per request; the app performs the swap.
    if (_world.battle_request != "") {
        var _id = _world.battle_request;
        _world.battle_request = "";
        pp_app_request(PPMode.battle, { encounter_id: _id, from_world: true });
        return;
    }

    // Copy the objective marker off for its respawn window (spec 04: gone for 30 steps).
    var _names = variable_struct_get_names(_world.marker_off);
    var _n = 0;
    while (_n < array_length(_names)) {
        var _key = _names[_n];
        var _left = _world.marker_off[$ _key] - 1;
        if (_left <= 0) {
            variable_struct_remove(_world.marker_off, _key);
        } else {
            _world.marker_off[$ _key] = _left;
        }
        _n += 1;
    }

    pp_world_move_step(_world);
    if (_world.hero.moving) {
        pp_overworld_clock_step(_world);
        return;
    }

    // A marker fires on touch, never on confirm.
    var _here = pp_map_trigger_at(_world.map, _world.hero.tx, _world.hero.ty);
    if (!is_undefined(_here) && _here.kind == "marker") {
        var _mkey = string(_here.x) + "_" + string(_here.y);
        if (!variable_struct_exists(_world.marker_off, _mkey)) {
            _world.marker_off[$ _mkey] = PP_MARKER_RESPAWN_STEPS;
            pp_overworld_fire(_world, _here);
            return;
        }
    }

    if (_world.trigger_lock <= 0 && pp_pressed("confirm")) {
        var _talk = pp_overworld_actor_ahead(_world);
        if (!is_undefined(_talk)) {
            // Card R30 (spec 19 section 2, Q5 and Q10): an actor whose id the bake carries a conversation for talks
            // from data/meta_bake.json, and any other actor keeps its authored dialogue id. One door, in
            // pp_talk_actor_open, so the map data decides who speaks and this branch decides nothing by name.
            _world.dialogue = pp_talk_actor_open(_talk, _world);
            if (is_undefined(_world.dialogue)) _world.dialogue = undefined;
            pp_overworld_clock_step(_world);
            return;
        }
        var _target = pp_overworld_confirm_target(_world);
        if (!is_undefined(_target) && _target.kind != "marker") {
            pp_overworld_fire(_world, _target);
            pp_overworld_clock_step(_world);
            return;
        }
    }

    // Free walk: one tile per press, four directions, facing updates instantly.
    var _dir = "";
    if (pp_pressed("left")) _dir = "left";
    else if (pp_pressed("right")) _dir = "right";
    else if (pp_pressed("up")) _dir = "up";
    else if (pp_pressed("down")) _dir = "down";

    if (_dir != "") {
        _world.hero.facing = _dir;
        var _d = pp_world_dir_vector(_dir);
        var _nx = _world.hero.tx + _d.x;
        var _ny = _world.hero.ty + _d.y;
        if (pp_map_walkable(_world.map, _nx, _ny) && is_undefined(pp_overworld_actor_at(_world, _nx, _ny))) {
            pp_world_start_move(_world, _nx, _ny, PP_WALK_STEPS_FREE);
        } else if (PP_DEBUG) {
            show_debug_message("PP: wall at " + string(_nx) + "," + string(_ny));
        }
    }

    pp_overworld_clock_step(_world);
}

/// The fade, the camera pan and the follow, which run under everything else.
function pp_overworld_clock_step(_world) {
    if (!is_undefined(_world.fade)) {
        var _f = _world.fade;
        _f.steps += 1;
        _f.alpha = clamp(_f.alpha + _f.dir * (1 / max(1, _f.total)), 0, 1);
        if (_f.steps >= _f.total) {
            _f.alpha = (_f.dir < 0) ? 0 : 1;
            _world.fade = undefined;
        }
    }

    if (!is_undefined(_world.cam_pan)) {
        var _p = _world.cam_pan;
        _p.steps += 1;
        var _t = min(1, _p.steps / max(1, _p.total));
        _world.cam_x = floor(lerp(_p.from_x, _p.to_x, _t));
        _world.cam_y = floor(lerp(_p.from_y, _p.to_y, _t));
        if (_p.steps >= _p.total) _world.cam_pan = undefined;
    } else if (_world.camera_follow) {
        pp_overworld_camera_follow(_world);
    }
}

/// Draw the map, the actors, the hero, the dialogue and the fade. Shake is whole pixels, 1 or 2, every 2 steps.
function pp_overworld_draw(_world) {
    if (is_undefined(_world)) return;

    var _ox = 0;
    var _oy = 0;
    if (_world.shake_steps > 0) {
        var _phase = floor(_world.shake_steps / PP_SHAKE_PERIOD) mod 2;
        _ox = _phase == 0 ? _world.shake_strength : -_world.shake_strength;
        _oy = _phase == 0 ? -_world.shake_strength : _world.shake_strength;
    }

    // The tile art, in the two planes the hero stands in front of: ground first, then the props that stand on it
    // (card R28). The above plane is drawn after him, below.
    pp_map_draw(_world.map, floor(_world.cam_x) + _ox, floor(_world.cam_y) + _oy, _world.steps);

    // Story actors and the hero, each a sheet frame when the art lane has delivered one and a shaped block
    // until then (card ASSEMBLE: SPRITE-1 was not on disk, so the block fallback is the live path and the
    // frame branch is what a delivered sheet switches on with no code change).
    pp_overworld_draw_actors(_world, _ox, _oy);

    // Encounter markers: a small silhouette, skipped while respawning.
    var _t = 0;
    while (_t < array_length(_world.map.triggers)) {
        var _tr = _world.map.triggers[_t];
        if (_tr.kind == "marker") {
            var _key = string(_tr.x) + "_" + string(_tr.y);
            if (!variable_struct_exists(_world.marker_off, _key)) {
                draw_set_colour(pp_role_colour("hazard"));
                draw_rectangle(_tr.x * PP_TILE - _world.cam_x + 4 + _ox, _tr.y * PP_TILE - _world.cam_y + 3 + _oy,
                               _tr.x * PP_TILE - _world.cam_x + 11 + _ox, _tr.y * PP_TILE - _world.cam_y + 15 + _oy, false);
            }
        }
        _t += 1;
    }

    // The hero, 12x12 in a 16x16 tile, centred, with the walk cycle.
    pp_overworld_draw_hero(_world, _ox, _oy);

    // The above plane of the tile art, over the hero and the actors: a lamp post, a harbour sign, the things a
    // walker passes behind (card R28). Drawn after him so the overlap is the layer order and not a coincidence.
    pp_map_draw_above(_world.map, floor(_world.cam_x) + _ox, floor(_world.cam_y) + _oy, _world.steps);

    if (!pp_dialogue_closed(_world.dialogue)) {
        pp_dialogue_draw(_world.dialogue);
        // Card R30 (spec 19 section 5, Q9): the hint is the row under the box's text, in the second ink, inside the
        // window's own 64 pixels. A box the bake did not open carries no hints and draws nothing here.
        var _hint = pp_talk_npc_hint(_world.dialogue);
        if (_hint != "") {
            // Card BATTLE-FONT-WIRE: the sheet's glyphs, wrapped to the box's 224 px inside, on the row under the
            // dialogue rows. Where it sits is what marks it out, not a second ink the sheet does not have (rule 6).
            pp_font_draw_wrapped(_hint, PP_TEXT_X, PP_BOX_Y + PP_BOX_H - 22,
                pp_font_cols(PP_TEXT_RIGHT - PP_TEXT_X), 8, 1);
        }
        draw_set_halign(fa_left);
    }

    // A flash is the whole frame flooded in one role the room's own palette set declares (card t_531bc76c): a palette
    // change, never a blend, so the screen still spends one declared colour and spec 13's no-gradients rule holds.
    // Drawn over the map, the actors and the box, and under the fade, because a fade is the darker statement of intent.
    if (_world.flash_steps > 0) {
        draw_set_alpha(1);
        draw_set_colour(pp_role_colour(_world.flash_role));
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
    }

    if (!is_undefined(_world.fade)) {
        draw_set_alpha(_world.fade.alpha);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
    }

    // Card ASSEMBLE self check: with PP_SHIP_CAPTURE set in the environment, the room writes one PNG of its own frame
    // from inside the draw, so the room can be proven without a screen copy of whatever window sits on top of the game.
    // The 90th draw is 1.5 s in, past pp_app's 12 step fade in, so the file shows the room and not a black fade frame.
    // Unset, which is every real launch, this costs one environment read per frame and writes nothing.
    if (environment_get_variable(PP_SHIP_CAPTURE) != "") {
        if (!variable_global_exists("pp_ship_draws")) global.pp_ship_draws = 0;
        global.pp_ship_draws += 1;
        if (global.pp_ship_draws == 90) {
            screen_save("pp_ship_frame.png");
            show_debug_message("PP ship: wrote pp_ship_frame.png from the room itself at draw " + string(global.pp_ship_draws));
        }
        // The second file is five seconds in, after the harness has pressed Right eight times, so the pair proves the
        // walker moved and the camera followed it inside the room's own pixels.
        if (global.pp_ship_draws == 360) {
            screen_save("pp_ship_frame_2.png");
            show_debug_message("PP ship: wrote pp_ship_frame_2.png from the room itself at draw " + string(global.pp_ship_draws));
        }
        // The third file is after the harness has pressed confirm next to the sailor, so the dialogue box in the window
        // frame is in the room's own pixels rather than inferred from the code path.
        if (global.pp_ship_draws == 460) {
            screen_save("pp_ship_frame_3.png");
            show_debug_message("PP ship: wrote pp_ship_frame_3.png from the room itself at draw " + string(global.pp_ship_draws));
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The two overworld figures. Both ask the art index first: a delivered sheet is 4 directions by 3 frames
// (idle, walk a, walk b) in rows of 16x16, so the frame index is direction * 3 + step. With no sheet the
// same silhouette is drawn from blocks at the same size, which is the card's stated fallback and keeps the
// walk cycle, the facing and the dialogue reach working before any art lands.

#macro PP_HERO_SHEET "zander_ow_v2"
#macro PP_SAILOR_SHEET "sailor_ow_v2"

/// Row of a direction inside an overworld sheet. The sheet the character lane draws is 128x16, eight frames in
/// one row: down 0, down 1, up 0, up 1, right 0, right 1, left 0, left 1. So the direction order is down, up,
/// right, left, two frames each: frame 0 stands (idle) and frame 1 steps.
function pp_world_dir_row(_dir) {
    switch (_dir) {
        case "down":  return 0;
        case "up":    return 1;
        case "right": return 2;
        case "left":  return 3;
    }
    return 0;
}

/// The frame of one figure in its sheet: direction times frames per direction, plus the walk step. Frames per
/// direction is read off the sheet (eight frames over four directions is two), so a twelve frame sheet with three
/// frames per direction would animate without a code change. Idle is frame 0 of the direction; a move cycles.
function pp_world_sheet_frame(_name, _dir, _moving, _steps) {
    var _per = 2;
    var _info = pp_art_info(_name);
    if (!is_undefined(_info) && _info.frames > 0 && (_info.frames mod 4) == 0) _per = _info.frames div 4;
    var _step = 0;
    if (_moving && _per > 1) _step = floor(_steps / 4) mod _per;
    return pp_world_dir_row(_dir) * _per + _step;
}

/// The walk step of a figure: 0 standing, 1 and 2 while a move is under way. Two frames, 4 steps apart, so the
/// cycle reads at a walking pace without a separate clock.
function pp_world_walk_frame(_moving, _steps) {
    if (!_moving) return 0;
    return 1 + (floor(_steps / 4) mod 2);
}

function pp_overworld_draw_hero(_world, _ox, _oy) {
    var _hero = _world.hero;
    var _sx = _hero.px - _world.cam_x + _ox;
    var _sy = _hero.py - _world.cam_y + _oy;
    var _step = pp_world_walk_frame(_hero.moving, _hero.steps);
    var _frame = pp_world_sheet_frame(PP_HERO_SHEET, _hero.facing, _hero.moving, _hero.steps);
    if (pp_art_draw(PP_HERO_SHEET, _frame, _sx, _sy, PP_UNTINTED, 1)) return;

    // Blocks: blond head, light blue bomber, dark trousers. 12 wide, 14 tall inside the 16 pixel tile.
    var _bob = (_step == 0) ? 0 : 1;
    draw_set_colour(pp_role_colour("warn"));
    draw_rectangle(_sx + 5, _sy + 1 + _bob, _sx + 10, _sy + 5 + _bob, false);
    draw_set_colour(pp_role_colour("marker"));
    draw_rectangle(_sx + 4, _sy + 6 + _bob, _sx + 11, _sy + 11 + _bob, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(_sx + 4, _sy + 12, _sx + 5, _sy + 14, false);
    draw_rectangle(_sx + 10, _sy + 12, _sx + 11, _sy + 14, false);
    if (_hero.facing == "left" || _hero.facing == "right") {
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(_sx + (_hero.facing == "left" ? 5 : 9), _sy + 3 + _bob,
                       _sx + (_hero.facing == "left" ? 5 : 9), _sy + 3 + _bob, false);
    } else if (_hero.facing == "down") {
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(_sx + 6, _sy + 3 + _bob, _sx + 6, _sy + 3 + _bob, false);
        draw_rectangle(_sx + 9, _sy + 3 + _bob, _sx + 9, _sy + 3 + _bob, false);
    }
}

function pp_overworld_draw_actors(_world, _ox, _oy) {
    var _names = variable_struct_get_names(_world.actors);
    var _i = 0;
    while (_i < array_length(_names)) {
        var _a = _world.actors[$ _names[_i]];
        var _sx = _a.px - _world.cam_x + _ox;
        var _sy = _a.py - _world.cam_y + _oy;
        var _frame = pp_world_sheet_frame(PP_SAILOR_SHEET, _a.facing, false, 0);
        if (!pp_art_draw(PP_SAILOR_SHEET, _frame, _sx, _sy, PP_UNTINTED, 1)) {
            // Blocks: navy jacket with a white collar, cap, so a sailor does not read as the hero.
            draw_set_colour(pp_role_colour("dim"));
            draw_rectangle(_sx + 3, _sy + 2, _sx + 12, _sy + 6, false);
            draw_set_colour(pp_role_colour("paper"));
            draw_rectangle(_sx + 4, _sy + 7, _sx + 11, _sy + 8, false);
            draw_set_colour(pp_role_colour("dim"));
            draw_rectangle(_sx + 4, _sy + 9, _sx + 11, _sy + 15, false);
        }
        _i += 1;
    }
}
