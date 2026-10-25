/// pp_map_tile: the character to tile index tables for every environment sheet, and the plane each tile lives on
/// (spec 04, spec 15, card R28).
/// The map data names its tiles with one character per cell, so no sheet file name and no tile number ever appears in
/// data\maps\all.json. This module is the one place a character becomes an index, and it holds one table per set:
/// "ship" for the small warship (spec 15), "quay" for the Town Quay block and the dock office (card R46), with
/// "office" as the interior profile of the same sheet, because the office floor is its own tile, and "drive" for the
/// M3 corridor (card t_af836a62).
/// A table also says which of the three planes a tile is drawn on. The map carries one plane of text, the draw needs
/// three: ground and props go under the hero, above goes over him, so a lamp post or a sign can stand in front of the
/// walker without a second layer in the data.
/// A table also names the background palette group each tile spends, and the roles in it, because spec 13 caps a
/// screen at 16 colours and a tile may only spend a colour the map row's own room palette set declares.
/// Provenance: the exterior numbers and roles are read off game\sprites_src\env\quay\quay_tiles.json, which is card
/// R46's manifest and the authority on that sheet. The ship numbers are the ones the ship sheet's own tile names give
/// in game\sprites_src\env\ts_ship_tiled.json: bulkhead 8, deck_plain 2, hatch_open 13, crate 21, pipes 18,
/// deck_grate 3. Where this file and those two manifests disagree, the manifests win and this file is the bug.
/// The drive numbers are the index each tile carries in assets\tiles\drive\drive_tiles.json (index 0 road_surface to
/// index 23 barrier_end, character a to x), and its four groups print as palette.json roles in that same manifest.

#macro PP_TILE_PLANE_GROUND 0
#macro PP_TILE_PLANE_PROPS 1
#macro PP_TILE_PLANE_ABOVE 2

#macro PP_TILE_SET_SHIP "ship"
#macro PP_TILE_SET_QUAY "quay"
#macro PP_TILE_SET_OFFICE "office"
#macro PP_TILE_SET_DRIVE "drive"

#macro PP_TILE_SHEET_SHIP "ts_ship"
#macro PP_TILE_SHEET_QUAY "quay_tiles"
#macro PP_TILE_SHEET_DRIVE "drive_tiles"

/// The ship sheet is 16 cells across, the exterior sheet is 8 (quay_tiles.json names columns 8), and the drive sheet
/// is 8 too (assets\tiles\drive\drive_tiles.json names columns 8, 24 tiles, characters a to x).
#macro PP_TILE_COLUMNS_SHIP 16
#macro PP_TILE_COLUMNS_QUAY 8
#macro PP_TILE_COLUMNS_DRIVE 8

/// Card R46 holds each water frame for 24 game frames: the slow swell the night quay wants, not a flicker.
#macro PP_TILE_WATER_HOLD 24

/// The four background palette groups of the exterior sheet, by role, in sheet order (quay_tiles.json palettes).
/// The drive sheet's four groups are answered here too, in palette.json names, because this is the one place a group
/// name becomes a role list and a second function would be a second answer to the same question.
function pp_map_tile_group_roles(_group) {
    switch (_group) {
        case "bg0_quay_stone":   return ["grey_4", "grey_5", "sea_1"];
        case "bg1_harbour_water": return ["sea_1", "sea_2", "sea_4"];
        case "bg2_brick_iron":   return ["blood_3", "stone_2", "blood_4"];
        case "bg3_lamp_glass":   return ["gold_4", "gold_5", "stone_2"];
        // drive_tiles.json palettes: asphalt (grey_1, grey_3, grey_5), verge (moss_1, moss_2, moss_5),
        // sign (moss_3, moss_2, grey_5), lamp (gold_5, stone_2, moss_2). All nine names are drive_night's own roles.
        case "bg0_asphalt":      return ["grey_1", "grey_3", "grey_5"];
        case "bg1_verge":        return ["moss_1", "moss_2", "moss_5"];
        case "bg2_sign":         return ["moss_3", "moss_2", "grey_5"];
        case "bg3_lamp":         return ["gold_5", "stone_2", "moss_2"];
    }
    return [];
}

/// The exterior rows, in sheet order, exactly as quay_tiles.json lists them. Plane is this module's decision: the
/// backdrops (paving, water, brick, window, office boards) are ground, the things that stand up out of the ground
/// (bollard, chain, barrier, both doors, the desk) are props under the hero, and the two things a walker passes
/// behind (the lamp post and the harbour sign) are above him.
function pp_map_tile_rows_quay() {
    return [
        { ch: ".", gid: 0,  plane: PP_TILE_PLANE_GROUND, group: "bg0_quay_stone" },
        { ch: ",", gid: 1,  plane: PP_TILE_PLANE_GROUND, group: "bg0_quay_stone" },
        { ch: "~", gid: 2,  plane: PP_TILE_PLANE_GROUND, group: "bg0_quay_stone" },
        { ch: "q", gid: 3,  plane: PP_TILE_PLANE_GROUND, group: "bg0_quay_stone" },
        { ch: "w", gid: 4,  plane: PP_TILE_PLANE_GROUND, group: "bg1_harbour_water" },
        { ch: "W", gid: 5,  plane: PP_TILE_PLANE_GROUND, group: "bg1_harbour_water" },
        { ch: "R", gid: 6,  plane: PP_TILE_PLANE_GROUND, group: "bg1_harbour_water" },
        { ch: "B", gid: 7,  plane: PP_TILE_PLANE_PROPS,  group: "bg0_quay_stone" },
        { ch: "c", gid: 8,  plane: PP_TILE_PLANE_PROPS,  group: "bg0_quay_stone" },
        { ch: "b", gid: 9,  plane: PP_TILE_PLANE_PROPS,  group: "bg0_quay_stone" },
        { ch: "#", gid: 10, plane: PP_TILE_PLANE_GROUND, group: "bg2_brick_iron" },
        { ch: "=", gid: 11, plane: PP_TILE_PLANE_GROUND, group: "bg2_brick_iron" },
        { ch: "D", gid: 12, plane: PP_TILE_PLANE_PROPS,  group: "bg2_brick_iron" },
        { ch: "d", gid: 13, plane: PP_TILE_PLANE_PROPS,  group: "bg2_brick_iron" },
        { ch: "o", gid: 14, plane: PP_TILE_PLANE_GROUND, group: "bg3_lamp_glass" },
        { ch: "O", gid: 15, plane: PP_TILE_PLANE_GROUND, group: "bg2_brick_iron" },
        { ch: "L", gid: 16, plane: PP_TILE_PLANE_ABOVE,  group: "bg3_lamp_glass" },
        { ch: "S", gid: 17, plane: PP_TILE_PLANE_ABOVE,  group: "bg3_lamp_glass" },
        { ch: "f", gid: 18, plane: PP_TILE_PLANE_GROUND, group: "bg2_brick_iron" },
        { ch: "k", gid: 19, plane: PP_TILE_PLANE_PROPS,  group: "bg2_brick_iron" }
    ];
}

/// The ship rows, from ts_ship_tiled.json's tile names. The ship has no props or above tiles yet: spec 15 draws every
/// fitting flat on the deck, so all six characters are ground.
function pp_map_tile_rows_ship() {
    return [
        { ch: "#", gid: 8,  plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: ".", gid: 2,  plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: "D", gid: 13, plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: "H", gid: 13, plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: "C", gid: 21, plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: "P", gid: 18, plane: PP_TILE_PLANE_GROUND, group: "" },
        { ch: "G", gid: 3,  plane: PP_TILE_PLANE_GROUND, group: "" }
    ];
}

/// The drive rows, in sheet order, exactly as assets\tiles\drive\drive_tiles.json lists them: index i is character
/// chr(97 + i), so "a" is road_surface at 0 and "x" is barrier_end at 23. Plane is this module's decision, and it is
/// the corridor's: everything the car or the camera travels on or over (road, lines, shoulder, verge, hedge, kerb) is
/// ground, everything that stands up out of the ground (posts, gantry, its sign, the barrier) is props, and nothing is
/// above, because no fitting on this corridor is drawn over a walker. The brief for the drive row is that the road is
/// two tiles wide with the shoulder outside it and the lane line between the lanes.
function pp_map_tile_rows_drive() {
    return [
        { ch: "a", gid: 0,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "b", gid: 1,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "c", gid: 2,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "d", gid: 3,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "e", gid: 4,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "f", gid: 5,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "g", gid: 6,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "h", gid: 7,  plane: PP_TILE_PLANE_GROUND, group: "bg0_asphalt" },
        { ch: "i", gid: 8,  plane: PP_TILE_PLANE_GROUND, group: "bg1_verge" },
        { ch: "j", gid: 9,  plane: PP_TILE_PLANE_GROUND, group: "bg1_verge" },
        { ch: "k", gid: 10, plane: PP_TILE_PLANE_GROUND, group: "bg1_verge" },
        { ch: "l", gid: 11, plane: PP_TILE_PLANE_GROUND, group: "bg1_verge" },
        { ch: "m", gid: 12, plane: PP_TILE_PLANE_GROUND, group: "bg3_lamp" },
        { ch: "n", gid: 13, plane: PP_TILE_PLANE_PROPS,  group: "bg3_lamp" },
        { ch: "o", gid: 14, plane: PP_TILE_PLANE_PROPS,  group: "bg3_lamp" },
        { ch: "p", gid: 15, plane: PP_TILE_PLANE_PROPS,  group: "bg3_lamp" },
        { ch: "q", gid: 16, plane: PP_TILE_PLANE_PROPS,  group: "bg0_asphalt" },
        { ch: "r", gid: 17, plane: PP_TILE_PLANE_PROPS,  group: "bg0_asphalt" },
        { ch: "s", gid: 18, plane: PP_TILE_PLANE_PROPS,  group: "bg2_sign" },
        { ch: "t", gid: 19, plane: PP_TILE_PLANE_PROPS,  group: "bg2_sign" },
        { ch: "u", gid: 20, plane: PP_TILE_PLANE_PROPS,  group: "bg2_sign" },
        { ch: "v", gid: 21, plane: PP_TILE_PLANE_PROPS,  group: "bg0_asphalt" },
        { ch: "w", gid: 22, plane: PP_TILE_PLANE_PROPS,  group: "bg0_asphalt" },
        { ch: "x", gid: 23, plane: PP_TILE_PLANE_PROPS,  group: "bg0_asphalt" }
    ];
}

/// Build one set's lookup: character to {gid, plane, group, roles}. The office profile is the quay sheet read as an
/// interior: the same bricks, the same door, and "." is the office's own boards rather than the quay's paving.
function pp_map_tile_build(_set) {
    var _rows = (_set == PP_TILE_SET_SHIP) ? pp_map_tile_rows_ship() : pp_map_tile_rows_quay();
    // Card t_af836a62: a fourth set answers with its own rows. Without this branch an unknown set still builds the
    // quay's table, which is how the drive room drew the ship's deck: wrong art AND the quay's planes and roles.
    if (_set == PP_TILE_SET_DRIVE) _rows = pp_map_tile_rows_drive();
    var _table = {};
    var _i = 0;
    while (_i < array_length(_rows)) {
        var _row = _rows[_i];
        _table[$ _row.ch] = {
            gid: _row.gid,
            plane: _row.plane,
            group: _row.group,
            roles: pp_map_tile_group_roles(_row.group),
            name: ""
        };
        _i += 1;
    }
    if (_set == PP_TILE_SET_OFFICE) {
        // Office floor: the interior's own boards, so the office does not draw as an outdoor quay.
        _table[$ "."] = { gid: 18, plane: PP_TILE_PLANE_GROUND, group: "bg2_brick_iron",
                          roles: pp_map_tile_group_roles("bg2_brick_iron"), name: "office_floor" };
        // The office set holds ten roles and is quay_night without the brightest teal, so the harbour's water tiles
        // cannot be coloured in it (quay_tiles.json, sets office_night). An office map that asks for water therefore
        // draws the office floor rather than a colour the room does not hold, and the checker counts that cell as a
        // character the set does not name.
        variable_struct_remove(_table, "w");
        variable_struct_remove(_table, "W");
        variable_struct_remove(_table, "R");
    }
    return _table;
}

/// The lookup for a set, built once and kept. A draw of a 16 by 15 tile window asks 240 times a frame, so a table
/// rebuilt per tile would be 240 struct builds a frame for no gain.
function pp_map_tile_table(_set) {
    if (!variable_global_exists("pp_map_tile_tables")) global.pp_map_tile_tables = {};
    var _name = string(_set);
    if (variable_struct_exists(global.pp_map_tile_tables, _name)) return global.pp_map_tile_tables[$ _name];
    var _table = pp_map_tile_build(_name);
    global.pp_map_tile_tables[$ _name] = _table;
    return _table;
}

/// One character's row in one set, or undefined when the set does not name that character.
function pp_map_tile_row(_set, _ch) {
    var _table = pp_map_tile_table(_set);
    if (variable_struct_exists(_table, _ch)) return _table[$ _ch];
    return undefined;
}

/// The ship set's index for a character, kept for the callers that predate the exterior sheet: pp_map_tile_gid() in
/// pp_map is the one name, and it asks this function.
function pp_map_tile_gid_in(_set, _ch) {
    var _row = pp_map_tile_row(_set, _ch);
    if (is_undefined(_row)) return pp_map_tile_default_gid(_set);
    return _row.gid;
}

/// The plane a character draws on. An unnamed character is ground, because that is where a hole would show.
function pp_map_tile_plane(_set, _ch) {
    var _row = pp_map_tile_row(_set, _ch);
    if (is_undefined(_row)) return PP_TILE_PLANE_GROUND;
    return _row.plane;
}

/// The palette roles a character spends in a set, for the 16 colour audit.
function pp_map_tile_roles(_set, _ch) {
    var _row = pp_map_tile_row(_set, _ch);
    if (is_undefined(_row)) return [];
    return _row.roles;
}

/// The index an unnamed character draws as: the plain floor of the set.
function pp_map_tile_default_gid(_set) {
    switch (_set) {
        case PP_TILE_SET_SHIP:   return 2;
        case PP_TILE_SET_OFFICE: return 18;
        case PP_TILE_SET_DRIVE: return 0;
    }
    return 0;
}

/// The sheet a set draws its art from. The build is asked first: a set whose sheet has not been mirrored draws flat,
/// which is the rule pp_map_draw already followed for the ship.
function pp_map_tile_sheet(_set) {
    switch (_set) {
        case PP_TILE_SET_SHIP:   return PP_TILE_SHEET_SHIP;
        case PP_TILE_SET_DRIVE:   return PP_TILE_SHEET_DRIVE;
    }
    return PP_TILE_SHEET_QUAY;
}

/// The cells across the sheet a set draws from.
function pp_map_tile_columns(_set) {
    if (_set == PP_TILE_SET_SHIP) return PP_TILE_COLUMNS_SHIP;
    if (_set == PP_TILE_SET_DRIVE) return PP_TILE_COLUMNS_DRIVE;
    return PP_TILE_COLUMNS_QUAY;
}

/// The set a room draws with, from the room palette id the map row names. The two exterior sets are quay_night and
/// office_night (quay_tiles.json declares both); every other room keeps the ship's set, which is the set that was
/// there before this card. Card ARRIVAL-MAP-2 appends the two sets to data\room_palettes.json; this function only
/// reads the id, so a room naming a set the data does not carry yet still resolves its tiles.
function pp_map_tile_set_for_room(_room_palette) {
    var _id = string(_room_palette);
    if (_id == "office_night") return PP_TILE_SET_OFFICE;
    if (_id == "quay_night") return PP_TILE_SET_QUAY;
    if (_id == "drive_night") return PP_TILE_SET_DRIVE;
    return PP_TILE_SET_SHIP;
}

/// The water animation: the harbour is the only thing on the quay that moves, two frames held PP_TILE_WATER_HOLD each
/// (quay_tiles.json animation "water"). The branch names the quay set, not "everything but the ship": the drive sheet
/// spends "w" on barrier_post, so a set-agnostic branch would draw water in the middle of the barrier run (card
/// t_af836a62). Every other character, and every character of a set with no animation, draws the index its own row
/// names.
function pp_map_tile_gid_at(_set, _ch, _steps) {
    if (_set == PP_TILE_SET_QUAY && (_ch == "w" || _ch == "W")) {
        return (floor(_steps / PP_TILE_WATER_HOLD) mod 2 == 0) ? 4 : 5;
    }
    return pp_map_tile_gid_in(_set, _ch);
}

/// The roles one map's tiles spend that the room set it named does not declare. An empty list is the 16 colour rule
/// holding; a role here would draw as PP_COLOUR_MISSING in the flat fallback, so the caller logs it rather than
/// spending a colour the room does not hold.
function pp_map_tile_role_gaps(_map, _set) {
    var _gaps = [];
    var _seen = {};
    var _y = 0;
    while (_y < _map.h) {
        var _x = 0;
        while (_x < _map.w) {
            var _ch = pp_map_tile_char(_map, _x, _y);
            var _roles = pp_map_tile_roles(_set, _ch);
            var _i = 0;
            while (_i < array_length(_roles)) {
                var _role = _roles[_i];
                if (!variable_struct_exists(_seen, _role)) {
                    _seen[$ _role] = true;
                    if (pp_look_role_index(_role) < 0) array_push(_gaps, _role);
                }
                _i += 1;
            }
            _x += 1;
        }
        _y += 1;
    }
    return _gaps;
}
