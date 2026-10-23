#!/usr/bin/env python3
"""probe_states.py: launch the built game, capture frames at several times, and keep the stdout.

This is the measurement for the first-screen card: what the game actually shows, in order, and what it
prints to the run log. Everything is a capture, nothing is inferred.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inspect_frame as inf  # noqa: E402
import pp_launch  # noqa: E402  the launch policy: PP_MUTE=1, the idle gate, and the quiet window (card CAPTURE-QUIET)

OUT = os.path.join(inf.OUTPUT_DIR, "probe")


def main():
    os.makedirs(OUT, exist_ok=True)
    # Card CAPTURE-QUIET: no window while the user is at the PC, and PP_MUTE=1 so nothing plays.
    if not pp_launch.Policy().gate("state probe"):
        return pp_launch.EXIT_REFUSED
    build = inf.newest_build()
    if build is None:
        print("no built game")
        return 1
    exe_path, win_path = build
    print("launching %s" % exe_path)
    # The stdout of the game goes to a file, never to a pipe: a full pipe blocks the runtime, and the run then
    # shows a black window that looks like a rendering fault but is only a blocked log.
    log_path = os.path.join(OUT, "stdout.txt")
    log_handle = open(log_path, "w", encoding="utf-8", errors="replace")
    process = subprocess.Popen([exe_path, "-game", win_path], cwd=os.path.dirname(exe_path),
                               stdin=subprocess.DEVNULL, stdout=log_handle,
                               stderr=subprocess.STDOUT, env=pp_launch.game_env())
    hwnd = None
    try:
        deadline = time.time() + 20
        while time.time() < deadline and hwnd is None:
            for window in inf.enum_windows():
                if window[3] and window[1] == process.pid and inf.GAME_WINDOW_TITLE.lower() in window[2].lower():
                    hwnd = window[0]
                    break
            time.sleep(0.2)
        if hwnd is None:
            print("no window")
            return 1
        # Card CAPTURE-QUIET: off the primary screen, so the window is not in his face.
        pp_launch.place_window_quietly(hwnd)
        marks = [0.3, 0.8, 1.5, 3.0, 6.0]
        start = time.time()
        for mark in marks:
            while time.time() - start < mark:
                time.sleep(0.05)
            rect = inf.client_screen_rect(hwnd)
            path = os.path.join(OUT, "t_%04.1f.png" % mark)
            ok, note = inf.capture(rect, path)
            print("t=%.1f  window=%s  capture=%s %s" % (mark, rect, ok, note))
    finally:
        if hwnd is not None:
            inf.user32.PostMessageW(hwnd, inf.WM_CLOSE, 0, 0)
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
        log_handle.close()
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            out = fh.read()
        print("---- stdout tail ----")
        print("\n".join(out.splitlines()[-25:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
