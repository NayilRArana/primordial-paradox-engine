"""The build step must distinguish "the build passed" from "the build was never measured".

Written with the 2026-10-19 change that made a GameMaker-less machine report honestly. Before it,
tools/integration_build.py returned 0 for run.ps1's exit 2, so the push output read
"integration primordial-paradox-build: PASS ... BUILD SKIP": an unmeasured step reported as measured.
It now exits 3, and suite_config.json declares 3 as that step's unmeasured result, so the gate prints
UNMEASURED and never PASS.

run.ps1 is not executed here. subprocess.run inside the tool is replaced with a stub that returns the
exit code the real script returns, which is exactly the branch under test.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import integration_build


class _Completed:
    def __init__(self, returncode: int, stdout: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _run_with(monkeypatch, returncode: int) -> tuple[int, str]:
    monkeypatch.setattr(integration_build.subprocess, "run",
                        lambda *a, **k: _Completed(returncode, "run.ps1 said something"))
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = integration_build.main()
    return code, buf.getvalue()


def test_missing_game_maker_is_unmeasured_not_a_pass(monkeypatch):
    # run.ps1 exit 2 means no runtime, no Igor, or no licence folder. That is unmeasured.
    code, out = _run_with(monkeypatch, 2)
    assert code == 3
    assert "BUILD UNMEASURED" in out
    assert "NOT a pass" in out
    assert "BUILD PASS" not in out


def test_successful_build_is_a_pass(monkeypatch):
    code, out = _run_with(monkeypatch, 0)
    assert code == 0
    assert "BUILD PASS" in out


def test_other_failure_is_a_failure(monkeypatch):
    code, out = _run_with(monkeypatch, 1)
    assert code == 1
    assert "BUILD FAIL" in out
    assert "BUILD UNMEASURED" not in out


def test_missing_run_script_fails_rather_than_skips(monkeypatch, tmp_path):
    # A missing script is a broken install, not an absent GameMaker: it must not read as a skip.
    monkeypatch.setattr(integration_build, "RUN_PS1", str(tmp_path / "run.ps1"))
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = integration_build.main()
    assert code == 1
    assert "BUILD FAIL" in buf.getvalue()


def test_the_gate_config_declares_three_as_unmeasured():
    """The exit code only means something because the gate config declares it."""
    import json
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = os.path.join(root, "..", "arananet", "manager", "guard", "suite_config.json")
    with open(config, encoding="utf-8") as fh:
        data = json.load(fh)
    step = next(s for s in data["integration"] if s["name"] == "primordial-paradox-build")
    assert step["unmeasured_exit_codes"] == [3]
