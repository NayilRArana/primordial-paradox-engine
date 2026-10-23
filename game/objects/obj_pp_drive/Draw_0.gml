/// obj_pp_drive, Draw: the drive draws itself here (card R21a).
/// One owner per frame: the app's own mode draws nothing for this room, which is exactly how obj_pp_title owns the
/// title screen. With PP_DRIVE_CAPTURE set the screen also writes one PNG per shot from inside this draw, so a proof
/// run reads the game's own pixels instead of a screen copy.
if (room != rm_pp_drive) exit;
pp_drive_draw({});
