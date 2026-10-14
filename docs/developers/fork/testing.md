# Testing

There are four layers. Small Python tests check one rule each. `regress018.py` builds a set of
test recipes and checks the worlds without the game. `test_modstudio_build.py` runs Build and
install through Mod Studio itself, on a PC set up like a player's. Only the game itself proves
that a world plays. Run all four before a release.

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
| `test_dll_check.py` | | Install the modules stops, naming the file, when an antivirus takes or empties a DLL right after the copy; Home / Diagnostics (`checks.dll_problems`) and *4. Check* say the same while a switched-on module's DLL is missing |
| `test_game_supercups.py` | tables | a super cup added to a game league (`game_cups`) is a two-club cup in the league's region, dated at the end of January in a February-December country, and its `gsuper` line names the league and the cup that fill it; fl26joindll and fl26swiss read that line; a division's line (a new J2 under the J.League, `scup=97`) never gives fl26swiss a calendar super cup's league (runs the Lua block when `lupa` is installed) |
| `test_febdec_cups.py` | tables | a February-December new league's national cup and super cup are accepted, a league cup refused, their `dates` lines take the calendar prototypes, and Build's summary puts the super cup at the end of January |
| `test_febdec_division.py` | tables | a division under a game league that plays February-December (Colombia) plays that season, so Build refuses a split or Apertura/Clausura on it |
| `test_import_csv.py` | | Import CSV: a row naming a game player of another club makes him join |
| `test_keep_added.py` | | pictures put by hand into the world folder survive a Build (`keep_added`) |
| `test_keep_continent.py` | | a drag on the Leagues page keeps each continent's Select Team places |
| `test_keep_continental.py` | tables | a game club moved into a new league can keep its continental places (#84, `keep`); with a swap, the other club gets only the league and cup rows |
| `test_keep_ids.py` | | the world's own players keep the ids of the last Build (#126); a player listed twice moves once, a stale ids file is skipped |
| `test_kitpics.py` | | `kitpics.py`: a Kit Server club folder from kit pictures; the picture branch of the Kits page (needs Pillow) |
| `test_kits_import.py` | | the kit-import helpers of `pages/kits.py` (works without PySide6: the helpers are pulled out of the source) |
| `test_lbpack.py` | | the two bundles contain every part in order, and the wrapper calls nothing Sider's Lua lacks (no `pcall`) |
| `test_newlife_fill.py` | | a placeholder player who stays at a NewLife club is brought to the club's level |
| `test_newlife_game.py` | NewLife folder, tables | *Bring the game's leagues to this season*: clubs that went up/down swap, a club that left the game's world hands its place to the release's, squads come from the release, hand edits stay, undo takes back exactly what it did |
| `test_newlife_pins.py` | folder with a `Team.bin` | a NewLife club keeps its world id when a league before it changes or goes (`newlife_ids`) |
| `test_newlife_put.py` | NewLife folder, folder with a `Team.bin` | NewLife clubs put into a hand-made league (#83): name, kits, id and squad at that place |
| `test_newlife_update.py` | two NewLife folders (older, newer) | *Update my leagues to this version* takes the newer clubs and squads and keeps the league's own settings (and a package's kit folders with their clubs) |
| `test_own_kit_line.py` | | a kit line of your own in Kit Server's `map.txt` wins over a league package's kit and a made one (no line or folder of ours, a line an older Build switched off comes back on); package kit folders move with their club on Remove / Insert / Move club |
| `test_pack_guard.py` | | the release guard (`mszip.check_pack`): a known crash site, a `fl26caps.lua` that is not the generated set or not the game's stops the zip; other modules that differ from the game's are listed |
| `test_retired_modules.py` | | `ensure_modules` switches a bundled module off only when its bundle is loaded too |
| `test_shift_newlife.py` | | Remove club / Insert club move the league's NewLife ids with the places |
| `test_squadimport.py` | | the table import reads the game's player id and the fields |
| `test_write_access.py` | | a game folder Windows does not let Mod Studio write in (a deny-write entry made with `icacls`, as under Program Files) is found before a write, a refused write is told from other errors, and the message says what to do (run as administrator, or move the game) |

```
python tools/test_cup_draw.py
python tools/test_newlife_update.py <NewLife folder A> <NewLife folder B>
```

A NewLife folder is an unpacked release (see [newlife-format.md](newlife-format.md)).

## `test_modstudio_build.py`: Build through Mod Studio, on a player's PC

```
python tools/test_modstudio_build.py <game folder> [<tables>] [--recipe <json>] [--keep]
```

`regress018.py` and the command line builder run on the developer's PC, where `FL26_DIR` is
set and the game sits where the tools expect it. A player's PC is not like that, and 0.2.2
went out with two Build bugs that only showed there: Mod Studio closed during Build (an error
inside the worker thread), and Build stopped with "FL_2026.exe not found at C:\Football Life
2026" when the game was anywhere else (OneDrive, another drive). This test runs the Build
page's *Build and install* offscreen with:

- the game in a temporary folder with a space and a letter outside ASCII in its path
  (`Football Life Ž test\Juego`), never `C:\Football Life 2026`;
- `FL26_DIR`, `FL26_EXE` and `FL26_SIDER` removed from the environment, so Mod Studio has only
  its Settings;
- a fresh Mod Studio settings folder holding only the tables and the recipe.

It passes when Build and install finishes (the after-build window), the output has no error,
the game's cup dates were read from the exe in that folder, and the world is built and
switched on. `<game folder>` only gives `FL_2026.exe`; `<tables>` defaults to
`%APPDATA%\FL26ModStudio	ables`; the recipe defaults to `testdata/regress018/eu_places.json`.
Needs PySide6. Before a release, also start the exe from the release zip once and press Build.

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
   - `fl26caps: applied all 3510 patches`;
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
