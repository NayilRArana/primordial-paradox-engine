# SFX-1, the sound effect set, measured

Card SFX-1 (t_f9a87b4f), builder lane. Sources: `tools\sfx.py` (synthesis, no samples,
no copied audio), tests: `tests/test_sfx.py`, index: `manifest.json` in this folder.
Card DRIVE-SFX (t_c365ff5d) added `car_engine_loop`, the set's one loop.

## What the set is

22 files. 21 of them come from the 19 cue names in card SFX-1: `text_blip` is three cues,
one per speaker (`text_blip_a` Konrad C5, `text_blip_b` Zander E5, `text_blip_c` Percy G5),
which is what `game\scripts\pp_audio\pp_audio.gml` and `tools\sync_art.py` ask for by name.
The 22nd is `car_engine_loop`, the drive's engine from shot 2 to shot 12 of
`knowledge/DRIVE-SHOT-LIST.md`; it is not one of the card's 19 names and it is the only file
in the set that loops.

Voices used: `pulse_12.5`, `pulse_25`, `pulse_50`, `triangle`, `noise_short` (93 cycle
LFSR), `noise_long` (4 to 4068 cycle LFSR). The noise generator is `render_chip.lfsr_cycle`,
the project's one copy of the APU noise hardware, so effects and the title theme agree
about what the chip does. Pulse and triangle are phase accumulators here because an effect
sweeps its pitch every sample, which the MIDI renderer never does.

## Measured from the committed files

| name | length s | peak dBFS | first 1 ms | last 1 ms |
| --- | --- | --- | --- | --- |
| menu_move | 0.060 | -3.000 | 0.03943 | 0.00037 |
| menu_select | 0.160 | -3.000 | 0.01047 | 0.00095 |
| menu_cancel | 0.180 | -3.000 | 0.03149 | 0.00372 |
| text_blip_a | 0.060 | -3.000 | 0.00549 | 0.00052 |
| text_blip_b | 0.060 | -3.000 | 0.00528 | 0.00070 |
| text_blip_c | 0.060 | -3.000 | 0.00528 | 0.00015 |
| footstep | 0.090 | -3.000 | 0.00967 | 0.00201 |
| door_hatch | 0.300 | -3.000 | 0.02075 | 0.00125 |
| item_get | 0.320 | -3.000 | 0.00357 | 0.00150 |
| heal | 0.520 | -3.000 | 0.00336 | 0.00198 |
| hit_light | 0.120 | -3.000 | 0.01468 | 0.00095 |
| hit_heavy | 0.340 | -3.000 | 0.00443 | 0.00143 |
| miss | 0.200 | -3.000 | 0.02258 | 0.00021 |
| crit | 0.420 | -3.000 | 0.02560 | 0.00174 |
| level_up | 1.200 | -3.000 | 0.00891 | 0.00293 |
| encounter_swoosh | 0.700 | -3.000 | 0.00082 | 0.00162 |
| thunder_soft | 1.450 | -3.000 | 0.03922 | 0.00269 |
| wave_wash | 1.100 | -3.000 | 0.02707 | 0.00052 |
| alarm | 0.640 | -3.000 | 0.01562 | 0.00583 |
| save_jingle | 1.400 | -3.000 | 0.00381 | 0.00006 |
| game_over | 1.400 | -3.000 | 0.00629 | 0.00333 |
| car_engine_loop (loop) | 0.800 | -3.000 | 0.64514 | 0.64740 |

Totals: 510678 samples, lengths 0.060 s (menu_move) to 1.450 s (thunder_soft), inside the
card's 0.05 to 1.5 s window. Every file peaks at exactly -3.000 dBFS. All files are mono,
44100 Hz, 16 bit PCM. Every one shot starts and ends on exactly 0.000000, because each one
carries a 5 ms raised cosine fade at both ends; the largest excursion in the first
millisecond is 0.03943 and in the last millisecond 0.00583, which is the fade, not a step.

`car_engine_loop` is the exception on purpose. It carries no fade, because a file that is
played round and round would duck at the seam once per lap, so its first and last samples
are +0.645142 and +0.647400 and the seam is the loop's own repeat (see the section below).

## The one loop

The shot list holds the engine under the whole film, so the effect has to be a loop rather
than a burst with a fade. It is built that way in `tools\sfx.py`:

- 0.800 s, 35280 samples. A four cylinder at idle: firing at 60 Hz (735 samples a firing,
  48 in the file), the crank half order at 30 Hz for the body, the second order at 120 Hz,
  and a noise tick per firing from the LFSR at a 2000 to 1200 cycle clock.
- Every voice is periodic in the buffer, and the file is one 4410 sample pattern (six
  firings, three 0.1 s load wobbles) repeated eight times. Shifting the file by its own
  period changes it by at most 4.3e-07 in float, which is -127 dBFS and is the 20 Hz high
  pass settling, not a seam; on the 16 bit file the shift changes one sample by at most one
  grid step, which is rounding.
- The seam therefore measures 0.002258, while the largest step anywhere inside the file is
  0.195660: the join is 87 times smaller than an ordinary step in the same file, so there is
  nothing to hear at the wrap.
- The 20 Hz high pass is primed with the file's own last 0.1 s before the file is filtered,
  so sample 0 starts from the filter state a repeat would have left behind.
- The OGG carries `LOOPSTART=0` and `LOOPLENGTH=35280` as Vorbis comments, which is spec 12
  rule 3 ("loop points come from the OGG file's own loop metadata, never from a code side
  guess"). The one shots carry no such tag, and a test holds both halves.
- Where the energy sits, measured: 40.0 percent of magnitude under 80 Hz, 12.6 percent 80 to
  200 Hz, 17.1 percent 200 Hz to 1 kHz, 19.0 percent 1 to 8 kHz, 9.6 percent above 8 kHz. The
  triangle carries the body because a 25 percent pulse at 60 Hz is mostly harmonics.

Ogg: 22 files, Vorbis mono 44100 Hz quality 5, 4959 to 25200 bytes, all 22 probed with
ffprobe for codec, rate, channels and duration (0 bad).

DC: a 20 Hz one pole high pass, like the APU's output capacitor. Worst residual offset is
wave_wash at 0.0041; before the blocker the worst was miss at 0.137. The loop sits at
-0.00000.

Preview: `output\sfx_preview_3x.png`, 1560x1782 px, one cell per effect at 3x, full
waveform above and the first 60 ms below.

## How to rebuild and how to check

    python tools\sfx.py                  # writes this folder and the preview
    python -m pytest tests\test_sfx.py -q

17 tests, all passing: every cue name present as wav and ogg, manifest agrees with the
generator table, lengths in range, mono 44100 16 bit, peak -3.000 dBFS within 0.05 dB,
every one shot starts and ends on zero inside the fade, no constant offset, the loop is one
pattern repeated rather than faded, the loop's ogg carries its loop points and a one shot's
does not, deterministic (two builds byte identical, and the committed wavs are byte identical
to a fresh build in a separate process), each tonal cue measured by FFT at its intended
pitch, no two effects share a shape, and the preview is the 3x sheet.

## Wiring

`tools\sync_art.py` mirrors each WAV into `game\datafiles\sfx` and writes `sfx.json` with the
offset, byte length, rate, channels and bit depth read from each WAV header, so GameMaker
never needs a hardcoded 44. Cue names here are the names the GML asks for; a typo in GML
fails the mirror rather than the runtime. `car_engine_loop` is in that cue list now, and
`pp_audio_cues()` already named it before the file existed.

Q: for gamedev. `pp_audio_sfx` plays every effect with `loop` off and `data\audio.json`
records the row with `"loop": true`; the file is a real loop but the runner has no looping
play call, so today it would fire once. Either the bus gets a looping effect path or the
drive streams it as an ambience in the music slot. The OGG's loop points are there for
whichever it is.
