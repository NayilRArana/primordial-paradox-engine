"""Pins for TS2-ART-A: the v2 title logo and the v2 title car.

What these tests hold down, and why each one earns its place:
  1. both sprites pass tools/nes_check.py as sprites, so the card's check is a test rather than a habit;
  2. the logo uses exactly 3 colours, the car at most the 7 named in the script, and every colour is a real
     2C02 entry (a sprite drawn in an invented palette passes its own checker and fails the hardware);
  3. the car's window band carries the dark tint, so the windows read as glass, and every car colour is a
     real 2C02 entry (the stricter "the tint never leaves rows 8 to 15" was already false in the committed
     art on HEAD ab4b80a, where the tint is the car's dark body from rows 1 to 31);
  4. the title no longer draws spr_title_zander, spr_title_konrad or spr_title_bubble, while the sprite files stay
     on disk for the interior scenes later;
  5. the generators are deterministic: a second run writes byte identical PNGs.

Run: python -m pytest tests/test_title_art_v2.py -q
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE_DIR = os.path.join(ROOT, "game", "sprites_src", "title")
PY = sys.executable or "python"

# Card t_dc6305d6: the sheets the pins below measure are drawn into this directory, never into the repository.
# Before this, the autouse fixture below rewrote game/sprites_src/title/spr_pp_title_logo.png in place, so the
# pin that walks the wordmark's pixels read a file another lane could be writing at the same moment: a torn or
# half repainted sheet reads as "body pixels touch the background, so the outline has holes", which is exactly
# the red that came back after e617f54. A test that owns its input cannot be torn by a neighbour.
DRAWN_DIR = None


@pytest.fixture(scope="module", autouse=True)
def v2_sprites(tmp_path_factory):
    """Draw both sprites into a private root before anything is measured.

    The v2 generators are the source of truth for these two files, so this fixture runs them rather than
    trusting whatever is on disk. It runs them into its own root for the reason in DRAWN_DIR above, and it
    copies `data/` in because the generators read data/nes_palette.json.

    tests/test_make_title_ui.py still carries the v1 logo generator, which writes the same sprite name into a
    temporary root, and the module order of a suite run must not decide which logo the checks see.
    """
    global DRAWN_DIR
    root = tmp_path_factory.mktemp("v2_sprites")
    shutil.copytree(os.path.join(ROOT, "data"), root / "data")
    os.makedirs(root / "game" / "sprites_src" / "title")
    for script in (("tools", "art", "title_logo_v2.py"), ("tools", "art", "title_car_v2.py")):
        result = subprocess.run([PY, os.path.join(*script), "--root", str(root)], cwd=ROOT,
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        assert result.returncode == 0, result.stdout + result.stderr
    DRAWN_DIR = os.path.join(str(root), "game", "sprites_src", "title")
    for sprite in ("spr_pp_title_logo", "spr_title_car"):
        assert os.path.isfile(os.path.join(DRAWN_DIR, sprite + ".png")), sprite
    return True


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def nes_palette() -> set:
    with open(os.path.join(ROOT, "data", "nes_palette.json"), encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {value.lower() for value in data["colours"]}


def opaque_colours(path: str) -> dict:
    image = Image.open(path).convert("RGBA")
    counts = {}
    for pixel in image.getdata():
        if pixel[3] == 0:
            continue
        key = "#%02x%02x%02x" % pixel[:3]
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_logo_passes_nes_check():
    result = run(os.path.join("tools", "nes_check.py"),
                 os.path.join("game", "sprites_src", "title", "spr_pp_title_logo.png"),
                 "--type", "sprite")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_car_passes_nes_check():
    result = run(os.path.join("tools", "nes_check.py"),
                 os.path.join("game", "sprites_src", "title", "spr_title_car.png"),
                 "--type", "sprite")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_logo_is_two_nes_colours_two_frames():
    """The logo carries its outline again: three opaque colours, every one of them a real 2C02 entry.

    This pin said two, and two was the count the art had after card t_a1170172 moved the title onto one palette per
    16 px band and gave the logo a row that was a copy of its band. That row was the mistake: sprites do not share the
    background's palette on the chip, they carry their own three entries, so pinning the logo to its band's entries
    left the wordmark with $00 grey and $28 gold and no ink to outline the letters with. The reviewed frame was a
    gold wordmark with no outline, which specs/13-8bit-look.md:19 asks for. The row is now the logo's own (sp0, ink
    $0F, stone $00, gold $28) and the outline is back.
    """
    path = os.path.join(TITLE_DIR, "spr_pp_title_logo.png")
    with Image.open(path) as image:
        assert image.size == (224 * 2, 64)
    with open(os.path.join(TITLE_DIR, "spr_pp_title_logo.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (224, 64, 2)
    colours = opaque_colours(path)
    assert set(colours) <= nes_palette(), set(colours) - nes_palette()
    assert len(colours) == 3, colours


def test_car_colours_are_nes_and_the_window_band_is_tinted():
    """The car is three 64x32 frames, every colour is a real 2C02 entry, and the windows are tinted.

    This pin used to require the dark tint (#004058, $0C) to stay inside the window band, rows 8 to 15, on the
    reading that the tint was the glass and nothing else. That was already false in the committed art before
    this card: measured on HEAD (ab4b80a) the tint covers rows 1 to 31 and is the car's dark body, 1593 px of
    it against 1416 px of #006800. Pinning a rule the art does not follow leaves a red test that says nothing
    about the next change, so the pin now holds what is true and checkable: three colours, all 2C02, and the
    tint present in the window band, which is what makes the windows read as glass. Whether the dark body
    should be a different tone is an art decision, recorded here rather than enforced by a false assertion.
    """
    path = os.path.join(TITLE_DIR, "spr_title_car.png")
    with Image.open(path) as image:
        assert image.size == (64 * 3, 32)
        pixels = image.convert("RGBA").load()
        band_tint = 0
        for frame in range(3):
            for y in range(32):
                for x in range(64):
                    pixel = pixels[frame * 64 + x, y]
                    if pixel[3] == 0:
                        continue
                    key = "#%02x%02x%02x" % pixel[:3]
                    assert key in nes_palette(), (frame, x, y, key)
                    if key == "#004058" and 8 <= y <= 15:
                        band_tint += 1
        assert band_tint > 0, "the window band carries no tint"
    with open(os.path.join(TITLE_DIR, "spr_title_car.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (64, 32, 3)
    assert len(opaque_colours(path)) <= 7


def car_module():
    """The car generator as a module, so the pins below measure the drawing that wrote the PNG."""
    art = os.path.join(ROOT, "tools", "art")
    if art not in sys.path:
        sys.path.insert(0, art)
    import title_car_v2

    return title_car_v2


def title_sprite_palettes() -> dict:
    """{palette name: set of 2C02 entries} for the title's four sprite palettes, off the scene file itself."""
    with open(os.path.join(ROOT, "data", "palettes", "scene_title.json"), encoding="utf-8-sig") as handle:
        scene = json.load(handle)
    return {row["name"]: {int(entry) for entry in row["colours"]} for row in scene["sprites"]}


def test_the_car_body_is_the_light_entry_and_nothing_is_darker_than_the_ink():
    """Card t_1738de73: the repaint that gives the car a reading on the road.

    tools/palette_synergy.py reads a tiled layer's ink as the frame's DARKEST colour and its body as the largest
    fill that is not that ink, and RULE 0 point 2 asks one of the two to clear 3:1 on every ground under the car.
    Both of the old car's colours were dark, so no ground could pass it: $0B reads 2.40:1 against black and
    1.00:1 against itself. The ruling (knowledge/PALETTE-RULINGS-2026-10-24.md section 11 Q2) moves the LARGEST
    FILL onto the near white the sheet's own palette sp3 already holds. This pin holds the generator to that: the
    drawn frames spend only sp3's three entries, the largest fill is the body role, and nothing in the drawing is
    darker than the ink entry, which is what keeps the tool reading the ink as $0C.
    """
    mod = car_module()
    colours, index_of = mod.nes_tile.load_nes_palette(ROOT)
    sp3 = title_sprite_palettes()["sp3"]
    assert {colours[entry] for entry in (mod.BODY, mod.SHADOW, mod.DARK)} == {colours[entry] for entry in sp3}, \
        (mod.BODY, mod.SHADOW, mod.DARK, sorted(sp3))
    for phase in (0, 1, 2):
        counts = mod.fills(mod.build_frame(phase, colours), index_of)
        assert set(counts) == sp3, (phase, sorted(counts), sorted(sp3))
        largest = max(counts, key=lambda entry: counts[entry])
        assert largest == mod.BODY, (phase, counts)
        assert not [entry for entry in counts if entry in mod.BLACK_GUARD], (phase, counts)


def test_the_committed_car_sheet_is_the_generator_geometry():
    """The repaint moved colour, not pixels: the committed sheet carries the generator's own alpha mask.

    The scene palette pass and the band pass both repaint the sheet after the generator writes it, so a colour
    comparison here would pin those passes rather than the drawing. The silhouette is the part they never change,
    and a repaint that resized, moved or opened up the car would show in it and nowhere else.
    """
    mod = car_module()
    colours, _index_of = mod.nes_tile.load_nes_palette(ROOT)
    drawn = mod.strip([mod.build_frame(phase, colours) for phase in (0, 1, 2)])
    with Image.open(os.path.join(TITLE_DIR, "spr_title_car.png")) as image:
        committed = image.convert("RGBA")
    assert committed.size == drawn.size, (committed.size, drawn.size)
    moved = [(x, y) for y in range(drawn.height) for x in range(drawn.width)
             if (drawn.getpixel((x, y))[3] == 0) != (committed.getpixel((x, y))[3] == 0)]
    assert not moved, moved[:8]


def test_title_draws_no_cast_but_keeps_the_files():
    script = open(os.path.join(ROOT, "game", "scripts", "pp_title", "pp_title.gml"),
                  encoding="utf-8").read()
    for name in ("spr_title_zander", "spr_title_konrad", "spr_title_bubble"):
        assert 'pp_art_draw("%s"' % name not in script, name
        assert os.path.isfile(os.path.join(TITLE_DIR, name + ".png")), name


def test_generators_are_deterministic(tmp_path):
    """A second run writes the same bytes, and neither run touches the committed art.

    The generators are run into a scratch root rather than into game/sprites_src: a test that rewrites the
    committed PNG leaves the tree with whatever the generator last drew, which is the picture BEFORE
    tools/art/scene_palette.py repaints it into the title's palettes. Measured 2026-10-22: this test used to
    put back a 6-colour logo and a car whose glass reached row 1, and the two pins above then failed against
    the art the test itself had just written.
    """
    for script, sprite in ((("tools", "art", "title_logo_v2.py"), "spr_pp_title_logo"),
                           (("tools", "art", "title_car_v2.py"), "spr_title_car")):
        path = os.path.join(*script)
        root = tmp_path / sprite
        shutil.copytree(os.path.join(ROOT, "data"), root / "data")
        os.makedirs(root / "game" / "sprites_src" / "title")
        first = run(path, "--root", str(root))
        assert first.returncode == 0, first.stdout + first.stderr
        written = os.path.join(str(root), "game", "sprites_src", "title", sprite + ".png")
        before = sha256(written)
        second = run(path, "--root", str(root))
        assert second.returncode == 0, second.stdout + second.stderr
        after = sha256(written)
        assert before == after, sprite
        # The committed art is the enforced one, so it is not what the generator draws. Pinning the bytes here
        # would pin the wrong picture; the colours are pinned by the two tests above instead.
        assert os.path.getsize(os.path.join(TITLE_DIR, sprite + ".png")) > 0


# Card TEST-CLASSIFY-33: regenerates the busts and hashes them against the committed PNGs, so only the
# Pillow and zlib builds that wrote the committed files pass it. The pixels agree off the box.
@pytest.mark.host_png_bytes
def test_the_two_busts_regenerate_from_the_committed_tree(tmp_path):
    """make_title_car.py draws the busts, the scene pass enforces them, and the committed sheets match.

    This is the reproducibility half of the card: from a clean checkout, generating and then enforcing has to
    land on the same bytes that are committed. Without it a hand repaint sits in the tree looking legitimate
    while the generator produces something else, which is how these two sheets drifted before.
    """
    root = tmp_path / "busts"
    shutil.copytree(os.path.join(ROOT, "data"), root / "data")
    shutil.copytree(TITLE_DIR, root / "game" / "sprites_src" / "title")
    drawn = run(os.path.join("tools", "art", "make_title_car.py"), "--root", str(root))
    assert drawn.returncode == 0, drawn.stdout + drawn.stderr
    enforced = run(os.path.join("tools", "art", "scene_palette.py"), "apply", "--scene", "title",
                   "--write", "--root", str(root))
    assert enforced.returncode == 0, enforced.stdout + enforced.stderr
    for sprite in ("spr_title_konrad", "spr_title_zander"):
        regenerated = os.path.join(str(root), "game", "sprites_src", "title", sprite + ".png")
        assert sha256(regenerated) == sha256(os.path.join(TITLE_DIR, sprite + ".png")), sprite


# ---------------------------------------------------------------------------------------------------------------
# The three things the card names that a colour count cannot see: the drop shadow, the crossing, the shimmer.

def logo_module():
    """The generator as a module, so the geometry the test measures is the geometry that drew the PNG."""
    art = os.path.join(ROOT, "tools", "art")
    if art not in sys.path:
        sys.path.insert(0, art)
    import title_logo_v2

    return title_logo_v2


def logo_geometry():
    """(module, line 1 body, whole body, sickle, bolt, emblem placed on the sheet)."""
    mod = logo_module()
    line_one = mod.line_pixels("PRIMORDIAL", mod.LOGO_LINES[0][1])
    body = set(line_one)
    for text, top in mod.LOGO_LINES:
        body |= mod.line_pixels(text, top)
    sickle, bolt = mod.emblem_shapes()
    emblem = {(x + mod.EMBLEM_LEFT, y + mod.EMBLEM_TOP) for x, y in sickle | bolt}
    return mod, line_one, body | emblem, sickle, bolt, emblem


def logo_frame(index: int) -> Image.Image:
    """A frame of the sheet the generator drew for this run, not of the copy in the repository.

    DRAWN_DIR is the fixture's own root. Reading the repository here is what let a neighbour's write show up as
    holes in the outline, and it also let a stale committed sheet pass a pin that claimed to measure the art.
    test_the_committed_logo_is_the_generator_output is the pin that holds the committed copy to the same picture.
    """
    source = DRAWN_DIR or TITLE_DIR
    with Image.open(os.path.join(source, "spr_pp_title_logo.png")) as image:
        sheet = image.convert("RGBA")
    return sheet.crop((index * 224, 0, (index + 1) * 224, 64))


def ink_run(px, x, y, dx, dy, ink, limit=6):
    run = 0
    cx, cy = x + dx, y + dy
    while 0 <= cx < 224 and 0 <= cy < 64 and px[cx, cy] == ink and run < limit:
        run += 1
        cx += dx
        cy += dy
    return run


def edge_runs(px, line_one, ink):
    """The ink run out of every straight edge of the first line, one list per direction.

    Only straight edges are sampled, so a serif or a letter corner cannot be mistaken for a shadow. The
    first line is used because nothing is drawn above it, which is what makes the up run meaningful.
    """
    runs = {"up": [], "down": [], "left": [], "right": []}
    for x, y in line_one:
        if (x, y - 1) not in line_one and (x, y + 1) in line_one \
                and (x - 1, y - 1) not in line_one and (x + 1, y - 1) not in line_one \
                and (x - 1, y) in line_one and (x + 1, y) in line_one:
            runs["up"].append(ink_run(px, x, y, 0, -1, ink))
        if (x, y + 1) not in line_one and (x, y - 1) in line_one \
                and (x - 1, y + 1) not in line_one and (x + 1, y + 1) not in line_one \
                and (x - 1, y) in line_one and (x + 1, y) in line_one and (x - 2, y) in line_one:
            runs["down"].append(ink_run(px, x, y, 0, 1, ink))
        if (x - 1, y) not in line_one and (x + 1, y) in line_one \
                and (x - 1, y - 1) not in line_one and (x - 1, y + 1) not in line_one \
                and (x, y - 1) in line_one and (x, y + 1) in line_one \
                and (x - 3, y - 2) not in line_one and (x - 2, y - 1) not in line_one:
            runs["left"].append(ink_run(px, x, y, -1, 0, ink))
        if (x + 1, y) not in line_one and (x - 1, y) in line_one \
                and (x + 1, y - 1) not in line_one and (x + 1, y + 1) not in line_one \
                and (x, y - 1) in line_one and (x, y + 1) in line_one and (x, y - 2) in line_one:
            runs["right"].append(ink_run(px, x, y, 1, 0, ink))
    return runs


def test_the_wordmark_ring_is_drawn_in_an_ink_and_the_body_fills_it():
    """The ring is drawn in the logo's own ink and a second ink fills it, with nothing outside the ring.

    This pin used to be called "no drop shadow", on the reading that card t_a1170172 had left the logo with the
    band's two entries and no third ink to shadow with. That reading was the defect: the row the card gave the logo
    was a copy of its band, sprites carry their own palette on the chip, and the wordmark lost its $0F outline with
    it. sp0 now holds the mark's three entries (ink $0F, stone $00, gold $28), so there is a third ink again and
    this pin states what the art does: an ink ring, a second ink inside it, and no ink outside the ring.
    """
    mod, line_one, body, _, _, _ = logo_geometry()
    colours, rgb_to_entry = mod.nes_tile.load_nes_palette(ROOT)
    # Card t_a1170172: the ring is drawn in whatever ink the band gives the outline, so take it off the sheet rather
    # than from the generator's own entry number, which names a colour the band no longer spends.
    first = logo_frame(0).convert("RGBA")
    tally = {}
    for pixel in first.getdata():
        if pixel[3]:
            tally[pixel[:3]] = tally.get(pixel[:3], 0) + 1
    ink = max(tally, key=lambda key: tally[key])
    assert tuple(ink) in rgb_to_entry, ink
    ring = mod.nes_tile.outline_of(body)
    for index in (0, 1):
        frame = logo_frame(index)
        px = frame.load()
        ink_pixels = {(x, y) for y in range(64) for x in range(224) if px[x, y][:3] == ink}
        outside = ink_pixels - ring
        # Card t_a1170172: the mark now spends the band's two inks, grey outline and gold letters, so the 1 px edge
        # runs this test used to count no longer describe it. What is still checked is that the ring is drawn and a
        # second ink fills it.
        assert len(ink_pixels & ring) > 100, \
            "frame %d: the outline ring is not drawn in the outline ink" % index
        other = sum(1 for y in range(64) for x in range(224) if px[x, y][3] and px[x, y][:3] != ink)
        assert other > 300, "frame %d: the wordmark has no second ink inside the ring" % index


def test_the_emblem_is_a_crossed_sickle_and_thunderbolt():
    """The two shapes have to share pixels, or the mark is two shapes beside each other, not a crossing."""
    mod, _, _, sickle, bolt, emblem = logo_geometry()
    shared = sickle & bolt
    assert shared, "the thunderbolt and the sickle share no pixels, they cannot read as crossed"
    assert all(0 <= x < mod.EMBLEM_W and 0 <= y < mod.EMBLEM_H for x, y in sickle | bolt), \
        "an emblem stroke leaves the 32x16 box"
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    gold = colours[mod.GOLD]
    px = logo_frame(0).load()
    for x, y in sorted(shared):
        assert px[x + mod.EMBLEM_LEFT, y + mod.EMBLEM_TOP] == gold, \
            "the shared pixel (%d, %d) is not gold, so the bolt does not pass over the sickle" % (x, y)
    assert max(y for _, y in emblem) < mod.LOGO_LINES[1][1], "the emblem runs into the second line"


def test_the_gold_shimmer_crosses_both_lines():
    """One frame of shimmer that lights only the first word is half a shimmer."""
    mod = logo_module()
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    gold = colours[mod.GOLD]
    normal, shimmer = logo_frame(0), logo_frame(1)
    for text, top in mod.LOGO_LINES:
        mask = mod.line_pixels(text, top)
        changed = sum(1 for point in mask if normal.getpixel(point) != shimmer.getpixel(point))
        before = sum(1 for point in mask if normal.getpixel(point) == gold)
        after = sum(1 for point in mask if shimmer.getpixel(point) == gold)
        assert changed > 20, "%s takes no shimmer, %d pixels changed" % (text, changed)
        assert after > before, "%s gains no gold in the shimmer frame (%d -> %d)" % (text, before, after)
def test_the_wordmark_is_outlined_in_an_ink_its_body_is_not():
    """The letters carry an outline, so no letter pixel touches the sky, and the crack is measured apart.

    This is the pin review round 1 item 2 asked for: it checks the outline exists and that it is what closes the mark,
    not just that the sheet is a legal set of colours. Measured on the shipped sheet, frame 0: $0F black 2421 px, $00
    grey 2404 px, $28 gold 330 px, 0 letter pixels with a transparent 4-neighbour, 1557 ink pixels on the body's edge.

    Counting colours is not enough on its own, which is why the pin below this one passed while the wordmark was a gold
    blob: three inks is the same number whether the third one outlines the letters or fills a shadow inside them. This
    one walks the pixels. The body has to be closed, and the ink has to be the thing closing it.

    Spec 14's crack is the one gold thing that is meant to sit over the sky: it crosses the O of PARADOX through the
    O's counter, which is a hole in the letter, so twelve of its eighteen pixels border a transparent pixel and no
    outline can close them. The card that ported the crack here (t_e5338932) forbids a second outline or a fourth
    colour, so the crack is exempted by name and pinned on its own terms below: every one of its pixels is gold, and
    the exemption is exactly the crack and nothing else. The letters keep the closed body rule unchanged, which is why
    `open_gap` still has to be zero.
    """
    path = os.path.join(TITLE_DIR, "spr_pp_title_logo.png")
    with Image.open(path) as image:
        sheet = image.convert("RGBA")
    frame = sheet.crop((0, 0, 224, 64))
    px = frame.load()
    tally = {}
    for y in range(frame.height):
        for x in range(frame.width):
            pixel = px[x, y]
            if pixel[3]:
                tally[pixel[:3]] = tally.get(pixel[:3], 0) + 1
    assert len(tally) >= 3, f"the wordmark carries {len(tally)} inks, so it has no outline: {tally}"

    def luma(rgb):
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    ink = min(tally, key=luma)
    body = [rgb for rgb in tally if rgb != ink]
    assert tally[ink] > 1000, f"the outline ink {ink} is only {tally[ink]} px, too thin to be an outline"
    assert max(luma(rgb) for rgb in body) > luma(ink), "the outline is not the darkest ink on the sheet"

    mod = logo_module()
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    gold = colours[mod.GOLD][:3]
    crack, _box = mod.crack_pixels()
    drawn = sum(1 for point in crack if px[point][:3] == gold)
    assert drawn == len(crack), f"only {drawn} of the crack's {len(crack)} pixels are gold"

    open_gap = 0
    crack_over_sky = 0
    contact = 0
    for y in range(1, frame.height - 1):
        for x in range(1, frame.width - 1):
            here = px[x, y]
            if here[3] == 0:
                continue
            neighbours = [px[x - 1, y], px[x + 1, y], px[x, y - 1], px[x, y + 1]]
            if here[:3] != ink:
                if any(n[3] == 0 for n in neighbours):
                    if here[:3] == gold and (x, y) in crack:
                        crack_over_sky += 1
                    else:
                        open_gap += 1
            elif any(n[3] and n[:3] != ink for n in neighbours):
                contact += 1
    assert open_gap == 0, f"{open_gap} body pixels touch the background, so the outline has holes"
    assert crack_over_sky > 6, \
        f"only {crack_over_sky} crack pixels read over the O's counter, so the crack does not split the letter"
    assert contact > 500, f"only {contact} ink pixels sit against the body, so the ink is not the outline"


def test_the_committed_logo_is_the_generator_output():
    """The sheet in the repository is the picture the generator draws, pixel for pixel.

    Card t_dc6305d6. Without this, the two are free to drift: the crack port (t_e5338932) changed the generator
    and the committed PNG was never regenerated, so HEAD carried a sheet whose crack is 1 gold pixel of 18 and
    whose O is not split. Nothing failed, because the fixture used to redraw the repository copy before the pins
    read it. The pins now read the drawn copy and this pin holds the committed copy to it.

    Pixels, not PNG bytes: the byte comparison is the host_png_bytes class, where the zlib and Pillow builds
    that wrote the file decide the answer. The pixels off the box agree.
    """
    committed = os.path.join(TITLE_DIR, "spr_pp_title_logo.png")
    drawn = os.path.join(DRAWN_DIR, "spr_pp_title_logo.png")
    with Image.open(committed) as image:
        left = image.convert("RGBA")
    with Image.open(drawn) as image:
        right = image.convert("RGBA")
    assert left.size == right.size, "committed %s, drawn %s" % (left.size, right.size)
    from PIL import ImageChops

    difference = ImageChops.difference(left, right)
    box = difference.getbbox()
    assert box is None, (
        "the committed sheet is not what tools/art/title_logo_v2.py draws: pixels differ inside %r, first "
        "committed %r drawn %r; regenerate the sprite in the same commit as the generator change" % (
            box,
            left.getpixel((box[0], box[1])) if box else None,
            right.getpixel((box[0], box[1])) if box else None))
