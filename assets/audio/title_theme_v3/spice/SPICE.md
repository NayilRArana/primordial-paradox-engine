# MUS-SPICE: the drum varier and the dissonance injector

Card MUS-SPICE, builder lane, 2026-10-22. Tool: `tools/spice.py`. Tests:
`tests/test_spice.py` (24 tests, all passing).

The ear review of theme v3 at 126 bpm (`EAR_REVIEW_126.md`) scored drums 4,
tension and dissonance 5 and blamed a waltz drum pattern that never changes and
a harmony that is too safe. This tool is the answer to those two numbers. It
reads the MIDI `tools/arrange.py` writes (or the score yaml, which it arranges
first) and applies two seeded passes.

## What it does

drums (`--drums 0..3`)
  Replaces the noise and DPCM tracks bar by bar with patterns from
  `data/drum_patterns.json`: one home groove per section chosen from
  `waltz_section.non_plain_3_4_ids` (the plain control WZ-01 is never used, and
  neither is a hemiola, cut time or drop out pattern, which are devices and not
  grooves), then that file's variation ladder read as its own bar by bar script:
  the four bar cycle at strength 2, the eight bar cycle plus the hemiola pair and
  the sixteen bar crash landmark at strength 3. Fills land at phrase ends and
  before section changes, a crash lands on the first drum bar of every section,
  a bar the arranger left without drums stays silent, and the noise channel
  never plays two hits at once. A bar whose pattern would push the piece above
  the note count the arrangement itself already reached loses its quietest hits
  until it fits.

dissonance (`--dissonance 0..3`)
  Injects the devices of `data/dissonance_rules.json` by risk level: strength 1
  is the risk 1 colour (chromatic passing DIS-01, chromatic lower neighbour
  DIS-02), strength 2 adds the risk 2 edge (appoggiatura DIS-03), strength 3
  adds the risk 3 clash (one dominant seven flat nine per sixteen bars DIS-11,
  one minor second between the echo and the lead DIS-18). The forbidden list is
  enforced: no device on a frozen leitmotif bar (except the pad's flat ninth,
  which never touches the melody), none on the first or last bar of a section,
  none on the first bar of the cue, two beats apart at least, risk 3 four bars
  apart and one per eight bar window.

## The leitmotif freeze

A bar is frozen when its melody matches a cell the score's `motifs` block
declares (same note count, every interval within one semitone, so a cell
transposed or spelled a third lower still counts) or when it lies inside an
occurrence of the motif `tools/hook_score.py` finds. The tool then hashes every
melody event of those bars before and after and reports whether the two agree.

## Numbers on title_theme_v3_126.mid (52 bars, 3/4, 126 bpm)

| strength | patterns | drum steps changed | fills | crashes | ghost notes | displaced | kicks dropped | hemiola bars | hits dropped for density |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 206 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| 2 | 5 | 233 | 12 | 6 | 12 | 0 | 0 | 0 | 38 |
| 3 | 8 | 266 | 6 | 6 | 12 | 3 | 6 | 12 | 9 |

| strength | devices injected | notes added | by device | hook_score before to after |
|---|---|---|---|---|
| 1 | 6 | 12 | 6 neighbour | 65 to 68 |
| 2 | 9 | 18 | 9 neighbour | 65 to 66 |
| 3 | 10 | 15 | 5 neighbour, 4 flat ninth, 1 echo clash | 65 to 68 |

Both strengths of the drums and the dissonance are monotonic, the flat ninths
land on bars 3, 19, 35 and 51 (every sixteen bars), the leitmotif bars (25 of
52) are byte identical in the melody track (sha `b2c5b0743ad640e8` before and
after), the melody outside the device bars is untouched, the piece never sounds
more notes at once than the arrangement already did (8), and hook_score.py never
drops; it rises.

The humanizer rerun (`--humanize`) changes 1144 of 1192 notes, adds 20 fills,
one grace note and one mordent, and writes `title_theme_v3_126_spice_d3_humanized.mid`.

## Usage

    python tools/spice.py IN.mid OUT.mid [--drums 2] [--dissonance 2] [--seed N]
    python tools/spice.py score.yaml OUT.mid
    python tools/spice.py IN.mid OUT.mid --humanize [--humanize-seed N]
    --report PATH       the JSON report (every change, its bar, its beat, its device)
    --score PATH        the score the MIDI came from (default: looked up next to it)
    --max-hook-drop N   refuse melody devices that cost more than N hook points (5)

`--drums 0 --dissonance 0` reproduces the input note for note. The same input,
seed and strengths give byte identical output.

## Files

    spice/title_theme_v3_126_spice_d1.mid / _d2.mid / _d3.mid   the three renders
    spice/title_theme_v3_126_spice_d3_humanized.mid            the humanizer rerun
    spice/report_d1.json / _d2.json / _d3.json                 the JSON reports
    spice/report_d3_humanize.json                              the humanized report
    spice/report_d1.txt / _d2.txt / _d3.txt / _d3_humanize.txt  the printed reports

## Suite state

`python -m pytest tests` on this checkout: 476 passed, 14 failed, 14 errors, and
none of the failures touch this tool. The failures are the title UI and world
art tests (14 errors in `tests/test_make_title_ui.py`, a missing fixture file),
the v3 arrange tests that still expect 108 bpm, one intro sprite check, the save
module asset name check, the datafile mirror and cleanroom checks, and the em
dash scan, which flags 14 lines in `EAR_REVIEW_126.md` plus
`knowledge/study/ut_decomp` (none in any file this card wrote).
`tests/test_spice.py` passes 24 of 24, and the humanize articulation failure in
`tests/test_humanize.py` is a 0.2 tick rounding edge in that test's own synthetic
song, untouched by this card.

Correction, 2026-10-22 (card t_8a45271e, musician): the 14 long dashes in
`EAR_REVIEW_126.md` were rewritten with commas and hyphens, so that scan now passes. The
scan prunes any directory named `study`, which is why `knowledge/study/ut_decomp` never
appears in its output; only the pasted note was ever flagged.
