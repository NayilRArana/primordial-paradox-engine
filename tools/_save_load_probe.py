"""A real save and a real load against the freshly built game, for card t_73f08da5 item 5.

The GML validator cannot be run without the game, so this drives the built exe: it writes a save
document with a chosen "music" value into the slot the game reads, launches the game, lets the title
ask the slot what it holds, and reads back what the game printed.

Three documents, same everything except music:
  ""        the baseline the game itself wrote on 2026-10-20
  "PP-05"   a cue id, which the card's fix has to accept
  "PP-99"   a cue id that does not exist, which must still be refused by name

The slot and its backup are copied to the scratch folder first and restored at the end.
"""

import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "PrimordialParadox")
EXE = os.path.join(OUT, "PrimordialParadox.exe")
WIN = os.path.join(OUT, "PrimordialParadox.win")
SAVE_DIR = os.path.join(os.environ["LOCALAPPDATA"], "PrimordialParadox", "default")
SAVE = os.path.join(SAVE_DIR, "pp_save_01.json")
BACKUP = os.path.join(SAVE_DIR, "pp_save_01.json.bak")
KEEP = os.path.join(ROOT, "build", "save_slot_probe")

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


def run_game(tag):
    log_path = os.path.join(KEEP, "run_%s.log" % tag)
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen([EXE, "-game", WIN], cwd=OUT, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
        time.sleep(9)
        process.terminate()
        try:
            process.wait(timeout=8)
        except Exception:
            process.kill()
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def main():
    if not os.path.isfile(EXE) or not os.path.isfile(WIN):
        print("no built game at %s" % OUT)
        return 1
    os.makedirs(KEEP, exist_ok=True)
    if os.path.isfile(SAVE):
        shutil.copy2(SAVE, os.path.join(KEEP, "pp_save_01.original.json"))
    if os.path.isfile(BACKUP):
        shutil.copy2(BACKUP, os.path.join(KEEP, "pp_save_01.original.bak"))
        os.remove(BACKUP)

    results = {}
    for tag, music in (("empty", ""), ("cue", "PP-05"), ("bogus", "PP-99")):
        size = write_slot(music)
        lines = run_game(tag)
        problems = [line for line in lines if "save problem" in line or "PP: music" in line]
        ready = [line for line in lines if "save" in line.lower()]
        results[tag] = {"music": music, "bytes": size, "problems": problems,
                        "save_lines": ready[:6], "lines": len(lines)}
        print("music=%-5r bytes=%d save problems=%s" % (music, size, problems or "none"))

    # Put the player's own slot back exactly as it was.
    if os.path.isfile(os.path.join(KEEP, "pp_save_01.original.json")):
        shutil.copy2(os.path.join(KEEP, "pp_save_01.original.json"), SAVE)
    if os.path.isfile(os.path.join(KEEP, "pp_save_01.original.bak")):
        shutil.copy2(os.path.join(KEEP, "pp_save_01.original.bak"), BACKUP)
    elif os.path.isfile(BACKUP):
        os.remove(BACKUP)

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
