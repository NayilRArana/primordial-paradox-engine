"""measure_legacy_difference.py: the number the legacy check reports.

Renders the old four voice title theme and compares it with the committed
reference render, and prints the difference in dB so the figure in the report
is measured rather than asserted.

Usage:
    measure_legacy_difference.py
"""

from __future__ import annotations

import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import render_chip  # noqa: E402


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        frames = handle.readframes(handle.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0


def main() -> int:
    old_mid = os.path.join(ROOT, "assets", "audio", "title_theme", "title_theme.mid")
    reference = os.path.join(ROOT, "assets", "audio", "title_theme", "title_theme.wav")
    if not (os.path.isfile(old_mid) and os.path.isfile(reference)):
        print("the old title theme is not on this machine")
        return 1

    out = os.path.join(ROOT, "output", "title_theme_legacy_check.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    report = render_chip.render_file(old_mid, out, 32, None, None)
    new = read_wav(out)
    old = read_wav(reference)
    length = min(new.size, old.size)
    difference = new[:length] - old[:length]
    rms = float(np.sqrt(np.mean(difference ** 2)))
    reference_rms = float(np.sqrt(np.mean(old[:length] ** 2))) or 1.0
    db = 20.0 * np.log10(max(rms, 1e-12) / reference_rms)
    print("  renderer: %s" % report["renderer"])
    print("  voice map: %s" % ", ".join("%s=%s" % kv for kv in sorted(report["voice_map"].items())))
    print("  samples: new %d, reference %d" % (new.size, old.size))
    print("  difference rms: %.3e" % rms)
    print("  difference: %.1f dB (the limit is -60 dB)" % db)
    print("  VERDICT: %s" % ("PASS" if db <= -60.0 else "FAIL"))
    return 0 if db <= -60.0 else 1


if __name__ == "__main__":
    sys.exit(main())
