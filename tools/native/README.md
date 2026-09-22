# Native module: fl26join.dll

`sider/fl26join.dll` is the one compiled module in this repository. `sider/fl26joindll.lua`
loads it from `SiderAddons\modules\` at startup and hands it the list of your leagues'
rulebook ids; the DLL hooks four functions of the game (see the header of
`fl26joindll.lua` and the comments in `fl26join.c`) so that those leagues are registered
into the Master League season. Everything the DLL does is in `fl26join.c` -- under 500
lines of C and a few lines of inline assembly, no third-party code, no network, no file
written other than `SiderAddons\fl26join.log`.

## The shipped binary

| file | SHA-256 |
|---|---|
| `sider/fl26join.dll` | `4b2dcdec0dd9798055e1ad2ef9bde3dc1e77e0ff39ec89b8f6c0b103b4aab624` |

```powershell
(Get-FileHash "C:\fl26\sider\fl26join.dll" -Algorithm SHA256).Hash
```

If you would rather not run a binary you did not build, build it yourself; the result is a
plain 64-bit Windows DLL, about 75 KB, that imports kernel32 and the C runtime and nothing
else.

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

`build-join.sh` writes the DLL next to the source (`tools/native/fl26join.dll`) unless you
pass an output path as its first argument; copy the result to `SiderAddons\modules\`.
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

The addresses are for `FL_2026.exe` 26.0.0.0 (458,910,720 bytes), which has no ASLR. On any
other build the signature check fails and the game runs unmodified.
