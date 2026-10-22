/// pp_input: the only place in the project that reads a key or a gamepad (spec 02 rule 1).
/// Samples once per step in Begin Step, then publishes held, pressed, released and repeat per action.
/// Provenance: our own action table and normalised vector; see knowledge\PROVENANCE.md.

#macro PP_STICK_DEADZONE 0.35
#macro PP_REPEAT_FIRST 16
#macro PP_REPEAT_EVERY 8

/// The action table (spec 02 table). A later options screen reads this, so keys are data here and nowhere else.
/// A key or a pad button belongs to one action only: two actions on one key is a silent double fire, and the table is
/// what an options screen will show. tests\test_project.py pins that rule.
function pp_input_table() {
    return [
        { id: "confirm", keys: [ord("Z"), vk_space, vk_enter], pads: [gp_face1], axis: "" },
        { id: "cancel",  keys: [ord("X"), vk_escape, vk_backspace], pads: [gp_face2], axis: "" },
        { id: "menu",    keys: [vk_tab], pads: [gp_start], axis: "" },
        { id: "up",      keys: [vk_up, ord("W")], pads: [gp_padu], axis: "y" },
        { id: "down",    keys: [vk_down, ord("S")], pads: [gp_padd], axis: "y" },
        { id: "left",    keys: [vk_left, ord("A")], pads: [gp_padl], axis: "x" },
        { id: "right",   keys: [vk_right, ord("D")], pads: [gp_padr], axis: "x" },
        { id: "debug_warp",  keys: [vk_f1], pads: [], axis: "" },
        { id: "debug_step",  keys: [vk_f2], pads: [], axis: "" },
        { id: "debug_flags", keys: [vk_f3], pads: [], axis: "" }
    ];
}

/// Build the input state. Called once from pp_app_boot.
function pp_input_init() {
    var _actions = {};
    var _table = pp_input_table();
    for (var i = 0; i < array_length(_table); i++) {
        var _row = _table[i];
        _actions[$ _row.id] = {
            keys: _row.keys,
            pads: _row.pads,
            axis: _row.axis,
            held: false,
            prev: false,
            pressed: false,
            released: false,
            repeat: false,
            held_steps: 0
        };
    }
    return {
        actions: _actions,
        lock_steps: 0,
        vec_x: 0,
        vec_y: 0,
        vec_len: 0,
        pad_seen: -1
    };
}

/// One sample per step. Call from Begin Step only (spec 02, event order).
function pp_input_sample() {
    var _in = global.pp_input;
    var _keys = variable_struct_get_names(_in.actions);
    for (var i = 0; i < array_length(_keys); i++) {
        var _a = _in.actions[$ _keys[i]];
        var _down = false;
        for (var k = 0; k < array_length(_a.keys); k++) {
            if (keyboard_check(_a.keys[k])) { _down = true; break; }
        }
        for (var p = 0; p < array_length(_a.pads); p++) {
            if (gamepad_is_connected(0) && gamepad_button_check(0, _a.pads[p])) { _down = true; break; }
        }

        _a.prev = _a.held;
        _a.held = _down;
        _a.pressed = _a.held && !_a.prev;
        _a.released = (!_a.held) && _a.prev;

        if (_a.pressed) {
            _a.held_steps = 1;
            _a.repeat = false;
        } else if (_a.held) {
            _a.held_steps += 1;
            _a.repeat = (_a.held_steps == PP_REPEAT_FIRST)
                || (_a.held_steps > PP_REPEAT_FIRST && ((_a.held_steps - PP_REPEAT_FIRST) mod PP_REPEAT_EVERY == 0));
        } else {
            _a.held_steps = 0;
            _a.repeat = false;
        }
    }

    if (_in.lock_steps > 0) {
        _in.lock_steps -= 1;
        pp_input_clear_edges();
    }

    pp_input_update_vector();
    if (gamepad_is_connected(0)) _in.pad_seen = 1; else _in.pad_seen = -1;
}

/// Wipe the one step edges. Called on mode entry (spec 02 rule 3) and by the lock counter.
function pp_input_clear_edges() {
    var _in = global.pp_input;
    var _keys = variable_struct_get_names(_in.actions);
    for (var i = 0; i < array_length(_keys); i++) {
        var _a = _in.actions[$ _keys[i]];
        _a.pressed = false;
        _a.released = false;
        _a.repeat = false;
    }
}

/// Lock input for a few steps after a mode swap, so a held confirm cannot act twice (spec 02 rule 3).
function pp_input_lock(_steps) {
    global.pp_input.lock_steps = _steps;
    pp_input_clear_edges();
}

/// True on the step any key, any face button or start goes down. The title's opening shot is skippable with any
/// key, and this stays the only place that reads a key (spec 02 rule 1). A locked input reports nothing, so a
/// held key from the previous mode cannot skip the shot by accident.
function pp_input_any_pressed() {
    var _in = global.pp_input;
    if (!is_struct(_in)) return false;
    if (_in.lock_steps > 0) return false;
    if (keyboard_check_pressed(vk_anykey)) return true;
    if (gamepad_is_connected(0)) {
        for (var b = gp_face1; b <= gp_face4; b += 1) {
            if (gamepad_button_check_pressed(0, b)) return true;
        }
        if (gamepad_button_check_pressed(0, gp_start)) return true;
    }
    return false;
}

function pp_action(_name) {
    var _a = global.pp_input.actions[$ _name];
    if (is_undefined(_a)) return false;
    return _a.held;
}

function pp_pressed(_name) {
    var _a = global.pp_input.actions[$ _name];
    if (is_undefined(_a)) return false;
    return _a.pressed;
}

function pp_released(_name) {
    var _a = global.pp_input.actions[$ _name];
    if (is_undefined(_a)) return false;
    return _a.released;
}

function pp_repeat(_name) {
    var _a = global.pp_input.actions[$ _name];
    if (is_undefined(_a)) return false;
    return _a.repeat;
}

/// One normalised vector for the dodge phase (spec 02 rule 5, spec 08, and delta T3).
/// Keyboard gives one of eight unit directions; stick keeps its angle but not its magnitude.
function pp_input_update_vector() {
    var _in = global.pp_input;
    var _x = 0;
    var _y = 0;
    var _ax = 0;
    var _ay = 0;
    var _from_stick = false;

    if (gamepad_is_connected(0)) {
        _ax = gamepad_axis_value(0, gp_axislh);
        _ay = gamepad_axis_value(0, gp_axislv);
        if (point_distance(0, 0, _ax, _ay) > PP_STICK_DEADZONE) {
            _x = _ax;
            _y = _ay;
            _from_stick = true;
        }
    }

    if (!_from_stick) {
        if (pp_action("left")) _x -= 1;
        if (pp_action("right")) _x += 1;
        if (pp_action("up")) _y -= 1;
        if (pp_action("down")) _y += 1;
    }

    var _len = point_distance(0, 0, _x, _y);
    if (_len > 1) {
        _x = _x / _len;
        _y = _y / _len;
        _len = 1;
    }
    _in.vec_x = _x;
    _in.vec_y = _y;
    _in.vec_len = point_distance(0, 0, _x, _y);
}

/// Cursor axis with repeat, for menus: -1, 0 or 1 on the step the player moves the cursor.
function pp_menu_axis(_negative, _positive) {
    var _dir = 0;
    if (pp_pressed(_negative) || pp_repeat(_negative)) _dir = -1;
    if (pp_pressed(_positive) || pp_repeat(_positive)) _dir = (_dir == -1) ? 0 : 1;
    return _dir;
}
