/// obj_pp_game, Other 72: the Save/Load asynchronous event (spec 11). Both buffer_save_async and buffer_load_async
/// report here through async_load, and pp_save matches the reported id against its own request before acting, so an
/// unrelated transfer (an audio group load later, for instance) is never mistaken for a save.
/// The event number is the IDE's Async - Save/Load slot. The manual page names the event and its async_load keys but
/// does not print the number, so 72 is the one fact here that only the IDE or a running build can confirm.
pp_save_async_event();
