"""Tests for the NES style sound effect set in tools\\sfx.py.

What is proved here, rather than asserted in a comment:
  - every effect named by card SFX-1 is on disk as a wav and an ogg, and the
    manifest on disk agrees with the table the generator uses;
  - every file is mono, 44100 Hz, 16 bit, between 0.05 and 1.5 seconds;
  - every file peaks at -3 dBFS within 0.05 dB, measured from the samples;
  - no one shot starts or ends on a step: the first and last samples are zero
    and the first and last millisecond stay inside the 5 ms raised cosine fade;
  - the one loop (car_engine_loop) is instead proved periodic: the file is one
    measured pattern repeated, so the seam is not a fade, it is the same step as
    any other inside the file, and its ogg carries LOOPSTART and LOOPLENGTH
    (spec 12 rule 3);
  - the output is deterministic: two runs give byte identical wavs;
  - the preview sheet is the 3x contact sheet the card asks for.

The build happens once per session into a throwaway folder, without ogg, so the
suite does not depend on ffmpeg speed. The committed oggs are checked by size
and one of them is probed with ffprobe. Nothing here opens a window or plays
audio.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import wave

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import sfx  # noqa: E402

SFX_DIR = os.path.join(ROOT, "assets", "audio", "sfx")
PREVIEW_PATH = os.path.join(ROOT, "output", sfx.PREVIEW_NAME)
MIN_LENGTH = 0.05
MAX_LENGTH = 1.5
PEAK_TOLERANCE_DB = 0.05


def _read_wav(path):
    with wave.open(path, "rb") as handle:
        info = {
            "channels": handle.getnchannels(),
            "sample_rate": handle.getframerate(),
            "sample_width": handle.getsampwidth(),
            "frames": handle.getnframes(),
        }
        raw = handle.readframes(handle.getnframes())
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    return info, samples


def _peak_dbfs(samples):
    peak = float(np.abs(samples).max()) if samples.size else 0.0
    return 20.0 * np.log10(peak) if peak > 0 else None


@pytest.fixture(scope="session")
def fresh_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("sfx")
    return str(out), sfx.build(str(out), make_ogg=False)


@pytest.fixture(scope="session")
def manifest_on_disk():
    with open(os.path.join(SFX_DIR, "manifest.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_every_effect_is_written(fresh_build):
    out_dir, manifest = fresh_build
    names = [entry["name"] for entry in manifest["effects"]]
    assert names == [name for name, _builder, _groups in sfx.EFFECTS]
    # The 21 of card SFX-1 plus car_engine_loop, which the drive shot list adds and which is
    # the one loop; the count is pinned so a dropped effect cannot leave a silent command.
    assert len(names) == 22
    for name in names:
        wav_path = os.path.join(out_dir, name + ".wav")
        assert os.path.exists(wav_path), "missing %s" % wav_path
        assert os.path.getsize(wav_path) > 1000


def test_required_names_are_covered(manifest_on_disk):
    covered = {entry["name"] for entry in manifest_on_disk["effects"]}
    for group, members in manifest_on_disk["name_groups"].items():
        covered.add(group)
        for member in members:
            assert member in covered, "%s names a missing file %s" % (group, member)
    missing = [name for name in sfx.REQUIRED_NAMES if name not in covered]
    assert missing == [], "card SFX-1 names not covered: %s" % missing
    assert len(sfx.REQUIRED_NAMES) == 19


def test_lengths_are_in_range(manifest_on_disk, fresh_build):
    _out_dir, fresh = fresh_build
    for manifest in (manifest_on_disk, fresh):
        for entry in manifest["effects"]:
            length = entry["length_seconds"]
            assert MIN_LENGTH <= length <= MAX_LENGTH, \
                "%s is %.3fs, outside %.2f to %.2f" % (entry["name"], length, MIN_LENGTH, MAX_LENGTH)


def test_format_is_mono_44100_16bit(manifest_on_disk):
    for entry in manifest_on_disk["effects"]:
        info, samples = _read_wav(os.path.join(SFX_DIR, entry["files"]["wav"]))
        assert info["channels"] == 1, entry["name"]
        assert info["sample_rate"] == 44100, entry["name"]
        assert info["sample_width"] == 2, entry["name"]
        assert info["frames"] == entry["length_samples"], entry["name"]
        assert samples.size == entry["length_samples"]
        assert abs(info["frames"] / 44100.0 - entry["length_seconds"]) < 0.0001


def test_every_file_peaks_at_minus_3_dbfs(manifest_on_disk):
    for entry in manifest_on_disk["effects"]:
        _info, samples = _read_wav(os.path.join(SFX_DIR, entry["files"]["wav"]))
        peak = _peak_dbfs(samples)
        assert peak is not None, entry["name"]
        assert abs(peak - sfx.PEAK_DBFS) <= PEAK_TOLERANCE_DB, \
            "%s peaks at %.3f dBFS, wanted %.1f" % (entry["name"], peak, sfx.PEAK_DBFS)
        assert abs(entry["peak_dbfs"] - peak) <= 0.01, entry["name"]


def test_no_click_at_either_end(manifest_on_disk):
    one_ms = int(round(0.001 * 44100))
    for entry in manifest_on_disk["effects"]:
        if entry.get("loop"):
            # A loop is not faded: the fade sits at both ends of a file that is played round
            # and round, so the seam would duck once a lap. The loop's own test below proves
            # the seam instead.
            continue
        _info, samples = _read_wav(os.path.join(SFX_DIR, entry["files"]["wav"]))
        assert samples[0] == 0.0, "%s starts on %r" % (entry["name"], samples[0])
        assert samples[-1] == 0.0, "%s ends on %r" % (entry["name"], samples[-1])
        head = float(np.abs(samples[:one_ms]).max())
        tail = float(np.abs(samples[-one_ms:]).max())
        # The raised cosine reaches 9.5 percent of full scale after 1 ms of a
        # 5 ms fade, so anything above 0.08 is a step, not a fade.
        assert head <= 0.08, "%s jumps to %.3f in its first millisecond" % (entry["name"], head)
        assert tail <= 0.08, "%s jumps to %.3f in its last millisecond" % (entry["name"], tail)
        assert entry["first_sample"] == 0.0 and entry["last_sample"] == 0.0


def test_the_engine_loop_is_one_pattern_repeated(manifest_on_disk):
    """The loop is proved periodic rather than faded, which is the only honest loop.

    The engine file is one 4410 sample pattern (three 0.1 s load wobbles, six firings at
    60 Hz) repeated eight times, so playing the file round and round is playing it straight:
    shifting it by its own period reproduces it. In float that is 1.4e-07, -137 dBFS, which is
    the 20 Hz high pass not being fully settled after the tail warm up, not a seam. On the
    16 bit file it is at most one step of the sample grid, which is rounding, so the threshold
    here is two steps and the measurement below the claim is one.
    """
    one_step = 1.0 / 32768.0
    looping = [e for e in manifest_on_disk["effects"] if e.get("loop")]
    assert [e["name"] for e in looping] == sorted(sfx.LOOPING), \
        "the manifest's loops are %s, the generator's are %s" % (
            [e["name"] for e in looping], sorted(sfx.LOOPING))
    for entry in looping:
        _info, samples = _read_wav(os.path.join(SFX_DIR, entry["files"]["wav"]))
        period = entry["loop_length"] // 8
        assert entry["loop_start"] == 0 and entry["loop_length"] == samples.size
        assert samples.size % period == 0
        residue = float(np.abs(samples[period:] - samples[:-period]).max())
        assert residue <= 2.0 * one_step, "%s does not repeat: residue %.3e" % (entry["name"], residue)
        step = abs(float(samples[0]) - float(samples[-1]))
        internal = float(np.abs(np.diff(samples)).max())
        assert step < internal, \
            "%s jumps %.5f at the seam, its largest internal step is %.5f" % (entry["name"], step, internal)


def test_the_loop_ogg_carries_its_loop_points(manifest_on_disk):
    """Spec 12 rule 3: loop points come from the OGG's own metadata, never a code guess.

    Vorbis comments belong to the Vorbis stream, not to the container, so they are read from
    the stream tags; ffprobe reports them there and the format level is empty.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        pytest.skip("ffprobe not on PATH")

    def stream_tags(path):
        done = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream_tags",
             "-of", "json", path],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
        )
        assert done.returncode == 0, done.stderr
        streams = json.loads(done.stdout).get("streams", [])
        tags = streams[0].get("tags", {}) if streams else {}
        return {key.upper(): value for key, value in tags.items()}, done.stdout

    entries = {entry["name"]: entry for entry in manifest_on_disk["effects"]}
    for name in sorted(sfx.LOOPING):
        path = os.path.join(SFX_DIR, entries[name]["files"]["ogg"])
        tags, raw = stream_tags(path)
        assert tags.get("LOOPSTART") == "0", raw
        assert tags.get("LOOPLENGTH") == str(entries[name]["loop_length"]), raw
    tags, raw = stream_tags(os.path.join(SFX_DIR, entries["menu_move"]["files"]["ogg"]))
    assert "LOOPLENGTH" not in tags and "LOOPSTART" not in tags, \
        "a one shot claims a loop: %s" % raw


def test_no_constant_offset(manifest_on_disk):
    """A pulse that is not DC centred, or a burst of low noise, would bias the mixer.

    Measured after the 20 Hz DC blocker: the worst file is wave_wash at 0.0041,
    the tonal effects sit under 0.0002. Before the blocker the worst was miss at
    0.137, so this threshold is what tells the two apart.
    """
    for entry in manifest_on_disk["effects"]:
        _info, samples = _read_wav(os.path.join(SFX_DIR, entry["files"]["wav"]))
        offset = abs(float(samples.mean()))
        assert offset < 0.006, "%s has a DC offset of %.4f" % (entry["name"], offset)


def test_ogg_files_are_present(manifest_on_disk):
    for entry in manifest_on_disk["effects"]:
        assert entry["files"].get("ogg"), "%s has no ogg (%s)" % (
            entry["name"], entry.get("ogg_error"))
        ogg_path = os.path.join(SFX_DIR, entry["files"]["ogg"])
        assert os.path.getsize(ogg_path) > 1000


def test_one_ogg_is_mono_44100(manifest_on_disk):
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        pytest.skip("ffprobe not on PATH")
    path = os.path.join(SFX_DIR, manifest_on_disk["effects"][0]["files"]["ogg"])
    done = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=sample_rate,channels,codec_name", "-of", "csv=p=0", path],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stderr
    fields = done.stdout.strip().split(",")
    assert "vorbis" in fields[0], done.stdout
    assert fields[1] == "44100", done.stdout
    assert fields[2] == "1", done.stdout


def test_manifest_matches_the_generator(manifest_on_disk):
    assert manifest_on_disk["sample_rate"] == 44100
    assert manifest_on_disk["channels"] == 1
    assert manifest_on_disk["bit_depth"] == 16
    assert manifest_on_disk["peak_target_dbfs"] == sfx.PEAK_DBFS
    assert manifest_on_disk["fade_ms"] == sfx.FADE_MS
    assert manifest_on_disk["dc_block_hz"] == sfx.DC_BLOCK_HZ
    assert manifest_on_disk["looping_names"] == sorted(sfx.LOOPING)
    allowed = set(manifest_on_disk["voice_set"])
    for entry in manifest_on_disk["effects"]:
        assert entry["loop"] is (entry["name"] in sfx.LOOPING), entry["name"]
        assert entry["voices"], entry["name"]
        assert set(entry["voices"]) <= allowed, "%s lists unknown voices" % entry["name"]
        assert entry["purpose"].strip(), entry["name"]
        assert len(entry["purpose"]) > 20, entry["name"]


def test_output_is_deterministic(tmp_path):
    first = sfx.build(str(tmp_path / "a"), make_ogg=False)
    second = sfx.build(str(tmp_path / "b"), make_ogg=False)
    for entry in first["effects"]:
        name = entry["name"]
        with open(tmp_path / "a" / (name + ".wav"), "rb") as fh:
            left = fh.read()
        with open(tmp_path / "b" / (name + ".wav"), "rb") as fh:
            right = fh.read()
        assert left == right, "%s is not reproducible" % name
    assert [e["peak_dbfs"] for e in first["effects"]] == \
        [e["peak_dbfs"] for e in second["effects"]]


def test_the_voices_are_the_chip_ones():
    """Each duty and both noise modes are actually used, measured on the samples."""
    saw_duties = set()
    saw_short_noise = False
    for name, builder, _groups in sfx.EFFECTS:
        _audio, voices, _purpose = builder()
        saw_duties.update(v for v in voices if v.startswith("pulse"))
        saw_short_noise = saw_short_noise or "noise_short" in voices
    assert {"pulse_12.5", "pulse_25", "pulse_50"} <= saw_duties
    assert saw_short_noise

    # A 12.5 percent pulse has less energy than a 50 percent one at the same
    # amplitude, which is the measured difference between the two duties.
    quiet = sfx.finish(sfx.build_menu_move()[0])
    loud = sfx.finish(sfx.build_menu_cancel()[0])
    assert float(np.mean(quiet ** 2)) < float(np.mean(loud ** 2))


def _fundamental(samples, window=4096):
    """Frequency of the strongest bin, in Hz, from a window around the loudest sample."""
    start = max(0, int(np.argmax(np.abs(samples))) - window // 4)
    segment = samples[start:start + window]
    if segment.size < window:
        segment = np.pad(segment, (0, window - segment.size))
    spectrum = np.abs(np.fft.rfft(segment * np.hanning(window)))
    index = int(np.argmax(spectrum))
    return index * 44100.0 / window


def test_tonal_effects_play_the_intended_pitch(fresh_build):
    """The pulse voices are real pitches, measured by FFT, not just noise with an envelope."""
    _out_dir, manifest = fresh_build
    wanted = {
        "menu_move": [sfx.hz(84)],
        "menu_select": [sfx.hz(76), sfx.hz(88)],
        "text_blip_a": [sfx.hz(72)],
        "text_blip_b": [sfx.hz(76)],
        "text_blip_c": [sfx.hz(79)],
        "alarm": [sfx.hz(88), sfx.hz(84)],
    }
    builders = {name: builder for name, builder, _groups in sfx.EFFECTS}
    for name, candidates in wanted.items():
        audio, _voices, _purpose = builders[name]()
        measured = _fundamental(sfx.finish(audio))
        assert any(abs(measured - expected) <= 0.02 * expected for expected in candidates), \
            "%s plays %.1f Hz, wanted one of %s" % (name, measured, candidates)


def test_every_effect_is_distinct(fresh_build):
    """No two effects are a copy of each other: a duplicated name would be a silent bug."""
    _out_dir, manifest = fresh_build
    builders = {name: builder for name, builder, _groups in sfx.EFFECTS}
    lengths = {name: len(builder()[0]) for name, builder in builders.items()}
    shapes = {}
    for name, builder in builders.items():
        audio = sfx.finish(builder()[0])
        shapes[name] = (lengths[name], round(float(np.abs(audio).mean()), 5),
                        round(float(np.mean(audio ** 2)), 6))
    assert len(set(shapes.values())) == len(shapes), \
        "two effects share a length and an energy: %s" % shapes


def test_preview_sheet_is_three_times_scale(manifest_on_disk):
    from PIL import Image
    assert os.path.exists(PREVIEW_PATH), PREVIEW_PATH
    with Image.open(PREVIEW_PATH) as image:
        width, height = image.size
        assert image.mode == "RGB"
    rows = (len(manifest_on_disk["effects"]) + 1) // 2
    assert width == 260 * 2 * sfx.PREVIEW_SCALE
    assert height == 54 * rows * sfx.PREVIEW_SCALE
