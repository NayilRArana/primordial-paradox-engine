"""Tests for tools/kaggle_r7.py (card t_8079559f, 2026-10-23).

The tool has two claims that a test can settle without a GPU and without writing a candidate: a painted
concept survives the per area quantiser with the scene's own rules intact, and a sprite lands inside ONE of
the scene's four sprite palettes, never in a mixture of them. The rest of the tool is arithmetic over numbers
that tools/palette_synergy.py and tools/nes_check.py already own, so no rule is restated here.

Nothing in this file touches the network, the Kaggle token, or output/kaggle_r7.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import kaggle_r7  # noqa: E402
import palette_synergy  # noqa: E402
import quantize_concept  # noqa: E402
import scene_palette_set  # noqa: E402

BRIEF = {"sky": [(24, 26, 62), (232, 126, 62)],
         "water": [(22, 36, 60), (58, 86, 104)],
         "structures": [{"shape": "mast", "x": 8, "width": 2, "top": 4, "bottom": 56,
                         "colour": (30, 26, 34)},
                        {"shape": "lantern", "x": 8, "y": 10, "colour": (246, 210, 126)}]}


def painted_scene(size=(64, 64)):
    scene = scene_palette_set.scene(ROOT, "battle_quay_dusk")
    return kaggle_r7.paint_scene(BRIEF, size, kaggle_r7.seeded("test"), scene, 8)


def test_the_painter_is_deterministic():
    first = painted_scene()
    second = painted_scene()
    assert first.tobytes() == second.tobytes()
    assert kaggle_r7.count_colours(first) > 20, "a concept with one colour would test nothing"


def test_a_painted_frame_quantises_inside_the_scene_set_and_three_colours_per_area():
    scene = scene_palette_set.scene(ROOT, "battle_quay_dusk")
    grid = palette_synergy.Grid(ROOT)
    painted = painted_scene()
    after, stats = quantize_concept.quantise_areas(painted, scene)
    assert stats["mapping"] == "areas"
    assert stats["palettes_used"] <= 4, stats
    assert kaggle_r7.area_colour_ceiling(after, scene.rgb(scene.backdrop)) <= 3
    problems = palette_synergy.background_report(grid, scene, after)
    assert problems == [], problems


def test_a_sprite_is_painted_through_one_sprite_palette_only():
    scene = scene_palette_set.scene(ROOT, "battle_deck_night")
    brief = {"coat": (26, 58, 138), "coat_dark": (16, 34, 92), "skin": (200, 138, 90),
             "gold": (224, 176, 64), "outline": (16, 16, 24)}
    sprite = kaggle_r7.paint_sprite(brief, (16, 16), kaggle_r7.seeded("sprite"), scene, 8)
    rows = [sorted({scene.rgb(entry) for entry in palette}) for palette in scene.sprites]
    chosen = rows[2]
    counts = sprite.getcolors(1 << 24) or []
    colours = [colour[:3] for _, colour in counts if colour[3]]
    mapped = {kaggle_r7.nearest_in(chosen, colour) for colour in colours}
    assert len(mapped) <= 3, mapped
    assert all(colour in chosen for colour in mapped)


def test_the_segments_cover_every_area_once():
    segments = kaggle_r7.segment(painted_scene(), k=3)
    assert segments
    assert abs(sum(item["coverage_percent"] for item in segments) - 100.0) < 0.2, segments


def test_the_score_is_the_failed_share_of_the_checks():
    assert kaggle_r7.score_of(0, 10) == 100.0
    assert kaggle_r7.score_of(5, 10) == 50.0
    assert kaggle_r7.score_of(1, 4) == 75.0


def test_the_selftest_passes():
    assert kaggle_r7.selftest() == 0


# ------------------------------------------------------------------------------------------------------------------
# The model lane (card t_d1906a5b): a frame generated elsewhere is read, not repainted.


def model_lane(tmp_path, monkeypatch, frames, manifest=None):
    for subject_id, image in frames.items():
        image.save(str(tmp_path / (subject_id + ".png")), "PNG")
    if manifest is not None:
        (tmp_path / "r7_manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(kaggle_r7, "CONCEPTS", str(out))
    monkeypatch.setattr(kaggle_r7, "EXTERNAL", {"dir": str(tmp_path), "manifest": manifest, "rows": {}})
    return out


def test_a_model_frame_is_used_as_it_arrived(tmp_path, monkeypatch):
    frame = Image.new("RGBA", (256, 240), (12, 34, 56, 255))
    out = model_lane(tmp_path, monkeypatch, {"quay_dusk_scene": frame})
    subject = kaggle_r7.SUBJECTS[0]
    assert subject["id"] == "quay_dusk_scene"
    written = kaggle_r7.write_concept(ROOT, subject, None)
    assert written == str(out / "quay_dusk_scene.png")
    with Image.open(written) as handle:
        assert handle.size == (256, 240)
        assert handle.convert("RGBA").tobytes() == frame.tobytes()
    row = kaggle_r7.EXTERNAL["rows"]["quay_dusk_scene"]
    assert row["resized"] is False and row["source_size"] == [256, 240]
    assert len(row["sha256"]) == 64


def test_a_model_frame_at_another_size_is_scaled_without_blending(tmp_path, monkeypatch):
    frame = Image.new("RGBA", (32, 32), (200, 10, 10, 255))
    model_lane(tmp_path, monkeypatch, {"quay_dusk_scene": frame})
    written = kaggle_r7.write_concept(ROOT, kaggle_r7.SUBJECTS[0], None)
    with Image.open(written) as handle:
        converted = handle.convert("RGBA")
    assert converted.size == (256, 240)
    assert {colour[1] for colour in (converted.getcolors(1 << 20) or [])} == {(200, 10, 10, 255)}
    assert kaggle_r7.EXTERNAL["rows"]["quay_dusk_scene"]["resized"] is True


def test_a_subject_the_model_lane_did_not_cover_is_painted_instead(tmp_path, monkeypatch):
    model_lane(tmp_path, monkeypatch, {})
    subject = kaggle_r7.SUBJECTS[0]
    scene = scene_palette_set.scene(ROOT, subject["scene"])
    written = kaggle_r7.write_concept(ROOT, subject, scene)
    with Image.open(written) as handle:
        painted = handle.convert("RGBA").tobytes()
    assert kaggle_r7.count_colours(Image.frombytes("RGBA", (256, 240), painted)) > 20
    assert kaggle_r7.EXTERNAL["rows"] == {}


def test_the_candidate_row_names_the_lane_that_made_the_concept(tmp_path, monkeypatch):
    monkeypatch.setattr(kaggle_r7, "EXTERNAL", {"dir": None, "manifest": None, "rows": {}})
    assert kaggle_r7.concept_lane("local") == "local"
    monkeypatch.setattr(kaggle_r7, "EXTERNAL", {"dir": str(tmp_path), "manifest": None, "rows": {}})
    assert kaggle_r7.concept_lane("local") == "kaggle-gpu"


def test_the_painted_report_is_parked_once_the_model_lane_overwrites_it(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    report_json = output / "report.json"
    report_json.write_text('{"concept_source": {"mode": "painted"}, "picked": {"id": "quay_dusk_scene"}}',
                           encoding="utf-8")
    (output / "report.md").write_text("# painted\n", encoding="utf-8")
    monkeypatch.setattr(kaggle_r7, "OUTPUT", str(output))
    monkeypatch.setattr(kaggle_r7, "REPORT_JSON", str(report_json))
    monkeypatch.setattr(kaggle_r7, "REPORT_MD", str(output / "report.md"))
    monkeypatch.setattr(kaggle_r7, "EXTERNAL", {"dir": str(tmp_path), "manifest": None, "rows": {}})
    first = kaggle_r7.keep_baseline()
    assert first["kept"] is True
    assert (output / "report_local_baseline.json").exists()
    assert json.loads((output / "report_local_baseline.json").read_text(encoding="utf-8"))["picked"]["id"] \
        == "quay_dusk_scene"
    second = kaggle_r7.keep_baseline()
    assert second["kept"] is False and "already exists" in second["reason"]
