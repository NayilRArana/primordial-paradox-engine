"""Hold the clean-room gate on the specs: no code is written from a spec nobody has confirmed.

The manager's rule after the breach of 2026-10-19: specs 01 to 13 were drafted before the notice, so a reviewer who has
read only public genre design and the official GameMaker manual has to confirm or rewrite each one before code is
written from it. Reading the spec against a decompilation is exactly what the rule forbids, so the check cannot compare
text against a corpus. What it can do is make the gate mechanical:

1. EVERY SPEC HAS A ROW. Each specs\\NN-*.md file needs one row in knowledge\\SPEC-REVIEW.md.
2. A STATUS MAY NOT LIE. Only `confirmed` or `rewritten` count as a pass, and each needs a reviewer and a date. A row
   that says reviewed, checked or ok is an error, because those words have no agreed meaning here.
3. PENDING IS LOUD. The default run prints every pending spec by name and exits 0, so the debt shows up on every run
   without stopping work that does not come from a spec. `--strict` exits 1 while anything is pending, and that is the
   check an implementation card runs before it writes code.

Usage:
    python tools/check_spec_review.py
    python tools/check_spec_review.py --strict
    python tools/check_spec_review.py --root .
"""

from __future__ import annotations

import argparse
import os
import re
import sys

REVIEW_FILE = os.path.join("knowledge", "SPEC-REVIEW.md")
PASS_WORDS = {"confirmed", "rewritten"}
LIE_WORDS = {"reviewed", "checked", "ok", "approved", "looks good"}
ROW_RE = re.compile(r"^\|\s*`?([^|`]+?)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")


def read(path: str) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read()
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def spec_files(root: str) -> list[str]:
    base = os.path.join(root, "specs")
    if not os.path.isdir(base):
        return []
    found = []
    for name in sorted(os.listdir(base)):
        if name.lower().endswith(".md"):
            found.append("specs/" + name)
    return found


def review_rows(root: str) -> dict[str, tuple[str, str, str, str]]:
    """Every row of the ledger: spec -> (status, reviewer, date, note)."""
    rows: dict[str, tuple[str, str, str, str]] = {}
    path = os.path.join(root, REVIEW_FILE)
    if not os.path.isfile(path):
        return rows
    for line in read(path).splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        if line.split("|")[1].strip().lower() == "spec":
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        spec = match.group(1).strip()
        if spec.startswith("specs/"):
            rows[spec] = (match.group(2).strip(), match.group(3).strip(),
                          match.group(4).strip(), line)
    return rows


def check(root: str = ".") -> list[str]:
    global PENDING, TOTAL_SPECS
    root = os.path.abspath(root)
    errors: list[str] = []
    specs = spec_files(root)
    rows = review_rows(root)
    if not rows:
        errors.append("%s: missing or empty, so the spec gate has no record"
                      % REVIEW_FILE.replace("\\", "/"))
    pending = []
    for spec in specs:
        row = rows.get(spec)
        if row is None:
            errors.append("%s: no row in %s" % (spec, REVIEW_FILE.replace("\\", "/")))
            continue
        status, reviewer, date = row[0], row[1], row[2]
        lowered = status.lower()
        if lowered in LIE_WORDS:
            errors.append("%s: status %r is not a verdict, use confirmed or rewritten" % (spec, status))
            pending.append(spec)
        elif lowered in PASS_WORDS:
            if not reviewer or reviewer == "-" or not date or date == "-":
                errors.append("%s: says %r with no reviewer or no date recorded" % (spec, status))
        else:
            pending.append(spec)

    print("check_spec_review: %d specs, %d still awaiting a clean-room reviewer, %d problem(s)"
          % (len(specs), len(pending), len(errors)))
    TOTAL_SPECS, PENDING = len(specs), len(pending)
    for spec in pending:
        print("PENDING spec review: %s" % spec)
    return errors


PENDING = 0
TOTAL_SPECS = 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 while any spec is still pending, for an implementation gate")
    args = parser.parse_args(argv)

    errors = check(args.root)
    if errors:
        for line in errors[:40]:
            print("FAIL " + line)
        if len(errors) > 40:
            print("... and %d more" % (len(errors) - 40))
        print("\n%d spec review problem(s)" % len(errors))
        return 1
    if PENDING:
        if args.strict:
            print("check_spec_review: STRICT REFUSED, %d of %d specs have no clean-room verdict yet"
                  % (PENDING, TOTAL_SPECS))
            return 1
        print("check_spec_review: no malformed row, but %d of %d specs still await a clean-room verdict"
              % (PENDING, TOTAL_SPECS))
        return 0
    print("check_spec_review: every spec has a named reviewer's clean-room verdict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
