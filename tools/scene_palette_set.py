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

# The pairs tools/palette_synergy.py checks on every gate run (--gate). Kept here rather than written by hand
# into the JSON so a rebuild cannot lose them. gate is read from the scene's own "gate" flag.
AUDIT = (
    {"scene": "title", "background": "output/nes_title_frame.png",
     "sprites": ["game/sprites_src/title/spr_title_car.png",
                 "game/sprites_src/title/spr_pp_title_logo.png",
                 "game/sprites_src/title/spr_pp_menu_cursor.png"],
     "note": "the finished title frame against the sprites that stand on it"},
    {"scene": "battle_deck_night", "background": "output/bg_battle_deck_night_frame.png",
     "sprites": ["game/sprites_src/chars/sailor_battle.png", "game/sprites_src/chars/sailor_ow_v2.png"],
     "note": "the ship deck at night, the ground the sailor sprites stand on"},
    {"scene": "ship", "background": "output/ship_dialogue.png",
     "sprites": ["game/sprites_src/chars/sailor_battle.png", "game/sprites_src/chars/sailor_ow_v2.png"],
     "note": "the ship screen with dialogue, the other frame that ships today"},
    {"scene": "ship", "background": "output/nes_title_frame.png",
     "sprites": ["game/sprites_src/chars/sailor_ow_v2.png"],
     "note": "the ship scene's set against the title ground: what a shared ground costs a scene that did not "
             "design for it"},
    {"scene": "battle_corridor", "background": "output/bg_battle_corridor_frame.png",
     "sprites": ["game/sprites_src/chars/percy_battle.png", "game/sprites_src/chars/hadrian_battle.png",
                 "game/sprites_src/chars/zander_ow_v2.png"],
     "note": "the corridor battle ground against the three hero battle sheets"},
    {"scene": "battle_corridor", "background": "output/bg_battle_corridor_frame.png",
     "sprites": ["output/sprites_v2_sheet.png"],
     "note": "the sprites_v2 contact sheet, the whole v2 cast read against one ground at a time"},
)


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


def scene_payload(entry: dict) -> dict:
    """The shape tools/art/scene_palette.py Scene reads: backdrop, background[4], sprites[4], scene name."""
    payload = {
        "scene": entry["id"],
        "backdrop": entry["backdrop"],
        "background": [{"name": row.get("name", "bg%d" % index), "colours": list(row["colours"])}
                       for index, row in enumerate(entry["background"])],
        "sprites": [{"name": row.get("name", "sp%d" % index), "colours": list(row["colours"])}
                    for index, row in enumerate(entry["sprites"])],
    }
    return payload


def scene(root: str, scene_id: str) -> scene_palette.Scene:
    """A scene_palette.Scene for this scene, so callers reuse the enforcement arithmetic instead of copying it."""
    return scene_palette.Scene(scene_payload(find_scene(load(root), scene_id)), root)


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


def scene_entries(data: dict, scene_id: str) -> set:
    """Every entry the scene may spend: the backdrop, the 4 background and 4 sprite palettes, and the heroes."""
    entry = find_scene(data, scene_id)
    out = {int(entry["backdrop"])}
    for row in entry["background"] + entry["sprites"]:
        out.update(int(value) for value in row["colours"])
    if entry.get("heroes", True):
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
    return {
        "id": scene_id,
        "backdrop": int(payload["backdrop"]),
        "background": [{"name": row.get("name", "bg%d" % index), "colours": list(map(int, row["colours"]))}
                       for index, row in enumerate(payload["background"])],
        "sprites": [{"name": row.get("name", "sp%d" % index), "colours": list(map(int, row["colours"]))}
                    for index, row in enumerate(payload["sprites"])],
        "heroes": True,
        "source": "%s/%s" % (PALETTE_DIR.replace(os.sep, "/"), os.path.basename(path)),
        # Every scene starts advisory. The first gate run on the frames that ship today reports failing pairs in
        # all of them (output/palette_synergy_gate.json), so gating one now would stop the build on art nobody has
        # repainted yet. Gamedev flips a scene's gate to true once the pairs it owns are fixed; the tool never
        # flips it itself.
        "gate": False,
        "note": "solved by tools/art/scene_palette.py from the art on disk, then checked by "
                "tools/nes_composite_check.py and tools/check_scene_palettes.py",
    }


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
            "gate true means tools/palette_synergy.py may fail the build on this scene; a scene with gate false "
            "still reports its failing pairs, and gamedev decides when it becomes gated.",
            "Generated by tools/scene_palette_set.py build --write from data/palettes/scene_*.json. Do not hand "
            "edit a scene's numbers here: edit the per scene file or the art, then rebuild, so the numbers stay "
            "derived from something measured.",
        ],
        "hero_palettes": hero_block(colours),
        "scenes": scenes,
        "audit": [dict(item) for item in AUDIT
                  if os.path.isfile(os.path.join(root, item["background"]))],
    }


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

    for item in data.get("audit", []):
        for key in ("scene", "background", "sprites"):
            if not item.get(key):
                problems.append("audit entry missing %r: %s" % (key, json.dumps(item, sort_keys=True)[:120]))
        if item.get("scene") and item["scene"] not in seen_ids:
            problems.append("audit names unknown scene %r" % item["scene"])
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
