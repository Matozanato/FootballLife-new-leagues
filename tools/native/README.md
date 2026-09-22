# Native modules: fl26join.dll and fl26clubs.dll

Two modules here are compiled rather than written in Lua, because each of them has to run a
few instructions of its own inside a live call, which is easier to get right in C than in
hand-assembled bytes. In both cases a Lua loader (`sider/fl26joindll.lua`,
`sider/experimental/fl26clubs.lua`) loads the DLL from `SiderAddons\modules\` at startup and
hands it the configuration; the DLL does the rest.

- **`fl26join.dll`** hooks four functions so that added leagues are registered into a Master
  League season. Under 500 lines of C and a few lines of inline assembly. Writes no table;
  the only file it touches is `SiderAddons\fl26join.log`.
- **`fl26clubs.dll`** (experimental) replaces the two functions that read the Select Team
  club list, answering from the league's own rulebook for named slots only. Around 220 lines.
  Writes nothing at all.

Neither has third-party code or any network access.

## The shipped binaries

| file | SHA-256 |
|---|---|
| `sider/fl26join.dll` | `4b2dcdec0dd9798055e1ad2ef9bde3dc1e77e0ff39ec89b8f6c0b103b4aab624` |
| `sider/experimental/fl26clubs.dll` | `1db2a4f9af91a5c76f903d5443eb08df417006b2bd1a3674aa87a8957a43aae5` |

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

`fl26clubs.dll` is built the same way, with `build-clubs.sh` or:

```
zig cc -shared -target x86_64-windows-gnu -O2 -s -o sider/experimental/fl26clubs.dll tools/native/fl26clubs.c -lkernel32
```

Both scripts write the DLL next to the source (`tools/native/fl26join.dll`) unless you
pass an output path as the first argument; copy the result to `SiderAddons\modules\`.
Any C compiler that targets x86-64 Windows and understands GCC-style inline assembly
(`__attribute__((naked))`, AT&T syntax) should work as well -- clang does; MSVC does not,
because it has no inline assembly on x86-64.

## What is in the source, for reviewers

- `fl26_join_install(base, cave, ids, n, logpath)` -- verifies the first bytes of each of
  the four functions against the bytes this build has (a mismatch installs nothing and
  returns a status the loader prints), allocates a trampoline within reach of each hook,
  and redirects the function entry to a handler.
- `join_pre` -- the fix: appends our ids to the vector `register_all` received, skipping
  any id whose regulation record already carries a season year.
- `door_pre` / `door_post` -- refuses the season builder's creation-time ask for our ids
  (they enter through `register_all` instead) and logs every answer the door gives for them.
- `enter_pre`, `bld_pre` -- observers only. No hook calls any game code; the regulation
  record is found by walking the array.
- `fl26_join_log`, `fl26_join_stats` -- the text log and eight counters the loader drains
  into `sider.log`.

`fl26clubs.c` is the same shape, smaller: `fl26_clubs_install(base, cfg, ncfg)` takes the
`{slot, regulation id}` pairs from the loader and replaces two reader functions, and a slot
that is not in that list — or whose rulebook cannot be read yet — falls through to the
game's own answer, so no slot can come out emptier than it is today.
`fl26_clubs_log` / `fl26_clubs_stats` are the log and counters.

The addresses are for `FL_2026.exe` 26.0.0.0 (458,910,720 bytes), which has no ASLR. On any
other build the signature check fails and the game runs unmodified.
