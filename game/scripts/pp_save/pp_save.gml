/// pp_save: one save slot (spec 11). The game writes a versioned JSON document into a 64 KB buffer and hands it to the
/// asynchronous buffer functions, so no step ever waits on the disk, and it reads it back the same way and validates
/// every field before a single value is applied. The route ledger (spec 10) is saved as its four counters, its named
/// flags and the last fight's exit rows; the route name and the fight verdict are never stored, they are derived on read
/// by pp_ledger_route and pp_ledger_verdict_of.
/// Provenance: knowledge\PROVENANCE.md, entry "save, load and resume". Sources are specs\11, 10 and 01 plus the manual
/// pages named below, all read on 2026-10-20. Nothing was studied for this module.
///
/// Manual pages read for this module, 2026-10-20 (daily branch):
/// - Async Events/Save_Load: buffer_save_async and buffer_load_async end in this event, which holds the built in
///   async_load map with "id" (the value the function returned) and "status" (true when the transfer worked). The
///   documented poll is ds_map_find_value(async_load, "id") against the stored id, then "status".
/// - buffer_save_async / buffer_load_async: (buffer, filename, offset, size); a relative filename lands in the save
///   area's "default" folder, and every other file function would need that folder in the path. This module therefore
///   never uses file_exists or file_copy on the slot: the async load's "status" is the only existence test, which is
///   also why the title asks once at boot instead of guessing at a path.
/// - buffer_create (size, type, alignment), buffer_write and buffer_read (buffer_string carries a terminator,
///   buffer_text does not), buffer_tell, buffer_seek, buffer_delete.
/// - json_stringify, json_parse (it throws on invalid text, so every parse sits in a try/catch),
///   date_current_datetime and date_datetime_string.
///
/// File layout: a 4 byte byte-count, then the JSON text as a null terminated string, then nothing. The count is what
/// lets a truncated or foreign file be refused instead of half parsed (spec 11 numbers: a larger save is a clear
/// error, never a silent truncation).
///
/// Two writers, one slot (spec 11 rule 4): the panel at a save point the player confirms, and the entry autosave,
/// once per map entry, after the fade in, never while a scene, a dialogue or a fight owns the screen. The autosave is
/// silent on screen and still prints one line to the log, because a save that leaves no trace cannot be told apart
/// from a save that never happened (the lesson of the slot probe, 2026-10-22).

/// The state of the slot. Every async step is a state, and pp_save_async_event is the only thing that moves it on.
///
/// The two buffer fields hold a buffer handle or undefined, never a number. That is not a style choice: in this
/// runtime a buffer handle is a reference, not a number (measured 2026-10-20: typeof is "ref" and is_real is false),
/// so the old -1 sentinel made every "is there a buffer" test compare a reference against a number, and the
/// is_real guard in pp_save_payload_text refused every valid buffer. undefined is the one value that means
/// "no buffer" and is safe to test with is_undefined.
function pp_save_init() {
    global.pp.save = {
        state: PPSaveState.idle,
        payload: undefined,
        spare: undefined,
        request: -1,
        purpose: "",
        source: "main",
        main_loaded: false,
        present: false,
        data: undefined,
        error: "",
        note: "",
        panel: 0,
        ticks: 0,
        // The entry autosave (spec 11 rule 4). autosave_map is the map a fresh entry armed and "" when nothing is
        // armed; silent marks a save the player did not ask for, so the panel stays off the screen.
        autosave_map: "",
        silent: false
    };
    return global.pp.save;
}

function pp_save_name_main() {
    return PP_SAVE_SLOT;
}

function pp_save_name_backup() {
    return PP_SAVE_BACKUP;
}

/// Every key of the document, in the order spec 11 lists them. A save with a key outside this list, or without one of
/// them, is refused rather than partially read: a missing field is not a default, it is a file this build did not write.
/// The one exception is the optional key below, which pp_save_optional_keys names and which a save written before it
/// existed simply does not carry.
function pp_save_key_list() {
    return [
        "format", "game_version", "saved_at", "play_seconds", "map", "spawn", "x", "y",
        "hp", "max_hp", "powers", "items", "flags", "counters", "seen_scenes", "music",
        "fight_exits"
    ];
}

/// A key this build writes but a save written before it existed does not have (spec 10 rule 6). Absent means empty,
/// not damaged, so a player's older save keeps loading and the ledger starts with no rows.
function pp_save_optional_keys() {
    return ["fight_exits"];
}

/// Play time as a plain clock, because the title shows it to the player (spec 11 goal).
function pp_save_clock_text(_seconds) {
    var _s = max(0, floor(_seconds));
    var _m = floor(_s / 60);
    var _r = _s mod 60;
    if (_r < 10) return string(_m) + ":0" + string(_r);
    return string(_m) + ":" + string(_r);
}

function pp_save_busy() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return false;
    return _s.state == PPSaveState.reading || _s.state == PPSaveState.retrying
        || _s.state == PPSaveState.backing || _s.state == PPSaveState.backing_write
        || _s.state == PPSaveState.writing;
}

// ---------------------------------------------------------------------------------------------------------------
// The entry autosave (spec 11 rule 4: it fires on entering a new map, after the fade in, never in battle)

/// Arm one silent save for the map the player has just entered. Called by pp_overworld on a fresh map and on a map
/// change; the write itself waits for pp_save_autosave_step, so a scene that opens on the new map is never cut into.
function pp_save_autosave_arm(_map_id) {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    _s.autosave_map = string(_map_id);
    return true;
}

/// Drop the armed entry save. A load cancels it: a save that was just read is the state the player resumes, so
/// writing it straight back would rotate the backup for nothing (spec 11 rule 5).
function pp_save_autosave_cancel() {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    _s.autosave_map = "";
    return true;
}

/// The map id the armed entry save belongs to, or "" when nothing is armed.
function pp_save_autosave_armed() {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return "";
    return _s.autosave_map;
}

/// The app's fade is the one the player sees, and it is over when its direction is 0 and its alpha has reached 0.
/// Nothing else in the module reads the app frame; this is the one fact an entry save needs from it.
function pp_save_fade_settled() {
    var _app = global.pp.app;
    if (is_undefined(_app) || !is_struct(_app)) return true;
    if (_app.fade_dir != 0) return false;
    return _app.fade_alpha <= 0;
}

/// The screen has settled after an entry: on a map, no scene, no dialogue, no fight asked for, and the fade is done.
/// A scene plays over the overworld, so the mode alone would let a save land inside one; this is the test that does not.
function pp_save_entry_settled(_world) {
    if (pp_app_mode() != PPMode.overworld) return false;
    if (is_undefined(_world) || !is_struct(_world)) return false;
    if (pp_scene_running(_world.scene)) return false;
    if (!pp_dialogue_closed(_world.dialogue)) return false;
    if (_world.battle_request != "") return false;
    return pp_save_fade_settled();
}

/// True when no scene, dialogue or requested fight owns the screen. Used by the write as the second half of the
/// "only from the overworld" rule: a scene runs inside the overworld mode, so the mode check cannot see it.
function pp_save_screen_free() {
    var _world = global.pp.world;
    if (is_undefined(_world) || !is_struct(_world)) return true;
    if (pp_scene_running(_world.scene)) return false;
    if (!pp_dialogue_closed(_world.dialogue)) return false;
    if (_world.battle_request != "") return false;
    return true;
}

/// One step of the entry autosave. Fires once for the armed map, only after the fade and only on a settled screen,
/// and it is silent: the panel is for a save the player asked for. A transfer already in flight keeps it armed for
/// the next step instead of losing the save.
function pp_save_autosave_step(_world) {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    var _map = _s.autosave_map;
    if (!is_string(_map) || _map == "") return false;
    // The arm belongs to one world. A throwaway world built by the scene self test arms a map the player is not
    // standing on, and that arm is dropped here rather than written over the player's slot.
    if (!is_struct(_world) || !is_struct(_world.map) || _world.map.id != _map) {
        _s.autosave_map = "";
        return false;
    }
    if (pp_save_busy()) return false;
    if (!pp_save_entry_settled(_world)) return false;
    _s.autosave_map = "";
    if (!pp_save_write("entry " + string(_map), true)) return false;
    // Silence on screen, not in the log: a save that leaves no line cannot be told from one that never happened
    // (the lesson of the slot probe, 2026-10-22).
    show_debug_message("PP: autosave, " + string(_map) + " " + string(_world.hero.tx) + "," + string(_world.hero.ty));
    return true;
}

/// A save that was read and validated, and can be applied. A save that was just written is "saved", not "ready":
/// nothing was read back, so nothing here claims it loads.
function pp_save_ready() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return false;
    return _s.state == PPSaveState.ready && !is_undefined(_s.data);
}

/// The title line: where the player is and how long they have played (spec 11 goal). Empty when there is no save.
function pp_save_status_line() {
    if (!pp_save_ready()) return "";
    var _d = global.pp.save.data;
    var _map = pp_data_find(global.pp_data.maps.maps, _d.map);
    var _name = _d.map;
    if (!is_undefined(_map)) _name = _map.name;
    return "Continue: " + string(_name) + ", " + pp_save_clock_text(_d.play_seconds);
}

/// The second title line: a plain sentence while the slot is being checked, when a file was refused, or when the
/// backup was the one that loaded. Plain words, no codes (spec 11 rule 1).
function pp_save_title_note() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return "";
    if (pp_save_busy()) return "checking the save";
    if (_s.state == PPSaveState.failed) return _s.error;
    if (_s.note != "") return _s.note;
    return "";
}

/// Ask the slot what it holds, once, when the title appears. The answer arrives through pp_save_async_event. A slot
/// that was just written is asked again too, because nothing has read that file back yet.
function pp_save_title_start() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return false;
    if (_s.state != PPSaveState.idle && _s.state != PPSaveState.saved) return false;
    return pp_save_read("title");
}

/// Start a new run: a fresh ledger, the clock at zero, and the slice's first map. The save file is not touched; it is
/// only replaced when the player next saves (spec 11 out of scope: no slot deletion screen).
function pp_save_new_game() {
    global.pp_ledger = pp_ledger_new();
    global.pp.world = undefined;
    var _s = global.pp.save;
    if (!is_undefined(_s)) {
        _s.ticks = 0;
        _s.data = undefined;
        _s.note = "";
        _s.state = PPSaveState.idle;
    }
    var _slice = global.pp_data.slice;
    // Card ASSEMBLE: a new run opens on the ship lower deck, rm_pp_ship, and the ship map is played from
    // data\maps\ship_sample.json. No scene is played on entry, so the player walks the moment the fade lifts.
    pp_app_request(PPMode.overworld, { map_id: PP_NEW_GAME_MAP, spawn: PP_NEW_GAME_SPAWN, scene: "" });
    // The room the run is played in. obj_pp_game is persistent, so it is the same controller instance inside
    // rm_pp_ship; the room exists so the frame has a real home and the map is not drawn inside the title room.
    // asset_get_index keeps a build that predates the room from failing to compile, and the request above
    // still plays the map either way.
    var _room = asset_get_index(PP_NEW_GAME_ROOM);
    if (_room != -1 && room != _room) room_goto(_room);
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// Writing

/// Save now, at a save point the caller has already established (spec 11 rule 4). Never from a battle: the mode check
/// is the mechanical half of "only at a save point, never mid battle", the trigger data is the other half.
///
/// _purpose names the point for the player's sake (a save row's id is a label, not a row in a table), and _silent
/// marks the entry autosave, whose panel never appears. A scene plays over the overworld, so the mode check alone
/// does not keep a save out of one; pp_save_screen_free is the check that does, and the refusal is printed by name.
function pp_save_write(_purpose, _silent) {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    if (pp_save_busy()) return false;
    if (pp_app_mode() != PPMode.overworld) {
        show_debug_message("PP: save refused, the game is not on a map");
        return false;
    }
    if (!pp_save_screen_free()) {
        show_debug_message("PP: save refused, a scene or a dialogue is running");
        return false;
    }

    var _snapshot = pp_save_snapshot();
    if (is_undefined(_snapshot)) return false;
    var _json = json_stringify(_snapshot, true);
    if (!is_string(_json) || _json == "") {
        pp_save_fail("the save could not be written as text");
        return false;
    }
    if (string_byte_length(_json) > PP_SAVE_BUFFER - 5) {
        pp_save_fail("the save is larger than one slot can hold");
        return false;
    }

    pp_save_free();
    var _buf = buffer_create(PP_SAVE_BUFFER, buffer_fixed, 1);
    var _e1 = buffer_write(_buf, buffer_u32, string_byte_length(_json));
    var _e2 = buffer_write(_buf, buffer_string, _json);
    if (_e1 != 0 || _e2 != 0) {
        buffer_delete(_buf);
        pp_save_fail("the save is larger than one slot can hold");
        return false;
    }
    _s.payload = _buf;
    _s.purpose = _purpose;
    _s.source = "main";
    _s.error = "";
    _s.note = "";
    _s.panel = 0;
    _s.silent = (_silent == true);

    // Rotate the file only when this session read it as a good save. A corrupt file is never copied over the last
    // good backup, which is the one property spec 11 rule 2 exists for.
    if (_s.present) {
        // Rotate by reading the current file back through the async pair, so there is no synchronous copy and no path
        // guess. The request id is 0 for the first asynchronous transfer in a process (measured 2026-10-20), so the
        // test for "the transfer did not start" is a negative id, never "less than or equal to zero".
        _s.spare = buffer_create(PP_SAVE_BUFFER, buffer_fixed, 1);
        var _id = buffer_load_async(_s.spare, pp_save_name_main(), 0, PP_SAVE_BUFFER);
        if (_id >= 0) {
            _s.request = _id;
            _s.state = PPSaveState.backing;
            return true;
        }
        // The runtime refused the transfer, so nothing will report back. The buffer is abandoned rather than freed:
        // the runtime may still be holding it, and buffer_delete would raise "in use" (see pp_save_read).
        _s.spare = undefined;
    }

    pp_save_start_write();
    return true;
}

/// Hand the payload to the disk. The buffer stays alive until the event reports back, because the transfer reads it.
function pp_save_start_write() {
    var _s = global.pp.save;
    var _id = buffer_save_async(_s.payload, pp_save_name_main(), 0, buffer_tell(_s.payload));
    if (_id < 0) {
        // The runtime refused to start the transfer, so nothing will ever report back and it may still be holding
        // this buffer. Abandon it rather than free it: one lost 64 KB is cheaper than the player's window.
        _s.payload = undefined;
        pp_save_fail("the save could not be started");
        return false;
    }
    _s.request = _id;
    _s.state = PPSaveState.writing;
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// Reading

/// Read the slot. On a failed or invalid main file the backup is tried once (spec 11 rule 3), and only then is the
/// player told, in plain words, that the save could not be read.
///
/// There is no existence test before the buffer is made. A relative name given to buffer_load_async lands in the
/// save area's "default" folder, while file_exists resolves the same name against the save area root, so a
/// file_exists check cannot see the slot this module writes (measured 2026-10-20: file_exists("pp_save_01.json")
/// was false while file_exists("default/pp_save_01.json") was true, and the slot lived in the latter). The async
/// load's own "status" is the honest existence test, which is also what the manual describes.
function pp_save_read(_from) {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    if (pp_save_busy()) return false;
    pp_save_free();
    _s.source = "main";
    _s.purpose = _from;
    _s.error = "";
    _s.note = "";
    _s.panel = 0;
    _s.main_loaded = false;

    _s.spare = buffer_create(PP_SAVE_BUFFER, buffer_fixed, 1);
    // The request id is 0 for the first asynchronous transfer in a process (measured 2026-10-20), so the test for
    // "the transfer did not start" is a negative id. The old test took the zero id as a refusal, and then
    // pp_save_read_backup deleted a buffer the runtime was still holding: "Cannot delete buffer, it's in use by
    // 1 others", which is the crash this card was raised for.
    var _id = buffer_load_async(_s.spare, pp_save_name_main(), 0, PP_SAVE_BUFFER);
    if (_id < 0) {
        // The runtime refused to start the transfer, so nothing will ever report back. The buffer is abandoned
        // rather than freed: the runtime may still be holding it, and one lost 64 KB is cheaper than the window.
        _s.spare = undefined;
        return pp_save_read_backup();
    }
    _s.request = _id;
    _s.state = PPSaveState.reading;
    return true;
}

/// Try the backup once. Only ever deletes a buffer that a transfer has already reported back, which is the one moment
/// the runtime no longer holds it.
function pp_save_read_backup() {
    var _s = global.pp.save;
    if (!is_undefined(_s.spare)) {
        buffer_delete(_s.spare);
        _s.spare = undefined;
    }
    _s.source = "backup";
    _s.spare = buffer_create(PP_SAVE_BUFFER, buffer_fixed, 1);
    var _id = buffer_load_async(_s.spare, pp_save_name_backup(), 0, PP_SAVE_BUFFER);
    if (_id < 0) {
        // Refused, so nothing will report back and the runtime may still be holding this buffer. Abandon it.
        _s.spare = undefined;
        return pp_save_absent();
    }
    _s.request = _id;
    _s.state = PPSaveState.retrying;
    return true;
}

/// No file at all, both names refused to load. Not an error: a player who has never saved sees a plain title.
function pp_save_absent() {
    var _s = global.pp.save;
    if (!is_undefined(_s.spare)) {
        buffer_delete(_s.spare);
        _s.spare = undefined;
    }
    _s.state = PPSaveState.absent;
    _s.data = undefined;
    _s.error = "";
    _s.request = -1;
    return true;
}

function pp_save_fail(_message) {
    var _s = global.pp.save;
    _s.state = PPSaveState.failed;
    _s.error = _message;
    _s.panel = 0;
    _s.request = -1;
    // Nothing is in flight when this is called: a transfer that cannot start, or one that has already reported. So the
    // buffers can be released here and a failed save never leaves 64 KB behind.
    pp_save_free();
    show_debug_message("PP: save problem, " + string(_message));
    return true;
}

/// Free every buffer this module owns. Only ever called when nothing is in flight, because the runner reads a buffer
/// for the length of a transfer.
function pp_save_free() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return false;
    if (!is_undefined(_s.payload)) buffer_delete(_s.payload);
    _s.payload = undefined;
    if (!is_undefined(_s.spare)) buffer_delete(_s.spare);
    _s.spare = undefined;
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// The asynchronous event

/// Called from obj_pp_game's Save/Load event only. One id matches one request; anything else (an audio group load
/// later, for instance) is left alone, so this module never mistakes another transfer's callback for its own.
function pp_save_async_event() {
    var _s = global.pp.save;
    if (is_undefined(_s) || !is_struct(_s)) return false;
    var _id = ds_map_find_value(async_load, "id");
    var _ok = ds_map_find_value(async_load, "status");
    // The request id is 0 for the first asynchronous transfer in a process (measured 2026-10-20), so the guard is
    // "no request" as a negative number, not "less than or equal to zero".
    if (is_undefined(_id) || _s.request < 0 || _id != _s.request) return false;

    switch (_s.state) {
        case PPSaveState.backing:
            // The copy is in _s.spare as raw file bytes. Re-emit those bytes into a buffer whose length is known, and
            // then let the same async pair write the backup. No sync file call, no "default" folder guess.
            if (_ok) {
                var _text = pp_save_payload_text(_s.spare);
                if (is_string(_text)) {
                    if (!is_undefined(_s.spare)) buffer_delete(_s.spare);
                    _s.spare = undefined;
                    var _bak = buffer_create(PP_SAVE_BUFFER, buffer_fixed, 1);
                    var _b1 = buffer_write(_bak, buffer_u32, string_byte_length(_text));
                    var _b2 = buffer_write(_bak, buffer_string, _text);
                    if (_b1 == 0 && _b2 == 0) {
                        var _wid = buffer_save_async(_bak, pp_save_name_backup(), 0, buffer_tell(_bak));
                        if (_wid >= 0) {
                            _s.spare = _bak;
                            _s.request = _wid;
                            _s.state = PPSaveState.backing_write;
                            return true;
                        }
                    }
                    // The backup write could not be started, so nothing will report back and the runtime may still be
                    // holding this buffer. Abandon it rather than free it.
                    _s.spare = undefined;
                }
            }
            // No usable current file: write the new one anyway. A save that does not happen because a backup could not
            // be made would be the worse failure.
            if (!is_undefined(_s.spare)) {
                buffer_delete(_s.spare);
                _s.spare = undefined;
            }
            return pp_save_start_write();

        case PPSaveState.backing_write:
            if (!_ok) _s.error = "the backup was not written";
            if (!is_undefined(_s.spare)) {
                buffer_delete(_s.spare);
                _s.spare = undefined;
            }
            return pp_save_start_write();

        case PPSaveState.writing:
            if (!is_undefined(_s.payload)) {
                buffer_delete(_s.payload);
                _s.payload = undefined;
            }
            _s.panel = 0;
            _s.request = -1;
            if (_ok) {
                _s.state = PPSaveState.saved;
                _s.present = true;
                return true;
            }
            pp_save_fail("the save could not be written");
            return false;

        case PPSaveState.reading:
            _s.main_loaded = _ok;
            if (_ok && pp_save_parse(_s.spare)) {
                if (!is_undefined(_s.spare)) {
                    buffer_delete(_s.spare);
                    _s.spare = undefined;
                }
                _s.state = PPSaveState.ready;
                _s.present = true;
                _s.request = -1;
                _s.panel = 0;
                return true;
            }
            return pp_save_read_backup();

        case PPSaveState.retrying:
            if (_ok && pp_save_parse(_s.spare)) {
                if (!is_undefined(_s.spare)) {
                    buffer_delete(_s.spare);
                    _s.spare = undefined;
                }
                _s.state = PPSaveState.ready;
                // The main file is the damaged one here, so present stays false: the next write must not rotate that
                // file over the backup that just proved itself.
                _s.request = -1;
                _s.panel = 0;
                _s.note = "the save was damaged, so the backup was loaded";
                return true;
            }
            if (!is_undefined(_s.spare)) {
                buffer_delete(_s.spare);
                _s.spare = undefined;
            }
            _s.request = -1;
            if (!_s.main_loaded && !_ok) {
                return pp_save_absent();
            }
            var _why = _s.error;
            if (_why == "") _why = "the save file is unreadable";
            return pp_save_fail(_why);
    }
    return false;
}

// ---------------------------------------------------------------------------------------------------------------
// Parsing and validation

/// The JSON text out of a file buffer, or undefined when the header does not agree with the bytes. The length prefix is
/// what turns a truncated file into a clear error instead of a half parsed document.
///
/// The buffer handle is not a number in this runtime (measured 2026-10-20: typeof is "ref" and is_real is false), so
/// the old "is it a number, and is it non negative" guard refused every valid buffer and made every load fail with
/// "the save file is not whole". The only test that is true of a real buffer and false of nothing is is_undefined,
/// and the byte count and the string are checked afterwards, so a wrong buffer still cannot slip through.
function pp_save_payload_text(_buf) {
    if (is_undefined(_buf)) return undefined;
    buffer_seek(_buf, buffer_seek_start, 0);
    var _size = buffer_read(_buf, buffer_u32);
    // A number read out of a buffer is an int64 in this runtime (measured 2026-10-20: typeof is "int64" and is_real
    // is false, while is_numeric is true), so is_real would refuse a perfectly good length prefix. is_numeric is the
    // test that is true of every number and false of a string.
    if (!is_numeric(_size) || _size <= 0 || _size > PP_SAVE_BUFFER - 5) return undefined;
    var _text = buffer_read(_buf, buffer_string);
    if (!is_string(_text)) return undefined;
    if (string_byte_length(_text) != _size) return undefined;
    return _text;
}

/// Read one file buffer into a validated save. False leaves a plain sentence in _s.error.
function pp_save_parse(_buf) {
    var _s = global.pp.save;
    var _text = pp_save_payload_text(_buf);
    if (!is_string(_text)) {
        _s.error = "the save file is not whole";
        return false;
    }
    var _parsed = undefined;
    try {
        _parsed = json_parse(_text);
    } catch (_e) {
        _s.error = "the save file is not readable text";
        return false;
    }
    if (!is_struct(_parsed)) {
        _s.error = "the save file does not hold a save";
        return false;
    }
    var _problem = pp_save_validate(_parsed);
    if (_problem != "") {
        _s.error = _problem;
        return false;
    }
    _s.data = _parsed;
    _s.error = "";
    // A read that is accepted prints one line, the mirror of the failure line in pp_save_fail. Silence cannot tell
    // "the slot was read and accepted" from "the slot was never asked", which is exactly how a killed runtime run was
    // read as a clean load on 2026-10-22.
    show_debug_message("PP: save read and accepted, music " + string(_parsed.music));
    return true;
}

/// A whole number in range, or undefined. Used for every number in the file, so a string "20" and a fraction are both
/// refused rather than silently coerced.
function pp_save_number(_value, _min, _max) {
    if (!is_real(_value)) return undefined;
    if (_value != floor(_value)) return undefined;
    if (_value < _min || _value > _max) return undefined;
    return _value;
}

function pp_save_boolish(_value) {
    if (is_bool(_value)) return true;
    if (!is_real(_value)) return false;
    return _value == 0 || _value == 1;
}

function pp_save_strings_have(_list, _value) {
    if (!is_array(_list)) return false;
    for (var i = 0; i < array_length(_list); i++) {
        if (_list[i] == _value) return true;
    }
    return false;
}

/// The scene a derived scene flag stands for, or "" when the name is not one of ours.
function pp_save_scene_flag_id(_name) {
    if (!is_string(_name)) return "";
    if (string_copy(_name, 1, 6) != "scene_") return "";
    return string_delete(_name, 1, 6);
}

/// A flag name this build could have written: a story flag from data\flags.json, a scene flag for a real scene, or a
/// derived trigger flag. Anything else is a typo or a foreign file, and the save says so by name (spec 10 rule 3).
function pp_save_flag_allowed(_name) {
    if (!is_string(_name) || _name == "") return false;
    if (string_length(_name) > PP_SAVE_MAX_FLAG_CHARS) return false;
    if (string_pos(" ", _name) > 0) return false;
    var _known = [];
    if (is_struct(global.pp_data.flags) && is_array(global.pp_data.flags.flags)) _known = global.pp_data.flags.flags;
    if (pp_save_strings_have(_known, _name)) return true;
    var _scene = pp_save_scene_flag_id(_name);
    if (_scene != "") return variable_struct_exists(global.pp_data.scene_by_id, _scene);
    // Trigger flags are derived from a map and a tile by pp_overworld_trigger_flag. Their exact set is a function of
    // the map data, so the name shape is checked here and the tile itself is not second guessed.
    if (string_copy(_name, 1, 5) == "trig_") return true;
    return false;
}

function pp_save_counter_keys() {
    return ["bosses_killed", "bosses_spared", "regulars_killed", "regulars_spared"];
}

/// One exit row of the last fight, checked as strictly as every other record in the file (spec 10 rule 6). The enemy
/// id is checked for shape and not resolved against data\enemies, because a row is a record of what already happened:
/// a later balance change that retires an enemy must not make a player's save unreadable.
function pp_save_exit_row_problem(_row) {
    var _shape = "a saved fight exit is not a record of an id, an exit and a round";
    if (!is_struct(_row)) return _shape;
    if (array_length(variable_struct_get_names(_row)) != 3) return _shape;
    if (!variable_struct_exists(_row, "id") || !variable_struct_exists(_row, "exit")
        || !variable_struct_exists(_row, "round")) return _shape;
    if (!is_string(_row.id) || _row.id == "") return "a saved fight exit id is not a name";
    if (string_length(_row.id) > PP_SAVE_MAX_FLAG_CHARS) return "a saved fight exit id is too long";
    if (string_pos(" ", _row.id) > 0) return "a saved fight exit id is not a name";
    if (is_undefined(pp_save_number(_row.exit, PPExit.down, PPExit.turned))) {
        return "a saved fight exit is not one of the three exits";
    }
    if (is_undefined(pp_save_number(_row.round, 0, PP_SAVE_MAX_ROUND))) return "a saved fight exit round is out of range";
    return "";
}

function pp_save_exit_rows_problem(_rows) {
    if (!is_array(_rows)) return "the save fight exits are not a list";
    if (array_length(_rows) > PP_SAVE_MAX_EXIT_ROWS) return "the save records more fight exits than one fight holds";
    for (var i = 0; i < array_length(_rows); i++) {
        var _problem = pp_save_exit_row_problem(_rows[i]);
        if (_problem != "") return _problem;
    }
    return "";
}

/// The whole contract of the file, checked in the order the player would notice it: format first, so an unknown file is
/// refused before any other field is looked at, then the key set, then every id and every number.
function pp_save_validate(_d) {
    // Validation reads the map, spawn, item, power, scene, flag and audio lists, so a data failure is named here rather
    // than crashing inside a lookup.
    if (!is_struct(global.pp_data) || !is_struct(global.pp_data.maps)) return "the data did not load, so no save can be read";
    if (!variable_struct_exists(_d, "format")) return "the save file has no format";
    var _format = pp_save_number(_d.format, -2147483647, 2147483647);
    if (is_undefined(_format)) return "the save format is not a number";
    if (_format != PP_SAVE_FORMAT) {
        return "the save is format " + string(_format) + ", and this build reads format " + string(PP_SAVE_FORMAT);
    }

    var _keys = pp_save_key_list();
    var _names = variable_struct_get_names(_d);
    for (var i = 0; i < array_length(_names); i++) {
        if (!pp_save_strings_have(_keys, _names[i])) return "the save has a field this build does not know: " + string(_names[i]);
    }
    for (var j = 0; j < array_length(_keys); j++) {
        if (!variable_struct_exists(_d, _keys[j])) {
            // The optional key is here so a save written before it existed still loads. Absent means empty.
            if (pp_save_strings_have(pp_save_optional_keys(), _keys[j])) continue;
            return "the save is missing the field " + string(_keys[j]);
        }
    }

    if (!is_string(_d.game_version) || _d.game_version == "") return "the save has no game version";
    if (!is_string(_d.saved_at)) return "the save has no save time";
    if (is_undefined(pp_save_number(_d.play_seconds, 0, PP_SAVE_MAX_PLAY_SECONDS))) return "the play time is out of range";

    if (!is_string(_d.map)) return "the save map is not a name";
    var _map = pp_data_find(global.pp_data.maps.maps, _d.map);
    if (is_undefined(_map)) return "the save names a map this build does not have: " + string(_d.map);
    if (!is_string(_d.spawn)) return "the save spawn is not a name";
    if (!is_struct(_map.spawns) || !variable_struct_exists(_map.spawns, _d.spawn)) {
        return "the save names a spawn point this build does not have: " + string(_d.spawn);
    }
    if (is_undefined(pp_save_number(_d.x, 0, _map.width - 1))) return "the save x is outside the map";
    if (is_undefined(pp_save_number(_d.y, 0, _map.height - 1))) return "the save y is outside the map";

    var _max_hp = pp_save_number(_d.max_hp, 1, PP_SAVE_MAX_HP);
    if (is_undefined(_max_hp)) return "the save max hp is out of range";
    var _hp = pp_save_number(_d.hp, 0, _max_hp);
    if (is_undefined(_hp)) return "the save hp is out of range";

    if (!is_array(_d.powers)) return "the save powers are not a list";
    for (var p = 0; p < array_length(_d.powers); p++) {
        if (!is_string(_d.powers[p])) return "a saved power is not a name";
        if (!variable_struct_exists(global.pp_data.power_by_id, _d.powers[p])) {
            return "the save names a power this build does not have: " + string(_d.powers[p]);
        }
    }

    if (!is_array(_d.items)) return "the save items are not a list";
    for (var t = 0; t < array_length(_d.items); t++) {
        var _bag = _d.items[t];
        if (!is_struct(_bag)) return "a saved item is not a record";
        var _bag_names = variable_struct_get_names(_bag);
        if (array_length(_bag_names) != 2) return "a saved item has fields it should not have";
        if (!variable_struct_exists(_bag, "id") || !variable_struct_exists(_bag, "count")) {
            return "a saved item needs an id and a count";
        }
        if (!is_string(_bag.id)) return "a saved item id is not a name";
        if (!variable_struct_exists(global.pp_data.item_by_id, _bag.id)) {
            return "the save names an item this build does not have: " + string(_bag.id);
        }
        if (is_undefined(pp_save_number(_bag.count, 1, PP_SAVE_MAX_ITEM_COUNT))) return "a saved item count is out of range";
    }

    if (!is_struct(_d.flags)) return "the save flags are not a table";
    var _flag_names = variable_struct_get_names(_d.flags);
    var _scene_ids = [];
    for (var f = 0; f < array_length(_flag_names); f++) {
        var _fname = _flag_names[f];
        if (!pp_save_flag_allowed(_fname)) return "the save carries a flag this build does not know: " + string(_fname);
        if (!pp_save_boolish(_d.flags[$ _fname])) return "the flag " + string(_fname) + " is not true or false";
        var _sf = pp_save_scene_flag_id(_fname);
        if (_sf != "") array_push(_scene_ids, _sf);
    }

    if (!is_struct(_d.counters)) return "the save counters are not a table";
    var _counter_keys = pp_save_counter_keys();
    var _counter_names = variable_struct_get_names(_d.counters);
    if (array_length(_counter_names) != array_length(_counter_keys)) return "the save counters are not the four the route reads";
    for (var c = 0; c < array_length(_counter_names); c++) {
        if (!pp_save_strings_have(_counter_keys, _counter_names[c])) {
            return "the save counters carry a name the route does not read: " + string(_counter_names[c]);
        }
    }
    for (var k = 0; k < array_length(_counter_keys); k++) {
        var _count = pp_save_number(_d.counters[$ _counter_keys[k]], 0, PP_SAVE_MAX_COUNTER);
        if (is_undefined(_count)) return "the counter " + string(_counter_keys[k]) + " is out of range";
    }

    // The last fight's exit rows (spec 10 rule 6). The key is optional, so an older save has none and starts empty.
    if (variable_struct_exists(_d, "fight_exits")) {
        var _exits_problem = pp_save_exit_rows_problem(_d.fight_exits);
        if (_exits_problem != "") return _exits_problem;
    }

    if (!is_array(_d.seen_scenes)) return "the save seen scenes are not a list";
    for (var v = 0; v < array_length(_d.seen_scenes); v++) {
        if (!is_string(_d.seen_scenes[v])) return "a seen scene is not a name";
        if (!variable_struct_exists(global.pp_data.scene_by_id, _d.seen_scenes[v])) {
            return "the save names a scene this build does not have: " + string(_d.seen_scenes[v]);
        }
    }
    // The flags are the record and seen_scenes is the same fact written plainly. Two copies of one fact are only safe
    // when they are checked against each other, which is what the next two loops do.
    for (var a = 0; a < array_length(_scene_ids); a++) {
        if (!pp_save_strings_have(_d.seen_scenes, _scene_ids[a])) {
            return "the save flags and seen scenes disagree about the scene " + string(_scene_ids[a]);
        }
    }
    for (var b = 0; b < array_length(_d.seen_scenes); b++) {
        var _seen_name = "scene_" + string(_d.seen_scenes[b]);
        if (!variable_struct_exists(_d.flags, _seen_name)) {
            return "the save seen scenes and flags disagree about the scene " + string(_d.seen_scenes[b]);
        }
        if (!_d.flags[$ _seen_name]) {
            return "the save seen scenes and flags disagree about the scene " + string(_d.seen_scenes[b]);
        }
    }

    if (!is_string(_d.music)) return "the save music is not a name";
    if (_d.music != "") {
        if (!variable_struct_exists(global.pp_data.audio_by_id, _d.music)) {
            return "the save names music this build does not have: " + string(_d.music);
        }
        var _track = global.pp_data.audio_by_id[$ _d.music];
        if (!is_struct(_track) || !variable_struct_exists(_track, "kind") || _track.kind != "music") {
            return "the save names a sound that is not music: " + string(_d.music);
        }
    }

    return "";
}

// ---------------------------------------------------------------------------------------------------------------
// The snapshot

/// The live game as a save document, or undefined when there is no world to save. Nothing here reads the clock for
/// gameplay, and nothing stores a route name: counters and flags only (spec 10). The ledger's story stage is not in the
/// document either: spec 10 records the four counters and the flags and nothing else, so the stage stays memory only
/// until a spec says a save carries it.
function pp_save_snapshot() {
    var _w = global.pp.world;
    if (is_undefined(_w) || !is_struct(_w)) return undefined;
    var _ledger = global.pp_ledger;
    var _party = global.pp_data.party.characters[0];
    var _max_hp = _party.max_hp;
    var _hp = _max_hp;
    if (variable_struct_exists(_ledger, "hp")) _hp = clamp(_ledger.hp, 0, _max_hp);

    return {
        format: PP_SAVE_FORMAT,
        game_version: PP_SAVE_GAME_VERSION,
        saved_at: date_datetime_string(date_current_datetime()),
        play_seconds: floor(global.pp.save.ticks / PP_STEPS_PER_SECOND),
        map: _w.map.id,
        spawn: _w.spawn_name,
        x: _w.hero.tx,
        y: _w.hero.ty,
        hp: _hp,
        max_hp: _max_hp,
        powers: pp_save_snapshot_powers(_ledger),
        items: pp_save_snapshot_items(_ledger, _party),
        flags: pp_save_snapshot_flags(_ledger),
        counters: {
            bosses_killed: _ledger.counters.bosses_killed,
            bosses_spared: _ledger.counters.bosses_spared,
            regulars_killed: _ledger.counters.regulars_killed,
            regulars_spared: _ledger.counters.regulars_spared
        },
        fight_exits: pp_save_snapshot_exits(_ledger),
        seen_scenes: pp_save_snapshot_scenes(_ledger),
        music: _w.music
    };
}

/// The last fight's exit rows, as an id, an exit number and a round (spec 10 rule 6). The fight verdict is not written:
/// it is a function of these rows, so it is recomputed on load rather than kept as a second copy that could disagree.
function pp_save_snapshot_exits(_ledger) {
    var _out = [];
    if (!variable_struct_exists(_ledger, "exits") || !is_array(_ledger.exits)) return _out;
    for (var i = 0; i < array_length(_ledger.exits); i++) {
        var _row = _ledger.exits[i];
        if (!is_struct(_row)) continue;
        array_push(_out, { id: _row.id, exit: _row.exit, round: _row.round });
    }
    return _out;
}

/// Power ids only. The full row is rebuilt from data on load, so a balance change lands on the next load instead of
/// being frozen into every old save.
function pp_save_snapshot_powers(_ledger) {
    var _out = [];
    if (!variable_struct_exists(_ledger, "powers") || !is_array(_ledger.powers)) return _out;
    for (var i = 0; i < array_length(_ledger.powers); i++) {
        var _power = _ledger.powers[i];
        if (is_struct(_power) && variable_struct_exists(_power, "id")) array_push(_out, _power.id);
    }
    return _out;
}

/// Item ids with a count, collapsed from the one record per copy the battle uses. A fresh run records the party's
/// starting items, which is the inventory the player actually has before the first fight.
function pp_save_snapshot_items(_ledger, _party) {
    var _bags = [];
    var _source = [];
    if (variable_struct_exists(_ledger, "items") && is_array(_ledger.items) && array_length(_ledger.items) > 0) {
        _source = _ledger.items;
    } else if (variable_struct_exists(_party, "starting_items")) {
        _source = _party.starting_items;
    }
    for (var i = 0; i < array_length(_source); i++) {
        var _row = _source[i];
        if (!is_struct(_row) || !variable_struct_exists(_row, "id")) continue;
        var _found = -1;
        for (var j = 0; j < array_length(_bags); j++) {
            if (_bags[j].id == _row.id) _found = j;
        }
        if (_found >= 0) {
            _bags[_found].count += variable_struct_exists(_row, "count") ? _row.count : 1;
        } else {
            array_push(_bags, { id: _row.id, count: variable_struct_exists(_row, "count") ? _row.count : 1 });
        }
    }
    return _bags;
}

function pp_save_snapshot_flags(_ledger) {
    var _out = {};
    if (!is_struct(_ledger.flags)) return _out;
    var _names = variable_struct_get_names(_ledger.flags);
    for (var i = 0; i < array_length(_names); i++) {
        // Only the flags that are set are written. A false flag is the absence of a flag, in the ledger and here.
        if (_ledger.flags[$ _names[i]]) _out[$ _names[i]] = true;
    }
    return _out;
}

/// The scene flags written plainly, for a reader of the file. On load the flags are the record and this list is checked
/// against them, so the pair can never drift silently.
function pp_save_snapshot_scenes(_ledger) {
    var _out = [];
    if (!is_struct(_ledger.flags)) return _out;
    var _names = variable_struct_get_names(_ledger.flags);
    for (var i = 0; i < array_length(_names); i++) {
        var _scene = pp_save_scene_flag_id(_names[i]);
        if (_scene != "" && _ledger.flags[$ _names[i]]) array_push(_out, _scene);
    }
    return _out;
}

// ---------------------------------------------------------------------------------------------------------------
// Applying a validated save

/// Put a validated save back into the live game. Nothing is applied until the whole document has passed validation, so
/// a failed load leaves the run, and the file, exactly as they were (spec 11 rule 3).
function pp_save_apply() {
    var _s = global.pp.save;
    if (!pp_save_ready()) return false;
    var _d = _s.data;

    var _ledger = pp_ledger_new();
    _ledger.counters = {
        bosses_killed: _d.counters.bosses_killed,
        bosses_spared: _d.counters.bosses_spared,
        regulars_killed: _d.counters.regulars_killed,
        regulars_spared: _d.counters.regulars_spared
    };
    var _flag_names = variable_struct_get_names(_d.flags);
    for (var i = 0; i < array_length(_flag_names); i++) {
        var _name = _flag_names[i];
        _ledger.flags[$ _name] = (_d.flags[$ _name] != 0);
    }
    _ledger.hp = _d.hp;

    // The last fight's rows come back, and the verdict is recomputed from them by the ledger's own rule, so a loaded
    // ledger reads exactly like the one that was saved (spec 10 rule 6). A save written before the rows existed has
    // none, which is an empty record and a quiet verdict, not an error.
    _ledger.exits = [];
    _ledger.verdict = PPFightVerdict.quiet;
    if (variable_struct_exists(_d, "fight_exits")) {
        for (var e = 0; e < array_length(_d.fight_exits); e++) {
            var _exit_row = _d.fight_exits[e];
            array_push(_ledger.exits, { id: _exit_row.id, exit: _exit_row.exit, round: _exit_row.round });
        }
        _ledger.verdict = pp_ledger_verdict_of(_ledger.exits);
    }

    var _powers = [];
    for (var p = 0; p < array_length(_d.powers); p++) {
        var _power = global.pp_data.power_by_id[$ _d.powers[p]];
        if (!is_undefined(_power)) array_push(_powers, _power);
    }
    _ledger.powers = _powers;

    var _items = [];
    for (var t = 0; t < array_length(_d.items); t++) {
        var _bag = _d.items[t];
        var _row = global.pp_data.item_by_id[$ _bag.id];
        if (is_undefined(_row)) continue;
        for (var n = 0; n < _bag.count; n++) {
            array_push(_items, { id: _row.id, name: _row.name, heal: _row.heal });
        }
    }
    _ledger.items = _items;
    global.pp_ledger = _ledger;

    _s.ticks = _d.play_seconds * PP_STEPS_PER_SECOND;

    var _world = pp_overworld_new(_d.map, _d.spawn);
    if (is_undefined(_world)) {
        pp_save_fail("the saved map did not load");
        return false;
    }
    // A load lands on the map the save was taken on, at the state it recorded, so the entry is not written back
    // (spec 11 rule 5). The arm pp_overworld_new set for this entry is dropped here.
    pp_save_autosave_cancel();
    // The saved tile is the save point the player stood on, and the story flags are back by now, so a tile that was
    // gated when the save was written is walkable again here. Anywhere else, the named spawn is the honest fallback.
    if (pp_map_walkable(_world.map, _d.x, _d.y)) {
        _world.hero = pp_overworld_hero(_d.x, _d.y);
    }
    _world.music = _d.music;
    pp_overworld_camera_follow(_world);
    global.pp.world = _world;

    _s.state = PPSaveState.idle;
    _s.data = undefined;
    _s.note = "";
    _s.error = "";
    pp_app_request(PPMode.overworld, { resumed: true });
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// The panel on screen (spec 11: the panel shows for at least 20 steps, and the game does not freeze)

function pp_save_panel_step() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return false;
    if (_s.panel < 100000) _s.panel += 1;
    return true;
}

function pp_save_panel_text() {
    var _s = global.pp.save;
    if (is_undefined(_s)) return "";
    // A save the player did not ask for shows nothing (spec 11 rule 4, the card's "silent"). A failure is the one
    // exception: a save that did not happen and says nothing is the silence that costs the player.
    if (_s.silent && _s.state != PPSaveState.failed) return "";
    if (_s.state == PPSaveState.reading || _s.state == PPSaveState.retrying) return "Loading";
    if (_s.state == PPSaveState.backing || _s.state == PPSaveState.backing_write || _s.state == PPSaveState.writing) {
        return "Saving";
    }
    // The transfer can finish inside one frame; the panel still holds for the shortest readable time (spec 11 numbers).
    if (_s.state == PPSaveState.saved && _s.panel < PP_SAVE_PANEL_STEPS) return "Saving";
    if (_s.state == PPSaveState.failed && _s.panel < PP_SAVE_ERROR_STEPS) return _s.error;
    if (_s.state == PPSaveState.saved && _s.error != "" && _s.panel < PP_SAVE_ERROR_STEPS) return _s.error;
    return "";
}

function pp_save_draw_panel() {
    // The title has its own plain lines, so the panel belongs to the modes under it, never over the boot card.
    if (pp_app_mode() == PPMode.boot) return false;
    var _text = pp_save_panel_text();
    if (_text == "") return false;
    draw_set_colour(pp_role_colour("paper"));
    draw_rectangle(48, 92, PP_FRAME_W - 49, 148, false);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(48, 92, PP_FRAME_W - 49, 148, true);
    // Card BATTLE-FONT-WIRE: the panel's sentence is the sheet's glyphs, centred and wrapped to the panel's inside.
    // x 48 to x 207 leaves 159 px, so the old draw_text_ext width of PP_FRAME_W - 112 (144 px) is 18 characters, and
    // three rows at the 10 px pitch still end above the panel's bottom edge at y 148.
    pp_font_draw_wrapped_centre(_text, PP_FRAME_W * 0.5, 101, pp_font_cols(PP_FRAME_W - 112), 10, 1);
    return true;
}
