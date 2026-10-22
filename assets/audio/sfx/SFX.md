# SFX-1, the sound effect set, measured

Card SFX-1 (t_f9a87b4f), builder lane. Sources: `tools\sfx.py` (synthesis, no samples,
no copied audio), tests: `tests/test_sfx.py`, index: `manifest.json` in this folder.

## What the set is

21 files from the 19 cue names in the card. `text_blip` is three cues, one per speaker
(`text_blip_a` Konrad C5, `text_blip_b` Zander E5, `text_blip_c` Percy G5), which is what
`game\scripts\pp_audio\pp_audio.gml` and `tools\sync_art.py` ask for by name.

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

Totals: 475395 samples, lengths 0.060 s (menu_move) to 1.450 s (thunder_soft), inside the
card's 0.05 to 1.5 s window. Every file peaks at exactly -3.000 dBFS. All files are mono,
44100 Hz, 16 bit PCM. Every first and last sample is exactly 0.000000, because each one
carries a 5 ms raised cosine fade at both ends; the largest excursion in the first
millisecond is 0.03943 and in the last millisecond 0.00583, which is the fade, not a step.

Ogg: 21 files, Vorbis mono 44100 Hz quality 5, 4959 to 25200 bytes, all 21 probed with
ffprobe for codec, rate, channels and duration (0 bad).

DC: a 20 Hz one pole high pass, like the APU's output capacitor. Worst residual offset is
wave_wash at 0.0041; before the blocker the worst was miss at 0.137.

Preview: `output\sfx_preview_3x.png`, 1560x1782 px, one cell per effect at 3x, full
waveform above and the first 60 ms below.

## How to rebuild and how to check

    python tools\sfx.py                  # writes this folder and the preview
    python -m pytest tests\test_sfx.py -q

15 tests, all passing: every cue name present as wav and ogg, manifest agrees with the
generator table, lengths in range, mono 44100 16 bit, peak -3.000 dBFS within 0.05 dB,
first and last sample zero and the first and last millisecond inside the fade, no constant
offset, deterministic (two builds byte identical, and the committed wavs are byte identical
to a fresh build in a separate process), each tonal cue measured by FFT at its intended
pitch, no two effects share a shape, and the preview is the 3x sheet.

## Wiring

`tools\sync_art.py` mirrors each WAV into `game\datafiles\sfx` and writes `sfx.json` with the
offset, byte length, rate, channels and bit depth read from each WAV header, so GameMaker
never needs a hardcoded 44. Cue names here are the names the GML asks for; a typo in GML
fails the mirror rather than the runtime.
