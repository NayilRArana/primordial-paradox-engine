"""The two ways out of the slice, proved where they can be proved (card R33).

GameMaker is not installed on this PC and no game window may be opened, so nothing here plays the
game. What can be proved without it is the contract between four files: the save writer
(pp_save.gml), the entry autosave (same file, but its timing is owned by pp_app's fade and
pp_overworld's step), and the game over screen (pp_battle_director.gml). Every check is one of two
kinds:

1. A text check against the GML. The family's readers are imported from tests\\test_save.py and not
   copied, the way test_slice_route.py imports test_first_fight.py, so a change of wording in the
   game breaks one reader and both files see it.
2. A Python mirror of one GML function, driven over the real data files, pinned back to the GML by
   MIRROR_QUOTES so a change on either side fails here instead of at the first run.

The three parts of the card: the save round trip and the refusal of an older format, the autosave
timing, and the defeat restore with CONTINUE from the title.

Two fields the card names cannot round trip as written, and this file says so instead of pretending.

Facing is not a key of spec 11, so pp_save_snapshot has nowhere to put it and every load faces
"down". The round trip reports the loss by name (FACING_LOSS) and a test asserts it, so the day a
facing key is added this file goes red rather than passing quietly.

Mercy per enemy has no per-enemy number in the document either: spec 10's record is the last
fight's exit rows plus the four counters, so a spare comes back as the row (enemy id, exit, round)
and the counter it moved, and the verdict is recomputed from the rows on load.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import check_data  # noqa: E402  the family's validator mirror needs the checker beside it
import test_save as save_family  # noqa: E402  the family's readers, called and not copied

SAVE_GML = save_family.SAVE_GML
CONFIG_GML = save_family.CONFIG_GML
OVERWORLD_GML = os.path.join("game", "scripts", "pp_overworld", "pp_overworld.gml")
APP_GML = os.path.join("game", "scripts", "pp_app", "pp_app.gml")
TITLE_GML = os.path.join("game", "scripts", "pp_title", "pp_title.gml")
# The environment variable points the game over checks at a copy, so a mutation can be shown to fail
# this test and not only the helper, exactly as PP_SAVE_GML does in tests\\test_save.py.
BATTLE_GML = os.environ.get("PP_BATTLE_GML") or os.path.join(
    "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
SPEC_SAVE = save_family.SPEC_SAVE
SPEC_BATTLE = os.path.join("specs", "07-battle-director.md")

COUNTER_KEYS = ("bosses_killed", "bosses_spared", "regulars_killed", "regulars_spared")
EXIT_DOWN, EXIT_SPARED, EXIT_TURNED = 0, 1, 2
VERDICT_QUIET, VERDICT_MIXED, VERDICT_VIOLENT = 0, 1, 2
MODE_OVERWORLD = 2

# The mirror's stand in for date_datetime_string(). The writer stamps the clock; nothing reads the
# stamp back, so the value is fixed here rather than borrowed from the machine and made flaky.
SAVED_AT = "2026-10-22 20:00:00"

FACING_LOSS = ("facing: the save has no facing key, so a load faces \"down\" and the facing the "
               "player left with is lost")


# ---------------------------------------------------------------------------------------------------------------
# Numbers and names out of the GML, so a changed macro fails here instead of being hardcoded twice


def config_number(name: str) -> int:
    match = re.search(r"#macro %s (\d+)" % name, save_family.read_code(CONFIG_GML))
    assert match is not None, "pp_config does not define %s" % name
    return int(match.group(1))


def config_text(name: str) -> str:
    match = re.search(r'#macro %s "([^"]*)"' % name, save_family.read_code(CONFIG_GML))
    assert match is not None, "pp_config does not define %s" % name
    return match.group(1)


def steps_per_second() -> int:
    return config_number("PP_STEPS_PER_SECOND")


def fade_steps() -> int:
    return config_number("PP_FADE_STEPS")


def save_format() -> int:
    return config_number("PP_SAVE_FORMAT")


def save_version() -> str:
    return config_text("PP_SAVE_GAME_VERSION")


# ---------------------------------------------------------------------------------------------------------------
# The data the writer and the applier read


def data_tables() -> dict:
    """The four tables pp_save_apply and pp_overworld_new resolve ids against, out of data\\."""
    return {
        "maps": {row["id"]: row for row in save_family._load_json("maps/all.json")["maps"]},
        "items": {row["id"]: row for row in save_family._load_json("items.json")["items"]},
        "powers": {row["id"]: row for row in save_family._load_json("powers.json")["powers"]},
        "party": save_family._load_json("characters/party.json")["characters"][0],
    }


def live_state(map_id="ship_small", spawn="start", hero=(18, 7), facing="left", music="battle_percy",
               hp=14, powers=("tide_step",), items=("salve", "salve"), flags=None, counters=None,
               exits=None, ticks=3720) -> dict:
    """A running game as the modules hold it, not as the file holds it.

    The shapes are the game's, not the document's: one item record per copy (the battle's shape),
    full power rows (resolved from data), a flag table that may hold false values, and exit rows.
    """
    tables = data_tables()
    return {
        "world": {"map_id": map_id, "spawn_name": spawn,
                  "hero": {"tx": hero[0], "ty": hero[1], "facing": facing}, "music": music},
        "ledger": {
            "counters": dict(counters or {"bosses_killed": 0, "bosses_spared": 1,
                                          "regulars_killed": 0, "regulars_spared": 2}),
            "flags": dict(flags if flags is not None else {
                "ship_door_open": True, "percy_spared": True,
                "scene_ship_boarding": True, "met_prometheus": False,
            }),
            "powers": [dict(tables["powers"][pid]) for pid in powers],
            "items": [{"id": item_id} for item_id in items],
            "exits": copy.deepcopy(exits if exits is not None else [
                {"id": "percy", "exit": EXIT_SPARED, "round": 3},
                {"id": "navy_sailor", "exit": EXIT_SPARED, "round": 2},
            ]),
            "stage": 0,
            "verdict": VERDICT_QUIET,
            "hp": hp,
        },
        "party": {"max_hp": tables["party"]["max_hp"]},
        "ticks": ticks,
    }


# ---------------------------------------------------------------------------------------------------------------
# The mirror of the writer and the applier


def snapshot(live: dict) -> dict:
    """The mirror of pp_save_snapshot. Same keys, same order, same narrowing rules."""
    ledger = live["ledger"]
    world = live["world"]
    party = live["party"]
    max_hp = party["max_hp"]
    hp = ledger.get("hp", max_hp)
    hp = max(0, min(hp, max_hp))
    return {
        "format": save_format(),
        "game_version": save_version(),
        "saved_at": SAVED_AT,
        "play_seconds": live["ticks"] // steps_per_second(),
        "map": world["map_id"],
        "spawn": world["spawn_name"],
        "x": world["hero"]["tx"],
        "y": world["hero"]["ty"],
        "hp": hp,
        "max_hp": max_hp,
        "powers": [row["id"] for row in ledger["powers"] if "id" in row],
        "items": snapshot_items(live),
        "flags": {name: True for name, value in ledger["flags"].items() if value},
        "counters": {name: ledger["counters"][name] for name in COUNTER_KEYS},
        "fight_exits": [{"id": row["id"], "exit": row["exit"], "round": row["round"]}
                        for row in ledger["exits"]],
        "seen_scenes": sorted(name[len("scene_"):] for name, value in ledger["flags"].items()
                              if value and name.startswith("scene_")),
        "music": world["music"],
    }


def snapshot_items(live: dict) -> list[dict]:
    """The mirror of pp_save_snapshot_items: one record per copy collapses to one bag per id.

    A run whose ledger has no items yet records the party's starting items, which is the inventory
    the player actually holds before the first fight (the GML says so in a comment beside the
    fallback, and test_a_fresh_run_records_the_partys_starting_items pins it).
    """
    source = live["ledger"]["items"]
    if not source:
        source = data_tables()["party"].get("starting_items", [])
    bags: list[dict] = []
    for row in source:
        found = next((bag for bag in bags if bag["id"] == row["id"]), None)
        if found is None:
            bags.append({"id": row["id"], "count": int(row.get("count", 1))})
        else:
            found["count"] += int(row.get("count", 1))
    return bags


def verdict_of(rows: list[dict]) -> int:
    """The mirror of pp_ledger_verdict_of, which pp_save_apply calls to recompute the verdict."""
    down = sum(1 for row in rows if row["exit"] == EXIT_DOWN)
    soft = len(rows) - down
    if down == 0:
        return VERDICT_QUIET
    return VERDICT_MIXED if soft > 0 else VERDICT_VIOLENT


def collision(map_row: dict, tx: int, ty: int, flags: dict) -> int:
    """The mirror of pp_map_collision: 1 is blocked, 2 is blocked until the map's story flag is set."""
    if tx < 0 or ty < 0 or tx >= map_row["width"] or ty >= map_row["height"]:
        return 1
    char = map_row["collision"][ty][tx]
    if char == "2":
        story_flag = map_row.get("story_flag", "")
        return 0 if story_flag and flags.get(story_flag) else 1
    return 1 if char == "1" else 0


class Refused(Exception):
    """A document this build will not load. The message is the sentence the game prints."""


def refusal(document: dict) -> str:
    """The first sentence the family's validator mirror would print, or "" for a good document."""
    problems = save_family.save_document_errors(document)
    return problems[0] if problems else ""


def apply_document(document: dict, tables: dict = None) -> dict:
    """The mirror of pp_save_apply, and the only door this file uses to put a save back.

    Nothing is applied before the whole document validates (spec 11 rule 3), the flags are restored
    before the tile is tested (so a tile that was gated when the save was taken is walkable again),
    the hero faces "down" because the document carries no facing, and the world is rebuilt from the
    named map and spawn, with the saved tile only when it is walkable.
    """
    tables = tables or data_tables()
    problem = refusal(document)
    if problem:
        raise Refused(problem)

    flags = {name: (value != 0) for name, value in document["flags"].items()}
    exits = [{"id": row["id"], "exit": row["exit"], "round": row["round"]}
             for row in document.get("fight_exits", [])]
    items = []
    for bag in document["items"]:
        row = tables["items"][bag["id"]]
        for _ in range(int(bag["count"])):
            items.append({"id": row["id"], "name": row["name"], "heal": row.get("heal", 0)})
    ledger = {
        "counters": {name: document["counters"][name] for name in COUNTER_KEYS},
        "flags": flags,
        "hp": document["hp"],
        "powers": [dict(tables["powers"][pid]) for pid in document["powers"]],
        "items": items,
        "exits": exits,
        "verdict": verdict_of(exits),
        "stage": 0,
    }

    map_row = tables["maps"][document["map"]]
    spawn = map_row["spawns"][document["spawn"]]
    tx, ty = spawn["x"], spawn["y"]
    if collision(map_row, document["x"], document["y"], flags) == 0:
        tx, ty = document["x"], document["y"]
    world = {"map_id": map_row["id"], "spawn_name": document["spawn"],
             "hero": {"tx": tx, "ty": ty, "facing": "down"}, "music": document["music"]}
    return {"world": world, "ledger": ledger, "party": {"max_hp": tables["party"]["max_hp"]},
            "ticks": document["play_seconds"] * steps_per_second()}


def round_trip_problems(live: dict) -> list[str]:
    """Every field the card names that does not come back, each named with what went in and what came out."""
    document = snapshot(live)
    problem = refusal(document)
    if problem:
        return ["the writer's own document would be refused by its own validator: " + problem]
    back = apply_document(document)

    saved_items = [row["id"] for row in live["ledger"]["items"]]
    back_items = [row["id"] for row in back["ledger"]["items"]]
    saved_true = sorted(name for name, value in live["ledger"]["flags"].items() if value)
    pairs = [
        ("map", live["world"]["map_id"], back["world"]["map_id"]),
        ("the spawn", live["world"]["spawn_name"], back["world"]["spawn_name"]),
        ("the tile x", document["x"], back["world"]["hero"]["tx"]),
        ("the tile y", document["y"], back["world"]["hero"]["ty"]),
        ("hp", live["ledger"]["hp"], back["ledger"]["hp"]),
        ("max_hp", live["party"]["max_hp"], back["party"]["max_hp"]),
        ("the flag block", saved_true, sorted(back["ledger"]["flags"])),
        ("the item list", saved_items, back_items),
        ("the power list", [row["id"] for row in live["ledger"]["powers"]],
         [row["id"] for row in back["ledger"]["powers"]]),
        ("the counters", live["ledger"]["counters"], back["ledger"]["counters"]),
        ("mercy per enemy", live["ledger"]["exits"], back["ledger"]["exits"]),
        ("the fight verdict", verdict_of(live["ledger"]["exits"]), back["ledger"]["verdict"]),
        ("music", live["world"]["music"], back["world"]["music"]),
        ("play_seconds", live["ticks"], back["ticks"]),
        ("format", save_format(), document["format"]),
        ("game_version", save_version(), document["game_version"]),
    ]
    problems = ["%s: saved %r, came back %r" % (field, saved, got)
                for field, saved, got in pairs if saved != got]
    if live["world"]["hero"]["facing"] != back["world"]["hero"]["facing"]:
        problems.append(FACING_LOSS)
    return problems


# ---------------------------------------------------------------------------------------------------------------
# The key set, and the mutation that proves the checks bite


def write_keys(text: str) -> list[str]:
    return save_family.write_keys(text)


def drop_writer_key(text: str, key: str) -> str:
    """The writer as a real edit that deletes one key's line would leave it, on a copy of the text."""
    body = save_family.function_body(text, "pp_save_snapshot")
    literal = save_family.brace_block(body[body.index("return {"):], "return {")
    parts = save_family.split_top_level(literal[1:-1])
    kept = [part for part in parts if part.split(":", 1)[0].strip() != key]
    assert len(kept) == len(parts) - 1, "the writer has no entry for %r to remove" % key
    return text.replace(literal, "{" + ",".join(kept) + "}", 1)


# Each document key, and the exact line of pp_save_snapshot that puts the player's value in it. The
# mirror quotes these, so an edit on either side breaks a test rather than letting the two drift.
MIRROR_QUOTES = {
    "format": "format: PP_SAVE_FORMAT,",
    "game_version": "game_version: PP_SAVE_GAME_VERSION,",
    "saved_at": "saved_at: date_datetime_string(date_current_datetime()),",
    "play_seconds": "play_seconds: floor(global.pp.save.ticks / PP_STEPS_PER_SECOND),",
    "map": "map: _w.map.id,",
    "spawn": "spawn: _w.spawn_name,",
    "x": "x: _w.hero.tx,",
    "y": "y: _w.hero.ty,",
    "hp": "hp: _hp,",
    "max_hp": "max_hp: _max_hp,",
    "powers": "powers: pp_save_snapshot_powers(_ledger),",
    "items": "items: pp_save_snapshot_items(_ledger, _party),",
    "flags": "flags: pp_save_snapshot_flags(_ledger),",
    "counters": "counters: {",
    "fight_exits": "fight_exits: pp_save_snapshot_exits(_ledger),",
    "seen_scenes": "seen_scenes: pp_save_snapshot_scenes(_ledger),",
    "music": "music: _w.music",
}


# ---------------------------------------------------------------------------------------------------------------
# 1. The save round trip


def test_a_save_round_trips_every_field_the_card_names():
    """Write through the writer's own shape, read back, and hold every changed field against the save."""
    problems = round_trip_problems(live_state())
    # The one loss is named, not dropped: the document has no facing key, so the load faces down.
    assert problems == [FACING_LOSS], problems


def test_a_second_state_round_trips_too_so_the_first_is_not_a_lucky_fixture():
    """A second map with the opposite shapes: no powers, one item, an empty flag block, no music, hp 0."""
    live = live_state(map_id="ship_cabin", spawn="from_deck", hero=(7, 7), facing="left", music="",
                      hp=0, powers=(), items=("salve",), flags={}, counters={
                          "bosses_killed": 3, "bosses_spared": 0,
                          "regulars_killed": 9, "regulars_spared": 0,
                      }, exits=[{"id": "deck_hound", "exit": EXIT_DOWN, "round": 1}], ticks=60)
    assert round_trip_problems(live) == [FACING_LOSS], round_trip_problems(live)


def test_a_fresh_run_records_the_partys_starting_items():
    """A ledger with no items yet writes the party's starting bags, which is what pp_save_snapshot_items does."""
    live = live_state(items=())
    assert live["ledger"]["items"] == []
    assert snapshot(live)["items"] == [{"id": "salve", "count": 2}], snapshot(live)["items"]


def test_the_round_trip_witnesses_every_key_the_writer_writes():
    """The set the mirror exercises is the set the writer writes, and the set spec 11 lists.

    A key added to one side only has to fail here rather than at the first load: this is the check
    the card's mutation is aimed at.
    """
    text = save_family.read_code(SAVE_GML)
    written = write_keys(text)
    assert set(written) == set(MIRROR_QUOTES), "the writer's keys and the mirror's quotes disagree"
    assert set(written) == set(save_family.spec_save_keys()), "the writer and spec 11 disagree"
    assert len(written) == len(set(written)), written


def test_the_mirror_quotes_the_writer_so_it_cannot_drift():
    """Every line the mirror stands on is in pp_save_snapshot, so a change of shape is caught here."""
    body = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_snapshot")
    missing = [key for key, quote in MIRROR_QUOTES.items() if quote not in body]
    assert missing == [], "the writer no longer holds the line the mirror stands on: %s" % missing


def test_a_dropped_field_turns_the_writer_agreement_red_and_names_the_field(tmp_path):
    """One key at a time, dropped from a copy of the writer: the check must name it, every time.

    The mutation is done on a copy, and one of the seventeen is also written to disk and read back,
    so the in memory edit and a real one are shown to be the same edit.
    """
    original = save_family.read_code(SAVE_GML)
    assert save_family.parity_failures(original) == []

    for key in save_family.spec_save_keys():
        mutated = drop_writer_key(original, key)
        assert MIRROR_QUOTES[key] not in mutated, "dropping %r left its line in place" % key
        problems = save_family.parity_failures(mutated)
        assert any(key in problem for problem in problems), \
            "dropping %r did not name it: %s" % (key, problems)

    scratch = tmp_path / "pp_save.gml"
    scratch.write_text(drop_writer_key(original, "x"), encoding="utf-8")
    problems = save_family.parity_failures(scratch.read_text(encoding="utf-8"))
    assert any("'x'" in problem for problem in problems), problems


def test_an_older_format_is_refused_cleanly_and_nothing_is_half_loaded():
    """A save from a format this build does not read is refused first, by name, and applies nothing.

    Both directions are checked: the sentence the validator mirror prints, and the live state, which
    must be untouched by a refused load (spec 11 rule 1 and rule 3).
    """
    live = live_state()
    document = snapshot(live)
    for old_format in (0, 2, 7):
        assert refusal(dict(document, format=old_format)).startswith("the save is format"), \
            refusal(dict(document, format=old_format))

    refused = dict(document, format=2, map="no_such_map", hp=-4)
    before = copy.deepcopy(live)
    try:
        apply_document(refused)
    except Refused as exc:
        assert "format 2" in str(exc), str(exc)
    else:
        raise AssertionError("a save of an unknown format was applied")
    assert live == before, "a refused load changed the live game"

    # The order inside the game is the same order: the format is read before the key set is walked, and
    # the validated document is stored only after every check has passed.
    parse = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_parse")
    assert parse.index("pp_save_validate(_parsed)") < parse.index("_s.data = _parsed"), \
        "the document is stored before it has been validated"


def test_facing_cannot_round_trip_and_the_loss_is_named():
    """The card asks for facing, spec 11 has no key for it, and this file reports the gap by name."""
    assert "facing" not in save_family.spec_save_keys()
    assert "facing" not in save_family.read_code(SAVE_GML).lower()
    hero = save_family.function_body(save_family.read_code(OVERWORLD_GML), "pp_overworld_hero")
    assert 'facing: "down"' in hero, "the hero builder does not face down, so the loss is not what it is"
    problems = round_trip_problems(live_state(facing="left"))
    assert FACING_LOSS in problems, problems
    assert [problem for problem in problems if problem != FACING_LOSS] == [], problems


def test_mercy_per_enemy_is_the_exit_rows_and_the_counters_never_a_trust_number():
    """Mercy survives as spec 10 records it: the enemy's exit row, and the counter its kind moves.

    A per enemy trust number would be a new key, and spec 11's key list is fixed, so the honest test
    is that the row and the counter are the whole record and that nothing else is in the document.
    """
    text = save_family.read_code(SAVE_GML)
    assert "trust" not in text.lower(), "the save module grew a trust number"
    document = snapshot(live_state())
    assert [row["id"] for row in document["fight_exits"]] == ["percy", "navy_sailor"]
    assert document["counters"]["bosses_spared"] == 1
    assert document["counters"]["regulars_spared"] == 2

    # The bucket an enemy moves is the enemy's own data, and the ledger's one door applies it.
    record = save_family.function_body(save_family.read_code("game/scripts/pp_ledger/pp_ledger.gml"),
                                       "pp_ledger_record_exit")
    assert record.count('if (_kind == "boss")') == 2, "a kill and a spare no longer bucket by kind"
    assert "route_kind" in save_family.function_body(read_battle(), "pp_battle_record"), \
        "the fight no longer asks the enemy data which bucket it moves"


# ---------------------------------------------------------------------------------------------------------------
# 2. The autosave timing


def read_battle() -> str:
    return save_family.read_code(BATTLE_GML)


def fade_settled(app: dict) -> bool:
    """The mirror of pp_save_fade_settled: the fade is over when its direction is 0 and its alpha has reached 0."""
    if app.get("fade_dir", 0) != 0:
        return False
    return app.get("fade_alpha", 0) <= 0


def entry_settled(world: dict, app: dict) -> bool:
    """The mirror of pp_save_entry_settled, in its order, with the fade last."""
    if world.get("mode") != MODE_OVERWORLD:
        return False
    if world.get("scene"):
        return False
    if not world.get("dialogue_closed", True):
        return False
    if world.get("battle_request", "") != "":
        return False
    return fade_settled(app)


def autosave_step(state: dict, world: dict, app: dict, writes: list) -> bool:
    """The mirror of pp_save_autosave_step, which writes at most once per armed entry."""
    armed = state.get("autosave_map", "")
    if armed == "":
        return False
    if world is None or world.get("map_id") != armed:
        state["autosave_map"] = ""
        return False
    if state.get("busy"):
        return False
    if not entry_settled(world, app):
        return False
    state["autosave_map"] = ""
    writes.append({"map": armed, "silent": True})
    return True


def app_fade_step(app: dict) -> None:
    """The mirror of pp_app_step's fade arithmetic, which is the clock the autosave waits on."""
    if app.get("fade_dir", 0) == 0:
        return
    app["fade_alpha"] = app.get("fade_alpha", 0) + app["fade_dir"] * (1 / fade_steps())
    if app["fade_dir"] < 0 and app["fade_alpha"] <= 0:
        app["fade_alpha"] = 0
        app["fade_dir"] = 0


def test_the_autosave_fires_after_the_fade_and_never_before_it():
    """The GML order first, then a run of the real fade arithmetic with the mirror of the same three tests.

    The arm is made on map entry by pp_overworld_new, the step waits for pp_save_entry_settled, and
    that waits for the app's fade. A write before the fade would be a save taken on a screen the
    player has not been shown yet.
    """
    step = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_autosave_step")
    assert step.index("pp_save_entry_settled(_world)") < step.index("pp_save_write("), \
        "the autosave writes before it has asked whether the screen has settled"
    assert 'pp_save_write("entry " + string(_map), true)' in step, "the entry save is no longer silent"

    settled = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_entry_settled")
    checks = [settled.index(token) for token in (
        "pp_app_mode() != PPMode.overworld", "pp_scene_running(_world.scene)",
        "pp_dialogue_closed(_world.dialogue)", '_world.battle_request != ""',
        "pp_save_fade_settled()")]
    assert checks == sorted(checks), "the fade is asked before the screen checks, or a check was dropped"

    assert "pp_save_autosave_arm(_map.id)" in save_family.function_body(
        save_family.read_code(OVERWORLD_GML), "pp_overworld_new"), "a map entry arms no save"

    # The run. The fade in starts at alpha 1 with a direction of -1, which is pp_app_fade_in's own line.
    app_gml = save_family.read_code(APP_GML)
    assert "_app.fade_alpha = 1;" in app_gml and "_app.fade_dir = -1;" in app_gml
    assert "_app.fade_dir * (1 / PP_FADE_STEPS)" in app_gml, "the app no longer fades by PP_FADE_STEPS"
    app = {"fade_alpha": 1, "fade_dir": -1}
    world = {"mode": MODE_OVERWORLD, "map_id": "ship_small", "scene": None,
             "dialogue_closed": True, "battle_request": ""}
    state = {"autosave_map": "ship_small", "busy": False}
    writes: list = []
    guarded = 0
    while app["fade_dir"] != 0:
        assert autosave_step(state, world, app, writes) is False, "the autosave wrote during the fade"
        assert writes == [], "the autosave wrote during the fade"
        guarded += 1
        app_fade_step(app)
    assert guarded >= fade_steps(), "the fade settled in %d steps, fewer than the %d it is made of" \
        % (guarded, fade_steps())

    assert autosave_step(state, world, app, writes) is True, "the autosave did not fire on the first settled step"
    assert writes == [{"map": "ship_small", "silent": True}], writes


def test_the_autosave_writes_once_per_entry_and_says_nothing_on_screen():
    """One write per entry, and the panel stays off the screen for it, while a failure still speaks."""
    state = {"autosave_map": "ship_small", "busy": False}
    world = {"mode": MODE_OVERWORLD, "map_id": "ship_small", "scene": None,
             "dialogue_closed": True, "battle_request": ""}
    app = {"fade_alpha": 0, "fade_dir": 0}
    writes: list = []
    assert autosave_step(state, world, app, writes) is True
    assert autosave_step(state, world, app, writes) is False, "a second step wrote the entry again"
    assert len(writes) == 1, writes

    text = save_family.read_code(SAVE_GML)
    assert "_s.silent = (_silent == true);" in save_family.function_body(text, "pp_save_write")
    panel = save_family.function_body(text, "pp_save_panel_text")
    assert "if (_s.silent && _s.state != PPSaveState.failed) return \"\";" in panel, \
        "a silent save draws a panel, or a silent failure draws nothing"
    # A scene that opens on the new map holds the save instead of losing it, and so does a transfer
    # that is already in flight: the arm is dropped only by the write, by a load, or by a wrong world.
    waiting = {"autosave_map": "ship_small", "busy": False}
    assert autosave_step(waiting, dict(world, scene={"id": "ship_boarding"}), app, []) is False
    assert waiting["autosave_map"] == "ship_small", "a scene on the new map dropped the entry save"
    assert autosave_step(dict(waiting, busy=True), world, app, []) is False
    assert waiting["autosave_map"] == "ship_small", "a transfer in flight dropped the entry save"
    # A world the player is not standing on is not saved over their slot.
    elsewhere = {"autosave_map": "ship_small", "busy": False}
    assert autosave_step(elsewhere, dict(world, map_id="ship_cabin"), app, []) is False
    assert elsewhere["autosave_map"] == "", "an arm for another map survived"


def screen_free(world: dict) -> bool:
    """The mirror of pp_save_screen_free: a scene or a dialogue runs inside the overworld, so the mode is not enough."""
    if world is None:
        return True
    if world.get("scene"):
        return False
    if not world.get("dialogue_closed", True):
        return False
    return world.get("battle_request", "") == ""


def save_write(state: dict, mode: int, world: dict) -> tuple[bool, str]:
    """The mirror of pp_save_write's refusals, in the game's order, ending in the one write it allows."""
    if state.get("busy"):
        return False, ""
    if mode != MODE_OVERWORLD:
        return False, "PP: save refused, the game is not on a map"
    if not screen_free(world):
        return False, "PP: save refused, a scene or a dialogue is running"
    return True, ""


def test_a_save_request_during_a_scene_is_refused_by_name():
    """The mode check is not enough: a scene runs inside the overworld, so the write asks twice.

    Both refusals print a sentence (spec 11 rule 4, and the overworld's save trigger only prints its
    log line when the write returned true), and both come before any snapshot is taken.
    """
    write = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_write")
    assert "pp_app_mode() != PPMode.overworld" in write, "the battle refusal left the write path"
    assert '"PP: save refused, the game is not on a map"' in write
    assert "!pp_save_screen_free()" in write, "the scene refusal left the write path"
    assert '"PP: save refused, a scene or a dialogue is running"' in write
    assert write.index("pp_save_screen_free()") < write.index("pp_save_snapshot()"), \
        "the snapshot is taken before the screen is asked"

    screen_free = save_family.function_body(save_family.read_code(SAVE_GML), "pp_save_screen_free")
    for refusal in ("pp_scene_running(_world.scene)", "pp_dialogue_closed(_world.dialogue)",
                    '_world.battle_request != ""'):
        assert refusal in screen_free, "a running scene, an open box or a fight no longer refuses a save"

    written = save_family.read_code(OVERWORLD_GML)
    assert "if (pp_save_write(_label, false))" in written, \
        "the save point prints its log line whether or not the save happened"

    # The run of the mirror, in the game's order: a settled overworld writes, and every other screen
    # refuses with the sentence it prints.
    settled = {"mode": MODE_OVERWORLD, "map_id": "ship_small", "scene": None,
               "dialogue_closed": True, "battle_request": ""}
    assert save_write({}, MODE_OVERWORLD, settled) == (True, "")
    for mode, screen, why in (
        (4, settled, "PP: save refused, the game is not on a map"),
        (MODE_OVERWORLD, dict(settled, scene={"id": "ship_boarding"}),
         "PP: save refused, a scene or a dialogue is running"),
        (MODE_OVERWORLD, dict(settled, dialogue_closed=False),
         "PP: save refused, a scene or a dialogue is running"),
        (MODE_OVERWORLD, dict(settled, battle_request="percy"),
         "PP: save refused, a scene or a dialogue is running"),
    ):
        assert save_write({}, mode, screen) == (False, why), screen


def test_a_moved_write_turns_the_autosave_order_check_red(tmp_path):
    """Swap the settled test and the write on a copy of the module: the order check has to notice."""
    original = save_family.read_code(SAVE_GML)
    step = save_family.function_body(original, "pp_save_autosave_step")
    settled_line = "    if (!pp_save_entry_settled(_world)) return false;\n"
    write_line = '    if (!pp_save_write("entry " + string(_map), true)) return false;\n'
    assert settled_line in step and write_line in step
    mutated = original.replace(settled_line + "    _s.autosave_map = \"\";\n" + write_line,
                               write_line + "    _s.autosave_map = \"\";\n" + settled_line)
    assert mutated != original, "the swap did not apply"

    scratch = tmp_path / "pp_save.gml"
    scratch.write_text(mutated, encoding="utf-8")
    body = save_family.function_body(scratch.read_text(encoding="utf-8"), "pp_save_autosave_step")
    assert body.index("pp_save_entry_settled(_world)") > body.index("pp_save_write("), \
        "the swapped module still reads as settled first"


# ---------------------------------------------------------------------------------------------------------------
# 3. The game over: a defeat restores the last save


def test_continue_restores_the_same_document_the_panel_wrote():
    """Save, lose, CONTINUE: the fields of (1) come back from the file, not from the fight.

    The fight moves the hero, empties the health bar and adds its own exit row. None of that may
    survive a CONTINUE, which reads the slot and applies it (spec 07 acceptance 4, spec 11 rule 5).
    """
    live = live_state()
    document = json.loads(json.dumps(snapshot(live)))

    after_the_fight = copy.deepcopy(live)
    after_the_fight["world"]["hero"]["tx"] = 9
    after_the_fight["world"]["hero"]["ty"] = 11
    after_the_fight["ledger"]["hp"] = 0
    after_the_fight["ledger"]["exits"].append({"id": "percy", "exit": EXIT_DOWN, "round": 7})
    after_the_fight["ledger"]["counters"]["bosses_killed"] += 1

    back = apply_document(document)
    assert back["world"]["hero"]["tx"] == live["world"]["hero"]["tx"]
    assert back["world"]["hero"]["ty"] == live["world"]["hero"]["ty"]
    assert back["ledger"]["hp"] == live["ledger"]["hp"]
    assert back["ledger"]["counters"] == live["ledger"]["counters"]
    assert back["ledger"]["exits"] == live["ledger"]["exits"], "the fight's row survived a reload"
    assert back["ledger"]["verdict"] == verdict_of(live["ledger"]["exits"])
    assert round_trip_problems(live) == [FACING_LOSS]

    # The director restores through pp_save_apply and copies no field itself.
    text = read_battle()
    assert continue_problems(text) == [], continue_problems(text)
    assert "pp_save_apply" in save_family.function_body(text, "pp_battle_continue")
    for stolen in ("pp_ledger_new", "pp_overworld_new", "_d.", "global.pp_ledger ="):
        assert stolen not in save_family.function_body(text, "pp_battle_continue"), \
            "the game over restores %r itself instead of through pp_save_apply" % stolen


def continue_problems(text: str) -> list[str]:
    """Every way the game over's CONTINUE can stop being the save module's one door."""
    problems = []
    body = save_family.function_body(text, "pp_battle_continue")
    if "if (!pp_save_apply())" not in body:
        problems.append("pp_battle_continue no longer calls pp_save_apply")
    for stolen in ("pp_ledger_new", "pp_overworld_new", "_d.", "global.pp_ledger ="):
        if stolen in body:
            problems.append("pp_battle_continue restores %r itself" % stolen)
    step = save_family.function_body(text, "pp_battle_step_gameover")
    if 'pp_save_read("game over continue")' not in step:
        problems.append("CONTINUE no longer re-reads the slot, so a stale in memory read is applied")
    return problems


def test_a_defeat_leaves_the_runs_health_to_the_save():
    """A lost fight writes no ledger health, so the only health a defeat restores is the file's."""
    record = save_family.function_body(read_battle(), "pp_battle_record")
    assert "if (!_battle.defeated) {" in record
    # The first not-defeated guard is the example's record exit; the health guard is the last one.
    guarded = save_family.brace_block(record[record.rindex("if (!_battle.defeated) {"):],
                                      "if (!_battle.defeated) {")
    assert "_battle.ledger.hp = _battle.actor.hp;" in guarded, \
        "the run's health is written outside the not-defeated guard"
    assert record.count("_battle.ledger.hp") == 1, "a second place writes the run's health"
    # The fight's own actor is still put back to full, which is not the run.
    assert "_battle.actor.hp = _battle.actor.max_hp;" in record

    live = live_state(hp=9)
    back = apply_document(snapshot(live))
    assert back["ledger"]["hp"] == 9, "a defeat would come back at the fight's stand in health"


def test_continue_from_the_title_lands_on_the_saved_tile():
    """The title's CONTINUE and the game over's CONTINUE take the same door, so they land the same way."""
    title = save_family.read_code(TITLE_GML)
    block = title[title.index('if (_name == "CONTINUE") {'):]
    block = block[:block.index("if (_name == \"SETTINGS\")")]
    assert "pp_save_apply()" in block, "the title's CONTINUE no longer applies the save"
    assert "pp_title_goto_run_room()" in block, "the title applies a save and never leaves the room"
    assert "pp_save_ready()" in block, "CONTINUE is offered without a validated save"

    live = live_state()
    back = apply_document(snapshot(live))
    assert (back["world"]["hero"]["tx"], back["world"]["hero"]["ty"]) == (live["world"]["hero"]["tx"],
                                                                         live["world"]["hero"]["ty"])

    # The tile is the door tile, which is story blocked until ship_door_open; the flags are restored
    # first, so the walkable test sees the flag the save carried.
    tables = data_tables()
    door = tables["maps"]["ship_small"]
    assert collision(door, 18, 7, {}) == 1, "the saved tile is not gated, so the order is not proved"
    assert collision(door, 18, 7, {"ship_door_open": True}) == 0
    assert collision(door, 5, 3, {"ship_door_open": True}) == 1

    # A saved tile that is not walkable falls back to the named spawn instead of dropping the player.
    document = snapshot(live)
    document["x"], document["y"] = 5, 3
    back = apply_document(document)
    spawn = door["spawns"][document["spawn"]]
    assert (back["world"]["hero"]["tx"], back["world"]["hero"]["ty"]) == (spawn["x"], spawn["y"])


def test_the_game_over_frame_refuses_input_until_the_fade_is_done():
    """A held confirm cannot skip the fade or pick a row the player never saw."""
    text = read_battle()
    clear = save_family.function_body(text, "pp_battle_gameover_clear")
    assert "_battle.phase_steps > pp_battle_gameover_fade_steps()" in clear
    assert "return PP_FADE_STEPS;" in save_family.function_body(text, "pp_battle_gameover_fade_steps"), \
        "the game over fade is a second number instead of the app's own"
    step = save_family.function_body(text, "pp_battle_step_gameover")
    assert step.index("if (!pp_battle_gameover_clear(_battle)) return;") < step.index('pp_pressed("confirm")'), \
        "the game over reads input before the frame is clear"
    assert row_labels(save_family.function_body(text, "pp_battle_gameover_rows")) == [
        "CONTINUE", "RETURN TO TITLE"]


def test_a_refused_continue_says_its_sentence_instead_of_doing_nothing():
    """Spec 07 rule 1: a disabled entry is drawn in the second ink, blips, and never silently no-ops."""
    text = read_battle()
    can = save_family.function_body(text, "pp_battle_gameover_can_continue")
    assert "if (pp_save_ready()) return true;" in can
    assert "PPSaveState.absent" in can and "PPSaveState.failed" in can
    step = save_family.function_body(text, "pp_battle_step_gameover")
    assert step.count('"there is no save to continue"') == 2, \
        "one of the two refusal paths lost its sentence"
    assert 'pp_audio_play("menu_cancel")' in step, "a refused row makes no sound"
    assert '"the save could not be read"' in step, "a slot that was read and refused says nothing"


def test_removing_the_apply_call_turns_the_only_door_check_red(tmp_path):
    """Delete the one restore call from a copy of the director: continue_problems has to name it."""
    original = read_battle()
    assert continue_problems(original) == []
    mutated = original.replace("if (!pp_save_apply()) {", "if (false) {")
    assert mutated != original, "the mutation did not apply"
    scratch = tmp_path / "pp_battle_director.gml"
    scratch.write_text(mutated, encoding="utf-8")
    problems = continue_problems(scratch.read_text(encoding="utf-8"))
    assert any("pp_save_apply" in problem for problem in problems), problems


def row_labels(body: str) -> list[str]:
    """The row labels the game over frame returns, read out of its own literal."""
    inner = body[body.index("return ["):body.index("]") + 1]
    rows = save_family.quoted_strings(inner)
    assert rows, "the row list holds no label"
    return rows
