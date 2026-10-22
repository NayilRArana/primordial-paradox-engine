"""render_chip.py: render a chiptune MIDI to WAV and MP3, loop safe.

A small, self contained NES style renderer. It reads a Standard MIDI File and
synthesises the voices directly, with no emulator, no window and no external
dependency beyond numpy.

Version 2 voices (7 chip voices plus a drum track):

  pulse 1      2A03 square, 50 percent duty (25 percent when the MIDI says so)
  pulse 2      2A03 square, 25 percent duty (50 percent when the MIDI says so)
  triangle     16 step NES triangle, fixed level
  noise        15 bit LFSR, period taken from the note number
  vrc6 pulse a Konami VRC6 square, 8 duty steps from 1/16 to 8/16
  vrc6 pulse b Konami VRC6 square, 8 duty steps from 1/16 to 8/16
  vrc6 saw     Konami VRC6 sawtooth, 6 bit DAC
  dpcm         short kick and snare samples, MIDI note 36 and 38

VRC6 saw reference (read on 2026-10-21, from the NESdev wiki):
  https://www.nesdev.org/wiki/VRC6_audio
  The CPU clock drives a 12 bit divider F. Every cycle the divider counts
  down until it reaches zero, at which point it reloads and clocks the
  accumulator, but the accumulator only reacts on every second clock. When
  clocked, the rate value A is added to an internal 8 bit accumulator and the
  high 5 bits of the accumulator are output while the channel is enabled.
  After A has been added 6 times, on the 7th clock the accumulator is reset to
  zero instead of A being added. With A = 42 the seven steps of one period are
  0, 42, 84, 126, 168, 210, 252, whose high 5 bits are 0, 5, 10, 15, 21, 26
  and 31, so the waveform is a seven step staircase that rises and then drops
  back to zero. The output frequency is f = CPU / (14 * (t + 1)), so one
  fundamental period holds exactly seven accumulator steps.

Voice assignment: by track name first ("pulse 1", "vrc6 saw", "dpcm", ...),
then by the order in which the tracks start playing. Control change 11 sets
the level of a voice, control change 12 sets its duty (or the noise loop bit),
control change 1 sets the vibrato depth and control change 20 sets the
vibrato onset delay in eighth notes. Vibrato runs at a fixed 5.5 Hz.

Each note gets a linear decay envelope from its own velocity, so a note fades
out over its own length instead of stopping dead.

Mix: the per voice gain table below, then a soft limiter, then the peak is
set to -1 dBFS.

Legacy compatibility: a MIDI that only uses the four 2A03 voices and only the
old control changes is rendered through the original code path, so an old
render such as title_theme.wav is reproduced sample for sample.

Loop handling: with --loop-bars the render is trimmed to exactly that many bars,
or tailed with silence when the MIDI is shorter, so the end of the last bar
lands on the loop point. A 5 ms fade is applied at both ends of the loop, and
the sample difference across the seam is reported, so a click is a number and
not a surprise.

Usage:
    render_chip.py in.mid out.wav --loop-bars 32
    render_chip.py in.mid out.wav --loop-bars 4 --no-mp3

Outputs: out.wav (44100 Hz, mono, 16 bit), out.mp3 (192 kbit/s, via ffmpeg) and
out_loop.json (the loop point in samples and seconds).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import wave

import numpy as np

SR = 44100
DEFAULT_TEMPO_US_PER_QN = 500000.0
FADE_MS = 5.0
MP3_BITRATE = "192k"

# NES APU noise period table, in CPU cycles (nesdev APU period table).
NOISE_PERIODS = [4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068]
# NES duty table: 12.5, 25, 50, 25 negated.
DUTY_TABLE = [0.125, 0.25, 0.5, 0.25]
# Mixer levels, matching the levels the Musikage NES synth uses.
GAIN = {"pulse1": 0.35, "pulse2": 0.30, "triangle": 0.45, "noise": 0.25}
ATTACK_MS = 1.0

# ---------------------------------------------------------------------------
# Version 2 header tables
# ---------------------------------------------------------------------------

# Per voice mix gain table. This is the header of the file on purpose: it is
# the one place a mixer level is decided, and a level change belongs next to
# the other chip constants, not buried in a function.
GAIN_TABLE = {
    "pulse1": 0.35,
    "pulse2": 0.30,
    "triangle": 0.45,
    "noise": 0.25,
    "vrc6_pulse_a": 0.32,
    "vrc6_pulse_b": 0.30,
    "vrc6_saw": 0.34,
    "echo": 0.22,
    "dpcm": 0.55,
}

# The peak the final mix is set to, in dBFS.
PEAK_TARGET_DBFS = -1.0
PEAK_TARGET = 10.0 ** (PEAK_TARGET_DBFS / 20.0)

# Soft limiter: the signal passes through untouched below the knee, and is
# compressed into the headroom above it with a tanh shaped curve.
LIMITER_KNEE = 0.8

# The VRC6 saw accumulator rate. 42 is the largest value that does not wrap the
# 8 bit accumulator over its six steps (NESdev wiki, read 2026-10-21).
VRC6_SAW_RATE = 42
VRC6_SAW_STEPS = 7

# Vibrato: fixed rate, depth from CC1, onset delay in eighth notes from CC20.
VIBRATO_RATE_HZ = 5.5
VIBRATO_MAX_SEMITONES = 2.0
VIBRATO_RAMP_S = 0.02

# DPCM drums: MIDI note to drum.
DPCM_KICK_NOTE = 36
DPCM_SNARE_NOTE = 38
DPCM_KICK_SECONDS = 0.16
DPCM_SNARE_SECONDS = 0.14


# ---------------------------------------------------------------- MIDI reading


def read_varlen(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("malformed variable length quantity in MIDI data")


class Track:
    def __init__(self) -> None:
        self.name = ""
        self.notes: list[tuple[int, int, int, int]] = []  # (start tick, end tick, pitch, velocity)
        self.cc: dict[int, list[tuple[int, int]]] = {}
        self.open: dict[int, tuple[int, int]] = {}


def parse_midi(path: str) -> dict:
    """Read a Standard MIDI File into tracks, a tempo map and a time signature."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"MThd":
        raise ValueError("%s is not a Standard MIDI File (no MThd header)" % path)
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, ntracks, division = struct.unpack(">hhh", data[8:14])
    if division <= 0:
        raise ValueError("SMPTE time division is not supported (division=%d)" % division)

    pos = 8 + header_len
    tracks: list[Track] = []
    tempo_events: list[tuple[int, int]] = []
    time_sig: tuple[int, int] | None = None

    for _ in range(ntracks):
        if data[pos : pos + 4] != b"MTrk":
            break
        length = struct.unpack(">I", data[pos + 4 : pos + 8])[0]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 8 + length
        track = Track()
        tick = 0
        ipos = 0
        status = 0
        while ipos < len(chunk):
            delta, ipos = read_varlen(chunk, ipos)
            tick += delta
            byte = chunk[ipos]
            if byte & 0x80:
                status = byte
                ipos += 1
            kind = status & 0xF0
            if status == 0xFF:
                meta = chunk[ipos]
                ipos += 1
                mlen, ipos = read_varlen(chunk, ipos)
                payload = chunk[ipos : ipos + mlen]
                ipos += mlen
                if meta == 0x03:
                    track.name = payload.decode("latin-1", "replace").strip()
                elif meta == 0x51 and mlen == 3:
                    tempo_events.append((tick, int.from_bytes(payload, "big")))
                elif meta == 0x58 and mlen >= 2:
                    if time_sig is None:
                        time_sig = (payload[0], 2 ** payload[1])
            elif status in (0xF0, 0xF7):
                mlen, ipos = read_varlen(chunk, ipos)
                ipos += mlen
            else:
                if kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    nbytes = 1 if kind in (0xC0, 0xD0) else 2
                    payload = chunk[ipos : ipos + nbytes]
                    ipos += nbytes
                    if kind == 0x90 and payload[1] > 0:
                        track.open[payload[0]] = (tick, payload[1])
                    elif kind == 0x80 or (kind == 0x90 and payload[1] == 0):
                        started = track.open.pop(payload[0], None)
                        if started is not None:
                            track.notes.append((started[0], tick, payload[0], started[1]))
                    elif kind == 0xB0:
                        track.cc.setdefault(payload[0], []).append((tick, payload[1]))
                else:
                    ipos += 1
        for pitch, (start, vel) in track.open.items():
            track.notes.append((start, tick, pitch, vel))
        track.notes.sort()
        tracks.append(track)

    if not tempo_events:
        tempo_events = [(0, int(DEFAULT_TEMPO_US_PER_QN))]
    tempo_events.sort()
    if tempo_events[0][0] != 0:
        tempo_events.insert(0, (0, int(DEFAULT_TEMPO_US_PER_QN)))
    if time_sig is None:
        time_sig = (4, 4)
    return {
        "format": fmt,
        "division": division,
        "tracks": tracks,
        "tempo": tempo_events,
        "time_sig": time_sig,
    }


def make_clock(tempo_events: list[tuple[int, int]], division: int):
    """Return a tick to seconds function built from the tempo map."""
    segments = []
    seconds = 0.0
    for index, (tick, us_per_qn) in enumerate(tempo_events):
        if index:
            prev_tick, prev_us = tempo_events[index - 1]
            seconds += (tick - prev_tick) * prev_us / 1e6 / division
        segments.append((tick, us_per_qn / 1e6 / division, seconds))

    def to_seconds(tick: int) -> float:
        chosen = segments[0]
        for segment in segments:
            if segment[0] <= tick:
                chosen = segment
            else:
                break
        start_tick, per_tick, start_seconds = chosen
        return start_seconds + (tick - start_tick) * per_tick

    return to_seconds


# ------------------------------------------------------------- voice assignment

VOICE_NAMES = ("pulse1", "pulse2", "triangle", "noise")

# The version 2 voice set, in the order the spare slots are filled.
VOICE_NAMES_V2 = (
    "pulse1", "pulse2", "triangle", "noise",
    "vrc6_pulse_a", "vrc6_pulse_b", "vrc6_saw", "echo", "dpcm",
)

# Track name fragments that name a version 2 voice. Longest first so that
# "vrc6 pulse a" is never read as a plain pulse.
_V2_NAME_TABLE = (
    ("vrc6pulsea", "vrc6_pulse_a"),
    ("vrc6pulseb", "vrc6_pulse_b"),
    ("vrc6saw", "vrc6_saw"),
    ("vrc6sawtooth", "vrc6_saw"),
    ("dpcm", "dpcm"),
    ("echo", "echo"),
)


def name_to_voice(name: str) -> str | None:
    low = name.lower().replace(" ", "").replace("_", "").replace("-", "")
    if not low:
        return None
    if "noise" in low or low in ("hat", "perc", "drums", "drum"):
        return "noise"
    if "tri" in low:
        return "triangle"
    if "pulse2" in low or low in ("p2", "sq2", "square2"):
        return "pulse2"
    if "pulse1" in low or low in ("p1", "sq1", "square1", "pulse"):
        return "pulse1"
    return None


def name_to_voice_v2(name: str) -> str | None:
    """Map a track name to a version 2 voice, or None if the name says nothing."""
    low = name.lower().replace(" ", "").replace("_", "").replace("-", "")
    if not low:
        return None
    for fragment, voice in _V2_NAME_TABLE:
        if fragment in low:
            return voice
    return name_to_voice(name)


def assign_voices(tracks: list[Track]) -> dict[str, Track]:
    """Map tracks to the four chip voices, by name first and by start order second."""
    voices: dict[str, Track] = {}
    for track in tracks:
        if not track.notes:
            continue
        voice = name_to_voice(track.name)
        if voice is None or voice in voices:
            continue
        voices[voice] = track
    remaining = [t for t in tracks if t.notes and t not in voices.values()]
    remaining.sort(key=lambda t: t.notes[0][0])
    for track, voice in zip(remaining, VOICE_NAMES):
        if voice in voices:
            continue
        voices[voice] = track
    return voices


def assign_voices_v2(tracks: list[Track]) -> dict[str, Track]:
    """Map tracks to the version 2 voice set.

    A named voice wins. A track whose name says nothing (an "echo" track is a
    normal track) takes the next free slot, and the 2A03 voices are filled
    first so a four voice file keeps the same assignment it always had.
    """
    voices: dict[str, Track] = {}
    for track in tracks:
        if not track.notes:
            continue
        voice = name_to_voice_v2(track.name)
        if voice is None or voice in voices:
            continue
        voices[voice] = track
    remaining = [t for t in tracks if t.notes and t not in voices.values()]
    remaining.sort(key=lambda t: t.notes[0][0])
    for track in remaining:
        for voice in VOICE_NAMES_V2:
            if voice in voices:
                continue
            voices[voice] = track
            break
    return voices


def is_legacy_only(midi: dict) -> bool:
    """True when the file can be rendered by the original four voice path.

    Legacy means: no version 2 voice names, and none of the version 2 control
    changes (CC1 vibrato depth, CC12 duty, CC20 vibrato delay).
    """
    for track in midi["tracks"]:
        if not track.notes:
            continue
        if name_to_voice_v2(track.name) not in (None, "pulse1", "pulse2", "triangle", "noise"):
            return False
        for controller in track.cc:
            if controller in (1, 12, 20):
                return False
    return True


# ------------------------------------------------------------------ synthesis


def pulse_wave(freq: float, count: int, duty: float) -> np.ndarray:
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    phase = (freq * np.arange(count) / SR) % 1.0
    return (phase < duty).astype(np.float64)


def triangle_wave(freq: float, count: int) -> np.ndarray:
    """16 step NES triangle, bipolar, 32 samples per period."""
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    phase = (freq * np.arange(count) / SR) % 1.0
    step = (phase * 32.0) % 32.0
    return 2.0 * np.abs(step - 16.0) / 16.0 - 1.0


def lfsr_bits(count: int, short_mode: bool) -> np.ndarray:
    """The APU 15 bit LFSR, short mode taps bit 6 instead of bit 1."""
    out = np.empty(count, dtype=np.uint8)
    reg = 1
    for i in range(count):
        out[i] = reg & 1
        if short_mode:
            fb = (reg & 1) ^ ((reg >> 6) & 1)
        else:
            fb = (reg & 1) ^ ((reg >> 1) & 1)
        reg = (reg >> 1) | (fb << 14)
    return out


# The 15 bit register cycles with period 32767, so one cycle covers every output.
# The two cycles (long mode and short mode) are fixed, so they are built once
# and shared. Building them per note was the render's bottleneck: the loop is
# 32767 steps in Python, and a 32 bar theme has hundreds of noise notes.
_LFSR_CACHE: dict[bool, np.ndarray] = {}


def lfsr_cycle(short_mode: bool) -> np.ndarray:
    if short_mode not in _LFSR_CACHE:
        _LFSR_CACHE[short_mode] = lfsr_bits(32767, short_mode)
    return _LFSR_CACHE[short_mode]


def noise_wave(pitch: int, count: int, short_mode: bool) -> np.ndarray:
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    index = min(15, max(0, pitch - 1))
    period = 93 if short_mode else NOISE_PERIODS[index]
    clock_rate = 1789772.5 / float(period)
    clocks = (np.arange(count) / SR * clock_rate).astype(np.int64)
    bits = lfsr_cycle(short_mode)
    return bits[clocks % 32767].astype(np.float64) * 2.0 - 1.0


def control_at(events: list[tuple[int, int]], to_seconds, times: np.ndarray, default: float) -> np.ndarray:
    """Per sample value of a stepwise control change list."""
    out = np.full(times.shape, default, dtype=np.float64)
    if not events:
        return out
    values = np.array([(to_seconds(tick), value) for tick, value in events], dtype=np.float64)
    index = np.searchsorted(values[:, 0], times, side="right") - 1
    ok = index >= 0
    out[ok] = values[index[ok], 1]
    return out


def render_voice(voice: str, track: Track, to_seconds, total_samples: int) -> np.ndarray:
    out = np.zeros(total_samples, dtype=np.float64)
    times = np.arange(total_samples) / SR
    cc11 = track.cc.get(11, [])
    cc12 = track.cc.get(12, [])
    level = control_at(cc11, to_seconds, times, 15.0) / 15.0 if cc11 else None
    duty_value = control_at(cc12, to_seconds, times, 2.0) if cc12 else None
    loop_value = control_at(cc12, to_seconds, times, 0.0) if cc12 else None

    for start_tick, end_tick, pitch, velocity in track.notes:
        start = int(round(to_seconds(start_tick) * SR))
        end = int(round(to_seconds(end_tick) * SR))
        if end <= start:
            continue
        start = max(0, start)
        end = min(total_samples, end)
        count = end - start
        if count <= 0:
            continue

        if voice == "triangle":
            wave = triangle_wave(440.0 * 2.0 ** ((pitch - 69) / 12.0), count)
        elif voice == "noise":
            short = bool(int(loop_value[start]) & 1) if loop_value is not None else False
            wave = noise_wave(pitch, count, short)
        else:
            if duty_value is not None:
                duty = DUTY_TABLE[int(duty_value[start]) & 3]
            else:
                duty = 0.5 if voice == "pulse1" else 0.25
            wave = pulse_wave(440.0 * 2.0 ** ((pitch - 69) / 12.0), count, duty)

        amp = velocity / 127.0
        if level is not None:
            amp = amp * float(level[start])
        if voice != "triangle":
            # A per note linear decay, from the note's own start to its own end.
            amp = amp * (1.0 - np.arange(count) / float(count))
        attack = max(1, int(round(ATTACK_MS * SR / 1000.0)))
        ramp = np.minimum(1.0, np.arange(count) / float(attack))
        out[start:end] += wave * amp * ramp
    return out * GAIN[voice]


# -------------------------------------------------------- version 2 synthesis


def vrc6_saw_wave(freq, count: int) -> np.ndarray:
    """The VRC6 sawtooth: a seven step staircase per period.

    See the header for the reference and the date it was read. The 8 bit
    accumulator is clocked with the rate value every second divider clock and
    is reset to zero on the seventh clock, so one period is seven steps of
    A, 2A, ... 6A, whose high 5 bits are the output.

    freq is either a single frequency in Hz or a per sample frequency array,
    so vibrato reaches this voice the same way it reaches the pulses.
    """
    if count <= 0:
        return np.zeros(count if count > 0 else 0, dtype=np.float64)
    freqs = np.asarray(freq, dtype=np.float64)
    if freqs.ndim == 0:
        if freqs <= 0:
            return np.zeros(count, dtype=np.float64)
        freqs = np.full(count, float(freqs))
    else:
        freqs = np.resize(freqs, count)
    # The step boundaries come from a float phase, not an integer division, so
    # the seven steps of one period land exactly on the period and the pitch
    # does not drift with the rounding of the step length.
    phase = np.cumsum(freqs) / SR
    step = np.floor(phase * VRC6_SAW_STEPS).astype(np.int64) % VRC6_SAW_STEPS
    accumulator = step * VRC6_SAW_RATE
    level = (accumulator >> 3).astype(np.float64) / 31.0
    return level * 2.0 - 1.0


def pulse_wave_v2(freqs: np.ndarray, duty: float) -> np.ndarray:
    """A square wave from a per sample frequency array."""
    if freqs.size == 0:
        return np.zeros(0, dtype=np.float64)
    phase = (np.cumsum(freqs) / SR) % 1.0
    return (phase < duty).astype(np.float64)


def triangle_wave_v2(freqs: np.ndarray) -> np.ndarray:
    if freqs.size == 0:
        return np.zeros(0, dtype=np.float64)
    phase = (np.cumsum(freqs) / SR) % 1.0
    step = (phase * 32.0) % 32.0
    return 2.0 * np.abs(step - 16.0) / 16.0 - 1.0


def vibrato_frequencies(base: float, count: int, depth: float, delay: float,
                         ramp: float = VIBRATO_RAMP_S) -> np.ndarray:
    """Per sample frequency with a 5.5 Hz vibrato that starts after a delay.

    The depth is in semitones, the delay in seconds. The vibrato fades in over
    the ramp so the note does not step at the moment it starts.
    """
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    if depth <= 0.0:
        return np.full(count, base, dtype=np.float64)
    times = np.arange(count) / SR
    since = times - delay
    active = since > 0.0
    ramp_up = np.clip(since / max(ramp, 1e-6), 0.0, 1.0)
    lfo = np.sin(2.0 * np.pi * VIBRATO_RATE_HZ * np.where(active, since, 0.0))
    semitones = depth * lfo * ramp_up
    return base * np.power(2.0, semitones / 12.0)


def dpcm_kick(count: int) -> np.ndarray:
    """A short kick: a sine whose pitch drops fast, plus a click at the start."""
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    times = np.arange(count) / SR
    duration = times[-1] + 1.0 / SR if count else 0.0
    sweep = 150.0 * np.exp(-times / 0.030) + 45.0
    phase = 2.0 * np.pi * np.cumsum(sweep) / SR
    body = np.sin(phase)
    env = np.exp(-times / 0.055)
    click = np.zeros(count, dtype=np.float64)
    click_length = min(count, int(round(0.004 * SR)))
    if click_length:
        click[:click_length] = np.linspace(1.0, 0.0, click_length)
    return (0.85 * body * env + 0.35 * click) * min(1.0, duration / 0.02 + 0.5)


def dpcm_snare(count: int) -> np.ndarray:
    """A short snare: a filtered noise burst with a fast decay.

    The high pass of white noise is unbounded, so it is normalised to its own
    peak before it is mixed. Without that, the burst level depends on the
    random draw and the drum track can leave full scale on its own.
    """
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    times = np.arange(count) / SR
    noise = np.random.default_rng(20261021).standard_normal(count)
    # A one pole high pass, so the burst is bright like a snare and not a hiss.
    bright = np.diff(noise, prepend=0.0)
    peak = float(np.abs(bright).max())
    if peak > 0:
        bright = bright / peak
    env = np.exp(-times / 0.035)
    body = 0.6 * np.sin(2.0 * np.pi * 190.0 * times) * np.exp(-times / 0.020)
    return (0.9 * bright * env + 0.3 * body)


def soft_limit(signal: np.ndarray, knee: float = LIMITER_KNEE) -> np.ndarray:
    """A soft limiter: linear below the knee, tanh shaped above it."""
    if signal.size == 0:
        return signal
    peak = float(np.abs(signal).max())
    if peak <= knee:
        return signal
    sign = np.sign(signal)
    magnitude = np.abs(signal)
    over = magnitude > knee
    out = signal.copy()
    headroom = 1.0 - knee
    out[over] = sign[over] * (knee + headroom * np.tanh((magnitude[over] - knee) / headroom))
    return out


def render_voice_v2(voice: str, track: Track, to_seconds, total_samples: int,
                    bpm: float) -> np.ndarray:
    """Render one version 2 voice into a full length buffer."""
    out = np.zeros(total_samples, dtype=np.float64)
    times = np.arange(total_samples) / SR
    cc11 = track.cc.get(11, [])
    cc12 = track.cc.get(12, [])
    cc1 = track.cc.get(1, [])
    cc20 = track.cc.get(20, [])

    # Level is a 0 to 15 chip volume. A value of 127 means full volume, so the
    # scale is clamped at 15: both the 0 to 15 chip convention and the 0 to 127
    # mixer convention then read the same way.
    level = None
    if cc11:
        level = np.minimum(control_at(cc11, to_seconds, times, 15.0), 15.0) / 15.0
    duty_value = control_at(cc12, to_seconds, times, 0.0) if cc12 else None
    depth_value = control_at(cc1, to_seconds, times, 0.0) if cc1 else None
    delay_value = control_at(cc20, to_seconds, times, 0.0) if cc20 else None

    eighth = 60.0 / bpm / 2.0
    attack = max(1, int(round(ATTACK_MS * SR / 1000.0)))

    for start_tick, end_tick, pitch, velocity in track.notes:
        start = int(round(to_seconds(start_tick) * SR))
        end = int(round(to_seconds(end_tick) * SR))
        if end <= start:
            continue
        start = max(0, start)
        end = min(total_samples, end)
        count = end - start
        if count <= 0:
            continue

        base = 440.0 * 2.0 ** ((pitch - 69) / 12.0)

        if voice == "dpcm":
            if pitch == DPCM_KICK_NOTE:
                count = min(count, int(round(DPCM_KICK_SECONDS * SR)))
            elif pitch == DPCM_SNARE_NOTE:
                count = min(count, int(round(DPCM_SNARE_SECONDS * SR)))
            else:
                continue
            wave = dpcm_kick(count) if pitch == DPCM_KICK_NOTE else dpcm_snare(count)
            amp = velocity / 127.0
        else:
            depth = 0.0
            delay = 0.0
            if depth_value is not None:
                depth = (float(depth_value[start]) / 127.0) * VIBRATO_MAX_SEMITONES
            if delay_value is not None:
                delay = float(delay_value[start]) * eighth
            freqs = vibrato_frequencies(base, count, depth, delay)

            if voice == "triangle":
                wave = triangle_wave_v2(freqs)
            elif voice == "noise":
                short = False
                if duty_value is not None:
                    short = bool(int(duty_value[start]) & 1)
                wave = noise_wave(pitch, count, short)
            elif voice == "vrc6_saw":
                wave = vrc6_saw_wave(freqs, count)
            else:
                # The duty is read per note. A VRC6 pulse has 8 steps from 1/16
                # to 8/16; a 2A03 pulse keeps its 4 step table.
                if duty_value is not None:
                    raw = int(duty_value[start])
                    if voice in ("vrc6_pulse_a", "vrc6_pulse_b"):
                        duty = (min(7, max(0, raw)) + 1) / 16.0
                    else:
                        duty = DUTY_TABLE[raw & 3]
                else:
                    duty = 0.25 if voice in ("vrc6_pulse_a", "vrc6_pulse_b") else (
                        0.5 if voice in ("pulse1", "echo") else 0.25
                    )
                wave = pulse_wave_v2(freqs, duty)

            amp = velocity / 127.0
            if voice not in ("triangle", "dpcm"):
                amp = amp * (1.0 - np.arange(count) / float(count))

        if level is not None:
            amp = amp * float(level[start])
        ramp = np.minimum(1.0, np.arange(count) / float(attack))
        out[start:start + len(wave)] += wave[:max(0, min(len(wave), total_samples - start))] * amp * ramp[:len(wave)]
    return out * GAIN_TABLE[voice]


# ------------------------------------------------------------------- the render


def render_file(midi_path: str, wav_path: str, loop_bars: int | None, mp3_path: str | None,
                loop_json_path: str | None, normalize: bool = True,
                force_v2: bool = False) -> dict:
    midi = parse_midi(midi_path)
    to_seconds = make_clock(midi["tempo"], midi["division"])
    legacy = is_legacy_only(midi) and not force_v2
    voices = assign_voices(midi["tracks"]) if legacy else assign_voices_v2(midi["tracks"])

    end_tick = 0
    for track in voices.values():
        for start_tick, end_tick_, _pitch, _vel in track.notes:
            end_tick = max(end_tick, end_tick_)
    total_seconds = to_seconds(end_tick) if end_tick else 0.0
    total_samples = int(round(total_seconds * SR)) + 1

    beats_per_bar = midi["time_sig"][0]
    us_per_qn = midi["tempo"][0][1]
    bpm = 60_000_000.0 / us_per_qn

    mix = np.zeros(total_samples, dtype=np.float64)
    for voice, track in voices.items():
        if legacy:
            mix += render_voice(voice, track, to_seconds, total_samples)
        else:
            mix += render_voice_v2(voice, track, to_seconds, total_samples, bpm)

    report: dict = {
        "source_midi": os.path.abspath(midi_path),
        "sample_rate": SR,
        "channels": 1,
        "bit_depth": 16,
        "bpm": round(bpm, 4),
        "beats_per_bar": beats_per_bar,
        "time_signature": "%d/%d" % midi["time_sig"],
        "voice_map": {voice: track.name or "(unnamed track %d)" % (midi["tracks"].index(track))
                      for voice, track in voices.items()},
        "source_duration_seconds": round(total_seconds, 6),
        "source_samples": int(total_samples),
        "renderer": "v1" if legacy else "v2",
    }

    if loop_bars:
        loop_seconds = loop_bars * beats_per_bar * 60.0 / bpm
        loop_samples = int(round(loop_seconds * SR))
        if total_samples > loop_samples:
            mix = mix[:loop_samples]
            report["loop_trimmed"] = True
        else:
            mix = np.concatenate([mix, np.zeros(loop_samples - total_samples, dtype=np.float64)])
            report["loop_trimmed"] = False
        report["loop_bars"] = loop_bars
        report["loop_seconds"] = round(loop_samples / SR, 6)
        report["loop_start_sample"] = 0
        report["loop_end_sample"] = int(loop_samples)
    else:
        report["loop_bars"] = None
        report["loop_seconds"] = round(len(mix) / SR, 6)
        report["loop_start_sample"] = 0
        report["loop_end_sample"] = int(len(mix))

    if len(mix) > 0:
        fade = min(int(round(FADE_MS * SR / 1000.0)), len(mix) // 2)
        if fade > 0:
            # A raised cosine ramp, not a linear one. A linear ramp still sits at
            # half level 2.5 ms from the seam, so a high frequency square wave
            # arrives at the loop point with a step. The raised cosine falls to
            # near zero much faster, so the seam is silent.
            ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade) / float(fade)))
            mix[:fade] *= ramp
            mix[-fade:] *= ramp[::-1]
        report["fade_ms"] = FADE_MS
        report["fade_samples"] = int(fade)
        report["fade_shape"] = "raised_cosine"

    if legacy:
        # The original path: scale the peak to 0.85 and nothing else, so an old
        # render is reproduced exactly.
        if normalize and len(mix) and np.abs(mix).max() > 0:
            peak_before = float(np.abs(mix).max())
            mix = mix / peak_before * 0.85
            report["peak_before_normalize"] = round(peak_before, 6)
        else:
            report["peak_before_normalize"] = round(float(np.abs(mix).max()), 6) if len(mix) else 0.0
        report["limiter"] = "none (legacy path)"
        report["peak_target_dbfs"] = round(20.0 * np.log10(0.85), 2)
    else:
        peak_before = float(np.abs(mix).max()) if len(mix) else 0.0
        report["peak_before_normalize"] = round(peak_before, 6)
        mix = soft_limit(mix)
        report["limiter"] = "soft (knee %.2f)" % LIMITER_KNEE
        if normalize and len(mix) and np.abs(mix).max() > 0:
            mix = mix / np.abs(mix).max() * PEAK_TARGET
        report["peak_target_dbfs"] = PEAK_TARGET_DBFS
        report["voice_gains"] = {voice: GAIN_TABLE[voice] for voice in sorted(voices)}

    data = (np.clip(mix, -1.0, 1.0) * 32767).astype("<i2")
    peak = int(np.abs(data).max()) if data.size else 0
    rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2))) if data.size else 0.0
    report["duration_seconds"] = round(len(data) / SR, 6)
    report["samples"] = int(len(data))
    report["peak"] = peak
    report["peak_dbfs"] = round(20.0 * np.log10(peak / 32767.0), 2) if peak else None
    report["rms"] = round(rms, 3)
    report["rms_dbfs"] = round(20.0 * np.log10(rms / 32767.0), 2) if rms else 0.0

    # Click measurement at the loop point. The wrap jump is the step from the last
    # sample to the first one, which is the step a player hears when the loop wraps.
    # The edge levels report how loud the faded edges are, so a loud edge would be
    # visible here even when the wrap step itself is zero. The window is 1 ms, the
    # region the fade actually covers: a longer window would report the level of
    # the music just after the fade, which says nothing about the seam.
    edge_window = min(int(round(0.001 * SR)), len(data))
    if len(data) > 1:
        tail = data[-edge_window:].astype(np.float64)
        head = data[:edge_window].astype(np.float64)
        report["loop_seam_sample_difference"] = int(abs(int(data[-1]) - int(data[0])))
        report["loop_edge_window_ms"] = 1
        report["loop_edge_peak_head"] = int(np.abs(head).max())
        report["loop_edge_peak_tail"] = int(np.abs(tail).max())
        edge_jumps = []
        for block in (head, tail):
            if block.size > 1:
                edge_jumps.append(int(np.abs(np.diff(block)).max()))
        report["loop_edge_max_jump"] = max(edge_jumps) if edge_jumps else 0
    else:
        report["loop_seam_sample_difference"] = 0
        report["loop_edge_window_ms"] = 1
        report["loop_edge_peak_head"] = 0
        report["loop_edge_peak_tail"] = 0
        report["loop_edge_max_jump"] = 0

    with wave.open(wav_path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(data.tobytes())
    report["wav"] = os.path.abspath(wav_path)

    if mp3_path:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            report["mp3"] = None
            report["mp3_error"] = "ffmpeg not found on PATH"
        else:
            command = [ffmpeg, "-y", "-loglevel", "error", "-i", wav_path,
                       "-codec:a", "libmp3lame", "-b:a", MP3_BITRATE, mp3_path]
            # stdin=DEVNULL on purpose. With no stdin given, CPython hands the child this process's own
            # STD_INPUT_HANDLE and duplicates it; if that handle is already invalid the duplication raises
            # OSError [WinError 6] The handle is invalid before the child ever starts. Measured on this
            # machine by setting STD_INPUT_HANDLE to an invalid value: inheriting it failed with exactly
            # that error, and DEVNULL ran the child. ffmpeg reads no stdin here, so DEVNULL costs nothing.
            done = subprocess.run(command, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL)
            if done.returncode == 0 and os.path.isfile(mp3_path):
                report["mp3"] = os.path.abspath(mp3_path)
                report["mp3_bitrate"] = MP3_BITRATE
            else:
                report["mp3"] = None
                report["mp3_error"] = (done.stderr or "").strip()[:400] or "ffmpeg failed"

    if loop_json_path:
        with open(loop_json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        report["loop_json"] = os.path.abspath(loop_json_path)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a chiptune MIDI to WAV and MP3.")
    parser.add_argument("midi", help="input MIDI file")
    parser.add_argument("wav", help="output WAV file")
    parser.add_argument("--loop-bars", type=int, default=None,
                        help="render exactly this many bars, trimmed or tailed to fit")
    parser.add_argument("--mp3", default=None,
                        help="MP3 path (default: the WAV path with a .mp3 extension)")
    parser.add_argument("--no-mp3", action="store_true", help="skip the MP3 export")
    parser.add_argument("--loop-json", default=None,
                        help="loop point JSON path (default: the WAV path with _loop.json)")
    parser.add_argument("--no-normalize", action="store_true",
                        help="keep the raw mix level instead of scaling the peak to the target")
    parser.add_argument("--force-v2", action="store_true",
                        help="use the version 2 voice path even for a four voice file")
    parser.add_argument("--hook-report", nargs="?", const="", default=None,
                        metavar="JSON",
                        help="score the melody's memorability (optional JSON path)")
    parser.add_argument("--humanize", action="store_true",
                        help="render the chip legal humanization of the MIDI "
                             "(written next to the WAV as <wav stem>_humanized.mid)")
    args = parser.parse_args(argv)

    wav_path = args.wav
    if args.no_mp3:
        mp3_path = None
    elif args.mp3:
        mp3_path = args.mp3
    else:
        mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
    if args.loop_json:
        loop_json_path = args.loop_json
    else:
        stem = os.path.splitext(wav_path)[0]
        loop_json_path = stem + "_loop.json"

    midi_path = args.midi

    if args.hook_report is not None:
        import hook_score
        hook = hook_score.score_file(midi_path)
        print(hook_score.format_report(hook))
        if args.hook_report:
            directory = os.path.dirname(os.path.abspath(args.hook_report))
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(args.hook_report, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(hook, handle, indent=2, sort_keys=True)
                handle.write("\n")

    if args.humanize:
        import humanize
        with open(midi_path, "rb") as handle:
            source_bytes = handle.read()
        human_bytes, human_report = humanize.humanize_bytes(source_bytes, name=midi_path)
        human_path = os.path.splitext(wav_path)[0] + "_humanized.mid"
        directory = os.path.dirname(os.path.abspath(human_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(human_path, "wb") as handle:
            handle.write(human_bytes)
        print(humanize.format_report(human_report))
        midi_path = human_path

    report = render_file(midi_path, wav_path, args.loop_bars, mp3_path, loop_json_path,
                         normalize=not args.no_normalize, force_v2=args.force_v2)

    print("render_chip: %s -> %s" % (os.path.basename(args.midi), wav_path))
    print("  duration %.3f s | peak %d (%.2f dBFS) | rms %.1f (%.2f dBFS)"
          % (report["duration_seconds"], report["peak"], report["peak_dbfs"] or 0.0,
             report["rms"], report["rms_dbfs"]))
    if report.get("loop_bars"):
        print("  loop %d bars | %d samples | seam sample difference %d | edge peak head %d tail %d"
              % (report["loop_bars"], report["loop_end_sample"],
                 report["loop_seam_sample_difference"],
                 report["loop_edge_peak_head"], report["loop_edge_peak_tail"]))
    print("  voices: %s" % ", ".join("%s=%s" % (k, v) for k, v in sorted(report["voice_map"].items())))
    print("  renderer: %s | limiter: %s | peak target %.1f dBFS"
          % (report.get("renderer", "v1"), report.get("limiter", "none"),
             report.get("peak_target_dbfs", 0.0)))
    if report.get("mp3"):
        print("  mp3: %s" % report["mp3"])
    elif report.get("mp3_error"):
        print("  mp3 FAILED: %s" % report["mp3_error"])
    print("  loop json: %s" % report.get("loop_json", "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
