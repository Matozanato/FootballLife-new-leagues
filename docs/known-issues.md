# Known issues

Honest list, as of 2026-09-21. Addresses are given so that a fault offset in your Event
Viewer can be matched against them: the offset is the address minus `0x140000000`
(so `0x1414c674d` shows up as exception offset `0x14c674d`).

## Crashes

| where | address | status |
|---|---|---|
| Scene setup: season generation, and season rollovers | `0x1484ed4c0` | Shipped game bug (occurs without any mod). Not guarded and not guardable: the pointer it writes through is already corrupt when it arrives, so skipping the write would trade a crash for silent damage. Start the season again, or reload your last save. |
| Exhibition kick-off with new clubs | `0x141fea5ba` | **Fixed** by `fl26nullguard.lua`. |
| Loading a season (schedule read) | `0x140cd6a1c` | **Fixed** by `fl26nullguard3.lua`. |
| Mid-season, calendar advance | `0x140fc9238` | **Fixed** by `fl26nullguard2.lua`. |
| Calendar advance, coach record walker | `0x141572125` | **Fixed** by `fl26nullguard4.lua`. The root cause (a mis-placed coach table after a load) was a bug in this patch set and is also fixed at the source. |
| Calendar advance, AI lineup pass, field getter | `0x1414c674d` | **Guarded** by `fl26nullguard5.lua`. |
| Calendar advance, AI lineup pass, a day after matchday 1 | `0x1415032f0` | **Fixed 2026-09-16** in `fl26caps.lua` — see below. Update the module if you downloaded earlier. |
| Squad table, first-element read | `0x14128a3a3` | **Fixed** by `fl26nullguard7.lua`. |
| Calendar advance, standings position used as an index | `0x1413236e4` | **Fixed 2026-09-17** by `fl26nullguard8.lua`. A club with no position yet holds −1, and the game indexed a table with it. This was a wall rather than a rarity: before the guard every long run died here, twice at the same point; after it, 313 game days across New Year with no crash. |
| Startup, 9–11 seconds in, occasionally | — | Shipped game bug, reproduces on a clean install. Start again. |

## Missing or unverified features

- **Continental competitions: unexplained, not absent.** New clubs have been seen taking
  part in the Champions League in a test world. That is not something this project built,
  and it does not follow from what has been mapped: qualification is a static table in the
  exe whose rows name a *shipped* league and a place in it, filtered by region, so it should
  hand out places to shipped clubs only. Either something else fills the entry list when a
  season is created, or the grown tables have shifted an index and the clubs in that
  competition are not the ones the game meant to put there. Until that is settled, do not
  treat continental entry for new clubs as a feature, and **if you see it, say what you saw**
  — which competition, which clubs, and whether the shipped clubs that should have been
  there are missing. Deliberate qualification (patching that table so a new league is granted
  places of its own) is mapped and not done. Cloning a continental competition itself works: the
  tooling copies every phase of a multi-phase competition and renumbers the replicas
  correctly, and cloning the Europa League into a scratch world and reading it back checks
  out — but a clone keeps its source's dates and would collide with it, so nothing playable
  is published. A 36-club single-table Champions League in the modern format exists in the
  research repository and has not been run in a game yet either.
- **Promotion and relegation between new leagues.** The engine does the top joint of a
  three-league chain by itself and skips the middle one. A module that finishes the chain is
  written and not yet tested in a season; it is not published here.
- **Cups.** `mkcup.py` produces a valid knockout competition, but no cup has been carried
  through a Master League season yet.
- **Menu regions.** New leagues can only be placed in a menu region the game already
  knows (default: England's slot). The region name table is understood; adding regions is a
  separate patch that has not been verified in play.
- **Kits, names, players.** All placeholders / clones. Not a bug, but a limitation of this
  beta: the tools prove capacity, they do not author content.
- **Promotion/relegation between new leagues, transfers, finances**: not observed yet.
  Report what you see.
- **Second season and beyond**: now played. Four seasons have been run end to end on one
  world, with season rollovers, and the tables no longer carry the previous season's
  results (see below).

## The 100-competition wall — fixed 2026-09-17, with a caveat

If you ever saw a league table showing **76 matches played and around 130 points**, this
was why. The season keeps one entry per competition in a table of exactly **100**, and a
39-league world wants more than that. Competitions that did not fit were turned away with
no error at all and went on writing their results into the previous season's table.

`fl26hdr127.lua` widens that table to **127**. Measured on a world built with it, the
season holds 115 and then 124 competitions, and entries 100 upwards carry real
competitions with their own standings — including the multi-group ones, which were exactly
what was being lost. The cost is one of the 600 per-phase standings tables, of which a
running season uses about 375.

**The caveat, because it is not finished.** An entry is never given back: a competition
that has ever run keeps its slot for good, so the count only rises. Watched across four
seasons it went 88, 115, 119, **124 of 127**. Whether it stops there or reaches 127 is not
yet known, and if it reaches 127 the same silent turning-away returns at the higher number.
127 is also the ceiling of this patch's approach, so going further is a different and larger
job. If you are playing many seasons on one world, this is the thing to watch.

## Later seasons lost their fixtures — fixed 2026-09-17, verified across a rollover

Found and explained on 2026-09-17. If you downloaded before that date, **replace
`sider/fl26caps.lua`** — the one published earlier has this fault.

What it looked like: five seasons played back to back on one world, the number of fixture
records in use falling steadily across them —

    2194  2314  2616  2329  1593  1461  1201  1133  1087  997  883

— until by the fifth season **4 of the 39 new leagues had fixtures and the other 35 had
none**, and the in-game calendar showed empty days because nothing was scheduled.

### The cause

A match record holds its competition at `+0x04` and the year it is played at `+0x08`. The
records were all there — every league had its 380, a 20-club double round robin — but the
year read `0xffff`. A match with no date is never put on a calendar day, and a match that
is not on a calendar day is never played. Counted per competition, the four leagues that
still worked were exactly the four that carried real years.

That came from the patch set, not from the game. The generator takes the list of leagues
that are to be given the big-league calendar, and when the list is not passed it falls back
to a single test league. The set published on 2026-09-16 was regenerated to raise the
fixture list to 8,000 and that regeneration did not pass the list, so it shipped dating one
league where the set before it dated thirty-nine. The one league that kept its date is the
one league that played all six seasons.

Two things that were **not** the cause, though both are real and worth knowing:

- the match table does fill up (26,000 records), because the leagues that kept dates kept
  six seasons of history while the shipped competitions keep two;
- calendar days hold 280 match ids and the surplus is dropped without a word. In the broken
  world nine days sat at exactly 280, all of them the same weekday.

### The fix, and what is verified

The set is regenerated with all 39 leagues and the measured day-spread: **2,760 patches**,
and the edit block, the copy size and every array base are unchanged, so **saves made with
the previous version still load**.

Verified on a fresh season: all 39 leagues are in the calendar, no match record is undated,
and the busiest calendar day is 243 of 280 with no day at the ceiling.

**Now verified across a rollover**, which is what this fault needed, since it only ever
showed itself in the second season and later. A world was played on into its second season:
every one of the 39 leagues was dealt a fresh 380-match season on schedule, every record
carried a real date, and none was dropped.

**One thing is still imperfect, and it is not the same fault.** Five of the 39 leagues do
not keep the *previous* season's matches across the turn of the year. At the point in the
second season where the other 34 hold 760 records — two seasons at once, which is what the
shipped competitions do — those five hold only their new 380. They are scheduled, they play,
their new season is complete; what they lose is history. The cause is not known and is not
the dating fault above, which is fixed and holding. It is written here rather than left out
because "leagues with no fixtures" was the wrong description of it and stood in this file
for a day.

An honest note on how it was missed in the first place: the falling record count was watched
all afternoon and read as the game reclaiming finished rounds, which it does do. A falling
count looks the same whether old rounds are being freed or new ones are never created, and
the more comfortable reading was taken without checking whether matches were actually on the
calendar.

## Things that are by design and will bite you

- **Saves are tied to the world.** A save made with world A does not load with world B or
  with the shipped game. Move your saves aside when you switch roots.
- **Rulebook ids must be in the date table** (39 ids shipped in `fl26caps.lua`). A league
  outside it is silently never scheduled — this is the single most common way a new league
  ends up existing but never playing. See build-your-world.md and
  [how-it-works.md](how-it-works.md).
- **Rulebook ids above 175 do work**, but by default a league on one is invisible in the
  **Select Team** list. It generates, schedules and plays a full Master League season; only
  that one menu cannot show it. Easy to mistake for a data error. That list comes from a
  static table in the exe, and `sider/experimental/fl26comptab.lua` copies and extends it so
  those leagues become selectable — not yet verified across a season, which is why it sits in
  the experimental folder.
- **1,536 clubs in total is a wall** in the season generator, independent of the 1,600 table
  size. 793 new clubs is the most we have built and loaded; the world played across four
  seasons had 39 leagues and 780.
- **A calendar day holds 280 match ids**; overflow is dropped silently by the scheduler.
  More leagues on the same weekday lose fixtures with no error at all. Do not trust the
  calendar to tell you: it counts what was accepted, so a day that turned matches away reads
  as a tidy 280. Count the match records instead — measured once at 280 accepted against 351
  that wanted the day. `tools/dayplan.py --demand` does this and prints the day-spread that
  fixes it; see [limits.md](limits.md).
- **The calendar is 365 days** and cannot be extended in place.
- Squads are exactly `--per` players (default 23). We do not yet know whether a squad that
  thin is what starves the AI lineup pass at day 238 (see above). Bigger squads cost player
  slots: the budget is 18,266 new players in total.

## Fixed along the way (so you can confirm)

- 2026-09-16: a season loaded from a save died a day after matchday 1 in the AI lineup pass,
  with the game asking for a player that does not exist. The cause was in this patch set: the
  regulation accessor's index bound was raised from 300 to 600 while the base displacement
  next to it kept the shipped layout, so on load 293 regulation records were written 0x21b100
  bytes low — straight over the team array. 69 of 1483 clubs came back with 233 broken squad
  entries; 147 pointed at an empty record and 86 silently at the wrong player. The game counts
  a broken entry as an available player and then cannot place it. The coach branch of the same
  function had the identical gap. Both fixed (2,688 → 2,690 patches), and the generator now
  refuses to emit a set while any moved offset is left unpatched and unexplained. Verified by
  loading the same save and checking every squad entry against the live player table: 0 broken
  in all 1473 clubs, and the season then played past the day it used to die on.
  **Save files were never damaged** — only the memory the load filled — so an old save loads
  clean with the new module.
- 2026-09-15: after a load, the manager's name was blank, the standings panel empty, and the
  season crashed within minutes. Cause: the load path wrote the coach table and the rulebook
  table into the wrong place (the club table's growth was added twice). Fixed in the
  generator; verified by comparing the tables byte for byte before saving and after loading,
  three loads in a row.
- 2026-09-15: a saved season lost every club past the shipped count. Cause: the game
  serialises from a second copy of the tables that had kept the shipped sizes. Fixed by
  growing that copy too (`mlcopy` in the set name).
