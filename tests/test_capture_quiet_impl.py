"""Pins for card CAPTURE-QUIET-IMPL: one shared launch helper, and every launcher goes through it.

Ruling D9 of knowledge\\GAMEDEV-DECISIONS-2026-10-23.md makes two things evidence: the launch was muted, and it was idle
gated. The helper in tools\\pp_launch.py is where both live, and this file holds down the four claims the card makes:

  1. the helper sets PP_MUTE in the child environment before the process starts, and starts no console window;
  2. it refuses the GameMaker IDE and Igor by name, so no launcher can open a window through the IDE;
  3. it prints exactly one `PP: muted` line, and only when the game's own log carries that line, plus exactly one exit
     line from Run.finish();
  4. the launchers call it: every game launch site in tools\\capture_title.py, tools\\play_demo.py and
     tools\\capture_drive.py starts through start_game and closes through run.finish().

The idle threshold is D9's two minutes for a launcher. tools\\idle_check.py keeps its own three minute default for a
direct caller, and knowledge\\ART-BIBLE.md states that one, so both numbers are pinned here and there: this file checks
the launcher's number, tests\\test_capture_quiet.py checks the gate's.

Run: python -m pytest tests/test_capture_quiet_impl.py -q
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


def load(name: str):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(name: str) -> str:
    with open(os.path.join(TOOLS, name + ".py"), "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


class DeadProcess(object):
    """A process that has already ended, so the helper's close path is exercised without opening anything."""

    pid = 4242

    def poll(self):
        return 0


class LiveProcess(object):
    """A process that never ends on its own: kill_tree must force it, and the exit line must say it is still running."""

    pid = 4343

    def __init__(self):
        self.killed = False

    def poll(self):
        return None

    def kill(self):
        self.killed = True


# ---------------------------------------------------------------------------------------------------------------------
# 1: the environment and the window flag


def test_the_child_environment_is_muted_before_the_process_starts():
    pp_launch = load("pp_launch")
    assert pp_launch.game_env()["PP_MUTE"] == "1"
    assert "PP_MUTE" not in pp_launch.game_env(sound=True)
    policy = pp_launch.Policy()
    assert policy.env()["PP_MUTE"] == "1"
    # An extra flag the tool owns does not remove the mute.
    assert policy.env(extra={"PP_DRIVE_CAPTURE": "1"})["PP_MUTE"] == "1"


def test_no_console_window_is_asked_for():
    """CREATE_NO_WINDOW is 0x08000000, and start_game passes it on Windows."""
    pp_launch = load("pp_launch")
    assert pp_launch.NO_WINDOW == 0x08000000
    text = source("pp_launch")
    start = text[text.index("def start_game("):]
    assert "creationflags=flags" in start, "start_game does not pass a creation flag to Popen"
    assert "flags = NO_WINDOW if sys.platform" in start, "the flag is not the no console one on this host"


def test_the_launcher_idle_rule_is_two_minutes():
    """Ruling D9: an automatic launch waits for two minutes of machine idle."""
    pp_launch = load("pp_launch")
    assert pp_launch.D9_IDLE_S == 120.0
    assert pp_launch.Policy().min_idle == 120.0
    lines = []
    quiet = pp_launch.Policy(idle_read=lambda: 120.0, say=lines.append)
    assert quiet.gate("pin") is True
    assert "120 s" in " ".join(lines)
    recent = pp_launch.Policy(idle_read=lambda: 119.0, say=lambda line: None)
    assert recent.gate("pin") is False


# ---------------------------------------------------------------------------------------------------------------------
# 2: the IDE is refused


def test_the_ide_and_igor_are_refused_by_name(tmp_path):
    pp_launch = load("pp_launch")
    said = []
    for image in ("GameMaker.exe", "Igor.exe", "GameMakerStudio.exe"):
        exe = str(tmp_path / image)
        with pytest.raises(pp_launch.LaunchRefused):
            pp_launch.start_game(exe, str(tmp_path / "x.win"), log_path=str(tmp_path / "run.log"), say=said.append)
    text = " ".join(said)
    assert text.count("not the game") == 3
    assert "no window was opened" in text
    # Nothing was created: a refusal must not leave a log behind.
    assert not (tmp_path / "run.log").exists()


def test_a_launch_without_a_log_is_refused(tmp_path):
    """The muted line is the evidence, so a run that cannot write a log is not started at all."""
    pp_launch = load("pp_launch")
    with pytest.raises(pp_launch.LaunchRefused):
        pp_launch.start_game(str(tmp_path / "PrimordialParadox.exe"), str(tmp_path / "x.win"),
                             log_path=None, say=lambda line: None)


# ---------------------------------------------------------------------------------------------------------------------
# 3: exactly one PP: muted line and exactly one exit line


def test_the_muted_line_comes_from_the_games_own_log(tmp_path):
    pp_launch = load("pp_launch")
    log = tmp_path / "game.log"
    log.write_text("PP boot: data loaded\nPP: muted, PP_MUTE=1 in the environment, so the master gain is 0 for this run\n",
                   encoding="utf-8")
    said = []
    run = pp_launch.Run(DeadProcess(), log_path=str(log), label="pin", say=said.append)
    assert run.mute_evidence(timeout_s=1.0) is True
    # A second call is the same line, not a second one: the card asks for exactly one.
    assert run.mute_evidence(timeout_s=1.0) is True
    muted = [line for line in said if line.startswith("PP: muted")]
    assert len(muted) == 1, said
    assert "PP_MUTE=1" in muted[0]
    assert str(log) in muted[0]


def test_a_log_without_the_line_prints_no_muted_line(tmp_path):
    pp_launch = load("pp_launch")
    log = tmp_path / "game.log"
    log.write_text("PP boot: data loaded\n", encoding="utf-8")
    said = []
    run = pp_launch.Run(DeadProcess(), log_path=str(log), label="audio proof", say=said.append)
    assert run.mute_evidence(timeout_s=0.3) is False
    assert not [line for line in said if line.startswith("PP: muted")]
    assert "not evidence" in " ".join(said)


def test_no_log_named_means_no_muted_line():
    pp_launch = load("pp_launch")
    said = []
    run = pp_launch.Run(DeadProcess(), log_path=None, label="pin", say=said.append)
    assert run.mute_evidence(timeout_s=0.1) is False
    assert not [line for line in said if line.startswith("PP: muted")]


def test_finish_prints_one_exit_line_and_closes_the_game():
    pp_launch = load("pp_launch")
    said = []
    run = pp_launch.Run(DeadProcess(), log_path=None, label="pin", say=said.append)
    assert run.finish() == 0
    assert run.finish() == 0
    exits = [line for line in said if line.startswith("P: exit:")]
    assert len(exits) == 1, said
    assert "closed" in exits[0]
    assert "4242" in exits[0]


def test_finish_reports_a_game_that_will_not_close(monkeypatch):
    """A green exit line on a process that is still alive would be the exact lie D9 forbids."""
    pp_launch = load("pp_launch")
    monkeypatch.setattr(pp_launch, "kill_tree", lambda process, grace_s=0.0: False)
    said = []
    run = pp_launch.Run(LiveProcess(), log_path=None, label="pin", say=said.append)
    assert run.finish() == 1
    assert "STILL RUNNING" in " ".join(said)


# ---------------------------------------------------------------------------------------------------------------------
# 4: every launcher calls it


CAPTURE_TITLE_SITES = ("run_video_capture", "run_game_capture", "run_ship_capture", "run_intro_capture",
                       "run_keys_capture", "run_scroll_capture")


def function_body(text: str, name: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.search(r"\ndef %s\(" % re.escape(name), text)
    assert match, "no function %s" % name
    rest = text[match.end():]
    following = re.search(r"\ndef [a-zA-Z_]", rest)
    return rest[:following.start()] if following else rest


@pytest.mark.parametrize("name", CAPTURE_TITLE_SITES)
def test_each_title_capture_starts_and_closes_through_the_helper(name):
    body = function_body(source("capture_title"), name)
    assert "pp_launch.start_game(" in body
    assert "LAUNCH.gate(" in body
    assert "return IDLE_REFUSED" in body
    assert "run.finish()" in body, "%s never prints the exit line" % name


def test_play_demo_and_capture_drive_use_the_helper():
    for name in ("play_demo", "capture_drive"):
        text = source(name)
        # Card PINE-HONEST (t_84fe63ff): play_demo reaches pp_launch through launch_module(), so its call reads
        # launch.start_game(. capture_drive still imports the module directly. The property pinned is that the game
        # is started by the helper either way.
        assert ("pp_launch.start_game(" in text) or ("launch.start_game(" in text), \
            "%s does not start the game through the helper" % name
        assert "run.finish()" in text, "%s never prints the exit line" % name


def test_no_launcher_starts_the_game_itself():
    """The game is only ever started by pp_launch: a raw Popen of the runner in a launcher is the drift this card stops."""
    for name in ("capture_title", "play_demo", "capture_drive"):
        text = source(name)
        for match in re.finditer(r"subprocess\.Popen\(", text):
            window = text[match.start():match.start() + 400]
            assert "exe_path" not in window, "%s still starts the built game with a raw Popen" % name


# ---------------------------------------------------------------------------------------------------------------------
# 5: the rule is written down, and no long dashes


def test_the_helper_documents_the_ruling_and_the_lines():
    text = source("pp_launch")
    assert "GAMEDEV-DECISIONS-2026-10-23.md" in text
    assert "PP: muted" in text
    assert "D9_IDLE_S" in text


@pytest.mark.parametrize("name", ("pp_launch", "capture_title", "play_demo", "capture_drive"))
def test_no_em_dash_or_en_dash(name):
    text = source(name)
    for bad in ("\u2014", "\u2013"):
        assert bad not in text, "%s carries a long dash" % name
