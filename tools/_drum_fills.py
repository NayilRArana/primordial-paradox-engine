"""_drum_fills.py: the fill library (40 fills, 1 and 2 beats).

A fill is written the same way as a pattern, with hits as (step, level), but its
length is a number of steps rather than bars, because the arranger drops it into
the last steps of a bar. Placement is the list of moments where the fill earns
its keep:

  before_section_change   the bar before a new section starts
  phrase_end_4            the last beat of a four bar phrase
  phrase_end_8            the last beat or two of an eight bar phrase
  phrase_end_16           the last two beats of a sixteen bar phrase, or the loop point

The instrument vocabulary is the same as the patterns: noise (with period and
loop mode), dpcm_kick, dpcm_snare. A sweep is written as one lane whose period
changes from hit to hit, which is the only pitch control the noise channel has.
"""

from _drum_dsl import L

KICK = "dpcm_kick"
SNARE = "dpcm_snare"
HAT = "noise"


class Fill:
    def __init__(self, fid, name, ftype, beats, steps, feels, placement, lanes, note=""):
        self.id = fid
        self.name = name
        self.type = ftype
        self.beats = beats
        self.steps = steps
        self.feels = list(feels)
        self.placement = list(placement)
        self.lanes = lanes
        self.note = note


def fill(fid, name, ftype, beats, steps, feels, placement, lanes, note=""):
    return Fill(fid, name, ftype, beats, steps, feels, placement, lanes, note)


ALL4 = ("waltz", "march", "rock", "metal", "baroque", "boss", "calm", "battle")
LOUD = ("march", "rock", "metal", "boss", "battle")

FILLS = [
    # --- noise rolls -------------------------------------------------------
    fill("FLR-01", "One beat sixteenth roll, flat", "noise_roll", 1, 4, LOUD,
         ["phrase_end_4", "before_section_change"],
         [L(SNARE, [(0, 6), (1, 6), (2, 7), (3, 8)], rate=13),
          L(KICK, [(0, 8)], rate=11)],
         "The plain roll. Four even hits, last one accented, kick underneath the first."),
    fill("FLR-02", "One beat roll, crescendo", "noise_roll", 1, 4, LOUD,
         ["phrase_end_8", "before_section_change"],
         [L(SNARE, [(0, 3), (1, 5), (2, 7), (3, 9)], rate=13),
          L(KICK, [(0, 8)], rate=11)],
         "Level rises 3, 5, 7, 9 across four steps. The single most useful fill in the file for a four or eight bar phrase."),
    fill("FLR-03", "Two beat roll, crescendo", "noise_roll", 2, 8, LOUD,
         ["phrase_end_8", "phrase_end_16", "before_section_change"],
         [L(SNARE, [(0, 2), (1, 3), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 9)], rate=13),
          L(KICK, [(0, 8), (4, 7)], rate=11)],
         "Eight sixteenths rising from level 2 to level 9. Use at bar 8 and bar 16, not both in the same eight bars."),
    fill("FLR-04", "Two beat roll, hairpin (loud to soft)", "noise_roll", 2, 8, LOUD,
         ["phrase_end_8"],
         [L(SNARE, [(0, 9), (1, 8), (2, 7), (3, 6), (4, 5), (5, 4), (6, 4), (7, 3)], rate=13)],
         "A falling roll pulls the listener into the next phrase instead of pushing them. Use before a quiet section."),
    fill("FLR-05", "One beat buzz roll in short mode", "noise_roll", 1, 4, ("rock", "metal", "boss", "battle"),
         ["phrase_end_4", "before_section_change"],
         [L(SNARE, [(0, 5), (1, 5), (2, 6), (3, 7)], rate=13),
          L(HAT, [(0, 4), (1, 4), (2, 4), (3, 5)], period=5, loop="short")],
         "Short loop mode gives the buzz the metallic edge that a straight noise roll lacks (DR-S01). The two lanes are the same chip channel, so the arranger must write them as alternating hits, not doubles."),
    fill("FLR-06", "Roll with a gap before the downbeat", "noise_roll", 2, 8, LOUD,
         ["phrase_end_16", "before_section_change"],
         [L(SNARE, [(0, 4), (1, 5), (2, 6), (3, 7), (4, 8), (5, 9)], rate=13),
          L(KICK, [(0, 8)], rate=11)],
         "The roll stops on the third beat, so the last two steps are silence and the next downbeat lands on nothing. A gap is a fill too."),
    fill("FLR-07", "Roll that speeds up (eighths into sixteenths)", "noise_roll", 2, 8, LOUD,
         ["phrase_end_8", "phrase_end_16"],
         [L(SNARE, [(0, 5), (2, 5), (4, 6), (5, 6), (6, 8), (7, 9)], rate=13)],
         "Eighth, eighth, then sixteenths. The ear hears acceleration even though the grid never changes."),
    fill("FLR-08", "Snare roll with a tom landing", "noise_roll", 2, 8, LOUD,
         ["before_section_change", "phrase_end_16"],
         [L(SNARE, [(0, 4), (1, 5), (2, 6), (3, 7), (4, 8)], rate=13),
          L(HAT, [(5, 7), (6, 8), (7, 9)], period=[(5, 6), (6, 9), (7, 12)])],
         "The roll hands over to two toms that drop in pitch, which is the fill a section change wants when the new section starts low."),

    # --- tom style pitch drops --------------------------------------------
    fill("FLT-01", "One beat tom drop, four hits", "tom_sweep", 1, 4, LOUD,
         ["phrase_end_4", "before_section_change"],
         [L(HAT, [(0, 6), (1, 7), (2, 8), (3, 9)], period=[(0, 6), (1, 8), (2, 10), (3, 12)])],
         "Period climbs 6, 8, 10, 12, so the pitch falls. The noise period is the only pitch control on the channel, and a four step sweep is one beat at most tempos."),
    fill("FLT-02", "Two beat tom drop, six hits then a kick", "tom_sweep", 2, 8, LOUD,
         ["phrase_end_8", "before_section_change"],
         [L(HAT, [(0, 6), (1, 7), (2, 7), (3, 8), (4, 8), (5, 9)], period=[(0, 5), (1, 7), (2, 8), (3, 10), (4, 11), (5, 13)]),
          L(KICK, [(6, 9), (7, 8)], rate=11)],
         "Six toms falling into two kicks. This is the standard fill before a chorus or a boss phase."),
    fill("FLT-03", "One beat tom rise", "tom_sweep", 1, 4, ("boss", "battle", "metal"),
         ["phrase_end_4"],
         [L(HAT, [(0, 8), (1, 8), (2, 7), (3, 7)], period=[(0, 12), (1, 10), (2, 8), (3, 6)])],
         "The same sweep upwards. Rising toms sound like a question, falling toms sound like an answer; pick by what the next bar does."),
    fill("FLT-04", "Two beat tom cascade, sixteen notes", "tom_sweep", 2, 8, ("metal", "battle", "boss"),
         ["phrase_end_16", "before_section_change"],
         [L(HAT, [(s, 5 + (s % 3)) for s in range(8)],
            period=[(0, 4), (1, 6), (2, 7), (3, 9), (4, 10), (5, 11), (6, 12), (7, 14)]),
          L(SNARE, [(0, 4)], rate=13)],
         "One continuous fall across two beats. The uneven levels (5, 6, 7 repeating) stop it sounding like a scale."),
    fill("FLT-05", "One beat kick and tom alternation", "tom_sweep", 1, 4, LOUD,
         ["phrase_end_4", "before_section_change"],
         [L(KICK, [(0, 9), (2, 8)], rate=11),
          L(HAT, [(1, 6), (3, 8)], period=[(1, 7), (3, 11)])],
         "Kick, tom, kick, lower tom. Alternating the DMC and the noise channel is how the chip imitates a five piece kit with two channels."),
    fill("FLT-06", "Two beat timpani style drop with roll", "tom_sweep", 2, 8, ("baroque", "boss", "calm"),
         ["phrase_end_8", "phrase_end_16"],
         [L(KICK, [(0, 8), (2, 7), (4, 7), (6, 8)], rate=[(0, 9), (2, 10), (4, 11), (6, 12)]),
          L(HAT, [(0, 3), (4, 3)], period=13)],
         "Four strokes with the DMC rate falling, which is a timpani drop rather than a drum set fill. Rate is the DMC's pitch control, so a rate sweep is the sample's bend."),
    fill("FLT-07", "One beat tom triplet gesture", "tom_sweep", 1, 4, LOUD,
         ["phrase_end_4"],
         [L(HAT, [(0, 8), (1, 5), (2, 5)], period=[(0, 8), (1, 9), (2, 11)]),
          L(SNARE, [(3, 8)], rate=13)],
         "Three toms then a snare. On a sixteenth grid the triplet is a gesture rather than a true triplet, which is enough at any tempo above 100."),
    fill("FLT-08", "Two beat tom sweep into a crash", "tom_sweep", 2, 8, LOUD,
         ["before_section_change", "phrase_end_16"],
         [L(HAT, [(0, 6), (1, 6), (2, 7), (3, 8)], period=[(0, 6), (1, 8), (2, 10), (3, 12)]),
          L(HAT, [(4, 7)], period=14),
          L(KICK, [(4, 9)], rate=11)],
         "Four toms, then one very low noise hit at period 14 over a kick. The period 14 hit is the crash, and it needs a long note to decay."),

    # --- DPCM snare flams -------------------------------------------------
    fill("FLF-01", "One beat closing flam", "snare_flam", 1, 4, ALL4,
         ["phrase_end_4", "before_section_change"],
         [L(SNARE, [(2, 4), (3, 9)], rate=13),
          L(KICK, [(3, 8)], rate=11)],
         "Two hits one step apart, soft then loud, with a kick under the loud one. The cheapest fill that still reads as a fill."),
    fill("FLF-02", "One beat flam cascade", "snare_flam", 1, 4, LOUD,
         ["phrase_end_4", "phrase_end_8"],
         [L(SNARE, [(0, 5), (1, 8), (2, 5), (3, 9)], rate=13)],
         "Two flams in a beat. The soft hit before each loud one is what makes a drum sound struck twice by a wrist rather than once by a machine."),
    fill("FLF-03", "Two beat flams with ghosts", "snare_flam", 2, 8, LOUD,
         ["phrase_end_8", "phrase_end_16"],
         [L(SNARE, [(0, 5), (1, 8), (3, 3), (4, 5), (5, 9), (7, 3)], rate=13),
          L(KICK, [(0, 8), (4, 7)], rate=11)],
         "Flam, ghost, flam, ghost. The ghosts are level 3 and they are what stop the fill from sounding like a metronome."),
    fill("FLF-04", "Two beat flam into silence", "snare_flam", 2, 8, ("boss", "rock", "metal"),
         ["before_section_change"],
         [L(SNARE, [(0, 6), (1, 9), (4, 5), (5, 8)], rate=13),
          L(KICK, [(0, 8)], rate=11)],
         "Two flams and then two beats of nothing. Silence before a new section is stronger than a louder fill."),
    fill("FLF-05", "One beat flam on the downbeat", "snare_flam", 1, 4, ALL4,
         ["before_section_change", "phrase_end_4"],
         [L(SNARE, [(0, 3), (1, 9)], rate=13),
          L(KICK, [(1, 9)], rate=11),
          L(HAT, [(1, 5)], period=13)],
         "A flam plus a low noise wash on the beat where the new section starts. The wash is what makes the flam sound large."),
    fill("FLF-06", "Two beat flam and roll", "snare_flam", 2, 8, LOUD,
         ["phrase_end_8", "phrase_end_16", "before_section_change"],
         [L(SNARE, [(0, 3), (1, 9), (4, 4), (5, 5), (6, 7), (7, 9)], rate=13)],
         "Flam to open the fill, crescendo roll to close it. This covers both jobs in the file with one gesture."),
    fill("FLF-07", "One beat double flam", "snare_flam", 1, 4, ("march", "battle", "metal"),
         ["phrase_end_4"],
         [L(SNARE, [(0, 4), (1, 8), (2, 4), (3, 9)], rate=13),
          L(HAT, [(3, 5)], period=10)],
         "A marching double stroke, written as two flams. The low noise hit on the last step gives it weight without a second sample."),
    fill("FLF-08", "Two beat flam with tom answer", "snare_flam", 2, 8, LOUD,
         ["before_section_change", "phrase_end_16"],
         [L(SNARE, [(0, 5), (1, 9)], rate=13),
          L(HAT, [(3, 6), (4, 6), (5, 7)], period=[(3, 7), (4, 10), (5, 13)]),
          L(KICK, [(5, 8)], rate=11)],
         "Flam, gap, three falling toms into a kick. Use when the next section starts with a big harmony change."),

    # --- cymbal style long decay -----------------------------------------
    fill("FLC-01", "One beat crash with long decay", "cymbal_decay", 1, 4, LOUD,
         ["before_section_change", "phrase_end_16"],
         [L(HAT, [(0, 8)], period=14)],
         "One hit, low period, long note. A period of 14 gives the 2034 cycle rate, about 880 Hz of random clocking, which is the chip's rumble rather than its hiss (DR-S01). The decay is the note length, so hold it for a beat or more."),
    fill("FLC-02", "Two beat crash swell", "cymbal_decay", 2, 8, LOUD,
         ["before_section_change", "phrase_end_16"],
         [L(HAT, [(0, 5), (2, 6), (4, 7), (6, 8)],
            period=[(0, 13), (2, 13), (4, 14), (6, 14)])],
         "Four long hits getting louder and darker. A ride wash written with one channel and no samples."),
    fill("FLC-03", "One beat metallic crash (short mode)", "cymbal_decay", 1, 4, ("metal", "boss", "battle"),
         ["before_section_change"],
         [L(HAT, [(0, 8)], period=3, loop="short"),
          L(KICK, [(0, 9)], rate=11)],
         "Short mode on a low period gives the metallic ring rather than a hiss, which is the closest the 2A03 gets to a china cymbal (DR-S01)."),
    fill("FLC-04", "Two beat cymbal choke", "cymbal_decay", 2, 8, ("rock", "metal", "battle"),
         ["phrase_end_8"],
         [L(HAT, [(0, 8)], period=12),
          L(HAT, [(4, 6)], period=0)],
         "A long hit at period 12 followed by a short bright hit at period 0, which reads as the cymbal being grabbed. The second hit must be short or the choke does not read."),
    fill("FLC-05", "One beat crash into the downbeat", "cymbal_decay", 1, 4, LOUD,
         ["before_section_change", "phrase_end_4"],
         [L(HAT, [(3, 9)], period=15),
          L(KICK, [(3, 9)], rate=11),
          L(SNARE, [(3, 5)], rate=13)],
         "Everything hits together one step before the new section, with the longest decay the chip has. The new section's downbeat then lands in the tail."),
    fill("FLC-06", "Two beat cymbal and tom combination", "cymbal_decay", 2, 8, ("boss", "baroque", "battle"),
         ["phrase_end_16", "before_section_change"],
         [L(HAT, [(0, 7)], period=14),
          L(HAT, [(2, 6), (4, 7), (6, 8)], period=[(2, 9), (4, 11), (6, 13)])],
         "One long crash under three falling toms. Fills the two beats and still leaves the low end to the kick that follows."),

    # --- mixed and situational -------------------------------------------
    fill("FLX-01", "One beat kick and snare exchange", "mixed", 1, 4, ALL4,
         ["phrase_end_4"],
         [L(KICK, [(0, 9), (2, 7)], rate=11),
          L(SNARE, [(1, 6), (3, 8)], rate=13)],
         "Alternating kick and snare. Every drum in the kit speaks once, which is what makes a one beat fill feel finished."),
    fill("FLX-02", "Two beat rock fill with open hat", "mixed", 2, 8, ("rock", "metal"),
         ["phrase_end_8", "before_section_change"],
         [L(KICK, [(0, 9), (4, 8)], rate=11),
          L(SNARE, [(2, 8), (6, 9)], rate=13),
          L(HAT, [(6, 5)], period=11)],
         "Kick, snare, kick, snare, with a long hat at the end. The open hat needs the following bar to start clean, so do not use it at a loop point."),
    fill("FLX-03", "One beat waltz fill (4 steps in 3/4)", "mixed", 1, 4, ("waltz", "baroque", "calm"),
         ["phrase_end_4", "before_section_change"],
         [L(KICK, [(0, 9)], rate=11),
          L(SNARE, [(1, 4), (2, 5), (3, 7)], rate=13)],
         "One kick and three snare hits inside the last beat of a 3/4 bar. At 100 bpm a four step fill is 150 ms per hit, which is fast but playable."),
    fill("FLX-04", "Two beat waltz fill (8 steps in 3/4)", "mixed", 2, 8, ("waltz", "baroque", "boss"),
         ["phrase_end_8", "phrase_end_16"],
         [L(KICK, [(0, 8), (4, 7)], rate=11),
          L(SNARE, [(1, 4), (2, 5), (3, 6), (5, 6), (6, 7), (7, 8)], rate=13)],
         "The last two beats of a waltz phrase filled. Because a 3/4 bar is twelve steps, eight steps is two beats and it will cross a bar line if the arranger is careless: place it on beats 2 and 3 only."),
    fill("FLX-05", "Two beat march rudiment fill", "mixed", 2, 8, ("march", "battle"),
         ["phrase_end_8", "before_section_change"],
         [L(SNARE, [(0, 5), (1, 4), (2, 6), (3, 4), (4, 7), (5, 5), (6, 8), (7, 6)], rate=13),
          L(KICK, [(0, 8), (4, 7)], rate=11)],
         "An uneven rudimental figure with the accents on 1 and the offbeat of 2. Marching snare fills are deliberately not even."),
    fill("FLX-06", "Two beat battle crescendo fill", "mixed", 2, 8, ("battle", "metal", "boss"),
         ["phrase_end_8", "phrase_end_16", "before_section_change"],
         [L(KICK, [(0, 9), (4, 8)], rate=11),
          L(SNARE, [(2, 4), (3, 5), (4, 6), (5, 7), (6, 8), (7, 9)], rate=13),
          L(HAT, [(7, 6)], period=14)],
         "Groove for a beat, then crescendo into the loudest hit in the library. Use once per loop at most."),
    fill("FLX-07", "One beat drop out fill (silence)", "mixed", 1, 4, ALL4,
         ["phrase_end_4", "before_section_change"],
         [L(KICK, [(0, 4)], rate=11)],
         "A single soft kick and three steps of nothing. The ladder's drop out rung applied to a fill: the absence is the gesture."),
    fill("FLX-08", "Two beat boss fill with a low hit", "mixed", 2, 8, ("boss", "metal"),
         ["before_section_change", "phrase_end_16"],
         [L(KICK, [(0, 9)], rate=10),
          L(SNARE, [(2, 7), (4, 6), (5, 7)], rate=13),
          L(HAT, [(7, 9)], period=15)],
         "Ends on the deepest noise period there is. The period 15 hit is about a 4.7 Hz repeat, which reads as a sub thump rather than a cymbal."),
    fill("FLX-09", "One beat unison hit and stop", "mixed", 1, 4, ALL4,
         ["before_section_change"],
         [L(KICK, [(3, 9)], rate=11),
          L(SNARE, [(3, 8)], rate=13),
          L(HAT, [(3, 6)], period=12)],
         "All three channels hit once on the last step. The chip's biggest single moment, and it costs three bytes of state."),
    fill("FLX-10", "Two beat loop point turnaround", "mixed", 2, 8, ALL4,
         ["phrase_end_16"],
         [L(KICK, [(0, 9), (6, 8)], rate=11),
          L(SNARE, [(2, 7), (4, 6), (7, 5)], rate=13),
          L(HAT, [(0, 4), (3, 4)], period=3)],
         "Written for the two beats before a loop point: it ends soft, so the loop start is louder than the fill and the seam does not click. A loud fill at a loop point is what makes old game music sound like it stutters."),
]
