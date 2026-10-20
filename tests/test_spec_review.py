"""Tests for the spec clean-room gate (tools/check_spec_review.py).

The gate exists so that code cannot be written from a spec that no fresh reviewer has confirmed from public material.
These tests prove the gate catches a missing row, a lying status and a strict refusal, and that it does not quietly pass
the repository's own current debt.
"""

from __future__ import annotations

import os

import check_spec_review

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_root(tmp_path, rows: str):
    """A throwaway root with two specs and a ledger holding the given table body."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "01-state-machine.md").write_text("# one\n", encoding="utf-8")
    (tmp_path / "specs" / "02-input.md").write_text("# two\n", encoding="utf-8")
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "knowledge" / "SPEC-REVIEW.md").write_text(
        "| Spec | Status | Reviewer | Date | Note |\n| --- | --- | --- | --- | --- |\n" + rows,
        encoding="utf-8")
    return str(tmp_path)


def test_pending_debt_is_reported_and_is_not_an_error(tmp_path, capsys):
    """The gate reports debt loudly without failing the run.

    Built on a fixture root on purpose: the live repository's own debt must not be pinned here, because paying that
    debt is the point of the gate, and a test that asserts PENDING > 0 on the real repository breaks exactly when the
    review lands.
    """
    root = _make_root(tmp_path,
                      "| specs/01-state-machine.md | pending | code-review | - | - |\n"
                      "| specs/02-input.md | confirmed | code-review | 2026-10-20 | ok |\n")
    assert check_spec_review.check(root) == []
    assert check_spec_review.PENDING == 1
    assert check_spec_review.TOTAL_SPECS == 2
    assert check_spec_review.main(["--root", root]) == 0
    output = capsys.readouterr().out
    assert "PENDING spec review: specs/01-state-machine.md" in output


def test_strict_refuses_while_pending(tmp_path):
    root = _make_root(tmp_path,
                      "| specs/01-state-machine.md | confirmed | code-review | 2026-10-20 | ok |\n"
                      "| specs/02-input.md | pending | code-review | - | - |\n")
    assert check_spec_review.check(root) == []
    assert check_spec_review.main(["--root", root, "--strict"]) == 1


def test_strict_passes_when_every_spec_has_a_verdict(tmp_path):
    root = _make_root(tmp_path,
                      "| specs/01-state-machine.md | confirmed | code-review | 2026-10-20 | ok |\n"
                      "| specs/02-input.md | rewritten | code-review | 2026-10-20 | removed rule 4 |\n")
    assert check_spec_review.check(root) == []
    assert check_spec_review.main(["--root", root, "--strict"]) == 0


def test_a_spec_with_no_row_is_an_error(tmp_path):
    root = _make_root(tmp_path, "| specs/01-state-machine.md | confirmed | code-review | 2026-10-20 | ok |\n")
    errors = check_spec_review.check(root)
    assert any("specs/02-input.md: no row" in line for line in errors)


def test_a_lying_status_is_an_error(tmp_path):
    root = _make_root(tmp_path,
                      "| specs/01-state-machine.md | reviewed | code-review | 2026-10-20 | ok |\n"
                      "| specs/02-input.md | confirmed | code-review | 2026-10-20 | ok |\n")
    errors = check_spec_review.check(root)
    assert any("is not a verdict" in line for line in errors)


def test_a_verdict_without_a_reviewer_is_an_error(tmp_path):
    root = _make_root(tmp_path,
                      "| specs/01-state-machine.md | confirmed | - | - | ok |\n"
                      "| specs/02-input.md | confirmed | code-review | 2026-10-20 | ok |\n")
    errors = check_spec_review.check(root)
    assert any("no reviewer or no date" in line for line in errors)
