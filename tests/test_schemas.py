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

    # The box wraps on spaces, so the limit is on one WORD, not on a sentence: 30 characters fit, 31 do not.
    validator = jsonschema.Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/entry"})
    fits = {"id": "t", "speaker": "narrator", "lines": ["* " + "a" * check_data.LINE_CHARS]}
    over = {"id": "t", "speaker": "narrator", "lines": ["* " + "a" * (check_data.LINE_CHARS + 1)]}
    assert list(validator.iter_errors(fits)) == []
    assert list(validator.iter_errors(over)) != []


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
