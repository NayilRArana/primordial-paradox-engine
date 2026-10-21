"""Integration step for the repo gates: build the GameMaker project when GameMaker exists, say so when it does not.

The unit gate is pytest over tools\\check_data.py, tools\\check_project.py and tools\\check_cleanroom.py, which needs no
GameMaker. This step is the part a unit test cannot reach: Igor compiling the .yyp and launching the game. It is written
to be honest about the difference between "the build passed" and "the build was never measured":

    exit 0 and "BUILD PASS"        Igor compiled and launched the game
    exit 3 and "BUILD UNMEASURED"  GameMaker, Igor or the licence folder is absent (run.ps1 exit 2)
    exit 1                        anything else, including a data check failing inside run.ps1

A skip is a third outcome, not a quiet pass: exit 3 is declared as this step's unmeasured result in
suite_config.json, where the gate prints it as "UNMEASURED (GameMaker not installed)" and never as
PASS. Exit 0 here for a skip is what made the push output read "integration primordial-paradox-build:
PASS ... BUILD SKIP" on 2026-10-19, an unmeasured step reported as measured. It stays unmeasured until
Nayil installs GameMaker and logs in once, which is his step and not the bot's.

Usage:
    python tools/integration_build.py
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_PS1 = os.path.join(ROOT, "tools", "run.ps1")


def main() -> int:
    if not os.path.isfile(RUN_PS1):
        print("BUILD FAIL: tools/run.ps1 is missing")
        return 1

    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", RUN_PS1, "-SkipChecks",
    ]
    # stdin=DEVNULL on purpose: with no stdin given, CPython hands the child this process's own
    # STD_INPUT_HANDLE and duplicates it, which raises OSError [WinError 6] if that handle is already
    # invalid. The build reads no stdin, so DEVNULL costs nothing.
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                stdin=subprocess.DEVNULL)
    output = (completed.stdout or "") + (completed.stderr or "")
    for line in output.splitlines():
        print(line)

    if completed.returncode == 0:
        print("BUILD PASS: Igor compiled the project and launched the game")
        return 0
    if completed.returncode == 2:
        print("BUILD UNMEASURED: GameMaker is not installed on this machine, so no build was measured. "
              "This is NOT a pass, it is an unmeasured integration step.")
        return 3

    print("BUILD FAIL: run.ps1 exited %d" % completed.returncode)
    return 1


if __name__ == "__main__":
    sys.exit(main())
