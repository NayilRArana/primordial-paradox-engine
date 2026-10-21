/// pp_title: the title screen, the night drive and the menu (spec 14 and its night drive addendum).
///
/// The screen is one scene drawn from the title art: seven seamless night layers that scroll at the speeds
/// TITLE-COORD.md fixes, the battered hatchback with its two passengers, Theo's storm cloud, the counting down
/// road sign, the logo, and then the menu. The state of the screen lives here, in one struct, and the app mode
/// machine owns the frame (spec 01).
///
/// Everything is written from specs\14-title-screen-drive.md, its addendum, TITLE-COORD.md and the manual pages
/// named in each function. The art is this project's own; nothing is copied from any existing game.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone".

// The logo takes one second to arrive (spec 14: it fades in over 1 second, then shimmers).
#macro PP_TITLE_FADE_STEPS 60
// The world scrolls at the rate the offline preview used: 12 pixels a second at 12 frames a second, which at
// this game's 60 steps a second is 0.2 pixels a step.
#macro PP_TITLE_SCROLL_PX_PER_STEP 0.2
// The prompt blinks at 2 Hz, the logo shimmers for 0.4 seconds every 4 seconds, and the menu cursor blinks at 4 Hz.
#macro PP_TITLE_BLINK_STEPS 30
#macro PP_TITLE_SHIMMER_STEPS 24
#macro PP_TITLE_SHIMMER_PERIOD 240
#macro PP_TITLE_CURSOR_PERIOD 15
// The drive out before the map: the intro text scrolls over the road for four seconds.
#macro PP_TITLE_DRIVE_STEPS 240
#macro PP_TITLE_DRIVE_LINE_STEPS 70
// Where the logo, the prompt and the menu sit, in frame pixels.
#macro PP_TITLE_LOGO_X 16
#macro PP_TITLE_LOGO_Y 2
#macro PP_TITLE_PROMPT_Y 72
#macro PP_TITLE_MENU_X 16
#macro PP_TITLE_MENU_Y 66
#macro PP_TITLE_MENU_STEP 12
#macro PP_TITLE_CURSOR_X 6
// The car sits at the left of the road, and the headlight cone is on the tarmac ahead of it.
#macro PP_TITLE_CAR_X 76
#macro PP_TITLE_CAR_Y 186
#macro PP_TITLE_CONE_X 140
#macro PP_TITLE_CONE_Y 200
// The wheel arches and the two window openings of the car sprite, measured from its own pixels by
// tools\art\measure_title_car.py.
#macro PP_TITLE_ARCH_NEAR 14
#macro PP_TITLE_ARCH_FAR 46
#macro PP_TITLE_WINDOW_A 8
#macro PP_TITLE_WINDOW_A_END 24
#macro PP_TITLE_WINDOW_B 28
#macro PP_TITLE_WINDOW_B_END 50
#macro PP_TITLE_BAND_TOP 8
#macro PP_TITLE_BAND_BOTTOM 15
// The sign plate is baked into the verge tile, and this is where it stands in that tile.
#macro PP_TITLE_SIGN_X 30
#macro PP_TITLE_SIGN_Y 30

/// The layer table, the car and the menu, exactly as the offline preview composed them. The file data\title.json
/// can override any of it; these are the values the art lane's own manifest published.
function pp_title_defaults() {
    return {
        layers: [
            { name: "title_L1_sky",    y: 0,   speed: 0.0  },
            { name: "title_L2_clouds", y: 0,   speed: 0.05 },
            { name: "title_L3_downs",  y: 92,  speed: 0.15 },
            { name: "title_L4_fields", y: 128, speed: 0.35 },
            { name: "title_L5_verge",  y: 120, speed: 0.7  },
            { name: "title_L6_road",   y: 196, speed: 1.0  },
            { name: "title_L7_fg",     y: 196, speed: 1.3  }
        ],
        car_x: PP_TITLE_CAR_X,
        car_y: PP_TITLE_CAR_Y,
        cone_x: PP_TITLE_CONE_X,
        menu: ["NEW GAME", "CONTINUE", "SETTINGS", "QUIT"],
        intro: [
            "THE ROAD TO SOUTHAMPTON.",
            "TWO MEN WHO DO NOT KNOW EACH OTHER.",
            "ONE OF THEM IS WAITING FOR THE OTHER."
        ]
    };
}

/// Read data\title.json if the build has it. A file that is missing or unreadable leaves the defaults alone,
/// so the screen works even before the data file lands.
function pp_title_read_data() {
    var _paths = ["datafiles/title.json", "title.json"];
    for (var i = 0; i < array_length(_paths); i += 1) {
        var _p = working_directory + _paths[i];
        if (!file_exists(_p)) continue;
        var _f = file_text_open_read(_p);
        if (_f < 0) continue;
        var _out = "";
        while (!file_text_eof(_f)) {
            _out += file_text_readln(_f);
            if (!file_text_eof(_f)) _out += "\n";
        }
        file_text_close(_f);
        try {
            var _d = json_parse(_out);
            if (is_struct(_d)) return _d;
        } catch (_e) {
            // A data file that will not parse is the defaults' problem, not the screen's.
            return undefined;
        }
    }
    return undefined;
}

/// The table the screen draws from: the defaults, with anything the data file names laid over them.
function pp_title_data() {
    var _d = pp_title_defaults();
    var _f = pp_title_read_data();
    if (is_undefined(_f)) return _d;
    if (variable_struct_exists(_f, "layers") && is_array(_f.layers) && array_length(_f.layers) > 0) {
        var _rows = [];
        for (var i = 0; i < array_length(_f.layers); i += 1) {
            var _row = _f.layers[i];
            if (!is_struct(_row) || !variable_struct_exists(_row, "name")) continue;
            _rows.push({
                name: _row.name,
                y: (variable_struct_exists(_row, "y") ? _row.y : 0),
                speed: (variable_struct_exists(_row, "speed") ? _row.speed : 0)
            });
        }
        if (array_length(_rows) > 0) _d.layers = _rows;
    }
    if (variable_struct_exists(_f, "menu") && is_array(_f.menu) && array_length(_f.menu) > 0) {
        var _menu = [];
        for (var m = 0; m < array_length(_f.menu); m += 1) {
            if (is_string(_f.menu[m])) _menu.push(_f.menu[m]);
        }
        if (array_length(_menu) > 0) _d.menu = _menu;
    }
    if (variable_struct_exists(_f, "intro") && is_array(_f.intro) && array_length(_f.intro) > 0) {
        var _intro = [];
        for (var n = 0; n < array_length(_f.intro); n += 1) {
            if (is_string(_f.intro[n])) _intro.push(_f.intro[n]);
        }
        if (array_length(_intro) > 0) _d.intro = _intro;
    }
    if (variable_struct_exists(_f, "car_x")) _d.car_x = _f.car_x;
    if (variable_struct_exists(_f, "car_y")) _d.car_y = _f.car_y;
    return _d;
}

/// A fresh screen. The logo starts invisible and the prompt is up.
function pp_title_state_new() {
    return {
        steps: 0,
        phase: "prompt",
        menu_index: 0,
        scroll: 0,
        logo_alpha: 0,
        drive: 0,
        drive_line: 0,
        flash: false,
        data: pp_title_data()
    };
}

/// Enter the screen. The theme and the engine are asked for by cue name; the bus stays silent until the
/// music lane delivers the files (spec 12 rule 1, and the addendum's silence until then).
function pp_title_enter(_params) {
    global.pp.title = pp_title_state_new();
    pp_audio_play("title_theme");
    pp_audio_play("car_engine_loop");
}

/// One step of the screen. The only thing that reads a key here is the input module (spec 02 rule 1).
function pp_title_step(_params) {
    var _s = global.pp.title;
    if (is_undefined(_s)) return;
    _s.steps += 1;
    _s.scroll += PP_TITLE_SCROLL_PX_PER_STEP;
    if (_s.logo_alpha < 1) {
        _s.logo_alpha = min(1, _s.logo_alpha + (1 / PP_TITLE_FADE_STEPS));
    }

    if (_s.phase == "prompt") {
        if (pp_pressed("confirm")) {
            _s.phase = "menu";
            _s.menu_index = 0;
            pp_audio_play("menu_select");
        }
        return;
    }

    if (_s.phase == "menu") {
        var _count = array_length(_s.data.menu);
        var _dir = pp_menu_axis("up", "down");
        if (_dir != 0 && _count > 0) {
            _s.menu_index = (_s.menu_index + _dir + _count) mod _count;
            pp_audio_play("menu_move");
        }
        if (pp_pressed("confirm")) {
            pp_title_select(_s);
        }
        return;
    }

    if (_s.phase == "settings") {
        // The placeholder screen has one row, BACK, and both the confirm and the cancel key leave it.
        if (pp_pressed("confirm") || pp_pressed("cancel")) {
            _s.phase = "menu";
            pp_audio_play("menu_select");
        }
        return;
    }

    if (_s.phase == "drive") {
        _s.drive += 1;
        if (_s.drive >= PP_TITLE_DRIVE_STEPS) {
            // A new run: a fresh ledger, the slice's first map, and the fade the app machine owns.
            pp_save_new_game();
        }
    }
}

/// What the chosen row does.
function pp_title_select(_s) {
    var _row = _s.menu_index;
    var _name = "";
    if (_row >= 0 && _row < array_length(_s.data.menu)) _name = _s.data.menu[_row];
    if (_name == "NEW GAME") {
        pp_audio_play("menu_select");
        _s.phase = "drive";
        _s.drive = 0;
        _s.drive_line = 0;
        return;
    }
    if (_name == "CONTINUE") {
        // The row is greyed when there is no save, so choosing it does nothing but make a noise.
        if (!pp_save_ready()) {
            pp_audio_play("menu_move");
            return;
        }
        pp_audio_play("menu_select");
        pp_save_apply();
        return;
    }
    if (_name == "SETTINGS") {
        pp_audio_play("menu_select");
        _s.phase = "settings";
        return;
    }
    if (_name == "QUIT") {
        pp_audio_play("menu_select");
        game_end();
    }
}

/// True when the save slot holds a run that CONTINUE could load.
function pp_title_has_save() {
    return pp_save_ready();
}

/// The scene, back to front, and then the logo and the words on top of it.
function pp_title_draw(_params) {
    var _s = global.pp.title;
    if (is_undefined(_s)) return;
    var _d = _s.data;

    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    pp_title_draw_layers(_s, _d);
    pp_title_draw_sign(_s, _d);
    pp_title_draw_cone(_s, _d);
    pp_title_draw_car(_s, _d);
    pp_title_draw_cloud(_s, _d);
    pp_title_draw_logo(_s);
    pp_title_draw_words(_s, _d);
}

/// The seven night layers, each scrolled at its own speed. A layer is one image wider than the view, so the
/// wrap is drawn as a tail and then a head (the art lane's own technique).
function pp_title_draw_layers(_s, _d) {
    for (var i = 0; i < array_length(_d.layers); i += 1) {
        var _layer = _d.layers[i];
        var _info = pp_art_info(_layer.name);
        if (is_undefined(_info)) continue;
        var _offset = round(_s.scroll * _layer.speed);
        pp_art_layer(_layer.name, pp_art_frame_at(_layer.name, _s.steps), _layer.y, _offset, PP_FRAME_W, _info.frame_h);
    }
}

/// The road sign, drawn over the plate the verge tile carries, so the miles to Southampton count down.
function pp_title_draw_sign(_s, _d) {
    if (!pp_art_has("spr_title_sign")) return;
    var _verge = pp_title_layer_named(_d, "title_L5_verge");
    if (is_undefined(_verge)) return;
    var _offset = (round(_s.scroll * _verge.speed) mod 512);
    var _index = floor((_s.steps / 15) mod 4);
    for (var shift = -512; shift <= 512; shift += 512) {
        var _x = PP_TITLE_SIGN_X - _offset + shift;
        if (_x > -100 && _x < PP_FRAME_W) {
            pp_art_draw("spr_title_sign", _index, _x, _verge.y + PP_TITLE_SIGN_Y, c_white, 1);
        }
    }
}

/// The headlight cone on the tarmac ahead of the car.
function pp_title_draw_cone(_s, _d) {
    if (!pp_art_has("spr_title_cone")) return;
    pp_art_draw("spr_title_cone", 0, _d.cone_x, PP_TITLE_CONE_Y, c_white, 1);
}

/// The car, its wheels, its exhaust and the two people in it.
function pp_title_draw_car(_s, _d) {
    if (!pp_art_has("spr_title_car")) return;
    var _x = _d.car_x;
    var _y = _d.car_y;

    // The exhaust puff, behind the rear of the car, one frame every fifth of a second.
    var _puff = (floor(_s.steps / 5) mod 20);
    if (_puff < 4 && pp_art_has("spr_title_exhaust")) {
        pp_art_draw("spr_title_exhaust", _puff, _x, _y + 14, c_white, 1);
    }

    // The wheels turn, and the body bobs over them.
    if (pp_art_has("spr_title_wheel")) {
        var _wheel = floor(_s.steps / 5) mod pp_art_frames("spr_title_wheel");
        pp_art_draw("spr_title_wheel", _wheel, _x + PP_TITLE_ARCH_NEAR - 5, _y + 22, c_white, 1);
        pp_art_draw("spr_title_wheel", _wheel, _x + PP_TITLE_ARCH_FAR - 5, _y + 22, c_white, 1);
    }
    var _body = floor(_s.steps / 10) mod pp_art_frames("spr_title_car");
    pp_art_draw("spr_title_car", _body, _x, _y, c_white, 1);

    // The two heads, in the two windows: the passenger on the left, the driver on the right.
    var _bust_y = _y + max(0, floor((PP_TITLE_BAND_TOP + PP_TITLE_BAND_BOTTOM) / 2) - 3 - 1);
    var _index = floor(_s.steps * 2 / 15);
    if (pp_art_has("spr_title_theo")) {
        var _theo = _index mod pp_art_frames("spr_title_theo");
        var _theo_x = _x + floor((PP_TITLE_WINDOW_A + PP_TITLE_WINDOW_A_END) / 2) - 6;
        pp_art_draw("spr_title_theo", _theo, _theo_x, _bust_y, c_white, 1);
    }
    if (pp_art_has("spr_title_ronan")) {
        var _ronan = _index mod pp_art_frames("spr_title_ronan");
        var _ronan_x = _x + floor((PP_TITLE_WINDOW_B + PP_TITLE_WINDOW_B_END) / 2) - 6;
        pp_art_draw("spr_title_ronan", _ronan, _ronan_x, _bust_y, c_white, 1);
    }

    // The speech bubble, once per loop, when Theo turns to say something.
    var _phase = _s.steps mod 600;
    if (_phase >= 360 && _phase < 420 && pp_art_has("spr_title_bubble")) {
        var _bubble = floor(_s.steps / 10) mod pp_art_frames("spr_title_bubble");
        pp_art_draw("spr_title_bubble", _bubble, _x + PP_TITLE_WINDOW_A - 1, _y - 10, c_white, 1);
    }
}

/// Theo's storm cloud, which follows the car, with a soft flash every ten seconds.
function pp_title_draw_cloud(_s, _d) {
    if (!pp_art_has("spr_title_cloud")) return;
    var _phase = _s.steps mod 600;
    var _flash = (_phase >= 540 && _phase < 564);
    if (_flash && !_s.flash) pp_audio_play("thunder_soft");
    _s.flash = _flash;
    var _index = 0;
    if (_flash) {
        _index = 2;
    } else {
        _index = floor(_s.steps / 30) mod 2;
    }
    pp_art_draw("spr_title_cloud", _index, _d.car_x + 64, 80, c_white, 1);
}

/// The logo: it fades in over a second, then a gold shimmer passes over it every four seconds.
function pp_title_draw_logo(_s) {
    if (!pp_art_has("spr_pp_title_logo")) return;
    var _index = 0;
    if ((_s.steps mod PP_TITLE_SHIMMER_PERIOD) < PP_TITLE_SHIMMER_STEPS) _index = 1;
    pp_art_draw("spr_pp_title_logo", _index, PP_TITLE_LOGO_X, PP_TITLE_LOGO_Y, c_white, _s.logo_alpha);
}

/// The words: the prompt, the menu, the settings placeholder, or the intro text over the road.
function pp_title_draw_words(_s, _d) {
    if (_s.phase == "drive") {
        pp_title_draw_intro(_s, _d);
        return;
    }
    if (_s.phase == "settings") {
        pp_title_draw_settings(_s);
        return;
    }
    if (_s.phase == "prompt") {
        if (floor(_s.steps / PP_TITLE_BLINK_STEPS) mod 2 == 0) {
            pp_font_draw_centre("PRESS Z OR ENTER", PP_FRAME_W / 2, PP_TITLE_PROMPT_Y, pp_role_colour("bright"), 1);
        }
        return;
    }
    // The menu. CONTINUE is greyed when the slot holds no run.
    var _has_save = pp_title_has_save();
    for (var i = 0; i < array_length(_d.menu); i += 1) {
        var _label = _d.menu[i];
        var _colour = pp_role_colour("bright");
        if (_label == "CONTINUE" && !_has_save) _colour = pp_role_colour("faint");
        pp_font_draw(_label, PP_TITLE_MENU_X, PP_TITLE_MENU_Y + i * PP_TITLE_MENU_STEP, _colour, 1);
    }
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_TITLE_CURSOR_X, PP_TITLE_MENU_Y + _s.menu_index * PP_TITLE_MENU_STEP, c_white, 1);
    }
}

/// The settings placeholder: a title and one row, BACK.
function pp_title_draw_settings(_s) {
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(24, 76, PP_FRAME_W - 24, 150, false);
    draw_set_colour(pp_role_colour("bright"));
    draw_rectangle(24, 76, PP_FRAME_W - 24, 150, false);
    draw_set_alpha(1);
    pp_font_draw_centre("SETTINGS", PP_FRAME_W / 2, 92, pp_role_colour("bright"), 1);
    pp_font_draw_centre("NOTHING HERE YET", PP_FRAME_W / 2, 110, pp_role_colour("faint"), 1);
    pp_font_draw_centre("BACK", PP_FRAME_W / 2, 130, pp_role_colour("bright"), 1);
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_FRAME_W / 2 - 40, 130, c_white, 1);
    }
}

/// The intro text over the road, one line at a time, each line scrolling up as it goes.
function pp_title_draw_intro(_s, _d) {
    var _count = array_length(_d.intro);
    if (_count == 0) return;
    var _index = floor(_s.drive / PP_TITLE_DRIVE_LINE_STEPS);
    if (_index >= _count) _index = _count - 1;
    var _within = _s.drive - _index * PP_TITLE_DRIVE_LINE_STEPS;
    var _y = 210 - _within * 2;
    pp_font_draw_centre(_d.intro[_index], PP_FRAME_W / 2, _y, pp_role_colour("bright"), 1);
    if (_index + 1 < _count) {
        var _next_y = 210 + (PP_TITLE_DRIVE_LINE_STEPS - _within) * 2;
        pp_font_draw_centre(_d.intro[_index + 1], PP_FRAME_W / 2, _next_y, pp_role_colour("bright"), 1);
    }
}

/// The layer with this name, or undefined.
function pp_title_layer_named(_d, _name) {
    for (var i = 0; i < array_length(_d.layers); i += 1) {
        if (_d.layers[i].name == _name) return _d.layers[i];
    }
    return undefined;
}

/// The app mode that runs the title screen. Registered by pp_app_boot.
function pp_title_mode() {
    return {
        enter: function(_params) { pp_title_enter(_params); },
        step: function(_params) { pp_title_step(_params); },
        draw: function(_params) { pp_title_draw(_params); }
    };
}
