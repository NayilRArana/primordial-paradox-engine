"""The slice's middle act, proved from data: Percy's phases, the Prometheus interruption and both endings (G0-4T).

GameMaker is not installed on this PC, so nothing here plays the fight. What this file can do, and does, is walk the
data the way the engine will have to: from the slice entry through the scenes, the maps, their triggers, the
encounters and the enemies to the interruption, resolving every id on the way against the table that owns it.

Sources this file measures, never restates:

    data/slice.json                    the entry: map, spawn, scene, encounter, and the route steps
    data/maps/all.json                 both ship maps, their spawns, their triggers and each trigger's condition
    data/scenes/all.json               the scene rows, their maps and their commands
    data/encounters/all.json           the Percy encounter: endings, flags, interrupt, epilogue, spare rule
    data/enemies/all.json              Percy: hp, attack, patterns, phases, talk set and line per phase
    data/patterns/all.json             the four patterns, their shapes, lengths and declared concurrency
    data/dialogue/all.json             every line the slice shows, and its choices
    data/flags.json                    the flag names every reference above has to land in
    data/talk_cards.json               the phase card a phase row's talk_phase has to match
    data/project.json                  route_labels, the four words spec 10's table uses
    specs/05-dialogue.md               the box: 28 characters a line, 3 lines a page, two control codes
    specs/07-battle-director.md        Percy 120 hp, attack 3 to 6, FIGHT damage 2 to 12
    specs/09-bullet-pattern-recipes.md the 2, 3, 3 concurrency ladder
    specs/10-route-ledger.md           the route table, the exit rows and the turned enemy
    tools/check_data.py                imported, not copied: LINE_CHARS, PAGES, PAGE_LINES, simulate()
    tests/test_ledger.py               imported, not copied: the door's mirror, exits and verdicts
    game/scripts/pp_ledger/pp_ledger.gml  pp_ledger_route, the order the derived route is read in

What is proved, in the card's order:

  1. Percy's phase thresholds strictly descend below 120 hp, every phase pattern id exists, the last phase is
     reachable from 120 hp by whole FIGHT blows, every attack stays inside the 3 to 6 band, and the interrupt
     threshold sits at 60 or below as the card decided.
  2. From the slice entry the walk resolves every id it crosses, and a path exists from ship_boarding through
     tutorial_sailors and percy to prometheus_interrupt without one unknown id. The walk is Python over the data,
     including each trigger's condition flag, so a flag that nothing sets stops the walk instead of being ignored.
  3. Both Percy endings carry their dialogue and their flag, the interrupted ending plays the Prometheus scene and
     leaves Percy standing, and each ending writes its exit row through tests/test_ledger.py's mirror of the one door.
     The route is derived from the counters, never stored.
  4. Every dialogue line fits the spec 05 box after our own {pause:N} and {speed:N} codes are stripped, and every
     TODO_NAME_ placeholder is printed by id so Nayil sees exactly what is unnamed.
  5. Every phase pattern runs through tools/check_data.py's own simulation twice with the same seed and reports the
     same positions, ends inside the 900 step cap, never spawns inside the exclusion radius, and stays inside its
     declared concurrency.
  6. Two mutations: an unknown pattern id in a phase, and the spare dialogue removed. Both are shown failing here,
     and the checker's own answer to each is printed rather than assumed.

A finding this file measured, and the fix that closed it (card t_905a18ce F3): the interrupt used to be written on the
Percy encounter row as an hp crossing at 60, with FIGHT damage capped at 12 (spec 07), so no blow could take Percy from
above 60 to 0 and the kill ending was authored in data but unreachable through the fight. specs/18-boss-phases.md
section 4 (settled 2026-10-22, card t_00a94c86) answers it by moving the trigger to a refused SPARE, and section 7
refusal 10 makes an encounter level interrupt a checker error. The data now carries one block, the enemy row's, the
checker refuses the encounter copy, and every assertion here reads the row the director reads.

No test here reads the network, writes a tracked file, or needs a key. The two mutation tests work on a copy of
data\\ that the conftest fixture makes.
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

import check_data  # noqa: E402  the checker's simulation and its box numbers, imported and not copied
import test_ledger as ledger  # noqa: E402  the door's mirror, its exits and its verdicts, called not copied

DEFAULT_ROOT = os.environ.get("PP_SLICE_STORY_ROOT") or ROOT

# The box (spec 05) and the fight numbers (spec 07). The two box numbers come from the checker so this file and the
# gate cannot disagree about what "fits" means.
LINE_CHARS = check_data.LINE_CHARS          # 28
PAGE_LINES = check_data.PAGE_LINES          # 3
PAGES = check_data.PAGES                    # 3
FIGHT_DAMAGE_MIN, FIGHT_DAMAGE_MAX = 2, 12  # spec 07, the FIGHT row: sweeps 0 to 100 in 60 steps, damage 2 to 12
BOSS_ATTACK_MIN, BOSS_ATTACK_MAX = 3, 6     # spec 07, health: Percy 120 hp and attack 3 to 6
PERCY_MAX_HP = 120                          # spec 07, health
INTERRUPT_CEILING = 60                      # the card's decision: the interruption threshold sits at 60 or below
ROUTE_LABELS = ("undecided", "mercy", "blooded", "genocide")  # spec 10 table, and data/project.json

# The four content ids the card names as the slice's path, in its order. `percy` is the encounter row's id; the enemy
# row of the same name is reached through it and is asserted separately.
BOARDING = ("scene", "ship_boarding")
SAILORS = ("encounter", "tutorial_sailors")
PERCY = ("encounter", "percy")
INTERRUPTION = ("scene", "prometheus_interrupt")

# Two control codes only (spec 05 rule 5). Anything else in braces would be printed literally by the engine, so a
# leftover brace after the strip is a fault and not a style note.
CONTROL_CODE = re.compile(r"\{(pause|speed):\d+\}")
PLACEHOLDER = re.compile(r"TODO_NAME_[A-Za-z0-9_]*")
ANY_TODO = re.compile(r"\bTODO[A-Z_]*")
LONG_DASHES = ("\u2013", "\u2014", "\u2015")

# The tables the walk resolves against, by node kind.
ROWS_BY_KIND = {"scene": "scenes", "encounter": "encounters", "enemy": "enemies",
                "pattern": "patterns", "dialogue": "dialogues", "map": "maps"}

# A trigger kind names a row in one table (tools/check_data.py TRIGGER_ID_TABLES, which this repeats because a walk
# needs the arrow and the checker needs the error). "save" is absent on purpose: a save point's id is a label.
TRIGGER_TARGET = {"scene": "scene", "battle": "encounter", "map": "map",
                  "say": "dialogue", "flag": "flag", "marker": "encounter"}


# ---------------------------------------------------------------------------------------------------------------
# Reading the data, and walking it


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _table(path, collection):
    rows = _load(path).get(collection) or []
    return {row["id"]: row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)}


def _raw(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


class Story:
    """Everything one walk reads, so a check can be handed a copy of any of it. A mutation test builds one on a copy."""

    def __init__(self, root=DEFAULT_ROOT):
        self.root = root
        data = os.path.join(root, "data")
        self.slice = _load(os.path.join(data, "slice.json"))
        self.project = _load(os.path.join(data, "project.json"))
        self.flags = set(_load(os.path.join(data, "flags.json")).get("flags") or [])
        self.talk_cards = _load(os.path.join(data, "talk_cards.json")).get("cards") or []
        self.enemies = _table(os.path.join(data, "enemies", "all.json"), "enemies")
        self.patterns = _table(os.path.join(data, "patterns", "all.json"), "patterns")
        self.encounters = _table(os.path.join(data, "encounters", "all.json"), "encounters")
        self.scenes = _table(os.path.join(data, "scenes", "all.json"), "scenes")
        self.dialogues = _table(os.path.join(data, "dialogue", "all.json"), "dialogue")
        # Two map files make the id table: the registry, and the lower deck's own file. The checker loads both.
        self.maps = {}
        for relative in ("maps/all.json", "maps/ship_sample.json"):
            self.maps.update(_table(os.path.join(data, relative), "maps"))
        self._dangles = set()
        self._dependants = None

    # -- resolution -------------------------------------------------------------------------------------------

    def rows(self, kind):
        return getattr(self, ROWS_BY_KIND[kind])

    def exists(self, kind, name):
        if kind == "flag":
            return isinstance(name, str) and name in self.flags
        return isinstance(name, str) and name != "" and name in self.rows(kind)

    def resolve(self, kind, name, where):
        """One reference, resolved against the table that owns it. A miss is remembered and named, never guessed."""
        found = self.exists(kind, name)
        if not found:
            self._dangles.add((where, kind, name))
        return found

    def dangles(self):
        return sorted(self._dangles, key=lambda item: (item[0], item[1], str(item[2])))

    # -- edges ------------------------------------------------------------------------------------------------

    def _dialogue_refs(self, row, where, out):
        for index, name in enumerate(row.get("sets") or []):
            out.append((("flag", name), "%s.sets[%d]" % (where, index), None))
        for index, choice in enumerate(row.get("choices") or []):
            choice_path = "%s.choices[%d]" % (where, index)
            for flag_index, flag_name in enumerate(choice.get("sets") or []):
                out.append((("flag", flag_name), "%s.sets[%d]" % (choice_path, flag_index), None))
            if "goto" in choice:
                out.append((("dialogue", choice.get("goto")), choice_path + ".goto", None))
            if choice.get("condition"):
                out.append((("flag", choice.get("condition")), choice_path + ".condition", None))

    def dependants(self):
        """Flags that gate something. A flag node's outgoing edges are the triggers and choices it unlocks."""
        if self._dependants is not None:
            return self._dependants
        index = {}
        for map_id, row in self.maps.items():
            for position, trigger in enumerate(row.get("triggers") or []):
                condition = trigger.get("condition")
                if condition:
                    index.setdefault(condition, []).append(
                        (("map", map_id), "%s.triggers[%d].condition" % (map_id, position), None))
        for dialogue_id, row in self.dialogues.items():
            for choice_index, choice in enumerate(row.get("choices") or []):
                condition = choice.get("condition")
                if condition:
                    index.setdefault(condition, []).append(
                        (("dialogue", dialogue_id), "%s.choices[%d].condition" % (dialogue_id, choice_index), None))
        self._dependants = index
        return index

    def edges(self, node):
        """The next content a node hands to, with the path that names the reference, and the flag it is gated on."""
        kind, name = node
        out = []
        if kind == "flag":
            return list(self.dependants().get(name, []))
        if kind == "pattern":
            return out
        if kind == "scene":
            row = self.scenes[name]
            out.append((("map", row.get("map")), "%s.map" % name, None))
            for index, command in enumerate(row.get("commands") or []):
                where = "%s.commands[%d]" % (name, index)
                cmd = command.get("cmd")
                if cmd == "say":
                    out.append((("dialogue", command.get("id")), where + ".id", None))
                elif cmd == "battle":
                    out.append((("encounter", command.get("id")), where + ".id", None))
                elif cmd == "setflag":
                    out.append((("flag", command.get("name")), where + ".name", None))
                elif cmd == "branch":
                    out.append((("flag", command.get("flag")), where + ".flag", None))
                    out.append((("scene", command.get("scene")), where + ".scene", command.get("flag")))
        elif kind == "map":
            row = self.maps[name]
            for index, trigger in enumerate(row.get("triggers") or []):
                where = "%s.triggers[%d]" % (name, index)
                target = TRIGGER_TARGET.get(trigger.get("kind"))
                if target is not None:
                    out.append(((target, trigger.get("id")), where + ".id", trigger.get("condition") or None))
                if trigger.get("kind") == "map" and trigger.get("spawn"):
                    # A map trigger's spawn names a spawn on the map it leads TO, not on the map it sits on.
                    target_map = self.maps.get(trigger.get("id")) or {}
                    spawns = target_map.get("spawns") or {}
                    if trigger["spawn"] not in spawns:
                        self._dangles.add((where + ".spawn", "spawn", trigger["spawn"]))
            for index, actor in enumerate(row.get("actors") or []):
                if actor.get("dialogue"):
                    out.append((("dialogue", actor.get("dialogue")), "%s.actors[%d].dialogue" % (name, index), None))
        elif kind == "encounter":
            row = self.encounters[name]
            for index, enemy_id in enumerate(row.get("enemies") or []):
                out.append((("enemy", enemy_id), "%s.enemies[%d]" % (name, index), None))
            for field_name in ("intro_dialogue", "win_dialogue_kill", "win_dialogue_spare", "lose_dialogue"):
                if row.get(field_name):
                    out.append((("dialogue", row[field_name]), "%s.%s" % (name, field_name), None))
            for field_name in ("flags_on_kill", "flags_on_spare"):
                for index, flag_name in enumerate(row.get(field_name) or []):
                    out.append((("flag", flag_name), "%s.%s[%d]" % (name, field_name, index), None))
            # Card t_905a18ce (F3): the interrupt block is the ENEMY row's (spec 18 section 4, C18-7), so the walk follows
            # it from the enemy and a copy on the encounter row is a checker error rather than a second arrow here.
            if row.get("epilogue_scene"):
                out.append((("scene", row["epilogue_scene"]), "%s.epilogue_scene" % name, None))
        elif kind == "enemy":
            row = self.enemies[name]
            for index, pattern_id in enumerate(row.get("patterns") or []):
                out.append((("pattern", pattern_id), "%s.patterns[%d]" % (name, index), None))
            if row.get("talk_dialogue"):
                out.append((("dialogue", row["talk_dialogue"]), "%s.talk_dialogue" % name, None))
            for index, phase in enumerate(row.get("phases") or []):
                where = "%s.phases[%d]" % (name, index)
                out.append((("pattern", phase.get("pattern_id")), where + ".pattern_id", None))
                for field_name in ("talk_set", "line_id"):
                    out.append((("dialogue", phase.get(field_name)), "%s.%s" % (where, field_name), None))
                if phase.get("talk_phase"):
                    # A talk card is a row in its own file, matched on enemy id plus the phase string. It is not a
                    # node of this walk, so it is resolved here and named if no card claims the pair.
                    pair = (name, phase["talk_phase"])
                    if not any(card.get("enemy") == pair[0] and card.get("phase") == pair[1]
                               for card in self.talk_cards):
                        self._dangles.add((where + ".talk_phase", "talk_card", "%s/%s" % pair))
            # Card t_905a18ce (F3): the interruption is the enemy row's block (spec 18 section 4), so this is the arrow
            # from the fight to the scene the middle act plays. It used to be read off the encounter row, where no GML
            # looked and the checker did not refuse it.
            interrupt = row.get("interrupt") or {}
            if isinstance(interrupt, dict) and interrupt.get("scene"):
                scene = interrupt["scene"]
                if isinstance(scene, str):
                    out.append((("scene", scene), "%s.interrupt.scene" % name, None))
                elif isinstance(scene, dict):
                    for key in ROUTE_LABELS:
                        if scene.get(key):
                            out.append((("scene", scene[key]), "%s.interrupt.scene.%s" % (name, key), None))
        elif kind == "dialogue":
            self._dialogue_refs(self.dialogues[name], name, out)
        return out

    # -- the walk ---------------------------------------------------------------------------------------------

    def starts(self):
        """The slice entry, exactly as the card names it: its map and spawn, its opening scene, its first encounter.

        The route steps in data/slice.json are not walked here on purpose. They are tests/test_slice_route.py's to
        prove step by step, and that file measures them against the same rows; this walk starts where the player does.
        """
        entry = self.slice
        return [("map", entry.get("map")), ("scene", entry.get("scene")),
                ("encounter", entry.get("encounter"))]

    def walk(self):
        """Everything the slice can reach, to a fixed point, resolving every id on the way."""
        seen = set()
        for kind, name in self.starts():
            if self.resolve(kind, name, "data/slice.json"):
                seen.add((kind, name))
        changed = True
        while changed:
            changed = False
            for node in list(seen):
                for target, where, condition in self.edges(node):
                    if not self.resolve(target[0], target[1], where):
                        continue
                    if target not in seen:
                        seen.add(target)
                        changed = True
        return seen

    def path(self, start, goal):
        """The shortest chain of data references from one node to another, as (nodes, steps). [] when none exists."""
        parents = {start: None}
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node == goal:
                nodes, steps, cursor = [], [], node
                while cursor is not None:
                    nodes.append(cursor)
                    parent = parents[cursor]
                    if parent is not None:
                        steps.append(parent[1])
                    cursor = parent[0] if parent is not None else None
                nodes.reverse()
                steps.reverse()
                return nodes, steps
            for target, where, condition in self.edges(node):
                if target in parents or not self.resolve(target[0], target[1], where):
                    continue
                parents[target] = (node, where)
                queue.append(target)
        return [], []


@pytest.fixture(scope="module")
def story():
    return Story()


# ---------------------------------------------------------------------------------------------------------------
# Small readers over the data, so a check and its mutation test share one rule


def phase_rows(story):
    """(enemy id, index, phase row) for every phase row in the enemy table."""
    for enemy_id, row in sorted(story.enemies.items()):
        for index, phase in enumerate(row.get("phases") or []):
            yield enemy_id, index, phase


def unknown_phase_patterns(story):
    return ["%s.phases[%d] names pattern %r, which no pattern row carries"
            % (enemy_id, index, phase.get("pattern_id"))
            for enemy_id, index, phase in phase_rows(story)
            if not story.exists("pattern", phase.get("pattern_id"))]


def threshold_problems(story):
    """Strictly decreasing, and every threshold below the enemy's own max_hp: the first crossing must be a crossing."""
    problems = []
    for enemy_id, row in sorted(story.enemies.items()):
        thresholds = [phase.get("hp_at_or_below") for phase in row.get("phases") or []]
        if not thresholds:
            continue
        previous = row.get("max_hp")
        for index, value in enumerate(thresholds):
            if not isinstance(value, int) or isinstance(value, bool):
                problems.append("%s.phases[%d].hp_at_or_below is %r, not an integer" % (enemy_id, index, value))
                continue
            if not isinstance(previous, int):
                problems.append("%s has phases but no integer max_hp to be below" % enemy_id)
                break
            if value >= previous:
                problems.append("%s.phases[%d] is at %d hp, which is not below the %s before it"
                                % (enemy_id, index, value, previous))
            if value <= 0:
                problems.append("%s.phases[%d] is at %d hp, so the phase could never be entered alive"
                                % (enemy_id, index, value))
            previous = value
    return problems


def band_problems(story):
    """Every attack range a phase row raises, inside spec 07's boss band of 3 to 6.

    Only rows that carry phases are read, and their base range with them: the band belongs to the boss whose attack
    rises at a crossing (spec 07 health, and the enemies schema's PHASE_ATTACK_BAND note). A regular with attack 2 is
    the tutorial's number and is not this check's business.
    """
    problems = []
    for enemy_id, row in sorted(story.enemies.items()):
        if not row.get("phases"):
            continue
        ranges = [("attack", row.get("attack"))]
        ranges += [("phases[%d].attack" % index, phase.get("attack"))
                   for index, phase in enumerate(row.get("phases") or []) if phase.get("attack")]
        for where, band in ranges:
            if not isinstance(band, dict):
                problems.append("%s.%s is missing" % (enemy_id, where))
                continue
            low, high = band.get("min"), band.get("max")
            if not (isinstance(low, int) and isinstance(high, int)):
                problems.append("%s.%s is not two integers" % (enemy_id, where))
                continue
            if low > high:
                problems.append("%s.%s has min %d above max %d" % (enemy_id, where, low, high))
            if low < BOSS_ATTACK_MIN or high > BOSS_ATTACK_MAX:
                problems.append("%s.%s covers %d to %d, outside spec 07's %d to %d"
                                % (enemy_id, where, low, high, BOSS_ATTACK_MIN, BOSS_ATTACK_MAX))
    return problems


def reachable_hp(max_hp, damages):
    """Every hp value a sequence of whole blows can leave, alive. The kill window is one computation, not a guess."""
    seen = {max_hp}
    frontier = [max_hp]
    while frontier:
        hp = frontier.pop()
        for damage in damages:
            left = hp - damage
            if 0 < left and left not in seen:
                seen.add(left)
                frontier.append(left)
    return seen


def display_text(line):
    """The line as the box receives it: our two control codes removed, nothing else touched."""
    return CONTROL_CODE.sub("", line)


def wrapped(line, width=LINE_CHARS):
    """Word wrap, the spec 05 rule 4 way: a word that does not fit moves whole to the next line."""
    lines, current = [], ""
    for word in display_text(line).split(" "):
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def boxed_lines(story):
    """(dialogue id, one authored line) for every line the slice can show, in either shape."""
    for dialogue_id, row in story.dialogues.items():
        if "lines" in row:
            for line in row["lines"]:
                yield dialogue_id, line
        else:
            for page in row.get("pages") or []:
                for line in page.get("lines") or []:
                    yield dialogue_id, line


def route_of(document, stage, prison_stage):
    """Spec 10's table, in the order pp_ledger_route reads it: counters first, then the story stage."""
    counters = document["counters"]
    if counters["bosses_killed"] > 0:
        return "genocide"
    if counters["regulars_killed"] > 0:
        return "blooded"
    if stage >= prison_stage:
        return "mercy"
    return "undecided"


# ---------------------------------------------------------------------------------------------------------------
# 1. Percy's phases


def test_percy_carries_the_hp_spec_07_gives_him(story):
    percy = story.enemies["percy"]
    assert percy.get("route_kind") == "boss", "Percy is a boss row, which is what moves the boss counters"
    assert percy.get("max_hp") == PERCY_MAX_HP, "spec 07: Percy is %d hp, data says %r" % (PERCY_MAX_HP, percy.get("max_hp"))


def test_phase_thresholds_are_strictly_decreasing_and_below_max_hp(story):
    problems = threshold_problems(story)
    assert problems == [], problems
    # The one row the card asks about, named so a silent deletion is a failure and not an empty loop.
    thresholds = [phase["hp_at_or_below"] for phase in story.enemies["percy"].get("phases") or []]
    assert thresholds, "Percy carries no phases at all"
    previous = PERCY_MAX_HP
    for index, value in enumerate(thresholds):
        assert value < previous, "Percy phase %d at %d hp is not below the %d before it" % (index, value, previous)
        previous = value


def test_every_phase_pattern_id_exists_and_the_pool_is_three_shapes(story):
    problems = unknown_phase_patterns(story)
    assert problems == [], problems
    percy = story.enemies["percy"]
    pool = list(percy.get("patterns") or []) + [phase.get("pattern_id") for phase in percy.get("phases") or []]
    shapes = {}
    for pattern_id in pool:
        shapes[pattern_id] = story.patterns[pattern_id].get("shape")
    assert len(set(pool)) == 3, "spec 09: Percy's three attacks, data names %r" % sorted(set(pool))
    assert sorted(shapes.values()) == ["fan", "rain", "wall"], \
        "spec 09: Percy's three attacks are rain, wall and fan, data says %r" % sorted(shapes.values())


def test_the_phase_patterns_climb_the_spec_09_concurrency_ladder(story):
    percy = story.enemies["percy"]
    pool = [percy["patterns"][0]]
    pool += [phase["pattern_id"] for phase in percy.get("phases") or []]
    concurrency = []
    for pattern_id in pool:
        declared = story.patterns[pattern_id].get("max_concurrent")
        concurrency.append(declared)
        assert isinstance(declared, int) and 1 <= declared <= 4, "%s declares %r concurrent hazards" % (pattern_id, declared)
    # spec 09 acceptance 5: Percy's data shows 2, 3, 3 concurrent hazards, matching the ladder.
    assert concurrency[0] == 2, "the first pattern is the 2 hazard rung, data says %r" % concurrency[0]
    assert concurrency[-1] == 3, "the last pattern is the 3 hazard rung, data says %r" % concurrency[-1]
    assert concurrency == sorted(concurrency), "the ladder never comes back down: %r" % concurrency


def test_every_attack_range_stays_inside_the_spec_07_boss_band(story):
    problems = band_problems(story)
    assert problems == [], problems
    percy = story.enemies["percy"]
    bands = [percy["attack"]] + [phase["attack"] for phase in percy.get("phases") or [] if phase.get("attack")]
    lows = {band["min"] for band in bands}
    highs = {band["max"] for band in bands}
    assert BOSS_ATTACK_MIN in lows, "nothing in Percy's data reaches the band's floor of %d" % BOSS_ATTACK_MIN
    assert BOSS_ATTACK_MAX in highs, "nothing in Percy's data reaches the band's ceiling of %d" % BOSS_ATTACK_MAX


def test_the_last_phase_is_reachable_from_120_hp_with_the_fight_damage_band(story):
    percy = story.enemies["percy"]
    last = (percy.get("phases") or [])[-1]["hp_at_or_below"]
    damages = range(FIGHT_DAMAGE_MIN, FIGHT_DAMAGE_MAX + 1)
    reachable = reachable_hp(percy["max_hp"], damages)
    entered = sorted(hp for hp in reachable if hp <= last)
    assert entered, ("no sequence of FIGHT blows of %d to %d takes Percy from %d hp down to %d without dying first"
                     % (FIGHT_DAMAGE_MIN, FIGHT_DAMAGE_MAX, percy["max_hp"], last))
    assert min(entered) > 0, "the reachable set must exclude 0, or the phase would only fire on a corpse"
    # Named example, so the report can carry one: whole blows from 120 to the threshold.
    blows, hp = 0, percy["max_hp"]
    while hp > last:
        hp -= FIGHT_DAMAGE_MAX
        blows += 1
    assert hp > 0 and hp <= last, "the ceiling blow walks past the threshold into a corpse: %d hp" % hp
    print("Percy: %d hp, last phase at %d hp, reached by %d blows of %d, so %d hp is reachable"
          % (percy["max_hp"], last, blows, FIGHT_DAMAGE_MAX, hp))


def test_the_interrupt_threshold_sits_inside_the_gate_band(story):
    """Card t_905a18ce (F3): the block is read off the ENEMY row, which is the row the director reads.

    The threshold is a percent of max_hp (spec 18 section 4, P3), so it is compared in hp here against the card's own
    ceiling. The old version of this test read the encounter row and compared a percent to an hp number, which is how a
    dead copy of the block stayed green for a card.
    """
    percy = story.enemies["percy"]
    interrupt = percy.get("interrupt")
    assert isinstance(interrupt, dict), "the Percy enemy row carries no interrupt block (spec 18 section 4, C18-7)"
    threshold = interrupt.get("hp_at_or_below")
    assert isinstance(threshold, int) and not isinstance(threshold, bool), "the threshold is %r" % (threshold,)
    gate_hp = threshold * percy["max_hp"] // 100
    assert 0 < threshold < 100, "the threshold is a percent of max_hp, and %r is not one" % (threshold,)
    assert gate_hp <= INTERRUPT_CEILING, \
        "the card decided the interruption sits at or below %d hp, data says %d percent (%d hp)" % (
            INTERRUPT_CEILING, threshold, gate_hp)
    assert story.exists("flag", interrupt.get("unless_flag")), \
        "unless_flag %r is not a name in data/flags.json" % (interrupt.get("unless_flag"),)
    assert story.exists("scene", interrupt.get("scene")), \
        "interrupt.scene %r is not a scene row" % (interrupt.get("scene"),)
    spares = percy.get("spare_hp_percent")
    assert threshold > spares, "refusal 8: a gate at or below the spare line can never fire"
    print("Percy interrupt: at or below %d percent (%d hp) unless %s, scene %s; spare opens at %s percent"
          % (threshold, gate_hp, interrupt.get("unless_flag"), interrupt.get("scene"), spares))


def test_the_kill_window_is_measured_against_the_interrupt_trigger(story):
    """Measures the arithmetic the card's 'interrupted, spared and killed' claim rests on. It does not rule.

    Read off the enemy row (spec 18 section 4, C18-7), which is the row the director reads. With the trigger written as
    an hp crossing, a kill needs one blow from above the threshold all the way to 0. The biggest legal blow is 12. So a
    threshold above 12 makes the kill unreachable, whatever the ending's data says: that is spec 18 section 4's finding
    (A18-1) against this data, and it is printed here and reported on the card.
    """
    percy = story.enemies["percy"]
    interrupt = percy.get("interrupt") or {}
    threshold = interrupt.get("hp_at_or_below")
    trigger = interrupt.get("on") or "hp_crossing"
    assert isinstance(threshold, int) and threshold > 0
    crossing_kill = trigger == "hp_crossing" and threshold <= FIGHT_DAMAGE_MAX
    spare_refused_kill = trigger == "spare_refused"  # a player action below the threshold can always be answered
    print("interrupt trigger %r at %d percent, biggest FIGHT blow %d: crossing kill %s, refused spare kill %s"
          % (trigger, threshold, FIGHT_DAMAGE_MAX,
             "possible" if crossing_kill else "impossible", "possible" if spare_refused_kill else "impossible"))
    # What the data must at least do: name a trigger the two endings can be read against.
    assert trigger in ("hp_crossing", "spare_refused")


def test_the_phase_talk_set_line_and_card_all_resolve(story):
    for enemy_id, index, phase in phase_rows(story):
        for field_name in ("talk_set", "line_id"):
            assert story.exists("dialogue", phase.get(field_name)), \
                "%s.phases[%d].%s is %r, not a dialogue id" % (enemy_id, index, field_name, phase.get(field_name))
        if "talk_phase" in phase:
            pair = (enemy_id, phase["talk_phase"])
            claimed = [card for card in story.talk_cards
                       if card.get("enemy") == pair[0] and card.get("phase") == pair[1]]
            assert len(claimed) == 1, "%d talk cards claim enemy %r phase %r" % (len(claimed), pair[0], pair[1])


# ---------------------------------------------------------------------------------------------------------------
# 2. Reachability from the slice entry


def test_the_slice_entry_resolves(story):
    entry = story.slice
    map_row = story.maps.get(entry.get("map"))
    assert map_row is not None, "slice map %r is not a map row" % (entry.get("map"),)
    spawns = map_row.get("spawns") or {}
    assert entry.get("spawn") in spawns, "slice spawn %r is not a spawn on %s" % (entry.get("spawn"), entry.get("map"))
    assert entry.get("scene") in story.scenes, "slice scene %r is not a scene" % (entry.get("scene"),)
    assert entry.get("encounter") in story.encounters, "slice encounter %r is not an encounter" % (entry.get("encounter"),)


def test_no_id_the_slice_uses_dangles(story):
    reached = story.walk()
    problems = story.dangles()
    assert problems == [], "the walk crossed %d reference(s) that resolve nowhere: %s" % (len(problems), problems)
    assert reached, "the walk reached nothing at all"


def test_the_walk_reaches_every_table_the_slice_reads(story):
    reached = story.walk()
    for node in (BOARDING, SAILORS, PERCY, INTERRUPTION, ("enemy", "percy")):
        assert node in reached, "%s %r is not reachable from the slice entry" % node
    for kind in ("scene", "dialogue", "pattern", "flag", "map", "encounter", "enemy"):
        count = len([node for node in reached if node[0] == kind])
        assert count > 0, "the walk reached no %s at all" % kind
        print("reached %d %s row(s)" % (count, kind))


def test_the_path_from_boarding_through_sailors_and_percy_reaches_the_interruption(story):
    nodes, steps = [], []
    cursor = BOARDING
    for waypoint in (SAILORS, PERCY, INTERRUPTION):
        hop_nodes, hop_steps = story.path(cursor, waypoint)
        assert hop_nodes, "no chain of data references leads from %r to %r" % (cursor, waypoint)
        nodes.extend(hop_nodes if not nodes else hop_nodes[1:])
        steps.extend(hop_steps)
        cursor = waypoint
    assert nodes[0] == BOARDING and nodes[-1] == INTERRUPTION
    for waypoint in (SAILORS, PERCY):
        assert waypoint in nodes, "%r is not on the path: %r" % (waypoint, nodes)
    assert nodes.index(SAILORS) < nodes.index(PERCY) < nodes.index(INTERRUPTION), nodes
    print("path: " + " -> ".join("%s:%s" % node for node in nodes))
    print("steps: " + " -> ".join(steps))
    # The interruption has to be named by the fight, or the fight can never hand over to it.
    assert "percy.interrupt.scene" in steps, "no step names data/encounters/all.json percy.interrupt.scene"


def test_every_gate_the_data_names_is_a_flag(story):
    gates = []
    for map_id, row in story.maps.items():
        for trigger in row.get("triggers") or []:
            if trigger.get("condition"):
                gates.append((map_id + ".triggers.condition", trigger["condition"]))
    for scene_id, row in story.scenes.items():
        for command in row.get("commands") or []:
            if command.get("cmd") == "branch":
                gates.append((scene_id + ".branch", command.get("flag")))
    for dialogue_id, row in story.dialogues.items():
        for choice in row.get("choices") or []:
            if choice.get("condition"):
                gates.append((dialogue_id + ".choice.condition", choice["condition"]))
    for where, name in gates:
        assert story.exists("flag", name), "%s gates on %r, which is not a name in data/flags.json" % (where, name)
    reached = story.walk()
    # The negative gate is not a dependant: the interruption is enabled while its flag is unset, so the flag has to
    # be a settable name, not a reached dependant of another trigger. Card t_905a18ce (F3): read off the enemy row,
    # which is where the block lives and where pp_battle_interrupt_block looks.
    guards = [(enemy_id, (row.get("interrupt") or {}).get("unless_flag"))
              for enemy_id, row in story.enemies.items()]
    # The settable half is scoped to the gates that sit on content this walk reaches. A gate on a map the walk never
    # enters is still a name that has to exist (asserted above), but it cannot be settable "within the slice entry";
    # that is the route's business, and tests/test_slice_route.py walks the route steps. Anything dropped here is
    # counted and printed so a widening of the data can never silently fall out of the check.
    on_reached, off_reached = [], []
    for name, targets in story.dependants().items():
        if any(node in reached for node, _where, _condition in targets):
            on_reached.append(name)
        else:
            off_reached.append(name)
    for name in sorted(set(on_reached)):
        assert ("flag", name) in reached, "flag %r gates content the slice reaches, but nothing it reaches sets it" % (name,)
    assert on_reached, "no gate sits on any reached node, so the settable half of this check proved nothing"
    for enemy_id, guard in guards:
        if guard:
            assert story.exists("flag", guard), "%s.interrupt.unless_flag %r is not a name in data/flags.json" % (
                enemy_id, guard)
    print("gates: %d named in the data, all in data/flags.json; %d gate reached content and are all set by it: %r;"
          " %d gate content outside the slice entry (the route's, not this walk's): %r"
          % (len(gates), len(set(on_reached)), sorted(set(on_reached)), len(set(off_reached)), sorted(set(off_reached))))
    print("negative guards: %r" % [guard for _, guard in guards if guard])


def test_the_flag_that_disables_a_second_interruption_is_set_by_the_interrupt_scene(story):
    """Card t_905a18ce (F3): the guard is read from the enemy row, the block the director reads."""
    percy = story.enemies["percy"]
    block = percy.get("interrupt") or {}
    guard = block.get("unless_flag")
    assert guard, "the interruption carries no unless_flag, so it could fire twice in one fight"
    scene_id = block.get("scene")
    assert isinstance(scene_id, str), "the shipped row names one scene id, so this test can name it"
    scene = story.scenes[scene_id]
    set_flags = [command.get("name") for command in scene.get("commands") or []
                 if command.get("cmd") == "setflag" and command.get("value") is True]
    assert guard in set_flags, "the scene that plays on interruption never sets %r, so it would fire again" % guard
    print("interruption guard %r is set by scene %r" % (guard, scene_id))


# ---------------------------------------------------------------------------------------------------------------
# 3. The endings


def test_both_percy_endings_carry_their_dialogue_and_their_flag(story):
    encounter = story.encounters["percy"]
    pairs = (("win_dialogue_kill", "flags_on_kill"), ("win_dialogue_spare", "flags_on_spare"))
    seen_flags = []
    for dialogue_field, flag_field in pairs:
        dialogue_id = encounter.get(dialogue_field)
        assert dialogue_id in story.dialogues, "%s names %r, not a dialogue id" % (dialogue_field, dialogue_id)
        flags = encounter.get(flag_field) or []
        assert len(flags) == 1, "%s must write exactly one flag, data says %r" % (flag_field, flags)
        assert flags[0] in story.flags, "%s names %r, not a name in data/flags.json" % (flag_field, flags[0])
        seen_flags.append(flags[0])
        rows = story.dialogues[dialogue_id]
        lines = rows.get("lines") or [line for page in rows.get("pages") or [] for line in page.get("lines") or []]
        assert lines, "the ending dialogue %r has no lines" % dialogue_id
        print("%s: dialogue %r, flag %r, %d line(s)" % (dialogue_field, dialogue_id, flags[0], len(lines)))
    assert seen_flags[0] != seen_flags[1], "kill and spare write the same flag, so the epilogue cannot tell them apart"


def test_the_epilogue_branches_on_the_kill_flag(story):
    encounter = story.encounters["percy"]
    epilogue = story.scenes.get(encounter.get("epilogue_scene"))
    assert epilogue is not None, "epilogue_scene %r is not a scene row" % (encounter.get("epilogue_scene"),)
    branches = [command for command in epilogue.get("commands") or [] if command.get("cmd") == "branch"]
    assert len(branches) == 1, "the epilogue must branch exactly once, data has %d" % len(branches)
    kill_flag = (encounter.get("flags_on_kill") or [None])[0]
    assert branches[0].get("flag") == kill_flag, \
        "the epilogue branches on %r, but the kill path writes %r" % (branches[0].get("flag"), kill_flag)
    target = branches[0].get("scene")
    assert target in story.scenes, "the epilogue branch target %r is not a scene" % (target,)
    assert story.scenes[target].get("commands"), "the kill variant scene %r has no commands" % (target,)


def test_the_interrupted_ending_plays_the_prometheus_scene_and_leaves_percy_standing(story):
    """Card t_905a18ce (F3): the scene id is the ENEMY row's, and it is the odd one out only in where it is written."""
    block = story.enemies["percy"].get("interrupt") or {}
    scene = story.scenes.get(block.get("scene"))
    assert scene is not None, "interrupt.scene %r is not a scene row" % (block.get("scene"),)
    said = [command.get("id") for command in scene.get("commands") or [] if command.get("cmd") == "say"]
    assert len(said) >= 2, "the interruption shows %d dialogue entries; it needs Percy's line and Prometheus's" % len(said)
    speakers = {story.dialogues[dialogue_id]["speaker"] for dialogue_id in said}
    assert "percy" in speakers, "Percy does not speak in his own interruption: %r" % sorted(speakers)
    assert "prometheus" in speakers, "Prometheus never speaks, so the veil is never explained: %r" % sorted(speakers)
    set_flags = {command.get("name"): command.get("value") for command in scene.get("commands") or []
                 if command.get("cmd") == "setflag"}
    assert set_flags.get("met_prometheus") is True, "the scene never sets met_prometheus"
    assert set_flags.get("percy_standing") is True, "the scene never records that Percy is left standing"
    assert scene.get("commands")[-1].get("cmd") == "end", \
        "the interruption must end, or control never returns to the overworld"
    music = [command.get("id") for command in scene.get("commands") or [] if command.get("cmd") == "music"]
    assert music, "the interruption changes nothing musically; PP-07 is owed by the card"
    print("interruption scene %r: %d say, flags %r, music %r"
          % (block.get("scene"), len(said), sorted(set_flags), music))


def test_each_ending_writes_its_row_and_only_kill_and_spare_move_a_counter(story):
    percy = story.enemies["percy"]
    assert percy.get("route_kind") == "boss"
    for result, expected_exit, counter in (("kill", ledger.DOWN, "bosses_killed"),
                                           ("spare", ledger.SPARED, "bosses_spared"),
                                           ("interrupt", ledger.TURNED, None)):
        battle = ledger.new_ledger()
        ledger.begin_fight(battle)
        ledger.record_exit(battle, "percy", percy["route_kind"], result, 3)
        assert len(battle["exits"]) == 1, "%s left %d rows" % (result, len(battle["exits"]))
        row = battle["exits"][0]
        assert row["id"] == "percy" and row["exit"] == expected_exit and row["round"] == 3, row
        if counter is None:
            assert sum(battle["counters"].values()) == 0, \
                "a turned enemy moved a counter: %r (spec 10 rule 7)" % battle["counters"]
            assert battle["verdict"] == ledger.QUIET, "one turned row must read quiet, got %r" % battle["verdict"]
        else:
            assert battle["counters"][counter] == 1, "%s did not move %s: %r" % (result, counter, battle["counters"])
            assert sum(battle["counters"].values()) == 1, "one row moved more than one counter: %r" % battle["counters"]


def test_the_route_is_derived_from_the_counters_and_never_stored(story):
    prison_stage = story.project.get("prison_stage")
    assert isinstance(prison_stage, int), "data/project.json carries no prison_stage"
    assert tuple(story.project.get("route_labels") or ()) == ROUTE_LABELS, \
        "spec 10's four routes are %r, project.json says %r" % (ROUTE_LABELS, story.project.get("route_labels"))

    # The mirror's four cases, one per row of spec 10's table.
    fresh = ledger.new_ledger()
    assert route_of(fresh, 0, prison_stage) == "undecided"
    assert route_of(fresh, prison_stage, prison_stage) == "mercy"
    regular = ledger.new_ledger()
    ledger.record_exit(regular, "navy_sailor", "regular", "kill", 1)
    assert route_of(regular, prison_stage, prison_stage) == "blooded"
    boss = ledger.new_ledger()
    ledger.record_exit(boss, "percy", "boss", "kill", 1)
    assert route_of(boss, prison_stage, prison_stage) == "genocide"

    # A spared or turned Percy leaves the route where it was: mercy, not genocide.
    spared = ledger.new_ledger()
    ledger.record_exit(spared, "percy", "boss", "spare", 1)
    ledger.record_exit(spared, "percy", "boss", "interrupt", 2)
    assert route_of(spared, prison_stage, prison_stage) == "mercy", "a spare or a turned enemy moved the route"

    # Derived, not stored: the ledger struct has no route, and the save snapshot carries none either.
    assert "route" not in fresh, "the ledger carries a stored route: %r" % sorted(fresh)
    saved = ledger.snapshot_exits(fresh)
    for row in saved:
        assert set(row) == {"id", "exit", "round"}, "a saved exit row carries an extra field: %r" % sorted(row)

    # The mirror is the GML's order, not this file's invention.
    body = ledger.function_body(ledger.read_code(ledger.LEDGER_GML), "pp_ledger_route")
    boss_first = body.index("counters.bosses_killed > 0")
    regular_next = body.index("counters.regulars_killed > 0")
    stage_last = body.index("_ledger.stage >= _prison_stage")
    assert boss_first < regular_next < stage_last, "pp_ledger_route no longer reads counters then stage in order"
    code = ledger.read_code(ledger.LEDGER_GML)
    assert "_ledger.route" not in code, "a route is being written into the ledger, which spec 10 refuses"
    print("route mirror pinned to pp_ledger_route; prison_stage %d" % prison_stage)


def test_the_spare_refusal_names_a_real_route(story):
    encounter = story.encounters["percy"]
    rule = encounter.get("spare_refuses_on_route")
    assert rule in ROUTE_LABELS, "spare_refuses_on_route is %r, not one of spec 10's routes" % (rule,)
    # The rule only bites where killing Percy is what produces that route, which the mirror shows it does.
    boss = ledger.new_ledger()
    ledger.record_exit(boss, "percy", "boss", "kill", 1)
    assert route_of(boss, 0, story.project["prison_stage"]) == rule, \
        "the encounter refuses SPARE on %r, but killing Percy derives %r" % (rule, route_of(boss, 0, story.project["prison_stage"]))


# ---------------------------------------------------------------------------------------------------------------
# 4. Text fits the box


def test_every_dialogue_line_fits_the_spec_05_box(story):
    worst_shorthand = 0
    for dialogue_id, row in story.dialogues.items():
        if "lines" in row:
            assert "pages" not in row, "%r carries both shapes" % dialogue_id
            total = []
            for line in row["lines"]:
                for word in display_text(line).split(" "):
                    assert len(word) <= LINE_CHARS, \
                        "%r has the word %r, %d characters, longer than the %d character line it cannot wrap out of" \
                        % (dialogue_id, word, len(word), LINE_CHARS)
                total.extend(wrapped(line))
            assert len(total) <= PAGES * PAGE_LINES, \
                "%r wraps to %d lines, more than the %d the box holds" % (dialogue_id, len(total), PAGES * PAGE_LINES)
            worst_shorthand = max(worst_shorthand, len(total))
        else:
            pages = row.get("pages") or []
            assert 1 <= len(pages) <= PAGES, "%r carries %d pages" % (dialogue_id, len(pages))
            for page_index, page in enumerate(pages):
                lines = page.get("lines") or []
                assert 1 <= len(lines) <= PAGE_LINES, \
                    "%r page %d carries %d lines" % (dialogue_id, page_index, len(lines))
                for line in lines:
                    shown = display_text(line)
                    assert len(shown) <= LINE_CHARS, \
                        "%r page %d has a %d character line: %r" % (dialogue_id, page_index, len(shown), shown)
                    for word in shown.split(" "):
                        assert len(word) <= LINE_CHARS, "%r page %d has the word %r, too long to wrap" % (
                            dialogue_id, page_index, word)
    assert worst_shorthand <= PAGES * PAGE_LINES
    print("dialogue: %d entries, longest shorthand entry wraps to %d of %d lines"
          % (len(story.dialogues), worst_shorthand, PAGES * PAGE_LINES))


def test_no_control_code_other_than_pause_and_speed_reaches_the_box(story):
    for dialogue_id, line in boxed_lines(story):
        shown = display_text(line)
        assert "{" not in shown and "}" not in shown, \
            "%r carries a brace the engine would print literally: %r" % (dialogue_id, line)


def test_todo_name_placeholders_are_listed_by_dialogue_id(story):
    """The card asks Nayil to see exactly what is unnamed, so this prints the list rather than only counting it."""
    found = []
    others = []
    for dialogue_id, line in boxed_lines(story):
        for match in PLACEHOLDER.finditer(line):
            found.append((dialogue_id, match.group(0)))
        for match in ANY_TODO.finditer(display_text(line)):
            if not match.group(0).startswith("TODO_NAME_"):
                others.append((dialogue_id, match.group(0)))
    for dialogue_id, token in found:
        tail = token[len("TODO_NAME_"):]
        assert tail != "", "%r carries the bare marker %r with nothing named after it" % (dialogue_id, token)
    assert others == [], "a placeholder under a different prefix: %r" % others
    if found:
        print("TODO_NAME_ placeholders (%d):" % len(found))
        for dialogue_id, token in found:
            print("  %s: %s" % (dialogue_id, token))
    else:
        print("TODO_NAME_ placeholders: none. Every line in data/dialogue/all.json names its speaker outright.")
    assert isinstance(found, list)


def test_no_long_dash_reaches_the_slice_text(story):
    for relative in ("dialogue/all.json", "scenes/all.json", "enemies/all.json", "encounters/all.json"):
        text = _raw(os.path.join(story.root, "data", relative))
        for codepoint in LONG_DASHES:
            assert codepoint not in text, "data/%s carries %r" % (relative, codepoint)


# ---------------------------------------------------------------------------------------------------------------
# 5. The pattern recipes, through the checker's own simulation


def test_every_phase_pattern_simulates_deterministically_and_ends(story):
    """The checker's simulate() is the engine's rules a second time; this reuses it and adds the determinism claim."""
    percy = story.enemies["percy"]
    ids = [percy["patterns"][0]] + [phase["pattern_id"] for phase in percy.get("phases") or []]
    encounter_seed = story.encounters["percy"].get("seed")
    assert isinstance(encounter_seed, int) and encounter_seed >= 0
    for pattern_id in ids:
        pattern = story.patterns[pattern_id]
        first = check_data.simulate(pattern, seed=1)
        second = check_data.simulate(pattern, seed=1)
        assert first == second, "%s is not deterministic with one seed: %r then %r" % (pattern_id, first, second)
        traced_first = check_data.simulate(pattern, seed=1, trace=True)["paths"]
        traced_second = check_data.simulate(pattern, seed=1, trace=True)["paths"]
        assert traced_first == traced_second, "%s puts its hazards in different places on a replay" % pattern_id
        assert first["finished"], "%s does not end inside the %d step cap" % (pattern_id, check_data.ARENA_CAP)
        assert first["exclusion_violations"] == 0, \
            "%s spawned %d hazard(s) inside the %d px exclusion" % (
                pattern_id, first["exclusion_violations"], check_data.SPAWN_EXCLUSION)
        assert first["peak"] <= pattern["max_concurrent"], \
            "%s peaks at %d concurrent hazards, declares %d" % (pattern_id, first["peak"], pattern["max_concurrent"])
        assert first["spawns"] > 0, "%s spawns nothing" % pattern_id
        # The fight's own seed replays the same shapes as seed 1 does, and still ends: the seed moves the origins.
        with_seed = check_data.simulate(pattern, seed=encounter_seed)
        assert with_seed["finished"] and with_seed["exclusion_violations"] == 0, \
            "%s does not hold up on the fight's own seed %d: %r" % (pattern_id, encounter_seed, with_seed)
        print("%-12s seed 1: spawns %2d peak %d steps %3d | fight seed %d: steps %3d"
              % (pattern_id, first["spawns"], first["peak"], first["steps"], encounter_seed, with_seed["steps"]))


def test_the_simulation_is_the_checkers_and_the_checker_passes(story):
    assert check_data.simulate.__module__ == "check_data", "the simulation must be the checker's, not a copy"
    assert check_data.check(str(story.root)) == [], "tools/check_data.py does not pass over the tree under test"


# ---------------------------------------------------------------------------------------------------------------
# 6. The mutations: the checks above fail on purpose, on a copy


def test_mutation_an_unknown_phase_pattern_is_refused_here(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    document = read_json(path)
    percy = [row for row in document["enemies"] if row.get("id") == "percy"][0]
    assert percy["phases"], "the fixture no longer carries a phase row to mutate"
    percy["phases"][0]["pattern_id"] = "percy_tsunami"
    write_json(path, document)

    mutated = Story(str(data_root))
    problems = unknown_phase_patterns(mutated)
    assert problems, "a phase naming a pattern id that does not exist was accepted"
    assert any("percy_tsunami" in problem for problem in problems), problems
    mutated.walk()
    assert any(dangle[2] == "percy_tsunami" for dangle in mutated.dangles()), \
        "the walk did not record the unknown pattern id: %r" % (mutated.dangles(),)
    # The real data is untouched.
    assert unknown_phase_patterns(Story()) == []


def test_mutation_a_removed_spare_dialogue_is_refused_here_and_by_the_checker(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    document = read_json(path)
    before = len(document["dialogue"])
    document["dialogue"] = [row for row in document["dialogue"] if row.get("id") != "percy_win_spare"]
    assert len(document["dialogue"]) == before - 1, "the fixture no longer carries percy_win_spare"
    write_json(path, document)

    mutated = Story(str(data_root))
    encountered = story_failures(mutated)
    assert encountered, "removing the spare dialogue did not break the ending"
    assert any("percy_win_spare" in problem for problem in encountered), encountered
    mutated.walk()
    assert any(dangle[1] == "dialogue" and dangle[2] == "percy_win_spare" for dangle in mutated.dangles()), \
        "the walk did not notice the missing spare dialogue: %r" % (mutated.dangles(),)

    errors = check_data.check(str(data_root))
    assert any("percy_win_spare" in error for error in errors), \
        "tools/check_data.py no longer names the removed spare dialogue: %r" % (errors[:5],)


def test_the_checker_refuses_an_interrupt_on_an_encounter_row(data_root, read_json, write_json):
    """Spec 18 section 7 refusal 10, which card t_905a18ce (F3) implemented: the enemy row owns the block.

    The pin this replaces recorded the opposite, that nothing refused the encounter copy, and it was right for as long
    as the checker had no such rule. The copy is gone from the data and the rule is here now, so the pin is inverted
    rather than deleted: a future encounter level interrupt has to fail the gate, not pass it in silence.
    """
    enemies_path = data_root / "data" / "enemies" / "all.json"
    enemies = read_json(enemies_path)
    percy = [row for row in enemies["enemies"] if row.get("id") == "percy"][0]
    percy["phases"][0]["pattern_id"] = "percy_tsunami"
    write_json(enemies_path, enemies)

    encounters_path = data_root / "data" / "encounters" / "all.json"
    encounters = read_json(encounters_path)
    row = [item for item in encounters["encounters"] if item.get("id") == "percy"][0]
    row["interrupt"] = {"hp_at_or_below": 60, "unless_flag": "met_prometheus", "scene": "prometheus_interupt"}
    write_json(encounters_path, encounters)

    errors = check_data.check(str(data_root))
    refused = [error for error in errors
               if "data/encounters/all.json" in error and error.split(":")[1].strip().endswith(".interrupt")]
    assert refused, "the checker no longer refuses an interrupt on an encounter row: %r" % (errors[:8],)
    assert "refusal 10" in refused[0], refused
    assert any("percy_tsunami" in error for error in errors), \
        "the checker no longer refuses a phase row's unknown pattern_id, which card t_d1eb2a47 added"

    # And the scene id a bad row names is caught too, on the same copy, so refusal 10 is not doing refusal 7's work.
    assert not any("prometheus_interupt" in error for error in errors), \
        ("the encounter copy's scene id is judged by refusal 10 and nothing else: %r" % (errors,))

    # The net this file keeps: the walk still names the ids it crosses, and the corrupted encounter copy is not one.
    mutated = Story(str(data_root))
    problems = unknown_phase_patterns(mutated)
    assert any("percy_tsunami" in problem for problem in problems), problems
    mutated.walk()
    dangling = {(kind, name) for _, kind, name in mutated.dangles()}
    assert ("pattern", "percy_tsunami") in dangling, mutated.dangles()
    assert ("scene", "prometheus_interupt") not in dangling, \
        "the walk still follows the encounter copy, so it can see an id the build never reads"


def test_an_unknown_interrupt_scene_on_the_enemy_row_is_refused(data_root, read_json, write_json):
    """Refusal 7 on the row the director reads: the scene id is resolved, not printed."""
    enemies_path = data_root / "data" / "enemies" / "all.json"
    enemies = read_json(enemies_path)
    percy = [row for row in enemies["enemies"] if row.get("id") == "percy"][0]
    percy["interrupt"]["scene"] = "prometheus_interupt"
    write_json(enemies_path, enemies)

    errors = check_data.check(str(data_root))
    assert any("prometheus_interupt" in error for error in errors), errors
    mutated = Story(str(data_root))
    mutated.walk()
    assert ("scene", "prometheus_interupt") in {(kind, name) for _, kind, name in mutated.dangles()}, \
        mutated.dangles()


def story_failures(story):
    """The ending checks as a list of strings, so a mutation can call the same rule the tests above assert."""
    problems = []
    encounter = story.encounters.get("percy") or {}
    for field_name in ("win_dialogue_kill", "win_dialogue_spare", "intro_dialogue"):
        dialogue_id = encounter.get(field_name)
        if dialogue_id not in story.dialogues:
            problems.append("data/encounters/all.json percy.%s names %r, which is not a dialogue id"
                            % (field_name, dialogue_id))
    for field_name in ("flags_on_kill", "flags_on_spare"):
        for flag_name in encounter.get(field_name) or []:
            if flag_name not in story.flags:
                problems.append("data/encounters/all.json percy.%s names %r, which is not a flag"
                                % (field_name, flag_name))
    return problems


def test_the_ending_failures_helper_passes_on_the_real_data(story):
    assert story_failures(story) == [], story_failures(story)
