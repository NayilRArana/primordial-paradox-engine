#!/usr/bin/env python3
"""capture_talk_fight.py: record the built game from the ship spawn to a TALK spare, and check the recording.

Why this file exists (card t_27aa179e, raised by testing from card t_87ee4228): the parent card's GOAL names "the TALK
fight reached through three TALK options" and its CHECK names only the FIGHT path. The FIGHT capture at
output\\first_fight_capture.mp4 is green and proves a fight was fought. It cannot prove a fight was talked through, and
neither can any other file in this tree, because the only line the battle wrote was `PP: battle start`, which says a
fight began and nothing about how it was answered.

This is the second run, not a second leg of the first: the deck's battle trigger at ship_small (4,7) is `once: true`,
so the FIGHT capture spent it. One launch, one trigger, one run, as the parent's own comment recorded before it stopped.

THE THREE RULINGS THIS CARD OWED (D15 in knowledge\\GAMEDEV-DECISIONS-2026-10-24.md):

  1. OUTPUT PATHS. The TALK run writes its own three files beside the FIGHT run's, never over them:
         output\\first_fight_talk_capture.mp4     the run, cropped to a true 3x of the 256x240 screen
         output\\first_fight_talk_verify.json     the verifier's report, with its own `ok` field
         output\\first_fight_talk_frames\\*.png    the frame sample the report scores, one a second
     The FIGHT capture alone does NOT satisfy the hackathon claim, because the claim is the talk path and the talk path
     is exactly what that video does not contain.

  2. ONE TOOL PER RUN. This is a separate tool from tools\\capture_first_fight.py, not a second schedule inside it. Two
     reasons, both mechanical: a run that writes to a sibling's paths can silently replace evidence another card signed
     off (this file opens its own log, its own raw recording and its own verify json), and a verifier whose `ok` starts
     depending on a second run is a verifier that fails for a reason it does not name. What IS shared is the reading
     code: role colours, palette snapping, the frame reader, the ink measures and the menu geometry are imported from
     capture_first_fight, so the two tools cannot drift apart about what the game's paper is.

  3. WHAT THIS CAPTURE MUST PROVE. Five things, each measured on the game's own files and its own draws:
     a. the battle is on screen: the command window is paper with a bounded edge (the parent's own measure);
     b. the cursor is on the TALK command: the TALK cell carries the label's ink across at least three of its four
        8 px glyphs, and the text role mark the menu draws beside the cursor row is beside THAT cell;
     c. three authored options are on screen: the option panel's three rows carry the three labels the encounter's
        talk dialogue names, each within its own 8 px per glyph width, at the band positions pp_talk_draw_options
        draws them;
     d. the reply board is on screen: the message window is paper and carries several rows of ink while the command
        band is not drawn, which is the panel shape only the talk reply path takes;
     e. the fight ends on the word `spare`: the result panel is paper, its outcome word is wider than the four glyph
        word `kill` and no wider than five glyphs at the 8 px pitch, and its `press Z` prompt is there;
     and the log, which the game writes itself:
     f. exactly three `PP: command talk` lines and zero `PP: command fight` lines, so the run never fought;
     g. three `PP: talk pick` lines whose mercy moves by the encounter's own mercy_per_option each time and reaches
        its mercy_to_spare on the third, plus three `PP: talk open` lines with the option count the data declares;
     h. one `PP: fight result spare` line with the enemy at FULL hp, which is what makes the spare the trust gate and
        not a health threshold;
     i. the muted line, one `PP: battle start` naming this encounter on this map, and no `PP CRASH`.

The run is DRIVEN BY THE LOG, not by a stopwatch. Card t_da94341c showed what a fixed press schedule costs: a fight
that ran longer than the schedule ended one turn short of its result panel. This driver reads the game's own lines out
of the log file as they are written (`pp_launch.wait_for_log_line` is the same read, used by tools\\capture_save.py mid
run) and presses only when the game says a press will land: the command list, and the option panel. Answer boards,
telegraphs and dodges take no press at all, so nothing here can accidentally choose FIGHT while waiting.

Usage:
    python tools\\capture_talk_fight.py                record, then check, and write all three outputs
    python tools\\capture_talk_fight.py --check        re-check the files already on disk, launching nothing
    python tools\\capture_talk_fight.py --idle-wait 600   poll for the machine to go quiet, then record
    python tools\\capture_talk_fight.py --show         leave the window on the primary screen (a person's run)
    python tools\\capture_talk_fight.py --force        the idle gate override, for a person at the keyboard

Exit codes:
    0  the recording was written and every check passed
    1  a check failed, the game window never appeared, or the game never reached a cue the driver waits for
    3  the watchdog fired (the run overran)
    4  the idle gate refused to open a window: there was recent input, so nothing was opened
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import capture_title as cap  # noqa: E402  the window, key and screen copy primitives proved on this PC
import play_demo  # noqa: E402  the gdigrab recorder and the viewport crop
import pp_launch  # noqa: E402  muted, idle gated launch policy (ruling D9)
import capture_first_fight as fig  # noqa: E402  the palette, frame reader and ink measures, shared not copied

OUTPUT_DIR = os.path.join(ROOT, "output")
FRAME_DIR = os.path.join(OUTPUT_DIR, "first_fight_talk_frames")
BUILD_DIR = os.path.join(ROOT, "build")
MP4_PATH = os.path.join(OUTPUT_DIR, "first_fight_talk_capture.mp4")
VERIFY_PATH = os.path.join(OUTPUT_DIR, "first_fight_talk_verify.json")
RAW_PATH = os.path.join(BUILD_DIR, "first_fight_talk_raw.mp4")
GAME_LOG = os.path.join(BUILD_DIR, "first_fight_talk_game.log")

SCREEN_W, SCREEN_H = fig.SCREEN_W, fig.SCREEN_H
SCALE = fig.SCALE
FPS = fig.FPS

WATCHDOG_S = 420.0
WINDOW_TIMEOUT_S = 25.0
SETTLE_S = 2.5
FRAME_EVERY_S = 1.0

# The title leg is the one the FIGHT run proved on this build: Enter opens the menu, Enter chooses NEW GAME, Enter skips
# the crawl for the ship. Seconds from the launch. From there the driver reads the log instead of counting.
TITLE_LEG = ((2.5, "enter"), (4.0, "enter"), (18.0, "enter"))
KEY_GAP_S = 0.35
HOLD_S = 1.8              # a longer read than a press, so the one-second frame sample lands on the list and panel

# The sheet's ink, and the room the recording's own compression needs around it. pp_font_draw paints the sheet with
# PP_UNTINTED, so a glyph is the sheet's colour and not a role: the sheet is (248,248,248) and this run's frames carry
# it as (232,231,236). Read from the shipped PNG at run time (sheet_ink), measured here for the tolerance.
GLYPH_TOLERANCE = 40
GLYPH_ROW_MIN = 3         # a row of a line of text carries at least this many glyph pixels
GLYPH_BAND_MIN = 20       # and a line carries at least this many across its rows
WALK_RETRY_S = 2.0
WALK_TRIES = 8
WALK_TIMEOUT_S = 45.0

MENU_TIMEOUT_S = 90.0     # the intro board types itself out, so this covers its pages and the frame slide
PANEL_TIMEOUT_S = 15.0    # the option panel opens on the same step the TALK press arrives
PICK_RETRY_S = 1.6        # per press, when a confirm is spent on the board above the panel
PICK_TRIES = 4
TURN_TIMEOUT_S = 120.0    # the reply board, the telegraph and the dodge, then the next command list
RESULT_TIMEOUT_S = 25.0   # the SPARE press reaches the result board inside the same second
CLOSING_BOARD_S = 9.0     # the win spare board is three lines of typing, then the 30 step result beat
EXIT_HOLD_S = 4.0         # the map after the fight, held on video after the press that leaves the panel

# ---------------------------------------------------------------------------------------------------------------------
# Data the checks read, never restate

def _read_json(name):
    with open(os.path.join(ROOT, "data", name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def talk_encounter():
    """The encounter this card names, read from data, and the talk block it carries."""
    for entry in _read_json("encounters/all.json")["encounters"]:
        if entry.get("id") == "tutorial_sailors":
            return entry
    raise SystemExit("data/encounters/all.json has no tutorial_sailors, so this capture has nothing to walk into")


def option_labels():
    """The three option labels the panel draws, from the encounter's talk dialogue, as the game spells them.

    pp_talk_option_label strips the narration marker and the speech quotes and cuts to 28 columns, so the label the
    panel draws is the authored line without those two marks. Read here so the option rows are measured against the
    words the data names and not against whatever ink happens to be in the band.
    """
    encounter = talk_encounter()
    dialogue_id = (encounter.get("talk") or {}).get("options_dialogue") or ""
    rows = _read_json("dialogue/all.json")
    rows = rows["dialogue"] if isinstance(rows, dict) else rows
    for row in rows:
        if row.get("id") == dialogue_id:
            labels = []
            for line in row.get("lines") or []:
                text = str(line).strip()
                if text.startswith("* "):
                    text = text[2:]
                if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
                    text = text[1:-1]
                labels.append(text.strip()[:28])
            count = (encounter.get("talk") or {}).get("option_count")
            if isinstance(count, int) and count > 0:
                labels = labels[:count]
            if len(labels) < 2:
                raise SystemExit("the talk dialogue %r carries fewer than two option lines" % dialogue_id)
            return labels
    raise SystemExit("data/dialogue/all.json has no row %r, so the option panel's labels cannot be read"
                     % dialogue_id)


def talk_geometry():
    """The two facts the option panel is drawn from, pinned to the source text they are read out of.

    The same discipline the FIGHT tool's menu_geometry uses: a check that samples a rectangle the game stopped drawing
    is worse than no check. The ROWS are found in the frame (glyph_bands) rather than placed from these numbers,
    because this run's first attempt to place them from the pitch of one function measured frames drawn by another.
    What is pinned here is the one thing that has to hold for a cell to mean anything: the panel draws pp_font labels
    at x 24, so the left column of ink is the labels and not something else.
    """
    path = os.path.join(ROOT, "game", "scripts", "pp_battle_text", "pp_battle_text.gml")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if "pp_font_draw(_battle.talk_options[i].label, 24, _y, 1);" not in text:
        raise SystemExit("pp_talk_draw_options no longer draws its labels at x 24 with pp_font_draw; the option "
                         "rows this capture measures cannot be trusted")
    if "draw_triangle(14, _y, 14, _y + 8, 20, _y + 4, false);" not in text:
        raise SystemExit("pp_talk_draw_options no longer draws its cursor at x 14 to 20; the mark this capture "
                         "measures beside the option rows cannot be trusted")
    return {
        "label_x": 24,
        "cursor_x": (14, 20),
        "source": "pp_battle_text.gml pp_talk_draw_options",
    }


def roles_all():
    """The four battle roles, plus the game's own check that the cursor's role is not one of the ink roles."""
    roles = fig.role_colours()
    if roles["text"] in (roles["ink"], roles["paper"], roles["dim"]):
        raise SystemExit("the deck_day set gives the cursor role the same colour as a glyph role, so a cursor mark "
                         "beside the TALK cell could not be told apart from the label itself")
    return roles


# ---------------------------------------------------------------------------------------------------------------------
# Reading the game's log as it is written

def parse_menu(line):
    match = re.search(r"PP: battle menu, turn (\d+), cursor (\d+), enemy hp (\d+)/(\d+)", line)
    if not match:
        return None
    return {"turn": int(match.group(1)), "cursor": int(match.group(2)),
            "enemy_hp": int(match.group(3)), "enemy_max": int(match.group(4))}


def parse_open(line):
    match = re.search(r"PP: talk open, (\d+) options, mercy (\d+), trust (\d+)", line)
    if not match:
        return None
    return {"options": int(match.group(1)), "mercy": int(match.group(2)), "trust": int(match.group(3))}


def parse_pick(line):
    match = re.search(r"PP: talk pick, option (\d+), effect (\w+), mercy (\d+), trust (\d+)", line)
    if not match:
        return None
    return {"option": int(match.group(1)), "effect": match.group(2),
            "mercy": int(match.group(3)), "trust": int(match.group(4))}


def parse_command(line):
    match = re.search(r"PP: command (\w+), turn (\d+), enemy ([\w]+), enemy hp (\d+), party hp (\d+)", line)
    if not match:
        return None
    return {"key": match.group(1), "turn": int(match.group(2)), "enemy": match.group(3),
            "enemy_hp": int(match.group(4)), "party_hp": int(match.group(5))}


def parse_result(line):
    match = re.search(r"PP: fight result (\w+), turn (\d+), enemy ([\w]+), enemy hp (\d+)/(\d+)", line)
    if not match:
        return None
    return {"outcome": match.group(1), "turn": int(match.group(2)), "enemy": match.group(3),
            "enemy_hp": int(match.group(4)), "enemy_max": int(match.group(5))}


class LogTail(object):
    """The game's own log, read forward as the run writes it.

    Two cursors, and both matter. `position` is the byte the next read starts at, so only new bytes are parsed; a file
    that shrinks (a second launch truncating it) is restarted from the top rather than read past its end. `scanned` is
    the line the next `wait` starts looking from, so a line that arrived in the same chunk as the one a caller matched
    is still there for the caller after it. Without that second cursor a fast pair of lines would be half lost, and a
    driver that reads the game's state this way cannot afford to lose one.
    """

    def __init__(self, path):
        self.path = path
        self.position = 0
        self.scanned = 0
        self.lines = []

    def pump(self):
        new = []
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return new
        if size < self.position:
            self.position = 0
        if size <= self.position:
            return new
        with open(self.path, "rb") as handle:
            handle.seek(self.position)
            chunk = handle.read()
        # A line is only a line once its newline is written, so a partial tail is left for the next pump.
        if not chunk.endswith(b"\n"):
            cut = chunk.rfind(b"\n")
            if cut < 0:
                return new
            chunk = chunk[:cut + 1]
        self.position += len(chunk)
        for line in chunk.decode("utf-8", "replace").splitlines():
            if line.strip():
                new.append(line.rstrip())
        self.lines.extend(new)
        return new

    def wait(self, accept, timeout_s, poll_s=0.1):
        """The next line `accept` likes, or None when the timeout runs out. Returns (line, seconds waited)."""
        started = time.monotonic()
        while True:
            self.pump()
            while self.scanned < len(self.lines):
                line = self.lines[self.scanned]
                self.scanned += 1
                if accept(line):
                    return line, time.monotonic() - started
            if time.monotonic() - started >= timeout_s:
                return None, time.monotonic() - started
            time.sleep(poll_s)


# ---------------------------------------------------------------------------------------------------------------------
# The launch and the run

def build():
    found = cap.newest_build()
    if found is None:
        raise SystemExit("no built game under %s: run the build first" % cap.GAME_OUTPUT_DIR)
    return found


def start_recorder(rect, out_path):
    """gdigrab on the viewport, with a pipe on stdin so the recording ends on ffmpeg's own quit key.

    No -t: the run's length is decided by the game, not by a stopwatch (card t_27d9a3b0 measured the cost of the other
    way round: a schedule that stops early cuts the result panel out of the video). A plain terminate would kill ffmpeg
    before it writes the mp4 trailer, which reads as "moov atom not found" afterwards.
    """
    left, top, width, height = rect
    if os.path.exists(out_path):
        os.remove(out_path)
    log_path = os.path.join(BUILD_DIR, "first_fight_talk_ffmpeg.log")
    handle = open(log_path, "wb")
    arguments = [
        play_demo.FFMPEG, "-hide_banner", "-y",
        "-f", "gdigrab", "-framerate", str(FPS),
        "-offset_x", str(left), "-offset_y", str(top),
        "-video_size", "%dx%d" % (width, height),
        "-i", "desktop",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
        out_path,
    ]
    process = subprocess.Popen(arguments, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    return process, handle, log_path


def stop_recorder(process, handle):
    """End ffmpeg on its own quit key so the trailer is written, then let go of its log."""
    if process is None:
        return
    try:
        process.stdin.write(b"q")
        process.stdin.flush()
        process.stdin.close()
        process.wait(timeout=40)
    except Exception:  # gate: ok a recorder that will not take the key is stopped below, and the duration check decides
        try:
            process.terminate()
            process.wait(timeout=20)
        except Exception:  # gate: ok best effort, the file's own duration is what the verifier reads
            pass
    try:
        handle.close()
    except Exception:  # gate: ok the handle is closed for tidiness and its failure cannot change the verdict
        pass


def sample_frames(mp4_path, fps=FRAME_EVERY_S):
    """Cut the frame sample out of the recording, one picture a second, at the recording's own pixels."""
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR, ignore_errors=True)
    os.makedirs(FRAME_DIR, exist_ok=True)
    pattern = os.path.join(FRAME_DIR, "t_%04d.png")
    arguments = [play_demo.FFMPEG, "-hide_banner", "-y", "-i", mp4_path,
                 "-vf", "fps=%g" % float(fps), "-start_number", "0", pattern]
    done = subprocess.run(arguments, capture_output=True, stdin=subprocess.DEVNULL, timeout=300)
    if done.returncode != 0:
        print("P: ffmpeg could not cut the frame sample: %s"
              % (done.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:])
    return len([name for name in os.listdir(FRAME_DIR) if name.endswith(".png")])


def press_key(hwnd, key):
    return fig.press(hwnd, key, cap.KEY_CODES[key])


def move_cursor(hwnd, from_slot, to_slot, count, notes):
    """Down presses until the cursor sits on `to_slot`. Down is the only direction this needs.

    The command list wraps, so the distance is a modulo against the list's own length, read from
    pp_battle_commands.gml through capture_first_fight.command_labels. The cursor the game reports is the start.
    """
    downs = (to_slot - from_slot) % count
    for _ in range(downs):
        notes.append("down %s" % press_key(hwnd, "down"))
        time.sleep(KEY_GAP_S)
    return downs


def drive(hwnd, tail, notes):
    """Drive the run from the title to the spare, pressing only where the game's own log says a press lands.

    Returns (ok, note). Every press is written into `notes`, with the seconds it went out, so the report can say what
    the run did without the reviewer having to replay it.
    """
    labels = fig.command_labels()
    talk_slot = labels.index("TALK")
    spare_slot = labels.index("SPARE")
    count = len(labels)
    encounter = talk_encounter()
    talk = encounter.get("talk") or {}
    talks = int(talk.get("talks_to_spare") or 3)
    started = time.monotonic()

    def at_second(target):
        now = time.monotonic() - started
        if now < target:
            time.sleep(target - now)

    for at_s, key in TITLE_LEG:
        at_second(at_s)
        notes.append("%.1f s %s %s" % (time.monotonic() - started, key, press_key(hwnd, key)))

    # The deck has to be live before a press can mean anything: the run's own entry autosave line names the map it
    # landed on and the tile it landed on, and it is written once per entry.
    deck_line, waited = tail.wait(lambda line: line.startswith("PP: autosave,"), WALK_TIMEOUT_S)
    if not deck_line:
        return False, "the run never reached a map within %.0f s of the title" % WALK_TIMEOUT_S
    notes.append("run start: %s" % deck_line)
    if "+" + "ship_small" not in deck_line and " ship_small " not in deck_line:
        return False, "the run started on a map that is not the deck: %s" % deck_line

    # The battle trigger is a CONFIRM trigger, not a walk-on one (pp_overworld_step: only a marker fires on touch).
    # pp_overworld_confirm_target reads the tile the hero faces first and the tile under him second, so one step east
    # and one confirm is the press a player makes to open this fight. Each retry is the same pair again, which is why
    # a run whose title leg landed late still reaches the fight instead of walking past it.
    trigger, attempt = None, 0
    for attempt in range(WALK_TRIES):
        notes.append("%.1f s right %s" % (time.monotonic() - started, press_key(hwnd, "right")))
        time.sleep(KEY_GAP_S)
        notes.append("%.1f s z %s (the tile ahead)" % (time.monotonic() - started, press_key(hwnd, "z")))
        trigger, waited = tail.wait(lambda line: line.startswith("PP: battle start"), WALK_RETRY_S)
        if trigger:
            break
    if not trigger:
        return False, "the deck trigger never fired in %d walk-and-confirm attempts" % WALK_TRIES
    notes.append("battle start after %d walk-and-confirm attempt(s): %s" % (attempt + 1, trigger))

    menu_line, waited = tail.wait(lambda line: parse_menu(line) is not None, MENU_TIMEOUT_S)
    cue = parse_menu(menu_line) if menu_line else None
    if cue is None:
        return False, "the command list never opened within %.0f s of the fight starting" % MENU_TIMEOUT_S
    notes.append("menu turn %d cursor %d" % (cue["turn"], cue["cursor"]))

    for turn in range(talks):
        downs = move_cursor(hwnd, cue["cursor"], talk_slot, count, notes)
        notes.append("turn %d: %d down press(es) onto %s, then confirm" % (turn + 1, downs, labels[talk_slot]))
        # Hold on the list with the cursor on TALK. The frame sample is one copy a second, and a run that presses the
        # moment the list opens can be over before a sample lands on it: the first run of this tool wrote 63 frames and
        # not one of them held the command list. A player reads the list before pressing, so the capture holds too.
        time.sleep(HOLD_S)
        notes.append("z %s" % press_key(hwnd, "z"))
        opened, _waited = tail.wait(lambda line: parse_open(line) is not None, PANEL_TIMEOUT_S)
        if not opened:
            return False, "the TALK panel did not open on turn %d" % (turn + 1)
        notes.append("panel: %s" % opened)
        # Same hold for the panel: the three options are the frame the claim is about.
        time.sleep(HOLD_S)
        # One press per attempt, up to PICK_TRIES. The panel's confirm is an edge on the frame it is read, and a press
        # that lands on the tail of the reply board above the panel is spent there, which is exactly what happened on
        # turn 2 of the first run this tool made. A player presses again; so does this, and it stops on the pick line
        # rather than on a count, so a press that lands the first time is the only press sent.
        picked = None
        for attempt in range(PICK_TRIES):
            notes.append("z %s (first option, press %d of %d)" % (press_key(hwnd, "z"), attempt + 1, PICK_TRIES))
            picked, _waited = tail.wait(lambda line: parse_pick(line) is not None, PICK_RETRY_S)
            if picked:
                break
        if not picked:
            return False, "the TALK pick did not apply on turn %d after %d presses" % (turn + 1, PICK_TRIES)
        notes.append("pick: %s" % picked)
        menu_line, _waited = tail.wait(lambda line: parse_menu(line) is not None, TURN_TIMEOUT_S)
        cue = parse_menu(menu_line) if menu_line else None
        if cue is None:
            return False, "the command list did not come back after turn %d" % (turn + 1)
        notes.append("menu turn %d cursor %d" % (cue["turn"], cue["cursor"]))

    downs = move_cursor(hwnd, cue["cursor"], spare_slot, count, notes)
    notes.append("%d down press(es) onto %s, then confirm" % (downs, labels[spare_slot]))
    notes.append("z %s" % press_key(hwnd, "z"))
    result_line, _waited = tail.wait(lambda line: parse_result(line) is not None, RESULT_TIMEOUT_S)
    if not result_line:
        return False, "the fight never reached a result after the SPARE press"
    notes.append("result: %s" % result_line)

    # The closing board types itself out, then the 30 step result beat, then the panel waits on a confirm. Two presses
    # leave it with room for the map and the epilogue scene after them.
    time.sleep(CLOSING_BOARD_S)
    notes.append("closing board done, leaving the panel: z %s" % press_key(hwnd, "z"))
    time.sleep(EXIT_HOLD_S)
    notes.append("map: z %s" % press_key(hwnd, "z"))
    time.sleep(EXIT_HOLD_S)
    return True, "the run reached a result: %s" % result_line


def run_capture(policy, show=False):
    exe_path, win_path = build()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(FRAME_DIR, exist_ok=True)
    if os.path.exists(GAME_LOG):
        os.remove(GAME_LOG)
    print("P: launching %s -game %s" % (exe_path, win_path))
    print("P: the run is driven by the game's own log, so its length is decided by the game and not by a schedule")

    run = pp_launch.start_game(exe_path, win_path, log_path=GAME_LOG, policy=policy, label="talk fight capture")
    cap.start_watchdog(run.process, WATCHDOG_S)
    recorder = None
    recorder_handle = None
    try:
        match = cap.find_window(
            lambda hwnd, pid, title, visible, rect: visible and pid == run.process.pid
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

        rect, box, score, note = play_demo.pre_roll_viewport(hwnd, os.path.join(BUILD_DIR, "talk_preroll.png"))
        if box is None:
            print("P: the pre-roll frame is not the game: %s" % note)
            return 1
        print("P: viewport %s in the window, score %.3f" % (str(box), score))

        recorder, recorder_handle, rec_log = start_recorder(rect, RAW_PATH)
        notes = []
        tail = LogTail(GAME_LOG)
        ok, note = drive(hwnd, tail, notes)
        print("P: %s" % note)
        for line in notes:
            print("P: %s" % line)

        cap.close_window(hwnd)
        deadline = time.time() + 6.0
        while time.time() < deadline and run.alive():
            time.sleep(0.2)
        if run.alive():
            print("P: the game did not close on request, terminating it")
        stop_recorder(recorder, recorder_handle)
        recorder = None
        recorder_handle = None
        run.finish()

        if not ok:
            print("P: the drive stopped before the spare; the recording is %s and no verify file was written"
                  % RAW_PATH)
            return 1
        if not os.path.isfile(RAW_PATH) or os.path.getsize(RAW_PATH) == 0:
            print("P: the recorder wrote no file; the ffmpeg log is %s" % rec_log)
            return 1
        cut_ok, cut_note = play_demo.cut_and_scale(RAW_PATH, box,
                                                   {"record": {"width": SCREEN_W * SCALE,
                                                               "height": SCREEN_H * SCALE,
                                                               "fps": FPS}}, MP4_PATH, None)
        print("P: cut and scale: %s (%s)" % ("ok" if cut_ok else "failed", cut_note))
        if not cut_ok:
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
            except Exception:  # gate: ok the recorder's own error is already printed and must not mask it
                pass
# ---------------------------------------------------------------------------------------------------------------------
# The frame checks: measured on the game's own colours and its own draw geometry

def sheet_ink():
    """The colour the 8x8 sheet paints, read from the sheet the build ships.

    pp_font_draw paints the sheet with PP_UNTINTED, so what lands on screen is the sheet's own ink and NOT a role
    colour: on every frame this run sampled the glyphs carry (232,231,236) while the deck_day roles are 11/28/74/200.
    The sheet is the shipped PNG and its ink is (248,248,248); GLYPH_TOLERANCE is the room the recording's own
    compression needs between those two numbers, measured on this run's frames.
    """
    from PIL import Image
    path = os.path.join(ROOT, "game", "datafiles", "art", "spr_pp_font8.png")
    if not os.path.isfile(path):
        raise SystemExit("the font sheet %s is not in the build, so the colour its glyphs paint cannot be read" % path)
    counts = {}
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        source = image.load()
        for y in range(height):
            for x in range(width):
                pixel = source[x, y]
                counts[pixel] = counts.get(pixel, 0) + 1
    best = None
    for colour, count in counts.items():
        if max(colour) < 200:
            continue
        if best is None or count > best[1]:
            best = (colour, count)
    if best is None:
        raise SystemExit("spr_pp_font8.png carries no bright ink, so the glyphs cannot be measured")
    return best[0]


def glyph_mask(pixels, rect, colour, tolerance=GLYPH_TOLERANCE):
    """The pixels of one rectangle that are the sheet's ink within `tolerance`, as (x, y) pairs."""
    x1, y1, x2, y2 = rect
    out = []
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            pixel = pixels[x, y]
            if (abs(pixel[0] - colour[0]) <= tolerance and abs(pixel[1] - colour[1]) <= tolerance
                    and abs(pixel[2] - colour[2]) <= tolerance):
                out.append((x, y))
    return out


def glyph_bands(pixels, top, bottom, x1, x2, colour):
    """The rows of glyph ink inside a window, grouped into the bands one line of text occupies.

    The rows are FOUND, not assumed. pp_talk_draw_options spaces its rows at one pitch and pp_battle_draw_menu at
    another, and this run's first reading of the frames got that wrong because it copied a pitch out of one function
    and measured frames drawn by another. A band is a run of rows that carry ink, and a line of 8 px text is one.
    """
    bands = []
    current = None
    for y in range(top, bottom + 1):
        count = len(glyph_mask(pixels, (x1, y, x2, y), colour))
        if count >= GLYPH_ROW_MIN:
            if current is None:
                current = {"top": y, "bottom": y, "ink": count}
            else:
                current["bottom"] = y
                current["ink"] += count
        elif current is not None:
            bands.append(current)
            current = None
    if current is not None:
        bands.append(current)
    return [band for band in bands if band["ink"] >= GLYPH_BAND_MIN]


def cell_ink(pixels, band, x1, x2, colour):
    """The glyph ink of one label cell on one band, with the width its own ink spans."""
    rect = (x1, band["top"], x2, band["bottom"])
    mask = glyph_mask(pixels, rect, colour)
    if not mask:
        return {"rect": rect, "ink_pixels": 0, "bbox_width": 0}
    xs = [pixel[0] for pixel in mask]
    return {"rect": rect, "ink_pixels": len(mask), "bbox_width": max(xs) - min(xs) + 1}


def triangle_ink(pixels, band, colour):
    """The cursor triangle on one band: the text role mark both draw calls put at x 14 to x 20.

    pp_battle_draw_menu draws it at (label_x - 10, y) to (label_x - 4, y + 4) and pp_talk_draw_options at x 14 to 20,
    which is the same six columns. The role is the one colour a glyph is never painted in, so an exact match is right
    here and no tolerance is used.
    """
    return len(fig.ink_mask(pixels, (10, band["top"], 22, band["bottom"]), (colour,)))


def talk_scores(pixels, roles, geom, labels, options, colour):
    """Every number this report prints for one frame: the FIGHT tool's measures plus the talk ones.

    fig.score_frame is asked for the ink role, which is what its own report and its result panel are written in. The
    glyphs the command list and the option panel draw are NOT that role (pp_font paints the sheet's own colour), so
    the cells and the bands below are measured against `colour` instead.
    """
    scores = fig.score_frame(pixels, roles, geom, labels, text_colour=roles["ink"])
    band_top = geom["box"][1] + 1
    band_bottom = geom["box"][3] - 1
    bands = glyph_bands(pixels, band_top, band_bottom, 20, SCREEN_W - 8, colour)
    for band in bands:
        band["triangle"] = triangle_ink(pixels, band, roles["text"])
    scores["bands"] = bands

    talk_band = labels.index("TALK") // 2
    if talk_band < len(bands):
        scores["talk_cell"] = cell_ink(pixels, bands[talk_band], 24, 24 + 8 * len("TALK") - 1, colour)
    else:
        scores["talk_cell"] = {"rect": None, "ink_pixels": 0, "bbox_width": 0}

    rows = []
    for index, label in enumerate(options):
        width = 8 * len(label)
        if index < len(bands):
            row = cell_ink(pixels, bands[index], 24, 24 + width - 1, colour)
        else:
            row = {"rect": None, "ink_pixels": 0, "bbox_width": 0}
        row["expected_width"] = width
        row["label"] = label
        rows.append(row)
    scores["options"] = rows
    return scores


def box_drawn(scores):
    """The command window is on screen: paper filled inside its frame.

    Card t_27aa179e. This is fig.is_battle_frame without its border half, because the border half is a claim about the
    rows ABOVE this window and on the deck_day scene they are paper one row in three. Measured on 20 of the 63 frames
    this tool sampled: battle_box_paper 1.00 and battle_box_border 0.67 on every one, so the FIGHT tool's 0.70 border
    threshold is unreachable on this map while the window is plainly drawn. The paper share is the claim that matters
    here (there is a window), and the same number fig.BATTLE_BOX_MIN asks for.
    """
    return scores["battle_box_paper"] >= fig.BATTLE_BOX_MIN


def is_talk_frame(scores):
    """The command list with the cursor on TALK.

    Three bands of text in the window (the menu's three rows), the cursor triangle on the middle one, and the four
    glyph TALK label whose own ink spans most of its 32 px cell. The middle row is where TALK is because the command
    table lists it third, and the draw call puts entries 2 and 3 on the second row; the index is computed from the
    table, not written here.
    """
    bands = scores.get("bands") or []
    if len(bands) < 3:
        return False
    talk = scores["talk_cell"]
    middle = bands[len(bands) // 2]
    return (box_drawn(scores)
            and talk["bbox_width"] >= TALK_SPAN_MIN
            and talk["ink_pixels"] >= TALK_INK_MIN
            and middle["triangle"] >= CURSOR_INK_MIN)


def is_option_frame(scores):
    """The option panel: three bands of text, each as wide as the label the encounter's dialogue names."""
    rows = scores.get("options") or []
    if len(rows) < 3:
        return False
    if not box_drawn(scores):
        return False
    for row in rows:
        if row["ink_pixels"] < OPTION_INK_MIN:
            return False
        if row["bbox_width"] < row["expected_width"] * OPTION_WIDTH_FLOOR:
            return False
        if row["bbox_width"] > row["expected_width"]:
            return False
    return True


def is_reply_frame(scores):
    """A talk reply board: the message window is paper with several rows of ink, and no command list is drawn."""
    if scores["message_box_paper"] < MESSAGE_BOX_MIN or scores["message_text_rows"] < MESSAGE_ROWS_MIN:
        return False
    for cell in scores["cells"].values():
        if cell.get("bbox_width", 0) >= TALK_SPAN_MIN and cell.get("ink_pixels", 0) >= TALK_INK_MIN:
            return False
    return True


def is_spare_frame(scores):
    """The result panel with a five glyph word on it, which is what `spare` is and what `kill` is not."""
    return (scores["victory_panel_paper"] >= VICTORY_PANEL_MIN
            and SPARE_WORD_MIN <= scores["victory_word_width"] <= SPARE_WORD_MAX
            and scores["victory_press_width"] >= VICTORY_PRESS_MIN)


# Thresholds. Each is a structural property of the screen or of the game's own data, never a number copied from one
# run: a paper window with its dim edge, a four glyph TALK label, the text role mark beside it, three rows of the
# authored labels at their own widths, a paper message window with several rows of reply text, and a result panel
# whose word is wider than the four glyph `kill` (measured 31 px on output/first_fight_capture.mp4 frame f_0100) and
# no wider than five glyphs at the 8 px pitch (40 px).
TALK_SPAN_MIN = 28
TALK_INK_MIN = 30
CURSOR_INK_MIN = 8
OPTION_INK_MIN = 20
OPTION_WIDTH_FLOOR = 0.80
MESSAGE_BOX_MIN = 0.70
MESSAGE_ROWS_MIN = 3
VICTORY_PANEL_MIN = fig.VICTORY_PANEL_MIN
VICTORY_PRESS_MIN = fig.VICTORY_PRESS_MIN
SPARE_WORD_MIN = 33
SPARE_WORD_MAX = 44

VIDEO_PICTURE_MIN = fig.VIDEO_PICTURE_MIN


def video_checks(path):
    """The mp4 itself: the 3x viewport, a real duration, and frames that are the game's own picture.

    The picture gate is the union of data/palette.json and data/nes_palette.json, the same question and the same
    number as the frame reader (capture_first_fight.video_checks documents the measurement that made it a union). The
    samples are written under their own names so a run of this tool cannot replace the FIGHT run's samples on disk.
    """
    checks = {}
    ffprobe = cap.ffprobe_path(play_demo.FFMPEG)
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
    game_allowed = fig.game_palette()
    both_allowed = game_allowed + [c for c in nes_allowed if c not in game_allowed]
    samples = []
    if checks["exists"]:
        duration = checks.get("duration_s") or 0.0
        for fraction in (0.02, 0.2, 0.4, 0.55, 0.7, 0.85, 0.95):
            stamp = max(0.05, duration * fraction)
            out = os.path.join(BUILD_DIR, "talk_sample_%02d.png" % int(fraction * 100))
            ok = cap.extract_frame(play_demo.FFMPEG, path, stamp, out)
            both_share = play_demo.palette_share(out, both_allowed) if ok else None
            samples.append({"at_s": round(stamp, 2),
                            "on_game_colours": None if both_share is None else round(both_share, 4),
                            "ok": bool(ok)})
    checks["samples"] = samples
    checks["size_ok"] = checks.get("width") == SCREEN_W * SCALE and checks.get("height") == SCREEN_H * SCALE
    checks["duration_ok"] = (checks.get("duration_s") or 0) >= 20.0
    checks["colours_allowed"] = ("data/palette.json (%d colours) plus data/nes_palette.json (%d entries)"
                                 % (len(game_allowed), len(nes_allowed)))
    checks["on_game_colours_min"] = VIDEO_PICTURE_MIN
    checks["game_picture_ok"] = bool(samples) and all(
        (sample["on_game_colours"] or 0.0) >= VIDEO_PICTURE_MIN for sample in samples)
    return checks


def read_log_lines():
    if not os.path.isfile(GAME_LOG):
        return []
    with open(GAME_LOG, "r", encoding="utf-8", errors="replace") as handle:
        return [line.rstrip() for line in handle if line.strip()]


def check_outputs():
    """Score the frame sample, the mp4 and the game's own log, write the verify json, and return its ok field."""
    roles = roles_all()
    geom = fig.menu_geometry()
    geom_talk = talk_geometry()
    colour = sheet_ink()
    labels = fig.command_labels()
    options = option_labels()
    encounter = talk_encounter()
    talk = encounter.get("talk") or {}
    per_option = int(talk.get("mercy_per_option") or 0)
    to_spare = int(talk.get("mercy_to_spare") or 0)
    talks_needed = int(talk.get("talks_to_spare") or 0)
    enemy_id = (encounter.get("enemies") or [""])[0]
    enemy_row = {}
    for row in _read_json("enemies/all.json")["enemies"]:
        if row.get("id") == enemy_id:
            enemy_row = row
    enemy_max_hp = int(enemy_row.get("max_hp") or 0)

    frames = []
    for name in sorted(os.listdir(FRAME_DIR)) if os.path.isdir(FRAME_DIR) else []:
        if not name.endswith(".png"):
            continue
        path = os.path.join(FRAME_DIR, name)
        pixels, why = fig.load_screen_pixels(path)
        if pixels is None:
            frames.append({"frame": name, "error": why})
            continue
        scores = talk_scores(pixels, roles, geom, labels, options, colour)
        try:
            at_second = float(name.split("_")[1].split(".")[0])
        except (IndexError, ValueError):
            at_second = None
        frames.append({"frame": name, "at_second": at_second, "scores": scores})

    scored = [frame for frame in frames if "scores" in frame]
    battle_frames = [frame for frame in scored if box_drawn(frame["scores"])]
    talk_frames = [frame for frame in scored if is_talk_frame(frame["scores"])]
    option_frames = [frame for frame in scored if is_option_frame(frame["scores"])]
    reply_frames = [frame for frame in scored if is_reply_frame(frame["scores"])]
    spare_frames = [frame for frame in scored if is_spare_frame(frame["scores"])]

    lines = read_log_lines()
    muted = [line for line in lines if "PP: muted" in line]
    starts = [line for line in lines if line.startswith("PP: battle start")]
    commands = [parsed for parsed in (parse_command(line) for line in lines) if parsed]
    picks = [parsed for parsed in (parse_pick(line) for line in lines) if parsed]
    opens = [parsed for parsed in (parse_open(line) for line in lines) if parsed]
    results = [parsed for parsed in (parse_result(line) for line in lines) if parsed]
    crash = [line for line in lines if "PP CRASH" in line]

    talk_commands = [entry for entry in commands if entry["key"] == "talk"]
    fight_commands = [entry for entry in commands if entry["key"] == "fight"]
    spare_commands = [entry for entry in commands if entry["key"] == "spare"]
    mercy_steps = [entry["mercy"] for entry in picks]
    expected_mercy = [per_option * (index + 1) for index in range(len(picks))]
    spare_results = [entry for entry in results if entry["outcome"] == "spare"]
    kill_results = [entry for entry in results if entry["outcome"] == "kill"]

    video = video_checks(MP4_PATH)

    def best(rows, key):
        if not rows:
            return None
        return sorted(rows, key=lambda row: row["scores"][key], reverse=True)[0]

    best_battle = best(battle_frames, "battle_box_paper")

    checks = {
        "battle_box_in_sample": {
            "ok": bool(battle_frames),
            "frames": len(battle_frames),
            "first_at": battle_frames[0]["frame"] if battle_frames else None,
            "paper_min_required": fig.BATTLE_BOX_MIN,
            "border_reported_not_required": (best_battle["scores"]["battle_box_border"] if best_battle else None),
            "border_note": "the FIGHT tool's 0.70 border claim reads the rows above this window; on deck_day they are "
                           "paper one row in three (0.67 on every drawn frame), so this tool asks for the paper only",
            "best": best(battle_frames, "battle_box_paper"),
        },
        "talk_command_in_sample": {
            "ok": bool(talk_frames),
            "frames": len(talk_frames),
            "first_at": talk_frames[0]["frame"] if talk_frames else None,
            "span_min_required": TALK_SPAN_MIN,
            "ink_min_required": TALK_INK_MIN,
            "cursor_ink_min_required": CURSOR_INK_MIN,
            "best": best(talk_frames, "battle_box_paper"),
        },
        "option_panel_in_sample": {
            "ok": bool(option_frames),
            "frames": len(option_frames),
            "first_at": option_frames[0]["frame"] if option_frames else None,
            "labels": options,
            "ink_min_required": OPTION_INK_MIN,
            "width_floor": OPTION_WIDTH_FLOOR,
            "best": best(option_frames, "message_box_paper"),
        },
        "reply_board_in_sample": {
            "ok": bool(reply_frames),
            "frames": len(reply_frames),
            "first_at": reply_frames[0]["frame"] if reply_frames else None,
            "message_box_min_required": MESSAGE_BOX_MIN,
            "message_rows_min_required": MESSAGE_ROWS_MIN,
            "best": best(reply_frames, "message_text_rows"),
        },
        "spare_result_in_sample": {
            "ok": bool(spare_frames),
            "frames": len(spare_frames),
            "first_at": spare_frames[0]["frame"] if spare_frames else None,
            "panel_min_required": VICTORY_PANEL_MIN,
            "word_width_band": [SPARE_WORD_MIN, SPARE_WORD_MAX],
            "press_min_required": VICTORY_PRESS_MIN,
            "best": best(spare_frames, "victory_panel_paper"),
        },
        "muted_line_in_log": {
            "ok": bool(muted),
            "line": muted[0] if muted else None,
        },
        "battle_start_in_log": {
            "ok": len(starts) == 1 and encounter["id"] in starts[0],
            "count": len(starts),
            "first": starts[0] if starts else None,
            "expects": "%s on the map the trigger lives on" % encounter["id"],
        },
        "talk_commands_in_log": {
            "ok": len(talk_commands) == talks_needed and not fight_commands,
            "talk": len(talk_commands),
            "fight": len(fight_commands),
            "other": [entry["key"] for entry in commands if entry["key"] not in ("talk", "spare")],
            "expects": "%d talk commands and no fight command" % talks_needed,
            "lines": ["PP: command %s, turn %d" % (entry["key"], entry["turn"]) for entry in commands],
        },
        "talk_picks_in_log": {
            "ok": (len(picks) == talks_needed and mercy_steps == expected_mercy
                   and (not to_spare or mercy_steps[-1] == to_spare)
                   and all(entry["trust"] >= talks_needed for entry in picks[-1:])),
            "picks": len(picks),
            "mercy_measured": mercy_steps,
            "mercy_expected": expected_mercy,
            "mercy_to_spare": to_spare,
            "trust_measured": [entry["trust"] for entry in picks],
            "options_opened": [entry["options"] for entry in opens],
            "option_count_declared": talk.get("option_count"),
        },
        "spare_at_full_health_in_log": {
            "ok": bool(spare_commands) and enemy_max_hp > 0
            and spare_commands[-1]["enemy_hp"] == enemy_max_hp,
            "spare_command": spare_commands[-1] if spare_commands else None,
            "enemy_max_hp": enemy_max_hp,
            "note": "a spare whose command line carries the enemy's full bar came through the trust gate, not the "
                    "health threshold",
        },
        "spare_result_in_log": {
            "ok": len(spare_results) == 1 and not kill_results,
            "spare": len(spare_results),
            "kill": len(kill_results),
            "line": results[-1] if results else None,
        },
        "no_crash_in_log": {"ok": not crash, "crash_lines": crash[:5]},
        "video": video,
    }
    ok = all(checks[name]["ok"] for name in (
        "battle_box_in_sample", "talk_command_in_sample", "option_panel_in_sample", "reply_board_in_sample",
        "spare_result_in_sample", "muted_line_in_log", "battle_start_in_log", "talk_commands_in_log",
        "talk_picks_in_log", "spare_at_full_health_in_log", "spare_result_in_log", "no_crash_in_log"))
    ok = ok and video["exists"] and video["size_ok"] and video["duration_ok"] and video["game_picture_ok"]

    report = {
        "ok": ok,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "card": "t_27aa179e",
        "video": MP4_PATH,
        "frame_sample": FRAME_DIR,
        "sources": {
            "roles": "data/palette.json and data/room_palettes.json (deck_day)",
            "labels": "pp_battle_commands.gml, through capture_first_fight.command_labels",
            "options": "data/encounters/all.json talk.options_dialogue, through data/dialogue/all.json",
            "geometry": geom,
            "option_geometry": geom_talk,
        },
        "thresholds": {
            "talk_span": TALK_SPAN_MIN, "talk_ink": TALK_INK_MIN, "cursor_ink": CURSOR_INK_MIN,
            "option_ink": OPTION_INK_MIN, "option_width_floor": OPTION_WIDTH_FLOOR,
            "message_box": MESSAGE_BOX_MIN, "message_rows": MESSAGE_ROWS_MIN,
            "victory_panel_paper": VICTORY_PANEL_MIN, "spare_word_band": [SPARE_WORD_MIN, SPARE_WORD_MAX],
            "victory_press_width": VICTORY_PRESS_MIN,
        },
        "checks": checks,
        "frames": frames,
        "log_lines_total": len(lines),
    }
    with open(VERIFY_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return ok, report


def print_report(report):
    print("P: ok=%s" % report["ok"])
    checks = report["checks"]
    for name in ("battle_box_in_sample", "talk_command_in_sample", "option_panel_in_sample",
                 "reply_board_in_sample", "spare_result_in_sample", "muted_line_in_log", "battle_start_in_log",
                 "talk_commands_in_log", "talk_picks_in_log", "spare_at_full_health_in_log", "spare_result_in_log",
                 "no_crash_in_log"):
        entry = checks[name]
        print("P: %-28s ok=%-5s %s" % (name, entry["ok"],
                                       {key: value for key, value in entry.items()
                                        if key not in ("ok", "best", "lines")}))
        best = entry.get("best")
        if best:
            scores = best["scores"]
            talk = scores["talk_cell"]
            bands = scores["bands"]
            print("P:   best frame %s: box paper %.3f TALK span %spx ink %s bands %d triangle %s "
                  "message paper %.3f rows %s panel %.3f word %spx press %spx"
                  % (best["frame"], scores["battle_box_paper"],
                     talk["bbox_width"], talk["ink_pixels"], len(bands),
                     [band["triangle"] for band in bands],
                     scores["message_box_paper"], scores["message_text_rows"], scores["victory_panel_paper"],
                     scores["victory_word_width"], scores["victory_press_width"]))
    video = checks["video"]
    print("P: video %sx%s %s fps %.2f s, samples %s"
          % (video.get("width"), video.get("height"), video.get("fps"), video.get("duration_s") or 0.0,
             [(sample["at_s"], sample["on_game_colours"]) for sample in video.get("samples", [])]))
    print("P: wrote %s" % VERIFY_PATH)


def main():
    parser = argparse.ArgumentParser(description="record the TALK fight to a spare and check the recording")
    parser.add_argument("--check", action="store_true", help="only check the files already on disk")
    pp_launch.add_launch_flags(parser, default_wait=0.0)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not args.check:
        policy = pp_launch.policy_from_args(args)
        policy.min_idle = 120.0  # the card's own gate: two quiet minutes before a window opens
        if not policy.gate("talk fight capture"):
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

