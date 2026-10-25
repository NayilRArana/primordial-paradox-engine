"""Pins for the intro capture gate (card INTRO-1-PROOF): a copy is only saved when it is the game's own screen.

What these tests hold down, and why each one earns its place:
  1. a window copy that carries the game's 3x viewport passes the NES test the capture now runs, and the box it
     finds is the measured one, [8, 31, 768, 720] inside a 784x759 window;
  2. a copy of a terminal or of the desktop is refused, because no box inside it is made of legal 2C02 colours,
     which is exactly the mistake the first --intro pass saved as four frames;
  3. the saving gate really gates: with the copy stubbed to a terminal picture the frame is not written, and with
     it stubbed to a game picture the frame is written and carries its score;
  4. the card's four timestamps are still 1, 4, 8 and 14 s, and the score threshold sits between the measurements
     (a terminal scores 0.000, the real window capture measured 0.986).

Run: python -m pytest tests/test_capture_title.py -q
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile

import pytest
from PIL import Image

# Card TEST-CLASSIFY-33: every test in this module loads tools/capture_title.py, which binds
# ctypes.windll.user32 at module level (line 128), so on a Linux host the import raises
# AttributeError before a line of any test runs. The marker is a skip there, never a pass.
pytestmark = pytest.mark.windows_only

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
WINDOW = (784, 759)
VIEWBOX = (8, 31, 768, 720)
# A colour no NES PPU can output. The window border and the terminal are painted with it, so nothing outside the
# game box can be mistaken for the screen.
FOREIGN = (7, 7, 7)


def load(name: str):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def palette():
    ncc = load("nes_composite_check")
    return ncc.load_palette(ncc.default_palette_path(ROOT))


def write_game_capture(path: str) -> None:
    """A window capture of the game: illegal border, and a 768x720 box of legal PPU colours at [8, 31]."""
    # load_palette returns {"allowed": {rgb: (index, hex), ...}, ...}, so read the colours back in
    # palette-index order instead of slicing the mapping. Index 0 is the background and is skipped,
    # which is what [1:16] always meant here.
    allowed = palette()["allowed"]
    colours = sorted(allowed, key=lambda rgb: allowed[rgb][0])[1:16]
    image = Image.new("RGB", WINDOW, FOREIGN)
    x0, y0, w, h = VIEWBOX
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            block = Image.new("RGB", (8, 8), colours[(tx // 8 + ty // 8) % len(colours)])
            image.paste(block, (x0 + tx, y0 + ty))
    image.save(path, "PNG")


def write_terminal_capture(path: str) -> None:
    """A copy of a terminal: dark navy panes and light text, none of it a legal PPU colour."""
    image = Image.new("RGB", WINDOW, (9, 9, 24))
    for row in range(40, 700, 22):
        for column in range(40, 700, 9):
            if (row // 22 + column // 9) % 3:
                image.paste((197, 190, 229), (column, row, column + 6, row + 12))
    image.save(path, "PNG")


def test_a_game_window_copy_passes_the_nes_check():
    capture = load("capture_title")
    scratch = tempfile.mkdtemp(prefix="pp_capture_")
    try:
        path = os.path.join(scratch, "game.png")
        write_game_capture(path)
        box, score, note = capture.viewport_box_and_score(path)
        assert box == list(VIEWBOX), (box, note)
        assert score >= capture.INTRO_VIEWPORT_MIN_SCORE, score
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_a_terminal_copy_is_refused():
    capture = load("capture_title")
    scratch = tempfile.mkdtemp(prefix="pp_capture_")
    try:
        path = os.path.join(scratch, "terminal.png")
        write_terminal_capture(path)
        box, score, note = capture.viewport_box_and_score(path)
        assert box is None, (box, note)
        assert score < capture.INTRO_VIEWPORT_MIN_SCORE, score
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_the_frame_is_not_saved_when_the_copy_is_not_the_game():
    capture = load("capture_title")
    scratch = tempfile.mkdtemp(prefix="pp_capture_")
    saved = {name: getattr(capture, name) for name in
             ("ensure_key_focus", "capture_with_pil", "capture_with_powershell", "get_window_rect")}
    try:
        out = os.path.join(scratch, "intro_9.png")

        def stub_focus(hwnd, attempts=8, settle=0.3):
            return True, "stub"

        def stub_pil(rect, path):
            write_terminal_capture(path)
            return True, "stub"

        capture.ensure_key_focus = stub_focus
        capture.capture_with_pil = stub_pil
        capture.capture_with_powershell = lambda rect, path: (False, "stub")
        capture.get_window_rect = lambda hwnd: (0, 0) + WINDOW

        rect, box, score, route, taken, cost = capture.capture_intro_frame(0, out, 1.0, __import__("time").time())
        assert rect is None, (rect, box, score, route)
        assert box is None and score == 0.0, (box, score)
        assert not os.path.isfile(out), "a copy that is not the game was left on disk"
    finally:
        for name, value in saved.items():
            setattr(capture, name, value)
        shutil.rmtree(scratch, ignore_errors=True)


def test_the_frame_is_saved_when_the_copy_is_the_game():
    capture = load("capture_title")
    scratch = tempfile.mkdtemp(prefix="pp_capture_")
    saved = {name: getattr(capture, name) for name in
             ("ensure_key_focus", "capture_with_pil", "capture_with_powershell", "get_window_rect")}
    try:
        out = os.path.join(scratch, "intro_1.png")

        def stub_pil(rect, path):
            write_game_capture(path)
            return True, "stub"

        capture.ensure_key_focus = lambda hwnd, attempts=8, settle=0.3: (True, "stub")
        capture.capture_with_pil = stub_pil
        capture.capture_with_powershell = lambda rect, path: (False, "stub")
        capture.get_window_rect = lambda hwnd: (0, 0) + WINDOW

        rect, box, score, route, taken, cost = capture.capture_intro_frame(0, out, 1.0, __import__("time").time())
        assert rect == (0, 0) + WINDOW, rect
        assert box == list(VIEWBOX), box
        assert score >= capture.INTRO_VIEWPORT_MIN_SCORE, score
        assert route == "PIL", route
        assert os.path.isfile(out), "a good copy was not written"
        assert Image.open(out).size == WINDOW
    finally:
        for name, value in saved.items():
            setattr(capture, name, value)
        shutil.rmtree(scratch, ignore_errors=True)


def test_the_threshold_sits_between_the_two_measurements():
    capture = load("capture_title")
    assert capture.INTRO_TIMES == (1.0, 4.0, 8.0, 14.0)
    # Measured on this PC: a terminal copy scores 0.000, the real window capture of the title 0.986.
    assert 0.0 < capture.INTRO_VIEWPORT_MIN_SCORE <= 0.986, capture.INTRO_VIEWPORT_MIN_SCORE
    assert capture.INTRO_VIEWPORT_MIN_SCORE >= 0.90, capture.INTRO_VIEWPORT_MIN_SCORE
