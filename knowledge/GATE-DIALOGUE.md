# Gate voice: Morgan and Nye, the voice bank the bake reads

Card: t_be10336d (R38 GATE-VOICE, GAME-ROADMAP-2, step S4). Lane: research-assistant. Written 2026-10-22.
Status: content spec, the last written thing before a model touches either character.

Scope of this file: the written voice of the two NPCs D6 approved for chat, Morgan the gate sentry and Nye the dock
office clerk, in the shape the bake needs. It does not write dialogue JSON, it does not bake, and it does not edit any
data file. What it produces is one voice note, one ready to paste character block, and one line bank per NPC, plus the
three alternates for the gate's third reply and the list of what a character block must never contain.

The consumer is R29 META-BAKE (t_f943951a), which needs a character block per NPC and a hand written fallback row for
every baked line, and R30 TALK-BAKED after it. Both read spec 19; this file supplies the words spec 19 fixes the shape
of.

Read for this file, all on 2026-10-22:

| What | Where | What was taken from it |
| --- | --- | --- |
| The 14 arrival rows and the checkpoint's three replies | `knowledge/ARRIVAL-CONTENT.md` sections 4, 5, 6 and 9 | who the two people are, the beats they speak in, the three flags, the shipped wording of the branch replies |
| Character rules | `knowledge/CHARACTER-BIBLE.md` | the modern Britain register: ordinary jobs, no armour, no myth diction in the mouth |
| The two name picks | `knowledge/NAMES-BIBLE.md` sections 3.5 and 3.6 | Morgan (Old Welsh Morcant, sea plus circle) and Nye (Welsh diminutive of Aneurin, root honour) |
| The reply shape | `specs/19-llm-talk.md` sections 2 and 5 | 4 lines of 28 characters, code prepends the marker, the NPC scene allows only `none` and `end`, the character block fields |
| The five gate flags | `knowledge/GAMEDEV-DECISIONS-2026-10-22.md` D3, and `knowledge/ARRIVAL-CONTENT.md` section 9 | `gate_passed`, `gate_truth`, `gate_bluff`, `gate_authority`, `has_boarding_pass`, and which line sets which |
| The card vocabulary | `data/talk_cards.json` and `data/schemas/talk_cards.schema.json` | the shape a voice, a want, a fear and a topic already take in this project |

What was checked against the repo rather than assumed: `data/flags.json` read on 2026-10-22 holds nine flags
(`met_prometheus` to `kronos_spared`) and none of the five gate flags. D3 gives those five to ARRIVAL-MAP, append only,
after `kronos_spared`. This file therefore names the flags as ARRIVAL-CONTENT and D3 name them and touches no data file;
landing them is A2's row, not this card's. See section 8.

---

## 1. The rule every line in this file obeys

| Rule | Where it comes from | What it means here |
| --- | --- | --- |
| 28 characters maximum | spec 19 Q1, answered: 28 plus the 2 character `* ` prefix is spec 05's 30 | every bank line, every hint, measured in section 9 |
| 1 to 4 lines a reply | spec 19 section 4 | a reply is one to four bank lines, never five |
| The model never writes the marker | spec 19 Q6, answered | the bank stores the words only, with no `*` and no leading space |
| The alphabet is the font | `data/ui_layouts.json` `spr_pp_font8`: 46 glyphs, capitals, digits, space and `.,:!?'()-`, no lowercase and no quote mark | the bank is written in that alphabet, so a line cannot fail at the pixel step |
| Nobody speaks myth | `knowledge/CHARACTER-BIBLE.md` | two working people in modern Britain: no god, no oracle, no "mortal", no armour |
| Nerve, not cruelty | spec 19 system rule 7 | both men are tired, neither is a villain, and neither taunts |
| A chat line changes no state | spec 19 section 6 rule 3 | in the `npc` scene only `none` and `end` are legal, so no line sets a flag; the flags in the tables are the ones the beat sets, or the one the line reads |

One note on quotation marks, because it looks like a mistake otherwise. `data/dialogue/all.json` writes speech inside
double quotes, `* \"Honest. That is new.\"`, which is spec 05's convention. The 46 glyph font has no quote mark, and
spec 19's schema refuses one, so a line on the model path cannot carry it. The bank therefore holds the same words with
the quotes off, and where a line already ships in `data/dialogue/all.json` it is the shipped sentence with the quotes
removed and nothing else changed.

---

## 2. The beats these lines answer

| Beat id | Where it is | Who speaks | What the beat does |
| --- | --- | --- | --- |
| B20-P2 | `quay_gate_checkpoint`, page 2 | Morgan | his first speech, and the first reply of the scene |
| B20-P4 | `quay_gate_checkpoint`, page 4 | Morgan | the press: no pass, no gate, what is it |
| B20-R3 | `quay_gate_truth` / `quay_gate_bluff` / `quay_gate_authority` | Morgan | the third reply, the branch answer, which sets `gate_passed` plus exactly one of the three |
| B20-T2 | `morgan_again`, one page, gated on `gate_passed` | Morgan | the second talk, where the plot first leaks |
| MC1 to MC4 | chat, `scene` `npc`, turns 1 to 4 | Morgan | free lines the model writes at the gate, `none` or `end` only |
| B22-P2 | `quay_dock_office`, page 2 | Nye | his first speech at the counter |
| B22-P4 | `quay_dock_office`, page 4 | Nye | berth nine, deck two, do not leave the cabin |
| B22-P6 | `quay_dock_office`, page 6 | Nye | the pink slip changes hands, `has_boarding_pass` is set |
| NC1 to NC4 | chat, `scene` `npc`, turns 1 to 4 | Nye | free lines the model writes in the office, `none` or `end` only |

Beats 20 and 22 and their page numbers are ARRIVAL-CONTENT sections 4 and 5. The chat turn range is spec 19 section 3,
which allows 1 to 12; the bank covers 1 to 4 because a box that has said four things has said enough, and turn 5 and
after reuse turn 4's line.

---

## 3. Morgan, gate sentry

### 3.1 Voice note

Morgan is a leading hand on the duty watch, not an officer, and the morning is wet and nearly over. What he wants is to
hand over a clean book: his watch ending with nothing written in the incident book. What he will not say is what the
clipboard says, because the crew list is blank against the name he is about to write down, and a blank he cannot explain
is a blank that becomes his. He speaks in procedure, in the fewest words that close a sentence, and he uses the form of
the sentence to keep the person in front of him at arm's length: name, business, office, sign. He is not cruel and he is
not warm; he is a man doing paperwork in the rain who has already decided the player is somebody else's problem. He never
raises his voice, never explains himself, and never says the word "please" unless the sentence is a threat in disguise.

### 3.2 Character block, ready to paste (spec 19 section 3 shape)

```json
{
  "id": "morgan",
  "name": "Morgan",
  "voice": "Gate sentry on a wet morning watch: a leading hand, clipped procedure, fewest words that close a sentence, dry, no warmth, never raises his voice.",
  "wants": [
    "a watch that ends with nothing written down",
    "the clipboard to stay shut",
    "the player to be somebody else's problem"
  ],
  "fears": [
    "an incident book entry with his name against it",
    "an officer who wakes up tonight",
    "being asked what the list says"
  ],
  "weak_topics": [{ "topic": "the long watch" }, { "topic": "the rain" }, { "topic": "his own name in the book" }],
  "strong_topics": [{ "topic": "the clipboard" }, { "topic": "orders" }, { "topic": "threats" }],
  "phase_note": ""
}
```

Keywords and examples are deliberately absent, as spec 19 section 3 requires: they belong to the fallback scorer and
sending them would turn the talk into a keyword hunt. If this block ever lands in `data/talk_cards.json`, the card needs
keywords and examples to satisfy `data/schemas/talk_cards.schema.json`, and that is a separate card's edit, not this one.

### 3.3 Line bank

Beat codes are section 2. Flags: `sets:` names what the dialogue row hands the save, `reads:` what it is gated on,
`none` means the line moves no flag, which is every chat line.

| # | Line | Beat it answers | Flag |
| --- | --- | --- | --- |
| M1 | `FAR ENOUGH. NAME, BUSINESS.` | B20-P2, reply 1 | none, `gate_passed` is still unset |
| M2 | `NAME AND BUSINESS. SLOWLY.` | B20-P2, reply 1, the variant for a player who moved first | none |
| M3 | `NO PASS, NO GATE. WELL?` | B20-P4, reply 2, the press before the choice | none |
| M4 | `HONEST. THAT IS NEW. GO IN.` | B20-R3, the truth branch, one line of the shipped pair | sets: `gate_passed`, `gate_truth` |
| M5 | `THE LIST IS FULL. OFFICE.` | B20-R3, the bluff branch, one line of the shipped pair | sets: `gate_passed`, `gate_bluff` |
| M6 | `THE OFFICER SLEEPS. OFFICE.` | B20-R3, the authority branch, one line of the shipped pair | sets: `gate_passed`, `gate_authority` |
| M7 | `YOU TOLD ME THE TRUTH.` | B20-T2, the second talk on the truth branch | reads: `gate_truth` |
| M8 | `I CHECKED THE LIST AGAIN.` | B20-T2, the second talk on the bluff branch, the line where the plot leaks | reads: `gate_bluff` |
| M9 | `HE WAS NOT ASLEEP.` | B20-T2, the second talk on the authority branch | reads: `gate_authority` |
| M10 | `NOTHING IN THE BOOK TONIGHT.` | MC1, chat turn 1, what he wants said out loud | none, `none` effect |
| M11 | `DO NOT READ THE CLIPBOARD.` | MC3, chat turn 3, a player line that pushed on the clipboard | none, `setback` is refused in chat and becomes `none` |
| M12 | `GO ON. BEFORE I WRITE YOU.` | MC4, chat turn 4, the `end` line | none, the box closes |

M1 and M2 are the same beat by design: the reply is one line, and which of the two a bake picks is the choice. M4, M5
and M6 are the first line of each shipped branch pair; the second line of each pair is in the alternates table, so a
bake can build a whole third reply out of this file alone.

---

## 4. The gate's third reply: three alternates

The third reply, B20-R3, is the branch answer after the player picks a choice, and it is the only place in the block
where the gate's voice carries a consequence. The shipped version is in `data/dialogue/all.json` and in M4, M5 and M6.
Each alternate below is a complete two line reply that sits against the same one flag, lifts the same barrier, and costs
the same seconds, so a bake can choose without changing what the game does.

| # | Line | Answers | Flag |
| --- | --- | --- | --- |
| A1A | `NO PASS, AND YOU SAID SO.` | B20-R3 alternate, line 1 of 2, truth | sets: `gate_passed`, `gate_truth` |
| A1B | `OFFICE. SIGN IN.` | B20-R3 alternate, line 2 of 2, truth | sets: `gate_passed`, `gate_truth` |
| A2A | `FULL LIST. NOT FOR LONG.` | B20-R3 alternate, line 1 of 2, bluff | sets: `gate_passed`, `gate_bluff` |
| A2B | `SIGN AND GO.` | B20-R3 alternate, line 2 of 2, bluff | sets: `gate_passed`, `gate_bluff` |
| A3A | `HE IS NOT ASLEEP. NOTED.` | B20-R3 alternate, line 1 of 2, authority | sets: `gate_passed`, `gate_authority` |
| A3B | `OFFICE. NOW.` | B20-R3 alternate, line 2 of 2, authority | sets: `gate_passed`, `gate_authority` |

What each alternate is doing to the character. A1 is the honest man getting a small gift and not saying thank you: "you
said so" is the closest Morgan comes to respect. A2 is him not reading the list, which is the bluff working, and "not
for long" is the first time he admits the list can change. A3 is the officer who is not asleep, so the second talk's
revelation lands as a correction rather than a surprise, which is what the authority branch is for.

One rule the alternates do not bend: none of them may open the gate conditionally, name a person, or promise anything.
All three lift the barrier because the gate cannot be failed (ARRIVAL-CONTENT section 6), and `gate_passed` is set by
whichever reply plays.

---

## 5. Nye, dock office clerk

### 5.1 Voice note

Nye is the only man in the dock office still doing the paperwork honestly, and the handles of the ledger have gone warm
under his hands. What he wants is for the ledger to balance, so the last berth is filled and he can shut the office and
go home. What he will not say is who put the player's name on the manifest, because the last line in the book is not in
his handwriting and he has stopped asking, which is the one place where his honesty has quietly given up. He speaks in
official sentences: short, exact, counting things twice, fussing about the pen and the ink, courteous to a fault because
courtesy is the only authority a clerk has. He does not joke and he does not threaten. Where Morgan's lines are a door
closing, Nye's are a form being completed, and his warmth, when it comes, arrives as a small exact kindness: the berth,
the deck, the warning about the cabin.

### 5.2 Character block, ready to paste (spec 19 section 3 shape)

```json
{
  "id": "nye",
  "name": "Nye",
  "voice": "Dock office clerk: exact and courteous, counts everything twice, fussy about pen and ink, short official sentences, never raises his voice and never jokes.",
  "wants": [
    "the ledger to balance",
    "the last berth filled so the office can shut",
    "to be home before the light"
  ],
  "fears": [
    "a line in the book that is not in his hand",
    "a name he cannot account for",
    "being asked who signed it"
  ],
  "weak_topics": [{ "topic": "the ledger" }, { "topic": "the last line" }, { "topic": "going home" }],
  "strong_topics": [{ "topic": "the manifest" }, { "topic": "who signed" }, { "topic": "the Navy" }],
  "phase_note": ""
}
```

Same note as Morgan's block: no keywords, no examples, because spec 19 section 3 keeps them home.

### 5.3 Line bank

| # | Line | Beat it answers | Flag |
| --- | --- | --- | --- |
| N1 | `YOU ARE THE LAST ONE. NAME.` | B22-P2, reply 1 | none, `has_boarding_pass` is not set yet |
| N2 | `NAME, THEN. SLOWLY. PEN WET.` | B22-P2, reply 1, the variant for a player who gave a name at once | none |
| N3 | `BERTH NINE. DECK TWO.` | B22-P4, reply 2, line 1 | none |
| N4 | `DO NOT LEAVE THE CABIN.` | B22-P4, reply 2, line 2, the one warning he gives | none |
| N5 | `SIGN HERE. THE BOOK SHUTS.` | B22-P6, the pass changes hands | sets: `has_boarding_pass` |
| N6 | `LEDGER BALANCES. GOODNIGHT.` | B22-P6, his last line, the want granted | sets: `has_boarding_pass` |
| N7 | `I COUNT WHAT I AM GIVEN.` | NC1, chat turn 1, the weak topic a player can find | none |
| N8 | `THE LAST LINE IS NOT MINE.` | NC3, chat turn 3, a player line that pushed on the manifest | none, `setback` is refused in chat and becomes `none` |
| N9 | `I WANT TO GO HOME TOO.` | NC3, the soft spot: the man behind the counter | none, `soften` is refused in chat and becomes `none` |
| N10 | `GOODNIGHT. SHUT THE DOOR.` | NC4, chat turn 4, the `end` line | none, the box closes |

N6 is the same beat as N5 and the two are not interchangeable: N5 is the transaction, N6 is the man after it. A bake
that uses both spends two of its four lines on one beat, which is legal and is the warmest the office gets.

---

## 6. Hint slot lines

Spec 19 Q9 gives the hit a fourth line under the box, at most 28 characters, in the second ink, and spec 19 section 3
forbids a command and the words MERCY, HP and RULES. These four are noun phrases a player can act on, each naming
something its character already answers to.

| # | Hint | NPC | Answers |
| --- | --- | --- | --- |
| H1 | `THE WATCH AND THE RAIN.` | Morgan | MC1, after a neutral or off topic line |
| H2 | `THE CLIPBOARD.` | Morgan | MC2, after the player pushed on orders |
| H3 | `THE LEDGER. THE LAST LINE.` | Nye | NC1, after a neutral line |
| H4 | `BERTH NINE.` | Nye | NC2, after the pass is in hand |

---

## 7. What the character block must never contain

Four things, and each one is a rule with a test rather than a preference. Spec 19 section 3 already lists most of these
as never sent on any path; this section is the version a bake card can check against the block it built.

1. **No key, and nothing that leads to one.** No key name, no key value, no environment variable name, no endpoint, no
   URL, no model id, no provider name, no file path, no cache path. The block is character data. Under D5 the shipped
   game holds no key at all, and a block that names one would be the first place a key could leak from.
2. **No real address.** No house number, no postcode, no street number, no coordinate, and no building name used as an
   address. The block says `southampton_dock` and `quay_dock_office`, which are the ids the data already carries, and
   the lines say "the gate", "the office" and "the quay". The OSM extract is full of named premises; a character block is
   not a place to publish one, and a clerk who says an address reads as a delivery note, not as a man.
3. **The player's real name, or any name for the player.** No name field, no "Aeson", no "Kit", no pronoun that assumes
   one. Spec 19 section 3 never sends the player's name, and the block must not carry it either, because a block is
   written once and read on every turn: a name in it is a name in every reply. The player is "you", "the last one", "the
   one at the gate".
4. **Anything about a real person in the OSM extract.** The extract is ways and nodes; it holds no person, and it does
   hold the contributors' own `source` tags (25 Bing, 4 survey, 3 maxar) and real trading names. No contributor name, no
   business operator, no member of staff, no named landlord and no "the landlord says" enters the block or the lines.
   This is also why the nightclub's OSM name never appears here: ARRIVAL-CONTENT section 8 keeps it off the screen, and
   this file keeps it out of the block for the same reason.

Two names are retired in `knowledge/NAMES-BIBLE.md` section 2, the two old picks that the Skye rule replaced, and
neither may appear anywhere in this file. The check in section 9 reads the retired list out of that section rather than
copying it here, so the two names are named in exactly one place in the repo.

---

## 8. What this file does not decide, and Q: for gamedev

- It does not write `data/dialogue/all.json`. R22 owns that file and the arrival rows; three of them already ship
  (`quay_gate_truth`, `quay_gate_bluff`, `quay_gate_authority`) and the rest of section 5 of ARRIVAL-CONTENT is R22's
  to land.
- It does not write `data/flags.json`. Read 2026-10-22, that file holds nine flags and none of the five gate flags. D3
  hands the five to ARRIVAL-MAP, append only, in this order: `gate_passed`, `gate_truth`, `gate_bluff`,
  `gate_authority`, `has_boarding_pass`. The bank names them from ARRIVAL-CONTENT section 9 and D3 and waits for that
  row.
- It does not decide the bake file's format, the model, or the fallback ids. R29 META-BAKE owns those, and its rows
  need one fallback id per bank line that can be a reply on its own.
- It does not write a talk card for either man. Spec 19 Q5 and Q10 put them in scope for chat, not for a fight.

Q1. Spec 19 section 2's consumer table pairs "the talk fight with Morgan the gate sentry (beat 28)" with the effect path.
No data carries that: `data/encounters/all.json` has two encounters, beat 28 is `tutorial_sailors` (the `navy_sailor`
card, 15 hp) and Morgan has no enemy id and no encounter row, while his scene is beat 20 and cannot be failed. Please
say which is meant: Morgan gets a talk encounter row at beat 28 and a card, or section 2's row is the gate chat and the
phrase "talk fight" is a slip. This file writes the chat only, so nothing here blocks either way, but R29's row list
follows that answer.

Q2. `knowledge/NAMES-BIBLE.md` section 3.6 casts Nye as the High Street herald, and D6 Q5 and Q10 plus ARRIVAL-CONTENT
section 4.2 make him the dock office clerk, with Cass holding the High Street line. This is the same conflict spec 19
raised as Q12 and it is still open. This file follows D6, because a head ruled it: one paragraph and one block change if
the bible's casting ships instead, and no bank line changes, because none of them names the street.

---

## 9. Checks, and what each one measured

Every check below was run on 2026-10-22 with `scan_gate_dialogue.py`, a scratch script that reads this file and
`data/ui_layouts.json` and prints what it finds. It is not committed, because the card's scope is this file.

| Check | How it was proved | Result |
| --- | --- | --- |
| Every line is 28 characters or fewer | the script reads every row of the four line tables and measures the string between the backticks | 32 rows measured, 0 over 28 |
| The longest line, printed | the script prints the longest line with its id and its length | N2, 28 characters, `NAME, THEN. SLOWLY. PEN WET.`, tied with M10 at 28 |
| Every character is drawable | each character of each line is looked up in `spr_pp_font8`'s glyph string in `data/ui_layouts.json`, read from the file rather than typed into the script | 0 refused characters, every character is in the 46 glyph string |
| No quote mark or asterisk in a line | the same scan refuses `"` and `*` outright | 0 of each |
| Every line names the beat it answers | every row's beat cell is non empty and starts with a beat id from section 2 | 32 of 32 rows carry a beat id |
| The three alternates sit against the three flags | A1A and A1B carry `gate_truth`, A2A and A2B carry `gate_bluff`, A3A and A3B carry `gate_authority`, and each pair also carries `gate_passed` | 6 lines, all 6 correct, each pair carries `gate_passed` |
| The never contain list is present | section 7 carries the four numbered items and the retired name sentence | all four items present verbatim |
| No em dash, en dash or long dash | the script greps for U+2013, U+2014, U+2015 and U+2212 | 0 occurrences of any of the four |
| No retired name | the script reads the two retired names out of `knowledge/NAMES-BIBLE.md` section 2 and greps this file for them | 0 occurrences of either |
| Line counts inside the card | 12 Morgan lines, 10 Nye lines, 6 alternate lines, 4 hint lines | 12, 10, 6 and 4, as the card asks |

What is not measured, stated plainly: whether the lines are good is a reading judgement, not a check, and the one that
matters is whether a player who has just been stopped in the rain believes Morgan and whether a player holding a pink
slip believes Nye. The gate's register is short because his sentences are short; the office's is exact because the
ledger is. Neither man explains the plot, and neither says anything the other could not hear.
