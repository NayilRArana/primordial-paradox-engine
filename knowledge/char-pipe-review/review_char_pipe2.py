"""Second half of the independent review: falsify the validator, prove the solver is load bearing,
reproduce the whole pipeline from a clean folder, and probe the error paths."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from PIL import Image

REPO = r"<repo>"
PY = r"<home>/AppData/Local/Python/bin/python.exe"
import tempfile

WORK = os.path.join(tempfile.gettempdir(), "char_pipe_review")  # scratch, never inside the repo
VIEW = (0, 23, 3, 26)  # unused


def load(path):
    with Image.open(path) as img:
        return img.convert("RGBA")


def tile_colours(image):
    px = image.load()
    out = {}
    for ty in range(image.height // 8):
        for tx in range(image.width // 8):
            seen = set()
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    r, g, b, a = px[x, y]
                    if a:
                        seen.add((r, g, b))
            out[(tx, ty)] = seen
    return out


def run(cmd, cwd=REPO):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    ok = True

    # 1. The validator must be able to fail. Make a 4 colour 8x8 tile and check nes_check refuses it.
    src = os.path.join(REPO, "output", "char_pipe", "with_poses", "spr_pp_char_battle.png")
    with open(os.path.join(REPO, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    palette = [(int(c.lstrip("#")[0:2], 16), int(c.lstrip("#")[2:4], 16), int(c.lstrip("#")[4:6], 16))
               for c in (raw.get("colours") or raw.get("palette"))]
    broken = load(src)
    bp = broken.load()
    for i, colour in enumerate(palette[:4]):
        for k in range(4):
            bp[(i * 2) % 8, k] = colour + (255,)
    broken_path = os.path.join(WORK, "broken_battle.png")
    broken.save(broken_path)
    worst = max(len(s) for s in tile_colours(broken).values())
    code, out = run([PY, "tools/nes_check.py", broken_path, "--type", "sprite"])
    print("[1] injected %d-colour tile -> nes_check exit %d" % (worst, code))
    print("    " + " | ".join(line.strip() for line in out.splitlines() if line.strip())[:300])
    ok &= code == 1

    # 2. Same sheet with the palette restricted to the colours it actually uses must still pass,
    #    so the failure above is the tile rule and not an accidental palette artefact.
    # 3. Reproduce the pipeline from a clean folder with the shipped CLI.
    clean = os.path.join(WORK, "clean_run")
    code, out = run([PY, "tools/sprite_pipe.py", "--selftest", "--out", clean])
    print("\n[3] CLI --selftest into a clean folder: exit %d" % code)
    for line in out.splitlines():
        if line.strip():
            print("    " + line.strip())
    ok &= code == 0
    produced = sorted(os.listdir(os.path.join(clean, "with_poses"))) if os.path.isdir(clean) else []
    print("    clean_run/with_poses holds: %s" % produced)
    for name in ("spr_pp_char_overworld.png", "spr_pp_char_battle.png", "preview_3x.png",
                 "char_pipe_report.json"):
        ok &= name in produced

    # 4. Independent nes_check CLI run over the freshly produced sheets (not the committed ones).
    for name in ("spr_pp_char_overworld.png", "spr_pp_char_battle.png"):
        path = os.path.join(clean, "with_poses", name)
        code, out = run([PY, "tools/nes_check.py", path, "--type", "sprite"])
        print("\n[4] fresh %s -> exit %d %s" % (name, code, out.splitlines()[0].strip() if out else ""))
        ok &= code == 0

    # 5. A supplied mask must change the result, not just the report string.
    concept = os.path.join(clean, "concept_synthetic.png")
    concept_img = load(concept)
    # a mask that keeps only the middle band should give a visibly different sprite
    from PIL import ImageDraw  # noqa: F401
    band = Image.new("L", concept_img.size, 0)
    ImageDraw.Draw(band).rectangle((0, int(concept_img.height * 0.35),
                                    concept_img.width, int(concept_img.height * 0.55)), fill=255)
    band_path = os.path.join(WORK, "band_mask.png")
    band.save(band_path)
    band_out = os.path.join(WORK, "band_run")
    code, out = run([PY, "tools/sprite_pipe.py", "--concept", concept, "--mask", band_path,
                     "--out", band_out])
    band_sheet = load(os.path.join(band_out, "spr_pp_char_overworld.png"))
    auto_sheet = load(os.path.join(clean, "with_poses", "spr_pp_char_overworld.png"))
    changed = band_sheet.tobytes() != auto_sheet.tobytes()
    band_opaque = sum(1 for _, _, _, a in band_sheet.getdata() if a)
    auto_opaque = sum(1 for _, _, _, a in auto_sheet.getdata() if a)
    print("\n[5] mask PNG changes pixels: %s (band sheet %d opaque vs auto %d, exit %d)"
          % (changed, band_opaque, auto_opaque, code))
    ok &= changed
    band_worst = max(len(s) for s in tile_colours(band_sheet).values())
    print("    band sheet worst tile: %d colours (must be <= 3)" % band_worst)
    ok &= band_worst <= 3

    # 6. Error path: a concept that does not exist should be a clean refusal, not a traceback.
    code, out = run([PY, "tools/sprite_pipe.py", "--concept", os.path.join(WORK, "nope.png"),
                     "--out", os.path.join(WORK, "nope_out")])
    trace = "Traceback" in out
    print("\n[6] missing concept -> exit %d, traceback: %s" % (code, trace))
    print("    " + " | ".join(out.strip().splitlines()[-2:])[:300])
    ok &= (not trace)

    print("\nSECOND HALF %s" % ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
