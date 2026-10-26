"""Tests for the Pine retry rounds and the coverage verdict in tools/run_tests.py.

What is proved here, rather than asserted in a comment:

  - a shard whose upload died is retried, and the retry replaces that shard's record instead of
    joining it, so the same file is never held by a delivered record and a failed one at once
    (which is what would make the merge count those rows on Pine and on the desktop);
  - a retry that delivers sends nothing to the desktop for those files, and one that fails still
    does, so no row goes unmeasured either way;
  - a run where Pine carried 47.2 percent of the rows prints a named COVERAGE FAIL line, names the
    shard that never delivered, and states the target, instead of leaving the share inside a green
    SUMMARY (card t_8e880980, following t_a6fc50a2);
  - a run that carried its share, and a --local run, print no coverage failure at all.

Nothing here opens a socket, starts a Computer or spends anything: run_pine is replaced with a
function that returns the record the far side would have written.
"""

from __future__ import annotations

import run_tests


def _shard(name, files, *, status="completed", passed=0, failed=0, skipped=0,
           failed_ids=(), no_tests=False, summary=""):
    """One shard record in the shape run_pine.py builds, with only the fields the merge reads."""
    counts = {"passed": passed, "failed": failed, "error": 0, "skipped": skipped, "deselected": 0}
    return {
        "path": "offload-%s.json" % name,
        "name": name,
        "status": status,
        "files": list(files),
        "deselected_on_pine": [],
        "summary": summary,
        "wall_seconds": 10.0,
        "est_computer_usd": 0.001,
        "counts": counts,
        "counts_line": "" if no_tests else "%d passed in 1.0s" % passed,
        "failed_ids": list(failed_ids),
        "error_ids": [],
        "reasons": {node: "assert 0" for node in failed_ids},
        "agent_summary": "",
        "no_tests": no_tests,
    }


def _pine(*shards):
    return {"interpreter": "python", "command": ["pine_offload.py"], "exit_code": 0,
            "wall_seconds": 30.0, "log": "first attempt", "shards": list(shards),
            "stale_shard_files": []}


def _dead(name, files, message):
    """A shard that died on the upload, the way t_8e880980 measured it."""
    record = _shard(name, files, status="error", summary=message)
    return record


UPLOAD_RESET = ("PineCallError: pine write_file failed: ConnectionError: pinesandbox: connection "
                "failed: [Errno 10054] An existing connection was forcibly closed by the remote host")


def test_a_delivered_retry_replaces_the_dead_record_for_the_same_files(monkeypatch):
    """The retried files are Pine's, in one record, and the desktop owes none of them."""
    files = ["tests/test_a.py", "tests/test_b.py"]
    pine = _pine(_shard("sweep-0", ["tests/test_other.py"], passed=5),
                 _dead("sweep-1", files, UPLOAD_RESET))

    calls = []

    def fake_run_pine(paths, name, shards, extra_args, timeout_s):
        calls.append({"paths": list(paths), "name": name, "shards": shards})
        return {"interpreter": "python", "command": ["pine_offload.py", name], "exit_code": 0,
                "wall_seconds": 20.0, "log": "retry log",
                "shards": [_shard(name + "-0", paths, passed=11)], "stale_shard_files": []}

    monkeypatch.setattr(run_tests, "run_pine", fake_run_pine)
    out = run_tests.retry_failed_shards(pine, "sweep", [], 60, rounds=2, backoff=0.0)

    assert calls and calls[0]["paths"] == files
    assert calls[0]["shards"] == 1
    assert run_tests._undelivered(out) == []
    held = [path for shard in out["shards"] for path in shard["files"]]
    assert sorted(held) == sorted(files + ["tests/test_other.py"])
    assert out["retry_rounds"] == 1

    merged = run_tests.merge(out, None)
    assert merged["total_tests"] == 16  # 5 + 11, each row once
    assert merged["desktop_targets"] == []
    assert run_tests.coverage_gap(merged, 90.0, out) == ""


def test_a_retry_that_fails_too_leaves_the_rows_to_the_desktop(monkeypatch):
    """Two rounds of failure still measure every row, now on the desktop, and say so."""
    files = ["tests/test_a.py"]
    pine = _pine(_dead("sweep-0", files, UPLOAD_RESET))

    def always_dead(paths, name, shards, extra_args, timeout_s):
        return {"interpreter": "python", "command": ["pine_offload.py", name], "exit_code": 0,
                "wall_seconds": 20.0, "log": "retry log",
                "shards": [_dead(name + "-0", paths, UPLOAD_RESET)], "stale_shard_files": []}

    monkeypatch.setattr(run_tests, "run_pine", always_dead)
    out = run_tests.retry_failed_shards(pine, "sweep", [], 60, rounds=2, backoff=0.0)

    dead = run_tests._undelivered(out)
    assert [shard["name"] for shard in dead] == ["sweep-retry2-0"]  # the last attempt is the record
    assert out["retry_rounds"] == 2
    assert len([s for s in out["shards"] if "tests/test_a.py" in s["files"]]) == 1

    merged = run_tests.merge(out, None)
    # main() builds the desktop targets from the undelivered shards, so those files have to still be
    # there for it: nothing goes unmeasured, it just moves host.
    assert [shard["files"] for shard in run_tests._undelivered(out)] == [files]
    gap = run_tests.coverage_gap(merged, 90.0, out)
    assert gap.startswith("COVERAGE FAIL")
    assert "sweep-retry2-0" in gap
    assert "target 90.0 percent" in gap


def test_a_shard_with_no_tests_counts_as_undelivered():
    pine = _pine(_shard("sweep-0", ["tests/test_a.py"], no_tests=True))
    assert [s["name"] for s in run_tests._undelivered(pine)] == ["sweep-0"]


def test_the_coverage_line_names_the_shortfall_and_the_target():
    pine = _pine(_shard("sweep-0", ["tests/test_a.py"], passed=740),
                 _dead("sweep-1", ["tests/test_b.py"], UPLOAD_RESET))
    merged = {"pine_share": 47.2, "total_tests": 1560, "pine_tests": 740,
              "desktop_targets": ["tests/test_b.py", "tests/test_c.py"]}

    gap = run_tests.coverage_gap(merged, 90.0, pine)

    assert gap.startswith("COVERAGE FAIL ")
    assert "pine carried 47.2 percent of 1560 tests" in gap
    assert "target 90.0 percent" in gap
    assert "sweep-1 never delivered" in gap
    assert "2 desktop target(s)" in gap


def test_a_run_that_carried_its_share_has_no_coverage_failure():
    pine = _pine(_shard("sweep-0", ["tests/test_a.py"], passed=1427))
    merged = {"pine_share": 94.6, "total_tests": 1511, "pine_tests": 1511, "desktop_targets": []}
    assert run_tests.coverage_gap(merged, 90.0, pine) == ""


def test_a_local_run_makes_no_pine_claim():
    merged = {"pine_share": 0.0, "total_tests": 1561, "pine_tests": 0, "desktop_targets": []}
    assert run_tests.coverage_gap(merged, 90.0, None) == ""


def test_a_delivered_retry_is_a_pine_run_even_though_the_first_attempt_exited_2(monkeypatch):
    """The retry is worth nothing if the run still reports a broken Pine: exit code is not the test."""
    files = ["tests/test_a.py"]
    pine = _pine(_dead("sweep-0", files, UPLOAD_RESET))
    pine["exit_code"] = 2  # the first attempt's exit code, kept in the record

    def delivers(paths, name, shards, extra_args, timeout_s):
        return {"interpreter": "python", "command": ["pine_offload.py", name], "exit_code": 0,
                "wall_seconds": 20.0, "log": "retry log",
                "shards": [_shard(name + "-0", paths, passed=12)], "stale_shard_files": []}

    monkeypatch.setattr(run_tests, "run_pine", delivers)
    out = run_tests.retry_failed_shards(pine, "sweep", [], 60, rounds=2, backoff=0.0)
    merged = run_tests.merge(out, None)

    assert out["exit_code"] == 2
    assert out["retry_rounds"] == 1
    assert run_tests.pine_undelivered(out, merged) is False
    assert run_tests.coverage_gap(merged, 90.0, out) == ""


def test_a_run_where_every_round_died_is_a_broken_pine_run(monkeypatch):
    files = ["tests/test_a.py"]
    pine = _pine(_dead("sweep-0", files, UPLOAD_RESET))

    def always_dead(paths, name, shards, extra_args, timeout_s):
        return {"interpreter": "python", "command": ["pine_offload.py", name], "exit_code": 0,
                "wall_seconds": 20.0, "log": "retry log",
                "shards": [_dead(name + "-0", paths, UPLOAD_RESET)], "stale_shard_files": []}

    monkeypatch.setattr(run_tests, "run_pine", always_dead)
    out = run_tests.retry_failed_shards(pine, "sweep", [], 60, rounds=2, backoff=0.0)
    merged = run_tests.merge(out, None)

    assert run_tests.pine_undelivered(out, merged) is True


def test_a_completed_shard_with_no_counts_is_a_broken_pine_run():
    pine = _pine(_shard("sweep-0", ["tests/test_a.py"], no_tests=True))
    merged = run_tests.merge(pine, None)
    assert run_tests.pine_undelivered(pine, merged) is True


def test_a_local_run_is_not_a_broken_pine_run():
    merged = {"pine_share": 0.0, "total_tests": 1561, "pine_tests": 0, "desktop_targets": []}
    assert run_tests.pine_undelivered(None, merged) is False


def _desktop(targets, passed=3):
    return {"command": ["python", "-m", "pytest"], "exit_code": 0, "wall_seconds": 2.0, "log": "",
            "targets": list(targets),
            "counts": {"passed": passed, "failed": 0, "error": 0, "skipped": 0},
            "counts_line": "%d passed in 0.1s" % passed, "failed_ids": [], "error_ids": [],
            "reasons": {}, "no_tests": False, "agent_summary": ""}


def _run_main(monkeypatch, tmp_path, pine_results, argv, desktop_passed=3):
    """Drive main() with the far side replaced, so the printed lines and the exit code are the run's."""
    offload = ["tests/test_a.py"]
    here = ["tests/test_red.py"]
    monkeypatch.setattr(run_tests, "selection_files", lambda paths: offload + here)
    monkeypatch.setattr(run_tests, "offload_rules", lambda: {})
    monkeypatch.setattr(run_tests, "split_selection", lambda selection, rules: (offload, here, {}))
    results = list(pine_results)

    def fake_run_pine(paths, name, shards, extra_args, timeout_s):
        return results.pop(0) if results else _pine(_dead(name + "-0", paths, UPLOAD_RESET))

    monkeypatch.setattr(run_tests, "run_pine", fake_run_pine)
    monkeypatch.setattr(run_tests, "run_desktop",
                        lambda targets, extra, passthrough: _desktop(targets, desktop_passed))
    monkeypatch.setattr(run_tests, "report_path", lambda name: tmp_path / ("offload-" + name + ".json"))
    monkeypatch.setattr(run_tests.sys, "argv", ["run_tests.py"] + list(argv))
    return run_tests.main()


def test_main_prints_the_coverage_failure_and_exits_2_when_pine_lost_a_shard(monkeypatch, tmp_path, capsys):
    """The 2026-10-25 run: 47.2 percent, every row measured, and it must not read as a Pine run."""
    dead = _pine(_shard("sweep-0", ["tests/test_other.py"], passed=740),
                 _dead("sweep-1", ["tests/test_a.py"], UPLOAD_RESET))
    dead["exit_code"] = 2
    rc = _run_main(monkeypatch, tmp_path, [dead], ["--name", "cov", "--retry-rounds", "1"],
                   desktop_passed=822)
    out = capsys.readouterr().out

    assert rc == 2
    assert "COVERAGE FAIL" in out
    assert "pine carried 47.4 percent of 1562 tests" in out
    assert "target 90.0 percent" in out
    assert "never delivered" in out
    assert "target 90.0 percent NOT met" in out


def test_main_exits_0_when_a_retry_brought_the_shard_back(monkeypatch, tmp_path, capsys):
    """A retried shard that delivered is Pine's: the run counts as a Pine run, first exit code or not."""
    dead = _pine(_dead("sweep-0", ["tests/test_a.py"], UPLOAD_RESET))
    dead["exit_code"] = 2
    back = {"interpreter": "python", "command": ["pine_offload.py"], "exit_code": 0,
            "wall_seconds": 20.0, "log": "retry log",
            "shards": [_shard("sweep-retry-0", ["tests/test_a.py"], passed=900)],
            "stale_shard_files": []}
    rc = _run_main(monkeypatch, tmp_path, [dead, back], ["--name", "cov2", "--retry-rounds", "2"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "COVERAGE FAIL" not in out
    assert "delivered after 1 retry round(s)" in out
    assert "SUMMARY passed=" in out
