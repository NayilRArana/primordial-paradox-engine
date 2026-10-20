# Spec 12: audio bus

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: one music track and a budget of short sounds, crossfaded, never clicking, with separate music and effects
volume, and silence while the window is unfocused.

Rules
1. Music is one track at a time, played with audio_play_sound(sound, 10, true) and its instance id kept, per the
   manual's signature and return value
   (https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Audio/audio_play_sound.htm,
   checked 2026-10-19). Boss music uses priority 12 so it cannot be culled for an ambience.
2. SFX priority 5, UI blips 4. The channel limit is set once with audio_channel_num and never changed mid scene.
3. Loop points come from the OGG file's own loop metadata, never from a code side guess, so the musician lane owns the
   loop.
4. Crossfade: outgoing fades to 0 over 30 steps and stops; incoming starts at 0 and rises over the same 30 steps. Two
   tracks overlap only for those 30 steps.
5. `music stop` fades out over 30 steps, never cuts.
6. Text blips: one every 3 characters at 0.5 of the SFX bus, pitch from a per speaker table (spec 05).
7. Battle intro: one encounter sting, then the battle theme crossfades as the frame slides in.
8. Losing focus pauses music and stops SFX; regaining focus resumes music where it stopped.
9. A sound requested with its kind all busy replaces the oldest of that kind, so the newest hit is audible.

Budgets: 1 music, 1 ambience (reserved), 6 SFX, 2 UI, 10 channels total. Volumes: music 0.7, SFX 0.9, adjustable in
steps of 0.1 and remembered between runs.

What the musician lane delivers: OGG, 44.1 kHz, mono SFX and stereo music, music at minus 14 LUFS and SFX at minus 10,
10 ms trimmed at each end so a loop does not click, plus a sidecar text file naming source tempo and loop. FamiTracker
renders are the source of the 8-bit character; the OGG is the delivery format.

PP content: the intro's A minor waltz with scrolling text, the Percy theme in 3/4 with its E minor to G minor
modulations, and the Kronos family leitmotif that must be recognisable when it returns in the final room.

Acceptance (Nayil)
1. Walking from High Street to the Harbor crossfades with no click and no silence gap.
2. Entering the Percy fight: boss theme wins, the sting plays once.
3. Fast forwarding dialogue speeds the blips without buzzing.
4. Alt tab out and back: music pauses and resumes at the same place.
5. Music set to 0 survives a restart while SFX stays audible.

Out of scope: positional audio, reverb, layered dynamic music, a jukebox.
