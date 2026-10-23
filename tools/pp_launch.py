#!/usr/bin/env python3
"""pp_launch.py: the one place an automatic launch of the game is allowed to start from.

Card CAPTURE-QUIET, Nayil 2026-10-22. Three rules, and every capture helper goes through this file so no lane has to
remember them:

  1. QUIET BY DEFAULT. The game is started with PP_MUTE=1 in its environment, which makes pp_app_boot take the master
     audio gain to 0 before the first cue (game\\scripts\\pp_app\\pp_app.gml, pp_app_mute_from_env). A capture that has
     to prove a sound passes sound=True (the harness's --sound flag) and PP_MUTE is then removed, not set to 0, so an
     inherited mute in the parent environment cannot leak into an audio proof and silence it.
  2. NO WINDOW WHILE HE IS AT THE PC. game_env() and Policy.gate() run the idle gate in tools\\idle_check.py first:
     nothing opens unless there has been no keyboard or mouse input for three minutes, and a refused launch returns
     idle_check.EXIT_REFUSED with a P: line saying so, so the next run tries again.
  3. OFF THE PRIMARY SCREEN. Policy.place() moves the window onto a monitor other than the primary one when the run is
     not --show, so the window is not in his face on the screen he is working on. A single monitor host gets the
     honest answer instead of a pretend move.

Why this is a module and not a paragraph in each tool: six launch sites in tools\\capture_title.py, one in
play_demo.py and one in each of the probe tools all start the same executable, and the rule only holds if every one of
them sets the same environment. tests\\test_capture_quiet.py reads those files and fails when a launch site drifts.

Usage inside a tool:
    import pp_launch
    policy = pp_launch.Policy(show=args.show, sound=args.sound, wait_s=args.idle_wait, force=args.force)
    if not policy.gate("title capture"):
        return pp_launch.EXIT_REFUSED
    ...
    subprocess.Popen([exe, "-game", win], env=policy.env())
    policy.place(hwnd)
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idle_check  # noqa: E402  the gate itself, one implementation for every lane

# The variable the game reads. It is also a macro in game\\scripts\\pp_config\\pp_config.gml, because the project check
# refuses a bare PP_ name in GML; the literal here is the other half of that pair.
MUTE_VAR = "PP_MUTE"
EXIT_REFUSED = idle_check.EXIT_REFUSED
MIN_IDLE_S = idle_check.MIN_IDLE_S

SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SM_CXSCREEN, SM_CYSCREEN = 0, 1
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79


def game_env(sound: bool = False, base=None, extra=None) -> dict:
    """The environment a game launch runs with: muted unless this run is an audio proof.

    `base` defaults to this process's own environment, so a caller that already builds a child environment (the ship
    and scroll captures set their own PP_ capture flags) keeps doing that and only passes it here.
    """
    env = dict(os.environ if base is None else base)
    if sound:
        # Removed, not zeroed: an audio proof must not inherit a mute from whoever launched it.
        env.pop(MUTE_VAR, None)
    else:
        env[MUTE_VAR] = "1"
    if extra:
        env.update(extra)
    return env


def check_idle(label: str = "launch", wait_s: float = 0.0, min_idle: float = MIN_IDLE_S, force: bool = False,
               say=print):
    """Run the gate for one launch. Returns (allowed, idle_seconds)."""
    allowed, idle = idle_check.verdict(min_idle=min_idle, wait_s=wait_s, force=force, say=say)
    idle_check.log("%s: %s" % (label, "allowed" if allowed else "refused"))
    return allowed, idle


def primary_rect():
    """The primary monitor as (x, y, w, h). The primary always starts at 0,0 in Windows' own coordinates."""
    user32 = ctypes.windll.user32
    return (0, 0, user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN))


def virtual_rect():
    """The bounding box of every monitor, as (x, y, w, h)."""
    user32 = ctypes.windll.user32
    return (user32.GetSystemMetrics(SM_XVIRTUALSCREEN), user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CXVIRTUALSCREEN), user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))


def quiet_target(size, primary, virtual):
    """A top left corner that sits on a monitor other than the primary one, or None when there is only one monitor.

    Pure arithmetic on three rectangles, so it is decided in a test and not on the desktop: a host with one monitor has
    no second screen to move to, and the caller then says so instead of pretending the window is out of sight.
    """
    w, h = int(size[0]), int(size[1])
    px, py, pw, ph = (int(value) for value in primary)
    vx, vy, vw, vh = (int(value) for value in virtual)
    candidates = []
    if vx + vw > px + pw:                       # a monitor to the right of the primary
        candidates.append((px + pw, vy))
    if vx < px:                                  # to the left
        candidates.append((vx, vy))
    if vy + vh > py + ph:                        # below
        candidates.append((vx, py + ph))
    if vy < py:                                  # above
        candidates.append((vx, vy))
    for left, top in candidates:
        # The whole window has to sit inside the virtual desktop, and outside the primary monitor's own rectangle.
        left = max(vx, min(left, vx + vw - w))
        top = max(vy, min(top, vy + vh - h))
        inside_primary = (left + w <= px + pw) and (left >= px) and (top + h <= py + ph) and (top >= py)
        if inside_primary:
            continue
        return (left, top)
    return None


def move_window(hwnd, left, top) -> bool:
    """Move a window without resizing it and without activating it."""
    return bool(ctypes.windll.user32.SetWindowPos(int(hwnd), 0, int(left), int(top), 0, 0,
                                                  SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE))


def window_rect(hwnd):
    """The window's screen rectangle as (x, y, w, h), or None."""
    rect = wt.RECT()
    if not ctypes.windll.user32.GetWindowRect(int(hwnd), ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)


def place_window_quietly(hwnd, rect=None):
    """Put the window on a monitor other than the primary one. Returns (moved, note).

    The window is not minimised on purpose: the capture paths read the window's own pixels off the screen, and a
    minimised window has none. A second monitor is exactly the quiet version of "on screen": the pixels are there to
    be copied and nothing of it is on the screen Nayil is working on.
    """
    if sys.platform != "win32":
        return False, "not moved: this host has no window to move"
    rect = rect or window_rect(hwnd)
    if rect is None:
        return False, "not moved: the window has no rectangle"
    target = quiet_target((rect[2], rect[3]), primary_rect(), virtual_rect())
    if target is None:
        return False, ("not moved: this host has one monitor, so there is no screen off the primary one; "
                       "the idle gate is what keeps the window out of his way")
    if not move_window(hwnd, target[0], target[1]):
        return False, "not moved: SetWindowPos refused %d,%d" % target
    after = window_rect(hwnd)
    if after is None or (after[0], after[1]) != target:
        return False, "not moved: the window is at %s, not at %s" % (after, target)
    return True, ("moved off the primary screen to %d,%d, which is the second monitor" % target)


class Policy(object):
    """What one run is allowed to do: muted or sound, gated or waiting, shown or off the primary screen."""

    def __init__(self, show=False, sound=False, wait_s=0.0, min_idle=MIN_IDLE_S, force=False,
                 idle_read=None, say=print):
        self.show = bool(show)
        self.sound = bool(sound)
        self.wait_s = float(wait_s)
        self.min_idle = float(min_idle)
        self.force = bool(force)
        self.idle_read = idle_read
        self.say = say

    def gate(self, label="launch"):
        """True when this run may open a window. A False answer is a skip, never a failure of the work."""
        allowed, idle = idle_check.verdict(idle_read=self.idle_read, min_idle=self.min_idle, wait_s=self.wait_s,
                                           force=self.force, say=self.say)
        idle_check.log("%s: %s (idle %s)" % (label, "allowed" if allowed else "refused",
                                             "unreadable" if idle is None else "%.0f s" % idle))
        if allowed:
            self.say("P: %s: launch allowed, the game starts with PP_MUTE=%s"
                     % (label, "cleared for an audio proof" if self.sound else "1, so nothing plays"))
        return allowed

    def env(self, extra=None, base=None):
        """The child environment for this run: muted unless --sound was given."""
        return game_env(sound=self.sound, base=base, extra=extra)

    def place(self, hwnd, rect=None):
        """Move the window off the primary screen unless --show was given. Returns (moved, note)."""
        if self.show:
            note = "left where it is: --show was given"
            self.say("P: window: %s" % note)
            return False, note
        moved, note = place_window_quietly(hwnd, rect)
        self.say("P: window: %s" % note)
        return moved, note


def add_launch_flags(parser, default_wait=0.0):
    """The three flags every launching tool takes, spelled once so the tools cannot disagree about them."""
    parser.add_argument("--sound", action="store_true",
                        help="audio proof: start the game with PP_MUTE cleared so its sound is real "
                             "(default: PP_MUTE=1, nothing plays)")
    parser.add_argument("--show", action="store_true",
                        help="leave the window where it is (default: move it off the primary screen)")
    parser.add_argument("--idle-wait", type=float, default=default_wait, dest="idle_wait",
                        help="poll this many seconds for the user to go quiet before skipping (default %g: skip at "
                             "once when there has been input in the last %.0f s)" % (default_wait, MIN_IDLE_S))
    parser.add_argument("--force", action="store_true",
                        help="run even though input was recent: only a person at the keyboard should use this")
    return parser


def policy_from_args(args) -> Policy:
    """Build the policy from the flags add_launch_flags put on a parser."""
    return Policy(show=getattr(args, "show", False), sound=getattr(args, "sound", False),
                  wait_s=getattr(args, "idle_wait", 0.0), force=getattr(args, "force", False))


if __name__ == "__main__":
    # Run as a script it is only a report: what the launch policy would decide right now, and where the window would go.
    arguments = sys.argv[1:]
    if "--selftest" in arguments:
        sys.exit(idle_check.selftest())
    idle = idle_check.idle_seconds()
    print("P: idle now %s" % ("cannot be read on this host" if idle is None
                              else "%.0f s since the last keyboard or mouse input" % idle))
    print("P: three minutes required, so a launch is %s"
          % ("allowed" if idle is not None and idle >= MIN_IDLE_S else "refused"))
    if sys.platform == "win32":
        target = quiet_target((784, 759), primary_rect(), virtual_rect())
        print("P: a 784x759 window would be placed at %s" % (target,))
    sys.exit(0 if idle is not None and idle >= MIN_IDLE_S else EXIT_REFUSED)
