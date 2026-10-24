"""Shared fixtures: the tools directory on the import path, and a throwaway copy of data\\ to break on purpose."""

from __future__ import annotations

import os
import shutil
import subprocess
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


def _is_git_checkout() -> bool:
    """True when git itself says this tree is inside a work tree.

    The checks that shell out to git (check_build_inputs, the palette table pin) need this one: off the
    box the tree arrives as a zip, and `git` there answers "not a git repository", which is a skip and
    not a verdict on the code. Asking git is the only answer that also covers a worktree, where .git is
    a file, and this repository, whose root is three levels above this module.
    """
    try:
        result = subprocess.run(
            ["git", "-C", ROOT, "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=20,
            # A DEFINED stdin, never inherited (card t_668201ec, measured 2026-10-24). Without this,
            # a parent with no valid standard input handle makes the spawn itself raise
            # OSError [WinError 6], this probe answers "not a checkout", and every
            # needs_git_checkout row SKIPS with a reason that sounds like the tree's fault. Measured
            # on this host with capture on: 2 of 5 identical runs of tests/test_build_inputs.py
            # reported 13 skipped and 3 reported 13 passed, same tree, same command. It is the same
            # defect commit_gate.run() already answers with stdin=subprocess.DEVNULL.
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def pytest_collection_modifyitems(config, items):
    """Card TEST-CLASSIFY-33: the two host-only kinds of test are skipped, with the reason, off the host.

    The suite runs on two hosts: this Windows PC and the Pine Linux computers through
    tools/pine_offload.py. Three things cannot cross the boundary, and each one has a marker in
    pytest.ini so the reason travels with the test instead of living in this file:

      windows_only     the test, or a tool it loads, binds a Win32 API through ctypes.windll at
                       import, so on Linux the import raises AttributeError before a line of the test
                       runs (tools/capture_title.py binds user32 at module level, and play_demo
                       imports it);
      host_png_bytes   the test compares a PNG this host just wrote with the committed copy byte for
                       byte, so only the Pillow and zlib builds that wrote the committed files pass.
                       The pixels agree; the encoder does not;
      needs_git_checkout  the check shells out to git, and the offloaded tree is a zip.
    """
    if sys.platform != "win32":
        reason = "Windows host only: the tool this test loads binds ctypes.windll (card TEST-CLASSIFY-33)"
        for item in items:
            if item.get_closest_marker("windows_only"):
                item.add_marker(pytest.mark.skip(reason=reason))
        reason = (
            "compares a PNG this host wrote byte for byte with the committed one, and the committed "
            "files were written on Windows (card TEST-CLASSIFY-33)"
        )
        for item in items:
            if item.get_closest_marker("host_png_bytes"):
                item.add_marker(pytest.mark.skip(reason=reason))
    if not _is_git_checkout():
        reason = "needs a git checkout, and this tree is a copy (card TEST-CLASSIFY-33)"
        for item in items:
            if item.get_closest_marker("needs_git_checkout"):
                item.add_marker(pytest.mark.skip(reason=reason))


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
