# The modern UEFA league phase: what the engine does, and what it would take

Written 2026-09-20. **Static only** — the exe was read, nothing was run. Image base
`0x140000000`, no ASLR. This answers plan stage F7 ("the modern Champions League / Europa
League format") and settles it: the Swiss league phase is **not expressible in data**.

Goal: one table of 36 clubs where each club plays 8 of the other 35, then a knockout play-off
for places 9-24 and a last 16. Same shape for the Europa League, and 6 matches instead of 8 for
the Conference League.

## 1. The real fixture generator

The chain named in earlier notes (`0x14134e570` / `0x14134d9c0`) is the fixture **reader** that
builds the UI lists. The generator is elsewhere:

| address | what it is |
|---|---|
| `0x1413ac170` | `buildCompetitionFixtures(ctx, u16 competition id)`; callers `0x141315c06`, `0x141343c56`, `0x141343cb3` |
| `0x1413ac1b7` | gate: the regulation must have `+0x304` bit 8 set |
| `0x1413ac1c4` | switch on `+0x84`, the competition **kind** (from `CompetitionRegulation.bin +0x09`) — **not** on `format` |
| `0x1413f36c0` | kind 1: the league builder (called at `0x1413ac233`) |
| `0x1413f49f0` | kind 3: the knockout builder (called at `0x1413ac269`) |
| `0x1413f63e0` | kind 4 |
| — | kinds 2, 5 and 6 produce no fixtures at all |

Inside the league builder: `0x1413f29e0` builds the schedule context, a switch on the
competition id (jump table `0x1413f39f4` / `0x1413f3a08`) picks a per-league *constraint
seeder* (`0x1413f3c30`, `0x1413f42c0`, `0x1413f3a60`, `0x1413f40f0`), `0x1413f3010` validates
the resulting grid and falls back to the generic builder `0x1413f3e00`, and `0x1413f4430`
writes the matches into the global fixture array.

## 2. Matches per club are computed, not configured

`0x1413f29e0` sets the schedule context from three things only:

* `ctx+0x3c` = `+0x308 >> 29`, the rounds field (`0x1413f2a0f`)
* the club vector at `ctx+0x20`, filled by looping `i < (+0x30a & 0x7f)` over the `+0x170`
  handle list through `0x140a9d150` (`0x1413f2a24`..`0x1413f2a6a`)
* `ctx+0x38` = **`(N - (N even ? 1 : 0)) * rounds`**, the total number of matchdays
  (`0x1413f2ac9`); `ctx+0x44` marks an odd club count and `ctx+0x40` is the padded count

There is no field, anywhere in the record, that says how many matches a club plays. It is
always `rounds * (N-1)`.

## 3. The pairings are arithmetic, not a table

`0x1413f3e00` is the circle method written out inline. `0x1413f30f0` allocates
`grid[legs][N][N]` of `{matchday, home/away}` pre-filled with `{0x37, 2}` = no match, the
round offset is `(N-1) * leg` (`0x1413f3ed2`), the matchday of a pair is `(i + j) mod (N-1)`
plus that offset (`0x1413f3f88`..`0x1413f3f98`, with the fixed team handled at
`0x1413f3f63`..`0x1413f3f86`), and the second leg flips home advantage (`0x1413f405a`).

The per-competition seeders are not schedules: `0x1413f3c30`, for example, stack-builds twelve
`{matchday, club A, club B}` triples and pins them into the grid. They constrain a handful of
fixtures inside a full round robin.

## 4. The format field chooses no schedule

Every read of the format field (`mov r32,[rec+0x308]; shr 0x17; and 0x3f`) sits in
classification predicates and UI code — `0x1414cf1d7`, `0x1414cf4b7`, `0x1414cf717`,
`0x14131f1ce`, `0x141321b3e`, `0x141264660`. None of them is inside `0x1413ac170`,
`0x1413f29e0`..`0x1413f4880` or `0x1413f49f0`.

Two corrections to `competition-shapes-catalog.md` section 7 follow from this. The loader
rejects a format of `0x35` or more before storing it (`0x1414f7fde`), so 53 and 54 can never be
set at all; and the 54 seen in the scheduler is a **stage id**, not a format — `0x1413f49f0` and
`0x1413f54b0` use 46, 53 and 54 as stage ids, 54 being the third-place play-off. The unused
values that can be stored (16, 17, 21, 24, 34, 47) change how a competition is classified and
displayed, not how it is scheduled.

## 5. Where matches are written

Global fixture array: `edit block + 0xd65f64`, 2000 records of `0x208`, 16 match slots of 32
bytes from `+0x004`, count in the low 26 bits at `+0x204`.

* league emitter `0x1413f4430`: record lookup `0x141579ee0(compId, &matchday)` at
  `0x1413f4649`, allocation `0x141579db0` at `0x1413f4680`, slot append `0x1414e3430` at
  `0x1413f46de`, count store at `0x1413f470a`, home id at `0x1413f4724`, away id at
  `0x1413f4749`
* cup and group emitter `0x1413f54b0` (siblings `0x1413f59d0`, `0x1413f62b0`, `0x1413f64f0`)
* allocator `0x141579db0` registers each record index into the regulation's own list at
  `+0x88` through `0x1414c9db0`

## 6. Verdict and the hook

**A league regulation always plays a complete round robin.** 36 clubs means 35 or 70 matchdays
and 630 matches. No data change reaches the Swiss draw.

The replacement point is `0x1413f3e00`, signature `bool(ctx* rcx, u16 compId dx, u8 flag r8b)`,
single caller `0x1413f38bb`. Our own builder would:

1. call `0x1413f30f0(ctx)` to allocate and clear the grid at `ctx+0x08`;
2. write `ctx+0x38` = 8, the matchday count — the emitter reads it at `0x1413f4490`, after we
   return;
3. fill `grid[0][i][j] = {matchday, 0}` and the mirror `grid[0][j][i] = {matchday, 1}` with our
   own seeded draw, the club index being the position in the `ctx+0x20` vector;
4. return 1, so the caller skips the fallback and runs the emitter.

Everything downstream — dates, records, standings — is then the game's own.

## 7. The two ceilings this runs into

| ceiling | where | effect on 36 clubs |
|---|---|---|
| 16 matches in one fixture record | `0x1414e3430` scans exactly `0x10` slots and returns null when full; `0x1413f4430` then **drops the match silently** at `0x1413f4793` | a matchday of 18 loses 2 matches every round |
| 58 matchdays per competition | the `+0x88` list, bound `0x3a` at `0x1414c9890` and `0x1414c9dcc` | fine for 8 rounds; fatal for a 36-club double round robin (70) |

The record key is (competition id, matchday), so the first one has two ways out: the planned
G2b widening of the record from 16 slots to 32 (`docs/g2b-fixture-record.md`), or splitting each
Swiss round across two matchday numbers, which costs nothing but shows as two dates.

## 8. Everything else already fits

Measured the same day, from the same static reading:

* the club count field is 6 bits, so 36 is inside the 63 ceiling;
* the club list in a regulation holds 48;
* one standings phase table holds 48 clubs (`0x1414fd600`, `0x30` entries of `0x10`) and 40
  rounds (`0x1414fefa0` and `0x1414ff010`, `0x28` entries of `0x14` at `+0xe04` and `+0xad8`);
* the structure "league phase, then play-off, then last 16" needs no new machinery: the shipped
  Champions League already carries a play-off of 16 (reg 2) and a knockout of 16 (reg 4) under
  one competition, and Scotland proves a league row and a knockout row can share a competition;
* fixture **dates** are chosen by regulation id, not by shape: a byte table at `0x1415802e8`
  maps ids 1..175 onto cases in `0x1415801ec`, case 62 returns no dates at all, and each real
  case copies a static array of 12-byte `{day, key, flags}` records. Eight matchdays means our
  own array and a redirected case byte — the same class of patch we already apply.

## 9. Implemented: fl26swiss (2026-09-20, built, not run)

* `tools/mkswiss.py` generates and checks the draw, and writes `tools/native/fl26swiss_table.h`.
  144 matches; every club has 8 different opponents, exactly two from each pot of nine, exactly
  four home and four away; each of the 8 rounds is a perfect matching of all 36 clubs and is
  split over two matchdays of nine, so no matchday can overflow a fixture record. Output is
  byte-identical between runs.
* `tools/native/fl26swiss.c` replaces `0x1413f3e00` for configured regulation ids only, with the
  16-byte prologue verified before the patch. For our regulation it calls `0x1413f30f0` for the
  grid, writes the pairings with every vector length checked, sets the matchday count to 16 and
  returns 1; for anything else it jumps to the untouched original through the trampoline. It
  also refuses, and falls back to the original, unless the club count and the padded count are
  both 36.
* `sider/fl26swiss.lua` loads it and reports on F8. Deployed to `SiderAddons/modules`, and its
  `sider.ini` line is left commented out until the competitions exist.
* Build: `tools/native/build-swiss.sh` regenerates the table first, so the DLL cannot drift
  from the generator.

## 10. The sixteen matchdays now have dates (2026-09-21, built, not run)

The third of those three gaps is closed. A calendar in this engine is a flat array of twelve-byte
records -- day of the year, round, kind -- copied into a vector by a function that does nothing
else (`docs/fixture-dates-arbitrary.md`), so the module can simply write its own.

`fl26swiss.dll` now also hooks the date lookup at `0x14157f810` (seventeen bytes stolen: the
prologue starts with a REX-prefixed `push rbp`, the same trap the chain hook's apply site set).
For any regulation that is not ours the original runs untouched, which leaves the patch set's own
date stub in charge of our ordinary leagues. For ours it asks the shipped 38-round league
calendar for its records first -- purely so the game's own allocator grows the vector -- then
rewrites the first sixteen and cuts the vector to sixteen by moving its end pointer. Nothing is
freed and nothing is reallocated, so the memory stays exactly as the game laid it out, and the
trick only ever shortens: a calendar longer than 38 rounds is refused rather than guessed at.

The sixteen days are two a week through the European weeks of autumn and four in January
(259, 260, 273, 274, 294, 295, 308, 309, 329, 330, 343, 344, 20, 21, 28, 29) -- January is a small
number after a December one because the day counter is a calendar year, exactly as the shipped
array wraps from 363 to 2.

Both hooks are checked before either is patched, so a signature mismatch leaves the game
unmodified rather than half hooked. Deployed; its `sider.ini` line is still commented out.

## 11. The competition itself (2026-09-21, written, not run)

`tools/mkswisscomp.py` writes it: a league competition of exactly thirty-six clubs, in seeding
order, appended to the same three tables every other competition here is made of. It refuses
any other club count (the module refuses it at runtime too, and then the shipped 35-matchday
round robin runs instead), refuses a repeated club, and refuses a prototype that is not a
league, because the module hooks the league builder and a cup would never reach it. The
default region is the inter-club slot, where the Champions League and the Europa League
already sit, not a country. It prints the four pots back, and the regulation id to put in the
`REGS` list in `sider/fl26swiss.lua` -- the loader passes the ids to the DLL, so adding a
competition needs no rebuild.

Checked against `_FL26G39Tri`: competition 174, regulation 186, 36 entries in draw order,
written and read back. Not yet run in the game.

Still needed after that: the play-off of 16 and the last 16 under the same competition, which
is the multi-phase clone described in the Conference League blueprint in `docs/findings.md`.
The league phase stands on its own without them -- it just ends at a table instead of a
trophy.

## 12. Live in the shipped competitions (2026-09-23 / 24)

The test competition of section 11 was dropped. The shipped Champions League and Europa League
carry the format instead: `tools/mkreshape.py` turns regulation 3 and regulation 5 into one group
of 36 each (world `_FL26G39UCL36`), and the league phase is that group's row, 1027 and 1029.

What had to be added on top of sections 9-10, all in `fl26swiss.dll`, all measured in a Master
League career that starts in August:

* **The play-off had no dates** a career could reach: the shipped legs are on days 230 and 237
  and the European competitions enter on 238. The date hook moves regulation 2 and its replicas
  two weeks later (244, 251).
* **The seeding emptied the list.** After the play-off, `0x141344920` builds the entrant lists of
  3 and 5 and hands each to the seeding `0x14155cd30`, which builds pots for eight groups of four,
  fails on one group of 36 and on failure clears the list. The hook puts the list back in entry
  order; the group draw hook gives row 1027 / 1029 the whole list when the draw did not.
  A Champions League short of 36 is topped up from the head of the Europa League's list, and
  the Europa League is cut to 36.
* **The table showed "Group A".** The standings screen pages the 36 rows with L1/R1 and its
  header says "League Phase".
* **Knockout entry.** When a group stage ends, the progression `0x141345cc0` takes the first N
  rows of every group's table, N four bits of `+0x304` (bits 20-23) -- the top two of one group
  of 36. The hook on set_clubs `0x141522b50` (in front of `fl26chain.dll`'s own hook on the same
  function) hands reg 4 and reg 6 the top 16 of the league-phase table instead, in the order
  1-16, 8-9, 4-13, 5-12, 2-15, 7-10, 3-14, 6-11, because the knockout pairs neighbours.
  Scheduled by the game: Champions League round of 16 on 24.02 / 17.03, quarter-finals 7/14.04, semi-finals
  28.04 / 5.05, final 30.05; Europa League 18/25.02, 8/15.04, 29.04 / 6.05, 20.05. The first tie
  is rank 1 against rank 16. The 9-24 knockout play-off is not there: ranks 1-16 go straight
  into the round of 16.

### The Conference League (2026-09-24, league phase live)

`tools/mkuecl.py` copies a world and clones the reshaped Europa League into it with
`mkphases.py`: competition 174, league phase 186 (one group, row 1210), knockout 187, 36 entries
from the European first divisions that are in no other European competition's entries.
`modscan.py` against the source world: one new competition, three new regulations, nothing
changed.

The exe knows nothing of competition 174. The progression switches on the regulation id
(cases 2..0xaf, byte table at `0x141345f74`), so 186 falls to the default and does nothing, and
no builder gives it entrants. `fl26swiss.dll` hooks the progression and does both hand-overs the
way the shipped cases do:

* when the play-off (reg 2) ends and the original case has filled 3 and 5, it builds the
  Conference League field -- the Europa League's direct entrants cut to make 36, then 186's own
  clubs, then the list the Lua loader passes (`UECL` in `sider/fl26swiss.lua`), minus anyone in
  the Champions League or the Europa League -- and runs set_clubs(186), the group draw (186),
  pushes 186 onto the caller's list of started stages and calls `0x141590420(186)`, the same
  four steps `0x1413449b4..0x1413449f7` take for reg 3;
* when 186 ends, set_clubs(187) (the knockout hook turns it into the top 16 of 1210's table),
  push 187, `0x141590420(187)`.

The league phase plays on the module's sixteen days plus four (1210 is third in `REGS`), the
knockout keeps the Europa League's calendar -- the same days, different clubs.

**A club is not a team id.** Clubs in a regulation are stored as `slot | team_id << 14`: the
low 14 bits are the club's slot in the game's club list, the team id is above them (England's
reg 17 holds `0x194014` = slot 20, team 101). The first run passed bare team ids from the Lua
list; the game read them as slots, every Conference League match was a 3-0 forfeit. The loader
list is now resolved to full club values by finding, among the existing regulations, the value
whose `>> 14` is the team id; all 36 resolve. Matching the low 14 bits instead finds 14.

Live (2026-09-24, world `_FL26G39UECL`): after the play-off on day 251 the progression was asked
for reg 2, the Conference League got 36 clubs, the draw ran, and its matchdays from day 263 on
play with ordinary scores.

### The knockout play-off, ranks 9-24 (2026-09-24, live)

The shipped Champions League play-off (reg 2: eight ties, replicas 1026 + 1024k) has finished
by September, so the module uses it a second time in February. The game's own day counter
(u16 at edit block + `0x1642a1c`) decides which use is meant; below day 180 is the second half.

* Progression asked for reg 3 in the second half: the original case is skipped. Replica k gets
  ranks 9+k and 24-k of 1027's table, reg 2 all sixteen, and reg 2 is started. The date hook
  gives its two legs days 34 and 41 (3 and 10 February) instead of the August shift.
* Progression asked for reg 2 in the second half: the original case (it would rebuild both
  league phases, `0x141344920`) is skipped. The winner of each tie is read with
  `0x14151b2e0(&club, replica)`, the read `0x141346030` makes; reg 4 is filled with rank i
  against the winner of tie 7-i (rank 1 against the winner of 16 v 17) and started. The
  round of 16 keeps its own day, 24.02.

The Europa League and the Conference League keep the direct top 16.

**Stale tie tables.** Each play-off replica keeps the tie table it was given in August
(rec +0x88 -> a 0x208-byte record in the fixtures array, type 53 in the top six bits of +0x204).
The schedule builder reuses a table it finds instead of allocating one, so in the first live
run the February matches were created and played but every tie was still "decided" from
August's two clubs, and 0x14151b2e0 returned the null club for all eight: the round of 16 got
eight clubs. Before filling the replicas the module now calls 0x141363040(0, replica), the
July teardown's own table free (it frees each table and empties the slot list); the builder
then allocates fresh ones.

Live (2026-09-24, world `_FL26G39UECL`, from a day-351 save): play-off filled on day 29 with
ranks 9-24, played 4 and 11 February, eight real winners, round of 16 with sixteen clubs on
24 February; the rest of the knockout ran on its own to the final on 30 May.

### The Conference League knockout and the second season (2026-09-24)

* Reg 187 is past the end of the calendar switch, so its sixteen ties had no dates. The date
  hook gives it reg 6's calendar (the Europa League knockout days). Live: round of 16 on 18/25
  February, quarter-finals, semi-finals and a final on 20 May.
* At the rollover the exe's teardown list (0x141314350) does not contain 186/187, so they kept
  last season's clubs, year 2025 and tables, and the second season had no Conference League.
  The module chains a hook in front of fl26join's on the same function and appends 186 and
  187 to the European list (the one that contains shipped id 2).
* The Champions League and Europa League rolled over on their own: second-season play-off in
  August, both league phases rebuilt with 36 clubs and 144 matches.

### Toward the real 2025/26 format (2026-09-24, built, not yet live)

* **Conference League, six matches.** `mkswiss.py` writes a second table, `FL26_SWISS6`: six
  pots of six (pot = list position / 6), one opponent from every pot including a club's own,
  three at home and three away, 108 matches. Five rounds pair the pots by the 1-factorisation
  of K6 (pot 5 fixed, the others rotating; club k meets club k+r+1 of the other pot), the
  sixth is inside each pot. Each round of 18 is split over two dates, like the eight-round
  table. The module uses it for row 1210 and dates it on the real Thursdays 2/23 Oct,
  6/27 Nov, 11/18 Dec (days 273/274 ... 350/351). The ban on same-country opponents cannot be
  expressed in a static table and is not applied.
* **UEFA bracket.** The play-off follows the fixed tree: 9/10 v 23/24 (bracket I), 11/12 v
  21/22 (II), 13/14 v 19/20 (III), 15/16 v 17/18 (IV), who meets whom inside a bracket drawn.
  Round of 16: 1/2 draw the two winners of IV, 3/4 of III, 5/6 of II, 7/8 of I. The sixteen
  ties are listed 1/2, 7/8, 3/4, 5/6 twice over, which assumes the game pairs neighbouring
  ties in the quarter-finals (to be checked). Seeded clubs are listed second, which on the
  first-knockout screen is the away side of the first leg.
* **Dates.** Play-off 17/24 Feb (days 47/54). Knockouts on UEFA's evenings: Champions League
  10/17 Mar, 7/14 Apr, 28 Apr/5 May, final 30 May; Europa League and Conference League 12/19
  Mar, 9/16 Apr, 30 Apr/7 May, finals 20 and 27 May. Applied only when the calendar returns
  exactly seven dates; anything else is logged and left alone.
* The Conference League teardown list also gets row 1210, whose 144 matches survived the
  first attempt.
