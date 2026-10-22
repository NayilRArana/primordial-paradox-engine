"""Tests for the route ledger's per enemy exit rows and the fight verdict (spec 10 rule 6).

GameMaker is not installed on this PC, so these tests cannot run the ledger. They can do two things, and they do both.

1. They read the GML as text and pin the shape spec 10 promises: one door that writes the row, then the verdict, then
   the counter; a fresh fight that starts empty and quiet; no other module touching a counter; the F3 dump carrying
   the rows; the save writing the rows and never the verdict.
2. They carry a Python mirror of the door's rules and drive the four cases the card names through it: one spared and
   one turned reads quiet, one down and one spared reads mixed, the counters equal the row counts, and a save round
   trip preserves the rows. The mirror is pinned to the GML by the structural tests, so it cannot drift in silence.

Nothing here executes or edits the game.
"""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEDGER_GML = os.path.join("game", "scripts", "pp_ledger", "pp_ledger.gml")
DIRECTOR_GML = os.path.join("game", "scripts", "pp_battle_director", "pp_battle_director.gml")
SAVE_GML = os.path.join("game", "scripts", "pp_save", "pp_save.gml")
CONFIG_GML = os.path.join("game", "scripts", "pp_config", "pp_config.gml")
OVERLAY_GML = os.path.join("game", "objects", "obj_pp_debug_overlay", "Draw_64.gml")
SPEC_LEDGER = os.path.join("specs", "10-route-ledger.md")
SPEC_SAVE = os.path.join("specs", "11-save.md")
TEST_SAVE = os.path.join("tests", "test_save.py")

# The enum values the GML uses. They are read out of pp_config by test_the_three_exits_are_named_in_config below, and
# repeated here because Python has to hold a number to compare against.
DOWN, SPARED, TURNED = 0, 1, 2
QUIET, MIXED, VIOLENT = 0, 1, 2


# ---------------------------------------------------------------------------------------------------------------
# Reading the GML as text


def read_text(relative: str) -> str:
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8-sig") as fh:
        return fh.read()


def code_only(text: str) -> str:
    """Drop // and /// comments so a check reads code, not prose."""
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def read_code(relative: str) -> str:
    return code_only(read_text(relative))


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


# ---------------------------------------------------------------------------------------------------------------
# The mirror of the door, from spec 10 rule 6


def new_ledger() -> dict:
    return {
        "counters": {
            "bosses_killed": 0,
            "bosses_spared": 0,
            "regulars_killed": 0,
            "regulars_spared": 0,
        },
        "exits": [],
        "verdict": QUIET,
    }


def begin_fight(ledger: dict) -> dict:
    ledger["exits"] = []
    ledger["verdict"] = QUIET
    return ledger


def exit_of_result(result: str) -> int:
    """PPResult name to PPExit number, or -1 for a result that leaves no row."""
    return {"kill": DOWN, "spare": SPARED, "interrupt": TURNED}.get(result, -1)


def verdict_of(rows: list[dict]) -> int:
    down = sum(1 for row in rows if row["exit"] == DOWN)
    soft = len(rows) - down
    if down == 0:
        return QUIET
    if soft > 0:
        return MIXED
    return VIOLENT


def record_exit(ledger: dict, enemy_id: str, kind: str, result: str, round_no: int) -> dict:
    """The mirror of pp_ledger_record_exit: row, then verdict, then counter, in one call."""
    exit_state = exit_of_result(result)
    if exit_state < 0:
        return ledger
    ledger["exits"].append({"id": enemy_id, "exit": exit_state, "round": round_no})
    ledger["verdict"] = verdict_of(ledger["exits"])
    if exit_state == DOWN:
        ledger["counters"]["bosses_killed" if kind == "boss" else "regulars_killed"] += 1
    elif exit_state == SPARED:
        ledger["counters"]["bosses_spared" if kind == "boss" else "regulars_spared"] += 1
    return ledger


def snapshot_exits(ledger: dict) -> list[dict]:
    """The mirror of pp_save_snapshot_exits: ids and numbers only, no verdict."""
    return [{"id": row["id"], "exit": row["exit"], "round": row["round"]} for row in ledger["exits"]]


def apply_exits(document: dict) -> dict:
    """The mirror of the exit rows coming back out of a save, verdict recomputed from the rows."""
    ledger = new_ledger()
    ledger["exits"] = []
    ledger["verdict"] = QUIET
    if "fight_exits" in document:
        ledger["exits"] = [{"id": row["id"], "exit": row["exit"], "round": row["round"]}
                           for row in document["fight_exits"]]
        ledger["verdict"] = verdict_of(ledger["exits"])
    return ledger


def round_trip(ledger: dict) -> dict:
    """A save document carrying the rows, through JSON text, back into a ledger. The file shape is the real one."""
    import json
    document = {"fight_exits": snapshot_exits(ledger)}
    return apply_exits(json.loads(json.dumps(document)))


# ---------------------------------------------------------------------------------------------------------------
# 1. The shape the GML must keep


def test_the_three_exits_are_named_in_config():
    """The doctrine's three exit states and three verdict words are enum values, not strings scattered in code."""
    config = read_code(CONFIG_GML)
    exits = brace_block(config, "enum PPExit {")
    verdicts = brace_block(config, "enum PPFightVerdict {")
    for name in ("down", "spared", "turned"):
        assert re.search(r"\b%s\s*=" % name, exits), "PPExit does not name %r" % name
    for name in ("quiet", "mixed", "violent"):
        assert re.search(r"\b%s\s*=" % name, verdicts), "PPFightVerdict does not name %r" % name
    assert re.search(r"down\s*=\s*%d" % DOWN, exits)
    assert re.search(r"spared\s*=\s*%d" % SPARED, exits)
    assert re.search(r"turned\s*=\s*%d" % TURNED, exits)
    assert re.search(r"quiet\s*=\s*%d" % QUIET, verdicts)
    assert re.search(r"mixed\s*=\s*%d" % MIXED, verdicts)
    assert re.search(r"violent\s*=\s*%d" % VIOLENT, verdicts)


def test_a_new_ledger_starts_empty_and_quiet():
    body = function_body(read_code(LEDGER_GML), "pp_ledger_new")
    assert "exits: []" in body, "a new ledger must hold no exit rows"
    assert "verdict: PPFightVerdict.quiet" in body, "a new ledger must read quiet"


def test_the_door_writes_the_row_then_the_verdict_then_the_counter():
    """Spec 10 rule 6: the order is the guarantee that a row and a counter cannot disagree."""
    body = function_body(read_code(LEDGER_GML), "pp_ledger_record_exit")
    row = body.index("array_push(_ledger.exits")
    verdict = body.index("_ledger.verdict = pp_ledger_verdict_of(_ledger.exits)")
    first_counter = min(
        body.index("_ledger.counters.bosses_killed += 1"),
        body.index("_ledger.counters.regulars_killed += 1"),
        body.index("_ledger.counters.bosses_spared += 1"),
        body.index("_ledger.counters.regulars_spared += 1"),
    )
    assert row < verdict < first_counter, "the door must write the row, then the verdict, then the counter"
    assert body.count("array_push(_ledger.exits") == 1, "the door writes exactly one row per call"
    assert "return _ledger;" in body


def test_the_exit_states_map_from_the_result_enum():
    body = function_body(read_code(LEDGER_GML), "pp_ledger_exit_of_result")
    assert "case PPResult.kill: return PPExit.down;" in body
    assert "case PPResult.spare: return PPExit.spared;" in body
    assert "case PPResult.interrupt: return PPExit.turned;" in body
    assert "return -1;" in body, "a result that leaves no row must be refused, not guessed at"


def test_the_verdict_is_generous_in_the_documented_order():
    """quiet beats mixed beats violent, and the order of the three returns is what makes that true."""
    body = function_body(read_code(LEDGER_GML), "pp_ledger_verdict_of")
    quiet = body.index("if (_down == 0) return PPFightVerdict.quiet;")
    mixed = body.index("if (_soft > 0) return PPFightVerdict.mixed;")
    violent = body.index("return PPFightVerdict.violent;")
    assert quiet < mixed < violent, "a fight with no down must read quiet before any other rule is tried"
    assert "if (_rows[i].exit == PPExit.down) _down += 1;" in body, "a turned enemy counts as soft, not as down"


def test_no_module_increments_a_counter_outside_the_door():
    """Spec 10 rule 1: one door. A counter moved anywhere else is the drift this card exists to prevent."""
    pattern = re.compile(r"counters\.(bosses|regulars)_(killed|spared)\s*\+=")
    offenders = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if not name.endswith(".gml"):
                continue
            path = os.path.join(dirpath, name)
            text = code_only(open(path, "r", encoding="utf-8-sig").read())
            for match in pattern.finditer(text):
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                if rel != LEDGER_GML.replace("\\", "/"):
                    offenders.append("%s:%s" % (rel, match.group(0)))
                else:
                    door = function_body(text, "pp_ledger_record_exit")
                    if match.start() < text.index(door) or match.start() > text.index(door) + len(door):
                        offenders.append("%s: outside the door" % rel)
    assert offenders == [], "a counter is moved outside the ledger's door: %s" % offenders
    # And the ledger has exactly four such lines, one per counter, all inside the door.
    assert len(pattern.findall(read_code(LEDGER_GML))) == 4, "the door must move each of the four counters once"


def test_the_director_records_through_one_call_and_names_no_counter():
    director = read_code(DIRECTOR_GML)
    record = function_body(director, "pp_battle_record")
    assert record.count("pp_ledger_record_exit(") == 1, "the director records an exit in exactly one call"
    assert "_battle.enemy.id" in record and "_battle.turn" in record, "the row carries the enemy and the round"
    assert "counters" not in director, "the battle director must not touch a counter"
    assert "pp_ledger_record_result" not in read_code(LEDGER_GML), "the old counter only door must be gone"


def test_a_new_fight_starts_with_a_clean_record():
    director = read_code(DIRECTOR_GML)
    battle_new = function_body(director, "pp_battle_new")
    assert "pp_ledger_begin_fight(_ledger)" in battle_new, "the fight must clear the last fight's rows"
    begin = function_body(read_code(LEDGER_GML), "pp_ledger_begin_fight")
    assert "_ledger.exits = [];" in begin
    assert "_ledger.verdict = PPFightVerdict.quiet;" in begin


def test_the_debug_dump_lists_the_last_fights_rows():
    """Spec 10 rule 5: F3 carries the rows, so a tester can see the record without opening the save."""
    ledger = read_code(LEDGER_GML)
    dump = function_body(ledger, "pp_ledger_debug_text")
    assert "array_length(_ledger.exits)" in dump, "the dump does not walk the rows"
    assert "pp_ledger_exit_name(_row.exit)" in dump, "a row is drawn without its exit"
    assert 'string(_row.round)' in dump, "a row is drawn without its round"
    assert "pp_ledger_verdict_name(_ledger.verdict)" in dump, "the dump does not carry the fight verdict"

    lines = function_body(ledger, "pp_ledger_debug_lines")
    assert "2 + array_length(_ledger.exits)" in lines, "the line count must follow the rows"

    overlay = read_text(OVERLAY_GML)
    assert "pp_ledger_debug_text(global.pp_ledger" in overlay
    assert "pp_ledger_debug_lines(global.pp_ledger)" in overlay, "the F3 box must size itself from the rows"
    assert re.search(r"draw_rectangle\(4, 4, \d+, _bottom", overlay), "the box height is not the computed one"


def test_the_save_writes_the_rows_and_never_the_verdict():
    save = read_code(SAVE_GML)
    assert "fight_exits: pp_save_snapshot_exits(_ledger)," in save
    snapshot = function_body(save, "pp_save_snapshot")
    keys = re.findall(r"(\w+):", brace_block(snapshot, "return {"))
    assert "fight_exits" in keys, "the save document does not carry the rows"
    assert "verdict" not in keys, "the verdict is derived on read, so storing it would be a second copy"
    exits = function_body(save, "pp_save_snapshot_exits")
    assert "id: _row.id, exit: _row.exit, round: _row.round" in exits


def test_the_save_key_is_optional_so_an_older_file_still_loads():
    save = read_code(SAVE_GML)
    assert '"fight_exits"' in function_body(save, "pp_save_key_list")
    optional = function_body(save, "pp_save_optional_keys")
    assert 'return ["fight_exits"];' in optional
    validate = function_body(save, "pp_save_validate")
    assert "if (pp_save_strings_have(pp_save_optional_keys(), _keys[j])) continue;" in validate, \
        "a missing optional key must not be reported as a missing field"
    assert "if (variable_struct_exists(_d, \"fight_exits\"))" in validate, \
        "the rows must be checked when they are there and not demanded when they are not"
    assert "pp_save_exit_rows_problem(_d.fight_exits)" in validate


def test_the_save_apply_rebuilds_the_verdict_from_the_rows():
    apply = function_body(read_code(SAVE_GML), "pp_save_apply")
    assert "_ledger.exits = [];" in apply, "a save with no rows must start empty rather than keep the old ones"
    assert "pp_ledger_verdict_of(_ledger.exits)" in apply, "the verdict must be recomputed, never read from the file"


def test_the_specs_name_the_rows_and_the_verdict():
    spec = read_text(SPEC_LEDGER)
    for word in ("`down`", "`spared`", "`turned`", "`quiet`", "`mixed`", "`violent`"):
        assert word in spec, "spec 10 does not name %s" % word
    assert "Exit rows:" in spec, "spec 10 does not record the rows as a recorded fact"
    assert "6. An enemy exit is recorded in one call" in spec, "spec 10 does not state the door rule"
    save_spec = read_text(SPEC_SAVE)
    assert "Optional keys: `fight_exits`" in save_spec, "spec 11 does not list the optional key"


def test_the_mirror_messages_match_the_game():
    """The Python mirror of the row checks in tests/test_save.py repeats these sentences, so pin both sides."""
    for message in ("a saved fight exit is not a record of an id, an exit and a round",
                    "a saved fight exit is not one of the three exits"):
        assert message in function_body(read_code(SAVE_GML), "pp_save_exit_row_problem"), message
        assert message in read_text(TEST_SAVE), "the save test's mirror no longer says %r" % message


# ---------------------------------------------------------------------------------------------------------------
# 2. The four cases the card names, through the mirror


def test_a_fight_of_one_spared_and_one_turned_reads_quiet():
    ledger = new_ledger()
    begin_fight(ledger)
    record_exit(ledger, "navy_sailor", "regular", "spare", 2)
    record_exit(ledger, "percy", "boss", "interrupt", 3)
    assert ledger["verdict"] == QUIET
    assert [row["exit"] for row in ledger["exits"]] == [SPARED, TURNED]
    assert [row["round"] for row in ledger["exits"]] == [2, 3]


def test_a_fight_of_one_down_and_one_spared_reads_mixed():
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "kill", 1)
    record_exit(ledger, "percy", "boss", "spare", 4)
    assert ledger["verdict"] == MIXED
    assert [row["exit"] for row in ledger["exits"]] == [DOWN, SPARED]


def test_a_fight_of_only_downs_reads_violent():
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "kill", 1)
    record_exit(ledger, "percy", "boss", "kill", 2)
    assert ledger["verdict"] == VIOLENT


def test_a_result_that_leaves_no_row_moves_nothing():
    """A defeat is the party leaving the field, and the director records nothing for it, so the door must too."""
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "none", 1)
    assert ledger["exits"] == []
    assert ledger["verdict"] == QUIET
    assert ledger["counters"] == {"bosses_killed": 0, "bosses_spared": 0,
                                  "regulars_killed": 0, "regulars_spared": 0}


def test_the_counters_equal_the_row_counts():
    """Every row is accounted for exactly once: down moves a kill counter, spared a spare counter, turned neither."""
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "kill", 1)
    record_exit(ledger, "navy_sailor", "regular", "spare", 2)
    record_exit(ledger, "navy_sailor", "regular", "spare", 3)
    record_exit(ledger, "percy", "boss", "interrupt", 4)
    rows = ledger["exits"]
    counted = {"bosses_killed": sum(1 for r in rows if r["exit"] == DOWN and r["id"] == "percy"),
               "bosses_spared": sum(1 for r in rows if r["exit"] == SPARED and r["id"] == "percy"),
               "regulars_killed": sum(1 for r in rows if r["exit"] == DOWN and r["id"] != "percy"),
               "regulars_spared": sum(1 for r in rows if r["exit"] == SPARED and r["id"] != "percy")}
    assert ledger["counters"] == counted, ledger["counters"]
    turned = sum(1 for row in rows if row["exit"] == TURNED)
    assert turned == 1
    assert sum(ledger["counters"].values()) + turned == len(rows), \
        "the counters plus the turned rows must add up to the rows, with nothing counted twice"


def test_a_save_round_trip_preserves_the_rows():
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "kill", 1)
    record_exit(ledger, "percy", "boss", "spare", 5)
    loaded = round_trip(ledger)
    assert loaded["exits"] == ledger["exits"]
    assert loaded["verdict"] == ledger["verdict"] == MIXED


def test_a_fight_reads_the_same_after_a_load():
    """The verdict is derived, so a loaded quiet fight must not come back as the default by accident."""
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "spare", 2)
    record_exit(ledger, "percy", "boss", "interrupt", 3)
    loaded = round_trip(ledger)
    assert loaded["verdict"] == QUIET
    assert loaded["exits"] == ledger["exits"]


def test_an_old_save_with_no_exit_key_loads_as_an_empty_quiet_ledger():
    loaded = apply_exits({"format": 1})
    assert loaded["exits"] == []
    assert loaded["verdict"] == QUIET


def test_a_new_fight_clears_the_last_one_and_keeps_the_counters():
    ledger = new_ledger()
    record_exit(ledger, "navy_sailor", "regular", "kill", 1)
    counters_before = dict(ledger["counters"])
    begin_fight(ledger)
    assert ledger["exits"] == []
    assert ledger["verdict"] == QUIET
    assert ledger["counters"] == counters_before, "the run's history is not the last fight's record"
