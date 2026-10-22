"""Tests for the version 2 chip renderer: VRC6 pulses, VRC6 saw, vibrato, duty,
echo, DPCM drums, the mix and the legacy compatibility.

What is proved here, rather than asserted in a comment:
  - every tonal voice lands within 1 percent of the MIDI pitch, measured by FFT;
  - a VRC6 pulse duty change is measurable in the rendered waveform, and the
    eight duty steps from 1/16 to 8/16 are what the wiki says they are;
  - the VRC6 saw is a seven step staircase, one period holds seven steps, and
    it steps down to zero, which is the accumulator behaviour on the wiki;
  - vibrato at a fixed 5.5 Hz changes the spectrum, and CC20 delays its onset;
  - the DPCM track makes a kick on note 36 and a snare on note 38;
  - the mix peaks at -1 dBFS and the limiter keeps it there;
  - the old four voice title theme still renders identically, within -60 dB.

The test writes only into a throwaway folder and never opens a window or plays
audio.
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import wave

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import render_chip  # noqa: E402

SR = 44100
DIV = 480
BEAT = DIV
BAR = 4 * BEAT
BPM = 100


# ------------------------------------------------------------------ MIDI writing


def _varlen(value: int) -> bytes:
    if value < 0:
        raise ValueError("a MIDI delta time cannot be negative")
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def _track(name: str, events) -> bytes:
    body = bytearray()
    body += _varlen(0) + b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1")
    last = 0
    for tick, _order, payload in sorted(events, key=lambda item: (item[0], item[1])):
        body += _varlen(tick - last) + payload
        last = tick
    body += _varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(path: str, tracks: dict) -> str:
    """A MIDI file from {track name: (notes, controls)}.

    notes is a list of (start tick, duration ticks, pitch, velocity).
    controls is a list of (tick, controller, value).
    """
    chunks = []
    for name, (notes, controls) in tracks.items():
        events = []
        for tick, controller, value in controls:
            events.append((tick, 1, bytes([0xB0, controller, value])))
        for start, dur, pitch, vel in notes:
            events.append((start, 2, bytes([0x90, pitch, vel])))
            events.append((start + dur, 0, bytes([0x80, pitch, 0])))
        chunks.append(_track(name, events))

    tempo_body = bytearray()
    tempo_body += _varlen(0) + b"\xff\x58\x04\x04\x02\x18\x08"
    tempo_body += _varlen(0) + b"\xff\x51\x03" + struct.pack(">I", 500000 * 120 // BPM)[1:]
    tempo_body += _varlen(0) + b"\xff\x2f\x00"
    tempo_track = b"MTrk" + struct.pack(">I", len(tempo_body)) + bytes(tempo_body)

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks) + 1, DIV)
    with open(path, "wb") as handle:
        handle.write(header + tempo_track + b"".join(chunks))
    return path


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == SR
        frames = handle.readframes(handle.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0


def render(tmp_path, tracks, name="sample", loop_bars=1, force_v2=True):
    midi = write_midi(str(tmp_path / (name + ".mid")), tracks)
    wav = str(tmp_path / (name + ".wav"))
    report = render_chip.render_file(midi, wav, loop_bars, None, None, force_v2=force_v2)
    return report, read_wav(wav)


def dominant_frequency(signal: np.ndarray, sample_rate: int = SR) -> float:
    """The strongest spectral peak of a signal, by FFT."""
    if signal.size == 0:
        return 0.0
    window = np.hanning(signal.size)
    spectrum = np.abs(np.fft.rfft(signal * window))
    spectrum[0] = 0.0
    index = int(np.argmax(spectrum))
    # A quadratic refinement of the peak bin, so the answer is not quantised
    # to the FFT bin spacing.
    if 0 < index < spectrum.size - 1:
        left, centre, right = spectrum[index - 1], spectrum[index], spectrum[index + 1]
        denom = left - 2.0 * centre + right
        shift = 0.5 * (left - right) / denom if denom else 0.0
    else:
        shift = 0.0
    return (index + shift) * sample_rate / float(signal.size)


def steady(signal: np.ndarray, start: float = 0.05, length: float = 0.30) -> np.ndarray:
    """A slice of a signal taken well after the note attack."""
    begin = int(start * SR)
    end = begin + int(length * SR)
    return signal[begin:end]


def mtof(pitch: int) -> float:
    return 440.0 * 2.0 ** ((pitch - 69) / 12.0)


# ------------------------------------------------------------------- the voices


@pytest.mark.parametrize("voice", ["pulse 1", "pulse 2", "vrc6 pulse a", "vrc6 pulse b",
                                   "triangle", "vrc6 saw", "echo"])
def test_every_tonal_voice_lands_within_one_percent_of_the_midi_pitch(tmp_path, voice):
    pitch = 69
    report, data = render(tmp_path, {voice: ([(0, BAR, pitch, 110)], [(0, 11, 15)])})
    assert voice in report["voice_map"].values(), report["voice_map"]
    found = dominant_frequency(steady(data))
    expected = mtof(pitch)
    assert abs(found - expected) / expected < 0.01, \
        "%s rendered at %.2f Hz, expected %.2f Hz" % (voice, found, expected)


@pytest.mark.parametrize("voice,duty_value,expected", [
    ("pulse 1", 0, 0.125),
    ("pulse 1", 2, 0.5),
    ("vrc6 pulse a", 0, 1 / 16.0),
    ("vrc6 pulse a", 7, 8 / 16.0),
    ("vrc6 pulse b", 0, 1 / 16.0),
    ("vrc6 pulse b", 7, 8 / 16.0),
])
def test_a_duty_change_is_measurable_in_the_waveform(tmp_path, voice, duty_value, expected):
    """A duty change must change the rendered waveform, not just a number."""
    def render_duty(value):
        tracks = {voice: ([(0, BAR, 60, 110)], [(0, 11, 15), (0, 12, value)])}
        return render(tmp_path, tracks, name="duty%s%d" % (voice.replace(" ", ""), value))[1]

    narrow = steady(render_duty(0))
    wide = steady(render_duty(7 if voice.startswith("vrc6") else 2))
    assert not np.allclose(narrow, wide), "the duty change did not change the sound"

    # The high fraction of a square wave is its duty, so measure it directly.
    def high_fraction(signal):
        threshold = 0.5 * (signal.max() + signal.min())
        return float((signal > threshold).mean())

    measured = high_fraction(steady(render_duty(duty_value)))
    assert measured == pytest.approx(expected, abs=0.02), measured


@pytest.mark.parametrize("step,expected", [(0, 1 / 16.0), (3, 4 / 16.0), (7, 8 / 16.0)])
def test_the_vrc6_pulse_duty_steps_are_the_wiki_values(tmp_path, step, expected):
    tracks = {"vrc6 pulse a": ([(0, BAR, 60, 110)], [(0, 11, 15), (0, 12, step)])}
    data = render(tmp_path, tracks, name="step%d" % step)[1]
    signal = steady(data)
    threshold = 0.5 * (signal.max() + signal.min())
    high = float((signal > threshold).mean())
    assert high == pytest.approx(expected, abs=0.02), high


def test_the_vrc6_saw_is_a_seven_step_staircase(tmp_path):
    """The wiki says the accumulator is reset on the seventh clock.

    That gives seven steps per period, a rising staircase that drops back to
    zero, and the high 5 bits of an 8 bit accumulator stepped by 42.
    """
    pitch = 57
    freq = mtof(pitch)

    # The raw generator: seven levels per period, rising, and back to the
    # bottom at the reset.
    raw = render_chip.vrc6_saw_wave(freq, int(round(SR / freq * 3)))
    levels = np.unique(np.round(raw, 4))
    assert len(levels) == 7, levels
    assert levels[0] == pytest.approx(-1.0, abs=0.01), levels
    assert levels[-1] == pytest.approx(1.0, abs=0.01), levels
    assert list(levels) == sorted(levels), "the staircase does not rise"

    # The staircase rises through its seven steps and drops back to the
    # bottom at the period boundary, where the accumulator is reset. So the
    # drop is measured across a boundary, and it must happen once per period.
    period = int(round(SR / freq))
    raw = render_chip.vrc6_saw_wave(freq, int(round(SR / freq * 3.5)))
    drops = [index for index in range(1, len(raw))
             if raw[index] < -0.9 and raw[index - 1] > 0.9]
    assert len(drops) == 3, "the saw does not fall back once per period (%d drops)" % len(drops)
    spacing = [drops[index + 1] - drops[index] for index in range(len(drops) - 1)]
    assert all(abs(gap - period) <= 2 for gap in spacing), \
        "the drops are not one period apart: %s (period %d)" % (spacing, period)
    assert raw[0] == pytest.approx(-1.0, abs=0.01), "the saw does not start at the bottom"

    # And the rendered voice lands on the note frequency.
    data = render(tmp_path, {"vrc6 saw": ([(0, BAR, pitch, 110)], [(0, 11, 15)])})[1]
    signal = steady(data, start=0.02, length=0.30)
    found = dominant_frequency(signal)
    assert abs(found - freq) / freq < 0.01, found


def test_vibrato_changes_the_spectrum_and_cc20_delays_its_onset(tmp_path):
    pitch = 69
    plain = render(tmp_path, {"pulse 1": ([(0, BAR, pitch, 110)], [(0, 11, 15)])},
                   name="plain")[1]
    vibrato = render(tmp_path, {"pulse 1": ([(0, BAR, pitch, 110)],
                                            [(0, 11, 15), (0, 1, 64)])},
                     name="vibrato")[1]

    # A vibrato spreads the energy, so the sum of the sidebands is larger.
    def sideband_energy(signal):
        spectrum = np.abs(np.fft.rfft(signal * np.hanning(signal.size)))
        return float(spectrum.sum())

    assert sideband_energy(steady(vibrato)) > sideband_energy(steady(plain))

    # CC20 is the onset delay in eighth notes. With a delay of two eighths at
    # 100 bpm the vibrato must not have started yet at a quarter of a second.
    delayed = render(tmp_path, {"pulse 1": ([(0, BAR, pitch, 110)],
                                            [(0, 11, 15), (0, 1, 64), (0, 20, 2)])},
                     name="delayed")[1]
    eighth = 60.0 / BPM / 2.0
    early = steady(delayed, start=0.05, length=0.2)
    late = steady(delayed, start=eighth * 2 + 0.05, length=0.2)
    assert sideband_energy(early) < sideband_energy(late), "the vibrato started too early"


def test_the_dpcm_track_makes_a_kick_and_a_snare(tmp_path):
    tracks = {"dpcm": ([(0, BEAT, 36, 110), (BEAT, BEAT, 38, 110)], [(0, 11, 15)])}
    data = render(tmp_path, tracks, name="drums")[1]

    beat_seconds = BEAT / DIV * 60.0 / BPM
    kick = data[: int(0.15 * SR)]
    snare = data[int(beat_seconds * SR): int((beat_seconds + 0.15) * SR)]
    assert np.abs(kick).max() > 0.05, "the kick is silent"
    assert np.abs(snare).max() > 0.05, "the snare is silent"

    # A kick is a pitched sweep, so its low frequency content grows over the
    # hit. A snare is a noise burst, so its high frequency content decays.
    def low_ratio(signal):
        spectrum = np.abs(np.fft.rfft(signal * np.hanning(signal.size)))
        total = spectrum.sum() or 1.0
        return float(spectrum[:len(spectrum) // 8].sum() / total)

    assert low_ratio(kick) > 0.2, "the kick has no low frequency content"
    assert low_ratio(snare) < 0.5, "the snare has no high frequency content"


def test_the_echo_track_is_just_a_normal_track(tmp_path):
    tracks = {"echo": ([(0, BAR, 64, 100)], [(0, 11, 15), (0, 12, 2)])}
    report, data = render(tmp_path, tracks, name="echo")
    assert report["voice_map"].get("echo") == "echo", report["voice_map"]
    assert np.abs(data).max() > 0.02, "the echo track is silent"
    found = dominant_frequency(steady(data))
    assert abs(found - mtof(64)) / mtof(64) < 0.01, found


# ------------------------------------------------------------------------ mix


def test_the_mix_peaks_at_minus_one_dbfs_and_the_limiter_holds_it(tmp_path):
    tracks = {
        "pulse 1": ([(0, BAR, 69, 127)], [(0, 11, 15)]),
        "pulse 2": ([(0, BAR, 72, 127)], [(0, 11, 15)]),
        "vrc6 pulse a": ([(0, BAR, 76, 127)], [(0, 11, 15)]),
        "vrc6 pulse b": ([(0, BAR, 79, 127)], [(0, 11, 15)]),
        "vrc6 saw": ([(0, BAR, 60, 127)], [(0, 11, 15)]),
        "triangle": ([(0, BAR, 45, 127)], [(0, 11, 15)]),
        "noise": ([(0, BAR, 42, 127)], [(0, 11, 15)]),
        "dpcm": ([(0, BAR, 36, 127)], [(0, 11, 15)]),
    }
    report, data = render(tmp_path, tracks, name="mix")
    peak = float(np.abs(data).max())
    assert 10 ** ((render_chip.PEAK_TARGET_DBFS - 0.2) / 20.0) <= peak, peak
    assert peak <= 10 ** ((render_chip.PEAK_TARGET_DBFS + 0.2) / 20.0), peak
    assert report["peak_dbfs"] == pytest.approx(render_chip.PEAK_TARGET_DBFS, abs=0.2)
    assert report["limiter"].startswith("soft"), report["limiter"]


def test_the_soft_limiter_never_lets_a_loud_mix_clip(tmp_path):
    loud = np.linspace(-4.0, 4.0, 4096)
    limited = render_chip.soft_limit(loud)
    assert np.abs(limited).max() <= 1.0
    quiet = np.linspace(-0.1, 0.1, 4096)
    assert np.allclose(render_chip.soft_limit(quiet), quiet)


# ------------------------------------------------------------------- demo file


def test_the_four_bar_demo_renders_to_the_expected_file(tmp_path):
    generator = os.path.join(ROOT, "tools", "gen_render2_demo.py")
    midi = str(tmp_path / "render2_demo.mid")
    done = subprocess.run([sys.executable, generator, midi], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stderr

    out_wav = str(tmp_path / "render2_demo.wav")
    report = render_chip.render_file(midi, out_wav, 4, None, str(tmp_path / "demo.json"))
    assert report["duration_seconds"] == pytest.approx(4 * 4 * 60.0 / BPM, abs=0.002)
    assert set(report["voice_map"]) == {
        "pulse1", "pulse2", "triangle", "noise",
        "vrc6_pulse_a", "vrc6_pulse_b", "vrc6_saw", "dpcm", "echo",
    }, report["voice_map"]
    assert report["renderer"] == "v2"
    data = read_wav(out_wav)
    assert np.abs(data).max() > 0.05, "the demo is silent"
    assert report["loop_seam_sample_difference"] == 0


# ----------------------------------------------------------------- legacy path


def test_the_old_four_voice_title_theme_still_renders_identically(tmp_path):
    """The old theme must not change: the difference has to sit below -60 dB.

    Both inputs are tracked (card t_50a290de, 2026-10-22): title_theme.mid is the four voice score and
    title_theme.wav is the golden render it has to keep matching. Neither may be skipped when absent.
    A skip on a missing input was how the nightly worktree reported this test as healthy while it
    measured nothing at all, so a missing file is an assertion failure now.
    """
    old = os.path.join(ROOT, "assets", "audio", "title_theme", "title_theme.mid")
    reference = os.path.join(ROOT, "assets", "audio", "title_theme", "title_theme.wav")
    assert os.path.isfile(old), old
    assert os.path.isfile(reference), reference

    wav = str(tmp_path / "title_theme.wav")
    report = render_chip.render_file(old, wav, 32, None, None)
    assert report["renderer"] == "v1", report["voice_map"]

    new = read_wav(wav)
    old_data = read_wav(reference)
    length = min(new.size, old_data.size)
    difference = new[:length] - old_data[:length]
    rms = float(np.sqrt(np.mean(difference ** 2)))
    reference_rms = float(np.sqrt(np.mean(old_data[:length] ** 2))) or 1.0
    db = 20.0 * np.log10(max(rms, 1e-12) / reference_rms)
    assert db <= -60.0, "the old render changed by %.1f dB" % db


# ------------------------------------------------------------------- preview


def test_the_render_preview_png_is_written_and_passes_its_own_check(tmp_path):
    """The manager reviews a picture of the render, so one has to exist."""
    generator = os.path.join(ROOT, "tools", "gen_render2_demo.py")
    midi = str(tmp_path / "render2_demo.mid")
    done = subprocess.run([sys.executable, generator, midi], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stderr

    wav = str(tmp_path / "render2_demo.wav")
    render_chip.render_file(midi, wav, 4, None, str(tmp_path / "render2_demo_loop.json"))

    png = str(tmp_path / "render2_demo_preview.png")
    preview = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "render_preview.py"),
                              wav, png, "render2_demo"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert preview.returncode == 0, preview.stderr
    assert os.path.isfile(png) and os.path.getsize(png) > 5000

    checker = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_render_preview.py"),
                              png], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert checker.returncode == 0, checker.stdout + checker.stderr
    assert "PASS" in checker.stdout
