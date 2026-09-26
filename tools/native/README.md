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
  (slots 69/73/75). Around 270 lines. Writes nothing at all (its loader changes three bytes
  of the game's slot switch, see `fl26clubs.lua`).
- **`fl26chain.dll`** (experimental) hooks the end-of-season step that applies promotion
  and relegation, and completes a chain of three or more divisions, which the game on its
  own only exchanges one joint of. Around 400 lines. Up to 8 chains.
- **`fl26swiss.dll`** (experimental) replaces the league schedule builder for the listed
  regulations only: the 36-club league phase of the Champions League, Europa League and
  Conference League (the draw tables are generated and checked by `tools/mkswiss.py` into
  `fl26swiss_table.h`), their 9-24 play-off and fixed knockout bracket, the UEFA access
  list, and the calendar of leagues that are not 20 clubs playing twice. About 1,700 lines.
  It writes no file; its log goes to `sider.log` through the loader.

None has third-party code or any network access.

## The shipped binaries

| file | SHA-256 |
|---|---|
| `sider/fl26join.dll` | `c107bd8387ba38073d4c4747e2f94f0604a50b535a6d644a0767d879aa4e7919` |
| `sider/experimental/fl26clubs.dll` | `2b79cb83eb24877553596d5fe9b18e7c1c453ff2e43d21915a788e2c977bb469` |
| `sider/experimental/fl26chain.dll` | `2a093ebd89478516609428c87252969521914f350670af2aa22b8ae2ea17f1d5` |
| `sider/experimental/fl26swiss.dll` | `1403737001c5c5a31cdda2c833a630be47ccff4b2564bf798d969d0202cbcfba` |

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
- `set_pre`, `enter_pre`, `bld_pre` -- observers only.
- `fl26_join_log`, `fl26_join_stats` -- the text log and eight counters the loader drains
  into `sider.log`.

Where a hook needs the game to do something (close a season, rebuild a record, keep a group
still) it calls the game's own function for it rather than writing the tables itself.

`fl26clubs.c` is the same shape, smaller: `fl26_clubs_install(base, cfg, ncfg)` takes the
`{slot, regulation id}` pairs from the loader and replaces two reader functions, and a slot
that is not in that list — or whose rulebook cannot be read yet — falls through to the
game's own answer, so no slot can come out emptier than it is today.
`fl26_clubs_log` / `fl26_clubs_stats` are the log and counters.

The addresses are for `FL_2026.exe` 26.0.0.0 (458,910,720 bytes), which has no ASLR. On any
other build the signature check fails and the game runs unmodified.
