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

## In Mod Studio (branch feature/cwc32)

Leagues > More > **Club World Cup** (`ClubWorldCupDialog` in `pages/builder.py`) writes the recipe's
`club_world_cup`: `on`, `every` (years), `first` (the first year it is played), `keep_old`,
`old_name` and `replace`. Build (`leaguebuilder.club_world_cup`, after the super cups):

- `mkcwc.reshape` on competition 1, the knockout on a free regulation id kept from Build to Build
  (cup_ids `cwc:club_world_cup`);
- with `keep_old`, `mkcwc.intercontinental` first copies the shipped four-club cup onto a
  competition and regulation of its own (cup_ids `cwc:intercontinental`). A world with no free
  competition id gives it the ids of a cup it no longer builds: the dialog unticks that cup
  (`cwc_untick`) and `replace` names it, so the first Build pins its old ids (`cwc_pins`);
- the world file gets `cwc32 ko=<reg> every=<n> first=<year> ic=<reg> iccid=<cid>`;
  fl26swiss.lua hands it to `fl26_swiss_cwc`. Without the line the DLL behaves as before
  (knockout 200, every season).

At run time (fl26swiss.c, `cwc_handoff`): the game's four entrants of regulation 1 go to the
Intercontinental every year (set_clubs + register_all, dated with the shipped regulation 1 days),
and the 32-club draw is made only when the year it is played (June after the draw) is in the
cycle. A career saved before has none of the new rows (`cwc_world` and `ic_world` say no) and
keeps the old cup. Not yet played in the game.

### The field (cwc_quota_field, the user's rule of 2026-11-17)

12 UEFA, 6 CONMEBOL, 5 AFC, 5 CAF, 4 CONCACAF (FIFA's shares; the OFC place, with no OFC clubs in
the game, goes to the AFC and the CAF). Each confederation first takes the champions of its
continental cup of the four seasons before the cup (titles of T-4 .. T-1 for a cup played in June
of T; the confederation is the club's country's, from the world file's confed line): the game's
Champions League (4), Libertadores (10) and AFC Champions League (16) knockouts and every cup of
ours the league champions go to. A club with two titles is in once; the places left go to the
best of the confederation ranking. No limit per country. Pots of eight in list order: UEFA 1-4
and CONMEBOL 1-4, UEFA 5-12, then the other sixteen by points.

The titles and the ranking are fl26cwc.dll's (tools/cwcrank, now in the pack: build-cwc.sh,
sider/experimental/fl26cwc.lua): fl26swiss tells it every winner at the teardowns and at the
draw (`fl26_cwc_champion`), it keeps them in each save's ledger (`K_CHAMP`, six years whatever
the window) and hands them back with the ranking (`fl26_cwc_champions`, `fl26_cwc_ranking`).
Its cycle comes from the same cwc32 line (`fl26_cwc_every`). Without fl26cwc.dll, or with a
confederation it cannot fill, the old access list stands in.
