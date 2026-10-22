# Title theme v3: what is in the render, and what to listen for

Card MUS-V3. The score is the manager's composition
(`score_v3.yaml`, seven sections, 52 bars of 3/4 at 108 bpm, A minor, the
Kronos motif E C D E and the new Percy and Hadrian motifs). This card did not
recompose anything: it extends `tools/arrange.py` to read the sections schema,
renders the result with `tools/render_chip.py`, and measures it with the new
`tools/measure_theme_v3.py`.

## What the arranger reads, and what it implements

The structured fields come from the file: `sections` in playing order, the bar
count of each section, the chord list (including the `X|Y` split form), the
melody bars where they are written as lists, and the written rule where the
melody is prose. Three sections are prose directives:

- `A_prime`: same notes as A, bars 1 to 4 an octave up;
- `B_prime`: Z and the B melody, bars 5 and 6 an octave up;
- `A_return`: same notes as A, the last bar B4 held.

`arrange.resolve_melody_v3` understands exactly those phrases and raises on
anything else, so a rewording in the score cannot silently produce no melody.

The texture lines are prose, so they are implemented as recipes keyed by
section name (`V3_TEXTURE_READ_AS` in the tool records the reading in one
place). Three readings are worth the manager's eye:

1. **The pulse 2 echo.** The score asks for it in A, B and A return. It is
   dropped in A prime and B prime, where the pulse b thirds line takes the same
   slot, because both together would put nine notes on the beat. The note limit
   is 8 and the arrangement hits exactly 8 in A, A prime, B, B prime and
   A return.
2. **The B pad.** The texture says "sustained pad". It is a shell (third and
   seventh, two notes), not a full triad, for the same eight note budget.
3. **The snare fills.** `voices.noise` names bars 8, 16, 24, 32 and 40, which is
   the bar numbering of the 44 bar form that existed before section C trio was
   inserted. The arranger puts the fill on the last bar of each section
   instead: bars 12, 20, 28, 36, 52, and no fill at the end of the trio because
   the trio's bars 5 to 8 are written as "no hats".

## The numbers, as measured

- MIDI: format 1, ppq 480, 3/4, tempo meta 555556 us/qn (108.0 bpm), 9 tracks
  (meta plus the 8 the renderer expects), 13,218 bytes.
- 52 bars, 86.667 s of score; the rendered WAV is 3,822,003 samples, 86.667 s.
- The chord list of every section equals the score (`chords_match_score` true).
- Key signature meta is A minor (no accidentals), as the score says.
- At most 8 notes sound at once; per section the count is intro 6, A 8,
  A prime 7, B 8, B prime 8, C trio 6, A return 7.
- No voice writes outside its register (`out_of_range` empty).
- Loop: bar 5 (the first bar of section A) to the end of A return (bar 52),
  48 bars, 80.0 s, from sample 294000 to sample 3822003. The wrap step across
  that seam is 0 samples.
- Per voice RMS (each voice rendered alone at its mix gain): triangle -18.35 dB,
  vrc6 saw -24.74 dB, vrc6 pulse a (the lead) -25.12 dB, vrc6 pulse b -30.80 dB,
  pulse 1 -30.41 dB, noise -31.00 dB, dpcm -33.71 dB, pulse 2 (the echo)
  -48.48 dB. Nothing is silent and nothing clips.
- The mix peaks at -1.0 dBFS with an RMS of -16.59 dBFS.

## The FFT checks

Measured on the lead voice rendered on its own, middle half of each note, peak
interpolated between FFT bins:

| check | expected | measured | error |
|---|---|---|---|
| A bar 1, note 1 | E5 659.26 Hz | 659.15 Hz | -0.27 cents |
| A bar 1, note 2 | C5 523.25 Hz | 523.62 Hz | +1.23 cents |
| A bar 1, note 3 | D5 587.33 Hz | 587.58 Hz | +0.73 cents |
| A bar 1, note 4 | E5 659.26 Hz | 659.48 Hz | +0.59 cents |
| trio bar 1, note 1 | E4 329.63 Hz | 330.45 Hz | +4.30 cents |
| trio bar 1, note 2 | G4 392.00 Hz | 392.09 Hz | +0.44 cents |
| trio bar 1, note 3 | B4 493.88 Hz | 493.73 Hz | -0.52 cents |
| trio bar 5, note 1 | D5 587.33 Hz | 588.42 Hz | +3.22 cents |
| trio bar 5, note 2 | C#5 554.37 Hz | 554.37 Hz | +0.02 cents |

All nine are inside one percent (17.2 cents).

In the **full mix** the answer is different and worth saying plainly: the
triangle bass is 6.8 dB above the lead and the saw pad is level with it, so a
broadband FFT of the mix picks the bass or an arpeggio partial on some notes
(bar 5 note 3 reads 165 Hz, the trio bar 1 reads 247.66 Hz). Searched in the
melody band (380 to 900 Hz) the mix reads the melody correctly in A bar 1
(within 1.41 cents) and in trio bar 5 (within 3.82 cents), but in trio bar 1
the melody sits at E4, G4 and B4, inside the register where the arpeggio and
the bass live, so the E4 is still masked by the B4 of the arpeggio. If the lead
is to be the loudest voice, that is a mix decision for the manager: the melody
gain in `render_chip.py` (vrc6_pulse_a 0.32) is unchanged by this card.

## Files

- `assets/audio/title_theme_v3/score_v3.yaml` (the manager's composition, not
  touched by this card)
- `assets/audio/title_theme_v3/title_theme_v3.mid` (arranged, 8 voices)
- `assets/audio/title_theme_v3/title_theme_v3.wav` (44.1 kHz mono 16 bit)
- `assets/audio/title_theme_v3/title_theme_v3.mp3` (192 kbit/s)
- `assets/audio/title_theme_v3/title_theme_v3.ogg` (Vorbis q6)
- `assets/audio/title_theme_v3/title_theme_v3_loop.json` (loop point, per
  voice levels, FFT checks)
- `tools/arrange.py` (version 3 schema added, version 2 path byte identical)
- `tools/measure_theme_v3.py` (loop, per voice levels, the three FFT checks,
  OGG encode)
- `tests/test_arrange_v3.py` (24 tests)

The version 2 render is untouched: `tools/arrange.py` on
`assets/audio/title_theme_v2/score.yaml` still writes a byte identical
`title_theme_v2.mid`, and the three music test files still pass (118 tests).

`melody_guard.py` against `Shared/projects/musikage`: PASS, 11 references
compared, highest 5-gram Jaccard 0.0000, longest identical (interval, rhythm)
run 0, longest identical interval run 3.

The OGG is not yet copied into `game/datafiles/streams`; `tools/sync_art.py`
does that and it is the next card's call, since it also touches the GameMaker
project file.
