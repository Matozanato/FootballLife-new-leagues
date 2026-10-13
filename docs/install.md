# Install

> **Easier way:** [FL26 Mod Studio](mod-studio-guide.md) ([hrvatski](mod-studio-guide.hr.md)) does
> all of this from one window -- install, build leagues, edit players, switch mods on and
> off. This page is the manual route, and what the program does underneath.

Everything here goes into the `SiderAddons` folder that Football Life 2026 ships with, next to
`FL_2026.exe`. Nothing is written to the game's own files.

For the whole route on one page, including leagues in other countries and the new European
format, see [how-to.md](how-to.md). This is the reference version, with the reasons. For one continuous walkthrough from a stock
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

Also known to work (reported by a tester, all patches applied): FL26 v2.2, file version
`26.2.0.3`, same size, SHA-256
`9EE0C30651E5E3C37E3D308FB8224F5FEA135CD8E929DEE2CDDCA6E041836281`. A different hash does not
by itself mean the modules will refuse; `sider.log` tells you (next step).

If yours differ, the modules will log `MISMATCH` and `ABORTED` and the game runs unmodified.
Please open an issue with your version so we know which builds are out there.

## 2. Copy the modules

> **Mod Studio installs these for you** (Home > Build and install, or Install modules), and that
> is the way we test. The steps below are for installing by hand, from the same files.

Since 0.2.2 the module set is the one in the Mod Studio download: its `pack\modules\` folder
holds every file (the Lua modules, the compiled DLLs, the regen face pack) and
`pack\modules.txt` the order they load in. Copy everything in `pack\modules\` into
`SiderAddons\modules\`, and the folder `pack\livecpk\FL26 Regen Faces` into
`SiderAddons\livecpk\`.

The files come from this repository: the Lua from `sider/` and `sider/experimental/`, the
DLLs built from `tools/native/*.c` (`tools/native/build-*.sh`; what each is and its checksum:
[tools/native/README.md](../tools/native/README.md)), and the two bundles `fl26guards.lua`
and `fl26lateguards.lua` made by `tools/lbpack.py` from the single guard files. Do not copy
the `.dll` files committed in `sider/`: the pack builds them fresh from the sources.

> **Updating to 0.2.2?** The raised limits are in: 2400 clubs, 250 competition slots, 255
> competitions a season (`fl26hdr255` replaces `fl26hdr192`), 128 regions (`fl26reg128`
> replaces `fl26reg64`), 600 regulations, 65,000 appearance records. `fl26caps.lua` is a new
> set (3510 patches), so **a career saved with 0.2.1 or older does not load** (the game stays on
> the loading screen with no message; close it in Task Manager): start a new one.
> Install modules switches off the old lines it replaces (`fl26hdr192`, `fl26hdr127`,
> `fl26reg64`, `fl26deep4`, `fl26nullguard3` and the single guards of the bundles).
>
> Older notes: 0.2.0 made a calendar day hold 792 matches (a new set, old careers void);
> `fl26nullguard3.lua` was replaced by `fl26nullguard9.lua` on 2026-09-22 (they overlap: never
> both); `fl26joindll.lua` + `fl26join.dll` came on 2026-09-22.

## 3. Register them in sider.ini

Open `SiderAddons\sider.ini` in a text editor. Two edits.

**3a. The module lines.** Above the first `lua.module` line already in the file, add one line
per name in `pack\modules.txt`, in that order (0.2.2):

```ini
lua.module = "fl26caps.lua"
lua.module = "fl26appcap.lua"
lua.module = "fl26regs600.lua"
lua.module = "fl26slots250.lua"
lua.module = "fl26slot7.lua"
lua.module = "fl26guards.lua"
lua.module = "fl26regfast.lua"
lua.module = "fl26walk.lua"
lua.module = "fl26joindll.lua"
lua.module = "fl26hdr255.lua"
lua.module = "fl26chain.lua"
lua.module = "fl26comptab.lua"
lua.module = "fl26slotnames.lua"
lua.module = "fl26clubs.lua"
lua.module = "fl26regen.lua"
lua.module = "fl26editlist.lua"
lua.module = "fl26edit.lua"
lua.module = "fl26rank.lua"
lua.module = "fl26deeprank.lua"
lua.module = "fl26regions.lua"
lua.module = "fl26reg128.lua"
lua.module = "fl26regnames.lua"
lua.module = "fl26catlist.lua"
lua.module = "fl26swiss.lua"
lua.module = "fl26augseason.lua"
lua.module = "fl26lateguards.lua"
lua.module = "fl26seasonend.lua"
```

The DLLs have no line: each `.lua` loads its own. `fl26regions.lua` and `fl26regnames.lua`
belong to a world (Mod Studio writes them when it switches a world on). `fl26caps.lua` must
come first; the rest is the order the set is played in.

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

Start FL26 once, get to the main menu, quit, and open `SiderAddons\sider.log`. Every module
writes an `applied all ...` line (or says why it did nothing). Among them:

```
[fl26caps.lua] fl26caps: applied all 3510 patches -- block 0x1877068 -> 0x4a2b568, 3510 patches
[fl26regs600.lua] fl26regs: applied all 4 patches -- regulation records 600: ...
[fl26slots250.lua] fl26slots: applied all 35 patches -- competition slots 123 -> 250 ...
[fl26guards.lua] fl26caps: applied all 2 patches -- nullguard: null-check at 0x141fea5b0
[fl26joindll.lua] fl26joindll: installed -- 86 added leagues will be registered on the first registration day of the season; ...
[fl26hdr255.lua] fl26caps: applied all 45 patches -- hdr255: season header widened to 255 competitions, 595 phase tables
```

No line may say `MISMATCH` or `ABORTED`. One that does means two modules patch the same
bytes (an old line left on) or a different game build: send the sider.log.

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

## 4b. The experimental modules

Since 0.2.0 the modules of `sider/experimental/` that a world needs are in the pack and in the
list above. The others there (`fl26deep4`, `fl26hdr192`, `fl26reg64` ...) are older versions kept
to read; [sider/experimental/README.md](../sider/experimental/README.md) says which replaced
which.

## 5. Add a world

The modules only make room. The clubs and leagues come from a `livecpk` root you generate
from your own game data: [build-your-world.md](build-your-world.md).

## Removing

Delete the `lua.module` lines of section 3a (or the files) and comment out the `cpk.root` line of your
world. `luajit.ext.enabled` can stay as it is; Sider's own modules do not mind it. Saves made
with the world will not load afterwards; restore your backup.
