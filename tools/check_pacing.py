"""Prove the pacing study and its recipe file, for card t_0ef1125d (MECH-STUDY-3).

This checker owns exactly two artifacts:

    knowledge/mechanics/PACING-AND-CUTSCENES.md
    data/mechanics/pacing_recipes.json   (mirrored to game/datafiles/mechanics/)

and it asserts the card's acceptance conditions plus the internal consistency the study claims:

  1. at least 25 recipes, ids unique and sequential from PAC-01, each recipe with at least three numeric
     parameters, and the declared family counts matching the recipes actually present;
  2. the beat sheet sums to exactly 900 seconds and every running total recomputes from the durations;
  3. the per kind totals recompute from the beats, the cutscene share is at most 60 percent and walk plus
     battle at least 20 percent;
  4. every source id a recipe cites resolves in the study's section 10 table, and the declared list of used
     ids matches what the recipes actually cite;
  5. the measured gates (first input, full control, first fight, first save, first interior) fall inside the
     ceilings PAC-32 states, and the measured values PAC-32 carries match the sheet;
  6. neither file contains an em dash, an en dash or a horizontal bar;
  7. the data file trips none of the clean room gate's names or phrases, because data/ is scanned and a
     title belongs in the study, not in a data file.

Usage:
    python tools/check_pacing.py
    python tools/check_pacing.py --root .
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

DASHES = ("\u2014", "\u2013", "\u2015")
RECIPE_RE = re.compile(r"^PAC-\d\d$")
SOURCE_ROW_RE = re.compile(r"^\|\s*(P-\d\d)\s*\|")
DATA_FILE = os.path.join("data", "mechanics", "pacing_recipes.json")
STUDY_FILE = os.path.join("knowledge", "mechanics", "PACING-AND-CUTSCENES.md")
TOTAL_SECONDS = 900


def numeric_count(value) -> int:
    """How many real numbers a params tree holds, so a recipe of prose is caught."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return sum(numeric_count(item) for item in value)
    if isinstance(value, dict):
        return sum(numeric_count(item) for item in value.values())
    return 0


def clean_room_errors(root: str, text: str) -> list[str]:
    """The gate's own blacklists, applied to one file the gate scans."""
    tools_dir = os.path.join(root, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        import check_cleanroom as gate
    except Exception as exc:                                  # pragma: no cover
        return ["clean room: could not import check_cleanroom (%s)" % exc]
    name_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in gate.FORBIDDEN_NAMES) + r")\b", re.IGNORECASE)
    errors = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in name_re.finditer(line):
            errors.append("clean room: %s line %d names %r" % (DATA_FILE, number, match.group(0)))
        flat = gate.normalise(line)
        for phrase in gate.FORBIDDEN_PHRASES:
            if phrase in flat:
                errors.append("clean room: %s line %d carries a refused phrase" % (DATA_FILE, number))
    return errors


def check(root: str = ".") -> list[str]:
    root = os.path.abspath(root)
    data_path = os.path.join(root, DATA_FILE)
    study_path = os.path.join(root, STUDY_FILE)
    errors: list[str] = []

    if not os.path.isfile(data_path):
        return ["missing %s" % DATA_FILE]
    if not os.path.isfile(study_path):
        return ["missing %s" % STUDY_FILE]
    with open(data_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    with open(study_path, "r", encoding="utf-8-sig") as handle:
        study = handle.read()

    recipes = data.get("recipes", [])
    if len(recipes) < 25:
        errors.append("recipes: %d, fewer than the 25 the card requires" % len(recipes))
    ids = [recipe.get("id", "") for recipe in recipes]
    if len(set(ids)) != len(ids):
        errors.append("recipes: duplicate ids")
    if sorted(ids) != ["PAC-%02d" % n for n in range(1, len(recipes) + 1)]:
        errors.append("recipes: ids are not a clean sequence from PAC-01")
    for recipe in recipes:
        if not RECIPE_RE.match(recipe.get("id", "")):
            errors.append("recipes: bad id %r" % recipe.get("id"))
        if numeric_count(recipe.get("params", {})) < 3:
            errors.append("recipes: %s has fewer than three numeric parameters" % recipe.get("id"))
        if not recipe.get("forbidden"):
            errors.append("recipes: %s lists no refusal" % recipe.get("id"))
    counted: dict[str, int] = {}
    for recipe in recipes:
        family = recipe.get("family", "?")
        counted[family] = counted.get(family, 0) + 1
    declared = data.get("meta", {}).get("families", {})
    if counted != declared:
        errors.append("recipes: family counts %s do not match the declared %s" % (counted, declared))
    if declared and sum(declared.values()) != len(recipes):
        errors.append("recipes: declared families sum to %d, not %d" % (sum(declared.values()), len(recipes)))

    sheet = data.get("beat_sheet", {})
    beats = sheet.get("beats", [])
    if not beats:
        errors.append("beats: the sheet is empty")
    total = 0
    for beat in beats:
        total += beat.get("seconds", 0)
        if beat.get("running_total") != total:
            errors.append("beats: %s running total %r, recomputed %d"
                          % (beat.get("id"), beat.get("running_total"), total))
    if total != TOTAL_SECONDS:
        errors.append("beats: sum is %d seconds, not %d" % (total, TOTAL_SECONDS))
    if sheet.get("total_seconds") != TOTAL_SECONDS:
        errors.append("beats: declared total_seconds is %r" % sheet.get("total_seconds"))
    if len({beat.get("id") for beat in beats}) != len(beats):
        errors.append("beats: duplicate ids")

    by_kind: dict[str, int] = {}
    for beat in beats:
        kind = beat.get("kind", "?")
        by_kind[kind] = by_kind.get(kind, 0) + beat.get("seconds", 0)
    if by_kind != sheet.get("totals_by_kind", {}):
        errors.append("beats: kind totals %s do not match the declared %s" % (by_kind, sheet.get("totals_by_kind")))
    play = by_kind.get("walk", 0) + by_kind.get("battle", 0)
    cutscene = by_kind.get("cutscene", 0)
    if total:
        if cutscene / total > 0.6:
            errors.append("beats: cutscene share %.3f is over 0.6" % (cutscene / total))
        if play / total < 0.2:
            errors.append("beats: play share %.3f is under 0.2" % (play / total))
        if abs(sheet.get("cutscene_share", 0) - cutscene / total) > 0.001:
            errors.append("beats: declared cutscene_share does not recompute")
        if abs(sheet.get("play_share", 0) - play / total) > 0.001:
            errors.append("beats: declared play_share does not recompute")
    if sheet.get("play_seconds") != play:
        errors.append("beats: declared play_seconds %r, recomputed %d" % (sheet.get("play_seconds"), play))

    table_ids = set()
    for line in study.splitlines():
        match = SOURCE_ROW_RE.match(line.strip())
        if match:
            table_ids.add(match.group(1))
    cited = set()
    for recipe in recipes:
        for source in recipe.get("source", []):
            cited.add(source)
    missing = sorted(cited - table_ids)
    if missing:
        errors.append("sources: cited but absent from the section 10 table: %s" % ", ".join(missing))
    declared_sources = set(data.get("checks", {}).get("source_ids_used", []))
    if declared_sources and declared_sources != cited:
        errors.append("sources: declared list differs from the recipes (%s)"
                      % ", ".join(sorted(declared_sources ^ cited)))

    gates = next((recipe for recipe in recipes if recipe.get("id") == "PAC-32"), None)
    if gates is None:
        errors.append("gates: PAC-32 is missing")
    else:
        params = gates.get("params", {})
        starts = {beat["id"]: beat["running_total"] - beat["seconds"] for beat in beats}
        pairs = (
            ("first_input_seconds", "services_interlude", "first_input_seconds_max"),
            ("full_control_seconds", "yard_walk", "full_control_seconds_max"),
            ("first_fight_seconds", "first_encounter_hound", "first_fight_start_seconds_max"),
            ("first_save_seconds", "cabin_save", "first_save_start_seconds_max"),
            ("first_interior_seconds", "dock_office", "first_interior_seconds_max"),
        )
        for label, beat_id, ceiling_key in pairs:
            measured, ceiling = starts.get(beat_id), params.get(ceiling_key)
            if measured is None:
                errors.append("gates: beat %s is missing from the sheet" % beat_id)
            elif ceiling is None:
                errors.append("gates: %s has no ceiling" % label)
            elif measured > ceiling:
                errors.append("gates: %s is %d s, over the ceiling %d s" % (label, measured, ceiling))
            elif params.get("measured_" + label) not in (None, measured):
                errors.append("gates: %s declared %r, sheet says %r"
                              % (label, params.get("measured_" + label), measured))

    for path, text in ((DATA_FILE, json.dumps(data, ensure_ascii=False)), (STUDY_FILE, study)):
        for dash in DASHES:
            if dash in text:
                errors.append("dashes: %s contains U+%04X" % (path, ord(dash)))

    errors.extend(clean_room_errors(root, json.dumps(data, ensure_ascii=False)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the pacing study and its recipe file.")
    parser.add_argument("--root", default=os.getcwd(), help="repository root, default the working directory")
    args = parser.parse_args()
    errors = check(args.root)
    data_path = os.path.join(args.root, DATA_FILE)
    try:
        with open(data_path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        summary = "%d recipes, %d beats, %d seconds" % (
            len(data.get("recipes", [])), len(data.get("beat_sheet", {}).get("beats", [])),
            sum(beat.get("seconds", 0) for beat in data.get("beat_sheet", {}).get("beats", [])))
    except Exception:
        summary = "no readable data file"
    for error in errors:
        print("FAIL  " + error)
    if errors:
        print("check_pacing: %d problem(s), %s" % (len(errors), summary))
        return 1
    print("check_pacing: pass, %s" % summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
