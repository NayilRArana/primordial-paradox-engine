"""Sharpest version of the blank-frame finding: a pose file that exists but is empty.

The tool's own stated rule is that a blank slot must never pass for art. A missing file gives a
visible X and a TODO label. An empty file gives... what?
"""
from __future__ import annotations

import json
import os
import subprocess

from PIL import Image

REPO = r"<repo>"
PY = r"<home>/AppData/Local/Python/bin/python.exe"
import tempfile

WORK = os.path.join(tempfile.gettempdir(), "char_pipe_review")  # scratch, never inside the repo


def opaque(path):
    with Image.open(path) as img:
        return sum(1 for _, _, _, a in img.convert("RGBA").getdata() if a)


def main():
    concept = os.path.join(WORK, "clean_run", "concept_synthetic.png")
    poses = os.path.join(WORK, "empty_poses")
    os.makedirs(poses, exist_ok=True)
    # every battle pose present, every one of them fully transparent
    for name in ("idle_0", "idle_1", "attack_0", "attack_1", "attack_2", "hurt_0", "down_0"):
        Image.new("RGBA", (96, 128), (0, 0, 0, 0)).save(os.path.join(poses, "battle_%s.png" % name))
    out = os.path.join(WORK, "empty_pose_run")
    proc = subprocess.run([PY, "tools/sprite_pipe.py", "--concept", concept, "--poses", poses,
                           "--out", out], cwd=REPO, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    sheet = os.path.join(out, "spr_pp_char_battle.png")
    print("exit %d" % proc.returncode)
    for line in text.splitlines():
        if "battle" in line or "TODO" in line:
            print("  " + line.strip())
    if os.path.isfile(sheet):
        print("battle sheet opaque pixels: %d of %d" % (opaque(sheet), 168 * 32))
        report = json.load(open(os.path.join(out, "char_pipe_report.json"), encoding="utf-8"))
        print("todo list: %s" % report["battle"]["todo"])
        print("frame sources: %s" % {k: os.path.basename(v.get("source") or "None")
                                     for k, v in report["battle"]["frames"].items()})
        print("nes_check ok: %s" % report["battle"]["nes_check"]["ok"])


if __name__ == "__main__":
    main()
