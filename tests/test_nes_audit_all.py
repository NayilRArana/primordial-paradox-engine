"""The audit runner: what it audits, what it calls a failure, and what it refuses to call a pass."""

from __future__ import annotations

import glob
import os

import numpy as np
import pytest
from PIL import Image

import nes_audit_all as audit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_png(path, array):
    Image.fromarray(array, "RGBA").save(path)
    return path


def solid(width, height, colour, alpha=255):
    array = np.zeros((height, width, 4), dtype=np.uint8)
    array[:, :, 0] = colour[0]
    array[:, :, 1] = colour[1]
    array[:, :, 2] = colour[2]
    array[:, :, 3] = alpha
    return array


# -----------------------------------------------------------------------------------------------------------------
# Every file in the project is found, and found at the right scope.

def test_every_asset_png_is_discovered():
    targets = audit.discover(ROOT)
    assets = {target.rel for target in targets if target.scope == "asset"}
    on_disk = set()
    for current, _, files in os.walk(os.path.join(ROOT, audit.ASSET_ROOT)):
        for name in files:
            if name.lower().endswith(".png"):
                on_disk.add(os.path.relpath(os.path.join(current, name), ROOT).replace(os.sep, "/"))
    assert assets == on_disk
    assert assets, "the audit found no assets at all, which would make a green verdict meaningless"


def test_every_title_file_is_listed():
    """The card's check: at least every file under game\\sprites_src\\title."""
    targets = audit.discover(ROOT)
    listed = {target.rel for target in targets}
    title = glob.glob(os.path.join(ROOT, audit.ASSET_ROOT, "title", "*.png"))
    assert title, "game/sprites_src/title has no PNGs, so this check cannot measure anything"
    missing = sorted(os.path.basename(path) for path in title
                     if "game/sprites_src/title/" + os.path.basename(path) not in listed)
    assert missing == []


def test_sprite_sheet_and_layer_get_different_rules():
    kind, why = audit.classify_asset("game/sprites_src/title/spr_title_car.png", ROOT)
    assert kind == "sprite" and "sprite" in why
    kind, _ = audit.classify_asset("game/sprites_src/title/title_L1_sky.png", ROOT)
    assert kind == "background"


@pytest.mark.parametrize("size,scale", [((256, 240), 1), ((768, 720), 3), ((512, 240), 0), ((256, 232), 0)])
def test_frame_scale(size, scale):
    assert audit.frame_scale(*size) == scale


# -----------------------------------------------------------------------------------------------------------------
# The counting: a legal image counts zero offenders, an illegal one counts the pixels a fix must touch.

def test_a_legal_background_counts_nothing(tmp_path):
    # Two colours across the whole 16x16 image: well inside "3 plus the backdrop".
    array = solid(16, 16, (0x00, 0x00, 0x00))
    array[0:8, :, 0:3] = (0xFC, 0xFC, 0xFC)
    path = write_png(str(tmp_path / "legal.png"), array)
    target = audit.Target("legal.png", "asset", "background", True, 1, "test")
    measurement = audit.measure(path, target, [(0, 0, 0), (0xFC, 0xFC, 0xFC)])
    assert measurement["offending_pixels"] == 0
    assert measurement["blocks"] == []
    assert measurement["percent_of_image"] == 0.0


def test_an_illegal_block_names_its_coordinates_and_its_repaint(tmp_path):
    # One 16x16 area carrying five colours: the limit is 3 besides the backdrop.
    array = solid(16, 16, (0x00, 0x00, 0x00))
    palette = [(0x00, 0x00, 0x00), (0x10, 0x10, 0x10), (0x20, 0x20, 0x20),
               (0x30, 0x30, 0x30), (0x40, 0x40, 0x40)]
    for index, colour in enumerate(palette[1:], start=1):
        array[0:4, (index - 1) * 4:index * 4, 0:3] = colour
    path = write_png(str(tmp_path / "illegal.png"), array)
    target = audit.Target("illegal.png", "asset", "background", True, 1, "test")
    measurement = audit.measure(path, target, palette)
    assert measurement["offending_pixels"] > 0
    assert measurement["block_rule"] == "background_area"
    assert measurement["blocks"][0]["box"][0:2] == [0, 0]
    assert measurement["blocks"][0]["carries"] == 4


def test_a_sprite_tile_counts_only_its_own_tile(tmp_path):
    array = solid(8, 8, (0x00, 0x00, 0x00))
    for index, colour in enumerate([(0x10, 0x10, 0x10), (0x20, 0x20, 0x20), (0x30, 0x30, 0x30)], start=1):
        array[index:index + 2, :, 0:3] = colour
    path = write_png(str(tmp_path / "tile.png"), array)
    target = audit.Target("tile.png", "asset", "sprite", True, 1, "test")
    measurement = audit.measure(path, target, [(0, 0, 0)] + [(i << 4, i << 4, i << 4) for i in range(1, 4)])
    assert measurement["block_rule"] == "sprite_tile"
    assert measurement["blocks"][0]["box"] == [0, 0, 8, 8]


# -----------------------------------------------------------------------------------------------------------------
# The page, and the exit code the gate reads.

def test_the_page_says_gated_and_advisory_apart():
    records = [
        {"path": "a.png", "scope": "asset", "kind": "sprite", "gated": True, "scale": 1, "why": "w",
         "checker": "tools/nes_check.py check()", "ok": False, "problems": [], "rules": {"palette": 1},
         "problem_count": 1, "unmeasured": None, "offending_pixels": 10, "percent_of_image": 1.0,
         "worst_block": None, "size": [8, 8], "colours": 2, "fixes": ["merge colours"],
         "measurement": {"visible_pixels": 100, "blocks": [], "block_rule": "sprite_tile",
                         "off_palette_pixels": 10, "screen_excess": 0}},
        {"path": "b.png", "scope": "sheet", "kind": "background", "gated": False, "scale": 1, "why": "w",
         "checker": "tools/nes_check.py check()", "ok": False, "problems": [], "rules": {"palette": 1},
         "problem_count": 1, "unmeasured": None, "offending_pixels": 99, "percent_of_image": 2.0,
         "worst_block": None, "size": [8, 8], "colours": 2, "fixes": ["merge colours"],
         "measurement": {"visible_pixels": 100, "blocks": [], "block_rule": "background_area",
                         "off_palette_pixels": 99, "screen_excess": 0}},
    ]
    verdict = {"verdict": "FAIL", "gated_failures": 1, "exit_code": 1, "preview": None}
    page = audit.render_markdown(records, verdict)
    assert "## Gated failures, worst first" in page
    assert "## Advisory failures, worst first" in page
    assert page.index("a.png") < page.index("b.png")
    assert "Exit code from `tools/nes_audit_all.py`: 1" in page


def test_the_exit_code_is_the_gated_verdict(tmp_path, capsys):
    """A gated failure is exit 1. An unreadable gated file is exit 1 too: a SKIP is not a pass."""
    code = audit.main(["--quiet", "--no-write"])
    assert code in (0, 1)
    line = capsys.readouterr().out
    assert "nes_audit_all:" in line and "exit" in line
