# FootballLife — new leagues (public beta)

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-support%20this%20work-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/mata28)

> This is unpaid reverse-engineering work done in spare time. If it is useful to you,
> **[buy me a coffee on Ko-fi](https://ko-fi.com/mata28)** — it keeps the seasons running.

**New leagues, new clubs and whole new countries in Football Life 2026's Master League**, plus
one program to manage everything else you add to the game. No patched executable, no repacked
CPKs: it all goes in through Sider modules and data files, and comes out again.

> ## FL26 Mod Studio (beta)
>
> **[Download the latest version](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest)**
> (`FL26ModStudio-<version>.zip`), unzip, run `FL26ModStudio.exe`. No Python needed. It
> tells you when a new version is out and installs it (*Help → Check for updates*); your
> settings and recipes stay.
>
> Guide: [English](docs/mod-studio-guide.md) · [hrvatski](docs/mod-studio-guide.hr.md) ·
> [español](docs/mod-studio-guide.es.md) · [français](docs/mod-studio-guide.fr.md) ·
> **questions** (updating, crashes at start, cups, promotion, what to send when something is
> wrong): [docs/faq.md](docs/faq.md) · how it works and the package format:
> [docs/mod-studio.md](docs/mod-studio.md)

This is a **beta**. It is published so that people who mod this game can use it, break it and
tell us where. Read [what works and what does not](#status) before you start a long career.

## What you can do

**Leagues and countries**

- Up to **39 new leagues** in one world, **10 to 24 clubs** each, playing each other 1 to 4
  times with the real number of rounds (10 clubs four times = 36 rounds). Select Team has room
  for 36 of them: the 37th to 39th play their season, but no career can start in them.
- **Any country.** A league is listed under its country in Select Team and Kick Off, with the
  country's flag; a country the game has no league for gets a heading of its own and plays on
  its own continent's calendar and cups (Europe, South America, Asia, Africa ...).
- **Pyramids.** Put a new league under another new league or under one of the game's
  (Championship, Serie B, 2. Bundesliga ...), down to the 7th division, with promotion and
  relegation at every joint. **Add lower tier** makes the next division in one click.
- **Formats:** everyone plays everyone; a Scottish-style **split**; **Apertura and Clausura**
  with play-offs of 8 or 4.
- **Season months** for a new country: August to May, or February to December like Brazil,
  Japan or Saudi Arabia (0.1.4).
- **Exhibition-only leagues** for Kick Off: legends, historical sides.
- Your own **league logo** and **country flag** (it replaces the game's flag of that country
  everywhere while the world is on). After Build, the **League ID** and **Team ID** columns
  show the ids the game uses.

**Clubs and players**

- New clubs with your **names, short names and crests** (or a numbered badge), **managers**
  with names and portraits (0.1.4), kits lent from the game's clubs, and a **formation** per
  league or per club with the first eleven on a pitch (0.1.4).
- **Clubs the game already has** in your new leagues. When such a club plays somewhere in the
  game, you pick who takes its place there, so no competition of the game changes size (0.1.4).
- **Rename** the game's own leagues and clubs, with new logos and crests.
- **Edit every player of every club**: name, number, positions, abilities, skills, rating,
  face, squad order, best eleven, squad level; CSV export and import.
- **Squads from a table**: any table of players — typed by hand, copied off a website, a
  Football Manager or EA FC export — becomes a club's squad.
- **Transfers** between any two clubs and **national team call-ups** (0.1.4); your own
  **club and player ids** for kit, crest and face packs made for a certain id (0.1.4).

**Cups and continents**

- The **2024 European format**: Champions League and Europa League with a league phase of 36,
  the February play-off and a fixed knockout bracket, and a new **Conference League**. Filled
  from a UEFA access list from the second season; in the first, by squad strength. The draw
  keeps clubs of one country apart as UEFA does (0.1.4).
- **Continental places** for your leagues: Champions League, Europa League, Conference League;
  AFC Champions League and Champions League Two; Copa Libertadores (also its qualifying round,
  0.1.4) and Copa Sudamericana; CAF Champions League and CAF Confederation Cup. The four the
  game does not have are built with your world.
- A country's own **national cup** (any size up to 44 clubs, with byes like the FA Cup, 0.1.4)
  and **super cup**, a **league cup**, and **pre-season cups** of 4 or 8 invited clubs in July.
  A new second division under a country the game has goes into that country's cup (0.1.4).
- **Europe only** (0.1.4): just the new European format, no new leagues.

**Everything else in your game folder**

- **Install mods** by dropping them on the window (zip, 7z, folder, .lua, .cpk): it says what
  each part is and where it goes, merges content-server map files into yours, and every mod it
  installs can be removed again.
- **Content servers** (stadiums, kits, balls, commentary, music, scoreboards, menus ...) with
  their map files edited as tables.
- **Sider setup**: content folders and Lua modules on, off and in order; profiles; a restore
  point for every file it changes; a diagnostics report to paste into a bug report.
- **League packages** (`.fl26pack`): a modder makes a league once — clubs, names, crests,
  logos, squads, faces — and anybody adds it to their own game.
- English, Croatian, Spanish and French.

**Versions**

| Version | Date | What it brought |
|---|---|---|
| 0.1.0 | 2026-09-28 | the mod manager and the League Builder |
| 0.1.1 | 2026-09-28 | the Conference League, European places for new leagues, updates itself |
| 0.1.2 | 2026-09-28 | squads from a table, the League ID column, Spanish and French |
| 0.1.3 | 2026-09-29 | cups of other continents, national and super cups, new countries on their own continent, manager names, **Add lower tier** |
| 0.1.3.1 | 2026-09-29 | promotion and relegation outside Europe and for January-December leagues, the Rating field, a League window that fits 1080p |
| 0.1.4 | 2026-09-30 | formations, clubs of the game in new leagues, transfers, national teams, club and player ids, manager portraits, national cups up to 44, February-December seasons, Libertadores qualifying, a shipped country's cup taking your second division, Europe only, the UEFA draw rules, split and Apertura/Clausura leagues fixed, the Kick Off order under Colombia and MLS |

The release notes of each version are on the
[Releases](https://github.com/Matozanato/FootballLife-new-leagues/releases) page.

> **Rather do it by hand, with Python?** [docs/how-to.md](docs/how-to.md) is the complete
> how-to on one page, [docs/beginners-guide.md](docs/beginners-guide.md) takes someone who has
> never used Python through every step, and [docs/step-by-step.md](docs/step-by-step.md) has
> the same path with everything worth checking along the way.

## The people who made this better

This project is tested in the open, and every fix in it since the first beta traces back to
someone who played a season, wrote down what happened and sent it. Thank you, all of you.

### vmardonesdev: the tester this project owes the most

**vmardonesdev** has done more for this project than anyone besides its author. Twenty-one of
the first thirty-seven GitHub issues come from vmardonesdev, and every one is a proper test
report: the exact commit, the exact world, what was installed, what was expected, what
happened, with logs and saves attached. vmardonesdev runs full seasons and season rollovers
that take hours, repeats a test on a fresh install before calling it a bug, says so when
something does **not** reproduce, and even published a complete testing plan. Several of the
worst bugs here were found only because vmardonesdev played further than anyone else:

- [#1](https://github.com/Matozanato/FootballLife-new-leagues/issues/1): the v2.2 report,
  a missing first round and a second season that only half rolled over.
- [#2](https://github.com/Matozanato/FootballLife-new-leagues/issues/2): the first matchday,
  Select Team and club lists; it led to the 25th league moving off regulation 145.
- [#4](https://github.com/Matozanato/FootballLife-new-leagues/issues/4) and
  [#5](https://github.com/Matozanato/FootballLife-new-leagues/issues/5): a six-league
  regression suite and a five-tier English pyramid played through a full season and a rollover.
- [#6](https://github.com/Matozanato/FootballLife-new-leagues/issues/6): showed that the
  "Team Spirit 99" squads did not come back on a clean build, which closed a false trail.
- [#7](https://github.com/Matozanato/FootballLife-new-leagues/issues/7): a written testing
  pipeline for the whole project.
- [#8](https://github.com/Matozanato/FootballLife-new-leagues/issues/8): two full seasons of
  an English D1-D5 world; it exposed new clubs in the Libertadores pools and led to the UEFA
  access list.
- [#9](https://github.com/Matozanato/FootballLife-new-leagues/issues/9): the 36-club
  continental test; it found the results-screen crash, the Conference League stall and the
  missing play-off regulation.
- [#10](https://github.com/Matozanato/FootballLife-new-leagues/issues/10): European
  knockouts that sometimes never started in the second or third season; the cause was a day
  counter that forgot New Year.
- [#12](https://github.com/Matozanato/FootballLife-new-leagues/issues/12): a Master League
  career on region 29 that started in January with no table; fixed in `fl26reg64`.
  [#14](https://github.com/Matozanato/FootballLife-new-leagues/issues/14) and
  [#16](https://github.com/Matozanato/FootballLife-new-leagues/issues/16) followed it through.
- [#17](https://github.com/Matozanato/FootballLife-new-leagues/issues/17) and
  [#20](https://github.com/Matozanato/FootballLife-new-leagues/issues/20): the first full
  walk-throughs of Mod Studio, the League Builder and every part of the Players page.
- [#18](https://github.com/Matozanato/FootballLife-new-leagues/issues/18): the League
  Builder crash on an empty region map.
- [#19](https://github.com/Matozanato/FootballLife-new-leagues/issues/19): a new second
  division linked under a league with no table had no fixtures; fixed in `fl26join`.
- [#21](https://github.com/Matozanato/FootballLife-new-leagues/issues/21): a new second
  division took over the country's domestic cup; `fl26chain` now keeps the cup to the top flight.
- [#22](https://github.com/Matozanato/FootballLife-new-leagues/issues/22): the same club
  drawn into two Libertadores groups in a first season; fixed in `fl26swiss`.
- [#29](https://github.com/Matozanato/FootballLife-new-leagues/issues/29): confirmed the
  domestic cup fix and caught a new second division's club playing the Supercup; the
  Supercups now stay with the top flight.
- [#31](https://github.com/Matozanato/FootballLife-new-leagues/issues/31): asked what to
  test next and turned the answer into the test runs for Apertura, the new countries' cups
  and the Kick Off order.

If you use anything from this repository, vmardonesdev's name belongs next to it.

### Alikhaled_727: the reports from outside Europe

**Alikhaled_727** (Evo-Web) builds the leagues nobody else tests (Saudi Arabia, Egypt,
Morocco, the rest of Asia and Africa) and writes up every result in long, careful messages
with screenshots: what the recipe was, which settings the career had, what the table, the
calendar and the board said, and what happened on the next day. A good part of 0.1.3.1 and
of 0.1.4 comes straight from those messages:

- a Saudi second division that moved its clubs in the table but not in the fixtures, and
  broke in the third season: the calendar-year promotion fixed in 0.1.3.1
  ([#27](https://github.com/Matozanato/FootballLife-new-leagues/issues/27));
- the League window taller than a 1080p screen, fixed in 0.1.3.1;
- the table of the AFC countries' seasons, behind 0.1.4's choice of season months for a new
  country;
- an Egyptian league with a Scottish-style split whose table filled with one club, fixed in
  0.1.4;
- CAF cups refused with fewer than four places, fixed in 0.1.4;
- the board asking for the Copa Libertadores in Africa, and an African league listed among
  the Asian ones;
- the ideas for moving the game's own clubs into new leagues, the CAF Super Cup, the CAF
  cups in Cup mode and the Club World Cup places for Africa.

Asian leagues with their own continental places, and with them the AFC Champions League Two
in the League Builder, were Alikhaled_727's idea too.

### Everyone else who helped

- **Stagnant09**: the flags in the Select Team list. The idea, the hook on the
  slot-to-country lookup and the first working version
  ([#11](https://github.com/Matozanato/FootballLife-new-leagues/issues/11));
  `fl26comptab.lua` and `tools/mkflags.py` are built on it.
- **pioup38**: the first report from a different game build and a clean configuration
  ([#3](https://github.com/Matozanato/FootballLife-new-leagues/issues/3)).
- **vector360** (Evo-Web): tested the new European format and reported that in a first
  season big clubs such as PSG, Real Madrid and Inter ended up in the Conference League.
  That report is why the first season is now ordered by squad strength. vector360's own
  36/36/36 list of 2026/27 clubs is why `fl26swiss` can take a first-season list
  (`fl26swiss-first.txt`). vector360 also saw Manchester United drawn against Manchester City
  in the league phase, which is why each pot is now spread so two clubs of one country do not
  meet there, and asked for the rest of the real draw rules, which the draw follows since
  0.1.4: no club meets a club of its own country and at most two of any other
  ([#15](https://github.com/Matozanato/FootballLife-new-leagues/issues/15)).
- **jibibi** (Evo-Web): tested the modules alongside a full French patch and the kit server
  and sent the logs, which show how the patch's own roots and the new clubs' kit names have to
  sit next to ours. jibibi's Sider folder with another name
  ([#28](https://github.com/Matozanato/FootballLife-new-leagues/issues/28)) is why Mod Studio
  now finds Sider by its `sider.ini`, whatever the folder is called.
- **bobzera** (Evo-Web): brought the "ACL71" kit problem into the open, new clubs past id
  65536 showing only the default kit, and worked on a fix of their own. That problem is the
  one `tools/mkkits.py` now solves by naming the kit files the way the engine looks them up.
- **spursfan07**: one of the first to build leagues by hand in the game's database files and
  bring every wall here: a league missing from the menu (its region had no label), clubs
  with blank names, and fixture dates that turned out to come from the regulation id
  itself. Those questions mapped a good part of what this project is built on, and
  spursfan07 is now testing the modules.
- **Amir** ([AmirPjanic](https://github.com/AmirPjanic)): tests Mod Studio release by
  release and asks for what a modder actually needs. The Team ID and League ID columns, the
  division shown next to each league, nationality typed by name, removing players from new
  clubs and club names with č, ć, š, ž, đ all came from those questions
  ([#23](https://github.com/Matozanato/FootballLife-new-leagues/issues/23)), and so did the
  managers' names of new clubs. Amir's own world, with leagues of 26 clubs, is why 0.1.4 lets a
  national cup have any number of clubs, and Amir asked for the national team editor, transfers
  between clubs and the formations of new clubs.
- **victormican** ([victormican](https://github.com/victormican)): tested Mod Studio on a
  South American world and reported what broke there: the Asia-Oceania national teams and the
  Classic Teams disappearing from Kick Off
  ([#26](https://github.com/Matozanato/FootballLife-new-leagues/issues/26)), a Colombian second
  division that plays January to December
  ([#27](https://github.com/Matozanato/FootballLife-new-leagues/issues/27)), the teams in no
  league that could not be found ([#25](https://github.com/Matozanato/FootballLife-new-leagues/issues/25))
  and the language switch ([#24](https://github.com/Matozanato/FootballLife-new-leagues/issues/24)),
  the Kick Off order that did not follow Mod Studio's
  ([#30](https://github.com/Matozanato/FootballLife-new-leagues/issues/30)) and the League
  window that did not fit the screen, with the idea of a separate editor for competitions
  ([#34](https://github.com/Matozanato/FootballLife-new-leagues/issues/34)).
- **jyanj083-dotcom** ([jyanj083-dotcom](https://github.com/jyanj083-dotcom)): a Peruvian
  world tested to the end: the empty Libertadores qualifying places, the wrong continent in
  League Info, player names and ratings that could not be changed and the Conference League
  switch that broke the other two
  ([#33](https://github.com/Matozanato/FootballLife-new-leagues/issues/33)); the DFB Pokal that
  ignored a new 2. Bundesliga ([#32](https://github.com/Matozanato/FootballLife-new-leagues/issues/32));
  the League window on a 1080p screen ([#35](https://github.com/Matozanato/FootballLife-new-leagues/issues/35)).
- **Gabyyy2008** ([Gabyyy2008](https://github.com/Gabyyy2008)): Apertura and Clausura in
  Argentina and Venezuela, and the same clubs playing the Libertadores and the Sudamericana
  ([#37](https://github.com/Matozanato/FootballLife-new-leagues/issues/37)).
- **alexfe87** ([alexfe87](https://github.com/alexfe87)): asked for the new UEFA formats on
  their own, without any new league, which is why 0.1.4 has a Europe-only build
  ([#36](https://github.com/Matozanato/FootballLife-new-leagues/issues/36)).
- **ThanosMJ** (Evo-Web): Greek leagues three divisions deep, the league order in Select Team,
  and the request to edit team and player ids in Mod Studio.
- **NudnyNick999** (Evo-Web): asked for a league to appear higher in the selection menu, which
  started the Kick Off order work, and saw an exhibition-only league land below Classic Teams.
- **bnaanana** (Evo-Web): sent a full `sider.log` of a crash, which showed how another
  module's errors look next to ours.
- **dannydecai** (Evo-Web): found that the commentary call names probably stop working for
  ids above 9999.
- **astyleUZ** (Evo-Web): asked the first-time questions that show where the guides have to
  be clearer.
- **Zega_1991** (Reddit): asked for regens that do not come back with a retired player's name
  and ratings.
- **Alby17** (Evo-Web): found that a shirt number typed as 10 came out as 11 in the game; the
  game stores the number minus one, and every editor here now goes through that.
- **n1ne** (Discord): follows the work closely and asks the questions that show where the
  docs are not clear yet, such as how the European competitions get their clubs.

Reports are welcome from anyone: open an
[issue](https://github.com/Matozanato/FootballLife-new-leagues/issues) with what you
installed, what you did and what you saw, and you will be on this list too.

## Free to use — please credit

Everything in this repository is **free**, and it stays free. MIT licence: use it, change
it, ship it inside your own mod, charge for your mod if you want to. No permission needed
and nothing to pay.

There is one thing I do ask, and it is not a legal condition, just the normal courtesy
between modders:

> **If you use these findings, addresses, patch sets or tools in your own mod, credit this
> work and link back to this repository.**

A line in your readme or your release post is enough — something like:

```
Limit-raising and league research: Matozanato — https://github.com/Matozanato/FootballLife-new-leagues
```

Why it matters: none of this came from a leaked tool or somebody else's notes. Every
address here was found by disassembling the game and by running test seasons until they
crashed, and it is published openly so that nobody has to do it twice. Credit is what keeps
that worth doing — and it also means the next person who hits the same wall can find where
the answer came from instead of starting over.

If you are building something on top of this, I would rather hear about it than not.
Open an issue and say what you are making; if a limit is in your way, it may already be
mapped.

## What it is

Football Life 2026 (PES 2021 engine) keeps every club, coach, competition and fixture in
fixed-size tables inside the executable's memory. Shipped, those tables hold 750 clubs, 1,300
coaches, 300 competition rulebooks and 13,000 match records. Add a few more leagues and the
data simply falls off the end: the season generator drops fixtures without a word, a saved
game loses everything past the shipped count, and a coach lookup lands on the wrong record.

Mod Studio installs and sets up everything below for you; this part is for anyone who wants
to know how it works, or to build by hand. The project does two things:

1. **`sider/fl26caps.lua`** — a runtime patch set of 2,759 byte changes, applied by Sider at
   startup, that grows those tables and every piece of code that indexes them:

   | table | shipped | with fl26caps |
   |---|---|---|
   | clubs | 750 | 1,600 |
   | coaches | 1,300 | 2,600 |
   | competition rulebooks (regulations) | 300 | 600 |
   | players | 30,001 | 51,729 |
   | match records per season | 13,000 | 46,000 |
   | fixtures list | 2,000 | 8,000 |
   | competitions a season can hold | 100 | 192 with `fl26hdr192.lua` (experimental, used on our test world); 127 with the stable `fl26hdr127.lua` |

   Every module verifies the bytes it is about to change and refuses to touch a different
   game build. If anything does not match, the game runs unmodified and `sider.log` says why.

2. **`tools/`** — Python scripts that build a set of new leagues and placeholder clubs
   (with squads) from **your own** game data, as a Sider `livecpk` root. No game data is
   shipped in this repository; everything is generated on your machine from your install.

Plus seven small **null-guard modules** that stop known crashes in the game's own code which
the larger world exposes, **`fl26hdr127.lua`**, which widens the table a season uses to
hold its competitions from 100 to 127 — the fix for league tables showing 76 matches played
and ~130 points — and **`fl26joindll.lua` + `fl26join.dll`**, which get every added league
*into* the season and, since 2026-09-23, *out of it again* at the end. The game registers
and closes competitions from lists compiled into the executable, so a new league standing in
a country of its own was never presented to the season at all, and once it was, it was never
closed and carried its table on into the next season. The module handles both. It is the one
compiled piece in the main folder; its source and how to build it are in
[tools/native/](tools/native/README.md).

`sider/experimental/` holds seventeen more that go further and **were first run on our own
test worlds**: 192 competitions instead of 127; every league selectable in the Select Team
list, under its own name, showing its own clubs; 64 menu regions instead of 29; a league rank
wide enough for a pyramid five divisions deep, with the relegation gate to match; a career
that starts in August instead of January; promotion and relegation through a whole pyramid,
not just its top joint; guards for the Super Cup and the play-off results screen; **the 2024 European format** for the
Champions League, the Europa League and a new Conference League, filled from a UEFA access
list, with leagues of 10 to 24 clubs; the added countries listed by name under
Database -> Competition Info; and every added league in Edit mode's team lists. They abort cleanly if anything does
not match, and they are the part where another pair of hands helps most —
[what they are, and in what order](sider/experimental/README.md).

## Status

Everything below was measured on our own test worlds, by playing Master League seasons
unattended with matches simulated. This section was last checked on **2026-09-29**, against
Mod Studio 0.1.4. The full list, with dates and details, is in
[docs/known-issues.md](docs/known-issues.md); the hard numbers are in
[docs/limits.md](docs/limits.md).

**Measured and working**

- **A Master League career in a new league, or with a club of the game**: the season
  generates, every league gets its fixtures, the Team Sheet shows a real squad (30 players a
  new club) and the hub shows the standings. On 2026-09-29 a career with a club of the game, in
  a world with two new South American leagues, played 338 days in one unattended run.
- **Saving and loading**: the club, the squad, the manager, the standings and the fixtures all
  come back, also from a save made after a full season.
- **Season after season.** The added leagues close in July with the game's own and open again
  with empty tables and the right year; leagues that play January to December go on into their
  next season too. Four rollovers in a row on one world, and 655 game days in one run without a crash.
- **Promotion and relegation through whole pyramids**: three up and three down at every joint
  of five chains, one of them under the Championship (2026-09-28). New countries outside Europe
  and January-December leagues go on into their second season (0.1.3.1), and so does a league
  outside Europe with no division below it (0.1.4: Egypt, Morocco and Venezuela, 2026-09-29).
- **The 2024 European format**: the league phase of 36, the play-off and the knockout of all
  three competitions, and in the second season 108 of 108 places filled from the previous
  season's tables.
- **Cups of other continents**: the CAF Champions League and CAF Confederation Cup play their
  groups and knockout; the Copa Sudamericana was drawn with 32 clubs on 2026-09-29, with the
  clubs already in the Copa Libertadores left out.
- **Leagues of 10 to 24 clubs** with the right number of rounds, different sizes in one world.
- **The menus**: the first 36 new leagues in Select Team, every one in Kick Off, Edit mode and Database →
  Competition Info, under its own country's name and flag.

**Known problems**

- **The game crashes now and then inside its own protected code** (fault offsets `0x84ed4c0`,
  `0x131cc313`, `0x18ecc042`) while a scene is being set up: generating a season, loading a
  match, a season rollover. **They are the game's own:** on 2026-09-25/26, with none of our
  modules and no patch set, 10 of 12 season creations crashed at the manager-settings step, and
  the untouched game started without Sider crashed at the same step in 4 of 8. Start the game
  from its launcher, start again or reload, and **save often**: the saved season is not
  damaged.
- **A saved career belongs to its world.** It loads only with the same world switched on, and
  any change to a league's clubs needs a new career.
- **A new league outside Europe shows the wrong continent** in Select Team's League Info
  panel (the European cups for one that plays August to May, the South American text for some
  others) and in the board's objectives, and a new Asian league sits below *Other Clubs (Asia)*
  (issue #43). Its places go to its own continent's cups; only the text is wrong. Not fixed
  yet.
- **An Exhibition only league still shows** in Master League's team list (the game has one
  list for Kick Off and Master League). Do not start a career with one of its clubs.
- **February-December seasons** cannot yet be combined with a split, Apertura/Clausura, a
  national cup or a league cup.
- **A calendar day holds 280 matches**; everything past that is dropped in silence. A world of
  39 leagues stays under it; `tools/dayplan.py` measures a running season.
- **The competition table can fill up** over many seasons: `fl26hdr127.lua` raises it from 100
  to 127 and the experimental `fl26hdr192.lua` to 192. Long-running worlds are the most useful
  thing you can report — see the [testing guide](docs/testing-guide.md).
- **39 new leagues in one world** and **1,536 clubs in all** are walls; more leagues need a
  regenerated patch set ([why](docs/for-developers.md)).
- **A new patch set means a new career**: a save made under one `fl26caps.lua` does not load
  under another.

## Requirements

- Football Life 2026 with its bundled Sider (`SiderAddons` folder next to `FL_2026.exe`).
  The modules were built against `FL_2026.exe` version **26.0.0.0**, 458,910,720 bytes,
  SHA-256 `7c27ecb303b71331e36f9ccd8ac879f0f0d8c56c754bd4d0d2e9c8353464f847`. A different build
  is refused, safely, at startup.
- Python 3.10 or newer for the world-building tools. No third-party packages are needed to
  build a world. Regenerating the patch set (developers only) needs `capstone`.
- FL26 Mod Studio: nothing, the release `.exe` carries what it needs. Run from source
  (`python tools/modstudio_main.py`) it needs `PySide6`, `Pillow` and `py7zr`; making the
  release zip (`tools/mszip.py`) also needs `pyinstaller`, `markdown` and zig for the DLLs.
- Windows. The tools were only ever run on Windows.

## Quick start

1. **Back up** your save folder
   (`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`) and your `sider.ini`.
2. Download **FL26 Mod Studio** from
   [Releases](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest), unzip it
   and run `FL26ModStudio.exe`. In **Settings**, pick the game folder (the one with
   `FL_2026.exe`) and press **Unpack the game's tables**.
3. **League Builder → New leagues → Add league**: a name, a country, the number of clubs.
   Then **Build**: install the modules, check the plan, build the world, switch it on.
4. Start the game through its launcher, come back and press **After a start: check**. Then
   start a **new** Master League career: the new leagues are under their country in Select
   Team.

The [guide](docs/mod-studio-guide.md) goes through every page, and the
[FAQ](docs/faq.md) answers what people ask most. Building by hand with Python instead:
[docs/how-to.md](docs/how-to.md), then [docs/install.md](docs/install.md) and
[docs/build-your-world.md](docs/build-your-world.md).

## Reporting

Open a GitHub issue. From Mod Studio, **Diagnostics → Run the checks → Copy a report** puts
everything useful in the clipboard; paste it into the issue. The
[testing guide](docs/testing-guide.md#what-to-send) says what else helps: your `sider.log`, the
crash's *fault offset* from Windows Event Viewer, your recipe (or how you built your world),
and the save file if the problem can be repeated from a save.

## Layout

```
sider/              fl26caps.lua (generated patch set), the null guards, fl26hdr127.lua,
                    fl26joindll.lua and the compiled fl26join.dll it loads
sider/experimental/ seventeen modules that go further: 192 competitions, the Select Team
                    list (names, slots, club lists, flags, Kick Off order), 64 regions, a
                    3-bit league rank and its relegation gate, an August start, season-end
                    promotion through a pyramid (fl26chain.dll), Super Cup, results-screen and
                    club-change guards, the 2024 European format, league sizes, split
                    seasons and other continents' cups (fl26swiss.dll), country names in
                    Competition Info, the added leagues in Edit mode's team lists
tools/              world builders (mkworld, mkplayers, mkcrests, mkkits, mkcup, mkflags,
                    mkreshape, mkuecl, mkeuropo, mksizes, mktactics, rename, players,
                    playeredit, playereditor ...), pesdb/CPK readers, the patch-set generator
                    and its checkers
tools/modstudio/    FL26 Mod Studio (tools/modstudio_main.py starts it from source,
                    tools/mszip.py makes the release zip) and the League Builder behind it
                    (leaguebuilder, lbplayers, lbfaces, lbpackage, lbpack ...)
tools/native/       the C source of the four DLLs, their build scripts and checksums
patches/            the patch set as JSON plus the layout tables the generator reads
docs/               mod-studio-guide (en/hr/es/fr), mod-studio (how it works, package format),
                    faq, how-to, beginners-guide, step-by-step, install, build-your-world,
                    testing-guide, known-issues, limits, how-it-works, for-developers,
                    league-phase-swiss-decode, player-record
```

## Support

Everything here is free and MIT-licensed. Weeks of disassembly, unattended test seasons and
crash dumps went into it, and there is more to do (the crashes in the game's protected code,
the African leagues' League Info panel, more competitions and formats). If you want to help it
along: **[ko-fi.com/mata28](https://ko-fi.com/mata28)**. Testing and good bug reports help just
as much — see the [testing guide](docs/testing-guide.md).

## Licence and credits

MIT — see [LICENSE](LICENSE). Football Life 2026, PES 2021 and Sider belong to their
respective authors; nothing of theirs is redistributed here.

The reverse engineering was done from scratch against the game's executable and data
files. Nothing here is derived from anyone else's tool or notes, except where a contributor
is named.

Contributors, and what each of them did, are listed in
[The people who made this better](#the-people-who-made-this-better) near the top: above all
**vmardonesdev** and **Alikhaled_727**, and **Stagnant09**, **pioup38**, **vector360**, **jibibi**, **bobzera**,
**spursfan07**, **Amir**, **victormican**, **Alby17**, **jyanj083-dotcom**, **Gabyyy2008**, **alexfe87**,
**ThanosMJ**, **NudnyNick999**, **bnaanana**, **dannydecai**, **astyleUZ**, **Zega_1991** and **n1ne**.

The licence asks nothing of you. I do: **if you use these findings, addresses, patch sets
or tools in a mod, credit this work and link back** — see
[Free to use — please credit](#free-to-use--please-credit) at the top. It costs you one
line and it is the only thing asked in return.
