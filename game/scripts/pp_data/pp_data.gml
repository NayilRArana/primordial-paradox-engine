/// pp_data: loads every JSON file in data\ and hands out lookups by id (PLAN section 3, spec delta M1).
/// Runtime files are the copies made by tools\sync_data.py into game\datafiles\, which are added to the project as
/// Included Files. Nothing in here contains content: if a number or a name is in this file, it is in the wrong file.

/// Candidate locations for one data file. Included Files land under the working directory; the second and third
/// paths are the two layouts GameMaker uses on Windows, checked in order so a wrong guess fails loudly once.
function pp_data_paths(_name) {
    return [
        working_directory + "datafiles/" + _name,
        working_directory + _name,
        "data/" + _name
    ];
}

/// Read a whole text file, or return undefined with the error saved on global.pp_data_errors.
function pp_data_read(_name) {
    var _paths = pp_data_paths(_name);
    for (var i = 0; i < array_length(_paths); i++) {
        var _p = _paths[i];
        if (file_exists(_p)) {
            var _f = file_text_open_read(_p);
            if (_f < 0) continue;
            var _out = "";
            while (!file_text_eof(_f)) {
                _out += file_text_readln(_f);
                if (!file_text_eof(_f)) _out += "\n";
            }
            file_text_close(_f);
            return _out;
        }
    }
    array_push(global.pp_data_errors, "missing data file: " + _name);
    return undefined;
}

/// Parse one JSON file. parse errors are caught so a hand edited file reports its own name.
function pp_data_json(_name) {
    var _text = pp_data_read(_name);
    if (is_undefined(_text)) return undefined;
    try {
        return json_parse(_text);
    } catch (_e) {
        array_push(global.pp_data_errors, "unreadable JSON in " + _name);
        return undefined;
    }
}

/// "#RRGGBB" to a GameMaker colour. Palette entries are strings in data\palette.json (spec 13).
function pp_data_colour(_hex) {
    if (!is_string(_hex) || string_length(_hex) < 7) return PP_COLOUR_MISSING;
    var _r = pp_hex_to_int(string_copy(_hex, 2, 2));
    var _g = pp_hex_to_int(string_copy(_hex, 4, 2));
    var _b = pp_hex_to_int(string_copy(_hex, 6, 2));
    return make_colour_rgb(_r, _g, _b);
}

/// Local hex parser, so this module does not depend on a helper that may not exist in every runtime version.
function pp_hex_to_int(_two) {
    var _digits = "0123456789abcdef";
    var _out = 0;
    for (var i = 1; i <= 2; i++) {
        var _c = string_lower(string_char_at(_two, i));
        var _v = string_pos(_c, _digits) - 1;
        if (_v < 0) _v = 0;
        _out = _out * 16 + _v;
    }
    return _out;
}

/// Find one entry by id in an array of structs, or undefined.
function pp_data_find(_list, _id) {
    if (!is_array(_list)) return undefined;
    for (var i = 0; i < array_length(_list); i++) {
        var _row = _list[i];
        if (is_struct(_row) && variable_struct_exists(_row, "id") && _row.id == _id) return _row;
    }
    return undefined;
}

/// Build {id: entry} for a list, which is what menus and the checker both want.
function pp_data_index(_list) {
    var _map = {};
    if (!is_array(_list)) return _map;
    for (var i = 0; i < array_length(_list); i++) {
        var _row = _list[i];
        if (is_struct(_row) && variable_struct_exists(_row, "id")) {
            _map[$ _row.id] = _row;
        }
    }
    return _map;
}

/// Load the whole bundle. Missing files collect in global.pp_data_errors instead of crashing the loader, because the
/// boot mode draws those errors in plain words (spec delta M2).
function pp_data_load() {
    global.pp_data_errors = [];
    var _bundle = {
        project: pp_data_json("project.json"),
        palette: pp_data_json("palette.json"),
        room_palettes: pp_data_json("room_palettes.json"),
        party: pp_data_json("characters/party.json"),
        enemies: pp_data_json("enemies/all.json"),
        encounters: pp_data_json("encounters/all.json"),
        patterns: pp_data_json("patterns/all.json"),
        maps: pp_data_json("maps/all.json"),
        scenes: pp_data_json("scenes/all.json"),
        dialogue: pp_data_json("dialogue/all.json"),
        items: pp_data_json("items.json"),
        powers: pp_data_json("powers.json"),
        flags: pp_data_json("flags.json"),
        audio: pp_data_json("audio.json"),
        slice: pp_data_json("slice.json"),
        // data\ui_layouts.json is the design file the battle screen's slots come from (card t_4275136f). It has
        // shipped in the bundle since ASSEMBLE, unused by any script; the director reads it now instead of restating
        // four slot rects and four hero names in code.
        ui_layouts: pp_data_json("ui_layouts.json")
    };

    // The ship room's own map file (card ASSEMBLE). data\maps\ship_sample.json holds just the map rm_pp_ship plays;
    // it is appended to the registry list here so pp_map_load finds it by id like any other map. A build without the
    // file simply has no ship_sample map, and the boot card says so in plain words instead of crashing.
    var _ship_maps = pp_data_json("maps/ship_sample.json");
    if (is_struct(_ship_maps) && is_array(_ship_maps.maps)) {
        for (var _m = 0; _m < array_length(_ship_maps.maps); _m += 1) {
            array_push(_bundle.maps.maps, _ship_maps.maps[_m]);
        }
    }

    // Index the id lists once so nothing scans an array every step.
    _bundle.enemy_by_id = pp_data_index(is_struct(_bundle.enemies) ? _bundle.enemies.enemies : []);
    _bundle.encounter_by_id = pp_data_index(is_struct(_bundle.encounters) ? _bundle.encounters.encounters : []);
    _bundle.pattern_by_id = pp_data_index(is_struct(_bundle.patterns) ? _bundle.patterns.patterns : []);
    _bundle.dialogue_by_id = pp_data_index(is_struct(_bundle.dialogue) ? _bundle.dialogue.dialogue : []);
    _bundle.item_by_id = pp_data_index(is_struct(_bundle.items) ? _bundle.items.items : []);
    _bundle.power_by_id = pp_data_index(is_struct(_bundle.powers) ? _bundle.powers.powers : []);
    _bundle.scene_by_id = pp_data_index(is_struct(_bundle.scenes) ? _bundle.scenes.scenes : []);
    _bundle.map_by_id = pp_data_index(is_struct(_bundle.maps) ? _bundle.maps.maps : []);
    _bundle.audio_by_id = pp_data_index(is_struct(_bundle.audio) ? _bundle.audio.sounds : []);
    // A cue id is a music name too. A scene command writes the cue id into world.music and the save stores it, so the
    // save check has to accept PP-05 as readily as the old sound id. Each cue is added as its own row carrying kind
    // music, so no cue struct from audio.json is rewritten and the registry the bus holds keeps the data file's shape.
    if (is_struct(_bundle.audio) && is_array(_bundle.audio.cues)) {
        for (var _c = 0; _c < array_length(_bundle.audio.cues); _c += 1) {
            var _cue = _bundle.audio.cues[_c];
            if (!is_struct(_cue) || !variable_struct_exists(_cue, "id")) continue;
            _bundle.audio_by_id[$ _cue.id] = { id: _cue.id, kind: "music", cue: true };
        }
    }

    // The palette resolves to colours once, at load, so drawing never parses a string.
    _bundle.palette_rgb = [];
    if (is_struct(_bundle.palette) && is_array(_bundle.palette.colours)) {
        for (var i = 0; i < array_length(_bundle.palette.colours); i++) {
            array_push(_bundle.palette_rgb, pp_data_colour(_bundle.palette.colours[i]));
        }
    }
    return _bundle;
}

/// One palette colour by index, with a visible fallback so a bad index draws the missing colour rather than crashing.
function pp_colour(_index) {
    var _p = global.pp_data.palette_rgb;
    if (_index < 0 || _index >= array_length(_p)) return PP_COLOUR_MISSING;
    return _p[_index];
}

/// True when every file the runtime needs parsed. The boot mode refuses to continue otherwise.
function pp_data_ok() {
    return is_array(global.pp_data_errors) && array_length(global.pp_data_errors) == 0;
}

/// One plain sentence for the screen, for the boot failure path.
function pp_data_error_text() {
    if (pp_data_ok()) return "";
    var _out = "Data problem: " + global.pp_data_errors[0];
    if (array_length(global.pp_data_errors) > 1) {
        _out += " (+" + string(array_length(global.pp_data_errors) - 1) + " more)";
    }
    return _out;
}
