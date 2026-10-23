"""A real save and a real load against the freshly built game, for card t_73f08da5 item 5.

The GML validator cannot be run without the game, so this drives the built exe: it writes a save
document with a chosen "music" value into the slot the game reads, launches the game, waits until
the game has answered that slot, and reports what it printed.

Three documents, same everything except music:
  ""        the baseline the game itself wrote on 2026-10-20
  "PP-05"   a cue id, which the card's fix has to accept
  "PP-99"   a cue id that does not exist, which must still be refused by name

WHY THIS FILE WAITS FOR AN ANSWER AND NOT FOR A CLOCK. The first version slept a flat nine seconds
and every run was killed before the slot was read, so a quiet log read as a clean load: silence
looked the same whether the document was accepted or never opened (round 1 review, 2026-10-22).
Nothing here counts as passed on silence.

THE POSITIVE MARKER. pp_save_parse prints "PP: save read and accepted, music <name>" for a document
that parsed and validated, and pp_save_fail prints "PP: save problem, <sentence>" for one that did
not. Both are answers about the slot, and a run that prints neither never read it. That pair is the
marker, so "read and accepted" cannot be mistaken for "never got there".

What the LOAD lines mean, corrected 2026-10-22. The runtime prints one "LOAD: numFiles N,
numBundleFiles 0" line per datafile read. One line is the slot this probe wrote: it appears before
the title plays anything, at the boot read. A second line is the backup read that follows a refused
main file, which is why the refusal run of 12:35 printed two and the accepted runs of the same
build printed one. The first version of this file read that count the wrong way round and reported
a successful load as "never read"; the count is now recorded as evidence beside the marker, not
used as the verdict.

A run with no answer at all is reported UNPROVEN and the script exits 2. The slot and its backup
are copied to the scratch folder first and restored at the end, and the sha256 of the restored slot
is compared with the copy.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pp_launch  # noqa: E402  the launch policy: PP_MUTE=1, the idle gate, and the quiet window (card CAPTURE-QUIET)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "PrimordialParadox")
EXE = os.path.join(OUT, "PrimordialParadox.exe")
WIN = os.path.join(OUT, "PrimordialParadox.win")
SAVE_DIR = os.path.join(os.environ["LOCALAPPDATA"], "PrimordialParadox", "default")
SAVE = os.path.join(SAVE_DIR, "pp_save_01.json")
BACKUP = os.path.join(SAVE_DIR, "pp_save_01.json.bak")
KEEP = os.path.join(ROOT, "build", "save_slot_probe")

ACCEPT_PREFIX = "PP: save read and accepted, music "
REFUSE_PREFIX = "PP: save problem, "

# Long enough for the title to ask the slot on a loaded machine: the nine second run of 2026-10-22
# reached "Entering main loop." and was killed before the answer. Each run stops the moment its
# answer appears, so this is a ceiling and not a wait.
DEADLINE_S = 60
FLUSH_S = 1.5

BASE = {
    "format": 1,
    "game_version": "0.1.0-slice",
    "saved_at": "2026-10-20 19:35:00",
    "play_seconds": 0,
    "map": "ship_small",
    "spawn": "start",
    "x": 2,
    "y": 7,
    "hp": 20,
    "max_hp": 20,
    "powers": [],
    "items": [],
    "flags": {},
    "counters": {"bosses_killed": 0, "bosses_spared": 0, "regulars_killed": 0, "regulars_spared": 0},
    "seen_scenes": [],
    "music": "",
}


def write_slot(music):
    document = dict(BASE)
    document["music"] = music
    text = json.dumps(document, separators=(",", ":"))
    payload = text.encode("utf-8")
    with open(SAVE, "wb") as handle:
        handle.write(len(payload).to_bytes(4, "little"))
        handle.write(payload)
        handle.write(b"\x00")
    return os.path.getsize(SAVE)


def _read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def _answer(lines):
    """The sentence the game printed about the slot, or "" when it printed none yet."""
    for line in lines:
        if line.startswith(REFUSE_PREFIX) or line.startswith(ACCEPT_PREFIX):
            return line
    return ""


def slot_reads(lines):
    """How many datafile reads the runtime reported. One is the slot, two adds the backup retry."""
    return sum(1 for line in lines if line.startswith("LOAD: numFiles"))


def run_game(tag):
    log_path = os.path.join(KEEP, "run_%s.log" % tag)
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen([EXE, "-game", WIN], cwd=OUT, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   env=pp_launch.game_env())
        started = time.time()
        while time.time() - started < DEADLINE_S:
            time.sleep(1.0)
            if _answer(_read_lines(log_path)) != "":
                break
            if process.poll() is not None:
                break
        # Give the line's neighbours their moment to land, then close the game.
        time.sleep(FLUSH_S)
        process.terminate()
        try:
            process.wait(timeout=8)
        except Exception:
            process.kill()
    return _read_lines(log_path), time.time() - started


def sha256(path):
    if not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    if not os.path.isfile(EXE) or not os.path.isfile(WIN):
        print("no built game at %s" % OUT)
        return 1
    # Card CAPTURE-QUIET: this probe launches the game three times, so the gate is asked once, before the first of
    # them, and a refusal leaves the save slot untouched.
    if not pp_launch.Policy().gate("save slot probe"):
        return pp_launch.EXIT_REFUSED
    os.makedirs(KEEP, exist_ok=True)
    original_digest = sha256(SAVE)
    if os.path.isfile(SAVE):
        shutil.copy2(SAVE, os.path.join(KEEP, "pp_save_01.original.json"))
    if os.path.isfile(BACKUP):
        shutil.copy2(BACKUP, os.path.join(KEEP, "pp_save_01.original.bak"))
        os.remove(BACKUP)

    results = {}
    unanswered = []
    for tag, music in (("empty", ""), ("cue", "PP-05"), ("bogus", "PP-99")):
        size = write_slot(music)
        lines, elapsed = run_game(tag)
        answer = _answer(lines)
        accepted = answer.startswith(ACCEPT_PREFIX)
        refused = answer.startswith(REFUSE_PREFIX)
        read = accepted or refused
        results[tag] = {"music": music, "bytes": size, "answer": answer or None,
                        "read": read, "accepted": accepted, "refused": refused,
                        "slot_reads": slot_reads(lines), "seconds": round(elapsed, 1),
                        "lines": len(lines)}
        if not read:
            unanswered.append(tag)
        print("music=%-6r bytes=%d seconds=%.1f datafile reads=%d read=%s outcome=%s %s"
              % (music, size, elapsed, slot_reads(lines), "YES" if read else "NO",
                 "accepted" if accepted else ("refused" if refused else "NO ANSWER"), answer))

    # Put the player's own slot back exactly as it was, and prove it byte for byte.
    if os.path.isfile(os.path.join(KEEP, "pp_save_01.original.json")):
        shutil.copy2(os.path.join(KEEP, "pp_save_01.original.json"), SAVE)
    if os.path.isfile(os.path.join(KEEP, "pp_save_01.original.bak")):
        shutil.copy2(os.path.join(KEEP, "pp_save_01.original.bak"), BACKUP)
    elif os.path.isfile(BACKUP):
        os.remove(BACKUP)
    restored_digest = sha256(SAVE)
    print("slot restored: %s (was %s)" % (restored_digest or "absent", original_digest or "absent"))

    print(json.dumps(results, indent=2))
    if restored_digest != original_digest:
        print("UNPROVEN: the player's slot did not come back byte for byte")
        return 2
    if unanswered:
        print("UNPROVEN: the game printed no answer about the slot in run(s) %s, so nothing is "
              "proved about loading them" % ", ".join(unanswered))
        return 2
    if not results["empty"]["accepted"]:
        print('FAILED: music "" in the slot was not accepted')
        return 1
    if not results["cue"]["accepted"]:
        print("FAILED: a cue id in the slot was refused")
        return 1
    if not results["bogus"]["refused"] or "PP-99" not in results["bogus"]["answer"]:
        print("FAILED: an unknown cue id in the slot was not refused by name")
        return 1
    print('PROVEN: the built game answered the slot three times; music "" and "PP-05" were read and '
          'accepted, music "PP-99" was refused by name')
    return 0


if __name__ == "__main__":
    sys.exit(main())
