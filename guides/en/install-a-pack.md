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

Steps 1 to 5 are the same for everyone and you do them once. Then pick the way that matches
the file you were given:

- **Way A: a ready world**, as one `.zip` (a modpack, a friend's world). The quickest way:
  nothing to build.
- **Way C: a league package**, a `.fl26pack` file someone made. Mod Studio builds it for you.

Nobody gave you anything, and you want to choose real leagues yourself (from the NewLife
Database) or make your own? That is the other guide:
[Make your own leagues and packs](make-your-own-leagues.md). Do steps 1 to 5 here first.

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
Credits**, and a green **Play** button on the right. Down the left: **Home**, then the groups
**LEAGUE BUILDER**, **GAME CONTENT** and **MANAGE**.

If Windows says "Windows protected your PC": click **More info** → **Run anyway**.

Want the window in another language? Top bar → **Language** → Hrvatski, Español or Français.

## Step 3. Tell it where your game is

1. Left bar, at the bottom under **MANAGE**: click **Settings**.
2. Next to the game folder, click **Browse...**.
3. Pick the folder that holds `FL_2026.exe` (for example `C:\Football Life 2026`). Not
   `SiderAddons`, not a subfolder: the folder with `FL_2026.exe` in it.
4. Click **Use this folder**.

**You should see:** under the folder, a line saying `SiderAddons\sider.ini` was found.

(The same is in the top bar: **Game → Choose the game folder...**.)

## Step 4. Unpack the game's tables

Still on **Settings**: click **Unpack the game's tables**. Wait a few seconds.

**You should see:** a line saying the tables were unpacked.

You do this once. Do it again only after a game update; Mod Studio notices one and asks.

If you skip this step, Build later says `error: no game tables -- Settings > Unpack the game's tables`.

## Step 5. Install Mod Studio's modules

1. Left bar, under **LEAGUE BUILDER**: click **Build**.
2. Click **0. Install the modules**. It asks whether to copy them: click **Yes**.

**You should see:** in the box at the bottom, the modules listed as installed.

The new leagues only work with these modules. They also carry the face pack that gives the new
players their faces. You do this once, and again after every new version of Mod Studio.

Now pick the way that matches your file.

---

## Way A: a ready world (one .zip)

Use this when someone gave you a world as a zip (a modpack, an exported world).

**A1.** Do not unzip it yourself.

**A2.** Left bar, under **MANAGE**: click **Install mods**.

**A3.** Click **Choose a file...** and pick the zip. (Or drag the zip onto that page.)

**A4. You should see:** a list of what is inside, for example the world (`_FL26Modpack` or
similar, marked as a League Builder world), kits and scoreboards. Everything is ticked. Leave it so.

**A5.** Click **Install**. Wait until it says it is done. Mod Studio copies the world, puts its
world file where the modules read it, and switches the world on.

**A6.** If it asks to install the modules: say **Yes**.

Do **not** press Build for a ready world. It is already built. Go to [Step 6](#step-6-start-the-game).

---

## Way B: build your own leagues

Choosing real leagues from the NewLife Database, or making leagues of your own, has a guide of
its own, with every field explained:
[Make your own leagues and packs](make-your-own-leagues.md).

---

## Way C: a league package (.fl26pack)

**C1.** Left bar, under **LEAGUE BUILDER**: click **League packages**.

**C2.** Click **Add a package...** and pick the `.fl26pack` file. (Or top bar: **File → Add a
league package...**.)

**C3. You should see:** a window **Add a league package** with what is inside: its name, version
and author, then its leagues, each ticked. A package with several leagues has **Select all** /
**Select none** over the list: untick a league you do not want. Under **What to take** you can
untick parts (for example **Scoreboards ...**). If you are not sure, leave everything ticked.
Click **OK**.

If the package has a league with a name you already have, it asks whether to add it under a
new name: click **Yes**.

**You should see:** a green line under the page title: "Added ... Save the recipe, then Build to
put the leagues in the game."

**C4.** Top bar: **File → Save recipe**. The first time, a save window opens: give the file a
name and click **Save**. (The recipe is your list of leagues. Save it so you can change it later.)

**C5.** Left bar: **Build** → the big blue **Build and install** → **Yes**.

It installs the modules, builds the world and switches it on, all in one. It takes from a few
seconds to a few minutes.

**You should see:** a window **Build finished** with ticks (World built, Leagues and clubs,
Modules installed and switched on, Switched on in sider.ini). Click **Done**. In the box at the
bottom of the Build page there is no line starting with `error:`.

---

## Step 6. Start the game

Click the green **Play** button at the top right (or **Game → Start the game**). Wait for the
game's menu.

## Step 7. Start a NEW Master League

1. **Master League** → **New game** (not Continue: an old career does not get the new leagues).
2. At **Select Team**, scroll: the new leagues are in the list, under their countries.
3. Pick a club and play.

The new leagues are also in **Kick Off** → League, and in **Database → Competition Info**.

## Step 8. Let Mod Studio check that it worked

1. Close the game.
2. In Mod Studio: **Build** → **4. After a start: check**.

**You should see:** one line per module saying how many leagues it read from the world, and at
the end `the world works as built`. A line saying `not loaded` or `did NOT read the world file`,
and the last line `something is wrong -- see the lines above`, tell you what is wrong.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | Do [Step 4](#step-4-unpack-the-games-tables). |
| No new leagues at Select Team | Did you start a **new** Master League? Then **Build → 4. After a start: check**. If its log says `world file -- 0 leagues`, the recipe was empty: add the package again (Way C) and build again. |
| The world says it was built with `0 leagues, 0 clubs` | Same: the recipe had no leagues. Add some first, then Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | The check ran before you started the game. Start it to the main menu, close it, press **4. After a start: check** again. |
| All new players have the same face | **Build → 0. Install the modules** (it brings the face pack), then start the game again. |
| The game crashes at start | Start it once more through the launcher (a crash in the first 10 seconds also happens without mods). If it keeps crashing: **Game → Start the game without mods (safe mode)...** and ask on Discord. |
| You want everything back as it was | **MANAGE → Install mods → Remove the mod** for an installed world; **MANAGE → Restore points** puts back any file Mod Studio changed. |

**Asking for help:** on the [Discord](https://discord.gg/StQqtk3G3M), send a screenshot of what
you see and your `sider.log` (**Game → Open sider.log**, or `SiderAddons\sider.log` in the game folder).
