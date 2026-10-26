#!/usr/bin/env python3
"""scene_palette_set.py: the palette set every scene starts from, written down before any art is made.

Why this exists
---------------
ART-BIBLE.md RULE 0 (Nayil, 2026-10-22): concept art, backgrounds and sprites are designed INSIDE the NES
palette system, never converted into it afterwards. So a scene starts from a palette set, and the set is a
fact of the scene before a single pixel is drawn:

    data\\scene_palettes.json     every scene: 1 backdrop, 4 background palettes of 3, 4 sprite palettes of 3
                                 plus the 4 reserved hero palettes

This module is the loader and the validator for that file. It does not restate the palette arithmetic: the
2C02 master palette, the entry lookup, the nearest-entry search and the `Scene` object all come from
tools\\art\\scene_palette.py, which is the art lane's single authority for which palette is which. What this
module adds is the one thing that file does not hold: one place where ALL scenes and the fixed hero palettes
are visible together, so a concept art prompt can name them and tools\\palette_synergy.py can reject art that
does not use them.

The hero palettes are fixed by RULE 0 point 3 and are the only entries in the file that are not derived from
a scene: Percy blue and gold, Hadrian near black and purple, Zander light blue, Konrad grey and amber. Each
is 3 colours: 1 dark outline, 1 mid body, 1 accent. Gamedev owns the palette decisions, so a hero colour is
changed by editing this file and nothing else; every tool reads it from here.

Usage:
    python tools\\scene_palette_set.py build            # print the set derived from data\\palettes\\scene_*.json
    python tools\\scene_palette_set.py build --write    # write data\\scene_palettes.json
    python tools\\scene_palette_set.py validate          # exit 1 on any rule break
    python tools\\scene_palette_set.py list
    python tools\\scene_palette_set.py show --scene title
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))

import scene_palette  # noqa: E402  (the master palette and the Scene object, reused and not rewritten)

DATA_FILE = os.path.join("data", "scene_palettes.json")
PALETTE_DIR = os.path.join("data", "palettes")
HEROES = ("percy", "hadrian", "zander", "konrad")

RULE = ("one backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, 4 sprite "
        "palettes of 3 entries plus transparency on 8x8 tiles, and 4 reserved hero palettes of 3; every entry "
        "is a data/nes_palette.json entry number, every entry usable")

# RULE 0 point 3, as entry numbers. outline first (dark), then body (mid), then accent, which is the order
# contrast_check.py and palette_synergy.py both read a palette in.
HERO_PALETTES = {
    "percy": {
        "colours": [15, 18, 40],
        "hue": "blue and gold",
        "note": "Percy: $0F outline, $12 blue body, $28 gold accent. The reserved hero blue: no enemy uses $12.",
    },
    "hadrian": {
        "colours": [15, 3, 35],
        "hue": "near black and purple",
        "note": "Hadrian: $0F outline, $03 dark violet body, $23 light violet accent.",
    },
    "zander": {
        "colours": [15, 33, 49],
        "hue": "light blue",
        "note": "Zander: $0F outline, $21 light blue body, $31 pale blue accent. Reads pale, so never on a pale ground.",
    },
    "konrad": {
        "colours": [15, 0, 39],
        "hue": "grey and amber",
        "note": "Konrad: $0F outline, $00 grey body, $27 amber accent.",
    },
}

HERO_ROLES = ("outline", "body", "accent")

# The rows tools/palette_synergy.py checks on every gate run (--gate) are NOT written here any more.
#
# They lived in this module as a hand constant until card t_4f18c0ac, and that is where the deck's row went stale:
# a card re-solved the deck's four sprite palettes for the fight cast, the row still named the walking sailor, and
# because the row and the scene file are two different files nothing failed. Every draw round then measured the
# same 16 failures on the difference. A cast now lives in the scene file that solved it, as a "judged" list, and
# validate() measures it against the set in the same file: see JUDGED_KEY below.
JUDGED_KEY = "judged"
JUDGED_FIELDS = ("background", "sprites")

# Card t_c93a983f. On a scene that draws the party (the four battle strips) the four RESERVED HERO PALETTES ARE
# its four sprite palettes, so they REPLACE the scene's own four rows instead of adding to them: ruling 7.1 of
# knowledge/PALETTE-RULINGS-2026-10-25.md, because the PPU picks a sprite palette with two attribute bits and a
# frame therefore has four of them and nowhere to put a fifth. A per scene flag in the DERIVED file rather than
# a global change, because the towns, the ship, the title, the icons, the sea and the ui scene carry their own
# four sprite rows today and that behaviour is correct.
#
# The declaration lives HERE and not in data/palettes/scene_battle_*.json because tools/art/make_battle_bg.py
# writes those four files whole and emits neither `judged` nor this key (read at HEAD 2026-10-25), and the copy
# added to the files earlier that morning did not survive the next working session: anything the generator does
# not itself write is one regeneration away from disappearing. The wiring is per scene all the same: build()
# emits party_cast into data/scene_palettes.json and every checker reads that, so a fifth battle strip is one
# line here and no change anywhere else.
PARTY_CAST_KEY = "party_cast"
PARTY_CAST_SCENES = ("battle_corridor", "battle_deck_night", "battle_quay_dusk", "battle_wardroom")
# A judged row whose file is a BY-PRODUCT: gitignored, and written differently by two generators, so a clean
# checkout cannot reproduce it. The row is reported NOT MEASURED instead of refusing the whole run (ruling
# section 8; three Pine jobs refused on output/sprites_v2_sheet.png before this flag existed).
BY_PRODUCT_KEY = "by_product"


# -----------------------------------------------------------------------------------------------------------------
# Loading.

def repo_root() -> str:
    return ROOT


def data_path(root: str = ROOT) -> str:
    return os.path.join(root, DATA_FILE)


def load_master(root: str = ROOT):
    """(colours, usable, index_of) from tools/art/scene_palette.py, so there is one master palette reader."""
    return scene_palette.load_master(root)


def load(root: str = ROOT) -> dict:
    """The file as written. A missing file is an error, not an empty set: a scene with no palette set is the
    bug RULE 0 exists to stop."""
    path = data_path(root)
    if not os.path.isfile(path):
        raise SystemExit("scene_palette_set: %s is missing. Run: python tools\\scene_palette_set.py build --write"
                         % os.path.relpath(path, root))
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def scene_ids(data: dict) -> list:
    return [scene["id"] for scene in data.get("scenes", [])]


def find_scene(data: dict, scene_id: str) -> dict:
    for scene in data.get("scenes", []):
        if scene["id"] == scene_id:
            return scene
    raise SystemExit("scene_palette_set: no scene %r in %s. Known: %s"
                     % (scene_id, DATA_FILE.replace(os.sep, "/"), ", ".join(sorted(scene_ids(data)))))


def scene_payload(entry: dict, sprites=None) -> dict:
    """The shape tools/art/scene_palette.py Scene reads: backdrop, background[4], sprites[4], scene name.

    `sprites` is the sprite half to write, as rows of name + colours; it defaults to the scene's OWN four rows,
    which is right for every scene that spends its own rows. Callers that must read the room rather than the
    declaration pass allowed_sprite_rows(), which is the hero four on a party_cast strip (card t_6e8ca42f).
    """
    rows = entry["sprites"] if sprites is None else sprites
    payload = {
        "scene": entry["id"],
        "backdrop": entry["backdrop"],
        "background": [{"name": row.get("name", "bg%d" % index), "colours": list(row["colours"])}
                       for index, row in enumerate(entry["background"])],
        "sprites": [{"name": row.get("name", "sp%d" % index), "colours": list(row["colours"])}
                    for index, row in enumerate(rows)],
    }
    return payload


def scene(root: str, scene_id: str) -> scene_palette.Scene:
    """A scene_palette.Scene for this scene, so callers reuse the enforcement arithmetic instead of copying it.

    The sprite half comes from allowed_sprite_rows(), not from the entry's own rows, because on a party_cast
    strip the four reserved hero palettes ARE the strip's four sprite palettes (ruling 7.1, card t_c93a983f).
    Reading the declaration there measured every repainted party sheet as needing a palette the chip cannot
    have, while the triple it draws with was the strip's own (card t_6e8ca42f). One assembly point, so a
    checker, a quantiser and a painter all read the same four.
    """
    data = load(root)
    entry = find_scene(data, scene_id)
    return scene_palette.Scene(scene_payload(entry, allowed_sprite_rows(data, scene_id)), root)


def hero(data: dict, name: str) -> dict:
    palettes = data.get("hero_palettes", {})
    if name not in palettes:
        raise SystemExit("scene_palette_set: no hero palette %r. Known: %s" % (name, ", ".join(sorted(palettes))))
    return palettes[name]


def hero_entries(data: dict) -> set:
    out = set()
    for palette in data.get("hero_palettes", {}).values():
        out.update(int(entry) for entry in palette["colours"])
    return out


def allowed_sprite_rows(data: dict, scene_id: str) -> list:
    """The sprite half of a scene as Scene rows (name + colours): FOUR rows, never eight (card t_c93a983f).

    A scene that declares party_cast (the four battle strips) is drawn with the four RESERVED HERO PALETTES as
    its four sprite palettes, so the hero triples are what a checker may approve on it and the scene's own
    declared rows are not added on top: ruling 7.1 of knowledge/PALETTE-RULINGS-2026-10-25.md, "on a battle strip
    the four reserved hero palettes ARE the strip's four sprite palettes". Every other scene spends its own four
    rows, which is how the towns, the ship, the title, the icons, the sea and the ui scene behave.

    This is the shape scene() assembles a Scene from (card t_6e8ca42f); allowed_sprite_sets() is the same rows
    with the names dropped, kept for the callers that only compare entry sets.
    """
    entry = find_scene(data, scene_id)
    if entry.get(PARTY_CAST_KEY):
        return [{"name": name, "colours": list(map(int, data["hero_palettes"][name]["colours"]))}
                for name in HEROES]
    return [{"name": row.get("name", "sp%d" % index), "colours": list(map(int, row["colours"]))}
            for index, row in enumerate(entry.get("sprites", []))]


def allowed_sprite_sets(data: dict, scene_id: str) -> list:
    """The entry sets of allowed_sprite_rows(): four triples of colour numbers."""
    return [row["colours"] for row in allowed_sprite_rows(data, scene_id)]


def scene_entries(data: dict, scene_id: str) -> set:
    """Every entry the scene may spend: the backdrop, the 4 background palettes, and the 4 sprite palettes.

    On a party_cast scene the sprite half is the hero four (allowed_sprite_sets), not its own rows plus the
    heroes: a checker that approved eight palettes would approve art no frame can draw (card t_c93a983f).
    """
    entry = find_scene(data, scene_id)
    out = {int(entry["backdrop"])}
    for row in entry["background"]:
        out.update(int(value) for value in row["colours"])
    for row in allowed_sprite_sets(data, scene_id):
        out.update(row)
    if entry.get("heroes", True) and not entry.get(PARTY_CAST_KEY):
        out.update(hero_entries(data))
    return out


# -----------------------------------------------------------------------------------------------------------------
# The 2C02 grid: 4 brightness rows by 16 hue columns (ART-BIBLE 1.3). Both numbers are read off the entry.

GREY_COLUMNS = (0, 13, 14, 15)   # $x0 grey, $xD dark grey, $xE and $xF black


def row_of(entry: int) -> int:
    """The brightness row, 0 dark to 3 pale."""
    return (int(entry) >> 4) & 0x03


def column_of(entry: int) -> int:
    return int(entry) & 0x0F


def hue_family(entry: int) -> str:
    """The hue a colour belongs to. Every grey, dark grey and black column is one family, because a viewer reads
    them as grey whatever the hardware calls them."""
    column = column_of(entry)
    if column in GREY_COLUMNS:
        return "grey"
    return "hue_%X" % column


def codename(entry: int) -> str:
    return "$%02X" % int(entry)


# -----------------------------------------------------------------------------------------------------------------
# Building the set from the per scene files the art lane already solved.

def source_files(root: str) -> list:
    pattern = os.path.join(root, PALETTE_DIR, "scene_*.json")
    return sorted(glob.glob(pattern))


def judged_rows(root: str) -> list:
    """The audit rows, read from the scene files that solved the palettes the rows judge.

    A row says: this is the baked frame, these are the sheets that stand on it. A file can carry more than one (the
    ship's own screen and the ship's set read against the title ground are two different readings), so "judged" is
    a list. It lives beside the palettes because the cast decision and the row that measures it are one decision:
    a card that re-solves a scene's sprite half edits this list in the same file.

    "exempt" is an optional string on a row the cast check does not enforce, and it has to say why. The tests hold
    the list of exempt rows, so an exemption is a decision that shows up in a diff, not a way to quiet the check.
    """
    rows = []
    for path in source_files(root):
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        scene_id = os.path.basename(path)[len("scene_"):-len(".json")]
        for index, row in enumerate(payload.get(JUDGED_KEY, [])):
            if not isinstance(row, dict):
                raise SystemExit("scene_palette_set: %s judged row %d is not an object"
                                 % (os.path.basename(path), index))
            missing = [key for key in JUDGED_FIELDS if not row.get(key)]
            if missing:
                raise SystemExit("scene_palette_set: %s judged row %d is missing %s"
                                 % (os.path.basename(path), index, ", ".join(missing)))
            entry = {"scene": scene_id,
                     "background": row["background"],
                     "sprites": list(row["sprites"]),
                     "note": row.get("note", "")}
            for key in ("at", "frame", "exempt", BY_PRODUCT_KEY):
                if key in row:
                    entry[key] = row[key]
            rows.append(entry)
    return rows


def scene_from_source(root: str, path: str, colours) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    scene_id = os.path.basename(path)[len("scene_"):-len(".json")]
    rows = []
    for key in ("background", "sprites"):
        for row in payload[key]:
            if len(row["colours"]) != scene_palette.LIMIT:
                raise SystemExit("scene_palette_set: %s has a %s palette of %d entries, the rule is %d"
                                 % (path, key, len(row["colours"]), scene_palette.LIMIT))
    entry = {
        "id": scene_id,
        "backdrop": int(payload["backdrop"]),
        "background": [{"name": row.get("name", "bg%d" % index), "colours": list(map(int, row["colours"]))}
                       for index, row in enumerate(payload["background"])],
        "sprites": [{"name": row.get("name", "sp%d" % index), "colours": list(map(int, row["colours"]))}
                    for index, row in enumerate(payload["sprites"])],
        "heroes": True,
        # Card t_c93a983f. Written from PARTY_CAST_SCENES, not read from the scene file: see the note beside
        # that constant for the measurement that decided it.
        PARTY_CAST_KEY: scene_id in PARTY_CAST_SCENES,
        "source": "%s/%s" % (PALETTE_DIR.replace(os.sep, "/"), os.path.basename(path)),
        # Every scene starts advisory. The first gate run on the frames that ship today reports failing pairs in
        # all of them (output/palette_synergy_gate.json), so gating one now would stop the build on art nobody has
        # repainted yet. Gamedev flips a scene's gate to true once the pairs it owns are fixed; the tool never
        # flips it itself.
        "gate": False,
        "note": "solved by tools/art/scene_palette.py from the art on disk, then checked by "
                "tools/nes_composite_check.py and tools/check_scene_palettes.py",
    }
    # Card t_a1170172: the title scene also carries the per-band plan and the per-sprite band assignment, because a
    # scene that scrolls along x only is legal per 16 px row band and not per area. They are derived here from the
    # scene file rather than written by hand into data/scene_palettes.json, which is the point of this builder: the
    # shipped set must be reproducible from the per scene files, or the file has two owners.
    for key in ("bands", "band_sprites"):
        if key in payload:
            entry[key] = json.loads(json.dumps(payload[key]))
    return entry


def hero_block(colours) -> dict:
    out = {}
    for name in HEROES:
        spec = HERO_PALETTES[name]
        out[name] = {
            "roles": list(HERO_ROLES),
            "colours": list(spec["colours"]),
            "hex": ["#%02x%02x%02x" % colours[entry] for entry in spec["colours"]],
            "hue": spec["hue"],
            "fixed": True,
            "note": spec["note"],
        }
    return out


def build(root: str = ROOT) -> dict:
    """The palette set, derived from the per scene files that already exist. Deterministic: same inputs, same file."""
    colours, usable, _ = load_master(root)
    scenes = []
    for path in source_files(root):
        scenes.append(scene_from_source(root, path, colours))
    if not scenes:
        raise SystemExit("scene_palette_set: no %s/scene_*.json to build from" % PALETTE_DIR.replace(os.sep, "/"))
    return {
        "format": 1,
        "kind": "scene_palettes",
        "name": "scene palette sets",
        "rule": RULE,
        "hero_rule": "ART-BIBLE.md RULE 0 point 3: 4 reserved hero palettes of 3 colours each, 1 dark outline, "
                     "1 mid body, 1 accent; fixed, and changed only here",
        "master": "data/nes_palette.json",
        "master_source": "tools/art/nes_palette_build.py, cited to NESdev and 8bitphoto in knowledge/ART-BIBLE.md",
        "notes": [
            "A scene's set is written down before the art is made (RULE 0 point 1) and named in the card and the "
            "output manifest of every concept round (RULE 0 point 6).",
            "background and sprites are lists of 4 palettes of 3, in the order the PPU selects them: the first is "
            "palette 0, so entry 0 of background palette 0 is the backdrop.",
            "heroes true means the scene also carries the 4 reserved hero palettes, so a character concept is "
            "quantised against the colours it will really ship with.",
            "party_cast true means the scene draws the party, so its 4 sprite palettes ARE the 4 reserved hero "
            "palettes: they replace the scene's own sprite rows instead of adding to them, because the PPU has "
            "4 sprite palettes and a frame has nowhere to put a fifth (knowledge/PALETTE-RULINGS-2026-10-25.md "
            "section 7.1, card t_c93a983f). A scene without the flag keeps its own 4 sprite rows, so the towns, "
            "the ship, the title, the icons, the sea and the ui scene are unchanged; the four battle strips carry "
            "it and nothing else does.",
            "gate true means tools/palette_synergy.py may fail the build on this scene; a scene with gate false "
            "still reports its failing pairs, and gamedev decides when it becomes gated.",
            "Generated by tools/scene_palette_set.py build --write from data/palettes/scene_*.json. Do not hand "
            "edit a scene's numbers here: edit the per scene file or the art, then rebuild, so the numbers stay "
            "derived from something measured.",
        ],
        "hero_palettes": hero_block(colours),
        "scenes": scenes,
        # The audit rows come from the scene files (JUDGED_KEY), not from a constant here: see the note beside
        # JUDGED_KEY. A row whose baked frame is not on disk is an ERROR, not a row that quietly disappears:
        # output/ is not in git, so a tree without these frames is a broken tree, and dropping the row is how
        # data/scene_palettes.json came to hold 6 audit rows that a rebuild could only reproduce 3 of in a
        # clean checkout (card t_19b41ab7). See audit_rows().
        "audit": audit_rows(root),
    }


def audit_rows(root: str = ROOT) -> list:
    """The audit rows, with a hard failure for any row whose baked frame is not on disk.

    The frames are committed and each one is written by a tool, so the only way one is absent is a broken
    checkout or a moved path. Failing here names the row, the scene and the writer; returning a shorter list
    would make `build --write` strip rows out of data/scene_palettes.json and leave the file looking derived.
    """
    rows = []
    for row in judged_rows(root):
        path = os.path.join(root, row["background"].replace("/", os.sep))
        if not os.path.isfile(path):
            raise SystemExit(
                "scene_palette_set: judged row of scene %r names %s, which is not on disk. It is committed, and "
                "written by a tool (output/cloud_sky_ground.png by tools/art/title_cloud_ground.py, "
                "output/bg_battle_*_frame.png by tools/art/make_battle_bg.py), so a tree without it is a broken "
                "tree: rebuild the frame or fix the row, do not ship a shorter audit list."
                % (row["scene"], row["background"]))
        rows.append(row)
    return rows


def write(root: str, payload: dict) -> str:
    path = data_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")
    return path


# -----------------------------------------------------------------------------------------------------------------
# Validation. Every number is checked against the file the project already trusts for it.

def validate(root: str = ROOT, data: dict | None = None) -> list:
    problems = []
    data = load(root) if data is None else data
    colours, usable, _ = load_master(root)

    if data.get("kind") != "scene_palettes":
        problems.append("kind is %r, expected 'scene_palettes'" % data.get("kind"))

    heroes = data.get("hero_palettes", {})
    missing = [name for name in HEROES if name not in heroes]
    if missing:
        problems.append("hero palettes missing: %s" % ", ".join(missing))
    for name, palette in sorted(heroes.items()):
        entries = [int(value) for value in palette.get("colours", [])]
        if len(entries) != 3:
            problems.append("hero %s has %d colours, the rule is 3" % (name, len(entries)))
        if len(set(entries)) != len(entries):
            problems.append("hero %s repeats a colour: %s" % (name, entries))
        for entry in entries:
            if not 0 <= entry < len(colours):
                problems.append("hero %s has $%02X, outside the 2C02 palette" % (name, entry))
            elif not usable[entry]:
                problems.append("hero %s has $%02X, a forbidden entry" % (name, entry))
        if len(entries) == 3 and not (row_of(entries[0]) <= row_of(entries[1]) <= row_of(entries[2])):
            problems.append("hero %s is not dark to light: rows %s for %s"
                            % (name, [row_of(entry) for entry in entries], entries))

    scenes = data.get("scenes", [])
    if not scenes:
        problems.append("no scenes: a palette set with no scene is not a set")
    seen_ids = set()
    for entry in scenes:
        scene_id = entry.get("id")
        if not scene_id:
            problems.append("a scene has no id")
            continue
        if scene_id in seen_ids:
            problems.append("scene id %r appears twice" % scene_id)
        seen_ids.add(scene_id)
        backdrop = int(entry.get("backdrop", -1))
        if not 0 <= backdrop < len(colours):
            problems.append("%s: backdrop $%02X is outside the 2C02 palette" % (scene_id, backdrop))
        elif not usable[backdrop]:
            problems.append("%s: backdrop $%02X is a forbidden entry" % (scene_id, backdrop))
        for key, label in (("background", "background"), ("sprites", "sprite")):
            rows = entry.get(key, [])
            if len(rows) != 4:
                problems.append("%s: %d %s palettes, the PPU has 4" % (scene_id, len(rows), label))
            for index, row in enumerate(rows):
                entries = [int(value) for value in row.get("colours", [])]
                if len(entries) != 3:
                    problems.append("%s: %s palette %d has %d colours, the rule is 3"
                                    % (scene_id, label, index, len(entries)))
                if len(set(entries)) != len(entries):
                    problems.append("%s: %s palette %d repeats a colour: %s"
                                    % (scene_id, label, index, entries))
                for value in entries:
                    if not 0 <= value < len(colours):
                        problems.append("%s: %s palette %d has $%02X, outside the 2C02 palette"
                                        % (scene_id, label, index, value))
                    elif not usable[value]:
                        problems.append("%s: %s palette %d has $%02X, a forbidden entry"
                                        % (scene_id, label, index, value))
                # The backdrop is entry 0 of background palette 0 and is shared by every palette, so the same
                # entry may also be named inside a palette (a sprite outline in $0F is black, not a second
                # backdrop). That is the PPU's own behaviour, so it is not a rule break.
        total = {backdrop}
        for row in entry.get("background", []) + entry.get("sprites", []):
            total.update(int(value) for value in row.get("colours", []))
        if len(total) > 25:
            problems.append("%s: %d colours across the set, one frame may show 25" % (scene_id, len(total)))
        party = entry.get(PARTY_CAST_KEY, False)
        if not isinstance(party, bool):
            problems.append("%s: %s is %r, expected true or false" % (scene_id, PARTY_CAST_KEY, party))
        elif party and not entry.get("heroes", True):
            problems.append("%s: %s true but heroes false, so the party would have no palette to be drawn in"
                            % (scene_id, PARTY_CAST_KEY))
        elif party and len(allowed_sprite_sets(data, scene_id)) != 4:
            problems.append("%s: %s true but %d sprite palettes are allowed, a frame has 4"
                            % (scene_id, PARTY_CAST_KEY, len(allowed_sprite_sets(data, scene_id))))

    for item in data.get("audit", []):
        for key in ("scene", "background", "sprites"):
            if not item.get(key):
                problems.append("audit entry missing %r: %s" % (key, json.dumps(item, sort_keys=True)[:120]))
        if item.get("scene") and item["scene"] not in seen_ids:
            problems.append("audit names unknown scene %r" % item["scene"])
        if item.get("exempt") is not None and not str(item.get("exempt")).strip():
            problems.append("audit entry on %r is exempt with no reason given" % item.get("scene"))
        if BY_PRODUCT_KEY in item and not isinstance(item[BY_PRODUCT_KEY], bool):
            problems.append("audit entry on %r has %s %r, expected true or false"
                            % (item.get("scene"), BY_PRODUCT_KEY, item.get(BY_PRODUCT_KEY)))

    problems.extend(cast_problems(root, data))
    return problems


def cast_problems(root: str, data: dict) -> list:
    """Every audit row whose cast the scene's four sprite palettes cannot carry.

    This is the check that was missing when the deck's row named the walking sailor for a day after the deck's four
    palettes were re-solved for the fight cast: the row was a constant in another file, so nothing compared it with
    the set it judged (card t_4f18c0ac, knowledge/PALETTE-RULINGS-2026-10-24.md section 9).

    The measurement is tools/palette_synergy.py's own, through cast_problems() there: R7 on the sheet's own colours
    and R6 in both readings. Nothing is restated here, and a pair failure (body against ground) is NOT a cast
    failure, because a scene whose frame still fails its pair column can carry its cast perfectly well.

    A row marked "exempt" is skipped: the tests hold the exact list of exempt rows, so an exemption is a ruling
    with a reason in the scene file, not a quiet escape. A row marked "by_product" is skipped as well, because
    its file is one no clean checkout reproduces and whatever it measures is advisory, not a cast ruling (card
    t_c93a983f, ruling section 8). A row whose frame or sheets are not on disk is skipped too, because output/
    is not in git and a fresh worktree has none of it.
    """
    import palette_synergy  # local: palette_synergy imports this module, so this cannot be a top level import

    problems = []
    for item in data.get("audit", []):
        if item.get("exempt") or item.get(BY_PRODUCT_KEY):
            continue
        background = item.get("background")
        if not background or not os.path.isfile(os.path.join(root, background)):
            continue
        sprites = [path for path in item.get("sprites", []) if os.path.isfile(os.path.join(root, path))]
        if not sprites:
            continue
        frame = item.get("frame") or [None, None]
        result = palette_synergy.analyse(root, item["scene"], background, sprites, item.get("at"),
                                         frame[0], frame[1])
        by_sheet = {}
        for problem in palette_synergy.cast_problems(result):
            by_sheet.setdefault(problem.get("sprite", "?"), []).append(problem["detail"])
        for sheet, details in sorted(by_sheet.items()):
            problems.append("%s: the audit row on %s names %s, and the scene's 4 sprite palettes cannot carry it "
                            "(%d problem(s); first: %s)"
                            % (item["scene"], background, sheet, len(details), details[0]))
    return problems


# -----------------------------------------------------------------------------------------------------------------
# CLI.

def describe_scene(entry: dict, colours) -> str:
    lines = ["%s  backdrop %s %s  gate=%s"
             % (entry["id"], codename(entry["backdrop"]), "#%02x%02x%02x" % colours[entry["backdrop"]],
                entry.get("gate", False))]
    for key in ("background", "sprites"):
        for index, row in enumerate(entry[key]):
            shown = " ".join("%s %s" % (codename(value), "#%02x%02x%02x" % colours[value])
                             for value in row["colours"])
            lines.append("  %s %d %-4s %s" % (key[:2], index, row.get("name", ""), shown))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="The palette set every scene starts from (ART-BIBLE RULE 0).")
    parser.add_argument("command", choices=["build", "validate", "list", "show"])
    parser.add_argument("--scene", default=None)
    parser.add_argument("--write", action="store_true", help="build only: write data/scene_palettes.json")
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.command == "build":
        payload = build(root)
        if args.write:
            print("wrote %s (%d scenes)" % (write(root, payload), len(payload["scenes"])))
        else:
            print(json.dumps(payload, indent=2))
        return 0

    if args.command == "validate":
        data = load(root)
        problems = validate(root, data)
        if problems:
            for problem in problems:
                print("FAIL %s" % problem)
            print("scene_palette_set: %d problem(s)" % len(problems))
            return 1
        print("scene_palette_set: PASS, %d scene(s), %d hero palette(s)"
              % (len(data["scenes"]), len(data["hero_palettes"])))
        return 0

    data = load(root)
    colours, _, _ = load_master(root)
    if args.command == "list":
        for entry in data["scenes"]:
            print("%-24s backdrop %s  gate=%s  %s"
                  % (entry["id"], codename(entry["backdrop"]), entry.get("gate", False), entry.get("source", "")))
        return 0

    if not args.scene:
        print("show needs --scene. Known: %s" % ", ".join(scene_ids(data)))
        return 2
    print(describe_scene(find_scene(data, args.scene), colours))
    for name in HEROES:
        palette = hero(data, name)
        print("  hero %-8s %s  %s" % (name, " ".join(codename(value) for value in palette["colours"]),
                                      palette.get("hue", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
