# Baroque and Classical fundamentals on the 2A03 and the VRC6

Card t_4b89e9b6 (STUDY-CLASSICAL), research-assistant, written 2026-10-21. Scope name `classical`.
Companion files: `knowledge/MUSIC-HOOK-GRAMMAR.md`, `knowledge/MUSIC-STYLE-BIBLE.md` (sections 10, 11 and
14.1, 14.2 are the short version of this lane), `knowledge/MUSIC-DRUMS.md`, `knowledge/MUSIC-DISSONANCE.md`,
and the executable recipes in `data/recipes/classical.json`.

Reference rule (PLAN-V2 section 0, and decision 5 in section 6): the repertoire was studied through published
form descriptions, theory references, the Mutopia Project catalogue of public domain editions, and measured
statistics over a MIDI corpus of public domain compositions. Nothing was transcribed, copied or sampled into
this project. No melody appears anywhere in this file. Every musical statement is a shape, a scale degree,
an interval, a rate or a bar count. The one exception allowed by Nayil (PLAN-V2 section 6, item 5) is that the
corpus itself exists outside the game repo at `D:\Musikage-Corpus`, is never shipped, and every generated
melody passes `tools\melody_guard.py` before it is used.

Tagging. Every claim ends with a source id in square brackets, for example [C8]. Section 13 has the link and
read date for each id. `[inference]` marks my own operationalisation of a source, written so the arranger has
a number to hit rather than an adjective to interpret.

P: lines, as the card asks. There are none below this header because nothing here is a progress report; the
whole file is the deliverable. The progress line lives in the task handoff.

---

## 1. What the repertoire is, and which part of it we measured

The card names seven composers and two eras. They are not one style, and the arranger needs to know which
door it is opening:

- **Bach (1685 to 1750).** Two voice inventions and three voice sinfonias as compositional exercises, fugue
  subjects and answers, and the chaconne as a variation engine over a repeated harmonic ground [C7, C8].
  This is the densest counterpoint in the set and the most useful to the chip, because an invention is written
  for exactly two independent lines at a time [C7, inference for the chip].
- **Handel and Vivaldi.** Sequence and drive: a ritornello returns in the tonic, leaves for the dominant, and
  comes back, with the returning statements often shortened to one or two of the opening units [C15]. The
  engine is repetition of a two to four bar unit with changing harmony underneath [C15, C22].
- **Mozart and Haydn.** The period and the sentence, the four bar phrase, the minuet in 3/4 with two repeated
  eight bar sections, and the Alberti broken chord as accompaniment [C11, C23, C24].
- **Beethoven.** The scherzo replaces the minuet, keeps the 3/4 and the ternary shape, and is considerably
  quicker; the joke is built out of a tiny cell rather than a long tune [C9].
- **Chopin, Schubert, Brahms, Strauss.** The waltz as a chain: an introduction, a run of numbered waltzes with
  an A strain and a B strain each, sometimes an intrada between them, and a coda [C16]. Rubato is part of the
  notation of the style even when it is not written [C6].

Why the corpus matters here: the seven names above are represented unevenly, and knowing the counts stops the
arranger from treating "classical" as one texture [C1].

Measured corpus, read 2026-10-21: 200 pieces, 18,942 bars, 333,293 notes of which 119,057 are melody notes,
1,078 phrases, 1,078 cadences [C1]. Composer counts: Bach 45, Mozart 40, Beethoven 37, Schubert 33, Chopin 22,
Haydn 11, misc 9, Brahms 3. No Strauss, no Handel, no Vivaldi [C1]. Licence lines on those 200: 189 public
domain, 8 CC BY 4.0, 3 CC BY 3.0, read per file from the Mutopia search table [C1, C2]. The corpus is a
measuring instrument, not a source of material.

`[inference]` Reading the counts: Bach and Mozart together are 42.5 percent of the corpus and both are
median two voice [C1], which is the same voice budget as the stock 2A03. That is the accident that makes this
lane cheap to arrange. Haydn is 11 pieces and 5 of them are 3/4 [C1], so Haydn is the minuet supplier, not a
general source. Brahms is 3 pieces, all 3/4 [C1], so Brahms and Strauss have to be arranged from form
descriptions [C16] plus the waltz grammar in section 5, not from measured melody habits.

---

## 2. The measured facts

All rows from [C1] unless marked. The file records `generated_at 2026-10-21T22:56:28`, `files_analysed 200`,
`files_failed 0`.

### 2.1 Key, mode, tempo, meter

| Measure | Value | What it means for us |
| --- | --- | --- |
| Mode | 132 major, 68 minor | Major is two thirds of the repertoire, the opposite of the Konami lane |
| Tonics | G 30, C 19, F 17, Bb 14, Cm 14, D 14, Fm 12, Eb 10, A 10, Am 9, Gm 8, Bm 8 | G, C, F and Bb lead: the flat side of the circle |
| Tempo | median 90 bpm, mean 98.7, min 18, max 300, 73 distinct values | Slow by NES standards; a cue at 130 is already fast for this style |
| Meter | 4/4 in 67, 3/4 in 56, 2/4 in 21, 2/2 in 18, 3/8 in 16, 6/8 in 13, others 9 | Triple is 28 percent of the corpus: the waltz and minuet share is real |
| 3/4 tempo | median 104 bpm, range 40 to 300 | The minuet and slow waltz band, not the Viennese band |
| 4/4 tempo | median 90 bpm, range 24 to 272 | The inventions and sonata movements |

Tempo conventions the corpus cannot give, from the dance and form sources: the slow (English) waltz is about
90 beats per minute at 3 beats to the bar, 30 measures per minute; the Viennese waltz is about 180 beats, 58 to
60 measures per minute [C5]. A minuet sits between them; the scherzo is quicker than the minuet it replaced
[C9]. So the project's 3/4 tempo map is a decision, not a single number [inference]:

| Cue type | 3/4 tempo | Seconds per bar | Seconds per 16 bars |
| --- | --- | --- | --- |
| Slow waltz, town or title | 90 | 2.00 | 32.0 |
| Project title theme (score.yaml) | 104 | 1.73 | 27.7 |
| Minuet, court or menu | 120 | 1.50 | 24.0 |
| Viennese waltz, ballroom or ending | 180 | 1.00 | 16.0 |
| Scherzo, battle | 168 to 200 | 1.07 to 0.90 | 17.1 to 14.4 |

### 2.2 Per composer

| Composer | Pieces | Median bars | Median voices | Median bpm | Meter mix | Top keys |
| --- | --- | --- | --- | --- | --- | --- |
| Bach | 45 | 31 | 2 | 80 | 4/4 19, 3/4 18, 3/8 4 | G major 7, G minor 4, A minor 4 |
| Mozart | 40 | 38 | 2 | 100 | 4/4 14, 3/4 9, 2/4 7 | C major 10, F major 9, D major 5 |
| Beethoven | 37 | 164 | 2 | 124 | 4/4 15, 3/4 7, 2/4 5 | G major 8, C minor 5 |
| Schubert | 33 | 83 | 3 | 80 | 4/4 9, 2/2 6, 2/4 5 | Ab major 4, Bb major 4 |
| Chopin | 22 | 71 | 2 | 112 | 4/4 8, 3/4 6, 2/2 5 | F minor 5, B minor 2, Ab major 2 |
| Haydn | 11 | 58 | 2 | 108 | 3/4 5, 2/4 3, 4/4 2 | G major 5, Eb major 3 |
| Brahms | 3 | 32 | 2 | 116 | 3/4 3 | B minor, Ab major, C major |

Two readings that change arrangement decisions [inference]: Bach and Mozart are median 31 and 38 bars, so a
chip cue that copies their scale is 16 to 32 bars and loops, not a 3 minute piece. Beethoven at median 164 bars
is sonata and concerto movement length, which is why the classical source for a long cue should be his cell and
not his form.

Named pieces with their measured readings, because they are the ones a listening pass can check [C1]:
Bach Invention 2 is 27 bars in 4/4 at 64 bpm; Invention 5 is 32 bars at 105; Invention 10 is 32 bars in 9/8 at
172; Invention 13 is 25 bars at 100; Invention 15 is 22 bars at 105. Brahms Waltz No. 10 is 32 bars in 3/4 at
160; Waltz No. 15 is 44 bars in 3/4 at 116. Chopin's Waltz Op. 64 No. 1 is 140 bars in 3/4; his "Walzer h-moll"
is 145 bars in 3/4 at 152. Mozart 12 Duets No. 11 Menuetto is 32 bars at 120 in C major; Haydn's Sonate I
Menuetto is 66 bars at 92 in G major; Beethoven's Quartet No. 4 Menuetto is 167 bars at 192 in C minor.

Caveat, stated so nobody quotes the corpus carelessly [inference]: the key detector is a correlation score, and
it is wrong on well known pieces (it reads Chopin's Waltz Op. 64 No. 1 as F minor because the piece spends its
middle on the parallel minor; mean key correlation 0.8776, with 2 pieces below 0.70 [C1]). Use the corpus for
distributions, not for single piece identity.

### 2.3 Harmony

| Measure | Value | What it means |
| --- | --- | --- |
| Chord beats counted | 60,127 | Per beat, so a held chord appears repeated |
| Changes per bar | 3.17 | Harmony moves on almost every beat in the aggregate |
| Distinct labels | 332 | Roman numeral labels plus inversions, so inversions are part of the style |
| Qualities | maj 22,096; min 10,199; dom7 10,129; min7 4,050; dim 3,772; maj7 3,329; sus4 3,201; dim7 1,374; half-dim7 1,369; sus2 313; aug 295 | Sevenths are as common as plain minor triads |
| Most used single labels | I 9.87 pct, V7 4.69, V 4.58, i 3.54, IV 3.40, I6/4 2.83, I6 2.19, i6/4 1.97, iv 1.88, I7 1.88, Vsus4 1.73, bIII 1.67 | Second inversion is a top ten chord: the cadential 6/4 is everywhere |
| Top bigrams | V7 to I 285, I to I6/4 195, V to I 168, I6/4 to V7 153, V to i 150, I to IV 136, I6/4 to I 132, I to I6 131 | The cadence frame dominates |
| Top trigrams | I6/4 V7 I 66; I I6/4 I 55; i V i 49; V7 I I6/4 48; I V7 I 41 | Prolongation and cadence, almost nothing else at the top |

Dissonance budget from the same table [C1]: diminished labels are 3,772 plus dim7 1,374 plus half-dim 1,369 =
6,515 of 60,127 chord beats, which is 10.8 percent of chord labels carrying a diminished interval; augmented is
295, 0.5 percent; sus4 is 3,201, 5.3 percent. `[inference]` A workable rule for this style is one diminished
colour every 8 to 10 chord changes and almost no augmented chord outside a cadence or a modulation pivot.

### 2.4 Melody

| Measure | Value | What it means |
| --- | --- | --- |
| Intervals counted | 118,857 | Large sample |
| Top intervals | down 2nd 11.36 pct, down m2 8.13, down m3 8.12, up 2nd 7.79, up m2 7.70, unison 6.74, up m3 5.57, down M3 5.25, down P4 4.50, up P4 4.23 | Descending steps slightly outnumber ascending ones |
| Octave leaps | down octave 3.32, up octave 2.72 | The octave leap is common enough to be a gesture, not an exception |
| Step to leap | 41.7 percent steps, 58.3 percent leaps, 0.67 percent leaps over 19 semitones | Leaps are normal; this is not a hymn |
| Top 3 interval shapes | down 2 down 2 down m2 (1,601); down 2 down m2 down 2 (1,581); down m2 down 2 down 2 (1,516) | The micro shape is a descending scale fragment, not an arpeggio |
| Other frequent shapes | 0 0 0 (1,152); up 2 up 2 up m2 (1,028); down octave up octave down octave (750) | Repeated notes and octave oscillation are real devices here |
| Melody duration | 48.4 percent one sixteenth, 28.5 percent two sixteenths, 14.6 percent a quarter, 2.9 percent a half, 1.9 percent a dotted eighth | Half the surface is sixteenths, but quarters are a sixth of it |
| Duration pairs | 1 1 (50,743), 2 2 (25,685), 4 4 (10,616), 2 4 (3,200), 4 2 (3,170) | Rhythm is built in even runs, then a longer value ends them |
| Melody pitch | median 72, C5 | About one octave above the chord voice at 62 |
| Inner voice pitch | median 58, Bb3 | The counterpoint sits a ninth below the melody |
| Bass pitch | median 48, C3 | Bass is two octaves below the melody |

Motif repetition from the same file [C1]: of 16,975 one bar windows, 10,055 (59.23 percent) repeat a token that
occurs at least twice; median per piece 44.64 percent. At two bars, 7,073 of 16,311 windows (43.36 percent)
repeat, median per piece 22.72 percent. This is the single most usable number in the file: more than half of
the bars in this repertoire reuse another bar's rhythm and interval shape, and almost half do it at two bar
span. The style is far more repetitive than it sounds [inference].

### 2.5 Form and cadence

| Measure | Value | What it means |
| --- | --- | --- |
| Phrases | 1,078, mean 5.39 per piece | Short pieces with several phrases |
| Phrase length | median 7 bars, mean 17.57 bars per phrase | The median is the loop unit; the mean is dragged by sonata movements |
| Phrase length histogram | 16 bars 323 (30 pct), 2 bars 167, 1 bar 108, 3 bars 81, 4 bars 78, 5 bars 60, 8 bars 60 | A 16 bar phrase is the modal unit, and 8 bar periods are the second |
| Cadence kinds | other 44.1 pct, half 22.2, tonic prolongation 18.6, authentic 5.8, tonic other 2.6, plagal 2.1, predominant to tonic 2.0, minor plagal 1.5, deceptive 1.1 | Loops end on V or on the tonic being prolonged, not on a full stop |
| Cadence rate | 0.0569 per bar, 5.39 per piece | One cadence per 17.6 bars |

Caveat on the cadence table [inference]: the classifier reads only the last two bars of a phrase, so the 44.1
percent "other" is classifier uncertainty, not an absence of cadences. The usable signal is the ratio: half
cadence is 3.8 times as common as authentic, and that is the sound of an open loop.

### 2.6 The Mutopia study list, counted

The card points at `Shared\projects\arananet\pine\data\results\mutopia-list.json`, 28 qualifying pieces, all
28 shown as Public Domain on their own record pages, no files downloaded [C2]. Counted by type, because the
counts are the useful part:

| Group | Count | Why it matters to this lane |
| --- | --- | --- |
| Bach inventions | 11 (2, 3, 4, 5, 7, 8, 10, 11, 13, 14, 15) | The two voice model, and 11 is enough to see that the form is a template, not a one off |
| Bach dance movements | 3 (Minuet in A minor, Minuet in C minor, March in E flat) | 3/4 and duple dance cells at minuet tempo |
| Bach preludes and gigues | 6 | Sequence and arpeggio figuration, and the gigue's compound metre |
| Haydn minuets | 2 (Sonate I and II) | The Classical minuet pair: A and B sections plus trio |
| Mozart dance movements | 2 (Menuett K.V. 2, Gigue in G major) | A minuet and a compound metre dance side by side |
| Brahms waltzes | 2 (No. 10, No. 15) | The short waltz without introduction or coda |
| Chopin waltz | 1 (Op. 64 No. 1) | The waltz at its most decorated |
| Beethoven prelude | 1 (WoO 55) | A short free movement, useful as a cadence study |

`[inference]` What the counts say: 20 of 28 are Bach and 11 of those are inventions, so the public domain study
material for this lane is weighted towards exactly the texture the stock 2A03 can play. The waltz chain of
section 3.8 is represented by four pieces, none of which contains the five number Strauss chain, which is why
that form is documented from C16 rather than measured here.

---

## 3. Signature moves, with numbers

### 3.1 The invention: two lines, no answer needed

- An invention is a short keyboard piece in two part counterpoint; the exposition states a short motif in one
  voice in the tonic, the second voice takes it in the dominant while the first plays a countersubject or free
  counterpoint; the development alternates episodes with statements, reaching related keys through sequences
  and often a circle of fifths; the final episode ends on a half cadence so the returning subject sounds fresh;
  a recapitulation, if any, is two to four bars [C7].
- The difference from a fugue that matters on a chip: an invention usually has no separate answer form, and it
  is two voices, which is exactly the stock pulse budget [C7].
- Measured lengths: 11 Bach inventions in the corpus run 20 to 59 bars, median 25, median tempo 90 bpm [C1].
- `[inference]` Project recipe: subject of 1 bar (2 bars at slow tempo), entry delay 1 bar, answer at the
  octave or the fifth, episode 1 to 2 bars of sequence, three to five entries in 16 to 32 bars, and a half
  cadence two bars before the last entry.

### 3.2 The fugue subject, stripped to what the chip can use

- The subject is stated in imitation at different pitches; the exposition is complete when every voice has
  entered; episodes separate the later entries; the last entry returns to the tonic and Bach is the model [C25],
  and the same source is summarised at S18 in the style bible [C18].
- `[inference]` On two pulses a fugue can only be an invention with a subject of 1 to 2 bars, one answer at the
  fifth, and two episodes; three part entries need the VRC6. The subject has to state the tonic triad's third
  or fifth early so the answer's key is audible, and it must fit a ninth so it stays invertible.

### 3.3 The chaconne ground

- A chaconne is variation over a short repeated harmonic progression, often with a short repeating bass line
  that gives the harmonic outline for variation and figuration; it closely resembles the passacaglia, and the
  ground may descend from tonic to dominant with harmonies emphasising the circle of fifths [C8].
- Bach's Ciaccona, the last movement of the Violin Partita No. 2 in D minor, is 256 measures over a four bar
  phrase [C8]. Arithmetic from that: 64 statements of the ground [inference]. The earliest chaconnes are in
  triple metre, often starting on the second beat of the bar, with a four measure theme [C8].
- `[inference]` Project recipe: 4 bar ground on the triangle, 8 to 16 statements, the melody restated on every
  second statement so the ear gets the shape back after each decoration, and the major mode inserted for 4 bars
  in the middle third so the return reads as a return.

### 3.4 Sequence and ritornello drive (Handel, Vivaldi)

- A sequence restates a motif higher or lower in the same voice, usually two to four segments in one direction
  at the same interval distance; it can be real (exact transposition) or tonal (diatonic) [C22].
- In Vivaldi's ritornello conventions the opening ritornello is built from small units of two to four measures,
  later statements are partial (one or some of the units, sometimes varied), the first and last statements are
  in the tonic, at least one is in the dominant, and the ritornello does not return in the same key every time
  the way a Classical rondo refrain does [C15].
- `[inference]` Project recipe: a 2 bar cell, three to four statements stepping up a second or down a third
  each time, 4 to 8 bars total, one statement shifted to the dominant before the return; the accompanying
  bass moves by fifths under the static cell, which is what makes the sequence drive instead of stall.

### 3.5 The period (Mozart, Haydn)

- A period is an antecedent plus a consequent, about eight bars, with the antecedent ending in a weaker cadence
  (often half) and the consequent in a stronger one (often authentic) [C27, C23]; a phrase ends in a cadence and
  is often four bars in common practice [C28].
- `[inference]` Project template: bars 1 to 4 antecedent, same opening motif as the consequent, bars 5 to 8
  consequent, same motif with the last two notes changed so the cadence lands on I instead of V. The cheapest
  memorability trick in the whole repertoire is that the consequent differs from the antecedent in its last two
  bars only.

### 3.6 The sentence (the other Classical theme type)

- In the Schoenberg tradition a sentence is a basic motive, then a complementary repetition (the tonic version
  answered by a dominant version), then a continuation that reduces and condenses the material into a cadence;
  Schoenberg called the sentence a higher construction than the period because it starts developing at once
  [C11]. Macpherson's older sense, two balanced four bar phrases, is what modern theory calls a period [C11].
- `[inference]` Bar plan: 2 bars basic idea, 2 bars exact repetition up a step or down a third, then 4 bars of
  fragmentation: half bar units, then quarter bar units, then a cadence. That is 8 bars and it is the most
  accelerando-feeling device available without changing tempo, which is why it suits a battle cue.

### 3.7 Minuet and scherzo

- The minuet is normally 3/4, usually binary with two repeated sections of about eight bars, later a rounded
  binary A B A with a trio in the middle [C24]. Measured in genre pieces: 16 and 32 bar minuets are the norm,
  at 92 to 134 bpm [C1].
- The scherzo developed from the minuet and trio, keeps the triple metre and ternary shape, and is considerably
  quicker; its rounded binary becomes ABA with the trio and the return, sometimes ABABA; a 6/8 melody with one
  beat per bar is named as a main feature, and Beethoven in particular turned the polite minuet rhythm into an
  intense and sometimes savage dance [C9].
- `[inference]` Chip reading: minuet = triangle root on beat 1, two pulses on beats 2 and 3, noise almost
  absent. Scherzo = same grid at 168 to 200 bpm, offbeat pulse stabs on the second eighth of beat 3, noise on
  the third beat only, and a two bar cell instead of a four bar phrase.

### 3.8 The waltz chain (Chopin, Schubert, Brahms, Strauss)

- The waltz is in triple time, 3/4, a closed position couples dance from German speaking Europe in the 18th
  century [C4]. Slow waltz about 90 bpm, Viennese about 180 bpm [C5].
- Strauss's Blue Danube shows the full chain: an extended introduction in A major with tremolo violins and a
  horn stating the familiar waltz theme, answered by staccato wind chords; a contrasting quick phrase in D major
  anticipating the waltz; three quiet descending bass notes ushering in waltz 1; waltz 1A a gently rising triad
  motif in the tonic with the Viennese beat accentuated at the end of each three note phrase, then waltz 1B in
  the same key; waltz 2A quietly, with a contrasting middle in B flat; waltz 3A in G major, a fleeting melodic
  phrase as 3B, then an intrada in G minor; waltz 4A in F major, 4B in the same key; another short intrada
  cadencing in F sharp minor; waltz 5A in A, and 5B the climax with cymbal crashes; then a coda, which Strauss
  himself singled out [C16].
- `[inference]` The card's spec (introduction, waltz 1 to 5 at 16 bars each, coda) matches that description
  exactly once each waltz number is read as an A strain of 8 bars plus a B strain of 8 bars. Project bar
  budget: introduction 8 to 16, five waltzes at 16 bars each, up to two intradas of 4 to 8 bars, coda 8 to 16,
  total 120 to 137 bars. At 180 bpm that is 120 to 137 seconds, which is a full cue; at 104 it is 3.5 minutes,
  which is why a waltz cue for a game should sit at 150 to 180 or drop to three waltz numbers.

### 3.9 Oom pah, hemiola, rubato

- Oom pah: root on beat 1 in the bass, the chord on beats 2 and 3 in the upper voices [C4, C16]. On the chip the
  triangle takes the root and the two pulses take two chord tones, which means the chord on beats 2 and 3 has to
  be a dyad plus the triangle's held root [inference].
- Hemiola is the ratio 3:2: three beats of equal value in the time normally occupied by two, and it was common
  in Baroque dances including the minuet, with Bach's keyboard Partita No. 5 minuet given as an example of
  groups of two times three quavers that are really 6/8 inside a 3/4 notation [C3].
- `[inference]` Chip hemiola recipe, exactly: over two 3/4 bars the six beats regroup as three groups of two.
  Play the triangle on beats 1 and 4 (the two bar downbeats plus the second in each group), accent the pulse
  channel on 1, 3, 5 and let beats 2, 4, 6 be light. The ear hears 3 x 2 for two bars, then the 3/4 returns,
  and that is the cheapest large scale accent available without a tempo change.
- Rubato is expressive and rhythmic freedom by slight speeding up and then slowing down; in Chopin the melody
  may linger or anticipate while the accompaniment stays relatively in time, and 18th century practice included
  playing notes unevenly [C6].
- `[inference]` Frame budget for rubato: at 60 Hz one frame is 16.67 ms. A 4 percent tempo change at 104 bpm
  moves a beat from 577 ms to 554 ms, which is 1.4 frames; so a rubato that the ear can hear has to be at least
  2 frames per beat. Cap it at 3 frames per beat (about 5 percent) and only at phrase ends, on repeats, and at
  the waltz strain returns. Anything more reads as a broken engine, not as rubato.

### 3.10 How a classical theme stays in the head

Five devices, all measurable, all already in the hook grammar file [C19]:

1. **Motif first, tune second.** 59.2 percent of one bar windows in the corpus reuse another bar's token [C1],
   so the memorable unit is a bar, not a melody [inference].
2. **The consequent edits two bars.** Antecedent and consequent share the opening; the difference is the
   cadence, half against authentic [C27].
3. **A sequence of two to four statements, one direction, one interval** [C26], which gives the ear a rule it
   can predict and then a place where the rule breaks.
4. **Cadence type as punctuation:** half cadence to hold the loop open (22.2 percent of measured cadences),
   authentic to close it (5.8 percent) [C1].
5. **Octave placement:** melody median C5, bass median C3, two octaves apart [C1]; the range itself is part of
   the identity, and a chip cue that keeps the melody in the fourth octave loses it.

The hook grammar's own figures still apply: a hook is 8 to 18 notes over 2 to 4 bars, and listeners can name a
tune in about 5 seconds, with the fastest recognitions at 2.3 to 2.6 seconds [C19]. At 104 bpm in 3/4, 2 to 4
bars is 3.5 to 6.9 seconds [inference: 1.73 s per bar], so a waltz hook has to start inside bar 1.

---

## 4. Harmony: progressions by function, with bar counts

The numbers in brackets are the measured supports from [C1]; the bar counts are the project's operational
version [inference], sized so that a 16 bar phrase holds exactly two of them.

**Cadence frames (end of phrase, 1 to 2 bars).**

| Progression | Bars | Function | Measured support |
| --- | --- | --- | --- |
| I6/4, V7, I | 2 (6/4 half bar, V7 half bar, I one bar) | Cadential 6/4 then perfect cadence | I6/4 V7 I is the top trigram at 66 |
| V7, I | 1 to 2 | Plain authentic | Top bigram at 285 |
| V, i | 1 to 2 | Minor authentic | 150 |
| V, vi | half to 1 | Deceptive, keeps the loop open | 12 measured, rare on purpose |
| IV, I | 1 | Plagal, amen | 23 measured, plus 16 minor plagal |
| I, V | 2 | Half cadence, the open loop | Half cadence is 22.2 percent of all |

**Prolongation (the body of a phrase, 2 to 4 bars).**

| Progression | Bars | Function | Measured support |
| --- | --- | --- | --- |
| I, I6, I6/4, I | 4 (one chord per bar) | Tonic prolongation by inversion | I to I6 131, I6/4 to I 132, trigram I I6/4 I 55 |
| I, vi6/5, I, vi6/5 | 2 (half bar each) | Rocking inner voice over a pedal | I to vi6/5 118 |
| i, i6, i, V | 4 | Minor prolongation then half | i V i trigram 49 |
| I, IV, I, V | 4 | Primary triad shuttle | I to IV 136 |

**Motion (the driving middle, 2 to 8 bars).**

| Progression | Bars | Function | Measured support |
| --- | --- | --- | --- |
| I, IV, vii°, iii, vi, ii, V, I | 8 (one chord per bar) | Circle of fifths descent, the strongest sequence carrier | V to I and I to IV are the top measured motions; the fifths motion itself is the documented norm [C26] |
| ii, V, I | 2 to 3 | Predominant, dominant, tonic, the smallest complete motion | V7 I 285 plus IV family 3,180 |
| I, V, vi, iii, IV, I, IV, V | 8 (one chord per bar) | Ground bass / chaconne outline | Chaconne grounds emphasise the circle of fifths [C8] |
| I, vi, IV, V | 4 or 8 | Doo wop shuttle, the most singable frame | I to vi6/5 118, I to IV 136, V to I 285 |
| bVI, bIII, bVII, i | 4 | Minor plagal colour, heroic | bIII is 1.67 percent of labels, minor plagal cadence measured 16 |
| i, bVII, bVI, V | 4 | Andalusian descent, a sequence in itself | Descending stepwise roots mirror the top melody shape (down 2nd 11.36 percent) |

**Pivot and colour (1 to 2 bars, used once per 8).**

| Progression | Bars | Function | Measured support |
| --- | --- | --- | --- |
| V/V, V | 1 | Secondary dominant, the Classical sharp | Dominant sevenths are 10,129 of 60,127 chord beats |
| bIII as pivot to the relative major | 2 | The mode turn that makes a middle section | 1,005 labels |
| iv in a major key | 1 | Minor plagal colour, the "sad" borrowed chord | iv is 1,133 labels, 1.88 percent |
| Ger+6 or vii°7 to I | 1 | The one dramatic dissonance a cue gets | dim7 1,374 plus dim 3,772 |

Rules that hold across all four tables [inference, from C1's inversion counts]: second inversion is not a free
choice, it appears before a dominant or as a passing chord; a seventh resolves down by step; a diminished
label is followed within one bar by a chord containing its resolution note; and a sequence never changes its
interval distance mid run.

---

## 5. Ornaments, and how to render them on the 2A03 in frames

### 5.1 The four basic ornaments, defined

- **Trill.** Rapid alternation between an indicated note and the one above it, diatonic by default; a cadential
  trill belongs to the cadence; the rate need not be constant and can start slower and increase; at fast tempo
  or on a short note a trill can reduce to three notes, which makes it an upper mordent [C13]. Baroque and
  Classical practice often begins the trill on the upper auxiliary note [C14].
- **Mordent.** A single rapid alternation with the note above (upper) or below (lower), returning to the
  principal note; in the Baroque the plain mordent meant the lower one and the upper was called a pralltriller;
  in the 19th century usage the names swapped, and the lower mordent became the inverted mordent; Baroque
  mordents could on occasion take more than one alternation, making an inverted trill [C14].
- **Turn (gruppetto).** Four notes around the principal: upper, principal, lower, principal [C12, defining
  turns among the standard ornaments].
- **Appoggiatura.** An added non chord note on a strong beat that resolves to the chord note, one degree above
  or below, often chromatically altered, and it delays the principal note; the long appoggiatura takes its time
  from the principal, the short one is the acciaccatura; the double appoggiatura is two small notes, the second
  one degree from the principal, and in all cases the time comes out of the principal note [C10].
- Performance context: ornamentation was expected from a Baroque keyboard player and was partly improvised,
  with the repeat of a da capo section more decorated than its first statement [C12, C13].

### 5.2 Frame arithmetic

At 60 Hz the frame counter clocks envelopes and the triangle's linear counter at about 240 Hz, length and
sweep at about 120 Hz, and can raise a 60 Hz interrupt [C17]. A note therefore has 16.67 ms resolution
[inference from C17]. Frames per note value:

| BPM | 16th | 32nd | 64th | 3/4 bar |
| --- | --- | --- | --- | --- |
| 60 | 15.0 | 7.5 | 3.75 | 3.00 s |
| 72 | 12.5 | 6.25 | 3.12 | 2.50 s |
| 84 | 10.7 | 5.36 | 2.68 | 2.14 s |
| 90 | 10.0 | 5.00 | 2.50 | 2.00 s |
| 100 | 9.0 | 4.50 | 2.25 | 1.80 s |
| 104 | 8.65 | 4.33 | 2.16 | 1.73 s |
| 112 | 8.04 | 4.02 | 2.01 | 1.61 s |
| 120 | 7.50 | 3.75 | 1.87 | 1.50 s |
| 132 | 6.82 | 3.41 | 1.70 | 1.36 s |
| 144 | 6.25 | 3.12 | 1.56 | 1.25 s |
| 168 | 5.36 | 2.68 | 1.34 | 1.07 s |
| 180 | 5.00 | 2.50 | 1.25 | 1.00 s |
| 200 | 4.50 | 2.25 | 1.12 | 0.90 s |

Closed forms, so the arranger can compute any tempo: frames per 16th = 900 divided by bpm; frames per 32nd =
450 divided by bpm; frames per 64th = 225 divided by bpm. At 60 Hz nothing under 2 frames is playable as a
distinct note, which is the hard wall: a 64th rate ornament needs 3 frames per note from about 75 bpm upward,
and a 32nd rate trill needs 3 to 5 frames.

### 5.3 Rendering rules per ornament

| Ornament | Note sequence | Rate to use | Frames at 104 bpm | Constraint |
| --- | --- | --- | --- | --- |
| Trill | principal, upper, repeat, end on principal | 32nd, 4 frames minimum | 4 to 5 | Only on the melody pulse; the other pulse must not be playing a note the trill collides with |
| Mordent, upper | principal, upper, principal | 64th, 2 frames each is 6 total | 2, 2, 2 | Needs the note to be at least 6 frames long; below that use 3 frames of principal and skip it |
| Mordent, lower | principal, lower, principal | same | same | Same |
| Turn | upper, principal, lower, principal | 64th | 2 each, 8 total | Play at the end of a long note, never inside a run |
| Appoggiatura, long | auxiliary on the beat, then principal | half the principal's value | half | Auxiliary must be a scale step and must be one of the two worst notes against the chord, resolved on the beat |
| Appoggiatura, short | one grace note, 1 to 2 frames | 1 to 2 frames | 1 to 2 | Below 2 frames it is a click; drop it or lengthen |
| Cadential trill | trill on the leading tone or second degree for 1 to 2 beats, ending with a turn | 32nd, then 64th | 4 to 5 then 2 | Ends on the tonic at the moment the bass lands on I |

Three chip specific facts that decide whether an ornament reads as an ornament [inference, from C17 and the
project's own renderer notes]: (1) writing the high period byte resets the pulse phase and pops, so a trill has
to move only the low byte; (2) volume is 4 bits, so an ornament can be shaped by dropping volume one step on
the auxiliary rather than changing pitch rate; (3) the triangle has no volume, so a triangle ornament reads
only as pitch, which is why ornaments belong on the pulses and the triangle keeps the ground.

### 5.4 Ornament budget

`[inference]` Measured basis: the corpus melody is 48.4 percent sixteenths already [C1], so there is little
room for added notes before the line turns to mud. Rule: at most one ornament per 2 bars, at most three per
8 bar period, and never on two channels in the same beat. Ornaments go on the first note of a strain, the last
note before a cadence, and on the repeat of a strain, mirroring the documented practice of decorating the
repeat more than the first statement [C12].

---

## 6. Counterpoint on two pulse channels

The chip constraint first: two pulses at the same duty and similar volume fuse into one timbre, and parallel
motion in thirds or sixths at that point stops being two voices [C18 entry for counterpoint; wiki page [C29]].

Rules, in priority order [inference, built from C29, C7 and the corpus pitch data in C1]:

1. **Rhythmic independence over pitch independence.** When one voice moves in eighths, the other moves in
   quarters or holds. Two voices moving in the same rhythm are one voice with a chorus effect.
2. **Contrary motion as the default.** When both move, at least one of the intervals must be a step and the
   direction must oppose. Parallel perfect fifths and octaves between the two pulses are out: they collapse
   into one pitch class identity and they also beat badly on the pulse timbre.
3. **Different duty cycles.** Pulse 1 at 50 percent (the round, loud one) for the subject, pulse 2 at 12.5 or
   25 percent for the countersubject; the timbre difference is what lets the ear follow two lines at once.
4. **Octave discipline.** Melody median 72 and inner median 58 in the corpus [C1]; keep the two pulses 7 to 12
   semitones apart and let them cross for at most two notes.
5. **Invertibility test.** Swap the two lines. If the result has a parallel fifth or an unusable range, the
   counterpoint fails; that test is cheap and catches most bad two voice writing before rendering.
6. **Unison is a landing, not a resting place.** Two pulses on the same pitch for more than 4 frames at 60 Hz
   (67 ms) reads as one detuned note.
7. **Entry discipline.** Subject 1 to 2 bars, entry delay 1 bar (2 at 80 bpm or slower), answer at the octave
   or the fifth, one entry per 4 to 8 bars, and a half cadence 2 bars before the final entry [C7].
8. **Echo is free polyphony.** Pulse 2 repeating pulse 1 three frames later at half volume creates depth
   without a third voice; use it on one statement only, or the trick becomes the texture [C19, the chip echo
   recipe].

With VRC6 the budget becomes four melodic voices plus saw [C18 section 10.3 for the chip's own description of
the VRC6]: then a three voice invention is legal, the saw takes the ground or the pad, and rules 1 to 5 still
apply pairwise, because the VRC6 pulses have the same fusing problem.

---

## 7. Instrument assignment on 2A03 and VRC6

| Role | Stock 2A03 | VRC6 build | Notes |
| --- | --- | --- | --- |
| Subject or melody | pulse 1, 50 percent duty, volume 12 to 15 | pulse 1, or VRC6 pulse 1 for a thinner sound | The melody owns the 32nd rate ornaments |
| Countersubject or answer | pulse 2, 12.5 or 25 percent, volume 8 to 10 | pulse 2 or VRC6 pulse 2 | Never the same duty as the melody |
| Ground bass or root | triangle, always, one note at a time | triangle, or VRC6 saw for a sustained pad | Triangle has no volume: it is the foundation, not a voice [C18 10.2] |
| Broken chord (Alberti, oom pah chord) | pulse 2 arpeggiating, 4 notes per bar in eighths | VRC6 pulse 2 plus saw stabs | Cheapest Classical texture the chip can play [C18 11.2] |
| Echo or shadow | pulse 2 delayed 3 frames, half volume | VRC6 pulse 2 | One statement only |
| Timpani or drum | noise, low rate index, 2 to 4 frame decay | same, or saw thump | Classical has no kit: noise is punctuation |
| Big hall | VRC6 saw pad at low volume | saw | The style tolerates a pad more than rock does |

Percussion habits by era, since the card asks for drum and bass habits and the era has none [inference]:
Baroque is bass driven, no drums, and the bass is a ground; add noise only for a dance's downbeat, 2 frames at
low volume. Classical uses timpani on tonic and dominant only, so noise on beats 1 of bars 1 and 5 of a period.
Waltz uses no kit at all: the oom pah is the percussion, and if a drum is wanted it is a light brush on beat 2
at 25 percent volume. The measured corpus has no drum data at all because the repertoire has no kit [C1].

---

## 8. Human touches, and the exact size of each

| Touch | Where | Size, in frames or percent |
| --- | --- | --- |
| Rubato | Last 2 beats of a phrase, and strain repeats | 2 to 3 frames per beat late or early, never more than 5 percent of tempo |
| Late entry of the answer | Every answer | 1 to 2 frames after the beat, once per entry, not every entry |
| Ornament on the repeat | Repeat of an 8 bar strain | 1 ornament per 2 bars on the repeat, none on the first pass |
| Gate length | All melodic notes | 80 to 92 percent of the written value, so notes breathe; legato only inside a slurred pair |
| Volume shaping | Each 4 bar phrase | Start at 10, peak 14 in bar 3, end 11; a 4 bit ramp is 4 steps and is audible |
| Vibrato | Long notes over 8 frames | Depth 1 to 3 period units on the low byte only, starting 4 frames after the attack |
| Duty change mid note | Climax note of a strain | 50 to 25 percent at the halfway frame of the note, once per cue |
| Hemiola | Last 2 bars before the coda | Triangle on beats 1 and 4 only |
| Cadential trill | 1 to 2 beats before I | 32nd rate for 4 frames each, ending with a 2 frame turn |
| Noise decay | Timpani hits | 2 to 4 frames total, no tail |
| Silence | Before the final I | Drop all channels for 3 to 6 frames, once per cue |
| Tempo | Whole cue | One tempo; rubato supplies the variation, because a chip engine that changes tempo globally sounds broken |

Anti list, from the same evidence: no exact quantization of every note to the grid with no gate variation, no
ornament on every note, no vibrato from the attack, no rubato on a loop point (it desynchronises the loop), no
parallel thirds between the two pulses for more than one bar, no 64th rate ornament below 75 bpm, and no
change of tempo mid-loop.

---

## 9. What to avoid in this style

1. **Do not write this style at NES rock tempo.** The corpus median is 90 bpm and the 3/4 median 104 [C1]; a
   150 bpm minuet is a scherzo whether or not it is labelled one.
2. **Do not put the melody in the fourth octave.** Melody median is C5 with the bass at C3 [C1]; dropping the
   tune an octave destroys the identity more than any wrong chord does.
3. **Do not cadence every four bars.** Authentic cadences are 5.8 percent of measured cadences [C1]; the loop
   works because it ends on V or on a prolonged tonic.
4. **Do not stack thirds on one pulse.** A chord that is not an arpeggio has to be split across channels; a
   three note stack on one pulse is either an arpeggio or an inaudible mud [C18 chip section, C30].
5. **Do not sequence without a target.** A sequence is 2 to 4 segments at one interval [C26]; more than four
   stops being a sequence and becomes a chromatic walk.
6. **Do not ornament on the beat in every bar.** Baroque practice decorates repeats [C12]; constant ornament is
   a different, later style.
7. **Do not use hemiola as a whole section.** It is a two bar event at a phrase end [C3].
8. **Do not use a full authentic cadence plus a cymbal crash on a town loop.** Reserve the full close and the
   noise hit for the ending cue.

---

## 10. Ten listening notes

Bar numbers are section boundaries taken from the published form descriptions, or the measured bar totals in
[C1]; nothing here is a transcription, and where a number is approximate it is marked so.

1. **Bach, Ciaccona, Violin Partita No. 2 in D minor.** 256 bars over a 4 bar ground, so 64 statements [C8].
   Listen to bars 1 to 8: the ground twice, unchanged harmonically, the melody completely different each time.
   Then listen to the major mode passage in the middle third (roughly bars 129 to 192) and notice that the
   ground is still the same four bars underneath. That is the whole lesson: the ground carries identity, the
   surface carries interest.
2. **Bach, Invention 10 in G major, 9/8, 32 bars.** Measured at 172 bpm in the corpus [C1]. Listen to the first
   two bars only: one voice states a short figure, and by the end of bar 2 the other has answered. Then find
   the moment the sixteenth motion stops for a bar; that silence is the half cadence before the last entry
   [C7].
3. **Bach, Invention 2 in C minor, 4/4, 27 bars at 64 bpm** [C1]. At this tempo the entry delay is 2 bars, so
   the answer arrives late enough to be heard as an answer and not as an echo. Compare bars 1 to 4 with
   Inventions 10's first four: same machinery, different density.
4. **Bach, Invention 13 in A minor, 4/4, 25 bars at 100 bpm** [C1]. The shortest of the set in the corpus, and
   the best model for a 16 bar chip loop: subject, answer, two episodes, one return.
5. **Bach, Minuet in A minor, 3/4, 28 bars at 80 bpm** [C1]. Listen for the two bar phrase pairs and the
   cadence at bar 8 and bar 16: the first leaves the door open, the second closes it [C27]. This is a period
   you can count on your fingers, which is why it belongs in the town cue.
6. **Mozart, 12 Duets No. 11 Menuetto, C major, 3/4, 32 bars at 120 bpm** [C1]. Two voices only, so it is the
   model for two pulses. In each 8 bar section find the bar where both voices stop being rhythmically
   independent; that is the cadence, and there should be exactly two per 16 bars.
7. **Haydn, Sonate I Menuetto, G major, 3/4, 66 bars at 92 bpm** [C1]. The minuet that is nearly a scherzo:
   the joke is a two bar cell repeated with one note changed [C9]. Listen to how little material there is.
8. **Beethoven, Quartet No. 4 in C minor, third movement Menuetto, 3/4, 167 bars** [C1, read at 192 bpm]. The
   measured tempo is nearly double Haydn's, and that difference is the scherzo arriving. Listen to the trio
   section for the change of key and texture, then to the return of the opening, which is where the ternary
   shape does its work [C9].
9. **Chopin, Waltz Op. 64 No. 1, 3/4, 140 bars** [C1; the corpus reads the key as F minor while the piece is
   commonly in D flat major, a detector artifact noted in section 2.2]. Listen only for the accompaniment:
   bass on beat 1, chord on 2 and 3, and in the B section how the chord on beat 2 arrives a frame or two early,
   which is the rubato that makes it breathe [C6].
10. **J. Strauss II, The Blue Danube, Op. 314.** The full chain in one piece: introduction in A major, waltz 1
    in D major with the rising triad motif and its B strain in the same key, waltz 2 with a B flat middle,
    waltz 3 in G major followed by an intrada in G minor, waltz 4 in F major, waltz 5 in A with the climax in
    5B, then the coda [C16]. Listen for the three descending bass notes that usher in waltz 1 and count how
    many bars pass between the last waltz strain and the coda: that gap is the one a game cue has to cut.

A sixth bonus, because the corpus has one: **Brahms, Waltz No. 15 in A flat, 3/4, 44 bars at 116 bpm** [C1].
Two bar phrases throughout, no introduction, no coda. That is what a waltz looks like when it has to fit in 8
bars of game music.

---

## 11. Recipe families in `data/recipes/classical.json`

Thirty recipes, ids CLC-01 to CLC-30, in seven families. The file is the executable half of this document; the
section numbers below say where each family's numbers come from.

| Family | Count | What it covers | Section here |
| --- | --- | --- | --- |
| INV | 6 | Invention and fugue subject, answer, entry delay, episode, three voice version on VRC6 | 3.1, 3.2, 6 |
| GRD | 4 | Chaconne ground, passacaglia variant, ground with a mode turn, ground as a waltz bass | 3.3, 5 |
| SEQ | 4 | Sequence cell, circle of fifths drive, ritornello return, episode | 3.4, 4 |
| PER | 6 | Period, sentence, minuet, scherzo, Alberti bass, cadence frames | 3.5 to 3.7, 4 |
| WZ | 5 | Waltz chain, oom pah, hemiola, rubato, coda | 3.8, 3.9 |
| ORN | 3 | Trill, mordent and turn, appoggiatura, all frame timed | 5 |
| MEM | 2 | Hook construction for this style, and the human touch bundle | 3.10, 8 |

Every recipe carries `when_to_use`, `params`, `forbidden` and `source`, and the param names match the tokens
already used by the arranger (`subject_bars`, `entry_delay_bars`, `entry_interval`, `episode_bars`,
`sequence_segments`, `ground_bars`, `ornament_rate`, `cadence_a`, `cadence_b`, `phrase_bars`, `form`,
`gate_pct`, `decay_frames`) so the build script can read them the same way it reads the other scopes.

---

## 12. Where this style goes in the game

`[inference]` Four placements, chosen so the style earns its keep instead of being wallpaper:

- **Town, menu, shop:** a two voice invention digest at 90 to 104 bpm, 16 bars, triangle ground, no drums, one
  ornament per 2 bars on the second pass. Cheapest possible texture: two pulses and a triangle.
- **Court or library scene:** minuet, 3/4 at 120, 16 bar binary with a repeat, noise on beat 1 of bars 1 and 5
  only.
- **Ballroom or waltz scene, and the title theme:** the waltz chain at 104 (title, already in score.yaml) or
  180 (a party scene), three waltz numbers for a game loop, five for a set piece.
- **Boss or chase:** scherzo, 3/4 or 6/8 at 168 to 200, two bar cell, sequence of three, hemiola in the last two
  bars before the loop point.

---

## 13. Sources

All read or generated on 2026-10-21. Links were fetched live that day; the corpus and Mutopia files are local.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| C1 | Corpus statistics, `D:\Musikage-Corpus\style-pp\stats\classical.json` (schema musikage-style-pp/1, generated 2026-10-21T22:56:28, 200 pieces) | local file | Every measured number in sections 2, 3 and 4; licence counts; motif repetition; cadence kinds |
| C2 | Mutopia Project, public domain editions | https://www.mutopiaproject.org | The 200 piece corpus source, and the 28 piece study list at `Shared\projects\arananet\pine\data\results\mutopia-list.json` (28 of 28 shown as Public Domain) |
| C3 | Wikipedia, "Hemiola" | https://en.wikipedia.org/wiki/Hemiola | The 3:2 ratio, three in the time of two, use in Baroque dances including the minuet, the Bach Partita No. 5 minuet example |
| C4 | Wikipedia, "Waltz" | https://en.wikipedia.org/wiki/Waltz | 3/4, closed position, 18th century German speaking origin, the ländler lineage |
| C5 | Wikipedia, "Viennese waltz" | https://en.wikipedia.org/wiki/Viennese_waltz | Slow waltz about 90 beats and 30 measures per minute, Viennese about 180 beats and 58 to 60 measures |
| C6 | Wikipedia, "Tempo rubato" | https://en.wikipedia.org/wiki/Tempo_rubato | Speeding up then slowing; Chopin melody lingering or anticipating while the accompaniment holds time; 18th century uneven-note practice |
| C7 | Wikipedia, "Invention (musical composition)" | https://en.wikipedia.org/wiki/Invention_(musical_composition) | Two part counterpoint, exposition, development by episodes and sequences through the circle of fifths, half cadence before the final return, no separate answer form |
| C8 | Wikipedia, "Chaconne" | https://en.wikipedia.org/wiki/Chaconne | Variation over a repeated harmonic ground, the descending bass and circle of fifths outline, Bach's 256 bar Ciaccona over a four bar phrase, triple metre and second-beat openings in early examples |
| C9 | Wikipedia, "Scherzo" | https://en.wikipedia.org/wiki/Scherzo | Origin from minuet and trio, triple metre kept, considerably quicker, rounded binary plus trio, 6/8 one beat per bar, Beethoven intensifying the minuet rhythm |
| C10 | Wikipedia, "Appoggiatura" | https://en.wikipedia.org/wiki/Appoggiatura | Non chord note on a strong beat resolving to the chord note, one degree above or below, long versus short form, time taken from the principal note, double appoggiatura |
| C11 | Wikipedia, "Sentence (music)" | https://en.wikipedia.org/wiki/Sentence_(music) | Schoenberg's basic motive plus complementary repetition plus reduction and liquidation; Macpherson's duple sentence 4 plus 4 with half then perfect cadence |
| C12 | Wikipedia, "Ornament (music)" | https://en.wikipedia.org/wiki/Ornament_(music) | Baroque improvised ornamentation, the harpsichord player expected to improvise trills, mordents and appoggiaturas, more decoration on the da capo repeat, turns among the standard ornaments |
| C13 | Wikipedia, "Trill (music)" | https://en.wikipedia.org/wiki/Trill_(music) | Rapid alternation with the note above, diatonic by default, cadential trill, rate may start slower, three note reduction at fast tempo, ending with a turn |
| C14 | Wikipedia, "Mordent" | https://en.wikipedia.org/wiki/Mordent | Single rapid alternation above or below and back, Baroque lower versus modern upper, inverted mordent, occasional multiple alternations |
| C15 | Wikipedia, "Ritornello" | https://en.wikipedia.org/wiki/Ritornello | Vivaldi's conventions: units of two to four measures, partial returns, first and last in the tonic, at least one in the dominant |
| C16 | Wikipedia, "The Blue Danube" | https://en.wikipedia.org/wiki/The_Blue_Danube | The full waltz chain: extended introduction in A major, waltz 1 to 5 with A and B strains and their keys, intradas, waltz 5B as the climax, the coda, the rising triad cello and horn motif, three descending bass notes into waltz 1 |
| C17 | NESdev Wiki, "APU Frame Counter" | https://www.nesdev.org/wiki/APU_Frame_Counter | Quarter frame about 240 Hz, half frame about 120 Hz, frame interrupt about 60 Hz, the 4 step and 5 step sequences |
| C18 | This project, `knowledge/MUSIC-STYLE-BIBLE.md` (internal, 2026-10-21) | local file | Chip constraints for two voice writing, the VRC6 budget, the rule that a chord is an interval, the trade-off table, its source ids S1 to S28 for the chip and theory pages |
| C19 | This project, `knowledge/MUSIC-HOOK-GRAMMAR.md` (internal, 2026-10-21) | local file | Hook length 8 to 18 notes over 2 to 4 bars, about 5 second recognition with 2.29 to 2.62 s fastest, the humanness gestures and the chip echo recipe |
| C20 | This project, `knowledge/MUSIC-DRUMS.md` (internal, 2026-10-21) | local file | The waltz feels and the 3/4 grids this lane's percussion borrows |
| C21 | This project, `knowledge/MUSIC-DISSONANCE.md` (internal, 2026-10-21) | local file | The dissonance devices and rates that the section 2.3 budget cross-checks against |
| C22 | Wikipedia, "Sequence (music)" | https://en.wikipedia.org/wiki/Sequence | Restatement of a motif at another pitch in the same voice, two to four segments, one direction, same interval, real versus tonal |
| C23 | Wikipedia, "Cadence" | https://en.wikipedia.org/wiki/Cadence | Authentic, half, plagal and deceptive definitions with chord motions |
| C24 | Wikipedia, "Minuet" | https://en.wikipedia.org/wiki/Minuet | 3/4, binary with two repeated eight bar sections, later rounded binary with a trio |
| C25 | Wikipedia, "Fugue" | https://en.wikipedia.org/wiki/Fugue | Subject stated in imitation at different pitches, exposition complete at the last entry, episodes, final entry in the tonic |
| C26 | Wikipedia, "Circle of fifths" | https://en.wikipedia.org/wiki/Circle_of_fifths | Progressions move between roots a fifth apart; modulation to a neighbouring key |
| C27 | Wikipedia, "Period (music)" | https://en.wikipedia.org/wiki/Period_(music) | Antecedent plus consequent, about eight bars, weak then strong cadence |
| C28 | Wikipedia, "Phrase (music)" | https://en.wikipedia.org/wiki/Phrase_(music) | A phrase ends in a cadence and is often four bars |
| C29 | Wikipedia, "Counterpoint" | https://en.wikipedia.org/wiki/Counterpoint | Independent lines, harmonic dependence, parallel perfect intervals treated as a fault |
| C30 | Wikipedia, "Chiptune" | https://en.wikipedia.org/wiki/Chiptune | The quick arpeggio as the standard way to imply a chord with few voices |

Notes on sourcing: the corpus file is ours, generated from public domain editions under the Mutopia licence
lines recorded per file [C1, C2]; nothing from IMSLP is claimed in that file. The Wikipedia pages are used for
form descriptions and standard definitions only, never for a melody. Section 2.2 caveats the key detector, and
section 2.5 caveats the cadence classifier, because both are the weakest instruments in the measurement.

---

## 14. Limits of this file

1. The corpus is 200 pieces with Bach at 45 and Strauss, Handel and Vivaldi at zero [C1]. Everything measured
   about Baroque sequence drive and about the Viennese waltz chain comes from form descriptions [C15, C16], not
   from measurement.
2. The tempo figures are the typesetters' playback tempi recorded in each MIDI file, 73 distinct values, not
   historical performance tempi [C1]. Use them as a distribution; use C5 and C9 for dance conventions.
3. The key detector is a correlation fit and is demonstrably wrong on at least one famous piece [C1, section
   2.2].
4. The cadence classifier reads only the last two bars of a phrase, so 44.1 percent "other" is uncertainty
   [C1, section 2.5].
5. No claim here is a statement about how a specific recording of a specific work sounds. The listening notes
   name sections and bar counts from published form descriptions; a listener's ear will be the check, not this
   table.
6. Ornament rates on real instruments are not fixed; the frame table in section 5.2 is the chip's approximation
   of a practice that was itself partly improvised [C12, C13].
