"""Shared fixtures: the tools directory on the import path, and a throwaway copy of data\\ to break on purpose."""

from __future__ import annotations

import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


@pytest.fixture(scope="session", autouse=True)
def generated_mirror():
    """Build the generated mirrors before the suite measures anything.

    game\\datafiles\\ holds two generated mirrors, and both are gitignored on purpose, because
    their sources are the tracked ones: tools\\sync_data.py copies data\\ into
    game\\datafiles\\, and tools\\sync_art.py copies game\\sprites_src\\title\\ into
    game\\datafiles\\art\\. So a fresh checkout of a commit has the sources and no mirror, and
    the checks that measure the generated project have nothing to read.

    Measured 2026-10-21: the pinned nightly worktree failed 3 of 110 tests for exactly this,
    with 'PrimordialParadox.yyp: lists Included File audio.json which is not in game/datafiles'
    and 'assert 1 == 0' from the two --check tools. Running the sync first made the same
    worktree pass 110 of 110.

    Both syncs are needed, not just the data one. The .yyp also lists the art files under
    game/datafiles/art\\, and sync_data deliberately leaves that subtree alone (it is owned by
    sync_art), so with only sync_data run the second failure remained: 'lists Included File
    art/spr_pp_font8.png which is not in game/datafiles'. The order here is the order
    tools\\run.ps1 uses: sync_data.py, then sync_art.py.

    The mirrors are gitignored, so writing them does not dirty the checkout: the worktree was
    still clean after the run.
    """
    import sync_art
    import sync_data

    for module, name, extra in ((sync_data, "sync_data.py", []),
                                (sync_art, "sync_art.py", ["--no-project"])):
        # --no-project is what keeps two rows honest (card t_e40f9705): a write run of sync_art now
        # regenerates game/PrimordialParadox.yyp from the mirror, so letting the fixture do that
        # would repair a stale committed .yyp before test_project.py could measure it. The fixture
        # builds the mirror only; the landing path is the thing that regenerates.
        argv = sys.argv
        sys.argv = [name] + extra
        try:
            assert module.main() == 0, "%s could not build its mirror" % name
        finally:
            sys.argv = argv
    return True


@pytest.fixture()
def data_root(tmp_path):
    """A private root with a copy of data\\ inside, so a test can corrupt one file and nothing else."""
    shutil.copytree(os.path.join(ROOT, "data"), tmp_path / "data")
    return tmp_path


@pytest.fixture()
def read_json():
    def _read(path):
        import json
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    return _read


@pytest.fixture()
def write_json():
    def _write(path, data):
        import json
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")

    return _write
