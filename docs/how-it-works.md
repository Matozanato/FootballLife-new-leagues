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
