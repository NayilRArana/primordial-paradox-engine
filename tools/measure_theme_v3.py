"""Measure the title theme v3 render for card MUS-V3.

Reads the version 3 score, the arranged MIDI and the WAV that
tools/render_chip.py just wrote, and reports, as numbers a check can fail on:

  * the loop region: it runs from the start of section A to the end of
    A_return, so the loop start is the first bar of section A and the loop end
    is the last bar of the file,
  * per voice peak and RMS, from each voice rendered on its own at its own mix
    gain, so "silent" and "clipping" are measured and not guessed,
  * the FFT pitch of the melody in three places:
        the first bar of section A (the Kronos motif, E5 C5 D5 E5),
        the first bar of section C trio (the Percy motif, E4 G4 B4),
        the fifth bar of section C trio (the Hadrian motif, D5 C#5),
  * an OGG encode of the same WAV.

The pitch of every note is taken from the score itself, not typed in here, so
the check cannot drift away from the composition.

Writes the merged report to the loop JSON next to the WAV. Usage:

    python tools/measure_theme_v3.py [--midi ...] [--wav ...] [--json ...]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import arrange  # noqa: E402
import measure_theme_render as base  # noqa: E402

ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "assets", "audio", "title_theme_v3")
DEFAULT_SCORE = os.path.join(AUDIO, "score_v3.yaml")
DEFAULT_MIDI = os.path.join(AUDIO, "title_theme_v3.mid")
DEFAULT_WAV = os.path.join(AUDIO, "title_theme_v3.wav")
DEFAULT_JSON = os.path.join(AUDIO, "title_theme_v3_loop.json")

MELODY_VOICE = "vrc6_pulse_a"

# Which melody bar each check listens to, as (section, bar offset in section).
CHECKS = (
    ("A_bar_1_kronos", "A", 0),
    ("C_trio_bar_1_percy", "C_trio", 0),
    ("C_trio_bar_5_hadrian", "C_trio", 4),
)


def midi_hz(pitch):
    return 440.0 * 2.0 ** ((pitch - 69) / 12.0)


def fft_bar(signal, rate, bpm, beats_per_bar, bar, measured_on,
            band=(150.0, 1400.0)):
    """The measured pitch of every melody note of one bar.

    The window is the middle half of each note, so the attack and the release
    that bleeds into the next note stay out of it.
    """
    eighth = 60.0 / bpm / 2.0
    bar_seconds = beats_per_bar * 60.0 / bpm
    bar_start = (bar.number - 1) * bar_seconds
    rows = []
    for slot, length, pitch in bar.melody:
        if pitch is None:
            continue
        start = bar_start + slot * eighth
        note_seconds = length * eighth
        pad = note_seconds * 0.25
        lo = int(round((start + pad) * rate))
        hi = int(round((start + note_seconds - pad) * rate))
        expected = midi_hz(pitch)
        found = base.peak_hz(signal[lo:hi], rate, band) if 0 <= lo < hi <= signal.size else None
        off = base.cents(found, expected)
        rows.append({
            "note": arrange.midi_to_name(pitch),
            "midi_pitch": pitch,
            "slot": slot,
            "length_eighths": length,
            "bar_number": bar.number,
            "score_seconds": round(start, 3),
            "window_seconds": round((hi - lo) / float(rate), 3),
            "expected_hz": round(expected, 2),
            "found_hz": round(found, 2) if found else None,
            "cents_off": off,
            "within_1_percent": bool(off is not None and abs(off) <= 17.2),
        })
    return {"measured_on": measured_on,
            "bar": bar.number,
            "section": bar.section,
            "notes": rows,
            "all_within_1_percent": bool(rows) and all(r["within_1_percent"] for r in rows)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score", default=DEFAULT_SCORE)
    parser.add_argument("--midi", default=DEFAULT_MIDI)
    parser.add_argument("--wav", default=DEFAULT_WAV)
    parser.add_argument("--json", default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    score = arrange.load_score(args.score)
    bars = arrange.build_bars_v3(score)
    loop_start_bar = arrange.v3_loop_start_bar(score, bars)

    with open(args.json, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    data, rate = base.read_wav(args.wav)
    bpm = float(report["bpm"])
    beats_per_bar = int(report["beats_per_bar"])
    bar_seconds = beats_per_bar * 60.0 / bpm

    loop_start_sample = int(round((loop_start_bar - 1) * bar_seconds * rate))
    loop_end_sample = len(data)
    edge = min(int(round(0.005 * rate)), len(data) // 4)
    head = data[loop_start_sample:loop_start_sample + edge]
    tail = data[max(0, loop_end_sample - edge):loop_end_sample]
    step = int(abs(int(data[loop_end_sample - 1]) - int(data[loop_start_sample])))
    report["loop"] = {
        "loop_start_section": (score.get("meta") or {}).get("loop_start_section"),
        "loop_end_section": (score.get("meta") or {}).get("loop_end_section"),
        "loop_start_bar": loop_start_bar,
        "loop_start_sample": loop_start_sample,
        "loop_start_seconds": round(loop_start_sample / rate, 6),
        "loop_end_bar": len(bars),
        "loop_end_sample": loop_end_sample,
        "loop_bars": len(bars) - loop_start_bar + 1,
        "loop_seconds": round((loop_end_sample - loop_start_sample) / rate, 6),
        "wrap_step": step,
        "wrap_step_dbfs": round(20.0 * np.log10(max(step, 1) / 32767.0), 2),
        "head_peak_dbfs": base.dbfs(float(np.abs(head).max()) if head.size else 0.0),
        "tail_peak_dbfs": base.dbfs(float(np.abs(tail).max()) if tail.size else 0.0),
        "edge_window_ms": 5,
    }

    signals, levels = base.voice_signals(args.midi, len(data))
    report["per_voice"] = levels

    fft = {}
    for name, section, offset in CHECKS:
        chosen = [bar for bar in bars if bar.section == section]
        if offset >= len(chosen):
            raise ValueError("section %s has no bar %d" % (section, offset + 1))
        bar = chosen[offset]
        fft[name] = {
            "melody_voice": fft_bar(signals[MELODY_VOICE], rate, bpm, beats_per_bar,
                                    bar, "%s rendered on its own" % MELODY_VOICE),
            "in_mix_broadband": fft_bar(data, rate, bpm, beats_per_bar, bar,
                                        "the full mix"),
            "in_mix_melody_band": fft_bar(data, rate, bpm, beats_per_bar, bar,
                                          "the full mix, searched in 380 to 900 Hz",
                                          band=(380.0, 900.0)),
        }
    report["fft_checks"] = fft

    ogg = os.path.splitext(args.wav)[0] + ".ogg"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        done = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", args.wav,
             "-codec:a", "libvorbis", "-q:a", "6", ogg],
            capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if done.returncode == 0 and os.path.isfile(ogg):
            report["ogg"] = os.path.abspath(ogg)
        else:
            report["ogg_error"] = (done.stderr or "").strip()[:300]
    else:
        report["ogg_error"] = "ffmpeg not found on PATH"

    temporary = args.json + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    os.replace(temporary, args.json)

    print(json.dumps({"loop": report["loop"],
                      "per_voice": report["per_voice"],
                      "fft": {name: {"melody_voice": row["melody_voice"]["all_within_1_percent"],
                                     "in_mix_melody_band": row["in_mix_melody_band"]["all_within_1_percent"],
                                     "notes": [n["note"] for n in row["melody_voice"]["notes"]]}
                              for name, row in report["fft_checks"].items()},
                      "ogg": report.get("ogg") or report.get("ogg_error")},
                     indent=2))
    for name, row in report["fft_checks"].items():
        print(name)
        for note in row["melody_voice"]["notes"]:
            print("  %-4s bar %2d slot %d  expected %7.2f Hz  found %7s  %6s cents  %s"
                  % (note["note"], note["bar_number"], note["slot"], note["expected_hz"],
                     ("%.2f" % note["found_hz"]) if note["found_hz"] else "none",
                     ("%.2f" % note["cents_off"]) if note["cents_off"] is not None else "none",
                     "ok" if note["within_1_percent"] else "OUT"))
    silent = [v for v, row in report["per_voice"].items() if row["silent"]]
    clipping = [v for v, row in report["per_voice"].items() if row["clipping"]]
    print("silent voices: %s | clipping voices: %s" % (silent or "none", clipping or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
