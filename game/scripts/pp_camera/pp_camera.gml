/// pp_camera: integer scaling and a whole pixel camera (spec 03).
/// One place computes the scale and one place maps world to screen, so no object carries its own offset.
/// Provenance: knowledge\PROVENANCE.md; our camera lives in a struct and recomputes from the window each step
/// instead of listening for an event index we have not verified against the IDE.

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

/// The integer scale for a window size: max(1, min(6, floor(min(w/256, h/240)))).
function pp_camera_scale_for(_ww, _hh) {
    var _sx = floor(_ww / PP_FRAME_W);
    var _sy = floor(_hh / PP_FRAME_H);
    var _s = min(_sx, _sy);
    return max(1, min(PP_MAX_SCALE, _s));
}

/// Size the window, the application surface and the GUI to one scale. No interpolation anywhere (spec 03 rule 1).
function pp_camera_apply_window(_state) {
    var _s = pp_camera_scale_for(window_get_width(), window_get_height());
    _state.scale = _s;
    var _w = PP_FRAME_W * _s;
    var _h = PP_FRAME_H * _s;

    if (window_get_width() != _w || window_get_height() != _h) {
        window_set_size(_w, _h);
    }
    if (surface_exists(application_surface)) {
        if (surface_get_width(application_surface) != _w || surface_get_height(application_surface) != _h) {
            surface_resize(application_surface, _w, _h);
        }
    }
    display_set_gui_size(PP_FRAME_W, PP_FRAME_H);
    gpu_set_tex_filter(false);

    _state.last_window_w = window_get_width();
    _state.last_window_h = window_get_height();
    return _s;
}

/// Recompute only when the window actually changed, which is what the resize handler would have done.
function pp_camera_step(_state) {
    if (window_get_width() != _state.last_window_w || window_get_height() != _state.last_window_h) {
        pp_camera_apply_window(_state);
    }
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
