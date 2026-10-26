/// pp_title: the title screen, the night drive and the menu (spec 14, its night drive addendum and plan v2 section 2).
///
/// The screen is one scene drawn from the title art: seven seamless night layers that scroll at the speeds
/// TITLE-COORD.md fixes, the battered hatchback with its two passengers, Zander's storm cloud, the counting down
/// road sign, the logo, and then the menu inside the FF1 style window. The state of the screen lives here, in one
/// struct, and the app mode machine owns the frame (spec 01).
///
/// The opening shot pans down from Big Ben into the drive and plays once, on the first boot only; a marker file in
/// the save area records that it has been seen, so every later launch goes straight to the title card.
///
/// Everything is written from specs\14-title-screen-drive.md, its addendum, TITLE-COORD.md and the manual pages
/// named in each function. The art is this project's own; nothing is copied from any existing game.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone".

/// The logo takes one second to arrive (spec 14: it fades in over 1 second, then shimmers).
#macro PP_TITLE_FADE_STEPS 60
// Beat macros derived from data\title_timing.json by tools\apply_title_timing.py: edit the json, not these.
#macro PP_TITLE_BPM 126
#macro PP_TITLE_BEAT_STEPS 29
#macro PP_TITLE_BAR_STEPS 87
#macro PP_TITLE_SCROLL_PX_PER_STEP 0.552
#macro PP_TITLE_BOB_PX 1
#macro PP_TITLE_BOB_STEPS 29
#macro PP_TITLE_EXHAUST_STEPS 58
#macro PP_TITLE_TWINKLE_PERIOD 87
#macro PP_TITLE_FLASH_STEPS 2
#macro PP_TITLE_FLASH_MIN_STEPS 696
#macro PP_TITLE_FLASH_MAX_STEPS 696
#macro PP_TITLE_SHIMMER_STEPS 24
#macro PP_TITLE_SHIMMER_PERIOD 348
#macro PP_TITLE_BLINK_STEPS 29
#macro PP_TITLE_CURSOR_PERIOD 14
// The intro after NEW GAME (card INTRO-1): the camera pans up out of the road over three seconds with an ease
// out, the world fades four palette steps to black, the sky fades the same four steps and leaves the stars, the
// stars are held for a beat, and then the crawl runs. Every number here is measured in steps at 60 a second.
#macro PP_TITLE_INTRO_PAN_STEPS 180
#macro PP_TITLE_INTRO_PAN_PX 240
#macro PP_TITLE_INTRO_FADE_STEP_STEPS 18
#macro PP_TITLE_INTRO_WORLD_FADE 180
#macro PP_TITLE_INTRO_SKY_FADE 252
#macro PP_TITLE_INTRO_TEXT 540
#macro PP_TITLE_INTRO_HOLD 60
// The intro step the self check's mid crawl frame is written on (card TEXT-REVEAL-2): 360 steps into the crawl, which
// is six seconds of typing, so the frame shows rows filling rather than a finished or an empty screen.
#macro PP_TITLE_CRAWL_CAPTURE_MID 900
// The three steps the scroll self check's own frames are written on (card TEMPO-1, review round 1): ten beats in, then
// a half beat and a whole beat after it. Ten beats clears the opening shot and the logo fade on either a first boot or
// a later one, and the gaps are what make the measurement honest: half a beat is 0.25 s, which at 126 bpm is 8 px of
// road, comfortably inside the 16 px dash period, and three frames on one lattice also cover the card's half second
// (two gaps) without ever asking a correlation to resolve a shift the art repeats every 16 px.
#macro PP_TITLE_SCROLL_CAPTURE_FIRST (PP_TITLE_BEAT_STEPS * 10)
#macro PP_TITLE_SCROLL_CAPTURE_GAP (PP_TITLE_BEAT_STEPS div 2)
#macro PP_TITLE_INTRO_COLUMNS 32
#macro PP_TITLE_INTRO_LINES 6
#macro PP_TITLE_INTRO_LINE_H 12
#macro PP_TITLE_INTRO_TEXT_Y 132
// The crawl's own timing. It is not a reveal: the numbers are handed to pp_text (the one machine) as settings when the
// crawl starts, so this module keeps the title's values and pp_text keeps the mechanism (spec 14, addendum 2026-10-22).
#macro PP_TITLE_TEXT_CPS 18
#macro PP_TITLE_TEXT_PAUSE 72
#macro PP_TITLE_TEXT_BLIP_EVERY 3
// The star twinkle is one bar, and a bar is the only number it has: PP_TITLE_TWINKLE_PERIOD in the beat group above
// is data\title_timing.json's stars.steps, which tools\apply_title_timing.py refuses to write unless it equals
// PP_TITLE_BAR_STEPS. The intro's stars and the title card's own sky both turn over on that one number, so there is
// no second twinkle rate anywhere in the file (card TEMPO-1, review round 1).
// The theme ducks this far under the crawl, and comes back up when the crawl ends or is skipped.
#macro PP_TITLE_DUCK_DB 6
// Where the logo, the prompt, the window and its rows sit, in frame pixels. The window is the classic NES JRPG
// box, low and centred, sized in whole 8x8 tiles (18 by 9) because the art lane's spr_pp_window is nine tiles and
// scaling it would tear its edges. The four rows sit inside its 8 pixel border, and the cursor is against that edge.
// Two of these numbers are also palette boundaries (card t_a1170172): the frame is drawn in four 16 px row bands, so
// the logo starts at row 0 and ends at row 63, inside the first band group, and the car sits from row 193 down, so
// its 32 rows stay in the road's bands and never put a car colour in the field's. Moving either without moving the
// band plan in data/palettes/scene_title.json takes the frame off the palette it is drawn in.
#macro PP_TITLE_LOGO_X 16
#macro PP_TITLE_LOGO_Y 0
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
// The copyright line: one quiet row at the very bottom of the frame.
#macro PP_TITLE_COPY_TEXT "(c) 2026 NAYILINIST"
#macro PP_TITLE_COPY_Y 228
// The opening shot: a three second pan down out of the Big Ben frame, and a dissolve over the last three quarters
// of a second. Any key skips it.
#macro PP_TITLE_OPEN_STEPS 180
#macro PP_TITLE_OPEN_PAN 24
#macro PP_TITLE_OPEN_FADE 45
// Lightning: the scene swaps to the flash palette for PP_TITLE_FLASH_STEPS frames (two, so a 60th of a second twice)
// every 8 bars of the theme, which is 696 steps, 11.6 s at 126 bpm in three four time. FLASH_MIN and FLASH_MAX are
// both that number, so the wait is the tempo and not a random 8 to 12 seconds any more. The wait is still drawn from
// the title's own seeded stream, so the same launch flashes at the same moments.
#macro PP_TITLE_FLASH_SEED 20261021
// The marker that says the opening has been seen. It lands in the save area beside the slot, so nothing here
// writes outside the sandbox.
#macro PP_TITLE_SEEN_FILE "pp_title_seen.txt"
// The car sits at the left of the road, and the headlight cone is on the tarmac ahead of it.
#macro PP_TITLE_CAR_X 76
#macro PP_TITLE_CAR_Y 193
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
    var _timing = pp_title_intro_timing();
    var _s = {
        steps: 0,
        phase: _phase,
        menu_index: 0,
        scroll: 0,
        logo_alpha: 0,
        open: 0,
        flash_left: 0,
        flash_wait: 0,
        flash_count: 0,
        rng: pp_rng_new(PP_TITLE_FLASH_SEED),
        data: pp_title_data(),
        // The intro's own clock and levels. The pan is a pixel offset; the two fade levels are 0 (untouched) to
        // 4 (black), one per NES brightness row the strips were drawn with.
        intro: 0,
        intro_pan: 0,
        intro_world: 0,
        intro_sky: 0,
        intro_hold: 0,
        ducked: false,
        crawl: undefined,
        stars: pp_title_intro_stars(),
        text_beats: pp_title_intro_beats(),
        timing: _timing,
        twinkle_period: _timing.twinkle_period,
        char_steps: _timing.char_steps,
        beat_pause: _timing.beat_pause,
        blip_every: _timing.blip_every
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

    // The storm flashes on its own clock in every phase but the intro, which is a cutscene and owns its own light.
    if (_s.phase != "intro") pp_title_step_lightning(_s);

    // Leaving is a real phase and not a fall through: the run has been asked for and the frame is inside the twelve
    // step fade (spec 01 rule 2), so the title must not read a key or start a second run on the way out.
    if (_s.phase == "leaving") return;

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
        // START opens the menu, and the confirm key does too: the row on screen says PRESS START, the pad's start is
        // the menu action in spec 02's bindings, and Z or ENTER are the two keys spec 14's logo names.
        if (pp_pressed("confirm") || pp_pressed("menu")) {
            _s.phase = "menu";
            // The first row, by name and not by position: a data file that reorders the menu still lands the cursor
            // on NEW GAME (spec 14: the menu opens on NEW GAME).
            _s.menu_index = pp_title_menu_index(_s, "NEW GAME");
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
            pp_audio_play("menu_cancel");
        }
        return;
    }

    if (_s.phase == "intro") {
        pp_title_step_intro(_s);
        return;
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

/// The row a name sits on in the menu table, or 0 when the table does not carry it. The cursor starts on a row by
/// name because the table can come from data\\title.json, and a reordered file must still open on NEW GAME.
function pp_title_menu_index(_s, _name) {
    if (!is_struct(_s) || !is_struct(_s.data) || !is_array(_s.data.menu)) return 0;
    for (var i = 0; i < array_length(_s.data.menu); i += 1) {
        if (string(_s.data.menu[i]) == string(_name)) return i;
    }
    return 0;
}

/// Move the frame to the room a run is played in. Both title paths end in the overworld and that mode is drawn by the
/// persistent obj_pp_game, so the room only has to be the one the run's frame lives in, which is rm_pp_ship.
/// asset_get_index keeps a build that predates the room compiling; the app's own request has named the mode either way.
function pp_title_goto_run_room() {
    var _room = asset_get_index(PP_NEW_GAME_ROOM);
    if (_room != -1 && room != _room) room_goto(_room);
    return true;
}

/// The route steps a capture holds (card DEMO-WALK). data\demo\run_001.json names the ids in its game.env, one or more
/// comma separated, and every id it names is a step the crawl does not hand to in that run. The day 1 video holds
/// "drive": the drive is a 178 second cutscene whose twelve caption pages each wait for a press, so it cannot be the
/// shot a 71 s recording is cut from, and holding it leaves the new run's own map standing, which is the handoff this
/// screen made before the route existed. Empty in every real launch, so a player's run takes the route as the file says.
/// Split the same way every other PP_ environment name is, so the macro's definition is not itself a use of the name.
#macro PP_ROUTE_HOLD "PP_" + "ROUTE_HOLD"

/// Is this route step held in this run? One environment read per handoff, and none at all when the name is unset.
function pp_title_route_held(_id) {
    if (string(_id) == "") return false;
    var _held = environment_get_variable(PP_ROUTE_HOLD);
    if (_held == "") return false;
    var _parts = string_split(_held, ",");
    for (var i = 0; i < array_length(_parts); i += 1) {
        if (string_trim(_parts[i]) == string(_id)) return true;
    }
    return false;
}

/// What follows the crawl on the demo's route (data/slice.json, card R24). The crawl is the last thing this screen
/// plays, so the step after it is where the run begins, and the route is the one place that says what that step is.
/// A route whose next step is not in the build yet, which is the drive until card R21 writes it, leaves the new run's
/// own map standing: that is the handoff this screen made before the route existed, and the reason is printed once.
function pp_title_crawl_handoff() {
    // When the demo walk is switched on, the walk takes every step's handoff (card R24), so the screen does not take
    // this one as well: one owner per handoff keeps the drive scene from being asked for twice.
    if (pp_slice_walk_enabled()) return false;
    var _crawl = pp_slice_route_row("crawl");
    if (!is_struct(_crawl) || !variable_struct_exists(_crawl, "next")) return false;
    var _next_id = string(_crawl.next);
    if (_next_id == "") return false;
    // A step this run holds is not taken (card DEMO-WALK), and the run room stands in its place. The line names both
    // the step and the variable, so the recording's own log answers why the route stopped here.
    if (pp_title_route_held(_next_id)) {
        show_debug_message("PP title: the route's step " + _next_id + " is held by " + PP_ROUTE_HOLD
            + " in this run, so the run room stands and the crawl did not hand to the route");
        return false;
    }
    var _next = pp_slice_route_row(_next_id);
    if (!is_struct(_next)) {
        show_debug_message("PP title: the route after the crawl names " + _next_id + ", which is not in the route");
        return false;
    }
    var _why = pp_slice_handoff(_next);
    if (_why != "") {
        show_debug_message("PP title: the route's next step " + _next_id + " cannot be taken yet: " + _why);
        return false;
    }
    show_debug_message("PP title: the crawl handed to the route's step " + _next_id);
    return true;
}

/// What the chosen row does.
function pp_title_select(_s) {
    var _row = _s.menu_index;
    var _name = "";
    if (_row >= 0 && _row < array_length(_s.data.menu)) _name = _s.data.menu[_row];
    if (_name == "NEW GAME") {
        pp_audio_play("menu_select");
        // The intro runs before the run starts (card INTRO-1): pan up, fade, stars, crawl. The run itself, its
        // ledger and rm_pp_ship are only entered when the crawl ends.
        _s.phase = "intro";
        _s.intro = 0;
        _s.intro_pan = 0;
        _s.intro_world = 0;
        _s.intro_sky = 0;
        _s.intro_hold = 0;
        _s.crawl = pp_title_crawl_new(_s);
        show_debug_message("PP title: intro started, pan " + string(PP_TITLE_INTRO_PAN_STEPS) + " steps, "
            + string(array_length(_s.stars)) + " stars, " + string(array_length(_s.text_beats)) + " crawl lines");
        return;
    }
    if (_name == "CONTINUE") {
        // The row is greyed when there is no save, so choosing it does nothing but make a noise (spec 11: CONTINUE
        // is only offered while the slot holds a run that was read and validated).
        if (!pp_save_ready()) {
            pp_audio_play("menu_move");
            return;
        }
        pp_audio_play("menu_select");
        // Applying the save puts the ledger, the map and the saved tile back and asks the app for the overworld, but
        // it does not move the room: pp_save is card R26's file and this card may not edit it, so the one line the
        // load needs is taken here, on the same room a new run is played in.
        if (pp_save_apply()) {
            _s.phase = "leaving";
            pp_title_goto_run_room();
        }
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

    // The clear is the scene's own backdrop, $0F black, and not the design palette's ink: #0b0b0f is a bookkeeping
    // colour, not a PPU output, and the four rows the layers leave open above the road used to show it (card
    // t_a1170172, which measured 1314 pixels of it). A hole in the art now shows black, which the frame is allowed.
    draw_set_colour(PP_TITLE_BACKDROP);
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);

    // The intro is its own shot, drawn from the same layers but with a camera that has left the road, so it does
    // not go through the title card's draws (card INTRO-1).
    if (_s.phase == "intro") {
        pp_title_draw_intro_scene(_s, _d);
        return;
    }

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

/// The frame an animation is drawn on. Every layer but the sky is on the art index's own fps. The sky's two frames are
/// the star field and its twinkle variant, and a twinkle is on the bar, so the sky turns over on PP_TITLE_BAR_STEPS
/// rather than on the index's 2 fps, which is a 30 step turn and lands on no beat of the theme at all: 60 steps for the
/// pair, against a bar of 87 (review round 1, card TEMPO-1). The two fade twins and the flash twin carry the same two
/// frames, so they are matched by prefix.
function pp_title_layer_frame(_name, _steps) {
    if (string_pos("title_L1_sky", _name) == 1) {
        var _frames = pp_art_frames(_name);
        if (_frames > 1) return floor(_steps / PP_TITLE_BAR_STEPS) mod _frames;
        return 0;
    }
    return pp_art_frame_at(_name, _steps);
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
        pp_art_layer(_name, pp_title_layer_frame(_name, _s.steps), _layer.y, _offset, PP_FRAME_W, _info.frame_h);
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
    // A road sign never changes while it is on screen. Each pass of the verge tile is a new sign further down the
    // M3, so the plate follows the lap: the next sign names the next city and a smaller distance.
    var _lap = floor((_s.scroll * _verge.speed) / 512);
    for (var shift = -512; shift <= 512; shift += 512) {
        var _x = PP_TITLE_SIGN_X - _offset + shift;
        var _index = (_lap + (shift div 512) + 400) mod 4;
        if (_x > -100 && _x < PP_FRAME_W) {
            pp_art_draw(_name, _index, _x, _verge.y + PP_TITLE_SIGN_Y, PP_UNTINTED, 1);
        }
    }
}

/// The headlight cone on the tarmac ahead of the car.
function pp_title_draw_cone(_s, _d, _flash) {
    var _name = pp_title_flash_name("spr_title_cone", _flash);
    if (!pp_art_has(_name)) return;
    pp_art_draw(_name, 0, _d.cone_x, PP_TITLE_CONE_Y, PP_UNTINTED, 1);
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
    pp_art_draw("title_BG_bigben", 0, 0, _y, PP_UNTINTED, _alpha);
}

/// The car, its wheels, its exhaust and the empty dark glass: nobody is inside it.
function pp_title_draw_car(_s, _d) {
    if (!pp_art_has("spr_title_car")) return;
    var _x = _d.car_x;
    var _y = _d.car_y;

    // The exhaust: one puff cycle every two beats, so a puff leaves the pipe on every other beat of the theme.
    if (pp_art_has("spr_title_exhaust")) {
        var _puff_frames = max(1, pp_art_frames("spr_title_exhaust"));
        var _puff_phase = (_s.steps mod PP_TITLE_EXHAUST_STEPS);
        var _puff = min(_puff_frames - 1, floor(_puff_phase * _puff_frames / PP_TITLE_EXHAUST_STEPS));
        pp_art_draw("spr_title_exhaust", _puff, _x, _y + 14, PP_UNTINTED, 1);
    }

    // The v2 car carries its own wheels, baked into the sprite so each one sits in its arch and cannot drift,
    // and the frames turn those spokes. There is no separate wheel sprite on the title any more. The frames run one
    // full turn a beat, and the body rides PP_TITLE_BOB_PX high on the second half of each beat (card TEMPO-1).
    var _car_frames = max(1, pp_art_frames("spr_title_car"));
    var _body = floor(_s.steps * _car_frames / PP_TITLE_BEAT_STEPS) mod _car_frames;
    var _bob = 0;
    if ((_s.steps mod PP_TITLE_BOB_STEPS) >= PP_TITLE_BOB_STEPS / 2) _bob = PP_TITLE_BOB_PX;
    pp_art_draw("spr_title_car", _body, _x, _y - _bob, PP_UNTINTED, 1);

    // The cast is off the title as of TS2-ART-A (Nayil: the car shows only its exterior, no faces). The
    // sprites spr_title_konrad, spr_title_zander and spr_title_bubble stay in game\sprites_src\title for the
    // interior scenes later; the title simply does not draw them. Konrad and Zander are the two car figures,
    // named after the adopted cast (CHARACTER-BIBLE); the retired picks Ronan Harrow and Theo Skye are gone.
}

/// Zander's storm cloud, which follows the car. The lightning itself is the screen's clock (pp_title_step_lightning);
/// the cloud simply lights up while a flash is on.
function pp_title_draw_cloud(_s, _d, _flash) {
    if (!pp_art_has("spr_title_cloud")) return;
    var _index = 0;
    if (_flash) {
        _index = 2;
    } else {
        // Zander's cloud drifts one frame a bar, so it turns over with the storm's own slow clock.
        _index = floor(_s.steps / PP_TITLE_BAR_STEPS) mod 2;
    }
    pp_art_draw("spr_title_cloud", _index, _d.car_x + 64, 80, PP_UNTINTED, 1);
}

/// The logo: it fades in over a second, then a gold shimmer passes over it once every four bars (PP_TITLE_SHIMMER_PERIOD
/// steps, 5.7 s at 126 bpm, not the four seconds the comment here used to claim).
function pp_title_draw_logo(_s) {
    if (!pp_art_has("spr_pp_title_logo")) return;
    var _index = 0;
    if ((_s.steps mod PP_TITLE_SHIMMER_PERIOD) < PP_TITLE_SHIMMER_STEPS) _index = 1;
    pp_art_draw("spr_pp_title_logo", _index, PP_TITLE_LOGO_X, PP_TITLE_LOGO_Y, PP_UNTINTED, _s.logo_alpha);
}

/// The words: the prompt, the menu in its window, the settings placeholder, or the intro crawl.
function pp_title_draw_words(_s, _d) {
    if (_s.phase == "settings") {
        pp_title_draw_settings(_s);
        return;
    }
    if (_s.phase == "prompt") {
        if (floor(_s.steps / PP_TITLE_BLINK_STEPS) mod 2 == 0) {
            pp_font_draw_centre("PRESS START", PP_FRAME_W / 2, PP_TITLE_PROMPT_Y, 1);
        }
        pp_title_draw_copy();
        return;
    }
    // The menu, inside the window. A row that cannot be chosen is marked by a rule through it in the ground band's
    // dark green, because the font sheet carries one ink and a tint would be a colour the PPU cannot output
    // (card t_a1170172, review round 1 item 3). The disabled row still answers a press with the move cue only.
    pp_title_draw_menu_window();
    var _has_save = pp_title_has_save();
    for (var i = 0; i < array_length(_d.menu); i += 1) {
        var _label = _d.menu[i];
        var _cx = PP_TITLE_MENU_WIN_X + PP_TITLE_MENU_WIN_W / 2;
        var _cy = PP_TITLE_MENU_ROW_Y + i * PP_TITLE_MENU_STEP;
        if (_label == "CONTINUE" && !_has_save) {
            pp_title_draw_disabled(_label, _cx, _cy);
        } else {
            pp_font_draw_centre(_label, _cx, _cy, 1);
        }
    }
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_TITLE_MENU_WIN_X + PP_TITLE_CURSOR_X,
                    PP_TITLE_MENU_ROW_Y + _s.menu_index * PP_TITLE_MENU_STEP, PP_UNTINTED, 1);
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
/// build, and it is the same shadow line and white border over a black field the sheet carries.
function pp_title_draw_window_plain(_x, _y, _w, _h) {
    draw_set_colour(PP_TITLE_BACKDROP);
    draw_rectangle(_x + 2, _y + 2, _x + _w - 2, _y + _h - 2, false);
    draw_set_colour(PP_TITLE_DIM);
    draw_rectangle(_x, _y, _x + _w - 1, _y + _h - 1, true);
    draw_set_colour(PP_TITLE_WHITE);
    draw_rectangle(_x + 1, _y + 1, _x + _w - 2, _y + _h - 2, true);
}

/// The copyright line: one quiet row at the bottom of the frame, on every phase but the opening. The font carries one
/// ink, so the line is the same white as the menu and sits behind the frame rather than in it.
function pp_title_draw_copy() {
    pp_font_draw_centre(PP_TITLE_COPY_TEXT, PP_FRAME_W / 2, PP_TITLE_COPY_Y, 1);
}

/// A label that cannot be chosen: the font's one ink with a 1 px rule through it, in the ground band's dark green.
/// The font sheet is 368x8 with one ink and no second weight, and a tint is a multiply that produced #7b7b7b, a value
/// no PPU can output (card t_a1170172). A rule in $0B is a colour both ground bands declare, so "off" reads on the
/// hardware instead of only in the code. Returns the width drawn.
function pp_title_draw_disabled(_text, _centre_x, _y) {
    var _w = pp_font_width(_text);
    var _x = _centre_x - floor(_w / 2);
    pp_font_draw(_text, _x, _y, 1);
    draw_set_colour(PP_TITLE_DIM);
    draw_line_width(_x, _y + 4, _x + _w - 1, _y + 4, 1);
    draw_set_colour(PP_TITLE_WHITE);
    return _w;
}

/// The settings placeholder: a title and one row, BACK, inside the same window frame as the menu (26 by 9 tiles).
function pp_title_draw_settings(_s) {
    if (!pp_window_draw(24, 84, 26, 9, 1)) pp_title_draw_window_plain(24, 84, 208, 72);
    draw_set_alpha(1);
    pp_font_draw_centre("SETTINGS", PP_FRAME_W / 2, 92, 1);
    pp_title_draw_disabled("NOTHING HERE YET", PP_FRAME_W / 2, 108);
    pp_font_draw_centre("BACK", PP_FRAME_W / 2, 128, 1);
    if (pp_art_has("spr_pp_menu_cursor")) {
        var _cursor = floor(_s.steps / PP_TITLE_CURSOR_PERIOD) mod 2;
        pp_art_draw("spr_pp_menu_cursor", _cursor, PP_FRAME_W / 2 - 40, 128, PP_UNTINTED, 1);
    }
    pp_title_draw_copy();
}

// ---------------------------------------------------------------------------------------------------------------
// The intro after NEW GAME (card INTRO-1): pan up out of the road, fade the world, fade the sky to the stars, then
// the crawl. Its data is data\intro_text.json (the crawl), data\intro_stars.json (where the stars stand) and
// data\title_timing.json (the beat the twinkles are measured against). Each file is optional: a build without it
// still runs the shot, with the built in numbers below.

/// Read the first of several candidate paths that exists, relative to the working directory. The bundle ships the data
/// files at the root of the game folder while a dev checkout may carry them under datafiles/, and the first build of
/// this shot read neither: it ran with zero stars and two fallback lines, which is how the difference was found.
function pp_title_read_any(_paths) {
    for (var i = 0; i < array_length(_paths); i += 1) {
        var _d = pp_art_read_json(_paths[i]);
        if (is_struct(_d)) return _d;
    }
    return undefined;
}

/// The timing table for the intro. A missing or unreadable file gives the numbers the card names.
function pp_title_intro_timing() {
    var _out = {
        bpm: 126,
        twinkle_period: PP_TITLE_TWINKLE_PERIOD,
        char_steps: 60 / PP_TITLE_TEXT_CPS,
        beat_pause: PP_TITLE_TEXT_PAUSE,
        blip_every: PP_TITLE_TEXT_BLIP_EVERY,
        lines_on_screen: PP_TITLE_INTRO_LINES
    };
    var _d = pp_title_read_any(["datafiles/title_timing.json", "title_timing.json"]);
    if (!is_struct(_d)) return _out;
    if (variable_struct_exists(_d, "bpm") && _d.bpm > 0) _out.bpm = _d.bpm;
    // The twinkle is on the bar, and the bar is the only source: stars.steps is what
    // tools\apply_title_timing.py writes as PP_TITLE_TWINKLE_PERIOD, and that script refuses to write it unless it
    // equals bar_steps, so reading either one gives the same value. Reading stars.steps first means a json edit
    // needs no rebuild of the macro to take effect, and there is no second twinkle rate for the two to disagree on.
    // Review round 1 found this branch computing four beats (114 steps) from intro.twinkle_beats while the card's own
    // stars.steps said 86; that key is gone from the file.
    if (variable_struct_exists(_d, "bar_steps") && _d.bar_steps > 0) _out.twinkle_period = _d.bar_steps;
    if (variable_struct_exists(_d, "stars") && is_struct(_d.stars)
        && variable_struct_exists(_d.stars, "steps") && _d.stars.steps > 0) {
        _out.twinkle_period = _d.stars.steps;
    }
    _out.twinkle_period = max(1, round(_out.twinkle_period));
    if (variable_struct_exists(_d, "text") && is_struct(_d.text)) {
        var _t = _d.text;
        if (variable_struct_exists(_t, "chars_per_second") && _t.chars_per_second > 0) {
            _out.char_steps = 60 / _t.chars_per_second;
        }
        if (variable_struct_exists(_t, "pause_after_beat_seconds") && _t.pause_after_beat_seconds >= 0) {
            _out.beat_pause = round(_t.pause_after_beat_seconds * 60);
        }
        if (variable_struct_exists(_t, "lines_on_screen") && _t.lines_on_screen > 0) {
            _out.lines_on_screen = _t.lines_on_screen;
        }
        if (variable_struct_exists(_t, "blip_every_chars") && _t.blip_every_chars > 0) {
            _out.blip_every = _t.blip_every_chars;
        }
    }
    return _out;
}

/// The crawl's beats, flattened into one line per entry: an array of { beat, text } in reading order.
function pp_title_intro_beats() {
    var _rows = [];
    var _d = pp_title_read_any(["datafiles/intro_text.json", "intro_text.json"]);
    if (is_struct(_d) && variable_struct_exists(_d, "beats") && is_array(_d.beats)) {
        for (var b = 0; b < array_length(_d.beats); b += 1) {
            var _beat = _d.beats[b];
            if (!is_array(_beat)) continue;
            for (var l = 0; l < array_length(_beat); l += 1) {
                if (!is_string(_beat[l])) continue;
                array_push(_rows, { beat: b, text: _beat[l] });
            }
        }
    }
    if (array_length(_rows) > 0) return _rows;
    // The fallback crawl, so the shot never runs on an empty screen.
    var _fallback = ["THE GODS NEVER DIED.", "THEY WERE FORGOTTEN."];
    for (var f = 0; f < array_length(_fallback); f += 1) array_push(_rows, { beat: f, text: _fallback[f] });
    return _rows;
}

/// Every star as a point, in one flat array: the shapes in reading order, then the loose ones.
function pp_title_intro_stars() {
    var _stars = [];
    var _d = pp_title_read_any(["datafiles/intro_stars.json", "intro_stars.json"]);
    if (!is_struct(_d)) return _stars;
    if (variable_struct_exists(_d, "shapes") && is_array(_d.shapes)) {
        for (var s = 0; s < array_length(_d.shapes); s += 1) {
            var _shape = _d.shapes[s];
            if (!is_struct(_shape) || !variable_struct_exists(_shape, "points")) continue;
            var _name = (variable_struct_exists(_shape, "name") ? _shape.name : "loose");
            var _points = _shape.points;
            if (!is_array(_points)) continue;
            for (var p = 0; p < array_length(_points); p += 1) {
                var _pt = _points[p];
                if (!is_array(_pt) || array_length(_pt) < 2) continue;
                array_push(_stars, { x: _pt[0], y: _pt[1], shape: _name });
            }
        }
    }
    if (variable_struct_exists(_d, "loose") && is_array(_d.loose)) {
        for (var k = 0; k < array_length(_d.loose); k += 1) {
            var _loose = _d.loose[k];
            if (!is_array(_loose) || array_length(_loose) < 2) continue;
            array_push(_stars, { x: _loose[0], y: _loose[1], shape: "loose" });
        }
    }
    return _stars;
}

/// The crawl as a layout over pp_text (spec 14, addendum 2026-10-22). One beat of the music is one unit of the
/// reveal, so the beat pause is the machine's gap at a unit end; one line of the beat is one row this module draws.
/// Nothing here decides when a character appears: the speed, the punctuation holds, the gap and the blip interval are
/// the title's own numbers, handed to the one machine.
function pp_title_crawl_new(_s) {
    var _rows = [];
    var _units = [];
    var _beat = -1;
    var _unit = [];
    for (var i = 0; i < array_length(_s.text_beats); i += 1) {
        var _row = _s.text_beats[i];
        if (_row.beat != _beat) {
            if (_beat >= 0) array_push(_units, _unit);
            _unit = [];
            _beat = _row.beat;
        }
        var _items = pp_text_items(_row.text);
        array_push(_rows, { beat: _row.beat, text: _row.text, count: array_length(_items) });
        for (var k = 0; k < array_length(_items); k += 1) array_push(_unit, _items[k]);
    }
    if (_beat >= 0) array_push(_units, _unit);
    // The narrator's pitch, because the crawl is the game speaking and not a character (spec 05 rule 3), and auto
    // advance, because a crawl has no confirm to wait for.
    var _reveal = pp_text_reveal_begin(_units, "narrator", true);
    pp_text_reveal_timing(_reveal, _s.char_steps, _s.beat_pause, _s.blip_every);
    return { rows: _rows, reveal: _reveal };
}

/// One step of the crawl is one step of the machine. There is no timer and no per line counter here: the reveal's
/// own fields are the truth, and the duck under the words happens on the first step.
function pp_title_crawl_step(_s) {
    if (!is_struct(_s.crawl)) return;
    pp_text_reveal_step(_s.crawl.reveal, false);
}

/// True when the last beat has been typed out, or the player skipped to it.
function pp_title_crawl_done(_s) {
    if (!is_struct(_s.crawl)) return true;
    return pp_text_reveal_done(_s.crawl.reveal);
}

/// Jump the crawl to its end, which is what the start key does: the last beat is shown whole, then the shot leaves.
function pp_title_crawl_finish(_s) {
    if (!is_struct(_s.crawl)) return;
    pp_text_reveal_finish(_s.crawl.reveal);
}

/// One step of the intro: the pan, the two four step fades, the held stars, the crawl, and the skip.
function pp_title_step_intro(_s) {
    _s.intro += 1;

    // The pan: a camera move up out of the road, slowed at the end (ease out) so it settles instead of stopping.
    var _t = min(1, _s.intro / PP_TITLE_INTRO_PAN_STEPS);
    _s.intro_pan = round(PP_TITLE_INTRO_PAN_PX * (1 - power(1 - _t, 2)));

    // The world fades four NES brightness rows to black while the sky is still bright, then the sky does the same.
    if (_s.intro >= PP_TITLE_INTRO_WORLD_FADE) {
        _s.intro_world = min(4, 1 + floor((_s.intro - PP_TITLE_INTRO_WORLD_FADE) / PP_TITLE_INTRO_FADE_STEP_STEPS));
    }
    if (_s.intro >= PP_TITLE_INTRO_SKY_FADE) {
        _s.intro_sky = min(4, 1 + floor((_s.intro - PP_TITLE_INTRO_SKY_FADE) / PP_TITLE_INTRO_FADE_STEP_STEPS));
    }

    if (_s.intro >= PP_TITLE_INTRO_TEXT && !pp_title_crawl_done(_s)) {
        if (!_s.ducked) {
            // The theme keeps playing and drops under the words, then comes back for the run.
            pp_audio_duck_db(PP_TITLE_DUCK_DB);
            _s.ducked = true;
        }
        pp_title_crawl_step(_s);
    }

    // The start key skips to the end of the crawl. The pad's start is the menu action, and Z or X work too, which is
    // how a cutscene of this kind is skipped on the hardware this game is written for.
    if (pp_pressed("menu") || pp_pressed("cancel") || pp_pressed("confirm")) {
        if (!pp_title_crawl_done(_s)) {
            pp_title_crawl_finish(_s);
            show_debug_message("PP title: intro skipped, the crawl jumped to its end");
        }
    }

    if (pp_title_crawl_done(_s)) {
        if (_s.ducked) {
            pp_audio_unduck();
            _s.ducked = false;
        }
        _s.intro_hold += 1;
        if (_s.intro_hold >= PP_TITLE_INTRO_HOLD) {
            // One second of the last frame, then the run: a fresh ledger and rm_pp_ship, behind the app machine's fade.
            _s.phase = "leaving";
            show_debug_message("PP title: intro finished, starting the run in " + PP_NEW_GAME_ROOM);
            pp_save_new_game();
            // The crawl's handoff to the demo's route (card R24). A newer request replaces the one just made (spec 01
            // rule 2), so a route that knows what follows the crawl is taken here and one that does not leaves the
            // new run's own map standing.
            pp_title_crawl_handoff();
        }
    }
}

/// The name of a strip at a fade level: the untouched art at level 0, and the pre-drawn palette row copies after
/// that. A level whose strip is not in the build falls back to the brightest one that is, so a half built fade
/// never shows a hole.
function pp_title_fade_name(_name, _level) {
    if (_level <= 0) return _name;
    for (var level = _level; level >= 1; level -= 1) {
        var _candidate = _name + "_fade" + string(level);
        if (pp_art_has(_candidate)) return _candidate;
    }
    return _name;
}

/// The intro shot: the sky, the world sliding down out of frame, the stars over it, and the crawl under them.
function pp_title_draw_intro_scene(_s, _d) {
    var _pan = _s.intro_pan;

    // The sky fills the frame once the camera is above the road, so it is drawn as two strips, one above the other.
    // The fade picks the pre-drawn NES brightness row copies of the sky; the stars are drawn after it and are never
    // faded, which is the whole point of the shot.
    var _sky = pp_title_fade_name("title_L1_sky", _s.intro_sky);
    var _sky_info = pp_art_info(_sky);
    if (!is_undefined(_sky_info)) {
        var _sky_frame = pp_title_layer_frame(_sky, _s.steps);
        var _sky_offset = round(_s.scroll * 0.02);
        for (var r = 0; r < 2; r += 1) {
            pp_art_layer(_sky, _sky_frame, r * _sky_info.frame_h, _sky_offset, PP_FRAME_W, _sky_info.frame_h);
        }
    }

    // The world: every layer but the sky, with the pan added, so the road and the fields slide out of the bottom of
    // the frame as if the camera rose. Each one is drawn at the world's fade level.
    for (var i = 0; i < array_length(_d.layers); i += 1) {
        var _layer = _d.layers[i];
        if (_layer.name == "title_L1_sky") continue;
        var _name = pp_title_fade_name(_layer.name, _s.intro_world);
        var _info = pp_art_info(_name);
        if (is_undefined(_info)) continue;
        var _offset = round(_s.scroll * _layer.speed);
        pp_art_layer(_name, pp_title_layer_frame(_name, _s.steps), _layer.y + _pan, _offset, PP_FRAME_W, _info.frame_h);
    }

    var _car = pp_title_fade_name("spr_title_car", _s.intro_world);
    if (pp_art_has(_car)) {
        pp_art_draw(_car, floor(_s.steps / 10) mod pp_art_frames(_car), _d.car_x, _d.car_y + _pan, PP_UNTINTED, 1);
    }
    var _cloud = pp_title_fade_name("spr_title_cloud", _s.intro_world);
    if (pp_art_has(_cloud)) {
        pp_art_draw(_cloud, floor(_s.steps / 30) mod 2, _d.car_x + 64, 80 + _pan, PP_UNTINTED, 1);
    }

    pp_title_draw_stars(_s);

    if (_s.intro >= PP_TITLE_INTRO_TEXT) pp_title_draw_crawl(_s);
}

/// The twenty four stars, each on its own beat of the theme: a star is spread a slot apart, so neighbours light on
/// different beats, and each one runs the three frame twinkle from the dot to the wide cross and back.
function pp_title_draw_stars(_s) {
    if (!is_array(_s.stars)) return;
    var _count = array_length(_s.stars);
    if (_count == 0) return;
    var _period = max(1, _s.twinkle_period);
    for (var i = 0; i < _count; i += 1) {
        var _star = _s.stars[i];
        // The stagger: the stars are spread evenly across one twinkle period, so a group of nine in a sickle never
        // lights as a group. A star's own twinkle is nine steps: wide, plus, dot, then the dot until its next turn.
        var _slot = floor(i * _period / _count);
        var _local = (_s.intro - _slot) mod _period;
        if (_local < 0) _local += _period;
        var _frame = 0;
        if (_local < 3) _frame = 2;
        else if (_local < 6) _frame = 1;
        pp_art_draw("spr_title_star", _frame, _star.x - 2, _star.y - 2, PP_UNTINTED, 1);
    }
}

/// The crawl: the lines already typed stack upward, the line being typed sits at the bottom, and when the stack is
/// full the oldest line scrolls off the top. How many characters are on screen is the machine's revealed count, spent
/// across the rows of the beat being typed; this function only decides which rows are in the window and where they sit.
function pp_title_draw_crawl(_s) {
    var _c = _s.crawl;
    if (!is_struct(_c)) return;
    var _rv = _c.reveal;
    var _visible = _s.timing.lines_on_screen;
    var _total = array_length(_c.rows);
    if (_total == 0) return;

    // The row being typed, and how much of it is shown. The reveal counts items over the current beat, so the beat's
    // rows are walked and the count is spent on each until the row it stops in.
    var _row = 0;
    while (_row < _total && _c.rows[_row].beat < _rv.unit) _row += 1;
    var _budget = _rv.revealed;
    while (_row < _total && _c.rows[_row].beat == _rv.unit && _budget > _c.rows[_row].count) {
        _budget -= _c.rows[_row].count;
        _row += 1;
    }
    if (_row >= _total) {
        _row = _total - 1;
        _budget = _c.rows[_row].count;
    }
    if (_budget > _c.rows[_row].count) _budget = _c.rows[_row].count;

    var _first = max(0, _row - (_visible - 1));
    for (var i = _first; i <= _row; i += 1) {
        var _text = _c.rows[i].text;
        if (i == _row) _text = string_copy(_text, 1, floor(_budget));
        if (_text == "") continue;
        var _at = i - _first;
        pp_font_draw_centre(_text, PP_FRAME_W / 2, PP_TITLE_INTRO_TEXT_Y + _at * PP_TITLE_INTRO_LINE_H, 1);
    }
}

/// The layer with this name, or undefined.
function pp_title_layer_named(_d, _name) {
    for (var i = 0; i < array_length(_d.layers); i += 1) {
        if (_d.layers[i].name == _name) return _d.layers[i];
    }
    return undefined;
}

/// The self check for the crawl (card TEXT-REVEAL-2). With PP_TITLE_CAPTURE set in the environment the game writes its
/// own frames from inside the draw, which is the only copy of this window this host can be trusted with: a screen
/// rectangle copy of the DirectX11 window has measured the desktop's colours in this session, and the ship room's
/// capture uses the same escape for the same reason. The two files are the crawl six seconds in, and the first draw
/// after the last beat is typed (inside the one second hold, before the run starts). Unset, which is every real
/// launch, this costs one environment read per draw and writes nothing.
///
/// The same escape carries the scroll check of card TEMPO-1: on the title card (any phase but the intro) three frames
/// are written PP_TITLE_SCROLL_CAPTURE_GAP steps apart, and each one logs the step it was taken on. The frames are the
/// game's own pixels, so the shift between them is the tempo and not the desktop's scaling, which is what the window
/// copies could never show (review round 1 of TEMPO-1: two copies 10 s apart, resampled, with no measurable scroll).
function pp_title_capture_frames() {
    if (environment_get_variable(PP_TITLE_CAPTURE) == "") return;
    var _s = global.pp.title;
    if (!is_struct(_s)) return;
    if (_s.phase != "intro") {
        for (var _i = 0; _i < 3; _i += 1) {
            if (_s.steps != PP_TITLE_SCROLL_CAPTURE_FIRST + _i * PP_TITLE_SCROLL_CAPTURE_GAP) continue;
            var _file = "pp_title_scroll_" + string(_i + 1) + ".png";
            screen_save(_file);
            if (file_exists(_file)) {
                show_debug_message("PP title: wrote " + _file + " at step " + string(_s.steps) + ", scroll "
                                   + string(_s.scroll) + ", phase " + string(_s.phase));
            } else {
                show_debug_message("PP title: screen_save wrote nothing for " + _file);
            }
        }
        return;
    }
    if (_s.intro == PP_TITLE_CRAWL_CAPTURE_MID) {
        screen_save("pp_crawl_mid.png");
        show_debug_message("PP title: wrote pp_crawl_mid.png at intro step " + string(_s.intro));
    }
    if (!variable_global_exists("pp_crawl_end_written")) global.pp_crawl_end_written = false;
    if (!global.pp_crawl_end_written && is_struct(_s.crawl) && pp_title_crawl_done(_s)) {
        global.pp_crawl_end_written = true;
        screen_save("pp_crawl_end.png");
        show_debug_message("PP title: wrote pp_crawl_end.png at intro step " + string(_s.intro));
    }
}

/// The app mode that runs the title screen. Registered by pp_app_boot.
/// Since card W1 the screen lives in rm_pp_title and obj_pp_title runs it. When that object is in the room it is the
/// only stepper and the only drawer, so the mode hands over rather than running the same screen a second time. The
/// guards are also what keeps the screen still while the room move is in flight, because the object does not exist yet.
function pp_title_mode() {
    return {
        enter: function(_params) { if (!instance_exists(obj_pp_title)) pp_title_enter(_params); },
        step: function(_params) { if (instance_exists(obj_pp_title)) return; pp_title_step(_params); },
        draw: function(_params) { if (instance_exists(obj_pp_title)) return; pp_title_draw(_params); }
    };
}
