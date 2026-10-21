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
| `test_auto_formation.py` | tables | a new club with no formation in the recipe gets the one its squad fits (`lbplayers.pick_formation`): two strikers play two up front, wingers three forwards, three centre backs three or five at the back; in a built world the clubs of one league play different formations with their best eleven in them, and a club's or league's formation from the recipe stands |
| `test_country_order.py` | | League order (0.2.0) follows the recipe's `country_order` and never `league_order` (the Leagues page's drag order) |
| `test_crestmatch.py` | | the crest file name matcher |
| `test_cup_draw.py` | | `cup_draw` becomes the `cupdraw` line; `seeded` unless the recipe says otherwise; any other value is refused |
| `test_dll_check.py` | | Install the modules stops, naming the file, when an antivirus takes or empties a DLL right after the copy; Home / Diagnostics (`checks.dll_problems`) and *4. Check* say the same while a switched-on module's DLL is missing |
| `test_conmebol_modern.py` | tables | the modern CONMEBOL competitions (#146) only when picked: a recipe with Libertadores, qualifying and Copa Sudamericana places plans and builds the classic competitions (no phases, first stage, Recopa or helper ids); `"conmebol": "modern"` or a phase / first-stage / country place picks them, switching off takes out only those places, `recipe_from_plan` keeps the switch; the League dialog's list keeps a place it does not offer (offscreen Qt); a modern world built, then with a league and its cups added in front, then without it, keeps every CONMEBOL competition and regulation id (builds in a temporary game folder) |
| `test_game_supercups.py` | tables | a super cup added to a game league (`game_cups`) is a two-club cup in the league's region, dated at the end of January in a February-December country, and its `gsuper` line names the league and the cup that fill it; fl26joindll and fl26swiss read that line; a division's line (a new J2 under the J.League, `scup=97`) never gives fl26swiss a calendar super cup's league (runs the Lua block when `lupa` is installed) |
| `test_febdec_cups.py` | tables | a February-December new league's national cup and super cup are accepted, a league cup refused, their `dates` lines take the calendar prototypes, and Build's summary puts the super cup at the end of January |
| `test_febdec_division.py` | tables | a division under a game league that plays February-December (Colombia) plays that season, so Build refuses a split or Apertura/Clausura on it |
| `test_finished_cap.py` | tables | the player cap is for the finished world: a world over it only halfway through Build (placeholders a club's own squad replaces go at the end) is built with squads of 30; one over it when done is built again with smaller squads; one too big even at 22 a club is refused |
| `test_build_apart.py` | tables | Build runs in a process of its own: the same tables as built in the window's process, the log lines and a BuildError come back, and the window's thread is not held up while it builds |
| `test_filecache.py` | | a file read on every page visit (the built world's plan) is read again only when it changes; a changed or removed file is never served from before |
| `test_import_csv.py` | | Import CSV: a row naming a game player of another club makes him join |
| `test_keep_added.py` | | pictures put by hand into the world folder survive a Build (`keep_added`) |
| `test_keep_continent.py` | | a drag on the Leagues page keeps each continent's Select Team places |
| `test_keep_continental.py` | tables | a game club moved into a new league can keep its continental places (#84, `keep`); with a swap, the other club gets only the league and cup rows |
| `test_keep_ids.py` | | the world's own players keep the ids of the last Build (#126); a player listed twice moves once, a stale ids file is skipped |
| `test_keep_ids_people.py` | | a rebuilt world keeps each player's id with the player, not his squad place: a doubled player taken out (B52) moves nobody else's id; NewLife id, name and birth date, a unique name, then the place; the id of a player who left goes to nobody (until no other id is free, with a NOTE) |
| `test_kit_crest.py` | | `kitmaker.py`: the chest crest of a drawn kit stands upright and the shorts crest is turned a quarter clockwise, as the shorts lie in the kit texture (B138; needs Pillow) |
| `test_kitpics.py` | | `kitpics.py`: a Kit Server club folder from kit pictures; the picture branch of the Kits page (needs Pillow) |
| `test_kits_import.py` | | the kit-import helpers of `pages/kits.py` (works without PySide6: the helpers are pulled out of the source) |
| `test_lbpack.py` | | the two bundles contain every part in order, and the wrapper calls nothing Sider's Lua lacks (no `pcall`) |
| `test_newlife_fill.py` | | a placeholder player who stays at a NewLife club is brought to the club's level |
| `test_newlife_game.py` | NewLife folder, tables | *Bring the game's leagues to this season*: clubs that went up/down swap, a club that left the game's world hands its place to the release's, squads come from the release, hand edits stay, undo takes back exactly what it did |
| `test_newlife_pins.py` | folder with a `Team.bin` | a NewLife club keeps its world id when a league before it changes or goes (`newlife_ids`) |
| `test_newlife_put.py` | NewLife folder, folder with a `Team.bin` | NewLife clubs put into a hand-made league (#83): name, kits, id and squad at that place |
| `test_newlife_twins.py` | tables | a NewLife club whose `clubs.csv` `game_id` names a club of the game (B56) is that club: *Bring the game's leagues* keeps it in its place, gives it its squad and gives no place away; a release without the column reads as before; a world that has the club as a new club keeps it, in Bring and in *Update my leagues*; tables without the club, and New clubs, take it for a new club |
| `test_newlife_update.py` | two NewLife folders (older, newer) | *Update my leagues to this version* takes the newer clubs and squads and keeps the league's own settings (and a package's kit folders with their clubs) |
| `test_own_kit_line.py` | | a kit line of your own in Kit Server's `map.txt` wins over a league package's kit and a made one (no line or folder of ours, a line an older Build switched off comes back on); package kit folders move with their club on Remove / Insert / Move club |
| `test_pack_guard.py` | | the release guard (`mszip.check_pack`): a known crash site, a `fl26caps.lua` that is not the generated set or not the game's stops the zip; other modules that differ from the game's are listed |
| `test_pool_nibble_edits.py` | | B65: a club renamed (`edits.clubs`) or swapped (`edits.swaps`) into a league leaves the "Other ..." group (`clear_league_pools`), a club in a pre-season tournament only or in no competition stays; `buildcheck.py` check 4 fails on such a club and not on what the base ships (synthetic tables) |
| `test_retired_modules.py` | | `ensure_modules` switches a bundled module off only when its bundle is loaded too |
| `test_shift_newlife.py` | | Remove club / Insert club move the league's NewLife ids with the places |
| `test_squadimport.py` | | the table import reads the game's player id and the fields |
| `test_ui_language.py` | `es`, `fr`, `pt` or `hr` (none: all four) | the whole window in that language (offscreen, a fake game): every page and tab, the menus and the state boxes show no text that is an English text of the translation catalogue left untranslated (as it is, or filled in with a name or number), and no English sentence missing from the catalogue; the builder's South American places and UEFA ranking lines come out translated by the `log` rules (and stay English on the command line); the world-name, move-club and world-in-the-way messages are translated |
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
tab's *Build and install* offscreen with:

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
4. A club whose league changed has its "Other ..." group bits cleared (`Team.bin` +0x4f), and
   so has every club with a place in a league (pre-season tournaments aside): a club renamed or
   swapped into one (B65). The base's own club there, as the base ships it, is INFO.
5. Record counts compared with the base (information only).

Checks 1, 3 and 4 count only what the world introduces, so a normal world passes.

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
