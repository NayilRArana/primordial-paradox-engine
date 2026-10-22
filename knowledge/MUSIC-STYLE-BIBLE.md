# MUSIC-STYLE-BIBLE

Composition techniques of Toby Fox, Keiichi Suzuki and Hirokazu Tanaka (Mother / EarthBound Beginnings) and
Nobuo Uematsu (Final Fantasy I to III on NES), converted into executable arranger recipes for
Primordial Paradox.

Written by research-assistant on 2026-10-21 for card t_890befb5 (MUS-STYLE-BIBLE).

## 0. Scope, rules and how to read this file

- Reference rule (PLAN-V2 section 0): published games were studied by reading interviews, published analyses and
  the NESdev hardware documentation. Nothing was downloaded, ripped, traced, transcribed, sampled or decompiled.
  No melody of any of these composers is written out anywhere in this file or in `data\music_recipes.json`. Every
  recipe is a rule about how to build something, not a quotation of a tune.
- The recipes are for the 2A03 plus the Konami VRC6 expansion (the chip *Akumajou Densetsu* used): two pulse
  channels, one triangle, one noise, one DPCM sample channel, plus two VRC6 pulses and one VRC6 sawtooth
  (`assets\audio\title_theme_v2\score.yaml`).
- A recipe is machine readable. The table in section 5 is the source of truth; `data\music_recipes.json` is
  generated from it by `tools\check_music_style_bible.py`, which also runs the acceptance checks (recipe count,
  a source on every recipe, JSON validity, no long dashes, table and JSON in sync).
- Read "verified" as: the claim is stated in the linked source, which was read on the date given in section 4.
  Read "inferred" as: the source supports the general habit and the specific rule is our operationalisation of it.

### Parameter conventions used by the recipes

| Token | Meaning on the NES 2A03 / VRC6 |
| --- | --- |
| `pulse1`, `pulse2` | the two native square channels ($4000 to $4007) |
| `triangle` | the native triangle channel ($4008 to $400B), fixed volume, used for bass |
| `noise` | the native noise channel ($400C to $400F), 15 bit LFSR, 16 selectable rates |
| `dpcm` | the delta modulation channel ($4010 to $4013), 1 bit sample playback |
| `vrc6_p1`, `vrc6_p2` | the two Konami VRC6 pulse channels, 8 duty steps plus a 100 percent mode |
| `vrc6_saw` | the VRC6 sawtooth channel, 5 bit output, 12 bit period |
| `duty` | pulse width: 12.5, 25, 50, 75 percent on the 2A03; 6.25 to 50 percent in 16th steps on the VRC6 |
| `delay_eighths` | how many eighth notes the delayed voice waits before sounding |
| `vol_pct` | volume of a secondary voice relative to the lead, 0 to 100 |

## 1. The chip, because every style below is a consequence of it

Verified from the NESdev wiki.

- The APU has five channels: two pulse waves, one triangle, one noise and one DMC sample channel. Pulse, triangle
  and noise only sound while their length counters are non-zero (S1).
- Pulse duty options are 12.5, 25, 50 and 75 percent. A pulse channel with a timer value below 8 is silenced
  (S1). The pulse frequency is `f = fCPU / (16 * (t + 1))` with fCPU 1.789773 MHz on NTSC (S1).
- The pulse envelope is a stepped decay from volume 15 to 0, or a constant volume, and can loop forever (S1).
- The sweep unit can raise or lower a pulse pitch over time; the negate flag lets it fall instead of rise (S1).
- The noise channel is a 15 bit linear feedback shift register with 16 selectable clock rates and a periodic mode
  that shortens the sequence to 93 or 31 steps, which is what turns hiss into a tonal buzz (S3).
- The DMC channel plays 1 bit delta encoded samples from CPU memory at 15 fixed rates; the rate index also names
  the approximate pitch of the sample (S4).
- The VRC6 adds two pulses with 8 duty steps and a 100 percent mode, plus one sawtooth whose accumulator rate
  controls its volume. A saw accumulator rate above 42 distorts (S6).
- Pitch lookup: the published period table gives the byte values for every note, and the triangle table starts at
  the low A while the pulses sound one octave higher (S2).

Consequence for style: on this chip a chord is not a chord. It is one note at a time, moved fast enough that the
ear joins them. Every recipe below that says "arpeggio" means exactly that: a sequence of pitches the ear
fuses into a harmony that no single channel can sound.

## 2. Nobuo Uematsu, Final Fantasy I to III (NES)

### 2.1 Harmony habits

Verified: the series scores share a small set of recurring pieces, the Prelude, the Opening, the Fanfare and the
Chocobo theme, and each mainline score otherwise stands on its own (S7). Final Fantasy I already contains the
first versions of the long-lived themes (S7).

Verified: FF I opens with a Bach-like arpeggio figure played on two pulse channels, one of them deliberately
about an eighth note late so that the pair reads as a harp with a delay (S7).

Verified: FF II reads as Baroque in shape, building to a fanfare, with a wider range of instruments and audio
tricks than FF I (S7).

Verified: FF III is the entry where character themes arrive. The first is the piece for the Maiden of the Temple
of Water, which the same source describes as simple arpeggios plus a delicate melody line (S7).

Inferred for the recipes: the harmonic vocabulary is functional, with a strong pull to a tonic chord after any
tension, and colour comes from the mode of the accompaniment rather than from chromatic harmony. Borrowed chords
are rare in these three scores; the borrowed colour in our score comes from the manager's own writing, and the
Uematsu recipes below are deliberately diatonic so that they read as period-correct rather than as a copy.

### 2.2 Melody habits

Verified from Uematsu's own account: he had no formal training, and his heroes were the 1970s progressive rock
and pop records of his teens (Led Zeppelin, Deep Purple, Yes, King Crimson, Pink Floyd, Elton John) alongside
Bach, Chopin, Debussy, Ravel, Tchaikovsky and Stravinsky (S7, S8).

Verified: his key strength is memorable character themes that return and are remixed as leitmotifs at narrative
moments (S7).

Verified: the ability to write very catchy melodies is often credited to the hardware limits he worked under
(S7).

Verified in his own words: "I think that the more limited people are, the more ingenious they begin to get", and
he describes the NES as making only sounds like "peee", "booo", "paaa", so that expressing emotion was a matter
of how a sound faded in and out (S8).

### 2.3 Texture and orchestration on the chip

Verified: the NES gave five channels, two pulse for melody, triangle for simple bass and percussion, noise for
metallic effects and percussion, and a digital sample channel, and sound programmers used arpeggios to simulate
background chords (S7).

Verified, in his own words, the trick that defines the FF I Prelude and much of the FF II and FF III texture:
play the melody on one pulse at the right frequency and play the same melody on the second pulse with the
frequency shifted slightly and the timing shifted slightly, which creates a shimmer that makes plain electronic
sounds feel emotional (S8). The Line of Best Fit description of the Prelude as two pulses with the second about
an eighth note late is the same device (S7).

Verified: he worked on an MSX, typing note data directly, and used goto loops to avoid repetition, up to Final
Fantasy III (S8).

Verified: the Prelude was written in half an hour because a new opening scene needed music, and he did not expect
it to be reused for 30 years (S8).

Verified: he prefers to write love themes or a magnificent main theme, and is not keen on battle music (S8).

### 2.4 Form, tempo and meter

Verified: the Prelude is about 52 seconds (S7). Verified: the FF II main piece is a Baroque shape that builds to
a triumphant fanfare (S7).

Inferred: the period habit is a short, single-theme piece with an internal crescendo, one character theme per
person or place, and a fanfare reserved for the end of a quest. Our recipes follow that: one theme per scene,
variation by instrumentation rather than by new notes.

### 2.5 What makes the theme memorable

Inferred from the verified material above: the melody is written inside a narrow range so the ear can hold it,
the harmony arrives as a broken chord the ear completes, and a second voice repeats the melody slightly late or
slightly detuned so the single line gains depth for free.

## 3. Keiichi Suzuki and Hirokazu Tanaka, Mother / EarthBound Beginnings

### 3.1 Harmony habits

Verified: the Mother series music carries a broad, "disorderly" spread of styles, which Itoi credits to Tanaka
and Suzuki, and the same interview reports that the amount of music fitted into eight megabits would fill two
compact discs as an album (S9).

Verified: the SNES gave the composers far more freedom than the NES, which made EarthBound's music easier than
Mother's, and part of that difficulty was fitting all the music onto the cartridge (S9).

Verified: Suzuki cites John Lennon as an influence on all the composers while EarthBound was being developed,
because the love songs matched the feeling of the game, and critics and players have noted similarities to
popular songs and suspected homages to Lennon and the Beatles (S9).

Verified: Itoi says EarthBound was the first video game to include vibrato, or string bending, in its music, and
that it had more "jazzy" pieces than Mother (S9).

Verified: the Mother 1 score is credited to Suzuki and Tanaka, and Mother 1 reused the same two plus Hiroshi
Kanazu for EarthBound (S9).

Verified: several melodies recur across all three games, including Pollyanna, Snowman and Humoresque of a
Little Dog (S9).

### 3.2 Melody habits

Verified: the NES was able to play three notes at a time, which Suzuki has said greatly limited what he was able
to produce, since he could not make some of the sounds he wanted (S9).

Verified: Suzuki estimated he composed over 100 pieces for EarthBound, including pieces that never made it into
the game, and that his favourite was the music played when the player rode a bicycle, which he had composed
before starting work on the game (S9).

Verified: Itoi asked for a song that anyone could hum along with, and imagined a child who cannot really play the
piano playing it with a single finger, which is the brief behind the Eight Melodies piece (S11).

Verified: the Mother 1 album contained seven English vocal arrangements of game tracks written by Suzuki with
David Bedford and Michael Nyman, and the Eight Melodies piece ended up in Japanese school textbooks (S9, S11).

### 3.3 Texture and orchestration on the chip

Verified: Tanaka came from Nintendo's sound team, where Famicom and Game Boy sound source development was the
hardest part of the job, and his stated goal on Metroid was a soundtrack that left no distinction between music
and sound effects, as if the player lived inside a living entity (S10).

Verified: on EarthBound the SNES could play eight notes at once, which combined with better sound quality let
Suzuki compose in a way closer to how he composes in real life (S9).

Inferred for the recipes: the Mother texture is bass plus a single melodic instrument plus a percussive layer
that blends music and effects, with style changing from place to place. That is why the recipes below give each
scene one dominant timbre rather than a full ensemble.

### 3.4 Form, tempo and meter

Verified: EarthBound has one named theme per location, and the album groups several in-game pieces into longer
arrangements under one title, for example the shop and hotel pieces merged into one track (S9).

Verified: the EarthBound soundtrack album has 24 tracks, many of them merged arrangements (S9).

Verified: the Mother 1 score pairs short place pieces with a set of eight short character pieces, and the
"World of Mother" album track plays the game pieces back to back in their order of appearance in the game (S9).

Inferred: the form habit is a set of short cues, one per location and one per character, that can be strung
together. Our recipes give each scene one cue with a stated cue length.

### 3.5 What makes the theme memorable

Inferred from the verified material: a theme that a child can hum with one finger, played by one instrument at a
time, in a style that matches the place. The memorability comes from the pairing of a plain, singable line with a
place-specific rhythm and timbre, and from the same line turning up again elsewhere in a different mood.

## 4. Toby Fox, Undertale and Deltarune

### 4.1 Harmony and colour

Verified: Fox describes himself as musically "inspired by everything I listen to", and says he learned music theory
by trying to write video game music, focusing on which emotions certain chord progressions invoke (S12).

Verified: his primary influences are the Touhou Project and Shigesato Itoi's Mother series (S12). In the same
interview series he says he loves retro game music and still listens to the soundtrack of Secret of Mana
(S14).

Verified: he credits the soundtrack's power to the frequent use of melodies and themes, and to each song finding a
way to grow outside the realm of chiptunes without losing its simplicity (S13, quoting Fox).

### 4.2 Melody and leitmotif

Verified: the melody of the solo guitar in the "Home" scene is the same melody as the opening piece, which the
analysis names as a leitmotif (S13).

Verified: the sparse snow field theme becomes a more upbeat piece in Snowdin Town while keeping the melody of the
field theme, and a third variant appears in the shop (S13).

Verified: the same piece is heard as a music box when the lamp is turned off, which the analysis names as adaptive
music that changes the tone of the tune to reflect what is on screen (S13).

Verified: Papyrus's battle theme is described as having a classical polka one two rhythm with a driving drum beat
(S13).

Verified: Fox often began writing the music before creating the scene it belongs to (S13), and the same point
appears in the Wikipedia account of his method, where some of the Undertale music was composed before he started
work on the game, with story beats and main character themes written to fit a given situation or emotion (S12).

### 4.3 Texture and orchestration

Verified: the soundtrack follows NES era restrictions with some liberties, and the visual, menu and battle
presentation follows the same NES aesthetic (S13).

Verified: the "Home" scene is a single acoustic guitar, and the snow field theme is a piano plus a small group of
strings (S13).

Verified: Fox stated that the majority of the Undertale soundtrack was composed using reiterations of free
soundfonts and synths, so a small set of instruments carries the whole score (S15). The NES era restriction
point and the two instrument snow field are in S13.

Inferred for the recipes: instrument count is a narrative choice, not a budget accident. The snow field uses two
timbres, the town adds a third, and the melody does not change. Our recipes therefore separate "which instrument
plays" from "which notes are played", so a scene can be revoiced without rewriting its melody.

### 4.4 Form, tempo and meter

Verified: Papyrus's theme is in a polka one two feel (S13).

Verified: the Undertale music was written with simple, discernible melodies in the spirit of the era where
melodies had to be simple (S13, quoting Fox).

Inferred: scene length cues, one theme per location, and a character theme per character, with the theme returning
in a different instrumentation when the story turns.

### 4.5 What makes the theme memorable

Inferred from the verified material: one melody that recurs across the score in several guises, so that the
listener recognises a place or a person from three notes, plus a rule that the arrangement changes before the
melody does.

## 5. Recipe table

Thirty recipes in this table, and forty six more in section 14 for the Baroque, Classical, rock and metal families.
Each row is one executable rule. `params` are written as `key=value` pairs separated by semicolons;
values that contain no spaces are used verbatim by the arranger. `use` lists the cue types where the recipe applies:
title, town, battle, boss, sad, field, character, secret. Sources are the identifiers in section 6.

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| UEM-01 | Prelude harp arpeggio | Uematsu FF I | Play the chord as an up then down broken chord over two octaves in sixteenths on pulse1, and repeat the same figure on pulse2 one eighth later at lower volume, so the pair reads as a harp with a delay | subdivision=16ths; octaves=2; order=up_then_down; notes=chord_tones_only; delay_eighths=1; vol_pct=40; channel=pulse1+pulse2 | title, town, sad | S7, S8 |
| UEM-02 | Detuned shimmer pair | Uematsu | Play one melody on two pulses at the same rhythm, the second pulse shifted a few cents flat and a fraction later, which is the trick that makes plain square tones feel emotional | cents_offset=-8; delay_ms=18; vol_pct=70; envelope=soft_decay | town, sad, character | S8 |
| UEM-03 | Maiden arpeggio and melody | Uematsu FF III | Under a delicate single line melody, let a simple arpeggio of the chord run in eighths on pulse1 with the melody on vrc6_p1, keeping the arpeggio below the melody in register | arp=eighths; arp_register=below_melody; melody_duty=0.25; arp_duty=0.125; chord_tones=3 | sad, character | S7 |
| UEM-04 | Driving sixteenth battle riff | Uematsu | Play a repeating sixteenth riff on pulse1 at a fixed two bar cell, put the root on the triangle on every beat, and put a noise hit on beats 2 and 4 | riff_cell_bars=2; subdivision=16ths; bass=root_on_beats; noise_hits=beats_2_and_4; tempo_floor=140 | battle | S7 |
| UEM-05 | Baroque fanfare cadence | Uematsu FF II | End a cue with a rising arpeggio figure on pulse1, a sawtooth chord stab on vrc6_saw, then a single held tonic, in a shape that arrives at the last bar | figure=rising_arp; stab_channel=vrc6_saw; final=held_tonic; bars=2 | boss, title, town | S7 |
| UEM-06 | Ostinato under arpeggio | Uematsu | Hold a repeated root and fifth ostinato on the triangle under the UEM-01 arpeggio, so the harmony is stated twice by two different voices | pattern=root_fifth; repetition=per_bar; triangle=fixed_volume; pulse2=delayed_arp | title, field | S7, S8 |
| MOT-01 | Three note melody discipline | Mother | Write the lead melody for one pulse channel only and put no more than three distinct pitches in any two bar span, because the NES cannot play three notes at once and Mother was written inside that limit | max_pitches_per_2bars=3; melody_channel=pulse1; harmony_channel=pulse2 | any | S9 |
| MOT-02 | Jazz town shuffle | EarthBound | Write a town cue with a swung eighth feel over a walking triangle bass, and give the melody a blue third, because EarthBound deliberately carried more jazzy pieces than Mother | feel=shuffle_2_3; bass=walking_root_third_approach; melody_colour=blue_third; cue=town | town | S9 |
| MOT-03 | Slow vibrato on held notes | EarthBound | Bend the pitch of any melody note held longer than a quarter note by a few cents and back, the string bending that EarthBound is credited with bringing to a video game | bend_cents=18; bend_rate_hz=5; applies_to=notes_longer_than_quarter; channel=vrc6_p1 | sad, town | S9 |
| MOT-04 | Bicycle lilt | EarthBound | Write a travel cue in a compound feel with a skipping melody in thirds, a light triangle accompaniment on beats 1 and 3, and no drum layer at all | meter=6/8; melody=thirds; triangle=beats_1_and_3; drums=none; tempo=medium | field, town | S9 |
| MOT-05 | Style switch per place | Mother | Give each location its own style and its own rhythmic signature, and let the piece change style between locations rather than varying one global theme | style_per_location=yes; new_rhythm_signature_per_location=yes; shared_melody=no | town, field, secret | S9, S11 |
| MOT-06 | Music and effects as one | Tanaka | Use the noise channel as part of the arrangement, not only as a separate effect layer, so that the track and the sound effects share one surface | noise_in_arrangement=yes; noise_role=texture_and_rhythm; separate_sfx_layer=no | secret, battle, field | S10 |
| MOT-07 | One finger singable theme | Mother | Write the theme as a single line, stepwise, with no leap larger than a fourth and no more than one chromatic note in the whole phrase, so that a beginner can play it with one finger and hum it | max_leap=perfect_fourth; stepwise=yes; chromatic_notes_max=1; range=one_octave | title, sad, character | S11 |
| MOT-08 | Layered hidden motif | Mother | Keep one secondary motif in reserve and reveal it only in the secret or late scene, so the earlier scenes feel like they were hiding something | motif=secondary_cell; reveal_scene=secret; earlier_scenes=omit; cell_length=3_notes | secret, boss | S9, S11 |
| FOX-01 | Recast the leitmotif | Fox | Reuse the same melodic cell in a new scene and change only the instrumentation and the register, never the notes, so the listener recognises the place from the melody | melody=fixed; change=instrumentation_and_register_only; reuse=across_cues | any | S13 |
| FOX-02 | Adaptive instrument on a state flag | Fox | Bind the instrument of the current cue to a game state flag, so the same cue plays as a different instrument when the state changes, as the music box variant does | trigger=state_flag; mapping=instrument_to_flag; melody=unchanged; swap=soundfont | town, secret | S13 |
| FOX-03 | Music first, scene second | Fox | Write the cue before the scene it belongs to, then name the scene in the cue metadata, so the music sets the emotion the scene then has to carry | order=music_then_scene; cue_metadata=scene_name; reuse_of_earlier_cue=allowed | title, sad, character | S12, S13 |
| FOX-04 | Simple line that grows | Fox | Keep the melody inside a narrow range with one deliberate deviation, then let the arrangement grow around it without changing the melody | range=one_octave; deviations=1; arrangement_growth=add_voices; melody=unchanged | title, town, field | S13 |
| FOX-05 | Character theme with a signature rhythm | Fox | Give each character theme one rhythmic signature, a fixed two or three note figure that carries the personality, and keep the drum pattern behind it constant and driving | signature=one_rhythmic_figure; drums=driving_constant; figure_bars=1 | character, battle | S13 |
| FOX-06 | Field then town, same melody | Fox | Write a sparse field cue with a small instrumental palette, then write the town cue as the same melody with more voices and a brighter rhythm | melody=identical; field_voices=2; town_voices=4; brightness=rhythm_and_drums | field, town | S13 |
| FOX-07 | Small synth set for the whole score | Fox | Restrict the whole score to one small set of soundfonts and synths and reuse them everywhere, as the 2015 2D RPG score does with its soundfonts | soundfont_count=6; reuse=everywhere; variation=register_and_envelope_only | any | S13, S15 |
| CHIP-01 | Duty layering for melody and accompaniment | APU | Give the lead a 12.5 or 25 percent duty pulse and the accompaniment a 50 percent duty pulse, so the two voices stay separable under the mixer | lead_duty=0.125; accomp_duty=0.50; separation=by_duty | any | S1 |
| CHIP-02 | Triangle bass with envelope bass | APU | Put the bass line on the triangle and vary its loudness with the sweep unit falling in pitch on each note, which is the classic NES bass envelope | channel=triangle; pitch=falling_sweep_per_note; base=root; volume=triangle_fixed | any | S1 |
| CHIP-03 | Noise kit from the LFSR rates | APU | Build the percussion kit from the noise channel only: a short high rate burst for the hat, a mid rate burst for the snare, and a periodic mode burst for a metallic hit | hat=short_high_rate; snare=mid_rate_burst; metal=periodic_mode; rates=from_published_table | battle, boss | S3 |
| CHIP-04 | DPCM kick | DMC | Use the sample channel for a kick drum, because a one bit sample gives a pitched thump that the noise channel cannot, and keep the sample short | sample_length=short; pitch_from=rate_index; use=kick_only; loop=no | battle, boss | S4 |
| CHIP-05 | Sawtooth pad and oom pah | VRC6 | Use the VRC6 sawtooth as a sustained pad on long values and as an oom pah two hit stab on beats 2 and 3 of a waltz, with a rate that stays under the distortion threshold | channel=vrc6_saw; accum_rate_max=42; mode=pad_or_oom_pah; waltz_stabs=beats_2_and_3 | title, town, boss | S6 |
| CHIP-06 | VRC6 pulse doubling and echo | VRC6 | Double the lead with the second VRC6 pulse a step below, or use the VRC6 pulse in 100 percent mode as a flat organ voice for a held chord | doubling=parallel_at_third_below; mode_100=organ_held_chord; duty_range=0.0625_to_0.5 | any | S5, S6 |
| CHIP-07 | Falling sweep line | APU | Express a falling melody line by enabling the sweep unit with the negate flag so the pitch glides down under each note | sweep=negate_falling; note_length=quarter; register=upper | sad, boss | S1 |
| CHIP-08 | Delayed echo voice | APU | Send a copy of the lead to the second pulse one eighth later at reduced volume, the way the FF I Prelude does, and vary the delay across sections | delay_eighths=1; vol_pct=40; varies_per_section=yes | title, town, sad | S1, S7, S16 |
| GRM-01 | Instantiate a mood grammar | this bible | Pick the grammar for the mood of the scene from section 7, draw the progression for the key of the cue, and drop the section that does not fit the scene's function | key=scene_key; progression=from_section_7; drop_rule=scene_function | any | S16 |

### 5.1 How the recipes combine into a cue

A cue is built as: one melody recipe (FOX-04, MOT-07, UEM-03 or the manager's own leitmotif cell) plus one
accompaniment recipe (UEM-01, CHIP-05, MOT-02 or MOT-04) plus one bass recipe (CHIP-02 or UEM-06) plus one
percussion recipe (CHIP-03, CHIP-04 or FOX-05) plus, when the scene must feel familiar, one recall rule (FOX-01,
FOX-02, MOT-08). Every cue in the score should be reproducible from a row id and a parameter set with no further
prose.

## 6. Sources

All read on 2026-10-21.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| S1 | NESdev Wiki, APU | https://www.nesdev.org/wiki/APU | Five channels, duty values, envelope, sweep, mixer, the length counter condition |
| S2 | NESdev Wiki, APU period table | https://www.nesdev.org/wiki/APU_period_table | Note to period byte lookup, triangle one octave below the pulses |
| S3 | NESdev Wiki, APU Noise | https://www.nesdev.org/wiki/APU_Noise | 15 bit LFSR, 16 rates, periodic mode, noise as percussion source |
| S4 | NESdev Wiki, APU DMC | https://www.nesdev.org/wiki/APU_DMC | One bit sample playback, rate index and pitch table, sample length |
| S5 | NESdev Wiki, VRC6 | https://www.nesdev.org/wiki/VRC6 | The Konami chip used by Akumajou Densetsu, mapper 24 and 26 |
| S6 | NESdev Wiki, VRC6 audio | https://www.nesdev.org/wiki/VRC6_audio | Two VRC6 pulses with 8 duty steps and a 100 percent mode, one sawtooth, accumulator rate limit |
| S7 | The Line of Best Fit, "The lasting impact of Nobuo Uematsu and the music of Final Fantasy" | https://www.thelineofbestfit.com/features/articles/nobuo-uematsu-music-final-fantasy | FF I Prelude as a two pulse Bach-like arpeggio with a delayed second pulse, FF II Baroque shape, FF III first character themes, five channel limits and the arpeggio trick, Uematsu influences |
| S8 | Red Bull Music Academy Daily, "Interview: Final Fantasy's Nobuo Uematsu" | https://daily.redbullmusicacademy.com/2014/10/nobuo-uematsu-interview/ | Uematsu on the Prelude in 30 minutes, typing note data by hand on an MSX, the shimmer trick of a shifted second voice, "the more limited people are, the more ingenious they begin to get", his dislike of battle music |
| S9 | Wikipedia, "Music of the Mother series" | https://en.wikipedia.org/wiki/Music_of_the_Mother_series | Suzuki on the three note limit of the NES, the Famitsu interview on Lennon and on EarthBound's eight note SNES freedom, Itoi on the eight megabit soundtrack and on vibrato and jazzy pieces, Suzuki's 100 plus pieces and the bicycle theme, the Mother Music Revisited track list, EarthBound album track list |
| S10 | Shinesparkers, "Interview: Hirokazu Tanaka" | https://shinesparkers.net/interviews/hirokazu-tanaka/ | Tanaka on Nintendo sound source development and on the Metroid goal of no distinction between music and effects |
| S11 | Nindori.com Itoi interview (Mother 3 fan translation) | https://mother3.fobby.net/interview/m3int_02.html | Itoi asking for a song anyone could hum along with, playable with one finger; the request that became Eight Melodies |
| S12 | Wikipedia, "Toby Fox" | https://en.wikipedia.org/wiki/Toby_Fox | Influences (Touhou, Mother), learning music theory through chord progressions, composing some music before the game work started |
| S13 | Game Audio Lookout (Alexander Pensler), "Coherent Situational Music in Undertale", Feb 2 2019 | https://medium.com/game-audio-lookout/coherent-situational-music-in-undertale-e9d682c366ff | The Home and Once Upon a Time shared melody, the music box adaptive variant, the field to town melody reuse, Papyrus's polka one two rhythm and driving drum beat, the NES era restriction point, Fox quoted on themes and simplicity |
| S14 | AUTOMATON, "An Interview with Toby Fox, Developer of the 2D RPG Undertale: A Cocktail of Touhou, Mother, and Shin Megami Tensei" (Japanese, 2015) | https://automaton-media.com/articles/interviewsjp/undertale-developer-toby-fox-interview/ | Fox naming Mother and Touhou as strong inspirations, his love of retro game music, and that he still listens to the Seiken Densetsu 2 (Secret of Mana) soundtrack |
| S15 | Undertale Wiki (Fandom), "Leitmotifs" | https://undertale.fandom.com/wiki/Leitmotifs | The statement that Fox said the majority of the soundtrack was composed using reiterations of free soundfonts and synths, and the leitmotif index per character and place |
| S16 | Primordial Paradox, `assets\audio\title_theme_v2\score.yaml` (internal, read 2026-10-21) | <repo>\assets\audio\title_theme_v2\score.yaml | The target chip list, the seven voices, the A minor waltz at 104 bpm and the existing voice roles that these recipes must fit |

| S17 | Wikipedia, "Counterpoint" | https://en.wikipedia.org/wiki/Counterpoint | Two or more simultaneous lines that are harmonically dependent but rhythmically independent; imitative counterpoint repeats a main idea across voices; parallel voices are prohibited because they destroy voice independence |
| S18 | Wikipedia, "Fugue" | https://en.wikipedia.org/wiki/Fugue | Subject stated in imitation at different pitches, exposition complete when every voice has entered, episodes between entries, entries in related keys, final entry in the tonic; Bach as the model |
| S19 | Wikipedia, "Ornament (music)" | https://en.wikipedia.org/wiki/Ornament_(music) | Trill as rapid alternation between a note and the one above it, mordent as a single quick alternation, ornaments improvised in the Baroque and expected from a keyboard player |
| S20 | Wikipedia, "Circle of fifths" | https://en.wikipedia.org/wiki/Circle_of_fifths | The twelve pitch classes in ascending fifths; chord progressions often move between roots a fifth apart, and modulation goes to a key one signature away |
| S21 | Wikipedia, "Ostinato" (ground bass redirects here) | https://en.wikipedia.org/wiki/Ground_bass | A figure that persistently repeats in the same voice, exact repetition or repetition with variation, and the ground bass as a bass line repeated under changing upper parts |
| S22 | Wikipedia, "Sequence (music)" | https://en.wikipedia.org/wiki/Sequence | Restatement of a motif at a higher or lower pitch in the same voice, usually two to four segments in one direction at the same interval distance, real versus tonal sequences |
| S23 | Wikipedia, "Alberti bass" | https://en.wikipedia.org/wiki/Alberti_bass | Broken chord accompaniment presenting the chord as lowest, highest, middle, highest, repeated, typical of the Classical era; named after Domenico Alberti |
| S24 | Wikipedia, "Cadence" | https://en.wikipedia.org/wiki/Cadence | The four cadence types with their chord motions: authentic V to I or V7 to I, half ending on V, plagal IV to I, deceptive V to vi; a ii-V-I example in C major; the cadence as the cradle of tonality |
| S25 | Wikipedia, "Sonata form" | https://en.wikipedia.org/wiki/Sonata_form | Exposition, development and recapitulation as the three large sections, with introduction and coda optional |
| S26 | Wikipedia, "Rondo" | https://en.wikipedia.org/wiki/Rondo | A refrain alternating with contrasting episodes, the patterns ABACA and ABACABA named, and the form as the height of its popularity in the late eighteenth century |
| S27 | Wikipedia, "Minuet" | https://en.wikipedia.org/wiki/Minuet | A dance usually in 3/4; the early minuet usually binary with two repeated sections of about eight bars, later a rounded binary A B A with the trio in the middle |
| S28 | Wikipedia, "Period (music)" | https://en.wikipedia.org/wiki/Period_(music) | A period as an antecedent plus a consequent phrase, about eight bars, the antecedent ending in a weaker cadence (often half) and the consequent in a stronger one (often authentic) |
| S29 | Wikipedia, "Power chord" | https://en.wikipedia.org/wiki/Power_chord | A power chord is the root plus the fifth and possibly octaves, with no third, so it is neither major nor minor; the 3:2 ratio keeps it coherent under distortion; it survives fast chord changes |
| S30 | Wikipedia, "Palm mute" | https://en.wikipedia.org/wiki/Palm_mute | Damping the strings at the bridge while picking gives the short chugging attack; heavier muting shortens the note and adds percussion; thrash metal fused it with fast alternate picking |
| S31 | Wikipedia, "Alternate picking" (tremolo picking redirects here) | https://en.wikipedia.org/wiki/Tremolo_picking | Rapid down and up strokes on one note at high speed are called tremolo; alternate picking is required at very high tempos; palm muting plus alternate picking gives blast picking, the machine gun riff of thrash and death metal |
| S32 | Wikipedia, "Phrygian dominant scale" | https://en.wikipedia.org/wiki/Phrygian_dominant_scale | Phrygian dominant as the fifth mode of harmonic minor, spelled 1 b2 3 4 5 b6 b7, its flat second and augmented second as the signature intervals, its main chords I, bII, iv and vii, and its use for secondary dominants |
| S33 | Wikipedia, "Pentatonic scale" | https://en.wikipedia.org/wiki/Pentatonic_scale | The minor pentatonic as scale degrees 1, b3, 4, 5 and b7 of the natural minor, described as a gapped blues scale, with no semitones in the anhemitonic form |
| S34 | Wikipedia, "Dorian mode" | https://en.wikipedia.org/wiki/Dorian_mode | Dorian as a diatonic mode with a major sixth; the i to III to VII to IV chord sequence that reads as minor but ends with a major third above the tonic |
| S35 | Wikipedia, "Chiptune" | https://en.wikipedia.org/wiki/Chiptune | With few voices the standard way to fake polyphony is a quick arpeggio, described as one of the most relevant features of chip music |
| S36 | Wikipedia, "Harmonic minor scale" | https://en.wikipedia.org/wiki/Harmonic_minor_scale | The raised seventh makes an augmented second between the sixth and seventh degrees; harmonically it is used over V7 rather than over the tonic; the diminished triad on the raised seventh has dominant function; the scale spawned neoclassical metal |
| S37 | Wikipedia, "Phrase (music)" | https://en.wikipedia.org/wiki/Phrase_(music) | A phrase ends with a cadence; in common practice phrases are often four bars, and the antecedent and consequent are the two halves of a period |
| S38 | Wikipedia, "Nintendocore" | https://en.wikipedia.org/wiki/Nintendocore | A style fusing chiptune and game music with hardcore punk and heavy metal; bands such as Minibosses play NES repertoire with heavy metal riffing, which shows the repertoire carries rock and metal reading |
| S39 | Wikipedia, "Mega Man 2" | https://en.wikipedia.org/wiki/Mega_Man_2 | Capcom NES title with a soundtrack by Takashi Tateishi that reviewers and later publications rank among the greatest game soundtracks, and which cover bands have rerecorded as rock |
| S40 | Wikipedia, "Castlevania III: Dracula's Curse" | https://en.wikipedia.org/wiki/Castlevania_III:_Dracula%27s_Curse | Konami NES title with music by Hidenori Maezawa and colleagues, its soundtrack singled out by critics, and a programmer citing the Japanese version's special sound chip |
| S41 | Wikipedia, "Castlevania" | https://en.wikipedia.org/wiki/Castlevania | The series as gothic horror, praised across retrospectives for its iconic music as well as its setting |
| S42 | Wikipedia, "Contra (video game)" | https://en.wikipedia.org/wiki/Contra_(video_game) | Konami run and gun with the NES version scored by Hidenori Maezawa and Kiyohiro Sada, the arcade composer being Kazuki Muraoka |
| S43 | Wikipedia, "Kid Icarus" | https://en.wikipedia.org/wiki/Kid_Icarus_(video_game) | Nintendo NES title composed by Hirokazu Tanaka, with reviewers praising its music, set in a Greek-inspired fantasy world |
| S44 | Wikipedia, "Bass drum" (double bass drum redirects here) | https://en.wikipedia.org/wiki/Double_bass_drum | The kick drum as the pedal-struck bass drum of a kit, with double bass drumming treated as its own technique with method books |

| S45 | BBC News, "People recognise songs in five seconds" (reporting Burgoyne et al., Hooked on Music, 2013) | https://www.bbc.com/news/science-environment-29847739 | About 5 second average recognition, 12,000 plus participants, 1,000 plus clips, fastest times 2.29 to 2.62 s |
| S46 | Jakubowski, Finkel, Stewart and Mullensiefen, "Dissecting an earworm", 2017 | https://doi.org/10.1037/aca0000090 | 3,000 people, 100 earworm vs 100 control tunes, 83 melodic features, tempo plus two contour measures, faster tempo and common global contours |
| S47 | Dowling and Bartlett, "The importance of interval information in long term memory for melodies", 1981 | https://doi.org/10.1037/h0094275 | Contour dominates after a 5 s delay, interval information retained at 31 s |
| S48 | Bailes, "Dynamic melody recognition: distinctiveness and the role of musical expertise", 2010 | https://doi.org/10.3758/mc.38.5.641 | 32 listeners, 120 melodies, distinctiveness model explaining 85 percent of variance |
| S49 | Temperley, "Melodic pattern repetition and efficient encoding: a corpus study", 2024 | https://doi.org/10.18061/emr.v18i2.9289 | 6,208 folk songs and 9,788 themes, local metrically parallel multi interval repetition, R-I-I 2.7 times I-I-I at one measure distance |
| S50 | Bechtold, Curry and Witek, "The perceived catchiness of music affects the experience of groove", 2024 | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0303309 | 450 participants, 240 clips, 56 percent recognition, 60.7 percent drums, 54.7 percent bass, catchiness predicts urge to move |
| S51 | Hooktheory theorytab, Mega Man 2 Dr Wily Stage 1 | https://www.hooktheory.com/theorytab/view/takashi-tateishi/mega-man-2---dr-wily-stage-1 | C minor, 180 bpm, 29 semitone range, 0.89 beats per note over 160 beats, 95 percent diatonic, 68 percent chord tones, chord bass melody 91 |
| S52 | Hooktheory theorytab, Super Mario Bros 3 Overworld | https://www.hooktheory.com/theorytab/view/koji-kondo/super-mario-bros-3---overworld | 15 semitone range, 0.89 beats per note over 64 beats, 91 percent diatonic, 81 percent chord tones, chord complexity 32, chord bass melody 96 |
| S53 | Hooktheory theorytab, Final Fantasy Battle | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---battle | G minor, 150 bpm, 8 semitone range, 0.88 beats per note over 106 beats, 80 percent diatonic, 69 percent chord tones, chord complexity 94 |
| S54 | Hooktheory theorytab, Final Fantasy Prelude | https://www.hooktheory.com/theorytab/view/nobuo-uematsu/final-fantasy---prelude | B flat major, 100 bpm, melodic complexity 93 to 94, chord prog novelty 95, one broken chord pattern |
| S55 | Hooktheory theorytab, Kid Icarus Underworld | https://www.hooktheory.com/theorytab/view/hirokazu-tanaka/underworld---kid-icarus | 152 bpm, 6/8, 22 semitone range, chord prog novelty 88 |
| S56 | Hooktheory theorytab mirror, Castlevania Vampire Killer | http://devhookpad.hooktheory.com/theorytab/view/kinuyo-yamashita/castlevania---vampire-killer | 41 semitone range, 0.62 beats per note over 64 beats, 82 percent diatonic, 76 percent chord tones, punchy syncopation. The main domain page did not load and the mirror did |
| S57 | Andrew Schartmann interview, Analyzing NES Music, Intellect Books | https://intellect.stisonbooks.com/media/Andrew-Schartmann-interview.pdf | Short reusable units reordered and recombined, nested loops, layered loops across voices, illusion of variety (Neil Baldwin), transpositional sequences, Lydian colour from D to E major |
| S58 | Wikipedia, Super Mario Bros. theme | https://en.wikipedia.org/wiki/Super_Mario_Bros._theme | C major, about 100 bpm, swing and prominent syncopation, periodic structure, tempo raised to match Mario's movement |
| S59 | Cartridge Lit, "High Scores: Dr. Wily Stage 1", 2020 | http://cartridgelit.com/2020/10/29/high-scores-dr-wily-stage-1 | Minor march, two sections with a bridge that releases tension, hook dense writing, 150 to 180 bpm claimed for the series |
| S60 | Zelda Universe, "The copyright incident responsible for the iconic Zelda theme", quoting the 2016 Nintendo developer interview | https://zeldauniverse.net/2019/10/22/zeldas-study-the-copyright-incident-responsible-for-the-iconic-zelda-theme | Planned Ravel Bolero use blocked by copyright, replacement written overnight from the game's own overworld theme |
| S61 | Eurogamer, "Castlevania's Vampire Killer beats" | https://www.eurogamer.net/castlevanias-vampire-killer-beats | Fast driving beats, classical organ and horror score references, two square voices taking turns and crossing registers, 16 bar loop, D minor with heavy flat seven use |
| S62 | Music Production Wiki, "How to recreate the chiptune sound" | https://musicproductionwiki.com/articles/how-to-recreate-the-chiptune-sound | Duty settings and their timbres, frame locked engine at 60 Hz, one frame per step arpeggio, delayed vibrato, mid note duty change, pseudo echo, noise percussion by envelope |
| S63 | NESdev Wiki, APU basics | https://www.nesdev.org/wiki/APU_basics | Register level volume, duty and period bytes, writing the high period byte resets the phase and pops so vibrato uses the low byte |
| S64 | WiKirby, Green Greens (theme) | https://wikirby.com/wiki/Green_Greens_(theme) | Two sections, C major then C minor, ascending tonic triad peaking over an octave above the start then descending about half a scale, offbeat entry with elongated strong beat, deceptive cadence into the relative minor |
| S65 | Wikipedia, Korobeiniki | https://en.wikipedia.org/wiki/Korobeiniki | The folk song as the Tetris theme, Tanaka's 1989 arrangement, required in every version since 2002 |
| S66 | Zelda Dungeon, "The legend of music 02: Koji Kondo's masterpiece" | https://zeldadungeon.net/the-legend-of-music-02-koji-kondos-masterpiece | The Bolero copyright story, the title theme written in one day, the non standard mode reading of the overworld melody (fan analysis, treated as such) |
| S67 | Killingly and Lacherez, "The song that never ends", 2023 | https://europepmc.org/article/PMC/PMC10585939 | 44 participants, four novel choruses heard 1 to 4 times, exposure increased later musical interference, familiarity and desire to sing along rose |

Link check on 2026-10-21: S7, S8, S9, S10, S11, S12 and S14 answered HTTP 200 to a scripted request; S1 to S6,
S13 and S15 return 403 to scripted requests, so those were opened through a page extractor the same day and the
titles, dates and quoted statements above were read from the live pages. S16 is a local file read on 2026-10-21.

Sources deliberately not used: any transcript or analysis that quotes a tune, and any source that could only be
reached by downloading or decompiling a game.

## 7. Progression grammar per mood

Two keys only: A minor (the title theme's key, per S16) and C major (the middle section of the title theme, per
S16). Each mood is a set of progressions, and each progression is a list of chords. A generator draws one
progression, then realises it with the recipes above.

Notation: Roman numerals are relative to the stated key. `bVI` is the borrowed flat sixth, `iv` the minor
subdominant, `bIII` the flat third, `V7` the dominant seventh, `v7` the minor dominant seventh, `ii7` the supertonic
seventh, `sus4` the suspended fourth.

### 7.1 A minor

| Mood | Progressions | Colour notes | Recipes to pair |
| --- | --- | --- | --- |
| Determined | i, i, bVI, bVII ; i, bVI, bVII, i | bVI as F major (Dorian colour), bVII as G major | UEM-01, CHIP-05, CHIP-02 |
| Melancholy | i, iv6, v, i ; i, bVI, iv, i | iv6 first inversion D minor over F, v as E minor | UEM-03, MOT-01, CHIP-07 |
| Hopeful | i, bVI, bIII, bVII ; i, iv, bVII, i | bIII as C major, iv as D minor | UEM-01, MOT-04, CHIP-08 |
| Ominous | i, v, bVI, V7 ; i, bII, i, V7 | bII as the Neapolitan Db major, V7 as E7 | CHIP-03, CHIP-07, CHIP-01 |
| Tender | i7, v7, bVI, iv ; i, v, bVI, bVII | seventh chords on i and v soften the tonic | MOT-03, MOT-07, UEM-02 |
| Triumphant | i, bVI, bIII, bVII, i ; v7, V7, i | V7 to i as the arrival | UEM-05, CHIP-04, CHIP-02 |
| Playful | i, bVII, bVI, bVII ; i, bIII, bVII, i | bVII rocking between the tonic and the flat sixth | MOT-02, CHIP-03, CHIP-01 |

### 7.2 C major

| Mood | Progressions | Colour notes | Recipes to pair |
| --- | --- | --- | --- |
| Determined | I, V, vi, IV ; I, IV, V, I | vi as the minor colour under a major tonic | UEM-04, CHIP-05, CHIP-02 |
| Melancholy | I, iii, vi, iv ; I, vi, ii, V | iii as E minor, ii as D minor | UEM-03, MOT-01, CHIP-07 |
| Hopeful | I, ii, IV, V ; I, V, vi, IV | ii as the minor pre dominant, sus4 available on V | UEM-01, MOT-04, CHIP-08 |
| Ominous | I, vi, iv, V7 ; I, bVII, I, V7 | bVII as Bb major, V7 as G7 | CHIP-03, CHIP-07, CHIP-01 |
| Tender | Imaj7, vi, IVmaj7, V7 ; I, vi, iii, vi | major sevenths on the tonic and the subdominant | MOT-03, MOT-07, UEM-02 |
| Triumphant | I, IV, V, I ; I, V, vi, IV, V, I | I IV V I as the arrival | UEM-05, CHIP-04, CHIP-02 |
| Playful | I, V, vi, IV ; I, IV, vi, V | the same four chords with a swung feel | MOT-02, CHIP-03, CHIP-01 |

### 7.3 Rules that apply to every mood

1. Every progression resolves to the tonic of its key, and the resolution is the loudest arrival of the cue.
2. Borrowed chords are at most one per four bars, so the colour reads as an event and not as a key change.
3. A cue never changes key except at a section boundary, and the section boundary is marked by a change of
   rhythmic signature rather than by a modulation (this is the MOT-05 style switch rule).
4. The title theme follows the A minor determined grammar for bars 5 to 20 and the C major hopeful grammar for the
   middle section, which is the shape already written in S16.

### 7.4 Twenty common progressions, with function labels

The twenty rows below are the common-practice and popular progressions this score draws on, written in A minor and in C major
(the two keys of the title theme). The A minor column is the reference spelling; the C major column gives the same shape in the
major key, which for the modal rows is the relative-major or parallel reading rather than a literal transposition, and the row says
so. Function labels: **T** tonic, **PD** pre-dominant, **D** dominant, and a label in brackets marks a substitute or a borrowed
function. Bar counts are the typical harmonic rhythm for a cue in this score at 96 to 132 bpm, one chord per bar unless the bar
column says otherwise. Every progression ends on a cadence type named in section 11, and the recipe ids in the last column are the
ones that realise it.

| # | Progression | A minor chords | C major chords | Roman numerals | Functions | Bars | Recipes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Authentic close | Am, Dm, E7, Am | C, F, G7, C | i, iv, V7, i | T, PD, D, T | 4 | CLS-03, CLS-08, BAR-10 |
| 2 | Plagal close | Am, Dm, Am | C, F, C | i, iv, i | T, PD, T | 3 | CLS-03, BAR-11 |
| 3 | Deceptive close | Am, E7, F | C, G7, Am | i, V7, bVI | T, D, T substitute | 3 | CLS-03, BAR-05 |
| 4 | Half cadence | Am, Dm, Em | C, F, G | i, iv, v | T, PD, D | 4 with i held 2 bars | CLS-02, CLS-12 |
| 5 | Two five one | Bm7b5, E7, Am | Dm, G7, C | ii7b5, V7, i | PD, D, T | 3 | CLS-10, CLS-03 |
| 6 | Turnaround | Am, F, Bm7b5, E7 | C, Am, Dm, G7 | i, bVI, ii7b5, V7 | T, T substitute, PD, D | 4 | CLS-10, UEM-01 |
| 7 | Circle of fifths descent | C, F, Bm7b5, E7, Am | C, F, Bdim, Em, Am | bIII, bVI, ii7b5, V7, i | T, PD, PD, D, T | 5 | BAR-04, BAR-05 |
| 8 | Pop loop | Am, F, Dm, Em | C, Am, F, G | i, bVI, iv, v | T, T substitute, PD, D | 4 | RCK-11, CLS-12 |
| 9 | Royal road | F, G, Em, Am | F, G, Em, Am | bVI, bVII, v, i | PD, D, T, T | 4 | CLS-09, UEM-05 |
| 10 | Ostinato ground | Am, Em, F, C, Dm, Am, Dm, E | C, G, Am, Em, F, C, F, G | i, v, bVI, bIII, iv, i, iv, V | T, D, T substitute, T, PD, T, PD, D | 8, one chord per bar | BAR-05, BAR-04 |
| 11 | Modal minor lament | Am, F, G | Am, F, G (relative minor reading) | i, bVI, bVII | T, PD borrowed, D borrowed | 3 or 6 | BAR-02, UEM-06 |
| 12 | Secondary dominant chain | Am, A7, Dm, E7 | C, A7, Dm, G7 | i, V7/iv, iv, V7 | T, D of PD, PD, D | 4 | CLS-11, CLS-10 |
| 13 | Neapolitan approach | Bb, E7, Am | Db, G7, C (chromatic in major) | bII, V7, i | PD chromatic, D, T | 3 | CLS-11, MET-06 |
| 14 | Pivot to the relative major | Am, C, Dm, E7 | Am, C, Dm, G7 (minor reading) | i, bIII, iv, V7 | T, T, PD, D | 4 | CLS-02, BAR-10 |
| 15 | Cadential six four | Am, Dm over F, E7, Am | C, F over A, G7, C | i, iv6, V7, i | T, PD, D, T | 4 | CLS-03, CLS-08 |
| 16 | Dorian vamp | Am, D | Dm7, G (D Dorian) | i, IV | T, PD with raised sixth | 2 or 4 | RCK-07, MOT-02 |
| 17 | Minor pentatonic vamp | Am, G | C, Bb | i, bVII | T, D borrowed | 2 or 4 | RCK-06, RCK-09 |
| 18 | Waltz period | Am, Dm, E7, Am | C, F, G7, C | i, iv, V7, i in 3/4 | T, PD, D, T | 4, one chord per bar | CLS-06, CLS-07, CHIP-05 |
| 19 | Lament bass descent | Am, Em over G, Dm over F, E | C, G over B, Am, G | i, v6, iv6, V | T, D, PD, D | 4, bass descends 1 7 6 5 | BAR-05, CHIP-02 |
| 20 | Flat side cadence | F, G, Am | F, G, C | bVI, bVII, i | PD borrowed, D borrowed, T | 3 or 6 | MET-06, UEM-05 |

## 8. Limits of this document

- No melody is transcribed, and no source was read that would have required one. Every recipe is a rule.
- The recipe parameters are our operationalisation of a described habit. Where the source says a thing happened
  (for example a delayed second pulse in the FF I Prelude) the recipe reproduces the mechanism; where the source
  only describes a feel (for example "jazzy pieces" on EarthBound) the recipe is our reading of it and is marked
  as such in section 4 and 5.
- The harmony claims about Mother and Fox are thin in the published record, because most published writing about
  those scores is descriptive rather than analytical. The progression grammar in section 7 is therefore largely
  period convention plus the manager's own score, not a transcription of any one cue.
- Nothing here has been rendered yet. The proof that these recipes work is that the arranger can realise the
  title theme from the row ids alone; that is the next card, MUS-ARRANGER.

## 9. The four new families, and what changes on the chip

Sections 10 to 13 cover four styles that the first pass of this bible did not treat: Baroque practice, Classical period practice,
rock scaled down to two pulse channels, and metal on the 2A03. Section 14 holds the forty six recipes as tables, in the same seven
column format as section 5, so the build script reads them the same way. Section 7.4 holds the twenty progressions all four families
draw from.

Three things stay true across all four families, and they are the reason every recipe below is short and mechanical rather than a
description of a mood.

1. A chord is an interval, not a stack. With two pulse channels, the widest reliable harmony is two notes at a time; a third becomes
   an arpeggio or a second channel's trade-off. This is why the Baroque recipes are two voice and why the rock recipes are dyads.
2. An ornament is a rate, not a symbol. There is no notation layer here: a trill is an alternation at 32nd rate, a mordent is three
   notes at 64th rate, a palm mute is an envelope decay counted in frames, a tremolo is a note rate with channel alternation.
3. A form is a bar count. Rondo, sonata and minuet enter the arranger as section lengths and cadence positions, never as a diagram
   the generator has to interpret.

New parameter tokens introduced by sections 10 to 13:

| Token | Meaning |
| --- | --- |
| `subject_bars` | length of the imitative subject, in bars |
| `entry_delay_bars` | bars between one voice's entry and the next |
| `entry_interval` | interval of the answering entry, for example perfect_fifth_above or octave_below |
| `episode_bars` | bars of free or sequenced material between subject entries |
| `sequence_segments` | how many statements a sequence makes, 2 to 4 |
| `ground_bars` | length of the repeating bass, in bars |
| `ornament_rate` | note rate of an ornament, for example 32nd or 64th |
| `cadence_a`, `cadence_b` | cadence types at the end of the antecedent and consequent |
| `phrase_bars` | bars per phrase |
| `form` | section letter pattern, for example ABACA |
| `gate_pct` | fraction of a note's value the channel actually sounds |
| `decay_frames` | envelope decay length in frames at 60 Hz |
| `scale` | named pitch set, for example minor_pentatonic, dorian, phrygian, harmonic_minor |
| `alternation` | what the fast figure alternates between, for example per_note or pulse1_pulse2 |
| `kick_grid`, `snare_grid`, `hat_grid` | the note grid each drum sound sits on |

The cue types are the existing ones plus one new one: title, town, battle, boss, ending, field, sad, character, secret, any. The
`ending` type is new in this pass and means the staff roll and the final scene music, which is the one cue where a slow tempo and a
full cadence are allowed to run longer than eight bars.

## 10. Baroque on the NES

### 10.1 What the sources say

- Counterpoint is the relationship of two or more simultaneous lines that depend on each other harmonically but stay independent in
  rhythm and contour, and imitative counterpoint repeats a main idea across voices (S17). Parallel voices that fuse into one timbre
  are treated as a fault, which on two pulse channels is a real constraint and not an abstraction: two pulses moving in parallel
  thirds at 50 percent duty genuinely fuse (S17, S1).
- A fugue states its subject at different pitches, the exposition is complete when every voice has entered, episodes separate the
  later entries, and the last entry returns to the tonic (S18).
- A sequence restates a motif higher or lower in the same voice, usually two to four segments in one direction at the same interval
  distance, and it may be real (exact transposition) or tonal (diatonic) (S22).
- Progressions and modulation in tonal music very often move by fifths, and the circle of fifths is the standard map of that motion
  (S20). A ground bass repeats one bass figure while the upper parts change (S21).
- A trill alternates a note with the one above it; a mordent is a single quick alternation; both were expected of a Baroque keyboard
  player and were partly improvised (S19).

### 10.2 What the chip forces

- Two voice counterpoint has to earn its independence in rhythm, not in register, because both pulses have the same tone colour at the
  same duty. The recipe answer is a fixed rule: when one voice holds, the other moves; when both move, one moves in eighths and the
  other in quarters.
- A three note chord has to be an arpeggio. The published account of chiptune practice names the quick arpeggio as the standard way to
  fake polyphony (S35), which is exactly what a Baroque broken chord wants anyway, so the two constraints agree.
- A ground bass lives on the triangle, because the triangle holds pitch without an envelope and its one fixed volume is what makes a
  repeating figure read as a foundation rather than as a melody (S1, S21).
- Ornaments are free on the pulse channels: no extra voice is needed, only a rate. The cost is that an ornament eats the note's time,
  so the recipes below budget it as a percentage of the note.

### 10.3 NES precedent

- The Final Fantasy prelude is the strongest single precedent: a two pulse arpeggio with the second pulse delayed, described in
  published writing as Bach-like (S7), with the composer himself describing the trick of a shifted second voice and the in-game
  arpeggio as the way a five channel chip implies a chord (S7, S8).
- Uematsu's second Final Fantasy score is described as having a Baroque shape (S7), which is the same lineage the BAR recipes formalise.
- Castlevania III on the Famicom carries the Konami VRC6, which adds two pulses and a sawtooth (S5, S6); the soundtrack is singled out
  in published retrospectives, and a Konami programmer cited that special sound chip as a reason the game is his favourite (S40).
  This is the reason our score carries the same expansion chip: a three or four voice imitative texture is only practical with it.

### 10.4 Where Baroque goes in this game

- `title`: a two voice invention over a circle of fifths descent, with the VRC6 pulse holding a slow cantus. This is the section that
  should feel older than the rest of the score.
- `town`: a binary dance pair, 8 plus 8 bars, repeated, with a mordent on the phrase openings. Cheaper in voices than the title.
- `boss`: subject entries at one bar intervals, no episode longer than two bars, trill on the cadence. The imitation is the tension:
  the second voice is the boss answering the hero.
- `ending`: the same subject as the title, with the answer on the VRC6 pulse in 100 percent mode, so the ending is audibly the title
  grown up.

## 11. Classical period

### 11.1 What the sources say

- Alberti bass presents the chord lowest, highest, middle, highest, repeated, and it is the characteristic Classical accompaniment,
  named after Domenico Alberti (S23).
- A period is an antecedent plus a consequent, about eight bars, with the antecedent ending in a weaker cadence, often a half cadence,
  and the consequent in a stronger one, often an authentic cadence (S28). A phrase ends in a cadence and in common practice is often
  four bars (S37).
- Cadences: authentic is V to I or V7 to I, half cadence ends on V, plagal is IV to I, deceptive is V to vi, and the article's own
  example is a ii-V-I in C major (S24).
- Sonata form is exposition, development and recapitulation, with introduction and coda optional (S25). Rondo is a refrain alternating
  with episodes, with ABACA and ABACABA given as patterns (S26).
- The minuet is normally 3/4, usually binary with two repeated sections of about eight bars, later a rounded binary A B A with a trio
  in the middle (S27).

### 11.2 What the chip forces

- Alberti bass is free: four notes per bar in eighths on pulse2 costs one channel and no voices, and it fills the harmonic space that a
  two note dyad cannot. It is the cheapest Classical texture the chip can play.
- A period is a bar template, not a mood: 4 plus 4, first cadence weak, second cadence strong, same opening motif on both phrases. The
  arranger only has to know where the two cadences land.
- An eight bar period is our phrase unit and a 32 bar cue is four of them, which is also the shortest honest sonata form: 8 bars of
  theme A in the tonic, 8 bars of theme B in the dominant, 8 bars of development sequencing the A cell, 8 bars of recapitulation with
  both themes in the tonic.
- A rondo is how a looping cue stops feeling like a loop: 8 bars of refrain, 8 of episode, 8 of refrain, 8 of a second episode, 8 of
  refrain, 40 bars total and about 90 seconds at 104 bpm.

### 11.3 Where Classical goes in this game

- `town`: Alberti bass under a period melody, at 96 to 108 bpm. This is the default town texture from here on, and it is the reason the
  town does not sound like the title.
- `field`: rondo with a short refrain, because a field cue is the one place where a 40 bar loop can be heard twice without fatigue.
- `character`: a period per character, 8 bars, with the cadence type doing the characterisation: a half cadence reads as a question,
  a deceptive cadence as a dodge.
- `ending`: the slowest cadence in the game, a plagal extension after the authentic close, and the only place a four bar tonic pedal
  is allowed.

## 12. Scaled down rock on 2A03

### 12.1 What the sources say

- A power chord is the root plus the fifth and possibly octaves, with no third, so it is neither major nor minor; the near 3:2 ratio
  keeps it coherent when distorted, and it is easy to move fast (S29). That last property is why it survives on a chip where a real
  triad does not exist.
- Palm muting damps the strings at the bridge, which shortens the note, adds percussion and produces the chug; heavier muting makes the
  note less recognisable and more rhythmic, and thrash metal fused it with fast alternate picking (S30).
- Alternate picking alternates down and up strokes continuously; at high speed on one pitch it is called tremolo, and palm muting plus
  alternate picking is blast picking, the machine gun riff of thrash and death metal (S31).
- The minor pentatonic is scale degrees 1, b3, 4, 5 and b7 of the natural minor and is described as a gapped blues scale with no
  semitones (S33). Dorian has a major sixth, and the sequence i to III to VII to IV reads as minor but lands with a major third above
  the tonic (S34).
- The NES repertoire does carry a rock and metal reading: bands in the chiptune and metal fusion style play NES music with heavy metal
  riffing (S38), and the Mega Man 2 score, with music by Takashi Tateishi, is ranked among the greatest game soundtracks and has been
  rerecorded by rock cover acts (S39). Contra's NES score is by Hidenori Maezawa and Kiyohiro Sada (S42).

### 12.2 What the chip forces

- The power chord is the perfect chip chord: root on pulse1 and fifth on pulse2, both at 50 percent duty, both on the same grid. Two of
  the chip's three usable voices then spell the interval that a distorted guitar spells with six strings, and the missing third is not a
  loss because a power chord has no third (S29).
- A third voice for the octave needs the VRC6 pulse; without it, the octave belongs to whichever channel is free for that bar.
- Palm mute is an envelope, not a hand: a decay from volume 10 to 0 in two to four frames, with the gate at 40 to 60 percent of the
  note, gives the chug (S30). A sustain of a whole bar is the opposite instruction and belongs only to a chorus chord.
- The drums are the noise channel and the DPCM channel, which is what the rock kit already is here: noise for snare and hat, DPCM for
  the kick, because the noise channel has no pitched low thud (S3, S4).

### 12.3 Where rock goes in this game

- `battle`: a two bar riff cell in minor pentatonic over a triangle root on eighths, muted dyads on the offbeats, snare on 2 and 4. This
  is the standard random encounter cue and it should never be longer than 16 bars.
- `boss`: the same kit with the riff moved to Dorian, so the major sixth arrives at the chorus and the room feels bigger, plus the
  octave doubling on the VRC6.
- `title`: one statement of the theme as a rock arrangement at the end of the title loop, so the player hears the theme twice, once as a
  waltz and once as a riff. This is the cheapest way to make the theme feel like it belongs to the game rather than to the menu.
- `ending`: a half time version of the battle riff with the mute released, which is the rock vocabulary for "the fight is over".

## 13. Metal on the NES

### 13.1 What the sources say

- At high tempo alternate picking on one pitch is tremolo, and palm muted alternate picking is blast picking (S31, S30), which gives the
  two mechanical facts the MET recipes need: a note rate, and an envelope short enough to hear the rate as rhythm.
- Harmonic minor raises the seventh, creating an augmented second between the sixth and seventh degrees; harmonically the scale is used
  over V7 rather than over the tonic, the diminished triad on the raised seventh has dominant function, and the scale had a notable
  influence on heavy metal, spawning neoclassical metal (S36). The article names players who used it (S36).
- Phrygian dominant is the fifth mode of harmonic minor, spelled with a flat second and a major third, with a flat second and augmented
  second as its signature intervals; its main chords are I, bII, iv and vii, and it is the chord scale for secondary dominants (S32).
- The bass drum is the pedal-struck kick of a kit, and double bass drumming is treated as a technique in its own right, with method books
  (S44). On this chip the kick is the DPCM channel (S4) and the metal that a noise burst cannot make.
- Castlevania III's soundtrack is singled out in published retrospectives and its Japanese version carries the VRC6 (S40); the series as a
  whole is praised for its music alongside its gothic setting (S41), and Kid Icarus, composed by Hirokazu Tanaka, was also praised for its
  music (S43). These are the two NES precedents most often described as dark or heavy in tone, which is what the MET recipes formalise.

### 13.2 What the chip forces

- Tremolo picking cannot be one channel retriggering as fast as a guitar, because at 16th rate the pulse stops being a note and becomes a
  buzz with no attack. The chip version is channel alternation: pulse1 plays note n, pulse2 plays note n+1, and the ear hears one attack
  train with an accent pattern. On the VRC6 that becomes three or four attacks per beat with real accents.
- The double bass drum is a grid, not a feel: DPCM kick on every 16th, accent on alternating strokes, which is what a double pedal does.
  Anything slower reads as a single kick.
- A diminished or phrygian riff is a dyad: root plus flat fifth, or root plus flat second, one channel each. The interval is the riff.
- The mixer gives the metal mix for free: pulse, triangle and noise are summed and the triangle and DPCM are added on top, so a riff
  doubled on the triangle gains weight without a fourth melodic voice (S1).

### 13.3 Where metal goes in this game

- `boss`: tremolo lead on the pulses over a 16th DPCM kick, phrygian riff in the second half, harmonic minor run over the V7 in the last
  four bars before the loop.
- `battle`: the rock battle kit with the riff in harmonic minor instead of pentatonic, one bar of blast picking per eight bars and no
  more, because the noise channel cannot carry eight bars of blast picking without eating the melody.
- `ending`: metal has no ending in this score. The one allowed use is a two bar unison hit figure that resolves to the tonic and hands
  over to the waltz, which is the joke: the fight music stops when the game does.

## 14. Recipe tables for the four families

Four tables, forty six recipes. Same columns as section 5: id, name, lineage, rule, parameters, cue types, sources. The build script
parses every table with this header, so a row here is as executable as a row in section 5.

### 14.1 Baroque, twelve recipes

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| BAR-01 | Two voice imitative entry | Baroque | State the subject on pulse1, bring pulse2 in on the same subject one bar later at the fifth above, and give pulse1 free eighths from that point so the two voices never move in the same rhythm | subject_bars=1; entry_delay_bars=1; entry_interval=perfect_fifth_above; counter_voice=eighths; channels=pulse1+pulse2 | title, town, boss | S17, S18 |
| BAR-02 | Four entry exposition | Bach fugue practice | Alternate subject and answer on the two pulses for four entries, with a two bar episode between entries, and drop the entry that would collide rather than voice crossing | entries=4; pattern=subject_answer_subject_answer; episode_bars=2; collision_rule=drop_entry | title, boss | S18, S17 |
| BAR-03 | Tonal sequence | Baroque and Classical | Restate a two beat motif at the next scale step, three segments in one direction, then cadence; use diatonic transposition so the sequence stays in key | cell_beats=2; sequence_segments=3; direction=up; step=diatonic_second; end=cadence | title, town, boss | S22 |
| BAR-04 | Circle of fifths descent | Baroque harmony | Move the roots down a fifth every bar for four bars and put the function order pre-dominant to dominant to tonic at the end of the chain, with the root on the triangle and the chord broken on pulse2 | root_motion=descending_fifths; bars=4; bass=triangle_root; arp=pulse2; seventh_allowed=yes | title, town, ending | S20, S21 |
| BAR-05 | Ground bass | Baroque | Repeat one four bar triangle figure exactly two to four times and change only the pulse parts above it, so the bass is the fixed point and the melody is the argument | ground_bars=4; repetitions=2_to_4; bass=triangle; upper=varied; rhythm_fixed=yes | boss, secret, title | S21, S20 |
| BAR-06 | Trill on a long note | Baroque ornament | When a melody note is a quarter or longer, alternate it with the upper diatonic neighbour in 32nds for the last third of its value, on 12.5 percent duty so the two pitches stay distinct | ornament_rate=32nd; interval=upper_second; duration_pct_of_note=33; duty=0.125; note_floor=quarter | title, town, character | S19, S1 |
| BAR-07 | Mordent on an accent | Baroque ornament | Start an accented note with three quick notes main, lower neighbour, main at 64th rate, which costs two frames and marks the beat | figure=main_lower_main; ornament_rate=64th; position=start_of_note; cost_frames=2 | title, town | S19 |
| BAR-08 | Arpeggiated chord figure | Baroque keyboard practice | Break the chord root, third, fifth, octave upward in sixteenths over two octaves on pulse2, which is the chip's only way to state a triad and the Baroque way to state it too | order=root_third_fifth_octave; subdivision=16ths; octaves=2; channel=pulse2; sustain_last=no | title, town, ending | S35, S7 |
| BAR-09 | Dance pair, binary | Baroque suite | Write section A of 8 bars in the tonic and section B of 8 bars starting on the dominant, repeat both, and keep one rhythmic figure for the whole dance | form=binary_repeats; A_bars=8; B_bars=8; B_start=dominant; repeat=both | town, field | S27, S22 |
| BAR-10 | Cadential trill to the tonic | Baroque cadence | Put the trill on the penultimate note of the phrase and land the tonic on the last beat, with the bass moving fifth to first under it, so the ornament and the cadence are one gesture | ornament=BAR-06; cadence=V_to_i; landing_beat=last; bass=triangle | ending, title, town | S19, S24 |
| BAR-11 | Cantus firmus against motion | Baroque counterpoint | Hold long values on pulse2 (halves and wholes) while pulse1 moves in eighths, forbid voice crossing, and let the slow voice change only on strong beats so the motion is audibly one voice | slow_voice=pulse2; slow_values=half_or_whole; fast_voice=pulse1; fast_values=eighths; crossing=none | town, sad, secret | S17 |
| BAR-12 | Organ chorale stab | Baroque, VRC6 | Use the first VRC6 pulse in 100 percent duty as a held chorale voice, move one voice at a time, and double the bass on the triangle so the four voice texture reads as four voices on seven channels | channel=vrc6_p1; duty=1.0; motion=one_voice_at_a_time; bass=triangle_doubling; voices=4 | title, town, ending | S6, S17 |

### 14.2 Classical, twelve recipes

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| CLS-01 | Alberti bass | Classical | Under the melody, break the chord on pulse2 in the order lowest, highest, middle, highest at eighth rate, one chord per bar, which is the standard Classical accompaniment and costs exactly one channel | order=lowest_highest_middle_highest; subdivision=8ths; chord_per_bars=1; channel=pulse2 | town, title, field | S23 |
| CLS-02 | Antecedent and consequent | Classical period | Write an 8 bar period as 4 plus 4, the antecedent ending on a half cadence and the consequent ending on an authentic cadence, with both phrases opening on the same motif | phrase_bars=4; period_bars=8; cadence_a=half; cadence_b=authentic; opening=shared_motif | town, character, title | S28, S37 |
| CLS-03 | Cadence palette | Classical | End every phrase with one of the four named cadences: authentic V to I for closure, half ending on V for a question, plagal IV to I for a soft end, deceptive V to vi for a dodge, and never leave a phrase without one | authentic=V7_to_i; half=any_to_V; plagal=IV_to_I; deceptive=V7_to_vi; phrases_unclosed=0 | any | S24, S37 |
| CLS-04 | Compressed sonata | Classical | Build a 32 bar cue as 8 bars of theme A in the tonic, 8 bars of theme B in the dominant, 8 bars of development sequencing the A cell, 8 bars recapitulating both themes in the tonic, which is the shortest honest sonata form on this chip | A_bars=8; B_bars=8; development_bars=8; recap_bars=8; B_key=dominant; recap_key=tonic; total_bars=32 | boss, battle | S25 |
| CLS-05 | Rondo refrain loop | Classical | Alternate an 8 bar refrain with two 8 bar episodes, episode one in the dominant and episode two in the relative major or minor, then close on the refrain, giving a 40 bar loop that does not read as a loop | form=ABACA; refrain_bars=8; episode_bars=8; episode_1_key=dominant; episode_2_key=relative; total_bars=40 | town, field, title | S26 |
| CLS-06 | Minuet figure | Classical dance | Write 3/4 with the bass on beat 1, a chord stab on beats 2 and 3, an 8 bar binary section repeated, and the melody in quarters with a stepwise lift on beat 3 | meter=3/4; bars=8; repeat=yes; bass=beat_1; stabs=beats_2_and_3; melody=quarters | town, title | S27, S1 |
| CLS-07 | Waltz at cue tempo | Classical dance | Take the minuet figure to 130 to 160 bpm, put the melody in dotted rhythms in the second half of each bar, and keep the beat 2 and 3 stabs on the saw channel so the dance pulse survives the tempo | meter=3/4; tempo_min=130; tempo_max=160; melody=dotted_second_half; stabs=vrc6_saw | title, town, ending | S27, S16 |
| CLS-08 | Function rule | Classical harmony | Label every chord tonic, pre-dominant or dominant before writing it, and forbid a pre-dominant from moving to another pre-dominant except ii to IV; this one rule removes most amateur harmonic stalls | functions=T_PD_D; pre_to_pre=forbidden_except_ii_IV; cadence_every=phrase_end | any | S24, S28 |
| CLS-09 | Minor close, counted | Classical, minor key | Take the i, iv, V7, i close and give each chord a stated number of bars, two then two then two then two, with the V7 held longest so the arrival is heard | progression=i_iv_V7_i; bars_per_chord=2; V7_bars=2; cadence=authentic | ending, town, boss | S24, S37 |
| CLS-10 | Turnaround, counted | Popular and Classical | Play I, vi, ii, V one bar each to close a section and reopen it, with the V on the last bar, which is the cheapest four bar engine in the score | progression=I_vi_ii_V; bars_per_chord=1; section_bars=4; last_chord=V | town, battle, title | S24, S28 |
| CLS-11 | Secondary dominant | Classical and later | One bar before a target chord, play the dominant seventh of that target, resolve it on the next bar, and allow at most one secondary dominant per four bars so the colour reads as an event | pattern=V7_of_target; resolve=next_bar; max_per_bars=4; targets=ii_IV_V | town, boss, ending | S24, S32 |
| CLS-12 | Four bar phrase rhythm | Classical | Put one chord per bar, one cadence every four bars, and never the same chord on both sides of a cadence, so the harmonic rhythm and the phrase rhythm agree | chord_per_bars=1; cadence_every_bars=4; repeat_across_cadence=no | town, field, character | S37, S28 |

### 14.3 Rock on 2A03, twelve recipes

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| RCK-01 | Power chord on two pulses | Rock | Play the root on pulse1 and the fifth on pulse2 on the same grid at 50 percent duty, with no third anywhere, which is a real power chord and the only triad the chip can voice | interval=perfect_fifth; channels=pulse1+pulse2; third=omitted; duty=0.5; grid=8ths | battle, boss | S29, S1 |
| RCK-02 | Octave doubled power chord | Rock, VRC6 | Add the octave of the root on the first VRC6 pulse at the same rhythm and lower volume, so the chord gains size without gaining a third | voicing=root_fifth_octave; octave_channel=vrc6_p1; vol_pct=70; third=omitted | boss, battle | S29, S6 |
| RCK-03 | Palm mute by envelope | Rock and metal | Give every muted chord an envelope decay of three frames from volume 10 to 0 and a 50 percent gate, which is the chip's palm mute: the attack is the whole note | decay_frames=3; vol_start=10; gate_pct=50; applies=chords_on_the_grid | battle, boss | S30, S1 |
| RCK-04 | Triangle root pulse | Rock bass | Put the root on the triangle on every eighth with an accent on beats 1 and 3, and jump the octave only on the last beat before a chord change, so the bass drives without competing with the riff | pattern=root_eighths; accent=beats_1_and_3; octave_jump=last_beat; channel=triangle | battle, boss, town | S1, S29 |
| RCK-05 | Rock drum kit | Rock | Build the kit as DPCM kick on beats 1 and 3, noise snare on 2 and 4, and noise hat on every eighth, with the hat rate high enough to sit above the riff | kick_grid=beats_1_and_3; snare_grid=beats_2_and_4; hat_grid=8ths; kick=dpcm; snare=noise | battle, boss | S4, S3 |
| RCK-06 | Minor pentatonic riff | Rock | Write the riff from 1, b3, 4, 5, b7 only, in a two bar cell, with the root on the beat and the highest scale tone on the last beat of the cell | scale=minor_pentatonic; cell_bars=2; root_on_beat=yes; peak=last_beat; semitones=none | battle, boss | S33, S39 |
| RCK-07 | Dorian chorus | Rock | Keep the riff minor but raise the sixth, so the major chord on the fourth degree is available, and use that chord as the chorus arrival | scale=dorian; sixth=raised; vamp=i_IV; cell_bars=2; chorus_chord=IV | boss, battle, field | S34 |
| RCK-08 | Gallop rhythm | Rock and metal | Play eighth then two sixteenths, repeated every beat, on muted dyads, which is the gallop and the cheapest way to make a two bar cell sound fast | pattern=eighth_two_sixteenths; repeats=per_beat; muted=yes; decay_frames=2 | battle, boss | S30, S31 |
| RCK-09 | Half time riff | Rock | Halve the riff's note values to quarters, keep the hat in eighths and the snare on 2 and 4, so the same riff reads as heavy instead of fast, which is the contrast the boss cue needs | riff_values=quarters; drums=half_time; hat=eighths; tempo_pct=100 | boss, battle | S29, S3 |
| RCK-10 | Bend into the blue note | Rock, APU sweep | Use the sweep unit with the negate flag to glide up a semitone onto the flat third and back over a quarter note, so the blue note arrives by bend rather than by a new attack | sweep=up_then_back; interval=semitone; target=b3; note_length=quarter; channel=pulse1 | battle, character, town | S1, S33 |
| RCK-11 | Verse and chorus riffs | Rock form | Write a verse riff on the tonic and a chorus riff transposed up a fourth with the octave doubled, three sections maximum, and loop the pair four times for a 32 bar cue | verse=tonic; chorus=transpose_fourth; contrast=register_and_octave; sections_max=3; loop_bars=32 | battle, boss, title | S39, S29 |
| RCK-12 | Ending tag | Rock | End with a held power chord, a noise crash and a triangle root, held for two bars, with the mute released, which is the rock full stop | final=held_power_chord; crash=noise; bass=triangle_root; bars=2; mute=released | ending, boss | S4, S29 |

### 14.4 Metal, ten recipes

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| MET-01 | Tremolo by channel alternation | Metal | Play one pitch at 16th rate and alternate the note between pulse1 and pulse2 on every attack, so the ear hears one continuous attack train with an accent pattern and no gap | note_rate=16ths; alternation=per_note; channels=pulse1,pulse2; gate_pct=60; tempo_floor=150 | battle, boss | S31, S29 |
| MET-02 | Blast picking | Metal | Take MET-01 to 32nd rate with a two frame decay on every attack, which is palm muted tremolo and reads as the machine gun figure rather than as a note | note_rate=32nd; decay_frames=2; gate_pct=40; mute=palm; bars_max=1 | boss | S31, S30 |
| MET-03 | Double bass drum feel | Metal | Put the DPCM kick on every 16th with the accent on alternate strokes, keep the noise snare on 2 and 4, and never leave a gap, which is what a double pedal does | kick_grid=16ths; accent=alternate; snare_grid=beats_2_and_4; kick=dpcm; gap=none | boss, battle | S44, S4 |
| MET-04 | Diminished riff on the raised seventh | Metal, harmonic minor | Build the riff from the diminished triad on the raised seventh and its tritone, one channel per note, and resolve it up a semitone to the tonic | scale=harmonic_minor; chord=vii_diminished; interval=tritone; resolve=up_semitone; voices=2 | boss, battle | S36, S29 |
| MET-05 | Phrygian flat second riff | Metal | Write the riff with the flat second next to the root as its signature move, over a i to bII vamp, and let the semitone be the riff rather than an ornament | scale=phrygian; signature_interval=b2; vamp=i_bII; voices=2 | boss, battle | S32, S36 |
| MET-06 | Harmonic minor leap | Metal, neoclassical | End a two bar cell with the augmented second as an upward leap from the flat sixth to the raised seventh, then resolve the seventh up to the tonic on the next strong beat | leap=flat6_to_raised7; direction=up; cell_bars=2; resolve=7_to_1; position=end_of_cell | boss, battle, ending | S36, S32 |
| MET-07 | Neoclassical lead over V7 | Metal, neoclassical | Put the harmonic minor run in sixteenths over the dominant seventh rather than over the tonic, because the raised seventh belongs to the dominant and clashes on the tonic | scale=harmonic_minor; applied_over=V7; subdivision=16ths; avoid_on=tonic_chord; run_bars=1_to_2 | boss, battle | S36 |
| MET-08 | Tritone stab | Metal | Hit root and flat fifth on the two pulses as a one beat stab with a four frame decay, on beat 4 before a section change, and never twice in the same bar | interval=tritone; duration=beat; decay_frames=4; position=beat_4; max_per_bar=1 | boss, battle | S29, S36 |
| MET-09 | Unison hit ending | Metal | End with three unison hits on one pitch, separated by rests, then a DPCM crash and one beat of silence, so the cue stops rather than fades | hits=3; spacing=rest_between; crash=dpcm; silence_beats=1; fade=no | ending, boss | S4, S44 |
| MET-10 | Low register weight | Metal mix | Keep the riff in the lowest usable pulse octave and double its root on the triangle, because the mixer sums the triangle on top of the pulses and that doubling is the only way to add weight without spending a melodic voice | riff_register=lowest_usable; bass=triangle_root_unison; extra_voice=no; mixer_note=pulses_then_triangle | boss, battle | S1, S29 |

### 14.5 How the new families join a cue

A Baroque cue is BAR-01 or BAR-02 for the texture, BAR-03 for motion, BAR-05 or BAR-04 for the foundation, BAR-06 and BAR-07 for the
ornaments, and BAR-10 for the close. A Classical cue is CLS-01 plus CLS-02 plus one of CLS-03 or CLS-12, with CLS-04 or CLS-05 choosing
the form and CLS-06 or CLS-07 choosing the dance if there is one. A rock cue is RCK-01 plus RCK-04 plus RCK-05 plus one riff recipe, with
RCK-03 deciding how percussive the chords are and RCK-11 deciding the section count. A metal cue is MET-01 or MET-02 plus MET-03 plus one
riff recipe, with MET-07 or MET-06 as the lead material and MET-09 if the cue ends.

Cross family rules, which matter more than any single recipe:

1. Never run a rock or metal cue and an Alberti bass in the same section. The two textures both want the middle of the register and the
   chip has no middle.
2. The `ending` cue is the one place where a Baroque close, a Classical plagal extension and a rock tag may follow each other, in that
   order, because the staff roll is a medley and a medley is allowed to change style at every section boundary.
3. The progression grammar in section 7.4 is shared by all four families. Rock and metal use rows 12, 16, 17 and 20 as their default
   material; Baroque uses rows 5, 7 and 10; Classical uses rows 1 to 6 and 15; the ending uses row 1 with a plagal extension.

## 15. Limits of the new sections

- Nothing here is a transcription. No melody, riff or bass line from any published game is written down in this file or in
  `data\\music_recipes.json`, and no source was read that would have required one. The game sources are cited for the fact that a score
  exists, who wrote it, what the chip adds, and how published writing describes it, not for its notes.
- The Baroque, Classical, rock and metal claims are split the same way as in section 0: a claim marked as coming from a source is stated
  in that source; the recipe is our operationalisation of it for the 2A03. Where a claim is our reading (for example that the first
  Castlevania cue reads as metal, or that the NES repertoire carries a rock reading), the sentence says so.
- The published record is thin on exactly how the cited NES composers wrote their parts. There is no interview read for this card that
  says "this riff is phrygian". The metal recipes are therefore period convention from the theory sources plus the hardware facts, not a
  description of one cue.
- The twenty progressions in section 7.4 are common practice plus popular convention, not a statistical study. "Most common" in the
  heading means most common in the literature and in this project's own score, and the bar counts are this project's tempo-dependent
  defaults.
- Nothing here has been rendered. The proof that these recipes work is that MUS-ARRANGER can realise a cue from row ids alone, and that
  the melody guard passes whatever comes out of the generator.

## 16. The hooks and humanness family, thirty rules

Nayil's verdict on the first rendered themes was that they sound good but not quite human, and that nothing sticks out. This
family answers both halves in one place: recognisability (sections 1 to 6 of knowledge/MUSIC-HOOK-GRAMMAR.md) and humanness
(section 7 of the same file). The evidence base is different from the earlier families: six peer reviewed recognition and
earworm studies, six quantitative Hooktheory theorytabs of NES themes, one scholarly interview on NES composition, and two
chip technique references. The full argument, the measured numbers and the 12 theme table live in MUSIC-HOOK-GRAMMAR.md;
the style bible cites the same source ids so the two files cannot drift.

Three numbers govern the whole family, and every rule below either enforces one of them or converts one into a parameter:

1. Recognition arrives fast. About 5 s on average and 2.3 to 2.6 s at the fastest, with contour carrying memory inside the
   first 5 s and intervals taking over later [S45, S47].
2. Repetition must be varied. Varied repetition beats literal repetition 2.7 to 1 at one measure distance, and NES composers
   faked variety with nested loops and transpositional sequences [S49, S57].
3. The chip's expression resolution is fixed: 16.7 ms per frame, 16 volume steps, 3 usable duty timbres, and a pitch write
   that pops if it touches the high period byte [S62, S63].

| ID | Name | Lineage | Rule | Params | Use | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| HOK-01 | Hook inside four bars | NES hook grammar | State the hook completely inside the first 4 bars, which is 6.9 s at 104 bpm in 3/4 and 5.3 s at 180 bpm in 4/4, because average recognition is about 5 s and the fastest is 2.3 to 2.6 s | bars_max=4; seconds_max=6.9; tempo_ref=104; metre_ref=3/4 | title, battle, field | S45, S47 |
| HOK-02 | Identifiable from two bars | NES hook grammar | Make the identifying feature audible inside the first 2 bars, because contour memory forms within 5 s and the fastest recognitions land at 2.3 to 2.6 s | bars_to_identity=2; feature=rhythm_or_leap_or_timbre | title, battle, boss | S45, S47 |
| HOK-03 | No intro before the hook | NES hook grammar | Start with the hook's own rhythmic cell in bar 1 and put any build up inside the hook; the studied stage theme opens with the figure that becomes its first half | intro_bars=0; build_inside_hook=yes | title, battle, boss | S59 |
| HOK-04 | Hook note budget | NES hook grammar | Keep the hook between 8 and 18 notes over 2 to 4 bars, which follows from the measured 0.89 beats per note of the studied themes | notes_min=8; notes_max=18; bars=2-4; beats_per_note_ref=0.89 | title, town, battle | S51, S52 |
| HOK-05 | Hook inside an octave | NES hook grammar | Keep the hook within 12 semitones even when the whole cue is wider, because the measured narrow melodies are the ones that behave as riffs | hook_range_max=12; whole_cue_range_allowed=41 | town, character, sad | S52, S53 |
| HOK-06 | One leap only | NES hook grammar | Allow at most one interval larger than a perfect fourth in the hook, always at the same metric position, so the leap itself becomes the signature | leaps_gt_fourth_max=1; position=fixed | title, battle | S56 |
| HOK-07 | Diatonic floor | NES hook grammar | Keep at least 80 percent of hook notes in the key, which is the bottom of the measured 80 to 95 percent band | diatonic_pct_min=80; measured_band_pct=80-95 | any | S51, S52, S53, S56 |
| HOK-08 | Chord tone band | NES hook grammar | Land 60 to 85 percent of hook notes on chord tones, so the strong beats belong to the harmony and the weak beats carry the colour | chord_tone_pct=60-85; strong_beats=chord_tones | any | S51, S52 |
| HOK-09 | Rhythm first | NES hook grammar | Write the rhythmic cell before the pitches: drums alone reach 60.7 percent recognition and bass alone 54.7 percent, so rhythm carries identity without a melody | cell_attacks=2-6; write_order=rhythm_then_pitch | battle, boss, field | S50 |
| HOK-10 | One predictable syncopation | NES hook grammar | Put exactly one syncopation or one rest in the cell and repeat it at the same place every statement; the studied themes are tagged loose or punchy syncopation, never freely syncopated | syncopations=1; predictability=repeat_exact | title, battle, town | S51, S52, S56 |
| HOK-11 | Arch contour | NES hook grammar | Shape the phrase as a rise to a peak near its middle then a fall back, the shape used by the studied first stage theme | peak_position=0.4-0.6; start_end=low | title, town | S64 |
| HOK-12 | Rise then leap down | NES hook grammar | After the rise, leave the phrase with one fall, which pairs with a march or heroic cue and stays audible inside a wide range | exit=leap_down; range_ref=41 | battle, boss | S56, S61 |
| HOK-13 | Pedal then step | NES hook grammar | Repeat one pitch then move by step, the design behind the measured narrow melodies that earn identity from rhythm against rich harmony | pedal_notes=2-4; motion_after=step | battle, boss | S53 |
| HOK-14 | Repeated note anchor | NES hook grammar | Anchor the hook on a repeated note so the rhythm is audible with no pitch travel; the measured narrow melodies pair an 8 to 15 semitone range with 0.88 to 0.89 beats per note | repeated_notes=1; beats_per_note=0.88-0.89 | any | S52, S53 |
| HOK-15 | Exact repeat cap | NES hook grammar | Repeat a phrase exactly no more than twice in a row and make the third statement carry an operation, because varied repetition outweighs literal repetition 2.7 to 1 at one measure distance | exact_repeats_max=2; third_statement=operated | any | S49 |
| HOK-16 | Sequence on the third statement | NES hook grammar | Transpose the whole cell by a fixed interval for the third statement, the operation described as ubiquitous in the repertoire and cheap for early sound drivers | operation=transpose_fixed; interval=one_fixed_semitone_value; statement=3 | town, battle | S57, S49 |
| HOK-17 | Rhythm variation once per eight bars | NES hook grammar | Keep the pitches and change the rhythm or the accent once per 8 bar phrase, so the phrase reads as the same idea twice | rate=1_per_8_bars; changed=pitch_kept_rhythm_changed | field, town | S49 |
| HOK-18 | Changed ending every second phrase | NES hook grammar | Rewrite the last 2 notes or the cadence on every second statement, including a deceptive cadence into the relative minor, and keep the new ending loopable | rate=every_2nd; changed=last_2_notes_or_cadence; loopable=yes | title, town, sad | S64 |
| HOK-19 | Sixteen bar loop with an eight bar B | NES hook grammar | Build the loop as 16 bars with an 8 or 16 bar B section; 16 bars is the measured workhorse loop and the wide melodies span 64 to 160 beats | loop_bars=16; b_section_bars=8-16; melody_beats=64-160 | field, town, battle | S52, S56, S61 |
| HOK-20 | Antecedent and consequent | NES hook grammar | End the first 4 bar phrase open on the dominant and close the answering phrase with an authentic cadence, joining the melody in chords at the close as the studied theme does | first_cadence=half; second_cadence=authentic; close=chords_with_melody | title, town, character | S64 |
| HOK-21 | Call and response, never doubling | NES hook grammar | Give the answering voice its own path: take turns, chase a beat apart and cross registers instead of doubling the lead | doubling=no; offset=1_beat; register_cross=yes | town, battle, character | S61 |
| HOK-22 | Declare the bass type | NES hook grammar | Name the bass line as walking, pedal or ostinato before writing the melody, because the bass alone carries 54.7 percent recognition | bass_type=walking_or_pedal_or_ostinato; recognition_ref=54.7 | any | S50, S57 |
| HOK-23 | Couple melody to bass | NES hook grammar | Keep the melody tightly coupled to the bass motion, the property the studied themes score 91 to 96 on against a database average of 50 | chord_bass_melody=91-96; coupling=high | battle, boss, title | S51, S52 |
| HOK-24 | One or two chromatic notes, fixed place | NES hook grammar | Put one or two notes outside the key in a 4 bar hook, always on the same beat, since the measured chromatic share runs 5 to 20 percent | chromatic_notes=1-2; position=fixed; share_pct=5-20 | town, sad, boss | S51, S56, S57 |
| HOK-25 | Contrast by mode first | NES hook grammar | Change section by mode or key before touching instrumentation, as the studied theme moves from the major to the parallel minor while keeping tempo and cell | contrast=mode_or_key; tempo_same=yes; cell_same=yes | battle, boss, field | S64 |
| HOK-26 | Contrast by timbre second | NES hook grammar | Spend the second contrast on duty, register or voice count: 12.5 percent thin, 25 reedy, 50 hollow, one voice dropped for 2 bars, or the lead moved an octave | duty_set=12.5_25_50; dropped_voice_bars=2; octave_shift=yes | battle, boss, secret | S62, S63 |
| HOK-27 | Frame jitter on non bass voices | NES hook grammar | Move one non bass voice by 1 or 2 frames at the same place in each phrase, because one frame is 16.7 ms and that is the smallest human timing unit on the chip | jitter_frames=1-2; voices=non_bass; place=fixed | any | S62, S63 |
| HOK-28 | Delayed vibrato, low byte only | NES hook grammar | Start a small period wobble 2 to 4 frames after the attack and write only the low period byte, because a high byte write resets the phase and pops | vibrato_delay_frames=2-4; period_bytes=low_only; depth=small | sad, character, title | S62, S63 |
| HOK-29 | Envelope per note | NES hook grammar | Give each note a volume shape from the 16 hardware levels and change it in steps of 2 or more, because a 2 step change is audible and a 1 step change is not | volume_steps=16; minimum_change=2; shape=attack_decay_or_swell | any | S62, S63 |
| HOK-30 | Breath rest and pre change fill | NES hook grammar | Rest one eighth note at the end of every 4 bar phrase on the melody voice and play a one bar noise fill before each section change, landing on the beat | rest=eighth_at_phrase_end; fill_bars=1; fill_landing=on_beat | any | S62 |

### 16.1 How the family joins a cue

The hooks and humanness rules are not a fifth style next to Baroque, Classical, rock and metal; they are the pass that every
cue goes through before delivery. Order of use: pick the cue's style family and its progression from section 7, write the cell
and the hook under HOK-01 to HOK-14, build the phrase and loop under HOK-15 to HOK-21, choose the bass and colour under
HOK-22 to HOK-24, plan the contrasts under HOK-25 and HOK-26, then run the performance pass HOK-27 to HOK-30 over the finished
note data. The twenty item checklist in section 9 of MUSIC-HOOK-GRAMMAR.md is the QA form for that last pass.

### 16.2 Link check and limits

Sources S45 to S67 were read on 2026-10-21 through a page extractor and search snippets; the Hooktheory pages were read as
pages, and S56 is the mirror because the main domain page for that theme returned not found. S58, S60, S64, S65 and S66 are
wiki and fan analyses rather than scholarship, and they are used only for documented composition facts and for structural
readings, never for note data. Two of the three research files this card expected (nes-hooks.json and chip-expression.json)
returned no answer, so the NES hook evidence here comes from the sources listed above instead of from those files.
