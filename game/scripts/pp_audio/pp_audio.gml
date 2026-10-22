/// pp_audio: the cue bus the game asks for sounds by name.
/// A cue is a name, never a file. The bus knows which cues exist and which sound each one is; a cue whose
/// sound has not been delivered yet stays silent on purpose rather than making a noise out of nothing.
/// The cue list is spec 14 for the title and spec 12 for the effects (card SFX-WIRE): title_theme,
/// car_engine_loop, menu_move, menu_select, menu_cancel, text_blip_a/b/c, footstep, door_hatch,
/// encounter_swoosh, thunder_soft.
///
/// Delivery: tools\sync_art.py copies each effect WAV from assets\audio\sfx into game\datafiles\sfx and writes
/// sfx\sfx.json with the data chunk offset and byte length measured from the file, so no number here is a guess.
/// Every effect is loaded once into a buffer and played with audio_play_sound as a buffer sound (not a stream:
/// a stream decodes from disk while it plays, which is right for a 90 second theme and wrong for a 60 ms tick).
/// A cue with no file, or a file whose measurement does not fit, is silent and says so in the log; nothing
/// here throws.
///
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\12-audio.md, specs\05-dialogue.md (blip rule 3) and specs\14-title-screen-drive.md.

#macro PP_AUDIO_SFX_DIR "sfx/"

/// The cue names the game asks for. A cue is requested by name; the bus decides what that means.
function pp_audio_cues() {
    return [
        "title_theme", "car_engine_loop",
        "menu_move", "menu_select", "menu_cancel",
        "text_blip_a", "text_blip_b", "text_blip_c",
        "footstep", "door_hatch", "encounter_swoosh", "thunder_soft",
        "item_get", "heal", "hit_light", "hit_heavy", "miss", "crit", "level_up",
        "alarm", "wave_wash", "save_jingle", "game_over"
    ];
}

/// The effects the build actually ships, read from the manifest the sync tool writes. The manifest is the only
/// source: a cue that is not in it is silent, which is the audio guard the card asks for.
function pp_audio_load_manifest() {
    var _manifest = pp_data_json(PP_AUDIO_SFX_DIR + "sfx.json");
    if (is_undefined(_manifest) || !is_struct(_manifest) || !variable_struct_exists(_manifest, "cues")) {
        show_debug_message("PP audio: no effect manifest at " + PP_AUDIO_SFX_DIR + "sfx.json, every effect stays silent");
        return undefined;
    }
    return pp_data_index(_manifest.cues);
}

/// The bus state. One struct holds the counters the log reads, the manifest, and the loaded sounds.
function pp_audio_state() {
    if (!variable_struct_exists(global.pp, "audio") || !is_struct(global.pp.audio)) {
        global.pp.audio = {
            last_cue: "", asked: 0, played: 0, silent: 0,
            entries: pp_audio_load_manifest(),
            sounds: {}
        };
    }
    return global.pp.audio;
}

/// The cue names whose sound is in the build right now.
function pp_audio_available() {
    var _a = pp_audio_state();
    var _out = [];
    if (is_undefined(_a.entries)) return _out;
    var _names = variable_struct_get_names(_a.entries);
    var _i = 0;
    while (_i < array_length(_names)) {
        array_push(_out, _names[_i]);
        _i += 1;
    }
    return _out;
}

/// The theme streams to try, best first. v3_126 is the 2026-10-21 waltz at 126 bpm, the tempo the title's own
/// animation is timed to (card TEMPO-1); v3 is the same piece at its first tempo, and v2 and v1 stay as fallbacks
/// so a build that predates a render still has music.
function pp_audio_theme_streams() {
    return ["streams/title_theme_v3_126.ogg", "streams/title_theme_v3.ogg",
            "streams/title_theme_v2.ogg", "streams/title_theme.ogg"];
}

/// One effect, loaded once. Returns the sound, or -1 when the file is missing or unreadable, and says why.
/// The buffer is kept in the state because a buffer sound reads from that memory for as long as it exists.
function pp_audio_sound(_a, _cue, _entry) {
    if (variable_struct_exists(_a.sounds, _cue)) return _a.sounds[$ _cue];
    var _file = working_directory + PP_AUDIO_SFX_DIR + string(_entry.file);
    if (!file_exists(_file)) {
        show_debug_message("PP audio: " + string(_cue) + " silent, no file at " + _file);
        _a.sounds[$ _cue] = -1;
        return -1;
    }
    var _raw = buffer_load(_file);
    if (_raw < 0) {
        show_debug_message("PP audio: " + string(_cue) + " silent, buffer_load failed on " + _file);
        _a.sounds[$ _cue] = -1;
        return -1;
    }
    // buffer_load gives a growing buffer and audio_create_buffer_sound refuses anything but a fixed one, which is
    // what the runtime said the first time this ran: "unsupported buffer type (buffer_grow)". So the data chunk is
    // copied out of the file image into a fixed buffer the size of the chunk, and the file image is let go.
    var _bytes = int64(_entry.data_bytes);
    var _offset = int64(_entry.offset);
    if (_bytes <= 0 || _offset < 0 || _offset + _bytes > buffer_get_size(_raw)) {
        show_debug_message("PP audio: " + string(_cue) + " silent, the measured length does not fit " + _file);
        buffer_delete(_raw);
        _a.sounds[$ _cue] = -1;
        return -1;
    }
    var _buffer = buffer_create(_bytes, buffer_fixed, 1);
    buffer_copy(_raw, _offset, _bytes, _buffer, 0);
    buffer_delete(_raw);
    var _format = buffer_s16;
    if (variable_struct_exists(_entry, "sample_format") && _entry.sample_format == "buffer_u8") _format = buffer_u8;
    var _channels = audio_mono;
    if (_entry.channels == 2) _channels = audio_stereo;
    var _sound = audio_create_buffer_sound(_buffer, _format, _entry.rate, 0, _bytes, _channels);
    if (_sound < 0) {
        show_debug_message("PP audio: " + string(_cue) + " silent, audio_create_buffer_sound failed on " + _file);
        buffer_delete(_buffer);
        _a.sounds[$ _cue] = -1;
        return -1;
    }
    if (!variable_struct_exists(_a, "buffers")) _a.buffers = {};
    _a.buffers[$ _cue] = _buffer;
    _a.sounds[$ _cue] = _sound;
    show_debug_message("PP audio: " + string(_cue) + " loaded " + string(_entry.file) + " ("
        + string(_entry.seconds) + " s, " + string(_entry.rate) + " Hz, buffer " + string(_buffer) + ")");
    return _sound;
}

/// The theme: an external OGG stream shipped as an included file, looped. The v2 theme is asked for first and
/// the v1 theme is the fallback, so the music lane can land a new render with no code change.
function pp_audio_play_theme(_a) {
    if (!variable_struct_exists(_a, "theme_inst")) {
        var _candidates = pp_audio_theme_streams();
        for (var t = 0; t < array_length(_candidates); t += 1) {
            var _rel = _candidates[t];
            var _file = working_directory + _rel;
            if (!file_exists(_file)) continue;
            var _stream = audio_create_stream(_file);
            _a.theme_stream = _stream;
            _a.theme_file = _rel;
            _a.theme_inst = audio_play_sound(_stream, 1, true);
            show_debug_message("PP audio: title_theme streaming " + _rel + ", instance " + string(_a.theme_inst));
            _a.played += 1;
            return true;
        }
        show_debug_message("PP audio: no title theme stream in " + working_directory + "streams");
    }
    return false;
}

/// Ask for a cue. Returns true when a sound was played, false when the cue is silent because its sound has
/// not arrived yet. Every request is recorded and every play writes one log line, so a scripted run can be
/// read back and checked cue by cue.
function pp_audio_play(_cue) {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    _a.last_cue = _cue;
    _a.asked += 1;

    var _known = pp_audio_cues();
    var _is_cue = false;
    for (var i = 0; i < array_length(_known); i += 1) {
        if (_known[i] == _cue) { _is_cue = true; break; }
    }
    if (!_is_cue) {
        show_debug_message("PP audio: unknown cue " + string(_cue));
        return false;
    }

    if (_cue == "title_theme") return pp_audio_play_theme(_a);

    if (is_undefined(_a.entries) || !variable_struct_exists(_a.entries, _cue)) {
        _a.silent += 1;
        show_debug_message("PP audio: " + string(_cue) + " silent, not in " + PP_AUDIO_SFX_DIR + "sfx.json");
        return false;
    }
    var _entry = _a.entries[$ _cue];
    var _sound = pp_audio_sound(_a, _cue, _entry);
    if (_sound < 0) {
        _a.silent += 1;
        return false;
    }
    var _inst = audio_play_sound(_sound, 1, false);
    _a.played += 1;
    show_debug_message("PP audio: " + string(_cue) + " played, instance " + string(_inst));
    return true;
}

/// The blip cue for a speaker: three pitches, one class of speaker each, so a line reads in a voice before the
/// portrait does (spec 05 dialogue rule 3). An unknown speaker gets the narrator pitch rather than silence.
function pp_audio_blip_cue(_speaker) {
    switch (string_lower(string(_speaker))) {
        case "sailor":     return "text_blip_b";
        case "percy":      return "text_blip_c";
        case "prometheus": return "text_blip_b";
        case "narrator":   return "text_blip_a";
    }
    return "text_blip_a";
}

/// The cue that was asked for last, or an empty string.
function pp_audio_last_cue() {
    if (!is_struct(global.pp) || !is_struct(global.pp.audio)) return "";
    return global.pp.audio.last_cue;
}

/// How many cues were asked for, played and left silent. The capture harness reads the log for the same story.
function pp_audio_counts() {
    var _a = pp_audio_state();
    return { asked: _a.asked, played: _a.played, silent: _a.silent };
}

/// Duck the theme by a number of decibels, for the intro's text crawl (card INTRO-1): the music keeps playing and
/// only drops under the words. The level is recorded on the bus even when no stream file is in the build, so the log
/// and the tests can see that the duck was asked for. Returns true when a live instance was turned down.
function pp_audio_duck_db(_db) {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    _a.duck_db = _db;
    if (!variable_struct_exists(_a, "theme_inst")) {
        show_debug_message("PP audio: title_theme ducked " + string(_db) + " dB in the state, no stream instance to turn down");
        return false;
    }
    var _gain = power(10, _db / 20);
    audio_sound_gain(_a.theme_inst, _gain, 0);
    show_debug_message("PP audio: title_theme ducked " + string(_db) + " dB, gain " + string(_gain));
    return true;
}

/// Put the theme back to full, when the crawl ends or is skipped.
function pp_audio_unduck() {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    var _was = 0;
    if (variable_struct_exists(_a, "duck_db")) _was = _a.duck_db;
    _a.duck_db = 0;
    if (!variable_struct_exists(_a, "theme_inst")) return false;
    audio_sound_gain(_a.theme_inst, 1, 0);
    if (_was != 0) show_debug_message("PP audio: title_theme back to full after " + string(_was) + " dB");
    return true;
}
