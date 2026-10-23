"""The demo route, every step of it, read from data/slice.json without running GameMaker (card t_030a89e5, R32).

Nothing here executes GML. Every check reads a real file and computes the answer from it, so a route row that
names content nobody wrote fails here instead of in the recording, and a step deleted from the file fails by name.

Sources this file measures, never restates:

    data/slice.json                          the route: first, steps, and every id a step hands to
    data/scenes/all.json                     the scene rows a scene step names, their maps and their commands
    data/maps/all.json                       the map rows, their spawns, their collision grid and their triggers
    data/encounters/all.json                 the fight step's encounter and the enemy ids it fields
    data/enemies/all.json                    the enemy rows behind those ids
    data/mechanics/pacing_recipes.json       beat_sheet: 32 beats, total_seconds 900, one seconds value a beat
    data/intro_text.json                     the crawl the crawl step names
    game/rooms/<room>/<room>.yy              the room a title step names, the thing asset_get_index resolves
    tools/check_data.py                      SCENE_COMMANDS, imported rather than copied (one command set)
    tests/test_first_fight.py                assert_hero_survives, the cannot-be-lost proof, called not copied
    game/scripts/pp_app/pp_app.gml           pp_slice_handoff and pp_slice_spawn, the resolution this file mirrors
    knowledge/mechanics/PACING-AND-CUTSCENES.md section 9, the beat sheet the authored seconds come from

What is proven, in the card's own order:

  1. every step of the route exists and resolves the one id it names: a room in the project, a data file, a
     scene row and its map, a map row, an encounter and its enemies, a trigger on a map, or another step id;
  2. every scene step's commands are the checker's own command set, and the scene ends on `end`;
  3. every map step's spawn tile is walkable in that map's own collision grid;
  4. the fight step's encounter exists and cannot be lost, by calling the first fight's proof;
  5. the save step names a trigger that exists on the map the walk is standing on;
  6. the route is one chain from the first step to the save, every next, lose and to id resolves, nothing after
     the save is unreachable, and the game over branch is reached through the fight's lose edge;
  7. every step owns a contiguous block of the beat sheet, no beat is owned by two steps, each block is made of
     beats of the step's own kind, and the blocks plus the beats no step owns add up to the sheet's stated 900;
     the beats the route does not walk are named (beat 23, the hound's own fight, and 29 to 32 after the save),
     so the route authors 684 s of the sheet's 900;
  8. the steps' own order is printed against the beat order, because the route puts the arrival walk before the
     gate and the save after the fight while the sheet has the gate (20) first and the save (27) before the hold
     fight (28). The table names those inversions; this file does not rule on them;
  9. every step the walk takes carries an authored time, and any step without one is named;
 10. deleting a step from a copy of data/slice.json, and misspelling a scene id in a copy, are both refused and
     both name the step, so the checks above can fail.

The resolution rules are the walker's, not this file's invention: pp_slice_handoff is what a step hands to, and
pp_slice_spawn is which spawn a step lands on (its own spawn when the map has it, otherwise "start", otherwise the
first spawn alphabetically). The save step and the branch step hand nothing to a mode in the walker, so their
checks are the card's: a named trigger on the map, and a `to` that resolves.

Two things this file does not assert, both reported on the card rather than decided here:

  - the fight step's encounter (tutorial_sailors) is authored as beat 28 with 90 s, and the route holds it where
    the sheet's hold fight sits, so beat 23 (the hound, 48 s) is a fight no route step walks. The encounter exists
    and cannot be lost, which is what the card asks; whether the route should also walk the hound is gamedev's.
  - the route's fight step names no scene, so nothing in data/scenes/all.json carries a battle command for it. The
    card asks that the encounter exist, and it does; whether a scene must also call it is a scene author's ruling.

No test in this file reads the network, writes a tracked data file, or needs a key.
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import check_data  # noqa: E402  the checker's own command set, imported and not copied
import test_first_fight as first_fight  # noqa: E402  the first fight's proof, called and not copied

# The slice is the file under test, and it can be pointed at a copy so a mutation is shown to fail these checks
# and not only a helper, the same way tests/test_first_fight.py takes its two row files.
SLICE_PATH = os.environ.get("PP_SLICE_ROUTE_SLICE") or os.path.join(ROOT, "data", "slice.json")
SCENES_PATH = os.environ.get("PP_SLICE_ROUTE_SCENES") or os.path.join(ROOT, "data", "scenes", "all.json")
MAPS_PATH = os.path.join(ROOT, "data", "maps", "all.json")
ENCOUNTERS_PATH = os.path.join(ROOT, "data", "encounters", "all.json")
ENEMIES_PATH = os.path.join(ROOT, "data", "enemies", "all.json")
PACING_PATH = os.path.join(ROOT, "data", "mechanics", "pacing_recipes.json")
DATA_DIR = os.path.join(ROOT, "data")
ROOMS_DIR = os.path.join(ROOT, "game", "rooms")

# The seven step kinds the walker knows (pp_slice_kind). A row naming any other word stops the walk.
STEP_KINDS = ("title", "crawl", "scene", "map", "battle", "save", "branch")

# The step keys that name the thing a step hands to, by kind. A row missing its key names nothing.
TARGET_KEY = {"title": "room", "crawl": "text", "scene": "scene", "map": "map",
              "battle": "encounter", "branch": "to"}

# The beats each route step owns as an inclusive (first, last) pair of beat numbers in
# data/mechanics/pacing_recipes.json beat_sheet. The seconds are not copied: they are summed from the beats
# themselves. The fight step is not listed, because its beats are the ones its own encounter row names
# (data/encounters/all.json `beat`), so the route and the encounter cannot drift apart in this file.
#
# The route's own order is not the beat sheet's order, and this file does not pretend otherwise: the route puts
# the arrival walk before the gate and the save after the fight, while the sheet has the gate (20) before the yard
# walk (21, 22) and the save (27) before the hold fight (28). test_each_step_owns_a_contiguous_block_of_the_sheet
# prints the inversions, and the card carries them as a question for gamedev instead of this file ruling on them.
BEATS_BY_STEP = {
    "title": (1, 2),      # title attract, then PRESS START, menu, NEW GAME confirmed
    "crawl": (3, 6),      # fade to stars, then the three crawl beats
    "drive": (7, 19),     # Big Ben, the London street, the M3, the rain, the radio, the services interlude
    "gate": (20, 20),     # the gate checkpoint, four pages and the one three option choice
    "arrival": (21, 22),  # full control on the dock yard, then the dock office and the boarding pass
    "boarding": (24, 26),  # the quay side walk, the gangway and horn, the ship corridor
    "save": (27, 27),     # the cabin, the ship's log, the first save
}

# The beat kinds a step of each kind may own. A step's range has to be made of its own kinds, so a range cannot
# be slid onto unrelated beats to make a total add up.
BEAT_KINDS_BY_STEP_KIND = {
    "title": {"title", "menu"},
    # The crawl opens on the fade to the star field (beat 3, a cutscene), so its block carries that one cutscene.
    "crawl": {"crawl", "cutscene"},
    "scene": {"cutscene", "walk"},
    "map": {"cutscene", "walk"},
    "battle": {"battle"},
    "save": {"save"},
}

NETWORK_TOKENS = ("urllib", "requests", "socket", "http.client", "httplib", "aiohttp", "ftplib")


# --------------------------------------------------------------------------- reading files and rows


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write(document: dict, path: str) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return path


def _rows(document: dict, collection: str, path: str) -> dict:
    """A row table indexed by id, or a loud failure naming the file that has none."""
    rows = document.get(collection)
    assert isinstance(rows, list), "%s carries no %s list" % (os.path.basename(path), collection)
    table = {}
    for row in rows:
        assert isinstance(row, dict) and isinstance(row.get("id"), str), \
            "%s carries a %s row with no string id" % (os.path.basename(path), collection)
        table[row["id"]] = row
    return table


class Route:
    """Everything one audit run reads, so a check can be handed a copy of any of it."""

    def __init__(self, slice_path: str = SLICE_PATH, scenes_path: str = SCENES_PATH, maps_path: str = MAPS_PATH,
                 encounters_path: str = ENCOUNTERS_PATH, enemies_path: str = ENEMIES_PATH,
                 pacing_path: str = PACING_PATH, rooms_dir: str = ROOMS_DIR):
        self.slice_path = slice_path
        self.scenes_path = scenes_path
        self.maps_path = maps_path
        self.encounters_path = encounters_path
        self.enemies_path = enemies_path
        self.pacing_path = pacing_path
        self.rooms_dir = rooms_dir

        self.slice = _load(slice_path)
        self.route = self.slice.get("route") or {}
        self.steps = self.route.get("steps") or []
        self.first = self.route.get("first") or ""
        self.by_id = {step.get("id"): step for step in self.steps if isinstance(step, dict)}

        self.scenes = _rows(_load(scenes_path), "scenes", scenes_path)
        self.maps = _rows(_load(maps_path), "maps", maps_path)
        self.encounters = _rows(_load(encounters_path), "encounters", encounters_path)
        self.enemies = _rows(_load(enemies_path), "enemies", enemies_path)
        self.beat_sheet = _load(pacing_path).get("beat_sheet") or {}

    # the walker's own lookup, pp_slice_route_row: one row by id, whatever its position in the array
    def step(self, step_id):
        return self.by_id.get(step_id)

    def kind(self, step):
        return step.get("kind") if isinstance(step, dict) else None

    def walk(self):
        """The ids the `next` chain visits, in order. Stops at the first id the route does not carry."""
        order = []
        step_id = self.first
        while step_id:
            if step_id in order:
                break
            step = self.step(step_id)
            if step is None:
                break
            order.append(step_id)
            step_id = step.get("next") or ""
        return order


# --------------------------------------------------------------------------- the resolution rules

def room_exists(route: Route, room: str) -> bool:
    """The room a title step names, the way the project holds it: game/rooms/<room>/<room>.yy."""
    return os.path.isfile(os.path.join(route.rooms_dir, room, room + ".yy"))


def spawn_name(map_row: dict, step: dict) -> str:
    """pp_slice_spawn: the row's own spawn when the map has it, otherwise "start", otherwise the first name."""
    named = step.get("spawn") if isinstance(step, dict) else None
    spawns = map_row.get("spawns") or {}
    if named and named in spawns:
        return named
    if "start" in spawns:
        return "start"
    return sorted(spawns)[0] if spawns else "start"


def map_step_map(route: Route, step: dict):
    """The map a step stands on: the row's own map, or for the save step the map the walk reached it on."""
    if step.get("map"):
        return step["map"]
    if step.get("kind") == "save":
        index = route.walk().index(step.get("id")) if step.get("id") in route.walk() else -1
        for step_id in reversed(route.walk()[:index]):
            earlier = route.step(step_id) or {}
            if earlier.get("map"):
                return earlier["map"]
            if earlier.get("scene"):
                scene = route.scenes.get(earlier["scene"]) or {}
                return scene.get("map") or ""
    return ""


def trigger_row(map_row: dict, trigger_id: str):
    for trigger in map_row.get("triggers") or []:
        if isinstance(trigger, dict) and trigger.get("id") == trigger_id:
            return trigger
    return None


def resolution_problems(route: Route, step: dict) -> list:
    """What one step hands to, checked the way pp_slice_handoff takes it. Every line names the step."""
    step_id = step.get("id") if isinstance(step, dict) else "?"
    label = "step %s" % step_id
    kind = route.kind(step)
    if kind not in STEP_KINDS:
        return ["%s: the kind %r is not one of %s" % (label, kind, ", ".join(STEP_KINDS))]

    problems = []
    key = TARGET_KEY.get(kind)

    if kind == "title":
        room = step.get(key) or ""
        if not room:
            problems.append("%s: the row names no room" % label)
        elif not room_exists(route, room):
            problems.append("%s: the room %r is not in the project (game/rooms/%s/%s.yy)"
                            % (label, room, room, room))

    elif kind == "crawl":
        text = step.get(key) or "intro_text"
        if not os.path.isfile(os.path.join(DATA_DIR, text + ".json")):
            problems.append("%s: data/%s.json is not in the build" % (label, text))

    elif kind == "scene":
        scene_id = step.get(key) or ""
        if not scene_id:
            problems.append("%s: the row names no scene" % label)
        else:
            scene = route.scenes.get(scene_id)
            if scene is None:
                problems.append("%s: the scene %r is not in data/scenes/all.json" % (label, scene_id))
            else:
                scene_map = scene.get("map") or ""
                if scene_map not in route.maps:
                    problems.append("%s: the scene %r names the map %r, which is not in data/maps/all.json"
                                    % (label, scene_id, scene_map))

    elif kind == "map":
        map_id = step.get(key) or ""
        if not map_id:
            problems.append("%s: the row names no map" % label)
        elif map_id not in route.maps:
            problems.append("%s: the map %r is not in data/maps/all.json" % (label, map_id))

    elif kind == "battle":
        encounter_id = step.get(key) or ""
        if not encounter_id:
            problems.append("%s: the row names no encounter" % label)
        else:
            encounter = route.encounters.get(encounter_id)
            if encounter is None:
                problems.append("%s: the encounter %r is not in data/encounters/all.json"
                                % (label, encounter_id))
            else:
                unplaced = [enemy for enemy in encounter.get("enemies") or [] if enemy not in route.enemies]
                if unplaced:
                    problems.append("%s: the encounter %r fields %r, which data/enemies/all.json does not carry"
                                    % (label, encounter_id, unplaced))

    elif kind == "save":
        trigger_id = step.get("trigger") or ""
        map_id = map_step_map(route, step)
        if not trigger_id:
            problems.append("%s: the row names no trigger" % label)
        elif not map_id:
            problems.append("%s: the row names no map and no map step stands before it" % label)
        elif map_id not in route.maps:
            problems.append("%s: the row names the map %r, which is not in data/maps/all.json"
                            % (label, map_id))
        else:
            trigger = trigger_row(route.maps[map_id], trigger_id)
            if trigger is None:
                problems.append("%s: the map %r carries no trigger %r" % (label, map_id, trigger_id))
            elif trigger.get("kind") != "save":
                problems.append("%s: the trigger %r on %r is a %r trigger, not a save"
                                % (label, trigger_id, map_id, trigger.get("kind")))

    elif kind == "branch":
        target = step.get(key) or ""
        if not target:
            problems.append("%s: the row names no target step" % label)
        elif target not in route.by_id:
            problems.append("%s: the row hands to the step %r, which the route does not carry"
                            % (label, target))

    return problems


def chain_problems(route: Route) -> list:
    """The ids the route names between its own steps: every one has to resolve, or the walk stops unnamed."""
    problems = []
    if not route.first:
        problems.append("the route names no first step")
    elif route.first not in route.by_id:
        problems.append("the route's first step %r is not one of its steps" % route.first)

    for step in route.steps:
        if not isinstance(step, dict):
            problems.append("a route step is not an object")
            continue
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            problems.append("a route step carries no string id")
            continue
        for edge in ("next", "lose", "to"):
            target = step.get(edge)
            if target and target not in route.by_id:
                problems.append("step %s: its %r edge names the step %r, which the route does not carry"
                                % (step_id, edge, target))
    return problems


def scene_problems(route: Route, step: dict) -> list:
    """A scene's commands against the checker's own set, and the scene ending on `end` (spec 06 rule 6)."""
    scene_id = step.get("scene") or ""
    scene = route.scenes.get(scene_id)
    if scene is None:
        return ["step %s: the scene %r is not in data/scenes/all.json, so its commands cannot be read"
                % (step.get("id"), scene_id)]
    commands = scene.get("commands")
    if not isinstance(commands, list) or not commands:
        return ["step %s: the scene %r carries no commands" % (step.get("id"), scene_id)]

    problems = []
    for index, command in enumerate(commands):
        word = command.get("cmd") if isinstance(command, dict) else None
        if word not in check_data.SCENE_COMMANDS:
            problems.append("step %s: the scene %r command %d names %r, which is not one of the checker's %d "
                            "commands" % (step.get("id"), scene_id, index, word, len(check_data.SCENE_COMMANDS)))
    ends = [index for index, command in enumerate(commands)
            if isinstance(command, dict) and command.get("cmd") == "end"]
    if not ends:
        problems.append("step %s: the scene %r never reaches the end command" % (step.get("id"), scene_id))
    elif ends != [len(commands) - 1]:
        problems.append("step %s: the scene %r has its end command at %r, and only the last one ends it"
                        % (step.get("id"), scene_id, ends))
    return problems


def spawn_tile_problems(route: Route, step: dict) -> list:
    """A map step lands on a tile its own collision grid says the hero can stand on."""
    map_id = step.get("map") or ""
    map_row = route.maps.get(map_id)
    if map_row is None:
        return ["step %s: the map %r is not in data/maps/all.json, so its spawn tile cannot be read"
                % (step.get("id"), map_id)]
    spawn = spawn_name(map_row, step)
    point = (map_row.get("spawns") or {}).get(spawn)
    if not isinstance(point, dict):
        return ["step %s: the map %r carries no spawn %r" % (step.get("id"), map_id, spawn)]
    x, y = point.get("x"), point.get("y")
    collision = map_row.get("collision") or []
    if not isinstance(x, int) or not isinstance(y, int) or not (0 <= y < len(collision)) \
            or not (0 <= x < len(collision[y])):
        return ["step %s: the spawn %r of %r is at %r, %r, outside the %d by %d collision grid"
                % (step.get("id"), spawn, map_id, x, y, len(collision[0]) if collision else 0, len(collision))]
    if collision[y][x] != "0":
        return ["step %s: the spawn %r of %r sits on a blocked tile (%s) at %d, %d"
                % (step.get("id"), spawn, map_id, collision[y][x], x, y)]
    return []


def audit(route: Route) -> list:
    """Every problem the route has, in one list, so a copy of the file can be shown to fail as a whole."""
    problems = list(chain_problems(route))
    for step in route.steps:
        if isinstance(step, dict) and isinstance(step.get("id"), str):
            problems.extend(resolution_problems(route, step))
            if route.kind(step) == "scene":
                problems.extend(scene_problems(route, step))
            if route.kind(step) == "map":
                problems.extend(spawn_tile_problems(route, step))
    return problems


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def route() -> Route:
    return Route()


@pytest.fixture(scope="module")
def beats(route) -> dict:
    return {beat["n"]: beat for beat in route.beat_sheet.get("beats") or []}


def steps_of_kind(route: Route, kind: str) -> list:
    return [step.get("id") for step in route.steps if isinstance(step, dict) and step.get("kind") == kind]


ROUTE = Route()
WALK = ROUTE.walk()


# --------------------------------------------------------------------------- 1. the chain and the resolution


def test_the_route_reads_as_one_chain_to_the_save(route):
    """Ids are unique, every next, lose and to id resolves, and the next chain visits each step once."""
    ids = [step.get("id") for step in route.steps if isinstance(step, dict)]
    assert ids, "data/slice.json carries no route steps"
    assert len(ids) == len(set(ids)), "the route carries two steps with one id: %r" % ids
    assert chain_problems(route) == [], "\n".join(chain_problems(route))

    order = route.walk()
    assert order and order[0] == route.first, "the walk starts at %r, the route's first is %r" % (
        order[:1], route.first)
    repeats = [step_id for step_id in order if order.count(step_id) > 1]
    assert not repeats, "the next chain revisits %r" % repeats

    terminal = route.step(order[-1])
    assert route.kind(terminal) in ("save", "branch"), (
        "the next chain ends on step %r of kind %r, and the last step has to be the save or the ending"
        % (order[-1], route.kind(terminal)))
    assert route.kind(terminal) == "save", (
        "the next chain ends on step %r of kind %r, and the demo ends on the save; the game over branch is "
        "reached through the fight's lose edge" % (order[-1], route.kind(terminal)))


def test_every_step_of_the_route_is_reachable_from_the_first_step(route):
    """Nothing after the save may be unreachable: a step no edge reaches is a step nobody ever plays."""
    reached = set()
    frontier = [route.first] if route.first in route.by_id else []
    while frontier:
        step_id = frontier.pop()
        if step_id in reached or step_id not in route.by_id:
            continue
        reached.add(step_id)
        step = route.by_id[step_id]
        for edge in ("next", "lose", "to"):
            target = step.get(edge)
            if target and target in route.by_id:
                frontier.append(target)

    stranded = [step.get("id") for step in route.steps
                if isinstance(step, dict) and step.get("id") not in reached]
    assert not stranded, (
        "these steps are unreachable from the first step: %r; the game over branch has to hang off the fight's "
        "lose edge or a branch's to" % stranded)


@pytest.mark.parametrize("step_id", [step.get("id") for step in ROUTE.steps], ids=lambda value: str(value))
def test_a_step_resolves_the_one_id_it_names(step_id):
    """The card's first rule, one test a step, so a broken step fails by name."""
    step = ROUTE.step(step_id)
    assert step is not None, "the route has no step %r" % step_id
    problems = resolution_problems(ROUTE, step)
    assert problems == [], "\n".join(problems)


def test_the_slice_header_keys_still_resolve(route):
    """The four keys the checker reads beside the route: map, spawn, scene, encounter."""
    problems = []
    map_name, spawn = route.slice.get("map") or "", route.slice.get("spawn") or ""
    if map_name not in route.maps:
        problems.append("data/slice.json: map %r is not in data/maps/all.json" % map_name)
    else:
        if spawn not in (route.maps[map_name].get("spawns") or {}):
            problems.append("data/slice.json: map %r has no spawn %r" % (map_name, spawn))
    if (route.slice.get("scene") or "") not in route.scenes:
        problems.append("data/slice.json: scene %r is not in data/scenes/all.json" % route.slice.get("scene"))
    if (route.slice.get("encounter") or "") not in route.encounters:
        problems.append("data/slice.json: encounter %r is not in data/encounters/all.json"
                        % route.slice.get("encounter"))
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------- 2. the scenes reach end


@pytest.mark.parametrize("step_id", steps_of_kind(ROUTE, "scene"), ids=lambda value: str(value))
def test_a_scene_step_reaches_end_with_only_known_commands(step_id):
    """The commands are the checker's own set, imported, and the scene ends on `end`."""
    assert check_data.SCENE_COMMANDS, "the checker's command set came back empty"
    step = ROUTE.step(step_id)
    assert step is not None, "the route has no step %r" % step_id
    problems = scene_problems(ROUTE, step)
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------- 3. the spawn tile


@pytest.mark.parametrize("step_id", steps_of_kind(ROUTE, "map"), ids=lambda value: str(value))
def test_a_map_step_spawns_on_a_walkable_tile(step_id):
    """The spawn the walker picks, read out of the map's own collision grid."""
    step = ROUTE.step(step_id)
    assert step is not None, "the route has no step %r" % step_id
    problems = spawn_tile_problems(ROUTE, step)
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------- 4. the fight cannot be lost


def _fixture_value(module, name: str, *args):
    """A fixture's own function, for the two values the first fight's proof needs. pytest wraps a fixture so it
    cannot be called directly; the wrapper keeps the function it wraps, and that is what this calls."""
    function = getattr(module, name)
    inner = getattr(function, "__wrapped__", None)
    assert inner is not None, (
        "tests/test_first_fight.py fixture %r can no longer be called by another file; the proof has to be "
        "reused rather than copied, so this is the thing to fix rather than re-derive" % name)
    return inner(*args)


@pytest.fixture(scope="module")
def first_fight_proof() -> dict:
    """The first fight's own proof, raised into values this file can hand a route step."""
    numbers = _fixture_value(first_fight, "decision_numbers",
                             _fixture_value(first_fight, "knowledge_decision_two"))
    hero = first_fight.find_row(first_fight._load(first_fight.PARTY_PATH), "characters", "hero")
    config_text = first_fight._read(first_fight.CONFIG_GML)
    macros = {"min": first_fight.macro(config_text, "PP_FIGHT_DAMAGE_MIN"),
              "max": first_fight.macro(config_text, "PP_FIGHT_DAMAGE_MAX"),
              "sweep": first_fight.macro(config_text, "PP_FIGHT_SWEEP_STEPS"),
              "steps_per_second": first_fight.macro(config_text, "PP_STEPS_PER_SECOND")}
    return {"numbers": numbers, "hero": hero, "macros": macros}


def test_the_fight_step_names_an_encounter_that_cannot_be_lost(route, first_fight_proof):
    """The card's fight rule, through the first fight's own survivability predicate, not a second copy of it."""
    fight_steps = [step for step in route.steps if isinstance(step, dict) and step.get("kind") == "battle"]
    assert len(fight_steps) == 1, "the route names %d fight steps, and the slice has one" % len(fight_steps)
    step = fight_steps[0]
    encounter_id = step.get("encounter") or ""
    encounter = route.encounters.get(encounter_id)
    assert encounter is not None, "step %s: the encounter %r is not in data/encounters/all.json" % (
        step.get("id"), encounter_id)

    enemies = [route.enemies[enemy_id] for enemy_id in encounter.get("enemies") or []
               if enemy_id in route.enemies]
    assert len(enemies) == len(encounter.get("enemies") or []) == 1, (
        "step %s: encounter %r fields %r" % (step.get("id"), encounter_id, encounter.get("enemies")))

    turns = first_fight.authored_turns(encounter)
    hardest = first_fight.assert_hero_survives(enemies[0], first_fight_proof["hero"], turns,
                                               first_fight_proof["numbers"])
    assert hardest <= first_fight_proof["numbers"]["ceiling"], (
        "step %s: the hardest hit on the hero is %d, above the first fight's ceiling of %d"
        % (step.get("id"), hardest, first_fight_proof["numbers"]["ceiling"]))
    assert turns * hardest < first_fight_proof["hero"]["max_hp"], (
        "step %s: %d turns at %d takes the hero to %d of %d hp, and the fight must not be losable in the route"
        % (step.get("id"), turns, hardest, first_fight_proof["hero"]["max_hp"] - turns * hardest,
           first_fight_proof["hero"]["max_hp"]))


# --------------------------------------------------------------------------- 5. the save step


def test_the_save_step_names_a_trigger_that_exists_on_its_map(route):
    """The card's save rule: the step names a trigger id, and the map the walk is on carries it as a save."""
    save_steps = [step for step in route.steps if isinstance(step, dict) and step.get("kind") == "save"]
    assert len(save_steps) == 1, "the route names %d save steps, and the slice has one" % len(save_steps)
    step = save_steps[0]
    problems = resolution_problems(route, step)
    assert problems == [], "\n".join(problems)

    map_id = map_step_map(route, step)
    trigger_id = step.get("trigger")
    trigger = trigger_row(route.maps[map_id], trigger_id)
    x, y = trigger.get("x"), trigger.get("y")
    collision = route.maps[map_id].get("collision") or []
    assert isinstance(x, int) and isinstance(y, int) and 0 <= y < len(collision) \
        and 0 <= x < len(collision[y]) and collision[y][x] == "0", (
        "step %s: the trigger %r of %r sits at %r, %r, which is not a walkable tile, so the player cannot reach it"
        % (step.get("id"), trigger_id, map_id, x, y))


# --------------------------------------------------------------------------- 6. the sheet, and the seconds


def step_spans(route: Route) -> dict:
    """Every route step's inclusive beat span: declared in BEATS_BY_STEP, or for the fight the beat its own
    encounter row names, so the route and the encounter cannot drift apart here."""
    spans = {}
    for step in route.steps:
        if not isinstance(step, dict):
            continue
        span = BEATS_BY_STEP.get(step.get("id"))
        if span is None and step.get("kind") == "battle":
            encounter = route.encounters.get(step.get("encounter") or "") or {}
            beat = encounter.get("beat")
            if isinstance(beat, int):
                span = (beat, beat)
        spans[step.get("id")] = span
    return spans


def time_table(route: Route, beats: dict) -> list:
    """One row a route step: the beats it owns, the seconds they add up to, and the content's own number."""
    spans = step_spans(route)
    rows = []
    for step in route.steps:
        if not isinstance(step, dict):
            continue
        step_id, kind = step.get("id"), step.get("kind")
        span = spans.get(step_id)
        if kind == "branch" or span is None:
            rows.append({"id": step_id, "kind": kind, "beats": (), "seconds": None, "content": None,
                         "missing": kind != "branch"})
            continue
        first, last = span
        owned = [beats[number] for number in range(first, last + 1) if number in beats]
        seconds = sum(beat["seconds"] for beat in owned)
        content = None
        if kind == "battle" and (step.get("encounter") or "") in route.encounters:
            content = (route.encounters[step["encounter"]].get("pacing") or {}).get("seconds")
        rows.append({"id": step_id, "kind": kind, "beats": (first, last), "seconds": seconds,
                     "content": content, "missing": False})
    return rows


def format_time_table(rows: list, total: int) -> str:
    lines = ["step       kind     beats    authored  content  note"]
    for row in rows:
        beats = "%d-%d" % row["beats"] if row["beats"] else "-"
        seconds = "%4d s" % row["seconds"] if row["seconds"] is not None else "  -  "
        content = "%4d s" % row["content"] if row["content"] is not None else "  -  "
        if row["missing"]:
            note = "MISSING authored time"
        elif row["content"] is not None and row["seconds"] != row["content"]:
            note = "content authors %d s at this position" % row["content"]
        else:
            note = ""
        lines.append("%-10s %-8s %-8s %s   %s   %s" % (row["id"], row["kind"], beats, seconds, content, note))
    authored = sum(row["seconds"] for row in rows if row["seconds"] is not None)
    owned = sum(row["beats"][1] - row["beats"][0] + 1 for row in rows if row["beats"])
    lines.append("route authored: %d s over %d beats; the sheet's own total: %d s" % (authored, owned, total))
    return "\n".join(lines)


def test_each_step_owns_a_contiguous_block_of_the_sheet(route, beats):
    """One block a step, no beat owned twice, each block made of beats of the step's own kind."""
    rows = time_table(route, beats)
    print("\n" + format_time_table(rows, route.beat_sheet.get("total_seconds") or 0))

    owners = {}
    for row in rows:
        if not row["beats"]:
            continue
        allowed = BEAT_KINDS_BY_STEP_KIND.get(row["kind"])
        assert allowed, "step %r of kind %r owns no beat family" % (row["id"], row["kind"])
        for number in range(row["beats"][0], row["beats"][1] + 1):
            assert number in beats, "step %r owns beat %d, which the sheet does not carry" % (row["id"], number)
            assert number not in owners, (
                "beat %d is owned by both step %r and step %r, so its seconds would be counted twice"
                % (number, owners.get(number), row["id"]))
            owners[number] = row["id"]
            assert beats[number]["kind"] in allowed, (
                "step %r of kind %r owns beat %d of kind %r, and it may only own %r"
                % (row["id"], row["kind"], number, beats[number]["kind"], sorted(allowed)))

    # The route's order is not the sheet's order in two places, and the table says so instead of hiding it:
    # the arrival step sits before the gate, and the save sits after the fight.
    walked, order = [], []
    for step_id in route.walk():
        span = spans_of(rows, step_id)
        if span:
            walked.append(step_id)
            order.append(span[0])
    inversions = ["%s (beat %d) before %s (beat %d)" % (walked[index], order[index], walked[index + 1],
                                                        order[index + 1])
                  for index in range(len(order) - 1) if order[index + 1] < order[index]]
    print("the route's own order against the beat sheet: %s"
          % ("no inversion" if not inversions else "; ".join(inversions)))
    assert owners, "no step owns a beat"


def spans_of(rows: list, step_id: str):
    for row in rows:
        if row["id"] == step_id:
            return row["beats"]
    return ()


def test_the_route_seconds_and_the_sheet_add_up_to_900(route, beats):
    """The card's total: what the steps author plus the beats no step walks is the sheet's own 900, and the route
    authors everything up to and including the save."""
    total = route.beat_sheet.get("total_seconds")
    assert total == 900, "the beat sheet's total is %r, and section 9's sheet sums to 900" % total
    assert sum(beat["seconds"] for beat in beats.values()) == total

    rows = time_table(route, beats)
    authored = sum(row["seconds"] for row in rows if row["seconds"] is not None)
    owned = set()
    for row in rows:
        owned.update(range(row["beats"][0], row["beats"][1] + 1) if row["beats"] else [])
    unowned = sorted(set(beats) - owned)
    unowned_seconds = sum(beats[number]["seconds"] for number in unowned)
    named = ", ".join("%d %s (%d s)" % (number, beats[number]["id"], beats[number]["seconds"])
                      for number in unowned)

    assert authored + unowned_seconds == total, (
        "the route authors %d s and the beats no step walks are %d s, which is %d s against the sheet's %d s"
        % (authored, unowned_seconds, authored + unowned_seconds, total))

    # The route has to cover the sheet through its first save, or the demo stops before the beat the card records.
    save_beat = [number for number, beat in beats.items() if beat["kind"] == "save"]
    assert len(save_beat) == 1, "the sheet carries %d save beats" % len(save_beat)
    assert save_beat[0] in owned, "no route step owns the sheet's save beat %d" % save_beat[0]
    covered = beats[save_beat[0]]["running_total"]
    assert authored >= covered, (
        "the route authors %d s and the sheet reaches its first save at %d s, so the route stops short of the save"
        % (authored, covered))

    print("\nthe route authors %d s of the sheet's %d s; the %d s it does not walk: %s"
          % (authored, total, unowned_seconds, named or "none"))


def test_no_step_the_walk_takes_is_missing_its_authored_time(route, beats):
    """Every step on the next chain has to own beats; one without an authored time is named, not skipped."""
    spans = step_spans(route)
    walked = route.walk()
    missing = [step_id for step_id in walked if not spans.get(step_id)]
    assert not missing, (
        "these steps of the walk carry no authored time in the beat sheet: %r; add their beats to the sheet and "
        "to BEATS_BY_STEP" % missing)


# --------------------------------------------------------------------------- 7. the checks can fail


def _slice_copy(tmp_path, mutate) -> str:
    """A copy of data/slice.json with one thing changed, written under tmp_path and never in data/."""
    document = _load(SLICE_PATH)
    mutate(document["route"]["steps"])
    return _write(document, str(tmp_path / "slice.json"))


def test_deleting_a_step_is_named(tmp_path):
    """The card's first failing case: drop a step, and the audit names the step that is now missing."""
    before = audit(Route())
    assert not [problem for problem in before if problem.startswith("step boarding")], (
        "the real route already fails on step boarding, so this case would not prove the audit can name it:\n%s"
        % "\n".join(before))

    path = _slice_copy(tmp_path, lambda steps: steps.remove(
        next(step for step in steps if step.get("id") == "boarding")))
    after = audit(Route(slice_path=path))
    named = [problem for problem in after if "boarding" in problem]
    assert named, "deleting step boarding from the route was not named:\n%s" % "\n".join(after)
    assert any("does not carry" in problem for problem in named), (
        "the deleted step is named, but not as an id the route cannot find:\n%s" % "\n".join(named))


def test_a_misspelled_scene_id_is_named(tmp_path):
    """The card's second failing case: one letter off in a scene id, and the audit names the step and the typo."""
    before = audit(Route())
    scene_steps = [step for step in ROUTE.steps
                   if isinstance(step, dict) and step.get("kind") == "scene"]
    clean = [step for step in scene_steps
             if not [problem for problem in before if problem.startswith("step %s" % step.get("id"))]]
    assert clean, "no scene step of the route resolves today, so a misspelling could not be told from the real gap"
    target = clean[0]
    step_id, scene_id = target["id"], target["scene"]
    misspelled = scene_id[:-1] + ("x" if not scene_id.endswith("x") else "y")

    def mutate(steps):
        for step in steps:
            if step.get("id") == step_id:
                step["scene"] = misspelled

    after = audit(Route(slice_path=_slice_copy(tmp_path, mutate)))
    named = [problem for problem in after if problem.startswith("step %s" % step_id) and misspelled in problem]
    assert named, ("the scene id %r misspelled as %r was not named on step %s:\n%s"
                   % (scene_id, misspelled, step_id, "\n".join(after)))


# --------------------------------------------------------------------------- 8. the file's own promises


def test_the_file_imports_no_network():
    """Spec 16's rule for the shipping fallback holds for the suite too: no network module is imported here."""
    source = _read(os.path.abspath(__file__))
    for token in NETWORK_TOKENS:
        assert not re.search(r"^\s*(?:import|from)\s+" + re.escape(token), source, re.M), (
            "this test file imports %s" % token)
