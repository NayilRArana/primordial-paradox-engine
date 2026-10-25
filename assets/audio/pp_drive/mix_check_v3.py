"""mix_check_v3.py: will the drive cue survive a laptop speaker, and will it fight the engine?

Card CUE-DRIVE (t_b84a9264), the two listening conditions the card names. Reads two rendered WAVs:

    assets/audio/pp_drive/pp_drive_v3_humanized.wav   the cue this card delivers
    assets/audio/pp_01_title/pp_01_title.wav          the identity reference the card names

Nothing is written except the JSON report beside the cue. Four measurements, each printed for both
files so the cue is judged against the sound the project already accepted, not against a number
invented here.

  A weighted band share
      the energy in four bands as a share of the total, weighted by the A curve, which is how loud
      a band is rather than how much energy it holds. A laptop speaker plays roughly 300 Hz to
      12 kHz and gives up below 200 Hz, so the cue's message (the lead, the hats) has to hold up in
      the hook band or the film's clock is inaudible on the machine the player actually has.
      Absolute shares are meaningless for chip music (a triangle bass always wins on raw energy),
      so the check is against the reference: the cue must not be more than 10 percent short of the
      title cue's own hook share.

  crest
      peak minus RMS. Under 8 dB reads as squashed and a laptop makes it worse, because the only
      band it can reproduce is the one being pushed.

  low duty
      the share of 100 ms frames whose 80 to 320 Hz band is within 15 dB of the cue's loudest such
      frame. The engine loop the shot list names (car_engine_loop, an effect, not this cue) sits in
      that band. A cue that holds it at full level for the whole film has nowhere left for the
      engine, which is what "must not fight" means.

  engine band breathing
      the same band measured in the bars the car is at rest (1 to 2), while rolling (3 to 25) and
      across the first drum hole (24 to 26). Reported, not gated: the triangle plays a root on beat
      one in every section, so some level there is the arrangement, not an accident.

Exit 0 means every gated check passed. The numbers are printed either way.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
REFERENCE = os.path.join(REPO, "assets", "audio", "pp_01_title", "pp_01_title.wav")

BANDS = (("sub", 20.0, 80.0), ("engine", 80.0, 320.0), ("hook", 320.0, 3000.0), ("air", 3000.0, 16000.0))
MIN_CREST_DB = 8.0
MAX_LOW_DUTY = 0.92
LOW_NEAR_PEAK_DB = 15.0
HOOK_SHARE_TOLERANCE = 0.10
ENGINE_SHARE_TOLERANCE = 1.15


def a_weight(freqs):
    """The A weighting curve as a power multiplier, so a share can mean loudness."""
    f2 = np.square(np.maximum(freqs, 1e-6))
    num = (12194.0 ** 2) * np.square(f2)
    den = ((f2 + 20.6 ** 2)
           * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
           * (f2 + 12194.0 ** 2))
    ra = num / np.maximum(den, 1e-12)
    return np.power(10.0, (20.0 * np.log10(np.maximum(ra, 1e-12)) + 2.0) / 10.0)


def read_wav(path):
    with wave.open(path, "rb") as handle:
        params = handle.getparams()
        frames = handle.readframes(handle.getnframes())
    if params.sampwidth != 2:
        raise SystemExit("expected 16 bit PCM, got %d bytes a sample" % params.sampwidth)
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if params.nchannels > 1:
        samples = samples.reshape(-1, params.nchannels).mean(axis=1)
    return samples, params.framerate


def band_shares(samples, rate, size=8192):
    window = np.hanning(size).astype(np.float32)
    freqs = np.fft.rfftfreq(size, 1.0 / rate)
    weight = a_weight(freqs)
    totals = dict.fromkeys([band[0] for band in BANDS], 0.0)
    grand = 0.0
    count = 0
    for start in range(0, len(samples) - size, size):
        frame = samples[start:start + size] * window
        power = np.abs(np.fft.rfft(frame)) ** 2 * weight
        grand += float(power.sum())
        for name, low, high in BANDS:
            mask = (freqs >= low) & (freqs < high)
            totals[name] += float(power[mask].sum())
        count += 1
    if not grand:
        raise SystemExit("silent file")
    return {name: totals[name] / grand for name in totals}, count


def low_duty(samples, rate, frame_s=0.1):
    """Share of frames whose engine band is within LOW_NEAR_PEAK_DB of the loudest one."""
    size = int(rate * frame_s)
    window = np.hanning(size).astype(np.float32)
    freqs = np.fft.rfftfreq(size, 1.0 / rate)
    mask = (freqs >= BANDS[1][1]) & (freqs < BANDS[1][2])
    levels = []
    for start in range(0, len(samples) - size, size):
        frame = samples[start:start + size] * window
        power = np.abs(np.fft.rfft(frame)) ** 2
        levels.append(10.0 * np.log10(float(power[mask].sum()) + 1e-12))
    levels = np.array(levels)
    if not len(levels):
        return 0.0
    return float((levels >= float(levels.max()) - LOW_NEAR_PEAK_DB).mean())


def section_level(samples, rate, seconds_per_bar, bars, window_s=0.25):
    size = int(rate * window_s)
    window = np.hanning(size).astype(np.float32)
    freqs = np.fft.rfftfreq(size, 1.0 / rate)
    mask = (freqs >= BANDS[1][1]) & (freqs < BANDS[1][2])
    start = int((bars[0] - 1) * seconds_per_bar * rate)
    end = int(bars[1] * seconds_per_bar * rate)
    levels = []
    for offset in range(start, min(end, len(samples)) - size, size):
        frame = samples[offset:offset + size] * window
        power = np.abs(np.fft.rfft(frame)) ** 2
        levels.append(10.0 * np.log10(float(power[mask].sum()) + 1e-12))
    return float(np.median(levels)) if levels else float("nan")


def measure(path, bars=None, seconds=0.0):
    samples, rate = read_wav(path)
    if seconds:
        samples = samples[:int(seconds * rate)]
    peak = float(np.abs(samples).max())
    rms = float(np.sqrt(np.mean(samples ** 2)))
    peak_db = 20.0 * np.log10(max(peak, 1e-9))
    rms_db = 20.0 * np.log10(max(rms, 1e-9))
    shares, frames = band_shares(samples, rate)
    result = {
        "file": os.path.relpath(path, REPO).replace(os.sep, "/"),
        "duration_s": round(len(samples) / float(rate), 3),
        "sample_rate": rate,
        "frames": frames,
        "peak_dbfs": round(peak_db, 2),
        "rms_dbfs": round(rms_db, 2),
        "crest_db": round(peak_db - rms_db, 2),
        "band_share_percent_a_weighted": {name: round(shares[name] * 100.0, 2) for name, _, _ in BANDS},
        "low_duty_percent": round(low_duty(samples, rate) * 100.0, 2),
    }
    if bars is not None:
        seconds_per_bar = 60.0 / 126.0 * 3.0
        result["engine_band_median_db"] = {
            "at_rest_bars_1_2": round(section_level(samples, rate, seconds_per_bar, (1, 2)), 2),
            "rolling_bars_3_25": round(section_level(samples, rate, seconds_per_bar, (3, 25)), 2),
            "drum_hole_bars_24_26": round(section_level(samples, rate, seconds_per_bar, (24, 26)), 2),
        }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("wav", nargs="?", default=os.path.join(HERE, "pp_drive_v3_humanized.wav"))
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="analyse only the first N seconds of each file (a fast slice; the "
                             "delivered report is the whole file and leaves this at 0)")
    parser.add_argument("--report", default=os.path.join(HERE, "mix_check_v3.json"),
                        help="where to write the JSON report")
    args = parser.parse_args(argv)

    cue = measure(args.wav, bars=True, seconds=args.seconds)
    reference = measure(REFERENCE, seconds=args.seconds)

    print("cue:       %s" % cue["file"])
    print("reference: %s (the identity reference the card names)" % reference["file"])
    for label, item in (("cue", cue), ("reference", reference)):
        print("  %-9s %7.3f s  peak %6.2f dBFS  rms %6.2f dBFS  crest %5.2f dB"
              % (label, item["duration_s"], item["peak_dbfs"], item["rms_dbfs"], item["crest_db"]))
    print("  A weighted band share, cue against reference:")
    for name, low, high in BANDS:
        cue_share = cue["band_share_percent_a_weighted"][name]
        ref_share = reference["band_share_percent_a_weighted"][name]
        print("    %-6s %6.0f to %6.0f Hz   cue %5.1f percent   reference %5.1f percent   delta %+5.1f"
              % (name, low, high, cue_share, ref_share, cue_share - ref_share))
    print("  low duty (100 ms frames within %.0f dB of the loudest engine band frame): cue %.1f percent, reference %.1f percent"
          % (LOW_NEAR_PEAK_DB, cue["low_duty_percent"], reference["low_duty_percent"]))
    engine = cue["engine_band_median_db"]
    print("  engine band, cue median: at rest (bars 1 to 2) %.1f dB, rolling (bars 3 to 25) %.1f dB, drum hole (24 to 26) %.1f dB"
          % (engine["at_rest_bars_1_2"], engine["rolling_bars_3_25"], engine["drum_hole_bars_24_26"]))

    hook_floor = reference["band_share_percent_a_weighted"]["hook"] * (1.0 - HOOK_SHARE_TOLERANCE)
    engine_ceiling = reference["band_share_percent_a_weighted"]["engine"] * ENGINE_SHARE_TOLERANCE
    checks = {
        "crest_at_least_%.1f_db" % MIN_CREST_DB: cue["crest_db"] >= MIN_CREST_DB,
        "hook_share_at_least_%.1f_percent" % round(hook_floor, 1):
            cue["band_share_percent_a_weighted"]["hook"] >= hook_floor,
        "engine_share_at_most_%.1f_percent" % round(engine_ceiling, 1):
            cue["band_share_percent_a_weighted"]["engine"] <= engine_ceiling,
        "low_duty_at_most_%.2f" % MAX_LOW_DUTY: cue["low_duty_percent"] / 100.0 <= MAX_LOW_DUTY,
    }
    for name, ok in checks.items():
        print("  %-42s %s" % (name, "PASS" if ok else "FAIL"))
    breathes = min(engine["at_rest_bars_1_2"], engine["drum_hole_bars_24_26"]) < engine["rolling_bars_3_25"]
    print("  %-42s %s (reported, not gated)" % ("engine_band_breathes_under_the_film",
                                                "YES" if breathes else "NO"))

    report = {
        "card": "t_b84a9264",
        "cue": cue,
        "reference": reference,
        "thresholds": {"min_crest_db": MIN_CREST_DB,
                       "hook_share_floor_percent": round(hook_floor, 2),
                       "engine_share_ceiling_percent": round(engine_ceiling, 2),
                       "max_low_duty": MAX_LOW_DUTY,
                       "hook_tolerance": HOOK_SHARE_TOLERANCE,
                       "engine_tolerance": ENGINE_SHARE_TOLERANCE},
        "checks": {name: bool(ok) for name, ok in checks.items()},
        "engine_band_breathes": bool(breathes),
        "passed": all(checks.values()),
    }
    out = args.report
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
        handle.write("\n")
    print("report: %s (%s)" % (os.path.basename(out), "all gated checks passed" if report["passed"] else "a gated check failed"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
