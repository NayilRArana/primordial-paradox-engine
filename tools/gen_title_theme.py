"""Generate the Primordial Paradox title theme MIDI (cue title_theme, PP-01) from the manager's score.
A natural minor, 3/4, 84 bpm, 32 bars, 4 tracks. Deterministic, standard library only."""
import struct, sys, os
PPQ = 480
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "title_theme", "title_theme.mid")

def vlq(n):
    b = [n & 0x7F]; n >>= 7
    while n: b.append((n & 0x7F) | 0x80); n >>= 7
    return bytes(reversed(b))

# chord per bar (1 based): (root_midi, minor?)
A = {"Am": (45, 1), "F": (41, 0), "Dm": (38, 1), "E": (40, 0), "C": (48, 0), "G": (43, 0)}
secA = ["Am", "Am", "F", "F", "Dm", "Dm", "E", "E"]
secB = ["C", "C", "G", "G", "F", "F", "E", "E"]
chords = secA + secA + secB + secA[:7] + ["E"]
# melody (pitch, dur beats), bars with rests implied by running offset; None = rest
melA = [[(69,1),(72,1),(76,1)], [(77,1),(76,2)], [(72,1),(69,1),(65,1)], [(67,1),(69,2)],
        [(74,1),(77,1),(81,1)], [(79,1),(77,2)], [(76,1),(80,1),(83,1)], [(83,1),(80,1),(76,1)]]
melB = [[(72,1),(76,1),(79,1)], [(81,1),(79,2)], [(74,1),(79,1),(83,1)], [(81,1),(79,2)],
        [(72,1),(77,1),(81,1)], [(79,1),(77,2)], [(83,1),(80,1),(76,1)], [(80,2)]]
mel = []
mel += melA
mel += [[(p + (12 if i >= 4 else 0), d) for p, d in bar] for i, bar in enumerate(melA)]
mel += melB
mel += melA[:7] + [[(76, 3)]]
SC = [9, 11, 0, 2, 4, 5, 7]
def third_below(p, bar):
    if chords[bar] == "E":
        return {83: 80, 80: 76, 76: 72, 95: 92, 92: 88}.get(p, p - 4)
    pc = p % 12; octv = p - pc
    if pc in SC:
        i = SC.index(pc); j = i - 2
        q = SC[j % 7] + octv + (-12 if j < 0 and SC[j % 7] > pc else 0)
        while q >= p: q -= 12
        return q
    return p - 4

def track(name, events):
    ev = sorted(events, key=lambda e: (e[0], 0 if e[1][0] == 0x80 else 1))
    data = vlq(0) + b"\xFF\x03" + bytes([len(name)]) + name.encode()
    last = 0
    for t, msg in ev:
        data += vlq(t - last) + bytes(msg); last = t
    data += vlq(0) + b"\xFF\x2F\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + data

def note(ev, bar, off, dur, pitch, vel, ch):
    t0 = int((bar * 3 + off) * PPQ); t1 = int((bar * 3 + off + dur) * PPQ) - 8
    ev.append((t0, (0x90 | ch, pitch, vel))); ev.append((t1, (0x80 | ch, pitch, 0)))

p1, p2, tri, noi = [], [], [], []
for ch, ev in ((0, p1), (1, p2), (2, tri), (3, noi)):
    ev.append((0, (0xB0 | ch, 11, 127)))
for bar in range(32):
    root, minor = A[chords[bar]]
    note(tri, bar, 0, 1, root, 100, 2); note(tri, bar, 2, 1, root + 7, 100, 2)
    off = 0
    for p, d in mel[bar]:
        note(p1, bar, off, d, p, 92, 0); off += d
    if 8 <= bar < 16:
        off = 0
        for p, d in mel[bar]:
            note(p2, bar, off, d, third_below(p, bar), 72, 1); off += d
    else:
        note(p2, bar, 1, 1, root + 12 + (3 if minor else 4), 72, 1)
        note(p2, bar, 2, 1, root + 12 + 7, 72, 1)
    if 8 <= bar < 24:
        note(noi, bar, 1, 0.25, 60, 30, 3); note(noi, bar, 2, 0.25, 60, 30, 3)
meta = vlq(0) + b"\xFF\x51\x03" + (60000000 // 84).to_bytes(3, "big") + vlq(0) + b"\xFF\x58\x04\x03\x02\x18\x08" + vlq(0) + b"\xFF\x03\x04meta" + vlq(0) + b"\xFF\x2F\x00"
mt = b"MTrk" + struct.pack(">I", len(meta)) + meta
body = mt + track("pulse 1", p1) + track("pulse 2", p2) + track("triangle", tri) + track("noise", noi)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, "wb").write(b"MThd" + struct.pack(">IHHH", 6, 1, 5, PPQ) + body)
print("wrote", OUT, "notes p1", len(p1) // 2)
