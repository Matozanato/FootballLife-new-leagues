# Club World Cup with 32 clubs (unfinished, not in Mod Studio)

The 2025 format -- 32 clubs, eight groups of four played once, then a single-match knockout of
sixteen -- works in the game, but it was never wired into Mod Studio. The code is here for anyone
who wants to finish it. Mod Studio itself does not use it, and nothing below is supported.

## What exists

- **`tools/mkcwc.py`** reshapes competition 1 (the Club World Cup) in the tables: regulation 1
  becomes the group stage (a copy of the Libertadores group stage with one round, replicas
  1025, 2049 ... 8193) and a new regulation, 200 by default (`--ko`), the knockout of sixteen.
  `--dry` prints the plan and writes nothing.

  ```
  python tools/mkcwc.py --base <pesdb dir> --out <livecpk root> [--ko 200] [--dry]
  ```

- **`tools/native/fl26swiss.c`** already carries the run-time half (search `CWC_`): when the game
  hands the Club World Cup its entrants on regulation 1, the field is replaced by 32 clubs from
  league tables (the access list in the source, pots of eight), drawn into eight groups with the
  game's own group draw, handed over to the knockout when the groups end, and dated
  (`CWC_GROUP_DAYS` / `CWC_KO_DAYS`). A world without the reshaped rows (no regulation 200 or no
  replica 1025) is left alone, which is why it is inert in every Mod Studio world.

Tested once in a private world (two seasons in one session): 48/48 group matches and 16/16
knockout matches played, and the July teardown was clean.

## What is missing

- **Mod Studio integration.** `leaguebuilder.py` does not call `mkcwc.py`; the rows have to be
  written into the world by hand or by a new Build step. Check that the knockout regulation id
  is not one the builder already hands out in that world (pass a free one with `--ko`, and change
  `CWC_KO` in fl26swiss.c to match).
- **A configurable field.** The 32 places come from a fixed access list in fl26swiss.c, not from
  the recipe.
- **Every four years.** It plays every season (mid-December); the real one is every four years
  in summer.
- **Calendar.** Its days are fixed and are not checked against the league and continental
  calendars of the world.
- The game's own clubs pools (the only Africa and Oceania clubs it has) go into the fourth pot.
