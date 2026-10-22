/// pp_scene: the cutscene runner (spec 06). A scene is a list of commands in data; one runs at a time; anything that
/// takes time blocks the list. branch is the only control flow, and a branch cycle is refused by the checker.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop", written before the notice of
/// 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The runner is spec 06: one command at a
/// time, branch as the only control flow.

/// The commands this runner implements. The checker reads this list from data\scenes and refuses anything else.
function pp_scene_commands() {
    return ["say", "move", "face", "wait", "fade", "music", "sfx", "camera", "shake",
            "spawn", "destroy", "battle", "setflag", "branch", "end"];
}

/// A new runner for a scene id. Returns undefined when the id or its commands are missing.
function pp_scene_new(_scene_id, _world) {
    var _row = pp_data_find(global.pp_data.scenes.scenes, _scene_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no scene with id " + string(_scene_id));
        return undefined;
    }
    var _sc = {
        id: _row.id,
        map: _row.map,
        commands: _row.commands,
        index: 0,
        state: "idle",
        timer: 0,
        dialogue: undefined,
        executed: 0,
        finished: false
    };
    pp_scene_command_start(_sc, _world);
    return _sc;
}

/// True while the scene still owns the screen.
function pp_scene_running(_sc) {
    if (is_undefined(_sc)) return false;
    return !_sc.finished;
}

/// Run the command at the current index, or finish if there is none.
function pp_scene_command_start(_sc, _world) {
    _sc.executed += 1;
    if (_sc.executed > 1000) {
        // branch is the only control flow, and a data cycle should have been refused; never hang the game anyway.
        show_debug_message("PP: scene " + string(_sc.id) + " passed 1000 commands, stopping");
        _sc.finished = true;
        return;
    }
    if (_sc.index < 0 || _sc.index >= array_length(_sc.commands)) {
        _sc.finished = true;
        return;
    }
    var _cmd = _sc.commands[_sc.index];
    var _kind = _cmd.cmd;

    switch (_kind) {
        case "say":
            _sc.dialogue = pp_dialogue_open(_cmd.id);
            _sc.state = "dialogue";
            return;

        case "move":
            var _steps = PP_WALK_STEPS_RAIL;
            if (_cmd.actor == "hero") {
                var _d = pp_world_dir_vector(_cmd.dir);
                pp_world_start_move(_world, _world.hero.tx + _d.x * _cmd.tiles, _world.hero.ty + _d.y * _cmd.tiles, _steps);
            }
            _sc.state = "move";
            return;

        case "face":
            if (_cmd.actor == "hero") _world.hero.facing = _cmd.dir;
            pp_scene_advance(_sc, _world);
            return;

        case "wait":
            _sc.timer = _cmd.steps;
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
            _world.music = _cmd.id;
            pp_audio_music(_cmd.id, PP_AUDIO_FADE_STEPS);
            show_debug_message("PP: music " + string(_cmd.id) + " requested");
            pp_scene_advance(_sc, _world);
            return;

        case "sfx":
            _world.sfx = _cmd.id;
            pp_audio_sfx("sfx", _cmd.id);
            show_debug_message("PP: sfx " + string(_cmd.id) + " requested");
            pp_scene_advance(_sc, _world);
            return;

        case "camera":
            if (variable_struct_exists(_cmd, "actor")) {
                _world.camera_follow = true;
                _world.cam_pan = undefined;
            } else {
                var _px = _cmd.x * PP_TILE;
                var _py = _cmd.y * PP_TILE;
                _world.camera_follow = false;
                _world.cam_pan = { from_x: _world.cam_x, from_y: _world.cam_y, to_x: _px, to_y: _py,
                                   total: PP_CAMERA_MOVE_STEPS, steps: 0 };
            }
            _sc.state = "camera";
            return;

        case "shake":
            _world.shake_steps = min(_cmd.steps, PP_SHAKE_MAX_STEPS);
            _world.shake_strength = _cmd.strength;
            pp_scene_advance(_sc, _world);
            return;

        case "spawn":
            pp_world_spawn_actor(_world, _cmd.actor, _cmd.x, _cmd.y);
            pp_scene_advance(_sc, _world);
            return;

        case "destroy":
            pp_world_destroy_actor(_world, _cmd.actor);
            pp_scene_advance(_sc, _world);
            return;

        case "battle":
            _world.battle_request = _cmd.id;
            _sc.state = "battle";
            return;

        case "setflag":
            pp_ledger_set_flag(global.pp_ledger, _cmd.name, _cmd.value);
            pp_scene_advance(_sc, _world);
            return;

        case "branch":
            if (pp_ledger_flag(global.pp_ledger, _cmd.flag)) {
                var _target = pp_data_find(global.pp_data.scenes.scenes, _cmd.scene);
                if (is_undefined(_target)) {
                    show_debug_message("PP: branch target missing " + string(_cmd.scene));
                    pp_scene_advance(_sc, _world);
                    return;
                }
                _sc.commands = _target.commands;
                _sc.index = 0;
                pp_scene_command_start(_sc, _world);
                return;
            }
            pp_scene_advance(_sc, _world);
            return;

        case "end":
            _sc.state = "idle";
            _sc.finished = true;
            return;

        default:
            show_debug_message("PP: unknown scene command " + string(_kind) + " at " + string(_sc.id) + "[" + string(_sc.index) + "]");
            pp_scene_advance(_sc, _world);
            return;
    }
}

/// Move to the next command, or finish.
function pp_scene_advance(_sc, _world) {
    _sc.index += 1;
    if (_sc.index >= array_length(_sc.commands)) {
        _sc.finished = true;
        _sc.state = "idle";
        return;
    }
    pp_scene_command_start(_sc, _world);
}

/// One step of the current command. The world steps its own fade, camera pan, shake and movement.
function pp_scene_step(_sc, _world) {
    if (is_undefined(_sc) || _sc.finished) return;

    switch (_sc.state) {
        case "dialogue":
            if (is_undefined(_sc.dialogue)) {
                pp_scene_advance(_sc, _world);
                return;
            }
            if (pp_pressed("confirm")) pp_dialogue_advance(_sc.dialogue);
            pp_dialogue_step(_sc.dialogue);
            if (pp_dialogue_closed(_sc.dialogue)) {
                _sc.dialogue = undefined;
                pp_scene_advance(_sc, _world);
            }
            return;

        case "move":
            if (!_world.hero.moving) pp_scene_advance(_sc, _world);
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
