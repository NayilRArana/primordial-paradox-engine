"""Tests for the scene palettes (card NES-PALETTES, 2026-10-22).

Why this file exists: the palette rule was enforced by a manual step (`scene_palette.py apply`) that ran
once and was then silently undone by the next regeneration of the art, because the test suite itself runs
tools/art/title_car_v2.py and title_logo_v2.py. A rule that a rerun can erase is not a rule, so this test
asks the checker rather than trusting a comment: tools/check_scene_palettes.py measures the art on disk and
fails the suite when a scene stops fitting its declared palettes.

What is pinned, in order of how the tree fails:
  1. Both scene files exist, declare one backdrop, four background palettes of three, four sprite palettes
     of three, and every entry is a legal 2C02 entry from data/nes_palette.json.
  2. The check passes on the current art: the composed title frame, the car frame and the ship stack all
     satisfy tools/nes_composite_check.py, no 8x16 sprite group carries more than three colours, and every
     group fits one of the four sprite palettes.
  3. The budget stays honest: 25 colours on screen at most, counted the way the PPU counts them.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import check_scene_palettes  # noqa: E402
import scene_palette  # noqa: E402


def test_both_scene_files_declare_the_nes_budget():
    for name in ("title", "ship"):
        scene = scene_palette.load_scene(ROOT, name)
        assert len(scene.background) == 4, name
        assert len(scene.sprites) == 4, name
        for row in scene.background + scene.sprites:
            assert len(row) == 3, (name, row)
            for entry in row:
                assert scene.usable[entry], (name, entry)
        assert scene.usable[scene.backdrop], name
        assert scene.backdrop not in scene.bg_colours(), "%s spends the backdrop as a palette colour" % name


def test_the_art_on_disk_fits_the_scenes():
    report = {"scenes": {}, "failures": []}
    failures = check_scene_palettes.check_title(ROOT, report) + check_scene_palettes.check_ship(ROOT, report)
    assert not failures, "\n".join(failures)
    for key in ("title_frame", "title_car_frame", "ship_frame"):
        assert report[key]["exit"] == 0, (key, report[key]["report"])
    for name, asset in report["title_sprites"].items():
        assert asset["groups_over_three"] == 0, (name, asset)
        assert asset["groups_outside_a_palette"] == 0, (name, asset)
    for name, asset in report["ship_sprites"].items():
        assert asset["groups_over_three"] == 0, (name, asset)
        assert asset["groups_outside_a_palette"] == 0, (name, asset)


def test_the_scenes_stay_inside_the_colour_cap():
    for name in ("title", "ship"):
        budget = check_scene_palettes.scene_budget(scene_palette.load_scene(ROOT, name))
        assert budget["distinct_colours"] <= budget["limit"], name
        assert budget["background_colours"] <= 12, name
        assert budget["sprite_colours"] <= 12, name


def test_a_solve_keeps_a_pinned_sprite_half_and_its_judged_row(tmp_path):
    """Card t_a6a7a436: the ship's sprite half is a CAST decision, and a solve used to overwrite it.

    write_scene() wrote the scene file whole and emitted no `judged` key, so `solve --scene ship --write` deleted
    the audit row card t_1dc346b9 landed and re-solved the party's four walking triples back into the sailor's
    pool. Measured here on a scratch root that holds only the master palette and a copy of the shipped file: the
    solver's background half lands, the pinned sprite half, its notes and the judged row survive, and a file
    WITHOUT the pin still takes the solver's rows (the mechanism is the pin, not "never write sprites").
    """
    import shutil

    (tmp_path / "data" / "palettes").mkdir(parents=True)
    shutil.copy(os.path.join(ROOT, "data", "nes_palette.json"), str(tmp_path / "data" / "nes_palette.json"))
    with open(os.path.join(ROOT, "data", "palettes", "scene_ship.json"), encoding="utf-8") as handle:
        shipped = json.load(handle)
    target = tmp_path / "data" / "palettes" / "scene_ship.json"
    target.write_text(json.dumps(shipped, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    solver_rows = [[0x00, 0x10, 0x30], [0x02, 0x12, 0x30], [0x07, 0x17, 0x36], [0x08, 0x27, 0x28]]
    solver_background = [[0x00, 0x10, 0x30], [0x10, 0x28, 0x30], [0x02, 0x07, 0x17], [0x00, 0x02, 0x21]]
    scene_palette.write_scene(str(tmp_path), "ship", 0x0F, solver_background, solver_rows, ["solved by a rerun"])
    with open(str(target), encoding="utf-8") as handle:
        written = json.load(handle)

    assert written["sprites"] == shipped["sprites"], "a solve re-solved a pinned sprite half"
    assert written["notes"] == shipped["notes"], "a solve overwrote the notes that explain the pinned half"
    assert written["judged"] == shipped["judged"], "a solve deleted the judged row"
    assert written["sprites_pinned"] is True, written.get("sprites_pinned")
    background = [row["colours"] for row in written["background"]]
    assert background == solver_background, "the background half is the solver's and did not land"

    # The control: the same call on a file with no pin takes the solver's sprite rows.
    del shipped["sprites_pinned"]
    target.write_text(json.dumps(shipped, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scene_palette.write_scene(str(tmp_path), "ship", 0x0F, solver_background, solver_rows, ["solved by a rerun"])
    with open(str(target), encoding="utf-8") as handle:
        unpinned = json.load(handle)
    assert [row["colours"] for row in unpinned["sprites"]] == solver_rows, unpinned["sprites"]
    assert unpinned["judged"] == shipped["judged"], "the judged row is carried whether the half is pinned or not"


def test_the_check_reports_its_numbers_so_a_reviewer_can_read_them():
    """The card asks for the palette sets and the check output, so the report carries both as data."""
    path = os.path.join(ROOT, "output", "scene_palettes.json")
    code = check_scene_palettes.main(["--json", path, "--quiet"])
    assert code == 0, code
    with open(path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["failures"] == []
    assert set(saved["scenes"]) == {"title", "ship"}


WALKING_CAST = ("hadrian_ow_v2", "konrad_ow_v2", "zander_ow_v2", "percy_ow_v2", "sailor_ow_v2")


def test_the_solve_pool_and_the_judge_name_the_same_five_walking_sheets():
    """Card t_0b9c2faf Q3: two lists called SHIP_SPRITES disagreed, so the pool and the judge drew different casts.

    scene_palette.SHIP_SPRITES is what the solver pools and what `apply --scene ship` enforces; check_scene_palettes
    .SHIP_SPRITES is what the suite measures against the ship's four rows. On HEAD they were
    ["sailor_ow", "sailor_battle"] against the five walking sheets, so the pool enforced a 168x32 battle sheet into a
    walking room's triples (621 of its 2398 opaque pixels rewritten) while the judge did not look at it at all. One
    cast, one list, and the judged row is the third statement of it that has to agree.
    """
    pool = list(scene_palette.SHIP_SPRITES)
    judge = list(check_scene_palettes.SHIP_SPRITES)
    assert pool == judge, (pool, judge)
    assert tuple(pool) == WALKING_CAST, pool
    for retired in ("sailor_battle", "sailor_ow"):
        assert retired not in pool, "%s is retired from the ship's budget (card t_0b9c2faf)" % retired

    # The pool may not name a sheet that is not on disk, and the row may not name a sheet the pool does not.
    for name in pool:
        base = os.path.join(ROOT, "game", "sprites_src", "chars", name)
        assert os.path.isfile(base + ".png") and os.path.isfile(base + ".json"), base
    with open(os.path.join(ROOT, "data", "palettes", "scene_ship.json"), "r", encoding="utf-8") as handle:
        ship = json.load(handle)
    rows = [row for row in ship["judged"] if "ts_ship.png" in row["background"]]
    assert len(rows) == 1, rows
    judged = [os.path.basename(path)[:-4] for path in rows[0]["sprites"]]
    # The row's own order is the order card t_a6a7a436 wrote it in; the membership is what has to agree.
    assert sorted(judged) == sorted(pool), (judged, pool)


def test_the_retired_sailor_battle_sheet_is_rebuilt_by_nothing_and_stands_on_no_row():
    """Card t_0b9c2faf Q1 and Q2: sailor_battle.png is retired, and the two measurements that retire it.

    Q1: it is not the sailor fight's art. No GML file in any commit has ever named it (git log -S over
    game/scripts is empty), the encounter draws navy_sailor.png, and the battle screen's enemy slot is 32x32 px and
    reads game/sprites_src/enemies/<id>.png. Q2: it is judged on no row, and it must not be put back on one. Its own
    shape is why: every party battle frame is ONE reserved hero triple, and no frame of this sheet is, so no 24x32
    party slot can draw it; as background art on a strip, the best any strip's four background triples carry is 21
    of its 72 inked 8x8 tiles (wardroom), 20 on the deck.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_characters  # noqa: E402

    assert make_characters.writes_battle_sheet("sailor") is False, "the retired sheet would be rebuilt"
    assert make_characters.BATTLE_RETIRED == {"sailor"}
    for keeps in ("percy", "hadrian", "zander", "konrad"):
        assert make_characters.writes_battle_sheet(keeps) is True, keeps

    # The drawing stays on disk and is still the 168x32 seven frame sheet the ruling measured.
    base = os.path.join(ROOT, "game", "sprites_src", "chars", "sailor_battle")
    with open(base + ".json", "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (24, 32, 7), meta
    from PIL import Image  # noqa: E402
    with Image.open(base + ".png") as handle:
        assert handle.size == (168, 32), handle.size

    # No scene in the project names it on any row, judged or solved.
    with open(os.path.join(ROOT, "data", "scene_palettes.json"), "r", encoding="utf-8") as handle:
        whole = json.load(handle)
    for scene in whole["scenes"]:
        for row in scene["sprites"]:
            assert "sailor_battle" not in json.dumps(row), (scene["id"], row)
        for row in scene.get("judged", []):
            assert "sailor_battle" not in json.dumps(row), (scene["id"], row)

    # And no draw call names it, which is what "retired" means here: nothing in the game asks the art index for it.
    scripts = os.path.join(ROOT, "game", "scripts")
    for folder, _dirs, files in os.walk(scripts):
        for name in files:
            if not name.endswith(".gml"):
                continue
            with open(os.path.join(folder, name), "r", encoding="utf-8", errors="replace") as handle:
                assert "sailor_battle" not in handle.read(), "%s names the retired sheet" % name

    # The crux: a party battle frame is one reserved hero triple, and not one frame of this sheet is.
    entries_of = _frame_entries
    for hero in ("hadrian_battle", "percy_battle", "zander_battle", "konrad_battle"):
        per_frame = entries_of(os.path.join(ROOT, "game", "sprites_src", "chars", hero + ".png"), 24, 32)
        assert all(len(one) == 3 for one in per_frame), (hero, per_frame)
    retired = entries_of(os.path.join(ROOT, "game", "sprites_src", "chars", "sailor_battle.png"), 24, 32)
    assert all(len(one) > 3 for one in retired), retired


def _frame_entries(path, frame_w, frame_h):
    """The set of 2C02 entries in each frame of a sheet, read through the project's own palette table."""
    from PIL import Image  # noqa: E402

    _colours, _usable, index_of = scene_palette.load_master(ROOT)
    out = []
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
        pixels = image.load()
        for frame in range(image.width // frame_w):
            entries = set()
            for y in range(frame_h):
                for x in range(frame * frame_w, (frame + 1) * frame_w):
                    r, g, b, a = pixels[x, y]
                    if a == 0:
                        continue
                    entry = index_of.get((r, g, b))
                    assert entry is not None, (path, frame, x, y, (r, g, b))
                    entries.add(entry)
            out.append(entries)
    return out
