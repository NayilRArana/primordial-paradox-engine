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
