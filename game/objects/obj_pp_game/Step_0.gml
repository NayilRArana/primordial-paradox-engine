/// obj_pp_game, Step: one step of the frame. Camera scaling first, then the audio bus, then the mode machine.
pp_camera_step(global.pp_camera);
pp_audio_step();
pp_app_step();
// Card R23: the scene debug keys. F1 plays every committed scene in order and prints the run log, F2 steps one command
// of the running scene. Both are dead unless the scratch run sets the self test environment variable.
pp_scene_debug_key(global.pp.world);
