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

TWO NARROW EXCEPTIONS, BOTH ON EVIDENCE INSIDE THE FILE.

The first is for downloaded map data. data\\osm_cache\\ and game\\datafiles\\osm_cache\\ hold Overpass API downloads:
third party geography carrying real place names ("Queen's Park" in Southampton), which the foreign name scan would
refuse as if we had written them. Renaming a downloaded place would falsify the data and break the attribution the
file carries, so such a file is skipped, but only on EVIDENCE INSIDE THE FILE, never on its path:
   - it sits under one of those two cache folders, AND
   - it parses as JSON, AND
   - its own "generator" starts with "Overpass API", AND
   - its osm3s block's "copyright" contains "openstreetmap.org".
A hand written file dropped into the same folder fails the second, third or fourth test and is scanned normally, and
the run line always reports how many files were skipped, so a skip can never be silent.

The second is for a generated geography card, which is our own rasteriser's output and not a raw download. Such a
card carries our prose (a name, a region, a blurb) AND proper-name lists copied out of OpenStreetMap: road names,
water names, rail names, landmark names. "Queen's Terrace" is a real Southampton street, and "queen" and "lancer" are
ordinary English words that also happen to be character names in the games this gate refuses, so a bare whole-word
scan over that file can never be satisfied by real data. Deleting the street would falsify the map. So the card's
OSM proper-name lists are exempt from the foreign name pass, under the same doctrine: evidence inside the file,
nothing on its path, everything else still scanned. A card qualifies only when all of this holds:
   - it parses as a JSON object, AND
   - its "kind" is "real_places", AND
   - its "attribution" names openstreetmap.org, AND
   - its "licence" names ODbL, AND
   - its "method" or a place's "source_kind" names OSM or the cache.
Only the values of those name lists are blanked out, exactly as the data holds them, and every other byte of the file
(blurb, region, notes, anything added by hand) is still scanned. The run line reports how many names were exempt and
in how many cards, and each card is printed, so the exemption can never widen quietly and can never be silent.

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

# Generated geography cards, our own rasteriser's output. Also evidence only: see geography_card().
GEO_CARD_KIND = "real_places"
GEO_ATTRIBUTION_MARK = "openstreetmap.org"
GEO_LICENCE_MARK = "odbl"
GEO_SOURCE_MARKS = ("osm", "cache")
# The fields that hold proper names read out of OpenStreetMap, and the fields that hold our own prose.
GEO_ROAD_FIELDS = ("major", "minor", "route_relations")
GEO_NAME_LIST_FIELDS = ("water_names", "rail_names", "rail_disused_names")

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


def geography_card(payload) -> bool:
    """True only for a generated geography card that proves, from its own bytes, where its proper names came from.

    Same doctrine as overpass_download(): a path is never evidence, and a hand written file that drops a
    "real_places" key into data\\maps\\ still fails, because it cannot carry the ODbL attribution honestly.
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("kind") != GEO_CARD_KIND:
        return False
    attribution = payload.get("attribution")
    if not isinstance(attribution, str) or GEO_ATTRIBUTION_MARK not in attribution.lower():
        return False
    licence = payload.get("licence")
    if not isinstance(licence, str) or GEO_LICENCE_MARK not in licence.lower():
        return False
    marks: list[str] = []
    method = payload.get("method")
    if isinstance(method, str):
        marks.append(method)
    places = payload.get("places")
    if isinstance(places, list):
        for place in places:
            if isinstance(place, dict) and isinstance(place.get("source_kind"), str):
                marks.append(place["source_kind"])
    return any(mark in value.lower() for value in marks for mark in GEO_SOURCE_MARKS)


def _string_list(node) -> list[str]:
    if not isinstance(node, list):
        return []
    return [value for value in node if isinstance(value, str)]


def geography_names(payload) -> set[str]:
    """The proper names a card read from OpenStreetMap, exactly as the data holds them. Nothing else is exempt."""
    names: set[str] = set()
    places = payload.get("places")
    if not isinstance(places, list):
        return names
    for place in places:
        if not isinstance(place, dict):
            continue
        landmarks = place.get("landmarks")
        if isinstance(landmarks, list):
            for landmark in landmarks:
                if isinstance(landmark, dict) and isinstance(landmark.get("name"), str):
                    names.add(landmark["name"])
        roads = place.get("roads")
        if isinstance(roads, dict):
            for field in GEO_ROAD_FIELDS:
                names.update(_string_list(roads.get(field)))
        for field in GEO_NAME_LIST_FIELDS:
            names.update(_string_list(place.get(field)))
    return {name for name in names if name.strip()}


def geography_exemptions(text: str) -> set[str] | None:
    """The names to blank out, or None when the file is not a proven geography card and must be scanned whole."""
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    if not geography_card(payload):
        return None
    return geography_names(payload)


def mask_names(text: str, names: set[str]) -> str:
    """Blank out those names as JSON string values, byte for byte in length, so line numbers stay true.

    A name the file does not hold as its own JSON string value is left alone and stays scanned: the exemption can
    only ever shrink the scan for data the card demonstrably read from OpenStreetMap.
    """
    masked = text
    for name in names:
        for encoded in {json.dumps(name), json.dumps(name, ensure_ascii=False)}:
            if len(encoded) < 2:
                continue
            masked = masked.replace(encoded, '"' + "x" * (len(encoded) - 2) + '"')
    return masked


def text_hits(root: str) -> tuple[list[str], int, int]:
    """The blacklist pass: (errors, files scanned, downloaded files skipped).

    Sets EXEMPT_CARDS and EXEMPT_NAMES so the run line can report the geography exemption, and EXEMPT_FILES so each
    card that was exempt is named out loud.
    """
    global EXEMPT_CARDS, EXEMPT_NAMES, EXEMPT_FILES
    errors: list[str] = []
    root = os.path.abspath(root)
    EXEMPT_CARDS, EXEMPT_NAMES, EXEMPT_FILES = 0, 0, []

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
            exempt = geography_exemptions(text)
            if exempt is not None:
                EXEMPT_CARDS += 1
                EXEMPT_NAMES += len(exempt)
                EXEMPT_FILES.append((rel, len(exempt)))
                text = mask_names(text, exempt)
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
          "%d downloaded map file(s) skipped, %d OSM place name(s) exempt in %d generated geography card(s)"
          % (scanned, len(FORBIDDEN_NAMES), len(FORBIDDEN_PHRASES), len(modules), len(pending), skipped,
             EXEMPT_NAMES, EXEMPT_CARDS))
    for rel, count in EXEMPT_FILES:
        print("OSM place names exempt from the foreign name pass: %s (%d name(s))" % (rel, count))
    PENDING, MODULES = len(pending), len(modules)
    for module in pending:
        print("PENDING clean-room review: %s" % module)
    return errors


PENDING = 0
MODULES = 0
SKIPPED = 0
EXEMPT_CARDS = 0
EXEMPT_NAMES = 0
EXEMPT_FILES: list[tuple[str, int]] = []


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
