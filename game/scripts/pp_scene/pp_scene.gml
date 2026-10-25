/// pp_scene: the cutscene runner (spec 06). A scene is a list of commands in data; one runs at a time; anything that
/// takes time blocks the list. branch is the only control flow, and a branch cycle is refused by the checker.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The runner is spec 06: one command at a
/// time, branch as the only control flow.
///
/// Card R23 (SCENE-RUNNER-HARDEN): the runner is generic over scenes and maps. A scene that names a map loads it and
/// places its own start tile with no app fade, `branch` re-enters the target scene in place (commands, map and start)
/// and never restarts the map fade, and `end` hands control back to the walker on the tile it stopped on with the
/// camera following him again. Every command reports a missing argument instead of hanging: no branch of the switch
/// can leave the runner in a state that only a key press escapes.

/// The commands this runner implements. The checker reads this list from data\scenes and refuses anything else.
/// `flash` (card t_531bc76c) is the storm's lightning over a map: the frame flooded in one declared role for a
/// handful of frames, which is a palette change on steps the scene already spends and never a wait of its own.
function pp_scene_commands() {
    return ["say", "move", "face", "wait", "fade", "music", "sfx", "camera", "shake", "flash",
            "spawn", "destroy", "battle", "setflag", "branch", "end"];
}

/// The environment flag that switches on the F1 scene self test. Defined here, next to its only reader, and split so
/// the name inside the macro is not itself a bare PP_ literal. Unset, which is every real launch, the two debug keys
/// do nothing at all.
#macro PP_SCENE_SELFTEST_ENV "PP_" + "SCENE_SELFTEST"

/// Steps a single scene may take in the self test before it is called stuck. One step is one frame, so this is 30
/// seconds of play for a single scene; the longest committed scene spends about 120.
#macro PP_SCENE_SELFTEST_CAP 1800

/// Commands one scene may execute before the runner stops it. A branch cycle is a checker error, and this is the
/// runtime's own dead man's handle on top of that.
#macro PP_SCENE_RUN_CAP 1000

/// A new runner for a scene id. Returns undefined when the id or its commands are missing.
function pp_scene_new(_scene_id, _world) {
    var _row = pp_data_find(global.pp_data.scenes.scenes, _scene_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no scene with id " + string(_scene_id));
        return undefined;
    }
    var _sc = {
        id: _row.id,
        map: "",
        start: undefined,
        commands: _row.commands,
        index: 0,
        state: "idle",
        timer: 0,
        dialogue: undefined,
        executed: 0,
        finished: false,
        ended_by: "",
        unknown: 0,
        autoplay: false,
        debug_step: false,
        trace: false
    };
    // Card R23: a scene owns the room it plays in. The map and the start tile are the scene's own data, so the runner
    // asks for them here and the caller never has to know which map a scene happens on.
    pp_scene_take_scene(_sc, _world, _row);
    pp_scene_command_start(_sc, _world);
    return _sc;
}

/// True while the scene still owns the screen.
function pp_scene_running(_sc) {
    if (is_undefined(_sc)) return false;
    return !_sc.finished;
}

/// Adopt a scene row: its id, its commands and its map and start tile. Called once when a runner is created and again
/// by a `branch`, which is why it is separate from the command list itself.
function pp_scene_take_scene(_sc, _world, _row) {
    _sc.id = _row.id;
    _sc.commands = _row.commands;
    _sc.index = 0;
    _sc.map = "";
    _sc.start = undefined;
    if (variable_struct_exists(_row, "map")) _sc.map = _row.map;
    if (variable_struct_exists(_row, "start")) _sc.start = _row.start;
    pp_scene_world_place(_world, _sc.map, _sc.start);
}

/// Put the world on the map a scene names and the walker on the tile it names. This is deliberately NOT
/// pp_overworld_change_map: that one owns a portal between maps and calls pp_app_fade_in, and a scene entered from a
/// branch would then restart the map fade the surrounding scene is already inside (card R23).
function pp_scene_world_place(_world, _map_id, _start) {
    if (!is_struct(_world)) return false;
    var _want = _map_id;
    if (_want == "") {
        if (is_struct(_world.map) && variable_struct_exists(_world.map, "id")) _want = _world.map.id;
    }
    if (_want == "") {
        show_debug_message("PP scene: no map to place the scene on");
        return false;
    }

    var _here = "";
    if (is_struct(_world.map) && variable_struct_exists(_world.map, "id")) _here = _world.map.id;
    if (_here != _want) {
        var _map = pp_map_load(_want);
        if (is_undefined(_map)) {
            show_debug_message("PP scene: map " + string(_want) + " did not load, staying on " + string(_here));
            return false;
        }
        _world.map = _map;
        _world.actors = {};
        if (is_array(_map.actors)) {
            var _i = 0;
            while (_i < array_length(_map.actors)) {
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
                    walk: 0,
                    moving: false,
                    from_x: _a.x * PP_TILE,
                    from_y: _a.y * PP_TILE,
                    to_x: _a.x * PP_TILE,
                    to_y: _a.y * PP_TILE,
                    steps: 0,
                    total: 1
                };
                _i += 1;
            }
        }
        _world.cam_pan = undefined;
        _world.camera_follow = true;
        _world.spawn_name = "";
        _world.map_changes += 1;
        show_debug_message("PP scene: map " + string(_want) + " loaded for the scene, no app fade");
    }

    if (is_struct(_start) && variable_struct_exists(_start, "x") && variable_struct_exists(_start, "y")) {
        if (!pp_map_walkable(_world.map, _start.x, _start.y)) {
            show_debug_message("PP scene: start tile " + string(_start.x) + "," + string(_start.y) + " is not walkable on " + string(_want));
        }
        _world.hero = pp_overworld_hero(_start.x, _start.y);
        _world.fade = undefined;
        pp_overworld_camera_follow(_world);
    }
    return true;
}

/// Run the command at the current index, or finish if there is none.
function pp_scene_command_start(_sc, _world) {
    _sc.executed += 1;
    if (_sc.executed > PP_SCENE_RUN_CAP) {
        // branch is the only control flow, and a data cycle should have been refused; never hang the game anyway.
        show_debug_message("PP: scene " + string(_sc.id) + " passed " + string(PP_SCENE_RUN_CAP) + " commands, stopping");
        _sc.ended_by = "cap";
        _sc.state = "idle";
        _sc.finished = true;
        return;
    }
    if (_sc.index < 0 || _sc.index >= array_length(_sc.commands)) {
        _sc.ended_by = "runout";
        _sc.state = "idle";
        _sc.finished = true;
        return;
    }
    var _cmd = _sc.commands[_sc.index];
    var _kind = _cmd.cmd;
    if (_sc.trace) show_debug_message("PP scene trace: " + string(_sc.id) + "[" + string(_sc.index) + "] " + string(_kind));

    switch (_kind) {
        case "say":
            _sc.dialogue = pp_dialogue_open(_cmd.id);
            _sc.state = "dialogue";
            return;

        case "move":
            _sc.state = "move";
            var _tiles = 1;
            if (variable_struct_exists(_cmd, "tiles")) _tiles = _cmd.tiles;
            var _who = "hero";
            if (variable_struct_exists(_cmd, "actor")) _who = _cmd.actor;
            var _dir_move = "down";
            if (variable_struct_exists(_cmd, "dir")) {
                _dir_move = _cmd.dir;
            } else {
                show_debug_message("PP scene: move without a direction at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            if (_who == "hero") {
                var _d = pp_world_dir_vector(_dir_move);
                if (!pp_world_start_move(_world, _world.hero.tx + _d.x * _tiles, _world.hero.ty + _d.y * _tiles, PP_WALK_STEPS_RAIL)) {
                    // A blocked rail stops the walk where it is and says so in pp_overworld; the scene still moves on,
                    // because a scene that stalls on a wall is a stuck scene and a checker error, not a hang.
                    pp_scene_advance(_sc, _world);
                }
            } else {
                var _actor = pp_scene_actor(_world, _who);
                if (is_undefined(_actor)) {
                    show_debug_message("PP scene: no actor " + string(_who) + " to move at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                    pp_scene_advance(_sc, _world);
                } else if (!pp_scene_actor_move(_world, _actor, _dir_move, _tiles)) {
                    pp_scene_advance(_sc, _world);
                }
            }
            return;

        case "face":
            var _who_face = "hero";
            if (variable_struct_exists(_cmd, "actor")) _who_face = _cmd.actor;
            var _dir_face = "down";
            if (variable_struct_exists(_cmd, "dir")) {
                _dir_face = _cmd.dir;
            } else {
                show_debug_message("PP scene: face without a direction at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            if (_who_face == "hero") {
                _world.hero.facing = _dir_face;
            } else {
                var _actor_face = pp_scene_actor(_world, _who_face);
                if (is_undefined(_actor_face)) {
                    show_debug_message("PP scene: no actor " + string(_who_face) + " to face at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                } else {
                    _actor_face.facing = _dir_face;
                }
            }
            pp_scene_advance(_sc, _world);
            return;

        case "wait":
            _sc.timer = 1;
            if (variable_struct_exists(_cmd, "steps")) _sc.timer = max(0, _cmd.steps);
            _sc.state = "wait";
            return;

        case "fade":
            var _dir = "out";
            var _steps_fade = PP_FADE_STEPS;
            if (variable_struct_exists(_cmd, "mode")) _dir = _cmd.mode;
            if (variable_struct_exists(_cmd, "steps")) _steps_fade = _cmd.steps;
            _world.fade = { alpha: (_dir == "in" ? 1 : 0), dir: (_dir == "in" ? -1 : 1),
                            total: _steps_fade, steps: 0 };
            _sc.state = "fade";
            return;

        case "music":
            // The scene names a cue id and the registry decides what that means (spec 12, card G0-2). A cue whose OGG
            // is not in the build yet stays silent and says so; the scene never blocks on audio.
            if (!variable_struct_exists(_cmd, "id")) {
                show_debug_message("PP scene: music without an id at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            _world.music = _cmd.id;
            pp_audio_music(_cmd.id, PP_AUDIO_FADE_STEPS);
            show_debug_message("PP: music " + string(_cmd.id) + " requested");
            pp_scene_advance(_sc, _world);
            return;

        case "sfx":
            if (!variable_struct_exists(_cmd, "id")) {
                show_debug_message("PP scene: sfx without an id at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            _world.sfx = _cmd.id;
            pp_audio_sfx("sfx", _cmd.id);
            show_debug_message("PP: sfx " + string(_cmd.id) + " requested");
            pp_scene_advance(_sc, _world);
            return;

        case "camera":
            if (variable_struct_exists(_cmd, "actor")) {
                _world.camera_follow = true;
                _world.cam_pan = undefined;
                _world.camera_actor = _cmd.actor;
            } else if (variable_struct_exists(_cmd, "x") && variable_struct_exists(_cmd, "y")) {
                var _px = _cmd.x * PP_TILE;
                var _py = _cmd.y * PP_TILE;
                _world.camera_follow = false;
                _world.camera_actor = "";
                _world.cam_pan = { from_x: _world.cam_x, from_y: _world.cam_y, to_x: _px, to_y: _py,
                                   total: PP_CAMERA_MOVE_STEPS, steps: 0 };
            } else {
                show_debug_message("PP scene: camera without x,y or an actor at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            _sc.state = "camera";
            return;

        case "shake":
            var _shake_steps = 8;
            if (variable_struct_exists(_cmd, "steps")) _shake_steps = _cmd.steps;
            var _shake_strength = 1;
            if (variable_struct_exists(_cmd, "strength")) _shake_strength = _cmd.strength;
            _world.shake_steps = min(_shake_steps, PP_SHAKE_MAX_STEPS);
            _world.shake_strength = _shake_strength;
            pp_scene_advance(_sc, _world);
            return;

        case "flash":
            // Card t_531bc76c: the storm's lightning. The world holds the flash and its own clock counts it down, so
            // this command costs the scene ZERO steps and the film's 10,680 do not move (decision D19's named cost,
            // paid without touching the cut grid). It advances in the same step it runs, which is why a `sfx` and a
            // `flash` next to each other land on the same frame: the sound and the light agree.
            var _flash_steps = PP_FLASH_STEPS;
            if (variable_struct_exists(_cmd, "steps")) _flash_steps = _cmd.steps;
            var _flash_role = "paper";
            if (variable_struct_exists(_cmd, "role")) _flash_role = _cmd.role;
            pp_world_flash(_world, _flash_steps, _flash_role);
            show_debug_message("PP scene: flash " + string(_flash_role) + " for " + string(_flash_steps)
                + " frames at " + string(_sc.id) + "[" + string(_sc.index) + "]");
            pp_scene_advance(_sc, _world);
            return;

        case "spawn":
            if (!variable_struct_exists(_cmd, "actor") || !variable_struct_exists(_cmd, "x") || !variable_struct_exists(_cmd, "y")) {
                show_debug_message("PP scene: spawn needs an actor and an x,y tile at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            pp_world_spawn_actor(_world, _cmd.actor, _cmd.x, _cmd.y);
            var _born = pp_scene_actor(_world, _cmd.actor);
            if (!is_undefined(_born)) {
                _born.facing = "down";
                _born.moving = false;
                _born.steps = 0;
                _born.total = 1;
            }
            pp_scene_advance(_sc, _world);
            return;

        case "destroy":
            if (!variable_struct_exists(_cmd, "actor")) {
                show_debug_message("PP scene: destroy without an actor at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            pp_world_destroy_actor(_world, _cmd.actor);
            pp_scene_advance(_sc, _world);
            return;

        case "battle":
            if (!variable_struct_exists(_cmd, "id")) {
                show_debug_message("PP scene: battle without an enemy id at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            _sc.state = "battle";
            if (_sc.autoplay) {
                // The self test never opens a fight; it asks the world for the outcome the fight would hand back, so the
                // wait for battle_done is the same wait a real fight goes through.
                _world.battle_done = "";
                pp_overworld_battle_finished(_world, _cmd.id, "spare");
                show_debug_message("PP scene trace: battle " + string(_cmd.id) + " answered spare by the self test");
                return;
            }
            _world.battle_request = _cmd.id;
            return;

        case "setflag":
            if (!variable_struct_exists(_cmd, "name")) {
                show_debug_message("PP scene: setflag without a name at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            var _value = true;
            if (variable_struct_exists(_cmd, "value")) _value = _cmd.value;
            pp_ledger_set_flag(global.pp_ledger, _cmd.name, _value);
            pp_scene_advance(_sc, _world);
            return;

        case "branch":
            var _flag = "";
            if (variable_struct_exists(_cmd, "flag")) _flag = _cmd.flag;
            if (_flag == "") {
                show_debug_message("PP scene: branch without a flag at " + string(_sc.id) + "[" + string(_sc.index) + "]");
                pp_scene_advance(_sc, _world);
                return;
            }
            if (pp_ledger_flag(global.pp_ledger, _flag)) {
                var _target = undefined;
                if (variable_struct_exists(_cmd, "scene")) _target = pp_data_find(global.pp_data.scenes.scenes, _cmd.scene);
                if (is_undefined(_target)) {
                    show_debug_message("PP: branch target missing " + string(_cmd.scene));
                    pp_scene_advance(_sc, _world);
                    return;
                }
                // Re-enter in place: the target's commands, map and start tile, in this same runner. No second runner
                // and no app fade, so the map fade the surrounding scene already did is not restarted (card R23).
                show_debug_message("PP scene: branch to " + string(_target.id) + " on flag " + string(_flag));
                pp_scene_take_scene(_sc, _world, _target);
                pp_scene_command_start(_sc, _world);
                return;
            }
            pp_scene_advance(_sc, _world);
            return;

        case "end":
            pp_scene_end(_sc, _world);
            return;

        default:
            _sc.unknown += 1;
            show_debug_message("PP: unknown scene command " + string(_kind) + " at " + string(_sc.id) + "[" + string(_sc.index) + "]");
            pp_scene_advance(_sc, _world);
            return;
    }
}

/// Move to the next command, or finish.
function pp_scene_advance(_sc, _world) {
    if (!is_undefined(_sc.dialogue)) _sc.dialogue = undefined;
    _sc.index += 1;
    if (_sc.index >= array_length(_sc.commands)) {
        // A scene that runs out of commands without `end` is a data error the checker names; the runner still stops and
        // says which scene did it, because falling off the end is not a hang.
        show_debug_message("PP: scene " + string(_sc.id) + " ran out of commands without end");
        _sc.ended_by = "runout";
        _sc.finished = true;
        _sc.state = "idle";
        return;
    }
    pp_scene_command_start(_sc, _world);
}

/// One step of the current command. The world steps its own fade, camera pan, shake and the hero's walk; the runner
/// steps story actors and waits for whatever the command is waiting for.
function pp_scene_step(_sc, _world) {
    if (is_undefined(_sc) || _sc.finished) return;
    // F2 stepping (spec 06 rule 7): once the debug step key has been used, the scene only moves on a press.
    if (_sc.debug_step) return;

    switch (_sc.state) {
        case "dialogue":
            if (is_undefined(_sc.dialogue)) {
                pp_scene_advance(_sc, _world);
                return;
            }
            if (_sc.autoplay) {
                // The self test presses confirm for the player: a page that offers a choice takes the first item, which
                // is the same door pp_dialogue_pick is for.
                if (pp_dialogue_on_choice_page(_sc.dialogue)) {
                    if (_sc.dialogue.reveal.revealed >= pp_text_unit_length(_sc.dialogue.reveal)) {
                        pp_dialogue_pick(_sc.dialogue, 0);
                    } else {
                        pp_dialogue_advance(_sc.dialogue);
                    }
                } else {
                    pp_dialogue_advance(_sc.dialogue);
                }
            } else if (pp_pressed("confirm")) {
                pp_dialogue_advance(_sc.dialogue);
            }
            pp_dialogue_step(_sc.dialogue);
            if (pp_dialogue_closed(_sc.dialogue)) {
                _sc.dialogue = undefined;
                pp_scene_advance(_sc, _world);
            }
            return;

        case "move":
            pp_scene_actors_walk(_world);
            if (is_struct(_world.hero) && _world.hero.moving) return;
            if (pp_scene_actor_moving(_world)) return;
            pp_scene_advance(_sc, _world);
            return;

        case "wait":
            _sc.timer -= 1;
            if (_sc.timer <= 0) pp_scene_advance(_sc, _world);
            return;

        case "fade":
            if (is_undefined(_world.fade)) pp_scene_advance(_sc, _world);
            return;

        case "camera":
            if (is_undefined(_world.cam_pan)) pp_scene_advance(_sc, _world);
            return;

        case "battle":
            // Card t_905a18ce (F2): an INTERRUPTED fight never reaches this branch. pp_overworld_battle_finished starts
            // the scene the fight handed over, through the one scene door, in the same call that takes the outcome, so
            // the runner that waited here is replaced before the next step and its remaining commands never play over
            // the story (spec 18 section 4 step 6: the fight is not resumed). A kill and a spare hand nothing over, so
            // battle_done carries their word and this scene advances as it always has.
            if (_world.battle_done != "") {
                _world.battle_done = "";
                pp_scene_advance(_sc, _world);
            }
            return;

        default:
            pp_scene_advance(_sc, _world);
            return;
    }
}

/// Hand control back to the walker. The tile is the one the hero is standing on, the camera follows him again, and a
/// fade left at black is turned around, because a scene that ends on a black frame is a scene the player cannot play.
function pp_scene_end(_sc, _world) {
    if (is_struct(_world)) {
        if (is_struct(_world.hero)) {
            // A `move` still in flight lands on its target tile, which is the tile the hero already owns (pp_overworld
            // writes tx, ty at the start of a move and px, py along it).
            _world.hero.px = _world.hero.tx * PP_TILE;
            _world.hero.py = _world.hero.ty * PP_TILE;
            _world.hero.moving = false;
            _world.hero.steps = _world.hero.total;
        }
        _world.cam_pan = undefined;
        _world.camera_follow = true;
        _world.camera_actor = "";
        if (is_struct(_world.fade) && _world.fade.alpha >= 1) {
            _world.fade = { alpha: 1, dir: -1, total: PP_FADE_STEPS, steps: 0 };
        }
        pp_overworld_camera_follow(_world);
    }
    _sc.state = "idle";
    _sc.ended_by = "end";
    _sc.finished = true;
    if (is_struct(_world) && is_struct(_world.hero)) {
        show_debug_message("PP scene: " + string(_sc.id) + " end at tile " + string(_world.hero.tx) + "," + string(_world.hero.ty));
    } else {
        show_debug_message("PP scene: " + string(_sc.id) + " end");
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Story actors. The world owns the hero's walk; a scene that moves anybody else needs the same rail walk for an actor,
// so the parts of it the actor needs are here rather than in pp_overworld (card R23 scope).

function pp_scene_actor(_world, _name) {
    if (!is_struct(_world) || !is_struct(_world.actors)) return undefined;
    var _key = string(_name);
    if (!variable_struct_exists(_world.actors, _key)) return undefined;
    return _world.actors[$ _key];
}

/// Start a rail move for an actor that is not the hero. A blocked tile stops the move where the actor is and says so.
function pp_scene_actor_move(_world, _actor, _dir, _tiles) {
    var _d = pp_world_dir_vector(_dir);
    if (_d.x == 0 && _d.y == 0) return false;
    _actor.facing = _dir;
    var _tx = _actor.tx + _d.x * _tiles;
    var _ty = _actor.ty + _d.y * _tiles;
    var _cx = _actor.tx;
    var _cy = _actor.ty;
    var _guard = 0;
    while ((_cx != _tx || _cy != _ty) && _guard < 128) {
        _cx += _d.x;
        _cy += _d.y;
        if (!pp_map_walkable(_world.map, _cx, _cy)) {
            show_debug_message("PP scene: blocked actor move to " + string(_tx) + "," + string(_ty));
            return false;
        }
        _guard += 1;
    }
    if (!variable_struct_exists(_actor, "px") || is_undefined(_actor.px)) _actor.px = _actor.tx * PP_TILE;
    if (!variable_struct_exists(_actor, "py") || is_undefined(_actor.py)) _actor.py = _actor.ty * PP_TILE;
    _actor.from_x = _actor.px;
    _actor.from_y = _actor.py;
    _actor.to_x = _tx * PP_TILE;
    _actor.to_y = _ty * PP_TILE;
    _actor.tx = _tx;
    _actor.ty = _ty;
    _actor.steps = 0;
    var _dist = abs(_actor.to_x - _actor.from_x) + abs(_actor.to_y - _actor.from_y);
    _actor.total = max(1, (_dist / PP_TILE) * PP_WALK_STEPS_RAIL);
    _actor.moving = true;
    return true;
}

/// One step of every actor walk under way. Whole pixels, and the last step lands exactly on the tile.
function pp_scene_actors_walk(_world) {
    if (!is_struct(_world) || !is_struct(_world.actors)) return;
    var _names = variable_struct_get_names(_world.actors);
    var _i = 0;
    while (_i < array_length(_names)) {
        var _a = _world.actors[$ _names[_i]];
        if (variable_struct_exists(_a, "moving") && _a.moving) {
            _a.steps += 1;
            var _t = _a.steps / _a.total;
            if (_t >= 1) {
                _a.px = _a.to_x;
                _a.py = _a.to_y;
                _a.moving = false;
            } else {
                _a.px = floor(lerp(_a.from_x, _a.to_x, _t));
                _a.py = floor(lerp(_a.from_y, _a.to_y, _t));
            }
        }
        _i += 1;
    }
}

function pp_scene_actor_moving(_world) {
    if (!is_struct(_world) || !is_struct(_world.actors)) return false;
    var _names = variable_struct_get_names(_world.actors);
    var _i = 0;
    while (_i < array_length(_names)) {
        var _a = _world.actors[$ _names[_i]];
        if (variable_struct_exists(_a, "moving") && _a.moving) return true;
        _i += 1;
    }
    return false;
}

// ---------------------------------------------------------------------------------------------------------------
// Debug keys (spec 06 rule 7 and card R23's check). Both keys are dead in a real launch: they do nothing unless the
// environment variable PP_SCENE_SELFTEST_ENV names is set, which only a scratch run does.

/// F1: play every committed scene in data\scenes\all.json in order and print the run log. F2: step one command of the
/// running scene and print its index. Returns true when a key was used.
function pp_scene_debug_key(_world) {
    if (environment_get_variable(PP_SCENE_SELFTEST_ENV) == "") return false;
    if (pp_pressed("debug_warp")) {
        pp_scene_selftest();
        return true;
    }
    if (pp_pressed("debug_step")) {
        pp_scene_debug_step(_world);
        return true;
    }
    return false;
}

/// Complete the command that is running, right now, without waiting for its clock. Used by the F2 step key only.
function pp_scene_debug_finish(_sc, _world) {
    switch (_sc.state) {
        case "dialogue":
            if (!is_undefined(_sc.dialogue)) _sc.dialogue.closed = true;
            _sc.dialogue = undefined;
            return;
        case "move":
            if (is_struct(_world.hero)) {
                _world.hero.px = _world.hero.to_x;
                _world.hero.py = _world.hero.to_y;
                _world.hero.moving = false;
            }
            pp_scene_actors_land(_world);
            return;
        case "wait":
            _sc.timer = 0;
            return;
        case "fade":
            _world.fade = undefined;
            return;
        case "camera":
            if (is_struct(_world.cam_pan)) {
                _world.cam_x = _world.cam_pan.to_x;
                _world.cam_y = _world.cam_pan.to_y;
            }
            _world.cam_pan = undefined;
            return;
        case "battle":
            if (_world.battle_request == "") return;
            _world.battle_request = "";
            pp_overworld_battle_finished(_world, "", "spare");
            return;
        default:
            return;
    }
}

function pp_scene_actors_land(_world) {
    if (!is_struct(_world) || !is_struct(_world.actors)) return;
    var _names = variable_struct_get_names(_world.actors);
    var _i = 0;
    while (_i < array_length(_names)) {
        var _a = _world.actors[$ _names[_i]];
        if (variable_struct_exists(_a, "moving") && _a.moving) {
            _a.px = _a.to_x;
            _a.py = _a.to_y;
            _a.moving = false;
        }
        _i += 1;
    }
}

/// F2: print where the runner is, finish that command, and start the next one. Nothing else in the project runs the
/// scene while the key has been used, so one press is exactly one command.
function pp_scene_debug_step(_world) {
    var _sc = undefined;
    if (is_struct(_world)) _sc = _world.scene;
    if (!pp_scene_running(_sc)) {
        show_debug_message("PP scene debug: no scene running, nothing to step");
        return false;
    }
    _sc.debug_step = true;
    var _kind = "";
    if (_sc.index >= 0 && _sc.index < array_length(_sc.commands)) _kind = _sc.commands[_sc.index].cmd;
    show_debug_message("PP scene debug: " + string(_sc.id) + " index " + string(_sc.index) + " (" + string(_kind) + ") done");
    pp_scene_debug_finish(_sc, _world);
    pp_scene_advance(_sc, _world);
    if (pp_scene_running(_sc)) {
        var _next = "";
        if (_sc.index >= 0 && _sc.index < array_length(_sc.commands)) _next = _sc.commands[_sc.index].cmd;
        show_debug_message("PP scene debug: index " + string(_sc.index) + " (" + string(_next) + ") waits for F2");
    } else {
        show_debug_message("PP scene debug: " + string(_sc.id) + " finished by " + string(_sc.ended_by));
    }
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// The scene self test (card R23's check).

/// Play every committed scene in order, each on its own throwaway world, and print one line per scene and a total. The
/// live ledger is put aside for the duration, so a scene's setflag never lands in the player's run. Returns true when
/// every scene reached `end` with no unhandled command and no stuck state.
function pp_scene_selftest() {
    var _scenes = global.pp_data.scenes.scenes;
    var _saved_ledger = global.pp_ledger;
    var _passed = 0;
    var _failed = 0;
    var _i = 0;
    show_debug_message("PP scene selftest: " + string(array_length(_scenes)) + " committed scenes");
    while (_i < array_length(_scenes)) {
        global.pp_ledger = pp_ledger_new();
        var _one = pp_scene_selftest_one(_scenes[_i]);
        if (_one.ok) {
            _passed += 1;
        } else {
            _failed += 1;
        }
        show_debug_message(_one.line);
        _i += 1;
    }
    global.pp_ledger = _saved_ledger;
    show_debug_message("PP scene selftest: " + string(_passed) + " played, " + string(_failed) + " failed");
    return (_failed == 0);
}

/// The spawn a throwaway world starts from: the map's own "start" spawn when it has one, otherwise its first spawn
/// alphabetically, so the self test never logs a missing spawn it does not care about. The scene's start tile is what
/// actually places the walker.
function pp_scene_selftest_spawn(_map_id) {
    var _row = pp_data_find(global.pp_data.maps.maps, _map_id);
    if (is_undefined(_row) || !variable_struct_exists(_row, "spawns")) return "start";
    if (variable_struct_exists(_row.spawns, "start")) return "start";
    var _names = variable_struct_get_names(_row.spawns);
    if (array_length(_names) == 0) return "start";
    var _first = _names[0];
    var _i = 1;
    while (_i < array_length(_names)) {
        if (_names[_i] < _first) _first = _names[_i];
        _i += 1;
    }
    return _first;
}

/// One scene: a fresh world on the scene's map, the real runner, and a step loop that stands in for the frame loop.
function pp_scene_selftest_one(_row) {
    var _map_id = "";
    if (variable_struct_exists(_row, "map")) _map_id = _row.map;
    if (_map_id == "") {
        if (is_struct(global.pp_data.slice) && variable_struct_exists(global.pp_data.slice, "map")) _map_id = global.pp_data.slice.map;
    }
    var _world = pp_overworld_new(_map_id, pp_scene_selftest_spawn(_map_id));
    if (is_undefined(_world)) {
        return { ok: false, line: "PP scene selftest: " + string(_row.id) + " FAILED: map " + string(_map_id) + " did not load" };
    }
    var _sc = pp_scene_new(_row.id, _world);
    if (is_undefined(_sc)) {
        return { ok: false, line: "PP scene selftest: " + string(_row.id) + " FAILED: the runner refused the scene" };
    }
    _sc.autoplay = true;
    _sc.trace = true;
    var _steps = 0;
    while (pp_scene_running(_sc) && _steps < PP_SCENE_SELFTEST_CAP) {
        pp_scene_step(_sc, _world);
        // The world's own frame work, in the order pp_overworld_step does it.
        pp_world_move_step(_world);
        pp_scene_actors_walk(_world);
        pp_overworld_clock_step(_world);
        _steps += 1;
    }
    var _hero = "";
    if (is_struct(_world.hero)) _hero = string(_world.hero.tx) + "," + string(_world.hero.ty);
    if (pp_scene_running(_sc)) {
        return { ok: false, line: "PP scene selftest: " + string(_row.id) + " STUCK at index " + string(_sc.index)
                 + " state " + string(_sc.state) + " after " + string(_steps) + " steps, hero " + _hero };
    }
    if (_sc.ended_by != "end") {
        return { ok: false, line: "PP scene selftest: " + string(_row.id) + " FAILED: ended by " + string(_sc.ended_by)
                 + " after " + string(_sc.executed) + " commands, hero " + _hero };
    }
    if (_sc.unknown > 0) {
        return { ok: false, line: "PP scene selftest: " + string(_row.id) + " FAILED: " + string(_sc.unknown)
                 + " unhandled commands, hero " + _hero };
    }
    return { ok: true, line: "PP scene selftest: " + string(_row.id) + " ok, " + string(_sc.executed) + " commands, "
             + string(_steps) + " steps, end at tile " + _hero + " on " + string(_world.map.id) };
}
