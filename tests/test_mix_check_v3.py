"""tests for assets/audio/pp_drive/mix_check_v3.py, the laptop and engine measurement.

The script is part of the card's evidence, so two things are checked here. First the committed
report, which is the whole file's measurement and is what NOTES-v3.md quotes: it must be a whole,
A weighted split that favours the hook band, taken against the title cue, with every gated check
passing and the delivered render's own length. Second that the script still runs and computes on a
short slice, so a regression in the code fails here instead of hiding behind a committed report.
The slice run writes to a temporary report so it cannot overwrite the delivered one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(ROOT, "assets", "audio", "pp_drive")
MIX_SCRIPT = os.path.join(FOLDER, "mix_check_v3.py")
MIX_REPORT = os.path.join(FOLDER, "mix_check_v3.json")


def delivered():
    with open(MIX_REPORT, encoding="utf-8") as handle:
        return json.load(handle)


def test_the_delivered_report_is_a_whole_a_weighted_split():
    payload = delivered()
    shares = payload["cue"]["band_share_percent_a_weighted"]
    assert abs(sum(shares.values()) - 100.0) <= 1.0, shares
    assert shares["hook"] > shares["engine"], shares


def test_the_reference_is_the_title_cue():
    payload = delivered()
    assert payload["reference"]["file"].endswith("pp_01_title.wav")
    assert payload["reference"]["duration_s"] > 0


def test_every_gated_check_passes_on_the_delivered_render():
    payload = delivered()
    assert payload["passed"] is True
    assert payload["checks"]["crest_at_least_8.0_db"] is True
    assert payload["checks"]["low_duty_at_most_0.92"] is True


def test_the_delivered_report_is_the_178_second_render():
    payload = delivered()
    assert payload["cue"]["file"].endswith("pp_drive_v3_humanized.wav")
    assert abs(payload["cue"]["duration_s"] - 178.55) <= 0.5


def test_the_script_still_runs_on_a_slice(tmp_path):
    report = tmp_path / "slice.json"
    proc = subprocess.run([sys.executable, MIX_SCRIPT, "--seconds", "30", "--report", str(report)],
                          capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    with open(report, encoding="utf-8") as handle:
        payload = json.load(handle)
    assert abs(payload["cue"]["duration_s"] - 30.0) <= 0.5
    shares = payload["cue"]["band_share_percent_a_weighted"]
    assert abs(sum(shares.values()) - 100.0) <= 1.0, shares
