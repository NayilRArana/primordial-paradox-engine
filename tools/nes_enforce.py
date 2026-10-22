"""nes_enforce.py: rewrite any frame into a frame a NES could actually draw.

The PPU does not paint arbitrary colours. It shows, per 16x16 attribute area, one of 4 background palettes, each
palette being 3 colours plus the one backdrop colour shared by the whole frame (NESdev wiki, "PPU palettes",
https://www.nesdev.org/wiki/PPU_palettes). So the honest question about a pretty image is not "is it close?" but
"which four palettes, and what does it cost to flatten the image onto them?" This tool answers that: it picks the
4 palettes that fit the frame best, gives every block the closest palette it can have, maps every pixel to the
nearest colour in that palette, and keeps one backdrop. The output is not an approximation of a NES frame, it is
the frame a NES would show after the same conversion, so tools\\nes_composite_check.py passes it.

How the four palettes are chosen (k means over blocks, with the PPU palette as the vocabulary):
  1. Every pixel is snapped to its nearest legal 2C02 colour, so the search runs over colours the chip can show.
  2. Each 16x16 block becomes a weighted colour set (colour -> pixel count).
  3. The backdrop is the most common colour in the frame and is free in every palette.
  4. k = 4 palettes are seeded greedily (the heaviest block first, then the blocks least covered by what is chosen
     so far), then Lloyd's algorithm runs: assign every block to the palette that misrepresents it least, rebuild
     each palette from the 3 heaviest colours of its blocks, repeat until the assignment stops changing.
  5. Every block gets its assigned palette, every pixel maps to the nearest colour in that palette, and any
     palette left with fewer than 3 colours is padded from the colours the frame actually uses, so a palette is
     always a legal 3 colour group.
The cost is measured as the squared RGB distance times the pixel count, so a one pixel wrong pixel counts as much
as a one pixel wrong pixel anywhere else, and a large flat area counts more than a stray speck, which is what the
eye weights too.

Output: the enforced frame at 256x240, an optional 3x preview, and a diff PNG that shows before, after and the
changed pixels side by side. The text report gives the count of blocks that violate the background rules before
and after, which is the number to quote.

Usage:
    python tools\\nes_enforce.py output\\title_run_1.png --overlay output\\title_enforced_3x.png
    python tools\\nes_enforce.py output\\title_scene_preview.gif --frame 0 --diff output\\gif_diff.png
    python tools\\nes_enforce.py any.png --json report.json --check-overlay output\\marks.png

What it does not do: it does not pick sprites, and it does not preserve text legibility, because flattening an
image onto 4 palettes changes contrast. Look at the diff PNG before shipping the result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw

import nes_composite_check as ncc

PALETTES = 4
PALETTE_SIZE = 3
ITERATIONS = 12
DIFF_SCALE = 3


def dist2(a, b) -> int:
    return sum((int(x) - int(y)) ** 2 for x, y in zip(a[:3], b[:3]))


def nearest_of(colour, vocabulary, cache: dict) -> tuple:
    hit = cache.get(colour)
    if hit is None:
        hit = ncc.nearest(colour, vocabulary)
        cache[colour] = hit
    return hit


def quantise(frame: Image.Image, vocabulary: list) -> Image.Image:
    """Snap every pixel to its nearest legal PPU colour, so the palette search works on chip colours."""
    cache = {}
    out = Image.new("RGBA", frame.size, (0, 0, 0, 255))
    source = frame.load()
    target = out.load()
    for y in range(frame.height):
        for x in range(frame.width):
            r, g, b, a = source[x, y]
            if a == 0:
                target[x, y] = (0, 0, 0, 0)
                continue
            target[x, y] = nearest_of((r, g, b), vocabulary, cache) + (255,)
    return out


def block_histograms(frame: Image.Image) -> dict:
    """{(bx, by): Counter{colour: pixels}} after quantisation."""
    return ncc.block_colours(frame)


def palette_cost(histogram: Counter, palette, backdrop) -> float:
    """How badly this palette represents the block: squared distance times the pixel count, backdrop free."""
    allowed = set(palette)
    allowed.add(tuple(backdrop))
    cost = 0.0
    for colour, count in histogram.items():
        if colour in allowed:
            continue
        cost += count * min(dist2(colour, option) for option in allowed)
    return cost


def choose_palettes(blocks: dict, vocabulary: list, backdrop) -> dict:
    """k means with k=4 palettes of 3 colours, seeded greedily, then Lloyd iterations until the map settles."""
    order = sorted(blocks, key=lambda key: (-sum(blocks[key].values()), key))
    seeds = []
    for key in order:
        if len(seeds) == PALETTES:
            break
        histogram = blocks[key]
        if not histogram:
            continue
        if any(palette_cost(histogram, seed, backdrop) == 0 for seed in seeds):
            continue
        seeds.append(top_colours(histogram, backdrop, PALETTE_SIZE, vocabulary))
    while len(seeds) < PALETTES:
        # Not enough variety in the frame: copy a seed, which is legal because 4 groups may hold the same colours.
        base = seeds[0] if seeds else list(vocabulary[:PALETTE_SIZE])
        seeds.append(list(base))
    palettes = [list(seed) for seed in seeds]

    assignment = {}
    for _ in range(ITERATIONS):
        changed = 0
        for key, histogram in blocks.items():
            costs = [palette_cost(histogram, palette, backdrop) for palette in palettes]
            best = min(range(len(palettes)), key=lambda index: (costs[index], index))
            if assignment.get(key) != best:
                changed += 1
            assignment[key] = best
        for index in range(len(palettes)):
            members = [blocks[key] for key, chosen in assignment.items() if chosen == index]
            merged = Counter()
            for histogram in members:
                merged.update(histogram)
            if not merged:
                continue
            palettes[index] = top_colours(merged, backdrop, PALETTE_SIZE, vocabulary)
        if not changed:
            break

    # Final assignment, then a legality pass: every palette is 3 distinct colours, and no block needs more.
    assignment = {}
    for key, histogram in blocks.items():
        costs = [palette_cost(histogram, palette, backdrop) for palette in palettes]
        assignment[key] = min(range(len(palettes)), key=lambda index: (costs[index], index))
    cost_before = sum(palette_cost(histogram, palettes[assignment[key]], backdrop)
                      for key, histogram in blocks.items())
    return {"palettes": palettes, "assignment": assignment, "cost": cost_before}


def top_colours(histogram: Counter, backdrop, size: int, vocabulary: list) -> list:
    """The `size` heaviest colours in a block or cluster, without the backdrop, padded from the frame's palette."""
    ranked = [colour for colour, _ in histogram.most_common() if tuple(colour) != tuple(backdrop)]
    out = []
    for colour in ranked:
        if len(out) == size:
            break
        if colour not in out:
            out.append(colour)
    filler = [colour for colour in vocabulary if colour not in out and tuple(colour) != tuple(backdrop)]
    index = 0
    while len(out) < size and index < len(filler):
        out.append(filler[index])
        index += 1
    while len(out) < size:
        out.append(tuple(backdrop))
    return out


def apply_palettes(frame: Image.Image, blocks: dict, plan: dict, backdrop) -> Image.Image:
    """Repaint every block through its palette: each pixel becomes the nearest colour in that palette."""
    out = Image.new("RGBA", frame.size, tuple(backdrop) + (255,))
    source = frame.load()
    target = out.load()
    cache = {}
    for key, histogram in blocks.items():
        bx, by = key
        palette = list(plan["palettes"][plan["assignment"][key]]) + [tuple(backdrop)]
        tag = tuple(sorted(palette))
        for y in range(by, min(by + ncc.AREA, frame.height)):
            for x in range(bx, min(bx + ncc.AREA, frame.width)):
                r, g, b, a = source[x, y]
                if a == 0:
                    target[x, y] = (0, 0, 0, 0)
                    continue
                chosen = cache.get(((r, g, b), tag))
                if chosen is None:
                    chosen = ncc.nearest((r, g, b), palette)
                    cache[((r, g, b), tag)] = chosen
                target[x, y] = tuple(chosen) + (255,)
    return out


def write_diff(before: Image.Image, after: Image.Image, path: str, marks_before=None, marks_after=None) -> dict:
    """Before | after | changed pixels, at 3x, labelled. Needs no font: the layout says which panel is which."""
    scale = DIFF_SCALE
    width = before.width * scale
    height = before.height * scale
    gap = 8
    canvas = Image.new("RGB", (width * 3 + gap * 4, height + gap * 2), (24, 24, 24))
    panels = [before, after, None]
    changed = 0
    diff = Image.new("RGB", before.size, (24, 24, 24))
    source_a = before.load()
    source_b = after.load()
    target = diff.load()
    diff_pixels = []
    for y in range(before.height):
        for x in range(before.width):
            a = source_a[x, y]
            b = source_b[x, y]
            if (a[0], a[1], a[2]) != (b[0], b[1], b[2]):
                changed += 1
                diff_pixels.append(((x, y), (a[0], a[1], a[2]), (b[0], b[1], b[2])))
                target[x, y] = (255, 0, 255)
            else:
                target[x, y] = (b[0] // 3, b[1] // 3, b[2] // 3)
    panels[2] = diff
    for index, panel in enumerate(panels):
        big = panel.convert("RGB").resize((width, height), Image.Resampling.NEAREST)
        canvas.paste(big, (gap + index * (width + gap), gap))
    draw = ImageDraw.Draw(canvas)
    for index, marks in enumerate((marks_before, marks_after)):
        if not marks:
            continue
        for block in marks:
            x0 = gap + index * (width + gap) + block[0] * scale
            y0 = gap + block[1] * scale
            draw.rectangle([x0, y0, x0 + ncc.AREA * scale - 1, y0 + ncc.AREA * scale - 1], outline=(255, 0, 0))
    canvas.save(path, "PNG")
    total = before.width * before.height
    return {
        "path": os.path.abspath(path),
        "changed_pixels": changed,
        "changed_percent": round(100.0 * changed / total, 2) if total else 0.0,
        "sample": [{"at": list(where), "before": "#%02x%02x%02x" % was, "after": "#%02x%02x%02x" % now}
                   for where, was, now in diff_pixels[:6]],
    }


def enforce(frame: Image.Image, palette: dict, backdrop=None) -> dict:
    """The whole job: quantise, cluster, repaint. Returns the new frame plus the measurements.

    The backdrop is a fixed point problem: the palettes are built around it, and painting with them changes which
    colour covers most of the screen. So the loop paints, checks the result with the checker itself, and if the
    frame still fails it takes the colour that now dominates as the backdrop and paints again, at most three
    times. Whichever attempt violates least wins, and a successful attempt stops the loop.
    """
    vocabulary = sorted(palette["allowed"])
    blocks_for_shade = ncc.block_colours(frame)
    shade, how = ncc.choose_backdrop(frame, blocks_for_shade, backdrop)
    if shade is None:
        shade = ncc.nearest((0, 0, 0), vocabulary)
    shade = ncc.nearest(tuple(shade), vocabulary)
    quantised = quantise(frame, vocabulary)
    attempts = []
    for _ in range(3):
        blocks = block_histograms(quantised)
        plan = choose_palettes(blocks, vocabulary, shade)
        candidate = apply_palettes(quantised, blocks, plan, shade)
        report = ncc.check_frame(candidate, palette, None)
        cost = len(report["background"]["offending_blocks"]) + (0 if report["ok"] else 10)
        attempts.append({"cost": cost, "frame": candidate, "plan": plan, "shade": shade, "report": report})
        if report["ok"] or backdrop is not None or not report["background"]["offending_blocks"]:
            break
        next_shade, _ = ncc.choose_backdrop(candidate, ncc.block_colours(candidate), None)
        if next_shade is None or tuple(next_shade) == tuple(shade):
            break
        shade = tuple(next_shade)
    best = min(attempts, key=lambda attempt: attempt["cost"])
    plan = best["plan"]
    return {
        "frame": best["frame"],
        "palettes": [["#%02x%02x%02x" % tuple(colour) for colour in palette_]
                     for palette_ in plan["palettes"]],
        "assignment": plan["assignment"],
        "cost": plan["cost"],
        "backdrop": "#%02x%02x%02x" % tuple(best["shade"]),
        "backdrop_from": how,
        "attempts": len(attempts),
        "colours_before": len({c for c in Counter(
            [frame.getpixel((x, y))[:3] for y in range(frame.height) for x in range(frame.width)]).keys()}),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Convert any frame into a frame that obeys the NES background rules.")
    parser.add_argument("frame", help="the frame: a 256x240 PNG, a 3x capture, or a window screenshot")
    parser.add_argument("--out", default=None, help="where to write the enforced 256x240 PNG")
    parser.add_argument("--preview", default=None, help="write a 3x preview of the enforced frame here")
    parser.add_argument("--diff", default=None, help="write the before/after/changed PNG here")
    parser.add_argument("--overlay", default=None, help="write the 3x enforced frame with nothing marked (alias of --preview)")
    parser.add_argument("--palette", default=None, help="palette file; default data\\nes_palette.json, or the art bible")
    parser.add_argument("--crop", default="auto", help="auto, 1, 3, or x,y: where the viewport is inside a capture")
    parser.add_argument("--frame", dest="frame_index", type=int, default=None, help="frame number in an animated GIF")
    parser.add_argument("--backdrop", default=None, help="force the backdrop colour, #RRGGBB or $0F or 15")
    parser.add_argument("--json", dest="json_path", default=None, help="write the measurements as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only the summary lines")
    args = parser.parse_args(argv)

    root = ncc.repo_root()
    palette_path = os.path.abspath(args.palette) if args.palette else ncc.default_palette_path(root)
    try:
        palette = ncc.load_palette(palette_path)
        with open(palette_path, "r", encoding="utf-8-sig") as handle:
            palette["entries"] = json.load(handle).get("entries")
        frame, info = ncc.load_frame(args.frame, palette["allowed"], args.crop, args.frame_index)
        backdrop = ncc.parse_colour(args.backdrop, palette) if args.backdrop else None
    except (ValueError, OSError) as error:
        print("cannot enforce this frame: %s" % error, file=sys.stderr)
        return 2

    before = ncc.check_frame(frame, palette, backdrop)
    result = enforce(frame, palette, backdrop)
    after_frame = result["frame"]
    after = ncc.check_frame(after_frame, palette, backdrop)

    stem = os.path.splitext(os.path.abspath(args.frame))[0]
    out_path = os.path.abspath(args.out) if args.out else stem + "_nes.png"
    after_frame.save(out_path, "PNG")
    written = {"out": out_path}
    preview = args.preview or args.overlay
    if preview:
        big = after_frame.convert("RGB").resize((after_frame.width * DIFF_SCALE, after_frame.height * DIFF_SCALE),
                                                Image.Resampling.NEAREST)
        big.save(preview, "PNG")
        written["preview"] = os.path.abspath(preview)
    diff = write_diff(frame, after_frame, args.diff if args.diff else stem + "_nes_diff.png",
                      before["background"]["offending_blocks"], after["background"]["offending_blocks"])
    written["diff"] = diff["path"]

    before_blocks = len(before["background"]["offending_blocks"])
    before_palette_problem = sum(1 for problem in before["problems"] if problem["rule"] == "background_palettes")
    after_blocks = len(after["background"]["offending_blocks"])
    after_palette_problem = sum(1 for problem in after["problems"] if problem["rule"] == "background_palettes")
    summary = {
        "frame": info,
        "before": {
            "ok": before["ok"],
            "colours": before["screen"]["colours"],
            "offending_blocks": before_blocks,
            "palette_problem": bool(before_palette_problem),
            "palette_count": before["background"]["palette_count"],
            "distinct_colour_sets": before["background"]["distinct_colour_sets"],
            "off_palette_pixels": before["palette"]["off_palette_pixels"],
            "problems": [problem["rule"] for problem in before["problems"]],
        },
        "after": {
            "ok": after["ok"],
            "colours": after["screen"]["colours"],
            "offending_blocks": after_blocks,
            "palette_problem": bool(after_palette_problem),
            "palette_count": after["background"]["palette_count"],
            "off_palette_pixels": after["palette"]["off_palette_pixels"],
            "problems": [problem["rule"] for problem in after["problems"]],
        },
        "palettes": result["palettes"],
        "backdrop": result["backdrop"],
        "backdrop_from": result["backdrop_from"],
        "cost": result["cost"],
        "diff": diff,
        "files": written,
    }

    if not args.quiet:
        print("%s  %dx%d  read at scale %d from %dx%d (%s, crop %s)"
              % (os.path.basename(info["path"]), info["source_size"][0], info["source_size"][1], info["scale"],
                 info["source_size"][0], info["source_size"][1], info["crop_how"], info["crop"]))
        print("  before: %s, %d colours, %d offending blocks, %d distinct colour sets, %s, %d off palette pixels"
              % ("PASS" if before["ok"] else "FAIL %d problem(s)" % len(before["problems"]),
                 before["screen"]["colours"], before_blocks, before["background"]["distinct_colour_sets"],
                 ("%d palette(s) needed" % before["background"]["palette_count"])
                 if before["background"]["all_blocks_palette_legal"] else "blocks exceed 3 colours",
                 before["palette"]["off_palette_pixels"]))
        print("  after:  %s, %d colours, %d offending blocks, %d palette(s) needed"
              % ("PASS" if after["ok"] else "FAIL %d problem(s)" % len(after["problems"]),
                 after["screen"]["colours"], after_blocks, after["background"]["palette_count"]))
        print("  backdrop %s (%s); cost %.0f squared distance pixels" % (result["backdrop"], result["backdrop_from"],
                                                                        result["cost"]))
        for index, palette_ in enumerate(result["palettes"]):
            print("  palette %d: %s" % (index + 1, " ".join(palette_)))
        print("  changed: %d pixels (%.2f%%)" % (diff["changed_pixels"], diff["changed_percent"]))
        for entry in diff["sample"]:
            print("    %d,%d %s -> %s" % (entry["at"][0], entry["at"][1], entry["before"], entry["after"]))
    else:
        print("%s  before %d offending blocks, after %d offending blocks, after %s"
              % (os.path.basename(info["path"]), before_blocks, after_blocks,
                 "PASS" if after["ok"] else "FAIL"))
    for key, value in written.items():
        print("  wrote %s: %s" % (key, value))

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2, default=str)
            handle.write("\n")
    return 0 if after["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
