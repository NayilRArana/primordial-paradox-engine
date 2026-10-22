# Title theme v2: what is in the render, and what to listen for

Card MUS-THEME-2. The score is the manager's composition
(`score.yaml`, 52 bars of 3/4 at 104 bpm, A minor, Kronos leitmotif
A C E F E). This card did not recompose anything: it runs
`tools/arrange.py` on that score, renders the result with
`tools/render_chip.py`, and measures it.

## The defect that was fixed first

`tools/arrange.py` wrote the MIDI tempo meta as `500000 * 60 / bpm`
microseconds per quarter note. The unit wants `60000000 / bpm`, so the
value came out exactly half: the file said 288461 us/qn where 104 bpm
needs 576923. Every render of that file played at 208 bpm, and the 90 s
cue came out 45 s long. That also explains the pitch reading the manager
saw: the bar 5 and 6 analysis windows were landing on the wrong bars of
a file running at double speed.

Fixed in `_meta_track` (plus a `_microseconds_per_quarter` helper), and
`self_check` now re-reads the written file and reports
`midi_bpm`, `midi_time_signature`, `midi_bar_ticks`,
`midi_duration_seconds` and `tempo_meta_matches_score`, so the same unit
error cannot pass silently again. After the fix the arranger prints
`midi_bpm 104.0`, `midi_time_signature 3/4`, `midi_bar_ticks 1440`,
`midi_duration_seconds 90.0`, `tempo_meta_matches_score true`.
`pytest tests/test_arrange.py tests/test_render_chip.py
tests/test_render_chip_v2.py` still passes, 118 tests.

## Files

| file | what it is |
| --- | --- |
| `title_theme_v2.mid` | the arrangement, 9 tracks, ppq 480, 3/4, 104 bpm |
| `title_theme_v2.wav` | the render, 90.000 s, mono 44100, peak -1.00 dBFS, RMS -16.55 dBFS |
| `title_theme_v2.mp3` | same audio, 192k |
| `title_theme_v2.ogg` | same audio, Vorbis q6 |
| `title_theme_v2_loop.json` | the renderer report plus the loop region, per voice levels and the FFT pitch check |
| `arrange_report.json` | the arranger self check |

Loop: intro is bars 1 to 4, the loop is bar 5 to bar 52, so the loop
point is sample 305308 (6.923 s) and the loop is 48 bars (83.077 s).
Measurements are reproducible with
`python tools/measure_theme_render.py`.

## What each voice does

- **vrc6 pulse a, melody.** States the leitmotif (A4 C5 E5), leans on
  the b6 (F5), and in section B climbs to A5 and G#5. Duty 0.25 in the
  intro and A, 0.5 in B. Vibrato of 15 cents at 5.5 Hz starts one eighth
  into notes of three eighths or longer.
- **vrc6 pulse b, guide tone countermelody.** A2 only, 48 notes: the 3rd
  or 7th of each chord in quarters, kept under the melody.
- **vrc6 saw, harmony.** Sustained chords in the intro, oom-pah-pah
  stabs on beats 2 and 3 in A and A2 (shell voicing, 3rd and 7th), a
  soft pad through B. 196 notes.
- **pulse 1, arpeggio and thirds.** Broken-chord eighths in octave 4
  through the intro and A, parallel thirds or sixths in B, arpeggio again
  in A2. Duty 0.125. 149 notes.
- **pulse 2, echo.** The melody one eighth late at 40 percent, duty
  0.125. 136 notes.
- **triangle, waltz bass.** Root on beat 1, rest on beat 2, fifth or a
  chromatic approach on beat 3; walking quarters in B. 120 notes.
- **noise, hat and fills.** Closed hat on beats 2 and 3 from A on,
  silent in the intro, three-eighth snare fill on the last beat of bars
  20, 36 and 52. 102 notes.
- **dpcm, kick.** Beat 1 only, in B and A2. 32 notes.

Note that the score names `dpcm_kick` and the arranged track is `dpcm`;
they are the same voice.

## The checks

- Duration 90.000 s, tempo 104.0 bpm, 3/4, 52 bars.
- Peak -1.00 dBFS (soft limiter, knee 0.80), RMS -16.55 dBFS.
- Loop seam: whole-file wrap step 0 samples. Across the musical loop
  point (end of bar 52 into bar 5) the step is 456 counts, -37.13 dBFS,
  and the last 5 ms of the file are faded by the renderer's raised cosine
  so the wrap is not a hard edge. Head of the loop peaks at -15.09 dBFS,
  tail at digital zero.
- Per voice, measured with each voice rendered on its own at its own mix
  gain: none silent, none clipping. RMS in dBFS: triangle -17.79,
  vrc6_saw -23.94, vrc6_pulse_a -24.55, noise -30.59, vrc6_pulse_b
  -30.65, pulse1 -31.39, dpcm -32.20, pulse2 -37.23.
- FFT of the leitmotif in bars 5 and 6, measured on the melody voice:
  A4 439.71 Hz, C5 523.15, E5 659.13, F5 698.51, E5 660.83. All five
  within 1 percent, worst 4.12 cents, which is the vibrato.
- In the full mix a broadband FFT peak picks the accompaniment on three
  of the five notes (it reads C4, C4, E4, because the saw stabs and the
  waltz bass are louder than the melody's fundamental). Limited to the
  melody band, four of five read correctly and only the F5 window fails,
  where the pulse 1 arpeggio is on C5. The melody is present at the right
  pitches; it is simply not the loudest thing in the mix.
- Originality guard: `tools/melody_guard.py` on the melody track against
  `Shared/projects/musikage`: PASS, highest 5-gram Jaccard 0.0000,
  longest identical (interval, rhythm) run 0, longest identical interval
  run 3. The tool compared 10 of the 724 MIDI files under that folder.

## What Nayil may want changed

1. **Melody level.** The melody is 6.8 dB under the triangle bass in RMS
   and level with the saw stabs, which is why the mix FFT reads the
   accompaniment. Raising `vrc6_pulse_a` and lowering `triangle` a little
   would make the tune sit on top. This is the one change I would make
   second, after hearing it.
2. **The 5 ms fade at the file end.** That is the renderer's loop
   treatment, not part of the music; a game engine looping bar 5 to 52
   gets a very short fade into the loop start. If it is audible, the
   alternative is an unfaded tail with the seam handled by the engine.
3. **The drum kit.** The hat and the three-eighth fills are the sparsest
   part of the arrangement; the waltz could take a softer closed hat on
   beat 2 only, or the fills could move to the last beat of every fourth
   bar instead of bars 20, 36 and 52.
4. **Pulse 2 echo at 40 percent** is subtle; a little more would widen
   the theme, a little less would clean up the counterpoint in B.

Nayil judges by ear. Nothing here is uploaded or published.
