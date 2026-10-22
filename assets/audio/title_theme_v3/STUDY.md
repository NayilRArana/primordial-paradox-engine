# Motif study: what makes the four leitmotifs recognisable

Card MUS-STUDY, musician lane, 2026-10-21. Deliberate practice, not generation.

Nayil's verdict on v3: the compositions sound great but not quite human, and nothing
really sticks out. This card studies that complaint on the four motifs of
`score_v3.yaml` (K Kronos, Z Zeus, P Poseidon, H Hades) and writes 8 candidate
rewrites of each, 32 in all, scored against a written checklist.

Two hard rules were followed throughout. Nothing here is copied, transcribed or
derived from a published game's music: the sources read were the project's own
`knowledge/MUSIC-STYLE-BIBLE.md` (which cites interviews and hardware documents, no
tunes), the Pine research extracts on NES hardware and on public domain and open
licence classical scores (`Shared/projects/arananet/pine/data/results/*.json`), and
the project's own `score_v3.yaml`. The first pass of this card ran before the hook
grammar and the scorer existed; both landed while it was running, so the second pass
read `knowledge/MUSIC-HOOK-GRAMMAR.md`, reconciled its 20 item delivery checklist
(section 9) against the interim checklist in section 2 below, and scored all 32
candidates with the project's own `tools/hook_score.py` as well as by hand. Section 3
now carries both score tables and section 4 the reconciled picks.
`score_v3.yaml` was not edited by this card: the manager chooses. It does carry an
uncommitted change from an earlier card (the 126 render, `title_theme_v3_126.mid` was
made from it), so `git status` shows it modified; its content hash at the end of this
run is `57333d464e5ab3f2ca63c830672cb3ef`, unchanged by this card.

## 1. What the data said (ten sentences)

1. Across the 32 candidates the checklist mean is 17.1 of 20 with a spread of only 15 to 19, so the checklist separates weak from strong at the margins but cannot, on its own, rank the top five of any family.
2. Six items passed for all 32 (one to two bars, range inside an octave, diatonic to the key, every chromatic note next to a diatonic neighbour, and both the rhythm and the contour differing from the parent motif), which means those six describe the brief rather than discriminate between answers.
3. The item that failed most often on merit was duration contrast, 10 of 32, and the failures cluster in motifs whose rhythm is a single repeated value (plain eighths in Z4 and P3, plain dotted quarters in Z7, plain quarters in Z1 and H2), which is exactly the habit that makes a line sound like a run instead of a hook.
4. Sparse motifs won: K3, K6, Z6, P7 and H7 carry three or fewer attacks in the whole motif, and the four candidates that reach 19 of 20 (Z3, P7, H8 and, after its second pass, H1) are the ones that combine a rest or a held note with a peak in a strong metric position.
5. The busiest motifs lost: Z4 and P3 (six attacks of equal length) and Z8 (15 of 20) show that filling a bar with even notes costs both duration contrast and a clear peak.
6. Peak position is the second strongest discriminator: 11 of 32 put their highest note on a weak eighth, and the worst of them are the arpeggio types (Z4, Z8, P3, P5), where the top of the figure arrives as something to leave rather than as a goal.
7. Two candidates repeat an entire bar of `score_v3` note for note in interval and rhythm (P1 repeats the parent's rising bar E4 G4 B4 in quarters, P2 repeats the D5 B4 dotted pair from section B), so a rewritten motif has to be checked bar by bar, not only by its opening three notes.
8. The chord items cost the chromatic candidates almost nothing (28 to 31 of 32 pass the start and end chord tone items, chromatic nearness passes 32 of 32), which says the four family keys are wide enough to hold their own motifs without cleaning up.
9. Register and metre separate the families rather than the candidates: every P failure on register is a mid register version (P4, P6) and the K and H failures on metre are held bars (K5, H4), so those two items measure the brief, not the version.
10. The honest limit of the run is that no item measures whether a melody is memorable to a listener: the checklist ranks structure, the manager and Nayil rank the sound, and the strongest evidence for that limit is section 3.3, where the project scorer and the checklist agree on only three of the eight picks and disagree in a systematic way, so this study stops at two candidates per motif plus a named alternate that I would also want heard.

## 2. The 20 item checklist

Derived from `knowledge/MUSIC-STYLE-BIBLE.md`: section 2.5 and FOX-04 and MOT-07 for
the narrow singable line, MOT-01 for the three note discipline, MOT-03 and BAR-06 for
the ornament, BAR-11 for the held voice, CLS-02 and CLS-03 for the phrase and its
cadence, CLS-06 and CLS-07 for the waltz, RCK-03 and MET-05 for the flat second and
the short attack, and S1 to S6 for what the chip can actually sound. Each item is one
point, so the score is out of 20. It is computed by `score_motifs.py` (in the card
workspace, not in the repo) from the note data, so every number in section 3 can be
reproduced by anyone who reads the same rows.

| # | Item | The rule it encodes |
| --- | --- | --- |
| 1 | one_to_two_bars | the motif fits one or two 3/4 bars, so it can be heard as one gesture |
| 2 | range_within_octave | at most 12 semitones between the lowest and highest note (FOX-04) |
| 3 | diatonic_to_key | at most one chromatic note outside the key and its named chromatic set (MOT-07) |
| 4 | conjunct_or_arpeggio | at least half the moves are steps, or the figure is a broken chord with at most one turn (BAR-08) |
| 5 | salient_leap | at least one interval of a third or more, so the line has a landmark |
| 6 | duration_contrast | the longest value is at least twice the shortest, so the rhythm has a shape (CLS-07) |
| 7 | attacks_per_bar | at most five attacks in any bar, so it stays singable at 108 bpm |
| 8 | starts_on_chord_tone | the first note belongs to the chord of its bar |
| 9 | ends_on_chord_tone | the last note belongs to the chord of its bar (CLS-03) |
| 10 | ends_with_breath | the last note is a dotted quarter or longer, or the motif ends on a rest (BAR-11) |
| 11 | gap_or_offbeat | the motif contains a rest, or it starts off the beat (RCK-10) |
| 12 | repeated_element | some pitch, interval or duration repeats, so the ear has an anchor (BAR-07) |
| 13 | contour_simplicity | at most two changes of direction (FOX-04) |
| 14 | peak_on_strong_beat | the highest note lands on beat 1, 2 or 3, not on a weak eighth |
| 15 | rhythm_differs_from_parent | the duration reading differs from the motif in `score_v3` |
| 16 | contour_differs_from_parent | the interval reading differs from the motif in `score_v3` (the card's not just transposition rule) |
| 17 | chromatic_near_diatonic | every chromatic note sits within a step of a diatonic note of the motif (MET-05, MET-06) |
| 18 | register_character | the duration weighted mean pitch is inside the family's band (K 60 to 81, Z 64 to 86, P 45 to 72, H 48 to 78) |
| 19 | meter_clarity | at least half the attacks land on a beat of the 3/4 bar |
| 20 | no_exact_bar_copy | no bar is identical in intervals and durations to a bar of `score_v3` (the bar level form of the melody guard) |

Item 20 started as a three note window check against `score_v3` and was replaced: any
three stepwise eighth notes match somewhere in a 52 bar score, so it flagged Z1 and H3
for being ordinary scale motion. The bar level check is stricter and found the two real
repeats named in sentence 7.

## 3. The scores

Tie-break for the ranking: higher total, then fewer attacks, then id. The full per item
breakdown, the intervals and the durations of every candidate are in the `scores` block
of `motif_candidates.yaml`; the same table is in the card workspace as
`scores_table.md`.

| motif | id | label | score | failed items |
| --- | --- | --- | --- | --- |
| K | K1 | the long call | 17/20 | ends_with_breath, gap_or_offbeat, meter_clarity |
| K | K2 | the horn fifth | 18/20 | ends_with_breath, gap_or_offbeat |
| K | K3 | the three knocks | 18/20 | salient_leap, ends_with_breath |
| K | K4 | the descent from the octave | 17/20 | ends_with_breath, gap_or_offbeat, meter_clarity |
| K | K5 | the tolling fourth | 18/20 | gap_or_offbeat, meter_clarity |
| K | K6 | the semitone neighbour | 18/20 | salient_leap, gap_or_offbeat |
| K | K7 | the offbeat summons | 18/20 | peak_on_strong_beat, meter_clarity |
| K | K8 | the two peaks | 18/20 | gap_or_offbeat, peak_on_strong_beat |
| Z | Z1 | the rising steps | 18/20 | salient_leap, duration_contrast |
| Z | Z2 | the leap and roll | 17/20 | ends_with_breath, gap_or_offbeat, repeated_element |
| Z | Z3 | the triplet shine | 19/20 | duration_contrast |
| Z | Z4 | the bell arpeggio | 15/20 | duration_contrast, attacks_per_bar, ends_with_breath, gap_or_offbeat, peak_on_strong_beat |
| Z | Z5 | the held sunrise | 17/20 | gap_or_offbeat, repeated_element, peak_on_strong_beat |
| Z | Z6 | the two note motto | 18/20 | gap_or_offbeat, repeated_element |
| Z | Z7 | the dotted climb | 16/20 | duration_contrast, gap_or_offbeat, peak_on_strong_beat, meter_clarity |
| Z | Z8 | the fanfare third | 15/20 | conjunct_or_arpeggio, ends_on_chord_tone, ends_with_breath, gap_or_offbeat, peak_on_strong_beat |
| P | P1 | the swell | 16/20 | duration_contrast, gap_or_offbeat, peak_on_strong_beat, no_exact_bar_copy |
| P | P2 | the undertow | 16/20 | duration_contrast, gap_or_offbeat, meter_clarity, no_exact_bar_copy |
| P | P3 | the double wave | 15/20 | duration_contrast, attacks_per_bar, ends_with_breath, gap_or_offbeat, peak_on_strong_beat |
| P | P4 | the crest | 16/20 | gap_or_offbeat, repeated_element, peak_on_strong_beat, register_character |
| P | P5 | the deep swell | 16/20 | gap_or_offbeat, repeated_element, peak_on_strong_beat, meter_clarity |
| P | P6 | the tide turn | 17/20 | gap_or_offbeat, register_character, meter_clarity |
| P | P7 | the trident | 19/20 | duration_contrast |
| P | P8 | the surge | 17/20 | conjunct_or_arpeggio, gap_or_offbeat, meter_clarity |
| H | H1 | the two prongs, faster | 19/20 | duration_contrast |
| H | H2 | the double prong | 16/20 | duration_contrast, ends_with_breath, gap_or_offbeat, contour_simplicity |
| H | H3 | the cold descent | 18/20 | salient_leap, ends_on_chord_tone |
| H | H4 | the held prong | 18/20 | repeated_element, meter_clarity |
| H | H5 | the rising bident | 17/20 | starts_on_chord_tone, peak_on_strong_beat, meter_clarity |
| H | H6 | the knocking prong | 17/20 | conjunct_or_arpeggio, ends_with_breath, gap_or_offbeat |
| H | H7 | the thin line | 15/20 | salient_leap, ends_on_chord_tone, ends_with_breath, gap_or_offbeat, repeated_element |
| H | H8 | the low growl | 19/20 | gap_or_offbeat |

Family means: K 17.75 (17 to 18), Z 16.75 (15 to 19), P 16.50 (15 to 19), H 17.00
(15 to 19). No candidate scores 20, which is the honest result: every one of them
breaks a rule on purpose, and the pick is which broken rule a listener will not hear.

### 3.1 The project scorer, tools/hook_score.py, on all 32

`tools/hook_score.py` was run over every candidate twice. "Cell" mode is the candidate
exactly as written; "tiled" mode is the same candidate repeated four times, so the
tool's repetition criteria have something to measure. The harness, the 64 melody and
report files, and the combined result are in the card workspace (`hook_run.py`,
`hook_all.py`, `hook_scores/`, `hook_scores_all.json`), and the same numbers are in the
`scores.hook_score` block of `motif_candidates.yaml`. The tool is out of 100, but three
criteria cannot be earned by a bare one or two bar cell at all (motif_returns 12,
third_return 8, loop_length 6), so the cell column below is out of 74. No candidate
passes third_return in either mode: a motif repeated literally four times is 1.0
similar to itself, and the tool's band for a varied third return is 0.30 to 0.85, which
is a property of the surrounding phrase and not of the cell. Read the cell column as
the shape of the cell and the tiled column as whether that shape survives a loop.

One gap to report rather than hide: the tool looks for a fenced yaml `hook_score:` block
in `knowledge/MUSIC-HOOK-GRAMMAR.md`, found none (the grammar states its thresholds in
prose and in the section 9 table), so its DEFAULTS applied and every report says
`grammar: defaults`. The defaults are Nayil's MEM-TOOLS card of 2026-10-21, so this is
the intended stop gap, but the grammar and the tool's weights are not yet wired together.

| id | cell | notes | tiled | cell failed items |
| --- | --- | --- | --- | --- |
| K1 | 45/74 | 5 | 72/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif, step_ratio |
| K2 | 62/74 | 4 | 67/100 | hook_cell, motif_returns, third_return, repeat_pitch, loop_length |
| K3 | 64/74 | 3 | 86/100 | hook_cell, motif_returns, third_return, loop_length, leaps_per_motif |
| K4 | 58/74 | 7 | 85/100 | hook_cell, contour, motif_returns, third_return, loop_length |
| K5 | 62/74 | 4 | 89/100 | hook_cell, motif_returns, third_return, repeat_pitch, loop_length |
| K6 | 58/74 | 3 | 86/100 | hook_cell, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| K7 | 45/74 | 5 | 72/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif, step_ratio |
| K8 | 58/74 | 6 | 85/100 | hook_cell, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| Z1 | 48/74 | 5 | 64/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| Z2 | 40/74 | 3 | 46/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| Z3 | 46/74 | 4 | 46/100 | step_ratio, hook_cell, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| Z4 | 44/74 | 6 | 46/100 | step_ratio, hook_cell, motif_returns, third_return, leaps_per_motif, repeat_pitch, loop_length |
| Z5 | 40/74 | 3 | 67/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| Z6 | 40/74 | 2 | 56/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| Z7 | 48/74 | 4 | 65/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| Z8 | 46/74 | 4 | 62/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, step_ratio |
| P1 | 44/74 | 5 | 71/100 | step_ratio, hook_cell, motif_returns, third_return, leaps_per_motif, repeat_pitch, loop_length |
| P2 | 48/74 | 4 | 65/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| P3 | 44/74 | 6 | 46/100 | step_ratio, hook_cell, motif_returns, third_return, leaps_per_motif, repeat_pitch, loop_length |
| P4 | 36/74 | 3 | 63/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| P5 | 36/74 | 4 | 63/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| P6 | 72/74 | 7 | 95/100 | motif_returns, third_return, repeat_pitch, loop_length |
| P7 | 36/74 | 3 | 46/100 | step_ratio, hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| P8 | 51/74 | 5 | 78/100 | hook_cell, motif_returns, third_return, step_ratio, repeat_pitch, loop_length, leaps_per_motif |
| H1 | 52/74 | 4 | 57/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| H2 | 52/74 | 6 | 69/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| H3 | 48/74 | 6 | 75/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| H4 | 49/74 | 3 | 76/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, step_ratio |
| H5 | 52/74 | 4 | 69/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |
| H6 | 68/74 | 4 | 83/100 | hook_cell, motif_returns, third_return, loop_length |
| H7 | 48/74 | 2 | 80/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length, leaps_per_motif |
| H8 | 52/74 | 5 | 79/100 | hook_cell, contour, motif_returns, third_return, repeat_pitch, loop_length |

Cell means by family: K 56.5 (45 to 64), Z 44.0 (40 to 48), P 45.9 (36 to 72), H 52.6
(48 to 68). Exactly one candidate of the 32 passes the tool's hook cell item as a bare
cell, P6, and 21 of 32 pass it once the cell is repeated. That is the sharpest single
result of the run: a one bar figure usually states a shape but not yet a cell, so the
fix for "nothing sticks out" is repetition and variation around the cell, not a busier
cell.

### 3.2 The grammar's delivery checklist against a cell

Grammar section 9 is a delivery checklist for a whole cue, so most of it cannot be
answered by a motif cell and belongs to the arrangement card. The items a cell can
answer, measured on all 32 candidates: item 4, range inside an octave, 32 of 32; item 6,
at least one repeated note, 15 of 32; item 7, at most one leap larger than a fourth, 27
of 32; item 8, at least 80 percent diatonic, 24 of 32; item 10, one or two notes outside
the key at a fixed place, answered in the eight picks by naming the note (P6 C5 over Em,
H8 G sharp, K5 D5 over E7). Items 1, 5, 9, 11 and 12 to 19 need the phrase around the
cell (hook length in bars and notes, chord tone share across a phrase, the operation on
the third statement, loop length, antecedent and consequent, bass type, section
contrast, frame timing deviations, rests and fills, the changed ending) and item 20 needs
`tools/melody_guard.py` and its reference folder, which this study did not run.

The interim checklist in section 2 is therefore not replaced by the grammar: it scores
the cell level question the delivery checklist leaves out, namely whether the figure has
a rhythm with a shape, a clear peak, a breath, and is different from its parent. Where
they overlap the grammar is stricter and it sends back more than the interim checklist
did: the 80 percent diatonic rule fails for all eight H candidates (50 to 75 percent,
H8 at 60) and only for those, because the Hades motif is written in harmonic minor and
its identity is the raised seventh, so the rule as phrased in section 9 item 8 is wrong
for a harmonic minor character and needs a named carve-out; the single leap rule (item 7,
at most one leap larger than a fourth) fails for Z3, P1, P3, P4 and P7, five figures that
identify themselves by leaping.

### 3.3 The reconciled ranking

Ranking rule: cell score first, tiled score second, checklist total third, id last. The
cell score leads because the cell is what this card asked for; the tiled score breaks
ties in favour of the figure that survives a loop, which is the repetition problem the
tool exists to catch.

| motif | pick 1 | pick 2 | also hear |
| --- | --- | --- | --- |
| K | K3 (64 cell, 86 tiled) | K5 (62 cell, 89 tiled) | K6 (58 cell, 86 tiled), the checklist's other pick |
| Z | Z7 (48 cell, 65 tiled) | Z1 (48 cell, 64 tiled) | Z3 (46 cell, 46 tiled), the checklist's first pick |
| P | P6 (72 cell, 95 tiled) | P8 (51 cell, 78 tiled) | P7 (36 cell, 46 tiled), the checklist's first pick |
| H | H6 (68 cell, 83 tiled) | H8 (52 cell, 79 tiled) | H5 (62 cell, 79 tiled), the tool's second on the cell score |

The two methods agree on three picks out of eight: K3, P8 and H8. They disagree in a
pattern worth naming. Where a motif's identity is silence or a single held note (P7,
Z3, H4, K6) the tool marks it down, because a rest is not a cell it can count and a held
note gives it no step_ratio; the checklist rewards those figures. Where a motif's
identity is a repeated rhythm (P6, Z7, K5) the tool marks it up and the checklist is
neutral. Both are right about their own question, so the picks below are the tool's
order with the checklist's choices named as the alternates to hear, with one deliberate
override in H: the tool ranks H5 second, level with H1 at 62 on the cell score and tied
with H8 at 79 tiled, and the lane took H8 instead because it is the only 19 in the
family and the only H with an octave drop, so H5 is named as the alternate to hear. This is the one
judgement the lane cannot settle: which of the two readings is what a listener hears.

## 4. The top two per motif, with reasons

### K, the Kronos call

**K3, the three knocks (18/20 checklist, 64 of 74 cell, 86 of 100 tiled).** `E5 1, rest 1, E5 1, rest 1, E5 2`, one bar, Am.
The only K whose identity survives with no melodic movement at all: two staccato knocks
and a held one on a single pitch. It is the cheapest hook on the chip, it cannot be
confused with any other motif in the score, and it fits the character exactly, because
Kronos is time and a clock strikes. It fails the leap item and the breath item, which
is the cost of being pure rhythm. Risk: a repeated E5 at 108 bpm needs the noise
channel kept off that beat or it reads as percussion rather than as a theme.

**K5, the tolling fourth (18/20 checklist, 62 of 74 cell, 89 of 100 tiled).** `E5 6 | B4 1,
C5 1, D5 4`, two bars, Am then E7. A whole bar on E5 is a bell, then a three step
staircase that lands on the seventh of E7, so the call comes back open instead of closing,
which is what a summons should do. It has the highest tiled score in K, 89, with four
returns at coverage 1.0, so it is the K most able to carry a four bar statement. It fails
repeat_pitch (four distinct pitches) and hook_cell (no rhythm cell repeats inside two
bars). Risk: a whole bar on one pitch at 104 bpm needs the echo voice under it or it reads
as a held note rather than a bell, and the second bar wants an answer from another voice.

The tool's own K ranking is K3 64, then K5 and K2 at 62 (K5 ahead on the tiled score,
89 against 67), so the pair is K3 and K5. The checklist's other pick was K6 the semitone
neighbour (58 cell, 86 tiled, 18 of 20): hear it if the manager wants a three note
ornament instead of a bell, because it is the most singable K line and the tool marks it
down only for having no repeated pitch.

### Z, the Zeus rising figure

**Z7, the dotted climb (16/20 checklist, 48 of 74 cell, 65 of 100 tiled).** `C5 3, D5 3 |
E5 3, G5 3`, two bars, C. Four dotted quarters, two per bar, every one of them higher than
the last. The second attack of each bar falls after the beat, so the waltz is pulled
forward and the motif has a lilt that no other Z candidate has. It has the highest tiled
score in Z, 65, and its repeated 3 3 duration pattern is the reason: duration repetition
is the only rhythm identity a two bar cell of four notes can carry. It fails hook_cell
at the cell level and its single leap is the G5 at the top of the second bar. Risk: four
notes in two bars is very slow to read; it needs the rising arpeggio underneath to say
"sunrise" in the first bar, and the 16/20 checklist score is the honest warning.

**Z1, the rising steps (18/20 checklist, 48 of 74 cell, 64 of 100 tiled).** `C5 1, D5 1,
E5 1, F5 1, G5 1, rest 1`, one bar, C. A plain scale with a rest at the end: the simplest
upward shape, and the only Z contour the tool reads as one direction. It passes
step_ratio at the cell and coverage at the tiled run, which is why it holds second place
on the tool's order despite having no repeated pitch. Risk: it is a scale, so the rest
in the last eighth has to be heard as a breath and not as a missing note.

The checklist's first pick was Z3, the triplet shine (19/20, 46 cell, 46 tiled). The
tool ranks it fourth: three fast notes up to C6 read to the tool as leaps without a
repeated cell, and item 7 of the grammar (at most one leap larger than a fourth) fails
it. It stays the one to hear if the manager wants section B marked by register rather
than by rhythm.

### P, the Poseidon tide

**P6, the tide turn (17/20 checklist, 72 of 74 cell, 95 of 100 tiled).** `E5 2, D5 1, C5
1, B4 2 | A4 1, B4 1, E5 4`, two bars, Em throughout. It starts at the crest and curls:
a stepwise fall to the fifth, then a turn and a climb back up the same line, ending on a
long E5. It is the strongest result in the whole study, the only candidate of the 32
whose bare cell passes the tool's hook cell item, because the 2 1 1 2 rhythm repeats inside
the two bars, and tiled it scores 95 with nothing failing except third_return. The turn is
what makes it a wave rather than a scale. Risk: seven notes is the busiest P, and the
checklist marks it down for no rest, so it needs the noise wash and the bass to give the
midpoint somewhere to land; its register band failure is at the top, a duration weighted
mean of 73.7 against the P band ceiling of 72, because of the two E5s.

**P8, the surge (17/20 checklist, 51 of 74 cell, 78 of 100 tiled).** `B4 2, E5 4 | D5 1,
B4 1, G4 4`, two bars, Em. Peak first, then a stepwise roll home. It is the only P that
starts at the top, and because Z is the rising motif and P shares the score with it, a P
that begins high is worth more than one more rising figure. Risk: it fails the conjunct
or arpeggio item because D5 is not in the triad, which is also the reason the roll sounds
like water, and the tool marks it down on step_ratio for the same reason.

The checklist's first pick was P7, the trident (19/20, 36 cell, 46 tiled). The tool ranks
it last in P, and the disagreement is instructive rather than a mistake: three separated
notes give it no step motion, no repeated pitch and no cell it can count, while the ear
hears the gaps themselves as the hook. If the manager wants the sparsest possible P, P7
is the one to hear against P6.

### H, the Hades bident

**H6, the knocking prong (17/20 checklist, 68 of 74 cell, 83 of 100 tiled).** `D5 1, D5 1,
C#5 2, A4 2`, one bar, Dm. The first note is struck twice before it slides: a hammer on
metal, then the semitone, then the drop. It has the best cell score in H and the doubled
attack is the whole difference from the parent; the tool passes range, step_ratio and
leaps_per_motif together at the cell, and tiled it fails only hook_cell. Risk: the
repeated D5 at eighth rate can sound like a mistake unless the second one is quieter or
slightly detached, and the checklist fails it on breath because it ends on a plain A4.

**H8, the low growl (19/20 checklist, 52 of 74 cell, 79 of 100 tiled).** `A4 2, G#4 1, A4
1, G#4 2 | D4 6`, two bars, A7 then Dm. The low prong hammers its semitone four times and
then the motif falls an octave to D4. The drop to the bottom of the usable range is the
strongest register gesture in the whole set, and it ends on the tonic, which no other H
candidate does. It is also the only H pick that scores 19 of 20, and the tool reads its
repeated G sharp as repeat_pitch. Risk: the repeated G sharp at eighth rate can sound like
the metal vocabulary in section 13.2 of the style bible; keep it at quarter rate or slower
so it stays cold and not busy.

The tool's second in H was H5, the rising bident (17/20, 62 cell, 79 tiled), and the lane
did not take it: it is level with H1 on the cell score and with H8 on the tiled score,
and H8 wins the checklist by two points, so H5 is the alternate to hear if the manager
wants the bident pointing up. The checklist's other pick was H4, the held prong (18/20,
49 cell, 76 tiled): a whole bar
on the cold high D, then the drop and the second prong inside one bar. The tool marks it
down on step_ratio because its only moves are one semitone and a rest, so hear it if the
manager wants patience rather than a mechanism.

### One cross motif warning

The picks now lean on repetition more than the first pass did: K3 stays on one pitch, H6
doubles its opening note, Z7 repeats one duration four times, and P6 reuses the 2 1 1 2
rhythm inside its own two bars. Four motifs whose identity is "a note or a duration
repeated" will blur into each other across a cue even though each one passes on its own.
If K3, H6, Z7 and P6 are all chosen, the difference has to be carried by register (K3 at
E5, H6 an octave below, Z7 climbing through the middle, P6 falling from the top) and by
direction, and the manager should hear all four back to back before deciding.

## 5. What the checklist cannot see

1. It cannot hear timbre, duty cycle, vibrato, the echo voice or the noise kit, which
   is where half of the character of these motifs lives.
2. It punishes unisons: K3 is a strong hook and scores badly on two melodic items.
3. It punishes plain even-note arpeggios: Z4 and P3 are the most obviously singable of
   their families and score 15 each, because a repeated note value has no rhythm shape.
4. It has no item for whether two motifs feel alike, which is why the K3 and P7 warning
   above had to be written by hand.
5. It was written in one sitting for this card and has not been tested against a corpus
   of known strong and weak melodies, so the thresholds (half the moves are steps, a
   ratio of two in duration, a third or more for a leap) are judgement calls. The second
   pass reconciled it with `MUSIC-HOOK-GRAMMAR.md` rather than replacing it, and the two
   scorers disagree on five of the eight picks, which is the measure of how much of this
   question is still a listening call.
6. Neither scorer can see silence as a hook. P7, the most distinctive P figure, is last in
   P on the tool and low on the checklist, purely because a rest carries no pitch and no
   duration to measure.

## 6. Files, checks and how to reproduce

Files written by this card:

- `assets/audio/title_theme_v3/motif_candidates.yaml`: 32 candidates, 8 per motif, each
  with bars, chords, notes, rhythm cell, the recognisability reason and the recipe
  citations; the `scores` block holds the 20 item checklist table and, under
  `scores.hook_score`, the tool scores and the reconciled picks.
- `assets/audio/title_theme_v3/STUDY.md`: this file.
- `<agent-runtime>/skills/musician-hooks/SKILL.md`: the skill that
  puts the grammar and this checklist in front of the musician lane on every motif task.

Scripts live in the card workspace, not in the repo: `score_motifs.py` (the checklist
scorer), `summarise_scores.py`, `hook_run.py` and `hook_all.py` (the tool harness, its 64
melody and report files are in `hook_scores/`, the combined result in
`hook_scores_all.json`), `hook_stats.py` and `grammar_items.py` (the numbers quoted in
3.1 and 3.2), `add_hook_scores.py` (writes the tool block into the yaml) and
`verify_mus_study.py` (the checks below).

Checks that ran (all assert failures abort the run, so a green run is the proof):

1. 32 candidates total, 8 per motif, unique ids, ids K Z P H in order.
2. Every candidate is 1 or 2 bars and every bar sums to exactly 6 eighths.
3. Every authored `rhythm_cell` string matches the notes it claims to describe, 32 of 32.
4. The rhythm and contour pair of every candidate is unique: 32 of 32 distinct, 8 of 8
   inside each motif, which is the card's "not just transposition requirement". Every
   candidate also differs from its own parent motif in both rhythm and contour, 32 of 32:
   the first pass left Z2 (same durations as Z), H1 (same contour as H) and H5 (same
   durations as H) failing one of those two items, and those three were rewritten on the
   retry, which is why their totals in section 3 are 17, 19 and 17 rather than 16, 17
   and 16.
5. Every checklist score in section 3 is computed from the note data, not typed, and the
   sum is recomputed from the items.
6. `tools/hook_score.py` ran 64 times without error, once per candidate per mode; the 32
   cell reports and 32 tiled reports are in `hook_scores/`, and every one of them says
   `grammar: defaults`.
7. `score_v3.yaml` was not written by this card. Its md5 is `57333d464e5ab3f2ca63c830672cb3ef`,
   the same as at the end of the second run, and its mtime, 22:08, is the `MUSIC-126` tempo
   retime, whose own render `title_theme_v3_126.mid` is dated 22:09. `git status` lists the
   file, but with line endings ignored the only content difference from git HEAD is
   `bpm: 108` to `bpm: 126` and the `form:` sentence that quotes the duration; no note,
   chord or section differs from the committed score.
8. No em dash or en dash in any of the three written files; `verify_mus_study.py` checks
   the bytes for that and for stray carriage returns.

To reproduce, from `<repo>`:

    python <card workspace>/hook_all.py          # rewrites hook_scores_all.json
    python <card workspace>/hook_stats.py        # the family means and hook cell counts
    python <card workspace>/score_motifs.py      # the checklist table, rewrites the yaml
    python <card workspace>/add_hook_scores.py   # re-adds the tool block to the yaml
    python <card workspace>/verify_mus_study.py  # the checks above

Run `score_motifs.py` before `add_hook_scores.py`: the first one rewrites the whole yaml
and would drop the tool block.

What is not done, on purpose: no candidate has been rendered, because the musician lane
cannot hear and the choice belongs to the manager and to Nayil. The next step is a
listening test of the eight picks plus the four alternates against the four parent motifs
in the same key and tempo, which needs a MIDI render of the candidates, a card the manager
can open. The other gap is that `tools/hook_score.py` and the grammar are not wired
together yet: the tool wants a fenced yaml block with its weights and the grammar states
them in prose, so the tool runs on Nayil's MEM-TOOLS defaults until that block exists.
