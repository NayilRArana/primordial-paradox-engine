"""Tests for tools/check_test_inputs.py.

The checker exists because a test that skips when its input file is absent is indistinguishable from a
test that passes, and in a HEAD worktree that is how two tests at once reported healthy while they read
nothing. These tests pin both halves, and the negative controls matter more than the positive one: a
checker that can only print PASS is worthless.
"""

import importlib.util
import os

import pytest

# Card TEST-CLASSIFY-33: every test here drives tools/check_test_inputs.py, which asks git what the
# commit carries, so the offloaded zip cannot answer it. tools/pine_offload.py already excludes this
# file; the marker covers a run that passes `tests/` wholesale.
pytestmark = pytest.mark.needs_git_checkout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checker():
    return load("check_test_inputs")


# ------------------------------------------------------------------ the real tree

def test_no_test_skips_on_a_missing_input_and_every_fixture_is_committed():
    module = checker()
    problems = module.check()
    assert problems == [], problems


def test_the_real_tests_are_actually_scanned():
    """Guard against a silently empty walk, which would make the skip rule trivially pass."""
    module = checker()
    seen = [name for name, _source in module.test_sources()]
    assert len(seen) > 30, len(seen)
    assert "tests/test_humanize.py" in seen


def test_the_fixture_table_names_the_files_this_card_committed():
    module = checker()
    for name in ("assets/audio/title_theme/title_theme.mid",
                 "assets/audio/title_theme/title_theme.wav",
                 "assets/audio/title_theme_v2/title_theme_v2.mid"):
        assert name in module.FIXTURES, name


# ------------------------------------------------------------- the skip rule half

def test_a_skip_guarded_by_a_missing_asset_is_reported():
    """The exact shape this card removed from test_hook_score and test_render_chip_v2."""
    module = checker()
    source = (
        "import os\n"
        "import pytest\n"
        "\n"
        "def test_it():\n"
        "    if not os.path.exists(PATH):\n"
        "        pytest.skip('asset not present')\n"
        "    assert True\n"
    )
    found = module.absent_input_skips(source, "tests/fake.py")
    assert len(found) == 1, found
    assert "tests/fake.py:5" in found[0]


def test_a_skip_on_an_isfile_guard_is_reported_too():
    module = checker()
    source = (
        "import os\n"
        "import pytest\n"
        "\n"
        "def test_it():\n"
        "    if not os.path.isfile(REF):\n"
        "        pytest.skip('the render is not on this machine')\n"
    )
    assert module.absent_input_skips(source, "tests/fake.py")


def test_a_skip_for_a_missing_tool_is_allowed():
    """ffprobe not being on PATH is the machine's capability, not an input this repo carries."""
    module = checker()
    source = (
        "import shutil\n"
        "import pytest\n"
        "\n"
        "def test_it():\n"
        "    if not shutil.which('ffprobe'):\n"
        "        pytest.skip('ffprobe not on PATH')\n"
    )
    assert module.absent_input_skips(source, "tests/fake.py") == []


def test_a_plain_skip_without_a_guard_is_not_reported():
    module = checker()
    source = "import pytest\n\n\ndef test_it():\n    pytest.skip('not applicable here')\n"
    assert module.absent_input_skips(source, "tests/fake.py") == []


# --------------------------------------------------------- the committed set half

def test_a_fixture_the_commit_lacks_is_named():
    module = checker()
    missing = module.untracked_fixtures(set(), "projects/primordial-paradox/")
    assert set(missing) == set(module.FIXTURES), missing
    assert "assets/audio/title_theme/title_theme.wav" in missing


def test_a_fixture_the_commit_carries_is_not_named():
    module = checker()
    tracked = {"projects/primordial-paradox/" + name for name in module.FIXTURES}
    assert module.untracked_fixtures(tracked, "projects/primordial-paradox/") == []
