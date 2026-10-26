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
    # Card t_23b5739a pinned the BACKGROUND half of the shipped file too. This test is about the sprite half, so
    # its scratch copy drops that one key; the background pin and its own control are measured below.
    shipped.pop("background_pinned", None)
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


def test_a_solve_keeps_a_pinned_background_half(tmp_path):
    """Card t_23b5739a: a pinned background half survives a `solve --write`, and the key is the mechanism.

    The rows are an INPUT to the pixels of ts_ship.png (make_env_ship's scene palette pass repaints the sheet into
    them), so a solve that rewrites them rebuilds a different PNG. The key still does that job for a half that
    genuinely is a ruling; what changed on card t_463cb8c1 is that the SHIP no longer needs it, because its rows are
    now the measured best fit to the drawing `solve_ship()` itself measures, and a worse proposal is refused instead
    of written (test_a_ship_solve_will_not_write_a_worse_proposal). So this test seeds its own scratch copy with the
    key rather than asserting the shipped file carries it, and keeps its control: with the key the rows stay, and
    without it the same call moves them.
    """
    import shutil

    (tmp_path / "data" / "palettes").mkdir(parents=True)
    shutil.copy(os.path.join(ROOT, "data", "nes_palette.json"), str(tmp_path / "data" / "nes_palette.json"))
    with open(os.path.join(ROOT, "data", "palettes", "scene_ship.json"), encoding="utf-8") as handle:
        shipped = json.load(handle)
    pinned = json.loads(json.dumps(shipped))
    pinned["background_pinned"] = True
    target = tmp_path / "data" / "palettes" / "scene_ship.json"
    target.write_text(json.dumps(pinned, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    solver_rows = [[0x00, 0x10, 0x30], [0x02, 0x12, 0x30], [0x07, 0x17, 0x36], [0x08, 0x27, 0x28]]
    solver_background = [[0x00, 0x10, 0x30], [0x10, 0x28, 0x30], [0x02, 0x07, 0x17], [0x00, 0x02, 0x21]]
    scene_palette.write_scene(str(tmp_path), "ship", 0x0F, solver_background, solver_rows, ["solved by a rerun"])
    with open(str(target), encoding="utf-8") as handle:
        written = json.load(handle)

    assert [row["colours"] for row in written["background"]] == [row["colours"] for row in pinned["background"]], (
        "a solve moved a pinned background half, which repaints ts_ship.png")
    assert written["background_pinned"] is True, written.get("background_pinned")
    assert written["notes"] == pinned["notes"], "the note that explains the pin was overwritten"
    assert written["judged"] == pinned["judged"], "a solve deleted the judged row"

    # The control: drop the key and the same call moves the background rows, so the pin is the mechanism.
    pinned.pop("background_pinned")
    target.write_text(json.dumps(pinned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scene_palette.write_scene(str(tmp_path), "ship", 0x0F, solver_background, solver_rows, ["solved by a rerun"])
    with open(str(target), encoding="utf-8") as handle:
        unpinned = json.load(handle)
    assert [row["colours"] for row in unpinned["background"]] == solver_background, unpinned["background"]
    assert "background_pinned" not in unpinned


def test_the_check_reports_its_numbers_so_a_reviewer_can_read_them(tmp_path):
    """The card asks for the palette sets and the check output, so the report carries both as data.

    Card t_8690e219: `output/scene_palettes.json` is COMMITTED (card t_933d8840), and this test used to write it
    straight into the tree and assert nothing about the file it had just overwritten. So the suite rewrote a tracked
    file on every run and could never notice when the committed copy stopped matching what the checker writes, which
    is exactly how the report went stale on 17c3660 and stayed stale for five commits. The run now lands in a scratch
    file and the committed copy has to equal it field for field, so a change to the ship's rows or cast that does not
    come with a regenerated report is a red test instead of a silent rewrite.

    Compared as parsed JSON and not as bytes on purpose: this file is committed with CRLF on Windows while the gate
    also runs on Linux (see the TOWN-PALETTES-LF entry in DEVLOG.md), so bytes would fail on the machine, not the tree.
    The content is what is pinned; the frame names in the report are basenames for the same reason.
    """
    fresh_path = tmp_path / "scene_palettes.json"
    code = check_scene_palettes.main(["--json", str(fresh_path), "--quiet"])
    assert code == 0, code
    with open(fresh_path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["failures"] == []
    assert set(saved["scenes"]) == {"title", "ship"}

    committed_path = os.path.join(ROOT, "output", "scene_palettes.json")
    with open(committed_path, "r", encoding="utf-8") as handle:
        committed = json.load(handle)
    assert committed == saved, (
        "output/scene_palettes.json is stale: it is not what the checker writes today. Regenerate it with "
        "`python tools/check_scene_palettes.py --json output/scene_palettes.json` and commit the result "
        "(card t_8690e219).")

    # Card t_8bb7bdea: the compared content has to be platform free, or the same tree cannot agree with itself.
    # The report embeds the checker's stdout, and that stdout used to spend the local path separator in its
    # palette line: `data\\nes_palette.json` on Windows against `data/nes_palette.json` on Linux, one red row on
    # the Pine gate with every measured number identical. A committed record may not carry an OS path.
    for key in ("title_frame", "title_car_frame", "ship_frame"):
        for line in committed[key]["report"]:
            assert "\\" not in line, (
                "%s carries the local path separator, so the report cannot be reproduced on another platform: "
                "%r (card t_8bb7bdea). Print it with tools/nes_composite_check.py's shown_path() and regenerate."
                % (key, line))


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
    """Card t_0b9c2faf Q1 and Q2 retired the sheet; card t_4848159e took the drawing out of the tree.

    Q1: it is not the sailor fight's art. No GML file in any commit has ever named it (git log -S over
    game/scripts is empty), the encounter draws navy_sailor.png, and the battle screen's enemy slot is 32x32 px and
    reads game/sprites_src/enemies/<id>.png. Q2: it is judged on no row, and it must not be put back on one. Its own
    shape was why: every party battle frame is ONE reserved hero triple, and no frame of this sheet was, so no 24x32
    party slot could draw it; as background art on a strip, the best any strip's four background triples carried was
    21 of its 72 inked 8x8 tiles (wardroom), 20 on the deck.

    Since card t_4848159e the 168x32 seven frame drawing and its sidecar are deleted, because a declared retirement
    that still ships is not a retirement: tools/sync_art.py mirrors game/sprites_src/chars/ whole, so the sheet was an
    entry in the art index and a GMIncludedFile in the project. The measurements above cannot be re-taken here
    because the input is gone; they live in knowledge/PALETTE-RULINGS-2026-10-25.md section 19. What this test keeps
    is everything that can still be measured: the generator refuses the sheet, no row names it, no draw call names
    it, and the drawing is not back on disk.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_characters  # noqa: E402

    assert make_characters.writes_battle_sheet("sailor") is False, "the retired sheet would be rebuilt"
    assert make_characters.BATTLE_RETIRED == {"sailor"}
    for keeps in ("percy", "hadrian", "zander", "konrad"):
        assert make_characters.writes_battle_sheet(keeps) is True, keeps

    # Card t_4848159e: the drawing is gone from the authored tree, so nothing can rebuild it or mirror it.
    base = os.path.join(ROOT, "game", "sprites_src", "chars", "sailor_battle")
    assert not os.path.exists(base + ".png"), "the retired sheet is back on disk: %s.png" % base
    assert not os.path.exists(base + ".json"), "the retired sidecar is back on disk: %s.json" % base

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

    # The crux, half of it still measurable: every party battle frame is exactly one reserved hero triple. The other
    # half, that no frame of the deleted sheet was, was measured before the input went away (ruling section 19).
    entries_of = _frame_entries
    for hero in ("hadrian_battle", "percy_battle", "zander_battle", "konrad_battle"):
        per_frame = entries_of(os.path.join(ROOT, "game", "sprites_src", "chars", hero + ".png"), 24, 32)
        assert all(len(one) == 3 for one in per_frame), (hero, per_frame)


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


# --------------------------------------------------------------------------- the drawing under the rows (card t_463cb8c1)

def test_the_ship_file_carries_no_background_pin_and_its_rows_are_the_drawings_fit():
    """Card t_463cb8c1: the rows are the measured best fit to the drawing, so the pin is gone and the number is the pin.

    Ruling section 23 chose the four rows by scoring all 1929501 four row sets the sheet's nine non backdrop entries
    can make; this is the number that has to hold when the art moves: 76 pixels of the drawing repainted, in two
    tiles. It is pinned rather than merely reported because it is what the whole card is for, and a redraw that
    pushes it up is a decision someone has to make on purpose.
    """
    with open(os.path.join(ROOT, "data", "palettes", "scene_ship.json"), encoding="utf-8") as handle:
        shipped = json.load(handle)
    assert "background_pinned" not in shipped, (
        "the ship carries the old background pin again; its rows are now the fit to the drawing, and the solver "
        "refuses a worse proposal instead (ruling section 23)")
    assert [[int(entry) for entry in row["colours"]] for row in shipped["background"]] == [
        [0x00, 0x10, 0x30], [0x00, 0x10, 0x28], [0x07, 0x17, 0x28], [0x02, 0x12, 0x21]], shipped["background"]

    result = scene_palette.solve_ship(ROOT)
    assert result["file"]["pixels"] == 76, (
        "the ship's rows repaint %d of the drawing's pixels; they were chosen at 76 (bunk 60, lifebuoy 16)"
        % result["file"]["pixels"])
    assert result["file"]["tiles_split"] == 2, result["file"]
    assert result["proposal"]["pixels"] > result["file"]["pixels"], (
        "the solver now proposes a better fit (%d against %d): the rows are no longer the drawing's best fit, so "
        "ruling section 23 needs re-measuring" % (result["proposal"]["pixels"], result["file"]["pixels"]))


def test_a_ship_solve_will_not_write_a_worse_proposal(tmp_path):
    """Card t_463cb8c1: the floor. A proposal that repaints more of the drawing than the shipped rows is not written.

    This is what replaced `background_pinned` on the ship. The first half seeds a scratch root with the shipped file
    and asserts the refusal; the second seeds the same root with four sea rows, which are obviously not the art's, and
    asserts that the same call DOES write, so the guard is a floor and not a pin wearing a different name.
    """
    import shutil

    (tmp_path / "data" / "palettes").mkdir(parents=True)
    shutil.copy(os.path.join(ROOT, "data", "nes_palette.json"), str(tmp_path / "data" / "nes_palette.json"))
    with open(os.path.join(ROOT, "data", "palettes", "scene_ship.json"), encoding="utf-8") as handle:
        shipped = json.load(handle)
    target = tmp_path / "data" / "palettes" / "scene_ship.json"
    target.write_text(json.dumps(shipped, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    before = target.read_bytes()

    refused = scene_palette.solve_ship(str(tmp_path), write=True)
    assert refused["written"] is False, "a solve wrote a proposal that repaints more than the file's rows"
    assert refused["proposal"]["pixels"] > refused["file"]["pixels"], refused
    assert target.read_bytes() == before, "the file moved even though the proposal was refused"

    # The control: a set that is not the drawing's at all. The same proposal beats it, so the call writes.
    sea = [[0x02, 0x12, 0x21]] * 4
    control = json.loads(json.dumps(shipped))
    for index, row in enumerate(control["background"]):
        row["colours"] = list(sea[index])
        row["hex"] = ["#%02x%02x%02x" % scene_palette.load_master(ROOT)[0][entry] for entry in sea[index]]
    target.write_text(json.dumps(control, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    written = scene_palette.solve_ship(str(tmp_path), write=True)
    assert written["written"] is True, "the floor refused a proposal that is better than the file's rows"
    with open(str(target), encoding="utf-8") as handle:
        after = json.load(handle)
    assert [[int(entry) for entry in row["colours"]] for row in after["background"]] == [
        [int(entry) for entry in row] for row in written["scene"].background], after["background"]

