# FootballLife — new leagues (public beta)

[![Join the Discord](https://img.shields.io/badge/Discord-join%20the%20community-5865f2?logo=discord&logoColor=white)](https://discord.gg/StQqtk3G3M)

[![Latest release](https://img.shields.io/github/v/release/Matozanato/FootballLife-new-leagues?display_name=release&label=release&color=2ea44f&logo=github&logoColor=white)](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Matozanato/FootballLife-new-leagues/total?label=downloads&color=2ea44f&logo=github&logoColor=white)](https://github.com/Matozanato/FootballLife-new-leagues/releases)
[![License: MIT](https://img.shields.io/github/license/Matozanato/FootballLife-new-leagues?color=blue)](LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4?logo=windows&logoColor=white)
![Languages](https://img.shields.io/badge/languages-EN%20%C2%B7%20ES%20%C2%B7%20FR%20%C2%B7%20HR-6f42c1)
![Game: Football Life 2026](https://img.shields.io/badge/game-Football%20Life%202026-c0392b)

**📖 Guides, step by step:** [install a ready pack or make your own leagues](guides/README.md) (English · hrvatski · español · português · français)

<div align="center">

## ❤️ Supporters

This is unpaid reverse-engineering work done in spare time.
**They keep it going. Thank you!**

<table>
<tr><td align="center">

### 🏆 Special thanks to the **Ultimate Master League (UML)** crew

who covered a big part of what the project costs

</td></tr>
</table>

<table>
<tr>
<td align="center">⭐<br><b>Thunder105</b><br><sub>the first one ever</sub></td>
<td align="center">⭐<br><b>GutGut</b></td>
<td align="center">⭐<br><b>LaraCroft</b></td>
<td align="center">⭐<br><b>Pierro1912</b></td>
<td align="center">⭐<br><b>David.BDJ</b></td>
<td align="center">⭐<br><b>Facemaker Jacobson</b></td>
<td align="center">⭐<br><b>Cristian B.</b></td>
</tr>
</table>

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-become%20a%20supporter-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/mata28)

</div>

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
> **Never used it? Start here,** every click in order: [install a ready pack](guides/en/install-a-pack.md)
> (you were given a world, a modpack or a `.fl26pack`) · [make your own leagues and packs](guides/en/make-your-own-leagues.md)
> (you pick the leagues). Other languages: [guides/](guides/README.md)
>
> **0.2.0 is the last release with new features.** From here on: bug fixes, about once a week.
> **0.2.3** (same evening) fixes Mod Studio closing or stopping during Build: [changelog-0.2.3](docs/changelog/changelog-0.2.3.md).
>
> **0.2.2** is the big fix update with raised limits (2,400 clubs, up to 97 new leagues).
> Careers saved before 0.2.2 do not load: start a new one after Build. What changed:
> [changelog-0.2.2](docs/changelog/changelog-0.2.2.md) · every version: [changelog](docs/changelog/README.md).
>
> **Discord:** [FL Mod Studio](https://discord.gg/StQqtk3G3M): questions, help, new versions, and new
> GitHub issues posted there as they come in. Bugs still go to a GitHub issue.

This is a **beta**. It is published so that people who mod this game can use it, break it and
tell us where. Read [what works and what does not](docs/known-issues.md) before you start a
long career.

## Documentation

All of it, folder by folder: [docs/README.md](docs/README.md).

- **[Guides](guides/README.md)** in English, hrvatski, español, português and français:
  - **[Install a ready pack](guides/en/install-a-pack.md)**: someone gave you a world or a
    league package; from nothing to a new Master League, every click in order.
  - **[Make your own leagues and packs](guides/en/make-your-own-leagues.md)**: real leagues from
    the NewLife Database, every setting of a league, Build, and sharing what you made.
  - **[Guide to every page](guides/en/mod-studio-guide.md)** of Mod Studio.
- **[Questions](docs/faq.md)**: updating, crashes at start, cups, promotion, what to send when
  something is wrong. **[Known issues](docs/known-issues.md)**: what works, what does not yet.
- **[Changelog](docs/changelog/README.md)**: what each version brought.
- **[Developers](docs/developers/for-developers.md)**: forks, pull requests, the code, the
  manual route with Python. **[Research](docs/research/research-findings.md)**: how the game
  was taken apart, limits and addresses.

## What you can do

**Leagues and countries**

- **Many new leagues** in one world, **10 to 24 clubs** each, playing each other 1 to 4
  times with the real number of rounds (10 clubs four times = 36 rounds). Since 0.2.2 there
  is room for 2,400 clubs in all, and our test world plays 86 new leagues with 1,294 new
  clubs; Build stops with a message when regulation ids or club room run out. Every league
  is selectable in Select Team (250 slots).
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
  with names and portraits (0.1.4), kits lent from the game's clubs or plain kits you can
  change in the game's Edit mode, Paste Image included (0.1.6), and a **formation** per
  league or per club with the first eleven on a pitch (0.1.4).
- **Edit mode keeps what you change on the new clubs** (0.1.8): shirt numbers, formations,
  colours, a squad imported from a .ted file. The game's Edit save has room for 750 clubs and
  its own 749 fill it; `fl26edit.dll` gives it room for 2048 and keeps the clubs past 749 in
  `EDIT00000000.fl26x` beside it. The EDIT file itself stays what the game writes
  ([#55](https://github.com/Matozanato/FootballLife-new-leagues/issues/55)).
- **Real clubs and players** from the **NewLife Database** (0.1.5.5): pick a league and it
  becomes a new league with its real clubs and squads — names, birth dates, positions,
  ratings on the game's scale, club colours, ids that stay the same in every version. A club
  with no crest gets a shield in its colours and the game's kit closest to them. A separate
  download on our [Discord](https://discord.gg/StQqtk3G3M); version 1.1 (2026-10-01) is the
  2026/27 season, with the summer transfers and the new divisions.
  Leave clubs out of a league or bring in clubs of other leagues (0.1.7).
- **Faces**: new players get a face that fits their nationality, and any player can get a
  **portrait** instead of a 3D face (0.1.5.5).
- **Regens** in Master League get a new name, a new potential and a new face (0.1.5.5).
- **Clubs in no league** (0.1.8): one club, or a few, without a league around them -- BATE
  Borisov alone -- in one of the game's groups for clubs that play in no league (*Other
  European teams*, *Other Latin American teams*, *Classic Teams* ...), with names, crests,
  kits, a manager and players like any new club.
- **Clubs the game already has** in your new leagues. When such a club plays somewhere in the
  game, you pick who takes its place there, so no competition of the game changes size (0.1.4). Move
  a new club to another new league, or swap two clubs of the game's leagues -- a promoted one for a
  relegated one (0.1.7). A club in a pre-season tournament keeps playing it, and *Edit club* renames
  a club of the game right on *New clubs* (0.1.7).
- **Rename** the game's own leagues and clubs, with new logos and crests.
- **Edit every player of every club**: name, number, positions, abilities, skills, rating,
  face, squad order, best eleven, squad level; CSV export and import.
- **Squads from a table**: any table of players — typed by hand, copied off a website, a
  Football Manager or EA FC export — becomes a club's squad.
- **Transfers** between any two clubs and **national team call-ups** (0.1.4); your own
  **club and player ids** for kit, crest and face packs made for a certain id (0.1.4), and a
  Player ID column for minifaces made for new players (0.1.5.5).

**Cups and continents**

- The **2024 European format**: Champions League and Europa League with a league phase of 36,
  the February play-off and a fixed knockout bracket, and a new **Conference League**. Filled
  from a UEFA access list from the second season; in the first, by squad strength. The draw
  keeps clubs of one country apart as UEFA does (0.1.4). **August qualifying** (0.1.7): up to
  three rounds of 16 clubs over two legs -- second qualifying round, third, play-off -- for the
  Champions League (losers drop to the Europa League), Europa League (losers to the Conference
  League) and Conference League; a world gets as many rounds as its European places fill. Name
  the Conference League yourself (0.1.7).
- **Continental places** for your leagues: Champions League, Europa League, Conference League;
  AFC Champions League, Champions League Two and the AFC Challenge League (0.2.0); Copa
  Libertadores (also its qualifying round, 0.1.4) and Copa Sudamericana; CAF Champions League
  and CAF Confederation Cup, and the CAF Super Cup between their winners (0.1.6); the CONCACAF
  Champions Cup and the OFC Champions League (0.2.0). The ones the game does not have are built
  with your world, and their champions go to the game's Club World Cup. The **game's own leagues** can get their European places changed too (0.1.7).
  **UEFA ranking** (0.1.7): put the world's European leagues in order and each gets its places
  from UEFA's key; **South American places** lists the Libertadores and Sudamericana places of
  every South American league, the game's and yours. **First-season European clubs** (0.1.8):
  pick by hand who plays the three European league phases in a new career's first season.
- A country's own **national cup** (any size up to 44 clubs, with byes like the FA Cup, 0.1.4)
  and **super cup**, a **league cup** (the clubs past 16 through a pre-round, 0.1.7), and **pre-season cups** of 4 or 8 invited clubs in July,
  each with your own **logo** (0.1.5.5). A **league cup** for the game's own countries (the
  Carabao Cup), and a super cup where the game has none (Scotland, Greece ...) (0.1.7).
- **Rename** any cup or continental competition of the game, and the ones the world builds,
  with your own logo (0.1.7); the game's leagues and clubs too.
  A new second division under a country the game has goes into that country's cup (0.1.4).
  The national cup of a new country is tested over two full seasons: it rebuilds from the
  current first division after every promotion and relegation (issue #46).
- **Europe only** (0.1.4): just the new European format, no new leagues.

**Everything else in your game folder**

- **Install mods** by dropping them on the window (zip, 7z, folder, .lua, .cpk): it says what
  each part is and where it goes, merges content-server map files into yours, and every mod it
  installs can be removed again.
- **Content servers** (stadiums, kits, balls, commentary, music, scoreboards, menus ...) with
  their map files edited as tables. A new club's **home stadium** is picked in Edit club and
  written for you when the world is switched on (0.1.7).
- **Sider setup**: content folders and Lua modules on, off and in order; profiles; a restore
  point for every file it changes; a diagnostics report to paste into a bug report. The health
  check also catches a database mod (UML ...) that hides the world's tables (0.1.7).
- **League packages** (`.fl26pack`): a modder makes a league once — clubs, names, crests,
  logos, squads, faces — and anybody adds it to their own game. Adding a newer version replaces
  the old one (0.1.7).
- English, Croatian, Spanish, Brazilian Portuguese and French.


Every version and what it brought: [docs/changelog](docs/changelog/README.md).

> **Rather do it by hand, with Python?** [docs/developers/by-hand.md](docs/developers/by-hand.md)
> is the whole manual route on one page: install the modules, build leagues, put one in a
> country of your choice, the new European format, and every world-building option.

## The people who made this better

This project is tested in the open, and every fix in it since the first beta traces back to
someone who played a season, wrote down what happened and sent it. Thank you, all of you.

### vmardonesdev: the tester this project owes the most

**vmardonesdev** (Vicentico12 and a moderator on the Discord) has done more for this project than anyone besides its author. Twenty-one of
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
- [#44](https://github.com/Matozanato/FootballLife-new-leagues/issues/44), [#45](https://github.com/Matozanato/FootballLife-new-leagues/issues/45), [#46](https://github.com/Matozanato/FootballLife-new-leagues/issues/46), [#47](https://github.com/Matozanato/FootballLife-new-leagues/issues/47): new clubs missing from Players, Apertura/Clausura with no table or
  calendar, the national cup over two full seasons and the Kick Off / Edit order (0.1.3.1).
- [#49](https://github.com/Matozanato/FootballLife-new-leagues/issues/49), [#52](https://github.com/Matozanato/FootballLife-new-leagues/issues/52): the Player ID column and random looks for generated players.
- [#61](https://github.com/Matozanato/FootballLife-new-leagues/issues/61), [#63](https://github.com/Matozanato/FootballLife-new-leagues/issues/63), [#64](https://github.com/Matozanato/FootballLife-new-leagues/issues/64): NewLife tested on a whole world: duplicated faces, the Game Plan lag of
  `fl26regen`, minifaces that did not match and the game clubs' starting elevens.
- [#66](https://github.com/Matozanato/FootballLife-new-leagues/issues/66), [#68](https://github.com/Matozanato/FootballLife-new-leagues/issues/68), [#69](https://github.com/Matozanato/FootballLife-new-leagues/issues/69): Libertadores qualifying places, a Brazilian cup taken over by a new lower
  division and the February to December season.
- [#74](https://github.com/Matozanato/FootballLife-new-leagues/issues/74), [#77](https://github.com/Matozanato/FootballLife-new-leagues/issues/77), [#78](https://github.com/Matozanato/FootballLife-new-leagues/issues/78): the Croatian cup bracket crash and full 0.1.7 runs with Croatia, UEFA and
  the league cup of a game country.
- [#87](https://github.com/Matozanato/FootballLife-new-leagues/issues/87), [#89](https://github.com/Matozanato/FootballLife-new-leagues/issues/89), [#90](https://github.com/Matozanato/FootballLife-new-leagues/issues/90), [#92](https://github.com/Matozanato/FootballLife-new-leagues/issues/92), [#93](https://github.com/Matozanato/FootballLife-new-leagues/issues/93): clubs missing in Kits, the UEFA ranking moving European places,
  Kit Server kits of NewLife clubs, leagues under a second division and a game country with
  only a league cup.
- [#112](https://github.com/Matozanato/FootballLife-new-leagues/issues/112), [#119](https://github.com/Matozanato/FootballLife-new-leagues/issues/119), [#122](https://github.com/Matozanato/FootballLife-new-leagues/issues/122): Paste Image on the base kits of added clubs, a combined South American
  world whose Libertadores did not use the final table, and the cup draw crash on a new career.
- [#124](https://github.com/Matozanato/FootballLife-new-leagues/issues/124), [#127](https://github.com/Matozanato/FootballLife-new-leagues/issues/127), [#131](https://github.com/Matozanato/FootballLife-new-leagues/issues/131): the 34 extra leagues of the FL26 Modpack tested one by one, and the
  Libertadores places after a first season.
- On the Discord, as Vicentico12: European places for the game's own leagues, which 0.1.7's
  UEFA ranking gives, a logo for the Copa Sudamericana, the calendar that stopped showing its
  events after 0.2.0 (with a save to test it on), the July leagues of the modpack that never
  reach the hub, and Norway's league that never started
  ([#124](https://github.com/Matozanato/FootballLife-new-leagues/issues/124)).
- Code, too: [#139](https://github.com/Matozanato/FootballLife-new-leagues/pull/139) gives a
  February-December league its national cup and super cup (`fl26swiss`, `fl26join`, the League
  Builder and a test of its own), in 0.2.2. And
  [#146](https://github.com/Matozanato/FootballLife-new-leagues/pull/146), with nissindiaz: the modern CONMEBOL cups (Libertadores qualifying in
  phases, the pre-Sudamericana, the Recopa and the Sudamericana play-off), going into 0.2.5.
- The night 0.2.2 came out: the traceback that showed why Build stopped for everyone whose game
  is not in `C:\Football Life 2026`, sent the moment it happened, and the fix tested and
  confirmed within minutes, so 0.2.3 could go out for everyone the same evening.

If you use anything from this repository, vmardonesdev's name belongs next to it.

### Alikhaled_727: the reports from outside Europe

**Alikhaled_727** (Evo-Web; Mohamed_248 on GitHub) builds the leagues nobody else tests (Saudi Arabia, Egypt,
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
- a league of 20 whose league cup left four clubs out, and a league round played on a cup
  day: the league cup pre-round and the split-date fix of 0.1.7
  ([#70](https://github.com/Matozanato/FootballLife-new-leagues/issues/70)).

In 0.2.0 a whole African world: the Egyptian split table, the promotion arrows, the league cup
played after the Super Cup and the continent's best player ([#70](https://github.com/Matozanato/FootballLife-new-leagues/issues/70)).

Asian leagues with their own continental places, and with them the AFC Champions League Two
in the League Builder, were Alikhaled_727's idea too.

### vector360: the European format, checked against the real one

**vector360** (Evo-Web, Discord) played the new European format season after season and
compared it with the real UEFA one:

- big clubs such as PSG, Real Madrid and Inter in the Conference League in a first season:
  the reason the first season is ordered by squad strength;
- a 36/36/36 list of the real 2026/27 clubs, the reason `fl26swiss` can take a first-season
  list (`fl26swiss-first.txt`);
- Manchester United drawn against Manchester City in the league phase, and the request for the
  rest of UEFA's draw rules, which the draw follows since 0.1.4: no club meets a club of its own
  country and at most two of any other ([#15](https://github.com/Matozanato/FootballLife-new-leagues/issues/15));
- the request for a Carabao Cup, which became the league cup for the game's own countries in
  0.1.7, and for a way to rename the Conference League.

### jibibi: tester, moderator and the community's first answer

**jibibi** (Evo-Web; moderator on the Discord) has been there from the first public builds,
testing Mod Studio on a real, heavily modded game and helping everyone else get theirs working:

- the modules tested alongside a full French patch and the kit server, with the logs that show
  how the patch's own roots and the new clubs' kit names have to sit next to ours;
- Sider in a folder with another name ([#28](https://github.com/Matozanato/FootballLife-new-leagues/issues/28)) and four Sider folders one level
  down (`sider\patch 1` ... `sider\patch 4`): why Mod Studio finds Sider by its `sider.ini`,
  whatever the folder is called and wherever it sits;
- faces by nationality ([#52](https://github.com/Matozanato/FootballLife-new-leagues/issues/52)): the skin colour and face picked from a player's
  country, the idea behind new players getting a face that fits their nationality;
- the Players page on a 1366x768 screen, a whole Scottish pyramid of NewLife leagues under the
  game's Premiership built step by step, NewLife ratings that were off in a Romanian second
  division, and sorting the NewLife table by any column (0.2.0);
- material for NewLife and the modpack: the real 2026/27 UEFA lists, Croatian clubs and the
  skills and positions of a player scraper;
- day after day on the Discord: answering members' questions about install order, face packs
  and other patches before anyone else gets to them, and keeping the server tidy.

### novarama: moderator on the Discord, with a developer's eye

**novarama** joined jibibi and vmardonesdev as a moderator on the Discord on 11 October 2026,
and looks at Mod Studio the way a professional developer does:

- the Bundesliga 2 crests missing from NewLife 1.3, which put the crests back into every
  NewLife build;
- NewLife's refresh of the game's leagues getting in the way of a league added after it
  (French National taking a club Ligue 2 had already turned into another);
- the most thorough answer to the community poll: what is not clear in the interface for
  someone who is not a modder, why replacing a club that plays in another league should not
  be the user's job, a list of every change made to a world, restore points, and a small
  separate installer just for league packs and the modpack;
- every day on the Discord: answering members, testing what they report and keeping the
  channels in order.

### Amir: Mod Studio, tested release by release

**Amir** ([AmirPjanic](https://github.com/AmirPjanic)) tests Mod
Studio release by release and asks for what a modder actually needs:

- the Team ID and League ID columns, the division shown next to each league, nationality typed
  by name, removing players from new clubs, club names with č, ć, š, ž, đ and the managers'
  names of new clubs ([#23](https://github.com/Matozanato/FootballLife-new-leagues/issues/23));
- a world with leagues of 26 clubs: the reason 0.1.4 lets a national cup have any number of
  clubs;
- the "set-hook signature mismatch" report, which showed two of our modules hooking the same
  function in the wrong order, fixed in 0.1.3, and a second league with no ID, which is why
  Mod Studio now says when a league is not built yet;
- the national team editor, transfers between clubs, the formations of new clubs and a Balkan
  friendly cup in July.

### victormican: South America from top to bottom

**victormican** ([victormican](https://github.com/victormican)) tests Mod Studio on a South
American world and reports what breaks there:

- the Asia-Oceania national teams and the Classic Teams disappearing from Kick Off
  ([#26](https://github.com/Matozanato/FootballLife-new-leagues/issues/26)), the teams in no league that could not be found
  ([#25](https://github.com/Matozanato/FootballLife-new-leagues/issues/25)) and the language switch ([#24](https://github.com/Matozanato/FootballLife-new-leagues/issues/24));
- a Colombian second division that plays January to December ([#27](https://github.com/Matozanato/FootballLife-new-leagues/issues/27)), and
  the Torneo BetPlay listed after the MLS in Select Team, fixed in 0.1.4
  ([#38](https://github.com/Matozanato/FootballLife-new-leagues/issues/38));
- the Kick Off order that did not follow Mod Studio's ([#30](https://github.com/Matozanato/FootballLife-new-leagues/issues/30)), the limit of
  leagues ([#39](https://github.com/Matozanato/FootballLife-new-leagues/issues/39)) and the season and league choices of a new league
  ([#56](https://github.com/Matozanato/FootballLife-new-leagues/issues/56));
- the League window that did not fit the screen, the idea of a separate editor for
  competitions, and Select all / Select none for league packages
  ([#34](https://github.com/Matozanato/FootballLife-new-leagues/issues/34));
- a new club in place of a game club, the other South Americans and Europeans missing in
  Select Team, a plan that would not build and the new South American cups in Cup mode
  ([#72](https://github.com/Matozanato/FootballLife-new-leagues/issues/72), [#73](https://github.com/Matozanato/FootballLife-new-leagues/issues/73), [#80](https://github.com/Matozanato/FootballLife-new-leagues/issues/80), [#81](https://github.com/Matozanato/FootballLife-new-leagues/issues/81));
- the game's clubs in no league, quicker checks from the NewLife Database and the Uruguayan
  format ([#82](https://github.com/Matozanato/FootballLife-new-leagues/issues/82), [#83](https://github.com/Matozanato/FootballLife-new-leagues/issues/83), [#99](https://github.com/Matozanato/FootballLife-new-leagues/issues/99));
- 0.1.9 tested to its limits: NewLife clubs in a recipe, the order of leagues and of
  countries, the rest of the leagues not updating, reordering new clubs, the limit of 38
  leagues, the "Others" groups and a crash ([#101](https://github.com/Matozanato/FootballLife-new-leagues/issues/101), [#105](https://github.com/Matozanato/FootballLife-new-leagues/issues/105), [#107](https://github.com/Matozanato/FootballLife-new-leagues/issues/107), [#113](https://github.com/Matozanato/FootballLife-new-leagues/issues/113), [#114](https://github.com/Matozanato/FootballLife-new-leagues/issues/114), [#115](https://github.com/Matozanato/FootballLife-new-leagues/issues/115), [#116](https://github.com/Matozanato/FootballLife-new-leagues/issues/116), [#117](https://github.com/Matozanato/FootballLife-new-leagues/issues/117), [#120](https://github.com/Matozanato/FootballLife-new-leagues/issues/120)).

### jyanj083-dotcom: Peru and the Libertadores, tested to the end

**jyanj083-dotcom** ([jyanj083-dotcom](https://github.com/jyanj083-dotcom)) builds Peruvian
and other Latin American worlds and writes up every bug with screenshots:

- the empty Libertadores qualifying places, the wrong continent in League Info, player names
  and ratings that could not be changed and the Conference League switch that broke the other
  two ([#33](https://github.com/Matozanato/FootballLife-new-leagues/issues/33));
- the DFB Pokal that ignored a new 2. Bundesliga ([#32](https://github.com/Matozanato/FootballLife-new-leagues/issues/32)) and the League
  window on a 1080p screen ([#35](https://github.com/Matozanato/FootballLife-new-leagues/issues/35));
- an Apertura/Clausura with a liguilla of 8 that made no calendar ([#40](https://github.com/Matozanato/FootballLife-new-leagues/issues/40)),
  and the kits, the Apertura/Clausura table and the moved clubs in Kick Off of Latin American
  leagues ([#57](https://github.com/Matozanato/FootballLife-new-leagues/issues/57));
- Liga 1 and Liga 2 of Peru with the NewLife Database ([#60](https://github.com/Matozanato/FootballLife-new-leagues/issues/60)), crests kept
  across builds ([#67](https://github.com/Matozanato/FootballLife-new-leagues/issues/67)) and the competition places of new South American
  leagues ([#71](https://github.com/Matozanato/FootballLife-new-leagues/issues/71));
- league creation bugs, kits of new clubs past id 65535 and random managers
  ([#79](https://github.com/Matozanato/FootballLife-new-leagues/issues/79), [#85](https://github.com/Matozanato/FootballLife-new-leagues/issues/85), [#88](https://github.com/Matozanato/FootballLife-new-leagues/issues/88), [#91](https://github.com/Matozanato/FootballLife-new-leagues/issues/91));
- the Copa Peru crash after its first round, promotion with Apertura/Clausura, the Be a
  Legend crash of 0.2.0 and a long list of bugs from 0.2.1 ([#95](https://github.com/Matozanato/FootballLife-new-leagues/issues/95), [#106](https://github.com/Matozanato/FootballLife-new-leagues/issues/106), [#125](https://github.com/Matozanato/FootballLife-new-leagues/issues/125), [#132](https://github.com/Matozanato/FootballLife-new-leagues/issues/132)).

### Everyone else who helped

- **Stagnant09**: the flags in the Select Team list. The idea, the hook on the
  slot-to-country lookup and the first working version
  ([#11](https://github.com/Matozanato/FootballLife-new-leagues/issues/11));
  `fl26comptab.lua` and `tools/mkflags.py` are built on it.
- **AlexRufolo**: asked to pick the clubs of the European cups by hand, which became Mod
  Studio's **First-season European clubs** (0.1.8); asked for clubs listed A-Z, and found the
  Korean January-December league that never started; a second-season crash, Serie C with no
  promotion and two Carabao Cups ([#97](https://github.com/Matozanato/FootballLife-new-leagues/issues/97), [#98](https://github.com/Matozanato/FootballLife-new-leagues/issues/98), [#118](https://github.com/Matozanato/FootballLife-new-leagues/issues/118)).
- **pioup38**: the first report from a different game build and a clean configuration
  ([#3](https://github.com/Matozanato/FootballLife-new-leagues/issues/3)), and players
  created from a CSV file ([#58](https://github.com/Matozanato/FootballLife-new-leagues/issues/58)).
- **bobzera** (Evo-Web): brought the "ACL71" kit problem into the open, new clubs past id
  65536 showing only the default kit, and worked on a fix of their own. That problem is the
  one `tools/mkkits.py` now solves by naming the kit files the way the engine looks them up.
- **spursfan07**: one of the first to build leagues by hand in the game's database files and
  bring every wall here: a league missing from the menu (its region had no label), clubs
  with blank names, and fixture dates that turned out to come from the regulation id
  itself. Those questions mapped a good part of what this project is built on, and
  spursfan07 is now testing the modules.
- **Gabyyy2008** ([Gabyyy2008](https://github.com/Gabyyy2008)): Apertura and Clausura in
  Argentina and Venezuela, and the same clubs playing the Libertadores and the Sudamericana
  ([#37](https://github.com/Matozanato/FootballLife-new-leagues/issues/37)).
- **alexfe87** ([alexfe87](https://github.com/alexfe87)): asked for the new UEFA formats on
  their own, without any new league, which is why 0.1.4 has a Europe-only build
  ([#36](https://github.com/Matozanato/FootballLife-new-leagues/issues/36)), and the
  question of a clean install ([#130](https://github.com/Matozanato/FootballLife-new-leagues/issues/130)).
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
- **daemonkf-a11y** ([daemonkf-a11y](https://github.com/daemonkf-a11y)): a database mod that
  renamed the Europa League and stopped the build, and a Romanian split too long for the
  calendar, and a European-only world whose leagues got no schedule
  ([#54](https://github.com/Matozanato/FootballLife-new-leagues/issues/54)), and the same
  match shown twice in the hub, followed over two versions.
- **alby171994** ([alby171994](https://github.com/alby171994)): an exhibition-only world
  that left every league without a schedule, narrowed down to one module
  ([#53](https://github.com/Matozanato/FootballLife-new-leagues/issues/53)), and the Edit
  mode changes to new clubs that were never saved
  ([#55](https://github.com/Matozanato/FootballLife-new-leagues/issues/55)), and faces and hair
  reset to the dummy ([#104](https://github.com/Matozanato/FootballLife-new-leagues/issues/104)).
- **Jabo9** (Evo-Web): saw a new League One take the FA Cup from the Premier League and the
  Championship ([#68](https://github.com/Matozanato/FootballLife-new-leagues/issues/68)),
  and asked for new players to keep the look the game gives them, now a switch in More.
- **n1ne** (Discord): follows the work closely and asks the questions that show where the
  docs are not clear yet, such as how the European competitions get their clubs.
- **mushroomwehk** ([mushroomwehk](https://github.com/mushroomwehk)): a new 12-club league
  that started on matchday 3 ([#41](https://github.com/Matozanato/FootballLife-new-leagues/issues/41)),
  the request for the game's own clubs in new leagues ([#42](https://github.com/Matozanato/FootballLife-new-leagues/issues/42)),
  an Asian league with a South American description ([#43](https://github.com/Matozanato/FootballLife-new-leagues/issues/43))
  and Edit mode on a database of more than 30,001 players ([#65](https://github.com/Matozanato/FootballLife-new-leagues/issues/65)).
  As Gu on the Discord: the AFC Challenge League, Asian leagues by strength, the regen faces past
  30,023 players, and Create Edit Data that made no save in a big world (the managers table
  `fl26edit` widens in 0.2.2).
- **pepponeee98** ([pepponeee98](https://github.com/pepponeee98)): leagues that disappeared
  and a crash ([#62](https://github.com/Matozanato/FootballLife-new-leagues/issues/62)), and free
  agents created when a new world is loaded ([#96](https://github.com/Matozanato/FootballLife-new-leagues/issues/96)).
- **okarin-hub** ([okarin-hub](https://github.com/okarin-hub), Okarin on the Discord): an
  Indonesian league and the start-up crashes ([#59](https://github.com/Matozanato/FootballLife-new-leagues/issues/59)), and the
  Kit Server kits of a new club ([#103](https://github.com/Matozanato/FootballLife-new-leagues/issues/103)).
- **iptory** ([iptory](https://github.com/iptory)): the Argentinian format, two zones of 15
  and a play-off of eight ([#48](https://github.com/Matozanato/FootballLife-new-leagues/issues/48)).
- **JamesNotLike** (Discord): LaLiga and Ligue 1 gone from Select Team, followed patiently
  through log after log to four mods that wrote into the same empty spot of the game as
  `fl26caps`; the reason 0.1.7 moves our code to a page of its own.
- **KamyFC** (Discord): built an Asian pyramid step by step and asked every question on the
  way, which shows where the Club of the game window has to explain itself better.
- **San Marino** (Discord): NewLife players that were copied instead of moved, the reason
  0.1.7 moves the game's own players, and a Polish cup of 36 whose bracket lost clubs.
- **lukewcfc** (Discord): option files next to the new European cups.
- **mauro1977doni** (Discord): a Europe-only world with an empty schedule.
- **N3RO** (Discord): asked for the Czech Chance Liga.
- **Hector** (Discord): crests and logos for the NewLife Database.
- **LaraCroft** (Discord): asked for BATE Borisov on its own, which became 0.1.8's
  **Clubs in no league**, and for the clubs of a league listed A-Z; found the game's clubs
  showing up in two Dutch leagues at once. In the 0.2.4 beta: Switzerland stuck to Greece again in
  Select Team, a Player editor rating that came out lower in the game, and the wish to open an
  installed world in Mod Studio.
- **Xxspedd** (Discord): shared his own crest, kit, squad and rating scripts; the idea of
  matching a folder of crests to clubs by name (0.1.8's Import crests) is his, and he pointed
  out the missing third kit. 0.2.0's kits made from plain pictures (**Import kits** with
  `p1.png`, `g1.png` ...) use his png -> ftex conversion, from his kit tool, given to Mod Studio.
  In the 0.2.4 beta: seven Serie B clubs of the game that NewLife did not pair, and the old crest
  that stayed on a replaced club.

- **DavidBDJ** ([DavidBDJ](https://github.com/DavidBDJ)): the UEFA league phase as one scrolling
  table in Competition Info (the game's league standings page for the 36 clubs instead of four
  group pages; reverse engineering, code and tests are his, in `fl26swiss.c`). Before that, complete test reports with saves
  and logs from two seasons in Austria
  ([#128](https://github.com/Matozanato/FootballLife-new-leagues/issues/128),
  [#129](https://github.com/Matozanato/FootballLife-new-leagues/issues/129)): the kits of new
  clubs that went to a folder the Kit Server does not read, and the European qualifiers. In the
  0.2.4 beta: the main menu background stuck on a league, 183 players all named "Tahj" in the
  modpack, and the first full report on NewLife 1.5.
- **B2Y26Arabia** ([B2Y26Arabia](https://github.com/B2Y26Arabia)): found the Kick Off > Cup
  crash with the Champions League of 36
  ([#100](https://github.com/Matozanato/FootballLife-new-leagues/issues/100)), plus new leagues
  missing in Edit mode and the skin colour of linked faces; a club crest that was not saved
  ([#140](https://github.com/Matozanato/FootballLife-new-leagues/issues/140)) and a group of clubs with no league that stayed "not built yet"
  ([#144](https://github.com/Matozanato/FootballLife-new-leagues/issues/144)).
- **rickydicky4444** and **MIQABARI**: the UECL gameweeks shown wrong in the calendar
  ([#75](https://github.com/Matozanato/FootballLife-new-leagues/issues/75)) and a Master League
  creation crash ([#123](https://github.com/Matozanato/FootballLife-new-leagues/issues/123)).
- **rwee** (Discord): the Champions League's January matchday landing on a league day in leagues
  of 18 and 20, a full world recipe to reproduce with, and the squad limit regression of 0.1.8;
  two full seasons of a 60-league world, cup by cup.
- **Risto** (Discord): club by club corrections for the FL26 Modpack's smaller countries
  (Armenia, Moldova, the Faroe Islands ...) and the duplicate players in NewLife.
- **Yanis** (Discord): `fl26caps` below the other modules in sider.ini, which led to Switch on
  putting it first.
- **LumpierTheGunner** (Discord): the Kit Server crash with editable kits (now caught by
  `fl26kitguard`) and the idea of a page with every competition id.
- **Bon Kirk** (Discord): the recipe changes lost on closing, which Mod Studio now asks about.
- **wishfulshot** (Discord): an old league package that stopped Check the plan, the case behind
  packages with clubs from outside NewLife.
- **beny609o** (Discord): Import kits keeping a broken map line, now replaced.
- **Nickdaw** (Discord): patient crash reports on the modpack world.
- **the_pelado** (Dream Patch): a full write-up of how the game picks trophy ceremonies, the
  starting point for ceremonies of added competitions.
- **capital030** (Discord): the idea of packages without squads that only add to leagues already
  there, and offered logos for the community.
- **nissindiaz** ([nissindiaz](https://github.com/nissindiaz)): code for the calendar patch set
  ([#135](https://github.com/Matozanato/FootballLife-new-leagues/pull/135): three sites that read
  a day's events and five unwind words the survey missed, so the calendar shows its event icons
  again) and `patchset.py --calendar-ids N` for another calendar day size, with the module
  constants it needs ([#136](https://github.com/Matozanato/FootballLife-new-leagues/pull/136)),
  both in 0.2.2; the Copa do Nordeste and, with vmardonesdev, the modern South American cups
  ([#146](https://github.com/Matozanato/FootballLife-new-leagues/pull/146), going into 0.2.5); and Master League removing clubs it took for
  duplicates.
- **Julio** (juliorivera10, Discord): players imported with a Spanish foot column all came out
  right-footed; Import players reads "Pie", "Zurdo", "Diestro" ... since 0.2.2.
- **Uncle Lanscilo** (lanscilo, Discord): help for other players in #support, adding leagues
  and reading their Build logs with them; Sparta gone from the list after a club swap, and a
  club NewLife put in two leagues.
- **vmican** (Discord): a long run of 0.2.4 beta reports: Build stopping on a club of more than
  40 players and the crash after it, a package adding a game club twice, Install on a nearly full
  C:, the final check after Import your world, and "New club here" doing nothing; and the
  requests for a warning when a club is already in another league and a tick to leave a league
  out.
- **GiorgiM** (Discord): a Georgian world that crashed in its second season, with the saves and
  logs that led to a super cup with no clubs in it.
- **bythezl19** (Discord): the second season's European places given by squad strength instead
  of the table, and the Europa League qualifiers skipped, with logs.
- **quicksite** (Discord): a zip that could not be dropped on the window, and a modpack
  scoreboard that never showed.
- **fjchivvdub** (Discord): Serbian clubs in Argentinian kits, and a Master League with Partizan
  stuck after the last cutscene.
- **ZeDosCaes21** (Discord): Import kits with the game under Program Files, which ended in a raw
  "access denied".
- **ELBastos** (Discord): the modpack's kits not loading, and an Install of a big zip cut short.
- **Konkubent**, **beni_93** and **jojofiaz** (Discord): modpack clubs in the wrong kits, from a
  world that had lost its kit data.
- **Tysonche35** (Discord): the Serbian Superliga club by club, and African clubs without
  players that crashed the club select.
- **diwwanmago** (Discord): a modpack crash on a new Master League, followed to the end.
- **bikolunar42** (Discord): a UEFA league phase that was never drawn, down to old module lines
  in sider.ini, and the event icons gone from Advance time.
- **lmazot** (Discord): Mod Studio closing during Build (since 0.2.3 it writes `crash.log`),
  and the Dutch and national team matches that were skipped.
- **Erax** (Discord): an invented league of two divisions whose league cup broke, a stadium left
  dark, and the Best Player in Europe award going to the wrong player.
- **juanjose6124** (Discord): a duplicated club in the beta, with the Build logs to check it.
- **antoniodias_pt** (Discord): João Cancelo a free agent in the game while Mod Studio had him
  at Barcelona, the case behind NewLife keeping the players of a club outside its top 30.
- **bruce_wayne** (avro_constantine, Discord): Build stopping on a club of more than 40, and a
  crash at 99% while saving a new Master League.
- **Sasukidas** (Discord): an empty Copa Sudamericana in the first season.
- **diablofumao** (Discord): an exhibition with modpack clubs that never started, with logs.
- **gxldemorci** (Discord): a best eleven of only defenders after a faces update.
- **General Kreutaa** (Discord): the scoreboard of another country's league in the modpack.

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

## Reporting

Open a GitHub issue. From Mod Studio, **Diagnostics → Run the checks → Copy a report** puts
everything useful in the clipboard; paste it into the issue. The
[testing guide](docs/developers/testing-guide.md#what-to-send) says what else helps: your `sider.log`, the
crash's *fault offset* from Windows Event Viewer, your recipe (or how you built your world),
and the save file if the problem can be repeated from a save.

For questions that are not bugs (how do I ..., does this work with ...), ask on
[Discord](https://discord.gg/StQqtk3G3M).

## Contributing

You do not need your own separate Mod Studio to add something. Send it to this one with a pull
request and everyone gets it in the next release:

1. **Fork** the repository. On GitHub that is just your working copy, not a new project.
2. Make your fix or feature there, on a branch.
3. **Open a pull request.** We read it, test it in the game and may ask for small changes;
   you push them to the same branch and the pull request updates itself.
4. We **merge** it, it ships with the next release, and you go in the credits.

Bug fixes and new features are both welcome this way: 0.2.0 was the last release where *we*
add features, not the last one that gets them. Before something big, open an issue or ask on
[Discord](https://discord.gg/StQqtk3G3M) so two people do not build the same thing.
[docs/developers/forking.md](docs/developers/forking.md) and the [fork chapters](docs/developers/fork/) explain the code; they
work the same for a pull request as for a fork. For `sider/` and `patches/`, describe the
disassembly evidence in the pull request the way the module headers do.

## Support

Everything here is free and MIT-licensed. Weeks of disassembly, unattended test seasons and
crash dumps went into it, and there is more to do (the crashes in the game's protected code,
the African leagues' League Info panel, more competitions and formats). If you want to help it
along: **[ko-fi.com/mata28](https://ko-fi.com/mata28)**. Testing and good bug reports help just
as much — see the [testing guide](docs/developers/testing-guide.md).

Thank you to everyone who has: **Thunder105**, **GutGut**, **LaraCroft**, **Pierro1912**, **David.BDJ**, **Facemaker Jacobson** and **Cristian B.** Supporters are listed at
the top of this page.

## Licence and credits

MIT — see [LICENSE](LICENSE). Football Life 2026, PES 2021 and Sider belong to their
respective authors; nothing of theirs is redistributed here.

The reverse engineering was done from scratch against the game's executable and data
files. Nothing here is derived from anyone else's tool or notes, except where a contributor
is named.

Contributors, and what each of them did, are listed in
[The people who made this better](#the-people-who-made-this-better) near the top: above all
**vmardonesdev** and **Alikhaled_727**, **vector360** and **jibibi**, and **Stagnant09**, **pioup38**, **bobzera**,
**spursfan07**, **Amir**, **victormican**, **Alby17**, **jyanj083-dotcom**, **Gabyyy2008**, **alexfe87**,
**ThanosMJ**, **NudnyNick999**, **bnaanana**, **dannydecai**, **astyleUZ**, **Zega_1991**, **daemonkf-a11y**, **alby171994**, **Jabo9**, **Xxspedd**, **n1ne**, **LaraCroft**, **AlexRufolo**, **DavidBDJ**, **B2Y26Arabia**, **rwee**, **Risto**, **Yanis**, **LumpierTheGunner**, **Bon Kirk**, **wishfulshot**, **beny609o**, **Nickdaw**, **the_pelado**, **capital030**, **novarama** (moderator), **rickydicky4444**, **MIQABARI**, **nissindiaz**, **Julio**, **Uncle Lanscilo**, **vmican**, **GiorgiM**, **bythezl19**, **quicksite**, **fjchivvdub**, **ZeDosCaes21**, **ELBastos**, **Konkubent**, **beni_93**, **jojofiaz**, **Tysonche35**, **diwwanmago**, **bikolunar42**, **lmazot**, **Erax**, **juanjose6124**, **antoniodias_pt**, **bruce_wayne**, **Sasukidas**, **diablofumao**, **gxldemorci** and **General Kreutaa**.

The licence asks nothing of you. I do: **if you use these findings, addresses, patch sets
or tools in a mod, credit this work and link back** — see
[Free to use — please credit](#free-to-use--please-credit) at the top. It costs you one
line and it is the only thing asked in return.
