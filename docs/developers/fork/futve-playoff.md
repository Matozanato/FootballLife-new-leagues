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
  `futve_finals.py` (phase 3, retired in fase 6): a copy of the play-off's competition row with a
  new id and the code `FL_<rid>_AFI` / `FL_<rid>_CFI`, the knockout regulation moved to it and
  named after it, and two
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
not needed for these lines; it was retired with the hand-made worlds.

### January to December: `"season": "calendar"` with `"apertura"`

The Liga FUTVE of phase 4 in Mod Studio: the Apertura from February to May, its play-off and final,
the Clausura from late July (after the summer tournaments) to October, its play-off and final, the
grand final before the Club World Cup, the cup's rounds through the year, the super cup at the end of
January. For now with playoffs of groups and a grand final, and one such league in a world: the DLL
runs the season of one title league (`futve_cal`), the one a grand final decides.

- **The days** (`cal_layout`): every piece CAL_GAP (2) days from the game's busy days -- the national
  teams' windows (88 91 94, 153 156 159, 182..203, 244 247, 279 282, 314 317), the Libertadores' (34
  41, 62 ... 139, 163 ... 331), the Club World Cup's (348..352) and, with `conmebol: modern`, its
  rounds (6 13 18 25 40 49 55 144 161) -- and CAL_SPACE (3) from each other, the rounds on Saturdays
  first, the play-offs and finals the first free days after them. 16 clubs at most (17 rounds do not
  fit February to May). `calendar_days` gives any piece by hand (the Liga FUTVE's final on day 157,
  a day from the June window, by Felix's choice), the rest laid around it.
- **The world file**: `season <region> 1`, `splitdays` of the Apertura and the Clausura, the
  play-offs' `fill=`/`gdays=`/`days=` and the grand final's `days=` from the layout, the cup's and the
  super cup's `dates ... days=`; the league line's `cup=` puts the cup in the New Year season and
  names the cup whose winner plays the super cup.
- **fl26joindll.lua**: a January-December split's phases go with their league -- closed at New
  Year, let in again with it on day 41 -- and out of the July teardown (the Apertura's results stay on
  the calendar all year), as phase 4's copy did.
- **fl26swiss.dll**: the January-December code of phase 4 (the Apertura reopened for its new season,
  the Clausura on the calendar from February, the finals counted by the calendar year, the cup filled
  at New Year) for the title league; the cup is its own (`futve_copa_reg`: its super cup's), no
  longer a fixed 255.
- Mod Studio's league window: February to December with Apertura and Clausura, and Days by hand
  (`final_apertura=157; grand_final=342,345`).

`tools/testdata/regress018/apertura_calendar.json`; `tools/test_calsplit.py`.

### The continental places in the order of the finals

`"places_order": "finals"` (with `season: calendar`, `apertura` and `conmebol: modern`; the default
`"table"`): the league's eight continental places go as the real Liga FUTVE gives them, not by the
accumulated table --

| Place | Club |
|---|---|
| 1 | the champion (the grand final's winner, or the club that won both finals) |
| 2 | the best of the table besides the champion and the runner-up |
| 3 | the runner-up (the grand final's loser; the table's next when there is none) |
| 4 | the table's next |
| 5, 6 | the Apertura's and the Clausura's final losers (the table's next when already placed) |
| 7, 8 | the table's next two |

The league's `europe` positions keep their competitions (1-4 the Libertadores, 5-8 the
Sudamericana, as the modern CONMEBOL gives them); only the club of each position changes.

- **The world file**: `contorder <reg> finals` (`leaguebuilder.contorder_lines`).
- **fl26swiss.dll**: `fl26_swiss_contorder` takes the league; `futve_cont_club` (phase 5's order,
  until now always on for the title league) answers only for it. A world without the line keeps the
  table's order -- a phase 5 world that wants its order needs the line with the new DLL.
- Mod Studio's league window: continental places in the order of the finals.

`tools/test_places_order.py`; `tools/native/test_grand_final.c`.

### Nobody abroad in the first season

`"first_season_abroad": false` (with `season: calendar` and `apertura`; the default `true`): in a new
career's first season the league has no final table yet (the real Liga FUTVE's first year), so it
sends no club abroad. From its second season, when the DLL has kept its table, its places go as
usual. Until now this was always on for the title league, with a list by hand of substitutes.

- **Its Libertadores places** (`cont_build`) stay with the pool clubs; **its cup entries** (a
  Sudamericana of ours) send nobody.
- **Its pre-round slots** (`lpre`, the qualifying rounds and the Sudamericana's first stage) go to the
  other leagues of that round in turn, in the order of the round's entries, each its next club after
  the last position it sends anywhere abroad (`abroad_last`: every pre-round's, every cup's entry,
  every access place) -- a club with no continental place, not already in this round or another
  (`first_sub`). Phase 5's list by hand (Colombia 16-20, Chile 16, Argentina 19-24) is gone: with
  phase 5's world the same leagues and the same first positions, taken in turn.
- **The world file**: `firstabroad <reg> 0` (`leaguebuilder.firstabroad_lines`).
- **fl26swiss.dll**: `fl26_swiss_firstabroad` takes the league; `first_noabroad` gates the three
  places. A world without the line: the first season by squad strength, as any league's -- a phase 5
  world that wants it needs the line with the new DLL.
- Mod Studio's league window: nobody abroad in the first season.

`tools/test_first_season_build.py`; `tools/test_first_season.py` (`tools/native/test_first_season.c`).

### The modern CONMEBOL alongside

With `conmebol: modern` a club of the January-December league also plays the Libertadores' phases 1
and 2, the Sudamericana's first stage and play-off and the Recopa. `cal_layout` lays the league
CAL_GAP from their days (`modern_busy`), the shipped ones or `conmebol_days` by hand -- the Liga
FUTVE's `{"sudamericana_playoff": [144, 161]}`: the shipped 146 153 has its second leg on the June
window's 153. Until now the layout kept clear of 144 and 161 whatever the play-off's days were.

- **Days by hand** (`conmebol_days`, `conmebol_days()`): any of `libertadores_1`, `libertadores_2`,
  `sudamericana_first`, `sudamericana_playoff`; each between its fill and the next round
  (`CONMEBOL_DAYS`). The Build writes them in the rounds' `lpre ... days=`.
- **A note** (`modern_clashes`, the plan's notes, in the Build log): a day of the league by hand
  (`calendar_days`) under CAL_GAP from one of them. A note, not a refusal: two clubs' clash only
  if one plays both.
- **The ids**: the finals' (`CREATION_IDS`, `spare_case`) and the modern helpers' (`helper_ids`)
  come from the same Build and are each their own, pinned by the next Build.
- Mod Studio's South American places window: Days by hand (`sudamericana_playoff=144,161`).

`tools/test_conmebol_days.py`.

### The Liga FUTVE recipe

`tools/testdata/regress018/liga_futve.json` is phase 5's world in recipe keys alone, with no tool
of the `futve_*` set:

| Key | Value |
|---|---|
| `season` | `calendar` |
| `apertura` | 8 clubs, `groups`, `grand_final: two_legs`, the names of phase 5 |
| `calendar_days` | every piece on phase 5's days (the Apertura's final on 157, the grand final 342 345, the cup 69 ... 286, the super cup 30) |
| `ceremony` | `true` |
| `cinematics` | `{"final_apertura": "LIB"}` |
| `places_order` | `finals` |
| `first_season_abroad` | `false` |
| `europe` | 1-2 Libertadores groups, 3 phase 2, 4 phase 1, 5-8 the Sudamericana's first stage |
| `conmebol`, `conmebol_days` | `modern`, `{"sudamericana_playoff": [144, 161]}` |
| `game_europe`, `conmebol_associations` | the places of phase 5 (Brazil, Argentina, Chile, Colombia; Bolivia, Uruguay, Ecuador, Paraguay, Peru) |

The automatic layout lays the same pieces on other days (Saturdays first, the play-off groups and
the cup on other days); the days by hand are the ones played three seasons in the game.

`tools/test_liga_futve.py` builds it with phase 5's ids pinned (`tools/testdata/futve/phase5-ids.json`)
and finds every Liga FUTVE and South American line of phase 5's world file
(`tools/testdata/futve/phase5-world.txt`) but for:

- `contorder 11 finals` and `firstabroad 11 0`, phase 5's behaviour now an option;
- the league line: no `scupcup=255` (the league's `cup=255` names the same cup) and the cup's entry
  options every Build writes since 0.2.4;
- the Final del Clausura on competition 147: phase 5 took 129, the base's Danish cup
  (DENMARK_CUP), which a Build keeps.

**A world that played phase 5** (Felix's `_FL26MyWorld`): its `leaguebuilder-plan.json` is the
Build of 19.10., before the FUTVE tools, and knows none of the ids they gave. Before the first Build
with these keys, its `cup_ids` take `phase5-ids.json`'s, so every competition and regulation keeps
its id; a career keeps its titles (the trophy cabinet holds regulations). The Final del Clausura's
competition moves to 147: a career started before keeps playing it, its title is regulation 262's.

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
left alone; a world with another squad or another team is `--team`/`--world`. After a Build that
changes the squads, make it again.

## The sandbox of the in-game tests

```
python tools/futve_test.py --world "<a Build's livecpk\<world> folder>" --game "G:\Games\SP Football Life 2026"
python tools/futve_test.py --restore out/futve/tests/<date>
python tools/futve_test.py --self-test
```

The world is one Mod Studio built: a Build into a copy of the game, or the world's own folder. One
process per test, run by you in your terminal (it writes to the game and to the save folder,
outside the agent's sandbox). It:

1. refuses to start while the game is open (a process name or a locked file);
2. backs up, under `out/futve/tests/<date>/backup/` with a `manifest.json` of sizes, mtimes and
   sha256: the files it installs -- the world's `fl26world.txt` (in `livecpk\<world>` and in
   `modules`), its three `Competition*.bin` and its competition emblems, the fixture's `Player.bin`
   (`--no-fixture`: the world's own), the repo's `fl26swiss.dll` (or `--dll`), `fl26swiss.lua`,
   `fl26joindll.lua` and, with `cine` lines, `fl26cine.lua` (a `sider.ini` that does not load it is
   a warning: Install the modules in Mod Studio) -- the game's `*.log`, `*.cache`, `sider.ini` and
   `ReShade.ini`/`ReShade.log`, and the **whole save folder**
   (`...\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`, detected under `Documents` and
   `OneDrive\Documents`, or `--save`);
3. installs them and the world's sandbox careers (`out/futve/careers-<world>`, or `--careers`),
   checks every hash and runs the fixture check on the installed `Player.bin`;
4. prints the checklist of the Liga FUTVE recipe and waits. `FIN` + Enter: requires the game
   closed, copies the evidence (the post-test logs, the new screenshots, the manifest, a report) to
   `evidence/`, keeps the careers the session played in the store, then restores everything --
   files, save folder, logs, caches -- with the original mtimes, and verifies it against the
   manifest. `ABORTAR` restores at once; Ctrl+C restores nothing and prints the `--restore` command;
5. reports any file changed under the game folder that the sandbox did not expect, so the managed
   set can grow.

`--self-test` runs the whole round trip on a fake game/save/world tree under `out/futve/tmp` (a
real Player.bin/PlayerAssignment.bin pair, a built world with a `cine` line, a simulated career
save, appended logs, a new cache) and requires the tree to come back byte for byte.

## The hand-made worlds of phases 1-5 (retired)

Phases 1-5 were tested on worlds made by hand on top of a Build: `futve_world.py` (the play-off
groups), `futve_finals.py` (the finals as competitions of their own, on 142/129/175),
`futve_calendar.py` (January to December), `futve_conmebol.py` (the modern CONMEBOL competitions),
`futve_logo.py` (the play-offs' and finals' emblems), `futve_cinematics.py` (a patched
`common\cinematics.lua`) and `futve_join.py` (a patched `fl26joindll.lua`, obsolete since phase 3).
A Build makes all of it now from the recipe keys above, and the Liga FUTVE recipe reproduces phase
5's world, so fase 6 took them out with their tests (`test_futve_world.py`, `test_futve_finals.py`).
They are in the history of the `v025-futve` branch. What phases 1-5 found is in the sections above;
the decisions of the in-game tests (the days, the 157, the ceremony, the order of the places) went
into the recipe.

## Tests without the game

```
python tools/test_playoff_groups.py <pesdb>  # the recipe keys, the Build's cups and finals, the league window
python tools/test_grand_final_build.py <pesdb>  # the grand final: recipe key, Build, league window
python tools/test_grand_final.py       # the DLL's title leagues (any number), native
python tools/test_ceremony_build.py <pesdb>  # the trophy ceremony: recipe key, tmap lines, league window
python tools/test_ceremony.py          # the DLL's tournament map, native
python tools/test_fl26cine.py          # the cinematics module in Lua (lupa)
python tools/test_futve_playoff.py     # the pure parts (groups, order of the final), native
python tools/test_futve_fixture.py     # the fixture; skip without a world
python tools/futve_test.py --self-test # the sandbox round trip on a fake tree
python tools/test_liga_futve.py <pesdb>  # the Liga FUTVE recipe against phase 5's world
```

The native runner needs zig (`ZIG`, `PATH`, `D:/dev/tools/zig-*/zig.exe` or the branch's
`out/tools/py/ziglang/zig.exe`).
