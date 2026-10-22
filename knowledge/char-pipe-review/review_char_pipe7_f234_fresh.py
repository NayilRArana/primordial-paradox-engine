"""Re-confirm F2 (clean refusal vs traceback), F3 (identical facing rows) and F4 (docstring claim
about the mock backend and the ai ledger) on the current tree. Writes to the Hermes scratch dir only.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from PIL import Image

REPO = r"<repo>"
PY = r"<home>/AppData/Local/Python/bin/python.exe"
WORK = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "profiles",
                    "code-review", "cache", "scratch", "charpipe_f234")
os.makedirs(WORK, exist_ok=True)


def run(args):
    proc = subprocess.run([PY, "tools/sprite_pipe.py"] + args, cwd=REPO, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text


def main() -> int:
    bad = os.path.join(WORK, "bad.png")
    with open(bad, "wb") as fh:
        fh.write(b"not an image at all")
    code, text = run(["--concept", bad, "--out", os.path.join(WORK, "o_bad")])
    print("F2 corrupt concept: exit %d, traceback %s, last line: %s"
          % (code, "Yes" if "Traceback" in text else "No", text.strip().splitlines()[-1][:120]))
    code, text = run(["--concept", os.path.join(WORK, "missing.png"), "--out", os.path.join(WORK, "o_missing")])
    print("F2 missing concept: exit %d, traceback %s, last line: %s"
          % (code, "Yes" if "Traceback" in text else "No", text.strip().splitlines()[-1][:120]))

    sheet = os.path.join(REPO, "output", "char_pipe", "with_poses", "spr_pp_char_overworld.png")
    with Image.open(sheet) as img:
        im = img.convert("RGBA")
        rows = {"down": 0, "up": 1, "left": 2, "right": 3}
        frame = {}
        for name, r in rows.items():
            frame[name] = [im.crop((c * 16, r * 16, c * 16 + 16, r * 16 + 16)).tobytes() for c in (0, 1)]
        for name in rows:
            print("F3 %s: walk0 == walk1 -> %s" % (name, frame[name][0] == frame[name][1]))
        mirror = im.crop((0, 32, 16, 48)).transpose(Image.FLIP_LEFT_RIGHT).tobytes()
        print("F3 left walk0 is byte mirror of right walk0 -> %s" % (mirror == frame["right"][0]))
        print("F3 identical facings: up==right %s, down==right %s, down==up %s"
              % (frame["up"][0] == frame["right"][0], frame["down"][0] == frame["right"][0],
                 frame["down"][0] == frame["up"][0]))

    ledger = os.path.join(REPO, "data", "ai_ledger.csv")
    print("F4 data/ai_ledger.csv exists -> %s" % os.path.isfile(ledger))
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import ai_client
    print("F4 ai_client public names: %s" % sorted(n for n in dir(ai_client) if not n.startswith("_")))
    for attr in ("segment", "generate_pose", "segment_image", "text_to_image"):
        if hasattr(ai_client, attr):
            print("F4 ai_client.%s present" % attr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
