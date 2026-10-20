# Spec 03: camera and pixel perfect scaling

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: a 256x240 window on the world, hard pixels, integer scale only, camera in whole pixels.

Numbers
- Base frame 256x240, a hard constant. Scale 1 to 6, chosen as
  `max(1, min(6, floor(min(window_w / 256, window_h / 240))))`. Default window 768x720 (3x).
- One viewport (0), 256*scale by 240*scale at the top left, window resized to match so an integer scale leaves no bars.
- Application surface resized to 256*scale by 240*scale, the pattern the manual documents on
  https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/Surfaces/application_surface.htm
  (checked 2026-10-19).
- Camera view exactly 256x240; camera position floored to whole pixels every step, no interpolation.
- Follow: dead zone 32x24 pixels, maximum 4 pixels per step, 16 pixel look ahead in the facing direction.
- Clamp: x from 0 to room_width minus 256, y from 0 to room_height minus 240, so no out of map black shows.
- GUI drawn at `display_set_gui_size(256, 240)`, so one GUI unit is one pixel at 1x.

Rules
1. Texture interpolation off once at start (`gpu_set_tex_filter(false)`); point sampling everywhere.
2. The window is never set to a non integer scale in a release build, and no smooth filter is applied at any point.
3. Movement maths may use fractions; every drawn position is snapped to integers first.
4. World to screen is one function; no object computes its own offset.
5. No rotation, no gameplay zoom, no view size change. A story "zoom", if ever needed, is a fake over two layers.
6. Scaling is recomputed on window resize and the application surface resized with it.

PP content: the FF3 style overworld (spec 04) needs a stable whole pixel camera; boss backdrops are composed for
exactly 256x240 so a variable frame would force redrawing each one; the intro's starry night drive is the only camera
move with no walker, done as a scripted pan (spec 06).

Acceptance (Nayil)
1. At 3x every tile edge is sharp, no grey fringe, the 8x8 font is crisp.
2. Resize the window by one pixel: the image snaps to a valid integer scale, never becomes blurry.
3. Walk to each map edge: no black strip, no repeated tile.
4. A long straight walk shows no one pixel shimmer on tile edges.
5. Fullscreen on a 1080p screen gives 1024x960 with black bars, not a stretched image.

Out of scope: sub pixel smooth scrolling, world rotation or zoom, per room resolutions, a boss zoom.
