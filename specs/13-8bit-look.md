# Spec 13: the 8-bit look

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: a cartridge era look drawn today: hard pixels, a limited palette, flat colour, no gradients, sprites that read as
solid shapes, nothing that looks like a photograph with a filter over it.

Frame and pixels: 256x240, integer scaled (spec 03), point sampled, every drawable on whole pixels. No rotation, no
fractional scaling, no anti aliasing, including the font.

Palette
- One master palette of 54 colours in `data\palette.json`: 9 hues by 6 visible levels. Data, not code.
- At most 16 colours on screen at once, chosen per room and declared in that room's data.
- At most 4 colours per sprite including its outline; backgrounds may use 6; one shared transparent key.
- Every sprite is authored as indices into the master palette, so a palette swap gives a boss variant or a night map
  with no new art. New entries are only ever appended, never inserted, so existing art does not shift.

Line and shape
- 1 pixel dark outline on characters and readable objects; none on background tiles.
- No drop shadows and no soft shadows. A shadow is a 1 pixel darker line under the feet.
- Two dither patterns only, 50 percent checker and 25 percent, for skies and fog. A gradient is a stack of those, never
  a blended ramp.
- Detail budget: 3 distinct shapes in a 16x16 tile, 2 in an 8x8 glyph.
- Battle sprites follow the convention in knowledge\genre-design.md section 7: silhouette first, 2 to 4 frame loops,
  held contact frame, 32x48 player, 48x64 characters, 96x96 or larger bosses.

Font and UI
- One 8x8 font for dialogue and menus, one 8x16 for titles, both original, both as sprite sheets with fixed cells.
- Panels use the 2 pixel frame and 1 pixel outer line of spec 05.
- Whole numbers only: no decimal point and no leading zero in a damage popup.
- Cursor is a 6 pixel arrow blinking 15 steps on and 15 off.

Shader: one optional post shader may quantise the palette slightly, off by default, toggleable, a no-op at 1x, never
blurring, and cut if it costs more than 1 ms per frame on the target PC. The look is carried by the art, not by a
filter.

Rules
1. All art original. No ripped or traced sprite, font or tile from any commercial game.
2. The checker validates that every sprite's pixels reference palette indices and that no room declares over 16 colours.
3. Manual check screenshots are taken at 3x in a 768x720 window, so they compare run to run.

PP content: bronze, wine, sea and stone read well in a narrow palette; the six colour backdrop budget is what makes the
Percy ship deck, Hector's data center and the Kronos AI OS room look drawn rather than rendered; the veil lore is a 25
percent dither over the world rather than a transparency effect.

Acceptance (Nayil)
1. A 3x screenshot shows no blended colour inside a sprite.
2. A tile edge is one crisp boundary with no fringe.
3. No screen shows over 16 colours, and its room data agrees.
4. Palette swapping a boss to its night variant shifts every sprite cleanly with nothing turning black.
5. Dialogue at 1x is legible, letters are distinct, no glyph touches its cell edge.

Out of scope: scanline and CRT filters, 3D, more than two parallax layers, per pixel lighting.
