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

Exit codes:
    0  both frames were written (or the selftest frame was written)
    1  the game window never appeared, or the capture failed
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
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
SW_RESTORE = 9
KEYEVENTF_KEYUP = 0x0002


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


def send_enter(hwnd):
    """Send exactly one Enter key press to the game window. No other key is sent."""
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
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()
    return run_game_capture()


if __name__ == "__main__":
    sys.exit(main())
