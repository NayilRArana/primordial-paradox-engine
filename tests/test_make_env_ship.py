"""Tests for tools/art/make_env_ship.py (ENV-TILES, card t_4f58c88d).

What these pin, and why each one is a measurement rather than a matter of taste:

1. The generator writes the five outputs the card names, and writing them twice gives byte identical
   files. Determinism is what lets a commit carry the art: a reviewer reruns the script and gets the
   same PNG, so the picture in the diff is the picture in the code.
2. The 10 colours on the sheet are exactly the 10 the tileset declares, the PNG is 256x48 (16 columns
   of 16x16, 48 tiles), and every tile the card names is in the tile table with a unique name.
3. The collision layer is derived from the tileset's own solid flags, cell for cell, not typed twice.
4. The map is 20x15, uses only tiles the sheet has, its three spawns sit on walkable cells, and every
   walkable cell is reachable from player_start.
5. The map path rule: another lane's data/maps/ship_sample.json is never overwritten, and this lane's
   own file at that name is rewritten.
6. The committed files under game/sprites_src/env/, data/maps/ and output/ are what the script writes
   today, so the repository cannot drift from the code that made it. That only means something if the
   fresh build is fed the same inputs the repository build is fed, so every scratch root is seeded with
   the two files the optional scene palette pass reads (see seed_palette_inputs), and the same test
   proves a build without them does not match the committed sheet.
7. tools/check_env_tiles.py passes on the repository, and its facts say the art is inside the NES
   colour budgets.

The suite runs the generator six times (about 1.3 s each) and the checker once (about 5 s), so it
stays inside a normal test pass.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for folder in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "tools", "art")):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import check_env_tiles as ce  # noqa: E402
import make_env_ship as ms  # noqa: E402


def sha(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def load(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def output_files(root: str) -> dict:
    """The five files a build writes, keyed by what they are."""
    env = os.path.join(root, "game", "sprites_src", "env")
    return {
        "sheet": os.path.join(env, "ts_ship.png"),
        "meta": os.path.join(env, "ts_ship.json"),
        "tileset": os.path.join(env, "ts_ship_tiled.json"),
        "map": ms.map_output_path(root),
        "preview": os.path.join(root, "output", "env_ship_preview.png"),
    }


# The optional scene palette pass in tools/art/make_env_ship.py build() reads these two files from the
# build root and prints "scene palettes: skipped" without them, which rewrites 762 fewer pixels and
# lands a different sheet. A repository build has them, so a scratch root must too, or the provenance
# test compares the committed palette build against a no-palette build and can never pass.
PALETTE_INPUTS = (
    os.path.join("data", "nes_palette.json"),
    os.path.join("data", "palettes", "scene_ship.json"),
)


def seed_palette_inputs(root: str) -> None:
    """Give a scratch root the repository's copies of the files the scene palette pass reads."""
    for relative in PALETTE_INPUTS:
        source = os.path.join(ROOT, relative)
        assert os.path.isfile(source), "the repository is missing a build input: %s" % source
        target = os.path.join(root, relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)


def build_in(root: str) -> dict:
    """Build into a scratch root the way the repository builds, and refuse a build that skipped the pass.

    Seeding is not a bypass: the pass still reads the files and still rewrites pixels. The assertion is
    there so this fixture cannot quietly go back to a bare root, which is the bug this file guards.
    """
    seed_palette_inputs(root)
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        paths = ms.build(root)
    log = said.getvalue()
    assert "scene palettes: skipped" not in log, (
        "the fixture built without the scene palette inputs, so it is not the build the repository "
        "makes: %s" % log.strip())
    assert "scene palettes: ts_ship" in log, (
        "the scene palette pass did not report a result: %s" % log.strip())
    return paths


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict:
    """One build into a throwaway root, shared by the tests that only read it."""
    root = str(tmp_path_factory.mktemp("env_ship"))
    paths = build_in(root)
    return {"root": root, "paths": paths, "files": output_files(root)}


# ---------------------------------------------------------------------------- 1. outputs and determinism

def test_build_writes_the_five_outputs_the_card_names(built):
    paths = built["paths"]
    for key in ("sheet", "meta", "tileset", "map", "preview"):
        assert os.path.isfile(paths[key]), key
        assert os.path.getsize(paths[key]) > 0, key
    assert os.path.basename(paths["sheet"]) == "ts_ship.png"
    assert os.path.basename(paths["preview"]) == "env_ship_preview.png"
    meta = load(paths["meta"])
    assert meta == {"name": "ts_ship", "frame_w": 16, "frame_h": 16, "frames": 48,
                    "fps": 0.0, "kind": "tileset", "columns": 16, "rows": 3}
    assert load(paths["map"])["kind"] == "map"


def test_two_builds_are_byte_identical(tmp_path):
    first = output_files(str(tmp_path / "a"))
    second = output_files(str(tmp_path / "b"))
    build_in(str(tmp_path / "a"))
    build_in(str(tmp_path / "b"))
    for key in first:
        assert sha(first[key]) == sha(second[key]), key


# ---------------------------------------------------------------------------- 2. the sheet and the tile table

def test_sheet_is_the_size_the_metadata_says(built):
    image = Image.open(built["files"]["sheet"]).convert("RGBA")
    assert image.size == (16 * 16, 3 * 16) == (256, 48)
    assert image.getpixel((0, 0))[3] == 255


def test_every_colour_on_the_sheet_is_one_of_the_ten_declared(built):
    tileset = load(built["files"]["tileset"])
    declared = [entry["hex"].lower() for entry in tileset["palette"]]
    assert len(declared) == 10, "the card allows 8 to 10 colours for the scene"
    expected = {tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5)) for hexv in declared}
    image = Image.open(built["files"]["sheet"]).convert("RGB")
    used = {colour for _, colour in image.getcolors(maxcolors=1 << 24)}
    assert used == expected, "every declared colour must be used, and no other colour may appear"


def test_declared_colours_are_the_2c02_entries_they_name(built):
    chip = load(os.path.join(ROOT, "data", "nes_palette.json"))["colours"]
    for entry in load(built["files"]["tileset"])["palette"]:
        assert chip[entry["entry"]].lower() == entry["hex"].lower(), entry["key"]


def test_tile_table_holds_every_item_the_card_names(built):
    tileset = load(built["files"]["tileset"])
    assert tileset["tilecount"] == 48
    assert [tile["id"] for tile in tileset["tiles"]] == list(range(48))
    names = [prop["value"] for tile in tileset["tiles"]
             for prop in tile["properties"] if prop["name"] == "tile_name"]
    assert len(names) == 48
    assert len(set(names)) == 48, "tile names must be unique"
    missing = [name for name in ce.REQUIRED_TILES if name not in names]
    assert missing == [], "the card lists these tiles: %s" % ", ".join(missing)


def test_each_16x16_tile_stays_inside_the_nes_attribute_budget(built):
    tileset = load(built["files"]["tileset"])
    backdrop = tuple(int(tileset["palette"][0]["hex"][i:i + 2], 16) for i in (1, 3, 5))
    image = Image.open(built["files"]["sheet"]).convert("RGB")
    worst = 0
    for tid in range(48):
        left, top = (tid % 16) * 16, (tid // 16) * 16
        colours = {image.getpixel((left + x, top + y))
                   for y in range(16) for x in range(16)}
        worst = max(worst, len(colours - {backdrop}))
    assert worst <= 3, "a NES attribute area holds 3 colours plus the backdrop, worst tile has %d" % worst


# ---------------------------------------------------------------------------- 3. the collision layer

def test_collision_layer_is_the_solid_flags_of_the_tiles_above_it(built):
    tileset = load(built["files"]["tileset"])
    solid = {}
    for tile in tileset["tiles"]:
        props = {prop["name"]: prop["value"] for prop in tile["properties"]}
        solid[tile["id"] + 1] = props["solid"]          # gids start at 1
    ship = load(built["files"]["map"])
    layers = {layer["name"]: layer for layer in ship["layers"]}
    ground = layers["ground"]["data"]
    collision = layers["collision"]["data"]
    assert len(ground) == len(collision) == 20 * 15
    assert set(collision) <= {0, 1}, "a collision layer of this map is 0 or 1"
    for index, (gid, value) in enumerate(zip(ground, collision)):
        want = 1 if solid[gid] else 0
        assert value == want, "cell %d,%d holds gid %d" % (index % 20, index // 20, gid)
    rows = ship["collision_rows"]
    assert len(rows) == 15
    rebuilt = ["".join(str(collision[y * 20 + x]) for x in range(20)) for y in range(15)]
    assert rows == rebuilt, "collision_rows must restate the collision layer, not disagree with it"
    blocked = sum(collision)
    assert 0 < blocked < len(collision), "a ship interior has walls and floor, %d blocked cells" % blocked


# ---------------------------------------------------------------------------- 4. the map itself

def test_map_is_20x15_and_uses_only_tiles_the_sheet_has(built):
    ship = load(built["files"]["map"])
    assert (ship["width"], ship["height"]) == (20, 15)
    assert (ship["tilewidth"], ship["tileheight"]) == (16, 16)
    ground = [layer for layer in ship["layers"] if layer["name"] == "ground"][0]["data"]
    assert len(ground) == 300
    assert min(ground) >= 1 and max(ground) <= 48, "gids outside the 48 tile sheet"
    assert set(ship["tile_legend"].values()) <= set(
        prop["value"] for tile in load(built["files"]["tileset"])["tiles"]
        for prop in tile["properties"] if prop["name"] == "tile_name")


def test_every_walkable_cell_is_reachable_from_the_player_start(built):
    ship = load(built["files"]["map"])
    layers = {layer["name"]: layer for layer in ship["layers"]}
    collision = layers["collision"]["data"]
    walkable = {(x, y) for y in range(15) for x in range(20) if collision[y * 20 + x] == 0}
    for name, point in ship["spawns"].items():
        assert (point["x"], point["y"]) in walkable, "%s sits on a blocked cell" % name
    start = (ship["spawns"]["player_start"]["x"], ship["spawns"]["player_start"]["y"])
    seen, queue = {start}, [start]
    while queue:
        x, y = queue.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in walkable and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    assert seen == walkable, "%d walkable cells are cut off from the player start" % len(walkable - seen)


def test_map_shows_the_rooms_ladder_and_the_hatch_out(built):
    tileset = load(built["files"]["tileset"])
    names = {tile["id"] + 1: [prop["value"] for prop in tile["properties"]
                              if prop["name"] == "tile_name"][0]
             for tile in tileset["tiles"]}
    ship = load(built["files"]["map"])
    ground = [layer for layer in ship["layers"] if layer["name"] == "ground"][0]["data"]
    used = {names[gid] for gid in ground}
    for name in ce.REQUIRED_IN_MAP:
        assert name in used, "the sample map never places %s" % name
    exits = {obj["name"]: obj for obj in
             [layer for layer in ship["layers"] if layer["name"] == "objects"][0]["objects"]
             if obj.get("type") == "map_exit"}
    assert set(exits) == {"hatch_percy", "ladder_down", "stairs_up"}
    hatch = exits["hatch_percy"]
    props = {prop["name"]: prop["value"] for prop in hatch["properties"]}
    assert props["target_map"] == "percy_wardroom"
    cell = (hatch["x"] // 16, hatch["y"] // 16)
    assert names[ground[cell[1] * 20 + cell[0]]] == "hatch_closed"


# ---------------------------------------------------------------------------- 5. the map path rule

def test_a_foreign_map_at_the_plain_name_is_never_overwritten(tmp_path):
    foreign = tmp_path / "data" / "maps" / "ship_sample.json"
    foreign.parent.mkdir(parents=True)
    foreign.write_text(json.dumps({"format": 1, "kind": "maps", "maps": []}), encoding="utf-8")
    before = foreign.read_bytes()
    paths = build_in(str(tmp_path))
    assert os.path.basename(paths["map"]) == "ship_sample_tiled.json"
    assert foreign.read_bytes() == before, "another lane's ship_sample.json was modified"


def test_this_lanes_own_map_at_the_plain_name_is_rewritten(tmp_path):
    plain = tmp_path / "data" / "maps" / "ship_sample.json"
    plain.parent.mkdir(parents=True)
    plain.write_text(json.dumps({"format": 1, "kind": "map", "width": 1, "height": 1}), encoding="utf-8")
    paths = build_in(str(tmp_path))
    assert os.path.basename(paths["map"]) == "ship_sample.json"
    assert (load(paths["map"])["width"], load(paths["map"])["height"]) == (20, 15)


# ---------------------------------------------------------------------------- 6. the committed art is current

# Card TEST-CLASSIFY-33: builds the outputs on this host and compares them with the committed copies,
# so only the Pillow and zlib builds that wrote the committed files pass it.
@pytest.mark.host_png_bytes
def test_the_committed_outputs_are_what_the_script_writes_today(built, tmp_path):
    fresh = built["files"]
    for key, fresh_path in fresh.items():
        committed = output_files(ROOT)[key]
        assert os.path.isfile(committed), "run tools/art/make_env_ship.py: %s is missing" % committed
        assert sha(committed) == sha(fresh_path), (
            "%s differs from a fresh build, so the committed art is stale" % committed)
    # A build without the palette inputs is the one case this comparison could miss: it is what the
    # fixture used to produce, and if it matched the committed sheet the test would be pinning art the
    # generator no longer makes. Measured 2026-10-21: bare root f858d411..., palette build 2d213039...
    bare = ms.build(str(tmp_path / "no_palette_inputs"))
    assert sha(bare["sheet"]) != sha(fresh["sheet"]), (
        "the scene palette pass changed nothing, so this test cannot tell the two builds apart")
    assert sha(bare["sheet"]) != sha(output_files(ROOT)["sheet"]), (
        "the committed sheet is a build without the scene palette inputs")


def test_preview_holds_the_map_rendered_at_three_times_size(built):
    sheet = Image.open(built["files"]["sheet"]).convert("RGBA")
    preview = Image.open(built["files"]["preview"]).convert("RGBA")
    assert preview.width % 3 == 0 and preview.height % 3 == 0
    assert preview.width >= 20 * 16 * 3 and preview.height >= 15 * 16 * 3
    ship = load(built["files"]["map"])
    ground = [layer for layer in ship["layers"] if layer["name"] == "ground"][0]["data"]

    def block(tid: int) -> Image.Image:
        left, top = (tid % 16) * 16, (tid // 16) * 16
        return sheet.crop((left, top, left + 16, top + 16)).resize((48, 48), Image.Resampling.NEAREST)

    haystack = preview.tobytes()
    stride = preview.width * 4
    span = 48 * 4
    for tid in sorted({gid - 1 for gid in ground}):
        tile = block(tid).tobytes()
        first_row = tile[:span]
        found = False
        for y in range(preview.height - 48):
            row_start = y * stride
            limit = row_start + stride - span + 1
            offset = haystack.find(first_row, row_start, limit)
            while offset != -1 and not found:
                x = offset - row_start
                if x % 12 == 0:      # a 3x nearest neighbour block starts on a 3 px boundary
                    found = all(
                        haystack[(y + dy) * stride + x:(y + dy) * stride + x + span] == tile[dy * span:(dy + 1) * span]
                        for dy in range(1, 48))
                if not found:
                    offset = haystack.find(first_row, offset + 4, limit)
            if found:
                break
        assert found, "tile %d never appears in the preview at 3x" % tid


# ---------------------------------------------------------------------------- 7. the checker agrees

def test_check_env_tiles_passes_on_the_repository():
    failures, facts = ce.check(ROOT)
    assert failures == [], "\n".join(failures)
    assert facts["colours_used"] == 10
    assert facts["png"] == [256, 48]
    assert facts["worst_area_colours"] <= 3
    assert facts["worst_subtile_colours"] <= 3
    assert facts["nes_check"] == 0
    assert facts["reachable_cells"] == facts["walkable_cells"]
    assert facts["collision_blocked"] + facts["collision_walkable"] == 300


# ---------------------------------------------------------------------------- 8. the redrawn sea (card t_463bc8c1)
#
# The sea used to be a flat fill named after things it did not draw: on the sheet before this card, water_a, water_b,
# water_edge and water_foam were 256 identical pixels of $12, because the row they were forced into carried sea mid
# and nothing else. These tests measure the drawing and the built sheet, so a row move that flattens the sea again, or
# a redraw that goes back to one colour, fails here instead of shipping.

SEA = (0x02, 0x12, 0x21)          # deep, mid, crest: the three tones of bg3 in data/palettes/scene_ship.json
CARGO = ("crate", "crate_stack", "barrel", "table", "bollard")
WATER = ("water_a", "water_b", "water_edge", "water_deep", "water_foam")


def entry_of_key() -> dict:
    return {key: entry for key, entry, _hex, _use in ms.PALETTE}


def drawn_counts(name: str) -> dict:
    """Palette entries of one tile as this file draws it, keyed by 2C02 entry, backdrop included."""
    keys = entry_of_key()
    cell = ms.Cell()
    ms.DRAW[name](cell)
    counts = {}
    for y in range(16):
        for x in range(16):
            entry = keys[cell.get(x, y)]
            counts[entry] = counts.get(entry, 0) + 1
    return counts


def sheet_counts(image, name: str) -> dict:
    """The same count, read off a built sheet, so a repaint shows up as a colour that is not there."""
    keys = set(entry_of_key().values())
    chip = load(os.path.join(ROOT, "data", "nes_palette.json"))["colours"]
    rgba_of = {entry: tuple(int(chip[entry][i:i + 2], 16) for i in (1, 3, 5)) for entry in keys}
    tid = ms.BY_NAME[name][0]
    left, top = (tid % 16) * 16, (tid // 16) * 16
    rgb_of = {rgba: entry for entry, rgba in rgba_of.items()}
    counts = {}
    for y in range(16):
        for x in range(16):
            entry = rgb_of[image.getpixel((left + x, top + y))[:3]]
            counts[entry] = counts.get(entry, 0) + 1
    return counts


def test_the_water_family_is_drawn_as_water_in_three_tones():
    for name in WATER:
        counts = drawn_counts(name)
        used = set(counts) - {0x0F}
        assert used == set(SEA), "%s draws %s, the sea row carries $02 $12 $21" % (
            name, " ".join("$%02X" % entry for entry in sorted(used)))
        body = max(used, key=lambda entry: counts[entry])
        expect = 0x02 if name == "water_deep" else 0x12
        assert body == expect, "%s is mostly $%02X; deep water is $02 and the rest is $12" % (name, body)


def test_the_two_sea_frames_are_a_swell_and_the_edge_and_foam_are_not_the_same_tile():
    a = ms.Cell()
    b = ms.Cell()
    ms.water_a(a)
    ms.water_b(b)
    assert a.px != b.px, "water_a and water_b are the same picture, so the sea does not animate"
    crests = [drawn_counts(name)[0x21] for name in WATER]
    assert len(set(crests)) > 1, "every water tile carries the same number of crest pixels: %s" % crests
    # The edge tile is the waterline: its top row is foam, which no other water tile has.
    assert drawn_counts("water_edge")[0x21] > drawn_counts("water_deep")[0x21], (
        "the waterline carries less foam than the deep water")
    cell = ms.Cell()
    ms.water_edge(cell)
    assert [cell.get(x, 0) for x in range(16)].count("c") >= 8, (
        "the top row of water_edge is not a foam line")


def test_the_cargo_family_keeps_the_brass_its_row_can_show(built):
    """Q2 of card t_463bc8c1: brass is GIVEN a row, not quietly dropped from the drawing."""
    image = Image.open(built["files"]["sheet"]).convert("RGB")
    for name in CARGO:
        drawn = drawn_counts(name)[0x28]
        assert drawn > 0, "%s no longer draws any brass" % name
        kept = sheet_counts(image, name)[0x28]
        assert kept == drawn, "%s lost %d of its %d brass pixels to the row it was painted into" % (
            name, drawn - kept, drawn)


def test_the_scene_palette_pass_repaints_only_the_bunk_and_the_lifebuoy(built):
    """The rows were moved onto the drawing (card t_463bc8c1): what is left over is two other cards' art.

    Pinned exactly, because this is the number ruling 21.2 measured and 21.7 replaced: 762 pixels repainted by the
    old rows, 76 by these. A future redraw that raises it, or a row edit that raises it, has to move this test.
    """
    drawn = ms.render_sheet()
    image = Image.open(built["files"]["sheet"]).convert("RGBA")
    assert image.size == drawn.size
    changed = {}
    for tid, name, _kind, _solid, _climb, _group in ms.TILES:
        left, top = (tid % 16) * 16, (tid // 16) * 16
        count = 0
        for y in range(16):
            for x in range(16):
                if drawn.getpixel((left + x, top + y)) != image.getpixel((left + x, top + y)):
                    count += 1
        if count:
            changed[name] = count
    assert changed == {"bunk": 60, "lifebuoy": 16}, changed

