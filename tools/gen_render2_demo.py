"""gen_render2_demo.py: build the four bar version 2 demo MIDI.

The demo exists to exercise every version 2 voice of the chip renderer in one
file: the two VRC6 pulses with per note duty, the VRC6 saw, the two 2A03
pulses, the triangle, the noise, the DPCM drums, an echo track, vibrato with an
onset delay, and per note level.

The output is a Standard MIDI File at assets/audio/render2_demo/render2_demo.mid.
The renderer turns it into output/render2_demo.wav.

Usage:
    gen_render2_demo.py [path.mid]
"""

from __future__ import annotations

import os
import struct
import sys

DIV = 480
BEAT = DIV
BAR = 4 * BEAT
BPM = 100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "assets", "audio", "render2_demo", "render2_demo.mid")

# MIDI note numbers, spelled out so no arithmetic can go out of range.
A4, C5, D5, E5, F5, G5, A5 = 69, 72, 74, 76, 77, 79, 81
C6, D6, E6 = 84, 86, 88
A3, C4, D4, E4, F4, G4 = 57, 60, 62, 64, 65, 67
A2, C3, D3, E3, F3 = 45, 48, 50, 52, 53


def _varlen(value: int) -> bytes:
    if value < 0:
        raise ValueError("a MIDI delta time cannot be negative")
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def _track(name: str, events: list[tuple[int, int, bytes]]) -> bytes:
    """One MIDI track from (tick, order, payload) events."""
    body = bytearray()
    body += _varlen(0) + b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1")
    last = 0
    for tick, _order, payload in sorted(events, key=lambda item: (item[0], item[1])):
        body += _varlen(tick - last) + payload
        last = tick
    body += _varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def note_events(notes, duty=None, level=None, vibrato=None, delay=None):
    """Turn (start, duration, pitch, velocity) notes into track events.

    duty, level, vibrato and delay are lists of (tick, value) control changes
    written just before the note they belong to.
    """
    events = []
    for start, dur, pitch, vel in notes:
        for tick, value in (duty or []):
            if start - 1 <= tick <= start:
                events.append((tick, 1, bytes([0xB0, 12, value])))
        for tick, value in (level or []):
            if start - 1 <= tick <= start:
                events.append((tick, 1, bytes([0xB0, 11, value])))
        for tick, value in (vibrato or []):
            if start - 1 <= tick <= start:
                events.append((tick, 1, bytes([0xB0, 1, value])))
        for tick, value in (delay or []):
            if start - 1 <= tick <= start:
                events.append((tick, 1, bytes([0xB0, 20, value])))
        events.append((start, 2, bytes([0x90, pitch, vel])))
        events.append((start + dur, 0, bytes([0x80, pitch, 0])))
    return events


def build() -> bytes:
    # A minor pentatonic-ish phrase, four bars.
    melody = [
        (0 * BAR, BEAT, A5, 100), (1 * BAR, BEAT, C6, 96),
        (2 * BAR, BEAT, E6, 100), (3 * BAR, BEAT, D6, 96),
        (1 * BAR + BEAT, BEAT, A5, 88), (1 * BAR + 2 * BEAT, BEAT, G5, 92),
        (2 * BAR + BEAT, BEAT, F5, 88), (2 * BAR + 2 * BEAT, BEAT, E5, 92),
        (3 * BAR + BEAT, BEAT, D5, 88), (3 * BAR + 2 * BEAT, BEAT, C5, 96),
        (3 * BAR + 3 * BEAT, BEAT, A4, 100),
    ]
    harmony = [
        (0 * BAR + 2 * BEAT, 2 * BEAT, E5, 70),
        (1 * BAR + 2 * BEAT, 2 * BEAT, C5, 68),
        (2 * BAR + 2 * BEAT, 2 * BEAT, D5, 68),
        (3 * BAR + 2 * BEAT, 2 * BEAT, E5, 70),
    ]
    bass = [
        (0 * BAR, 2 * BEAT, A3, 110), (0 * BAR + 2 * BEAT, 2 * BEAT, A3, 100),
        (1 * BAR, 2 * BEAT, F4, 110), (1 * BAR + 2 * BEAT, 2 * BEAT, E4, 100),
        (2 * BAR, 2 * BEAT, D4, 110), (2 * BAR + 2 * BEAT, 2 * BEAT, D4, 100),
        (3 * BAR, 2 * BEAT, E4, 110), (3 * BAR + 2 * BEAT, 2 * BEAT, A3, 100),
    ]
    counter = [
        (0 * BAR + BEAT, BEAT, E5, 84), (0 * BAR + 3 * BEAT, BEAT, A4, 80),
        (1 * BAR + BEAT, BEAT, G4, 84), (1 * BAR + 3 * BEAT, BEAT, E4, 80),
        (2 * BAR + BEAT, BEAT, F4, 84), (2 * BAR + 3 * BEAT, BEAT, D4, 80),
        (3 * BAR + BEAT, BEAT, E4, 84), (3 * BAR + 3 * BEAT, BEAT, C4, 80),
    ]
    stabs = [
        (0 * BAR + 3 * BEAT, BEAT, A4, 92),
        (1 * BAR + 3 * BEAT, BEAT, F4, 92),
        (2 * BAR + 3 * BEAT, BEAT, D4, 92),
        (3 * BAR + 3 * BEAT, BEAT, E4, 92),
    ]
    saw_bass = [
        (0 * BAR, BEAT, A2, 96), (0 * BAR + 2 * BEAT, BEAT, E3, 88),
        (1 * BAR, BEAT, F3, 96), (1 * BAR + 2 * BEAT, BEAT, C3, 88),
        (2 * BAR, BEAT, D3, 96), (2 * BAR + 2 * BEAT, BEAT, A2, 88),
        (3 * BAR, BEAT, E3, 96), (3 * BAR + 2 * BEAT, BEAT, A2, 88),
    ]
    hats = [
        (bar * BAR + beat * BEAT, BEAT // 2, 42, 64)
        for bar in range(4) for beat in range(4)
    ]
    drums = []
    for bar in range(4):
        drums.append((bar * BAR, BEAT, 36, 110))
        drums.append((bar * BAR + BEAT, BEAT, 38, 96))
        drums.append((bar * BAR + 2 * BEAT, BEAT, 36, 100))
        drums.append((bar * BAR + 3 * BEAT, BEAT, 38, 100))
    echo = [
        (2 * BAR, BEAT, A4, 64), (2 * BAR + 2 * BEAT, BEAT, E4, 60),
        (3 * BAR, BEAT, C5, 64), (3 * BAR + 2 * BEAT, BEAT, G4, 60),
    ]

    # Per note duty: the VRC6 pulses walk through the eight steps.
    vrc6_a_duty = []
    step = 0
    for start, _dur, _pitch, _vel in counter:
        vrc6_a_duty.append((start, step % 8))
        step += 1
    vrc6_b_duty = [(start, 7) for start, _d, _p, _v in stabs]

    tracks = [
        ("pulse 1", note_events(melody, duty=[(s, 2) for s, _d, _p, _v in melody],
                                level=[(0, 15)])),
        ("pulse 2", note_events(harmony, duty=[(s, 1) for s, _d, _p, _v in harmony],
                                level=[(0, 12)])),
        ("triangle", note_events(bass, level=[(0, 15)])),
        ("noise", note_events(hats, level=[(0, 9)])),
        ("vrc6 pulse a", note_events(counter, duty=vrc6_a_duty, level=[(0, 14)])),
        ("vrc6 pulse b", note_events(stabs, duty=vrc6_b_duty, level=[(0, 14)])),
        # The saw voice carries the vibrato, with an onset delay in eighths.
        ("vrc6 saw", note_events(saw_bass, level=[(0, 13)],
                                 vibrato=[(s, 30) for s, _d, _p, _v in saw_bass],
                                 delay=[(s, 2) for s, _d, _p, _v in saw_bass])),
        ("dpcm", note_events(drums, level=[(0, 15)])),
        ("echo", note_events(echo, duty=[(s, 2) for s, _d, _p, _v in echo],
                             level=[(0, 8)])),
    ]

    tempo_body = bytearray()
    tempo_body += _varlen(0) + b"\xff\x58\x04\x04\x02\x18\x08"
    tempo_body += _varlen(0) + b"\xff\x51\x03" + struct.pack(">I", 500000 * 120 // BPM)[1:]
    tempo_body += _varlen(0) + b"\xff\x2f\x00"
    tempo_track = b"MTrk" + struct.pack(">I", len(tempo_body)) + bytes(tempo_body)

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks) + 1, DIV)
    return header + tempo_track + b"".join(_track(name, events) for name, events in tracks)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = argv[0] if argv else DEFAULT_OUT
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as handle:
        handle.write(build())
    print("gen_render2_demo: wrote %s" % os.path.abspath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
