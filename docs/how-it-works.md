# How it works, briefly

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

## The null guards

A world of 1,536 clubs walks code paths the shipped data never reaches. Several of them
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
[for-developers.md](for-developers.md).
