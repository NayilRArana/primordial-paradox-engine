"""render_chip.py: render a 4 track chiptune MIDI to WAV and MP3, loop safe.

A small, self contained NES 2A03 style renderer. It reads a Standard MIDI File and
synthesises four voices directly, with no emulator, no window and no external
dependency beyond numpy:

  pulse 1 : 50 percent duty square (25 percent when the MIDI says so)
  pulse 2 : 25 percent duty square (50 percent when the MIDI says so)
  triangle : 16 step NES triangle, fixed level
  noise    : 15 bit LFSR, period taken from the note number

Voice assignment: by track name first ("p1", "pulse 2", "triangle", "noise", ...),
then by the order in which the tracks start playing. Control change 11 sets the
level of a pulse or a noise voice and control change 12 sets its duty (or the
noise loop bit), which is the convention the Musikage dataset uses.

Each note gets a linear decay envelope from its own velocity, so a note fades
out over its own length instead of stopping dead.

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


# ------------------------------------------------------------------- the render


def render_file(midi_path: str, wav_path: str, loop_bars: int | None, mp3_path: str | None,
                loop_json_path: str | None, normalize: bool = True) -> dict:
    midi = parse_midi(midi_path)
    to_seconds = make_clock(midi["tempo"], midi["division"])
    voices = assign_voices(midi["tracks"])

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
        mix += render_voice(voice, track, to_seconds, total_samples)

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

    if normalize and len(mix) and np.abs(mix).max() > 0:
        peak_before = float(np.abs(mix).max())
        mix = mix / peak_before * 0.85
        report["peak_before_normalize"] = round(peak_before, 6)
    else:
        report["peak_before_normalize"] = round(float(np.abs(mix).max()), 6) if len(mix) else 0.0

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
    parser = argparse.ArgumentParser(description="Render a 4 track chiptune MIDI to WAV and MP3.")
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
                        help="keep the raw mix level instead of scaling the peak to 0.85")
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

    report = render_file(args.midi, wav_path, args.loop_bars, mp3_path, loop_json_path,
                         normalize=not args.no_normalize)

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
    if report.get("mp3"):
        print("  mp3: %s" % report["mp3"])
    elif report.get("mp3_error"):
        print("  mp3 FAILED: %s" % report["mp3_error"])
    print("  loop json: %s" % report.get("loop_json", "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
