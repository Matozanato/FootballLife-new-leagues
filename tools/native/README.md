# Native modules: fl26join.dll, fl26clubs.dll, fl26chain.dll and fl26swiss.dll

Four modules here are compiled rather than written in Lua, because each of them has to run a
few instructions of its own inside a live call, which is easier to get right in C than in
hand-assembled bytes. In each case a Lua loader (`sider/fl26joindll.lua`,
`sider/experimental/fl26clubs.lua`, `sider/experimental/fl26chain.lua`, `sider/experimental/fl26swiss.lua`) loads the DLL from `SiderAddons\modules\` at startup and
hands it the configuration; the DLL does the rest.

- **`fl26join.dll`** hooks eight functions so that added leagues are registered into a
  Master League season and closed again at the end of it, the way the shipped leagues are.
  About 1,000 lines of C, with a few lines of inline assembly per hook. The only file it
  writes is `SiderAddons\fl26join.log`.
- **`fl26clubs.dll`** (experimental) replaces the two functions that read the Select Team
  club list, answering from the league's own rulebook for named slots only. When a Master
  League is created it also keeps our clubs out of the Club World Cup "other clubs" pools
  (slots 69/73/75), and the clubs of the game that a world moved into one of its leagues (the
  world file's `nopool` line, `fl26_clubs_keep_out`) out of every "other clubs" pool. Around
  350 lines. Writes nothing at all (its loader changes three bytes of the game's slot switch,
  see `fl26clubs.lua`).
- **`fl26chain.dll`** (experimental) hooks the end-of-season step that applies promotion
  and relegation, and completes a chain of three or more divisions, which the game on its
  own only exchanges one joint of. Around 400 lines. Up to 8 chains. It also decides which
  clubs a country's cup takes when a world adds a second division under a shipped top flight:
  the top flight's alone, or both divisions with `cupall=1` (issue #32).
- **`fl26swiss.dll`** (experimental) replaces the league schedule builder for the listed
  regulations only: the 36-club league phase of the Champions League, Europa League and
  Conference League (the draw tables are generated and checked by `tools/mkswiss.py` into
  `fl26swiss_table.h`), their 9-24 play-off and fixed knockout bracket, the UEFA access
  list, and the calendar of leagues that are not 20 clubs playing twice. It also runs new
  continental cups named by `ccup` lines of a world file (groups then a knockout, or a
  straight knockout), as Mod Studio's League Builder writes them. The league-phase draw keeps
  associations apart as UEFA does (no opponent from a club's own country, at most two from any
  one other): `fl26swiss_draw.h` reshuffles each pot, with the countries the loader passes in
  `fl26_swiss_nations`, and `swissdraw_test.c` checks that search offline on random fields
  (`zig cc -O2 -o swissdraw_test.exe swissdraw_test.c`). About 3,700 lines.
  It writes no file; its log goes to `sider.log` through the loader.

None has third-party code or any network access.

## The shipped binaries

| file | SHA-256 |
|---|---|
| `sider/fl26join.dll` | `f1235180fa83b3d5a166a257468cf1085c336efbcf02fc94cba86bc147c5d311` |
| `sider/experimental/fl26clubs.dll` | `ddd572832ec68eec36bbaf18eba4cdc1e1c8341c6da40114bb61a3a8637cd943` |
| `sider/experimental/fl26chain.dll` | `4425f3fceee9a7a4fc8cb03234745280644dd6240aa9b072f87a474b99d7bb67` |
| `sider/experimental/fl26swiss.dll` | `074494fd2ec5be271ec49c7e13106fcf10ce44d45025c1f32e01193cba9c80a3` |

```powershell
(Get-FileHash "C:\fl26\sider\fl26join.dll" -Algorithm SHA256).Hash
```

If you would rather not run a binary you did not build, build it yourself; each is a plain
64-bit Windows DLL, about 75 KB, that imports kernel32 and the C runtime and nothing else.

## Building it yourself

The DLL is built with `zig cc`, which is a C compiler that needs no Visual Studio and no
SDK install. Download Zig 0.16.0 for Windows x86_64 from https://ziglang.org/download/,
unpack it anywhere, then from a Git Bash or MSYS shell:

```sh
ZIG=/c/tools/zig-x86_64-windows-0.16.0/zig.exe sh tools/native/build-join.sh
```

or the same command by hand, from any shell:

```
zig cc -shared -target x86_64-windows-gnu -O2 -s -o sider/fl26join.dll tools/native/fl26join.c -lkernel32
```

`fl26clubs.dll`, `fl26chain.dll` and `fl26swiss.dll` are built the same way, with
`build-clubs.sh` / `build-chain.sh` / `build-swiss.sh` (which regenerates the draw table with
Python first), or:

```
zig cc -shared -target x86_64-windows-gnu -O2 -s -o sider/experimental/fl26clubs.dll tools/native/fl26clubs.c -lkernel32
zig cc -shared -target x86_64-windows-gnu -O2 -s -o sider/experimental/fl26chain.dll tools/native/fl26chain.c -lkernel32
zig cc -shared -target x86_64-windows-gnu -O2 -s -o sider/experimental/fl26swiss.dll tools/native/fl26swiss.c -lkernel32
```

The scripts write the DLL next to the source (`tools/native/fl26join.dll`) unless you
pass an output path as the first argument; copy the result to `SiderAddons\modules\`.
Any C compiler that targets x86-64 Windows and understands GCC-style inline assembly
(`__attribute__((naked))`, AT&T syntax) should work as well -- clang does; MSVC does not,
because it has no inline assembly on x86-64.

## What is in the source, for reviewers

- `fl26_join_install(base, cave, ids, n, logpath)` -- verifies the first bytes of each of
  the eight functions against the bytes this build has (a mismatch installs nothing and
  returns a status the loader prints), allocates a trampoline within reach of each hook,
  and redirects the function entry to a handler.
- `join_pre` -- appends our ids to the vector `register_all` received, skipping any id whose
  regulation record already carries a season year.
- `door_pre` / `door_post` -- refuses the season builder's creation-time ask for our ids
  (they enter through `register_all` instead) and logs every answer the door gives for them.
- the teardown hook -- adds our ids to the July list of competitions whose season is closed
  (the list is compiled into the exe and never had them), and keeps them off the New Year
  one, since their season runs August to May.
- `close_handler` -- keeps our ids out of the New Year close of calendar-year competitions.
- `mover_handler` -- at the season end, sends a league that has no final table down the
  game's own no-movement path instead of letting it stop the whole group's promotions.
- `reg_fix_pre` / `reg_post` -- at registration, resets a season that is already over and
  rebuilds a stale season record, so a league is not refused a new season.
- `fl26_join_season_types` -- the world file's `season <region> <type>` lines, answered in
  front of the game's own region -> season type table (0x141576140), so a new country can play
  February to December.
- `canon_listed` -- at the door of our leagues, a club value that does not point at its own
  team record gets the row of the one record with its id (the "same club on every row" of a
  split phase, issue #37).
- `set_pre`, `enter_pre`, `bld_pre` -- observers only.
- `fl26_join_log`, `fl26_join_stats` -- the text log and eight counters the loader drains
  into `sider.log`.

Where a hook needs the game to do something (close a season, rebuild a record, keep a group
still) it calls the game's own function for it rather than writing the tables itself.

`fl26clubs.c` is the same shape, smaller: `fl26_clubs_install(base, cfg, ncfg)` takes the
`{slot, regulation id}` pairs from the loader and replaces two reader functions, and a slot
that is not in that list — or whose rulebook cannot be read yet — falls through to the
game's own answer, so no slot can come out emptier than it is today.
`fl26_clubs_keep_out(tids, n)` takes the team ids of the world's `nopool` line.
`fl26_clubs_log` / `fl26_clubs_stats` are the log and counters.

The addresses are for `FL_2026.exe` 26.0.0.0 (458,910,720 bytes), which has no ASLR. On any
other build the signature check fails and the game runs unmodified.
