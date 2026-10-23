"""G0-4a: enemy phases are data, and the battle director reads them with no branch on an enemy name.

Card t_d1eb2a47, the first third of the split ruled in D4 of `knowledge/GAMEDEV-DECISIONS-2026-10-23.md`. Spec 18
sections 1 and 6 are the source: a phase row is `{hp_at_or_below, pattern_id, talk_set, line_id}`, the breakpoint is a
PERCENT of max_hp compared in integers (section 8 P3), and Percy's bands are 70 percent and 40 percent, which at 120 hp
are 84 and 48.

What this file holds down, and why each one earns its place:

  1. the shipped data is the spec's row, not a row that merely looks plausible: two crossings at 70 and 40 percent,
     `percy_rain` alone above them, `percy_wall` added by the first and `percy_fan` by the second, attack inside the
     hand written checker's band, and each crossing landing on the hp the spec's arithmetic names (84 and 48);
  2. the percent unit is real, not decoration: halving max_hp to 60 moves both crossings to 42 and 24 and leaves the
     bands where they were, which is spec 07's acceptance 5 and the reason section 8 P3 chose percent;
  3. the checker is a gate and not a print: an unknown pattern id, a threshold outside 1 to 99, an ascending or
     duplicate threshold, a fifth row, an attack outside the band, and a pattern already in the pool above the row are
     each refused with a message naming the file, the enemy and the field;
  4. the director reads `_battle.pattern_pool` and `_battle.attack_range`, never `_battle.enemy.patterns` or
     `_battle.enemy.attack`, and the enemy's name appears nowhere in its code. That pair of facts is what makes the
     next boss a data edit rather than a code branch;
  5. the crossing comparison is the integer one spec 18 writes, and the crossing's line is taken and cleared before
     its board opens, so it cannot play twice.

Known gap, recorded rather than hidden: phase 3's own dialogue ids (`talk_percy_phase3`, `percy_phase3_line`) do not
exist yet and data/dialogue/all.json is not this card's file, so both rows name the phase 2 ids and the follow-up card
on the board owns the swap. The checker's job here is that every id resolves today, which it does.

Run: python -m pytest tests/test_enemy_phases.py -q
Headless probe: python tests/test_enemy_phases.py
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
SCHEMA = os.path.join(ROOT, "data", "schemas", "enemies.schema.json")
DIRECTOR = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")

# Spec 18 section 6, the table and the data block: 70 percent of 120 is 84, 40 percent of 120 is 48.
PERCY_BANDS = (70, 40)
PERCY_CROSSINGS = (84, 48)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def enemies():
    return read_json(ENEMIES)


def percy_rows():
    rows = [row for row in enemies()["enemies"] if row["id"] == "percy"]
    assert len(rows) == 1, "data/enemies/all.json must hold exactly one percy row"
    return rows[0]


def crossing_hp(threshold, max_hp):
    """The highest hp at which `hp * 100 <= threshold * max_hp` holds, in integers only.

    This is the director's own comparison (`pp_battle_enemy_phase_reached`), solved for hp rather than guessed at.
    """
    return (threshold * max_hp) // 100


def phase_walk(enemy):
    """The fight's pool, attack range and TALK set at every hp, top down.

    A mirror of `pp_battle_enemy_phase_sync`, written from the GML rather than from memory: the pool starts as the
    enemy's own patterns, and each row is applied once, in data order, the first time hp satisfies the comparison. It
    is a mirror and not the engine (GameMaker is not installed on this host), which is why the GML's own comparison
    and its pool read are pinned text for text further down.
    """
    max_hp = enemy["max_hp"]
    pool = list(enemy["patterns"])
    attack = dict(enemy["attack"])
    talk = enemy.get("talk_dialogue", "")
    applied = 0
    rows = enemy.get("phases") or []
    out = []
    for hp in range(max_hp, 0, -1):
        while applied < len(rows) and hp * 100 <= rows[applied]["hp_at_or_below"] * max_hp:
            row = rows[applied]
            applied += 1
            pool = pool + [row["pattern_id"]]
            if "attack" in row:
                attack = dict(row["attack"])
            if "talk_set" in row:
                talk = row["talk_set"]
        out.append({"hp": hp, "pool": tuple(pool), "attack": (attack["min"], attack["max"]), "talk": talk})
    return out


# ---------------------------------------------------------------------------------------------------------------
# 1. The shipped row is the spec's row.


def test_percy_ships_the_two_rows_spec_18_section_6_writes():
    row = percy_rows()
    thresholds = [phase["hp_at_or_below"] for phase in row["phases"]]
    assert thresholds == list(PERCY_BANDS), thresholds
    assert [phase["pattern_id"] for phase in row["phases"]] == ["percy_wall", "percy_fan"]
    # Section 6's phase 1 is rain only; C18-1 is the delta that narrows this list, and the checker refuses the wall in
    # both places at once, so the two cannot drift.
    assert row["patterns"] == ["percy_rain"], row["patterns"]
    assert row["max_hp"] == 120 and row["route_kind"] == "boss"


def test_the_crossings_are_the_arithmetic_the_spec_names():
    row = percy_rows()
    crossings = tuple(crossing_hp(phase["hp_at_or_below"], row["max_hp"]) for phase in row["phases"])
    assert crossings == PERCY_CROSSINGS, crossings
    # The numbers in words, so a reader can check the sum without running anything:
    assert 70 * 120 // 100 == 84
    assert 40 * 120 // 100 == 48
    # Strictly descending, which is the order the director walks them in.
    assert 84 > 48


def test_the_attack_stays_inside_the_spec_07_band():
    row = percy_rows()
    low, high = check_data.PHASE_ATTACK_BAND
    assert (low, high) == (3, 6), "spec 07 line 32 gives Percy attack 3 to 6"
    enemy_low, enemy_high = row["attack"]["min"], row["attack"]["max"]
    assert (enemy_low, enemy_high) == (3, 5), "section 6's enemy level range"
    for index, phase in enumerate(row["phases"]):
        attack = phase["attack"]
        assert low <= attack["min"] <= attack["max"] <= high, (index, attack)
        assert attack["min"] >= enemy_low, (index, attack)
    assert row["phases"][0]["attack"] == {"min": 4, "max": 5}
    assert row["phases"][1]["attack"] == {"min": 4, "max": 6}


def test_the_pool_and_the_attack_move_at_each_threshold():
    walk = {step["hp"]: step for step in phase_walk(percy_rows())}
    assert walk[120]["pool"] == ("percy_rain",)
    assert walk[85]["pool"] == ("percy_rain",), "85 hp is above 84, so nothing has crossed"
    assert walk[84]["pool"] == ("percy_rain", "percy_wall"), "84 is the first crossing"
    assert walk[49]["pool"] == ("percy_rain", "percy_wall"), "49 hp is above 48"
    assert walk[48]["pool"] == ("percy_rain", "percy_wall", "percy_fan"), "48 is the second crossing"
    assert walk[1]["pool"] == ("percy_rain", "percy_wall", "percy_fan")
    # The attack is the number the player cannot name, so it moves with the same crossings and needs no label.
    assert (walk[85]["attack"], walk[84]["attack"], walk[48]["attack"]) == ((3, 5), (4, 5), (4, 6))
    # The TALK set follows the same door.
    assert walk[85]["talk"] == "talk_percy"
    assert walk[84]["talk"] == "talk_percy_phase2"


def test_the_breakpoint_is_a_percent_so_halving_max_hp_moves_nothing():
    """Spec 07's acceptance 5, which is the whole reason section 8 P3 chose percent of max_hp."""
    row = json.loads(json.dumps(percy_rows()))
    row["max_hp"] = 60
    walk = {step["hp"]: step for step in phase_walk(row)}
    assert walk[60]["pool"] == ("percy_rain",)
    assert walk[43]["pool"] == ("percy_rain",), "43 of 60 is 71 percent, still phase 1"
    assert walk[42]["pool"] == ("percy_rain", "percy_wall"), "42 of 60 is 70 percent"
    assert walk[24]["pool"] == ("percy_rain", "percy_wall", "percy_fan"), "24 of 60 is 40 percent"
    assert crossing_hp(70, 60) == 42 and crossing_hp(40, 60) == 24


# ---------------------------------------------------------------------------------------------------------------
# 2. The checker refuses each fault, naming the file, the enemy and the field.


def check_messages(root):
    return check_data.check(str(root))


def phase_messages(root, needle):
    return [message for message in check_messages(root)
            if "data/enemies/all.json" in message and needle in message]


def test_a_phase_naming_an_unknown_pattern_id_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][1]["phases"][0]["pattern_id"] = "percy_wall_twice"
    write_json(path, data)

    messages = phase_messages(data_root, "phases[0].pattern_id")
    assert messages, check_messages(data_root)
    assert any("percy_wall_twice" in message for message in messages), messages


def test_a_threshold_outside_one_to_ninety_nine_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][1]["phases"][0]["hp_at_or_below"] = 120
    write_json(path, data)
    messages = phase_messages(data_root, "phases[0].hp_at_or_below")
    assert any("outside 1 to 99" in message for message in messages), messages


def test_an_ascending_or_duplicate_threshold_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"

    data = read_json(path)
    data["enemies"][1]["phases"][0]["hp_at_or_below"] = 40
    data["enemies"][1]["phases"][1]["hp_at_or_below"] = 70
    write_json(path, data)
    messages = phase_messages(data_root, "phases[1].hp_at_or_below")
    assert any("not strictly descending" in message for message in messages), messages

    data = read_json(path)
    data["enemies"][1]["phases"][0]["hp_at_or_below"] = 70
    data["enemies"][1]["phases"][1]["hp_at_or_below"] = 70
    write_json(path, data)
    messages = phase_messages(data_root, "phases[1].hp_at_or_below")
    assert any("duplicate threshold" in message for message in messages), messages


def test_a_fifth_phase_row_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    rows = data["enemies"][1]["phases"]
    for threshold in (30, 20, 10):
        rows.append({"hp_at_or_below": threshold, "pattern_id": "percy_rain",
                     "talk_set": "talk_percy_phase2", "line_id": "percy_phase2_line"})
    write_json(path, data)
    messages = phase_messages(data_root, "phases")
    assert any("at most %d" % check_data.PHASE_ROWS_MAX in message for message in messages), messages


def test_an_attack_outside_the_band_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][1]["phases"][1]["attack"]["max"] = 7
    write_json(path, data)
    messages = phase_messages(data_root, "phases[1].attack.max")
    assert any("PHASE_ATTACK_BAND" in message for message in messages), messages


def test_a_pattern_already_in_the_pool_above_the_row_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][1]["patterns"] = ["percy_rain", "percy_wall"]
    write_json(path, data)
    messages = phase_messages(data_root, "phases[0].pattern_id")
    assert any("already in the pool above this row" in message for message in messages), messages


def test_an_attack_on_a_regular_enemy_phase_row_is_refused(data_root, read_json, write_json):
    """No spec writes a band for a regular enemy, so the checker refuses the row instead of guessing one."""
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][0]["phases"] = [{"hp_at_or_below": 50, "pattern_id": "percy_wall",
                                     "talk_set": "talk_navy_sailor", "line_id": "talk_navy_sailor",
                                     "attack": {"min": 4, "max": 5}}]
    write_json(path, data)
    messages = phase_messages(data_root, "phases[0].attack")
    assert any("route_kind boss" in message for message in messages), messages


def test_the_shipped_data_passes_every_checker_rule():
    assert check_messages(ROOT) == [], check_messages(ROOT)


# ---------------------------------------------------------------------------------------------------------------
# 3. The director is data driven, and the engine comparison is the spec's integer one.

def code_only(text):
    """Drop // comments so these pins read code, not the prose that explains it (tests/test_project.py does the same)."""
    return "\n".join(line if line.find("//") == -1 else line[:line.find("//")] for line in text.split("\n"))


def director_code():
    with open(DIRECTOR, "r", encoding="utf-8-sig") as handle:
        return code_only(handle.read())


def test_the_director_reads_the_phase_fields_and_not_the_enemy_row():
    code = director_code()
    assert "_battle.pattern_pool" in code
    assert "_battle.attack_range" in code
    assert "_battle.talk_set" in code
    assert "_battle.enemy.patterns" not in code, "the pool must be the battle's, so a crossing can append to it"
    assert "_battle.enemy.attack" not in code, "the range must be the battle's, so a phase can raise it"
    assert "_battle.enemy.talk_dialogue" not in code, "the TALK set must be the battle's, so a phase can swap it"


def test_the_crossing_comparison_is_the_integer_one_from_the_spec():
    code = director_code()
    pattern = re.compile(r"enemy_hp\s*\*\s*100\s*<=\s*_row\.hp_at_or_below\s*\*\s*_battle\.enemy\.max_hp")
    assert pattern.search(code), "spec 18 section 1: hp * 100 <= hp_at_or_below * max_hp, no float, no rounding"


def test_no_enemy_name_appears_anywhere_in_the_director_code():
    code = director_code().lower()
    for name in ("percy", "navy_sailor", "deck_hound"):
        assert name not in code, "%r in pp_battle_director.gml would be a branch on an enemy name" % name


def test_the_crossing_line_is_taken_and_cleared_before_its_board_opens():
    code = director_code()
    assert '_battle.phase_line = "";' in code
    body = code[code.index("function pp_battle_after_message(_battle)"):]
    open_board = body.index("pp_battle_say(_battle, pp_battle_dialogue_lines(_line_id)")
    cleared = body.index('_battle.phase_line = "";')
    assert cleared < open_board, "the id must be cleared before the board, so a fast read cannot replay it"


def test_enemy_hp_has_one_door_and_it_is_where_a_crossing_is_applied():
    code = director_code()
    assert code.count("pp_battle_enemy_phase_sync(") == 2, "one definition and one call site, in pp_battle_hurt_enemy"
    hurt = code[code.index("function pp_battle_hurt_enemy(_battle, _damage)"):]
    hurt = hurt[:hurt.index("\n}")]
    assert "pp_battle_enemy_phase_sync(_battle)" in hurt
    assert "enemy_hp > 0" in hurt, "a blow that kills crosses nothing: spec 18 section 4, rule 3 beats rule 5"


def test_the_schema_pins_the_percent_range_and_the_checker_pins_the_count():
    schema = read_json(SCHEMA)
    field = schema["$defs"]["phase"]["properties"]["hp_at_or_below"]
    assert (field["minimum"], field["maximum"]) == (1, 99), field
    assert schema["$defs"]["phase"]["required"] == ["hp_at_or_below", "pattern_id", "talk_set", "line_id"]
    assert check_data.PHASE_ROWS_MAX == 4, "spec 18 section 1: at most four rows"


# ---------------------------------------------------------------------------------------------------------------
# 4. The headless probe the card asks for: Percy's active pattern set at each threshold, printed.

def probe() -> int:
    row = percy_rows()
    max_hp = row["max_hp"]
    print("G0-4a headless probe: enemy phases as data (spec 18 sections 1 and 6)")
    print("enemy: %s, max_hp %d, route_kind %s" % (row["id"], max_hp, row.get("route_kind", "regular")))
    print("pool above the first crossing: %s" % (row["patterns"],))
    walk = phase_walk(row)
    shown = None
    for step in walk:
        state = (step["pool"], step["attack"], step["talk"])
        if state == shown:
            continue
        shown = state
        print("hp %3d  pool %-46s attack %d to %d  talk %s"
              % (step["hp"], str(list(step["pool"])), step["attack"][0], step["attack"][1], step["talk"]))
    first, second = [crossing_hp(phase["hp_at_or_below"], max_hp) for phase in row["phases"]]
    above = tuple(walk[[step["hp"] for step in walk].index(first + 1)]["pool"])
    at_first = tuple(walk[[step["hp"] for step in walk].index(first)]["pool"])
    at_second = tuple(walk[[step["hp"] for step in walk].index(second)]["pool"])
    print("crossing 1 at %d hp: %s -> %s" % (first, list(above), list(at_first)))
    print("crossing 2 at %d hp: %s -> %s" % (second, list(at_first), list(at_second)))
    print("the two sets the card asks for:")
    print("  set 1 (above 70 percent, hp %d to %d): %s" % (max_hp, first + 1, list(above)))
    print("  set 2 (at or below 70 percent, hp %d to 1): %s" % (first, list(at_second)))
    return 0


if __name__ == "__main__":
    sys.exit(probe())
