# Music hook grammar: what makes NES music recognisable and memorable

Card t_d8758a07 (MEM-STUDY), research-assistant, written 2026-10-21. Companion to
knowledge/MUSIC-STYLE-BIBLE.md. Read PLAN-V2-2026-10-21.md section 0 first: study and measure,
never copy or transcribe. This file contains no melodic transcriptions and no note strings; it
carries structural facts and numbers only.

Tagging convention. Every factual claim ends with a source id in square brackets, for example
[S51]. The full rows are in section 10 of this file and are also added to section 6 of the style
bible, so the recipe JSON can cite the same ids. Anything not backed by a source is marked
[inference]; an inference is mine (research-assistant) and it exists so the composer has a
number to aim at, not so it can be quoted.

| Source type | Count | What it gives us |
| --- | --- | --- |
| Peer reviewed recognition and earworm studies | 6 | Recognition time, contour vs interval memory, repetition statistics [S45 to S50] |
| Quantitative per song analyses (Hooktheory theorytabs) | 6 | Key, tempo, metre, melody range in semitones, beats per note, diatonic share, chord tone share [S51 to S56] |
| NES music scholarship and long form criticism | 4 | Why loops work, how variety is faked, section-level analysis [S57, S59, S60, S61] |
| Chip technique references | 2 | What the 2A03 can express and in what units [S62, S63] |
| Reference wiki and primary histories | 3 | Per theme composition facts [S58, S64, S65] |

---

## 1. The first five seconds rule

### 1.1 What listeners can identify, and how fast

- In the Hooked on Music experiment (more than 12,000 participants, more than 1,000 clips),
  people recognised the well known songs in about 5 seconds on average; the fastest answers were
  2.29 s for "Wannabe", 2.48 s for "Mambo No. 5" and 2.62 s for "Eye of the Tiger" [S45].
- Earworm tunes, as opposed to merely familiar ones, are faster and have more common global
  contours: 3,000 people, 100 earworm tunes against 100 controls, 83 melodic features per tune,
  and a final model built from tempo plus two contour measures [S46].
- Contour is what carries melody memory over the first few seconds, and exact interval
  information is what survives longer: contour dominated memory after a 5 s delay, while interval
  information was retained efficiently at a 31 s delay [S47].
- Recognition is driven by how distinctive a theme is rather than by how often it is heard; a
  model built on timing and pitch distinctiveness explained 85 percent of the variance in
  recognition point across 120 melodies and 32 listeners [S48].
- Perceived catchiness also changes how the body responds: across 450 participants and 240 clips,
  catchiness predicted the pleasurable urge to move (beta = .262, variance Rm squared = .037), and
  rhythm alone was the most recognisable layer (56 percent overall recognition, 60.7 percent for
  drums, 54.7 percent for bass on its own) [S50].

### 1.2 Converted into bars and seconds for this project

Tempo arithmetic for our own cues, so "the first five seconds" is a bar count and not a feeling
[inference from the tempos below]:

| Tempo | Metre | One bar | 2 bars | 4 bars | 8 bars |
| --- | --- | --- | --- | --- | --- |
| 104 bpm (title theme v2) | 3/4 | 1.73 s | 3.46 s | 6.92 s | 13.85 s |
| 120 bpm | 4/4 | 2.00 s | 4.00 s | 8.00 s | 16.00 s |
| 150 bpm | 4/4 | 1.60 s | 3.20 s | 6.40 s | 12.80 s |
| 180 bpm | 4/4 | 1.33 s | 2.66 s | 5.33 s | 10.66 s |

Rules that follow, all [inference] from the numbers above:

1. The hook must be fully stated inside the first 4 bars. At 104 bpm in 3/4 that is 6.9 s, which
   sits just above the 5 s average recognition time [S45]; at 150 to 180 bpm it is 5.3 to 6.4 s.
   A hook that needs 8 bars to complete arrives after the listener has already decided.
2. The first 2 bars must already carry the hook's identifying feature, because the fastest
   recognitions happen at 2.3 to 2.6 s [S45] and contour memory forms within 5 s [S47].
3. The hook must be an intro optional design: the identifying rhythmic cell should be playable
   from bar 1 with no preparation. The Mega Man 2 stage theme opens with a rising figure that
   builds tension before the main melody, which works because the figure is itself the hook's
   first half; the theme is discussed as two sections with a bridge rather than an intro plus
   melody [S59].
4. Distinctiveness beats familiarity, so the first 4 bars must contain at least one element that
   no other cue in the game uses (a duty change, a register leap, an unusual accent, a
   non diatonic note) [S48].

### 1.3 Hook length in bars and notes

Measured beats per note in the analysis set: 0.62 (Vampire Killer), 0.88 (FF Battle), 0.89
(Dr Wily Stage 1, SMB3 Overworld) [S51, S52, S53, S56]. That converts a bar count into a note
count [inference, arithmetic]:

| Hook phrase | Beats in 4/4 | Notes at 0.89 beats/note | Notes at 0.62 beats/note |
| --- | --- | --- | --- |
| 1 bar | 4 | 4 to 5 | 6 to 7 |
| 2 bars | 8 | 9 | 13 |
| 4 bars | 16 | 18 | 26 |
| 8 bars | 32 | 36 | 52 |

Working numbers for delivery [inference]:

- Primary hook: 2 to 4 bars, 8 to 18 notes, and it must be repeatable without the listener
  noticing a seam.
- Answer phrase: 2 bars, 5 to 9 notes, ending on a different cadence from the first phrase.
- The measured whole-song melody spans in the analysis set were 64 beats (Vampire Killer, SMB3
  Overworld), 106 beats (FF Battle) and 160 beats (Dr Wily Stage 1), which is 16, 26.5 and 40
  bars of melody respectively [S51, S52, S53, S56]; a NES cue is therefore a small number of
  phrases reused, not a long tune.

---

## 2. Motif anatomy

A motif that survives a 40 second loop has five separable properties. Each one is separately
scored in the checklist in section 9.

### 2.1 Rhythm identity: a repeatable rhythmic cell

- Rhythm is the most recognisable layer on its own: 60.7 percent recognition from drums alone and
  54.7 percent from bass alone [S50]. That is the strongest single argument for writing the
  rhythm first and the pitches second [inference].
- The measured melodies are note dense and short: 0.62 to 0.89 beats per note [S51, S52, S53,
  S56]. At 0.62 beats per note the melody has roughly 1.6 notes per beat, which is a rhythmic
  figure, not a tune of long held notes [S56].
- Syncopation is explicitly measured in the analysis set: Vampire Killer is tagged "punchy
  syncopation", Dr Wily Stage 1 "loose syncopation", SMB3 Overworld "loose syncopation"
  [S51, S52, S56]. The Super Mario Bros. Ground Theme is described as a swing rhythm with
  prominent syncopation, in cut time, at about 100 bpm [S58].
- Practical target [inference]: the cell is 2 to 6 attacks long, it contains exactly one
  syncopation or one rest that the listener can predict, and the same cell must be hummable
  without the harmony.

### 2.2 Contour: arch, rise then leap down, pedal then step

Three contour shapes cover most of the material we studied [inference, built from the analyses
below]:

1. Arch: rise to the peak near the middle of the phrase, then fall back. The Kirby first stage
   theme uses an ascending tonic triad that peaks more than an octave above its starting note and
   then descends about half a scale to the nearest G [S64].
2. Rise then leap down: a short climb and then one fall, which is the shape that pairs with a
   heroic or march-like cue. The Vampire Killer melody spans 41 semitones (A2 to D6) with 82
   percent diatonic notes and 76 percent chord tones, so a wide, leap-heavy line is possible
   provided the harmony underneath stays simple [S56, S61].
3. Pedal then step: repeat one note, then move by step. The Final Fantasy battle theme melody
   spans only 8 semitones (A4 to F5) at 150 bpm with 0.88 beats per note, which is a narrow,
   insistent, high-chord-complexity design: identity comes from the riff against the harmony
   rather than from pitch travel [S53].

- Contour is what carries memory in the first seconds [S47], and common global contours are a
  property of earworm tunes [S46]. So the contour should be one of the familiar shapes above, not
  a novel shape [inference].

### 2.3 Interval usage: mostly steps with one memorable leap

- Diatonic note share in the measured set: 95 percent (Dr Wily Stage 1), 91 percent (SMB3
  Overworld), 82 percent (Vampire Killer), 80 percent (FF Battle) [S51, S52, S53, S56]. That
  leaves 5 to 20 percent of notes outside the key, which is one or two notes per phrase at these
  lengths [inference].
- Chord tone share in the same set: 68 percent (Dr Wily Stage 1), 81 percent (SMB3 Overworld),
  76 percent (Vampire Killer), 69 percent (FF Battle) [S51, S52, S53, S56]. About two notes in
  three land on a chord tone, so the strong beats belong to the harmony and the weak beats carry
  the colour [inference].
- Practical target [inference]: at most one leap larger than a fourth in the hook, placed at the
  same metric position every time the hook returns, so the leap itself becomes the signature.

### 2.4 Range: an octave or less for the hook, wider for the whole cue

- Measured whole melody ranges: 8 semitones (FF Battle) [S53], 15 (SMB3 Overworld) [S52],
  22 (Kid Icarus Underworld, E flat 3 to D flat 5) [S55], 29 (Dr Wily Stage 1) [S51], 41
  (Vampire Killer) [S56].
- Reading: famous NES melodies are not uniformly narrow; the narrow ones (8 to 15 semitones) are
  the riff and hook type, and the wide ones (29 to 41) put their width in fast passing motion
  rather than in the hook itself [inference].
- Target for our hook: within 12 semitones, so it can be sung by one voice and so it fits the
  triangle bass plus two pulses without a register jump that the chip renders badly [inference].

### 2.5 Repeated notes

- A repeated note is the cheapest identity marker: it costs one pitch and no harmonic risk, and
  it makes the rhythm audible [inference]. Its measured signature is a low beats per note figure
  (0.88 and 0.89 in the set) combined with a narrow range (8 to 15 semitones) [S52, S53].
- The 2A03 makes a repeated note easy to keep alive: the pulse envelope and the volume nibble can
  be re-triggered per frame, so a repeated note can pulse rather than sit flat [S62, S63].

---

## 3. Repetition with variation

### 3.1 The statistics

- In a corpus of 6,208 folk songs and 9,788 melodic themes, repeated interval patterns were
  local, metrically parallel and multi-interval; at a distance of one measure, the pattern
  R-I-I occurred 2.7 times as often as I-I-I in one corpus [S49]. Repetition in real music is
  repetition with an operation applied, not literal cloning [inference from S49].
- NES composers solved the loop problem by building short reusable units that can be reordered or
  recombined, and by layering loops across voices; the composer Neil Baldwin described the aim as
  creating the illusion of variety [S57].
- Transpositional sequences, meaning a motif shifted up or down by a fixed interval, are
  everywhere in the repertoire, and they were cheap to implement in early sound drivers [S57].
- Exposure matters for stickiness: across 44 participants hearing four novel choruses 1 to 4
  times, more exposure increased later musical interference consistent with earworm formation,
  and perceived familiarity and the desire to sing along rose significantly between sessions
  [S67].

### 3.2 The four operations and their ratios

Ratios here are [inference] sized to the measured phrase lengths (2 to 4 bars, 8 to 18 notes) and
to the 2.7:1 preference for varied over literal repetition [S49]:

| Operation | What changes | Ratio to use inside an 8 bar phrase | Chip cost |
| --- | --- | --- | --- |
| Exact repeat | Nothing; used to plant the hook | 2 statements maximum before an operation | Zero |
| Sequence | Whole cell transposed by a fixed interval | 1 per phrase, usually the third statement | Zero |
| Rhythmic variation | Same pitches, new rhythm or new accent | 1 per 8 bars | Zero |
| Changed ending | Same head, different cadence or last 2 notes | Every second statement of the phrase | Zero, but it must still loop |

Rules [inference]:

1. Statement, then varied statement, then sequence, then changed ending, over 8 bars, is the
   default shell.
2. Never repeat a phrase exactly three times in a row; the third time must carry an operation
   [S49].
3. The changed ending is the seam of the loop; write it so the last note points back at the first
   note.
4. A deceptive cadence on the repeat is a legal and cheap way to vary an ending: the Kirby first
   stage theme repeats its first phrase with a deceptive cadence into the relative minor before
   resolving [S64].

---

## 4. Structure: loop lengths, call and response, antecedent and consequent

### 4.1 Measured loop and section lengths

| Cue | Section or loop length | Notes |
| --- | --- | --- |
| Vampire Killer (Castlevania, 1986) | 16 bar first stage loop | Described as a 16 bar loop built on rock roots with heavy use of the flat seven chord [S61] |
| Vampire Killer analysis | 64 beats of melody | same 16 bars at 4/4 [S56] |
| SMB3 Overworld | 64 beats of melody, 15 semitone range | [S52] |
| Mega Man 2, Dr Wily Stage 1 | 160 beats of melody, two sections plus a bridge | Section analysis in prose, no transcription [S51, S59] |
| Final Fantasy battle theme | 106 beats of melody | [S53] |
| Super Mario Bros. Ground Theme | Periodic structure, cut time, about 100 bpm, swing and prominent syncopation; built from short reusable units | [S57, S58] |
| Kirby first stage theme | Two primary sections, C major then C minor | Second section repeats a rising figure twice before returning [S64] |

- 8 and 16 bars are the measured workhorses; 16 bars is directly evidenced twice [S52, S56,
  S61], and 32 bars appears as the sum of two 16 bar sections rather than as a single loop
  [inference from S51, S59].
- Because the melody in the set runs 64 to 160 beats, the practical unit is a 4 or 8 bar phrase
  inside a 16 bar loop, with a B section of 8 to 16 bars [inference].

### 4.2 Call and response, antecedent and consequent

- Call and response is documented at register level in Vampire Killer: the two square voices take
  turns, one falls silent so the other can speak, they chase each other a beat apart, and they
  arc in opposite directions, so one voice never merely doubles the other [S61 confirms the
  stylistic template; the register-level claim is from the analysis page cited at S61].
- Antecedent and consequent at phrase level: the Kirby first stage theme's first phrase ends on a
  half cadence (tonic, then two, then dominant), the repeat leads into the relative minor by a
  deceptive cadence, and the resolution arrives with an authentic cadence while the accompaniment
  stops and joins the melody in chords [S64]. That is a textbook antecedent-consequent pair with
  the second ending rewritten [inference].
- Practical shape for our cues [inference]: 4 bar antecedent ending on V or on an open note, then
  4 bar consequent that answers it and closes, with the answering voice on a different duty or a
  different octave so the turnover is audible.

---

## 5. Harmony and the bass line

### 5.1 The bass carries identity

- Bass alone carries 54.7 percent recognition [S50], which is nearly as much as drums alone at
  60.7 percent, so the bass line is a hook in its own right and not filler [inference].
- The analysis set measures how the melody sits against the bass: the "chord-bass melody" figure
  is 91 for Dr Wily Stage 1 [S51] and 96 for SMB3 Overworld [S52], against a database average of
  50, so in these themes the melody is unusually tightly coupled to the bass motion.
- Layering is how the chip fakes variety: the triangle vamps on a simple bass line while the
  pulses do melodic or contrapuntal work [S57].
- Three bass types to write as recipes, each with a different identity cost [inference]:
  1. Walking: one pitch per beat or per eighth, step or small leap, so the bass itself has a
     contour the listener can anticipate.
  2. Pedal: one pitch held or re-attacked, which frees attention for a busy melody and is the
     safest choice under a narrow-range hook.
  3. Ostinato: a 2 or 4 beat cell repeated for the whole section, which is the cheapest route to a
     memorable cue because the cell becomes the hook.

### 5.2 One or two non diatonic notes

- Measured non diatonic share is 5 percent (Dr Wily Stage 1), 9 percent (SMB3 Overworld),
  18 percent (Vampire Killer) and 20 percent (FF Battle) [S51, S52, S53, S56]. At these phrase
  lengths that is one to three coloured notes per phrase [inference].
- Transpositional sequences produce non standard modal colour for free; the interviewed scholar
  gives a move from D major to E major as an example that introduces a G sharp and a Lydian
  flavour [S57].
- Target [inference]: exactly one, or at most two, notes outside the key in a 4 bar hook, placed
  on a weak beat or on the peak of the contour, and repeated at the same place every time the
  hook returns so it becomes part of the theme's fingerprint.

---

## 6. Contrast between sections

- The cheapest contrast in the repertoire is mode or key, not instrumentation: the Kirby first
  stage theme moves from C major in section one to C minor in section two while the tempo and the
  rhythmic cell continue [S64].
- Second cheapest is register and voice count: the Vampire Killer texture is documented as voices
  taking turns and crossing registers so that it is briefly unclear which voice leads [S61].
- Third is harmonic weight, measured as chord complexity: 32 (SMB3 Overworld), 43 (Dr Wily
  Stage 1), 94 (Final Fantasy battle theme), all on a scale where 50 is average [S51, S52, S53].
  A battle or boss cue earns its contrast from harmony, a field or title cue from rhythm and
  timbre [inference].
- Fourth is the bridge as release: Dr Wily Stage 1 is described as a minor march whose melody
  builds through two sections with a bridge that releases tension before the return [S59].
- Chip means for contrast [S62, S63]: change duty (12.5 percent is thin, 25 is reedy, 50 is
  hollow), drop a voice for 2 bars, move the lead up or down an octave, swap the noise shade for
  hats only, or change the arpeggio speed.

---

## 7. Humanness: what listeners hear as human, and how to do it on the chip

The brief from Nayil is that the music sounds great but not quite human. These are the specific,
cheap, chip legal gestures that read as human performance. The numbers below are the resolution
of the chip, because that is what sets the smallest possible variation.

### 7.1 The chip's expression resolution

| Unit | Value | Consequence |
| --- | --- | --- |
| Frame | 1/60 s = 16.7 ms on NTSC | The smallest timing variation is one frame; a 1 to 2 frame jitter is the human timing range [S62, S63] |
| Volume | 16 steps (0 to 15) per channel | An envelope is a 16 level staircase; a 2 step swell is audible, a 1 step change is not [S63] |
| Envelope clock | 240 Hz envelope divider source | Envelope shapes are hardware timed, so "human" decay is a choice of divider and loop, not a curve [S63] |
| Duty | 4 settings, 3 distinct timbres (12.5, 25, 50 percent) | A mid note duty change is a timbral gesture that costs nothing [S62] |
| Pitch | 11 bit period | Fine pitch wobble is available; writing the high period byte re-triggers the phase and pops, so vibrato goes through the low byte only [S63] |
| Arpeggio speed | 1 frame per note is about 20 chord cycles per second | 1 frame reads as a buzzy chord; 2 to 3 frames per note slows into an audible strum [S62] |

### 7.2 The gestures, with a chip legal route for each

| Human hearing | Why it reads as human | Chip legal route | Source |
| --- | --- | --- | --- |
| Micro timing variation | Machines are exactly on the grid; players are not | Detune a delay of 1 to 2 frames on the answering voice only, never on the bass | [S62, S63] plus [inference] |
| Delayed vibrato | Singers and string players add vibrato after the attack, not at it | Hold a note, then start a small period wobble after 2 to 4 frames; write the low period byte only | [S62, S63] |
| Ornament and grace note | A real player decorates a repeated note | Insert a 1 frame upper neighbour on the second statement of a repeated note | [inference] |
| Breath rests | Phrase ends need air | A rest of one eighth note at the end of every 4 bar phrase, on the melody voice only | [inference] |
| Imperfect repetition | Literal repetition sounds mechanical | Apply one operation on the third statement; R-I-I over I-I-I at 2.7 to 1 | [S49] |
| Volume envelope shape | Instruments have attack and decay, not square gates | Per note volume nibble plus hardware envelope; percussive decay for the lead in fast cues, slow swell for the pad | [S62, S63] |
| Fills before a change | Drummers mark the seam | One bar of noise, hat or tom figures before the section change, ending on the beat | [inference] |
| Unison shimmer | Real ensembles are never exactly in tune | Second pulse a few cents flat and about 18 ms late | [S8, S62] |
| Timbre change mid phrase | Players change colour on a new phrase | Change duty at the phrase boundary, not mid note, so the change lands with the phrase | [S62] |
| A slightly surprising ending | The expected cadence is the boring one | Change the last 2 notes, or use a deceptive cadence on the repeat | [S64] |
| Full sounding drums | A single noise channel read as a full kit | Noise pitch and decay per hit; periodic mode for metallic hits; arpeggio speed shifts for tom versus hat | [S62, S63] |

### 7.3 The anti human list

These read as machine output and should be removed before delivery [inference, from S62, S63 and
from the analysis set above]:

1. Every note at the same volume and the same length.
2. Every note exactly on the sixteenth grid with no 1 frame deviations anywhere.
3. The same duty for the whole cue.
4. A chord held as a real chord via an arpeggio that never drops out.
5. A loop whose last bar is identical to its first bar in every voice.
6. Fills that land a beat early or a frame late.
7. A melody that only moves by step with no repeated note and no leap.

---

## 8. Twelve famous NES themes, and the structural reason each works

Each row states the structural reason in the analyst's terms, gives the measured or documented
fact, and links the public analysis. No melodies are transcribed.

| # | Theme (game, cue) | Composer | Structural reason it works | Documented or measured fact | Source |
| --- | --- | --- | --- | --- | --- |
| 1 | Super Mario Bros., Ground Theme | Koji Kondo | A short periodic phrase with prominent syncopation over a walking bass, tempo matched to the speed of running, so the loop locks to movement | C major, about 100 bpm, cut time, swing and syncopation, periodic structure; the tempo was raised from a slower first draft to match Mario's movement | [S58](https://en.wikipedia.org/wiki/Super_Mario_Bros._theme) |
| 2 | Super Mario Bros. 3, Overworld | Koji Kondo | A near octave melody at high chord tone density over low complexity harmony, so pitch clarity comes from harmony, not from chords | Melody range 15 semitones, 0.89 beats per note over 64 beats, 91 percent diatonic, 81 percent chord tones, chord complexity 32 against melodic complexity 91 | [S52](https://www.hooktheory.com/theorytab/view/koji-kondo/super-mario-bros-3---overworld) |
| 3 | The Legend of Zelda, title theme | Koji Kondo | An overture assembled from the game's own two themes, written in one night after the planned Ravel replacement was blocked by copyright, so it is a distillation rather than a new tune | Planned Ravel use was stopped by copyright, the replacement was written in one day; the analyst argues the resulting theme condenses the overworld and dungeon material | [S60](https://zeldauniverse.net/2019/10/22/zeldas-study-the-copyright-incident-responsible-for-the-iconic-zelda-theme) |
| 4 | Mega Man 2, Dr. Wily Stage 1 | Takashi Tateishi | A fast minor march: a rising figure then a two section hook with a bridge that releases before the return, at a tempo that forbids padding | 180 bpm, 4/4, 29 semitone range, 0.89 beats per note over 160 beats, 95 percent diatonic, loose syncopation, melodic complexity 81 | [S51](https://www.hooktheory.com/theorytab/view/takashi-tateishi/mega-man-2---dr-wily-stage-1), [S59](http://cartridgelit.com/2020/10/29/high-scores-dr-wily-stage-1) |
| 5 | Castlevania, Vampire Killer | Satoe Terashima and Kinuyo Yamashita | A 16 bar loop with two voices answering and crossing instead of doubling, over an unbroken bass pulse, at high note density | 16 bar loop in D minor with heavy flat seven use; 41 semitone range, 0.62 beats per note over 64 beats, 82 percent diatonic, 76 percent chord tones, punchy syncopation | [S56](http://devhookpad.hooktheory.com/theorytab/view/kinuyo-yamashita/castlevania---vampire-killer), [S61](https://www.eurogamer.net/castlevanias-vampire-killer-beats) |
| 6 | Final Fantasy, battle theme | Nobuo Uematsu | Identity from rhythm against rich harmony rather than from pitch travel: a narrow, insistent line over an unusually complex progression | G minor, 150 bpm, 8 semitone range, 0.88 beats per note over 106 beats, 80 percent diatonic, 69 percent chord tones, chord complexity 94 | [S53](https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---battle) |
| 7 | Final Fantasy, Prelude | Nobuo Uematsu | One broken chord pattern reused, with a second pulse entering slightly late and slightly quieter so the pair reads as a harp with an echo | Harp style arpeggio on two pulses, second pulse delayed by one eighth at lower volume; and the composer's own shifted second voice shimmer trick | [S54](https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---prelude), [S7](https://www.thelineofbestfit.com/features/articles/nobuo-uematsu-music-final-fantasy), [S8](https://daily.redbullmusicacademy.com/2014/10/nobuo-uematsu-interview/) |
| 8 | Kid Icarus, Underworld | Hirokazu Tanaka | A compound metre ostinato with uncommon chord changes; the metre instead of the melody does the identifying | 152 bpm, 6/8, 22 semitone range, chord prog novelty 88 on a scale where 50 is average | [S55](https://www.hooktheory.com/theorytab/view/hirokazu-tanaka/underworld---kid-icarus) |
| 9 | Metroid, title and area cues | Hirokazu Tanaka | Atmosphere first: melody and effect share one language, so the cue is a sound world rather than a tune | The composer described a goal of no distinction between music and sound effects on Metroid | [S10](https://shinesparkers.net/interviews/hirokazu-tanaka/) |
| 10 | Tetris, Type A | Hirokazu Tanaka, arranging a Russian folk song | Repetition of a folk cell with a rising intensity expectation, aligned to the falling piece rhythm | The arrangement of the folk song became the Tetris theme and the Tetris Company has required its inclusion in every version since 2002 | [S65](https://en.wikipedia.org/wiki/Korobeiniki) |
| 11 | Kirby's Dream Land, Green Greens | Jun Ishikawa | Antecedent then consequent with a rewritten ending: phrase one ends on a half cadence, the repeat turns deceptive into the relative minor, then an authentic close with the accompaniment joining as chords; section two shifts to the parallel minor | Key C major with a C minor second section; ascending tonic triad peaking over an octave above the start and descending about half a scale; offbeat entry with the following strong beat elongated | [S64](https://wikirby.com/wiki/Green_Greens_(theme)) |
| 12 | Mother (EarthBound Beginnings), Eight Melodies | Keiichi Suzuki, Hirokazu Tanaka | A deliberately hummable, one finger melody: the design brief was a song anyone could sing, so the range and the harmony are kept small | The director asked for a song anyone could hum along with and play with one finger; the composer worked inside a three note simultaneous limit on the chip | [S9](https://en.wikipedia.org/wiki/Music_of_the_Mother_series), [S11](https://mother3.fobby.net/interview/m3int_02.html) |

Reading of the table as a whole [inference]: eight of the twelve earn recognition from one of
three devices, a rhythmic cell that never varies (rows 1, 4, 5, 10), a narrow line over rich
harmony (rows 2, 6, 7, 8), or singable simplicity (rows 11, 12). Rows 3 and 9 are the exceptions
that prove the rule: they are remembered as a setting and a sound world, and both were built out
of material the game already had.

---

## 9. Delivery checklist, 20 yes or no items

Run this before any cue is delivered. Any "no" means the cue is not finished.

| # | Question | Threshold |
| --- | --- | --- |
| 1 | Does the hook complete within its first 4 bars? | 6.9 s or less at 104 bpm in 3/4 |
| 2 | Is the hook identifiable from 2 bars alone? | Yes or no |
| 3 | Does the first bar contain the identifying rhythmic cell, with no intro needed? | Yes or no |
| 4 | Is the hook's range inside an octave (12 semitones)? | 12 or fewer |
| 5 | Is the hook between 8 and 18 notes? | 2 to 4 bars at 0.89 beats per note |
| 6 | Does the hook use at least one repeated note? | Yes or no |
| 7 | Does the hook contain at most one leap larger than a fourth? | 0 or 1 |
| 8 | Are at least 80 percent of hook notes diatonic? | 80 percent or more |
| 9 | Are between 60 and 85 percent of hook notes chord tones? | 60 to 85 |
| 10 | Are there one or two notes outside the key, at a fixed place? | 1 or 2 |
| 11 | Does the third statement of a phrase carry an operation (sequence, rhythm, ending)? | Yes or no |
| 12 | Is the phrase repeated exactly at most twice in a row? | 2 or fewer |
| 13 | Is the loop 8 or 16 bars, with a B section of 8 to 16 bars? | Yes or no |
| 14 | Is there an antecedent phrase ending open and a consequent phrase that closes? | Yes or no |
| 15 | Does the bass have a named type (walking, pedal, ostinato) and an audible contour? | Yes or no |
| 16 | Does section two differ by mode, key, duty, register or voice count, and not only by notes? | Yes or no |
| 17 | Is there at least one 1 to 2 frame timing deviation on a non bass voice? | Yes or no |
| 18 | Are there rests at phrase ends, and a fill in the bar before each section change? | Yes or no |
| 19 | Does the last bar lead back into the first bar, with a changed or deceptive ending on at least one repeat? | Yes or no |
| 20 | Does the cue pass tools/melody_guard.py, and does it contain no copied melodic material? | Yes |

---

## 10. Sources for this file

All read on 2026-10-21 unless stated. These rows are also added to section 6 of
knowledge/MUSIC-STYLE-BIBLE.md as S45 to S66 so that data/music_recipes.json can cite them.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| S45 | BBC News, "People recognise songs in five seconds" (reporting Burgoyne et al., Hooked on Music, 2013) | https://www.bbc.com/news/science-environment-29847739 | About 5 second average recognition, 12,000 plus participants, 1,000 plus clips, fastest times 2.29 to 2.62 s |
| S46 | Jakubowski, Finkel, Stewart and Mullensiefen, "Dissecting an earworm", 2017 | https://doi.org/10.1037/aca0000090 | 3,000 people, 100 earworm vs 100 control tunes, 83 melodic features, tempo plus two contour measures, faster tempo and common global contours |
| S47 | Dowling and Bartlett, "The importance of interval information in long term memory for melodies", 1981 | https://doi.org/10.1037/h0094275 | Contour dominates after a 5 s delay, interval information retained at 31 s |
| S48 | Bailes, "Dynamic melody recognition: distinctiveness and the role of musical expertise", 2010 | https://doi.org/10.3758/mc.38.5.641 | 32 listeners, 120 melodies, distinctiveness model explaining 85 percent of variance |
| S49 | Temperley, "Melodic pattern repetition and efficient encoding: a corpus study", 2024 | https://doi.org/10.18061/emr.v18i2.9289 | 6,208 folk songs and 9,788 themes, local metrically parallel multi interval repetition, R-I-I 2.7 times I-I-I at one measure distance |
| S50 | Bechtold, Curry and Witek, "The perceived catchiness of music affects the experience of groove", 2024 | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0303309 | 450 participants, 240 clips, 56 percent recognition, 60.7 percent drums, 54.7 percent bass, catchiness predicts urge to move |
| S51 | Hooktheory theorytab, Mega Man 2 Dr Wily Stage 1 | https://www.hooktheory.com/theorytab/view/takashi-tateishi/mega-man-2---dr-wily-stage-1 | C minor, 180 bpm, 29 semitone range, 0.89 beats per note over 160 beats, 95 percent diatonic, 68 percent chord tones, chord bass melody 91 |
| S52 | Hooktheory theorytab, Super Mario Bros 3 Overworld | https://www.hooktheory.com/theorytab/view/koji-kondo/super-mario-bros-3---overworld | 15 semitone range, 0.89 beats per note over 64 beats, 91 percent diatonic, 81 percent chord tones, chord complexity 32, chord bass melody 96 |
| S53 | Hooktheory theorytab, Final Fantasy Battle | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---battle | G minor, 150 bpm, 8 semitone range, 0.88 beats per note over 106 beats, 80 percent diatonic, 69 percent chord tones, chord complexity 94 |
| S54 | Hooktheory theorytab, Final Fantasy Prelude | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---prelude | B flat major, 100 bpm, melodic complexity 93 to 94, chord prog novelty 95, one arpeggio pattern |
| S55 | Hooktheory theorytab, Kid Icarus Underworld | https://www.hooktheory.com/theorytab/view/hirokazu-tanaka/underworld---kid-icarus | 152 bpm, 6/8, 22 semitone range, chord prog novelty 88 |
| S56 | Hooktheory theorytab mirror, Castlevania Vampire Killer | http://devhookpad.hooktheory.com/theorytab/view/kinuyo-yamashita/castlevania---vampire-killer | 41 semitone range, 0.62 beats per note over 64 beats, 82 percent diatonic, 76 percent chord tones, punchy syncopation (main domain page did not load; the mirror did) |
| S57 | Andrew Schartmann interview, Analyzing NES Music, Intellect Books | https://intellect.stisonbooks.com/media/Andrew-Schartmann-interview.pdf | Short reusable units reordered and recombined, nested loops, layered loops across voices, illusion of variety (Neil Baldwin), transpositional sequences, Lydian colour from D to E major |
| S58 | Wikipedia, Super Mario Bros. theme | https://en.wikipedia.org/wiki/Super_Mario_Bros._theme | C major, about 100 bpm, swing and prominent syncopation, periodic structure, tempo raised to match Mario's movement |
| S59 | Cartridge Lit, "High Scores: Dr. Wily Stage 1", 2020 | http://cartridgelit.com/2020/10/29/high-scores-dr-wily-stage-1 | Minor march, two sections with a bridge that releases tension, hook dense writing, tempo range 150 to 180 bpm claimed for the series |
| S60 | Zelda Universe, "The copyright incident responsible for the iconic Zelda theme", quoting the 2016 Nintendo developer interview | https://zeldauniverse.net/2019/10/22/zeldas-study-the-copyright-incident-responsible-for-the-iconic-zelda-theme | Planned Ravel Bolero use blocked by copyright, replacement written overnight from the game's own overworld theme |
| S61 | Eurogamer, "Castlevania's Vampire Killer beats" | https://www.eurogamer.net/castlevanias-vampire-killer-beats | Fast driving beats, classical organ and horror score references, two square voices taking turns and crossing registers, 16 bar loop |
| S62 | Music Production Wiki, "How to recreate the chiptune sound" | https://musicproductionwiki.com/articles/how-to-recreate-the-chiptune-sound | Duty settings, frame locked engine at 60 Hz, one frame per step arpeggio, delayed vibrato, mid note duty change, pseudo echo, noise percussion by envelope |
| S63 | NESdev Wiki, APU basics | https://www.nesdev.org/wiki/APU_basics | Register level volume, duty and period, writing the high period byte resets the phase and pops (so vibrato uses the low byte), envelope behaviour |
| S64 | WiKirby, Green Greens (theme) | https://wikirby.com/wiki/Green_Greens_(theme) | Two sections, C major then C minor, ascending tonic triad peaking over an octave above the start then descending about half a scale, offbeat entry with elongated strong beat |
| S65 | Wikipedia, Korobeiniki | https://en.wikipedia.org/wiki/Korobeiniki | The folk song as the Tetris theme, Tanaka's 1989 arrangement, required in every version since 2002 |
| S66 | Zelda Dungeon, "The legend of music 02: Koji Kondo's masterpiece" | https://zeldadungeon.net/the-legend-of-music-02-koji-kondos-masterpiece | The Bolero copyright story, the title theme written in one day, the non standard mode reading of the overworld melody (fan analysis, treated as such) |

| S67 | Killingly and Lacherez, "The song that never ends", 2023 | https://europepmc.org/article/PMC/PMC10585939 | 44 participants, four novel choruses heard 1 to 4 times, exposure increased later musical interference, familiarity and desire to sing along rose |

Existing bible sources reused here: S7 and S8 (Uematsu interviews, Prelude arpeggio and the
shifted second voice shimmer), S9 (Mother series music: the three note simultaneous limit),
S10 (Tanaka on Metroid and on no distinction between music and effects), S11 (the hummable one
finger song request that became Eight Melodies).

---

## 11. What this file does not claim

1. No melody in this project was transcribed, and none of the numbers above are pitch strings.
2. The Hooktheory figures are crowd sourced analyses of the songs, not the composers' own scores;
   they are used as a consistent yardstick across themes, not as authority on any single note
   [inference on method].
3. Beats per note and diatonic share describe whole analysed melody sections, not the hook alone;
   the 2 to 4 bar hook targets in section 1.3 are my conversion, not a measurement [inference].
4. The 12 theme table gives structural reasons at the level an arranger needs. It does not give
   the melodies, and the arranger must not reconstruct them from these rows.
5. Two of the three Pine research files named in the card (nes-hooks.json, chip-expression.json)
   returned no answer (status max_turns, 80 turns each); their questions are covered here from
   the sources listed above instead. earworm-science.json returned eight cited studies and is the
   backbone of sections 1 and 3.

---

## 12. Threshold numbers for tools/hook_score.py

tools/hook_score.py scores a melody against the numbers in this file. It looks for one fenced
block below that starts with `hook_score:` and merges those keys over its own defaults, and its
report then names this path instead of saying "defaults". Each value either restates a measured
number from section 9 or keeps the MEM-TOOLS card default because the research states no number
for that key; the comment says which. Change a threshold here, never in the tool, and expect every
score to move. No melodies appear in this block, only thresholds.

```yaml
hook_score:
  # section 2.1: "the cell is 2 to 6 attacks long"
  hook_cell_notes: [2, 6]
  # section 3.2: measured phrases run 2 to 4 bars; the hook inside one is 1 to 2
  motif_bars: [1, 2]
  # section 9 items 11 and 12: the third statement carries an operation, at most 2 exact repeats
  motif_min_returns: 3
  # card default: this file measures diatonic and chord tone share, not motif coverage
  motif_min_coverage: 0.6
  motif_match_min: 0.6
  # a step is a semitone or a tone
  step_semitones: 2
  # card default: the measured 80 to 95 percent diatonic share is not a step share
  step_ratio_min: 0.65
  # section 9 item 7: at most one leap larger than a fourth, so a fourth or more counts as a leap
  leap_semitones: 5
  leaps_per_motif: 1
  # section 9 item 4 asks for 12 semitones inside the hook; this key measures the whole melody
  # track, where the measured cues run 8 to 41 semitones (section 2.4), so the card's 18 applies
  max_range_semitones: 18
  pedal_range_semitones: 5
  # section 9 item 6: at least one repeated note
  repeat_pitch_min: 1
  # section 9 item 13 asks for 8 or 16; 32 is two 16 bar sections (section 4.1), kept as the card has it
  loop_bars: [8, 16, 32]
  # section 9 items 11 and 12: the third return is varied, so its similarity is a band, not a target
  third_return_similarity: [0.3, 0.85]
  grid: sixteenth
```

The ten weights (20 for motif coverage down to 6 for loop length) stay in the tool, because they
are the card's design choice for how the 0 to 100 total is built, not a measured property of the
repertoire.
