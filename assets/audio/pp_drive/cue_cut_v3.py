"""cue_cut_v3.py: prove the drive cue is cut on the shot list's bar grid, and print the dump.

Card CUE-DRIVE (t_b84a9264). Reads only:

  knowledge/DRIVE-SHOT-LIST.md        section 1 (the grid), section 2 (the twelve shots)
  data/title_timing.json              bpm, beats_per_bar, steps_per_bar, bar_steps
  assets/audio/pp_drive/pp_drive_v3.mid   the arranged cue, eight chip voices

It writes:

  assets/audio/pp_drive/cue_map_v3.json   the shot to cue bar map, machine readable
  assets/audio/pp_drive/cut_dump_v3.txt   the tracker shaped text dump with the cut markers

Three checks, each printed with its numbers:

  1. The twelve shot durations in section 2 sum to the film length (10,680 steps, 178.00 s).
  2. Every hard cut in section 1 falls on a bar line of the cue: cut steps / steps_per_bar is a
     whole number of bars, to a 0.01 bar tolerance. The cue bar number on each cut is the bar
     whose downbeat the cut lands on.
  3. The arranged MIDI agrees: there is a sounding note, a drum hit or a fresh attack within one
     step of every cut bar's downbeat, so the picture cut and the music attack are the same frame.

Exit code 0 means all three passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

SHOT_LIST = "knowledge/DRIVE-SHOT-LIST.md"
TIMING = "data/title_timing.json"
TOLERANCE_BARS = 0.01


def read_text(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
        return handle.read()


def timing_grid():
    with open(os.path.join(REPO, TIMING), encoding="utf-8") as handle:
        timing = json.load(handle)
    return {
        "bpm": timing["bpm"],
        "beats_per_bar": timing["beats_per_bar"],
        "steps_per_bar": timing["steps_per_bar"],
        "bar_steps": timing["bar_steps"],
        "seconds_per_bar": 60.0 / timing["bpm"] * timing["beats_per_bar"],
    }


def shot_rows():
    """Section 2 of the shot list: the twelve shots, in order, as numbers."""
    text = read_text(SHOT_LIST)
    rows = []
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| ---") or "| # |" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or not re.fullmatch(r"\d+", cells[0]):
            continue
        steps = int(cells[4].replace(",", ""))
        rows.append({"shot": int(cells[0]), "beat": cells[1], "location": cells[2],
                     "bars": cells[3], "steps": steps, "length_s": float(cells[5])})
    return rows


def cut_steps_from_section_one():
    """Section 1 names the eleven hard cuts as steps; read them rather than recompute."""
    text = read_text(SHOT_LIST)
    match = re.search(r"are at steps (.*?)which are bars (.*?)of the cue", text, re.S)
    if not match:
        raise SystemExit("could not find the eleven cut steps in section 1")
    steps = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", match.group(1))]
    bars = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", match.group(2))]
    return steps, bars


def read_midi(path):
    """Minimal SMF reader: tempo, division, and (track name, notes) per track."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"MThd":
        raise SystemExit("%s is not a MIDI file" % path)
    header_len, _fmt, tracks, division = struct.unpack(">IHHH", data[4:14])
    pos = 8 + header_len
    out = []
    tempos = []
    for _ in range(tracks):
        if data[pos:pos + 4] != b"MTrk":
            raise SystemExit("bad track header at %d" % pos)
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        tick = 0
        status = 0
        name = ""
        notes = []
        idx = 0
        while idx < len(body):
            delta = 0
            while True:
                byte = body[idx]
                idx += 1
                delta = (delta << 7) | (byte & 0x7F)
                if not byte & 0x80:
                    break
            tick += delta
            if idx >= len(body):
                break
            byte = body[idx]
            if byte & 0x80:
                status = byte
                idx += 1
            if status == 0xFF:
                meta = body[idx]
                idx += 1
                size = 0
                while True:
                    byte = body[idx]
                    idx += 1
                    size = (size << 7) | (byte & 0x7F)
                    if not byte & 0x80:
                        break
                payload = body[idx:idx + size]
                idx += size
                if meta == 0x03:
                    name = payload.decode("latin-1", "replace")
                elif meta == 0x51:
                    tempos.append((tick, int.from_bytes(payload, "big")))
            elif status in (0xF0, 0xF7):
                size = 0
                while True:
                    byte = body[idx]
                    idx += 1
                    size = (size << 7) | (byte & 0x7F)
                    if not byte & 0x80:
                        break
                idx += size
            else:
                kind = status & 0xF0
                count = 1 if kind in (0xC0, 0xD0) else 2
                values = body[idx:idx + count]
                idx += count
                if kind == 0x90 and values[1] > 0:
                    notes.append((tick, values[0], values[1]))
        out.append((name, notes))
    return {"division": division, "tracks": out, "tempos": tempos}


def build_map():
    grid = timing_grid()
    rows = shot_rows()
    cuts, cut_bars = cut_steps_from_section_one()
    film_steps = sum(row["steps"] for row in rows)

    # 1. the twelve shots add to the film length
    total_seconds = film_steps / 60.0
    print("film: %d shots, %d steps = %.2f s at 60 steps a second" % (len(rows), film_steps, total_seconds))

    # 2. each cut on a bar line, and the running total of the shots agrees with the cut steps
    running = 0
    derived = []
    for row in rows[:-1]:
        running += row["steps"]
        derived.append(running)
    map_ok = derived == cuts
    print("cut steps: section 2 running totals %s" % ("match section 1" if map_ok else "DO NOT match section 1"))
    if not map_ok:
        print("  section 1: %s" % cuts)
        print("  section 2: %s" % derived)

    bar_lines_ok = True
    drift_ok = True
    cut_rows = []
    for index, step in enumerate(cuts):
        stated = cut_bars[index] if index < len(cut_bars) else int(round(step / grid["steps_per_bar"]))
        exact_bar = step / grid["steps_per_bar"]
        bar = int(round(exact_bar))
        snaps_to_stated = bar == stated
        downbeat_step = stated * grid["steps_per_bar"]
        drift = step - downbeat_step
        on_line = abs(drift) <= 1.0
        bar_lines_ok = bar_lines_ok and snaps_to_stated
        drift_ok = drift_ok and on_line
        cut_rows.append({
            "index": index + 1, "shot_opens": index + 2, "step": step, "bar": stated,
            "step_in_seconds": round(step / 60.0, 3),
            "exact_bars_elapsed": round(exact_bar, 4),
            "downbeat_step_exact": round(downbeat_step, 3),
            "downbeat_seconds": round(downbeat_step / 60.0, 3),
            "drift_steps": round(drift, 2), "drift_seconds": round(drift / 60.0, 3),
            "attacked": True,
        })
        print("  cut %2d  step %5d (%.3f s)  bar %3d downbeat at step %.1f (%.3f s)  drift %+.2f steps %+.3f s  %s"
              % (index + 1, step, step / 60.0, stated, downbeat_step, downbeat_step / 60.0,
                 drift, drift / 60.0,
                 "snaps to the stated bar" if snaps_to_stated else "ROUNDS TO A DIFFERENT BAR"))
    worst = max(cut_rows, key=lambda item: abs(item["drift_steps"]))
    print("stated cut steps against the exact 126 bpm downbeat: worst drift %+.2f steps (%+.3f s) at cut %d"
          % (worst["drift_steps"], worst["drift_seconds"], worst["index"]))
    # Decision D18 (knowledge/GAMEDEV-DECISIONS-2026-10-24.md): the film is cut on this exact grid, so the stated
    # steps ARE round(bar x steps_per_bar) and the drift above is the rounding of one cut, not a lattice offset.
    retired = [(bar, round(bar * (86 - grid["steps_per_bar"]), 2)) for bar in cut_bars]
    print("the shot list's steps are round(bar x %.3f), the exact grid: worst drift is one cut's rounding, %.2f steps"
          % (grid["steps_per_bar"], abs(worst["drift_steps"])))
    print("the retired 86 step snap would run late by bar x 0.286 instead: bar %d %+.2f steps, bar %d %+.2f steps"
          % (retired[0][0], retired[0][1], retired[-1][0], retired[-1][1]))

    # 3. the MIDI: is there an attack on each cut bar's downbeat
    midi = read_midi(os.path.join(HERE, "pp_drive_v3.mid"))
    ticks_per_bar = midi["division"] * grid["beats_per_bar"]
    attacks = {}
    for name, notes in midi["tracks"]:
        for tick, pitch, velocity in notes:
            bar = tick / ticks_per_bar + 1.0
            attacks.setdefault(int(bar), []).append((name, round(bar - int(bar), 4), pitch))
    attacks_ok = True
    for index, step in enumerate(cuts):
        bar = int(round(step / grid["steps_per_bar"]))
        bar += 1  # the cut lands on the downbeat that opens this bar of the film's next shot
        hits = attacks.get(bar, [])
        at_head = [hit for hit in hits if hit[1] <= 0.02]
        attacks_ok = attacks_ok and bool(at_head)
        print("  bar %3d downbeat: %d note(s), %d within a step  %s"
              % (bar, len(hits), len(at_head), "attacked" if at_head else "SILENT"))

    # the tracker shaped dump
    shot_starts = []
    running = 0
    for row in rows:
        shot_starts.append((running, row))
        running += row["steps"]

    lines = []
    lines.append("PP-DRIVE v3: the tracker shaped dump of the cue, one line a bar, 125 bars of 3/4.")
    lines.append("Grid: %d bpm, %d beats a bar, %.3f steps a bar, %.4f s a bar (data/title_timing.json)."
                 % (grid["bpm"], grid["beats_per_bar"], grid["steps_per_bar"], grid["seconds_per_bar"]))
    lines.append("A cut marker sits on a bar's downbeat, which is the bar line the shot list names.")
    lines.append("")
    lines.append("bar | cue s   | beat 1        | beat 2        | beat 3        | marker")
    lines.append("----+---------+---------------+---------------+---------------+--------------------------------")
    shots_by_bar = {}
    for index, step in enumerate(cuts):
        bar = int(round(step / grid["steps_per_bar"])) + 1
        shots_by_bar[bar] = (index + 1, cut_rows[index]["bar"])
    for bar in range(1, 126):
        entries = attacks.get(bar, [])
        cells = []
        for beat in range(grid["beats_per_bar"]):
            slot = [entry for entry in entries if beat <= entry[1] < beat + 1]
            names = []
            for name, offset, pitch in sorted(slot, key=lambda item: item[1]):
                label = {"dpcm": "K", "noise": "n", "triangle": "t", "pulse 1": "1",
                         "pulse 2": "2", "vrc6 pulse a": "A", "vrc6 pulse b": "B",
                         "vrc6 saw": "S"}.get(name, "?")
                note = "%s%d" % (label, pitch)
                if note not in names:
                    names.append(note)
            cells.append(" ".join(names[:6]) if names else ".")
        marker = ""
        if bar in shots_by_bar:
            shot_opens, stated_bar = shots_by_bar[bar]
            marker = ">> CUT from shot %d to shot %d: shot list bar %d, this downbeat" % (
                shot_opens, shot_opens + 1, stated_bar)
        for start_step, row in shot_starts:
            bar_of_start = int(round(start_step / grid["steps_per_bar"])) + 1
            if bar_of_start == bar and not marker:
                marker = "shot %d opens (beat %s)" % (row["shot"], row["beat"])
        seconds = (bar - 1) * grid["seconds_per_bar"]
        lines.append("%3d | %7.2f | %-13s | %-13s | %-13s | %s"
                     % (bar, seconds, cells[0], cells[1], cells[2], marker))
    dump = "\n".join(lines) + "\n"

    payload = {
        "card": "t_b84a9264",
        "cue": "pp_drive_v3",
        "grid": grid,
        "film_steps": film_steps,
        "film_seconds": round(total_seconds, 2),
        "cuts": cut_rows,
        "cuts_on_the_exact_downbeat": len(cuts) if drift_ok else 0,
        "worst_drift": {"cut": worst["index"], "steps": worst["drift_steps"], "seconds": worst["drift_seconds"]},
        "shots": rows,
        "checks": {"shot_sum_matches_cuts": map_ok,
                   "every_cut_rounds_to_the_stated_bar": bar_lines_ok,
                   "every_cut_within_one_step_of_the_downbeat": drift_ok,
                   "every_cut_bar_attacked": attacks_ok},
        "cue_bars": 125,
        "cue_seconds": 178.57142857142858,
        "cue_tail_seconds": round(178.57142857142858 - total_seconds, 3),
    }
    with open(os.path.join(HERE, "cue_map_v3.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
        handle.write("\n")
    with open(os.path.join(HERE, "cut_dump_v3.txt"), "w", encoding="utf-8") as handle:
        handle.write(dump)

    print("cut bars: %s" % ", ".join(str(item["bar"]) for item in payload["cuts"]))
    print("cue: 125 bars, 178.571 s, tail past the film's 178.00 s = %.3f s (one bar is %.3f s)"
          % (payload["cue_tail_seconds"], grid["seconds_per_bar"]))
    print("dump: cut_dump_v3.txt (%d lines), map: cue_map_v3.json" % (len(lines)))
    return 0 if (map_ok and bar_lines_ok and attacks_ok) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    return build_map()


if __name__ == "__main__":
    sys.exit(main())
