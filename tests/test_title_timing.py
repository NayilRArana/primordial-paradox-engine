"""Pins for the title's one tempo (card TEMPO-1, review round 1): the json, the macros and the game agree.

Review round 1 found the three of them disagreeing: data\\title_timing.json said stars.steps 86 (a bar), the intro's
timing function recomputed 114 steps from an intro.twinkle_beats 4 that the same file still carried, and the title
card's own sky ran on the art index's 2 fps, a 60 step cycle that matched no beat at all. One twinkle rate, one bar,
one source is the whole point of the card, so these tests hold the agreement down instead of trusting it:

  1. the json is the tempo's own arithmetic: bar_steps is beats_per_bar beats, scroll * beat_steps is one lane dash,
     and the twinkle, the lightning and the shimmer are bars of the same lattice;
  2. the json carries exactly one twinkle rate, with no rival intro key to disagree with it;
  3. apply_title_timing.py --check passes, which is what proves the macros in pp_title.gml are that json's copy;
  4. the game derives the sky's star frame from PP_TITLE_BAR_STEPS and reads the twinkle from stars.steps, so the
     rates cannot come back as two.

Run: python -m pytest tests/test_title_timing.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMING = os.path.join(ROOT, "data", "title_timing.json")
TITLE_GML = os.path.join(ROOT, "game", "scripts", "pp_title", "pp_title.gml")
APPLY = os.path.join(ROOT, "tools", "apply_title_timing.py")


def timing() -> dict:
    with open(TIMING, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_the_json_is_the_tempo_its_own_arithmetic():
    data = timing()
    assert data["bpm"] == 126
    assert data["fps"] == 60
    assert data["beats_per_bar"] == 3
    # 126 bpm at 60 steps a second is 28.571 steps a beat and 85.714 a bar, and the integers the counters run on are
    # one lattice: a bar is three beats, not the 86 that rounding the bar on its own gave.
    assert round(data["steps_per_beat"], 3) == 28.571
    assert round(data["steps_per_bar"], 3) == 85.714
    assert data["bar_steps"] == data["beat_steps"] * data["beats_per_bar"]
    # One lane dash a beat: the road art draws a 16 px dash in every 16 px (tools/art/make_title_world.py build_road).
    scroll = data["scroll"]
    assert scroll["dash_px"] == 16
    assert abs(scroll["px_per_step"] * data["beat_steps"] - scroll["dash_px"]) < 0.05
    # Faster than the build the card was written against, and by more than the 1.6 it asked for.
    assert scroll["px_per_step"] / scroll["previous_px_step"] >= 1.6
    # The car, the exhaust, the flash and the shimmer are all counted in the same steps.
    assert data["car"]["bob_steps"] == data["beat_steps"]
    assert data["car"]["bob_px"] == 1
    assert data["exhaust"]["steps"] == data["exhaust"]["beats_per_puff"] * data["beat_steps"]
    assert data["lightning"]["steps"] == data["lightning"]["bars"] * data["bar_steps"]
    assert data["shimmer"]["steps"] == data["shimmer"]["bars"] * data["bar_steps"]


def test_the_twinkle_is_the_bar_and_has_no_rival():
    data = timing()
    stars = data["stars"]
    assert stars["twinkles_on"] == "bar"
    assert stars["steps"] == data["bar_steps"]
    assert stars["beats"] == data["beats_per_bar"]
    # The key that produced the 114 step twinkle in review round 1. Any second rate is the bug, not the number.
    for rival in ("twinkle_beats", "twinkle_steps", "twinkle_seconds"):
        assert rival not in data.get("intro", {})


def test_the_macros_are_that_json_s_copy():
    result = subprocess.run([sys.executable, APPLY, "--check"], cwd=ROOT, capture_output=True, text=True,
                            timeout=120, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
    assert "matches" in (result.stdout or "")


def test_the_game_derives_the_star_sky_from_the_bar():
    with open(TITLE_GML, "r", encoding="utf-8") as handle:
        source = handle.read()
    # The sky turns over on the bar, not on the art index's 2 fps.
    assert "floor(_steps / PP_TITLE_BAR_STEPS) mod _frames" in source
    # The intro's twinkle is read from the bar or from stars.steps, and never recomputed from a beat count. The
    # comment above the code names the old key on purpose, so only the code lines are read.
    assert "_out.twinkle_period = _d.bar_steps" in source
    assert "_out.twinkle_period = _d.stars.steps" in source
    code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("//"))
    assert "twinkle_beats" not in code
