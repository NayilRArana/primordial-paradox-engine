/// obj_pp_drive, Step: one step of the drive film (card R21a).
/// The room is the screen's scope: the instance only steps while the frame is in rm_pp_drive, so a move to another
/// room cannot leave the shot clock running behind it.
if (room != rm_pp_drive) exit;
pp_drive_step({});
