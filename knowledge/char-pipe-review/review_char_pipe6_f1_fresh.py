"""Fresh re-confirmation of finding F1 on the current tree: a pose folder whose seven battle
PNGs all exist but are fully transparent must not pass as finished art.

Writes only to temp. Prints exit code, the battle TODO list, opaque pixel count per sheet and
nes_check's own verdict.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

REPO = r"<repo>"
PY = r"<home>/AppData/Local/Python/bin/python.exe"
WORK = os.path.join(tempfile.gettempdir(), "char_pipe_recheck")
NAMES = ("idle_0", "idle_1", "attack_0", "attack_1", "attack_2", "hurt_0", "down_0")


def opaque(path: str) -> int:
    with Image.open(path) as img:
        return sum(1 for px in img.convert("RGBA").getdata() if px[3])


def concept(path: str) -> None:
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    d.ellipse((64, 48, 192, 176), fill=(216, 80, 48, 255))
    d.rectangle((96, 160, 160, 224), fill=(40, 72, 168, 255))
    img.save(path)


def run(label: str, poses: str | None, want_sheet: str) -> None:
    out = os.path.join(WORK, label)
    cmd = [PY, "tools/sprite_pipe.py", "--concept", os.path.join(WORK, "concept.png")]
    if poses:
        cmd += ["--poses", poses]
    cmd += ["--out", out]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    print("== %s ==" % label)
    print("exit %d" % proc.returncode)
    for line in text.splitlines():
        if "TODO" in line or "PASS" in line or "FAIL" in line:
            print("  " + line.strip()[:160])
    sheet = os.path.join(out, want_sheet)
    if os.path.isfile(sheet):
        with Image.open(sheet) as img:
            total = img.size[0] * img.size[1]
        print("  %s opaque pixels: %d of %d" % (want_sheet, opaque(sheet), total))
    report_path = os.path.join(out, "char_pipe_report.json")
    if os.path.isfile(report_path):
        report = json.load(open(report_path, encoding="utf-8"))
        section = report.get("battle") or report.get("overworld") or {}
        print("  todo: %s" % section.get("todo"))
        print("  nes_check ok: %s" % (section.get("nes_check") or {}).get("ok"))


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    concept(os.path.join(WORK, "concept.png"))
    poses = os.path.join(WORK, "empty_poses")
    os.makedirs(poses, exist_ok=True)
    for name in NAMES:
        Image.new("RGBA", (96, 128), (0, 0, 0, 0)).save(os.path.join(poses, "battle_%s.png" % name))
    run("empty_poses", poses, "spr_pp_char_battle.png")
    Image.new("RGBA", (256, 256), (0, 0, 0, 255)).save(os.path.join(WORK, "black_mask.png"))
    out = os.path.join(WORK, "black_mask")
    proc = subprocess.run([PY, "tools/sprite_pipe.py", "--concept", os.path.join(WORK, "concept.png"),
                           "--mask", os.path.join(WORK, "black_mask.png"), "--out", out],
                          cwd=REPO, capture_output=True, text=True)
    print("== black_mask ==")
    print("exit %d" % proc.returncode)
    for line in (proc.stdout or "").splitlines():
        if "PASS" in line or "FAIL" in line or "0 colours" in line:
            print("  " + line.strip()[:160])
    sheet = os.path.join(out, "spr_pp_char_overworld.png")
    if os.path.isfile(sheet):
        print("  overworld opaque pixels: %d of %d" % (opaque(sheet), 32 * 64))
    return 0


if __name__ == "__main__":
    sys.exit(main())
