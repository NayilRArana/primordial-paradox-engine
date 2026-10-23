"""G0-4c: every ending of both early fights is reachable, and each one has its epilogue.

Card t_801681a4, the third third of the split ruled in D4 of `knowledge/GAMEDEV-DECISIONS-2026-10-23.md`. The sources
are specs/07-battle-director.md (SPARE is enabled at trust 3 or at enemy hp of 25 percent or less), specs/10-route-ledger.md
(the genocide route, and SPARE refused on it), and specs/18-boss-phases.md sections 4 and 8 (the interruption is the
Percy path's refusal).

What this file holds down, and why each one earns its place:

  1. the four outcome rows `percy_win_spare`, `percy_win_kill`, `navy_win_spare` and `navy_win_kill` each exist, carry
     lines, and are the ids the two encounter rows name. A fight that ends on a missing id prints fallback text and the
     ending is lost, which no playtest would attribute to the data;
  2. each of the four endings is DRIVEN to its end here: FIGHT down to 0 hp for the two kills, three TALKs then SPARE for
     Percy, and FIGHT down to the 25 percent floor then SPARE for the navy sailor. The drive goes through the director's
     own spare gate and its own damage formula reimplemented from pp_config.gml and party.json, not through a constant
     this file keeps;
  3. each ending writes exactly one distinguishing flag and takes a conditional epilogue: `percy_aftermath` branches on
     `percy_killed` and falls through to the spare set, `navy_aftermath` branches on `sailor_killed` the same way. The
     kill and spare epilogue rows are different sets of lines, so the epilogue can tell the endings apart;
  4. the spare refusal is visible on the genocide route, in the two shapes the data has and the code now reads
     (card t_905a18ce F4: `spare_refuses_on_route` was read by no GML before this card). Percy's refused SPARE below his
     40 percent gate hands the fight to `prometheus_interrupt` (the G0-4b interruption, where his own refusal line
     plays); above it, and at the spare line itself, the entry is refused with the route's own reason text, which is
     the second shape of visible refusal (spec 07 rule 1: a disabled entry draws its reason, makes a low blip, and
     never silently no-ops);
  5. the mutation cases at the bottom remove the refusal line, point an outcome row at a missing id and point an epilogue
     branch at the wrong flag, so the checks above are measurements and can fail.

Known gaps, recorded rather than hidden:
  - no GML is executed. GameMaker is not installed on this host, so the driver below is a mirror of the menu and of the
    director. The menu's own spare case, the director's spare gate, its order (spare first, then the interruption), its
    outcome words and its result dialogue branches are pinned text for text from the GML, so the mirror cannot silently
    drift from it;
  - nothing in the build reads `epilogue_scene` or `spare_refused_dialogue` yet: pp_overworld_battle_finished writes the
    outcome flags and returns to the map, and the route refusal is a reason drawn at the menu rather than a typed line.
    Both rows are data and their reachability is proven here; the caller wiring for the epilogue is a named gap, and the
    interruption scene's own handover is the one G0-4R did wire (card t_905a18ce F2).

Run: python -m pytest tests/test_fight_endings.py -q
Headless probe: python tests/test_fight_endings.py
"""

from __future__ import annotations

import json
import math
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENEMIES = os.path.join(ROOT, "data", "enemies", "all.json")
ENCOUNTERS = os.path.join(ROOT, "data", "encounters", "all.json")
SCENES = os.path.join(ROOT, "data", "scenes", "all.json")
DIALOGUE = os.path.join(ROOT, "data", "dialogue", "all.json")
FLAGS = os.path.join(ROOT, "data", "flags.json")
PARTY = os.path.join(ROOT, "data", "characters", "party.json")
PROJECT = os.path.join(ROOT, "data", "project.json")
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
DIRECTOR_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
COMMANDS_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")

NAVY = "tutorial_sailors"
PERCY = "percy"

# The four outcome ids this card is about, and the fight each one belongs to.
OUTCOMES = ((PERCY, "kill", "percy_win_kill"), (PERCY, "spare", "percy_win_spare"),
            (NAVY, "kill", "navy_win_kill"), (NAVY, "spare", "navy_win_spare"))

# The route a fight happens on when the player has already killed a boss (spec 10), which is what makes the refusal
# reachable data rather than a hypothetical.
GENOCIDE = "genocide"

LONG_DASHES = ("\u2014", "\u2013", "\u2015", "\u2212")


# ------------------------------------------------------------------------------------------------- reading the data


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    return json.loads(_read(path))


def find_row(document: dict, collection: str, row_id: str) -> dict:
    rows = document.get(collection) or []
    found = [row for row in rows if row.get("id") == row_id]
    assert len(found) == 1, "expected one %s row %r, found %d" % (collection, row_id, len(found))
    return found[0]


def by_id(document: dict, collection: str) -> dict:
    return {row["id"]: row for row in document[collection]}


def macro(text: str, name: str) -> int:
    match = re.search(r"^#macro\s+%s\s+(-?\d+)\s*$" % re.escape(name), text, re.M)
    assert match, "no numeric #macro %s in pp_config.gml" % name
    return int(match.group(1))


def code_only(text: str) -> str:
    return "\n".join(line.split("//")[0] for line in text.split("\n"))


def function_body(text: str, name: str) -> str:
    start = text.index("function %s(" % name)
    open_index = text.index("{", start)
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index:index + 1]
    raise AssertionError("unbalanced block after %r" % name)


def lines_of(row: dict) -> list:
    if "lines" in row:
        return list(row["lines"])
    return [line for page in row.get("pages") or [] for line in page.get("lines") or []]


# ------------------------------------------------------------------------------- the director's own numbers, mirrored


class Data(object):
    """Everything this file reads once, so a test never reloads a file the probe already has."""

    def __init__(self):
        self.enemies = by_id(_load(ENEMIES), "enemies")
        self.encounters = by_id(_load(ENCOUNTERS), "encounters")
        self.scenes = by_id(_load(SCENES), "scenes")
        self.dialogues = by_id(_load(DIALOGUE), "dialogue")
        self.flags = set(_load(FLAGS)["flags"])
        self.hero = find_row(_load(PARTY), "characters", "hero")
        self.project = _load(PROJECT)
        config = _read(CONFIG_GML)
        self.fight_min = macro(config, "PP_FIGHT_DAMAGE_MIN")
        self.fight_max = macro(config, "PP_FIGHT_DAMAGE_MAX")
        self.multiplier = self.hero["power_multiplier"]

    def enemy_of(self, encounter_id: str) -> dict:
        return self.enemies[self.encounters[encounter_id]["enemies"][0]]

    def fight_damage(self, power: int) -> int:
        """pp_battle_fight_damage from its own body: clamp, the band, the actor multiplier, floor 1."""
        p = max(0, min(100, power))
        raw = self.fight_min + (self.fight_max - self.fight_min) * (p / 100)
        return max(1, int(math.floor(raw * self.multiplier + 0.5)))

    def route_of(self, counters: dict, stage: int) -> str:
        """pp_ledger_route, in its own order: boss kills, then regular kills, then the story stage."""
        if counters["bosses_killed"] > 0:
            return "genocide"
        if counters["regulars_killed"] > 0:
            return "blooded"
        if stage >= self.project["prison_stage"]:
            return "mercy"
        return "undecided"


def new_counters() -> dict:
    return {"bosses_killed": 0, "bosses_spared": 0, "regulars_killed": 0, "regulars_spared": 0}


class Fight(object):
    """A headless mirror of one fight: the hp, the trust, the exit row it would write, and the flags it would set."""

    def __init__(self, data: Data, encounter_id: str, stage: int = 0, routed_counters=None):
        self.data = data
        self.encounter_id = encounter_id
        self.encounter = data.encounters[encounter_id]
        self.enemy = data.enemy_of(encounter_id)
        self.hp = self.enemy["max_hp"]
        self.trust = 0
        self.stage = stage
        self.counters = routed_counters or new_counters()
        self.outcome = None
        self.exit = None
        self.flags = set()
        self.events = []

    # pp_battle_spare_allowed
    def spare_allowed(self) -> bool:
        if self.hp <= 0:
            return False
        if self.trust >= self.enemy["trust_to_spare"]:
            return True
        return self.hp * 100 <= self.enemy["spare_hp_percent"] * self.enemy["max_hp"]

    # pp_battle_interrupt_ready
    def interrupt_ready(self) -> bool:
        if self.hp <= 0 or self.spare_allowed():
            return False
        block = self.enemy.get("interrupt")
        if not isinstance(block, dict):
            return False
        if block.get("on") != "spare_refused":
            return False
        if block.get("unless_flag") and block["unless_flag"] in self.flags:
            return False
        if "hp_at_or_below" not in block:
            return False
        return self.hp * 100 <= block["hp_at_or_below"] * self.enemy["max_hp"]

    def interrupt_scene(self) -> str:
        block = self.enemy.get("interrupt") or {}
        scene = block.get("scene")
        if isinstance(scene, str):
            return scene
        if isinstance(scene, dict):
            return scene.get(self.route()) or ""
        return ""

    # pp_battle_route_name: the route, derived on read from the counters and the story stage (spec 10, never stored).
    def route(self) -> str:
        return self.data.route_of(self.counters, self.stage)

    # pp_battle_spare_route_refused: the encounter row's own refusal, on the derived route (card t_905a18ce F4).
    def route_refused(self) -> bool:
        return self.encounter.get("spare_refuses_on_route") == self.route()

    # pp_command_state's SPARE case: the interruption first, then the route, then the spare gate. Card t_905a18ce (F1)
    # is the reason the interruption is asked first: the entry has to be pressable across the whole gate window.
    def command_state(self):
        if self.interrupt_ready():
            return (True, "")
        if self.route_refused():
            return (False, "no mercy left on this route")
        if not self.spare_allowed():
            return (False, "not ready to end it")
        return (True, "")

    def fight(self, power: int = 100) -> int:
        damage = self.data.fight_damage(power)
        self.hp = max(0, self.hp - damage)
        self.events.append(("fight", damage))
        if self.hp <= 0 and self.outcome is None:
            self._end("kill")
        return damage

    def talk(self) -> int:
        self.trust += self.encounter["trust_per_talk"]
        self.events.append(("talk", self.trust))
        return self.trust

    def press_spare(self):
        """The menu entry and then the director's SPARE case, which is the path the engine takes.

        Card t_905a18ce (F1 and F4): the press is resolved through pp_command_state's mirror first, so a disabled entry
        comes back as `refused` with the reason the menu would draw, and the route refusal is answered here the way the
        menu answers it. Returns (kind, reference) where reference is the scene id, the refusal dialogue id, or the
        disabled entry's reason.
        """
        self.events.append(("spare", self.hp))
        enabled, reason = self.command_state()
        if not enabled:
            # Spec 07 rule 1: a refused entry is visible, makes a sound and never advances the turn.
            return ("refused", reason)
        if self.spare_allowed() and not self.route_refused():
            self.hp = 0
            self._end("spare")
            return ("spare", self.encounter["win_dialogue_spare"])
        if self.interrupt_ready():
            self._end("interrupt")
            return ("interrupt", self.interrupt_scene())
        return ("refused", "not ready to end it")

    def _end(self, outcome: str) -> None:
        self.outcome = outcome
        self.exit = {"kill": "down", "spare": "spared", "interrupt": "turned"}[outcome]
        if outcome in ("kill", "spare"):
            prefix = "bosses_" if self.enemy["route_kind"] == "boss" else "regulars_"
            self.counters[prefix + ("killed" if outcome == "kill" else "spared")] += 1
        field_name = {"kill": "flags_on_kill", "spare": "flags_on_spare"}.get(outcome)
        if field_name:
            self.flags.update(self.encounter.get(field_name) or [])


def run_epilogue(data: Data, scene_id: str, flags: set) -> list:
    """Run a scene's commands the way pp_scene does far enough to say which dialogue set it took.

    `branch` re-enters the target scene in place, which is what pp_scene_take_scene does, so a branch is followed
    once and the target's own commands run from their start.
    """
    trace = []
    current = scene_id
    commands = list(data.scenes[current]["commands"])
    index = 0
    guard = 0
    while index < len(commands):
        guard += 1
        assert guard < 256, "the epilogue never ends: %r" % trace
        command = commands[index]
        kind = command["cmd"]
        if kind == "say":
            trace.append((kind, command["id"]))
            index += 1
        elif kind == "branch":
            if command["flag"] in flags:
                trace.append((kind, command["scene"]))
                current = command["scene"]
                commands = list(data.scenes[current]["commands"])
                index = 0
            else:
                index += 1
        elif kind == "end":
            trace.append((kind, ""))
            break
        else:
            raise AssertionError("the epilogue commands may only say, branch or end; found %r" % kind)
    else:
        raise AssertionError("the epilogue %r has no end command" % scene_id)
    return trace


def ending_of(data: Data, fight: Fight):
    """(outcome word, outcome dialogue id, epilogue scene path, epilogue dialogue id) for a finished fight."""
    assert fight.outcome in ("kill", "spare"), "the fight ended %r, not an ending" % (fight.outcome,)
    dialogue_id = fight.encounter["win_dialogue_%s" % fight.outcome]
    scene_id = fight.encounter["epilogue_scene"]
    trace = run_epilogue(data, scene_id, fight.flags)
    taken = [scene_id]
    said = []
    for kind, value in trace:
        if kind == "branch":
            taken.append(value)
        elif kind == "say":
            said.append(value)
    assert len(said) == 1, "the epilogue %r says %r, one set is expected" % (scene_id, said)
    return fight.outcome, dialogue_id, " -> ".join(taken), said[0]


# ------------------------------------------------------------------------------------------- 1. the four rows exist


@pytest.fixture(scope="module")
def data() -> Data:
    return Data()


def test_the_four_outcome_rows_exist_and_are_the_ones_the_encounters_name(data):
    """A missing or renamed outcome row is a fight that ends in fallback text."""
    named = {}
    for encounter_id in (PERCY, NAVY):
        encounter = data.encounters[encounter_id]
        for outcome in ("kill", "spare"):
            field = "win_dialogue_%s" % outcome
            dialogue_id = encounter.get(field)
            assert dialogue_id in data.dialogues, "%s names %r for %s, not a dialogue id" % (
                encounter_id, dialogue_id, field)
            row = data.dialogues[dialogue_id]
            assert lines_of(row), "the ending %r has no lines" % dialogue_id
            named[(encounter_id, outcome)] = dialogue_id
    assert sorted(named.values()) == sorted(outcome for _, _, outcome in OUTCOMES)
    for dialogue_id in named.values():
        assert dialogue_id in data.dialogues, dialogue_id

    # No long dashes in the ending rows: the house writing rule is a semicolon, and a dash here would ship.
    for _, _, dialogue_id in OUTCOMES:
        for line in lines_of(data.dialogues[dialogue_id]):
            for dash in LONG_DASHES:
                assert dash not in line, "%r carries a long dash" % dialogue_id


def test_each_ending_writes_one_flag_and_the_two_outcomes_do_not_share_it(data):
    """Two endings that write the same flag cannot be told apart by the epilogue."""
    for encounter_id in (PERCY, NAVY):
        encounter = data.encounters[encounter_id]
        kill_flags = encounter.get("flags_on_kill") or []
        spare_flags = encounter.get("flags_on_spare") or []
        assert kill_flags and spare_flags, (encounter_id, kill_flags, spare_flags)
        kill_only = [name for name in kill_flags if name not in spare_flags]
        spare_only = [name for name in spare_flags if name not in kill_flags]
        assert len(kill_only) == len(spare_only) == 1, (encounter_id, kill_only, spare_only)
        assert kill_only[0] in data.flags and spare_only[0] in data.flags, (kill_only, spare_only)


# ---------------------------------------------------------------------------------- 2. four endings, driven to the end


def drive(data: Data, encounter_id: str, outcome: str) -> Fight:
    """Drive one fight to one outcome with the moves a player has, and print the numbers it took."""
    fight = Fight(data, encounter_id)
    if outcome == "kill":
        blows = 0
        while fight.hp > 0:
            fight.fight(100)
            blows += 1
            assert blows < 100, "the kill never lands on %r" % encounter_id
    elif encounter_id == PERCY:
        # The trust route: three TALKs at trust_per_talk 1 reach trust_to_spare 3 with the enemy untouched.
        while fight.trust < fight.enemy["trust_to_spare"]:
            fight.talk()
        kind, _ = fight.press_spare()
        assert kind == "spare", "three TALKs did not open SPARE on %r: %s" % (encounter_id, kind)
    else:
        # The hp route: FIGHT at the bar's floor down to the 25 percent line, then SPARE.
        while not fight.spare_allowed():
            fight.fight(0)
            assert fight.hp > 0, "the navy sailor died on the way to the spare line"
        kind, _ = fight.press_spare()
        assert kind == "spare", "the hp route did not open SPARE on %r: %s" % (encounter_id, kind)
    assert fight.outcome == outcome, "%r ended %r, not %r" % (encounter_id, fight.outcome, outcome)
    return fight


@pytest.mark.parametrize("encounter_id,outcome,dialogue_id", OUTCOMES)
def test_each_of_the_four_endings_is_reachable(data, encounter_id, outcome, dialogue_id):
    """Each ending is reached by real moves, names its own row, its own flag and its own epilogue set."""
    fight = drive(data, encounter_id, outcome)
    word, taken_dialogue, epilogue_path, epilogue_dialogue = ending_of(data, fight)
    print("%s %s: %d event(s), dialogue %r, epilogue %r, flag(s) %r"
          % (encounter_id, word, len(fight.events), taken_dialogue, epilogue_path, sorted(fight.flags)))
    assert word == outcome
    assert taken_dialogue == dialogue_id
    assert epilogue_dialogue in data.dialogues and lines_of(data.dialogues[epilogue_dialogue])

    # The exit row the ledger would keep, and the counter that moves (spec 10 rules 6 and 7).
    expected_exit = {"kill": "down", "spare": "spared"}[outcome]
    assert fight.exit == expected_exit
    moved = [name for name, value in fight.counters.items() if value]
    assert len(moved) == 1 and moved[0].endswith("ed"), fight.counters
    assert fight.flags, "the ending wrote no flag at all"

    # The route the fight leaves behind: a kill makes genocide possible, a spare never does.
    route = data.route_of(fight.counters, fight.stage)
    if outcome == "kill":
        assert route in ("genocide", "blooded") and moved[0] in ("bosses_killed", "regulars_killed"), (route, moved)
    else:
        assert route != "genocide" and moved[0] in ("bosses_spared", "regulars_spared"), (route, moved)


def test_the_epilogue_sets_are_conditional_and_differ_between_the_two_endings(data):
    """Every epilogue branches on the flag only the kill path writes, and the two sets are not the same lines."""
    for encounter_id in (PERCY, NAVY):
        encounter = data.encounters[encounter_id]
        scene_id = encounter.get("epilogue_scene")
        assert scene_id in data.scenes, "%s names epilogue_scene %r, not a scene" % (encounter_id, scene_id)
        branches = [command for command in data.scenes[scene_id]["commands"] if command["cmd"] == "branch"]
        assert len(branches) == 1, "%s must branch exactly once, data has %d" % (scene_id, len(branches))
        kill_flag = [name for name in encounter["flags_on_kill"] if name not in encounter["flags_on_spare"]][0]
        assert branches[0]["flag"] == kill_flag, "%s branches on %r, the kill path writes %r" % (
            scene_id, branches[0]["flag"], kill_flag)
        assert branches[0]["scene"] in data.scenes, "%s branches to a missing scene" % scene_id

        kill_flags = set(encounter["flags_on_kill"])
        spare_flags = set(encounter["flags_on_spare"])
        kill_said = [value for kind, value in run_epilogue(data, scene_id, kill_flags) if kind == "say"]
        spare_said = [value for kind, value in run_epilogue(data, scene_id, spare_flags) if kind == "say"]
        assert kill_said and spare_said, (kill_said, spare_said)
        assert kill_said != spare_said, "%s plays the same epilogue for both endings" % encounter_id
        assert kill_said[0] != spare_said[0]
        # The kill epilogue goes through the branch target, the spare one falls through the entry scene.
        assert [value for kind, value in run_epilogue(data, scene_id, kill_flags) if kind == "branch"]
        assert not [value for kind, value in run_epilogue(data, scene_id, spare_flags) if kind == "branch"]


# ------------------------------------------------------------------------------------------------- 3. the refusal


def test_the_refusal_is_visible_on_the_genocide_route(data):
    """Percy below his gate hands the fight to the interruption; the navy sailor's SPARE is refused at the menu.

    Card t_905a18ce (F4): `spare_refuses_on_route` was data no GML read, so on the genocide route the navy sailor could
    still be spared and Percy could be spared from 30 hp down. Both refusals are now answered where the entry is drawn,
    and these are the two shapes spec 07 line 33 and spec 10 leave: an interruption for Percy inside the gate, and a
    disabled entry with a reason of its own outside it.
    """
    # A player who already killed a boss is on the genocide route (spec 10), and the route is derived, not stored.
    genocide = new_counters()
    genocide["bosses_killed"] = 1

    percy = Fight(data, PERCY, routed_counters=dict(genocide))
    percy.hp = 31   # inside the 40 percent gate (48 hp) and above the spare floor at 30 hp
    assert data.route_of(genocide, 0) == GENOCIDE
    assert not percy.spare_allowed()
    before = sum(percy.counters.values())
    assert percy.command_state() == (True, ""), "the entry is pressable inside the gate, or the story exit is dead (F1)"
    kind, scene = percy.press_spare()
    assert kind == "interrupt" and scene == "prometheus_interrupt", (kind, scene)
    refusal_said = [command["id"] for command in data.scenes[scene]["commands"] if command["cmd"] == "say"]
    assert "percy_interrupt_line" in refusal_said, refusal_said
    assert data.dialogues["percy_interrupt_line"]["speaker"] == "percy"
    assert lines_of(data.dialogues["percy_interrupt_line"])
    assert percy.exit == "turned", "a refused SPARE left the row as %r" % (percy.exit,)
    assert sum(percy.counters.values()) == before, "a turned enemy moved a counter: %r" % (percy.counters,)

    # Percy at 30 hp on the genocide route: the spare gate would take him, and the route refuses the entry anyway.
    percy_low = Fight(data, PERCY, routed_counters=dict(genocide))
    percy_low.hp = 30
    assert percy_low.spare_allowed(), "25 percent of 120 is 30 hp, where the spare gate opens"
    assert percy_low.command_state() == (False, "no mercy left on this route"), percy_low.command_state()
    kind, reason = percy_low.press_spare()
    assert (kind, reason) == ("refused", "no mercy left on this route"), (kind, reason)
    assert percy_low.outcome is None, "a refused SPARE ended the fight as %r" % (percy_low.outcome,)

    # Above Percy's gate the press is refused too, and the reason is the route's, not the spare gate's.
    percy_high = Fight(data, PERCY, routed_counters=dict(genocide))
    kind, reason = percy_high.press_spare()
    assert kind == "refused" and percy_high.outcome is None
    assert reason == "no mercy left on this route", reason

    # The navy sailor has no interruption block, so nothing answers its refused press but the disabled entry.
    navy = Fight(data, NAVY, routed_counters=dict(genocide))
    navy.hp = navy.enemy["max_hp"]
    assert not navy.spare_allowed()
    kind, reason = navy.press_spare()
    assert kind == "refused", kind
    assert reason == "no mercy left on this route", reason
    assert navy.outcome is None, "a refused SPARE ended the fight as %r" % (navy.outcome,)

    # And the same press on a route the encounter does not refuse is a plain disabled entry, with no route reason.
    navy_free = Fight(data, NAVY)
    assert navy_free.route() == "undecided"
    kind, reason = navy_free.press_spare()
    assert (kind, reason) == ("refused", "not ready to end it")


def test_the_interruption_and_the_disabled_entry_are_the_gml_this_file_mirrors(data):
    """The mirror is only a proof while the director still reads: spare first, then the interruption, else nothing."""
    code = code_only(_read(DIRECTOR_GML))
    spare = function_body(code, "pp_battle_spare_allowed")
    assert "if (_battle.enemy_hp <= 0) return false;" in spare, spare
    assert "if (_battle.trust >= _battle.enemy.trust_to_spare) return true;" in spare, spare
    assert "(_battle.enemy_hp <= (_battle.enemy.max_hp * _battle.enemy.spare_hp_percent / 100))" in spare, spare

    begin = function_body(code, "pp_battle_begin_action")
    spare_case = begin[begin.index("case PPCommand.spare:"):]
    spare_case = spare_case[:spare_case.index("case PPCommand.item:")]
    assert spare_case.index("pp_battle_spare_allowed(_battle)") < spare_case.index("pp_battle_interrupt_ready(_battle)"), \
        spare_case
    assert "PPResult.spare" in spare_case and "PPResult.interrupt" in spare_case, spare_case

    outcome = function_body(code, "pp_battle_outcome")
    assert 'return "interrupted"' in outcome and 'return "spare"' in outcome and 'return "kill"' in outcome, outcome

    result = function_body(code, "pp_battle_enter_result")
    assert "win_dialogue_spare" in result and "win_dialogue_kill" in result, result

    commands = code_only(_read(COMMANDS_GML))
    state = function_body(commands, "pp_command_state")
    spare_state = state[state.index("case PPCommand.spare:"):]
    spare_state = spare_state[:spare_state.index("case PPCommand.item:")]
    # Card t_905a18ce (F1): the entry is pressable while the interruption is ready, and that read comes first.
    assert 'if (pp_battle_interrupt_ready(_battle)) return { enabled: true, reason: "" };' in spare_state, spare_state
    assert spare_state.index("pp_battle_interrupt_ready(_battle)") < \
        spare_state.index("pp_battle_spare_route_refused(_battle)"), spare_state
    # Card t_905a18ce (F4): the route refusal is read at the menu, and its reason is the menu's, not a dialogue id.
    assert 'if (pp_battle_spare_route_refused(_battle)) _reason = "no mercy left on this route";' in spare_state, \
        spare_state
    assert 'else if (!pp_battle_spare_allowed(_battle)) _reason = "not ready to end it";' in spare_state, spare_state
    route = function_body(code_only(_read(DIRECTOR_GML)), "pp_battle_spare_route_refused")
    assert "spare_refuses_on_route" in route and "pp_battle_route_name(_battle)" in route, route


# ------------------------------------------------------------------------------------------------- 4. they can fail


def _write_copy(tmp_path, name: str, document: dict) -> str:
    path = tmp_path / name
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return str(path)


def test_removing_the_route_refusal_changes_what_the_menu_answers(data, tmp_path):
    """The refusal checks are measurements: take the field off the row and the same press gets another answer."""
    document = _load(ENCOUNTERS)
    navy_row = find_row(document, "encounters", NAVY)
    assert navy_row.get("spare_refuses_on_route") == GENOCIDE, "the navy row no longer refuses the genocide route"
    del navy_row["spare_refuses_on_route"]
    path = _write_copy(tmp_path, "encounters_no_route_refusal.json", document)

    genocide = new_counters()
    genocide["bosses_killed"] = 1
    fight = Fight(data, NAVY, routed_counters=dict(genocide))
    assert fight.command_state() == (False, "no mercy left on this route"), fight.command_state()
    # The same fight on the mutated row: no field, so the only thing that refuses the entry is the spare gate.
    fight.encounter = find_row(_load(path), "encounters", NAVY)
    assert fight.command_state() == (False, "not ready to end it"), "the copy still refuses the route"

    # A win dialogue id that names nothing is caught, which is the whole point of the first test above.
    document = _load(ENCOUNTERS)
    find_row(document, "encounters", NAVY)["win_dialogue_spare"] = "navy_win_spare_gone"
    path = _write_copy(tmp_path, "encounters_missing_id.json", document)
    assert find_row(_load(path), "encounters", NAVY)["win_dialogue_spare"] not in data.dialogues


def test_the_two_refusal_lines_the_rows_name_still_resolve(data):
    """`spare_refused_dialogue` is data the build does not say yet (recorded gap), so this keeps the rows readable.

    Card t_905a18ce (F4) moved the refusal into the menu, where it is a reason drawn under the boxes rather than a line
    a board types out. The navy row still names the line its refusal was written as, and a row that names a dialogue id
    that does not exist would be a second dead fact on top of the first.
    """
    assert data.encounters[NAVY]["spare_refused_dialogue"] == "navy_spare_refused"
    row = data.dialogues["navy_spare_refused"]
    assert lines_of(row), row


def test_a_branch_on_the_wrong_flag_breaks_the_epilogue_check(data, tmp_path):
    """An epilogue that branches on the spare flag would play the kill set for a spared enemy."""
    document = _load(SCENES)
    scene = find_row(document, "scenes", "navy_aftermath")
    scene["commands"][0]["flag"] = "sailor_spared"
    path = _write_copy(tmp_path, "scenes_wrong_flag.json", document)
    mutated = by_id(_load(path), "scenes")

    def said(scenes: dict, encounter_row: dict, outcome: str) -> str:
        flags = set(encounter_row["flags_on_%s" % outcome])
        commands = list(scenes[encounter_row["epilogue_scene"]]["commands"])
        spoken = []
        index = 0
        while index < len(commands):
            command = commands[index]
            if command["cmd"] == "say":
                spoken.append(command["id"])
                index += 1
            elif command["cmd"] == "branch" and command["flag"] in flags:
                commands = list(scenes[command["scene"]]["commands"])
                index = 0
            else:
                index += 1
        return spoken[-1]

    encounter = data.encounters[NAVY]
    assert said(data.scenes, encounter, "kill") == "navy_epilogue_kill"
    assert said(mutated, encounter, "kill") == "navy_epilogue_spare", "the wrong flag still took the kill set"


# --------------------------------------------------------------------------------------------- 5. the headless probe


def probe() -> int:
    data = Data()
    print("G0-4c headless probe: the four fight endings and their epilogues")
    for encounter_id in (PERCY, NAVY):
        enemy = data.enemy_of(encounter_id)
        print("%s: enemy %s, max_hp %d, route_kind %s, spare_hp_percent %d, trust_to_spare %d"
              % (encounter_id, enemy["id"], enemy["max_hp"], enemy["route_kind"],
                 enemy["spare_hp_percent"], enemy["trust_to_spare"]))
    print("FIGHT band %d to %d, hero multiplier %s, at the bar's floor %d a blow"
          % (data.fight_min, data.fight_max, data.multiplier, data.fight_damage(0)))

    print("\nthe four endings, each driven to its end")
    for encounter_id, outcome, expected_dialogue in OUTCOMES:
        fight = drive(data, encounter_id, outcome)
        word, dialogue_id, epilogue_path, epilogue_dialogue = ending_of(data, fight)
        assert dialogue_id == expected_dialogue
        print("  %-15s %-5s -> outcome %-5s  row exit %-6s  dialogue %-16s epilogue %-40s says %s  flags %s"
              % (encounter_id, outcome, word, fight.exit, dialogue_id, epilogue_path,
                 epilogue_dialogue, sorted(fight.flags)))

    print("\nthe spare refusal on the genocide route")
    genocide = new_counters()
    genocide["bosses_killed"] = 1
    percy = Fight(data, PERCY, routed_counters=dict(genocide))
    before = sum(percy.counters.values())
    percy.hp = 31
    kind, scene = percy.press_spare()
    print("  percy at 31 hp, SPARE -> %s, scene %s, exit row %s, counters before %d after %d"
          % (kind, scene, percy.exit, before, sum(percy.counters.values())))
    assert (kind, scene, percy.exit) == ("interrupt", "prometheus_interrupt", "turned")
    assert sum(percy.counters.values()) == before
    percy = Fight(data, PERCY, routed_counters=dict(genocide))
    percy.hp = 30
    kind, reason = percy.press_spare()
    print("  percy at 30 hp (the spare line), SPARE -> %s, disabled entry reason %r" % (kind, reason))
    assert (kind, reason) == ("refused", "no mercy left on this route")
    navy = Fight(data, NAVY, routed_counters=dict(genocide))
    kind, reason = navy.press_spare()
    print("  navy at %d hp, SPARE -> %s, disabled entry reason %r" % (navy.enemy["max_hp"], kind, reason))
    assert (kind, reason) == ("refused", "no mercy left on this route")
    percy = Fight(data, PERCY, routed_counters=dict(genocide))
    kind, reason = percy.press_spare()
    print("  percy at 120 hp, above the gate, SPARE -> %s, disabled entry reason %r" % (kind, reason))
    assert (kind, reason) == ("refused", "no mercy left on this route")
    return 0


if __name__ == "__main__":
    sys.exit(probe())
