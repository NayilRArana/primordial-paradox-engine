/// obj_pp_title, Step: one step of the title screen.
/// The screen stops acting the moment the app machine leaves the title mode, so the overworld is not drawn over.
if (pp_app_mode() != PPMode.title) exit;
pp_title_step({});
