"""Tests for tools/check_build_inputs.py.

The checker exists because HEAD repeatedly shipped a committed .yyp that named Included Files the
commit did not carry, which the audit nightly reported as dozens of unrelated FileNotFoundError.
These tests pin both halves: it must pass on a healthy tree, and it must fail and NAME the file on a
broken one. A checker that only ever prints PASS is worthless, so the negative controls matter more
than the positive one here.
"""

import importlib.util
import os
import subprocess

import pytest

# Card TEST-CLASSIFY-33: every test here drives tools/check_build_inputs.py, which asks git what the
# commit carries. tools/pine_offload.py already refuses to offload this file for that reason; the
# marker covers the runs that pass `tests/` wholesale to pytest instead of the shard list.
pytestmark = pytest.mark.needs_git_checkout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


@pytest.fixture(autouse=True)
def clean_git_environment(monkeypatch):
    """A pre-commit hook hands its children an index, a work tree and a git dir. Drop them here.

    Measured 2026-10-24 (card t_668201ec) on the first gate run of this file: the hook sets
    GIT_INDEX_FILE to the temporary index it is building, so `git -C <scratch repo> add` in the rows
    below wrote into the SHARED repository's index and the scratch rows read the shared index back.
    The reverse row then reported the wrong tree and failed. A scratch repository's git must be
    asked in a clean environment, and a test may never stage anything in the one index every lane on
    this tree shares.
    """
    for name in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        monkeypatch.delenv(name, raising=False)


def load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check():
    return load("check_build_inputs")


def test_the_committed_project_resolves_every_included_file():
    """The real tree is healthy: every declared Included File maps to a committed source."""
    module = check()
    assert module.main() == 0


def test_the_yyp_declares_included_files_at_all():
    """Guard against a silently empty parse, which would make the checker trivially pass."""
    module = check()
    with open(module.YPP, "r", encoding="utf-8") as fh:
        included = module.included_files(fh.read())
    assert len(included) > 100, "expected the real project to declare many Included Files"
    assert "datafiles/streams/title_theme_v3.ogg" in included
    assert "datafiles/nes_palette.json" in included


def test_an_included_file_with_no_committed_source_is_named():
    """Negative control: the exact dc104a7 shape, a stream the commit does not carry."""
    module = check()
    repo = module.repo_root()
    tracked = module.tracked_files(repo)
    bogus = "datafiles/streams/theme_that_was_never_committed.ogg"
    missing = module.unresolved([bogus], tracked, repo)
    assert missing == [bogus], missing


def test_a_committed_source_satisfies_its_included_file():
    """The title theme's source is committed, so the mirror target resolves and is not reported."""
    module = check()
    repo = module.repo_root()
    tracked = module.tracked_files(repo)
    assert module.unresolved(["datafiles/streams/title_theme_v3.ogg"], tracked, repo) == []


def test_a_data_json_resolves_through_the_sync_data_mirror():
    """data/** is mirrored to datafiles/** by sync_data, so the source keeps the same tail."""
    module = check()
    repo = module.repo_root()
    tracked = module.tracked_files(repo)
    assert module.unresolved(["datafiles/nes_palette.json"], tracked, repo) == []


def test_generated_indexes_are_not_treated_as_missing_sources():
    """The art manifest and sfx index are written by sync_art, so they have no source file."""
    module = check()
    repo = module.repo_root()
    tracked = module.tracked_files(repo)
    for name in sorted(module.GENERATED):
        assert module.unresolved([name], tracked, repo) == [], name


def test_an_uncommitted_mirror_source_is_named():
    """Direction B: a source sync_art would mirror but git does not carry."""
    module = check()
    repo = module.repo_root()
    sync = module.load_sync_art()
    unc = module.uncommitted_sources(sync, set(), repo)
    assert unc, "with an empty tracked set every mirrored source must be reported"
    assert all(not os.path.isabs(name) for name in unc), "paths must be repo relative"


# ---- Direction C: the staged pairing, judged against the index (card t_668201ec) -----------------
# Every row below builds its OWN throwaway repository under tmp_path and stages files only there. No
# row may `git add` in the shared repository: it carries one index for every lane on this tree, and a
# test that stages anything in it would either commit another lane's work or lose it.
YPP_REL = "game/PrimordialParadox.yyp"


def scratch_repo(tmp_path):
    """A git repository with an index and NO commit, which is the shape a pre-commit hook sees."""
    repo = tmp_path / "repo"
    (repo / "game").mkdir(parents=True)
    (repo / "assets" / "audio" / "cue_probe").mkdir(parents=True)
    result = subprocess.run(["git", "init", "-q"], cwd=str(repo),
                            capture_output=True, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    return repo


def write_yyp(repo, names):
    items = ", ".join('{"filePath": "datafiles/streams/", "name": "%s"}' % n for n in names)
    (repo / "game" / "PrimordialParadox.yyp").write_text(
        '{"IncludedFiles": [%s]}' % items, encoding="utf-8")


def write_cue(repo, name):
    path = repo / "assets" / "audio" / "cue_probe" / name
    path.write_bytes(b"OggS a probe, not a real stream")
    return path


def git_add(repo, *paths):
    result = subprocess.run(["git", "add", *paths], cwd=str(repo),
                            capture_output=True, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr


def staged_problems(repo, yyp_rel=YPP_REL):
    return check().staged_problems(repo=str(repo), yyp_rel=yyp_rel)


def test_a_staged_cue_with_no_staged_project_file_is_named(tmp_path):
    """The hole: an ogg in the INDEX whose stream the index project does not name.

    Measured against the live tree on 2026-10-24: this shape exits 0 today, because git ls-files
    counts a staged file as carried while the worktree .yyp is already regenerated.
    """
    repo = scratch_repo(tmp_path)
    write_cue(repo, "cue_a.ogg")
    git_add(repo, "assets/audio/cue_probe/cue_a.ogg")
    problems = staged_problems(repo)
    assert problems, "a staged cue with no staged project file must be refused"
    assert all(problem.startswith(check().UNPAIRED) for problem in problems), problems
    assert "assets/audio/cue_probe/cue_a.ogg" in problems[0], problems


def test_a_staged_project_file_that_omits_a_staged_cue_is_named(tmp_path):
    """The same hole with the .yyp staged: it is in the commit, and it does not name the cue."""
    repo = scratch_repo(tmp_path)
    write_cue(repo, "cue_a.ogg")
    write_yyp(repo, [])
    git_add(repo, "assets/audio/cue_probe/cue_a.ogg", YPP_REL)
    problems = staged_problems(repo)
    assert problems, "a staged project file that omits a staged cue must be refused"
    assert "datafiles/streams/cue_a.ogg" in problems[0], problems


def test_a_staged_cue_and_the_staged_project_file_that_names_it_pass(tmp_path):
    """The paired shape, which is the only shape a cue may land in."""
    repo = scratch_repo(tmp_path)
    write_cue(repo, "cue_a.ogg")
    write_yyp(repo, ["cue_a.ogg"])
    git_add(repo, "assets/audio/cue_probe/cue_a.ogg", YPP_REL)
    assert staged_problems(repo) == []


def test_a_staged_project_file_naming_an_unstaged_stream_is_named(tmp_path):
    """The reverse direction: the commit would declare a stream it does not carry."""
    repo = scratch_repo(tmp_path)
    write_yyp(repo, ["cue_gone.ogg"])
    git_add(repo, YPP_REL)
    problems = staged_problems(repo)
    assert problems, "a staged project file naming an absent stream must be refused"
    assert "datafiles/streams/cue_gone.ogg" in problems[0], problems


def test_the_flag_absent_leaves_the_worktree_directions_alone(tmp_path):
    """Without --staged the checker is unchanged: it does not read another repository's index.

    The scratch repo below is red under the flag, and the flagless run still reports the real tree
    as healthy. That is what keeps the nightly and the rows above this section meaning what they
    said before the flag existed.
    """
    module = check()
    repo = scratch_repo(tmp_path)
    write_cue(repo, "cue_a.ogg")
    git_add(repo, "assets/audio/cue_probe/cue_a.ogg")
    assert staged_problems(repo), "the scratch index must be red for this row to mean anything"
    assert module.main() == 0, "the flagless check still measures the real tree"
    assert module.main(staged=False) == 0


def test_the_staged_direction_passes_on_this_repositorys_index():
    """`python tools/check_build_inputs.py --staged` exits 0 on the clean index (its own measure)."""
    assert check().main(staged=True) == 0
