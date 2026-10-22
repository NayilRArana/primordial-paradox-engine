# Konami gothic rock and metal on the 2A03 and the VRC6

Card t_b5632857 (STUDY-KONAMI), research-assistant, written 2026-10-21. Scope name `konami`.
Companion files: `knowledge/MUSIC-HOOK-GRAMMAR.md`, `knowledge/MUSIC-STYLE-BIBLE.md`,
`knowledge/MUSIC-DRUMS.md`, and the executable recipes in `data/recipes/konami.json`.

Reference rule (PLAN-V2 section 0): the games were studied from published interviews, credit
records, wiki hardware documentation, theory references and measured corpus statistics. Nothing was
downloaded, ripped, sampled or decompiled. No melody is written out anywhere in this file: every
musical statement is a shape, a scale degree, an interval or a count.

Tagging. Every claim ends with a source id in square brackets, for example [K15]. The table in
section 13 has the link and the read date for each id. `[inference]` marks my own operationalisation
of a source, written so the arranger has a number to hit.

---

## 1. Who wrote what, and why it matters to the recipes

- Castlevania (Akumajou Dracula, Famicom Disk System, 1986) music is by Kinuyo Yamashita and Satoe
  Terashima, and the two composed separately rather than collaborating: Terashima wrote stage 1,
  stage 2, stage 6 and the ending; Yamashita wrote stage 3, stage 4, stage 5, the boss theme, and
  both Dracula themes [K1]. In a 2026 interview Yamashita restated that the composers were Terashima
  and herself, that Hidenori Maezawa was not involved, and that she was unsure who wrote the sound
  program [K2, K4].
- Yamashita's account of method: she could not use a sequencer, so she played each piece on a
  portable keyboard for the sound team leader (Sakamoto), and only then entered it as Famicom data;
  she says that without piano ability she could not have composed at all [K2].
- Her stated aim was music for "the dynamism with which the player moves and the gothic images of
  the background", and she says the rock approach "came naturally", piece by piece, with no initial
  plan [K1].
- Castlevania III / Akumajou Densetsu (1989) is credited to Hidenori Maezawa, Jun Funahashi and
  Yukie Morimoto [K5]. The Japanese cartridge carries the Konami VRC6, which adds two pulse channels
  with finer duty control and one sawtooth, taking the soundtrack from five voices to eight [K6, K7].
  The North American release dropped the chip and Yoshinori Sasaki reduced the same compositions to
  the five stock channels [K7].
- Contra (NES, 1988): the arcade themes are Kazuki Muraoka's; the NES score was ported and rebuilt by
  Hidenori Maezawa and Kiyohiro Sada, who also wrote the new Introduction theme heard in the Japanese
  release [K8, K10]. Super C (NES) sound design is credited to Maezawa [K9].
- Gradius (1985) is Miki Higashino: thirteen pieces, buoyant melodic stage themes, but a boss theme
  that deliberately uses odd metres, rapid arpeggios and the Lydian mode to picture outer space, with
  Kraftwerk as an influence [K11].
- Rush'n Attack (Green Beret) and The Adventures of Bayou Billy sit with Kiyohiro Sada, and Bayou
  Billy is a four person job with Tsutomu Ogura, Jun Funahashi, Sada and Maezawa, including two
  versions of the sound driver [K12, K13].
- Why this section exists in a study of style: the Konami house sound of this period is not one
  composer's voice, it is a shared grammar of driving eighth and gallop bass, minor key riffing,
  arpeggiated harmony and a hard, short drum kit, executed by people who all played keyboards and all
  wrote inside the same five or eight channel box [inference from K1, K5, K8, K11].

---

## 2. The measured facts: what the corpus says

Source: the corpus statistics file `D:\Musikage-Corpus\style-pp\stats\nes_rock_metal.json`,
generated 2026-10-21 from 86 NES-MDB pieces, of which 16 are Castlevania and 13 are Contra [K22].
This is the one place where the numbers are ours rather than quoted.

| Measure | Value | What it means for us |
| --- | --- | --- |
| Pieces in the measurement | 86 (Castlevania 16, Contra 13) | Small but the two scope games are well represented |
| Castlevania keys | 13 of 16 minor; D minor 4, C minor 4, G minor 2 | Minor is the default, and the favourite tonics are D, C and G minor |
| Contra keys | 10 of 13 minor; A minor 4, C minor 2 | A minor and C minor lead |
| Castlevania median length | 15 bars, longest 45 (Heart of Fire) | Stage themes are 15 to 45 bars, not 60 bar epics |
| Contra median length | 17 bars, longest 42 | Same order of magnitude |
| Tempo in the corpus | every file reads 120 bpm | The archive normalises tempo, so no tempo conclusion is drawn from it [K22] |
| Meter in the corpus | 4/4 in all 86 pieces | Straight four is the default; the odd metre exceptions are in Gradius, not here [K11] |
| Melody intervals | 14,747 total; unison 16.5 percent, minor second 10.2 percent, major second 9.6 percent down plus 7.8 percent up | The melodic surface is stepwise and neighbour-note heavy, not arpeggio heavy |
| Step to leap ratio | 51.6 percent steps, 48.4 percent leaps, 8.3 percent leaps wider than 19 semitones | Half the moves are leaps; that is a melodic style with real jumps in it |
| Most common 2 and 3 interval shapes | -1 +1, +1 -1, -2 +2, 0 0 0, -1 +1 -1, +2 -2 +2 | Oscillation around a pitch is the micro shape of the style |
| Melody note duration | 76.0 percent of melody notes are one sixteenth; 12.5 percent are two sixteenths; 5.1 percent are a dotted eighth | The melody is a sixteenth-note machine with occasional long notes |
| Harmony density | 3.78 chord changes per bar, 249 distinct labels | Roughly four chords a bar: harmony moves constantly |
| Chord qualities | sus4 1033, maj 953, min7 876, min 871, maj7 522, dim 455, dom7 408, half-dim7 312, aug 131, dim7 42 | Sus4 and diminished are as common as plain major and minor; that is the gothic colour |
| Most common transitions | V sus4 to i (23), i to i7 (19), i6/4 to V sus4 (19) | Second inversion to a sus4 dominant to the tonic is the loop engine |
| Phrase length | median 10 bars, mean 12.77 bars, 1.36 phrases per piece | Pieces are one or two long phrases, cut off by the loop |
| Cadences | tonic prolongation 22.2 percent, half cadence 15.4 percent, authentic only 3.4 percent | Loops end open or sustained, not with a decisive full stop |
| Pitch by role | melody median 71 (B4), inner voice 61.5 (near C#4), bass 46 (Bb2) | Melody sits about two octaves above the bass; the inner voice is one octave up from the bass |

Two ways the corpus can mislead, stated so nobody quotes it carelessly [inference]:
1. The motif repetition figure (4.3 percent of one-bar windows repeat exactly) is low because the
   corpus comes from converted MIDI with small timing deviations; exact-token matching undercounts
   repeats. Do not read it as "Konami music has no repetition".
2. Phrase counts are low because many corpus files are truncated loops, so the 1.36 phrases per piece
   is the archive's editing, not the composers' form.

Quoted measurements from published theory tabs, which do carry real tempo:

| Track | Key | Tempo | Meter | Melody range | Complexity readings |
| --- | --- | --- | --- | --- | --- |
| Castlevania, Vampire Killer | D minor | 129 bpm | 4/4 | A2 to D6, 41 semitones | melodic complexity 96, chord complexity 65, chord-melody tension 58, progression novelty 41, most used chord i [K15] |
| Castlevania III, Mad Forest | D minor | 129 bpm | 4/4 | C3 to A6, 45 semitones | melodic complexity 95, chord complexity 96, chord-melody tension 20, progression novelty 94, most used chord V [K16] |

Two facts jump out of that table. Both tracks sit at 129 bpm, and both are D minor, so the two ends of
the trilogy share a tempo band and a tonic [K15, K16]. And the two differ exactly where the style
differs: Vampire Killer is comparatively simple in harmony but tense between melody and chord
(tension 58); Mad Forest is harmonically rich and comfortable between melody and chord (tension 20)
because the melody sits on chord tones while the chords do the chromatic work [K16]. The recipe set
below contains one path for each.

---

## 3. Signature moves, with numbers

### 3.1 The gallop

- The gallop is one eighth note followed by two sixteenths inside a single beat: counted "1 _ and a",
  a 2:1:1 split of the beat in sixteenths, not a triplet [K17, K18]. The reverse gallop is two
  sixteenths then an eighth, counted "1 e and _", a 1:1:2 split [K17].
- The style family that made it famous runs it at mid to fast tempo, 120 to 180 bpm, with the drummer
  and bassist locked to the same cell [K18, K25].
- On the NES the gallop has to be split across channels because one channel plays one note: pulse1
  takes the riff, the triangle doubles the long note of each cell, and the noise channel marks the
  two short notes with hats [inference from K14, K17].
- Practical rule [inference]: at 129 bpm (the two measured tracks, [K15, K16]) a beat is 465 ms, so
  the long note is 232 ms and each short note 116 ms; below about 110 bpm the short notes blur into
  the long one and the gallop stops reading as a gallop.

### 3.2 Driving eighths

- The corpus melody is 76 percent sixteenth notes [K22], so the surface density is already high. The
  bass does the opposite job: steady eighths on the root, one pitch per eighth, with the guitar riff
  above it [inference from K22's 3.78 changes per bar and the Vampire Killer "punchy syncopation"
  reading at 0.62 beats per note].

### 3.3 Harmonic minor and the raised seventh

- The harmonic minor scale is the natural minor with a raised seventh, and that raise creates the
  augmented second between the sixth and seventh degrees, for example F to G sharp in A minor [K20].
- That augmented second is the single most useful melodic interval in this style: it sounds exotic and
  old, and it is one semitone short of the tritone, which is why it reads as gothic rather than
  merely sad [inference from K20, K21].
- Operationally [inference]: allow the augmented second in the melody once per two bars, on the way up
  to the tonic; allow it more often in the boss theme; never put it in a title theme hook, where it
  competes with the memory of the contour.

### 3.4 Phrygian and Phrygian dominant

- The Phrygian dominant scale is the fifth mode of harmonic minor: 1, flat 2, 3, 4, 5, flat 6, flat 7,
  with the step pattern half, augmented second, half, whole, half, whole, whole [K19].
- Its identifying move is the flat second, one semitone above the tonic, which is the interval that
  makes a gothic or "vampire" cue sound like it comes from somewhere older than the key [inference
  from K19].
- Operationally [inference]: use flat 2 as a melodic neighbour or as a whole chord (a major triad a
  semitone above the tonic) once per four bars in boss and crypt cues, and never in the same bar as
  the raised seventh, because the two together destroy the sense of key.

### 3.5 Tritone and diminished moves

- A tritone is six semitones, half an octave, and it is the interval that makes diminished, dominant
  and half-diminished chords push for resolution [K21].
- The measured Mad Forest progression is built almost entirely from that family: a V with a flat five,
  then a diminished ii in second inversion, then III, then IV with a mixture, then V in second
  inversion, then a Lydian flavoured V, then i. Its progression novelty score is 94 against the
  Hooktheory database, that is, almost nobody writes this [K16].
- The corpus agrees on the raw material even though it cannot name that progression: diminished
  triads appear 455 times and half diminished sevenths 312 times, against 871 plain minor triads, so
  the dark chords are not ornaments, they are a large share of the harmony [K22].
- Operational reading of that progression as a general shape rather than a quote [inference]: step the
  bass up by semitone or tone through second inversion chords, put a diminished chord at the weakest
  point of the climb, and land on a sus4 dominant before the tonic. That is one executable recipe
  (KON-06, KON-07) and it explains the most common corpus transition, V sus4 to i [K22].

### 3.6 Arpeggio heavy gothic organ

- On the 2A03 a chord exists only as a fast sequence: the arpeggio is played one note per frame at the
  60 Hz engine rate, so a three note triad repeats 20 times a second and the ear fuses it into a
  chord [K14].
- Mad Forest's chord complexity of 96 with a melody tension of only 20 says the harmony is dense while
  the melody stays consonant against it [K16]; the practical route to that combination is a melody
  that moves by step and neighbour tone inside a harmony that changes 3.78 times a bar [K16, K22].
- In the trilogy the organ is the "gothic" signal, and both the criticism and the composer's own
  account put classical organ colour and horror scoring next to the rock drive [K24, K1].

### 3.7 The VRC6 saw bass

- The VRC6 adds two pulses with eight duty steps plus a full duty mode, and one sawtooth whose volume
  is set by an accumulator rate; a rate above 42 distorts [K14].
- The three extra channels took Akumajou Densetsu from five voices to eight, and the extra voices are
  mostly used to imitate a string section rather than to add a third melody [K7].
- The sawtooth is the one voice on the chip that can carry a bass line with harmonics in it, which is
  why the Castlevania III bass sounds like a bass guitar and the Castlevania I bass sounds like a
  triangle wave [inference from K7, K14].
- Operational rule [inference]: saw bass plays the riff's root on eighths below the melody's octave,
  accumulator rate 32 to 40, with the triangle either silent or doubling at the octave down for the
  first 4 bars only; doubling the saw with the triangle for a whole cue muddies the low end because
  the two waveforms beat against each other.

### 3.8 Fast fills

- The corpus's melody durations are overwhelmingly single sixteenths [K22], so a fill that is a run of
  sixteenths is not a special event, it is the same rhythmic surface accelerating into the next
  phrase; the fill has to change pitch direction or register to be heard at all [inference].
- Mad Forest's melody spans 45 semitones, C3 to A6 [K16], and Vampire Killer's spans 41, A2 to D6
  [K15]. Both are more than three octaves, so a register jump is native to the style, not an effect.

### 3.9 Boss themes

- Higashino's Gradius boss theme deliberately abandons the buoyant stage style for odd metres and
  rapid arpeggios [K11]; the lesson transfers: the boss cue is where the rhythm is allowed to become
  irregular and the harmony is allowed to become an arpeggio wall [inference].
- Corpus evidence for the same division of labour: cadences are mostly open (half cadence 15.4
  percent, authentic only 3.4 percent) [K22], which suits a boss loop that must not feel finished
  [inference].

---

## 4. How a 4 bar riff becomes the hook

The card asks the direct question, so here is the mechanism as a sequence of steps with numbers, and
then the two worked patterns the recipes encode.

1. State a rhythmic cell of 1 to 2 bars that is 76 percent sixteenths, with exactly one long note
   [K22]. At 129 bpm one bar of 4/4 is 1.86 s, so a four bar riff is 7.4 s, which is just past the
   5 s average recognition time and inside the 2.3 to 2.6 s fastest time for the first two bars
   [K15 tempo plus the recognition figures in the hook grammar].
2. Give the cell a contour that oscillates: the top interval pairs in the corpus are -1 +1 and +1 -1
   [K22], so a neighbour-note wobble is the style's default memory shape, not a leap.
3. Put one leap of a fourth or more at the same position in every repetition, so the leap becomes the
   signature and the wobble becomes the texture [inference from K22's 48.4 percent leap share].
4. Harmonise it four chords to the bar instead of one chord to the bar, and make the bass move while
   the melody holds a pitch: Mad Forest's identity is exactly this split, high chord complexity under
   low melodic tension [K16].
5. Repeat the riff four times, change only one element on the third repetition (register, duty, or the
   last two sixteenths), then return. That is one variation per 7.4 s, which is slow enough to register
   and fast enough to prevent the loop from flattening [inference].
6. End the fourth bar on either a sus4 dominant or a half cadence rather than the tonic, because the
   corpus ends open far more often than it closes [K22].
7. The hook is the first two bars of that riff, not the whole four: what the listener hums is the
   wobble plus the leap, and the harmony underneath is what makes it feel composed [inference].

Two worked patterns, no pitches quoted, only degrees and counts:

- Pattern A, the Vampire Killer path: minor key, riff on two pulses trading register, one chord per
  beat, melody tension high against the chord (the measured tension is 58) [K15, K24]. The hook is the
  tension itself: the melody leans on notes that are not in the chord.
- Pattern B, the Mad Forest path: minor key, riff on the bass, harmony climbing in second inversion
  chords with a diminished chord as the hinge, melody sitting on chord tones (tension 20) [K16]. The
  hook is the climb, not a tune.

Both patterns sit at 129 bpm in D minor in the published analyses [K15, K16]; that is coincidence in
the source, not a rule, but it is a safe default tempo for this style [inference].

---

## 5. Drum and bass habits

Drum side, from the chip constraints and the corpus [K14, K22, plus inference]:

- Kick on the downbeat of every bar and on the "and" of 2 when the riff is a gallop, because the kick
  has to land with the long note of the cell, not with the short ones.
- Snare (mid rate noise burst) on beat 3 in 4/4, or on 2 and 4 when the cue is a run and gun like
  Contra; the corpus is straight 4/4 throughout [K22].
- Hats as eighth or sixteenth noise at a low volume, which is what makes a five channel mix sound like
  it has a full kit.
- Fills every 4 or 8 bars, two beats long, sixteenth based, and pitched: a noise sweep is not
  available, so the fill is a snare run plus a DPCM tom at the end [K14].
- No swing: the gallop is explicitly not a triplet [K17], and the corpus shows no swung subdivision
  in the melody durations [K22].

Bass side:

- Triangle on the root, eighth notes, one pitch per eighth, no octave jumps except at phrase ends,
  because the triangle has no volume control and cannot accent [K14].
- VRC6 saw when available: the riff root, eighths, with the saw's harmonics supplying the "bass
  guitar" edge [K7, K14].
- Bass pitch centre in the corpus is 46, which is Bb2 [K22]; keep the bass line between MIDI 40 and 52
  so the saw stays clean and the triangle stays audible on small speakers.
- The bass carries the riff in the Mad Forest pattern and merely the roots in the Vampire Killer
  pattern [K15, K16].

---

## 6. Harmony and the dissonance this style tolerates

- Keys: minor, with D minor, C minor, G minor (Castlevania) and A minor, C minor (Contra) as the
  measured leaders [K22]. Major cues exist (3 of 16 Castlevania pieces) and are short: stage clear,
  all clear, player miss [K22].
- Chord vocabulary, in descending measured frequency: sus4, major, minor seventh, minor, major
  seventh, diminished, dominant seventh, half diminished seventh, augmented, diminished seventh [K22].
- Progressions: the corpus's most common bigram is V sus4 to i, and the third most common shape is
  i6/4 to V sus4, both of which mean second inversion chords used as approach chords [K22]. This is
  the same device the Mad Forest tab spells out in Roman numerals [K16].
- Borrowed colour that this style tolerates: the flat five on the dominant [K16], the Neapolitan flat
  second [K19], an augmented dominant as a passing chord (131 augmented chords in the corpus) [K22],
  and the flat six major triad which appears 9 times as a bigram with its own seventh in the corpus
  [K22].
- Dissonance ceiling, operationalised [inference]: one non-diatonic chord per two bars is the norm;
  two adjacent non-diatonic chords is the boss theme exception and should resolve immediately; a
  tritone held in the melody against the bass for more than a sixteenth is a special effect, not a
  texture.
- What the style does NOT tolerate [inference from K15, K16, K22]: extended jazz voicings stacked two
  deep (the corpus has maj7 and min7 in quantity but almost always as the single colour tone of a
  triad, not as a stack), quartal harmony as a default, and modulation to a key a minor third away
  inside one loop, because a 15 to 45 bar stage theme has no room to establish two tonics [K22].

---

## 7. Form, loop lengths and tempo ranges

| Cue type | Bars | Loop | Evidence |
| --- | --- | --- | --- |
| Stage theme | 15 to 45, median 15 (Castlevania), 17 (Contra) | one long phrase, sometimes two | [K22] |
| Boss theme | 8 to 16 bars | tight loop, irregular rhythm allowed | [inference from K11, K22] |
| Title or prelude | 3 to 8 bars, often a fanfare then a loop | statement plus loop | Castlevania prologue 3 bars, Contra title 3 bars [K22] |
| Stage clear, game over, miss | 1 to 4 bars | one shot, no loop | [K22] |
| Longest measured cue | 45 bars (Castlevania, Heart of Fire), 42 (Contra, Sandinista ending) | 45 bars at 129 bpm is 83 s | [K22, K15] |

Tempo: the two published analyses of this repertoire sit at 129 bpm [K15, K16]; the gallop family
runs 120 to 180 [K18]; the corpus tempo field is normalised and must not be cited [K22]. Working
defaults [inference]: stage 126 to 132, boss 138 to 150, title 96 to 108 with a 129 bpm loop after the
fanfare, stage clear 150 to 160 and under 4 bars.

Phrase architecture that the corpus supports [K22, K23]: short reusable units, recombined and nested,
with loops layered across voices so the piece never sounds identical twice; the shared 16 bar loop
figure for Vampire Killer in the published commentary is one instance [K24]. For our arranger, a
16 bar loop built from a 4 bar riff, a 2 bar answer and a 1 bar drum link covers the whole form
vocabulary of this style.

---

## 8. Instrument assignment on the 2A03 and the VRC6

Five channel (Castlevania I and II, Contra, Gradius, Rush'n Attack, Bayou Billy) [K14]:

| Channel | Default role in this style | Alternative |
| --- | --- | --- |
| pulse1 | lead riff and melody, duty 12.5 or 25 percent | organ arpeggio top note |
| pulse2 | second guitar: parallel third or the answer phrase, duty 50 percent | delayed echo at low volume |
| triangle | bass, eighth notes, root | kick substitute with a fast pitch drop |
| noise | hats, snare, the two short notes of a gallop | snare fill |
| dpcm | kick | tom in fills, one short sample only |

Eight channel (Akumajou Densetsu) [K6, K7, K14]:

| Channel | Default role | Constraint |
| --- | --- | --- |
| pulse1 and pulse2 | as above, now free to be the organ | keep the two duties different |
| vrc6_p1 | third line: organ chord tone, countermelody, or the string pad | 8 duty steps, use 6.25 to 25 percent for strings |
| vrc6_p2 | doubling the lead in unison or an octave, or the "strings" second voice | 100 percent mode for a flat organ |
| vrc6_saw | bass with harmonics | accumulator rate 32 to 40, hard cap 42 [K14] |
| triangle | free for percussion or a low pedal | still no volume control |
| noise and dpcm | kit as before | |

The published history is explicit that the extra channels were used chiefly to imitate a string
section rather than to add a third melody [K7]; the recipes below follow that: a sustained VRC6 pad
under a 2A03 riff, not three competing tunes.

---

## 9. Human touches that read as "played"

- Vibrato on held notes only, applied through the low period byte because writing the high byte resets
  the phase and clicks [K14]. Depth 10 to 20 cents, rate about 5 Hz, starting 120 ms into the note.
- Duty change inside a long note (12.5 to 25 percent) to make the note "open up", done once per cue
  and never on the hook note [K14, inference].
- The piano-first method of the original composers is audible as writing that is playable by ten
  fingers: one melody line, chord shapes that fall under the hand, and bass lines that are scale runs
  rather than machine patterns [K1, K2]. The arranger should therefore keep at most one voice leaping
  at a time [inference].
- Small timing pushes: 10 to 20 ms early on the short notes of a gallop make it sound driven rather
  than quantised; on the 60 Hz engine that is one frame, which is the smallest unit available [K14].
- Deliberate imperfection in repetition: change one sixteenth in the third repetition of the riff, not
  the whole pattern, because exact repetition is what the corpus's low motif-repeat figure actually
  measures once MIDI quantisation is removed from the account [K22 plus inference].

---

## 10. What to avoid

1. Triplet gallops. The style's cell is 2:1:1 in sixteenths, and the gallop is explicitly not a
   triplet [K17].
2. Swing or shuffle anywhere in a stage or boss cue [K22, K17].
3. Long held lead notes as the main content: 76 percent of the corpus's melody notes are a single
   sixteenth [K22]; a cue of half notes is a different genre.
4. A single chord per bar under a busy melody: the corpus changes harmony 3.78 times a bar [K22].
5. Major key for a stage theme. Major is reserved for clear, miss and ending cues in the measured
   Castlevania set [K22].
6. Stacking two extended chords back to back, and any jazz substitution of the dominant: the style's
   dominant is a sus4 or a flat five dominant, not an altered jazz dominant [K16, K22].
7. Using the VRC6 saw for the melody. It is a bass and pad voice on this chip, and above about the
   bass register its aliasing is audible [K14].
8. Three simultaneous melodies on the VRC6. The documented use of the extra channels is string and
   pad doubling [K7].
9. Fills longer than two beats in a 15 bar stage loop. There is no room; the fill becomes the theme
   [inference from K22's form sizes].
10. Closing every loop with a tonic cadence. The corpus closes open [K22].

---

## 11. The 30 recipes

Full machine-readable rows are in `data/recipes/konami.json` (family prefix KON, 30 recipes). Index:

| ID | Name | Where it goes |
| --- | --- | --- |
| KON-01 | Gallop cell, 2:1:1 | stage riff, boss riff |
| KON-02 | Reverse gallop answer | phrase two of a riff |
| KON-03 | Driving eighth bass under a sixteenth riff | stage | 
| KON-04 | Harmonic minor riff frame | stage, boss |
| KON-05 | Raised seventh cadence | end of every 4 bar group |
| KON-06 | Flat two Neapolitan stab | crypt, boss |
| KON-07 | Flat five dominant | stage, boss |
| KON-08 | Diminished hinge chord | mid riff |
| KON-09 | Second inversion climb | boss, Mad Forest path |
| KON-10 | Chromatic bass walk | transition bar |
| KON-11 | Organ arpeggio at frame rate | title, crypt |
| KON-12 | Held organ chord on VRC6 | crypt, boss intro |
| KON-13 | Saw bass riff | VRC6 stage |
| KON-14 | Saw and triangle split octaves | VRC6 stage intro only |
| KON-15 | Two pulse register crossing | Vampire Killer path |
| KON-16 | Call and response bars | stage A section |
| KON-17 | Dotted eighth echo voice | title, crypt |
| KON-18 | Fast sixteenth fill, two beats | every 8 bars |
| KON-19 | Descending harmonic minor run | phrase end |
| KON-20 | Stop time break | boss transition |
| KON-21 | Boss tempo lift plus minor second pedal | boss |
| KON-22 | Four bar riff to hook, one change on repeat three | every stage theme |
| KON-23 | Half cadence loop ending | all loops |
| KON-24 | Transposition ladder | boss escalation |
| KON-25 | Run and gun march kit | Contra style |
| KON-26 | Odd metre arpeggio wall | boss, Gradius lineage |
| KON-27 | Stage clear fanfare, under 4 bars | one shots |
| KON-28 | Duty change inside a note | human touch |
| KON-29 | One frame push on short notes | human touch |
| KON-30 | Layered loop with 1, 2, 4 bar periods | long stage loops |

---

## 12. Listening notes: ten tracks, what to listen for

These are ear training notes. No melody is written out; each note names a section and a bar position
and a feature to count.

1. Castlevania, Vampire Killer (Terashima, stage 1) [K1]. Listen to the first bar only. Count how many
   attacks there are in the first beat and whether the lead is on one pulse or trading with the
   second. The published analysis puts this cue at 129 bpm in D minor with a 41 semitone melody range
   and a chord-melody tension of 58 [K15]; the training target is to hear which note in the first bar
   is not in the chord under it. Then listen to bars 9 to 16: the published commentary describes a 16
   bar loop with the two square voices crossing registers [K24], so mark the bar where the lead drops
   below the second voice.
2. Castlevania, Vampire Killer, the bass line in isolation. Listen for whether the bass changes pitch
   on every eighth or holds the root. Then compare with the melody's sixteenth density; the corpus
   says 76 percent of melody notes are a sixteenth [K22], and if the bass is eighths the contrast is
   the thing you are training.
3. Castlevania III, Mad Forest (Maezawa, Funahashi, Morimoto) [K5]. Listen to the first four bars and
   count chord changes rather than notes: the tab lists seven chords in the intro and verse section,
   moving through a flat five dominant, a diminished second, and second inversion chords before the
   tonic [K16]. Then listen for the bar where the bass steps up by semitone, and note that the melody
   on top stays consonant (tension 20) [K16].
4. Castlevania III, Mad Forest, the intro only. Compare the wall of VRC6 pulses with the NES version
   of the same section. The Japanese cartridge runs eight channels and the North American release runs
   five [K6, K7]; the audible difference is a sustained pad under the riff, which is what a string
   imitation sounds like on this chip [K7]. Count how many sustained layers you can separate.
5. Castlevania III, any stage theme, the saw bass. Listen for the bass's harmonics: whether the bass
   sounds like a triangle wave (pure, no bite) or like a bass guitar (buzzy, buzzy on the attack).
   That difference is the VRC6 saw against the 2A03 triangle [K7, K14].
6. Castlevania, Heart of Fire (Yamashita, stage 5) [K1]. It is the longest piece in the measured
   Castlevania set at 45 bars [K22], which at the measured tempo band is about 83 s. Listen for how
   the piece avoids repeating itself over that length: which layer changes first, bass, harmony or
   melody, and at what bar interval. This is the training for section 9's deliberate imperfection.
7. Castlevania, Wicked Child (Yamashita, stage 3) [K1]. 34 bars by the same measurement [K22]. Listen
   for the phrase lengths: count bars until the melody rests for two beats. The corpus's median phrase
   is 10 bars [K22]; check whether the ear agrees with the counter.
8. Contra, stage 1 (Maezawa and Sada, after Muraoka) [K8, K10]. The measured Contra set is 10 of 13
   pieces in minor with A minor most common [K22]. Listen to the drum pattern only: is the snare on 3
   or on 2 and 4, and does the kick double the riff's long note. Then listen for the point where the
   bass stops playing eighths and the riff carries the low end alone.
9. Gradius, boss theme (Higashino) [K11]. The documented aim was odd metres, rapid arpeggios and the
   Lydian mode, against buoyant stage themes [K11]. Listen for the bar where the metre stops being four
   and count the beats in that bar; then listen to whether the arpeggio is rising or falling, which
   tells you the direction the tension is being pushed.
10. Super C (Maezawa sound design) [K9], any stage. Listen to how few elements the mix carries: a riff,
    a bass, a drum kit, and whether the fourth voice at any moment is harmony or noise. The exercise is
    to name the role of each of the five channels at bar 1, bar 5, bar 9, so you can hear the
    arrangement change under a static riff.

---

## 13. Sources

All links read on 2026-10-21.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| K1 | Legacy Music Hour, Episode 36, Kinuyo Yamashita interview | http://www.legacymusichour.com/2011/07/legacy-music-hour-episode-36-kinuyo.html | Track by track attribution between Yamashita and Terashima; separate composition; the "James Banana" alias |
| K2 | Dongled, Kinuyo Yamashita 40th anniversary interview (quoted in the Time Extension report) | https://timeextension.com/news/2026/09/i-feel-very-fortunate-castlevanias-kinuyo-yamashita-celebrates-40-years-of-the-vampire-slaying-classic | Maezawa was not involved; Sakamoto listened to her piano performances; no sequencer; credits correction |
| K3 | Wikipedia, Kinuyo Yamashita | https://en.wikipedia.org/wiki/Kinuyo_Yamashita | Co-credit with Terashima under James Banana; strict hardware constraints; fast beats as the series format |
| K4 | Time Extension news, September 2026 | https://timeextension.com/news/2026/09/i-feel-very-fortunate-castlevanias-kinuyo-yamashita-celebrates-40-years-of-the-vampire-slaying-classic | The modern credit correction and the Vampire Killer MSX2 data entry work |
| K5 | Enjoy Game Japan Museum, Jun Funahashi creator page | https://museum.enjoygamejapan.online/en/creators/jun-funahashi | Castlevania III co-composed by Funahashi, Maezawa and Morimoto; VRC6 detail; NES downgrade |
| K6 | The Cutting Room Floor, Castlevania III regional differences | https://tcrf.net/Castlevania_III:_Dracula%27s_Curse/Regional_Differences | VRC6 debut, two extra squares with extended duty, one sawtooth, eight channel BGM |
| K7 | Internet Archive, Akumajou Densetsu soundtrack notes | https://archive.org/details/akumajo_densetsu-castlevania3-soundtrack | VRC6 adds two pulses and a saw; music mostly imitates a string section; Yoshinori Sasaki downgraded the NES release |
| K8 | Video Game Music Preservation Foundation, Contra (NES) | https://vgmpf.com/Wiki?title=Contra_(NES) | Arcade themes by Muraoka, ported by Maezawa and Sada, new Introduction |
| K9 | MusicBrainz, Konami Kukeiha Club release credits | https://musicbrainz.org/medium/142c9767-fad6-3342-ad52-6c857255b288 | Contra NES sound creators; Super C sound design by Maezawa |
| K10 | Original Sound Version, Mondo Contra release note | http://originalsoundversion.com/mondos-contra-ost-vinyl-premiering-at-san-diego-comic-con | NES Contra composed by Maezawa and Sada, arcade arranged by Muraoka, Kukeiha Club pseudonyms |
| K11 | VGMO, Miki Higashino profile | https://vgmonline.net/mikihigashino | Thirteen Gradius pieces, boss theme with odd metres and rapid arpeggios and Lydian, Kraftwerk influence |
| K12 | Video Game Music Preservation Foundation, Kiyohiro Sada | https://vgmpf.com/Wiki/index.php/Kiyohiro_Sada | Bayou Billy, Rush'n Attack, Green Beret, Top Gun credits; Konami to Natsume |
| K13 | Video Game Music Preservation Foundation, Tsutomu Ogura | https://vgmpf.com/Wiki/index.php/Tsutomu_Ogura | Bayou Billy four person job, sheet first then driver arrangement, two driver versions |
| K14 | NESdev Wiki, APU and VRC6 audio | https://www.nesdev.org/wiki/APU and https://www.nesdev.org/wiki/VRC6_audio | Five channels, duty values, no volume control on triangle, VRC6 eight duty steps, 100 percent mode, saw accumulator cap 42, phase reset on the high period byte |
| K15 | Hooktheory theorytab mirror, Castlevania Vampire Killer | http://devhookpad.hooktheory.com/theorytab/view/kinuyo-yamashita/castlevania---vampire-killer | D minor, 129 bpm, 4/4, range A2 to D6, melodic complexity 96, tension 58, novelty 41, most used chord i |
| K16 | Hooktheory theorytab mirror, Castlevania III Mad Forest | http://devhookpad.hooktheory.com/theorytab/view/konami/castlevania-3---mad-forest | 129 bpm, 4/4, range C3 to A6, chord complexity 96, melody tension 20, novelty 94, the seven chord intro and verse progression with V flat five, diminished ii, second inversions and a Lydian V |
| K17 | Guitar World, gallop rhythm lesson | https://guitarworld.com/lessons/gallop-rhythms-heavy-metal-guitar-part-2 | Eighth plus two sixteenths, counted 1 and a, explicitly not a triplet, reverse gallop 1 e and |
| K18 | Wikipedia, Heavy metal gallop | http://en.wikipedia.org/wiki/Heavy_metal_gallop | The cell, palm muted ostinato, drum translation, variants |
| K19 | Wikipedia, Phrygian dominant scale | https://en.wikipedia.org/wiki/Phrygian_dominant_scale | Fifth mode of harmonic minor, 1 flat2 3 4 5 flat6 flat7, half augmented second half whole half whole whole |
| K20 | Wikipedia, Minor scale | https://en.wikipedia.org/wiki/Minor_scale | Harmonic minor as natural minor with a raised seventh, the augmented second it creates |
| K21 | Wikipedia, Tritone | https://en.wikipedia.org/wiki/Tritone | Six semitones, the interval that drives diminished, dominant and half diminished chords to resolve |
| K22 | Primordial Paradox corpus statistics, `D:\Musikage-Corpus\style-pp\stats\nes_rock_metal.json` (generated 2026-10-21 from 86 NES-MDB pieces) | local file | Keys, lengths, interval histogram, duration histogram, chord qualities and transitions, phrase and cadence shares, role pitch medians, and the normalised tempo caveat |
| K23 | Andrew Schartmann interview, Analyzing NES Music (as recorded in MUSIC-HOOK-GRAMMAR.md) | https://intellect.stisonbooks.com/media/Andrew-Schartmann-interview.pdf | Short reusable units recombined, nested and layered loops, the illusion of variety |
| K24 | Eurogamer, Castlevania's Vampire Killer beats (as recorded in MUSIC-HOOK-GRAMMAR.md) | https://www.eurogamer.net/castlevanias-vampire-killer-beats | Driving beats, classical organ and horror reference, two squares crossing registers, 16 bar loop |
| K25 | Kaos Metal, the gallop rhythm explainer | https://kaosmetal.com/magazine/explainers/gallop-rhythm-metal | The cell written as long plus two shorts, reverse gallop, why it is neither shuffle nor straight eighths |

---

## 14. Limits of this document

- The corpus figures come from converted MIDI of 86 pieces across five Konami style games, so they
  describe the archive's transcription as much as the composers' intent; they are used for ratios and
  shapes, never as bar level ground truth about a specific track.
- Tempo cannot be measured from that corpus at all [K22]; every tempo statement here is either quoted
  from a published analysis [K15, K16], from the gallop literature [K18], or marked as inference.
- Two published theory tabs are a thin sample. The key and tempo figures for Vampire Killer and Mad
  Forest are real but should not be generalised to the whole trilogy.
- The credit record of 1980s Konami is still being corrected (Yamashita's 2026 interview removed
  Maezawa from the original Castlevania) [K2, K4]; attributions here follow the most recent primary
  source and say so.
- Nothing in this file is a transcription, and the recipes in `data/recipes/konami.json` describe
  construction rules only, so no melody of these games can be reconstructed from them.
