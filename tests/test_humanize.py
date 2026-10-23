"""Tests for the chip humanizer (tools/humanize.py, MEM-TOOLS).

What is proved here, rather than asserted in a comment:

  - a file that is read and written again keeps its format, division, tempo,
    time signature, track names and every note;
  - humanizing changes at least 30 percent of the notes' lengths, keeps every
    note off no later than the written length and no earlier than 85 percent of
    it (or the latest frame it can end on, when no frame reaches that far), on
    the 1/60 s frame grid, and moves every velocity by at most 6;
  - the same input and seed give byte identical output, twice;
  - the level envelope is shaped per role: the melody decays inside the note,
    the bass stays flat, the arpeggio is plucked;
  - the vibrato depth and delay vary from phrase to phrase;
  - a melody whose motif returns three times gets a grace note and a mordent
    on the third return, the phrase end gets a rest breath, and the last beat
    before a section change gets a fill;
  - the arrange pipeline writes the humanized file and the hook report behind
    its two new flags, and the file still reads as the eight voice schema.

The test writes only into a throwaway folder and never opens a window.
"""

from __future__ import annotations

import json
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import arrange       # noqa: E402
import hook_score    # noqa: E402
import humanize      # noqa: E402

V3_MIDI = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "title_theme_v3.mid")
V3_SCORE = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "score_v3.yaml")

DIVISION = 480
BEATS_PER_BAR = 3
BAR = BEATS_PER_BAR * DIVISION
TEMPO_US = 500000            # 120 bpm, so one 1/60 s frame is 16 ticks


def blank_track(name):
    return {"name": name, "notes": [], "cc": {}}


def synthetic_song():
    """Eight bars of the eight voice schema, with a motif that returns three times."""
    tracks = [blank_track(name) for name in
              ("meta", "vrc6 pulse a", "vrc6 pulse b", "vrc6 saw", "pulse 1",
               "pulse 2", "triangle", "noise", "dpcm")]
    by_name = {track["name"]: track for track in tracks}

    melody = by_name["vrc6 pulse a"]
    arpeggio = by_name["pulse 1"]
    echo = by_name["pulse 2"]
    bass = by_name["triangle"]
    noise = by_name["noise"]

    # A two bar motif in 3/4, six quarter notes, the last one running exactly
    # into the phrase end so the breath rule has something to cut.
    motif = [(69, 472), (71, 472), (72, 472), (74, 472), (76, 472), (69, 480)]
    for return_index in range(4):
        base = return_index * 2 * BAR
        for index, (pitch, length) in enumerate(motif):
            start = base + index * 480
            melody["notes"].append((start, start + length, pitch, 100))

    for bar in range(8):
        start = bar * BAR
        for beat in range(BEATS_PER_BAR):
            arpeggio["notes"].append((start + beat * DIVISION,
                                      start + beat * DIVISION + 232, 72 + beat * 2, 96))
        bass["notes"].append((start, start + BAR - 10, 45, 104))
        # hats on the first two beats only, so the last beat is free for a fill
        for beat in (0, 1):
            noise["notes"].append((start + beat * DIVISION,
                                   start + beat * DIVISION + 60, 6, 90))
        echo["notes"].append((start + 240, start + 500, 69, 70))
    by_name["vrc6 pulse b"]["notes"].append((0, BAR - 8, 64, 90))
    by_name["dpcm"]["notes"].append((0, 120, 36, 110))

    for track in tracks:
        track["notes"].sort()
        track["cc"] = {11: [(bar * BAR, 11) for bar in range(8)]}
    by_name["pulse 2"]["cc"][11] = [(bar * BAR, 4) for bar in range(8)]
    # The arranger's vibrato convention: depth on the melody note starts.
    melody["cc"][1] = [(start, 10) for start, _end, _pitch, _vel in melody["notes"]]
    melody["cc"][20] = [(start, 1) for start, _end, _pitch, _vel in melody["notes"]]

    return {"format": 1, "division": DIVISION, "tempo_us": TEMPO_US,
            "time_sig": (BEATS_PER_BAR, 4), "tracks": tracks}


def notes_by_start(track):
    return {(start, pitch): end for start, end, pitch, _velocity in track["notes"]}


def off_contract_failures(before, after, unit, ornament_zone=None):
    """Check every note off the humanizer writes, and return (checked, bad).

    The off is the frame boundary inside the note nearest the role's band, so:

      - it is never later than the written end, plus half a tick of rounding;
      - it is always on the 1/60 s frame grid;
      - it is never earlier than 85 percent of the written length, unless the
        note holds no frame that late, and then it is the latest frame the note
        can end on. A hat written at 60 ticks, at 16 ticks a frame, is that
        case: its frames are 48 and 64, so it ends at 48, which is 80 percent.
    """
    checked = 0
    bad = []
    for name, original in before.items():
        for (start, pitch), end in original.items():
            new_end = after[name].get((start, pitch))
            if new_end is None:
                continue            # rewritten by an ornament, checked below
            if ornament_zone and name == "vrc6 pulse a" and \
                    ornament_zone[0] <= start < ornament_zone[1]:
                continue
            written = end - start
            sounding = new_end - start
            floor = 0.85 * written
            latest = int(math.floor(end / unit + 1e-9) * unit) - start
            checked += 1
            if new_end < start + 1:
                bad.append(("under one tick", name, start, pitch, sounding))
            if sounding > written + 0.5:
                bad.append(("past the written end", name, start, pitch,
                            sounding, written))
            if humanize.next_frame_tick(start + floor, unit) <= end:
                if sounding < floor - 1:
                    bad.append(("under the floor", name, start, pitch,
                                sounding, floor))
            elif sounding < latest:
                bad.append(("under the last frame", name, start, pitch,
                            sounding, latest))
            if abs(new_end - round(new_end / unit) * unit) > 1.0:
                bad.append(("off the frame grid", name, new_end, unit))
    return checked, bad


# ------------------------------------------------------------- read and write

def test_read_write_round_trip_keeps_everything():
    # No skip when the input is missing (card t_50a290de, 2026-10-22). The score is tracked, and a
    # skip here was how a HEAD checkout reported this test as healthy while it measured nothing.
    assert os.path.isfile(V3_MIDI), V3_MIDI
    song = hook_score.read_smf(V3_MIDI)
    again = hook_score.parse_smf(humanize.write_smf(song))
    assert again["division"] == song["division"]
    assert again["tempo_us"] == song["tempo_us"]
    assert again["time_sig"] == song["time_sig"]
    assert [t["name"] for t in again["tracks"]] == [t["name"] for t in song["tracks"]]
    for before, after in zip(song["tracks"], again["tracks"]):
        assert sorted(before["notes"]) == sorted(after["notes"]), before["name"]
        for controller in before["cc"]:
            assert sorted(before["cc"][controller]) == sorted(after["cc"][controller])


# ------------------------------------------------------------------ the rules

def test_articulation_velocity_and_the_frame_grid():
    song = synthetic_song()
    out, report = humanize.humanize_song(song, seed=humanize.DEFAULT_SEED)
    unit = humanize.ticks_per_frame(song["division"], song["tempo_us"])

    before = {t["name"]: notes_by_start(t) for t in song["tracks"]}
    after = {t["name"]: notes_by_start(t) for t in out["tracks"]}
    # The one note the mordent rewrites is checked by the ornament test.
    ornament_bar = ((report["motif"] or {}).get("third_return_bar") or 0) - 1
    ornament_zone = (ornament_bar * BAR, ornament_bar * BAR + 240)
    checked, bad = off_contract_failures(before, after, unit, ornament_zone)
    assert not bad, bad[:4]
    assert checked > 40

    # Velocity moves by at most 6 either way, per note.
    velocities_before = {(t["name"], n[0], n[2]): n[3] for t in song["tracks"] for n in t["notes"]}
    for track in out["tracks"]:
        for start, _end, pitch, velocity in track["notes"]:
            original = velocities_before.get((track["name"], start, pitch))
            if original is None:
                continue
            assert abs(velocity - original) <= 6

    assert report["notes_changed"] / float(report["notes"]) >= 0.30
    assert report["changed_fraction"] if "changed_fraction" in report else True


def test_the_note_off_contract_holds_at_every_seed():
    """The floor, the grid and the written end, swept over 40 seeds.

    The two notes the card measured failed on one seed each (84.75 and 80
    percent), so the contract is swept across seeds instead of asserted once.
    """
    for seed in range(40):
        song = synthetic_song()
        out, report = humanize.humanize_song(song, seed=seed)
        unit = humanize.ticks_per_frame(song["division"], song["tempo_us"])
        before = {t["name"]: notes_by_start(t) for t in song["tracks"]}
        after = {t["name"]: notes_by_start(t) for t in out["tracks"]}
        ornament_bar = ((report["motif"] or {}).get("third_return_bar") or 0) - 1
        ornament_zone = (ornament_bar * BAR, ornament_bar * BAR + 240)
        checked, bad = off_contract_failures(before, after, unit, ornament_zone)
        assert not bad, (seed, bad[:4])
        assert checked > 40


def test_a_note_with_no_frame_at_the_floor_ends_on_its_last_frame():
    """A hat of 60 ticks at 16 ticks a frame has the frames 48 and 64 only.

    51 ticks is 85 percent of it and no frame lands there, while 64 is past the
    written end, so the hat ends on 48: the grid holds and the report records
    the note as left under the floor rather than the off drifting off the grid.
    """
    song = synthetic_song()
    out, report = humanize.humanize_song(song, seed=humanize.DEFAULT_SEED)
    unit = humanize.ticks_per_frame(song["division"], song["tempo_us"])
    before = notes_by_start(next(t for t in song["tracks"] if t["name"] == "noise"))
    after = notes_by_start(next(t for t in out["tracks"] if t["name"] == "noise"))
    assert before
    for (start, _pitch), end in before.items():
        assert end - start == 60, (start, end)      # every hat is 60 ticks long
        new_end = after[(start, _pitch)]
        assert new_end <= end + 0.5, (start, new_end)
        assert abs(new_end - round(new_end / unit) * unit) <= 1.0, (start, new_end, unit)
        assert new_end - start >= 48, (start, new_end)
    assert report["floor_misses"] > 0


def test_same_seed_gives_byte_identical_output_twice():
    song = synthetic_song()
    data = humanize.write_smf(song)
    first, first_report = humanize.humanize_bytes(data)
    second, second_report = humanize.humanize_bytes(data)
    assert first == second
    assert first_report["sha256_out"] == second_report["sha256_out"]
    third, _ = humanize.humanize_bytes(data, seed=humanize.DEFAULT_SEED + 1)
    assert third != first


def test_the_level_envelope_is_shaped_per_role():
    song = synthetic_song()
    out, report = humanize.humanize_song(song)
    tracks = {t["name"]: t for t in out["tracks"]}
    levels = {name: len(tracks[name]["cc"].get(11, [])) for name in tracks}

    # The melody and the arpeggio gain points inside their notes; the bass
    # keeps only the eight bar level points it came with, because a waltz
    # bass is flat.
    assert levels["vrc6 pulse a"] > 8
    assert levels["pulse 1"] > 8
    assert levels["triangle"] == 8
    assert report["envelope_points"] > 0

    # The plucked arpeggio decays further than the melody does over one note.
    def end_level(name, start):
        events = tracks[name]["cc"][11]
        values = [value for tick, value in events if start <= tick < start + 240]
        return values[-1]

    assert end_level("pulse 1", 0) < end_level("vrc6 pulse a", 0)


def test_vibrato_depth_and_delay_vary_from_phrase_to_phrase():
    song = synthetic_song()
    out, report = humanize.humanize_song(song)
    melody = next(t for t in out["tracks"] if t["name"] == "vrc6 pulse a")
    depths = {value for _tick, value in melody["cc"][1] if value}
    delays = {value for _tick, value in melody["cc"][20] if value}
    assert len(depths) >= 2, depths
    assert len(delays) >= 2, delays
    assert report["vibrato_notes"] > 0


def test_ornaments_breath_and_fills_appear():
    song = synthetic_song()
    out, report = humanize.humanize_song(song)
    assert report["grace_notes"] == 1
    assert report["mordents"] == 1
    assert report["breaths"] >= 1
    assert report["fills"] > 0
    assert report["section_bars"]
    assert report["motif"] and report["motif"]["returns"] >= 3

    melody = next(t for t in out["tracks"] if t["name"] == "vrc6 pulse a")
    third_bar = report["motif"]["third_return_bar"] - 1
    ornamented = [n for n in melody["notes"] if third_bar * BAR <= n[0] < third_bar * BAR + 240]
    assert len(ornamented) >= 2, "the mordent splits the first note of the third return"

    # The breath: no melody note runs into the two bar phrase end any more.
    boundary = 2 * BAR
    running = [n for n in melody["notes"] if n[1] > boundary - 8 and n[1] <= boundary]
    assert not running, running


def test_no_track_holds_more_than_eight_notes_at_once():
    song = synthetic_song()
    out, _report = humanize.humanize_song(song)
    edges = []
    for track in out["tracks"]:
        for start, end, _pitch, _velocity in track["notes"]:
            edges.append((start, 1))
            edges.append((end, -1))
    edges.sort(key=lambda item: (item[0], item[1]))
    sounding = 0
    peak = 0
    for _tick, change in edges:
        sounding += change
        peak = max(peak, sounding)
    assert peak <= 8, peak


# ------------------------------------------------------------------ the MIDIs

def test_the_real_theme_is_humanized_and_stays_readable(tmp_path):
    assert os.path.isfile(V3_MIDI), V3_MIDI
    out_path = str(tmp_path / "theme_human.mid")
    report = humanize.humanize_file(V3_MIDI, out_path)
    assert report["notes_changed"] / float(report["notes"]) >= 0.30
    assert report["notes_out"] >= report["notes_in"]
    written = hook_score.read_smf(out_path)
    original = hook_score.read_smf(V3_MIDI)
    assert [t["name"] for t in written["tracks"]] == [t["name"] for t in original["tracks"]]
    assert written["division"] == original["division"]
    assert written["tempo_us"] == original["tempo_us"]
    # Every original note still starts where it did.
    for before, after in zip(original["tracks"], written["tracks"]):
        starts_before = {(start, pitch) for start, _end, pitch, _v in before["notes"]}
        starts_after = {(start, pitch) for start, _end, pitch, _v in after["notes"]}
        assert starts_before <= starts_after, before["name"]

    again = str(tmp_path / "theme_human_again.mid")
    humanize.humanize_file(V3_MIDI, again)
    with open(out_path, "rb") as handle:
        first = handle.read()
    with open(again, "rb") as handle:
        second = handle.read()
    assert first == second


def test_the_cli_reports_and_can_dry_run(tmp_path, capsys):
    assert os.path.isfile(V3_MIDI), V3_MIDI
    report_path = tmp_path / "human.json"
    assert humanize.main([V3_MIDI, "--dry-run", "--report", str(report_path)]) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["changed_fraction"] >= 0.30
    assert "midi_out" not in report
    out = capsys.readouterr().out
    assert "articulation:" in out
    assert "ornaments:" in out


# --------------------------------------------------------------- the pipeline

def test_arrange_hook_report_and_humanize_flags(tmp_path):
    assert os.path.isfile(V3_SCORE), V3_SCORE
    midi = tmp_path / "theme.mid"
    hook_path = tmp_path / "hook.json"
    report_path = tmp_path / "arrange.json"
    assert arrange.main([V3_SCORE, "-o", str(midi), "--report", str(report_path),
                         "--hook-report", str(hook_path), "--humanize"]) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["hook"]["score"] > 0
    assert report["humanize"]["changed_fraction"] >= 0.30
    assert report["midi_humanized"] == os.path.abspath(str(midi))
    hook = json.loads(hook_path.read_text(encoding="utf-8"))
    assert hook["score"] == report["hook"]["score"]
    written = hook_score.read_smf(str(midi))
    assert len(written["tracks"]) == 9
    assert "vrc6 pulse a" in [t["name"] for t in written["tracks"]]
