# Install

Everything here goes into the `SiderAddons` folder that Football Life 2026 ships with, next to
`FL_2026.exe`. Nothing is written to the game's own files.

This is the reference version, with the reasons. For one continuous walkthrough from a stock
install to a playing season — including building the world and what to look at in the game —
use [step-by-step.md](step-by-step.md) instead.

## 0. Back up first

- `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save` — your Master League saves.
- `SiderAddons\sider.ini`.

A save made with the patch set installed contains more clubs than the unpatched game can
read. Do not expect to load such a save after removing the modules.

## 1. Check your game build

The modules verify every byte they change and refuse a different build, so this step only
saves you a confusing startup. In PowerShell:

```powershell
(Get-Item "C:\path\to\FL_2026.exe").Length
(Get-FileHash "C:\path\to\FL_2026.exe" -Algorithm SHA256).Hash
```

Expected: `458910720` and
`7C27ECB303B71331E36F9CCD8AC879F0F0D8C56C754BD4D0D2E9C8353464F847`.

If yours differ, the modules will log `MISMATCH` and `ABORTED` and the game runs unmodified.
Please open an issue with your version so we know which builds are out there.

## 2. Copy the modules

Copy all eleven files from this repository's `sider/` folder (not the `experimental`
subfolder) into `SiderAddons\modules\`:

```
fl26caps.lua          the patch set: bigger tables
fl26nullguard.lua     seven crash guards
fl26nullguard2.lua
fl26nullguard4.lua
fl26nullguard5.lua
fl26nullguard7.lua
fl26nullguard8.lua
fl26nullguard9.lua
fl26joindll.lua       gets every added league into the season ...
fl26join.dll          ... and the compiled module it loads
fl26hdr127.lua        room for 127 competitions in a season
```

`fl26join.dll` is the one compiled file. It must sit in the same `modules\` folder as
`fl26joindll.lua`, which loads it from there. What it is, its checksum, and how to build it
yourself from the source in `tools/native/` are in
[tools/native/README.md](../tools/native/README.md).

> **Updating from an earlier download?** Two things changed on 2026-09-22.
>
> - **`fl26nullguard3.lua` is replaced by `fl26nullguard9.lua`.** Both guard the same
>   unchecked read of the schedule list; the new one covers it on both paths that reach it
>   (loading a season, and the board meeting when a season is created), the old one only on
>   the first. They patch overlapping bytes, so **remove the `fl26nullguard3.lua` line** — if
>   both are listed, whichever loads second logs `MISMATCH` and `ABORTED` and does nothing,
>   which is harmless but confusing.
> - **`fl26joindll.lua` + `fl26join.dll` are new**, and need one setting in `sider.ini`
>   (step 3). Neither changes the edit block or any table, so a season saved before them
>   still loads.
>
> If you downloaded before 2026-09-17: `fl26caps.lua` also changed then, and it made the
> edit block bigger. A save is only loadable by the patch set that wrote it, so **saves made
> with that earlier version will not load.** Finish the season you are in, or keep the old
> `fl26caps.lua` for that world. The guards, `fl26joindll.lua` and `fl26hdr127.lua` do not
> have this problem: they only write small trampolines into spare code, and saves survive
> them.

## 3. Register them in sider.ini

Open `SiderAddons\sider.ini` in a text editor. Two edits.

**3a. The module lines.** Find the block of `lua.module = ...` lines and add these **in this
order**, before any other FL26 modules you may have and after Sider's own:

```ini
lua.module = "fl26caps.lua"
lua.module = "fl26nullguard.lua"
lua.module = "fl26nullguard2.lua"
lua.module = "fl26nullguard4.lua"
lua.module = "fl26nullguard5.lua"
lua.module = "fl26nullguard7.lua"
lua.module = "fl26nullguard8.lua"
lua.module = "fl26nullguard9.lua"
lua.module = "fl26joindll.lua"
lua.module = "fl26hdr127.lua"
```

Ten lines for eleven files: `fl26join.dll` has no line of its own, `fl26joindll.lua` loads
it. The order matters: `fl26caps.lua` must come first, the guards write small trampolines
into fixed spare bytes of the code section in a fixed order, and `fl26joindll.lua` goes
after the guards and before `fl26hdr127.lua` -- that is the order the set was verified in.

**3b. One setting.** `fl26joindll.lua` needs Sider's Lua extension, which gives modules the
`ffi` library that loads a DLL. Find this line in `sider.ini` -- it is in the same `[sider]`
section as the module lines, usually below them -- and make sure it reads `1`:

```ini
luajit.ext.enabled = 1
```

If the line is not there at all, add it. Without it the loader stops at once and writes
`fl26joindll: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini` to the log; the
game runs with everything else applied and this one module doing nothing.

## 4. Start the game and read sider.log

Start FL26 once, get to the main menu, quit, and open `SiderAddons\sider.log`. You must see
ten lines like these, one per module line in `sider.ini`:

```
[fl26caps.lua] fl26caps: applied all 2760 patches -- block 0x1877068 -> 0x3171a68, 2760 patches
[fl26nullguard.lua] fl26caps: applied all 2 patches -- nullguard: null-check at 0x141fea5b0
[fl26nullguard2.lua] fl26caps: applied all 2 patches -- nullguard2: null-check at 0x140fc9238
[fl26nullguard4.lua] fl26caps: applied all 2 patches -- nullguard4: null-check at 0x1415720d0
[fl26nullguard5.lua] fl26caps: applied all 2 patches -- nullguard5: null-check at 0x1414c66c0
[fl26nullguard7.lua] fl26caps: applied all 2 patches -- nullguard7: empty squad table guarded at 0x14128a3a3
[fl26nullguard8.lua] fl26caps: applied all 2 patches -- nullguard8: negative standings position guarded at 0x1413236e1
[fl26nullguard9.lua] fl26caps: applied all 2 patches -- nullguard9: empty schedule list guarded at 0x140cd6a18
[fl26joindll.lua] fl26joindll: installed -- 39 added leagues will be registered on the first registration day of the season; the DLL's own log is ...\SiderAddons\fl26join.log (F10 = counters)
[fl26hdr127.lua] fl26caps: applied all 29 patches -- hdr127: season header widened to 127 competitions, 599 phase tables
```

The `fl26joindll` line is followed by one more from the DLL itself,
`fl26join: hooks live (register_all ..., enter_season ..., builder ..., door ...), 39 competition ids`.
From then on that module also writes `SiderAddons\fl26join.log`, a small text file with one
line per decision it takes; it is created on the first start and appended to, and it is the
file to attach when an added league has no fixtures.

Anything else — `MISMATCH`, `ABORTED`, `WRITE FAILED`, `PARTIAL` — means that module did
not apply. `ABORTED` is safe (nothing was written). `PARTIAL` is not: quit the game and open
an issue with the log. For `fl26joindll.lua` the failure lines read `install FAILED (status
N) -- ...`, `LoadLibraryA failed` (the DLL is not in `modules\`) or `global ffi is nil` (step
3b); in all three cases the game is unmodified by that module.

With the modules applied and **no new world yet**, the game should play exactly as before.
That is a useful first test in itself: if the shipped game misbehaves with only the modules
installed, please report it.

## 4b. The experimental modules, later

`sider/experimental/` holds eight modules that go further than the eleven above and have not
been through a full season yet: 192 competitions instead of 127; the Select Team list fixed
three ways (leagues that had no slot, slots that draw a hard-coded heading, slots that show
the wrong clubs); 64 menu regions instead of 29; and a league rank wide enough for five
divisions with the relegation gate to match. Add them **one at a time**, after the eleven
have been confirmed, and read
[sider/experimental/README.md](../sider/experimental/README.md) first — several of them
depend on each other and two carry a slot list you must fill in from your own world.
`fl26hdr192.lua` replaces `fl26hdr127.lua`; never run both, since they patch the same
thirteen places. If you use it, keep `fl26joindll.lua` before it, where `fl26hdr127.lua` was.

## 5. Add a world

The modules only make room. The clubs and leagues come from a `livecpk` root you generate
from your own game data: [build-your-world.md](build-your-world.md).

## Removing

Delete the ten `lua.module` lines (or the files) and comment out the `cpk.root` line of your
world. `luajit.ext.enabled` can stay as it is; Sider's own modules do not mind it. Saves made
with the world will not load afterwards; restore your backup.
