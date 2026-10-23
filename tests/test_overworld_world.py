"""The overworld's world struct and the first fight's trigger (card FIRST-FIGHT-WIRE, t_4a1a6662).

Why this file exists: the overworld crashed on the first frame of every entry into it, so no encounter trigger on
`ship_small` could ever fire. Build log of the run that found it (`build/first_fight_game.log`, card t_87ee4228):

    PP title: intro finished, starting the run in rm_pp_ship
    PP CRASH: Variable <unknown_object>.steps(100104, -2147483648) not set before reading it.
              | at gml_Script_pp_overworld_draw line 478

The cause was one missing key: `pp_overworld_new` built the world struct without `steps`, and `pp_overworld_draw` hands
`_world.steps` to `pp_map_draw` (for the animated tiles) on the very first draw. GameMaker is not installed on this PC,
so nothing here can execute GML. What it can do is read the module and the data as text and pin the class of failure:

  1. every `_world.<name>` the overworld module reads or writes is declared by the struct `pp_overworld_new` builds,
     which is the check that would have caught the crash before a build;
  2. the world clock is declared at 0 and climbs by one in `pp_overworld_step`, so the value handed to the map draw is
     a counted clock rather than a default;
  3. the first fight is reachable on foot from the map's own spawn: a `battle` trigger two tiles east of `start`, on
     walkable tiles, with no condition, naming an encounter whose enemy row exists;
  4. starting an encounter prints one unconditional log line naming the encounter, which is the line this card's check
     reads out of the run.

Sources this file measures, never restates: game/scripts/pp_overworld/pp_overworld.gml, data/maps/all.json,
data/encounters/all.json, data/enemies/all.json.

No test here reads the network, writes a data file, launches the game or needs a key.
"""

from __future__ import annotations

import io
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
MAPS_PATH = os.path.join(ROOT, "data", "maps", "all.json")
ENCOUNTERS_PATH = os.path.join(ROOT, "data", "encounters", "all.json")
ENEMIES_PATH = os.path.join(ROOT, "data", "enemies", "all.json")

MAP_ID = "ship_small"
SPAWN_NAME = "start"


def _read(path: str) -> str:
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def code_only(text: str) -> str:
    """Drop `//` comments, so a structural check reads code and never the prose about it."""
    return "\n".join(line[:line.find("//")] if "//" in line else line for line in text.split("\n"))


def brace_block(text: str, marker: str) -> str:
    """The brace balanced block that starts at the first `{` after `marker`."""
    start = text.index(marker)
    open_index = text.index("{", start)
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index:index + 1]
    raise AssertionError("unbalanced block after %r" % marker)


def function_body(text: str, name: str) -> str:
    return brace_block(text, "function %s(" % name)


def struct_keys(block: str) -> list:
    """The keys declared directly in a GML struct literal, at depth one, in the order they are written."""
    keys = []
    depth = 0
    for line in block.split("\n"):
        if depth == 1:
            match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", line.strip())
            if match:
                keys.append(match.group(1))
        depth += line.count("{") - line.count("}")
    return keys


@pytest.fixture(scope="module")
def world() -> str:
    return code_only(_read(OVERWORLD_GML))


@pytest.fixture(scope="module")
def world_keys(world) -> list:
    return struct_keys(brace_block(world, "var _world = {"))


@pytest.fixture(scope="module")
def ship() -> dict:
    maps = _load(MAPS_PATH)["maps"]
    found = [row for row in maps if row.get("id") == MAP_ID]
    assert len(found) == 1, "expected one map row %r, found %d" % (MAP_ID, len(found))
    return found[0]


# --------------------------------------------------------------------------- 1. the struct


def test_the_world_struct_declares_every_field_the_module_uses(world, world_keys):
    """The crash class: a field the module reads that the constructor never declared.

    Reads and writes are both taken (`_world.fade = undefined` is a read of `_world` for the same key), because a key
    written before it is declared is just as fatal on the frame that reads it first. The three names that are written
    into a nested struct (`_world.marker_off[$ key]`) resolve to the declared parent, so no exception is needed.
    """
    used = sorted(set(re.findall(r"_world\.([A-Za-z_][A-Za-z0-9_]*)", world)))
    assert "steps" in used, "pp_overworld no longer reads _world.steps; this test pins the field that crashed it"
    missing = [name for name in used if name not in world_keys]
    assert not missing, "pp_overworld_new does not declare %r, and the module reads it: %s" % (
        missing, sorted(world_keys))
    # The struct is a struct of its own, not the hero's: the hero's own clock is a different key on a different struct.
    hero_body = function_body(world, "pp_overworld_hero")
    hero_keys = struct_keys(brace_block(hero_body, "return {"))
    assert "steps" in hero_keys and "map" not in hero_keys, hero_keys


def test_both_draw_calls_hand_the_map_the_world_clock(world, world_keys):
    """The draw is where the missing key was read, so the argument is pinned by name."""
    assert "_world.steps" in world_keys or "steps" in world_keys
    draw = function_body(world, "pp_overworld_draw")
    assert draw.count("_world.steps") == 2, draw
    assert "pp_map_draw(_world.map, floor(_world.cam_x) + _ox, floor(_world.cam_y) + _oy, _world.steps)" in draw, draw
    assert "pp_map_draw_above(_world.map, floor(_world.cam_x) + _ox, floor(_world.cam_y) + _oy, _world.steps)" in draw


def test_the_world_clock_is_declared_at_zero_and_climbs_every_step(world, world_keys):
    """A declared but never counted clock would freeze every animated tile, so both halves are checked."""
    assert "steps" in world_keys, "pp_overworld_new declares no steps clock: %s" % world_keys
    body = brace_block(world, "var _world = {")
    assert re.search(r"^\s*steps:\s*0\s*,?\s*$", body, re.M), body
    step = function_body(world, "pp_overworld_step")
    assert "_world.steps += 1" in step, step[:400]
    # It climbs before the branch that returns for a scene, so a scene on the deck still animates the ground.
    assert step.index("_world.steps += 1") < step.index("pp_scene_running(_world.scene)")


# --------------------------------------------------------------------------- 2. the trigger


def collision_rows(ship: dict) -> list:
    rows = ship.get("collision")
    assert isinstance(rows, list) and len(rows) == ship["height"], "ship_small carries no collision grid"
    assert all(len(row) == ship["width"] for row in rows), "a collision row is not the map's width"
    return rows


def walkable(ship: dict, x: int, y: int) -> bool:
    return collision_rows(ship)[y][x] == "0"


def test_the_first_fight_is_two_tiles_from_the_spawn_on_walkable_ground(ship):
    """The whole card in one measurement: the walk from `start` to the fight, tile by tile, on the map's own grid."""
    spawn = ship["spawns"][SPAWN_NAME]
    battles = [row for row in ship["triggers"] if row.get("kind") == "battle"]
    assert battles, "ship_small carries no battle trigger, so the first fight cannot be reached on foot"

    # The walk is a straight line, because a player presses one direction from the spawn.
    candidates = [row for row in battles if row["y"] == spawn["y"] and row["x"] > spawn["x"]]
    assert candidates, "no battle trigger lies east of the spawn on the same row: %r" % battles
    trigger = candidates[0]
    for x in range(spawn["x"], trigger["x"] + 1):
        assert walkable(ship, x, trigger["y"]), "the walk east hits a wall at %d,%d" % (x, trigger["y"])
    # Confirm reads the tile ahead, so the tile before the trigger has to be standable.
    assert walkable(ship, trigger["x"] - 1, trigger["y"])
    assert trigger["x"] - spawn["x"] == 2, "the trigger moved: %d tiles from the spawn" % (trigger["x"] - spawn["x"])


def test_the_trigger_fires_with_no_condition_and_names_a_fight_that_exists(ship):
    """A trigger gated on a flag that nothing sets yet is a trigger the demo cannot reach."""
    trigger = [row for row in ship["triggers"] if row.get("kind") == "battle"][0]
    assert trigger["condition"] == "", "the first fight's trigger is gated on %r" % trigger["condition"]
    for key in ("x", "y", "kind", "id", "once", "condition"):
        assert key in trigger, "the trigger row does not carry %r" % key

    encounters = _load(ENCOUNTERS_PATH)["encounters"]
    found = [row for row in encounters if row.get("id") == trigger["id"]]
    assert len(found) == 1, "the trigger names %r and data/encounters/all.json holds %d rows with it" % (
        trigger["id"], len(found))
    encounter = found[0]
    assert encounter["enemies"], encounter
    enemies = {row["id"] for row in _load(ENEMIES_PATH)["enemies"]}
    for enemy_id in encounter["enemies"]:
        assert enemy_id in enemies, "the encounter names enemy %r, which has no row" % enemy_id


def test_firing_the_battle_trigger_asks_the_app_for_the_fight(world):
    """The data row is inert unless the `battle` case of the trigger switch starts the encounter."""
    fire = function_body(world, "pp_overworld_fire")
    battle_case = fire[fire.index('case "battle":'):]
    battle_case = battle_case[:battle_case.index("break;")]
    assert "pp_overworld_start_encounter(_world, _trigger.id)" in battle_case, battle_case


# --------------------------------------------------------------------------- 3. the proof line


def test_starting_an_encounter_prints_one_line_naming_the_encounter(world):
    """This card's check reads the log, so the line has to be printed, and printed unconditionally.

    It is not behind `PP_DEBUG`: the constant is false in a release build (`pp_config.gml`), and the run that proves the
    fight is reachable is a release build.
    """
    body = function_body(world, "pp_overworld_start_encounter")
    assert "show_debug_message(" in body, body
    assert '"PP: battle start "' in body, body
    assert "string(_encounter_id)" in body, body
    assert "PP_DEBUG" not in body, "the proof line is behind the debug switch, so a release build never prints it"
    # One line per fight: the guard above it is what keeps a second request from printing a second line.
    assert body.index('if (_world.battle_request != "") return false;') < body.index("show_debug_message(")
