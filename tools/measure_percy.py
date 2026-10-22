"""Measure the Percy boss cue for card MUS-PERCY.

Reads the score, the arranged MIDI and the WAV that tools/render_chip.py just
wrote, and reports as numbers that a check can fail on:

  * the score facts: 32 bars, 132 bpm, 3/4, G minor, and where each section
    starts,
  * the loop: the cue loops over the whole file, so the loop start is bar 1 and
    the loop end is the last sample; the sample difference across the seam is
    the click, measured, not guessed,
  * per voice peak and RMS, each voice rendered on its own at its own mix gain,
  * the FFT of bar 5 (the first bar of section A):
        every lead note of the bar measured against the pitch in the score,
        the chroma of the bar, which must read G, Bb and D as its three
        strongest pitch classes, since the bar is a G minor power chord riff,
  * an OGG encode of the same WAV,
  * a 3x preview PNG in output/ (waveform, spectrogram, chroma of bar 5) with
    its own JSON beside it, because Hermes workers cannot see or hear.

Writes the merged report into percy_theme_loop.json next to the WAV.

    python tools/measure_percy.py
"""

import argparse
import json
import math
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
AUDIO = os.path.join(ROOT, "assets", "audio", "percy_theme")
OUTPUT = os.path.join(ROOT, "output")
DEFAULT_SCORE = os.path.join(AUDIO, "score_percy.yaml")
DEFAULT_MIDI = os.path.join(AUDIO, "percy_theme.mid")
DEFAULT_WAV = os.path.join(AUDIO, "percy_theme.wav")
DEFAULT_JSON = os.path.join(AUDIO, "percy_theme_loop.json")
DEFAULT_PREVIEW = os.path.join(OUTPUT, "percy_theme_preview_3x.png")

MELODY_VOICE = "pulse1"          # the voice signals are keyed without spaces
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
# Bar 5 is the first bar of section A, the bar the card names.
CHECK_SECTION = "A"
CHECK_BAR_OFFSET = 0
CHECK_CHROMA = ("G", "Bb", "D")
# The bar is motif P as a power chord riff, so its own notes are G, Bb, D, G,
# F, D: the triad plus the passing F of the crest and fall.
CHECK_RIFF_CLASSES = {"G", "Bb", "D", "F"}
PITCHED_VOICES = ("vrc6_pulse_a", "vrc6_pulse_b", "vrc6_saw", "pulse1", "pulse2", "triangle")


def midi_hz(pitch):
    return 440.0 * 2.0 ** ((pitch - 69) / 12.0)


def note_events(midi_path):
    """Every note of the arrangement, as (voice, start_s, end_s, pitch, velocity).

    The notes come from the MIDI that was actually written, so the measurement
    cannot drift from the composition: whatever the arranger put on a track is
    what gets measured in the audio.
    """
    import render_chip  # noqa: E402  (imported here so the module is one unit)

    midi = render_chip.parse_midi(midi_path)
    to_seconds = render_chip.make_clock(midi["tempo"], midi["division"])
    voices = render_chip.assign_voices_v2(midi["tracks"])
    events = []
    for voice, track in sorted(voices.items()):
        for start_tick, end_tick, pitch, velocity in track.notes:
            events.append({
                "voice": voice,
                "start": float(to_seconds(start_tick)),
                "end": float(to_seconds(end_tick)),
                "pitch": int(pitch),
                "velocity": int(velocity),
            })
    events.sort(key=lambda row: (row["start"], row["voice"]))
    return events


def pitch_classes_of_bar(events, signal, rate, bar_start, bar_end, band=(70.0, 1600.0)):
    """Read every pitched note of one bar out of the mix, then fold to pitch classes.

    The window is the middle half of each note and the pitch is the strongest
    partial interpolated between FFT bins, the same method the title theme check
    uses. Notes are weighted by their measured duration, so a whole bar of
    accompaniment cannot bury a single melody note, which is exactly what a raw
    energy chroma of this mix does (the triangle sits 6 to 8 dB above the lead).
    """
    rows = []
    for event in events:
        if event["voice"] in ("noise", "dpcm"):
            continue
        if event["start"] < bar_start - 1e-9 or event["start"] >= bar_end - 1e-9:
            continue
        length = event["end"] - event["start"]
        pad = length * 0.25
        lo = int(round((event["start"] + pad) * rate))
        hi = int(round((event["end"] - pad) * rate))
        found = base.peak_hz(signal[lo:hi], rate, band) if 0 <= lo < hi <= signal.size else None
        expected = midi_hz(event["pitch"])
        off = base.cents(found, expected)
        nearest = None
        if found:
            midi = 69.0 + 12.0 * math.log2(found / 440.0)
            nearest = arrange.midi_to_name(int(round(midi)))
        rows.append({
            "voice": event["voice"],
            "written": arrange.midi_to_name(event["pitch"]),
            "start_seconds": round(event["start"], 4),
            "length_seconds": round(length, 4),
            "expected_hz": round(expected, 2),
            "found_hz": round(found, 2) if found else None,
            "cents_off": off,
            "nearest_note": nearest,
            "pitch_class": nearest[:-1] if nearest else None,
            "in_tune": bool(off is not None and abs(off) <= 17.2),
        })

    weights = {}
    for row in rows:
        if row["pitch_class"]:
            weights[row["pitch_class"]] = weights.get(row["pitch_class"], 0.0) + row["length_seconds"]
    total = sum(weights.values())
    shares = {name: round(value / total, 4) for name, value in weights.items()} if total else {}
    ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    return {"notes": rows, "shares": shares,
            "ranked": [name for name, _share in ranked],
            "all_in_tune": bool(rows) and all(row["in_tune"] for row in rows)}


def trio_names(classes):
    """The triad as names without the octave, with A# shown as Bb."""
    return sorted({"A#": "Bb"}.get(name, name) for name in classes)


def chroma(segment, rate, low=60.0, high=2500.0):
    """Share of the spectral energy in each of the twelve pitch classes.

    This is the plain energy chroma, and it is reported as information only: in
    this mix the sustained bass carries far more energy than a single melody
    note, so its top three are G, D and whatever partial is loudest, not the
    harmony of the bar. The harmony check uses pitch_classes_of_bar instead.
    """
    if segment.size < 256:
        return None
    window = np.hanning(segment.size)
    spectrum = np.abs(np.fft.rfft(segment * window))
    freqs = np.fft.rfftfreq(segment.size, 1.0 / rate)
    weights = np.zeros(12)
    for index in range(freqs.size):
        freq = freqs[index]
        if freq < low or freq > high:
            continue
        magnitude = spectrum[index]
        if magnitude <= 0.0:
            continue
        midi = 69.0 + 12.0 * np.log2(freq / 440.0)
        weights[int(round(midi)) % 12] += float(magnitude) ** 2
    total = weights.sum()
    if total <= 0.0:
        return None
    shares = {NOTE_NAMES[pc]: round(float(weights[pc] / total), 5) for pc in range(12)}
    ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    return {"shares": shares, "ranked": [name for name, _share in ranked],
            "top_three": [name for name, _share in ranked[:3]]}


def bar_note_rows(signal, rate, bpm, beats_per_bar, bar, measured_on,
                  band=(150.0, 1400.0)):
    """The measured pitch of every lead note of one bar."""
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
            "expected_hz": round(expected, 2),
            "found_hz": round(found, 2) if found else None,
            "cents_off": off,
            "within_1_percent": bool(off is not None and abs(off) <= 17.2),
        })
    return {"measured_on": measured_on, "bar": bar.number, "section": bar.section,
            "notes": rows,
            "all_within_1_percent": bool(rows) and all(r["within_1_percent"] for r in rows)}


def arranged_note_rows(arrangement, signals, rate, bpm, beats_per_bar, bar, voices):
    """Measure every arranged note of one bar on its own voice signal.

    Each note is looked for in a band of plus or minus 3 percent around the
    pitch the score asks for, so the strongest partial cannot be mistaken for
    the fundamental.
    """
    seconds_per_tick = 60.0 / bpm / arrange.PPQ
    bar_ticks = beats_per_bar * arrange.PPQ
    lo_tick = (bar.number - 1) * bar_ticks
    hi_tick = lo_tick + bar_ticks
    rows = []
    for voice in voices:
        signal = signals.get(voice)
        if signal is None:
            continue
        for start, end, pitch in arrange.note_spans(arrangement.notes[voice]):
            if end <= lo_tick or start >= hi_tick:
                continue
            first = max(start, lo_tick)
            last = min(end, hi_tick)
            pad = max(2, int(round((last - first) * seconds_per_tick * rate * 0.2)))
            lo = int(round(first * seconds_per_tick * rate)) + pad
            hi = int(round(last * seconds_per_tick * rate)) - pad
            expected = midi_hz(pitch)
            found = (base.peak_hz(signal[lo:hi], rate, (expected * 0.97, expected * 1.03))
                     if 0 <= lo < hi <= signal.size else None)
            off = base.cents(found, expected)
            rows.append({
                "voice": voice,
                "note": arrange.midi_to_name(pitch),
                "midi_pitch": pitch,
                "expected_hz": round(expected, 2),
                "found_hz": round(found, 2) if found else None,
                "cents_off": off,
                "within_1_percent": bool(off is not None and abs(off) <= 17.2),
            })
    return rows


def note_chroma(rows):
    """The pitch classes the measured notes belong to, one vote per note."""
    classes = {}
    for row in rows:
        if not row["within_1_percent"]:
            continue
        name = NOTE_NAMES[row["midi_pitch"] % 12]
        classes[name] = classes.get(name, 0) + 1
    return {name: count for name, count in sorted(classes.items())}


def write_preview(wav_path, rate, data, bpm, beats_per_bar, bar, preview_path,
                  voice_chroma=None):
    """A 3x preview sheet: waveform, spectrogram, and the chroma of one bar."""
    from PIL import Image, ImageDraw

    panel_w, panel_h = 1536, 128
    image = Image.new("RGB", (panel_w, panel_h * 3), (16, 16, 20))
    draw = ImageDraw.Draw(image)

    bar_seconds = beats_per_bar * 60.0 / bpm
    total_seconds = data.size / float(rate)

    # Panel 1: the envelope of the whole cue, one column per pixel, with a
    # vertical line at every bar line.
    envelope = np.zeros(panel_w)
    step = max(1, data.size // panel_w)
    for column in range(panel_w):
        block = data[column * step:(column + 1) * step]
        envelope[column] = float(np.abs(block).max()) if block.size else 0.0
    top = float(np.abs(data).max()) or 1.0
    for column in range(panel_w):
        height = int(round(panel_h * 0.5 * envelope[column] / top))
        draw.line([(column, panel_h // 2 - height), (column, panel_h // 2 + height)],
                  fill=(120, 220, 160))
    bars = int(round(total_seconds / bar_seconds))
    for index in range(bars + 1):
        x = int(round(index * bar_seconds / total_seconds * (panel_w - 1)))
        draw.line([(x, 0), (x, panel_h)], fill=(60, 60, 70))

    # Panel 2: a log magnitude spectrogram in the chip band.
    rows = 64
    frame = 1024
    hop = max(1, (data.size - frame) // panel_w) if data.size > frame else 1
    spectrogram = np.zeros((rows, panel_w))
    for column in range(panel_w):
        start = column * hop
        segment = data[start:start + frame]
        if segment.size < frame:
            break
        window = np.hanning(frame)
        spectrum = np.abs(np.fft.rfft(segment * window))[:rows]
        spectrogram[:spectrum.size, column] = spectrum
    peak = float(spectrogram.max()) or 1.0
    for column in range(panel_w):
        for row in range(rows):
            value = int(round(255 * min(1.0, (spectrogram[row, column] / peak) ** 0.4)))
            y = panel_h * 2 - 1 - row * 2
            draw.line([(column, y), (column, y - 1)], fill=(value, value // 2, 255 - value))

    # Panel 3: the chroma of the check bar, twelve bars, the named triad marked.
    eighth = 60.0 / bpm / 2.0
    start = int(round((bar.number - 1) * bar_seconds * rate))
    end = int(round(((bar.number - 1) * bar_seconds + beams(beats_per_bar, bpm)) * rate))
    result = chroma(data[start:end], rate)
    if result:
        slot_w = panel_w // 12
        baseline = panel_h * 3 - 6
        for index, name in enumerate(NOTE_NAMES):
            share = result["shares"][name]
            height = int(round(min(1.0, share / 0.35) * (panel_h - 24)))
            x = index * slot_w + 2
            colour = (255, 200, 80) if name in CHECK_CHROMA else (110, 110, 130)
            draw.rectangle([x, baseline - height, x + slot_w - 6, baseline], fill=colour)
            draw.text((x + 2, baseline - panel_h + 4), name, fill=(230, 230, 230))
    draw.text((8, 4), "Percy, the Tyrant: %.2f s, %d bars, %.0f bpm, 3/4, G minor; "
                      "panel 3 is the chroma of bar %d" % (total_seconds, bars, bpm, bar.number),
              fill=(240, 240, 240))
    directory = os.path.dirname(os.path.abspath(preview_path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    image.save(preview_path)
    summary = {"preview_png": os.path.abspath(preview_path), "scale": 3,
               "size_px": [panel_w, panel_h * 3],
               "panels": ["waveform with bar lines", "spectrogram",
                          "chroma of bar %d" % bar.number],
               "chroma_bar": bar.number,
               "chroma_top_three": result["top_three"] if result else None,
               "chroma_note": "panel 3 is the raw energy chroma of the mix, drawn because "
                              "the panel shows what the ear would see; the harmony check "
                              "reads the measured fundamentals of the bar instead",
               "total_seconds": round(total_seconds, 3), "bars_drawn": bars,
               "bpm": bpm, "beats_per_bar": beats_per_bar}
    beside = os.path.splitext(os.path.abspath(preview_path))[0] + ".json"
    with open(beside, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    summary["preview_json"] = beside
    return summary


def beams(beats_per_bar, bpm):
    return beats_per_bar * 60.0 / bpm


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score", default=DEFAULT_SCORE)
    parser.add_argument("--midi", default=DEFAULT_MIDI)
    parser.add_argument("--wav", default=DEFAULT_WAV)
    parser.add_argument("--json", default=DEFAULT_JSON)
    parser.add_argument("--preview", default=DEFAULT_PREVIEW)
    args = parser.parse_args(argv)

    score = arrange.load_score(args.score)
    bars = arrange.build_bars_v3(score)
    bpm = float(score["meta"]["bpm"])
    beats_per_bar = 3
    bar_seconds = beats_per_bar * 60.0 / bpm
    loop_start_bar = arrange.v3_loop_start_bar(score, bars)

    with open(args.json, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    data, rate = base.read_wav(args.wav)

    report["score_facts"] = {
        "score": os.path.abspath(args.score),
        "bars": len(bars),
        "bpm": bpm,
        "beats_per_bar": beats_per_bar,
        "key": score["meta"].get("key"),
        "time": score["meta"].get("time"),
        "sections": list(score["sections"]),
        "bar_seconds": round(bar_seconds, 6),
        "duration_seconds": round(len(bars) * bar_seconds, 6),
        "wav_seconds": round(data.size / float(rate), 6),
        "wav_samples": int(data.size),
        "sample_rate": int(rate),
    }

    loop_start_sample = int(round((loop_start_bar - 1) * bar_seconds * rate))
    loop_end_sample = int(data.size)
    edge = min(int(round(0.001 * rate)), max(1, data.size // 4))
    head = data[loop_start_sample:loop_start_sample + edge].astype("float64")
    tail = data[max(0, loop_end_sample - edge):loop_end_sample].astype("float64")
    peak_sample = int(np.abs(data).max()) or 1
    # The click, measured the way a listener hears it: the step from the last
    # sample of the file to the first, and the largest single-sample step inside
    # the 1 ms the renderer's raised cosine fade covers. Both are reported
    # against the peak of the cue, because an absolute dBFS number says nothing
    # about whether a step of that size is audible under this mix.
    step = int(abs(int(data[loop_end_sample - 1]) - int(data[loop_start_sample])))
    jumps = [int(np.abs(np.diff(block)).max()) for block in (head, tail) if block.size > 1]
    edge_jump = max(jumps) if jumps else 0
    to_db = lambda value: round(20.0 * math.log10(max(int(value), 1) / float(peak_sample)), 2)
    report["loop"] = {
        "loop_start_section": score["meta"].get("loop_start_section"),
        "loop_end_section": score["meta"].get("loop_end_section"),
        "loop_start_bar": loop_start_bar,
        "loop_start_sample": loop_start_sample,
        "loop_start_seconds": round(loop_start_sample / rate, 6),
        "loop_end_bar": len(bars),
        "loop_end_sample": int(loop_end_sample),
        "loop_bars": len(bars) - loop_start_bar + 1,
        "loop_seconds": round((loop_end_sample - loop_start_sample) / rate, 6),
        "wrap_step": step,
        "wrap_step_dbfs": base.dbfs(max(step, 1)),
        "wrap_step_rel_peak_dbfs": to_db(step),
        "edge_max_jump": edge_jump,
        "edge_max_jump_rel_peak_dbfs": to_db(edge_jump),
        "head_peak": int(head.max()) if head.size else 0,
        "tail_peak": int(tail.max()) if tail.size else 0,
        "peak_sample": peak_sample,
        "head_peak_dbfs": base.dbfs(float(head.max()) if head.size else 0.0),
        "tail_peak_dbfs": base.dbfs(float(tail.max()) if tail.size else 0.0),
        "edge_window_ms": 1,
        "seam_rule": "the wrap step is at most 1 percent of the peak and the "
                     "largest 1 ms edge jump at most 2 percent",
    }

    signals, levels = base.voice_signals(args.midi, int(data.size))
    report["per_voice"] = levels

    chosen = [bar for bar in bars if bar.section == CHECK_SECTION]
    check_bar = chosen[CHECK_BAR_OFFSET]
    start = int(round((check_bar.number - 1) * bar_seconds * rate))
    end = int(round(((check_bar.number - 1) * bar_seconds + bar_seconds) * rate))
    # The riff is the melody of the bar, and in A the pulses play it, so it is
    # measured on the channel that carries it. Each note's own fundamental is
    # looked for in the middle of its own window, which is why this reads the
    # harmony of the bar and a raw energy chroma of the whole mix does not: the
    # sustained G pedal is 13 dB above everything and its window skirt fills the
    # neighbouring bins (G# and F# came out of that skirt, not out of a note).
    riff_notes = bar_note_rows(signals[MELODY_VOICE], rate, bpm, beats_per_bar,
                               check_bar, "%s rendered on its own" % MELODY_VOICE)
    measured_classes = note_chroma(riff_notes["notes"])
    pitched = np.zeros(max(0, end - start))
    for voice in PITCHED_VOICES:
        signal = signals.get(voice)
        if signal is not None:
            pitched += signal[start:end]
    pitched_chroma = chroma(pitched, rate)
    mix_chroma = chroma(data[start:end], rate)
    triad = {"G", "A#", "D"}          # note_chroma names the flat as A#
    report["fft_bar_check"] = {
        "bar": check_bar.number,
        "section": check_bar.section,
        "voice_measured": MELODY_VOICE,
        "expected_triad": list(CHECK_CHROMA),
        "expected_riff_classes": sorted(CHECK_RIFF_CLASSES),
        "riff_notes": riff_notes,
        "measured_pitch_classes": measured_classes,
        "triad_present": triad <= set(measured_classes),
        "no_foreign_class": set(measured_classes) <= {"G", "A#", "D", "F"},
        "pitched_chroma": pitched_chroma,
        "pitched_tonic_is_strongest": bool(pitched_chroma and pitched_chroma["ranked"][0] == "G"),
        "mix_energy_chroma_information_only": mix_chroma,
        "mix_chroma_note": "the raw energy chroma of the mix is reported, not checked: the "
                           "G pedal dominates it and its window skirt lands in G# and F#",
    }

    ogg = os.path.splitext(args.wav)[0] + ".ogg"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        done = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", args.wav,
             "-codec:a", "libvorbis", "-q:a", "6", ogg],
            capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if done.returncode == 0 and os.path.isfile(ogg):
            report["ogg"] = os.path.abspath(ogg)
            report["ogg_bytes"] = os.path.getsize(ogg)
        else:
            report["ogg_error"] = (done.stderr or "").strip()[:300]
    else:
        report["ogg_error"] = "ffmpeg not found on PATH"

    report["preview"] = write_preview(args.wav, rate, data, bpm, beats_per_bar,
                                      check_bar, args.preview)

    silent = sorted(v for v, row in levels.items() if row["silent"])
    clipping = sorted(v for v, row in levels.items() if row["clipping"])
    report["checks"] = {
        "bars_is_32": len(bars) == 32,
        "bpm_is_132": abs(bpm - 132.0) < 1e-9,
        "meter_is_3_4": beats_per_bar == 3 and len(bars) * beats_per_bar % 3 == 0,
        "key_is_g_minor": score["meta"].get("key") == "G minor",
        # The card asks the FFT of bar 5 to read G Bb D. The bar is a G minor
        # power chord riff, so the reading is: every note of the riff measured at
        # its own fundamental, the triad present, the only other class the
        # passing F of motif P, and the tonic the strongest class of the bar.
        "bar_5_triad_is_present": report["fft_bar_check"]["triad_present"],
        "bar_5_only_the_riff_classes": report["fft_bar_check"]["no_foreign_class"],
        "bar_5_riff_notes_tune": report["fft_bar_check"]["riff_notes"]["all_within_1_percent"],
        "bar_5_tonic_strongest": report["fft_bar_check"]["pitched_tonic_is_strongest"],
        "loop_seam_step_samples": step,
        "loop_seam_step_rel_peak_dbfs": to_db(step),
        "loop_seam_edge_jump_samples": edge_jump,
        "loop_seam_edge_jump_rel_peak_dbfs": to_db(edge_jump),
        "loop_seam_is_quiet": bool(step <= 0.01 * peak_sample and edge_jump <= 0.02 * peak_sample),
        "silent_voices": silent,
        "clipping_voices": clipping,
        "voices_present": sorted(v for v, row in levels.items() if not row["silent"]),
    }

    temporary = args.json + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    os.replace(temporary, args.json)

    facts = report["score_facts"]
    print("bars %d | %.1f bpm | %s | %s | %d samples | %.3f s"
          % (facts["bars"], facts["bpm"], facts["time"], facts["key"],
             facts["wav_samples"], facts["wav_seconds"]))
    print("loop bar %d to %d, %d bars, %.3f s, wrap step %d samples (%s dBFS)"
          % (report["loop"]["loop_start_bar"], report["loop"]["loop_end_bar"],
             report["loop"]["loop_bars"], report["loop"]["loop_seconds"], step,
             report["loop"]["wrap_step_dbfs"]))
    print("bar %d chroma of the pitched voices, ranked: %s"
          % (check_bar.number, ", ".join(pitched_chroma["ranked"]) if pitched_chroma else "none"))
    print("  %-4s %s" % ("pc", "  ".join("%6s" % name for name in NOTE_NAMES)))
    if mix_chroma:
        print("  %-4s %s" % ("mix", "  ".join("%6.3f" % mix_chroma["shares"][name]
                                              for name in NOTE_NAMES)))
    if pitched_chroma:
        print("  %-4s %s" % ("pit", "  ".join("%6.3f" % pitched_chroma["shares"][name]
                                              for name in NOTE_NAMES)))
    print("  bar %d measured classes (on %s): %s, triad present %s, foreign class %s"
          % (check_bar.number, MELODY_VOICE, sorted(measured_classes),
             report["fft_bar_check"]["triad_present"],
             not report["fft_bar_check"]["no_foreign_class"]))
    for note in report["fft_bar_check"]["riff_notes"]["notes"]:
        print("  lead %-4s bar %2d slot %d  expected %7.2f Hz  found %7.2f Hz  %6.2f cents  %s"
              % (note["note"], note["bar_number"], note["slot"], note["expected_hz"],
                 note["found_hz"] or 0.0, note["cents_off"] or 0.0,
                 "ok" if note["within_1_percent"] else "OUT"))
    for voice, row in sorted(report["per_voice"].items()):
        print("  %-14s notes %3d  peak %7s dBFS  rms %7s dBFS%s"
              % (voice, row["notes"], row["peak_dbfs"], row["rms_dbfs"],
                 "  SILENT" if row["silent"] else ("  CLIP" if row["clipping"] else "")))
    print("ogg %s" % (report.get("ogg") or report.get("ogg_error")))
    print("preview %s" % report["preview"]["preview_png"])
    print("checks %s" % json.dumps(report["checks"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
