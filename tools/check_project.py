"""Check the GameMaker project graph: the .yyp, every .yy, and the folders on disk must agree.

This is the check that catches the class of mistake that stops a project opening: a resource listed in the .yyp that
does not exist, a .gml event file with no matching entry in its object's eventList, an instance pointing at an object
that is not there, a script folder whose name and file name disagree.

Run it after adding or renaming anything under game\\.

Usage:
    python tools/check_project.py
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
PROJECT = os.path.join(GAME, "PrimordialParadox.yyp")

EVENT_PATTERNS = [
    (re.compile(r"^Create_(\d+)$"), 0),
    (re.compile(r"^Destroy_(\d+)$"), 1),
    (re.compile(r"^Alarm_(\d+)$"), 2),
    (re.compile(r"^Step_(\d+)$"), 3),
    (re.compile(r"^Other_(\d+)$"), 7),
    (re.compile(r"^Draw_(\d+)$"), 8),
    (re.compile(r"^KeyPress_(\d+)$"), 9),
    (re.compile(r"^KeyRelease_(\d+)$"), 10),
    (re.compile(r"^CleanUp_(\d+)$"), 12),
    (re.compile(r"^Gesture_(\d+)$"), 13),
    (re.compile(r"^PreCreate_(\d+)$"), 14),
]


def event_key(fname: str):
    stem = fname[:-4]
    if stem.startswith("Collision_"):
        return (4, 0)
    for pattern, event_type in EVENT_PATTERNS:
        match = pattern.match(stem)
        if match:
            return (event_type, int(match.group(1)))
    return None


def load_json(path: str, errors: list[str]):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        errors.append("%s: not valid JSON: %s" % (os.path.relpath(path, ROOT).replace("\\", "/"), exc))
        return None


def check(root: str = ROOT) -> list[str]:
    errors: list[str] = []
    project_path = os.path.join(root, "game", "PrimordialParadox.yyp")

    if not os.path.isfile(project_path):
        return ["game/PrimordialParadox.yyp: missing"]

    yyp = load_json(project_path, errors)
    if yyp is None:
        return errors

    listed = {}
    for entry in yyp.get("resources", []):
        try:
            name = entry["id"]["name"]
            path = entry["id"]["path"]
        except (KeyError, TypeError):
            errors.append("PrimordialParadox.yyp: malformed resources entry %r" % (entry,))
            continue
        if name in listed:
            errors.append("PrimordialParadox.yyp: resource listed twice: %s" % name)
        listed[name] = path
        if not os.path.isfile(os.path.join(root, "game", path)):
            errors.append("PrimordialParadox.yyp: lists %s but game/%s does not exist" % (name, path))

    # Every resource on disk must be listed, or the IDE silently ignores it.
    on_disk = {}
    for kind in ("scripts", "objects", "rooms"):
        base = os.path.join(root, "game", kind)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, name + ".yy")):
                on_disk[name] = "%s/%s/%s.yy" % (kind, name, name)
    for name, path in on_disk.items():
        if name not in listed:
            errors.append("PrimordialParadox.yyp: %s exists on disk (game/%s) but is not listed" % (name, path))

    # Naming conventions are ours and are worth enforcing mechanically.
    for name in on_disk:
        if name.startswith("obj_") and not name.startswith("obj_pp_"):
            errors.append("game/objects/%s: object names are obj_pp_*" % name)
        if name.startswith("rm_") and not name.startswith("rm_pp_"):
            errors.append("game/rooms/%s: room names are rm_pp_*" % name)
        if name.startswith("scr_"):
            errors.append("game/scripts/%s: script resources are named pp_*, not scr_*" % name)

    # Object events: the eventList and the .gml files must match one to one.
    for name, path in on_disk.items():
        if not path.startswith("objects/"):
            continue
        obj_path = os.path.join(root, "game", path)
        obj = load_json(obj_path, errors)
        if obj is None:
            continue
        declared = set()
        for event in obj.get("eventList", []):
            declared.add((event.get("eventType"), event.get("eventNum")))
        on_disk_events = set()
        folder = os.path.dirname(obj_path)
        for fname in os.listdir(folder):
            if not fname.endswith(".gml"):
                continue
            key = event_key(fname)
            if key is None:
                errors.append("game/objects/%s/%s: event file name does not map to an event" % (name, fname))
                continue
            on_disk_events.add(key)
        for key in sorted(on_disk_events - declared):
            errors.append("game/objects/%s: event %s has a .gml file but no eventList entry" % (name, key))
        for key in sorted(declared - on_disk_events):
            errors.append("game/objects/%s: eventList declares %s with no .gml file" % (name, key))

    # Script resources: directory name, file name and resource name must agree.
    for name, path in on_disk.items():
        if not path.startswith("scripts/"):
            continue
        script = load_json(os.path.join(root, "game", path), errors)
        if script is None:
            continue
        if script.get("name") != name:
            errors.append("game/scripts/%s: resource name is %r" % (name, script.get("name")))
        gml = os.path.join(root, "game", "scripts", name, name + ".gml")
        if not os.path.isfile(gml):
            errors.append("game/scripts/%s: %s.gml is missing" % (name, name))
        else:
            with open(gml, "r", encoding="utf-8-sig") as fh:
                text = fh.read()
            if "function " not in text and "#macro" not in text:
                errors.append("game/scripts/%s: %s.gml defines no function or macro" % (name, name))

    # Room instances must point at objects that exist, and the room order must only name real rooms.
    for name, path in on_disk.items():
        if not path.startswith("rooms/"):
            continue
        room = load_json(os.path.join(root, "game", path), errors)
        if room is None:
            continue
        for layer in room.get("layers", []):
            for instance in layer.get("instances", []):
                object_id = instance.get("objectId") or {}
                object_name = object_id.get("name")
                if object_name not in on_disk:
                    errors.append("game/rooms/%s: instance %s points at unknown object %r"
                                  % (name, instance.get("name"), object_name))
        ordered = [node.get("roomId", {}).get("name") for node in yyp.get("RoomOrderNodes", [])]
        del ordered
    for node in yyp.get("RoomOrderNodes", []):
        room_name = node.get("roomId", {}).get("name")
        if room_name not in on_disk:
            errors.append("PrimordialParadox.yyp: RoomOrderNodes names unknown room %r" % room_name)

    # Included Files must match the mirror that sync_data.py builds.
    data_dir = os.path.join(root, "game", "datafiles")
    expected = set()
    if os.path.isdir(data_dir):
        for dirpath, _dirnames, filenames in os.walk(data_dir):
            for fname in filenames:
                expected.add(os.path.relpath(os.path.join(dirpath, fname), data_dir).replace("\\", "/"))
    listed_files = set()
    for entry in yyp.get("IncludedFiles", []):
        file_path = entry.get("filePath", "")
        rel = file_name = entry.get("name", "")
        if file_path and file_path != "datafiles" and file_path.startswith("datafiles/"):
            rel = file_path[len("datafiles/"):] + "/" + file_name
        listed_files.add(rel)
    for rel in sorted(expected - listed_files):
        errors.append("PrimordialParadox.yyp: game/datafiles/%s is not listed as an Included File" % rel)
    for rel in sorted(listed_files - expected):
        errors.append("PrimordialParadox.yyp: lists Included File %s which is not in game/datafiles" % rel)

    # Nothing in the shipped tree may reach into the study copies (PLAN.md section 1).
    for dirpath, _dirnames, filenames in os.walk(os.path.join(root, "game")):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            try:
                with open(full, "r", encoding="utf-8-sig") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            if "knowledge/study" in text or "knowledge\\study" in text:
                errors.append("%s: references the study copies" % os.path.relpath(full, root).replace("\\", "/"))

    return errors


def main() -> int:
    errors = check()
    if errors:
        for line in errors:
            print("FAIL " + line)
        print("\n%d project problem(s)" % len(errors))
        return 1
    print("check_project: project graph and disk agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
