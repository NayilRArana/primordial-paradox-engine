/// pp_look: the 8 bit look as a rule the engine enforces, not a habit (specs 13 and 03).
/// One place owns the frame: the whole integer scale, the application surface, the GUI size, point sampling, the whole
/// pixel drawing offset, and the palette set the screen is drawing with. pp_camera asks this module for the scale
/// instead of computing a second one, so no part of a frame can believe it is drawn at 2x while the window is at 3x.
/// Provenance: knowledge\PROVENANCE.md, entry "the 8 bit look: one scale, one palette set per room" (2026-10-22).

// ---------------------------------------------------------------------------------------------------------------
// The frame: one size, one whole scale, no filter.

/// Create the look state and apply it once. Called from pp_app_boot after the data load, because the palette sets and
/// their role names are data.
function pp_look_init() {
    global.pp_look = {
        scale: 1,
        offset_x: 0,
        offset_y: 0,
        last_window_w: -1,
        last_window_h: -1,
        palette: "",
        roles: {},          // role name -> master palette index, for the set in use
        master: {},         // role name -> master palette index, every role the master palette declares
        colours: []         // the set in use, resolved to colours once, so drawing never parses a role name
    };

    if (is_struct(global.pp_data) && is_struct(global.pp_data.palette)) {
        if (variable_struct_exists(global.pp_data.palette, "roles")) {
            global.pp_look.master = global.pp_data.palette.roles;
        }
    }

    pp_look_apply_window();
    pp_look_palette("");
    return global.pp_look;
}

/// The largest whole scale that fits a window: max(1, min(6, floor(min(w / 256, h / 240)))) (spec 03).
function pp_look_scale_for(_ww, _hh) {
    var _sx = floor(_ww / PP_FRAME_W);
    var _sy = floor(_hh / PP_FRAME_H);
    return max(1, min(PP_MAX_SCALE, min(_sx, _sy)));
}

/// Size the window, the application surface and the GUI to one whole scale. Never to a fraction (spec 03 rule 2).
function pp_look_apply_window() {
    var _look = global.pp_look;
    var _s = pp_look_scale_for(window_get_width(), window_get_height());
    _look.scale = _s;
    var _w = PP_FRAME_W * _s;
    var _h = PP_FRAME_H * _s;

    if (window_get_width() != _w || window_get_height() != _h) {
        window_set_size(_w, _h);
    }
    // The manual's own pattern for a pixel perfect frame: the application surface is the frame times the scale, so one
    // game pixel is a whole square of screen pixels and nothing is ever resampled (checked at the source 2026-10-22).
    if (surface_exists(application_surface)) {
        if (surface_get_width(application_surface) != _w || surface_get_height(application_surface) != _h) {
            surface_resize(application_surface, _w, _h);
        }
    }
    display_set_gui_size(PP_FRAME_W, PP_FRAME_H);

    // A letterbox offset is a whole number of pixels, so a window that cannot take the scale (a fullscreen display)
    // still centres the frame with no half pixel seam (spec 13: no fractional scaling, no anti aliasing).
    _look.offset_x = max(0, (window_get_width() - _w) div 2);
    _look.offset_y = max(0, (window_get_height() - _h) div 2);

    // Once, in the one place that owns the frame. Texture interpolation off is what makes a pixel a pixel.
    gpu_set_tex_filter(false);
    gpu_set_tex_repeat(false);

    _look.last_window_w = window_get_width();
    _look.last_window_h = window_get_height();
    return _s;
}

/// Poll the window once per step. GameMaker has no window resize event, so the resize is noticed here (spec 03 rule 6),
/// and the scale is recomputed on the new size, never interpolated between two sizes.
function pp_look_update() {
    var _look = global.pp_look;
    if (window_get_width() != _look.last_window_w || window_get_height() != _look.last_window_h) {
        return pp_look_apply_window();
    }
    return _look.scale;
}

/// The whole scale in use right now, 1 to PP_MAX_SCALE.
function pp_look_scale() {
    return global.pp_look.scale;
}

/// Snap a coordinate to the nearest whole pixel before it is drawn. Movement may use fractions, drawing may not
/// (spec 03 rule 3).
function pp_look_pixel(_v) {
    return round(_v);
}

// ---------------------------------------------------------------------------------------------------------------
// The palette: at most 16 colours per screen, named by role, declared in data.

/// Load the palette set a room draws with. An empty id asks for the default set named in data\room_palettes.json, so a
/// screen that has not named one still draws in a declared set instead of an accident.
function pp_look_palette(_id) {
    var _look = global.pp_look;
    var _wanted = _id;
    var _roles = [];

    var _pal = undefined;
    if (is_struct(global.pp_data) && variable_struct_exists(global.pp_data, "room_palettes")) {
        _pal = global.pp_data.room_palettes;
    }

    if (is_struct(_pal)) {
        if (!is_string(_wanted) || _wanted == "") {
            if (variable_struct_exists(_pal, "default")) _wanted = _pal.default;
        }
        if (variable_struct_exists(_pal, "sets") && is_array(_pal.sets)) {
            for (var i = 0; i < array_length(_pal.sets); i++) {
                var _set = _pal.sets[i];
                if (is_struct(_set) && variable_struct_exists(_set, "id") && _set.id == _wanted) {
                    if (variable_struct_exists(_set, "roles")) _roles = _set.roles;
                    break;
                }
            }
        }
    }

    if (array_length(_roles) == 0 && _wanted != "") {
        show_debug_message("PP: no room palette set with id " + string(_wanted) + ", drawing in the master roles");
    }

    _look.palette = string(_wanted);
    _look.roles = {};
    _look.colours = [];
    if (is_array(_roles)) {
        for (var r = 0; r < array_length(_roles); r++) {
            var _name = _roles[r];
            if (variable_struct_exists(_look.master, _name)) {
                _look.roles[$ _name] = _look.master[$ _name];
                array_push(_look.colours, pp_colour(_look.master[$ _name]));
            }
        }
    }
    return array_length(_look.colours);
}

/// The master palette index a role resolves to. The room's set wins, then the master palette, and an unknown name falls
/// back to index 0 so a typo is a checker error rather than a crash in the middle of a frame.
function pp_look_role_index(_name) {
    var _look = global.pp_look;
    if (is_struct(_look)) {
        if (variable_struct_exists(_look.roles, _name)) return _look.roles[$ _name];
        if (variable_struct_exists(_look.master, _name)) return _look.master[$ _name];
    }
    return 0;
}

/// A role name to a colour. Every draw call in the game asks for a role and never for a colour literal (spec 13).
function pp_role_colour(_name) {
    return pp_colour(pp_look_role_index(_name));
}

/// The colours of the set in use, in the order the set names them. The debug overlay reads this, and so does the test
/// that checks a room cannot spend more than 16 colours.
function pp_look_colours() {
    return global.pp_look.colours;
}

/// The id of the set in use, for the debug overlay and for a boot line that names what the screen is drawn with.
function pp_look_palette_id() {
    return global.pp_look.palette;
}
