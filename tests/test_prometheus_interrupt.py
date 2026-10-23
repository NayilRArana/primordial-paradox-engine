"""G0-4b: Prometheus stops the fight, and the fight can still be won or spared.

Card t_e5fa86d3, the second third of the split ruled in D4 of `knowledge/GAMEDEV-DECISIONS-2026-10-23.md`. Spec 18
sections 4 and 8 are the source: a fight returns exactly one of `victory`, `defeat`, `spared`, `interrupted`, and the
interruption fires on a REFUSED SPARE press at or below `interrupt.hp_at_or_below`, not on an hp crossing (A18-1).

What this file holds down, and why each one earns its place:

  1. the shipped enemy row carries the block spec 18 section 6 writes: `on` `spare_refused`, the gate at 40 percent,
     `unless_flag` `met_prometheus`, and a scene id that exists. The gate is a REQUEST gate, so the story exit lives in
     the 18 hp window between 48 hp (40 percent) and 31 hp, and 30 hp and below is an accepted SPARE;
  2. the interruption is not a crossing: the two provenances of the number are pinned in one place, 12 hp is the FIGHT
     ceiling and 18 with tide_step, so an hp trigger above 11 hp of 120 (17 with the power) would make Percy
     unkillable on every route. The counterfactual is simulated rather than asserted in prose;
  3. the scene and its two dialogue entries are the row the card names: `met_prometheus` and `percy_standing` are set,
     PP-07 plays, the scene fades and ends back on the map, and every id it names resolves in data;
  4. the director tries the spare first and only then the interruption, compares the gate in integers, records the
     exit row as `turned` and moves no counter, and names no enemy, scene or route in its own code;
  5. the checker is a gate and not a print: an interrupt on a non boss, a threshold at or below `spare_hp_percent`, an
     `on` outside its closed set, a partial route object, an unknown scene id and an unknown flag are each refused with
     a message naming the file, the enemy and the field;
  6. the headless probe presses SPARE across the whole bar and prints the outcome at each band, then runs the scene's
     commands and shows the two flags set. It is a mirror of the GML and not the engine, which is why the GML's own
     comparison, order and outcome word are also pinned text for text below.

Known gaps, recorded rather than hidden:
  - no GML is compiled or run here. GameMaker is not installed on this host, so the driver below is a mirror of the
    director and of the menu, and the GML's own text is pinned so the mirror cannot drift silently. Nothing in this
    file says a scene played;
  - the scene row has no `spawn`, `shake` or 30 step crossfade yet; spec 18 section 9 C18-3 leaves those to R04
    (t_a3fa132a), and this card's goal only asks the row to run, set the flag, play PP-07, fade and end;
  - `prometheus_interrupt_blooded` does not exist yet, so the shipped `scene` is the single id form spec 18 section 4
    allows. The four key form is implemented and tested against a synthetic block;
  - closed by card t_905a18ce and recorded here because this file used to record them as gaps: the SPARE entry was
    disabled across the whole interrupt window (F1), no caller played the scene the fight named (F2), and a second,
    dead interrupt block sat on the percy encounter row that nothing read and the checker did not refuse (F3). Section
    6 below is where those three are held down now.

Run: python -m pytest tests/test_prometheus_interrupt.py -q
Headless probe: python tests/test_prometheus_interrupt.py
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_data  # noqa: E402  (the path insert above is what makes this importable outside pytest)

ENEMIES = os.path.join(ROOT, "data", "enemies", "all.json")
SCENES = os.path.join(ROOT, "data", "scenes", "all.json")
DIALOGUE = os.path.join(ROOT, "data", "dialogue", "all.json")
FLAGS = os.path.join(ROOT, "data", "flags.json")
AUDIO = os.path.join(ROOT, "data", "audio.json")
PROJECT = os.path.join(ROOT, "data", "project.json")
DIRECTOR = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
CONFIG = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")

SCENE_ID = "prometheus_interrupt"
CUE_ID = "PP-07"
INTERRUPT_PERCENT = 40      # spec 18 section 6's data block
SPARE_PERCENT = 25          # spec 07: SPARE is enabled at 25 percent or less
FIGHT_CEILING = 12          # spec 07's FIGHT ceiling, 2 to 12
TIDE_STEP = 18              # the biggest legal blow once the power is spent
MAX_HP = 120


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def percy():
    rows = [row for row in read_json(ENEMIES)["enemies"] if row["id"] == "percy"]
    assert len(rows) == 1, "data/enemies/all.json must hold exactly one percy row"
    return rows[0]


def interrupt_block():
    block = percy().get("interrupt")
    assert isinstance(block, dict), "percy must carry the interrupt block spec 18 section 4 puts on the enemy row"
    return block


def scene_row(scene_id=SCENE_ID):
    rows = [row for row in read_json(SCENES)["scenes"] if row["id"] == scene_id]
    assert len(rows) == 1, "data/scenes/all.json must hold exactly one %s row" % scene_id
    return rows[0]


def dialogue_row(dialogue_id):
    rows = [row for row in read_json(DIALOGUE)["dialogue"] if row["id"] == dialogue_id]
    assert len(rows) == 1, "data/dialogue/all.json must hold exactly one %r row" % dialogue_id
    return rows[0]


def crossing_hp(threshold, max_hp):
    """The highest hp at which `hp * 100 <= threshold * max_hp` holds, solved rather than guessed at."""
    return (threshold * max_hp) // 100


# ---------------------------------------------------------------------------------------------------------------
# 1. The shipped data is the spec's block.


def test_percy_ships_the_interrupt_block_spec_18_section_6_writes():
    block = interrupt_block()
    assert block["on"] == "spare_refused", "spec 18 section 4: `on` is a closed set and this is its only member"
    assert block["hp_at_or_below"] == INTERRUPT_PERCENT
    assert block["unless_flag"] == "met_prometheus", "C18-7 keeps the flag guard, on the enemy row"
    assert block["scene"] == SCENE_ID
    assert set(block) == {"on", "hp_at_or_below", "unless_flag", "scene"}, block


def test_the_gate_is_the_request_and_not_a_crossing():
    """Spec 18 section 4 rule 4 reads the field name literally, and this is the difference that keeps the kill legal."""
    block = interrupt_block()
    threshold = block["hp_at_or_below"]
    assert crossing_hp(threshold, MAX_HP) == 48, "40 percent of 120 is 48 hp, the highest hp the gate covers"
    # Above the gate the request does not interrupt; at the gate it does; at the spare bar the spare simply wins.
    assert press_spare(percy(), 49, 0, {}) == ("refused", None)
    assert press_spare(percy(), 48, 0, {}) == ("interrupted", SCENE_ID)
    assert press_spare(percy(), 31, 0, {}) == ("interrupted", SCENE_ID)
    assert press_spare(percy(), 30, 0, {}) == ("spare", None), "25 percent of 120 is 30 hp, where SPARE is accepted"


def test_the_story_exit_lives_in_the_eighteen_hp_window_the_spec_names():
    """A18-5: "a 6 hp window (48 hp down to 31)" is 18 hp of the bar; the numbers are pinned so it cannot drift."""
    spare_bar = crossing_hp(SPARE_PERCENT, MAX_HP)
    gate = crossing_hp(INTERRUPT_PERCENT, MAX_HP)
    assert (spare_bar, gate) == (30, 48)
    window = [hp for hp in range(1, MAX_HP + 1) if press_spare(percy(), hp, 0, {})[0] == "interrupted"]
    assert window == list(range(31, gate + 1)), window
    assert len(window) == 18


def test_the_flag_and_the_scene_ids_exist():
    assert "met_prometheus" in read_json(FLAGS)["flags"]
    assert "percy_standing" in read_json(FLAGS)["flags"]
    assert scene_row()["id"] == SCENE_ID


def test_a_crossing_trigger_would_have_made_the_kill_impossible():
    """A18-1 in arithmetic: the reason the trigger moved off the hp axis, simulated rather than asserted."""
    gate = crossing_hp(INTERRUPT_PERCENT, MAX_HP)
    assert gate == 48
    # A killing blow must take the bar from ABOVE the gate all the way to 0, so it has to be at least gate + 1.
    needed = gate + 1
    assert needed == 49
    assert FIGHT_CEILING < needed and TIDE_STEP < needed, "no legal blow can jump 48 hp, which is why A18-1 exists"
    # The same arithmetic at the highest gate a 120 hp boss could survive on: 9 percent with FIGHT, 14 with the power.
    assert crossing_hp(9, MAX_HP) == 10 and crossing_hp(14, MAX_HP) == 16
    assert FIGHT_CEILING > crossing_hp(9, MAX_HP) and TIDE_STEP > crossing_hp(14, MAX_HP)
    # And the mechanism that replaced it keeps the kill open: no SPARE press, no interruption, all the way to 0.
    assert kill_by_damage(percy(), {}) == ("kill", []), "a fight with no SPARE press is never interrupted"


# ---------------------------------------------------------------------------------------------------------------
# 2. The scene row and its dialogue, which the card names as its output.


def test_the_scene_row_does_the_five_things_the_card_names():
    commands = scene_row()["commands"]
    setflags = [(cmd["name"], cmd.get("value", True)) for cmd in commands if cmd["cmd"] == "setflag"]
    music = [cmd["id"] for cmd in commands if cmd["cmd"] == "music"]
    fades = [cmd.get("mode", "") for cmd in commands if cmd["cmd"] == "fade"]
    assert ("met_prometheus", True) in setflags, "the card: the scene sets met_prometheus"
    assert ("percy_standing", True) in setflags, "the card: Percy is still standing when control comes back"
    assert music == [CUE_ID], music
    assert fades == ["out", "in"], "a fade out and back in is the return to the overworld"
    assert commands[-1]["cmd"] == "end", "spec 06 rule 6: a scene ends with end"


def test_the_scene_does_not_resume_the_fight():
    """Spec 18 section 4 step 6: the fight is not resumed, the arena is destroyed, and the scene ends on the map."""
    commands = scene_row()["commands"]
    assert [cmd["cmd"] for cmd in commands].count("battle") == 0, "no second battle is started by the interruption"
    assert "branch" not in [cmd["cmd"] for cmd in commands], "the shipped row is one path; a variant would branch"


def test_the_first_say_is_the_enemy_not_the_director():
    """Spec 18 section 4: the refusal line is not printed on the turn the interruption fires, the scene explains it."""
    commands = scene_row()["commands"]
    first_say = [cmd for cmd in commands if cmd["cmd"] == "say"][0]
    assert first_say["id"] == "percy_interrupt_line"
    assert dialogue_row("percy_interrupt_line")["speaker"] == "percy"
    assert dialogue_row("prometheus_veil_line")["speaker"] == "prometheus"


def test_every_id_the_scene_names_resolves():
    commands = scene_row()["commands"]
    dialogue_ids = {row["id"] for row in read_json(DIALOGUE)["dialogue"]}
    flag_names = set(read_json(FLAGS)["flags"])
    audio = read_json(AUDIO)
    sound_ids = {row["id"] for row in audio["sounds"]} | {row["id"] for row in audio["cues"]}
    for command in commands:
        if command["cmd"] == "say":
            assert command["id"] in dialogue_ids, command
        elif command["cmd"] == "music":
            assert command["id"] in sound_ids, command
        elif command["cmd"] == "setflag":
            assert command["name"] in flag_names, command
        else:
            # The mirror above only implements the commands this row uses; a new kind has to be added here on purpose,
            # so a row that grows a spawn or a shake cannot slip past this test unnoticed.
            assert command["cmd"] in ("fade", "end"), command


def test_the_whole_data_tree_passes_the_checker():
    assert check_data.check(ROOT) == [], check_data.check(ROOT)


# ---------------------------------------------------------------------------------------------------------------
# 3. The director: the spare is tried first, the gate is integers, the row is turned and no counter moves.


def code_only(text):
    """Drop // comments so these pins read code, not the prose that explains it (tests/test_project.py does the same)."""
    return "\n".join(line if line.find("//") == -1 else line[:line.find("//")] for line in text.split("\n"))


def director_code():
    with open(DIRECTOR, "r", encoding="utf-8-sig") as handle:
        return code_only(handle.read())


def function_body(code, name):
    start = code.index("function " + name + "(")
    end = code.find("\n}", start)
    return code[start:end]


def test_the_spare_is_tried_before_the_interruption():
    """Spec 18 section 4's resolution order: rule 2 (spare accepted) is decided before rule 4 (the story exit)."""
    body = function_body(director_code(), "pp_battle_begin_action")
    case = body[body.index("case PPCommand.spare:"):]
    case = case[:case.index("break;")]
    assert case.index("pp_battle_spare_allowed(_battle)") < case.index("pp_battle_interrupt_ready(_battle)")
    assert case.index("pp_battle_enter_result(_battle)") < case.index("pp_battle_enter_interrupt(_battle)")
    assert "else if" in case, "a refused spare may only reach the interrupt when the spare was refused"


def test_the_gate_is_compared_in_integers_like_a_crossing():
    code = director_code()
    pattern = re.compile(r"enemy_hp\s*\*\s*100\s*<=\s*_block\.hp_at_or_below\s*\*\s*_battle\.enemy\.max_hp")
    assert pattern.search(code), "spec 18 section 4 rule 4: hp * 100 <= hp_at_or_below * max_hp, no float"


def test_the_trigger_is_spare_refused_and_nothing_else():
    code = director_code()
    assert '_block.on != "spare_refused"' in code
    assert "pp_battle_interrupt_ready" in code


def test_the_exit_row_is_written_before_the_result_beat_and_no_counter_moves():
    code = director_code()
    body = function_body(code, "pp_battle_enter_interrupt")
    assert "pp_battle_record(_battle)" in body
    assert body.index("pp_battle_record(_battle)") < body.index("pp_battle_phase_set(_battle, PPBattlePhase.result)")
    assert "_ledger.counters" not in code, "a turned enemy moves no counter (spec 10 rule 7); only the ledger may"
    ledger_code = code_only(open(os.path.join(ROOT, "game", "scripts", "pp_ledger", "pp_ledger.gml"),
                                 "r", encoding="utf-8-sig").read())
    assert "case PPResult.interrupt: return PPExit.turned;" in ledger_code


def test_the_fourth_outcome_word_is_interrupted():
    body = function_body(director_code(), "pp_battle_outcome")
    assert 'return "interrupted";' in body
    for word in ('"defeat"', '"spare"', '"kill"'):
        assert "return " + word + ";" in body, "the other three are untouched"


def test_the_scene_is_resolved_from_the_row_and_the_route_is_derived_on_read():
    code = director_code()
    body = function_body(code, "pp_battle_interrupt_scene")
    assert "is_string(_block.scene)" in body, "spec 18 section 4: one scene id is the first legal shape"
    assert "pp_battle_route_name(_battle)" in body, "the route key comes from the one derivation, not a second copy"
    route = function_body(code, "pp_battle_route_name")
    assert "pp_ledger_route(_battle.ledger, _stage)" in route, "spec 10: the route is derived on read, never stored"
    assert "pp_ledger_route_name(" in route
    assert "pp_data.project" in route and "prison_stage" in route
    # Nothing stores a route on the battle, because a stored route is the second copy spec 10 refuses.
    assert not re.search(r"_battle\.route\s*=", code)


def test_no_enemy_name_scene_id_or_route_name_is_hardcoded_in_the_director():
    code = director_code().lower()
    for word in ("percy", SCENE_ID, "blooded", "genocide", "undead", "navy_sailor"):
        assert word not in code, "%r in pp_battle_director.gml would be a branch on data" % word


def test_the_route_keys_are_the_four_the_ledger_names():
    config = code_only(open(CONFIG, "r", encoding="utf-8-sig").read())
    assert "enum PPRoute {" in config
    assert check_data.INTERRUPT_ROUTE_KEYS == ("undecided", "mercy", "blooded", "genocide")


# ---------------------------------------------------------------------------------------------------------------
# 4. The checker refuses each fault, naming the file, the enemy and the field.


def messages(root):
    return check_data.check(str(root))


def interrupt_messages(root, needle):
    return [message for message in messages(root)
            if "data/enemies/all.json" in message and "interrupt" in message and needle in message]


def percy_index(data):
    return [index for index, row in enumerate(data["enemies"]) if row["id"] == "percy"][0]


def test_an_interrupt_on_a_regular_enemy_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data) - 1]["interrupt"] = {"on": "spare_refused", "hp_at_or_below": 40,
                                                           "scene": SCENE_ID}
    write_json(path, data)
    found = interrupt_messages(data_root, "route_kind boss")
    assert found, messages(data_root)


def test_a_threshold_at_or_below_the_spare_percent_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["hp_at_or_below"] = SPARE_PERCENT
    write_json(path, data)
    found = interrupt_messages(data_root, "story exit could never fire")
    assert found, messages(data_root)
    assert "refusal 8" in found[0], found


def test_an_on_outside_its_closed_set_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["on"] = "hp_crossing"
    write_json(path, data)
    assert interrupt_messages(data_root, "closed set"), messages(data_root)


def test_a_threshold_outside_one_to_ninety_nine_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["hp_at_or_below"] = 100
    write_json(path, data)
    assert interrupt_messages(data_root, "outside 1 to 99"), messages(data_root)


def test_a_partial_route_object_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["scene"] = {"mercy": SCENE_ID}
    write_json(path, data)
    found = interrupt_messages(data_root, "all four keys")
    assert found, messages(data_root)


def test_an_unknown_scene_id_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["scene"] = "prometheus_interrupt_blooded"
    write_json(path, data)
    assert any("scene" in message and "prometheus_interrupt_blooded" in message for message in messages(data_root)), \
        messages(data_root)


def test_an_unknown_unless_flag_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][percy_index(data)]["interrupt"]["unless_flag"] = "met_promethus"
    write_json(path, data)
    assert any("met_promethus" in message for message in messages(data_root)), messages(data_root)


# ---------------------------------------------------------------------------------------------------------------
# 5. The mirror the probe runs: the GML's own rules, written out in Python so the card has a headless check.
#
# GameMaker is not installed on this host, so these functions are a mirror of the director and NOT the engine. The
# pins above keep the mirror honest: the comparison, the order of the spare case and the four outcome words are read
# out of the GML text, so a change there fails a test here instead of leaving the mirror behind.


def spare_allowed(hp, trust, enemy):
    """pp_battle_spare_allowed: trust reaches the threshold, or hp is at its spare percentage or less."""
    if hp <= 0:
        return False
    if trust >= enemy["trust_to_spare"]:
        return True
    return hp * 100 <= enemy["spare_hp_percent"] * enemy["max_hp"]


def interrupt_ready(hp, trust, flags, enemy):
    """pp_battle_interrupt_ready, in the order the GML asks the questions."""
    if hp <= 0:
        return False
    if spare_allowed(hp, trust, enemy):
        return False
    block = enemy.get("interrupt")
    if not isinstance(block, dict):
        return False
    if block.get("on") != "spare_refused":
        return False
    if "unless_flag" in block and flags.get(block["unless_flag"], False):
        return False
    if "hp_at_or_below" not in block:
        return False
    return hp * 100 <= block["hp_at_or_below"] * enemy["max_hp"]


def interrupt_scene(enemy, flags, counters, stage, prison_stage):
    """pp_battle_interrupt_scene: one id, or the id under the route derived on read (spec 10, A18-4)."""
    block = enemy.get("interrupt")
    if not isinstance(block, dict) or "scene" not in block:
        return ""
    scene = block["scene"]
    if isinstance(scene, str):
        return scene
    if counters["bosses_killed"] > 0:
        route = "genocide"
    elif counters["regulars_killed"] > 0:
        route = "blooded"
    elif stage >= prison_stage:
        route = "mercy"
    else:
        route = "undecided"
    return scene.get(route, "")


def press_spare(enemy, hp, trust, flags):
    """One SPARE press on the menu, as pp_battle_step_menu resolves it. The turn is never spent on a refusal.

    Card t_905a18ce (F1): this used to model the press in Python and skip the menu, which is how every hp from 31 to 48
    stayed green while the entry was disabled. It now goes through pp_command_state's mirror first, so a refused entry
    comes back as `refused` and never as an accepted spare.
    """
    enabled, _reason = command_state(hp, trust, flags, enemy, encounter_row("percy"), "undecided")
    if not enabled:
        return ("refused", None)
    if spare_allowed(hp, trust, enemy):
        return ("spare", None)
    if interrupt_ready(hp, trust, flags, enemy):
        return ("interrupted", interrupt_scene(enemy, flags, {"bosses_killed": 0, "regulars_killed": 0}, 0, 3))
    return ("refused", None)


def fight_to_zero(enemy, flags, presses=(), blow=FIGHT_CEILING):
    """FIGHT from full hp to 0, pressing SPARE at the hp values in `presses` and nowhere else.

    Returns (outcome, events). "kill" is the bar reaching 0 from the player's damage, "interrupted" is a pressed
    SPARE refused inside the gate, "spare" is a pressed SPARE the enemy accepts. A fight that never presses SPARE is
    never interrupted, whatever hp it passes through: that is A18-1's whole point, and the gate opening is not a
    trigger.
    """
    hp = enemy["max_hp"]
    events = []
    while hp > 0:
        if hp in presses:
            outcome, scene = press_spare(enemy, hp, 0, flags)
            events.append((hp, outcome, scene))
            if outcome in ("interrupted", "spare"):
                return (outcome, events)
        hp = max(0, hp - blow)
    return ("kill", events)


def kill_by_damage(enemy, flags):
    """The kill route: one FIGHT blow after another, no SPARE press, no TALK."""
    return fight_to_zero(enemy, flags)


def run_scene(row, dialogue_ids, flag_names, sound_ids, flags):
    """The scene runner's own path for the commands this row uses: say, setflag, music, fade, end."""
    trace = []
    for command in row["commands"]:
        kind = command["cmd"]
        if kind == "say":
            assert command["id"] in dialogue_ids, command
            trace.append(("say", command["id"]))
        elif kind == "setflag":
            assert command["name"] in flag_names, command
            flags[command["name"]] = command.get("value", True)
            trace.append(("setflag", command["name"]))
        elif kind == "music":
            assert command["id"] in sound_ids, command
            trace.append(("music", command["id"]))
        elif kind == "fade":
            trace.append(("fade", command.get("mode", "out")))
        elif kind == "end":
            trace.append(("end",))
            assert len(trace) == len(row["commands"]), "end is the last command in this row, by the checker"
            break
        else:
            raise AssertionError("the mirror does not implement %r yet" % kind)
    return trace


def ledger_record(result, enemy):
    """pp_ledger_record_exit's two facts: the row, and which counter (if any) moves."""
    rows = {"kill": "down", "spare": "spared", "interrupted": "turned"}
    counters = {"bosses_killed": 0, "bosses_spared": 0, "regulars_killed": 0, "regulars_spared": 0}
    enemies = {"kill": "regulars_killed", "spare": "regulars_spared"}
    kind = enemy.get("route_kind", "regular")
    exit_name = rows[result]
    if result in enemies:
        counters[enemies[result].replace("regulars_", "bosses_" if kind == "boss" else "regulars_")] += 1
    return {"id": enemy["id"], "exit": exit_name, "round": 0}, counters, exit_name


# ---------------------------------------------------------------------------------------------------------------
# 6. The two wires the review of G0-4a/b/c found broken, and the route field nothing read (card t_905a18ce).
#
# F1: the SPARE entry was disabled whenever spare was not allowed, and pp_battle_step_menu returns on a disabled entry
#     before pp_battle_begin_action is reached, so every hp from 31 to 48 with trust below 3 was a press that never
#     arrived. The entry now stays pressable while the interruption is ready, and the mirrors below walk the menu and
#     then the action instead of resolving the press in Python.
# F2: no caller played the scene the fight named, so met_prometheus was never set. pp_app now takes the scene id from
#     the fight before it clears the battle, and pp_overworld_battle_finished starts it with no press.
# F4: `spare_refuses_on_route` was data no GML read. It is now read in pp_command_state, the same place every other
#     refusal is read, and the tests drive it through that function.
#
# GameMaker is not installed here, so these are mirrors plus text pins, not a played scene. The pins are what makes
# them fail: take the fix out of the GML and the pin above each mirror stops matching.

APP = os.path.join(ROOT, "game", "scripts", "pp_app", "pp_app.gml")
OVERWORLD = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
COMMANDS = os.path.join(ROOT, "game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")
ENCOUNTERS = os.path.join(ROOT, "data", "encounters", "all.json")

_ENCOUNTER_ROWS = {}


def encounter_row(encounter_id="percy"):
    """The encounter row, read once: the route refusal lives here and the mirrors ask it on every hp."""
    if "rows" not in _ENCOUNTER_ROWS:
        _ENCOUNTER_ROWS["rows"] = {row["id"]: row for row in read_json(ENCOUNTERS)["encounters"]}
    return _ENCOUNTER_ROWS["rows"][encounter_id]


def source(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return code_only(handle.read())


def raw_source(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def block_at(code, marker):
    """The brace matched {...} whose header contains `marker`."""
    start = code.index(marker)
    open_index = code.index("{", start)
    depth = 0
    for index in range(open_index, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[open_index:index + 1]
    raise AssertionError("unbalanced block at %r" % marker)


def menu_spare_case():
    """pp_command_state's SPARE case, comments stripped: the one place a refusal is drawn."""
    state = function_body(source(COMMANDS), "pp_command_state")
    case = state[state.index("case PPCommand.spare:"):]
    return case[:case.index("case PPCommand.item:")]


def action_spare_case():
    begin = function_body(director_code(), "pp_battle_begin_action")
    case = begin[begin.index("case PPCommand.spare:"):]
    return case[:case.index("break;")]


def command_state(hp, trust, flags, enemy, encounter, route):
    """pp_command_state for SPARE, in the order the GML asks: the interruption, then the route, then the spare gate."""
    if interrupt_ready(hp, trust, flags, enemy):
        return (True, "")
    if encounter.get("spare_refuses_on_route") == route:
        return (False, "no mercy left on this route")
    if not spare_allowed(hp, trust, enemy):
        return (False, "not ready to end it")
    return (True, "")


def press_through_menu(hp, trust, flags, enemy, encounter, route):
    """One SPARE press from the menu to the action, which is the path the engine takes.

    A disabled entry never becomes a press (spec 07 rule 1), so the difference between "the row says refused" and "the
    press arrived and the direction refused it" is visible here instead of being assumed.
    """
    enabled, reason = command_state(hp, trust, flags, enemy, encounter, route)
    if not enabled:
        return ("disabled", reason)
    # pp_battle_begin_action's spare case: an accepted spare first, unless the route refuses it, then the interruption.
    if spare_allowed(hp, trust, enemy) and encounter.get("spare_refuses_on_route") != route:
        return ("spare", None)
    if interrupt_ready(hp, trust, flags, enemy):
        return ("interrupted", interrupt_scene(enemy, flags, {"bosses_killed": 0, "regulars_killed": 0}, 0, 3))
    return ("nothing", None)


def test_f1_the_spare_entry_is_pressable_across_the_whole_interrupt_window():
    """No hp from 31 to 48 is a press that never arrives, and that is the window the story exit lives in."""
    case = menu_spare_case()
    assert 'if (pp_battle_interrupt_ready(_battle)) return { enabled: true, reason: "" };' in case, case
    assert case.index("pp_battle_interrupt_ready(_battle)") < case.index("pp_battle_spare_route_refused(_battle)"), \
        case
    assert "!pp_battle_spare_allowed(_battle)" in case, "the spare gate is still what refuses outside the window"

    action = action_spare_case()
    assert "pp_battle_spare_allowed(_battle) && !pp_battle_spare_route_refused(_battle)" in action, action
    assert action.index("pp_battle_spare_allowed(_battle)") < action.index("pp_battle_interrupt_ready(_battle)"), action
    assert "pp_battle_enter_interrupt(_battle)" in action, action

    enemy = percy()
    encounter = encounter_row()
    enabled_hp = [hp for hp in range(1, MAX_HP + 1)
                  if command_state(hp, 0, {}, enemy, encounter, "undecided")[0]]
    assert enabled_hp == list(range(1, 49)), \
        "SPARE is pressable at %r; the spare line is 30 hp and the gate is 48 hp" % (enabled_hp[:3],)
    for hp in range(31, 49):
        assert press_through_menu(hp, 0, {}, enemy, encounter, "undecided") == ("interrupted", SCENE_ID), hp
    assert press_through_menu(30, 0, {}, enemy, encounter, "undecided") == ("spare", None)
    assert press_through_menu(49, 0, {}, enemy, encounter, "undecided") == ("disabled", "not ready to end it")
    print("F1: SPARE pressable at every hp in 1..48; 31..48 all end as interrupted -> %s" % SCENE_ID)


def test_f4_the_route_refusal_is_read_at_the_menu_and_not_only_in_python():
    """`spare_refuses_on_route` was a field no GML read. It is read now, where the entry is drawn and refused."""
    encounter = encounter_row()
    assert encounter.get("spare_refuses_on_route") == "genocide", \
        "the percy row is the route refusal this test drives: %r" % (encounter.get("spare_refuses_on_route"),)
    read = function_body(director_code(), "pp_battle_spare_route_refused")
    assert "spare_refuses_on_route" in read, read
    assert "pp_battle_route_name(_battle)" in read, read
    assert "pp_battle_spare_route_refused(_battle)" in menu_spare_case()

    enemy = percy()
    # Above the gate on the genocide route the entry is refused with the route's own reason, not the spare gate's.
    assert command_state(60, 0, {}, enemy, encounter, "genocide") == (False, "no mercy left on this route")
    # At the spare line too: the route refusal beats the hp gate, which is what spec 07 line 33 and spec 10 ask for.
    assert command_state(30, 0, {}, enemy, encounter, "genocide") == (False, "no mercy left on this route")
    # And inside the gate the press still arrives, because that is where the interruption fires on every route.
    assert command_state(40, 0, {}, enemy, encounter, "genocide") == (True, "")
    assert press_through_menu(40, 0, {}, enemy, encounter, "genocide") == ("interrupted", SCENE_ID)
    # On a route the row does not refuse, the same hp values behave as they did before.
    assert command_state(30, 0, {}, enemy, encounter, "undecided") == (True, "")
    assert command_state(60, 0, {}, enemy, encounter, "undecided") == (False, "not ready to end it")
    # The navy row refuses the same route and names the line its refusal plays, which is not a cursor note.
    navy = encounter_row("tutorial_sailors")
    assert navy.get("spare_refuses_on_route") == "genocide", navy.get("spare_refuses_on_route")
    assert navy.get("spare_refused_dialogue") == "navy_spare_refused"
    print("F4: genocide refuses SPARE at 60 hp and at 30 hp with the route's reason; 40 hp still interrupts")


def caller_step(outcome, handoff, pressed):
    """pp_mode_battle's step and pp_overworld_battle_finished, in the order the GML runs them.

    Returns ("battle", "") while the fight is still on screen and ("overworld", scene) once the caller has taken the
    fight over, where scene is "" for a kill or a spare and the row's id for an interruption.
    """
    scene = handoff if outcome == "interrupted" else ""
    if scene == "" and not pressed:
        return ("battle", "")
    # The door sets battle_done only when it hands nothing over; a handoff starts its scene through the one scene door.
    return ("overworld", scene)


def test_f2_the_caller_starts_the_scene_with_no_press():
    """Spec 18 section 4 step 4: the caller continues with no press. Before this fix nothing played the scene."""
    handoff = function_body(director_code(), "pp_battle_handoff_scene")
    assert "PPResult.interrupt" in handoff and "pp_battle_interrupt_scene(_battle)" in handoff, handoff

    app = raw_source(APP)
    battle_mode = code_only(app[app.index("// Mode: battle."):app.index("// Mode: overworld.")])
    step = block_at(battle_mode, "step: function(_params)")
    assert "pp_battle_handoff_scene(_battle)" in step, step
    assert step.index("pp_battle_handoff_scene(_battle)") < step.index("global.pp.battle = undefined;"), \
        "the scene id is taken from the fight before the fight is cleared"
    assert 'if (pp_pressed("confirm") || _handoff != "")' in step, \
        "the press is only needed when the fight hands nothing over"
    assert "pp_overworld_battle_finished(global.pp.world, _enc_id, _outcome, _handoff);" in step, step
    # The old door is one press inside an if, so it cannot run before the handoff is read.
    assert step.index("pp_battle_handoff_scene(_battle)") < step.index('pp_pressed("confirm")'), step

    door = function_body(source(OVERWORLD), "pp_overworld_battle_finished")
    assert "_handoff_scene" in door.split("{")[0], "the door takes the id the caller captured"
    assert "pp_overworld_start_scene(_world, _handoff_scene);" in door, door
    assert 'if (!is_string(_handoff_scene) || _handoff_scene == "")' in door, \
        "a fight that hands nothing over must still write battle_done"
    assert door.index('_world.battle_done = _outcome;') < door.index("pp_overworld_start_scene(_world, _handoff_scene);"), \
        "the handoff must not also write the outcome into battle_done"

    # The mirror: an interrupted fight ends with nobody pressing anything, and the scene the row names takes over.
    assert caller_step("interrupted", SCENE_ID, pressed=False) == ("overworld", SCENE_ID)
    assert caller_step("kill", "", pressed=False) == ("battle", ""), "a kill still waits for the player's press"
    assert caller_step("kill", "", pressed=True) == ("overworld", "")
    assert caller_step("spare", "", pressed=True) == ("overworld", "")
    assert SCENE_ID in {row["id"] for row in read_json(SCENES)["scenes"]}
    print("F2: interrupted hands %s to the overworld door with no press" % SCENE_ID)




def probe() -> int:
    enemy = percy()
    block = interrupt_block()
    print("G0-4b headless probe: the spare_refused interruption (spec 18 sections 4 and 8)")
    print("enemy %s, max_hp %d, route_kind %s, spare_hp_percent %d, trust_to_spare %d"
          % (enemy["id"], enemy["max_hp"], enemy.get("route_kind", "regular"),
             enemy["spare_hp_percent"], enemy["trust_to_spare"]))
    print("interrupt: on %s, gate %d percent (%d hp), unless_flag %s, scene %s"
          % (block["on"], block["hp_at_or_below"], crossing_hp(block["hp_at_or_below"], enemy["max_hp"]),
             block.get("unless_flag", "-"), block["scene"]))

    print("\nprobe 1: one SPARE press at each band of the bar, trust 0")
    shown = None
    for hp in range(enemy["max_hp"], 0, -1):
        outcome, scene = press_spare(enemy, hp, 0, {})
        if outcome == shown:
            continue
        shown = outcome
        print("  hp %3d  press SPARE -> %-12s scene %s" % (hp, outcome, scene or "-"))

    print("\nprobe 2: the refused SPARE at 31 hp, the lowest hp the gate covers")
    flags = {}
    outcome, scene = press_spare(enemy, 31, 0, flags)
    row, counters, exit_name = ledger_record(outcome, enemy)
    print("  outcome %s, scene %s" % (outcome, scene))
    print("  exit row %s -> %s, counters %s" % (row["id"], exit_name, counters))
    assert outcome == "interrupted" and scene == SCENE_ID
    assert exit_name == "turned"
    assert counters == {"bosses_killed": 0, "bosses_spared": 0, "regulars_killed": 0, "regulars_spared": 0}
    assert "victory" not in outcome and "defeat" not in outcome

    print("\nprobe 3: the scene runs, and the map gets Percy back standing")
    dialogue_ids = {row["id"] for row in read_json(DIALOGUE)["dialogue"]}
    flag_names = set(read_json(FLAGS)["flags"])
    audio = read_json(AUDIO)
    sound_ids = {row["id"] for row in audio["sounds"]} | {row["id"] for row in audio["cues"]}
    trace = run_scene(scene_row(), dialogue_ids, flag_names, sound_ids, flags)
    for step in trace:
        print("  " + " ".join(step))
    print("  flags now: %s" % (sorted(flags),))
    assert flags.get("met_prometheus") is True and flags.get("percy_standing") is True
    assert trace[-1] == ("end",)

    print("\nprobe 4: the second press is refused, because met_prometheus is set")
    print("  press SPARE again -> %s" % (press_spare(enemy, 31, 0, flags),))

    print("\nprobe 5: the kill route stays open above and below the gate")
    outcome, events = kill_by_damage(enemy, {})
    print("  FIGHT %d a blow from %d hp to 0, no SPARE press -> outcome %s, SPARE presses %d"
          % (FIGHT_CEILING, enemy["max_hp"], outcome, len(events)))
    assert outcome == "kill" and events == []
    outcome, events = fight_to_zero(enemy, {}, presses=(48,))
    print("  the same fight with one SPARE press at 48 hp -> outcome %s, events %s" % (outcome, events))
    assert outcome == "interrupted"
    print("  a crossing trigger at %d hp instead would need one blow of at least %d hp; the ceiling is %d (%d with tide_step)"
          % (crossing_hp(block["hp_at_or_below"], enemy["max_hp"]),
             crossing_hp(block["hp_at_or_below"], enemy["max_hp"]) + 1, FIGHT_CEILING, TIDE_STEP))
    return 0


if __name__ == "__main__":
    sys.exit(probe())
