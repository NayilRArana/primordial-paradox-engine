#!/usr/bin/env python3
"""
capture_title.py: capture the real game window, press one Enter, capture again, then close the game.

Why this file exists: the computer-use screenshot tool returns a blank frame for some windows on this PC, so
the working method is the one recorded in Shared\\projects\\arananet\\manager\\STATE.md: find the window
rectangle with user32 GetWindowRect, then copy that rectangle off the screen with System.Drawing
CopyFromScreen. The CopyFromScreen call needs .NET, so this script calls the sibling helper
tools\\capture_rect.ps1, which does exactly that. If PowerShell is unavailable it falls back to PIL
ImageGrab, which is the same screen copy done a different way.

The launch recipe is the one Igor used for the run, recorded in build\\igor-run5.log and in DEVLOG:
    <game>.exe -game <data>.win
That argument form was measured on this PC on 2026-10-21. Two other forms were tried and both fail:
    <game>.exe <data>.win     opens a file dialog titled "Open", never starts the game
    <game>.exe                opens the same file dialog
The DEVLOG already warned that the runner opens a file dialog for its data when it is started wrong.

Usage:
    python capture_title.py             capture output\\title_run_1.png and output\\title_run_2.png
    python capture_title.py --selftest  prove the capture path on notepad, write output\\_capture_selftest.png
    python capture_title.py --video     record output\\title_run.mp4 of the running title screen and check it

Exit codes:
    0  both frames were written (or the selftest frame was written, or the video passed its checks)
    1  the game window never appeared, or the capture failed, or a video check failed
    3  the watchdog fired (the run overran)
    4  the idle gate refused to open a window: the user had input in the last three minutes (card CAPTURE-QUIET)

Quiet by default (card CAPTURE-QUIET, Nayil 2026-10-22). Every launch in this file goes through tools\pp_launch.py:
the game is started with PP_MUTE=1 so nothing plays, the idle gate in tools\idle_check.py refuses to open a window
unless the user has been quiet for three minutes, and the window is moved off the primary screen. --sound turns the
mute off for an audio proof, --show leaves the window where it is, --idle-wait polls for the user to go quiet, and
--force is the override a person at the keyboard may use on purpose.
"""

import argparse
import ctypes
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# The window primitives are Windows only. This module still has to IMPORT on a machine that has no window at all,
# because the Pine suite imports the demo tools in order to run them (card PINE-HONEST, t_84fe63ff). When the
# primitives are absent, WINDOW_PRIMITIVES is False and the callers refuse with the harness's not-measured code
# instead of reporting a capture they never made. That distinction is the whole point: a silent skip would tell the
# same lie as the original traceback, only quieter.
WINDOW_PRIMITIVES = sys.platform == "win32"
if WINDOW_PRIMITIVES:
    import ctypes.wintypes as wt
else:  # the branch exists so an import cannot fail, not so the window code can run
    wt = None

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
import pp_launch  # noqa: E402  the launch policy every capture path below goes through (card CAPTURE-QUIET)
OUTPUT_DIR = os.path.join(ROOT, "output")
BUILD_DIR = os.path.join(ROOT, "build")
GAME_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "PrimordialParadox")
GAME_WINDOW_TITLE = "Primordial Paradox"
# The window must belong to the game executable itself. Checking the window title alone is not enough on this
# desktop: another app can put a window with a similar name on top, and the screen copy would then show that app.
GAME_EXE_NAME = "PrimordialParadox.exe"
CAPTURE_HELPER = os.path.join(TOOLS_DIR, "capture_rect.ps1")
# A real frame of the game has more than one flat colour in it. A blank rectangle, a covered window or a desktop
# with one wallpaper colour gives fewer than this, so the frame is rejected instead of being written out.
MIN_DISTINCT_COLOURS = 6
# The screen copy is taken after the window has been brought forward and the desktop has had a moment to
# repaint, so the frame shows the game and not the window that was on top of it.
FOREGROUND_SETTLE_S = 0.5

# Hard limits. The harness must never hang: a watchdog kills the game and exits if a step overruns.
GAME_WINDOW_TIMEOUT_S = 20.0
GAME_SETTLE_S = 3.0
AFTER_ENTER_S = 1.5
# The gap between the two frames of the --scroll run: half a second is the card's number, and at 126 bpm that is
# just over one beat, so the frames differ by about one lane dash of road.
SCROLL_GAP_S = 0.5
CLOSE_GRACE_S = 5.0
SELFTEST_WINDOW_TIMEOUT_S = 20.0
WATCHDOG_S = 120.0

# ---------------------------------------------------------------------------------------------------------------------
# Video capture settings

VIDEO_OUT = os.path.join(OUTPUT_DIR, "title_run.mp4")
VIDEO_PREVIEW = os.path.join(OUTPUT_DIR, "title_video_preview_3x.png")
# The true 3x of the captured title viewport: 768x720 of the game's own pixels, cut from title_run_1 by
# record_viewport(). A file whose name says 3x reference has to be exactly that, or the name is a claim.
REFERENCE_3X_NAME = "title_run_reference_3x.png"
VIDEO_FPS = 30
VIDEO_FIRST_S = 10.0
VIDEO_SECOND_S = 3.0
VIDEO_TOTAL_S = VIDEO_FIRST_S + VIDEO_SECOND_S
# The video check allows this much slack on the duration, because ffmpeg rounds to the frame and the
# container duration is only exact to a few milliseconds.
VIDEO_DURATION_SLACK_S = 1.0
# The game window is 256x240 inside a scaled window. The preview sheet shows the frames at 3x of that
# native size, which is the convention the other previews in this project use.
VIDEO_PREVIEW_FRAME = (256, 240)
VIDEO_PREVIEW_SCALE = 3
# The timestamps sampled out of the recording for the preview sheet and the frame difference check.
VIDEO_SAMPLE_TIMES = (0.5, 4.0, 8.0, 11.0, 12.5)
# Two frames count as different when this share of their pixels differ. A still frame scores 0.0 and a
# moving scene scores far above this.
VIDEO_FRAME_DIFF_RATIO = 0.001
# The frames of a real game screen carry the title screen's own colours. Those colours are read from the
# newest title reference frame on disk instead of being hardcoded, because a hardcoded list goes stale the
# moment the art lane ships new layers: the 2026-10-21 night rebuild turned the old (8,20,32) sky into the
# NES blues, and the old list then failed a recording that showed the title perfectly. A recording of a
# foreign window scores near zero against the same list, which is what the check is for.
VIDEO_GAME_REFERENCE_FILES = (
    os.path.join(OUTPUT_DIR, "nes_title_frame.png"),
    os.path.join(OUTPUT_DIR, "title_run_1.png"),
)
# Used only when no reference frame can be read at all.
VIDEO_GAME_ANCHOR_FALLBACK = ((0, 120, 248), (0, 104, 0), (0, 88, 248), (0, 88, 0))
VIDEO_GAME_ANCHOR_COUNT = 6
VIDEO_GAME_ANCHOR_TOLERANCE = 12
# A colour becomes an anchor only when its channels differ by this much, which keeps the black, white and
# grey of window furniture out and keeps the title's sky, field and teal in.
VIDEO_GAME_ANCHOR_SPREAD = 24
# The share of a frame that must carry those colours. Measured on 2026-10-21: a recording of a covering
# claude.exe window scored 0.0013, and a recording of the title screen scored about 0.30, so 0.05 sits
# clear of both.
VIDEO_GAME_ANCHOR_SHARE = 0.05

# user32 and kernel32 through ctypes: no extra packages needed for the window side. Guarded with the import above,
# because ctypes.windll and ctypes.WINFUNCTYPE do not exist off Windows and touching them at module level is what
# made every Pine run abort on import rather than report anything.
if WINDOW_PRIMITIVES:
    user32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:  # gate: ok DPI awareness is best effort: it may fail on a headless session and the capture still works.
            pass

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
else:
    user32 = None
    EnumWindowsProc = None

WM_CLOSE = 0x0010
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_RIGHT = 0x27
VK_Z = 0x5A
# The ship room capture (card ASSEMBLE): the wait covers NEW GAME's 240 step drive (4 s at 60 steps) and the fade,
# the walk is the card's eight Right presses, and the minimum difference rejects two copies of one still frame.
SHIP_DRIVE_WAIT_S = 40.0
# The line pp_title prints when the crawl ends and pp_save_new_game starts the run. The capture waits for it instead
# of trusting a stopwatch, and SHIP_ROOM_SETTLE_S then covers pp_app's 12 step fade and the first drawn frames.
SHIP_RUN_MARKER = "starting the run in"
SHIP_ROOM_SETTLE_S = 1.5
# The title's own line when NEW GAME is chosen. The capture reads it to know the opening shot and the prompt are
# behind it, so it presses Enter until it appears rather than assuming one press is enough.
TITLE_INTRO_MARKER = "PP title: intro started"
TITLE_INTRO_PRESS_CAP = 5
TITLE_PRESS_GAP_S = 0.9
SHIP_WALK_STEPS = 8
SHIP_KEY_GAP_S = 0.18
SHIP_AFTER_WALK_S = 4.0
SHIP_MIN_DIFF = 0.001
# The intro capture (card INTRO-1): the opening shot lasts 3 s on a first boot and any key skips it, so the first
# wait covers it either way; then Enter opens the menu and Enter again chooses NEW GAME. The four timestamps are the
# card's own, measured from the second Enter: mid pan, pan landed and the world fading, the stars, the crawl.
INTRO_OPEN_WAIT_S = 0.8
INTRO_MENU_WAIT_S = 1.2
INTRO_LEAD_S = 0.15
INTRO_TIMES = (1.0, 4.0, 8.0, 14.0)
INTRO_MIN_DIFF = 0.001
INTRO_START_TIMEOUT_S = 12.0
INTRO_NUDGE_S = 4.0
# The nes check on a grabbed frame (card INTRO-1). A window copy is only a frame of the game when it carries the
# game's own 3x viewport, and the only honest test of that is the NES palette test: the box inside the capture whose
# pixels are all legal 2C02 colours, found by the same search record_viewport and nes_composite_check.py --crop auto
# run. Measured on this PC: a real window capture of the title scores 0.986 (the rest is desktop scaling blend, see
# DEVLOG), and a copy of a terminal or of the desktop scores 0.000. The gate sits between the two.
INTRO_VIEWPORT_MIN_SCORE = 0.90
# A grab that fails the nes check is retried after the window is raised again: the first pass's frames were the
# terminal because SetForegroundWindow was refused, so the raise is retried rather than trusted once.
INTRO_GRAB_ATTEMPTS = 3
# How long before a target time the copy is started, so the BitBlt lands on the target and not a PowerShell spawn
# after it. It is replaced by the measured cost of the first copy as the run goes on.
INTRO_COPY_LEAD_S = 0.25
# The band the title logo occupies inside the window screenshot: the viewport sits at (8, 31) at 3x, and the
# logo fills most of the top third of the 256x240 frame. Fewer than this many grey pixels there means the intro
# has begun, because the intro shot never draws the logo.
LOGO_BAND = (68, 121, 716, 331)
LOGO_GONE_PIXELS = 3000
SW_RESTORE = 9
KEYEVENTF_KEYUP = 0x0002
# The keys whose scancode is only correct when the extended flag is set. Sent without it they arrive as their
# numpad twins, which is why the Down presses in the first keys run moved nothing while Enter worked.
KEYEVENTF_EXTENDEDKEY = 0x0001
EXTENDED_KEYS = frozenset((0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2C, 0x2D, 0x2E,
                           0x5B, 0x5C, 0x6F, 0x90))
# Topmost and not topmost, for the window handles that SetWindowPos takes.
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

# What this process may do with a window and with sound (card CAPTURE-QUIET, Nayil 2026-10-22). main() replaces this
# from the flags, so one place decides for all six capture paths below: the game starts with PP_MUTE=1 (nothing plays),
# no window opens unless the idle gate says the user has been quiet for three minutes, and the window is moved off the
# primary screen unless --show was given.
LAUNCH = pp_launch.Policy()
# The exit code a run returns when the idle gate refused to open a window. It is not a failure of the work, so it is
# not 1: a card that is retried later reads a 1 as a bug and a 4 as "he was at the PC".
IDLE_REFUSED = pp_launch.EXIT_REFUSED


# ---------------------------------------------------------------------------------------------------------------------
# Window helpers

def enum_windows():
    """Every top level window on the desktop as (hwnd, pid, title, visible, rect)."""
    found = []

    def callback(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        rect = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append(
            (
                hwnd,
                pid.value,
                buffer.value,
                bool(user32.IsWindowVisible(hwnd)),
                (rect.left, rect.top, rect.right, rect.bottom),
            )
        )
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return found


def find_window(predicate, timeout_s, poll_s=0.25):
    """Wait for a window matching predicate(hwnd, pid, title, visible, rect). Returns the match or None."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        for window in enum_windows():
            if predicate(*window):
                return window
        time.sleep(poll_s)
    return None


def get_window_rect(hwnd):
    rect = wt.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    left, top = rect.left, rect.top
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def process_image_name(pid):
    """The image name of the process that owns a window, for example 'PrimordialParadox.exe'.

    This is the check that stops the harness capturing the wrong window. The window title alone is not proof:
    the desktop can have a dialog on top with a similar name, and a screen copy of the rectangle would show
    that dialog instead of the game.
    """
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wt.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def distinct_colours(path):
    """How many different colours the PNG holds. A blank or single colour frame gives a small number."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as image:
            return len(image.convert("RGB").getcolors(maxcolors=1 << 16) or [])
    except Exception:
        return None


def frame_is_real(path):
    """True when the captured file looks like a game frame rather than a blank or covered rectangle."""
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return False, "the capture file is missing or empty"
    colours = distinct_colours(path)
    if colours is None:
        # Pillow is not available, so the check cannot run. The window and process checks already ran.
        return True, "colour check skipped, Pillow is not installed"
    if colours < MIN_DISTINCT_COLOURS:
        return False, "the frame has only %d distinct colours, so it is blank or covered" % colours
    return True, "%d distinct colours" % colours


def discard(path):
    """Remove a rejected frame, so a failed run leaves no picture behind that looks like a good one."""
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:  # gate: ok Best-effort cleanup of a stale temp file: the capture does not depend on it being gone.
        pass


def bring_to_front(hwnd):
    """Put the window on top and in the foreground, briefly, so a screen copy shows the window itself.

    Windows refuses SetForegroundWindow from a background process, so the input queues of the foreground
    thread and the target thread are attached first. That is the standard way to do it without a click.
    The previous foreground window is given the focus back at the end, so the harness does not hold the
    focus for long.
    """
    foreground = user32.GetForegroundWindow()
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    attached = False
    if foreground and target_thread and target_thread != current_thread:
        attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread, target_thread, False)
    time.sleep(0.35)
    return foreground


def restore_foreground(previous):
    """Give the focus back to whatever had it, so the harness holds it for as short a time as possible."""
    if not previous or not user32.IsWindow(previous):
        return
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    target_thread = user32.GetWindowThreadProcessId(previous, None)
    attached = False
    if target_thread and target_thread != current_thread:
        attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))
    try:
        user32.SetForegroundWindow(previous)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread, target_thread, False)


def hold_on_top(hwnd):
    """Make the window topmost, so no other window can cover it while it is recorded.

    gdigrab reads the screen, so anything that comes to the front during the recording ends up in the
    file instead of the game. On this desktop another agent's terminal came to the front halfway through
    the first recording, and the last three seconds of that file show that terminal and not the game.
    """
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    time.sleep(0.2)


def release_on_top(hwnd):
    """Give the topmost flag back, so the game window behaves like any other window afterwards."""
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def window_at_point(x, y):
    """The top level window that owns the pixel at x, y, as (hwnd, image, title).

    SetWindowPos with HWND_TOPMOST is not a promise. Another always on top window can hold the band above
    the game, and Windows keeps giving the foreground to whatever it likes, so the window can end up fully
    covered while this process believes it is on top. Asking Windows which window owns the pixels is the
    only answer that matches what gdigrab will record.
    """
    point = wt.POINT(x, y)
    child = user32.WindowFromPoint(point)
    if not child:
        return None, "", ""
    # The game draws into a child render window, so walk up to the top level window it belongs to.
    GA_ROOT = 2
    top = user32.GetAncestor(child, GA_ROOT) or child
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(top, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(top)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(top, buffer, length + 1)
    try:
        image = process_image_name(pid.value)
    except Exception:  # gate: ok A window that exits mid query has no image name, the hwnd check still decides.
        image = ""
    return top, image, buffer.value


COVERAGE_SAMPLES = ((0.5, 0.5), (0.08, 0.08), (0.92, 0.92), (0.5, 0.06), (0.5, 0.94))


def cover_report(hwnd, rect):
    """Which sampled points of rect the game owns, and what covers the rest.

    Returns (covered, owners) where covered is a list of (x, y, image, title) for the points that belong to
    another window, and owners is every distinct (hwnd, image, title) seen inside the rectangle.
    """
    left, top, width, height = rect
    covered = []
    owners = []
    for fx, fy in COVERAGE_SAMPLES:
        x = int(left + width * fx)
        y = int(top + height * fy)
        owner, image, title = window_at_point(x, y)
        if owner != hwnd:
            covered.append((x, y, image, title))
        row = (owner, image, title)
        if row not in owners:
            owners.append(row)
    return covered, owners


def move_window(hwnd, left, top):
    """Move the window without changing its size, so the game stays at its own resolution."""
    SWP_NOZORDER = 0x0004
    return bool(user32.SetWindowPos(hwnd, 0, int(left), int(top), 0, 0,
                                    SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOZORDER))


def virtual_screen():
    """The bounding box of every monitor, so a placement off the primary monitor is still on screen."""
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
    return (user32.GetSystemMetrics(SM_XVIRTUALSCREEN), user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CXVIRTUALSCREEN), user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))


def ensure_game_visible(hwnd, rect, attempts=None):
    """Make sure no other window covers the game rectangle, moving the game if that is what it takes.

    Returns (rect, note) with the rectangle that is clear, or (None, note) when every placement tried stays
    covered. A covered rectangle is never recorded: the file would show the covering window and would still
    look like a valid 13 s video.
    """
    left, top, width, height = rect
    covered, owners = cover_report(hwnd, rect)
    if not covered:
        return rect, "clear: every sampled point of the rectangle belongs to the game window"
    described = ", ".join(sorted({"%s %r" % (image or "?", title) for _hwnd, image, title in owners
                                 if _hwnd != hwnd}))
    covered, _owners = cover_report(hwnd, rect)
    if not covered:
        return rect, "clear after a second check"
    note = "the rectangle is covered by %s, looking for a clear place to move the game" % (described or "another window")

    if attempts is None:
        vx, vy, vw, vh = virtual_screen()
        attempts = []
        steps_x = 4
        steps_y = 2
        for row in range(steps_y + 1):
            for column in range(steps_x + 1):
                x = vx + int((vw - width) * column / float(steps_x))
                y = vy + int((vh - height) * row / float(steps_y))
                attempts.append((x, y))

    tried = []
    for x, y in attempts:
        if (x, y) == (left, top) or (x, y) in tried:
            continue
        tried.append((x, y))
        if not move_window(hwnd, x, y):
            continue
        hold_on_top(hwnd)
        bring_to_front(hwnd)
        hold_on_top(hwnd)
        time.sleep(0.4)
        candidate = get_window_rect(hwnd)
        if candidate is None:
            continue
        covered, _owners = cover_report(hwnd, candidate)
        if not covered:
            return candidate, "%s; moved the game to %d,%d where nothing covers it" % (note, candidate[0], candidate[1])
    # Put the window back where it was, so a failed run does not leave the game somewhere strange.
    move_window(hwnd, left, top)
    return None, "%s; every placement tried (%d) stayed covered" % (note, len(tried))


def game_has_focus(hwnd):
    """True when the window holding the keyboard focus is hwnd or one of its child windows.

    The game draws into a child render window, and that child is what Windows names as the foreground
    window, so comparing the foreground handle with the top level one answered "not focused" while the game
    really did hold the focus. That mistake sent the Enter through PostMessage, and a GameMaker game reads
    the key state rather than the window messages, so the press was lost: the 22:00 run of 2026-10-21 shows
    the title still on screen two and a half seconds after an Enter that was "posted".
    """
    foreground = user32.GetForegroundWindow()
    if not foreground:
        return False
    GA_ROOT = 2
    top = user32.GetAncestor(foreground, GA_ROOT) or foreground
    return top == hwnd


def send_vk_focused(vk):
    """Send one real key press while this process already holds the focus for the game.

    A posted key is read by the window procedure, not by the game's key state, so a scripted run built out of
    posted keys reads as "the player did nothing". This sends the press through the input queue, which is the
    only path GameMaker's keyboard_check_pressed sees.

    The arrow keys, Insert/Delete/Home/End/PageUp/PageDown and the right hand Ctrl/Alt are extended keys: sent
    without KEYEVENTF_EXTENDEDKEY they arrive as their numpad twins, so the Enter that was sent worked and the
    two Down presses before it did nothing (first keys run of 2026-10-22, menu never moved).
    """
    flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
    user32.keybd_event(vk, 0, flags, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, flags | KEYEVENTF_KEYUP, 0)
    return "sent"


def allow_foreground_change():
    """Ask Windows to stop refusing SetForegroundWindow to this process.

    The foreground lock times out after SPI_GETFOREGROUNDLOCKTIMEOUT by default, and a window started by a
    background process has to wait it out. Setting it to zero for the duration of the harness is the documented
    escape, and it is restored by the same call with the old value at the end of the run.
    """
    SPI_GETFOREGROUNDLOCKTIMEOUT = 0x2000
    SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
    SPIF_SENDCHANGE = 0x2
    old = ctypes.c_void_p()
    try:
        if user32.SystemParametersInfoW(SPI_GETFOREGROUNDLOCKTIMEOUT, 0, ctypes.byref(old), 0):
            user32.SystemParametersInfoW(SPI_SETFOREGROUNDLOCKTIMEOUT, 0, ctypes.c_void_p(0), SPIF_SENDCHANGE)
            return old.value
    except Exception:  # gate: ok Focus is best effort here; the caller checks the result.
        pass
    return None


def ensure_key_focus(hwnd, attempts=8, settle=0.3):
    """Take the keyboard focus for the game and keep it there. Returns (ok, note).

    Windows refuses SetForegroundWindow from a background process often enough that one ask is not enough, and
    the fallback (posting the key) silently proves nothing, which is how the first keys run of 2026-10-22
    reported "posted" four times while the menu never moved. Four routes are tried per attempt: the input queue
    attach, the foreground lock lifted, SwitchToThisWindow, and a real SetForegroundWindow after both.
    """
    allow_foreground_change()
    for attempt in range(attempts):
        bring_to_front(hwnd)
        if game_has_focus(hwnd):
            return True, "keyboard focus taken on attempt %d" % (attempt + 1)
        # An attach to the window that holds the foreground is the route Windows actually honours: the lock is
        # judged against the foreground thread, not against the target's thread, so attaching to the target
        # alone (which is what bring_to_front does) still loses the race on this desktop.
        foreground = user32.GetForegroundWindow()
        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
        attached = False
        if fg_thread and fg_thread != current_thread:
            attached = bool(user32.AttachThreadInput(current_thread, fg_thread, True))
        try:
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            try:
                user32.SwitchToThisWindow(hwnd, True)
            except Exception:  # gate: ok One route failing does not stop the others.
                pass
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(current_thread, fg_thread, False)
        if game_has_focus(hwnd):
            return True, "keyboard focus taken on attempt %d by attaching to the foreground thread" % (attempt + 1)
        time.sleep(settle)
    return False, "the game never took the keyboard focus after %d attempts" % attempts


def send_enter(hwnd, keep_foreground=False):
    """Send exactly one Enter key press to the game window. No other key is sent.

    keep_foreground leaves the game window on top instead of handing the focus back. The video capture
    needs that: the recording grabs the screen rectangle of the game, so anything else on top of it
    would end up in the file instead of the game.
    """
    previous = bring_to_front(hwnd)
    focused = game_has_focus(hwnd)
    try:
        if focused:
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
            result = "sent"
        else:
            # The window did not take focus, so a global key press would land on the wrong window. Post the
            # key to the game window instead, which is the safest thing that is left.
            user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)
            result = "posted"
    finally:
        if not keep_foreground:
            restore_foreground(previous)
    return result


def send_vk(hwnd, vk):
    """Send one key press of the given virtual key code to the game window.

    The same far/near split as send_enter: a focused window gets a real key event, an unfocused one gets the
    key posted to it, so a dud focus can never type into another application.
    """
    previous = bring_to_front(hwnd)
    focused = game_has_focus(hwnd)
    try:
        if focused:
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            result = "sent"
        else:
            user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)
            result = "posted"
    finally:
        restore_foreground(previous)
    return result


def close_window(hwnd):
    """Ask the window to close the normal way."""
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


# ---------------------------------------------------------------------------------------------------------------------
# Capture helpers

POWERSHELL_CAPTURE = r"""
param([int]$X, [int]$Y, [int]$W, [int]$H, [string]$Out)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if ($W -le 0 -or $H -le 0) { Write-Error "bad rectangle"; exit 1 }
$bitmap = New-Object System.Drawing.Bitmap($W, $H)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($W, $H)))
    $bitmap.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
Write-Output "saved"
exit 0
"""


def capture_with_powershell(rect, out_path):
    """CopyFromScreen through System.Drawing, the method that works on this PC."""
    left, top, width, height = rect
    script_path = CAPTURE_HELPER
    temp_script = None
    if not os.path.isfile(script_path):
        handle, temp_script = tempfile.mkstemp(suffix=".ps1")
        os.close(handle)
        with open(temp_script, "w", encoding="utf-8") as script_file:
            script_file.write(POWERSHELL_CAPTURE)
        script_path = temp_script
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                # The window is hidden, so the capture never puts a console on the screen and never takes
                # the focus away from the game while it is being recorded.
                "-WindowStyle",
                "Hidden",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script_path,
                "-X",
                str(left),
                "-Y",
                str(top),
                "-W",
                str(width),
                "-H",
                str(height),
                "-Out",
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            # stdin=DEVNULL on purpose: with no stdin given, CPython hands the child this process's own
            # STD_INPUT_HANDLE and duplicates it, which raises OSError [WinError 6] if that handle is
            # already invalid. The capture reads no stdin, so DEVNULL costs nothing.
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or "").strip()
    finally:
        if temp_script:
            try:
                os.remove(temp_script)
            except OSError:  # gate: ok Best-effort cleanup of a temp script: the capture result is already returned.
                pass
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 0, "powershell"


def capture_with_pil(rect, out_path):
    """Fallback: PIL grabs the same screen rectangle."""
    try:
        from PIL import ImageGrab
    except Exception as exc:
        return False, "PIL missing: %s" % exc
    left, top, width, height = rect
    try:
        image = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
        image.save(out_path)
    except Exception as exc:
        return False, "PIL failed: %s" % exc
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 0, "PIL"


def capture(rect, out_path):
    """Write the screen rectangle to out_path. Returns (ok, note)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ok, note = capture_with_powershell(rect, out_path)
    if ok:
        return True, note
    ok, fallback_note = capture_with_pil(rect, out_path)
    if ok:
        return True, fallback_note
    return False, "powershell: %s; %s" % (note, fallback_note)


def capture_window(hwnd, out_path):
    """Bring the window forward briefly, copy its rectangle, then hand the focus back."""
    previous = bring_to_front(hwnd)
    try:
        # The desktop needs a moment to repaint the window that was just raised, otherwise the copy can still
        # show whatever was on top of it a frame earlier.
        time.sleep(FOREGROUND_SETTLE_S)
        rect = get_window_rect(hwnd)
        if rect is None:
            return None, None, "the window has no rectangle, cannot capture"
        ok, note = capture(rect, out_path)
        if not ok:
            return rect, None, "capture failed: %s" % note
        return rect, out_path, note
    finally:
        restore_foreground(previous)


def png_size(path):
    """Read width and height straight out of the PNG header, so the report does not rely on a library."""
    with open(path, "rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def record_viewport(path, scale: int = 3, reference: str | None = None):
    """Write where the game viewport sits inside a window capture, and cut a true 3x reference from it.

    A window capture carries the desktop, the window's border and the DPI scaling of this PC, so the picture is
    not a frame until someone says which box inside it is the game. That box is a measurement, not a guess: the
    game's pixels are all 2C02 colours and the window furniture is not, so the box is found by asking which offset
    makes the pixels legal PPU colours, using the same search tools\\nes_composite_check.py runs. The result goes
    into a sidecar beside the PNG (`title_run_1.json`: {"viewport": [x, y, w, h], "scale": 3}), which is the crop
    the audit reads instead of searching a second time and calling the file UNMEASURED when it fails.

    `reference`, when given, is written as a true 3x of that viewport: 768x720 of the game's own pixels, not a
    scaled window screenshot. A file called a reference has to carry one.
    """
    try:
        from PIL import Image  # imported here so the other captures never pay for it

        sys.path.insert(0, TOOLS_DIR)
        import nes_composite_check as ncc
        palette = ncc.load_palette(ncc.default_palette_path(ROOT))
        with Image.open(path) as handle:
            image = handle.convert("RGBA")
        found = ncc.find_viewport(image, palette["allowed"])
    except Exception as error:  # gate: ok a capture that cannot be located is reported, never guessed at
        print("no viewport recorded for %s (%s)" % (os.path.basename(path), error))
        return None
    box = found["box"]
    sidecar = os.path.splitext(path)[0] + ".json"
    with open(sidecar, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({
            "viewport": list(box),
            "scale": scale,
            "viewport_score": found["score"],
            "source_size": [image.width, image.height],
            "reference": os.path.basename(reference) if reference else None,
            "note": "the box inside this window capture that holds %dx of the 256x240 screen, found by asking "
                    "which offset is all 2C02 colours (tools/capture_title.py record_viewport)" % scale,
        }, indent=2, sort_keys=True) + "\n")
    if reference:
        x, y, w, h = box
        image.crop((x, y, x + w, y + h)).save(reference, "PNG")
        with open(os.path.splitext(reference)[0] + ".json", "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                "viewport": [0, 0, w, h],
                "scale": scale,
                "cut_from": os.path.basename(path),
                "note": "the whole picture is the %dx viewport of the game screen, cut from a window capture" % scale,
            }, indent=2, sort_keys=True) + "\n")
        print("reference %s: %dx%d at %dx (cut from %s at %s, score %.3f)"
              % (os.path.basename(reference), w, h, scale, os.path.basename(path), [x, y, w, h], found["score"]))
    print("viewport %s: %s at %dx, score %.3f" % (os.path.basename(path), list(box), scale, found["score"]))
    return found


# ---------------------------------------------------------------------------------------------------------------------
# Launch helpers

def newest_build():
    """The newest built game under output\\PrimordialParadox: the newest .win data file and its runner.

    Returns (exe_path, win_path) or None.
    """
    if not os.path.isdir(GAME_OUTPUT_DIR):
        return None
    wins = []
    for folder, _dirs, files in os.walk(GAME_OUTPUT_DIR):
        for name in files:
            if name.lower().endswith(".win"):
                path = os.path.join(folder, name)
                wins.append((os.path.getmtime(path), path))
    if not wins:
        return None
    wins.sort()
    _mtime, win_path = wins[-1]
    folder = os.path.dirname(win_path)
    exe_path = os.path.join(folder, os.path.splitext(os.path.basename(win_path))[0] + ".exe")
    if not os.path.isfile(exe_path):
        candidates = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.lower().endswith(".exe")
        ]
        if not candidates:
            return None
        exe_path = max(candidates, key=os.path.getmtime)
    return exe_path, win_path


def kill_tree(process):
    """Make sure nothing is left running."""
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


def start_watchdog(process, seconds):
    """Kill the child and this process if the harness overruns, so a run can never hang the lane."""
    def watchdog():
        time.sleep(seconds)
        print("watchdog: the harness overran %.0f s, killing the game and exiting" % seconds, flush=True)
        kill_tree(process)
        os._exit(3)

    thread = threading.Thread(target=watchdog, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------------------------------------------------
# Video capture

FFMPEG_GLOBS = (
    r"<home>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_*\ffmpeg-*\bin\ffmpeg.exe",
    r"<home>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.*\ffmpeg-*\bin\ffmpeg.exe",
)


def find_ffmpeg():
    """The path of the installed ffmpeg, or None. ffmpeg was installed with winget, so the exe lives in
    the winget package folder. Nothing is installed here; the tool only looks for what is already there.
    """
    override = os.environ.get("PP_FFMPEG")
    if override and os.path.isfile(override):
        return override
    for pattern in FFMPEG_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    on_path = shutil.which("ffmpeg")
    return on_path


def ffprobe_path(ffmpeg_path):
    """ffprobe sits next to ffmpeg in the same bin folder."""
    folder = os.path.dirname(ffmpeg_path)
    candidate = os.path.join(folder, "ffprobe.exe")
    if os.path.isfile(candidate):
        return candidate
    return shutil.which("ffprobe")


def dshow_audio_devices(ffmpeg_path):
    """The DirectShow audio devices on this host, as (name, kind) pairs.

    System audio in an ffmpeg capture on Windows needs a loopback style device, because gdigrab itself
    has no audio input. This host reports no audio only device at all, so the recording falls back to
    video only and says so.
    """
    result = subprocess.run(
        [ffmpeg_path, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    output = (result.stderr or "") + (result.stdout or "")
    devices = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith('"'):
            continue
        name = line.split('"')[1]
        kind = "video" if "(video)" in line else ("audio" if "(audio)" in line else "unknown")
        devices.append((name, kind))
    return devices


def pick_loopback_device(devices):
    """The audio device that carries system sound, or None.

    A loopback device shows up as a Stereo Mix, a CABLE Output or a virtual audio capturer. A plain
    microphone is not one: recording it would capture the room, not the game's sound.
    """
    hints = ("stereo mix", "cable output", "virtual-audio-capturer", "loopback")
    for name, kind in devices:
        if kind == "audio" and any(hint in name.lower() for hint in hints):
            return name
    return None


def run_ffmpeg(ffmpeg_path, arguments, timeout):
    """Run ffmpeg to completion. Returns (ok, note)."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-y"] + arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False, "ffmpeg ran past %.0f s" % timeout
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "ffmpeg failed").strip()[-800:]
    return True, "ok"


def probe_duration(ffprobe, path):
    """The duration of the video in seconds, or None when it cannot be read."""
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def extract_frame(ffmpeg_path, video_path, timestamp, out_path):
    """Write one frame of the video at timestamp to out_path. Returns True on success."""
    ok, _note = run_ffmpeg(
        ffmpeg_path,
        ["-ss", "%.3f" % timestamp, "-i", video_path, "-frames:v", "1", "-f", "image2", out_path],
        timeout=90,
    )
    return ok and os.path.isfile(out_path) and os.path.getsize(out_path) > 0


def frames_differ(path_a, path_b):
    """The share of pixels that differ between two frames, from 0.0 to 1.0."""
    try:
        from PIL import Image, ImageChops
    except Exception:
        return None
    try:
        with Image.open(path_a) as first, Image.open(path_b) as second:
            left = first.convert("RGB")
            right = second.convert("RGB")
            if left.size != right.size:
                right = right.resize(left.size)
            difference = ImageChops.difference(left, right).convert("L")
            histogram = difference.histogram()
            changed = sum(histogram[1:])
            total = sum(histogram)
            if total == 0:
                return None
            return changed / float(total)
    except Exception:
        return None


def title_anchor_colours(paths=VIDEO_GAME_REFERENCE_FILES, count=VIDEO_GAME_ANCHOR_COUNT):
    """The title screen's own colours, read from the newest title reference frame on disk.

    Returns (path, colours). The path is None when no reference frame could be read, and the colours are
    then the built in fallback list, so the check still runs on a checkout that has no render of the title.
    """
    try:
        from PIL import Image
    except Exception:
        return None, VIDEO_GAME_ANCHOR_FALLBACK
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            with Image.open(path) as image:
                counts = image.convert("RGB").getcolors(maxcolors=1 << 20) or []
        except Exception:
            continue
        colours = [tuple(pixel) for _count, pixel in sorted(counts, key=lambda row: row[0], reverse=True)
                   if max(pixel) - min(pixel) >= VIDEO_GAME_ANCHOR_SPREAD]
        if len(colours) >= 2:
            return path, tuple(colours[:count])
    return None, VIDEO_GAME_ANCHOR_FALLBACK


def frame_shows_game(path, anchors):
    """The share of pixels in a frame that carry one of the title screen's colours.

    A frame that shows some other window, a terminal or a black rectangle scores near zero here, so this
    is the check that the recording shows the game and not whatever else was on the desktop.
    """
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as image:
            counts = image.convert("RGB").getcolors(maxcolors=1 << 20) or []
    except Exception:
        return None
    if not counts:
        return None
    total = sum(count for count, _pixel in counts)
    hit = 0
    for count, pixel in counts:
        for anchor in anchors:
            if abs(pixel[0] - anchor[0]) <= VIDEO_GAME_ANCHOR_TOLERANCE \
                    and abs(pixel[1] - anchor[1]) <= VIDEO_GAME_ANCHOR_TOLERANCE \
                    and abs(pixel[2] - anchor[2]) <= VIDEO_GAME_ANCHOR_TOLERANCE:
                hit += count
                break
    return hit / float(total)


def build_video_preview(frames, out_path, notes):
    """A labelled contact sheet of the sampled frames at 3x of the 256x240 native size.

    Workers cannot see images, so the sheet is the picture the manager reviews. The frames are placed
    side by side with the timestamp each one was taken at.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        return False, "PIL missing: %s" % exc
    usable = [(path, note) for path, note in zip(frames, notes) if path and os.path.isfile(path)]
    if not usable:
        return False, "no frames to put on the sheet"
    native_w, native_h = VIDEO_PREVIEW_FRAME
    cell_w = native_w * VIDEO_PREVIEW_SCALE
    cell_h = native_h * VIDEO_PREVIEW_SCALE
    # The margins are 24 px so the sheet's own size is a whole number of 3x pixels (3984x792 for five frames).
    # tools/nes_audit_all.py reads a picture whose size divides by 3 and by the 24 px cell as a 3x sheet and
    # measures it; a sheet 770 px tall is neither 3x nor 1x, and the audit can only call it unmeasured.
    margin = 24
    label_h = 24
    sheet = Image.new("RGB", (len(usable) * cell_w + margin * (len(usable) + 1),
                              cell_h + label_h + margin * 2), (18, 18, 26))
    draw = ImageDraw.Draw(sheet)
    for index, (path, note) in enumerate(usable):
        with Image.open(path) as frame:
            tile = frame.convert("RGB").resize((cell_w, cell_h), Image.Resampling.NEAREST)
        x = margin + index * (cell_w + margin)
        sheet.paste(tile, (x, margin))
        draw.text((x + 4, margin + cell_h + 6), note, fill=(232, 232, 240))
    sheet.save(out_path, optimize=True)
    return True, "%dx%d, %d bytes" % (sheet.width, sheet.height, os.path.getsize(out_path))


def run_video_capture():
    """Record the running title screen with ffmpeg, press one Enter, keep recording, then check the file.

    The game window is brought to the front and stays there for the whole recording, because gdigrab
    grabs the screen rectangle of the desktop. Nothing else opens on this desktop while it records.
    """
    if not LAUNCH.gate("title video capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build

    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("ffmpeg was not found in the winget package folder and is not on PATH")
        return 1
    ffprobe = ffprobe_path(ffmpeg_path)
    print("ffmpeg: %s" % ffmpeg_path)
    print("ffprobe: %s" % (ffprobe or "not found, the duration check will use ffmpeg"))

    devices = dshow_audio_devices(ffmpeg_path)
    loopback = pick_loopback_device(devices)
    audio_devices = [name for name, kind in devices if kind == "audio"]
    if loopback:
        print("system audio device: %s" % loopback)
    else:
        print("system audio: none, dshow reports %d audio device(s) %s, so the recording is video only"
              % (len(audio_devices), audio_devices if audio_devices else ""))

    print("launching %s -game %s" % (exe_path, win_path))
    os.makedirs(BUILD_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-video-game.log")
    game_log = open(game_log_path, "wb")
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="title video capture")
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    video_ok = False
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))

        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s, so it is not the game window"
                  % (image_name, GAME_EXE_NAME))
            return 1

        time.sleep(GAME_SETTLE_S)
        rect = get_window_rect(hwnd)
        if rect is None:
            print("the game window has no rectangle, cannot record it")
            return 1
        left, top, width, height = rect
        print("recording rectangle: %d,%d %dx%d" % (left, top, width, height))

        # The game must be the top window for the whole recording, since gdigrab reads the screen.
        previous = bring_to_front(hwnd)
        hold_on_top(hwnd)
        time.sleep(FOREGROUND_SETTLE_S)

        # Topmost is not proof of being visible: an always on top window of another program can still hold
        # the band above the game. Ask Windows who owns the pixels, and move the game if it is covered.
        rect, coverage = ensure_game_visible(hwnd, rect)
        print("coverage: %s" % coverage)
        if rect is None:
            print("FAIL another window covers the game window, so the recording would show that window; "
                  "nothing was recorded")
            return 1
        left, top, width, height = rect
        print("recording rectangle: %d,%d %dx%d" % (left, top, width, height))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if os.path.exists(VIDEO_OUT):
            os.remove(VIDEO_OUT)

        arguments = [
            "-f", "gdigrab",
            "-framerate", str(VIDEO_FPS),
            "-offset_x", str(left),
            "-offset_y", str(top),
            "-video_size", "%dx%d" % (width, height),
            "-i", "desktop",
            "-t", "%.2f" % VIDEO_TOTAL_S,
            # libx264 needs even dimensions for yuv420p, and the window height is odd.
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", "libx264",
            # ultrafast, because gdigrab hands the encoder a full desktop frame 30 times a second and the
            # slower presets cannot keep up with it on this host. A slow encode means the file ends up
            # shorter than the recording it was meant to hold.
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
        ]
        if loopback:
            arguments += ["-f", "dshow", "-i", "audio=%s" % loopback,
                          "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
        arguments.append(VIDEO_OUT)

        recorder_log_path = os.path.join(BUILD_DIR, "capture-video-ffmpeg.log")
        # The ffmpeg output goes to a file, never to a pipe. A pipe that nobody reads fills up after about
        # 64 KB, and ffmpeg then blocks on the write, which is how the first run of this harness stopped
        # recording at 9 s of a 13 s file.
        recorder_log = open(recorder_log_path, "wb")
        recorder = subprocess.Popen(
            [ffmpeg_path, "-hide_banner", "-y"] + arguments,
            stdout=recorder_log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        try:
            time.sleep(VIDEO_FIRST_S)
            print("recording %.0f s done, pressing Enter" % VIDEO_FIRST_S)
            key_result = send_enter(hwnd, keep_foreground=True)
            print("enter key %s" % key_result)
            recorder.wait(timeout=VIDEO_TOTAL_S + 60)
        except subprocess.TimeoutExpired:
            recorder.terminate()
            try:
                recorder.wait(timeout=10)
            except subprocess.TimeoutExpired:
                recorder.kill()
            print("ffmpeg did not stop on its own, it was terminated")
        try:
            recorder_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass
        # Ask Windows again who owns the pixels of the recorded rectangle, while the game is still held on
        # top. The window was topmost for the whole recording, so a foreign owner here means the recording
        # may have caught that window too, and the title colour check alone would not say so.
        covered, owners = cover_report(hwnd, rect)
        if covered:
            print("FAIL after the recording another window owns %d of the %d sampled points of the recorded "
                  "rectangle: %s"
                  % (len(covered), len(COVERAGE_SAMPLES),
                     ", ".join(sorted({"%s %r" % (image or "?", title)
                                       for _h, image, title in owners if _h != hwnd}))))
            release_on_top(hwnd)
            restore_foreground(previous)
            return 1
        print("coverage after the recording: every sampled point of the rectangle still belongs to the game")
        release_on_top(hwnd)
        if recorder.returncode not in (0, None):
            print("ffmpeg exited with code %s, its log is %s" % (recorder.returncode, recorder_log_path))
            with open(recorder_log_path, "r", encoding="utf-8", errors="replace") as handle:
                print(handle.read()[-600:])
            return 1
        restore_foreground(previous)

        # Check 1: the file exists and is not empty.
        if not os.path.isfile(VIDEO_OUT) or os.path.getsize(VIDEO_OUT) == 0:
            print("FAIL the video file is missing or empty: %s" % VIDEO_OUT)
            return 1
        size_bytes = os.path.getsize(VIDEO_OUT)
        print("video: %s, %d bytes" % (VIDEO_OUT, size_bytes))

        # Check 2: the duration is 13 s within 1 s.
        duration = probe_duration(ffprobe, VIDEO_OUT)
        if duration is None:
            print("FAIL the duration could not be read")
            return 1
        print("duration: %.3f s" % duration)
        if abs(duration - VIDEO_TOTAL_S) > VIDEO_DURATION_SLACK_S:
            print("FAIL the duration is %.3f s, which is more than %.1f s away from %.0f s"
                  % (duration, VIDEO_DURATION_SLACK_S, VIDEO_TOTAL_S))
            return 1
        print("PASS the duration is %.3f s, within %.1f s of %.0f s"
              % (duration, VIDEO_DURATION_SLACK_S, VIDEO_TOTAL_S))

        # Check 3: at least two sampled frames differ, so the scene moves.
        anchor_source, anchors = title_anchor_colours()
        if anchor_source:
            print("title colours: %d anchor(s) from %s (written %s): %s"
                  % (len(anchors), anchor_source,
                     time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(anchor_source))),
                     ", ".join("rgb(%d,%d,%d)" % anchor for anchor in anchors)))
        else:
            print("title colours: no reference frame on disk, using the built in fallback list %s"
                  % (", ".join("rgb(%d,%d,%d)" % anchor for anchor in anchors)))
        work_dir = tempfile.mkdtemp(prefix="titlevid-")
        frames = []
        notes = []
        title_shares = []
        after_shares = []
        for stamp in VIDEO_SAMPLE_TIMES:
            frame_path = os.path.join(work_dir, "frame_%.1f.png" % stamp)
            before_enter = stamp < VIDEO_FIRST_S
            label = ("t=%.1f s" % stamp) if before_enter else ("t=%.1f s after the enter" % stamp)
            if extract_frame(ffmpeg_path, VIDEO_OUT, stamp, frame_path):
                frames.append(frame_path)
                notes.append(label)
                share = frame_shows_game(frame_path, anchors)
                if share is not None:
                    (title_shares if before_enter else after_shares).append((label, share))
            else:
                frames.append(None)
                notes.append("%s (missing)" % label)

        if title_shares:
            for note, share in title_shares:
                print("game pixels in %s: %.4f" % (note, share))
            best_title_note, best_title_share = max(title_shares, key=lambda row: row[1])
            if best_title_share < VIDEO_GAME_ANCHOR_SHARE:
                print("FAIL no frame before the enter carries the game's title colours (the highest of %d "
                      "frames is %.4f at %s, against the %.3f required), so the recording shows something "
                      "else" % (len(title_shares), best_title_share, best_title_note,
                                VIDEO_GAME_ANCHOR_SHARE))
                return 1
            print("PASS the title screen is in the recording: %s carries %.4f of the game's title colours "
                  "(%.3f required). The title screen changes within the recording (PRESS START, then the menu), "
                  "so one frame is the bar and the rest are reported"
                  % (best_title_note, best_title_share, VIDEO_GAME_ANCHOR_SHARE))
        else:
            print("FAIL the game colour check could not run on any frame")
            return 1
        # The frames after the enter are a different scene on purpose, since the title's own confirm leads
        # on, so their title colour share is reported and not required.
        for note, share in after_shares:
            print("after the enter, %s: %.4f of the title colours, reported only" % (note, share))

        differences = []
        for i in range(len(frames)):
            for j in range(i + 1, len(frames)):
                if frames[i] and frames[j]:
                    ratio = frames_differ(frames[i], frames[j])
                    if ratio is not None:
                        differences.append((notes[i], notes[j], ratio))
        if not differences:
            print("FAIL the sampled frames could not be compared")
            return 1
        differences.sort(key=lambda row: row[2], reverse=True)
        best = differences[0]
        print("frame differences: %s vs %s, %.5f of the pixels differ (the largest of %d pairs)"
              % (best[0], best[1], best[2], len(differences)))
        if best[2] < VIDEO_FRAME_DIFF_RATIO:
            print("FAIL no two frames differ by more than %.5f, the scene is static"
                  % VIDEO_FRAME_DIFF_RATIO)
            return 1
        print("PASS at least two frames differ (%.5f of the pixels), so the scene moves" % best[2])

        # The preview sheet the manager reviews, since a worker cannot see the frames.
        made, note = build_video_preview(frames, VIDEO_PREVIEW, notes)
        if made:
            print("preview: %s (%s)" % (VIDEO_PREVIEW, note))
        else:
            print("preview failed: %s" % note)

        # Check 4: the game closes.
        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("the game did not close on request, terminating it")
            kill_tree(process)
            closed = "terminated"
        else:
            print("the game closed on request (exit code %s)" % process.returncode)
            closed = "closed on request"
        video_ok = True
        print(VIDEO_OUT)
        print(VIDEO_PREVIEW if made else "no preview")
        print("closed: %s" % closed)
        return 0
    finally:
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


# ---------------------------------------------------------------------------------------------------------------------
# The two jobs

def run_game_capture():
    """Launch the built game, capture the title screen, press one Enter, capture again, close the game."""
    if not LAUNCH.gate("title capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("launching %s -game %s" % (exe_path, win_path))

    os.makedirs(BUILD_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-title-game.log")
    # The game's own stdout goes to a file, never to this process's pipe. A game that writes to an
    # unread pipe blocks on the write, which is how the first attempt of this harness hung for 45 minutes.
    game_log = open(game_log_path, "wb")
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="title capture")
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))

        # The window must be the game's own window, not another app's window that happens to be on top of it.
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s, so it is not the game window"
                  % (image_name, GAME_EXE_NAME))
            return 1

        time.sleep(GAME_SETTLE_S)
        first_path = os.path.join(OUTPUT_DIR, "title_run_1.png")
        rect, written, note = capture_window(hwnd, first_path)
        if rect is None or written is None:
            print("capture 1 failed: %s" % note)
            return 1
        real, why = frame_is_real(first_path)
        if not real:
            print("capture 1 rejected: %s" % why)
            discard(first_path)
            return 1
        print("captured %s %sx%s via %s (%s)" % (first_path, rect[2], rect[3], note, why))
        # The crop the audit needs, recorded next to the picture instead of searched for later. title_run_1 is the
        # frame the title screen is judged by, and its true 3x is what the manager looks at.
        record_viewport(first_path, 3, os.path.join(OUTPUT_DIR, REFERENCE_3X_NAME))

        time.sleep(1.0)
        key_result = send_enter(hwnd)
        print("enter key %s" % key_result)
        time.sleep(AFTER_ENTER_S)
        second_path = os.path.join(OUTPUT_DIR, "title_run_2.png")
        rect, written, note = capture_window(hwnd, second_path)
        if rect is None or written is None:
            print("capture 2 failed: %s" % note)
            return 1
        real, why = frame_is_real(second_path)
        if not real:
            print("capture 2 rejected: %s" % why)
            discard(second_path)
            return 1
        print("captured %s %sx%s via %s (%s)" % (second_path, rect[2], rect[3], note, why))
        record_viewport(second_path, 3)

        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("the game did not close on request, terminating it")
            kill_tree(process)
        else:
            print("the game closed on request (exit code %s)" % process.returncode)

        print(first_path)
        print(second_path)
        return 0
    finally:
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


def log_has_line(path, needle):
    """True when the game's log already carries a line. The log is the game's own account, so the harness reads it
    instead of guessing how many key presses or seconds a screen takes."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return needle in handle.read()


def wait_for_log_line(path, needle, timeout_s):
    """Wait until the game's own log carries a line, and say whether it did.

    The run start is a fact the game prints itself, so the capture does not guess at how long the title's opening
    shots take. The marker is written by pp_title when the crawl ends and pp_save_new_game begins.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # The log does not exist on the first polls, which is a normal state: no handler to swallow, just a check.
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                if needle in handle.read():
                    return True
        time.sleep(0.2)
    return False


def self_frame_paths():
    """Where the room writes its own two frames.

    GameMaker's screen_save writes beside the game's save area, which is the folder the runtime derives from the
    project name under the user's local AppData, not the folder the runner was started in. Measured 2026-10-22:
    the files land in %LOCALAPPDATA%\\PrimordialParadox while the runner runs from output\\PrimordialParadox.
    """
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "PrimordialParadox")
    return [os.path.join(base, "pp_ship_frame.png"), os.path.join(base, "pp_ship_frame_2.png"),
            os.path.join(base, "pp_ship_frame_3.png")]


def run_ship_capture():
    """Enter the ship room from the title, walk right, and capture the room twice.

    Steps, and why each wait is the number it is:
      1. Launch the built game and wait for its own window (the same guard run_game_capture uses).
      2. Take the keyboard focus, then press Enter until the game's own "intro started" line appears, once more to
         skip the crawl, and wait for its "starting the run in rm_pp_ship" line.
      3. Copy one screen rectangle (output\\ship_window_1.png) and, more importantly, ask the game for its own frame:
         with PP_SHIP_CAPTURE set the room writes pp_ship_frame.png at draw 90 and pp_ship_frame_2.png at draw 240.
         The screen copy cannot be trusted on a DirectX11 window, and this session measured exactly that: two window
         copies 0.65 apart with the desktop's colours in them, while the room's own frame is 88% tileset steel.
      4. Press Right eight times, the card's own walk.
      5. Copy output\\ship_run_1.png and output\\ship_run_2.png from the room's own frames, then fail if they are the
         same picture, if the walker did not move, or if the game log carries "PP CRASH".

    Usage: python tools\\capture_title.py --room ship
    """
    if not LAUNCH.gate("ship room capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("launching %s -game %s" % (exe_path, win_path))

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-ship-game.log")
    game_log = open(game_log_path, "wb")
    # Card ASSEMBLE: the room writes its own two frames when this is set, so the proof is the game's frame and not a
    # copy of whatever the desktop shows inside the window rectangle. The old pair is removed first so a stale file
    # can never be mistaken for this run's.
    ship_self_paths = self_frame_paths()
    for old in ship_self_paths:
        if os.path.exists(old):
            os.remove(old)
    child_env = dict(os.environ)
    child_env["PP_SHIP_CAPTURE"] = "1"
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="ship room capture", base=child_env)
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s" % (image_name, GAME_EXE_NAME))
            return 1
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))

        time.sleep(GAME_SETTLE_S)
        # Card ASSEMBLE: the game reads key STATE, not posted window messages, so a posted Enter is a dud (the file's
        # own note of 2026-10-22 records a menu that never moved after four "posted" keys). The harness takes the
        # keyboard focus first and every key below goes through the input queue.
        focused, focus_note = ensure_key_focus(hwnd)
        print("keyboard focus: %s" % focus_note)

        def press(vk):
            return send_vk_focused(vk) if focused else send_vk(hwnd, vk)

        presses = 0
        while presses < TITLE_INTRO_PRESS_CAP:
            presses += 1
            print("title enter %d %s" % (presses, press(VK_RETURN)))
            time.sleep(TITLE_PRESS_GAP_S)
            if log_has_line(game_log_path, TITLE_INTRO_MARKER):
                print("the game reported the intro starting after %d Enters" % presses)
                break
        else:
            print("no intro marker after %d Enters" % TITLE_INTRO_PRESS_CAP)

        if log_has_line(game_log_path, TITLE_INTRO_MARKER):
            # The crawl is 540 steps of quiet before the words; one more confirm is the game's own skip to its end.
            print("title enter skip %s" % press(VK_RETURN))
            time.sleep(TITLE_PRESS_GAP_S)

        # The wait is the game's own marker line, not a guessed sleep. When the game says the run has started, the
        # room is one short fade away.
        if wait_for_log_line(game_log_path, SHIP_RUN_MARKER, SHIP_DRIVE_WAIT_S):
            print("the game reported the run starting")
            time.sleep(SHIP_ROOM_SETTLE_S)
        else:
            print("no run marker within %.1f s, capturing on the clock instead" % SHIP_DRIVE_WAIT_S)
            time.sleep(SHIP_DRIVE_WAIT_S)

        # The window copies are kept under their own names as a second opinion. They are not the card's proof: a
        # screen rectangle copy of a DirectX11 window measured the desktop's colours in this session, so the pair the
        # card names comes from the room's own frames below.
        window_first = os.path.join(OUTPUT_DIR, "ship_window_1.png")
        raised, raise_note = ensure_key_focus(hwnd, attempts=3, settle=0.2)
        print("capture raise: %s" % raise_note)
        rect, written, note = capture_window(hwnd, window_first)
        if rect is None or written is None:
            print("window copy 1 failed (not fatal, the room's own frame is the proof): %s" % note)
        else:
            print("copied window rectangle %s %sx%s" % (window_first, rect[2], rect[3]))

        sent = 0
        for _step in range(SHIP_WALK_STEPS):
            if press(VK_RIGHT) in ("sent", "posted"):
                sent += 1
            time.sleep(SHIP_KEY_GAP_S)
        print("right key sent %d times" % sent)
        # The sailor stands on the tile the hero has just walked up against, so one confirm opens the dialogue box in
        # the spr_pp_window frame. The third self frame is taken after this press.
        print("confirm at the sailor %s" % press(VK_Z))
        time.sleep(SHIP_AFTER_WALK_S)

        window_second = os.path.join(OUTPUT_DIR, "ship_window_2.png")
        raised, raise_note = ensure_key_focus(hwnd, attempts=3, settle=0.2)
        print("capture raise: %s" % raise_note)
        rect, written, note = capture_window(hwnd, window_second)
        if rect is None or written is None:
            print("window copy 2 failed (not fatal, the room's own frame is the proof): %s" % note)
        else:
            print("copied window rectangle %s %sx%s" % (window_second, rect[2], rect[3]))

        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            kill_tree(process)

        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort: the crash check below reads the file from disk.
            pass
        with open(game_log_path, "r", encoding="utf-8", errors="replace") as handle:
            log_text = handle.read()
        if "PP CRASH" in log_text:
            crash_lines = [line for line in log_text.splitlines() if "PP CRASH" in line]
            print("the game reported a crash: %s" % crash_lines[0][:200])
            return 1
        print("no PP CRASH in %s" % game_log_path)

        first_path = os.path.join(OUTPUT_DIR, "ship_run_1.png")
        second_path = os.path.join(OUTPUT_DIR, "ship_run_2.png")
        self_first, self_second, self_third = ship_self_paths
        missing = [p for p in (self_first, self_second) if not os.path.isfile(p)]
        if missing:
            print("the room wrote no frame at %s, so the run cannot be proven from the game's own pixels" % missing[0])
            return 1
        shutil.copyfile(self_first, first_path)
        shutil.copyfile(self_second, second_path)
        print("the pair is the room's own frames: %s and %s" % (first_path, second_path))
        dialogue_path = os.path.join(OUTPUT_DIR, "ship_dialogue.png")
        if os.path.isfile(self_third):
            shutil.copyfile(self_third, dialogue_path)
            print("the dialogue frame is the room's own: %s" % dialogue_path)
        else:
            print("the room wrote no dialogue frame, so the box is not proven on screen")

        # The walker really walked: pp_overworld plays one footstep cue per tile it starts. A key pressed while the
        # walker is between tiles is correctly ignored, so the count is five or so out of eight presses, never zero.
        footsteps = len([line for line in log_text.splitlines() if "footstep played" in line])
        print("footstep cues in the log: %d" % footsteps)
        if footsteps == 0:
            print("the walker never moved, so the Right presses did not reach the room")
            return 1

        share = frames_differ(first_path, second_path)
        if share is None:
            print("the two ship frames could not be compared")
            return 1
        print("frames differ by %.4f of their pixels" % share)
        if share < SHIP_MIN_DIFF:
            print("the two ship frames are the same picture, so the player did not move")
            return 1

        print(first_path)
        print(second_path)
        return 0
    finally:
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact.
            pass


def intro_probe_capture(hwnd, out_path):
    """Copy the window rectangle quickly, for the start probe only. PIL first: a probe has to be cheap."""
    rect = get_window_rect(hwnd)
    if rect is None:
        return None, "the window has no rectangle, cannot capture"
    ok, note = capture_with_pil(rect, out_path)
    if not ok:
        ok, note = capture(rect, out_path)
    if not ok:
        return None, "capture failed: %s" % note
    return rect, note


def viewport_box_and_score(path):
    """The 3x viewport inside a window capture, as (box, score, note).

    This is the nes check card INTRO-1 asks for before a frame is saved: the same search record_viewport and
    nes_composite_check.py --crop auto run, so a copy is only accepted when the box inside it is made of legal 2C02
    colours. A copy of a terminal, of the desktop or of a covered window finds no such box and returns score 0.0.
    """
    try:
        from PIL import Image  # imported here so the other captures never pay for it
        sys.path.insert(0, TOOLS_DIR)
        import nes_composite_check as ncc
        palette = ncc.load_palette(ncc.default_palette_path(ROOT))
        with Image.open(path) as handle:
            image = handle.convert("RGBA")
        found = ncc.find_viewport(image, palette["allowed"])
        return list(found["box"]), float(found["score"]), "a 3x viewport at %s" % list(found["box"])
    except Exception as error:  # gate: ok A copy with no legal viewport is reported, never guessed at
        return None, 0.0, str(error).split(";")[0]


def logo_grey_pixels(path):
    """Count the grey pixels in the band the title logo occupies, inside a window screenshot.

    The logo is the only large light-grey mass in the top third of the frame, so its disappearance is the
    intro's first step: the title card measures about 10000 of these pixels and the star field about 1000.
    """
    from PIL import Image  # imported here so the other captures never pay for it

    try:
        image = Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None
    pixels = image.load()
    x0, y0, x1, y1 = LOGO_BAND
    total = 0
    for y in range(y0, min(y1, image.size[1])):
        for x in range(x0, min(x1, image.size[0])):
            r, g, b = pixels[x, y]
            if r == g == b and 90 <= r <= 250:
                total += 1
    return total


def press_until_intro(hwnd, attempts=TITLE_INTRO_PRESS_CAP, gap=1.2):
    """Press Enter while the title card is still on screen, and return the time the intro started.

    Enter is the confirm key (game/scripts/pp_input/pp_input.gml: confirm is Z, space and vk_enter). On the intro a
    confirm FINISHES the crawl (game/scripts/pp_title/pp_title.gml, pp_title_step_intro: menu, cancel or confirm jump
    the crawl to its end), so a press sent after the intro has begun would destroy the frames this capture exists to
    prove. The loop therefore probes first and presses only while the title logo is still in the frame, and it
    returns None when the logo never goes.
    """
    probe = os.path.join(BUILD_DIR, "_intro_probe.png")
    deadline = time.time() + attempts * gap + 6.0
    presses = 0
    next_press_at = 0.0
    while time.time() < deadline:
        rect, _note = intro_probe_capture(hwnd, probe)
        if rect is None:
            ensure_key_focus(hwnd, attempts=3, settle=0.2)
            time.sleep(0.2)
            continue
        grey = logo_grey_pixels(probe)
        if grey is None:
            discard(probe)
            return None
        if grey < LOGO_GONE_PIXELS:
            # The logo has gone. Believe it only when the copy is the game's own screen: a window that slipped over
            # the game would also lose the logo band, and that mistake is what the first pass saved as four frames.
            box, score, why = viewport_box_and_score(probe)
            if box is not None and score >= INTRO_VIEWPORT_MIN_SCORE:
                discard(probe)
                return time.time()
            print("the logo is gone but the copy is not the game (%s, score %.3f), raising the window" % (why, score))
            ensure_key_focus(hwnd, attempts=3, settle=0.2)
            time.sleep(0.15)
            continue
        if time.time() >= next_press_at:
            if presses >= attempts:
                break
            presses += 1
            # A press is only ever sent on a frame where the title card was just measured to be up, so it cannot
            # land on the intro.
            print("enter %d %s" % (presses, send_vk(hwnd, VK_RETURN)))
            next_press_at = time.time() + gap
        time.sleep(0.15)
    discard(probe)
    return None


def copy_rect_verified(rect, out_path):
    """Copy the window rectangle and return (box, score, route, cost), keeping only a copy that is the game.

    The PowerShell CopyFromScreen helper is the method DEVLOG records as working on this PC, but a fresh PowerShell
    with System.Drawing costs about 6 s a frame here (tools/measure_title_scroll.py measured 7.5 s), which makes a
    timed capture of a 14 s cutscene impossible: the first pass of this card copied at 6.8, 13.2, 17.7 and 21.8 s
    for targets of 1, 4, 8 and 14 s. PIL's ImageGrab is the same BitBlt through an already loaded library, so it is
    tried first; the nes check decides whether its copy is the game, and PowerShell stays the fallback when it is not.
    """
    before = time.time()
    ok, note = capture_with_pil(rect, out_path)
    cost = time.time() - before
    if ok:
        box, score, why = viewport_box_and_score(out_path)
        if box is not None and score >= INTRO_VIEWPORT_MIN_SCORE:
            return box, score, "PIL", cost
    else:
        why = note
    discard(out_path)
    before = time.time()
    ok, note = capture_with_powershell(rect, out_path)
    cost = time.time() - before
    if not ok:
        return None, 0.0, "PIL: %s; powershell: %s" % (why, note), cost
    box, score, powershell_why = viewport_box_and_score(out_path)
    if box is not None and score >= INTRO_VIEWPORT_MIN_SCORE:
        return box, score, "powershell", cost
    discard(out_path)
    return None, score, "PIL: %s; powershell: %s" % (why, powershell_why), cost


def capture_intro_frame(hwnd, out_path, target, started, lead=INTRO_COPY_LEAD_S):
    """Copy the game window at target seconds into the intro, keeping the copy only if the nes check passes.

    Every grab raises the window with SetForegroundWindow first, because a refused raise is exactly what put the
    terminal in the previous pass's four frames. The copy is then tested with the same search
    nes_composite_check.py --crop auto runs: the frame must hold the game's own 3x viewport made of legal 2C02
    colours. A rejected copy is deleted and tried again instead of being saved as if it were a frame.

    Returns (rect, box, score, route, taken_at, cost) or (None, None, 0.0, note, taken_at, lead).
    """
    last = "not attempted"
    for _attempt in range(INTRO_GRAB_ATTEMPTS):
        ok, focus_note = ensure_key_focus(hwnd, attempts=3, settle=0.15)
        if not ok:
            print("could not raise the game window for the frame at t=%.0f s: %s" % (target, focus_note))
        # The copy costs a few milliseconds through PIL and about six seconds through PowerShell, so it is started
        # early by the measured cost of the previous one: the copy then lands on the card's timestamp.
        remaining = started + target - lead - time.time()
        if remaining > 0:
            time.sleep(remaining)
        rect = get_window_rect(hwnd)
        if rect is None:
            last = "the window has no rectangle, cannot capture"
            continue
        box, score, route, cost = copy_rect_verified(rect, out_path)
        if box is not None:
            return rect, box, score, route, time.time(), cost
        last = "no legal 3x NES viewport in the copy (%s, score %.3f), so it is not the game" % (route, score)
        print("frame at t=%.0f s rejected: %s" % (target, last))
    return None, None, 0.0, last, time.time(), lead


def wait_for_intro_start(log_path, hwnd, timeout_s=INTRO_START_TIMEOUT_S):
    """Return the time the intro's first step was seen in the game log, or None if it never started.

    Reading the log is the only proof that NEW GAME really took: the menu may swallow a press that lands
    while the opening shot is still playing. When the line is late, one more Enter is sent, which covers
    the case where the first press opened the menu a beat later than the fixed wait assumed.
    """
    began = time.time()
    nudged = False
    while time.time() - began < timeout_s:
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                if "PP title: intro started" in handle.read():
                    return time.time()
        except OSError:
            # The game may hold the file for writing on this platform; the fixed waits still apply then.
            return None
        if not nudged and time.time() - began > INTRO_NUDGE_S:
            print("no intro line yet, pressing enter again %s" % send_vk(hwnd, VK_RETURN))
            nudged = True
        time.sleep(0.05)
    return None


def run_intro_capture():
    """Start a new game and capture the intro at 1, 4, 8 and 14 seconds into it (card INTRO-1).

    The wait before the first Enter covers the opening shot, which plays for three seconds on a first boot and any
    key skips it; on a later boot the title simply sits on PRESS START for the same wait, so the sequence is the same
    either way. Then Enter opens the menu and Enter again chooses NEW GAME, which is what starts the intro.

    The four frames are the card's own timestamps, measured from the frame the intro starts on: at 1 s the camera is
    mid pan, at 4 s the pan has landed and the world is fading, at 8 s only the sky's last fade and the stars are on
    screen, and at 14 s the crawl is running.

    Usage: python tools\\capture_title.py --intro
    """
    if not LAUNCH.gate("intro capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("launching %s -game %s" % (exe_path, win_path))

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-intro-game.log")
    game_log = open(game_log_path, "wb")
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="intro capture")
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    hwnd = None
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s" % (image_name, GAME_EXE_NAME))
            return 1
        print("game window found: %s (hwnd %s), process image %s" % (match[2], hwnd, image_name))

        time.sleep(GAME_SETTLE_S + INTRO_OPEN_WAIT_S)
        # Card INTRO-1, the fix: the first pass's four frames were the terminal, because the copy was taken from the
        # screen while another window sat on the game. The window is raised once here and held topmost for the whole
        # shot, so nothing can land in the rectangle the copies are read from.
        focused, focus_note = ensure_key_focus(hwnd)
        print("keyboard focus: %s" % focus_note)
        if not focused:
            print("the game never took the keyboard focus, so the intro cannot be started")
            return 1
        hold_on_top(hwnd)
        print("the game window is held topmost until the last frame is copied")

        # Press until the title logo leaves the frame: that frame is the intro's first step, and it is the only
        # honest start time. The game's own log line is block buffered when stdout is a file, so it cannot be
        # read live, and a stopwatch started at the key press drifts whenever the title eats a press.
        started = press_until_intro(hwnd)
        if started is None:
            print("the intro never started: the title logo stayed on screen through every press")
            return 1
        print("the intro started, the clock is on that frame")
        time.sleep(INTRO_LEAD_S)

        frames = []
        lead = INTRO_COPY_LEAD_S
        for index, target in enumerate(INTRO_TIMES, start=1):
            out_path = os.path.join(OUTPUT_DIR, "intro_%d.png" % index)
            rect, box, score, route, taken, cost = capture_intro_frame(hwnd, out_path, target, started, lead)
            # The next copy is started early by what this one cost, so its BitBlt lands on the card's time.
            lead = max(0.05, cost)
            if rect is None:
                print("intro capture %d failed: %s" % (index, route))
                return 1
            real, why = frame_is_real(out_path)
            if not real:
                print("intro capture %d rejected: %s" % (index, why))
                discard(out_path)
                return 1
            # The viewport sidecar, so the audit and the manager read the box instead of searching a second time.
            record_viewport(out_path, 3)
            print("captured %s at t=%.1f s (copy at %.2f s) %sx%s via %s, nes score %.3f, viewport %s"
                  % (out_path, target, taken - started, rect[2], rect[3], route, score, box))
            frames.append(out_path)

        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("the game did not close on request, terminating it")
            kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort: the crash check below reads the file from disk.
            pass

        with open(game_log_path, "r", encoding="utf-8", errors="replace") as handle:
            log_text = handle.read()
        if "PP CRASH" in log_text:
            crash_lines = [line for line in log_text.splitlines() if "PP CRASH" in line]
            print("the game reported a crash: %s" % crash_lines[0][:200])
            return 1
        print("no PP CRASH in %s" % game_log_path)
        # The line NEW GAME writes when the intro starts is the proof that the two Enters landed on the menu row the
        # card asks for; without it the frames could be the menu and still look plausible.
        started_lines = [line for line in log_text.splitlines() if "PP title: intro started" in line]
        if not started_lines:
            print("the log has no 'PP title: intro started' line, so NEW GAME never started the intro")
            return 1
        print(started_lines[0].strip())

        differences = []
        for i in range(len(frames)):
            for j in range(i + 1, len(frames)):
                ratio = frames_differ(frames[i], frames[j])
                if ratio is not None:
                    differences.append((INTRO_TIMES[i], INTRO_TIMES[j], ratio))
        if not differences:
            print("the intro frames could not be compared")
            return 1
        differences.sort(key=lambda row: row[2], reverse=True)
        best = differences[0]
        print("frame differences: the largest is %.5f of the pixels between t=%.0f and t=%.0f"
              % (best[2], best[0], best[1]))
        if best[2] < INTRO_MIN_DIFF:
            print("the intro frames are all the same picture, so nothing played")
            return 1

        for path in frames:
            print(path)
        return 0
    finally:
        # The topmost flag is given back whether the run worked or not, so the game window never stays pinned over
        # the desktop after the harness ends.
        if hwnd is not None:
            release_on_top(hwnd)
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact.
            pass


# ---------------------------------------------------------------------------------------------------------------------
# Scripted keys (card SFX-WIRE). Drives a menu with real key presses so the audio cues it plays can be read from
# the game log afterwards, which is the only proof a sound was asked for at the moment the player acted.

# Virtual key codes for the key names a script may use. The names are the game's own input ids where the two
# agree, so a script reads like the action it performs. confirm is Z and cancel is X, the same binding as
# game\scripts\pp_input\pp_input.gml.
KEY_CODES = {
    "enter": 0x0D,
    "confirm": 0x5A,
    "z": 0x5A,
    "cancel": 0x58,
    "x": 0x58,
    "space": 0x20,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "escape": 0x1B,
}
# "wait" is not a key: it is a pause in the script, so a scene that plays out over several seconds can be given
# the time it needs without guessing one gap for every press.
KEY_WAIT_S = 1.0
KEY_GAP_S = 0.45
KEYS_USER_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PrimordialParadox")
KEYS_SEEN_FILE = os.path.join(KEYS_USER_DIR, "pp_title_seen.txt")


def parse_key_script(text):
    """Split "enter,down,down,enter" into a list of tokens, refusing any token that is not a key or wait."""
    tokens = []
    for raw in str(text).split(","):
        token = raw.strip().lower()
        if not token:
            continue
        if token == "wait" or token in KEY_CODES:
            tokens.append(token)
            continue
        raise SystemExit("unknown key %r in --keys; the names are %s and wait"
                         % (raw, ", ".join(sorted(KEY_CODES))))
    return tokens


def run_keys_capture(tokens, expect=None, first_boot=False):
    """Launch the game, send one key at a time, capture a frame, then check the audio lines in the log.

    Steps:
      1. --first-boot removes the opening marker, so the title is in its first boot phase and the key script
         starts from a known state instead of depending on whether the game was run before.
      2. Every token is sent with KEY_GAP_S between presses, because the game reads the key state once a step
         and two presses inside one step read as one.
      3. A frame is captured after the script, to prove the window was the game and to give the reviewer a
         picture of where the script left it.
      4. The game log is read back. Every "PP audio: <cue> played" line is printed, each cue in --expect must
         appear at least once, and a PP CRASH anywhere fails the run.
    """
    # Card CAPTURE-QUIET: a --keys run is normally an audio proof, so --sound is what a card asking about cues passes.
    if not LAUNCH.gate("keys capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    expect = [cue.strip() for cue in (expect or "").split(",") if cue.strip()]

    if first_boot:
        if os.path.isfile(KEYS_SEEN_FILE):
            os.remove(KEYS_SEEN_FILE)
            print("removed the opening marker so the title starts in its first boot phase: %s" % KEYS_SEEN_FILE)
        else:
            print("no opening marker at %s, the title is already in its first boot phase" % KEYS_SEEN_FILE)

    print("launching %s -game %s" % (exe_path, win_path))
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-keys-game.log")
    game_log = open(game_log_path, "wb")
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="keys capture")
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s, so it is not the game window"
                  % (image_name, GAME_EXE_NAME))
            return 1
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))
        time.sleep(GAME_SETTLE_S)

        focus_ok, focus_note = ensure_key_focus(hwnd)
        print(focus_note)
        if not focus_ok:
            print("refusing to post the key script: a posted key is read by the window, not by the game's key "
                  "state, so a run built out of posted keys would prove nothing")
            return 1
        previous_foreground = user32.GetForegroundWindow()

        sent = 0
        for token in tokens:
            if token == "wait":
                print("wait %.1f s" % KEY_WAIT_S)
                time.sleep(KEY_WAIT_S)
                continue
            # The focus can be stolen between two presses (any window that pops up takes it). Take it back
            # rather than posting, so every press in the script is a press the game actually read.
            if not game_has_focus(hwnd):
                retaken, why = ensure_key_focus(hwnd, attempts=4, settle=0.2)
                print("focus lost before %s: %s" % (token, why))
                if not retaken:
                    return 1
            result = send_vk_focused(KEY_CODES[token])
            sent += 1
            print("key %s (%s)" % (token, result))
            time.sleep(KEY_GAP_S)
        print("keys sent: %d of %d tokens" % (sent, len(tokens)))
        restore_foreground(previous_foreground)
        time.sleep(FOREGROUND_SETTLE_S)

        frame_path = os.path.join(OUTPUT_DIR, "keys_run.png")
        rect, written, note = capture_window(hwnd, frame_path)
        if rect is None or written is None:
            print("frame capture failed: %s" % note)
            return 1
        real, why = frame_is_real(frame_path)
        if not real:
            print("frame rejected: %s" % why)
            discard(frame_path)
            return 1
        print("captured %s %sx%s (%s)" % (frame_path, rect[2], rect[3], why))

        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            kill_tree(process)
    finally:
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort: the checks below read the file from disk.
            pass

    with open(game_log_path, "r", encoding="utf-8", errors="replace") as handle:
        log_text = handle.read()
    audio_lines = [line.strip() for line in log_text.splitlines() if "PP audio:" in line]
    print("audio lines in %s: %d" % (game_log_path, len(audio_lines)))
    for line in audio_lines:
        print("  " + line)

    if "PP CRASH" in log_text:
        crash_lines = [line for line in log_text.splitlines() if "PP CRASH" in line]
        print("the game reported a crash: %s" % crash_lines[0][:200])
        return 1
    print("no PP CRASH in %s" % game_log_path)

    if not expect:
        print(frame_path)
        return 0

    missing = []
    for cue in expect:
        needle = "PP audio: %s played" % cue
        if not any(needle in line for line in audio_lines):
            missing.append(cue)
    if missing:
        print("FAIL these cues were never played: %s" % ", ".join(missing))
        return 1
    print("PASS every cue was played at least once: %s" % ", ".join(expect))
    print(frame_path)
    return 0


def run_selftest():
    """Prove the capture path works, using notepad, so the harness can be trusted before the room exists."""
    # Card CAPTURE-QUIET: the selftest opens a window too, so it is gated like every other launch here.
    if not LAUNCH.gate("capture selftest"):
        return IDLE_REFUSED
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "_capture_selftest.png")
    print("launching notepad")
    process = subprocess.Popen(["notepad.exe"], cwd=os.path.dirname(os.path.abspath(__file__)),
                               stdin=subprocess.DEVNULL)
    start_watchdog(process, WATCHDOG_S)
    match = None
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible and "notepad" in title.lower(),
            timeout_s=SELFTEST_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the notepad window did not appear within %.0f s" % SELFTEST_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        print("notepad window found: %s (hwnd %s)" % (match[2], hwnd))
        time.sleep(1.0)
        rect, written, note = capture_window(hwnd, out_path)
        if rect is None or written is None:
            print("selftest capture failed: %s" % note)
            return 1
        size = png_size(out_path)
        print("captured %s %sx%s via %s" % (out_path, rect[2], rect[3], note))
        print("png size: %sx%s" % size if size else "png size: unknown")
        print(out_path)
        return 0
    finally:
        if match is not None:
            try:
                close_window(match[0])
            except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
                pass
        kill_tree(process)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            kill_tree(process)


# Where the game writes its own frames. GameMaker's screen_save lands beside the game's save area, which is the
# folder the runtime derives from the project name under the user's local AppData, not the folder the runner was
# started in. Measured 2026-10-22 for the ship room's frames, and the title's frames land in the same place.
SCROLL_SELF_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "PrimordialParadox")
SCROLL_SELF_NAMES = ("pp_title_scroll_1.png", "pp_title_scroll_2.png", "pp_title_scroll_3.png")
# How long the three frames are given to appear after the title is up. The first one is written ten beats in (about
# five seconds) and the last a beat after that, so twenty seconds is generous and still bounded.
SCROLL_FRAME_TIMEOUT_S = 30.0
SCROLL_TOOL = os.path.join(TOOLS_DIR, "measure_title_scroll_native.py")
NES_CHECK = os.path.join(TOOLS_DIR, "nes_composite_check.py")
SCROLL_STAMP = re.compile(r"wrote (pp_title_scroll_\d\.png) at step (\d+), scroll ([0-9.]+)")


def scroll_self_paths():
    """The three files the game writes for this check, in the order it writes them."""
    return [os.path.join(SCROLL_SELF_DIR, name) for name in SCROLL_SELF_NAMES]


def native_screen(source_path, out_path):
    """Cut the 256x240 game screen out of a screen_save, and say what the cut was.

    screen_save writes this window at 768x720, which is the exact 3x of the game's own 256x240 screen, so the frame is
    sampled every third pixel rather than resized: a filter would blend neighbouring game pixels and the lane dashes
    this check follows would lose the edges the measurement needs. The result is the game's own pixels, which is also
    what makes the picture a legal NES frame for tools\\nes_composite_check.py (a window copy of the same scene measured
    111 colours and 65 palette violations, none of which were the art's).
    """
    try:
        from PIL import Image
    except Exception as exc:
        return None, "PIL missing: %s" % exc
    try:
        image = Image.open(source_path).convert("RGB")
    except (OSError, ValueError) as exc:
        return None, "the frame could not be read: %s" % exc
    if image.width % 256 or image.height % 240:
        return None, "the frame is %dx%d, which is not a whole multiple of 256x240" % (image.width, image.height)
    factor = max(1, image.width // 256)
    native = image.resize((image.width // factor, image.height // factor),
                          Image.Resampling.NEAREST) if factor > 1 else image
    native.save(out_path, "PNG")
    return native, "%dx%d at %dx -> %dx%d native" % (image.width, image.height, factor,
                                                     native.width, native.height)


def run_scroll_capture():
    """Capture the title's own three frames a half beat apart and measure the scroll they show (card TEMPO-1).

    The card asks for two frames 0.5 s apart whose scroll difference is the tempo's own number. Review round 1 found
    that the window copies this harness used to take cannot answer it: one PowerShell copy costs about 7.5 s, the pair
    landed 10 s apart, the copy carried the desktop's scaling (111 colours, 104 of them not palette entries), and an
    independent cross correlation found no scroll at all. So the frames are now the GAME'S OWN, written by screen_save
    inside the title's draw when PP_TITLE_CAPTURE is set (pp_title_capture_frames), three of them on one lattice: ten
    beats in, then a half beat and a beat after that. The gap is a step count the game logs, not a stopwatch, so
    0.25 s and 0.5 s are exact; and half a beat of road is 8 px, which stays inside the 16 px dash period the art
    repeats on, so the correlation is never asked to resolve an aliased shift.

    Usage: python tools\\capture_title.py --scroll
    """
    if not LAUNCH.gate("title scroll capture"):
        return IDLE_REFUSED
    build = newest_build()
    if build is None:
        print("no built game found under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("launching %s -game %s with PP_TITLE_CAPTURE=1" % (exe_path, win_path))
    for stale in scroll_self_paths():
        if os.path.exists(stale):
            os.remove(stale)

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    game_log_path = os.path.join(BUILD_DIR, "capture-scroll-game.log")
    game_log = open(game_log_path, "wb")
    child_env = dict(os.environ)
    child_env["PP_TITLE_CAPTURE"] = "1"
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one
    # PP: muted line from this run's own log. The exit line comes from run.finish() in this function's finally.
    run = pp_launch.start_game(exe_path, win_path, log=game_log, policy=LAUNCH, label="title scroll capture", base=child_env)
    process = run.process
    start_watchdog(process, WATCHDOG_S)
    try:
        match = find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and pid == process.pid
            and GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=GAME_WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("the game window did not appear within %.0f s" % GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved onto a monitor other than the primary one unless --show was given, so
        # the only part of this run Nayil can see is nothing.
        LAUNCH.place(hwnd, get_window_rect(hwnd))
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s, so it is not the game window" % (image_name, GAME_EXE_NAME))
            return 1
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))
        time.sleep(GAME_SETTLE_S)

        wanted = scroll_self_paths()
        deadline = time.time() + SCROLL_FRAME_TIMEOUT_S
        while time.time() < deadline and not all(os.path.isfile(path) for path in wanted):
            time.sleep(0.25)
        written = [path for path in wanted if os.path.isfile(path)]
        print("the game wrote %d of %d of its own frames: %s"
              % (len(written), len(wanted), ", ".join(os.path.basename(path) for path in written)))

        close_window(hwnd)
        deadline = time.time() + CLOSE_GRACE_S
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("the game did not close on request, terminating it")
            kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort: the log is read from disk just below.
            pass

        with open(game_log_path, "r", encoding="utf-8", errors="replace") as handle:
            log_text = handle.read()
        theme = [line for line in log_text.splitlines() if "title_theme streaming" in line]
        print("audio: %s" % (theme[0].strip() if theme else "no theme stream line in %s" % game_log_path))
        if "PP CRASH" in log_text:
            print("the game reported a crash")
            return 1
        if len(written) != len(wanted):
            print("the game did not write all three frames, so the scroll cannot be measured")
            return 1

        # The game's own account of when each frame was drawn: a step count and the scroll value it drew with.
        stamps = {}
        for line in log_text.splitlines():
            found = SCROLL_STAMP.search(line)
            if found:
                stamps[found.group(1)] = (int(found.group(2)), float(found.group(3)))
        missing = [name for name in SCROLL_SELF_NAMES if name not in stamps]
        if missing:
            print("the game's log has no step count for %s, so the frames cannot be timestamped" % ", ".join(missing))
            return 1

        copies, natives, steps, scrolls = [], [], [], []
        for index, name in enumerate(SCROLL_SELF_NAMES, start=1):
            step, scroll = stamps[name]
            source = os.path.join(SCROLL_SELF_DIR, name)
            copy_path = os.path.join(OUTPUT_DIR, "title_scroll_%d.png" % index)
            native_path = os.path.join(OUTPUT_DIR, "title_scroll_%d_native.png" % index)
            shutil.copyfile(source, copy_path)
            native, note = native_screen(source, native_path)
            if native is None:
                print("frame %d could not be cut to the game screen: %s" % (index, note))
                return 1
            copies.append(copy_path)
            natives.append(native_path)
            steps.append(step)
            scrolls.append(scroll)
            print("frame %d: %s, step %d, scroll %.3f, %s" % (index, os.path.basename(source), step, scroll, note))

        # The measurement: every band's shift against every layer's expected shift, computed from the same scroll
        # values the game drew with, so the arithmetic and the pixels are compared directly.
        command = [sys.executable, SCROLL_TOOL,
                   "--frames"] + natives + ["--steps"] + [str(step) for step in steps] \
                  + ["--scroll"] + ["%.3f" % scroll for scroll in scrolls] \
                  + ["--json", os.path.join(OUTPUT_DIR, "title_scroll_measure.json")]
        print("")
        result = subprocess.run(command, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        print((result.stdout or "").strip())
        if result.stderr:
            print((result.stderr or "").strip()[-1200:])

        # The NES frame check on the game's own picture: 256x240 of the game's pixels is a legal 2C02 frame, so a
        # failure here is the art and not the capture path (which is what review round 1 measured).
        print("")
        nes = subprocess.run([sys.executable, NES_CHECK, natives[0], "--crop", "1"],
                             capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        nes_text = (nes.stdout or "") + (nes.stderr or "")
        for line in nes_text.splitlines():
            if line.strip():
                print(line.strip())
        print("")

        if result.returncode != 0:
            print("the scroll measurement did not match the tempo")
            return 1
        if nes.returncode != 0:
            print("the game's own frame is not a legal NES picture")
            return 1
        print("frames: %s" % ", ".join(os.path.basename(path) for path in natives))
        return 0
    finally:
        # The one exit line, and the game closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


def main():
    global LAUNCH
    # Card PINE-HONEST (t_84fe63ff): a capture tool on a machine with no window cannot capture, and saying so is the
    # only honest answer. Same not-measured code as tools\play_demo.py, so a reader never mistakes it for a pass.
    if not WINDOW_PRIMITIVES:
        print("capture_title: unavailable on this platform")
        return pp_launch.EXIT_REFUSED
    parser = argparse.ArgumentParser(description="Capture the title screen frames of the built game.")
    # Card CAPTURE-QUIET: --sound, --show, --idle-wait and --force, spelled once in tools\pp_launch.py so every
    # launching tool takes the same four flags.
    pp_launch.add_launch_flags(parser)
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="prove the capture path on notepad instead of the game",
    )
    parser.add_argument(
        "--video",
        action="store_true",
        help="record the title screen with ffmpeg into output\\title_run.mp4 and check the file",
    )
    parser.add_argument(
        "--room",
        choices=("ship",),
        default=None,
        help="start a new game and capture the ship room twice into output\\ship_run_1.png and _2.png",
    )
    parser.add_argument(
        "--intro",
        action="store_true",
        help="start a new game and capture the intro at 1, 4, 8 and 14 s into output\\intro_1.png to intro_4.png",
    )
    parser.add_argument(
        "--keys",
        default=None,
        help="drive the game with a key script, for example 'enter,enter,down,down,enter,cancel', then read the "
             "PP audio lines back from the game log; 'wait' pauses between presses",
    )
    parser.add_argument(
        "--expect",
        default=None,
        help="comma separated cue names that must each be played at least once in the --keys run",
    )
    parser.add_argument(
        "--first-boot",
        action="store_true",
        help="remove the opening marker before the --keys run, so the title starts in its first boot phase",
    )
    parser.add_argument(
        "--scroll",
        action="store_true",
        help="capture two title frames half a second apart into output\\title_scroll_1.png and _2.png with no "
             "key pressed, and print the elapsed time so the world's travel can be measured (card TEMPO-1)",
    )
    args = parser.parse_args()
    LAUNCH = pp_launch.policy_from_args(args)
    if args.selftest:
        return run_selftest()
    if args.video:
        return run_video_capture()
    if args.keys:
        return run_keys_capture(parse_key_script(args.keys), args.expect, args.first_boot)
    if args.room == "ship":
        return run_ship_capture()
    if args.intro:
        return run_intro_capture()
    if args.scroll:
        return run_scroll_capture()
    return run_game_capture()


if __name__ == "__main__":
    sys.exit(main())
