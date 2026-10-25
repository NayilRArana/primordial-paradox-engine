#!/usr/bin/env python3
"""make_drive_map.py: the drive corridor's map row and the palette set it draws in (card t_e8a8f18a).

Why this row exists: a scene row must name a `map` id in data/maps/all.json, and the drive scene
(`drive_to_southampton`, R21b) had no map to name. This tool writes that map. It carries no art and no
shot list of its own; every number it uses is read from a file that already owns it:

    assets/tiles/drive/drive_tiles.json     the sheet: 24 tiles, their character, their palette group, the
                                            palette.json role behind every sheet role, the four groups
    data/tile_classes_drive.json            the walkable classification, which is what the collision grid is
    data/room_palettes.json                 the room palette sets, appended to (the file's own rule)
    assets/tiles/drive/TILES.md             the prose page the four background palettes are printed on

The row's two geometry numbers come from the scene it serves, not from taste:

    WIDTH 160 tiles. The shot list's L3 windows resolve through `offset = round(camera_x * 0.15) mod 512`
    (LAYERS, tools/art/make_title_world.py) to camera tile x 0, 25, 37, 83 and 141, so shot 8 needs tile
    141 plus the 16 tile frame, which is a floor of 158. 160 is the round number above that floor and the
    camera at 141 is reachable without a clamp (160 * 16 - 256 = 2304 px = tile 144).
    HEIGHT 24 tiles. A camera at tile y 8 shows rows 8 to 22 of a 240 px frame, so the map must hold 23 rows
    for that number not to be clamped (24 * 16 - 240 = 144 px, tile 9, past the 8 the scene asks for).
    ROAD_ROW 8 is the y the scene uses for all 15 of its camera commands and for its start.

The band, top to bottom. The road sits where the scene's camera already points at it, the far verge above it
and the near verge, barrier and hedge below, because a camera whose top row is the road row shows the road at
the top of the frame and the near side under it:

    rows 0 to 1    hedge mass, the far side of the corridor (blocked)
    row  2         the shadow under the hedge
    rows 3 to 4    the far verge, grass then tufts
    row  5         the kerb
    row  6         the hard shoulder
    row  7         the edge line
    row  8         the lane dash: the road row the scene names
    rows 9 to 10   the carriageway, with studs and reinstatement seams
    row  11        the near edge line
    row  12        the near hard shoulder
    row  13        the safety barrier, with four openings so the near verge is reachable
    row  14        the near kerb
    row  15        the near verge: grass, marker posts and lamp heads
    row  16        the near verge: tufts and the lamp columns
    row  17        the shadow
    rows 18 to 23  the near hedge mass (blocked)

What the row does not carry: the gantry, the sign face and the rain are film sprites drawn by the drive room
(spec 14, card R21a), not ground, so this row places no gantry tile. The sheet's sign tiles are still
colourable in this room, because the set declares their palette group.

Usage:
    python tools/art/make_drive_map.py            # print the row and what it spends, write nothing
    python tools/art/make_drive_map.py --write    # append the row and the palette set to the tree
    python tools/art/make_drive_map.py --check    # exit 1 if the tree differs from what --write would write
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TILES_JSON = os.path.join("assets", "tiles", "drive", "drive_tiles.json")
CLASSES_JSON = os.path.join("data", "tile_classes_drive.json")
PALETTE_JSON = os.path.join("data", "palette.json")
ROOMS_JSON = os.path.join("data", "room_palettes.json")
MAPS_JSON = os.path.join("data", "maps", "all.json")

MAP_ID = "drive_m4_corridor"
MAP_NAME = "The drive, London to Southampton: the M3 corridor"
SET_ID = "drive_night"
SET_NOTE = "the night drive: tarmac, lane paint, the chalk-lit verge, the sodium lamp and the barrier steel"
TILESET = "drive_tiles"
MUSIC = "PP-02"

WIDTH = 160
HEIGHT = 24
ROAD_ROW = 8

# The drawing roles every room set in this project carries, so a screen that clears or prints before its own
# art loads still asks for a real colour (spec 13). The drive's film draws in ink and text today.
DRAW_ROLES = ("ink", "paper", "dim", "text")

# The slip road: the corridor narrows to one painted lane as it comes into Southampton, and camera tile x 141
# is the shot that looks at it (shot 8, the cathedral on the skyline).
SLIP_COLS = list(range(150, WIDTH))

# The four openings in the barrier, each with its own barrier end one column before it, so the near verge is
# reachable from the road and the map is one walkable region rather than two (spec 04, no soft lock).
BARRIER_OPENINGS = [38, 70, 102, 134]

# Stamp positions, all fixed: the same numbers give the same bytes, so --check has something to compare with.
STUD_COLS = [c for c in range(4, WIDTH, 8)]
WET_SPANS = [[12, 20], [30, 34]]
SEAM_SPANS = [[5, 9], [24, 28], [47, 51], [70, 74], [95, 99], [120, 124], [140, 144]]
POST_COLS = list(range(0, WIDTH, 16))
END_COLS = [c - 1 for c in BARRIER_OPENINGS]
MARKER_COLS = list(range(6, WIDTH, 24))
LAMP_COLS = [18, 66, 114]


def span(cols):
    out = []
    for item in cols:
        if isinstance(item, (list, tuple)):
            out.extend(range(item[0], item[1]))
        else:
            out.append(item)
    return out


# (row, tile the row is made of, stamps put on top of it in order: the last stamp on a column wins)
BAND = [
    (0, "hedge_night", []),
    (1, "hedge_night", []),
    (2, "verge_shadow", []),
    (3, "verge_grass", []),
    (4, "verge_tuft", []),
    (5, "kerb", []),
    (6, "road_shoulder", []),
    (7, "road_edge_line", []),
    (8, "road_lane_dash", [("road_single_lane", SLIP_COLS)]),
    (9, "road_surface", [("road_stud", STUD_COLS), ("road_wet", span(WET_SPANS)),
                         ("road_single_lane", SLIP_COLS)]),
    (10, "road_surface", [("road_surface_worn", span(SEAM_SPANS)),
                          ("road_single_lane", SLIP_COLS)]),
    (11, "road_edge_line", [("road_single_lane", SLIP_COLS)]),
    (12, "road_shoulder", []),
    (13, "barrier_rail", [("barrier_post", POST_COLS), ("barrier_end", END_COLS),
                          ("road_shoulder", BARRIER_OPENINGS)]),
    (14, "kerb", []),
    (15, "verge_grass", [("marker_post", MARKER_COLS), ("lamp_head", LAMP_COLS)]),
    (16, "verge_tuft", [("lamp_post", LAMP_COLS)]),
    (17, "verge_shadow", []),
]
BAND += [(row, "hedge_night", []) for row in range(18, HEIGHT)]


def read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_text(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8-sig") as handle:
        return handle.read()


def sheet():
    """The manifest, plus the two lookups the row and the set are built from."""
    manifest = read(TILES_JSON)
    char_of = {tile["name"]: tile["character"] for tile in manifest["tiles"]}
    palette_of = {tile["name"]: tile["palette"] for tile in manifest["tiles"]}
    groups = {group["name"]: group["roles"] for group in manifest["palettes"]}
    role_of = {name: entry["role"] for name, entry in manifest["roles"].items()}
    index_of = {name: entry["palette_json_index"] for name, entry in manifest["roles"].items()}
    return manifest, char_of, palette_of, groups, role_of, index_of


def tiles():
    """HEIGHT rows of WIDTH characters, straight from the band table."""
    manifest, char_of, _palette_of, _groups, _role_of, _index_of = sheet()
    unknown = sorted({name for _row, name, stamps in BAND for name in [name] + [s[0] for s in stamps]
                      if name not in char_of})
    if unknown:
        raise SystemExit("make_drive_map: %s is not a tile in %s" % (", ".join(unknown), TILES_JSON))
    if len(BAND) != HEIGHT:
        raise SystemExit("make_drive_map: the band table has %d rows, HEIGHT is %d" % (len(BAND), HEIGHT))
    rows = []
    for index, (row, name, stamps) in enumerate(BAND):
        if row != index:
            raise SystemExit("make_drive_map: the band names row %d at position %d" % (row, index))
        cells = [char_of[name]] * WIDTH
        for stamp_name, cols in stamps:
            for col in cols:
                if not 0 <= col < WIDTH:
                    raise SystemExit("make_drive_map: %s stamps column %d, outside 0 to %d"
                                     % (stamp_name, col, WIDTH - 1))
                cells[col] = char_of[stamp_name]
        rows.append("".join(cells))
    del manifest
    return rows


def collision_rows(tile_rows):
    """0 where data/tile_classes_drive.json calls the tile walkable, 1 where it does not.

    The class file is the authority the map reads, so a tile that the art lane reclassifies moves the collision
    grid with it and no second table has to be kept in step.
    """
    classes = read(CLASSES_JSON)
    walkable = {tile["name"]: bool(tile["walkable"]) for tile in classes["tiles"]}
    manifest, char_of, _palette_of, _groups, _role_of, _index_of = sheet()
    name_of = {char_of[name]: name for name in char_of}
    missing = sorted({name for name in name_of.values() if name not in walkable})
    if missing:
        raise SystemExit("make_drive_map: %s classifies no %s" % (CLASSES_JSON, ", ".join(missing)))
    rows = []
    for line in tile_rows:
        rows.append("".join("0" if walkable[name_of[char]] else "1" for char in line))
    del manifest
    return rows


def legend(tile_rows):
    """Only the characters this map uses, each named as the sheet names its tile."""
    _manifest, char_of, _palette_of, _groups, _role_of, _index_of = sheet()
    name_of = {char_of[name]: name for name in char_of}
    used = sorted({char for line in tile_rows for char in line})
    return {char: name_of[char] for char in used}


def set_roles():
    """The roles the drive room draws in: the four drawing roles plus every palette.json role the sheet spends.

    Ordered by the role's own index in data/palette.json, so the set reads in the same order as the master
    palette rather than in the order a set happened to be built in.
    """
    _manifest, _char_of, _palette_of, groups, role_of, _index_of = sheet()
    master = read(PALETTE_JSON)["roles"]
    spent = set()
    for group_roles in groups.values():
        for sheet_role in group_roles:
            spent.add(role_of[sheet_role])
    ordered = sorted(spent, key=lambda name: master.get(name, 999))
    return list(DRAW_ROLES) + [name for name in ordered if name not in DRAW_ROLES]


def set_indices(roles):
    palette = read(PALETTE_JSON)["roles"]
    return sorted({palette[name] for name in roles})


def row():
    tile_rows = tiles()
    roles = set_roles()
    return {
        "id": MAP_ID,
        "name": MAP_NAME,
        "tileset": TILESET,
        "width": WIDTH,
        "height": HEIGHT,
        "music": MUSIC,
        "room_palette": SET_ID,
        "palette_indices": set_indices(roles),
        "tile_legend": legend(tile_rows),
        "tiles": tile_rows,
        "collision": collision_rows(tile_rows),
        "spawns": {
            "start": {"x": 0, "y": ROAD_ROW},
            "arrive": {"x": WIDTH - 1, "y": ROAD_ROW},
        },
        "triggers": [],
        "rails": [],
    }


def room_set(roles):
    return {"id": SET_ID, "note": SET_NOTE, "roles": roles}


def dump_row(document):
    """The row as the file writes it: two space indent, nested by four inside the maps list."""
    body = json.dumps(document, indent=2, ensure_ascii=True)
    return "\n".join(("    " + line) if line else line for line in body.splitlines())


def splice_maps(text, document):
    """Replace the row with this id, or append one, and touch nothing else in the file."""
    block = dump_row(document)
    end = text.rfind("\n  ]\n}")
    if end < 0:
        raise SystemExit("make_drive_map: data/maps/all.json does not end in the maps list")
    head, tail = text[:end], text[end:]
    marker = '"id": "%s"' % MAP_ID
    # Walk the top level rows to find the one that carries our id. A row's span stops at its closing brace, so
    # replacing it leaves the comma that follows it alone and the file's own layout survives.
    found = None
    for match in _row_spans(head):
        if marker in head[match[0]:match[1]]:
            found = match
    if found is not None:
        head = head[:found[0]] + block + head[found[1]:]
    else:
        head = head + ",\n" + block
    return head + tail


def _row_spans(text):
    """The (start, end) of every top level row of a list in this project's data files.

    The convention every data file here follows is two space nesting: a list's rows open on a line of four
    spaces and a brace, and close on a line of four spaces and a brace, with a comma after all but the last.
    A span stops at the closing brace and never swallows the comma.
    """
    spans = []
    open_at = None
    for line, offset in _iter_lines(text):
        if line == "    {":
            open_at = offset
        elif open_at is not None and line.rstrip(",") == "    }":
            spans.append((open_at, offset + len(line)))
            open_at = None
    return spans


def _iter_lines(text):
    offset = 0
    for line in text.splitlines(True):
        yield line.rstrip("\r\n"), offset
        offset += len(line)


def splice_rooms(text, document):
    """Append the set if it is missing, replace it in place if it is there. rooms[].roles is append only, so an
    existing set is never reordered; this tool only ever writes the set it owns."""
    rooms = json.loads(text)
    found = None
    for index, entry in enumerate(rooms.get("sets", [])):
        if entry.get("id") == SET_ID:
            found = index
    if found is None:
        if '"%s"' % SET_ID in text:
            raise SystemExit("make_drive_map: data/room_palettes.json mentions %r but not as a set" % SET_ID)
        end = text.rfind("\n  ]\n}")
        block = "\n".join("    " + line if line else line
                          for line in json.dumps(document, indent=2, ensure_ascii=True).splitlines())
        return text[:end] + ",\n" + block + text[end:]
    # Replace that set's block only, leaving the file's own formatting for everything else.
    span = _set_span(text, found)
    block = "\n".join("    " + line if line else line
                      for line in json.dumps(document, indent=2, ensure_ascii=True).splitlines())
    return text[:span[0]] + block + text[span[1]:]


def _set_span(text, wanted):
    spans = _row_spans(text)
    for index, span in enumerate(spans):
        if index == wanted:
            return span
    raise SystemExit("make_drive_map: data/room_palettes.json holds no set %d" % wanted)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv):
    global ROOT
    parser = argparse.ArgumentParser(description="Write the drive corridor map row and its palette set.")
    parser.add_argument("--root", default=ROOT, help="repository root, default is the one above tools/")
    parser.add_argument("--write", action="store_true", help="append the row and the set to the tree")
    parser.add_argument("--check", action="store_true", help="exit 1 when the tree differs from a write")
    parser.add_argument("--report", default="", help="write the counts to this JSON file")
    args = parser.parse_args(argv)

    ROOT = os.path.abspath(args.root)

    document = row()
    rooms = room_set(set_roles())

    maps_text = read_text(MAPS_JSON)
    rooms_text = read_text(ROOMS_JSON)
    new_maps = splice_maps(maps_text, document)
    new_rooms = splice_rooms(rooms_text, rooms)

    summary = {
        "map": MAP_ID,
        "width": WIDTH,
        "height": HEIGHT,
        "road_row": ROAD_ROW,
        "tiles_used": sorted(set(document["tile_legend"])),
        "blocked_cells": sum(line.count("1") for line in document["collision"]),
        "walkable_cells": sum(line.count("0") for line in document["collision"]),
        "palette_set": SET_ID,
        "roles": rooms["roles"],
        "palette_indices": document["palette_indices"],
        "maps_changed": new_maps != maps_text,
        "rooms_changed": new_rooms != rooms_text,
    }

    if args.write:
        if summary["maps_changed"]:
            write(MAPS_JSON, new_maps)
        if summary["rooms_changed"]:
            write(ROOMS_JSON, new_rooms)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

    print("make_drive_map: %s %dx%d tiles, road on row %d, %d walkable and %d blocked cells"
          % (MAP_ID, WIDTH, HEIGHT, ROAD_ROW, summary["walkable_cells"], summary["blocked_cells"]))
    print("make_drive_map: %d tile characters used: %s"
          % (len(summary["tiles_used"]), " ".join(summary["tiles_used"])))
    print("make_drive_map: set %s declares %d roles and %d distinct colours"
          % (SET_ID, len(rooms["roles"]), len(document["palette_indices"])))
    if args.check:
        stale = [name for name, changed in ((MAPS_JSON, summary["maps_changed"]),
                                            (ROOMS_JSON, summary["rooms_changed"])) if changed]
        if stale:
            print("make_drive_map: STALE, %s does not carry what this tool writes" % ", ".join(stale))
            return 1
        print("make_drive_map: the tree carries what this tool writes")
        return 0
    if not args.write:
        print("make_drive_map: nothing written, pass --write to land the row")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
