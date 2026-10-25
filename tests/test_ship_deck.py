"""The ship deck and the log save, proven from the data, without running GameMaker (card t_39aeaa6f, step S5).

Nothing here executes GML. Every assertion reads a real file and computes the answer from it, so a
change in the deck row, the colour lists, the scene rows or the runner's own command switch fails
here instead of in a playtest. The 25 checks the S5 card proved with a throwaway script, which is
gone, live here now, where every gate runs them.

Sources this file measures, never restates:

    data/maps/all.json                          the ship_small and ship_cabin rows
    data/scenes/all.json                        ship_boarding and ship_log
    data/slice.json                             the save step and the trigger it names
    data/palette.json                           the master palette roles
    data/room_palettes.json                     the named colour sets a room resolves through
    game/sprites_src/env/ts_ship.json           the 48 tile ship sheet the deck names
    game/scripts/pp_config/pp_config.gml        PP_TILE 16
    game/scripts/pp_map/pp_map.gml              pp_map_collision: 0 walkable, 1 blocked, 2 story blocked
    game/scripts/pp_overworld/pp_overworld.gml  pp_world_dir_vector, and the all or nothing move
    game/scripts/pp_scene/pp_scene.gml          pp_scene_commands, the runner's own list
    tools/check_data.py                         SCENE_COMMANDS and MAX_COLOURS_ON_SCREEN

What is proven, in the card's own order:

  1. ship_small names tileset ts_ship, and the manifest beside the sheet declares 48 frames of 16 by
     16 in 16 columns, which is 3 rows of 16;
  2. both ship rows' palette_indices equal, as a sorted list, the colours their room_palette resolves
     to through data/room_palettes.json and data/palette.json, and neither list is over the 16 colour
     screen cap;
  3. every tile character of the deck is a key of its own legend, and every cell's collision follows
     its character: #, C and P blocked; ., G, H and D walkable; except the story blocked hatch at 18,7;
  4. the pinned tiles the other suites read are still the pinned tiles: 18,7 story blocked, 5,3
     blocked, the one battle trigger 2 tiles east of spawns.start with a clear line, and all four
     spawns plus the save point walkable;
  5. every walkable cell of the deck is reachable from spawns.start, 176 of 176, and opening the story
     flag adds exactly the one hatch tile and nothing else;
  6. the runner's own command list and check_data.SCENE_COMMANDS are the same 16 strings, both ship
     scenes use only those, and both end on end;
  7. the log scene's own move commands, simulated from its start tile against the collision grid,
     land the hero on the tile that carries the save trigger deck_save at 3,2.

The card's three mutations are rows in this file, run on a deep copy of the real data so the tree is
never written: a palette index the set does not resolve to, a log move one tile too far, and a
deleted deck_save trigger. Each one is refused by the same function the real row passes through.

Two places the card's prose and the shipped grid disagree, measured here and reported rather than
quietly followed:

  - the card calls 3,1 the bulkhead a 6 tile move walks into. On the shipped grid 3,1 is the back
    floor of the watch cabin, and the bulkhead is 3,0: a 6 tile move therefore reaches a legal tile
    that carries no save, and a 7 tile move is the one the engine refuses at the wall. The mutation
    row below asserts both, so the check is red either way;
  - the card's "25 checks" is the S5 verifier's own count. This file holds them as 24 named rows,
    because two verifier lines (the deck size and the trigger count) are folded into the rows that
    would be meaningless without them.

No test in this file reads the network, writes a tracked data file, or needs a key. The maps and the
scenes files can be pointed at a copy with PP_SHIP_DECK_MAPS and PP_SHIP_DECK_SCENES, the same knob
tests/test_arrival_map.py carries, so a broken deck or scene can be shown to fail these rows and not
only a helper.
"""

from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAPS_PATH = os.environ.get("PP_SHIP_DECK_MAPS") or os.path.join(ROOT, "data", "maps", "all.json")
SCENES_PATH = os.environ.get("PP_SHIP_DECK_SCENES") or os.path.join(ROOT, "data", "scenes", "all.json")
SLICE_PATH = os.path.join(ROOT, "data", "slice.json")
PALETTE_PATH = os.path.join(ROOT, "data", "palette.json")
ROOM_PALETTES_PATH = os.path.join(ROOT, "data", "room_palettes.json")
SHEET_PATH = os.path.join(ROOT, "game", "sprites_src", "env", "ts_ship.json")
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
MAP_GML = os.path.join(ROOT, "game", "scripts", "pp_map", "pp_map.gml")
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
SCENE_GML = os.path.join(ROOT, "game", "scripts", "pp_scene", "pp_scene.gml")

DECK = "ship_small"
CABIN = "ship_cabin"
DECK_SIZE = (20, 15)
DECK_WALKABLE = 176
DECK_TRIGGERS = 7

# The sheet the deck names: 48 tiles of 16 by 16, 16 to a row, so 3 rows.
SHEET = "ts_ship"
SHEET_FRAMES = 48
SHEET_COLUMNS = 16
SHEET_ROWS = 3
SHEET_FRAME = 16

# The card's own character rules for this deck, with the one story blocked hatch named apart.
LEGEND_COLLISION = {"#": "1", "C": "1", "P": "1", ".": "0", "G": "0", "H": "0", "D": "0"}
STORY_CELLS = {(18, 7): "2"}
STORY_FLAG = "ship_door_open"

# The tiles other suites pin, and the two the beats ride on.
PINNED_STORY_TILE = (18, 7)
PINNED_BLOCKED_TILE = (5, 3)
FIGHT_TRIGGER_OFFSET = 2
SAVE_ID = "deck_save"
SAVE_TILE = (3, 2)

LOG_SCENE = "ship_log"
BOARDING_SCENE = "ship_boarding"
LOG_START = (3, 7)
LOG_PATH = [(3, 7), (3, 6), (3, 5), (3, 4), (3, 3), (3, 2)]
RUNNER_COMMANDS = 16

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# --------------------------------------------------------------------------- reading files


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _copy(value):
    """A deep copy, so a mutation row breaks a throwaway tree and never the file on disk."""
    return json.loads(json.dumps(value))


@pytest.fixture(scope="module")
def maps_doc() -> dict:
    return _load(MAPS_PATH)


@pytest.fixture(scope="module")
def scenes_doc() -> dict:
    return _load(SCENES_PATH)


@pytest.fixture(scope="module")
def palette_doc() -> dict:
    return _load(PALETTE_PATH)


@pytest.fixture(scope="module")
def room_palettes_doc() -> dict:
    return _load(ROOM_PALETTES_PATH)


@pytest.fixture(scope="module")
def sheet() -> dict:
    return _load(SHEET_PATH)


@pytest.fixture(scope="module")
def rows(maps_doc: dict) -> dict:
    return maps_by_id(maps_doc)


@pytest.fixture(scope="module")
def deck(rows: dict) -> dict:
    assert DECK in rows, "data/maps/all.json holds no map %r" % DECK
    return rows[DECK]


@pytest.fixture(scope="module")
def cabin(rows: dict) -> dict:
    assert CABIN in rows, "data/maps/all.json holds no map %r" % CABIN
    return rows[CABIN]


@pytest.fixture(scope="module")
def scenes(scenes_doc: dict) -> dict:
    return {row["id"]: row for row in scenes_doc["scenes"]}


# --------------------------------------------------------------------------- map geometry


def maps_by_id(doc: dict) -> dict:
    return {row["id"]: row for row in doc["maps"]}


def triggers_of(row: dict, kind: str = None) -> list:
    found = row.get("triggers", [])
    if kind is None:
        return list(found)
    return [trigger for trigger in found if trigger.get("kind") == kind]


def trigger_at(row: dict, x: int, y: int, kind: str = None) -> list:
    return [trigger for trigger in triggers_of(row, kind)
            if trigger["x"] == x and trigger["y"] == y]


def cell_char(row: dict, x: int, y: int) -> str:
    """The collision character at a tile, or "off" outside the map (pp_map_collision returns 1 there)."""
    if x < 0 or y < 0 or y >= len(row["collision"]) or x >= len(row["collision"][y]):
        return "off"
    return row["collision"][y][x]


def tile_char(row: dict, x: int, y: int) -> str:
    if x < 0 or y < 0 or y >= len(row["tiles"]) or x >= len(row["tiles"][y]):
        return "off"
    return row["tiles"][y][x]


def is_walkable(row: dict, x: int, y: int, gate_open: bool = False) -> bool:
    """Mirror of pp_map_collision: 0 is walkable, 2 is walkable only while the story flag is set."""
    char = cell_char(row, x, y)
    if char == "0":
        return True
    if char == "2":
        return gate_open
    return False


def walkable_tiles(row: dict, gate_open: bool = False) -> list:
    return [(x, y) for y in range(row["height"]) for x in range(row["width"])
            if is_walkable(row, x, y, gate_open)]


def flood_fill(row: dict, start: tuple, gate_open: bool = False) -> tuple:
    """Every tile reachable from start in four directions, and how many rows the queue served.

    Iterative on purpose, one enqueue per tile, the same bound the arrival map's fill carries: a
    recursive fill on a big map is a stack overflow waiting for the first one.
    """
    if not is_walkable(row, start[0], start[1], gate_open):
        return set(), 0
    seen = {start}
    queue = [start]
    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen or not is_walkable(row, nx, ny, gate_open):
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return seen, head


# --------------------------------------------------------------------------- the deck's rules


def sheet_problems(row: dict, manifest: dict) -> list:
    """The deck's tileset, and the manifest beside the sheet, must describe the same 48 tiles."""
    problems = []
    named = row.get("tileset")
    if named != SHEET:
        problems.append("map %r names tileset %r, the deck is drawn from %r" % (row["id"], named, SHEET))
    if manifest.get("name") != SHEET:
        problems.append("game/sprites_src/env/ts_ship.json names %r, not %r"
                        % (manifest.get("name"), SHEET))
    frames = manifest.get("frames")
    columns = manifest.get("columns")
    rows = manifest.get("rows")
    if frames != SHEET_FRAMES:
        problems.append("the sheet declares %r frames, the deck's set is %d" % (frames, SHEET_FRAMES))
    if columns != SHEET_COLUMNS:
        problems.append("the sheet declares %r columns, the deck's set is %d" % (columns, SHEET_COLUMNS))
    if rows != SHEET_ROWS:
        problems.append("the sheet declares %r rows, %d frames in %d columns is %d rows"
                        % (rows, SHEET_FRAMES, SHEET_COLUMNS, SHEET_ROWS))
    if columns and rows and frames != columns * rows:
        problems.append("the sheet says %r frames but %r columns by %r rows is %d"
                        % (frames, columns, rows, columns * rows))
    for field in ("frame_w", "frame_h"):
        if manifest.get(field) != SHEET_FRAME:
            problems.append("the sheet declares %s %r, a tile of this deck is %d"
                            % (field, manifest.get(field), SHEET_FRAME))
    return problems


def palette_problems(row: dict, palette: dict, room_palettes: dict, cap: int) -> list:
    """A row's palette_indices must be exactly what its room_palette resolves to, and fit the cap."""
    problems = []
    sets = {named["id"]: named for named in room_palettes.get("sets", [])}
    set_id = row.get("room_palette")
    if set_id not in sets:
        return ["map %r names room_palette %r, which is not a set in data/room_palettes.json (it has %s)"
                % (row["id"], set_id, ", ".join(sorted(sets)))]

    roles = palette.get("roles", {})
    named_roles = sets[set_id].get("roles", [])
    unknown = [name for name in named_roles if name not in roles]
    if unknown:
        problems.append("set %r names %s, which data/palette.json has no role for" % (set_id, unknown))
    resolved = sorted({roles[name] for name in named_roles if name in roles})

    listed = row.get("palette_indices")
    if not isinstance(listed, list):
        return problems + ["map %r carries no palette_indices list" % row["id"]]
    if sorted(listed) != resolved:
        extra = sorted(set(listed) - set(resolved))
        missing = sorted(set(resolved) - set(listed))
        problems.append(
            "map %r lists palette_indices %s, its set %r resolves to %s (extra %s, missing %s)"
            % (row["id"], sorted(listed), set_id, resolved, extra, missing))
    if len(listed) > cap:
        problems.append("map %r lists %d colours, the screen cap is %d"
                        % (row["id"], len(listed), cap))
    return problems


def legend_problems(row: dict) -> list:
    """Every character the grid draws must be in the legend, and every legend entry must be drawn."""
    problems = []
    legend = row.get("tile_legend", {})
    used = set()
    for y, line in enumerate(row.get("tiles", [])):
        used |= set(line)
        unknown = sorted(set(line) - set(legend))
        if unknown:
            problems.append("tiles[%d] draws %s, which the legend of %r does not name"
                            % (y, unknown, row["id"]))
    unused = sorted(set(legend) - used)
    if unused:
        problems.append("the legend of %r names %s, which no tile of the deck draws"
                        % (row["id"], unused))
    return problems


def collision_problems(row: dict, legend_collision: dict = None, story_cells: dict = None) -> list:
    """Every cell's collision character must follow the character drawn under it."""
    legend_collision = LEGEND_COLLISION if legend_collision is None else legend_collision
    story_cells = STORY_CELLS if story_cells is None else story_cells
    problems = []
    for y, line in enumerate(row.get("tiles", [])):
        for x, char in enumerate(line):
            drawn = story_cells.get((x, y), legend_collision.get(char))
            if drawn is None:
                problems.append("(%d,%d) draws %r, which this file has no collision rule for" % (x, y, char))
                continue
            actual = cell_char(row, x, y)
            if actual != drawn:
                problems.append("(%d,%d) draws %r and collides %r, its rule is %r"
                                % (x, y, char, actual, drawn))
    return problems


def walk_hero(scene: dict, row: dict, vectors: dict, gate_open: bool = False) -> tuple:
    """Walk a scene's own move commands from its start tile, the way pp_scene and pp_overworld do.

    pp_world_start_move refuses a move whose every tile is not walkable, and the hero does not move
    at all when it does, so a step onto a wall is a refused move and not a walk that stops short.
    """
    start = scene.get("start") or {}
    if "x" not in start or "y" not in start:
        return [], ["scene %r has no start tile to walk from" % scene.get("id")]
    x, y = start["x"], start["y"]
    path = [(x, y)]
    problems = []
    for index, command in enumerate(scene.get("commands", [])):
        if command.get("cmd") != "move":
            continue
        if command.get("actor", "hero") != "hero":
            continue
        direction = command.get("dir")
        if direction not in vectors:
            problems.append("commands[%d] moves %r, which pp_world_dir_vector does not know, so the "
                            "hero does not move" % (index, direction))
            continue
        dx, dy = vectors[direction]
        tiles = command.get("tiles", 1)
        target = (x + dx * tiles, y + dy * tiles)
        blocked = []
        for step in range(1, tiles + 1):
            nx, ny = x + dx * step, y + dy * step
            if not is_walkable(row, nx, ny, gate_open):
                blocked.append(((nx, ny), cell_char(row, nx, ny)))
        if blocked:
            problems.append("commands[%d] moves %r %d tile(s) to %s and is refused at %s (collision %r)"
                            % (index, direction, tiles, target, blocked[0][0], blocked[0][1]))
            continue
        for step in range(1, tiles + 1):
            path.append((x + dx * step, y + dy * step))
        x, y = target
    return path, problems


def save_problems(scene: dict, row: dict, vectors: dict) -> list:
    """The log scene must finish on a tile that carries a save trigger, or the beat has no save."""
    path, problems = walk_hero(scene, row, vectors)
    if not path:
        return problems or ["the log scene walks nowhere"]
    final = path[-1]
    if not trigger_at(row, final[0], final[1], "save"):
        problems.append("the walk of %r ends at %s, where map %r carries no save trigger (it carries %s)"
                        % (scene.get("id"), final, row["id"],
                           sorted((trigger["kind"], trigger["x"], trigger["y"])
                                  for trigger in triggers_of(row))))
    return problems


def runner_commands(source: str) -> list:
    """The command list pp_scene_commands() returns, read out of the runner itself."""
    start = source.index("function pp_scene_commands")
    end = source.index("\n}", start)
    body = source[start:end]
    found = re.findall(r'"([a-z_]+)"', body)
    assert found, "pp_scene_commands() returns no command names this file can read"
    return found


def direction_vectors(source: str) -> dict:
    """pp_world_dir_vector's own table, so a renamed direction fails here and not in a playtest."""
    start = source.index("function pp_world_dir_vector")
    end = source.index("\n}", start)
    body = source[start:end]
    found = re.findall(r'case "([a-z]+)":\s*return \{ x: (-?\d+), y: (-?\d+) \};', body)
    assert found, "pp_world_dir_vector states no direction vectors this file can read"
    return {name: (int(x), int(y)) for name, x, y in found}


def unknown_command_problems(scenes: list, implemented) -> list:
    problems = []
    for scene in scenes:
        for index, command in enumerate(scene.get("commands", [])):
            if command.get("cmd") not in implemented:
                problems.append("scene %r commands[%d] is %r, which the runner has no case for"
                                % (scene.get("id"), index, command.get("cmd")))
    return problems


def unpinned_command_problems(scenes: list, implemented) -> list:
    """A scene that does not end on end runs out of commands instead, which is not an ending."""
    return ["scene %r ends on %r, not end" % (scene.get("id"), scene["commands"][-1].get("cmd"))
            for scene in scenes
            if not scene.get("commands") or scene["commands"][-1].get("cmd") != "end"]


# --------------------------------------------------------------------------- 0. the engine's own numbers


def test_the_engine_constants_this_file_reads_are_the_ones_pp_config_states(deck):
    """The tile size and the collision codes are read from the engine, so a change there fails here."""
    config = _read(CONFIG_GML)
    match = re.search(r"^#macro\s+PP_TILE\s+(\d+)", config, re.MULTILINE)
    assert match, "PP_TILE is no longer a #macro in pp_config.gml"
    assert int(match.group(1)) == SHEET_FRAME, (
        "pp_config says a tile is %s px, the ship sheet is %d" % (match.group(1), SHEET_FRAME))

    maps = _load(MAPS_PATH)
    assert maps.get("tile_size") == SHEET_FRAME, (
        "data/maps/all.json declares tile_size %r, the ship sheet is %d"
        % (maps.get("tile_size"), SHEET_FRAME))

    map_gml = _read(MAP_GML)
    assert 'if (_ch == "2")' in map_gml, "pp_map_collision no longer reads the story blocked 2 tile"
    assert 'if (_ch == "1") return 1;' in map_gml, "pp_map_collision no longer reads 1 as blocked"
    assert "return 0;" in map_gml, "pp_map_collision no longer returns 0 for a walkable tile"
    assert cell_char(deck, -1, 0) == "off" and cell_char(deck, 0, deck["height"]) == "off"


# --------------------------------------------------------------------------- 1. the sheet


def test_the_deck_names_the_48_tile_ship_sheet(deck, sheet):
    """The card's first line: the deck map uses the 48 tile ship set, and the manifest says so too."""
    problems = sheet_problems(deck, sheet)
    assert problems == [], problems
    assert deck.get("tileset") == SHEET


# --------------------------------------------------------------------------- 2. the colours


def test_the_deck_palette_indices_are_exactly_what_deck_day_resolves_to(deck, palette_doc,
                                                                       room_palettes_doc):
    """Both ship rows were wrong before this card: the deck carried accent 17 and hazard 53."""
    import check_data

    assert check_data.MAX_COLOURS_ON_SCREEN == 16, (
        "tools/check_data.py caps a screen at %d colours" % check_data.MAX_COLOURS_ON_SCREEN)
    problems = palette_problems(deck, palette_doc, room_palettes_doc, check_data.MAX_COLOURS_ON_SCREEN)
    assert problems == [], problems
    assert len(deck["palette_indices"]) == 13, (
        "deck_day resolves to 13 colours, the deck lists %d" % len(deck["palette_indices"]))
    assert 17 not in deck["palette_indices"] and 53 not in deck["palette_indices"], (
        "the deck lists accent 17 or hazard 53, which deck_day does not declare")


def test_the_cabin_palette_indices_are_exactly_what_its_set_resolves_to(cabin, palette_doc,
                                                                       room_palettes_doc):
    """The cabin carried 10 and 17, which its own set does not declare."""
    import check_data

    problems = palette_problems(cabin, palette_doc, room_palettes_doc, check_data.MAX_COLOURS_ON_SCREEN)
    assert problems == [], problems
    assert len(cabin["palette_indices"]) == 13, (
        "ship_cabin resolves to 13 colours, the cabin lists %d" % len(cabin["palette_indices"]))
    assert 17 not in cabin["palette_indices"], "the cabin lists accent 17, its set does not declare it"


def test_a_palette_index_the_room_set_does_not_resolve_is_refused(deck, palette_doc,
                                                                  room_palettes_doc):
    """The card's first mutation, on a copy: add hazard 53 to the deck and row 2 must go red."""
    import check_data

    cap = check_data.MAX_COLOURS_ON_SCREEN
    assert palette_problems(deck, palette_doc, room_palettes_doc, cap) == []

    broken = _copy(deck)
    broken["palette_indices"] = sorted(broken["palette_indices"] + [53])
    problems = palette_problems(broken, palette_doc, room_palettes_doc, cap)
    assert problems, "a palette index deck_day does not resolve to passed the colour check"
    assert any("53" in line and "extra" in line for line in problems), problems
    assert any("ship_small" in line for line in problems), problems


def test_a_colour_list_over_the_screen_cap_is_refused():
    """The cap is a rule on numbers this file owns, so it is exercised where it can fail alone."""
    palette = {"roles": {"c%02d" % index: index for index in range(20)}}
    room_palettes = {"sets": [
        {"id": "narrow", "roles": ["c%02d" % index for index in range(16)]},
        {"id": "wide", "roles": ["c%02d" % index for index in range(20)]},
    ]}

    sixteen = {"id": "synthetic", "room_palette": "narrow", "palette_indices": list(range(16))}
    assert palette_problems(sixteen, palette, room_palettes, 16) == []

    twenty = {"id": "synthetic", "room_palette": "wide", "palette_indices": list(range(20))}
    problems = palette_problems(twenty, palette, room_palettes, 16)
    assert problems and any("screen cap" in line for line in problems), problems


# --------------------------------------------------------------------------- 3. the grid


def test_the_deck_is_20_by_15_and_every_grid_row_says_so(deck):
    """The cross row rule a schema cannot express, and the count the S5 verifier measured."""
    width, height = deck["width"], deck["height"]
    assert (width, height) == DECK_SIZE, (width, height)
    for name in ("tiles", "collision"):
        grid = deck[name]
        assert len(grid) == height, "%s has %d rows, the row declares %d" % (name, len(grid), height)
        for index, line in enumerate(grid):
            assert len(line) == width, "%s[%d] is %d characters, the row declares %d" % (
                name, index, len(line), width)
    for index, line in enumerate(deck["collision"]):
        assert set(line) <= set("012"), "collision[%d] uses a character that is not 0, 1 or 2" % index


def test_every_tile_character_of_the_deck_is_a_key_of_its_own_legend(deck):
    problems = legend_problems(deck)
    assert problems == [], problems
    assert set(deck["tile_legend"]) == set(LEGEND_COLLISION), (
        "the deck's legend names %s, the card's character rules name %s"
        % (sorted(deck["tile_legend"]), sorted(LEGEND_COLLISION)))


def test_every_deck_cell_collides_the_way_its_character_says(deck):
    """# C P blocked; . G H D walkable; except the story blocked hatch at 18,7."""
    problems = collision_problems(deck)
    assert problems == [], problems
    assert deck["story_flag"] == STORY_FLAG, (
        "the deck names story_flag %r; the 2 tile only opens for a named flag" % deck.get("story_flag"))


def test_the_story_blocked_hatch_is_the_one_tile_the_flag_opens(deck, cabin):
    """18,7 is a 2 tile behind a door drawn as a door, and the door leads onto a walkable cabin tile."""
    assert cell_char(deck, *PINNED_STORY_TILE) == "2", (
        "the hatch at %s collides %r, the card pins it as story blocked"
        % (PINNED_STORY_TILE, cell_char(deck, *PINNED_STORY_TILE)))
    assert tile_char(deck, *PINNED_STORY_TILE) == "D", (
        "the hatch at %s is drawn %r, not as a door" % (PINNED_STORY_TILE, tile_char(deck, *PINNED_STORY_TILE)))

    hatch = trigger_at(deck, *PINNED_STORY_TILE, "map")
    assert len(hatch) == 1, (
        "the hatch at %s carries %d map triggers, expected 1" % (PINNED_STORY_TILE, len(hatch)))
    door = hatch[0]
    assert door["condition"] == STORY_FLAG, (
        "the cabin door at %s is gated on %r, the story flag is %r"
        % (PINNED_STORY_TILE, door.get("condition"), STORY_FLAG))
    assert door["id"] == CABIN, "the hatch at %s leads to %r, not %r" % (PINNED_STORY_TILE, door["id"], CABIN)

    landing = cabin["spawns"].get(door.get("spawn"))
    assert landing is not None, "the cabin has no spawn %r to land on" % door.get("spawn")
    assert is_walkable(cabin, landing["x"], landing["y"]), (
        "the hatch lands the hero on %r of the cabin at (%d,%d), which is not walkable"
        % (door.get("spawn"), landing["x"], landing["y"]))


# --------------------------------------------------------------------------- 4. the pinned tiles


def test_the_two_pinned_tiles_are_still_the_two_the_other_suites_read(deck):
    """18,7 story blocked and 5,3 blocked are read by the save and fight suites, so they are pinned here."""
    assert cell_char(deck, *PINNED_STORY_TILE) == "2", cell_char(deck, *PINNED_STORY_TILE)
    assert cell_char(deck, *PINNED_BLOCKED_TILE) == "1", (
        "the pinned blocked tile %s collides %r, other suites read it as blocked"
        % (PINNED_BLOCKED_TILE, cell_char(deck, *PINNED_BLOCKED_TILE)))


def test_the_first_fight_sits_two_tiles_east_of_the_spawn_with_a_clear_line(deck):
    """The hand off the boarding scene ends on: the trigger is one step ahead, and the line is open."""
    spawn = deck["spawns"]["start"]
    battles = triggers_of(deck, "battle")
    assert len(battles) == 1, "the deck carries %d battle triggers, the first fight is one" % len(battles)
    fight = battles[0]

    assert fight["y"] == spawn["y"], (
        "the fight at (%d,%d) is not on the spawn's row %d" % (fight["x"], fight["y"], spawn["y"]))
    offset = fight["x"] - spawn["x"]
    assert offset == FIGHT_TRIGGER_OFFSET, (
        "the fight is %d tiles east of the spawn, the card pins %d" % (offset, FIGHT_TRIGGER_OFFSET))
    between = [(spawn["x"] + step, spawn["y"]) for step in range(1, offset)]
    blocked = [(tile, cell_char(deck, *tile)) for tile in between if not is_walkable(deck, *tile)]
    assert blocked == [], "the tiles between the spawn and the fight are blocked: %s" % blocked


def test_every_spawn_and_the_save_point_are_walkable(deck):
    assert set(deck["spawns"]) == {"start", "after_percy", "from_cabin", "from_hatch"}, sorted(deck["spawns"])
    problems = []
    for name, point in sorted(deck["spawns"].items()):
        if not is_walkable(deck, point["x"], point["y"]):
            problems.append("spawn %r at (%d,%d) collides %r"
                            % (name, point["x"], point["y"], cell_char(deck, point["x"], point["y"])))
    assert problems == [], problems

    save = [trigger for trigger in triggers_of(deck, "save") if trigger["id"] == SAVE_ID]
    assert len(save) == 1, "the deck carries %d %r triggers, expected 1" % (len(save), SAVE_ID)
    assert (save[0]["x"], save[0]["y"]) == SAVE_TILE, (
        "the save point stands at (%d,%d), the card pins %s" % (save[0]["x"], save[0]["y"], SAVE_TILE))
    assert is_walkable(deck, *SAVE_TILE), (
        "the save point at %s collides %r, a save has to be standable" % (SAVE_TILE, cell_char(deck, *SAVE_TILE)))


def test_the_deck_carries_the_seven_triggers_the_beats_ride_on(deck):
    """Seven triggers, each one where a hero can reach it: on a walkable tile, or a door to face."""
    triggers = triggers_of(deck)
    assert len(triggers) == DECK_TRIGGERS, (
        "the deck carries %d triggers, the S5 measurement is %d" % (len(triggers), DECK_TRIGGERS))
    problems = []
    for trigger in triggers:
        tile = (trigger["x"], trigger["y"])
        if is_walkable(deck, *tile, gate_open=True):
            continue
        facing = [(tile[0] + dx, tile[1] + dy) for dx, dy in DIRECTIONS
                  if is_walkable(deck, tile[0] + dx, tile[1] + dy, gate_open=True)]
        if not facing:
            problems.append("trigger %r at %s can be neither stood on nor faced from any open tile"
                            % (trigger["id"], tile))
    assert problems == [], problems
    assert {(trigger["kind"], trigger["id"]) for trigger in triggers} == {
        ("save", SAVE_ID), ("battle", "tutorial_sailors"), ("flag", "ship_deck_seen"),
        ("scene", LOG_SCENE), ("map", CABIN), ("map", "ship_sample"),
        ("map", "southampton_town_quay"),
    }, sorted((trigger["kind"], trigger["id"]) for trigger in triggers)


# --------------------------------------------------------------------------- 5. reachability


def test_every_walkable_tile_of_the_deck_is_reachable_from_the_spawn(deck):
    """176 of 176 at 103e628, and opening the flag adds exactly the one hatch tile."""
    start = deck["spawns"]["start"]
    origin = (start["x"], start["y"])
    walkable = walkable_tiles(deck)
    assert len(walkable) == DECK_WALKABLE, (
        "the deck has %d walkable tiles with the hatch shut, the S5 measurement is %d"
        % (len(walkable), DECK_WALKABLE))

    reachable, served = flood_fill(deck, origin, gate_open=False)
    assert served == len(reachable), "%d tiles were served for %d visited" % (served, len(reachable))
    stranded = sorted(tile for tile in walkable if tile not in reachable)
    assert stranded == [], (
        "%d of %d walkable tiles cannot be walked to from %s: %s"
        % (len(stranded), len(walkable), origin, stranded[:12]))
    assert len(reachable) == DECK_WALKABLE, "%d of %d reachable" % (len(reachable), DECK_WALKABLE)

    opened, _served = flood_fill(deck, origin, gate_open=True)
    assert opened - reachable == {PINNED_STORY_TILE}, (
        "opening %r adds %s, the only story blocked tile is %s"
        % (STORY_FLAG, sorted(opened - reachable), PINNED_STORY_TILE))
    assert reachable <= opened, "opening the hatch closed tiles that were reachable before it"


def test_the_flood_fill_is_iterative_and_walks_each_tile_once():
    """The bound the arrival map's fill carries, kept here too: no recursion, one pass per tile."""
    size = 250
    grid = {"id": "synthetic", "width": size, "height": size,
            "collision": ["0" * size for _ in range(size)], "tiles": [], "tile_legend": {}}
    seen, served = flood_fill(grid, (0, 0), gate_open=False)
    assert len(seen) == size * size, "the fill reached %d of %d open tiles" % (len(seen), size * size)
    assert served == len(seen), "%d tiles were served for %d visited" % (served, len(seen))

    walled = {"id": "synthetic_wall", "width": size, "height": size,
              "collision": ["1" * size for _ in range(size)], "tiles": [], "tile_legend": {}}
    assert flood_fill(walled, (0, 0), gate_open=False) == (set(), 0)


# --------------------------------------------------------------------------- 6. the scenes


def test_the_runner_command_list_and_the_checker_agree():
    """Two files state the command list; if they drift, a scene the runner skips passes the checker."""
    import check_data

    implemented = runner_commands(_read(SCENE_GML))
    assert len(implemented) == RUNNER_COMMANDS, (
        "pp_scene_commands() lists %d commands, the card pins %d (%s)"
        % (len(implemented), RUNNER_COMMANDS, implemented))
    assert len(set(implemented)) == len(implemented), "pp_scene_commands() repeats a command: %s" % implemented
    assert set(implemented) == set(check_data.SCENE_COMMANDS), (
        "pp_scene runs %s, tools/check_data.py allows %s"
        % (sorted(set(implemented)), sorted(check_data.SCENE_COMMANDS)))
    assert "end" in implemented, "a scene cannot end"


def test_both_ship_scenes_use_only_commands_the_runner_implements(scenes):
    """The boarding and log scenes, every command checked against the runner's own list."""
    implemented = runner_commands(_read(SCENE_GML))
    ship = [scenes[LOG_SCENE], scenes[BOARDING_SCENE]]
    for scene in ship:
        assert scene["map"] == DECK, "scene %r runs on map %r, not on the deck" % (scene["id"], scene["map"])
    problems = unknown_command_problems(ship, implemented)
    assert problems == [], problems
    assert len(scenes[BOARDING_SCENE]["commands"]) == 11, (
        "the boarding scene authors %d commands" % len(scenes[BOARDING_SCENE]["commands"]))
    # The log scene gained the one `say ship_log_open` that reads the ship's log before the jingle (card t_4c7368fb),
    # so the S5 measurement of 8 is 9 now: the two pages of words are the beat's, and the move commands are unchanged.
    assert len(scenes[LOG_SCENE]["commands"]) == 9, (
        "the log scene authors %d commands" % len(scenes[LOG_SCENE]["commands"]))


def test_both_ship_scenes_end_on_end(scenes):
    problems = unpinned_command_problems([scenes[LOG_SCENE], scenes[BOARDING_SCENE]], runner_commands(_read(SCENE_GML)))
    assert problems == [], problems


def test_a_command_the_runner_has_no_case_for_is_refused(scenes):
    """Row 6's own failing case: a scene that says something the runner never implements."""
    implemented = runner_commands(_read(SCENE_GML))
    assert unknown_command_problems([scenes[LOG_SCENE]], implemented) == []

    broken = _copy(scenes[LOG_SCENE])
    broken["commands"].insert(1, {"cmd": "teleport", "to": "cabin"})
    problems = unknown_command_problems([broken], implemented)
    assert problems, "a command pp_scene has no case for passed the scene check"
    assert any("teleport" in line and LOG_SCENE in line for line in problems), problems


# --------------------------------------------------------------------------- 7. the log save


def test_the_log_scene_walks_the_hero_onto_the_save_tile(deck, scenes):
    """3,7 up five tiles to 3,2, where deck_save stands: the card's reaches a save command."""
    vectors = direction_vectors(_read(OVERWORLD_GML))
    scene = scenes[LOG_SCENE]
    assert (scene["start"]["x"], scene["start"]["y"]) == LOG_START, (
        "the log scene starts at (%d,%d), not at %s"
        % (scene["start"]["x"], scene["start"]["y"], LOG_START))

    path, problems = walk_hero(scene, deck, vectors)
    assert problems == [], problems
    assert path == LOG_PATH, "the log walk is %s, the card pins it to %s" % (path, LOG_PATH)

    save = trigger_at(deck, *path[-1], "save")
    assert [trigger["id"] for trigger in save] == [SAVE_ID], (
        "the walk ends at %s, which carries %s, not %r"
        % (path[-1], [(trigger["kind"], trigger["id"]) for trigger in trigger_at(deck, *path[-1])], SAVE_ID))
    assert save_problems(scene, deck, vectors) == [], save_problems(scene, deck, vectors)


def test_a_log_move_one_tile_too_far_is_refused(deck, scenes):
    """The card's second mutation: the log move becomes 6, and the walk no longer reaches the save.

    On the shipped grid a 6 tile move ends at 3,1, the back floor of the watch cabin, which is legal
    ground with no save on it, so the refusal is the missing trigger and not a wall. The bulkhead
    stands at 3,0, and the 7 tile case below is the one pp_world_start_move refuses outright.
    """
    vectors = direction_vectors(_read(OVERWORLD_GML))
    scene = scenes[LOG_SCENE]

    too_far = _copy(scene)
    move = [command for command in too_far["commands"] if command["cmd"] == "move"]
    assert len(move) == 1, "the log scene authors %d move commands, the card simulates one" % len(move)
    move[0]["tiles"] = move[0]["tiles"] + 1

    path, problems = walk_hero(too_far, deck, vectors)
    assert path[-1] == (3, 1), "the 6 tile walk ends at %s, expected (3, 1)" % (path[-1],)
    assert problems == [], (
        "a 6 tile move up from %s is legal ground on this grid, so it is not refused for a wall: %s"
        % (LOG_START, problems))
    refused = save_problems(too_far, deck, vectors)
    assert refused, "a walk that ends one tile past the save passed the reaches a save check"
    assert any("(3, 1)" in line and LOG_SCENE in line for line in refused), refused

    into_wall = _copy(scene)
    move = [command for command in into_wall["commands"] if command["cmd"] == "move"]
    move[0]["tiles"] = 7
    _path, walled = walk_hero(into_wall, deck, vectors)
    assert walled, "a 7 tile move up from %s walked into the bulkhead at (3, 0) unrefused" % (LOG_START,)
    assert any("(3, 0)" in line for line in walled), walled


def test_a_deleted_save_trigger_is_refused(deck, scenes):
    """The card's third mutation: take deck_save off the deck and the walk of the log reaches nothing."""
    vectors = direction_vectors(_read(OVERWORLD_GML))
    scene = scenes[LOG_SCENE]
    assert save_problems(scene, deck, vectors) == []

    broken = _copy(deck)
    broken["triggers"] = [trigger for trigger in broken["triggers"] if trigger["id"] != SAVE_ID]
    assert [trigger for trigger in triggers_of(broken, "save")] == [], "the copy still carries a save trigger"

    problems = save_problems(scene, broken, vectors)
    assert problems, "a deck with no deck_save trigger passed the reaches a save check"
    assert any("no save trigger" in line for line in problems), problems


# --------------------------------------------------------------------------- the slice's own save step


def test_the_slice_save_step_names_the_deck_save_on_a_walkable_tile(deck, scenes):
    """The save point moved from 2,5 to 3,2, so the slice's step is pinned by tile here as well."""
    vectors = direction_vectors(_read(OVERWORLD_GML))
    slice_doc = _load(SLICE_PATH)
    steps = {step["id"]: step for step in slice_doc["route"]["steps"]}
    assert "save" in steps, "data/slice.json has no save step"
    save_step = steps["save"]
    assert save_step.get("kind") == "save", "the slice's save step is kind %r" % save_step.get("kind")
    assert save_step.get("trigger") == SAVE_ID, (
        "the slice's save step names %r, not %r" % (save_step.get("trigger"), SAVE_ID))

    named = [trigger for trigger in triggers_of(deck) if trigger["id"] == save_step["trigger"]]
    assert len(named) == 1, "the deck carries %d triggers named %r" % (len(named), save_step["trigger"])
    assert (named[0]["x"], named[0]["y"]) == SAVE_TILE, (
        "the slice's save trigger stands at (%d,%d), the card pins %s"
        % (named[0]["x"], named[0]["y"], SAVE_TILE))
    assert is_walkable(deck, *SAVE_TILE), "the save trigger the slice names stands on a blocked tile"

    path, _problems = walk_hero(scenes[LOG_SCENE], deck, vectors)
    assert path[-1] == SAVE_TILE, (
        "the log walk ends at %s, the slice's save step is at %s" % (path[-1], SAVE_TILE))
