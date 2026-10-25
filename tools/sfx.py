"""NES 2A03 style sound effects for Primordial Paradox, synthesised from scratch.

Why this file exists
--------------------
The game needs a small, consistent set of menu, text, battle, magic and world
sounds before any of it can be wired into GML. There is no sample library in
this project and there never will be: the plan's ground rule is that every
sound is original. So each effect here is built from the four voices the real
chip has (two pulses, a triangle and a noise channel), with the pulse duties
12.5, 25 and 50 percent, the APU 15 bit LFSR in both its short (93 cycle) and
long (4 to 4068 cycle) modes, per effect envelopes and per effect pitch
sweeps. Nothing is loaded from disk and nothing is sampled.

How it relates to the music renderer
------------------------------------
The noise generator is not reimplemented. ``render_chip.lfsr_cycle`` and
``render_chip.NOISE_PERIODS`` are the project's one copy of the APU noise
hardware, so a sound effect and the title theme never disagree about what the
chip does. The pulse and triangle here are vectorised with a phase accumulator
because a sound effect sweeps its pitch every sample, which the MIDI renderer
never has to do.

Outputs, all deterministic (same bytes on every run)
---------------------------------------------------
  assets\\audio\\sfx\\<name>.wav    44100 Hz, mono, 16 bit PCM
  assets\\audio\\sfx\\<name>.ogg    Vorbis, quality 5, via ffmpeg
  assets\\audio\\sfx\\manifest.json  name, length, peak, voices, purpose
  output\\sfx_preview_3x.png       contact sheet of every waveform at 3x

Every one shot effect is normalised to a peak of -3 dBFS and gets a 5 ms raised
cosine fade at each end, so no file starts or ends on a step. A 20 Hz one pole
high pass (the APU's output capacitor, in effect) removes the DC bias that a
short burst of low noise otherwise carries.

`car_engine_loop` is the one file that loops (the drive holds it from shot 2 to
shot 12 of knowledge/DRIVE-SHOT-LIST.md), so it is built as a genuine loop
instead: every voice in it is periodic in the file length, it carries no fade,
and the high pass is primed with the file's own tail so the filter is already in
steady state at sample 0. A fade at the seam would duck the loop once per lap,
which is the click spec 12 rule 3 exists to avoid. Its OGG also carries
LOOPSTART and LOOPLENGTH, because rule 3 says loop points come from the file.

Usage:
    python tools\\sfx.py               build everything under the project root
    python tools\\sfx.py --out DIR     build into another folder (tests do this)
    python tools\\sfx.py --no-ogg      waveforms only, for a fast run
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from typing import Callable

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import render_chip  # noqa: E402  (the project's one copy of the APU noise hardware)

ROOT = os.path.dirname(_HERE)
OUT_REL = os.path.join("assets", "audio", "sfx")
PREVIEW_DIR_REL = "output"
PREVIEW_NAME = "sfx_preview_3x.png"
PREVIEW_SCALE = 3

SR = 44100
FADE_MS = 5.0
PEAK_DBFS = -3.0
PEAK = 10.0 ** (PEAK_DBFS / 20.0)
BIT_DEPTH = 16
LIMITER_KNEE = 0.95
# The one pole DC blocker corner, in Hz. Below the lowest thing the chip can play
# (the triangle bottoms out around 27 Hz) so it removes bias, not notes.
DC_BLOCK_HZ = 20.0

# The effects that loop instead of firing once. A loop must not be faded, because the
# fade is at both ends of the file and the file is played round and round: the seam
# would duck every lap. So the high pass is primed with the loop's own tail instead,
# which leaves the filter in the steady state a repeat would have given it.
LOOPING = {"car_engine_loop"}
LOOP_WARMUP_S = 0.10

# APU noise periods, in CPU cycles, from the hardware table.
NOISE_PERIODS = render_chip.NOISE_PERIODS
# The short mode taps bit 6, which gives a 93 cycle period.
SHORT_PERIOD = 93.0
CPU_HZ = 1789772.5

DUTY_12 = 0.125
DUTY_25 = 0.25
DUTY_50 = 0.5


# --------------------------------------------------------------- oscillators


def hz(midi: float) -> float:
    """Equal tempered frequency of a MIDI note number."""
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def _count(duration: float) -> int:
    return max(1, int(round(duration * SR)))


def _times(duration: float) -> np.ndarray:
    return np.arange(_count(duration), dtype=np.float64) / SR


def _freqs(duration: float, f0: float, f1: float, curve: str = "exp") -> np.ndarray:
    """Per sample frequency from f0 to f1. Exponential by default, which is
    what a pitch sweep by ear is; linear is offered for a noise whoosh."""
    n = _count(duration)
    if f0 == f1 or n == 1:
        return np.full(n, float(f0))
    x = np.linspace(0.0, 1.0, n)
    if curve == "lin":
        return f0 + (f1 - f0) * x
    return f0 * (f1 / float(f0)) ** x


def pulse(freqs: np.ndarray, duty: float) -> np.ndarray:
    """A 2A03 pulse, DC centred so it does not bias the mix."""
    phase = np.cumsum(np.broadcast_to(freqs, freqs.shape)) / SR
    return (phase % 1.0 < duty).astype(np.float64) - float(duty)


def triangle(freqs: np.ndarray) -> np.ndarray:
    """The 16 step 2A03 triangle: 32 samples per period, quantised steps."""
    phase = np.cumsum(np.broadcast_to(freqs, freqs.shape)) / SR
    step = (phase * 32.0) % 32.0
    return 2.0 * np.abs(step - 16.0) / 16.0 - 1.0


def noise(duration: float, period0: float, period1: float, short: bool,
          curve: str = "exp") -> np.ndarray:
    """APU noise with a swept period, in CPU cycles.

    The short mode is the 93 cycle LFSR (a metallic buzz); the long mode runs
    from 4 cycles (bright hiss) to 4068 (a low rumble).
    """
    n = _count(duration)
    if short:
        periods = _freqs(duration, period0 if period0 else SHORT_PERIOD,
                         period1 if period1 else SHORT_PERIOD, curve)
        periods = np.maximum(periods, 4.0)
    else:
        periods = _freqs(duration, period0, period1, curve)
        periods = np.clip(periods, 4.0, 4068.0)
    clock_rate = CPU_HZ / periods
    clocks = np.cumsum(clock_rate / SR).astype(np.int64)
    bits = render_chip.lfsr_cycle(short)
    return bits[clocks % 32767].astype(np.float64) * 2.0 - 1.0


# ------------------------------------------------------------------ envelopes


def _envelope(duration: float, tau: float, attack_ms: float = 2.0,
              release_ms: float = 4.0) -> np.ndarray:
    """Attack ramp, exponential decay, short release, all per sample.

    The release matters: effects lay notes end to end, and a note that stops on
    a non zero sample is a click.
    """
    n = _count(duration)
    t = np.arange(n, dtype=np.float64) / SR
    attack = min(n, max(1, int(round(attack_ms * SR / 1000.0))))
    env = np.exp(-t / max(tau, 1e-4))
    ramp = np.linspace(0.0, 1.0, attack)
    env[:attack] *= ramp
    release = min(n, max(1, int(round(release_ms * SR / 1000.0))))
    if release > 1:
        env[-release:] *= np.linspace(1.0, 0.0, release)
    return env


def _mix_at(target: np.ndarray, start: float, piece: np.ndarray, gain: float = 1.0) -> None:
    i = int(round(start * SR))
    if i >= target.size:
        return
    end = min(target.size, i + piece.size)
    target[i:end] += gain * piece[: end - i]


def _notes(total: float, voice: str, notes: list[tuple], duty: float | None = None,
           gain: float = 1.0, curve: str = "exp", attack_ms: float = 2.0) -> np.ndarray:
    """Render a sequence of notes into one buffer.

    A note is (start_seconds, length_seconds, f_start, f_end, tau). For the
    noise voices f_start and f_end are periods in CPU cycles instead of Hz.
    """
    out = np.zeros(_count(total), dtype=np.float64)
    for start, length, f0, f1, tau in notes:
        if voice.startswith("noise"):
            length = min(length, total - start)
            if length <= 0:
                continue
            wave = noise(length, f0, f1, short=(voice == "noise_short"), curve=curve)
        else:
            duty = 0.5 if duty is None else duty
            wave = pulse(_freqs(length, f0, f1, curve), duty) if voice.startswith("pulse") \
                else triangle(_freqs(length, f0, f1, curve))
        _mix_at(out, start, wave * _envelope(length, tau, attack_ms), gain)
    return out


def _duty_name(duty: float) -> str:
    """Name a pulse voice the way the manifest lists it: pulse_12.5, pulse_25, pulse_50."""
    return "pulse_%g" % round(duty * 100.0, 3)


def _fanfare(total: float, notes: list[tuple], duty_lead: float, duty_harmony: float,
             harmony: float = 4.0, bass: list[tuple] | None = None) -> tuple[np.ndarray, list[str]]:
    """A lead pulse, a parallel harmony a few semitones below, and a triangle bass."""
    lead = _notes(total, "pulse", [(s, l, hz(m), hz(m2), tau) for s, l, m, m2, tau in notes],
                  duty=duty_lead, gain=1.0)
    harm = _notes(total, "pulse", [(s, l, hz(m - harmony), hz(m2 - harmony), tau)
                                   for s, l, m, m2, tau in notes],
                  duty=duty_harmony, gain=0.45)
    out = lead + harm
    voices = [_duty_name(duty_lead), _duty_name(duty_harmony)]
    if bass:
        out = out + _notes(total, "triangle",
                           [(s, l, hz(m), hz(m2), tau) for s, l, m, m2, tau in bass],
                           gain=0.7)
        voices.append("triangle")
    return out, voices


# -------------------------------------------------------------------- effects
#
# Each builder returns (audio, voices, purpose). Names and purposes are the
# strings the game code will look up, so they stay stable.


def build_menu_move() -> tuple[np.ndarray, list[str], str]:
    dur = 0.06
    audio = _notes(dur, "pulse", [(0.0, dur, hz(84), hz(84), 0.018)], duty=DUTY_12)
    return audio, ["pulse_12.5"], "Cursor moves one row in a menu. A tick, not a tune."


def build_menu_select() -> tuple[np.ndarray, list[str], str]:
    dur = 0.16
    audio = _notes(dur, "pulse", [(0.0, 0.07, hz(76), hz(76), 0.045),
                                  (0.07, 0.09, hz(88), hz(88), 0.05)], duty=DUTY_25, gain=0.9)
    return audio, ["pulse_25"], "Confirm in a menu: two steps up, second one longer."


def build_menu_cancel() -> tuple[np.ndarray, list[str], str]:
    dur = 0.18
    audio = _notes(dur, "pulse", [(0.0, dur, hz(79), hz(55), 0.11)], duty=DUTY_50)
    return audio, ["pulse_50"], "Cancel or back out of a menu: a falling square blip."


def _text_blip(midi: int) -> np.ndarray:
    dur = 0.06
    return _notes(dur, "pulse", [(0.0, dur, hz(midi), hz(midi), 0.02)], duty=DUTY_12)


def build_text_blip_a() -> tuple[np.ndarray, list[str], str]:
    return _text_blip(72), ["pulse_12.5"], "Typewriter blip for speaker A (Konrad), C5."


def build_text_blip_b() -> tuple[np.ndarray, list[str], str]:
    return _text_blip(76), ["pulse_12.5"], "Typewriter blip for speaker B (Zander), E5."


def build_text_blip_c() -> tuple[np.ndarray, list[str], str]:
    return _text_blip(79), ["pulse_12.5"], "Typewriter blip for speaker C (Percy), G5."


def build_footstep() -> tuple[np.ndarray, list[str], str]:
    dur = 0.09
    grit = noise(dur, 900.0, 380.0, short=True) * _envelope(dur, 0.028)
    thud = triangle(_freqs(dur, hz(38), hz(36))) * _envelope(dur, 0.03)
    audio = 0.8 * grit + 0.7 * thud
    return audio, ["noise_short", "triangle"], "One step on stone decking; alternates with the other foot."


def build_door_hatch() -> tuple[np.ndarray, list[str], str]:
    dur = 0.30
    scrape = noise(dur, 1400.0, 260.0, short=False, curve="lin") * _envelope(dur, 0.10)
    clunk = _notes(dur, "pulse", [(0.0, 0.10, hz(45), hz(36), 0.05)], duty=DUTY_25, gain=0.8)
    audio = 0.9 * scrape + clunk
    return audio, ["noise_long", "pulse_25"], "A bulkhead hatch swings open and clunks."


def build_item_get() -> tuple[np.ndarray, list[str], str]:
    dur = 0.32
    arp = [(0.00, 0.08, hz(72), hz(72), 0.05),
           (0.08, 0.08, hz(76), hz(76), 0.05),
           (0.16, 0.08, hz(79), hz(79), 0.05),
           (0.24, 0.08, hz(84), hz(84), 0.06)]
    audio = _notes(dur, "pulse", arp, duty=DUTY_25) + \
        _notes(dur, "triangle", [(0.0, dur, hz(48), hz(48), 0.30)], gain=0.5)
    return audio, ["pulse_25", "triangle"], "Pickup collected: a four note rising arpeggio."


def build_heal() -> tuple[np.ndarray, list[str], str]:
    dur = 0.52
    steps = [72, 76, 79, 84]
    arp = [(i * 0.11, 0.12, hz(m), hz(m), 0.09) for i, m in enumerate(steps)]
    shimmer = [(i * 0.11 + 0.03, 0.10, hz(m + 12), hz(m + 12), 0.06) for i, m in enumerate(steps)]
    audio = _notes(dur, "pulse", arp, duty=DUTY_25) + \
        _notes(dur, "pulse", shimmer, duty=DUTY_12, gain=0.4) + \
        _notes(dur, "triangle", [(0.0, dur, hz(48), hz(48), 0.5)], gain=0.4)
    return audio, ["pulse_25", "pulse_12.5", "triangle"], "Restorative magic: a rising shimmer with a held root."


def build_hit_light() -> tuple[np.ndarray, list[str], str]:
    dur = 0.12
    crack = noise(dur, 260.0, 1100.0, short=True) * _envelope(dur, 0.035)
    body = _notes(dur, "pulse", [(0.0, 0.07, hz(52), hz(40), 0.035)], duty=DUTY_50, gain=0.7)
    return 0.85 * crack + body, ["noise_short", "pulse_50"], "A light physical hit that does not kill."


def build_hit_heavy() -> tuple[np.ndarray, list[str], str]:
    dur = 0.34
    boom = noise(dur, 800.0, 140.0, short=False) * _envelope(dur, 0.14)
    sub = triangle(_freqs(dur, hz(33), hz(31))) * _envelope(dur, 0.12)
    snap = _notes(dur, "pulse", [(0.0, 0.10, hz(55), hz(36), 0.04)], duty=DUTY_25, gain=0.6)
    return 0.9 * boom + 0.6 * sub + snap, ["noise_long", "triangle", "pulse_25"], \
        "A heavy blow: long noise body, sub thump, short snap on top."


def build_miss() -> tuple[np.ndarray, list[str], str]:
    dur = 0.20
    air = noise(dur, 1500.0, 520.0, short=False, curve="lin") * _envelope(dur, 0.07)
    return 0.7 * air, ["noise_long"], "An attack that misses: air only, no impact, quieter than a hit."


def build_crit() -> tuple[np.ndarray, list[str], str]:
    dur = 0.42
    blast = noise(dur, 1400.0, 170.0, short=False) * _envelope(dur, 0.16)
    sub = triangle(_freqs(dur, hz(36), hz(30))) * _envelope(dur, 0.14)
    ring = _notes(dur, "pulse", [(0.0, 0.16, hz(76), hz(55), 0.06),
                                 (0.16, 0.26, hz(55), hz(43), 0.10)], duty=DUTY_50, gain=0.55)
    return 0.9 * blast + 0.55 * sub + ring, ["noise_long", "triangle", "pulse_50"], \
        "A critical hit: the heavy hit plus a two stage falling ring."


def build_level_up() -> tuple[np.ndarray, list[str], str]:
    dur = 1.20
    melody = [(0.00, 0.14, 67, 67, 0.13),
              (0.14, 0.14, 72, 72, 0.13),
              (0.28, 0.14, 76, 76, 0.13),
              (0.42, 0.28, 79, 79, 0.22),
              (0.70, 0.50, 84, 84, 0.40)]
    bass = [(0.00, 0.42, 48, 48, 0.42), (0.42, 0.28, 55, 55, 0.28),
            (0.70, 0.50, 48, 48, 0.50)]
    audio, voices = _fanfare(dur, melody, DUTY_25, DUTY_12, harmony=4.0, bass=bass)
    return audio, voices, "Level up: a short fanfare, five notes, third above and a bass root."


def build_encounter_swoosh() -> tuple[np.ndarray, list[str], str]:
    dur = 0.70
    sweep = noise(dur, 3200.0, 260.0, short=False) * _envelope(dur, 0.28, attack_ms=60.0)
    rise = _notes(dur, "pulse", [(0.05, 0.35, hz(45), hz(81), 0.30)],
                  duty=DUTY_12, gain=0.45, attack_ms=40.0)
    return 0.85 * sweep + rise, ["noise_long", "pulse_12.5"], \
        "Encounter transition: a noise sweep down with a rising pulse under it."


def build_thunder_soft() -> tuple[np.ndarray, list[str], str]:
    dur = 1.45
    roll = _freqs(dur, 1.0, 1.0)
    swell = np.exp(-_times(dur) / 0.55) * (0.75 + 0.25 * np.sin(2.0 * np.pi * 6.0 * _times(dur)))
    clap = noise(dur, 2200.0, 120.0, short=False) * swell * roll
    rumble = triangle(_freqs(dur, hz(29), hz(28))) * _envelope(dur, 0.7, attack_ms=120.0)
    return 0.9 * clap + 0.45 * rumble, ["noise_long", "triangle"], \
        "Distant thunder for a scene or the storm cloud: long decay, low rumble under it."


def build_wave_wash() -> tuple[np.ndarray, list[str], str]:
    dur = 1.10
    t = _times(dur)
    swell = np.exp(-((t - 0.35) ** 2) / (2.0 * 0.24 ** 2))
    wash = noise(dur, 1100.0, 240.0, short=False) * swell
    foam = noise(dur, 300.0, 900.0, short=True) * swell * 0.25
    return 0.95 * wash + foam, ["noise_long", "noise_short"], \
        "A wave breaking and draining: noise only, a swell then a fall."


def build_alarm() -> tuple[np.ndarray, list[str], str]:
    dur = 0.64
    seq = [(0.00, 0.14, 88, 88, 0.14), (0.16, 0.14, 84, 84, 0.14),
           (0.32, 0.14, 88, 88, 0.14), (0.48, 0.16, 84, 84, 0.16)]
    audio = _notes(dur, "pulse", [(s, l, hz(m), hz(m), tau) for s, l, m, m, tau in seq],
                   duty=DUTY_50, attack_ms=4.0)
    return audio, ["pulse_50"], "Ship alarm or a timed hazard: two tones alternating, square and hard."


def build_save_jingle() -> tuple[np.ndarray, list[str], str]:
    dur = 1.40
    melody = [(0.00, 0.16, 72, 72, 0.15),
              (0.16, 0.16, 76, 76, 0.15),
              (0.32, 0.16, 79, 79, 0.15),
              (0.48, 0.22, 84, 84, 0.20),
              (0.72, 0.66, 79, 79, 0.60)]
    bass = [(0.00, 0.48, 48, 48, 0.48), (0.48, 0.24, 55, 55, 0.24),
            (0.72, 0.66, 48, 48, 0.66)]
    audio, voices = _fanfare(dur, melody, DUTY_12, DUTY_25, harmony=3.0, bass=bass)
    return audio, voices, "Save confirmed: the level up fanfare's cousin, a third above instead of a fourth."


def build_game_over() -> tuple[np.ndarray, list[str], str]:
    dur = 1.40
    melody = [(0.00, 0.24, 69, 69, 0.24), (0.26, 0.24, 65, 65, 0.24),
              (0.52, 0.32, 62, 62, 0.32), (0.86, 0.52, 57, 57, 0.52)]
    bass = [(0.00, 1.40, 45, 45, 1.40)]
    audio = _notes(dur, "pulse", [(s, l, hz(m), hz(m), tau) for s, l, m, m, tau in melody],
                   duty=DUTY_25) + \
        _notes(dur, "pulse", [(s, l, hz(m - 5), hz(m - 5), tau) for s, l, m, m, tau in melody],
               duty=DUTY_12, gain=0.4) + \
        _notes(dur, "triangle", [(s, l, hz(m), hz(m), tau) for s, l, m, m, tau in bass], gain=0.6)
    return audio, ["pulse_25", "pulse_12.5", "triangle"], \
        "Death or a lost run: four notes down the minor scale, slow, with a held low root."


# The drive's bed, shot 2 to shot 12 of knowledge/DRIVE-SHOT-LIST.md: "engine from here to
# the end". It is the one effect that is a loop, so it is built as one.
#
# The film's engine is a four cylinder at idle: a firing at 60 Hz (900 rpm times four
# cylinders over two crank turns, near enough for a sound effect), a 30 Hz crank half order
# under it for the body, a 120 Hz second order for the block, and a short noise tick on each
# firing for the combustion. Everything is periodic in the buffer, so the loop has no seam to
# hide: the file is one 4410 sample pattern (three 0.1 s wobbles, six firings) repeated eight
# times, which is why tools/sfx.py can prove the repeat instead of fading it.
ENGINE_FIRING_HZ = 60.0
ENGINE_SUB_HZ = 30.0
ENGINE_SECOND_HZ = 120.0
ENGINE_WOBBLE_HZ = 10.0


def build_car_engine_loop() -> tuple[np.ndarray, list[str], str]:
    dur = 0.80
    n = _count(dur)
    firing = int(round(SR / ENGINE_FIRING_HZ))          # 735 samples, one firing
    block = firing * 2                                   # 1470: one whole 30 Hz cycle
    wobble_samples = int(round(SR / ENGINE_WOBBLE_HZ))   # 4410: three blocks, 8 in the file
    if n % block or n % wobble_samples:
        raise AssertionError("the engine loop length must divide into whole blocks")

    local = (np.arange(block) % firing) / float(SR)
    # Each firing opens with a 2.5 ms attack and is nearly gone 16.7 ms later, so the tick
    # lands on the next firing instead of smearing across it.
    chug = np.clip(local / 0.0025, 0.0, 1.0) * np.exp(-local / 0.0045)

    body = pulse(_freqs(block / float(SR), ENGINE_FIRING_HZ, ENGINE_FIRING_HZ), DUTY_25)
    second = pulse(_freqs(block / float(SR), ENGINE_SECOND_HZ, ENGINE_SECOND_HZ), DUTY_12)
    sub = triangle(_freqs(block / float(SR), ENGINE_SUB_HZ, ENGINE_SUB_HZ))
    grit = noise(block / float(SR), 2000.0, 1200.0, short=False) * chug

    # Measured share of the finished file's magnitude: 40 percent under 80 Hz, 13 percent
    # 80 to 200, 17 percent 200 Hz to 1 kHz, 19 percent 1 to 8 kHz. The triangle carries the
    # body because a 25 percent pulse at 60 Hz is mostly harmonics; the pulse is kept quiet
    # under it for the firing fundamental, and the noise is a slow LFSR clock so it reads as
    # combustion rather than hiss.
    one_block = (0.30 * body * (0.55 + 0.45 * chug)
                 + 0.20 * second * (0.35 + 0.65 * chug)
                 + 0.85 * sub
                 + 0.28 * grit)
    # A 10 Hz load wobble gives the idle some hunt without leaving the loop's period.
    wobble_one = 1.0 + 0.10 * np.sin(2.0 * np.pi * np.arange(wobble_samples) / float(wobble_samples))
    audio = np.tile(one_block, n // block) * np.tile(wobble_one, n // wobble_samples)
    return audio, ["pulse_25", "pulse_12.5", "triangle", "noise_long"], \
        "The drive's engine: a four cylinder at idle, 60 Hz firing, held under the whole film as a loop."


# The order is the order in the manifest and on the preview sheet. It follows
# the game: menus, then text, then the world, then battle, then magic, then
# jingles, then death. car_engine_loop is the last entry and the only loop.
EFFECTS: list[tuple[str, "Callable[[], tuple[np.ndarray, list[str], str]]", list[str]]] = [
    ("menu_move", build_menu_move, []),
    ("menu_select", build_menu_select, []),
    ("menu_cancel", build_menu_cancel, []),
    ("text_blip_a", build_text_blip_a, ["text_blip"]),
    ("text_blip_b", build_text_blip_b, ["text_blip"]),
    ("text_blip_c", build_text_blip_c, ["text_blip"]),
    ("footstep", build_footstep, []),
    ("door_hatch", build_door_hatch, []),
    ("item_get", build_item_get, []),
    ("heal", build_heal, []),
    ("hit_light", build_hit_light, []),
    ("hit_heavy", build_hit_heavy, []),
    ("miss", build_miss, []),
    ("crit", build_crit, []),
    ("level_up", build_level_up, []),
    ("encounter_swoosh", build_encounter_swoosh, []),
    ("thunder_soft", build_thunder_soft, []),
    ("wave_wash", build_wave_wash, []),
    ("alarm", build_alarm, []),
    ("save_jingle", build_save_jingle, []),
    ("game_over", build_game_over, []),
    ("car_engine_loop", build_car_engine_loop, []),
]

# The names a caller may ask for, including the grouped text_blip.
NAME_GROUPS = {"text_blip": ["text_blip_a", "text_blip_b", "text_blip_c"]}
REQUIRED_NAMES = [
    "menu_move", "menu_select", "menu_cancel", "text_blip", "footstep", "door_hatch",
    "item_get", "heal", "hit_light", "hit_heavy", "miss", "crit", "level_up",
    "encounter_swoosh", "thunder_soft", "wave_wash", "alarm", "save_jingle", "game_over",
]


# --------------------------------------------------------------------- master


def dc_block(signal: np.ndarray, cutoff_hz: float = DC_BLOCK_HZ) -> np.ndarray:
    """A one pole high pass at 20 Hz, which is what the APU's output capacitor does.

    Without it an effect that is a short burst of low pitch noise has a real DC
    offset (measured: miss sat at -0.137, footstep at -0.112, because a decaying
    burst spends more time above zero than below). A DC offset eats mixer
    headroom and thumps when a file is started, so it goes.
    """
    if signal.size == 0:
        return signal
    a = math.exp(-2.0 * math.pi * cutoff_hz / SR)
    out = np.empty_like(signal)
    previous_in = 0.0
    previous_out = 0.0
    for index in range(signal.size):
        value = signal[index]
        previous_out = value - previous_in + a * previous_out
        previous_in = value
        out[index] = previous_out
    return out


def finish(audio: np.ndarray, loop: bool = False) -> np.ndarray:
    """Remove DC, soft limit, fade both ends with a raised cosine, then set the peak.

    The order is deliberate. A linear fade would still sit at half level a
    couple of milliseconds from the seam, so a square wave would arrive at the
    file's end with a step; the raised cosine reaches near zero much sooner.

    A looping file takes no fade (see LOOPING): its high pass is run over the
    file's own tail first and that warm up is dropped, so sample 0 starts from
    the state a repeat would have left behind and the seam is the same step as
    any other inside the file.
    """
    mix = np.asarray(audio, dtype=np.float64)
    if mix.size == 0:
        return mix
    if loop:
        warm = min(mix.size, max(1, int(round(LOOP_WARMUP_S * SR))))
        mix = dc_block(np.concatenate((mix[-warm:], mix)))[warm:]
    else:
        mix = dc_block(mix)
    peak = float(np.abs(mix).max())
    if peak > LIMITER_KNEE:
        mix = render_chip.soft_limit(mix, LIMITER_KNEE)
    if not loop:
        fade = min(int(round(FADE_MS * SR / 1000.0)), mix.size // 2)
        if fade > 0:
            ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade) / float(fade)))
            mix[:fade] *= ramp
            mix[-fade:] *= ramp[::-1]
    peak = float(np.abs(mix).max())
    if peak > 0:
        mix = mix / peak * PEAK
    return mix


def measure(audio: np.ndarray) -> dict:
    peak = float(np.abs(audio).max()) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0
    dc = float(np.mean(audio)) if audio.size else 0.0
    window = max(1, int(round(FADE_MS * SR / 1000.0)))
    edge = audio[:window]
    step = float(np.max(np.abs(np.diff(edge)))) if edge.size > 1 else 0.0
    return {
        "length_seconds": round(audio.size / SR, 6),
        "length_samples": int(audio.size),
        "peak_dbfs": round(20.0 * math.log10(peak), 3) if peak > 0 else None,
        "rms_dbfs": round(20.0 * math.log10(rms), 3) if rms > 0 else None,
        "dc_offset": round(dc, 6),
        "first_sample": round(float(audio[0]), 6),
        "last_sample": round(float(audio[-1]), 6),
        "edge_max_step": round(step, 6),
    }


def write_wav(path: str, audio: np.ndarray) -> None:
    ints = np.clip(np.round(audio * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(ints.tobytes())


def write_ogg(wav_path: str, ogg_path: str, loop_samples: int | None = None) -> str | None:
    """Encode one wav to Vorbis. A loop also carries its loop points in the OGG itself.

    Spec 12 rule 3 says loop points come from the OGG's own loop metadata and never from a
    code side guess, so a looping effect writes LOOPSTART and LOOPLENGTH as Vorbis comments
    over the whole file. A one shot effect gets no tags, because a tag on it would claim a
    loop the sound does not have.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return "ffmpeg not found on PATH"
    command = [ffmpeg, "-y", "-loglevel", "error", "-i", wav_path]
    if loop_samples is not None:
        command += ["-metadata", "LOOPSTART=0", "-metadata", "LOOPLENGTH=%d" % int(loop_samples)]
    command += ["-ac", "1", "-ar", str(SR), "-c:a", "libvorbis", "-q:a", "5", ogg_path]
    done = subprocess.run(
        command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    if done.returncode != 0:
        return (done.stderr or "").strip()[:300] or "ffmpeg failed"
    if not os.path.exists(ogg_path) or os.path.getsize(ogg_path) == 0:
        return "ffmpeg wrote no ogg"
    return None


def build(out_dir: str, make_ogg: bool = True, fade_ms: float | None = None) -> dict:
    """Render every effect into out_dir and return the manifest."""
    global FADE_MS
    if fade_ms is not None:
        FADE_MS = float(fade_ms)
    os.makedirs(out_dir, exist_ok=True)
    effects = []
    for name, builder, groups in EFFECTS:
        audio, voices, purpose = builder()
        looping = name in LOOPING
        audio = finish(audio, loop=looping)
        wav_path = os.path.join(out_dir, "%s.wav" % name)
        write_wav(wav_path, audio)
        entry = {"name": name, "voices": voices, "purpose": purpose,
                 "groups": groups, "loop": looping, "files": {"wav": "%s.wav" % name}}
        entry.update(measure(audio))
        if looping:
            entry["loop_start"] = 0
            entry["loop_length"] = int(audio.size)
        if make_ogg:
            ogg_path = os.path.join(out_dir, "%s.ogg" % name)
            error = write_ogg(wav_path, ogg_path,
                              loop_samples=int(audio.size) if looping else None)
            if error is None:
                entry["files"]["ogg"] = "%s.ogg" % name
            else:
                entry["files"]["ogg"] = None
                entry["ogg_error"] = error
        effects.append(entry)

    manifest = {
        "generated_by": "tools/sfx.py",
        "source": "synthesised from the 2A03 voice set; no sampled or copied audio",
        "sample_rate": SR,
        "channels": 1,
        "bit_depth": BIT_DEPTH,
        "peak_target_dbfs": PEAK_DBFS,
        "fade_ms": FADE_MS,
        "fade_shape": "raised_cosine",
        "dc_block_hz": DC_BLOCK_HZ,
        "voice_set": ["pulse_12.5", "pulse_25", "pulse_50", "triangle",
                      "noise_short", "noise_long"],
        "looping_names": sorted(LOOPING),
        "required_names": REQUIRED_NAMES,
        "name_groups": NAME_GROUPS,
        "effects": effects,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    return manifest


# -------------------------------------------------------------------- preview


def _font(size: int):
    """A monospaced TrueType face at this size, or Pillow's built in bitmap font.

    A candidate that is missing is skipped, and one that exists but cannot be opened
    (a truncated or locked font file) falls through to the next candidate rather than
    ending the preview: the sheet is a measurement aid and must still be written.
    """
    from PIL import ImageFont
    for candidate in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"):
        if not os.path.exists(candidate):
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def write_preview(manifest: dict, wav_dir: str, png_path: str) -> dict:
    """A contact sheet of every effect, drawn at three times its natural size.

    One cell per effect, two columns: a full waveform in the top line and the
    first 60 ms below it, so the attack is visible as well as the overall shape.
    """
    from PIL import Image, ImageDraw

    cell_w, cell_h = 260, 54
    cols = 2
    rows = (len(manifest["effects"]) + cols - 1) // cols
    scale = PREVIEW_SCALE
    sheet = Image.new("RGB", (cell_w * cols * scale, cell_h * rows * scale), (16, 16, 24))
    draw = ImageDraw.Draw(sheet)
    font = _font(9 * scale)
    small = _font(7 * scale)
    wav_cache = {}
    for index, entry in enumerate(manifest["effects"]):
        col, row = index % cols, index // cols
        ox, oy = col * cell_w * scale, row * cell_h * scale
        draw.rectangle([ox + 2, oy + 2, ox + cell_w * scale - 3, oy + cell_h * scale - 3],
                       outline=(60, 60, 90))
        name = entry["name"]
        draw.text((ox + 6, oy + 4), name, fill=(220, 220, 240), font=font)
        draw.text((ox + 6, oy + 6 + 9 * scale),
                  "%.2fs  %+.2f dBFS  %s" % (entry["length_seconds"], entry["peak_dbfs"],
                                             ",".join(entry["voices"])[:28]),
                  fill=(150, 170, 200), font=small)
        if name not in wav_cache:
            with wave.open(os.path.join(wav_dir, entry["files"]["wav"]), "rb") as handle:
                raw = handle.readframes(handle.getnframes())
            wav_cache[name] = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
        audio = wav_cache[name]
        top = oy + 4 + 18 * scale
        mid = top + 12 * scale
        width = cell_w * scale - 12
        for line_index, (start, span) in enumerate((
                (0, audio.size),
                (0, min(audio.size, int(0.06 * SR))))):
            seg = audio[start:start + span]
            base = mid + line_index * 22 * scale
            if seg.size == 0:
                continue
            n = min(width, seg.size)
            buckets = np.array_split(seg, n)
            highs = np.array([b.max() for b in buckets])
            lows = np.array([b.min() for b in buckets])
            for x in range(n):
                draw.line([(ox + 6 + x, base - highs[x] * 9 * scale),
                           (ox + 6 + x, base - lows[x] * 9 * scale)],
                          fill=(120, 220, 160) if line_index == 0 else (240, 190, 120))
            draw.line([(ox + 6, base), (ox + 6 + n, base)], fill=(40, 40, 60))
    os.makedirs(os.path.dirname(os.path.abspath(png_path)) or ".", exist_ok=True)
    sheet.save(png_path)
    return {"preview": os.path.abspath(png_path), "scale": scale,
            "width": sheet.width, "height": sheet.height, "cells": len(manifest["effects"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesise the NES style sound effect set.")
    parser.add_argument("--out", default=os.path.join(ROOT, OUT_REL))
    parser.add_argument("--preview", default=os.path.join(ROOT, PREVIEW_DIR_REL, PREVIEW_NAME))
    parser.add_argument("--no-ogg", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args(argv)

    manifest = build(args.out, make_ogg=not args.no_ogg)
    if args.no_ogg and os.path.isdir(args.out) and any(
            n.endswith(".ogg") for n in os.listdir(args.out)):
        # --no-ogg exists for a fast iteration loop. It is not a way to refresh a folder
        # whose manifest lists oggs: the manifest written here would drop them, and the
        # committed set would then claim 21 wav and no ogg while 21 oggs sit beside them.
        print("Q: --no-ogg wrote a manifest without ogg entries, but %s already holds oggs."
              % args.out)
        print("Q: run tools\\sfx.py without --no-ogg to restore the committed manifest.")
    missing = [e["name"] for e in manifest["effects"] if e["files"].get("ogg") is None] \
        if not args.no_ogg else []
    for entry in manifest["effects"]:
        print("P: %-18s %5.3fs  peak %+.2f dBFS  rms %+.2f dBFS  %s"
              % (entry["name"], entry["length_seconds"], entry["peak_dbfs"],
                 entry["rms_dbfs"], ",".join(entry["voices"])))
    print("P: %d effects, %d wav, %d ogg" %
          (len(manifest["effects"]), len(manifest["effects"]),
           sum(1 for e in manifest["effects"] if e["files"].get("ogg"))))
    if missing:
        print("P: ogg failures: %s" % ", ".join(missing))
    if not args.no_preview:
        info = write_preview(manifest, args.out, args.preview)
        print("P: preview %s at %dx" % (info["preview"], info["scale"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
