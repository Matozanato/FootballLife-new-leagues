# Beginner's guide: from nothing to playing the new leagues

This guide assumes you have never used Python, PowerShell or Sider modules. Do every step in
order and do not skip any. After each step it says **what you should see**. If you see
something else, stop there, read the table at the end ("If something goes wrong"), and ask
if it does not help.

It takes about 30 minutes. Most of that is waiting for the game to start.

**What you end up with:** six new leagues of 20 clubs each, added next to all the leagues the
game already has. Nothing that exists is replaced. You can play them in Kick Off and in
Master League.

---

## Step 0. Know where your game is

Find the folder that contains `FL_2026.exe`. In this guide it is written as

```
C:\Football Life 2026
```

If yours is somewhere else (for example `D:\Games\FL26`), **use your own path everywhere this
guide says `C:\Football Life 2026`.** That is the most common mistake.

## Step 1. Make a backup

Copy these two to a safe place, for example a folder on your desktop called `FL26 backup`:

1. The folder
   `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`
   (your Master League saves and your Edit data).
2. The file `C:\Football Life 2026\SiderAddons\sider.ini`.

With these two copies you can always get back to exactly how your game was. The last step of
this guide says how.

## Step 2. Install Python

Python runs the small programs that build the new leagues.

1. Go to https://www.python.org/downloads/ and click the big yellow **Download Python** button.
2. Run the installer. **On the first screen, tick the box "Add python.exe to PATH"** at the
   bottom. This is important. Then click **Install Now**.
3. When it finishes, close it.

**Check it:** press the Windows key, type `powershell`, press Enter. A blue or black window
opens. This is PowerShell, where you will type the commands in this guide. Type:

```powershell
python --version
```

and press Enter. **You should see** something like `Python 3.12.6`. Any version 3.10 or newer
is fine.

> **To paste into PowerShell:** copy the command here, then right-click inside the PowerShell
> window. Press Enter to run it. Run commands **one line at a time** unless the guide says
> otherwise.

## Step 3. Download this project

1. On the GitHub page of this project, click the green **Code** button, then
   **Download ZIP**.
2. Right-click the downloaded ZIP → **Extract All...** and extract it to `C:\fl26`.
3. Open `C:\fl26`. **You should see** folders called `docs`, `sider` and `tools` directly
   inside it. If you see one more folder in between (like
   `C:\fl26\FootballLife-new-leagues-main\docs`), move everything from that inner folder up
   into `C:\fl26`.

Do **not** put this folder inside the game folder.

## Step 4. Check that your game is the right version

The modules only work with one exact version of `FL_2026.exe`. In PowerShell type (with your
own game path):

```powershell
(Get-Item "C:\Football Life 2026\FL_2026.exe").Length
```

**You should see** `458910720`.

If you see a different number, stop here. Your game is a different version and the modules
will switch themselves off (nothing breaks, they just do nothing). Please open an issue on
GitHub with that number.

## Step 5. Copy the modules into the game

1. Open `C:\fl26\sider`.
2. Select these **11 files** (not the `experimental` folder):

   ```
   fl26caps.lua          fl26nullguard.lua     fl26nullguard2.lua    fl26nullguard4.lua
   fl26nullguard5.lua    fl26nullguard7.lua    fl26nullguard8.lua    fl26nullguard9.lua
   fl26joindll.lua       fl26join.dll          fl26hdr127.lua
   ```

   (`fl26caps.template.lua` is not one of them. Leave it.)
3. Copy them into `C:\Football Life 2026\SiderAddons\modules\`.

**You should see** all 11 files in that `modules` folder, among the files that were already
there.

## Step 6. Tell Sider to load them

1. Open `C:\Football Life 2026\SiderAddons\sider.ini` with **Notepad** (right-click →
   Open with → Notepad).
2. Press `Ctrl+F` and search for `lua.module`. The cursor jumps to the **first** line that
   starts with `lua.module =`.
3. Click at the very beginning of that line and paste these 10 lines **above it**, exactly
   like this, in this order:

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

4. Press `Ctrl+F` again and search for `luajit.ext.enabled`.
   - If you find it, make sure the line says `luajit.ext.enabled = 1`.
   - If it is not in the file, add the line `luajit.ext.enabled = 1` at the very end of the
     file.
5. Save (`Ctrl+S`) and close Notepad.

## Step 7. First start: check that the modules work

1. Start the game the way you always do. Wait for the main menu, then quit the game.
2. Open `C:\Football Life 2026\SiderAddons\sider.log` with Notepad.
3. Press `Ctrl+F` and search for `fl26`.

**You should see** lines like these (the numbers can differ):

```
[fl26caps.lua] fl26caps: applied all 2760 patches -- ...
[fl26nullguard.lua] fl26caps: applied all 2 patches -- ...
...
[fl26joindll.lua] fl26joindll: installed -- 39 added leagues will be registered ...
[fl26hdr127.lua] fl26caps: applied all 32 patches -- ...
```

The important words are **`applied all`** and **`installed`**. If you see `MISMATCH`,
`ABORTED`, `FAILED` or `ffi is nil`, look at the table at the end.

At this point the game has more room but no new leagues yet. It should play exactly like
before.

## Step 8. Copy the game's own tables out of its archives

The new leagues are built from your own game's data, so nothing from the game is ever
downloaded from here. First, those tables have to be unpacked.

1. Open `C:\Football Life 2026\download`. You will see files like `data_s2526.cpk`,
   `data_s2526a.cpk`, `data_s2526b.cpk`, `data_s2526c.cpk`. Newer updates add a new letter.
2. In PowerShell, go to the project folder:

   ```powershell
   cd C:\fl26
   ```

3. Unpack each of the `data_s2526` archives **from the oldest to the newest** into the same
   folder. The newer one overwrites the older one, and that is intended. For a game that has
   `data_s2526` to `data_s2526c`:

   ```powershell
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526.cpk"  C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526a.cpk" C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526b.cpk" C:\fl26\pesdb
   python tools\cpkx.py "C:\Football Life 2026\download\data_s2526c.cpk" C:\fl26\pesdb
   ```

   If you have a `data_s2526d.cpk` or later, do that one last, the same way. Each command
   prints a long list of file names. That is normal.

4. Open `C:\fl26\pesdb\common\etc\pesdb`. **You should see** `Team.bin`, `Player.bin`,
   `Competition.bin`, `CompetitionEntry.bin`, `CompetitionRegulation.bin` and
   `PlayerAssignment.bin` (and a few more).

## Step 9. Build the new leagues

In the same PowerShell window, run these two commands (each one is one long line):

```powershell
python tools\mkworld.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --leagues 6 --clubs 20
```

**You should see** six lines like
`FL League 01     competition 130  regulation 11   20 clubs ...` and at the end
`6 leagues, 120 clubs added`.

```powershell
python tools\mkplayers.py --base C:\fl26\pesdb\common\etc\pesdb --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --per 30 --cap 51729
```

**You should see** at the end `120 clubs given 30 players each`.

The folder `C:\Football Life 2026\SiderAddons\livecpk\_FL26World` now holds your new
leagues.

> The `regulation` numbers must be `11, 49, 60, 61, 62, 74`. On a normal install they are.
> If yours are different, the leagues will show up but never play a match: report it.

## Step 10. Switch the new leagues on

Run this (with your own game path in the first line):

```powershell
$env:FL26_DIR = "C:\Football Life 2026"
python tools\siderroot.py _FL26World
```

This adds the line `cpk.root = ".\livecpk\_FL26World"` to `sider.ini` in the right place.
**You should see** it print `_FL26World` as the active world.

(If you prefer to do it by hand: open `sider.ini`, find the first line that starts with
`cpk.root`, and paste `cpk.root = ".\livecpk\_FL26World"` above it.)

## Step 11. Play

Start the game.

1. **Kick Off:** choose a league, go to England. **You should see** `FL League 01` to
   `FL League 06`, with clubs named `FL 0001`, `FL 0002` and so on. Play a match between two
   of them.
2. **Master League:** start a new career and pick one of the `FL` clubs.
   - The season may start in **August** (the table and fixtures are there straight away) or
     in **January** (the hub is empty at first). If it is January, use *Forward Time*. After
     about two weeks of game time the league gets its full fixture list. That is expected.
   - If the game crashes while the season is being created, **just try again**. That crash
     also happens in the game without any of this installed, and it usually works on the
     second try.

That is it. You are playing the new leagues.

---

## Optional: give clubs and players real names

- **Rename clubs:** `tools\rename.py`. See [How do I rename the new clubs?](faq.md#how-do-i-rename-the-new-clubs)
- **Edit players in a window:** `tools\playereditor.py`. For the world from step 9:

  ```
  python tools\playereditor.py --root "C:\Football Life 2026\SiderAddons\livecpk\_FL26World"
  ```

  (Without `--root` it asks for the world folder: pick `_FL26World`, the folder that holds
  `common`.) **You should see** a window with the clubs on the left. Click a club, then a
  player; his fields are on the right in four tabs (Profile, Positions, Abilities, Skills).
  Change what you want and press **Apply**, then **Save**. The green rows are the starting
  eleven; **Up** and **Down** move the selected player, **New player** adds one to the club
  as a copy of the selected player. A value the game cannot store (Speed 150, say) is refused
  with a message and nothing is changed. The first Save keeps the originals as
  `Player.bin.bak` and `PlayerAssignment.bin.bak`.
- **Edit players in Excel instead:** `tools\playeredit.py`. It exports a club to a CSV
  file you open in Excel (every player on one line, every field in its own column: name,
  position, height, abilities, skills, shirt number...), and imports it back. For example,
  for the first club of the world from step 9:

  ```
  python tools\playeredit.py --root "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --export C:\fl26\club.csv --club "FL 0001"
  ```

  Change what you want in Excel, save it as **CSV UTF-8**, then:

  ```
  python tools\playeredit.py --root "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --import C:\fl26\club.csv
  ```

  **You should see** `... players changed`. If you see `nothing written:` instead, the list
  under it says which line and which value is wrong; fix it and import again. Nothing was
  changed in the meantime. The first 11 players by the `order` column are the starting
  eleven, in this order: GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF.
  More, including how to create a new player: [How do I edit the players of the new clubs?](faq.md#how-do-i-edit-the-players-of-the-new-clubs-if-not-in-edit-mode)
- **Crests and kits:** step 7 of [step-by-step.md](step-by-step.md).

After any of these, start a **new** Master League career to see the change. A career that
already started keeps its own copy of the clubs.

## Optional: more leagues and bigger features

The six-league world above is the tested, safe start. Bigger worlds (39 leagues, different
league sizes, promotion and relegation, the new Champions League format) need the
experimental modules. Only try them after the steps above work:
[sider/experimental/README.md](../sider/experimental/README.md) and
[build-your-world.md](build-your-world.md).

---

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `'python' is not recognized` | Python is not installed, or "Add python.exe to PATH" was not ticked | Run the Python installer again, choose **Modify**/**Repair**, and make sure the PATH box is ticked. Then close and reopen PowerShell. |
| `can't open file ... tools\cpkx.py` | PowerShell is not in the project folder | Type `cd C:\fl26` first. Check that `C:\fl26\tools` exists (step 3). |
| `No such file or directory` with a `.cpk` or `.bin` in it | A path is wrong | Check your game path (step 0) and the file names in your `download` folder. |
| Step 4 shows a different number | Different game version | The modules will not run. Report the number. |
| `MISMATCH` / `ABORTED` in `sider.log` | Different game version | Same as above. The game runs normally, just without the new leagues. |
| `fl26joindll: global ffi is nil` | `luajit.ext.enabled = 1` is missing | Step 6, point 4. |
| `LoadLibraryA failed` | `fl26join.dll` is not in the `modules` folder | Step 5. |
| No `fl26` lines at all in `sider.log` | The `lua.module` lines are not in `sider.ini`, or it was not saved | Step 6. |
| The leagues are not in Kick Off | The world is not switched on | Step 10. Check that `sider.ini` has `cpk.root = ".\livecpk\_FL26World"` without a `#` in front. |
| Old club names, or changes do not show | An old Edit save is used instead | Move `EDIT00000000` out of the save folder (step 1 path) and start the game again. |
| Crash when the Master League season is created | A crash in the game itself | Try again. If it happens every time, report it. |

## Getting back to normal

1. Close the game.
2. Put your backup `sider.ini` (step 1) back in `C:\Football Life 2026\SiderAddons\`,
   replacing the one there.
3. Put your backup `save` folder back.

Your game is exactly as it was before. The game's own files were never changed. Master
League saves made with the new leagues will not load without the modules, so keep them
separate.

## Asking for help

Open an issue on GitHub and include:

1. which step you were on and what you saw;
2. your `SiderAddons\sider.log` (attach the file);
3. the number from step 4.
