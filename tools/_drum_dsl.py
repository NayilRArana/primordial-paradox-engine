"""_drum_dsl.py: authoring shorthand for the drum pattern library.

The patterns in this project are written by hand as compact grids and expanded
into the verbose per step form that data/drum_patterns.json carries. Keeping the
authoring form compact is the only way 120 patterns stay readable and stay
reviewable; keeping the output form explicit is the only way the arranger can
read one step at a time without a decoder.

Grid convention: a hit is (step, level) where level is 0 to 9. Level 0 would be
a rest, so levels are 1 to 9 and map to an even velocity ramp in the expander
(9 = 127). A level of 8 or 9 is an accent. A step may hold two hits on different
instruments (a DPCM kick under a noise hat), which the chip can do because the
noise channel and the DMC are separate.

Period convention for noise: period is either one integer 0 to 15 (constant for
every hit of the lane) or a list of (step, period) covering every hit of the
lane, which is how a tom sweep or a cymbal decay is written. Loop mode is
"long" (15 bit, white, the default) or "short" (the 93 step metallic buzz),
given as one string or per hit.
"""

from __future__ import annotations

FEELS = ("waltz", "march", "rock", "metal", "baroque", "boss", "calm", "battle")
METERS = {"4/4": 16, "3/4": 12, "6/8": 6}  # steps per bar at the meter's grid
SUBDIVISION = {"4/4": "16th", "3/4": "16th", "6/8": "8th"}

LEVEL_VELOCITY = {1: 14, 2: 28, 3: 42, 4: 57, 5: 71, 6: 85, 7: 99, 8: 113, 9: 127}
ACCENT_FLOOR = 113


class Lane:
    def __init__(self, inst, hits, period=None, loop="long", rate=None, note=""):
        self.inst = inst
        self.hits = list(hits)
        self.period = period
        self.loop = loop
        self.rate = rate
        self.note = note


def L(inst, hits, period=None, loop="long", rate=None, note=""):
    return Lane(inst, hits, period, loop, rate, note)


class Pattern:
    def __init__(self, pid, name, feel, meter, tempo, bars, lanes, devices=(),
                 tags=(), note=""):
        self.id = pid
        self.name = name
        self.feel = feel
        self.meter = meter
        self.tempo = tempo
        self.bars = bars
        self.lanes = lanes
        self.devices = list(devices)
        self.tags = list(tags)
        self.note = note

    @property
    def steps(self):
        return METERS[self.meter] * self.bars


def pat(pid, name, feel, meter, tempo, bars, lanes, devices=(), tags=(), note=""):
    return Pattern(pid, name, feel, meter, tempo, bars, lanes, devices, tags, note)


def expand_step_hits(p: Pattern):
    """Expand a pattern into steps: a list of lists of hit dicts."""
    steps = p.steps
    grid = [[] for _ in range(steps)]
    for lane in p.lanes:
        if not lane.hits:
            continue
        # Noise lanes need a period; DPCM lanes need a playback rate index.
        period_map = {}
        loop_map = {}
        rate_map = {}
        if lane.inst == "noise":
            if lane.period is None:
                raise ValueError("%s: noise lane without a period" % p.id)
            if isinstance(lane.period, int):
                period_map = {s: lane.period for s, _ in lane.hits}
            else:
                period_map = dict(lane.period)
            if isinstance(lane.loop, str):
                loop_map = {s: lane.loop for s, _ in lane.hits}
            else:
                loop_map = dict(lane.loop)
        if lane.inst.startswith("dpcm"):
            if lane.rate is None:
                raise ValueError("%s: dpcm lane without a rate" % p.id)
            if isinstance(lane.rate, int):
                rate_map = {s: lane.rate for s, _ in lane.hits}
            else:
                rate_map = dict(lane.rate)
        for step, level in lane.hits:
            if not 0 <= step < steps:
                raise ValueError("%s: %s hit at step %d outside %d steps" % (p.id, lane.inst, step, steps))
            if not 1 <= level <= 9:
                raise ValueError("%s: %s level %r outside 1..9" % (p.id, lane.inst, level))
            velocity = LEVEL_VELOCITY[level]
            hit = {
                "instrument": lane.inst,
                "velocity": velocity,
                "accent": velocity >= ACCENT_FLOOR,
            }
            if lane.inst == "noise":
                if step not in period_map:
                    raise ValueError("%s: noise hit at step %d has no period" % (p.id, step))
                period = period_map[step]
                if not isinstance(period, int) or not 0 <= period <= 15:
                    raise ValueError("%s: noise period %r at step %d outside 0..15" % (p.id, period, step))
                hit["period"] = period
                mode = loop_map.get(step, "long")
                if mode not in ("long", "short"):
                    raise ValueError("%s: loop mode %r at step %d" % (p.id, mode, step))
                hit["loop"] = mode
            elif lane.inst.startswith("dpcm"):
                rate = rate_map.get(step)
                if not isinstance(rate, int) or not 0 <= rate <= 15:
                    raise ValueError("%s: dpcm rate %r at step %d outside 0..15" % (p.id, rate, step))
                hit["rate"] = rate
            grid[step].append(hit)
    for step_hits in grid:
        step_hits.sort(key=lambda h: (h["instrument"], -h["velocity"]))
    return grid


def expand_pattern(p: Pattern, sources=()):
    channels = sorted({lane.inst for lane in p.lanes if lane.hits})
    tempo = p.tempo
    if isinstance(tempo, int):
        tempo = (tempo, tempo)
    tmin, tmax = tempo
    return {
        "id": p.id,
        "name": p.name,
        "feel": p.feel,
        "meter": p.meter,
        "bars": p.bars,
        "subdivision": SUBDIVISION[p.meter],
        "steps_count": p.steps,
        "tempo": {"min": tmin, "max": tmax, "default": int(round((tmin + tmax) / 2))},
        "channels": channels,
        "devices": p.devices,
        "tags": p.tags,
        "note": p.note,
        "sources": list(sources),
        "steps": expand_step_hits(p),
    }
