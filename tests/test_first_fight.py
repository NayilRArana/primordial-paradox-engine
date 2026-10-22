"""The first fight, computed from the data, without running GameMaker (card t_6cd2cc3c, step S6).

Nothing here executes GML. Every check reads a real file and computes the answer from it, so a change
in the data, the macros or the spec fails here instead of in the first playtest.

Sources this file measures, never restates:

    data/enemies/all.json                    the deck_hound row: 2 hp, attack 2 to 2
    data/encounters/all.json                 beat 23 deck_hound, beat 28 tutorial_sailors
    data/mechanics/pacing_recipes.json       beat 23 is 48 s, beat 28 is 90 s, PAC-26 first fight band
    data/mechanics/jrpg_recipes.json         DM-05, the ratio damage recipe behind decision 2
    data/characters/party.json               the hero's 20 hp and power_multiplier 1.0
    data/dialogue/all.json                   the three talk option lines per fight
    game/scripts/pp_config/pp_config.gml     PP_FIGHT_DAMAGE_MIN 2, PP_FIGHT_DAMAGE_MAX 12
    game/scripts/pp_battle_director/...gml   pp_battle_fight_damage, pp_battle_spare_allowed, the talk branch
    game/scripts/pp_battle_commands/...gml   the FIGHT entry is enabled on the first menu frame
    knowledge/mechanics/JRPG-MECHANICS.md    decision 2, the enemy damage formula and the ceiling of 5
    specs/07-battle-director.md              the FIGHT row, the SPARE condition, rule 4
    specs/16-talk-command.md                 the option list, the mercy meter, section 9 the fallback

What is proven, in the card's own order:

  1. the damage this file computes is the director's own function, on three worked cases, and the
     macros are the numbers spec 07 prints in its FIGHT row;
  2. one FIGHT command removes the enemy at every bar power, so no timing press can fail the kill;
  3. no single hit on the hero is above 5, at every defence the demo allows and under both damage
     paths the engine could take (decision 2, and the raw attack roll the dodge arena subtracts);
  4. the hero survives the worst case for as many turns as the fight can run, with margin to spare;
  5. the authored turn count gives 48 s, inside PAC-26's 45 to 60, and the band is met by exactly one
     turn count, so the number is forced rather than chosen;
  6. the TALK fight reaches SPARE after three context options, and the mercy meter agrees with the
     director's trust counter that three is the number;
  7. the fallback line is deterministic with no model and no RNG, and it is in its own pool;
  8. raising the enemy's hp or its attack in a copy of the data breaks these checks, so they can fail.

Two things this file deliberately does not assert, both reported on the card rather than decided here:

  - Spec 07 acceptance 1 says a FIGHT win "always" gets a dodge phase in reply, while
    pp_battle_after_message enters the result before the enemy turn when the result is already a kill.
    The survivability bound does not depend on which wording wins, so neither is encoded.
  - The encounter's talk block carries mercy_per_option and the director's TALK carries
    trust_per_talk. Both reach the same threshold in three talks and this file asserts that they
    agree, without ruling on which meter the shipping TALK uses.

No test in this file reads the network, writes a tracked data file, or needs a key.
"""

from __future__ import annotations

import json
import math
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The two row files can be pointed at a copy, so a mutation can be shown to fail these tests and not
# only a helper.
ENEMIES_PATH = os.environ.get("PP_FIRST_FIGHT_ENEMIES") or os.path.join(ROOT, "data", "enemies", "all.json")
ENCOUNTERS_PATH = os.environ.get("PP_FIRST_FIGHT_ENCOUNTERS") or os.path.join(ROOT, "data", "encounters", "all.json")
PARTY_PATH = os.path.join(ROOT, "data", "characters", "party.json")
DIALOGUE_PATH = os.path.join(ROOT, "data", "dialogue", "all.json")
PACING_PATH = os.path.join(ROOT, "data", "mechanics", "pacing_recipes.json")
JRPG_PATH = os.path.join(ROOT, "data", "mechanics", "jrpg_recipes.json")
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
DIRECTOR_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
COMMANDS_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")
SPEC_07 = os.path.join(ROOT, "specs", "07-battle-director.md")
SPEC_16 = os.path.join(ROOT, "specs", "16-talk-command.md")
KNOWLEDGE = os.path.join(ROOT, "knowledge", "mechanics", "JRPG-MECHANICS.md")

ENEMY_ID = "deck_hound"
FIRST_ENCOUNTER = "deck_hound"
TALK_ENCOUNTER = "tutorial_sailors"

# The defences the demo can field: DM-05's pp_mapping says hero defence 0 to 2.
DEMO_DEFENCES = (0, 1, 2)

NETWORK_TOKENS = ("urllib", "requests", "socket", "http.client", "httplib", "aiohttp", "ftplib")


# --------------------------------------------------------------------------- reading text and data


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def code_only(text: str) -> str:
    """Drop // and /// comments so a structural check reads code, not prose."""
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def brace_block(text: str, marker: str) -> str:
    """The brace balanced block that starts at the first '{' after marker."""
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
    """The whole text of one GML function, braces included."""
    return brace_block(text, "function %s(" % name)


def macro(text: str, name: str) -> int:
    """A numeric #macro from pp_config.gml, read rather than restated."""
    match = re.search(r"^#macro\s+%s\s+(-?\d+)\s*$" % re.escape(name), text, re.M)
    assert match, "no numeric #macro %s in pp_config.gml" % name
    return int(match.group(1))


def find_row(document: dict, collection: str, row_id: str) -> dict:
    """The one row in a data document with this id, or a loud failure."""
    rows = document.get(collection)
    assert isinstance(rows, list) and rows, "no %s list in the document" % collection
    found = [row for row in rows if row.get("id") == row_id]
    assert len(found) == 1, "expected one %s row %r, found %d" % (collection, row_id, len(found))
    return found[0]


def section(text: str, heading: str) -> str:
    """One markdown section, from its heading to the next level two heading."""
    start = text.index(heading)
    rest = text[start:]
    nxt = rest.find("\n## ", len(heading))
    return rest if nxt == -1 else rest[:nxt]


def flat(text: str) -> str:
    """Prose with its line wrapping removed, so a phrase can be found across a wrap."""
    return " ".join(text.split())


def display_text(line: str) -> str:
    """A message board line without the leading '* ' narration marker the dialogue rows use."""
    text = line.strip()
    return text[2:].strip() if text.startswith("* ") else text


# --------------------------------------------------------------------------- the formulas


def gml_round(value: float) -> int:
    """GameMaker's round to nearest, halves away from zero.

    A tie is never relied on: every case this file feeds it is asserted not to land on a half, so the
    tie rule cannot hide a formula difference.
    """
    return int(math.floor(value + 0.5)) if value >= 0 else -int(math.floor(-value + 0.5))


def fight_damage(power: int, minimum: int, maximum: int, multiplier: float) -> int:
    """pp_battle_fight_damage, reimplemented from its own body and the two macros.

    Body under test, pinned by test_the_gml_function_is_the_shape_this_file_reimplements:
        var _p = clamp(_power, 0, 100);
        var _raw = PP_FIGHT_DAMAGE_MIN + (PP_FIGHT_DAMAGE_MAX - PP_FIGHT_DAMAGE_MIN) * (_p / 100);
        return max(1, round(_raw * _battle.actor.power_multiplier));
    game/scripts/pp_battle_director/pp_battle_director.gml:208
    """
    p = max(0, min(100, power))
    raw = minimum + (maximum - minimum) * (p / 100)
    return max(1, gml_round(raw * multiplier))


def decision_two_hit(power: int, defence: float, roll: int) -> int:
    """Decision 2, the DQ1 ratio shape: (power - half defence) * roll / 1024, truncated, minimum 1.

    knowledge/mechanics/JRPG-MECHANICS.md:413, and DM-05 in data/mechanics/jrpg_recipes.json:293.
    """
    raw = (power - defence / 2) * roll / 1024
    return max(1, int(raw))


def worst_hero_hit(power: int, defence: float, roll_low: int, roll_high: int) -> int:
    """The hardest single hit over the whole roll band, not a sampled one."""
    return max(decision_two_hit(power, defence, roll) for roll in range(roll_low, roll_high + 1))


def normalise(line: str) -> str:
    """Strip and collapse whitespace, lower case: the shape the fallback rule hashes."""
    return " ".join(line.split()).lower()


def fnv1a32(text: str) -> int:
    """FNV-1a 32 bit, the hash spec 16 section 9 step 5 names."""
    value = 0x811C9DC5
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value


def fallback_index(line: str, mercy_before: int, pool: list) -> int:
    """index = (fnv1a32(norm_line) + mercy_before) mod len(pool), no RNG anywhere."""
    assert pool, "the fallback pool is empty"
    return (fnv1a32(normalise(line)) + mercy_before) % len(pool)


def authored_turns(encounter: dict) -> int:
    """The turns the fight can actually run: the authored count, or the TALK route to SPARE."""
    talk = encounter.get("talk") or {}
    return max(encounter["pacing"]["turns"], talk.get("talks_to_spare", 0))


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def config_text() -> str:
    return _read(CONFIG_GML)


@pytest.fixture(scope="module")
def fight_macros(config_text) -> dict:
    return {
        "min": macro(config_text, "PP_FIGHT_DAMAGE_MIN"),
        "max": macro(config_text, "PP_FIGHT_DAMAGE_MAX"),
        "sweep": macro(config_text, "PP_FIGHT_SWEEP_STEPS"),
        "steps_per_second": macro(config_text, "PP_STEPS_PER_SECOND"),
    }


@pytest.fixture(scope="module")
def hero() -> dict:
    return find_row(_load(PARTY_PATH), "characters", "hero")


@pytest.fixture(scope="module")
def hound() -> dict:
    return find_row(_load(ENEMIES_PATH), "enemies", ENEMY_ID)


@pytest.fixture(scope="module")
def first_encounter() -> dict:
    return find_row(_load(ENCOUNTERS_PATH), "encounters", FIRST_ENCOUNTER)


@pytest.fixture(scope="module")
def talk_encounter() -> dict:
    return find_row(_load(ENCOUNTERS_PATH), "encounters", TALK_ENCOUNTER)


@pytest.fixture(scope="module")
def dialogue() -> dict:
    return _load(DIALOGUE_PATH)


@pytest.fixture(scope="module")
def pacing() -> dict:
    return _load(PACING_PATH)


@pytest.fixture(scope="module")
def pac26(pacing) -> dict:
    return find_row(pacing, "recipes", "PAC-26")


@pytest.fixture(scope="module")
def beats(pacing) -> dict:
    return {beat["n"]: beat for beat in pacing["beat_sheet"]["beats"]}


@pytest.fixture(scope="module")
def director_code() -> str:
    return code_only(_read(DIRECTOR_GML))


@pytest.fixture(scope="module")
def knowledge_decision_two() -> str:
    text = _read(KNOWLEDGE)
    start = text.index("**Decision 2.")
    rest = text[start:]
    cut = rest.find("\n\n")
    return rest if cut == -1 else rest[:cut]


@pytest.fixture(scope="module")
def decision_numbers(knowledge_decision_two) -> dict:
    """The roll band, the divisor, the floor and the ceiling, read out of decision 2 itself."""
    match = re.search(
        r"random (\d+) to (\d+), divided by (\d+) and truncated, minimum (\d+)", knowledge_decision_two)
    assert match, knowledge_decision_two
    ceiling = re.search(r"no single bullet or contact hit above (\d+)", knowledge_decision_two)
    assert ceiling, knowledge_decision_two
    low, high, divisor, minimum = (int(group) for group in match.groups())
    return {"low": low, "high": high, "divisor": divisor, "minimum": minimum,
            "ceiling": int(ceiling.group(1))}


# --------------------------------------------------------------------------- 1. the formula


def test_the_macros_are_the_numbers_spec_07_prints(fight_macros):
    """Spec 07's FIGHT row is the source of 2 and 12, and pp_config must carry them."""
    match = re.search(r"sweeps 0 to 100 in (\d+) steps; damage (\d+) to (\d+)", _read(SPEC_07))
    assert match, "spec 07's FIGHT row no longer states the sweep and the damage band"
    sweep, low, high = (int(group) for group in match.groups())
    assert (fight_macros["sweep"], fight_macros["min"], fight_macros["max"]) == (sweep, low, high), (
        "pp_config carries %r, spec 07 says sweep %d, damage %d to %d" % (fight_macros, sweep, low, high))
    assert fight_macros["min"] < fight_macros["max"]
    assert fight_macros["steps_per_second"] == 60


def test_the_gml_function_is_the_shape_this_file_reimplements(director_code, hero):
    """The three lines of pp_battle_fight_damage, so a rewrite cannot pass as the same formula."""
    body = function_body(director_code, "pp_battle_fight_damage")
    assert "clamp(_power, 0, 100)" in body, body
    assert "PP_FIGHT_DAMAGE_MIN + (PP_FIGHT_DAMAGE_MAX - PP_FIGHT_DAMAGE_MIN) * (_p / 100)" in body, body
    assert "max(1, round(_raw * _battle.actor.power_multiplier))" in body, body
    # The multiplier is the actor's, and the actor's comes from party data.
    assert "power_multiplier: _party.power_multiplier" in director_code
    assert isinstance(hero["power_multiplier"], (int, float))
    assert 0 < hero["power_multiplier"] <= 1.0, (
        "a multiplier above 1 would lift the whole band past the numbers spec 07 prints")


def test_three_worked_cases_match_the_director(fight_macros, hero):
    """Power 0, 50 and 100 at the hero's own multiplier: 2, 7 and 12, the midpoint included."""
    low, high, multiplier = fight_macros["min"], fight_macros["max"], hero["power_multiplier"]
    cases = ((0, low), (50, (low + high) // 2), (100, high))
    for power, expected in cases:
        raw = low + (high - low) * (power / 100)
        assert raw != math.floor(raw) + 0.5, "power %d lands on a rounding tie, which hides a difference" % power
        got = fight_damage(power, low, high, multiplier)
        assert got == expected, "power %d gave %d, expected %d" % (power, got, expected)
    assert (fight_damage(0, low, high, multiplier), fight_damage(50, low, high, multiplier),
            fight_damage(100, low, high, multiplier)) == (2, 7, 12)


def test_the_bar_is_monotonic_so_no_press_is_wasted(fight_macros, hero):
    """Every power on the bar gives a whole number that never falls as the press gets better."""
    low, high, multiplier = fight_macros["min"], fight_macros["max"], hero["power_multiplier"]
    damages = [fight_damage(power, low, high, multiplier) for power in range(0, 101)]
    assert damages == sorted(damages), "a better press cannot do less damage"
    assert all(isinstance(value, int) for value in damages)
    assert min(damages) == low and max(damages) == high


# --------------------------------------------------------------------------- 2. one command wins


def assert_one_fight_kills(enemy: dict, fight_macros: dict, hero: dict) -> int:
    """The one command predicate, shared by the real row and the mutated copies.

    Returns the weakest hit on the bar. Raises AssertionError when any press would leave the enemy
    standing, which is the card's required failing case.
    """
    low, high, multiplier = fight_macros["min"], fight_macros["max"], hero["power_multiplier"]
    weakest = min(fight_damage(power, low, high, multiplier) for power in range(0, 101))
    assert weakest >= enemy["max_hp"], (
        "the enemy has %d hp and the weakest FIGHT press does %d, so one command can fail"
        % (enemy["max_hp"], weakest))
    assert fight_damage(0, low, high, multiplier) >= enemy["max_hp"], (
        "a bar confirmed at its far end does %d, which does not remove %d hp"
        % (fight_damage(0, low, high, multiplier), enemy["max_hp"]))
    return weakest


def test_one_fight_removes_the_enemy_at_every_bar_power(hound, fight_macros, hero, first_encounter):
    """The kill does not depend on the timing press, which is what makes it one command."""
    assert first_encounter["enemies"] == [ENEMY_ID], first_encounter["enemies"]
    weakest = assert_one_fight_kills(hound, fight_macros, hero)
    assert weakest == fight_macros["min"] == hound["max_hp"] == 2
    assert hound["max_hp"] <= fight_macros["min"]


def test_fight_is_the_first_enabled_entry_on_the_first_menu_frame(director_code):
    """One command means one confirm, with no cursor movement before it."""
    commands = code_only(_read(COMMANDS_GML))
    table = function_body(commands, "pp_command_table")
    assert table.index("PPCommand.fight") < table.index("PPCommand.power")
    state = function_body(commands, "pp_command_state")
    fight_case = state[state.index("case PPCommand.fight:"):]
    fight_case = fight_case[:fight_case.index("case PPCommand.power:")]
    assert "enabled: true" in fight_case, fight_case
    assert 'reason: ""' in fight_case, fight_case
    assert "cursor: PPCommand.fight" in function_body(director_code, "pp_battle_new")


def test_the_first_encounter_is_beat_23_and_the_beat_says_one_command(hound, first_encounter, beats):
    """The rows are the first fight the beat sheet describes, not a later one relabelled."""
    beat = beats[first_encounter["beat"]]
    assert first_encounter["beat"] == 23
    assert first_encounter["beat_id"] == beat["id"]
    assert beat["kind"] == "battle"
    assert beat["seconds"] == first_encounter["pacing"]["seconds"]
    assert "one command win" in beat["beat"], beat["beat"]
    assert hound["route_kind"] == "regular"


def test_both_win_dialogues_resolve(hound, first_encounter, talk_encounter, dialogue):
    """A fight that ends on a missing dialogue id shows '* ...' instead of its ending."""
    rows = {row["id"]: row for row in dialogue["dialogue"]}
    for key, encounter in (("win_dialogue_kill", first_encounter), ("win_dialogue_spare", talk_encounter)):
        row = rows.get(encounter[key])
        assert row is not None, "%s %r does not resolve" % (key, encounter[key])
        assert row["lines"], row
    talk = rows.get(hound["talk_dialogue"])
    assert talk is not None and len(talk["lines"]) >= 1


# --------------------------------------------------------------------------- 3. no hit above 5


def test_decision_two_and_dm05_carry_the_same_band(knowledge_decision_two, decision_numbers):
    """The knowledge paragraph and the recipe it cites must not drift apart."""
    prose = flat(knowledge_decision_two)
    assert "half of hero defense" in prose
    assert "truncated" in prose
    assert (decision_numbers["low"], decision_numbers["high"], decision_numbers["divisor"],
            decision_numbers["minimum"], decision_numbers["ceiling"]) == (256, 511, 1024, 1, 5)

    recipe = find_row(_load(JRPG_PATH), "recipes", "DM-05")
    assert "from 256 to 511, divide by 1024 and drop the remainder" in recipe["rule"], recipe["rule"]
    assert "Feeds decision 2" in recipe["pp_mapping"], recipe["pp_mapping"]


def assert_hits_stay_under_the_ceiling(enemy: dict, numbers: dict) -> int:
    """The ceiling predicate: at every demo defence, and across the whole roll band."""
    ceiling = numbers["ceiling"]
    worst = 0
    for defence in DEMO_DEFENCES:
        hardest = worst_hero_hit(enemy["attack"]["max"], defence, numbers["low"], numbers["high"])
        assert hardest <= ceiling, (
            "attack %d at defence %d hits for %d, above the ceiling of %d"
            % (enemy["attack"]["max"], defence, hardest, ceiling))
        worst = max(worst, hardest)
    return worst


def test_no_single_hit_exceeds_five_at_every_demo_defence(hound, decision_numbers):
    """Defence 0 to 2 with the enemy's own attack: the hardest hit over the whole roll band."""
    assert hound["attack"]["min"] == hound["attack"]["max"] == 2
    assert decision_numbers["minimum"] == 1
    assert assert_hits_stay_under_the_ceiling(hound, decision_numbers) == 1
    # The floor applies at every defence the formula can be handed, so the ceiling is not luck.
    for defence in range(0, 11):
        assert worst_hero_hit(hound["attack"]["max"], defence, decision_numbers["low"],
                              decision_numbers["high"]) <= decision_numbers["ceiling"]


def test_the_engines_own_attack_roll_is_under_the_ceiling(director_code, hound, decision_numbers):
    """The dodge arena subtracts the raw roll, not decision 2, so both paths have to be bounded.

    pp_battle_step_dodge does hp - arena.attack and pp_battle_roll_attack rolls the enemy's attack
    band, so the roll's own ceiling is checked beside the formula's.
    game/scripts/pp_battle_director/pp_battle_director.gml:298
    """
    ceiling = decision_numbers["ceiling"]
    roll_body = function_body(director_code, "pp_battle_roll_attack")
    assert "pp_rng_int(_battle.rng, _atk.min, _atk.max)" in roll_body, roll_body
    assert hound["attack"]["max"] <= ceiling, (
        "the raw attack roll of %d is already above the %d ceiling" % (hound["attack"]["max"], ceiling))
    dodge = function_body(director_code, "pp_battle_step_dodge")
    assert "_battle.actor.hp = max(0, _battle.actor.hp - _battle.arena.attack)" in dodge, dodge
    # No critical or damage multiplier exists beside the roll, so the raw band is the whole bound.
    assert "critical" not in director_code.lower()


# --------------------------------------------------------------------------- 4. it cannot be lost


def assert_hero_survives(enemy: dict, hero: dict, turns: int, numbers: dict) -> int:
    """The survivability predicate: every turn answered by the hardest hit, no healing, still up."""
    hardest = worst_hero_hit(enemy["attack"]["max"], 0, numbers["low"], numbers["high"])
    hp = hero["max_hp"]
    for turn in range(1, turns + 1):
        hp = max(0, hp - hardest)
        assert hp > 0, "%d turns at %d drops the hero on turn %d" % (turns, hardest, turn)
    hits_to_defeat = math.ceil(hero["max_hp"] / hardest)
    assert hits_to_defeat - turns >= 4, (
        "only %d hits of margin over %d authored turns, decision 2 promises four clean mistakes"
        % (hits_to_defeat - turns, turns))
    return hardest


def test_the_hero_survives_the_worst_case_for_every_turn_the_fight_runs(
        hero, first_encounter, talk_encounter, decision_numbers, pac26):
    """Every turn answered by the hardest hit, for both S6 fights, with the margin counted."""
    assert pac26["params"]["first_fight_can_be_lost"] is False
    assert pac26["params"]["first_fight_one_command_win"] is True
    assert "a first fight that can be lost" in pac26["forbidden"]

    enemies = _load(ENEMIES_PATH)
    for encounter in (first_encounter, talk_encounter):
        assert len(encounter["enemies"]) == 1, encounter["enemies"]
        enemy = find_row(enemies, "enemies", encounter["enemies"][0])
        turns = authored_turns(encounter)
        assert turns == 3, "%s runs %d turns" % (encounter["id"], turns)
        hardest = assert_hero_survives(enemy, hero, turns, decision_numbers)
        assert hardest == 1
        assert turns * hardest == 3 < hero["max_hp"] == 20


def test_the_two_fights_share_one_attack_band(hound, talk_encounter):
    """The bound is a property of the authored fight pair, not of one lucky row."""
    enemies = _load(ENEMIES_PATH)
    for enemy_id in talk_encounter["enemies"]:
        row = find_row(enemies, "enemies", enemy_id)
        assert row["attack"] == hound["attack"], (
            "%s attacks %r, the first fight bound was computed at %r" % (enemy_id, row["attack"], hound["attack"]))


# --------------------------------------------------------------------------- 5. the length


def test_the_authored_turn_count_gives_48_seconds_inside_45_to_60(first_encounter, talk_encounter, pac26, beats):
    """27 s fixed plus 21 s a turn, solved from the two beats, then checked against PAC-26."""
    band = pac26["params"]["first_fight_seconds"]
    assert band == [45, 60]
    assert first_encounter["pacing"]["band_seconds"] == band
    assert beats[23]["seconds"] == 48 and beats[28]["seconds"] == 90

    # The two authored beats are two equations; solve them rather than trust the stored shares.
    per_turn = (beats[28]["seconds"] - beats[23]["seconds"]) // 2
    fixed = beats[23]["seconds"] - per_turn
    assert (fixed, per_turn) == (27, 21)
    for encounter in (first_encounter, talk_encounter):
        pacing = encounter["pacing"]
        assert (pacing["seconds_fixed"], pacing["seconds_per_turn"]) == (fixed, per_turn), (
            "%s stores %r, the beats give %r"
            % (encounter["id"], (pacing["seconds_fixed"], pacing["seconds_per_turn"]), (fixed, per_turn)))
        assert pacing["seconds"] == pacing["seconds_fixed"] + pacing["turns"] * pacing["seconds_per_turn"]

    seconds = first_encounter["pacing"]["seconds"]
    assert band[0] <= seconds <= band[1], "%d s is outside PAC-26's %r" % (seconds, band)
    assert seconds == 48

    # Exactly one turn count lands inside the band, so the authored 1 is forced by the numbers.
    inside = [turns for turns in range(0, 6) if band[0] <= fixed + turns * per_turn <= band[1]]
    assert inside == [first_encounter["pacing"]["turns"]] == [1], inside


def test_the_talk_fight_length_is_the_same_two_numbers(talk_encounter, pac26):
    """The second S6 fight is 90 s by the same shares, and PAC-26's band is the first fight only."""
    assert talk_encounter["pacing"]["seconds"] == 90
    assert talk_encounter["beat"] == 28
    assert talk_encounter["beat_id"] == "hold_encounter_talk"
    assert "band_seconds" not in talk_encounter["pacing"], "PAC-26 bands the first fight, not the talk fight"
    assert pac26["params"]["first_fight_seconds"] == [45, 60]


# --------------------------------------------------------------------------- 6. TALK to SPARE


def test_three_options_fill_the_mercy_meter_exactly(first_encounter, talk_encounter, dialogue):
    """option_count and the per option value must add up to the threshold, not past it."""
    rows = {row["id"]: row for row in dialogue["dialogue"]}
    for encounter in (first_encounter, talk_encounter):
        talk = encounter["talk"]
        option_row = rows.get(talk["options_dialogue"])
        assert option_row is not None, "%s names an options dialogue that does not exist" % encounter["id"]
        assert len(option_row["lines"]) == talk["option_count"], (
            "%s says %d options, the dialogue has %d"
            % (encounter["id"], talk["option_count"], len(option_row["lines"])))
        fill = talk["option_count"] * talk["mercy_per_option"]
        assert fill == talk["mercy_to_spare"], (
            "%s: %d options at %d is %d, the threshold is %d"
            % (encounter["id"], talk["option_count"], talk["mercy_per_option"], fill, talk["mercy_to_spare"]))
        # No remainder: a leftover would mean a fourth option, which no data row carries.
        assert talk["mercy_to_spare"] // talk["mercy_per_option"] == talk["talks_to_spare"]


def test_the_mercy_meter_and_the_trust_counter_agree_on_three_talks(first_encounter, talk_encounter):
    """Spec 16 derives trust from mercy, the director counts trust; both must need 3 talks."""
    spec = section(_read(SPEC_16), "## 2. The mercy meter")
    match = re.search(r"trust = floor\(mercy / (\d+)\)", spec)
    assert match, "spec 16 section 2 no longer states how trust derives from mercy"
    divisor = int(match.group(1))
    per_option = re.search(r"Context option TALK that lands on a weak topic \| \+(\d+) \|", spec)
    assert per_option, "spec 16 section 2 no longer states the context option gain"

    enemies = _load(ENEMIES_PATH)
    for encounter in (talk_encounter, first_encounter):
        enemy = find_row(enemies, "enemies", encounter["enemies"][0])
        talk = encounter["talk"]
        assert int(per_option.group(1)) == talk["mercy_per_option"] == 20
        talks_by_mercy = math.ceil(talk["mercy_to_spare"] / talk["mercy_per_option"])
        talks_by_trust = math.ceil(enemy["trust_to_spare"] / encounter["trust_per_talk"])
        assert talks_by_mercy == talks_by_trust == talk["option_count"] == 3, (
            "%s: mercy needs %d, trust needs %d, the data offers %d"
            % (encounter["id"], talks_by_mercy, talks_by_trust, talk["option_count"]))
        trust_at_threshold = talk["mercy_to_spare"] // divisor
        assert trust_at_threshold >= enemy["trust_to_spare"], (
            "%s: mercy %d gives trust %d, the enemy needs %d"
            % (encounter["id"], talk["mercy_to_spare"], trust_at_threshold, enemy["trust_to_spare"]))


def test_the_spare_rule_in_the_director_is_the_two_conditions_the_data_uses(director_code):
    """The simulated spare must be the engine's spare, not a rule this file invented."""
    body = function_body(director_code, "pp_battle_spare_allowed")
    assert "if (_battle.enemy_hp <= 0) return false;" in body, body
    assert "if (_battle.trust >= _battle.enemy.trust_to_spare) return true;" in body, body
    assert "(_battle.enemy_hp <= (_battle.enemy.max_hp * _battle.enemy.spare_hp_percent / 100))" in body, body
    assert "enabled at trust 3 or enemy hp at 25 percent or less" in _read(SPEC_07)


def test_three_talk_turns_reach_spare_with_the_enemy_untouched(hound, first_encounter, director_code):
    """The whole TALK route, turn by turn, on data only: no model, no damage, spare on turn 3."""
    talk = first_encounter["talk"]
    enemy_hp = hound["max_hp"]
    mercy = 0
    spare_on = None
    for turn in range(1, talk["option_count"] + 1):
        mercy = min(100, mercy + talk["mercy_per_option"])
        trust = mercy // 20
        if trust >= hound["trust_to_spare"] or enemy_hp <= (hound["max_hp"] * hound["spare_hp_percent"] / 100):
            spare_on = spare_on or turn
        assert enemy_hp == hound["max_hp"], "TALK damaged the enemy on turn %d" % turn
    assert mercy == talk["mercy_to_spare"] == 60
    assert spare_on == 3, "spare opened on turn %r, the card says three options" % spare_on

    # The director's TALK branch really never damages: no hurt_enemy call, no hp write.
    begin = function_body(director_code, "pp_battle_begin_action")
    talk_case = begin[begin.index("case PPCommand.talk:"):]
    talk_case = talk_case[:talk_case.index("case PPCommand.spare:")]
    assert "pp_battle_hurt_enemy" not in talk_case, talk_case
    assert "enemy_hp" not in talk_case, talk_case
    assert "_battle.trust += _battle.encounter.trust_per_talk" in talk_case, talk_case


def test_the_hp_route_never_opens_on_a_two_hp_enemy(hound):
    """spare_hp_percent 25 of 2 hp is below 1, so no positive hp can trip it and talk is the only route."""
    threshold = hound["max_hp"] * hound["spare_hp_percent"] / 100
    assert threshold == 0.5
    assert threshold < 1
    assert all(hp > threshold for hp in range(1, hound["max_hp"] + 1)), (
        "a positive hp would open the percentage route, which changes how the fight can end")


def test_the_option_count_fits_the_panel_spec_16_draws(first_encounter, talk_encounter):
    """Three options is legal only because the spec allows up to four lines plus SAY IT YOURSELF."""
    spec = section(_read(SPEC_16), "## 1. The command the player uses")
    match = re.search(r"up to (\d+) lines from the enemy's talk_dialogue", spec)
    assert match, "spec 16 section 1 no longer states the option ceiling"
    ceiling = int(match.group(1))
    assert ceiling == 4
    assert "SAY IT YOURSELF" in spec
    for encounter in (first_encounter, talk_encounter):
        assert 1 <= encounter["talk"]["option_count"] <= ceiling


# --------------------------------------------------------------------------- 7. the fallback


def test_the_fallback_line_is_in_its_own_pool_and_moves_no_mercy(first_encounter, talk_encounter):
    """A fallback that is not in the pool would be a line no replay can ever reach.

    The pool lines are compared with their leading '* ' narration marker removed, the marker the
    dialogue rows carry (data/dialogue/all.json). The two authored rows differ on whether they use
    it, which is reported on the card rather than fixed here.
    """
    spec = flat(section(_read(SPEC_16), "## 10. Per enemy talk card, the data"))
    assert "60 characters max" in spec
    for encounter in (first_encounter, talk_encounter):
        talk = encounter["talk"]
        pool = [display_text(line) for line in talk["fallback_pool"]]
        assert display_text(talk["fallback_line"]) in pool, (
            "%s carries a fallback line outside its pool" % encounter["id"])
        assert len(talk["fallback_pool"]) == 3
        assert len(set(pool)) == 3, "duplicate lines make the index look deterministic by accident"
        for line in talk["fallback_pool"] + [talk["fallback_line"]]:
            assert len(line) <= 60, "%s has a reply line of %d characters" % (encounter["id"], len(line))
        assert talk["fallback_delta"] == 0
        assert -20 <= talk["fallback_delta"] <= 20, "spec 16 clamps a delta to -20..20"
        assert isinstance(talk["fallback_mood"], str) and talk["fallback_mood"]


def test_the_fallback_rule_is_the_specs_rule_and_it_is_deterministic(first_encounter, talk_encounter):
    """Same line, same mercy, same words: the property spec 16 says makes the tests possible."""
    spec = _read(SPEC_16)
    assert re.search(r"index = \(fnv1a32\(norm_line\) \+ mercy_before\) mod len\(pool\)", spec), (
        "spec 16 section 9 step 5 no longer states the deterministic index")
    assert "No RNG anywhere" in spec

    for encounter in (first_encounter, talk_encounter):
        talk = encounter["talk"]
        rule = talk["fallback_rule"]
        assert "fnv1a32" in rule and "modulo the pool length" in rule and "no RNG" in rule, rule
        pool = talk["fallback_pool"]
        for line in ("how long have you been out here", "* a low growl", ""):
            for mercy in (0, 20, 60, 100):
                first = fallback_index(line, mercy, pool)
                assert first == fallback_index(line, mercy, pool), "the index is not deterministic"
                assert 0 <= first < len(pool), "%d is outside a pool of %d" % (first, len(pool))
        # The pool is not one line repeated: a small sample reaches all three indices.
        seen = {fallback_index(line, mercy, pool)
                for line in ("one", "two", "three", "four", "five", "six") for mercy in (0, 20, 40, 60)}
        assert seen == set(range(len(pool))), "%s only reaches %r of its pool" % (encounter["id"], seen)


def test_the_fallback_needs_no_model_and_no_network(first_encounter):
    """Spec 16 makes the fallback the shipping path for offline play, in 0 steps."""
    spec = section(_read(SPEC_16), "## 9. The deterministic fallback, when there is no model")
    assert "in 0 steps" in spec
    assert "offline play" in spec
    assert "The fallback is not a stub" in spec
    # The encounter row carries the reply, so the turn is answerable from the data alone.
    assert first_encounter["talk"]["fallback_line"].strip()
    # This file must not start reaching the network: its import list is scanned, the same way
    # tests/test_beat_sheet.py scans its own.
    source = _read(os.path.abspath(__file__))
    for token in NETWORK_TOKENS:
        assert not re.search(r"^\s*(?:import|from)\s+" + re.escape(token), source, re.M), (
            "this test file imports %s" % token)


# --------------------------------------------------------------------------- 8. the checks can fail


def _mutated_enemy(tmp_path, field: str, value: int) -> dict:
    """A copy of the enemy row with one number raised, written under tmp_path and never in data/."""
    document = _load(ENEMIES_PATH)
    row = find_row(document, "enemies", ENEMY_ID)
    if field == "max_hp":
        row["max_hp"] = value
    elif field == "attack":
        row["attack"] = {"min": value, "max": value}
    else:
        raise AssertionError("unknown field %r" % field)
    path = tmp_path / ("enemies_%s_%d.json" % (field, value))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return find_row(_load(str(path)), "enemies", ENEMY_ID)


def test_raising_the_enemy_hp_breaks_the_one_command_win(tmp_path, fight_macros, hero):
    """The card's own failing case: 3 hp and 20 hp must both be refused by the real predicate.

    The cases are written as their own copies, so the check does not depend on what the file under
    test happens to hold; the 2 hp case is the one that must pass.
    """
    assert assert_one_fight_kills(_mutated_enemy(tmp_path, "max_hp", 2), fight_macros, hero) == 2

    for hp in (3, 20):
        row = _mutated_enemy(tmp_path, "max_hp", hp)
        assert row["max_hp"] == hp and row["id"] == ENEMY_ID
        with pytest.raises(AssertionError) as caught:
            assert_one_fight_kills(row, fight_macros, hero)
        assert "weakest FIGHT press" in str(caught.value), str(caught.value)


def test_raising_the_enemy_attack_breaks_the_ceiling_and_the_margin(tmp_path, hero, decision_numbers,
                                                                    first_encounter, hound):
    """The other side of the card: the damage checks can fail too, so they are measurements."""
    assert assert_hits_stay_under_the_ceiling(hound, decision_numbers) == 1
    turns = authored_turns(first_encounter)
    assert_hero_survives(hound, hero, turns, decision_numbers)

    heavier = _mutated_enemy(tmp_path, "attack", 13)
    with pytest.raises(AssertionError) as caught:
        assert_hits_stay_under_the_ceiling(heavier, decision_numbers)
    assert "above the ceiling" in str(caught.value), str(caught.value)

    # At 10 the ceiling still holds, but the four mistake promise no longer does, and that is a failure too.
    middling = _mutated_enemy(tmp_path, "attack", 10)
    assert assert_hits_stay_under_the_ceiling(middling, decision_numbers) == 4
    with pytest.raises(AssertionError) as caught:
        assert_hero_survives(middling, hero, turns, decision_numbers)
    assert "margin" in str(caught.value), str(caught.value)
