"""Measure the title theme v2 render for card MUS-THEME-2.

Reads the arranged MIDI and the WAV that tools/render_chip.py just wrote, then
reports, as numbers a check can fail on:

  * the loop region (loop start bar from the score) and the seam at that point,
  * per voice peak and RMS, from each voice rendered on its own at its own mix
    gain, so "silent" and "clipping" are measured and not guessed,
  * the FFT pitch of the first five melody notes of bars 5 and 6, which the
    score says are A4 C5 E5 F5 E5,
  * an OGG encode of the same WAV.

Writes the merged report to the loop JSON next to the WAV. Usage:

    python tools/measure_theme_render.py [--wav ...] [--midi ...] [--json ...]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_chip  # noqa: E402

ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "assets", "audio", "title_theme_v2")
DEFAULT_MIDI = os.path.join(AUDIO, "title_theme_v2.mid")
DEFAULT_WAV = os.path.join(AUDIO, "title_theme_v2.wav")
DEFAULT_JSON = os.path.join(AUDIO, "title_theme_v2_loop.json")

LOOP_START_BAR = 5
EXPECTED = [("A4", 69, 440.00), ("C5", 72, 523.25), ("E5", 76, 659.26),
            ("F5", 77, 698.46), ("E5", 76, 659.26)]
# Slot and length in eighths of those five notes, straight from score.yaml.
EXPECTED_SLOTS = [(0, 3), (3, 1), (4, 2), (6, 4), (10, 2)]


def read_wav(path):
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise ValueError("expected 16 bit audio, got %d bytes per sample" % width)
    data = np.frombuffer(frames, dtype="<i2").astype(np.float64)
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, rate


def dbfs(value, full_scale=32767.0):
    if value <= 0:
        return None
    return round(20.0 * np.log10(value / full_scale), 2)


def peak_hz(segment, rate, band=(150.0, 1400.0)):
    """The strongest partial of a segment, interpolated between FFT bins."""
    if segment.size < 64:
        return None
    window = np.hanning(segment.size)
    spectrum = np.abs(np.fft.rfft(segment * window))
    freqs = np.fft.rfftfreq(segment.size, 1.0 / rate)
    band = np.where((freqs >= band[0]) & (freqs <= band[1]))[0]
    if band.size < 3:
        return None
    index = band[int(np.argmax(spectrum[band]))]
    if index <= 0 or index >= spectrum.size - 1:
        return freqs[index]
    left, middle, right = spectrum[index - 1], spectrum[index], spectrum[index + 1]
    denominator = left - 2.0 * middle + right
    offset = 0.0 if denominator == 0 else 0.5 * (left - right) / denominator
    return float(freqs[index] + offset * (freqs[1] - freqs[0]))


def cents(found, expected):
    if not found:
        return None
    return round(1200.0 * np.log2(found / expected), 2)


def fft_melody(signal, rate, bpm, beats_per_bar, measured_on,
               band=(150.0, 1400.0)):
    """Pitch of the five leitmotif notes in bars 5 and 6 of the score.

    Measured on the melody voice on its own: in the full mix the waltz bass and
    the saw stabs sit a few dB above the melody, so a broadband FFT peak picks
    whichever of them is strongest in the window instead of the melody. The mix
    is also measured with the search limited to the melody band, which shows the
    melody partials are present at the right frequencies inside the mix.
    """
    eighth = 60.0 / bpm / 2.0
    bar_seconds = beats_per_bar * 60.0 / bpm
    out = []
    for (name, pitch, expected_hz), (slot, length) in zip(EXPECTED, EXPECTED_SLOTS):
        start = ((LOOP_START_BAR - 1) * bar_seconds
                 + slot * eighth)
        note_seconds = length * eighth
        # The middle half of the note, so the attack and the release that
        # bleeds into the next note stay out of the window.
        pad = note_seconds * 0.25
        lo = int(round((start + pad) * rate))
        hi = int(round((start + note_seconds - pad) * rate))
        found = peak_hz(signal[lo:hi], rate, band) if 0 <= lo < hi <= signal.size else None
        off = cents(found, expected_hz)
        out.append({
            "note": name,
            "midi_pitch": pitch,
            "score_seconds": round(start, 3),
            "window_seconds": round((hi - lo) / float(rate), 3),
            "expected_hz": expected_hz,
            "found_hz": round(found, 2) if found else None,
            "cents_off": off,
            "within_1_percent": bool(off is not None and abs(off) <= 17.2),
        })
    return {"measured_on": measured_on,
            "notes": out,
            "all_five_within_1_percent": all(row["within_1_percent"] for row in out)}


def voice_signals(midi_path, total_samples):
    """Each voice rendered on its own at its own mix gain, plus its levels."""
    midi = render_chip.parse_midi(midi_path)
    to_seconds = render_chip.make_clock(midi["tempo"], midi["division"])
    us_per_qn = midi["tempo"][0][1]
    bpm = 60_000_000.0 / us_per_qn
    voices = render_chip.assign_voices_v2(midi["tracks"])
    legacy = render_chip.is_legacy_only(midi)
    signals = {}
    levels = {}
    for voice, track in sorted(voices.items()):
        if legacy:
            signal = render_chip.render_voice(voice, track, to_seconds, total_samples)
        else:
            signal = render_chip.render_voice_v2(voice, track, to_seconds,
                                                 total_samples, bpm)
        signals[voice] = signal
        peak = float(np.abs(signal).max()) if signal.size else 0.0
        rms = float(np.sqrt(np.mean(signal ** 2))) if signal.size else 0.0
        notes = len(track.notes)
        levels[voice] = {
            "notes": notes,
            "peak_dbfs": dbfs(peak, 1.0),
            "rms_dbfs": dbfs(rms, 1.0),
            "clipping": bool(peak >= 1.0),
            "silent": bool(notes == 0 or rms <= 0.0),
        }
    return signals, levels


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--midi", default=DEFAULT_MIDI)
    parser.add_argument("--wav", default=DEFAULT_WAV)
    parser.add_argument("--json", default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    with open(args.json, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    data, rate = read_wav(args.wav)
    bpm = float(report["bpm"])
    beats_per_bar = int(report["beats_per_bar"])
    bar_seconds = beats_per_bar * 60.0 / bpm

    loop_start_sample = int(round((LOOP_START_BAR - 1) * bar_seconds * rate))
    loop_bars = int(report.get("loop_bars") or round(len(data) / rate / bar_seconds))
    loop_end_sample = min(int(round(loop_bars * bar_seconds * rate)), len(data))
    edge = min(int(round(0.005 * rate)), len(data) // 4)
    head = data[loop_start_sample:loop_start_sample + edge]
    tail = data[max(0, loop_end_sample - edge):loop_end_sample]
    step = int(abs(int(data[loop_end_sample - 1]) - int(data[loop_start_sample])))
    report["loop"] = {
        "loop_start_bar": LOOP_START_BAR,
        "loop_start_sample": loop_start_sample,
        "loop_start_seconds": round(loop_start_sample / rate, 6),
        "loop_bars": loop_bars - (LOOP_START_BAR - 1),
        "loop_seconds": round((loop_end_sample - loop_start_sample) / rate, 6),
        "wrap_step": step,
        "wrap_step_dbfs": round(20.0 * np.log10(max(step, 1) / 32767.0), 2),
        "head_peak_dbfs": dbfs(float(np.abs(head).max()) if head.size else 0.0),
        "tail_peak_dbfs": dbfs(float(np.abs(tail).max()) if tail.size else 0.0),
        "edge_window_ms": 5,
        "whole_file_head_peak_dbfs": report.get("loop_edge_peak_head"),
    }
    signals, levels = voice_signals(args.midi, len(data))
    report["per_voice"] = levels
    melody_voice = "vrc6_pulse_a"
    report["fft_melody_bars_5_6"] = fft_melody(
        signals[melody_voice], rate, bpm, beats_per_bar,
        "%s rendered on its own" % melody_voice)
    report["fft_melody_bars_5_6_in_mix"] = fft_melody(
        data, rate, bpm, beats_per_bar, "the full mix")
    report["fft_melody_bars_5_6_in_mix_melody_band"] = fft_melody(
        data, rate, bpm, beats_per_bar,
        "the full mix, searched in 380 to 900 Hz (the melody band)",
        band=(380.0, 900.0))

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

    # Write through a temporary file, so an error mid dump never leaves a
    # truncated loop JSON behind (it did once, and the next run could not read it).
    temporary = args.json + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    os.replace(temporary, args.json)

    print(json.dumps({"loop": report["loop"],
                      "per_voice": report["per_voice"],
                      "fft": report["fft_melody_bars_5_6"],
                      "fft_in_mix": report["fft_melody_bars_5_6_in_mix"],
                      "ogg": report.get("ogg") or report.get("ogg_error")},
                     indent=2))
    ok = report["fft_melody_bars_5_6"]["all_five_within_1_percent"]
    ok_mix = report["fft_melody_bars_5_6_in_mix"]["all_five_within_1_percent"]
    ok_band = report["fft_melody_bars_5_6_in_mix_melody_band"]["all_five_within_1_percent"]
    silent = [v for v, row in report["per_voice"].items() if row["silent"]]
    clipping = [v for v, row in report["per_voice"].items() if row["clipping"]]
    print("melody A C E F E ok (melody voice): %s | ok (mix, melody band): %s | "
          "ok (mix, broadband): %s | silent voices: %s | clipping voices: %s"
          % (ok, ok_band, ok_mix, silent or "none", clipping or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
