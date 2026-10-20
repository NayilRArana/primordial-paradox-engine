"""Check that every committed subsystem has a provenance entry, and that each entry says how ours differs.

The rule from PLAN.md section 1 and from the card: a subsystem with no provenance entry is not commit ready. This
script makes the rule mechanical instead of a promise.

It requires:
  1. knowledge\\PROVENANCE.md exists and has a "## module map" section.
  2. Every module file under game\\scripts\\<name>\\<name>.gml and every object directory appears in that map, so no
     module can land without an owner.
  3. Every subsystem entry (a "## " heading) carries the four fields of the entry format: Studied, Mechanics learned,
     Our implementation differs by, Copied expression.
  4. "Copied expression: none" is stated, since that is the claim the log exists to make.

Usage:
    python tools/check_provenance.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVENANCE = os.path.join(ROOT, "knowledge", "PROVENANCE.md")
REQUIRED_FIELDS = [
    "Studied:",
    "Mechanics learned",
    "Our implementation differs by",
    "Copied expression: none",
]


def modules(root: str) -> list[str]:
    found = []
    scripts = os.path.join(root, "game", "scripts")
    if os.path.isdir(scripts):
        for name in sorted(os.listdir(scripts)):
            if os.path.isfile(os.path.join(scripts, name, name + ".gml")):
                found.append("game/scripts/%s/%s.gml" % (name, name))
    objects = os.path.join(root, "game", "objects")
    if os.path.isdir(objects):
        for name in sorted(os.listdir(objects)):
            if os.path.isfile(os.path.join(objects, name, name + ".yy")):
                found.append("game/objects/%s" % name)
    return found


def parse_entries(text: str) -> list[tuple[str, str]]:
    """Split the file into (heading, body) pairs on level two headings."""
    headings = [m for m in re.finditer(r"^## (.+)$", text, re.MULTILINE)]
    entries = []
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        entries.append((match.group(1).strip(), text[start:end]))
    return entries


def check(root: str = ROOT) -> list[str]:
    errors: list[str] = []
    if not os.path.isfile(PROVENANCE):
        return ["knowledge/PROVENANCE.md: missing"]

    with open(PROVENANCE, "r", encoding="utf-8-sig") as fh:
        text = fh.read()

    entries = parse_entries(text)
    if not entries:
        errors.append("knowledge/PROVENANCE.md: no entries")

    module_map = None
    for heading, body in entries:
        if heading.lower().startswith("module map"):
            module_map = body
    if module_map is None:
        errors.append("knowledge/PROVENANCE.md: no '## module map' section")
    else:
        for path in modules(root):
            key = path.replace("game/scripts/", "").replace(".gml", "").replace("game/objects/", "")
            if path not in module_map and key not in module_map:
                errors.append("knowledge/PROVENANCE.md: %s is not in the module map" % path)

    for heading, body in entries:
        if heading.lower().startswith("module map"):
            continue
        for field in REQUIRED_FIELDS:
            if field not in body:
                errors.append("knowledge/PROVENANCE.md: entry %r is missing %r" % (heading, field))

    if "Copied expression: none" not in text:
        errors.append("knowledge/PROVENANCE.md: never states 'Copied expression: none'")

    if len(modules(root)) == 0:
        errors.append("game/: no modules found, so nothing was proved")

    return errors


def main() -> int:
    errors = check()
    if errors:
        for line in errors:
            print("FAIL " + line)
        print("\n%d provenance problem(s)" % len(errors))
        return 1
    print("check_provenance: %d modules, every one mapped to an entry" % len(modules(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
