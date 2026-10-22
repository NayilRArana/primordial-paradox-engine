/// pp_audio: the cue bus the title screen asks for sounds by name.
/// A cue is a name, never a file. The bus knows which cues exist and which sound each one is; a cue whose
/// sound has not been delivered yet stays silent on purpose rather than making a noise out of nothing.
/// The cue list is spec 14: title_theme, car_engine_loop, menu_move, menu_select, thunder_soft.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\12-audio.md and specs\14-title-screen-drive.md.

/// The cue names the title screen uses. A cue is requested by name; the bus decides what that means.
function pp_audio_cues() {
    return ["title_theme", "car_engine_loop", "menu_move", "menu_select", "thunder_soft"];
}

/// The sounds that are actually present in the build. It is empty until the music lane delivers its files,
/// which is why every cue below is silent today and the screen still works.
function pp_audio_available() {
    return [];
}

/// The theme streams to try, best first. v2 is the 2026-10-21 waltz; v1 stays as the fallback so a build that
/// predates the new render still has music.
function pp_audio_theme_streams() {
    return ["streams/title_theme_v2.ogg", "streams/title_theme.ogg"];
}

/// Ask for a cue. Returns true when a sound was played, false when the cue is silent because its sound has
/// not arrived yet. Every request is recorded, so the log shows what the screen asked for.
function pp_audio_play(_cue) {
    if (!is_struct(global.pp)) return false;
    if (!variable_struct_exists(global.pp, "audio") || !is_struct(global.pp.audio)) {
        global.pp.audio = { last_cue: "", asked: 0, played: 0 };
    }
    global.pp.audio.last_cue = _cue;
    global.pp.audio.asked += 1;

    var _known = pp_audio_cues();
    var _is_cue = false;
    for (var i = 0; i < array_length(_known); i += 1) {
        if (_known[i] == _cue) { _is_cue = true; break; }
    }
    if (!_is_cue) {
        show_debug_message("PP audio: unknown cue " + string(_cue));
        return false;
    }

    // The title theme is an external OGG stream shipped as an included file, looped. The v2 theme is asked for first and
    // the v1 theme is the fallback, so the music lane can land a new render and the build picks it up with no code change.
    // A missing file leaves the screen silent, and nothing here can throw.
    if (_cue == "title_theme") {
        if (!variable_struct_exists(global.pp.audio, "theme_inst")) {
            var _candidates = pp_audio_theme_streams();
            for (var t = 0; t < array_length(_candidates); t += 1) {
                var _rel = _candidates[t];
                var _file = working_directory + _rel;
                if (!file_exists(_file)) continue;
                var _stream = audio_create_stream(_file);
                global.pp.audio.theme_stream = _stream;
                global.pp.audio.theme_file = _rel;
                global.pp.audio.theme_inst = audio_play_sound(_stream, 1, true);
                show_debug_message("PP audio: title_theme streaming " + _rel + ", instance " + string(global.pp.audio.theme_inst));
                global.pp.audio.played += 1;
                return true;
            }
            show_debug_message("PP audio: no title theme stream in " + working_directory + "streams");
        }
        return false;
    }

    var _have = pp_audio_available();
    for (var j = 0; j < array_length(_have); j += 1) {
        if (_have[j] == _cue) {
            global.pp.audio.played += 1;
            return true;
        }
    }
    return false;
}

/// The cue that was asked for last, or an empty string.
function pp_audio_last_cue() {
    if (!is_struct(global.pp) || !is_struct(global.pp.audio)) return "";
    return global.pp.audio.last_cue;
}
