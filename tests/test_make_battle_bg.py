#!/usr/bin/env python3
"""Pins for the battle strips' party block floor (card t_d64eb2a9).

The ruling on card t_8c27208b (knowledge/PALETTE-RULINGS-2026-10-25.md section 7.4 point 2) decided the floor
under the party block is the shared backdrop $0F on the battle strips, because the four party bodies are the
light entry of each hero triple and those four clear RULE 0 point 2 on $0F and not on the mixed floors the
corridor and wardroom carry. tools/art/make_battle_bg.py draws it. These tests hold down four things:

  1. the block's placement is READ from data/ui_layouts.json rather than typed, and the layout's tile-unit
     party list and its pixel-unit sprites list agree, which is the one unit error the loader could make
     silently;
  2. the corridor and the wardroom strip are $0F over the whole block inside the strip, and the deck night
     and quay dusk strips are not, because no card decided their floor;
  3. the party pass moves EXACTLY the block and nothing else: the pixel diff against the same scene built
     without the flag is the clipped block and its pixel count, no more, no less;
  4. the committed strip PNGs are what the generator writes now, so the shipped art and the code that owns
     it cannot drift apart (the same shape tests/test_title_art_v2.py uses for the v2 title art).

No em dash or en dash anywhere in this file: the project refuses them at the door (tests/test_project.py).

Run: python -m pytest tests/test_make_battle_bg.py -q
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for folder in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "tools", "art")):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import make_battle_bg as mb  # noqa: E402

LAYOUT = os.path.join(ROOT, "data", "ui_layouts.json")
BG_DIR = os.path.join(ROOT, "game", "sprites_src", "bg")


def scene(name: str) -> dict:
    for entry in mb.SCENES:
        if entry["name"] == name:
            return entry
    raise AssertionError("no scene named %r" % name)


@pytest.fixture(scope="module")
def built():
    entries, _ = mb.load_palette(ROOT)
    rects, _ = mb.load_party_block(ROOT)
    table = {}
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        scene_dict = scene(name)
        table[name] = (
            mb.build_scene(scene_dict, entries, rects),
            mb.build_scene(dict(scene_dict, party_floor=False), entries, rects),
        )
    return entries, rects, table


def test_the_block_is_read_from_the_layout_in_pixels():
    rects, path = mb.load_party_block(ROOT)
    assert os.path.abspath(path) == os.path.abspath(LAYOUT)
    assert rects == [(224, 32, 24, 32), (224, 64, 24, 32), (224, 96, 24, 32), (224, 128, 24, 32)]

    with open(LAYOUT, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    battle = [screen for screen in data["screens"] if screen["name"] == "battle"][0]
    tile = data["frame"]["tile"]
    # The party list is in tiles and the sprites list in pixels: both describe the same four slots.
    assert [(slot["x"] * tile, slot["y"] * tile) for slot in battle["party"]] == [(x, y) for x, y, _, _ in rects]
    assert all(slot["w"] * tile == w and slot["h"] * tile == h for slot, (_, _, w, h) in zip(battle["party"], rects))


def test_the_loader_refuses_a_layout_whose_two_lists_disagree(tmp_path):
    with open(LAYOUT, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    battle = [screen for screen in data["screens"] if screen["name"] == "battle"][0]
    # Move one slot in the pixel list only, which is how a silent unit error would look.
    party = [sprite for sprite in battle["sprites"] if sprite.get("role") == "party"]
    party[0]["y"] += 8
    broken = tmp_path / "data"
    broken.mkdir()
    (broken / "ui_layouts.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit) as refused:
        mb.load_party_block(str(tmp_path))
    assert "is not the sprite at pixel" in str(refused.value) or "party sprite" in str(refused.value)


def test_only_the_corridor_and_the_wardroom_declare_the_floor():
    declared = sorted(entry["name"] for entry in mb.SCENES if entry.get("party_floor"))
    assert declared == ["corridor", "wardroom"]


def test_the_block_is_the_backdrop_on_the_two_strips_that_declare_it(built):
    entries, rects, table = built
    backdrop = entries[mb.BACKDROP]
    for name in ("corridor", "wardroom"):
        pixels = table[name][0]["pixels"]
        floor = table[name][0]["party_floor"]
        assert floor is not None, name
        assert floor["pixels"] == 1920, "24 px by the 80 rows of the block that lie inside the 112 px strip"
        for x, y, w, h in rects:
            for py in range(y, min(mb.H, y + h)):
                for px in range(x, x + w):
                    assert pixels[py][px] == backdrop, "%s is not $0F at %d,%d" % (name, px, py)


def test_the_other_two_strips_are_left_alone(built):
    entries, rects, table = built
    backdrop = entries[mb.BACKDROP]
    for name in ("deck_night", "quay_dusk"):
        assert table[name][0]["party_floor"] is None, name
        pixels = table[name][0]["pixels"]
        not_black = 0
        for x, y, w, h in rects:
            for py in range(y, min(mb.H, y + h)):
                for px in range(x, x + w):
                    not_black += pixels[py][px] != backdrop
        # Not a decision, a measurement: these floors were scoped out of the card, so they are not $0F.
        assert not_black > 0, "%s already reads as a black block; re-measure before changing the card" % name


def test_the_pass_moves_the_block_and_nothing_else(built):
    for name in ("corridor", "wardroom"):
        with_flag, without = built[2][name]
        moved = set()
        for y in range(mb.H):
            for x in range(mb.W):
                if with_flag["pixels"][y][x] != without["pixels"][y][x]:
                    moved.add((x, y))
        assert len(moved) == with_flag["party_floor"]["pixels"] == 1920, name
        assert min(x for x, _ in moved) == 224 and max(x for x, _ in moved) == 247, name
        assert min(y for _, y in moved) == 32 and max(y for _, y in moved) == 111, name


def test_the_tile_count_describes_what_ships(built):
    """The pass runs before the tile count, so a counted tile is a shipped tile."""
    for name in ("corridor", "wardroom"):
        with_flag = built[2][name][0]
        rebuilt = {}
        for ty in range(mb.H // mb.TILE):
            for tx in range(mb.W // mb.TILE):
                block = tuple(
                    with_flag["pixels"][ty * mb.TILE + y][tx * mb.TILE + x]
                    for y in range(mb.TILE)
                    for x in range(mb.TILE)
                )
                rebuilt.setdefault(block, []).append((tx, ty))
        assert len(rebuilt) == len(with_flag["tiles"]), name


def test_the_committed_strips_are_what_the_generator_writes(built, tmp_path):
    entries, _, table = built
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        path = tmp_path / ("bg_battle_%s.png" % name)
        mb.write_png(table[name][0]["pixels"], str(path))
        committed = os.path.join(BG_DIR, "bg_battle_%s.png" % name)
        assert path.read_bytes() == open(committed, "rb").read(), (
            "run tools/art/make_battle_bg.py: %s is not what the generator writes" % committed
        )
        assert Image.open(committed).size == (mb.W, mb.H)


def test_the_sidecar_names_the_floor_where_it_applies(built):
    entries, _, table = built
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        scene_dict = scene(name)
        meta = mb.scene_json(scene_dict, table[name][0], entries, "bg_battle_%s.png" % name, "x.json")
        if scene_dict.get("party_floor"):
            floor = meta["party_floor"]
            assert floor["hex"] == entries[mb.BACKDROP]
            assert floor["pixels"] == 1920
            assert "t_d64eb2a9" in floor["reason"]
        else:
            assert "party_floor" not in meta, name
