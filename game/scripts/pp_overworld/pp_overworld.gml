/// pp_overworld: the walker, the triggers, the markers and the scene that plays over the map (spec 04).
/// One tile per press, always centred; rail walk at 8 steps per tile, free walk at 12; triggers inert for 20 steps after
/// a scene or battle; story blocked tiles open with a flag. Nothing here reads a key directly, only pp_input.
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
        shake_steps: 0,
        shake_strength: 0,
        music: "",
        sfx: "",
        battle_request: "",
        battle_done: "",
        spawn_name: _spawn_name,
        map_changes: 0
    };
    pp_overworld_camera_follow(_world);
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
        return;
    }
    _hero.px = floor(lerp(_hero.from_x, _hero.to_x, _t));
    _hero.py = floor(lerp(_hero.from_y, _hero.to_y, _t));
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
    return true;
}

/// Called by the battle mode when it hands control back.
function pp_overworld_battle_finished(_world, _encounter_id, _outcome) {
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
    _world.battle_done = _outcome;
    _world.trigger_lock = PP_TRIGGER_LOCK_STEPS;
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
            pp_overworld_change_map(_world, _trigger.id, _spawn);
            break;

        case "flag":
            pp_ledger_set_flag(global.pp_ledger, _trigger.id, true);
            break;

        // A save point (spec 11 rule 4). The data says where one is; pp_save refuses everything except the overworld,
        // so a save can never happen mid battle, mid scene or mid dialogue.
        case "save":
            pp_save_write("point");
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
    return true;
}

/// The trigger the hero would fire with confirm: the tile ahead first, then the tile underfoot.
function pp_overworld_confirm_target(_world) {
    var _d = pp_world_dir_vector(_world.hero.facing);
    var _ahead = pp_map_trigger_at(_world.map, _world.hero.tx + _d.x, _world.hero.ty + _d.y);
    if (!is_undefined(_ahead)) return _ahead;
    return pp_map_trigger_at(_world.map, _world.hero.tx, _world.hero.ty);
}

/// Step the overworld: clocks, scene, dialogue, walking, triggers.
function pp_overworld_step(_world) {
    if (is_undefined(_world)) return;

    // Clocks that run whether or not anything else does.
    if (_world.shake_steps > 0) _world.shake_steps -= 1;
    if (_world.trigger_lock > 0) _world.trigger_lock -= 1;

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
        if (pp_map_walkable(_world.map, _nx, _ny)) {
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

    pp_map_draw(_world.map, floor(_world.cam_x) + _ox, floor(_world.cam_y) + _oy);

    // Story actors, drawn as a plain block until sprites exist.
    var _names = variable_struct_get_names(_world.actors);
    var _i = 0;
    while (_i < array_length(_names)) {
        var _a = _world.actors[$ _names[_i]];
        draw_set_colour(pp_role_colour("accent"));
        draw_rectangle(_a.px - _world.cam_x + 2 + _ox, _a.py - _world.cam_y + 2 + _oy,
                       _a.px - _world.cam_x + 13 + _ox, _a.py - _world.cam_y + 15 + _oy, false);
        _i += 1;
    }

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

    // The hero, 12x12 in a 16x16 tile, centred.
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(_world.hero.px - _world.cam_x + 2 + _ox, _world.hero.py - _world.cam_y + 2 + _oy,
                   _world.hero.px - _world.cam_x + 13 + _ox, _world.hero.py - _world.cam_y + 15 + _oy, false);

    if (!pp_dialogue_closed(_world.dialogue)) pp_dialogue_draw(_world.dialogue);

    if (!is_undefined(_world.fade)) {
        draw_set_alpha(_world.fade.alpha);
        draw_set_colour(c_black);
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
    }
}
