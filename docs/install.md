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

Copy all nine files from this repository's `sider/` folder into `SiderAddons\modules\`:

```
fl26caps.lua
fl26nullguard.lua
fl26nullguard2.lua
fl26nullguard3.lua
fl26nullguard4.lua
fl26nullguard5.lua
fl26nullguard7.lua
fl26nullguard8.lua
fl26hdr127.lua
```

> **Updating from an earlier download?** `fl26caps.lua` now also raises the fixture list,
> which makes the edit block bigger. A save is only loadable by the patch set that wrote
> it, so **saves made with the previous version will not load.** Finish the season you are
> in, or keep the old `fl26caps.lua` for that world. The guards and `fl26hdr127.lua` do not
> have this problem: they only write small trampolines into spare code, and saves survive
> them.

## 3. Register them in sider.ini

Open `SiderAddons\sider.ini`. Find the block of `lua.module = ...` lines and add these **in
this order**, before any other FL26 modules you may have and after Sider's own:

```ini
lua.module = "fl26caps.lua"
lua.module = "fl26nullguard.lua"
lua.module = "fl26nullguard3.lua"
lua.module = "fl26nullguard2.lua"
lua.module = "fl26nullguard4.lua"
lua.module = "fl26nullguard5.lua"
lua.module = "fl26nullguard7.lua"
lua.module = "fl26nullguard8.lua"
lua.module = "fl26hdr127.lua"
```

The order matters: `fl26caps.lua` must come first, and the guards write small trampolines
into fixed spare bytes of the code section in a fixed order. (nullguard3 before nullguard2
is deliberate; it is the order they were verified in.)

## 4. Start the game and read sider.log

Start FL26 once, get to the main menu, quit, and open `SiderAddons\sider.log`. You must see
nine lines like these:

```
[fl26caps.lua] fl26caps: applied all 2760 patches -- block 0x1877068 -> 0x3171a68, 2760 patches
[fl26nullguard.lua] fl26caps: applied all 2 patches -- nullguard: null-check at 0x141fea5b0
[fl26nullguard3.lua] fl26caps: applied all 2 patches -- nullguard3: schedule null-check at 0x140cd6a1c
[fl26nullguard2.lua] fl26caps: applied all 2 patches -- nullguard2: null-check at 0x140fc9238
[fl26nullguard4.lua] fl26caps: applied all 2 patches -- nullguard4: null-check at 0x1415720d0
[fl26nullguard5.lua] fl26caps: applied all 2 patches -- nullguard5: null-check at 0x1414c66c0
[fl26nullguard7.lua] fl26caps: applied all 2 patches -- nullguard7: squad-table null-check at 0x14128a3a3
[fl26nullguard8.lua] fl26caps: applied all 2 patches -- nullguard8: standings-position guard at 0x1413236e1
[fl26hdr127.lua] fl26caps: applied all 29 patches -- hdr127: season header widened to 127 competitions, 599 phase tables
```

Anything else — `MISMATCH`, `ABORTED`, `WRITE FAILED`, `PARTIAL` — means that module did
not apply. `ABORTED` is safe (nothing was written). `PARTIAL` is not: quit the game and open
an issue with the log.

With the modules applied and **no new world yet**, the game should play exactly as before.
That is a useful first test in itself: if the shipped game misbehaves with only the modules
installed, please report it.

## 4b. The experimental modules, later

`sider/experimental/` holds two modules that go further than the nine above and have not
been through a full season yet: 192 competitions instead of 127, and every league selectable
in the Select Team list. Add them **one at a time**, after the nine have been confirmed, and
read
[sider/experimental/README.md](../sider/experimental/README.md) first. `fl26hdr192.lua`
replaces `fl26hdr127.lua`; never run both, since they patch the same thirteen places.

## 5. Add a world

The modules only make room. The clubs and leagues come from a `livecpk` root you generate
from your own game data: [build-your-world.md](build-your-world.md).

## Removing

Delete the nine `lua.module` lines (or the files) and comment out the `cpk.root` line of your
world. Saves made with the world will not load afterwards; restore your backup.
