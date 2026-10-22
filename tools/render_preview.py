"""render_preview.py: a 3x preview PNG of a rendered chip WAV.

The manager reviews visuals and cannot hear a WAV, so a render is delivered with
a picture of it: the waveform, the spectrum, the per voice gain table and the
loop numbers, all measured from the rendered file rather than from the score.

The preview is three times the size of a normal thumbnail, so small details
(the saw staircase, the duty steps, the drum hits) are still readable.

Usage:
    render_preview.py in.wav out.png [title]
"""

from __future__ import annotations

import json
import os
import struct
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

SCALE = 3
WIDTH = 640 * SCALE
PANEL = 220 * SCALE
MARGIN = 16 * SCALE
BACKGROUND = (18, 18, 26)
GRID = (46, 46, 62)
TEXT = (232, 232, 240)
DIM = (150, 150, 170)
ACCENT = (255, 196, 64)
WAVE = (120, 200, 255)
SPECTRUM = (150, 120, 255)


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        if handle.getsampwidth() != 2 or handle.getnchannels() != 1:
            raise ValueError("%s is not a 16 bit mono WAV" % path)
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0, rate


def wave_panel(draw, data, box, rate):
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    middle = (y0 + y1) // 2

    draw.rectangle([x0, y0, x1, y1], outline=GRID)
    draw.line([x0, middle, x1, middle], fill=GRID)

    # The envelope, as min and max per pixel column.
    columns = max(1, width)
    step = max(1, len(data) // columns)
    usable = (len(data) // step) * step
    if usable:
        blocks = data[:usable].reshape(-1, step)
        lows = blocks.min(axis=1)
        highs = blocks.max(axis=1)
        scale = (height / 2.0) * 0.92
        for index in range(len(lows)):
            x = x0 + index
            top = middle - highs[index] * scale
            bottom = middle - lows[index] * scale
            draw.line([x, top, x, bottom], fill=WAVE)

    seconds = len(data) / float(rate)
    draw.text((x0 + 6, y0 + 4), "waveform  %.2f s" % seconds, fill=TEXT)
    draw.text((x1 - 130, y0 + 4), "0 dBFS top", fill=DIM)


def spectrum_panel(draw, data, box, rate):
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    draw.rectangle([x0, y0, x1, y1], outline=GRID)

    window = np.hanning(len(data))
    spectrum = np.abs(np.fft.rfft(data * window))
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)
    limit = 12000.0
    keep = freqs <= limit
    spectrum = spectrum[keep]
    freqs = freqs[keep]
    if spectrum.max() > 0:
        spectrum = spectrum / spectrum.max()
    # Log frequency axis, so a low chip note is as visible as a high one.
    mapped = np.log2(np.maximum(freqs, 40.0) / 40.0)
    mapped = mapped / max(1e-9, np.log2(limit / 40.0))
    columns = max(1, width)
    edges = np.linspace(0.0, 1.0, columns + 1)
    for index in range(columns):
        low, high = edges[index], edges[index + 1]
        selection = (mapped >= low) & (mapped < high)
        if not selection.any():
            continue
        level = float(np.sqrt((spectrum[selection] ** 2).mean()))
        bar = int(level * (height - 24))
        if bar <= 0:
            continue
        x = x0 + index
        draw.line([x, y1 - bar, x, y1 - 1], fill=SPECTRUM)

    draw.text((x0 + 6, y0 + 4), "spectrum  0 to 12 kHz, log frequency", fill=TEXT)


def text_panel(draw, box, lines):
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], outline=GRID)
    y = y0 + 10
    for label, value, colour in lines:
        draw.text((x0 + 12, y), label, fill=DIM)
        draw.text((x0 + 250, y), value, fill=colour)
        y += 22


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    wav_path, png_path = argv[0], argv[1]
    title = argv[2] if len(argv) > 2 else os.path.basename(wav_path)

    data, rate = read_wav(wav_path)
    loop_json = os.path.splitext(wav_path)[0] + "_loop.json"
    report = {}
    if os.path.isfile(loop_json):
        with open(loop_json, "r", encoding="utf-8") as handle:
            report = json.load(handle)

    peak = float(np.abs(data).max()) if len(data) else 0.0
    rms = float(np.sqrt(np.mean(data ** 2))) if len(data) else 0.0
    lines = [
        ("duration", "%.3f s" % (len(data) / float(rate)), TEXT),
        ("peak", "%.2f dBFS" % (20.0 * np.log10(peak) if peak > 0 else -999.0), TEXT),
        ("rms", "%.2f dBFS" % (20.0 * np.log10(rms) if rms > 0 else -999.0), TEXT),
        ("renderer", str(report.get("renderer", "?")), ACCENT),
        ("limiter", str(report.get("limiter", "?")), TEXT),
        ("loop bars", str(report.get("loop_bars")), TEXT),
        ("seam sample difference", str(report.get("loop_seam_sample_difference")), TEXT),
    ]
    for voice, gain in sorted((report.get("voice_gains") or {}).items()):
        lines.append(("gain %s" % voice, "%.2f" % gain, TEXT))

    # The image grows with the text, so the last line never touches the edge.
    text_height = 22 * len(lines) + 24
    top = MARGIN + 46 * SCALE
    bottom = top + PANEL * 2 + MARGIN * 2
    height = bottom + text_height + MARGIN
    image = Image.new("RGB", (WIDTH, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw.text((MARGIN, MARGIN), title, fill=ACCENT)
    draw.text((MARGIN + 520 * SCALE, MARGIN),
              "44100 Hz mono 16 bit  chiptune preview", fill=DIM)

    wave_panel(draw, data, (MARGIN, top, WIDTH - MARGIN, top + PANEL), rate)
    spectrum_panel(draw, data, (MARGIN, top + PANEL + MARGIN,
                                WIDTH - MARGIN, top + PANEL * 2 + MARGIN), rate)

    text_panel(draw, (MARGIN, bottom, WIDTH - MARGIN, height - MARGIN), lines)

    os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
    image.save(png_path)
    print("render_preview: wrote %s (%dx%d)" % (os.path.abspath(png_path), WIDTH, height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
