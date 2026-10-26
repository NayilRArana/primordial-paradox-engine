#!/usr/bin/env python3
"""capture_battle_slice.py: one real frame of the running game in the tutorial fight, taken without any key press.

Why this file exists (card t_4275136f). tools/capture_first_fight.py is the project's evidence tool for the first
fight, and it drives the fight with 45 timed key presses from the title screen. Measured on this tree 2026-10-25: the
drive no longer reaches the fight (the title now runs an 840 frame pan and a 14 line crawl, so the presses that are
meant to skip the crawl land inside it and the game types text to the end of the recording), and nothing in this card
is allowed to guess at new timings by opening window after window. The game's own demo walk is the cheaper door: with
PP_SLICE set, pp_app walks data/slice.json, whose "fight" step is encounter tutorial_sailors on the deck, and it walks
there on its own with no input at all. This tool watches the walk's log for that step, copies one frame of the game's
3x viewport, and writes it out at 1x.

What it does NOT do: it does not press a key, it does not touch the build, and it does not claim the frame is a
player's run. PP_SLICE is a developer route and the frame is evidence that the BUILD draws the strip, the enemy and
the party at the numbers data/ui_layouts.json gives, which is this card's question. The player's path is
tools/capture_first_fight.py's job and its own card.

Rules it obeys, from tools/pp_launch.py (ruling D9): muted, no window while the machine is not idle, off the primary
screen, one launch and one exit line.

Usage:
    python tools\\art\\capture_battle_slice.py
    python tools\\art\\capture_battle_slice.py --wait 300 --out output\\battle_slice_deck.png
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

from PIL import Image

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import capture_title as cap  # noqa: E402  the window, screen copy and viewport primitives
import pp_launch  # noqa: E402  the launch policy every automatic launch goes through
import play_demo  # noqa: E402  the same pre-roll viewport search the recorder uses

SCALE = 3
WINDOW_TIMEOUT_S = 40.0
SETTLE_S = 1.5
FIGHT_SETTLE_S = 4.0
SLICE_LOG = "pp_slice_run.log"


def build():
    found = cap.newest_build()
    if found is None:
        raise SystemExit("no built game under %s: build it first" % cap.GAME_OUTPUT_DIR)
    return found


def slice_log_path(exe_path: str) -> str:
    """The walk's log sits beside the runner, because the game's working directory is its own folder."""
    return os.path.join(os.path.dirname(os.path.abspath(exe_path)), SLICE_LOG)


def wait_for_fight(log_path: str, timeout_s: float) -> str:
    """Wait for the walk to enter the fight step, and return the line it said.

    The line is pp_slice_walk_step's own: "PP slice: step 6 of 8 fight (the first fight): ...". Matching on " fight ("
    keeps the wait on the walk rather than on the word fight appearing anywhere in a log.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if " fight (" in line:
                        return line.strip()
        time.sleep(0.5)
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Capture one frame of the running game in the tutorial fight.")
    parser.add_argument("--wait", type=float, default=300.0, help="seconds to wait for the walk to reach the fight")
    parser.add_argument("--out", default=os.path.join(ROOT, "output", "battle_slice_deck_night.png"))
    pp_launch.add_launch_flags(parser, default_wait=0.0)
    args = parser.parse_args(argv)

    policy = pp_launch.policy_from_args(args)
    policy.min_idle = 120.0  # ruling D9's gate: two quiet minutes before a window opens
    if not policy.gate("battle slice capture"):
        return pp_launch.EXIT_REFUSED

    exe_path, win_path = build()
    env = policy.env()
    env["PP_SLICE"] = "1"
    log_path = os.path.join(ROOT, "build", "battle_slice_game.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    game_log = open(log_path, "wb")
    print("P: launching %s -game %s with PP_SLICE=1" % (exe_path, win_path))
    process = subprocess.Popen([exe_path, "-game", win_path], cwd=os.path.dirname(exe_path),
                               stdin=subprocess.DEVNULL, stdout=game_log, stderr=subprocess.STDOUT, env=env)
    cap.start_watchdog(process, args.wait + 180.0)
    hwnd = None
    try:
        match = cap.find_window(
            lambda hwnd, pid, title, visible, rect: visible and pid == process.pid
            and cap.GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=WINDOW_TIMEOUT_S)
        if match is None:
            print("P: the game window did not appear within %.0f s" % WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        policy.place(hwnd, cap.get_window_rect(hwnd))
        time.sleep(SETTLE_S)

        walk_log = slice_log_path(exe_path)
        if os.path.isfile(walk_log):
            os.remove(walk_log)
        line = wait_for_fight(walk_log, args.wait)
        if not line:
            print("P: the walk never reached the fight step within %.0f s, so no frame was taken" % args.wait)
            return 1
        print("P: walk line: %s" % line)

        # The intro phase flashes the frame; four seconds is past PP_INTRO_FLASH_STEPS at 60 steps a second and lands
        # the capture in the menu phase, where the field, both actors and the command band are all up.
        time.sleep(FIGHT_SETTLE_S)
        rect, box, score, note = play_demo.pre_roll_viewport(hwnd, os.path.join(ROOT, "build", "battle_slice_preroll.png"))
        if box is None:
            print("P: the frame is not the game's viewport: %s" % note)
            return 1
        print("P: viewport %s in the window, score %.3f" % (str(box), score))

        three_x = os.path.join(ROOT, "build", "battle_slice_3x.png")
        ok, how = cap.capture_with_pil(box, three_x)
        if not ok:
            print("P: the screen copy failed: %s" % how)
            return 1
        image = Image.open(three_x).convert("RGB")
        if image.size != (256 * SCALE, 240 * SCALE):
            print("P: the copy is %dx%d, not the 768x720 viewport, so it is not used" % image.size)
            return 1
        frame = image.resize((256, 240), Image.NEAREST)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        frame.save(args.out)
        print("P: wrote %s (%dx%d, %d colours)" % (
            args.out, frame.width, frame.height,
            len(frame.convert("RGB").getcolors(maxcolors=1 << 16))))
        return 0
    finally:
        if hwnd is not None:
            cap.close_window(hwnd)
        deadline = time.time() + 6.0
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("P: the game did not close on request, terminating it")
            cap.kill_tree(process)
        else:
            print("P: the game closed on request (exit code %s)" % process.returncode)
        game_log.close()


if __name__ == "__main__":
    sys.exit(main())
