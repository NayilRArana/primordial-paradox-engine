/// pp_look: the 8 bit look as a rule the engine enforces, not a habit (specs 13 and 03).
/// One place owns the frame: the whole integer scale, the viewport, the application surface, the GUI size, point
/// sampling, and the palette set the screen is drawing with. pp_camera asks this module for the scale instead of
/// computing a second one, so no part of a frame can believe it is drawn at 2x while the window is at 3x.
/// Provenance: knowledge\PROVENANCE.md, entry "the 8 bit look: one scale, one palette set per room" (2026-10-22).
///
/// Every engine call in this module is cited at its manual page, on the line above the call, because the argument of
/// an engine call is the part that is easy to remember wrongly. The pages were read on 2026-10-22 while writing these
/// calls, and each one states the behaviour the comment beside it claims. They are cited by URL under
/// https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/ .

// ---------------------------------------------------------------------------------------------------------------
// The frame: one size, one whole scale, one viewport, no filter.

/// Create the look state and apply it once. Called from pp_app_boot after the data load, because the palette sets and
/// their role names are data.
function pp_look_init() {
    global.pp_look = {
        scale: 1,
        surface_w: -1,      // the surface size this module last asked for, which is not the size it reports back yet
        surface_h: -1,
        last_window_w: -1,
        last_window_h: -1,
        palette: "",        // the id of the set in use
        roles: {},          // role name -> master palette index, for the set in use
        master: {},         // role name -> master palette index, every role the master palette declares
        colours: [],        // the set in use, resolved to colours once, so drawing never parses a role name
        missing: {}         // role name -> true, so a role outside the set is reported once, not once per frame
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

/// Size the window, the viewport, the application surface and the GUI to one whole scale. Never to a fraction
/// (spec 03 rule 2). One game pixel is one surface pixel, and the viewport is the frame times the scale, so the whole
/// screen is drawn at the integer scale the window can hold.
function pp_look_apply_window() {
    var _look = global.pp_look;
    var _s = pp_look_scale_for(window_get_width(), window_get_height());
    _look.scale = _s;
    var _w = PP_FRAME_W * _s;
    var _h = PP_FRAME_H * _s;

    if (window_get_width() != _w || window_get_height() != _h) {
        window_set_size(_w, _h);
    }

    // Viewport 0 is the frame's own port (spec 03: one viewport, 256*scale by 240*scale at the top left). The camera
    // view stays exactly 256x240 at the room origin, and GameMaker scales a view up into its port: "if you have a larger
    // or smaller viewport size than that assigned to the camera, then the camera view will be scaled down - or up - to
    // fit". That sentence is on the view_wport page, so it is cited here on the quote itself, not only at the calls
    // below it.
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/view_wport.htm
    // The room origin, not the camera position, is what moves: pp_camera offsets the world in room space, so a view
    // that also moved would count the same offset twice.
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/view_enabled.htm
    view_enabled = true;
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/view_visible.htm
    view_visible[0] = true;
    view_set_xport(0, 0);
    view_set_yport(0, 0);
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/view_set_wport.htm
    view_set_wport(0, _w);
    view_set_hport(0, _h);
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/camera_set_view_size.htm
    camera_set_view_size(view_camera[0], PP_FRAME_W, PP_FRAME_H);

    // The application surface is the port, so one game pixel is a whole square of screen pixels and nothing is ever
    // resampled twice: "the camera size is multiplied with that resolution scale and applied as the size of the
    // application surface, which defines the game's resolution".
    if (surface_exists(application_surface)) {
        // The size is remembered rather than read back, because surface_resize "will not be registered until the start
        // of the next draw frame", so surface_get_width still reports the old size within the same step.
        // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/Surfaces/application_surface.htm
        // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/Surfaces/surface_resize.htm
        if (_look.surface_w != _w || _look.surface_h != _h) {
            surface_resize(application_surface, _w, _h);
            _look.surface_w = _w;
            _look.surface_h = _h;
        }
    }

    // The GUI is the frame, so one GUI unit is one game pixel at 1x: "the GUI layer is stretched to fit the size of the
    // game window no matter the resolution".
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/display_set_gui_size.htm
    display_set_gui_size(PP_FRAME_W, PP_FRAME_H);

    // Once, in the one place that owns the frame. Texture interpolation off is what makes a pixel a pixel. The manual
    // documents this call as gpu_set_texfilter(enable), with no underscores in the name; the runtime's own function
    // table (GmlSpec.xml in runtime-2026.0.0.23) lists gpu_set_tex_filter as the same real, non deprecated function
    // with the same one boolean argument, and this module uses that spelling.
    // https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/GPU_Control/gpu_set_texfilter.htm
    gpu_set_tex_filter(false);
    gpu_set_tex_repeat(false);

    _look.last_window_w = window_get_width();
    _look.last_window_h = window_get_height();
    return _s;
}

/// Poll the window once per step, and keep the viewport this module set. GameMaker has no window resize event, so the
/// resize is noticed here (spec 03 rule 6), and the scale is recomputed on the new size, never interpolated between two
/// sizes. The port is re-asserted on the same poll because the view settings are properties of a room, not of the game:
/// entering another room applies that room's ports and visibility, which are all invisible in this project, so without
/// this the second room would draw 1:1 into the corner of a 3x surface.
/// https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Room_Properties/Room_Properties.htm
function pp_look_update() {
    var _look = global.pp_look;
    if (window_get_width() != _look.last_window_w || window_get_height() != _look.last_window_h) {
        return pp_look_apply_window();
    }
    var _w = PP_FRAME_W * _look.scale;
    var _h = PP_FRAME_H * _look.scale;
    if (!view_enabled || !view_visible[0] || view_get_wport(0) != _w || view_get_hport(0) != _h) {
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
        show_debug_message("PP: no room palette set with id " + string(_wanted) + ", every role draws as PP_COLOUR_MISSING");
    }

    _look.palette = string(_wanted);
    _look.roles = {};
    _look.colours = [];
    _look.missing = {};
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

/// The master palette index a role resolves to inside the set the screen is drawing with, or -1 when the set does not
/// declare that role. There is deliberately no fallback to the master palette: a room that asked for a colour its own
/// set does not declare would spend a colour past the 16 the screen may hold, which is what spec 13 rule 2 forbids and
/// what acceptance 3 refuses, so the gap is drawn and logged instead of absorbed.
function pp_look_role_index(_name) {
    var _look = global.pp_look;
    if (is_struct(_look) && variable_struct_exists(_look.roles, _name)) {
        return _look.roles[$ _name];
    }
    return -1;
}

/// A role name to a colour. Every draw call in the game asks for a role and never for a colour literal (spec 13). A role
/// the room's set does not declare draws as PP_COLOUR_MISSING, which is a colour no palette set may declare, and is
/// reported once per role per set so the gap shows in the run log as well as on screen.
function pp_role_colour(_name) {
    var _index = pp_look_role_index(_name);
    if (_index >= 0) return pp_colour(_index);

    var _look = global.pp_look;
    if (is_struct(_look)) {
        var _key = string(_name);
        if (!variable_struct_exists(_look.missing, _key)) {
            _look.missing[$ _key] = true;
            show_debug_message("PP: role " + _key + " is not in the room palette set " + string(_look.palette)
                               + ", drawing it as PP_COLOUR_MISSING");
        }
    }
    return PP_COLOUR_MISSING;
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
