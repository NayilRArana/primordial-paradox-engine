"""Checks for the tools that judge a whole composed frame against the NES palette rules."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from PIL import Image

import nes_composite_check

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = TOOLS


def run(*args):
    result = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, cwd=ROOT, stdin=subprocess.DEVNULL)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def test_legal_frame_passes(tmp_path):
    """Two NES colours in flat 16x16 areas, backdrop elsewhere: legal, so exit 0."""
    frame = Image.new("RGB", (256, 240), (0, 0, 0))
    for y in range(0, 48):
        for x in range(0, 48):
            frame.putpixel((x, y), (0x00, 0x78, 0xF8) if (x // 8 + y // 8) % 2 else (0xF8, 0xF8, 0xF8))
    path = tmp_path / "legal.png"
    frame.save(path)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(path))
    assert code == 0, text
    assert "PASS" in text


def test_five_palettes_fail(tmp_path):
    """Five unrelated colour pairs is more than four background palettes, so the frame is impossible."""
    pairs = [((0x00, 0x78, 0xF8), (0xF8, 0xF8, 0xF8)),
             ((0x00, 0x68, 0x00), (0x00, 0x58, 0x00)),
             ((0x88, 0x14, 0x00), (0xF8, 0x38, 0x00)),
             ((0x00, 0xBC, 0x00), (0xF8, 0xB8, 0x00)),
             ((0x94, 0x00, 0x3C), (0x3C, 0xBC, 0xFC))]
    frame = Image.new("RGB", (256, 240), (0, 0, 0))
    for index, (first, second) in enumerate(pairs):
        for y in range(index * 16, index * 16 + 16):
            for x in range(0, 240):
                frame.putpixel((x, y), first if (x // 8) % 2 else second)
    path = tmp_path / "five.png"
    frame.save(path)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(path))
    assert code == 1, text
    assert "FAIL" in text


def test_scene_palettes_declare_the_ppu_budget():
    """Both scene files declare 4 background and 4 sprite palettes of three usable entries each."""
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        master = json.load(handle)
    usable = master.get("usable") or [True] * len(master["colours"])
    for name in ("scene_title", "scene_ship"):
        path = os.path.join(ROOT, "data", "palettes", name + ".json")
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert len(payload["background"]) == 4
        assert len(payload["sprites"]) == 4
        for row in payload["background"] + payload["sprites"]:
            assert len(row["colours"]) == 3
            for entry in row["colours"]:
                assert 0 <= entry < 64
                assert usable[entry], "%s uses forbidden entry $%02X" % (name, entry)
        assert usable[payload["backdrop"]]


def build_legal_frame():
    """256x240 in the shared backdrop, with one legal 3 colour block painted in its top left corner."""
    frame = Image.new("RGB", (256, 240), (0x00, 0x00, 0x00))
    colours = [(0x00, 0x78, 0xF8), (0xF8, 0xF8, 0xF8), (0x00, 0x58, 0x00)]
    for y in range(0, 16):
        for x in range(0, 16):
            frame.putpixel((x, y), colours[(x // 4 + y // 4) % 3])
    return frame


def test_three_x_capture_is_downsampled_and_passes(tmp_path):
    """A 768x720 nearest neighbour capture of a legal frame reads at scale 3 and passes."""
    big = build_legal_frame().resize((768, 720), Image.Resampling.NEAREST)
    path = tmp_path / "capture3x.png"
    big.save(path)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(path), "--crop", "3")
    assert code == 0, text
    assert "read at scale 3" in text


def test_one_off_palette_pixel_fails(tmp_path):
    """A single colour that is not a PPU output makes the frame impossible, so exit 1."""
    frame = build_legal_frame()
    frame.putpixel((200, 200), (0x7B, 0x7B, 0x7B))
    path = tmp_path / "offpalette.png"
    frame.save(path)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(path))
    assert code == 1, text
    assert "[palette]" in text
    assert "#7b7b7b" in text


def test_four_background_palettes_are_enough(tmp_path):
    """Four blocks in four unrelated 3 colour palettes fit four groups, so the frame passes."""
    frame = Image.new("RGB", (256, 240), (0x00, 0x00, 0x00))
    palettes = [[(0x00, 0x78, 0xF8), (0xF8, 0xF8, 0xF8), (0x00, 0x58, 0x00)],
                [(0x00, 0x68, 0x00), (0x88, 0x14, 0x00), (0xF8, 0x38, 0x00)],
                [(0x00, 0x58, 0xF8), (0xF8, 0xB8, 0x00), (0xA8, 0x00, 0x20)],
                [(0x68, 0x44, 0xFC), (0xD8, 0x00, 0xCC), (0xE4, 0x5C, 0x10)]]
    for index, palette in enumerate(palettes):
        for y in range(0, 16):
            for x in range(index * 16, index * 16 + 16):
                frame.putpixel((x, y), palette[(x // 4 + y // 4) % 3])
    path = tmp_path / "four_palettes.png"
    frame.save(path)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(path))
    assert code == 0, text
    assert "PASS" in text


def sprite_frame(colours, boxes):
    """A backdrop frame with each box painted at its own colour list, cycling."""
    frame = Image.new("RGB", (256, 240), (0x00, 0x00, 0x00))
    for box, palette in zip(boxes, colours):
        x0, y0, w, h = box
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                frame.putpixel((x, y), palette[((x - x0) // 2 + (y - y0) // 2) % len(palette)])
    return frame


def write_sprites(path, boxes, transparent=None):
    payload = {"sprites": [{"x": x, "y": y, "w": w, "h": h} for x, y, w, h in boxes]}
    if transparent is not None:
        for entry in payload["sprites"]:
            entry["transparent"] = transparent
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle)
    return path


def test_sprite_with_four_colours_fails(tmp_path):
    """One 8x8 sprite drawn in 4 colours is impossible: a sprite group holds 3 plus transparency."""
    boxes = [(0, 0, 8, 8)]
    colours = [[(0x00, 0x00, 0x00), (0xF8, 0xF8, 0xF8), (0x00, 0x78, 0xF8), (0xF8, 0x38, 0x00)]]
    frame = sprite_frame(colours, boxes)
    frame_path = tmp_path / "sprite4.png"
    frame.save(frame_path)
    list_path = write_sprites(tmp_path / "sprites.json", boxes)
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(frame_path), "--sprites", str(list_path))
    assert code == 1, text
    assert "sprite 0" in text and "4 colours" in text


def test_sprite_with_three_colours_and_transparency_passes(tmp_path):
    """Three opaque colours plus a declared transparent colour is a legal sprite."""
    boxes = [(0, 0, 8, 8)]
    colours = [[(0x00, 0x00, 0x00), (0xF8, 0xF8, 0xF8), (0x00, 0x78, 0xF8), (0xF8, 0x38, 0x00)]]
    frame = sprite_frame(colours, boxes)
    frame_path = tmp_path / "sprite3.png"
    frame.save(frame_path)
    list_path = write_sprites(tmp_path / "sprites_ok.json", boxes, transparent="#000000")
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(frame_path), "--sprites", str(list_path))
    assert code == 0, text
    assert "PASS" in text


def test_nine_sprites_on_one_scanline_fail(tmp_path):
    """The PPU drops sprites after the eighth on a scanline, so nine on one line is a violation."""
    boxes = [(index * 8, 0, 8, 8) for index in range(9)]
    colours = [[(0x00, 0x00, 0x00), (0xF8, 0xF8, 0xF8)]] * 9
    frame = sprite_frame(colours, boxes)
    frame_path = tmp_path / "nine.png"
    frame.save(frame_path)
    list_path = write_sprites(tmp_path / "nine.json", boxes, transparent="#000000")
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(frame_path), "--sprites", str(list_path))
    assert code == 1, text
    assert "scanline" in text


def test_eight_sprites_on_one_scanline_pass(tmp_path):
    """Eight is exactly what the hardware draws."""
    boxes = [(index * 8, 0, 8, 8) for index in range(8)]
    colours = [[(0x00, 0x00, 0x00), (0xF8, 0xF8, 0xF8)]] * 8
    frame = sprite_frame(colours, boxes)
    frame_path = tmp_path / "eight.png"
    frame.save(frame_path)
    list_path = write_sprites(tmp_path / "eight.json", boxes, transparent="#000000")
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(frame_path), "--sprites", str(list_path))
    assert code == 0, text


def test_sixty_five_sprites_fail(tmp_path):
    """OAM holds 64 entries, so 65 sprites cannot all be drawn."""
    boxes = [(index % 8 * 8, index // 8 * 16, 8, 8) for index in range(65)]
    colours = [[(0x00, 0x00, 0x00), (0xF8, 0xF8, 0xF8)]] * 65
    frame = sprite_frame(colours, boxes)
    frame_path = tmp_path / "many.png"
    frame.save(frame_path)
    list_path = write_sprites(tmp_path / "many.json", boxes, transparent="#000000")
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(frame_path), "--sprites", str(list_path))
    assert code == 1, text
    assert "65 sprites" in text


def test_five_sprite_palettes_fail():
    """Four sprite groups, so five unrelated 3 colour sets cannot be drawn."""
    sets = [[(0x00, 0x78, 0xF8), (0xF8, 0xF8, 0xF8), (0x00, 0x58, 0x00)],
            [(0x00, 0x68, 0x00), (0x88, 0x14, 0x00), (0xF8, 0x38, 0x00)],
            [(0x00, 0x58, 0xF8), (0xF8, 0xB8, 0x00), (0xA8, 0x00, 0x20)],
            [(0x68, 0x44, 0xFC), (0xD8, 0x00, 0xCC), (0xE4, 0x5C, 0x10)],
            [(0x7C, 0x7C, 0x7C), (0xBC, 0xBC, 0xBC), (0x00, 0x40, 0x58)]]
    sprites = [{"box": [0, i * 16, 8, 8], "colours": sorted(value)} for i, value in enumerate(sets)]
    report = nes_composite_check.check_sprites(sprites)
    rules = [problem["rule"] for problem in report["problems"]]
    assert "sprite_palettes" in rules, report
    detail = [problem["detail"] for problem in report["problems"] if problem["rule"] == "sprite_palettes"][0]
    assert "4" in detail, detail


def test_enforce_turns_a_noisy_frame_into_a_legal_one(tmp_path):
    """The enforcer rewrites any frame, and the checker then passes its output."""
    import random
    rng = random.Random(20261021)
    master = nes_composite_check.load_palette(
        nes_composite_check.default_palette_path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    vocabulary = sorted(master["allowed"])
    frame = Image.new("RGB", (256, 240))
    for y in range(240):
        for x in range(256):
            frame.putpixel((x, y), rng.choice(vocabulary))
    source = tmp_path / "noise.png"
    frame.save(source)
    out = tmp_path / "noise_nes.png"
    code, text = run(os.path.join("tools", "nes_enforce.py"), str(source), "--out", str(out),
                     "--diff", str(tmp_path / "noise_diff.png"), "--quiet")
    assert code == 0, text
    assert "after 0 offending blocks" in text, text
    assert out.is_file()
    code, text = run(os.path.join("tools", "nes_composite_check.py"), str(out))
    assert code == 0, text


def test_enforce_output_is_stable_under_a_second_pass(tmp_path):
    """Enforcing an already legal frame changes nothing, so the filter is a fixed point."""
    source = tmp_path / "legal.png"
    build_legal_frame().save(source)
    first = tmp_path / "pass1.png"
    code, text = run(os.path.join("tools", "nes_enforce.py"), str(source), "--out", str(first),
                     "--diff", str(tmp_path / "d1.png"), "--quiet")
    assert code == 0, text
    second = tmp_path / "pass2.png"
    code, text = run(os.path.join("tools", "nes_enforce.py"), str(first), "--out", str(second),
                     "--diff", str(tmp_path / "d2.png"), "--quiet")
    assert code == 0, text
    with Image.open(first) as a, Image.open(second) as b:
        assert a.convert("RGB").tobytes() == b.convert("RGB").tobytes()
