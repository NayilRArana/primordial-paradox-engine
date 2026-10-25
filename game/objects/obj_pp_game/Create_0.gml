/// obj_pp_game: the one controller instance in the boot room.
/// Create builds the game frame (data, input, camera, ledger, app modes) exactly once. Nothing else in the project
/// sets any of it up, so there is one order and it is this one.
//
// Crash log, installed before anything that can throw. The default behaviour on Windows is a modal error box, which no
// script, no build and no unattended run can read, so an unhandled exception is reported and the game closes.
//
// Two channels, because either one alone can be lost:
//   1. show_debug_message, which the runtime prints into the Igor run log. This is the channel that is known to work
//      on this machine (measured 2026-10-20), so it comes first and it touches nothing that can fail.
//   2. pp_crash.log in the save area, for a human reading the machine later.
//
// The handler must not itself throw, because an exception inside the handler loses the error entirely. So every field
// is read defensively, and the callstack is only walked if the field is really an array.
exception_unhandled_handler(function(_ex) {
    var _message = "";
    var _script = "";
    var _line = "";
    if (is_struct(_ex)) {
        if (variable_struct_exists(_ex, "message")) _message = string(_ex.message);
        if (variable_struct_exists(_ex, "script")) _script = string(_ex.script);
        if (variable_struct_exists(_ex, "line")) _line = string(_ex.line);
    }
    var _head = "PP CRASH: " + _message + " | at " + _script + " line " + _line;
    show_debug_message(_head);

    var _text = _head + "\n";
    if (is_struct(_ex) && variable_struct_exists(_ex, "longMessage")) {
        _text += string(_ex.longMessage) + "\n";
    }
    if (is_struct(_ex) && variable_struct_exists(_ex, "stacktrace")) {
        var _frames = _ex.stacktrace;
        if (is_array(_frames)) {
            _text += "callstack:\n";
            for (var _i = 0; _i < array_length(_frames); _i += 1) {
                _text += "  " + string(_frames[_i]) + "\n";
            }
        }
    }

    // The file write is the part that can fail, so it is last and it is guarded.
    var _file = -1;
    _file = file_text_open_write("pp_crash.log");
    if (_file != -1) {
        file_text_write_string(_file, _text);
        file_text_close(_file);
    }

    game_end();
    return 0;
});

// The window opens at 3x (768x720), integer scaled, so the pixels are readable on a desktop monitor.
window_set_size(PP_FRAME_W * 3, PP_FRAME_H * 3);
window_set_position(max(0, (display_get_width() - PP_FRAME_W * 3) div 2), max(0, (display_get_height() - PP_FRAME_H * 3 - 90) div 2));
pp_app_boot();

// Card R21a: the drive room's door. Unset in every real launch, so the game opens where the route says it does. A
// proof run sets PP_DRIVE_ROOM and the frame moves to rm_pp_drive through the app's own room door (pp_drive_goto_room
// asks for PPMode.cutscene and room_goto, the drive being a cutscene and its room the screen's owner). This door is the
// capture door and it stays a capture door: decision D19 (knowledge/GAMEDEV-DECISIONS-2026-10-24.md) rules that the
// drive ships as the drive_to_southampton scene on drive_m4_corridor, which is the step data/slice.json already plays.
// Do not route the slice here.
if (environment_get_variable(PP_DRIVE_ROOM) != "") pp_drive_goto_room();
