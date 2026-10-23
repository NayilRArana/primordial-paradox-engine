#!/usr/bin/env python3
"""inspect_frame.py: launch the built game, capture the client area, and print what is on it.

Why: the first screen of the game has to be read as pixels before it can be judged. The picture is mapped
onto the master palette in data\\palette.json, so the print names the palette role of every mark instead of
guessing from a thumbnail.

Usage:
    python tools/inspect_frame.py                 capture output\\_inspect_frame.png and print the map
    python tools/inspect_frame.py --keys          also send Enter after the first capture
    python tools/inspect_frame.py --wait 6        seconds to wait before capturing (default 3)
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pp_launch  # noqa: E402  the launch policy: PP_MUTE=1, the idle gate, and the quiet window (card CAPTURE-QUIET)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
GAME_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "PrimordialParadox")
GAME_WINDOW_TITLE = "Primordial Paradox"

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:  # gate: ok DPI awareness is best effort: it may fail on a headless session and the inspection still works.
        pass

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

WM_CLOSE = 0x0010
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D


def enum_windows():
    found = []
    def callback(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        rect = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append((hwnd, pid.value, buffer.value, bool(user32.IsWindowVisible(hwnd)),
                      (rect.left, rect.top, rect.right, rect.bottom)))
        return True
    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return found


def client_rect(hwnd):
    rect = wt.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def client_screen_rect(hwnd):
    rect = client_rect(hwnd)
    if rect is None:
        return None
    origin = wt.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    left, top, right, bottom = rect
    return (origin.x, origin.y, right - left, bottom - top)


def newest_build():
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
        candidates = [os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(".exe")]
        if not candidates:
            return None
        exe_path = max(candidates, key=os.path.getmtime)
    return exe_path, win_path


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


def capture(rect, out_path):
    import tempfile
    left, top, width, height = rect
    handle, script_path = tempfile.mkstemp(suffix=".ps1")
    os.close(handle)
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(POWERSHELL_CAPTURE)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path,
             "-X", str(left), "-Y", str(top), "-W", str(width), "-H", str(height), "-Out", out_path],
            capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or "").strip()
    finally:
        try:
            os.remove(script_path)
        except OSError:  # gate: ok Best-effort cleanup of a temp file: the frame inspection result does not depend on it.
            pass
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 0, "powershell"


SW_RESTORE = 9
KEYEVENTF_KEYUP = 0x0002


def bring_to_front(hwnd):
    """Put the window on top and in the foreground, briefly, so a screen copy shows the window itself.

    A screen copy of a rectangle that is not the foreground window shows whatever is on top of it, which
    is how the first version of this tool measured a desktop instead of the game.
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
    if not previous or not user32.IsWindow(previous):
        return
    user32.SetForegroundWindow(previous)


def load_palette():
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    colours = []
    for value in data["colours"]:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
    roles = data.get("roles", {})
    return colours, roles


def nearest(colours, pixel):
    best = 0
    best_d = 1 << 30
    for index, colour in enumerate(colours):
        dr = pixel[0] - colour[0]
        dg = pixel[1] - colour[1]
        db = pixel[2] - colour[2]
        d = dr * dr + dg * dg + db * db
        if d < best_d:
            best_d = d
            best = index
    return best, best_d


def report(path, step):
    colours, roles = load_palette()
    role_of = {}
    for name, index in roles.items():
        role_of.setdefault(index, name)
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    print("client area %dx%d" % (w, h))
    used = {}
    for y in range(0, h, step):
        row = ""
        for x in range(0, w, step):
            index, distance = nearest(colours, px[x, y])
            used[index] = used.get(index, 0) + 1
            if distance > 9000:
                row += "?"
            else:
                row += role_of.get(index, chr(65 + index % 26))
        print("%3d|%s" % (y, row))
    print()
    for index in sorted(used, key=lambda i: -used[i]):
        r, g, b = colours[index]
        print("  #%02x%02x%02x  index %2d  %-14s %6d samples" % (
            r, g, b, index, role_of.get(index, "-"), used[index]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", action="store_true", help="send Enter after the first capture")
    parser.add_argument("--wait", type=float, default=3.0, help="seconds to wait before capturing")
    parser.add_argument("--step", type=int, default=2, help="ascii step in pixels")
    parser.add_argument("--out", default=os.path.join(OUTPUT_DIR, "_inspect_frame.png"))
    args = parser.parse_args()

    # Card CAPTURE-QUIET: no window while the user is at the PC, and PP_MUTE=1 so nothing plays.
    if not pp_launch.Policy().gate("inspect frame"):
        return pp_launch.EXIT_REFUSED
    build = newest_build()
    if build is None:
        print("no built game under %s" % GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("launching %s" % exe_path)
    process = subprocess.Popen([exe_path, "-game", win_path], cwd=os.path.dirname(exe_path),
                               stdin=subprocess.DEVNULL, env=pp_launch.game_env())
    hwnd = None
    try:
        deadline = time.time() + 20
        while time.time() < deadline and hwnd is None:
            for window in enum_windows():
                if window[3] and window[1] == process.pid and GAME_WINDOW_TITLE.lower() in window[2].lower():
                    hwnd = window[0]
                    break
            time.sleep(0.25)
        if hwnd is None:
            print("the game window did not appear")
            return 1
        # Card CAPTURE-QUIET: off the primary screen, so the window is not in his face.
        pp_launch.place_window_quietly(hwnd)
        time.sleep(args.wait)
        previous = bring_to_front(hwnd)
        try:
            rect = client_screen_rect(hwnd)
            print("client rect on screen: %s" % (rect,))
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            ok, note = capture(rect, args.out)
        finally:
            restore_foreground(previous)
        if not ok:
            print("capture failed: %s" % note)
            return 1
        print("captured %s" % args.out)
        if args.keys:
            user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)
            time.sleep(1.5)
            second = args.out.replace(".png", "_2.png")
            ok, note = capture(client_screen_rect(hwnd), second)
            print("captured %s (%s)" % (second, note))
        report(args.out, args.step)
        return 0
    finally:
        if hwnd is not None:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()


if __name__ == "__main__":
    sys.exit(main())
