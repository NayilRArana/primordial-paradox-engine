/// obj_pp_game: the one controller instance in the boot room.
/// Create builds the game frame (data, input, camera, ledger, app modes) exactly once. Nothing else in the project
/// sets any of it up, so there is one order and it is this one.
pp_app_boot();
