"""Tests for the title art and stream mirrors: tools/sync_art.py.

These are the checks that a fresh checkout of a commit can regenerate the committed project
file from. The committed game/PrimordialParadox.yyp lists 35 Included Files, and 21 of them
are the title art sprites plus the title theme stream, so both mirrors have to exist and be
current for the .yyp to be reproducible. Measured 2026-10-21: with the art mirror missing the
suite failed with "lists Included File art/spr_pp_font8.png which is not in game/datafiles",
and with the stream mirror missing it failed with "lists Included File
streams/title_theme.ogg which is not in game/datafiles".
"""

from __future__ import annotations

import json
import os
import sys

import sync_art

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(ROOT, "game", "datafiles")


def _run_main(argv: list[str]) -> int:
    """Call sync_art.main() with the given argv, the way the script does."""
    saved = sys.argv
    sys.argv = argv
    try:
        return sync_art.main()
    finally:
        sys.argv = saved


def _listed_included_files(directory: str) -> list[str]:
    """The Included File paths the committed .yyp lists under the given directory.

    The .yyp stores the directory in filePath and the file name in name, so an entry is
    read as filePath + "/" + name, for example datafiles/art/spr_title_car.png.
    """
    with open(os.path.join(ROOT, "game", "PrimordialParadox.yyp"), encoding="utf-8") as handle:
        project = json.load(handle)
    return [
        entry["filePath"] + "/" + entry["name"]
        for entry in project["IncludedFiles"]
        if entry.get("resourceType") == "GMIncludedFile"
        and entry.get("filePath", "") == directory
    ]


def test_art_mirror_is_current():
    """The art mirror matches its source, so the .yyp can be regenerated from the sources."""
    assert _run_main(["sync_art.py", "--check"]) == 0


def test_main_mirrors_the_title_theme_stream():
    """main() mirrors the stream, not only the script's __main__ block.

    The suite fixture and any other caller of main() need the stream mirror too. The
    __main__ block used to call mirror_streams() and main() alone did not, so a caller of
    main() silently got an incomplete mirror and the committed .yyp could not be regenerated.
    """
    assert _run_main(["sync_art.py"]) == 0
    stream = os.path.join(MIRROR, "streams", "title_theme.ogg")
    assert os.path.isfile(stream), "main() did not mirror the title theme stream"
    source = os.path.join(ROOT, "assets", "audio", "title_theme", "title_theme.ogg")
    assert os.path.getsize(stream) == os.path.getsize(source)


def test_art_mirror_holds_the_sprites_the_project_lists():
    """Every art sprite the committed .yyp lists is present in the mirror."""
    listed = _listed_included_files("datafiles/art")
    assert listed, "the committed .yyp lists no art sprites"
    for file_path in listed:
        # The .yyp paths are relative to the game folder, so the mirror is game\<path>.
        mirrored = os.path.join(ROOT, "game", file_path)
        assert os.path.isfile(mirrored), f"{file_path} is not in the mirror"


def test_the_retired_sailor_battle_sheet_is_in_neither_the_mirror_nor_the_project():
    """Card t_4848159e: a sheet declared retired must not ship, and one index entry plus one Included File is shipping.

    Card t_0b9c2faf retired sailor_battle.png from the palette budgets and stopped tools/art/make_characters.py from
    rebuilding it, but the drawing stayed in game/sprites_src/chars/ and this mirror reads that folder whole, so the
    sheet was still an entry in game/datafiles/art/title_manifest.json and a GMIncludedFile in the project: 5376 px of
    art in every build that nothing draws. The pair is deleted now, and this is the row that keeps it deleted: no
    source, no mirrored PNG, no index entry and no Included File, while the four battle sheets the party does draw
    stay in all four places.
    """
    retired = "sailor_battle"
    source = os.path.join(ROOT, "game", "sprites_src", "chars", retired)
    assert not os.path.exists(source + ".png"), "the retired drawing is back in the authored tree"
    assert not os.path.exists(source + ".json"), "the retired sidecar is back in the authored tree"
    assert not os.path.exists(os.path.join(MIRROR, "art", retired + ".png")), "the retired drawing is mirrored"

    with open(os.path.join(MIRROR, "art", "title_manifest.json"), encoding="utf-8") as handle:
        names = [entry["name"] for entry in json.load(handle)["animations"]]
    assert retired not in names, "the art index still carries the retired sheet"
    assert "datafiles/art/%s.png" % retired not in _listed_included_files("datafiles/art"), \
        "the project still lists the retired sheet as an Included File"

    # The party's own battle sheets are the ones the slots draw, and they stay in the index and in the project.
    listed = _listed_included_files("datafiles/art")
    for hero in ("hadrian_battle", "percy_battle", "zander_battle", "konrad_battle"):
        assert hero in names, "%s left the art index" % hero
        assert "datafiles/art/%s.png" % hero in listed, "%s left the project" % hero


def test_the_project_lists_the_title_theme_stream():
    """The committed .yyp lists the title theme stream, so the mirror must carry it.

    The list is not fixed to one entry any more: the music lane added title_theme_v2.ogg, and the
    .yyp lists every stream in the mirror. So the test pins what actually matters, which is that the
    original theme is among them and that each listed stream exists.
    """
    listed = _listed_included_files("datafiles/streams")
    assert "datafiles/streams/title_theme.ogg" in listed, f"unexpected stream entries: {listed}"
    for file_path in listed:
        assert os.path.isfile(os.path.join(ROOT, "game", file_path)), f"{file_path} is not in the mirror"


def test_a_landed_cue_regenerates_the_project_without_a_second_command():
    """Landing a cue through this script brings the .yyp back in line in the same run.

    This is the whole point of card t_e40f9705. A cue landed five times and each time the two
    GMIncludedFile entries were added by hand in a follow-up commit, because mirror_streams() wrote
    into game/datafiles/streams and nothing ran the generator. The cue here is a stand-in: the
    mirror copies any .ogg and does not read it, so two bytes named .ogg are a real landing as far
    as this path is concerned. The yyp is restored byte for byte afterwards, and the test fails
    loudly if the restore does not match, so it cannot leave the tree dirty.
    """
    import hashlib

    import gen_project

    project_path = os.path.join(ROOT, "game", "PrimordialParadox.yyp")
    before = hashlib.sha256(open(project_path, "rb").read()).hexdigest()

    cue = "t_e40f9705_landed_probe"
    source_dir = os.path.join(ROOT, "assets", "audio", cue)
    source = os.path.join(source_dir, cue + ".ogg")
    mirrored = os.path.join(MIRROR, "streams", cue + ".ogg")
    os.makedirs(source_dir, exist_ok=True)
    with open(source, "wb") as handle:
        handle.write(b"OggS")

    try:
        assert _run_main(["sync_art.py"]) == 0
        assert os.path.isfile(mirrored), "sync_art did not mirror the landed cue"
        assert "datafiles/streams/%s.ogg" % cue in _listed_included_files("datafiles/streams"), (
            "the .yyp still does not list the cue that just landed, so the landing path did not "
            "run the generator"
        )
        assert gen_project.regenerate(check=True)[0], "the project is still stale after the landing"
    finally:
        os.remove(source)
        os.rmdir(source_dir)
        if os.path.isfile(mirrored):
            os.remove(mirrored)
        assert _run_main(["sync_art.py"]) == 0

    after = hashlib.sha256(open(project_path, "rb").read()).hexdigest()
    assert after == before, "the probe left game/PrimordialParadox.yyp changed"
    assert "datafiles/streams/%s.ogg" % cue not in _listed_included_files("datafiles/streams")


def test_the_no_project_flag_leaves_the_yyp_alone():
    """--no-project is what the suite fixture uses, so it must not touch the project file.

    Without it the fixture would repair a stale committed .yyp before test_project.py could
    measure it, and the two rows that catch this class of staleness would stop meaning anything.
    """
    import hashlib

    project_path = os.path.join(ROOT, "game", "PrimordialParadox.yyp")
    before = hashlib.sha256(open(project_path, "rb").read()).hexdigest()
    assert _run_main(["sync_art.py", "--no-project"]) == 0
    after = hashlib.sha256(open(project_path, "rb").read()).hexdigest()
    assert after == before, "--no-project rewrote the project file"
