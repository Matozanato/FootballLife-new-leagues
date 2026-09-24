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

> **New to all this? Start here: [docs/beginners-guide.md](docs/beginners-guide.md)** —
> every step from installing Python to playing the new leagues, written for someone who has
> never used Python or Sider modules. It says what you should see after each step and what
> to do if you see something else. About thirty minutes.
>
> Testing it in detail? [docs/step-by-step.md](docs/step-by-step.md) has the same path with
> everything worth checking and reporting along the way.

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

`sider/experimental/` holds fourteen more that go further and **have only been run on our own
test world**: 192 competitions instead of 127; every league selectable in the Select Team
list, under its own name, showing its own clubs; 64 menu regions instead of 29; a league rank
wide enough for a pyramid five divisions deep, with the relegation gate to match; a career
that starts in August instead of January; promotion and relegation through a whole pyramid,
not just its top joint; a guard for the Super Cup; **the 2024 European format** for the
Champions League, the Europa League and a new Conference League, filled from a UEFA access
list, with leagues of 10 to 24 clubs; and the added countries listed by name under
Database -> Competition Info. They abort cleanly if anything does
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
published modules on **2026-09-24**.

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
  season's final tables through a UEFA access list, 108 of 108 places. The Champions League
  and Europa League are shipped competitions and are modified in your own world copy; the
  Conference League is added. [Details and caveats](sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).
- **Leagues of 10, 12, 14, 16, 18, 22 and 24 clubs** with the real number of rounds: 10 clubs
  play four times (36 rounds), 12 three times (33) or four (44), 24 clubs twice (46). Checked
  in two seasons running. Built with `tools/mksizes.py`; dated with `fl26swiss.dll`.
- **Database -> Competition Info** lists the countries of the added leagues under their own
  names (experimental, `fl26catlist.lua`). The flags there are still borrowed.
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
  Both tables now show, and the knockout item appears once that phase starts.
  [Details](sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).

**Does not work yet / under investigation**

- **The competition table can still fill up.** `fl26hdr127.lua` raises it from 100 to 127,
  but an entry is never given back, so across four seasons the count rose 88, 115, 119, 124.
  Whether it stops below 127 is not yet known. The experimental `fl26hdr192.lua`, which our
  current test world runs, raises the ceiling to 192 and leaves far more room. Long-running worlds are the most useful thing
  you can report — see the [testing guide](docs/testing-guide.md).
- **The game crashes now and then inside its own protected code** (fault offsets
  `0x84ed4c0`, `0x131cc313`, `0x18ecc042`), while a scene is being set up: generating a
  season, loading a match, a season rollover. On 2026-09-24 that was five times in about four
  hours of simulated play. **Two of them are the game's own:** on 2026-09-24 a stock game,
  with none of our modules and no added world, crashed at `0x131cc313` on the first match
  day and, in a second run, at `0x1fea5ba` while loading a live match (the crash
  `fl26nullguard.lua` catches); `0x18ecc042` at start-up also happens on a stock game.
  `0x84ed4c0` has not been seen on a stock game yet (about an hour and a half tried), so it
  is still open. The saved season is not damaged: reload and carry on, and save often.
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
  league is simply mislabelled, or missing, in that one menu.
- **Promotion and relegation between the new leagues works, with experimental modules
  only.** Of the 214 shipped rulebooks only eleven carry a promotion or relegation link at
  all, and none of them chains three tiers. On its own the engine moves clubs across every
  other joint of a chain; the rank field is **two bits**, so a third, fourth and fifth
  division look the same; and France and Italy are left out of the European season end. Each
  has an experimental module (`fl26rank` + `fl26deeprank`, `fl26chain`, `fl26seasonend`), and
  together they worked at the 2026-09-23 rollover (see Works). Their lists carry our world's
  league ids and must be edited for yours. Still wrong: Ligue 2 came out of that rollover
  with 21 clubs.
- Continental places for new leagues: done only through the experimental `fl26swiss.dll`,
  whose UEFA access list names our world's leagues. Without it, new clubs can end up in the
  Champions League anyway when their league is built as a first division in a shipped
  country — see [known-issues.md](docs/known-issues.md).
- New clubs use **placeholder names, cloned kits and cloned squads**. This project proves the
  capacity; dressing the clubs is ordinary Team.bin / kit editing on top of it.
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
- Windows. The tools were only ever run on Windows.

## Quick start

Never done this before? Follow [docs/beginners-guide.md](docs/beginners-guide.md) instead;
it is the same route, one small step at a time.

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

Renaming the new clubs, editing their players, and whether they show up in Edit mode: see [docs/faq.md](docs/faq.md).

## Reporting

Open a GitHub issue. The [testing guide](docs/testing-guide.md#what-to-send) says exactly
what to attach — in short: your `sider.log`, the crash's *fault offset* from Windows Event
Viewer, how you built your world (the `mkworld.py` line and what it printed), and the save
file if the problem is reproducible from a save.

## Layout

```
sider/              fl26caps.lua (generated patch set), the null guards, fl26hdr127.lua,
                    fl26joindll.lua and the compiled fl26join.dll it loads
sider/experimental/ fourteen modules that go further, run on our test world only:
                    192 competitions, the Select Team list (names, slots, club lists),
                    64 regions, a 3-bit league rank and its relegation gate, an August
                    start, season-end promotion through a pyramid (fl26chain.dll),
                    a Super Cup guard, the 2024 European format and league sizes
                    (fl26swiss.dll), country names in Competition Info
tools/              world builders (mkworld, mkplayers, mkcrests, mkkits, mkcup,
                    spreadregions, mkreshape, mkuecl, mkeuropo, mksizes, rename, players,
                    playeredit, playereditor ...),
                    pesdb/CPK readers, the patch-set generator and its checkers
tools/native/       the C source of the four DLLs, their build scripts and checksums
patches/            the patch set as JSON plus the layout tables the generator reads
docs/               step-by-step, install, build-your-world, testing-guide, known-issues,
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
files. Nothing here is derived from anyone else's tool or notes.

The licence asks nothing of you. I do: **if you use these findings, addresses, patch sets
or tools in a mod, credit this work and link back** — see
[Free to use — please credit](#free-to-use--please-credit) at the top. It costs you one
line and it is the only thing asked in return.
