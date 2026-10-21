/// obj_pp_title, Draw: the title screen is drawn here.
/// The screen draws itself, so the app machine's title mode draws nothing: there is one owner per frame.
if (pp_app_mode() != PPMode.title) exit;
pp_title_draw({});
