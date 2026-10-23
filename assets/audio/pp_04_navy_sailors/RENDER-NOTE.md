# PP-04 "Navy Sailors", render note

Card MUS-CUE-PP04 (t_becd6879), musician lane, 2026-10-22. Cue row PP-04 in `data/audio.json` (not edited).

## The four numbers the card asks for

| item | value |
| --- | --- |
| tempo | 176 bpm, 4/4, one bar 1.363636 s, D minor |
| bars | 32, 43.636 s total |
| loop point | bar 1 to bar 28, 38.182 s; bars 29 to 32 are the resolve tail, played once when the fight ends |
| voices | `vrc6 pulse a` lead, `vrc6 pulse b` held fifth, `vrc6 saw` low root, `pulse 1` power chord root, `pulse 2` power chord fifth, `triangle` bass, `noise` hats, `dpcm` kick and snare. Eight chip voices, no sample beyond DPCM, no instrumental |

## Form, and why the hook lands inside four seconds

- `A` 8 (bars 1 to 8) states motif N: A Bb A, a fifth leap to D5, E5 held, then the answer
  G A Bb C D settling on C. Six notes a bar, rhythm 1 1 2 1 2 1, one leap and the rest steps.
- The hook cell is bars 1 and 2 and it is complete at 2.727 s. The four bar phrase ends at 5.455 s.
  The lead's first note is at 0.000 s: there is no intro, which is the Capcom stage rule (capcom.md 4.2).
  The cell returns at bars 5, 17 and 25, and bars 23 and 24 change it, so the third return is not a copy.
- `B` 8 (bars 9 to 16) is the release, and it is deliberately where the dodge phase sits: long notes,
  duty 0.25, the power chord and the kick drop out for four bars, hats only on beats 2 and 4.
- `A2` 8 (17 to 24) is the hook with the full band, sixteenth hats and a noise fill in bar 24.
- `A3` 8 (25 to 32): bars 25 to 28 state the hook and end on the leading tone, so the loop seam is a
  lift back to D minor; bars 29 to 32 walk up the triad and stop on a held tonic D.

## The warning blip, and the margin against it

The blip id is `alarm` (`assets/audio/sfx/alarm.wav`): a 50 percent pulse on MIDI 84 and 88, that is
C6 1046.5 Hz and E6 1318.5 Hz, the two tones alternating for 0.64 s. That is the cue the arena and the
spec 08 hit feedback can play over the music.

Two things keep it clear, and both are measured:

1. No voice writes a note within a semitone of either tone. Lead 67 to 81, held fifth 62 to 69, saw 43 to
   50, `pulse 1` 43 to 50, `pulse 2` 50 to 57, triangle 36 to 46. The noise channel is hats only at the
   top rate (18,643 Hz clock), the fill and crash rates 3.5 to 8.9 kHz, all far above 1046 to 1319 Hz.
2. Narrow band RMS of the mix at each tone against the alarm's own level in the same 50 Hz window:
   33.7 dB down at 1046.5 Hz and 30.5 dB down at 1318.5 Hz.

## Checks run, with the output

```
python assets/audio/pp_04_navy_sailors/build_pp04.py
    -> 43.636 s, 32 bars, 158 lead notes, hook cell end 2.727 s
python tools/melody_guard.py assets/audio/pp_04_navy_sailors/melody_lead.json \
    "<workspace>/Shared/projects/musikage" --json .../melody_guard.json
    -> PASS, longest identical interval run 5 of 8 allowed, best jaccard 0.0000
python tools/render_chip.py .../pp_04_navy_sailors.mid .../pp_04_navy_sailors.wav --loop-bars 32
    -> peak -1.00 dBFS, rms -15.67 dBFS, seam sample difference 0
ffmpeg -c:a libvorbis -q:a 6 (the ogg, from the same wav)
python assets/audio/pp_04_navy_sailors/pp04_check.py
    length 30 to 45 s                PASS   wav, mp3, ogg all 43.636 s
    mp3 and ogg same length          PASS   spread 0.000 s
    hook cell inside 4 s             PASS   2.727 s, first lead note at 0.000 s
    no voice on a blip tone          PASS   no clash in any of the six pitched voices
    blip band at least 10 dB down    PASS   30.5 dB worst case
    eight chip voices only           PASS   meta plus the eight chip tracks
```

The project's hook grammar tool (`--hook-report`) scores the melody 74 of 100: motif returns, hook cell,
steps over leaps, range, repeated pitch and loop length all pass; contour (0 of 5 returns read as arch or
pedal) and motif coverage (38 percent) do not, because motif N opens with a neighbour turn rather than a
single arch. That read is not a card gate, and the fix would cost the turn that gives the hook its shape.

## Files

| file | what it is |
| --- | --- |
| `score_pp04.yaml` | the score: meta, motifs, sections, chords, melody, voices, the blip note |
| `build_pp04.py` | the recipe: score to the eight voices, via the project's own MIDI writer |
| `pp_04_navy_sailors.mid` | the arrangement, ppq 480, 176 bpm, 4/4, 9 tracks |
| `pp_04_navy_sailors.wav`, `.mp3`, `.ogg` | the render, mono 44.1 kHz, peak -1.00 dBFS |
| `pp_04_navy_sailors_loop.json` | the renderer's own loop report for the whole file |
| `pp_04_loop_points.json` | the intended loop: bar 1 to 28, plus the 4 bar resolve tail |
| `pp_04_score_report.json` | bars, seconds, section counts, note counts per voice, voice ranges |
| `pp_04_hook.json` | the hook grammar read of the lead line |
| `melody_lead.json`, `melody_guard.json` | the lead line and the originality report |
| `pp04_check.py`, `pp_04_check.json` | the six card checks and their numbers |

## Which files here the commit carries, and why one does not

Committed: `score_pp04.yaml`, `build_pp04.py`, `pp_04_navy_sailors.ogg`,
`pp_04_navy_sailors_loop.json`, `pp_04_loop_points.json`, `pp_04_score_report.json`,
`pp_04_hook.json`, `pp_04_check.json`, `melody_lead.json`, `melody_guard.json` and this note. The
builder is measured by `tests/test_build_pp04.py` (card t_6af137c1), which reads the committed score
only: it rebuilds the cue, checks it against `pp_04_score_report.json`, writes the MIDI through
`tools/arrange.py` into a throwaway folder and reads the lead line back through
`tools/melody_guard.py` against the committed `melody_lead.json`.

`pp04_check.py` is a WORKING TREE TOOL, deliberately not committed. It reads
`pp_04_navy_sailors.wav` and `.mp3` (ffprobe on all three codecs), takes a narrow band FFT of the
wav, and needs numpy; the wav and mp3 are masters the root `.gitignore` keeps out of the repository.
A test for it could only skip when the master is absent, and this project ruled that out after card
t_50a290de: a test that passes by skipping reads nothing and looks healthy at HEAD. Run it from the
live tree instead:

```
python assets/audio/pp_04_navy_sailors/pp04_check.py
```

## Two decisions for Nayil's ear

1. The resolve: bars 29 to 32 are a 5.5 s tail that ends on the tonic. If the fight ends on the command
   menu rather than on the last hit, the engine should start the tail from bar 29 and stop the loop.
2. The bridge (bars 9 to 16) is the quietest part and the place the alarm has to cut through. If it reads
   too thin under the blip, the fix is two levels on the lead in `SECTION_LEVEL` for `B`, nothing else.
