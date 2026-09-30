# Known issues

Honest list, as of 2026-09-28. Addresses are given so that a fault offset in your Event
Viewer can be matched against them: the offset is the address minus `0x140000000`
(so `0x1414c674d` shows up as exception offset `0x14c674d`).

## Crashes

| where | address | status |
|---|---|---|
| Scene setup: season generation (the manager-settings step), match loading, and season rollovers | `0x1484ed4c0`, also reported as `0x1531cc313` or `0x158ecc042` (all three inside the game's protected, encrypted code) | **All three are the game's own.** Measured on 2026-09-25 and 26 over 81 season creations in different setups. With none of our modules and no patch set, 10 of 12 crashed at the manager-settings step: at `0x141fea5ba` six times, `0x1531cc313` three times and `0x1484ed4c0` once. The untouched game, started without Sider at all, crashed at the same step (at `0x141fea5ba`) in 4 of 8. With our full set it was 13 of 30 -- fewer, because `fl26nullguard.lua` catches `0x141fea5ba`. The rate changes a lot from one session to the next. Earlier, on 2026-09-24, a stock game also crashed at `0x1531cc313` on the first match day, and `0x158ecc042` at start-up happens on a stock game too. Not guarded and not guardable where it faults: the pointer it writes through is already corrupt when it arrives, so skipping the write would trade a crash for silent damage. The save is not damaged. Intermittent: on 2026-09-22 it took three of five season creations here, with and without the hooks of `fl26join.dll`, and passed on the next attempt each time. Start the season again, or reload your last save. |
| Exhibition kick-off with new clubs | `0x141fea5ba` | **Fixed** by `fl26nullguard.lua`. |
| Loading a season, and the board meeting when a season is created (schedule list read) | `0x140cd6a21` (guard site `0x140cd6a18`) | **Fixed** by `fl26nullguard9.lua`, which on 2026-09-22 replaced `fl26nullguard3.lua`. Same unchecked read: a lookup that finds no schedule list is indexed anyway. The old guard covered the load path; the new one covers both, and the two overlap, so only one may be installed. |
| Mid-season, calendar advance | `0x140fc9238` | **Fixed** by `fl26nullguard2.lua`. |
| Calendar advance, coach record walker | `0x141572125` | **Fixed** by `fl26nullguard4.lua`. The root cause (a mis-placed coach table after a load) was a bug in this patch set and is also fixed at the source. |
| Calendar advance, AI lineup pass, field getter | `0x1414c674d` | **Guarded** by `fl26nullguard5.lua`. |
| Calendar advance, AI lineup pass, a day after matchday 1 | `0x1415032f0` | **Fixed 2026-09-16** in `fl26caps.lua` — see below. Update the module if you downloaded earlier. |
| Squad table, first-element read | `0x14128a3a3` | **Fixed** by `fl26nullguard7.lua`. |
| Calendar advance, standings position used as an index | `0x1413236e4` | **Fixed 2026-09-17** by `fl26nullguard8.lua`. A club with no position yet holds −1, and the game indexed a table with it. This was a wall rather than a rarity: before the guard every long run died here, twice at the same point; after it, 313 game days across New Year with no crash. |
| Calendar advance in a February-December career, when a European draw is made (memory grows by gigabytes, then an out-of-memory crash) | `0x140affe1b` (endless loop in `0x140caee00`) | **Fixed 2026-09-30** by `fl26nullguard10.lua`. A walk over linked leagues never ended for a lower league whose league above has no league linked below it; every turn copied a date list, and the game grew from 3 to more than 8 GB in under a minute. Seen on day 30 of the second year of a Korea career, while the Europa League play-off was drawn. |
| UEFA Super Cup setup | `0x1413605a9` | **Guarded** by `sider/experimental/fl26superguard.lua` (2026-09-23). The setup indexes the Champions League and Europa League entries without checking that they were found; when one is missing it read entry −1. With the guard that season simply has no Super Cup. Seen in an August-start career, where the European competitions do not start (see below). |
| Matchday-results screen after *Skip Match*, on the day of the Europa / Conference League play-off first leg | `ucrtbase.dll` offset `0xa527e` (exception `0xc0000409`); the game's side is `0x140ca2203` / `0x140ca21db` | **Guarded** by `sider/experimental/fl26resultsguard.lua` (2026-09-25). The screen takes a page out of a list without checking that the list has any; on that day, with `fl26swiss`, it has none, and the game's own check ends the program. With the guard the page stays empty and the career goes on; both play-offs were played to the end. Reported in issue #9 at the Europa League knockout. Why the list is empty is not known yet. |
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
  is published. **Since 2026-09-24** the experimental `fl26swiss` stack (see
  [sider/experimental](../sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss))
  reshapes the Champions League and Europa League to the 2024 format, adds a Conference
  League, and fills all three from a UEFA access list. Since 2026-09-26 that list names only
  the shipped leagues and tops the rest up from the big five; before, it named our world's
  leagues by id, and another world's leagues on the same ids got those countries' places
  (issue #8).
- **In a career that starts in August, the European competitions do not start.** Measured
  2026-09-23 with `sider/experimental/fl26augseason.lua`: the Champions League play-off is
  dated on days 230 and 237 of the year, and the game registers the European competitions
  on day 238, after both. The play-off is drawn but given no matches, so it never finishes,
  the group stage is never filled and the Europa League never begins. The domestic season is
  not affected. With the experimental European format (`fl26swiss`, 2026-09-24) the play-off
  is run by the DLL and all three competitions start and play; without it, this still
  happens.
- **Promotion and relegation between new leagues.** A chain of three of our leagues moved no
  club, and the likely reason is now known and is data, not code: all three were first
  divisions, and the resolver only looks for the league above when the lower league is
  division 2 or 3. Build the pyramid with `--tiers 1,2,3` (see build-your-world.md).
  **Played through a rollover on 2026-09-23**, on our world with a third, fourth and fifth
  division under Ligue 2 and under Serie B: with the experimental `fl26chain` (which
  completes the joints of a chain the game skips) and `fl26seasonend` (which lets France and
  Italy into the European season end), three clubs went up and three down at every joint of
  both chains. One thing still wrong there: Ligue 2 came out of that rollover with 21 clubs.
- **The league rank only counts to three, which breaks pyramids deeper than that.** Measured
  2026-09-22: the rank lives in the top two bits of the rulebook's flags word, so a third,
  fourth and fifth division all store the value 3. The League Info panel then shows a league
  as its own lower league, and the relegation gate — which asks "is the league below me a
  third division, and am I a second" — cannot separate them.
  `sider/experimental/fl26rank.lua` moves the field down one bit (147 in-place rewrites, into
  a bit the shipped loader never sets) so it counts to seven, and `fl26deeprank.lua` rewrites
  both copies of that gate to "second division or deeper, and the one below is third or
  deeper". `tools\deepen.py --retier <top ids>` renumbers a pyramid built before the change,
  since the old value 3 is what is stored in your world's files. Verified against the exe,
  seen live in the menus, and in the stack the chains above were played on.
- **Cups: working, with one rule.** A cup built by `mkcup.py` has been carried through a
  Master League season with every round dated — 16 ties, then 8, 4, 2, 1. The rule is that the
  game fills a cup from the **first league in its region** (lowest competition id) and ignores
  the cup's own entry list, and the shipped cup calendar only has dates for a sixteen-club
  bracket. So the feeder league must have sixteen clubs; with twenty, the extra round lands on
  a date row that does not exist and that round never plays. No executable patch is involved.
- **Menu regions: the ceiling is 64, not 29, and headings are a separate table.** Spreading
  leagues across the shipped countries needs no executable change (`mkworld.py --regions`).
  Above that, two separate things were measured on 2026-09-21. First, the parser that reads a
  competition's region masks it to five bits and throws away anything from 29 up, while the
  runtime field it feeds is six bits and holds 64 — that is one instruction, and
  `sider/experimental/fl26reg64.lua` rewrites it. Second, the menu heading for a region comes
  from a table of 24 rows, each naming a *drawn* label in the menu's texture atlas rather than
  a translated string, and ids 11, 13, 14 and 20 have no row — a league placed on one of them
  shows whatever the previous lookup left behind, because the loop that reads the table falls
  out without touching the register. So a region above the shipped 24 groups correctly and
  borrows a name. The module that gives our regions headings of their own copies the game's
  own rows into spare space; the version that exists carries those rows inside itself as
  shipped bytes, and this repository does not redistribute game data, so it is published only
  once it copies them out of memory at startup.
- **Listed here as "not possible yet" on 2026-09-28, done since:**
  - **Two tournaments a year (Apertura / Clausura) with a play-off**: Mod Studio 0.1.3, driven
    by `fl26swiss`; the phase tables and playoffs of a new country were put right in 0.1.4
    (see below).
  - **A second domestic cup (a League Cup)**: Mod Studio 0.1.3, a knockout of 16, 8 or 4 clubs
    from September to December.
  - **Leagues for exhibition only (historic squads)**: Mod Studio 0.1.3. Their clubs still show
    in the team list of a new Master League career (the game has one list for Kick Off and
    Master League); do not pick one, their league never plays a season.
- **Kits, names, players.** All placeholders / clones. Not a bug, but a limitation of this
  beta: the tools prove capacity, they do not author content.
- **Transfers and finances**: the game's own transfer market in a career is not observed yet.
  Report what you see. Moving players between clubs before a career starts is a Mod Studio
  feature since 0.1.4 (*Players > Sign players... / Transfer to...*).
- **Second season and beyond**: now played. Four seasons have been run end to end on one
  world, with season rollovers, and the tables no longer carry the previous season's
  results (see below).

- **One split or Apertura/Clausura league per country** (2026-09-30, GitHub #45). A world of
  Mod Studio 0.1.3.1 with Apertura/Clausura in both Icelandic divisions entered both leagues
  and both Apertura phases (`door(191) -> YES`, `door(193) -> YES`), wrote the dates of both
  (`split regular phase of 11/49: 9 rounds on days 254..2`), and still had no table and no
  match in either by 30 October; League Info listed all 20 clubs under the first division.
  Both phases sit under the same competition key (the country, `under key 29` in
  `sider.log`), and the game looks a split's phase up by that key (`0x1414ce270` under
  `0x14134a540`); the shipped data never has two splits in one country. Since 0.1.4 the
  builder refuses a second split or Apertura/Clausura league in a country. Giving the second
  one a key of its own is not tried yet.
- **National team call-ups do not stay in a Master League career** (2026-09-30). A world with
  one player called up to South Korea and one dropped: `PlayerAssignment.bin` of the build had
  both changes, and 279 days into a career the live South Korea squad did not have the called-up
  player and had 11 players the file does not list -- the game picks its own national squads in
  a career.
  Whether Kick Off shows the squad of the file is not checked yet. Transfers (`Sign players...`, `Transfer to...`) and the club and
  player ids did stay in the same career.
- **Team of the Season of a new league is empty** (2026-09-30, GitHub #46). At the end of
  season 1 and again of season 2 the screen for a new Icelandic league came up with all 11
  places empty. Fixtures, tables, promotion and relegation and the national cup were fine in
  the same career. Not investigated; whether a league the game already has shows its team in
  the same career is asked on the issue.

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

**The second season (updated 2026-09-23).** It did not work, and now it does. The game
closes last season's competitions in July from a list compiled into the exe, and the added
leagues were never on it: they kept last season's year, the next registration refused them,
their points and matches added up season on season (a league at 76 matches after two
seasons), and old matches stayed on the calendar. The updated `fl26join.dll` puts them on
the July list and keeps them off the New Year one (their season runs August to May). Measured
since: at the July rollover the added leagues close and re-open with the shipped ones, the
new season starts with empty tables and the right year, and they carry on past the New Year
after it with points still rising. **If you downloaded `fl26join.dll` before 2026-09-23,
replace it.**

What is **not** verified, stated plainly:

- **A season created with a shipped club as your team** on such a world. The measured run
  picked one of the added clubs.
- **The January opening: fixed experimentally.** With a club from a stand-alone league the
  season used to open in January. `sider/experimental/fl26augseason.lua` makes it open on
  1 August (day 212), measured on two new careers on 2026-09-23. The cost, for now: the
  European competitions do not start in such a career (see "Missing or unverified
  features" above).
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
job (the experimental `fl26hdr192.lua` is that job). If you are playing many seasons on one
world, this is the thing to watch.

**Three sites added on 2026-09-23 (29 -> 32 patches).** Reading the live code after two
seasons on the 192 version found three places that use the moved tables and that the scan
had missed, because each carries the table start folded together with a field offset: the
byte that says whether a table holds a final standing (+0x314), a copy that walks the tables
(+0x1876), and a header copy that moves entries two at a time and still stopped at 100. The
first one made the season end report "no table" for leagues that plainly had one, so they
were left out of promotion and relegation. The fix was verified in play on the 192 version;
the 127 version is generated by the same tool from the same list and has not been played
yet. **If you downloaded `fl26hdr127.lua` before 2026-09-23, replace it.**

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
- **Rulebook ids must be in the date table** (the 39 ids a default `mkworld.py` run uses,
  shipped in `fl26caps.lua`) **and in the id list of `fl26joindll.lua`** (the same ids; both
  also keep 145 for worlds built before 2026-09-25). A league outside the first is silently
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
- **With `fl26comptab.lua` installed, Kick Off loses three shipped entries.** Select Team
  and Kick Off use the same list of slots. Three of our leagues sit on slots 4, 5 and 6,
  which the shipped game uses for the **Asia-Oceania** national teams and the two
  **Classic Teams** entries, so in Kick Off those three entries show our leagues and their
  clubs instead (measured 2026-09-25). Nothing is deleted: remove the module, or give those
  three leagues other slots in its `APPEND` list, and the entries come back. Every other free
  slot is already in use, which is why they were taken.
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

- 2026-09-30 (Mod Studio 0.1.4): **a split or Apertura/Clausura league in a new country showed
  one club on every row** (issue #37, and an Egyptian split). The badge of a row goes by the
  team id, the name and the match by the team record, and the values our new clubs carried in
  split phases pointed at record 0: every row read as one club, a match between two of them
  asked for *"2 Controllers"*, and the phases were never played. `fl26swiss` and `fl26join` now
  give such a value the row of its own record where the values are used to make matches, a
  playoff filled at the end of its phase is started as the game's own group fills are, and a
  playoff whose phase played no match is not filled. Confirm: every club under its own name,
  the Apertura playoff before the Clausura, `fl26swiss` report lines for each phase in
  `sider.log`.
- 2026-09-30 (Mod Studio 0.1.4): **the same clubs played the Copa Libertadores and the Copa
  Sudamericana** (issue #37). The continental cups Mod Studio builds skipped clubs already in
  another of them, but not the game's own Libertadores (regulation 9), its qualifying round (8)
  and the AFC Champions League (15), whose fields are set on day 0. They are now skipped too.
- 2026-09-30 (Mod Studio 0.1.4): **a club sent to the Libertadores qualifying round stayed at
  home** (issue #33). The round holds only shipped clubs, none from the pool the other places
  replace. `fl26swiss` now gives each of our places the place of a shipped club (the last one
  listed of the country with the most clubs in the round, at most half the round), and the
  round's ties follow. `sider.log`: `... in place of <team> (slot ...)`.
- 2026-09-30 (Mod Studio 0.1.4): **the cup of a country the game already has kept a new second
  division out** (issue #32). It now takes both divisions, the top one's clubs first, when its
  calendar dates every round of that field and the field is at most 44 clubs (Build raises the
  cup's bracket in the world's tables); `fl26chain` gives the cup both leagues' clubs.
- 2026-09-30 (Mod Studio 0.1.4): **a CAF cup with fewer than 4 places was not built** ("a cup
  needs 4 clubs"). It now takes the next CAF cup's places, then the next league positions.
- 2026-09-30 (Mod Studio 0.1.4): **a national cup needed 12, 16, 18 or 20 clubs** (or 36, 40,
  44 with the division below). Any field up to 44 now plays on the English cup's calendar,
  which dates every round of a field of 9 to 64, with the game's own byes.
- 2026-09-30 (Mod Studio 0.1.4): **a league of a new country outside Europe with no division
  below it played no second season** (an Egyptian, Moroccan or Venezuelan league on its own;
  GitHub issues #40, #41). 0.1.3.1 kept UEFA only on an upper division, and the July
  season-end filter passed over the others: `fl26join.log` said `door(<id>) -> no ... flag OFF`
  from the second season on. With its continent's code such a league also entered its first
  season late, on a registration day after the career started, so rounds dated before that day
  were lost (a K League starting from round 3). The builder now keeps UEFA on every league of a
  new country that plays August to May; February-December countries keep their own code.
  Checked in game on 2026-09-29: Egypt (split), Morocco and Venezuela (Apertura/Clausura) enter
  the season when the career is created and again in July (`door(<id>) -> YES` from
  `141315c0b`), with every match of the second season on a calendar day (Egypt 190, Morocco 240,
  the Apertura 66). Side effect: Select Team's *League Info* panel shows the European cups for
  these leagues; their places still go to their own continent's cups. **Checks** names a world
  built before 0.1.4. **Build the world again** and start a new career.
- 2026-09-29 (Mod Studio 0.1.3.1): **a new country outside Europe lost its leagues after the
  first season.** Since 0.1.3 a new league carries its country's confederation, but the game
  moves clubs between two divisions only when the upper one passes a July season-end filter
  that wants UEFA for the regions of new countries: a Peruvian or African first division
  promoted nobody, and the July season list then left both divisions out, so they had no clubs
  from the second season on. The builder now keeps UEFA on an upper division of a new country
  (the division below keeps its own), and the League Info icons come from the world file's
  `conf` instead. Checked in game: Peru first and second division swapped 3 and 3 clubs in
  July. **Build the world again** and start a new career.
- 2026-09-29 (Mod Studio 0.1.3.1): **a new league that plays January to December played no
  second season**, and the next New Year promoted the same clubs again (duplicates in the
  division above). Two causes in `fl26join.dll`: the July season list let such a league in a
  second time (a doubled schedule that could not be finished), and on day 41 the league,
  flagged again by the promotion at New Year, read as "already in a season" and was left
  out. Now it is judged by whether it has rounds, not by its table. Checked in game: a Saudi
  second division promoted and relegated at New Year and started its next year (30 rounds for
  16 clubs). `fl26join.log`: `door(<id>) YES` once on day 41.
- 2026-09-29 (Mod Studio 0.1.3.1): **with the Conference League off, the Champions League and
  Europa League broke** (issue #33). `fl26swiss.dll` runs their league phase of 36 in every
  world, but with the option off the builder left the game's groups of four. The league phase
  and the Europa League play-off are now built either way; **Checks** flags a world built the
  old way.
- 2026-09-29 (Mod Studio 0.1.3.1): **an Exhibition only league went to the bottom of
  Competition Info** (below Classic Teams). Its region is now in the world file's order line.
- 2026-09-29 (GitHub issue #39): **with 37 to 39 new leagues, the last ones are missing from
  Select Team.** That is the fix for #26 below: Select Team has room for 36 new leagues, and the
  37th to 39th get a hidden slot. They play their season, but no career can start in them. Mod
  Studio 0.1.4 names them in the plan (*NOTE: no place in Select Team for ...*); put the leagues
  you want to play with first in the list.
- 2026-09-29 (Mod Studio 0.1.3.1): **the League window was taller than a 1080p screen**
  (issues #34, #35); it now fits the screen and scrolls.
- 2026-09-28 (GitHub issue #26): **the Asia-Oceania national teams and the Classic Teams
  vanished from Kick Off** in a world with 37 or more new leagues. The 37th to 39th league
  took Select Team slots 4, 5 and 6, which the Kick Off list keeps for those entries. The
  builder now gives those leagues a hidden slot (they play, they are not in the Select Team
  list), and `fl26comptab.lua` refuses slots 4-6 also in world files built before. Confirm:
  Kick Off shows both entries again.
- 2026-09-28 (GitHub issue #27): **a new league that plays January to December** (Colombia,
  Japan and the other calendar-year countries) was closed by the game's July season teardown
  like a European league, and lost its second half. `fl26join.dll` now leaves such a league
  alone in July and its region closes it at New Year, and `fl26swiss` dates it between days
  45 and 333. Confirm: `sider.log` at boot says `calendar-year leagues of ours (closed at New
  Year): <n>`, and the league still has fixtures after July. Measured 2026-09-29 with a Saudi
  second division: all rounds February to December, New Year without a crash. Promotion and
  relegation with the division above at New Year did not happen yet (`fl26join.log`:
  `season end: ... 11(no table) 162(below has none)`); fixed in 0.1.3.1, see above.
- 2026-09-28 (Evo-Web report): **two clubs of one country could meet in the league phase**
  (Manchester United v Manchester City). The draw was a fixed table by list position; each pot
  is now reordered so one league's clubs are spread. Confirm: `sider.log` has `draw spread by
  league: ... before, 0 and 0 after` for the Champions League and the Europa League. The
  Conference League, with more clubs from a few countries, can keep one such pair. Since Mod
  Studio 0.1.4 the draw follows UEFA's rules instead: no club meets a club from its own
  country, and at most two of its opponents come from any one other country (`sider.log`:
  `draw by association: ...`, then one line per club with its opponents' countries). A field
  that no draw can satisfy keeps the closest draw and says so.
- 2026-09-28 (Evo-Web report): **a shirt number typed as 10 came out as 11.** The game stores
  the number minus one; the player editor, the builder and Mod Studio now read and write it
  that way. Numbers set with an older version are one too high: set them again.
- 2026-09-28: **a new league outside Europe sat among the European categories** (an Emirati
  or Peruvian league listed as UEFA). Every new league was a copy of England's row; the builder
  now writes the country's own confederation.
- 2026-09-28: **`mkcup.py --region` took the raw byte**, so `--region 29` put the cup in
  region 35. It is now a region id.
- 2026-09-28 (GitHub issue #28): **Sider in a folder not called `SiderAddons`** was not found.
  Mod Studio and the League Builder now look for the folder that holds `sider.ini`, and
  Settings chooses between several.

- 2026-09-27 (Evo-Web report): **in the first season `fl26swiss` put big clubs such as PSG,
  Real Madrid or Inter in the Conference League.** With no final tables yet, the access list
  read the league's own club list, which is in no useful order. Worse, a new career is built
  on day 216, after the summer capture, so its empty tables were captured as if they were
  final. Now tables with no match played are not kept, and a first season orders each league
  by squad strength (the eleven best players by their ratings). Confirm: start a new career,
  play to the end of August; `sider.log` shows `first season -- reg ... by squad strength`
  and `108 from first-season order`, and the Champions League holds the strongest clubs.
- 2026-09-27: **new clubs played in the plain default kit even after `mkkits.py`.** The tool
  named the files after the team id (`72163_DEF_1st_realUni.bin`), but the engine looks a kit
  up under a shortened number and a range tag: ids 65536..81919 are `<id-65536>_ACL_...`, the
  form the game uses for its own AFC clubs. `mkkits.py` now writes those names. Confirm: rerun
  `mkkits.py ... --archive` into your world, pick one of your clubs in Kick Off; the pre-match
  screen and the Strip screen show its donor's kits.
- 2026-09-27 (GitHub issue #12): **a Master League career in a league on region 29 started on
  1 January with no table and no calendar,** with or without `fl26augseason`. Region 29 was
  never reachable in the stock game, so two tests in the career builder that throw region 29
  out never fired. With `fl26reg64` they do, and the league is removed from the new career
  (it is still there at boot and in the main menu). `fl26reg64.lua` now also patches both
  tests (`0x141264659`, `0x141264b51`). Only careers created after the update keep the
  league. Regions 30 to 63 were never affected.
- 2026-09-27 (GitHub issue #11): **an added league could show another country's flag.** The
  game's own region-to-country table still answers for four regions no shipped league uses:
  11 Poland, 13 Sweden, 14 Norway, 20 Mexico. `spreadregions.py --plan own` hands those
  regions out, so a league placed there wore that country's flag (the tester saw a Swedish one
  on a Lithuanian league). `tools/mkflags.py` now writes each league's own country for those
  regions, or "no country" when it cannot tell, and warns when it overrides the game. It also
  fills the new Select Team flags in `fl26comptab.lua`. Checked against `Country.bin`: every
  flag id in the tables is the country it claims.
- 2026-09-27 (GitHub issue #10): **the UEFA play-offs were skipped in later seasons played
  in one session.** With `fl26swiss`, in seasons 2 and 3 the league phases ended and no
  play-off followed: the Champions League screen showed `%s` and eight empty rows, the Europa
  and Conference League stayed on the league phase. A restart of the game made the next try
  work, which is why it looked intermittent. The DLL guards against drawing a play-off twice by
  keeping the day it was drawn, and the game's day counter is the day of the calendar year: a
  season later the same February day (December for the Conference League) looked "already
  drawn", so nothing was drawn and the game was told it had been handled. The tester's log
  shows exactly that (the progression answered for all three, with no tie lines). The final
  league tables kept for next season's UEFA places had the same flaw from the third season on.
  `fl26swiss.dll` now counts days across New Year for every such check. Not yet followed here
  through two play-offs in one session (the protection crashes above force restarts in our long
  runs); the first play-off of a session is unchanged. A save made after a missed play-off does
  not get it back: replay from a save before the league phase ended (for the Conference
  League, before its last matchday in December).
- 2026-09-26: **every club of every new league had the same manager, "Jorge Jesus".** A club
  names its manager in the first four bytes of its `Team.bin` record (Arsenal's is Mikel
  Arteta's coach id). `mkworld.py` gave each new club a fresh id there but wrote no coach for
  it, and the game fills a missing coach with a copy of its first one. `mkworld.py` now writes
  `Coach.bin` too, one placeholder manager per new club; `tools/mkcoaches.py` does the same for
  a world built before. Checked in Edit > Managers and on an exhibition's pre-match screen.
  Not yet followed through a Master League season.
- 2026-09-26 (GitHub issue #8): **clubs of new leagues turned up in the Copa Libertadores.**
  When a Master League is created the game gives every club a "slot" by a hard-coded remap
  (`0x141263b40`): slots 26, 27, 28, 67 and 74 become 73, 71 becomes 69, and 69, 73 and 75
  are the "other clubs" pools the Libertadores and the Club World Cup are filled from. A
  league on rulebook id 11 keeps the exe's row on slot 28, so all its clubs went into the
  Latin American pool. `fl26clubs.lua` now sets the switch for slots 28, 71 and 74 to "keep
  your own slot", and `fl26clubs.dll` leaves new leagues' clubs out of pool slots 69/73/75 for
  that step. Checked on a new career: none of our clubs on 69/70/73/75 (before: 118). The slot
  is stored in the save when the career is created, so **only careers started after the
  update** get it.
- 2026-09-25: the 25th league of a default world sat on rulebook id **145**, which is the
  shipped J2 League's id, and the shipped **J1 League relegates into 145**. `mkworld.py` now
  puts that league on **190**; `fl26caps.lua`, `fl26joindll.lua`, `fl26comptab.lua`,
  `fl26chain.lua` and `fl26swiss.dll` know 190 and still know 145, so a world built before
  keeps working. In our own runs J1 never actually sent a club into 145, at New Year or at
  the July rollover, but the link is there, so the league was moved rather than trusted.
  Verified on a new world: league 190 enters the season with all its clubs and every round
  dated.
- 2026-09-25 (GitHub issue #2): `fl26slotnames.lua` left a **blank heading** on any slot of
  its list that has no league of yours on it. It now falls back to the heading the slot
  always had ("Asia-Oceania", "Classic Teams", ...), so the default list is safe in any
  world. Checked in game both ways: our leagues keep their own names, and with a slot
  emptied on purpose its heading reads "Asia-Oceania" again.

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
