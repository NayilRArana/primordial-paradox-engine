"""Every spawn in this suite must pass stdin explicitly, so no child depends on the parent's handle table.

The defect this pins, measured on 2026-10-25: the nightly ran the suite with its stdout redirected to a log and
three checks died with OSError [WinError 6] The handle is invalid, raised inside subprocess._make_inheritable
before the child existed. Same 24 checks, same interpreter, no redirection: 24 passed. The trigger is not the
code under test, it is the inherited handle.

A spawn that leaves stdin unset asks subprocess to duplicate whatever stdin the parent holds. When the parent
holds nothing, or holds a handle that was replaced by the capture machinery and then closed, the duplicate fails
and the failure arrives as a red that looks like a defect in the thing under test. Passing stdin=DEVNULL or
stdin=PIPE makes the child independent of the parent's table, which is what we want from a test's child process.

Scope: the suite. tools/ still carries thirteen unguarded one-shot spawns (git, python, pip); they are the same
shape one level deeper and are carded separately rather than changed here without their own verification.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPAWN_FUNCS = {"run", "Popen", "check_output", "check_call", "call"}


def offenders():
    found = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr not in SPAWN_FUNCS:
                continue
            if not (isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
                continue
            keywords = {kw.arg for kw in node.keywords if kw.arg}
            if "stdin" not in keywords:
                found.append("%s:%d subprocess.%s" % (
                    path.relative_to(ROOT).as_posix(), node.lineno, func.attr))
    return found


def test_every_spawn_in_the_suite_passes_stdin_explicitly():
    bad = offenders()
    assert bad == [], (
        "these spawns inherit the parent's stdin handle, so they die with WinError 6 when the suite's stdout is "
        "redirected to a log. Pass stdin=subprocess.DEVNULL or stdin=subprocess.PIPE:\n  " + "\n  ".join(bad))


def test_the_scan_actually_finds_spawns():
    """A scanner that silently matches nothing would pass the row above and prove nothing."""
    count = 0
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in SPAWN_FUNCS \
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                count += 1
    assert count >= 20, "only %d spawns seen, so the scan is not reading the suite" % count
