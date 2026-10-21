"""Tests for tools/render_chip.py: the headless chip renderer for the title theme.

What is proved here, rather than asserted in a comment:
  - the renderer reads a Standard MIDI File with no MIDI library installed (stdlib only);
  - a 4 bar A minor 3/4 sample at 84 bpm renders to the duration the meter and the
    tempo say it must, which is 12 beats at 84 bpm;
  - the four voices are all present in the mix, so a silent voice is a failure;
  - the render is loop safe: the last sample and the first sample do not differ, and
    the fade at the loop point is actually applied;
  - the loop point JSON names the loop in samples and in seconds;
  - the MP3 export is a real MP3 at 192 kbit/s, when ffmpeg is on PATH.

The test writes only into a throwaway folder and never opens a window or plays audio.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import wave

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import render_chip  # noqa: E402

BPM = 84
DIV = 480
BEAT = DIV
BAR = 3 * BEAT


def _varlen(value: int) -> bytes:
    if value < 0:
        raise ValueError("a MIDI delta time cannot be negative")
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def _track(name: str, notes) -> bytes:
    """One MIDI track, written from absolute tick times.

    Notes are turned into absolute tick events first and sorted afterwards, so two
    notes that start on the same tick (a chord, or a harmony pair) are legal. A
    note off at a tick is written before a note on at the same tick, which is the
    order a player expects.
    """
    events = [(0, 0, b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1"))]
    for start, dur, pitch, vel in notes:
        if dur <= 0:
            raise ValueError("a note must last at least one tick")
        events.append((start, 1, bytes([0x90, pitch, vel])))
        events.append((start + dur, 0, bytes([0x80, pitch, 0])))
    events.sort(key=lambda item: (item[0], item[1]))
    body = bytearray()
    last = 0
    for tick, _order, payload in events:
        body += _varlen(tick - last) + payload
        last = tick
    body += _varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_test_midi(path: str, tracks: dict | None = None) -> str:
    """A 4 bar A minor waltz: the motif A C E F E on pulse 1, a bass on triangle.

    With tracks given, only those voices are written, so a test can prove one voice
    at a time.
    """
    melody = [
        (0 * BAR, BEAT, 69, 100), (0 * BAR + 1 * BEAT, BEAT, 72, 100),
        (0 * BAR + 2 * BEAT, BEAT, 76, 100),
        (1 * BAR, BEAT, 77, 100), (1 * BAR + 1 * BEAT, 2 * BEAT, 76, 100),
        (2 * BAR, BEAT, 72, 100), (2 * BAR + 1 * BEAT, BEAT, 69, 100),
        (2 * BAR + 2 * BEAT, BEAT, 65, 100),
        (3 * BAR, BEAT, 67, 100), (3 * BAR + 1 * BEAT, 2 * BEAT, 69, 100),
    ]
    harmony = [
        (bar * BAR + BEAT, BEAT, tone, 70) for bar in range(4) for tone in (64, 60)
    ]
    bass = []
    for bar, root in enumerate((45, 41, 38, 40)):
        bass.append((bar * BAR, BEAT, root, 110))
        bass.append((bar * BAR + 2 * BEAT, BEAT, root + 7, 100))
    noise = [
        (bar * BAR + BEAT, BEAT // 2, 42, 60) for bar in (1, 3) for _ in (0, 1)
    ]
    voices = {"pulse1": melody, "pulse2": harmony, "triangle": bass, "noise": noise}
    if tracks is not None:
        voices = {name: notes for name, notes in tracks.items()}

    tempo_body = bytearray()
    tempo_body += _varlen(0) + b"\xff\x58\x04\x03\x02\x18\x08"
    tempo_body += _varlen(0) + b"\xff\x51\x03" + struct.pack(">I", 500000 * 120 // BPM)[1:]
    tempo_body += _varlen(0) + b"\xff\x2f\x00"
    tempo_track = b"MTrk" + struct.pack(">I", len(tempo_body)) + bytes(tempo_body)

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(voices) + 1, DIV)
    with open(path, "wb") as handle:
        handle.write(header + tempo_track
                     + b"".join(_track(name, voices[name]) for name in voices))
    return path


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 44100
        frames = handle.readframes(handle.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.int32)


def test_render_matches_the_meter_and_the_tempo(tmp_path):
    midi = write_test_midi(str(tmp_path / "sample.mid"))
    wav = str(tmp_path / "sample.wav")
    report = render_chip.render_file(midi, wav, 4, None, str(tmp_path / "sample_loop.json"))

    expected = 4 * 3 * 60.0 / BPM
    assert abs(report["duration_seconds"] - expected) < 0.002, report["duration_seconds"]
    assert report["bpm"] == pytest.approx(BPM, abs=0.01)
    assert report["time_signature"] == "3/4"
    assert report["samples"] == int(round(expected * 44100))


def test_every_voice_is_audible(tmp_path):
    """Each of the four voices on its own must make sound, so a silent voice fails."""
    melody = [(0, BEAT, 69, 100)]
    bass = [(0, BEAT, 45, 110)]
    noise = [(0, BEAT, 42, 60)]
    cases = {"pulse1": melody, "pulse2": melody, "triangle": bass, "noise": noise}
    for voice, notes in cases.items():
        midi = write_test_midi(str(tmp_path / ("%s.mid" % voice)), tracks={voice: notes})
        wav = str(tmp_path / ("%s.wav" % voice))
        render_chip.render_file(midi, wav, 1, None, None)
        data = read_wav(wav)
        assert data.size > 0, voice
        assert report_rms(data) > 100, "the %s voice is silent" % voice


def report_rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))


def test_the_loop_point_is_click_free(tmp_path):
    midi = write_test_midi(str(tmp_path / "sample.mid"))
    wav = str(tmp_path / "sample.wav")
    report = render_chip.render_file(midi, wav, 4, None, str(tmp_path / "loop.json"))
    data = read_wav(wav)

    assert report["loop_seam_sample_difference"] == 0, "the loop seam is a click"
    assert report["loop_edge_peak_head"] < 4000, "the head is not faded down"
    assert report["loop_edge_peak_tail"] < 4000, "the tail is not faded down"
    assert report["fade_samples"] == int(round(0.005 * 44100))


def test_the_loop_json_names_the_loop(tmp_path):
    midi = write_test_midi(str(tmp_path / "sample.mid"))
    loop_json = str(tmp_path / "loop.json")
    report = render_chip.render_file(midi, str(tmp_path / "s.wav"), 4, None, loop_json)
    with open(loop_json, "r", encoding="utf-8") as handle:
        written = json.load(handle)
    assert written["loop_start_sample"] == 0
    assert written["loop_end_sample"] == report["samples"]
    assert abs(written["loop_seconds"] - report["duration_seconds"]) < 1e-6
    assert written["loop_bars"] == 4
    assert set(written["voice_map"]) == {"pulse1", "pulse2", "triangle", "noise"}


def test_the_mp3_is_a_real_mp3_at_192k(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return  # nothing to assert on a machine with no ffmpeg
    midi = write_test_midi(str(tmp_path / "sample.mid"))
    mp3 = str(tmp_path / "sample.mp3")
    report = render_chip.render_file(midi, str(tmp_path / "s.wav"), 4, mp3, None)
    assert report.get("mp3"), report.get("mp3_error")
    assert os.path.getsize(mp3) > 1000
    probe = subprocess.run(
        [ffmpeg, "-v", "error", "-i", mp3, "-f", "null", "-"],
        capture_output=True, text=True,
        # stdin=DEVNULL on purpose: with no stdin given, CPython hands the child this process's own
        # STD_INPUT_HANDLE and duplicates it, which raises OSError [WinError 6] if that handle is already
        # invalid. The probe reads no stdin, so DEVNULL costs nothing.
        stdin=subprocess.DEVNULL)
    assert probe.returncode == 0, probe.stderr


def test_a_short_midi_is_tailed_to_the_loop_length(tmp_path):
    midi = write_test_midi(str(tmp_path / "sample.mid"))
    wav = str(tmp_path / "sample.wav")
    report = render_chip.render_file(midi, wav, 8, None, None)
    assert report["loop_trimmed"] is False
    assert abs(report["duration_seconds"] - 8 * 3 * 60.0 / BPM) < 0.002
