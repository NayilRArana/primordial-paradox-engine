"""Tests for tools/art/title_bands.py: the title frame is NES legal at every scroll offset, not just at one.

Card t_a1170172. tools/nes_composite_check.py found two blended colours and 25 attribute areas over budget in the
composited drive frame. The tool that fixed it repaints the art per 16-px row band, because the title scrolls along x
only: a band of the screen always takes its pixels from the same band of a strip, so a band plan is stable where the
per-area palette choice was not.

These tests do not trust the tool's own report. They compose the frame the title draws, at several camera positions
including the ones the captured scroll frames were taken at, and ask tools/nes_composite_check.py, which knows
nothing about the plan, whether the result is a frame a PPU could show.
"""

from __future__ import annotations

import glob
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "art"))

import nes_composite_check as ncc  # noqa: E402
import scene_palette  # noqa: E402
import title_bands  # noqa: E402

TITLE = os.path.join(ROOT, "game", "sprites_src", "title")
SCENE_PATH = os.path.join(ROOT, "data", "palettes", "scene_title.json")
TABLE_PATH = os.path.join(ROOT, "data", "title.json")

# The camera positions the frames are composed at: a still, an arbitrary scroll, and the two positions the captured
# scroll frames were drawn at (step 290 and step 304 of the drive, saved in output/title_scroll_measure.json).
CAMERAS = (0.0, 7.0, 37.0, 160.08, 175.54)

# The title's own geometry, read from the macros the game uses so the test cannot drift from the screen.
LAYOUT = {
    "logo": (16, 0),          # PP_TITLE_LOGO_X, PP_TITLE_LOGO_Y
    "car": (76, 193),         # PP_TITLE_CAR_X, PP_TITLE_CAR_Y
    "cone": (140, 200),       # PP_TITLE_CONE_X, PP_TITLE_CONE_Y
    "sign_y": 26,             # PP_TITLE_SIGN_Y, relative to the verge layer
    "window": (56, 148),      # PP_TITLE_MENU_WIN_X, PP_TITLE_MENU_WIN_Y
    "window_tiles": (18, 9),  # PP_TITLE_MENU_WIN_TW, PP_TITLE_MENU_WIN_TH
    "row_y": 156,             # PP_TITLE_MENU_ROW_Y
    "row_step": 12,           # PP_TITLE_MENU_STEP
    "copy_y": 228,            # PP_TITLE_COPY_Y
}


def load(name: str):
    with Image.open(os.path.join(TITLE, name + ".png")) as handle:
        image = handle.convert("RGBA")
    with open(os.path.join(TITLE, name + ".json"), "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    return image, meta


def compose(camera: float, words: bool = True, puff: int = 0) -> Image.Image:
    """The title's drive frame at one camera position: the layers, then every sprite the screen draws over them.

    ``words`` draws the menu box and its rows, which is the menu phase. The prompt phase the captured scroll frames
    were taken in has only the blinking PRESS START and the copyright line, so the measurement experiment asks for
    the frame without the box: a static box in the middle of a band is content that does not scroll.

    ``puff`` chooses which frame of the animated sprites is drawn. The exhaust and the cloud turn over while the
    world scrolls, and their frames are not alike: the puff that leaves the pipe is a different picture from the one
    that has thinned. Drawing only frame 0 and calling the frame legal was how 24 blended pixels (a half transparent
    puff blended over the road) stayed invisible to this file while the game's own capture showed them. Card
    t_a1170172, review round 2.
    """
    with open(TABLE_PATH, "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    frame = Image.new("RGBA", (256, 240), (0, 0, 0, 255))
    offsets = {}
    for row in table["layers"]:
        image, meta = load(row["name"])
        width, height = meta["frame_w"], meta["frame_h"]
        strip = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        strip.paste(image.crop((0, 0, width, height)), (0, 0))
        strip.paste(image.crop((0, 0, width, height)), (width, 0))
        offset = int(round(camera * row["speed"])) % width
        offsets[row["name"]] = (offset, row["y"], width)
        frame.alpha_composite(strip.crop((offset, 0, offset + 256, height)), (0, row["y"]))

    # The road sign follows the verge's scroll one lap at a time.
    sign, sign_meta = load("spr_title_sign")
    verge_offset, verge_y, verge_w = offsets["title_L5_verge"]
    lap = (int(round(camera * 0.7)) // verge_w) if verge_w else 0
    for shift in (-verge_w, 0, verge_w):
        x = 30 - verge_offset + shift
        if -224 < x < 256:
            index = (lap + (shift // verge_w) + 400) % sign_meta["frames"]
            frame.alpha_composite(sign.crop((index * sign_meta["frame_w"], 0,
                                             (index + 1) * sign_meta["frame_w"], sign_meta["frame_h"])),
                                  (x, verge_y + LAYOUT["sign_y"]))

    cone, cone_meta = load("spr_title_cone")
    frame.alpha_composite(cone.crop((0, 0, cone_meta["frame_w"], cone_meta["frame_h"])), LAYOUT["cone"])

    exhaust, exhaust_meta = load("spr_title_exhaust")
    exhaust_index = puff % max(1, exhaust_meta["frames"])
    frame.alpha_composite(exhaust.crop((exhaust_index * exhaust_meta["frame_w"], 0,
                                        (exhaust_index + 1) * exhaust_meta["frame_w"], exhaust_meta["frame_h"])),
                          (LAYOUT["car"][0], LAYOUT["car"][1] + 14))

    car, car_meta = load("spr_title_car")
    frame.alpha_composite(car.crop((0, 0, car_meta["frame_w"], car_meta["frame_h"])), LAYOUT["car"])

    cloud, cloud_meta = load("spr_title_cloud")
    cloud_index = puff % max(1, cloud_meta["frames"])
    frame.alpha_composite(cloud.crop((cloud_index * cloud_meta["frame_w"], 0,
                                      (cloud_index + 1) * cloud_meta["frame_w"], cloud_meta["frame_h"])),
                          (LAYOUT["car"][0] + 64, 80))

    logo, logo_meta = load("spr_pp_title_logo")
    frame.alpha_composite(logo.crop((0, 0, logo_meta["frame_w"], logo_meta["frame_h"])), LAYOUT["logo"])

    # The menu box, nine sliced the way pp_window_draw stacks it.
    window, window_meta = load("spr_pp_window")
    slices = window_meta["slice"]
    tiles_w, tiles_h = LAYOUT["window_tiles"]
    ox, oy = LAYOUT["window"]
    for ty in range(tiles_h if words else 0):
        for tx in range(tiles_w):
            column = 0 if tx == 0 else (2 if tx == tiles_w - 1 else 1)
            row = 0 if ty == 0 else (2 if ty == tiles_h - 1 else 1)
            name = ("tl", "t", "tr", "l", "c", "r", "bl", "b", "br")[row * 3 + column]
            index = slices.index(name)
            tile = window.crop((index * 8, 0, index * 8 + 8, 8))
            frame.alpha_composite(tile, (ox + tx * 8, oy + ty * 8))

    # The words: the font is one row of 8x8 frames in one ink, so every label is the same white. A row that cannot be
    # chosen is marked by a 1 px rule through it in the ground band's dark green, which is what pp_title_draw_disabled
    # draws on the screen (card t_a1170172, review round 1 item 3): the second row this model used to crop does not
    # exist on the sheet, so it was drawing nothing and the copyright line was missing from the judged frame.
    font, font_meta = load("spr_pp_font8")
    dim_rgb = (0x00, 0x58, 0x00)   # PP_TITLE_DIM, 2C02 $0B, declared by both ground bands

    def draw_text(text, centre_x, y, dim):
        x = centre_x - (len(text) * 8) // 2
        for index, char in enumerate(text):
            glyph = " !'(),-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(char)
            if glyph < 0:
                continue
            cell = font.crop((glyph * 8, 0, glyph * 8 + 8, 8))
            frame.alpha_composite(cell, (x + index * 8, y))
        if dim:
            for dx in range(len(text) * 8):
                frame.putpixel((x + dx, y + 4), dim_rgb + (255,))

    for index, label in enumerate(("CONTINUE", "NEW GAME", "SETTINGS", "QUIT")):
        if words:
            draw_text(label, 128, LAYOUT["row_y"] + index * LAYOUT["row_step"], index == 0)
    draw_text("(c) 2026 NAYILINIST", 128, LAYOUT["copy_y"], True)
    return frame


def check(frame: Image.Image) -> dict:
    palette_path = ncc.default_palette_path(ROOT)
    palette = ncc.load_palette(palette_path)
    return ncc.check_frame(frame.convert("RGBA"), palette)


# ---------------------------------------------------------------------------------------------------------------
# The plan itself.

def test_the_scene_declares_one_palette_per_row_band():
    with open(SCENE_PATH, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    plan = payload["bands"]["palette"]
    assert len(plan) == 15, "240 px is fifteen 16 px bands"
    declared = {row["name"] for row in payload["background"]}
    assert set(plan) <= declared, set(plan) - declared
    assert len(declared) <= 4, "the PPU has four background palettes"


def test_every_band_spends_three_colours_or_fewer():
    scene = scene_palette.load_scene(ROOT, "title")
    for index, palette in enumerate(title_bands.band_plan(scene)):
        assert len(palette) == 3, (index, palette)
        assert len(set(palette)) == 3, (index, palette)
        assert scene.backdrop not in [scene.entry_of(rgb) for rgb in palette], \
            "band %d re-declares the backdrop, which every area already has" % index


def test_no_band_uses_a_colour_the_ppu_cannot_output():
    scene = scene_palette.load_scene(ROOT, "title")
    for index, palette in enumerate(title_bands.band_plan(scene)):
        for rgb in palette:
            entry = scene.entry_of(rgb)
            assert entry is not None, "band %d carries #%02x%02x%02x, which is not a 2C02 entry" % ((index,) + rgb)
            assert scene.usable[entry], "band %d carries $%02X, a forbidden entry" % (index, entry)


def test_the_title_spends_at_most_twelve_colours_and_the_backdrop():
    """Four background palettes of three entries is twelve colours, and that is the hardware's own ceiling.

    The plan spends eight: the two sky blues, the gold of the logo, the grey of the stars, and the four ground
    entries the fields, the road, the window and the text share. The assertion is the ceiling, not the count, so a
    later band may add an entry without this test having to be told about it.
    """
    scene = scene_palette.load_scene(ROOT, "title")
    spent = set()
    for palette in title_bands.band_plan(scene):
        spent.update(palette)
    assert len(spent) <= 12, sorted("#%02x%02x%02x" % rgb for rgb in spent)


# ---------------------------------------------------------------------------------------------------------------
# The frame, composed and judged by the checker.

def test_the_composed_frame_is_legal_at_every_camera_position():
    failures = []
    for camera in CAMERAS:
        report = check(compose(camera))
        if not report["ok"]:
            failures.append((camera, [problem["detail"] for problem in report["problems"]]))
    assert not failures, failures


def test_the_composed_frame_uses_no_blended_colour():
    for camera in CAMERAS:
        report = check(compose(camera))
        assert report["palette"]["off_palette_pixels"] == 0, \
            (camera, [problem["detail"] for problem in report["palette"]["problems"]])


def test_no_attribute_area_carries_more_than_three_colours():
    for camera in CAMERAS:
        report = check(compose(camera))
        assert report["background"]["all_blocks_palette_legal"], \
            (camera, report["background"]["offending_blocks"])


def test_the_art_on_disk_matches_the_plan():
    """The tool is idempotent: the shipped art is already what title_bands.py would write."""
    scene = scene_palette.load_scene(ROOT, "title")
    with open(TABLE_PATH, "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    for row in table["layers"]:
        image = Image.open(os.path.join(TITLE, row["name"] + ".png")).convert("RGBA")
        rows = title_bands.layer_rows(ROOT, row["name"], table, title_bands.band_plan(scene))
        copy = image.copy()
        moved = title_bands.map_image(copy, rows, tuple(scene.rgb(scene.backdrop)), "nearest")
        assert moved == 0, "%s is %d pixels away from its band plan" % (row["name"], moved)


def test_every_sprite_frame_composes_a_legal_frame():
    """Every frame the title cycles through, not just the first one.

    The exhaust and the cloud animate while the world scrolls, and the frames are not alike. This file drew frame 0
    and called the frame legal, so a half transparent puff in a later frame never reached the checker here; the game's
    own capture caught it as 24 blended pixels (#616161, #001923, #619761) at x81-86 y211-219. Card t_a1170172, review
    round 2.
    """
    _exhaust, exhaust_meta = load("spr_title_exhaust")
    _cloud, cloud_meta = load("spr_title_cloud")
    frames = max(exhaust_meta["frames"], cloud_meta["frames"])
    failures = []
    for puff in range(frames):
        for camera in (0.0, 160.08):
            report = check(compose(camera, puff=puff))
            if not report["ok"]:
                failures.append((puff, camera, [problem["detail"] for problem in report["problems"]]))
    assert not failures, failures


def test_no_title_sheet_carries_partial_alpha():
    """A NES sprite pixel is on or off, so no sheet may ship a 110/255 pixel.

    title_bands.map_image keeps the alpha it finds, and that is how the exhaust's half transparent puffs survived the
    band pass and blended against the road at draw time. The pass now resolves partial alpha before it repaints, and
    this pin holds every sheet in the folder to the same state the chips needs, whatever wrote it. Card t_a1170172,
    review round 2.
    """
    offenders = {}
    for path in sorted(glob.glob(os.path.join(TITLE, "*.png"))):
        with Image.open(path) as handle:
            alpha = handle.convert("RGBA").getchannel("A")
        partial = sum(1 for value in alpha.getdata() if value not in (0, 255))
        if partial:
            offenders[os.path.basename(path)] = partial
    assert not offenders, offenders

