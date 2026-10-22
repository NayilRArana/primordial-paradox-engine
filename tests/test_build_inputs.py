"""Tests for tools/check_build_inputs.py.

The checker exists because HEAD repeatedly shipped a committed .yyp that named Included Files the
commit did not carry, which the audit nightly reported as dozens of unrelated FileNotFoundError.
These tests pin both halves: it must pass on a healthy tree, and it must fail and NAME the file on a
broken one. A checker that only ever prints PASS is worthless, so the negative controls matter more
than the positive one here.
"""

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


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
