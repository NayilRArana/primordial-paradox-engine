"""measure_demo_voices.py: what each voice contributes to the demo mix.

A render can pass every per voice test and still have one voice missing from
the mix, so each track of the demo is rendered on its own and its level is
measured. The numbers are printed and the check fails if any voice is silent
or if a voice dominates the mix.

Usage:
    measure_demo_voices.py [path.mid]
"""

from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import render_chip  # noqa: E402

DEMO = os.path.join(ROOT, "assets", "audio", "render2_demo", "render2_demo.mid")
SCRATCH = os.path.join(ROOT, "output", "render2_demo_voice_probe.wav")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    midi = argv[0] if argv else DEMO
    if not os.path.isfile(midi):
        print("the demo MIDI is not on this machine: %s" % midi)
        return 1

    parsed = render_chip.parse_midi(midi)
    to_seconds = render_chip.make_clock(parsed["tempo"], parsed["division"])
    voices = render_chip.assign_voices_v2(parsed["tracks"])

    end_tick = 0
    for track in voices.values():
        for _start, end, _pitch, _vel in track.notes:
            end_tick = max(end_tick, end)
    total = int(round(to_seconds(end_tick) * render_chip.SR)) + 1
    bpm = 60_000_000.0 / parsed["tempo"][0][1]

    levels = {}
    for voice, track in voices.items():
        signal = render_chip.render_voice_v2(voice, track, to_seconds, total, bpm)
        peak = float(np.abs(signal).max()) if signal.size else 0.0
        rms = float(np.sqrt(np.mean(signal ** 2))) if signal.size else 0.0
        levels[voice] = (peak, rms, track.name)

    mix_peak = max(peak for peak, _rms, _name in levels.values())
    problems = []
    for voice in sorted(levels):
        peak, rms, name = levels[voice]
        share = peak / mix_peak if mix_peak else 0.0
        print("  %-14s %-14s peak %.4f  rms %.5f  share %5.1f%%"
              % (voice, name, peak, rms, share * 100.0))
        if peak < 0.001:
            problems.append("%s is silent" % voice)
        elif share < 0.01:
            problems.append("%s is below 1 percent of the loudest voice" % voice)

    if problems:
        for problem in problems:
            print("  FAIL %s" % problem)
        return 1
    print("  PASS every one of the %d voices is audible in the mix" % len(levels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
