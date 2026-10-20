# The GameMaker project format, and how to add rooms, objects and scripts by editing text

All facts about the format in this file come from one page of the official manual, re-read at the source on
2026-10-19:
https://manual.gamemaker.io/monthly/en/Additional_Information/Project_Format.htm

Everything in this file that the manual does not state is labelled as ours or as unsourced. This file used to carry a
section headed "verified against a real GameMaker 2024.1400 project", built on a read that was quarantined as a
clean-room breach; that section is gone and nothing here rests on it.

## What the manual states

- At the root is the main project file, with a *.yyp extension. It describes the resources in the project and other
  metadata specific to it.
- Next to it is a *.resource_order file which stores the order of groups and assets in the Asset Browser when the
  filter is set to Custom Order. The manual notes GameMaker adds it to .gitignore by default when "Add skeleton .git
  defaults to new/imported projects" is enabled, because it is a user specific ordering of the asset tree.
- Resource files have the *.yy extension. They store information on individual assets: the data for the resource "and
  any other files belonging to the resource (e.g. scripts, shaders, images and audio files)". The data are stored in a
  "JSON-like format".
- A *.yy whose associated files are missing (the manual's example is a sprite missing its PNG) is reported in the
  Project Health window when the project opens.
- .gitignore and .gitattributes are added to new or imported projects when the same setting is on. The manual lists
  what the defaults do: .gitattributes marks *.yy files as linguist-generated so hosts do not misidentify the
  language, and forces LF line endings for metadata files so merges across platforms are easier. The default
  .gitignore ignores editor droppings and the .resource_order file.
- A *.yyz is a compressed project export made with Export Project > YYZ, and the manual says the compression method
  may vary with the GameMaker version. Marketplace and local packages are .yymps (2.3 and later), .yymp (before 2.3)
  and .gmez (1.x), and older resource files are .gmx (with project.gmx as the old project file); all of those are
  upgraded on import.
- If a project fails to load because resources are missing, GameMaker offers to unlink resources so the IDE can open.
  The manual states plainly that this is "not a replacement for proper source control" and "not a solution for a
  broken project". Missing package resources get a reinstall option instead.
- The same page names the Project Tool as the route for project compatibility problems.

## What the manual does NOT state, and what we therefore do

The page publishes the ROLE of each file and nothing else. It does not publish one field name for a .yyp or a .yy,
does not name event files, does not describe the room's internal structure, and does not define the "JSON-like format"
beyond that phrase. Our rule follows from that, and it is a rule about evidence, not about style:

1. Until a GameMaker-generated project exists on this PC, we write the smallest possible files and treat every
   hand-written key as UNVERIFIED. A key that appears in a blog post, a forum answer or our own generator is not a
   contract.
2. The first time Nayil opens our project in GameMaker, we immediately create one throwaway room, one object and one
   script inside the IDE, then diff those files against ours. Whatever the IDE wrote is the reference schema; our
   files get corrected to match it, and this document gets a "verified against IDE version X" note with the date.
3. We never invent a field. If we do not know a field, the asset is added inside the IDE once and the shape is copied
   from what the IDE produced.
4. Nothing in game code depends on a .yy field. Game logic reads data files, so a .yy correction is a build fix, not a
   code change.

## Safe editing procedure (our procedure, not a manual procedure)

1. Copy the file to <name>.bak-<date>-<tag> before editing. Backup naming matches the fleet convention.
2. Validate the result as JSON before saving the edit: python -c "import json,sys; json.load(open(sys.argv[1]))" <file>
   The manual calls the format JSON-like; our files are strict JSON, so a parse failure is always our mistake, and a
   file the IDE cannot read is a project that will not open.
3. Keep resource names and any GUIDs exactly as they are. Renaming an asset by editing text leaves stale references
   in the .yyp and in every file that pointed at it; rename inside the IDE instead.
4. One resource per change. Adding a room and a script in the same edit makes a bad load ambiguous.
5. After any hand edit, open the Project Health window and read it. The manual says missing associated files show up
   there.
6. Never hand edit a .yyz; it is a compressed export.

## What our generator writes today, and why that is not the format

tools\gen_project.py writes the shapes below. They are recorded here so the next person knows what is on disk, NOT as
facts about GameMaker: the manual supports none of them at the level stated, and the IDE check in the section above is
what will confirm or replace each one. Where the manual does support the general shape, that is said.

1. One folder per resource, named like the resource: a script folder with one .gml and one .yy, an object folder with
   one .yy and one .gml per event that carries code (obj_pp_game today holds Create_0.gml, Step_0.gml, Step_1.gml and
   Draw_0.gml), a room folder with one .yy. No sprite exists in the project yet; the first sprite will be created in
   the IDE and its shape copied, rather than guessed here. The manual's sentence that a .yy stores the data "and any
   other files belonging to the resource" is consistent with a folder per resource, and with one .yy per room, because
   a room's layers belong to the room; that is an inference from the manual, not a published layout, and we hold it as
   an inference. UNSOURCED and UNVERIFIED: the folder names, the file counts per folder, and the event file naming.
2. A room is ONE .yy with layers as an array inside it; instance layers carry their instances inline and tile layers
   carry a tile blob. UNSOURCED. Rooms are the most fragile hand edit, so they are generated by tools\gen_project.py
   from a small table in that script rather than typed by hand, and the first open in the IDE is still the proof.
3. Event files are named by event type and number: Create_0, Step_0, Step_1, Step_2, Draw_0, Draw_64, Draw_76,
   Alarm_<n>, Destroy_0, CleanUp_0, Other_<n>, Collision_<object>. UNSOURCED. The manual's Object Events page lists the
   event categories an object can hold (Alarm, Step, Draw and the rest) and does not name a file for any of them; the
   numbering our generator uses is therefore a guess that only the first IDE-created object can settle.
4. The .yy and .yyp dialect: a per kind version tag ("$GMObject", "$GMRoom", "$GMScript", "$GMMainOptions") and
   trailing commas. UNSOURCED, and it does not matter to us: the manual says the files are JSON-like, strict JSON
   reads as JSON-like, and every file we write is strict JSON so that tools\check_project.py can parse the project
   with the standard library.
5. Folder entries in the .yyp are a browser view: a Folders array holding folder entries with folderPath strings, and
   no folder .yy exists on disk today (the generator writes none). Whether the IDE needs one is UNVERIFIED. Our
   generator writes the Folders array and points each resource at a folder path.
6. The .yyp carries `IDEVersion 2024.1400.0.911`, a value that survives from the quarantined study copy and is the only
   fragment of it left in the repo. It is inert: no generator reads it, no check asserts it, and GameMaker rewrites it
   when the project is first saved. It is recorded here rather than replaced with a number nobody here has seen; the
   first IDE open is what turns it into a real value.

What our scripts and objects contain is our own decision, not a format question: plain .gml with
`function name(...) { ... }` bodies, no GML Visual blocks (knowledge\gml-essentials.md, section 3), and no object
inheritance (knowledge\PROVENANCE.md, our implementation differences).

## What we can and cannot verify today

- CAN verify: the files are valid JSON, the resource list in the .yyp matches the folders on disk, every event file has
  an eventList entry and the reverse, every room instance names a real object, every Included File exists in the
  mirror, no shipped file names the study copies, and our own data checker passes (tools\check_project.py,
  tools\check_data.py, and the pytest suite in tests\). These checks prove our files agree with EACH OTHER; they cannot
  prove the files are what GameMaker wants, because that reference does not exist on this machine yet.
- CANNOT verify without GameMaker installed: that the IDE opens the project with no errors, that event files are
  attached to the right event, that a room's layer order draws as expected, and that the five generator shapes above
  match what the IDE writes. Each one goes into DEVLOG.md as an open item on the day the skeleton lands, and the
  procedure under "What the manual does NOT state" answers all of them the first time Nayil opens the project.

## Build and run

The command line build is documented separately in igor-cli.md. It needs an installed runtime and an IDE login, so
nothing in this file depends on it.
