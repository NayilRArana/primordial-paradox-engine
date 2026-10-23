#!/usr/bin/env python3
"""capture_drive.py: prove room rm_pp_drive in the running game, shot by shot, and check one frame against the NES rules.

Card R21a. The room draws the twelve shots of knowledge/DRIVE-SHOT-LIST.md with placeholder art, and with
PP_DRIVE_CAPTURE set it writes one PNG of its own frame per shot from inside its draw (pp_drive.gml), so the proof is
the game's own pixels and not a screen copy of whatever window sits on top of it.

What this tool does, in order:
  1. opens the built game through the one launch policy (tools/pp_launch.py): PP_MUTE=1, the idle gate, the window off
     the primary screen (card CAPTURE-QUIET, ruling D9). --sound and --show and --force are the same flags every
     launching tool takes. It refuses a build that is older than the game source, because a run then proves the old
     exe and not this source (card t_89d60fe5); --allow-stale is the deliberate override;
  2. sets PP_DRIVE_ROOM and PP_DRIVE_CAPTURE in the child environment, so the frame moves to rm_pp_drive and the film
     plays at the capture clock;
  3. waits for the game's own log to carry "PP: muted", then waits for the twelve frames and closes the game;
  4. checks the twelve frames are twelve different pictures (the gantry sign at 55 has to be in shot 3), that none of
     them carries more than 16 colours, and runs the existing NES tool on the shot 3 crop and on a whole frame.

Nothing here invents a shot or a number: the shot ids, the durations and the sign the check asks for are read from the
frames and the log the run itself wrote.

Usage:
    python tools\\capture_drive.py                build the game first, then prove the room
    python tools\\capture_drive.py --show         leave the window where it is (a person at the keyboard)
    python tools\\capture_drive.py --force        skip the idle gate (a person's deliberate override)
    python tools\\capture_drive.py --allow-stale  prove the built game even though the source is newer than it
    python tools\\capture_drive.py --no-launch    re-check the frames from an earlier run, without opening the game

Exit codes:
    0  twelve frames, at least six distinct shots, the sign at 55, the muted line, and the colour checks passed
    1  a check failed, or the build is older than the game source (run tools\\run.ps1 and try again)
    3  the watchdog fired
    4  the idle gate refused to open a window: the user had input in the last three minutes
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import capture_title as cap  # noqa: E402  the proved window primitives, imported rather than copied
import pp_launch  # noqa: E402  the launch policy: PP_MUTE=1, the idle gate, the quiet window (card CAPTURE-QUIET)

OUTPUT_DIR = os.path.join(ROOT, "output")
BUILD_DIR = os.path.join(ROOT, "build")
GAME_LOG = os.path.join(BUILD_DIR, "capture-drive-game.log")
# The game writes its own frames beside its save area; that is the folder the runtime derives from the game name, and
# tools/capture_title.py reads the ship and title frames from the same place.
GAME_FRAME_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "PrimordialParadox")
FRAME_GLOB = "pp_drive_shot_*.png"
# One frame per shot, twelve shots: knowledge/DRIVE-SHOT-LIST.md section 2.
SHOT_COUNT = 12
# The card's check asks for at least six distinct shots, so the run has to beat that number, not only reach it.
MIN_DISTINCT = 6
# The gantry sign at 55 miles is shot 3 (section 5 of the shot list). Its frame is the one the NES tool is pointed at.
SIGN_SHOT = 3
SIGN_MILES = "55"
# One screen may show 16 colours (spec 13 rule 2), and the NES ceiling is 25. The card asks the stricter number.
MAX_COLOURS = 16
# The frame the sign sits in: the plate is drawn at y 60 to 95, x from 24 (pp_drive.gml, pp_drive_gantry_sign). Both
# sides are a multiple of 8, because the NES tool cuts its picture into 8x8 tiles and refuses a size it cannot cut.
SIGN_CROP = (16, 48, 208, 104)
# Waiting room for the run: the capture clock holds each shot 24 steps, so twelve shots are 288 frames (4.8 s) plus the
# window's own start up. The limits are generous on purpose and the watchdog still ends a stuck run.
FRAMES_TIMEOUT_S = 60.0
WATCHDOG_S = 120.0
# The window's own start up limit. Longer than the title capture's because this can be the first launch after a
# compile, which loads 236 datafiles and the shader cache before the first frame.
WINDOW_TIMEOUT_S = 45.0


def frame_paths() -> list:
    """The frames the room wrote, in shot order."""
    return sorted(glob.glob(os.path.join(GAME_FRAME_DIR, FRAME_GLOB)))


def clear_old_frames(say=print) -> int:
    """Remove the frames of an earlier run, so a run answers for itself. Returns how many were removed."""
    removed = 0
    for path in frame_paths():
        try:
            os.remove(path)
            removed += 1
        except OSError as exc:
            say("could not remove %s: %s" % (path, exc))
    return removed


def stale_sources(build_path: str, limit: int = 8) -> list:
    """The game source files newer than the build, newest first, as (mtime, relative path).

    Card t_89d60fe5: the drive crash that filed this card came from a run of a build that was older than the source it
    was supposed to prove, so this tool now refuses that instead of grading an old exe. Only the game's own sources
    count (GML, the project file and its .yy parts), because those are what a compile turns into the runner.
    """
    if not os.path.isfile(build_path):
        return []
    built = os.path.getmtime(build_path)
    newer = []
    for folder, _dirs, files in os.walk(os.path.join(ROOT, "game")):
        for name in files:
            if not name.endswith((".gml", ".yy", ".yyp")):
                continue
            path = os.path.join(folder, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > built + 1.0:
                newer.append((mtime, os.path.relpath(path, ROOT)))
    newer.sort(reverse=True)
    return newer[:limit]


def launch(say=print) -> int:
    """One run of the built game, opened on the drive room, muted, and gated. Returns an exit code."""
    policy = pp_launch.Policy(show=LAUNCH_ARGS.show, sound=False, wait_s=LAUNCH_ARGS.idle_wait,
                              force=LAUNCH_ARGS.force)
    if not policy.gate("drive capture"):
        return pp_launch.EXIT_REFUSED

    build = cap.newest_build()
    if build is None:
        say("no built game found under %s, run tools/run.ps1 first" % cap.GAME_OUTPUT_DIR)
        return 1
    exe_path, win_path = build

    # The build has to be this source's build. A capture of an older exe is a picture of code nobody can see, which is
    # exactly how the card that filed this fix was filed: the room crashed on a build older than its own fix.
    stale = stale_sources(win_path)
    if stale:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(win_path)))
        if not LAUNCH_ARGS.allow_stale:
            say("P: the built game %s is older than %d source file(s), so a run now would prove the old build:"
                % (os.path.basename(win_path), len(stale)))
            for _mtime, rel in stale:
                say("P:   %s (%s)" % (rel, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_mtime))))
            say("P: run tools\\run.ps1 to build, or --allow-stale to prove this older build on purpose")
            return 1
        say("P: --allow-stale given, so this run proves the build from %s, which is older than %d source file(s)"
            % (stamp, len(stale)))
    say("launching %s -game %s" % (exe_path, win_path))

    os.makedirs(BUILD_DIR, exist_ok=True)
    removed = clear_old_frames(say)
    if removed:
        say("removed %d frame(s) from an earlier run" % removed)

    game_log = GAME_LOG
    # Card CAPTURE-QUIET-IMPL: the start, the mute, the missing console window and the PP: muted line are all one call,
    # and the exit line comes from run.finish() below.
    run = pp_launch.start_game(
        exe_path, win_path, log_path=GAME_LOG, policy=policy, label="drive capture",
        # The card's own two switches for the room: the app opens rm_pp_drive and the room plays at the capture clock
        # and writes one frame per shot.
        extra={"PP_DRIVE_ROOM": "1", "PP_DRIVE_CAPTURE": "1"},
    )
    process = run.process
    cap.start_watchdog(process, WATCHDOG_S)
    try:
        match = cap.find_window(
            lambda hwnd, pid, title, visible, rect: visible
            and cap.GAME_WINDOW_TITLE.lower() in title.lower()
            # The first run after a compile loads every datafile and the shader cache, so the window can take longer
            # than the title capture's 20 s to appear; the process image is the identity that cannot be faked by
            # another app's window title.
            and (pid == process.pid
                 or cap.process_image_name(pid).lower() == cap.GAME_EXE_NAME.lower()),
            timeout_s=WINDOW_TIMEOUT_S,
        )
        if match is None:
            say("the game window did not appear within %.0f s" % WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        policy.place(hwnd, cap.get_window_rect(hwnd))
        image_name = cap.process_image_name(match[1])
        if image_name.lower() != cap.GAME_EXE_NAME.lower():
            say("the window belongs to %r, not to %s, so it is not the game window" % (image_name, cap.GAME_EXE_NAME))
            return 1
        say("game window found: %s (hwnd %s)" % (match[2], hwnd))

        # The muted line is ruling D9's evidence; pp_launch.start_game printed it from this run's own log, so the run
        # only has to say that it still holds before the frames are graded.
        if not run.muted_said:
            say("the game's log never printed the PP: muted line, so this run is not evidence")
            return 1

        deadline = time.time() + FRAMES_TIMEOUT_S
        while time.time() < deadline:
            if len(frame_paths()) >= SHOT_COUNT:
                break
            if process.poll() is not None:
                break
            time.sleep(0.5)
        frames = frame_paths()
        say("the room wrote %d frame(s) to %s" % (len(frames), GAME_FRAME_DIR))

        cap.close_window(hwnd)
        grace = time.time() + cap.CLOSE_GRACE_S
        while time.time() < grace and process.poll() is None:
            time.sleep(0.2)
        return 0
    finally:
        # The one exit line, and the process closed with nothing left running (card CAPTURE-QUIET-IMPL).
        run.finish()


def log_lines(needle: str) -> list:
    """Every line of the run's log that carries a needle, in order."""
    if not os.path.isfile(GAME_LOG):
        return []
    with open(GAME_LOG, "r", encoding="utf-8", errors="replace") as handle:
        return [line.rstrip("\r\n") for line in handle if needle in line]


def check_frames(say=print) -> int:
    """The card's checks, over the frames the run wrote. Returns 0 when every one of them passed."""
    from PIL import Image

    frames = frame_paths()
    if len(frames) < SHOT_COUNT:
        say("FAIL only %d of %d frames exist, so fewer than twelve shots were drawn" % (len(frames), SHOT_COUNT))
        return 1

    signature = {}
    too_many = []
    sizes = set()
    for path in frames:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            sizes.add(rgb.size)
            colours = rgb.getcolors(maxcolors=1 << 16) or []
            signature[path] = len(colours)
            distinct = len(colours)
            if distinct > MAX_COLOURS:
                too_many.append((os.path.basename(path), distinct))
    say("frames: %d, sizes: %s" % (len(frames), sorted(sizes)))
    say("colours per frame: %s" % ", ".join("%s=%d" % (os.path.basename(p), signature[p]) for p in frames))
    if too_many:
        say("FAIL %d frame(s) carry more than %d colours: %s"
            % (len(too_many), MAX_COLOURS, ", ".join("%s=%d" % item for item in too_many)))
        return 1

    # Distinct shots: two frames are the same picture when their colour counts and their own pixel bytes agree.
    unique = {}
    for path in frames:
        with open(path, "rb") as handle:
            unique.setdefault(handle.read(), []).append(os.path.basename(path))
    say("distinct shots: %d of %d frames" % (len(unique), len(frames)))
    for names in unique.values():
        if len(names) > 1:
            say("  these frames are the same picture: %s" % ", ".join(names))
    if len(unique) < MIN_DISTINCT:
        say("FAIL only %d distinct shot(s), the card asks for at least %d" % (len(unique), MIN_DISTINCT))
        return 1

    sign_frame = os.path.join(GAME_FRAME_DIR, "pp_drive_shot_%02d.png" % SIGN_SHOT)
    if not os.path.isfile(sign_frame):
        say("FAIL the frame of shot %d, the gantry sign, was not written" % SIGN_SHOT)
        return 1
    say("the gantry sign frame: %s" % sign_frame)

    # The film's own numbers, from the game's own log lines.
    shots_logged = log_lines("PP drive: shot ")
    for line in shots_logged:
        say("log: %s" % line)
    if len(shots_logged) < SHOT_COUNT:
        say("FAIL the log names %d shots, the film has %d" % (len(shots_logged), SHOT_COUNT))
        return 1
    if not any(("sign %s" % SIGN_MILES) in line for line in shots_logged):
        say("FAIL no shot in the log carries the gantry sign at %s miles" % SIGN_MILES)
        return 1
    say("the log names %d shots and the sign at %s" % (len(shots_logged), SIGN_MILES))

    # The existing NES tool, on the sign crop and on the whole frame, with the card's 16 colour ceiling, and then on the
    # 2C02 enforced version of the same frame, which is the palette half of the answer.
    say("checking the sign crop and a whole frame against the NES rules")
    sign_1x = frame_1x(sign_frame)
    whole_1x = frame_1x(frames[0])
    results = []
    for label, source, extra in (
        ("sign crop", sign_1x, ["--crop", SIGN_CROP]),
        ("whole frame", whole_1x, []),
    ):
        results.append(run_nes_check(label, source, extra, say))
    results.append(run_enforce(sign_1x, say))
    return 0 if all(results) else 1


def frame_1x(source: str) -> str:
    """Write the 256x240 version of one frame and return its path.

    The room's screen_save writes the application surface, which is 3x on this host (768x720): one game pixel is nine
    image pixels. The NES rules are per tile and per 16x16 attribute area of the 256x240 frame, so the check runs on the
    1x picture, downsampled by nearest so no colour is invented.
    """
    from PIL import Image

    base = os.path.splitext(os.path.basename(source))[0]
    out = os.path.join(OUTPUT_DIR, "%s_1x.png" % base)
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        if rgb.size == (256, 240):
            rgb.save(out)
        else:
            scale = max(1, round(rgb.size[0] / 256))
            rgb.resize((256, 240), Image.NEAREST).save(out)
            if scale % 1:
                print("frame %s is %s, not a whole multiple of 256x240" % (source, rgb.size))
    return out


def crop_to(source: str, box: tuple) -> str:
    """Write the crop of one 1x frame and return its path. The box is in game pixels and a multiple of 8 on each side."""
    from PIL import Image

    base = os.path.splitext(os.path.basename(source))[0]
    out = os.path.join(OUTPUT_DIR, "%s_crop.png" % base)
    with Image.open(source) as image:
        image.convert("RGB").crop(box).save(out)
    return out


def colours_in(png: str) -> int:
    """How many distinct colours one picture carries."""
    from PIL import Image

    with Image.open(png) as image:
        return len(image.convert("RGB").getcolors(maxcolors=1 << 16) or [])


def run_nes_check(label: str, source: str, extra: list, say=print) -> bool:
    """Run tools/nes_check.py on one frame at the card's 16 colour ceiling, and print what it said.

    The card's own check is the colour count, so that is what decides this function's answer. The tool's other rules are
    printed as they come: a placeholder frame is drawn from the design palette (data/palette.json by role, spec 13), and
    the design palette is not the chip's, which is the gap tools/nes_enforce.py closes and which this tool then proves
    separately on the enforced picture.
    """
    target = source
    if extra and extra[0] == "--crop":
        target = crop_to(source, extra[1])
    command = [sys.executable, os.path.join(TOOLS_DIR, "nes_check.py"), target,
               "--type", "background", "--max-colours", str(MAX_COLOURS)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    text = (result.stdout or "") + (result.stderr or "")
    lines = text.splitlines()
    for line in lines[:10]:
        say("  nes_check %s: %s" % (label, line.strip()))
    if len(lines) > 10:
        say("  nes_check %s: ... %d more line(s) in the tool's own report" % (label, len(lines) - 10))
    count = colours_in(target)
    say("  nes_check %s: %d colour(s) of the %d the card allows" % (label, count, MAX_COLOURS))
    if count > MAX_COLOURS:
        say("  nes_check %s: FAIL, more colours than one screen may hold" % label)
        return False
    say("  nes_check %s: PASS at the card's own rule (16 colours or fewer)" % label)
    return True


def run_enforce(frame_1x: str, say=print) -> bool:
    """Rewrite one frame into a frame a 2C02 could draw, then check that frame with the NES tool.

    This is the second half of the palette answer: the placeholders ask for colours by role from the design palette, as
    spec 13 requires, and tools/nes_enforce.py maps them onto the chip's 64 outputs. A frame with a legal PPU version is
    a frame the hardware could show, so the check runs on the enforced picture too.
    """
    base = os.path.splitext(os.path.basename(frame_1x))[0]
    out = os.path.join(OUTPUT_DIR, "%s_ppu.png" % base)
    command = [sys.executable, os.path.join(TOOLS_DIR, "nes_enforce.py"), frame_1x,
               "--out", out, "--crop", "1"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.isfile(out):
        say("  nes_enforce: FAIL, no enforced frame was written")
        for line in ((result.stdout or "") + (result.stderr or "")).splitlines()[-6:]:
            say("  nes_enforce: %s" % line)
        return False
    check = subprocess.run(
        [sys.executable, os.path.join(TOOLS_DIR, "nes_check.py"), out,
         "--type", "background", "--max-colours", str(MAX_COLOURS)],
        cwd=ROOT, capture_output=True, text=True)
    lines = ((check.stdout or "") + (check.stderr or "")).splitlines()
    for line in lines[:8]:
        say("  nes_check ppu: %s" % line.strip())
    ok = check.returncode == 0
    say("  nes_check ppu: %s (enforced frame %s)" % ("PASS" if ok else "FAIL", out))
    return ok


def main(argv=None) -> int:
    global LAUNCH_ARGS
    parser = argparse.ArgumentParser(description="Prove room rm_pp_drive in the running game.")
    pp_launch.add_launch_flags(parser)
    parser.add_argument("--no-launch", action="store_true",
                        help="re-check the frames an earlier run wrote, without opening the game")
    parser.add_argument("--allow-stale", action="store_true", dest="allow_stale",
                        help="prove the built game even when game source files are newer than it (a deliberate proof "
                             "of an older build; default is to refuse and ask for tools\\run.ps1)")
    LAUNCH_ARGS = parser.parse_args(argv)

    if not LAUNCH_ARGS.no_launch:
        code = launch()
        if code != 0:
            return code
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return check_frames()


if __name__ == "__main__":
    sys.exit(main())
