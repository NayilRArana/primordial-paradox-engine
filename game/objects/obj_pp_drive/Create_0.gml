/// obj_pp_drive, Create: the drive room's screen owner (card R21a).
/// The room is entered through the app's own door, so the screen is entered exactly once and here: the art index is
/// built if the frame has not built one yet (this room can be the first screen a capture run sees, and the caption
/// font comes from that index), the palette set is asked for by id, and the shot table is read and printed once.
if (!variable_struct_exists(global.pp, "art") || !is_struct(global.pp.art)) global.pp.art = pp_art_init();
pp_drive_enter({});
show_debug_message("PP drive: room " + room_get_name(room) + " live, screen owned by obj_pp_drive");
