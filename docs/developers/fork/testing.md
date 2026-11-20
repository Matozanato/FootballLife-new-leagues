# Testing

There are four layers. Small Python tests check one rule each. `regress018.py` builds a set of
test recipes and checks the worlds without the game. `test_modstudio_build.py` runs Build and
install through Mod Studio itself, on a PC set up like a player's. Only the game itself proves
that a world plays. Run all four before a release.

The tests need no framework. Each is a script with plain `assert`s. It stops at the first
failure, and most print an `ok` line per check. Run them from the repository root.

## CUPS branch: final pre-PR validation

The final blocker-fix pass restored `sider/experimental/fl26swiss.dll` by copying
the verified `tools/native/fl26swiss.dll`, without rebuilding it. Both copies are
295,424 bytes, contain `standings zones v2`, preserve the base's 34 exports, and
have SHA-256 `37ddc522a0933896ae7e5ea02ad2ba1dc7f87717e0e8578ee411669b8deb8b1a`.

Fresh checks passed: native CONMEBOL zones; CUPS page/layout/performance/refinements
and hover scrolling; Continental Competitions; Qualification (130 checks with real
tables) and its UX; UEFA Ranking (27); CONMEBOL automatic qualification allocation (80 with real tables);
continental emblems (7); Trophies page (46); My World navigation (74); BUILD layout
and plan problems; helper emblems; DLL installation checks; and module-pack tests.
Recipe/plan round-trips and country IDs passed 46 checks, plus a separate optional
`continental_emblems` round-trip. Seven trophy backend checks and five legacy UI
checks passed. The actual module installer also copied the verified DLL correctly
from a minimal pack into a temporary fake game; no active world or FL27 install
was modified, and no full game Build or full release package was produced.

Explicit skips: `test_mkmpcol.py` found no `rankingTeam.bin` fixture; the remaining
offline trophy Lua checks need optional `lupa`, unavailable locally. Earlier
development counts in the feature notes describe their corresponding test runs.

The maintainer has visually verified modern CONMEBOL strips in FL27 using Bolivia
(three blue, four orange). FL26 in-game behavior has not been independently checked.
Dark/Light emblems passed automated tests; their in-game rendering is not fully
verified. With modern mode off, the world builds with original Libertadores.
Legacy Sudamericana places are preserved and reported as a Build error.

## The game's tables

Several tests and both build checks need the game's own unpacked tables (the `pesdb` folder).
Mod Studio unpacks them to `%APPDATA%\FL26ModStudio\tables` (FL27's: `tables27`) (Settings > *Unpack the game's
tables*). Pass that folder with `--base`, or set `FL26_PESDB` (several folders separated by `;`,
newest first). `FL26_DIR` is the game folder (or `FL26_EXE` the exe) for the tools that read the
exe. See `tools/flpaths.py`.

## The Python tests

| test | arguments | what it proves |
|---|---|---|
| `test_world_game.py` | tables (for the Build half) | a world says its game (`game fl26|fl27 teams= players=` in `fl26world.txt`, written at Build and at Export): Install, Switch on (My world, Content folders) and Build refuse a world or recipe of the other game, an old unstamped world only when it is over FL26's 2400 clubs / 61905 players; a world at exactly FL26's caps still goes in; the refusals are translated; Export stamps the zip's world file, json and README; `fl26gameguard.lua` (in lupa, a fake ffi) passes FL26 and unstamped worlds and stops the game on a world of the other game |
| `test_auto_formation.py` | tables | a new club with no formation in the recipe gets the one its squad fits (`lbplayers.pick_formation`): two strikers play two up front, wingers three forwards, three centre backs three or five at the back; in a built world the clubs of one league play different formations with their best eleven in them, and a club's or league's formation from the recipe stands |
| `test_players_changed.py` | | B322: the *Players changed* column counts for a NewLife club only what was changed by hand, not the squad the release set |
| `test_unknown_formation.py` | tables | B105: a formation the tables do not have (a league's, a club's) goes from the plan with a note naming the league, and Build does not stop; a formation the tables have stays |
| `test_install_space.py` | none | B41: a zip unpacks in %TEMP% while its disk has room, else in a folder beside the game, else a message naming the sizes before anything is unpacked |
| `test_install_long_paths.py` | none | B400: under an audit hook that plays Windows without long paths (open / mkdir / listdir / scandir / remove / copy past 259 characters refused unless `\\?\`), a zip member of 217 characters unpacks into a deep %TEMP%, Install copies a file past MAX_PATH into the game and Remove the mod deletes it, export_world zips it; `too_long` names the files the game could not open from a long game folder and the message gives the longest folder path that fits; the trophies' GzsTool copies (`#Win\x_fpk` beside `#Win\x.fpk`) stay out of Install, Export and Build (`lbtrophies.copy_ignore`), a `_fpk` folder with no `.fpk` beside it stays |
| `test_face_pool.py` | none (zig for the DLL half) | the face pool (`facepool.py`): 32,760 faces in the groups' shares; every group but sas and sea (made again 17.11.) the 06.11. and 07.11. pools byte for byte (per-group md5) but the 2 REPLACE faces (block 2 only in the grown groups, the SKIP draws left out), each face's block in the pack; South Asia brown, South-East Asia skin 2-4; with the 32,000 pack each group's share n0/n of players keeps his face of the 20,000 pack, and a pack all in block 0 picks as the DLL before the blocks (11b138c, built from git); the same for the same seed, no two alike, every field inside the game's own values (a hair style the game's players wear, no glasses), skin fitting the region (Nordic/Eastern Europe light, Africa dark, Latin America mixed); the version 2 pack reads back; fl26regen.dll loads it and picks for each player what `facepool.face_of` picks, a version 1 pack the same face as before, and refuses a pack too big or cut short |
| `test_facemini.py` | none (zig for the DLL half) | the face pool's portraits (`facemini.py`): on a screenshot of the red menu made in the test, the picture is 128 x 128 with the game's own portrait header (DXT5, 16,512 bytes), transparent around the player and over the grid, the face and black hair opaque, no red edge, the shirt grey (green with `--shirt keep`); a shot without a player and the same picture twice are told; `pack` gives the faces with a picture their portrait number and changes nothing else; `share` (18.11.) gives every face of a group with a picture the nearest captured one, a captured face its own, another group's only when it looks close, and on the real pool covers all 32,760 faces with numbers that all have their `.dds`; `rank` starts with one face of every group; fl26regen's capture file: every line form, what is refused, the last line wins, the lookups answer with face k for that player only and are counted, `off` or no file stops it, the thread answers within a second |
| `test_face_groups.py` | none | B183: `facegroups.nordic` puts the Nordic nations on a face group of the pack's own light faces (skin 1-2 of nweu and eeu, the same portraits); every other nation and face stays, and done twice it is the same. 17.11.: `facegroups.regroup` puts South-East Asia and Polynesia on sea (group 10), Pakistan on sas, Melanesia on afr, Kazakhstan/Kyrgyzstan on eas, Uzbekistan/Tajikistan/Turkmenistan on mena, Belize on lat; sas is South Asia only, every other nation stays |
| `test_face_regions.py` | none (zig for the DLL half; the 07.11. pack in `../faces30k/out/facepool` for the per-player half) | the face pool reaches the package (17.11.: the candidates had shipped the 30.09. pack of 103 game faces): `lbpack.face_pack` writes `FL26RF02` with 32,760 faces, md5 `POOL_MD5`; `FL26_REGEN_FACES` with the old pack, a pool under 20,000 faces, the old map or other faces stops it, the pool with portrait numbers goes, the pool with shared portrait numbers (`facemini.py share`) goes with their `.dds` and stops when one is missing or not 128 x 128 DXT5, in lbpack and in `mszip.check_pack`; `mszip.check_pack` stops the old pack and a small pool; the 17.11. map; the kept groups' faces byte for byte (and each English, Brazilian, Nigerian ... player's face the same as with the 07.11. pack); Pakistani and Indian players get sas faces, Indonesian, Thai and Samoan sea, Kazakh eas, Fijian afr, in `face_of` and in fl26regen.dll |
| `test_country_order.py` | | League order (0.2.0) follows the recipe's `country_order` and never `league_order` (the Leagues page's drag order) |
| `test_crestmatch.py` | | the crest file name matcher |
| `test_cup_draw.py` | | `cup_draw` becomes the `cupdraw` line; `seeded` unless the recipe says otherwise; any other value is refused |
| `test_dll_check.py` | | Install the modules stops, naming the file, when an antivirus takes or empties a DLL right after the copy; Home / Diagnostics (`checks.dll_problems`) and *4. Check* say the same while a switched-on module's DLL is missing |
| `test_game_text.py` | (font files: `pes_fnt.bin` ... of `dt11_x64.cpk`, optional) | names go into the game's tables in letters its fonts have (`pesdb.game_text`, B173): Azerbaijani ə as a, Romanian ș ț as ş ţ, Vietnamese letters with the accents the fonts have; what they have (Ə, Turkish, Greek, Cyrillic, Chinese ...) stays; a player's name slots and shirt, a club's and a league's name; with font files, the ranges are checked against them |
| `test_conmebol_modern.py` | tables | the modern CONMEBOL competitions (#146) only when picked: a recipe with legacy Sudamericana places is refused with a repair message and kept intact; after explicit removal it builds with original Libertadores; `"conmebol": "modern"` or a phase / first-stage / country place enables modern mode, switching off removes Sudamericana, modern phase and association places, `recipe_from_plan` keeps the switch; the League dialog's list keeps a place it does not offer (offscreen Qt); a modern world built, then with a league and its cups added in front, then without it, keeps every CONMEBOL competition and regulation id (builds in a temporary game folder) |
| `test_game_supercups.py` | tables | a super cup added to a game league (`game_cups`) is a two-club cup in the league's region, dated at the end of January in a February-December country, and its `gsuper` line names the league and the cup that fill it; fl26joindll and fl26swiss read that line; a division's line (a new J2 under the J.League, `scup=97`) never gives fl26swiss a calendar super cup's league (runs the Lua block when `lupa` is installed) |
| `test_febdec_cups.py` | tables | a February-December new league's national cup and super cup are accepted, a league cup refused, their `dates` lines take the calendar prototypes, and Build's summary puts the super cup at the end of January |
| `test_febdec_division.py` | tables | a division under a game league that plays February-December (Colombia) plays that season, so Build refuses a split or Apertura/Clausura on it |
| `test_b335_argentina_calendar.py` | tables, FL_2026.exe / FL_2027.exe (read only, optional) | the February-December regions come from the game's exe (its region table, which agrees with the exe's own league dates): FL26's set as in 0.3.0, FL27's with Argentina (B335); a division under the Liga Profesional plays August-May on FL26 and February-December on FL27, with a `season 17 1` line and a real calendar from after the day-41 join to before New Year |
| `test_finished_cap.py` | tables | the player cap is for the finished world: a world over it only halfway through Build (placeholders a club's own squad replaces go at the end) is built with squads of 30; one over it when done is built again with smaller squads; one too big even at 22 a club is refused |
| `test_build_apart.py` | tables | Build runs in a process of its own: the same tables as built in the window's process, the log lines and a BuildError come back, and the window's thread is not held up while it builds |
| `test_b480_big_world.py` | `--big` or `B480_BIG=1` (opt-in, ~10 min, ~8 GB free memory); `B480_WORLD`, `B480_TABLES` (default: the built GigaPack on `E:\FL\FL27`, FL27's tables27), `B480_KEEP=<dir>` (the recorder's lines), `B480_TRIM=0` (no emptied working set before each step), `B480_SETTLE=<s>` (seconds from that to the click, default 3; 0 = at once), `B480_STEP_S=<s>` (how long a step may take, default 900) | B480 round 3: the window with the real GigaPack (317 leagues, 4,500 new clubs, 109k players; its plan copied, the recipe read back from it as Make it editable does) in a fake game, read only: the end of the world's install, Make it editable, the end of Build (the build itself stubbed, its plan copied in), Leagues opened first and Edit league > OK. Each step's longest stop of the window (`FL26_STALLS` recorder) and longest wait of a thread for Python's lock must stay under 0.5 s; before each step the process's memory is put out of RAM (`EmptyWorkingSet`, `B480_TRIM=0` to skip) as Windows did in the exe test. Prints a table per step; without the switch it says why it is skipped and passes |
| `test_b480_edit_noop.py` | tables (default: tables27, else tables) | B480 round 3: New leagues > Edit league... > OK with nothing changed leaves the recipe byte for byte (the dialog sorted `europe`, `[[1,10],[0,12],[2,12]]` to `[[0,12],[1,10],[2,12]]`), calls no `touch()`, keeps no Undo step and has nothing to save; a league without places the same; one place more is kept, sorted and remembered |
| `test_filecache.py` | | a file read on every page visit (the built world's plan) is read again only when it changes; a changed or removed file is never served from before |
| `test_header_pack.py` | | the header's PACK box names the pack of the world in the game, not the last zip installed (B168): after Activate of another installed world, its own pack; a world built on this PC, the newest pack that brought no world, or none |
| `test_league_groups.py` | tables (optional) | groups of one division and promotion play-offs (GitHub #98): `fl26world.group_lines` / `read_groups` and fl26chain.lua's `group_line` read the same `gset`/`ghome`/`poff` lines, fl26chain.lua makes no pair of a group, fl26comptab gives a game league above groups the sum of their promotes; with the tables: three groups under Serie B make one set with one link, nine under three make two sets, `relegate` shares out, uneven counts, Apertura/Clausura and a group of all its clubs are refused; group winners', EFL-style and tie play-offs, their errors, the recipe given back, Check the plan's line of the set (how many down, how many up); a world built with three groups and a play-off: league lines, `gset`, `ghome`, `poff` with the knockout's id, only the lowest group linked in the tables; `zone_border` (16.11.2026): `gborder` lines written and read back by fl26world and fl26chain.lua, the plan's problems (a club not of the group, a group not of its division, not a group), the summary line and the recipe given back |
| `test_chain_groups.py` | zig | compiles and runs `tools/native/test_chain_groups.c`: fl26chain.dll's group sets on a fake game image -- three groups under Serie B with the game's own half move, idempotent; counts that do not add up and a club in no list refused; two sets (Serie B / three C / nine D) with home groups; group winners', EFL place (two legs, penalties) and tie play-offs, a level tie leaves the counts; 16.11.2026: a group under one set and over another (TFF 2. Lig) with a guest going home and a relegated club of its region not moved, both orders of the `gset` lines, a second pass writing nothing; a guest after a save and a load going home from the standings and `ghome` alone |
| `test_group_assign.py` | zig | compiles and runs `tools/native/test_group_assign.c` (16.11.2026): fl26chain's `group_assign` -- as many relegated clubs at home as there are places (where taking them in turn sent two of Girone A to B), Serbia's and Hungary's counts, no home, guests home, swaps and rings, border clubs, 3000 random cases against a brute force; `group_plan` with guests, `gborder` and without it, every league its size, no club twice, as many down as up |
| `test_league_band.py` | tables | the league band 320..499 (past the 97 leagues): a caps set whose date keys stay below 256 gets the date stub byte for byte as before, one with the band a 1024-byte table and only `cmp eax, 1024` changed; `DATE_SHIFT` agrees with both tracked caps sets; fl26comptab / fl26join / fl26chain / fl26swiss limits; every recipe of testdata and a 97-league world get the same ids, slots and cids with the band and without; 250 leagues use 320.. on slots 182.. for the top leagues and the shared ids for their divisions; cups never get a band id |
| `test_plan_problems.py` | tables | `plan()` raises every problem at once (`PlanProblems`), each with where it is (league and place, league, club of the game, a club's players); a league under one with a problem is not listed again; a swap of two clubs the tables have in one league now is left out with a note; a club of the game is named with its team id |
| `test_build_problems.py` | tables | the Build page lists the plan's problems above the log with where they are, and Go there opens Clubs at the league and place, Leagues at the league or at the game's league of a club; a plan with no problem hides the list |
| `test_trophies.py` | tables | Game content > Trophies backend and legacy dialog wrapper: phase folders, missing/empty folders, Entrance.lua integration (Lua checks require lupa), and copying folders with every regulation id; its optional full Build is separate from the UI migration checks |
| `test_trophies_page.py` | | Embedded Game content > Trophies, per-world temporary edits, Apply/Discard, Undo/Redo/autosave, existing recipe compatibility, metadata workers, obsolete LEAGUES menu removals including South American places, retained callbacks, responsive layout and unchanged copy/index output without a full world Build |
| `test_move_game_club.py` | tables | B95: Club of the game moves a club of the game from another place of the world (its old place a new club, its swap along), a club that only takes another's place stays greyed; NewLife club... lists the release's clubs the game has, greyed, and leaves out those a league has already |
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
| `test_newlife_game_only.py` | NewLife folder, tables | *Bring the game's leagues* with *Only the game's own players*: a club that keeps its place gets no new player and lets nobody go (unless past 40), its transfers are the same as the full Bring, a club that came up still gets its squad, undo takes it all back |
| `test_newlife_hand_crest.py` | NewLife folder, tables | B196: a crest or other change set on a place Bring gave another club stays with that club when the leagues are brought again; the place is not skipped as changed by hand; a change for a club that no longer comes in goes; undo leaves only the person's change |
| `test_first_afc.py` | | the first-season AFC Champions League list: recipe `europe_first` `afc` to the world file's `first 3`, 32 at most, a club in two lists refused; fl26swiss.lua and the DLL take competition 3 |
| `test_newlife_lost_clubs.py` | | B324: a NewLife league whose club of the game the tables in use have not got (FL27 dropped 60 clubs of FL26, Wisla Krakow 1695 among them) is offered for *Update my leagues*, which makes the club a new club of the release; a league of your own and FL26's tables are left alone |
| `test_newlife_pins.py` | folder with a `Team.bin` | a NewLife club keeps its world id when a league before it changes or goes (`newlife_ids`) |
| `test_newlife_put.py` | NewLife folder, folder with a `Team.bin` | NewLife clubs put into a hand-made league (#83): name, kits, id and squad at that place |
| `test_newlife_twins.py` | tables | a NewLife club whose `clubs.csv` `game_id` names a club of the game (B56) is that club: *Bring the game's leagues* keeps it in its place, gives it its squad and gives no place away; a release without the column reads as before; a world that has the club as a new club keeps it, in Bring and in *Update my leagues*; tables without the club, and New clubs, take it for a new club; a club of the game with `game_id` (FL27 numbers it differently) goes by the id the tables have; with `game_names`, an id the tables give another club of the country is a new club, and a new club of the release with that id as `game_id` is the game's club there (the release's own club of that id a new one under `900000` + id). FL26's tables: the fixture is FL26's Série A and B |
| `test_newlife_update.py` | two NewLife folders (older, newer) | *Update my leagues to this version* takes the newer clubs and squads and keeps the league's own settings (and a package's kit folders with their clubs) |
| `test_own_kit_line.py` | | a kit line of your own in Kit Server's `map.txt` wins over a league package's kit and a made one (no line or folder of ours, a line an older Build switched off comes back on); package kit folders move with their club on Remove / Insert / Move club |
| `test_pack_guard.py` | | the release guard (`mszip.check_pack`): a known crash site, a `fl26caps.lua` that is not the generated set or not the game's, no face pack or one that is not the face pool stops the zip; other modules that differ from the game's are listed |
| `test_pool_nibble_edits.py` | | B65: a club renamed (`edits.clubs`) or swapped (`edits.swaps`) into a league leaves the "Other ..." group (`clear_league_pools`), a club in a pre-season tournament only or in no competition stays; `buildcheck.py` check 4 fails on such a club and not on what the base ships (synthetic tables) |
| `test_retired_modules.py` | | `ensure_modules` switches a bundled module off only when its bundle is loaded too |
| `test_shift_newlife.py` | | Remove club / Insert club move the league's NewLife ids with the places |
| `test_shirt_numbers.py` | | a player Build adds to a squad takes a free number for his position (a keeper 1, 12 ...); B157: the 1 of a new club goes to its first keeper |
| `test_shirt_positions.py` | | a new club's squad is numbered by position (`lbplayers.position_shirts`): the first eleven by their places, the rest by their line, keepers always a keeper's number, no number twice; a recipe's own numbers stay |
| `test_recipe_shirts.py` | tables (optional) | a number the recipe or a NewLife-format release's `shirt` column gives stays with its player and is his alone in the squad (`lbplayers.unique_shirts`): a stand-in or a game player who wore it takes a free one of his line's; a club with no number is numbered as before; a national team keeps its own numbers; contract and loan columns are not read; one Build in a temporary game folder |
| `test_squadimport.py` | | the table import reads the game's player id and the fields |
| `test_ui_language.py` | `es`, `fr`, `pt` or `hr` (none: all four) | the whole window in that language (offscreen, a fake game): every page and tab, the menus and the state boxes show no text that is an English text of the translation catalogue left untranslated (as it is, or filled in with a name or number), and no English sentence missing from the catalogue; the builder's South American places and UEFA ranking lines come out translated by the `log` rules (and stay English on the command line); the world-name, move-club and world-in-the-way messages are translated |
| `test_write_access.py` | | a game folder Windows does not let Mod Studio write in (a deny-write entry made with `icacls`, as under Program Files) is found before a write, a refused write is told from other errors, and the message says what to do (run as administrator, or move the game) |

```
python tools/test_cup_draw.py
python tools/test_newlife_update.py <NewLife folder A> <NewLife folder B>
```

A NewLife folder is an unpacked release (see [newlife-format.md](newlife-format.md)).

Stops of the window in the exe: `FL26_STALLS=<file>` makes Mod Studio write each stop of 0.3 s and
more with the lines its threads were at (B480 round 3: also the threads in faulthandler's C dumps,
which see the holder of Python's lock while it holds it, and from Windows each thread's processor
time and the process's page faults in the stop). `python tools/hangstacks.py FL26ModStudio.exe
<out.txt> --after 1.0` writes the native stacks of every thread when the window or, with
`FL26_STALLS` on, its heartbeat stands still, with each thread's processor time since the dump
before and whether it waits in a system call or runs with Python under it.

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
| `regress018/groups_playoffs` | three Serie C groups under Serie B, one with a place play-off (2nd to 5th), and a National under Ligue 2 with a tie play-off (GitHub #98) |
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

0. **The game runs the pack and nothing else of ours.** `python tools/rigcheck.py <game
   folder> <pack folder> --log` (the pack is `pack` next to the Mod Studio exe you test). It
   fails on a `fl26*.lua` line the pack does not have, a module of the pack without its line, a
   module or DLL whose bytes are not the pack's, or a `sider.log` that loaded something else.
   A test game that ran a module by hand proves nothing about the pack (B408: the GigaPack's
   tests passed with `fl26match` put in by hand; Mod Studio did not install it and a player's
   new career died). Modules of others (kits, ML Fast Forward) are listed, not judged.
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
