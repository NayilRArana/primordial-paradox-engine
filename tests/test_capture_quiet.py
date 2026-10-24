"""Pins for card CAPTURE-QUIET: a proof run is silent and out of sight, or it does not run.

What these tests hold down, and why each one earns its place:
  1. the idle gate refuses while input is recent, allows after three quiet minutes, refuses when this host cannot report
     the idle time at all, and a wait that runs out is a skip and not a launch;
  2. the selftest table in tools\\idle_check.py still answers every one of those rows correctly;
  3. every game launch is started with PP_MUTE=1, and --sound clears an inherited mute instead of setting it;
  4. every launch site in tools\\capture_title.py, tools\\play_demo.py and the four probe tools goes through
     tools\\pp_launch.py, so no lane can add a launch that skips the gate or the mute;
  5. the game reads PP_MUTE at boot and takes the master gain to 0, the variable is a macro in pp_config so the
     project check accepts it, and the hook stays OUT of pp_audio.gml (the card's own Q: it is one guard line in
     pp_app.gml and nothing else);
  6. the placement arithmetic puts a window on a second monitor, and answers None honestly on a one monitor host;
  7. the rule is written down in knowledge\\ART-BIBLE.md and none of the new files carries an em dash or an en dash.

Run: python -m pytest tests/test_capture_quiet.py -q
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

MIN_IDLE = 180.0
# This PC's own layout, measured on 2026-10-22: one 1920x1080 primary at 0,0 and a second monitor beside it, so the
# virtual desktop is 3840x1080. The placement test uses these numbers rather than a made up pair.
PRIMARY = (0, 0, 1920, 1080)
VIRTUAL = (0, 0, 3840, 1080)


def load(name: str):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def source(name: str) -> str:
    return read(os.path.join(TOOLS, name + ".py"))


# ---------------------------------------------------------------------------------------------------------------------
# 1 and 2: the gate

def test_gate_refuses_while_input_is_recent():
    idle_check = load("idle_check")
    lines = []
    allowed, idle = idle_check.check(idle_read=lambda: 5.0, min_idle=MIN_IDLE, say=lines.append)
    assert allowed is False
    assert idle == 5.0
    text = " ".join(lines)
    assert "SKIPPED" in text
    assert "P: " in text


def test_gate_allows_after_three_quiet_minutes():
    idle_check = load("idle_check")
    lines = []
    allowed, idle = idle_check.check(idle_read=lambda: 600.0, min_idle=MIN_IDLE, say=lines.append)
    assert allowed is True
    assert idle == 600.0
    assert "allows the launch" in " ".join(lines)


def test_gate_refuses_when_the_idle_time_cannot_be_read():
    """A host that cannot measure the idle time cannot promise nobody is at the keyboard, so it refuses."""
    idle_check = load("idle_check")
    lines = []
    allowed, idle = idle_check.check(idle_read=lambda: None, min_idle=MIN_IDLE, say=lines.append)
    assert allowed is False
    assert idle is None
    assert "REFUSED" in " ".join(lines)


def test_gate_refuses_on_a_non_windows_host():
    idle_check = load("idle_check")
    allowed, idle = idle_check.check(idle_read=None, min_idle=MIN_IDLE, say=lambda line: None)
    if sys.platform == "win32":
        # On this PC the real read answers with a number; the point of this row is the None branch, tested above.
        assert idle is None or idle >= 0.0
    else:
        assert allowed is False and idle is None


def test_a_wait_that_runs_out_is_a_skip():
    idle_check = load("idle_check")
    ticks = {"t": 0.0}
    allowed, _idle = idle_check.check(idle_read=lambda: 10.0, min_idle=MIN_IDLE, wait_s=60.0, poll_s=20.0,
                                      clock=lambda: ticks["t"],
                                      sleep=lambda seconds: ticks.__setitem__("t", ticks["t"] + seconds),
                                      say=lambda line: None)
    assert allowed is False
    assert ticks["t"] == pytest.approx(60.0)


def test_a_wait_takes_the_launch_when_the_user_goes_quiet():
    idle_check = load("idle_check")
    values = [10.0, 20.0, 200.0]
    ticks = {"t": 0.0, "n": 0}

    def idle_read():
        value = values[min(ticks["n"], len(values) - 1)]
        ticks["n"] += 1
        return value

    allowed, idle = idle_check.check(idle_read=idle_read, min_idle=MIN_IDLE, wait_s=60.0, poll_s=20.0,
                                     clock=lambda: ticks["t"],
                                     sleep=lambda seconds: ticks.__setitem__("t", ticks["t"] + seconds),
                                     say=lambda line: None)
    assert allowed is True
    assert idle == 200.0


def test_force_is_the_only_override():
    idle_check = load("idle_check")
    lines = []
    allowed, _idle = idle_check.verdict(idle_read=lambda: 3.0, min_idle=MIN_IDLE, force=True, say=lines.append)
    assert allowed is True
    assert "OVERRIDDEN" in " ".join(lines)


def test_the_selftest_table_passes():
    idle_check = load("idle_check")
    assert idle_check.selftest(say=lambda line: None) == 0


def test_the_refusal_exit_code_is_not_the_watchdog_code():
    """capture_title.py and play_demo.py both exit 3 when the watchdog fires, so a skip must not be a 3."""
    idle_check = load("idle_check")
    assert idle_check.EXIT_REFUSED == 4


def test_the_gate_reuses_the_manager_guard_arithmetic():
    """The card asks for the manager's GetLastInputInfo logic, not a second way to ask Windows."""
    text = source("idle_check")
    assert "GetLastInputInfo" in text
    assert "GetTickCount" in text
    assert "LASTINPUTINFO" in text


# ---------------------------------------------------------------------------------------------------------------------
# 3: the environment

def test_game_env_mutes_by_default():
    pp_launch = load("pp_launch")
    env = pp_launch.game_env(base={"PATH": "/bin", "PP_SHIP_CAPTURE": "1"})
    assert env["PP_MUTE"] == "1"
    # The caller's own capture flags survive, which is what the ship and scroll captures rely on.
    assert env["PP_SHIP_CAPTURE"] == "1"
    assert env["PATH"] == "/bin"


def test_sound_clears_an_inherited_mute():
    pp_launch = load("pp_launch")
    env = pp_launch.game_env(sound=True, base={"PP_MUTE": "1", "PATH": "/bin"})
    assert "PP_MUTE" not in env
    assert env["PATH"] == "/bin"


def test_the_policy_carries_the_flags():
    pp_launch = load("pp_launch")
    quiet = pp_launch.Policy()
    assert quiet.env()["PP_MUTE"] == "1"
    assert "PP_MUTE" not in pp_launch.Policy(sound=True).env()
    lines = []
    loud = pp_launch.Policy(sound=True, idle_read=lambda: 500.0, say=lines.append)
    assert loud.gate("audio proof") is True
    assert "cleared for an audio proof" in " ".join(lines)
    recent = pp_launch.Policy(idle_read=lambda: 1.0, say=lines.append)
    assert recent.gate("capture") is False


def test_the_three_minute_rule_is_the_default():
    pp_launch = load("pp_launch")
    assert pp_launch.MIN_IDLE_S == 180.0
    assert pp_launch.Policy().wait_s == 0.0


# ---------------------------------------------------------------------------------------------------------------------
# 4: every launch site goes through the policy

# The seven places tools\capture_title.py opens a window: the six captures and the notepad selftest.
CAPTURE_LAUNCHES = (
    ("run_video_capture", 'LAUNCH.gate("title video capture")'),
    ("run_game_capture", 'LAUNCH.gate("title capture")'),
    ("run_ship_capture", 'LAUNCH.gate("ship room capture")'),
    ("run_intro_capture", 'LAUNCH.gate("intro capture")'),
    ("run_keys_capture", 'LAUNCH.gate("keys capture")'),
    ("run_scroll_capture", 'LAUNCH.gate("title scroll capture")'),
    ("run_selftest", 'LAUNCH.gate("capture selftest")'),
)


def function_body(text: str, name: str) -> str:
    """The source of one top level function, from its def to the next top level def.

    The GML files carry CRLF line endings and the Python files here do not, so the text is normalised first: a regex
    written against "\\ndef " would otherwise miss every GML function, which is how this helper first failed.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.search(r"\ndef %s\(" % re.escape(name), text)
    assert match, "no function %s" % name
    rest = text[match.end():]
    following = re.search(r"\ndef [a-zA-Z_]", rest)
    return rest[:following.start()] if following else rest


@pytest.mark.parametrize("name,marker", CAPTURE_LAUNCHES)
def test_each_capture_path_asks_the_gate(name, marker):
    body = function_body(source("capture_title"), name)
    assert marker in body, "%s does not ask the idle gate" % name
    assert "return IDLE_REFUSED" in body, "%s does not return the refusal code" % name


@pytest.mark.parametrize("name,_marker", CAPTURE_LAUNCHES)
def test_each_capture_path_starts_the_game_muted(name, _marker):
    body = function_body(source("capture_title"), name)
    if name == "run_selftest":
        # The selftest opens notepad, not the game, so there is no environment to set: it is gated, not muted.
        assert "notepad.exe" in body
        return
    # Card CAPTURE-QUIET-IMPL: the launch itself moved into pp_launch.start_game, which owns the mute, the missing
    # console window and the PP: muted line, so a site is proved by calling it and by not starting the game itself.
    # Card PINE-HONEST (t_84fe63ff): play_demo now imports pp_launch on first use, so the call reads
    # launch.start_game( instead of pp_launch.start_game(. The property is the same one: the launch goes through
    # the helper rather than being built here, so the pin is on the call and not on the module prefix.
    assert ("pp_launch.start_game(" in body) or ("launch.start_game(" in body), \
        "%s does not start the game through the helper" % name
    assert 'label="' in body, "%s gives the helper no label for its lines" % name
    # ffmpeg is started here on purpose (the recorder), so the pin is on the game: no Popen of exe_path in the body.
    for match in re.finditer(r"subprocess\.Popen\(", body):
        assert "exe_path" not in body[match.start():match.start() + 300], \
            "%s still starts the game without the helper" % name


def test_the_window_goes_off_the_primary_screen_on_every_launch():
    text = source("capture_title")
    placements = text.count("LAUNCH.place(hwnd")
    launches = text.count('LAUNCH.gate("')
    assert placements == launches == len(CAPTURE_LAUNCHES)


@pytest.mark.parametrize("name", ("capture_title", "play_demo", "inspect_frame", "probe_states",
                                  "measure_title_scroll", "_save_load_probe"))
def test_every_launching_tool_uses_the_policy(name):
    text = source(name)
    assert "import pp_launch" in text
    # The gate and the environment, one or the other spelling, in every tool. Card CAPTURE-QUIET-IMPL added the third
    # spelling: start_game, which sets the environment and prints the muted line for the tool.
    assert ("pp_launch.Policy().gate(" in text) or ("LAUNCH.gate(" in text), "%s never asks the gate" % name
    assert ("pp_launch.game_env(" in text) or ("LAUNCH.env(" in text) or ("pp_launch.start_game(" in text) \
        or ("launch.start_game(" in text), \
        "%s never sets PP_MUTE" % name


def test_play_demo_records_what_it_was_told():
    text = source("play_demo")
    # Card PINE-HONEST (t_84fe63ff): both calls now go through the lazily imported launcher, so they read
    # launch.add_launch_flags( and launch.policy_from_args(. Same two properties, accessor instead of prefix.
    assert ("pp_launch.add_launch_flags(parser)" in text) or ("launch.add_launch_flags(parser)" in text)
    assert ("LAUNCH = pp_launch.policy_from_args(args)" in text) \
        or ("LAUNCH = launch.policy_from_args(args)" in text)


def test_capture_title_exposes_the_four_flags():
    text = source("capture_title")
    assert "pp_launch.add_launch_flags(parser)" in text
    assert "LAUNCH = pp_launch.policy_from_args(args)" in text
    flags = source("pp_launch")
    for flag in ("--sound", "--show", "--idle-wait", "--force"):
        assert flag in flags, "the launch flags lost %s" % flag


# ---------------------------------------------------------------------------------------------------------------------
# 5: the game side

def test_the_game_reads_pp_mute_at_boot():
    text = read(os.path.join(ROOT, "game", "scripts", "pp_app", "pp_app.gml")).replace("\r\n", "\n")
    assert "environment_get_variable(PP_MUTE) != \"1\"" in text
    assert "audio_master_gain(0)" in text
    # The call sits inside pp_app_boot and before the frame struct exists, so nothing can play first. The GML file opens
    # its functions with `function name()` rather than `def`, so the order is read from the text and not from a split.
    boot_at = text.index("function pp_app_boot(")
    mute_at = text.index("pp_app_mute_from_env();")
    frame_at = text.index("global.pp = {", boot_at)
    assert boot_at < mute_at < frame_at


def test_the_environment_name_is_a_macro():
    """The project check refuses a bare PP_ name in GML, so the name is a macro, split like PP_SLICE beside it.

    It sits in pp_app.gml and not in pp_config.gml on purpose: the title lane was editing pp_config.gml in the same
    hours as this card, and a name whose only reader is in this file does not need to widen that file's owner list.
    """
    text = read(os.path.join(ROOT, "game", "scripts", "pp_app", "pp_app.gml")).replace("\r\n", "\n")
    assert '#macro PP_MUTE "PP_" + "MUTE"' in text


def test_the_mute_hook_stays_out_of_the_audio_module():
    """The card's own Q: one guard line, and pp_audio.gml untouched. This is the check that keeps the answer true."""
    text = read(os.path.join(ROOT, "game", "scripts", "pp_audio", "pp_audio.gml"))
    assert "audio_master_gain" not in text
    assert "PP_MUTE" not in text


# ---------------------------------------------------------------------------------------------------------------------
# 6: the placement

def test_a_second_monitor_is_used_for_the_window():
    pp_launch = load("pp_launch")
    target = pp_launch.quiet_target((784, 759), PRIMARY, VIRTUAL)
    assert target == (1920, 0)
    # And the target is not inside the primary monitor's rectangle.
    left, top = target
    assert left >= PRIMARY[2] or top >= PRIMARY[3]


def test_a_one_monitor_host_gets_the_honest_answer():
    pp_launch = load("pp_launch")
    assert pp_launch.quiet_target((784, 759), PRIMARY, PRIMARY) is None


def test_show_leaves_the_window_alone():
    pp_launch = load("pp_launch")
    lines = []
    moved, note = pp_launch.Policy(show=True, say=lines.append).place(object())
    assert moved is False
    assert "--show" in note
    assert any("--show" in line for line in lines)


# ---------------------------------------------------------------------------------------------------------------------
# 7: the rule is written down, and nothing new carries a long dash

def test_the_rule_is_written_down():
    text = read(os.path.join(ROOT, "knowledge", "ART-BIBLE.md"))
    assert "RULE 1" in text and "CAPTURE-QUIET" in text
    for needle in ("PP_MUTE", "tools\\idle_check.py", "tools\\pp_launch.py", "three minutes"):
        assert needle in text, "the rule does not name %s" % needle


@pytest.mark.parametrize("path", ("tools/idle_check.py", "tools/pp_launch.py", "tools/capture_title.py",
                                 "tools/play_demo.py", "tools/inspect_frame.py", "tools/probe_states.py",
                                 "tools/measure_title_scroll.py", "tools/_save_load_probe.py",
                                 "knowledge/ART-BIBLE.md", "tests/test_capture_quiet.py"))
def test_no_em_dash_or_en_dash(path):
    """Nayil's standing rule: no em dash, en dash or similar long dash punctuation in any response or artifact."""
    text = read(os.path.join(ROOT, *path.split("/")))
    for dash in ("\u2014", "\u2013", "\u2012", "\u2015"):
        assert dash not in text, "%s carries a long dash (%r)" % (path, dash)
