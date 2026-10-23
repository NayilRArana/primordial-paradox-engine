"""humanize.py: chip legal humanization for a MIDI written by tools/arrange.py.

arrange.py writes every note exactly on the grid, at one fixed length per
recipe and at a flat level per section. That is correct and it reads as a
sequencer. This tool plays the same notes with the small imperfections a
player or an NES sound driver puts in, without leaving the chip's own rules:

  articulation   every note is shortened to 85 to 100 percent of its written
                 length, per role, and its note-off snaps to the 1/60 s frame
                 grid the NES runs on. The grid comes first, because a chip
                 driver can only end a note on a frame: among the frames the
                 note may end on (at least one tick in, never past its written
                 end) the tool takes the one nearest the role's band, and never
                 earlier than 85 percent of the written length unless the note
                 holds no frame that late. The noise hats the arranger writes
                 at 60 ticks are the case that decides it: at 16 ticks a frame
                 their frames are 48 and 64, so 48 is the off and 80 percent is
                 as close as that hat can come to the floor. A note an ornament
                 created, split or cut short is exempt, because the ornament
                 rewrote it and its frames are the ornament's
  velocity       plus or minus 6, clamped, from a fixed seed
  envelopes      control change 11 shapes per role: melody and counter melody
                 decay inside the note, the arpeggio is plucked, the bass and
                 the pad stay flat
  vibrato        control change 1 (depth) and 20 (delay) vary per two bar
                 phrase on the melody, instead of one fixed depth
  breaths        the melody note that runs into a phrase end is cut short, so
                 the next phrase starts after a short rest, and it keeps the
                 85 percent floor
  grace, mordent on the third return of the motif, the first melody note gets
                 a grace note and a mordent, the way a player ornaments a
                 repeat
  fills          the last beat before a section change gets a noise fill (and
                 a pulse pickup when that voice is free)

Everything is deterministic: the same input and the same seed give the same
bytes. Two runs of this tool on the same input are byte identical.

The track names, the format, the division and the meta track are untouched,
so the version 2 and version 3 renderer paths both keep working.

Usage:
    humanize.py IN.mid OUT.mid [--seed N] [--report report.json]
    humanize.py IN.mid OUT.mid --dry-run          (report only, writes nothing)

The reader lives in hook_score.py, so there is one SMF parser in the project
and this tool is the only writer of the humanized file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hook_score                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SEED = 20261021

# Which role a voice plays, by the track name arrange.py writes.
ROLES = {
    "vrc6 pulse a": "melody",
    "vrc6 pulse b": "counter",
    "vrc6 saw": "pad",
    "pulse 1": "arpeggio",
    "pulse 2": "echo",
    "triangle": "bass",
    "noise": "drums",
    "dpcm": "kick",
}

# Articulation as a fraction of the written note length. The card asks for 85
# to 100 percent; each role sits in its own part of that window, because a
# plucked arpeggio and a held pad do not shorten the same way.
ARTICULATION = {
    "melody": (0.86, 1.00),
    "counter": (0.88, 0.98),
    "pad": (0.96, 1.00),
    "arpeggio": (0.85, 0.95),
    "echo": (0.85, 0.96),
    "bass": (0.90, 1.00),
    "drums": (0.85, 0.98),
    "kick": (0.88, 1.00),
}

# The floor the tool promises on every note, as a fraction of the length the
# arranger wrote. The bands in ARTICULATION sit at or above it, but the bands
# alone are not enough: the off is snapped to the 1/60 s frame grid after the
# band is applied, and that rounding can put a short note under 85 percent on
# its own. So the floor is applied to the rounded off, wherever a frame that
# late exists inside the note.
ARTICULATION_FLOOR = 0.85

# Control change 11 points inside a note, as (fraction of the note, level
# multiplier of the level in force when the note started). An empty tuple is a
# flat voice: the bass and the pad hold their level, which is what the waltz
# bass and the pad want.
ENVELOPES = {
    "melody": ((0.55, 0.90), (0.85, 0.74)),
    "counter": ((0.60, 0.92),),
    "echo": ((0.60, 0.86),),
    "arpeggio": ((0.35, 0.55), (0.70, 0.26)),
    "pad": (),
    "bass": (),
    "drums": (),
    "kick": (),
}

# The melody's vibrato, in cents, and its delay in eighth notes. Three
# variants chosen by the phrase index, so no two neighbouring phrases breathe
# exactly alike.
VIBRATO_CENTS = (12.0, 15.0, 18.0)
VIBRATO_DELAY_EIGHTHS = (1, 2)
VIBRATO_MIN_EIGHTHS = 3

PHRASE_BARS = 2
BREATH_FRAMES = 2
LOOP_PERIODS = (8, 16, 32)


# ------------------------------------------------------------------- SMF write

def _varlen(value):
    if value < 0:
        raise ValueError("negative delta time")
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append(0x80 | (value & 0x7F))
        value >>= 7
    chunks.reverse()
    return bytes(chunks)


def write_smf(song, path=None):
    """Write a song dict back as a Standard MIDI File, format 1.

    Events at the same tick are written meta first, then note offs, then
    control changes, then note ons, the same order arrange.py uses, so a
    control change always applies to the note that starts on the same tick.
    """
    tracks = song["tracks"]
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), song["division"])
    parts = []
    for index, track in enumerate(tracks):
        events = []
        name = track.get("name", "")
        events.append((0, 0, b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1")))
        if index == 0:
            tempo = int(song.get("tempo_us", 500000))
            events.append((0, 0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")))
            numerator, denominator = song.get("time_sig", (4, 4))
            power = int(round(math.log(denominator, 2))) if denominator else 2
            events.append((0, 0, b"\xff\x58\x04" + bytes((int(numerator), power, 24, 8))))
        for start, end, pitch, velocity in sorted(track["notes"]):
            start = max(0, int(round(start)))
            end = max(start + 1, int(round(end)))
            events.append((start, 3, bytes((0x90, int(pitch) & 0x7F,
                                            max(1, min(127, int(velocity)))))))
            events.append((end, 1, bytes((0x80, int(pitch) & 0x7F, 0))))
        for controller in sorted(track["cc"]):
            for tick, value in sorted(track["cc"][controller]):
                events.append((max(0, int(round(tick))), 2,
                               bytes((0xB0, int(controller) & 0x7F,
                                      max(0, min(127, int(value)))))))
        events.sort(key=lambda item: (item[0], item[1], item[2]))
        body = bytearray()
        last = 0
        for tick, _order, payload in events:
            body += _varlen(tick - last) + payload
            last = tick
        body += _varlen(0) + b"\xff\x2f\x00"
        parts.append(b"MTrk" + struct.pack(">I", len(body)) + bytes(body))
    data = header + b"".join(parts)
    if path:
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
    return data


# ------------------------------------------------------------------ the timing

def ticks_per_frame(division, tempo_us):
    """Ticks in one 1/60 s NES frame at a fixed tempo."""
    bpm = 60_000_000.0 / tempo_us
    return division * bpm / 3600.0


def snap_to_frame(tick, unit):
    """Round a tick to the nearest frame boundary."""
    if unit <= 0:
        return int(round(tick))
    return int(round(round(tick / unit) * unit))


def next_frame_tick(tick, unit):
    """The first frame boundary at or after a tick, never the frame before it."""
    if unit <= 0:
        return int(math.ceil(tick))
    return int(round(math.ceil(tick / unit - 1e-9) * unit))


def frame_off(start, end, target, floor_ticks, unit):
    """The note-off: the frame boundary inside the note nearest the target.

    The NES ends a note on a 1/60 s frame, so the off is always a frame
    boundary, never the written end when that end falls between frames. The
    note may use any frame from one tick in to its written end; among those the
    one nearest the role's target is the off, and when the target lands under
    the floor the first frame at or above it is taken instead, if the note
    holds one. A note shorter than a frame, or one whose only reachable frames
    are all under the floor, keeps the last frame it can play.
    """
    if unit <= 0:
        return max(start + 1, min(end, int(round(target))))
    # A frame counts when its tick value (the tick the file will carry, so the
    # rounded value, not the exact multiple) lies inside the note. An end half a
    # tick short of a frame still makes that frame usable, and the voice needs
    # it: a breath cut lands between frames.
    last = int(math.floor((end + 0.5) / unit))           # latest frame in the note
    first = int(math.ceil((start + 0.5) / unit - 1e-9))  # earliest frame in the note
    if last < first:
        return end                                     # shorter than one frame
    chosen = min(max(int(round(target / unit)), first), last)
    if floor_ticks:
        above = int(math.ceil((start + floor_ticks) / unit - 1e-9))
        if above <= last and chosen < above:
            chosen = above
    return int(round(chosen * unit))


def _level_at(events, tick, default=15):
    """The value of a stepwise control change list at a tick."""
    value = default
    for at, level in events:
        if at <= tick:
            value = level
        else:
            break
    return value


def _busy(notes, start, end):
    """True when any note sounds anywhere in [start, end)."""
    return any(n[0] < end and start < n[1] for n in notes)


# ---------------------------------------------------------------- the sections

def loop_period(song, melody):
    """The bar period the melody tiles at, or 8 when it does not tile.

    The motif loops of the card are 8, 16 or 32 bars, so those are the only
    periods tested. A period passes when the melody bars repeat at least 75
    percent across the file.
    """
    if melody is None or melody.bars < 8:
        return 8
    signatures = [melody.bar_signature(bar) for bar in range(melody.bars)]
    for period in LOOP_PERIODS:
        if melody.bars < period * 2:
            continue
        pairs = [(i, i + period) for i in range(melody.bars - period)]
        if not pairs:
            continue
        same = sum(1 for i, j in pairs if signatures[i] == signatures[j])
        if same / float(len(pairs)) >= 0.75:
            return period
    return 8


def section_bars(bars, period):
    """The bars that start a section: every period, plus the loop seam."""
    out = [bar for bar in range(period, bars, period)]
    if bars not in out:
        out.append(bars)
    return out


# ----------------------------------------------------------- the humanization

def _role(track):
    return ROLES.get(track["name"].strip().lower(), "other")


def humanize_song(song, seed=DEFAULT_SEED, onset_frames=0.0):
    """Return a humanized copy of the song dict, plus a report dict."""
    rng = random.Random(seed)
    division = song["division"]
    tempo_us = song.get("tempo_us", 500000)
    unit = ticks_per_frame(division, tempo_us)
    beats_per_bar = song.get("time_sig", (4, 4))[0]
    bar_ticks = beats_per_bar * division
    breath = max(1, int(round(BREATH_FRAMES * unit)))
    phrase_ticks = PHRASE_BARS * bar_ticks

    tracks = [{"name": t["name"],
               "notes": [tuple(note) for note in t["notes"]],
               "cc": {controller: sorted(events)
                      for controller, events in t["cc"].items()}}
              for t in song["tracks"]]

    report = {
        "seed": seed,
        "division": division,
        "tempo_us": tempo_us,
        "bpm": round(60_000_000.0 / tempo_us, 3),
        "ticks_per_frame": round(unit, 4),
        "notes": sum(len(t["notes"]) for t in tracks),
        "notes_by_track": {},
        "notes_changed": 0,
        "floor_misses": 0,
        "fills": 0,
        "grace_notes": 0,
        "mordents": 0,
        "ornament_notes": [],
        "breaths": 0,
        "vibrato_notes": 0,
        "envelope_points": 0,
        "motif": None,
        "loop_period_bars": 0,
        "section_bars": [],
    }

    # ---- 1. the melody, its ornaments and its phrase breaths, on the notes
    # as the arranger wrote them. Order matters: a breath cuts a note that
    # runs into a phrase end, and the ornament rewrites the first note of the
    # third return, so both have to happen before the lengths are humanized.
    melody_track = next((t for t in tracks
                         if _role(t) == "melody" and t["notes"]), None)
    if melody_track is None:
        with_notes = [t for t in tracks if t["notes"]]
        if with_notes:
            melody_track = max(with_notes,
                               key=lambda t: sum(n[2] for n in t["notes"]) / len(t["notes"]))
    melody = None
    original_lengths = {}
    vibrato_intent = set()
    if melody_track is not None:
        melody = _melody_view(melody_track, division, beats_per_bar)
        for start, end, pitch, _velocity in melody_track["notes"]:
            original_lengths[(start, pitch)] = end - start
        for tick, value in melody_track["cc"].get(1, []):
            if value > 0:
                vibrato_intent.add(tick)

        # The breath: the melody note that runs into a two bar phrase end is
        # cut `breath` ticks short, so the next phrase starts after a rest.
        notes = sorted(melody_track["notes"])
        last_end = max([note[1] for note in notes], default=0)
        for boundary in range(phrase_ticks, (last_end // phrase_ticks + 1) * phrase_ticks,
                              phrase_ticks):
            candidates = [note for note in notes
                          if boundary - breath < note[1] <= boundary]
            if not candidates:
                continue
            last = max(candidates, key=lambda note: note[1])
            new_end = max(last[0] + 1, boundary - breath)
            # The breath keeps the floor: the cut stops at the first frame at
            # or above 85 percent of the written length, so the articulation
            # pass can still find a frame inside its own window afterwards. A
            # note too short to give a breath and keep the floor is left alone.
            written = original_lengths.get((last[0], last[2]))
            if written:
                new_end = max(new_end, min(last[1], next_frame_tick(
                    last[0] + ARTICULATION_FLOOR * written, unit)))
            if new_end >= last[1]:
                continue
            notes[notes.index(last)] = (last[0], new_end, last[2], last[3])
            report["breaths"] += 1
        melody_track["notes"] = notes

        # The ornament on the third return of the motif.
        config, _source = hook_score.load_grammar()
        motif = hook_score.find_motif(melody, config)
        report["motif"] = None if motif is None else {
            "bars": motif["bars"], "start_bar": motif["start_bar"] + 1,
            "returns": motif["returns"],
            "third_return_bar": (motif["occurrences"][2] + 1
                                 if len(motif["occurrences"]) >= 3 else None)}
        if motif and len(motif["occurrences"]) >= 3:
            added = _ornament(melody_track, motif["occurrences"][2],
                              bar_ticks, division)
            report["grace_notes"] += added["grace"]
            report["mordents"] += added["mordent"]
            report["ornament_notes"] = added["keys"]
            melody_track["notes"] = sorted(melody_track["notes"])

    # ---- 2. articulation and velocity, per track in a fixed order
    for track in tracks:
        role = _role(track)
        low, high = ARTICULATION.get(role, (0.85, 1.0))
        is_melody = track is melody_track
        changed = 0
        under = 0
        new_notes = []
        for start, end, pitch, velocity in sorted(track["notes"]):
            written = max(1, end - start)
            # The length the arranger wrote, before the breath or an ornament
            # touched the note. None means an ornament created this note, and
            # an ornament is allowed to rewrite what it creates.
            source = original_lengths.get((start, pitch)) if is_melody else written
            floor_ticks = ARTICULATION_FLOOR * source if source else 0.0
            factor = low + (high - low) * rng.random()
            off = frame_off(start, end, start + written * factor, floor_ticks, unit)
            # A note the grid could not hold at the floor: every frame it may
            # end on is under 85 percent of the written length.
            if floor_ticks and off - start < floor_ticks:
                under += 1
            velocity = max(1, min(127, velocity + rng.randint(-6, 6)))
            if off - start != written:
                changed += 1
            new_notes.append((start, off, pitch, velocity))
        track["notes"] = new_notes
        report["notes_changed"] += changed
        report["floor_misses"] += under
        report["notes_by_track"][track["name"]] = {
            "role": role, "notes": len(new_notes), "changed": changed,
            "floor_misses": under}

    # ---- 2b. onset micro-timing. The chip clock is a 1/60 s frame, so a played
    # onset moves by a fraction of a frame, never by a smooth random amount: the
    # note lands one frame early or late, or stays put. Drum roles already carry
    # their own timing feel from the drum pass, so they are left alone here.
    report["onset_shifts"] = 0
    report["onset_frames"] = round(onset_frames, 4)
    if onset_frames > 0:
        probability = min(0.75, onset_frames)
        magnitude = int(round(unit * min(1.5, max(0.5, onset_frames))))
        for track in tracks:
            if _role(track) in ("drums", "kick"):
                continue
            moved = []
            for start, end, pitch, velocity in sorted(track["notes"]):
                target = start
                if magnitude and rng.random() < probability:
                    step = magnitude if rng.random() < 0.5 else -magnitude
                    target = max(0, min(end - 2, start + step))
                    if target != start:
                        report["onset_shifts"] += 1
                moved.append((target, end, pitch, velocity))
            track["notes"] = sorted(moved)

    # ---- 3. control change 11 envelopes per role
    for track in tracks:
        role = _role(track)
        shape = ENVELOPES.get(role, ())
        if not shape:
            continue
        original = list(track["cc"].get(11, []))
        if not original and role not in ("melody", "counter", "echo", "arpeggio"):
            continue
        bar_levels = {tick for tick, _value in original}
        levels = dict(original)
        added = 0
        for start, end, _pitch, _velocity in track["notes"]:
            base = _level_at(original, start, 15)
            if start not in levels:
                levels[start] = base
                added += 1
            length = end - start
            for fraction, multiplier in shape:
                tick = snap_to_frame(start + length * fraction, unit)
                if not (start < tick < end):
                    continue
                if tick in bar_levels:
                    continue
                levels[tick] = max(0, min(15, int(round(base * multiplier))))
                added += 1
        track["cc"][11] = sorted(levels.items())
        report["envelope_points"] += added

    # ---- 4. vibrato per phrase on the melody. The note keeps the vibrato
    # the arranger gave it (its original length, or a depth already written
    # on that tick); what changes is the depth and the delay, which now vary
    # phrase by phrase instead of staying at one fixed value.
    if melody_track is not None:
        depth_events = []
        delay_events = []
        for start, end, pitch, _velocity in melody_track["notes"]:
            phrase = int(start // phrase_ticks)
            cents = VIBRATO_CENTS[(phrase * 7) % len(VIBRATO_CENTS)]
            delay = VIBRATO_DELAY_EIGHTHS[(phrase * 5) % len(VIBRATO_DELAY_EIGHTHS)]
            written = original_lengths.get((start, pitch), end - start)
            held = (written >= VIBRATO_MIN_EIGHTHS * (division // 2)
                    or start in vibrato_intent)
            depth = int(round(cents / 200.0 * 127)) if held else 0
            depth_events.append((start, max(0, min(127, depth))))
            delay_events.append((start, delay if held else 0))
            if held:
                report["vibrato_notes"] += 1
        melody_track["cc"][1] = depth_events
        melody_track["cc"][20] = delay_events

    # ---- 5. last beat fills before each section change
    period = loop_period(song, melody)
    report["loop_period_bars"] = period
    boundaries = section_bars(max(1, (max([n[1] for t in tracks for n in t["notes"]],
                                         default=bar_ticks) + bar_ticks - 1)
                                  // bar_ticks),
                              period)
    report["section_bars"] = boundaries
    noise = next((t for t in tracks if _role(t) == "drums"), None)
    echo = next((t for t in tracks if _role(t) == "echo"), None)
    for boundary in boundaries:
        bar_start = (boundary - 1) * bar_ticks
        if bar_start < 0:
            continue
        beat = division
        if noise is not None:
            pitches = [n[2] for n in noise["notes"]]
            hit = pitches[len(pitches) // 2] if pitches else 6
            step = max(1, division // 8)
            for index in range(3):
                tick = bar_start + bar_ticks - beat + index * (beat // 4)
                if _busy(noise["notes"], tick, tick + step):
                    continue
                velocity = 26 + index * 6
                noise["notes"].append((tick, tick + step, hit, velocity))
                report["fills"] += 1
        if echo is not None and not _busy(echo["notes"], bar_start + bar_ticks - beat,
                                         bar_start + bar_ticks):
            pitches = [n[2] for n in echo["notes"]]
            top = pitches[-1] if pitches else 60
            step = max(1, division // 4)
            for index, offset in enumerate((0, step)):
                tick = bar_start + bar_ticks - beat + offset
                echo["notes"].append((tick, tick + step, max(0, top - 2 * (index + 1)), 30))
                report["fills"] += 1
        if noise is not None:
            noise["notes"] = sorted(noise["notes"])
        if echo is not None:
            echo["notes"] = sorted(echo["notes"])

    report["notes_out"] = sum(len(t["notes"]) for t in tracks)
    song_out = {"format": song.get("format", 1), "division": division,
                "tempo_us": tempo_us, "time_sig": song.get("time_sig", (4, 4)),
                "tracks": tracks}
    return song_out, report


def _melody_view(track, division, beats_per_bar):
    """The melody as a hook_score grid, so the motif can be looked up."""
    notes = [(start, end, pitch, velocity) for start, end, pitch, velocity in track["notes"]]
    return hook_score.Melody(notes, division, beats_per_bar, 4, name=track["name"])


def _ornament(track, bar_index, bar_ticks, division):
    """A grace note and a mordent on the first melody note of a bar.

    Returns the counts and the keys the ornament rewrote, split, created or cut
    short, so the articulation pass can leave those notes the frames the
    ornament gave them.
    """
    out = {"grace": 0, "mordent": 0, "keys": []}
    notes = sorted(track["notes"])
    bar_start = bar_index * bar_ticks
    in_bar = [n for n in notes if bar_start <= n[0] < bar_start + bar_ticks]
    if not in_bar:
        return out
    first = in_bar[0]
    index = notes.index(first)
    start, end, pitch, velocity = first
    step = max(1, division // 8)

    # The grace note: a written appoggiatura. It is short, it is one step
    # below the main note, and it ends exactly where the main note starts.
    grace_pitch = pitch - 2 if pitch - 2 >= 0 else pitch - 1
    if index > 0:
        previous = notes[index - 1][2]
        if 0 < start - previous <= 2:
            grace_pitch = previous
    grace_start = max(0, start - step)
    # A grace note has to have the tick to itself: whatever note is still
    # sounding there (normally the note before it) is released at the grace
    # note's start, which is what a player does with a written appoggiatura.
    others = [note for note in notes if note is not first]
    for note in list(others):
        if note[0] < grace_start < note[1]:
            track["notes"].remove(note)
            track["notes"].append((note[0], grace_start, note[2], note[3]))
            others[others.index(note)] = (note[0], grace_start, note[2], note[3])
            out["keys"].append([note[0], note[2]])
    if not _busy(others, grace_start, start):
        track["notes"].append((grace_start, start, grace_pitch, max(1, velocity - 3)))
        out["keys"].append([grace_start, grace_pitch])
        out["grace"] = 1

    # The mordent: the first note is played, flicked one step up, then played
    # again. The note is rewritten as three notes on one voice, so no two
    # notes of this track overlap.
    if end - start >= 3 * step:
        upper = pitch + 1 if pitch + 1 <= 127 else pitch
        rest_start = start + 2 * step
        track["notes"].remove(first)
        track["notes"].append((start, start + step, pitch, velocity))
        track["notes"].append((start + step, rest_start, upper, max(1, velocity - 2)))
        track["notes"].append((rest_start, end, pitch, max(1, velocity - 1)))
        out["keys"].append([start, pitch])
        out["keys"].append([start + step, upper])
        out["keys"].append([rest_start, pitch])
        out["mordent"] = 1
    return out


# ------------------------------------------------------------------ file level

def humanize_bytes(data, seed=DEFAULT_SEED, name="<bytes>", onset_frames=0.0):
    """Humanize a whole SMF given as bytes. Returns (bytes, report)."""
    song = hook_score.parse_smf(data, name=name)
    out, report = humanize_song(song, seed=seed, onset_frames=onset_frames)
    result = write_smf(out)
    report["sha256_in"] = hashlib.sha256(data).hexdigest()
    report["sha256_out"] = hashlib.sha256(result).hexdigest()
    report["bytes_in"] = len(data)
    report["bytes_out"] = len(result)
    report["notes_in"] = report["notes"]
    report["changed_fraction"] = (round(report["notes_changed"] / float(report["notes"]), 4)
                                  if report["notes"] else 0.0)
    return result, report


def humanize_file(source, target=None, seed=DEFAULT_SEED, write=True,
                  onset_frames=0.0):
    """Humanize a file. Returns the report."""
    with open(source, "rb") as handle:
        data = handle.read()
    result, report = humanize_bytes(data, seed=seed, name=source,
                                    onset_frames=onset_frames)
    report["midi_in"] = os.path.abspath(source)
    if write and target:
        directory = os.path.dirname(os.path.abspath(target))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(result)
        report["midi_out"] = os.path.abspath(target)
    return report


def format_report(report):
    lines = []
    lines.append("humanize: %s" % report.get("midi_in", "(bytes)"))
    if report.get("midi_out"):
        lines.append("  out %s" % report["midi_out"])
    lines.append("  seed %d | %d bpm | %.2f ticks per frame | %d notes in, %d out"
                 % (report["seed"], report["bpm"], report["ticks_per_frame"],
                    report["notes_in"], report["notes_out"]))
    lines.append("  articulation: %d of %d notes changed length (%.1f%%), "
                 "%d left under the %.0f%% floor by the frame grid"
                 % (report["notes_changed"], report["notes_in"],
                    report["changed_fraction"] * 100,
                    report.get("floor_misses", 0), ARTICULATION_FLOOR * 100))
    for name in sorted(report["notes_by_track"]):
        item = report["notes_by_track"][name]
        lines.append("    %-14s %-9s %3d notes, %3d changed"
                     % (name, item["role"], item["notes"], item["changed"]))
    lines.append("  envelopes %d points | vibrato on %d melody notes | breaths %d"
                 % (report["envelope_points"], report["vibrato_notes"],
                    report["breaths"]))
    lines.append("  ornaments: %d grace note(s), %d mordent(s) | fills %d "
                 "before section changes at bars %s (loop period %d)"
                 % (report["grace_notes"], report["mordents"], report["fills"],
                    ",".join(str(bar + 1) for bar in report.get("section_bars", [])),
                    report.get("loop_period_bars", 0)))
    if report.get("sha256_out"):
        lines.append("  sha256 in %s" % report["sha256_in"][:16])
        lines.append("  sha256 out %s" % report["sha256_out"][:16])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("midi", help="input MIDI (an arrange.py output)")
    parser.add_argument("out", nargs="?", default=None, help="output MIDI")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="fixed humanization seed (default %d)" % DEFAULT_SEED)
    parser.add_argument("--report", default=None, help="write the report JSON here")
    parser.add_argument("--onset-frames", type=float, default=0.0,
                        help="onset micro-timing: move up to this many 1/60 s "
                             "frames early or late, on at most 75 percent of the "
                             "notes (default 0, notes stay on the written grid)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report only, write no MIDI")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.out:
        parser.error("give an output path or --dry-run")

    report = humanize_file(args.midi, args.out, seed=args.seed,
                           write=not args.dry_run,
                           onset_frames=args.onset_frames)
    print(format_report(report))
    if args.report:
        directory = os.path.dirname(os.path.abspath(args.report))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print("  json: %s" % os.path.abspath(args.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
