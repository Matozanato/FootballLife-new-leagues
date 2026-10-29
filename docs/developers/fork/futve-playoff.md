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

## Building the world

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

The Apertura and Clausura play-offs take these pictures:

| competition | picture |
|---|---|
| 134 Liga FUTVE Apertura Playoffs | `PLAYOFF_APERTURA.png` |
| 135 Liga FUTVE Clausura Playoffs | `PLAYOFF_CLAUSURA.png` |

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
installs exactly the list in `files.json` (today the two play-offs, 12 files) and restores the game's
emblems at the end, so it never puts a logo on a competition that is not in the plan. `--install`
writes the staged set into the live world and backs up what it replaces under
`out/futve/logos/backup-<date>/` (the game closed) for after a Build, as for the world file;
`--restore` puts a backup back.

The three finals' pictures (`FINAL_APERTURA.png`, `FINAL_CLAUSURA.png`, `FINAL_FUTVE.png`) are for
the Final del Apertura, Final del Clausura and Final del FUTVE, which do not exist yet. **Their
competition ids are not 136-138**: 136 is a UEFA competition and 137/138 are Scotland's league and
cup (the world's own new competitions are 130-135 and the free ids start after them), so the finals
will take their ids from the world's free ids when they are built, and the logo tool gets them then.

## The sandbox of the in-game tests

```
python tools/futve_test.py --phase 1 --game "G:\Games\SP Football Life 2026"
python tools/futve_test.py --phase 2 --game "G:\Games\SP Football Life 2026"
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
   play-offs now, the finals when their ids are added), the game's `*.log`, `*.cache`, `sider.ini`
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
Clausura final), when the match is the final (`ctx.match_info == 53`), take the UEFA Europa League
final's entrance (`entry = 16`, `UEFA Europa League F`), and **263** (the Final del FUTVE) takes the
UEFA Champions League final's (`entry = 16`, `UEFA Champions League F`); all three take the generic
`Final\st001` scene from cinematicsB. The game's files are put back at the end, like everything
else.

## The two tests

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
- **The finals as competitions of their own.** The user's design for the next block: the Final del
  Apertura and the Final del Clausura as separate two-club cups (the two group winners), and the
  Final del FUTVE between the two champions -- no match and the title directly when it is the same
  club, or against a runner-up if a match must be played. Their competitions will take the world's
  free competition ids (the Build's; 136-138 are the game's: a UEFA competition and Scotland's
  league and cup); when they are built, add those ids to `futve_logo.py`'s PLAN and the sandbox
  installs their `FINAL_*` logos automatically. The cinematics above already reserve their
  regulations (261/262 the Europa League final's entrance, 263 the Champions League final's); the
  world and DLL side (new competitions, entries, fills, dates) is the next implementation. A
  separate competition of ours is still outside the game's trophy/title table, so the
  entrance/atmosphere is the visible part; the palmarés/records item below stands.
- **The club palmarés.** The 28 October final was played and the winner was read by the DLL
  (`cup 261 -- its final is over on day 15: champion 45ed8006`), but the club's Palmarés screen
  stayed empty. That screen is the game's own honours data, filled by its title bookkeeping, which
  exists for the shipped competitions only (the research notes: no table, code); a competition of
  ours (cid 134) is not in it. The champion is still the competition's winner -- the rights code the
  DLL reads -- and the sandbox now keeps the career save in the evidence for the analysis. Whether
  the title appears at the season's close, and whether a normal cup's final row (the change above)
  makes the game record it, is what the next test checks. A real fix would call the game's
  title-recording code, a new investigation, not a data change.
- **Competition Info.** The cup's group pages are the pages of a group competition; a crash there
  (as B205 once had) is checked in each test.
- **Saves.** A save loaded between two group days is covered by the match-count fallback; a save
  loaded at other points, the July teardown and the second season are phase 6.
- **A Build** overwrites the bins, `fl26world.txt`, `Player.bin` and the emblems: rerun
  `futve_world.py`, `futve_fixture.py --make` and `futve_logo.py --install`, then install with the
  sandbox.

## Tests without the game

```
python tools/test_futve_playoff.py     # the pure parts (groups, order of the final), native
python tools/test_futve_world.py       # both staging worlds against the real world; skip without one
python tools/test_futve_fixture.py     # the fixture; skip without a world
python tools/futve_test.py --self-test # the sandbox round trip on a fake tree
```

The native runner needs zig (`ZIG`, `PATH`, `D:/dev/tools/zig-*/zig.exe` or the branch's
`out/tools/py/ziglang/zig.exe`).
