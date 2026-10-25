"""The quay's boarding page, measured from the data and from the tool that prints it (card t_4dc4751c).

`ship_aboard` was written by card t_4c7368fb and left with nothing to say it. The wiring this file
pins is one `say` trigger on the quay row, and the two things a bad edit would break: the trigger
sharing a tile with the gangway door (which makes it unreachable, because pp_map_trigger_at keeps the
first row on a tile), and the tile itself falling outside the walk.

Sources this file measures, never restates:

    data/maps/all.json                    southampton_town_quay and its triggers
    data/dialogue/all.json                the ship_aboard row
    tools/check_data.py                   LINE_CHARS, the dialogue box limit
    tools/walk_ship_aboard.py             the read only walker the card asked for
    game/scripts/pp_map/pp_map.gml        pp_map_trigger_at and pp_map_collision
    game/scripts/pp_overworld/pp_overworld.gml
                                          pp_overworld_confirm_target: ahead first, then underfoot

No test here reads the network, writes a tracked file, or needs a key.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPS_PATH = os.path.join(ROOT, "data", "maps", "all.json")
DIALOGUE_PATH = os.path.join(ROOT, "data", "dialogue", "all.json")
WALKER = os.path.join(ROOT, "tools", "walk_ship_aboard.py")

MAP_ID = "southampton_town_quay"
ENTRY_SPAWN = "start"
PAGE_ID = "ship_aboard"
GANGWAY_MAP = "ship_small"
GANGWAY_TILE = (17, 38)
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def quay() -> dict:
    rows = {row["id"]: row for row in load(MAPS_PATH)["maps"]}
    assert MAP_ID in rows, "data/maps/all.json holds no map %r" % MAP_ID
    return rows[MAP_ID]


@pytest.fixture(scope="module")
def dialogue() -> dict:
    return {row["id"]: row for row in load(DIALOGUE_PATH)["dialogue"]}


def triggers_on(row: dict, x: int, y: int) -> list:
    return [trigger for trigger in row["triggers"] if trigger["x"] == x and trigger["y"] == y]


def trigger_at(row: dict, x: int, y: int):
    """pp_map_trigger_at: the first row whose tile is this one, or None."""
    found = triggers_on(row, x, y)
    return found[0] if found else None


def confirm_target(row: dict, x: int, y: int, facing: str):
    """pp_overworld_confirm_target: the tile ahead first, then the tile underfoot."""
    dx, dy = DIRS[facing]
    ahead = trigger_at(row, x + dx, y + dy)
    if ahead is not None:
        return ahead
    return trigger_at(row, x, y)


def reachable(row: dict, start: tuple) -> set:
    """pp_map_collision, four directions: 0 walkable, 1 blocked, 2 blocked until the story flag."""
    collision = row["collision"]
    seen = {start}
    queue = [start]
    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        for dx, dy in DIRECTIONS:
            nxt = (x + dx, y + dy)
            if nxt in seen:
                continue
            nx, ny = nxt
            if 0 <= ny < row["height"] and 0 <= nx < row["width"] and collision[ny][nx] == "0":
                seen.add(nxt)
                queue.append(nxt)
    return seen


def test_the_page_has_one_trigger_on_a_tile_of_its_own(quay):
    """One row, walkable, and nothing else on the tile: two rows there would hide the second one."""
    pages = [trigger for trigger in quay["triggers"]
             if trigger["kind"] == "say" and trigger["id"] == PAGE_ID]
    assert len(pages) == 1, "the quay carries %d %r say triggers, expected 1" % (len(pages), PAGE_ID)

    page = pages[0]
    tile = (page["x"], page["y"])
    shared = triggers_on(quay, tile[0], tile[1])
    assert len(shared) == 1, (
        "tile %s carries %d triggers; pp_map_trigger_at keeps the first, so the page would be dead data"
        % (tile, len(shared)))
    assert quay["collision"][tile[1]][tile[0]] == "0", (
        "the page tile %s is not walkable, so nobody can stand on it and confirm" % (tile,))
    assert page["once"] is False, "the page fires once and then the tile is silent for the rest of the run"
    assert page["condition"] == "", "the page is gated on %r, so it is not there on the first walk" % (
        page["condition"],)


def test_the_page_resolves_to_a_dialogue_row_that_fits_the_box(quay, dialogue):
    """The id has to be a row, and every line has to fit the 28 character box the pages are measured in."""
    import check_data

    page = [trigger for trigger in quay["triggers"]
            if trigger["kind"] == "say" and trigger["id"] == PAGE_ID][0]
    entry = dialogue.get(page["id"])
    assert entry is not None, "the trigger names %r and data/dialogue/all.json holds no such row" % page["id"]
    assert len(entry["pages"]) == 1, "ship_aboard is %d pages, the board is one page" % len(entry["pages"])

    lines = [line for page_row in entry["pages"] for line in page_row["lines"]]
    assert lines, "ship_aboard carries no line at all"
    too_long = [line for line in lines if len(line) > check_data.LINE_CHARS]
    assert too_long == [], "line(s) longer than the %d character box: %s" % (check_data.LINE_CHARS, too_long)
    assert not any("\u2013" in line or "\u2014" in line for line in lines), "a long dash in a page line"


def test_the_pier_head_still_boards_and_the_page_fires_one_step_back(quay):
    """The landing keeps its tile: confirm on the pier head boards, confirm one tile south reads the page."""
    pier_head = confirm_target(quay, GANGWAY_TILE[0], GANGWAY_TILE[1], "up")
    assert pier_head is not None, "the pier head carries no trigger, so there is no way onto the ship"
    assert pier_head["kind"] == "map" and pier_head["id"] == GANGWAY_MAP, (
        "confirm on the pier head resolves to %r %r instead of the gangway"
        % (pier_head["kind"], pier_head["id"]))

    foot = confirm_target(quay, GANGWAY_TILE[0], GANGWAY_TILE[1] + 2, "up")
    assert foot is not None and foot["kind"] == "say" and foot["id"] == PAGE_ID, (
        "standing two tiles back from the gangway and facing it resolves to %r, not the page"
        % (foot["id"] if foot else None,))


def test_the_page_tile_is_walkable_from_the_entry_spawn(quay):
    """A page on a tile the flood fill never reaches is a page no run can read."""
    page = [trigger for trigger in quay["triggers"]
            if trigger["kind"] == "say" and trigger["id"] == PAGE_ID][0]
    entry = quay["spawns"][ENTRY_SPAWN]
    walk = reachable(quay, (entry["x"], entry["y"]))
    assert (page["x"], page["y"]) in walk, (
        "the page tile (%d,%d) is not reachable from the entry spawn %r at (%d,%d)"
        % (page["x"], page["y"], ENTRY_SPAWN, entry["x"], entry["y"]))


def test_the_walker_tool_passes_and_names_the_trigger():
    """The card's own proof, run as a tool: it has to exit 0 and print the tile, the kind and the id."""
    result = subprocess.run([sys.executable, WALKER], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, "tools/walk_ship_aboard.py exited %d: %s%s" % (
        result.returncode, result.stdout, result.stderr)
    assert "trigger tile (%d, %d) kind 'say' id '%s'" % (17, 39, PAGE_ID) in result.stdout, (
        "the walker did not print the trigger tile: %s" % result.stdout)
    assert "dialogue row %r" % PAGE_ID in result.stdout, "the walker did not print the dialogue row"
