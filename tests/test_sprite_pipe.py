"""Tests for tools\\sprite_pipe.py, CHAR-PIPE: concept art to NES legal overworld and battle sheets.

Every test uses a synthetic concept image (circles and blocks) drawn here, so the suite needs no art, no model,
no key and no network. What is measured, and why:

    geometry      the two sheets are the sizes the card names, on the 8x8 grid nes_check requires
    palette       every opaque pixel is a 2C02 output, alpha is 0 or 255 only (nes_check fails partial alpha)
    constraint    every 8x8 tile carries at most 3 opaque colours, and the solver had to merge something,
                  which proves the constraint is doing work rather than being satisfied by a small palette
    directions    left is the mirror of right, and the two walk frames differ
    poses         a pose folder fills the battle frames; no pose folder leaves them named TODO
    plug points   segment() reports where the mask came from, generate_pose() reports todo and never invents
    preview       3x PNG exists at the expected size
"""

from __future__ import annotations

import json
import os

import pytest
from PIL import Image

import nes_check
import sprite_pipe


@pytest.fixture()
def concept(tmp_path):
    path = tmp_path / "concept.png"
    sprite_pipe.synthetic_concept(192).save(path)
    return str(path)


@pytest.fixture()
def poses(tmp_path):
    folder = tmp_path / "poses"
    sprite_pipe.synthetic_poses(str(folder))
    return str(folder)


def _tile_colour_counts(path):
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
    return nes_check.tile_colours(image)


def test_overworld_sheet_geometry(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    path = report["overworld"]["path"]
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
    assert image.size == (sprite_pipe.OW_FRAME * sprite_pipe.WALK_FRAMES,
                          sprite_pipe.OW_FRAME * len(sprite_pipe.DIRECTIONS))
    assert image.size == (32, 64)
    assert image.width % 8 == 0 and image.height % 8 == 0
    assert len(report["overworld"]["frames"]) == 8


def test_battle_sheet_geometry(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    path = report["battle"]["path"]
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
    assert image.size == (sprite_pipe.BATTLE_W * 7, sprite_pipe.BATTLE_H)
    assert image.size == (168, 32)
    assert set(report["battle"]["frames"]) == {"idle_0", "idle_1", "attack_0", "attack_1",
                                               "attack_2", "hurt_0", "down_0"}


def test_both_sheets_pass_nes_check(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    for name in ("overworld", "battle"):
        verdict = report[name]["nes_check"]
        assert verdict["ok"], (name, verdict["problems"])
        assert verdict["problem_count"] == 0
    assert report["ok"] is True


def test_no_partial_alpha_and_palette_only(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    allowed = set(sprite_pipe.load_palette()["allowed"])
    for name in ("overworld", "battle"):
        with Image.open(report[name]["path"]) as handle:
            image = handle.convert("RGBA")
        colours = [colour for _, colour in image.getcolors(1 << 20)]
        alphas = {colour[3] for colour in colours}
        assert alphas <= {0, 255}, (name, alphas)
        visible = {colour[:3] for colour in colours if colour[3]}
        assert visible <= allowed, (name, sorted(visible - allowed))


def test_every_tile_fits_three_colours_and_the_solver_ran(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    for name in ("overworld", "battle"):
        tiles = _tile_colour_counts(report[name]["path"])
        worst = max(len(seen) for seen in tiles.values())
        assert worst <= 3, (name, [(tile, sorted(seen)) for tile, seen in tiles.items()
                                   if len(seen) > 3][:3])
        assert report[name]["max_colours_in_a_tile"] == worst
    # The synthetic concept deliberately carries more than three colours in a frame, so a clean sheet with
    # no merge recorded would mean the solver is not the thing enforcing the rule.
    assert report["overworld"]["merges"] >= 1


def test_left_is_the_mirror_of_right_and_walk_frames_differ(concept, tmp_path):
    import PIL.Image as Image
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    with Image.open(report["overworld"]["path"]) as handle:
        sheet = handle.convert("RGBA")
    size = sprite_pipe.OW_FRAME
    rows = {direction: index for index, direction in enumerate(sprite_pipe.DIRECTIONS)}

    def frame(direction, walk):
        y = rows[direction] * size
        return sheet.crop((walk * size, y, walk * size + size, y + size))

    right0, right1 = frame("right", 0), frame("right", 1)
    left0, left1 = frame("left", 0), frame("left", 1)
    assert left0.tobytes() == right0.transpose(Image.FLIP_LEFT_RIGHT).tobytes()
    assert left1.tobytes() == right1.transpose(Image.FLIP_LEFT_RIGHT).tobytes()
    assert right0.tobytes() != right1.tobytes(), "walk frames are identical"
    for direction in ("down", "up"):
        assert frame(direction, 0).tobytes() != frame(direction, 1).tobytes()


def test_without_poses_the_battle_frames_are_named_todo(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"))
    assert report["battle"]["todo"] == [name for _, _, name in sprite_pipe.BATTLE_FRAMES]
    for name in report["battle"]["todo"]:
        assert report["battle"]["frames"][name]["status"] == "TODO"


def test_pose_folder_fills_every_battle_frame(concept, poses, tmp_path):
    report = sprite_pipe.run(concept, poses_folder=poses, out_dir=str(tmp_path / "out"))
    assert report["poses_found"] == 10
    assert report["battle"]["todo"] == []
    for _, _, name in sprite_pipe.BATTLE_FRAMES:
        assert report["battle"]["frames"][name]["source"].endswith(".png")
    assert report["battle"]["nes_check"]["ok"]
    # The overworld walk frame 1 also came from a pose file for the authored directions.
    assert report["overworld"]["frames"]["right_1"]["origin"] == "pose"


def test_stand_in_is_labelled(concept, tmp_path):
    report = sprite_pipe.run(concept, out_dir=str(tmp_path / "out"), stand_in=True)
    assert "idle_0" not in report["battle"]["todo"]
    assert "stand in" in report["battle"]["frames"]["idle_0"]["source"]
    assert len(report["battle"]["todo"]) == 6


def test_segment_reports_its_source_and_masks_the_background(concept):
    import PIL.Image as Image
    with Image.open(concept) as handle:
        image = handle.convert("RGBA")
    result = sprite_pipe.segment(image, path=concept)
    assert result["mask"].size == image.size
    assert result["detail"], "segment() must say what it did"
    mask = result["mask"]
    # Corners of the synthetic concept are sky, the body block is at the centre.
    assert mask.getpixel((0, 0)) == 0
    assert mask.getpixel((image.width - 1, image.height - 1)) == 0
    assert mask.getpixel((image.width // 2, image.height // 2)) == 255


def test_supplied_mask_png_is_used_verbatim(concept, tmp_path):
    import PIL.Image as Image
    mask_path = tmp_path / "mask.png"
    with Image.open(concept) as handle:
        mask = Image.new("L", handle.size, 0)
        mask.paste(255, (40, 40, handle.width - 40, handle.height - 40))
    mask.save(mask_path)
    report = sprite_pipe.run(concept, mask_path=str(mask_path), out_dir=str(tmp_path / "out"))
    assert report["segmentation"]["mask_source"] == "supplied mask PNG"
    assert report["overworld"]["nes_check"]["ok"]


def test_generate_pose_never_invents_an_image():
    result = sprite_pipe.generate_pose("hero idle, NES proportions")
    assert result["status"] in ("ready", "todo")
    if result["status"] == "todo":
        assert result["reason"]
    assert "image" not in result


def test_preview_is_three_times_the_sheets(concept, poses, tmp_path):
    import PIL.Image as Image
    out = str(tmp_path / "out")
    report = sprite_pipe.run(concept, poses_folder=poses, out_dir=out)
    with Image.open(report["preview"]) as handle:
        preview = handle.convert("RGB")
    expected_w = sprite_pipe.BATTLE_W * 7 * sprite_pipe.PREVIEW_SCALE
    assert preview.size[0] == expected_w
    assert preview.size[1] > sprite_pipe.OW_FRAME * sprite_pipe.PREVIEW_SCALE


def test_report_json_is_written_and_readable(concept, tmp_path):
    out = str(tmp_path / "out")
    sprite_pipe.run(concept, out_dir=out)
    path = os.path.join(out, sprite_pipe.REPORT_NAME)
    with open(path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["ok"] is True
    assert saved["overworld"]["nes_check"]["ok"]
    assert saved["palette_file"].endswith(".json")
    for name in ("overworld", "battle"):
        assert os.path.isfile(saved[name]["path"])
    assert os.path.isfile(saved["preview"])


def test_cli_selftest_exit_code(monkeypatch, tmp_path):
    monkeypatch.setattr(sprite_pipe, "DEFAULT_OUT", str(tmp_path / "out"))
    code = sprite_pipe.main(["--selftest", "--out", str(tmp_path / "out")])
    assert code == 0
    assert os.path.isfile(os.path.join(str(tmp_path / "out"), "with_poses", sprite_pipe.REPORT_NAME))
