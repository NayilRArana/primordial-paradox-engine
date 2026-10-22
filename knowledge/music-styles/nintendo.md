# Nintendo first-party NES: Mario, Zelda, Metroid, Kid Icarus and the Tanaka and Kondo hooks

Card t_90f62589 (STUDY-NINTENDO), written by the audit lane, 2026-10-21. Scope name `nintendo`.
Companion files: `knowledge/MUSIC-HOOK-GRAMMAR.md`, `knowledge/MUSIC-STYLE-BIBLE.md`,
`knowledge/MUSIC-DRUMS.md`, and the executable recipes in `data/recipes/nintendo.json`.

Reference rule (`PLAN-V2-2026-10-21.md` section 0): these games were studied from published interviews, credit
records, wiki hardware documentation, crowd-sourced theory tabs and measured corpus statistics.
Nothing was downloaded, ripped, sampled, traced or decompiled. No melody is written out anywhere in
this file; every musical statement is a shape, a scale degree, an interval or a count.

Tagging. Every claim ends with a source id in square brackets, for example [N7]. Section 13 has the
link and the read date for each id, and section 14 states what could not be checked. `[inference]`
marks my own operationalisation of a source, written so the arranger has a number to hit.

---

## 1. Who wrote what, and three corrections to the card

- Super Mario Bros (NES, 1985) is Koji Kondo alone, six themes, including the players' jump and
  coin sound effects, written in his second year at Nintendo [N1, N2].
- The Legend of Zelda (FDS, 1986) is Koji Kondo, credited in game as "Konchan" [N6].
- Zelda II: The Adventure of Link (FDS, 1987) is **Akito Nakatsuka alone**, credited as "Tsukasan"
  [N7, N8]. The card credits it to Kondo and Nakatsuka; every source I read gives Nakatsuka sole
  credit, and the enjoygamejapan creator page states he composed Zelda II, Devil World, Ice Climber
  and Punch-Out!! [N8].
- Metroid (FDS, 1986) and Kid Icarus (FDS, 1986) are Hirokazu "Hip" Tanaka [N3, N4, N5]. Kid Icarus
  music is credited to Tanaka alone in the game and in the Famicom 20th Anniversary credits [N5].
- Tetris (NES, 1989), Dr. Mario (NES, 1990) and Mother are Tanaka's too [N3]. The NES Tetris Type A
  is an arrangement of the 19th century Russian folk song Korobeiniki, that is, a public domain tune
  arranged on the chip rather than a composed theme (unverified in this run; no source page fetched).
- Punch-Out!! (NES): the 1987 NES soundtrack, including Mike Tyson's Punch-Out!!, is credited to
  Akito Nakatsuka [N8]. The card gives Tanaka; I could not find Tanaka on that credit and I am not
  asserting he is absent, only that the source I read names Nakatsuka (unverified beyond [N8]).
- "Naoki Tomita" in the card does not appear in any credit record I read for Super Mario Bros 1 to 3
  (unverified; no source found). Super Mario Bros 3 (1988) is credited to Koji Kondo in the material
  I could reach (unverified in this run; not fetched).
- Why this matters to the recipes: two composers with opposite instincts share this scope. Kondo
  writes a bright, rhythm-first, major-key hook that has to sit under a running character; Tanaka
  writes atmosphere first, refuses "the same game-melody cliches", and deliberately withholds a
  strong melody until the player has earned it [N2, N4]. The recipe file therefore has two families,
  a bright Kondo path and a dark Tanaka path, plus the shared chip craft both used.

---

## 2. The measured facts

### 2.1 What I measured on this machine

Source: `D:\Musikage-Corpus\style-pp\stats\nintendo.json`, generated 2026-10-21 by
`style-pp/tools/nintendo_stats.py` from 132 NES-MDB MIDI pieces across nine games, using the
measurement functions of `build_style_corpus.py` unmodified [N20]. This is the only place in this
file where the numbers are ours rather than quoted.

| Measure | Value | What it means for us |
| --- | --- | --- |
| Pieces measured | 132 (SMB 20, Zelda 11, Zelda II 17, Metroid 12, Kid Icarus 12, Tetris 16, Dr. Mario 11, Punch-Out 28, Mario Bros 5) | Small but every scope game except SMB2 and SMB3 is represented |
| Mode | major 94, minor 38 (71 percent major) | The opposite of the Konami scope, where 13 of 16 were minor. Nintendo first party is a **major-key** style [N20] |
| Tonic histogram | C 38, G 15, F 12, A minor 12, Bb 7, C minor 6, G minor 6 | C is a fifth of the whole scope. C major is the house key, not a coincidence [N20] |
| Key fit quality | mean Krumhansl correlation 0.768, 35 pieces below 0.7 | A quarter of the pieces are weakly tonal by this detector; do not quote single-piece keys as fact [N20] |
| Chord changes | 3.85 per bar, 6588 chord-beats | Harmony moves as fast here as in the Konami scope (3.78) [N20] |
| Chord qualities | maj 1659, min 965, sus4 929, min7 889, maj7 612, 7 571, dim 360, hdim7 347, aug 117 | Sus4 is the third most common quality: the NES arpeggio writes it constantly [N20] |
| Melody intervals (11554) | unison 15.0 percent, down minor 2nd 12.7, up minor 2nd 11.7, down major 2nd 10.6, up major 2nd 10.3 | Half of all melodic moves are within a whole tone of the previous note [N20] |
| Step to leap | 60.3 percent steps, 39.7 percent leaps, only 1.5 percent wider than 19 semitones | More stepwise than Konami (51.6 percent steps) and with almost no wild jumps [N20] |
| Common 2, 3 and 4 shapes | 0 0, +1 -1, -1 +1, +2 -2; 0 0 0, +1 -1 +1, -1 +1 -1; 0 0 0 0, +1 -1 +1 -1 | The style's micro-shape is **repetition of one pitch and oscillation around it**, not the leap [N20] |
| Melody range | median 18 semitones (Konami: 41 to 45) | Hooks are written in a narrow band; the octave-plus range of Castlevania is absent [N20] |
| Melody note durations | single 16th 67.0 percent, two 16ths 11.8, three 16ths 8.0, quarter 4.9 | Sixteenth surface, but less relentlessly than Konami's 76 percent [N20] |
| Durations by game | SMB 89.4 percent single 16ths, Dr. Mario 85.3, Punch-Out 72.4, Kid Icarus 70.0, Tetris 69.2, Metroid 52.1, Zelda 28.8, Zelda II 26.7 | Two distinct surfaces: Kondo's sixteenth machine and the Zelda and Metroid long-note style [N20] |
| Melody density | 6.65 melody notes per bar | About one and a half notes per beat on average [N20] |
| Onset gaps | 1 16th 1 16th (4475), 2 2 (1808), then a long tail | Straight eighths and straight sixteenth runs, no shuffle in the token stream [N20] |
| Voice roles | inner 204, melody 132, bass 51; median pitches melody 72 (C5), inner 61.8, bass 45 (A2) | Melody sits 27 semitones above the bass, and every piece has an inner voice [N20] |
| Voices per piece | median 3 | Three pitched parts plus noise. Two of the five channels are usually free for effects [N20] |
| Most common chords | I 470, i 344, Vsus4 329, I6/4 268, I6 161, Isus4 154, IV 152, V 120 | Tonic and second-inversion tonic dominate; I6/4 is a **pedal**, not an inversion curiosity [N20] |
| Chord bigrams | I I 237, i i 235, Vsus4 Vsus4 229, I6/4 I6/4 136 | Chords are held, not churned, even though the harmonic rhythm is fast: the same label repeats for 2 to 4 beats [N20] |

Two ways this corpus misleads, stated so nobody quotes it carelessly [inference]:
1. Tempo is useless here: every one of the 132 files reads 120 bpm, because NES-MDB normalises it
   [N20]. Every tempo in this file is either quoted from a published tab [N9, N10, N11] or marked
   as inference.
2. Median piece length is short because many files are single jingles (Punch-Out median 3 bars).
   Length statistics must be read per cue type, not as a scope average [N20].

### 2.2 Quoted measurements from published theory tabs

These carry real tempo, key and meter, and they are the numbers the recipes lean on [N9, N10, N11, N12].

| Track | Key and mode | Tempo | Meter | Melody range | Complexity readings |
| --- | --- | --- | --- | --- | --- |
| Super Mario Bros, Overworld | C major | 200 bpm in the tab (eighth-note pulse; Wikipedia states 100 bpm with swing) | 4/4 | C2 to C6, 48 semitones | melodic 97, chord 45, chord-melody tension 96, novelty 44, most used I [N9, N1] |
| The Legend of Zelda, Overworld | Bb Mixolydian | 152 bpm | **12/8** | F4 to Bb5 | chord 88, melodic 86, tension 51, novelty 92, chord-bass melody 94, most used I [N10] |
| The Legend of Zelda, Main Theme tab (separate entry) | Bb minor | 92 bpm | 4/4 | F4 to Db6 | chord 92, melodic 91, tension 29, novelty 78, most used VI [N11] |
| Metroid, Brinstar (chorus) | G minor | 151 bpm | **12/8** | C4 to F#5, 18 semitones | chord 95, melodic 99, tension 8, novelty 95, 85 percent chord tones, 4 or more beats per note [N12] |

Three facts jump out of that table, and they set up the whole document:
- Mario and Metroid are the same era and the same chip and they are opposites. Mario's tab scores a
  chord-melody tension of 96 over simple harmony (chord complexity 45): the tune fights the chords.
  Brinstar scores tension 8 over dense harmony (95) with long notes: the tune sits on the chords and
  the harmony does the work [N9, N12]. These are the two hooks in this scope and they are different
  mechanisms, not different moods.
- Zelda and Metroid are both **12/8 at 151 to 152 bpm** in the published tabs, while Mario is 4/4 at
  100 (or 200 counted in eighths) [N9, N10, N12]. Compound metre is a first-party NES habit, not an
  exception, and it is the honest answer to "swing on a rigid chip": write the compound grouping into
  the notation instead of trying to make the APU swing.
- The narrow melody range (18 semitones in Brinstar, 7 in the Zelda overworld tab's verse) matches
  the corpus median of 18 semitones. Mario's tab range of 48 is the outlier and it comes from the
  tab including the bass and the echo [N9, N20, inference].

---

## 3. Signature moves, with numbers

### 3.1 The rhythm cell is the identity, not the tune

- Kondo's account of the method: he wrote a theme, the team put it in the game, and if it did not
  accentuate the action, line up with Mario's running and jumping, or harmonise with the sound
  effects, he scrapped it and started again; the overworld theme took the most work of the six [N1,
  N2].
- The first version he wrote was slower and lazier and was rejected as unengaging against a running
  character; he raised the tempo and rewrote it around a rhythm [N1].
- Operationally [inference]: the cell is one bar, holds 2 to 4 attacks, and its **attack pattern**
  (not its pitches) is what repeats. The corpus supports the pitch side of this: the top interval
  shapes are 0 0, +1 -1, -1 +1, so the pitches are doing very little while the rhythm does the
  identifying [N20].
- A one-bar cell at 100 bpm is 2.4 s. Four repetitions is 9.6 s, past the 5 s average recognition
  time and inside the range the hook grammar cites for a first listen [inference from MUSIC-HOOK-
  GRAMMAR.md's recognition figures and N1's 100 bpm].

### 3.2 Swing that is written in, not played in

- Wikipedia describes the Mario theme as "swing rhythm with prominent use of syncopation" at 100 bpm
  in C major [N1]. The APU cannot swing: its timing resolution is one frame (about 16.7 ms at 60 Hz)
  and there is no groove template in the driver [N14].
- So the swing is an artefact of two things the composer does control [inference from N1, N14]:
  uneven note lengths (a long-short pair inside the beat, which the corpus sees as 2 1 and 1 2
  duration bigrams) and accents placed off the beat.
- The other route, and the one the Zelda and Metroid tabs show, is **compound metre**: 12/8 at about
  151 bpm gives four dotted-quarter beats per bar, so every beat divides 3:3:3 and the shuffle feel
  is notated rather than implied [N10, N12].
- Operational rule [inference]: choose one route per cue and never mix. If the cue is 4/4, uneven
  note lengths plus off-beat accents carry the lilt, with the second note of a pair placed one frame
  late. If the cue wants a real lilt, write 12/8 and let the notation do it.

### 3.3 The 1 to 2 bar motif, and the fourth repetition

- The corpus's melodic micro-shapes are repetition and neighbour motion: 0 0 is 15.0 percent of all
  intervals, and 0 0 0 is the most common 3-gram, 0 0 0 0 the most common 4-gram [N20].
- Karen Collins's analysis of the Mario overworld, as recorded by Wikipedia, describes repeating
  four-bar sections with subtle variations that alternate before looping, and the theme as four
  distinct motifs that each vary slightly to prevent listener fatigue [N1].
- Operational rule [inference]: write a 1 bar cell, state it four times, and change exactly one
  parameter on the fourth (register, duty, last two sixteenths, or the bass note under it). That is
  25 percent variation, which is enough to defeat exact-match repetition detectors and small enough
  that the ear still hears one idea.

### 3.4 How bass and melody interlock

- The corpus puts the melody at median MIDI 72 and the bass at 45: 27 semitones, two and a quarter
  octaves, with the inner voice at 61.8 in between [N20]. There is almost always a third part.
- The triangle has no volume control on the 2A03; it is on at full amplitude or silent [N14]. That
  single fact explains the bass style of this scope: because the triangle cannot accent, the bass
  cannot play a groove by dynamics, so it plays one by **pitch change and note length**.
- The Zelda overworld tab scores chord-bass melody at 94 against a database average of 40 to 45
  [N10, N12], that is, its bass is unusually melodic and moves independently of the tune.
- The Mario overworld is the other pattern: the triangle walks under a melody that never stops, and
  the interlock is rhythmic, with the bass landing on the beats the melody leaves empty [N1, N2,
  inference].
- Operational rule [inference]: for bright cues, bass on eighths with pitch changes every two
  eighths, and the melody leaving beat 4 of every second bar to the bass. For atmosphere, bass on
  whole bars with one pitch, and let the inner voice do the moving.

### 3.5 Chromatic embellishment, and how little this style tolerates

- The corpus chord vocabulary includes 360 diminished, 347 half-diminished and 117 augmented chords
  out of 6588 chord-beats, that is about 8 percent, and 41 occurrences of the bII6/5 bigram [N20].
  Chromaticism exists and it is a garnish, not a surface.
- The Zelda overworld tab is Bb Mixolydian: a major scale with a flat seventh, no raised leading tone
  [N10]. The Mixolydian flat seventh is the cheapest chromatic colour in the scope (one flat, no
  chord change needed) [inference from N10].
- The Metroid Brinstar tab is G minor with a chord complexity of 95 and 95 percent progression
  novelty: the chromaticism lives in the harmony while the melody stays diatonic and on chord tones
  (85 percent) [N12].
- Operational rule [inference]: at most one borrowed chord per four bars in a bright cue, at most one
  per two bars in an atmosphere cue, and never a chromatic note in the hook itself; the hook is the
  diatonic part, the colour is what happens underneath it.

### 3.6 Sound effects that agree with the key

- Kondo's stated test was whether a theme "harmonised with the sound effects", and he scrapped
  themes that failed it [N1].
- The hardware reason is that effects and music share the same channels: a jump and a coin are pulse
  channel events, so their pitch is heard as part of the harmony whether or not the composer intended
  it [N14, inference].
- Operational rule [inference]: tune the two most frequent effects to the tonic and the fifth of the
  cue's key, and put the coin on a pitch that is in the I chord. If a cue is in C major, the coin
  blip is a C or a G, never a D. Cheap to implement if the effect table is keyed off the cue's tonic
  rather than fixed; the arranger recipe NIN-31 carries the parameters.

### 3.7 Theme reuse as variation

- Kondo's Mario score has six themes for one game and reuses the overworld material across the
  overworld, the underground and the swimming cues by changing tempo, register, duty and drum feel
  under the same cell (unverified in this run; the six-theme count is [N1], the variation claim is
  [inference]).
- The corpus shows the mechanism in the numbers: the hurrying variants in the SMB set have their own
  entries in the archive, and the whole set is 89.4 percent single sixteenths, so a variation cannot
  be made by adding notes; it has to be made by changing register, duty, tempo or drums [N20].
- Tanaka's version of a related idea is withholding: he wanted not to "repeat the same game-melody
  cliches", and in Metroid the strong melody arrives at the end of the game, after a score that stays
  dark [N4].
- Operational rule [inference]: three variations of one cell per game is the target, and each
  variation changes exactly two of {tempo, mode, register, duty, drum pattern}. A boss cue built from
  the stage cell should differ in at least three.

---

## 4. How a one bar cell becomes the hook

1. Choose the surface first, because it decides everything else: bright cue, sixteenth surface
   (Kondo path, 67 to 89 percent single sixteenths in the corpus [N20]); atmosphere cue, long-note
   surface (Brinstar, 4 or more beats per note [N12]).
2. Write a one bar cell with 2 to 4 attacks, and make its intervals small: unison, minor second,
   major second, or a single leap of a fourth or fifth at a fixed position [N20].
3. State it four times. Change one parameter on the fourth statement [inference from N1's four
   motifs].
4. Put a two bar answer under it that ends on a non-tonic degree, so the loop does not close. The
   Zelda and Mario tabs both use I as the most used chord but neither loop ends decisively [N9, N10,
   inference].
5. Under a bright hook, keep the harmony simple (Mario chord complexity 45) and let the melody fight
   it (tension 96) [N9]. Under an atmosphere hook, invert it: dense harmony (95) and a melody of
   chord tones (tension 8) [N12].
6. Write the bass as a second line, not as a root pad: the triangle cannot accent, so give it pitch
   motion (chord-bass melody 94 on the Zelda tab) [N10, N14].
7. Check the loop length. A 4 bar loop at 100 bpm is 9.6 s; at 152 bpm it is 6.3 s. The corpus's
   median stage cue in this scope runs 4 to 22 bars depending on the game, and the longest measured
   piece is 74 bars (Metroid) [N20]. Our arranger should default to 8 or 16 bars.

Two worked patterns, degrees and counts only [inference]:

- Pattern K (Kondo path): major key on the tonic (C is a fifth of the corpus [N20]), 4/4, 100 bpm,
  2 to 4 attacks per bar, sixteenth surface, one pitch repeated with a neighbour wobble, a walking
  bass on eighths, harmony at one chord per two beats, loop 8 bars with the fourth statement
  altered. Hook mechanism: rhythm plus a melody that leans off the chord (tension high).
- Pattern T (Tanaka path): minor or modal, 12/8 or very slow 4/4, 151 bpm in dotted quarters or 92 in
  common time, long notes of 2 to 4 beats, one chord per bar, an inner voice arpeggiating, and the
  melody restricted to chord tones with the chromaticism in the harmony. Hook mechanism: colour plus
  a repeated rhythm figure in the accompaniment, not a tune [N10, N12].

---

## 5. Drum and bass habits

Drums, from the chip and the corpus [N14, N20, plus inference]:

- The noise channel is the whole kit, and the corpus keeps three pitched voices plus noise, so the
  drums are one channel: hat, snare and kick cannot sound simultaneously on the 2A03 without DPCM.
- Straight cues: hat on eighths or sixteenths at low volume, snare or noise burst on 2 and 4, kick
  (DPCM) on 1 and 3, no fills in an 8 bar loop, one fill at the loop seam.
- Compound cues (12/8 at 151 bpm): the hat marks the dotted-quarter pulse, which means the drum is
  telling the listener where the three-grouping is [N10, N12]. Without it, 12/8 on a chip reads as
  4/4 with a limp.
- Tanaka's dark cues drop the backbeat almost entirely; the percussion becomes a pulse and the
  harmony carries the motion [N12 inference].
- No groove template: every drum decision is a written pattern, and swing comes from pattern choice,
  not from timing jitter [N14].

Bass:

- Triangle on the root, eighths for bright cues, whole bars for atmosphere cues [inference from N14
  and N20's role pitch median of 45].
- Keep the triangle between MIDI 40 and 52; below that it stops being audible on small speakers and
  above it, it collides with the inner voice at 61.8 [N20, N14].
- Give it at least one pitch change per bar in a bright cue, because it has no volume control, so
  pitch is its only accent [N14].
- On a VRC6 cart (this scope has none: no first-party game used VRC6 [N15 inference]) the saw would
  take the low end; the recipes therefore do not specify VRC6 for this style except in the optional
  arrangement row NIN-27.

---

## 6. Harmony and the dissonance this style tolerates

- Keys: C major for a fifth of the corpus, then G, F, A minor, Bb. Mode split is 71 percent major
  [N20]. Major is the default here, unlike the Konami scope.
- The available scales beyond plain major: Mixolydian (flat seven) for wandering overworlds [N10],
  natural minor with a flat six for serious cues [N11], and the harmonic minor vocabulary only when
  a cue is meant to sound old or threatening [inference].
- Chord vocabulary in descending measured frequency: major, minor, sus4, minor seventh, major
  seventh, dominant seventh, diminished, half-diminished, augmented, sus2, diminished seventh [N20].
- I6/4 is the fourth most common chord label (268 beats) and the second most common bigram form
  (I6/4 I6/4, 136) [N20]. Operationally that is a tonic pedal: the bass sits on the fifth while the
  upper voices move. It is the scope's cheapest way to keep a loop from sounding static [inference].
- Vsus4 is the third most common single label (329) and Vsus4 Vsus4 the third most common bigram
  (229), which is the NES arpeggio writing a suspended dominant and holding it [N20].
- Dissonance ceiling, operationalised [inference]: one non-diatonic chord per four bars in a bright
  cue and per two bars in an atmosphere cue; a flat seventh in the melody is fine anywhere in a
  Mixolydian cue; a tritone in the melody is a special effect and belongs to boss and danger cues
  only.
- What the style does NOT tolerate [inference from N9, N10, N12, N20]: a melody that wanders more
  than an octave and a half (corpus median range 18 semitones), a chord per beat with no repetition
  (the bigrams show labels held for 2 to 4 beats), jazz voicings stacked two deep, and a modulation
  inside a 4 or 8 bar loop.

---

## 7. Form, loop lengths and tempo ranges

| Cue type | Bars | Loop | Evidence |
| --- | --- | --- | --- |
| Overworld or stage theme | 8 to 32, median 4 to 22 depending on the game | one or two sections, looped | SMB max 44 bars, Zelda max 40, Zelda II max 46, Metroid max 74, Kid Icarus median 22 [N20] |
| Battle or boss | 4 to 16 | tight loop | Punch-Out's whole set is 1 to 16 bars, median 3 [N20] |
| Title theme | 4 to 16 bars then loop | statement plus loop | Kid Icarus title and Dr. Mario title are separate archived pieces [N20] |
| Jingle (item, secret, flute) | 1 to 4 bars | one shot | six Zelda and Zelda II jingles were too short to analyse (under 12 pitched notes) [N20] |
| Hurry-up variant | same length as the parent cue | loop at higher tempo with one less voice | SMB archive holds separate "Hurry" entries for six cues [N20] |

Tempo, quoted where a source exists and inferred otherwise:
- Mario overworld: 100 bpm per Wikipedia with a swing feel, 200 bpm in the tab's eighth-note count
  [N1, N9]. Working default for bright cues: 96 to 112 [inference].
- Zelda overworld: 152 bpm in 12/8 [N10]. Metroid Brinstar: 151 bpm in 12/8 [N12]. Working default
  for compound cues: 144 to 156 [inference].
- Zelda main theme tab: 92 bpm in 4/4 [N11]. Working default for serious or title cues: 84 to 96
  [inference].
- Punch-Out and other march and fanfare cues: no published tempo found; the cues are 1 to 5 bars, so
  anything from 120 to 160 works and the number is not load bearing [N20, unverified tempo].

Phrase architecture [N20, inference]: the corpus's own repetition shape is a one bar cell plus
two bar answer, so build every cue as an 8 bar loop of 4 + 4, with the second four being the answer
plus a 1 bar drum or bass link. The published analysis of the Mario overworld as repeating four-bar
sections with subtle variation is the same design seen from the listener's side [N1].

---

## 8. Instrument assignment on the 2A03

Five channels, no expansion [N14]. No first-party Nintendo NES title in this scope used a sound
expansion chip (unverified; no source states a Nintendo game with VRC6, and VRC6 is a Konami part
[N15]).

| Channel | Bright cue (Kondo path) | Atmosphere cue (Tanaka path) | Constraint |
| --- | --- | --- | --- |
| pulse1 | lead hook, duty 25 or 50 percent | lead, long notes, duty 12.5 for thin colour | duty changes inside a held note are audible and free [N14] |
| pulse2 | answer phrase, echo one 16th late at low volume, or parallel third | inner arpeggio or drone fifth | keep the two duties different so the parts are separable [inference] |
| triangle | walking bass, eighths, one pitch per eighth to one per half bar | pedal on the tonic or fifth, one pitch per bar | no volume control, so no accents [N14] |
| noise | hat plus snare, kick via DPCM if ROM allows | pulse only, no backbeat | one channel for the whole kit [N14] |
| dpcm | kick, one short sample | silent, or a single low tom | ROM cost, one sample reused [N14] |

The corpus's own arrangement agrees: median 3 pitched voices with an inner part present in every
piece (204 inner voices against 132 melodies), melody at 72 and bass at 45 [N20]. The fifth channel
is normally the drum, so a mix with four melodic parts is out of style.

---

## 9. Human touches that read as "played"

- One frame of timing: at 60 Hz a frame is 16.7 ms, and the only expressive timing the hardware
  offers is to place a note one frame early or late [N14]. Kondo's Latin and fusion reference is what
  makes this audible as feel rather than error [N1].
- Uneven note lengths inside a beat, long-short or short-long, are the written form of swing on this
  chip [N1, N14, inference].
- Vibrato only on held notes of 2 beats or more, applied through the low period byte, depth 10 to 20
  cents, rate about 5 Hz, starting about 120 ms in [N14].
- Duty change on the last long note of a section, once per cue, never on the hook note [N14,
  inference].
- Deliberate imperfection in the fourth repetition: one sixteenth altered, not the pattern [N1,
  inference].
- Ask before writing: does the hook still work with the drums muted? Both Kondo and Tanaka write
  hooks that survive on one pulse plus the triangle [N2, N4, inference].

---

## 10. What to avoid

1. A melody that roams more than an octave and a half. The corpus median range is 18 semitones [N20].
2. Sixteenth-note density in an atmosphere cue. Metroid sits at 52 percent single sixteenths and
   Brinstar at 4 or more beats per note [N20, N12].
3. Triplet or shuffled timing written as a timing offset. Use 12/8 or uneven note lengths instead
   [N14, N10].
4. A chord per beat with no held label. The bigrams show labels held for 2 to 4 beats [N20].
5. Four melodic voices. Three pitched parts plus noise is the measured norm [N20].
6. A hook that only works with the drums. Kondo's test was the game, Tanaka's was the atmosphere; in
   both cases the melody carries alone [N1, N4].
7. Effects in a foreign key. Kondo scrapped themes that did not agree with the effects [N1].
8. Ending every loop on the tonic. Both scopes loop open; the tabs' most used chord is I but the
   cadence is not the hook [N9, N10, inference].
9. Copying the sound of a specific cue. The clean-room rule and the melody guard both apply
   (PLAN-V2 section 0; `tools/melody_guard.py`).
10. Treating "8-bit" as a genre. The numbers say Mario and Metroid share a chip and almost nothing
    else [N9, N12].

---

## 11. The 32 recipes

Full machine-readable rows are in `data/recipes/nintendo.json` (family prefix NIN, 32 recipes).
Index:

| ID | Name | Where it goes |
| --- | --- | --- |
| NIN-01 | One bar rhythm cell, four statements, one change | every bright cue |
| NIN-02 | Neighbour wobble hook | hook core |
| NIN-03 | Two bar question and answer, answer unresolved | loop second half |
| NIN-04 | Written swing, long-short pair plus one frame late | bright 4/4 cues |
| NIN-05 | Compound 12/8 groove | Zelda and Metroid path |
| NIN-06 | Walking triangle bass, eighths, two pitches | bright cues |
| NIN-07 | Bass octave answer on bar four | phrase end |
| NIN-08 | Bass carries the hook for two bars | section B |
| NIN-09 | Hocket: melody rests, bass answers | loop seam |
| NIN-10 | C major bright hook default | overworld |
| NIN-11 | Mixolydian flat seven colour | wandering overworld |
| NIN-12 | Natural minor with flat six | serious cue |
| NIN-13 | Neapolitan flat two stab | danger, boss |
| NIN-14 | Tonic second-inversion pedal | long loops |
| NIN-15 | Suspended dominant, held then resolved | loop end |
| NIN-16 | Chromatic approach bass | transitions |
| NIN-17 | Inner voice arpeggio at frame rate | atmosphere cues |
| NIN-18 | Echo pulse one sixteenth late | titles, caves |
| NIN-19 | Noise kit, straight | any bright cue |
| NIN-20 | Noise kit, pulse only | atmosphere cues |
| NIN-21 | Long-note ambient lead | Metroid path |
| NIN-22 | Melody on chord tones under dense harmony | atmosphere cues |
| NIN-23 | Melody against simple harmony, high tension | Kondo path |
| NIN-24 | Hurry-up variant, tempo lift plus one voice dropped | time limit |
| NIN-25 | Theme reuse as variation, two parameters changed | throughout a game |
| NIN-26 | Title jingle under 4 bars, half cadence | title, menus |
| NIN-27 | Stage clear fanfare, 2 bars, V to I | one shots |
| NIN-28 | Optional expansion arrangement (VRC6, out of scope for authenticity) | optional arrangement |
| NIN-29 | Miss and death cue, descending, no drums | one shots |
| NIN-30 | Eight bar loop with a one bar link | default form |
| NIN-31 | One frame push on the peak note | human touch |
| NIN-32 | Sound effects tuned to the cue's key | every cue with effects |

---

## 12. Listening notes: ten tracks, what to listen for

These are ear training notes, and the clean-room rule in `PLAN-V2-2026-10-21.md` section 0 applies. No melody is written out; each note names a section, a bar position
and a feature to count.

1. Super Mario Bros, Overworld (Kondo) [N2]. Listen to bar 1 and count attacks only: the cell is
   short. Then listen for the fourth statement of the cell and name the one thing that changed. The
   published tab puts the cue in C major at 200 bpm counted in eighths with a chord-melody tension of
   96 [N9], and Wikipedia describes a swing feel [N1], so the exercise is to hear the swing without
   being able to point at a late note.
2. Super Mario Bros, Overworld, bass only [N2]. Count how many times the triangle changes pitch per
   bar. The corpus says Nintendo-scope bass sits at MIDI 45 with pitch motion rather than accents
   [N20], and the triangle cannot accent at all [N14], so what you should hear is a walking line, not
   a groove.
3. Super Mario Bros, Underground [N2]. Compare it with the Overworld: same game, same chip, lower
   register, sparser drums. Mark the bar where the echo pulse starts and note whether it is a
   sixteenth or an eighth behind the lead. This is the variation method of section 3.7 heard
   directly.
4. The Legend of Zelda, Overworld (Kondo) [N6]. Tap the pulse first without counting: the published
   tab calls it 12/8 at 152 bpm in Bb Mixolydian [N10]. Then clap only the chord changes and see
   whether the bass moves when the chord does; the tab scores chord-bass melody at 94, so the
   exercise is to notice the bass is a line, not a root.
5. The Legend of Zelda, Overworld, second loop [N6]. Listen for the one element that differs between
   the first and second pass. Write down which of {register, drums, bass, harmony} changed. That is
   the loop-variation budget this style actually spends.
6. Metroid, Brinstar (Tanaka) [N4]. Count notes per bar, not beats: the published tab records 4 or
   more beats per melody note with 85 percent chord tones [N12]. Then listen to the inner voice and
   notice that it, not the melody, is doing the moving.
7. Metroid, Norfair or Tourian [N4]. Listen for the absence of a backbeat. Tanaka's stated aim was to
   avoid game-melody cliches and to keep the score dark until the end [N4], so the exercise is to
   hear how tension is created with harmony and noise rather than with a tune.
8. Kid Icarus, Overworld or The Sky World (Tanaka) [N5]. This is the bright Tanaka, 70 percent single
   sixteenths by the corpus measurement [N20], so listen for how the same composer switches surface
   density: same chip, more notes, major key.
9. Punch-Out!!, fight music (Nakatsuka) [N8]. Each cue is 1 to 5 bars by the corpus measurement
   [N20]. Listen to a fight loop and count how long it takes before it repeats, then listen for what
   the drums do at the repeat: the answer is usually nothing, which is the point of a 2 bar cue.
10. Tetris, Type A (Tanaka's arrangement of a folk tune) [N3]. This one is worth ear training because
    the tune is not his: listen for where the arrangement, not the tune, creates the identity (the
    bass pattern, the drum pulse, the octave placement), and compare it with the same tune's B
    section. It is the cleanest example in the scope of arrangement as composition (unverified
    beyond [N3] for the folk-song origin).

---

## 13. Sources

All links read on 2026-10-21. The four Hooktheory tabs and the three credit pages were fetched and read in this run; the remaining entries were read from search result extracts, so their page bodies are unverified here.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| N1 | Wikipedia, Super Mario Bros. theme | https://en.wikipedia.org/wiki/Super_Mario_Bros._theme | C major, 100 bpm, swing rhythm and syncopation, influence of T-Square's Sister Marian, the revise-until-it-fits method, the sound-effect test, four motifs with variation, Karen Collins's four-bar analysis, National Recording Registry 2023 |
| N2 | Grokipedia, Super Mario Bros. theme | https://grokipedia.com/page/Super_Mario_Bros._theme | Kondo solo composer including effects, four channels, toy keyboard then assembly programming, Latin rhythm, first version rejected as unengaging |
| N3 | Wikipedia, Hirokazu Tanaka | https://en.wikipedia.org/wiki/Hirokazu_Tanaka | Credits: Metroid, Kid Icarus, Tetris (1989), Mother, Dr. Mario; Red Bull lecture attribution for "not repeating game-melody cliches" and the Birdy inspiration; APU hardware design role |
| N4 | Shinesparkers, Hirokazu Tanaka interview (2018) | https://shinesparkers.net/interviews/hirokazu-tanaka/ | Metroid method, Brinstar made lighter on purpose, his correction of the "Nintendo disliked it" claim, no memory of individual sound effects |
| N5 | Nintendo Fandom, Kid Icarus soundtrack | https://nintendo.fandom.com/wiki/Kid_Icarus/soundtrack | Kid Icarus music solely by Tanaka, credited as Hip Tanaka |
| N6 | Zelda Universe forum composer list | https://zeldauniverse.net/forums?thread/207228-composers-of-zelda/ | Zelda 1986 composer Kondo credited as Konchan; Zelda II composer Nakatsuka credited as Tsukasan |
| N7 | Nintendo Fandom, Zelda II soundtrack | https://nintendo.fandom.com/wiki/Zelda_II:_The_Adventure_of_Link/soundtrack | Zelda II music solely by Akito Nakatsuka |
| N8 | Enjoy Game Japan Museum, Akito Nakatsuka | https://museum.enjoygamejapan.online/en/creators/akito-nakatsuka | Nakatsuka joined Nintendo 1984, composed Devil World, Ice Climber, Zelda II and Punch-Out!!, wrote his own sound engine around 1986, economical repeating motifs in Zelda II |
| N9 | Hooktheory theorytab, Super Mario Bros Overworld Theme | https://www.hooktheory.com/theorytab/view/koji-kondo/super-mario-bros-overworld-theme | C major, 200 bpm, 4/4, range C2 to C6, chord complexity 45, melodic 97, tension 96, novelty 44, most used chord I, 0.92 beats per note |
| N10 | Hooktheory theorytab, The Legend of Zelda Overworld Theme | https://www.hooktheory.com/theorytab/view/nintendo/the-legend-of-zelda---overworld-theme | Bb Mixolydian, 152 bpm, 12/8, chord complexity 88, melodic 86, tension 51, novelty 92, chord-bass melody 94, most used chord I |
| N11 | Hooktheory theorytab, The Legend of Zelda Main Theme (separate entry) | https://www.hooktheory.com/theorytab/view/nintendo/legend-of-zelda-main-theme | Bb minor, 92 bpm, 4/4, range F4 to Db6, chord complexity 92, melodic 91, tension 29, most used chord VI |
| N12 | Hooktheory theorytab, Metroid Brinstar Theme | https://www.hooktheory.com/theorytab/view/nintendo/metroid---brinstar-theme | G minor, 151 bpm, 12/8, chord complexity 95, melodic 99, tension 8, novelty 95, 85 percent chord tones, 4 or more beats per note, most used chord III |
| N13 | Enjoy Game Japan Museum, Kondo and Super Mario Overworld review | https://museum.enjoygamejapan.online/en/sounds/reviews/kondo-koji-super-mario-overworld | Five days to write the score, the four plus one channel split, tempo chosen before melody, triangle with no volume control; treated as secondary because it is an aggregator page |
| N14 | NESdev Wiki, APU | https://www.nesdev.org/wiki/APU | Two pulse channels with four duty cycles, triangle with no volume control, noise, DPCM, frame rate timing; the period byte write resets phase |
| N15 | NESdev Wiki, VRC6 audio | https://www.nesdev.org/wiki/VRC6_audio | VRC6 is a Konami mapper chip; two pulses and a saw, not part of the stock 2A03 |
| N16 | Primordial Paradox hook grammar | knowledge/MUSIC-HOOK-GRAMMAR.md | Recognition-time figures used in section 3.1 and the hook-first method |
| N17 | Primordial Paradox style bible | knowledge/MUSIC-STYLE-BIBLE.md | Channel role conventions and the arranger's recipe format |
| N18 | Famicom 20th Anniversary Arrange Sound Tracks credits (khinsider listing) | https://downloads.khinsider.com/game-soundtracks/album/famicom-20th-anniversary-arrange-sound-tracks | Credit split: Kondo for Super Mario Bros and Zelda, Tanaka for Dr. Mario, Kid Icarus and Metroid |
| N19 | VGMdb, NES Classics 1 credits | https://vgmdb.net/album/86919 | Second credit record confirming Tanaka for Kid Icarus and Nakatsuka appearing in the same NES composer list |
| N20 | Primordial Paradox nintendo corpus statistics, `D:\Musikage-Corpus\style-pp\stats\nintendo.json` (generated 2026-10-21 from 132 NES-MDB pieces) | local file | Modes, tonics, chord changes, qualities, bigrams, interval and rhythm histograms, ranges, role pitches, per-game surfaces, cue lengths; tempo field normalised and not used |

---

## 14. Limits of this document

- The corpus figures describe NES-MDB's transcriptions as much as the composers' intent. They are
  used for ratios and shapes, never as bar level ground truth about a named track [N20].
- Tempo cannot be measured from that corpus at all [N20]. Four tempo figures are quoted from
  crowd-sourced Hooktheory tabs [N9, N10, N11, N12] and those are one contributor's analysis per
  track, not a scholarly source. Two independent tabs agreeing on 12/8 at 151 and 152 bpm is
  suggestive, not proof.
- Super Mario Bros 2 and 3 are not in the corpus, so nothing in this file is measured from them
  [N20]. Their credits are marked unverified and should be fixed from a primary source before any
  recipe cites them.
- The card's credits for Zelda II (Kondo and Nakatsuka), Punch-Out (Tanaka) and "Naoki Tomita" do
  not match the sources I read [N7, N8]. I corrected them and stated what I could not check.
- Nothing in this file is a transcription, and the recipes in `data/recipes/nintendo.json` describe
  construction rules only, so no melody of these games can be reconstructed from them.
