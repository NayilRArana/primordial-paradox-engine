/// obj_pp_title, Draw: the title screen is drawn here.
/// The screen draws itself, so the app machine's title mode draws nothing: there is one owner per frame.
if (pp_app_mode() != PPMode.title) exit;
pp_title_draw({});

// Card W1 self check: with PP_TITLE_CAPTURE set in the environment, the game writes one PNG of its own frame from
// inside the draw, so a run can be proven without a screen copy of whatever window happens to sit on top of the game.
// Unset, which is every real launch, this costs one environment read per frame and writes nothing.
// screen_save has no return value on this runtime, so the file it wrote is what gets checked.
if (global.pp.title.steps == 30 && environment_get_variable(PP_TITLE_CAPTURE) != "") {
    screen_save("pp_title_frame.png");
    if (file_exists("pp_title_frame.png")) {
        show_debug_message("PP title: wrote pp_title_frame.png at step 30, phase " + string(global.pp.title.phase));
    } else {
        show_debug_message("PP title: screen_save wrote nothing");
    }
}

// Card TEXT-REVEAL-2 self check: the same escape for the intro crawl, which writes its own mid frame and its own
// finished frame from inside this draw (pp_title_capture_frames). The crawl cannot be photographed with a screen copy:
// the last beat is held for one second before the run starts, which is shorter than a copy takes on this host.
pp_title_capture_frames();
