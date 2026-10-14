# Install a ready pack: every click, in order

> **English** · [hrvatski](../hr/install-a-pack.md) · [español](../es/install-a-pack.md) · [português](../pt/install-a-pack.md)

> The other step-by-step guide: [Make your own leagues and packs](make-your-own-leagues.md)
> · every page explained: [mod-studio-guide.md](mod-studio-guide.md)
> · questions: [faq.md](../../docs/faq.md) · help: [Discord](https://discord.gg/StQqtk3G3M)

This page is for someone who has never opened Mod Studio and has been given something ready to
play: a world, a modpack or a league package. It does not explain how anything works. It only
says what to click, in what order, and what you should see after each step. Do the steps in
order and do not skip one. If you see something different from what a step says, stop there
and go to [If something goes wrong](#if-something-goes-wrong).

Steps 1 to 3 are the same for everyone and you do them once. Then pick the way that matches
the file you were given:

- **Way A: a ready world**, as one `.zip` (a modpack, a friend's world). The quickest way:
  nothing to build.
- **Way C: a league package**, a `.fl26pack` file someone made. Mod Studio builds it for you.

Nobody gave you anything, and you want to choose real leagues yourself (from the NewLife
Database) or make your own? That is the other guide:
[Make your own leagues and packs](make-your-own-leagues.md). Do steps 1 to 3 here first.

---

## Step 1. Close the game

The game must be closed while you change anything. Sider reads its setup only when the game
starts. Check the taskbar: no Football Life window, no launcher.

## Step 2. Download Mod Studio

1. Open the [latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. Under **Assets**, click `FL26ModStudio-<version>.zip` (for example `FL26ModStudio-0.2.1.zip`).
3. Right-click the downloaded zip → **Extract All...** → choose a folder, for example
   `Documents\FL26 Mod Studio` → **Extract**.

   Do not run the program from inside the zip. Do not move `FL26ModStudio.exe` out of its
   folder: the `_internal` and `pack` folders next to it must stay with it.

4. Open that folder and double-click `FL26ModStudio.exe`.

**You should see:** a dark window. Along the top: **File, Game, Profiles, Language, Help,
Credits**, and a green **Play** button on the right. Down the left: **Home**, then **YOUR WORLD**
(**Build and edit your world**, **Import your world**, **NewLife Database**), **GAME CONTENT**,
**TOOLS** and, at the bottom, **Settings**.

If Windows says "Windows protected your PC": click **More info** → **Run anyway**.

Want the window in another language? Top bar → **Language** → Hrvatski, Español or Français.

## Step 3. Tell it where your game is

1. Left bar, at the bottom: click **Settings**.
2. Next to the game folder, click **Browse...**.
3. Pick the folder that holds `FL_2026.exe` (for example `C:\Football Life 2026`). Not
   `SiderAddons`, not a subfolder: the folder with `FL_2026.exe` in it.
4. Click **Use this folder**.

**You should see:** under the folder, a line saying `SiderAddons\sider.ini` was found.

(The same is in the top bar: **Game → Choose the game folder...**.)

There is nothing more to set up. Once it knows where your game is, Mod Studio unpacks the game's
tables (its list of clubs, leagues and players) by itself, the first time only. Mod Studio's
modules go in with **Install the world** (Way A) or **Build and install** (Way C). The new
leagues only work with these modules, and they carry the face pack that gives the new players
their faces. If **Home** ever says they are missing or older, click **Install now** there.

Now pick the way that matches your file.

---

## Way A: a ready world (one .zip)

Use this when someone gave you a world as a zip (a modpack, an exported world).

**A1.** Do not unzip it yourself.

**A2.** Left bar, under **YOUR WORLD**: click **Import your world**.

**A3.** Click **Choose a file...** and pick the zip. (Or drag the zip onto that page.)

**A4. You should see:** one line saying what it is, for example `a ready world to play
(_FL26Modpack)`, or `a newer version of the world _FL26Modpack you have` when you have an older
one, and under it how many leagues are inside. The parts (the world, kits, scoreboards ...) are
under **More options: which parts, name, order of the content folders, map lines**, all ticked.
Leave them so. (To install it without the kits, untick the kits there.)

**A5.** Click **Install the world**. If an older version of the same world is installed (an
earlier Modpack), it asks to replace it: say **Yes**. The older one is taken out first, so
nothing of it stays behind; your saves are not touched. Wait until it says it is done. Mod Studio
installs its modules (the ones of this version), copies the world, puts its world file where the
modules read it, and puts the world in the game.

**You should see:** `✓ Ready to play: press Play and start a new Master League`, and a window
**Ready to play** with a list of ticks (the world, the modules, the face pack ...). If it says
**Almost ready** instead, it lists what to fix.

A ready world needs no Build: it is already built. While it is in the game, the Build steps are
switched off (0.2.4). To build leagues of your own later, put your own world in the game first
(**Home → Switch world...**). Go to [Step 4](#step-4-start-the-game).

---

## Way B: build your own leagues

Choosing real leagues from the NewLife Database, or making leagues of your own, has a guide of
its own, with every field explained:
[Make your own leagues and packs](make-your-own-leagues.md).

---

## Way C: a league package (.fl26pack)

**C1.** Left bar, under **YOUR WORLD**: click **Build and edit your world**, then the tab
**League packages**.

**C2.** Click **Add a package...** and pick the `.fl26pack` file. (Or top bar: **File → Add a
league package...**.)

**C3. You should see:** a window **Add a league package** with what is inside: its name, version
and author, then its leagues, each ticked. A package with several leagues has **Select all** /
**Select none** over the list: untick a league you do not want. Under **What to take** you can
untick parts (for example **Scoreboards ...**). If you are not sure, leave everything ticked.
Click **OK**.

If the package has a league with a name you already have, it asks whether to add it under a
new name: click **Yes**.

**You should see:** a green line under the page title: "Added ... Build and install puts its
leagues in the game."

There is nothing to save: your world saves itself a moment after each change (the bottom bar
says **Your world is saved**).

**C4.** Tab **Build** (next to **League packages**) → the big blue **Build and install** → **Yes**.

It puts Mod Studio's modules in, builds your world and puts it in the game, all in one. It takes
from a few seconds to a few minutes.

(Dropping the `.fl26pack` on **Import your world** does the same: after the window of C3 the
package goes into your world and **Build and install** starts by itself.)

**You should see:** a window **Build finished** with ticks (World built, Leagues and clubs,
Modules installed and switched on, In the game). Click **Done**. In the box at the bottom of the
Build page there is no line starting with `error:`.

---

## Step 4. Start the game

Click the green **Play** button at the top right (or **Game → Start the game**). Wait for the
game's menu.

## Step 5. Start a NEW Master League

1. **Master League** → **New game** (not Continue: an old career does not get the new leagues).
2. At **Select Team**, scroll: the new leagues are in the list, under their countries.
3. Pick a club and play.

The new leagues are also in **Kick Off** → League, and in **Database → Competition Info**.

## Step 6. Let Mod Studio check that it worked

1. Close the game.
2. In Mod Studio: **Build and edit your world** → tab **Build** → **Step by step, and Export the
   world** → **4. After a start: check**.

**You should see:** one line per module saying how many leagues it read from the world, and at
the end `the world works as built`. A line saying `not loaded` or `did NOT read the world file`,
and the last line `something is wrong -- see the lines above`, tell you what is wrong.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| No new leagues at Select Team | Did you start a **new** Master League? Then **4. After a start: check** ([Step 6](#step-6-let-mod-studio-check-that-it-worked)). If its log says `world file -- 0 leagues`, your world was empty: add the package again (Way C) and build again. |
| The world says it was built with `0 leagues, 0 clubs` | Same: your world had no leagues. Add some first, then Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | The check ran before you started the game. Start it to the main menu, close it, press **4. After a start: check** again. |
| All new players have the same face | **Home → Install now** (when Home says the modules are missing or older), or **Build and edit your world → Build → Step by step, and Export the world → 0. Install the modules**: it brings the face pack. Then start the game again. |
| The game crashes at start | Start it once more through the launcher (a crash in the first 10 seconds also happens without mods). If it keeps crashing: **Game → Start the game without mods (safe mode)...** and ask on Discord. |
| You want everything back as it was | **Import your world** → select it under **In the game now** → **Remove** takes out an installed world. **TOOLS → Restore points → Put Sider back as before Mod Studio...** (also in the **Game** menu) puts back every file Mod Studio changed and takes out what it brought. Nothing is deleted: it is kept in `SiderAddons\ModStudio\reset-<time>`, and **Undo the last reset** puts it back. |

**Asking for help:** on the [Discord](https://discord.gg/StQqtk3G3M), send a screenshot of what
you see and your `sider.log` (**Game → Open sider.log**, or `SiderAddons\sider.log` in the game folder).
