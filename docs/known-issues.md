# Known issues

Honest list, as of 2026-09-22. Addresses are given so that a fault offset in your Event
Viewer can be matched against them: the offset is the address minus `0x140000000`
(so `0x1414c674d` shows up as exception offset `0x14c674d`).

## Crashes

| where | address | status |
|---|---|---|
| Scene setup: season generation (the manager-settings step), and season rollovers | `0x1484ed4c0`, sometimes reported as `0x1531cc313` in a module outside the exe | Shipped game bug (occurs without any mod). Not guarded and not guardable: the pointer it writes through is already corrupt when it arrives, so skipping the write would trade a crash for silent damage. Intermittent: on 2026-09-22 it took three of five season creations here, with and without the hooks of `fl26join.dll`, and passed on the next attempt each time. Start the season again, or reload your last save. |
| Exhibition kick-off with new clubs | `0x141fea5ba` | **Fixed** by `fl26nullguard.lua`. |
| Loading a season, and the board meeting when a season is created (schedule list read) | `0x140cd6a21` (guard site `0x140cd6a18`) | **Fixed** by `fl26nullguard9.lua`, which on 2026-09-22 replaced `fl26nullguard3.lua`. Same unchecked read: a lookup that finds no schedule list is indexed anyway. The old guard covered the load path; the new one covers both, and the two overlap, so only one may be installed. |
| Mid-season, calendar advance | `0x140fc9238` | **Fixed** by `fl26nullguard2.lua`. |
| Calendar advance, coach record walker | `0x141572125` | **Fixed** by `fl26nullguard4.lua`. The root cause (a mis-placed coach table after a load) was a bug in this patch set and is also fixed at the source. |
| Calendar advance, AI lineup pass, field getter | `0x1414c674d` | **Guarded** by `fl26nullguard5.lua`. |
| Calendar advance, AI lineup pass, a day after matchday 1 | `0x1415032f0` | **Fixed 2026-09-16** in `fl26caps.lua` — see below. Update the module if you downloaded earlier. |
| Squad table, first-element read | `0x14128a3a3` | **Fixed** by `fl26nullguard7.lua`. |
| Calendar advance, standings position used as an index | `0x1413236e4` | **Fixed 2026-09-17** by `fl26nullguard8.lua`. A club with no position yet holds −1, and the game indexed a table with it. This was a wall rather than a rarity: before the guard every long run died here, twice at the same point; after it, 313 game days across New Year with no crash. |
| Startup, 9–11 seconds in, occasionally | — | Shipped game bug, reproduces on a clean install. Start again. |

## Missing or unverified features

- **Continental competitions: explained, and it is the division flag.** New clubs have been
  seen taking part in the Champions League. The reason is not an overflow and nothing was
  taken from anyone: every league these tools build is a copy of a first-division prototype,
  and the engine offers European places to the **tier-1 leagues of a region**
  (`0x141358bd0`, `0x141359a60`, `0x1413b7910` all gate on tier == 1 before resolving the
  right). Thirty-nine first divisions in England's region are thirty-nine leagues the engine
  considers eligible. Build them with `--tiers 1,2,3` and only the top flight of each
  pyramid is offered places, which is what you would want anyway. Still not done: granting a
  new league places of its OWN deliberately, by extending the rights table in the exe. Cloning a continental competition itself works: the
  tooling copies every phase of a multi-phase competition and renumbers the replicas
  correctly, and cloning the Europa League into a scratch world and reading it back checks
  out — but a clone keeps its source's dates and would collide with it, so nothing playable
  is published. A 36-club single-table Champions League in the modern format exists in the
  research repository and has not been run in a game yet either.
- **Promotion and relegation between new leagues.** A chain of three of our leagues moved no
  club, and the likely reason is now known and is data, not code: all three were first
  divisions, and the resolver only looks for the league above when the lower league is
  division 2 or 3. Build the pyramid with `--tiers 1,2,3` (see build-your-world.md). Whether
  clubs then actually cross at the rollover has not been played yet. A module that moves them
  itself exists in the research repository as a fallback and is not published here.
- **Cups: working, with one rule.** A cup built by `mkcup.py` has been carried through a
  Master League season with every round dated — 16 ties, then 8, 4, 2, 1. The rule is that the
  game fills a cup from the **first league in its region** (lowest competition id) and ignores
  the cup's own entry list, and the shipped cup calendar only has dates for a sixteen-club
  bracket. So the feeder league must have sixteen clubs; with twenty, the extra round lands on
  a date row that does not exist and that round never plays. No executable patch is involved.
- **Menu regions.** New leagues can only be placed in a menu region the game already knows
  (default: England's slot). The table was read in full since: 24 rows, each naming a *drawn*
  label in the menu's texture atlas rather than a translated string, and ids 11, 13, 14 and 20
  have no row — a league placed on one of them shows whatever the previous lookup left behind.
  Spreading leagues across the shipped countries needs no executable change; a region carrying
  our own name needs a new label in that atlas, and the field itself runs out at 31.
- **Kits, names, players.** All placeholders / clones. Not a bug, but a limitation of this
  beta: the tools prove capacity, they do not author content.
- **Transfers and finances**: not observed yet. Report what you see.
- **Second season and beyond**: now played. Four seasons have been run end to end on one
  world, with season rollovers, and the tables no longer carry the previous season's
  results (see below).

## Added leagues that never entered the season — fixed 2026-09-22, one season measured

What it looked like: a league exists, has its twenty clubs, shows in every menu, can be
picked as your own club — and never plays a match. Picking a club from it made it worse:
the season opened in **January** instead of August, only 24 countries had a season instead
of 55, less than half the usual matches existed, the hub showed no table and no fixtures,
and a mid-season review cutscene turned up in June on a world whose season the game already
considered over.

Measured on 2026-09-22 on a world of 41 added leagues, each a first division standing in a
country of its own: **8 entered the season and 33 never did**, in any run. The eight were
the ones the game reaches by its own routes — a league hanging under a shipped second
division through the promotion link, and a league whose id the game's own list happens to
carry.

### The cause

Competitions enter a season on two occasions, and both are driven by lists compiled into
the executable. At creation, the season builder admits a fixed list of calendar-year
competitions. Everything else enters in play, when the calendar reaches a registration date
and the game calls its registration routine with the ids due that day — and that vector
comes from a case table over ids 2..175, of which 142 entries are empty. No data file can
add an id to either list. The function every competition goes through on its way in was
measured live and said **yes to every one of our ids it was ever shown**; the only refusals
it has are "no record" and "season flag off". Nothing ever showed it our ids.

Two earlier attempts had widened the builder's include list. Both changed nothing, because
the builder's list is the wrong list: it is for calendar-year competitions, and a league
admitted there gets a January-to-December season the game does not expect for a league.

### The fix, and what is verified

`fl26join.dll`, loaded by `fl26joindll.lua`, appends the listed ids to the vector the
registration routine receives on the first registration day (the game's ids first, then
ours), skipping any id whose record already carries a season year so nothing is registered
twice. When the builder asks about one of our ids at creation, the module answers no, so the
three of our ids that reuse shipped calendar-year ids no longer get a second, doubled
schedule. Nothing is written to any table; the game's own registration then runs exactly
as it does for its own leagues.

Verified in one run: 40 of the 41 listed leagues were present in the world (one id had no
record, harmless), all 40 entered on day 41 of the calendar, **39 were dealt a full 38-round
season** with 10 matches a round, 17,551 match records in all, and the busiest calendar day
held 172 of its 280 places. At the second registration date the module found all 40 already
in a season and appended nothing.

What is **not** verified, stated plainly:

- **The second season.** Whether the game re-registers the added leagues at the next
  registration day, and whether the first season's records survive the turn of the year,
  has not been played yet. It is the first thing to report if you get there.
- **A season created with a shipped club as your team** on such a world. The measured run
  picked one of the added clubs.
- **The January opening is unchanged.** With a club from a stand-alone league, the season
  still opens in January; the league is registered about two weeks later and dated from
  August, and the hub is empty until then. That the league now plays at all is the fix; the
  odd start is not addressed.
- **A split-season format league** (a rulebook of the "two halves" kind, 12 clubs) enters
  the season but is given no fixtures. Different mechanism, not looked at yet.

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
- **Rulebook ids must be in the date table** (39 ids shipped in `fl26caps.lua`) **and in
  the id list of `fl26joindll.lua`** (the same 39). A league outside the first is silently
  never scheduled; a league outside the second is only entered into the season if the game
  happens to list it itself. Together these are the single most common way a new league
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
