"""Write the GameMaker project files (.yyp and one .yy per resource) from what is on disk.

Why a generator: a GameMaker project is a resource graph and the graph must match the folders exactly. Hand editing
twenty .yy files and one 200 line .yyp is where a project stops opening. This script derives the graph from the
directories, so the files on disk are the source of truth and the .yyp can never list a resource that is not there.

Field shapes are taken from a real GameMaker 2024.1400 project (see knowledge\\PROVENANCE.md, entry "room and object
conventions across a whole game"). Every file we write is STRICT JSON, which GameMaker reads and Python can check.

Usage:
    python tools/gen_project.py            # rewrite the project files
    python tools/gen_project.py --check    # write nothing, exit 1 if a file is missing or stale

Never touches: scripts' .gml, objects' event .gml, room instances you added in the IDE (those live in the room .yy,
so re-running this DOES rewrite a room .yy; add new rooms to ROOMS below instead of editing them in the IDE by hand
until the IDE has been opened once and this generator has been diffed against it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
PROJECT_NAME = "PrimordialParadox"
IDE_VERSION = "2024.1400.0.911"

FOLDER_ROOT = "Primordial Paradox"


# ---------------------------------------------------------------------------------------------------------------
# Rooms. Instance layers are declared here. Coordinates are frame pixels at 1x.
ROOMS = {
    "rm_pp_boot": {
        "size": (256, 240),
        "background": 4278190080,  # opaque black, ARGB
        "instances": [
            ("obj_pp_game", 0, 0),
            ("obj_pp_debug_overlay", 0, 0),
        ],
    },
    "rm_pp_title": {
        "size": (256, 240),
        "background": 4278190080,  # opaque black, ARGB
        "instances": [
            ("obj_pp_title", 0, 0),
            ("obj_pp_debug_overlay", 0, 0),
        ],
    },
    # Map 2 (card ASSEMBLE): the Navy ship lower deck, played from data/maps/ship_sample.json. The instance
    # layer is empty on purpose. obj_pp_game is persistent, so it is already alive when the run enters this
    # room, and a placed copy here would be a second controller in the same frame.
    "rm_pp_ship": {
        "size": (256, 240),
        "background": 4278190080,  # opaque black, ARGB
        "instances": [],
    },
    # R21a: the drive to Southampton. obj_pp_drive owns the screen, the same way obj_pp_title owns rm_pp_title, so the
    # twelve shots are drawn by one instance and the app's modes stay out of the way. The debug overlay rides along as
    # it does in every room.
    "rm_pp_drive": {
        "size": (256, 240),
        "background": 4278190080,  # opaque black, ARGB
        "instances": [
            ("obj_pp_drive", 0, 0),
            ("obj_pp_debug_overlay", 0, 0),
        ],
    },
}

ROOM_ORDER = ["rm_pp_boot", "rm_pp_title", "rm_pp_drive", "rm_pp_ship"]

# Per object settings the generated .yy carries. obj_pp_game is persistent because it owns the app mode machine,
# the input sample and the save panel, and all three must survive the move from the boot room to the title room.
OBJECT_SETTINGS = {
    "obj_pp_game": {"persistent": True},
}

# Event file name -> (eventType, eventNum). Names follow what the IDE writes.
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


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace("\\", "/")


def ref(name: str, path: str) -> dict:
    return {"name": name, "path": path}


def folder_ref(folder: str) -> dict:
    return ref(folder, "folders/%s/%s.yy" % (FOLDER_ROOT, folder))


def write_text(path: str, text: str, check: bool) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as fh:
            existing = fh.read()
        if existing == text:
            return True
    if check:
        print("STALE: %s" % rel(path))
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s" % rel(path))
    return True


# ---------------------------------------------------------------------------------------------------------------
# Resource descriptions


def script_yy(name: str) -> dict:
    return {
        "$GMScript": "v1",
        "%Name": name,
        "isCompatibility": False,
        "isDnD": False,
        "name": name,
        "parent": folder_ref("Scripts"),
        "resourceType": "GMScript",
        "resourceVersion": "2.0",
    }


def event_entry(event_type: int, event_num: int, collision_object: str | None = None) -> dict:
    return {
        "$GMEvent": "v1",
        "%Name": "",
        "collisionObjectId": ref(collision_object, "objects/%s/%s.yy" % (collision_object, collision_object))
        if collision_object
        else None,
        "eventNum": event_num,
        "eventType": event_type,
        "isDnD": False,
        "name": "",
        "resourceType": "GMEvent",
        "resourceVersion": "2.0",
    }


def read_events(object_dir: str, name: str) -> list:
    events = []
    for fname in sorted(os.listdir(object_dir)):
        if not fname.endswith(".gml"):
            continue
        stem = fname[:-4]
        if stem.startswith("Collision_"):
            target = stem[len("Collision_"):]
            events.append(event_entry(4, 0, target))
            continue
        for pattern, event_type in EVENT_PATTERNS:
            match = pattern.match(stem)
            if match:
                events.append(event_entry(event_type, int(match.group(1))))
                break
        else:
            raise SystemExit(
                "object %s has event file %s which does not match a known event name; "
                "rename it or add the pattern to EVENT_PATTERNS" % (name, fname)
            )
    # Stable order: create first, then the rest by type and number, which is how the IDE lists them.
    events.sort(key=lambda e: (e["eventType"], e["eventNum"]))
    return events


def object_yy(name: str) -> dict:
    obj_dir = os.path.join(GAME, "objects", name)
    settings = OBJECT_SETTINGS.get(name, {})
    return {
        "$GMObject": "",
        "%Name": name,
        "eventList": read_events(obj_dir, name),
        "managed": True,
        "name": name,
        "overriddenProperties": [],
        "parent": folder_ref("Objects"),
        "parentObjectId": None,
        "persistent": bool(settings.get("persistent", False)),
        "physicsAngularDamping": 0.1,
        "physicsDensity": 0.5,
        "physicsFriction": 0.2,
        "physicsGroup": 1,
        "physicsKinematic": False,
        "physicsLinearDamping": 0.1,
        "physicsObject": False,
        "physicsRestitution": 0.1,
        "physicsSensor": False,
        "physicsShape": 1,
        "physicsShapePoints": [],
        "physicsStartAwake": True,
        "properties": [],
        "resourceType": "GMObject",
        "resourceVersion": "2.0",
        "solid": False,
        "spriteId": None,
        "spriteMaskId": None,
        "visible": True,
    }


def instance_layer(name: str, instances: list) -> dict:
    made = []
    for index, (object_name, x, y) in enumerate(instances):
        iname = "inst_%04X" % (index + 1)
        made.append({
            "$GMRInstance": "v4",
            "%Name": iname,
            "colour": 4294967295,
            "frozen": False,
            "hasCreationCode": False,
            "ignore": False,
            "imageIndex": 0,
            "imageSpeed": 1.0,
            "inheritCode": False,
            "inheritedItemId": None,
            "inheritItemSettings": False,
            "isDnd": False,
            "name": iname,
            "objectId": ref(object_name, "objects/%s/%s.yy" % (object_name, object_name)),
            "properties": [],
            "resourceType": "GMRInstance",
            "resourceVersion": "2.0",
            "rotation": 0.0,
            "scaleX": 1.0,
            "scaleY": 1.0,
            "x": x,
            "y": y,
        })
    return {
        "$GMRInstanceLayer": "",
        "%Name": "Instances",
        "depth": 0,
        "effectEnabled": True,
        "effectType": None,
        "gridX": 32,
        "gridY": 32,
        "hierarchyFrozen": False,
        "inheritLayerDepth": False,
        "inheritLayerSettings": False,
        "inheritSubLayers": True,
        "inheritVisibility": True,
        "instances": made,
        "layers": [],
        "name": "Instances",
        "properties": [],
        "resourceType": "GMRInstanceLayer",
        "resourceVersion": "2.0",
        "userdefinedDepth": False,
        "visible": True,
    }


def background_layer(colour: int) -> dict:
    return {
        "$GMRBackgroundLayer": "",
        "%Name": "Background",
        "animationFPS": 15.0,
        "animationSpeedType": 0,
        "colour": colour,
        "depth": 100,
        "effectEnabled": True,
        "effectType": None,
        "gridX": 32,
        "gridY": 32,
        "hierarchyFrozen": False,
        "hspeed": 0.0,
        "htiled": False,
        "inheritLayerDepth": False,
        "inheritLayerSettings": False,
        "inheritSubLayers": True,
        "inheritVisibility": True,
        "layers": [],
        "name": "Background",
        "properties": [],
        "resourceType": "GMRBackgroundLayer",
        "resourceVersion": "2.0",
        "spriteId": None,
        "stretch": False,
        "userdefinedAnimFPS": False,
        "userdefinedDepth": False,
        "visible": True,
        "vspeed": 0.0,
        "vtiled": False,
        "x": 0,
        "y": 0,
    }


def room_yy(name: str, spec: dict) -> dict:
    width, height = spec["size"]
    view = {
        "hborder": 32, "hport": height, "hspeed": -1, "hview": width, "inherit": False,
        "objectId": None, "vborder": 32, "visible": False, "vspeed": -1, "wport": width,
        "wview": width, "xport": 0, "xview": 0, "yport": 0, "yview": 0,
    }
    return {
        "$GMRoom": "v1",
        "%Name": name,
        "creationCodeFile": "",
        "inheritCode": False,
        "inheritCreationOrder": False,
        "inheritLayers": False,
        "instanceCreationOrder": [
            ref("inst_%04X" % (i + 1), "rooms/%s/%s.yy" % (name, name))
            for i in range(len(spec["instances"]))
        ],
        "isDnd": False,
        "layers": [
            instance_layer(name, spec["instances"]),
            background_layer(spec["background"]),
        ],
        "name": name,
        "parent": folder_ref("Rooms"),
        "parentRoom": None,
        "physicsSettings": {
            "inheritPhysicsSettings": False,
            "PhysicsWorld": False,
            "PhysicsWorldGravityX": 0.0,
            "PhysicsWorldGravityY": 10.0,
            "PhysicsWorldPixToMetres": 0.1,
        },
        "resourceType": "GMRoom",
        "resourceVersion": "2.0",
        "roomSettings": {"Height": height, "inheritRoomSettings": False, "persistent": False, "Width": width},
        "sequenceId": None,
        "views": [dict(view) for _ in range(8)],
        "viewSettings": {
            "clearDisplayBuffer": True,
            "clearViewBackground": False,
            "enableViews": False,
            "inheritViewSettings": False,
        },
        "volume": 1.0,
    }


# ---------------------------------------------------------------------------------------------------------------
# Included files: everything under game/datafiles, which tools/sync_data.py fills from data/.


def included_files() -> list:
    base = os.path.join(GAME, "datafiles")
    out = []
    if not os.path.isdir(base):
        return out
    for dirpath, _dirnames, filenames in os.walk(base):
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            sub = os.path.relpath(dirpath, base).replace("\\", "/")
            file_path = "datafiles" if sub == "." else "datafiles/" + sub
            out.append({
                "$GMIncludedFile": "",
                "%Name": fname,
                "CopyToMask": -1,
                "filePath": file_path,
                "name": fname,
                "resourceType": "GMIncludedFile",
                "resourceVersion": "2.0",
            })
    out.sort(key=lambda e: (e["filePath"], e["name"]))
    return out


# ---------------------------------------------------------------------------------------------------------------


def project_yy(paths: dict) -> dict:
    resources = []
    for kind in ("scripts", "objects", "rooms"):
        for name in sorted(paths[kind]):
            resources.append({"id": ref(name, paths[kind][name])})

    folders = []
    for folder in ("Scripts", "Objects", "Rooms"):
        folders.append({
            "$GMFolder": "",
            "%Name": folder,
            "folderPath": "folders/%s/%s.yy" % (FOLDER_ROOT, folder),
            "name": folder,
            "resourceType": "GMFolder",
            "resourceVersion": "2.0",
        })
    folders.insert(0, {
        "$GMFolder": "",
        "%Name": FOLDER_ROOT,
        "folderPath": "folders/%s.yy" % FOLDER_ROOT,
        "name": FOLDER_ROOT,
        "resourceType": "GMFolder",
        "resourceVersion": "2.0",
    })

    return {
        "$GMProject": "v1",
        "%Name": PROJECT_NAME,
        "AudioGroups": [{
            "$GMAudioGroup": "v1",
            "%Name": "audiogroup_default",
            "exportDir": "",
            "name": "audiogroup_default",
            "resourceType": "GMAudioGroup",
            "resourceVersion": "2.0",
            "targets": -1,
        }],
        "configs": {"children": [{"children": [], "name": "Debug"}], "name": "Default"},
        "defaultScriptType": 1,
        "Folders": folders,
        "ForcedPrefabProjectReferences": [],
        "IncludedFiles": included_files(),
        "isEcma": False,
        "LibraryEmitters": [],
        "MetaData": {"IDEVersion": IDE_VERSION},
        "name": PROJECT_NAME,
        "resources": resources,
        "resourceType": "GMProject",
        "resourceVersion": "2.0",
        "RoomOrderNodes": [{"roomId": ref(n, paths["rooms"][n])} for n in ROOM_ORDER if n in paths["rooms"]],
        "templateType": "game",
        "TextureGroups": [{
            "$GMTextureGroup": "",
            "%Name": "Default",
            "autocrop": True,
            "border": 2,
            "compressFormat": "bz2",
            "customOptions": "",
            "directory": "",
            "groupParent": None,
            "isScaled": True,
            "loadType": "default",
            "mipsToGenerate": 0,
            "name": "Default",
            "resourceType": "GMTextureGroup",
            "resourceVersion": "2.0",
            "targets": -1,
        }],
    }


def collect() -> dict:
    paths = {"scripts": {}, "objects": {}, "rooms": {}}

    scripts_dir = os.path.join(GAME, "scripts")
    for name in sorted(os.listdir(scripts_dir)) if os.path.isdir(scripts_dir) else []:
        gml = os.path.join(scripts_dir, name, name + ".gml")
        if os.path.isfile(gml):
            paths["scripts"][name] = "scripts/%s/%s.yy" % (name, name)

    objects_dir = os.path.join(GAME, "objects")
    for name in sorted(os.listdir(objects_dir)) if os.path.isdir(objects_dir) else []:
        if os.path.isdir(os.path.join(objects_dir, name)):
            paths["objects"][name] = "objects/%s/%s.yy" % (name, name)

    for name in ROOMS:
        paths["rooms"][name] = "rooms/%s/%s.yy" % (name, name)

    return paths


def regenerate(check: bool = False) -> tuple[bool, list[str]]:
    """Write the project files the folders on disk imply. Idempotent: a second run writes nothing.

    This loop used to live inside main(), so a caller that changed the resource graph had no way to
    bring the .yyp back in line. tools/sync_art.py does change it: mirror_streams() copies a
    rendered cue into game/datafiles/streams, every file under game/datafiles is an Included File,
    and nothing ran the generator when a cue landed. The .yyp then disagreed with disk until a
    person noticed and an FIX-YYP card was raised: five cards, five commits of the same two
    entries (card t_e40f9705). The landing path now calls this in the same run.

    Returns (ok, written) where ok is True when disk matches the folders and written names the
    files this call rewrote, relative to the repository root. With check=True nothing is written
    and each stale file still prints its own STALE line through write_text().
    """
    paths = collect()
    files = []
    for name, path in paths["scripts"].items():
        files.append((os.path.join(GAME, path), script_yy(name)))
    for name, path in paths["objects"].items():
        files.append((os.path.join(GAME, path), object_yy(name)))
    for name, path in paths["rooms"].items():
        files.append((os.path.join(GAME, path), room_yy(name, ROOMS[name])))
    files.append((os.path.join(GAME, PROJECT_NAME + ".yyp"), project_yy(paths)))

    ok = True
    written = []
    for full, data in files:
        # write_text() answers True both when it wrote and when the bytes already matched, so
        # whether a file was stale has to be read before the write, not from the return value.
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        matched = False
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8-sig") as fh:
                matched = fh.read() == text
        ok &= write_text(full, text, check)
        if not matched:
            written.append(rel(full))
    return ok, written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="write nothing, report stale files")
    args = parser.parse_args()

    ok, _written = regenerate(args.check)

    paths = collect()
    total = len(paths["scripts"]) + len(paths["objects"]) + len(paths["rooms"])
    print("%d resources: %d scripts, %d objects, %d rooms, %d included files"
          % (total, len(paths["scripts"]), len(paths["objects"]), len(paths["rooms"]),
             len(included_files())))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
