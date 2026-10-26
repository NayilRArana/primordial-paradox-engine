"""Tests for tools/scene_palette_set.py (card PAL-SYSTEM, 2026-10-22).

Why this file exists: ART-BIBLE RULE 0 makes a scene's palette set an input to the art, not a report on it.
That only holds if the file is real, complete for every scene, and derived from the per scene files that the
art lane already solved. The strongest test here is the regeneration test: `build()` must reproduce the file
that is on disk byte for byte, so a hand edit that drifts from the measured art fails the suite.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import scene_palette_set  # noqa: E402


def data():
    return scene_palette_set.load(ROOT)


def test_file_is_there_and_is_the_right_kind():
    payload = data()
    assert payload["kind"] == "scene_palettes"
    assert payload["format"] == 1
    assert payload["master"] == "data/nes_palette.json"


def test_every_scene_file_the_art_lane_solved_is_in_the_set():
    listed = set(scene_palette_set.scene_ids(data()))
    on_disk = {os.path.basename(path)[len("scene_"):-len(".json")]
               for path in scene_palette_set.source_files(ROOT)}
    assert on_disk <= listed, "a scene file on disk is not in the palette set"
    assert len(listed) == len(on_disk)


def test_every_scene_is_one_backdrop_four_plus_four_of_three():
    colours, usable, _ = scene_palette_set.load_master(ROOT)
    for entry in data()["scenes"]:
        assert usable[entry["backdrop"]], entry["id"]
        assert 0 <= entry["backdrop"] < len(colours)
        for key in ("background", "sprites"):
            rows = entry[key]
            assert len(rows) == 4, "%s has %d %s palettes" % (entry["id"], len(rows), key)
            for row in rows:
                assert len(row["colours"]) == 3, (entry["id"], key, row)
                assert len(set(row["colours"])) == 3, (entry["id"], key, row)
                for value in row["colours"]:
                    assert usable[value], "%s uses forbidden entry $%02X" % (entry["id"], value)


def test_the_four_hero_palettes_are_fixed_and_dark_to_light():
    payload = data()
    assert sorted(payload["hero_palettes"]) == sorted(scene_palette_set.HEROES)
    for name, palette in payload["hero_palettes"].items():
        entries = palette["colours"]
        assert palette["fixed"] is True, name
        assert len(entries) == 3 and len(set(entries)) == 3, name
        rows = [scene_palette_set.row_of(value) for value in entries]
        assert rows == sorted(rows), "%s is not outline, body, accent: %s" % (name, rows)
    # RULE 0 point 3 names the colours in words; the entries are what the tools read.
    assert payload["hero_palettes"]["percy"]["colours"] == [15, 18, 40]
    assert payload["hero_palettes"]["hadrian"]["colours"] == [15, 3, 35]
    assert payload["hero_palettes"]["zander"]["colours"] == [15, 33, 49]
    assert payload["hero_palettes"]["konrad"]["colours"] == [15, 0, 39]


def test_a_scene_can_be_loaded_as_the_art_lanes_own_scene_object():
    scene = scene_palette_set.scene(ROOT, "title")
    assert scene.name == "title"
    assert len(scene.background) == 4 and len(scene.sprites) == 4
    assert len(scene.bg_sets()[0]) == 4  # three entries plus the shared backdrop
    assert scene.rgb(scene.backdrop) == (0, 0, 0)


def test_every_entry_of_the_set_is_a_usable_master_entry():
    payload = data()
    entries = scene_palette_set.scene_entries(payload, "title")
    _, usable, _ = scene_palette_set.load_master(ROOT)
    assert entries, "title has no entries"
    for entry in entries:
        assert usable[entry], "$%02X is not usable" % entry


def test_validate_passes_on_the_shipped_file():
    assert scene_palette_set.validate(ROOT) == []


def test_validate_catches_a_broken_scene():
    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["background"] = payload["scenes"][0]["background"][:3]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("background palettes" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["hero_palettes"]["percy"]["colours"] = [15, 18]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("percy" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["backdrop"] = 13  # $0D, the entry the art bible forbids
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("forbidden" in problem for problem in problems), problems


def test_build_reproduces_the_file_on_disk():
    """The file must be derived, not hand written: a regeneration either changes nothing or the art changed."""
    rebuilt = json.loads(json.dumps(scene_palette_set.build(ROOT)))
    shipped = data()
    assert rebuilt["scenes"] == shipped["scenes"]
    assert rebuilt["hero_palettes"] == shipped["hero_palettes"]
    assert rebuilt["rule"] == shipped["rule"]
    # The audit rows are derived too. They were a constant in tools/scene_palette_set.py until card t_4f18c0ac,
    # and that is how the deck's row kept naming the walking sailor after the deck's palettes were re-solved for
    # the fight cast: two files, no comparison. Now the rows live in data/palettes/scene_*.json, so a hand edit to
    # data/scene_palettes.json is a drift the rebuild test catches.
    assert rebuilt["audit"] == shipped["audit"]


# -----------------------------------------------------------------------------------------------------------------
# The cast check (card t_4f18c0ac). An audit row may only name sheets the scene's four sprite palettes can carry.

def judged_rows():
    return scene_palette_set.judged_rows(ROOT)


def test_every_judged_row_lives_in_a_scene_file_and_names_a_frame_and_a_cast():
    rows = judged_rows()
    assert rows, "no scene file carries a judged row"
    scene_ids = set(scene_palette_set.scene_ids(data()))
    for row in rows:
        assert row["scene"] in scene_ids, row["scene"]
        assert row["background"], row
        assert row["sprites"], row


def test_the_battle_rows_name_the_party_four_and_no_walking_sheet():
    """Card t_0949bd4e: the cast of a battle row is the party's four battle sheets, and nothing else.

    The deck row named the fight cast (sailor_battle + navy_sailor) from 2026-10-24 until this card, and the
    corridor row named a 16x16 walking sheet. Both are the same defect: every battle screen puts four 24x32
    party slots at x=224 (data/ui_layouts.json) and the PPU gives the strip four sprite palettes, so a strip that
    draws all four heroes has no slot left for an enemy (ruling 7.5: the enemy is background art there) and no
    slot for the map's walking cast. Measured under the hero four: the old deck cast fails 126, the old corridor
    cast fails 24 (all of them zander_ow_v2), the party's four sheets fail 0 on both.

    Card t_39b06dd5: both rows carried an exemption while tools/palette_synergy.py read a party_cast scene
    against the scene's own four rows (card t_6e8ca42f). That tool change landed, the rows measure 0 fails
    through the hero four, and their exemptions ended, so the assertion below is inverted on purpose: an
    exemption back on a party row is how a red row goes quiet.
    """
    party = ["percy_battle.png", "hadrian_battle.png", "zander_battle.png", "konrad_battle.png"]
    for scene_id in ("battle_corridor", "battle_deck_night"):
        rows = [row for row in judged_rows() if row["scene"] == scene_id and not row.get("by_product")]
        assert len(rows) == 1, (scene_id, rows)
        sprites = [os.path.basename(path) for path in rows[0]["sprites"]]
        assert sprites == party, (scene_id, sprites)
        assert not rows[0].get("exempt"), \
            "%s draws the party four and is enforced, so its cast is measured and not exempted" % scene_id
    # The ship's row is its WALKING cast (card t_a6a7a436): the party's four walking sheets plus the sailor
    # actor, and no battle sheet. A walking room draws walking sheets, the ship's four rows are the party's four
    # triples, and sailor_battle.png is a 168x32 battle figure that no encounter and no draw call names; its own
    # ground is card t_0b9c2faf.
    ship = [os.path.basename(path) for row in judged_rows()
            if row["scene"] == "ship" and "ts_ship.png" in row["background"] for path in row["sprites"]]
    assert ship == ["hadrian_ow_v2.png", "percy_ow_v2.png", "zander_ow_v2.png", "konrad_ow_v2.png",
                    "sailor_ow_v2.png"], ship
    assert "sailor_battle.png" not in ship, ship


def test_the_cast_check_catches_the_walking_sheet_put_back_on_a_battle_row():
    """The mutation this check exists for, kept alive after this card cleared both rows' exemptions.

    A 16x16 walking sheet on a battle row is the defect the corridor row carried until card t_0949bd4e. The row
    is enforced since card t_39b06dd5, so the mutation only has to put the sheet back; the pop stays so the
    fixture does not depend on that, and the check has to name the sheet.
    """
    broken = json.loads(json.dumps(data()))
    mutated = 0
    for row in broken["audit"]:
        if row["scene"] == "battle_corridor" and row["sprites"] and "percy_battle.png" in row["sprites"][0]:
            row["sprites"] = ["game/sprites_src/chars/zander_ow_v2.png"]
            row.pop("exempt", None)
            mutated += 1
    assert mutated == 1, broken["audit"]
    problems = scene_palette_set.cast_problems(ROOT, broken)
    assert len(problems) == 1, problems
    assert "battle_corridor" in problems[0]
    assert "zander_ow_v2.png" in problems[0]
    # And it is part of validate, so the suite fails on it rather than only this function.
    assert any("zander_ow_v2.png" in problem for problem in scene_palette_set.validate(ROOT, broken))


def test_every_enforced_judged_row_has_a_cast_its_scene_can_carry():
    """The enforced rows measure clean through the tool's own cast reading; the exempt ones are named below."""
    assert scene_palette_set.cast_problems(ROOT, data()) == []


def test_the_exempt_row_is_the_known_one_and_says_why():
    """An exemption is a ruling, not a way to quiet the check, so the exact list is held here.

    One row is exempt: the corridor contact sheet, which is a diagnostic and a by-product, and it says why.
    The corridor and deck party rows were the other two until card t_39b06dd5: they measured red only because
    tools/palette_synergy.py read a party_cast scene against the scene's own four rows instead of the hero four
    (card t_6e8ca42f). That tool change landed, both rows read 0 failing pairs through the hero four, and their
    exemptions ended, exactly as their own text said they would.
    """
    exempt = [row for row in judged_rows() if row.get("exempt")]
    assert [(row["scene"], os.path.basename(row["sprites"][0])) for row in exempt] == [
        ("battle_corridor", "sprites_v2_sheet.png"),
    ], exempt
    for row in exempt:
        assert len(row["exempt"]) > 80, "an exemption has to say why, in words: %s" % row["exempt"]


def test_a_judged_row_may_not_be_exempt_without_a_reason():
    broken = json.loads(json.dumps(data()))
    for row in broken["audit"]:
        if row.get("exempt"):
            row["exempt"] = " "
            break
    problems = scene_palette_set.validate(ROOT, broken)
    assert any("exempt with no reason" in problem for problem in problems), problems


def test_the_quay_strip_has_no_judged_row_because_nothing_in_play_draws_it():
    """Ruling on card t_4f18c0ac: no encounter names battle_quay_dusk and no room set maps to it."""
    assert not [row for row in judged_rows() if row["scene"] == "battle_quay_dusk"]
    assert "battle_quay_dusk" in scene_palette_set.scene_ids(data()), "the set still exists; only its row is absent"


def test_a_battle_strip_spends_four_sprite_triples_not_eight():
    """Card t_c93a983f and ruling 7.1: on a battle strip the four hero palettes ARE the strip's four.

    allowed() used to union the scene's four sprite rows with the four hero palettes, so a checker built on it
    could approve a drawing no frame can hold (the PPU has four sprite palettes and no fifth). The replacement
    is encoded per scene: only the four battle strips declare party_cast, and on those the hero four stand in
    for the scene's own rows instead of being added to them.
    """
    payload = data()
    heroes = [payload["hero_palettes"][name]["colours"] for name in scene_palette_set.HEROES]
    assert heroes == [[15, 18, 40], [15, 3, 35], [15, 33, 49], [15, 0, 39]], heroes
    for scene_id in ("battle_corridor", "battle_deck_night", "battle_quay_dusk", "battle_wardroom"):
        rows = scene_palette_set.allowed_sprite_sets(payload, scene_id)
        assert rows == heroes, (scene_id, rows)
        assert len(rows) == 4, (scene_id, len(rows), "a frame has four sprite palettes, so four triples")

    # The four towns, the ship, the title, the icons, the sea and the ui scene keep their own four rows, and
    # their entry set is unchanged: every background entry plus every sprite entry plus the hero entries.
    for scene_id in ("title", "ship", "icons", "sea", "ui", "southampton", "westminster", "winchester"):
        entry = scene_palette_set.find_scene(payload, scene_id)
        assert scene_palette_set.allowed_sprite_sets(payload, scene_id) == [
            row["colours"] for row in entry["sprites"]], scene_id
        expected = {entry["backdrop"]}
        for row in entry["background"] + entry["sprites"]:
            expected.update(row["colours"])
        expected.update(scene_palette_set.hero_entries(payload))
        assert scene_palette_set.scene_entries(payload, scene_id) == expected, scene_id

    # And on a battle strip the entry set is the backdrop plus the background rows plus the hero four, with the
    # strip's own sprite rows NOT added on top.
    corridor = scene_palette_set.find_scene(payload, "battle_corridor")
    expected = {corridor["backdrop"]}
    for row in corridor["background"]:
        expected.update(row["colours"])
    for row in heroes:
        expected.update(row)
    assert scene_palette_set.scene_entries(payload, "battle_corridor") == expected


def test_only_the_four_battle_strips_declare_the_party_cast():
    declared = sorted(entry["id"] for entry in data()["scenes"] if entry.get(scene_palette_set.PARTY_CAST_KEY))
    assert declared == ["battle_corridor", "battle_deck_night", "battle_quay_dusk", "battle_wardroom"], declared


def test_the_by_product_flag_survives_the_rebuild_and_says_what_it_means():
    """Card t_c93a983f: the contact sheet row is a by-product, and the derived file has to carry the flag.

    output/sprites_v2_sheet.png is gitignored and two generators write different content under the one name, so
    the row cannot be evidence a clean checkout reproduces. audit_rows() carries the flag through, which is what
    lets tools/palette_synergy.py report the row NOT MEASURED when the file is absent (ruling section 8).
    """
    rows = judged_rows()
    by_product = [row for row in rows if row.get(scene_palette_set.BY_PRODUCT_KEY)]
    assert [(row["scene"], os.path.basename(row["sprites"][0])) for row in by_product] == [
        ("battle_corridor", "sprites_v2_sheet.png")], by_product
    shipped = [row for row in data()["audit"] if row.get(scene_palette_set.BY_PRODUCT_KEY)]
    assert shipped == by_product, "build --write must carry the flag into data/scene_palettes.json"


def test_cli_validate_and_list(capsys):
    assert scene_palette_set.main(["validate"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert scene_palette_set.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "title" in out and "ship" in out


def test_cli_show_names_the_palettes(capsys):
    assert scene_palette_set.main(["show", "--scene", "title"]) == 0
    out = capsys.readouterr().out
    assert "$0F" in out and "percy" in out


def test_the_ship_judged_row_names_the_tileset_and_not_the_capture():
    """Card t_1dc346b9 ruling 2026-10-25: a ground has to be something a tool can measure.

    output/ship_dialogue.png is a composed capture carrying colours off the 2C02 palette, and
    palette_synergy charges the capture's own background_area and set_member failures to whatever
    sprite stands on it, so it cannot be evidence about the ship cast. The ship tileset is authored
    inside the scene's own background palettes, so the pair column measures only the sprite.
    """
    ship = [row for row in judged_rows() if row["scene"] == "ship"
            and "ts_ship.png" in row["background"]]
    assert len(ship) == 1, ship
    row = ship[0]
    sprites = [os.path.basename(path) for path in row["sprites"]]
    assert "sailor_ow_v2.png" in sprites, sprites
    # Card t_a6a7a436 ruling section 17: the row is the WALKING cast, so the battle sheet is off it. Keeping it
    # here judged a 24x32 fight figure on a ground a walking room never draws it on, which is card t_0949bd4e's
    # defect (a walking sheet on a battle strip) in the other direction.
    assert "sailor_battle.png" not in sprites, sprites
    assert row["at"] == [64, 64], row
    assert not [r for r in judged_rows()
                if r["scene"] == "ship" and "ship_dialogue" in r["background"]], (
        "no ship judged row may name the capture as its ground (t_1dc346b9)")


def test_the_four_walking_grounds_carry_the_party_four_walking_triples():
    """Card t_a6a7a436 ruling section 17: the ship is a walking ground, so it carries the party's four triples.

    The towns were solved on card t_dec4e92c (section 16). The ship was not: its four rows were solved from
    ts_ship.png's own 8x8 subtiles with the sailor cast in the pool, and of the four walking sheets only Percy
    fitted one of them (measured 2026-10-25 at 64,64 on ts_ship.png: percy 0 failing pairs, konrad 8, zander 32,
    hadrian 8). The sailor costs no row of his own, because his sheet is the same three entries as Percy's.
    """
    import scene_palette

    payload = data()
    party = [(0x00, 0x0F, 0x30), (0x07, 0x17, 0x28), (0x01, 0x11, 0x31), (0x02, 0x12, 0x30)]
    walking = {}
    for scene_id in ("southampton", "westminster", "winchester", "ship"):
        rows = [tuple(int(value) for value in row["colours"])
                for row in scene_palette_set.find_scene(payload, scene_id)["sprites"]]
        walking[scene_id] = sorted(rows)
    for scene_id, rows in walking.items():
        assert rows == sorted(party), (scene_id, rows)

    def sheet_entries(name):
        from PIL import Image
        scene = scene_palette_set.scene(ROOT, "ship")
        path = os.path.join(ROOT, "game", "sprites_src", "chars", name + ".png")
        with Image.open(path) as handle:
            image = handle.convert("RGBA")
        out = set()
        for frame in range(image.width // 16):
            for ty in (0, 8):
                for tx in (0, 8):
                    box = (frame * 16 + tx, ty, frame * 16 + tx + 7, ty + 7)
                    out.update(scene_palette._pixel_counts(image, box, scene.index_of, {}))
        return out

    assert sheet_entries("sailor_ow_v2") == sheet_entries("percy_ow_v2") == {0x02, 0x12, 0x30}, (
        "the walking sailor and Percy share one triple, which is why the sailor needs no row of his own")
    for name, triple in (("hadrian_ow_v2", {0x00, 0x0F, 0x30}), ("konrad_ow_v2", {0x07, 0x17, 0x28}),
                         ("zander_ow_v2", {0x01, 0x11, 0x31}), ("percy_ow_v2", {0x02, 0x12, 0x30})):
        assert sheet_entries(name) == triple, (name, sheet_entries(name))


def test_the_cloud_declares_itself_a_layer_in_its_sidecar_and_in_its_generator():
    """Card t_1dc346b9 ruling: the cloud hangs in the sky band over the strip's own cloud tops, so it is
    judged by R1b overlay_contrast, not by the figure tests. cf3d43a made a 24x16 frame a figure, and the
    white crown then read white_blob on the 5 white pixels of its own sky crop: scenery meeting scenery.
    The declaration lives in the sidecar AND in save_strip, so a regeneration cannot lose it.
    """
    sidecar = json.load(open(os.path.join(ROOT, "game", "sprites_src", "title",
                                          "spr_title_cloud.json"), encoding="utf-8"))
    assert sidecar.get("layer") is True, sidecar
    gen = open(os.path.join(ROOT, "tools", "art", "make_title_car.py"),
               encoding="utf-8").read()
    assert 'meta["layer"] = True' in gen, "the generator stopped owning the declaration"


# -----------------------------------------------------------------------------------------------------------------
# The fixtures the rows read (card t_19b41ab7). Three rows named a baked frame that output/* excluded and no
# commit carried, so a clean checkout of 5f290c5 was red on this file while this machine was green.

def tracked_paths():
    """The paths git tracks in THIS project, relative to the project root, or None when git cannot answer.

    None in two cases, both unanswerable rather than failures. No git at all, or a tree that is not inside a
    repository: a bare `git archive` extraction has no .git, which is the measuring stick this card used. And a
    tree that sits inside SOME repository that is not the one that owns it: an archive unpacked under another
    checkout still answers `git ls-files`, and answers with the wrong set, which turned this row red on a
    correct tree once already. The ownership test is the project's own manifest: the repository that owns
    projects/primordial-paradox tracks its DEVLOG.md. Where a repository passes both (the live tree, a detached
    worktree) the set answers, and a broken git is still an error rather than a skip.
    """
    def git(*arguments):
        return subprocess.run(["git", *arguments], cwd=ROOT, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120)

    try:
        top = git("rev-parse", "--show-toplevel")
    except (OSError, subprocess.SubprocessError):
        return None
    if top.returncode != 0 or not top.stdout.strip():
        return None
    listing = git("ls-files", "--full-name")
    if listing.returncode != 0:
        raise AssertionError("git ls-files failed in %s: %s" % (ROOT, listing.stderr.strip()[:400]))
    tracked = set(listing.stdout.splitlines())
    relative = os.path.relpath(ROOT, top.stdout.strip())
    prefix = "" if os.path.normpath(relative) == "." else relative.replace(os.sep, "/") + "/"
    if prefix + "DEVLOG.md" not in tracked:
        return None
    return {path[len(prefix):] for path in tracked if path.startswith(prefix)}


def test_every_judged_rows_ground_is_a_file_a_clean_checkout_carries():
    """The row that would have caught t_19b41ab7 before Pine did: a ground a row measures has to be in git.

    build() drops nothing any more (tools/scene_palette_set.py audit_rows()), so this is the earlier gate:
    the frames the six judged rows name are committed. Three of them were not on 2026-10-25.
    """
    tracked = tracked_paths()
    if tracked is None:
        pytest.skip("no repository that owns this tree, so what it commits cannot be read (see tracked_paths)")
    missing = sorted({row["background"] for row in judged_rows() if row["background"] not in tracked})
    assert missing == [], ("a judged row measures a frame no commit carries, so a clean checkout fails on it: %s"
                           % missing)


def test_the_committed_cloud_ground_is_the_crop_its_generator_builds():
    """The crop the cloud row reads is derived, not pasted: this compares it with the tool's own pixels.

    output/cloud_sky_ground.png is 48x16 of title_L1_sky frame 0 at the composer's CLOUD_DY. Before card
    t_19b41ab7 nothing wrote it: it was a one-off crop, in no commit, and a clean checkout of 5f290c5 failed
    the cloud row on the missing file. tools/art/title_cloud_ground.py now owns it, and this row refuses a
    hand edited or hand pasted replacement.

    Pixels, not PNG bytes (card t_78db3b2c, measured 2026-10-25). A Pine run built the same 48x16 crop from
    the same source rows and wrote a file that differed from byte 36 on, which is the low byte of the first
    IDAT length: signature and IHDR agreed, only the deflate differed, and each disk's copy was stable
    (this machine 80a7f373397fe133). A hand pasted crop still changes pixels, which is what this row is
    for, so it reads the crop and not the encoder.
    """
    import title_cloud_ground  # tools/art is on sys.path above

    path = os.path.join(ROOT, "output", "cloud_sky_ground.png")
    assert os.path.isfile(path), "output/cloud_sky_ground.png is missing; build it with tools/art/title_cloud_ground.py"
    built = title_cloud_ground.build(ROOT)
    with Image.open(io.BytesIO(built)) as fresh, Image.open(path) as on_disk:
        assert fresh.size == on_disk.size, (
            "output/cloud_sky_ground.png is %s and tools/art/title_cloud_ground.py builds %s"
            % (on_disk.size, fresh.size))
        assert fresh.convert("RGBA").tobytes() == on_disk.convert("RGBA").tobytes(), (
            "output/cloud_sky_ground.png is not what tools/art/title_cloud_ground.py builds, so it is either "
            "stale or hand edited: rerun the tool")


# -----------------------------------------------------------------------------------------------------------------
# The party walking sheets (card t_dec4e92c). The towns are a ground the party walks on, so their four sprite
# palettes are the party's four walking triples, and each town's judged row measures the four sheets on the frame
# tools/art/make_exterior_maps.py composes at that map's spawn.

WALKING_SHEETS = ("percy_ow_v2.png", "konrad_ow_v2.png", "zander_ow_v2.png", "hadrian_ow_v2.png")
# The four rows in the order the towns declare them, then the sheet each row carries.
WALKING_ROWS = ((0, 15, 48), (7, 23, 40), (1, 17, 49), (2, 18, 48))
SHEET_TRIPLES = {"hadrian_ow_v2.png": (0, 15, 48), "konrad_ow_v2.png": (7, 23, 40),
                 "zander_ow_v2.png": (1, 17, 49), "percy_ow_v2.png": (2, 18, 48)}
TOWNS = ("southampton", "westminster", "winchester")


def sheet_entries(name):
    """The 2C02 entry set of one sheet's inked pixels, read through the tool's own Grid."""
    from PIL import Image
    import palette_synergy

    grid = palette_synergy.Grid(ROOT)
    image = Image.open(os.path.join(ROOT, "game", "sprites_src", "chars", name)).convert("RGBA")
    pixels = image.load()
    out = set()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a:
                entry = grid.entry((r, g, b))
                assert entry is not None, "%s has #%02x%02x%02x, off the 2C02 palette" % (name, r, g, b)
                out.add(entry)
    return out


def test_the_towns_four_sprite_rows_are_the_party_that_walks_there():
    """Card t_dec4e92c: sp0 and sp2 were copies of the background groups carrying no art at all.

    Measured when this card started: only konrad_ow_v2 ($07 $17 $28) and percy_ow_v2 ($02 $12 $30) fitted a town
    row; zander_ow_v2 ($01 $11 $31) and hadrian_ow_v2 ($00 $0F $30) fitted NO set in the project, and no sheet in
    game/sprites_src fitted sp0 or sp2. So the two free rows were solved for the two homeless sheets rather than
    leaving two of the four heroes with nowhere to be drawn on the map they walk.
    """
    payload = data()
    for scene_id in TOWNS:
        entry = scene_palette_set.find_scene(payload, scene_id)
        rows = [list(row["colours"]) for row in entry["sprites"]]
        assert rows == [list(triple) for triple in WALKING_ROWS], (scene_id, rows)
    # And the sheets themselves say the same thing: each one's own colours fit exactly one of those four rows.
    for name, triple in SHEET_TRIPLES.items():
        entries = sheet_entries(name)
        assert entries == set(triple), (name, sorted(entries), triple)
        for scene_id in TOWNS:
            rows = scene_palette_set.allowed_sprite_sets(data(), scene_id)
            fits = [index for index, row in enumerate(rows) if entries <= set(row)]
            assert len(fits) == 1, (scene_id, name, fits, rows)


def test_each_town_judged_row_names_the_four_walking_sheets_on_its_own_frame():
    """The row format, held: one row per town, the frame that town's map spawns in, at the spawn tile.

    The ground is the composed frame and NOT game/sprites_src/env/ts_exterior.png, because that atlas spends
    five background palettes and a scene spends four: measured 2026-10-25, it reports 7 palette_count problems
    on southampton and 4 on each of the other two, so as a ground it can never be clean and would charge its own
    background failures to the sprites standing on it (the defect card t_1dc346b9 ruled on).

    Card t_b01c88ff added a SECOND row to westminster and only to westminster: the park, which is the ground the
    party walks in and the one check 13 carried as an exemption until the grass was darkened. A row on the park
    is where the light grass showed up as 56 failing pairs before the fix, so it is the number that says the fix
    is real. The other two towns carry no park cell inside their 15 tile tall frames, which is why they hold no
    such row rather than a row that measures pavement.
    """
    rows = [row for row in judged_rows() if row["scene"] in TOWNS]
    spawn = [row for row in rows if row["at"] == [128, 112]]
    park = [row for row in rows if row["at"] != [128, 112]]
    assert len(spawn) == 3, spawn
    for row in spawn:
        assert row["background"] == "output/%s_sample_frame.png" % row["scene"], row["background"]
        assert row["at"] == [128, 112], row["at"]
        assert [os.path.basename(path) for path in row["sprites"]] == list(WALKING_SHEETS), row["sprites"]
        assert not row.get("exempt"), "the three towns carry the cast, so the rows are enforced, not exempt"
        assert not row.get("by_product"), row
        assert "ts_exterior" in row["note"], "the row has to say why the atlas is not the ground"
    assert len(park) == 1, park
    row = park[0]
    assert row["scene"] == "westminster", row["scene"]
    assert row["background"] == "output/westminster_sample_frame.png", row["background"]
    # Map cell 14,24 is grass_a, reached from the spawn, and the frame crop starts at tile 8,13 (x0 8, y0 13).
    assert row["at"] == [96, 176], row["at"]
    assert [os.path.basename(path) for path in row["sprites"]] == list(WALKING_SHEETS), row["sprites"]
    assert not row.get("exempt") and not row.get("by_product"), row
    assert "t_b01c88ff" in row["note"] and "section 22" in row["note"], (
        "the park row has to name the card and the ruling section that closed the exemption")
    assert "0 failing pair(s)" in row["note"], row["note"]


def test_the_towns_ground_is_the_frame_their_generator_writes():
    """The three grounds are build products, not captures: the generator writes them, and the row names them.

    A composed capture carries colours off the 2C02 table and the tool then charges those to the sprite standing
    on it (card t_1dc346b9). These frames are built tile by tile from ts_exterior.png under the four group budget
    tools/art/make_exterior_maps.py enforces on itself, so every pixel is a scene palette entry, and the
    background half measures 0 against the town's own four rows.
    """
    import palette_synergy

    grid = palette_synergy.Grid(ROOT)
    for scene_id in TOWNS:
        path = os.path.join(ROOT, "output", "%s_sample_frame.png" % scene_id)
        assert os.path.isfile(path), path
        scene = scene_palette_set.scene(ROOT, scene_id)
        frame = palette_synergy.load_background(ROOT, "output/%s_sample_frame.png" % scene_id)
        assert frame.size == (256, 240), (scene_id, frame.size)
        assert palette_synergy.background_report(grid, scene, frame) == [], \
            "%s: the ground is not drawn inside the scene's own four background palettes" % scene_id

