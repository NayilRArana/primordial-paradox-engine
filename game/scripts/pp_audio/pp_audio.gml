/// pp_audio: the cue bus the game asks for sounds by name.
/// A cue is a name, never a file. The bus knows which cues exist and which sound each one is; a cue whose
/// sound has not been delivered yet stays silent on purpose rather than making a noise out of nothing.
/// Two tables live behind this module and both are data:
///   effects, the short sounds, listed in game\datafiles\sfx\sfx.json by tools\sync_art.py with the data chunk
///     offset and byte length measured from the file, so no number in here is a guess;
///   music cues, keyed by the musician's own ids PP-01 to PP-16 in data\audio.json, so his OGG named after the
///     cue's asset is picked up with no code edit (spec 12, card G0-2).
///
/// Audio calls used here, and where each behaviour was checked. Every page named below was read on 2026-10-22 at
/// https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Audio/ :
///   audio_play_sound(index, priority, loop, gain) returns the instance id, and that id is what the gain, pause,
///     resume and stop calls below address (audio_play_sound.htm);
///   audio_sound_gain(index, volume, time) fades linearly over a time given in MILLISECONDS, and with an instance
///     id it affects only that instance; a time of 0 changes the gain instantly (audio_sound_gain.htm);
///   audio_pause_sound(index) and audio_resume_sound(index) resume "from its paused state", so the play position
///     survives a pause (audio_pause_sound.htm, audio_resume_sound.htm);
///   audio_stop_sound(index) also stops a paused sound (audio_stop_sound.htm);
///   audio_is_playing(index) asks whether an instance is playing, and its own note says it STILL RETURNS TRUE for a
///     sound that was paused, so it answers "is this instance alive", never "is this instance audible"
///     (audio_is_playing.htm);
///   audio_channel_num(num) is a configuration call that STOPS ALL PLAYING SOUNDS, so it is called exactly once,
///     before the first cue (audio_channel_num.htm);
///   audio_create_stream(file) streams an external OGG, and the page says the sound must be destroyed with
///     audio_destroy_stream or the game leaks and eventually crashes (audio_create_stream.htm);
///   audio_create_buffer_sound(buffer, format, rate, offset, length, channels) makes a sound from a fixed buffer, and
///     its own page defines the channel constants audio_mono and audio_stereo passed to it here
///     (Audio_Buffers/audio_create_buffer_sound.htm).
/// Focus is polled with window_has_focus(), which the manual documents as valid on Windows and which returns false
/// while the window has lost focus (Cameras_And_Display/The_Game_Window/window_has_focus.htm). Polling beats an
/// event number this project has never compiled and therefore cannot claim.
///
/// Priorities and budgets are spec 12: music 10 and boss music 12 so it cannot be culled for an ambience, effects 5,
/// UI blips 4, 10 channels in total.
///
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone" and the G0-2 entry written on
/// 2026-10-22, written from specs\12-audio.md, specs\05-dialogue.md (blip rule 3), specs\14-title-screen-drive.md and
/// the cue list in the musician's round 1 note (PP-01 to PP-16).

#macro PP_AUDIO_SFX_DIR "sfx/"
#macro PP_AUDIO_MUSIC_DIR "music/"
#macro PP_AUDIO_FADE_STEPS 30
#macro PP_AUDIO_PRI_MUSIC 10
#macro PP_AUDIO_PRI_BOSS 12
#macro PP_AUDIO_PRI_SFX 5
#macro PP_AUDIO_PRI_UI 4
#macro PP_AUDIO_CHANNELS 10
#macro PP_AUDIO_GAIN_MUSIC 0.7
#macro PP_AUDIO_GAIN_SFX 0.9
#macro PP_AUDIO_GAIN_BLIP 0.5
#macro PP_AUDIO_STEP_MS 16.6667
#macro PP_AUDIO_SFX_SLOTS 8

/// The effect names the game asks for by name. Music is asked for by cue id through pp_audio_music instead.
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

/// The bus state. One struct holds the counters the log reads, the manifest, the loaded sounds, the current music
/// instance and its crossfade, and whether focus has paused everything.
/// audio_channel_num is called here and nowhere else, because the manual says it stops every playing sound.
function pp_audio_state() {
    if (!variable_struct_exists(global.pp, "audio") || !is_struct(global.pp.audio)) {
        global.pp.audio = {
            last_cue: "", asked: 0, played: 0, silent: 0,
            entries: pp_audio_load_manifest(),
            sounds: {},
            channels_set: false,
            registry: undefined,
            music_cue: "", music_inst: -1, music_stream: -1,
            fade_inst: -1, fade_stream: -1, fade_end_ms: 0,
            sfx_insts: [],
            focus_paused: false
        };
    }
    var _a = global.pp.audio;
    if (!_a.channels_set) {
        audio_channel_num(PP_AUDIO_CHANNELS);
        _a.channels_set = true;
    }
    return _a;
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

/// The music cue registry from data\audio.json, keyed by the musician's own ids (PP-01 to PP-16). Loaded once and
/// kept, because a cue id never changes while the game runs.
function pp_audio_registry() {
    var _a = pp_audio_state();
    if (!is_undefined(_a.registry)) return _a.registry;
    var _data = pp_data_json("audio.json");
    if (is_undefined(_data) || !is_struct(_data) || !variable_struct_exists(_data, "cues")
        || !is_array(_data.cues)) {
        show_debug_message("PP audio: data/audio.json has no cues table, every music cue stays silent");
        _a.registry = {};
        return _a.registry;
    }
    _a.registry = pp_data_index(_data.cues);
    return _a.registry;
}

/// One music cue, or undefined when the id is not registered. The checker refuses an unregistered id at build time,
/// so an undefined here means the data file and the module disagree at runtime.
function pp_audio_cue(_id) {
    var _reg = pp_audio_registry();
    if (!is_struct(_reg) || !variable_struct_exists(_reg, _id)) return undefined;
    return _reg[$ _id];
}

/// Where a cue's OGG may sit. The first path is what a shipped Included File looks like, the second is the same file
/// inside game\datafiles on a machine that has not built yet, so the musician can drop the OGG in either place.
function pp_audio_music_paths(_asset) {
    return [
        working_directory + PP_AUDIO_MUSIC_DIR + string(_asset) + ".ogg",
        working_directory + "datafiles/" + PP_AUDIO_MUSIC_DIR + string(_asset) + ".ogg"
    ];
}

/// Finish a fade that is still running, so a second cue or a stop inside the 500 ms window cannot overwrite the fade
/// slot and orphan the instance and the stream it holds. audio_create_stream.htm warns that a stream which is never
/// destroyed leaks and eventually crashes the game, so this is a stop and a destroy, not a variable reset.
function pp_audio_fade_flush(_a) {
    if (_a.fade_inst <= -1) return;
    audio_stop_sound(_a.fade_inst);
    if (_a.fade_stream > -1) audio_destroy_stream(_a.fade_stream);
    _a.fade_inst = -1;
    _a.fade_stream = -1;
}

/// Hand an instance and the stream behind it to the fade slot: faded to 0 here, then stopped and destroyed by
/// pp_audio_step once the fade's time is up. A fade already pending is finished first, so only one is ever live.
function pp_audio_fade_handoff(_a, _inst, _stream, _fade_ms) {
    if (_inst <= -1) return;
    pp_audio_fade_flush(_a);
    audio_sound_gain(_inst, 0, _fade_ms);
    _a.fade_inst = _inst;
    _a.fade_stream = _stream;
    _a.fade_end_ms = current_time + _fade_ms;
}

/// The title theme is music too. Before a cue starts, the theme is handed to the fade slot, so the two never play over
/// each other and the theme's stream is destroyed by the step that finishes the fade. theme_inst is then cleared, so
/// the focus poll and the duck cannot address a sound that is already on its way out.
function pp_audio_theme_release(_a, _fade_ms) {
    if (!variable_struct_exists(_a, "theme_inst") || _a.theme_inst <= -1) return false;
    var _stream = -1;
    if (variable_struct_exists(_a, "theme_stream")) _stream = _a.theme_stream;
    pp_audio_fade_handoff(_a, _a.theme_inst, _stream, _fade_ms);
    _a.theme_inst = -1;
    _a.theme_stream = -1;
    show_debug_message("PP audio: title_theme handed to the fade, the cue takes the one music source");
    return true;
}

/// Start one music cue, crossfading from whatever is playing. One music source at a time, the title theme
/// included: a live theme is handed to the same fade first. The outgoing instance fades to 0 over the fade and
/// is stopped by pp_audio_step when the fade time is up, and the incoming one rises from 0 to the music level
/// over the same time. Two tracks overlap only for those steps (spec 12 rule 4).
/// Returns true when a stream started, false when the cue is registered but its OGG has not arrived.
function pp_audio_music(_cue, _fade_steps) {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    var _entry = pp_audio_cue(_cue);
    if (is_undefined(_entry)) {
        show_debug_message("PP audio: unknown music cue " + string(_cue) + ", nothing played");
        return false;
    }
    // Asking for the track that is already playing must not restart it, or a room trigger on every step would stutter.
    if (_a.music_cue == _cue && _a.music_inst > -1) return true;

    if (_fade_steps < 1) _fade_steps = PP_AUDIO_FADE_STEPS;
    var _fade_ms = _fade_steps * PP_AUDIO_STEP_MS;
    // One music source: a live title theme goes to the same fade slot before this cue starts.
    pp_audio_theme_release(_a, _fade_ms);

    var _file = "";
    var _paths = pp_audio_music_paths(_entry.asset);
    for (var p = 0; p < array_length(_paths); p++) {
        if (file_exists(_paths[p])) { _file = _paths[p]; break; }
    }
    if (_file == "") {
        _a.silent += 1;
        _a.music_cue = _cue;
        show_debug_message("PP audio: music cue " + string(_cue) + " has no OGG yet, expected "
            + string(_entry.asset) + ".ogg, placeholder " + string(_entry.placeholder));
        // The sounds table stays as the stand-in behind the cue: if this cue names one, it is asked for here.
        if (variable_struct_exists(_entry, "placeholder_sound") && is_string(_entry.placeholder_sound)
            && _entry.placeholder_sound != "") {
            pp_audio_play(_entry.placeholder_sound);
        }
        return false;
    }

    var _priority = PP_AUDIO_PRI_MUSIC;
    if (variable_struct_exists(_entry, "boss") && _entry.boss) _priority = PP_AUDIO_PRI_BOSS;
    var _loop = true;
    if (variable_struct_exists(_entry, "loop")) _loop = _entry.loop;

    var _stream = audio_create_stream(_file);
    if (_stream < 0) {
        _a.silent += 1;
        show_debug_message("PP audio: music cue " + string(_cue) + " silent, audio_create_stream failed on " + _file);
        return false;
    }
    var _inst = audio_play_sound(_stream, _priority, _loop, 0);
    if (_inst < 0) {
        _a.silent += 1;
        audio_destroy_stream(_stream);
        show_debug_message("PP audio: music cue " + string(_cue) + " silent, no audio channel for it");
        return false;
    }
    audio_sound_gain(_inst, PP_AUDIO_GAIN_MUSIC, _fade_ms);

    if (_a.music_inst > -1) pp_audio_fade_handoff(_a, _a.music_inst, _a.music_stream, _fade_ms);
    _a.music_inst = _inst;
    _a.music_stream = _stream;
    _a.music_cue = _cue;
    _a.fade_end_ms = current_time + _fade_ms;
    _a.played += 1;
    show_debug_message("PP audio: music cue " + string(_cue) + " streaming " + _file + ", instance " + string(_inst)
        + ", priority " + string(_priority) + ", fade " + string(_fade_steps) + " steps");
    return true;
}

/// Stop the music over the full fade, never with a cut (spec 12 rule 5). The instance is handed to the fade slot so
/// pp_audio_step stops and destroys it once the fade has run its time.
function pp_audio_music_stop() {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    _a.music_cue = "";
    var _fade_ms = PP_AUDIO_FADE_STEPS * PP_AUDIO_STEP_MS;
    // The theme is music too, so a stop silences it with the same fade instead of leaving it playing.
    var _stopped_theme = pp_audio_theme_release(_a, _fade_ms);
    if (_a.music_inst <= -1) {
        if (_stopped_theme) show_debug_message("PP audio: title_theme stopping over "
            + string(PP_AUDIO_FADE_STEPS) + " steps");
        return _stopped_theme;
    }
    pp_audio_fade_handoff(_a, _a.music_inst, _a.music_stream, _fade_ms);
    _a.music_inst = -1;
    _a.music_stream = -1;
    show_debug_message("PP audio: music stopping over " + string(PP_AUDIO_FADE_STEPS) + " steps");
    return true;
}

/// One effect. kind is "sfx" (priority 5) or "ui" (priority 4), per spec 12 rule 2. When the channel limit is
/// reached the engine stops a sound of LOWER priority to free a channel: that is what audio_channel_num.htm says,
/// and the page never mentions age, so spec rule 9's "replaces the oldest of that kind" is not an engine
/// guarantee. Rule 9 is recorded as unproven in knowledge\PROVENANCE.md, and the channel budget plus the
/// priorities are what make the newest hit survive in practice. Returns the instance, or -1 when the sound is
/// missing.
function pp_audio_sfx(_kind, _id) {
    if (!is_struct(global.pp)) return -1;
    var _a = pp_audio_state();
    var _priority = PP_AUDIO_PRI_SFX;
    if (string_lower(string(_kind)) == "ui") _priority = PP_AUDIO_PRI_UI;
    if (is_undefined(_a.entries) || !variable_struct_exists(_a.entries, _id)) {
        _a.silent += 1;
        _a.asked += 1;
        show_debug_message("PP audio: sfx " + string(_id) + " silent, not in " + PP_AUDIO_SFX_DIR + "sfx.json");
        return -1;
    }
    var _sound = pp_audio_sound(_a, _id, _a.entries[$ _id]);
    if (_sound < 0) {
        _a.silent += 1;
        _a.asked += 1;
        return -1;
    }
    var _inst = audio_play_sound(_sound, _priority, false, PP_AUDIO_GAIN_SFX);
    _a.asked += 1;
    _a.played += 1;
    _a.last_cue = _id;
    array_push(_a.sfx_insts, _inst);
    // The instance list is the pause rule's working set, so it is capped; a long scene cannot grow it without bound.
    while (array_length(_a.sfx_insts) > PP_AUDIO_SFX_SLOTS) array_delete(_a.sfx_insts, 0, 1);
    // Card SFX-WIRE: this path is the text blip and the scene's own effects, so it writes the same one line per play
    // that pp_audio_play writes. Without it a blip could be asked for and heard with nothing in the log to prove it,
    // which is exactly what the cue check reads.
    show_debug_message("PP audio: " + string(_id) + " played, instance " + string(_inst));
    return _inst;
}

/// A text blip at half the effect level (spec 12 rule 6), pitched by speaker through the rule 3 table (spec 05).
/// pitch_role is a speaker name, or a blip letter already; an unknown name gets the narrator pitch rather than silence.
function pp_audio_blip(_pitch_role) {
    var _cue = pp_audio_blip_cue(_pitch_role);
    var _inst = pp_audio_sfx("ui", _cue);
    // The gain is set on the instance immediately in the same step it was played, so nothing at full level is heard
    // before the drop (audio_sound_gain.htm: a time of 0 changes the gain instantly).
    if (_inst > -1) audio_sound_gain(_inst, PP_AUDIO_GAIN_SFX * PP_AUDIO_GAIN_BLIP, 0);
    return _inst;
}

/// Focus rule (spec 12 rule 8). Losing focus pauses the music and stops the effects; regaining it resumes the music
/// where it stopped, because audio_resume_sound continues from the paused position rather than restarting. The
/// title theme is music too, so both instance slots are paused and resumed, not only the cue slot.
function pp_audio_focus(_paused) {
    if (!is_struct(global.pp)) return false;
    var _a = pp_audio_state();
    var _now = (_paused == true);
    if (_now == _a.focus_paused) return false;
    _a.focus_paused = _now;
    if (_now) {
        if (_a.music_inst > -1) audio_pause_sound(_a.music_inst);
        if (variable_struct_exists(_a, "theme_inst") && _a.theme_inst > -1) audio_pause_sound(_a.theme_inst);
        for (var i = 0; i < array_length(_a.sfx_insts); i++) {
            if (audio_is_playing(_a.sfx_insts[i])) audio_stop_sound(_a.sfx_insts[i]);
        }
        _a.sfx_insts = [];
        show_debug_message("PP audio: focus lost, music paused (cue and theme) and every effect stopped");
        return true;
    }
    if (_a.music_inst > -1) audio_resume_sound(_a.music_inst);
    if (variable_struct_exists(_a, "theme_inst") && _a.theme_inst > -1) audio_resume_sound(_a.theme_inst);
    show_debug_message("PP audio: focus back, music resumed where it stopped");
    return true;
}

/// One step of the bus, called from obj_pp_game. It polls the window for the focus rule and finishes a crossfade
/// whose time has run out: the outgoing instance is already at 0 by then, so stopping it cannot click.
function pp_audio_step() {
    if (!is_struct(global.pp)) return;
    var _a = pp_audio_state();
    pp_audio_focus(!window_has_focus());

    if (_a.fade_inst > -1 && current_time >= _a.fade_end_ms) pp_audio_fade_flush(_a);
}

/// The music cue playing now, or an empty string. The log and the tests read this instead of the instance id.
function pp_audio_music_cue() {
    if (!is_struct(global.pp) || !is_struct(global.pp.audio)) return "";
    return global.pp.audio.music_cue;
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

/// The title theme: an external OGG stream shipped as an included file, looped, and played at the music level. The
/// newest render is asked for first and older ones stay as fallbacks, so a new render lands with no code change.
function pp_audio_play_theme(_a) {
    // The key is absent until the first ask and left at -1 by pp_audio_theme_release once a cue takes the music
    // source, so the test is the same one duck and unduck make: absent or released. Testing existence alone would
    // make the theme unstartable for the rest of the run after the first cue.
    if (!variable_struct_exists(_a, "theme_inst") || _a.theme_inst <= -1) {
        var _candidates = pp_audio_theme_streams();
        for (var t = 0; t < array_length(_candidates); t += 1) {
            var _rel = _candidates[t];
            var _file = working_directory + _rel;
            if (!file_exists(_file)) continue;
            var _stream = audio_create_stream(_file);
            _a.theme_stream = _stream;
            _a.theme_file = _rel;
            // The theme is music, so it starts at the music level, not the engine default of 1.0, and a duck
            // already asked for multiplies that level instead of being lost.
            var _gain = PP_AUDIO_GAIN_MUSIC;
            if (variable_struct_exists(_a, "duck_db")) _gain *= power(10, _a.duck_db / 20);
            _a.theme_inst = audio_play_sound(_stream, PP_AUDIO_PRI_MUSIC, true, _gain);
            show_debug_message("PP audio: title_theme streaming " + _rel + ", instance "
                + string(_a.theme_inst) + ", gain " + string(_gain));
            _a.played += 1;
            return true;
        }
        show_debug_message("PP audio: no title theme stream in " + working_directory + "streams");
    }
    return false;
}

/// Ask for an effect by name. Returns true when a sound was played, false when the cue is silent because its sound
/// has not arrived yet. Every request is recorded and every play writes one log line, so a scripted run can be
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
    var _inst = audio_play_sound(_sound, PP_AUDIO_PRI_SFX, false);
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
    if (!variable_struct_exists(_a, "theme_inst") || _a.theme_inst <= -1) {
        show_debug_message("PP audio: title_theme ducked " + string(_db) + " dB in the state, no stream instance to turn down");
        return false;
    }
    // The duck multiplies the level the theme already sits at, so full is PP_AUDIO_GAIN_MUSIC and a duck is a
    // fraction of that, never a replacement that would quietly raise the theme back toward 1.0.
    var _gain = PP_AUDIO_GAIN_MUSIC * power(10, _db / 20);
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
    if (!variable_struct_exists(_a, "theme_inst") || _a.theme_inst <= -1) return false;
    audio_sound_gain(_a.theme_inst, PP_AUDIO_GAIN_MUSIC, 0);
    if (_was != 0) show_debug_message("PP audio: title_theme back to full after " + string(_was) + " dB");
    return true;
}
