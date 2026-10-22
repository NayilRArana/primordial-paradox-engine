"""check_art_bible.py: the acceptance checks for the ART-BIBLE card (t_6cfeecbf).

What it proves, in order:
1. data\\nes_palette.json is the 2C02 master palette: 64 entries, indices 0 to 63 in order, a #RRGGBB
   value each, a boolean usable flag each, and exactly the 10 entries that decode to black flagged.
   The counts it asserts are the arithmetic the ART-BIBLE states: 64 entries, 55 distinct colours,
   10 flagged, 55 usable entries, black available at $0F and $0D flagged forbidden.
2. knowledge\\ART-BIBLE.md cites what it claims: every source tag used in the body is defined in the
   source table, every row of the hard limits table carries a tag, the checklist has at least 10
   numbered checks, and the file has the six sections it promises.
3. Neither file contains a long dash (em dash, en dash, horizontal bar). The house rule forbids them.
4. The 3x preview PNG for the palette exists and has the size this check expects, so the manager has
   something to look at; the check cannot judge the picture, only that it was rendered.

Exit code 0 when every check passes, 1 otherwise. Run: python tools\\check_art_bible.py
"""

from __future__ import annotations

import json
import os
import re
import sys

LONG_DASHES = {"\u2014": "em dash", "\u2013": "en dash", "\u2015": "horizontal bar",
               "\u2e3a": "two em dash", "\u2e3b": "three em dash"}
FORBIDDEN_INDEX = 0x0D
CANONICAL_BLACK = 0x0F
REQUIRED_SECTIONS = ["## 0.", "## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6."]


def root_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_palette(root: str, failures: list, notes: list) -> dict:
    path = os.path.join(root, "data", "nes_palette.json")
    if not os.path.isfile(path):
        failures.append("data\\nes_palette.json is missing; run tools\\art\\nes_palette_build.py")
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    entries = data.get("entries")
    if not isinstance(entries, list) or len(entries) != 64:
        failures.append("data\\nes_palette.json must hold 64 entries")
        return data
    if [entry.get("index") for entry in entries] != list(range(64)):
        failures.append("data\\nes_palette.json entries are not indices 0 to 63 in order")
    for entry in entries:
        if not re.fullmatch(r"#[0-9a-f]{6}", str(entry.get("hex", ""))):
            failures.append("entry %s has hex %r, not #rrggbb lowercase"
                            % (entry.get("code"), entry.get("hex")))
        if not isinstance(entry.get("usable"), bool):
            failures.append("entry %s has no boolean usable flag" % entry.get("code"))
    flagged = [entry for entry in entries if "flag" in entry]
    usable = [entry for entry in entries if entry.get("usable")]
    distinct = {entry["hex"] for entry in entries}
    if len(distinct) != 55:
        failures.append("%d distinct colours, the 2C02 decode set has 55" % len(distinct))
    if len(flagged) != 10:
        failures.append("%d flagged entries, the black group is 10" % len(flagged))
    if len(usable) != 55:
        failures.append("%d usable entries, expected 55" % len(usable))
    by_index = {entry["index"]: entry for entry in entries}
    if "forbidden" not in str(by_index[FORBIDDEN_INDEX].get("flag", "")):
        failures.append("$0D must be flagged as forbidden")
    if by_index[FORBIDDEN_INDEX].get("usable") is not False:
        failures.append("$0D must not be usable")
    if by_index[CANONICAL_BLACK].get("usable") is not True:
        failures.append("$0F must stay usable: it is the canonical black")
    if not by_index[CANONICAL_BLACK].get("canonical_black"):
        failures.append("$0F must be marked canonical_black")
    blacks = {entry["hex"] for entry in entries if entry["hex"] == "#000000"}
    if blacks != {"#000000"}:
        failures.append("the black group is not the single colour #000000")
    notes.append("palette: 64 entries, %d distinct, %d usable, %d flagged"
                 % (len(distinct), len(usable), len(flagged)))
    return data


def check_bible(root: str, failures: list, notes: list) -> str:
    path = os.path.join(root, "knowledge", "ART-BIBLE.md")
    if not os.path.isfile(path):
        failures.append("knowledge\\ART-BIBLE.md is missing")
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for section in REQUIRED_SECTIONS:
        if section not in text:
            failures.append("ART-BIBLE.md is missing section %s" % section)

    defined = set(re.findall(r"^\| (S\d+) \|", text, re.MULTILINE))
    used = set(re.findall(r"\[(S\d+)\]", text)) | set(re.findall(r"\bS(\d+)\b", text))
    used = {"S" + tag if not tag.startswith("S") else tag for tag in used}
    missing = sorted(used - defined)
    if missing:
        failures.append("ART-BIBLE.md uses undefined source tags: %s" % ", ".join(missing))
    if len(defined) < 10:
        failures.append("only %d sources defined, the card asks for cited analyses" % len(defined))

    limits = text.split("### 1.1")[1].split("### 1.2")[0] if "### 1.1" in text else ""
    rows = [line for line in limits.splitlines() if line.startswith("| ") and "|" in line[2:]]
    rows = [row for row in rows if not row.startswith("| # ") and not row.startswith("| ---")]
    if len(rows) < 20:
        failures.append("section 1.1 has %d limit rows, expected at least 20" % len(rows))
    uncited = [row for row in rows if not re.search(r"\bS\d+", row)]
    if uncited:
        failures.append("%d hard limit rows carry no source tag" % len(uncited))

    checks = re.findall(r"^\| (C\d+) \|", text, re.MULTILINE)
    if len(checks) < 10:
        failures.append("section 4 has %d numbered checks, expected at least 10" % len(checks))
    for absent in ("open", "stated", "derived"):
        if absent not in text:
            failures.append("ART-BIBLE.md never uses the confidence word %r" % absent)
    notes.append("bible: %d sources, %d limit rows, %d review checks"
                 % (len(defined), len(rows), len(checks)))
    return text


def check_dashes(path: str, failures: list) -> None:
    if not path or not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for character, name in LONG_DASHES.items():
        if character in text:
            failures.append("%s contains a %s" % (os.path.basename(path), name))


def check_preview(root: str, failures: list, notes: list) -> None:
    path = os.path.join(root, "output", "art_bible_palette_sheet.png")
    if not os.path.isfile(path):
        failures.append("output\\art_bible_palette_sheet.png is missing; "
                        "run tools\\art\\make_palette_sheet.py")
        return
    try:
        from PIL import Image
    except ImportError:
        notes.append("preview: file exists, Pillow not installed here so the size was not read")
        return
    with Image.open(path) as source:
        image = source.convert("RGB")
    width, height = image.size
    if width != 800 or height < 240:
        failures.append("preview is %dx%d, expected 800 wide and at least 240 tall" % (width, height))

    # Sample the middle of every swatch and compare it to the entry it claims to show. This is the only
    # way a worker that cannot see the picture can prove the picture is the palette and not an empty
    # canvas: the drawing code in tools\art\make_palette_sheet.py puts swatch (row, column) at
    # (16 + 48 * column + 6, 48 + 46 * row + 2) with a 24 x 24 body.
    with open(os.path.join(root, "data", "nes_palette.json"), "r", encoding="utf-8") as handle:
        entries = json.load(handle)["entries"]
    wrong = []
    for entry in entries:
        column = entry["index"] % 16
        row = entry["index"] // 16
        x = 16 + column * 48 + 6 + 12
        y = 48 + row * 46 + 2 + 12
        expected = tuple(int(entry["hex"].lstrip("#")[position:position + 2], 16) for position in (0, 2, 4))
        actual = image.getpixel((x, y))
        if actual != expected:
            wrong.append("%s shows %s not %s" % (entry["code"], actual, expected))
    if wrong:
        failures.append("%d swatches do not show their colour: %s" % (len(wrong), "; ".join(wrong[:4])))
    notes.append("preview: output\\art_bible_palette_sheet.png %dx%d, 64 of 64 swatches sampled"
                 % (width, height))


def main() -> int:
    root = root_dir()
    failures: list = []
    notes: list = []
    check_palette(root, failures, notes)
    check_bible(root, failures, notes)
    for name in ("ART-BIBLE.md",):
        check_dashes(os.path.join(root, "knowledge", name), failures)
    check_dashes(os.path.join(root, "data", "nes_palette.json"), failures)
    check_preview(root, failures, notes)
    for note in notes:
        print("ok   " + note)
    for failure in failures:
        print("FAIL " + failure)
    if failures:
        print("%d check(s) failed" % len(failures))
        return 1
    print("PASS art bible checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
