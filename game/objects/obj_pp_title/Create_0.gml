/// obj_pp_title, Create: the title screen starts here.
/// The art index is loaded first, because the screen draws from it, then the screen's own state is made and the
/// screen is entered. Nothing else in the project sets the title state up, so there is one order and it is this one.
global.pp.art = pp_art_init();
pp_title_state_new();
pp_title_enter({});
