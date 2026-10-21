/// obj_pp_game: the one controller instance in the boot room.
/// Create builds the game frame (data, input, camera, ledger, app modes) exactly once. Nothing else in the project
/// sets any of it up, so there is one order and it is this one.
// Crash log, installed before anything that can throw. The default behaviour on Windows is a modal error box, which no
// script, no build and no unattended run can read, so an unhandled exception is written to pp_crash.log in the save area
// and the game closes. Read that file; do not infer a result from an exit code.
// Fields are the ones the runtime documents for the handler: message, longMessage, script, line, stacktrace.
exception_unhandled_handler(function(_ex) {
    var _text = "message: " + string(_ex.message) + "\n";
    _text += "where: " + string(_ex.script) + " line " + string(_ex.line) + "\n";
    _text += string(_ex.longMessage) + "\n";
    _text += "callstack:\n";
    var _frames = array_length(_ex.stacktrace);
    for (var _i = 0; _i < _frames; _i += 1) {
        _text += "  " + string(_ex.stacktrace[_i]) + "\n";
    }
    var _file = file_text_open_write("pp_crash.log");
    if (_file != -1) {
        file_text_write_string(_file, _text);
        file_text_close(_file);
    }
    game_end();
    return 0;
});

pp_app_boot();
