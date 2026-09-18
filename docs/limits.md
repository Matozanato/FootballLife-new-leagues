# Limits and numbers

What the shipped game holds, what `fl26caps.lua` raises it to, and which walls remain.

| what | shipped | with fl26caps | notes |
|---|---|---|---|
| clubs (team table) | 750 (743 used) | 1,600 | **1,536 clubs in total is a hard wall** elsewhere in the season generator |
| coaches | 1,300 (961 used) | 2,600 | one per club is invented by the game for new clubs |
| competition rulebooks (regulations) | 300 (214 used) | 600 | ids are 16-bit; the date table covers ids 1–255 |
| competitions | 256 ids (91 used, max id 141) | unchanged | ids are one byte in every table |
| players | 30,001 (27,927 used) | 51,729 | the cap must be ≡ 17 mod 32; 719 of our clubs carry a full 30 |
| match records per season | 13,000 | 26,000 | our 39-league season uses 21,010 |
| fixtures list | 2,000 | **8,000** | one record is one round of one competition, stride 0x208. Records are handed back as rounds finish, so a four-season world peaks under 2,700 |
| calendar | 365 days, 280 match ids per day | unchanged | overflow is dropped silently. Beware the obvious measurement: walking the calendar counts what the scheduler *accepted*, so a full day reads as exactly 280 and hides the matches it turned away. The match records carry their own dates and show the real demand — measured once at 280 on the calendar and 351 in the records for the same day |
| menu regions | 24 in use of 29 slots | unchanged | new leagues go into an existing slot |
| league size | 10–30 clubs | — | 10 is the shipped game's own smallest league, not a floor of ours. The round list holds 58 entries, which is a double round robin of 30 exactly; above that the extra rounds are dropped without an error |
| edit block (all tables together) | 0x1877068 bytes | 0x3171a68 bytes | |
| second copy of the tables (used for save/load) | 0x15b6d94 bytes | 0x25a7cc4 bytes | grown by the `mlcopy` part of the set |
| competitions a season can hold at once | 100 | **127** | raised by `fl26hdr127.lua`; entries are never released, so the count only rises — see known-issues.md |
| per-phase standings tables | 600 | 599 | one is spent paying for the wider header; a running season uses about 375 |

## The day counter

The game counts days of the calendar year, not of the season. A Master League season
starts on **day 212 (end of July / 1 August)**; day 365 rolls over to day 1 at New Year; the
season ends in May. When a report says "day 238", that is 26 days after the start — the last
week of August. The hub shows the real date bottom right; quote that in reports.

## Regulation (rulebook) ids covered by the shipped date table

```
11 12 13 49 60 61 62 63 64 65 66 69 70 71 72 73 74 75 76 77 78
93 94 96 98 100 101 102 109 110 111 112 113 114 121 138 139 140 143
```

Each id is mapped to a weekday shift of 0–6 days so that 39 leagues do not all land on the
same weekday. Anything outside this list gets no calendar at all.

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

## Rulebook ids above 175

They work. A league on an id above 175 generates, schedules and plays a full Master League
season. It is invisible in the **Select Team** list only, because that menu is built from a
shorter table. This is worth knowing because it looks exactly like a data error and is not
one.
