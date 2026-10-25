"""The drive tile wiring: the M3 corridor draws its own sheet, not the ship's deck (card t_af836a62).

Why a test and not a look at a screen: a map row naming a tileset proves nothing on its own. pp_map_tile_set_for_room
answered every room it did not recognise with the ship's table, so a drive room drew deck_plain in every cell while the
row was legal and the checker was silent. The wire is three facts that have to hold together:

    the table       every character the sheet names draws that tile's own index, on this set's plane, in a palette
                    group whose roles drive_night declares
    the choice      the room palette id drive_night resolves to the drive set, and an unknown id still falls back
    the delivery    assets/tiles/drive/ is read by tools/sync_art.py, so the sheet reaches game/datafiles/art and the
                    project lists it as an Included File

The authority for the first is the sheet's own manifest, assets/tiles/drive/drive_tiles.json. The authority for the
second is data/room_palettes.json and data/palette.json. The authority for the third is tools/sync_art.py and the
build index it writes. No test here reads the network, writes a tracked file, or needs GameMaker: this host cannot
run the project, so the wire is proven by the table and the index, not by a picture.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

TABLE_GML = os.path.join(ROOT, "game", "scripts", "pp_map_tile", "pp_map_tile.gml")
DRIVE_JSON = os.path.join(ROOT, "assets", "tiles", "drive", "drive_tiles.json")
ROOM_PALETTES = os.path.join(ROOT, "data", "room_palettes.json")
MASTER_PALETTE = os.path.join(ROOT, "data", "palette.json")
ART_MANIFEST = os.path.join(ROOT, "game", "datafiles", "art", "title_manifest.json")

SET_ID = "drive_night"
SHEET = "drive_tiles"
SCREEN_CAP = 16

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


def read_json(path: str):
    return json.loads(read(path))


def sheet() -> dict:
    return read_json(DRIVE_JSON)


def drive_rows() -> dict:
    return {match.group("ch"): (int(match.group("gid")), PLANES[match.group("plane")], match.group("group"))
            for match in ROW.finditer(body(TABLE_GML, "pp_map_tile_rows_drive"))}


def release_set() -> list:
    """The roles data/room_palettes.json declares for drive_night."""
    entry = next((row for row in read_json(ROOM_PALETTES)["sets"] if row["id"] == SET_ID), None)
    assert entry is not None, "data/room_palettes.json holds no set %r" % SET_ID
    return entry["roles"]


def master_roles() -> dict:
    return read_json(MASTER_PALETTE)["roles"]


def group_roles() -> dict:
    """The roles pp_map_tile_group_roles answers for each group, in palette.json names."""
    source = body(TABLE_GML, "pp_map_tile_group_roles")
    found = {}
    for group, listed in re.findall(r'case "(\w+)":\s*return \[([^\]]*)\];', source):
        found[group] = re.findall(r'"(\w+)"', listed)
    return found


def sheet_role_names() -> dict:
    """The sheet's own role key (asphalt, dim, ...) to the palette.json role it prints as (grey_1, grey_3, ...)."""
    return {name: entry["role"] for name, entry in sheet()["roles"].items()}


def room_sets() -> dict:
    found = {}
    for palette, name in re.findall(r'if \(_id == "(\w+)"\) return PP_TILE_SET_(\w+);',
                                    body(TABLE_GML, "pp_map_tile_set_for_room")):
        found[palette] = name.lower()
    return found


# ---------------------------------------------------------------------------------------------------------------
# 1. The table is the sheet: all 24 characters, their own indices, their own palette groups.

def test_the_table_names_every_tile_the_sheet_carries():
    missing = [tile["name"] for tile in sheet()["tiles"] if tile["character"] not in drive_rows()]
    assert missing == [], "the drive table does not name %s" % ", ".join(missing)


def test_the_table_names_no_character_the_sheet_does_not_carry():
    named = set(drive_rows())
    carried = {tile["character"] for tile in sheet()["tiles"]}
    assert named - carried == set(), "the drive table names %r, which the sheet has no tile for" % sorted(
        named - carried)


def test_each_character_is_the_sheets_own_column_for_that_index():
    # The sheet is a grid whose characters run a..x in index order (TILES.md, "How to wire it"). A table keyed on
    # its own order rather than the sheet's would still pass the two tests above if two rows were swapped.
    wrong = [(tile["character"], tile["index"]) for tile in sheet()["tiles"]
             if tile["character"] != chr(ord("a") + tile["index"])]
    assert wrong == [], "the sheet's character column is not a..x in index order at %r" % wrong


def test_every_index_and_palette_group_is_the_one_the_sheet_gives_that_character():
    table = drive_rows()
    wrong = []
    for tile in sheet()["tiles"]:
        gid, _plane, group = table[tile["character"]]
        if gid != tile["index"]:
            wrong.append("%r draws gid %d, the sheet says %d" % (tile["character"], gid, tile["index"]))
        if group != tile["palette"]:
            wrong.append("%r draws in %s, the sheet says %s" % (tile["character"], group, tile["palette"]))
    assert wrong == [], "\n".join(wrong)


def test_every_index_is_inside_the_sheet():
    count = sheet()["tilecount"]
    over = ["%r draws gid %d, the sheet holds %d" % (ch, gid, count)
            for ch, (gid, _plane, _group) in drive_rows().items() if not 0 <= gid < count]
    assert over == [], "\n".join(over)


# ---------------------------------------------------------------------------------------------------------------
# 2. The planes: everything walked on or over is ground, everything that stands up is props, nothing is above.

def test_ground_is_everything_the_corridor_is_walked_on_or_over():
    ground = sorted(ch for ch, (_gid, plane, _group) in drive_rows().items() if plane == 0)
    assert ground == sorted("abcdefghijklm"), \
        "the ground plane holds %r; the road, its lines, the shoulder, the verge, the hedge and the kerb are ground" \
        % ground


def test_props_is_everything_that_stands_up_out_of_the_ground():
    props = sorted(ch for ch, (_gid, plane, _group) in drive_rows().items() if plane == 1)
    assert props == sorted("nopqrstuvwx"), \
        "the props plane holds %r; the posts, the gantry, its sign and the barrier are props" % props


def test_the_above_plane_is_empty_on_purpose():
    # The corridor is the film's, and the car and the camera move along it. Nothing fitted to it is drawn over a
    # walker: a lamp post painted above the hero would read as a roof, not as a post. So this set carries no above
    # tile, and the absence is the decision, not an omission.
    above = [ch for ch, (_gid, plane, _group) in drive_rows().items() if plane == 2]
    assert above == [], "the drive set draws %r above the hero; the corridor has no roof fitting" % above


def test_the_hero_is_drawn_between_the_two_planes_that_are_used():
    # The plane values only mean something in the draw order pp_map and pp_overworld implement for the quay.
    from_overworld = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
    draw = body(from_overworld, "pp_overworld_draw")
    order = [draw.find("pp_map_draw("), draw.find("pp_overworld_draw_hero("), draw.find("pp_map_draw_above(")]
    assert min(order) >= 0 and order == sorted(order), \
        "the ground and props planes only sit under the hero when the overworld draws him between them"


# ---------------------------------------------------------------------------------------------------------------
# 3. The 16 colour rule: the roles the table can spend are the roles drive_night declares.

def test_every_group_names_three_roles():
    groups = group_roles()
    for group, roles in groups.items():
        if not group.startswith("bg") or group not in sheet_groups():
            continue
        assert len(roles) == 3, "%s carries %d roles, a 16x16 area holds 3 plus the backdrop" % (group, len(roles))


def sheet_groups() -> set:
    return {group["name"] for group in sheet()["palettes"]}


def test_the_group_roles_are_the_sheets_own_roles_in_palette_json_names():
    # pp_map_tile_group_roles answers in palette.json names because pp_look_role_index is asked in those names. The
    # sheet prints its roles its own way (asphalt, dim, bright); the two must say the same colour.
    names = sheet_role_names()
    groups = {group["name"]: group["roles"] for group in sheet()["palettes"]}
    table = group_roles()
    wrong = []
    for group, sheet_roles in groups.items():
        expected = [names[role] for role in sheet_roles]
        if table.get(group) != expected:
            wrong.append("%s answers %r, the sheet's roles print as %r" % (group, table.get(group), expected))
    assert wrong == [], "\n".join(wrong)


def test_the_drive_set_declares_every_role_the_drive_tiles_spend():
    groups = group_roles()
    spent = {role for tile in sheet()["tiles"] for role in groups[tile["palette"]]}
    declared = set(release_set())
    assert spent <= declared, "the drive tiles spend %s, which drive_night does not declare" % sorted(
        spent - declared)


def test_the_drive_set_stays_inside_the_screen_cap_with_room_for_the_missing_colour():
    roles = master_roles()
    colours = {roles[name] for name in release_set() if name in roles}
    assert len(colours) + 1 <= SCREEN_CAP, \
        "drive_night spends %d distinct colours, and a role outside it adds the missing colour" % len(colours)


# ---------------------------------------------------------------------------------------------------------------
# 4. The sheet reaches the build, or the game draws flat rectangles while the art lane believes it shipped.

def test_the_sheet_is_in_the_build_index_as_a_tileset_of_its_own_shape():
    index = read_json(ART_MANIFEST)
    entry = next((row for row in index["animations"] if row["name"] == SHEET), None)
    assert entry is not None, "the build index does not carry %s, so the drive falls back to flat rectangles" % SHEET
    assert entry["kind"] == "tileset"
    assert entry["columns"] == sheet()["columns"], \
        "the index says %d columns, the sheet has %d, so every tile past the first row would draw the wrong cell" % (
            entry["columns"], sheet()["columns"])
    assert entry["frames"] == sheet()["tilecount"]


def test_the_art_mirror_reads_the_drive_sheet_folder():
    source = read(os.path.join(ROOT, "tools", "sync_art.py"))
    assert 'DRIVE_SRC = os.path.join(ROOT, "assets", "tiles", "drive")' in source, \
        "tools/sync_art.py does not look in assets/tiles/drive, which is where the sheet lives (TILES.md)"
    assert "DRIVE_SRC" in source.split("SOURCES = (")[1].split(")")[0], \
        "tools/sync_art.py defines the drive folder but does not read it"


def test_the_build_input_checker_resolves_the_mirrored_drive_sheet():
    # An Included File whose source candidates do not include the drive folder reads as a source git does not carry,
    # which is a refusal at commit time rather than a missing sheet at runtime.
    checker = read(os.path.join(ROOT, "tools", "check_build_inputs.py"))
    assert 'os.path.join(ROOT, "assets", "tiles", "drive")' in checker, \
        "tools/check_build_inputs.py does not name assets/tiles/drive among the art sources"


# ---------------------------------------------------------------------------------------------------------------
# 5. The choice: drive_night picks the drive table, an unknown room still keeps the ship's, and the set answers the
#    sheet and the column count its own rows are built for.

def test_drive_night_chooses_the_drive_table():
    assert room_sets().get(SET_ID) == "drive"


def test_a_room_with_no_drive_set_keeps_the_ships_table():
    assert room_sets().get("deck_day") is None
    assert "return PP_TILE_SET_SHIP;" in body(TABLE_GML, "pp_map_tile_set_for_room"), \
        "an unknown room palette no longer falls back to the ship's table"


def test_the_drive_set_answers_its_own_sheet_and_column_count():
    assert '#macro PP_TILE_SET_DRIVE "drive"' in code(TABLE_GML)
    assert '#macro PP_TILE_SHEET_DRIVE "%s"' % SHEET in code(TABLE_GML)
    assert '#macro PP_TILE_COLUMNS_DRIVE %d' % sheet()["columns"] in code(TABLE_GML)
    answers = body(TABLE_GML, "pp_map_tile_sheet")
    assert "case PP_TILE_SET_DRIVE:   return PP_TILE_SHEET_DRIVE;" in answers
    columns = body(TABLE_GML, "pp_map_tile_columns")
    assert "if (_set == PP_TILE_SET_DRIVE) return PP_TILE_COLUMNS_DRIVE;" in columns


def test_the_table_builder_dispatches_the_drive_set_to_the_drive_rows():
    build = body(TABLE_GML, "pp_map_tile_build")
    assert "PP_TILE_SET_DRIVE" in build and "pp_map_tile_rows_drive" in build, \
        "pp_map_tile_build answers an unknown set with the quay's rows, so a drive room would draw paving"


# ---------------------------------------------------------------------------------------------------------------
# 6. The fallbacks behave: an unnamed character is the corridor floor, never a hole, and never another set's art.

def test_an_unnamed_character_draws_the_road_surface():
    floats = body(TABLE_GML, "pp_map_tile_default_gid")
    assert "case PP_TILE_SET_DRIVE: return 0;" in floats, \
        "the drive's default tile is road_surface, index 0: an unnamed character must draw the road, never a hole"
    road = next(tile for tile in sheet()["tiles"] if tile["index"] == 0)
    assert road["name"] == "road_surface"


def test_the_water_animation_stays_on_the_quays_set():
    # pp_map_tile_gid_at animates two characters into water frames for every set except the ship. The drive sheet
    # spends "w" on barrier_post, so a set-agnostic branch would draw water in the middle of the barrier run.
    source = body(TABLE_GML, "pp_map_tile_gid_at")
    assert "(_set == PP_TILE_SET_QUAY" in source, \
        "the water animation is asked of every set but the ship, so the drive's barrier post would draw as water"
    assert drive_rows()["w"][0] == next(tile["index"] for tile in sheet()["tiles"]
                                        if tile["name"] == "barrier_post")


def test_an_unnamed_character_is_ground_and_not_a_plane_of_its_own():
    assert "return PP_TILE_PLANE_GROUND;" in body(TABLE_GML, "pp_map_tile_plane")


def test_the_check_that_would_catch_a_wrong_index_is_not_vacuous():
    # A planted table where a character points at art that belongs to another character must be refused by the same
    # comparison the first tests make, or they prove nothing.
    tiles = sheet()["tiles"]
    planted = {"a": (13, 0, "bg0_asphalt")}
    art = next(tile for tile in tiles if tile["index"] == planted["a"][0])
    assert art["character"] != "a", "the planted index still belongs to the road, so the check could not bite"
