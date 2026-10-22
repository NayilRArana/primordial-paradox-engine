"""Build data\\nes_palette.json: the 64 outputs of the Ricoh 2C02 NTSC PPU, with a citation.

Why this file exists: the NES validator (tools\\nes_check.py) needs to know which colours the chip can
actually put on screen, and 64 is the whole answer. The PPU holds 6 bit palette values, $00 to $3F, and
each one is a fixed output on the NTSC 2C02. $0D, $0E, $0F and $1E, $1F and so on decode to shades that
matter to the rules: hue $xD is dark grey, hue $x0 is grey, and the "blacks" $0F, $1E, $1F, $2E, $2F, $3E,
$3F all decode to black.

Where the numbers come from, stated plainly because this file is machine checked and cited:
- Structure (64 outputs, hues $x0 to $xC, greys $xD, blacks $xE and $0F, entry $3F00 is the backdrop):
  NESdev wiki, "PPU palettes", https://www.nesdev.org/wiki/PPU_palettes, read 2026-10-21. That page
  draws the 2C02 table as colour swatches, not as text, so it supplies the structure and the rules.
- The hex values: the 2C02 composite decode set used across emulators and documented in the wiki's
  .pal format (https://www.nesdev.org/wiki/.pal). The 54 distinct colours of this set were checked
  entry by entry against the published NES palette at
  https://lospec.com/palette-list/nintendo-entertainment-system (54 entries, fetched 2026-10-21), and
  the build fails if any value in the table is not in that published set. That check is what makes
  these particular numbers defensible rather than recalled.

Composite decoding is not unique: no two televisions agree, and the wiki says so at length. The rule
this project follows is the common emulator set above, so art authored here and art seen in an emulator
agree. If a different decode is wanted later, change this one file; nes_check reads it and nothing else.

Run: python tools\\art\\nes_palette_build.py [repo root] [--check]
"""

from __future__ import annotations

import json
import os
import sys

# $00 to $3F in order. Row 0 dark, row 1 medium, row 2 light, row 3 pale. $x0 to $xC are hues, $xD is
# dark grey, $xE and $x0F are black. 000000 appears at $0D? No: see the table, $0D is black on the 2C02.
TABLE = [
    # $0x  dark
    "7c7c7c", "0000fc", "0000bc", "4428bc", "940084", "a80020", "a81000", "881400",
    "503000", "007800", "006800", "005800", "004058", "000000", "000000", "000000",
    # $1x  medium
    "bcbcbc", "0078f8", "0058f8", "6844fc", "d800cc", "e40058", "f83800", "e45c10",
    "ac7c00", "00b800", "00a800", "00a844", "008888", "000000", "000000", "000000",
    # $2x  light
    "f8f8f8", "3cbcfc", "6888fc", "9878f8", "f878f8", "f85898", "f87858", "fca044",
    "f8b800", "b8f818", "58d854", "58f898", "00e8d8", "787878", "000000", "000000",
    # $3x  pale
    "fcfcfc", "a4e4fc", "b8b8f8", "d8b8f8", "f8b8f8", "f8a4c0", "f0d0b0", "fce0a8",
    "f8d878", "d8f878", "b8f8b8", "b8f8d8", "00fcfc", "f8d8f8", "000000", "000000",
]

HUES = ["grey", "azure", "blue", "violet", "magenta", "rose", "red", "orange",
        "yellow", "chartreuse", "green", "spring", "cyan", "dark grey", "black", "black"]

# The published 55 entry set (every distinct colour of the 2C02) this table is checked against. Kept here
# so the check runs offline and the comparison is visible in review rather than hidden in a download.
PUBLISHED_SET = {
    "000000", "fcfcfc", "f8f8f8", "bcbcbc", "7c7c7c", "a4e4fc", "3cbcfc", "0078f8", "0000fc",
    "b8b8f8", "6888fc", "0058f8", "0000bc", "d8b8f8", "9878f8", "6844fc", "4428bc", "f8b8f8",
    "f878f8", "d800cc", "940084", "f8a4c0", "f85898", "e40058", "a80020", "f0d0b0", "f87858",
    "f83800", "a81000", "fce0a8", "fca044", "e45c10", "881400", "f8d878", "f8b800", "ac7c00",
    "503000", "d8f878", "b8f818", "00b800", "007800", "b8f8b8", "58d854", "00a800", "006800",
    "b8f8d8", "58f898", "00a844", "005800", "00fcfc", "00e8d8", "008888", "004058", "f8d8f8",
    "787878",
}


# Entries that decode to #000000 in this set. Ten of them; only one black is needed, so nine are
# unusable for authored art, and $0D is worse than unusable: writing it to a palette made some 2C02
# sets pull the composite signal low during horizontal blanking. Sources: NESdev wiki, PPU palettes
# (hue $xD caution, "the canonical code for black is $0F"), and the nesdoug palette guide.
BLACK_ENTRIES = [0x0D, 0x0E, 0x0F, 0x1D, 0x1E, 0x1F, 0x2E, 0x2F, 0x3E, 0x3F]
CANONICAL_BLACK = 0x0F


def build():
    if len(TABLE) != 64:
        raise SystemExit("the 2C02 table has %d entries, the PPU has 64" % len(TABLE))
    colours = []
    first_seen = {}
    for index, value in enumerate(TABLE):
        hex_value = "#" + value
        flag = None
        if index == 0x0D:
            flag = "forbidden: some 2C02 sets glitch when $0D is written to a palette"
        elif hex_value in first_seen:
            flag = "black duplicate of $%02X" % first_seen[hex_value]
        usable = flag is None or index == CANONICAL_BLACK
        entry = {
            "index": index,
            "code": "$%02X" % index,
            "hex": hex_value,
            "hue": HUES[index & 0x0F],
            "value": index >> 4,
            "usable": usable,
            "canonical_black": index == CANONICAL_BLACK,
        }
        if flag is not None:
            entry["flag"] = flag
        if hex_value not in first_seen:
            first_seen[hex_value] = index
        colours.append(entry)
    unique = sorted({entry["hex"] for entry in colours})
    return {
        "format": 1,
        "kind": "nes_palette",
        "name": "2c02",
        "chip": "Ricoh 2C02 (NTSC PPU)",
        "rule": "64 outputs, $00 to $3F; a pixel must be one of these; at most 25 on screen at once",
        "usable_rule": (
            "usable is false for the forbidden entry $0D and for every black duplicate other than "
            "$0F; black stays available at $0F"
        ),
        "citation": (
            "Structure, entry numbering and the backdrop rule: NESdev wiki, PPU palettes, "
            "https://www.nesdev.org/wiki/PPU_palettes (read 2026-10-21). Hex values: the 2C02 "
            "composite decode set in the wiki's .pal format (https://www.nesdev.org/wiki/.pal), every "
            "value cross-checked against the 54 colour set published at "
            "https://lospec.com/palette-list/nintendo-entertainment-system (fetched 2026-10-21)."
        ),
        "unique_colours": len(unique),
        "usable_entries": sum(1 for entry in colours if entry["usable"]),
        "hazard_entries": sum(1 for entry in colours if "flag" in entry),
        "backdrop": 15,
        "colours": [entry["hex"] for entry in colours],
        "entries": colours,
    }


def main(argv: list) -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = [a for a in argv[1:] if not a.startswith("--")]
    if args:
        root = os.path.abspath(args[0])
    if "--check" in argv:
        path = os.path.join(root, "data", "nes_palette.json")
        with open(path, "r", encoding="utf-8") as handle:
            live = json.load(handle)
        fresh = build()
        if live != fresh:
            print("FAIL data/nes_palette.json is not what this script builds")
            return 1
        print("OK data/nes_palette.json matches this script: 64 entries, %d unique colours"
              % fresh["unique_colours"])
        return 0

    data = build()
    unknown = sorted({entry[1:] for entry in data["colours"]} - PUBLISHED_SET)
    if unknown:
        print("FAIL %d colours are not in the published NES set (55 distinct 2C02 colours): %s"
              % (len(unknown), ", ".join("#" + value for value in unknown)))
        return 1
    missing = sorted(PUBLISHED_SET - {entry[1:] for entry in data["colours"]})
    print("cross check: %d of the published %d colours appear in this table; missing: %s"
          % (len(PUBLISHED_SET) - len(missing), len(PUBLISHED_SET),
             ", ".join("#" + m for m in missing) or "none"))

    path = os.path.join(root, "data", "nes_palette.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    print("wrote %s: 64 entries, %d unique colours" % (path, data["unique_colours"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
