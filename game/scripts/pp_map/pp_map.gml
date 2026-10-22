/// pp_map: one loaded tile map, its collision grid, its triggers and its rendering (spec 04).
/// Collision is a separate byte grid from the tile art on purpose, so walls change without redrawing tiles.
/// Telling 0 walkable, 1 blocked, 2 story blocked (blocked until the map's story flag is set).
/// Provenance: knowledge\PROVENANCE.md, entry "room and object conventions across a whole game", written before the
/// notice of 2026-10-19 and re-confirmed by the clean-room re-review of the same date. The three data pieces are spec
/// 04: tile art, collision grid and trigger list, validated by the checker before the game runs.

/// Load one map by id. Returns undefined and reports in plain words when the id is missing, so a bad slice names itself.
function pp_map_load(_map_id) {
    var _list = global.pp_data.maps.maps;
    var _row = pp_data_find(_list, _map_id);
    if (is_undefined(_row)) {
        show_debug_message("PP: no map with id " + string(_map_id));
        return undefined;
    }
    var _map = {
        id: _row.id,
        name: _row.name,
        w: _row.width,
        h: _row.height,
        tile: PP_TILE,
        music: (variable_struct_exists(_row, "music") ? _row.music : ""),
        legend: _row.tile_legend,
        tiles: _row.tiles,
        collision: _row.collision,
        triggers: _row.triggers,
        spawns: _row.spawns,
        actors: [],
        story_flag: "",
        palette: _row.palette_indices,
        tileset: ""
    };
    if (variable_struct_exists(_row, "actors")) _map.actors = _row.actors;
    if (variable_struct_exists(_row, "tileset")) _map.tileset = _row.tileset;
    if (variable_struct_exists(_row, "story_flag")) _map.story_flag = _row.story_flag;
    // The room's own palette set (spec 13). A map that names one draws in it; a map without one keeps the set already in
    // use, which is the default set the look module loaded at boot.
    if (variable_struct_exists(_row, "room_palette")) pp_look_palette(_row.room_palette);
    return _map;
}

/// Collision at a tile: 1 when off the map, 2 when story blocked and the flag is still false.
function pp_map_collision(_map, _tx, _ty) {
    if (_tx < 0 || _ty < 0 || _tx >= _map.w || _ty >= _map.h) return 1;
    var _row = _map.collision[_ty];
    var _ch = string_char_at(_row, _tx + 1);
    if (_ch == "2") {
        if (_map.story_flag != "" && pp_ledger_flag(global.pp_ledger, _map.story_flag)) return 0;
        return 1;
    }
    if (_ch == "1") return 1;
    return 0;
}

/// True when a walker may stand on this tile.
function pp_map_walkable(_map, _tx, _ty) {
    return pp_map_collision(_map, _tx, _ty) == 0;
}

/// The tile art character at a tile, or "#" off the map so an edge draws as wall rather than a hole.
function pp_map_tile_char(_map, _tx, _ty) {
    if (_tx < 0 || _ty < 0 || _tx >= _map.w || _ty >= _map.h) return "#";
    return string_char_at(_map.tiles[_ty], _tx + 1);
}

/// The legend word for a tile ("wall", "floor", "door"), which is what chooses its colour.
function pp_map_tile_kind(_map, _tx, _ty) {
    var _ch = pp_map_tile_char(_map, _tx, _ty);
    if (variable_struct_exists(_map.legend, _ch)) return _map.legend[$ _ch];
    return "wall";
}

/// Colour for a legend kind. Three kinds only in the slice; anything unknown draws as wall, which is visible.
function pp_map_kind_colour(_kind) {
    switch (_kind) {
        case "floor": return pp_role_colour("paper");
        case "door":  return pp_role_colour("accent");
        default:      return pp_role_colour("dim");
    }
}

/// The trigger on a tile, or undefined. The first match wins; the checker refuses two triggers on one tile.
function pp_map_trigger_at(_map, _tx, _ty) {
    var _i = 0;
    var _count = array_length(_map.triggers);
    while (_i < _count) {
        var _t = _map.triggers[_i];
        if (_t.x == _tx && _t.y == _ty) return _t;
        _i += 1;
    }
    return undefined;
}

/// A named spawn point as {x, y}. A missing name falls back to "start", then to tile (0,0) with a debug message.
function pp_map_spawn_point(_map, _name) {
    if (variable_struct_exists(_map.spawns, _name)) {
        var _s = _map.spawns[$ _name];
        return { x: _s.x, y: _s.y };
    }
    show_debug_message("PP: map " + string(_map.id) + " has no spawn " + string(_name));
    if (variable_struct_exists(_map.spawns, "start")) {
        var _s2 = _map.spawns.start;
        return { x: _s2.x, y: _s2.y };
    }
    return { x: 0, y: 0 };
}

/// Pixels a camera may scroll over, clamped so the view never leaves the map.
function pp_map_pixel_size(_map) {
    return { w: _map.w * _map.tile, h: _map.h * _map.tile };
}

/// The tile index a map character draws with inside the ship tileset. The numbers are the tile ids in
/// game\sprites_src\env\ts_ship_tiled.json, chosen by tile name there: bulkhead 8, deck_plain 2, hatch_open 13,
/// crate 21, pipes 18, deck_grate 3. A character the ship set does not name draws deck_plain, never a hole.
#macro PP_TILESET_COLUMNS 16
function pp_map_tile_gid(_ch) {
    switch (_ch) {
        case "#": return 8;
        case ".": return 2;
        case "D": return 13;
        case "C": return 21;
        case "P": return 18;
        case "G": return 3;
    }
    return 2;
}

/// Draw the visible tile window. The map's own tileset when the art lane delivered one (card ENV-TILES),
/// flat rectangles when it did not, so the room still reads on a build without the sheet.
function pp_map_draw(_map, _cam_x, _cam_y) {
    var _ts = "";
    if (_map.tileset != "" && pp_art_has(_map.tileset)) _ts = _map.tileset;
    var _info = is_string(_ts) && _ts != "" ? pp_art_info(_ts) : undefined;

    var _x0 = floor(_cam_x / _map.tile);
    var _y0 = floor(_cam_y / _map.tile);
    var _ty = _y0;
    while (_ty <= _y0 + PP_VIEW_H) {
        var _tx = _x0;
        while (_tx <= _x0 + PP_VIEW_W) {
            var _px = _tx * _map.tile - _cam_x;
            var _py = _ty * _map.tile - _cam_y;
            var _ch = pp_map_tile_char(_map, _tx, _ty);
            if (!is_undefined(_info)) {
                var _gid = pp_map_tile_gid(_ch);
                var _cols = PP_TILESET_COLUMNS;
                if (variable_struct_exists(_info, "columns") && _info.columns > 0) _cols = _info.columns;
                var _sx = (_gid mod _cols) * _map.tile;
                var _sy = floor(_gid / _cols) * _map.tile;
                draw_sprite_part_ext(_info.sprite, 0, _sx, _sy, _map.tile, _map.tile,
                                     _px, _py, 1, 1, PP_UNTINTED, 1);
            } else {
                draw_set_colour(pp_map_kind_colour(pp_map_tile_kind(_map, _tx, _ty)));
                draw_rectangle(_px, _py, _px + _map.tile - 1, _py + _map.tile - 1, false);
            }
            _tx += 1;
        }
        _ty += 1;
    }
}
