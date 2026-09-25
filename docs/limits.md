# Limits and numbers

What the shipped game holds, what `fl26caps.lua` raises it to, and which walls remain.

| what | shipped | with fl26caps | notes |
|---|---|---|---|
| clubs (team table) | 750 (743 used) | 1,600 | **1,536 clubs in total is a hard wall** elsewhere in the season generator |
| coaches | 1,300 (961 used) | 2,600 | one per club is invented by the game for new clubs |
| competition rulebooks (regulations) | 300 (214 used) | 600 | ids are 16-bit; the date table covers ids 1–255 |
| competitions | 256 ids (91 used, max id 141) | unchanged | ids are one byte in every table |
| players | 30,001 (27,927 used) | 51,729 | the cap must be ≡ 17 mod 32; 719 of our clubs carry a full 30 |
| match records per season | 13,000 | 46,000 | our 39-league season of 20-club leagues used 21,010; raised on 2026-09-24 so that an old season still being freed and the new one being built both fit at the rollover |
| fixtures list | 2,000 | **8,000** | one record is one round of one competition, stride 0x208. Records are handed back as rounds finish, so a four-season world peaks under 2,700 |
| calendar | 365 days, 280 match ids per day | unchanged | overflow is dropped silently. Beware the obvious measurement: walking the calendar counts what the scheduler *accepted*, so a full day reads as exactly 280 and hides the matches it turned away. The match records carry their own dates and show the real demand — measured once at 280 on the calendar and 351 in the records for the same day |
| menu regions | 24 in use of 29 slots | unchanged | new leagues go into an existing slot |
| league size | 10–30 clubs | — | 10 is the shipped game's own smallest league, not a floor of ours. The round list holds 58 entries, which is a double round robin of 30 exactly; above that the extra rounds are dropped without an error |
| edit block (all tables together) | 0x1877068 bytes | 0x3cd4ae8 bytes | |
| second copy of the tables (used for save/load) | 0x15b6d94 bytes | 0x25a7cc4 bytes | grown by the `mlcopy` part of the set |
| competitions a season can hold at once | 100 | **127**, or **192** with the experimental module | raised by `fl26hdr127.lua`; entries are never released, so the count only rises — see known-issues.md |
| per-phase standings tables | 600 | 599 (597 at 192) | they pay for the wider header; a running season uses about 375 |

## Divisions: three values, but a pyramid can be deeper than three

A competition's regulation record carries the division at `F+0x10` bits 15-17, and the game
reads it at runtime as `+0x304` bits 30-31. The setter is three instructions:

    0x1414c9cc0   and dword [rcx+0x304], 0x3fffffff
                  movzx eax, dl ; shl eax, 30 ; or [rcx+0x304], eax

Two bits survive whatever the file says, so the only division *values* are **1, 2 and 3**.
That is not the same as a three-deep ceiling, which is what an earlier version of this page
said. Who goes up and who comes down is decided by one function, and it takes the identity of
the partner league from the link fields, not from the division number:

    tier >= 2                        -> promoted into the league named by +0x7c
    tier == 1, bottom three          -> relegated into the league named by +0x7e
    below == 3 and this == 2, b. 3   -> relegated into the league named by +0x7e

The promotion gate is a "2 or more", so a **fourth** division marked 3 and pointed at the
third promotes its champion with no patch at all. Only the way down is missing: a tier-3
league matches neither relegation gate, so clubs climb out of the fourth division and never
fall back into it. That half is one byte -- `jne` to `jb` at 0x141510617 turns the second
relegation gate from "exactly 2" into "2 or 3" -- and `sider/experimental/fl26deep4.lua` writes it. With
it, four and five divisions behave like two and three. How many go down is not adjustable
from the data: both relegation tails are hard-coded to the bottom three.

Two things follow that are easy to trip over:

* **European places go to the tier-1 leagues of a region.** Every league built by these tools
  is a copy of a first-division prototype, so unless you pass `--tiers`, every league you add
  is a first division -- and a first division in England's region is offered European places
  by construction. That is the engine behaving normally with the data it was given.
* **Promotion needs the lower league to be tier 2 or 3.** The resolver only looks for the
  league above when the tier is at least 2, so a "pyramid" of three first divisions never
  promotes anybody. `mkworld.py --tiers 1,2,3 --group-regions 3` builds them properly.

## The day counter

The game counts days of the calendar year, not of the season. A Master League season
starts on **day 212 (end of July / 1 August)**; day 365 rolls over to day 1 at New Year; the
season ends in May. When a report says "day 238", that is 26 days after the start — the last
week of August. The hub shows the real date bottom right; quote that in reports.

## Regulation (rulebook) ids covered by the shipped date table

```
11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121
138 139 140 143 144 145 146 170 171 173 174 176 178 179 180 181 182 183 184 185 190
```

Read straight out of the shipped `sider/fl26caps.lua` (the 256-byte table at
`0x14252e690`, where `0xff` means "no calendar"). Each of the 40 is mapped to a weekday
shift of 0–6 days so that the leagues do not all land on the same weekday. 190 is the 25th
league in worlds built from 25 September 2026 on, 145 the same league in older worlds (see
[build-your-world.md](build-your-world.md)). Anything outside this list gets no calendar at
all, even though the stub itself is reached for every id from 1 to 1025.

## Game build

`FL_2026.exe` file version 26.0.0.0, 458,910,720 bytes,
SHA-256 `7c27ecb303b71331e36f9ccd8ac879f0f0d8c56c754bd4d0d2e9c8353464f847`.
Bundled Sider: `sider.dll` 7.3.3.0. The exe has no ASLR, which is why absolute addresses
are stable between runs and machines.

## The ceiling that costs you rounds, and how to live with it

A calendar day holds 280 matches. The scheduler drops the rest without a word: no error, no
entry in any log, nothing in the world files. A league simply plays one round fewer than it
should, and the only way to notice is to count.

The ceiling cannot usefully be raised. What works is to stop every league from wanting the
same weekday. Each new league is given a whole-number shift of 0 to 6 days, so moving a
league from shift a to shift b moves all of its fixtures by (b - a) days; `patchset.py`
takes that assignment as `--date-offsets`.

Dealing the shifts round-robin is *not* good enough, because the shipped competitions are
not spread evenly either: some weekdays start out much busier than others, and an even deal
that ignores them can be worse than the uneven one it replaced. `tools/dayplan.py` reads the
season out of the running game, separates the shipped load from each of your leagues' own
load, and searches for the assignment that makes the busiest day as quiet as it can be. It
prints the `--date-offsets` argument, so the loop is: create a season, measure it,
regenerate the set, create the season again.

Use `--demand` after the first rollover. Walking the calendar shows only what was accepted;
reading the match records shows what was wanted, including everything that was turned away.

## The three walls we are working on now

Written down because they are the next things to move, and because knowing where a ceiling
*is not* saves the next person the same search.

**The competition header, 100 → 127 → 192.** 127 was not the engine's limit but a byte's:
all thirteen bounds are `cmp r32, 0x64`, and 0x7f is the largest value that fits in the
one-byte immediate. Each of those thirteen is a compare plus a short branch — five bytes,
six with a prefix — which is exactly the room a long jump needs, so each can be redirected
to a stub holding a wider compare. `sider/experimental/fl26hdr192.lua` does that, at a price
of three of the 600 per-phase tables. Not played yet; that is what the experimental folder
is for.

**Players, 51,729.** Not an engine number either: the player table starts at the very
beginning of the block and cannot be moved, so it grows into whatever sits above it, and
what sits above it is the season calendar. Move the calendar and the ceiling becomes 61,905
— another 10,000 players, about 339 squads of thirty. The work that moves the calendar is
done but not yet played, so it is not published here.

**1,536 clubs.** Still the wall, and still not explained. What is now certain is that the
number is not written in the executable at all: no array is bounded at 1536 with any stride,
the constant appears in exactly two comparisons and both are message-code switches, and no
`mov` of it counts clubs. So it is either a capacity computed while the game runs or a
structure that simply ends, with nothing comparing anything. Both leave a trace in memory
rather than in the file, which is what `tools/vecscan.py` looks for: it reads the running
game and reports every vector whose capacity — `(end - first) / element size`, a number
written nowhere — is exactly 1,536. **If you get anywhere near this wall, running it with a
season loaded and posting the output would genuinely help.**

    python tools/vecscan.py 1536
    python tools/vecscan.py --used <however many clubs your world has>

It attaches no debugger (this exe kills itself under one), reads only, and writes nothing.

## Rulebook ids above 175

They work. A league on an id above 175 generates, schedules and plays a full Master League
season. It is invisible in the **Select Team** list only, because that menu is built from a
shorter table. This is worth knowing because it looks exactly like a data error and is not
one.
