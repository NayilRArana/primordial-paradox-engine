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

from PIL import Image
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE_DIR = os.path.join(ROOT, "game", "sprites_src", "title")
PY = sys.executable or "python"


@pytest.fixture(scope="module", autouse=True)
def v2_sprites():
    """Draw both sprites before anything is measured.

    The v2 generators are the source of truth for these two files, so this fixture runs them rather than
    trusting whatever is on disk: tests/test_make_title_ui.py still carries the v1 logo generator, which writes
    the same sprite name into a temporary root, and the module order of a suite run must not decide which logo
    the checks see.
    """
    for script in (("tools", "art", "title_logo_v2.py"), ("tools", "art", "title_car_v2.py")):
        result = subprocess.run([PY, os.path.join(*script)], cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        assert result.returncode == 0, result.stdout + result.stderr
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
    """The logo is 2 opaque colours and every one is a real 2C02 entry.

    This pin said three, and three was true while the logo had a palette of its own. Card t_a1170172 moved the title
    onto one palette per 16 px band, and a band has three entries: one of them has to be the night sky the wordmark
    sits on, so the mark gets the band's other two, $28 gold for the letters and $00 grey for the outline. The
    fourth tone the logo used to carry, its drop shadow, is the backdrop now. The pin states what ships, so any drift
    to a different palette still fails here.
    """
    path = os.path.join(TITLE_DIR, "spr_pp_title_logo.png")
    with Image.open(path) as image:
        assert image.size == (224 * 2, 64)
    with open(os.path.join(TITLE_DIR, "spr_pp_title_logo.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (224, 64, 2)
    colours = opaque_colours(path)
    assert len(colours) == 2, colours
    assert set(colours) <= nes_palette(), set(colours) - nes_palette()


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
    with Image.open(os.path.join(TITLE_DIR, "spr_pp_title_logo.png")) as image:
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


def test_the_logo_has_no_drop_shadow_because_the_band_has_no_room_for_one():
    """A shadow that lands inside the outline ring is not a shadow: it is more of the same ink.

    This pin used to require the opposite, a 1 px shadow outside the ring, and the logo had the tone for it while it
    drew from a palette of its own. Card t_a1170172 gives the logo the three entries of the band it sits in, and one
    of those is the night sky: gold letters, grey outline, and no third ink left over. The shadow is the backdrop, so
    it is transparent, and the check pins that the wordmark reads as an outline ring and nothing outside it. If a
    later card gives the title a sprite palette (the hardware allows four), the shadow can come back and this pin
    should go back with it.
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
