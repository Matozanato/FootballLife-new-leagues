# Testing

There are three layers. Small Python tests check one rule each. `regress018.py` builds a set of
test recipes and checks the worlds without the game. Only the game itself proves that a world
plays. Run all three before a release.

The tests need no framework. Each is a script with plain `assert`s. It stops at the first
failure, and most print an `ok` line per check. Run them from the repository root.

## The game's tables

Several tests and both build checks need the game's own unpacked tables (the `pesdb` folder).
Mod Studio unpacks them to `%APPDATA%\FL26ModStudio\tables` (Settings > *Unpack the game's
tables*). Pass that folder with `--base`, or set `FL26_PESDB` (several folders separated by `;`,
newest first). `FL26_DIR` is the game folder (or `FL26_EXE` the exe) for the tools that read the
exe. See `tools/flpaths.py`.

## The Python tests

| test | arguments | what it proves |
|---|---|---|
| `test_country_order.py` | | League order (0.2.0) follows the recipe's `country_order` and never `league_order` (the Leagues page's drag order) |
| `test_crestmatch.py` | | the crest file name matcher |
| `test_cup_draw.py` | | `cup_draw` becomes the `cupdraw` line; `seeded` unless the recipe says otherwise; any other value is refused |
| `test_febdec_division.py` | tables | a division under a game league that plays February-December (Colombia) plays that season, so Build refuses a split or Apertura/Clausura on it |
| `test_import_csv.py` | | Import CSV: a row naming a game player of another club makes him join |
| `test_keep_added.py` | | pictures put by hand into the world folder survive a Build (`keep_added`) |
| `test_keep_continent.py` | | a drag on the Leagues page keeps each continent's Select Team places |
| `test_keep_continental.py` | tables | a game club moved into a new league can keep its continental places (#84, `keep`); with a swap, the other club gets only the league and cup rows |
| `test_kitpics.py` | | `kitpics.py`: a Kit Server club folder from kit pictures; the picture branch of the Kits page (needs Pillow) |
| `test_kits_import.py` | | the kit-import helpers of `pages/kits.py` (works without PySide6: the helpers are pulled out of the source) |
| `test_lbpack.py` | | the two bundles contain every part in order, and the wrapper calls nothing Sider's Lua lacks (no `pcall`) |
| `test_newlife_fill.py` | | a placeholder player who stays at a NewLife club is brought to the club's level |
| `test_newlife_game.py` | NewLife folder, tables | *Bring the game's leagues to this season*: clubs that went up/down swap, a club that left the game's world hands its place to the release's, squads come from the release, hand edits stay, undo takes back exactly what it did |
| `test_newlife_pins.py` | folder with a `Team.bin` | a NewLife club keeps its world id when a league before it changes or goes (`newlife_ids`) |
| `test_newlife_put.py` | NewLife folder, folder with a `Team.bin` | NewLife clubs put into a hand-made league (#83): name, kits, id and squad at that place |
| `test_newlife_update.py` | two NewLife folders (older, newer) | *Update my leagues to this version* takes the newer clubs and squads and keeps the league's own settings |
| `test_retired_modules.py` | | `ensure_modules` switches a bundled module off only when its bundle is loaded too |
| `test_shift_newlife.py` | | Remove club / Insert club move the league's NewLife ids with the places |
| `test_squadimport.py` | | the table import reads the game's player id and the fields |

```
python tools/test_cup_draw.py
python tools/test_newlife_update.py <NewLife folder A> <NewLife folder B>
```

A NewLife folder is an unpacked release (see [newlife-format.md](newlife-format.md)).

## `regress018.py`: build every test recipe

```
python tools/regress018.py --base <tables>              # all recipes
python tools/regress018.py --base <tables> --only cup   # recipes whose name contains "cup"
```

It takes every `*.json` in `tools/testdata/buildcheck/` and `tools/testdata/regress018/`, and
for each one:

1. builds it with `leaguebuilder.py build` into `out/scratch/regress/<name>`. A failed build is
   one FAIL line with the last five lines of output;
2. runs `buildcheck.py` on the built tables;
3. counts the European days: every league of the world with European places in its recipe may
   play on at most one of the European match days (`leaguebuilder.EURO_DAYS`, GitHub #54).

The recipes:

| file | covers |
|---|---|
| `buildcheck/1_second_div_under_game_league` | a new division under a league of the game (France) |
| `buildcheck/2_three_tiers_outside_europe` | a three-tier pyramid outside Europe |
| `buildcheck/3_split_league` | a split league (12 clubs, two groups of 6) |
| `buildcheck/4_league_cup` | a league with a league cup |
| `regress018/acl_two` | a second division under an AFC league of the game |
| `regress018/cup_exact_32` | a national cup of two divisions with exactly 32 clubs |
| `regress018/eu_places` | European places of three new European leagues, one with a league cup |
| `regress018/europe_first` | the same world with `europe_first` |
| `regress018/game_cups` | `game_cups`: league and super cups for countries of the game |
| `regress018/hk_two_tiers` | two tiers under an AFC league of the game, with `edits`, `players`, `uecl` and `caf_super_cup` |
| `regress018/others` | a league plus the "Other ..." groups (`others`) |

It prints a summary table and exits 1 on any FAIL. Add a recipe there for every feature that
changes what Build writes.

## `buildcheck.py`: one world, offline

```
python tools/buildcheck.py <world's pesdb folder> --base <tables>
```

It runs five checks:

1. Every regulation the world adds or changes has its names. An empty name slot the base
   fills, or a gap byte set that the base keeps zero, is a FAIL.
2. No two regulations share an id.
3. Every team in `CompetitionEntry.bin` exists in `Team.bin`.
4. A club whose league changed has its "Other ..." group bits cleared (`Team.bin` +0x4f).
5. Record counts compared with the base (information only).

Checks 1 and 3 count only what the world introduces, so a normal world passes.

## `langcheck.py`: translations

```
python tools/langcheck.py               # per language: translated / missing
python tools/langcheck.py --missing es  # English strings es.json lacks
python tools/langcheck.py --unused      # keys no _("...") uses any more
```

## The C tests

```
cd tools/native
zig cc -O2 -o swissdraw_test.exe swissdraw_test.c && swissdraw_test.exe [runs] [seed]
zig cc -O2 -fno-sanitize=undefined test_chain_apclau.c -o test_chain_apclau.exe && test_chain_apclau.exe
```

- `swissdraw_test.c` runs random fields through the league-phase draw of `fl26swiss_draw.h`
  and checks the association rule: no club meets its own association, and none meets more
  than two clubs of another.
- `test_chain_apclau.c` includes `fl26chain.c`, builds a fake game image and checks that an
  Apertura/Clausura league's standings count both phases (#106).

Delete the `.exe` files afterwards.

## In the game

Nothing above starts the game. Before a release, play this checklist with a world that uses
your change, with every module installed by Build:

1. **Start the game and read `sider.log`.**
   - `fl26caps: applied all 3519 patches`;
   - no `MISMATCH`, `ABORTED` or status number from any module;
   - every reader says `world file -- <n> leagues`. Mod Studio's Build > *Check* reads this
     for you.
2. **New Master League career.** Pick a club of a new league in Select Team. Check that
   the league, the clubs and the squads are there, and the cups in Competition Info.
3. **Past the first matchday.** Play or skip to after the first league round. Our leagues
   have played, the results list shows them, and no crash.
4. **The first European / continental week**, if the world has European places: the draw has
   36 clubs, and our clubs are in it where the recipe says.
5. **Through the season change.** Skip to the end of the season and into the next.
   - Promotion and relegation happen in every chain.
   - The cups are drawn again.
   - The new season has a calendar for every league.
   This is where most season bugs show up.
6. **Save and load.** Save during the season, quit, start the game again and load. The
   manager's name, the calendar and the standings are as they were. Also save right after the
   season change and load that save.
7. **Edit mode.** Change a club of ours, save, restart and check the change is kept.

A career saved under another patch set does not load. Start a new career when you test a
change to `fl26caps`.
