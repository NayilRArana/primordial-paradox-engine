# PP-01 title theme: notes for the cue

Cue id `title_theme`, the intro waltz that plays under the title screen drive
(specs/14-title-screen-drive.md). Files in this folder:

| file | what it is |
|---|---|
| `title_theme.mid` | the authored MIDI (5 tracks: meta + pulse 1, pulse 2, triangle, noise) |
| `title_theme.wav` | the render, 44.1 kHz mono 16 bit, 68.571 s |
| `title_theme.mp3` | the same render as MP3, 192 kbit/s |
| `title_theme_loop.json` | the render report: voice map, loop samples, seam measurement, levels |

Everything below is measured from the delivered files, not from the generator source.
Scripts: card workspace `t_0d5099ae` (`verify_title_theme.py`, `read_exact.py`,
`check_counter2.py`, `measure_noise.py`, `measure_tail.py`).

## What is the manager's decision and what is mine

The score below is the manager's, given in the card comment of 2026-10-21, and
implemented literally. I did not choose key, meter, tempo, form, chords, the
melody, the bass figure, the counter line or the noise placement.

- Key A minor (A natural minor), 3/4, 84 bpm, 32 bars, one seamless loop.
- Form: A (1 to 8), A' (9 to 16), B (17 to 24, C major lift), return (25 to 32).
- The Kronos family cell A C E F E (degrees 1, b3, 5, b6, 5) in bars 1 to 2.
- End on E major so the loop wraps.
- NES 2A03 four voices only: pulse 1, pulse 2, triangle, noise.

What is mine, and therefore a proposal for Nayil's ear, is the voice table below
and the three items under "Proposals".

## Measured facts

| check | result |
|---|---|
| MIDI parses | yes, format 1, 5 tracks, 480 ticks per beat |
| key | A minor; pitch classes in the melody are A, B, C, D, E, F, G# |
| metre | 3/4 (time signature meta 3/4, 24 clocks) |
| tempo | 714285 us per quarter, 84.0001 bpm |
| bars | 32 exactly; last note off at 68.559 s |
| motif in bars 1 to 2 | pulse 1 reads 69, 72, 76, 77, 76 = A4 C5 E5 F5 E5, present |
| simultaneous voices | 4 at most, and that is the whole 2A03: pulse 1, pulse 2, triangle, noise |
| duration | 68.571 s (3,023,997 samples at 44.1 kHz) |
| loop seam | sample difference across the wrap 0, last sample 0, first sample 0 |
| loop gap | 11.90 ms of silence before the wrap, then a 5 ms fade in; about 17 ms of near silence at the join |
| peak | 27,851 = -1.41 dBFS sample peak, -0.9 dBFS true peak |
| RMS | 7,165 = -13.20 dBFS |
| loudness | -15.2 LUFS integrated (ffmpeg ebur128), LRA 1.4 LU, target -14 LUFS in specs/12-audio.md |
| project checks | `check_data.py` passes; `check_project.py` reports 2 failures, both in `game/objects/obj_pp_title` (gml without eventList), not audio and not from this card |

Duration is 68.571 s, not the 91 s the original brief said. The brief's figure was
an arithmetic slip: 32 bars of 3/4 at 84 bpm is 32 x 3 x 60/84 = 68.571 s.

## Harmonic plan

Eight bar loop of i, VI, iv, V in A minor: Am (1, 2), F (3, 4), Dm (5, 6), E (7, 8).
The V is E major (E G# B), so bar 7 and 8 carry the G# that makes the loop point
a dominant rather than a minor v. Bars 9 to 16 repeat the same eight bar cycle
with the melody doubled an octave up from bar 13 and the pulse 2 voice holding a
counter line a diatonic third below the melody. Bars 17 to 24 lift to C major
for the headlight feeling: C (17, 18), G (19, 20), F (21, 22), E (23, 24), the
motif stated a major third higher against C. Bars 25 to 32 return to the A minor
cycle and stop on E major, so bar 32 is V and bar 1 is i. That is the half
cadence the brief asked for, and it has a consequence worth hearing: the wrap
is a V into i, so the loop restarts as a resolution rather than as a
continuation. The seam does not sound like the music going on, it sounds like
the music arriving somewhere. If Nayil wants the loop to read as continuous,
bar 32 would need to be a different chord.

The cell sits in two places on purpose: bars 1 to 2 as A C E F E, and again
inside the C major section as C E G A G (bars 17 to 18, notes 72 76 79 81 79),
which is the same five degrees in C major. That is the "the motif becomes major"
idea from the brief, and it is the recognisable shape the leitmotif needs for
its later returns.

## Voice assignment table

| voice | chip | track name in the MIDI | what it plays | register | note velocity |
|---|---|---|---|---|---|
| pulse 1 | 2A03 square 1, 50 percent duty | `pulse 1` | the melody, and the counter line's answer above it in bars 13 to 16 | F4 to B6 (80 notes) | 92 |
| pulse 2 | 2A03 square 2, 25 percent duty | `pulse 2` | the counter line in bars 9 to 16, otherwise chord stabs on beats 2 and 3 | F3 to G#6 (69 notes) | 72 |
| triangle | 2A03 triangle | `triangle` | the waltz bass: root on beat 1, a fifth on beat 3 | D2 to G3 | 100 |
| noise | 2A03 noise | `noise` | a soft brush on beats 2 and 3, bars 9 to 24 only | one band | 30 |

Envelope: the file carries one control change (CC 11 = 127) at tick 0 of every
track and no per note volume ramp, because this renderer applies its own linear
decay to every pulse and noise note from its velocity, and holds the triangle
flat. Note that this renderer reads CC 11 as a level out of 15, so the value 127
is a uniform gain of 8.47 on all four voices, not "full level"; the relative
balance between the voices is therefore set by velocity alone, and the whole mix
is then scaled so its peak is 0.85. So "pulse 1 falls from 8 to 5 over each
note, pulse 2 a notch quieter, triangle fixed" is realised as: pulse 1 velocity
92 decaying linearly to zero across each note, pulse 2 velocity 72, triangle
velocity 100 with no decay. The 2A03 instrument envelopes are not in the MIDI,
and the renderer's decay is not the same curve as a hardware volume envelope:
at the end of a quarter note the amplitude is 0, not the 5 of a hardware
envelope sitting on a release point.

The pulse 2 stabs use the third and the fifth of the bar's chord, one octave
above the bass root: Am gives C4 and E4, F gives A3 and C4, Dm gives F3 and A3,
E major gives G#3 and B3, C gives E4 and G4, G gives B3 and D4. The root of the
chord is never in the stabs; it is carried by the triangle.

One thing to note against the brief: the brief named three chord tones for the
stabs (Am = 57, 60, 64) but asked for two short quarter notes, and the file
plays 60 and 64, the third and the fifth. So the stabs as rendered are the two
upper tones of the triad with the root left to the bass, on every chord in the
piece. If the intent was the root plus the third, that is a one line change in
`gen_title_theme.py` and it would thicken the bars that currently have only the
bass under the melody.

## Two defects in the delivered files

Both are in the generator `tools/gen_title_theme.py`, and I did not change the
files because the manager asked for NOTES.md only.

**1. Three counter line notes do not follow the stated rule.** The rule is
"the same melody a diatonic third below, in the bar's own chord scale, G# rather
than G over the E chords". Checked note by note against the bar's chord scale,
18 of the 21 counter notes in bars 9 to 16 are exact. The three that are not:

| bar | beat | pulse 1 | pulse 2 as rendered | the rule wants | cause |
|---|---|---|---|---|---|
| 13 | 1 | D6 | B5 | A#5 (Bb5) | the third was taken from the A minor scale, which has B natural, not from D minor |
| 15 | 1 | E6 | C6 | C#6 | the E chord map has no entry for E6, so it fell through to "four semitones below", which is C natural |
| 16 | 3 | E6 | C6 | C#6 | the same fall-through |

Why it matters musically: bar 13 is a D minor bar and B natural is a chromatic
raised 6th, six semitones from the F inside the same triad. Bars 15 and 16 are
E major bars, and C natural sits a semitone from the B of the triad, so the one
bar pair that is meant to sound most certain (E major, the dominant, the bar the
loop turns on) is the one that carries the foreign note. The fix is one line in
`third_below`: add `88: 85` to the E chord map, and use the bar's own scale for
the D minor bars instead of the A minor scale.

**2. The noise is not a hat, it is the lowest noise band the renderer has.** The
file writes the brush at MIDI pitch 60. This renderer maps a noise pitch to
`NOISE_PERIODS[min(15, pitch - 1)]`, so pitch 60 is index 15, the longest
period, and the LFSR then advances at only 440 steps per second. Measured on
the renderer's own noise function: 27.5 percent of the energy above 4 kHz,
spectral centroid 3.65 kHz, 90 percent of the energy by 13.1 kHz. A random
binary sequence that changes 440 times a second is a low crackle, not a closed
hat. The mapping is also inverted against FamiTracker, where a higher noise
number is a higher pitch: here a higher MIDI number is a lower frequency, so
the brush sits at the very bottom of the range. The same function at pitch 4
(period 32) puts 82 percent of the energy above 4 kHz, and pitch 6 (period 96)
puts 69 percent above 4 kHz. The MIDI pitch is not wrong as a MIDI pitch, but
in this renderer's numbering it is the wrong end of the noise range for a hat.
It is also quiet by design: velocity 30 against the melody's 92, about 12 dB
down.

## Proposals for Nayil's ear

1. The counter line in bars 9 to 16. As it stands the two pulse voices move in
   parallel thirds, which is the warmest and the most conventional reading. A
   version where the counter line only answers on the second half of each bar
   would leave the first half of bars 9 to 16 to the melody alone, and would
   make the second pulse feel like it is arriving rather than accompanying.
2. The noise brush. Low and quiet now, which suits a night drive. If it reads
   as a rumble rather than a brush, the fix is the noise pitch alone, not the
   level.
3. The loop gap. About 17 ms of near silence at the join, which is two
   separate things: every note in the MIDI is written 8 ticks (11.9 ms) short
   of its written length, so the last note ends 11.9 ms before the bar line,
   and the renderer then fades the last 5 ms. A loop with no gap at all would
   need the note-off offset removed and the last bar's bass held to the bar
   line. The seam itself is clean: the last sample is 0, the first sample is 0,
   and the sample difference across the wrap is 0.
4. The C major lift. Bars 17 to 24 are the only place the piece is not in a
   minor key, and the melody there is the same shape a third higher. It is the
   warmest 8 bars in the cue and it is where the "headlight" reading lives.

## Open items that are not mine to close

- Delivery format. specs/12-audio.md asks for OGG 44.1 kHz, stereo music, at
  -14 LUFS, trimmed 10 ms at each end, with the loop point in the file's own
  metadata plus a sidecar naming the source tempo and the loop. What is here is
  mono WAV and MP3 plus a JSON sidecar. The OGG conversion, the stereo image
  and the -14 LUFS trim are the next step, and the OGG needs the loop metadata
  written into it, not a code side guess.
- Loudness. -15.2 LUFS is 1.2 dB under the target. A plain +1.2 dB gain would
  put the sample peak at -0.21 dBFS and the MP3 true peak at about +0.3 dBFS,
  which risks clipping in the encode. Re-rendering with the normaliser off and
  the triangle trimmed a little is the cleaner route, but that means regenerating
  the files, which this card was told not to do.
- Registry. `data/audio.json` has no `title_theme` entry yet, and the project
  check requires the delivery to be an OGG, so the entry cannot be written
  before the OGG exists.
