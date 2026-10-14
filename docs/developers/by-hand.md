# Build it by hand, with Python

> **Easier way:** [FL26 Mod Studio](../../guides/en/mod-studio-guide.md) ([other languages](../../guides/README.md)) does
> all of this from one window -- install, build leagues, edit players, switch mods on and
> off. Start with [Install a ready pack](../../guides/en/install-a-pack.md) or
> [Make your own leagues and packs](../../guides/en/make-your-own-leagues.md). This page is the manual route, and what the
> program does underneath.

One page, every step, in order. It answers the three questions people ask most:

1. **How do I install this?** → [Part A](#part-a-install-the-mod)
2. **How do I get new leagues, for example a league in Asia?** → [Part B](#part-b-add-new-leagues) and [Part C](#part-c-put-a-league-in-a-particular-country-for-example-in-asia)
3. **How do I get the new Champions League format with a real schedule?** → [Part D](#part-d-the-new-champions-league-format-2024-with-a-real-schedule)

Much of what this page says works was found broken first by testers, above all
**vmardonesdev**. Who did what: [The people who made this better](../../README.md#the-people-who-made-this-better).

Then there is a list of [things to watch out for](#part-e-things-to-watch-out-for),
a [table of problems and fixes](#part-f-if-something-goes-wrong),
[how to ask for help](#part-h-asking-for-help) so that someone can actually help, and at the
end [every world-building option](#part-i-every-world-building-option) for bigger and deeper
worlds, crests and kits.

Every command on this page was run on a clean copy of the game tables before it was
written down, and each step says **what you should see**. If you see something else, stop
at that step. Do not carry on and hope: everything after a failed step builds on it.

Do Part A first, always. Parts B, C and D are separate: you can do only B, only D, or all
of them. The order in which they are written is the order that works.

---

## Before you start: words used on this page

| word | what it is |
|---|---|
| **game folder** | the folder with `FL_2026.exe` in it. This page writes it as `C:\Football Life 2026`. **Yours is probably somewhere else. Use your own path every time you see that one.** This is the most common mistake of all. |
| **Sider** | the program that Football Life starts together with the game. It loads mods. It lives in the `SiderAddons` folder inside the game folder. |
| **`sider.ini`** | Sider's settings file, `SiderAddons\sider.ini`. You edit it with Notepad. |
| **`sider.log`** | the file Sider writes every time the game starts, `SiderAddons\sider.log`. It tells you whether our modules worked. |
| **module** | a `.lua` file in `SiderAddons\modules\`, switched on by a line `lua.module = "name.lua"` in `sider.ini`. Two of ours also come with a `.dll` of the same name. |
| **world** | a folder under `SiderAddons\livecpk\` that holds the new leagues and clubs. You build it on your own PC from your own game (Part B). Nothing from the game is ever downloaded from here. Sider reads it because of a `cpk.root = ...` line in `sider.ini`. |
| **PowerShell** | the window where you type the commands on this page. Windows key, type `powershell`, Enter. |
| **regulation id** | a number every competition has inside the game. You never have to choose one, but some steps ask you to compare the numbers the tools print. |
| **region** | the country a competition is listed under in the menus (England, Japan, Brazil ...). |

---

## Part A. Install the mod

About 15 minutes. At the end the game has more room for clubs and leagues, and plays
exactly as before. The new leagues come in Part B.

### A1. What you need

- **Football Life 2026** with the Sider it comes with (the `SiderAddons` folder next to
  `FL_2026.exe`). Nothing else to install for Sider.
- **Windows.** Nothing here has been run on anything else.
- **Python 3.10 or newer** (step A4). Only needed for Parts B, C and D, but install it now.
- **No other mod that replaces the game's database tables** (squad packs, league packs,
  option files that ship `common\etc\pesdb\*.bin`). If you have one, see
  [E3](#e3-other-mods-that-change-the-database).

### A2. Show file extensions in Windows

Windows hides the end of file names by default, and then `fl26caps.lua` looks the same as
`fl26caps.lua.txt`. Open any folder, click **View** at the top → **Show** → tick **File name
extensions** (Windows 10: **View** tab → tick **File name extensions**).

### A3. Back up

Copy these two to a folder of your own, for example `Desktop\FL26 backup`:

1. The folder `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`
   (your Master League careers and your Edit data).
2. The file `C:\Football Life 2026\SiderAddons\sider.ini`.

With these two copies you can always go back to exactly how your game was
([Part G](#part-g-remove-it-and-go-back)).

### A4. Install Python

1. Go to https://www.python.org/downloads/ and click **Download Python**.
2. Run the installer. **On the first screen tick "Add python.exe to PATH"** (at the bottom).
   Then **Install Now**.
3. Close PowerShell if it is open, and open a new one (Windows key, `powershell`, Enter).
4. Type `python --version` and press Enter.

**You should see** `Python 3.12.x` or similar (anything from 3.10 up).
If you see `'python' is not recognized`, the box in point 2 was not ticked: run the installer
again, choose **Modify**, tick the PATH option, then open a new PowerShell.

> **How to paste into PowerShell:** copy the line from this page, right-click inside the
> PowerShell window, press Enter. One line at a time. A path with spaces in it must stay
> inside its `"quotes"`.

### A5. Download this project

1. On the GitHub page, green **Code** button → **Download ZIP**.
2. Right-click the ZIP → **Extract All...** → extract to `C:\fl26`.
3. Open `C:\fl26`. **You should see** the folders `docs`, `patches`, `sider` and `tools`
   directly inside it. If there is one more folder in between (for example
   `C:\fl26\FootballLife-new-leagues-main\sider`), move everything in that inner folder up one
   level, into `C:\fl26`.

Do **not** put this folder inside the game folder. Every command on this page assumes
`C:\fl26`; if you use another place, change it everywhere.

### A6. Check your game version

In PowerShell (your own game path):

```powershell
(Get-Item "C:\Football Life 2026\FL_2026.exe").Length
```

**You should see** `458910720`. Football Life 2026 v2.0 (file version `26.0.0.0`) and v2.2
(`26.2.0.3`) both have this size and both are known to work.

If the number is different, stop. The modules will switch themselves off on that version
(nothing breaks, they just do nothing). Open an issue with the number.

To check the exact build too:

```powershell
(Get-FileHash "C:\Football Life 2026\FL_2026.exe" -Algorithm SHA256).Hash
```

v2.0 gives `7C27ECB303B71331E36F9CCD8AC879F0F0D8C56C754BD4D0D2E9C8353464F847` (the build the
modules were made against); v2.2 (reported by a tester, all patches applied) gives
`9EE0C30651E5E3C37E3D308FB8224F5FEA135CD8E929DEE2CDDCA6E041836281`. A different hash does not
by itself mean the modules will refuse; `sider.log` tells you (A9). Everything is byte-exact:
a module that finds other bytes logs `MISMATCH` and `ABORTED` and changes nothing.

### A7. Copy the twelve files

From `C:\fl26\sider` copy these **12 files** into `C:\Football Life 2026\SiderAddons\modules\`:

```
fl26caps.lua          fl26nullguard.lua     fl26nullguard2.lua    fl26nullguard4.lua
fl26nullguard5.lua    fl26nullguard7.lua    fl26nullguard8.lua    fl26nullguard9.lua
fl26nullguard10.lua   fl26joindll.lua       fl26join.dll          fl26hdr127.lua
```

- **Not** `fl26caps.template.lua`. **Not** the `experimental` folder (that is for Part D and
  later).
- If Windows asks whether to replace files, you had an older version: say **yes**.
- If you have an `fl26nullguard3.lua` in `modules` from an older download, delete it.
- If your antivirus complains about `fl26join.dll`: it is built from the C source in
  `tools\native\`, and [tools/native/README.md](../../tools/native/README.md) has its checksum
  and how to build it yourself. If the antivirus removes it, the log in step A9 says
  `LoadLibraryA failed`.

**You should see** all 12 in the `modules` folder, among the files that were already there.

What they are: `fl26caps.lua` is the patch set (bigger tables), the eight `fl26nullguard`
files are crash guards, `fl26joindll.lua` gets every added league into the season and loads
`fl26join.dll` from the same folder (the two must sit next to each other), and
`fl26hdr127.lua` makes room for 127 competitions in a season.

> **Mod Studio installs these as bundles.** Since 0.2.0 it puts the eight `fl26nullguard` files
> in as one `fl26guards.lua`, and `fl26superguard`, `fl26resultsguard`, `fl26ctlguard` and
> `fl26kitguard` as `fl26lateguards.lua` (built by `tools/lbpack.py` from the single files,
> which stay the ones to read and change). Use either the single files or the bundles, never
> both: Mod Studio's Build switches the single lines off.

### A8. Switch them on in sider.ini

1. Open `C:\Football Life 2026\SiderAddons\sider.ini` with **Notepad** (right-click → Open
   with → Notepad).
2. `Ctrl+F`, search for `lua.module`. The cursor jumps to the **first** line that starts
   with `lua.module =`.
3. Click at the very start of that line and paste these **11 lines above it**, exactly like
   this, in this order:

   ```ini
   lua.module = "fl26caps.lua"
   lua.module = "fl26nullguard.lua"
   lua.module = "fl26nullguard2.lua"
   lua.module = "fl26nullguard4.lua"
   lua.module = "fl26nullguard5.lua"
   lua.module = "fl26nullguard7.lua"
   lua.module = "fl26nullguard8.lua"
   lua.module = "fl26nullguard9.lua"
   lua.module = "fl26nullguard10.lua"
   lua.module = "fl26joindll.lua"
   lua.module = "fl26hdr127.lua"
   ```

   Eleven lines for twelve files: `fl26join.dll` has no line of its own, `fl26joindll.lua`
   loads it. **The order matters**: `fl26caps.lua` first, `fl26hdr127.lua` last. The guards
   write small trampolines into fixed spare bytes of the code section and claim them in this
   order, and `fl26joindll.lua` goes after the guards; that is the order the set was verified in.
4. `Ctrl+F`, search for `luajit.ext.enabled`.
   - Found: make sure the line reads exactly `luajit.ext.enabled = 1`.
   - Not found: add the line `luajit.ext.enabled = 1` at the end of the file.
5. Save with **`Ctrl+S`** (not *Save As*, which can turn the file into `sider.ini.txt`).
   Close Notepad.

Rules for this file that catch people out:

- A line that starts with `#` or `;` is switched **off**.
- Never write a comment on the same line after a `lua.module` value. Put it on a line of its
  own.
- Each module is listed **once**.

### A9. First start: read sider.log

1. Start the game the way you always do. Wait for the main menu. Quit the game.
2. Open `C:\Football Life 2026\SiderAddons\sider.log` with Notepad. `Ctrl+F` → `fl26`.

**You should see** eleven lines like these (the numbers after `applied all` can differ):

```
[fl26caps.lua] fl26caps: applied all 3510 patches -- ...
[fl26nullguard.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard2.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard4.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard5.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard7.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard8.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard9.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard10.lua] fl26caps: applied all 2 patches -- ...
[fl26joindll.lua] fl26joindll: installed -- 39 added leagues will be registered ...
[fl26hdr127.lua] fl26caps: applied all 32 patches -- ...
```

The words that matter are **`applied all`** (nine times) and **`installed`** (once). Anything
else: [Part F](#part-f-if-something-goes-wrong).

The `fl26joindll` line is followed by one from the DLL itself,
`fl26join: hooks live (register_all ..., enter_season ..., builder ..., door ...), 39 competition ids`.
A new file `SiderAddons\fl26join.log` appears. That is normal: the module writes one line
there per decision it takes, it is short until a season is created, and it is the file to
attach when an added league has no fixtures.

`ABORTED` is safe (that module wrote nothing). `PARTIAL` is not: quit the game and report the
log.

### A10. Check that nothing changed

Play an exhibition match, and start a Master League career with any club and go a few days
forward. Everything should be exactly as before: the modules only made room, they added
nothing yet. If anything at all behaves differently at this point, that is a bug in the patch
set itself, and the most valuable report you can send.

> If the game crashes **while a Master League career is being created** (after you confirm
> the manager settings), start it again. That crash is in the game itself: it happens on an
> untouched Football Life too, often several times in a row. See
> [E6](#e6-crashes-that-are-not-this-mod).

**Part A is done.** Save the `sider.ini` you have now as a second backup
(`sider.ini.partA`): it is the known-good state to go back to.

---

## Part B. Add new leagues

About 15 minutes. At the end the game has six new leagues of 20 clubs each, with squads and
managers, next to everything the game already has. Nothing that exists is replaced.

The clubs are placeholders (`FL 0001`, `FL 0002` ..., players `FL P...`). You can rename them
afterwards ([B8](#b8-optional-names-crests-kits-players)).

### B1. Unpack your game's tables

The tools build the new leagues from your own game's data, so first it has to be unpacked.

1. Open `C:\Football Life 2026\download`. You will find files called `data_s2526.cpk`,
   `data_s2526a.cpk`, `data_s2526b.cpk`, `data_s2526c.cpk` (updates add more letters).
2. In PowerShell:

   ```powershell
   cd C:\fl26
   ```

3. Unpack **every** `data_s2526` file, **oldest first** (no letter, then `a`, `b`, `c` ...),
   all into the same folder. The newer one overwrites the older one. That is intended.

   ```powershell
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526.cpk"  C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526a.cpk" C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526b.cpk" C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526c.cpk" C:\fl26\pesdb
   ```

   If you have `data_s2526d.cpk` or later, run the same line for it, last. Each line prints a
   long list of file names. That is normal.

4. Open `C:\fl26\pesdb\common\etc\pesdb`. **You should see** (among others) `Team.bin`,
   `Coach.bin`, `Player.bin`, `PlayerAssignment.bin`, `Competition.bin`,
   `CompetitionEntry.bin` and `CompetitionRegulation.bin`.

> **Order matters.** If you unpack an older file after a newer one, the tables are old and
> the leagues are built on them. If in doubt, delete `C:\fl26\pesdb` and do point 3 again.
>
> **After every game update** (a new `data_s2526*.cpk` appears) do B1 again and build the
> world again (B2 onwards), into a **new** world folder.
>
> To see what an archive holds, `python tools\cpk.py <file>` lists it; the tables are the
> files under `common/etc/pesdb/`. If you run the tools often, set
> `$env:FL26_PESDB = "C:\fl26\pesdb\common\etc\pesdb"` and `$env:FL26_DIR` (your game folder)
> once per PowerShell window.

### B2. Build the leagues

Still in PowerShell, in `C:\fl26`. Each command is **one** line:

```powershell
python tools\mkworld.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --leagues 6 --clubs 20
```

**You should see** six lines like

```
  FL League 01     competition 130  regulation 11   20 clubs 71578-71597  region  16  division 1
```

and at the end `6 leagues, 120 clubs added; 863 clubs in all`.

**Check the `regulation` column now.** For six leagues it must read, top to bottom:
**`11, 49, 60, 61, 62, 74`**. If it reads anything else, stop and report it
([E4](#e4-the-regulation-ids)): those leagues would show in the menus and never play a match.

### B3. Give every club a squad

```powershell
python tools\mkplayers.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --per 30 --cap 61905
```

**You should see** at the end `120 clubs given 30 players each; ... players in all (cap 61905)`.

`--cap 61905` is not optional: it is the size of the player table with the mod installed.

### B4. Switch the world on

```powershell
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26World
```

**You should see** `active: ['cpk.root = ".\\livecpk\\_FL26World"']`.

This adds (or switches on) `cpk.root = ".\livecpk\_FL26World"` in `sider.ini`, above the other
`cpk.root` lines, and switches **off** every other world whose name starts with `_FL26`.
Only one of our worlds may be on at a time.

By hand instead: open `sider.ini`, find the first line that starts with `cpk.root`, paste
`cpk.root = ".\livecpk\_FL26World"` above it, and put a `#` in front of any other `_FL26...`
root line.

### B5. Look at it

Start the game.

1. **Kick Off** → pick a league → England. **You should see** `FL League 01` ... `FL League 06`
   with clubs `FL 0001`, `FL 0002` .... Play a match between two of them: 22 players on the
   pitch. New clubs wear a plain default kit until you give them kits ([B8](#b8-optional-names-crests-kits-players)).
2. **Master League** → **new** career → pick one of the `FL` clubs.
   - The season may open in **August** (table and fixtures are there at once) or in
     **January** (the hub is empty). In the January case use *Forward Time*: after about two
     weeks of game time the leagues are registered and get a full fixture list, and their
     season runs from August. That is expected.
   - After the registration day, every added league should show "38 Home & Away Fixtures" in
     League Info.
   - `SiderAddons\fl26join.log` should then hold one line
     `register_all 1: game gave N ids [...], we appended 39 -> ...` (all 39 listed ids are
     presented; the ones a six-league world does not have are turned away with `no-record`,
     which is expected) and, for each of your league ids, `door(ID) -> YES  ours flag on kind 1
     clubs 20`. A `door(ID) -> no` for one of yours, or a league with no fixtures while the log
     says YES, is exactly the report we want: attach the log.

### B6. Save, load, and a season change

Save (`System → Save`), quit to the main menu, load the save. Squad, table and fixtures must
come back as they were. At the end of the season the table must start again from zero; a
table that shows 76 matches played means `fl26hdr127.lua` did not apply (check `sider.log`).

### B7. Bigger worlds

- **More leagues:** `--leagues 39` is the most `mkworld.py` is set up for with the shipped
  files (39 leagues of 20 = 780 clubs, `--per 30` still fits). More than 39 from `mkworld.py`
  needs a regenerated patch set: [for-developers.md](for-developers.md). Mod Studio's Build
  goes further since 0.2.2: leagues past the game's free regulation ids take ids 255
  downward, which the shipped set dates, and our test world plays 86 new leagues.
- **Other league sizes** (`--clubs 18`, `--sizes 24,22,20,18`): the leagues are built fine,
  but only a league of **20 clubs playing twice** has its fixture dates without extra help.
  Any other size needs `fl26swiss.dll` from Part D for its dates, or it ends early or runs
  out of dates. Stay at 20 unless you also do Part D.
- **Divisions, promotion and relegation:** [Part I](#divisions-and-why-they-matter-more-than-they-look).
- The full list of options: [Part I](#part-i-every-world-building-option).

### B8. Optional: names, crests, kits, players

- **League and club names for all at once**: `mkworld.py` takes `--league-name "My League %02d"`
  and `--club-name "My Club %04d"`.
- **One club at a time, and managers:** `tools\rename.py`, see
  [faq.md](../faq.md#how-do-i-rename-the-new-clubs).
- **One league's own name:** see [C4](#c4-give-the-league-its-own-name).
- **Players:** `tools\playereditor.py` (a window) or `tools\playeredit.py` (Excel), see
  [faq.md](../faq.md#how-do-i-edit-the-players-of-the-new-clubs-if-not-in-edit-mode).
- **Crests and kits:** [Part I](#crests-and-kits-if-you-want-them-to-look-like-sides).

After any of these: move the Edit save aside ([E7](#e7-the-edit-save-shows-old-names)) and
start a **new** career. A career that already started keeps its own copy of the clubs.

---

## Part C. Put a league in a particular country (for example in Asia)

In this game a league does not belong to a continent. It belongs to a **region**, which is
the country it is listed under in the menus. "A league in Asia" therefore means: a new league
listed under one of the Asian countries the game has — **Japan**, **China** or **Saudi
Arabia** — or under a region of its own.

### C1. Pick the number

`mkworld.py` takes the region as a number, **eight times the region id**. Use the right-hand
column:

| country (region id) | type this | | country (region id) | type this |
|---|---|---|---|---|
| England (2) | `16` | | Brazil (16) | `128` |
| France (3) | `24` | | Argentina (17) | `136` |
| Spain (4) | `32` | | Chile (18) | `144` |
| Italy (5) | `40` | | Colombia (19) | `152` |
| Portugal (6) | `48` | | **China (21)** | **`168`** |
| Netherlands (7) | `56` | | Germany (22) | `176` |
| Belgium (8) | `64` | | USA (23) | `184` |
| Russia (9) | `72` | | **Japan (24)** | **`192`** |
| Greece (10) | `80` | | Turkey (27) | `216` |
| Denmark (12) | `96` | | **Saudi Arabia (28)** | **`224`** |
| Scotland (15) | `120` | | *free: 11, 13, 14, 20* | `88`, `104`, `112`, `160` |

These are read from the game's own competition table (for example the J1 League is stored
with `192`, the Saudi league with `224`). The four free regions are countries no shipped
competition uses; a league there works, but the menu heading over it is blank or borrowed
from another country. Regions above 28 need `sider\experimental\fl26reg128.lua` and are not
covered here.

**Do not use** 8 (inter-club), 200 (international) or 208 (event): those are groupings, not
countries.

### C2. Build it

Do B1 first if you have not. Then, instead of the B2 line (or into a **new** world folder if
you already have one):

**One new league under Japan and nothing else:**

```powershell
python tools\mkworld.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26Asia" --leagues 1 --clubs 20 --region 192
```

**Six leagues under England and a seventh under Japan:** `--regions` takes one number per
league, in order:

```powershell
python tools\mkworld.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26Asia" --leagues 7 --clubs 20 --regions 16,16,16,16,16,16,192
```

**You should see** the `region` column print the numbers you gave (`region 192` for the
Japanese one) and the regulation column `11, 49, 60, 61, 62, 74, 76` (for seven leagues).

Then B3 (squads) and B4 (switch it on) with `_FL26Asia` instead of `_FL26World`:

```powershell
python tools\mkplayers.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26Asia" --per 30 --cap 61905
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26Asia
```

### C3. What you should see, and what is not known yet

- **Kick Off:** the new league is listed under the country you picked, next to that country's
  own league.
- **Its fixture dates** follow the country: under Japan, China, Saudi Arabia and the other
  calendar-year countries it plays **February to December** like their own leagues
  (`fl26join.dll` and `fl26swiss`, GitHub issue #27); elsewhere **August to May**. A new
  country of its own plays August to May here; Mod Studio 0.1.4 can give a new country
  February to December instead (the *Season* field, a `season <region> 1` line in the world
  file).
- **Measured 2026-09-29** with a second division under the Saudi Pro League: the league joins
  its season in February, plays all its rounds by December, the July season change leaves it
  alone and the New Year closes it without a crash. Promotion and relegation with the division
  above at New Year work since the modules of Mod Studio 0.1.3.1 (`fl26join.dll`): measured
  with the same Saudi second division, which went up and down at New Year and started its next
  year. If you try it elsewhere, a short report is very welcome
  ([Part H](#part-h-asking-for-help)).
- **Continental places:** a league built with the scripts in this part gets **none** in the
  AFC Champions League or any other continental cup; the game fills those from its own entry
  lists. Mod Studio gives a new league places (the League window's *Europe* field, written as
  `uefa` lines of the world file) and builds the continental cups the game does not have.

### C4. Give the league its own name

`tools\mksizes.py` can rename one league without changing anything else. Make a text file
`C:\fl26\names.json` with Notepad (the number is the league's **regulation id** from the
mkworld output; `clubs` and `legs` must stay 20 and 2):

```json
{ "76": { "clubs": 20, "legs": 2, "name": "Asia Example League" } }
```

and write a renamed copy of the world into a new folder, then switch that one on:

```powershell
python tools\mksizes.py --src "C:\Football Life 2026\SiderAddons\livecpk\_FL26Asia" --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26AsiaNamed" --plan C:\fl26\names.json
python tools\siderroot.py _FL26AsiaNamed
```

**You should see** `reg  76  Asia Example League        20 clubs x 2 = 38 rounds`.
`mksizes.py` never overwrites: the `--out` folder must not exist yet.

---

## Part D. The new Champions League format (2024), with a real schedule

What you get: the **Champions League** and the **Europa League** each play one league phase
of 36 clubs (8 matches per club against 8 different opponents, two from each pot), a new
**Conference League** does the same with 36 clubs and 6 matches each, then a play-off for
places 9-24, then a fixed bracket from the round of 16 to the final. The matches are put on
**UEFA's real calendar** by the module, not on the old group-stage dates.

This part uses **experimental** modules. They were measured through two whole seasons on our
own test world (39 added leagues, a career with an added club, 2026-09-24/25). **Not measured
yet:** a career with a shipped club (Real Madrid, say) as your team, and a world with no added
leagues (D3, route 1). Both are built with exactly the same tools and ids as the measured
world, so they are expected to work; a report either way helps.

### D1. Before you start

- Part A done and `sider.log` clean.
- A **new** Master League career is required. A career started before this part will not
  get the new format.
- Save often while you play (every few game weeks). The game has crashes of its own
  ([E6](#e6-crashes-that-are-not-this-mod)).

### D2. Copy the modules and switch them on

From `C:\fl26\sider\experimental` copy these **five** files into
`C:\Football Life 2026\SiderAddons\modules\`:

```
fl26hdr192.lua    fl26superguard.lua    fl26resultsguard.lua    fl26swiss.lua    fl26swiss.dll
```

In `sider.ini`:

1. Find `lua.module = "fl26hdr127.lua"` and change it to `lua.module = "fl26hdr192.lua"`.
   **Never have both.** (`fl26hdr192.lua` makes room for 192 competitions instead of 127;
   the new format was measured with it. Changing between the two means a new career.)
2. Directly **below** that line add:

   ```ini
   lua.module = "fl26superguard.lua"
   lua.module = "fl26resultsguard.lua"
   lua.module = "fl26swiss.lua"
   ```

So our block now reads, in this order:

```ini
lua.module = "fl26caps.lua"
lua.module = "fl26nullguard.lua"
lua.module = "fl26nullguard2.lua"
lua.module = "fl26nullguard4.lua"
lua.module = "fl26nullguard5.lua"
lua.module = "fl26nullguard7.lua"
lua.module = "fl26nullguard8.lua"
lua.module = "fl26nullguard9.lua"
lua.module = "fl26nullguard10.lua"
lua.module = "fl26joindll.lua"
lua.module = "fl26hdr192.lua"
lua.module = "fl26superguard.lua"
lua.module = "fl26resultsguard.lua"
lua.module = "fl26swiss.lua"
```

What the two guards are for: `fl26superguard.lua` stops a crash when the Super Cup cannot
find its clubs; `fl26resultsguard.lua` stops a crash of the results screen on the play-off
day in February (issue #9). Both were needed in our runs.

### D3. Build the European world

The tools change the Champions League and Europa League **in your world folder only** and add
the Conference League. The game's own files are never touched; switching the world off
undoes all of it.

Each tool writes a **new** folder and refuses to overwrite one, so the in-between steps go to
`C:\fl26\build`. **If you run this part again, delete `C:\fl26\build` first.**

Pick **one** of the two routes.

#### Route 1: the new format with the game's own leagues only (no new leagues)

Mod Studio 0.1.4 does this in one step: **Only the new European cups...** on the Build page.
The commands below are the same thing by hand.

```powershell
cd C:\fl26
python tools\mkreshape.py --base C:\fl26\pesdb\common\etc\pesdb --out C:\fl26\build\eu1 --reshape UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:- --reshape UEFA_EUROPE_LEAGUE:1:groups:36:1:-
python tools\mkuecl.py   --src C:\fl26\build\eu1 --out C:\fl26\build\eu2
python tools\mkeuropo.py --src C:\fl26\build\eu2 --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26Euro"
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26Euro
```

(Needs B1 done, for `C:\fl26\pesdb`.)

#### Route 2: the new format on top of the world you built in Part B or C

Here the world folder is copied first, because `mkreshape.py` only writes the three
competition tables. Replace `_FL26World` with your world's folder name if it is different:

```powershell
cd C:\fl26
Copy-Item -Recurse "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" C:\fl26\build\eu1
python tools\mkreshape.py --base C:\fl26\build\eu1\common\etc\pesdb --out C:\fl26\build\eu1 --reshape UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:- --reshape UEFA_EUROPE_LEAGUE:1:groups:36:1:-
python tools\mkuecl.py   --src C:\fl26\build\eu1 --out C:\fl26\build\eu2
python tools\mkeuropo.py --src C:\fl26\build\eu2 --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26WorldEuro"
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26WorldEuro
```

#### What each tool must print (both routes)

| tool | the lines that must be there |
|---|---|
| `mkreshape.py` | `replica 1027 kept: 36 clubs` and `replica 1029 kept: 36 clubs` |
| `mkuecl.py` | `regulation    5 ->  186` and `regulation    6 ->  187`, then `36 entrants`, then a line starting `local UECL = {` |
| `mkeuropo.py` | `competition   3: play-off 188, ...` and `competition ...: play-off 189, ...`, then `18 regulation rows added` |

If a number differs (a `186`, `187`, `188`, `189`, `1027` or `1029` that is not there),
stop and report it with the whole output: the module is set up for exactly these ids.

`mkuecl.py` may print a line that starts `calendars are the source's`. With `fl26swiss.dll`
installed that line does not apply; ignore it.

### D4. Check the Conference League list

Open `C:\Football Life 2026\SiderAddons\modules\fl26swiss.lua` in Notepad and find the line
`local UECL = {`. Compare it with the `local UECL = { ... }` line `mkuecl.py` printed.

- **The same numbers:** nothing to do. (On Football Life 2026 with its current data packs
  they are the same, in both routes; we checked.)
- **Different:** replace the whole `local UECL = { ... }` block in `fl26swiss.lua` (it runs
  over three lines, up to the closing `}`) with the line `mkuecl.py` printed, and save.

Do **not** change `local REGS = { 1027, 1029, 1210 }`. Those are the ids from D3.

### D5. Start the game and check sider.log

**You should see**, besides the lines from A9 (with `fl26hdr192.lua` instead of
`fl26hdr127.lua`):

```
[fl26superguard.lua] ... applied all ...
[fl26resultsguard.lua] ... applied all ...
[fl26swiss.lua] fl26swiss: live -- 36-club league phase for regulation 1027, 1029, 1210; 8 opponents each over 16 matchdays (F8 = report)
```

and, among the lines after it, `knockout item guard live`, `group stage item live` and
`play-off names live`.

`fl26swiss: install FAILED (status ...)` means the module found a different game build and
changed nothing. `LoadLibraryA failed` means `fl26swiss.dll` is not in `modules`.

### D6. Play and check

Start a **new** Master League career.

- **Autumn:** Database → Competition Info → Champions League → *Group stage* shows **one
  table of 36 clubs**, the same for the Europa League and the Conference League. Every club
  plays 8 matches (6 in the Conference League). A Conference League table where every club
  has played 6 is **finished**, not stuck.
- **February:** the play-off for places 9-24. In Competition Info the item is called
  *Play-offs*; it stays grey until that play-off is drawn, then lists the ties.
- **From March:** round of 16, quarter-finals, semi-finals, final, in a bracket fixed in
  advance. In `sider.log` you may see `quarter-finals put back in bracket order`: that is
  the module undoing the game's random quarter-final draw. The *Knockout Phase* item appears
  once the knockout starts.
- **Second season:** the three competitions are filled from the previous season's **final
  league tables**, 36 + 36 + 36 clubs, by a UEFA-style access list (champions of the big
  leagues first, and so on). In `sider.log`:
  `access -- 36/36/36 (108 positions from last season's tables, 0 from first-season order, 0 missing)`.
- **First season:** there are no final tables yet, so each league is ordered by **squad
  strength** (the eleven best players by their ratings) and the access list reads that
  order. In `sider.log`: `first season -- reg ... by squad strength` per league and
  `access -- 36/36/36 (0 positions from last season's tables, 108 from first-season order, 0 missing)`.
- **Your own first-season field (optional):** put a text file called `fl26swiss-first.txt`
  next to `fl26swiss.lua` in `modules`. A line naming a competition (`Champions League`,
  `Europa League`, `Conference League`) starts its section; after it, every number in brackets
  is a team id, in the order the clubs should go in. The rest of each line is ignored, so a
  list like this works as it is:

  ```
  Champions League
  Paris Saint-Germain (114)     Manchester City (173)     Real Madrid CF (109)
  Europa League
  AS Roma (125)                 SL Benfica (191)
  Conference League
  Ajax Amsterdam (116)
  ```

  In the first season of a career started in this session of the game these clubs go in
  first; ids the game does not have, and clubs listed twice, are left out, and the access
  list fills the places that remain. A season you load (or the second season of a career, if
  the game was restarted between June and the August draw) leaves the list out: from the
  second season the places decide. In `sider.log`: `first-season list from
  fl26swiss-first.txt: 36 / 36 / 36 team ids` at start-up, `a new career, built on day ...`
  when the career is made and `first-season list -- 36 / 36 / 36 clubs taken` at the draw.
  The idea and the first list came from vector360 on Evo-Web.
- **The same list from Mod Studio:** League builder -> **First-season European clubs** picks
  the clubs of the three league phases from a list of your new clubs and the game's (search by
  name, league or team id). Build writes them into the world file (`first 0|1|2 <team ids>`
  lines), and they take the place of `fl26swiss-first.txt` while that world is switched on.
  Up to 36 clubs per competition, no club in two; the rest are filled as above. A club of the
  game must play in a league that season. The request came from AlexRufolo.

Press **F8** in the game any time to write a short report of what the module did into
`sider.log`.

### D7. What is not right yet

- **Do not quit the game between the end of June and the end of August** (in-game dates) of
  a season. The final tables the next draw needs are kept in memory from the season's end
  until the August draw. If the game is restarted in between (also: loading a save), they are
  gone and the draw falls back to squad strength, as in a first season. Save in June, play on
  to September in one go.
- The **first-season** order is a guess from the squads, not a result: a strong club in a
  weak season still starts in the Champions League.
- **New leagues get no European places on this route.** The access list names only the game's
  own leagues; the places of countries that are missing are topped up from the big five.
  Giving your leagues places here means editing `ACCESS` in `tools\native\fl26swiss.c` and
  building the DLL again ([tools/native/README.md](../../tools/native/README.md)). Mod Studio
  writes them for you: the League window's *Europe* field becomes `uefa` lines of the world
  file, which replace the DLL's list.
- **Title holders.** The Champions League and Europa League winners play the next Champions
  League, the Conference League winner the next Europa League. They come first on the list. A
  holder that also finished high enough at home takes the holder's place, and the league place
  it leaves goes to another country (the big-five league with the fewest clubs in that
  competition), as at UEFA, not to the next club of its own league. While no holder is known
  (a first season), those places go to the next club of England, Spain and Italy.
- The Conference League play-off is drawn in December (the real draw is in late January) and
  played in February together with the Europa League's.
- The European dates do not check the league calendars. A club can have a league match and
  a European match on the same day; both are played, but the next-match screen shows one.
- The page heading in Competition Info says *Group stage - Matchday ...*. That is the game's
  own text.

More detail on all of it: [sider/experimental/README.md](../../sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).

---

## Part E. Things to watch out for

### E1. Start a new career after every change

A Master League career keeps its own copy of the clubs, leagues and competitions it was
created with. After you build or change a world, switch modules, or update the mod: start a
**new** career. An old career will not show the change, and may not load at all.

### E2. Saves belong to the mod version that made them

A save made with the mod contains more clubs than the plain game can read, and a save made
with one `fl26caps.lua` cannot be read by another. **Before you update, finish your career or
keep the old files.** Never delete or overwrite a save you care about; keep careers made with
the mod in separate slots from your normal ones. `fl26hdr127.lua` → `fl26hdr192.lua` also
needs a new career.

### E3. Other mods that change the database

The tools build the world from the tables you unpacked in B1. If another mod (a squad
update, a league pack, an option file) also puts its own `Competition.bin`,
`Team.bin` or similar into a `livecpk` root, the two fight, and whichever root is higher in
`sider.ini` wins entirely. Keep our world root **above** the others (`siderroot.py` does
that), and know that the other mod's changes to those tables are then not used. If you use a
mod manager that edits `sider.ini`, open `sider.ini` after it has run and check that our `lua.module` lines and our
`cpk.root` line are still there.

### E4. The regulation ids

Whether a new league ever plays a match depends on its regulation id: the fixture dates are
looked up by that id, and only these 39 are set up (plus 145, for older worlds):

```
11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121
138 139 140 143 144 190 146 170 171 173 174 176 178 179 180 181 182 183 184 185
```

`mkworld.py` hands them out in exactly this order on a normal install, so the first N leagues
you build get the first N ids. If yours differ, the leagues appear in the menus and never
play: report it with the mkworld output.

Two things are keyed by that id:

1. **The fixture dates** come from a small table inside `fl26caps.lua`. A league whose id is
   not in it is never scheduled. Covering another id needs a regenerated patch set
   ([for-developers.md](for-developers.md)).
2. **The entry into the season** is done by `fl26joindll.lua`, which lists the same ids near
   the top of the file (`local IDS = { ... }`) and presents each of them to the game on the
   first registration day. A league that is dated but not in that list is entered only if
   the game lists it by itself, which a league standing in a country of its own is not. If
   your ids differ, edit that list too: a plain text edit, no regeneration needed. Ids in the
   list that your world does not use are harmless; the log notes them as `no-record`.

The 25th league is on **190**. Worlds built before 25 September 2026 have it on **145**
instead; 145 stays covered everywhere, so those worlds keep working. It was moved because the
game's own J1 League relegates into 145, which sent Japanese clubs into that league. Why an id
decides this at all: [how-it-works.md](../research/how-it-works.md).

### E5. One world at a time

Only one `_FL26...` world root may be switched on. Two roots with different tables give a
mixture that nobody tested. `siderroot.py` switches the others off for you.

### E6. Crashes that are not this mod

The game crashes now and then **inside its own protected code**, mostly while a scene is
being set up: creating a career (right after the manager settings), loading a match, a new
season. On an untouched Football Life 2026 with no mods at all, we saw 10 of 12 career
creations crash at the manager settings, and the game without Sider crash in 4 of 8. With our
modules it is fewer, because one of the guards catches one of these crashes. What helps:
**try again, and save often.** The save is not damaged.

If you report a crash, the useful part is the **fault offset** from Windows: Event Viewer →
Windows Logs → Application → the *Application Error* for `FL_2026.exe`.

### E7. The Edit save shows old names

If you renamed clubs and still see the old names, the game is reading your old Edit save
instead of the world. Move `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000`
somewhere safe (do not just delete it if it holds edits you want), start the game, and let
Edit mode write a new one.

### E8. The 2,400-club and 792-matches-a-day walls

The club table holds **2,400 clubs** in total since 0.2.2 (the season generator stopped at
1,536 up to 0.2.1), and a calendar day holds **792 matches** since 0.2.0 (280 in the game as
shipped); what is past that is dropped without a word. Up to 39 leagues of 20 clubs is
well inside both; our 0.2.2 test world has 86 new leagues and 1,294 new clubs. Details and the ways around: [limits.md](../research/limits.md).

### E9. Other experimental modules

`sider\experimental\` holds more: every league in the Select Team list (with its country's flag,
filled in by `tools\mkflags.py`), 128 regions, a career that starts in August, promotion and relegation through a whole pyramid, Edit mode lists.
Several of them carry lists of **our** world's ids that you must change for yours. Read
[sider/experimental/README.md](../../sider/experimental/README.md) before adding any, and add them
**one at a time**.

---

## Part F. If something goes wrong

| what you see | what it means | what to do |
|---|---|---|
| `'python' is not recognized` | Python is not installed, or not on PATH | A4, point 2 and 3 |
| `can't open file ... tools\...` | PowerShell is not in the project folder | type `cd C:\fl26` first; check that `C:\fl26\tools` exists (A5) |
| `No such file or directory` with a `.cpk` or `.bin` | a path is wrong | check your game folder and the file names in `download` |
| `... exists -- pick a new name, worlds are not overwritten` | the `--out` folder is already there | use a new folder name, or delete the old folder first |
| `FL_2026.exe not found at C:\Football Life 2026\...` | the tool needs the game folder | `$env:FL26_DIR = "<your game folder>"` in the same PowerShell window, then run it again |
| A6 shows a different number | a different game version | the modules will not run on it; report the number |
| no `fl26` lines at all in `sider.log` | the module lines are not in `sider.ini`, or it was not saved, or it was saved as `sider.ini.txt` | A2 and A8 |
| `MISMATCH` then `ABORTED` | that module found a different game build and changed nothing | report the lines; the game runs without it |
| `WRITE FAILED` or `PARTIAL` | a module was half applied | quit the game and report `sider.log` |
| `fl26joindll: global ffi is nil` (or `fl26swiss: global ffi is nil`) | `luajit.ext.enabled = 1` is missing | A8, point 4 |
| `LoadLibraryA failed` | the `.dll` is not in `modules`, or the antivirus removed it | A7 / D2 |
| `install FAILED (status N)` | the DLL found different bytes in the game and installed nothing | report it with the number |
| the new leagues are not in Kick Off | the world is not switched on | B4; check the `cpk.root` line has no `#` in front |
| a new league has no fixtures | its regulation id is not one of the 39, or it was not registered | E4; attach `SiderAddons\fl26join.log` |
| league table shows 76 matches after a season | `fl26hdr127.lua` (or 192) did not apply | check `sider.log` |
| the Champions League still has groups of 4 | an old career, or the Euro world is not switched on | D3 last line; new career (E1) |
| `fl26swiss: ... this world has no regulation 188` (or 189) | `mkeuropo.py` was skipped | D3, run all three tools |
| old club names | the old Edit save is read | E7 |
| crash while a career is created | the game's own crash | try again (E6) |
| clubs of new leagues play in the Copa Libertadores / Club World Cup | issue #8 | the experimental `fl26clubs.lua` + `fl26clubs.dll` stop it for careers created after installing them; read its entry in [sider/experimental/README.md](../../sider/experimental/README.md) first (it has a slot list of its own) |

---

## Part G. Remove it and go back

1. Close the game.
2. Put the `sider.ini` from your backup (A3) back into `SiderAddons`. (Or delete our
   `lua.module` lines and put a `#` in front of our `cpk.root` line.)
3. Put your backup `save` folder back.

The game's own files were never changed, so that is all. You can leave the files in
`modules` and the world folders in `livecpk`; without the lines in `sider.ini` nothing reads
them. `luajit.ext.enabled` can stay as it is; Sider's own modules do not mind it. Careers
made with the mod will not load without it.

### Updating to a newer version of this mod

1. Read the [changelogs](../changelog/) and the notes below: they say which files changed and
   whether saves still load.
2. Download the ZIP again, replace the files in `modules` with the new ones (all of them,
   also the `.dll`s).
3. If the notes say a tool changed the way worlds are built, build the world again into a
   **new** folder (B2 onwards) and switch to it.
4. New career if the notes say so (E2).

What changed in the twelve files, newest first:

- **0.2.0: `fl26caps.lua` is new** (3519 patches): a calendar day holds 792 matches instead
  of 280. It changes the size of the tables a career is saved with, so **a career saved before
  0.2.0 does not load** (it stays on the loading screen). Start a new career after you replace
  the file. Replace `fl26join.dll` too (and `fl26chain.dll`, `fl26swiss.dll` if you use the
  experimental modules): they read the moved tables.
- **2026-09-30: `fl26nullguard10.lua` is new.** Add the file and its line after
  `fl26nullguard9.lua`. It stops an endless loop that could fill the memory in a
  February-December career. It changes no table, so saves still load.
- **2026-09-25: `fl26caps.lua` lost one patch** (2,760 -> 2,759): it handed one game function
  the end of the moved match table where that function wants the start of the calendar. The
  edit block kept its size, so saves still load.
- **2026-09-22: `fl26nullguard3.lua` is replaced by `fl26nullguard9.lua`**, which guards the
  same unchecked read of the schedule list on both paths that reach it. They patch
  overlapping bytes, so **delete `fl26nullguard3.lua` and its `sider.ini` line**; with both,
  whichever loads second logs `MISMATCH` and `ABORTED`. **`fl26joindll.lua` + `fl26join.dll`
  are new** the same day and need `luajit.ext.enabled = 1` (A8); saves still load.
- **Before 2026-09-17:** `fl26caps.lua` changed then and made the edit block bigger. A save is
  only loadable by the patch set that wrote it, so saves made with that earlier version do not
  load. The guards, `fl26joindll.lua` and `fl26hdr127.lua` only write small trampolines into
  spare code, and saves survive them.

---

## Part H. Asking for help

Open an issue on this GitHub page (**Issues** → **New issue**). Messages elsewhere are easy
to miss; an issue is where the answer is also useful to the next person. Put in:

1. **which step of this page** you were on, what you expected and what you saw instead;
2. the file **`SiderAddons\sider.log`** (attach the file, do not paste it);
3. for anything about leagues or fixtures, **`SiderAddons\fl26join.log`**;
4. the **number from A6**;
5. if you built a world: **the whole output** of `mkworld.py` (and of the Part D tools);
6. for a crash: whether it happened again when you tried again, and the **fault offset** from
   Event Viewer (E6);
7. any other mods you have in `modules` or `livecpk`.

A screenshot of a wrong menu says more than a description of it.

Other pages, for when you want to know more:

- [testing-guide.md](testing-guide.md) — the tests worth running once a world plays, and what each should show
- [sider/experimental/README.md](../../sider/experimental/README.md) — the experimental modules
- [known-issues.md](../known-issues.md) and [limits.md](../research/limits.md) — what is still wrong, and the hard numbers
- [faq.md](../faq.md) — Mod Studio questions (updating, crashes, cups, promotion, what to send); renaming, managers, Edit mode, editing players

---

## Part I. Every world-building option

The reference for `mkworld.py` and the tools around it. Parts B and C use the defaults; this
is for bigger, mixed or deeper worlds. The clubs are deliberately placeholders (`FL League 03`,
`FL 0042`, players `FL P17021`): naming and dressing them is ordinary Team.bin and kit editing
on top of the same files (B8).

### The options

`--out` is the livecpk root; put it under `SiderAddons\livecpk\` with a name that sorts to
the top, for example `_FL26World`.

| option | default | notes |
|---|---|---|
| `--leagues N` | 6 | how many new leagues |
| `--clubs M` | 20 | clubs per league |
| `--sizes A,B,C` | | different sizes, cycled over the run, e.g. `--sizes 24,22,20,18` (10–30 all work; above 30 the round list runs out). Sizes other than 20 need `fl26swiss` for their dates (B7) |
| `--region N` | 16 | which existing menu region the leagues appear under (16 = England's slot; see C1) |
| `--regions A,B,C` | | one region per league, dealt out in order |
| `--tiers A,B,C` | | the division of each league, cycled over the run (see below) |
| `--group-regions N` | | how many consecutive leagues share a region |
| `--league-name`, `--club-name` | | name patterns, e.g. `"My Club %04d"` |
| `--cid-from N` | 130 | first competition id; leave it |
| `--reg-from N` | 1 | first rulebook id, handed out from the free list; **leave it** (E4) |
| `--cap` (mkplayers) | 30001 | must be **61905** with this patch set (51729 up to 0.2.1); it is the player table size |
| `--per` (mkplayers) | 23 | players per club; the budget is 61,905 − 27,927 shipped = 33,978 players ≈ 1,132 squads of 30, so `--per 30` fits a 39-league world (Mod Studio's Build gives new clubs 22 since 0.2.2) |

`mkworld.py` prints what it did. **Keep that output**: it lists the competition and rulebook
ids it used, and both the check in E4 and any bug report need it.

```
competition ids 130, 131, 132, 133, 134, 135
regulation  ids 11, 49, 60, 61, 62, 74
  FL League 01     competition 130  regulation 11   20 clubs 71578-71597  region  16  division 1
  ...
  wrote Team.bin (863 records)
  wrote Coach.bin (1081 records, 120 new managers)

6 leagues, 120 clubs added; 863 clubs in all
```

(The summary lines show the first eight ids; the per-league lines always show every league's.)

### Sizes worth knowing

Our largest world built with `mkworld.py`: **39 leagues, 793 clubs**, built with
`--leagues 39` and sizes around 20; the world that has been played across four seasons is 39
leagues of exactly 20, 780 clubs. Since 0.2.2 the club table holds **2,400 clubs in all**
(up to 0.2.1, **1,536 clubs in total was a hard wall** in the season generator), and a
calendar day holds 792 match ids at most (280 before 0.2.0). Our 0.2.2 test world, built with
Mod Studio, plays 86 new leagues of 10 to 24 clubs, 1,294 new clubs; Build stops with a
message when regulation ids or club room run out. Start smaller. A world
of 6 leagues × 20 clubs is a fine first test; 12 leagues with `--sizes 24,22,20,18,16,14` is a
good second.

A world of 39 leagues of 10 to 24 clubs (some playing each other three or four times), with
the Champions League, Europa League and a Conference League in the 2024 format, needs the
experimental modules and the tools of Part D on top; the route, command by command, is in
[sider/experimental](../../sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).

### If you build many leagues: spread them over the week

A calendar day holds **792 matches** (280 before 0.2.0) and the scheduler drops the rest
without a word: no error, no log line, a league just plays one round fewer than it should.
Each new league is given a shift of 0 to 6 days so that they do not all want the same weekday,
and the shipped set already carries a spread measured on a 39-league world.

With 792 a day the shipped spread leaves plenty of room for 39 leagues; a much bigger world
(or a set built without the `-calendar` part, which keeps 280) needs its own.
`tools/dayplan.py` reads a running season out of the game, separates the shipped
competitions' load from each of your leagues', and prints the `--date-offsets` argument for
`patchset.py` that makes the busiest day as quiet as it can be:

```
python tools/dayplan.py --set <your set name>
python tools/dayplan.py --set <your set name> --demand   # after the first rollover
```

Then regenerate the set with what it printed ([for-developers.md](for-developers.md)) and
create the season again. Use `--demand` once a world has rolled over: walking the calendar
only counts the matches that were accepted, so a day that turned matches away still reads as
exactly its cap, while the match records show what was really wanted.

### Switching between worlds

To try a different world, build it into a different folder and switch the root line (B4). To
go back to the shipped game, comment the line out. **Move your Master League save aside
between worlds**: a save carries the club table of the world it was made in.

### Divisions, and why they matter more than they look

Every league these tools build is a copy of a first-division prototype, which means that by
default **all of your leagues are first divisions**. Two consequences, both measured:

* a first division in a region is offered European places by the engine, so your new clubs
  can turn up in the Champions League;
* the promotion resolver only looks for the league above when the lower league is division 2
  or 3, so three leagues linked as a pyramid but all left as division 1 will never promote
  or relegate anybody.

```powershell
python tools\mkworld.py --base $env:FL26_PESDB --out <root> --leagues 9 --tiers 1,2,3 --group-regions 3
```

`--tiers` cycles over the run, `--group-regions` says how many consecutive leagues share a
region, so the line above builds three three-division pyramids, each one inside its own
region, which is the shape the engine understands. The division *number* stops at three, but
a pyramid does not have to: see [limits.md](../research/limits.md), and `sider/experimental/fl26rank.lua`
below, which raises the number itself to seven.

The shipped game reads a region number below 29 and ignores anything higher, so that is the
ceiling unless `sider/experimental/fl26reg128.lua` is installed, which raises it to 128 (0.2.2;
it replaces `fl26reg64.lua`, which gave 64). Above
the shipped 24 a region has no heading of its own and borrows the previous country's name in
the menus; it still groups the leagues correctly. Four ids (11, 13, 14 and 20) have no heading
row at all and are otherwise free.

`tools\deepen.py` does the other version of this: it takes one of your leagues and puts it
**underneath an existing pyramid**, one division lower (France and Italy each ship two),
copying the parent's region and calendar shape and writing the promotion link both ways. Run
it again on the league it just made and you get a fourth division, and again for a fifth:

```
python tools\deepen.py --root <root> --league 60 --below 81   # your league becomes Ligue 3
python tools\deepen.py --root <root> --league 61 --below 60   # and this one Ligue 4
```

Anything below the third division promotes upwards out of the box but is never relegated
into, until you install `sider/experimental/fl26deep4.lua`: one verified byte that makes the
engine's second relegation gate accept a third division as well as a second. `deepen.py`
says so when it builds one.

There is a better version of that, also experimental. The rank a league carries is a
**two-bit** field, so D3, D4 and D5 all store the value 3 and nothing can tell them apart,
which is why the League Info panel shows a fourth division as its own lower league.
`sider/experimental/fl26rank.lua` widens the field to three bits and `fl26deeprank.lua`
replaces the one-byte gate with the real rule (read
[sider/experimental/README.md](../../sider/experimental/README.md) for the order; `fl26deep4.lua`
must be off). With `fl26rank.lua` installed, build the chain with `--deep-rank` so each child
gets its parent's rank plus one, and renumber a pyramid you built earlier with:

```
python tools\deepen.py --root <root> --retier 20,18,11        # name the TOP league of each chain
```

`deepen.py` is the one tool here that writes into a shipped competition's own record (the
parent's relegation pointer), in your livecpk copy of the table. Nothing is replaced, but
Ligue 2's bottom clubs now have somewhere to fall.

### Crests and kits, if you want them to look like sides

A new club has no crest and no kit of its own: in the game it shows no crest and wears the
engine's plain default kit. Two tools fix that, and neither touches a shipped file: both only
write files for ids no shipped file uses.

```powershell
python -m pip install pillow
python tools\mkcrests.py --team-bin <your root>\common\etc\pesdb\Team.bin --flags <your root>
python tools\mkkits.py   --team-bin <your root>\common\etc\pesdb\Team.bin --unipar <UniformParameter.bin> --textures <cpklist.txt> --root <your root> --archive
```

`mkcrests.py` draws a distinct two-tone crest per club and needs Pillow. `mkkits.py` lends
each club a shipped club's first, second, third and goalkeeper kit; it needs one more archive
out of the game (`uniform/team/UniformParameter.bin`) and a list of the kit textures the game
ships. Run it with no arguments to see where both come from.

The files are named the way the engine looks them up, which is not the team id as it stands.
The engine splits the id: the low bits are the number in the path and bits 14-16 pick a tag.
Ids 65536..81919 get the tag `_ACL_` and lose 65536, so club 72163's first kit is
`uniform/team/6627/6627_ACL_1st_realUni.bin`, the same form the game uses for its own AFC
clubs. A file named `72163_DEF_...` is never asked for, and the club plays in the default kit.
`mkkits.py` handles this for any id (`kit_key()` in the tool); if you write kit files by hand
for a new club, use the same rule.

None of this changes whether a season works. After it, move the Edit save aside (E7) and
start a new career.
