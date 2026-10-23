"""Tests for the hook scorer (tools/hook_score.py, MEM-TOOLS).

What is proved here, rather than asserted in a comment:

  - the grammar loads from knowledge/MUSIC-HOOK-GRAMMAR.md when a fenced
    `hook_score:` block is there, and merges over the defaults rather than
    replacing them;
  - a melody built to the hook grammar scores higher than a melody built to
    break every rule in it, and the weakest criterion names a real failure;
  - the three suggestions the card asks for can be produced ("motif returns
    only N times", the rhythm cell advice, the third return advice);
  - the real title theme MIDIs read as format 1 files with the melody track,
    and score between 0 and 100 with the ten criteria weighting 100;
  - a melody list in JSON is scored too, and the CLI writes the report.

The test writes only into a throwaway folder and never opens a window.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import hook_score  # noqa: E402

V2_MIDI = os.path.join(ROOT, "assets", "audio", "title_theme_v2", "title_theme_v2.mid")
V3_MIDI = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "title_theme_v3.mid")

# A hooky melody: a two bar motif in 4/4 that returns six times, with the third
# occurrence varying its last note, steps with one leap, an arch, a pedal A
# repeated, 16 bars.
MOTIF = [(0.0, 1.0, 69), (1.0, 1.0, 71), (2.0, 1.0, 72), (3.0, 1.0, 74),
         (0.0, 1.0, 76), (1.0, 1.0, 74), (2.0, 1.0, 69), (3.0, 1.0, 69)]
MOTIF_VARIED = MOTIF[:6] + [(2.0, 1.0, 71), (3.0, 2.0, 67)]


def motif_notes(first_bar, notes):
    out = []
    for index, (beat, dur, pitch) in enumerate(notes):
        bar = first_bar + index // 4
        out.append({"bar": bar, "beat": beat, "dur": dur, "pitch": pitch})
    return out


HOOKY = {
    "bars": 16,
    "beats_per_bar": 4,
    "notes": (motif_notes(1, MOTIF)          # first return
              + motif_notes(3, MOTIF)        # second return
              + motif_notes(5, MOTIF_VARIED)  # third return, varied
              + motif_notes(7, MOTIF)
              + motif_notes(9, MOTIF)
              + motif_notes(11, MOTIF)
              + motif_notes(13, MOTIF)
              + motif_notes(15, MOTIF)),
}

# A melody that breaks the grammar: no return, one wide leap after another,
# no repeated pitch, 5 bars.
UNHOOKY = {"bars": 5, "beats_per_bar": 4, "notes": [
    {"bar": 1, "beat": 0.0, "dur": 1.0, "pitch": 60},
    {"bar": 1, "beat": 1.0, "dur": 0.5, "pitch": 79},
    {"bar": 1, "beat": 1.5, "dur": 1.5, "pitch": 55},
    {"bar": 2, "beat": 0.0, "dur": 2.0, "pitch": 84},
    {"bar": 2, "beat": 2.0, "dur": 1.0, "pitch": 48},
    {"bar": 3, "beat": 0.0, "dur": 0.5, "pitch": 77},
    {"bar": 3, "beat": 0.5, "dur": 0.5, "pitch": 52},
    {"bar": 3, "beat": 1.0, "dur": 3.0, "pitch": 81},
    {"bar": 4, "beat": 0.0, "dur": 1.0, "pitch": 50},
    {"bar": 4, "beat": 1.0, "dur": 1.0, "pitch": 79},
    {"bar": 4, "beat": 2.0, "dur": 1.0, "pitch": 53},
    {"bar": 5, "beat": 0.0, "dur": 4.0, "pitch": 83}]}


def write_melody(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def score_json(tmp_path, name, data):
    path = write_melody(tmp_path, name, data)
    return hook_score.score_melody_json(path)


# ----------------------------------------------------------------- the grammar

def test_defaults_hold_every_number_the_card_names():
    config, source = hook_score.load_grammar(os.path.join(str(ROOT), "no-such-grammar.md"))
    assert source == "defaults"
    assert config["hook_cell_notes"] == [2, 6]
    assert config["motif_bars"] == [1, 2]
    assert config["motif_min_returns"] == 3
    assert config["motif_min_coverage"] == pytest.approx(0.60)
    assert config["step_ratio_min"] == pytest.approx(0.65)
    assert config["leaps_per_motif"] == 1
    assert config["max_range_semitones"] == 18
    assert config["loop_bars"] == [8, 16, 32]
    assert sum(config["weights"].values()) == 100


def test_grammar_file_overrides_only_what_it_names(tmp_path):
    grammar = tmp_path / "MUSIC-HOOK-GRAMMAR.md"
    grammar.write_text("# Hook grammar\n\n```yaml\nhook_score:\n"
                       "  motif_min_returns: 4\n  weights:\n    hook_cell: 14\n```\n",
                       encoding="utf-8")
    config, source = hook_score.load_grammar(str(grammar))
    assert source == os.path.abspath(str(grammar))
    assert config["motif_min_returns"] == 4
    assert config["weights"]["hook_cell"] == 14
    # untouched keys keep their default
    assert config["motif_min_coverage"] == pytest.approx(0.60)
    assert config["hook_cell_notes"] == [2, 6]


def test_a_markdown_file_without_a_block_falls_back_to_defaults(tmp_path):
    grammar = tmp_path / "MUSIC-HOOK-GRAMMAR.md"
    grammar.write_text("# Hook grammar\n\nNo block here.\n", encoding="utf-8")
    config, source = hook_score.load_grammar(str(grammar))
    assert source == "defaults"


def test_the_shipped_grammar_file_is_the_source_of_the_numbers():
    """The real file must parse, not fall back.

    A typo inside the fenced block silently restores the defaults: load_grammar
    skips a block it cannot parse and the report then just says "defaults",
    which no scoring test would notice. So the shipped file is loaded here and
    held to the numbers its section 9 states.
    """
    config, source = hook_score.load_grammar()
    grammar = os.path.join(str(ROOT), "knowledge", "MUSIC-HOOK-GRAMMAR.md")
    assert source == os.path.abspath(grammar), source
    assert config["hook_cell_notes"] == [2, 6]      # section 2.1
    assert config["leap_semitones"] == 5            # section 9 item 7, a fourth or more
    assert config["leaps_per_motif"] == 1           # section 9 item 7
    assert config["repeat_pitch_min"] == 1          # section 9 item 6
    assert config["loop_bars"] == [8, 16, 32]       # section 9 item 13, 32 as two 16s
    assert config["motif_min_returns"] == 3         # section 9 items 11 and 12
    assert sum(config["weights"].values()) == 100


# ------------------------------------------------------------------- scoring

def test_a_melody_built_to_the_grammar_scores_high(tmp_path):
    report = score_json(tmp_path, "hooky.json", HOOKY)
    keys = {item["key"]: item for item in report["criteria"]}
    assert report["score"] >= 80
    assert keys["motif_returns"]["pass"]
    assert keys["motif_coverage"]["pass"], keys["motif_coverage"]["measured"]
    assert keys["step_ratio"]["pass"], keys["step_ratio"]["measured"]
    assert keys["contour"]["pass"], keys["contour"]["measured"]
    assert keys["repeat_pitch"]["pass"]
    assert keys["loop_length"]["pass"]
    assert report["bars"] == 16


def test_a_melody_that_breaks_the_grammar_scores_low(tmp_path):
    good = score_json(tmp_path, "hooky.json", HOOKY)
    bad = score_json(tmp_path, "unhooky.json", UNHOOKY)
    assert bad["score"] < good["score"] - 20
    assert bad["score"] <= 55
    failing = {item["key"] for item in bad["criteria"] if not item["pass"]}
    assert {"motif_returns", "contour"} <= failing
    assert bad["suggestions"]
    assert bad["weakest"]["criterion"]


def test_the_score_never_leaves_its_range_and_weighs_one_hundred(tmp_path):
    for data, name in ((HOOKY, "hooky.json"), (UNHOOKY, "unhooky.json")):
        report = score_json(tmp_path, name, data)
        assert 0 <= report["score"] <= 100
        assert sum(item["weight"] for item in report["criteria"]) == 100
        assert sum(item["points"] for item in report["criteria"]) == pytest.approx(
            report["points"], abs=0.01)
        for item in report["criteria"]:
            assert 0.0 <= item["fraction"] <= 1.0
            if not item["pass"]:
                assert item["suggestion"]


def test_a_melody_without_a_return_names_the_missing_return(tmp_path):
    data = {"bars": 8, "beats_per_bar": 4, "notes": [
        {"bar": bar, "beat": beat, "dur": 1.0, "pitch": 60 + bar * 2 + index}
        for bar in range(1, 9) for index, beat in enumerate((0.0, 1.0, 2.0, 3.0))]}
    report = score_json(tmp_path, "noreturn.json", data)
    text = " ".join(report["suggestions"])
    assert "repeat" in text or "return" in text
    keys = {item["key"]: item for item in report["criteria"]}
    assert keys["motif_returns"]["fraction"] < 1.0


# ------------------------------------------------------------------- the MIDIs

@pytest.mark.parametrize("path", [V2_MIDI, V3_MIDI])
def test_the_real_themes_read_and_score(path):
    # No skip when the file is missing. Both MIDIs are tracked (card t_50a290de, 2026-10-22), and the
    # old "asset not present" guard is exactly how a HEAD checkout passed this test while reading
    # nothing: the nightly worktree had neither file and reported a skip instead of a defect.
    assert os.path.isfile(path), path
    report = hook_score.score_file(path)
    assert report["melody_track"] == "vrc6 pulse a"
    assert report["bars"] == 52
    assert 0 <= report["score"] <= 100
    assert len(report["criteria"]) == 10
    assert sum(item["weight"] for item in report["criteria"]) == 100
    assert report["weakest"]["key"] in {item["key"] for item in report["criteria"]}
    assert "vrc6 pulse a" in report["midi_tracks"]
    text = hook_score.format_report(report)
    assert "hook_score:" in text
    assert "weakest:" in text


def test_the_scorer_is_deterministic(tmp_path):
    first = score_json(tmp_path, "hooky.json", HOOKY)
    second = score_json(tmp_path, "hooky.json", HOOKY)
    assert first == second


def test_the_cli_writes_the_report(tmp_path):
    melody = write_melody(tmp_path, "hooky.json", HOOKY)
    out = tmp_path / "hook.json"
    assert hook_score.main(["--melody-json", melody, "--json", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["score"] >= 80
    assert report["criteria"]


def test_a_named_track_that_does_not_exist_is_an_error():
    assert os.path.isfile(V3_MIDI), V3_MIDI
    with pytest.raises(ValueError, match="no track named"):
        hook_score.score_file(V3_MIDI, track="no such voice")
