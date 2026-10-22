"""Tests for the clean-room gate's two exceptions: downloaded OSM cache files, and generated geography cards.

The gate refuses the names of the two games this project must never copy, anywhere under data\\ or game\\. A real
Overpass download carries real place names ("Queen's Park" in Southampton), so it would trip that scan as if we had
written it. So does a generated real-places card, whose road, water, rail and landmark names were read out of
OpenStreetMap: "Queen's Terrace" is a Southampton street, and "queen" is also a character name the gate refuses. The
first exception skips a whole proven download; the second blanks out only the proven OSM name fields of a card and
scans every other byte of it, including the prose we wrote.

These tests exist so neither exemption can quietly widen into a directory allowlist or a file allowlist: remove any
one of the markers from a fixture and the foreign name must fail again, a hand written file parked inside the cache
folder must fail, and a hand written file wearing the card's keys must fail too.
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


# A generated geography card: our own prose plus proper-name lists read out of OpenStreetMap.
CARD = {
    "format": 1,
    "kind": "real_places",
    "generated_utc": "2026-10-22T19:42:36+00:00",
    "attribution": "(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, "
                   "https://www.openstreetmap.org/copyright",
    "licence": "OpenStreetMap data ODbL 1.0. Wikipedia text CC BY-SA 4.0, consulted, no images downloaded.",
    "method": "OSM map API bbox -> tools/osm_to_map.py rasteriser at the stated metres per tile",
    "places": [
        {
            "slug": "southampton_old_town",
            "name": "Southampton, the old town and the quay",
            "region": "Hampshire, Southampton",
            "blurb": "The town quay runs north to south with the docks behind it and the high street inland.",
            "landmarks": [{"name": "Bargate"}],
            "roads": {"major": ["Above Bar Street"], "minor": ["Queen's Terrace"], "route_relations": []},
            "water_names": ["River Test"],
            "rail_names": ["South Western Main Line"],
            "rail_disused_names": [],
            "source_kind": "cache",
        }
    ],
}


def _card(**changes):
    payload = json.loads(json.dumps(CARD))
    payload.update(changes)
    return payload


def test_a_generated_geography_card_keeps_its_osm_street_names(tmp_path):
    """The Queen's Terrace case: a real street in a proven card is data, not a borrowed character name."""
    _write(tmp_path, "data/maps/real_places.json", CARD)
    errors, scanned, skipped = check_cleanroom.text_hits(str(tmp_path))
    assert errors == [], errors
    assert scanned == 1
    assert skipped == 0
    assert check_cleanroom.EXEMPT_CARDS == 1
    assert check_cleanroom.EXEMPT_FILES == [("data/maps/real_places.json", 5)]
    assert check_cleanroom.EXEMPT_NAMES == 5


def test_the_card_without_the_odbl_attribution_is_scanned_whole(tmp_path):
    payload = _card()
    payload.pop("attribution")
    _write(tmp_path, "data/maps/real_places.json", payload)
    errors, _scanned, _skipped = check_cleanroom.text_hits(str(tmp_path))
    assert any("foreign name 'Queen'" in error for error in errors), errors
    assert check_cleanroom.EXEMPT_CARDS == 0


def test_the_card_without_the_osm_source_marker_is_scanned_whole(tmp_path):
    payload = _card()
    payload.pop("method")
    payload["places"][0].pop("source_kind")
    _write(tmp_path, "data/maps/real_places.json", payload)
    errors, _scanned, _skipped = check_cleanroom.text_hits(str(tmp_path))
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_a_hand_written_file_wearing_the_card_keys_still_fails(tmp_path):
    """Keys alone are not provenance: a card must carry the attribution and the licence with them."""
    _write(tmp_path, "data/maps/real_places.json",
           {"kind": "real_places", "places": [{"roads": {"minor": ["Queen Street"]}}]})
    errors, _scanned, _skipped = check_cleanroom.text_hits(str(tmp_path))
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_a_foreign_name_in_the_card_prose_still_fails(tmp_path):
    """Only the OSM name fields are exempt. The blurb is ours and is scanned, with a true line number."""
    payload = _card()
    payload["places"][0]["blurb"] = "The queen waits at the top of the high street."
    path = _write(tmp_path, "data/maps/real_places.json", payload)
    errors, _scanned, _skipped = check_cleanroom.text_hits(str(tmp_path))
    hits = [error for error in errors if "foreign name 'queen'" in error.lower()]
    assert hits, errors
    line = [number for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if "waits at the top" in text][0]
    assert hits[0] == "data/maps/real_places.json:%d: foreign name 'queen'" % line, hits


def test_a_foreign_name_outside_the_geography_fields_still_fails(tmp_path):
    payload = _card()
    payload["places"][0]["notes"] = "a hand written note about Queen's Guard"
    _write(tmp_path, "data/maps/real_places.json", payload)
    errors, _scanned, _skipped = check_cleanroom.text_hits(str(tmp_path))
    assert any("foreign name 'Queen'" in error for error in errors), errors


def test_the_exempt_name_lists_are_read_from_the_named_fields_only():
    payload = _card()
    payload["places"][0]["notes"] = "a hand written note about Queen's Guard"
    names = check_cleanroom.geography_names(payload)
    assert "Queen's Terrace" in names
    assert "Bargate" in names
    assert "River Test" in names
    assert "a hand written note about Queen's Guard" not in names


def test_the_run_line_names_every_exempt_card(capsys):
    """The exemption must be visible on every run, with a true count, and each card named."""
    errors = check_cleanroom.check(ROOT)
    printed = capsys.readouterr().out
    assert errors == []
    assert check_cleanroom.EXEMPT_CARDS >= 1, printed
    assert "%d OSM place name(s) exempt in %d generated geography card(s)" % (
        check_cleanroom.EXEMPT_NAMES, check_cleanroom.EXEMPT_CARDS) in printed, printed
    for rel, count in check_cleanroom.EXEMPT_FILES:
        assert "OSM place names exempt from the foreign name pass: %s (%d name(s))" % (rel, count) in printed, printed


def test_the_real_places_card_is_the_card_that_gets_exempted():
    """The file that failed the gate on 2026-10-22 is read, its street names count, and its prose is ours."""
    path = os.path.join(ROOT, "data", "maps", "real_places.json")
    payload = json.loads(open(path, encoding="utf-8-sig").read())
    assert check_cleanroom.geography_card(payload)
    names = check_cleanroom.geography_names(payload)
    assert "Queen's Terrace" in names
    assert check_cleanroom.geography_exemptions(open(path, encoding="utf-8-sig").read()) == names

