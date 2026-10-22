"""Tests for the clean-room gate's one exception: downloaded OpenStreetMap cache files.

The gate refuses the names of the two games this project must never copy, anywhere under data\\ or game\\. A real
Overpass download carries real place names ("Queen's Park" in Southampton), so it would trip that scan as if we had
written it. The skip is allowed only when the file itself proves what it is, and these tests exist so the skip can
never quietly widen into a directory allowlist: remove any one of the three markers from a fixture and the foreign
name must fail again, and a hand written file parked inside the cache folder must fail too.
"""

from __future__ import annotations

import json
import os

import check_cleanroom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OVERPASS = {
    "version": 0.6,
    "generator": "Overpass API 0.7.62.11 87bfad18",
    "osm3s": {
        "timestamp_osm_base": "2026-10-22T03:23:36Z",
        "copyright": "The data included in this document is from www.openstreetmap.org. The data is made available "
                     "under ODbL.",
    },
    "elements": [{"type": "way", "id": 1, "tags": {"name": "Queen's Park"}}],
}


def _write(root, rel, payload):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_a_real_overpass_download_is_skipped(tmp_path):
    _write(tmp_path, "data/osm_cache/queens_park.json", OVERPASS)
    errors, scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert errors == []
    assert skipped == 1
    assert scanned == 0


def test_the_same_file_without_the_generator_marker_fails(tmp_path):
    payload = dict(OVERPASS)
    payload.pop("generator")
    _write(tmp_path, "data/osm_cache/queens_park.json", payload)
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert skipped == 0
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_the_same_file_without_the_odbl_marker_fails(tmp_path):
    payload = dict(OVERPASS)
    payload["osm3s"] = {"timestamp_osm_base": "2026-10-22T03:23:36Z"}
    _write(tmp_path, "data/osm_cache/queens_park.json", payload)
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert skipped == 0
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_a_hand_written_file_in_the_cache_folder_still_fails(tmp_path):
    _write(tmp_path, "data/osm_cache/handwritten.json", {"place": "Queen's Park", "note": "typed by hand"})
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert skipped == 0
    assert any("handwritten.json" in error for error in errors), errors


def test_the_markers_do_not_protect_a_file_outside_the_cache(tmp_path):
    _write(tmp_path, "data/maps/southampton.json", OVERPASS)
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert skipped == 0
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_the_game_mirror_of_the_cache_is_skipped_too(tmp_path):
    _write(tmp_path, "game/datafiles/osm_cache/queens_park.json", OVERPASS)
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert errors == []
    assert skipped == 1


def test_a_non_json_file_in_the_cache_folder_is_scanned(tmp_path):
    path = tmp_path / "data" / "osm_cache" / "notes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Queen's Park is a real place\n", encoding="utf-8")
    errors, _scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert skipped == 0
    assert any("notes.json" in error for error in errors), errors


def test_the_gate_passes_on_this_repository():
    assert check_cleanroom.check(ROOT) == []


def test_the_run_line_reports_the_skipped_count(capsys):
    """A skip must be visible on every run, never silent, and its number must be true."""
    _errors, _scanned, skipped = check_cleanroom.text_hits(ROOT)
    check_cleanroom.check(ROOT)
    printed = capsys.readouterr().out
    assert "%d downloaded map file(s) skipped" % skipped in printed, printed


def test_the_real_cache_is_what_gets_skipped():
    expected = 0
    for folder in ("data/osm_cache", "game/datafiles/osm_cache"):
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        expected += len([name for name in os.listdir(base) if name.lower().endswith(".json")])
    _errors, _scanned, skipped = check_cleanroom.text_hits(ROOT)
    assert skipped == expected
