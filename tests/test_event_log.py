"""Tests for tools/event_log.py (card t_da72cf80).

What is pinned here: the parser, against a fixture git log, and the two properties the hackathon log is
read for. One commit becomes exactly one line whatever punctuation its subject carries; the card id is
picked out of the subject only when the subject names one; the newest commit is the LAST line; and the
first line of the file states the baseline tag and the commit it points at. The last test asks the real
tag, so a tag that the log cannot resolve fails here instead of writing an empty log on demo night.

The fixture is the exact shape the tool asks git for: `%h%x00%cd%x00%s`, one commit per line, oldest
first. No test in this file writes EVENT-LOG.md in this checkout; the pathspec test builds a throwaway
repository under tmp_path and writes a log there, because what it pins is git's reading of the
pathspec, not the state of this tree.
"""

import os
import re
import subprocess
import sys

import pytest

import event_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG_SHA = "ae3a6cb"
TAG_WHEN = "2026-10-25 20:58"

# Two commits in the order `git log --reverse` prints them, NUL separated like the real call. The second
# subject carries a pipe, a colon and a question mark: the log is read by people, and a subject is never
# rewritten to fit a format.
FIXTURE = "\n".join([
    "ae3a6cb\x002026-10-25 20:58\x00SHIP-DRAWN-IN-ITS-ROWS: the sea is drawn in three tones (card t_463cb8c1)",
    "37efb6a\x002026-10-26 09:12\x00PALETTE-REPORT | who reads c4e9843? the gate log entry, corrected",
]) + "\n"


def test_parse_log_keeps_one_row_per_commit_oldest_first():
    commits = event_log.parse_log(FIXTURE)
    assert [c["sha"] for c in commits] == ["ae3a6cb", "37efb6a"], commits
    assert commits[0]["when"] == TAG_WHEN
    assert commits[0]["subject"].startswith("SHIP-DRAWN-IN-ITS-ROWS: the sea is drawn")
    assert commits[1]["subject"] == "PALETTE-REPORT | who reads c4e9843? the gate log entry, corrected"


def test_the_card_id_comes_from_the_subject_only():
    commits = event_log.parse_log(FIXTURE)
    assert commits[0]["card"] == "t_463cb8c1"
    assert commits[1]["card"] == "", "a subject that names no card must carry none"
    assert event_log.card_id("no id here") == ""
    assert event_log.card_id("(card t_0badc0de) and t_463cb8c1") == "t_0badc0de", "the first id wins"
    assert event_log.card_id("t_463cb8c1 but a longer run later") == "t_463cb8c1"
    assert event_log.card_id("t_463cb8c1ff") == "", "an eight character id is the whole id"


def test_a_broken_line_raises_instead_of_becoming_a_half_row():
    with pytest.raises(ValueError):
        event_log.parse_log("ae3a6cb\x002026-10-25 20:58\n")
    with pytest.raises(ValueError):
        event_log.parse_log("just one field\n")
    assert event_log.parse_log("") == []
    assert event_log.parse_log("\n\n") == []


def test_render_states_the_tag_first_and_puts_the_newest_commit_last():
    commits = event_log.parse_log(FIXTURE)
    text = event_log.render(event_log.TAG, TAG_SHA, TAG_WHEN, commits)
    lines = text.splitlines()
    assert len(lines) == len(commits) + 1, "one baseline line plus one line per commit"
    assert lines[0].startswith("EVENT-LOG. Baseline tag %s at %s " % (event_log.TAG, TAG_SHA)), lines[0]
    assert TAG_WHEN in lines[0]
    assert lines[0].endswith("newest last.")
    assert lines[-1].startswith("2026-10-26 09:12 | 37efb6a | - | PALETTE-REPORT"), lines[-1]
    assert lines[1].endswith("(card t_463cb8c1)") and "| t_463cb8c1 |" in lines[1], lines[1]
    # The project path is named once, on line 1, so every commit row keeps the same four columns. A
    # subject that itself contains " | " stays in the last column, which is why the split is bounded.
    assert event_log.PROJECT in lines[0]
    assert all(len(line.split(" | ", 3)) == 4 for line in lines[1:]), lines


def test_the_log_is_ascii_and_carries_no_long_dash():
    commits = event_log.parse_log(FIXTURE)
    text = event_log.render(event_log.TAG, TAG_SHA, TAG_WHEN, commits)
    assert text.isascii(), [line for line in text.splitlines() if not line.isascii()]
    assert not re.search("[\u2010-\u2015\u2212]", text)
    # A subject written with a long dash is recorded with a hyphen rather than copied into the log.
    swapped = event_log.parse_log("37efb6a\x002026-10-26 09:12\x00one \u2014 two\n")
    assert swapped[0]["subject"] == "one - two", swapped[0]


def test_an_empty_event_is_a_one_line_file():
    text = event_log.render(event_log.TAG, TAG_SHA, TAG_WHEN, [])
    assert text.splitlines() == [
        "EVENT-LOG. Baseline tag %s at %s (%s local). One line per commit touching %s after it, "
        "local commit time first, newest last." % (event_log.TAG, TAG_SHA, TAG_WHEN, event_log.PROJECT)]


# Card TEST-CLASSIFY-33: this row asks the checkout's own git for the real tag, and the offloaded tree is
# a zip, so it is one of the rows that skip on Pine and run here.
@pytest.mark.needs_git_checkout
def test_the_real_tag_resolves_and_the_cli_prints_the_log():
    tag_sha = subprocess.run(["git", "rev-parse", "--short=7", event_log.TAG + "^{commit}"], cwd=ROOT,
                             capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    assert tag_sha.returncode == 0, tag_sha.stderr
    proc = subprocess.run([sys.executable, os.path.join("tools", "event_log.py"), "--print"], cwd=ROOT,
                          capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    lines = proc.stdout.splitlines()
    assert lines[0].startswith("EVENT-LOG. Baseline tag %s at %s " % (event_log.TAG, tag_sha.stdout.strip())), lines[0]
    rows = lines[1:]
    assert rows, "no commit touches %s since the tag, so the log would say nothing about the event" % event_log.PROJECT
    assert all(len(row.split(" | ", 3)) == 4 for row in rows), rows


def test_the_pathspec_is_the_project_minus_the_log_file_itself():
    """Card t_b412f8eb: the exclusion is the whole contract, so it is checked as text.

    git reads the pathspec from the repository root, so the exclusion has to be the root relative path
    of the file this tool writes. If the two ever drift apart, the exclusion guards a path git never
    logs and --check goes back to being red on a clean tree.
    """
    spec = event_log.log_pathspec()
    assert spec == ["--", event_log.PROJECT, ":(exclude)" + event_log.LOG_SELF], spec
    assert event_log.LOG_SELF == event_log.PROJECT + "/EVENT-LOG.md", event_log.LOG_SELF
    assert event_log.OUT == os.path.join(event_log.REPO, "EVENT-LOG.md"), event_log.OUT
    assert not os.path.isabs(event_log.LOG_SELF), "a pathspec from the root is relative"


def _git_in(repo, *args):
    """Run one git command inside a throwaway repository, with a pinned identity and a defined stdin."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_NAME": "event log test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "event log test", "GIT_COMMITTER_EMAIL": "test@example.invalid"})
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120, stdin=subprocess.DEVNULL)
    assert proc.returncode == 0, (args, proc.stdout, proc.stderr)
    return proc.stdout


def _write(path, text):
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


@pytest.mark.needs_git_checkout
def test_a_commit_that_only_rewrites_the_log_is_not_a_row(tmp_path, monkeypatch):
    """The property --check hangs on, measured on real git in a throwaway repository.

    Without the exclusion the refresh commit is a row, and the file it writes can never name it: the
    committed log is one row short of its own commit for ever, and --check is red on a clean tree. With
    the exclusion only a commit whose whole change is the log drops out, so the fourth commit here
    (log beside real work) keeps its row.
    """
    repo = tmp_path / "repo"
    project = repo / "projects" / "primordial-paradox"
    _write(project / "work.txt", "one\n")
    _git_in(repo, "init", "-q")
    _git_in(repo, "add", "-A")
    _git_in(repo, "commit", "-q", "-m", "scaffold")
    _git_in(repo, "tag", "-a", event_log.TAG, "-m", "baseline")
    _write(project / "work.txt", "two\n")
    _git_in(repo, "commit", "-q", "-am", "real work (card t_01234567)")
    _write(project / "EVENT-LOG.md", "the log\n")
    _git_in(repo, "add", "-A")
    _git_in(repo, "commit", "-q", "-m", "log refresh only")
    _write(project / "EVENT-LOG.md", "the log, again\n")
    _write(project / "more.txt", "three\n")
    _git_in(repo, "add", "-A")
    _git_in(repo, "commit", "-q", "-m", "log beside real work")

    real_git = event_log.git
    monkeypatch.setattr(event_log, "git", lambda args, cwd=None: real_git(args, cwd=str(repo)))
    monkeypatch.setattr(event_log, "PROJECT", "projects/primordial-paradox")
    monkeypatch.setattr(event_log, "LOG_SELF", "projects/primordial-paradox/EVENT-LOG.md")
    tag_sha, tag_when, commits = event_log.collect()

    assert re.fullmatch(r"[0-9a-f]{7}", tag_sha), tag_sha
    assert tag_when, "the baseline line needs the tag's commit time"
    assert [c["subject"] for c in commits] == ["real work (card t_01234567)", "log beside real work"], commits
    assert commits[0]["card"] == "t_01234567", commits[0]
