# Tasteful dissonance: 30 devices, their rules, their rates, and an injector spec

Card t_baafc947 (MUS-DISSONANCE), research-assistant, written 2026-10-21. This is the knowledge
file that turns Nayil's note ("a little odd dissonance against the tonal parts here and there")
into rules a program can follow. The machine readable twin is `data/dissonance_rules.json`, its
contract is `data/schemas/dissonance_rules.schema.json`, and the gate is
`tools/check_dissonance_rules.py`.

Read PLAN-V2-2026-10-21.md section 0 first. The rule for this card: study and measure, never copy
or transcribe. This file contains no melodic transcriptions of anyone's music. It carries
devices, intervals, beat positions and numbers. Every device is a technique, and technique is
not owned by anyone; the tunes are.

Tagging: every factual claim ends with a source id in square brackets, for example [S68]. New
rows for sources S68 to S77 are in section 11. Rows S1 to S67 already exist in
knowledge/MUSIC-STYLE-BIBLE.md section 6 and knowledge/MUSIC-HOOK-GRAMMAR.md section 10, and are
cited here by the same ids so one id means one source across all three files. Anything I derived
rather than read is marked [inference].

---

## 1. The problem this file answers

The Gemini ear review of title theme v3 (assets/audio/title_theme_v3/EAR_REVIEW_126.md, read
2026-10-21) scored the cue out of 10 as: hook memorability 6, drums 4, tension and dissonance 5,
human feel 3, instrumentation variety 6, structure and contrast 5. Its reason for the dissonance
score: "the harmony plays it far too safe inside standard A minor diatonic progressions without
utilizing secondary dominants, appoggiaturas, or spicy voice clashes between the 2A03 and VRC6
channels". Its own suggestion for the section change is an altered dominant, an E7 sharp 9 or a
G sharp diminished seventh, plus a noise fill.

Two of those three asks are harmonic and belong to this card; the drum interest and the human
feel belong to their own cards. What "too safe" means in numbers, using the score's own v3
tables: 52 bars, 8 of which are the trio, and the trio already carries one secondary dominant
(B7 into E minor, `C_trio` bar 3). That is one chromatic chord change in about 74 s of music.

The measured yardstick: across four analysed NES themes the melody is 95, 91, 80 and 82 percent
diatonic, so 5 to 20 percent of melody notes are chromatic, mean 13.0 [S51, S52, S53, S56]. Our
v3 melody is very close to fully diatonic, which is why a listener with no theory training still
registered a harmony that plays safe. The target in this file is not 13 percent of notes turned
dissonant; it is 3 to 6 percent of melody notes carrying a deliberate, resolved dissonance, which
is 23 to 46 percent of the chromatic budget those reference themes actually spend
[inference from the same four figures, arithmetic in section 4].

Why "odd" and not "sour": a dissonance is tasteful when the listener can predict where it is
going. That is the whole difference between an appoggiatura and a wrong note, and it is why every
rule in this file ends with a resolution.

---

## 2. The three part grammar: preparation, dissonance, resolution

Every device in the catalogue is one instance of the same shape, which the theory literature
states plainly: a chord tone, then a nonchord tone, then a chord tone [S68]. Music in Theory and
Practice puts it as: most nonharmonic tones are dissonant and form seconds, fourths or sevenths,
and are required to resolve to a chord tone in conventional ways [S68].

- PREPARATION: the note, voice and beat from which the dissonance is reached. Some devices need
  the same pitch to be a chord tone first (suspensions, retards); others need only a chord tone
  to leap or step from (appoggiaturas, escape tones).
- DISSONANCE: the note itself. Its character is set by four things: which interval it makes with
  the bass, whether it falls on a strong or a weak beat, which voice carries it, and how long it
  lasts. Accented and unaccented is the primary split in the literature, and it is the primary
  split in this file too [S68].
- RESOLUTION: the note the device owes. The obligation is directional (usually down by step),
  metric (within a stated number of beats) and harmonic (onto a chord tone of the sounding
  chord). A device with no resolution slot is a bug, not a colour, which is why F7 exists.

Three tests of taste, applied to every candidate before it is written:

1. PREDICTABLE. A listener who knows the key can name the resolution before it arrives. If the
   resolution is a surprise, the device is a mistake.
2. PROPORTIONED. The louder, longer and more exposed the voice, the lower the risk level it may
   carry. A cluster in the pad under a busy arpeggio is nearly free; a cluster in the lead on a
   held note is the loudest thing in the cue.
3. PAID BACK. Every dissonance that delays the tonic makes the arrival stronger, so it should sit
   before a cadence, a section change or a phrase end, never after the payoff.

---

## 3. What the chip allows, because it decides which devices exist

The title theme runs on NES 2A03 plus Konami VRC6: two 2A03 pulses, triangle, noise, DPCM, plus
VRC6's two pulses and sawtooth [S5, S6, S16]. Consequences that shape the catalogue:

- Three simultaneous voices are the realistic maximum before the texture turns to mud, and the
  Mother team's own working limit was three notes at once [S9]. So the cluster devices are two
  notes, not three, and no device may be doubled across two channels.
- The triangle has no volume envelope, which makes it the right voice for a pedal or a chromatic
  bass walk, and the wrong voice for a staccato stab [S1, S2].
- Two pulse channels a semitone apart beat against each other in the mixer. A semitone clash is
  therefore either very short (one beat, then resolved) or between channels of different timbre
  (2A03 pulse against VRC6 pulse), never sustained between two 2A03 pulses.
- The echo channel is a delayed copy at reduced volume [S62]. Any semitone the lead makes against
  the echo's held note is automatic, which is why DIS-18 is the one device that can happen by
  accident, and why the injector must compute it before it chooses.
- A duty change of one step is the cheapest accent the chip has, and it is how a device is marked
  without spending a voice [S62, S63].

---

## 4. Rate targets, and where the numbers come from

MUS-DATA-STATS does not exist in this repository as of 2026-10-21 (checked by search for any stats
artifact), so the fallback from the card applies: 3 to 6 percent of melody notes, and one stronger
clash per 8 bars. The derivation below turns that into whole devices per phrase.

| Step | Number | Source |
| --- | --- | --- |
| Beats per melody note in analysed NES themes | 0.88 to 0.89 | [S51, S52, S53] |
| Notes per bar in 4/4 | 4/4 divided by 0.89 = 4.49 | arithmetic |
| Notes in 8 bars, 4/4 | 36.0 | arithmetic |
| Notes in 8 bars, 3/4 at 0.89 beats per note | 27.0 | arithmetic |
| 3 percent of the 8 bar count | 0.8 to 1.1 devices | arithmetic |
| 6 percent of the 8 bar count | 1.6 to 2.2 devices | arithmetic |
| Working budget | 1 or 2 devices per 8 bars, so one per phrase | [inference] |
| Chromatic share of melody notes in four NES themes | 5, 9, 20, 18 percent, mean 13.0 | [S51, S52, S53, S56] |
| 3 to 6 percent as a share of that chromatic budget | 23 to 46 percent | arithmetic |
| One 3/4 bar at 126 bpm | 1.43 s, so 8 bars is 11.4 s | arithmetic |

Rules that follow from the table:

1. One device per 8 bars is the floor, two is the ceiling. An 8 bar section that carries three
   devices has stopped being "a little odd" and become a chromatic piece.
2. At most one risk 3 device per 8 bars, spaced at least 4 bars from any other risk 3 device.
3. At most two risk 2 devices per 8 bars, and never two in the same 2 bars.
4. No two devices within 2 beats of each other (F4), and no device that resolves onto another
   device's resolution (F5).
5. A device is counted per section, not per cue: the intro, A, A prime, B, B prime, the trio and A
   return each get their own budget of 1 to 2 per 8 bars, and the intro gets one device at most.

---

## 5. Risk levels

| Level | Name | What it sounds like | Max per 8 bars |
| --- | --- | --- | --- |
| 1 | colour | An adult chromatic note a listener hears as style: passing tones, neighbour tones, prepared suspensions, anticipations, flat six to five | 3 |
| 2 | edge | A deliberate oddity noticed once: strong beat appoggiatura, borrowed iv, secondary dominant, deceptive cadence, pedal, Neapolitan preparation | 2 |
| 3 | clash | A strong dissonance: b9 over a dominant, tritone riff, cross voice semitone, augmented pickup, cluster, Neapolitan, tritone substitution, wrong note gag | 1 |

The risk level is the injector's first filter. A cue written at risk ceiling 2 may use every
level 1 and 2 device and no level 3 device; the title theme is at ceiling 3 but with the budget of
one per 8 bars, which is one strong clash in the whole 8 bar section.

---

## 6. The catalogue: 30 devices

`data/dissonance_rules.json` holds the executable version of each row: trigger, ordered recipe
steps, permitted voices and beats, duration in beats, resolution target and window, rate, risk,
chip realisation, the assertion that proves it, sources, and the forbidden rules that apply. The
tables below are the same information in reading order. Note values are in beats; a beat is a
quarter, so at 126 bpm one beat is 0.476 s and one eighth is 0.238 s.

### 6.1 Chromatic passing and chromatic approach (4 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-01 | Chromatic passing tone, rising | Lead or countermelody, weak beat, between two chord tones a whole tone apart | 1/4 to 1/2 beat | Up a semitone to the upper chord tone, within 1/2 beat | 1 to 3 | 1 |
| DIS-07 | Accented passing tone on beat 2 of a waltz bar | Lead only, beat 2 of a 3/4 bar, chord held for the bar | 1 beat | Up a semitone to the beat 3 chord tone, exactly at beat 3 | 0.5 to 2 | 2 |
| DIS-27 | Chromatic bass descent under a held melody | Triangle, beats 2 and 3, melody held for 2 bars | 1/2 to 1 beat per step | Onto a chord tone of the next chord, from a semitone away | 0 to 1 | 2 |
| DIS-29 | Blue third slide | Lead, weak position, over a major chord or an open fifth | 1/4 to 1/2 beat | Up a semitone to the major third | 0 to 1 | 2 |

The distinction that matters: DIS-01 is unaccented and nearly invisible; DIS-07 puts the same
semitone on the beat, which is the difference between colour and comment. Use DIS-07 no more than
twice in an 8 bar waltz section, because beat 2 is where the waltz accompaniment lives.

### 6.2 Chromatic neighbour devices (3 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-02 | Chromatic lower neighbour | Lead or arpeggio, weak beat or beat 2, any chord where the melody note is 1, 3 or 5 | 1/4 to 1 beat | Back up a semitone to the note it left, same octave | 1 to 3 | 1 |
| DIS-08 | Escape tone | Lead or countermelody, weak position, between two chord tones | 1/4 to 1/2 beat | A leap of a third or fourth in the opposite direction onto a chord tone | 0.5 to 2 | 1 |
| DIS-26 | Changing tones around a chord tone | Lead, beats 2 or 3, chord held for the bar | 1/4 to 1 beat total | A step onto a chord tone after two nonchord tones | 0 to 1 | 1 |

Worked example for DIS-02 in the theme itself: in section B, the bar whose melody is a long B4
over E7, take the second eighth as A sharp and return to B4 on the third eighth. A sharp is out of
A minor and is a semitone below B, and the note it returns to is the same chord tone. It is not
the first or last note of Z, so F1 is satisfied; it is not the section's final bar, so F2 is too.

### 6.3 Appoggiatura (1 device)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-03 | Appoggiatura on a strong beat, resolving down by step | Lead or countermelody, beat 1 or beat 2, tonic, subdominant or dominant chord lasting 2 or more beats | 1/2 to 1 beat | Down a semitone or a tone onto a chord tone of the same chord, within 1 beat | 0.5 to 2 | 2 |

This is the device the ear review named first. It is the cheapest way to make a strong beat
interesting: the dissonance is where the listener expects an arrival, and the resolution is one
beat later. Enter by leap so the ear knows the note was chosen, not stepped into [S68].

### 6.4 Suspensions and retardations (5 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-04 | Suspension 4 to 3 | Lead, countermelody or pad, downbeat to beat 3, at a chord change where the fourth above the new bass was a chord tone | 1/2 to 1 beat | Down a semitone to the third above the bass | 0 to 2 | 1 |
| DIS-05 | Suspension 7 to 6 | Lead, pad or countermelody, downbeat or beat 2, on a stepwise bass or circle of fifths move | 1/2 to 1 beat | Down a step to the sixth above the bass | 0 to 2 | 1 |
| DIS-06 | Suspension 9 to 8 over a dominant | Lead or pad, beat 1 to beat 3, dominant held 2 or more beats | 1/2 to 1 beat | Down a step to the octave, which is the dominant root | 0 to 2 | 2 |
| DIS-10 | Retardation 7 to 8 | Lead or pad, downbeat or beat 2, tied into a chord where the tied note is a step below a chord tone | 1/2 to 1 beat | Up a step onto a chord tone | 0 to 1 | 2 |
| DIS-25 | Suspension chain | Lead or countermelody plus one other voice, 3 or 4 bars of descending bass | 1/2 to 1 beat per link | Down a step in every bar of the chain | 0 to 1 | 2 |

Suspensions are the device with the strongest historical warrant, and the oldest advice about
them is still the best: Fux, 1725, "endeavor, moreover, to introduce suspensions now in this
voice, now in that, for it is incredible how much grace the melody acquires by this means"
[S68]. A suspension must resolve downward; the upward resolving version is a retardation and is
the exception that proves the rule [S68].

Worked example, and this one is legal in the theme: the trio opens in E minor and moves to B7.
Prepare E5 (a chord tone of E minor) in the bar before, hold it across the change into the B7 bar,
where E is the fourth above B, and resolve down to D sharp on beat 2. The score already writes D
sharp on beat 2 of that bar, so the only change is the held preparation, and the device lands on a
note the melody already had.

### 6.5 Anticipation (1 device)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-09 | Anticipation of the next chord's third | Lead or countermelody, last eighth of a bar, any chord change at the bar line | 1/4 to 1/2 beat | The same pitch becomes a chord tone after the bar line | 0.5 to 2 | 1 |

An anticipation is the only device whose resolution is a change of harmony rather than a change of
pitch, which makes it the safest way to lean into a downbeat [S68].

### 6.6 Dominant colour (2 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-11 | Dominant seven flat nine | Lead or pad, one voice only, downbeat or beat 2, on a V7 that resolves within 2 bars | 1/2 to 2 beats | The flat nine falls a semitone to the fifth of the tonic, or any chord tone a semitone below | 0 to 1 | 3 |
| DIS-24 | Tritone substitution at a cadence approach | Pad and bass, downbeat or beat 2, the bar before the tonic | 2 to 3 beats | The bass falls a semitone to the tonic while the tritone resolves as written | 0 to 1 | 3 |

Why the b9 works: altered notes on a dominant are used as leading tones to their diatonic
neighbours, and using one in a resolving dominant "greatly increases the bite in the chord and
therefore the power of the resolution" [S74]. In A minor the b9 above E is F, and F falls to E.
That is one semitone of movement for a large increase in tension, which is exactly the trade this
card is after. The substitution variant works because the substitute chord shares the same
tritone, so the resolution is unchanged and only the bass moves [S75, S70].

### 6.7 Modal mixture (3 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-13 | Neapolitan flat two in first inversion | Pad, lead and bass, downbeat or beat 2, the bar before V in a minor key | 2 to 3 beats | The flat second falls a semitone, and the chord moves to the dominant | 0 to 1 | 3 |
| DIS-16 | Borrowed minor four from the parallel minor | Pad and lead, downbeat or beat 2, a major key reaching its subdominant | 2 to 3 beats | The lowered sixth falls a step onto the fifth of the tonic | 0 to 1 | 2 |
| DIS-17 | Flat six to five approach | Pad, bass and lead, beats 2 and 3, a minor key approaching its dominant | 1 to 3 beats | The bass falls a semitone onto the dominant root | 0.5 to 2 | 1 |

Mode mixture is borrowing from the parallel key: the most common borrowings in major lower the
sixth, and the borrowed chord is deliberately brief so the tonic is not lost [S72]. The
Neapolitan is the strongest version of the same idea, a major chord on the lowered second, most
often in first inversion, functioning as a subdominant that prepares the dominant [S70]. On the
chip it is the cheapest way to sound Baroque without a second voice.

### 6.8 Cadence and secondary function (3 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-14 | Deceptive cadence | Pad, bass and lead, downbeat of a phrase end marked as authentic | 2 to 3 beats | The dominant or the tonic within 2 bars, with the leading tone still rising to the tonic | 0 to 0.5 | 2 |
| DIS-15 | Secondary dominant | Pad, lead and bass, beat 2, beat 3 or a downbeat, before any diatonic chord that can be tonicised | 1 to 3 beats | The target chord on the next beat or bar, with the chromatic third resolving by step | 0.5 to 2 | 2 |
| DIS-23 | Secondary leading tone chord | Pad and bass, beat 2 or 3, a chord approached from a semitone below | 1/2 to 1 beat | The bass rises a semitone into the target root; the chordal seventh falls a semitone | 0 to 1 | 2 |

A secondary dominant is a major triad or dominant seventh built to resolve to a degree other than
the tonic, and its purpose is to emphasise a chord already in the progression; a tonicisation that
lasts longer than a phrase becomes a modulation [S71]. That limit is why DIS-15's resolution window
is 3 beats: the target must arrive quickly or the device turns into a key change.

The deceptive cadence is the one device here that changes harmony rather than melody. Keep the
leading tone rising to the tonic so the ear hears the arrival; move only the bass and the chord
[S24]. Green Greens is the reference case in this project's own files, where the section ends on a
deceptive move into the relative minor [S64].

### 6.9 Cross voice clash, harmonic colour, gag, pedal, cluster (8 devices)

| ID | Device | Where it may go | Duration | Resolution | Rate per 8 bars | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| DIS-12 | Tritone as a riff note | Bass or stab, eighths or offbeats, a static root with no third in the voicing | 1/4 to 1/2 beat | The riff's own root at the end of the 2 or 4 bar figure | 0 to 1 | 3 |
| DIS-18 | Cross voice minor second between echo and lead | Lead against echo, beat 2, beat 3 or an offbeat | 1/4 to 1 beat | A unison or a chord tone a semitone away, within 1 beat | 0 to 1 | 3 |
| DIS-19 | Augmented chord on a pickup | Stab or pad, pickup or the last eighth before a downbeat | 1/4 to 1 beat | The raised fifth rises a semitone at the downbeat | 0 to 1 | 3 |
| DIS-20 | Wrong note then resolve gag | Lead only, weak position, once per cue | 1/4 to 1/2 beat | The expected note, within 1 beat, louder than the mistake | 0 to 0.5 | 3 |
| DIS-21 | Pedal tone against changing chords | Triangle or pad, 2 to 4 bars, tonic or dominant | 6 to 12 beats | A bar where the pedal is a chord tone again at the end of the span | 0 to 0.5 | 2 |
| DIS-22 | Cluster stab | Two pulse voices, downbeat or section downbeat | 1 to 4 frames | Silence, then a chord tone at the next event | 0 to 1 | 3 |
| DIS-28 | Major seventh held over the tonic | Lead or pad, downbeat or beat 2, tonic held 2 or more beats | 1/2 to 2 beats | Down a semitone to the fifth, or up to the tonic | 0 to 1 | 2 |
| DIS-30 | Tritone leap answered by step | Lead, weak position, once per 16 bars | 1/4 to 1 beat | A step onto a chord tone in the opposite direction, within 1 beat | 0 to 0.5 | 3 |

Two notes on this group.

The tritone riff is the Castlevania and metal move, and the mechanism is documented in both
traditions: a power chord plus a note a tritone from the root, against a stagnant harmonic rhythm,
is the dissonant dark sound of the interval [S77, S29, S75], and the Castlevania line is one of
the most chromatic NES melodies on record at 82 percent diatonic, which means 18 percent of its
notes are outside the key [S56, S61]. The trap is tone: the riff only reads as colour when the
harmony stops moving. Against a chord that changes every beat it reads as a mistake.

The cross voice semitone is the device the ear review asked for by name ("spicy voice clashes
between the 2A03 and VRC6 channels"). It is also the only device that can happen without being
written, because the echo channel sounds a delayed copy of the lead [S62]. The injector therefore
computes the echo's held pitch from the renderer's delay before it decides anything, and DIS-18 is
the one rule whose resolution window is measured in the renderer's own delay unit.

The pedal tone deserves its own sentence: it is unique among nonchord tones because it starts on a
consonance, is sustained through a foreign harmony, and the harmony, not the pedal, returns to
consonance [S69]. That is why DIS-21's resolution target is a bar where the pedal is a chord tone
again, and why the device may not end on the dissonance.

---

## 7. The forbidden list

These eight rules are absolute. The injector checks them in this order and drops the candidate on
the first hit, because each one turns a device into something a listener hears as an error.

| ID | Rule | Check |
| --- | --- | --- |
| F1 | Never on the first or last note of a leitmotif statement: K, K2, Z, P or H, in any section, including the reprise and the character theme transpositions | note index is not 0 and not the final index of any motif span |
| F2 | Never in the final cadence bar of a section, of the loop or of the cue, and never on the tonic arrival the cadence lands on | device bar is not the last bar of a section and not a cadence arrival bar |
| F3 | Never on the first note of the loop and never in the first bar of the cue | bar index is at least the injector's first_allowed_bar, which is 1 for the cue and 1 after the loop point |
| F4 | Never closer than 2 beats to another device, and never closer than 4 bars to a risk 3 device | beat and bar gaps to neighbouring devices |
| F5 | Never on a note that is another device's resolution, and never in the same beat as another resolution | slot is not any other device's resolution slot |
| F6 | Never on the last beat before a section change | resolution slot lies inside the same section as the device slot |
| F7 | Never under a note held longer than 2 beats unless the score writes an earlier resolution slot | the resolution slot exists in the written melody |
| F8 | Never on a bar where fewer than 2 melody notes remain after the slot, and never on a tonic in the final cadence bar | remaining melody note count is at least 2 |

F1 and F2 are the two the card named. The other six exist because a device's failure mode is
almost always structural: nowhere to resolve, no silence after it, or a clash with the motif that
carries the cue's identity. Every device in the JSON carries at least F1 and F2, and the checker
refuses any device that does not.

---

## 8. The injector spec

This is the part the arranger card implements. Nothing here needs a model: it is a deterministic,
seeded search over candidate slots with a budget, and the rules already written to data.

### 8.1 Input and output

Input, per cue:

- `score`: the sections, bars, chords per bar, key, time signature, bpm, the beat grid in eighths,
  and the melody as `[pitch, duration_in_eighths]` lists, which is score_v3.yaml's own format.
- `motifs`: for each of K, K2, Z, P, H, the list of `[section, bar, note_index_start,
  note_index_end]` spans that are a statement of that motif.
- `cadences`: the list of `[section, bar, beat]` that end a section or the loop.
- `echo_delay_eighths`: 1 for this score, taken from the voice table, not assumed.
- `risk_ceiling`: 1, 2 or 3, set per cue.
- `seed`: an integer. Two runs with the same seed and the same score produce the same injections.
- `budget`: from section 4, which the injector computes from the actual melody note count of each
  section, not from a constant.

Output, one JSON object per cue:

```
{
  "cue": "title_theme",
  "seed": 126,
  "policy": "dissonance_rules.json version 1",
  "sections": [
    {"section": "A", "bars": 8, "melody_notes": 27, "budget_min": 1, "budget_max": 2}
  ],
  "events": [
    {"id": "EV-01", "rule": "DIS-04", "voice": "lead",
     "bar": 27, "beat": 1, "eighth": 1, "pitch": "E5", "duration_eighths": 1,
     "resolution": {"bar": 27, "beat": 2, "pitch": "D#5"},
     "risk": 1, "trigger": "chord change Em to B7, fourth above the new bass prepared in the previous bar"}
  ],
  "rejected": [
    {"rule": "DIS-11", "bar": 8, "beat": 1, "why": "F1: first note of a K2 statement"}
  ],
  "totals": {"events": 1, "risk1": 1, "risk2": 0, "risk3": 0, "per_8_bars": 1.0}
}
```

The `rejected` list is not debugging clutter: it is how a human reviews the injector's taste in
one page, and how the next run can be tuned without listening again.

### 8.2 Algorithm

1. COUNT. For each section, count melody notes and set `budget_min = ceil(notes * 0.03)` and
   `budget_max = ceil(notes * 0.06)`; clamp `budget_min` to at least 1, cap `budget_max` at 2 for
   an 8 bar section and at 3 for a 16 bar section, and cap risk 3 devices at one per 8 bars.
2. ENUMERATE. For each rule whose risk is at or below `risk_ceiling`, walk every slot that its
   `where` block allows: the voice exists in this score, the beat position matches the slot, the
   chord context matches the bar's chord, and the section is allowed.
3. PRE-CHECK the accidentals. Compute the current interval profile of the slot against the bass
   and against every other voice sounding on that beat, including the echo's delayed pitch. A
   candidate whose interval is already a dissonance is dropped: the device must introduce the
   clash, not repeat one.
4. GUARD. Apply F1 to F8 in order. Any failure moves the candidate to `rejected` with the rule id.
5. SCORE. Rank survivors with the weights below, which encode the three tests of taste rather
   than a model's opinion:
   - +3 if the resolution lands on a beat that is also a chord change (the payoff is shared).
   - +2 if the device sits in the 4 bars before a cadence or a section change.
   - +2 if the device is in a voice that is otherwise static for 2 or more bars.
   - -2 for every repeat of the same rule within the section, and -4 for a repeat within 8 bars.
   - -3 if the device's voice is doubled by another voice on that beat.
6. PLACE, highest risk first. Place one risk 3 device if the section has budget and the score is
   at ceiling 3; then risk 2; then fill with risk 1 until `budget_max`. After each placement,
   re-run F4 and F5 against everything placed so far.
7. STOP. Never exceed budget. An empty section is a legal outcome: silence is better than a
   device with nowhere to resolve.
8. WRITE and re-check. Emit the events, then run the checker over the emitted events with the same
   guard order, so the injector cannot ship a device the checker would reject.

### 8.3 Worked examples on title theme v3

- The trio, Em to B7. DIS-04, risk 1. Prepare E5 as a chord tone in the Em bar, hold it across
  into the B7 bar where it is the fourth above B, resolve down to D sharp on beat 2. Legal: the B7
  bar is not the section's last bar, the bar's P statement begins on B4 and ends on F sharp 5, so the
  prepared note is not one of its ends, and the resolution lands on a pitch the melody already
  contains.
- The trio, the E7 bar that turns back toward A minor. DIS-11, risk 3, in the pad only. The pad
  takes F5 on beat 2 for one beat and resolves to E5 on beat 3, while the lead keeps G sharp 4.
  One voice carries the flat nine, the resolution is a semitone down onto the fifth of the tonic
  that follows, and the section spends its single risk 3 slot there.
- Section B, the bar with the long B4 over E7. DIS-02, risk 1. A sharp on the second eighth, back
  to B4 on the third. Legal because it is neither the first nor the last note of Z and the section
  has budget for two risk 1 devices.
- Section B, lead and echo. DIS-18, risk 3, only when the computed echo pitch is a semitone from
  the lead's next note. At 126 bpm the echo delay of one eighth is 0.238 s, so the clash window is
  one eighth and the resolution must be the following eighth. If the computed pitch is not a
  semitone away, the device cannot fire, and that is the normal case.
- The final bar of A return. No device. F2 and F6 both refuse it, and the bar is already the
  dominant heard as a held B4, which has no resolution slot (F7).

### 8.4 Failure modes the spec is written against

- Device placed where the resolution is outside the section: caught by F6.
- Two semitones in a row, which reads as a chromatic scale rather than a device: caught by F4 and
  by the -4 repeat penalty.
- A device in the echo channel that doubles a lead dissonance, turning one clash into a cluster:
  caught by the interval pre-check in step 3.
- A risk 3 device every 8 bars across four sections, which is four clashes in a row: caught by the
  per cue ceiling, which no cue may exceed 4.
- A generated melody that walks into a rule's trigger constantly: caught by `tools/melody_guard.py`
  at delivery, not by the injector, which only sees scores.

---

## 9. How this plugs into the rest of the music lane

- The arranger (MUS-ARRANGER) reads `data/dissonance_rules.json` and treats an injection as a
  note event in a named voice, never as a rewrite of the melody. A chord substitution (DIS-13,
  DIS-15, DIS-16, DIS-17, DIS-24, DIS-14) is a change to the chord track, and it must be recorded
  in the score's chord list with the rule id in a comment, so the next reader can see why the
  harmony leaves the key.
- The renderer needs nothing new: every device is expressible with the seven voices the score
  already has, except the cluster, which needs both pulse channels at once and therefore one muted
  voice for its four frames [S16, S5, S6].
- The style bible's progression grammar is unchanged. A device may decorate a chord from that
  grammar, and the six substitution rules are the only ones allowed to change a chord.
- The ear review's other four asks are separate: drums (4 out of 10), human feel (3 out of 10),
  hook memorability (6 out of 10) and structure contrast (5 out of 10) each need their own card.
  Dissonance will move at most two of those scores.

---

## 10. Verification, and what the checker proves

`python tools/check_dissonance_rules.py` runs eight checks and exits 0 only when all pass:

1. The JSON validates against `data/schemas/dissonance_rules.schema.json`, with `jsonschema`
   when it is installed and with the checker's own resolver otherwise. The resolver implements
   every keyword the schema uses, so a machine without the library still validates the whole
   document.
2. Exactly 30 devices, ids DIS-01 to DIS-30, no duplicates and no gaps.
3. Every device has a resolution with a target, a direction and a positive window in beats.
4. Every forbidden id and every source id a device cites exists, with sources drawn from this
   file or from the style bible and hook grammar tables.
5. The rate policy is arithmetically consistent with the note counts it states, and no device
   exceeds its risk level's cap per 8 bars.
6. No em dash, no en dash and no other long dash in the JSON, the schema or this file.
7. This file names all 30 devices and all eight forbidden rules.
8. The device count and the rate band agree with each other under a quarter device tolerance,
   which is what rounding 0.81 devices up to 1 device needs.

What it does not prove: that a device is tasteful. That judgment is the ear review's, and the
injector's defence against bad taste is the budget, the forbidden list and the `rejected` list a
human can read.

---

## 11. Sources

New rows for this file, all read 2026-10-21. Rows S1 to S67, cited above, are in
knowledge/MUSIC-STYLE-BIBLE.md section 6 and knowledge/MUSIC-HOOK-GRAMMAR.md section 10; the ids
cited here from that set are S1, S2, S3, S5, S6, S9, S16, S17, S24, S29, S32, S33, S36, S51, S52,
S53, S56, S57, S61, S62, S63, S64.

| ID | Source | Link | What it supports |
| --- | --- | --- | --- |
| S68 | Wikipedia, "Nonchord tone" | https://en.wikipedia.org/wiki/Nonchord_tone | Definitions of passing tone, neighbour tone, escape tone, anticipation, suspension (4 to 3, 7 to 6, 9 to 8), retardation, appoggiatura, changing tones, pedal point and chromatic nonharmonic tones; the statement that most nonharmonic tones are dissonant and form seconds, fourths or sevenths and must resolve to a chord tone; the Fux 1725 quotation on suspensions; suspensions must resolve downward, the upward version being a retardation; chromatic appoggiaturas and passing tones increased in the Romantic period |
| S69 | Wikipedia, "Pedal point" | https://en.wikipedia.org/wiki/Pedal_point | A pedal point as a sustained tone, usually in the bass, against at least one foreign harmony; it begins as a chord tone, becomes a nonchord tone, and is a chord tone again when the harmony resolves; usually on the tonic or the dominant; the thrash metal muted low string as a pedal |
| S70 | Wikipedia, "Neapolitan chord" | https://en.wikipedia.org/wiki/Neapolitan_chord | The Neapolitan as a major chord on the lowered second, most often in first inversion, functioning as a subdominant substitute that prepares the dominant, and far more common in minor keys |
| S71 | Wikipedia, "Secondary chord" | https://en.wikipedia.org/wiki/Secondary_dominant | Secondary dominants as a major triad or dominant seventh resolving to a degree other than the tonic; V of V as the most common; their purpose of emphasising a chord already in the progression; a tonicisation longer than a phrase is a modulation |
| S72 | Wikipedia, "Borrowed chord" | https://en.wikipedia.org/wiki/Borrowed_chord | Mode mixture as chords borrowed from the parallel key; in major the most common borrowings lower the sixth; flat III and flat VII come from the parallel minor or Mixolydian; borrowed chords are brief enough that the tonic is not lost |
| S73 | Wikipedia, "Tone cluster" | https://en.wikipedia.org/wiki/Cluster_chord | A tone cluster as at least three adjacent tones, prototypically semitone separated; clusters are heard as dissonant in most Western music |
| S74 | Wikipedia, "Altered chord" | https://en.wikipedia.org/wiki/Altered_chord | The common dominant alterations of flat five, sharp five, flat nine and sharp nine; the statement that using one in a resolving dominant greatly increases the bite of the chord and the power of the resolution; altered notes used as leading tones to their diatonic neighbours |
| S75 | Wikipedia, "Tritone" | https://en.wikipedia.org/wiki/Tritone | The tritone as six semitones, a harmonic and melodic dissonance whose notes push toward resolution in dominant and diminished chords; its use against the keynote to avoid tonality |
| S76 | Wikipedia, "Augmented triad" | https://en.wikipedia.org/wiki/Augmented_chord | The augmented triad as a major third plus an augmented fifth; H.R. Palmer on its resolution, where the fifth rises a minor second and the third rises a minor second or stays; the augmented chord on V as a substitute dominant |
| S77 | Wikipedia, "Black Sabbath (song)" | https://en.wikipedia.org/wiki/Black_Sabbath_(song) | The main riff as a G5 power chord followed by an octave into a tritone away from the root, described as the dissonant dark sound of the tritone against a stagnant harmonic rhythm, and as one of metal's earliest uses of the interval |

Internal reads, not sources for a claim about anyone's music: assets/audio/title_theme_v3/
score_v3.yaml (52 bars, the sections and chords used in the worked examples), its
EAR_REVIEW_126.md (the scores quoted in section 1), and PLAN-V2-2026-10-21.md section 0 and
section 6 decision 5 (the corpus rule and the melody guard).

---

## 12. What this file does not claim

1. No melody from anyone's work was transcribed, and no interval in this file is a tune. The
   worked examples are the project's own theme v3 or a rule stated as intervals.
2. The Hooktheory figures are crowd sourced analyses, not the composers' own scores, and they
   measure whole analysed melody sections, so the 13 percent mean chromatic share is a yardstick
   rather than a law [inference on method].
3. The rate band is derived from published chromatic shares because MUS-DATA-STATS does not exist.
   When a measured per theme dissonance rate exists, section 4 should be replaced with it, and the
   numbers in `rate_policy` change, not the devices.
4. Taste is not in the JSON. The catalogue can stop a device from being ill-formed, and it can
   keep a cue from being saturated. It cannot make a dull idea interesting; that is the composer's
   work, and on this project it is Nayil's ear that rules.
5. The risk levels are my calibration for this project, not a published scale [inference]. They
   were set against the ear review's own language, which called the current harmony safe and asked
   for an altered dominant at a section change.
6. Nothing here licenses training on copyrighted game music. That question is separate and it is
   Nayil's decision, already recorded in PLAN-V2 section 6 decision 5.

---

## 13. Handoff

What the injector card needs from this file, in order:

1. `data/dissonance_rules.json`: the rules, the budget policy, the forbidden list, the risk caps.
2. Section 8 of this file: the algorithm, the output shape, the weights and the failure modes.
3. `tools/check_dissonance_rules.py`: the gate that must pass before an injected score is
   delivered, and the same guard order the injector uses internally.

What is deliberately left to other cards: drum interest and variation (ear review 4 out of 10),
human feel and micro timing (3 out of 10), hook memorability (6 out of 10), and structure contrast
(5 out of 10). Dissonance alone will not move those, and claiming otherwise would be the kind of
progress report that reads well and helps nobody.
