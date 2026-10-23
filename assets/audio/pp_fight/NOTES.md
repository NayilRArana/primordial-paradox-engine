# PP-FIGHT: the battle cue, two states on one hook

Card: CUE-FIGHT, created 2026-10-23 by gamedev. Output folder: `assets/audio/pp_fight/`.
This card does not write `data/audio.json`; the cue row is gamedev's.

Clean room: composed here from the written motif below, no borrowed battle theme, no reference
melody transcribed. `tools/melody_guard.py` run against the project's own cue catalogue reports no
shared run of 8 intervals (longest shared interval run: 4).

## Files

| File | What it is |
| --- | --- |
| `build_pp_fight.py` | writes all three MIDI files from note lists written in the file |
| `check_pp_fight.py` | the card's checks, printed as a table, exit 1 on any failure |
| `pp_fight_fight.mid`, `.wav`, `.mp3`, `.ogg` | state A, the FIGHT loop, 16 bars |
| `pp_fight_fight_loop.json` | the loop point the OGG loop comes from (spec 12 rule 3) |
| `pp_fight_calm.mid`, `.wav`, `.mp3`, `.ogg` | state B, the TALK menu loop, 16 bars |
| `pp_fight_calm_loop.json` | its loop point |
| `pp_fight_states.mid`, `.wav`, `.mp3`, `.ogg` | the two states end to end, no loop, so the junction can be heard |
| `hook_report_fight.json`, `hook_report_calm.json` | `tools/hook_score.py` reports |
| `build_report.json` | bars, seconds, notes and voices per module, written by the build |

## The two states

Both are 4/4, D minor, 168 bpm, 16 bars, 22.86 s per pass, and both are a whole number of 4 bar
phrases (four of them), which the check prints. The same tempo in both is deliberate: it is what
lets the last bar of one state be the first bar of the other, tick for tick.

FIGHT is the full VRC6 texture: lead on `vrc6 pulse a` at duty 5/16, guide tone counterline on
`vrc6 pulse b`, a broken chord on `pulse 1`, an echo on `pulse 2` one eighth late and one frame
off the grid, chord roots on `vrc6 saw`, an eighth ostinato on the triangle, and the full kit.

CALM drops to five voices: lead at duty 2/16 (12.5 percent, thin), the echo, one saw pad note and
one triangle pedal per bar, and rim ticks only, no kick at all. The lead plays the same hook at
half note values, so it reads at a felt 84 bpm inside the same 168 bpm grid. Levels fall from 12 to
7 on the lead, 8 to 2 on the saw, 12 to 6 on the triangle, 8 to 4 on the noise, 10 to 4 on the dpcm.

## The hook

Four bars, A4 to G5, 19 notes, one leap larger than a fourth (the A4 to F5 sixth into bar 3, at the
same metric place every statement), one note outside D minor in the phrase (the C# leading tone in
bar 4), and a repeated pedal D on the head. X is the head, Y the answer:

| Bars | What happens |
| --- | --- |
| 1 to 4 | statement: head, answer, third cell rising to the phrase peak, close on the leading tone |
| 5 to 8 | the head and answer again, then an opened, changed ending on A5 (the fifth) |
| 9 to 12 | the same head sequenced up a fourth into G minor, the only other chromatic note (E flat) |
| 13 to 16 | restated, the third cell varied on the third return, then the drop bar |

`tools/hook_score.py` scores the FIGHT lead 84 of 100 (motif returns 3, hook cell 6 notes, 88 percent
steps, contour arch on all three returns, range 15 semitones, 16 repeated pitches, 16 bar loop). The
two items it still marks are motif coverage 37 percent and zero leaps inside the detected 2 bar motif;
the leap sits at the bar 3 downbeat, outside the window it measures. The CALM lead scores 67; it is
the same material at half speed and the scorer sees fewer returns inside 16 bars.

## Why there is no pop at the state change

The FIGHT's bar 16 and the CALM's bar 1 are the same bar, written once and used twice: the lead
plays D5 twice as half notes and then rests, the triangle re-attacks one D3 for the bar, the saw
holds the D root, and `pulse 1` and the echo are silent. The kit is the only thing that changes,
from BAT-09 (drop to rims before the loop) to CLM-02 (rim ticks only). So entering the TALK menu
repeats the bar that was already sounding, and leaving it returns on the hook's first note.

`check_pp_fight.py` proves this by comparing `(offset in bar, length, pitch)` for the lead, the
triangle, the saw, `pulse 1` and the echo across the two files and again across the junction inside
`pp_fight_states.mid`. All five match; the kit differs, and that difference is the hearable entrance.

## Drums

From `data/drum_patterns.json` by id, expanded with the mapping in `knowledge/MUSIC-DRUMS.md`
section 6 (noise period p becomes MIDI note p + 1, `dpcm_kick` 36, `dpcm_snare` 38, a short loop
hit sets CC12 to 1 at that tick).

FIGHT, the variation ladder of section 4: BAT-01 driving eighths for bars 1 to 3, FLF-01 fill at 4,
BAT-06 half time breathing bar at 6 (rung 4, the kick drops out), FLT-01 tom sweep at 8, BAT-02
sixteenth kick across 9 to 12 with BAT-05 gallop at 11 and FLR-01 roll at 12, back to BAT-01 with
FLF-01 at 13, BAT-07 unison stomp at 15, BAT-09 rims at 16. No two fill bars touch, and the sixth
rung never lands twice in a section.

CALM alternates CLM-02 rim ticks and CLM-07 two strikes per two bars at 0.40 to 0.55 velocity, which
is rungs 0 and 1 of the ladder only.

## Numbers measured by the check

- phrase length: FIGHT 16 bars = four 4 bar phrases, CALM 16, STATES 32, all multiples of 4
- the FIGHT loop is 22.86 s, so a 20 s loop point lands inside the varied second half, not at a seam
- loop seam sample difference 0 for both modules, 1008000 samples each at 44.1 kHz
- peak -1.00 dBFS in all three renders; RMS -14.31 dBFS FIGHT, -11.81 dBFS CALM, -16.49 dBFS STATES
- rendered voices: FIGHT 8, CALM 5

## Decisions left for gamedev (not this card)

1. The CALM renders about 2.5 dB hotter in RMS than the FIGHT even after the level drops above,
   because its material is sustained and the renderer normalizes peak. If the mix wants the calm
   clearly under the fight, its volume row should be around 0.5 rather than 0.7, or the fight row
   stays 0.7 and the calm row 0.5. `data/audio.json` is gamedev's file, so this is written here and
   not there.
2. Which state the director switches on, and whether the TALK menu opens on FIGHT bar 1 or on the
   drop bar, is the director's call (specs 07 and 16). The seam works either way: the calm can be
   entered at any bar boundary of the fight, worst case on the drop bar.

## How to rebuild

```
cd assets/audio/pp_fight
python build_pp_fight.py
python ../../../tools/render_chip.py pp_fight_fight.mid pp_fight_fight.wav --loop-bars 16 --hook-report hook_report_fight.json
python ../../../tools/render_chip.py pp_fight_calm.mid  pp_fight_calm.wav  --loop-bars 16 --hook-report hook_report_calm.json
python ../../../tools/render_chip.py pp_fight_states.mid pp_fight_states.wav
ffmpeg -y -i pp_fight_fight.wav -c:a libvorbis -q:a 5 pp_fight_fight.ogg   (and the other two)
python check_pp_fight.py
```
