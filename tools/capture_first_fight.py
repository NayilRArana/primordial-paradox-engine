#!/usr/bin/env python3
"""capture_first_fight.py: record the built game from the ship spawn to the first fight's victory line.

Why this file exists (card t_87ee4228, from blocker 2 of knowledge/HACKATHON-AUDIT-2026-10-22.md): the audit
could not find one log line or one frame from the running game that reaches a battle, so the judged claim "a
talk-your-way-through fight" had no evidence. tests/test_first_fight.py proves the fight is winnable and cannot
be lost from the data, without ever running GameMaker. This tool runs it and records it.

What it does, in one launch (one window, muted, closed on request, ruling D9):
  1. starts the built game through tools/pp_launch.py, so PP_MUTE=1 is set and the idle gate in
     tools/idle_check.py refuses to open a window while Nayil is at the PC;
  2. drives the real title screen with key presses the game already reads (no debug key and no environment
     flag): Enter to open the menu, Enter to start, Enter past the boarding dialogue, then walk down and right
     from the spawn onto the encounter trigger at (4,7) of ship_small (data/maps/all.json);
  3. records the window with ffmpeg gdigrab, cuts the recording to the true 3x viewport, and cuts the frame
     sample out of that recording at one frame a second;
  4. checks its own output: the mp4 is the game's 3x viewport, and the frame sample contains the battle box,
     the FIGHT command on the command row and the victory panel with its outcome word, each measured against
     the role colours in data/palette.json and data/room_palettes.json, never against a guess.

The TALK leg the card's GOAL names is NOT in this run. tutorial_sailors, the deck's battle at ship_small (4,7),
does carry talks_to_spare 3 with no condition, so a three TALK spare is walkable, but the trigger is
`once: true`: one launch reaches it once, and this run spends it on the FIGHT path the card's CHECK names. The
TALK path therefore needs its own launch and its own output file, which the card does not name; the report
records the reachable talk fight under `talk_leg` instead of the tool claiming a leg it never walks.

Every number the frame checks use is read from the repository's own files at run time: the palette roles from
data/palette.json, the room set's role list from data/room_palettes.json, the menu geometry from
pp_battle_director.gml's draw calls, the font's 8 pixel pitch from pp_font.gml. A change in any of those makes
these checks measure something else, which is the point.

Usage:
    python tools\\capture_first_fight.py              record, then check, and write both outputs
    python tools\\capture_first_fight.py --check      re-check output\\first_fight_capture.mp4 and the frame
                                                     sample already on disk, without launching anything
    python tools\\capture_first_fight.py --idle-wait 600   poll for the machine to go quiet, then record
    python tools\\capture_first_fight.py --show       leave the window on the primary screen (a person's run)
    python tools\\capture_first_fight.py --force      the idle gate override, for a person at the keyboard

Outputs:
    output\\first_fight_capture.mp4        the run, cropped to a true 3x of the 256x240 screen
    output\\first_fight_verify.json        the verifier's report, with its own `ok` field
    output\\first_fight_frames\\*.png       the frame sample the report scores (cut from the recording, 1 a second)

Exit codes:
    0  the recording was written and every check passed
    1  a check failed, or the game window never appeared
    3  the watchdog fired (the run overran)
    4  the idle gate refused to open a window: there was recent input, so nothing was opened
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import capture_title as cap  # noqa: E402  the window, key and screen copy primitives proved on this PC
import play_demo  # noqa: E402  the gdigrab recorder and the viewport crop the demo already uses
import pp_launch  # noqa: E402  muted, idle gated launch policy (ruling D9)

OUTPUT_DIR = os.path.join(ROOT, "output")
FRAME_DIR = os.path.join(OUTPUT_DIR, "first_fight_frames")
BUILD_DIR = os.path.join(ROOT, "build")
MP4_PATH = os.path.join(OUTPUT_DIR, "first_fight_capture.mp4")
VERIFY_PATH = os.path.join(OUTPUT_DIR, "first_fight_verify.json")
RAW_PATH = os.path.join(BUILD_DIR, "first_fight_raw.mp4")
GAME_LOG = os.path.join(BUILD_DIR, "first_fight_game.log")

SCREEN_W, SCREEN_H = 256, 240
SCALE = 3
FPS = 60
WATCHDOG_S = 480.0
WINDOW_TIMEOUT_S = 25.0
SETTLE_S = 2.5
# The recording starts a little before the first key and runs past the last one, so the run on video includes the
# title screen it started from and the map it ends on.
RECORD_LEAD_S = 1.0
RECORD_TAIL_S = 6.0
FRAME_EVERY_S = 1.0

# The run, as key presses. These are the game's own bindings (game/scripts/pp_input/pp_input.gml): confirm is Z,
# Enter is also confirm, the arrows are the walk. No debug key and no PP_SLICE flag is set: this is the path a
# player takes. Times are seconds from the launch, chosen with room either side of each handoff, and every press
# is one tile or one menu row, so an early press lands on a wall and is swallowed instead of skipping a beat.
EVENTS = [
    # Title: Enter opens the menu, Enter chooses NEW GAME, the crawl plays, Enter skips it for the ship.
    (2.5, "enter"),
    (4.0, "enter"),
    (18.0, "enter"),
    # The run starts the hero on ship_small at (2,7) (the game's own autosave line says so), and the encounter
    # trigger is the battle row at (4,7): two steps east reach it. Nothing moves him first, so no other key is sent.
    (20.0, "right"),
    (20.7, "right"),
    # From the trigger on: the intro dialogue's pages, the command menu with the cursor on FIGHT, the FIGHT itself, the
    # hit message and the result panel, each one confirm. Spaced wide enough that the result panel is on two sampled
    # frames before the next press leaves it, so the victory line is in the video and not only in the log.
    #
    # Card t_da94341c: the fight the data authors runs about 48 s of play (tests/test_first_fight.py pins that number),
    # so the old schedule, which stopped at 39.6 s, always ended one turn short of the result panel and the run could
    # never carry the victory word. The presses now run to 77.5 s in 2.4 s steps: a press during a drain is a no-op,
    # a press during the timing bar only sets its power, and a press on the finished panel is what leaves it, so the
    # panel is on screen for two frame samples when it appears.
    (23.5, "z"),
    (25.9, "z"),
    (28.3, "z"),
    (30.7, "z"),
    (33.1, "z"),
    (35.5, "z"),
    (37.9, "z"),
    (40.3, "z"),
    (42.7, "z"),
    (45.1, "z"),
    (47.5, "z"),
    (49.9, "z"),
    (52.3, "z"),
    (54.7, "z"),
    (57.1, "z"),
    (59.5, "z"),
    (61.9, "z"),
    (64.3, "z"),
    (66.7, "z"),
    (69.1, "z"),
    (71.5, "z"),
    (73.9, "z"),
    (76.3, "z"),
    (78.7, "z"),
    (81.1, "z"),
    (83.5, "z"),
    (85.9, "z"),
    (88.3, "z"),
    (90.7, "z"),
    (93.1, "z"),
    (95.5, "z"),
    (97.9, "z"),
    (100.3, "z"),
    (102.7, "z"),
    (105.1, "z"),
    (107.5, "z"),
    (109.9, "z"),
    (112.3, "z"),
    (114.7, "z"),
    (117.1, "z"),
]
RECORD_SECONDS = EVENTS[-1][0] + RECORD_TAIL_S



# ---------------------------------------------------------------------------------------------------------------------
# Data the checks read, never restate

def _read_json(name):
    path = os.path.join(ROOT, "data", name)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def role_colours():
    """The RGB of each role the battle screen spends, from data/palette.json through data/room_palettes.json."""
    palette = _read_json("palette.json")
    rooms = _read_json("room_palettes.json")
    names = palette["roles"]
    colours = palette["colours"]

    def rgb(role):
        index = names[role]
        text = colours[index].lstrip("#")
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))

    deck = None
    for entry in rooms["sets"]:
        if entry.get("id") == "deck_day":
            deck = entry
            break
    if deck is None:
        raise SystemExit("data/room_palettes.json has no deck_day set, so the battle roles cannot be read")
    roles = {}
    for role in ("ink", "paper", "dim", "text"):
        if role not in deck["roles"]:
            raise SystemExit("the deck_day set does not carry the role %r the battle screen draws with" % role)
        roles[role] = rgb(role)
    return roles


def menu_geometry():
    """The command window and its label cells, read from the draw calls in pp_battle_director.gml."""
    path = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    box_x1, box_y1, box_x2, box_y2 = 8, 168, SCREEN_W - 8, SCREEN_H - 8
    if "draw_rectangle(8, PP_MENU_TOP, PP_FRAME_W - 8, PP_FRAME_H - 8, false);" not in text:
        raise SystemExit("pp_battle_draw_menu no longer draws the window at (8, PP_MENU_TOP)-(W-8, H-8); "
                         "the frame checks would measure a rectangle the game does not draw")
    if "var _x = 24 + (i mod 2) * 104;" not in text:
        raise SystemExit("pp_battle_draw_menu no longer draws its labels at 24 + (i mod 2) * 104; the label "
                         "cells the FIGHT check samples cannot be trusted")
    # Card t_da94341c: the labels are the 8x8 sheet's glyphs now (card BATTLE-FONT-WIRE), drawn by pp_font_draw, which
    # advances one 8 px cell per character and paints the sheet's own ink. The cell geometry is unchanged, and the
    # colour the FIGHT check looks for is not a role at all: the sheet's ink is a 2C02 white that the encoder spreads
    # over near-white values, so the cell is measured against the window's paper (card t_239422fe). Both facts are
    # pinned here.
    if "pp_font_draw(_entry.label, _x, _yy, 1);" not in text:
        raise SystemExit("pp_battle_draw_menu no longer draws its labels with pp_font_draw; the ink the FIGHT check "
                         "looks for would be a colour the game does not paint")
    glyph = 8
    with open(os.path.join(ROOT, "game", "scripts", "pp_font", "pp_font.gml"), "r", encoding="utf-8") as fh:
        font_text = fh.read()
    if "_cx += 8;" not in font_text:
        raise SystemExit("pp_font_draw no longer advances one 8 px cell per glyph; the label cell widths the FIGHT "
                         "check samples cannot be trusted")
    return {
        "box": (box_x1, box_y1, box_x2, box_y2),
        "label_y": box_y1 + 8,
        "label_x": (24, 24 + 104),
        "glyph": glyph,
        "cursor_note_y": SCREEN_H - 20,
    }


def command_labels():
    """The four labels and their order, from pp_battle_commands.gml, so the FIGHT cell is the first one."""
    path = os.path.join(ROOT, "game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    labels = []
    for line in text.splitlines():
        if 'label: "' in line:
            labels.append(line.split('label: "')[1].split('"')[0])
    if not labels or labels[0] != "FIGHT":
        raise SystemExit("pp_battle_commands.gml no longer has FIGHT as the first command, so cell 0 is not "
                         "the FIGHT command and this check would pass on the wrong word")
    return labels


def outcome_words():
    """The words the result panel can print: pp_battle_outcome's own strings."""
    return ("spare", "kill", "defeat")


# ---------------------------------------------------------------------------------------------------------------------
# The launch and the run

def build():
    found = cap.newest_build()
    if found is None:
        raise SystemExit("no built game under %s: run the build first" % cap.GAME_OUTPUT_DIR)
    return found


def press(hwnd, key, code):
    """One real key press, with the focus taken first when the frame copies have let it slip.

    A posted key is a dud: GameMaker reads the key state, not the window messages (the 2026-10-21 run in
    capture_title.py's own docstring posted four Enters and the title never moved). The screen copies this tool
    takes every second raise the window and hand the focus back, so the focus is re-taken here before the press
    rather than assumed to have survived. Arrows go through send_vk_focused, which marks the extended keys.
    """
    if not cap.game_has_focus(hwnd):
        ok, note = cap.ensure_key_focus(hwnd, attempts=4)
        if not ok:
            return "not sent (%s)" % note
    return cap.send_vk_focused(code)


def start_recorder(rect, out_path):
    x, y, w, h = rect
    os.makedirs(BUILD_DIR, exist_ok=True)
    log_path = os.path.join(BUILD_DIR, "first_fight_ffmpeg.log")
    handle = open(log_path, "wb")
    # Card t_4275136f: read the binary through play_demo.ffmpeg_path(), not play_demo.FFMPEG. The module global is
    # None until the finder has run, and this tool never ran it, so every launch reached Popen with None and died on
    # "expected str, bytes or os.PathLike object, not NoneType" after the game window was already up. Measured on this
    # host 2026-10-25: two launches died here, the second after PP_FFMPEG was set correctly, which is how the global
    # and not the search was identified.
    ffmpeg = play_demo.ffmpeg_path()
    if not ffmpeg:
        handle.close()
        raise SystemExit("capture_first_fight: no ffmpeg on this host (set PP_FFMPEG to the binary), so nothing can "
                         "be recorded; the game was not kept running")
    arguments = [
        "-f", "gdigrab", "-framerate", str(FPS),
        "-offset_x", str(x), "-offset_y", str(y),
        "-video_size", "%dx%d" % (w, h),
        "-i", "desktop",
        "-t", "%.2f" % RECORD_SECONDS,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
        out_path,
    ]
    process = subprocess.Popen([ffmpeg, "-hide_banner", "-y"] + arguments,
                               stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return process, handle, log_path


def sample_frames(mp4_path, fps=FRAME_EVERY_S):
    """Cut the frame sample out of the recording: one picture a second, at the recording's own pixels.

    The sample is taken from the mp4 and not from the desktop, so every frame the report scores is a frame the video
    carries, and nothing has to touch the window while the run is driving it.
    """
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR, ignore_errors=True)
    os.makedirs(FRAME_DIR, exist_ok=True)
    pattern = os.path.join(FRAME_DIR, "f_%04d.png")
    arguments = [play_demo.FFMPEG, "-hide_banner", "-y", "-i", mp4_path,
                 "-vf", "fps=%g" % float(fps if fps != FRAME_EVERY_S else 1.0),
                 "-start_number", "0", pattern]
    done = subprocess.run(arguments, capture_output=True, stdin=subprocess.DEVNULL, timeout=300)
    if done.returncode != 0:
        print("P: ffmpeg could not cut the frame sample: %s"
              % (done.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:])
    return len([name for name in os.listdir(FRAME_DIR) if name.endswith(".png")])


def run_capture(policy, show=False):
    exe_path, win_path = build()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR, ignore_errors=True)
    os.makedirs(FRAME_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    print("P: launching %s -game %s" % (exe_path, win_path))
    print("P: the run is %d key presses over %.0f s, recorded to %.0f s" % (len(EVENTS), EVENTS[-1][0],
                                                                          RECORD_SECONDS))

    game_log = open(GAME_LOG, "wb")
    process = subprocess.Popen(
        [exe_path, "-game", win_path], cwd=os.path.dirname(exe_path),
        stdin=subprocess.DEVNULL, stdout=game_log, stderr=subprocess.STDOUT,
        env=policy.env(),
    )
    cap.start_watchdog(process, WATCHDOG_S)
    recorder = None
    recorder_handle = None
    try:
        match = cap.find_window(
            lambda hwnd, pid, title, visible, rect: visible and pid == process.pid
            and cap.GAME_WINDOW_TITLE.lower() in title.lower(),
            timeout_s=WINDOW_TIMEOUT_S,
        )
        if match is None:
            print("P: the game window did not appear within %.0f s" % WINDOW_TIMEOUT_S)
            return 1
        hwnd = match[0]
        image_name = cap.process_image_name(match[1])
        if image_name.lower() != cap.GAME_EXE_NAME.lower():
            print("P: the window belongs to %r, not to the game, so nothing was recorded" % image_name)
            return 1
        policy.place(hwnd, cap.get_window_rect(hwnd))
        time.sleep(SETTLE_S)
        cap.ensure_key_focus(hwnd)

        rect, box, score, note = play_demo.pre_roll_viewport(hwnd, os.path.join(BUILD_DIR, "first_fight_preroll.png"))
        if box is None:
            print("P: the pre-roll frame is not the game: %s" % note)
            return 1
        print("P: viewport %s in the window, score %.3f" % (str(box), score))

        recorder, recorder_handle, rec_log = start_recorder(rect, RAW_PATH)
        started = time.monotonic()
        for at_s, key in EVENTS:
            now = time.monotonic() - started
            if now < at_s:
                time.sleep(at_s - now)
            code = cap.KEY_CODES[key]
            result = press(hwnd, key, code)
            print("P: %.1f s %s %s" % (at_s, key, result))

        # Hold the window open to the end of the recording, so the map after the fight is on video too. No screen copy
        # is taken while the run is driving the game: a copy raises the window and hands the focus back, which made
        # every press pay four focus retries and pushed the schedule minutes behind the recorder. The frame sample is
        # cut out of the recording itself after the cut, so what it scores is exactly what the mp4 shows.
        remaining = RECORD_SECONDS - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

        # Close on request, then stop the recorder and let it finish the file.
        cap.close_window(hwnd)
        deadline = time.time() + 6.0
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.2)
        if process.poll() is None:
            print("P: the game did not close on request, terminating it")
            cap.kill_tree(process)
        else:
            print("P: the game closed on request (exit code %s)" % process.returncode)

        try:
            recorder.wait(timeout=90)
        except Exception:  # noqa: BLE001  a recorder that will not stop must not hang the card
            recorder.kill()
        if recorder_handle:
            recorder_handle.close()

        if not os.path.isfile(RAW_PATH) or os.path.getsize(RAW_PATH) == 0:
            print("P: the recorder wrote no file; the ffmpeg log is %s" % rec_log)
            return 1
        ok, note = play_demo.cut_and_scale(RAW_PATH, box, {"record": {"width": SCREEN_W * SCALE,
                                                                     "height": SCREEN_H * SCALE,
                                                                     "fps": FPS}}, MP4_PATH, None)
        print("P: cut and scale: %s (%s)" % ("ok" if ok else "failed", note))
        if not ok:
            return 1
        count = sample_frames(MP4_PATH)
        print("P: %d frame copies cut from the recording into %s" % (count, FRAME_DIR))
        return 0
    finally:
        if recorder is not None and recorder.poll() is None:
            recorder.kill()
        if recorder_handle is not None:
            try:
                recorder_handle.close()
            except Exception:  # gate: ok the recorder's own error is already printed; a close failure on the way out must not mask it
                pass
        cap.kill_tree(process)
        try:
            game_log.close()
        except Exception:  # gate: ok the game has already exited; a handle close failure here would replace the run's verdict with a teardown one
            pass


# ---------------------------------------------------------------------------------------------------------------------
# The frame checks: measured on the game's own colours and its own draw geometry

# Card t_da94341c. The frame sample is cut from the recorded mp4 (sample_frames), so every frame it scores is an
# h264 picture: chroma is stored at a quarter of the luma resolution and the quantiser moves every sample a little,
# which is why a real battle frame measures 741 distinct colours and none of them exactly on a palette entry. The
# old reader here demanded exact palette pixels, so it refused every frame the tool itself had cut and the three
# structural checks could never pass on any run. The tolerance is the one play_demo.palette_share already documents
# for the same reason, and it is applied by SNAPPING each pixel onto the nearest game colour, so the role comparisons
# below still run at tolerance 0: a frame that is not the game's picture cannot be snapped and is refused.
PALETTE_SNAP_TOLERANCE = 12
PALETTE_SNAP_MIN = 0.90

# Card t_239422fe. The command labels are NOT drawn in the ink role. pp_font_draw paints the 8x8 sheet's one ink, which
# is a 2C02 white (pp_font.gml's header), and on the recorded first fight the FIGHT cell carries its strokes as 41 px
# exactly on the text role plus about 500 px spread over some twenty near-white values such as (248,247,252) that no
# palette entry is within 12 of, while the ink role #0b0b0f (11,11,15) appears 0 times in the cell and once in the whole
# window. The old mask here was exact equality with the ink role, so it scored the label at 0 px on a frame where the
# label is legible (resume_probe/frames/f_0046.png, box paper 0.952, a crop reads FIGHT POWER / TALK SPARE).
#
# A glyph is therefore measured as the paper's opposite: a pixel that differs from the paper role by more than 24 in
# some channel. 24 is the finding's own measured threshold (FIRST-FIGHT-FINDING-2026-10-26.md finding 2) and it is twice
# the reader's snap tolerance, so no pixel the reader would have snapped onto the paper counts as a glyph and the
# paper's own encoder bleed around a stroke does not add one. The paper role is (28,28,36) and the label's strokes
# measure (200,200,212) to (255,253,255), which is 168 to 227 away, so the threshold sits in empty space between the
# fill and the strokes rather than being tuned to a frame. The FIGHT cell's own thresholds are unchanged:
# FIGHT_SPAN_MIN 32 and FIGHT_INK_MIN 20, and the corrected cell reads 121 px over a 39 px span in 5 runs.
GLYPH_CONTRAST_MIN = 24


def game_palette():
    """The colours the game draws with, from data/palette.json, in the order the file lists them."""
    palette = _read_json("palette.json")
    out = []
    for text in palette["colours"]:
        text = text.lstrip("#")
        out.append(tuple(int(text[i:i + 2], 16) for i in (0, 2, 4)))
    return out


def snap_to_palette(image, colours, tolerance=PALETTE_SNAP_TOLERANCE):
    """Return (snapped image, share of pixels that landed on a game colour).

    One dict of settled answers keeps this linear in the number of DISTINCT colours, not in pixels: a battle frame
    carries a few hundred after the resize, and a terminal screenshot carries tens of thousands that do not settle.
    """
    from PIL import Image
    source = image.load()
    out = Image.new("RGB", image.size)
    target = out.load()
    width, height = image.size
    settled = {}
    landed = 0
    for y in range(height):
        for x in range(width):
            pixel = source[x, y]
            answer = settled.get(pixel)
            if answer is None:
                answer = pixel
                best = tolerance
                for colour in colours:
                    gap = max(abs(pixel[0] - colour[0]), abs(pixel[1] - colour[1]), abs(pixel[2] - colour[2]))
                    if gap <= best:
                        best = gap
                        answer = colour
                settled[pixel] = answer
            if answer is not pixel:
                landed += 1
            target[x, y] = answer
    return out, landed / float(width * height or 1)


def load_screen_pixels(path):
    """One frame of the sample, reduced to the 256x240 screen the game drew, on the game's own palette.

    The sample is cut from the recording, which is already cropped to the 3x viewport (play_demo.cut_and_scale), so
    a 768x720 frame is the whole screen and needs no viewport search. Anything else falls back to the search, which
    is what a window copy needs.
    """
    from PIL import Image
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        if width < SCREEN_W or height < SCREEN_H:
            return None, "the copy is %dx%d, smaller than one screen" % (width, height)
        if (width, height) == (SCREEN_W * SCALE, SCREEN_H * SCALE):
            box = (0, 0, width, height)
        else:
            # Not a cut frame, so it is a window copy: the viewport has to be found again, because the game's frame is
            # the largest area whose pixels are the legal palette. tools/nes_composite_check.py does the same search.
            box, _score, why = cap.viewport_box_and_score(path)
            if box is None:
                return None, "no legal 3x viewport in this frame (%s)" % why
        x, y, w, h = box
        crop = image.crop((x, y, x + w, y + h)).resize((SCREEN_W, SCREEN_H), Image.NEAREST)
        snapped, share = snap_to_palette(crop, game_palette())
        if share < PALETTE_SNAP_MIN:
            return None, ("only %.3f of this frame's pixels land within %d of a game colour, so it is not the game's "
                          "picture" % (share, PALETTE_SNAP_TOLERANCE))
        return snapped.load(), None


def rect_stats(pixels, rect, colour, tolerance=0):
    x1, y1, x2, y2 = rect
    total = 0
    hit = 0
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            pixel = pixels[x, y]
            total += 1
            if (abs(pixel[0] - colour[0]) <= tolerance and abs(pixel[1] - colour[1]) <= tolerance
                    and abs(pixel[2] - colour[2]) <= tolerance):
                hit += 1
    return hit, total


def ink_mask(pixels, rect, colours):
    x1, y1, x2, y2 = rect
    mask = {}
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            pixel = pixels[x, y]
            if pixel in colours:
                mask[(x - x1, y - y1)] = True
    return mask


def contrast_mask(pixels, rect, background, tolerance=GLYPH_CONTRAST_MIN):
    """The pixels of a cell that are not the colour it is filled with: a glyph, on a paper window.

    Card t_239422fe. The command labels are the sheet's own ink (a 2C02 white), which the encoder spreads over near
    white values, so no one colour is the label's. What IS known about a glyph is that it is drawn on the window's
    paper and is not it, so the mask is taken against the paper role instead of for a colour. Measured on
    resume_probe/frames/f_0046.png this reads the FIGHT cell at 121 px over a 39 px span in 5 runs; the ink role it
    used to look for appears 0 times in that cell.
    """
    x1, y1, x2, y2 = rect
    mask = {}
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            pixel = pixels[x, y]
            if (abs(pixel[0] - background[0]) > tolerance or abs(pixel[1] - background[1]) > tolerance
                    or abs(pixel[2] - background[2]) > tolerance):
                mask[(x - x1, y - y1)] = True
    return mask


def clusters_x(mask, width):
    """The number of ink runs along x: one per glyph when the font's cells leave a blank column between them."""
    hit = [False] * width
    for (x, _y) in mask:
        hit[x] = True
    runs = 0
    previous = False
    for x in range(width):
        if hit[x] and not previous:
            runs += 1
        previous = hit[x]
    return runs


def ink_bbox(mask):
    if not mask:
        return None
    xs = [x for (x, _y) in mask]
    ys = [y for (_x, y) in mask]
    return (min(xs), min(ys), max(xs), max(ys))


def ink_rows(mask, height):
    rows = [False] * height
    for (_x, y) in mask:
        rows[y] = True
    runs = 0
    previous = False
    for y in range(height):
        if rows[y] and not previous:
            runs += 1
        previous = rows[y]
    return runs


def score_frame(pixels, roles, geom, labels, text_colour=None):
    """Every number the report prints for one frame, computed from the roles and the draw geometry.

    The command cells are measured as contrast against the window's paper (contrast_mask, card t_239422fe): the
    sheet paints its one ink as a 2C02 white and the encoder spreads it, so no role colour is the label's.

    `text_colour` names the colour the victory panel's word and "press Z" are measured in, and defaults to the ink
    role: on the recorded fight's result panel (resume_probe/frames/f_0090.png, panel paper 0.953) those bands do
    carry the ink role, measured 28 px and 53 px wide. It is NOT used for the command cells, which carry no ink role
    pixel at all on the same recording.
    """
    box_colour = roles["paper"]
    border_colour = roles["dim"]
    ink_colour = roles["ink"]
    glyph_colour = text_colour or ink_colour
    bx1, by1, bx2, by2 = geom["box"]

    box_hit, box_total = rect_stats(pixels, (bx1 + 1, by1 + 1, bx2 - 1, by2 - 1),
                                    box_colour, tolerance=0)
    # The border is one row of pixels and a cut frame carries h264 chroma at a quarter resolution, so the row the
    # outline landed on can move by one. The best of the three rows around the drawn line is measured, which is the
    # same claim (the window has a dim border) without pinning the video's own half-pixel.
    border_hit = 0
    border_total = 1
    for row in (by1 - 1, by1, by1 + 1):
        if row < 0 or row >= SCREEN_H:
            continue
        hit, total = rect_stats(pixels, (bx1, row, bx2, row), border_colour, tolerance=0)
        if hit > border_hit:
            border_hit, border_total = hit, total
    # Card t_da94341c: a one pixel outline between a dim band and paper is exactly what the video quantiser smooths, so
    # no row of a cut frame is ever 70 percent dim (measured on output/first_fight_capture.mp4, see the note at the
    # thresholds). The claim the check exists for is that the window is bounded, so it is measured as the step it is:
    # the outside rows above the window are not paper, and the inside is. A screen that is all paper scores 0 here.
    #
    # Card t_239422fe: the second half of that step was never measured. The share of the three rows above the window
    # that are not paper is 1.0000 on ANY screen that is not paper, so the no-battle recording measured exactly 1.0000
    # on 123 of 123 frames while the window's own paper measured 0.0001 at most, and on the real fight 40 of the 42
    # frames with the window up measured 0.667 to 0.678, under the 0.70 threshold, because the window's top edge on a
    # cut frame sits inside that three row band. A boundary has two sides, so both are counted per column: a column is
    # bounded when at least one row above the window is not paper AND the window's first inside row is paper. Measured
    # on the recorded frames: 1.0000 on all 42 command window frames of the real fight, 0.0000 on all 123 frames of the
    # no-battle recording and on all 75 frames of the real fight without a window. The dim row is still measured above,
    # because it is the role the director outlines with, and the larger of the two is what the check compares.
    outside = 0
    outside_total = 0
    for x in range(bx1 + 1, bx2):
        above = False
        for row in range(max(0, by1 - 3), by1):
            if pixels[x, row] != box_colour:
                above = True
                break
        inside = by1 + 1 < SCREEN_H and pixels[x, by1 + 1] == box_colour
        outside += 1 if (above and inside) else 0
        outside_total += 1
    if outside_total:
        step = outside / float(outside_total)
        if step > border_hit / float(border_total):
            border_hit, border_total = outside, outside_total

    glyph = geom["glyph"]
    cells = {}
    for slot, label in enumerate(labels):
        cx = geom["label_x"][slot % 2]
        cy = geom["label_y"] + (slot // 2) * 20
        # Card t_da94341c: the sheet's ink lands a few rows below the y the draw call names (measured, see the note at
        # the thresholds), and that gap is the cut frame's own, not the game's. The cell is therefore found as the band
        # of glyph rows with the most ink in the cell's own column, and the rect that wins is the one measured.
        width = glyph * len(label)
        best = None
        for top in range(max(0, cy - 2), min(SCREEN_H - glyph, cy + 9) + 1):
            rect = (cx, top, cx + width - 1, top + glyph - 1)
            # Card t_239422fe: the cell is measured against the paper it is drawn on, not for one role colour. On a
            # cut frame the sheet's white label is a spray of near-white values and the ink role appears 0 times, so
            # an exact colour mask scored a legible FIGHT label at 0 px. See GLYPH_CONTRAST_MIN for the measurement.
            mask = contrast_mask(pixels, rect, box_colour)
            if best is None or len(mask) > best[0]:
                best = (len(mask), rect, mask)
        if best is None:
            best = (0, (cx, cy, cx + width - 1, cy + glyph - 1), {})
        _count, rect, mask = best
        bbox = ink_bbox(mask)
        cells[label] = {
            "rect": rect,
            "ink_pixels": len(mask),
            "clusters": clusters_x(mask, width),
            "bbox": bbox,
            "bbox_width": (bbox[2] - bbox[0] + 1) if bbox else 0,
        }

    # The victory panel (pp_app's battle draw): paper at (40,100)-(216,140), the outcome word at y=112 and
    # "press Z" at y=126, both centred on x=128 and both the sheet's glyphs.
    panel = (40, 100, SCREEN_W - 40, 140)
    panel_hit, panel_total = rect_stats(pixels, (panel[0] + 1, panel[1] + 1, panel[2] - 1, panel[3] - 1),
                                        box_colour, tolerance=0)
    word_band = (panel[0] + 1, 112, panel[2] - 1, 119)
    press_band = (panel[0] + 1, 126, panel[2] - 1, 133)
    word_mask = ink_mask(pixels, word_band, (glyph_colour,))
    press_mask = ink_mask(pixels, press_band, (glyph_colour,))
    word_bbox = ink_bbox(word_mask)
    press_bbox = ink_bbox(press_mask)

    # The message window the battle draws at the top of the frame (pp_battle_text_box_*): paper with a dim border,
    # then the fight's own text rows in ink.
    msg = (0, 0, SCREEN_W - 1, 47)
    msg_hit, msg_total = rect_stats(pixels, (msg[0] + 1, msg[1] + 1, msg[2] - 1, msg[3] - 1),
                                    box_colour, tolerance=0)
    msg_mask = ink_mask(pixels, (msg[0] + 16, msg[1] + 16, msg[2] - 16, msg[3] - 4), (ink_colour,))
    msg_bbox = ink_bbox(msg_mask)

    return {
        "battle_box_paper": round(box_hit / float(box_total), 4) if box_total else 0.0,
        "battle_box_border": round(border_hit / float(border_total), 4) if border_total else 0.0,
        "cells": cells,
        "message_box_paper": round(msg_hit / float(msg_total), 4) if msg_total else 0.0,
        "message_text_rows": ink_rows(msg_mask, 48),
        "message_text_bbox": msg_bbox,
        "victory_panel_paper": round(panel_hit / float(panel_total), 4) if panel_total else 0.0,
        "victory_word_width": (word_bbox[2] - word_bbox[0] + 1) if word_bbox else 0,
        "victory_word_cx": (word_bbox[0] + word_bbox[2]) / 2.0 + word_band[0] if word_bbox else None,
        "victory_press_width": (press_bbox[2] - press_bbox[0] + 1) if press_bbox else 0,
    }


def is_battle_frame(scores):
    return scores["battle_box_paper"] >= BATTLE_BOX_MIN and scores["battle_box_border"] >= BATTLE_BORDER_MIN


def is_menu_frame(scores):
    # Card t_da94341c: the five glyph FIGHT label is the claim, and the sheet's glyphs have internal gaps, so the old
    # "one ink run per glyph" counted 9 runs on a real label. The label's ink has to span the cell instead: at least
    # 4 of its 5 eight pixel glyphs wide, and at least FIGHT_INK_MIN ink pixels inside it. The cluster count stays in
    # the report as information, and a scattered few pixels cannot span 32 px.
    fight = scores["cells"].get("FIGHT") or {}
    span = fight.get("bbox_width", 0)
    return is_battle_frame(scores) and span >= FIGHT_SPAN_MIN and fight.get("ink_pixels", 0) >= FIGHT_INK_MIN


def is_victory_frame(scores):
    return (scores["victory_panel_paper"] >= VICTORY_PANEL_MIN
            and scores["victory_word_width"] >= VICTORY_WORD_MIN
            and scores["victory_press_width"] >= VICTORY_PRESS_MIN)


# Thresholds. Each is a structural property of the screen, not a value copied from one run: a paper filled window
# with its dim border, a five glyph FIGHT label in the first cell, a paper result panel with an outcome word and
# "press Z" on it. They are stated here once so the report can print what it compared.
BATTLE_BOX_MIN = 0.70
BATTLE_BORDER_MIN = 0.70
FIGHT_CLUSTERS = 5
FIGHT_SPAN_MIN = 32
FIGHT_INK_MIN = 20
VICTORY_PANEL_MIN = 0.85
VICTORY_WORD_MIN = 24
VICTORY_PRESS_MIN = 24

# The recording's own gate: at least 90 percent of every sampled frame's pixels land within 12 of a colour one of the
# game's two palette files names, and the frame is the card's 3x viewport. 0.90 is the same number the frame reader
# uses for the same question (PALETTE_SNAP_MIN), and the union is used because the game's screens do not all draw
# from one set; the measured split is in video_checks' docstring. The NES-only share is measured and reported under
# look_rule, where it belongs, and gates nothing here.
VIDEO_PICTURE_MIN = 0.90
VIDEO_NES_SHARE_MIN = 0.90

# Card t_da94341c, measured on the 123 s recording the fixed build produced (output/first_fight_capture.mp4). Three
# facts the checks above still assume, kept here so the next worker measures instead of rediscovering them:
#   1. The window's dim outline is one row. In a cut h264 frame no row near y=168 or y=232 is 70 percent dim: the
#      field band above it is dim too, and a 1 px line between paper and dim is exactly what the quantiser smooths.
#      A border claim has to be measured as a contrast step, not as a row of exact colour.
#   2. The FIGHT cell carries 9 ink column runs and a 41 px ink bbox, because the sheet's glyphs have internal gaps;
#      "one run per glyph" is false for this font. The bbox width (5 glyphs * 8 px = 40) is the honest measure.
#   3. The labels' ink sits about 6 px below the y pp_battle_draw_menu draws them at (ink measured on rows 182 to 190
#      where the draw call says 176), so a cell rect taken from the source alone lands on the wrong rows.
# The victory panel needs none of that: on frame f_0101 the panel paper measures 0.96, the outcome word 30 px and
# "press Z" 49 px wide, which is the run reaching its result screen with the word "kill" on it.
#
# Card t_239422fe, measured on a REAL first fight (resume_probe/first_fight_resume_capture.mp4, 117 frames, 2026-10-26):
#   4. The command labels are not the ink role. In the FIGHT cell the ink role #0b0b0f appears 0 times and the label's
#      strokes are the text role (200,200,212) plus near-white values no palette entry is within 12 of, so a cell
#      measured for one colour reads 0 px on a legible label. Measured against the paper role (>24 away in a channel)
#      the cell reads 121 px, a 39 px span and 5 runs, which is FIGHT. Fact 2's "9 runs, 41 px" was measured on material
#      where the label did land on the ink role.
#   5. The border step has two sides. "The three rows above the window are not paper" is 1.0 on any screen that is not
#      paper, so it read 1.0000 on all 123 frames of the no-battle run while the window's paper read 0.0001; on the
#      real fight the window's top edge falls inside that band and 40 of 42 window frames measured 0.667 to 0.678. The
#      boundary is measured per column as outside not paper AND inside paper, which reads 1.0 on all 42 window frames
#      of the real fight and 0.0 on every frame without a window.


def video_checks(path):
    """The mp4 itself: the size and rate the card asks for, a real duration, and frames that are the game.

    Two colour measures are taken on each sample, because they answer two different questions:

      on_game_colours  the share of the frame's pixels that sit on a colour one of the two files this game draws
                  from names them (data/palette.json, the roles file the battle screen and room sets bake from,
                  plus data/nes_palette.json). This is the question this verifier exists for: is the recorded
                  picture the game's own screen, and not a terminal or a window frame.
      nes_share   the share that sits on the FCEUX 2C02 list in data/nes_palette.json alone. That is the art
                  rule RULE 0 point 1 (knowledge/ART-BIBLE.md, knowledge/PALETTE-SYNERGY.md S13), and it is the
                  palette lane's ruling, not this capture's verdict.

    Measured on the 123 s recording of 2026-10-23, the game's screens do not all draw from one set, which is why
    the picture gate is the union and not either file alone:

      second 2    (title)          data/palette.json 0.061   nes 0.934
      second 25   (the fight)      data/palette.json 0.997   nes 0.002
      second 86   (the fight)      data/palette.json 0.996   nes 0.001
      second 105  (after the win)  data/palette.json 0.149   nes 0.947
      second 117  (ship deck)      data/palette.json 0.148   nes 0.949

    A gate on data/palette.json alone would fail the title and the post win screen; a gate on data/nes_palette.json
    alone fails every battle frame. Both would call a correct capture of a working fight a failed capture, and the
    second would also give the palette lane's open question (knowledge/PALETTE-SYNERGY.md line 261: should the room
    palette roles resolve into data/nes_palette.json?) a false answer of "no defect". So the pass is the union,
    nes_share is reported under `look_rule` with its own ok and gates nothing here, and the per sample split stays
    in the report for the lane that owns it.
    """
    checks = {}
    # Card t_239422fe: read the binary through play_demo.ffmpeg_path(), for the same reason start_recorder does (card
    # t_4275136f). The module global is None until the finder has run, and check_outputs is reachable on its own
    # through --check, with no launch to have run it: measured on this host 2026-10-26, --check died here on a
    # NoneType before it scored a single sample, so the "no new launch needed" mode could not score a recording.
    ffmpeg = play_demo.ffmpeg_path()
    ffprobe = cap.ffprobe_path(ffmpeg) if ffmpeg else None
    stream = play_demo.video_stream(ffprobe, path) if ffprobe else None
    checks["stream"] = stream
    checks["exists"] = os.path.isfile(path)
    checks["bytes"] = os.path.getsize(path) if checks["exists"] else 0
    if stream:
        checks["width"] = int(stream.get("width", 0))
        checks["height"] = int(stream.get("height", 0))
        checks["fps"] = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
        checks["duration_s"] = round(cap.probe_duration(ffprobe, path) or 0.0, 2)
    nes_allowed = play_demo.palette_entries() or []
    game_allowed = game_palette()
    both_allowed = game_allowed + [c for c in nes_allowed if c not in game_allowed]
    samples = []
    if checks["exists"]:
        duration = checks.get("duration_s") or 0.0
        for fraction in (0.02, 0.2, 0.4, 0.55, 0.7, 0.85, 0.95):
            stamp = max(0.05, duration * fraction)
            out = os.path.join(BUILD_DIR, "first_fight_sample_%02d.png" % int(fraction * 100))
            ok = cap.extract_frame(ffmpeg, path, stamp, out)
            game_share = play_demo.palette_share(out, game_allowed) if ok else None
            nes_share = play_demo.palette_share(out, nes_allowed) if (ok and nes_allowed) else None
            both_share = play_demo.palette_share(out, both_allowed) if ok else None
            samples.append({"at_s": round(stamp, 2),
                            "on_game_colours": None if both_share is None else round(both_share, 4),
                            "game_share": None if game_share is None else round(game_share, 4),
                            "nes_share": None if nes_share is None else round(nes_share, 4),
                            "ok": bool(ok)})
    checks["samples"] = samples
    checks["size_ok"] = checks.get("width") == SCREEN_W * SCALE and checks.get("height") == SCREEN_H * SCALE
    checks["duration_ok"] = (checks.get("duration_s") or 0) >= 20.0
    checks["colours_allowed"] = ("data/palette.json (%d colours) plus data/nes_palette.json (%d entries)"
                                 % (len(game_allowed), len(nes_allowed)))
    checks["on_game_colours_min"] = VIDEO_PICTURE_MIN
    checks["game_picture_ok"] = bool(samples) and all(
        (s["on_game_colours"] or 0.0) >= VIDEO_PICTURE_MIN for s in samples)
    checks["nes_share_min"] = VIDEO_NES_SHARE_MIN
    checks["nes_palette_ok"] = bool(samples) and all(
        (s["nes_share"] or 0.0) >= VIDEO_NES_SHARE_MIN for s in samples)
    return checks


def look_rule(video):
    """The NES colour rule, measured on this recording and reported to its owner, never used as this card's pass.

    RULE 0 point 1 asks for colours picked from the NES master colours. The capture cannot answer that question and
    must not pretend to: what it can say is what the recording measures. Named here so the number travels with the
    ruling it belongs to instead of sitting in a pass or fail field the wrong lane reads.
    """
    return {
        "ok": video.get("nes_palette_ok", False),
        "rule": "RULE 0 point 1: every drawn colour is a NES 2C02 colour",
        "owner": "palette lane",
        "sources": "knowledge/ART-BIBLE.md, knowledge/PALETTE-SYNERGY.md S13, its open Q: at line 261, "
                   "data/nes_palette.json",
        "min_share": VIDEO_NES_SHARE_MIN,
        "measured": [{"at_s": s["at_s"], "nes_share": s["nes_share"]} for s in video.get("samples", [])],
        "gates_this_card": False,
        "note": "The battle screen draws data/palette.json's greys (28,28,36), (74,74,88); no 2C02 entry is within "
                "12 of them, so the walk and the fight measure near 0 here while the title measures 0.934. That is "
                "the palette lane's open question, not a failed capture: this verifier's ok turns on game_share.",
    }


def talk_leg():
    """The GOAL's TALK fight, measured against the game's own data instead of asserted either way.

    A three TALK spare needs a battle trigger whose encounter has talks_to_spare 3 (data/encounters/all.json) and
    whose tile the hero can stand on. Every battle trigger in data/maps/all.json is listed here with its one_shot
    flag and condition, so the report says whether such a fight exists to walk into, and what stops it.
    """
    maps = _read_json("maps/all.json")["maps"]
    encounters = {e["id"]: e for e in _read_json("encounters/all.json")["encounters"]}
    battles = []
    for entry in maps:
        for trigger in entry.get("triggers", []):
            if trigger.get("kind") != "battle":
                continue
            talk = (encounters.get(trigger.get("id"), {}).get("talk") or {})
            battles.append({
                "map": entry["id"],
                "tile": [trigger.get("x"), trigger.get("y")],
                "encounter": trigger.get("id"),
                "one_shot": bool(trigger.get("once")),
                "condition": trigger.get("condition") or "",
                "talks_to_spare": talk.get("talks_to_spare"),
            })
    reachable = [b for b in battles if b["talks_to_spare"] and not b["condition"]]
    return {
        "ok": bool(reachable),
        "gates_this_card": False,
        "why_not_gated": "The card's CHECK names the battle box, the FIGHT command, the victory text and the "
                         "muted line; the TALK leg is in its GOAL only. Whether a TALK fight can be walked into is "
                         "game data, not this capture's pass.",
        "battle_triggers": battles,
        "reachable_talk_fights": reachable,
        "note": "A three TALK spare IS walkable: tutorial_sailors, the deck's battle at ship_small (4,7), carries "
                "talks_to_spare 3 and no condition (data/encounters/all.json). This run takes the FIGHT path because "
                "the card's CHECK names the FIGHT command and the victory text, and the trigger is once: true, so "
                "the TALK path needs its own launch and its own output file. deck_hound, the other encounter with "
                "talks_to_spare 3, is a marker at quay (23,14), not a battle: walking onto it starts nothing.",
        "sources": "data/maps/all.json, data/encounters/all.json",
    }


def read_log_lines():
    if not os.path.isfile(GAME_LOG):
        return []
    with open(GAME_LOG, "r", encoding="utf-8", errors="replace") as fh:
        return [line.rstrip() for line in fh if line.strip()]


def check_outputs():
    """Score the frame sample and the mp4, write output\\first_fight_verify.json, and return its ok field."""
    roles = role_colours()
    geom = menu_geometry()
    labels = command_labels()
    glyph_ink = roles["ink"]
    frames = []
    for name in sorted(os.listdir(FRAME_DIR)) if os.path.isdir(FRAME_DIR) else []:
        if not name.endswith(".png"):
            continue
        path = os.path.join(FRAME_DIR, name)
        pixels, why = load_screen_pixels(path)
        if pixels is None:
            frames.append({"frame": name, "error": why})
            continue
        scores = score_frame(pixels, roles, geom, labels, text_colour=glyph_ink)
        try:
            at_second = float(name.split("_")[1].split(".")[0])
        except (IndexError, ValueError):
            at_second = None
        frames.append({"frame": name, "at_second": at_second, "scores": scores})

    battle_frames = [f for f in frames if "scores" in f and is_battle_frame(f["scores"])]
    menu_frames = [f for f in frames if "scores" in f and is_menu_frame(f["scores"])]
    victory_frames = [f for f in frames if "scores" in f and is_victory_frame(f["scores"])]

    lines = read_log_lines()
    muted = [line for line in lines if "PP: muted" in line]
    # The trigger's own line, printed unconditionally by pp_overworld_start_encounter: it names the encounter, the map
    # and the tile the hero stood on, so the log alone says the fight started. The director's "battle phase" line is
    # behind PP_DEBUG, which is false in a release build, so it can never appear in this run and is not checked.
    starts = [line for line in lines if line.startswith("PP: battle start")]
    talk_lines = [line for line in lines if "talk" in line.lower() and "PP" in line]
    crash = [line for line in lines if "PP CRASH" in line]

    video = video_checks(MP4_PATH)

    def best(rows, key, largest=True):
        if not rows:
            return None
        return sorted(rows, key=lambda row: row["scores"][key], reverse=largest)[0]

    checks = {
        "battle_box_in_sample": {
            "ok": bool(battle_frames),
            "frames": len(battle_frames),
            "first_at": battle_frames[0]["frame"] if battle_frames else None,
            "paper_min_required": BATTLE_BOX_MIN,
            "border_min_required": BATTLE_BORDER_MIN,
            "best": best(battle_frames, "battle_box_paper"),
        },
        "fight_command_in_sample": {
            "ok": bool(menu_frames),
            "frames": len(menu_frames),
            "first_at": menu_frames[0]["frame"] if menu_frames else None,
            "clusters_required": FIGHT_CLUSTERS,
            "ink_min_required": FIGHT_INK_MIN,
            "best": best(menu_frames, "battle_box_paper"),
        },
        "victory_text_in_sample": {
            "ok": bool(victory_frames),
            "frames": len(victory_frames),
            "first_at": victory_frames[0]["frame"] if victory_frames else None,
            "word_min_width_required": VICTORY_WORD_MIN,
            "press_min_width_required": VICTORY_PRESS_MIN,
            "best": best(victory_frames, "victory_panel_paper"),
        },
        "muted_line_in_log": {
            "ok": bool(muted),
            "line": muted[0] if muted else None,
            "lines_required": "PP: muted",
        },
        "battle_start_in_log": {
            "ok": bool(starts),
            "count": len(starts),
            "first": starts[0] if starts else None,
            "last": starts[-1] if starts else None,
            "lines_required": "PP: battle start",
        },
        "no_crash_in_log": {"ok": not crash, "crash_lines": crash[:5]},
        "video": video,
    }
    ok = (checks["battle_box_in_sample"]["ok"] and checks["fight_command_in_sample"]["ok"]
          and checks["victory_text_in_sample"]["ok"] and checks["muted_line_in_log"]["ok"]
          and checks["battle_start_in_log"]["ok"] and checks["no_crash_in_log"]["ok"]
          and video["exists"] and video["size_ok"] and video["duration_ok"] and video["game_picture_ok"])

    report = {
        "ok": ok,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "video": MP4_PATH,
        "frame_sample": FRAME_DIR,
        "sources": {
            "roles": "data/palette.json and data/room_palettes.json (deck_day)",
            "box": "pp_battle_director.gml pp_battle_draw_menu",
            "labels": "pp_battle_commands.gml",
            "geometry": geom,
        },
        "thresholds": {
            "battle_box_paper": BATTLE_BOX_MIN, "battle_box_border": BATTLE_BORDER_MIN,
            "fight_clusters": FIGHT_CLUSTERS, "fight_ink_min": FIGHT_INK_MIN,
            "victory_panel_paper": VICTORY_PANEL_MIN, "victory_word_width": VICTORY_WORD_MIN,
            "victory_press_width": VICTORY_PRESS_MIN,
        },
        "checks": checks,
        "look_rule": look_rule(video),
        "talk_leg": talk_leg(),
        "talk_lines": talk_lines[:10],
        "log_lines_total": len(lines),
        "frames": frames,
    }
    with open(VERIFY_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return ok, report


def print_report(report):
    print("P: ok=%s" % report["ok"])
    checks = report["checks"]
    for name in ("battle_box_in_sample", "fight_command_in_sample", "victory_text_in_sample",
                 "muted_line_in_log", "battle_start_in_log", "no_crash_in_log"):
        entry = checks[name]
        print("P: %-26s ok=%-5s %s" % (name, entry["ok"],
                                       {k: v for k, v in entry.items() if k not in ("ok", "best")}))
        best = entry.get("best")
        if best:
            scores = best["scores"]
            print("P:   best frame %s: box paper %.3f border %.3f FIGHT clusters %s ink %s "
                  "victory panel %.3f word %spx press %spx message rows %s"
                  % (best["frame"], scores["battle_box_paper"], scores["battle_box_border"],
                     (scores["cells"].get("FIGHT") or {}).get("clusters"),
                     (scores["cells"].get("FIGHT") or {}).get("ink_pixels"),
                     scores["victory_panel_paper"], scores["victory_word_width"],
                     scores["victory_press_width"], scores["message_text_rows"]))
    video = checks["video"]
    print("P: video %sx%s %s fps %.2f s, samples %s"
          % (video.get("width"), video.get("height"), video.get("fps"), video.get("duration_s") or 0.0,
             [(s["at_s"], s["game_share"], s["nes_share"]) for s in video.get("samples", [])]))
    print("P: look rule (not this card's gate) %s" % {k: v for k, v in report["look_rule"].items()
                                                      if k in ("ok", "min_share", "measured")})
    print("P: talk leg (not this card's gate) %s" % {k: report["talk_leg"][k] for k in
                                                     ("ok", "battle_triggers", "reachable_talk_fights")})
    print("P: wrote %s" % VERIFY_PATH)


def main():
    parser = argparse.ArgumentParser(description="record the first fight and check the recording")
    parser.add_argument("--check", action="store_true", help="only check the files already on disk")
    pp_launch.add_launch_flags(parser, default_wait=0.0)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not args.check:
        policy = pp_launch.policy_from_args(args)
        policy.min_idle = 120.0  # the card's own gate: two quiet minutes before a window opens
        if not policy.gate("first fight capture"):
            return pp_launch.EXIT_REFUSED
        code = run_capture(policy, show=args.show)
        if code != 0:
            print("P: the capture did not finish; no verify file was written")
            return code
    ok, report = check_outputs()
    print_report(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
