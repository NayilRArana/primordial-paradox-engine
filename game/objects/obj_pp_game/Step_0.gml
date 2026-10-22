/// obj_pp_game, Step: one step of the frame. Camera scaling first, then the audio bus, then the mode machine.
pp_camera_step(global.pp_camera);
pp_audio_step();
pp_app_step();
