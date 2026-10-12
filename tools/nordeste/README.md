# Copa do Nordeste 2026 (work in progress)

A Brazilian regional cup on top of the South American cups world: 20 clubs in four groups
of five, A plays B and C plays D (one round, five matchdays), two per group into one-match
quarter-finals A1-C2, B1-D2, C1-A2, D1-B2, then two-leg semi-finals and final.

**Status: experimental.** Checked in game (lab, 0.2.1 modules + fl26caps 3510): the single
Info Database entry, the 50 group matches, the four group tables (0 points from day 1), the
knockout filled on day 118 and played (one-match quarter-finals on day 125, two-leg
semi-finals and final), its menu item live. Not for players yet.

## How it is built

The game's group builder only makes groups of four, and a group of five that plays the
other group's clubs has no shape in the regulation tables. So the cup is three masters:

| | competition | regulations | what it does |
|---|---|---|---|
| matches | carrier (`FL_NORDESTE_JOGOS`, never listed) | a master of 20, rows A/B and C/D of ten | `nordeste_schedule.h`: the 25 cross matches of each row (`gen_handler`), five dates |
| groups shown | the cup (`FL_NORDESTE_2026`, Brazil) | a master of 20, groups A-D of five | registered with no match (`nd_generate_empty`); their tables are written from the rows' results (`nd_tables`) |
| knockout | the cup | one knockout of eight (legs mode 2) | filled in bracket order when the groups end; the quarter-finals are one match (`nd_onematch`, 0x14151d1e0) |

`nordeste_engine.h` (in `tools/native`, included by `fl26swiss.c`) also:

- lists the cup once in Brazil's Info Database category, as a continental competition is
  (the three region tests of the two category lists, `nd_country`);
- leaves the carrier out of the list (`skipph_handler`);
- greys the group stage items until the four tables exist;
- hands a page that asks for the carrier's groups (the table after a match) the groups A-D;
- lights the Knockout stage item once the knockout has matches (`nd_pastgrp`, 0x14151c5e0:
  the shown groups play nothing and never read finished);
- counts the carrier's goals and assists into the cup's rankings;
- ranks a group: points, wins, goal difference, goals scored, then a draw seeded by the
  season and the club (the disciplinary criteria are not read yet).

Everything is inert unless the loader configures it (`fl26_nd_engine_config`).

## Files

- `prepare.py`: resolves the participants against the game's clubs and builds the 14
  missing ones (`--build-clubs`, placeholder squads); writes `nordeste2026.json` and
  `clubs.recipe.json`.
- `build_world.py`: the South American cups world (`sul_recipe.json`: the game's own
  leagues and clubs, no leagues of its own) plus the clubs and the cup's rows; writes
  `package/` and the loader lines. `--logo <picture>` for the cup's emblem.
- `rules.py`, `test_rules.py`: the competition rules as a reference model.
- `test_two_rows.py`: the runtime's exports (fixtures, quarter-finals over 200 seasons,
  bracket order, table rows against rows read from the game).
- `test_package.py`, `verify.py`: the built package and the specification.

```
sh tools/native/build-swiss.sh
python tools/nordeste/build_world.py --base <pesdb dir>
python tools/nordeste/test_two_rows.py
python tools/nordeste/test_package.py
```

## Not done

- disciplinary tie-breaks (cards), card reset after the groups;
- the Copa do Brasil berth for the champion;
- a full season, reload and rollover in game.
