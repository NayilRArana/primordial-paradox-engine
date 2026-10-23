/// obj_pp_title, Create: the title screen starts here.
/// The art index is loaded first, because the screen draws from it, and then the screen is entered. pp_title_enter
/// builds the screen's own state and reads the save slot, so the state is made in exactly one place; this event used
/// to build it a second time with no phase, which read the data files twice and left a discarded struct behind.
/// Card W1: this object, in rm_pp_title, is the single owner of the screen. pp_app_boot moves the frame here and the
/// app's title mode stays out of the way while this instance exists.
global.pp.art = pp_art_init();
pp_title_enter({});
show_debug_message("PP title: room " + room_get_name(room) + " live, screen owned by obj_pp_title");
