"""Probe three failure shapes: an all black mask, a corrupt concept file, and the origin labels
the sidecar records for each overworld frame."""
from __future__ import annotations

import json
import os
import subprocess

from PIL import Image

REPO = r"<repo>"
PY = r"<home>/AppData/Local/Python/bin/python.exe"
import tempfile

WORK = os.path.join(tempfile.gettempdir(), "char_pipe_review")  # scratch, never inside the repo


def run(cmd):
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def opaque(path):
    with Image.open(path) as img:
        return sum(1 for _, _, _, a in img.convert("RGBA").getdata() if a)


def main():
    concept = os.path.join(WORK, "clean_run", "concept_synthetic.png")
    with Image.open(concept) as handle:
        size = handle.size

    # A. an all black mask says "no character anywhere". Does the sheet stay empty and still PASS?
    black = Image.new("L", size, 0)
    black_path = os.path.join(WORK, "black_mask.png")
    black.save(black_path)
    out = os.path.join(WORK, "black_run")
    code, text = run([PY, "tools/sprite_pipe.py", "--concept", concept, "--mask", black_path,
                      "--out", out])
    ow = os.path.join(out, "spr_pp_char_overworld.png")
    bt = os.path.join(out, "spr_pp_char_battle.png")
    ow_opaque = opaque(ow) if os.path.isfile(ow) else None
    bt_opaque = opaque(bt) if os.path.isfile(bt) else None
    print("[A] all black mask -> exit %d, overworld opaque %s, battle opaque %s"
          % (code, ow_opaque, bt_opaque))
    print("    verdict lines: %s" % [l.strip() for l in text.splitlines()
                                     if "overworld" in l or "battle " in l])

    # B. a corrupt concept file
    bad = os.path.join(WORK, "not_an_image.png")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("this is not a png\n")
    code, text = run([PY, "tools/sprite_pipe.py", "--concept", bad, "--out", os.path.join(WORK, "bad_out")])
    print("\n[B] corrupt concept -> exit %d, traceback: %s" % (code, "Traceback" in text))
    print("    last line: %s" % (text.strip().splitlines()[-1][:200] if text.strip() else ""))

    # C. the origin labels the sidecar records for the committed with-poses run
    report = json.load(open(os.path.join(REPO, "output", "char_pipe", "with_poses",
                                         "char_pipe_report.json"), encoding="utf-8"))
    print("\n[C] overworld frame origins:")
    for name, frame in report["overworld"]["frames"].items():
        print("    %-8s %s" % (name, frame.get("origin")))
    print("    battle sources: %s" % {k: v.get("source") for k, v in report["battle"]["frames"].items()})
    print("    battlesegmentation: %s" % report["segmentation"])
    print("    ok=%s palette=%s" % (report["ok"], report["palette_file"]))

    # D. are down, up and right frame 0 the same pixels in the committed sheet?
    with Image.open(os.path.join(REPO, "output", "char_pipe", "with_poses",
                                 "spr_pp_char_overworld.png")) as img:
        sheet = img.convert("RGBA")
    rows = {"down": 0, "up": 1, "left": 2, "right": 3}
    f = lambda d, w: sheet.crop((w * 16, rows[d] * 16, w * 16 + 16, rows[d] * 16 + 16)).tobytes()  # noqa: E731
    print("\n[D] frame 0 identical across directions: down==up %s, down==right %s"
          % (f("down", 0) == f("up", 0), f("down", 0) == f("right", 0)))
    print("    walk 1 identical: down==up %s, down==right %s"
          % (f("down", 1) == f("up", 1), f("down", 1) == f("right", 1)))


if __name__ == "__main__":
    main()
