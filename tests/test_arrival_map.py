"""The arrival map, proven playable from the data, without running GameMaker (card t_3a52845d, step S4).

Nothing here executes GML. Every assertion reads a real file and computes the answer from it, so a
change in the map row, the scene rows, the schema or the engine's command switch fails here instead
of in a playtest.

Sources this file measures, never restates:

    data/maps/all.json                          the southampton_town_quay row and its door targets
    data/scenes/all.json                        the scenes the block triggers and their commands
    data/schemas/maps.schema.json               the published shape of a map row
    data/schemas/cutscenes.schema.json          the published shape of a scene
    game/scripts/pp_config/pp_config.gml        PP_TILE 16, PP_VIEW_W 16, PP_VIEW_H 15
    game/scripts/pp_map/pp_map.gml              pp_map_collision: 0 walkable, 1 blocked, 2 story blocked
    game/scripts/pp_scene/pp_scene.gml          the switch every scene command goes through
    tools/check_data.py                         SCENE_COMMANDS, the checker's own list of them
    specs/04-overworld-rails-and-triggers.md    the trigger list, markers only, 16 by 15 tiles visible
    specs/06-cutscene-runner.md                 what a scene may say
    knowledge/mechanics/PACING-AND-CUTSCENES.md 6.2   marker placement and the 40 to 60 density sentence
    knowledge/GAMEDEV-DECISIONS-2026-10-22.md D1      the ruling that splits markers by kind

What is proven, in the card's own order. Before any of it, the numbers this file encodes are read out
of spec 04, the study, the D1 ruling and pp_map_collision, so a document change fails here first.

  1. the maps file validates against data/schemas/maps.schema.json, and every grid row is the width
     and height the row declares (the cross-row rule a JSON Schema cannot express);
  2. the entry spawn is on a walkable tile, is not walled in, and every named spawn on the block is
     walkable and inside the map;
  3. every door names a target map and a spawn that exist, sits on a tile drawn as a door, and its
     target spawn is walkable; every tile drawn as a door carries a trigger, and the door back from
     the office is in reach of the spawn it drops the player on. The one map trigger that is not a
     building door is the ship gangway at the pier head (card t_67a36372): it names ship_small and
     the spawn start, it sits on a walkable pier tile rather than door art, and there is exactly one;
  4. the walkable area reaches every door and the gangway, by a flood fill from the entry spawn, run
     twice: once with the story barrier shut and once with it open, the way pp_map_collision reads a
     2 tile;
  5. the flood fill is iterative and bounded: it dequeues each tile once, it is not recursive in the
     source, and a 250 by 250 open grid is walked whole;
  6. no encounter marker is within 6 tiles of the entry tile, a door tile or a control handback tile,
     measured as tile steps (Chebyshev, which is never larger than the 4-direction walk, so the check
     is the strict one);
  7. the marker mix is the one D1 rules for this block: 1 story marker, 0 wild, and no screen window
     of 16 by 15 tiles holds more than 2 markers, which is D1's cap;
  8. the 40 to 60 wild density band is a real band, exercised on synthetic counts and on this block's
     own walkable count, and it has nothing to measure here because the block carries no wild marker;
  9. every command in the gate scene, and in every scene the block triggers through its branch chain,
     is one pp_scene implements, and the engine's switch and tools/check_data.py agree on that list;
 10. a door pointed at a map that does not exist, and a door pointed at a spawn that does not exist,
     are both refused, on a throwaway copy of the data.

Two things this file deliberately does not assert, and why:

  - The card's marker density line ("one per 60 to one per 40 walkable tiles") is the sentence
    PACING-AND-CUTSCENES 6.2 states, and D1 rules that it is about WILD markers only: a story
    marker's authored count wins. D1 also says a card that disagrees is the thing that is wrong, so
    the band is asserted for wild markers and the block's story marker is asserted against D1's own
    table. The band as written asks 1702 walkable tiles for 28 to 43 markers, which is a fight
    every 8 to 12 seconds; D1 names that contradiction and this file follows the ruling. The whole
    count band this file applies, for a count that sits between 40 and 60 tiles a marker, is 29 to 42.
  - The card's spawn line ("every tile around it is walkable") does not hold on the row as shipped:
    the entry spawn at 11,1 has a building wall to its east (12,1) and to its north east (12,0), so
    3 of its 4 orthogonal neighbours are walkable, not 4. Changing the map is outside this card's
    scope and choosing to relax a gamedev line is not this lane's call, so the test asserts the
    playability rule that does hold (not walled in, at least two open sides, every open side
    reachable from the spawn) and the gap is posted as a Q: for gamedev on the card.

No test in this file reads the network, writes a tracked data file, or needs a key.
"""

from __future__ import annotations

import ast
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The maps file can be pointed at a copy, so a broken door can be shown to fail these tests and not
# only a helper.
MAPS_PATH = os.environ.get("PP_ARRIVAL_MAPS") or os.path.join(ROOT, "data", "maps", "all.json")
SCENES_PATH = os.path.join(ROOT, "data", "scenes", "all.json")
MAPS_SCHEMA_PATH = os.path.join(ROOT, "data", "schemas", "maps.schema.json")
SCENES_SCHEMA_PATH = os.path.join(ROOT, "data", "schemas", "cutscenes.schema.json")
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
MAP_GML = os.path.join(ROOT, "game", "scripts", "pp_map", "pp_map.gml")
SCENE_GML = os.path.join(ROOT, "game", "scripts", "pp_scene", "pp_scene.gml")
SPEC_04 = os.path.join(ROOT, "specs", "04-overworld-rails-and-triggers.md")
STUDY = os.path.join(ROOT, "knowledge", "mechanics", "PACING-AND-CUTSCENES.md")
DECISIONS = os.path.join(ROOT, "knowledge", "GAMEDEV-DECISIONS-2026-10-22.md")

ARRIVAL_MAP = "southampton_town_quay"
ENTRY_SPAWN = "start"

# The block the roadmap's S4 names: 53 by 56 tiles at 8 m a tile.
ARRIVAL_SIZE = (53, 56)

# PACING-AND-CUTSCENES 6.2 and D1: none within 6 tiles of an entry, a door or a control handback.
MARKER_CLEAR_TILES = 6
# D1: a wild marker sits 1 per 40 to 60 walkable tiles; at most 2 markers of either kind on a screen.
WILD_TILES_PER_MARKER = (40, 60)
SCREEN_MARKER_CAP = 2
# D1 names 1701 walkable tiles for this block, which is the figure the density band is read against.
# Card t_67a36372 opens the pier junction at (35,47) so the ship gangway at the pier head can be walked
# to, which is one more: 1702 measured on the shipped grid, with the barrier shut.
ARRIVAL_WALKABLE = 1702
# The one map trigger on the block that is not a building door: the gangway onto the ship (t_67a36372).
GANGWAY_MAP = "ship_small"

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# --------------------------------------------------------------------------- reading files


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def maps_doc() -> dict:
    return _load(MAPS_PATH)


@pytest.fixture(scope="module")
def scenes_doc() -> dict:
    return _load(SCENES_PATH)


@pytest.fixture(scope="module")
def arrival(maps_doc: dict) -> dict:
    rows = maps_by_id(maps_doc)
    assert ARRIVAL_MAP in rows, "data/maps/all.json holds no map %r" % ARRIVAL_MAP
    return rows[ARRIVAL_MAP]


@pytest.fixture(scope="module")
def scenes_by_id(scenes_doc: dict) -> dict:
    return {row["id"]: row for row in scenes_doc["scenes"]}


# --------------------------------------------------------------------------- map geometry


def maps_by_id(doc: dict) -> dict:
    return {row["id"]: row for row in doc["maps"]}


def triggers_of(row: dict, kind: str) -> list:
    return [trigger for trigger in row["triggers"] if trigger["kind"] == kind]


def cell_of(row: dict, x: int, y: int) -> str:
    """The collision character at a tile, or "off" outside the map (pp_map_collision returns 1 there)."""
    if x < 0 or y < 0 or y >= len(row["collision"]) or x >= len(row["collision"][y]):
        return "off"
    return row["collision"][y][x]


def story_gate_is_open(row: dict) -> bool:
    """True when a 2 tile can ever be walked: the engine opens it only for a named story flag."""
    has_story_tile = any("2" in line for line in row["collision"])
    return has_story_tile and row.get("story_flag", "") != ""


def is_passable(row: dict, x: int, y: int, gate_open: bool) -> bool:
    """Mirror of pp_map_collision: 0 is walkable, 2 is walkable only while the story flag is set."""
    char = cell_of(row, x, y)
    if char == "0":
        return True
    if char == "2":
        return gate_open
    return False


def walkable_count(row: dict, gate_open: bool = False) -> int:
    return sum(1 for y in range(row["height"]) for x in range(row["width"])
               if is_passable(row, x, y, gate_open))


def flood_fill(row: dict, start: tuple, gate_open: bool) -> tuple:
    """Every tile reachable from start, four directions, and how many rows the queue served.

    Iterative on purpose: a 250 by 250 map is 62500 tiles and a recursive fill would be a stack
    overflow waiting for the first big map. Each tile is enqueued at most once, because it is marked
    seen when it is pushed, so the work is bounded by the tile count and not by the number of paths.
    """
    if not is_passable(row, start[0], start[1], gate_open):
        return set(), 0
    seen = {start}
    queue = [start]
    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen:
                continue
            if is_passable(row, nx, ny, gate_open):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen, head


def door_tiles(row: dict) -> list:
    """Every tile drawn as a door, by the row's own tile legend."""
    legend = row["tile_legend"]
    return [(x, y) for y, line in enumerate(row["tiles"]) for x, char in enumerate(line)
            if legend.get(char) == "door"]


def markers_of(row: dict) -> list:
    """Encounter markers, with D1's default of story for a row that does not state the kind."""
    return [(trigger.get("marker_kind", "story"), trigger["x"], trigger["y"], trigger["id"])
            for trigger in triggers_of(row, "marker")]


def handback_tiles(row: dict, scenes: dict, map_id: str = ARRIVAL_MAP) -> set:
    """Where a cutscene hands control back: every scene trigger tile, and every scene start tile."""
    tiles = {(trigger["x"], trigger["y"]) for trigger in triggers_of(row, "scene")}
    for scene in scenes.values():
        if scene.get("map") == map_id and isinstance(scene.get("start"), dict):
            tiles.add((scene["start"]["x"], scene["start"]["y"]))
    return tiles


def walk_steps(a: tuple, b: tuple) -> int:
    """Tile steps between two tiles, Chebyshev, the least the 4-direction walk can cost."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def screen_of(x: int, y: int, screen_w: int, screen_h: int) -> tuple:
    return (x // screen_w, y // screen_h)


def engine_constants() -> dict:
    """PP_TILE, PP_VIEW_W and PP_VIEW_H as the engine defines them, not as this file wishes them."""
    text = _read(CONFIG_GML)
    found = {}
    for name in ("PP_TILE", "PP_VIEW_W", "PP_VIEW_H"):
        match = re.search(r"^#macro\s+%s\s+(\d+)" % name, text, re.MULTILINE)
        assert match, "%s is not a #macro in pp_config.gml" % name
        found[name] = int(match.group(1))
    return found


def screen_size() -> tuple:
    constants = engine_constants()
    return constants["PP_VIEW_W"], constants["PP_VIEW_H"]


# --------------------------------------------------------------------------- rules, as functions


def marker_clearance_problems(marks: list, anchors: list, clear: int = MARKER_CLEAR_TILES) -> list:
    """D1's placement rule: no marker within `clear` tiles of any named anchor tile.

    marks and anchors are (label, x, y). The distance is the Chebyshev tile step, which is never
    larger than the number of steps the 4-direction walk takes, so a pass here is a pass on foot.
    """
    problems = []
    for label, x, y in marks:
        for anchor_label, ax, ay in anchors:
            distance = walk_steps((x, y), (ax, ay))
            if distance <= clear:
                problems.append(
                    "marker %s at (%d,%d) is %d tile(s) from %s at (%d,%d), inside the %d tile clear zone"
                    % (label, x, y, distance, anchor_label, ax, ay, clear))
    return problems


def screen_marker_problems(marks: list, screen: tuple, cap: int = SCREEN_MARKER_CAP) -> list:
    """D1's screen cap: no screen window holds more than `cap` markers of either kind."""
    counts = {}
    for label, x, y in marks:
        window = screen_of(x, y, screen[0], screen[1])
        counts.setdefault(window, []).append((label, x, y))
    return ["screen %r holds %d markers (%s), the cap is %d"
            % (window, len(rows), ", ".join(row[0] for row in rows), cap)
            for window, rows in sorted(counts.items()) if len(rows) > cap]


def wild_marker_band(walkable: int) -> tuple:
    """The count of wild markers one per 40 to 60 walkable tiles allows: (lowest, highest)."""
    low = -(-walkable // WILD_TILES_PER_MARKER[1])     # ceil(walkable / 60)
    high = walkable // WILD_TILES_PER_MARKER[0]        # floor(walkable / 40)
    return low, high


def density_problems(walkable: int, wild: int) -> list:
    """D1's density band, for wild markers only. A map with no wild marker has nothing to measure."""
    if wild == 0:
        return []
    low, high = wild_marker_band(walkable)
    if low <= wild <= high:
        return []
    return ["%d wild markers on %d walkable tiles is one per %.2f, outside one per 40 to 60 "
            "(the band for this block is %d to %d)"
            % (wild, walkable, walkable / float(wild), low, high)]


def door_problems(doc: dict, map_id: str) -> list:
    """Every map trigger on a row must name a map that exists and a spawn that exists and is walkable."""
    problems = []
    rows = maps_by_id(doc)
    if map_id not in rows:
        return ["data/maps/all.json holds no map %r" % map_id]
    row = rows[map_id]
    for trigger in triggers_of(row, "map"):
        where = "map %s door %r at (%d,%d)" % (map_id, trigger["id"], trigger["x"], trigger["y"])
        target = trigger["id"]
        if target not in rows:
            problems.append("%s names %r, which is not a map in data/maps/all.json" % (where, target))
            continue
        spawn = trigger.get("spawn")
        if not spawn:
            problems.append("%s names no spawn on %r" % (where, target))
            continue
        points = rows[target].get("spawns", {})
        if spawn not in points:
            problems.append("%s names spawn %r, which is not on map %r (it has %s)"
                            % (where, spawn, target, ", ".join(sorted(points))))
            continue
        point = points[spawn]
        if not is_passable(rows[target], point["x"], point["y"], gate_open=story_gate_is_open(rows[target])):
            problems.append("%s lands on %r at (%d,%d), which is not walkable"
                            % (where, spawn, point["x"], point["y"]))
    return problems


def scene_commands_implemented(source: str) -> tuple:
    """The commands pp_scene_command_start has a case for, and whether it guards the rest.

    A scene command with no case is not refused: pp_scene_command_start's default branch counts it
    as unknown, says so on the debug channel and moves on. That silence is why the set is measured
    from the engine rather than assumed.
    """
    start = source.index("function pp_scene_command_start")
    end = source.find("\nfunction ", start + 1)
    body = source[start:end if end != -1 else len(source)]
    has_default = re.search(r"^\s*default:", body, re.MULTILINE) is not None
    return set(re.findall(r'^\s*case "([a-z_]+)":', body, re.MULTILINE)), has_default


def scene_closure(scenes: dict, roots: list) -> dict:
    """The root scenes plus every scene their branch commands can reach, by id."""
    seen = {}
    queue = list(roots)
    while queue:
        scene_id = queue.pop()
        if scene_id in seen:
            continue
        assert scene_id in scenes, "a scene names %r, which is not in data/scenes/all.json" % scene_id
        seen[scene_id] = scenes[scene_id]
        for command in scenes[scene_id]["commands"]:
            if command["cmd"] == "branch" and "scene" in command:
                queue.append(command["scene"])
    return seen


# --------------------------------------------------------------------------- 0. the rules themselves


def test_the_rules_this_file_measures_are_the_ones_the_sources_state():
    """The numbers above are read from these files, so a study or ruling change fails here first."""
    spec = _read(SPEC_04)
    assert "16 by 15 tiles visible" in spec, "spec 04 no longer states the 16 by 15 tile screen"

    study = _read(STUDY)
    assert "One marker per 40 to 60 walkable tiles" in study, "6.2 no longer states the 40 to 60 band"
    assert "No marker within 6 tiles of a map entry, a door" in study, "6.2 no longer states the 6 tile rule"

    decisions = _read(DECISIONS)
    assert "1 per 40 to 60 walkable tiles" in decisions, "D1 no longer states the wild density band"
    assert "at most 2 on screen" in decisions, "D1 no longer states the screen cap"
    assert "`wild`" in decisions and "`story`" in decisions, "D1 no longer splits the marker kinds"

    map_gml = _read(MAP_GML)
    assert 'if (_ch == "2")' in map_gml, "pp_map_collision no longer reads the story blocked 2 tile"
    assert "return 0;" in map_gml, "pp_map_collision no longer returns 0 for a walkable tile"


# --------------------------------------------------------------------------- 1. the file parses


def test_the_maps_file_validates_against_the_published_schema():
    """The schema in data/schemas is enforced, not skipped: a schema nobody runs is a rotting document."""
    try:
        import jsonschema
    except ImportError:
        pytest.fail("jsonschema is not installed, so data/schemas/maps.schema.json cannot be enforced "
                    "(python -m pip install jsonschema)")

    schema = _load(MAPS_SCHEMA_PATH)
    doc = _load(MAPS_PATH)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc),
                    key=lambda error: list(error.absolute_path))
    assert errors == [], "\n".join("%s: %s" % (list(error.absolute_path), error.message)
                                   for error in errors[:6])


def test_the_scenes_the_block_reads_validate_against_their_schema(scenes_doc):
    try:
        import jsonschema
    except ImportError:
        pytest.fail("jsonschema is not installed, so data/schemas/cutscenes.schema.json cannot be enforced")

    schema = _load(SCENES_SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(scenes_doc),
                    key=lambda error: list(error.absolute_path))
    assert errors == [], "\n".join("%s: %s" % (list(error.absolute_path), error.message)
                                   for error in errors[:6])


def test_every_grid_row_is_the_size_the_row_declares(arrival):
    """The cross-row rule JSON Schema cannot express, which every measurement below depends on."""
    width, height = arrival["width"], arrival["height"]
    assert (width, height) == ARRIVAL_SIZE, (width, height)
    for name in ("tiles", "collision"):
        grid = arrival[name]
        assert len(grid) == height, "%s has %d rows, the row declares %d" % (name, len(grid), height)
        for index, line in enumerate(grid):
            assert len(line) == width, "%s[%d] is %d characters, the row declares %d" % (
                name, index, len(line), width)
    for index, line in enumerate(arrival["tiles"]):
        unknown = set(line) - set(arrival["tile_legend"])
        assert not unknown, "tiles[%d] uses %s, which the tile legend does not name" % (index, sorted(unknown))
    for index, line in enumerate(arrival["collision"]):
        assert set(line) <= set("012"), "collision[%d] uses a character that is not 0, 1 or 2" % index


# --------------------------------------------------------------------------- 2. the spawn


def test_the_entry_spawn_is_on_a_walkable_tile_and_not_walled_in(arrival):
    """The card asks for every tile around the entry to be walkable; the row has a wall on two of them.

    Measured here: 3 of the 4 orthogonal neighbours are walkable, the east one at 12,1 is a building
    wall, and the north east at 12,0 is a second. So this test proves the part that playability
    needs and that the row can pass: the spawn is walkable, it is not walled in, and every open side
    is part of the same walkable area. The clearance gap is on the card as a Q: for gamedev.
    """
    entry = arrival["spawns"][ENTRY_SPAWN]
    assert cell_of(arrival, entry["x"], entry["y"]) == "0", (
        "the entry spawn %r sits on a blocked tile (%s)" % (ENTRY_SPAWN, cell_of(arrival, entry["x"], entry["y"])))

    off_map = [(entry["x"] + dx, entry["y"] + dy) for dx, dy in DIRECTIONS
               if cell_of(arrival, entry["x"] + dx, entry["y"] + dy) == "off"]
    assert off_map == [], "the entry spawn %r is on the map edge, with %s off the map" % (ENTRY_SPAWN, off_map)

    open_sides = [(entry["x"] + dx, entry["y"] + dy) for dx, dy in DIRECTIONS
                  if cell_of(arrival, entry["x"] + dx, entry["y"] + dy) == "0"]
    assert len(open_sides) >= 2, (
        "the entry spawn %r at (%d,%d) has %d open side(s) out of 4, so the hero is in a dead end"
        % (ENTRY_SPAWN, entry["x"], entry["y"], len(open_sides)))

    reachable, _ = flood_fill(arrival, (entry["x"], entry["y"]), gate_open=False)
    stranded = [tile for tile in open_sides if tile not in reachable]
    assert stranded == [], (
        "the entry spawn has open side(s) at %s that no walk reaches, so they are a wall with a floor tile"
        % stranded)


def test_every_named_spawn_on_the_block_is_walkable_and_inside_the_map(arrival):
    """A door anywhere in the file may land on any of these, so each one has to be standable."""
    problems = []
    for name, point in sorted(arrival["spawns"].items()):
        char = cell_of(arrival, point["x"], point["y"])
        if char != "0":
            problems.append("spawn %r at (%d,%d) is on collision %r, not 0"
                            % (name, point["x"], point["y"], char))
    assert problems == [], problems
    assert set(arrival["spawns"]) == {"start", "from_gate", "from_office", "from_pier"}, \
        sorted(arrival["spawns"])


# --------------------------------------------------------------------------- 3. the doors


def test_every_door_names_a_target_map_and_a_spawn_that_exist(maps_doc):
    assert door_problems(maps_doc, ARRIVAL_MAP) == [], door_problems(maps_doc, ARRIVAL_MAP)


def test_every_door_tile_is_drawn_as_a_door_and_answers_something(arrival):
    """A door drawn on the art with nothing behind it is a lie on screen, and the reverse is a hidden door.

    One exception is named, not excused: the ship gangway at the pier head is a map trigger standing on
    a walkable pier tile, because a gangway is not a building door and the pier has no door art (card
    t_67a36372). Every other map trigger must still be drawn as a door.
    """
    drawn = set(door_tiles(arrival))
    firing = {(trigger["x"], trigger["y"]) for trigger in arrival["triggers"]}
    map_triggers = triggers_of(arrival, "map")
    gangway = [trigger for trigger in map_triggers if trigger["id"] == GANGWAY_MAP]
    interior = [trigger for trigger in map_triggers if trigger["id"] != GANGWAY_MAP]
    map_doors = {(trigger["x"], trigger["y"]) for trigger in interior}

    hidden = sorted(map_doors - drawn)
    assert hidden == [], "map trigger(s) at %s are not drawn as doors" % hidden
    silent = sorted(drawn - firing)
    assert silent == [], "tile(s) %s are drawn as doors and no trigger answers them" % silent

    assert len(drawn) == 8, "the block carries %d door tiles, ARRIVAL-CONTENT names 8" % len(drawn)
    assert len(interior) == 1, (
        "the block carries %d interior map doors; ARRIVAL-CONTENT makes the dock office the only "
        "interior, so the other doors are say triggers" % len(interior))

    assert len(gangway) == 1, (
        "the block carries %d gangway triggers to %r, the pier head needs 1"
        % (len(gangway), GANGWAY_MAP))
    tile = (gangway[0]["x"], gangway[0]["y"])
    assert tile not in drawn, "the gangway tile %s is drawn as a door, which a gangway is not" % (tile,)
    assert arrival["collision"][tile[1]][tile[0]] == "0", (
        "the gangway tile %s is not walkable, so nobody can stand on it and confirm" % (tile,))


def test_the_door_pair_leads_back_from_where_it_drops_the_player(maps_doc):
    """No one way door: the office spawn must be able to reach the door back to the quay."""
    rows = maps_by_id(maps_doc)
    door = triggers_of(rows[ARRIVAL_MAP], "map")[0]
    assert door["id"] in rows, "the door on the block names map %r, which does not exist" % door["id"]
    office = rows[door["id"]]
    spawn_name = door["spawn"]
    spawn = office["spawns"][spawn_name]
    reachable, _ = flood_fill(office, (spawn["x"], spawn["y"]), gate_open=story_gate_is_open(office))

    back = triggers_of(office, "map")
    assert back, "map %r has no door back, so the player is locked in" % office["id"]
    for trigger in back:
        tile = (trigger["x"], trigger["y"])
        if tile in reachable:
            continue
        # A door drawn in a wall is entered by facing it (spec 04 rule 2), so a reachable neighbour
        # is enough for that tile.
        near = [(tile[0] + dx, tile[1] + dy) for dx, dy in DIRECTIONS
                if (tile[0] + dx, tile[1] + dy) in reachable]
        assert near, ("the door back at %s in map %r cannot be reached from the spawn %r at (%d,%d)"
                      % (tile, office["id"], spawn_name, spawn["x"], spawn["y"]))


# --------------------------------------------------------------------------- 4. reachability


def test_the_walkable_area_reaches_every_door(arrival):
    """A flood fill from the entry, not a guess: once with the barrier shut, once with it open."""
    entry = arrival["spawns"][ENTRY_SPAWN]
    start = (entry["x"], entry["y"])
    doors = sorted(set(door_tiles(arrival)) | {(trigger["x"], trigger["y"])
                                               for trigger in triggers_of(arrival, "map")})
    # Eight drawn doors plus the gangway at the pier head, which is on a pier tile and not door art.
    assert len(door_tiles(arrival)) == 8, door_tiles(arrival)
    assert len(doors) == 9, doors

    shut, shut_steps = flood_fill(arrival, start, gate_open=False)
    assert story_gate_is_open(arrival), (
        "the block has a story blocked tile and no story flag, so pp_map_collision never opens it")
    opened, opened_steps = flood_fill(arrival, start, gate_open=True)

    for label, reachable in (("barrier shut", shut), ("barrier open", opened)):
        unreached = [tile for tile in doors if tile not in reachable]
        assert unreached == [], (
            "%d of %d door tiles cannot be walked to from the entry spawn at %s with the %s (%s)"
            % (len(unreached), len(doors), start, label, unreached))

    assert shut <= opened, "opening the story gate closed tiles that were reachable before it"
    assert shut_steps == len(shut) and opened_steps == len(opened)
    # The fill is a proper part of the walkable area: this block is a town, so building interiors and
    # walled yards are drawn walkable and cannot be entered. What matters is that no door is one of
    # them, which the loop above proves. The split is measured on the card: 1472 of 1702 reachable
    # with the barrier shut, 230 tiles in pockets, and 1473 with it open. Card t_67a36372 added the one
    # walkable junction tile at (35,47), which took the pier's 74 tile island into the main body, so
    # the gangway at (17,38) is on the same component as the entry.
    assert len(shut) <= walkable_count(arrival), (
        "the fill reached %d tiles, more than the %d walkable ones"
        % (len(shut), walkable_count(arrival)))


def test_every_spawn_a_door_lands_on_can_be_walked_out_of(maps_doc):
    """A door that drops the player into a pocket is a soft lock, so each named entry is filled from."""
    rows = maps_by_id(maps_doc)
    problems = []
    checked = 0
    for door_row in rows.values():
        for trigger in triggers_of(door_row, "map"):
            target = trigger["id"]
            if target not in rows:
                continue
            landing = rows[target]["spawns"].get(trigger.get("spawn"))
            if landing is None:
                continue
            checked += 1
            reachable, _steps = flood_fill(rows[target], (landing["x"], landing["y"]),
                                           gate_open=story_gate_is_open(rows[target]))
            exits = [tile for tile in door_tiles(rows[target])
                     if tile in reachable or any((tile[0] + dx, tile[1] + dy) in reachable
                                                 for dx, dy in DIRECTIONS)]
            if not exits:
                problems.append("a door lands on %r of map %r at (%d,%d) and no door can be walked to from there"
                                % (trigger["spawn"], target, landing["x"], landing["y"]))
    assert checked >= 2, "the file has %d door landings to fill from, expected at least 2" % checked
    assert problems == [], problems


def test_the_flood_fill_is_iterative_and_walks_each_tile_once():
    """The card's own bound: one pass, no recursion. Both are measured, not asserted in prose."""
    source = _read(os.path.abspath(__file__))
    tree = ast.parse(source)
    fill = [node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "flood_fill"]
    assert len(fill) == 1, "the file must define flood_fill exactly once"
    nested = [node for node in ast.walk(fill[0])
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "flood_fill"]
    assert nested == [], "flood_fill calls itself, so a big map is a recursion depth risk"

    size = 250
    grid = {"id": "synthetic", "width": size, "height": size, "story_flag": "",
            "collision": ["0" * size for _ in range(size)], "tiles": [], "tile_legend": {}}
    seen, steps = flood_fill(grid, (0, 0), gate_open=False)
    assert len(seen) == size * size, "the fill reached %d of %d open tiles" % (len(seen), size * size)
    assert steps == len(seen), "%d tiles were dequeued for %d visited, so a tile was served twice" % (
        steps, len(seen))

    walled = {"id": "synthetic_wall", "width": size, "height": size, "story_flag": "",
              "collision": ["1" * size for _ in range(size)], "tiles": [], "tile_legend": {}}
    assert flood_fill(walled, (0, 0), gate_open=False) == (set(), 0)


# --------------------------------------------------------------------------- 5. the markers


def test_no_marker_is_within_six_tiles_of_the_entry_a_door_or_a_handback(arrival, scenes_by_id):
    marks = [("marker %r" % marker_id, x, y) for _kind, x, y, marker_id in markers_of(arrival)]
    assert marks, "the block carries no marker, so the scripted first encounter has nowhere to fire"

    anchors = [("the entry tile", arrival["spawns"][ENTRY_SPAWN]["x"], arrival["spawns"][ENTRY_SPAWN]["y"])]
    anchors += [("door", x, y) for x, y in sorted(set(door_tiles(arrival)))]
    anchors += [("control handback", x, y) for x, y in sorted(handback_tiles(arrival, scenes_by_id))]

    assert marker_clearance_problems(marks, anchors) == [], marker_clearance_problems(marks, anchors)


def test_the_clearance_rule_refuses_a_marker_on_the_line_and_passes_one_tile_past_it():
    """The same rule, on numbers this file owns: a rule that cannot fail is not a check."""
    entry = [("the entry tile", 10, 10)]
    on_the_line = [("marker at the limit", 10 + MARKER_CLEAR_TILES, 10)]
    one_past = [("marker one tile past", 10 + MARKER_CLEAR_TILES + 1, 10)]
    diagonal = [("marker on the diagonal limit", 10 + MARKER_CLEAR_TILES, 10 + MARKER_CLEAR_TILES)]

    assert marker_clearance_problems(on_the_line, entry) != []
    assert marker_clearance_problems(diagonal, entry) != []
    assert marker_clearance_problems(one_past, entry) == []


def test_the_marker_mix_is_the_one_the_ruling_names(arrival):
    """D1 consequence 3: no wild marker on this block, exactly one story marker, and the row says so."""
    assert arrival["encounters"] == "scripted", (
        "the block declares encounters %r; D1 keeps the block scripted" % arrival.get("encounters"))
    kinds = [kind for kind, _x, _y, _id in markers_of(arrival)]
    explicit = [trigger for trigger in triggers_of(arrival, "marker") if "marker_kind" in trigger]
    assert len(explicit) == len(kinds), "a marker on this row does not state its marker_kind (D1 rule 4)"
    assert kinds.count("wild") == 0, "%d wild marker(s) on a scripted block" % kinds.count("wild")
    assert kinds.count("story") == 1, "the block carries %d story marker(s), D1 names 1" % kinds.count("story")

    marker = triggers_of(arrival, "marker")[0]
    assert marker["once"] is True, "a story marker fires once and never re-arms (D1), this one does not"


def test_no_screen_holds_more_than_two_markers(arrival):
    """D1's cap, on the real markers; with the block carrying one marker the card's stricter line holds too."""
    screen = screen_size()
    assert screen == (16, 15), "spec 04 says 16 by 15 tiles visible, pp_config says %s" % (screen,)
    marks = [("marker %r" % marker_id, x, y) for _kind, x, y, marker_id in markers_of(arrival)]
    assert screen_marker_problems(marks, screen) == [], screen_marker_problems(marks, screen)
    # One marker cannot be two on a screen: the card's "never two on one screen" follows from the count.
    assert len(marks) == 1


def test_the_screen_cap_refuses_a_third_marker_in_one_window():
    screen = (16, 15)
    two = [("first", 0, 0), ("second", 15, 14)]
    three = [("first", 0, 0), ("second", 1, 0), ("third", 2, 0)]
    across = [("first", 0, 0), ("second", 16, 0)]
    assert screen_marker_problems(two, screen) == []
    assert screen_marker_problems(across, screen) == []
    assert screen_marker_problems(three, screen) != []


def test_the_wild_density_band_is_one_per_forty_to_sixty_walkable_tiles(arrival):
    """D1's band, exercised on this block's own walkable count and on the counts either side of it."""
    assert walkable_count(arrival) == ARRIVAL_WALKABLE, (
        "the block has %d walkable tiles with the barrier shut, D1 names %d"
        % (walkable_count(arrival), ARRIVAL_WALKABLE))
    assert walkable_count(arrival, gate_open=True) == ARRIVAL_WALKABLE + 1, (
        "the story gate changes the walkable count by more than the one tile the barrier occupies")

    low, high = wild_marker_band(ARRIVAL_WALKABLE)
    assert (low, high) == (29, 42), (
        "1701 walkable tiles at one per 40 to 60 is %d to %d wild markers" % (low, high))
    assert density_problems(ARRIVAL_WALKABLE, low) == []
    assert density_problems(ARRIVAL_WALKABLE, high) == []
    assert density_problems(ARRIVAL_WALKABLE, low - 1) != [], "one wild marker too few passed the band"
    assert density_problems(ARRIVAL_WALKABLE, high + 1) != [], "one wild marker too many passed the band"

    # The block itself carries no wild marker, so the band has nothing to measure: D1 rules that a
    # scripted block's authored marker count wins, and the story count is checked above.
    assert density_problems(walkable_count(arrival), 0) == []
    assert markers_of(arrival)[0][0] == "story"


# --------------------------------------------------------------------------- 6. the gate scene


def test_the_engine_and_the_checker_agree_on_the_commands_a_scene_may_use():
    """Two files state the command list; if they drift, a scene the engine skips passes the checker."""
    import check_data

    implemented, has_default = scene_commands_implemented(_read(SCENE_GML))
    assert implemented == set(check_data.SCENE_COMMANDS), (
        "pp_scene implements %s, tools/check_data.py allows %s"
        % (sorted(implemented), sorted(check_data.SCENE_COMMANDS)))
    assert has_default, (
        "pp_scene_command_start has no default branch, so this test cannot rely on an unknown command "
        "being skipped instead of crashing")
    assert "end" in implemented, "a scene cannot end"


def test_every_command_in_the_gate_scene_is_one_pp_scene_implements(arrival, scenes_by_id):
    """The gate scene, its three replies, the yard walk and the office, each command checked."""
    implemented, _has_default = scene_commands_implemented(_read(SCENE_GML))

    scene_trigger = [trigger for trigger in triggers_of(arrival, "scene")
                     if trigger["id"] == "quay_gate_checkpoint"]
    assert len(scene_trigger) == 1, (
        "the block has %d triggers for the gate scene quay_gate_checkpoint, expected 1" % len(scene_trigger))

    roots = [trigger["id"] for trigger in triggers_of(arrival, "scene")]
    assert roots, "the block triggers no scene"
    for scene_id in roots:
        assert scene_id in scenes_by_id, "%r is not a scene in data/scenes/all.json" % scene_id
        assert scenes_by_id[scene_id].get("map") == ARRIVAL_MAP, (
            "scene %r runs on map %r, not on the block it is triggered from"
            % (scene_id, scenes_by_id[scene_id].get("map")))

    reached = scene_closure(scenes_by_id, roots)
    unknown = []
    for scene_id, scene in sorted(reached.items()):
        for index, command in enumerate(scene["commands"]):
            if command["cmd"] not in implemented:
                unknown.append("%s[%d] is %r" % (scene_id, index, command["cmd"]))
    assert unknown == [], "pp_scene has no case for %s and would skip it in silence" % unknown

    for scene_id, scene in sorted(reached.items()):
        assert scene["commands"][-1]["cmd"] == "end", (
            "scene %r stops at %r, so it runs out of commands instead of ending"
            % (scene_id, scene["commands"][-1]["cmd"]))

    gate = reached["quay_gate_checkpoint"]
    assert [command["cmd"] for command in gate["commands"]] == [
        "music", "say", "say", "branch", "branch", "branch", "end"], (
            "the gate scene's commands changed: %s" % [command["cmd"] for command in gate["commands"]])
    assert set(reached) == {"quay_gate_checkpoint", "quay_gate_truth", "quay_gate_bluff",
                            "quay_gate_authority", "quay_yard_walk"}, sorted(reached)


# --------------------------------------------------------------------------- 7. the failing run


def test_a_door_pointed_at_a_missing_map_is_refused(tmp_path, maps_doc):
    """The card's own failing case, in a temp copy: a door whose target map does not exist."""
    copy = tmp_path / "all.json"
    broken = json.loads(json.dumps(maps_doc))
    door = triggers_of(maps_by_id(broken)[ARRIVAL_MAP], "map")[0]
    door["id"] = "quay_dock_offices"
    copy.write_text(json.dumps(broken, indent=2), encoding="utf-8", newline="\n")

    problems = door_problems(_load(str(copy)), ARRIVAL_MAP)
    assert problems, "a door pointed at a map that does not exist passed the door check"
    assert any("quay_dock_offices" in line and "not a map" in line for line in problems), problems


def test_a_door_pointed_at_a_missing_spawn_is_refused(tmp_path, maps_doc):
    copy = tmp_path / "all.json"
    broken = json.loads(json.dumps(maps_doc))
    rows = maps_by_id(broken)

    found = None
    for row_id, row in sorted(rows.items()):
        for trigger in triggers_of(row, "map"):
            target = rows.get(trigger["id"])
            if target is not None and trigger.get("spawn") in target["spawns"]:
                found = (row_id, trigger, target)
                break
        if found is not None:
            break
    assert found is not None, "no door in this copy names a map and a spawn that both exist"
    row_id, door, target = found

    missing = "from_the_pier"
    assert missing not in target["spawns"], "%r is a real spawn, so the case would not be missing" % missing
    door["spawn"] = missing
    copy.write_text(json.dumps(broken, indent=2), encoding="utf-8", newline="\n")

    problems = door_problems(_load(str(copy)), row_id)
    assert problems, "a door pointed at a spawn that does not exist passed the door check"
    assert any(missing in line and "not on map" in line for line in problems), problems
