# Capcom NES rock: Mega Man, Ninja Gaiden, DuckTales and the house sound

Card t_c7507612 (STUDY-CAPCOM), musician, written 2026-10-21. Scope name `capcom`.
Companion files: `knowledge/MUSIC-HOOK-GRAMMAR.md`, `knowledge/MUSIC-STYLE-BIBLE.md`,
`knowledge/MUSIC-DRUMS.md`, `knowledge/MUSIC-DISSONANCE.md`, and the executable recipes in
`data/recipes/capcom.json`.

Reference rule (PLAN-V2 section 0): the games were studied from published interviews, credit
records, hardware documentation, one community guide built by frame-by-frame observation, and
measured corpus statistics. Nothing was downloaded, ripped, sampled, traced or decompiled. No melody
is written out anywhere in this file: every musical statement is a shape, a scale degree, an interval
or a count.

Tagging. Every claim ends with a source id in square brackets, for example [C4]. Section 13 has the
link and the read date for each id. `[inference]` marks my own operationalisation of a source,
written so an arranger has a number to hit.

---

## 1. Who wrote what, and why the recipe set needs four different paths

- Mega Man (Famicom, December 1987): all music and sound effects by Manami Matsumae, credited as
  Chanchacorin, composed and entered in three months by one person [C1, C2]. She had joined Capcom
  shortly before, and her first shipped piece was one song for a mahjong game [C3].
- Mega Man 2 (1988): all music and sound effects by Takashi Tateishi, credited as Ogeretsu Kun,
  with one exception: Air Man's melody includes measures written by Matsumae, and the MM2 opening
  theme was built as a continuation of the MM1 ending theme from data she handed over [C2, C3, C10].
- Yoshihiro Sakaguchi programmed the sound driver for both games and was the sound manager; the
  composers wrote the music, he built the playback system [C2, C10].
- Mega Man 3 (1990): Harumi Fujita started the score and completed only a few pieces (Needle Man,
  Gemini Man and the staff roll are the ones named) before leaving to give birth; Yasuaki Fujita
  (Bun Bun) finished and wrote the majority [C9, C10].
- Mega Man 4 is credited to Minae Fujii, Mega Man 5 to Mari Yamaguchi, Mega Man 6 to Yuko Takehara
  on the Rockman 1 to 6 box set, with two tracks shared from MM4 [C10]. So the series changes
  composer every game by design, which Matsumae describes as the source of its musical diversity
  [C3].
- Ninja Gaiden (Tecmo, 1988): Keiji Yamagishi (credited More Yamasan) composed, wrote the sound
  driver and did the data entry; Ryuichi Nitta contributed around three or four sounds [C8]. Yamagishi
  had no formal theory training and worked by ear, and he says the sampled drum channel is the thing
  that set Tecmo's sound apart [C7].
- DuckTales (Capcom, 1989): Hiroshige Tonomura composed the score, and the credit is confirmed by
  Capcom's own site listing plus Matsumae's direct confirmation after years of the game being
  miscredited to Sakaguchi [C16, C18].
- Consequence for the recipes: there is no single Capcom voice, but there is a shared house grammar.
  A riff-led rock texture with real layering, a melody written to be sung, and a drum kit that
  pretends to be a band are the constants across four composers at Capcom [C1, C4, C7, C14]. Ninja
  Gaiden shares the riff grammar and adds Tecmo's sampled percussion [C7, C8], and DuckTales shares
  the Capcom layering while pushing harmony and metre further than Mega Man does [C16, C17].

---

## 2. What the measurements say

### 2.1 Our own corpus

Source: `D:\Musikage-Corpus\style-pp\stats\nes_rock_metal.json`, generated 2026-10-21 from
NES-MDB MIDI, of which 16 pieces are Mega Man and 29 are Ninja Gaiden [C19]. These are counts from a
converted archive, not from the ROM, and the archive normalises tempo, so no tempo claim comes from
this file.

| Measure | Mega Man (16 pieces) | Ninja Gaiden (29 pieces) |
| --- | --- | --- |
| Minor key share | 9 of 16 | 23 of 29 |
| Favourite tonics | G minor 3, D flat major 2, B major 2, G flat minor 2 | A flat minor 4, F minor 4, A minor 4 |
| Length, median | 12.5 bars | 19 bars |
| Length, longest | 46 bars (Ending) | 74 bars (cutscene cue) |
| Longest stage theme | 22 bars (Ice Man) | 64 bars (a mid game stage cue) |
| Notes per bar, median | 42.5 | 27.85 |
| Melody share of notes | 23.6 percent | 35.2 percent |
| Voices per piece | 3 in all 16 | 3 in 26, 2 in 3 |

Whole-file figures for the same 86 piece rock and metal set, which is the only measured harmony and
interval data we have for this family [C19]: melody intervals are 16.5 percent unison, 10.2 percent
minor second, 9.6 percent major second upward and 7.8 percent downward; 51.6 percent steps against
48.4 percent leaps; 76.0 percent of melody notes are a single sixteenth; harmony changes 3.78 times
per bar across 249 distinct labels; chord qualities run sus4 1033, major 953, minor seventh 876,
minor 871, major seventh 522, diminished 455, dominant seventh 408, half diminished 312, augmented
131, diminished seventh 42.

Reading, and it matters [inference]: Mega Man is denser per bar than Ninja Gaiden (42.5 against 27.85
notes per bar) and gives less of that density to the melody (23.6 against 35.2 percent), which is the
measured signature of layering. Mega Man spends its notes on accompaniment, Ninja Gaiden spends them
on the tune and on the drums.

### 2.2 Published analysis, which carries real tempo

| Track | Key | Tempo | Meter | Melody range | Readings |
| --- | --- | --- | --- | --- | --- |
| Mega Man 2, Dr Wily Stage 1 | C minor | 180 bpm | 4/4 | D sharp 3 to G sharp 5, 29 semitones | 0.89 beats per note over 160 beats of melody, 95 percent diatonic, 68 percent chord tones, chord-bass-melody 91, chord complexity 55, melodic complexity 81, chord-melody tension 66 [C12] |

One tab is a thin sample and I treat it that way. What it establishes is a tempo band (180 bpm, not
120), a key (minor), a melody that is almost entirely diatonic, and a melody unusually tightly
coupled to the bass motion (91 on a scale where 50 is average) [C12]. The same source describes the
form as intro, chorus, bridge and outro rather than as one loop [C12].

### 2.3 Cue lengths from an official album track list

Stage Select 0:29, Game Start 0:08, Boss 1:00, Stage Clear 0:07, Dr Wily Stages 1 and 2 together
2:49 [C11]. These are album timings for looped cues, so they bound the loop rather than define it,
but they do establish the proportion: a boss loop is twice a stage select loop, and the jingles are
one or two bars [C11, inference].

---

## 3. Signature moves, with numbers

### 3.1 The power fifth as the default harmony

- The community guide built by watching Rockman run frame by frame states it directly: a power fifth
  chord is the signature harmony of the series, used to create a powerful harmony inside rock
  instrumentation [C14]. The theory source behind it: a power chord is root plus fifth and possibly
  octaves, with no third, so it is neither major nor minor and it survives fast chord changes [S29 in
  the style bible].
- On the chip this is the only triad the hardware can voice honestly: root on pulse1, fifth on
  pulse2, both at 50 percent duty, both on the same grid [C14, C15].
- Operational numbers [inference]: the fifth sits 7 semitones above the root; the dyad is re-attacked
  on eighths in a stage theme and on sixteenths in a boss theme; the third appears only in the melody
  or as a passing tone, never as a chord tone.

### 3.2 Dotted quarters, the other half of the riff grammar

- The same guide names dotted quarter notes as a second signature: they are what makes a two beat
  pattern feel like it leans [C14]. A dotted quarter is 3 sixteenths of a 4/4 bar, so a cell built as
  dotted quarter plus dotted quarter plus quarter covers the whole bar with three attacks and one
  long overlap [inference].
- Practical rule [inference]: at most one dotted quarter figure per bar in a stage theme, on the
  strong beat, because the length is what carries the swagger and it cannot be spent twice.

### 3.3 The one-frame note cut, which is the actual "NES sound"

- Rockman 1 and 2 cut a note one frame before the next note starts, so back to back notes do not fuse
  into one long tone; the guide calls this the "NES sound" and says 1 and 2 used it profusely while 4,
  5, 6 and 9 deviated [C14]. One frame is 16.7 ms at 60 Hz [C15].
- Numbers to write with [C14, inference]: a note's gate is its written length minus one frame, so at
  150 bpm a sixteenth (2 frames) sounds for 1 frame and an eighth (4 frames) sounds for 3. Apply it to
  every melodic channel, not to the bass, and apply it consistently, because mixing cut and uncut
  instruments in one pattern makes the timing sound sloppy [C14].

### 3.4 The volume staircase fade

- Rockman 2's releases descend the 16 hardware volume levels in pairs, and the guide quotes a shape
  close to 15, 15, 13, 13, 11, 11, 9, 9, 7, 7, 5, 5, 3, 3, 1, 1, 0 [C14].
- Because the resolution is 16 steps, a 2 step change is audible and a 1 step change is not [C15,
  inference]. The staircase is therefore the only honest fade on this chip, and every lead note
  longer than an eighth should have one [inference].

### 3.5 Duty practice

- Leads mostly ran 25 percent; 75 percent thickens slightly and is nearly identical by ear [C14].
- The series never changed pulse width to make a percussive attack, not once in Rockman 1 to 9,
  except an arpeggiated width sequence in a Rockman 9 siren [C14]. So duty is a voice colour, not an
  articulation on this side of the repertoire.
- Operational rule [C14, inference]: lead 25 percent, harmony pulse 50 percent, pad or support 50 or
  75 percent, and one duty change per cue at a section boundary at most.

### 3.6 Chorus, detune and the delayed echo

- Two channels playing the same pitch with the same width can fall out of phase and partially cancel,
  which is why Rockman detunes the second channel by a fine amount whenever it doubles [C14]. The
  guide says almost every Rockman did this [C14].
- Delayed chorus is the other device: the lead is echoed on the second pulse a short time later, used
  a lot in Rockman 2 and only ever as a delayed copy in Rockman 9, and the delayed channel has to be
  detuned or the two squares cancel [C14].
- Numbers [inference]: detune the doubling channel by 5 to 10 cents, delay an echo by one eighth at
  40 to 50 percent volume for a stage theme and by one sixteenth at 30 percent for a boss theme, and
  never echo the bass or the drums.

### 3.7 The rhythm section

- Drums: Rockman 2's kit is a noise snare, a closed hat and an open hat on the same noise rate, and a
  separate electric noise for the Quick Man style texture; the guide gives the starting noise pitches
  (snare 5, alternate snare 3, Wily snare 9, hats D, electric noise B) [C14]. On the 2A03 the starting
  pitch is the LFSR rate index, so those letters are actual values an arranger can write [C14, C15].
- Kicks: Rockman 3 and later used a noise kick, and Rockman 6 pulled out a triangle kick, which is a
  fast downward pitch slide on the triangle rather than a noise hit [C14].
- Tom slides are logarithmic on this chip, the typical slide value is 15, and a triangle tom is a
  short run of falling notes plus a note-off [C14].
- Ninja Gaiden's drums are the other route: Yamagishi sampled a kick and a snare and played them back
  on the sample channel, because Nintendo did not share its tools, and he names that as Tecmo's
  signature [C7, C8]. On our chip the equivalent is a short DPCM kick and snare sample [C15].
- Bass: the triangle plays the root, and the corpus bass median sits at MIDI 46 in this 86 piece set
  [C19]. Rockman's triangle also supplies the punch that a noise hit cannot when the cue calls for
  weight on the downbeat [C14].

### 3.8 Tempo

- Published analysis of Dr Wily Stage 1 reads 180 bpm [C12]; a published essay puts the Mega Man rock
  band in the 150 to 180 bpm range with liberal syncopation and minor keys [C13]; the frame table in
  the community guide is written at 150 bpm, where a beat is 24 frames and a sixteenth is 2 [C14].
- Working defaults [inference from C12, C13, C14 and the cue lengths in C11]: stage theme 150 to 180,
  boss theme 168 to 190 (the boss has to feel faster than the stage it ends), stage select 120 to 140,
  title or staff roll 126 to 150, jingles 132 to 168.

---

## 4. How the hook works

### 4.1 The brief was memorability, stated by the people who had to deliver it

- Matsumae's superior at Capcom told her she had to create melodies that were memorable, and thirty
  years later she described her signature as melodies that are catchy and memorable, a principle she
  says came from the machine and the deadline rather than from taste [C1].
- She framed the character as heroic and asked the planner for a lively, easy to remember melody, with
  Astro Boy as the image [C3].
- Tateishi's stated aim for his Capcom scores was melodies people could hum along with or play in
  their bands, and he describes singing nonsense lyrics over the stage themes while testing them
  [C6, C4]. The MM2 director rejected all but one of his first drafts for sounding too cute and asked
  for cool instead, which is why eight of the nine stage themes share one attitude [C4, C5].
- That is the whole hook doctrine of this style in three sentences [inference]: singable, catchable on
  one hearing, cool rather than pretty.

### 4.2 What the first two bars contain

- The recognition evidence in the hook grammar file applies unchanged: about 5 s average recognition
  and 2.3 to 2.6 s at the fastest, with contour carrying memory inside the first 5 s [S45, S47 in the
  hook grammar]. At 180 bpm one bar of 4/4 is 1.33 s, so two bars are 2.67 s and four bars are 5.33 s
  [inference, arithmetic]: the hook has to be complete in four bars and recognisable in two.
- Measured content of the one analysed Capcom hook: 0.89 beats per note over 160 beats, which is a
  mostly eighth-note melody, 95 percent diatonic, 68 percent chord tones [C12]. Eight bars at 180 bpm
  hold 32 beats, which at 0.89 beats per note is about 36 notes [inference, arithmetic].
- Practical build for our own cues [inference from C12, C14, C4]:
  1. Bar 1 states the rhythmic cell on the two pulses as a power fifth figure, no intro.
  2. Bar 2 answers it a step or a fourth away, so the two bar pair is already the hook.
  3. Bars 3 and 4 repeat the pair with one operation (a sequence up, or a changed last two notes).
  4. Bars 5 to 8 are the second half: usually a short bridge or a released phrase, and the released
     phrase is what makes the return feel like a chorus.

### 4.3 Stage, boss and stage select are three different hooks

- Stage theme: the hook is a riff, 2 to 4 bars, sung by a lead pulse over a power fifth layer, at 150
  to 180 bpm, with the whole loop 16 to 32 bars [C12, C13, C14]. Stage themes in the measured Mega Man
  set run 19 to 22 bars [C19], so 16 plus a two bar link is the honest target.
- Boss theme: the hook is rhythm, not melody, and it is short. The measured album timing is 1:00 for
  the MM2 boss loop against 1:34 to 2:40 for stage loops [C11]. The recipe answer is an 8 or 16 bar
  loop with a two note riff, a sixteenth hat, and no melodic padding [inference].
- Stage select: it is a menu, so it is the one cue that may be a single 4 or 8 bar figure with no
  development, played over a pedal, and the album timing is 0:29 [C11, inference].
- Jingles: Game Start 0:08 and Stage Clear 0:07 [C11]. That is two to four bars. The Game Start jingle
  is the most played cue in the series and is still performed in concerts [C1], so it gets an
  arpeggio up to the tonic and stops [inference]. The same brevity is a house trait: a reviewer of the
  DuckTales score describes its chiptunes as "surprisingly short" [C20], which is the constraint the
  loop design in section 7 is built around.

### 4.4 The Wily Stage 1 shape, described in words and numbers only

- Published criticism describes the cue as a driving minor march whose melody builds through two
  sections with a bridge that releases tension before the return, and it is the shape later Wily cues
  were compared against [C13, C12]. The Hooktheory section labels agree: intro, chorus, bridge, outro,
  with the outro progression unlike anything else in their database [C12].
- A second published description of the Wily castle cues: the third stage theme builds in pitch and
  intensity across the loop and drops just before the climax, so the loop itself is the tension
  device [C23].
- Both descriptions reduce to one recipe [inference]: two 8 bar sections at different harmonic weight,
  a 4 bar bridge that removes the drums or the bass for its first half, and a last bar that climbs
  rather than resolves, so the seam is a lift.

---

## 5. Drum and bass habits

Drum side, from the guide, the interviews and the chip [C14, C7, C8, C15, plus inference]:

- Snare on 2 and 4 in stage themes, played as a mid rate noise burst with a 2 to 4 frame decay. In
  boss themes the snare doubles to all four beats.
- Closed hat on eighths, at a high rate and low volume, because the hat is what makes five channels
  read as a kit.
- Kick on 1 and 3, either a noise kick (Rockman 3 onward) or the triangle kick (Rockman 6's trick, a
  fast falling pitch slide), and on the "and" of 3 when the riff cell needs a push [C14].
- Toms in fills, made as a logarithmic falling slide with a value near 15 and a note-off at the end
  [C14].
- Electric noise hits (the Quick Man texture) as a percussion colour that is not a drum, on the noise
  channel at the B rate [C14].
- Fills every 4 and 8 bars, one beat long, landing on the beat rather than before it; anything longer
  in a 16 bar loop starts to be the theme [inference, from the loop lengths in C19].
- Ninja Gaiden route: sampled kick and snare on DPCM, which gives a real drum attack the noise channel
  cannot, and this is what Yamagishi names as Tecmo's identity [C7, C8].
- No swing. The repertoire's syncopation is notational (dotted quarters, offbeat eighths), not a
  swing ratio [C14, C13].

Bass side:

- Triangle on the root, eighths, one pitch per eighth, with an octave jump on the last beat before a
  chord change [inference from C14, C19].
- The bass carries the riff in the bass-led cues: Heat Man's stage was built on a bass rather than a
  guitar [C5], which is the licence for a triangle riff that the melody doubles rather than the other
  way round.
- Keep the bass between MIDI 36 and 52; the corpus bass median is 46 [C19].
- The melody is tightly coupled to bass motion in the one measured Capcom cue (chord-bass-melody 91)
  [C12], so the bass should move when the melody moves, not vamp through it.

---

## 6. Harmony and the dissonance this style tolerates

- Keys: minor is the default in both measured sets (9 of 16 Mega Man, 23 of 29 Ninja Gaiden) [C19].
  Major cues exist and are mostly menu, stage clear and ending cues [C19, C11].
- The measured chord vocabulary for the family is sus4 first, then major, minor seventh, minor, major
  seventh, diminished, dominant seventh, half diminished [C19]. That ordering is the sound of the
  era's writing: a lot of suspended and added-colour triads, few chromatic chords.
- Two specific mixtures are documented in criticism and in the guide rather than in a tab:
  - Major and minor side by side inside one cue, which the Mega Man series does constantly by
    changing key or mode between sections rather than by borrowing chords [inference from C19's
    major and minor counts within one game, and from the hook grammar's mode-contrast rule S64].
  - The bright major cue used as relief: Crash Man's stage is the one cheerfully major stage theme in
    MM2, and it survived the director's "make it cool" purge precisely because it was the exception
    [C4, C5].
- Dissonance ceiling [inference from C12 and C19]: one non-diatonic note per two bars in a stage
  theme. The measured Capcom hook is 95 percent diatonic, which leaves about one note per 20, so a
  chromatic note is an event; two in a bar reads as a different style.
- Type of dissonance this style tolerates: a major second between the two pulses (a suspended
  colour), a sixth in the melody against the root, and a major seventh as a passing tone. It does not
  tolerate: a held tritone, a cluster of three chromatic notes, or two non-diatonic chords back to
  back inside a 16 bar loop [inference from the vocabulary counts in C19 and the diatonic share in
  C12].
- Harmonic rhythm: 3.78 chord changes per bar in the measured family [C19], but the Capcom stage
  themes are more riff-like than that number suggests, because the archive includes Castlevania and
  Contra as well. Our working default is one chord per half bar in a stage theme and one per bar in a
  boss theme [inference].

---

## 7. Form, loop lengths and tempo

| Cue type | Bars | Loop | Evidence |
| --- | --- | --- | --- |
| Stage theme | 19 to 22 in the measured MM set, 16 to 32 for us | 16 bar loop plus a 2 bar link | [C19], [C12] form labels |
| Boss theme | 8 to 16 | tight loop, rhythm carries it | album timing 1:00 [C11], inference |
| Stage select | 4 to 8 | one figure, no development | album timing 0:29 [C11] |
| Game start, stage clear | 2 to 4 | one shot | album timings 0:08 and 0:07 [C11] |
| Ending or staff roll | 32 to 46 | one pass, no loop | 46 bars measured [C19] |
| Ninja Gaiden cutscene cue | up to 74 | through composed | [C19] |

Tempo defaults [inference from C12, C13, C14]: stage 150 to 180, boss 168 to 190, stage select 120 to
140, title and staff roll 126 to 150, jingles 132 to 168. Below 140 the one-frame cut stops being
audible and the riff loses its snap.

Form habit worth naming [inference from C12, C13, C23]: the Capcom loop is usually two sections of
equal length with different harmonic weight, joined by a short bridge that takes something away
(drums, bass, or the lead) for a bar or two. That subtraction is the release, and it is cheaper and
more audible than adding a new melody.

---

## 7b. Capcom did not use the VRC6

Stated plainly because a study that claimed otherwise would be worthless: Capcom's Famicom and NES
releases of this period run on the stock 2A03, five channels, with no expansion audio, and the sound
driver differences between Rockman 1 and 2 and Rockman 3 to 6 are driver differences, not chip
differences [C14, C10]. The VRC6 is Konami's chip [C15]. Everything in section 8 under "VRC6" is our
arranger's extension of this style onto the seven voice palette the project's score already uses, and
it is marked as inference.

---

## 8. Instrument assignment

### 8.1 On the 2A03, which is how these scores actually sound [C14, C15]

| Channel | Default role in this style | Constraint |
| --- | --- | --- |
| pulse1 | lead melody or the riff, 25 percent duty, one frame note cut, volume staircase on long notes | 25 percent is the default; 75 only thickens |
| pulse2 | power fifth layer, inner line, or the delayed echo, 50 percent duty | detune it whenever it plays the same pitch as pulse1 |
| triangle | bass root on eighths, or the kick by pitch slide | no volume control, so no accents except by pitch and length |
| noise | snare, hats, electric noise hits, noise kick depending on the game | four usable rates carry the whole kit |
| dpcm | sampled kick and snare where the driver supports samples, as Tecmo did | one sample at a time, so a kick and a snare share the channel |

### 8.2 On the 2A03 plus VRC6, as our arranger will use it [inference, C15]

| Channel | Role in a Capcom style cue |
| --- | --- |
| pulse1 | lead, 25 percent, one frame cut |
| pulse2 | power fifth and inner line, detuned when doubling |
| vrc6_p1 | the octave of the root, or the third pulse of a real triad when the cue wants one |
| vrc6_p2 | delayed echo, or a second guitar line a third below |
| vrc6_saw | bass with harmonics, replacing or doubling the triangle on chorus sections |
| triangle | kick, tom slide, or the low root pedal |
| noise and dpcm | kit as on the 2A03 |

The rule that keeps this honest: the two VRC6 pulses may add size (octave, third, echo), but the
melody stays on the 2A03 pulses, because the 25 percent 2A03 lead is the sound of this style [C14,
inference]. A Capcom cue built entirely on VRC6 voices sounds like a Konami cue.

---

## 9. Human touches that read as played

- The one frame note cut is itself the performance gesture: it is what makes a machine-played pulse
  line articulate like a picked string [C14].
- The volume staircase on every held note, in 2 step increments, ending at zero [C14].
- Fine detune on any doubled pitch, 5 to 10 cents, which prevents the phase cancellation and reads as
  a second player [C14].
- Delayed echo at 30 to 50 percent volume, detuned, one eighth behind for stage cues and one sixteenth
  for boss cues [C14, inference].
- Tom slides that fall logarithmically with a value near 15, then a note-off, which is how a
  four channel mix gets a fill that sounds like a kit [C14].
- One deliberate exception per cue: a duty change, a register lift, or a single chromatic passing note
  at a fixed bar. The Mega Man series earns its distinctiveness per stage exactly this way, since all
  eight MM2 stage themes use the same palette and differ only in arrangement [C5, C12, inference].
- Never quantise the fill landing. On a 60 Hz engine the smallest push is 16.7 ms [C15], and a fill
  that lands exactly on the beat with every other voice is the one thing a frame push should fix
  [inference].

---

## 10. What to avoid

1. A third in the power chord. The signature is root plus fifth; putting the third in the dyad turns
   Mega Man into a different band [C14, S29].
2. Duty changes on percussive attacks. The series never did it, not in nine games [C14].
3. A swing feel. The syncopation is written, not swung [C14, C13].
4. Held half and whole notes as the main melodic content. 76 percent of the measured melody notes are
   a single sixteenth [C19], and the community guide's whole note-cut practice exists because notes
   are short [C14].
5. Doubling a pitch on both pulses without detuning. The two squares cancel and the cue sounds thin
   and amateur, which the guide names as the classic mistake [C14].
6. Echoing the bass or the drums [inference: the echo is a lead device in every described use, C14].
7. A stage theme in a major key as the default. Minor is 9 of 16 and 23 of 29 in the measured sets
   [C19]; the bright major cue is the deliberate exception, one per set [C4].
8. A boss theme longer than 16 bars or with a full melody. The published timing is a 1:00 loop [C11].
9. An intro before the hook in a stage theme. The style states the riff in bar 1 [C1, C4, C12].
10. Two non-diatonic chords in a row inside a 16 bar loop [inference from 95 percent diatonic measured
    in C12].
11. Sampling more than a kick and a snare on DPCM. Tecmo used the sample channel for drums and that
    was the whole technique [C7, C8].
12. Copying a Capcom riff. Everything in this file is a shape, a degree and a count, and the melody
    guard still has to pass [PLAN-V2 section 0].

---

## 11. The 32 recipes

Machine readable rows are in `data/recipes/capcom.json` (family prefix CAP). Index:

| ID | Name | Where it goes |
| --- | --- | --- |
| CAP-01 | Power fifth dyad, two pulses, 50 percent | every riff and chord |
| CAP-02 | Dotted quarter lean cell | stage riff |
| CAP-03 | One frame note cut on every melodic channel | all melodic writing |
| CAP-04 | Volume staircase release, 2 step increments | any note longer than an eighth |
| CAP-05 | Duty plan, 25 lead, 50 layer, one change per cue | whole cue |
| CAP-06 | Fine detune on any doubled pitch | doubling layers |
| CAP-07 | Delayed echo at 30 to 50 percent, detuned | stage and boss |
| CAP-08 | Triangle root eighths with an octave jump at the change | bass |
| CAP-09 | Triangle kick by logarithmic pitch slide | Rockman 6 lineage |
| CAP-10 | Noise snare on 2 and 4 from a mid rate burst | kit |
| CAP-11 | Hat on eighths, open hat in the B section | kit |
| CAP-12 | One beat fill every 4 and 8 bars | every loop |
| CAP-13 | 16 bar stage loop, 8 plus 8 plus a 2 bar link | stage theme |
| CAP-14 | 8 bar boss loop, two note riff, no padding | boss |
| CAP-15 | Stage select single figure over a pedal, 4 to 8 bars | menus |
| CAP-16 | Game start jingle, 2 bars, arpeggio to the tonic | cues |
| CAP-17 | Stage clear fanfare, 4 bars, three chords | cues |
| CAP-18 | Raised sixth in the B section of a minor stage theme | bright minor |
| CAP-19 | Relative major section inside a minor stage theme | bright mixture |
| CAP-20 | Hook stated in bars 1 and 2, no intro | every stage theme |
| CAP-21 | Layered inner line on pulse2, not a doubling | accompaniment |
| CAP-22 | Pulse call and response one beat apart | stage A section |
| CAP-23 | Bass led theme, melody sparse above it | bass line cues |
| CAP-24 | Arpeggio bass instead of power chords, piano reading | quiet stage, water stage |
| CAP-25 | Two section build with a bridge that subtracts a voice | Wily lineage |
| CAP-26 | Sampled kick and snare on DPCM | Ninja Gaiden lineage |
| CAP-27 | Odd grouping intro figure against a 4/4 body | DuckTales lineage |
| CAP-28 | Ascending arpeggio hook over a descending bass | DuckTales lineage |
| CAP-29 | VRC6 extension: octave, third and saw, melody stays on 2A03 | our palette |
| CAP-30 | Tempo ladder per cue type | whole score |
| CAP-31 | One cool set, one cute exception | whole score |
| CAP-32 | Loop seam that climbs rather than resolves | every loop |
| CAP-33 | Noise electric hit as a non drum percussion colour | texture |

---

## 12. Listening notes: ten tracks, what to listen for

Ear training only. No melody is written out. Each note names a section and a bar position and a
feature to count, and every count is something a listener can do in one pass.

1. Mega Man 1, Cut Man stage (Matsumae) [C1, C10]. Play bars 1 to 4 and count attacks on the lead
   pulse: the measured Mega Man set is 42.5 notes per bar across all channels with only 23.6 percent
   of them in the melody [C19], so most of what you hear in bar 1 is accompaniment. Then listen for
   the one frame cut: does each note stop just before the next starts, or do consecutive notes fuse?
   [C14]
2. Mega Man 1, Elec Man stage [C10]. Listen for the dotted quarter. The guide names dotted quarters as
   a signature because they make a two beat pattern lean [C14]. Count how many bars in the first eight
   contain exactly one long note that crosses the middle of the bar.
3. Mega Man 1, Boss theme [C10]. Time the loop. It is the shortest original in the game by structure
   and the album reference for the MM2 boss loop is 1:00 [C11]. Then listen to what the second pulse
   does: layering or doubling? Yamagishi names layering as the thing Capcom did that Tecmo did not
   [C7].
4. Mega Man 2, Dr Wily Stage 1 (Tateishi) [C4, C12]. Bars 1 to 8: the published analysis puts this at
   180 bpm, C minor, with the melody 95 percent diatonic and 68 percent chord tones [C12]. Listen for
   the note that is outside the key in the first two bars, and count how many bars pass before it
   happens again. Then listen to bars 9 to 16 for the second section and to the bridge for what drops
   out: published criticism describes a bridge that releases tension before the return [C13].
5. Mega Man 2, Wood Man stage [C5]. Tateishi wrote this one because the director asked for another
   song like Wily Stage 1 [C5]. Listen to the first four bars back to back with the Wily first four
   bars and name the shared device: same tempo band, same riff role for the two pulses, different
   contour. That comparison is the whole lesson of the style.
6. Mega Man 2, Heat Man stage and Bubble Man stage, compared [C5]. Heat Man was built on a bass, and
   Bubble Man was written piano-oriented for a quiet underwater place [C5]. Listen to which channel
   carries the identity in each: if the triangle is the memorable part in Heat Man and an arpeggio is
   the memorable part in Bubble Man, the recipe pair CAP-23 and CAP-24 is doing what the sources
   describe.
7. Mega Man 2, Crash Man stage [C4, C5]. It is the one cheerful, major-ish stage theme that survived
   the director's demand for cool music, and it was the only first draft accepted [C4]. Listen for
   what makes it read as "cute" against the other seven: chord quality, and a stepwise melody that
   never leaps. Then note that the series keeps exactly one of these per game, which is CAP-31.
8. Mega Man 3, Needle Man stage or Gemini Man stage (Harumi Fujita) [C9, C10]. Harumi Fujita wrote
   only these and the staff roll before leaving the project, and Yasuaki Fujita finished the score
   [C9]. Listen for a difference in melodic handwriting: which one of the two sounds like a different
   composer's dotted-quarter habit, and whether the lead duty differs.
9. Ninja Gaiden, the first stage cue [C7, C8]. Listen to the drums first, not the melody. Yamagishi
   sampled his own kick and snare for the sample channel and names that as Tecmo's signature [C7].
   Count how many distinct drum sounds you can hear and decide which are sampled and which are noise:
   the sampled ones have a pitch and a real attack, the noise ones hiss [C7, C15]. Then listen for the
   layering, which the measured Ninja Gaiden set puts at 35.2 percent melody share against Mega Man's
   23.6 [C19].
10. DuckTales, The Moon (Tonomura) [C16, C17]. Listen to the opening figure and count the grouping of
    its pulses. A fan transcription argues the intro riff is a 15 eighth-note group, that most covers
    smooth it to 4/4, and that a sharp note is added later to make it an even 16 [C17]; whether or not
    that count is right, the exercise is to hear that the intro's grouping is not the body's grouping.
    Then listen to the tempo: a prototype of the same cue runs slower, and the released version was
    sped up [C16], which is the cheapest lesson in this study about how much a tempo change buys.

---

## 13. Sources

All links read on 2026-10-21 unless stated. S29 and S45 to S47 are the existing ids from
`knowledge/MUSIC-STYLE-BIBLE.md` and `knowledge/MUSIC-HOOK-GRAMMAR.md`, cited here so the two files
cannot drift.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| C1 | Enjoy Game Japan Museum, Manami Matsumae creator page | https://museum.enjoygamejapan.online/en/creators/manami-matsumae | Three months for all Mega Man music and sound effects, four channels, the superior's instruction that melodies must be memorable, her own description of her signature as catchy and memorable, alias Chanchacorin, the Game Start jingle still performed |
| C2 | Square Enix Music Online (also VGMO), "Interview with the Mega Man 1 and 2 Sound Team: Reunited 20 Years On", November 2010 | https://www.squareenixmusic.com/features/interviews/manamimatsumae.shtml | Matsumae wrote all MM1 music and effects, Tateishi all MM2, Sakaguchi the driver; "three notes at a time"; the pleasure of reducing data to fit; Tateishi's respect for MM1 and "cool, singable instrumentals" |
| C3 | A Conversation with Manami Matsumae (koopa.tv, archived; Brave Wave arrangement) | https://web.archive.org/web/20180211131435/http:/koopa.tv/a-conversation-with-manami-matsumae | Bach Well-Tempered Clavier as her three voice training, drums studied from Propaganda, Phil Collins and Mezzoforte, the Astro Boy heroic image, the planner brief for a lively easy to remember melody, Air Man measures by her, MM2 opening built from the MM1 ending data, the composer changes game by game |
| C4 | Gaming.moe, "Interview: Takashi Tateishi, Composer at Capcom and Sound Producer at Konami" | http://gaming.moe/?p=3037 | Only Crash Man accepted from his first drafts, the director's demand for cool, studied piano, aim of hummable melodies, Wily 1 expresses a guitar sound well on Famicom |
| C5 | Rockman Corner, report on the MAGFest 2019 Tateishi talk | https://www.rockman-corner.com/2019/01/go-behind-scenes-of-mega-man-2-with.html | Cute to cool direction, Wood Man written to order after Wily 1, Wily 2 reuses Wily 1 for space, Heat Man bass based, Bubble Man piano oriented, layered melodies in Wily 1, data limits |
| C6 | Square Enix Music Online, Takashi Tateishi interview, December 2010 | https://www.squareenixmusic.com/features/interviews/takashitateishi.shtml | Aim of melodies people could hum or play in their bands, his band background |
| C7 | VG247, "Keiji Yamagishi on His Past and Future in Game Music" | https://vg247.com/keiji-yamagishi-on-his-past-and-future-in-game-music | Capcom had a lot of layering in its music; Tecmo used the sample channel for drums with self made samples because Nintendo did not share tools; no formal theory, played by ear |
| C8 | Brave Wave, "A Conversation with Keiji Yamagishi" | https://bravewave.net/interviews/a-conversation-with-keiji-yamagishi | Ninja Gaiden sampled kick and snare for DPCM, Ryuichi Nitta contributed three or four sounds, Yamagishi composed the rest and wrote the driver, the PC-9800 data entry workflow |
| C9 | Wikipedia, Mega Man 3 | https://en.wikipedia.org/wiki/Mega_Man_3 | Harumi Fujita as initial composer, the pieces she finished, Yasuaki Fujita completing the score |
| C10 | MusicBrainz, "Capcom Music Generation Famicom Music Complete Works Rockman 1 to 6" credits | https://musicbrainz.org/release/87c2827a-5f90-44dd-98c9-98f7084f13f1 | Per game composer credits for MM1 to MM6, Sakaguchi confirmed as sound programmer for 1 and 2, shared MM4 track, track titles |
| C11 | MusicBrainz, Mega Man 2 release track listing | https://musicbrainz.org/release/1f1356da-2fff-4ab9-910b-a953e922d193 | Album timings: Stage Select 0:29, Game Start 0:08, Boss 1:00, Stage Clear 0:07, Dr Wily Stages 1 and 2 2:49 |
| C12 | Hooktheory theorytab, Mega Man 2 Dr Wily Stage 1 | https://www.hooktheory.com/theorytab/view/takashi-tateishi/mega-man-2---dr-wily-stage-1 | C minor, 180 bpm, 4/4, range D sharp 3 to G sharp 5 (29 semitones), 0.89 beats per note over 160 beats, 95 percent diatonic, 68 percent chord tones, chord-bass-melody 91, chord complexity 55, melodic complexity 81, chord-melody tension 66, section labels intro chorus bridge outro |
| C13 | Cartridge Lit, "High Scores: Dr Wily Stage 1", 2020 | http://cartridgelit.com/2020/10/29/high-scores-dr-wily-stage-1 | The 150 to 180 bpm reading, liberal syncopation and minor keys as the series formula, two sections with a bridge that releases tension, the 8-bit Music Theory video reference |
| C14 | Mathew Valente (TSSF), "Rockman FamiTracker music guide", notes.txt, local file `<home>\OneDrive\Documents\FamiTracker-v0.4.6\FamiTracker-v0.4.6\Instruments\MegaManInstruments_jan6\notes.txt`, written 2008, read 2026-10-21 | local file | Power fifth as the signature harmony, dotted quarters, 25 percent leads and the 75 percent variant, no pulse width change for percussive attacks, the one frame note cut as the "NES sound" in Rockman 1 and 2, the 15 13 11 9 volume staircase, fine detune chorusing and delayed chorus, logarithmic tom slides at value 15, the 150 bpm frame table (beat 24 frames, sixteenth 2), noise starting pitches for snare and hats, triangle and noise kick differences |
| C15 | NESdev Wiki, APU and APU basics | https://www.nesdev.org/wiki/APU | Five channels, 16 volume levels, duty values, 60 Hz frame timing, noise rate table, DMC sample playback, phase reset on a high period byte |
| C16 | TheGamer, "On The Level: The Memorable Music Of DuckTales Moon Stage" | https://www.thegamer.com/ducktales-moon-stage-music/ | Tonomura composed the whole DuckTales score, the Moon theme is the most complex piece in it, the prototype runs slower and the released cue was sped up, the 2013 remaster arrangement |
| C17 | Glacius, transcription notes on DuckTales "The Moon" | https://glacius.tmont.com/music/projects/ducktales-nes-moon-theme-transcription | A fan transcription's claim that the intro riff groups in 15 eighths, that most covers smooth it to 4/4, and that a later bar adds a note to make an even 16. Cited as a fan claim, not as fact about the ROM |
| C18 | Through the Shattered Lens, "VGM Entry 37: DuckTales" | https://unobtainium13.com/2012/09/04/vgm-entry-37-ducktales/ | The DuckTales credit dispute, Sakaguchi's denial, Tonomura confirmed as composer, Tonomura's short Capcom stint in Alph Lyla |
| C19 | Primordial Paradox corpus statistics, `D:\Musikage-Corpus\style-pp\stats\nes_rock_metal.json`, generated 2026-10-21 from 86 NES-MDB pieces (Mega Man 16, Ninja Gaiden 29) | local file | Minor shares, tonics, lengths, notes per bar, melody share, voices, interval and duration histograms, chord vocabulary and harmonic rhythm, phrase and cadence shares, bass median pitch, and the normalised tempo caveat |
| C20 | VGMO, DuckTales Remastered soundtrack review | https://vgmonline.net/ducktalesremastered/ | The original DuckTales chiptunes are "surprisingly short", the Moon theme is the one track everyone can hum, Tonomura credited for the NES score |
| C21 | 8-bit Music Theory, video analysis of the Mega Man 2 soundtrack, referenced by C13 | https://www.youtube.com/watch?v=JknOdnEtwxs | Existence of a dedicated structural analysis of the MM2 score. Not watched by this worker: cited only as the reference C13 points to, so nothing in this file rests on it |
| C22 | Anatomy of Games, "The Anatomy of Mega Man 2 XIV", 2014 | https://anatomyofgames.com/2014/07/14/the-anatomy-of-mega-man-2-xiv-so-much-larger-than-life | The Wily castle third stage cue builds in pitch and intensity and drops just before the climax so the loop carries the tension. Fan criticism, treated as such |
| C23 | VGMO, "Mega Man 1 and 2 Sound Team Interview" (same transcript as C2, different host) | http://vgmonline.net/megamaninterview | Cross check for the Matsumae and Tateishi credit statements in C2 |
| S29 | Wikipedia, Power chord, as recorded in `knowledge/MUSIC-STYLE-BIBLE.md` | https://en.wikipedia.org/wiki/Power_chord | Root plus fifth and possibly octaves, no third, neither major nor minor, survives fast chord changes |
| S64 | WiKirby, Green Greens (theme), as recorded in `knowledge/MUSIC-HOOK-GRAMMAR.md` | https://wikirby.com/wiki/Green_Greens_(theme) | Contrast by mode before instrumentation, a major first section against a parallel minor second section at the same tempo and rhythmic cell |
| S45 | BBC News reporting the Hooked on Music study, as recorded in `knowledge/MUSIC-HOOK-GRAMMAR.md` | https://www.bbc.com/news/science-environment-29847739 | About 5 s average recognition, 2.29 to 2.62 s fastest |
| S47 | Dowling and Bartlett, 1981, as recorded in `knowledge/MUSIC-HOOK-GRAMMAR.md` | https://doi.org/10.1037/h0094275 | Contour carries memory inside 5 s, intervals later |

Two source quality notes. C14 is a community guide by a tracker author who rebuilt these cues by
watching them frame by frame; it is the most specific evidence available short of a ROM study and it
is treated as strong evidence for technique, not as authority on any single note. C17 is a fan
transcription and is marked as a claim every time it is used. C21 was not read or watched.

---

## 14. Limits of this document

- The only published quantitative analysis of a Capcom cue read for this card is Dr Wily Stage 1
  [C12]. One tab cannot represent four composers and thirty cues, so every other number here is
  either from the local corpus [C19], from the community guide's observed technique [C14], or marked
  as inference.
- The corpus figures come from converted MIDI, so they describe the archive's transcription as much
  as the composers' intent, and the tempo field is normalised and unusable [C19]. They are used for
  ratios and shapes only.
- The VRC6 section is our arranger's extension, not history: Capcom did not ship expansion audio on
  these games [C14, C15].
- Nothing in this file is a transcription, and the recipes in `data/recipes/capcom.json` state
  construction rules only, so no melody from these games can be reconstructed from them.
- Nothing has been rendered. The proof that these recipes work is that the arranger can realise a cue
  from row ids alone and that `tools/melody_guard.py` passes on the result.
- [C21], the 8-bit Music Theory video analysis of the Mega Man 2 score, was not watched by this
  worker. It is listed because C13 points to it, and no claim in this file depends on it.
