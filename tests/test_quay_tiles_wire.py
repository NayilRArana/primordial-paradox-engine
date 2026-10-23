"""The exterior tile wiring: the quay, the dock office and the roadside draw real tiles, not legend colours (card R28).

Why a test and not a look at a screen: the table that turns a map character into a tile index is the only thing standing
between the exterior and flat rectangles, and every way it can go wrong is silent. A character may point at a tile that
does not exist in the sheet, so a 16x16 patch of the atlas wraps into the wrong art. A room may draw the ship's table
while the room palette it named is the quay's, so the quay's paving draws as a steel deck. The above plane may be drawn
before the hero, so a lamp post disappears under his hat and nobody can tell whether the order was ever right. And the
sheet may sit in game/sprites_src/env/quay/ without ever reaching the build, so the game falls back to flat colour while
the art lane believes its set shipped.

So the rules are pinned to the two authorities: card R46's own manifest, game/sprites_src/env/quay/quay_tiles.json, for
the characters, the indices and the palette roles, and the GML source for the draw order.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

TABLE_GML = os.path.join(ROOT, "game", "scripts", "pp_map_tile", "pp_map_tile.gml")
MAP_GML = os.path.join(ROOT, "game", "scripts", "pp_map", "pp_map.gml")
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
QUAY_JSON = os.path.join(ROOT, "game", "sprites_src", "env", "quay", "quay_tiles.json")
ART_MANIFEST = os.path.join(ROOT, "game", "datafiles", "art", "title_manifest.json")

PLANES = {"PP_TILE_PLANE_GROUND": 0, "PP_TILE_PLANE_PROPS": 1, "PP_TILE_PLANE_ABOVE": 2}
ROW = re.compile(r'\{\s*ch:\s*"(?P<ch>[^"]*)"\s*,\s*gid:\s*(?P<gid>\d+)\s*,\s*plane:\s*(?P<plane>PP_TILE_PLANE_\w+)\s*,'
                 r'\s*group:\s*"(?P<group>[^"]*)"')


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def code(path: str) -> str:
    """The source with its comments stripped, so a rule is judged on code and a comment about it is not the rule."""
    return "\n".join(line.split("//")[0] for line in read(path).splitlines())


def body(path: str, name: str) -> str:
    source = code(path)
    start = source.find("function %s(" % name)
    assert start >= 0, "%s does not define %s()" % (os.path.basename(path), name)
    return source[start:source.find("\n}", start)]


def manifest() -> dict:
    return json.loads(read(QUAY_JSON))


def rows(function: str) -> dict:
    return {match.group("ch"): (int(match.group("gid")), PLANES[match.group("plane")], match.group("group"))
            for match in ROW.finditer(body(TABLE_GML, function))}


def quay_table() -> dict:
    return rows("pp_map_tile_rows_quay")


def ship_table() -> dict:
    return rows("pp_map_tile_rows_ship")


def office_table() -> dict:
    table = dict(quay_table())
    build = body(TABLE_GML, "pp_map_tile_build")
    override = re.search(r'_table\[\$ "\."\] = \{ gid: (\d+)', build)
    assert override, "pp_map_tile_build no longer overrides the office floor, so the office draws the quay's paving"
    table["."] = (int(override.group(1)), PLANES["PP_TILE_PLANE_GROUND"], "bg2_brick_iron")
    # The office set does not hold the brightest teal, so the harbour's three water characters are removed from the
    # office profile rather than drawn in a colour the room cannot colour.
    for ch in re.findall(r'variable_struct_remove\(_table, "(\w)"\)', build):
        table.pop(ch, None)
    return table


def room_sets() -> dict:
    found = {}
    for palette, name in re.findall(r'if \(_id == "(\w+)"\) return PP_TILE_SET_(\w+);',
                                    body(TABLE_GML, "pp_map_tile_set_for_room")):
        found[palette] = name.lower()
    return found


def group_roles() -> dict:
    source = body(TABLE_GML, "pp_map_tile_group_roles")
    found = {}
    for group, listed in re.findall(r'case "(\w+)":\s*return \[([^\]]*)\];', source):
        found[group] = re.findall(r'"(\w+)"', listed)
    return found


# ---------------------------------------------------------------------------------------------------------------
# 1. The table is the sheet: every character, index, palette group and plane agrees with R46's manifest.

def test_every_tile_in_the_sheet_has_a_character_in_the_table():
    tiles = manifest()["tiles"]
    table = quay_table()
    missing = [tile["name"] for tile in tiles if tile["character"] not in table]
    assert missing == [], "the quay table does not name %s" % ", ".join(missing)


def test_every_index_is_the_one_the_sheet_gives_that_character():
    table = quay_table()
    wrong = []
    for tile in manifest()["tiles"]:
        gid, _plane, group = table[tile["character"]]
        if gid != tile["index"]:
            wrong.append("%r draws gid %d, the sheet says %d" % (tile["character"], gid, tile["index"]))
        if group != tile["palette"]:
            wrong.append("%r draws in %s, the sheet says %s" % (tile["character"], group, tile["palette"]))
    assert wrong == [], "\n".join(wrong)


def test_every_index_is_inside_the_sheet():
    count = manifest()["tilecount"]
    over = ["%r draws gid %d, the sheet holds %d" % (ch, gid, count)
            for ch, (gid, _plane, _group) in quay_table().items() if not 0 <= gid < count]
    assert over == [], "\n".join(over)


def test_the_ship_table_is_unchanged_where_the_ship_sheet_speaks():
    # The numbers the ship sheet's own tile names give (spec 15). A ship character that moves would draw the wrong
    # fitting and nothing would fail on a machine without GameMaker.
    table = ship_table()
    assert table["#"][0] == 8
    assert table["."][0] == 2
    assert table["D"][0] == 13
    assert table["C"][0] == 21
    assert table["P"][0] == 18
    assert table["G"][0] == 3
    assert [plane for _gid, plane, _group in table.values()] == [0] * len(table), \
        "the ship has no props or above tiles, so every ship character draws on the ground plane"


# ---------------------------------------------------------------------------------------------------------------
# 2. The three planes: all of them are populated, and the hero sits between the props and the above set.

def test_all_three_planes_carry_a_tile():
    planes = {plane for _gid, plane, _group in quay_table().values()}
    assert planes == {0, 1, 2}, "the quay table draws planes %s, so one of the three is empty" % sorted(planes)


def test_the_above_plane_is_the_two_things_a_walker_passes_behind():
    above = sorted(ch for ch, (_gid, plane, _group) in quay_table().items() if plane == 2)
    assert above == ["L", "S"], "the above plane holds %s; the lamp post and the sign are the two tall things" % above


def test_the_planes_are_drawn_in_the_order_the_hero_needs():
    draw = body(MAP_GML, "pp_map_draw")
    ground = draw.find("PP_TILE_PLANE_GROUND")
    props = draw.find("PP_TILE_PLANE_PROPS")
    assert ground >= 0 and props > ground, "pp_map_draw draws the ground plane after the props plane, or not at all"
    assert "PP_TILE_PLANE_ABOVE" not in draw, \
        "pp_map_draw draws the above plane itself, so the hero cannot be drawn between the planes"
    assert "PP_TILE_PLANE_ABOVE" in body(MAP_GML, "pp_map_draw_above")


def test_the_overworld_draws_the_above_plane_after_the_hero():
    view = body(OVERWORLD_GML, "pp_overworld_draw")
    order = [view.find("pp_map_draw("), view.find("pp_overworld_draw_hero("), view.find("pp_map_draw_above(")]
    assert min(order) >= 0, "pp_overworld_draw does not call the map, the hero and the above plane in one function"
    assert order == sorted(order), "pp_overworld_draw calls the map, the hero and the above plane out of order"


# ---------------------------------------------------------------------------------------------------------------
# 3. The room palette a map row names chooses the table, which is the only thing that makes the exterior draw outdoors.

def test_the_two_arrival_room_sets_choose_the_exterior_tables():
    sets = room_sets()
    assert sets.get("quay_night") == "quay"
    assert sets.get("office_night") == "office"


def test_a_room_with_no_exterior_set_keeps_the_ships_table():
    assert room_sets().get("deck_day") is None
    source = body(TABLE_GML, "pp_map_tile_set_for_room")
    assert "return PP_TILE_SET_SHIP;" in source, "an unknown room palette no longer falls back to the ship's table"


def test_the_office_floor_is_the_offices_own_boards():
    quay = quay_table()
    office = office_table()
    assert office["."][0] == 18 and quay["."][0] == 0, \
        "the office floor and the quay paving must not be the same tile: %r vs %r" % (office["."][0], quay["."][0])
    assert office["#"] == quay["#"], "the office wall is the same brick frontage, so it must not be a second number"


def test_the_office_profile_does_not_names_the_harbour_water():
    office = office_table()
    assert not {"w", "W", "R"} & set(office), \
        "the office names the harbour's water characters, which office_night cannot colour"


def test_the_character_table_covers_the_characters_the_arrival_rows_use():
    # Card ARRIVAL-MAP-2 owns data/maps/all.json; its rows use three characters, exactly the ones the ship rows use,
    # which is why the table is keyed on characters and not on sets of maps.
    for ch in "#.D":
        assert ch in quay_table() and ch in office_table() and ch in ship_table()


# ---------------------------------------------------------------------------------------------------------------
# 4. The 16 colour rule: a room's tiles only spend roles the room palette set it named declares.

def test_every_tile_spends_at_most_three_roles():
    groups = group_roles()
    for group, roles in groups.items():
        assert len(roles) == 3, "%s carries %d roles, a 16x16 area holds 3 plus the backdrop" % (group, len(roles))
    over = [ch for ch, (_gid, _plane, group) in quay_table().items() if len(groups[group]) > 3]
    assert over == []


def test_the_quay_set_declares_every_role_its_own_tiles_spend():
    groups = group_roles()
    declared = set(manifest()["sets"]["quay_night"]["roles"])
    spent = {role for tile in manifest()["tiles"] if tile["palette"] in groups for role in groups[tile["palette"]]}
    assert spent <= declared, "the quay spends %s, which its own set does not declare" % sorted(spent - declared)


def test_the_office_set_covers_the_tiles_the_office_table_can_draw():
    # office_night is the quay_night set without the brightest sea teal, so water must not be reachable in the office.
    groups = group_roles()
    declared = set(manifest()["sets"]["office_night"]["roles"])
    office = office_table()
    spent = {role for _gid, _plane, group in office.values() for role in groups[group]}
    assert spent <= declared, "the office draws %s, which office_night does not declare" % sorted(spent - declared)


def test_the_two_sets_stay_inside_the_sixteen_colour_cap():
    for name, entry in manifest()["sets"].items():
        assert len(entry["roles"]) <= 16, "%s carries %d roles" % (name, len(entry["roles"]))


# ---------------------------------------------------------------------------------------------------------------
# 5. The sheet reaches the build: a set written into env/quay/ is mirrored and listed, or the game draws flat.

def test_the_sheet_is_in_the_build_index_with_its_own_column_count():
    index = json.loads(read(ART_MANIFEST))
    entry = next((row for row in index["animations"] if row["name"] == manifest()["name"]), None)
    assert entry is not None, "the build index does not carry %s, so the game falls back to flat rectangles" \
                              % manifest()["name"]
    assert entry["kind"] == "tileset"
    assert entry["columns"] == manifest()["columns"], \
        "the index says %d columns, the sheet has %d, so every tile id past the first row would draw the wrong cell" \
        % (entry["columns"], manifest()["columns"])
    assert entry["frames"] == manifest()["tilecount"]


def test_the_art_mirror_reads_the_exterior_subfolder():
    source = read(os.path.join(ROOT, "tools", "sync_art.py"))
    assert 'ENV_QUAY_SRC = os.path.join(ENV_SRC, "quay")' in source
    assert "ENV_QUAY_SRC" in source.split("SOURCES = (")[1].split(")")[0], \
        "tools/sync_art.py defines the quay folder but does not read it"


# ---------------------------------------------------------------------------------------------------------------
# 6. The fallbacks behave: an unnamed character is the set's own floor, never a hole and never art from another set.

def test_an_unnamed_character_draws_the_sets_own_floor():
    floats = body(TABLE_GML, "pp_map_tile_default_gid")
    assert 'case PP_TILE_SET_SHIP:   return 2;' in floats
    assert 'case PP_TILE_SET_OFFICE: return 18;' in floats
    assert floats.rstrip().endswith("return 0;"), "the quay's default floor is quay_paving, index 0"


def test_an_unnamed_character_is_ground_and_not_a_plane_of_its_own():
    source = body(TABLE_GML, "pp_map_tile_plane")
    assert "return PP_TILE_PLANE_GROUND;" in source


def test_the_water_animation_is_two_frames_of_the_same_tile():
    source = body(TABLE_GML, "pp_map_tile_gid_at")
    assert '(_ch == "w" || _ch == "W")' in source
    assert "PP_TILE_WATER_HOLD" in source and "mod 2" in source
    quay = quay_table()
    assert quay["w"][0] == 4 and quay["W"][0] == 5, "the two water frames are water_deep and water_ripple"


def test_the_check_that_would_catch_a_wrong_index_is_not_vacuous():
    # A planted table where a character points at art that belongs to another character must be refused by the same
    # comparison the first test makes, or that test proves nothing.
    tiles = manifest()["tiles"]
    planted = {".": (10, 0, "bg2_brick_iron")}
    art = next(tile for tile in tiles if tile["index"] == planted["."][0])
    assert art["character"] != ".", "the planted index still belongs to the floor, so the check could not bite"
