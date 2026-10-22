/// pp_title: the title screen, the night drive and the menu (spec 14, its night drive addendum and plan v2 section 2).
///
/// The screen is one scene drawn from the title art: seven seamless night layers that scroll at the speeds
/// TITLE-COORD.md fixes, the battered hatchback with its two passengers, Theo's storm cloud, the counting down
/// road sign, the logo, and then the menu inside the FF1 style window. The state of the screen lives here, in one
/// struct, and the app mode machine owns the frame (spec 01).
///
/// The opening shot pans down from Big Ben into the drive and plays once, on the first boot only; a marker file in
/// the save area records that it has been seen, so every later launch goes straight to the title card.
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
// Where the logo, the prompt, the window and its rows sit, in frame pixels. The window is the classic NES JRPG
// box, low and centred, sized in whole 8x8 tiles (18 by 9) because the art lane's spr_pp_window is nine tiles and
// scaling it would tear its edges. The four rows sit inside its 8 pixel border, and the cursor is against that edge.
#macro PP_TITLE_LOGO_X 16
#macro PP_TITLE_LOGO_Y 2
#macro PP_TITLE_PROMPT_Y 72
#macro PP_TITLE_MENU_WIN_X 56
#macro PP_TITLE_MENU_WIN_Y 148
#macro PP_TITLE_MENU_WIN_TW 18
#macro PP_TITLE_MENU_WIN_TH 9
#macro PP_TITLE_MENU_WIN_W 144
#macro PP_TITLE_MENU_WIN_H 72
#macro PP_TITLE_MENU_ROW_Y 156
#macro PP_TITLE_MENU_STEP 12
#macro PP_TITLE_CURSOR_X 8
// The window's own two text colours, taken from spr_pp_window so the letters and the frame agree: white #fcfcfc
// and the grey #7c7c7c under it. The scene text outside the window uses the same white.
#macro PP_TITLE_WHITE make_colour_rgb(252, 252, 252)
#macro PP_TITLE_GREY make_colour_rgb(124, 124, 124)
// The copyright line: one quiet row at the very bottom of the frame.
#macro PP_TITLE_COPY_TEXT "(c) 2026 NAYILINIST"
#macro PP_TITLE_COPY_Y 228
// The opening shot: a three second pan down out of the Big Ben frame, and a dissolve over the last three quarters
// of a second. Any key skips it.
#macro PP_TITLE_OPEN_STEPS 180
#macro PP_TITLE_OPEN_PAN 24
#macro PP_TITLE_OPEN_FADE 45
// Lightning: the scene swaps to the flash palette for two frames, every 8 to 12 seconds (480 to 720 steps). The
// wait is drawn from the title's own seeded stream, so the same launch flashes at the same moments.
#macro PP_TITLE_FLASH_STEPS 2
#macro PP_TITLE_FLASH_MIN_STEPS 480
#macro PP_TITLE_FLASH_MAX_STEPS 720
#macro PP_TITLE_FLASH_SEED 20261021
// The marker that says the opening has been seen. It lands in the save area beside the slot, so nothing here
// writes outside the sandbox.
#macro PP_TITLE_SEEN_FILE "pp_title_seen.txt"
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
            // array_push, not the method form: array.push(struct) reaches the runtime as an I32 and throws
            // "I32 argument is array", which killed the title the first time title.json carried layers.
            var _clean = {
                name: _row.name,
                y: (variable_struct_exists(_row, "y") ? _row.y : 0),
                speed: (variable_struct_exists(_row, "speed") ? _row.speed : 0)
            };
            array_push(_rows, _clean);
        }
        if (array_length(_rows) > 0) _d.layers = _rows;
    }
    if (variable_struct_exists(_f, "menu") && is_array(_f.menu) && array_length(_f.menu) > 0) {
        var _menu = [];
        for (var m = 0; m < array_length(_f.menu); m += 1) {
            if (is_string(_f.menu[m])) array_push(_menu, _f.menu[m]);
        }
        if (array_length(_menu) > 0) _d.menu = _menu;
    }
    if (variable_struct_exists(_f, "intro") && is_array(_f.intro) && array_length(_f.intro) > 0) {
        var _intro = [];
        for (var n = 0; n < array_length(_f.intro); n += 1) {
            if (is_string(_f.intro[n])) array_push(_intro, _f.intro[n]);
        }
        if (array_length(_intro) > 0) _d.intro = _intro;
    }
    if (variable_struct_exists(_f, "car_x")) _d.car_x = _f.car_x;
    if (variable_struct_exists(_f, "car_y")) _d.car_y = _f.car_y;
    return _d;
}

/// The marker file that says the opening shot has played. It is relative, so the sandbox puts it in the save
/// area next to the slot; nothing outside that folder is written.
function pp_title_seen_read() {
    return file_exists(PP_TITLE_SEEN_FILE);
}

function pp_title_seen_write() {
    var _f = file_text_open_write(PP_TITLE_SEEN_FILE);
    if (_f < 0) {
        show_debug_message("PP title: could not write the opening marker " + PP_TITLE_SEEN_FILE);
        return false;
    }
    file_text_write_string(_f, "1");
    file_text_close(_f);
    return true;
}

/// A fresh screen. The logo starts invisible, the lightning clock starts on its first wait, and the phase is the
/// opening on a first boot or the prompt on every later launch.
function pp_title_state_new(_phase) {
    var _s = {
        steps: 0,
        phase: _phase,
        menu_index: 0,
        scroll: 0,
        logo_alpha: 0,
        drive: 0,
        drive_line: 0,
        open: 0,
        flash_left: 0,
        flash_wait: 0,
        flash_count: 0,
        rng: pp_rng_new(PP_TITLE_FLASH_SEED),
        data: pp_title_data()
    };
    _s.flash_wait = pp_rng_int(_s.rng, PP_TITLE_FLASH_MIN_STEPS, PP_TITLE_FLASH_MAX_STEPS);
    return _s;
}

/// Enter the screen. The theme and the engine are asked for by cue name; the bus stays silent until the
/// music lane delivers the files (spec 12 rule 1, and the addendum's silence until then).
function pp_title_enter(_params) {
    if (!variable_struct_exists(global.pp, "art") || !is_struct(global.pp.art)) global.pp.art = pp_art_init();
    // The slot is asked once, when the title appears, so CONTINUE knows whether a run exists (same call the boot card makes).
    if (pp_data_ok()) pp_save_title_start();
    var _first_boot = !pp_title_seen_read();
    global.pp.title = pp_title_state_new(_first_boot ? "open" : "prompt");
    if (_first_boot) show_debug_message("PP title: first boot, playing the opening shot, any key skips it");
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

    // The storm flashes on its own clock in every phase, so the title card breathes while the menu is up.
    pp_title_step_lightning(_s);

    if (_s.phase == "open") {
        _s.open += 1;
        if (pp_input_any_pressed() || _s.open >= PP_TITLE_OPEN_STEPS) {
            // Skipping is as final as letting it run: either way this boot has seen the shot.
            _s.open = PP_TITLE_OPEN_STEPS;
            _s.phase = "prompt";
            pp_title_seen_write();
        }
        return;
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

/// The lightning clock. A flash is two frames of the flash palette and one soft thunder cue; the wait after it is
/// drawn from the state's own seeded stream, so no two waits are the same and none is shorter than 8 seconds.
function pp_title_step_lightning(_s) {
    if (_s.flash_left > 0) {
        _s.flash_left -= 1;
        return;
    }
    _s.flash_wait -= 1;
    if (_s.flash_wait > 0) return;
    _s.flash_left = PP_TITLE_FLASH_STEPS;
    _s.flash_wait = pp_rng_int(_s.rng, PP_TITLE_FLASH_MIN_STEPS, PP_TITLE_FLASH_MAX_STEPS);
    _s.flash_count += 1;
    pp_audio_play("thunder_soft");
}

/// True on the step a flash is on screen.
function pp_title_flashing(_s) {
    return is_struct(_s) && _s.flash_left > 0;
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

/// The scene, back to front, and then the logo and the words on top of it. During the opening the Big Ben frame
/// sits over the drive and drifts up out of it, so the cut into the title card is a camera move and not a jump.
function pp_title_draw(_params) {
    var _s = global.pp.title;
    if (is_undefined(_s)) return;
    var _d = _s.data;
    var _flash = pp_title_flashing(_s);

    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    pp_title_draw_layers(_s, _d, _flash);
    pp_title_draw_sign(_s, _d, _flash);
    pp_title_draw_cone(_s, _d, _flash);
    pp_title_draw_car(_s, _d);
    pp_title_draw_cloud(_s, _d, _flash);

    if (_s.phase == "open") {
        pp_title_draw_opening(_s);
        return;
    }

    pp_title_draw_logo(_s);
    pp_title_draw_words(_s, _d);
}

/// The seven night layers, each scrolled at its own speed. A layer is one image wider than the view, so the
/// wrap is drawn as a tail and then a head (the art lane's own technique). A flash swaps a layer for its
/// flash palette twin when the art lane has drawn one.
function pp_title_draw_layers(_s, _d, _flash) {
    for (var i = 0; i < array_length(_d.layers); i += 1) {
        var _layer = _d.layers[i];
        var _name = pp_title_flash_name(_layer.name, _flash);
        var _info = pp_art_info(_name);
        if (is_undefined(_info)) continue;
        var _offset = round(_s.scroll * _layer.speed);
        pp_art_layer(_name, pp_art_frame_at(_name, _s.steps), _layer.y, _offset, PP_FRAME_W, _info.frame_h);
    }
}

/// The flash twin of an animation name, or the name itself when the twin is not in the build.
function pp_title_flash_name(_name, _flash) {
    if (!_flash) return _name;
    var _twin = _name + "_flash";
    if (pp_art_has(_twin)) return _twin;
    return _name;
}

/// The road sign, drawn over the plate the verge tile carries, so the miles to Southampton count down.
function pp_title_draw_sign(_s, _d, _flash) {
    var _name = pp_title_flash_name("spr_title_sign", _flash);
    if (!pp_art_has(_name)) return;
    var _verge = pp_title_layer_named(_d, "title_L5_verge");
    if (is_undefined(_verge)) return;
    var _offset = (round(_s.scroll * _verge.speed) mod 512);
    var _index = floor((_s.steps / 15) mod 4);
    for (var shift = -512; shift <= 512; shift += 512) {
        var _x = PP_TITLE_SIGN_X - _offset + shift;
        if (_x > -100 && _x < PP_FRAME_W) {
            pp_art_draw(_name, _index, _x, _verge.y + PP_TITLE_SIGN_Y, c_white, 1);
        }
    }
}

/// The headlight cone on the tarmac ahead of the car.
function pp_title_draw_cone(_s, _d, _flash) {
    var _name = pp_title_flash_name("spr_title_cone", _flash);
    if (!pp_art_has(_name)) return;
    pp_art_draw(_name, 0, _d.cone_x, PP_TITLE_CONE_Y, c_white, 1);
}

/// The opening shot: the Big Ben frame drifts up out of the drive and dissolves, over three seconds. The drive
/// underneath is already running, so the pan lands on a moving road rather than a still.
function pp_title_draw_opening(_s) {
    if (!pp_art_has("title_BG_bigben")) return;
    var _t = min(1, _s.open / PP_TITLE_OPEN_STEPS);
    var _y = -round(PP_TITLE_OPEN_PAN * _t);
    var _left = PP_TITLE_OPEN_STEPS - _s.open;
    var _alpha = 1;
    if (_left < PP_TITLE_OPEN_FADE) _alpha = max(0, _left / PP_TITLE_OPEN_FADE);
    pp_art_draw("title_BG_bigben", 0, 0, _y, c_white, _alpha);
}

/// The car, its wheels, its exhaust and the empty dark glass: nobody is inside it.
function pp_title_draw_car(_s, _d) {
    if (!pp_art_has("spr_title_car")) return;
    var _x = _d.car_x;
    var _y = _d.car_y;

    // The exhaust puff, behind the rear of the car, one frame every fifth of a second.
    var _puff = (floor(_s.steps / 5) mod 20);
    if (_puff < 4 && pp_art_has("spr_title_exhaust")) {
        pp_art_draw("spr_title_exhaust", _puff, _x, _y + 14, c_white, 1);
    }

    // The v2 car carries its own wheels, baked into the sprite so each one sits in its arch and cannot drift,
    // and the frames turn those spokes. There is no separate wheel sprite on the title any more.
    var _body = floor(_s.steps / 10) mod pp_art_frames("spr_title_car");
    pp_art_draw("spr_title_car", _body, _x, _y, c_white, 1);

    // The cast is off the title as of TS2-ART-A (Nayil: the car shows only its exterior, no faces). The
    // sprites spr_title_theo, spr_title_ronan and spr_title_bubble stay in game\sprites_src\title for the
    // interior scenes later; the title simply does not draw them.
}

/// Theo's storm cloud, which follows the car. The lightning itself is the screen's clock (pp_title_step_lightning);
/// the cloud simply lights up while a flash is on.
function pp_title_draw_cloud(_s, _d, _flash) {
    if (!pp_art_has("spr_title_cloud")) return;
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

/// The words: the prompt, the menu in its window, the settings placeholder, or the intro text over the road.
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
            pp_font_draw_centre("PRESS START", PP_FRAME_W / 2, PP_TITLE_PROMPT_Y, PP_TITLE_WHITE, 1);
        }
        pp_title_draw_copy();
        return;
    }
    // The menu, inside the window. CONTINUE is greyed when the slot holds no run.
    pp_title_draw_menu_window();
    var _has_save = pp_title_has_save();
    for (var i = 0; i < array_length(_d.menu); i += 1) {
        var _label = _d.menu[i];
        var _colour = PP_TITLE_WHITE;
        if (_label == "CONTINUE" && !_has_save) _colour = PP_TITLE_GREY;
        pp_font_draw_centre(_label, PP_TITLE_MENU_WIN_X + PP_TITLE_MENU_WIN_W / 2,
                            PP_TITLE_MENU_ROW_Y + i * PP_TITLE_MENU_STEP, _colour, 1);
    }
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_TITLE_MENU_WIN_X + PP_TITLE_CURSOR_X,
                    PP_TITLE_MENU_ROW_Y + _s.menu_index * PP_TITLE_MENU_STEP, c_white, 1);
    }
    pp_title_draw_copy();
}

/// The menu window: the classic NES JRPG box, the art lane's spr_pp_window drawn as a nine slice at 18 by 9 tiles.
/// When that sprite is not in the build the box is drawn from the palette roles instead, which keeps the title
/// complete either way.
function pp_title_draw_menu_window() {
    if (pp_window_draw(PP_TITLE_MENU_WIN_X, PP_TITLE_MENU_WIN_Y,
                       PP_TITLE_MENU_WIN_TW, PP_TITLE_MENU_WIN_TH, 1)) return;
    pp_title_draw_window_plain(PP_TITLE_MENU_WIN_X, PP_TITLE_MENU_WIN_Y,
                               PP_TITLE_MENU_WIN_W, PP_TITLE_MENU_WIN_H);
}

/// The box drawn by hand, from the palette roles. This is the fallback while the window sprite is not in the
/// build, and it is the same two pale borders over a dark field.
function pp_title_draw_window_plain(_x, _y, _w, _h) {
    draw_set_colour(pp_role_colour("window"));
    draw_rectangle(_x + 2, _y + 2, _x + _w - 2, _y + _h - 2, false);
    draw_set_colour(pp_role_colour("window_shadow"));
    draw_rectangle(_x, _y, _x + _w - 1, _y + _h - 1, true);
    draw_set_colour(pp_role_colour("window_edge"));
    draw_rectangle(_x + 1, _y + 1, _x + _w - 2, _y + _h - 2, true);
}

/// The copyright line: one quiet row at the bottom of the frame, on every phase but the opening. The grey is the
/// window's own #7c7c7c, so the line sits behind the frame rather than competing with it.
function pp_title_draw_copy() {
    pp_font_draw_centre(PP_TITLE_COPY_TEXT, PP_FRAME_W / 2, PP_TITLE_COPY_Y, PP_TITLE_GREY, 1);
}

/// The settings placeholder: a title and one row, BACK, inside the same window frame as the menu (26 by 9 tiles).
function pp_title_draw_settings(_s) {
    if (!pp_window_draw(24, 84, 26, 9, 1)) pp_title_draw_window_plain(24, 84, 208, 72);
    draw_set_alpha(1);
    pp_font_draw_centre("SETTINGS", PP_FRAME_W / 2, 92, PP_TITLE_WHITE, 1);
    pp_font_draw_centre("NOTHING HERE YET", PP_FRAME_W / 2, 108, PP_TITLE_GREY, 1);
    pp_font_draw_centre("BACK", PP_FRAME_W / 2, 128, PP_TITLE_WHITE, 1);
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_FRAME_W / 2 - 40, 128, c_white, 1);
    }
    pp_title_draw_copy();
}

/// The intro text over the road, one line at a time, each line scrolling up as it goes.
function pp_title_draw_intro(_s, _d) {
    var _count = array_length(_d.intro);
    if (_count == 0) return;
    var _index = floor(_s.drive / PP_TITLE_DRIVE_LINE_STEPS);
    if (_index >= _count) _index = _count - 1;
    var _within = _s.drive - _index * PP_TITLE_DRIVE_LINE_STEPS;
    var _y = 210 - _within * 2;
    pp_font_draw_centre(_d.intro[_index], PP_FRAME_W / 2, _y, PP_TITLE_WHITE, 1);
    if (_index + 1 < _count) {
        var _next_y = 210 + (PP_TITLE_DRIVE_LINE_STEPS - _within) * 2;
        pp_font_draw_centre(_d.intro[_index + 1], PP_FRAME_W / 2, _next_y, PP_TITLE_WHITE, 1);
    }
    pp_title_draw_copy();
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
