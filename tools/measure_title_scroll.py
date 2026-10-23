#!/usr/bin/env python3
"""measure_title_scroll.py: measure the title's scroll rate from frames grabbed in a fast burst.

Why this exists (card TEMPO-1): the card asks that captured frames differ by the number of pixels the tempo sets.
tools\\capture_title.py --scroll takes its two copies through a PowerShell child, which costs about 7.5 s a frame on
this PC, so its "half a second apart" pair really lands 8 s apart and the road travels 265 px, past its own art
width, which no correlation can resolve.

How this tool gets a real half second: PrintWindow(flag 2) asks the window to render itself into a bitmap, which
costs about 0.23 s here and works while another window is in front. Two things were measured and are why the code
looks the way it does:

* A plain screen copy (ImageGrab of the window rectangle) returns a FROZEN frame when the game window is occluded:
  six copies taken over 0.75 s were byte identical. PrintWindow on the same window at the same moment gives six
  different frames, so it is the only grab used here.
* Raising the window first is not a fix: with the window forced forward, the copy came back showing the window that
  had been in front (322 colours, mean 224, a bright dialog) instead of the night frame (over 700 colours, mean 72).

The road layer repeats every 16 px (one dash a beat), so a half second of travel (16.6 px) sits 0.6 px past a whole
dash and cannot be told from a creep by correlation. The rate is therefore measured on pairs about 0.23 s apart,
where 7.7 px is comfortably inside the dash, and the half second figure is derived from the median pair rate.

Usage: python tools\\measure_title_scroll.py
Exit:  0 when the measured rate is within 15% of the timing file, 1 otherwise.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pp_launch  # noqa: E402  the launch policy: PP_MUTE=1, the idle gate, and the quiet window (card CAPTURE-QUIET)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
OUTPUT = os.path.join(ROOT, "output")
BUILD_DIR = os.path.join(ROOT, "build")
EXE = os.path.join(OUTPUT, "PrimordialParadox", "PrimordialParadox.exe")
WIN = os.path.join(OUTPUT, "PrimordialParadox", "PrimordialParadox.win")
TIMING = os.path.join(ROOT, "data", "title_timing.json")
EVIDENCE_1 = os.path.join(OUTPUT, "title_tempo_1.png")
EVIDENCE_2 = os.path.join(OUTPUT, "title_tempo_2.png")

COPIES = 6          # six copies make five pairs
GAP_S = 0.2         # target spacing; the real spacing is measured per pair
ROAD_TOP_NES = 196  # data\title.json: title_L6_road sits at y 196; the bottom 44 rows carry road, foreground and car
SEARCH_CAPTURED_PX = 40  # 13 NES px at 3x: covers a 0.2 s pair (20 captured px) and stays inside the 16 px dash
MIN_COLOURS = 48  # raw PrintWindow output is the game's own pixels: 76 colours on the night title, mean 73.5
MAX_MEAN = 140.0  # a bright covering window measured 322 colours and mean 224, so darkness is the real discriminator


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


def print_window(hwnd, width, height):
    """Ask the window to render itself into a bitmap. Returns (rgb array, note)."""
    hdc_screen = user32.GetDC(0)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    bitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    gdi32.SelectObject(hdc, bitmap)
    ok = user32.PrintWindow(hwnd, hdc, 2)
    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    lines = gdi32.GetDIBits(hdc, bitmap, 0, height, buffer, ctypes.byref(header), 0)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(hdc)
    user32.ReleaseDC(0, hdc_screen)
    if not ok or lines == 0:
        return None, "PrintWindow=%s GetDIBits=%s" % (ok, lines)
    array = np.frombuffer(buffer.raw, dtype=np.uint8).reshape(height, width, 4)
    return array[:, :, :3].copy(), "ok"


def find_game_window(pid, timeout_s=20.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
        def callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            title = ctypes.create_unicode_buffer(128)
            user32.GetWindowTextW(hwnd, title, 128)
            owner = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if "Primordial Paradox" in title.value and owner.value == pid:
                found.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        if found:
            return found[0]
        time.sleep(0.25)
    return 0


def frame_gate(array):
    """A night frame of the title: many colours, dark on average."""
    flat = array.reshape(-1, 3)
    colours = len(np.unique(flat, axis=0))
    mean = float(array.mean())
    return colours >= MIN_COLOURS and mean <= MAX_MEAN, "colours=%d mean=%.1f" % (colours, mean)


def band_shift(a, b, limit):
    """Horizontal shift of b relative to a, in captured pixels, by minimum mean absolute difference."""
    _h, w = a.shape
    best_score, best_shift = None, None
    for d in range(-limit, limit + 1):
        if d >= 0:
            left_a, left_b, width = d, 0, w - d
        else:
            left_a, left_b, width = 0, -d, w + d
        if width < w // 2:
            continue
        score = float(np.abs(a[:, left_a:left_a + width].astype(np.int16)
                             - b[:, left_b:left_b + width].astype(np.int16)).mean())
        if best_score is None or score < best_score:
            best_score, best_shift = score, d
    return best_shift, best_score


def row_shifts(a, b, limit, min_score=1.0):
    """Shift per scanline, then the median of the scanlines that have a clear match.

    A single band over the road holds three layers at different speeds (the road at 1.0, the foreground
    verge at 1.3) plus the car, which is fixed to the screen; averaging them finds no common shift. Each
    scanline belongs to one layer, so the scanlines answer separately and the median over them is the
    road's own rate.
    """
    h, w = a.shape
    answers = []
    for y in range(h):
        row_a, row_b = a[y], b[y]
        best_score, best_shift = None, 0
        for d in range(-limit, limit + 1):
            if d >= 0:
                sa, sb = row_a[d:], row_b[:w - d]
            else:
                sa, sb = row_a[:w + d], row_b[-d:]
            if sa.size < w // 2:
                continue
            score = float(np.abs(sa.astype(np.int16) - sb.astype(np.int16)).mean())
            if best_score is None or score < best_score:
                best_score, best_shift = score, d
        if best_score is not None and best_score <= min_score:
            answers.append(best_shift)
    if not answers:
        return None, 0
    answers.sort()
    return answers[len(answers) // 2], len(answers)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # gate: ok Best-effort: without it the copy is scaled, and the scale is measured anyway.
        pass
    user32.SetProcessDPIAware()

    with open(TIMING, "r", encoding="utf-8") as handle:
        timing = json.load(handle)
    base_rate = timing["scroll"]["px_per_step"] * timing["fps"]
    print("timing file: bpm %s, %.3f px a step at %s fps, so the base road rate is %.1f NES px/s (%.1f px in 0.5 s)" % (
        timing["bpm"], timing["scroll"]["px_per_step"], timing["fps"], base_rate, base_rate * 0.5))

    if not os.path.isfile(EXE) or not os.path.isfile(WIN):
        print("no built game at %s" % EXE)
        return 1

    # Card CAPTURE-QUIET: no window while the user is at the PC, and PP_MUTE=1 so nothing plays.
    if not pp_launch.Policy().gate("scroll measurement"):
        return pp_launch.EXIT_REFUSED

    os.makedirs(BUILD_DIR, exist_ok=True)
    log_path = os.path.join(BUILD_DIR, "measure-scroll-game.log")
    game_log = open(log_path, "wb")
    process = subprocess.Popen(
        [EXE, "-game", WIN], cwd=os.path.dirname(EXE),
        stdin=subprocess.DEVNULL, stdout=game_log, stderr=subprocess.STDOUT,
        # Card CAPTURE-QUIET: PP_MUTE=1, this is not an audio proof.
        env=pp_launch.game_env(),
    )
    try:
        hwnd = find_game_window(process.pid)
        if not hwnd:
            print("the game window did not appear")
            return 1
        # Card CAPTURE-QUIET: off the primary screen, so the window is not in his face.
        pp_launch.place_window_quietly(hwnd)
        time.sleep(3.0)
        # The game keeps its window on the desktop but stops drawing to it while it is not the active window, so
        # PrintWindow on a background window returns the last frame before the focus went away (measured: five
        # copies 0.2 s apart were identical). Bringing it forward for the length of the burst is the only way the
        # copies show the title running.
        user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        time.sleep(1.0)
        focused = bool(user32.GetForegroundWindow() == hwnd)
        print("window brought to the front: %s" % ("yes" if focused else "no, Windows refused the focus"))
        client = wt.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(client))
        width, height = client.right, client.bottom
        scale = min(round(width / 256.0), round(height / 240.0)) or 1
        print("client %dx%d drawn at %dx (NES frame %dx%d)" % (
            width, height, scale, width // scale, height // scale))

        frames, stamps = [], []
        target = time.time()
        for _index in range(COPIES):
            delay = target - time.time()
            if delay > 0:
                time.sleep(delay)
            array, note = print_window(hwnd, width, height)
            if array is None:
                print("PrintWindow failed: %s" % note)
                return 1
            stamps.append(time.time())
            frames.append(array)
            target += GAP_S

        ok, note = frame_gate(frames[0])
        print("frame gate: %s (%s)" % ("night frame" if ok else "NOT the game", note))
        if not ok:
            Image.fromarray(frames[0]).save(os.path.join(OUTPUT, "_measure_bad_frame.png"))
            print("the copy did not show the game; nothing is measured")
            return 1
        Image.fromarray(frames[0]).save(EVIDENCE_1)
        Image.fromarray(frames[-1]).save(EVIDENCE_2)
        print("saved %s and %s (first and last copy)" % (EVIDENCE_1, EVIDENCE_2))

        grey = [frame.mean(axis=2) for frame in frames]
        top = ROAD_TOP_NES * scale
        rates = []
        print("")
        print("pair | gap (s) | road shift (captured) | (NES) | rate (NES px/s)")
        for index in range(1, COPIES):
            gap = stamps[index] - stamps[index - 1]
            shot_a = grey[index - 1][top:]
            shot_b = grey[index][top:]
            shift, agreed = row_shifts(shot_a, shot_b, SEARCH_CAPTURED_PX)
            shift = 0 if shift is None else shift
            nes = shift / scale
            rate = nes / gap if gap else 0.0
            rates.append(rate)
            print("%4d | %7.3f | %21d | %5.1f | %14.1f  (%d scanlines agreed)" % (
                index, gap, shift, nes, rate, agreed))
        band, _score = band_shift(grey[-1][top:], grey[0][top:], SEARCH_CAPTURED_PX)
        print("whole band, last to first copy: %s px captured" % band)
        positive = sorted(rate for rate in rates if rate > 0)
        if not positive:
            print("no pair showed movement")
            return 1
        median = positive[len(positive) // 2]
        print("")
        print("pairs with movement: %d of %d" % (len(positive), len(rates)))
        print("median rate: %.1f NES px/s (expected %.1f), so %.1f px in 0.5 s (expected %.1f)" % (
            median, base_rate, median * 0.5, base_rate * 0.5))
        error = abs(median - base_rate) / base_rate * 100.0
        print("difference from the tempo: %.1f%%" % error)

        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        deadline = time.time() + 5.0
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort: the log is read from disk just below.
            pass
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        theme = [line.strip() for line in text.splitlines() if "title_theme streaming" in line]
        print("audio: %s" % (theme[0] if theme else "no theme stream line in %s" % log_path))
        if "PP CRASH" in text:
            print("the game reported a crash")
            return 1
        return 0 if error <= 15.0 else 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
        try:
            game_log.close()
        except Exception:  # gate: ok Best-effort cleanup.
            pass


if __name__ == "__main__":
    sys.exit(main())
