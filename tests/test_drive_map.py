"""The drive corridor map row and the palette set it draws in (card t_e8a8f18a).

Why a test and not a look at a screen: the row exists so that a scene can name a map, and every way it can be
wrong is silent. A corridor one tile narrower than the film's last camera target fails only when somebody
watches shot 8. A camera row that is not the row the scene's own commands name shows a band of hedge where the
road should be, and nothing refuses it. A tile character the map uses but the legend does not name is caught by
the checker, but a legend that names a different tile than the sheet's own character column is not. A room
palette that does not declare a role the sheet's tiles spend draws PP_COLOUR_MISSING in that tile, which is a
logged line and not an error. And a row the generator no longer writes drifts the first time the sheet is
redrawn, because nobody reruns a paste by hand.

So everything here is pinned to a file that already owns the fact:

    data/maps/all.json                    the row this card writes
    data/scenes/all.json                  drive_to_southampton: its map, its start, its 15 camera targets
    assets/tiles/drive/drive_tiles.json   the sheet's characters, indices, palette groups and role names
    data/tile_classes_drive.json          the walkable classification the collision grid is built from
    data/room_palettes.json               the drive_night set this card lands
    data/palette.json                     the master roles and their indices
    game/scripts/pp_config/pp_config.gml  PP_FRAME_W, PP_FRAME_H, PP_CAMERA_MOVE_STEPS, PP_FADE_STEPS
    knowledge/DRIVE-SHOT-LIST.md          the film's 10,680 steps (section 8), which the scene row has to sum to,
                                          and the eleven cut steps (section 1) this test cuts the scene at
    game/scripts/pp_drive/pp_drive.gml    pp_drive_shots(), the room's capture table, which must stay the scene's
                                          twelve durations (decision D19: the room is capture only)
    tools/art/make_drive_map.py           the generator, run with --check so the tree cannot drift from it

No test here reads the network, writes a tracked file, or needs GameMaker.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAP_ID = "drive_m4_corridor"
SCENE_ID = "drive_to_southampton"
SET_ID = "drive_night"
SHEET = "drive_tiles"
SCREEN_CAP = 16

# knowledge/DRIVE-SHOT-LIST.md section 8: the film is 178.00 s at 60 steps a second.
FILM_STEPS = 10680

# The shot list's L3 windows through `offset = round(camera_x * 0.15) mod 512` (LAYERS, in
# tools/art/make_title_world.py) resolve to these camera tile x values, and shot 8 is the furthest one.
FURTHEST_CAMERA_TILE = 141


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8-sig") as handle:
        return handle.read()


def read_json(rel: str):
    return json.loads(read(rel))


def config_macro(name: str) -> int:
    match = re.search(r"#macro\s+%s\s+(\d+)" % name, read(os.path.join("game", "scripts", "pp_config",
                                                                       "pp_config.gml")))
    assert match, "pp_config defines no %s" % name
    return int(match.group(1))


def maps() -> dict:
    return read_json(os.path.join("data", "maps", "all.json"))


def drive_map() -> dict:
    rows = maps()["maps"]
    row = next((entry for entry in rows if entry.get("id") == MAP_ID), None)
    assert row is not None, "data/maps/all.json holds no map %r" % MAP_ID
    return row


def scene() -> dict:
    rows = read_json(os.path.join("data", "scenes", "all.json"))["scenes"]
    row = next((entry for entry in rows if entry.get("id") == SCENE_ID), None)
    assert row is not None, "data/scenes/all.json holds no scene %r" % SCENE_ID
    return row


def sheet() -> dict:
    return read_json(os.path.join("assets", "tiles", "drive", "drive_tiles.json"))


def classes() -> dict:
    return read_json(os.path.join("data", "tile_classes_drive.json"))


def room_sets() -> dict:
    return read_json(os.path.join("data", "room_palettes.json"))


def master_roles() -> dict:
    return read_json(os.path.join("data", "palette.json"))["roles"]


def frame_tiles() -> int:
    return config_macro("PP_FRAME_W") // 16


def camera_targets() -> list:
    out = []
    for command in scene()["commands"]:
        if command.get("cmd") == "camera" and "x" in command:
            out.append((command["x"], command["y"]))
    return out


# ---------------------------------------------------------------------------------------------------------------
# 1. The row, and the two numbers the scene forces on it: a width every camera fits in and the row it pans along.

def test_the_row_is_in_the_tree_and_names_the_drive_sheet():
    row = drive_map()
    assert row["tileset"] == SHEET, "the row names %r, not the drive sheet" % row.get("tileset")
    assert row["width"] == len(row["tiles"][0]), "the width and the row length disagree"
    assert row["height"] == len(row["tiles"]) == len(row["collision"]), "height and grid rows disagree"


def windows_outside(row: dict) -> list:
    """The camera targets whose 16 tile frame would hang off the right edge of this row's map.

    One function, so the width test and its planted control below judge the same predicate instead of two
    spellings of it that could disagree.
    """
    return [(x, y) for x, y in camera_targets() if x + frame_tiles() > row["width"]]


def test_the_map_is_wide_enough_for_the_furthest_camera_the_shot_list_asks_for():
    row = drive_map()
    assert row["width"] >= FURTHEST_CAMERA_TILE + frame_tiles(), \
        "a %d tile map cannot show camera tile %d and a %d tile frame" % (row["width"], FURTHEST_CAMERA_TILE,
                                                                          frame_tiles())
    over = windows_outside(row)
    assert over == [], "camera targets outside the map: %r" % over


def test_the_scene_pans_along_one_row_and_that_row_is_the_road():
    row = drive_map()
    road_rows = {y for _x, y in camera_targets()}
    assert len(road_rows) == 1, "the film pans along %d rows, so the map's own row is ambiguous" % len(road_rows)
    road_row = road_rows.pop()
    assert scene()["start"]["y"] == road_row, "the scene starts on row %d and pans along row %d" % (
        scene()["start"]["y"], road_row)
    line = row["tiles"][road_row]
    assert len(set(line)) == 1 or set(line) <= {"c", "h"}, \
        "the road row is %r, which is not one corridor surface" % sorted(set(line))
    tile_of = {tile["character"]: tile["name"] for tile in sheet()["tiles"]}
    names = {tile_of[char] for char in line}
    assert names <= {"road_lane_dash", "road_single_lane"}, \
        "the scene's own row draws %r, not a lane" % sorted(names)
    assert set(row["collision"][road_row]) == {"0"}, "the road row is not walkable end to end"


def test_the_camera_row_is_not_clamped_by_the_map_height():
    row = drive_map()
    road_row = camera_targets()[0][1]
    frame = config_macro("PP_FRAME_H")
    slack = row["height"] * 16 - frame - road_row * 16
    assert slack >= 0, "the camera row sits %d px past the tallest row the map can show" % -slack


def test_the_start_and_every_spawn_sit_on_walkable_tiles():
    row = drive_map()
    assert row["spawns"], "the row carries no spawn, so the scene has nowhere to start"
    for name, point in row["spawns"].items():
        assert row["collision"][point["y"]][point["x"]] == "0", "spawn %r is not walkable" % name
    assert row["collision"][scene()["start"]["y"]][scene()["start"]["x"]] == "0", \
        "the scene starts on a blocked tile"


# ---------------------------------------------------------------------------------------------------------------
# 2. The art: every character is the sheet's own character for that tile, and the collision grid is the class file.

def test_every_character_the_map_uses_is_in_the_legend_and_names_a_sheet_tile():
    row = drive_map()
    legend = row["tile_legend"]
    used = {char for line in row["tiles"] for char in line}
    assert used <= set(legend), "characters outside the legend: %s" % sorted(used - set(legend))
    char_of = {tile["name"]: tile["character"] for tile in sheet()["tiles"]}
    name_of = {char_of[name]: name for name in char_of}
    for char in used:
        assert legend[char] == name_of.get(char), \
            "legend %r says %r, the sheet says %r" % (char, legend[char], name_of.get(char))


def test_every_legend_entry_is_a_tile_that_exists_in_the_sheet():
    count = sheet()["tilecount"]
    names = {tile["name"]: tile["index"] for tile in sheet()["tiles"]}
    bad = [entry for entry in drive_map()["tile_legend"].values() if entry not in names]
    assert bad == [], "the legend names %r, which the sheet does not carry" % bad
    over = [name for name in drive_map()["tile_legend"].values() if not 0 <= names[name] < count]
    assert over == [], "legend entries past the sheet's %d tiles: %r" % (count, over)


def test_the_collision_grid_is_the_class_files_verdict_and_nothing_else():
    row = drive_map()
    walkable = {tile["name"]: bool(tile["walkable"]) for tile in classes()["tiles"]}
    name_at = drive_map()["tile_legend"]
    expected = []
    for line in row["tiles"]:
        expected.append("".join("0" if walkable[name_at[char]] else "1" for char in line))
    assert row["collision"] == expected, "the collision grid and data/tile_classes_drive.json disagree"
    assert not any("2" in line for line in row["collision"]), \
        "the row uses the story blocked value but names no story flag"


def test_the_walkable_cells_are_one_region_from_the_start():
    row = drive_map()
    width, height = row["width"], row["height"]
    grid = row["collision"]
    start = (row["spawns"]["start"]["x"], row["spawns"]["start"]["y"])
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            point = (x + dx, y + dy)
            if (0 <= point[0] < width and 0 <= point[1] < height
                    and grid[point[1]][point[0]] == "0" and point not in seen):
                seen.add(point)
                queue.append(point)
    walkable = {(x, y) for y in range(height) for x in range(width) if grid[y][x] == "0"}
    assert walkable - seen == set(), "%d walkable tiles are cut off from the start, so the map is two rooms " \
                                     "with no way between them" % len(walkable - seen)


# ---------------------------------------------------------------------------------------------------------------
# 3. The palette: the set the row names declares every role the tiles it places spend, and fits the screen cap.

def spent_roles(row: dict) -> set:
    """The palette.json roles the tiles this map places actually spend, read from the sheet's own groups."""
    manifest = sheet()
    group_of = {tile["name"]: tile["palette"] for tile in manifest["tiles"]}
    groups = {group["name"]: group["roles"] for group in manifest["palettes"]}
    role_of = {name: entry["role"] for name, entry in manifest["roles"].items()}
    spent = set()
    for name in row["tile_legend"].values():
        for sheet_role in groups[group_of[name]]:
            spent.add(role_of[sheet_role])
    return spent


def test_the_set_the_row_names_exists_and_declares_every_role_its_tiles_spend():
    row = drive_map()
    sets = {entry["id"]: entry["roles"] for entry in room_sets()["sets"]}
    assert row["room_palette"] == SET_ID
    assert SET_ID in sets, "data/room_palettes.json holds no set %r" % SET_ID
    declared = set(sets[SET_ID])
    assert spent_roles(row) <= declared, "the map spends %s, which drive_night does not declare" % sorted(
        spent_roles(row) - declared)
    assert {"ink", "paper", "dim", "text"} <= declared, \
        "a room that clears or prints before its own art loads needs the four drawing roles"


def test_the_set_leaves_room_for_the_missing_colour():
    roles = master_roles()
    for entry in room_sets()["sets"]:
        colours = {roles[name] for name in entry["roles"] if name in roles}
        assert len(colours) + 1 <= SCREEN_CAP, \
            "set %r spends %d distinct colours, and a role outside it adds the missing colour" % (entry["id"],
                                                                                                len(colours))


def test_the_rows_own_colour_list_is_the_sets_colours():
    row = drive_map()
    roles = master_roles()
    declared = next(entry["roles"] for entry in room_sets()["sets"] if entry["id"] == SET_ID)
    expected = sorted({roles[name] for name in declared})
    assert row["palette_indices"] == expected, \
        "the row lists %r, the set's own colours are %r" % (row["palette_indices"], expected)


# ---------------------------------------------------------------------------------------------------------------
# 4. The scene that needed the row: it names this map, and its commands still sum to the film's stated length.

def test_the_scene_names_this_map_and_starts_on_the_road():
    row = scene()
    assert row["map"] == MAP_ID, "the scene names %r, so the map row this card writes is still unused" % row["map"]
    assert row["start"] == drive_map()["spawns"]["start"], \
        "the scene starts at %r and the map's start spawn is %r" % (row["start"], drive_map()["spawns"]["start"])


def test_the_scene_still_sums_to_the_shot_lists_ten_thousand_steps():
    fade = config_macro("PP_FADE_STEPS")
    camera = config_macro("PP_CAMERA_MOVE_STEPS")
    total = 0
    for command in scene()["commands"]:
        kind = command.get("cmd")
        if kind == "wait":
            total += command["steps"]
        elif kind == "fade":
            total += fade
        elif kind == "camera":
            total += camera
    assert total == FILM_STEPS, "the scene spends %d steps, the shot list states %d" % (total, FILM_STEPS)
    assert scene()["commands"][-1]["cmd"] == "end", "the scene does not end on the end command"


def test_shot_ten_flashes_on_the_thunder_and_costs_the_film_no_steps():
    """Card t_531bc76c. Shot 10 is the storm: the thunder and the light have to be the same beat, and the light has
    to be free. A flash that were priced as a wait would move the twelve durations, the eleven cuts and the cue."""
    commands = scene()["commands"]
    thunder = [index for index, command in enumerate(commands)
               if command.get("cmd") == "sfx" and command.get("id") == "thunder_soft"]
    assert len(thunder) == 1, "the drive names thunder_soft %d times, the shot list once" % len(thunder)
    after = commands[thunder[0] + 1]
    assert after.get("cmd") == "flash", \
        "the command after the thunder is %r, so the picture and the sound disagree on the loudest beat" % (after,)

    # The two frame clock is the title's own, read from the file the title drives its storm with, not retyped here.
    title_frames = read_json("data/title_flash.json")["frames"]
    assert after.get("steps") == title_frames, \
        "the flash asks for %r frames, the title's storm clock is %d" % (after.get("steps"), title_frames)

    # A flash costs zero steps: it is a palette change over steps the film already spends, so the total does not move.
    costs = scene_step_costs()
    assert costs[thunder[0] + 1] == 0, "the flash is priced at %d steps, so the cut grid moves" % costs[thunder[0] + 1]
    assert sum(costs) == FILM_STEPS, "the film now spends %d steps, the shot list states %d" % (sum(costs), FILM_STEPS)

    # And every other exact zero cost command in the drive is one the runner advances in the same step it runs.
    free = {"say", "sfx", "music", "setflag", "face", "flash", "end"}
    for index, command in enumerate(commands):
        if command["cmd"] not in free:
            assert costs[index] > 0, "%s at %d is priced at zero steps and is not a free command" % (
                command["cmd"], index)


# ---------------------------------------------------------------------------------------------------------------
# 4b. The twelve durations exist twice, in the room's GML table and in the scene's command list. Decision D19
# (knowledge/GAMEDEV-DECISIONS-2026-10-24.md) keeps the room as a capture rig, so the copy is allowed to exist but
# not to drift: this test cuts the scene at the shot list's own eleven cut steps and requires every window's steps
# and its say ids to be the room's row. Nothing here is read from the room's table to place a cut, or it would agree
# with itself.

def room_shots() -> list:
    text = read(os.path.join("game", "scripts", "pp_drive", "pp_drive.gml"))
    rows = []
    pattern = (r'\{\s*n:\s*(\d+),\s*id:\s*"([^"]*)",\s*place:\s*"([^"]*)",\s*steps:\s*(\d+),'
               r'\s*sign:\s*"([^"]*)",\s*pages:\s*\[([^\]]*)\]')
    for match in re.finditer(pattern, text):
        rows.append({"n": int(match.group(1)), "id": match.group(2), "place": match.group(3),
                     "steps": int(match.group(4)), "sign": match.group(5),
                     "pages": re.findall(r'"([^"]+)"', match.group(6))})
    return rows


def shot_list_cuts() -> tuple:
    """Section 1's eleven hard cuts, in steps and in the cue bars they are written on."""
    text = read(os.path.join("knowledge", "DRIVE-SHOT-LIST.md"))
    match = re.search(r"are at steps (.*?)which are bars (.*?)of the cue", text, re.S)
    assert match, "knowledge/DRIVE-SHOT-LIST.md section 1 no longer names the eleven cut steps"
    steps = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", match.group(1))]
    bars = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", match.group(2))]
    return steps, bars


def scene_step_costs() -> list:
    fade = config_macro("PP_FADE_STEPS")
    camera = config_macro("PP_CAMERA_MOVE_STEPS")
    costs = []
    for command in scene()["commands"]:
        kind = command.get("cmd")
        costs.append(command["steps"] if kind == "wait" else
                     fade if kind == "fade" else
                     camera if kind == "camera" else 0)
    return costs


def test_the_room_table_and_the_scene_are_the_same_twelve_durations():
    rows = room_shots()
    cuts, bars = shot_list_cuts()
    commands = scene()["commands"]
    costs = scene_step_costs()

    assert len(rows) == 12, "pp_drive_shots() carries %d rows" % len(rows)
    assert len(cuts) == 11, "the shot list names %d cuts" % len(cuts)
    assert bars == [8, 18, 25, 34, 46, 59, 69, 79, 92, 105, 113], bars
    assert [row["n"] for row in rows] == list(range(1, 13))

    # 1. every cut is a command boundary of the scene, so a shot cannot end halfway through a wait
    boundary_at = {}
    running = 0
    for index, cost in enumerate(costs):
        running += cost
        boundary_at[running] = index + 1
    for step in cuts:
        assert step in boundary_at, "cut at step %d falls inside a command, so the scene is on another lattice" % step

    bounds = [0] + [boundary_at[step] for step in cuts] + [len(commands)]
    windows = [commands[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    assert len(windows) == 12

    # 2. each window is the room's duration, and its captions are the room's pages in the same order
    opening = 0
    for index, window in enumerate(windows):
        close = cuts[index] if index < len(cuts) else FILM_STEPS
        spent = sum(costs[bounds[index]:bounds[index + 1]])
        assert spent == close - opening, \
            "shot %d spends %d steps, section 1 makes it %d" % (index + 1, spent, close - opening)
        assert rows[index]["steps"] == spent, \
            "pp_drive_shots() shot %d says %d steps, the scene spends %d" % (index + 1, rows[index]["steps"], spent)
        said = [command["id"] for command in window if command.get("cmd") == "say"]
        assert said == rows[index]["pages"], \
            "shot %d says %r, the room's row says %r" % (index + 1, said, rows[index]["pages"])
        if rows[index]["sign"]:
            assert "drive_sign_%s" % rows[index]["sign"] in said, \
                "shot %d is the sign %s and does not say it" % (index + 1, rows[index]["sign"])
        opening = close

    # 3. the eight places the shot list counts, and the total both copies agree on
    assert len({row["place"] for row in rows}) == 8, sorted({row["place"] for row in rows})
    assert sum(row["steps"] for row in rows) == FILM_STEPS
    assert opening == FILM_STEPS


# ---------------------------------------------------------------------------------------------------------------
# 5. The generator: the tree carries what it writes today, and it refuses a tree that lost the row.

def run_tool(root: str, *flags: str) -> subprocess.CompletedProcess:
    # stdin is given explicitly because this spawn must not inherit the parent's handles: when the suite runs with
    # its stdout redirected to a log, the inherited stdin handle can already be dead and _make_inheritable raises
    # OSError [WinError 6] before the child exists. 65 other call sites in this repo already pass it.
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "art", "make_drive_map.py"),
                           "--root", root] + list(flags),
                          stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_the_tree_carries_what_the_generator_writes():
    done = run_tool(ROOT, "--check")
    assert done.returncode == 0, "make_drive_map --check is stale:\n%s\n%s" % (done.stdout, done.stderr)


def test_a_tree_without_the_row_is_refused_and_a_write_restores_it(tmp_path):
    # The minimal tree the tool reads: the sheet, the class file, the master palette, the sets and the maps.
    for rel in (os.path.join("assets", "tiles", "drive", "drive_tiles.json"),
                os.path.join("data", "tile_classes_drive.json"),
                os.path.join("data", "palette.json"),
                os.path.join("data", "room_palettes.json"),
                os.path.join("data", "maps", "all.json")):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(os.path.join(ROOT, rel), "r", encoding="utf-8-sig") as handle:
            target.write_text(handle.read(), encoding="utf-8")

    assert run_tool(str(tmp_path), "--check").returncode == 0, "a copy of the tree reads as stale"

    maps_path = tmp_path / "data" / "maps" / "all.json"
    document = json.loads(maps_path.read_text(encoding="utf-8"))
    document["maps"] = [row for row in document["maps"] if row["id"] != MAP_ID]
    maps_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    lost = run_tool(str(tmp_path), "--check")
    assert lost.returncode == 1, "the tool passes a tree with no drive row:\n%s" % lost.stdout

    wrote = run_tool(str(tmp_path), "--write")
    assert wrote.returncode == 0, "the tool could not write the row back:\n%s\n%s" % (wrote.stdout, wrote.stderr)
    restored = json.loads(maps_path.read_text(encoding="utf-8"))
    assert [row for row in restored["maps"] if row["id"] == MAP_ID] == [drive_map()], \
        "the row the tool writes is not the row in the tree"
    assert run_tool(str(tmp_path), "--check").returncode == 0, "the tree is still stale after a write"


def test_the_width_check_bites_on_a_map_one_tile_too_narrow():
    # A planted row one tile under the floor, fed through the same predicate the width test uses. Without this
    # the width test would pass on any row at all, because a wider map is never asked to prove anything.
    row = dict(drive_map())
    row["width"] = FURTHEST_CAMERA_TILE + frame_tiles() - 1
    outside = windows_outside(row)
    assert outside, "a map %d tiles wide accepted every camera target" % row["width"]
    assert (FURTHEST_CAMERA_TILE, 8) in outside, "the planted row did not name the shot 8 target"
