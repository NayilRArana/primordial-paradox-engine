/// obj_pp_title, Create: the title screen starts here.
/// The art index is loaded first, because the screen draws from it, then the screen's own state is made and the
/// screen is entered. Nothing else in the project sets the title state up, so there is one order and it is this one.
/// Card W1: this object, in rm_pp_title, is the single owner of the screen. pp_app_boot moves the frame here and the
/// app's title mode stays out of the way while this instance exists.
global.pp.art = pp_art_init();
pp_title_state_new();
pp_title_enter({});
show_debug_message("PP title: room " + room_get_name(room) + " live, screen owned by obj_pp_title");
