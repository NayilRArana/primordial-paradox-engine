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
    if (!is_string(_hex) || string_length(_hex) < 7) return c_white;
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
        slice: pp_data_json("slice.json")
    };

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

    // The palette resolves to colours once, at load, so drawing never parses a string.
    _bundle.palette_rgb = [];
    if (is_struct(_bundle.palette) && is_array(_bundle.palette.colours)) {
        for (var i = 0; i < array_length(_bundle.palette.colours); i++) {
            array_push(_bundle.palette_rgb, pp_data_colour(_bundle.palette.colours[i]));
        }
    }
    return _bundle;
}

/// One palette colour by index, with a visible fallback so a bad index draws magenta rather than crashing.
function pp_colour(_index) {
    var _p = global.pp_data.palette_rgb;
    if (_index < 0 || _index >= array_length(_p)) return c_fuchsia;
    return _p[_index];
}

/// Palette indices are data, so drawing code asks for a ROLE ("ink", "paper", "hazard") and the palette file decides
/// which index that is. A missing role falls back to index 0 and is a checker error before it ships.
function pp_role_index(_name) {
    if (is_struct(global.pp_data.palette) && variable_struct_exists(global.pp_data.palette, "roles")) {
        var _roles = global.pp_data.palette.roles;
        if (variable_struct_exists(_roles, _name)) return _roles[$ _name];
    }
    return 0;
}

function pp_role_colour(_name) {
    return pp_colour(pp_role_index(_name));
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
