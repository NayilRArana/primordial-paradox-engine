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
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
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
CLOSE_GRACE_S = 5.0
SELFTEST_WINDOW_TIMEOUT_S = 20.0
WATCHDOG_S = 120.0

# ---------------------------------------------------------------------------------------------------------------------
# Video capture settings

VIDEO_OUT = os.path.join(OUTPUT_DIR, "title_run.mp4")
VIDEO_PREVIEW = os.path.join(OUTPUT_DIR, "title_run_preview.png")
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
# The frames of a real game screen carry the night blue of the title sky. The anchor is read from the
# reference capture of the same window (output\title_run_1.png), so a frame that shows a foreign window
# instead of the game fails this check. It is a share of pixels, so a small change in the art does not
# break it.
VIDEO_GAME_ANCHOUR_COLOURS = ((8, 20, 32), (13, 43, 58), (11, 11, 15))
VIDEO_GAME_ANCHOUR_SHARE = 0.02

# user32 and kernel32 through ctypes: no extra packages needed for the window side.
user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:  # gate: ok DPI awareness is best effort: it may fail on a headless session and the capture still works.
        pass

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

WM_CLOSE = 0x0010
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_RIGHT = 0x27
# The ship room capture (card ASSEMBLE): the wait covers NEW GAME's 240 step drive (4 s at 60 steps) and the fade,
# the walk is the card's eight Right presses, and the minimum difference rejects two copies of one still frame.
SHIP_DRIVE_WAIT_S = 5.5
SHIP_WALK_STEPS = 8
SHIP_KEY_GAP_S = 0.18
SHIP_AFTER_WALK_S = 0.5
SHIP_MIN_DIFF = 0.001
SW_RESTORE = 9
KEYEVENTF_KEYUP = 0x0002
# Topmost and not topmost, for the window handles that SetWindowPos takes.
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010


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


def send_enter(hwnd, keep_foreground=False):
    """Send exactly one Enter key press to the game window. No other key is sent.

    keep_foreground leaves the game window on top instead of handing the focus back. The video capture
    needs that: the recording grabs the screen rectangle of the game, so anything else on top of it
    would end up in the file instead of the game.
    """
    previous = bring_to_front(hwnd)
    focused = user32.GetForegroundWindow() == hwnd
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
    focused = user32.GetForegroundWindow() == hwnd
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


def frame_shows_game(path):
    """The share of pixels in a frame that carry the night blue of the title screen.

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
        if pixel[0] > 40 or pixel[1] > 60 or pixel[2] > 80:
            continue
        for anchor in VIDEO_GAME_ANCHOUR_COLOURS:
            if abs(pixel[0] - anchor[0]) <= 6 and abs(pixel[1] - anchor[1]) <= 6 \
                    and abs(pixel[2] - anchor[2]) <= 6:
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
    margin = 12
    label_h = 26
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
    process = subprocess.Popen(
        [exe_path, "-game", win_path],
        cwd=os.path.dirname(exe_path),
        stdin=subprocess.DEVNULL,
        stdout=game_log,
        stderr=subprocess.STDOUT,
    )
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
        work_dir = tempfile.mkdtemp(prefix="titlevid-")
        frames = []
        notes = []
        game_shares = []
        for stamp in VIDEO_SAMPLE_TIMES:
            frame_path = os.path.join(work_dir, "frame_%.1f.png" % stamp)
            if extract_frame(ffmpeg_path, VIDEO_OUT, stamp, frame_path):
                frames.append(frame_path)
                notes.append("t=%.1f s" % stamp)
                share = frame_shows_game(frame_path)
                if share is not None:
                    game_shares.append((notes[-1], share))
            else:
                frames.append(None)
                notes.append("t=%.1f s (missing)" % stamp)

        # Check 3a: every sampled frame shows the game, not another window that came to the front.
        if game_shares:
            for note, share in game_shares:
                print("game pixels in %s: %.4f" % (note, share))
            worst_note, worst_share = min(game_shares, key=lambda row: row[1])
            if worst_share < VIDEO_GAME_ANCHOUR_SHARE:
                print("FAIL the frame at %s carries only %.4f of the game's title colours, so the "
                      "recording shows something else" % (worst_note, worst_share))
                return 1
            print("PASS every sampled frame carries the game's title colours (the lowest is %.4f at %s)"
                  % (worst_share, worst_note))
        else:
            print("FAIL the game colour check could not run on any frame")
            return 1

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
        kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


# ---------------------------------------------------------------------------------------------------------------------
# The two jobs

def run_game_capture():
    """Launch the built game, capture the title screen, press one Enter, capture again, close the game."""
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
    process = subprocess.Popen(
        [exe_path, "-game", win_path],
        cwd=os.path.dirname(exe_path),
        stdin=subprocess.DEVNULL,
        stdout=game_log,
        stderr=subprocess.STDOUT,
    )
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
        kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact: the capture result does not depend on it.
            pass


def run_ship_capture():
    """Enter the ship room from the title, walk right, and capture the room twice.

    Steps, and why each wait is the number it is:
      1. Launch the built game and wait for its own window (the same guard run_game_capture uses).
      2. Enter once to pass the title's opening shot, wait, Enter again to choose NEW GAME. NEW GAME plays the
         240 step night drive before the run starts, so the wait after the second Enter covers the drive (4 s
         at 60 steps a second) plus the fade.
      3. Capture output\\ship_run_1.png.
      4. Press Right eight times, the card's own walk, then capture output\\ship_run_2.png.
      5. Fail if the two frames are the same picture, or if the game log carries "PP CRASH".

    Usage: python tools\\capture_title.py --room ship
    """
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
    process = subprocess.Popen(
        [exe_path, "-game", win_path],
        cwd=os.path.dirname(exe_path),
        stdin=subprocess.DEVNULL,
        stdout=game_log,
        stderr=subprocess.STDOUT,
    )
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
        image_name = process_image_name(match[1])
        if image_name.lower() != GAME_EXE_NAME.lower():
            print("the window belongs to %r, not to %s" % (image_name, GAME_EXE_NAME))
            return 1
        print("game window found: %s (hwnd %s)" % (match[2], hwnd))

        time.sleep(GAME_SETTLE_S)
        print("title enter 1 %s" % send_vk(hwnd, VK_RETURN))
        time.sleep(AFTER_ENTER_S)
        print("title enter 2 (NEW GAME) %s" % send_vk(hwnd, VK_RETURN))
        time.sleep(SHIP_DRIVE_WAIT_S)

        first_path = os.path.join(OUTPUT_DIR, "ship_run_1.png")
        rect, written, note = capture_window(hwnd, first_path)
        if rect is None or written is None:
            print("ship capture 1 failed: %s" % note)
            return 1
        real, why = frame_is_real(first_path)
        if not real:
            print("ship capture 1 rejected: %s" % why)
            discard(first_path)
            return 1
        print("captured %s %sx%s (%s)" % (first_path, rect[2], rect[3], why))

        sent = 0
        for _step in range(SHIP_WALK_STEPS):
            if send_vk(hwnd, VK_RIGHT) in ("sent", "posted"):
                sent += 1
            time.sleep(SHIP_KEY_GAP_S)
        print("right key sent %d times" % sent)
        time.sleep(SHIP_AFTER_WALK_S)

        second_path = os.path.join(OUTPUT_DIR, "ship_run_2.png")
        rect, written, note = capture_window(hwnd, second_path)
        if rect is None or written is None:
            print("ship capture 2 failed: %s" % note)
            return 1
        real, why = frame_is_real(second_path)
        if not real:
            print("ship capture 2 rejected: %s" % why)
            discard(second_path)
            return 1
        print("captured %s %sx%s (%s)" % (second_path, rect[2], rect[3], why))

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
        kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup of a temp artifact.
            pass


def run_selftest():
    """Prove the capture path works, using notepad, so the harness can be trusted before the room exists."""
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


def main():
    parser = argparse.ArgumentParser(description="Capture the title screen frames of the built game.")
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
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()
    if args.video:
        return run_video_capture()
    if args.room == "ship":
        return run_ship_capture()
    return run_game_capture()


if __name__ == "__main__":
    sys.exit(main())
