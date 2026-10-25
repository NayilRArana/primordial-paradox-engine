"""nes_audit_all.py: run the NES checkers over every art file in this project and say what to fix.

The card is PALETTE-AUDIT (t_3de37cbc): "run the NES checkers on every art asset in the project and list
fixes". This tool is the runner. It does not invent a rule and it does not soften one: the verdict for each
file is whatever `tools\\nes_check.py` (one sheet or layer, sprite tiles or 16x16 background areas) or
`tools\\nes_composite_check.py` (one finished 256x240 frame, both layers together) returns. Both are imported
and called directly, so the audit measures exactly the code the project already trusts, without paying a
process spawn per file.

What it audits, and why each scope is gated or not:

1. `asset`: every PNG under `game\\sprites_src\\`. GATED. These are the shipped art sources. A sheet whose
   sibling .json exists (or whose name starts `spr`) is a GameMaker sprite sheet and is checked under the
   sprite rules; a layer named `title_*`, `BG*` or with no sibling is checked under the background rules.
   The naming rule is in `classify_asset()` and it is deterministic: same name, same scope, every run.
2. `frame`: `output\\*preview*.png` that is exactly 256x240. GATED. It is one finished frame, so
   `nes_composite_check.py` judges it, background and sprites together.
3. `sheet`: every other `output\\*preview*.png`. ADVISORY. These are 3x contact sheets built to be looked at by
   a person; a 3x sheet is downsampled by nearest to the 1x art before the background rules run, so the
   failure still names the real art, but a contact sheet is a viewing aid and not a shipped asset.
4. `capture`: `output\\title_run_*.png`, the window captures of the running game. ADVISORY. A window capture
   carries the GameMaker compositor's own scaling, so a red there can measure the capture path instead of the
   art. It is still reported, and an unreadable capture is UNMEASURED, never a pass.

A SKIP is not a pass, so a file the checker cannot read is counted as UNMEASURED and the tool exits 1 on it
when the file is gated (PLAN-V2-2026-10-21.md section 0: measurable checks, no silent greens).

How visible a failure is. The checker says WHICH blocks break a rule. This tool also counts how many pixels a
fix would have to repaint, and sorts by that number, so worst first means most visible first: a 1024x120 sky
that breaks 3 colour slots is named above a 3 pixel cursor tint. The counting is the only thing here that is
not the checker's own arithmetic, and it is deliberately simple: an offending block's bad pixels are the
pixels that are not among the three most common colours in it (plus the backdrop for background areas), which
is exactly the set a merge has to touch.

Outputs (all deterministic; no timestamps, so a rerun either changes nothing or changed the art):
    output\\nes_audit\\<flattened path>.json     one report per file, one JSON each
    output\\nes_audit\\SUMMARY.json              every record plus the verdict
    output\\nes_audit_worst_3x.png              3x of the worst failure, offending blocks boxed in magenta
    knowledge\\NES-AUDIT.md                     the page a person reads, with coordinates and fixes

Usage:
    python tools\\nes_audit_all.py                     audit everything, write the page, exit 1 on a failure
    python tools\\nes_audit_all.py --quiet             the same with one line of output (this is the CI gate)
    python tools\\nes_audit_all.py --only title        audit only paths containing "title"
    python tools\\nes_audit_all.py --no-write          audit and report, write nothing (used by the tests)
    python tools\\nes_audit_all.py --list              print what would be audited and stop

Exit codes: 0 every gated file passes, 1 any gated failure or gated UNMEASURED, 2 nothing found.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw

TILE = 8
AREA = 16
MAX_COLOURS_ON_SCREEN = 25
FRAME = (256, 240)

ASSET_ROOT = os.path.join("game", "sprites_src")
OUTPUT_ROOT = "output"
REPORT_DIR = os.path.join(OUTPUT_ROOT, "nes_audit")
SUMMARY_PATH = os.path.join(REPORT_DIR, "SUMMARY.json")
MARKDOWN_PATH = os.path.join("knowledge", "NES-AUDIT.md")
PREVIEW_PATH = os.path.join(OUTPUT_ROOT, "nes_audit_worst_3x.png")
PREVIEW_SCALE = 3
# How many proposed fixes a file gets on the page. A 3x contact sheet can break a rule in thousands of areas,
# and printing every one of them buried the gated rows under four megabytes of advisory detail; the full list
# stays in the per file JSON, which is the machine readable copy.
MAX_FIX_LINES = 12


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# -----------------------------------------------------------------------------------------------------------------
# What to audit.

class Target:
    def __init__(self, rel: str, scope: str, kind: str, gated: bool, scale: int, reason: str,
                 backdrop=None, backdrop_why: str = "guessed from the pixels"):
        self.rel = rel
        self.scope = scope
        self.kind = kind
        self.gated = gated
        self.scale = scale
        self.reason = reason
        self.backdrop = backdrop
        self.backdrop_why = backdrop_why
        # A window capture's viewport box, when the capture recorded one beside the PNG.
        self.viewport: list | None = None

    def __repr__(self) -> str:
        return "Target(%r, %r)" % (self.rel, self.scope)


# Sidecar kinds that describe painted background art rather than a GameMaker sprite sheet. A tileset and a battle
# background are drawn through 16x16 attribute areas on the background layer; they are not a sheet of sprites, so
# the 3-colours-per-8x8-tile rule does not apply to them and the area rule does.
BACKGROUND_SIDECAR_KINDS = ("tileset", "battle_background", "background")


def declared_backdrop(rel: str, root: str):
    """(rgb, why) from the art's own sidecar, or (None, "guessed from the pixels").

    A background's shared backdrop is a property of the FRAME, and the frame cannot be guessed from a sheet: a
    tileset that is mostly stone grey and draws its void in $0F black makes the most common colour grey, and a
    guess then charges every black pixel against the three colours an area may carry. The art already declares
    the backdrop in its sidecar (`"backdrop": {"index": 15, "hex": "#000000"}`), which is the same value the CLI
    takes with --backdrop, so the audit reads it instead of guessing. No rule is relaxed: the areas are still
    measured, against the backdrop the art says it uses.
    """
    path = os.path.join(root, rel[:-4] + ".json")
    if not os.path.isfile(path):
        return None, "guessed from the pixels"
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None, "guessed from the pixels"
    value = payload.get("backdrop") if isinstance(payload, dict) else None
    if isinstance(value, dict):
        value = value.get("hex", value.get("colour"))
    if not isinstance(value, str) or len(value.lstrip("#")) != 6:
        return None, "guessed from the pixels"
    text = value.lstrip("#")
    rgb = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    return rgb, "declared in %s.json" % os.path.basename(rel)[:-4]


def sidecar_kind(rel: str, root: str) -> str | None:
    path = os.path.join(root, rel[:-4] + ".json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload.get("kind") if isinstance(payload, dict) else None


def classify_asset(rel: str, root: str) -> tuple:
    """(kind, why). A sprite sheet obeys the sprite rules; a layer or a screen obeys the background rules.

    The project's own naming decides first, because the sidecar cannot: `game\\sprites_src\\title\\title_L1_sky.json`
    is a GameMaker sprite definition too (fps 2, two 512x120 frames), so a sidecar alone would send a background
    layer down the sprite rules. A layer is drawn through 16x16 attribute areas; only a sheet of sprites is
    limited to 3 opaque colours per 8x8 tile.

    A sidecar that names its own kind decides next, because a tileset is not a sprite sheet even though it carries
    frame_w and frame_h: `game\\sprites_src\\env\\ts_exterior.json` says "kind": "tileset", and its pixels are
    background tiles drawn through 16x16 areas. Measuring them as sprites charged a 4-level stone ramp against a
    rule about transparent sprite pixels, which is a scope error and not an art defect.
    """
    stem = os.path.basename(rel)[:-4]
    lowered = stem.lower()
    if lowered.startswith("spr"):
        return "sprite", "named spr*, which is this project's prefix for a sprite sheet"
    kind = sidecar_kind(rel, root)
    if kind in BACKGROUND_SIDECAR_KINDS:
        return "background", ("a %s named in its own sidecar (%s.json), drawn through 16x16 attribute areas with "
                              "one shared backdrop" % (kind.replace("_", " "), stem))
    if lowered.startswith(("title_", "bg", "ui_")):
        return "background", ("a layer or screen named %s, drawn through 16x16 attribute areas with one shared "
                              "backdrop" % stem)
    if os.path.isfile(os.path.join(root, rel[:-4] + ".json")):
        return "sprite", ("a character sheet with a GameMaker sprite definition beside it (%s.json), so 3 colours "
                          "plus transparent per 8x8 tile" % stem)
    return "background", "no spr prefix and no sprite definition, so it is read as a background layer"


def is_3x(width: int, height: int) -> bool:
    return width % (3 * TILE) == 0 and height % (3 * TILE) == 0


def frame_scale(width: int, height: int) -> int:
    """A finished frame is 256x240 at 1x, or exactly 3x that. Anything else is not a frame."""
    if (width, height) == FRAME:
        return 1
    if (width, height) == (FRAME[0] * 3, FRAME[1] * 3):
        return 3
    return 0


def capture_note(rel: str, root: str):
    """(scale, viewport, why) for a window capture, from the sidecar the capture writes beside it.

    A window screenshot carries the desktop, the window border and whatever scale the compositor used, so it is
    unreadable as a frame unless the capture says where its viewport is. tools/capture_title.py writes that box
    and scale beside every capture it makes (`output/title_run_1.json`), which is the crop the checker needs; a
    capture without one is still tried with the viewport search, and is reported UNMEASURED when the search
    cannot find a legal box instead of being called a pass.
    """
    path = os.path.join(root, rel[:-4] + ".json")
    if not os.path.isfile(path):
        return 1, None, ("a window capture of the running game with no sidecar: the compositor's own scaling is in "
                         "the pixels, so this row is advisory")
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return 1, None, "a window capture whose sidecar could not be read"
    viewport = payload.get("viewport")
    scale = int(payload.get("scale", 1) or 1)
    if not isinstance(viewport, list) or len(viewport) != 4:
        return scale, None, "a window capture whose sidecar names no viewport"
    return scale, [int(value) for value in viewport], (
        "a window capture with its viewport recorded in %s.json: cropped to %s and read at %dx, so the row "
        "measures the art and not the capture path" % (os.path.basename(rel)[:-4], viewport, scale))


def named_output_files(root: str) -> list:
    """The output PNGs this repository's own tracked data names, sorted.

    A tree that has been narrowed (the far side carries only what a test reads, see pine_offload.py OUTPUT_KEEP)
    still carries `data/`, so the files the data names but the tree does not hold can be counted and named: that
    is the difference between "153 files pass" and "153 files pass, and 31 this tree cannot see". Read as text
    rather than as JSON because a name can sit in any string of any data file, and the scan must not care which.
    """
    pattern = re.compile(r"output/[A-Za-z0-9_./\-]+\.png")
    names = set()
    data_dir = os.path.join(root, "data")
    if not os.path.isdir(data_dir):
        return []
    for current, dirs, files in os.walk(data_dir):
        dirs.sort()
        for name in sorted(files):
            if not name.lower().endswith(".json"):
                continue
            try:
                with open(os.path.join(current, name), "r", encoding="utf-8-sig", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            for match in pattern.findall(text.replace("\\\\", "/")):
                names.add(match)
    return sorted(names)


def output_scope(root: str, targets: list, only: str | None = None) -> dict:
    """What this run measured in output/, and what it did not and why (card t_c93a983f).

    The universe is built from what is ON DISK, so a narrowed tree silently reads fewer files and a reader cannot
    tell a clean 153 from a shrunken one. This records the scope as numbers: the files measured, the output PNGs
    on disk that were not audit subjects because their name excludes them (neither a `preview` nor a `title_run_`
    capture), and the output PNGs this repository's data names that are not in this tree at all. The last number
    is the one the far side has to print (ruling section 8): it is advisory by design, and the scope says so
    instead of quietly measuring a smaller universe.
    """
    audited = [target.rel for target in targets if target.rel.startswith(OUTPUT_ROOT + "/")]
    on_disk = []
    output_dir = os.path.join(root, OUTPUT_ROOT)
    if os.path.isdir(output_dir):
        for name in sorted(os.listdir(output_dir)):
            path = os.path.join(output_dir, name)
            if os.path.isfile(path) and name.lower().endswith(".png"):
                on_disk.append("%s/%s" % (OUTPUT_ROOT, name))
    audited_set = set(audited)
    excluded = [rel for rel in on_disk if rel not in audited_set]
    named = named_output_files(root)
    absent = [rel for rel in named if not os.path.isfile(os.path.join(root, rel.replace("/", os.sep)))]
    return {
        "measured": len(targets),
        "asset_measured": sum(1 for target in targets if target.scope == "asset"),
        "output_measured": len(audited),
        "output_on_disk": len(on_disk),
        "excluded_by_name": excluded,
        "named_but_absent": absent,
        "only": only,
    }


def scope_lines(scope: dict, limit: int = 6) -> list:
    """The scope as the lines a person reads: the count, then what was skipped and why."""
    lines = []
    if scope["only"]:
        lines.append("  scope: %d file(s) measured (%d asset, %d output), filtered by --only %r; an output file "
                     "skipped by name is not counted here"
                     % (scope["measured"], scope["asset_measured"], scope["output_measured"], scope["only"]))
    else:
        lines.append("  scope: %d file(s) measured (%d asset, %d output); %d PNG(s) in output/ on disk, %d of them "
                     "skipped by name (not a preview and not a title_run_ capture)"
                     % (scope["measured"], scope["asset_measured"], scope["output_measured"],
                        scope["output_on_disk"], len(scope["excluded_by_name"])))
    if scope["named_but_absent"]:
        names = scope["named_but_absent"]
        lines.append("  scope: %d output file(s) named by this repository's data are not in this tree, so they "
                     "were not measured: %s%s"
                     % (len(names), ", ".join(names[:limit]),
                        ", ... %d more" % (len(names) - limit) if len(names) > limit else ""))
    else:
        lines.append("  scope: every output file this repository's data names is in this tree")
    return lines


def discover(root: str, only: str | None = None) -> list:
    targets = []
    asset_root = os.path.join(root, ASSET_ROOT)
    for current, dirs, files in os.walk(asset_root):
        dirs.sort()
        for name in sorted(files):
            if not name.lower().endswith(".png"):
                continue
            rel = os.path.relpath(os.path.join(current, name), root).replace(os.sep, "/")
            kind, why = classify_asset(rel, root)
            backdrop, backdrop_why = declared_backdrop(rel, root) if kind == "background" else (None, "sprite")
            targets.append(Target(rel, "asset", kind, True, 1, why, backdrop, backdrop_why))

    output_dir = os.path.join(root, OUTPUT_ROOT)
    if os.path.isdir(output_dir):
        for name in sorted(os.listdir(output_dir)):
            path = os.path.join(output_dir, name)
            if not os.path.isfile(path) or not name.lower().endswith(".png"):
                continue
            rel = "%s/%s" % (OUTPUT_ROOT, name)
            if name.startswith("title_run_"):
                scale, viewport, why = capture_note(rel, root)
                target = Target(rel, "capture", "frame", False, scale, why)
                target.viewport = viewport
                targets.append(target)
                continue
            if "preview" not in name:
                continue
            with Image.open(path) as probe:
                size = probe.size
            scale = frame_scale(size[0], size[1])
            if scale:
                backdrop, backdrop_why = declared_backdrop(rel, root)
                target = Target(rel, "frame", "frame", True, scale,
                                "a finished %dx%d frame (a 256x240 screen at %dx), so the composite checker "
                                "judges it, background and sprites together" % (size[0], size[1], scale),
                                backdrop, backdrop_why)
                targets.append(target)
            elif is_3x(size[0], size[1]):
                targets.append(Target(rel, "sheet", "background", False, 3,
                                      "a 3x contact sheet, downsampled by nearest to its 1x art before the "
                                      "background rules run"))
            else:
                targets.append(Target(rel, "sheet", "background", False, 1,
                                      "a preview that is neither a 256x240 frame nor a 3x sheet, read at 1x"))

    if only:
        needle = only.lower()
        targets = [t for t in targets if needle in t.rel.lower()]
    return targets


# -----------------------------------------------------------------------------------------------------------------
# Counting how visible a failure is. numpy, one pass, the same rules the checkers apply.

def rgba(path: str) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img.convert("RGBA"), dtype=np.uint8)


def pack(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.int32)
    return (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]


def block_offenders(packed: np.ndarray, opaque: np.ndarray, size: int, allowed_per_block: int,
                    backdrop: int | None) -> list:
    """Every size x size block with more opaque colours than allowed, and the pixels a fix has to repaint."""
    height, width = packed.shape
    blocks = []
    for y0 in range(0, height, size):
        for x0 in range(0, width, size):
            ys = slice(y0, min(y0 + size, height))
            xs = slice(x0, min(x0 + size, width))
            visible = opaque[ys, xs]
            if not visible.any():
                continue
            values = packed[ys, xs][visible]
            counts = Counter(values.tolist())
            if backdrop is not None:
                counts.pop(backdrop, None)
            if len(counts) <= allowed_per_block:
                continue
            keep = [colour for colour, _ in counts.most_common(allowed_per_block)]
            if backdrop is not None:
                keep.append(backdrop)
            good = int(np.isin(values, keep).sum())
            blocks.append({
                "box": [x0, y0, min(size, width - x0), min(size, height - y0)],
                "colours": ["#%06x" % colour for colour in sorted(counts)],
                "carries": len(counts),
                "bad_pixels": int(values.size - good),
            })
    return blocks


def downsample(array: np.ndarray, scale: int) -> np.ndarray:
    if scale <= 1:
        return array
    image = Image.fromarray(array, "RGBA")
    return np.array(image.resize((array.shape[1] // scale, array.shape[0] // scale), Image.NEAREST),
                    dtype=np.uint8)


def measure(path: str, target: Target, allowed: list, limit: int = MAX_COLOURS_ON_SCREEN) -> dict:
    """Offending pixels and block coordinates for the rules that name a block or a colour."""
    array = rgba(path)
    if target.viewport is not None:
        x, y, w, h = target.viewport
        array = array[y:y + h, x:x + w]
    array = downsample(array, target.scale)
    height, width = array.shape[0], array.shape[1]
    packed = pack(array)
    visible = array[:, :, 3] != 0
    opaque = array[:, :, 3] == 255
    semitransparent = int((visible & ~opaque).sum())
    total_visible = int(visible.sum())
    allowed_packed = [((r << 16) | (g << 8) | b) for r, g, b in allowed]
    off_palette = int((opaque & ~np.isin(packed, allowed_packed)).sum()) + semitransparent

    out = {
        "size": [width, height],
        "visible_pixels": total_visible,
        "off_palette_pixels": off_palette,
        "blocks": [],
        "block_rule": None,
        "screen_excess": 0,
        "colours": int(len(set(packed[visible].tolist()))),
    }

    if target.kind == "sprite":
        blocks = block_offenders(packed, opaque, TILE, 3, None)
        out["block_rule"] = "sprite_tile"
    else:
        counts = Counter(packed[opaque].tolist())
        if target.backdrop is not None:
            backdrop = (target.backdrop[0] << 16) | (target.backdrop[1] << 8) | target.backdrop[2]
        else:
            backdrop = counts.most_common(1)[0][0] if counts else None
        blocks = block_offenders(packed, opaque, AREA, 3, backdrop)
        out["block_rule"] = "background_area"
        out["backdrop"] = "#%06x" % backdrop if backdrop is not None else None
        out["backdrop_from"] = target.backdrop_why
    blocks.sort(key=lambda block: (-block["bad_pixels"], block["box"][1], block["box"][0]))
    out["blocks"] = blocks

    if out["colours"] > limit:
        counts = Counter(packed[visible].tolist())
        keep = sum(count for _, count in counts.most_common(limit))
        out["screen_excess"] = int(total_visible - keep)

    out["offending_pixels"] = max(out["off_palette_pixels"],
                                  sum(block["bad_pixels"] for block in blocks),
                                  out["screen_excess"])
    out["percent_of_image"] = round(100.0 * out["offending_pixels"] / total_visible, 1) if total_visible else 0.0
    return out


# -----------------------------------------------------------------------------------------------------------------
# The checker verdicts.

def run_check(nes_check, path: str, target: Target, palette: dict) -> dict:
    image = nes_check.load_image(path)
    if target.scale > 1:
        image = image.resize((image.width // target.scale, image.height // target.scale), Image.NEAREST)
    return nes_check.check(image, target.kind, palette, target.backdrop)


def run_composite(nes_composite_check, path: str, palette: dict, scale: int = 1,
                  viewport: list | None = None, backdrop=None) -> tuple:
    if viewport is not None:
        with Image.open(path) as img:
            array = np.array(img.convert("RGBA"), dtype=np.uint8)
        x, y, w, h = viewport
        if x < 0 or y < 0 or x + w > array.shape[1] or y + h > array.shape[0]:
            raise ValueError("the recorded viewport %s does not fit inside %dx%d"
                             % (viewport, array.shape[1], array.shape[0]))
        array = array[y:y + h, x:x + w]
        frame = Image.fromarray(downsample(array, scale), "RGBA")
        info = {"crop_how": "the viewport recorded beside the capture, read at %dx" % scale, "scale": scale,
                "crop": viewport, "source_size": [array.shape[1] // max(1, scale),
                                                  array.shape[0] // max(1, scale)]}
        return nes_composite_check.check_frame(frame, palette, backdrop), info
    if scale > 1:
        with Image.open(path) as img:
            array = np.array(img.convert("RGBA"), dtype=np.uint8)
        frame = Image.fromarray(downsample(array, scale), "RGBA")
        info = {"crop_how": "a %dx frame downsampled by nearest to 1x" % scale, "scale": scale,
                "crop": "none needed", "source_size": [array.shape[1], array.shape[0]]}
        return nes_composite_check.check_frame(frame, palette, backdrop), info
    frame, info = nes_composite_check.load_frame(path, palette["allowed"], crop="auto")
    return nes_composite_check.check_frame(frame, palette, backdrop), info


def rules_of(problems: list) -> dict:
    counts = Counter(problem["rule"] for problem in problems)
    return {rule: counts[rule] for rule in sorted(counts)}


def nearest_ppu(rgb: tuple, allowed: list) -> str:
    best = None
    for candidate in allowed:
        distance = (candidate[0] - rgb[0]) ** 2 + (candidate[1] - rgb[1]) ** 2 + (candidate[2] - rgb[2]) ** 2
        if best is None or distance < best[0]:
            best = (distance, candidate)
    return "#%06x" % ((best[1][0] << 16) | (best[1][1] << 8) | best[1][2]) if best else "?"


def shortest_list(colours: list, limit: int = 8) -> str:
    """A colour list a person can read: the first `limit`, then how many were left out.

    An 8x8 tile or a 16x16 area can carry dozens of colours, and printing all of them turned one advisory
    contact sheet into thousands of 400 character lines (knowledge/NES-AUDIT.md measured 4.5 MB before this).
    The full list is in the per file JSON, which is what a script reads.
    """
    if len(colours) <= limit:
        return " ".join(colours)
    return "%s (and %d more, see the JSON)" % (" ".join(colours[:limit]), len(colours) - limit)


def fix_for(problem: dict, image_size: tuple, allowed_colours: list) -> str:
    rule = problem["rule"]
    if rule == "grid":
        return ("align to the 8 pixel grid: %s, so the image cannot be cut into 8x8 tiles. "
                "Recrop or repaint to the nearest multiple of 8." % problem["detail"])
    if rule == "palette":
        colour = tuple(int(problem["colour"][i:i + 2], 16) for i in (1, 3, 5))
        return ("merge colours: %s is not a PPU output (%s). Repaint it with %s, the nearest of the 64, and this "
                "problem goes to zero." % (problem["colour"], problem["detail"],
                                           nearest_ppu(colour, allowed_colours)))
    if rule == "sprite_tile":
        tile_x, tile_y = problem["tile"]
        return ("split the sprite or merge its colours: the 8x8 tile at [%d, %d] carries %d colours, and a sprite "
                "tile carries 3 plus transparent. Keep 3 of %s and repaint the rest, or split one sprite into two "
                "at that tile edge." % (tile_x * TILE, tile_y * TILE, len(problem["colours"]),
                                        shortest_list(problem["colours"])))
    if rule == "background_area":
        area = problem.get("area") or problem.get("block")
        if not area:
            return ("merge colours in the blocks listed above: %s" % problem["detail"])
        area_x, area_y = area[0], area[1]
        clipped = area_y + AREA > image_size[1] or area_x + AREA > image_size[0]
        tail = (" The image is not a whole number of 16 pixel rows, so this band is clipped: align the band to "
                "16 pixel rows by padding or cropping the image to a multiple of 16."
                if clipped else "")
        return ("merge colours inside the attribute area at [%d, %d]: it carries %d colours besides the backdrop "
                "and the limit is 3. Keep 3 of %s, or move the band so the colours fall into different areas.%s"
                % (area_x, area_y, len(problem["colours"]), shortest_list(problem["colours"]), tail))
    if rule == "screen_colours":
        return ("reduce the frame to %d colours: %s. Split the excess between the background and the sprite "
                "palettes, or merge the least used colours into their nearest PPU neighbour."
                % (MAX_COLOURS_ON_SCREEN, problem["detail"]))
    return "read the checker output for this rule; no canned fix is written for %s" % rule


def audit_one(root: str, target: Target, nes_check, composite, palette: dict) -> dict:
    path = os.path.join(root, target.rel)
    record = {
        "path": target.rel,
        "scope": target.scope,
        "kind": target.kind,
        "gated": target.gated,
        "scale": target.scale,
        "why": target.reason,
    }
    try:
        if target.kind == "frame":
            report, info = run_composite(composite, path, palette, target.scale, target.viewport,
                                         target.backdrop)
            record["checker"] = "tools/nes_composite_check.py check_frame()"
            record["crop"] = {"how": info.get("crop_how"), "score": info.get("crop_score"),
                              "scale": info.get("scale"), "source_size": info.get("source_size")}
            record["colours"] = report["screen"]["colours"]
            record["backdrop"] = report["backdrop"]
            record["size"] = report["size"]
        else:
            report = run_check(nes_check, path, target, palette)
            record["checker"] = "tools/nes_check.py check()"
            record["colours"] = report["colours"]
            record["backdrop"] = report["backdrop"]
            record["size"] = report["size"]
        record["ok"] = bool(report["ok"])
        record["problems"] = report["problems"]
        record["rules"] = rules_of(report["problems"])
        record["problem_count"] = len(report["problems"])
        record["unmeasured"] = None
    except SystemExit as exc:
        record.update({"ok": False, "problems": [], "rules": {"unmeasured": 1}, "problem_count": 1,
                       "unmeasured": "the checker refused the file: %s" % exc, "checker": "refused"})
    except Exception as exc:  # noqa: BLE001 - an unreadable file is a result, not a crash
        record.update({"ok": False, "problems": [], "rules": {"unmeasured": 1}, "problem_count": 1,
                       "unmeasured": "%s: %s" % (type(exc).__name__, exc), "checker": "refused"})

    if record["unmeasured"]:
        record["offending_pixels"] = None
        record["percent_of_image"] = None
        record["worst_block"] = None
        record["measurement"] = None
        record["fixes"] = ["read the file by hand: the checker could not open it (%s)" % record["unmeasured"]]
        return record

    measurement = measure(path, target, palette["allowed"])
    record["measurement"] = measurement
    record["offending_pixels"] = measurement["offending_pixels"]
    record["percent_of_image"] = measurement["percent_of_image"]
    worst = measurement["blocks"][0] if measurement["blocks"] else None
    record["worst_block"] = ({"rule": measurement["block_rule"], "box": worst["box"],
                              "carries": worst["carries"], "bad_pixels": worst["bad_pixels"]}
                             if worst else None)

    fixes = []
    seen = Counter()
    for problem in record["problems"]:
        fix = fix_for(problem, tuple(record["size"]), palette["allowed"])
        if fix not in seen:
            fixes.append(fix)
        seen[fix] += 1
    record["fixes"] = ["%s (x%d)" % (fix, seen[fix]) if seen[fix] > 1 else fix for fix in fixes]
    return record


# -----------------------------------------------------------------------------------------------------------------
# The page.

def human(value) -> str:
    return "-" if value is None else "{:,}".format(value)


def worst_line(record: dict) -> str:
    block = record.get("worst_block")
    if not block:
        return "-"
    return "%s at [%d, %d]" % (block["rule"], block["box"][0], block["box"][1])


def run_synergy(root: str):
    """The palette synergy check, as a new check in this audit (card PAL-SYSTEM).

    tools\\palette_synergy.py measures what ne_check and nes_composite_check cannot: whether a sprite's body
    separates from the ground drawn behind it, and whether both layers stay inside the scene's palette set
    (ART-BIBLE RULE 0). It is imported and called, not shelled out, because it is a Python module like the
    other two. A missing tool or a scene with no palette set is reported as unmeasured, never as a pass.
    """
    path = os.path.join(root, "tools", "palette_synergy.py")
    if not os.path.isfile(path):
        return {"entries": 0, "gated_failures": 0, "advisory_failures": 0, "report": None,
                "unmeasured": "tools/palette_synergy.py is missing, so synergy was not measured", "rows": []}
    module = load_module("nes_audit_palette_synergy", path)
    try:
        results, blocked, advisory = module.gate(root)
    except SystemExit as error:
        return {"entries": 0, "gated_failures": 0, "advisory_failures": 0, "report": None,
                "unmeasured": str(error), "rows": []}
    report = os.path.relpath(module.write_audit(root, results), root).replace(os.sep, "/")
    rows = []
    for result in results:
        rows.append({
            "scene": result["scene"],
            "background": result["background"],
            "gated": result["gated"],
            "ok": result["ok"],
            "fail_count": result["fail_count"],
            "rules": sorted({problem["rule"] for problem in result["problems"]}),
            "first": [problem["detail"] for problem in result["problems"][:3]],
        })
    return {"entries": len(results), "gated_failures": len(blocked), "advisory_failures": len(advisory),
            "report": report, "rows": rows, "unmeasured": None}


def render_markdown(records: list, verdict: dict) -> str:
    failing = sorted([r for r in records if not r["ok"]],
                     key=lambda r: (-(r["offending_pixels"] or 0), r["path"]))
    unmeasured = [r for r in records if r["unmeasured"]]
    passing = [r for r in records if r["ok"]]

    lines = []
    add = lines.append
    add("# NES audit: every art asset against the PPU rules")
    add("")
    add("Generated by `tools/nes_audit_all.py`. Do not edit by hand: rerun the tool.")
    add("")
    add("Ground rule this audit serves: every asset in this project is original work drawn to the NES rules, and "
        "nothing is copied from a published game (PLAN-V2-2026-10-21.md section 0). The checker proves the RULES, "
        "not the taste: a frame that passes this page can still look wrong, and that judgement is the manager's, "
        "by eye.")
    add("")
    add("## Summary")
    add("")
    add("| scope | files | pass | fail | unmeasured | gated |")
    add("|---|---|---|---|---|---|")
    for scope in ("asset", "frame", "sheet", "capture"):
        rows = [r for r in records if r["scope"] == scope]
        if not rows:
            continue
        add("| %s | %d | %d | %d | %d | %d of %d |" % (
            scope, len(rows), sum(1 for r in rows if r["ok"]),
            sum(1 for r in rows if not r["ok"] and not r["unmeasured"]),
            sum(1 for r in rows if r["unmeasured"]),
            sum(1 for r in rows if r["gated"]), len(rows)))
    add("")
    add("Verdict: **%s**. %d file(s) checked, %d failing, %d the checker could not read, %d gated failure(s)."
        % (verdict["verdict"], len(records), len(failing), len(unmeasured), verdict["gated_failures"]))
    add("")
    add("Exit code from `tools/nes_audit_all.py`: %d. A gated row is a shipped asset or a finished 256x240 frame. "
        "A sheet or a window capture is ADVISORY: a 3x contact sheet and a window capture carrying the "
        "compositor's own scaling measure a viewing aid and the capture path before they measure the art, so "
        "their rows carry their own verdict and are never counted as a pass." % verdict["exit_code"])
    add("")
    add("Sorted by how visible each failure is. The count is the pixels a fix has to repaint: a block's pixels "
        "that are not among its three most common colours, an off-palette colour's pixels, or the excess beyond "
        "25 colours; the percentage is that count over the visible image.")
    add("")
    add("## Reproduce")
    add("")
    add("    python tools\\nes_audit_all.py                 # audit, rewrite this page, exit 1 on a gated failure")
    add("    python tools\\nes_audit_all.py --only title    # one family of files")
    add("    python tools\\nes_audit_all.py --quiet         # the CI gate: one line, exit code only")
    add("")
    add("One JSON per file: `output\\nes_audit\\<path with __ separators>.json`. Summary: "
        "`output\\nes_audit\\SUMMARY.json`.")
    add("")
    gated_failing = [r for r in failing if r["gated"]]
    advisory_failing = [r for r in failing if not r["gated"]]

    def distance_to_fix(record):
        return (-(record["offending_pixels"] or 0), record["path"])

    def emit_table(rows):
        add("| # | file | scope | pixels to repaint | % of image | rules | worst block |")
        add("|---|---|---|---|---|---|---|")
        for position, record in enumerate(sorted(rows, key=distance_to_fix), start=1):
            add("| %d | `%s` | %s | %s | %s | %s | %s |" % (
                position, record["path"], record["scope"],
                human(record["offending_pixels"]),
                "-" if record["percent_of_image"] is None else "%s%%" % record["percent_of_image"],
                ", ".join("%s x%d" % (rule, count) for rule, count in record["rules"].items()),
                worst_line(record)))
        add("")

    def emit_details(rows):
        for position, record in enumerate(sorted(rows, key=distance_to_fix), start=1):
            size = record.get("size") or [0, 0]
            add("### %d. `%s` (%s, %s, %dx%d, %s colours)" % (
                position, record["path"], record["scope"], "GATED" if record["gated"] else "advisory",
                size[0], size[1], record.get("colours") if record.get("colours") is not None else "-"))
            add("")
            add("Checker: `%s`. %s" % (record["checker"], record["why"]))
            add("")
            if record["unmeasured"]:
                add("UNMEASURED: %s" % record["unmeasured"])
                add("")
                continue
            measurement = record["measurement"]
            add("- pixels to repaint: %s of %s visible (%s%%)" % (
                human(record["offending_pixels"]), human(measurement["visible_pixels"]),
                record["percent_of_image"]))
            add("- rules: %s" % ", ".join("%s x%d" % (rule, count)
                                          for rule, count in record["rules"].items()))
            if measurement.get("backdrop"):
                add("- backdrop: %s (%s, shared by every background area)"
                    % (measurement["backdrop"], measurement.get("backdrop_from", "the most common colour")))
            if measurement["blocks"]:
                add("- %d block(s) over the limit; worst five:" % len(measurement["blocks"]))
                for block in measurement["blocks"][:5]:
                    add("  - %s at [%d, %d] size %dx%d carries %d colours besides the backdrop, %s pixel(s) to "
                        "repaint: %s" % (measurement["block_rule"], block["box"][0], block["box"][1],
                                         block["box"][2], block["box"][3], block["carries"],
                                         human(block["bad_pixels"]), shortest_list(block["colours"])))
            if measurement["off_palette_pixels"]:
                add("- off-palette or semi-transparent pixels: %s" % human(measurement["off_palette_pixels"]))
            if measurement["screen_excess"]:
                add("- colours beyond the 25 a frame can show: %s pixel(s) sit on colours past the 25 most common"
                    % human(measurement["screen_excess"]))
            add("")
            add("Proposed fix:")
            add("")
            for fix in record["fixes"][:MAX_FIX_LINES]:
                add("- %s" % fix)
            if len(record["fixes"]) > MAX_FIX_LINES:
                add("- ... and %d more fix(es) of the same kind: the whole list is in `%s`."
                    % (len(record["fixes"]) - MAX_FIX_LINES,
                       "output/nes_audit/%s.json" % flat_name(record["path"])))
            add("")

    add("## Gated failures, worst first")
    add("")
    add("These are the shipped art sources and the finished frames: a failure here is a release failure. Sorted "
        "by how visible it is, which is the number of pixels a fix has to repaint.")
    add("")
    emit_table(gated_failing)
    add("## Gated failures, with their fix")
    add("")
    emit_details(gated_failing)
    add("## Advisory failures, worst first")
    add("")
    add("Sheets and window captures. These measure a viewing aid and the capture path before they measure the "
        "art, so they are listed apart from the ranking above and are never counted as a pass: a red row here "
        "still means something is wrong with what the aid shows.")
    add("")
    emit_table(advisory_failing)
    add("## Advisory failures, with their fix")
    add("")
    emit_details(advisory_failing)
    if unmeasured:
        add("## Could not be read (not a pass)")
        add("")
        for record in unmeasured:
            add("- `%s` (%s): %s" % (record["path"], record["scope"], record["unmeasured"]))
        add("")
    add("## Passes")
    add("")
    add("Every file below passes every rule that applies to it. A pass is a rules pass only: nothing here says "
        "the art is good.")
    add("")
    for record in sorted(passing, key=lambda r: r["path"]):
        size = record.get("size") or [0, 0]
        add("- `%s` (%s%s, %dx%d, %d colours)" % (
            record["path"], record["scope"], "" if record["gated"] else " advisory",
            size[0], size[1], record.get("colours") or 0))
    add("")
    add("## The 3x preview a person can look at")
    add("")
    if verdict.get("preview"):
        add("`%s` is `%s` at 3x with every offending block boxed in magenta (%d box(es)). Nothing in this "
            "repository can see it: the manager looks, and turns a boxed block into a specific repaint."
            % (PREVIEW_PATH.replace(os.sep, "\\"), verdict["preview"]["path"], verdict["preview"]["boxes"]))
    else:
        add("No failing file was available to preview: every file passes.")
    add("")
    add("## Palette synergy: does the sprite read on the ground it stands on")
    add("")
    synergy = verdict.get("synergy")
    if not synergy:
        add("Synergy was not measured.")
    elif synergy.get("unmeasured"):
        add("Synergy was not measured: %s" % synergy["unmeasured"])
    else:
        add("%d pair(s) checked by `tools/palette_synergy.py` against ART-BIBLE RULE 0: %d gated failure(s), "
            "%d advisory failure(s). Report: `%s`."
            % (synergy["entries"], synergy["gated_failures"], synergy["advisory_failures"], synergy["report"]))
        add("")
        add("| scene | background | verdict | failures | rules | first failure |")
        add("|---|---|---|---|---|---|")
        for row in synergy["rows"]:
            add("| %s | `%s` | %s%s | %d | %s | %s |"
                % (row["scene"], row["background"], "PASS" if row["ok"] else "FAIL",
                   "" if row["gated"] else " (advisory)", row["fail_count"], ", ".join(row["rules"]) or "-",
                   (row["first"][0] if row["first"] else "-").replace("|", "/")))
        add("")
        add("A scene is gated once gamedev sets `gate: true` in `data/scene_palettes.json`; until then its pairs "
            "are reported and do not stop the build, because the art has not been repainted yet.")
    add("")
    return "\n".join(lines)


def write_preview(root: str, record: dict) -> dict:
    array = downsample(rgba(os.path.join(root, record["path"])), record["scale"])
    image = Image.fromarray(array, "RGBA").convert("RGB")
    big = image.resize((image.width * PREVIEW_SCALE, image.height * PREVIEW_SCALE), Image.NEAREST)
    draw = ImageDraw.Draw(big)
    blocks = record["measurement"]["blocks"]
    for block in blocks:
        x, y, w, h = block["box"]
        draw.rectangle([x * PREVIEW_SCALE, y * PREVIEW_SCALE,
                        (x + w) * PREVIEW_SCALE - 1, (y + h) * PREVIEW_SCALE - 1], outline=(255, 0, 255))
    out = os.path.join(root, PREVIEW_PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    big.save(out)
    return {"path": record["path"], "boxes": len(blocks),
            "png": PREVIEW_PATH.replace(os.sep, "/"), "size": [big.width, big.height]}


# -----------------------------------------------------------------------------------------------------------------
# The run.

def flat_name(rel: str) -> str:
    return rel.replace("/", "__")


def audit(root: str, only: str | None = None, write: bool = True) -> dict:
    nes_check = load_module("nes_audit_nes_check", os.path.join(root, "tools", "nes_check.py"))
    palette_path, palette_why = nes_check.palette_path(root)
    palette = nes_check.load_palette(palette_path)
    composite = None
    composite_path = os.path.join(root, "tools", "nes_composite_check.py")
    if os.path.isfile(composite_path):
        composite = load_module("nes_audit_composite", composite_path)
        palette = composite.load_palette(composite.default_palette_path(root))

    targets = discover(root, only)
    if not targets:
        return {"records": [], "verdict": None, "exit_code": 2, "targets": 0}
    scope = output_scope(root, targets, only)

    records = []
    for target in targets:
        if target.kind == "frame" and composite is None:
            records.append({"path": target.rel, "scope": target.scope, "kind": target.kind,
                            "gated": target.gated, "scale": target.scale, "why": target.reason,
                            "checker": "none", "ok": False, "problems": [], "rules": {"unmeasured": 1},
                            "problem_count": 1, "size": None, "colours": None, "unmeasured":
                            "tools/nes_composite_check.py is missing, so a frame cannot be judged",
                            "offending_pixels": None, "percent_of_image": None, "worst_block": None,
                            "measurement": None,
                            "fixes": ["restore tools/nes_composite_check.py, then rerun the audit"]})
            continue
        records.append(audit_one(root, target, nes_check, composite, palette))

    gated_failures = [r for r in records if r["gated"] and (not r["ok"] or r["unmeasured"])]
    synergy = run_synergy(root)
    synergy_gated = bool(synergy and synergy["gated_failures"])
    verdict = {
        "verdict": "PASS" if not gated_failures and not synergy_gated else "FAIL",
        "gated_failures": len(gated_failures) + (synergy["gated_failures"] if synergy else 0),
        "advisory_failures": sum(1 for r in records if not r["gated"] and (not r["ok"] or r["unmeasured"]))
                             + (synergy["advisory_failures"] if synergy else 0),
        "exit_code": 0 if (not gated_failures and not synergy_gated) else 1,
        "palette": os.path.relpath(palette_path, root).replace(os.sep, "/"),
        "palette_source": palette_why,
        "composite_checker": composite is not None,
        "preview": None,
        "synergy": synergy,
        "scope": scope,
    }

    if write:
        os.makedirs(os.path.join(root, REPORT_DIR), exist_ok=True)
        for record in records:
            path = os.path.join(root, REPORT_DIR, flat_name(record["path"])[:-4] + ".json")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(record, handle, indent=2, sort_keys=True)
                handle.write("\n")

        candidates = [r for r in records if r["gated"] and not r["ok"] and r["measurement"]
                      and r["measurement"]["blocks"]]
        candidates.sort(key=lambda r: (-(r["offending_pixels"] or 0), r["path"]))
        if not candidates:
            candidates = sorted([r for r in records if not r["ok"] and r["measurement"]
                                 and r["measurement"]["blocks"]],
                                key=lambda r: (-(r["offending_pixels"] or 0), r["path"]))
        if candidates:
            verdict["preview"] = write_preview(root, candidates[0])
        elif os.path.isfile(os.path.join(root, PREVIEW_PATH)):
            os.remove(os.path.join(root, PREVIEW_PATH))

        summary = {"verdict": verdict,
                   "counts": {"files": len(records),
                              "failing": sum(1 for r in records if not r["ok"]),
                              "unmeasured": sum(1 for r in records if r["unmeasured"])},
                   "records": records}
        with open(os.path.join(root, SUMMARY_PATH), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2, sort_keys=True)
            handle.write("\n")
        markdown = os.path.join(root, MARKDOWN_PATH)
        os.makedirs(os.path.dirname(markdown), exist_ok=True)
        with open(markdown, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_markdown(records, verdict))

    return {"records": records, "verdict": verdict, "exit_code": verdict["exit_code"], "targets": len(targets)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit every art file in the project against the NES rules.")
    parser.add_argument("--only", default=None, help="only audit paths containing this text")
    parser.add_argument("--no-write", action="store_true", help="audit and report without writing the page")
    parser.add_argument("--quiet", action="store_true", help="one line of output; the exit code carries the verdict")
    parser.add_argument("--list", action="store_true", help="print the files that would be audited and stop")
    args = parser.parse_args(argv)

    root = repo_root()
    if args.list:
        for target in discover(root, args.only):
            print("%-8s %-10s %s" % (target.scope, target.kind, target.rel))
        return 0

    result = audit(root, args.only, write=not args.no_write)
    if result["verdict"] is None:
        print("nes_audit_all: no art files found under %s or %s" % (ASSET_ROOT, OUTPUT_ROOT))
        return 2

    verdict = result["verdict"]
    records = result["records"]
    failing = [r for r in records if not r["ok"]]
    unmeasured = [r for r in records if r["unmeasured"]]

    if args.quiet:
        scope = verdict.get("scope") or {}
        print("nes_audit_all: %s, %d file(s), %d failing (%d gated), %d unmeasured, %d output file(s) skipped, "
              "exit %d"
              % (verdict["verdict"], len(records), len(failing), verdict["gated_failures"],
                 len(unmeasured), len(scope.get("excluded_by_name") or []) + len(scope.get("named_but_absent") or []),
                 result["exit_code"]))
        return result["exit_code"]

    print("nes_audit_all: %s  %d file(s), %d failing, %d unmeasured"
          % (verdict["verdict"], len(records), len(failing), len(unmeasured)))
    for line in scope_lines(verdict["scope"]):
        print(line)
    print("  palette: %s (%s)" % (verdict["palette"], verdict["palette_source"]))
    synergy = verdict.get("synergy") or {}
    if synergy.get("unmeasured"):
        print("  synergy: NOT MEASURED (%s)" % synergy["unmeasured"])
    elif synergy:
        print("  synergy: %d pair(s), %d gated failure(s), %d advisory (report %s)"
              % (synergy["entries"], synergy["gated_failures"], synergy["advisory_failures"], synergy["report"]))
    for record in sorted(failing, key=lambda r: (-(r["offending_pixels"] or 0), r["path"])):
        size = record.get("size") or [0, 0]
        print("  FAIL %-9s %-56s %dx%d  %s px  %s"
              % (record["scope"] + ("" if record["gated"] else "*"), record["path"], size[0], size[1],
                 human(record["offending_pixels"]),
                 ", ".join("%s x%d" % (rule, count) for rule, count in record["rules"].items())))
    for record in unmeasured:
        print("  UNMEASURED %-9s %s: %s" % (record["scope"], record["path"], record["unmeasured"]))
    if not args.no_write:
        print("  page: %s" % MARKDOWN_PATH.replace(os.sep, "\\"))
        print("  json: %s" % REPORT_DIR.replace(os.sep, "\\"))
        if verdict.get("preview"):
            print("  3x:   %s (%d box(es) on %s)"
                  % (PREVIEW_PATH.replace(os.sep, "\\"), verdict["preview"]["boxes"], verdict["preview"]["path"]))
    print("  exit: %d" % result["exit_code"])
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
