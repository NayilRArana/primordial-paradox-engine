#!/usr/bin/env python3
"""idle_check.py: the launch gate. Nothing automatic may open a window while Nayil is at the computer.

Nayil's rule, 2026-10-22 (card CAPTURE-QUIET): a game window that opens by itself while he is using the PC, and music
that starts on its own while his partner is home, break a standing rule. This file is the one answer to "may a worker
open a window right now". It reuses the GetLastInputInfo logic the manager's guard already runs
(Shared\\projects\\arananet\\manager\\guard\\idle_gate.py, measured on this PC since 2026-10-09) instead of inventing a
second way to ask Windows when the user last touched the keyboard or the mouse.

The rule in numbers: a launch is allowed only when there has been no keyboard or mouse input for MIN_IDLE_S (180 s,
three minutes). With --wait the gate polls and launches the moment the user goes quiet, up to that many seconds; with
no wait (the default) it skips at once and says so, so a capture card can be retried later instead of fighting him for
the screen.

Usage:
    python tools\\idle_check.py                    print the idle time and the verdict for 180 s
    python tools\\idle_check.py --min-idle 600     another threshold
    python tools\\idle_check.py --wait 600         poll up to ten minutes for him to go quiet
    python tools\\idle_check.py --force            the override a person at the keyboard may use on purpose
    python tools\\idle_check.py --selftest         run the decision table, opens nothing, no game needed
    python tools\\idle_check.py --json             one json line instead of the P: lines

Exit codes:
    0  the launch is allowed (quiet long enough, or --force)
    4  the launch is refused: input was recent, the wait ran out, or the idle time cannot be read on this host
    1  --selftest found a decision that is wrong

Every line the gate prints starts with "P: " like the other tools, so a worker's log shows the decision in the same
shape as its other claims.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time

# Three minutes of no keyboard and no mouse, which is Nayil's own number in the card.
MIN_IDLE_S = 180.0
# How often the gate asks again while it is waiting. The manager's guard polls every 20 s; 20 s is also short enough
# that a launch does not sit a whole minute after the user walks away.
POLL_S = 20.0
# The exit code a refused launch returns. It is 4 and not 3, because 3 is the watchdog's code in this harness and in
# play_demo.py: "I did not open a window" must never read as "the run overran".
EXIT_REFUSED = 4
LOG_NAME = "idle_check.log"


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds_windows() -> float:
    """Seconds since the last keyboard or mouse input, asked through GetLastInputInfo.

    This is the manager's guard arithmetic, unchanged: the tick of the last input is subtracted from the tick now, and
    both are 32 bit millisecond counters, so the subtraction is done on the unsigned difference.
    """
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise OSError("GetLastInputInfo failed")
    return (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0


def idle_seconds():
    """Seconds since the last input, or None when this host cannot answer.

    None is not zero and it is not a pass: a host that cannot measure the idle time cannot promise that nobody is at
    the keyboard, so the gate refuses. Pine has no desktop session at all, which is exactly when a launch must not
    happen anyway.
    """
    if sys.platform != "win32":
        return None
    try:
        return idle_seconds_windows()
    except Exception:  # gate: ok an unreadable idle time is refused below, never guessed at
        return None


def log(msg: str, path: str | None = None) -> None:
    """Append one line beside this file, trimmed to the last 100 KB like the manager's guard does."""
    target = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_NAME)
    try:
        if os.path.exists(target) and os.path.getsize(target) > 100_000:
            os.replace(target, target + ".old")
        with open(target, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(time.strftime("%Y-%m-%dT%H:%M:%S") + "  " + msg + "\n")
    except OSError:  # gate: ok the log is a record, never a precondition: a gate that cannot write still decides
        pass


def check(idle_read=None, min_idle: float = MIN_IDLE_S, wait_s: float = 0.0, poll_s: float = POLL_S,
          clock=time.monotonic, sleep=time.sleep, say=print):
    """May a window be opened now? Returns (allowed, idle_at_the_last_read).

    The wait is the whole difference between a capture card and a person: with wait_s = 0 the answer is given at once
    (skip this attempt, the next card run tries again), and with wait_s > 0 the gate holds the launch and takes it the
    moment the user has been quiet for min_idle seconds, or gives up when the wait runs out.
    """
    reader = idle_read or idle_seconds
    started = clock()
    while True:
        idle = reader()
        if idle is None:
            say("P: idle gate REFUSED: this host cannot report the idle time, so no window was opened")
            log("refused: idle time unreadable")
            return False, None
        if idle >= min_idle:
            say("P: idle gate allows the launch: no input for %.0f s, %.0f s required" % (idle, min_idle))
            log("allowed: idle %.0f s >= %.0f s" % (idle, min_idle))
            return True, idle
        waited = clock() - started
        if waited >= wait_s:
            say("P: idle gate SKIPPED the launch: input %.0f s ago, %.0f s required, waited %.0f s of %.0f s, "
                "so nothing was opened and the next run tries again" % (idle, min_idle, waited, wait_s))
            log("skipped: idle %.0f s < %.0f s, waited %.0f s" % (idle, min_idle, waited))
            return False, idle
        say("P: idle gate waits: input %.0f s ago, %.0f s required, %.0f s of %.0f s waited"
            % (idle, min_idle, waited, wait_s))
        sleep(max(0.0, min(poll_s, wait_s - waited)))


def verdict(idle_read=None, min_idle: float = MIN_IDLE_S, wait_s: float = 0.0, force: bool = False, say=print):
    """The gate with the one override a human may use on purpose. Returns (allowed, idle)."""
    if force:
        idle = (idle_read or idle_seconds)()
        say("P: idle gate OVERRIDDEN by --force: the launch runs even though input %s"
            % ("cannot be read" if idle is None else "was %.0f s ago" % idle))
        log("overridden by --force")
        return True, idle
    return check(idle_read=idle_read, min_idle=min_idle, wait_s=wait_s, say=say)


def selftest(say=print) -> int:
    """The decision table, with a fake reader and a fake clock: nothing is opened and no game is needed.

    Each row is a way the gate has to answer, and the wrong answer is the one that costs Nayil a window in his face
    (a launch it allowed while he was typing) or a card that silently never ran (a skip it reported as success).
    """
    rows = []

    def run(label, idle_read, expect_allowed, expect_reason, min_idle=MIN_IDLE_S, wait_s=0.0, force=False):
        lines = []
        allowed, idle = verdict(idle_read=idle_read, min_idle=min_idle, wait_s=wait_s, force=force,
                               say=lines.append)
        text = " ".join(lines)
        ok = allowed == expect_allowed and expect_reason in text
        rows.append((label, ok, text))
        say("P: selftest %-6s %-44s %s" % ("PASS" if ok else "FAIL", label, text))
        return ok

    def quiet(seconds):
        return lambda: seconds

    def counting(values):
        values = list(values)
        state = {"n": 0}

        def read():
            index = min(state["n"], len(values) - 1)
            state["n"] += 1
            return values[index]
        return read

    ok = True
    ok &= run("input is recent, no wait", quiet(5.0), False, "SKIPPED")
    ok &= run("quiet for exactly three minutes", quiet(180.0), True, "allows")
    ok &= run("quiet for ten minutes", quiet(600.0), True, "allows")
    ok &= run("recent input, a wait of 0 is still a skip", quiet(0.0), False, "SKIPPED", wait_s=0.0)
    ok &= run("idle time unreadable", lambda: None, False, "REFUSED")
    ok &= run("override at the keyboard", quiet(3.0), True, "OVERRIDDEN", force=True)
    # The wait: the clock is fake and each poll advances it, so the loop gives up at the deadline instead of sleeping.
    ticks = {"t": 0.0}

    def clock():
        return ticks["t"]

    def sleep(seconds):
        ticks["t"] += seconds

    allowed, _idle = check(idle_read=counting([10.0, 20.0, 30.0, 40.0]), wait_s=60.0, poll_s=20.0,
                           clock=clock, sleep=sleep, say=lambda line: None)
    waited_ok = allowed is False
    ok &= waited_ok
    rows.append(("a wait that runs out is a skip", waited_ok, "allowed=%r" % (allowed,)))
    say("P: selftest %-6s %-44s waited %.0f s and then skipped" % ("PASS" if waited_ok else "FAIL",
                                                                  "a wait that runs out is a skip", ticks["t"]))
    # The wait that succeeds: the reader reports quiet on the third poll, so the gate takes the launch.
    ticks["t"] = 0.0
    allowed, idle = check(idle_read=counting([10.0, 20.0, 200.0]), wait_s=60.0, poll_s=20.0,
                          clock=clock, sleep=sleep, say=lambda line: None)
    took_ok = allowed is True and idle == 200.0
    ok &= took_ok
    rows.append(("a wait that sees the user go quiet launches", took_ok, "allowed=%r idle=%r" % (allowed, idle)))
    say("P: selftest %-6s %-44s" % ("PASS" if took_ok else "FAIL", "a wait that sees the user go quiet launches"))

    passed = len([row for row in rows if row[1]])
    say("P: idle check selftest %s: %d of %d decisions right, threshold %.0f s"
        % ("PASS" if ok else "FAIL", passed, len(rows), MIN_IDLE_S))
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refuse to open a window while the user is at the computer.")
    parser.add_argument("--min-idle", type=float, default=MIN_IDLE_S,
                        help="seconds of no input required (default %.0f)" % MIN_IDLE_S)
    parser.add_argument("--wait", type=float, default=0.0, dest="wait_s",
                        help="poll this many seconds for the user to go quiet, then skip (default 0: skip at once)")
    parser.add_argument("--force", action="store_true", help="run anyway: the human at the keyboard says so")
    parser.add_argument("--selftest", action="store_true", help="run the decision table and open nothing")
    parser.add_argument("--json", action="store_true", help="print one json line instead of the P: lines")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    idle = idle_seconds()
    if args.json:
        lines = []
        allowed, idle = verdict(min_idle=args.min_idle, wait_s=args.wait_s, force=args.force,
                                say=lines.append)
        print(json.dumps({"allowed": bool(allowed), "idle_seconds": idle, "min_idle_seconds": args.min_idle,
                          "wait_seconds": args.wait_s, "force": bool(args.force), "platform": sys.platform,
                          "lines": lines}, sort_keys=True))
        return 0 if allowed else EXIT_REFUSED

    allowed, _idle = verdict(min_idle=args.min_idle, wait_s=args.wait_s, force=args.force)
    return 0 if allowed else EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
