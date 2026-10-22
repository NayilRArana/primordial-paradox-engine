/// obj_pp_debug_overlay, Draw GUI: counters, derived route, the last fight's exit rows and the set flags in plain words.
if (!visible_now) exit;

var _prison_stage = 3;
if (is_struct(global.pp_data.project) && variable_struct_exists(global.pp_data.project, "prison_stage")) {
    _prison_stage = global.pp_data.project.prison_stage;
}

// The box sizes itself from the ledger, so a fight with several enemies cannot draw its rows outside the panel
// (spec 10 rule 5). One line of the dump is 12 px tall and the first one sits at y 20.
var _lines = pp_ledger_debug_lines(global.pp_ledger);
var _bottom = max(56, 20 + _lines * 12 + 4);

draw_set_alpha(0.85);
draw_set_colour(c_black);
draw_rectangle(4, 4, 244, _bottom, false);
draw_set_alpha(1);
draw_set_halign(fa_left);
draw_set_colour(c_white);
draw_text(8, 8, "mode " + string(pp_app_mode()));
draw_text(8, 20, pp_ledger_debug_text(global.pp_ledger, _prison_stage));
