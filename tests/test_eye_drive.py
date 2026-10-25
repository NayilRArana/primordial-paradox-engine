"""tests for tools/eye_drive.py: the twelve shot sampler, the PPU numbers, and the model chain.

Card GEMINI-EYE-DRIVE (t_4bf72d3b). Three things are worth pinning, because each one is a way the
report could quietly become fiction:

  1. the sample is one frame per shot, at 256x240, and a missing capture is a FAILED shot rather
     than a skipped row (the card asks for twelve verdicts);
  2. the legality numbers come from the project's own checker, so a frame the checker fails cannot
     be reported as legal because a model liked it;
  3. the model chain moves to the next model on a per-day quota refusal instead of failing the run,
     proved against a fake transport that answers the real 429 body.

WHERE THE TWELVE FRAMES COME FROM, and why they are committed (decision taken 2026-10-24, card
t_d2c52f15). The input is output/drive/pp_drive_shot_01.png to _12.png, 768x720 captures that the
game writes from inside its own draw; only a GameMaker run produces them, so this test cannot make
them and must not pretend to. They are therefore committed, un-ignored by name in .gitignore and
listed one by one in tools/check_test_inputs.py FIXTURES, which is what makes a clean checkout
measure twelve real frames instead of reporting twelve failed shots. The alternative, a skip or a
note saying the row only runs on a capture machine, was refused: a row that cannot run where the
suite runs is the same silent pass this project already forbids in check_test_inputs.py. Nothing
in the assertions below was relaxed to allow this; the frames are the test's input, not a preview.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import eye_drive  # noqa: E402
import nes_composite_check as nes  # noqa: E402


@pytest.fixture(scope="module")
def palette():
    return nes.load_palette(eye_drive.PALETTE_PATH)


@pytest.fixture(scope="module")
def rows():
    return eye_drive.sample_frames()


def test_one_frame_per_shot_and_twelve_of_them(rows):
    assert len(rows) == 12
    assert [row["n"] for row in rows] == list(range(1, 13))
    missing = [row for row in rows if row.get("error")]
    assert not missing, "shots without a captured frame: %s" % [row["n"] for row in missing]
    for row in rows:
        assert os.path.exists(row["frame"]), row["frame"]
        assert row["capture"]["source_size"] == [768, 720]
        assert row["capture"]["scale"] == 3
        with open(row["frame"], "rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n"


def test_every_shot_row_carries_the_shot_list_description(rows):
    for row in rows:
        assert row["shows"], "shot %d has no description from DRIVE-SHOT-LIST" % row["n"]
        assert row["location"]
    # The four gantry signs, from DRIVE-SHOT-LIST section 5.
    signs = {row["n"]: row["sign"] for row in rows if row["sign"]}
    assert signs == {3: "55", 6: "43", 9: "30", 11: "20"}


def test_measurement_reports_colours_and_attribute_areas(rows, palette):
    for row in rows[:3]:
        measured = eye_drive.measure(row, palette)
        assert measured["size"] == [256, 240]
        assert measured["colours"] >= 1
        assert measured["off_palette_colours"] >= 0
        assert measured["attribute_areas_over"] >= 0
        assert isinstance(measured["legal"], bool)
        # The two halves must agree: a frame with a colour the PPU cannot output is not legal.
        if measured["off_palette_colours"]:
            assert measured["legal"] is False, "an off-palette frame cannot pass legality"


def test_verdict_cannot_pass_on_a_legal_failure():
    measured = {"legal": False, "colours": 8, "off_palette_colours": 8}
    good_review = {"scores": {"nes": 9, "readability": 9, "charm": 9}}
    verdict = eye_drive.verdict_for({"n": 1}, measured, good_review)
    assert verdict["legality"] == "FAIL"
    assert verdict["art"] == "PASS"
    assert verdict["overall"] == "FAIL", "a model score must never rescue an illegal frame"


def test_verdict_bands_and_the_unjudged_case():
    legal = {"legal": True}
    assert eye_drive.verdict_for({"n": 1}, legal, {"scores": {"nes": 8, "readability": 7,
                                                              "charm": 6}})["overall"] == "PASS"
    assert eye_drive.verdict_for({"n": 1}, legal, {"scores": {"nes": 6, "readability": 7,
                                                              "charm": 6}})["overall"] == "REVISE"
    assert eye_drive.verdict_for({"n": 1}, legal, {"scores": {"nes": 4, "readability": 7,
                                                              "charm": 6}})["overall"] == "FAIL"
    assert eye_drive.verdict_for({"n": 1}, legal, None)["overall"] == "NOT JUDGED"


def test_model_chain_falls_back_on_a_per_day_quota_refusal(tmp_path, rows):
    """The behaviour the report claims, driven with the API's own per-day 429 body."""
    os.environ.setdefault("PP_EYE_MAX_PER_MINUTE", "20")
    result = eye_drive.self_test(str(tmp_path / "selftest"))
    assert result["refused"] == eye_drive.MODEL_CHAIN[0]
    assert result["answered"] == eye_drive.MODEL_CHAIN[1]
    assert "quota refusal" in result["verdict"]


def test_the_quota_body_names_a_per_day_limit():
    """The self test is only honest if its 429 is the daily shape eye_critic refuses to retry."""
    assert eye_critic_daily_quota(eye_drive.QUOTA_BODY)


def eye_critic_daily_quota(body):
    sys.path.insert(0, TOOLS)
    import eye_critic
    return eye_critic._daily_quota(body) and "PerDay" in body
