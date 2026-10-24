#!/usr/bin/env python3
"""pp_launch.py: the one place an automatic launch of the game is allowed to start from.

Card CAPTURE-QUIET, Nayil 2026-10-22. Three rules, and every capture helper goes through this file so no lane has to
remember them:

  1. QUIET BY DEFAULT. The game is started with PP_MUTE=1 in its environment, which makes pp_app_boot take the master
     audio gain to 0 before the first cue (game\\scripts\\pp_app\\pp_app.gml, pp_app_mute_from_env). A capture that has
     to prove a sound passes sound=True (the harness's --sound flag) and PP_MUTE is then removed, not set to 0, so an
     inherited mute in the parent environment cannot leak into an audio proof and silence it.
  2. NO WINDOW WHILE HE IS AT THE PC. game_env() and Policy.gate() run the idle gate in tools\\idle_check.py first:
     nothing opens unless the machine has been quiet for two minutes (D9_IDLE_S, ruling D9 of
     knowledge\\GAMEDEV-DECISIONS-2026-10-23.md), and a refused launch returns idle_check.EXIT_REFUSED with a P: line
     saying so, so the next run tries again.
  3. OFF THE PRIMARY SCREEN. Policy.place() moves the window onto a monitor other than the primary one when the run is
     not --show, so the window is not in his face on the screen he is working on. A single monitor host gets the
     honest answer instead of a pretend move.
  4. ONE START, ONE PP: muted LINE, ONE EXIT LINE. start_game() is the only place a launcher starts the built runner:
     it sets PP_MUTE in the child environment, starts it with CREATE_NO_WINDOW so no console appears, refuses to touch
     the GameMaker IDE or Igor, and prints exactly one `PP: muted` line, and only after the game's own log carries it.
     Run.finish() closes the process and prints exactly one exit line. A capture that cannot show the muted line is not
     evidence (D9).

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
import os
import subprocess
import sys
import time

# Same guard as tools\capture_title.py, for the same reason (card PINE-HONEST, t_84fe63ff): this module must import
# on a machine with no window so the Pine suite can run the demo tools at all. Off Windows the primitives are absent
# and WINDOW_PRIMITIVES is False, which the callers read to refuse with the not-measured code.
WINDOW_PRIMITIVES = sys.platform == "win32"
if WINDOW_PRIMITIVES:
    import ctypes.wintypes as wt
else:  # the branch exists so an import cannot fail, not so the window code can run
    wt = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idle_check  # noqa: E402  the gate itself, one implementation for every lane

# The variable the game reads. It is also a macro in game\\scripts\\pp_config\\pp_config.gml, because the project check
# refuses a bare PP_ name in GML; the literal here is the other half of that pair.
MUTE_VAR = "PP_MUTE"
EXIT_REFUSED = idle_check.EXIT_REFUSED
MIN_IDLE_S = idle_check.MIN_IDLE_S
# Ruling D9 of knowledge\GAMEDEV-DECISIONS-2026-10-23.md is two idle minutes for an automatic launch, where the gate
# module's own default is three. Two numbers, each pinned: idle_check.MIN_IDLE_S is what a direct caller of the gate
# gets and what knowledge\ART-BIBLE.md states, and D9_IDLE_S is what a launcher gets through Policy. The card that owns
# this file (CAPTURE-QUIET-IMPL) has the two minute number in its body and cites D9, so the launchers follow D9.
D9_IDLE_S = 120.0
# The window creation flag that keeps a console from appearing for the child. The built runner is a GUI exe, but it is
# started from a Python console here and a run that pops a black window on his desktop is exactly what D9 forbids.
NO_WINDOW = 0x08000000
# The GameMaker IDE and its build tool. A launcher must never start one of these: the IDE opens a window, asks for a
# login, and a capture that runs through it is not reproducible. The guard refuses them by name.
IDE_IMAGES = ("gamemaker.exe", "gamemakerstudio.exe", "igor.exe")
DEFAULT_MUTE_NEEDLE = "PP: muted"

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


def wait_for_log_line(path, needle: str, timeout_s: float, poll_s: float = 0.25) -> bool:
    """True when the file at path carries a line with needle within timeout_s.

    The game writes its own lines to the file this run opened, so a line in it is the game's account of itself and not
    this process's claim about it. A missing file is not an error: the game may still be creating it.
    """
    deadline = time.time() + float(timeout_s)
    while True:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if needle in line:
                        return True
        except OSError:  # gate: ok the file is being written or not there yet; the loop retries until it times out
            pass
        if time.time() >= deadline:
            return False
        time.sleep(poll_s)


def kill_tree(process, grace_s: float = 5.0) -> bool:
    """Close the process and everything it started. True when nothing of it is left running.

    GameMaker's runner loads its data in the same process, but a capture also starts a window thread and the runner can
    answer a close message slowly, so the graceful close is given grace_s and the tree is then forced.
    """
    if process is None:
        return True
    if process.poll() is not None:
        return True
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=30)
        else:
            process.terminate()
    except Exception:  # gate: ok the forced close is best effort and the poll below is the answer that counts
        pass
    deadline = time.time() + grace_s
    while time.time() < deadline:
        if process.poll() is not None:
            return True
        time.sleep(0.2)
    try:
        process.kill()
    except Exception:  # gate: ok already gone, which is what this function is asking for
        pass
    deadline = time.time() + grace_s
    while time.time() < deadline:
        if process.poll() is not None:
            return True
        time.sleep(0.2)
    return process.poll() is not None


class LaunchRefused(RuntimeError):
    """A launch the helper will not make: an IDE image, or no log to prove the mute in."""


class Run(object):
    """One launched game: the process, its own log, the PP: muted line and the one exit line.

    Every launcher gets its evidence from here, so a capture tool cannot print the muted line without the game having
    written it into the log this run opened (ruling D9: a capture that cannot show that line is not evidence).
    """

    def __init__(self, process, log_path=None, label="game", say=print):
        self.process = process
        self.log_path = log_path
        self.label = label
        self.say = say
        self.muted_said = False
        self.exit_said = False

    def pid(self):
        return getattr(self.process, "pid", None)

    def mute_evidence(self, timeout_s: float = 20.0) -> bool:
        """Print the one PP: muted line, but only when the game's own log carries it. True once it has been printed."""
        if self.muted_said:
            return True
        if not self.log_path:
            self.say("FAIL: %s: no log was named, so the mute cannot be shown and this run is not evidence"
                     % self.label)
            return False
        if not wait_for_log_line(self.log_path, DEFAULT_MUTE_NEEDLE, timeout_s):
            self.say("FAIL: %s: the game's log never carried the PP: muted line within %.0f s (%s), so this run is "
                     "not evidence" % (self.label, timeout_s, self.log_path))
            return False
        self.muted_said = True
        self.say("PP: muted, PP_MUTE=1 in the child environment and the game's own log says so (%s)" % self.log_path)
        return True

    def finish(self, note: str = "") -> int:
        """Close the game and print the one exit line. Returns 0 when nothing of the process is left running."""
        closed = kill_tree(self.process)
        code = self.process.poll() if self.process is not None else None
        if not self.exit_said:
            self.exit_said = True
            self.say("P: exit: %s%s, the game process is %s (pid %s, code %s)"
                     % (self.label, (", " + note) if note else "",
                        "closed" if closed else "STILL RUNNING", self.pid(), "none" if code is None else code))
        return 0 if closed else 1

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None


def start_game(exe, win, log=None, log_path=None, policy=None, extra=None, base=None, label="game",
               wait_mute=True, mute_timeout_s=20.0, say=print):
    """Start the built game once: muted, without a console window, and with the PP: muted line.

    exe and win are the two arguments the runner was measured to take (`<game>.exe -game <data>.win`); every argument
    after that is a policy decision this module owns, not a launcher's. Raises LaunchRefused for an IDE image, because
    a launch through the IDE is not the thing any of these tools capture.
    """
    name = os.path.basename(str(exe)).lower()
    if name in IDE_IMAGES:
        say("FAIL: %s is the GameMaker IDE or its build tool, not the game; no window was opened" % name)
        raise LaunchRefused(name)
    if log is None and log_path:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        log = open(log_path, "wb")
    if log is not None and not log_path:
        # A launcher that already opened its own log handle gets the muted line too: the handle knows the path it writes
        # to, and reading the game's line back out of it is the whole point (card CAPTURE-QUIET-IMPL).
        opened = getattr(log, "name", None)
        log_path = opened if isinstance(opened, str) else None
    if log is None:
        raise LaunchRefused("no log named for %s, so the mute could not be shown" % label)
    environment = policy.env(base=base, extra=extra) if policy is not None else game_env(base=base, extra=extra)
    flags = NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen([exe, "-game", win], cwd=os.path.dirname(os.path.abspath(exe)),
                               stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                               env=environment, creationflags=flags)
    run = Run(process, log_path=log_path, label=label, say=say)
    if wait_mute:
        run.mute_evidence(mute_timeout_s)
    return run


def launch(exe, win, label="game", policy=None, log_path=None, extra=None, base=None, say=print,
           mute_timeout_s=20.0):
    """The whole rule in one call: gate, start, PP: muted line. Returns (run, exit_code); run is None when refused.

    This is the shape a one shot launcher uses. A capture that has to open a window and then drive it keeps the Run and
    calls run.finish() when it is done, so the exit line is still printed exactly once.
    """
    policy = policy if policy is not None else Policy(say=say)
    if not policy.gate(label):
        return None, EXIT_REFUSED
    run = start_game(exe, win, log_path=log_path, policy=policy, extra=extra, base=base, label=label,
                     mute_timeout_s=mute_timeout_s, say=say)
    return run, 0


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

    def __init__(self, show=False, sound=False, wait_s=0.0, min_idle=D9_IDLE_S, force=False,
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
