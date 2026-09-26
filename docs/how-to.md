# The complete how-to

One page, every step, in order. It answers the three questions people ask most:

1. **How do I install this?** → [Part A](#part-a-install-the-mod)
2. **How do I get new leagues, for example a league in Asia?** → [Part B](#part-b-add-new-leagues) and [Part C](#part-c-put-a-league-in-a-particular-country-for-example-in-asia)
3. **How do I get the new Champions League format with a real schedule?** → [Part D](#part-d-the-new-champions-league-format-2024-with-a-real-schedule)

Then there is a list of [things to watch out for](#part-e-things-to-watch-out-for),
a [table of problems and fixes](#part-f-if-something-goes-wrong), and
[how to ask for help](#part-h-asking-for-help) so that someone can actually help.

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

### A7. Copy the eleven files

From `C:\fl26\sider` copy these **11 files** into `C:\Football Life 2026\SiderAddons\modules\`:

```
fl26caps.lua          fl26nullguard.lua     fl26nullguard2.lua    fl26nullguard4.lua
fl26nullguard5.lua    fl26nullguard7.lua    fl26nullguard8.lua    fl26nullguard9.lua
fl26joindll.lua       fl26join.dll          fl26hdr127.lua
```

- **Not** `fl26caps.template.lua`. **Not** the `experimental` folder (that is for Part D and
  later).
- If Windows asks whether to replace files, you had an older version: say **yes**.
- If you have an `fl26nullguard3.lua` in `modules` from an older download, delete it.
- If your antivirus complains about `fl26join.dll`: it is built from the C source in
  `tools\native\`, and [tools/native/README.md](../tools/native/README.md) has its checksum
  and how to build it yourself. If the antivirus removes it, the log in step A9 says
  `LoadLibraryA failed`.

**You should see** all 11 in the `modules` folder, among the files that were already there.

### A8. Switch them on in sider.ini

1. Open `C:\Football Life 2026\SiderAddons\sider.ini` with **Notepad** (right-click → Open
   with → Notepad).
2. `Ctrl+F`, search for `lua.module`. The cursor jumps to the **first** line that starts
   with `lua.module =`.
3. Click at the very start of that line and paste these **10 lines above it**, exactly like
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
   lua.module = "fl26joindll.lua"
   lua.module = "fl26hdr127.lua"
   ```

   Ten lines for eleven files: `fl26join.dll` has no line of its own, `fl26joindll.lua`
   loads it. **The order matters**: `fl26caps.lua` first, `fl26hdr127.lua` last.
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

**You should see** ten lines like these (the numbers after `applied all` can differ):

```
[fl26caps.lua] fl26caps: applied all 2759 patches -- ...
[fl26nullguard.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard2.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard4.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard5.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard7.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard8.lua] fl26caps: applied all 2 patches -- ...
[fl26nullguard9.lua] fl26caps: applied all 2 patches -- ...
[fl26joindll.lua] fl26joindll: installed -- 39 added leagues will be registered ...
[fl26hdr127.lua] fl26caps: applied all 32 patches -- ...
```

The words that matter are **`applied all`** (nine times) and **`installed`** (once). Anything
else: [Part F](#part-f-if-something-goes-wrong).

A new file `SiderAddons\fl26join.log` appears. That is normal.

### A10. Check that nothing changed

Play an exhibition match, and start a Master League career with any club and go a few days
forward. Everything should be exactly as before: the modules only made room, they added
nothing yet.

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
python tools\mkplayers.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --per 30 --cap 51729
```

**You should see** at the end `120 clubs given 30 players each; ... players in all (cap 51729)`.

`--cap 51729` is not optional: it is the size of the player table with the mod installed.

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
   pitch, kits borrowed from the club each one was copied from.
2. **Master League** → **new** career → pick one of the `FL` clubs.
   - The season may open in **August** (table and fixtures are there at once) or in
     **January** (the hub is empty). In the January case use *Forward Time*: after about two
     weeks of game time the leagues are registered and get a full fixture list, and their
     season runs from August. That is expected.
   - After the registration day, every added league should show "38 Home & Away Fixtures" in
     League Info.

### B6. Save, load, and a season change

Save (`System → Save`), quit to the main menu, load the save. Squad, table and fixtures must
come back as they were. At the end of the season the table must start again from zero; a
table that shows 76 matches played means `fl26hdr127.lua` did not apply (check `sider.log`).

### B7. Bigger worlds

- **More leagues:** `--leagues 39` is the most the shipped files are set up for (39 leagues
  of 20 = 780 clubs, `--per 30` still fits). More than 39 needs a regenerated patch set:
  [for-developers.md](for-developers.md).
- **Other league sizes** (`--clubs 18`, `--sizes 24,22,20,18`): the leagues are built fine,
  but only a league of **20 clubs playing twice** has its fixture dates without extra help.
  Any other size needs `fl26swiss.dll` from Part D for its dates, or it ends early or runs
  out of dates. Stay at 20 unless you also do Part D.
- **Divisions, promotion and relegation:** [build-your-world.md](build-your-world.md#divisions-and-why-they-matter-more-than-they-look).
- The full list of options: [build-your-world.md](build-your-world.md).

### B8. Optional: names, crests, kits, players

- **League and club names for all at once**: `mkworld.py` takes `--league-name "My League %02d"`
  and `--club-name "My Club %04d"`.
- **One club at a time, and managers:** `tools\rename.py`, see
  [faq.md](faq.md#how-do-i-rename-the-new-clubs).
- **One league's own name:** see [C4](#c4-give-the-league-its-own-name).
- **Players:** `tools\playereditor.py` (a window) or `tools\playeredit.py` (Excel), see
  [beginners-guide.md](beginners-guide.md#optional-give-clubs-and-players-real-names).
- **Crests and kits:** [step-by-step.md, step 7](step-by-step.md#7-optional-give-the-clubs-their-own-crests-and-kits).

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
from another country. Regions above 28 need `sider\experimental\fl26reg64.lua` and are not
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
python tools\mkplayers.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26Asia" --per 30 --cap 51729
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26Asia
```

### C3. What you should see, and what is not known yet

- **Kick Off:** the new league is listed under the country you picked, next to that country's
  own league.
- **Its fixture dates** come from the league's regulation id, not from the country, so it
  plays an **August-to-May** season like a European league, even under Japan whose own
  league has a calendar-year season.
- **Not measured yet**, stated plainly: a Master League career *inside* a league placed
  under Japan, China or Saudi Arabia. Our test careers all used leagues under England or in
  regions of their own. What we expect, from how the game decides it: the career opens in
  **January**, the league is registered about two weeks later and plays from August (the
  January case of [B5](#b5-look-at-it)). If you try it, a short report of what happened is
  very welcome ([Part H](#part-h-asking-for-help)).
- **Continental places:** a new league gets **none** in the AFC Champions League or any other
  continental cup. The game fills those from its own entry lists.

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
  `access -- 36/36/36 (108 positions from last season's tables, 0 from list order, 0 missing)`.

Press **F8** in the game any time to write a short report of what the module did into
`sider.log`.

### D7. What is not right yet

- **Do not quit the game between the end of June and the end of August** (in-game dates) of
  a season. The final tables the next draw needs are kept in memory from the season's end
  until the August draw. If the game is restarted in between (also: loading a save), they are
  gone and the draw falls back to league order. Save in June, play on to September in one go.
- In the **first** season there are no final tables yet, so the field is the game's own
  entry list.
- **New leagues get no European places.** The access list names only the game's own
  leagues; the places of countries that are missing are topped up from the big five. Giving
  your leagues places means editing `ACCESS` in `tools\native\fl26swiss.c` and building the
  DLL again ([tools/native/README.md](../tools/native/README.md)).
- The Conference League play-off is drawn in December (the real draw is in late January) and
  played in February together with the Europa League's.
- The European dates do not check the league calendars. A club can have a league match and
  a European match on the same day; both are played, but the next-match screen shows one.
- The page heading in Competition Info says *Group stage - Matchday ...*. That is the game's
  own text.

More detail on all of it: [sider/experimental/README.md](../sider/experimental/README.md#the-european-format-and-league-sizes-fl26swiss).

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

### E8. The shipped 1,536-club and 280-matches-a-day walls

The season generator stops at **1,536 clubs** in total, and a calendar day holds **280
matches**; what is past that is dropped without a word. Up to 39 leagues of 20 clubs is
inside both. Details and the ways around: [limits.md](limits.md).

### E9. Other experimental modules

`sider\experimental\` holds more: every league in the Select Team list, 64 regions, a career
that starts in August, promotion and relegation through a whole pyramid, Edit mode lists.
Several of them carry lists of **our** world's ids that you must change for yours. Read
[sider/experimental/README.md](../sider/experimental/README.md) before adding any, and add them
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
| clubs of new leagues play in the Copa Libertadores / Club World Cup | issue #8 | the experimental `fl26clubs.lua` + `fl26clubs.dll` stop it for careers created after installing them; read its entry in [sider/experimental/README.md](../sider/experimental/README.md) first (it has a slot list of its own) |

---

## Part G. Remove it and go back

1. Close the game.
2. Put the `sider.ini` from your backup (A3) back into `SiderAddons`. (Or delete our
   `lua.module` lines and put a `#` in front of our `cpk.root` line.)
3. Put your backup `save` folder back.

The game's own files were never changed, so that is all. You can leave the files in
`modules` and the world folders in `livecpk`; without the lines in `sider.ini` nothing reads
them. Careers made with the mod will not load without it.

### Updating to a newer version of this mod

1. Read the top of [README.md](../README.md) and [install.md](install.md#2-copy-the-modules):
   it says which files changed and whether saves still load.
2. Download the ZIP again, replace the files in `modules` with the new ones (all of them,
   also the `.dll`s).
3. If the notes say a tool changed the way worlds are built, build the world again into a
   **new** folder (B2 onwards) and switch to it.
4. New career if the notes say so (E2).

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

- [beginners-guide.md](beginners-guide.md) — Parts A and B again, even slower
- [step-by-step.md](step-by-step.md) — the testing walkthrough, with what to report
- [build-your-world.md](build-your-world.md) — every world-building option
- [sider/experimental/README.md](../sider/experimental/README.md) — the experimental modules
- [known-issues.md](known-issues.md) and [limits.md](limits.md) — what is still wrong, and the hard numbers
- [faq.md](faq.md) — renaming, managers, Edit mode, editing players
