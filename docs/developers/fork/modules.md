# Sider modules and DLLs

Everything Mod Studio does inside the running game, it does through Sider Lua modules. Six of
them load a DLL of their own. This page lists them all: what each one is for, how it gets
installed, what its DLL exports and hooks, and what the numbers in `sider.log` mean. The
last two sections cover the 0.2.0 `-calendar` patch set and what to do when the game exe
changes.

All addresses are for `FL_2026.exe`, 458,910,720 bytes. Football Life 2026 v2.0 (file
version 26.0.0.0) and v2.2 (26.2.0.3) both have an exe of that size, and both are known to
work. It has no ASLR
(DllCharacteristics 0x8120), so the addresses are absolute.

## Install and load order

`tools/lbpack.py` makes the module pack. `leaguebuilder.install_modules` copies it into
`SiderAddons\modules` and writes the `lua.module` lines of `sider.ini` in this order (`ORDER`):

```
fl26gameguard, fl26caps, fl26match, fl26appcap, fl26regs600, fl26slots250, fl26slot7, fl26guards, fl26regfast, fl26walk,
fl26compcache, fl26joindll, fl26hdr255, fl26chain, fl26comptab, fl26slotnames, fl26clubs, fl26regen,
fl26editlist, fl26edit, fl26rank, fl26deeprank, fl26regions, fl26reg128, fl26regnames,
fl26catlist, fl26swiss, fl26augseason, fl26lateguards, fl26seasonend
```

- **Bundles.** `fl26guards` is `fl26nullguard`, `2`, `4`, `5`, `7`, `8`, `9` and `10`.
  `fl26lateguards` is `fl26superguard`, `fl26resultsguard`, `fl26ctlguard` and
  `fl26kitguard`. Each part stays its own file in `sider/`, so read and change those files,
  not the bundle. `lbpack.bundle()` runs each part's chunk in a function of its own, and the
  bundle's `init` calls the parts' `init` in order. Sider's Lua has **no `pcall`**: a part
  whose `init` raises an error stops the parts after it. That is why the oldest, most tried
  guards go first. The pack's `retired.txt` lists the single modules a bundle replaced.
  Build switches their old `lua.module` lines off and keeps the files as restore points in
  `SiderAddons\ModStudio\backups` (until 0.2.4 in `modules\before-builder-<n>\`).
- **Per world.** `fl26regions` and `fl26regnames` are not in the pack. They name the regions
  and competitions of one world, so Build writes them into the world folder
  (`region_modules`: `mkregioncats.py`, `mkregnames.py`, `mkcatflags.py`), and *Switch it on*
  copies them to `modules\`.
- **DLLs.** These are compiled when the pack is made (`DLLS` in `lbpack.py`, see
  [building.md](building.md)). Each DLL sits next to its loader in `modules\`.
- **Where the sources come from.** `lbpack.source()` takes `sider/<name>.lua`, else
  `sider/experimental/<name>.lua`.
- **Private-path check.** Before the pack is written, its Lua files are checked for drive
  paths and user folders (`PRIVATE`). Any match stops the pack.

Sider's Lua also has no `debug` or `rawget`. Check every value before you index it.

## The modules

| module | in the pack as | what it does |
|---|---|---|
| `fl26caps` | itself | applies the patch set: bigger tables (teams 750 -> 2400, coaches 1300 -> 3400, regulations 300 -> 600, the player cap 61905, match records; 0.2.1: 1600 teams, 2600 coaches, 51729 players), the date-spread stub, the save/load copy, and in 0.2.0 the 792-match calendar day. Generated, never edited by hand (below) |
| `fl26gameguard` | itself | first of all: reads the `game` line of `modules\fl26world.txt` and of every switched-on `cpk.root` world. A world stamped for the other game (an FL 2027 world in FL26, or the reverse) logs `fl26gameguard: REFUSED ...`, shows a message box and ends the game before its tables load, so nothing is written. A world without the line passes |
| `fl26match` | itself, and `fl26match.fl27.lua` for FL 2027 (with the committed `fl26match.dll`) | FL 2027 only, right after `fl26caps`: the match table's allocator and lookup with ids past 65535, and players past 65535 found by their id (lift16f port). A world past 65535 matches a season or 65535 players (the GigaPack) needs it; in FL26 it logs that it stands down (B408: GigaPack beta 1's Mod Studio did not install it and a new career died while it was made) |
| `fl26appcap` | itself | the PlayerAppearance table from 30,024 to 65,000 records (0.2.2) |
| `fl26regs600` | itself | the game's recount of regulation records covers all 600, not 300 (0.2.2) |
| `fl26slots250` | itself | Select Team / competition slots 123 -> 250, each with a club-list capacity of its own (0.2.2) |
| `fl26slot7` | itself | a club's league slot is 9 bits (0..511: +0x41c low byte, +0x41b high byte), not 7 (0.2.2 a whole byte, 9 bits since B391; needs `fl26slots250`) |
| `fl26regfast` | itself | speed fix: drops two redundant regulation searches from "which league is team X in" |
| `fl26walk` | itself + `fl26walk.dll` | speed fix: keeps the user's club and league for one calendar walk (Master League creation, day advance) |
| `fl26compcache` | itself + `fl26compcache.dll` | speed fix: the game's per-player competition scan (end of January, transfer deadline) asks each competition's lookup once per scan instead of once per player |
| `fl26nullguard`, `2`, `4`, `5`, `7`, `8`, `9`, `10` | `fl26guards` | code-cave guards at crash sites in the shipped code: a null or out-of-range value takes the safe path instead of crashing. Each header shows the disassembly of its site |
| `fl26joindll` | itself + `fl26join.dll` | gets our leagues into a Master League season and closes them at season end, the way shipped leagues are handled |
| `fl26hdr255` | itself | season competition header from 100 to 255 entries, 595 per-phase tables left (a patch set of the same kind as fl26caps; it replaced `fl26hdr192` and `sider/fl26hdr127.lua` in 0.2.2) |
| `fl26chain` | itself + `fl26chain.dll` | completes promotion/relegation chains deeper than two tiers; which clubs a country cup and super cup take (`cup*=`, `scup=`); Apertura/Clausura promotion |
| `fl26comptab` | itself | makes our leagues selectable in Select Team (Master League / Kick Off), their flags, and the `kickorder` |
| `fl26slotnames` | itself | stops seven of our leagues from borrowing a shipped section name; in FL 2027 also gives SmokePatch's `CommonLib` the leagues past competition id 255 under their own id (B427, below) |
| `fl26clubs` | itself + `fl26clubs.dll` | Select Team shows our clubs in the slots where the game would put someone else's; keeps clubs out of the "other clubs" pools (`nopool`) |
| `fl26regen` | itself + `fl26regen.dll` | regens are new players with faces from the regen face pack; the world's own players get faces (`newfaces`, `faceapp`) |
| `fl26editlist` | itself | all our leagues in Edit mode's team lists |
| `fl26edit` | itself + `fl26edit.dll` | Edit mode keeps the changes made to our clubs (#55) |
| `fl26rank` | itself | gives the league rank one more bit, so a pyramid can be more than three deep (generated by `tools/mkrankpatch.py`) |
| `fl26deeprank` | itself | the relegation gate for a pyramid of any depth (it replaced `fl26deep4`, which is still in `sider/experimental/` for reference) |
| `fl26regions`, `fl26regnames` | per world | region (country) names and category flags of the world |
| `fl26reg128` | itself | raises the number of regions (countries) from 29 to 128 (replaced `fl26reg64`, 64, in 0.2.2); an FL 2027 caps set with the `regions` step (tools/regions.py) writes its 44 sites itself with a parser for 0..255, and the module then writes nothing |
| `fl26catlist` | itself | our countries in ML > Database > Competition Info, in the world's `order`; League Info's promotion line for every group of a `gset` |
| `fl26squadlist` | itself + `fl26squadlist.dll` | Select Team (Team Info, League mode...): on a league row the right panel lists the league's clubs with their crests under "Team List" instead of staying empty (the crest cell is in the world's teamSelectSingle.bin, tools/mkteamcrest.py); inside the league it shows the club's players under "Squad List", as before |
| `fl26confgroups` | itself + `fl26confgroups.dll` | FL 2027 only: Select Team (Master League New, Kick Off, Edit) and Competition Info start with one row per confederation (UEFA, CONMEBOL, CONCACAF, AFC, CAF, OFC); Confirm opens one (its leagues or countries under it, the cursor on the first), Confirm again or Back closes it. League Info (a new Master League) on a confederation's row shows its continental cups (the line's `cups` without the Club World Cup). The groups come from the world's `confgroups` line (leaguebuilder.confgroups_lines: each slot and region by its country's confederation). Without the line, or in FL26, the lists stay the game's. On its own, in FL_2027.exe with any world (asked before the line is read): `fl26_confgroups_numbers(base)` lets Select Team's attack / midfield / defence numbers go below 39 -- one byte, 0x29 -> 0x21 at 0x141508b07, so the floor in 0x1415089e0 is the 40.0 next to the 50.0 (lowest number 26; a number of 40 or more unchanged), after its 25 bytes at 0x141508af6 are checked. Returns 0 written, 1 not FL 2027, 2 other bytes (nothing written), 4 VirtualProtect; sider.log `confgroups: team numbers: ok` / `off <why>`. In FL_2026.exe the loader does not ask for it and the export refuses |
| `fl26swiss` | itself + `fl26swiss.dll` | the 36-club league phase draw, play-offs, qualifying rounds, the UEFA access list, our continental/league/pre-season cups, cup draws and dates, the calendar of leagues that are not 20 clubs playing twice, seasons by region; in the standings the MP column and the coloured zone strip (every continental place -- UEFA, CONMEBOL, AFC, CAF, CONCACAF, OFC --, up, play-off, down; the cells are in the world's rankingTeam.bin, tools/mkmpcol.py) |
| `fl26augseason` | itself | a career started in one of our leagues starts in August |
| `fl26superguard` | `fl26lateguards` | stops the UEFA Super Cup setup from reading entry -1 |
| `fl26resultsguard` | `fl26lateguards` | keeps an empty matchday results list from ending the game |
| `fl26ctlguard` | `fl26lateguards` | after a club change, gives the old club back to the computer |
| `fl26kitguard` | `fl26lateguards` | the Kit Server's goalkeeper pick on a club with no kit of the game |
| `fl26seasonend` | itself | lets the season-end step run for our leagues (and the French and Italian chains) |

Every module logs to `sider.log` with its name in brackets. `leaguebuilder.check()` and
Diagnostics read the `world file -- <n> leagues` lines to tell a person whether each world-file
reader took the world.

## The DLLs

The C sources are in `tools/native/`. A loader calls `ffi.load` on the DLL and passes the
exe base, a configuration from the world file, and (for some) a log path. The DLL then
checks the code it hooks: the first bytes of every function it hooks are compared with the
bytes this build expects. **On a mismatch it installs nothing** and returns a status, which
the loader prints in words. A hook allocates a trampoline in reach of the function
(`VirtualAlloc`) and redirects the entry (`VirtualProtect`). Where the game has a function
for something (closing a season, rebuilding a record), the hook calls it instead of
writing the tables itself. The loaders drain `<dll>_log` and `<dll>_stats` into `sider.log`.

### fl26join.dll (loader `sider/fl26joindll.lua`)

- **Exports:** `fl26_join_install`, `fl26_join_calendar`, `fl26_join_teardown_extra`,
  `fl26_join_season_types` (the `season` lines), `fl26_join_log`, `fl26_join_stats`.
- **Hooks (RVAs):**
  - `register_all` 0x1343bf0: appends our ids to the season list;
  - `enter_season` 0x158f420, the season builder 0x13156e0 and the door 0x13ac170: refuse
    the creation-time ask for our ids, reset a season that is already over and rebuild a
    stale record; at the door, for every league (ours or the game's), a league with no match
    left in the table has its rounds' 16 places set free first (round table read off
    0x141579e38/0x141579e2e, 0x208 a round), so a January-December league is not built into
    last season's places (B253);
  - `close_listed` 0x1363210: keeps our ids out of the New Year close;
  - the mover 0x1365110: sends a league without a final table down the no-movement path;
  - teardown 0x1314350: adds our ids to the July close list;
  - the region -> season-type table 0x1576140 (`season` lines).
- **Constants that depend on the patch set:** `REG_ARRAY_OFF` 0x1d4c330 and `TODAY_OFF`
  0x19115ec (see below). Its own log file is `SiderAddons\fl26join.log`.
- **Status:**
  - 2 = `register_all` code is not as expected, 3 = `VirtualAlloc` failed,
    4 = `VirtualProtect` failed;
  - 12/13/14 = the same three for `enter_season`, 22/23/24 for the builder, 32/33/34 for
    the door;
  - 9 = bad id list.

### fl26chain.dll (loader `fl26chain.lua`)

- **Exports:** `fl26_chain_install`, `fl26_chain_apclau`, `fl26_chain_protect`,
  `fl26_chain_cups`, `fl26_chain_cupsize`, `fl26_chain_supercups`, `fl26_chain_gsets`,
  `fl26_chain_ghomes`, `fl26_chain_playoffs`, `fl26_chain_splits`, `fl26_chain_split_groups`,
  `fl26_chain_log`, `fl26_chain_stats`.
- **Hooks:**
  - `set_regulation_teams` 0x1522b50;
  - the season-end `apply` 0x135bff0. It completes chains of three or more divisions (up
    to 8 chains), sets the clubs of a country's cup and super cup, and runs the
    Apertura/Clausura promotion (`apclau`);
  - groups of one division (GitHub #98, the world file's `gset`/`ghome` lines): the observe
    pass keeps every member league's standings and list, and after the chains `apply` writes
    the new lists of the whole set at once (relegated to their home group, promoted into their
    group's league above, every size kept); a set whose counts or lists do not add up moves
    nothing and says why in sider.log;
  - promotion play-offs (`poff` lines): the winner is read from the match table (aggregate,
    then penalties) and swapped with the club the counts put on the place; with no clear
    winner the counts stand. By the season end the new season's schedule has usually replaced
    the play-off's matches, so the winner fl26swiss kept when the last match was played
    (`fl26_swiss_kept_winner`) is taken then, if it is one of this season's entrants;
  - split totals (`split` lines, `fl26_chain_split_groups`): the game builds a split total's
    final table only for two groups of the same size that end on the same day. For any other
    split (6 + 8, three groups) the total has no table, and its standings are taken from its
    groups in order, group 1 first; a group without a table, or a club in two groups, gives
    nothing (sider.log: `split N: no table of its own`). A group's table is gone by the season
    end too: fl26swiss keeps it when the group's last round is played (`fl26_swiss_kept_table`,
    in fl26swiss-state.bin), and fl26chain takes that one. The game has no table for a split's
    group (and none for the regular phase), so fl26swiss counts it from the match table: the
    group's own matches plus the regular phase's (not for Apertura/Clausura), points, then goal
    difference, then goals scored. It does that before and after each game day from 1 March,
    because the group's matches are wiped a few days after its last round (sider.log:
    `group table from N match(es)`).
- **Constant:** `REG_ARRAY_OFF` 0x1d4c330.
- **Status:**
  - 2/3/4 = set-hook code not as expected / `VirtualAlloc` / `VirtualProtect`;
  - 12/13/14 = the same for the apply hook;
  - 9 = bad configuration.

### fl26clubs.dll (loader `fl26clubs.lua`)

- **Exports:** `fl26_clubs_install`, `fl26_clubs_keep_out` (the `nopool` line),
  `fl26_clubs_log`, `fl26_clubs_stats`, `fl26_clubs_pool_calls`, `fl26_clubs_fans` (the
  `fans` lines), `fl26_clubs_fan_stats`, `fl26_clubs_fan_stats2`, and the handlers `set_hook`, `count_hook`,
  `get_hook`, `rank_find_hook`, `rank_pos_hook`, `fans_post`, `fans_total_post`.
- **Hooks:**
  - it replaces the two Select Team readers, count 0x1414d62c0 and get 0x1414d6290, and
    answers from the league's own rulebook for the slots in its list. Any other slot
    falls through to the game's answer;
  - the list setter 0x1414d6330 is hooked so our clubs stay out of the Club World Cup
    "other clubs" pools;
  - with `fans` lines in the world, it replaces the club ranking lookup 0x140de2310 and wraps
    the followers base 0x14150e950. The ranking holds 750 clubs at most and the lookup
    answered a miss with the top club, so a new club past it got the top class and millions
    of followers. A listed club now gets an entry of its own, with the class from its line,
    and the followers base is cut to the line's percent;
  - with the same lines it replaces the rank lookup 0x140b8abd0 (-1 for a miss, which the
    broadcasting fee 0x141567ca0 paid as better than first place: EUR 250M a season) and
    wraps the followers total 0x141589e90, whose star-player part is cut to the line's
    percent for clubs below the top flight. Without `fans` lines nothing is hooked.
    Build writes a line for every new club and for every club of the game it puts into a
    league that the game gives no money and no followers (the "other clubs" of the pools).
- **Status:**
  - 2 = count reader code not as expected, 3 = get reader code not as expected;
  - 4 / 5 = `VirtualProtect` on the count / get reader;
  - 6 = list setter code not as expected, 7 = `VirtualProtect` on the list setter;
  - 9 = bad slot list.

### fl26edit.dll (loader `fl26edit.lua`)

- **Exports:** `fl26_edit_install`, `fl26_edit_log`, `fl26_edit_stats`.
- **What it does:** it patches the Edit data constructor (0x1eeace0), the save flow
  (0x1f080a7), the 750-team cap function (0x1ef21d0) and, since 0.2.2, the 1300-manager cap
  function (0x1eeddd0). The Edit data then has room for every club of a world and its
  manager: the old room in the save itself (749 clubs, 1299 managers), and the records past
  that in `EDIT00000000.fl26x` next to the save (the folder of `fl26savedir.h`, below;
  `FL26EDX2`: tag, four counts, then team data,
  squad, tactics and managers; a 0.2.1 file is `FL26EDX1` with the first three only). Without
  the managers part, "Create Edit Data" fails in a big world: the check before the save
  (0x141ee85f0) wants every club's manager in the Edit data.
- **Status:**
  - 2 = code not as expected;
  - 3 = the Edit data was made before the module loaded (load order);
  - 4 = out of memory;
  - 5 = a patch failed.

### The save folder (`tools/native/fl26savedir.h`, B296)

`fl26edit.dll` and `fl26swiss.dll` find the game's save folder with `fl26_save_dir`, and Mod Studio
with `game.save_root` -- the same rule, checked against each other by `tools/test_savedir.py`:

- Documents by `SHGetFolderPathW` (shell32 asked at run time: the DLLs import kernel32 only), so a
  folder named in any letters works; the path travels in UTF-8 and `fl26_u8open` / `fl26_u8move`
  turn it back into UTF-16 for the file calls.
- Then `KONAMI\eFootball PES 2021 SEASON UPDATE\<id>\save`: `<id>` is `SteamID` of `sys.ini` next to
  the exe (2026) when its `save` holds `SYSTEM00000000`; else the numbered folder whose
  `SYSTEM00000000` was written last (the game saves under `0` when the Steam stand-in does not
  read `sys.ini`); else sys.ini's.
- Asked again at every load and save, as the game's first save can make the folder.

### fl26regen.dll (loader `sider/fl26regen.lua`)

- **Exports:** `fl26_regen_install`, `fl26_regen_log`, `fl26_regen_is`,
  `fl26_regen_faces_load`, `fl26_regen_face`, `fl26_regen_face_pick` (for the tests), `fl26_regen_new`,
  `fl26_regen_copy` (`faceapp`), `fl26_regen_faces`, `fl26_regen_stats`; capture mode:
  `fl26_regen_capture_watch`, `fl26_regen_capture_id`, `fl26_regen_capture_face`.
- **What it does:** it wraps the regen function 0x141534cc0 and the save unpacker
  0x1412e5eb0. A regen becomes a new player with a face from `fl26regen_faces.bin` (the face
  pack, see [building.md](building.md)): face `mix(id)` of the group of his nationality, so the
  same player always gets the same face. It reads version 1 (`FL26RF01`, up to 4,095 faces with
  portraits) and version 2 (`FL26RF02`, the face pool of `tools/facepool.py`, up to 32,767 faces
  without portraits: portrait number 0xffff, or k once `tools/facemini.py pack` gave face k
  its picture). The second byte of a version 2 face is its block: with faces in a later block a
  player takes the face of block 0 he had before for the share n0/n of his group, else one of the
  later faces, so a pool that grows keeps most of a career's faces; a pack all in block 0
  (version 1, the 20,000 pool) picks as before. Without the face pack it still makes new players,
  and they keep the generic face.
- **Capture mode** (for the face pool's portraits, never on in a game someone plays): only when
  `modules\fl26regen_capture.txt` is there when the game starts. A thread reads it every 100 ms:
  `player <id> face <k>` makes both appearance lookups answer for that player with pool face k
  (before the table and the new players' records), `faces <lo>-<hi>` lists those players' pool
  faces and names, `off` (or no file) stops it. The answer, `fl26regen_capture.ack`, counts the
  game's lookups of him since k was set. The loader hides his real face and sends his portrait to
  face k's.
- **Status:**
  - 2 = regen function code not as expected, 3 = save loader code not as expected;
  - 4 = an operand is not what this build expects;
  - 5 = out of memory;
  - 6 = could not wrap a function.

### fl26swiss.dll (loader `fl26swiss.lua`)

- **Exports:**
  - `fl26_swiss_install`;
  - configuration from the world file: `_nations`, `_confed`, `_ccup`, `_ccup_opts`,
    `_ccup_alt`, `_lpre`, `_cupdraw`, `_access`, `_qrounds`, `_first`, `_uecl`, `_leagues`,
    `_calendar_year`, `_european`, `_july`, `_splits`, `_nocarry`, `_datelike`;
  - `_ko_tick`, `_log`, `_stats`;
  - for fl26chain at the season end: `_kept_winner`, `_kept_table`.
- **Hooks:**
  - `build_generic_schedule` 0x1413f3e00: the league phase, our cups, league calendars;
  - `fixture_dates` 0x14157f810: dates;
  - `build_group_of_four` 0x1413f3c30;
  - plus calls into the game's draw, seeding, winner and tie-table functions.
- **The draw table** is `fl26swiss_table.h`. `tools/mkswiss.py` generates and checks it,
  and `build-swiss.sh` runs that first. `fl26swiss_draw.h` keeps associations apart, and
  `swissdraw_test.c` tests it offline.
- **Constant:** `TODAY_OFF` 0x19115e4.
- **League phase table of a past season** (`lp_table`, 0.2.2): the play-off and the round of 16
  read the league phase table through 0x14158b6f0, which takes the competition's newest season.
  The Europa League (competition 3, header 144) opens its next season around the play-off draw
  (seen on day 27 of season 2), and that table is empty. When it is, `season_table` walks the
  two season slots of every header (`[owner+0x78]`, stride 0xb4, slots at +4 / +0x5c, table
  indices at +8; the table array offset is read from the lea at 0x14158df91) and takes the
  fullest table of that regulation.
- **Kept tables on disk** (`state_store` / `state_sync`, 0.2.4, B49): the final tables and cup
  winners kept at a season's end (`g_final`, `g_cupwin`) are written to
  `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\fl26swiss-state.bin` (the save
  folder of `fl26savedir.h`, see fl26edit.dll), 176-byte
  records after an 8-byte magic `FL26SST1`: the user's club (0x1414bb650), the game's date
  (year * 365 + day: the day at `TODAY_OFF`, the year 8 bytes after it), the regulation, kind
  (0 table, 1 cup winner), the clubs and an FNV-1a check. When the game's date and `abs_day`
  stop moving together (a start, a load), memory is put on the new footing and the user's club's
  newest record of each regulation dated today or before is read back. No hook: written from
  `teardown_pre` and `apclau_keep`, read from `final_of`, `cupwin_of`, `any_final_kept`.
  `test_state_keep.c` (`tools/test_state_keep.py`) checks it offline.
- **A whole season of two tournaments** (`fl26_swiss_seasonsum`, `ssum_keep`): the world file's
  `seasonsum <total> parts=<half>,<half>` (Colombia 119 = 168 + 169, the MLS 51 = 166 + 167). On
  the day the last half has every match played (and before every teardown), the halves' tables
  (`TABLE_RVA`; a row: +0 club, +8 points, +9..+0x0e six-bit counts with goals for and against
  as 12 bits each, +0x0f matches played, as `tools/leaguetable.py` reads them) are added together
  -- points, goal difference, goals -- and kept as the total's final table; `keep_final` never
  keeps one for a total. With none kept yet, a place of the total reads its first half
  (`access_club_kept`, `cwc_club`). `test_season_sum.c` (`tools/test_season_sum.py`) checks it
  offline.
- **The classic Libertadores and the world's places of game leagues** (`lib_set_by_world`,
  `cont_swap`): without our pre-rounds (`modern_conmebol()` false) the game fills reg 9 and reg 8
  by the exe's rights (0x1434f1fa0). In the whole field (id < 1024) a club that is not a pool
  club, not a place of ours (`g_cont`) and not a title holder, of a league or cup the access list
  gives Libertadores places (`LIB`/`LIBQ`, whole seasons through their halves), goes first in the
  swap order: the next place of ours, else `conmebol_fallback`, kept in the season's map so the
  group lists follow it. Checked in the game: not yet.
- **Status:**
  - 2 / 12 / 22 = code not as expected at 0x1413f3e00 / 0x14157f810 / 0x1413f3c30;
  - 3 = `VirtualAlloc`, 4 = `VirtualProtect`;
  - 9 = bad configuration (REGS empty or more than 8).

## The 0.2.0 patch set: `-calendar`

0.2.2 ships (as 0.2.0 did, with the raised limits) `teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar`.
`sider/fl26caps.lua` is that set (the same file as
`sider/fl26caps.<set>.lua`), and its header says `block 0x1877068 -> 0x4a2b568, 3510 patches`.

- **What `-calendar` changes.** It widens every calendar day from 280 to 792 match ids. The
  day stride goes from 0x2c4 to 0x6c4 bytes (`tools/calwiden.py`, with the sites in
  `patches/calendar-sites.json` and `patches/calendar-tail-sites.json`). The calendar unit
  also moves to the top of the edit block. Everything stored after it moves by 0x2cebc8.
- **Saves.** A career saved with an older set does not load under this one. Worlds do not
  need a new Build.
- **Checking it.** `python tools/calaudit.py patches/<set>.json` re-checks every calendar
  reference of the exe against the set.

Module constants that changed with it:

| where | constant | -calendar (0.2.0) | older `-fixtures` set |
|---|---|---|---|
| `fl26join.c`, `fl26chain.c` | `REG_ARRAY_OFF` (regulation records in the edit block) | 0x1d4c330 | 0x1c84230 (`-DREG_ARRAY_OFF=0x1c84230`) |
| `fl26join.c` | `TODAY_OFF` (today's date) | 0x19115ec | `-DTODAY_OFF=...` |
| `fl26swiss.c` | `TODAY_OFF` | 0x19115e4 | `-DTODAY_OFF=...` |
| `fl26ctlguard.lua` | owner handle / controller table | block+0x19115f4 / block+0x19115f0 | 0x1642a2c / 0x1642a28 |

The C constants are `#ifndef` blocks, so a build for the older set only needs `-D...` on the
`zig cc` line. fl26caps itself rewrites the game's own references to the moved fields (for
example the 0x1642a1c -> 0x19115e4 date references). Modules that read those fields directly
have to be changed by hand, which is what the table lists. `OWNER_RVA` 0x3705e10 (fl26join,
fl26chain, fl26clubs, fl26regen) is a global of the exe and did not move.

The table is for the shipped 792 ids a day. A set made with `--calendar-ids N` (another day
size) moves all of these: `patchset.py` prints `REG_ARRAY_OFF` (the "regulations array moves
to" line) and the four calendar-tail values (`module constants for this layout: ...`). For
1304 ids (this set, `--player-cap 51729`) they are `REG_ARRAY_OFF` 0x1da7730, fl26swiss `TODAY_OFF` 0x196c9e4, fl26join
`TODAY_OFF` 0x196c9ec, fl26ctlguard block+0x196c9f0 / +0x196c9f4.

## fl26caps: how a patch set is made

Do not edit `fl26caps.lua` by hand. `tools/patchset.py <set> ...` disassembles the exe
(`capstone`), works out every instruction that touches a table it moves or grows, and writes
`patches/<set>.json` and `sider/fl26caps.lua` from `sider/fl26caps.template.lua`. It refuses to
emit a set while any reference is unattributed. The command for the shipped set and the
meaning of its flags are in [for-developers.md](../for-developers.md).

At game start fl26caps reads every target address and compares it with the bytes the
generator saw. Only if all of them match does it write anything. A single mismatch logs
`fl26caps: MISMATCH at 0x...` and `ABORTED`, and the game runs unmodified. A half-applied
layout would be worse than none.

## When the game exe updates

Nothing breaks silently. fl26caps, every guard and every DLL compare the original bytes
before they write, so on a different exe they install nothing and say so in `sider.log`.
The game then runs without them. That is safe, but the world's added leagues will not work.

To bring the project to a new exe:

1. **Check that it is a different exe.** Compare its size and SHA-256 with 458,910,720
   bytes. Some updates leave the exe alone.
2. **Regenerate the patch set** with `tools/patchset.py` against the new exe (`FL26_EXE`).
   - Its helpers find the sites: `callindex.py` (call graph), `impscan.py`, `boundscan.py`
     (loop bounds), `copyfields.py` (the save/load copy), `datecave.py`, `calwiden.py` with
     `calstride.py` / `tailscan.py` (the calendar).
   - `patches/layout.json` and the `*-sites.json` files hold addresses. Every address in them
     has to be found again in the new exe, by pattern, not by offset.
   - Run `calaudit.py` on the result.
3. **Re-find every address in the C sources.**
   - The `*_RVA` defines at the top of each `tools/native/*.c`, and the expected bytes next
     to them.
   - `OWNER_RVA`, the edit-block offsets (`REG_ARRAY_OFF`, `TODAY_OFF`), and the record
     strides: players 0x17c, clubs 0x690, coaches 0x258, regulations 0x314, match records
     0x254.
   - Rebuild the six DLLs ([building.md](building.md)).
4. **Re-find every address in the Lua modules.** Look for each `0x14...` and `va=` in
   `sider/*.lua` and `sider/experimental/*.lua`, along with the `old=` bytes:
   - the guards;
   - `fl26comptab`, `fl26catlist`, `fl26editlist`, `fl26slotnames`, `fl26seasonend` and
     `fl26augseason`;
   - `fl26ctlguard`, `fl26superguard` and `fl26resultsguard` (`fl26kitguard` wraps a Lua
     function of the Kit Server and has no address);
   - `fl26reg128`, `fl26slots250`, `fl26slot7`, `fl26regs600`, `fl26appcap`, `fl26regfast`;
   - `fl26rank`, which `tools/mkrankpatch.py` regenerates;
   - `fl26hdr255`.
5. **Start the game and read `sider.log`.** Every module has to report that it installed and
   that it read the world file, with no `MISMATCH` and no status number. Then run the
   in-game checklist in [testing.md](testing.md).

If a new exe moves only a few functions, a byte pattern search (the first 16 to 32 bytes the
DLL already checks) usually finds each one again quickly. If it changes the edit block layout,
the patch set has to be redone from the start.

### fl26slotnames and SmokePatch's CommonLib: leagues past competition id 255 (B427)

FL 2027's `modules\lib\CommonLib.lua` builds, from every read of `CompetitionEntry.bin`, a list of
clubs for each competition id in its playable list, and `tid_same_league(home, away)` answers the
tournament id two clubs share. `scoreboards.lua`, `referee.lua`, `omb.lua` and `SleeveBadge.lua`
ask it on `set_teams`, so it decides what a Kick Off match looks like. CommonLib reads the
competition id as ONE byte (entry +8). Our entries carry the high byte at +0x0B (`mkleague.py`,
`E_CID_HI`), so a league on 553 is read as 41 (the J.League) and its clubs land in that list; a
world's own ids in the playable list (`leaguebuilder.commonlib_leagues`) never match a byte, so
the league has no list of its own. On the GigaPack's built world 137 of CommonLib's lists held
clubs of another competition, 3,314 clubs in all.

`fl26slotnames.lua` (`ko_init`, only when the world file names a `cid` past 255) registers
`livecpk_read`, keeps the bytes of `CompetitionEntry.bin` as the game reads them, and on the next
`livecpk_make_key` or `set_teams` (CommonLib's own `livecpk_read` has run by then: our block is
before it in `sider.ini`, and the fix is done one event later on purpose) sets
`ctx.common_lib`'s tables: every list is rebuilt from the whole id (byte +8 and +0x0B), each
league of the world gets `teams_in_playable_leagues_map[cid]`, `compID_to_tournamentID_map[cid]`
and `tournamentID_to_compID_map[tid]`. CommonLib's file is not touched. The log line is
`fl26slotnames: Kick Off -- N league(s) of the world past competition id 255 given to CommonLib
under their own id; M club(s) taken out ...`. Test: `tools/test_kickoff_wide.py [<world folder>]`
(the module whole in Lua beside a stand-in that reads the file the way CommonLib does).
