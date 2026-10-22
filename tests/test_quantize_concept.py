"""Tests for tools/quantize_concept.py (card PAL-SYSTEM, 2026-10-22).

RULE 0 point 5 says concept art is accepted only after it survives quantisation to the scene's set. So the
tests are the two ends of that: a colour already in the set must come back unchanged (delta E 0), and a
picture full of ordinary 24 bit colour must come back with every pixel on a scene entry and a delta E that
says how much was lost. The files written next to the source are checked by name, and the source is checked
by hash so a run can never quietly overwrite the artist's original.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import quantize_concept  # noqa: E402
import scene_palette_set  # noqa: E402

COLOURS, USABLE, _ = scene_palette_set.load_master(ROOT)


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def concept_image(path, size=(32, 32)):
    """A small picture of ordinary 24 bit colour: a gradient with a blob on it. Nothing here is a NES colour on
    purpose, which is what concept art looks like before it is quantised."""
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (x * 7 % 256, y * 7 % 256, (x + y) * 3 % 256)
    image.save(path)
    return path


def test_delta_e_is_zero_for_a_colour_against_itself_and_grows_with_distance():
    assert quantize_concept.delta_e((10, 120, 200), (10, 120, 200)) == 0.0
    near = quantize_concept.delta_e((0, 0, 0), (40, 40, 40))
    far = quantize_concept.delta_e((0, 0, 0), (255, 255, 255))
    assert 0.0 < near < far
    # White and black are about 100 apart in CIE76 lightness, which is the anchor for the scale.
    assert 95.0 < far < 105.0, far


def test_a_colour_inside_the_set_survives_unchanged():
    scene = scene_palette_set.scene(ROOT, "title")
    inside = scene.rgb(scene.background[0][0])
    image = Image.new("RGBA", (16, 16), inside + (255,))
    out, stats = quantize_concept.quantise(image, scene)
    assert stats["mean_delta_e"] == 0.0
    assert stats["changed"] == 0
    assert out.getpixel((0, 0)) == inside + (255,)


def test_every_pixel_of_a_quantised_picture_is_on_a_scene_entry():
    scene = scene_palette_set.scene(ROOT, "title")
    allowed = scene.bg_colours() | scene.sprite_colours() | {scene.backdrop}
    image = Image.new("RGB", (16, 16))
    pixels = image.load()
    for y in range(16):
        for x in range(16):
            pixels[x, y] = (x * 15, y * 15, (x * y) % 256)
    out, stats = quantize_concept.quantise(image.convert("RGBA"), scene)
    for y in range(16):
        for x in range(16):
            entry = scene.entry_of(out.getpixel((x, y))[:3])
            assert entry in allowed, "pixel %d,%d is %s, not a scene entry" % (x, y, out.getpixel((x, y)))
    assert stats["mean_delta_e"] > 0.0
    assert stats["colours_after"] <= stats["colours_before"]
    assert stats["colours_after"] <= stats["allowed_entries"]


def test_transparent_pixels_stay_transparent():
    scene = scene_palette_set.scene(ROOT, "title")
    image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    image.putpixel((0, 0), tuple(scene.rgb(scene.background[0][0])) + (255,))
    out, stats = quantize_concept.quantise(image, scene)
    assert out.getpixel((4, 4))[3] == 0
    assert stats["pixels"] == 1


def test_convert_writes_the_suffixed_png_and_the_sheet_and_leaves_the_source_alone(tmp_path):
    scene = scene_palette_set.scene(ROOT, "title")
    source = concept_image(str(tmp_path / "thames.png"))
    before = digest(source)
    stats = quantize_concept.convert(ROOT, source, "title")
    assert digest(source) == before, "the source PNG was modified"
    assert stats["out"].endswith("thames_nes.png")
    assert stats["sheet"].endswith("thames_nes_sheet.png")
    out_path = os.path.join(ROOT, stats["out"])
    sheet_path = os.path.join(ROOT, stats["sheet"])
    assert os.path.isfile(out_path) and os.path.isfile(sheet_path)
    allowed = scene.bg_colours() | scene.sprite_colours() | {scene.backdrop}
    with Image.open(out_path) as image:
        for pixel in image.convert("RGBA").getcolors(maxcolors=1 << 24):
            colour = pixel[1]
            if colour[3]:
                assert scene.entry_of(colour[:3]) in allowed
    with Image.open(sheet_path) as sheet:
        assert sheet.width > 32 and sheet.height > 32


def test_an_image_that_loses_too_much_colour_is_rejected(tmp_path):
    source = concept_image(str(tmp_path / "thames.png"))
    stats = quantize_concept.convert(ROOT, source, "title", max_delta_e=0.5)
    assert stats["accepted"] is False
    assert stats["mean_delta_e"] > 0.5


def test_ordered_dither_is_off_by_default_and_honoured_when_asked(tmp_path):
    source = concept_image(str(tmp_path / "thames.png"))
    plain = quantize_concept.convert(ROOT, source, "title")
    assert plain["dither"] is False
    dithered = quantize_concept.convert(ROOT, source, "title", dither=True)
    assert dithered["dither"] is True
    with Image.open(os.path.join(ROOT, plain["out"])) as image:
        plain_colours = image.convert("RGB").getcolors(maxcolors=1 << 24)
    with Image.open(os.path.join(ROOT, dithered["out"])) as image:
        dithered_colours = image.convert("RGB").getcolors(maxcolors=1 << 24)
    assert len(dithered_colours) >= len(plain_colours)


def test_cli_runs_on_a_folder_and_writes_json(tmp_path, capsys):
    for name in ("a", "b"):
        concept_image(str(tmp_path / ("%s.png" % name)))
    out = tmp_path / "report.json"
    code = quantize_concept.main([str(tmp_path), "--scene", "title", "--json", str(out),
                                  "--max-delta-e", "100", "--quiet"])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool"] == "quantize_concept"
    assert len(payload["results"]) == 2
    assert all(item["source"].endswith(("a.png", "b.png")) for item in payload["results"])


def test_selftest_passes():
    assert quantize_concept.selftest(ROOT) == 0
