"""Tests for card t_baafc947 (MUS-DISSONANCE): the 30 device catalogue and its schema.

The catalogue is a data file, so the tests are the three things the card asked for, asserted
independently of the checker's own wording: there are 30 devices, every device has a resolution,
and the document validates against the schema written for it. The rate policy is recomputed here
from the percentages, so a hand edit to the JSON cannot quietly move the budget.
"""

from __future__ import annotations

import json
import math
import os

import pytest

import check_dissonance_rules as rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "data", "dissonance_rules.json")
SCHEMA_PATH = os.path.join(ROOT, "data", "schemas", "dissonance_rules.schema.json")
MD_PATH = os.path.join(ROOT, "knowledge", "MUSIC-DISSONANCE.md")


def load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def data():
    return load(JSON_PATH)


@pytest.fixture(scope="module")
def schema():
    return load(SCHEMA_PATH)


def test_the_checker_passes():
    assert rules.check(ROOT) == []


def test_the_schema_is_a_valid_2020_12_document(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["$schema"].endswith("2020-12/schema")


def test_the_shipped_document_validates_against_the_schema(data, schema):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(data)) == []


def test_there_are_thirty_devices_with_unique_ids(data):
    ids = [rule["id"] for rule in data["rules"]]
    assert len(ids) == 30
    assert len(set(ids)) == 30
    assert ids == ["DIS-%02d" % number for number in range(1, 31)]


def test_every_device_resolves(data):
    for rule in data["rules"]:
        resolution = rule["resolution"]
        assert resolution["target"], rule["id"]
        assert resolution["direction"] in ("up", "down", "either", "none_required"), rule["id"]
        assert resolution["within_beats_max"] > 0, rule["id"]
        assert rule["duration_beats"]["min"] <= rule["duration_beats"]["max"], rule["id"]


def test_every_device_carries_the_two_named_forbidden_rules(data):
    for rule in data["rules"]:
        assert "F1" in rule["forbidden"], rule["id"]
        assert "F2" in rule["forbidden"], rule["id"]


def test_the_rate_budget_follows_from_the_percentages(data):
    policy = data["rate_policy"]
    lo = policy["device_rate_min_percent"] / 100.0
    hi = policy["device_rate_max_percent"] / 100.0
    assert math.isclose(lo, 0.03, abs_tol=1e-9)
    assert math.isclose(hi, 0.06, abs_tol=1e-9)
    for notes in (policy["note_count_per_8_bars_3_4"], policy["note_count_per_8_bars_4_4"]):
        assert notes * lo <= policy["devices_per_8_bars_min"] + 0.25
        assert policy["devices_per_8_bars_max"] + 0.25 >= notes * hi


def test_no_device_exceeds_its_risk_cap(data):
    caps = {int(level): row["max_per_8_bars"] for level, row in data["risk_levels"].items()}
    for rule in data["rules"]:
        assert rule["rate_per_8_bars"]["max"] <= caps[rule["risk"]], rule["id"]


def test_every_device_cites_a_source_that_exists(data):
    local = set(data["sources"])
    published = rules.bible_source_ids(ROOT)
    for rule in data["rules"]:
        assert rule["sources"], rule["id"]
        for source in rule["sources"]:
            assert source in local or source in published, (rule["id"], source)


def test_the_markdown_names_every_device(data):
    with open(MD_PATH, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    for rule in data["rules"]:
        assert rule["id"] in text, rule["id"]
    for row in data["forbidden"]:
        assert row["id"] in text, row["id"]
