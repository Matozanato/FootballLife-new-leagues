# FootballLife — new leagues (public beta)

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-support%20this%20work-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/mata28)

> This is unpaid reverse-engineering work done in spare time. If it is useful to you,
> **[buy me a coffee on Ko-fi](https://ko-fi.com/mata28)** — it keeps the seasons running.

Raise Football Life 2026's hard limits so that **hundreds of new clubs and dozens of new
leagues** fit into a Master League season, using only Sider modules and data files. No
patched executable, no repacked CPKs.

This is a **research beta**. It is published so that people who mod this game can test it,
break it, and tell us where. Read [what works and what does not](#status) before you
install anything.

> **Read this first: [docs/how-to.md](docs/how-to.md)** — the complete how-to on one page:
> installing, adding new leagues, putting a league in a particular country (Japan, China,
> Saudi Arabia ...), the new Champions League format with UEFA's calendar, what to watch out
> for, and what to do when a step does not give what it should. Every step says what you
> should see. **Please go through it before asking**: most questions are answered there.
>
> **Never used Python? [docs/beginners-guide.md](docs/beginners-guide.md)** —
> every step from installing Python to playing the new leagues, written for someone who has
> never used Python or Sider modules. It says what you should see after each step and what
> to do if you see something else. About thirty minutes.
>
> Testing it in detail? [docs/step-by-step.md](docs/step-by-step.md) has the same path with
> everything worth checking and reporting along the way.

> ## New: FL26 Mod Studio (beta)
>
> **One program for everything you add to the game** — no Python needed. Download
> `FL26ModStudio-<version>.zip` from [Releases](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest), unzip, run `FL26ModStudio.exe`.
>
> - **Install mods** by dropping them on the window (zip, 7z, folder, .lua, .cpk): it says what
>   each part is and where it goes, merges content-server map files into yours, and every mod
>   it installs can be removed again.
> - **Content servers** — stadiums, kits, balls, commentary, music and goal songs, scoreboards,
>   menus, referee kits, sleeve badges, weather — with their map files edited as tables.
> - **Sider setup**: content folders and Lua modules switched on and off and put in order,
>   profiles, restore points for every file it changes, and a diagnostics report.
> - **League Builder**: new leagues and clubs, the game's own leagues and clubs renamed,
>   **every club's players edited** (names, numbers, positions, abilities, skills, faces), and
>   **league packages** (`.fl26pack`): a modder makes a league once, anybody adds it to their game.
> - **Europe** (0.1.1): a new league's own Champions League, Europa League and Conference League
>   places, and the Conference League itself (the 2024 format) as one tick in Build.
> - **Updates itself** (from 0.1.1): it says when a new version is out and installs it —
>   *Help → Check for updates*. Settings and projects stay.
> - **Squads from a table** (0.1.2): any table of players — typed by hand, copied off a
>   website, a Football Manager or EA FC export — becomes a club's squad; what the table does
>   not have comes from the game's own players of the same position and rating.
> - **Cups** (0.1.3): a new country's own national cup and super cup, and the continental cups
>   the game does not have (CAF Champions League, CAF Confederation Cup, AFC Champions League
>   Two, Copa Sudamericana) built from the places your leagues give. New leagues take their
>   own continent, managers get names, and a lower tier is one button.
> - **Fixes** (0.1.3.1): promotion and relegation for new countries outside Europe and for
>   leagues that play January to December, a **Rating** field on the Players page, the
>   Conference League switch, and a League window that fits a 1080p screen.
> - **Formations** (0.1.4): a new league's clubs, or a single club, line up in any formation
>   the game's clubs use, with the first eleven shown on a pitch on the Players page.
> - **Clubs and squads** (0.1.4): clubs the game already has in your new leagues, a national
>   team editor, transfers between clubs, your own team and player ids for new clubs and
>   players, and a portrait for a club's manager.
> - **Seasons and cups** (0.1.4): a national cup of any size up to 44 clubs, February to
>   December for a new country, Libertadores qualifying places, a shipped country's cup that
>   takes your new second division, a "Europe only" build, and a league-phase draw that keeps
>   clubs of one country apart as UEFA does. Split and Apertura/Clausura leagues in new
>   countries play properly again.
> - English, Croatian, Spanish and French.
>
> Guide: [docs/mod-studio-guide.md](docs/mod-studio-guide.md) ·
> [hrvatski](docs/mod-studio-guide.hr.md) · [español](docs/mod-studio-guide.es.md) ·
> [français](docs/mod-studio-guide.fr.md) · how it works and the package format:
> [docs/mod-studio.md](docs/mod-studio.md)
>
> **Questions** (updating, crashes at start, cups, promotion, what to send when something is
> wrong): [docs/faq.md](docs/faq.md)

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

This project does two things:

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

`sider/experimental/` holds sixteen more that go further and **have only been run on our own
test world**: 192 competitions instead of 127; every league selectable in the Select Team
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

Measured on our test worlds, always with a new club as the manager's team. The one played
most recently (2026-09-24) has **39 new leagues, 780 new clubs and 23,400 new players** (30 per
club): 602 of the clubs are placed in the leagues, which now have 10 to 24 clubs each, and 178
have no league, as the game's own unattached clubs do. One of the 39 (regulation 62, 12 clubs)
is in the data but is not loaded by the game, so 38 leagues and 590 clubs actually play; why
is not known yet. It also has the Champions League and Europa
League in the 2024 format and a new Conference League. Four seasons have been played end to
end on an earlier world of 39 leagues of 20 clubs, and since 2026-09-23 the added leagues also
close and re-open properly at every rollover. This page was last checked against the
published modules on **2026-09-25**.

> **New patch set on 2026-09-24: start a new career.** `sider/fl26caps.lua` now holds 46,000
> match records instead of 26,000 (everything since 2026-09-22 was played on it), and a save
> made under one patch set does not load under another. Keep your old `fl26caps.lua` if you
> want to go on with an old career.

**Works**

- Exhibition matches between new clubs.
- **Every added league entering the season, including leagues in countries of their own.**
  On a 41-league world where each league stood alone in its own country, only 8 were ever
  given a season; with `fl26join.dll`, 39 of the 40 present were dealt a full 38-round
  schedule (the 40th is a split-season format, a separate problem).
- **The next season, too (new 2026-09-23).** Before, the added leagues were never closed at
  the end of a season: they kept the old year, their points and matches added up season on
  season (76 matches after two), and old matches stayed on the calendar. The updated
  `fl26join.dll` closes them in July with the shipped leagues and keeps them open through
  New Year, since their season runs August to May. Measured: empty tables and the right year
  after the rollover, and points still rising past the New Year after it. **If you
  downloaded `fl26join.dll` before 2026-09-23, replace it.**
- Starting a Master League season with a new club in a new league: season generates,
  fixtures appear, the Team Sheet shows a real squad (the walkthrough builds 30 per club),
  the hub shows the standings.
- Saving the season and loading it back: the club, the squad, the manager's name, the
  standings and the fixtures all survive. The same save was loaded three times in a row with
  no drift, and the coach and player tables were compared byte for byte before and after.
- Advancing the calendar with matches simulated ("Skip Match") through complete seasons and
  across New Year: 655 game days in one unattended run with no crash, and four season
  rollovers in total.
- **A career that starts on 1 August** (experimental, `fl26augseason.lua`). A career in a
  league standing in a country of its own used to open in January. Measured on two new
  careers on 2026-09-23: both open on 1 August. On its own it leaves the European
  competitions unstarted (see below); with `fl26swiss` they start and play.
- **The Champions League, Europa League and Conference League in the 2024 format**
  (experimental, `fl26swiss.lua` + `fl26swiss.dll` and the European world tools, new
  2026-09-24). One league phase of 36 clubs each, a play-off for places 9-24, then a fixed
  bracket from the round of 16. In the second season all three were filled from the previous
  season's final tables through a UEFA access list, 108 of 108 places (in our world, whose
  list then named its own leagues). The Champions League
  and Europa League are shipped competitions and are modified in your own world copy; the
  Conference League is added. [Details and caveats](sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).
- **Leagues of 10, 12, 14, 16, 18, 22 and 24 clubs** with the real number of rounds: 10 clubs
  play four times (36 rounds), 12 three times (33) or four (44), 24 clubs twice (46). Checked
  in two seasons running. Built with `tools/mksizes.py`; dated with `fl26swiss.dll`.
- **Database -> Competition Info** lists the countries of the added leagues under their own
  names (experimental, `fl26catlist.lua`). The flags there are still borrowed.
- **Each added league shows its country's flag in the Select Team list** (experimental,
  `fl26comptab.lua`), using the flags the game already has. `tools/mkflags.py` works the
  country out from the league's name, or from a short list you write, and fills in the tables.
  The idea, the hook and the first working version are Stagnant09's (issue #11).
- **Edit mode reaches the added leagues** (experimental, `fl26editlist.lua`): Edit > Teams,
  Edit > Players > Edit Player, Transfer and Managers list every added league with its clubs,
  so their clubs and players can be edited in the game itself.
- **Every new club has a manager of its own** (`FL M0001`, ...): `mkworld.py` writes
  `Coach.bin` with them, and `tools/mkcoaches.py` adds them to an older world. Before, every
  new club showed the same made-up manager, "Jorge Jesus".
- **Promotion and relegation through a whole pyramid** (experimental, `fl26chain` +
  `fl26seasonend` + the rank modules). On our world, with a third, fourth and fifth division
  under Ligue 2 and under Serie B, three clubs went up and three down at every joint of both
  chains at the 2026-09-23 rollover, and on 2026-09-24 all five chains of the newer world,
  one of them under the Championship, did the same.
- All 39 new leagues of 20 clubs playing their full 38 rounds in the first season. Before the fixture
  list was raised, some of them played none at all. Later seasons went wrong for a different
  reason, found and fixed on 2026-09-17 — see the first item below.
- League tables that show the current season only. See `fl26hdr127.lua` above and the
  caveat in [known-issues.md](docs/known-issues.md). `fl26hdr127.lua` was updated on
  2026-09-23 (29 -> 32 patches): three places that read the moved tables had been missed,
  and one of them hid leagues from promotion and relegation. Replace it if you downloaded it
  earlier.
- League sizes from 10 to 30 clubs. Different sizes in the same world. Ten is not a
  floor we imposed — the shipped game runs a 10-club league of its own, and 10-club
  leagues have been played here. Above 30 the round list runs out: see
  [limits.md](docs/limits.md). A league that is not 20 clubs playing twice needs
  `fl26swiss.dll` for its dates, or it ends early or runs out of dates.
- **Cups.** A cup built with `mkcup.py` plays a full Master League knockout, every round
  dated: round of 16, quarter-finals, semi-finals, final. One rule decides it — the cup is
  filled from the **first league in its region**, and that league must have **sixteen clubs**,
  because the shipped cup calendar only covers a sixteen-club bracket. With twenty, one round
  is left with no date and the cup stalls. No executable change is involved.

**Fixed** (these used to be listed below as open problems)

- **(Fixed 2026-09-16.)** The crash a day after matchday 1 was ours: on load, regulation
  records were written over the top of the team array, so 69 clubs came back from a save
  with broken squad entries and the AI could not field a side. If you downloaded before
  2026-09-16, replace `sider/fl26caps.lua`. **Your save files are fine** — the damage was
  only ever in memory, and an old save loads clean with the new module.
- **(Fixed 2026-09-17, now verified across a rollover.)** Later seasons scheduled fewer and
  fewer leagues, until by the fifth season only 4 of the 39 new leagues had any fixtures and
  the calendar showed empty days. The match records were all there; they carried no date, so
  nothing ever put them on a calendar day. That came from the patch set, not from the game.
  **If you downloaded before 2026-09-17, replace `sider/fl26caps.lua`.** Verified since: a
  world played into its second season has all 39 leagues dealt a full 380-match season, every
  record on the calendar and none dropped. One thing is still imperfect and is written down
  rather than hidden: five of the 39 leagues do not keep the PREVIOUS season's matches across
  the turn of the year. The other 34 carry two seasons at once at that point; those five carry
  only the new one. They all play. [Details](docs/known-issues.md).
- **(Fixed with the experimental `fl26swiss`, 2026-09-24.) The European competitions in a
  career that starts in August.** The game registers the European competitions on day 238,
  after the Champions League play-off dates (days 230 and 237), so on its own the play-off
  never gets its matches and nothing after it begins. `fl26swiss` runs its own play-off and
  starts all three competitions; measured on 2026-09-24 through the knockout rounds. Without
  `fl26swiss` this still happens (the domestic season is not affected), and without
  `fl26augseason.lua` the career opens in January instead.

- **(Fixed with the experimental `fl26swiss`, 2026-09-24.) Competition Info for the
  European competitions.** The Europa League and Conference League tables were greyed out
  under *Group stage*, and opening *Knockout Phase* before the knockout draw crashed the game.
  Both tables now show, and the knockout item appears once that phase starts. The play-off
  item (places 9-24) is called *Play-offs* instead of *W-L Table*, stays grey until the
  play-off is drawn, and then lists its ties (updated 2026-09-25).
  [Details](sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).
- **(Fixed 2026-09-25.) The 25th league moved off rulebook id 145.** 145 is the shipped J2
  League's id, and the shipped J1 League relegates into it. `mkworld.py` now puts that league
  on **190**. Worlds built before still work: the modules know both ids. If you rebuild your
  world with the new `mkworld.py`, also take the new `fl26caps.lua`, `fl26joindll.lua` and,
  if you use them, `fl26comptab.lua`, `fl26chain.lua` and `fl26swiss.dll`, or league 190 gets
  no dates. The patch set's sizes did not change, so saves are not affected.
- **(Fixed 2026-09-25, issue #2.) Blank headings in the team list.** `fl26slotnames.lua`
  blanked the heading of a slot even when your world had no league on it. Such a slot now
  keeps its original heading, so the default list is safe in any world. Replace the file if
  you downloaded it earlier.

**Does not work yet / under investigation**

- **The competition table can still fill up.** `fl26hdr127.lua` raises it from 100 to 127,
  but an entry is never given back, so across four seasons the count rose 88, 115, 119, 124.
  Whether it stops below 127 is not yet known. The experimental `fl26hdr192.lua`, which our
  current test world runs, raises the ceiling to 192 and leaves far more room. Long-running worlds are the most useful thing
  you can report — see the [testing guide](docs/testing-guide.md).
- **The game crashes now and then inside its own protected code** (fault offsets
  `0x84ed4c0`, `0x131cc313`, `0x18ecc042`), while a scene is being set up: generating a
  season, loading a match, a season rollover. **They are the game's own:** on 2026-09-25/26,
  with none of our modules and no patch set, 10 of 12 season creations crashed at the
  manager-settings step (at `0x84ed4c0`, `0x131cc313` and `0x1fea5ba`), and the untouched
  game started without Sider crashed at the same step in 4 of 8. With our full set it was 13
  of 30, fewer because `fl26nullguard.lua` catches `0x1fea5ba`. The saved season is not
  damaged: start again or reload, and save often.
- **A calendar day holds only 280 matches**, and everything past that is dropped in silence
  — no error, no sign in the world files, just a round that never happens. The published
  remedy is to spread the leagues over different weekdays, which is what `--date-offsets` is
  for; `tools/dayplan.py` measures a running season and prints the spread that flattens it.
  (The ceiling itself can be moved — that work is done and measured, and it is not published
  because it has not been played yet.) Anyone building much past 39 leagues will meet this.
- **A league's rulebook id decides whether it ever plays — twice over.** Fixture dates are
  not built from the competition you create; they are looked up in a table compiled into
  the executable, keyed by that id. Most free ids map to an empty entry, so a league can be
  created, appear in the menus, hold its rounds and never play a single match. And the list
  of competitions the game registers into a season is a second compiled table keyed by the
  same id, which is what `fl26join.dll` now works around **(fixed 2026-09-22)**. The dates
  still come from the first table, so the id list in `fl26caps.lua` still matters. See
  [how-it-works.md](docs/how-it-works.md).
- Not measured yet: a world like this with a **shipped club** as your team.
- **Rulebook ids above 175 work in Master League but are invisible in the Select Team list**
  unless `sider/experimental/fl26comptab.lua` is installed. That list is a static table in the
  exe rather than anything built from your data; the module copies it, gives our leagues free
  slots, and is meant to make all 39 selectable. Two things that list gets wrong on its own
  were measured on 2026-09-21 and have experimental modules of their own: a slot can carry a
  **hard-coded section heading** ("Classic Teams" over a league of yours — `fl26slotnames.lua`),
  and for nine slots the game builds the **wrong club list** entirely, showing national teams
  or foreign clubs or nothing (`fl26clubs.lua` + its DLL). None of the three has been through
  a season, which is why they are experimental. Without them the season still plays — the
  league is simply mislabelled, or missing, in that one menu. One side effect of
  `fl26comptab.lua`: three of our leagues take the slots of the **Asia-Oceania** and two
  **Classic Teams** entries, so those do not appear in **Kick Off** while it is installed
  ([details](docs/known-issues.md)).
- **Promotion and relegation between the new leagues works, with experimental modules
  only.** Of the 214 shipped rulebooks only eleven carry a promotion or relegation link at
  all, and none of them chains three tiers. On its own the engine moves clubs across every
  other joint of a chain; the rank field is **two bits**, so a third, fourth and fifth
  division look the same; and France and Italy are left out of the European season end. Each
  has an experimental module (`fl26rank` + `fl26deeprank`, `fl26chain`, `fl26seasonend`), and
  together they worked at the 2026-09-23 rollover (see Works). Their lists carry our world's
  league ids and must be edited for yours. Still wrong: Ligue 2 came out of that rollover
  with 21 clubs.
- Continental places for new leagues: not given out. The experimental `fl26swiss.dll` fills
  Europe from a UEFA access list of the shipped leagues only (since 2026-09-26, issue #8;
  in a first season each league is ordered by squad strength, or taken from your own
  `fl26swiss-first.txt`, since 2026-09-27);
  to give your leagues places, add them to `ACCESS` in `tools/native/fl26swiss.c` and rebuild. Without it, new clubs can end up in the
  Champions League anyway when their league is built as a first division in a shipped
  country — see [known-issues.md](docs/known-issues.md).
- New clubs use **placeholder names and cloned squads**, and the default kit until
  `tools/mkkits.py` lends them shipped kits. This project proves the capacity; dressing the
  clubs is ordinary Team.bin / kit editing on top of it (kit files for ids 65536..81919 are
  named `<id-65536>_ACL_...`, see [build-your-world](docs/build-your-world.md)).
- New leagues appear under an **existing menu region** (England by default), and spreading
  them over several shipped countries needs no executable change — `mkworld.py --regions`
  does it. Two limits sit above that, both mapped since. The shipped parser throws away any
  region numbered 29 or more although the field holds 64:
  `sider/experimental/fl26reg64.lua` is the one instruction that fixes it. And the menu's
  *heading* per region comes from a table of 24 rows; a region with no row does not draw a
  blank, it draws the heading of the country looked up before it, so regions above 24 work
  as groupings and borrow a name. The module that gives them headings of their own copies
  the game's own rows and is not published, because the version that exists carries those
  rows as a blob of shipped bytes and this repository does not redistribute game data.
  Database -> Competition Info is a different screen: there the added countries show under
  their own names with `sider/experimental/fl26catlist.lua`, though still with borrowed flags.
- More than 39 leagues, or leagues built with non-default ids, need a regenerated patch set
  ([why](docs/for-developers.md)).

The full list with details is in [docs/known-issues.md](docs/known-issues.md) and the hard
numbers in [docs/limits.md](docs/limits.md).

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

Never done this before? Follow [docs/how-to.md](docs/how-to.md) instead; it is the same
route, one small step at a time, plus leagues in other countries and the new European format.

1. **Back up** your save folder
   (`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`) and your `sider.ini`.
2. Follow [docs/install.md](docs/install.md) to install the Sider modules — eleven files,
   ten `lua.module` lines and one setting, `luajit.ext.enabled = 1` — and confirm in
   `sider.log` that every patch module reports `applied all` and `fl26joindll` reports
   `installed`. (Or take the whole route in one pass:
   [docs/step-by-step.md](docs/step-by-step.md).)
3. Follow [docs/build-your-world.md](docs/build-your-world.md) to extract your game's tables,
   generate a world, and point `cpk.root` at it.
4. Start an exhibition match between two new clubs, then a Master League season with one of
   them. Then read the [testing guide](docs/testing-guide.md) and report what you see.

Common questions about Mod Studio, and renaming the new clubs, editing their players, and whether they show up in Edit mode with the scripts: see [docs/faq.md](docs/faq.md).

## Reporting

Open a GitHub issue. The [testing guide](docs/testing-guide.md#what-to-send) says exactly
what to attach — in short: your `sider.log`, the crash's *fault offset* from Windows Event
Viewer, how you built your world (the `mkworld.py` line and what it printed), and the save
file if the problem is reproducible from a save.

## Layout

```
sider/              fl26caps.lua (generated patch set), the null guards, fl26hdr127.lua,
                    fl26joindll.lua and the compiled fl26join.dll it loads
sider/experimental/ sixteen modules that go further, run on our test world only:
                    192 competitions, the Select Team list (names, slots, club lists),
                    64 regions, a 3-bit league rank and its relegation gate, an August
                    start, season-end promotion through a pyramid (fl26chain.dll),
                    Super Cup and results-screen guards, the 2024 European format and league sizes
                    (fl26swiss.dll), country names in Competition Info, the added
                    leagues in Edit mode's team lists
tools/              world builders (mkworld, mkplayers, mkcrests, mkkits, mkcup,
                    spreadregions, mkflags, mkreshape, mkuecl, mkeuropo, mksizes, rename, players,
                    playeredit, playereditor ...),
                    pesdb/CPK readers, the patch-set generator and its checkers
tools/modstudio/    FL26 Mod Studio (the window; tools/modstudio_main.py starts it from source,
                    tools/mszip.py makes the release zip) and the League Builder behind it
                    (leaguebuilder, lbplayers, lbfaces, lbpackage, lbpack ...)
tools/native/       the C source of the four DLLs, their build scripts and checksums
patches/            the patch set as JSON plus the layout tables the generator reads
docs/               mod-studio-guide (en/hr) and mod-studio (how it works, package format),
                    how-to (start here), step-by-step, install, build-your-world, testing-guide, known-issues,
                    limits, how-it-works, for-developers, faq, beginners-guide
```

## Support

Everything here is free and MIT-licensed. Weeks of disassembly, unattended test seasons
and crash dumps went into it, and there is more to do (the crashes in the game's protected code, loading long saves,
menu region names and flags, continental places for any world rather than ours). If you want to help it along:
**[ko-fi.com/mata28](https://ko-fi.com/mata28)**. Testing and good bug reports help just as
much — see the [testing guide](docs/testing-guide.md).

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
