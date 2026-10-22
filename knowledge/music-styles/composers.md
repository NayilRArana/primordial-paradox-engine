# Twelve game composers: what each one actually does, in numbers, and what to borrow

Card t_ef135a2f (STUDY-COMPOSERS), assistant, written 2026-10-21. Scope name `composers`.
Companion files: `knowledge/MUSIC-HOOK-GRAMMAR.md`, `knowledge/MUSIC-STYLE-BIBLE.md`,
`knowledge/MUSIC-DRUMS.md`, `knowledge/MUSIC-DISSONANCE.md`, `PLAN-V2-2026-10-21.md` section 0, and
the executable recipes in `data/recipes/composers.json`.

Reference rule (PLAN-V2 section 0): every composer here was studied from published interviews, credit
records, hardware documentation and measured corpus statistics already on disk. Nothing was
downloaded, ripped, sampled, traced, transcribed or decompiled. No melody is written out anywhere in
this file: every musical statement is a shape, a scale degree, an interval, a count or a bar number.

Tagging. Every claim ends with a source id in square brackets, for example [CO8]. Section 15 has the
link and the read date for each id. Ids starting with S are the existing ones from the style bible and
the hook grammar, cited with their own links so the three files cannot drift. `[inference]` marks my
own operationalisation of a source, written so an arranger has a number to hit, not so it can be
quoted.

Why this file exists: the composition engine already knows the grammar of a hook. What it does not
know is that these twelve people solved different problems with different tools, and that the tools
are countable. Each composer gets one page: documented technique with numbers, three habits worth
copying, one thing not to copy.

---

## 1. The twelve, and the problem each one solved

| Composer | Main chip work used here | The problem they solved | Source |
| --- | --- | --- | --- |
| Koji Kondo | Super Mario Bros. (1985), SMB3 (1988), Zelda (1986) | Music that locks to movement and to a room, on three voices | [S58, CO1, CO3] |
| Hirokazu Tanaka | Metroid, Kid Icarus (1986), Mother (1989), Tetris (1989) | Atmosphere and metre on a chip with no reverb and no samples | [S10, S55, CO32] |
| Nobuo Uematsu | Final Fantasy I to III (1987 to 1990) | A long RPG with a big emotional range, on three channels | [S53, S54, CO31] |
| Koichi Sugiyama | Dragon Quest I to IV (1986 to 1990) | Loop music that never tires, written with classical grammar | [CO11, CO12, CO13] |
| Kinuyo Yamashita | Castlevania (1986) | Gothic rock drive with two leads that answer each other | [CO5, S56, S61] |
| Manami Matsumae | Mega Man (1987) | Chord feeling from one channel, melody first | [CO8, CO9, CO10] |
| Keiichi Suzuki | Mother (1989), Mother 2 (1994) | Pop songwriting on a console where RPG music sounded classical | [CO15, CO16] |
| Yoko Shimomura | Street Fighter II (1991), later RPG work | A character in six bars, with an odd grouping | [CO20, CO21, CO22] |
| Yasunori Mitsuda | Chrono Trigger (1995) | Harmony and bass doing the storytelling | [CO23, CO24] |
| Motoi Sakuraba | Tales of Phantasia (1995), Golden Sun, later symphonic work | Progressive rock played by hand, not sequenced | [CO26, CO27] |
| Michiru Yamane | Castlevania: Bloodlines (1994), Symphony of the Night (1997) | Baroque grammar plus metal, chosen before a note is written | [CO28, CO29, CO30] |
| David Wise | Donkey Kong Country (1994) | Atmosphere from 64 KB of samples, bassline first | [CO17, CO18, CO19] |

Six of the twelve wrote their defining work on the 2A03 and are directly usable as chip recipes. The
other six wrote on the SNES, the Genesis, the arcade boards or the PlayStation, so for them this file
borrows technique and states how to land it on our chip. That distinction is marked on every page.

---

## 2. What our own measurements say

Four corpus files exist and are used here. All were generated from NES-MDB MIDI transcriptions already
on disk, all normalise tempo to 120 bpm, so no tempo claim in this file comes from them.

| File | Pieces | What it covers | Source |
| --- | --- | --- | --- |
| `nobuo_uematsu.json` | 104 | FF I to III | [CO31] |
| `hirokazu_tanaka.json` | 40 | Mother / EarthBound Beginnings | [CO32] |
| `nintendo.json` | 132 | SMB, Zelda, Zelda II, Metroid, Kid Icarus, Tetris, Dr Mario, Punch-Out | [CO33] |
| `nes_rock_metal.json` | 86 | Castlevania 16, Mega Man 16, Ninja Gaiden 29, Contra 13, Kid Icarus 12 | [CO34] |

The comparison that matters for the arranger [inference from the four tables]:

| Measure | Uematsu (FF I to III) | Tanaka (Mother) | Rock family (Castlevania plus Mega Man) | Nintendo mix |
| --- | --- | --- | --- | --- |
| Major to minor | 56 : 48 | 29 : 11 | 29 : 57 | 94 : 38 |
| Chord changes per bar | 3.94 | 3.55 | 3.78 | not published in the mix |
| Melody step share | 49.2 percent | 61.8 percent | 51.6 percent | not published |
| Repeated note share of intervals | 6.0 percent | 16.2 percent | 16.5 percent | not published |
| Median melody range | 35.5 semitones | 22.5 | not published in the mix | not published |
| Median melody notes per bar | 5.3 | 4.66 | not published in the mix | not published |
| Sixteenth-note share of melody durations | 59.6 percent | 59.3 | 76.0 | not published |
| Median voices per piece | 3 | 3 | 3 | 3 |

Readings [inference]:

1. Uematsu writes the widest lines and the most chord change per bar: 3.94 changes per bar against
   Tanaka's 3.55, with a median melody range of 35.5 semitones, which is three octaves of territory.
   His identity is harmony plus arpeggio, not narrow riffing.
2. Tanaka and the rock family share one number that the others do not: roughly one melody interval in
   six is a repeated note (16.2 and 16.5 percent). That is the cheapest identity marker on the chip
   and both houses use it constantly.
3. The rock family puts 76 percent of its melody notes on a sixteenth grid. That is what "fast" means
   in countable terms: three notes in four last one sixteenth.
4. All four sets sit at a median of three voices per piece, so a four or five voice arrangement is
   already a generation beyond what these scores did.

---

## 3. Koji Kondo: the phrase that locks to movement

Documented. The first Super Mario Bros. draft was thrown away because it did not match Mario's running
speed [CO1]. The shipped Ground Theme is about 100 bpm in cut time with swing and prominent
syncopation and a periodic phrase structure [S58]. Kondo describes the Famicom's three voices as the
right hand, left hand and pedal of an electronic organ, and says his music-class chords were useful
[CO1]. Schartmann's book describes the theme as a one-measure segment and its transposition down by a
step, with the two chords moving by parallel voice leading, "like shifting your hand on a piano
without altering its basic shape" [CO3]. Kondo's own favourites are the SMB and Zelda overworld
themes [CO3].

Signature moves with numbers.

- One-measure cell plus a transposition down one step at bar 3, with the chord quality unchanged
  [CO3]. Executable as: cell of 8 to 12 notes, repeat at minus 2 semitones, no new chord quality.
- Syncopation at about 100 bpm in cut time, which is one bar per 1.2 s [S58, inference].
- Three voices assigned like an organ: right hand lead, left hand chord or bass, pedal sustained
  [CO1]. On 2A03 that maps to pulse 1 melody, pulse 2 chord or harmony, triangle bass.
- Tempo is a gameplay number, not a musical one: the loop has to match the run cycle [CO1, S58].
- In our own Nintendo mix, C is the most common tonic (38 of 132 pieces) and major beats minor 94 to
  38 [CO33], which is why this style sounds bright even when the harmony is busy.

Three habits to adopt.

1. Write the cell first, transpose it for the answer, and refuse to change the chord quality with it
   [CO3]. This is the cheapest way a bot can sound like a composer.
2. Set tempo from the player's movement or the menu's rhythm before choosing any harmony [CO1, S58].
3. Give each of the three voices a body part (lead, hand, pedal), then never let two of them do the
   same job [CO1].

What not to copy. The exact horn-call opening shape of the SMB overworld and its step transposition is
the single most quoted melody in the medium [CO3]. Copy the mechanism (cell, step shift, parallel
voice leading) with a different interval and a different rhythmic cell, and check with
`tools/melody_guard.py`. Do not reproduce the cell itself.

Quote. "In Super Mario Brothers, the background became a blue sky, and for the first time, the world
felt bright. At first I wrote songs without putting a lot of thought into them, but they didn't match
Mario's running speed, so I discarded them." [CO1](https://glitterberri.com/ocarina-of-time/special-interview-koji-kondo)

---

## 4. Hirokazu Tanaka: metre and sound world as the identity

Documented. Tanaka's stated goal on Metroid was that there be no distinction between music and sound
effects [S10]. Kid Icarus Underworld is measured at 152 bpm in 6/8, melody range 22 semitones, chord
progression novelty 88 on a scale where 50 is average [S55]. Our Mother corpus of 40 pieces gives him
the highest repeated-note share in the project, 16.2 percent of melody intervals, with the top
two-note intervals being up a step then back down, and a repeated note twice, in that order [CO32].
The same corpus puts sus4 as the second most common chord quality after plain major (679 against 836
major), and dim seventh appears 220 times [CO32].

Signature moves with numbers.

- 6/8 or compound ostinato at 150 bpm and above, with the metre doing the identifying rather than the
  melody [S55].
- Melody that is 61.8 percent stepwise with a repeated note in every phrase, median range 22.5
  semitones [CO32].
- Harmony that lives on suspended chords: sus4 is 679 of 3,117 chord beats in Mother, about one chord
  in five [CO32, inference].
- A noise channel used as part of the tune's language rather than as a drum kit, which is the Metroid
  lesson stated by the composer himself [S10].
- 4.66 melody notes per bar at the median, the sparsest of the four corpora [CO32].

Three habits to adopt.

1. Choose the metre before the melody. A compound metre at speed is a free identity marker and no
   other cue in the game can have it [S55].
2. Put a suspended chord on the weak half of every second bar and let the melody resolve it [CO32,
   inference]. It reads as colour, not as a mistake.
3. Let the noise channel carry motif material for two bars of the intro or the bridge, then hand the
   motif back to a pulse [S10, inference].

What not to copy. The Metroid title's exact noise-only texture. It works because the game is about
isolation, and it costs the melody entirely; a second cue that does the same thing makes the first one
ordinary [S10, inference].

Paraphrase, not a direct quote. Tanaka's stated goal on Metroid was that there be no distinction
between the music and the sound effects, as recorded in the existing bible
[S10](https://shinesparkers.net/interviews/hirokazu-tanaka/).

---

## 5. Nobuo Uematsu: harmony first, and the arpeggio as an instrument

Documented. Our FF I to III corpus (104 pieces) shows the richest chord vocabulary in the project:
1,484 major, 1,017 minor, 954 minor sevenths, 848 sus4, 730 major sevenths, 675 dominant sevenths,
482 half diminished, 418 diminished, 166 diminished sevenths and 98 augmented chords, at 3.94 changes
per bar [CO31]. The melody leaps as often as it steps (50.8 against 49.2 percent) and its median
range is 35.5 semitones [CO31]. The most common two-interval shape in that corpus is the octave
arpeggio and back, with the up-and-down octave figure appearing 262 times as a two-gram [CO31]. The
FF battle theme is measured separately at 150 bpm, G minor, an 8 semitone melody range, 0.88 beats per
note and chord complexity 94 [S53]. The Prelude is a single broken chord pattern with the second pulse
entering about an eighth late and slightly quieter so the pair reads as a harp with an echo [S54, S7,
S8].

Signature moves with numbers.

- Arpeggio as the harmony instrument: one pulse plays the chord one note at a time, at 1 to 3 frames
  per note, so a triad becomes a strum or a buzz without a third voice [CO31, S62].
- Seventh chords everywhere: minor seventh plus major seventh plus half diminished together are
  2,166 of the chord beats, more than the plain major chords [CO31, inference].
- Wide melody: 35.5 semitones median, half the intervals leaps, with the octave arpeggio figure as the
  fingerprint [CO31].
- Battle cues carry the complexity in harmony, not in range: 8 semitone range over a chord complexity
  of 94 [S53].
- Voice priorities measured: melody median pitch 73, inner voice 62, bass 48 on the MIDI scale, with
  the inner voice playing shorter notes than the melody (0.473 against 0.659 beats) [CO31].

Three habits to adopt.

1. Put the harmony in an arpeggio on pulse 2 and keep pulse 1 for the tune, so a chord and a melody
   exist with no third voice spent [CO31, S62].
2. Use one seventh chord per four bars as the colour, not as the resting place [CO31].
3. Copy the Prelude trick exactly: same pattern, second voice late by one eighth and two volume steps
   down [S54, S8]. It is the cheapest "two instruments" illusion on the chip.

What not to copy. The Prelude's continuous arpeggio as the whole texture for every calm cue. Uematsu
uses it once as an invocation; five cues of it turn a score into a screensaver [inference].

Quote. "When making a fantasy world for a game, The Lord of the Rings or Celtic culture are the kind
of themes that are common as the basis of many RPGs. So, Japanese RPGs end up being based on foreign
ideas of fantasy too, and what you see in those is ultimately beautiful forests, rivers, castles,
fairies and so on."
[S8](https://daily.redbullmusicacademy.com/2014/10/nobuo-uematsu-interview)

---

## 6. Koichi Sugiyama: classical grammar as an anti-fatigue device

Documented. Asked what makes music nobody tires of, Sugiyama pointed at Beethoven and Mozart and said
humanity has listened to them for two hundred years without boredom, and because game music loops for
hours every theme had to pass that test [CO11]. He chose classical grammar because the brief called
Dragon Quest a medieval knightly romance, and delivered the complete Dragon Quest I score inside a
week, of which two days went on data entry and four on writing eight pieces [CO13]. The overture took
about five minutes after, in his phrase, fifty-four years [CO11, CO13]. Its structure is a fanfare
introduction, a lyrical middle, and a return of the opening material [CO12]. He used horn fifths, the
approach of two independent parts to a perfect interval, audibly in the opening [CO12, CO13]. Baroque
texture fitted the Famicom because Baroque instruments do not linger on a note, and the chip could not
sustain one either [CO13]. Enix had the score recorded by the Tokyo Strings Ensemble in 1986, the same
year as release [CO12, CO14].

Signature moves with numbers.

- Overture form: 3 sections, fanfare (8 to 16 bars), lyrical middle (8 to 16), return (8 to 16), total
  32 to 48 bars [CO12, inference on bar counts].
- Eight cues for the whole of Dragon Quest I, written in four days: the average cue is short and
  self-contained, and jingles are part of the set [CO13].
- Articulation, not sustain: every note is short enough that the chip's decay is part of the sound
  [CO13].
- Horn fifths as the cadential approach figure, used at phrase ends where two voices move to a perfect
  interval by contrary or oblique motion [CO12, CO13].
- The three to five second rule stated independently of the recognition research: he says an audience
  gives three to five seconds to catch attention, and the answer is clarity, not novelty [CO12]. That
  agrees with the measured 5 second recognition average [S45].

Three habits to adopt.

1. Write the overture as three sections with a real return, so the last 8 bars are not new material
   [CO12].
2. Ban long notes from fast cues. If a note would need sustain, split it into two articulated notes
   [CO13].
3. Use one classical cadential figure (horn fifths, a suspension, a Neapolitan) as the house cadence
   and put it at every loop seam [CO12, inference].

What not to copy. The four-note fanfare shape that opens the Dragon Quest overture. It is the most
recognisable four notes in Japanese games and it is exactly the kind of thing `tools/melody_guard.py`
exists to catch. Take the function (a fanfare that states root, fifth and octave) and use a different
rhythm and a different contour [CO11, inference].

Quote. "But those five minutes contained the fifty-four years I had lived up to that point."
[CO11](https://museum.enjoygamejapan.online/en/creators/koichi-sugiyama)

---

## 7. Kinuyo Yamashita: two leads that answer instead of doubling

Documented. Castlevania was her first work at Konami. She composed at the piano, performed pieces for
the sound team leader, and only entered the data once he approved, because there were no sequencers
[CO5]. The rock approach "came naturally", aimed at the dynamism of the player's movement and the
gothic background, and she did not work to a plan [CO5]. Vampire Killer is a 16 bar loop in D minor
with heavy use of the flat seven chord, a 41 semitone melody range, 0.62 beats per note over 64 beats,
82 percent diatonic and 76 percent chord tones with punchy syncopation [S56, S61]. In that texture the
two square voices take turns, one falls silent so the other can speak, they chase each other a beat
apart and arc in opposite directions [S61]. She and Satoe Terashima were the two composers, which she
confirmed for the fortieth anniversary [CO6].

Signature moves with numbers.

- 16 bar loop, one bass pulse that never stops, 0.62 beats per note which is about 1.6 melody notes
  per beat [S56].
- Two leads, one beat apart, opposite contours, one silent at a time [S61].
- Flat seven chord in a minor key as the default colour [S61].
- Dense sixteenth surface: in our rock family corpus, 76 percent of melody notes last one sixteenth,
  and Castlevania contributes 16 of those 86 pieces [CO34].
- Range is used for drama, not for the hook: 41 semitones across the cue [S56].

Three habits to adopt.

1. Write the answer voice one beat behind the call and give it the opposite contour [S61].
2. Keep an unbroken bass pulse under everything, and let the bass rest only at the loop seam [S56,
   inference].
3. Use the flat seven as the chord that says "this is a horror cue", once per four bars [S61].

What not to copy. The Vampire Killer bass line. It is the most quoted NES rock bass in existence and
its rhythm is the hook; replace the rhythm, keep the harmony idea [inference].

Quote. "I aimed to create music suitable for the image of the game, particularly noting the dynamism
with which the player moves and the gothic images of the background."
[CO5](https://vgmonline.net/kinuyoyamashitainterview)

---

## 8. Manami Matsumae: chord feeling from a single channel

Documented. She wrote all of Mega Man's music and sound effects and entered the data in three months
[CO9]. Her superior told her the melodies had to be memorable, and she says that instruction is the
signature she still works to: melody-focused, catchy, with chord modulation as a favourite device
[CO8]. On technique: the NES has three channels, one must be dedicated to the chord, so she used
arpeggios and inner-voiced chords, "like creating pieces of a puzzle" [CO8]. Elsewhere she says she
had "only three notes at a time" and always wondered how to get the feeling of chords with a melody
while sound effects played over it [CO10].

Signature moves with numbers.

- One channel reserved for the chord, played as an arpeggio or an inner-voiced figure, leaving a lead
  and a bass [CO8].
- Melody-first priority: if the arpeggio and the tune compete for a pulse, the arpeggio moves to
  sixteenths or is dropped for a bar [CO8, inference].
- Mechanical, cool colour rather than warm: her first read of the images was "robotic coolness" with a
  sorrowful inner side [CO9].
- Dense articulation: the rock family corpus puts 76 percent of melody notes on a sixteenth and only
  12.5 percent on a duration of two sixteenths [CO34].
- Wide leaps are allowed once: 8.3 percent of intervals in that corpus exceed 19 semitones, which in
  practice is the octave or larger jump that arrives at a phrase peak [CO34].

Three habits to adopt.

1. Reserve one channel for harmony and never borrow from it mid phrase [CO8].
2. When the arrangement is too dense, thin the arpeggio to the beat instead of thinning the melody
   [CO8, inference].
3. Modulate once per cue, at the B section, and let the melody keep its shape across the modulation
   [CO8].

What not to copy. The exact arpeggio pattern of Mega Man 1's opening stage. It is the template half
the chiptune scene already uses; the borrowable idea is the channel budget, not the pattern
[inference].

Quote. "The NES only has three sound channels, so it was particularly strenuous to work with. One
channel must be dedicated to the chord, so I had to use arpeggio and inner voiced chords."
[CO8](https://kotaku.com/mega-man-composer-manami-matsumae-doesnt-miss-the-9-6-g-1846809139)

---

## 9. Keiichi Suzuki: the pop song hiding inside the cartridge

Documented. Itoi asked for pop music with real vocals, with instrumental versions used in the game,
and Suzuki notes that RPGs of the period had to arpeggiate to express chords, so most game melodies
sounded classical, and there was nothing like real pop on the Famicom then [CO15]. For Mother 2 the
brief flipped to instrumentals, and he reached for ambient and world music as touchstones, while the
requests still came in scene by scene: Arabian for the desert, rock and roll for the club, something
that spurs you on for the overworld [CO15]. The sound is described as Beatles-like melody over Beach
Boys-like percussion, with Godley and Creme's L as an influence on the Eight Melodies motif [CO16].
Eight Melodies itself was designed as a tune anyone could hum and play with one finger, inside a three
note simultaneous limit [S9, S11].

Signature moves with numbers.

- Song form before game form: verse and chorus proportions rather than a loop with a bridge [CO15,
  inference].
- A vocal-shaped phrase: 2 bars of lyric, 1 bar of breath, then the answer [CO15, inference].
- Percussion as arrangement, not as a kit: the Beach Boys reference is about tom and hand patterns
  under a pop melody [CO16].
- A three note limit forces the harmony into the melody itself, so the tune carries its own chords
  [S9, CO10].
- One motif reused as a game mechanic (Eight Melodies collected in eight pieces) so repetition is
  story, not padding [CO16].

Three habits to adopt.

1. Write the tune as if a singer had to breathe: one clear rest per 4 bars, on the melody voice
   [CO15, inference].
2. Steal arrangement ideas from pop production (tom patterns, backing "ooh" figures) and put them on
   the noise and second pulse channels [CO16, inference].
3. Make one motif do double duty as the thing the player collects or recognises, so the loop is
   motivated [CO16].

What not to copy. The Eight Melodies contour, which is the emotional climax of an entire franchise and
is protected by more than copyright in players' memory [inference]. Also do not copy the trick of a
hummable tune with no harmonic motion at all: Mother gets away with it because the whole game is about
childhood, and our title screen is not [inference].

Quote. "For Mother, my original goal for the first game was to write pop music. This was at Shigesato
Itoi's request. He wanted me to make pop music with real vocals, and then use instrumental versions of
those songs in the game." [CO15](https://shmuplations.com/ksuzuki)

---

## 10. Yoko Shimomura: the odd grouping, and a classical ear in a rhythm game

Documented. On Guile's theme she says the thing people mention most is the intro being six measures:
music usually divides into four-bar segments, but this repeats two measures plus one, twice, and those
three measures were the first thing that came to her [CO20]. She came from a classical background, was
not prepared to write rhythm-focused music and says she has always tried to hide rhythm "in the vague
gaps between tones" [CO21]. For Street Fighter II she confirmed each character's homeland before
writing, asked for a unique sound effect per stage, and describes Blanka as a major-key rhythm track
with a minor melody on top [CO21, CO22].

Signature moves with numbers.

- Odd grouping: a 3 bar unit stated twice, giving a 6 bar intro against a 4 bar body [CO20].
- Polyrhythm of mode: major rhythm bed, minor melody, held for a whole section [CO22].
- Character first, music second: two or three adjectives about a character converted into one tempo,
  one chord quality and one rhythmic cell [CO20, inference].
- Rhythm hidden in the gaps: syncopation created by rests rather than by accents, so the grid is
  ambiguous without a written polyrhythm [CO21, inference].

Three habits to adopt.

1. Give one cue in the score a 3 bar unit inside a 4 bar frame. It costs nothing and it is instantly
   recognisable [CO20].
2. Put a major chord bed under a minor melody for a whole 8 bars before resolving [CO22].
3. Ask "what does this character brood about" and let the answer choose the chord quality before the
   tune [CO20].

What not to copy. The six-measure Guile intro figure itself. Use the 3 plus 3 mechanism with a
different internal rhythm [inference].

Quote. "But Guile's theme repeats two measures plus one twice, so many find it striking, I think."
[CO20](https://eventhubs.com/news/2019/dec/31/creator-guiles-theme-yoko-shimomura-explains-why-she-thinks-iconic-background-tune-became-so-popular)

---

## 11. Yasunori Mitsuda: harmonic storytelling, and the bass as the key keeper

Documented. He describes the Chrono Trigger opening cue as Dsus4, then Esus4 over F sharp, then Dsus4
over F: when the bass rises from D to F sharp the next chord sends the bass back from F sharp to F, so
"time goes back", and the closing cue moves the same shape with the bass going F sharp to G, so time
moves forward [CO23]. He wrote both in D and then moved the closer to D flat to add sadness [CO23]. He
gives the bass the highest priority because the SNES had eight notes with many tension notes and if the
bass disappeared the sense of key went with it [CO23]. Frog's Theme is minor in its key but does not
feel minor because of heavy substitute chords [CO23]. With only four field sounds available he faked
delay using the psychoacoustic effect where an initial delay is still heard after the sound stops
[CO23]. In the same stream he mentions losing over 200 sketched songs and developing a stomach ulcer
[CO23, CO24].

Signature moves with numbers.

- One harmonic shape, two directions: the same sus4 chord family with the bass moving up in the opening
  cue and up again to a different degree in the closer, one semitone apart in key [CO23].
- Suspended chords that resolve by bass motion, not by the upper voices [CO23, inference].
- Substitutions in a minor key so the mode is ambiguous: several chords per phrase outside the natural
  minor set [CO23].
- Bass priority rule: the bass gets the strong beats and the clearest pitch, and nothing else may
  occupy its register [CO23].
- Key change of one semitone as an emotional device (D to D flat) [CO23].

Three habits to adopt.

1. Write the bass line before the melody in any cue that carries story, and let the melody avoid the
   bass register entirely [CO23].
2. Use the same chord shape twice in a cue with the bass arriving from a different side, up in one
   place and down in the other, so "forward" and "back" become audible [CO23].
3. Add one substitute chord per 4 bars in a minor cue, so the key is felt but never announced [CO23].

What not to copy. The exact Dsus4 to Esus4/F sharp to Dsus4/F progression. It is specific, famous and
one search away. Keep the principle: a suspended family plus contrary bass motion [inference].

Quote. "So if the bass disappears, you lose the sense of tonality. So I gave the bass the highest
priority so that it wouldn't be drowned out by sound effects."
[CO23](https://chronocompendium.com/wiki/index.php/March_14,_2025_CT_30th_Music_Stream_with_Yasunori_Mitsuda)

---

## 12. Motoi Sakuraba: played by hand, and stylised rather than imitated

Documented. He is entirely self-taught, says he knows "next to nothing about music theory", and came
to orchestral writing to meet demand rather than from training [CO26]. His background is a keyboard,
bass and drums progressive rock trio called Deja-vu [CO27]. His working method is the point: he
composes, mixes and finishes everything himself, plays every part by hand, and says that if you leave
music to machines it will sound mechanical, so he does not make sequenced music [CO27]. He also says
that on FM, trying to mimic real instruments makes the sound indistinct or plain weird, so he writes
to the instrument's own character [CO27].

Signature moves with numbers.

- Hand-played timing and velocity on every part, which on our chip means 1 to 3 frame deviations and a
  per-note volume nibble rather than a fixed grid [CO27, S62, S63].
- Drum patterns written as a drummer's limbs, not as a loop: kick, snare and hats placed by beat
  position with the fills played, not pasted [CO27, inference].
- Stylised lead sound: a pulse with a narrow duty and a fast decay reads as a lead guitar without ever
  claiming to be one [CO27, inference].
- Progressive rock architecture: 3 to 4 sections, a meter or tempo change at least once per cue, and a
  keyboard-solo section that is a real 8 to 16 bar feature [CO26, CO27, inference].
- Prolific output as a design constraint: he says that even with five projects at once he has never
  been unable to write, because composition itself is what he enjoys [CO26].

Three habits to adopt.

1. Write the drum part as limbs: one hand on hats, one on snare, foot on kick, then let one limb
   improvise a fill every 8 bars [CO27, inference].
2. Never let a cue run without a humanising deviation for more than 4 bars [CO27, S62].
3. Give the second pulse one 8 bar solo per cue where it is the lead, and let the melody instrument
   become the accompaniment [CO26, inference].

What not to copy. Do not imitate Sakuraba's own imitation problem: he says mimicking real instruments
on FM makes them indistinct [CO27]. On 2A03 the equivalent failure is a pulse trying to be a violin by
adding vibrato everywhere; vibrato should start after the attack, not during it [S62, S63].

Quote. "I think that if you leave music to machines, then the music itself will sound mechanical, so I
don't make so-called sequenced music; I play everything myself by hand."
[CO27](https://shmuplations.com/motoisakuraba)

---

## 13. Michiru Yamane: decide the world, then the notes

Documented. Her university thesis was on Bach, so she was steeped in classical but dark music, and she
says she does not want that to become a stereotype [CO28]. Her style is described as drawing on
baroque, classical and rock, with Bach and Yellow Magic Orchestra as prominent influences [CO30]. Her
method, in her own words: at the very start she determines the bigger picture, whether the piece is
classical, heavy metal or something regional, then sits at the piano and drafts [CO29]. For Bloodlines
she started listening to a lot more rock, analysed the rhythmic styles and guitar phrases of many
artists, names Dream Theater, and says that for boss battles nothing is as effective as progressive
rock [CO29].

Signature moves with numbers.

- Genre declared per cue before composition: one of classical, metal, regional, chosen as a whole
  [CO29].
- Baroque grammar over a rock pulse: a continuous quaver or semiquaver line (8 or 16 per bar) against a
  backbeat [CO28, CO30, inference].
- Keyboard-led boss music: the lead is a soloist, not a singer, so phrases are 8 to 16 bars with
  sequential development [CO29, inference].
- Two chord vocabularies in one cue: a modal pedal for the atmosphere section, then functional
  dominant motion for the fight [CO28, inference].
- Art as the trigger: she looks at the illustrator's work first and composes from it [CO29].

Three habits to adopt.

1. Write one line per cue declaring classical, metal or regional, and let that line decide duty, tempo
   and drum density before a note exists [CO29].
2. Use a continuous semiquaver bass as the "baroque engine" under a rock backbeat, which is one
   triangle and one noise channel doing all the work [CO28, inference].
3. Keep a sequential development section in every boss cue: state the cell, sequence it up twice, then
   break it [CO29, inference].

What not to copy. The Symphony of the Night organ toccata opening as a texture. It is the most
imitated gothic game opening there is, and imitating it makes a cue read as a reference rather than as
a piece [inference].

Quote. "At the very start I like to determine the bigger picture. Will this be a classical piece,
heavy metal, something more regional? Once I've arrived at a basic premise, I sit down at the piano and
begin working out drafts." [CO29](https://videogameforums.com/t/meet-the-people-behind-the-art-and-soundtrack-of-castlevania-sotn.17850)

---

## 14. David Wise: bassline first, atmosphere by detuning everything

Documented. On Donkey Kong Country the music had 64 KB of sample memory, less than half a second of CD
quality audio, so he adapted the wave sequencing idea from the Korg Wavestation: small segments played
back in sequence [CO19]. For Aquatic Ambience the bassline came first, built from eight waveforms
played in sequence while he experimented with the chip, with a vocal sample plus a harp sample for the
arpeggios, and he describes the theme as "sad and uplifting at the same time", written after a failed
relationship: "I always felt as though I was drowning" [CO17]. A fan analysis of the cue counts it at
75 bpm in 4/4, roughly two minutes before it loops back to section two, with a major seventh chord
containing a semitone clash, a minor eleventh chord, reverb set slightly off the grid, panning that
chases the dry signal, and heavy pitch bending on the lead [CO18].

Signature moves with numbers.

- Sample memory economics as a compositional rule: a short set of waveforms, sequenced, reused
  [CO19].
- 75 bpm in 4/4, one bar every 3.2 s, and a 2 minute arc before the loop returns to section two
  [CO18].
- A major seventh with the tonic and the raised tonic sounding together as the signature dissonance
  [CO18].
- Reverb faked by a delayed, quieter copy, with the delay deliberately not on the grid [CO18, S62].
- Pitch bend on long lead notes, and volume swells shaped like breathing in and out [CO18].

Three habits to adopt.

1. Write the bassline first, then the pad, then the melody, and keep the melody in a different register
   from the bass at all times [CO17].
2. Fake reverb with a quieter copy of the lead at 3 to 6 frames delay, panned to the other side, and do
   not quantise the delay [CO18, S62].
3. Use one semitone clash inside a seventh chord as the signature colour of a whole cue, and resolve it
   only at the section change [CO18].

What not to copy. Do not try to reproduce sample-based textures on 2A03. The chip has no samples worth
the name, and a pulse doing an impression of a breathy choir reads as a broken pulse [CO19, inference].
Also do not copy the Aquatic Ambience chord progression, which the fan analysis spells out note by
note [CO18].

Quote. "As much as I'd wanted the relationship to work, I always felt as though I was drowning."
[CO17](https://mariowiki.com/Aquatic_Ambience)

---

## 15. Composer by strength

Ratings are 1 to 5 and are mine, from the evidence column, not the composers' own claims [inference].
5 means the technique is the reason the catalogue is remembered; 3 means it is competent and present;
1 means it is not a feature of that composer's work.

| Composer | Melody | Rhythm | Harmony | Drums | Form | Humor | Atmosphere | The evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Koji Kondo | 5 | 5 | 3 | 3 | 4 | 4 | 4 | Cell plus step transposition, tempo set by run speed, organ voice split, 94 major against 38 minor [CO1, CO3, CO33] |
| Hirokazu Tanaka | 3 | 5 | 4 | 3 | 4 | 3 | 5 | 6/8 at 152 bpm, chord novelty 88, 16.2 percent repeated notes, sus4 as one chord in five, music and effects merged [S55, S10, CO32] |
| Nobuo Uematsu | 5 | 3 | 5 | 3 | 4 | 3 | 4 | 3.94 changes per bar, 2,166 seventh chord beats, 35.5 semitone median range, octave arpeggio fingerprint [CO31, S53, S54] |
| Koichi Sugiyama | 5 | 3 | 4 | 2 | 5 | 2 | 3 | Three section overture with return, horn fifths, eight cues in four days, no long notes [CO11, CO12, CO13] |
| Kinuyo Yamashita | 4 | 5 | 3 | 3 | 4 | 2 | 4 | 16 bar loop, 0.62 beats per note, two leads one beat apart with opposite contours, flat seven [S56, S61] |
| Manami Matsumae | 5 | 4 | 3 | 3 | 3 | 4 | 3 | One channel reserved for chords, arpeggio as harmony, 76 percent sixteenth surface, one modulation per cue [CO8, CO9, CO34] |
| Keiichi Suzuki | 5 | 3 | 3 | 4 | 4 | 5 | 3 | Pop song form with vocal rests, percussion as arrangement, three note limit, one motif as a game mechanic [CO15, CO16, S9] |
| Yoko Shimomura | 5 | 4 | 4 | 3 | 4 | 4 | 3 | 3 plus 3 bar intro in a 4 bar frame, major bed under minor melody, character adjectives to chord quality [CO20, CO21, CO22] |
| Yasunori Mitsuda | 4 | 2 | 5 | 2 | 4 | 2 | 5 | One chord shape with the bass moving both ways, substitute chords, bass priority, semitone key shift [CO23] |
| Motoi Sakuraba | 4 | 5 | 4 | 5 | 4 | 3 | 3 | Hand-played parts, limb-written drums, progressive rock sections with a keyboard feature, no sequenced feel [CO26, CO27] |
| Michiru Yamane | 4 | 4 | 4 | 4 | 4 | 2 | 5 | Genre declared per cue, baroque semiquaver engine over a backbeat, sequential boss development [CO28, CO29, CO30] |
| David Wise | 4 | 3 | 4 | 3 | 3 | 2 | 5 | Bassline first, 8 waveforms sequenced, major seventh with a semitone clash, off-grid reverb and panning chase [CO17, CO18, CO19] |

Reading of the table [inference]. Nobody in this list is strong at all seven. The four with a 5 in
melody get it from four different mechanisms: a transposed cell (Kondo), seventh-chord arpeggios
(Uematsu), an overture with a return (Sugiyama), and a single channel reserved for harmony (Matsumae).
So "write a better melody" is not one operation; it is a choice between four operations, and the
arranger should name which one it is using.

---

## 16. Cross cutting: drums, bass, dissonance, form, tempo, instruments

### 16.1 Drum and bass habits by house

| House | Bass habit | Drum habit | Source |
| --- | --- | --- | --- |
| Nintendo (Kondo, Tanaka) | Walking or pedal, with the triangle carrying a stepwise contour under a wide melody | Noise as punctuation, often one hit per beat plus a fill at the seam, no kit illusion | [CO1, CO3, S58, inference] |
| Square (Uematsu, Mitsuda) | Bass is the key keeper: strong beats, clear pitch, protected register | Sparse: noise marks the bar line, and the harmony does the work | [S53, CO23, CO31] |
| Konami (Yamashita, Yamane) | Unbroken pulse, flat seven harmony, one note per eighth at speed | Rock kit on noise: kick on 1 and 3, snare on 2 and 4, hats on eighths, all by noise pitch and decay | [S61, CO28, CO34] |
| Capcom (Matsumae) | Bass locks to the riff, one pitch per sixteenth in fast stages | Noise drive with a hard backbeat, melody share only about a quarter of the notes | [CO8, CO34] |
| Enix (Sugiyama) | Functional bass, root and fifth, march or waltz patterns | Minimal: a march snare or a timpani substitute, never a rock kit | [CO12, CO13] |
| Mother (Suzuki, Tanaka) | Simple root motion, pop bass, often a step pattern | Arrangement-level percussion: toms and hand patterns, not a rock kit | [CO15, CO16, CO32] |

### 16.2 The dissonance each style tolerates

Measured non diatonic shares from the hook grammar: 5 percent (Dr Wily Stage 1), 9 percent (SMB3
Overworld), 18 percent (Vampire Killer), 20 percent (FF battle) [S51, S52, S56, S53]. What each house
does with the notes outside the key [inference unless sourced]:

- Kondo: one accidental, usually a raised fourth or a flat seventh, on a weak beat, repeated in the
  same place each loop [S52, inference].
- Tanaka: suspended chords instead of accidentals, sus4 as a structural chord, dim7 as a colour
  [CO32].
- Uematsu: functional sevenths and ninths, half diminished as a passing chord, augmented as a single
  beat [CO31].
- Sugiyama: classical chromatic approach, horn fifths at cadences, no blues colour [CO12].
- Yamashita: flat seven as the default, plus a chromatic passing note in the bass [S61].
- Matsumae: modulation as the dissonance, so the clash arrives at a section boundary rather than inside
  a phrase [CO8].
- Suzuki: pop major sevenths and added sixths, no functional dissonance to resolve [CO15, CO16].
- Shimomura: mode against mode (major bed, minor tune) rather than chromaticism [CO22].
- Mitsuda: sus4 and sus2 with substitutions, so the key is ambiguous but every note is diatonic to
  something [CO23].
- Sakuraba: modal interchange inside a rock frame, one borrowed chord per section [CO27, inference].
- Yamane: baroque chromaticism over a rock pedal, sequential rather than functional [CO28, CO29].
- Wise: a semitone clash held inside a major seventh chord as the identity of the cue [CO18].

Rule for the arranger [inference]: pick the house, then use its own tolerance number. One or two
coloured notes per 4 bar phrase for the Nintendo and Capcom houses, three to four for the Konami and
Square houses.

### 16.3 Form and loop lengths

- 16 bars is the measured workhorse (Vampire Killer, 16 bar loop [S61]; SMB3 64 beats of melody
  [S52]); 8 bars is the phrase unit inside it [inference].
- Sugiyama's overture is the exception: 32 to 48 bars of through-composed material with a return
  [CO12].
- Wise's atmospheric cue runs about 2 minutes before the loop returns to section two [CO18], which is
  five times a NES loop and needs a different budget: fewer sections, longer harmonic rhythm.
- Suzuki's Mother cues behave like songs: verse, chorus, breath, repeat [CO15, inference].
- Every house uses the changed ending at the seam; the hook grammar gives the ratio, one changed
  ending every second statement [S49, S64].

### 16.4 Tempo ranges

Published tempos only, since our corpus normalises to 120 bpm [CO31, CO32, CO33, CO34]:

| Cue type | Tempo | Source |
| --- | --- | --- |
| Overworld, catchy | 100 to 120 bpm, cut time, swing | [S58] |
| Stage, rock | 150 to 180 bpm | [S59, S51] |
| Boss battle | 150 bpm with dense harmony | [S53] |
| Compound metre atmosphere | 152 bpm in 6/8 | [S55] |
| Waltz or title | 104 bpm in 3/4 (our own title theme v2) | [PLAN-V2 section 1] |
| Atmospheric, sampled era | 75 bpm | [CO18] |
| Title or menu, pop | 100 to 120 bpm, with vocal phrasing (our Mother corpus is normalised to 120 bpm, so this band is inference from the pop reference) | [CO15, CO32] |

### 16.5 Instrument assignment on 2A03 and VRC6

2A03, five channels: two pulses with 4 duty settings, triangle with no volume control, noise with 16
rates and a periodic mode, and DPCM [S63].

| Role | 2A03 assignment | What the houses do | Source |
| --- | --- | --- | --- |
| Lead melody | Pulse 1, duty 0.5 for hollow, 0.25 for reedy, 0.125 for thin | Matsumae changes duty at phrase boundaries; Yamashita uses 0.5 for the answering voice | [CO8, S61, S62] |
| Harmony or second lead | Pulse 2, arpeggio or countermelody | Uematsu arpeggiates the chord; Yamashita answers one beat later; Matsumae reserves the channel | [CO31, S61, CO8] |
| Bass | Triangle, one pitch per beat or eighth | Yamashita never stops the pulse; Mitsuda's priority rule applies here | [S56, CO23] |
| Drums | Noise, pitch and decay per hit, periodic mode for metal | Konami rock kit; Enix march snare; Nintendo punctuation | [S61, CO12, S62] |
| Kick or sample | DPCM, 1 to 2 KB per sample | Capcom and Tecmo sampled drums; Sugiyama did not | [C8, C7, CO13] |

VRC6, three extra channels (two pulses plus a sawtooth), the expansion our arranger already targets
[PLAN-V2 section 1]:

| Role | VRC6 assignment | Which composer's habit it serves |
| --- | --- | --- |
| Sawtooth bass or cello | VRC6 saw, one octave below the pulses | Mitsuda's bass priority, Yamane's baroque engine |
| Third pulse for a real triad | VRC6 pulse 1, held, duty 0.5 | Sugiyama's three part writing, Kondo's organ left hand |
| Fourth pulse for a detuned double | VRC6 pulse 2, 3 to 8 cents flat, 1 to 2 frames late | Uematsu's shimmer, Wise's off-grid copy |
| Chord pad | Sawtooth with a slow volume staircase | Wise's pad, Yamane's organ |

### 16.6 Human touches that read as played

The hook grammar lists 11 gestures with a chip legal route for each [S62, S63]. The composers here add
four more, each attributable:

1. Play the part before entering it: Yamashita performed at a keyboard for approval, then typed the
   data, and says she could not have composed without playing [CO5]. On our side that means generating
   the line with a 1 to 3 frame timing spread on a non-bass voice, never on the bass [inference].
2. Decide the genre in one word and keep it: Yamane declares classical or metal per cue [CO29]. A cue
   that drifts between styles reads as an edit, not as a performance [inference].
3. Tell the story through the bass: Mitsuda's F sharp to F is the musical equivalent of a camera
   rewinding [CO23].
4. Let one channel be an odd length: Shimomura's 3 plus 3 [CO20]. Human listeners forgive an odd unit
   if it repeats.

### 16.7 What to avoid, in one list

1. Do not copy a hook. Nine of the twelve sections above name the specific figure to leave alone; the
   guard is `tools/melody_guard.py` and it is not optional [PLAN-V2 section 6 item 5].
2. Do not write a cue with no repeated note and no leap. Every house in section 2 uses at least one of
   those, most use both [CO31, CO32, CO34].
3. Do not let a sustained pad fill the melody register [CO23].
4. Do not use the same duty for a whole cue [S62].
5. Do not put an arpeggio on all three melodic channels at once, which is the "AI chord" sound the
   whole PROJECT is trying to escape [inference].
6. Do not write an intro longer than 4 bars for a looping cue; the hook grammar's first five seconds
   rule is measured, not stylistic [S45, S47].
7. Do not mix two houses' drum languages in one cue: a march snare under a rock backbeat reads as a
   mistake, not as fusion [inference].

---

## 17. Listening notes: 12 tracks, what to listen for

Ear training only. No melody is written out. Each note names a track, a section and a bar position,
and a count a listener can do in one pass.

1. Super Mario Bros., Ground Theme (Kondo) [S58, CO3]. Bars 1 to 4. Count the attacks in bar 1, then
   count them again in bar 3. If the second group sits one step lower with the same shape, you are
   hearing the measured one-measure cell plus transposition. Then listen for the swing: it is cut time
   at about 100 bpm, not straight eighths.
2. Super Mario Bros. 3, Overworld (Kondo) [S52]. Bars 1 to 8. The analysis gives 15 semitones of
   range, 0.89 beats per note and 81 percent chord tones. Listen for the one leap larger than a fourth
   and note which beat it lands on; then check that it lands there again the next time the phrase
   comes round.
3. Metroid, title and area cues (Tanaka) [S10]. The whole first minute. Ask one question: is this
   sound a melody or an effect? Tanaka's stated goal was that there be no distinction. Count how many
   distinct noise colours you can hear before a pitched note appears.
4. Kid Icarus, Underworld (Tanaka) [S55]. Bars 1 to 8. Count the beats in a bar: it is 6/8 at 152 bpm,
   so three pulses per beat group and two groups per bar. Then listen for the chord change that arrives
   somewhere you did not expect; the measured progression novelty is 88 where 50 is average.
5. Final Fantasy, Prelude (Uematsu) [S54, S8]. Bars 1 to 4, twice. First pass: count the notes in the
   arpeggio per bar. Second pass: listen only to the second pulse and find where it enters relative to
   the first. It is about an eighth late and slightly quieter, which is the whole trick.
6. Final Fantasy, battle theme (Uematsu) [S53]. Bars 1 to 8. The melody spans only 8 semitones and
   there are nearly four chord changes per bar. Listen for the moment the harmony moves and the tune
   does not. That is what "identity from rhythm against harmony" means in practice.
7. Castlevania, Vampire Killer (Yamashita, Terashima) [S56, S61]. Bars 1 to 16, then the loop. Find the
   bar where one square voice goes silent and the other speaks. Note whether the two voices move in the
   same direction or opposite ones. Then count the bass pulses in the 16 bars: there should be no gap.
8. Dragon Quest, Overture (Sugiyama) [CO12, CO13]. Whole cue. Mark the three sections by ear and count
   the bars in each. Then listen to the last note of the fanfare and the first note of the lyrical
   middle: the join is the lesson. Finally, listen for two voices approaching a perfect interval at a
   cadence, which is the horn fifths he names himself.
9. Mega Man, Cut Man stage (Matsumae) [CO8, CO9]. Bars 1 to 8. Listen for three things only: the tune,
   the bass, and the arpeggio. Decide which channel you would give up if you had to lose one, then note
   that Matsumae reserved one channel for the chord and did the rest with two.
10. Street Fighter II, Guile's theme (Shimomura) [CO20]. The intro, all of it. Count the bars. It is 6,
    built as 3 plus 3, against a body that is in 4. Then hum the first 3 bar unit and see whether it
    feels like it wants a fourth bar; if it does, that is exactly the tension she describes.
11. Chrono Trigger, the opening cue and the closing cue (Mitsuda) [CO23]. First 8 bars of each. Listen
    only to the bass. In the opener the bass rises and then steps back; in the closer it rises and keeps
    going. Same chord family, opposite story. Then note that the closer is one semitone lower in key.
12. Donkey Kong Country, Aquatic Ambience (Wise) [CO17, CO18]. The first 30 seconds, then the section
    where the drums enter. The tempo is 75 bpm, one bar every 3.2 s. Count how many bars pass before
    the lead instrument changes, and listen for the reverb copy arriving late and slightly off the
    grid on the other side.

---

## 18. The recipes

`data/recipes/composers.json` holds 32 executable recipes, CMP-01 to CMP-32, each with when to use,
parameters in frames, semitones, bars and volume steps, forbidden combinations, and the source id it
comes from. Index:

| Id | Recipe | From |
| --- | --- | --- |
| CMP-01 | Cell plus step transposition | Kondo [CO3] |
| CMP-02 | Parallel voice leading, same shape new root | Kondo [CO3] |
| CMP-03 | Tempo locked to movement | Kondo [CO1] |
| CMP-04 | Organ three part split | Kondo [CO1] |
| CMP-05 | Compound metre ostinato identity | Tanaka [S55] |
| CMP-06 | Noise as motif carrier | Tanaka [S10] |
| CMP-07 | Repeated note pulse with one frame gap | Tanaka, rock family [CO32, CO34] |
| CMP-08 | Sus4 as a structural chord | Tanaka [CO32] |
| CMP-09 | Chord via arpeggio on one pulse | Matsumae, Uematsu [CO8, CO31] |
| CMP-10 | Late quiet second voice (harp echo) | Uematsu [S54, S8] |
| CMP-11 | Narrow insistent riff over rich changes | Uematsu [S53] |
| CMP-12 | Secondary dominant every 8 bars | Uematsu [CO31] |
| CMP-13 | Overture with a real return | Sugiyama [CO12] |
| CMP-14 | Horn fifths approach figure | Sugiyama [CO12] |
| CMP-15 | No note longer than an eighth | Sugiyama [CO13] |
| CMP-16 | Two leads, one beat apart, opposite contours | Yamashita [S61] |
| CMP-17 | 16 bar loop, unbroken bass pulse | Yamashita [S56] |
| CMP-18 | Flat seven colour chord | Yamashita [S61] |
| CMP-19 | One modulation per cue, melody keeps its shape | Matsumae [CO8] |
| CMP-20 | Channel budget: one reserved for harmony | Matsumae [CO8] |
| CMP-21 | Pop phrase with a breath rest | Suzuki [CO15] |
| CMP-22 | Percussion as arrangement (tom and hand pattern) | Suzuki [CO16] |
| CMP-23 | Motif as a game mechanic (collect and return) | Suzuki [CO16, S9] |
| CMP-24 | 3 plus 3 bar unit in a 4 bar frame | Shimomura [CO20] |
| CMP-25 | Major bed under a minor melody | Shimomura [CO22] |
| CMP-26 | Bass priority rule | Mitsuda [CO23] |
| CMP-27 | Same sus4 shape, opposite bass direction | Mitsuda [CO23] |
| CMP-28 | Substitute chords so minor stops sounding minor | Mitsuda [CO23] |
| CMP-29 | Hand played timing spread | Sakuraba [CO27] |
| CMP-30 | Limb written drum part with an improvised fill | Sakuraba [CO27] |
| CMP-31 | Genre declared then baroque semiquaver engine | Yamane [CO29, CO28] |
| CMP-32 | Bassline first, off grid reverb copy, semitone clash | Wise [CO17, CO18] |

---

## 19. Sources

All links read on 2026-10-21. S ids are the existing rows from `knowledge/MUSIC-HOOK-GRAMMAR.md` and
`knowledge/MUSIC-STYLE-BIBLE.md`, repeated here with their own link so this file can be read alone.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| CO1 | GlitterBerri, translation of a Japanese special interview with Koji Kondo (Ocarina of Time era) | https://glitterberri.com/ocarina-of-time/special-interview-koji-kondo | Three Famicom voices as right hand, left hand and organ pedal; chords studied in music class; the SMB songs that did not match Mario's running speed were discarded; "rhythm for Mario, scenery for Zelda" |
| CO2 | The New Yorker, "How Video Games Changed Popular Music" | https://www.newyorker.com/culture/cultural-comment/how-video-games-changed-popular-music | Kondo's aim of emphasising the experience the player is having; tempo experiments always returning to the main theme; Schartmann's book as the structural analysis |
| CO3 | Andrew Schartmann, Koji Kondo's Super Mario Bros. Soundtrack (Bloomsbury), publisher page and excerpts | https://bloomsburycollections.com/monograph?docid=b-9781501305139 | The theme as a one-measure segment and its transposition down by a step; parallel voice leading between the two chords; Kondo's favourites being the SMB and Zelda overworld themes |
| CO4 | Nintendojo interview with Andrew Schartmann | https://nintendojo.com/features/interviews/nintendojo-interview-andrew-schartmann | Kondo's own line that technological advance is a double edged sword and does not force innovation |
| CO5 | VGMO, Kinuyo Yamashita interview (Chris Greening) | https://vgmonline.net/kinuyoyamashitainterview | Castlevania as her first Konami work; composing at the piano and performing for the sound team leader before entering data; the rock approach coming naturally; aim of music matching the dynamism of movement and the gothic backgrounds; "your melody is always there" |
| CO6 | Time Extension, 2026-09, Castlevania 40th anniversary report on the Dongled interview | https://timeextension.com/news/2026/09/i-feel-very-fortunate-castlevanias-kinuyo-yamashita-celebrates-40-years-of-the-vampire-slaying-classic | Yamashita and Terashima were the two composers; Maezawa was not involved; the MSX data conversion |
| CO7 | Wikipedia, Kinuyo Yamashita | https://en.wikipedia.org/wiki/Kinuyo_Yamashita | Castlevania as her debut and the format it set; the series of Konami titles that followed |
| CO8 | Kotaku, "Mega Man Composer Manami Matsumae Doesn't Miss The 9-6 Grind" | https://kotaku.com/mega-man-composer-manami-matsumae-doesnt-miss-the-9-6-g-1846809139 | Three channels with one dedicated to the chord, arpeggio and inner voiced chords; the superior's instruction that melodies must be memorable; chord modulation as a signature |
| CO9 | Square Enix Music Online, "Interview with the Mega Man 1 and 2 Sound Team: Reunited 20 Years On" | https://www.squareenixmusic.com/features/interviews/manamimatsumae.shtml | Matsumae wrote all MM1 music, sound effects and data in three months; her first image of the game as robotic coolness with a sorrowful side |
| CO10 | VGMO, Manami Matsumae interview, "A Career After Mega Man" | http://vgmonline.net/manamimatsumaeinterview | "Only three notes at a time" and the problem of getting the feeling of chords with a melody under sound effects; melodies easy to remember as a permanent goal |
| CO11 | Enjoy Game Japan Museum, Koichi Sugiyama creator page | https://museum.enjoygamejapan.online/en/creators/koichi-sugiyama | Classical music as the only fitting foundation; the score delivered in a week; the five minute overture and the "fifty-four years" remark; Beethoven and Mozart as the test of music that does not wear out |
| CO12 | Enjoy Game Japan Museum, review of the Dragon Quest Overture | https://museum.enjoygamejapan.online/en/sounds/reviews/koichi-sugiyama-dragon-quest-overture | Overture structure as fanfare, lyrical middle, return; horn fifths in the opening; the three to five seconds rule; the Tokyo Strings Ensemble recording in 1986 |
| CO13 | sackchief, "The Music of Dragon Quest, Koichi Sugiyama Retrospective" (video analysis, transcript) | https://youtube.com/watch?v=6HXA-x3LazM | Two days of data entry and four days of writing for eight Dragon Quest I cues; list of the eight cues; Baroque texture fitting the Famicom because notes do not linger; horn fifths; Toriyama's art as a trigger |
| CO14 | IGN, "The Dragon Quest Symphony" (2004) | http://ign.com/articles/2004/01/28/the-dragon-quest-symphony | Scene by scene composition assembled into a concert piece; Sugiyama as the originator of the ballet idea |
| CO15 | Shmuplations, Keiichi Suzuki 1997 composer interview | https://shmuplations.com/ksuzuki | Itoi's request for pop music with real vocals and instrumental versions in game; RPG arpeggiation making game melodies sound classical; Mother 2 turning to ambient and world music; scene by scene requests |
| CO16 | Music of the Mother series (summary of the series' documented influences) | https://grokipedia.com/page/Music_of_the_Mother_series | Beatles-like melody against Beach Boys-like percussion; Godley and Creme as an influence on Eight Melodies; Eight Melodies collected in eight parts as a mechanic |
| CO17 | Super Mario Wiki, Aquatic Ambience | https://mariowiki.com/Aquatic_Ambience | Bassline first; eight waveforms played in sequence; vocal plus harp sample for the arpeggios; "sad and uplifting at the same time"; the failed relationship remark |
| CO18 | "How David Wise Composed Aquatic Ambience from Donkey Kong Country" (fan analysis, video) | https://youtube.com/watch?v=QzL5sjztoiI | 75 bpm in 4/4; about two minutes before the loop returns to section two; major seventh with a semitone clash; minor eleventh chord; off grid 30 second reverb; panning chase; pitch bending. Cited as a fan claim, not as a ROM study |
| CO19 | Korg, "Patch of the Week 139: Aquatic Ambience on wavestate", presented by David Wise | https://youtube.com/watch?v=SUPpodo9yMQ | 64 KB of sample memory for the music, less than half a second of CD audio; wave sequencing adapted from the Wavestation; the 800 ms crossfade on a loop |
| CO20 | EventHubs report on the Otaquest Shimomura interview | https://eventhubs.com/news/2019/dec/31/creator-guiles-theme-yoko-shimomura-explains-why-she-thinks-iconic-background-tune-became-so-popular | Guile's theme intro as six measures, built as two plus one twice; character psyche as the starting point |
| CO21 | scrmbl, "Blending worlds with music: interview with Yoko Shimomura" | https://scrmbl.com/post/blending-worlds-with-music-interview-with-composer-yoko-shimomura | Classical background and discomfort with rhythm-led writing; hiding rhythm in the gaps between tones; a unique sound effect requested per stage; homelands checked before composing |
| CO22 | The Guardian, Yoko Shimomura interview (2025-06-20) | https://theguardian.com/culture/2025/jun/20/yoko-shimomura-interview-composer-street-fighter-final-fantasy | Blanka as a major key rhythm track with a minor key melody on top; stage art as the source of a character's musical identity |
| CO23 | Chrono Compendium, transcript of the 2025-03-14 Chrono Trigger 30th music stream with Yasunori Mitsuda | https://chronocompendium.com/wiki/index.php/March_14,_2025_CT_30th_Music_Stream_with_Yasunori_Mitsuda | The Dsus4 to Esus4 over F sharp to Dsus4 over F progression and its bass motion; the closer in D flat; bass given the highest priority; substitute chords in Frog's Theme; psychoacoustic delay with four field sounds; over 200 sketched songs lost |
| CO24 | RPGFan, interview with Yasunori Mitsuda | http://classic.rpgfan.com/features/mitsuda-interview | Health during early projects; composing a map-led RPG from an early stage |
| CO25 | 1UP, "Radical Dreamer: Yasunori Mitsuda interview" (archived) | https://web.archive.org/web/20090227122203/www.1up.com/do/feature?cId=3162780 | The ultimatum to Sakaguchi that produced Chrono Trigger; the hospitalisation during that project |
| CO26 | Square Enix Music Online / VGMO, Motoi Sakuraba interview (2011) | https://squareenixmusic.com/features/interviews/motoisakuraba.shtml | Entirely self taught with "next to nothing" of music theory; progressive rock trio background; live performance as the foundation; handling five projects at once |
| CO27 | Shmuplations, Motoi Sakuraba 2002 composer interview | https://shmuplations.com/motoisakuraba | Deja-vu as a keyboard, bass and drums prog trio; FM mimicry of real instruments sounding indistinct or weird; plays every part by hand and does not make sequenced music; composing, mixing and finishing alone |
| CO28 | Game Developer (Gamasutra), classic interview with Michiru Yamane (archived) | https://web.archive.org/web/20171208062929/https:/www.gamasutra.com/view/news/207767/A_classic_interview_with_Castlevania_composer_Michiru_Yamane.php | University thesis on Bach; immersion in classical but dark music; not wanting the gothic style to become a stereotype; arrangements in the series |
| CO29 | 1UP conversation with Michiru Yamane (Castlevania: Symphony of the Night feature) | https://videogameforums.com/t/meet-the-people-behind-the-art-and-soundtrack-of-castlevania-sotn.17850 | Deciding the bigger picture before drafting (classical, metal, regional); analysing rock rhythmic styles and guitar phrases for Bloodlines; Dream Theater named; progressive rock for boss battles; Kojima's art as a trigger |
| CO30 | Wikiwand, Michiru Yamane | https://wikiwand.com/en/Michiru_Yamane | Style drawing on baroque, classical and rock, with Bach and Yellow Magic Orchestra as prominent influences |
| CO31 | Primordial Paradox corpus statistics, `D:\Musikage-Corpus\style-pp\stats\nobuo_uematsu.json`, generated 2026-10-21 from 104 NES-MDB pieces (FF I to III) | local file | Mode split, chord quality counts, changes per bar, interval and interval n-gram shares, step and leap ratios, median range, notes per bar, sixteenth share, voice and pitch medians |
| CO32 | Corpus statistics, `hirokazu_tanaka.json`, 40 pieces of Mother / EarthBound Beginnings | local file | Repeated note share 16.2 percent, top bigrams, sus4 as second most common quality, dim7 counts, step share 61.8 percent, median range 22.5 semitones, 4.66 notes per bar |
| CO33 | Corpus statistics, `nintendo.json`, 132 pieces across nine Nintendo NES games | local file | Major 94 against minor 38, C as the most common tonic (38), mean key correlation 0.7681; the file's own caveat that SMB2 and SMB3 are absent and that tempo is normalised |
| CO34 | Corpus statistics, `nes_rock_metal.json`, 86 pieces (Castlevania 16, Mega Man 16, Ninja Gaiden 29, Contra 13, Kid Icarus 12) | local file | Minor 57 against major 29, repeated note 16.5 percent, sixteenth share 76.0 percent, wide leaps above 19 semitones 8.3 percent, phrase length median 10 bars, cadence shares |
| S7 | The Line of Best Fit, Nobuo Uematsu feature, as recorded in the style bible | https://www.thelineofbestfit.com/features/articles/nobuo-uematsu-music-final-fantasy | The shifted second voice shimmer trick |
| S8 | Red Bull Music Academy Daily, "Interview: Final Fantasy's Nobuo Uematsu", 2014 | https://daily.redbullmusicacademy.com/2014/10/nobuo-uematsu-interview | His beginnings, Kochi as a source of imagery, Elton John's Honky Chateau as the record that decided his career |
| S9 | Wikipedia, Music of the Mother series, as recorded in the style bible | https://en.wikipedia.org/wiki/Music_of_the_Mother_series | The three note simultaneous limit and the hummable one finger song |
| S10 | Shinesparkers, Hirokazu Tanaka interview, as recorded in the style bible | https://shinesparkers.net/interviews/hirokazu-tanaka/ | Metroid, no distinction between music and sound effects |
| S11 | Mother 3 fobby.net interview, as recorded in the style bible | https://mother3.fobby.net/interview/m3int_02.html | The request for a song anyone could hum and play with one finger |
| S45 | BBC News reporting the Hooked on Music study, as recorded in the hook grammar | https://www.bbc.com/news/science-environment-29847739 | About 5 s average recognition, 2.29 to 2.62 s fastest |
| S47 | Dowling and Bartlett, 1981, as recorded in the hook grammar | https://doi.org/10.1037/h0094275 | Contour carries memory inside 5 s, intervals later |
| S49 | Temperley, melodic pattern repetition corpus study, as recorded in the hook grammar | https://doi.org/10.18061/emr.v18i2.9289 | Varied repetition preferred to literal, R-I-I at 2.7 to 1 |
| S51 | Hooktheory theorytab, Mega Man 2 Dr Wily Stage 1, as recorded in the hook grammar | https://www.hooktheory.com/theorytab/view/takashi-tateishi/mega-man-2---dr-wily-stage-1 | 180 bpm, 29 semitone range, 95 percent diatonic, 68 percent chord tones |
| S52 | Hooktheory theorytab, Super Mario Bros 3 Overworld, as recorded in the hook grammar | https://www.hooktheory.com/theorytab/view/koji-kondo/super-mario-bros-3---overworld | 15 semitone range, 0.89 beats per note, 91 percent diatonic, 81 percent chord tones, chord complexity 32 |
| S53 | Hooktheory theorytab, Final Fantasy battle, as recorded in the hook grammar | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---battle | G minor, 150 bpm, 8 semitone range, 0.88 beats per note, 80 percent diatonic, chord complexity 94 |
| S54 | Hooktheory theorytab, Final Fantasy Prelude, as recorded in the hook grammar | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---prelude | One arpeggio pattern, melodic complexity 93 to 94 |
| S55 | Hooktheory theorytab, Kid Icarus Underworld, as recorded in the hook grammar | https://www.hooktheory.com/theorytab/view/hirokazu-tanaka/underworld---kid-icarus | 152 bpm, 6/8, 22 semitone range, chord progression novelty 88 |
| S56 | Hooktheory theorytab mirror, Castlevania Vampire Killer, as recorded in the hook grammar | http://devhookpad.hooktheory.com/theorytab/view/kinuyo-yamashita/castlevania---vampire-killer | 41 semitone range, 0.62 beats per note over 64 beats, 82 percent diatonic, 76 percent chord tones, punchy syncopation |
| S58 | Wikipedia, Super Mario Bros. theme, as recorded in the hook grammar | https://en.wikipedia.org/wiki/Super_Mario_Bros._theme | C major, about 100 bpm, cut time, swing, prominent syncopation, periodic structure, tempo raised to match movement |
| S59 | Cartridge Lit, "High Scores: Dr. Wily Stage 1", 2020, as recorded in the hook grammar | http://cartridgelit.com/2020/10/29/high-scores-dr-wily-stage-1 | The 150 to 180 bpm reading, two sections with a bridge that releases tension |
| S61 | Eurogamer, "Castlevania's Vampire Killer beats", as recorded in the hook grammar | https://www.eurogamer.net/castlevanias-vampire-killer-beats | 16 bar loop in D minor with heavy flat seven, two square voices taking turns and crossing registers |
| S62 | Music Production Wiki, "How to recreate the chiptune sound", as recorded in the hook grammar | https://musicproductionwiki.com/articles/how-to-recreate-the-chiptune-sound | Duty settings, 60 Hz frame engine, 1 frame per step arpeggio, delayed vibrato, pseudo echo |
| S63 | NESdev Wiki, APU basics, as recorded in the hook grammar | https://www.nesdev.org/wiki/APU_basics | Volume, duty and period registers, phase reset, envelope behaviour |
| S64 | WiKirby, Green Greens, as recorded in the hook grammar | https://wikirby.com/wiki/Green_Greens_(theme) | Antecedent and consequent with a deceptive cadence on the repeat, major to parallel minor second section |

Source quality notes. CO18 and CO13 are video analyses (a fan arrangement breakdown and a retrospective
respectively); they are used for countable claims and marked as fan claims where they go beyond what
interview material supports. CO16 is a summary page, used only for the influence list that the Suzuki
interview and series histories support. CO31 to CO34 are corpus statistics from MIDI transcriptions,
which describe the archive, not the ROM, and which normalise tempo, so no tempo claim rests on them.
CO3 and CO2 are a published academic book and its review coverage; the transposition and parallel
voice-leading claims are Schartmann's analysis, not Kondo's statement.

---

## 20. Limits of this document

1. No melody or bass line is transcribed here, and none of the numbers are pitch strings. The bar
   numbers in section 17 point at sections a listener can find, not at notes.
2. Six of the twelve composers wrote their defining work off the 2A03. For Sakuraba, Shimomura,
   Mitsuda, Yamane, Wise and the later Suzuki, the technique is documented but the chip mapping is my
   inference, and it is marked as such wherever it appears.
3. Our corpus covers four of the twelve (Kondo, Tanaka, Uematsu, and Yamashita plus Matsumae inside the
   rock family). Everything measured about the other eight is published analysis, interview statement
   or fan claim, and each is labelled with which.
4. The ratings in section 15 are a working opinion with evidence attached, meant to be argued with. They
   are not a ranking of the composers as artists.
5. The tempo bands in section 16.4 are the published tempos of specific cues, not the range of each
   composer's whole catalogue; four of our corpus files normalise tempo to 120 bpm and cannot be used
   for this at all.
