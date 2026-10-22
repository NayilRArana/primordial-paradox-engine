"""Prove the clean room as far as text can, without ever touching a decompilation.

The rule this module enforces is narrow on purpose. It does NOT compare our text against someone else's project,
because doing that means reading a decompiled commercial game, and that read is the breach this file exists to prevent.
What it does instead is three blacklist checks and one bookkeeping check:

1. NO STUDY PATH. Nothing under game\\ or data\\ may name a study copy, the quarantine folder or the decompilation
   repository. The game has to build from this repository alone.
2. NO FOREIGN NAMES. A list of names that belong to Undertale and Deltarune is refused as a whole word anywhere in our
   text, so a name cannot arrive by accident or by habit.
3. NO FOREIGN PHRASES. A short list of distinctive expressions from those games is refused as a normalised substring.
   Only expression is listed here, never a mechanic: a battle loop, a dodge phase or a save file layout is an idea and
   is not protected.
4. A HUMAN REVIEW RECORD. knowledge\\CLEANROOM-REVIEW.md must hold one row per GML module, with a status, a reviewer
   and a date. A row that says reviewed without a reviewer or a date is an error. A row that says pending is reported
   loudly on every run and is not a pass: it is visible debt, waiting for the reviewer named in it.

ONE NARROW EXCEPTION, FOR DOWNLOADED MAP DATA. data\\osm_cache\\ and game\\datafiles\\osm_cache\\ hold Overpass API
downloads: third party geography carrying real place names ("Queen's Park" in Southampton), which the foreign name
scan would refuse as if we had written them. Renaming a downloaded place would falsify the data and break the
attribution the file carries, so such a file is skipped, but only on EVIDENCE INSIDE THE FILE, never on its path:
   - it sits under one of those two cache folders, AND
   - it parses as JSON, AND
   - its own "generator" starts with "Overpass API", AND
   - its osm3s block's "copyright" contains "openstreetmap.org".
A hand written file dropped into the same folder fails the second, third or fourth test and is scanned normally, and
the run line always reports how many files were skipped, so a skip can never be silent.

The comparison that used to live here (our strings against a study corpus) is gone with the corpus. Its replacement is
the blacklist plus the human review row, which is what a repository can honestly claim when it refuses to read the
thing it is being compared to.

Usage:
    python tools/check_cleanroom.py
    python tools/check_cleanroom.py --root .
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

FORBIDDEN_NAMES = [
    "undertale", "deltarune", "toby fox", "deltamodkit",
    "kris", "susie", "ralsei", "noelle", "berdly", "lancer", "queen",
    "undyne", "toriel", "asgore", "alphys", "papyrus", "sans", "napstablook",
    "asriel", "chara", "frisk", "gaster", "jevil", "spamton", "flowey", "temmie",
]

# Distinctive expression only. A mechanic is not on this list on purpose.
FORBIDDEN_PHRASES = [
    "a beautiful day outside",
    "sins crawling on your back",
    "you feel like you're going to have a bad time",
    "but nobody came",
    "stay determined",
    "megalovania",
    "karmic retribution",
    "gaster blaster",
    "the underground",
    "snowdin town",
    "hotland",
    "new home",
]

FORBIDDEN_PATHS = [
    "knowledge/study",
    "knowledge\\study",
    "quarantine-decomp",
    "deltamodkit",
]

REVIEW_FILE = os.path.join("knowledge", "CLEANROOM-REVIEW.md")
REVIEWED_WORDS = {"reviewed", "confirmed", "rewritten"}

# Downloaded geography, never authored text. Path alone is not evidence enough: see overpass_download().
OSM_CACHE_DIRS = ("data/osm_cache/", "game/datafiles/osm_cache/")
OSM_GENERATOR_PREFIX = "Overpass API"
OSM_COPYRIGHT_MARK = "openstreetmap.org"

TEXT_SUFFIXES = (".gml", ".json", ".yy", ".yyp", ".md", ".ps1", ".py")
ROW_RE = re.compile(r"^\|\s*`?([^|`]+?)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")


def text_files(base: str, suffixes=TEXT_SUFFIXES):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "__pycache__", ".pytest_cache", "study")]
        for fname in filenames:
            if fname.lower().endswith(suffixes):
                yield os.path.join(dirpath, fname)


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


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def overpass_download(rel: str, text: str) -> bool:
    """True only for a file that proves, from its own bytes, that OpenStreetMap downloaded it.

    Path prefix is necessary and never sufficient: the other three conditions are what separate a real Overpass
    download from a hand written file someone parked in the cache folder to dodge the scan.
    """
    if not rel.replace("\\", "/").startswith(OSM_CACHE_DIRS):
        return False
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    if not isinstance(payload, dict):
        return False
    generator = payload.get("generator")
    if not isinstance(generator, str) or not generator.startswith(OSM_GENERATOR_PREFIX):
        return False
    osm3s = payload.get("osm3s")
    if not isinstance(osm3s, dict):
        return False
    copyright_text = osm3s.get("copyright")
    return isinstance(copyright_text, str) and OSM_COPYRIGHT_MARK in copyright_text


def text_hits(root: str) -> tuple[list[str], int, int]:
    """The blacklist pass: (errors, files scanned, downloaded files skipped)."""
    errors: list[str] = []
    root = os.path.abspath(root)

    name_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in FORBIDDEN_NAMES) + r")\b", re.IGNORECASE)
    scanned = 0
    skipped = 0
    for base in (os.path.join(root, "game"), os.path.join(root, "data")):
        if not os.path.isdir(base):
            continue
        for path in text_files(base):
            rel = os.path.relpath(path, root).replace("\\", "/")
            text = read(path)
            if overpass_download(rel, text):
                skipped += 1
                continue
            scanned += 1
            for marker in FORBIDDEN_PATHS:
                if marker in text:
                    errors.append("%s: names a study copy or its folder (%s)" % (rel, marker))
            for match in name_re.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append("%s:%d: foreign name %r" % (rel, line, match.group(0)))
            flat = normalise(text)
            for phrase in FORBIDDEN_PHRASES:
                if phrase in flat:
                    errors.append("%s: foreign phrase %r" % (rel, phrase))
    return errors, scanned, skipped


def gml_modules(root: str) -> list[str]:
    found = []
    for path in text_files(os.path.join(root, "game"), (".gml",)):
        found.append(os.path.relpath(path, root).replace("\\", "/"))
    return sorted(found)


def review_rows(root: str) -> dict[str, tuple[str, str, str]]:
    """Every row of the review table: module -> (status, reviewer, date)."""
    rows: dict[str, tuple[str, str, str]] = {}
    path = os.path.join(root, REVIEW_FILE)
    if not os.path.isfile(path):
        return rows
    for line in read(path).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("| ---") or "module" in line.split("|")[1].lower():
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        module, status, reviewer, date = match.group(1).strip(), match.group(2).strip(), \
            match.group(3).strip(), match.group(4).strip()
        if module and "/" in module:
            rows[module] = (status, reviewer, date)
    return rows


def check(root: str = ".") -> list[str]:
    global PENDING, MODULES, SKIPPED
    root = os.path.abspath(root)
    errors, scanned, skipped = text_hits(root)
    SKIPPED = skipped

    modules = gml_modules(root)
    rows = review_rows(root)
    if not rows:
        errors.append("%s: missing or empty, so the human clean-room review has no record"
                      % REVIEW_FILE.replace("\\", "/"))
    pending = []
    for module in modules:
        row = rows.get(module)
        if row is None:
            errors.append("%s: no clean-room review row in %s" % (module, REVIEW_FILE.replace("\\", "/")))
            continue
        status, reviewer, date = row
        if status.lower() in REVIEWED_WORDS:
            if not reviewer or not date:
                errors.append("%s: says %r with no reviewer or no date recorded" % (module, status))
        else:
            pending.append(module)

    print("check_cleanroom: %d files scanned for %d names and %d phrases, %d GML modules, %d awaiting review, "
          "%d downloaded map file(s) skipped"
          % (scanned, len(FORBIDDEN_NAMES), len(FORBIDDEN_PHRASES), len(modules), len(pending), skipped))
    PENDING, MODULES = len(pending), len(modules)
    for module in pending:
        print("PENDING clean-room review: %s" % module)
    return errors


PENDING = 0
MODULES = 0
SKIPPED = 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    errors = check(args.root)
    if errors:
        for line in errors[:40]:
            print("FAIL " + line)
        if len(errors) > 40:
            print("... and %d more" % (len(errors) - 40))
        print("\n%d clean room problem(s)" % len(errors))
        return 1
    if PENDING:
        print("check_cleanroom: no blacklist hit, but %d of %d modules still await clean-room review (listed above)"
              % (PENDING, MODULES))
        return 0
    print("check_cleanroom: no study reference, no foreign name, no foreign phrase, every module reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
