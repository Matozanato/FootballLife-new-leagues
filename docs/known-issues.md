# Known issues

Honest list, as of 2026-09-16. Addresses are given so that a fault offset in your Event
Viewer can be matched against them: the offset is the address minus `0x140000000`
(so `0x1414c674d` shows up as exception offset `0x14c674d`).

## Crashes

| where | address | status |
|---|---|---|
| Season generation, about one time in two | `0x1484ed4c0` | Shipped game bug (occurs without any mod). Not guarded. Just start the season again. |
| Exhibition kick-off with new clubs | `0x141fea5ba` | **Fixed** by `fl26nullguard.lua`. |
| Loading a season (schedule read) | `0x140cd6a1c` | **Fixed** by `fl26nullguard3.lua`. |
| Mid-season, calendar advance | `0x140fc9238` | **Fixed** by `fl26nullguard2.lua`. |
| Calendar advance, coach record walker | `0x141572125` | **Fixed** by `fl26nullguard4.lua`. The root cause (a mis-placed coach table after a load) was a bug in this patch set and is also fixed at the source. |
| Calendar advance, AI lineup pass, field getter | `0x1414c674d` | **Guarded** by `fl26nullguard5.lua`. |
| Calendar advance, AI lineup pass, a day after matchday 1 | `0x1415032f0` | **Fixed 2026-09-16** in `fl26caps.lua` — see below. Update the module if you downloaded earlier. |
| Startup, 9–11 seconds in, occasionally | — | Shipped game bug, reproduces on a clean install. Start again. |

## Missing or unverified features

- **Continental competitions.** New clubs do not qualify for Champions League / Europa
  League. The qualification table is a static table in the exe; extending it is mapped but
  not done.
- **Cups.** `mkcup.py` produces a valid knockout competition, but no cup has been carried
  through a Master League season yet.
- **Menu regions.** New leagues can only be placed in a menu region the game already
  knows (default: England's slot). The region name table is understood; adding regions is a
  separate patch that has not been verified in play.
- **Kits, names, players.** All placeholders / clones. Not a bug, but a limitation of this
  beta: the tools prove capacity, they do not author content.
- **Second season, promotion/relegation between new leagues, transfers, finances**: not
  observed yet. Report what you see.

## Things that are by design and will bite you

- **Saves are tied to the world.** A save made with world A does not load with world B or
  with the shipped game. Move your saves aside when you switch roots.
- **Rulebook ids must be in the date table** (39 ids shipped in `fl26caps.lua`). A league
  outside it is silently never scheduled. See build-your-world.md.
- **1,536 clubs in total is a wall** in the season generator, independent of the 1,600 table
  size. 793 new clubs is the most we have run.
- **A calendar day holds 280 match ids**; overflow is dropped silently by the scheduler.
  Our 39-league world peaks at 251 on the busiest day. More leagues on the same weekdays will
  lose fixtures without an error.
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
