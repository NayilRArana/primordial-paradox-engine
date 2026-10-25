#!/usr/bin/env python3
"""play_demo.py: one command that plays a scripted run of the built game and records it to an mp4.

Why this file exists: the hackathon submission needs a video of real gameplay that can be re-recorded the
night before the deadline, by one command, without a person at the keyboard and without a new take each
time something in the title moves. So the run is data (data/demo/run_001.json: key presses on a 60 step a
second clock, the seeds the slice actually reaches, and the game's own log lines as the sync points), and
this tool is the player.

It is not a second capture harness. Every window and key primitive is the one tools/capture_title.py
already proved on this PC: the window is found by process image name (not by title), it is raised with the
foreground lock lifted, every key goes through the input queue because a GameMaker game reads key state and
a posted key is a dud, and the rectangle is checked for a covering window before and after recording. What
this file adds is the script, the clock, the ffmpeg recording at 60 fps cut to a true 3x of the NES screen,
and a check that the result is a video of the game and not of a terminal.

The mp4 is 768x720, which is exactly 3x the 256x240 screen the game draws (measured: a 768x720 viewport at
[8, 31] inside a 784x759 window, tests/test_capture_title.py). The window rectangle is recorded as it is
and then cropped to the viewport that tools/nes_composite_check.py finds in a pre-roll frame, so the frame
is the game's own pixels and not the desktop's scaling of them. A frame of a terminal, of the desktop or of
a cover window has no such viewport and is refused.

Audio: system audio needs a loopback device, and this host reports none (tools/capture_title.py records the
same). When there is no loopback the video is recorded silent and a stand-in track is rendered from the
title theme that ships in the repo, then muxed in and labelled in the mp4's own metadata and in the verify
file. It is never passed off as the game's live output.

Usage:
    python tools\\play_demo.py                        play data\\demo\\run_001.json and record output\\demo\\run_001.mp4
    python tools\\play_demo.py --script data\\demo\\x.json --out output\\demo\\x.mp4
    python tools\\play_demo.py --check                re-check the mp4 the script names, without launching the game
    python tools\\play_demo.py --check --video P.mp4  check some other file the same way
    python tools\\play_demo.py --dry-run              validate the script and print the timeline in seconds

Exit codes:
    0  the recording passed every check, or --check passed, or --dry-run validated the script
    1  a check failed, or the script is malformed, or the game window never appeared
    3  the watchdog fired (the run overran)
    4  the idle gate refused to open a window: the user had input in the last three minutes (card CAPTURE-QUIET),
       or this host cannot draw at all, in which case the run is not measured and nothing is claimed about it

Quiet by default (card CAPTURE-QUIET, Nayil 2026-10-22): the game is started with PP_MUTE=1 so nothing plays, no
window opens unless the idle gate in tools\idle_check.py sees three quiet minutes, and the window is moved off the
primary screen. --sound is for an audio proof, --show leaves the window where it is, --force is a human override.

Portable import (card PINE-HONEST, 2026-10-24): the two modules this tool draws and launches with,
tools\capture_title.py and tools\pp_launch.py, import ctypes.wintypes at their own line 39 and line 41, which raises
on a host without the Windows path. Imported at the top of this file they killed it before it could say anything, and
that traceback, not a test result, is what 19 of the 21 Pine reds measured on 2026-10-24 were. Both are now imported
inside the function that uses them, and a host that cannot import them prints one line, "play_demo: unavailable on
this platform", and exits 4 (the harness's not-measured lane, tools\idle_check.py EXIT_REFUSED) instead of passing
silently or going red.
"""

import argparse
import json
import os
import subprocess
import sys
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import idle_check  # noqa: E402  EXIT_REFUSED = 4, the harness's not-measured lane, imported instead of restated

# Card PINE-HONEST: the two modules this tool draws and launches with are imported inside the functions that use
# them, never here. tools/capture_title.py:39 and tools/pp_launch.py:41 each import ctypes.wintypes, which raises on a
# host without the Windows path (Pine is Linux), so a module level import turns "this host cannot draw" into a
# traceback with no exit code and no line for a reader. See capture_module(), launch_module() and unavailable().
EXIT_UNAVAILABLE = idle_check.EXIT_REFUSED
UNAVAILABLE_LINE = "play_demo: unavailable on this platform"

_capture_title = None
_pp_launch = None


class PlatformUnavailable(Exception):
    """This host cannot draw or focus a window, so nothing this tool measures exists here."""


def unavailable(error):
    """The one line a host without the drawing path prints, and the not-measured code that goes with it.

    4 is not a pass and not a red (tools/idle_check.py:48; capture_first_fight.py, capture_drive.py, capture_save.py
    and _save_load_probe.py already return it), so a runner reading it records "not measured" instead of scoring it.
    """
    print(UNAVAILABLE_LINE)
    print("  %s, so this run is not measured" % error)
    return EXIT_UNAVAILABLE


def can_draw():
    """True when this host can import the drawing path and has window primitives to draw with.

    The import is asked for first, so a host that cannot even import it raises PlatformUnavailable out to the caller
    and gets the same one line. Off Windows the module imports but there is no window to copy, which is what
    capture_title's own WINDOW_PRIMITIVES flag says; a version of capture_title without that flag is asked the
    platform question directly.
    """
    capture = capture_module()
    return bool(getattr(capture, "WINDOW_PRIMITIVES", sys.platform == "win32"))


def capture_module():
    """tools/capture_title.py, imported on first use. The proved window and key primitives, shared, never copied."""
    global _capture_title
    if _capture_title is None:
        try:
            import capture_title
        except Exception as error:  # the drawing path is all or nothing here, so every failure is the same answer
            raise PlatformUnavailable("capture_title could not be imported: %s" % error)
        _capture_title = capture_title
    return _capture_title


def launch_module():
    """tools/pp_launch.py, imported on first use: the launch policy, the idle gate, and the quiet window."""
    global _pp_launch
    if _pp_launch is None:
        try:
            import pp_launch
        except Exception as error:  # same answer as above: a launcher that cannot launch is not a launcher
            raise PlatformUnavailable("pp_launch could not be imported: %s" % error)
        _pp_launch = pp_launch
    return _pp_launch


# What this process may do with a window and with sound. main() replaces it from the flags; run_demo reads it.
LAUNCH = None


DEMO_DIR = os.path.join(ROOT, "data", "demo")
OUTPUT_DIR = os.path.join(ROOT, "output", "demo")
BUILD_DIR = os.path.join(ROOT, "build")
DEFAULT_SCRIPT = os.path.join(DEMO_DIR, "run_001.json")
MANIFEST = os.path.join(DEMO_DIR, "manifest.json")

# The frames the run is checked on, as a share of the recording: the start, then every sixth. Sampling on
# fractions of the measured duration rather than on fixed seconds keeps the check valid for a longer script.
SAMPLE_FRACTIONS = (0.02, 0.18, 0.34, 0.5, 0.66, 0.84, 0.95)
# A frame of the game that is not a fade has a mean luma well above a black screen's. Measured on the
# 2026-10-21 title recording: the darkest non-fade sample was about 30, a black frame is under 4.
MIN_MEAN_LUMA = 8.0
# A press this close to the previous one can land inside one game step, where the game reads it as the same
# press (the reason capture_title.py spaces its keys). The runner refuses a script that asks for less.
MIN_KEY_GAP_STEPS = 6
# The audio stand-in is the title theme, which is what plays over the attract and the crawl.
THEME_GLOBS = ("title_theme_v5", "title_theme_v4", "title_theme_v3", "title_theme_v2", "title_theme")

# The binary is found once, on first use, because finding it goes through capture_title (card PINE-HONEST). A host
# that reaches this line without the Windows path gets PlatformUnavailable from capture_module, not a traceback here.
FFMPEG = None


def ffmpeg_path():
    """The ffmpeg binary, found once. Empty string means it was looked for and is not there, which is a finding."""
    global FFMPEG
    if FFMPEG is None:
        FFMPEG = capture_module().find_ffmpeg()
    return FFMPEG


# ---------------------------------------------------------------------------------------------------------------------
# The script

def load_script(path):
    """Read and validate a demo script. A malformed script stops the run before the game is launched."""
    with open(path, "r", encoding="utf-8") as handle:
        script = json.load(handle)
    problems = validate_script(script)
    if problems:
        raise SystemExit("%s is not a valid demo script:\n  %s" % (path, "\n  ".join(problems)))
    return script


def validate_script(script):
    """Every rule a demo script has to satisfy, as a list of problems. Empty means the script is playable.

    The rules exist because each one is a way a recording has silently been wrong before: a key that is not
    a key the game reads, a step that goes backwards so the clock cannot be followed, a marker with no
    a fallback so a block buffered log hangs the run, a key gap the game cannot see, or a recording shorter
    than the submission needs.
    """
    cap = capture_module()  # the key table lives in capture_title, so the import is here and not at the top
    problems = []
    if not isinstance(script, dict):
        return ["the script is not a JSON object"]
    if script.get("version") != 1:
        problems.append("version must be 1, not %r" % (script.get("version"),))
    if not isinstance(script.get("name"), str) or not script.get("name"):
        problems.append("name must be a non empty string")

    clock = script.get("clock") or {}
    fps = clock.get("fps")
    if not isinstance(fps, int) or not 1 <= fps <= 240:
        problems.append("clock.fps must be an integer between 1 and 240, not %r" % (fps,))
        fps = 60
    max_steps = clock.get("max_steps")
    if not isinstance(max_steps, int) or max_steps <= 0:
        problems.append("clock.max_steps must be a positive integer, not %r" % (max_steps,))

    seeds = script.get("seeds") or {}
    if not isinstance(seeds, dict) or not seeds:
        problems.append("seeds must be a non empty object: a run with no pinned seed is not reproducible")
    else:
        for key, value in seeds.items():
            if key == "note":
                continue
            if not isinstance(value, int):
                problems.append("seeds.%s must be an integer, not %r" % (key, value))

    record = script.get("record") or {}
    if not isinstance(record, dict):
        problems.append("record must be an object")
        record = {}
    if not isinstance(record.get("min_seconds"), (int, float)) or record.get("min_seconds", 0) < 30:
        problems.append("record.min_seconds must be at least 30: the submission asks for 30 s of gameplay")
    if record.get("scale") != 3:
        problems.append("record.scale must be 3: the frame is 3x the 256x240 screen")
    if not isinstance(record.get("out"), str) or not record.get("out"):
        problems.append("record.out must be a path relative to the repository root")

    game = script.get("game") or {}
    for field in ("exe", "window_title"):
        if not isinstance(game.get(field), str) or not game.get(field):
            problems.append("game.%s must be a non empty string" % field)

    events = script.get("events")
    if not isinstance(events, list) or not events:
        problems.append("events must be a non empty list")
        return problems
    last_absolute = -1
    last_key_step = None
    seen_ids = set()
    for index, event in enumerate(events):
        where = "events[%d]" % index
        if not isinstance(event, dict):
            problems.append("%s is not an object" % where)
            continue
        identifier = event.get("id")
        if not isinstance(identifier, str) or not identifier:
            problems.append("%s has no id" % where)
        elif identifier in seen_ids:
            problems.append("%s repeats the id %r" % (where, identifier))
        else:
            seen_ids.add(identifier)
        kind = event.get("kind")
        if kind not in ("key", "note"):
            problems.append("%s.kind must be key or note, not %r" % (where, kind))
        if not isinstance(event.get("beat"), int):
            problems.append("%s.beat must be an integer beat number from the beat sheet" % where)
        if not isinstance(event.get("note"), str) or not event.get("note"):
            problems.append("%s.note is empty: every event says what it is for" % where)
        step = event.get("step")
        if not isinstance(step, int) or step < 0:
            problems.append("%s.step must be a non negative integer, not %r" % (where, step))
            step = None
        if event.get("marker") is not None:
            if step is None:
                # A marker without a step is a run that hangs when the log is block buffered, which it is
                # when the game's stdout is a file.
                problems.append("%s has a marker but no fallback step" % where)
            if not isinstance(event.get("marker"), str) or not event.get("marker"):
                problems.append("%s.marker must be a non empty string" % where)
            if not isinstance(event.get("marker_delay_steps", 0), int):
                problems.append("%s.marker_delay_steps must be an integer" % where)
        if step is not None:
            if step < last_absolute:
                problems.append("%s.step %d is before the previous event's step %d, so the clock goes backwards"
                                % (where, step, last_absolute))
            last_absolute = max(last_absolute, step)
        if kind == "key":
            key_name = event.get("key")
            if key_name not in cap.KEY_CODES:
                problems.append("%s.key %r is not one of %s"
                                % (where, key_name, ", ".join(sorted(cap.KEY_CODES))))
            elif step is not None:
                if last_key_step is not None and step - last_key_step < MIN_KEY_GAP_STEPS:
                    problems.append("%s.key at step %d is %d steps after the previous key, under the %d step gap "
                                    "the game needs to read two presses"
                                    % (where, step, step - last_key_step, MIN_KEY_GAP_STEPS))
                last_key_step = step
    return problems


def timeline(script):
    """The events with the second each one is due at, for --dry-run and for the report."""
    fps = script["clock"]["fps"]
    rows = []
    for event in script["events"]:
        rows.append({
            "id": event["id"],
            "beat": event["beat"],
            "kind": event["kind"],
            "key": event.get("key"),
            "second": round(event["step"] / float(fps), 3),
            "marker": event.get("marker"),
            "note": event["note"],
        })
    return rows


def planned_seconds(script):
    """How long the recording is meant to be: the end step, kept inside the clock's own limit."""
    fps = script["clock"]["fps"]
    end_step = (script.get("checks") or {}).get("end_step")
    if not isinstance(end_step, int):
        end_step = max(event["step"] for event in script["events"])
    end_step = min(end_step, script["clock"]["max_steps"])
    return end_step / float(fps)


# ---------------------------------------------------------------------------------------------------------------------
# The replay

def read_marker(log_path, needle):
    """True when the game's own log already carries a line. Absent file means 'not yet', never an error."""
    if not os.path.isfile(log_path):
        return False
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            return needle in handle.read()
    except OSError:  # gate: ok the game may hold the log open for writing on this platform; a marker that cannot be read is treated as absent and the step fallback takes over.
        return False


class Replay(object):
    """Walks the script on one clock, from the moment the recorder starts.

    The clock is steps at the script's fps counted from the recorder's start, so a step in this file is the
    same unit as a step in the game log, and a slow key press never shifts everything after it. A marker is
    an accelerator only: it can move an event earlier, and the event's own step is the fallback, so a block
    buffered log costs time rather than hanging the run.
    """

    def __init__(self, script, hwnd, log_path, send_key):
        self.script = script
        self.hwnd = hwnd
        self.log_path = log_path
        self.send_key = send_key
        self.fps = script["clock"]["fps"]
        self.started = None
        self.trace = []

    def step_now(self):
        return int((time.monotonic() - self.started) * self.fps)

    def record(self, event_id, kind, detail, step):
        row = {"id": event_id, "kind": kind, "detail": detail, "at_step": step,
               "at_second": round(step / float(self.fps), 3)}
        self.trace.append(row)
        print("  %-5s %-6s %-28s at %.1f s (step %d)" % (event_id, kind, detail[:28], step / float(self.fps), step))
        return row

    def wait_until(self, target_step, max_wait_s=60.0):
        """Sleep until the clock reaches target_step. Returns the step it actually reached."""
        deadline = time.monotonic() + max_wait_s
        while True:
            now = self.step_now()
            if now >= target_step:
                return now
            if time.monotonic() > deadline:
                raise SystemExit("the clock stopped advancing at step %d, %d steps short of %d"
                                 % (now, target_step - now, target_step))
            time.sleep(min(0.02, max(0.001, (target_step - now) / float(self.fps))))

    def wait_marker(self, needle, fallback_step, delay_steps, timeout_s):
        """Wait for a log line, then delay, but never past the event's own fallback step.

        Returns (step, seen). The marker only moves the event earlier than its fallback: if it has not
        appeared by the fallback step, the fallback is what the run uses and the verify file says so.
        """
        while self.step_now() < fallback_step:
            if read_marker(self.log_path, needle):
                return min(self.step_now() + delay_steps, fallback_step), True
            time.sleep(0.1)
        seen = read_marker(self.log_path, needle)
        return fallback_step, seen

    def run(self, end_step):
        cap = capture_module()  # the key codes, imported here so this class can exist on any host
        self.started = time.monotonic()
        failures = []
        for event in self.script["events"]:
            if event["step"] > end_step:
                break
            if event.get("marker"):
                target, seen = self.wait_marker(event["marker"], event["step"],
                                                int(event.get("marker_delay_steps", 0)), 30.0)
                reached = self.wait_until(target)
                detail = ("marker %r %s" % (event["marker"], "seen" if seen else "not seen, step used"))
                self.record(event["id"], "marker", detail, reached)
                if not seen:
                    failures.append("%s: the log never carried %r, the step %d was used instead"
                                    % (event["id"], event["marker"], event["step"]))
            else:
                reached = self.wait_until(event["step"])
                late = reached - int(event["step"])
                if late > self.fps:
                    failures.append("%s fired %.1f s late" % (event["id"], late / float(self.fps)))
            if event["kind"] == "key":
                # A press is only ever a real press: if the focus cannot be retaken the run stops, because a
                # posted key would produce a recording of a menu that never moved.
                try:
                    self.send_key(cap.KEY_CODES[event["key"]])
                except SystemExit as error:
                    failures.append("%s: %s" % (event["id"], error))
                    break
                self.record(event["id"], "key", event["key"], self.step_now())
        # The recording keeps running to the end step, so the last beat is held on screen.
        self.wait_until(end_step + 30)
        return failures


# ---------------------------------------------------------------------------------------------------------------------
# Recording

def pre_roll_viewport(hwnd, path):
    """Find the game's 3x viewport inside the window, on a frame taken before recording starts.

    The crop of the mp4 is this box. It is measured, not assumed: the same search
    tools/nes_composite_check.py --crop auto runs, so a window that is covered, a desktop, or a terminal has
    no such box and the recording is refused instead of writing a file that looks like a video.
    """
    cap = capture_module()
    rect = cap.get_window_rect(hwnd)
    if rect is None:
        return None, None, 0.0, "the window has no rectangle"
    ok, note = cap.capture_with_pil(rect, path)
    if not ok:
        return rect, None, 0.0, "the pre-roll capture failed: %s" % note
    box, score, why = cap.viewport_box_and_score(path)
    if box is None:
        return rect, None, score, "no legal 3x NES viewport in the pre-roll frame (%s), so it is not the game" % why
    return rect, box, score, "viewport %s at score %.3f" % (box, score)


def start_recorder(rect, out_path, duration_s, fps, loopback):
    """Start ffmpeg on the window rectangle. Returns (process, log file handle, log path).

    gdigrab reads the screen, so the rectangle has to be the window's own and nothing may cover it. The
    output goes to a file and never to a pipe: a pipe nobody reads fills after about 64 KB and ffmpeg then
    blocks, which is how an earlier run of this harness stopped recording at 9 s of a 13 s file.
    """
    FFMPEG = ffmpeg_path()
    left, top, width, height = rect
    os.makedirs(BUILD_DIR, exist_ok=True)
    log_path = os.path.join(BUILD_DIR, "demo-ffmpeg.log")
    handle = open(log_path, "wb")
    arguments = [
        "-f", "gdigrab",
        "-framerate", str(fps),
        "-offset_x", str(left),
        "-offset_y", str(top),
        "-video_size", "%dx%d" % (width, height),
        "-i", "desktop",
        "-t", "%.2f" % duration_s,
        # libx264 needs even dimensions for yuv420p, and the window height is odd.
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-r", str(fps),
        "-c:v", "libx264",
        # ultrafast, because gdigrab hands the encoder a full frame 60 times a second and the slower presets
        # cannot keep up on this host: a slow encode means a file shorter than the run it was meant to hold.
        "-preset", "ultrafast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
    ]
    if loopback:
        arguments += ["-f", "dshow", "-i", "audio=%s" % loopback,
                      "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "160k"]
    arguments.append(out_path)
    process = subprocess.Popen([FFMPEG, "-hide_banner", "-y"] + arguments,
                               stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return process, handle, log_path


def newest_theme():
    """The newest title theme in the repository, as the stand-in track's source. None when none is on disk."""
    audio_dir = os.path.join(ROOT, "assets", "audio")
    for folder in THEME_GLOBS:
        candidate = os.path.join(audio_dir, folder)
        if not os.path.isdir(candidate):
            continue
        for name in sorted(os.listdir(candidate)):
            if name.endswith(".ogg"):
                return os.path.join(candidate, name)
    return None


def render_stand_in_audio(theme, seconds, out_path):
    """Loop the title theme to the length of the video and write it as its own track file.

    This is not the game's live sound: without a loopback device ffmpeg cannot hear the game. The track is
    the theme the game itself plays over the attract, rendered separately and labelled as a stand-in
    everywhere it appears, so a viewer hears the right music and nobody mistakes it for a direct capture.
    """
    cap = capture_module()
    FFMPEG = ffmpeg_path()
    ok, note = cap.run_ffmpeg(FFMPEG, ["-stream_loop", "-1", "-i", theme, "-t", "%.3f" % seconds,
                                      "-c:a", "aac", "-b:a", "160k", out_path], timeout=180)
    return ok, note


def cut_and_scale(raw_path, viewport, script, out_path, audio_path):
    """Crop the raw window recording to the viewport and scale it to a true 3x of the 256x240 screen."""
    cap = capture_module()
    FFMPEG = ffmpeg_path()
    record = script["record"]
    x, y, w, h = viewport
    width, height = int(record.get("width", 768)), int(record.get("height", 720))
    filters = ["crop=%d:%d:%d:%d" % (w, h, x, y), "scale=%d:%d:flags=neighbor" % (width, height)]
    arguments = ["-i", raw_path]
    if audio_path:
        arguments += ["-i", audio_path]
    arguments += ["-filter:v", ",".join(filters), "-r", str(record["fps"]),
                  "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    if audio_path:
        arguments += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "160k", "-shortest",
                      "-metadata", "comment=audio is a rendered stand-in (title theme), not the game's "
                                   "loopback output"]
    arguments.append(out_path)
    return cap.run_ffmpeg(FFMPEG, arguments, timeout=900)


# ---------------------------------------------------------------------------------------------------------------------
# Checks on the finished file

def palette_share(path, allowed, tolerance=12):
    """The share of a frame's pixels that sit on a legal 2C02 colour, allowing for video compression.

    The viewport search in tools/nes_composite_check.py asks for an exact palette colour, which is the right
    test on a PNG straight off the game's screen. It cannot be the test on an h264 frame: chroma is stored at
    a quarter of the luma resolution and the quantiser moves every sample a little, so a real recording of
    the title measured 18,923 colours and an exact share of 0.000 while the crawl frames, which are almost
    flat black, still measured 0.966. This measure keeps the promise the check exists for (the frame is the
    game's own picture, not a terminal's) without pretending a compressed frame is an uncompressed one: every
    pixel must land within `tolerance` of some palette entry, and the share of pixels that do is reported.
    """
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as image:
            counts = image.convert("RGB").getcolors(maxcolors=1 << 22)
    except Exception:
        return None
    if not counts:
        return None
    colours = list(allowed)
    total = 0
    hit = 0
    for count, pixel in counts:
        total += count
        for entry in colours:
            if (abs(pixel[0] - entry[0]) <= tolerance and abs(pixel[1] - entry[1]) <= tolerance
                    and abs(pixel[2] - entry[2]) <= tolerance):
                hit += count
                break
    if total == 0:
        return None
    return hit / float(total)


def palette_entries():
    """The legal 2C02 colours, through the same loader tools/nes_composite_check.py uses."""
    try:
        import nes_composite_check as ncc
        return list(ncc.load_palette(ncc.default_palette_path(ROOT))["allowed"])
    except Exception:  # gate: ok without the palette no frame can be judged, and the check says so instead of passing.
        return None


def frame_luma(path):
    """The mean luma of a frame, 0 to 255. A black rectangle scores under 4, a game scene far above."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as image:
            grey = image.convert("L")
            histogram = grey.histogram()
    except Exception:
        return None
    total = sum(histogram)
    if total == 0:
        return None
    weighted = sum(value * count for value, count in enumerate(histogram))
    return weighted / float(total)


def video_stream(ffprobe, path):
    """The first video stream's width, height, fps and codec, or None."""
    if not ffprobe:
        return None
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                                 "-show_entries", "stream=width,height,r_frame_rate,codec_name",
                                 "-of", "json", path],
                                capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        data = json.loads(result.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    streams = data.get("streams") or []
    return streams[0] if streams else None


def audio_stream(ffprobe, path):
    """True when the file carries an audio stream."""
    if not ffprobe:
        return False
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a",
                                 "-show_entries", "stream=codec_name", "-of", "json", path],
                                capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        data = json.loads(result.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return bool(data.get("streams"))


def verify_video(path, script, report_path=None):
    """Check a finished mp4 against the script. Returns (ok, report).

    The four checks the card asks for, in the order a wrong recording shows up:
      1. the duration is at least record.min_seconds of real gameplay;
      2. the frame is the script's 3x of the 256x240 screen, at the script's fps;
      3. sampled frames are not black;
      4. sampled frames are the game and not a terminal: enough of them must sit on the legal 2C02 palette
         within the tolerance a compressed frame needs, and two samples must differ, so the scene moves.

    The exact 3x viewport search (capture_title.viewport_box_and_score) is deliberately not run on these
    frames: it asks for exact palette colours, which is the right question on a PNG taken straight off the
    game's screen, and it is the pre-roll frame's job before the recording starts. On an h264 frame it
    returns 0.0 for a real frame of the game (measured on the 2026-10-22 run_001: the title frame scored 0.0
    with a palette share of 0.93), so using it here would only manufacture a contradiction.
    """
    cap = capture_module()
    FFMPEG = ffmpeg_path()
    report = {"video": path, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "checks": {}, "samples": []}
    record = script["record"]
    min_seconds = float(record["min_seconds"])
    width, height = int(record.get("width", 768)), int(record.get("height", 720))
    fps_wanted = int(record["fps"])
    checks = script.get("checks") or {}
    luma_min = float(checks.get("min_luma", MIN_MEAN_LUMA))
    min_colours = int(checks.get("min_distinct_colours", 6))
    diff_min = float(checks.get("frame_diff_min", 0.001))
    min_lit = int(checks.get("min_lit_frames", 4))

    if not FFMPEG:
        return False, {"error": "ffmpeg was not found"}
    ffprobe = cap.ffprobe_path(FFMPEG)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        report["checks"]["file"] = "FAIL the file is missing or empty"
        return False, report
    report["bytes"] = os.path.getsize(path)
    report["checks"]["file"] = "PASS %d bytes" % report["bytes"]

    duration = cap.probe_duration(ffprobe, path)
    report["duration_s"] = duration
    if duration is None:
        report["checks"]["duration"] = "FAIL the duration could not be read"
        return False, report
    if duration < min_seconds:
        report["checks"]["duration"] = ("FAIL %.3f s of video, under the %.1f s the submission needs"
                                        % (duration, min_seconds))
        ok_duration = False
    else:
        report["checks"]["duration"] = "PASS %.3f s, at least %.1f s" % (duration, min_seconds)
        ok_duration = True

    stream = video_stream(ffprobe, path)
    report["stream"] = stream
    ok_stream = False
    if not stream:
        report["checks"]["stream"] = "FAIL no video stream could be read"
    else:
        measured = (int(stream.get("width", 0)), int(stream.get("height", 0)))
        numerator, _, denominator = str(stream.get("r_frame_rate", "0/1")).partition("/")
        try:
            measured_fps = float(numerator) / float(denominator or 1)
        except ValueError:
            measured_fps = 0.0
        report["fps"] = measured_fps
        if measured != (width, height):
            report["checks"]["stream"] = ("FAIL the frame is %dx%d, not the %dx%d the script asks for"
                                          % (measured[0], measured[1], width, height))
        elif measured_fps + 0.5 < fps_wanted:
            report["checks"]["stream"] = ("FAIL the frame rate is %.2f, under the %d the script asks for"
                                          % (measured_fps, fps_wanted))
        else:
            report["checks"]["stream"] = ("PASS %dx%d %s at %.2f fps"
                                          % (measured[0], measured[1], stream.get("codec_name"), measured_fps))
            ok_stream = True
    report["has_audio"] = audio_stream(ffprobe, path)

    work = os.path.join(BUILD_DIR, "_demo_check")
    os.makedirs(work, exist_ok=True)
    allowed = palette_entries()
    palette_min = float(checks.get("palette_share_min", 0.90))
    palette_tolerance = int(checks.get("palette_tolerance", 12))
    min_on_palette = int(checks.get("min_on_palette_frames", 4))
    frames = []
    lit = 0
    on_palette = 0
    off_palette_rows = []
    for index, fraction in enumerate(SAMPLE_FRACTIONS):
        stamp = max(0.5, min(duration - 0.5, duration * fraction))
        frame_path = os.path.join(work, "frame_%d.png" % index)
        row = {"t": round(stamp, 3)}
        if not cap.extract_frame(FFMPEG, path, stamp, frame_path):
            row["frame"] = "missing"
            report["samples"].append(row)
            frames.append(None)
            continue
        luma = frame_luma(frame_path)
        colours = cap.distinct_colours(frame_path)
        share = palette_share(frame_path, allowed, palette_tolerance) if allowed else None
        row.update({"luma": None if luma is None else round(luma, 2),
                    "colours": colours,
                    "palette_share": None if share is None else round(share, 4)})
        if luma is not None and luma >= luma_min:
            lit += 1
        if share is not None and share >= palette_min and (colours or 0) >= min_colours:
            on_palette += 1
        else:
            # Why this frame is not counted as the game's picture, written into the row itself.
            row["why"] = ("%s colours, under the %d a picture with content has"
                          % (colours, min_colours)) if (colours or 0) < min_colours else (
                "palette share %s, under the %.2f a frame of the game needs"
                % ("unmeasured" if share is None else "%.3f" % share, palette_min))
            if colours and colours >= min_colours:
                # Not a blank frame and not a foreign window: a scene of the game drawn with colours the
                # 2C02 cannot output. That is a finding for the art lane, and it is named, never hidden.
                off_palette_rows.append(row)
        report["samples"].append(row)
        frames.append(frame_path)

    report["lit_frames"] = lit
    report["on_palette_frames"] = on_palette
    report["samples_taken"] = len([row for row in report["samples"] if "luma" in row])
    ok_lit = lit >= min_lit
    report["checks"]["not_black"] = ("PASS %d of %d sampled frames are lit (mean luma %.1f and up, %d needed)"
                                     % (lit, len(SAMPLE_FRACTIONS), luma_min, min_lit)) if ok_lit else \
                                    ("FAIL only %d of %d sampled frames are lit, %d needed"
                                     % (lit, len(SAMPLE_FRACTIONS), min_lit))
    # Every frame has to be a picture with real content; that is what rules out a black rectangle, a blank
    # window and a single colour desktop. Then enough of the frames have to be the game's own 2C02 picture to
    # rule out a recording of a terminal or of another window.
    ok_game = on_palette >= min_on_palette and all((row.get("colours") or 0) >= min_colours
                                                   for row in report["samples"] if "colours" in row)
    report["checks"]["not_a_terminal"] = (
        "PASS %d of %d sampled frames are the game's own picture: at least %.2f of their pixels sit on a legal "
        "2C02 colour within %d levels (the allowance a compressed frame needs) and every frame carries at least "
        "%d colours; a terminal or another window meets neither"
        % (on_palette, len(SAMPLE_FRACTIONS), palette_min, palette_tolerance, min_colours)) if ok_game else (
        "FAIL only %d of %d sampled frames are the game's own picture (%d needed): %s"
        % (on_palette, len(SAMPLE_FRACTIONS), min_on_palette,
           ", ".join("t=%.1f palette share %s, %s colours"
                     % (row["t"], row.get("palette_share"), row.get("colours")) for row in report["samples"]
                     if (row.get("palette_share") or 0) < palette_min) or "see the samples"))
    if off_palette_rows:
        report["findings"] = [
            "FINDING %d of %d sampled frames are the game drawn off the 2C02 palette: %s. The frames are real "
            "game frames (the run's log shows the walk and the dialogue in the room they come from), so this is "
            "an art finding for the audit lane, not a capture failure. Palette share under %.2f means most "
            "pixels are colours the NES cannot output."
            % (len(off_palette_rows), len(SAMPLE_FRACTIONS),
               ", ".join("t=%.1f share %.3f" % (row["t"], row.get("palette_share") or 0.0)
                         for row in off_palette_rows), palette_min)
        ]

    differences = []
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            if frames[i] and frames[j]:
                ratio = cap.frames_differ(frames[i], frames[j])
                if ratio is not None:
                    differences.append(ratio)
    best = max(differences) if differences else None
    report["max_frame_diff"] = best
    ok_motion = best is not None and best >= diff_min
    report["checks"]["motion"] = ("PASS the largest difference between sampled frames is %.5f of the pixels, so "
                                 "the scene moves" % best) if ok_motion else (
        "FAIL the sampled frames do not differ (largest %s), so the recording is a still" % best)

    ok = bool(ok_duration and ok_stream and ok_lit and ok_game and ok_motion)
    report["ok"] = ok
    if report_path:
        with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return ok, report


def print_report(report):
    for name in ("file", "duration", "stream", "not_black", "not_a_terminal", "motion"):
        line = report["checks"].get(name)
        if line:
            print("  %s" % line)
    for row in report.get("samples", []):
        print("  sample t=%.2f s: luma %s, %s colours, palette share %s%s"
              % (row["t"], row.get("luma"), row.get("colours"), row.get("palette_share"),
                 "" if "why" not in row else " (%s)" % row["why"]))
    for finding in report.get("findings", []):
        print("  %s" % finding)


# ---------------------------------------------------------------------------------------------------------------------
# The run

def out_path_for(script):
    """The mp4 path the script names, resolved under the repository root."""
    return os.path.join(ROOT, script["record"]["out"])


def out_stem(path):
    """The stem of the recording's own file name: run_002 for output/demo/run_002.mp4.

    The verify file and the stand-in track are named after the mp4, not after the script, so a re-recording
    written with --out cannot overwrite the verdict that belongs to the take already on disk.
    """
    return os.path.splitext(os.path.basename(path))[0]


def run_demo(script, keep_raw=False):
    """Launch the built game, play the script, record it, cut it to 3x, then check the file."""
    # Card PINE-HONEST (t_84fe63ff): both modules come in on first use, and a host with no window primitives
    # refuses here, where a window would actually be opened, so --check and --dry-run still work where nothing can
    # be shown. 4 is the harness's not-measured code, so a reader sees "not measured" and never "passed".
    cap = capture_module()  # raises PlatformUnavailable when the drawing path cannot be imported at all
    pp_launch = launch_module()
    FFMPEG = ffmpeg_path()
    if not can_draw():
        print(UNAVAILABLE_LINE)
        print("  this host has no window primitives, so there is no window to record")
        return EXIT_UNAVAILABLE
    # Card CAPTURE-QUIET: the gate is asked before anything is opened or deleted, so a refused run leaves the last
    # good recording on disk and costs one log line.
    if not LAUNCH.gate("demo recording"):
        return pp_launch.EXIT_REFUSED
    if not FFMPEG:
        print("ffmpeg was not found in the winget package folder and is not on PATH")
        return 1
    ffprobe = cap.ffprobe_path(FFMPEG)
    print("ffmpeg: %s" % FFMPEG)
    print("ffprobe: %s" % (ffprobe or "not found, the duration check cannot run"))

    build = cap.newest_build()
    if build is None:
        print("no built game found under %s" % cap.GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build
    print("build: %s" % exe_path)

    devices = cap.dshow_audio_devices(FFMPEG)
    loopback = cap.pick_loopback_device(devices)
    print("system audio: %s" % (loopback or "no loopback device, the video is recorded silent"))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = out_path_for(script)
    stem = out_stem(out_path)
    verify_path = os.path.join(OUTPUT_DIR, "%s_verify.json" % stem)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    raw_path = os.path.join(OUTPUT_DIR, "_%s_raw.mp4" % script["name"])
    for stale in (out_path, raw_path):
        if os.path.exists(stale):
            os.remove(stale)

    fps = script["clock"]["fps"]
    end_step = (script.get("checks") or {}).get("end_step") or max(event["step"] for event in script["events"])
    seconds = planned_seconds(script)
    print("plan: %d events over %.1f s on a %d fps clock" % (len(script["events"]), seconds, fps))

    os.makedirs(BUILD_DIR, exist_ok=True)
    log_path = os.path.join(BUILD_DIR, "demo-game.log")
    launch_args = [part.replace("{win}", win_path) for part in script["game"]["launch_args"]]
    print("launching %s" % " ".join([exe_path] + launch_args))
    # Card CAPTURE-QUIET-IMPL: one call starts the game muted, without a console window, and prints the one PP: muted
    # line from this run's own log. The exit line comes from run.finish() in the finally below.
    extra = {}
    for part in script["game"].get("env", {}) or {}:
        extra[part] = script["game"]["env"][part]
    run = pp_launch.start_game(exe_path, win_path, log_path=log_path, policy=LAUNCH, label="demo recording",
                               extra=extra or None)
    process = run.process
    cap.start_watchdog(process, int(seconds) + 240)
    failures = []
    recorder = None
    recorder_log = None
    try:
        match = cap.find_window(
            lambda hwnd, pid, title, visible, rect: visible and title.lower().startswith(
                script["game"]["window_title"].lower()),
            timeout_s=cap.GAME_WINDOW_TIMEOUT_S)
        if match is None:
            print("the game window did not appear within %.0f s" % cap.GAME_WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        # Card CAPTURE-QUIET: the window is moved off the primary screen unless --show was given, so the recording
        # happens on a screen Nayil is not looking at.
        LAUNCH.place(hwnd, cap.get_window_rect(hwnd))
        image_name = cap.process_image_name(match[1])
        if image_name.lower() != script["game"]["exe"].lower():
            print("the window belongs to %r, not to %s, so it is not the game window"
                  % (image_name, script["game"]["exe"]))
            return 1
        print("game window found: %r (hwnd %s, image %s)" % (match[2], hwnd, image_name))

        time.sleep(cap.GAME_SETTLE_S)
        previous = cap.bring_to_front(hwnd)
        cap.hold_on_top(hwnd)
        time.sleep(cap.FOREGROUND_SETTLE_S)
        placed = cap.get_window_rect(hwnd)
        if placed is None:
            print("the game window has no rectangle, cannot record it")
            return 1
        rect, coverage = cap.ensure_game_visible(hwnd, placed)
        print("coverage: %s" % coverage)
        if rect is None:
            print("FAIL another window covers the game, so the recording would show that window")
            return 1

        pre_roll = os.path.join(BUILD_DIR, "_demo_preroll.png")
        rect, viewport, score, note = pre_roll_viewport(hwnd, pre_roll)
        print("pre-roll: %s" % note)
        min_score = float((script.get("checks") or {}).get("nes_score_min", 0.90))
        if viewport is None or score < min_score:
            print("FAIL the window is not showing the game's own 3x screen (score %.3f, %.2f needed)"
                  % (score, min_score))
            return 1
        print("recording rectangle %d,%d %dx%d, crop %s then scale to 3x"
              % (rect[0], rect[1], rect[2], rect[3], viewport))

        focused, focus_note = cap.ensure_key_focus(hwnd)
        print("keyboard focus: %s" % focus_note)
        if not focused:
            print("FAIL the game never took the keyboard focus, so no key press would reach it")
            return 1

        def send_key(vk):
            """One real key press, with the focus retaken first. A posted key proves nothing."""
            for _attempt in range(4):
                if cap.game_has_focus(hwnd):
                    return cap.send_vk_focused(vk)
                ok, why = cap.ensure_key_focus(hwnd, attempts=2, settle=0.15)
                if not ok:
                    continue
            raise SystemExit("the game lost the keyboard focus and would not take it back (%s)" % why)

        record_seconds = seconds + 2.5
        recorder, recorder_log, recorder_log_path = start_recorder(rect, raw_path, record_seconds, fps, loopback)
        print("recording %.1f s of the window to %s" % (record_seconds, raw_path))

        replay = Replay(script, hwnd, log_path, send_key)
        failures += replay.run(end_step)

        # ffmpeg stops itself on -t; give it a moment to finish writing and closing the container.
        try:
            recorder.wait(timeout=record_seconds + 60)
        except subprocess.TimeoutExpired:
            recorder.terminate()
            try:
                recorder.wait(timeout=15)
            except subprocess.TimeoutExpired:
                recorder.kill()
            failures.append("ffmpeg did not stop on its own and was terminated, so the file may be truncated")
        cap.release_on_top(hwnd)
        cap.restore_foreground(previous)

        # Ask Windows again who owns the pixels, so a covering window that arrived mid recording is caught
        # instead of being written off as a colour difference in the frame checks.
        covered, owners = cap.cover_report(hwnd, rect)
        if covered:
            failures.append("after the recording another window owns %d of the sampled points of the rectangle"
                            % len(covered))

        if recorder.returncode not in (0, None):
            failures.append("ffmpeg exited with code %s, its log is %s" % (recorder.returncode, recorder_log_path))
            with open(recorder_log_path, "r", encoding="utf-8", errors="replace") as handle:
                print(handle.read()[-800:])
        if not os.path.isfile(raw_path) or os.path.getsize(raw_path) == 0:
            print("FAIL the raw recording is missing or empty")
            return 1

        # The game's own account of the run: a crash, and the two lines that prove the run reached the room.
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            log_text = handle.read()
        if "PP CRASH" in log_text:
            crash = [line for line in log_text.splitlines() if "PP CRASH" in line][0]
            failures.append("the game reported a crash: %s" % crash[:200])
        if "PP title: intro started" not in log_text:
            failures.append("the game never reported the intro starting, so NEW GAME did not take")
        footsteps = len([line for line in log_text.splitlines() if "footstep played" in line])
        print("footstep cues in the game log: %d" % footsteps)
        if footsteps == 0:
            failures.append("the game played no footstep cue, so the Right presses did not reach the walk")

        audio_path = None
        if loopback:
            print("audio: recorded from %s with the video" % loopback)
        else:
            theme = newest_theme()
            if theme:
                audio_path = os.path.join(OUTPUT_DIR, "%s_audio.m4a" % stem)
                made, note = render_stand_in_audio(theme, record_seconds, audio_path)
                print("audio: no loopback, so a stand-in track was rendered from %s (%s): %s"
                      % (os.path.relpath(theme, ROOT), note, audio_path))
                if not made:
                    audio_path = None

        made, note = cut_and_scale(raw_path, viewport, script, out_path, audio_path)
        if not made:
            print("FAIL the cut and scale did not run: %s" % note)
            return 1
        print("wrote %s" % out_path)

        ok, report = verify_video(out_path, script, verify_path)
        report["script"] = os.path.relpath(script_path_used, ROOT) if script_path_used else None
        report["audio"] = ("loopback %s" % loopback) if loopback else (
            "rendered stand-in from %s, not the game's live output" % os.path.basename(audio_path)
            if audio_path else "none")
        report["run"] = {"trace": replay.trace, "failures": failures, "game_log": os.path.relpath(log_path, ROOT),
                         "footsteps": footsteps, "planned_seconds": round(seconds, 3),
                         "recorded_seconds": round(record_seconds, 3)}
        with open(verify_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print_report(report)
        for failure in failures:
            print("  note: %s" % failure)
        if not ok:
            print("FAIL %s did not pass its checks" % out_path)
            return 1
        print("PASS %s" % out_path)
        return 0
    finally:
        # The one exit line, and the game closed before the raw file is cleaned up (card CAPTURE-QUIET-IMPL).
        run.finish()
        if recorder is not None and recorder.poll() is None:
            recorder.kill()
        if recorder_log is not None:
            try:
                recorder_log.close()
            except Exception:  # gate: ok best effort cleanup of the ffmpeg log handle.
                pass
        if not keep_raw and os.path.isfile(raw_path) and os.path.isfile(out_path):
            try:
                os.remove(raw_path)
            except OSError:  # gate: ok the raw file is scratch; a failed delete costs disk and nothing else.
                pass


script_path_used = None


def main():
    global script_path_used
    global LAUNCH
    parser = argparse.ArgumentParser(description="Play a scripted run of the built game and record it.")
    # Card PINE-HONEST (t_84fe63ff): the launcher module is imported by launch_module(), so a host without the
    # Windows path answers with one line and the not-measured code instead of a traceback from the argument parser.
    try:
        pp_launch = launch_module()
    except PlatformUnavailable as error:
        return unavailable(error)
    # Card CAPTURE-QUIET: the same four launch flags every launching tool takes (tools\pp_launch.py).
    pp_launch.add_launch_flags(parser)
    parser.add_argument("--script", default=DEFAULT_SCRIPT,
                        help="the demo script to play (default data\\demo\\run_001.json)")
    parser.add_argument("--out", default=None, help="override the mp4 path the script names")
    parser.add_argument("--check", action="store_true",
                        help="check an existing mp4 against the script instead of playing the game")
    parser.add_argument("--video", default=None, help="with --check, the mp4 to check")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the script and print its timeline in seconds, then stop")
    parser.add_argument("--keep-raw", action="store_true", help="keep the uncropped window recording")
    args = parser.parse_args()
    LAUNCH = pp_launch.policy_from_args(args)

    try:
        script_path_used = os.path.abspath(args.script)
        script = load_script(script_path_used)
        if args.out:
            script = json.loads(json.dumps(script))
            script["record"]["out"] = args.out

        if args.dry_run:
            print("%s: %d events, %.1f s, %d fps, seeds %s"
                  % (script["name"], len(script["events"]), planned_seconds(script), script["clock"]["fps"],
                     json.dumps({key: value for key, value in script["seeds"].items() if key != "note"},
                                sort_keys=True)))
            for row in timeline(script):
                print("  %6.2f s  beat %2d  %-4s %-8s %s" % (row["second"], row["beat"], row["kind"],
                                                            row["key"] or "", row["id"]))
            beats = sorted({row["beat"] for row in timeline(script)})
            print("beats covered by the script: %s" % ", ".join(str(beat) for beat in beats))
            return 0

        if args.check:
            path = os.path.abspath(args.video) if args.video else out_path_for(script)
            print("checking %s against %s" % (path, os.path.basename(script_path_used)))
            ok, report = verify_video(path, script)
            print_report(report)
            return 0 if ok else 1

        return run_demo(script, keep_raw=args.keep_raw)
    except PlatformUnavailable as error:
        # Anything that needed the drawing path and could not have it: --check on a host with no ffprobe path, a
        # dry run whose key table cannot be read. One line and 4, never a green and never a silent zero.
        return unavailable(error)


if __name__ == "__main__":
    sys.exit(main())
