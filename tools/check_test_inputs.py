"""No test in this project may pass because an input file was absent, and every fixture is committed.

Why this exists. The nightly runner measures a detached worktree at HEAD, and a worktree holds only
what git tracks. On 2026-10-22 that path reported 88 failed and 23 errors while the live tree at the
same moment reported 10, because most of what the tests read was untracked. Part of that damage was
not an error at all: two tests opened their input, found nothing, and called pytest.skip, so the
nightly row said "2 skipped" and looked healthy. A skip on a missing input is the failure mode that
keeps this class invisible, and it is the thing this checker exists to forbid.

Two rules, both mechanical:

1. No test may skip because a path does not exist. Concretely, a pytest.skip inside an if whose
   condition tests os.path.exists, os.path.isfile, os.path.isdir, or os.access is a failure of this
   check and is reported with its line number. A skip for a missing TOOL (shutil.which, or a program
   that is not on PATH) is allowed, because that is a capability of the machine rather than an input
   this repository is supposed to carry.

2. Every fixture in FIXTURES is tracked by git. The list is the audio inputs and the title frame the
   tests read by path, which is the set that was untracked when this card was written. It is written
   down rather than discovered, because a checker that guesses which files matter ends up checking the
   files it can see, which in a HEAD worktree is the ones that are already there.

The .yyp side of the same class is tools/check_build_inputs.py's job and is not repeated here.
"""

import ast
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")

# Paths relative to the project root. Each one is opened by a test by name, so a HEAD checkout that
# lacks it either errors in that test or, worse, skips it.
FIXTURES = (
    "assets/audio/title_theme/title_theme.mid",
    "assets/audio/title_theme/title_theme.wav",
    "assets/audio/title_theme_v2/score.yaml",
    "assets/audio/title_theme_v2/title_theme_v2.mid",
    "assets/audio/title_theme_v3/EAR_REVIEW_126.md",
    "assets/audio/title_theme_v3/score_v3.yaml",
    "assets/audio/title_theme_v3/title_theme_v3.mid",
    "assets/audio/title_theme_v3/title_theme_v3_126.mid",
    # The frame tests/test_palette_synergy.py measures with palette_synergy.analyse(). It was the
    # skipped input that made that test look healthy: absent, the test passed without measuring.
    "output/nes_title_frame.png",
    # Card t_dc6305d6: the ship screen with the dialogue box, the ground the sailor battle sheet is measured on.
    # It was the last capture a test read by path that no commit carried, so a HEAD worktree reported the
    # absent file as an art failure.
    "output/ship_dialogue.png",
    # Card t_d2c52f15: the drive cue's measurement pair and the two WAVs behind it. tests/test_mix_check_v3.py
    # reads the report by path and runs the script on a 30 s slice; the script reads both WAVs. A commit that
    # carried the test and the report but not the script left five rows red in a clean checkout, all of them
    # "FileNotFoundError: .../mix_check_v3.py" or the missing report behind it.
    "assets/audio/pp_drive/mix_check_v3.py",
    "assets/audio/pp_drive/mix_check_v3.json",
    "assets/audio/pp_drive/pp_drive_v3_humanized.wav",
    "assets/audio/pp_01_title/pp_01_title.wav",
    # Card t_19b41ab7: the three grounds three judged rows and one palette test measure by path. All three were
    # matched by output/* and in no commit, so a clean checkout of 5f290c5 was red on three rows while this
    # list's own row stayed green, which is the hole this list exists to close. They are derived, not pasted:
    # the crop by tools/art/title_cloud_ground.py, both battle frames by tools/art/make_battle_bg.py.
    "output/cloud_sky_ground.png",
    "output/bg_battle_corridor_frame.png",
    "output/bg_battle_deck_night_frame.png",
    # Card t_dec4e92c: the three exterior map frames, one per town, the ground each town's judged row measures the
    # party's four walking sheets on. Written by tools/art/make_exterior_maps.py, reproduced byte for byte by a
    # rerun, and un-ignored one by one above, for the same reason as the three grounds. A clean checkout without
    # them fails the gate on three rows whose art is fine.
    "output/southampton_sample_frame.png",
    "output/westminster_sample_frame.png",
    "output/winchester_sample_frame.png",
    # The twelve drive captures tests/test_eye_drive.py samples. tools/eye_drive.py reads them by name from
    # output/drive and measures each frame's own pixels, so they are that test's input, not a preview: with
    # them absent a clean checkout reported twelve failed shots and three reds (card t_d2c52f15). They are
    # un-ignored one by one in .gitignore after output/ and output/drive/ are re-excluded, and they are named
    # here one by one because this list is read rather than discovered: a missing fixture has to be visible
    # in the source, not inferred at run time.
    "output/drive/pp_drive_shot_01.png",
    "output/drive/pp_drive_shot_02.png",
    "output/drive/pp_drive_shot_03.png",
    "output/drive/pp_drive_shot_04.png",
    "output/drive/pp_drive_shot_05.png",
    "output/drive/pp_drive_shot_06.png",
    "output/drive/pp_drive_shot_07.png",
    "output/drive/pp_drive_shot_08.png",
    "output/drive/pp_drive_shot_09.png",
    "output/drive/pp_drive_shot_10.png",
    "output/drive/pp_drive_shot_11.png",
    "output/drive/pp_drive_shot_12.png",
)

# The calls that answer "is this input here". A skip guarded by one of these is the defect.
EXISTENCE_CALLS = {"os.path.exists", "os.path.isfile", "os.path.isdir", "os.access"}


def _dotted(node):
    """Render an attribute chain like os.path.exists as text, or None when it is not one."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _is_skip(node):
    if isinstance(node, ast.Expr):
        node = node.value
    if not isinstance(node, ast.Call):
        return False
    name = _dotted(node.func) or ""
    return name in {"pytest.skip", "skip"}


def _guards_on_existence(node):
    """True when this expression tests whether a path exists, in any polarity."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and (_dotted(child.func) or "") in EXISTENCE_CALLS:
            return True
    return False


def absent_input_skips(source, filename="<test>"):
    """Every line where a test skips because a path is missing, as readable strings."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as error:
        return ["%s: cannot parse (%s)" % (filename, error)]
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _guards_on_existence(node.test):
            continue
        if not any(_is_skip(child) for child in node.body):
            continue
        found.append("%s:%d: a pytest.skip is guarded by a path existence test"
                      % (filename, node.lineno))
    return found


def untracked_fixtures(tracked, prefix):
    """Fixtures the commit does not carry. `tracked` is the set of repo relative paths."""
    missing = []
    for name in FIXTURES:
        if prefix + name not in tracked:
            missing.append(name)
    return missing


def repo_root(cwd=ROOT):
    """The directory git reports as the top level for this project."""
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        raise SystemExit("cannot find the repository root: " + out.stderr.strip())
    return out.stdout.strip()


def tracked_files(repo):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, text=True,
                         stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        raise SystemExit("cannot read the tracked file list: " + out.stderr.strip())
    return {name for name in out.stdout.split("\0") if name}


def test_sources(tests_dir=TESTS):
    for name in sorted(os.listdir(tests_dir)):
        if name.endswith(".py"):
            path = os.path.join(tests_dir, name)
            with open(path, "r", encoding="utf-8") as handle:
                yield "tests/" + name, handle.read()


def check(root=ROOT):
    repo = repo_root(root)
    prefix = os.path.relpath(root, repo).replace(os.sep, "/") + "/"
    tracked = tracked_files(repo)
    problems = ["MISSING FROM COMMIT " + name for name in untracked_fixtures(tracked, prefix)]
    for name, source in test_sources(os.path.join(root, "tests")):
        problems.extend(absent_input_skips(source, name))
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("FAIL: %d problem(s)" % len(problems))
        for line in problems:
            print("  " + line)
        return 1
    print("PASS: %d fixtures tracked, no test skips on a missing input" % len(FIXTURES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
