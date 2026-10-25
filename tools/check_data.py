"""Validate every data file against its schema, its ranges and its references.

This is the gate that runs on a machine with no GameMaker installed. It answers three questions:

  1. SCHEMA: does the file have the fields the GML modules read, with the right types?
  2. RANGES: is every number inside the range the spec allows (speed, life, hp, counts, timings)?
  3. REFERENCES: does every id it names exist somewhere, and does every scene, trigger, rail and reward point at a
     real thing? A dangling id is the failure that would otherwise appear as a silent wrong fight at runtime.

It also SIMULATES every bullet pattern with the same recipe rules the engine uses (same linear congruential seed, same
origin and aim order, same 24 pixel spawn exclusion, the same pp_angle_to_gm mirror of a data angle, the same negated
curve, and the same GameMaker lengthdir, whose y component is negative because a direction of 90 points up) and asserts
that each pattern terminates inside the 900 step cap, never spawns inside the exclusion radius, and never exceeds its
declared concurrent hazard count. That simulation is a second implementation of pp_dodge_recipe.gml and
pp_dodge_arena.gml; when one changes, the other changes with it.

Every message names the file and the field path, because "data invalid" is not actionable.

Usage:
    python tools/check_data.py            # exit 0 when every file passes
    python tools/check_data.py --root .   # explicit repo root
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

# ---------------------------------------------------------------------------------------------------------------
# Mirror of pp_config.gml. If these drift, the checker stops being a proof, so keep them in one visible block.

FORMAT = 1
FRAME_W, FRAME_H = 256, 240
ARENA_CX, ARENA_CY = 128, 120
ARENA_W, ARENA_H = 160, 100
ARENA_X1 = ARENA_CX - ARENA_W // 2          # 48
ARENA_Y1 = ARENA_CY - ARENA_H // 2          # 70
ARENA_X2 = ARENA_X1 + ARENA_W               # 208
ARENA_Y2 = ARENA_Y1 + ARENA_H               # 170
MARKER_SIZE = 8
MARKER_SPEED = 2
HITBOX_INSET = 2
SPAWN_EXCLUSION = 24
ARENA_CAP = 900
WARN_STEPS = 12
PALETTE_SIZE = 54
MAX_COLOURS_ON_SCREEN = 16
# The master palette is 9 hue families by 6 visible levels, in that order (spec 13). Every family/level pair has a role
# name, so a room palette names colours instead of guessing indices, and a colour inserted into the middle of a family is
# caught because every later family role then points at the wrong entry.
PALETTE_LEVELS = 6
PALETTE_FAMILIES = ("grey", "sea", "bronze", "wine", "moss", "stone", "gold", "violet", "blood")
SEMANTIC_ROLES = ("ink", "paper", "dim", "accent", "marker", "marker_trail", "hazard", "warn")
MAX_FLAGS = 200
MAX_FLAG_LEN = 32
# The box's line in characters (spec 05, card t_1d828fcd). The dialogue window is 240 pixels wide with an 8 pixel
# padding on each side, so the text area is 224 pixels, so 28 cells of the 8x8 font fit: 16 + 28 * 8 = 240. This is
# the same number as PP_TEXT_CHARS in game/scripts/pp_config/pp_config.gml, and
# tests/test_dialogue_v2.py::test_the_box_geometry_and_the_wrap_agree fails when the two drift apart.
LINE_CHARS = 28
# Spec 18 section 1: at most four phase rows per enemy, and a breakpoint is a percent of max_hp compared in integers
# (section 8 P3), so 1 to 99 and never absolute hp. Spec 18 section 6 consequence 1 lets a phase row raise the attack
# inside the enemy's own band and calls that not a rule change; spec 07 line 32 writes Percy's band, 3 to 6. A regular
# enemy has no band written anywhere, so a phase row on one that carries an attack is refused instead of guessed at.
PHASE_ROWS_MAX = 4
PHASE_ATTACK_BAND = (3, 6)
# Spec 18 section 4: the interruption fires on a refused SPARE press, and `on` is a closed set with one member in the
# demo. The four route keys are all required when `scene` is an object, because a partial object would be a route
# table smuggled into the schema (section 8 A18-4).
INTERRUPT_TRIGGERS = {"spare_refused"}
INTERRUPT_ROUTE_KEYS = ("undecided", "mercy", "blooded", "genocide")
PAGES = 3
# Dialogue v2 (decision D2, 2026-10-22). A page is one row or three of them, a page holds at most three lines, and an
# entry holds at most three pages; a choice label is 12 characters of the row that draws it (spec 05, card
# t_01432e14: the label is drawn from x 24 of the text area, which leaves 27 columns, and 12 is the authored limit).
# These four numbers are the ones the schema repeats, and tests/test_schemas.py keeps the two descriptions equal.
PAGE_LINES = 3
CHOICES = 3
CHOICE_LABEL_CHARS = 12

PATTERN_FIELD_RANGES = {
    "at": (0, 899),
    "count": (1, 24),
    "spread": (0, 360),
    "speed": (0.25, 4.0),
    "angle": (0, 359),
    "accel": (-0.05, 0.05),
    "curve": (-6, 6),
    "life": (30, 900),
    "size": (8, 16),
    "delay": (0, 12),
    "jitter_angle": (0, 180),
}
WOBBLE_RANGES = {"amp": (0, 8), "period": (10, 120)}

PATTERN_SHAPES = {"rain", "wall", "ring", "fan", "spiral", "sweep", "pincer", "lob"}
PATTERN_AIM = {"fixed", "at_marker"}
ORIGIN_NAMES = {"top", "bottom", "left", "right", "centre", "corner"}

TRIGGER_KINDS = {"scene", "battle", "map", "say", "flag", "marker", "save"}
# The id table each trigger kind names, for the cross reference. "save" is absent on purpose: a save point's id is a
# label for the player's sake (spec 11), not a row in any table, so there is nothing to resolve it against.
TRIGGER_ID_TABLES = {
    "scene": "scene", "battle": "encounter", "map": "map",
    "say": "dialogue", "flag": "flag", "marker": "encounter",
}
SCENE_COMMANDS = {
    "say", "move", "face", "wait", "fade", "music", "sfx", "camera",
    "shake", "flash", "spawn", "destroy", "battle", "setflag", "branch", "end",
}
DIRECTIONS = {"up", "down", "left", "right"}
AUDIO_KINDS = {"music", "sfx", "ui"}

# The music cue registry (spec 12, card G0-2). A cue id is the musician's own label, PP-01 to PP-16, so his OGG drops
# in under the cue's asset name with no code edit. The id shape is checked because a typo in an id is exactly the kind
# of mistake that would otherwise make a room silent with no error.
AUDIO_CUE_RE = re.compile(r"^PP-[0-9]{2}[ab]?$")
# The four cues the vertical slice cannot ship without: the ship, Percy, and the two endings.
SLICE_CUES = ("PP-05", "PP-06", "PP-15a", "PP-15b")


HEX_DIGITS = set("0123456789abcdefABCDEF")

# The JSON Schema documents in data/schemas, one per data file that holds a table of things. The schema is the
# published shape of the file, readable by an editor or another tool; this checker enforces it and then goes on to the
# ranges, the cross references and the pattern simulation that a schema cannot express.
SCHEMA_FILES = {
    "maps/all.json": "maps.schema.json",
    "maps/ship_sample.json": "maps.schema.json",
    "enemies/all.json": "enemies.schema.json",
    "patterns/all.json": "patterns.schema.json",
    "dialogue/all.json": "dialogue.schema.json",
    "scenes/all.json": "cutscenes.schema.json",
    "talk_cards.json": "talk_cards.schema.json",
}


def _dot_path(parts) -> str:
    out = ""
    for part in parts:
        out += "[%d]" % part if isinstance(part, int) else ("." + str(part) if out else str(part))
    return out or "<root>"


def schema_failures(root: str) -> list[str]:
    """Validate each table file against its JSON Schema in data/schemas.

    jsonschema is a dev tool of this repository, not a runtime dependency of the game: the engine never reads a schema.
    It is reported as a failure rather than skipped when absent, because a schema nobody enforces is a document that
    rots while the data it describes moves on.
    """
    try:
        import jsonschema
    except ImportError:
        return ["data/schemas: jsonschema is not installed, so the JSON Schemas cannot be enforced "
                "(python -m pip install jsonschema)"]

    errors: list[str] = []
    schema_dir = os.path.join(root, "data", "schemas")
    for rel, schema_name in sorted(SCHEMA_FILES.items()):
        schema_path = os.path.join(schema_dir, schema_name)
        data_path = os.path.join(root, "data", rel)
        try:
            with open(schema_path, "r", encoding="utf-8") as handle:
                schema = json.load(handle)
        except OSError:
            errors.append("data/schemas/%s: missing, but data/%s is validated against it" % (schema_name, rel))
            continue
        except ValueError as exc:
            errors.append("data/schemas/%s: is not valid JSON: %s" % (schema_name, exc))
            continue
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            errors.append("data/schemas/%s: is not a valid 2020-12 schema: %s" % (schema_name, exc.message))
            continue
        if not os.path.exists(data_path):
            continue
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        shown = 0
        for problem in sorted(jsonschema.Draft202012Validator(schema).iter_errors(data),
                              key=lambda e: list(e.absolute_path)):
            errors.append("data/%s: %s: %s (schema %s)"
                          % (rel, _dot_path(list(problem.absolute_path)), problem.message, schema_name))
            shown += 1
            if shown >= 6:
                errors.append("data/%s: more schema errors in %s not shown" % (rel, schema_name))
                break
    return errors


class Checker:
    def __init__(self, root: str):
        self.root = root
        self.errors: list[str] = []
        self.files: dict[str, object] = {}
        self.room_palette_ids = None

    # -- plumbing ------------------------------------------------------------------------------------------------

    def error(self, filename: str, path: str, message: str) -> None:
        where = path if path else "<root>"
        self.errors.append("%s: %s: %s" % (filename, where, message))

    def load(self, rel: str, required: bool = True):
        full = os.path.join(self.root, "data", rel)
        if not os.path.isfile(full):
            if required:
                self.error("data/" + rel, "<file>", "file is missing")
            return None
        try:
            with open(full, "r", encoding="utf-8-sig") as fh:
                parsed = json.load(fh)
        except json.JSONDecodeError as exc:
            self.error("data/" + rel, "<file>", "not valid JSON: %s" % exc)
            return None
        self.files[rel] = parsed
        return parsed

    @staticmethod
    def want(obj, key, kind, filename, path):
        if not isinstance(obj, dict):
            return None
        if key not in obj:
            return None
        value = obj[key]
        ok = {
            "str": isinstance(value, str),
            "int": isinstance(value, int) and not isinstance(value, bool),
            "num": isinstance(value, (int, float)) and not isinstance(value, bool),
            "list": isinstance(value, list),
            "dict": isinstance(value, dict),
            "bool": isinstance(value, bool),
        }.get(kind, True)
        if not ok:
            return None
        return value

    def require(self, obj, key, kind, filename, path):
        value = self.want(obj, key, kind, filename, path)
        if value is None:
            if not isinstance(obj, dict) or key not in obj:
                self.error(filename, path + "." + key if path else key, "missing required field")
            else:
                self.error(filename, path + "." + key if path else key, "must be a %s" % kind)
        return value

    def in_range(self, value, low, high, filename, path):
        if value is None:
            return False
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            self.error(filename, path, "must be a number")
            return False
        if value < low or value > high:
            self.error(filename, path, "%s is outside %s to %s" % (value, low, high))
            return False
        return True

    # -- entry point ---------------------------------------------------------------------------------------------

    def register_ids(self, ids) -> None:
        """Pre-pass: fill every id table before any reference is checked.

        Without this, a file checked early (enemies) would report its references as missing merely because the file
        that defines them (patterns) is checked later. The per file checks still detect duplicates.
        """
        def rows(rel, key):
            data = self.files.get(rel)
            if isinstance(data, dict) and isinstance(data.get(key), list):
                return [row for row in data[key] if isinstance(row, dict)]
            return []

        for table, rel, key in (
            ("enemy", "enemies/all.json", "enemies"),
            ("encounter", "encounters/all.json", "encounters"),
            ("pattern", "patterns/all.json", "patterns"),
            ("map", "maps/all.json", "maps"),
            ("map", "maps/ship_sample.json", "maps"),
            ("scene", "scenes/all.json", "scenes"),
            ("dialogue", "dialogue/all.json", "dialogue"),
            ("item", "items.json", "items"),
            ("power", "powers.json", "powers"),
            ("sound", "audio.json", "sounds"),
            ("cue", "audio.json", "cues"),
        ):
            for row in rows(rel, key):
                name = row.get("id")
                if isinstance(name, str):
                    ids.setdefault(table, {})[name] = row

        flags = self.files.get("flags.json")
        if isinstance(flags, dict) and isinstance(flags.get("flags"), list):
            for name in flags["flags"]:
                if isinstance(name, str):
                    ids["flag"].add(name)

    def run(self) -> list[str]:
        project = self.load("project.json")
        palette = self.load("palette.json")
        party = self.load("characters/party.json")
        enemies = self.load("enemies/all.json")
        encounters = self.load("encounters/all.json")
        patterns = self.load("patterns/all.json")
        maps = self.load("maps/all.json")
        # The ship room's own map file (card ASSEMBLE), loaded with the rest so its map id is registered before any
        # other file references it. A map that names another map (card SFX-WIRE: the deck's hatch names the lower
        # deck) must not be reported as unknown just because the file that defines it is checked later.
        self.load("maps/ship_sample.json")
        scenes = self.load("scenes/all.json")
        dialogue = self.load("dialogue/all.json")
        # The talk cards (spec 16 section 10). The schema validates the file's shape; this check reads it as well so
        # a phase row and its phase card cannot point at different phases (card t_155e22e2).
        self.load("talk_cards.json")
        items = self.load("items.json")
        powers = self.load("powers.json")
        flags = self.load("flags.json")
        audio = self.load("audio.json")
        slice_ = self.load("slice.json")

        ids = {
            "enemy": {}, "encounter": {}, "pattern": {}, "map": {}, "scene": {},
            "dialogue": {}, "item": {}, "power": {}, "sound": {}, "flag": set(), "cue": {},
        }
        self.register_ids(ids)

        self.check_project(project, ids)
        self.check_palette(palette)
        self.check_room_palettes(palette, self.load("room_palettes.json"))
        self.check_flags(flags, ids)
        self.check_items(items, ids)
        self.check_powers(powers, ids)
        self.check_audio(audio, ids)
        self.check_dialogue(dialogue, ids)
        self.check_characters(party, ids)
        self.check_enemies(enemies, ids)
        self.check_phase_talk(enemies, ids)
        self.check_patterns(patterns, ids)
        self.check_encounters(encounters, ids)
        self.check_maps(maps, ids)
        # The ship room's own map file (card ASSEMBLE). It is the map rm_pp_ship plays, so it is checked by the same
        # rules as the registry file and not only by the schema.
        ship_sample = self.files.get("maps/ship_sample.json") if isinstance(self.files, dict) else None
        self.check_maps(ship_sample, ids, "data/maps/ship_sample.json")
        self.check_scenes(scenes, ids)
        self.check_slice(slice_, ids)

        # Anything named but never defined is collected while walking; report once, sorted, so the list is readable.
        for ref_path, (kind, name) in sorted(self.dangling.items()):
            self.error(ref_path.split("|")[0], ref_path.split("|")[1], "unknown %s id %r" % (kind, name))
        return self.errors

    dangling: dict[str, tuple[str, str]] = {}

    def ref(self, ids, kind, name, filename, path):
        if not isinstance(name, str) or name == "":
            self.error(filename, path, "reference must be a non empty string")
            return None
        table = ids.get(kind)
        if table is None:
            return name
        if kind == "flag":
            if name not in table:
                self.dangling["%s|%s" % (filename, path)] = ("flag", name)
            return name
        if name not in table:
            self.dangling["%s|%s" % (filename, path)] = (kind, name)
            return None
        return table[name]

    # -- per file -------------------------------------------------------------------------------------------------

    def check_header(self, data, kind, filename):
        if not isinstance(data, dict):
            self.error(filename, "<root>", "must be a JSON object")
            return False
        fmt = self.require(data, "format", "int", filename, "")
        if fmt is not None and fmt != FORMAT:
            self.error(filename, "format", "is %s, this build reads %s" % (fmt, FORMAT))
        declared = self.want(data, "kind", "str", filename, "")
        if declared is not None and declared != kind:
            self.error(filename, "kind", "is %r, expected %r" % (declared, kind))
        return True

    def check_project(self, data, ids):
        filename = "data/project.json"
        if not self.check_header(data, "project", filename):
            return
        self.require(data, "title", "str", filename, "")
        frame = self.require(data, "base_frame", "list", filename, "")
        if frame is not None:
            if frame != [FRAME_W, FRAME_H]:
                self.error(filename, "base_frame", "must be [%d, %d] (spec 03)" % (FRAME_W, FRAME_H))
        steps = self.require(data, "steps_per_second", "int", filename, "")
        if steps is not None and steps != 60:
            self.error(filename, "steps_per_second", "must be 60 (spec 01)")
        self.require(data, "prison_stage", "int", filename, "")
        self.require(data, "start_map", "str", filename, "")
        labels = self.want(data, "route_labels", "list", filename, "")
        if labels is not None and labels != ["undecided", "mercy", "blooded", "genocide"]:
            self.error(filename, "route_labels", "must list the four routes in that order (spec 10)")

    def check_palette(self, data):
        filename = "data/palette.json"
        if not self.check_header(data, "palette", filename):
            return
        colours = self.require(data, "colours", "list", filename, "")
        if colours is None:
            return
        if len(colours) < PALETTE_SIZE:
            # Append only: fewer than the shipped 54 is a colour that was removed or moved, which shifts every index
            # after it. More is allowed, because spec 13 lets a new entry be added at the end.
            self.error(filename, "colours", "has %d entries, the master palette is %d and is append only"
                       % (len(colours), PALETTE_SIZE))
        seen = set()
        for index, value in enumerate(colours):
            path = "colours[%d]" % index
            if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
                self.error(filename, path, "must be a #RRGGBB string")
                continue
            if set(value[1:]) - HEX_DIGITS:
                self.error(filename, path, "has a non hex digit")
            if value.lower() in seen:
                self.error(filename, path, "duplicates %s" % value.lower())
            seen.add(value.lower())
        roles = self.require(data, "roles", "dict", filename, "")
        if roles is None:
            return
        for role in SEMANTIC_ROLES:
            value = self.require(roles, role, "int", filename, "roles")
            if value is not None and not (0 <= value < PALETTE_SIZE):
                self.error(filename, "roles." + role, "index %s is outside the palette" % value)
        # The 9 by 6 grid, by name. A role edited by hand to point at another level is caught here, which is the mistake
        # that would otherwise move a room's colour with no error at all. An insertion in the middle of the list is
        # caught by the digest below, because it shifts every colour after it.
        for family_index, family in enumerate(PALETTE_FAMILIES):
            for level in range(PALETTE_LEVELS):
                role = "%s_%d" % (family, level)
                expected = family_index * PALETTE_LEVELS + level
                value = self.require(roles, role, "int", filename, "roles")
                if value is not None and value != expected:
                    self.error(filename, "roles." + role,
                               "is %s, the %s level %d of the master palette is %d (spec 13)"
                               % (value, family, level, expected))

        # The frozen prefix. Every entry below `frozen` is sealed by a digest of its own hex strings, so a colour that is
        # edited or removed in place is caught even when the entry count is unchanged. Appending past the prefix is the
        # one edit that leaves both numbers alone, which is the only edit spec 13 allows.
        frozen = self.require(data, "frozen", "int", filename, "")
        if frozen is not None and frozen != PALETTE_SIZE:
            self.error(filename, "frozen", "is %s, the sealed prefix is the %d entries spec 13 ships"
                       % (frozen, PALETTE_SIZE))
        digest = self.require(data, "frozen_digest", "str", filename, "")
        if digest is not None and frozen is not None:
            sealed = ",".join(value.lower() for value in colours[:frozen] if isinstance(value, str))
            actual = hashlib.sha256(sealed.encode("utf-8")).hexdigest()
            if digest != actual:
                self.error(filename, "frozen_digest",
                           "does not match the first %d colours, so an entry was changed or removed in place "
                           "(append a new entry at the end instead)" % frozen)

    def check_room_palettes(self, master, data):
        """A room palette is a named list of role names, capped at 16 colours, every role a real master palette role."""
        filename = "data/room_palettes.json"
        self.room_palette_ids = set()
        # The roles of each set, by set id, so a scene command that names a role (a `flash`) is judged against the set
        # the room it plays in declares, not against every role in the master palette (card t_531bc76c).
        self.room_palette_roles = {}
        if master is None or not isinstance(master, dict):
            # A master palette that failed its own check has already been reported. Without its roles the roles below
            # cannot be judged, so this check reports the sets by count only and does not invent unknown role errors.
            master_roles = {}
        else:
            master_roles = master.get("roles") if isinstance(master.get("roles"), dict) else {}
        if not self.check_header(data, "room_palettes", filename):
            return

        sets = self.require(data, "sets", "list", filename, "")
        if sets is None:
            return
        if not sets:
            self.error(filename, "sets", "is empty, so every room would fall back to one set")
            return

        for index, entry in enumerate(sets):
            path = "sets[%d]" % index
            set_id = self.require(entry, "id", "str", filename, path)
            if isinstance(set_id, str):
                # From here the path names the set by id as well as by position. A refusal is read by whoever owns the
                # room that draws in this set, and "sets[3]" alone makes them count sets to find out which room it was.
                path = "sets[%d] %r" % (index, set_id)
                if set_id in self.room_palette_ids:
                    self.error(filename, path + ".id", "duplicate set id %r" % set_id)
                self.room_palette_ids.add(set_id)
                if set_id != set_id.lower() or not set_id.replace("_", "").isalnum() or set_id[0].isdigit():
                    self.error(filename, path + ".id", "%r must be lower case letters, digits and underscores" % set_id)

            roles = self.require(entry, "roles", "list", filename, path)
            if roles is None:
                continue
            if isinstance(set_id, str):
                _role_list = roles if isinstance(roles, list) else []
                self.room_palette_roles[set_id] = [role for role in _role_list if isinstance(role, str)]
            if len(roles) > MAX_COLOURS_ON_SCREEN:
                self.error(filename, path + ".roles",
                           "%d colours, the screen cap is %d (spec 13)" % (len(roles), MAX_COLOURS_ON_SCREEN))
            if len(set(roles)) != len(roles):
                self.error(filename, path + ".roles", "names the same role twice")
            for role_index, role in enumerate(roles):
                if not isinstance(role, str):
                    self.error(filename, "%s.roles[%d]" % (path, role_index), "must be a role name")
                    continue
                if master_roles and role not in master_roles:
                    self.error(filename, "%s.roles[%d]" % (path, role_index),
                               "%r is not a role in data/palette.json" % role)

        fallback = self.require(data, "default", "str", filename, "")
        if isinstance(fallback, str) and fallback not in self.room_palette_ids:
            self.error(filename, "default", "%r is not one of the declared set ids" % fallback)

    def check_flags(self, data, ids):
        filename = "data/flags.json"
        if not self.check_header(data, "flags", filename):
            return
        flags = self.require(data, "flags", "list", filename, "")
        if flags is None:
            return
        if len(flags) > MAX_FLAGS:
            self.error(filename, "flags", "%d flags, the demo budget is %d (spec 10)" % (len(flags), MAX_FLAGS))
        for index, name in enumerate(flags):
            path = "flags[%d]" % index
            if not isinstance(name, str):
                self.error(filename, path, "must be a string")
                continue
            if len(name) > MAX_FLAG_LEN:
                self.error(filename, path, "is %d characters, the limit is %d" % (len(name), MAX_FLAG_LEN))
            if name != name.lower() or not all(c.islower() or c.isdigit() or c == "_" for c in name):
                self.error(filename, path, "must be lowercase with underscores")
            ids["flag"].add(name)

    def check_items(self, data, ids):
        filename = "data/items.json"
        if not self.check_header(data, "items", filename):
            return
        rows = self.require(data, "items", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "items[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            heal = self.require(row, "heal", "int", filename, path)
            if heal is not None:
                self.in_range(heal, 1, 99, filename, path + ".heal")
            carry = self.require(row, "max_carry", "int", filename, path)
            if carry is not None:
                self.in_range(carry, 1, 99, filename, path + ".max_carry")
            if isinstance(name, str):
                if name in ids["item"] and ids["item"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["item"][name] = row

    def check_powers(self, data, ids):
        filename = "data/powers.json"
        if not self.check_header(data, "powers", filename):
            return
        rows = self.require(data, "powers", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "powers[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            cost = self.require(row, "cost", "int", filename, path)
            if cost is not None:
                self.in_range(cost, 0, 10, filename, path + ".cost")
            power = self.require(row, "power", "int", filename, path)
            if power is not None:
                self.in_range(power, 1, 99, filename, path + ".power")
            self.require(row, "effect", "str", filename, path)
            if isinstance(name, str):
                if name in ids["power"] and ids["power"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["power"][name] = row

    def check_audio(self, data, ids):
        filename = "data/audio.json"
        if not self.check_header(data, "audio", filename):
            return
        rows = self.require(data, "sounds", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "sounds[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            kind = self.require(row, "kind", "str", filename, path)
            if kind is not None and kind not in AUDIO_KINDS:
                self.error(filename, path + ".kind", "must be one of %s" % sorted(AUDIO_KINDS))
            file_name = self.require(row, "file", "str", filename, path)
            if file_name is not None and not file_name.lower().endswith(".ogg"):
                self.error(filename, path + ".file", "the delivery format is OGG (spec 12)")
            if isinstance(name, str):
                if name in ids["sound"] and ids["sound"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["sound"][name] = row
        # The cue registry comes after the sounds, because a cue's stand-in is one of those sound ids.
        self.check_cues(data, ids)

    def check_cues(self, data, ids):
        """The music cue registry: the musician's own ids, one row each, and the four cues the slice needs.

        A cue is a name plus the asset it will be delivered as, so his OGG lands as data\\music\\<asset>.ogg and no code
        changes. `placeholder` records that the OGG does not exist yet, which is the honest state of every cue today;
        a row that dropped the flag would claim a file the build does not have.
        """
        filename = "data/audio.json"
        rows = self.require(data, "cues", "list", filename, "")
        if rows is None:
            return
        if len(rows) == 0:
            self.error(filename, "cues", "the cue registry is empty, so no music cue can be asked for by id")

        route_labels = None
        project = self.files.get("project.json")
        if isinstance(project, dict) and isinstance(project.get("route_labels"), list):
            route_labels = project["route_labels"]

        seen = set()
        for index, row in enumerate(rows):
            path = "cues[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            title = self.require(row, "title", "str", filename, path)
            if isinstance(title, str) and title.strip() == "":
                self.error(filename, path + ".title", "is empty")
            asset = self.require(row, "asset", "str", filename, path)
            if isinstance(asset, str):
                if asset.lower().endswith(".ogg"):
                    self.error(filename, path + ".asset", "is the asset name without the .ogg, the loader adds it")
                elif not re.fullmatch(r"[a-z0-9_]+", asset):
                    self.error(filename, path + ".asset", "must be lowercase letters, digits and underscores")
            loop = self.require(row, "loop", "bool", filename, path)
            del loop
            self.require(row, "placeholder", "bool", filename, path)

            if isinstance(name, str):
                if not AUDIO_CUE_RE.match(name):
                    self.error(filename, path + ".id", "must look like PP-01 or PP-15a (spec 12)")
                if name in seen:
                    self.error(filename, path + ".id", "duplicate cue id %r" % name)
                seen.add(name)
                ids["cue"][name] = row

            if isinstance(row, dict) and row.get("placeholder_sound") is not None:
                stand_in = row.get("placeholder_sound")
                if not isinstance(stand_in, str) or stand_in == "":
                    self.error(filename, path + ".placeholder_sound", "must be a sound id or null")
                else:
                    sound = self.ref(ids, "sound", stand_in, filename, path + ".placeholder_sound")
                    if isinstance(sound, dict) and sound.get("kind") != "music":
                        self.error(filename, path + ".placeholder_sound",
                                   "%r is not a music entry in data/audio.json" % stand_in)

            if isinstance(row, dict) and row.get("boss") is not None and not isinstance(row.get("boss"), bool):
                self.error(filename, path + ".boss", "must be true or false")

            if isinstance(row, dict) and row.get("route") is not None:
                route = row.get("route")
                if not isinstance(route, str):
                    self.error(filename, path + ".route", "must be a route label string")
                elif route_labels is not None and route not in route_labels:
                    self.error(filename, path + ".route",
                               "%r is not one of the route labels %s (spec 10)" % (route, route_labels))

        missing = [cue for cue in SLICE_CUES if cue not in seen]
        for cue in missing:
            self.error(filename, "cues", "the vertical slice needs cue %s and it is not registered" % cue)

    def check_music_ref(self, ids, name, filename, path):
        """A music reference names a cue id or a sound id, and a sound id must be of kind music.

        Two forms on purpose during the handover: a room can be pointed at PP-05 today and the old sound id still
        works, so the data moves across one room at a time instead of in one break-everything edit.
        """
        if not isinstance(name, str) or name == "":
            self.error(filename, path, "reference must be a non empty string")
            return None
        if name in ids["cue"]:
            return name
        row = ids["sound"].get(name)
        if row is None:
            self.dangling["%s|%s" % (filename, path)] = ("sound or cue", name)
            return None
        if row.get("kind") != "music":
            self.error(filename, path, "%r is not a music entry in data/audio.json" % name)
        return row

    def check_dialogue(self, data, ids):
        filename = "data/dialogue/all.json"
        if not self.check_header(data, "dialogues", filename):
            return
        rows = self.require(data, "dialogue", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "dialogue[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "speaker", "str", filename, path)
            self.check_dialogue_portrait(row, path, filename)
            if isinstance(name, str):
                if name in ids["dialogue"] and ids["dialogue"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["dialogue"][name] = row
            has_lines = isinstance(row, dict) and "lines" in row
            has_pages = isinstance(row, dict) and "pages" in row
            if has_lines and has_pages:
                self.error(filename, path, "carries both lines and pages; an entry is exactly one of the two (D2)")
            elif not has_lines and not has_pages:
                self.error(filename, path, "carries neither lines nor pages; an entry is exactly one of the two (D2)")
            if has_lines:
                self.check_dialogue_lines(row, path, filename)
            if has_pages:
                self.check_dialogue_pages(row, path, filename)
            self.check_dialogue_sets(row, path, filename, ids, path + ".sets")
            self.check_dialogue_choices(row, path, filename, ids)

    def check_dialogue_lines(self, row, path, filename):
        """The one page shorthand: 1 to 9 lines, wrapped by word at 28 characters (spec delta T6)."""
        lines = self.require(row, "lines", "list", filename, path)
        if lines is None:
            return
        if len(lines) == 0:
            self.error(filename, path + ".lines", "must have at least one line")
        if len(lines) > PAGES * PAGE_LINES:
            self.error(filename, path + ".lines", "%d lines is more than %d pages of %d (spec 05)"
                       % (len(lines), PAGES, PAGE_LINES))
        for line_index, line in enumerate(lines):
            line_path = "%s.lines[%d]" % (path, line_index)
            if not isinstance(line, str):
                self.error(filename, line_path, "must be a string")
                continue
            if line.strip() == "":
                self.error(filename, line_path, "is empty")
            # Spec delta T6: a WORD longer than a line cannot wrap, so that is the error; long sentences wrap.
            for word in line.split(" "):
                if len(word) > LINE_CHARS:
                    self.error(filename, line_path,
                               "word %r is %d characters, longer than a %d character line"
                               % (word, len(word), LINE_CHARS))
                    break

    def check_dialogue_pages(self, row, path, filename):
        """The spec 05 shape: 1 to 3 pages of 1 to 3 lines, each line already one row of 28 characters.

        A page line is not wrapped by the checker the way a shorthand line is, because a page IS the broken text:
        a line of 29 characters has nowhere to go in a 28 character box, so it is refused with the id and the index.
        """
        pages = self.require(row, "pages", "list", filename, path)
        if pages is None:
            return
        if len(pages) == 0:
            self.error(filename, path + ".pages", "must have at least one page")
        if len(pages) > PAGES:
            self.error(filename, path + ".pages",
                       "%d pages is more than the %d a box entry may carry (spec 05, D2)" % (len(pages), PAGES))
        for page_index, page in enumerate(pages):
            page_path = "%s.pages[%d]" % (path, page_index)
            if not isinstance(page, dict):
                self.error(filename, page_path, "must be an object with lines")
                continue
            if "speaker" in page:
                speaker = self.want(page, "speaker", "str", filename, page_path)
                if isinstance(speaker, str) and speaker.strip() == "":
                    self.error(filename, page_path + ".speaker", "is empty")
            self.check_dialogue_portrait(page, page_path, filename)
            lines = self.require(page, "lines", "list", filename, page_path)
            if lines is None:
                continue
            if len(lines) == 0:
                self.error(filename, page_path + ".lines", "must have at least one line")
            if len(lines) > PAGE_LINES:
                self.error(filename, page_path + ".lines",
                           "%d lines is more than the %d a page holds (spec 05)" % (len(lines), PAGE_LINES))
            for line_index, line in enumerate(lines):
                line_path = "%s.lines[%d]" % (page_path, line_index)
                if not isinstance(line, str):
                    self.error(filename, line_path, "must be a string")
                    continue
                if line.strip() == "":
                    self.error(filename, line_path, "is empty")
                elif len(line) > LINE_CHARS:
                    self.error(filename, line_path,
                               "%r is %d characters, the box holds %d on a page line"
                               % (line, len(line), LINE_CHARS))

    def check_dialogue_portrait(self, row, path, filename):
        """A bust name is a sheet that exists, or the empty string for a page that draws none (spec 05, card t_4d6b0f4b).

        The name is data, and the sheet it points at is art, so the one thing this checker can prove is that the two
        agree: `portrait: percy` is game/sprites_src/chars/spr_pp_portrait_percy.png and nothing else. That is the whole
        reason the empty string is legal: an entry whose pages change speaker has to be able to say "nobody here"
        rather than inherit the entry's bust, and the page that says it is the checkpoint's narrator page.
        """
        if not isinstance(row, dict) or "portrait" not in row:
            return
        name = self.require(row, "portrait", "str", filename, path)
        if name is None:
            return
        field_path = path + ".portrait"
        if name == "":
            return
        if row.get("speaker") == "narrator":
            self.error(filename, field_path,
                       "a narrator draws no bust; give the page that names the speaker its own portrait")
        if not re.match(r"^[a-z][a-z0-9_]*$", name):
            self.error(filename, field_path,
                       "%r is not a bust name: lowercase letters, digits and underscores" % name)
            return
        chars = os.path.join(self.root, "game", "sprites_src", "chars")
        if not os.path.isdir(chars):
            # A root with no art lane at all, which is the data-only copy the data rules are tested against, cannot
            # prove or disprove a sheet, so it does not guess. The repository always carries this folder, so the sheet
            # check is enforced everywhere it can be wrong.
            return
        sheet = os.path.join(chars, "spr_pp_portrait_%s.png" % name)
        if not os.path.isfile(sheet):
            self.error(filename, field_path,
                       "no bust sheet for %r: game/sprites_src/chars/spr_pp_portrait_%s.png is not there"
                       % (name, name))

    def check_dialogue_sets(self, row, path, filename, ids, field_path):
        """Every flag an entry or a choice sets is a name in data/flags.json, so a typo cannot be set silently."""
        if not isinstance(row, dict) or "sets" not in row:
            return
        names = self.require(row, "sets", "list", filename, path)
        if names is None:
            return
        if len(names) == 0:
            self.error(filename, field_path, "must name at least one flag")
        for flag_index, name in enumerate(names):
            flag_path = "%s[%d]" % (field_path, flag_index)
            if not isinstance(name, str):
                self.error(filename, flag_path, "must be a flag name")
                continue
            self.ref(ids, "flag", name, filename, flag_path)

    def check_dialogue_choices(self, row, path, filename, ids):
        """The choice list lives on the entry's last page: 1 to 3 items of label, sets and optional goto (D2)."""
        if not isinstance(row, dict) or "choices" not in row:
            return
        choices = self.require(row, "choices", "list", filename, path)
        if choices is None:
            return
        if len(choices) == 0:
            self.error(filename, path + ".choices", "must have at least one choice")
        if len(choices) > CHOICES:
            self.error(filename, path + ".choices",
                       "%d choices is more than the %d the panel holds (spec 05)" % (len(choices), CHOICES))
        for choice_index, choice in enumerate(choices):
            choice_path = "%s.choices[%d]" % (path, choice_index)
            if not isinstance(choice, dict):
                self.error(filename, choice_path, "must be an object with label and sets")
                continue
            label = self.require(choice, "label", "str", filename, choice_path)
            if isinstance(label, str):
                if label.strip() == "":
                    self.error(filename, choice_path + ".label", "is empty")
                elif len(label) > CHOICE_LABEL_CHARS:
                    self.error(filename, choice_path + ".label",
                               "%r is %d characters, the panel holds %d"
                               % (label, len(label), CHOICE_LABEL_CHARS))
            self.check_dialogue_sets(choice, choice_path, filename, ids, choice_path + ".sets")
            if "goto" in choice:
                target = self.want(choice, "goto", "str", filename, choice_path)
                if isinstance(target, str):
                    self.ref(ids, "dialogue", target, filename, choice_path + ".goto")

    def check_characters(self, data, ids):
        filename = "data/characters/party.json"
        if not self.check_header(data, "characters", filename):
            return
        rows = self.require(data, "characters", "list", filename, "")
        if rows is None:
            return
        if len(rows) == 0:
            self.error(filename, "characters", "the party needs at least one character")
        for index, row in enumerate(rows):
            path = "characters[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            hp = self.require(row, "max_hp", "int", filename, path)
            if hp is not None:
                self.in_range(hp, 1, 999, filename, path + ".max_hp")
            will = self.require(row, "will_max", "int", filename, path)
            if will is not None:
                self.in_range(will, 0, 20, filename, path + ".will_max")
            mult = self.require(row, "power_multiplier", "num", filename, path)
            if mult is not None:
                self.in_range(mult, 0.5, 3.0, filename, path + ".power_multiplier")
            self.require(row, "sprite", "str", filename, path)
            start = self.want(row, "starting_items", "list", filename, path)
            if start is not None:
                for item_index, item in enumerate(start):
                    item_path = "%s.starting_items[%d]" % (path, item_index)
                    self.ref(ids, "item", self.want(item, "id", "str", filename, item_path), filename, item_path + ".id")
                    count = self.require(item, "count", "int", filename, item_path)
                    if count is not None:
                        self.in_range(count, 1, 99, filename, item_path + ".count")
            if isinstance(name, str):
                ids.setdefault("character", {})[name] = row

    def check_enemies(self, data, ids):
        filename = "data/enemies/all.json"
        if not self.check_header(data, "enemies", filename):
            return
        rows = self.require(data, "enemies", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "enemies[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            hp = self.require(row, "max_hp", "int", filename, path)
            if hp is not None:
                self.in_range(hp, 1, 9999, filename, path + ".max_hp")
            attack = self.require(row, "attack", "dict", filename, path)
            if attack is not None:
                low = self.require(attack, "min", "int", filename, path + ".attack")
                high = self.require(attack, "max", "int", filename, path + ".attack")
                if low is not None and high is not None and low > high:
                    self.error(filename, path + ".attack", "min %s is above max %s" % (low, high))
                if low is not None:
                    self.in_range(low, 1, 99, filename, path + ".attack.min")
            self.require(row, "sprite", "str", filename, path)
            kind = self.want(row, "route_kind", "str", filename, path)
            if kind is not None and kind not in ("regular", "boss"):
                self.error(filename, path + ".route_kind", "must be regular or boss (spec 10)")
            self.require(row, "element", "str", filename, path)
            patterns = self.require(row, "patterns", "list", filename, path)
            if patterns is not None:
                if len(patterns) == 0:
                    self.error(filename, path + ".patterns", "an enemy needs at least one pattern")
                for pattern_index, pattern_id in enumerate(patterns):
                    self.ref(ids, "pattern", pattern_id, filename, "%s.patterns[%d]" % (path, pattern_index))
            self.ref(ids, "dialogue", self.want(row, "talk_dialogue", "str", filename, path),
                     filename, path + ".talk_dialogue")
            trust = self.require(row, "trust_to_spare", "int", filename, path)
            if trust is not None:
                self.in_range(trust, 1, 10, filename, path + ".trust_to_spare")
            percent = self.require(row, "spare_hp_percent", "int", filename, path)
            if percent is not None:
                self.in_range(percent, 1, 100, filename, path + ".spare_hp_percent")
            rewards = self.want(row, "rewards", "list", filename, path)
            if rewards is not None:
                for reward_index, reward in enumerate(rewards):
                    reward_path = "%s.rewards[%d]" % (path, reward_index)
                    kind_value = self.want(reward, "kind", "str", filename, reward_path)
                    if kind_value not in ("item", "power", "health"):
                        self.error(filename, reward_path + ".kind", "must be item, power or health")
                        continue
                    if kind_value == "health":
                        amount = self.require(reward, "count", "int", filename, reward_path)
                        if amount is not None:
                            self.in_range(amount, 1, 99, filename, reward_path + ".count")
                        continue
                    table = "item" if kind_value == "item" else "power"
                    self.ref(ids, table, self.want(reward, "id", "str", filename, reward_path),
                             filename, reward_path + ".id")
                    count = self.require(reward, "count", "int", filename, reward_path)
                    if count is not None:
                        self.in_range(count, 1, 99, filename, reward_path + ".count")
            else:
                self.error(filename, path + ".rewards", "missing required field")
            phases = self.want(row, "phases", "list", filename, path)
            if phases is not None:
                self.check_enemy_phases(phases, path, kind, patterns, ids)
            interrupt = self.want(row, "interrupt", "dict", filename, path)
            if interrupt is not None:
                self.check_enemy_interrupts(interrupt, path, kind, percent, ids)
            if isinstance(name, str):
                if name in ids["enemy"] and ids["enemy"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["enemy"][name] = row

    def check_enemy_phases(self, phases, path, kind, pool, ids):
        """Spec 18 section 7 refusals 1 and 2, and the attack band: the phase list is data, so every fault lives here.

        A breakpoint is a percent of max_hp compared in integers (section 8 P3), which is why the range is 1 to 99 and
        not an hp number: halving max_hp in data has to keep every band where it was. Rows are strictly descending and
        at most PHASE_ROWS_MAX. A pattern id must exist in data/patterns/all.json and must not already be in the pool
        above the row, because a crossing that adds a pattern the fight already has draws no change. The attack is
        optional; when a row carries one it must stay inside PHASE_ATTACK_BAND, and the enemy must be a boss, because
        the band spec 07 writes is Percy's.
        """
        filename = "data/enemies/all.json"
        if len(phases) > PHASE_ROWS_MAX:
            self.error(filename, path + ".phases",
                       "%d rows, and spec 18 section 1 allows at most %d" % (len(phases), PHASE_ROWS_MAX))
        above = [pattern_id for pattern_id in (pool or []) if isinstance(pattern_id, str)]
        previous = None
        for phase_index, phase in enumerate(phases):
            where = "%s.phases[%d]" % (path, phase_index)
            if not isinstance(phase, dict):
                self.error(filename, where, "must be an object")
                continue
            threshold = self.require(phase, "hp_at_or_below", "int", filename, where)
            if threshold is not None and self.in_range(threshold, 1, 99, filename, where + ".hp_at_or_below"):
                if previous is not None and threshold >= previous:
                    extra = "; a duplicate threshold" if threshold == previous else ""
                    self.error(filename, where + ".hp_at_or_below",
                               "%d percent is not below the row above it at %d percent, so the crossings are not "
                               "strictly descending%s" % (threshold, previous, extra))
                previous = threshold
            pattern_id = self.require(phase, "pattern_id", "str", filename, where)
            if pattern_id is not None:
                if pattern_id in above:
                    self.error(filename, where + ".pattern_id",
                               "%r is already in the pool above this row, so this crossing would draw no change"
                               % (pattern_id,))
                else:
                    self.ref(ids, "pattern", pattern_id, filename, where + ".pattern_id")
                    above.append(pattern_id)
            attack = self.want(phase, "attack", "dict", filename, where)
            if attack is not None:
                low = self.require(attack, "min", "int", filename, where + ".attack")
                high = self.require(attack, "max", "int", filename, where + ".attack")
                if low is not None and high is not None and low > high:
                    self.error(filename, where + ".attack", "min %s is above max %s" % (low, high))
                if kind != "boss":
                    self.error(filename, where + ".attack",
                               "a phase row may only raise the attack on a route_kind boss, and no spec writes a band "
                               "for a regular enemy")
                band_low, band_high = PHASE_ATTACK_BAND
                for label, value in (("min", low), ("max", high)):
                    if value is not None and (value < band_low or value > band_high):
                        self.error(filename, where + ".attack." + label,
                                   "%s is outside the spec 07 band %s to %s (PHASE_ATTACK_BAND)"
                                   % (value, band_low, band_high))

    def check_enemy_interrupts(self, block, path, kind, spare_percent, ids):
        """Spec 18 section 7 refusals 7 and 8: the interruption is data, so every fault in it lives here.

        A fight may stop with no victory and no defeat and hand a scene the story work (section 4). The trigger is a
        REFUSED SPARE press, not an hp crossing (section 8 A18-1), which is why this block has no breakpoint semantics
        and why refusal 8 matters: a threshold at or below the enemy's spare_hp_percent is dead data, because there
        SPARE is accepted and the interruption can never fire. `scene` is one id or all four route keys, and a partial
        object is refused rather than defaulted, because a default would be a route table hidden in the schema.
        """
        filename = "data/enemies/all.json"
        where = path + ".interrupt"
        if kind != "boss":
            self.error(filename, where,
                       "a fight may only be interrupted on a route_kind boss, and spec 18 section 4 puts the block on "
                       "the enemy row; this enemy is %r" % (kind,))
        trigger = self.require(block, "on", "str", filename, where)
        if trigger is not None and trigger not in INTERRUPT_TRIGGERS:
            self.error(filename, where + ".on",
                       "%r is not in the closed set %s (spec 18 section 4)"
                       % (trigger, sorted(INTERRUPT_TRIGGERS)))
        threshold = self.require(block, "hp_at_or_below", "int", filename, where)
        if threshold is not None and self.in_range(threshold, 1, 99, filename, where + ".hp_at_or_below"):
            if spare_percent is not None and threshold <= spare_percent:
                self.error(filename, where + ".hp_at_or_below",
                           "%d percent is at or below spare_hp_percent %d, where SPARE is accepted, so the story "
                           "exit could never fire (spec 18 section 7 refusal 8)" % (threshold, spare_percent))
        flag_name = self.want(block, "unless_flag", "str", filename, where)
        if flag_name is not None:
            self.ref(ids, "flag", flag_name, filename, where + ".unless_flag")

        scene = block.get("scene") if isinstance(block, dict) else None
        if scene is None:
            self.error(filename, where + ".scene", "missing required field")
        elif isinstance(scene, str):
            self.ref(ids, "scene", scene, filename, where + ".scene")
        elif isinstance(scene, dict):
            missing = [key for key in INTERRUPT_ROUTE_KEYS if key not in scene]
            if missing:
                self.error(filename, where + ".scene",
                           "a per route scene needs all four keys %s and is missing %s; a partial object is an "
                           "error, never a default (spec 18 section 8 A18-4)"
                           % (list(INTERRUPT_ROUTE_KEYS), missing))
            for key in INTERRUPT_ROUTE_KEYS:
                if key in scene:
                    self.ref(ids, "scene", self.want(scene, key, "str", filename, where + ".scene"),
                             filename, where + ".scene." + key)
        else:
            self.error(filename, where + ".scene",
                       "must be a scene id or an object with the four route keys %s"
                       % (list(INTERRUPT_ROUTE_KEYS),))

    def check_phase_talk(self, data, ids):
        """The two talk names a phase crossing carries, one meaning each (spec 16 section 10, card t_155e22e2).

        A phase row names the choice lines the TALK command draws from the crossing on in `talk_set`, which is a
        dialogue id in data/dialogue/all.json, and it names the personality card the director swaps in with
        `talk_phase`, which is a card's `phase` value in data/talk_cards.json. Two namespaces, so neither name may be
        read as the other: `talk_set` must resolve to a dialogue row, and `talk_phase` must resolve to exactly one card
        whose enemy is this enemy. The reverse is checked as well, because a phase card no row names is a card the
        fight can never reach, which is the drift this card was opened to stop.
        """
        filename = "data/enemies/all.json"
        cards_file = "data/talk_cards.json"
        document = self.files.get("talk_cards.json") if isinstance(self.files, dict) else None
        cards = document.get("cards") if isinstance(document, dict) else None

        # The phase cards, by the pair the director matches on: the enemy id and the card's own phase string.
        by_phase: dict[tuple[str, str], list[int]] = {}
        if isinstance(cards, list):
            for index, card in enumerate(cards):
                if not isinstance(card, dict):
                    continue
                enemy = card.get("enemy")
                phase = card.get("phase")
                if isinstance(enemy, str) and isinstance(phase, str) and phase != "":
                    by_phase.setdefault((enemy, phase), []).append(index)

        enemies = data.get("enemies") if isinstance(data, dict) else None
        if not isinstance(enemies, list):
            return
        named: set[tuple[str, str]] = set()
        for index, row in enumerate(enemies):
            if not isinstance(row, dict):
                continue
            enemy_id = row.get("id")
            if not isinstance(enemy_id, str):
                continue
            phases = row.get("phases")
            if not isinstance(phases, list):
                continue
            for phase_index, phase in enumerate(phases):
                if not isinstance(phase, dict):
                    continue
                phase_path = "enemies[%d].phases[%d]" % (index, phase_index)
                self.ref(ids, "dialogue", self.want(phase, "talk_set", "str", filename, phase_path),
                         filename, phase_path + ".talk_set")
                self.ref(ids, "dialogue", self.want(phase, "line_id", "str", filename, phase_path),
                         filename, phase_path + ".line_id")
                if "talk_phase" not in phase:
                    continue
                talk_phase = self.require(phase, "talk_phase", "str", filename, phase_path)
                if not isinstance(talk_phase, str) or talk_phase == "":
                    continue
                found = by_phase.get((enemy_id, talk_phase), [])
                if len(found) == 1:
                    named.add((enemy_id, talk_phase))
                elif not found:
                    self.error(filename, phase_path + ".talk_phase",
                               "no talk card in %s has enemy %r and phase %r, so the crossing would keep the base card"
                               % (cards_file, enemy_id, talk_phase))
                else:
                    self.error(filename, phase_path + ".talk_phase",
                               "%d talk cards in %s claim enemy %r and phase %r"
                               % (len(found), cards_file, enemy_id, talk_phase))

        # A phase card is reachable only through a phase row of its own enemy. Cards for enemies that live only in
        # data/enemies/roster.json are exempt: those enemies have no phase rows, so they have no crossing to reach.
        for (enemy_id, talk_phase), indexes in sorted(by_phase.items()):
            if enemy_id not in ids.get("enemy", {}):
                continue
            if (enemy_id, talk_phase) in named:
                continue
            self.error(cards_file, "cards[%d].phase" % indexes[0],
                       "no phase row in %s names talk_phase %r for enemy %r, so this phase card is unreachable"
                       % (filename, talk_phase, enemy_id))

    def check_patterns(self, data, ids):
        filename = "data/patterns/all.json"
        if not self.check_header(data, "patterns", filename):
            return
        rows = self.require(data, "patterns", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "patterns[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            shape = self.require(row, "shape", "str", filename, path)
            if shape is not None and shape not in PATTERN_SHAPES:
                self.error(filename, path + ".shape", "must be one of %s" % sorted(PATTERN_SHAPES))
            length = self.require(row, "length", "int", filename, path)
            if length is not None:
                self.in_range(length, 1, ARENA_CAP, filename, path + ".length")
            aim = self.require(row, "aim", "str", filename, path)
            if aim is not None and aim not in PATTERN_AIM:
                self.error(filename, path + ".aim", "must be fixed or at_marker (spec delta T11)")
            concurrent = self.require(row, "max_concurrent", "int", filename, path)
            if concurrent is not None:
                self.in_range(concurrent, 1, 4, filename, path + ".max_concurrent")
                if concurrent > 4:
                    self.error(filename, path + ".max_concurrent", "above 4 needs a fairness_note (spec 09 rule 6)")

            frames = self.require(row, "frames", "list", filename, path)
            if frames is None:
                continue
            if len(frames) == 0:
                self.error(filename, path + ".frames", "a pattern needs at least one frame")
            for frame_index, frame in enumerate(frames):
                frame_path = "%s.frames[%d]" % (path, frame_index)
                if not isinstance(frame, dict):
                    self.error(filename, frame_path, "must be an object")
                    continue
                for field_name, (low, high) in PATTERN_FIELD_RANGES.items():
                    value = self.require(frame, field_name, "num", filename, frame_path)
                    if value is not None:
                        self.in_range(value, low, high, filename, "%s.%s" % (frame_path, field_name))
                size = frame.get("size")
                if isinstance(size, int) and size not in (8, 16):
                    self.error(filename, frame_path + ".size", "must be 8 or 16 (spec 08)")
                origin = frame.get("origin")
                if isinstance(origin, str):
                    if origin not in ORIGIN_NAMES:
                        self.error(filename, frame_path + ".origin",
                                   "must be one of %s or an {x, y} object" % sorted(ORIGIN_NAMES))
                elif isinstance(origin, dict):
                    for axis in ("x", "y"):
                        if axis not in origin or not isinstance(origin[axis], (int, float)):
                            self.error(filename, frame_path + ".origin", "needs numeric x and y")
                    if isinstance(origin.get("x"), (int, float)):
                        self.in_range(origin.get("x"), 0, FRAME_W, filename, frame_path + ".origin.x")
                    if isinstance(origin.get("y"), (int, float)):
                        self.in_range(origin.get("y"), 0, FRAME_H, filename, frame_path + ".origin.y")
                else:
                    self.error(filename, frame_path + ".origin", "missing")

                wobble = self.require(frame, "wobble", "dict", filename, frame_path)
                if wobble is not None:
                    for field_name, (low, high) in WOBBLE_RANGES.items():
                        value = self.require(wobble, field_name, "num", filename, frame_path + ".wobble")
                        if value is not None:
                            self.in_range(value, low, high, filename, "%s.wobble.%s" % (frame_path, field_name))

                # A spawn must sit inside the pattern's own length.
                at = frame.get("at")
                delay = frame.get("delay", 0)
                count = frame.get("count", 1)
                if isinstance(at, int) and isinstance(delay, (int, float)) and isinstance(count, int):
                    if length is not None and at + (count - 1) * delay >= length:
                        self.error(filename, frame_path,
                                   "last spawn at step %s is at or past the pattern length %s"
                                   % (at + (count - 1) * delay, length))

            if isinstance(name, str):
                if name in ids["pattern"] and ids["pattern"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["pattern"][name] = row

    def check_encounters(self, data, ids):
        filename = "data/encounters/all.json"
        if not self.check_header(data, "encounters", filename):
            return
        rows = self.require(data, "encounters", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "encounters[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            enemies = self.require(row, "enemies", "list", filename, path)
            if enemies is not None:
                if len(enemies) == 0:
                    self.error(filename, path + ".enemies", "needs at least one enemy")
                if len(enemies) > 1:
                    self.error(filename, path + ".enemies",
                               "more than one enemy is out of scope for this slice (spec 07)")
                for enemy_index, enemy_id in enumerate(enemies):
                    self.ref(ids, "enemy", enemy_id, filename, "%s.enemies[%d]" % (path, enemy_index))
            seed = self.require(row, "seed", "int", filename, path)
            if seed is not None:
                self.in_range(seed, 0, 2 ** 31 - 1, filename, path + ".seed")
            music = self.want(row, "music", "str", filename, path)
            if music is not None:
                self.check_music_ref(ids, music, filename, path + ".music")
            for field_name in ("intro_dialogue", "win_dialogue_kill", "win_dialogue_spare", "lose_dialogue"):
                self.ref(ids, "dialogue", self.want(row, field_name, "str", filename, path),
                         filename, path + "." + field_name)
            trust = self.require(row, "trust_per_talk", "int", filename, path)
            if trust is not None:
                self.in_range(trust, 1, 5, filename, path + ".trust_per_talk")
            # Spec 18 section 7 refusal 10, delta C18-7: the enemy row owns the interrupt block, so a copy on the
            # encounter row is two copies of one fact, and the copy no code reads is the one that drifts. It is
            # refused by name rather than ignored, because a field the checker passes in silence reads like a feature
            # to whoever finds it in the data (card t_905a18ce F3).
            if "interrupt" in row:
                self.error(filename, path + ".interrupt",
                           "is refused on an encounter row: spec 18 section 7 refusal 10 puts the interrupt block on "
                           "the enemy row, which is the row pp_battle_interrupt_block reads")
            for flag_field in ("flags_on_kill", "flags_on_spare"):
                flags = self.want(row, flag_field, "list", filename, path)
                if not isinstance(flags, list):
                    self.error(filename, path + "." + flag_field, "missing required field")
                    continue
                for flag_index, flag_name in enumerate(flags):
                    self.ref(ids, "flag", flag_name, filename, "%s.%s[%d]" % (path, flag_field, flag_index))
            if isinstance(name, str):
                if name in ids["encounter"] and ids["encounter"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["encounter"][name] = row

    def check_maps(self, data, ids, filename="data/maps/all.json"):
        if not self.check_header(data, "maps", filename):
            return
        tile_size = self.require(data, "tile_size", "int", filename, "")
        rows = self.require(data, "maps", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "maps[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            # Every room names the palette set it draws with, and an unknown set is a room that would draw in the
            # fallback palette with no error at all, which is why it is a checker error here (spec 13).
            room_palette = self.require(row, "room_palette", "str", filename, path)
            if isinstance(room_palette, str) and self.room_palette_ids:
                if room_palette not in self.room_palette_ids:
                    self.error(filename, path + ".room_palette",
                               "names %r, which is not a set in data/room_palettes.json" % room_palette)
            width = self.require(row, "width", "int", filename, path)
            height = self.require(row, "height", "int", filename, path)
            if isinstance(name, str):
                if name in ids["map"] and ids["map"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["map"][name] = row

            legend = self.require(row, "tile_legend", "dict", filename, path)
            tiles = self.require(row, "tiles", "list", filename, path)
            collision = self.require(row, "collision", "list", filename, path)

            for grid_name, grid in (("tiles", tiles), ("collision", collision)):
                if grid is None:
                    continue
                if height is not None and len(grid) != height:
                    self.error(filename, "%s.%s" % (path, grid_name),
                               "has %d rows, the map height is %d" % (len(grid), height))
                for row_index, line in enumerate(grid):
                    if not isinstance(line, str):
                        self.error(filename, "%s.%s[%d]" % (path, grid_name, row_index), "must be a string")
                        continue
                    if width is not None and len(line) != width:
                        self.error(filename, "%s.%s[%d]" % (path, grid_name, row_index),
                                   "is %d characters, the map width is %d" % (len(line), width))
                    if grid_name == "collision":
                        if set(line) - set("012"):
                            self.error(filename, "%s.collision[%d]" % (path, row_index),
                                       "may only contain 0 (walkable), 1 (blocked) and 2 (story blocked)")
                    elif legend:
                        for char in line:
                            if char not in legend:
                                self.error(filename, "%s.tiles[%d]" % (path, row_index),
                                           "character %r is not in tile_legend" % char)
                                break

            palette_indices = self.require(row, "palette_indices", "list", filename, path)
            if palette_indices is not None:
                if len(palette_indices) > MAX_COLOURS_ON_SCREEN:
                    self.error(filename, path + ".palette_indices",
                               "%d colours, the on screen limit is %d (spec 13)" % (len(palette_indices),
                                                                                    MAX_COLOURS_ON_SCREEN))
                for colour_index, value in enumerate(palette_indices):
                    if not isinstance(value, int) or not (0 <= value < PALETTE_SIZE):
                        self.error(filename, "%s.palette_indices[%d]" % (path, colour_index),
                                   "must be an index below %d" % PALETTE_SIZE)

            music = self.want(row, "music", "str", filename, path)
            if music is not None:
                self.check_music_ref(ids, music, filename, path + ".music")

            story_flag = self.want(row, "story_flag", "str", filename, path)
            if story_flag:
                self.ref(ids, "flag", story_flag, filename, path + ".story_flag")
                if isinstance(collision, list) and not any("2" in line for line in collision if isinstance(line, str)):
                    self.error(filename, path + ".story_flag",
                               "names a flag but no tile is story blocked, so the flag would do nothing")

            spawns = self.require(row, "spawns", "dict", filename, path)
            if spawns is not None:
                for spawn_name, point in spawns.items():
                    spawn_path = "%s.spawns.%s" % (path, spawn_name)
                    if not isinstance(point, dict):
                        self.error(filename, spawn_path, "must be an object with x and y")
                        continue
                    self.check_tile_point(point, width, height, filename, spawn_path)
                    if collision is not None:
                        self.check_walkable(point, collision, filename, spawn_path, "spawn")

            triggers = self.want(row, "triggers", "list", filename, path)
            if triggers is None:
                self.error(filename, path + ".triggers", "missing required field")
            else:
                # Card TRIGGER-TILE-RULE: one trigger per tile, per map. pp_map_trigger_at returns the FIRST row
                # with that tile, so a second row there is data no walker can ever reach: a dead trigger rather
                # than a second effect. The tile is compared per map row, because a trigger only exists inside
                # the map it is written on. The style is the same object-with-x-and-y every other trigger check
                # uses; the path names both x and y so the report points at the pair and not at one coordinate.
                seen_trigger_tiles = {}
                for trigger_index, trigger in enumerate(triggers):
                    trigger_path = "%s.triggers[%d]" % (path, trigger_index)
                    self.check_tile_point(trigger, width, height, filename, trigger_path)
                    if isinstance(trigger, dict):
                        tile_x, tile_y = trigger.get("x"), trigger.get("y")
                        if isinstance(tile_x, int) and isinstance(tile_y, int):
                            first_row = seen_trigger_tiles.get((tile_x, tile_y))
                            if first_row is None:
                                seen_trigger_tiles[(tile_x, tile_y)] = (
                                    trigger_index, trigger.get("kind"), trigger.get("id"))
                            else:
                                self.error(filename, trigger_path + ".x/y",
                                           "tile (%d,%d) already carries %s trigger %r (triggers[%d])"
                                           % (tile_x, tile_y, first_row[1], first_row[2], first_row[0]))
                    kind = self.want(trigger, "kind", "str", filename, trigger_path)
                    target = self.want(trigger, "id", "str", filename, trigger_path)
                    if kind not in TRIGGER_KINDS:
                        self.error(filename, trigger_path + ".kind", "must be one of %s" % sorted(TRIGGER_KINDS))
                    else:
                        table = TRIGGER_ID_TABLES.get(kind)
                        if table is not None:
                            self.ref(ids, table, target, filename, trigger_path + ".id")
                    once = self.require(trigger, "once", "bool", filename, trigger_path)
                    del once
                    condition = self.want(trigger, "condition", "str", filename, trigger_path)
                    if condition:
                        self.ref(ids, "flag", condition, filename, trigger_path + ".condition")
                    if kind == "map":
                        entry_spawn = self.want(trigger, "spawn", "str", filename, trigger_path)
                        if entry_spawn is None:
                            self.error(filename, trigger_path + ".spawn",
                                       "a map trigger must name the spawn point to arrive at")
                        else:
                            destination = ids["map"].get(target) if isinstance(target, str) else None
                            if isinstance(destination, dict):
                                points = destination.get("spawns", {})
                                if not isinstance(points, dict) or entry_spawn not in points:
                                    self.error(filename, trigger_path + ".spawn",
                                               "%r is not a spawn point of map %r" % (entry_spawn, target))

            actors = self.want(row, "actors", "list", filename, path)
            if actors is not None:
                seen_actors = set()
                for actor_index, actor in enumerate(actors):
                    actor_path = "%s.actors[%d]" % (path, actor_index)
                    self.check_tile_point(actor, width, height, filename, actor_path)
                    if collision is not None:
                        self.check_walkable(actor, collision, filename, actor_path, "actor")
                    actor_id = self.require(actor, "id", "str", filename, actor_path)
                    if isinstance(actor_id, str):
                        if actor_id in seen_actors:
                            self.error(filename, actor_path + ".id", "duplicate actor id %r on this map" % actor_id)
                        seen_actors.add(actor_id)
                    facing = self.require(actor, "facing", "str", filename, actor_path)
                    if isinstance(facing, str) and facing not in ("up", "down", "left", "right"):
                        self.error(filename, actor_path + ".facing", "must be up, down, left or right")
                    self.ref(ids, "dialogue", self.require(actor, "dialogue", "str", filename, actor_path),
                             filename, actor_path + ".dialogue")

            if tile_size is not None and isinstance(width, int):
                span = width * tile_size
                if span < FRAME_W:
                    self.error(filename, path + ".width", "map is %d px wide, narrower than the %d px frame"
                               % (span, FRAME_W))

        # Rails are per map and each rail step must land on a walkable tile (spec 04, no soft lock).
        for index, row in enumerate(rows):
            path = "maps[%d]" % index
            rails = self.want(row, "rails", "list", filename, path)
            if rails is None:
                continue
            collision = row.get("collision") if isinstance(row, dict) else None
            spawns = row.get("spawns", {}) if isinstance(row, dict) else {}
            for rail_index, rail in enumerate(rails):
                rail_path = "%s.rails[%d]" % (path, rail_index)
                start = self.want(rail, "start", "dict", filename, rail_path)
                steps = self.want(rail, "steps", "list", filename, rail_path)
                if isinstance(start, dict) and isinstance(steps, list) and isinstance(collision, list):
                    self.walk_rail(start, steps, collision, filename, rail_path)
                elif start is None and spawns:
                    self.error(filename, rail_path + ".start", "missing required field")

    def walk_rail(self, start, steps, collision, filename, path):
        x, y = start.get("x"), start.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            self.error(filename, path + ".start", "needs integer x and y")
            return
        for step_index, step in enumerate(steps):
            direction = self.want(step, "dir", "str", filename, "%s.steps[%d]" % (path, step_index))
            count = self.want(step, "tiles", "int", filename, "%s.steps[%d]" % (path, step_index))
            if direction not in DIRECTIONS or not isinstance(count, int):
                self.error(filename, "%s.steps[%d]" % (path, step_index), "needs dir and tiles")
                continue
            for _ in range(count):
                if direction == "up":
                    y -= 1
                elif direction == "down":
                    y += 1
                elif direction == "left":
                    x -= 1
                else:
                    x += 1
                if not (0 <= y < len(collision) and 0 <= x < len(collision[y])):
                    self.error(filename, "%s.steps[%d]" % (path, step_index), "walks off the map")
                    return
                if collision[y][x] != "0":
                    self.error(filename, "%s.steps[%d]" % (path, step_index),
                               "walks into a blocked tile at %d, %d" % (x, y))
                    return

    def check_tile_point(self, point, width, height, filename, path):
        if not isinstance(point, dict):
            self.error(filename, path, "must be an object with x and y")
            return
        x = self.want(point, "x", "int", filename, path)
        y = self.want(point, "y", "int", filename, path)
        if x is None or y is None:
            self.error(filename, path, "needs integer x and y")
            return
        if isinstance(width, int) and not (0 <= x < width):
            self.error(filename, path + ".x", "%s is outside the map width %s" % (x, width))
        if isinstance(height, int) and not (0 <= y < height):
            self.error(filename, path + ".y", "%s is outside the map height %s" % (y, height))

    def check_walkable(self, point, collision, filename, path, label):
        x, y = point.get("x"), point.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return
        if not (0 <= y < len(collision)) or not (0 <= x < len(collision[y])):
            return
        if collision[y][x] != "0":
            self.error(filename, path, "%s sits on a blocked tile (%s)" % (label, collision[y][x]))

    def check_scenes(self, data, ids):
        filename = "data/scenes/all.json"
        if not self.check_header(data, "scenes", filename):
            return
        rows = self.require(data, "scenes", "list", filename, "")
        if rows is None:
            return
        for index, row in enumerate(rows):
            path = "scenes[%d]" % index
            name = self.require(row, "id", "str", filename, path)
            self.require(row, "name", "str", filename, path)
            if isinstance(name, str):
                if name in ids["scene"] and ids["scene"][name] is not row:
                    self.error(filename, path + ".id", "duplicate id %r" % name)
                ids["scene"][name] = row
            map_name = self.require(row, "map", "str", filename, path)
            self.ref(ids, "map", map_name, filename, path + ".map")
            start = self.require(row, "start", "dict", filename, path)
            if start is not None:
                self.check_tile_point(start, None, None, filename, path + ".start")

            commands = self.require(row, "commands", "list", filename, path)
            if commands is None:
                continue
            if len(commands) == 0:
                self.error(filename, path + ".commands", "a scene needs at least one command")
            if len(commands) > 256:
                self.error(filename, path + ".commands",
                           "%d commands, over the 256 limit; split the scene (spec 06)" % len(commands))
            if commands and isinstance(commands[-1], dict) and commands[-1].get("cmd") != "end":
                self.error(filename, "%s.commands[%d]" % (path, len(commands) - 1),
                           "a scene must end with the end command (spec 06 rule 6)")

            battle_seen = False
            for command_index, command in enumerate(commands):
                command_path = "%s.commands[%d]" % (path, command_index)
                cmd = self.want(command, "cmd", "str", filename, command_path)
                if cmd not in SCENE_COMMANDS:
                    self.error(filename, command_path + ".cmd", "unknown command %r" % (cmd,))
                    continue
                if cmd == "say":
                    self.ref(ids, "dialogue", self.want(command, "id", "str", filename, command_path),
                             filename, command_path + ".id")
                elif cmd in ("music", "sfx"):
                    if cmd == "music":
                        # A scene asks for music by cue id or by sound id; both resolve, a typo does not.
                        self.check_music_ref(ids, self.want(command, "id", "str", filename, command_path),
                                             filename, command_path + ".id")
                    else:
                        self.ref(ids, "sound", self.want(command, "id", "str", filename, command_path),
                                 filename, command_path + ".id")
                elif cmd == "move":
                    direction = self.want(command, "dir", "str", filename, command_path)
                    if direction not in DIRECTIONS:
                        self.error(filename, command_path + ".dir", "must be one of %s" % sorted(DIRECTIONS))
                    tiles = self.want(command, "tiles", "int", filename, command_path)
                    if tiles is not None:
                        self.in_range(tiles, 1, 8, filename, command_path + ".tiles")
                elif cmd == "wait":
                    steps = self.want(command, "steps", "int", filename, command_path)
                    if steps is not None:
                        self.in_range(steps, 0, 600, filename, command_path + ".steps")
                elif cmd == "fade":
                    mode = self.want(command, "mode", "str", filename, command_path)
                    if mode not in ("out", "in"):
                        self.error(filename, command_path + ".mode", "must be out or in")
                elif cmd == "setflag":
                    self.ref(ids, "flag", self.want(command, "name", "str", filename, command_path),
                             filename, command_path + ".name")
                elif cmd == "branch":
                    self.ref(ids, "flag", self.want(command, "flag", "str", filename, command_path),
                             filename, command_path + ".flag")
                    self.ref(ids, "scene", self.want(command, "scene", "str", filename, command_path),
                             filename, command_path + ".scene")
                elif cmd == "battle":
                    battle_seen = True
                    self.ref(ids, "encounter", self.want(command, "id", "str", filename, command_path),
                             filename, command_path + ".id")
                elif cmd == "spawn":
                    self.require(command, "actor", "str", filename, command_path)
                    for axis in ("x", "y"):
                        value = self.want(command, axis, "int", filename, command_path)
                        if value is not None:
                            self.in_range(value, 0, 999, filename, command_path + "." + axis)
                elif cmd == "destroy":
                    self.require(command, "actor", "str", filename, command_path)
                elif cmd == "shake":
                    steps = self.want(command, "steps", "int", filename, command_path)
                    if steps is not None:
                        self.in_range(steps, 1, 60, filename, command_path + ".steps")
                    strength = self.want(command, "strength", "int", filename, command_path)
                    if strength is not None:
                        self.in_range(strength, 1, 2, filename, command_path + ".strength")
                elif cmd == "flash":
                    # A flash floods the frame in one role for a handful of frames and costs the scene no steps, so
                    # there is nothing here about durations: only that the frames and the colour are real (card
                    # t_531bc76c, spec 06). The role is judged against the set the room this scene plays in declares,
                    # not against the whole master palette, because a role the set does not carry draws as the
                    # missing colour and that is a screen no palette of the set can produce (spec 13 rule 2).
                    steps = self.want(command, "steps", "int", filename, command_path)
                    if steps is not None:
                        self.in_range(steps, 1, 8, filename, command_path + ".steps")
                    role = self.want(command, "role", "str", filename, command_path)
                    if role is not None:
                        map_row = ids["map"].get(map_name) if isinstance(map_name, str) else None
                        room_palette = map_row.get("room_palette") if isinstance(map_row, dict) else None
                        declared = self.room_palette_roles.get(room_palette, []) if isinstance(room_palette, str) else []
                        if declared and role not in declared:
                            self.error(filename, command_path + ".role",
                                       "%r is not a role in %r, the set %r declares; a flash may only spend a colour "
                                       "the room already draws with" % (role, room_palette, map_name))
            del battle_seen

        # branch is the only control flow, so a cycle of branches would be a cutscene that never ends (spec 06 rule 3).
        edges = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                continue
            targets = []
            commands = row.get("commands")
            if isinstance(commands, list):
                for command in commands:
                    if isinstance(command, dict) and command.get("cmd") == "branch":
                        target = command.get("scene")
                        if isinstance(target, str):
                            targets.append(target)
            edges[row["id"]] = targets

        state = {}

        def visit(node, trail):
            mark = state.get(node, 0)
            if mark == 1:
                self.error(filename, "scenes", "branch cycle: %s" % " -> ".join(trail + [node]))
                return
            if mark == 2:
                return
            state[node] = 1
            for target in edges.get(node, []):
                visit(target, trail + [node])
            state[node] = 2

        for scene_id in edges:
            visit(scene_id, [])

        # Scene moves are checked against the map's collision grid, because a rail that walks into a wall is a soft lock.
        map_cache = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            map_name = row.get("map")
            start = row.get("start")
            commands = row.get("commands")
            if not (isinstance(map_name, str) and isinstance(start, dict) and isinstance(commands, list)):
                continue
            if map_name not in map_cache:
                map_row = ids["map"].get(map_name)
                map_cache[map_name] = map_row.get("collision") if isinstance(map_row, dict) else None
            collision = map_cache[map_name]
            if not isinstance(collision, list):
                continue
            x, y = start.get("x"), start.get("y")
            if not isinstance(x, int) or not isinstance(y, int):
                continue
            for command_index, command in enumerate(commands):
                if not isinstance(command, dict) or command.get("cmd") != "move":
                    continue
                direction = command.get("dir")
                count = command.get("tiles")
                if direction not in DIRECTIONS or not isinstance(count, int):
                    continue
                for _ in range(count):
                    if direction == "up":
                        y -= 1
                    elif direction == "down":
                        y += 1
                    elif direction == "left":
                        x -= 1
                    else:
                        x += 1
                    if not (0 <= y < len(collision)) or not (0 <= x < len(collision[y])):
                        self.error(filename, "%s.commands[%d]" % ("scenes[%d]" % index, command_index),
                                   "walks off the map")
                        break
                    if collision[y][x] != "0":
                        self.error(filename, "%s.commands[%d]" % ("scenes[%d]" % index, command_index),
                                   "walks into a blocked tile at %d, %d" % (x, y))
                        break

    def check_slice(self, data, ids):
        filename = "data/slice.json"
        if not self.check_header(data, "slice", filename):
            return
        map_name = self.require(data, "map", "str", filename, "")
        spawn = self.require(data, "spawn", "str", filename, "")
        self.ref(ids, "scene", self.require(data, "scene", "str", filename, ""), filename, "scene")
        self.ref(ids, "encounter", self.require(data, "encounter", "str", filename, ""), filename, "encounter")
        map_row = self.ref(ids, "map", map_name, filename, "map")
        if isinstance(map_row, dict):
            spawns = map_row.get("spawns", {})
            if isinstance(spawns, dict) and spawn not in spawns:
                self.error(filename, "spawn", "map %r has no spawn named %r" % (map_name, spawn))


# ---------------------------------------------------------------------------------------------------------------
# Pattern simulation: a second implementation of pp_dodge_recipe.gml and pp_dodge_arena.gml.


def rng_new(seed: int) -> list[int]:
    return [(seed % 4294967296)]


def rng_next(state: list[int]) -> float:
    state[0] = (state[0] * 1664525 + 1013904223) % 4294967296
    return state[0] / 4294967296


def rng_range(state, low, high):
    return low + (high - low) * rng_next(state)


def rng_int(state, low, high):
    if high <= low:
        return low
    return low + int(rng_next(state) * ((high - low) + 1))


def lengthdir_x(length, direction):
    import math
    return length * math.cos(math.radians(direction))


def lengthdir_y(length, direction):
    """GameMaker directions run 0 right, 90 up, 180 left, 270 down, and positive y is down, so the y component is the
    NEGATED sine. This mirrors the engine, not the screen convention a data recipe is written in."""
    import math
    return -length * math.sin(math.radians(direction))


def point_distance(x1, y1, x2, y2):
    import math
    return math.hypot(x2 - x1, y2 - y1)


def point_direction(x1, y1, x2, y2):
    """The GameMaker direction from one point to another: the mirrored cosine/sine of lengthdir, so also negated."""
    import math
    return math.degrees(math.atan2(-(y2 - y1), x2 - x1)) % 360.0


def angle_to_gm(data_angle):
    """Mirror of pp_angle_to_gm in pp_dodge_arena.gml. A data recipe angle is a screen angle (0 right, 90 down,
    clockwise); a GameMaker direction is the mirror of it. Every data degree passes through here once, at spawn."""
    return (360 - (data_angle % 360)) % 360


def origin_point(origin, rng, size):
    if isinstance(origin, dict):
        return origin["x"], origin["y"]
    if origin == "top":
        return rng_range(rng, ARENA_X1, ARENA_X2), ARENA_Y1 - size
    if origin == "bottom":
        return rng_range(rng, ARENA_X1, ARENA_X2), ARENA_Y2 + size
    if origin == "left":
        return ARENA_X1 - size, rng_range(rng, ARENA_Y1, ARENA_Y2)
    if origin == "right":
        return ARENA_X2 + size, rng_range(rng, ARENA_Y1, ARENA_Y2)
    if origin == "centre":
        return ARENA_CX, ARENA_CY
    corners = [
        (ARENA_X1 - size, ARENA_Y1 - size),
        (ARENA_X2 + size, ARENA_Y1 - size),
        (ARENA_X1 - size, ARENA_Y2 + size),
        (ARENA_X2 + size, ARENA_Y2 + size),
    ]
    return corners[rng_int(rng, 0, 3)]


def fit_spawn(x, y, size, marker_x, marker_y):
    hx, hy = x + size / 2, y + size / 2
    distance = point_distance(marker_x, marker_y, hx, hy)
    if distance >= SPAWN_EXCLUSION:
        return x, y
    if distance < 0.001:
        return x, y - SPAWN_EXCLUSION
    direction = point_direction(marker_x, marker_y, hx, hy)
    return (marker_x + lengthdir_x(SPAWN_EXCLUSION, direction) - size / 2,
            marker_y + lengthdir_y(SPAWN_EXCLUSION, direction) - size / 2)


def simulate(pattern: dict, seed: int = 1, trace: bool = False) -> dict:
    """Run one recipe with the marker parked at the arena centre and report what happened.

    The movement maths is the engine's: a data angle is mirrored once by angle_to_gm (or read straight from the marker
    for an aimed frame), a data curve is negated, and both then move through lengthdir, whose y component is negative
    because a GameMaker direction of 90 points up. With trace on, the result also carries one position list per hazard,
    in spawn order, so a test can assert where a hazard actually went.
    """
    rng = rng_new(seed)
    events = []
    for frame in pattern["frames"]:
        for member in range(frame["count"]):
            angle = frame["angle"]
            if frame["count"] > 1:
                t = member / (frame["count"] - 1)
                angle += (t - 0.5) * frame["spread"]
            events.append({
                "at": frame["at"] + member * frame["delay"],
                "angle": angle,
                "speed": frame["speed"],
                "accel": frame["accel"],
                "curve": frame["curve"],
                "life": frame["life"],
                "size": frame["size"],
                "origin": frame["origin"],
                "jitter": frame["jitter_angle"],
                "wobble_amp": frame["wobble"]["amp"],
                "wobble_period": frame["wobble"]["period"],
                # pp_dodge_recipe.gml honours a per frame aim as well as the pattern level one; so must this mirror.
                "aim": pattern["aim"] == "at_marker" or frame.get("aim") is True,
                "index": member,
            })
    events.sort(key=lambda e: (e["at"], e["index"]))

    marker_x, marker_y = float(ARENA_CX), float(ARENA_CY)
    hazards = []
    paths: list[list[tuple[float, float]]] = []
    cursor = 0
    peak = 0
    exclusion_violations = 0
    spawns = 0
    elapsed = 0
    finished = False
    length = pattern["length"]

    while elapsed < ARENA_CAP:
        while cursor < len(events) and events[cursor]["at"] <= elapsed:
            event = events[cursor]
            cursor += 1
            px, py = origin_point(event["origin"], rng, event["size"])
            direction = angle_to_gm(event["angle"])
            if event["aim"]:
                direction = point_direction(px, py, marker_x, marker_y)
            if event["jitter"] > 0:
                direction += rng_range(rng, -event["jitter"], event["jitter"])
            px, py = fit_spawn(px, py, event["size"], marker_x, marker_y)
            if point_distance(marker_x, marker_y,
                              px + event["size"] / 2, py + event["size"] / 2) < SPAWN_EXCLUSION - 0.01:
                exclusion_violations += 1
            hazards.append({
                "x": px, "y": py, "dir": direction, "speed": event["speed"],
                "accel": event["accel"], "curve": -event["curve"], "life": event["life"],
                "age": 0, "size": event["size"], "alive": True, "outside": 0, "path": len(paths),
            })
            paths.append([(px, py)])
            spawns += 1

        alive = []
        for hazard in hazards:
            if not hazard["alive"]:
                continue
            hazard["speed"] = max(0, hazard["speed"] + hazard["accel"])
            hazard["dir"] += hazard["curve"]
            hazard["x"] += lengthdir_x(hazard["speed"], hazard["dir"])
            hazard["y"] += lengthdir_y(hazard["speed"], hazard["dir"])
            hazard["age"] += 1
            paths[hazard["path"]].append((hazard["x"], hazard["y"]))
            outside = (hazard["x"] + hazard["size"] < ARENA_X1 or hazard["x"] > ARENA_X2
                       or hazard["y"] + hazard["size"] < ARENA_Y1 or hazard["y"] > ARENA_Y2)
            hazard["outside"] = hazard["outside"] + 1 if outside else 0
            if hazard["age"] >= hazard["life"] or hazard["outside"] > 12:
                hazard["alive"] = False
                continue
            alive.append(hazard)
        hazards = alive
        peak = max(peak, len(hazards))

        elapsed += 1
        if elapsed >= length and cursor >= len(events) and not hazards:
            finished = True
            break

    result = {
        "spawns": spawns,
        "peak": peak,
        "exclusion_violations": exclusion_violations,
        "finished": finished,
        "steps": elapsed,
    }
    if trace:
        result["paths"] = paths
    return result


def check_simulations(checker: Checker) -> None:
    data = checker.files.get("patterns/all.json")
    if not isinstance(data, dict):
        return
    filename = "data/patterns/all.json"
    for index, pattern in enumerate(data.get("patterns", [])):
        path = "patterns[%d]" % index
        if not isinstance(pattern, dict) or "frames" not in pattern:
            continue
        try:
            result = simulate(pattern)
        except (KeyError, TypeError, ZeroDivisionError) as exc:
            checker.error(filename, path, "simulation failed: %s" % exc)
            continue
        if result["exclusion_violations"] > 0:
            checker.error(filename, path, "%d spawns landed inside the %d px exclusion radius"
                           % (result["exclusion_violations"], SPAWN_EXCLUSION))
        if not result["finished"]:
            checker.error(filename, path, "does not end inside the %d step cap (spec 08 rule 5)" % ARENA_CAP)
        declared = pattern.get("max_concurrent")
        if isinstance(declared, int) and result["peak"] > declared:
            checker.error(filename, path, "peak %d concurrent hazards exceeds declared max_concurrent %d"
                           % (result["peak"], declared))


# ---------------------------------------------------------------------------------------------------------------


def check(root: str) -> list[str]:
    checker = Checker(root)
    checker.dangling = {}
    schema_problems = schema_failures(root)
    checker.errors.extend(schema_problems)
    errors = checker.run()
    check_simulations(checker)
    return checker.errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    errors = check(args.root)
    if errors:
        for line in errors:
            print("FAIL " + line)
        print("\n%d problem(s) in %d file(s)" % (len(errors), len({e.split(":")[0] for e in errors})))
        return 1

    counted = len([name for name in os.listdir(os.path.join(args.root, "data")) if name.endswith(".json")])
    print("check_data: all files pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
