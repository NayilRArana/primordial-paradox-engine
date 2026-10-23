"""Tests for the frame field audit on the dodge recipe reader.

Card BATTLE-CRASH (t_da94341c). The 02:34 shipping build died on the first dodge frame of every fight with

    Variable <unknown_object>.aim not set before reading it. | at gml_Script_pp_recipe_event

because pp_recipe_event read `_frame.aim` while `aim` is a RECIPE level field only: data/schemas/patterns.schema.json
declares the frame object with additionalProperties false and no aim key, and no frame in data/patterns/all.json
carries one. GML returns undefined for an unknown key in debug and raises in release, so the crash only reached a
player through a compiled build.

The lesson is not "delete one expression", it is that the recipe reader had no mechanical link to the frame contract
it reads. This audit is that link: every `_frame.<key>` read in pp_dodge_recipe.gml must be a key the schema declares.
A negative control proves the audit flags the exact expression that crashed.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "data", "schemas", "patterns.schema.json")
RECIPE_GML = os.path.join(ROOT, "game", "scripts", "pp_dodge_recipe", "pp_dodge_recipe.gml")

# Reads of the frame struct by name. The pattern deliberately allows a nested read (`_frame.wobble.amp`) and only
# captures the first key, because that is the one the data contract governs.
FRAME_READ = re.compile(r"_frame\.([A-Za-z_][A-Za-z0-9_]*)")


def declared_frame_fields():
    with open(SCHEMA, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    return set(schema["$defs"]["frame"]["properties"].keys())


def reads_in(source):
    return {match.group(1) for match in FRAME_READ.finditer(source)}


def test_the_recipe_reader_only_reads_declared_frame_fields():
    with open(RECIPE_GML, "r", encoding="utf-8") as fh:
        source = fh.read()
    declared = declared_frame_fields()
    read = reads_in(source)
    assert read, "the audit found no frame reads at all, so it would pass on an empty file"
    assert read <= declared, "pp_dodge_recipe.gml reads frame fields the schema does not declare: %s" % (
        sorted(read - declared),
    )


def test_the_frame_contract_keeps_aim_at_the_recipe_level():
    """If a per frame aim override is ever wanted, this test should fail and force the schema change first."""
    with open(SCHEMA, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    frame = schema["$defs"]["frame"]
    assert "aim" not in frame["properties"]
    assert frame.get("additionalProperties") is False
    assert "aim" in schema["$defs"]["pattern"]["properties"]


def test_the_audit_flags_the_expression_that_crashed():
    """Negative control: the exact source line from the 02:34 build must be reported as undeclared."""
    crashed = '    var _aims = _pattern_aim == "at_marker" || _frame.aim == true;\n'
    undeclared = reads_in(crashed) - declared_frame_fields()
    assert undeclared == {"aim"}


def test_the_audit_accepts_the_shipped_frames():
    """Positive control: the fields pp_recipe_event legitimately reads stay green."""
    legit = (
        "_frame.angle; _frame.count; _frame.spread; _frame.at; _frame.delay; _frame.speed; _frame.accel; "
        "_frame.curve; _frame.life; _frame.size; _frame.origin; _frame.jitter_angle; _frame.wobble.amp;"
    )
    assert reads_in(legit) <= declared_frame_fields()
