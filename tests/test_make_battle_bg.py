#!/usr/bin/env python3
"""Pins for the battle strips' party block floor and the scene palette writer (cards t_d64eb2a9, t_5802ecdb).

The ruling on card t_8c27208b (knowledge/PALETTE-RULINGS-2026-10-25.md section 7.4 point 2) decided the floor
under the party block is the shared backdrop $0F on the battle strips, because the four party bodies are the
light entry of each hero triple and those four clear RULE 0 point 2 on $0F and not on the mixed floors the
corridor and wardroom carry. tools/art/make_battle_bg.py draws it. Card t_d64eb2a9 landed it on the corridor and
the wardroom and left the deck night and the quay dusk named as a gamedev decision; card t_0949bd4e made that
decision (section 12 point 2) and card t_12c9b18f extended the pass to both, so all four strips now declare it.
These tests hold down six things:

  1. the block's placement is READ from data/ui_layouts.json rather than typed, and the layout's tile-unit
     party list and its pixel-unit sprites list agree, which is the one unit error the loader could make
     silently;
  2. all FOUR strips are $0F over the whole block inside the strip, which is the change card t_12c9b18f made
     on the two the earlier card was scoped out of;
  3. the party pass moves EXACTLY the block and nothing else: the pixel diff against the same scene built
     without the flag is the clipped block and its pixel count, no more, no less;
  4. the committed strip PNGs are what the generator writes now, so the shipped art and the code that owns
     it cannot drift apart (the same shape tests/test_title_art_v2.py uses for the v2 title art).
  5. the scene palette writer carries an existing file's `judged` rows through unchanged and in the place
     that file keeps them, writes no such key on a fresh tree, and refuses a file that is not a scene palette
     for the scene it is drawing, because one regeneration of a strip used to delete a cast ruling and
     nothing failed (card t_5802ecdb);
  6. the `notes` list is the generator's, not a field hand edits append to: the deck's four declared sprite
     rows ARE the rows its file carries, and every one of the four committed palette files reproduces byte
     for byte from the generator plus its own `judged` rows (card t_8ebcb489).

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


def test_all_four_strips_declare_the_floor():
    """One floor for the room: card t_0949bd4e ruled the deck and the quay in (section 12 point 2)."""
    declared = sorted(entry["name"] for entry in mb.SCENES if entry.get("party_floor"))
    assert declared == ["corridor", "deck_night", "quay_dusk", "wardroom"]


def test_the_block_is_the_backdrop_on_every_strip_the_screen_draws(built):
    entries, rects, table = built
    backdrop = entries[mb.BACKDROP]
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        pixels = table[name][0]["pixels"]
        floor = table[name][0]["party_floor"]
        assert floor is not None, name
        assert floor["pixels"] == 1920, "24 px by the 80 rows of the block that lie inside the 112 px strip"
        for x, y, w, h in rects:
            for py in range(y, min(mb.H, y + h)):
                for px in range(x, x + w):
                    assert pixels[py][px] == backdrop, "%s is not $0F at %d,%d" % (name, px, py)


def test_the_two_extended_strips_were_not_on_the_backdrop_before_the_flag(built):
    """The change is the flag's, not the art's: without it the deck and the quay stand on their own floors.

    This is the before half of card t_12c9b18f's pair fail column, measured on the pixels rather than quoted from
    the card, and it fails loudly if the strips ever come out black with the flag off (which would mean the strip
    was repainted rather than floored).
    """
    entries, rects, table = built
    backdrop = entries[mb.BACKDROP]
    for name in ("deck_night", "quay_dusk"):
        assert table[name][0]["party_floor"] is not None, name
        assert table[name][1]["party_floor"] is None, name
        not_black = 0
        for x, y, w, h in rects:
            for py in range(y, min(mb.H, y + h)):
                for px in range(x, x + w):
                    not_black += table[name][1]["pixels"][py][px] != backdrop
        assert not_black > 0, "%s already reads as a black block without the flag; re-measure the card" % name


def test_the_pass_moves_the_block_and_nothing_else(built):
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
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
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
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
    """The strip in git is the picture the generator draws, pixel for pixel.

    Pixels, not PNG bytes (card t_78db3b2c, measured 2026-10-25). A Pine run rebuilt bg_battle_corridor.png
    from these same pixels and held a file byte identical to this machine's copy (sha256 0d1036688fc56c77),
    while the copy an offloaded run wrote out of the generator differed from byte 36 on: byte 36 is the low
    byte of the first IDAT length, so the signature and the whole IHDR (width, height, depth, colour type,
    interlace) agreed and only the deflate differed. That made the old byte comparison a report on the zlib
    build, not on the art, and it could not be green off Windows. What this pin has to catch is stale art,
    and stale art is a pixel difference; test_title_art_v2.py reads its committed sheet the same way.
    """
    entries, _, table = built
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        path = tmp_path / ("bg_battle_%s.png" % name)
        mb.write_png(table[name][0]["pixels"], str(path))
        committed = os.path.join(BG_DIR, "bg_battle_%s.png" % name)
        assert os.path.isfile(committed), "run tools/art/make_battle_bg.py: %s is missing" % committed
        with Image.open(path) as fresh, Image.open(committed) as shipped:
            assert shipped.size == (mb.W, mb.H), committed
            assert fresh.size == shipped.size, (
                "%s: the generator writes %s and the committed file is %s" % (name, fresh.size, shipped.size)
            )
            assert fresh.convert("RGBA").tobytes() == shipped.convert("RGBA").tobytes(), (
                "run tools/art/make_battle_bg.py: %s is not what the generator writes, pixel for pixel" % committed
            )


def test_the_sidecar_names_the_floor_where_it_applies(built):
    entries, _, table = built
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        scene_dict = scene(name)
        meta = mb.scene_json(scene_dict, table[name][0], entries, "bg_battle_%s.png" % name, "x.json")
        floor = meta["party_floor"]
        assert floor["hex"] == entries[mb.BACKDROP]
        assert floor["pixels"] == 1920
        assert "t_d64eb2a9" in floor["reason"], "the ruling that set the floor is named on every record"
        # The two strips that card t_d64eb2a9 was scoped out of name the card that ruled THEM, so a reader of the
        # deck's sidecar does not learn only about the corridor (card t_12c9b18f).
        if name in ("deck_night", "quay_dusk"):
            assert "t_12c9b18f" in floor["reason"], name
        else:
            assert "t_12c9b18f" not in floor["reason"], "the two first strips are untouched by that card"


# -----------------------------------------------------------------------------------------------------------------
# The scene palette writer (card t_5802ecdb). A file the generator owns is written whole, so a `judged` row that
# only a card wrote is one regeneration away from being deleted with nothing failing. These pins are the writer's.

JUDGED = {
    "background": "output/bg_battle_corridor_frame.png",
    "sprites": ["game/sprites_src/chars/percy_battle.png"],
    "note": "a test row, standing in for a cast ruling",
    "exempt": "a test exemption, so the row carries the field a ruled row carries",
}


def write_scene_file(root, name: str, payload: dict):
    """A scene palette file in a throwaway tree, written the way the hand edited ones are (indent 2, trailing \\n)."""
    folder = root / "data" / "palettes"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("scene_battle_%s.json" % name)
    path.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
    return path


def test_a_judged_row_keeps_its_bytes_through_the_writer(tmp_path, built):
    entries, _, _ = built
    corridor = scene("corridor")
    payload = mb.scene_palette_json(corridor, entries)
    # The hand written files keep `judged` straight after `notes`, so the row goes exactly where they put it.
    ordered = {}
    for key, value in payload.items():
        ordered[key] = value
        if key == "notes":
            ordered["judged"] = [JUDGED]
    path = write_scene_file(tmp_path, "corridor", ordered)
    before = path.read_bytes()

    written, kept = mb.write_scene_palette(str(tmp_path), corridor, entries)

    assert os.path.abspath(written) == os.path.abspath(str(path))
    assert kept == 1
    after = json.loads(path.read_bytes().decode("utf-8"))
    assert after["judged"] == [JUDGED], "the row is carried as data, not re-derived from the generator"
    assert list(after) == list(ordered), "the key stays in the position the hand written file keeps it in"
    assert path.read_bytes() == before, "no palette moved, so a regeneration rewrites the same bytes"


def test_a_fresh_tree_writes_no_judged_key(tmp_path, built):
    entries, _, _ = built
    wardroom = scene("wardroom")

    written, kept = mb.write_scene_palette(str(tmp_path), wardroom, entries)

    with open(written, "rb") as handle:
        payload = json.loads(handle.read().decode("utf-8"))
    assert kept == 0
    assert "judged" not in payload, "a tree with no file gets a clean file, not an empty audit list"
    assert payload["kind"] == "scene_palette"
    assert payload["scene"] == "battle_wardroom"
    assert payload["background"] == mb.scene_palette_json(wardroom, entries)["background"]


@pytest.mark.parametrize(
    "bait",
    [
        {"format": 1, "kind": "battle_background", "scene": "battle_corridor"},
        {"format": 1, "kind": "scene_palette", "scene": "battle_wardroom"},
    ],
    ids=["not a scene palette", "another scene"],
)
def test_the_writer_refuses_a_file_that_is_not_this_scene(tmp_path, built, bait):
    entries, _, _ = built
    corridor = scene("corridor")
    path = write_scene_file(tmp_path, "corridor", dict(bait, judged=[JUDGED]))
    before = path.read_bytes()

    with pytest.raises(SystemExit) as refused:
        mb.write_scene_palette(str(tmp_path), corridor, entries)

    message = str(refused.value)
    assert "scene_battle_corridor.json" in message, "the refusal names the file it will not overwrite"
    assert "not a scene palette for battle_corridor" in message, "and the scene it wanted"
    assert path.read_bytes() == before, "a refused write leaves the file exactly as it was"


# -----------------------------------------------------------------------------------------------------------------
# The notes list and the declared sprite rows (card t_8ebcb489). The writer owns both, so the two defects this card
# closed are pinned the same way: what the generator declares has to be what the committed file carries, and a note
# added to the output has to be one regeneration away from gone rather than a title to be carried.

PALETTE_DIR = os.path.join(ROOT, "data", "palettes")


def committed_palette(name: str) -> str:
    return os.path.join(PALETTE_DIR, "scene_battle_%s.json" % name)


def test_the_deck_declares_the_four_rows_its_own_file_carries():
    """The rows are read from the file, not from the corridor.

    Until card t_8ebcb489 SCENES carried the corridor's boilerplate rows for the deck while the deck's own file
    carried the four rows card t_cc0c5bd5 solved, so a regeneration reverted a measured decision: 46 changed lines,
    0 of them a judged row. A file and its generator that disagree is the defect, and the measured set is the record.
    """
    declared = scene("deck_night")["sprites"]
    assert declared == [
        ("sp0", [0x00, 0x0F, 0x10]),
        ("sp1", [0x02, 0x0F, 0x30]),
        ("sp2", [0x07, 0x17, 0x36]),
        ("sp3", [0x08, 0x27, 0x28]),
    ], "the deck's four rows are the 2026-10-24 solve (card t_cc0c5bd5), not a copy of another strip's"
    assert declared != scene("corridor")["sprites"], (
        "the corridor's rows used to live here; if they are back, a regeneration is reverting the deck again"
    )
    with open(committed_palette("deck_night"), "r", encoding="utf-8-sig") as handle:
        committed = json.load(handle)
    assert [list(row["colours"]) for row in committed["sprites"]] == [colours for _, colours in declared]


def test_a_regeneration_reproduces_every_committed_palette_file(tmp_path, built):
    """The end to end property card t_12c9b18f's acceptance needs: regenerate, diff, 0 lines.

    Nothing is excluded from the comparison. The rows, the notes and the carried `judged` rows all have to come back
    byte for byte, which is what stops the next strip regeneration from reverting a hand decision.
    """
    entries, _, _ = built
    for name in ("corridor", "wardroom", "deck_night", "quay_dusk"):
        folder = tmp_path / name / "data" / "palettes"
        folder.mkdir(parents=True)
        (folder / ("scene_battle_%s.json" % name)).write_bytes(open(committed_palette(name), "rb").read())

        written, _kept = mb.write_scene_palette(str(tmp_path / name), scene(name), entries)

        assert os.path.abspath(written) == os.path.abspath(str(folder / ("scene_battle_%s.json" % name)))
        assert open(written, "rb").read() == open(committed_palette(name), "rb").read(), (
            "%s does not reproduce from the generator: run tools/art/make_battle_bg.py" % name
        )


def test_a_hand_added_note_does_not_survive_a_regeneration(tmp_path, built):
    """`judged` is carried because it is a whole key only a card writes. `notes` is not: it is the generator's text.

    So a note that has to survive belongs in SCENES, and a note typed into the written file is one regeneration away
    from gone. This is the decision, not an accident, so it is pinned.
    """
    entries, _, _ = built
    quay = scene("quay_dusk")
    payload = mb.scene_palette_json(quay, entries)
    payload["notes"] = list(payload["notes"]) + ["a hand typed note, standing in for a ruling written into the file"]
    path = write_scene_file(tmp_path, "quay_dusk", payload)
    assert "a hand typed note" in path.read_text(encoding="utf-8")

    mb.write_scene_palette(str(tmp_path), quay, entries)

    after = json.loads(path.read_bytes().decode("utf-8"))
    assert "a hand typed note" not in json.dumps(after), "notes are the generator's whole list"
    assert after["notes"] == mb.scene_palette_json(quay, entries)["notes"]


def test_the_two_hand_notes_that_must_survive_are_lines_in_the_generator():
    """The record is not lost by owning the notes list: the two ruling notes ARE generator content now."""
    deck_notes = " ".join(scene("deck_night")["notes"])
    quay_notes = " ".join(scene("quay_dusk")["notes"])
    assert "t_cc0c5bd5" in deck_notes, "the deck's 2026-10-24 solve note has to survive a regeneration"
    assert "party_cast" in deck_notes, "and it has to say the rows are the declaration, not the spend"
    assert "t_4f18c0ac" in quay_notes, "the quay's no cast and no judged row ruling has to survive a regeneration"


