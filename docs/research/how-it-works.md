# How it works, briefly

## What the project changes

Football Life 2026 (PES 2021 engine) keeps every club, coach, competition and fixture in
fixed-size tables inside the executable's memory. Shipped, those tables hold 750 clubs, 1,300
coaches, 300 competition rulebooks and 13,000 match records. Add a few more leagues and the
data simply falls off the end: the season generator drops fixtures without a word, a saved
game loses everything past the shipped count, and a coach lookup lands on the wrong record.

Mod Studio installs and sets up everything below for you; this part is for anyone who wants
to know how it works, or to build by hand ([by-hand.md](../developers/by-hand.md)). The project does two things:

1. **`sider/fl26caps.lua`** — a runtime patch set of 3,510 byte changes, applied by Sider at
   startup, that grows those tables and every piece of code that indexes them:

   | table | shipped | with fl26caps |
   |---|---|---|
   | clubs | 750 | 2,400 |
   | coaches | 1,300 | 3,400 |
   | competition rulebooks (regulations) | 300 | 600 |
   | players | 30,001 | 61,905 |
   | match records per season | 13,000 | 65,000 |
   | fixtures list | 2,000 | 8,000 |
   | competitions a season can hold | 100 | 255 with `fl26hdr255.lua` (0.2.2; replaces `fl26hdr127.lua` and `fl26hdr192.lua`) |
   | menu regions | 29 | 128 with `fl26reg128.lua` (0.2.2; replaces `fl26reg64.lua`) |
   | Select Team slots | 124 | 250 with `fl26slots250.lua` |

   Every module verifies the bytes it is about to change and refuses to touch a different
   game build. If anything does not match, the game runs unmodified and `sider.log` says why.

2. **`tools/`** — Python scripts that build a set of new leagues and placeholder clubs
   (with squads) from **your own** game data, as a Sider `livecpk` root. No game data is
   shipped in this repository; everything is generated on your machine from your install.

Plus seven small **null-guard modules** that stop known crashes in the game's own code which
the larger world exposes, **`fl26hdr127.lua`**, which widens the table a season uses to
hold its competitions from 100 to 127 — the fix for league tables showing 76 matches played
and ~130 points; Mod Studio 0.2.2 installs `experimental/fl26hdr255.lua` (255) in its place —
and **`fl26joindll.lua` + `fl26join.dll`**, which get every added league
*into* the season and, since 2026-09-23, *out of it again* at the end. The game registers
and closes competitions from lists compiled into the executable, so a new league standing in
a country of its own was never presented to the season at all, and once it was, it was never
closed and carried its table on into the next season. The module handles both. It is the one
compiled piece in the main folder; its source and how to build it are in
[tools/native/](../../tools/native/README.md).

`sider/experimental/` holds more that go further and **were first run on our own
test worlds**: 255 competitions instead of 127; every league selectable in the Select Team
list (250 slots), under its own name, showing its own clubs; 128 menu regions instead of 29; a league rank
wide enough for a pyramid five divisions deep, with the relegation gate to match; a career
that starts in August instead of January; promotion and relegation through a whole pyramid,
not just its top joint; guards for the Super Cup and the play-off results screen; **the 2024 European format** for the
Champions League, the Europa League and a new Conference League, filled from a UEFA access
list, with leagues of 10 to 24 clubs; the added countries listed by name under
Database -> Competition Info; and every added league in Edit mode's team lists. They abort cleanly if anything does
not match, and they are the part where another pair of hands helps most —
[what they are, and in what order](../../sider/experimental/README.md).

## Where the limits live

When a mode such as Master League starts, FL26 allocates one large block of memory (the
"edit block", 0x1877068 bytes) and lays every table out inside it at fixed offsets: players
first, then clubs, coaches, competition rulebooks, match records, and a long tail of smaller
tables. The sizes are constants in the code: the allocation size, the bounds checks
(`cmp esi, 750`), the offsets of every table after the first, and the strides of loops that
copy or reset them.

A new league is therefore not a data problem alone. The data side is easy — a league is one
row in each of three `pesdb` tables (`Competition.bin`, `CompetitionRegulation.bin`,
`CompetitionEntry.bin`), and Sider's `livecpk` overrides those files at runtime. The block is
the problem: the 751st club has nowhere to go.

## What fl26caps.lua does

`tools/patchset.py` reads `patches/layout.json` (which table sits where, what stride, which
constants) and `patches/attrib.json` (every instruction in the exe that references a table,
found by disassembly and attributed to its table), and emits one list of byte patches:

- the allocation and free sizes of the block and of its backup copy,
- every bounds check on a grown table,
- every displacement that addresses a table that had to move to make room,
- the second copy of the tables that the game builds when it saves and loads a season
  (it kept the shipped sizes, which is why saves used to lose the new clubs),
- a small "date spread" stub in spare bytes of the code section that gives new rulebook ids
  a fixture calendar on a weekday of our choosing.

The Lua module reads every target address first and compares it to the bytes the generator
saw. If one byte differs, nothing is written. That is what makes it safe to hand out: on any
other build it simply does nothing.

## The rulebook id decides whether a league ever plays

This is the single thing that costs newcomers the most time, so it is worth stating plainly.

When a season is generated, the game does not work out a league's fixture dates from the
league you created. It takes the rulebook's **id**, looks that id up in a switch compiled
into the executable, and copies out a fixed list of dates — one record per round, held as a
static array in the code. A league competition gets 38 of them; the shipped domestic cup
gets ten.

Most of the free ids do not appear in that switch. They fall through to an entry that
returns without writing anything. The competition still exists, still shows up in the menus,
still has its clubs and its rounds — and never plays, because no round was ever put on a
calendar day. Nothing reports this. It looks exactly like a league that is being ignored.

That is what the "date spread" stub in `fl26caps.lua` exists for: it gives the ids we use
their own entry, pointing at the same list of league dates the game already carries, plus a
shift of 0 to 6 days so that not every new league wants the same weekday (see
[limits.md](limits.md)).

Two practical consequences:

- **Pick your rulebook ids from the list that is known to be dated**, or regenerate the
  patch set with `--date-keys` for the ids you actually used. A league outside both is
  silently never scheduled.
- **A cup takes a different route, and it works.** A cup cannot live in the low id range we
  use for leagues, and the shipped switch stops consulting its table above id 175 — so the
  module also hooks the one branch that handles those ids, which is the only place a high id
  can be caught. In practice a cup does not even need that: the game fills a cup from the
  first league in its region and dates it with the shipped sixteen-club bracket, so a cup
  whose feeder league has sixteen clubs plays out fully dated with no patch of its own.

## How a league gets into a season, and what fl26join.dll does

Being dated is necessary and not sufficient. A competition also has to be *registered* into
the season, and that happens on two occasions, both driven by lists compiled into the
executable rather than by the data files:

1. **At creation**, the season builder walks a fixed include list of calendar-year
   competitions (the leagues that run January to December) and registers those.
2. **In play**, each time the calendar reaches a registration date, the game calls its
   registration routine with the ids due that day. That list comes from a case table over
   ids 2..175, and most of its entries are empty. A league hanging under a listed one
   through the promotion link is picked up with it; a league standing on its own is not.

The routine every competition passes on its way in was measured live, and it admits any id
that has a record with its season flag set — which every one of ours has. So a new league
in a country of its own is not refused; it is never asked about. It exists, it is dated, and
nothing presents it.

`fl26join.dll` is the piece that presents it. `fl26joindll.lua` loads it at startup and
hands it the rulebook ids of the added leagues; the DLL hooks the registration routine and
appends those ids to the vector it receives, after the game's own, skipping any whose record
already carries a season year. It also answers the builder's creation-time question about
our ids with "no" (a skip, to the builder), because the three of our ids that reuse shipped
calendar-year ids were otherwise registered twice and got a doubled schedule. It writes no
table; the game does the rest as it would for its own leagues. It is a DLL rather than a
Lua patch because the change is a few instructions of glue on a live call, with a vector to
grow, and that is easier to get right in C than in bytes. The source is in `tools/native/`.

Two things follow. The id list in `fl26joindll.lua` has to name your leagues, the same way
the date table in `fl26caps.lua` has to. And a season started with a club from a
stand-alone league still opens in January, because the game picks the opening date before
the registration day on which the league joins; the league's own season is then dated from
August.

## The null guards

A world of up to 2,400 clubs walks code paths the shipped data never reaches. Several of them
look up a record and read through the result without checking for "not found". Each
`fl26nullguardN.lua` replaces a few bytes at one such site with a jump to a tiny stub that
tests the pointer and takes the function's own existing "nothing to do" path when it is null.
They are hand-written, verified by disassembling the emitted bytes back, and documented in
their headers with the crash they stop and the evidence for it.

## Why placeholders

The tools prove capacity. `mkworld.py` clones existing club records with fresh ids and
names, `mkplayers.py` clones shipped squads and renames the players, so every new club is
internally consistent without inventing a single number. Real content is a different job —
the usual Team.bin / kit / face editing — and it sits on top of these files unchanged.

The full research log behind this (several thousand lines, addresses, dead ends and all) is
not part of this repository; the parts that a developer needs are summarised in
[for-developers.md](../developers/for-developers.md).
