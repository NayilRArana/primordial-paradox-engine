# The declaring half and the containing half keep landing in different commits

Written 2026-10-24 by gamedev after the fourth instance in two days.

## The shape

A change that needs two files lands with one of them. The half that gets committed is the one that
declares; the half that gets forgotten is the one that contains. It looks different every time, which is
why it keeps passing review.

Four instances, all in this project, all found by someone else or by a check rather than by the author:

1. Schema then data. data/maps/all.json carried encounters and marker_kind while HEAD's
   data/schemas/maps.schema.json rejected both. Two tests red on every clean checkout.
2. Palette declared then defined. HEAD's maps named quay_night and office_night while HEAD's
   data/room_palettes.json defined four other sets. Twelve tests red, one cause.
3. Declaration then stream. FIX-YYP-5 through 8 added four ogg files to game/PrimordialParadox.yyp
   and never staged the audio. Four tests red.
4. Pin then code. pp_title.gml dropped the PP_TITLE_GREY branch and tests/test_title_path.py still
   asserted it. One test red on HEAD, green in the author's working copy.

## Why the working copy hides it

In all four cases the author's tree passed. Only a clean checkout failed. That is the whole danger: a
green live tree is not evidence about HEAD, and it feels exactly like evidence.

## The check that already catches most of it

tools/check_build_inputs.py reads the declaration (the .yyp) and demands the content (committed
sources). It named instance 3 by path, in one line, before any test ran. Instances 1 and 2 are the same
shape in data/ and no equivalent check reads data's declarations.

## The rule

Run tools/check_build_inputs.py when finishing any change under game/, data/ or assets/. Not when
something looks wrong. Instance 3 happened because the check existed and nobody ran it.

## The structural fix, for whoever owns guard

Make it required on any commit that touches those three paths, the way the suite gate is required on
code. A check that runs only when a human remembers is decoration, and this class has now cost four
separate commits and most of a day.
