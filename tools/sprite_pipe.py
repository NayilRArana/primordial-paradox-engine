"""sprite_pipe.py: concept art in, NES legal overworld and battle sprites out (card CHAR-PIPE).

The pipeline the plan asks for, in the order it runs:

    concept image (any size)
      -> segment(image)            a mask saying which pixels are the character
      -> downscale                 fit the masked character into the frame, letterboxed, alpha cut
      -> palette quantisation      every opaque pixel becomes one of the 2C02 outputs
      -> per tile constraint solver merge colours until each 8x8 tile carries 3 plus transparent
      -> sheet assembly            overworld 16x16 in four directions, battle 24x32 in seven frames
      -> tools\\nes_check.py        the validator decides whether the sheet is legal, not this tool

Two plug points are the reason this file exists before the models do:

    segment(image, ...)          calls tools\\ai_client.py segment(). Measured today, no backend answers: the
                                 default gemini backend raises NotConfigured (SAM style segmentation is the
                                 Meta lane) and the mock backend raises ValueError because this tool passes
                                 neither points nor a box. So the mask always comes from the local corner
                                 colour matte, and the refusal reason is recorded in the report under
                                 "segmentation". No data\\ai_ledger.csv row is written: the call raises before
                                 ai_client reaches its ledger write, and the file does not exist after a run.
    generate_pose(prompt)        calls tools\\ai_client.py image(). No backend returns bytes today either:
                                 gemini raises NotConfigured, the mock answers with image_bytes 0. Either way
                                 a pose that was never generated is reported as TODO instead of being faked.

What each sheet is, and why the numbers are these numbers
    overworld   16x16 per frame, down, up, left, right, 2 walk frames each, the NES sprite tile is 8x8 so a
                16x16 frame is four tiles and the solver runs per tile. Left is a mirror of right, as the card
                allows, so one authored walk cycle serves both. Frame 1 falls back to a one pixel bob when no
                pose image exists for it: deterministic, visible at 3x, and never claimed to be hand drawn.
    battle      24x32 per frame, Castlevania proportioned (taller than wide), idle 2, attack 3, hurt 1, down 1:
                seven frames. A frame with no pose image is drawn as a single colour X and named in the
                sidecar's "todo" list, so a blank slot can never pass for finished art.

A blank frame is not art
    Every finished frame is counted for visible pixels before it is pasted (opaque_pixels()). A frame with
    none, whether it came from a concept whose matte removed everything, a pose image that is fully
    transparent, or a pose file that cannot be read, is replaced by the same TODO X and named in that
    sheet's "todo" list with the reason. A sheet that ends up with no finished frame at all makes run()
    report ok false and the report prints a warning, so the CLI cannot exit 0 on an empty sheet. The
    report also records the opaque pixel count per sheet and per frame, so the claim is checkable.

What this tool deliberately does not do
    It does not judge whether the sprite is good. It does not invent a pose, a costume or a face. It does not
    run a segmentation model whose reply shape is still unknown: mask_from_reply() raises with the reason.

Usage
    python tools\\sprite_pipe.py --selftest
    python tools\\sprite_pipe.py --concept art\\hero.png --mask art\\hero_mask.png --poses art\\poses --out output\\char_pipe
    python tools\\sprite_pipe.py --concept art\\hero.png --poses art\\poses --json

Outputs, in --out (default output\\char_pipe)
    spr_pp_char_overworld.png    32x64   8 frames: rows down, up, left, right, columns walk 0, walk 1
    spr_pp_char_battle.png       168x32  7 frames: idle 0, idle 1, attack 0, attack 1, attack 2, hurt, down
    preview_3x.png               both sheets at 3x, on black, for the manager to look at
    char_pipe_report.json        sizes, mask source, colour counts, per sheet nes_check verdict, TODO list

Exit codes
    0  both sheets were written, both pass nes_check, and each sheet holds at least one finished frame
    1  a sheet failed nes_check, a sheet holds only TODO placeholders, or an input could not be read
    2  no --concept and no --selftest given
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageChops, ImageDraw

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

DEFAULT_OUT = os.path.join(ROOT, "output", "char_pipe")
PALETTE_PATH = os.path.join(ROOT, "data", "nes_palette.json")

TILE = 8
OW_FRAME = 16
BATTLE_W = 24
BATTLE_H = 32
DIRECTIONS = ("down", "up", "left", "right")
WALK_FRAMES = 2
# One entry per battle frame, in sheet order: idle 2, attack 3, hurt 1, down 1.
BATTLE_FRAMES = (
    ("idle", 0, "idle_0"),
    ("idle", 1, "idle_1"),
    ("attack", 0, "attack_0"),
    ("attack", 1, "attack_1"),
    ("attack", 2, "attack_2"),
    ("hurt", 0, "hurt_0"),
    ("down", 0, "down_0"),
)
TILE_COLOUR_LIMIT = 3
DEFAULT_MAX_COLOURS = 5
ALPHA_CUT = 128
# A frame with fewer visible pixels than this is not art: it is a blank slot that must be named TODO.
BLANK_MIN_OPAQUE = 1
PREVIEW_SCALE = 3
PREVIEW_BACKDROP = (0, 0, 0)
SEGMENT_TOLERANCE = 40
SHEET_NAMES = {"overworld": "spr_pp_char_overworld.png", "battle": "spr_pp_char_battle.png"}
REPORT_NAME = "char_pipe_report.json"
PREVIEW_NAME = "preview_3x.png"

try:  # Pillow 9 moved the resampling constants; both spellings work.
    RESAMPLE = Image.Resampling.LANCZOS
    NEAREST = Image.Resampling.NEAREST
except AttributeError:  # pragma: no cover - old Pillow
    RESAMPLE = Image.LANCZOS
    NEAREST = Image.NEAREST


# -----------------------------------------------------------------------------------------------------------------
# Reading inputs and counting what is actually visible.

class InputError(Exception):
    """An input image could not be read.

    run() turns this into a clean SystemExit for a concept or a mask, and a pose frame turns it into a TODO
    entry, so a missing file or a file that is not an image never reaches the user as a traceback.
    """


def read_image(path: str, role: str, mode: str = "RGBA") -> Image.Image:
    """Open one input image, or raise InputError naming the file and why it could not be read."""
    if not path:
        raise InputError("no %s path given" % role)
    if not os.path.isfile(path):
        raise InputError("%s %s does not exist" % (role, path))
    try:
        with Image.open(path) as handle:
            return handle.convert(mode)
    except Exception as exc:
        raise InputError("%s %s is not a readable image: %s" % (role, path, str(exc)[:160]))


def opaque_pixels(image: Image.Image) -> int:
    """How many pixels survive the alpha cut. Zero means the frame has nothing visible in it.

    A blank frame is the one defect a colour count cannot see: nes_check counts 0 colours as legal, so a
    fully transparent sheet passes it. This count is the check that a frame is art at all.
    """
    return sum(count for value, count in enumerate(image.convert("RGBA").getchannel("A").histogram())
               if value >= ALPHA_CUT)


# -----------------------------------------------------------------------------------------------------------------
# The model client, reached lazily so this module imports and runs with no key and no network.

def ai_client():
    """tools\\ai_client.py as a module, or None when it is not there. Never opens a key itself."""
    try:
        import ai_client as client
    except Exception:
        return None
    return client


def segment(image: Image.Image, path: str | None = None, points=None, box=None,
            use_client: bool = True) -> dict:
    """Mask the character out of the concept image. Returns {"mask", "source", "detail"}.

    The model is asked first, because a segmentation model is the intended source (SAM 3.1 later), but no
    backend answers today: the default gemini backend raises NotConfigured and the mock raises ValueError
    because no points and no box are passed. The refusal is recorded in "detail" verbatim, and the mask
    itself comes from the local corner colour matte: the corners of a concept render are background, and
    every pixel within SEGMENT_TOLERANCE of any distinct corner colour is treated as background. That is
    honest for flat background concept art and useless for a photographed scene, which is exactly the case
    the model will be plugged in for.

    When the real backend returns masks, mask_from_reply() decodes them. It raises today because the reply
    shape is not documented yet, and guessing it would be fiction.
    """
    detail = []
    source = "local corner matte"
    client = ai_client() if use_client else None
    if client is None:
        detail.append("tools\\ai_client.py not importable, no model call made")
    else:
        try:
            reply = client.segment(path, points=points, box=box)
            source = "model reply + local masks" if (reply or {}).get("masks") else source
            detail.append("ai_client.segment answered via %s" % (reply or {}).get("backend", "?"))
            if (reply or {}).get("mock"):
                detail.append("mock reply carries no mask pixels, using the local matte")
            elif reply:
                detail.append("mask_from_reply: %s" % _mask_from_reply_note(reply))
        except Exception as exc:  # NotConfigured on azure and meta, ValueError on mock without a box
            detail.append("ai_client.segment refused: %s" % str(exc)[:160])
    return {"mask": _corner_matte(image), "source": source, "detail": detail}


def _mask_from_reply_note(reply) -> str:
    try:
        mask_from_reply(reply)
    except NotImplementedError as exc:
        return str(exc)
    return "decoded"


def mask_from_reply(reply) -> Image.Image:
    """Decode a segmentation reply into an L mode mask. Plug point: the reply shape is still unknown."""
    raise NotImplementedError(
        "the segmentation reply shape is not documented yet (SAM 3.1 arrives with the Meta rules on Oct 26), "
        "so the mask comes from the local matte until it is")


def _corner_matte(image: Image.Image) -> Image.Image:
    """L mode mask, 255 where the character is. Background = close to any of the distinct corner colours.

    Using every distinct corner colour rather than one mean handles the usual concept render: a subject on a
    plinth or floor, so two corners are sky and two are ground. A mean of all four would be a colour that
    appears nowhere in the image, and the matte would then keep most of the background.

    Limitation, stated rather than hidden: a subject that touches a corner is partly removed with it, and a
    background with gradients leaves a halo. That case is what the segmentation model is for.
    """
    rgba = image.convert("RGBA")
    w, h = rgba.size
    corners = [rgba.getpixel((0, 0)), rgba.getpixel((w - 1, 0)),
               rgba.getpixel((0, h - 1)), rgba.getpixel((w - 1, h - 1))]
    opaque = []
    for corner in corners:
        if corner[3] < ALPHA_CUT:
            continue
        if not any(abs(corner[0] - seen[0]) + abs(corner[1] - seen[1]) + abs(corner[2] - seen[2])
                   <= SEGMENT_TOLERANCE for seen in opaque):
            opaque.append(corner)
    if not opaque:
        # The concept arrived with a transparent background already: alpha is the mask.
        return rgba.getchannel("A").point(lambda value: 255 if value >= ALPHA_CUT else 0)
    rgb = rgba.convert("RGB")
    background = Image.new("L", rgba.size, 0)
    for corner in opaque:
        flat = Image.new("RGB", rgba.size, corner[:3])
        diff = ImageChops.difference(rgb, flat).convert("L")
        near = diff.point(lambda value: 255 if value <= SEGMENT_TOLERANCE else 0)
        background = ImageChops.lighter(background, near)
    mask = ImageChops.invert(background)
    if rgba.getchannel("A").getextrema()[0] < ALPHA_CUT:
        mask = ImageChops.multiply(mask, rgba.getchannel("A"))
    return mask


def generate_pose(prompt: str, size: str = "1024x1024") -> dict:
    """Ask the image model for a pose. Returns {"status": "ready"|"todo", ...}.

    A pose that the backend did not actually return is reported todo. Nothing here writes a placeholder
    image and calls it generated.
    """
    client = ai_client()
    if client is None:
        return {"status": "todo", "reason": "tools\\ai_client.py not importable", "prompt": prompt}
    try:
        reply = client.image(prompt, size=size)
    except Exception as exc:
        return {"status": "todo", "reason": str(exc)[:160], "prompt": prompt}
    if (reply or {}).get("image_bytes"):
        return {"status": "ready", "reply": reply, "prompt": prompt}
    return {"status": "todo", "reason": "backend returned metadata and no image bytes",
            "prompt": prompt, "backend": (reply or {}).get("backend")}


# -----------------------------------------------------------------------------------------------------------------
# Palette.

def load_palette(path: str | None = None) -> dict:
    """The 2C02 palette as nes_check reads it, so this tool and the validator cannot disagree."""
    import nes_check
    chosen, why = nes_check.palette_path(ROOT, path)
    palette = nes_check.load_palette(chosen)
    return {"file": chosen, "why": why, "allowed": palette["allowed"]}


def nearest_colour(rgb, allowed) -> tuple:
    """The palette entry closest to rgb in squared RGB distance."""
    best, best_distance = None, None
    for candidate in allowed:
        distance = ((rgb[0] - candidate[0]) ** 2 + (rgb[1] - candidate[1]) ** 2
                    + (rgb[2] - candidate[2]) ** 2)
        if best_distance is None or distance < best_distance:
            best, best_distance = candidate, distance
    return best


def quantise(image: Image.Image, allowed, max_colours: int = DEFAULT_MAX_COLOURS) -> tuple:
    """Snap every opaque pixel to the palette, then keep at most max_colours of them. Returns (image, info).

    Alpha becomes 0 or 255, because nes_check fails a partial alpha pixel and a NES sprite has no half
    transparent colour. The colours kept are the ones used most, which for a character is body, outline and
    the one highlight the concept actually spends pixels on.
    """
    rgba = image.convert("RGBA")
    px = rgba.load()
    counts = Counter()
    snapped = {}
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a < ALPHA_CUT:
                px[x, y] = (0, 0, 0, 0)
                continue
            rgb = snapped.get((r, g, b))
            if rgb is None:
                rgb = nearest_colour((r, g, b), allowed)
                snapped[(r, g, b)] = rgb
            counts[rgb] += 1
            px[x, y] = (rgb[0], rgb[1], rgb[2], 255)
    keep = [colour for colour, _ in counts.most_common(max(1, max_colours))]
    dropped = [colour for colour in counts if colour not in keep]
    remap = {colour: nearest_colour(colour, keep) for colour in dropped}
    if remap:
        remap.update({colour: colour for colour in keep})
        for y in range(rgba.height):
            for x in range(rgba.width):
                r, g, b, a = px[x, y]
                if not a:
                    continue
                target = remap.get((r, g, b))
                if target and target != (r, g, b):
                    px[x, y] = (target[0], target[1], target[2], 255)
    return rgba, {"colours_snapped": len(counts), "colours_kept": len(keep),
                  "merged_to_fit": len(dropped),
                  "kept": ["#%02X%02X%02X" % colour for colour in keep]}


def enforce_tile_colours(image: Image.Image, limit: int = TILE_COLOUR_LIMIT) -> tuple:
    """The per tile constraint solver. Returns (image, merges).

    Rule: one 8x8 sprite tile carries 3 opaque colours plus transparent (nes_check sprite_tile). A 16x16
    overworld frame is four such tiles, so a frame with five colours is not automatically illegal: only a
    tile that spends four is. The solver therefore merges per tile, and recolours the whole frame when it
    merges, so the same colour never means two things in one sprite.

    The colour merged away is the one with the fewest pixels in the offending tile (the detail a downscale
    left behind), and it goes to its nearest neighbour in the same tile, which is the smallest visual change
    available. Each merge is recorded so the sidecar can show what the constraint cost.
    """
    img = image.convert("RGBA")
    px = img.load()
    merges = []
    worst = 0
    for ty in range(max(1, img.height // TILE)):
        for tx in range(max(1, img.width // TILE)):
            for _ in range(16):
                counts = Counter()
                for y in range(ty * TILE, min(img.height, ty * TILE + TILE)):
                    for x in range(tx * TILE, min(img.width, tx * TILE + TILE)):
                        r, g, b, a = px[x, y]
                        if a:
                            counts[(r, g, b)] += 1
                if len(counts) <= limit:
                    break
                victim = sorted(counts.items(), key=lambda item: (item[1], item[0]))[0][0]
                keep = [colour for colour in counts if colour != victim]
                target = nearest_colour(victim, keep)
                for y in range(img.height):
                    for x in range(img.width):
                        r, g, b, a = px[x, y]
                        if a and (r, g, b) == victim:
                            px[x, y] = (target[0], target[1], target[2], 255)
                merges.append({"tile": [tx, ty], "from": "#%02X%02X%02X" % victim,
                               "to": "#%02X%02X%02X" % target,
                               "pixels_in_tile": counts[victim]})
    for ty in range(max(1, img.height // TILE)):
        for tx in range(max(1, img.width // TILE)):
            seen = set()
            for y in range(ty * TILE, min(img.height, ty * TILE + TILE)):
                for x in range(tx * TILE, min(img.width, tx * TILE + TILE)):
                    r, g, b, a = px[x, y]
                    if a:
                        seen.add((r, g, b))
            worst = max(worst, len(seen))
    return img, {"merges": merges, "max_colours_in_a_tile": worst}


# -----------------------------------------------------------------------------------------------------------------
# Frames.

def fit_frame(image: Image.Image, size: tuple, mask: Image.Image | None = None) -> Image.Image:
    """Crop the masked content, scale it to fit a size x size frame preserving aspect, centre it."""
    width, height = size
    rgba = image.convert("RGBA")
    if mask is None:
        mask = rgba.getchannel("A")
    bbox = mask.getbbox()
    if bbox is None:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cut = rgba.crop(bbox)
    cut_mask = mask.crop(bbox)
    # The mask decides which pixels survive, so a background that is not transparent cannot leak in.
    cut.putalpha(ImageChops.multiply(cut.getchannel("A"), cut_mask))
    scale = min(width / float(cut.width), height / float(cut.height))
    target = (max(1, int(round(cut.width * scale))), max(1, int(round(cut.height * scale))))
    small = cut.resize(target, RESAMPLE)
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    frame.paste(small, ((width - target[0]) // 2, (height - target[1]) // 2))
    px = frame.load()
    for y in range(height):
        for x in range(width):
            r, g, b, a = px[x, y]
            if a < ALPHA_CUT:
                px[x, y] = (0, 0, 0, 0)
    return frame


def bob(image: Image.Image) -> Image.Image:
    """The fallback second walk frame: lift the sprite one pixel, which reads as a step at 16x16."""
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.paste(image.crop((0, 1, image.width, image.height)), (0, 0))
    return out


def _find_pose(poses: dict, *keywords) -> str | None:
    """The first pose file whose stem holds every keyword, e.g. ("right", "1") or ("attack", "1")."""
    for path in sorted(poses or {}):
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        if all(word.lower() in stem for word in keywords if word is not None):
            return path
    return None


def collect_poses(folder: str | None) -> dict:
    """{path: None} for every image in a pose folder. Missing folder is an empty dict, never an error."""
    if not folder:
        return {}
    if not os.path.isdir(folder):
        raise SystemExit("%s is not a folder" % folder)
    out = {}
    for name in sorted(os.listdir(folder)):
        if os.path.splitext(name)[1].lower() in (".png", ".jpg", ".jpeg", ".webp"):
            out[os.path.join(folder, name)] = None
    return out


def _pose_frame(path: str, size: tuple, allowed, max_colours: int) -> tuple:
    """One pose image to one legal frame, through the same fit, quantise and solver steps.

    Raises InputError when the pose file cannot be read; the caller turns that into a named TODO frame.
    """
    rgba = read_image(path, "pose image")
    mask = segment(rgba, path=path, use_client=False)["mask"]
    frame = fit_frame(rgba, size, mask)
    frame, info = quantise(frame, allowed, max_colours)
    frame, solver = enforce_tile_colours(frame)
    return frame, {"source": path, "quantise": info, "solver": solver}


def todo_frame(size: tuple, allowed, label: str) -> Image.Image:
    """A frame with no pose: transparent with a single colour X, so a blank slot is visible at 3x."""
    frame = Image.new("RGBA", size, (0, 0, 0, 0))
    ink = nearest_colour((128, 128, 128), allowed)
    draw = ImageDraw.Draw(frame)
    width, height = size
    draw.line((0, 0, width - 1, height - 1), fill=(ink[0], ink[1], ink[2], 255))
    draw.line((width - 1, 0, 0, height - 1), fill=(ink[0], ink[1], ink[2], 255))
    return frame


# -----------------------------------------------------------------------------------------------------------------
# Sheets.

def _crop_box(image: Image.Image, box) -> Image.Image:
    """The frame a recorded box names, for a byte comparison between two frames."""
    x, y, width, height = box
    return image.crop((x, y, x + width, y + height))


def _frame_entry(frame, box, label, label_key: str = "origin", reason: str | None = None) -> tuple:
    """(frame to paste, report entry) for one candidate frame; a blank frame returns None as the frame.

    The visible pixel count is taken on the frame that would have been pasted, which is the only place the
    defect can be caught: nes_check counts 0 colours as legal, so an empty frame passes it.
    """
    visible = opaque_pixels(frame) if frame is not None else 0
    entry = {"box": [box[0], box[1], box[2], box[3]], label_key: label, "opaque": visible}
    if frame is None or visible < BLANK_MIN_OPAQUE:
        entry["status"] = "TODO"
        entry["reason"] = reason or "frame has no visible pixels"
        return None, entry
    return frame, entry


def build_overworld(concept: Image.Image, mask: Image.Image, poses: dict, allowed,
                    max_colours: int = DEFAULT_MAX_COLOURS, ow_frame: int = OW_FRAME) -> tuple:
    """The FF style sheet: 4 directions x 2 walk frames at ow_frame square, left mirrored from right."""
    size = (ow_frame, ow_frame)
    sheet = Image.new("RGBA", (ow_frame * WALK_FRAMES, ow_frame * len(DIRECTIONS)), (0, 0, 0, 0))
    merges, notes = [], []

    def concept_frame():
        frame, info = _concept_frame(concept, mask, size, allowed, max_colours)
        merges.extend(info["solver"]["merges"])
        return frame

    def walk_frame(base, direction):
        """(frame, origin) for walk 1: an authored pose when one reads, otherwise the one pixel bob."""
        pose = _find_pose(poses, direction, "1")
        if pose:
            try:
                frame, info = _pose_frame(pose, size, allowed, max_colours)
                merges.extend(info["solver"]["merges"])
                return frame, "pose"
            except InputError as exc:
                notes.append("%s walk 1 pose unreadable, the bob was used: %s" % (direction, str(exc)[:120]))
        walk, _ = quantise(bob(base), allowed, max_colours)
        walk, info = enforce_tile_colours(walk)
        merges.extend(info["merges"])
        return walk, "bob"

    # Right first, so left can be its mirror, exactly as the card allows.
    base = concept_frame()
    rows = {"right": [base]}
    origins = {"right": ["concept"]}
    second, origin = walk_frame(base, "right")
    rows["right"].append(second)
    origins["right"].append(origin)
    for direction in ("down", "up"):
        first = concept_frame()
        second, origin = walk_frame(first, direction)
        rows[direction] = [first, second]
        origins[direction] = ["concept", origin]

    final = {}
    for index, direction in enumerate(DIRECTIONS):
        if direction == "left":
            continue
        for walk in range(WALK_FRAMES):
            box = (walk * ow_frame, index * ow_frame, ow_frame, ow_frame)
            frame, entry = _frame_entry(rows[direction][walk], box, origins[direction][walk])
            final["%s_%d" % (direction, walk)] = (
                todo_frame(size, allowed, "%s_%d" % (direction, walk)) if frame is None else frame, entry)
    # Left mirrors the frame that was actually pasted on the right, a TODO X included, so the mirror
    # invariant holds even when the concept came out blank.
    left_index = DIRECTIONS.index("left")
    for walk in range(WALK_FRAMES):
        name = "left_%d" % walk
        box = (walk * ow_frame, left_index * ow_frame, ow_frame, ow_frame)
        source_name = "right_%d" % walk
        mirrored = final[source_name][0].transpose(Image.FLIP_LEFT_RIGHT)
        frame, entry = _frame_entry(mirrored, box, "mirror of right")
        if final[source_name][1].get("status") == "TODO":
            # The mirror of a placeholder is a placeholder, even though its X has visible pixels.
            entry = {"box": entry["box"], "origin": "mirror of right", "opaque": entry["opaque"],
                     "status": "TODO", "reason": "mirror of the TODO %s frame" % source_name}
            frame = None
        final[name] = (todo_frame(size, allowed, name) if frame is None else frame, entry)

    frames = {}
    for index, direction in enumerate(DIRECTIONS):
        for walk in range(WALK_FRAMES):
            name = "%s_%d" % (direction, walk)
            frame, entry = final[name]
            frames[name] = entry
            sheet.paste(frame, (walk * ow_frame, index * ow_frame))
    sheet, safety = enforce_tile_colours(sheet)
    merges += safety["merges"]

    todo = [name for direction in DIRECTIONS for walk in range(WALK_FRAMES)
            if frames["%s_%d" % (direction, walk)].get("status") == "TODO"
            for name in ["%s_%d" % (direction, walk)]]
    # Four rows read as four facings, but both walk frames of down and up are the same render as right,
    # because nothing here rotates the concept. The sheet says so rather than leaving a reviewer to guess.
    facing = {}
    for walk in range(WALK_FRAMES):
        twin = "right_%d" % walk
        if frames[twin].get("status") == "TODO":
            continue
        for direction in ("down", "up"):
            name = "%s_%d" % (direction, walk)
            if frames[name].get("status") == "TODO":
                continue
            if (_crop_box(sheet, frames[name]["box"]).tobytes()
                    == _crop_box(sheet, frames[twin]["box"]).tobytes()):
                facing[name] = twin
                frames[name]["facing"] = "same render as right"
    if facing:
        notes.append("not directional: %s byte identical to the right frame of the same walk column, so "
                     "those rows hold one render and not four" % ", ".join(sorted(facing)))
    return sheet, {"frames": frames, "size": list(sheet.size), "todo": todo, "facing": facing,
                   "notes": notes, "max_colours_in_a_tile": safety["max_colours_in_a_tile"],
                   "merges": len(merges)}


def _concept_frame(concept: Image.Image, mask: Image.Image, size: tuple, allowed,
                   max_colours: int) -> tuple:
    frame = fit_frame(concept, size, mask)
    frame, info = quantise(frame, allowed, max_colours)
    frame, solver = enforce_tile_colours(frame)
    return frame, {"quantise": info, "solver": solver}


def build_battle(concept: Image.Image | None, mask: Image.Image | None, poses: dict, allowed,
                 max_colours: int = DEFAULT_MAX_COLOURS, stand_in: bool = False) -> tuple:
    """The Castlevania style sheet: 24x32, idle 2, attack 3, hurt 1, down 1. No visible frame means TODO."""
    size = (BATTLE_W, BATTLE_H)
    sheet = Image.new("RGBA", (BATTLE_W * len(BATTLE_FRAMES), BATTLE_H), (0, 0, 0, 0))
    todo, made = [], {}
    for index, (role, which, name) in enumerate(BATTLE_FRAMES):
        box = (index * BATTLE_W, 0, BATTLE_W, BATTLE_H)
        path = _find_pose(poses, role, str(which))
        if path is None:
            path = _find_pose(poses, name)
        frame, origin, reason = None, None, None
        if path:
            origin = path
            try:
                frame, info = _pose_frame(path, size, allowed, max_colours)
            except InputError as exc:
                reason = "pose image unreadable: %s" % str(exc)[:140]
        elif stand_in and concept is not None and mask is not None and index == 0:
            frame, info = _concept_frame(concept, mask, size, allowed, max_colours)
            origin = "concept stand in, not a pose"
        else:
            reason = "no pose image for this frame"
        frame, entry = _frame_entry(frame, box, origin, label_key="source", reason=reason)
        if frame is None:
            todo.append(name)
            frame = todo_frame(size, allowed, name)
        made[name] = entry
        sheet.paste(frame, (box[0], 0))
    sheet, safety = enforce_tile_colours(sheet)
    return sheet, {"frames": made, "size": list(sheet.size), "todo": todo,
                   "max_colours_in_a_tile": safety["max_colours_in_a_tile"]}



# -----------------------------------------------------------------------------------------------------------------
# Validation and preview.

def _display_path(path: str) -> str:
    """A short path for the report. relpath refuses across Windows drives, so fall back to absolute."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return os.path.abspath(path)


def check_sheet(path: str, kind: str = "sprite", palette_path_override: str | None = None) -> dict:
    """Run tools\\nes_check.py's rules over one sheet. Same function the CLI uses, no subprocess."""
    import nes_check
    chosen, why = nes_check.palette_path(ROOT, palette_path_override)
    palette = nes_check.load_palette(chosen)
    image = nes_check.load_image(path)
    report = nes_check.check(image, kind, palette)
    report["lines"] = nes_check.describe(report, _display_path(path))
    return report


def build_preview(sheets: dict, path: str, scale: int = PREVIEW_SCALE) -> str:
    """Both sheets at scale, on black, one above the other. Not a validated asset: a viewing aid."""
    scaled = []
    for name in ("overworld", "battle"):
        sheet = sheets[name]
        big = sheet.resize((sheet.width * scale, sheet.height * scale), NEAREST)
        canvas = Image.new("RGBA", big.size, PREVIEW_BACKDROP + (255,))
        canvas.alpha_composite(big)
        scaled.append(canvas)
    width = max(s.width for s in scaled)
    height = sum(s.height for s in scaled) + TILE * scale * (len(scaled) - 1)
    preview = Image.new("RGBA", (width, height), PREVIEW_BACKDROP + (255,))
    y = 0
    for canvas in scaled:
        preview.paste(canvas, (0, y))
        y += canvas.height + TILE * scale
    preview.convert("RGB").save(path)
    return path


# -----------------------------------------------------------------------------------------------------------------
# The run.

def run(concept_path: str, mask_path: str | None = None, poses_folder: str | None = None,
        out_dir: str = DEFAULT_OUT, max_colours: int = DEFAULT_MAX_COLOURS, stand_in: bool = False,
        palette_path_override: str | None = None) -> dict:
    """Concept to two sheets plus a report. Returns the report dict; writes everything it names."""
    try:
        concept = read_image(concept_path, "concept")
        mask = None
        if mask_path:
            mask = read_image(mask_path, "mask", mode="L")
            if mask.size != concept.size:
                mask = mask.resize(concept.size, NEAREST)
    except InputError as exc:
        # The shape collect_poses() already uses: a message, no traceback, exit 1.
        raise SystemExit(str(exc))
    os.makedirs(out_dir, exist_ok=True)
    if mask is not None:
        segment_info = {"mask_source": "supplied mask PNG",
                        "detail": [os.path.basename(mask_path or "")]}
    else:
        segmented = segment(concept, path=concept_path)
        mask = segmented["mask"]
        segment_info = {"mask_source": segmented["source"], "detail": segmented["detail"]}
    palette = load_palette(palette_path_override)
    allowed = sorted(palette["allowed"])
    poses = collect_poses(poses_folder)

    overworld, ow_info = build_overworld(concept, mask, poses, allowed, max_colours)
    battle, battle_info = build_battle(concept, mask, poses, allowed, max_colours, stand_in=stand_in)
    paths = {name: os.path.join(out_dir, SHEET_NAMES[name]) for name in SHEET_NAMES}
    overworld.save(paths["overworld"])
    battle.save(paths["battle"])

    checks = {name: check_sheet(paths[name], "sprite", palette_path_override) for name in paths}
    preview = build_preview({"overworld": overworld, "battle": battle},
                            os.path.join(out_dir, PREVIEW_NAME))
    sheets = {"overworld": overworld, "battle": battle}
    infos = {"overworld": ow_info, "battle": battle_info}
    for name in sheets:
        infos[name].update(sheet_verdict(sheets[name], infos[name]))
    warnings = []
    for name in ("overworld", "battle"):
        if infos[name]["blank"]:
            warnings.append("%s sheet holds no finished frame: %d of %d frames are TODO placeholders"
                            % (name, infos[name]["todo_frames"], len(infos[name]["frames"])))
    report = {
        "concept": os.path.abspath(concept_path),
        "concept_size": list(concept.size),
        "segmentation": segment_info,
        "poses_folder": os.path.abspath(poses_folder) if poses_folder else None,
        "poses_found": len(poses),
        "palette_file": os.path.relpath(palette["file"], ROOT),
        "palette_why": palette["why"],
        "max_colours": max_colours,
        "overworld": dict(ow_info, path=paths["overworld"], nes_check=_summary(checks["overworld"])),
        "battle": dict(battle_info, path=paths["battle"], nes_check=_summary(checks["battle"])),
        "preview": preview,
        "warnings": warnings,
        # nes_check alone cannot see a blank sheet (0 colours is legal), so the visible pixel count and
        # the finished frame count are part of the verdict too.
        "ok": all(checks[name]["ok"] for name in checks) and not warnings,
    }
    with open(os.path.join(out_dir, REPORT_NAME), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report


def sheet_verdict(image: Image.Image, info: dict) -> dict:
    """Visible pixel count and finished frame count for one sheet, so an empty sheet is never ok."""
    todo = set(info.get("todo") or [])
    finished = [name for name in info["frames"] if name not in todo]
    visible = opaque_pixels(image)
    return {"opaque_pixels": visible, "finished_frames": len(finished), "todo_frames": len(todo),
            "blank": visible < BLANK_MIN_OPAQUE or not finished}


def _summary(report: dict) -> dict:
    return {"ok": report["ok"], "size": report["size"], "colours": report["colours"],
            "tiles": report["tiles"], "problems": report["problems"][:20],
            "problem_count": len(report["problems"])}


def _print_report(report: dict, out_dir: str) -> None:
    print("concept      %s  %dx%d" % (report["concept"], report["concept_size"][0],
                                      report["concept_size"][1]))
    print("mask         %s (%s)" % (report["segmentation"]["mask_source"],
                                    "; ".join(report["segmentation"]["detail"]) or "no detail"))
    print("palette      %s (%s), at most %d colours per sprite"
          % (report["palette_file"], report["palette_why"], report["max_colours"]))
    print("poses        %s" % (report["poses_folder"] or "none given"))
    for name in ("overworld", "battle"):
        sheet = report[name]
        check = sheet["nes_check"]
        print("%-12s %s  %dx%d  %d colours  max %d colours in any 8x8 tile  %d/8x8 tiles opaque  "
              "%d opaque px  %s"
              % (name, os.path.basename(sheet["path"]), sheet["size"][0], sheet["size"][1],
                 check["colours"], sheet["max_colours_in_a_tile"],
                 sheet["opaque_pixels"] // (TILE * TILE), sheet["opaque_pixels"],
                 "PASS nes_check" if check["ok"] else "FAIL nes_check (%d)" % check["problem_count"]))
        if sheet["todo"]:
            print("%-12s TODO %s" % (name, _todo_line(sheet)))
        else:
            print("%-12s TODO none, every frame holds visible pixels" % name)
        for note in sheet.get("notes") or []:
            print("%-12s note %s" % (name, note))
    for warning in report.get("warnings") or []:
        print("WARNING      %s" % warning)
    print("preview      %s" % report["preview"])
    print("report       %s" % os.path.join(out_dir, REPORT_NAME))


def _todo_line(sheet: dict) -> str:
    """Every TODO frame, with the reason when it is not simply a missing pose."""
    parts = []
    for name in sheet["todo"]:
        entry = sheet["frames"].get(name) or {}
        reason = entry.get("reason")
        parts.append("%s (%s)" % (name, reason) if reason else name)
    return ", ".join(parts)



# -----------------------------------------------------------------------------------------------------------------
# Self test: a synthetic concept (circles and blocks) and synthetic poses, no models, no network.

def synthetic_concept(size: int = 256) -> Image.Image:
    """Blue sky, a grey plinth, a body block, a head circle and two accent circles.

    Deliberately more than three colours in a 16x16 frame, so the per tile solver has real work to do and
    the test proves the merge happened rather than trusting a palette that was already small.
    """
    image = Image.new("RGBA", (size, size), (32, 96, 192, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, int(size * 0.86), size, size), fill=(96, 96, 96, 255))
    draw.ellipse((int(size * 0.18), int(size * 0.02), int(size * 0.82), int(size * 0.30)),
                 fill=(16, 16, 16, 255))
    draw.rectangle((int(size * 0.26), int(size * 0.30), int(size * 0.74), int(size * 0.70)),
                   fill=(216, 56, 56, 255))
    draw.ellipse((int(size * 0.10), int(size * 0.40), int(size * 0.26), int(size * 0.56)),
                 fill=(248, 216, 120, 255))
    draw.ellipse((int(size * 0.74), int(size * 0.40), int(size * 0.90), int(size * 0.56)),
                 fill=(120, 248, 232, 255))
    draw.rectangle((int(size * 0.34), int(size * 0.70), int(size * 0.46), int(size * 0.86)),
                   fill=(16, 16, 16, 255))
    draw.rectangle((int(size * 0.54), int(size * 0.70), int(size * 0.66), int(size * 0.86)),
                   fill=(16, 16, 16, 255))
    return image


def synthetic_poses(folder: str, size: tuple = (96, 128)) -> dict:
    """Seven pose images named so the finder can match them, written to a folder. Returns {path: None}."""
    os.makedirs(folder, exist_ok=True)
    made = {}
    for index, (role, which, name) in enumerate(BATTLE_FRAMES):
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        lean = index * 2
        draw.ellipse((12 + lean, 4, size[0] - 12 + lean, 30), fill=(16, 16, 16, 255))
        draw.rectangle((16, 32, size[0] - 16, int(size[1] * 0.72)), fill=(216, 56, 56, 255))
        if role == "attack":
            draw.rectangle((size[0] - 20 + which * 6, 40, size[0] - 4 + which * 6, 52),
                           fill=(248, 216, 120, 255))
        if role == "down":
            draw.rectangle((4, int(size[1] * 0.6), size[0] - 4, int(size[1] * 0.74)),
                           fill=(16, 16, 16, 255))
        path = os.path.join(folder, "battle_%s.png" % name)
        image.save(path)
        made[path] = None
    for direction in ("down", "up", "right"):
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((12, 2, 52, 26), fill=(16, 16, 16, 255))
        draw.rectangle((16, 26, 48, 54), fill=(216, 56, 56, 255))
        draw.rectangle((14, 54, 24, 62), fill=(16, 16, 16, 255))
        draw.rectangle((40, 54, 50, 62), fill=(16, 16, 16, 255))
        image.save(os.path.join(folder, "overworld_%s_walk1.png" % direction))
    return made


def selftest(out_dir: str = DEFAULT_OUT) -> dict:
    """Build the synthetic concept and poses, run the pipeline twice, print the verdicts."""
    os.makedirs(out_dir, exist_ok=True)
    concept_path = os.path.join(out_dir, "concept_synthetic.png")
    synthetic_concept().save(concept_path)
    poses_dir = os.path.join(out_dir, "poses_demo")
    synthetic_poses(poses_dir)
    with_poses = run(concept_path, poses_folder=poses_dir, out_dir=os.path.join(out_dir, "with_poses"))
    without = run(concept_path, out_dir=os.path.join(out_dir, "no_poses"), stand_in=True)
    print("selftest: concept %s, poses %s" % (concept_path, poses_dir))
    print("\n-- with pose images --")
    _print_report(with_poses, os.path.join(out_dir, "with_poses"))
    print("\n-- without pose images (idle 0 stands in, the rest TODO) --")
    _print_report(without, os.path.join(out_dir, "no_poses"))
    return {"with_poses": with_poses, "no_poses": without}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Concept art to NES legal overworld and battle sprites.")
    parser.add_argument("--concept", help="the concept image (any size)")
    parser.add_argument("--mask", default=None,
                        help="optional mask PNG, white where the character is; without it segment() runs")
    parser.add_argument("--poses", default=None, help="folder of pose images for the animation frames")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output folder (default output\\char_pipe)")
    parser.add_argument("--max-colours", type=int, default=DEFAULT_MAX_COLOURS,
                        help="colours kept per sprite before the per tile solver runs (default 5)")
    parser.add_argument("--palette", default=None, help="palette file; default the one nes_check would use")
    parser.add_argument("--stand-in", action="store_true",
                        help="when no idle pose exists, use the concept as battle idle 0 and label it")
    parser.add_argument("--selftest", action="store_true",
                        help="build a synthetic concept and poses, run the whole pipeline, print the verdicts")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    if args.selftest:
        result = selftest(args.out)
        passed = all(run_report["ok"] for run_report in result.values())
        print("\nselftest %s" % ("PASS" if passed else "FAIL"))
        if args.json:
            print(json.dumps(result, indent=2))
        return 0 if passed else 1
    if not args.concept:
        parser.print_help()
        print("\nnothing done: pass --concept, or --selftest for the synthetic run")
        return 2
    report = run(args.concept, args.mask, args.poses, args.out, args.max_colours,
                 stand_in=args.stand_in, palette_path_override=args.palette)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report, args.out)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
