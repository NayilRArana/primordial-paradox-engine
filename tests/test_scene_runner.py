"""Pins for R23, SCENE-RUNNER-HARDEN: any scene plays on any map and hands control back on end.

What these tests hold down, and why each one earns its place:
  1. the runner's command list, the switch that implements it and the committed scene data agree in BOTH directions,
     so a command in the list with no case (a hang) and a case with no entry in the list (an undocumented command)
     are both failures;
  2. every committed scene ends with `end`, so no scene in the slice depends on falling off the end of its list;
  3. every id a scene names exists: dialogue, music cue, encounter, branch target, and its map and start tile load and
     are walkable on that map;
  4. the hero's rail walk through a scene, following `branch` both ways, stays on walkable tiles and reaches `end`,
     which is spec 06 rule 4 checked at the data level where the card can check it;
  5. a branch target is not a cycle, because spec 06 rule 3 says branch is the only control flow and an authoring loop
     can hang the game;
  6. the map/start placement a scene asks for is done without the app fade, because a branch that re-entered a scene
     through pp_overworld_change_map would restart the map fade under the running scene;
  7. `end` hands the walker back on the tile he stopped on: the tile is snapped, the camera follows again, a fade left
     at black is turned around, and the overworld drops the finished runner;
  8. the debug keys exist, are gated by the environment variable, and the self test walks the committed scene list.

Run: python -m pytest tests/test_scene_runner.py -q
"""

from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENE_GML = os.path.join(ROOT, "game", "scripts", "pp_scene", "pp_scene.gml")
GAME_STEP_GML = os.path.join(ROOT, "game", "objects", "obj_pp_game", "Step_0.gml")
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")

# The arguments each command must carry and the ones it may carry. Read from spec 06's command table; a command whose
# required argument is missing is a scene that cannot run, so the data check below refuses it.
COMMAND_ARGS = {
    "say": ({"id"}, set()),
    "move": ({"dir"}, {"actor", "tiles", "dir"}),
    "face": ({"dir"}, {"actor", "dir"}),
    "wait": (set(), {"steps"}),
    "fade": (set(), {"mode", "steps"}),
    "music": ({"id"}, {"id"}),
    "sfx": ({"id"}, {"id"}),
    "camera": (set(), {"x", "y", "actor"}),
    "shake": (set(), {"steps", "strength"}),
    "flash": (set(), {"steps", "role"}),
    "spawn": ({"actor", "x", "y"}, {"actor", "x", "y"}),
    "destroy": ({"actor"}, {"actor"}),
    "battle": ({"id"}, {"id"}),
    "setflag": ({"name"}, {"name", "value"}),
    "branch": ({"flag", "scene"}, {"flag", "scene"}),
    "end": (set(), set()),
}

DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def read_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def gml_function(text: str, name: str) -> str:
    """The body of one GML function, from its declaration to the next top level function or macro."""
    start = text.find("function " + name + "(")
    assert start >= 0, "pp_scene.gml has no function " + name
    nxt = len(text)
    for marker in ("\nfunction ", "\n#macro ", "\n/// "):
        found = text.find(marker, start + 1)
        if found >= 0:
            nxt = min(nxt, found)
    return text[start:nxt]


def runner_commands(text: str) -> list:
    body = gml_function(text, "pp_scene_commands")
    found = re.search(r"return\s*\[(.*?)\];", body, re.S)
    assert found, "pp_scene_commands no longer returns a literal list"
    return re.findall(r'"([a-z_]+)"', found.group(1))


def switch_cases(body: str) -> set:
    return set(re.findall(r'case\s+"([a-z_]+)"\s*:', body))


def scenes() -> list:
    return read_json("data/scenes/all.json")["scenes"]


def maps() -> dict:
    return {row["id"]: row for row in read_json("data/maps/all.json")["maps"]}


def walkable(map_row: dict, tx: int, ty: int) -> bool:
    if tx < 0 or ty < 0 or tx >= map_row["width"] or ty >= map_row["height"]:
        return False
    return map_row["collision"][ty][tx] == "0"


# ---------------------------------------------------------------------------------------------------------------
# 1 and 2: the runner, its switch and the committed scenes agree, and every scene says how it ends.


def test_runner_command_list_and_switch_agree_in_both_directions():
    text = read_text(SCENE_GML)
    commands = runner_commands(text)
    assert commands == [
        "say", "move", "face", "wait", "fade", "music", "sfx", "camera", "shake", "flash",
        "spawn", "destroy", "battle", "setflag", "branch", "end",
    ], "the runner's command list changed; spec 06's table has to change with it"

    start = gml_function(text, "pp_scene_command_start")
    cases = switch_cases(start)
    missing_case = [name for name in commands if name not in cases]
    assert not missing_case, "commands with no case in the runner: %s (a scene using one hangs)" % missing_case
    extra_case = sorted(cases - set(commands))
    assert not extra_case, "cases the runner's own command list does not declare: %s" % extra_case

    for name in commands:
        assert name in COMMAND_ARGS, "the test has no argument table for command " + name


def test_every_committed_scene_is_a_list_that_ends_with_end():
    rows = scenes()
    assert len(rows) >= 5, "the committed scene list lost scenes"
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)), "two scenes share an id"
    commands = runner_commands(read_text(SCENE_GML))
    for row in rows:
        assert row["commands"], "scene %s has no commands" % row["id"]
        assert row["commands"][-1]["cmd"] == "end", "scene %s does not end with end" % row["id"]
        assert len(row["commands"]) <= 256, "scene %s is over the 256 command warning line" % row["id"]
        for index, cmd in enumerate(row["commands"]):
            assert cmd["cmd"] in commands, "scene %s[%d] uses %s, which the runner does not implement" % (
                row["id"], index, cmd["cmd"])
            required, allowed = COMMAND_ARGS[cmd["cmd"]]
            missing = required - set(cmd)
            assert not missing, "scene %s[%d] %s is missing %s" % (row["id"], index, cmd["cmd"], sorted(missing))
            unknown = set(cmd) - {"cmd"} - allowed - required
            assert not unknown, "scene %s[%d] %s carries unknown arguments %s" % (row["id"], index, cmd["cmd"], sorted(unknown))


# ---------------------------------------------------------------------------------------------------------------
# 3: every id a scene names exists, and its map and start tile are real.


def test_every_id_a_scene_names_exists():
    dialogues = {row["id"] for row in read_json("data/dialogue/all.json")["dialogue"]}
    cues = {row["id"] for row in read_json("data/audio.json")["cues"]}
    encounters = {row["id"] for row in read_json("data/encounters/all.json")["encounters"]}
    scene_ids = {row["id"] for row in scenes()}
    flags = set(read_json("data/flags.json")["flags"])

    for row in scenes():
        for index, cmd in enumerate(row["commands"]):
            where = "scene %s[%d] %s" % (row["id"], index, cmd["cmd"])
            if cmd["cmd"] == "say":
                assert cmd["id"] in dialogues, "%s names no dialogue: %s" % (where, cmd["id"])
            if cmd["cmd"] == "music":
                assert cmd["id"] in cues, "%s names no music cue: %s" % (where, cmd["id"])
            if cmd["cmd"] == "battle":
                assert cmd["id"] in encounters, "%s names no encounter: %s" % (where, cmd["id"])
            if cmd["cmd"] == "branch":
                assert cmd["scene"] in scene_ids, "%s branches to no scene: %s" % (where, cmd["scene"])
            if cmd["cmd"] == "setflag":
                assert cmd["name"] in flags, "%s writes a flag data/flags.json does not declare: %s" % (where, cmd["name"])
            if cmd["cmd"] == "move" or cmd["cmd"] == "face":
                assert cmd["dir"] in DIRECTIONS, "%s has no real direction: %s" % (where, cmd["dir"])
            if cmd["cmd"] == "move":
                assert int(cmd.get("tiles", 1)) > 0, "%s moves zero tiles" % where


def test_every_scene_map_loads_and_its_start_tile_is_walkable():
    map_rows = maps()
    for row in scenes():
        assert row.get("map"), "scene %s names no map" % row["id"]
        assert row["map"] in map_rows, "scene %s names a map that is not in data/maps/all.json: %s" % (row["id"], row["map"])
        start = row.get("start")
        assert start, "scene %s names no start tile" % row["id"]
        map_row = map_rows[row["map"]]
        assert walkable(map_row, start["x"], start["y"]), "scene %s starts on a blocked tile %d,%d" % (
            row["id"], start["x"], start["y"])


# ---------------------------------------------------------------------------------------------------------------
# 4: the hero's rail walk through a scene stays walkable and reaches end, with branch followed both ways.


def walk_scene(scene_id: str, take_branches: bool, map_rows: dict, seen: tuple = ()):
    """A data level walk of one scene: the hero's tile through the commands, branch followed or not. Returns the list
    of hero tiles visited. Raises AssertionError naming the command that walks into a wall or loops."""
    assert scene_id not in seen, "branch cycle through %s: %s" % (scene_id, seen + (scene_id,))
    assert len(seen) < 32, "branch chain longer than 32 scenes from %s" % (seen[0],)
    rows = {row["id"]: row for row in scenes()}
    row = rows[scene_id]
    map_row = map_rows[row["map"]]
    tx, ty = row["start"]["x"], row["start"]["y"]
    tiles = [(tx, ty)]

    for index, cmd in enumerate(row["commands"]):
        kind = cmd["cmd"]
        if kind == "end":
            return tiles
        if kind == "branch" and take_branches:
            return tiles + walk_scene(cmd["scene"], take_branches, map_rows, seen + (scene_id,))
        if kind == "move" and cmd.get("actor", "hero") == "hero":
            dx, dy = DIRECTIONS[cmd["dir"]]
            for _ in range(int(cmd.get("tiles", 1))):
                tx += dx
                ty += dy
                assert walkable(map_row, tx, ty), "scene %s[%d] moves the hero onto blocked tile %d,%d" % (
                    scene_id, index, tx, ty)
                tiles.append((tx, ty))
        if kind == "spawn":
            # A spawned actor stands somewhere; a scene that spawns on a wall is a checker error in spec 06 rule 4.
            assert walkable(map_row, cmd["x"], cmd["y"]), "scene %s[%d] spawns an actor on blocked tile %d,%d" % (
                scene_id, index, cmd["x"], cmd["y"])
    raise AssertionError("scene %s ran out of commands without end" % scene_id)


def test_every_scene_walks_to_end_on_walkable_tiles_with_branch_both_ways():
    map_rows = maps()
    for row in scenes():
        never = walk_scene(row["id"], False, map_rows)
        assert never, "scene %s walked no tiles" % row["id"]
        taken = walk_scene(row["id"], True, map_rows)
        assert taken, "scene %s walked no tiles with branch taken" % row["id"]


def test_a_branch_target_is_not_a_cycle():
    rows = {row["id"]: row for row in scenes()}
    edges = {}
    for scene_id, row in rows.items():
        edges[scene_id] = [cmd["scene"] for cmd in row["commands"] if cmd["cmd"] == "branch"]

    def visit(node, path):
        assert node not in path, "branch cycle: %s" % " -> ".join(list(path) + [node])
        for nxt in edges.get(node, []):
            visit(nxt, path + [node])

    for scene_id in edges:
        visit(scene_id, [])


# ---------------------------------------------------------------------------------------------------------------
# 6 and 7: how a scene takes its map and how it hands control back.


def test_a_scene_takes_its_map_and_start_tile_without_the_app_fade():
    text = read_text(SCENE_GML)
    place = gml_function(text, "pp_scene_world_place")
    assert "pp_map_load(" in place, "the placement no longer loads the map a scene names"
    assert "pp_overworld_hero(" in place, "the placement no longer puts the walker on the scene's start tile"
    assert "pp_overworld_camera_follow(" in place, "the placement leaves the camera on the old map"
    assert "pp_app_fade_in(" not in place, "the scene placement restarts the app fade"
    assert "pp_overworld_change_map(" not in place, (
        "a scene placed through pp_overworld_change_map restarts the map fade, which is what a branch must not do")

    take = gml_function(text, "pp_scene_take_scene")
    assert "pp_scene_world_place(" in take, "adopting a scene no longer places it"
    branch = gml_function(text, "pp_scene_command_start")
    branch_case = branch[branch.find('case "branch"'):]
    branch_case = branch_case[:branch_case.find("case \"end\"")]
    assert "pp_scene_take_scene(" in branch_case, "branch no longer re-enters the target scene in place"
    assert "pp_scene_new(" not in branch_case, "branch builds a second runner, which restarts the scene from zero"


def test_end_hands_the_walker_back_on_the_tile_it_stopped_on():
    text = read_text(SCENE_GML)
    end = gml_function(text, "pp_scene_end")
    assert "tx * PP_TILE" in end and "ty * PP_TILE" in end, "the walker is not snapped to the tile he stopped on"
    assert "camera_follow = true" in end, "the camera does not follow the walker again after a scene"
    assert "pp_overworld_camera_follow(" in end, "the camera is left where the scene put it"
    assert "dir: -1" in end, "a fade left at black is not turned around at the end of a scene"

    overworld = read_text(OVERWORLD_GML)
    assert "if (!pp_scene_running(_world.scene)) {" in overworld, (
        "the overworld no longer drops the finished runner, so control never comes back")
    assert "_world.scene = undefined;" in overworld
    assert "pp_scene_step(_world.scene, _world);" in overworld, "the overworld no longer steps the running scene"


# ---------------------------------------------------------------------------------------------------------------
# 8: the debug keys and the self test.


def test_the_debug_keys_are_gated_and_the_self_test_walks_the_scene_list():
    text = read_text(SCENE_GML)
    assert '#macro PP_SCENE_SELFTEST_ENV "PP_" + "SCENE_SELFTEST"' in text, "the self test has no environment gate"
    key = gml_function(text, "pp_scene_debug_key")
    assert "environment_get_variable(PP_SCENE_SELFTEST_ENV)" in key, "the debug key is not gated, so a real launch runs it"
    assert 'pp_pressed("debug_warp")' in key, "F1 no longer runs the self test"
    assert 'pp_pressed("debug_step")' in key, "F2 no longer steps one command"

    selftest = gml_function(text, "pp_scene_selftest")
    assert "global.pp_data.scenes.scenes" in selftest, "the self test does not walk the committed scene list"
    assert "pp_scene_selftest_one(" in selftest, "the self test does not play each scene"
    assert "played, " in selftest, "the self test prints no total line"
    assert "global.pp_ledger = pp_ledger_new();" in selftest, (
        "the self test runs on the live ledger, so a scene's setflag lands in the player's run")
    assert "global.pp_ledger = _saved_ledger;" in selftest, "the self test does not put the ledger back"

    one = gml_function(text, "pp_scene_selftest_one")
    assert "pp_scene_new(" in one, "the self test does not use the real runner"
    assert "pp_scene_step(_sc, _world);" in one, "the self test does not step the real runner"
    assert "PP_SCENE_SELFTEST_CAP" in one, "the self test has no step cap, so a stuck scene would hang it"
    assert 'ended_by != "end"' in one, "the self test accepts a scene that never reached end"
    assert "_sc.unknown > 0" in one, "the self test accepts an unhandled command"

    step = gml_function(text, "pp_scene_debug_step")
    assert "index " in step, "the F2 step does not print the command index (spec 06 rule 7)"

    game_step = read_text(GAME_STEP_GML)
    assert "pp_scene_debug_key(global.pp.world);" in game_step, "nothing calls the scene debug keys"


# ---------------------------------------------------------------------------------------------------------------
# 9: the flash (card t_531bc76c). The storm's lightning over a map: a palette change on steps the film already
# spends, so the command may not wait, may not own a runner state, and may not be its own clock.

def test_the_flash_command_costs_the_scene_no_steps_and_names_a_declared_role():
    text = read_text(SCENE_GML)
    start = gml_function(text, "pp_scene_command_start")
    flash_case = start[start.find('case "flash"'):]
    flash_case = flash_case[:flash_case.find('case "spawn"')]
    assert flash_case, "the runner has no flash case"
    assert "pp_world_flash(" in flash_case, "the flash case does not hand the flash to the world"
    assert "pp_scene_advance(_sc, _world);" in flash_case, "the flash case does not advance, so it would hang the scene"
    assert "_sc.state = " not in flash_case, (
        "the flash case sets a runner state, so it waits for a clock of its own and the film's steps move")
    assert "_sc.timer" not in flash_case, "the flash case carries a timer, which is a wait by another name"
    assert 'PP_FLASH_STEPS' in flash_case, "the flash case does not read the 2 frame default from pp_config"

    # The default role is a role every set in data/room_palettes.json declares, so the default draws a colour the
    # screen already spends; a role no set declares would draw the missing colour instead.
    assert '_flash_role = "paper";' in flash_case, "the flash default role is not paper"
    sets = read_json("data/room_palettes.json")["sets"]
    for entry in sets:
        assert "paper" in entry["roles"], "set %s does not declare the flash's default role" % entry["id"]

    # The world owns the flash and counts it down on its own clock, exactly as it owns the shake.
    world = read_text(OVERWORLD_GML)
    created = gml_function(text=world, name="pp_overworld_new")
    assert "flash_steps: 0," in created and 'flash_role: "paper"' in created, \
        "a fresh overworld does not declare the flash, so the first draw of a flashing scene reads a missing key"
    step = gml_function(text=world, name="pp_overworld_step")
    assert "if (_world.flash_steps > 0) _world.flash_steps -= 1;" in step, "nothing counts the flash down"
    setter = gml_function(text=world, name="pp_world_flash")
    assert "PP_FLASH_MAX_STEPS" in setter, "the world's flash setter is not capped by pp_config"
    draw = gml_function(text=world, name="pp_overworld_draw")
    assert "_world.flash_steps > 0" in draw, "the frame is never flooded, so the command would be invisible"
    assert "pp_role_colour(_world.flash_role)" in draw, (
        "the flash is not drawn in a role from the room's own set (spec 13 rule 2: no colour literal at a draw site)")


def test_a_committed_scene_exercises_the_flash():
    """Acceptance for the card: the command is used by a real scene, not only listed."""
    used = [(row["id"], index, command) for row in scenes() for index, command in enumerate(row["commands"])
            if command.get("cmd") == "flash"]
    assert used, "no committed scene uses the flash, so the command is declared and never played"
    for scene_id, index, command in used:
        assert set(command) <= {"cmd", "steps", "role"}, "scene %s[%d] carries an argument no runner reads" % (
            scene_id, index)
