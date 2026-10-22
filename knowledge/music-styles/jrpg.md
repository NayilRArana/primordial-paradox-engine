# Scope study: JRPG on the Famicom and NES (jrpg)

Card t_49c5e0b9 (STUDY-JRPG), job-discovery, written 2026-10-21. Covers Final Fantasy I to III
(Nobuo Uematsu), Dragon Quest I to IV (Koichi Sugiyama), Mother / EarthBound Beginnings (Keiichi
Suzuki and Hirokazu Tanaka) and Crystalis (Yoko Osaka) as a comparator. Final Fantasy Mystic Quest
is out of scope.

Read with `knowledge/MUSIC-HOOK-GRAMMAR.md` (the 20 item delivery checklist and the recognition
studies) and `knowledge/MUSIC-STYLE-BIBLE.md` (chip parameters, the Uematsu and Mother sections,
progression grammars). This file adds the per-game genre layer: what the JRPG cue does that the
general NES cue does not, with numbers.

## 0. Rules, method and what the numbers are

- Ground rule (PLAN-V2 section 0): study only. No melody was transcribed, and none is written here.
  Every musical statement below is a count, a ratio, a bar number or a described gesture. The
  arranger must not reconstruct a theme from these rows.
- Two kinds of number are used, and they are labelled:
  - **measured**: computed by the corpus script over NES-MDB transcriptions. Read from
    `D:\Musikage-Corpus\style-pp\stats\nobuo_uematsu.json` (104 pieces, 1758 bars, 34432 notes,
    10912 melody notes) and `D:\Musikage-Corpus\style-pp\stats\hirokazu_tanaka.json` (40 pieces,
    878 bars, 13953 notes, 4495 melody notes), both generated 2026-10-21T19:49:50.
  - **published**: stated in a linked analysis, interview or review, cited by id.
  - **[inference]**: my operationalisation of the above, phrased as a rule to build against.
- Corpus caveat, important: every piece in both statistics files carries tempo 120 bpm and metre
  4/4, so tempo and metre in that corpus are normalised artefacts and are NOT evidence about the
  original recordings. Tempo and metre claims in this file come from published analyses only. The
  corpus is good for intervals, durations, range, note density, chord vocabulary and cue length.
- Definition note, now resolved by arithmetic: the corpus records `step_ratio` and `leap_ratio` without
  stating a definition. Checked against the interval histograms, `step_ratio` is exactly the summed
  share of intervals 0, plus or minus 1, and plus or minus 2 semitones: 43.2 plus 6.0 equals 49.2
  for Uematsu (recorded 0.4921) and 45.6 plus 16.2 equals 61.8 for Tanaka (recorded 0.6177). Watch
  that it counts repeated notes as steps, which is why it reads high for the Mother corpus.
- Chord quality counts come from an automatic chord estimator on monophonic transcriptions, so the
  sus4, sixth and seventh figures are best read as proportions, not as the composer's written
  chords.
- No corpus exists for Sugiyama or for Crystalis in `D:\Musikage-Corpus\style-pp\stats` (the five
  files present are classical, nes_rock_metal, nobuo_uematsu, hirokazu_tanaka, toby_fox). Dragon
  Quest numbers below are therefore published or counted by hand [inference], and that gap is
  stated again in section 12.

Source ids: S-numbers are reused from MUSIC-STYLE-BIBLE.md section 6 and MUSIC-HOOK-GRAMMAR.md
section 10. JR-numbers are new, listed in section 13 with link and read date.

## 1. The four voice personalities, in one table

Measured melody behaviour over the two corpus files. This table is the single most useful artefact
in the file: two composers working on the same chip, same era, opposite melodic habits.

| Measure (measured) | Uematsu, FF I to III | Tanaka (with Suzuki), Mother |
| --- | --- | --- |
| Pieces / bars / melody notes | 104 / 1758 / 10912 | 40 / 878 / 4495 |
| Major to minor | 56 major to 48 minor | 29 major to 11 minor |
| Repeated notes (interval 0) | 6.0 percent | 16.2 percent |
| Step motion, 1 or 2 semitones | 43.2 percent | 45.6 percent |
| Octave leap up or down, 12 semitones | 8.1 percent | 1.3 percent |
| `step_ratio` as recorded | 0.4921 | 0.6177 |
| `leap_ratio` as recorded | 0.5079 | 0.3823 |
| Wide leaps over 19 semitones | 2.5 percent | 0.58 percent |
| Median melody range | 35.5 semitones | 22.5 semitones |
| Median notes per bar | 5.3 | 4.66 |
| Median melody pitch, MIDI number | 73 | 74 |
| Median bass pitch, MIDI number | 48 | 44 |
| Median melody note length, beats | 0.66 | 0.59 |
| Median bass note length, beats | 0.36 | 0.45 |
| Median voices per piece | 3 | 3 |

Reading [inference]:

1. Uematsu is a leaping, octave-based, wide-range melodist. Half his melodic motion is not stepwise,
   and one note in twelve is an octave jump. The octave is his cheapest identity device, and it is
   also the one every imitator forgets.
2. Tanaka and Suzuki write a repetitive, singable line: nearly one melody note in six is a repeat of
   the previous pitch, so step and repeat motion together make up 61.8 percent of all intervals,
   against 49.2 percent for Uematsu. That is the statistical fingerprint of the "anyone can hum it
   with one finger" brief [S11]. The gap between the two composers sits almost entirely in the
   repeated note and in the octave, not in step motion, which is nearly equal.
3. The bass tells the two styles apart as clearly as the melody: Uematsu's bass sits higher (MIDI 48
   against 44) and moves twice as fast (0.36 beats per note against 0.45), which is the walking,
   driving bass of his battle and field cues. Tanaka's bass is lower and longer, a foundation rather
   than a hook.
4. Both keep the melody near MIDI 73 to 74, roughly D5, so the lead sits in the pulse's sweet spot
   and the triangle can cover two octaves below without masking [S1, S2].

## 2. Signature moves, with numbers

### 2.1 Uematsu, Final Fantasy I to III

1. **The octave as punctuation.** Measured: 5.39 percent of intervals are a leap up of exactly 12
   semitones and 2.75 percent are down 12, and the two most common two-interval windows in the whole
   corpus are up an octave then back down (262 occurrences) and down an octave then back up (248).
   Together those windows are 4.7 percent of all two-interval windows. The shape is a note, its
   octave, and the return, which is a signal rather than a melody [measured].
   Rule: one octave jump per 2 to 4 bar phrase, always resolved back inside a beat or two.
2. **Sixteenth density with dotted emphasis.** Measured durations in sixteenths: 59.6 percent of
   melody notes are one sixteenth, 12.4 percent are three sixteenths (dotted eighth), 11.4 percent
   are two sixteenths (eighth), 3.6 percent are a quarter. The dotted eighth is 9 percent more
   common than the plain eighth, which is the audible reason his lines lurch rather than glide
   [measured]. The most common duration pair is sixteenth plus sixteenth (5665 of 10807 windows).
3. **A narrow hook over a rich progression.** Published: the FF I battle theme is G minor at 150 bpm
   with an 8 semitone melody range, 0.88 beats per note over 106 beats, 80 percent diatonic, 69
   percent chord tones, and chord complexity 94 on a scale where 50 is average [S53]. Identity sits
   in the harmony and rhythm, not in pitch travel. This is the opposite design from his field
   themes, which are wide [measured 35.5 semitone median range].
4. **Broken chord as a whole piece.** Published: the Prelude is B flat major at 100 bpm, melodic
   complexity 93 to 94, chord progression novelty 95, built on one arpeggio pattern [S54]. Measured
   in the corpus it is 19 bars, 2 voices, and it is the only FF I cue with two voices. Rule: one
   figure, two voices, no drum, and the figure itself carries the whole cue.
5. **The delayed, detuned second voice.** Published in his own words: the same line on two pulses
   with the second slightly shifted in pitch and time produces the shimmer that makes square waves
   feel emotional [S7, S8]. Measured support: chord quality counts put sus4 at 848, above maj7 at
   730 and dominant 7 at 675, which is what a delayed doubling produces under an automatic
   estimator (the second voice lands on the neighbouring tone) [measured, with the estimator caveat
   in section 0].
6. **Cruel economy in the stings.** Measured cue lengths in the corpus: FF I Fanfare 2 bars (G
   major), SaveJingle 3 bars (A major), Victory 8 bars (E flat major); FF II Revival 3 bars, Chocobo
   Theme 3 bars; FF III Item Get 2 bars (F major), A Comrade Joins 3 bars, Garuda Defeated 3 bars,
   Rest at the Inn 3 bars, A Comrade Leaves 2 bars. Rule: an event sting is 2 to 3 bars, a victory
   is 6 to 8 bars, and neither loops.
7. **A major third of colour between battle and victory.** Measured keys: FF I Battle is G minor and
   FF I Victory is E flat major, which is a minor sixth up (a minor third down) from the battle
   tonic; the victory lands on a flat-side major [measured]. Rule: put the victory a third away from
   the battle key, not in its dominant.

### 2.2 Sugiyama, Dragon Quest I to IV

1. **A march with a fanfare frame.** Published: the Overture has three sections, a majestic fanfare
   introduction marked Maestoso, a march main theme over a lively snare rhythm, and an ending that
   drops suddenly quiet and closes slower, marked Piu Lento [JR3]. Rule for our cues: fanfare of 2
   to 4 bars, march of 8 to 16, quiet 2, slow close 2.
2. **Horn fifths as a texture, on three voices.** Published: the introduction is built on exchanges
   between horns and trumpets in horn fifths, the traditional pair of hidden fifths that valveless
   brass forced on composers [JR3, JR4]. Sugiyama's own account of the chip: a real professional
   should be able to write with three voices, "in the opening theme I hear horns very clearly", and
   he sang three part choir with his parents, which is the same as the three channel PSG sound chip
   [JR2]. Rule: with three voices available, write the upper two as a horn pair moving in sixths and
   fifths and let the third voice be the bass. Do not try to state a four part chord.
3. **Classical grammar, not game grammar.** Published in his words: game music had been
   "overwhelmingly game-like", an RPG is "really a kind of drama", so he wrote it as drama music
   [JR1]. The consequence is phrase structure borrowed from the common practice period: antecedent
   and consequent, a full cadence at the end of every 4 or 8 bars, and a modulation to the dominant
   or the relative key for the middle section [inference from JR1, JR3].
4. **The overture was written in minutes.** Published: he wrote the theme in five minutes and
   explained it as "five minutes, but you could also say it took 55 years" [JR6, JR5]. The useful
   fact is the method, not the speed: a lifetime of television and orchestral writing, then a
   compact idea. His own test for a theme was whether a listener could hear it for hours on loop
   without tiring, which he answered with Beethoven and Mozart [JR7].
5. **A fixed ritual across sequels.** Published: every Dragon Quest entry he scored carries a nearly
   identical upbeat Overture, and he wrote more than 500 pieces across 35 years [JR8]. Rule: one
   short, unchangeable identity piece per game, reused with the instrumentation upgraded, never re
   written.
6. **Fast, busy harmony under a simple tune.** Published secondary analysis: a Dragon Quest VI cue is
   logged at 132 bpm in 4/4 [JR9, crowd sourced, treat as a yardstick]. Combined with the classical
   cadence habit, the deliverable rule is [inference]: chord rhythm of one change per beat to one per
   two beats, melody of mostly quarters and eighths, and a bass that walks in step motion.

### 2.3 Suzuki and Tanaka, Mother / EarthBound Beginnings

1. **Repetition as melody.** Measured: 16.2 percent of melody intervals are zero, three times
   Uematsu's 6.0 percent. The most common melodic gesture in the corpus is a repeated note
   [measured]. Rule: write repeated notes deliberately, on beats, as the tune's pulse.
2. **Step, then step, then step.** Measured: 45.6 percent of motion is a single or double step,
   repeated notes add another 16.2, range median is 22.5 semitones, and wide leaps over 19 semitones
   are 0.58 percent, a quarter of Uematsu's rate [measured]. Rule: no leap larger than a fourth in a
   Mother style cue, and no more than one octave of range in the singable theme [S11].
3. **Major by default, with a strange flat side.** Measured: 29 major against 11 minor, and the
   tonic histogram is unusually flat, with A flat major appearing 3 times among 40 pieces, and D flat
   major, F minor, E flat major once each [measured]. Rule: most Mother cues are major; one in eight
   sits on a flat key that no other cue in the game uses, and that is the "strange" cue.
4. **Sus4 and dim7 under a plain tune.** Measured chord qualities: sus4 679 against minor 581 and
   minor 7 345, so suspended chords are the second largest category after plain major, and the
   vocabulary includes 220 diminished and 61 half diminished [measured, estimator caveat applies].
   Rule: keep the melody diatonic and put the oddity in the accompaniment, on a weak beat.
5. **Genre mixing is the style.** Published: Itoi credits Suzuki and Tanaka with a broad,
   "disorderly" spread of styles, and says EarthBound carried more jazzy pieces than Mother, with
   vibrato or string bending appearing in a game soundtrack for the first time [S9]. Rule: each
   location gets its own genre, and the only thing shared across locations is the melodic language.
6. **One figure, one instrument, one place.** Published: the NES could play three notes at once and
   Suzuki has said the limit shaped what he could produce [S9]; the brief for the Eight Melodies
   piece was a song anyone could hum and a child could play with one finger [S11]. Measured: median
   3 voices, melody 4.66 notes per bar, bass notes twice as long as Uematsu's [measured].

### 2.4 Crystalis, as a comparator

- Published: composer Yoko Osaka (credited as Yoko O. in some databases), the game released 13 April
  1990 in Japan as God Slayer and that July in North America as Crystalis, and the NES original is
  praised for "one of the best soundtracks from the NES era" in a 2018 era re-review [JR10, JR11].
- Honest limit: there is no measured corpus for this score and no published bar level analysis that
  I could find in the time available, so it contributes no numeric rules here. Its use in this file
  is as a reminder that the action RPG branch of the genre (Konami and SNK lineage) leans on
  atmospheric, riff heavy field cues rather than the march and overture frame [inference].
- Do not build recipes on Crystalis until a source with numbers exists. Rule recorded in section 12.

## 3. How the hook works in a JRPG cue

The JRPG adds one thing to the general NES hook: the hook must survive being heard for 20 to 40
minutes, in a room, while the player is thinking about something else. Four devices do that work.

1. **The rhythm cell, stated in bar 1.** The measured hook rules in MUSIC-HOOK-GRAMMAR section 1.3
   (2 to 4 bars, 8 to 18 notes, identified from 2 bars) apply unchanged. What the JRPG adds is that
   the cell must be audible under a menu blip and a sword swing, so it lives in the 500 Hz to 2 kHz
   band and is mostly on the beat [inference].
2. **The octave signature (Uematsu branch).** Measured at 4.7 percent of two-interval windows in the
   corpus being octave up and back, or down and back. This is the cheapest "this is Final Fantasy"
   marker that exists on the chip, and it costs one pitch [measured].
3. **The repeated note (Mother branch).** Measured at 16.2 percent of intervals. A tune built from
   one pitch repeated on the beat, then one step away and back, is the most hummable shape on the
   chip because the listener needs no pitch memory, only a pulse [measured, S11].
4. **The cadence as the memory anchor (Sugiyama branch).** Where the other two branches repeat a
   cell, the classical branch repeats a cadence: the same 4 bar phrase ends on the same harmony every
   time, and the middle section leaves it open. Measured support for cadence weight: chord changes
   per bar in the corpus are 3.94 (Uematsu) and 3.55 (Tanaka), so harmony moves constantly and any
   static moment is heard as a cadence [measured]. Published support: shortened piece lengths and a
   fanfare frame [JR3], and a 20 bar classical phrase shape [S28].

Hook length targets for this scope [inference, from the measured figures above]:

| Branch | Hook bars | Hook notes | Range | Repeated notes | Octave jump |
| --- | --- | --- | --- | --- | --- |
| Uematsu field or town | 4 to 8 | 20 to 40 at 5.3 notes per bar | up to 20 semitones allowed | 1 or 2 | 1 per phrase |
| Uematsu battle | 2 to 4 | 8 to 18 at 5.3 notes per bar | 12 semitones or fewer | 2 to 4 | 0, the riff is the identity |
| Sugiyama march | 4 to 8 | 16 to 24 | 12 to 16 semitones | 0 to 1 | 0 |
| Mother singable | 4 | 12 to 16 | 12 semitones | 3 to 5 | 0 |
| Victory sting | 2 | 6 to 10 | 8 semitones | 1 | 1 at the close |

## 4. Drum and bass habits

### 4.1 Where the drums are

- The JRPG splits the repertoire by cue function [inference from S53, S59, JR3, and the measured
  role medians]:
  - **Fanfare and victory**: drums are the point. A snare figure drives the march [JR3], and the
    sting ends with one crash and a held tonic.
  - **Battle**: drums carry the groove, with a noise snare on 2 and 4 and a DPCM kick on 1 and 3 as
    the default frame [S4, S62], because a battle cue is the only JRPG cue where the player is on a
    beat with the music.
  - **Town and field**: drums thin out to a hat or a soft rim, or vanish. Measured evidence for the
    thin texture: the Mother corpus assigns 28 of 114 roles to bass and 46 to inner voices, and the
    Uematsu Prelude is 2 voices with no percussion at all [measured].
  - **Dungeon**: the snare is removed. Use one noise hit per bar, or periodic mode for a metallic
    tick [S3].
- Measured support that percussion is a role decision, not a constant: median voices per piece is 3
  in both corpora, so in a 3 voice cue the noise channel is competing with the accompaniment for the
  third slot [measured].

### 4.2 The three JRPG bass types

| Type | What it is | Where it belongs | Number |
| --- | --- | --- | --- |
| Driving eighths | one root per eighth, no rests, on the triangle | battle, boss, tense field | 0.36 beats per note median in Uematsu [measured] |
| Walking | quarter note line, step or small leap, approach note into each new chord | town, march, Sugiyama cadence | 1 note per beat, 0.45 to 0.5 beats per note [inference] |
| Pedal or slow root | one pitch per bar or two, low, triangle held | Mother singable cues, dungeon, sad | 0.45 beats per note median in Tanaka [measured], low median pitch MIDI 44 [measured] |

Rule [inference]: name the bass type before writing the melody, because the measured recognition
literature gives bass alone 54.7 percent and drums alone 60.7 percent of recognition [S50], so the
bass is not accompaniment, it is half the hook.

## 5. Harmony, and the dissonance each branch tolerates

Measured chord vocabulary in the two corpora (counts, estimator caveat in section 0):

| Quality | Uematsu | share of chord changes | Tanaka | share |
| --- | --- | --- | --- | --- |
| major | 1484 | 21.4 percent | 836 | 26.8 percent |
| minor | 1017 | 14.7 percent | 581 | 18.6 percent |
| minor 7 | 954 | 13.8 percent | 345 | 11.1 percent |
| sus4 | 848 | 12.2 percent | 679 | 21.8 percent |
| major 7 | 730 | 10.5 percent | 210 | 6.7 percent |
| dominant 7 | 675 | 9.7 percent | 138 | 4.4 percent |
| half diminished | 482 | 7.0 percent | 61 | 2.0 percent |
| diminished | 418 | 6.0 percent | 220 | 7.1 percent |
| diminished 7 | 166 | 2.4 percent | 5 | 0.2 percent |
| augmented | 98 | 1.4 percent | 9 | 0.3 percent |
| sus2 | 63 | 0.9 percent | 33 | 1.1 percent |

The counts sum exactly to the recorded chord beat totals, 6935 for Uematsu and 3117 for Tanaka, which
is the check that nothing is missing from the table.

Readings [inference]:

1. **Uematsu tolerates functional tension: dominant 7 at 9.7 percent, half diminished at 7.0 percent,
   diminished 7 at 2.4 percent.** That is the battle and boss vocabulary. Published support: chord
   complexity 94 for the FF I battle theme against a database average of 50 [S53].
2. **Tanaka tolerates colour without function: sus4 at 21.8 percent (more than one chord change in
   five) and diminished 7 at 0.2 percent.** Suspension is the Mother sound, and hard tension is rare.
   This is the harmony behind "the strange and the playful": a plain major triad with the fourth held
   over it sounds unresolved in a friendly way, and it costs nothing on a chip that cannot voice four
   notes.
3. **Both keep the tonic-heavy floor.** The single most common chord is the tonic in both corpora
   (4.22 percent of Uematsu changes, 7.48 percent of Tanaka changes), and the most common two-chord
   move in both is a chord repeated (I to I, vi to vi), which is what makes a 4 bar loop survive
   [measured].
4. **Borrowed chords are cheap identity.** Measured in the Uematsu corpus: flat VI 103, flat VII 86,
   minor iv 68, and even a flat VI major 4/2 at 69 [measured]. Published parallel: the Kirby reading
   of a major to parallel minor second section [S64], and the flat seven chord as the marker of the
   Castlevania 16 bar loop [S61]. Rule: one borrowed chord per 8 bars, in the same place every loop.
5. **Key changes.** Published: the Kid Icarus Underworld cue scores 88 on chord progression novelty
   against 50 average, on a 6/8 frame [S55]; Sugiyama's own ritual is the same Overture with the
   orchestration upgraded [JR8]. Rule [inference]: a JRPG cue changes mode or key at the section
   boundary (bar 9 or 17), never inside a phrase, and never more than twice in a loop.

What each branch must avoid [inference from the counts above]:

- Uematsu style: no sus4 as a resting chord, because his sus4 figure is a side effect of the delayed
  second voice, not a harmonic destination.
- Sugiyama style: no diminished 7 shock chords under a march; his tension is secondary dominant
  based, and an augmented chord in a march reads as a mistake.
- Mother style: no functional dominant 7 cadence in the singable theme; the tune must be able to
  stop anywhere.

## 6. Form and loop lengths

Measured cue lengths from the two corpora (bar counts as transcribed, tempo normalised):

| Game | Typical length | Longest | Shortest |
| --- | --- | --- | --- |
| FF I | 10 to 20 bars (Town 11, Dungeon 12, Castle Cornelia 10, Battle 23, End Theme 128) | 128 | 2 (Fanfare) |
| FF II | 14 to 24 bars (Town 24, Battle Theme 1 at 21, Main Theme 19) | 24 | 3 (Revival) |
| FF III | 9 to 28 bars (Way to the Top 10, Salonia 23, Boundless Ocean 28) | 28 | 2 (Item Get) |
| Mother | 11 to 40 bars (Shop 13, Cave 23, Pollyanna 27, Magicant 37, Cemetery 40) | 101 (staff roll) | 1 (Victory, Giegue's Cry) |

Readings [inference]:

1. The working loop is 16 bars, with 8 and 24 both common [measured above, plus S61 and S52]. The
   48 bar loop in our own title theme is longer than anything measured here, so it must be built as
   three 16 bar sections, not one long idea.
2. Stings are a separate form class. They run 1 to 3 bars, never loop, and end on a held tonic
   [measured]. A victory is the only sting that runs 6 to 8 bars, and it is the only one with a
   cadence in the middle [measured].
3. The Mother corpus is measurably longer per cue, with a median of 20 bars, because a Mother cue is
   a small suite of a place rather than one march. If we imitate Mother, plan two 8 bar sections
   rather than one 16 bar section [measured, inference].
4. Published anchor for the two-section shape: Green Greens runs two sections, C major then C minor
   [S64]; the Overture runs fanfare, march, quiet, slow close [JR3]; Final Fantasy II's main piece
   is described as a Baroque shape building to a fanfare [S7].

## 7. Tempo ranges

All published, because the corpus is normalised to 120 bpm (section 0):

| Cue type | Tempo | Source |
| --- | --- | --- |
| FF I Prelude (arpeggio cue) | 100 bpm | [S54] |
| FF VII Victory Fanfare (same fanfare lineage) | 107 bpm, 3/4 | [JR12] |
| Dragon Quest VI cue, mid tempo | 132 bpm, 4/4 | [JR9] |
| FF I Battle | 150 bpm | [S53] |
| Kid Icarus Underworld (compound metre cue) | 152 bpm, 6/8 | [S55] |
| Mega Man 2 Dr Wily Stage 1 (upper bound for the era) | 180 bpm | [S51] |

Rules [inference]:

1. A JRPG field or town cue sits at 100 to 132 bpm. Below 100 the loop sags, above 140 the town
   feels like a chase.
2. A battle cue sits at 140 to 160 bpm, and the eighth note bass at 150 bpm is 0.2 s per eighth,
   which is the fastest a player can still tap.
3. A fanfare sits at 100 to 110 bpm in 3/4 or in a march 4/4, because a fanfare is a gesture and the
   listener has to hear the harmony, not the speed.
4. Compound metre is a tempo trick as much as a rhythmic one: a 6/8 at 152 bpm reads as fast because
   of beat division, not because of tempo [S55].

## 8. Metre: 3/4 and 6/8 in a genre that defaults to 4/4

The measured corpus contains no compound or triple metre at all, and that is an artefact of the
transcription format, not a fact about the music (section 0). Published evidence does give us the
metres:

- **3/4**: the Final Fantasy victory fanfare lineage is 3/4 at 107 bpm with the flat seven as its most
  used chord and a chord complexity of 100 [JR12]. Rule: a 3/4 waltz cue is the "elegant or solemn"
  register in this genre, and a waltz bass is root on 1, chord on 2 and 3, which the triangle plus one
  pulse can play as three attacks per bar [inference, and our own title theme already does it, S16].
- **6/8**: the Kid Icarus Underworld cue is 6/8 at 152 bpm with progression novelty 88 [S55]. Rule:
  6/8 makes a cue feel like travel or unease, and the measured way to write it on the chip is two
  groups of three eighths with the bass on 1 and 4 only, leaving the melody to skip [inference].
- **March 4/4**: the Dragon Quest Overture march section, driven by a snare rhythm [JR3].
- Practical conversion [inference]: at 150 bpm a 3/4 bar is 1.2 s and a 6/8 bar is 1.2 s; a 4 bar
  phrase in either is 4.8 s, which lands inside the 5 s recognition window from [S45].

## 9. Instrument assignment on the 2A03 and VRC6

Assignments below are the ones the evidence supports, plus the chip constraint that forces them
[S1, S2, S3, S4, S5, S6, S62, S63].

| Voice | JRPG role | Why | Duty or setting |
| --- | --- | --- | --- |
| pulse1 | lead melody | 12.5 or 25 percent duty separates the lead from the accompaniment [S62] | duty 0.125 for battle and fast field, 0.25 for town and sad |
| pulse2 | delayed doubling, horn pair, or countermelody | the shimmer device [S8], the horn fifth texture [JR3, JR4] | same duty as lead when doubling, 0.5 when playing a horn pair |
| triangle | bass, always | fixed volume, one octave below the pulses [S2] | one root per eighth for battle, one per beat for march |
| noise | snare, hat, march snare, metallic tick | 15 rates plus periodic mode [S3] | mid rate for snare, high short for hat, periodic for metal |
| DPCM | kick only, or a spoken or breath sample | 1 bit, 15 rates, short samples [S4] | one sample per bar maximum |
| vrc6_p1 | second lead, echo of the lead, or third harmony voice | 8 duty steps give the reedy tone the 2A03 lacks [S6] | duty 6 to 8 sixteenths for a horn-like tone |
| vrc6_p2 | pad, arpeggio accompaniment, or melody in a bright cue | as above | narrow duty for a thin pad |
| vrc6_saw | sustained pad, or the oom pah in a 3/4 cue | accumulator rate above 42 distorts [S6] | rate 30 to 40, and never on a fast line |

Assignment rules [inference]:

1. In a 3 voice cue, the triangle is the bass and the two pulses are a horn pair. This is Sugiyama's
   own description of how he heard an orchestra inside three channels [JR2].
2. In a 5 voice cue, add noise and one VRC6 pulse: the VRC6 pulse takes the countermelody or the
   delayed doubling and leaves pulse2 free for the horn pair [S5, S6].
3. Never give the VRC6 sawtooth a line with sixteenths at battle tempo; the accumulator cannot reset
   fast enough and it reads as buzz [S6].
4. Give the lead the 12.5 percent duty in battle and the 25 percent in town. The measurement behind
   this is the duty timbre table in [S62], and the pairing rule is recipe CHIP-01 in
   MUSIC-STYLE-BIBLE.md section 5: a thin lead against a 50 percent accompaniment, so the two voices
   stay separable at the mixer.

## 10. Human touches that fit this genre

From MUSIC-HOOK-GRAMMAR section 7.2, narrowed to what a JRPG cue actually needs, and the one JRPG
specific addition:

| Gesture | JRPG use | Legal route |
| --- | --- | --- |
| Delayed vibrato | the sad character cue, the Mother singable theme on its last phrase | start the wobble 2 to 4 frames after the attack, write the low period byte only [S63] |
| Detuned pair | the Uematsu town and character cue | cents 8 flat, 18 ms late, volume 70 percent [S8] |
| Grace note on a repeated note | the Mother branch, where repeated notes are 16.2 percent of motion | 1 frame upper neighbour on the second statement only [measured, then inference] |
| Breath rest at a phrase end | every branch, one eighth on the melody voice | silence the lead for one eighth in the last bar of each 4 bar phrase |
| Duty change at the phrase boundary | town to field contrast, march to fanfare | change duty on the downbeat, never mid note [S62] |
| One bar drum fill before a section | the march and battle cues, which have drums to fill with | noise figure ending exactly on the downbeat |
| Cadential ritardando | the Sugiyama march close, the Piu Lento ending [JR3] | drop the last 2 beats by one frame each, on every voice except the bass |
| A wrong-sounding right note | the Mother strange cue | one sus4 held over the tonic for a full bar, no resolution [measured sus4 share 21.8 percent] |

Anti human list for this genre [inference]:

1. A victory sting that runs to 8 bars with a drum fill at bar 5: it should be over by then.
2. A battle cue with a wide, singable melody. The measured FF battle range is 8 semitones [S53].
3. A town cue with a driving eighth bass. That is the battle bass.
4. A 16 bar loop whose second half is the first half transposed with no change of duty, register or
   voice count. Measured repetition preference is varied over literal at 2.7 to 1 [S49].
5. A march without a snare. The snare is what makes it a march [JR3].
6. Any cadence in a Mother singable theme. The tune must be able to stop anywhere [S11].

## 11. Ten listening notes

Instructions: listen once for the thing named, then again for where the loop seam is. Bar numbers are
from the corpus transcription (tempo normalised to 120, so a bar is 2 s there) or from the published
analysis where one exists. No melody is written out here on purpose.

1. **Final Fantasy I, Prelude (B flat major, 19 bars, 2 voices)** [S54, measured]. Bars 1 to 4: the
   arpeggio figure and its delayed twin. Listen for whether the second pulse is quieter and later, and
   count how many notes it takes before the two voices blur into one shimmer. Bars 17 to 19: the
   seam, which is where the figure has to point back to bar 1 with no cadence.
2. **Final Fantasy I, Battle (G minor, 150 bpm, 23 bars)** [S53, measured]. Bars 1 to 2: the narrow
   line against the bass. Track the melody's total travel: it stays inside 8 semitones across the
   whole analysed section, so every time you think it will leap, it does not. Bars 9 to 12: the
   harmony changes under a melody that barely moves, which is the whole trick of the cue.
3. **Final Fantasy I, Victory (E flat major, 8 bars, and the 2 bar Fanfare in G, the 3 bar Save
   Jingle in A)** [measured]. Listen to the length difference: the event stings end before you can
   predict them. Then listen to bar 8 of Victory and hear that it is a full cadence, not a loop
   point.
4. **Final Fantasy II, Battle Theme 1 (A minor, 21 bars)** [measured]. Compare with note 2: same
   function, two more bars, and a different balance between the two pulses. Listen for which pulse
   carries the riff. The other pulse answers, and the answer is never a doubling.
5. **Final Fantasy III, Elia the Maiden of Water (A minor, 24 bars)** [S7, measured]. Bars 1 to 4:
   arpeggio below, melody above, nothing else. Listen for how much space a 3 voice cue can leave and
   still feel complete, then listen to the register gap between the arpeggio and the melody.
6. **Final Fantasy III, Town of Water (G major, 28 bars)** [measured]. Warmth mechanism: duty, bass
   speed, and the length of the melody notes. Count the number of notes in bars 1 to 8 and compare
   with the battle cue; the town has more space per note.
7. **Dragon Quest, Overture** [JR3, JR4, JR6]. Listen in the four published sections: Maestoso
   fanfare, march, sudden quiet passage, Piu Lento close. In the fanfare, listen for the horn and
   trumpet pair moving in horn fifths and count how few voices are actually sounding. In the march,
   listen to the snare as the thing that makes the section a march rather than a tune.
8. **Mother, Pollyanna (D major, 27 bars)** [measured, S9]. Bars 1 to 4: the repeated notes, one
   melody note in six across the whole corpus is a repeat of the previous one. Hum it after one
   listen and notice that you are humming a rhythm as much as a tune. Then listen for where the line
   steps rather than repeats, which is the only place it can sound like a melody.
9. **Mother, Eight Melodies (D major, 13 bars)** [S11, measured]. The one finger test: the whole
   range stays inside an octave and no leap is larger than a fourth. Listen for the moment the tune
   would need a chord to make sense and hear that it does not get one.
10. **Mother, Level Up (E flat major, 3 bars) and Victory (C major, 1 bar)** [measured]. Two stings
    shorter than a phrase. Listen to how a single bar can carry a full resolution, and note that the
    Level Up sting is in a flat major key a third away from the C major battle cue, the same
    third-away trick as the Final Fantasy pairing in section 2.1.

Not one of the ten, kept for the metre work: **Kid Icarus, Underworld (152 bpm, 6/8, 22 semitones,
chord progression novelty 88)** [S55]. Count the two groups of three and hear the bass land only on 1
and 4. This is the model for our 6/8 cues.

## 12. What to avoid, and the limits of this file

1. Do not build anything on Crystalis until a source with numbers exists (section 2.4). The entry is
   here because the card names it, and it is a comparator, not a recipe base.
2. Do not quote the corpus tempo or metre figures. Both corpora are normalised to 120 bpm and 4/4.
3. Do not treat the chord quality counts as written harmony. They come from an automatic estimator on
   monophonic transcriptions, and a delayed second voice inflates sus4 and sixth categories.
4. Do not reconstruct a theme from any row in this file. The bar counts and ranges describe shape, not
   pitch.
5. Do not import the Sugiyama ritual as a copy of the Overture. What transfers is the form (fanfare,
   march, quiet, slow close), the horn fifth texture, and the cadence placement.
6. The corpus covers 104 Uematsu pieces and 40 Tanaka or Suzuki pieces, which is the whole NES output
   of both composers in scope, minus Dragon Quest. Treat the ratios as robust and the individual
   counts as sample dependent.
7. Nothing here was measured from an audio recording, downloaded, ripped or sampled. The transcriptions
   used are the public NES-MDB derived corpus already on disk, and the published analyses are cited by
   link and date.

## 13. Sources

Reused ids (full rows in MUSIC-STYLE-BIBLE.md section 6 and MUSIC-HOOK-GRAMMAR.md section 10):
S1 to S6 NESdev APU, period table, noise, DMC, VRC6, VRC6 audio; S7 The Line of Best Fit on Uematsu;
S8 Red Bull Music Academy Daily Uematsu interview; S9 Wikipedia Music of the Mother series; S11 Itoi
interview on the one finger song; S16 our own score.yaml; S28 Wikipedia Period; S33 CHIP-01 in the
bible recipe table; S45 BBC Hooked on Music; S49 Temperley 2024; S50 Bechtold, Curry and Witek 2024;
S51 Mega Man 2 Dr Wily Stage 1 theorytab; S52 SMB3 Overworld theorytab; S53 Final Fantasy Battle
theorytab; S54 Final Fantasy Prelude theorytab; S55 Kid Icarus Underworld theorytab; S61 Eurogamer on
Vampire Killer; S62 chiptune recreation guide; S63 NESdev APU basics; S64 WiKirby Green Greens.

New rows, all read on 2026-10-21:

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| JR1 | Shmuplations, Koichi Sugiyama 1988 developer interview (translated from BEEP) | https://shmuplations.com/sugiyama/ | Game music was "overwhelmingly game-like", he wanted drama music because "RPGs are really a kind of drama"; he makes a demo tape and a music programmer sequences it; "a boring melody with better sound quality is still a boring melody" |
| JR2 | Same page, 2003 interview section | https://shmuplations.com/sugiyama/ | "A real pro should be able to make music even with three voices only", "in the opening theme I hear horns very clearly", he sang three part choir, which he compares to the three channel Famicom PSG |
| JR3 | SLEEP FREAKS DTM, "Dragon Quest Overture: Orchestration and DAW Production Explained" (Overture XI analysis, published 2022) | https://sleepfreaks-dtm.com/en/chord-analize/dq-opening/ | Three sections: Maestoso fanfare, march main theme with a lively snare rhythm, sudden quiet passage then Piu Lento close; horn fifths between horns and trumpets in the introduction; analysis of the orchestral roles |
| JR4 | Wikipedia, "Consecutive fifths", horn fifths section | https://en.wikipedia.org/wiki/Consecutive_fifths | Horn fifths arise from the valveless brass harmonic series, come in pairs, and are the acceptable case of hidden fifths where the top voice moves by step |
| JR5 | SoraNews24, "The unforgettable Dragon Quest theme music took an amazingly short time to write, composer says" (2020-10-31) | https://soranews24.com/2020/10/31/the-unforgettable-dragon-quest-theme-music-took-an-amazingly-short-time-to-write-composer-says | Sugiyama: "I wrote the Dragon Quest theme in five minutes", and "it took five minutes, but you could also say it took 55 years" |
| JR6 | sackchief, "The Music of Dragon Quest, Koichi Sugiyama Retrospective" (video essay, transcript) | https://youtube.com/watch?v=6HXA-x3LazM | One week to score Dragon Quest I, eight songs, two days to convert sheet music to game data; the Overture is built on horn fifths; "the Famicom could only make three sounds at a time"; dissonance used in battle cues |
| JR7 | Enjoy Game Japan Museum, Koichi Sugiyama creator page | https://museum.enjoygamejapan.online/en/creators/koichi-sugiyama | His test for a theme was whether it could be heard on loop for hours without tiring, answered with Beethoven and Mozart; the whole Dragon Quest I score delivered within a week |
| JR8 | Wikipedia, Koichi Sugiyama (Sugiyama Kobo) | https://en.wikipedia.org/wiki/Koichi_Sugiyama | Every entry he scored carries a nearly identical upbeat Overture; more than 500 pieces across 35 years |
| JR9 | Hooktheory theorytab, Dragon Quest VI Pegasus | http://devhookpad.hooktheory.com/theorytab/view/koichi-sugiyama/dragon-quest-vi---pegasus | 132 bpm, 4/4 (crowd sourced analysis, used as a yardstick only) |
| JR10 | Wikipedia, Crystalis (God Slayer) | https://en.wikipedia.org/wiki/God_Slayer | Composer Yoko Osaka; Japanese release 13 April 1990 as God Slayer, North American release as Crystalis in July; praise for the soundtrack in the SNK 40th Anniversary Collection re-review |
| JR11 | Retrocean, Crystalis (NES) history page | https://retrocean.com/nes/crystalis | Music by Yoko Osaka, director and producer Kazuto Kawano, release dates |
| JR12 | Hooktheory theorytab, Final Fantasy VII Victory Fanfare | http://hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy-vii---victory-fanfare | 107 bpm, 3/4, flat seven as the most used chord, chord complexity 100 (crowd sourced, used for the 3/4 fanfare metre claim only) |
| JR13 | Video Game Music Preservation Foundation wiki, Koichi Sugiyama | http://vgmpf.com/Wiki?title=Koichi_Sugiyama | Sugiyama wrote sheet music and Enix or Chunsoft programmers arranged it for the NES Ricoh 2A03 in assembly, naming Masumi Takimoto, Takenori Yamamori and Yasuhiro Taguchi |
| JR14 | RPGFan, Final Fantasy XIV battle tracks review (archived 2015) | https://web.archive.org/web/20150329191441/http:/www.rpgfan.com/soundtracks/ff14battle | Fan criticism observing that Uematsu's battle themes tend to common time or 6/8, with 7/8 as the exception (treated as reception, not fact) |

Data files read for this study: `D:\Musikage-Corpus\style-pp\stats\nobuo_uematsu.json` and
`D:\Musikage-Corpus\style-pp\stats\hirokazu_tanaka.json`, both generated 2026-10-21T19:49:50.

Machine readable companion: `data/recipes/jrpg.json`, 30 recipes with parameters, forbidden
combinations and the same source ids.
