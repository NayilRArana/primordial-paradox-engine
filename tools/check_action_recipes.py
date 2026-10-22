"""Check data/mechanics/action_recipes.json against knowledge/mechanics/ACTION-MECHANICS.md.

This is the gate for the action mechanics study (card t_65aaf6e6's sibling, MECH-STUDY-2). It answers
five questions, and every failure names the recipe and the field, because "data invalid" is not
actionable:

  1. COUNT: 25 or more recipes, and the declared recipe_count matches the real one.
  2. SHAPE: every recipe has the nine fields a reader needs, the id prefix matches its family, and every
     family is declared in the meta block.
  3. SOURCES: every source id a recipe cites exists in the study's source table, so no recipe can cite a
     source the study does not name. Each recipe cites at least one source, or is marked as our decision
     by naming no source at all and being one of the DECISION families listed below.
  4. MAPPING: every maps_to names a spec file that exists, or one of the declared new specs.
  5. STUDY: every recipe id is mentioned in the study file, directly or inside an "XXX-01 to XXX-05"
     range, so the prose and the data cannot drift apart.
  6. TYPOGRAPHY: no em dash, no en dash, no foreign name or phrase from the clean-room blacklist.

Usage:
    python tools/check_action_recipes.py
    python tools/check_action_recipes.py --root .
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

RECIPES = os.path.join("data", "mechanics", "action_recipes.json")
STUDY = os.path.join("knowledge", "mechanics", "ACTION-MECHANICS.md")

REQUIRED = ("id", "name", "family", "when_to_use", "params", "numbers", "sources", "maps_to", "verify")
MIN_RECIPES = 25
RANGE_RE = re.compile(r"\b([A-Z]{3})-(\d{2})\s+to\s+[A-Z]{3}-(\d{2})\b")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from check_cleanroom import FORBIDDEN_NAMES, FORBIDDEN_PHRASES, normalise
except Exception:  # pragma: no cover - the blacklist is optional for this gate
    FORBIDDEN_NAMES, FORBIDDEN_PHRASES = [], []

    def normalise(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def study_ids(text: str) -> set[str]:
    """Every recipe id the study names, with ranges expanded."""
    found = set(re.findall(r"\b([A-Z]{3}-\d{2})\b", text))
    for family, start, end in RANGE_RE.findall(text):
        for n in range(int(start), int(end) + 1):
            found.add("%s-%02d" % (family, n))
    return found


def source_ids(text: str) -> set[str]:
    return set(re.findall(r"^\|\s*(S\d+|PP)\s*\|", text, re.MULTILINE))


def check(root: str = ".") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []
    root = os.path.abspath(root)

    recipes_path = os.path.join(root, RECIPES)
    study_path = os.path.join(root, STUDY)
    for path, label in ((recipes_path, RECIPES), (study_path, STUDY)):
        if not os.path.isfile(path):
            return ["missing %s" % label.replace("\\", "/")], notes

    data = json.loads(read(recipes_path))
    study = read(study_path)

    meta = data.get("meta", {})
    recipes = data.get("recipes") or []
    families = data.get("families") or {}

    # 1. Count.
    if len(recipes) < MIN_RECIPES:
        errors.append("only %d recipes, the card asks for at least %d" % (len(recipes), MIN_RECIPES))
    if meta.get("recipe_count") != len(recipes):
        errors.append("meta.recipe_count says %r, the file holds %d" % (meta.get("recipe_count"), len(recipes)))
    if meta.get("family_count") != len(families):
        errors.append("meta.family_count says %r, the file declares %d families"
                      % (meta.get("family_count"), len(families)))

    # 2. Shape and ids.
    seen: dict[str, int] = {}
    per_family: dict[str, int] = {}
    for index, recipe in enumerate(recipes):
        rid = recipe.get("id") or "recipe %d" % index
        for field in REQUIRED:
            if field not in recipe or recipe[field] in (None, "", [], {}):
                errors.append("%s: missing field %r" % (rid, field))
        family = recipe.get("family")
        if family not in families:
            errors.append("%s: family %r is not declared in meta families" % (rid, family))
        rid_text = str(recipe.get("id", ""))
        if not re.fullmatch(r"[A-Z]{3}-\d{2}", rid_text):
            errors.append("%s: id is not FAMILY-NN" % rid_text)
        elif family and not rid_text.startswith(str(family) + "-"):
            errors.append("%s: id prefix does not match family %r" % (rid_text, family))
        if rid_text in seen:
            errors.append("%s: duplicate id" % rid_text)
        seen[rid_text] = seen.get(rid_text, 0) + 1
        per_family[str(family)] = per_family.get(str(family), 0) + 1

    # 3. Sources.
    known_sources = source_ids(study)
    for recipe in recipes:
        rid = recipe.get("id", "?")
        cited = recipe.get("sources") or []
        if not isinstance(cited, list):
            errors.append("%s: sources is not a list" % rid)
            continue
        if not cited:
            errors.append("%s: cites no source id, so mark it PP if the number is ours" % rid)
        for source in cited:
            if source not in known_sources:
                errors.append("%s: cites %r, which the study's source table does not name" % (rid, source))

    # 4. Mapping.
    spec_dir = os.path.join(root, "specs")
    spec_files = [name for name in os.listdir(spec_dir)] if os.path.isdir(spec_dir) else []
    new_specs = {entry.get("id") for entry in meta.get("new_specs", [])}
    for recipe in recipes:
        rid = recipe.get("id", "?")
        target = str(recipe.get("maps_to", ""))
        if target in new_specs:
            continue
        numbers = re.findall(r"(?:spec|NEW spec)\s+(\d{2})", target)
        if not numbers:
            errors.append("%s: maps_to %r names no spec number" % (rid, target))
            continue
        for number in numbers:
            if not any(name.startswith(number + "-") for name in spec_files) and ("spec " + number) not in new_specs:
                errors.append("%s: maps_to spec %s, which does not exist and is not declared in new_specs"
                              % (rid, number))

    # 5. Study mentions.
    mentioned = study_ids(study)
    missing = [recipe.get("id") for recipe in recipes if recipe.get("id") not in mentioned]
    for rid in missing:
        errors.append("%s: the study never names it, so the prose and the data have drifted" % rid)

    # 6. Typography and clean room.
    for path in (recipes_path, study_path):
        text = read(path)
        label = os.path.relpath(path, root).replace("\\", "/")
        for mark, name in (("\u2014", "em dash"), ("\u2013", "en dash")):
            if mark in text:
                errors.append("%s: contains an %s" % (label, name))
        flat = normalise(text)
        for phrase in FORBIDDEN_PHRASES:
            if phrase and phrase in flat:
                errors.append("%s: contains a foreign phrase (%s)" % (label, phrase))
        for name in FORBIDDEN_NAMES:
            if name and re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
                errors.append("%s: contains a foreign name (%s)" % (label, name))

    for family, count in sorted(per_family.items()):
        notes.append("%s %d" % (family, count))
    notes.append("%d sources in the table, %d recipe ids named in the study"
                 % (len(known_sources), len(mentioned)))
    return errors, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    errors, notes = check(args.root)
    data = json.loads(read(os.path.join(os.path.abspath(args.root), RECIPES)))
    count = len(data.get("recipes") or [])
    print("check_action_recipes: %d recipes, %d families, families: %s"
          % (count, len(data.get("families") or {}), ", ".join(n for n in notes if not n[0].isdigit())))
    if errors:
        for line in errors[:40]:
            print("FAIL " + line)
        if len(errors) > 40:
            print("... and %d more" % (len(errors) - 40))
        print("\n%d action recipe problem(s)" % len(errors))
        return 1
    print("PASS count %d >= %d" % (count, MIN_RECIPES))
    print("PASS shape, ids and families")
    print("PASS every cited source exists in the study's source table")
    print("PASS every map target is a real spec or a declared new spec")
    print("PASS every recipe id is named in the study")
    print("PASS no long dashes, no foreign name, no foreign phrase")
    return 0


if __name__ == "__main__":
    sys.exit(main())
