# A league play-off: groups, then a final (the Liga FUTVE, 0.2.5)

A country whose season is two short tournaments (the Liga FUTVE's Apertura and Clausura) decides
each one with two groups of four and a final. FL26 has every piece of that except the last step:
its own play-off fills a knockout, and a continental cup of ours fills a group stage in August, but
nothing fills a group stage in the middle of a season and sends only the winners on to a final.
This page is the format, the world file options, the tools that build and test it, and what is
still open.

## The format

- Eight clubs of a split phase (the regular phase's 1st to 8th) are dealt into two groups:
  **A = 1, 4, 5, 8** and **B = 2, 3, 6, 7**. No draw: the world file writes them in that order.
- Six matchdays, home and away, on the days the world file gives (`gdays=`).
- The winner of each group goes to the final, one match, on `days=`; the better placed club of the
  regular phase is first in the list (at home in the match record).
- The final is the cup's own knockout: a normal cup's row (the FA Cup's, one match a round) cut to
  two clubs, so the game sees a cup final and names it "Final"; its one date comes from the Belgium
  Super Cup's calendar (`kolike=`).
- The match screens and the Competition Info item name the final "Final" (`FINAL_TEXT`, a text the
  game's table does not use, answered by the DLL's phase-name hook).

The cup is filled the day after the phase ends (`ccup_fill_ahead`, the same trigger the straight
knockout has used since 0.2.0) and the groups are started and registered the way a qualifying round
is (see below). `adv=1` is what makes the final: without it the old progression sends the two first
of each group to a knockout of four.

## The world file

One line, in `modules\fl26world.txt`:

```
ccup 259 ko=261 groups=2 entry=191:1,191:4,191:5,191:8,191:2,191:3,191:6,191:7 ^
     fill=3 national=1 days=15 gdays=3,5,7,9,11,13 adv=1 kolike=128 name=Liga FUTVE Apertura Playoffs
```

- `entry=` is the draw: the first `4 x groups` entries are group A's, the next group B's, in order.
- `gdays=` switches the league play-off on: own group days, groups in entry order, no draw.
- `adv=1`: only the group winners advance (only 1 is supported).
- `kolike=<shipped regulation>`: the shipped cup whose calendar dates the final (the Belgium Super
  Cup's: one record). The knockout's *row* comes from `mkccup.py`'s own `kolike` (the FA Cup's,
  cut to `koclubs=2`), so the game treats it as a cup final; the two need not be the same cup.
- `days=` dates the knockout: one day for a final; several for the four-club knockout of the first
  test.
- `fill=`/`national=` are the usual options.

The loader parses the three new fields into `fl26_swiss_ccup_gdays`, `fl26_swiss_ccup_adv` and
`fl26_swiss_ccup_kolike`, called after `fl26_swiss_ccup` like the other per-cup options. An older
DLL without them logs that and keeps the cup on the old path; `gdays=` is also taken out of the
line before `days=` is read, because the plain `days=` pattern would find it inside `gdays=`.
The fields live in `ccup_t` (`adv`, `gnd`/`gdays`, `kolike`) and nothing else in the DLL changes
for a cup that does not set `gdays=`.

## How the DLL runs it

**Fill.** `ccup_fill_one` takes the field from the phase's table as any cup does (`ccup_club`: the
kept table, the live table or the table counted from the matches). With `gnd` it deals the field
into the groups in order (`ccup_league_groups`, after the game's own draw, so the competition is
marked drawn) and then does what `lpre_fill` and `q_fill` do for a competition that is not in the
season's calendar:

1. `start_stage(started, reg)` -- push the phase onto the caller's list of started stages
   (0x141590420);
2. `register_all(reg)` of the master, whose parent field names the groups;
3. `ccup_season_fix`;
4. count the match records under the master and under the group rows; if both are 0, the old
   `register_all` of the group rows is tried as well;
5. log `"groups filled, started and registered ... X match record(s) under the phase, Y under its
   groups"`.

That order is the fix for the test of 28 October, where the groups were filled and drawn but only
handed to `register_all`: no stage was started and no match was ever made. The same test dated the
groups on the Libertadores' calendar (days 327...47) while the career was on day 2, so two of the
six days were already past; `gdays=` removes that too. Whether those two were the only reasons is
what the first in-game test answers.

**Dates.** `ccup_dates` maps the six Libertadores group records to `gdays` (and logs them), and
`ccup_fill_days` knows the first group day for its fill window. The knockout with `kolike` borrows
the shipped cup's calendar (`ccup_borrowed_dates`, the same helper as a single-match league cup's)
and maps its records by round to `days`; with a one-day list every record falls on that day.

**Progression.** `ccup_progress` waits for every group (the bitmask of the progression calls). A
save loaded between two group days loses the earlier calls, so for a `gnd` cup it also accepts the
match records: 12 a group, all played. Then, with `adv`, it reads the winner (row 0) of each group,
orders them by the entry's regular position (`ccup_league_final`, lower first) and fills the
knockout with them; the same club twice is put in once and the final is refused. Without `adv` the
old bracket of two a group stands. When the final's progression arrives, `ccup_final_note` logs the
champion once a season.

## In Mod Studio: `"playoff_format": "groups"`

A recipe asks for this play-off on an Apertura/Clausura league; the Build makes all of it, the
finals included, and nothing of the tools below is needed:

```json
"apertura": {"playoff": 8, "playoff_format": "groups",
             "names": {"final_apertura": "Final del Apertura", "final_clausura": "Final del Clausura"},
             "logos": {"final_apertura": "C:/logos/final-apertura.png"}}
```

- `playoff_format`: `"knockout"` (the default: two legs a round, a one-match final) or `"groups"`,
  which needs `"playoff": 8`. Mod Studio's league window has it next to the playoff size.
- `names` and `logos`: `playoff_apertura`, `playoff_clausura`, `final_apertura`,
  `final_clausura`, any of them. The defaults are "<league> Apertura Playoffs" and "<league>
  Apertura Final"; a play-off's picture falls back to `playoff_logo`, a final's to the drawn
  emblem. The finals' keys mean something with `"groups"` only. The window has fields for the four
  names and the finals' two pictures; the playoffs keep the one "Playoffs" picture of the cup logos,
  and a hand-written recipe's own `logos.playoff_*` are kept when the window saves.
- `plan()` refuses another format, groups of other than 8 clubs and keys it does not know;
  `recipe_from_plan` gives the three keys back. Without them the plan, and the world, are the
  ones of before (the regress018 fingerprints of every recipe are unchanged).

What the Build does (`tools/leaguebuilder.py`):

- `playoff_cups` plans each play-off on the seven days a knockout of the league would have
  (`playoff_days`): the first six are `gdays=`, the last the final's `days=`. The entries are the
  group order above (`PLAYOFF_GROUP_ORDER`), `groups` 2, `adv=1`, and `kolike` the Belgium Super
  Cup (`PLAYOFF_FINAL_DATES`).
- `continental` passes `mkccup.py` the `koclubs` 2 and the FA Cup's regulation as the knockout's
  row (`PLAYOFF_FINAL_SHAPE`); `ccup_options` writes `gdays=`, `adv=1` and `kolike=` into the line.
- `playoff_finals` makes each final a **competition of its own**, as the Liga FUTVE's were made by
  `futve_finals.py`: a copy of the play-off's competition row with a new id and the code
  `FL_<rid>_AFI` / `FL_<rid>_CFI`, the knockout regulation moved to it and named after it, and two
  entry rows (placeholders: the DLL writes the group winners when it fills the final). The game then
  counts the final's winner as that competition's champion -- the title in the Palmarés carries the
  final's name and emblem, not the play-off's. The id is one the game creates at the season's start
  (`CREATION_IDS`, 130 and up, free): a knockout regulation moved to an id the season builder has no
  case for is never created. It is noted in the plan's `cup_ids` (`final:<code>`) and kept by the
  next Build, like every cup's id, since a career holds it.
- `cup_emblems` draws the finals' emblems (or puts their pictures) like any cup's.

```
ccup 257 ko=258 groups=2 entry=191:1,191:4,191:5,191:8,191:2,191:3,191:6,191:7 fill=3 national=1 days=28 gdays=5,8,11,14,18,25 adv=1 kolike=128 name=Apertura Groups League Apertura Playoffs
```

(`tools/testdata/regress018/apertura_groups.json`: the play-offs are competitions 143/144, their
finals 133/134, regulations 258 and 260. With a final in the world, `continental` gives the other
cups ids the game does not create first: those are few -- 130 to 175, about fifteen -- and every
final needs one.)

### The grand final: `"grand_final"`

```json
"apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": true,
             "names": {"grand_final": "Final del FUTVE"}, "logos": {"grand_final": "C:/logos/futve.png"}}
```

- `true` or `"two_legs"` (two legs), `"single"` (one match); `false`, the default, none. Only with
  `"playoff_format": "groups"`. Mod Studio's league window: Grand final, with its name and logo.
- After the Clausura's final (`playoff_days`, three days on), the two finals' winners. Its winner is
  the **league's champion**: its regulation carries the league's name in every slot, so its title in
  the Palmarés reads as the league's; fl26swiss.dll takes it as the champion for the super cup and,
  for a January-December league, the continental places. A club that won both finals is champion with
  no match (`ff_auto_champion`, the title written by `honours_fix`).
- The accumulated table's leader gets **no title**: the game's title of the split league is taken out
  of the user's trophy cabinet and season block (until fase 6 only for a January-December league).
- The Build (`playoff_cups`, `continental`, `grand_finals`): a straight knockout of two clubs on the
  FA Cup's row (`mkccup` `like`), dated by the Belgium Super Cup (`kolike=`), on a competition id the
  game creates at the season's start (`"case"`: `CREATION_IDS`), pinned by the next Build like every
  cup's. Its entry rows go (a placeholder pair counted as the title won before the final, 29.10.); the
  away goals rule is off; two legs set the knockout's legs mode to 2 (`KO_LEGS_*`). The world line:

```
ccup 261 ko=261 groups=0 entry=191:1,192:1 fill=0 national=1 days=166,169 kolike=128 src=258,260 cid=134 name=Final de la Liga
```

- The DLL: `src=` makes the knockout the final of the two play-offs' knockouts (filled when both are
  over, `ccup_fill_finals`), `cid=` names its competition (`fl26_swiss_title_league`). **Any number
  of such leagues in one world**: each split league whose phases feed a final of two cups is a title
  league (`grand_final_of`, `is_title_league`), with its own champion (`league_champion_kept`) and
  honours (`honours_fix_one`). Until fase 6 the DLL knew one: the last final of the world was every
  league's. `tools/native/test_grand_final.c` checks it offline.

### The trophy ceremony: `"ceremony"`

The game ends a match in the trophy ceremony when its competition's regulation is one of its big
finals: the exe's regulation -> tournament map (0x141e53910, `cx` = regulation | stage << 10) has
330 built-in pairs and answers 217 ("no tournament") for anything else, every regulation of ours.
`"ceremony": true` on a league gives its finals a tournament of the base game no world uses, 30 (the
shipped Copa Sudamericana's final, regulation 13; FL26's Sudamericana is a cup of its own):

- the Build (`tmap_lines`): `tmap <reg> 30` for the league's national cup and super cup, its
  play-offs' finals and its grand final, `noleg0` for a two-legged one; refused for a league with
  none of those, 16 at most in a world (`CEREMONY_MAX`, the DLL's `TMAP_MAX`);
- the DLL (`fl26_swiss_tmap`, `tmap_handler`): a chain of compares in front of the exe's function
  answers the world's regulations; with `noleg0`, the user's match on the first leg keeps 217. The
  hook goes in only for a world with `tmap` lines -- until fase 6 it answered 255, 256 and 261-263
  in every world;
- Mod Studio's league window: Trophy ceremony.

A world built before needs its `tmap` lines to keep the ceremony with this DLL: the Liga FUTVE's
`tmap 255 30`, `tmap 256 30`, `tmap 261 30`, `tmap 262 30`, `tmap 263 30 noleg0`.
`tools/native/test_ceremony.c` checks the map offline.

### The finals' cinematics: `"cinematics"`

The cinematics packs (`SiderAddons\content\cinematics`) hold a folder per competition -- `LIB`,
`UEFA Champions League F`, `ESPCF` ...: the entrance, the stadium dressing, the trophy ceremony's
animations and its cup -- and the packs' shared module (`common\cinematics.lua`) picks one by the
game's tournament id, which no competition of ours has. `"cinematics"` on a league picks one for
each of its finals:

```json
"cinematics": {"cup": "ESPCF", "super_cup": "UEFA Super Cup", "final_apertura": "LIB",
               "final_clausura": "LIB", "grand_final": "UEFA Champions League F"}
```

- the Build (`cine_lines`): `cine <reg> final <folder>` for the national cup (its final match),
  `cine <reg> all <folder>` for the super cup, the play-offs' finals and the grand final (each a
  final); a folder the game's `content\cinematics` has not got, or a final the league has not got, is
  said in the log;
- `sider\experimental\fl26cine.lua`: for those matches every file comes from that folder first;
  one it has not got goes on to the next module (sider takes the first module whose file exists), so
  `fl26cine` loads **before** `common\cinematics.lua`: Install the modules (`ensure_modules`,
  `cine_place`) puts its line there, out of Mod Studio's block (`group_ours` leaves it);
- Mod Studio's league window: Cinematics, a list per final of the folders the game has
  (`cine_folders`), "(the game's)" for none.

The cup lifted is the folder's own (a trophy chosen apart was tried and left: Felix, 01.11.). Tested
in the game on 01.11.: the Final del Apertura (261) with `LIB`, the Libertadores final's scenes, and
the ceremony. The Liga FUTVE's hand-made patch of `common\cinematics.lua` (`futve_cinematics.py`) is
not needed for these lines; it stays for the frozen phases.

## Building the world without Mod Studio

`tools/futve_world.py` builds the two test worlds from a real one, without touching the game:

```
python tools/futve_world.py --game "G:\Games\SP Football Life 2026"
```

- It finds the Apertura cup by its world line and its competition and takes the ids the Build gave
  it (competition 134, regulation 259; the knockout is the next free regulation, 261). The group
  rows are `reg + 1024` and `reg + 2048` (1283, 2307), as the game's rule for a group cup.
- It removes the competition row, the regulation rows and the entry rows of that one competition
  and hands the rest of the three tables to `mkccup.py`, which adds a group master, its two
  replicas and the knockout (four clubs for phase 1; for the final, the FA Cup's row cut to two
  clubs, dated by the Belgium Super Cup's one record). Every other competition, regulation and entry
  comes back untouched; the Clausura cup is never named.
- It writes `out/futve/world-phase1` and `out/futve/world-phase2`, each with
  `common\etc\pesdb\{Competition,CompetitionRegulation,CompetitionEntry}.bin` and the world file
  with the Apertura line replaced, in the source's line endings.
- `--dry` prints the ids and the line only; `--phase 1|2` builds one.

After a Mod Studio Build the bins and `fl26world.txt` are regenerated: run the script again (and
`futve_fixture.py --make`, see below). The ids are read from the world each time; only the cup's
name has to survive the Build.

`mkccup.py`'s `--cup` spec grew two optional fields for this: `koclubs` (the knockout's club count,
default `2 x groups`) and `kolike` (a shipped regulation whose row the knockout copies -- a normal
cup's, so a two-club field is a final the game names). Both are group-cup only; the existing cups
are unchanged.

## The fixture: Táchira 99

The in-game tests are careers with the world's Deportivo Táchira (team 71606) and every one of its
players' 25 stats at 99, so a test is quick and predictable.

```
python tools/futve_fixture.py --make  [--world <pesdb>] [--from <Player.bin>]
python tools/futve_fixture.py --check <Player.bin> [--assignments <PlayerAssignment.bin>]
```

`--make` reads the world's `Player.bin` and `PlayerAssignment.bin`, sets the 25 ability fields
(`playeredit.ABILITIES`) of the 30 players assigned to the team to 99, and writes
`out/futve/fixtures/Player.bin` and a manifest (sha256 of the source and the fixture, the team, the
player ids, the 750 values checked). It refuses to write if any other record would change. `--check`
is what the sandbox runs before and after installing it. Names, ids, positions, form and skills are
left alone; a world with another squad or another team is `--team`/`--world`.

There is no Táchira-99 `Player.bin` in the game today (the installed one runs 40-83 in those
stats), so the fixture is generated from whatever `Player.bin` the world has. If you have your own
copy, `--from` verifies and uses it.

## The competitions' logos

The Apertura and Clausura play-offs and the three finals take these pictures:

| competition | picture |
|---|---|
| 134 Liga FUTVE Apertura Playoffs | `PLAYOFF_APERTURA.png` |
| 135 Liga FUTVE Clausura Playoffs | `PLAYOFF_CLAUSURA.png` |
| 142 Final del Apertura | `FINAL_APERTURA.png` |
| 129 Final del Clausura | `FINAL_CLAUSURA.png` |
| 175 Gran Final del FUTVE | `FINAL_FUTVE.png` |

```
python tools/futve_logo.py --make
python tools/futve_logo.py --check
python tools/futve_logo.py --install --game "G:\Games\SP Football Life 2026"
python tools/futve_logo.py --restore out/futve/logos/backup-<date> --game "G:\Games\SP Football Life 2026"
```

`--make` writes the six variants (256 and 512 px) of each competition under `out/futve/logos/world`,
made the way a Build's league logo is (`lbassets.league_logo`: the picture fitted into a transparent
square, never stretched, in colour in every variant), and a `files.json` with the plan's competitions
and files. The pictures are in `G:\Downloads` (or `--source`/`FL26_LOGOS`). The in-game sandbox
installs exactly the list in `files.json` (the two play-offs and the three finals, 30 files) and
restores the game's emblems at the end, so it never puts a logo on a competition that is not in the
plan. `--install` writes the staged set into the live world and backs up what it replaces under
`out/futve/logos/backup-<date>/` (the game closed) for after a Build, as for the world file;
`--restore` puts a backup back.

The finals' competitions take ids **142/143/144**, the Mod Studio's next three free byte competition
ids (`leaguebuilder.free_comp_ids`: the pool starts at 130 and skips the world's used ones -- 130-135
the Liga FUTVE, 137-141 Scotland/KSA -- and the UEFA Conference League's reserved 136). 136 is why a
first version put a logo on a UEFA competition; 10342 is a team id, not a competition id.

## The sandbox of the in-game tests

```
python tools/futve_test.py --phase 1 --game "G:\Games\SP Football Life 2026"
python tools/futve_test.py --phase 2 --game "G:\Games\SP Football Life 2026"
python tools/futve_test.py --phase 3 --game "G:\Games\SP Football Life 2026"
python tools/futve_test.py --restore out/futve/tests/<date>
python tools/futve_test.py --self-test
```

One process per test, run by you in your terminal (it writes to the game and to the save folder,
outside the agent's sandbox). It:

1. refuses to start while the game is open (a process name or a locked file);
2. backs up, under `out/futve/tests/<date>/backup/` with a `manifest.json` of sizes, mtimes and
   sha256: the files it installs (`fl26swiss.dll`, `fl26swiss.lua`, `fl26world.txt` in both
   places, the three `Competition*.bin`, the fixture's `Player.bin`, the game's own
   `cinematics.lua`/`cinematicsB.lua`, and the competition logos the plan stages -- the two
   play-offs and the three finals, 30 files), the game's `*.log`, `*.cache`, `sider.ini`
   and `ReShade.ini`/`ReShade.log`, and the **whole save folder**
   (`...\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`, detected under `Documents` and
   `OneDrive\Documents`, or `--save`);
3. installs the DLL, the loader, the phase's world and the fixture, checks every hash and runs the
   fixture check on the installed `Player.bin`;
4. prints the checklist and waits. `FIN` + Enter: requires the game closed, copies the evidence
   (the post-test logs, the new screenshots, the manifest, a report) to `evidence/`, then restores
   everything -- files, save folder (the careers of the test and `fl26swiss-state.bin` are removed),
   logs, caches -- with the original mtimes, and verifies it against the manifest. `ABORTAR`
   restores at once; Ctrl+C restores nothing and prints the `--restore` command;
5. reports any file changed under the game folder that the sandbox did not expect, so the managed
   set can grow.

`--self-test` runs the whole round trip on a fake game/save/artifacts tree under `out/futve/tmp`
(a real Player.bin/PlayerAssignment.bin pair, a simulated career save, appended logs, a new cache)
and requires the tree to come back byte for byte.

The two cinematics files are the game's own `SiderAddons\modules\common\cinematics.lua` (the
entrance folder per tournament id) and `cinematicsB.lua` (the Final stadium scenes), with one
mapping added by `tools/futve_cinematics.py` (the sandbox runs it before a test, and `--check`
verifies it): the final competitions' regulations **261** (the Apertura final) and **262** (the
Clausura final), when the match is the final (`ctx.match_info == 53`), keep the UEFA Europa League
final's entrance (`UEFA Europa League F`), and **263** (the Final del FUTVE) the UEFA Champions
League final's (`UEFA Champions League F`); their trophy entry (`entry`, the `trophy_rewrite`) is
**16**, the UEL/UCL's, whose trophy and celebration are in the user's content/cinematics folders
(1/10/42/46 give the Club World Cup, Libertadores, the Copa America and the CAF trophy); all three take the generic
`Final\st001` scene from cinematicsB. The game's files are put back at the end, like everything
else.

## The two tests

**Phase 3 (the finals as competitions of their own).** `tools/futve_finals.py` builds
`out/futve/world-finals`: the Apertura and Clausura play-offs keep their groups (134/135, masters
259/260, rows 1283/1284/2307/2308), and the finals are separate competitions -- 142 "Final del
Apertura" (regulation 261), 129 "Final del Clausura" (262) and 175 "Final del FUTVE" (263), 2 clubs
each, ids the exe's builder 1 include list gives a case: 142 and 175 free, 129 replaces the base's own competition 129. The earlier 142/143/144 failed because 143/144 have no case in that list.
The three finals' entry rows are placeholders: the DLL rewrites them. The Final del FUTVE's line
carries `src=261,262`: the DLL reads the two finals' champions, plays the match when they differ and
leaves it unplayed -- logging the title -- when they are the same; its `fill=0` makes the DLL try it
every tick until both champions are known. The phase 3 sandbox installs that world, the 30 logos of
134/135/142/143/144, the two cinematics and the join module, and the full-season checklist runs the
Apertura final (day 15), the Clausura groups (145-160) and final (164), and the Final del FUTVE
(167) twice: the same champion (no match, the title direct) and a different champion (the match
played). At the season's close the palmarés should carry the finals' titles.

The finals' ids (142, 129, 175) are in the exe's builder 1 include list, so the season builder takes
them at creation like the shipped cups and their `enter_season` runs; no extra module patch is
needed. (The earlier attempt with 142/143/144 failed because 143/144 have no case in that list; the
`futve_join.py` copy, which added them to the calendar-year builder, is obsolete and no longer
installed by the sandbox.)

**Phase 1 (groups).** The Apertura cup has two groups and a four-club knockout; the groups are
dated 3, 5, 7, 9, 11, 13 and the knockout after them. A career with Táchira simulated to day 2, then
to the group days: the calendar must show the six matchdays, the Competition Info -> the cup must
show the two group tables with A = 1, 4, 5, 8 and B = 2, 3, 6, 7, and `sider.log` must have
`started and registered ... N match record(s)` with N > 0. If no match appears, stop the plan here.

**Phase 2 (the final).** The same groups, the knockout is the final (`adv=1`, `kolike=128`,
`days=15`): after the last group day the two winners are put in the final, the better regular
position first, and the match is played on day 15. The log names them (`final: X (regular position
p) v Y (position q)`) and the champion. The calendar and the match screens must call it "Final"
(the first test of 28 October showed the competition's name instead), the entrance must be the UEFA
Europa League final's (the Apertura final is regulation 261) and the pre-match scene the Final one
(`cinematicsB`); the Clausura follows and must be untouched. Check the club's Palmarés after the
final and, if you can, after the season's close: the champion is the competition's winner (the DLL
reads it), but the club's honours screen is the game's own bookkeeping, see below.

Both tests are about the Apertura only: the Clausura cup keeps its straight knockout of eight, and
the Gran Final, the continental places and the second season are later phases.

## What is still open

- **Mid-season group stages.** The 28 October test did not prove the engine refuses them: it dated
  the groups in the past and did not start the stage. Phase 1 is the test that decides; if the
  matches still do not appear, the format stops here.
- **The calendar.** The Apertura ends on day 2 and the Clausura starts on day 16: six group
  matchdays and a final in 13 days is a match every two days, and the finalists play the first
  Clausura round a day later. The compressed window is the chosen trade-off; the fallback is the
  final on day 14 or the 3-day rhythm of the old play-off, a data change only.
- **The final's ground.** The better placed club is first in the match record; the test of 28
  October had Táchira at home in the final. Whether a different row shape would change the venue is
  a data question, not a code one.
- **The finals as competitions of their own** are done (`futve_finals.py` for the Liga FUTVE,
  `playoff_finals` in the Build, above), and their titles are in the club's Palmarés
  ([palmares.md](palmares.md)). The Final del FUTVE between the two champions is a block of its own.
- **Competition Info.** The cup's group pages are the pages of a group competition; a crash there
  (as B205 once had) is checked in each test.
- **Saves.** A save loaded between two group days is covered by the match-count fallback; a save
  loaded at other points, the July teardown and the second season are phase 6.
- **A Build** overwrites the bins, `fl26world.txt`, `Player.bin` and the emblems: rerun
  `futve_world.py`, `futve_fixture.py --make` and `futve_logo.py --install`, then install with the
  sandbox.

## Tests without the game

```
python tools/test_playoff_groups.py <pesdb>  # the recipe keys, the Build's cups and finals, the league window
python tools/test_grand_final_build.py <pesdb>  # the grand final: recipe key, Build, league window
python tools/test_grand_final.py       # the DLL's title leagues (any number), native
python tools/test_ceremony_build.py <pesdb>  # the trophy ceremony: recipe key, tmap lines, league window
python tools/test_ceremony.py          # the DLL's tournament map, native
python tools/test_fl26cine.py          # the cinematics module in Lua (lupa)
python tools/test_futve_playoff.py     # the pure parts (groups, order of the final), native
python tools/test_futve_world.py       # both staging worlds against the real world; skip without one
python tools/test_futve_fixture.py     # the fixture; skip without a world
python tools/futve_test.py --self-test # the sandbox round trip on a fake tree
```

The native runner needs zig (`ZIG`, `PATH`, `D:/dev/tools/zig-*/zig.exe` or the branch's
`out/tools/py/ziglang/zig.exe`).
