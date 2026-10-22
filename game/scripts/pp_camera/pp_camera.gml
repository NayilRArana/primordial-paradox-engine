/// pp_camera: integer scaling and a whole pixel camera (spec 03).
/// One place computes the scale and one place maps world to screen, so no object carries its own offset.
/// Provenance: knowledge\PROVENANCE.md, entry "room and object conventions across a whole game", written before the
/// notice of 2026-10-19 and re-confirmed by the clean-room re-review of the same date. Scale and layout are spec 03;
/// the window is polled each step, so nothing here assumes an event number the IDE has not confirmed.

/// Create the camera state. Called once from pp_app_boot.
function pp_camera_init() {
    var _state = {
        scale: 1,
        base_w: PP_FRAME_W,
        base_h: PP_FRAME_H,
        last_window_w: -1,
        last_window_h: -1,
        x: 0,
        y: 0
    };
    pp_camera_apply_window(_state);
    return _state;
}

/// The integer scale for a window size. The arithmetic lives in pp_look, which owns the frame, so there is exactly one
/// implementation of it in the project (spec 03 numbers, spec 13 rule that one place decides the scale).
function pp_camera_scale_for(_ww, _hh) {
    return pp_look_scale_for(_ww, _hh);
}

/// Size the window, the application surface and the GUI to one whole scale. Delegated: pp_look owns the frame.
function pp_camera_apply_window(_state) {
    var _s = pp_look_apply_window();
    _state.scale = _s;
    return _s;
}

/// Recompute only when the window actually changed, which is what the resize handler would have done. The poll itself is
/// pp_look's, because that module owns the frame.
function pp_camera_step(_state) {
    _state.scale = pp_look_update();
    _state.last_window_w = window_get_width();
    _state.last_window_h = window_get_height();
}

/// Follow a walker with a dead zone, a speed cap and look ahead, then clamp inside the room (spec 03 rules).
function pp_camera_follow(_state, _px, _py, _facing_x, _facing_y, _room_w, _room_h) {
    var _target_x = _px - PP_FRAME_W * 0.5 + _facing_x * 16;
    var _target_y = _py - PP_FRAME_H * 0.5 + _facing_y * 16;

    if (abs(_target_x - _state.x) > 16) {
        _state.x += clamp(_target_x - _state.x, -4, 4);
    }
    if (abs(_target_y - _state.y) > 12) {
        _state.y += clamp(_target_y - _state.y, -4, 4);
    }

    _state.x = clamp(floor(_state.x), 0, max(0, _room_w - PP_FRAME_W));
    _state.y = clamp(floor(_state.y), 0, max(0, _room_h - PP_FRAME_H));
    return _state;
}

/// Put the camera exactly on a point, for a room entry or a scripted pan target (spec 06 camera command).
function pp_camera_snap_to(_state, _x, _y) {
    _state.x = floor(_x);
    _state.y = floor(_y);
    return _state;
}

function pp_camera_screen_x(_state, _wx) {
    return floor(_wx) - _state.x;
}

function pp_camera_screen_y(_state, _wy) {
    return floor(_wy) - _state.y;
}
