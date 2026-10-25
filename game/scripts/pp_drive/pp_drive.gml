/// pp_drive: the drive to Southampton, the screen owner of room rm_pp_drive.
///
/// Card R21a. The twelve shots, their order and their durations in steps come from knowledge/DRIVE-SHOT-LIST.md
/// section 2, which is the one place those numbers are authored. The commands each shot will eventually run come from
/// specs/06-cutscene-runner.md, and the art each shot needs from specs/14-title-screen-drive.md. This file draws the
/// film at 256x240 with placeholder rectangles wherever the art does not exist yet, which the card allows, and it
/// draws every one of them from the room palette set named below and never from a colour literal (spec 13).
///
/// What it is not: it is not the scene runner. The drive block of data/scenes/all.json is card R21b's, and this room
/// answers "does the drive exist in the running game, do the twelve shots read as twelve different pictures, and does
/// no shot sit still for twenty seconds". A scene that says `say drive_radio_1` will still be R21b's to write.
///
/// The clock is the music's clock (knowledge/DRIVE-SHOT-LIST.md section 1): 60 steps a second, a shot's own duration in
/// steps from the table, and no shot longer than 1,200 steps, which is the twenty second ceiling the shot list holds.
/// Fades are 12 steps, per spec 06 and pacing 4.2. The grid is the exact one, 85.714 steps a bar at 126 bpm, and every
/// cut in the table is `round(bar x 85.714)` (decision D18, knowledge/GAMEDEV-DECISIONS-2026-10-24.md): the twelve
/// durations here are the same twelve numbers data/scenes/all.json spends, and tests/test_drive_map.py now compares the
/// two tables shot for shot so the copy cannot drift.
///
/// Capture only (decision D19). The drive that ships is the `drive_to_southampton` scene of data/scenes/all.json on the
/// map drive_m4_corridor, played by the spec 06 runner. This room exists so a capture run can write the twelve pictures
/// from inside the game: it is reachable only when PP_DRIVE_ROOM is set, which no real launch sets. It is not on the
/// route and it must not be wired into it.

/// The two environment names this screen reads. Split the way every PP_ name in this project is split, so the macro
/// definition is not itself a use of the name (the same pattern as PP_SLICE and PP_SCENE_SELFTEST_ENV).
#macro PP_DRIVE_ROOM "PP_" + "DRIVE_ROOM"
#macro PP_DRIVE_CAPTURE "PP_" + "DRIVE_CAPTURE"

/// The room palette set the placeholders are drawn from. data/room_palettes.json is not this card's file (its owner
/// writes it), so the room asks for a set that already exists rather than inventing one; a set of its own for the night
/// drive is a palette card, not this one.
#macro PP_DRIVE_PALETTE "ui"
/// A fade is 12 steps (spec 06, and section 1 of the shot list). Four of them: in on shot 1, out on shot 6, in on
/// shot 7, out on shot 12.
#macro PP_DRIVE_FADE 12
/// The frame is cleared and the fades are drawn in the set's own ink role, which is how every other screen in the game
/// asks for its darkest colour (pp_app, pp_overworld, pp_dodge_arena and pp_battle_director all clear with
/// pp_role_colour("ink")). A colour literal here would be a colour the palette does not own, which spec 13 rule 2
/// forbids and which tests/test_look.py refuses at any draw site.
/// The film's own length in steps, which is the sum of the twelve rows and is asserted against the table below.
#macro PP_DRIVE_TOTAL_STEPS 10680
/// The shot list's own ceiling and floor, in steps: 20 s and 8 s.
#macro PP_DRIVE_MAX_SHOT 1200
#macro PP_DRIVE_MIN_SHOT 480
/// Capture only. With PP_DRIVE_CAPTURE set, every shot holds 24 steps instead of its film length and one frame of it
/// is written from inside the draw at step 12, so a proof run of the room costs 288 frames (4.8 s) instead of 178 s.
/// The durations the film plays at are untouched by this: it changes the capture's clock, not the shot table.
#macro PP_DRIVE_CAPTURE_STEPS 24
#macro PP_DRIVE_CAPTURE_AT 12
/// The road's own speed, from data/title_timing.json scroll.px_per_step, which is one lane dash per beat.
#macro PP_DRIVE_ROAD_PX_PER_STEP 0.552

/// The twelve shots, in order, exactly as knowledge/DRIVE-SHOT-LIST.md section 2 prints them.
/// steps: the row's duration in steps. sign: the miles the gantry sign reads on that shot, or "" when no sign is in
/// shot. pages: the caption ids the row carries, in order (the twelve ids section 10 names are R21b's to author, so
/// this file prints the id itself as the placeholder text rather than inventing a line).
function pp_drive_shots() {
    return [
        { n: 1,  id: "bigben",      place: "city",    steps: 686,  sign: "",   pages: [] },
        { n: 2,  id: "street",      place: "city",    steps: 857,  sign: "",   pages: [] },
        { n: 3,  id: "gantry_55",   place: "gantry",  steps: 600,  sign: "55", pages: ["drive_sign_55"] },
        { n: 4,  id: "rain",        place: "motorway", steps: 771, sign: "",   pages: [] },
        { n: 5,  id: "radio_1_2",   place: "motorway", steps: 1029, sign: "",  pages: ["drive_radio_1", "drive_radio_2"] },
        { n: 6,  id: "radio_3_4_43", place: "motorway", steps: 1114, sign: "43", pages: ["drive_radio_3", "drive_radio_4", "drive_sign_43"] },
        { n: 7,  id: "cutting",     place: "cutting", steps: 857,  sign: "",   pages: [] },
        { n: 8,  id: "cathedral",   place: "cathedral", steps: 857, sign: "",  pages: ["drive_cathedral"] },
        { n: 9,  id: "radio_5_6_7_30", place: "motorway", steps: 1115, sign: "30", pages: ["drive_radio_5", "drive_radio_6", "drive_radio_7", "drive_sign_30"] },
        { n: 10, id: "downland",    place: "downland", steps: 1114, sign: "",  pages: [] },
        { n: 11, id: "slip_20",     place: "slip",    steps: 686,  sign: "20", pages: ["drive_sign_20"] },
        { n: 12, id: "docks",       place: "docks",   steps: 994,  sign: "",   pages: [] }
    ];
}

/// The sum of the twelve rows, read from the table rather than from the macro, so a mistyped duration is caught.
function pp_drive_total_steps() {
    var _shots = pp_drive_shots();
    var _sum = 0;
    for (var i = 0; i < array_length(_shots); i += 1) _sum += _shots[i].steps;
    return _sum;
}

/// The longest and shortest shot, as steps. The card's rule is that no shot sits still for twenty seconds, and this is
/// the number the boot line prints so the rule is answered by the run and not by reading the table.
function pp_drive_longest_shot() {
    var _shots = pp_drive_shots();
    var _longest = 0;
    for (var i = 0; i < array_length(_shots); i += 1) _longest = max(_longest, _shots[i].steps);
    return _longest;
}

function pp_drive_shortest_shot() {
    var _shots = pp_drive_shots();
    var _shortest = 1000000;
    for (var i = 0; i < array_length(_shots); i += 1) _shortest = min(_shortest, _shots[i].steps);
    return _shortest;
}

/// True when the table agrees with the film: twelve rows, the durations summing to 10,680 steps, every shot inside 8 to
/// 20 seconds. The room prints the outcome once at entry, and a table that disagrees is named rather than drawn past.
function pp_drive_table_ok() {
    var _shots = pp_drive_shots();
    if (array_length(_shots) != 12) return false;
    if (pp_drive_total_steps() != PP_DRIVE_TOTAL_STEPS) return false;
    if (pp_drive_longest_shot() > PP_DRIVE_MAX_SHOT) return false;
    if (pp_drive_shortest_shot() < PP_DRIVE_MIN_SHOT) return false;
    return true;
}

/// A fresh screen: the shot being played, the step inside it, and the caption page up.
function pp_drive_state_new() {
    var _capture = (environment_get_variable(PP_DRIVE_CAPTURE) != "");
    return {
        steps: 0,
        shot_index: 0,
        shot_steps: 0,
        page_index: -1,
        pages_logged: -1,
        shots_logged: -1,
        done: false,
        capture: _capture,
        capture_writes: 0
    };
}

/// The number of steps the shot in front of us holds. The film's own length, except in a capture run, where every shot
/// holds PP_DRIVE_CAPTURE_STEPS so twelve pictures can be written in five seconds.
function pp_drive_shot_len(_shot, _capture) {
    if (_capture) return PP_DRIVE_CAPTURE_STEPS;
    return _shot.steps;
}

/// Which page of a shot's captions is up. A page advances on its own share of the shot, because this room has no
/// dialogue box yet: R21b's scene is what makes a page wait for the player's press.
function pp_drive_page_index(_shot, _steps, _len) {
    var _count = array_length(_shot.pages);
    if (_count <= 0) return -1;
    if (_len <= 1) return 0;
    var _index = floor(_steps * _count / _len);
    if (_index >= _count) _index = _count - 1;
    if (_index < 0) _index = 0;
    return _index;
}

/// Enter the room's screen. The palette set is asked for by id, the art index is built if the frame has not built one
/// yet (this room can be the first screen of a capture run, and the font comes from the art index), and the film's
/// own numbers are printed once.
function pp_drive_enter(_params) {
    pp_look_palette(PP_DRIVE_PALETTE);
    if (!variable_struct_exists(global.pp, "art") || !is_struct(global.pp.art)) global.pp.art = pp_art_init();
    // The drive is a cutscene, and PPMode.cutscene is the mode the app machine already declares for one (spec 06). The
    // room draws its own frame, so the mode itself is a pass-through: registering it is what stops the app machine
    // stepping or drawing a screen this room has replaced. A second entry into the room finds it already registered.
    pp_drive_mode_register();
    global.pp_drive = pp_drive_state_new();
    var _shots = pp_drive_shots();
    show_debug_message("PP drive: " + string(array_length(_shots)) + " shots, "
        + string(pp_drive_total_steps()) + " steps, " + string(pp_drive_longest_shot())
        + " steps longest, palette " + string(pp_look_palette_id())
        + ", capture " + string(global.pp_drive.capture));
    if (!pp_drive_table_ok()) {
        show_debug_message("PP drive: the shot table does not agree with the shot list: sum "
            + string(pp_drive_total_steps()) + " of " + string(PP_DRIVE_TOTAL_STEPS)
            + ", shortest " + string(pp_drive_shortest_shot()) + ", longest " + string(pp_drive_longest_shot()));
    }
    return global.pp_drive;
}

/// One step of the film: the shot clock, then the hand over to the next shot when this one has spent its steps.
function pp_drive_step(_params) {
    var _st = global.pp_drive;
    if (!is_struct(_st) || _st.done) return;
    var _shots = pp_drive_shots();
    var _shot = _shots[_st.shot_index];
    var _len = pp_drive_shot_len(_shot, _st.capture);

    // Say the shot once, on its first step, with its duration and whatever it carries, so the run log is the film's
    // own account of itself and a capture can be read without the picture.
    if (_st.shots_logged != _st.shot_index) {
        _st.shots_logged = _st.shot_index;
        _st.pages_logged = -1;
        show_debug_message("PP drive: shot " + string(_shot.n) + " of " + string(array_length(_shots)) + " "
            + _shot.id + " (" + _shot.place + ") " + string(_shot.steps) + " steps"
            + ((_shot.sign != "") ? ", sign " + _shot.sign : "")
            + ((array_length(_shot.pages) > 0) ? ", " + string(array_length(_shot.pages)) + " pages" : ""));
    }

    _st.shot_steps += 1;
    _st.steps += 1;

    // A caption page is announced when it comes up, by the id the shot list names for it.
    var _page = pp_drive_page_index(_shot, _st.shot_steps, _len);
    if (_page != _st.pages_logged && _page >= 0) {
        _st.pages_logged = _page;
        show_debug_message("PP drive: page " + _shot.pages[_page]);
    }
    _st.page_index = _page;

    if (_st.shot_steps < _len) return;

    // The shot has spent its steps. Shot 12 ends the film, which is held on its last frame rather than looping: the
    // route is what follows it (R21b).
    if (_st.shot_index >= array_length(_shots) - 1) {
        _st.done = true;
        show_debug_message("PP drive: the film ended after " + string(_st.steps) + " steps");
        return;
    }
    _st.shot_index += 1;
    _st.shot_steps = 0;
    _st.page_index = -1;
}

/// The black level over the frame: 1 is fully black. Twelve step fades, in on the shots the shot list fades in on and
/// out on the two it fades out on.
function pp_drive_fade_level(_st, _shot, _len) {
    var _t = _st.shot_steps;
    if (_shot.n == 1 || _shot.n == 7) {
        if (_t < PP_DRIVE_FADE) return 1 - (_t / PP_DRIVE_FADE);
        return 0;
    }
    if (_shot.n == 6 || _shot.n == 12) {
        var _tail = _len - PP_DRIVE_FADE;
        if (_t > _tail) return min(1, (_t - _tail) / PP_DRIVE_FADE);
        return 0;
    }
    return 0;
}

/// Draw one frame of the drive.
function pp_drive_draw(_params) {
    var _st = global.pp_drive;
    if (!is_struct(_st)) return;
    var _shots = pp_drive_shots();
    var _shot = _shots[_st.shot_index];
    var _len = pp_drive_shot_len(_shot, _st.capture);
    var _progress = _st.shot_steps / max(1, _len);
    var _scroll = _st.steps * PP_DRIVE_ROAD_PX_PER_STEP;

    draw_set_alpha(1);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    switch (_shot.place) {
        case "city":      pp_drive_draw_city(_st, _shot, _progress, _scroll); break;
        case "gantry":    pp_drive_draw_gantry(_st, _shot, _progress, _scroll); break;
        case "motorway":  pp_drive_draw_motorway(_st, _shot, _progress, _scroll); break;
        case "cutting":   pp_drive_draw_cutting(_st, _shot, _progress, _scroll); break;
        case "cathedral": pp_drive_draw_cathedral(_st, _shot, _progress, _scroll); break;
        case "downland":  pp_drive_draw_downland(_st, _shot, _progress, _scroll); break;
        case "slip":      pp_drive_draw_slip(_st, _shot, _progress, _scroll); break;
        case "docks":     pp_drive_draw_docks(_st, _shot, _progress, _scroll); break;
        default:          pp_drive_draw_motorway(_st, _shot, _progress, _scroll); break;
    }

    if (_st.page_index >= 0 && array_length(_shot.pages) > 0) pp_drive_draw_caption(_shot, _st.page_index);

    var _fade = pp_drive_fade_level(_st, _shot, _len);
    if (_fade > 0) {
        draw_set_alpha(_fade);
        draw_set_colour(pp_role_colour("ink"));
        draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
        draw_set_alpha(1);
    }

    // Card R21a self check: with PP_DRIVE_CAPTURE set, the room writes one PNG of its own frame per shot from inside
    // the draw, so twelve distinct pictures are the game's own pixels and not a screen copy of whatever window sits on
    // top of it (the same method pp_ship and pp_title use). Unset, which is every real launch, this is one
    // environment read per frame and nothing is written.
    if (_st.capture && _st.shot_steps == PP_DRIVE_CAPTURE_AT) {
        var _name = "pp_drive_shot_" + pp_drive_pad2(_shot.n) + ".png";
        screen_save(_name);
        _st.capture_writes += 1;
        show_debug_message("PP drive: wrote " + _name + " from the room itself, shot " + string(_shot.n)
            + " " + _shot.id + ", step " + string(_st.shot_steps));
    }
}

/// Two digit zero padded number, for the frame files and for the meters on the road.
function pp_drive_pad2(_n) {
    var _v = floor(_n);
    if (_v < 0) _v = 0;
    if (_v < 10) return "0" + string(_v);
    return string(_v);
}

// ---------------------------------------------------------------------------------------------------------------
// The shared picture: sky, land, road, car, sign and rain. Every colour is a role from the room's set and never a
// literal (spec 13 rule 2), and every coordinate is rounded before it is drawn (spec 03 rule 3).

function pp_drive_band(_x1, _y1, _x2, _y2, _role) {
    draw_set_colour(pp_role_colour(_role));
    draw_rectangle(round(_x1), round(_y1), round(_x2), round(_y2), false);
}

/// A night sky: the darker of the set's two darks, with a moon and a handful of stars that shift by the scroll, so the
/// sky is never a flat still.
function pp_drive_sky(_role, _scroll, _moon_x) {
    pp_drive_band(0, 0, PP_FRAME_W - 1, 159, _role);
    pp_drive_band(round(_moon_x), 20, round(_moon_x) + 23, 43, "text");
    pp_drive_band(round(_moon_x) + 5, 26, round(_moon_x) + 11, 32, _role);
    for (var i = 0; i < 12; i += 1) {
        var _x = (i * 47 + floor(_scroll * 0.05)) mod PP_FRAME_W;
        var _y = 8 + ((i * 29) mod 88);
        pp_drive_band(_x, _y, _x + 1, _y + 1, "text");
    }
}

/// Stepped hills, drawn as sixteen columns so the silhouette is made of whole 16 pixel steps and reads as a NES
/// background rather than a curve.
function pp_drive_hills(_base_y, _role, _scroll, _amplitude) {
    for (var i = 0; i < 16; i += 1) {
        var _h = _amplitude + 10 * sin((i * 16 + _scroll * 0.15) / 70);
        pp_drive_band(i * 16, _base_y - round(_h), i * 16 + 15, _base_y, _role);
    }
}

/// The road, from its own top edge down, with the verge above it and one dashed centre line per 32 pixels of tarmac,
/// scrolled by the film's own clock.
function pp_drive_road(_top, _scroll) {
    pp_drive_band(0, _top - 8, PP_FRAME_W - 1, _top - 1, "dim");
    pp_drive_band(0, _top, PP_FRAME_W - 1, PP_FRAME_H - 1, "paper");
    pp_drive_band(0, _top, PP_FRAME_W - 1, _top + 1, "window_shadow");
    var _phase = round(_scroll) mod 32;
    for (var i = 0; i < 9; i += 1) {
        var _x = i * 32 - _phase;
        pp_drive_band(_x, _top + 22, _x + 15, _top + 24, "marker");
    }
}

/// The car, from outside and in long shot (spec 14: no interior shot, no face). The body bobs one pixel on the beat.
function pp_drive_car(_x, _y, _steps) {
    var _bob = round((sin(_steps / 29 * 6.28318) > 0.5) ? 1 : 0);
    var _bx = round(_x);
    var _by = round(_y) + _bob;
    pp_drive_band(_bx + 10, _by - 7, _bx + 52, _by - 1, "window_shadow");
    pp_drive_band(_bx + 14, _by - 5, _bx + 30, _by - 2, "window");
    pp_drive_band(_bx, _by, _bx + 62, _by + 14, "dim");
    pp_drive_band(_bx, _by + 7, _bx + 62, _by + 9, "window_edge");
    pp_drive_band(_bx, _by + 9, _bx + 3, _by + 12, "hazard");
    pp_drive_band(_bx + 7, _by + 13, _bx + 19, _by + 18, "paper");
    pp_drive_band(_bx + 43, _by + 13, _bx + 55, _by + 18, "paper");
}

/// The headlight pool and the beam that makes it. Drawn as whole steps rather than a gradient, because a gradient is
/// more colours than one screen may hold.
function pp_drive_headlight(_x, _y) {
    pp_drive_band(_x + 62, _y + 6, _x + 66, _y + 9, "accent");
    pp_drive_band(_x + 66, _y + 4, _x + 92, _y + 12, "marker_trail");
    pp_drive_band(_x + 92, _y + 2, _x + 120, _y + 15, "accent");
}

/// A gantry sign: the plate over the road, two posts down to the verge, SOUTHAMPTON in the 8x8 font and the miles as
/// the shot list counts them. The font is the project's one text face (spec 13), and the sign is legible whether or
/// not the art lane's spr_title_sign has landed.
function pp_drive_gantry_sign(_x, _miles, _width) {
    var _w = (is_undefined(_width) ? 168 : _width);
    var _left = round(_x);
    pp_drive_band(_left + 18, 96, _left + 21, 159, "paper");
    pp_drive_band(_left + _w - 21, 96, _left + _w - 18, 159, "paper");
    pp_drive_band(_left, 60, _left + _w, 95, "dim");
    pp_drive_band(_left, 60, _left + _w, 61, "text");
    pp_drive_band(_left, 94, _left + _w, 95, "text");
    if (pp_art_has("spr_pp_font8")) {
        pp_font_draw("SOUTHAMPTON", _left + 8, 66, 1);
        pp_font_draw(string(_miles), _left + _w - 24, 78, 1);
    }
}

/// Rain, from outside the car: diagonal streaks that fall and slide every step, so shot 4 is never a still frame.
function pp_drive_rain(_steps) {
    draw_set_colour(pp_role_colour("text"));
    for (var i = 0; i < 40; i += 1) {
        var _x = (i * 53 + _steps * 6) mod PP_FRAME_W;
        var _y = (i * 37 + _steps * 9) mod 160;
        if (_y < 12) _y += 12;
        draw_line(_x, _y, _x - 4, _y + 9);
    }
}

/// The wipers, seen from outside: two blades sweeping the windscreen on a cycle that is not the shot's own length, so
/// the sweep is visible in a captured frame and not only in motion.
function pp_drive_wipers(_steps) {
    var _sweep = (_steps mod 60) / 60;
    var _x = round(150 - 26 * sin(_sweep * 3.14159));
    draw_set_colour(pp_role_colour("text"));
    draw_line(_x, 176, _x + 26, 158);
    draw_line(_x + 4, 176, _x + 30, 158);
}

/// The bottom of screen caption, which is where every line spoken in the car goes (spec 14: no interior shot). The
/// placeholder text is the dialogue id the shot list names, because R21b authors the line itself.
function pp_drive_draw_caption(_shot, _page_index) {
    // Card t_89d60fe5: the empty page list and the page index are both refused on the line that indexes, so a shot whose
    // page list and its caller's idea of the page up disagree draws no caption instead of stopping the room at the index.
    // Shot 1 (bigben) carries no pages at all, which is the case that crashed a build of this file, so the refusal is
    // here and not only at the call site.
    var _count = array_length(_shot.pages);
    if (_count <= 0) return;
    if (_page_index < 0 || _page_index >= _count) return;
    var _page = _shot.pages[_page_index];
    pp_drive_band(8, 184, PP_FRAME_W - 9, 231, "window");
    pp_drive_band(8, 184, PP_FRAME_W - 9, 185, "text");
    pp_drive_band(8, 230, PP_FRAME_W - 9, 231, "text");
    if (pp_art_has("spr_pp_font8")) {
        pp_font_draw("[" + string(_page) + "]", 16, 196, 1);
        pp_font_draw("placeholder page", 16, 212, 1);
        pp_font_draw(string(_page_index + 1) + " of " + string(_count), 168, 212, 1);
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The eight places. Each one is a different picture on purpose: knowledge/DRIVE-SHOT-LIST.md section 4 counts the
// eight locations and says how the player knows the place moved, and the placeholder art has to carry that count.

/// Shots 1 and 2: Big Ben panning down into the street, then the street and the Thames with the car pulling away.
function pp_drive_draw_city(_st, _shot, _p, _scroll) {
    var _pan = (_shot.n == 1) ? round(48 * (1 - min(1, _p * 1.4))) : 0;
    pp_drive_sky("window", _scroll, 196);
    pp_drive_hills(120 + _pan, "window_shadow", _scroll, 12);
    // The Palace along the horizon, then the clock tower on top of it.
    pp_drive_band(0, 118 + _pan, PP_FRAME_W - 1, 141 + _pan, "paper");
    for (var i = 0; i < 9; i += 1) pp_drive_band(i * 28 + 6, 110 + _pan, i * 28 + 14, 118 + _pan, "paper");
    pp_drive_band(96, 46 + _pan, 143, 120 + _pan, "paper");
    pp_drive_band(100, 38 + _pan, 139, 46 + _pan, "dim");
    pp_drive_band(104, 58 + _pan, 135, 86 + _pan, "accent");
    pp_drive_band(118, 62 + _pan, 121, 80 + _pan, "text");
    pp_drive_band(108, 70 + _pan, 132, 73 + _pan, "text");
    pp_drive_road(176 + round(24 * (1 - _p)), _scroll);

    if (_shot.n == 1) {
        // The camera is still on the clock face, so the car is not in shot yet.
        return;
    }
    // The Thames, then the car pulling away from the kerb and shrinking.
    pp_drive_band(0, 142, PP_FRAME_W - 1, 165, "window");
    for (var j = 0; j < 8; j += 1) {
        var _rx = (j * 34 + round(_scroll * 0.4)) mod PP_FRAME_W;
        pp_drive_band(_rx, 148 + (j mod 3) * 4, _rx + 18, 149 + (j mod 3) * 4, "accent");
    }
    var _car_x = 40 + round(150 * _p);
    pp_drive_car(_car_x, 168, _st.steps);
    pp_drive_headlight(_car_x, 168);
}

/// Shot 3: the gantry, the sign at 55 miles and the road under it.
function pp_drive_draw_gantry(_st, _shot, _p, _scroll) {
    pp_drive_sky("window", _scroll, 210);
    pp_drive_hills(140, "window_shadow", _scroll, 10);
    pp_drive_band(0, 132, PP_FRAME_W - 1, 147, "dim");
    pp_drive_road(160, _scroll);
    pp_drive_gantry_sign(24 + round(24 * _p), 55, 168);
    pp_drive_car(46, 178, _st.steps);
    pp_drive_headlight(46, 178);
}

/// Shots 4, 5, 6 and 9: open motorway. The rain, the wipers, the radio pages and the passing sign are what tell them
/// apart, and each of those moves inside the shot.
function pp_drive_draw_motorway(_st, _shot, _p, _scroll) {
    pp_drive_sky("window", _scroll, 24);
    pp_drive_hills(136, "window_shadow", _scroll, 8);
    pp_drive_band(0, 128, PP_FRAME_W - 1, 150, "dim");
    pp_drive_road(158, _scroll);

    if (_shot.n == 4) {
        pp_drive_band(0, 0, PP_FRAME_W - 1, 159, "window_shadow");
        pp_drive_road(158, _scroll);
        pp_drive_rain(_st.shot_steps);
        pp_drive_car(150, 168, _st.steps);
        pp_drive_wipers(_st.shot_steps);
        pp_drive_headlight(150, 168);
        return;
    }

    // A car in long shot, small in the frame, with the sign the shot carries passing it.
    var _car_x = 96 - round(12 * sin(_p * 3.0));
    pp_drive_car(_car_x, 176, _st.steps);
    pp_drive_headlight(_car_x, 176);
    if (_shot.sign != "") {
        var _miles = 0;
        var _left = 0;
        if (_shot.sign == "43") { _miles = 43; _left = round(260 - 360 * _p); }
        if (_shot.sign == "30") { _miles = 30; _left = round(250 - 340 * _p); }
        if (_miles > 0) pp_drive_gantry_sign(_left, _miles, 150);
    }
}

/// Shot 7: Twyford Down, the chalk cutting, one headlight pool and no sky worth the name.
function pp_drive_draw_cutting(_st, _shot, _p, _scroll) {
    pp_drive_band(0, 0, PP_FRAME_W - 1, 239, "window_shadow");
    pp_drive_band(0, 0, 47, 239, "text");
    pp_drive_band(208, 0, PP_FRAME_W - 1, 239, "text");
    pp_drive_band(47, 0, 58, 239, "dim");
    pp_drive_band(197, 0, 208, 239, "dim");
    pp_drive_road(150, _scroll);
    for (var i = 0; i < 6; i += 1) {
        var _y = 20 + i * 34 - round(_scroll * 0.4) mod 34;
        pp_drive_band(8, _y, 40, _y + 2, "dim");
        pp_drive_band(214, _y + 10, 246, _y + 12, "dim");
    }
    pp_drive_car(104, 170, _st.steps);
    pp_drive_headlight(104, 170);
}

/// Shot 8: Winchester Cathedral far off, one caption, the moon behind the tower.
function pp_drive_draw_cathedral(_st, _shot, _p, _scroll) {
    pp_drive_sky("window", _scroll, 214);
    pp_drive_hills(150, "window_shadow", _scroll, 8);
    pp_drive_band(0, 146, PP_FRAME_W - 1, 159, "dim");
    // The nave, long and low, and the square tower on it.
    pp_drive_band(70, 116, 186, 150, "paper");
    pp_drive_band(150, 84, 178, 150, "paper");
    pp_drive_band(152, 78, 176, 84, "dim");
    pp_drive_band(158, 92, 170, 104, "accent");
    pp_drive_road(162, _scroll);
    pp_drive_car(88, 180, _st.steps);
    pp_drive_headlight(88, 180);
}

/// Shot 10: the downland, the storm keeping pace over the car, and the two frame lightning flash the title's own
/// flash palette taught us to keep short.
function pp_drive_draw_downland(_st, _shot, _p, _scroll) {
    var _flash = ((_st.shot_steps mod 480) < 2);
    pp_drive_sky(_flash ? "text" : "window", _scroll, 40);
    pp_drive_hills(126, _flash ? "paper" : "window_shadow", _scroll, 14);
    pp_drive_band(0, 118, PP_FRAME_W - 1, 150, _flash ? "window_shadow" : "window");
    pp_drive_band(0, 138, PP_FRAME_W - 1, 159, "dim");
    // The chalk horse on the hill, drawn in whole steps (spec 14: an original figure, not a photograph of one).
    pp_drive_band(52, 122, 84, 124, "text");
    pp_drive_band(56, 116, 62, 122, "text");
    pp_drive_band(72, 118, 78, 122, "text");
    pp_drive_road(160, _scroll);
    // The personal storm cloud, which follows the car and never the world.
    pp_drive_band(120, 30, 176, 44, "window_shadow");
    pp_drive_band(112, 38, 184, 50, "window_shadow");
    if (_flash) pp_drive_band(140, 50, 143, 88, "marker");
    pp_drive_car(96, 172, _st.steps);
    pp_drive_headlight(96, 172);
}

/// Shot 11: the slip road, the sign at 20 miles and the headlights turning off.
function pp_drive_draw_slip(_st, _shot, _p, _scroll) {
    pp_drive_sky("window", _scroll, 32);
    pp_drive_hills(132, "window_shadow", _scroll, 8);
    pp_drive_band(0, 126, PP_FRAME_W - 1, 150, "dim");
    // The road narrows: one lane instead of two, its edge running in from both sides.
    pp_drive_band(0, 150, PP_FRAME_W - 1, 159, "dim");
    pp_drive_band(0, 160, PP_FRAME_W - 1, PP_FRAME_H - 1, "paper");
    var _narrow = round(40 * _p);
    pp_drive_band(0, 160, 26 + _narrow, 239, "dim");
    pp_drive_band(230 - _narrow, 160, PP_FRAME_W - 1, 239, "dim");
    pp_drive_band(0, 160, PP_FRAME_W - 1, 161, "window_shadow");
    var _phase = round(_scroll) mod 32;
    for (var i = 0; i < 9; i += 1) {
        var _x = i * 32 - _phase;
        pp_drive_band(_x, 182, _x + 15, 184, "marker");
    }
    pp_drive_gantry_sign(20 + round(20 * _p), 20, 150);
    pp_drive_car(92, 190, _st.steps);
    pp_drive_headlight(92, 190);
}

/// Shot 12: the docks. Cranes, containers and the ship lit at the quay, then the fade to black the film ends on.
function pp_drive_draw_docks(_st, _shot, _p, _scroll) {
    pp_drive_band(0, 0, PP_FRAME_W - 1, 239, "window");
    pp_drive_band(0, 108, PP_FRAME_W - 1, 239, "window_shadow");
    // Four cranes, each one stepping along the quay as the shot runs.
    for (var i = 0; i < 4; i += 1) {
        var _cx = 12 + i * 62 - round(_p * 12);
        pp_drive_band(_cx, 58, _cx + 4, 150, "dim");
        pp_drive_band(_cx - 10, 58, _cx + 34, 62, "dim");
        pp_drive_band(_cx + 30, 62, _cx + 34, 96, "dim");
        pp_drive_band(_cx - 10, 62, _cx - 6, 74, "dim");
    }
    // Containers in two rows on the quay.
    for (var j = 0; j < 7; j += 1) {
        var _kx = j * 38 - (round(_scroll * 0.6) mod 38);
        var _role = ((j mod 3) == 0) ? "hazard" : (((j mod 3) == 1) ? "marker_trail" : "dim");
        pp_drive_band(_kx, 150, _kx + 34, 166, _role);
        pp_drive_band(_kx + 4, 138, _kx + 30, 150, _role);
    }
    // The ship at the quay: hull, superstructure, and a lit row of windows that flickers as the shot runs.
    pp_drive_band(40, 168, 232, 200, "paper");
    pp_drive_band(56, 140, 96, 168, "paper");
    pp_drive_band(160, 148, 208, 168, "paper");
    for (var k = 0; k < 12; k += 1) {
        var _wx = 48 + k * 15;
        var _lit = (((k + floor(_st.shot_steps / 20)) mod 3) != 0);
        if (_lit) pp_drive_band(_wx, 176, _wx + 5, 181, "marker");
    }
    pp_drive_band(0, 200, PP_FRAME_W - 1, 239, "window");
    for (var m = 0; m < 10; m += 1) {
        var _rx = (m * 29 + round(_scroll * 0.3)) mod PP_FRAME_W;
        pp_drive_band(_rx, 206 + (m mod 4) * 6, _rx + 14, 207 + (m mod 4) * 6, "accent");
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The room door.

/// Register the drive's app mode: PPMode.cutscene, a pass-through whose step and draw do nothing, because the room's
/// own object owns the frame (the same division rm_pp_title and obj_pp_title use). Registering twice is refused by the
/// app machine, so the check comes first. Called by the door, which runs before the room exists, and by the room's own
/// enter, so whichever comes first registers it.
function pp_drive_mode_register() {
    if (!is_struct(global.pp) || !is_struct(global.pp.app) || !is_struct(global.pp.app.modes)) return false;
    if (variable_struct_exists(global.pp.app.modes, string(PPMode.cutscene))) return true;
    pp_app_register(PPMode.cutscene, {
        step: function(_p) { return; },
        draw: function(_p) { return; }
    });
    return true;
}

/// Move the frame to rm_pp_drive through the app's own room door, as a cutscene (pp_app_enter_room with
/// PPMode.cutscene). The room's object owns the screen from there, which is how rm_pp_title works, so nothing here
/// draws the drive itself. A build without the room answers false instead of moving anywhere.
function pp_drive_goto_room() {
    var _room = asset_get_index("rm_pp_drive");
    if (_room < 0) {
        show_debug_message("PP drive: rm_pp_drive is not in this build");
        return false;
    }
    if (room == _room) return true;
    // The mode is registered before the room door is asked for it: pp_app_enter_room refuses a mode nobody registered,
    // and the room cannot register its own before it exists.
    pp_drive_mode_register();
    return pp_app_enter_room(PPMode.cutscene, {}, _room);
}
