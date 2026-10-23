"""Tests for data/schemas and the schema stage of tools/check_data.py.

Two jobs. First, prove the schemas are real 2020-12 documents and that the shipped data satisfies them. Second, prove
the schema stage is not decoration: it refuses things the hand written field checks do not, and its numbers stay equal
to the constants in tools/check_data.py, so the two descriptions of the same file cannot drift apart.
"""

from __future__ import annotations

import json
import os

import pytest

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS = os.path.join(ROOT, "data", "schemas")


def load_schema(name):
    with open(os.path.join(SCHEMAS, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def walk(schema, *keys):
    node = schema
    for key in keys:
        node = node[key]
    return node


def schema_messages(root, filename):
    return [e for e in check_data.check(str(root)) if e.startswith("data/%s:" % filename) and "schema " in e]


def test_every_table_file_has_a_schema_document():
    for rel, schema_name in check_data.SCHEMA_FILES.items():
        assert os.path.isfile(os.path.join(ROOT, "data", rel)), rel
        assert os.path.isfile(os.path.join(SCHEMAS, schema_name)), schema_name


def test_schemas_are_valid_2020_12_documents():
    jsonschema = pytest.importorskip("jsonschema")
    for schema_name in sorted(set(check_data.SCHEMA_FILES.values())):
        jsonschema.Draft202012Validator.check_schema(load_schema(schema_name))


def test_real_data_matches_every_schema():
    assert check_data.schema_failures(ROOT) == []


def test_check_data_reports_unknown_enemy_field(data_root, read_json, write_json):
    """The hand written checks read the fields they know and ignore the rest; the schema does not."""
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][0]["hitbox"] = 4
    write_json(path, data)

    messages = schema_messages(data_root, "enemies/all.json")
    assert messages, check_data.check(str(data_root))
    assert any("hitbox" in m or "Additional properties" in m for m in messages), messages


def test_check_data_reports_a_wait_command_without_its_number(data_root, read_json, write_json):
    """A wait with no steps would hang the runner, and the hand written checks only validate steps when present."""
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    data["scenes"][0]["commands"].insert(1, {"cmd": "wait"})
    write_json(path, data)

    messages = schema_messages(data_root, "scenes/all.json")
    assert messages, check_data.check(str(data_root))
    assert any("commands" in m for m in messages), messages


def test_check_data_reports_an_enemy_hp_below_one(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][1]["max_hp"] = 0
    write_json(path, data)

    messages = schema_messages(data_root, "enemies/all.json")
    assert any("max_hp" in m for m in messages), messages


def test_pattern_bounds_match_the_checker_constants():
    schema = load_schema("patterns.schema.json")
    frame = schema["$defs"]["frame"]["properties"]
    for field, (low, high) in check_data.PATTERN_FIELD_RANGES.items():
        if field == "size":
            continue
        assert frame[field]["minimum"] == low, field
        assert frame[field]["maximum"] == high, field
    assert frame["size"]["enum"] == [8, 16]
    wobble = schema["$defs"]["wobble"]["properties"]
    for field, (low, high) in check_data.WOBBLE_RANGES.items():
        assert wobble[field]["minimum"] == low, field
        assert wobble[field]["maximum"] == high, field
    pattern = schema["$defs"]["pattern"]["properties"]
    assert pattern["length"]["maximum"] == check_data.ARENA_CAP
    assert pattern["max_concurrent"]["minimum"] == 1
    assert pattern["max_concurrent"]["maximum"] == 4
    assert set(pattern["shape"]["enum"]) == check_data.PATTERN_SHAPES
    assert set(pattern["aim"]["enum"]) == check_data.PATTERN_AIM


def test_dialogue_bounds_match_the_checker_constants():
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_schema("dialogue.schema.json")
    entry = schema["$defs"]["entry"]["properties"]
    assert entry["lines"]["maxItems"] == check_data.PAGES * 3

    # The pages shape (decision D2): 3 pages, 3 lines a page, 28 characters a page line, 3 choices in a 12 character
    # panel. Each of these is a number in two places, so the two descriptions of the file are compared here.
    assert entry["pages"]["maxItems"] == check_data.PAGES
    assert entry["pages"]["items"]["$ref"] == "#/$defs/page"
    page = schema["$defs"]["page"]["properties"]
    assert page["lines"]["maxItems"] == check_data.PAGE_LINES
    assert page["lines"]["items"]["$ref"] == "#/$defs/page_line"
    assert schema["$defs"]["page_line"]["maxLength"] == check_data.LINE_CHARS
    assert entry["choices"]["maxItems"] == check_data.CHOICES
    choice = schema["$defs"]["choice"]["properties"]
    assert choice["label"]["maxLength"] == check_data.CHOICE_LABEL_CHARS

    # The box wraps on spaces, so the limit is on one WORD, not on a sentence: 28 characters fit, 29 do not.
    validator = jsonschema.Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/entry"})
    fits = {"id": "t", "speaker": "narrator", "lines": ["* " + "a" * check_data.LINE_CHARS]}
    over = {"id": "t", "speaker": "narrator", "lines": ["* " + "a" * (check_data.LINE_CHARS + 1)]}
    assert list(validator.iter_errors(fits)) == []
    assert list(validator.iter_errors(over)) != []

    # The pages shape takes the opposite rule for a page line: it is already one row, so its length is the limit.
    page_fits = {"id": "t", "speaker": "narrator", "pages": [{"lines": ["* " + "a" * (check_data.LINE_CHARS - 2)]}]}
    page_over = {"id": "t", "speaker": "narrator", "pages": [{"lines": ["* " + "a" * (check_data.LINE_CHARS - 1)]}]}
    assert list(validator.iter_errors(page_fits)) == []
    assert list(validator.iter_errors(page_over)) != []

    # Exactly one shape per entry: both is refused, and neither is refused.
    both = {"id": "t", "speaker": "narrator", "lines": ["* a"], "pages": [{"lines": ["* a"]}]}
    neither = {"id": "t", "speaker": "narrator"}
    assert list(validator.iter_errors(both)) != []
    assert list(validator.iter_errors(neither)) != []

    # A fourth page and a fourth choice are both outside the box.
    four_pages = {"id": "t", "speaker": "narrator",
                  "pages": [{"lines": ["* a"]} for _ in range(check_data.PAGES + 1)]}
    assert list(validator.iter_errors(four_pages)) != []


def test_enemy_bounds_match_the_checker():
    schema = load_schema("enemies.schema.json")
    enemy = schema["$defs"]["enemy"]["properties"]
    assert enemy["max_hp"]["minimum"] == 1
    assert enemy["max_hp"]["maximum"] == 9999
    assert enemy["trust_to_spare"]["minimum"] == 1
    assert enemy["trust_to_spare"]["maximum"] == 10
    assert enemy["spare_hp_percent"]["minimum"] == 1
    assert enemy["spare_hp_percent"]["maximum"] == 100
    attack = schema["$defs"]["attack"]["properties"]
    assert (attack["min"]["minimum"], attack["min"]["maximum"]) == (1, 99)
    assert (attack["max"]["minimum"], attack["max"]["maximum"]) == (1, 99)


def test_map_bounds_match_the_frame_and_palette():
    schema = load_schema("maps.schema.json")
    single = schema["$defs"]["map"]["properties"]
    # The checker refuses a map narrower than the 256 px frame at a 16 px tile.
    assert single["width"]["minimum"] * 16 >= check_data.FRAME_W
    assert single["palette_indices"]["maxItems"] == check_data.MAX_COLOURS_ON_SCREEN
    assert single["palette_indices"]["items"]["maximum"] == check_data.PALETTE_SIZE - 1
    trigger = schema["$defs"]["trigger"]["properties"]
    assert set(trigger["kind"]["enum"]) == check_data.TRIGGER_KINDS
    rail = schema["$defs"]["rail"]["properties"]["steps"]["items"]["properties"]
    assert set(rail["dir"]["enum"]) == check_data.DIRECTIONS


def test_scene_commands_match_the_checker_vocabulary():
    schema = load_schema("cutscenes.schema.json")
    definitions = schema["$defs"]
    commands = set()
    for name, definition in definitions.items():
        if not isinstance(definition, dict):
            continue
        cmd = definition.get("properties", {}).get("cmd", {})
        if isinstance(cmd, dict) and "const" in cmd:
            commands.add(cmd["const"])
    assert commands == check_data.SCENE_COMMANDS


# ----------------------------------------------------------------------------------------------------------------
# Talk cards (specs/16-talk-command.md section 15 check 1).

TALK_CARDS = os.path.join(ROOT, "data", "talk_cards.json")


def talk_cards_document():
    with open(TALK_CARDS, "r", encoding="utf-8") as handle:
        return json.load(handle)


def talk_card_validator():
    jsonschema = pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(load_schema("talk_cards.schema.json"))


def first_card(document):
    return document["cards"][0]


def _extra_card_field(document):
    first_card(document)["mood"] = "tired"


def _long_reply_line(document):
    card = first_card(document)
    neutral = card["pools"]["neutral"]
    assert isinstance(neutral, list), "the first card's neutral pool is bucketed; this case needs a flat one"
    neutral[0] = "a" * 61


def _one_want(document):
    first_card(document)["wants"] = first_card(document)["wants"][:1]


def _uppercase_keyword(document):
    first_card(document)["weak_topics"][0]["keywords"][0] = "Watch"


def _bucket_without_mid(document):
    first_card(document)["pools"]["weak"] = {"low": ["Twenty two years of this."],
                                             "high": ["Take the hatch. I never saw you."]}


def _wrong_kind(document):
    document["kind"] = "talk_card"


# name, mutation, the keyword JSON Schema reports, and the field path the failure must name
TALK_CARD_BAD_INSTANCES = [
    ("an extra card field", _extra_card_field, "additionalProperties", ("cards", 0)),
    ("a reply line of 61 characters", _long_reply_line, "maxLength", ("cards", 0, "pools", "neutral", 0)),
    ("one want instead of two", _one_want, "minItems", ("cards", 0, "wants")),
    ("an uppercase keyword", _uppercase_keyword, "pattern", ("cards", 0, "weak_topics", 0, "keywords", 0)),
    ("a bucket object with no mid", _bucket_without_mid, "required", ("cards", 0, "pools", "weak")),
    ("the wrong kind", _wrong_kind, "const", ("kind",)),
]


def talk_card_errors(validator, document):
    """Every error, including the ones a oneOf wrapper hides.

    A pool is oneOf (one array of 3, or three named buckets), so a fault inside a pool is reported only as "is not
    valid under any of the given schemas" at the pool. The nested errors carry absolute paths, so unrolling them is
    what makes a bad case prove it failed for the RIGHT reason and not merely that it failed.
    """
    errors = []
    stack = list(validator.iter_errors(document))
    while stack:
        error = stack.pop()
        errors.append(error)
        stack.extend(list(getattr(error, "context", None) or []))
    return errors


def test_talk_cards_schema_runs_in_the_data_checker():
    """Spec 16 section 15 check 1 asks for this schema to be enforced; nothing enforces it unless it is named here."""
    assert check_data.SCHEMA_FILES.get("talk_cards.json") == "talk_cards.schema.json"


def test_talk_cards_schema_accepts_the_shipping_file():
    validator = talk_card_validator()
    document = talk_cards_document()
    assert document["cards"], "data/talk_cards.json has no cards"
    assert list(validator.iter_errors(document)) == []


@pytest.mark.parametrize("name,mutate,expected,path", TALK_CARD_BAD_INSTANCES,
                         ids=[case[0] for case in TALK_CARD_BAD_INSTANCES])
def test_talk_cards_schema_refuses_a_bad_instance_for_the_right_reason(name, mutate, expected, path):
    validator = talk_card_validator()
    document = talk_cards_document()
    mutate(document)
    reported = talk_card_errors(validator, document)
    errors = [error for error in reported if error.validator == expected]
    assert errors, "%s was accepted: %s" % (name, [(e.validator, e.message) for e in reported])
    assert any(tuple(error.absolute_path)[:len(path)] == path for error in errors), \
        "%s failed, but not at %s: %s" % (name, path, [(list(e.absolute_path), e.message) for e in errors])


def test_check_data_reports_a_bad_talk_card(data_root, read_json, write_json):
    """End to end: the checker itself, not only the validator, has to refuse the file and name the field."""
    path = data_root / "data" / "talk_cards.json"
    document = read_json(path)
    document["cards"][0]["voice"] = ""
    write_json(path, document)

    messages = schema_messages(data_root, "talk_cards.json")
    assert messages, check_data.check(str(data_root))
    assert any("voice" in m for m in messages), messages


def test_the_phase_row_and_the_phase_card_name_one_phase():
    """Card t_155e22e2: talk_phase is the card's phase, talk_set is a dialogue id, and the two never trade places.

    The decision this pins: the phase crossing's talk card is selected by a phase string the phase row carries
    (talk_phase), copied from the card's own phase, while talk_set stays an id in data/dialogue/all.json because it
    names the choice lines step 1 draws. Reading either name in the other namespace is the drift the card settled.
    """
    cards = talk_cards_document()["cards"]
    phase_cards = {(card["enemy"], card["phase"]) for card in cards if card["phase"]}
    assert ("percy", "percy_phase2") in phase_cards

    with open(os.path.join(ROOT, "data", "enemies", "all.json"), "r", encoding="utf-8") as handle:
        enemies = json.load(handle)["enemies"]
    with open(os.path.join(ROOT, "data", "dialogue", "all.json"), "r", encoding="utf-8") as handle:
        dialogue_ids = {row["id"] for row in json.load(handle)["dialogue"]}

    rows = [(enemy["id"], phase) for enemy in enemies for phase in enemy.get("phases", [])]
    assert rows, "no enemy ships a phase row, so this test would pass without checking anything"
    for enemy_id, row in rows:
        assert row["talk_set"] in dialogue_ids, (enemy_id, row["talk_set"])
        if "talk_phase" in row:
            assert (enemy_id, row["talk_phase"]) in phase_cards, (enemy_id, row["talk_phase"])

    percy = [row for enemy_id, row in rows if enemy_id == "percy"][0]
    assert percy["talk_phase"] == "percy_phase2"
    assert percy["talk_set"] == "talk_percy_phase2"

    with open(os.path.join(ROOT, "specs", "16-talk-command.md"), "r", encoding="utf-8") as handle:
        spec = handle.read()
    assert "talk_phase" in spec and "talk_set` stays a dialogue id" in spec, (
        "spec 16 section 10 no longer names the field that selects the phase card")
