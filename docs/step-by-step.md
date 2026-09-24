# Step by step, on a clean install

This is the walkthrough for testing the beta from the beginning: a stock Football Life 2026,
nothing else installed, no other mods loaded. Every step says what you should see, and the
ones worth reporting say so. **Reporting a step that worked is as useful as reporting one
that did not** — most of what we still do not know is which of these steps behave the same
way on somebody else's machine.

Roughly twenty minutes, most of it the game starting up.

Where a path is written as `C:\Football Life 2026`, use your own.

---

## Before you start

**Use a stock install.** Other mods that replace `common/etc/pesdb/*.bin` — squad packs,
league packs, option files — change the very tables this beta generates from, and then a
failure tells us nothing. If you have those installed, test this on a second copy of the
game, or be ready to say exactly what else is in there.

**What you need**

- Football Life 2026, the build below.
- Python 3.10 or newer, from python.org, "Add python.exe to PATH" ticked.
- No Python packages for these steps. (Only `tools/mkcrests.py`, step 7, wants `Pillow`.)
- The Sider that Football Life ships with, in `SiderAddons\`. Nothing extra to install.

**Back up, in this order**

1. `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save` — your Master League saves.
2. `SiderAddons\sider.ini`.

A save made with this beta holds more clubs than the unpatched game can read, and a save made
with one version of the patch set cannot be read by another. Treat saves made while testing
as disposable.

---

## 1. Check your game build

```powershell
(Get-Item "C:\Football Life 2026\FL_2026.exe").Length
(Get-FileHash "C:\Football Life 2026\FL_2026.exe" -Algorithm SHA256).Hash
```

Expected: `458910720` and
`7C27ECB303B71331E36F9CCD8AC879F0F0D8C56C754BD4D0D2E9C8353464F847`.

Also known to work (reported by a tester, all patches applied): FL26 v2.2, file version
`26.2.0.3`, same size, SHA-256
`9EE0C30651E5E3C37E3D308FB8224F5FEA135CD8E929DEE2CDDCA6E041836281`. A different hash does not
by itself mean the modules will refuse; `sider.log` tells you (next step).

**Different numbers? Stop and report them.** Everything here is byte-exact against that one
build. The modules will refuse to touch a different one — they log `MISMATCH` and the game
runs unmodified — but knowing which other builds exist is itself one of the things this beta
is trying to find out.

## 2. Get the files

Download this repository (green **Code** button → *Download ZIP*) and unpack it somewhere of
your own, e.g. `C:\fl26`. Do not unpack it into the game folder.

## 3. Install the eleven modules

Copy all eleven files from `sider\` (not the `experimental` subfolder) into
`C:\Football Life 2026\SiderAddons\modules\`:

```
fl26caps.lua          fl26nullguard.lua    fl26nullguard2.lua   fl26nullguard4.lua
fl26nullguard5.lua    fl26nullguard7.lua   fl26nullguard8.lua   fl26nullguard9.lua
fl26joindll.lua       fl26join.dll         fl26hdr127.lua
```

Ten Lua modules and one DLL. `fl26join.dll` is loaded by `fl26joindll.lua` from that same
folder, so the two must be next to each other. What the DLL is and how to build it yourself
from the source in `tools\native\` is in [tools/native/README.md](../tools/native/README.md);
its checksum is there too, if you want to check what you copied.

Leave `sider\experimental\` alone for now; that is step 10.

> Updating from a download made before 2026-09-22? `fl26nullguard3.lua` is gone; delete it
> from `modules\` and from `sider.ini`. `fl26nullguard9.lua` guards the same place and more,
> and the two cannot be loaded together.

## 4. Register them in sider.ini

Open `SiderAddons\sider.ini` in a text editor (Notepad is fine).

**4a.** Find the `lua.module = ...` lines and add these **in exactly this order**, after
Sider's own and before anything else of yours:

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

Ten lines: the DLL has none of its own. `fl26caps.lua` must come first. The guards write
small stubs into fixed spare bytes of the code section, and they claim them in this order.
`fl26joindll.lua` goes after the guards and before `fl26hdr127.lua`.

**4b.** Find the line `luajit.ext.enabled` further down in the same file and make sure it
says `1`:

```ini
luajit.ext.enabled = 1
```

If it is missing, add it below the module lines. This switches on the part of Sider's Lua
that can load a DLL; without it `fl26joindll.lua` does nothing and says so in the log.

Save the file.

## 5. First run: the modules alone, with no new world

Start the game, get to the main menu, quit. Open `SiderAddons\sider.log` and look for ten
lines like these, one per module:

```
[fl26caps.lua] fl26caps: applied all 2759 patches -- block 0x1877068 -> 0x3cd4ae8, 2759 patches
[fl26nullguard.lua] fl26caps: applied all 2 patches -- nullguard: null-check at 0x141fea5b0
...
[fl26nullguard9.lua] fl26caps: applied all 2 patches -- nullguard9: empty schedule list guarded at 0x140cd6a18
[fl26joindll.lua] fl26joindll: installed -- 39 added leagues will be registered on the first registration day of the season; the DLL's own log is ...\SiderAddons\fl26join.log (F10 = counters)
[fl26joindll.lua] fl26joindll: fl26join: hooks live (register_all 141343bf0, enter_season 14158f420, builder 1413156e0, door 1413ac170), 39 competition ids
[fl26hdr127.lua] fl26caps: applied all 32 patches -- hdr127: season header widened to 127 competitions, 599 phase tables
```

| what the log says | what it means |
|---|---|
| `applied all N patches` on the nine patch modules, and `installed` + `hooks live` for fl26joindll | good, carry on |
| `MISMATCH` then `ABORTED` | that module wrote nothing and the game is unmodified; **report the mismatch lines**, they name the addresses |
| `WRITE FAILED` or `PARTIAL` | quit the game and report it; `PARTIAL` means a module got half-applied |
| `fl26joindll: global ffi is nil` | step 4b was skipped; fix `luajit.ext.enabled` and start again |
| `fl26joindll: LoadLibraryA failed` | `fl26join.dll` is not in `modules\` next to the Lua file |
| `fl26joindll: install FAILED (status N)` | the DLL found different bytes at one of its eight hooks and installed nothing; **report it with the number** |

A new file, `SiderAddons\fl26join.log`, appears after this run. It is short at this point
(the `hooks live` line); it fills when a season is created.

Now **play the stock game for a few minutes with the modules on**: an exhibition match, and
a Master League season with a shipped club, far enough to see the fixture list. Nothing
should differ from the unmodified game.

> **Report point A.** This is the single most valuable result in the whole guide. Tables
> have been made bigger and no data has been added yet, so the game has more room and the
> same content: if anything at all behaves differently here, that is a bug in the patch set
> itself and everything after it is built on sand.

## 6. Build a world

The modules only make room; the leagues and clubs come from a folder you generate out of your
own game's tables. Nothing is downloaded and no game data is shipped in this repository.

**6a. Unpack the tables.** They live inside the game's CPK archives, under
`common/etc/pesdb/`:

```powershell
cd C:\fl26
python tools\cpk.py "C:\Football Life 2026\download\<some>.cpk"     # look for common/etc/pesdb/Team.bin
python tools\cpkx.py "C:\Football Life 2026\download\<that one>.cpk" C:\fl26\pesdb
```

Which archive holds the live tables depends on your install — the newest data pack wins. When
you have the right one, `C:\fl26\pesdb\common\etc\pesdb\` contains `Team.bin`,
`Player.bin`, `Competition.bin`, `CompetitionRegulation.bin`, `CompetitionEntry.bin` and
`PlayerAssignment.bin`.

Then tell the tools where things live:

```powershell
$env:FL26_DIR   = "C:\Football Life 2026"
$env:FL26_PESDB = "C:\fl26\pesdb\common\etc\pesdb"
```

**6b. Generate.** Start small — six leagues of twenty clubs. This is the shape most of the
beta's own testing was done on, so a failure here is a clear signal:

```powershell
python tools\mkworld.py   --base $env:FL26_PESDB --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --leagues 6 --clubs 20
python tools\mkplayers.py --base $env:FL26_PESDB --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --per 30 --cap 51729
```

**Keep the output of `mkworld.py`.** It lists the competition and rulebook id of every league
it made, and both the check below and any bug report need it.

**6c. The one check that matters: the rulebook ids.** Two things decide whether a new league
ever plays a match, and both are keyed by the league's **rulebook (regulation) id**:

1. **Its fixture dates** come from a small table inside `fl26caps.lua`. A league whose id is
   not in that table is never scheduled: it shows up in the menus, you can pick a club from
   it, and the season gives it no matches.
2. **Its entry into the season** is done by `fl26joindll.lua`, which carries a list of ids
   near the top of the file (`local IDS = { ... }`) and presents each of them to the game
   on the first registration day. A league whose id is not in that list is only entered if
   the game happens to list it itself — and for a league standing in a country of its own,
   it does not.

Both ship with the same 39 ids, which are exactly the ids a default `mkworld.py` run hands
out, in order:

```
11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121
138 139 140 143 144 145 146 170 171 173 174 176 178 179 180 181 182 183 184 185
```

Compare them with the `regulation` column `mkworld.py` printed. On a stock install with the
defaults, the first 39 leagues you build land exactly on these and there is nothing to do.
If one of yours does not: add it to `IDS` in `fl26joindll.lua` (a plain text edit, any
editor), and for the dates see [build-your-world.md](build-your-world.md) — that one needs
the patch set regenerated.

## 7. Optional: give the clubs their own crests and kits

Skip this the first time round. It changes nothing about whether a season works — it only
stops every new club from wearing the crest of the club it was cloned from.

```powershell
python -m pip install pillow
python tools\mkcrests.py --team-bin "C:\Football Life 2026\SiderAddons\livecpk\_FL26World\common\etc\pesdb\Team.bin" --flags "C:\Football Life 2026\SiderAddons\livecpk\_FL26World"
```

Kits need one more archive out of the game (`uniform/team/UniformParameter.bin`, in
`dt34_g4.cpk`); `tools\mkkits.py` with no arguments prints how.

## 8. Activate the world

Only one of these worlds may be live at a time. In `sider.ini`, above the other `cpk.root`
lines:

```ini
cpk.root = ".\livecpk\_FL26World"
```

or let the tool do it:

```powershell
python tools\siderroot.py _FL26World
```

## 9. Play it, and watch for these eight things

Start the game. In order, because each one is visible earlier than the next — **stop at the
first one that disagrees with what is written here, and report that one**; what comes after
a failure is usually noise.

1. **The leagues exist.** In the competition list, under England by default, `FL League 01`
   … `FL League 06` with twenty placeholder clubs each (`FL 0001`, `FL 0002`, …).
2. **An exhibition match.** Two new clubs, kickoff, 22 players on the pitch.
3. **A Master League season starts.** Pick a club from one of the new leagues, pick a
   manager, accept. The season should generate, the board meeting and press conference
   should pass, and the hub should come up.
   *If it crashes while the season is being generated, start it again before reporting.*
   There is a crash in the game's own scene setup, at the manager-settings step, that
   happens on a clean install too. On 2026-09-22 it took three of five attempts here, with
   and without these modules; it usually passes on the next try, and how often other people
   meet it is one of the things worth counting.
4. **The hub shows a table and fixtures for your league.** Look at the date on the hub
   first. If the season opened in **August**, your league's table and your next fixtures
   should be there right away. If it opened in **January** — which is what happens when
   your club's league is one the game does not list by itself — the hub is empty at first,
   and that is expected: the game registers such leagues on its first registration day of
   the year, about two weeks in, and dates their season from August. Use *Forward Time* to
   move on; after the registration day your league appears in League Info with a full
   fixture list, and the table fills from August. **Report which of the two you got**, with
   the league you picked. (Before 2026-09-22 the January case never recovered: the league
   stayed without matches for the whole year. That is what `fl26join.dll` fixes.)
5. **Every added league has fixtures, not just yours.** Once past the registration day,
   open Competition Info / League Info for each of the six leagues. Each should state its
   fixture count ("38 Home & Away Fixtures" for twenty clubs) and show rounds with dates.
   Then open `SiderAddons\fl26join.log`: you should find one line
   `register_all 1: game gave N ids [...], we appended 39 -> ...` (it presents all 39 listed
   ids; the 33 that do not exist in a six-league world are turned away with `no-record`,
   which is expected) and, for each of your six ids, a line `door(ID) -> YES  ours flag on
   kind 1 clubs 20`. A `door(ID) -> no` for one of your six, or a league with no fixtures
   while the log says YES, is exactly the report we want — attach the log.
6. **The fixture list is complete.** Your league should show a full home-and-away season
   (38 rounds for twenty clubs). A league with no fixtures at all is the rulebook-id
   problem from step 6c.
7. **A save and a load.** Save from `System → Save`, quit to the main menu, load it back.
   The squad, the table and the fixture list should all come back as they were.
8. **A season rollover.** Play or skip to the end of the season and let it roll into the
   next. Then look at your league table: it must start again from zero. A table showing
   something like 76 matches played and 130 points is the symptom `fl26hdr127.lua` exists to
   cure, and seeing it means that module did not apply — check the log. Whether the added
   leagues enter the *second* season the same way has **not** been measured here yet; if you
   get this far, what League Info shows for them in the new season is a finding either way.

## 10. Optional: the experimental modules

Only after steps 1-9 have gone through once. `sider\experimental\` holds fourteen modules that
do more and have only been run on our test world — a career that starts in August,
promotion and relegation through deeper pyramids, the Select Team list (three separate
faults in it), 64 menu regions, a league rank deep enough for five divisions, and 192
competitions instead of 127. Each is described, with the order they need and the two slot
lists you must fill in from your own world, in
[sider/experimental/README.md](../sider/experimental/README.md).

Add **one at a time**, start the game, read the log, and give it one season before adding
the next. `fl26hdr192.lua` replaces `fl26hdr127.lua` — never run both, and keep
`fl26joindll.lua` before it. These are the modules where a second tester is worth most:
everything in that folder has been verified against the executable and watched in the
menus, and none of it has survived a season yet. [T8 in the testing guide](testing-guide.md)
says what to look at.

---

## Reporting

Open an issue here, or reply wherever you found this. What makes a report usable:

1. **which step** you were on, and what you expected against what happened;
2. **`SiderAddons\sider.log`** — all of it, attached rather than pasted if it is long;
3. **`SiderAddons\fl26join.log`** for anything about leagues, fixtures or the season's start;
4. **the `mkworld.py` output** for the world you built (league count, club count, ids);
5. **your exe size and hash** from step 1;
6. for a crash: whether it reproduced when you did it again, and the Windows Event Viewer
   entry (*Windows Logs → Application*, the `Application Error` for `FL_2026.exe`) — the
   fault offset in it is what makes a crash findable;
7. anything else in `SiderAddons\modules\` or `livecpk\`, if this is not a stock install.

The [testing guide](testing-guide.md) lists the tests worth running once this walkthrough
is through, and what each one should show.

## Getting back to normal

Delete the ten `lua.module` lines (or the files), and comment out your `cpk.root` line.
Nothing in the game's own files was ever written to, so that is the whole of it — but saves
made while the beta was installed will not load without it. Restore the backup from before
you started.
