#!/usr/bin/env python3
r"""event_log.py: regenerate EVENT-LOG.md, the timestamped log of the work done during the event (card t_da72cf80).

Why: the Meta AI Developer Hackathon runs 2026-10-26 to 2026-11-04 and asks for the work done during the
event, with the demo and the write-up judged on it. A log written by hand goes stale on the first long
night, so this tool writes it from git instead, and the log cannot disagree with the repository it
describes. Every commit that touches projects/primordial-paradox after the baseline tag is one line:

    <local commit time> | <short sha> | <card id> | <subject>

The card id is picked out of the subject when the subject names one, and the newest commit is last, so
reading down the file is reading the event in the order it happened. The first line of the file states
the baseline tag and the commit it points at, so a reader can see what the log counts from without git.

A commit that touches nothing but this file is the log being refreshed, not work done in the window, so
it is not a row. It cannot be: the file in that commit cannot name the commit that carries it, so a
--check that demanded that row would stay red on an otherwise clean tree forever. A commit that touches
this file beside real work is still a row; only a commit whose whole change is the log drops out.

The tag's commit is resolved from the tag, never typed in here: a tag moved on purpose must move the log
with it, and a tag that does not exist is an error rather than an empty log.

Usage:
  python tools/event_log.py            write EVENT-LOG.md, then print the line count and the first two lines
  python tools/event_log.py --check    write nothing: exit 1 when the file on disk would change
  python tools/event_log.py --print    write nothing: print the text it would write

Cards and lanes both run this: the nightly demo card runs it after the gates, so the log is refreshed on
a night when work landed without anyone remembering to ask.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
OUT = os.path.join(REPO, "EVENT-LOG.md")
TAG = "hackathon-baseline-2026-10-25"
PROJECT = "projects/primordial-paradox"
LOG_SELF = PROJECT + "/EVENT-LOG.md"
CARD_ID = re.compile(r"\bt_[0-9a-f]{8}\b")
LONG_DASHES = {"\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-"}
NOWIN = 0x08000000 if os.name == "nt" else 0


def git(args, cwd=REPO):
    """Run one git command and return its stdout, or raise with git's own message.

    The GIT_* variables that point git at an index, work tree or object store are dropped: a pre-commit
    hook or a lane's shell exports them, and an inherited GIT_INDEX_FILE once made a shared repository
    read every tracked file as a staged deletion (manager-intake.md, 2026-10-24). A log generator has no
    business reading a deliberately redirected index, so it asks only the checkout it sits in.

    stdin is closed rather than inherited, for the reason knowledge/SPAWN-HANDLES-2026-10-25.md measured:
    under a runner that redirects stdout to a log, the parent's stdin handle can already be dead, and a
    spawn that leaves it unset fails with WinError 6 inside DuplicateHandle before git runs at all. That
    arrived dressed as a failure of whatever called it (card t_4d5984b4 saw it here, as
    test_event_log's pathspec test).
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
                        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES")}
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace", env=env, creationflags=NOWIN, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), (proc.stderr or "").strip()[:400]))
    return proc.stdout


def plain(text):
    """The repo's writing rule in one place: a long dash never reaches the log."""
    for bad, good in LONG_DASHES.items():
        text = text.replace(bad, good)
    return text.strip()


def card_id(subject):
    """The card id the subject names, or "" when it names none."""
    found = CARD_ID.search(subject or "")
    return found.group(0) if found else ""


def parse_log(text):
    """Turn `git log` output into commit rows, oldest first.

    One commit is one line, three NUL separated fields (%h, %cd, %s): a subject cannot contain a NUL,
    so no subject can be split or merged by this parser whatever punctuation it carries. Blank lines are
    skipped, and a line with fewer than three fields raises instead of becoming a half row.
    """
    commits = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split("\x00")
        if len(fields) != 3:
            raise ValueError("line %d has %d field(s), expected 3: %r" % (number, len(fields), line[:120]))
        sha, when, subject = (plain(f) for f in fields)
        commits.append({"sha": sha, "when": when, "subject": subject, "card": card_id(subject)})
    return commits


def format_line(commit):
    """One line for one commit, with the card column kept so the columns stay aligned."""
    return " | ".join((commit["when"], commit["sha"], commit["card"] or "-", commit["subject"]))


def render(tag, tag_sha, tag_when, commits):
    """The whole file: the baseline on line 1, then one line per commit, newest last."""
    first = ("EVENT-LOG. Baseline tag %s at %s (%s local). One line per commit touching %s after it, "
             "local commit time first, newest last." % (tag, tag_sha, tag_when, PROJECT))
    return "\n".join([plain(first)] + [format_line(c) for c in commits]) + "\n"


def log_pathspec():
    """The pathspec the log is read with: this project, minus the log file itself.

    The exclusion is what makes `--check` able to pass at all. The commit that writes EVENT-LOG.md sits
    inside the pathspec it is generated from, so without the exclusion the committed file is one row
    short of its own commit for ever and the check is red on a clean tree. `:(exclude)` drops a commit
    only when nothing else in the project moved with it, so a commit that rewrites the log beside real
    work keeps its row. Measured on git 2.54: the five in window commits before this change read the
    same with and without the exclusion, because none of them touched only the log.
    """
    return ["--", PROJECT, ":(exclude)" + LOG_SELF]


def collect():
    """Ask git for the tag, its commit, and every later commit that touches this project.

    The pathspec is relative to the repository ROOT, not to this file, so git is asked from the root:
    measured 2026-10-26, `git log TAG..HEAD -- projects/primordial-paradox` run inside
    projects/primordial-paradox matched nothing, because the path was read a second level down and the
    log came out empty on a checkout with one commit since the tag. The project path is also checked
    against the tree at HEAD first, so a renamed directory fails loudly instead of logging nothing.
    """
    root = git(["rev-parse", "--show-toplevel"]).strip()
    try:
        git(["cat-file", "-e", "HEAD:" + PROJECT], cwd=root)
    except RuntimeError:
        raise RuntimeError("%s is not in the tree at HEAD, so the log would be empty" % PROJECT)
    try:
        tag_sha = git(["rev-parse", "--short=7", TAG + "^{commit}"], cwd=root).strip()
    except RuntimeError:
        raise RuntimeError("the baseline tag %s does not resolve in %s" % (TAG, root))
    tag_when = git(["log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d %H:%M",
                    TAG + "^{commit}"], cwd=root).strip()
    raw = git(["log", "--reverse", "--abbrev=7", "--date=format-local:%Y-%m-%d %H:%M",
               "--format=%h%x00%cd%x00%s", TAG + "..HEAD"] + log_pathspec(), cwd=root)
    return tag_sha, tag_when, parse_log(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Regenerate EVENT-LOG.md from git since the baseline tag.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if the file is stale")
    parser.add_argument("--print", dest="show", action="store_true", help="print the text, write nothing")
    args = parser.parse_args(argv)

    try:
        tag_sha, tag_when, commits = collect()
    except (RuntimeError, ValueError) as exc:
        print("event_log: %s" % exc)
        return 2
    text = render(TAG, tag_sha, tag_when, commits)
    lines = text.splitlines()

    if args.check:
        try:
            with open(OUT, encoding="utf-8") as handle:
                on_disk = handle.read()
        except OSError:
            on_disk = None
        if on_disk == text:
            print("event_log: EVENT-LOG.md is current (%d commit line(s))" % len(commits))
            return 0
        print("event_log: EVENT-LOG.md is stale, run python tools/event_log.py")
        return 1
    if args.show:
        print(text, end="")
        return 0

    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("event_log: EVENT-LOG.md %d line(s), %d commit line(s) since %s" % (len(lines), len(commits), TAG))
    for line in lines[:2]:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
