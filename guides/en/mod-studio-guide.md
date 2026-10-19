# FL26 Mod Studio — user guide

> **English** · [hrvatski](../hr/mod-studio-guide.md) · [español](../es/mod-studio-guide.md) · [português](../pt/mod-studio-guide.md) · [français](../fr/mod-studio-guide.md)

> **New to Mod Studio?** Two step-by-step guides, every click in order: [Install a ready pack](install-a-pack.md)
> (someone gave you a world, a modpack or a `.fl26pack`) · [Make your own leagues and packs](make-your-own-leagues.md)
> (you pick the leagues and build them). This guide explains every page and option in depth.

> Common questions (updating, crashes at start, cups, promotion, what to send when something is
> wrong): [faq.md](../../docs/faq.md) · questions and help on [Discord](https://discord.gg/StQqtk3G3M)

FL26 Mod Studio is one program for everything you add to Football Life 2026:

- **mods** you download: stadiums, kits, balls, scoreboards, commentary, music, faces, Lua modules;
- the **content servers** that serve them (Stadium Server, Ball Server, Kit Server and the rest),
  with their map files edited as tables instead of by hand;
- the **Sider setup** itself: which content folders and modules are on, and in what order;
- **new leagues and clubs** (the League Builder), your changes to the game's own leagues, clubs
  and **players**, and **league packages** a modder makes once and anybody adds to their game.

Nothing of the game is overwritten. Before the program changes a file it keeps a copy, and every
mod it installs can be removed again.

---

## 1. Before you start

- **Football Life 2026** installed, with its `SiderAddons` folder (FL26 comes with Sider).
- Unzip the program anywhere, e.g. `Documents\FL26 Mod Studio`. Keep the folder together: the
  `_internal` and `pack` folders and the `README` files stay next to `FL26ModStudio.exe`.
- **Close the game** while you change things. Sider reads its setup when the game starts.

The window is in English. **Language** in the top bar (or **Settings → Language**) switches it to
Croatian (Hrvatski), Spanish (Español), Brazilian Portuguese (Português) or French (Français).
The new language shows the next time you start Mod Studio.

## 2. First run

**The quick tour.** The first time you start 0.2.4, a small card shows you where everything is
now, one place at a time, with an orange frame around the thing it talks about: the language,
the boxes of what is in the game, **Start the game**, then **1. Home** to **5. Settings** and
**Help**. Ten steps. Nothing is changed while it runs. **Next** and **Back** move through it,
**Skip the tour** closes it, and **Help → Quick tour** shows it again at any time. Its last card
has **Show me how to install a Modpack**: a second card that walks you through installing a Modpack
(a world zip), click by click (also **Help → Install a Modpack, step by step**).

1. **5. Settings → Game folder**: press **Browse...**, pick the folder that holds `FL_2026.exe`,
   then **Use this folder**. The line under it says what was found, e.g. `Found: FL_2026.exe,
   Sider in SiderAddons, sider.ini.`
2. The game's tables: Mod Studio unpacks them by itself the first time (it reads the game's
   clubs, leagues and players into a working folder; this takes a minute or two, and the bottom
   bar says so). After a game update Build notices and offers to unpack them again first;
   **Settings → The game's tables → Unpack the game's tables** does it by hand. **Use another
   tables folder...** is for a database of your own, such as a `pesdb` folder in livecpk: unpack
   the game's tables first, then pick that folder. Its files go over the game's, which give
   whatever it does not have. A database mod that moves the game's leagues into other leagues'
   places (UML 2026 and the like) is fine: each league of the game takes the country most of its
   clubs are of, and the NewLife Database counts a club as one of the game's only when these
   tables have it (0.2.4).
3. Open **1. Home**. It shows the world in the game (**IN THE GAME NOW**, with **Open its
   leagues** and **Switch world...**, which opens **2. My world**), a card that says whether your
   world has changes the game does not have yet (**Go to Build** and **Only the European
   cups...**), and the **Ready check**: a table with one row per check (game, Sider, modules,
   content folders ...). When something is wrong, a red bar names the problem and has the button
   that puts it right. When Mod Studio's modules are missing, older or switched off, the row says
   which ones and **Install now** puts them in. On the right: **Quick actions** (**Install the
   modules**, **Build the world again**, **Import a world zip**, **Add a league package**) and
   **Last changes** (the newest restore points, **All restore points**).

**Updates.** A few seconds after it starts, the program asks GitHub whether a newer FL26 Mod
Studio is out, and says so only when there is one. **Download and install** fetches the new zip,
checks it against the release's checksum, closes the program, puts the new files over the old
ones and starts it again. Your settings, worlds, restore points and the game are not touched.
**Help → Check for updates...** asks at any time; untick **Help → Check for updates at start** and
the program asks only then. If the program sits in a folder Windows will not
let it write to (such as Program Files), it opens the release page instead: unpack the zip
yourself, or move the program to a folder of your own.

**Careers from before 0.2.0.** 0.2.0 lets a calendar day hold 792 matches instead of 280, and that changes the tables a career is saved with: **a career saved with an older version does not load** (it stays on the loading screen). Start a new career after the update. Your worlds and Edit data are not affected.

**0.2.4 and your career.** A career saved with 0.2.2 or 0.2.3 keeps working, and a cup saved
before 0.2.4 loads too. One fix needs a new Build: until 0.2.4 the goalkeeper was the captain of
every club of a world made with Mod Studio. **Build** now gives every club and national team
that has none a captain and players who take the penalties, free kicks and corners. To get them,
**Build** your world again and start a new career.

**Play.** The **Start the game** button at the top right (or **Game → Start the game**) starts
the game and warns first when modules are in a wrong order. Next to it a label says whether all
is set: **READY TO PLAY**, **NOT READY** or **NO WORLD YET**. **Game → Start the game without
mods (safe mode)...** puts back the setup Mod Studio found the first time.

**Credits.** The **Credits** button next to **Help** lists everyone who helped make Mod Studio:
the testers, the people who sent reports and logs, and the ones whose ideas are in it.

**More than one Sider folder?** Sider does not have to be called `SiderAddons`. The program
looks for the folder next to `FL_2026.exe` that holds a `sider.ini`, and one level further
down too (`sider\patch 1`, `sider\patch 2` ... when one folder holds a few Sider copies). If
there are several, **Settings → Sider folder** chooses which one it works on; the others are
not touched.

**Game under Program Files.** Windows lets only a program run as administrator change files
there. When Mod Studio cannot write into the game folder, it says so (on **Home** too) and
offers **Restart as administrator**. Or move the game to a folder of your own.

## 3. The pages

At the top of the window, from left to right:

- the menus **File**, **Game**, **Profiles**, **Language** and **Help**, and **Credits**;
- the **Start the game** button with the ready label next to it;
- under them, boxes with what is in the game now: **GAME FOLDER**, **SIDER**, **ACTIVE WORLD**,
  **MODULES**, **LEAGUES** and **PACK**. A red box names the problem; click a box to go to the
  page where it is fixed;
- then the numbered sections, and at the bottom of the window a status bar (ready or the
  problem, what the program is doing, **Your world is saved**, the number of restore points).

| Section | What is in it |
|---|---|
| **1. Home** | The world in the game, the ready check, quick actions |
| **2. My world** | Your worlds as cards, and the tabs **Build**, **Leagues**, **Clubs**, **Players**, **Kits**, **Stadiums** and **Cups** (section 3.1) |
| **3. Game content** ▾ | **Balls**, **Commentary**, **Music**, **Other content** |
| **4. Tools** ▾ | **Lua modules**, **Content folders**, **Profiles**, **Restore points**, **Diagnostics** |
| **5. Settings** | Game folder, Sider folder, language, Master League careers, the game's tables |

**File** has **New world**, **Open a world...**, **Save your world as...**, **Changes in this
world...** (everything your world changes in the game in one list; pick lines and press **Undo
the picked changes** to take them back), **Add a league package...** and **Make a league
package...**. **Game** opens the game folder, the Sider folder, `sider.ini` and `sider.log`, and
starts the game. **Help** has **User guide**, **Quick tour**, **Install a Modpack, step by
step**, **Edit a Modpack, step by step**, **Check for updates...** and **About FL26 Mod Studio**.

### 3.1 My world

**2. My world** is the place for your worlds. A **world** is a content folder named `_FL26...`
that holds new leagues, clubs and players; the game reads one at a time (section 8).

**At the top**: **COMPETITIONS** (how many competitions, leagues and cups together, the world in
the game has; the game has room for 255), **NEW COUNTRIES** (how many countries it adds; room for
99), a reminder that **changes need a new Master League**, and the state of the open world.
**▾ Worlds** folds the row of cards away to make room, and shows it again.

**The cards**: one card for every world on disk. The world in the game comes first, then the
newest ones; the mouse wheel moves the row left and right.

- The world in the game is green, with **● IN THE GAME NOW** and **● Active**. A world installed
  from a zip has the tag **From zip**.
- Every other built world (**NOT IN THE GAME**) has **▶ Activate**: it puts that world in the
  game (switched on in `sider.ini`) and takes the one in the game out. Nothing is deleted: the
  other world stays on disk with its own careers. Start a new Master League after it.
- Every card has **Export...** (one `.zip` of the world for another PC, section 9.1),
  **Rename** and **Delete**. **Delete** takes the world out of the game and off the disk, but
  keeps all of it in **Restore points** (section 5), so it still takes its space on the disk until
  you remove that copy there with **Delete this copy for good...**. The world in the game cannot be
  deleted: activate another world first.
- **+ New world** at the end starts an empty world of your own (the same as **File → New
  world**); then add its leagues on **Leagues**.

If two worlds are switched on at once, the green card says **▶ Keep only this one**: it keeps
that world in the game and switches the others off.

**The tabs** under the cards change the open world: **Build** (section 8.2), **Leagues**,
**Clubs** and **Players** (section 8), **Kits** and **Stadiums** (section 6). **Cups ▾** opens
the cup windows: **Pre-season cups**, **Cups of our countries**, **Cups of the game's countries**
and **Competition names**. On the right:

- **NewLife Database** opens the NewLife page (section 8.4);
- **+ Add...** is one window for three things: a world zip (a Modpack), a league package
  (`.fl26pack`) and the NewLife Database (a folder or its zips). Drop the file on it or use
  **Choose a file...** / **Choose a folder...**. It says in one green line what it found; for a
  league package it lists the leagues to tick and how many competitions the world will have.
  **Add** hands it to the right page: a world zip to **Import your world** (section 4), a
  package into your world, the NewLife Database to its page. Nothing reaches the game until
  **Build and install**;
- **More ▾** has **League packages** (section 9), **Import a world zip** (section 4), **NewLife
  Database** and **Content folders** (section 5).

**A world from a zip** (a Modpack) is built already, so **Build** is switched off for it
(section 8.2). To change it anyway, **Make it editable...** at the top of My world turns it into
a world of your own, in place and under its own name. All of it is copied to **Restore points**
first. After you Build it, start a new Master League. **Help → Edit a Modpack, step by step**
shows it click by click.

**Each world keeps its own Master League careers** (0.2.4). A career is made for one world: in
another world its leagues and clubs are not there. So every time the world in the game changes
(**Activate**, **Build and install** of another world, Import your world, Content folders, a
profile), Mod Studio changes the game's save folder with it. The careers of the world going out
are kept in `save_<world>`, next to `save`, in `Documents\KONAMI\eFootball PES 2021 SEASON
UPDATE\2026`. The careers of the world coming in come back into `save`; a world with none yet
starts with an empty one. The whole folder goes with the world (careers, Become a Legend, the
Edit data), except your game settings, which come with you into every world.

Nothing is deleted: before the first switch Mod Studio copies your whole save folder into
`SiderAddons\ModStudio\backups\saves\<date>` (**Restore points** lists it), and the first time it
tells you where your careers went. It does not switch while the game is running, or when a
`save_<world>` folder of that name is there already: it says why and changes nothing. **Rename**
renames the world's `save_<world>` too; **Delete** leaves it alone (your careers are yours).
Don't want it? Untick **Settings → Each world keeps its own careers (the save folder is switched
with the world)**.

**Leagues** (a tab of My world) lists every league, the game's and yours, under its continent;
each country's divisions stand together, from the top down (Bundesliga, 2. Bundesliga, 3. Liga),
until you drag a league to put it somewhere else. Filters **All**, **Ours** and **Changed**, and
a search box. Pick one: a league of yours gets **Edit league...**, **Add lower tier**, **Clubs and
names**, **Players** and **Remove**; a league of the game gets its name, logo and clubs (section
8, "The game's leagues"). **Add league** makes a new one. **Places in Select Team** shows where
the last Build put each of your leagues. **More ▾** has **Pre-season cups**, **Cups of our
countries**, **Cups of the game's countries**, **European places of the game's leagues**,
**First-season European clubs**, **UEFA ranking**, **South American places**, **Competition
names**, **Competition IDs**, **League order**, **Seasons of the game's leagues** and **World
name and file...**. That last one opens the page with the world's name and the list of your
leagues (older guides call it *New leagues*).

## 4. Import your world

**Import your world** is the page that installs a downloaded pack. Reach it with **2. My world →
More ▾ → Import a world zip**, with **Import a world zip** under **Quick actions** on **Home**
(it opens the file picker at once), or with **+ Add...** in My world.

Drop the pack on it (`.zip`, `.7z`, a folder, `.lua`, `.cpk` or `.fl26pack`), or use
**Choose a file...** / **Choose a folder...**. When Mod Studio runs as administrator, Windows
blocks drag and drop; the page says so: use the two buttons.

The program looks inside and says in one line what it is: a newer version of a world you have, a
ready world to play, a league package or a mod, with the leagues inside. Then one button,
**Install** (**Install the world** for a world). A newer version of a world you have replaces the
older one: it asks once, the older one is taken out first so that nothing of it stays behind,
your saves are not touched, and you start a new Master League with the new one. If a world of
the same name was built on this PC, it says so before you press Install and tells you to rename
that world on its card in My world first.

The parts, and where each goes, are under the fold **More options: which parts, name, order of
the content folders, map lines**:

| Part | What happens |
|---|---|
| Content folder (livecpk) | Copied to `SiderAddons\livecpk\<name>` and added to `sider.ini`. |
| Content server files | Copied into the server's `content` folder. Its **map file is merged into yours**: your lines stay and the mod's new lines are added. For a club you have already mapped, the choice under **More options** decides: *use the mod's*, or *keep mine, add the mod's after*. A scoreboard or menu pack made for another world goes on the competition its name says in your world, and the page says which league your world does not have. |
| Lua module | Copied to `SiderAddons\modules` and switched on in the right place of the order. |
| Packed .cpk | Unpacked into a content folder on install. |
| League package | Added to your world (section 9). A `.fl26pack` dropped here goes in, and **Build and install** starts by itself. |
| Ready world | A built world from **Export the world** (section 9.1), or a copied `SiderAddons` folder with `modules\fl26world.txt`. The world folder is copied under its own name, its world file goes to `SiderAddons\modules`, and the world is put in the game with Mod Studio's modules. It ends with **✓ Ready to play: press Start the game and start a new Master League** and a final check list: the world, switched on, the modules, the face pack, the content servers the world uses, the home stadiums. If something is missing it says **Almost ready** and what to fix; the red line under the install (*see what to fix*) shows the list again. |
| DLL | **Not installed.** A DLL runs with the game's rights; install one only from a source you trust, by hand. |

In the same fold you can untick a part you do not want (the kits, say, to install a world
without kits), give the mod a name, and choose whether new content folders go on top (they win)
or at the bottom. **In the game now** lists every pack installed with the program. **Remove**
deletes the files it added and puts back the files it replaced.

The install copies every file first and writes the map lines last, so an install that stops
half way leaves no line that points at a missing file. If that happened with an older version,
**Diagnostics** names the zip or world: install it again (a world built on your PC: Build it
again).

## 5. Content folders and Lua modules

**Content folders** (**4. Tools**) lists the `cpk.root` lines of `sider.ini`; worlds (`_FL26...`)
show when you tick **Show the worlds (_FL26...)**, and **Only switched on** hides the rest. The
world the game uses now is on a green row, its name in bold, with **IN THE GAME NOW** in the
Note column. Sider looks a file up from the top down, so the folder higher in the list wins when
two have the same file.

- Tick or untick a folder to switch it on or off (the line is commented out, never deleted).
- **To top**, **Up**, **Down** change the order; **Add folder...** adds a folder you already have.
- The size and what is inside (faces, kits, stadiums...) are shown for each folder.
- **Rescan**, **Remove from the list** and **Delete from disk...** are there too.
- Nothing is written until you press **Apply**. **Discard** forgets the changes.

**Rename world...** and **Delete world...** (under the folder's details when a world is picked,
or right-click the world) do the same as **Rename** and **Delete** on a world's card in My world:

- **Delete world...** asks first and deletes nothing for good. The world's folder, its kits and
  scoreboards, its lines in `sider.ini` and in the kit and scoreboard maps, and its install
  record go into `SiderAddons\ModStudio\backups\worlds\<world>\<date> deleted`, and **Restore
  points → Put this copy back** brings it all back exactly as it was. The last 3 copies of each
  world are kept. The world in the game (the green one) cannot be deleted. Your world in Mod
  Studio (its leagues) is not deleted, so you can build it again. **Delete from disk...** on a
  world row does the same safe delete.
- **Rename world...** changes the name everywhere it is written: the `sider.ini` line (same
  place, on or off as it was), the kit and scoreboard folders and their map lines, the world
  file, your profiles and your world in Mod Studio. The new name must start with `_FL26`
  (letters, digits, `-` and `_`). A big world is renamed in the background ("Renaming ..." in the
  bottom bar and on its card). A career keeps working after a rename: the game never sees the
  world's name, only the files in it.

**Lua modules** (**4. Tools**) is the same for the `lua.module` lines. The line at the top says
whether Mod Studio's own modules are installed, up to date and switched on; when not, it names
the ones that are missing, older or switched off, and **Install now** puts them right. The
program knows the right order for the common modules (content servers after the modules they
use) and says so when a module sits in the wrong place. Some modules need a Sider setting (for
example Goal Song Server needs `match-stats.enabled = 1`); the program says which. Mod Studio's
own `fl26...` modules are hidden until you untick **Hide Mod Studio's own modules (fl26...)**;
**Add module...** adds a module you have.

Mod Studio's own modules keep the order they were installed in, together in one block of
`sider.ini` with a heading of its own. Old lines left by a hand install (an old caps set, a
module listed twice) are switched off by **Install now** and **Build**.

Since 0.2.0 the twelve small crash guards go in as two files, `fl26guards.lua` (the eight `fl26nullguard` ones) and `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), so the list is shorter. sider.log still names each guard on its own line. Build switches the old single lines off; there is nothing to do by hand.

**No copies next to your files** (0.2.4). When Build, Switch on or Install the modules change a
file, the copy from before goes into `SiderAddons\ModStudio\backups` and shows in **Restore
points**, not next to the file (no more `map.txt.before-builder` or `modules\before-builder-<n>`).

**Switching the regens off** (0.2.0): `fl26regen` gives regens new names, a new potential and a
face of the regen face pack. To play without it, untick **Hide Mod Studio's own modules
(fl26...)** so ours show, untick `fl26regen` and press **Apply**. Mod Studio writes it down in
`modules\fl26-off.txt` in the Sider folder, so **Build**, **Install the modules** and switching
worlds leave it off instead of turning it back on, as they do with every other module. The game
then makes its own regens: its own potential and names, no faces from the regen face pack. Tick
it again and **Apply** to switch it back on. Only `fl26regen` can be kept off this way.

## 6. Game content: the content servers

Each of these pages belongs to one content server. **Kits** and **Stadiums** are tabs of
**2. My world**; **Balls**, **Commentary**, **Music** and **Other content** are under **3. Game
content**. **Other content** has a tab each for **Scoreboards**, **Menus**, **Referee kits**,
**Sleeve badges** and **Weather**, and **Look modules**. SPFL26's own modules for kits, stadiums and scoreboards (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) read the same files from `content\kits`, `content\stadiums` and `content\scoreboards`; when the server itself is not installed, its page edits those instead (kits since 0.1.7, stadiums and scoreboards since 0.1.8). Every page has:

- a **status line**: is the module on, is its content folder there;
- a tab per **map file**, shown as a table: which competition, club or stadium gets what.
  **Add...**, **Change...**, **Copy**, **On / off** (the line becomes a comment) and **Remove**;
  pick items from the library instead of typing ids. **Save** writes the file; the copy before it goes to Restore
  points;
- the **Library**: what is in the server's content folder, with pictures where there are any.
  Items that no map line uses and map lines that point at missing items are marked;
- **Settings** of the server where it has any (favourite stadium, ball, scoreboard ...).

The program checks the tables before saving: a number where a number goes, no commas inside a
name, an item that exists. A line with a problem is coloured: **hold the mouse over it to see
why**. **Only lines with problems** shows just those. A club listed twice is marked too: only its
first line counts. The most common problem, "... not found in the library", means the line points
at a folder that is not in the server's content folder, and the game shows nothing there (a black
stadium, the club's old kit): point it at a folder the **Library** tab lists, or remove the line.
**Look modules** (on **Other content**) switches modules without map files on or off.

A competition line is keyed by a **stage** of the competition, not by the competition: the game
tells the content servers the stage it is playing (the Conference League is 186, 1210, 187,
189 and its later rounds 1213 ... 8381; the Champions League 2, 3, 4 and theirs), so a line
with the competition's own number (174) is never used. The competition picker lists every
competition once more as **(all N stages)**: pick that and one line is written for each stage
(0.1.9). A line keyed by a competition number is marked as a problem.

**Scoreboards of a world from a zip.** A ready world (the Modpack) brings the scoreboards of its
leagues. While another world is in the game, their lines stay in **Other content →
Scoreboards**, switched off, and they come back on with their world. The same goes for the menu
themes a world brought.

**Import kits...** (0.1.8, on the *Kits* tab): kits for many clubs at once. Pick a folder of ready kit-server kits -- one folder per club, holding `p1`, `p2`, `g1` ... and `order.ini`, named after the club (`Dinamo Zagreb`) or its team ID (`2215`). **Match to** picks *All clubs* or *The new clubs of the world in the game*. Matches of 60% or more are ticked; check the unticked ones and the *Match* column before **OK** (a folder with no match says "no club found"). The kits are copied into the kit-server library (`League\Club`, as the folder had them) and each club gets a line in `map.txt`; **Save** writes it. A club that already has a line keeps it unless **Replace kits already set** is ticked. A new club's kits go by the team ID Build gave it, so Build the world and keep it in the game first. A club folder can instead hold plain kit pictures (0.2.0): `p1.png`, `p2.png` ... for the kits and `g1.png` for the goalkeeper (2048 x 2048 is best; `.jpg` and `.dds` work too). Mod Studio turns them into kit-server kits; the back numbers, leg numbers and name font are textures of their own, so they come from a kit already in the library, picked in **Numbers and names from** (it starts on the first kit of the library that has them; *none*: the game keeps the club's own). The colours in `config.txt` are read off the picture. The picture conversion is Xxspedd's, from his kit tool. Mod Studio does not draw kits: the pictures come from you or a kit maker.

If your world is built with **Plain kits to change in Edit mode** (section 8), Kit Server does
not dress the new clubs, so imported kits do not show on them; **Import kits** says so. Untick
that option on the **Build** tab and Build again.

## 7. Profiles

A profile remembers which content folders and modules are on, and in what order. Keep one for
Master League, one for online play, one for testing (**4. Tools → Profiles**, or the
**Profiles** menu):

- **Save current setup...** stores what is on now under a name.
- **Switch to it** puts that setup in `sider.ini` (the old `sider.ini` goes to Restore points).
- **Update with current setup** overwrites the profile; **Delete** removes it.
- **Export...** / **Import...** move a profile to another PC (`.fl26profile.json`).

## 8. League Builder: new leagues, clubs and players

The League Builder adds new leagues to the game and changes the game's own. What it makes is a
**world**: a content folder named `_FL26...` that the game reads while it is in the game. You
work on the tabs of **2. My world**.

**Remove** (Leagues) deletes the selected league with its clubs. To delete several at once, open
**More → World name and file...**, pick them with Ctrl+click, Shift+click or Ctrl+A, then
**Remove** or the Delete key.

**Leagues → Add league**

| Field | What it means |
|---|---|
| **Name** | The league's name in the game. No two the same. |
| **Country** | Gives the flag and where the league is listed. A country the game has no league for gets a heading of its own. |
| **Clubs** | 10 to 24 (1 to 24 for clubs in no league). |
| **Clubs in no league** | For one club, or a few, without a league around them (0.1.8): say only BATE Borisov from Belarus. Pick the group they go in: *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* or *Classic Teams* -- where the game keeps its own clubs that play in no league (Dynamo Kyiv, Wydad Casablanca ...). In Select Team they show under that group. They get names, crests, kits, a manager, a formation, players and a home stadium like any new club (**Edit club**, **Players**); the name above is only how Mod Studio lists them. They play no league, no cup and no European competition, and everything else in this dialog goes grey. On *Leagues* such a group shows *no league (...)* instead of a league ID. |
| **Format** | *Everyone plays everyone*, 1 to 4 times, *splits in two (Scottish style)*, or *Apertura and Clausura*: two tournaments a season (September to early January, January to May), each from zero points, then playoffs of 8 or 4 clubs (or none). The whole season's table decides promotion and relegation. 18 clubs at most. A split is 46 rounds at most, before and after the split together (16 clubs twice is 30, so its biggest group twice can be 8 clubs, 14 rounds). One league per country can be split or Apertura/Clausura for now. **The split and Apertura and Clausura are experimental** (0.2.4): they work, but still have more open bugs than everyone plays everyone, the fully tested format. The window says so under the formats. Please keep reporting what you find. |
| **Division** | *(top division)*, or the league above it: another new league, or one of the game's. To put a new league under another new league in one step: select it and press **Add lower tier** (it takes the country, club count, format and up/down of the league above; only the name is left). A league another new league is already under is grey (0.1.9): the game follows one link down from a league, so groups of one division (three Serie C groups under Serie B) are not possible yet. |
| **Up / down** | How many clubs change places with the league above at the end of the season. |
| **Season** | Top division of a new country only: *August to May* (the default) or *February to December*, like Brazil, Japan or Saudi Arabia: clubs go up and down at New Year, and the divisions below it follow it. Not with a split, Apertura/Clausura or a league cup yet -- nor a split or Apertura/Clausura on a division under a February-to-December league, the game's Liga BetPlay or J1 League included. |
| **Europe** | Top division only: which league position goes to which European competition. **Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL** fills the usual three (*... qualifying* are the August play-offs, see 8.2); **Add place**, the ✕ on a row and **Clear** for anything else. Each position once, and only positions the league has. Below 1 the position reads **Cup winner** (0.1.7): the winner of the country's cup (a new country needs **National cup**) -- and when the winner already has a European place through the league, the place goes down the league to its next club, as UEFA does it. Since 0.2.0 the cup winner can also go to the cups Mod Studio builds (Copa Sudamericana, CAF Confederation Cup, AFC Champions League Two ...); in a new career, before anyone has won the cup, that place goes to the league's next club too. A league of the game can have one too (*European places of the game's leagues*). Leave it empty for a lower tier. The preset follows the country: Asia gets the AFC Champions League and AFC Champions League Two, South America the Libertadores and the Copa Sudamericana, Africa the CAF Champions League and CAF Confederation Cup, North and Central America the CONCACAF Champions Cup, Oceania the OFC Champions League. The **AFC Challenge League** (0.2.0) is the AFC's third cup, below the AFC Champions League Two as the Conference League is in Europe; pick it with **Add place** (*AFC CHL* in the Leagues list). Those seven cups the game does not have are built with the world (section 8.2). A *Libertadores qualifying* place takes the place of a club of the game in the qualifying round (the last one of the country with the most clubs in it), at most six of its eight places; **Check the plan** says which leagues are left out past that. |
| **Logo** | Any picture (PNG with a transparent background looks best). Empty: one is drawn for you. |
| **Country flag** | Your own picture of the country's flag, stretched into the game's flag frame. It replaces the game's flag of that country everywhere (Select Team, players' nationality, the country's heading in Database > Competition Info) while the world is on. Empty: the game's own flag. |
| **Cup** | Top division only. **National cup**: the country gets its own cup, with the name you give (empty: `<league> Cup`). The game fills a country's cup from its top division and the division below it, and the cup's size follows the National cup row of the Limits (8.3): the largest size the cup screen draws that fits, so a field of 22 gives a cup of 20, the top division first. Past 44 clubs the cup keeps the top division alone. A new second division under a country the game already has (Germany, Russia ...) goes into that country's cup too, after the top division's clubs, when the cup's rounds fit the field. A new third division or lower (League One under the Championship) leaves the country's cup to the game's top two divisions, as in the game. **Super cup (champion v cup winner)**: also a one-match super cup before the season. It needs the national cup. |
| **League cup** | Top division only. A knockout of this league and the one below it, the way the Carabao Cup is played (0.2.0): one match a round, the semi-final and the final too, on the Carabao Cup's weeks: 27 August, 23 September, 28 October, the quarter-final 23 December, the semi-final 14 January and the final on Sunday 15 March, on days of its own, never on a national cup or European day. The field is as many clubs of the two divisions as the cup screen draws, up to 44 (20 + 24: the whole Premier League and Championship); where that is not 16 or 32, this league's clubs get the byes and start in the second round. Every tie is drawn at random. Give it a name or leave it empty (`<league> League Cup`). A world built before 0.2.0 keeps the old two-legged cup of 16 with its pre-round until you build it again; a career started before that Build plays the old cup. |
| **Cup logos** | A picture for the national cup, the super cup, the league cup and the Apertura/Clausura playoffs, each on its own. Empty: an emblem with the cup's initials is drawn for it. |
| **Exhibition only -- not in Master League** | For Kick Off and exhibition matches: a historical league, legends and the like. Its clubs never play a Master League season, so the league stands alone: no division above or below, no European places, no cups. It still shows in Master League's team list; pick your own club from another league. |
| **Formation** | How the league's clubs line up. Pick one of the formations the game's clubs use (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; the list says how many clubs of the game play it): each new club gets a copy of the tactics of a club of the game with that formation, and its best eleven is lined up for it at Build. Empty: Build picks for each club the formation its squad fits best (0.2.4; before, a fixed 4-2-3-1): two strong strikers play two up front, good wingers three forwards, three centre backs three or five at the back. The Build log says which formations were picked. A single club can have its own (**Edit club**). |

**World name** (Leagues → More → **World name and file...**) must start with `_FL26`. That page also lists your leagues: after **Build** its **League ID** column
shows each league's competition id in the game, the one its logo file carries. The **#** column is the
league's place in the order (**Move up** / **Move down**), and **Select Team** says where the last Build
put it: *yes*, *in place of* one of the game's groups, or *no place (it plays)*. A `*` there means the
order changed since: Build again to see where it goes. A drag on the **Leagues** tab moves a league only among the places its continent's leagues already hold here (0.2.0; before, it put the whole order in continent order, so North American and Oceanian leagues always came last).

**Pre-season cups** (Leagues → More, or My world → Cups): friendly knockouts of 4 or 8 invited clubs in July, before the season, paired in the order you give them (first against second ...). A club is one of a new league or a club of the game (its id); at least one has to be from a new league, and its country hosts the cup. A career starts in August, so the first one is played in the second season. Each cup can have a **Logo**; empty: one is drawn for it.

**Cups of our countries** (Leagues → More, or My world → Cups, 0.2.4): the cups of your own leagues in one table. For each top division: its national cup, super cup and league cup, each with its name and logo. These are the same fields as in **Edit league...**, without opening every league.

**Cups of the game's countries** (Leagues → More, or My world → Cups): a league cup -- the Carabao Cup, say -- for leagues of the game. Tick **League cup** next to a league: it and the league below it, up to 44 clubs, one match a round from late August to the final in mid-March, drawn at random, the league's own clubs with the byes into the second round (0.2.0; the same cup as a new league's), on days the game's league and cup calendar leaves free. **Super cup**, the champion against the cup winner, only where the game has none (Brazil, Chile, Scotland, Greece, the USA). It is a one-match super cup of two clubs (0.2.4; before, it came out as a knockout of 16). It is played in late July; in a February-to-December country (the Supercopa de Chile, the Supercopa Rei) it is played at the end of January, between the champion and the cup winner of the season just ended. When there is no cup winner yet (a new career's first summer), or the champion won the cup as well, the league's runner-up plays. Empty name: the league's name and *League Cup* / *Super Cup*. **Logo** next to each name (0.2.0): a picture for that cup; none, an emblem with the cup's initials. Changes here need **Install the modules** (or Build and install), a new Build and a new career.

**European places of the game's leagues** (Leagues → More): which positions of the Premier League, LaLiga, Serie A ... go to which European competition. The list shows the game's own places; tick **Own places for this league** to change them. A league not ticked keeps the game's places, a ticked league with no rows sends nobody.

**UEFA ranking** (Leagues → More, 0.1.7): every European league of the world -- the game's and your
new top divisions -- in one list, strongest country first. Drag a league (or **Up** / **Down**)
to change the order, untick one to give it no European place, **UEFA's order** puts the list back
to UEFA's association ranking for 2026-27. The right side shows what each league gets, and
**OK** writes it: the places of UEFA's key for 2024-27 -- rank 1 has five Champions League
places, rank 6 two and a play-off place, rank 30 one place in the Champions League's second
qualifying round and three in the Conference League's, and so on, the cup winner's Europa League place included. A world never has all 55 of UEFA's countries, so
the places of the ranks it does not have go to the next clubs of the strongest leagues in turn,
one round at a time, and every competition stays full: with twelve leagues England's 6th, 7th
and 8th go to the Champions League qualifying, say. Past the 31st league there is no place left, and
the list says so. Each qualifying round holds sixteen clubs: with all 31 ranks in a world, the
lowest ranks' places past those sixteen get none (the notes say which; ranks 26 and below really
start in the first qualifying round, which Mod Studio does not have). The qualifying places go to the rounds in the key's order, the strongest
country to the round nearest the league phase. Afterwards you can still change any league's
places by hand (*Europe* on the league, *European places of the game's leagues*): Build takes
the places, not the ranking.

**South American places** (Leagues → More, 0.1.7, read only): for every South American league, the
game's four and yours, which positions go to the Copa Libertadores, its qualifying round and the
Copa Sudamericana. The game's Libertadores places are its own (Brazil 1st-4th and the Copa do
Brasil winner, qualifying 5th-6th, and so on -- the same the game's Competition Info shows); the
Copa Sudamericana is Mod Studio's, so the list shows how many clubs each of the game's leagues
sends to it with your places in: your leagues first, then Brazil, Argentina, Chile and Colombia
one club each in turn until 32. A club already in the Libertadores or its qualifying gives way to
the next one of its league. **Check the plan** prints the same list whenever the world has a
Libertadores or Sudamericana place.

**Competition names** (Leagues → More, or My world → Cups): a new name and logo for the game's cups, super cups and continental competitions -- the FA Cup, the Champions League, the Libertadores ... -- and for the continental cups the world builds (CAF Champions League, Confederation Cup, AFC Champions League Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Champions League, AFC Challenge League, CAF Super Cup). Every stage of a competition takes the name. Empty: the game's own. The game's leagues are renamed on *Leagues* (pick a league of the game).

**Competition IDs** (Leagues → More): every competition of the world in the game, leagues and cups, with its id. The game has room for 255; My world shows how many are used.

**League order** (Leagues → More, 0.2.0): the order of the countries in Master League's Select Team and in the Kick Off / Edit team list. *By continent* is the game's order (Europe, the Americas, Asia, then Africa, each A-Z). *Every country A-Z* puts all of them in one alphabetical run, and *My own order* lets you put them any way you like (drag, or Up / Down). A country's leagues stay together, top division first, and the club competitions, the "Other" groups and Classic Teams come after the countries. Germany, the USA and Japan sit in the "Other" groups of Select Team, so they move only in Kick Off. Build the world again afterwards.

**Seasons of the game's leagues** (Leagues → More, 0.2.0, experimental): Japan, China, Brazil, Chile and Saudi Arabia play February to December in the game. Tick one and its leagues play August to May like Europe: the season starts in August, promotion and relegation happen in summer, its cups move to August-May dates and its continental places come from the table that ended in May. A division of yours under one of those leagues follows it. Colombia and the USA play Apertura and Clausura and cannot move. Build the world again and start a new career.

**First-season European clubs** (Leagues → More, 0.1.8): pick by hand
the clubs of the Champions League, Europa League and Conference League phase in a new career's
first season. Your clubs go in first and the game fills the rest; from the second season the
European places decide.

**Clubs** (a tab of My world): pick the league, then **Edit club** (name, short name, crest; or double-click the club). Everything else is under **More ▾**: **Players**, **Club of the game...**, **NewLife club...**, **New club here**, **Insert club**, **Remove club**, **Move to another league...**, **Paste
names...**, **Load names from file...** and **Import crests...**. An empty name becomes `<league> 01`, `<league> 02` ...; a club
with no crest gets a numbered badge. Kits are lent from the game's own clubs. Such a kit is a
licensed one, and Edit mode will not change it ("You cannot edit this strip"): tick **Plain kits
to change in Edit mode** on the Build tab (World options) and the new clubs borrow none, each wears a plain kit
that Edit > Teams > Strip changes like any other club's, Paste Image included.
With Kit Server installed, **Kits made in the clubs' colours** (Build tab, World options, on unless you untick it, 0.2.1)
makes each new club home, away, third and goalkeeper kits in its shirt colours (NewLife's, or the
crest's when it has none), with its crest on the chest and the shorts, for whole leagues at once
when the world goes into the game. A crest you put in later (Import crests) goes on the kits at the
next switch-on. A club with a Kit Server kit of its own, or only a numbered badge, gets none.
A kit line of your own in `map.txt` (one you set on the *Kits* tab, to a kit that is in the
library) always wins: Build makes no kit for that club, puts no package kit on it and leaves your
line switched on (0.2.4; 0.2.3 switched it off for a league package's kit at every Build).
Names keep their letters (FK Željezničar); the three-letter short name has none, as in the game,
so Č, Ž, Đ become C, Z, D there. A league's A-Z order in the game files Đakovo under D and
Šibenik under S (0.2.4). After **Build**, the mouse over a club's name shows its id in
the game (**Team ID**).

**Faces from the regen face pack for new players** (Build tab, World options, on by default):
every new player without a face of his own gets a face of the regen face pack that fits his
nationality. Off: new players keep the look the game gives them, or the one you set in the
game's Edit mode. It takes effect at the next Build.

**Manager**: in **Edit club** of a new club you can name its manager. Empty: a made-up name from players of the club's country (a Croatian club gets a name like `Tomislav Krovinović`; the same one at every Build), or a numbered one (`FL M0001` ...) for a country the game has few players of. **Manager picture** under it gives the manager a portrait (the same as **Manager portrait...** on the Players tab); *Leagues* (a league of the game) > **Edit club** has it for the game's clubs too.

**Kit colours**: **Home kit colours** and **Away kit colours** in **Edit club**: Build lends the
game's kit nearest them, and **Kits made in the clubs' colours** uses them.

**Formation**: in **Edit club** of a new club you can give it a formation of its own; *As the league* keeps the league's. The pitch under the list shows where everyone stands.

**Captain and set-piece takers** (0.2.4): Build gives every club and national team that has none
a captain (a player with the Captaincy skill, else the strongest and most experienced one) and
its takers for penalties, free kicks and corners, from the outfield players of the first
eleven. A club of the game that has its own keeps them. A world built before 0.2.4 has the
goalkeeper as captain everywhere: Build it again and start a new career.

**Home stadium** (0.1.7): in **Edit club**, a stadium of Stadium Server's library for the club; the slot and the name are filled in from the folder, change the name if you like. It is written to Stadium Server's `map_teams.txt` when the world goes into the game (and when the world in the game is built again), so a new club's id never has to be looked up. A line of your own for the same club is switched off meanwhile, and on again when the club no longer has one here. *Leagues* (a league of the game) > **Edit club** has it for the game's clubs too. Stadium Server has to be installed (the *Stadiums* tab), or SPFL26's own stadium module (`common\stadiums.lua` with its `content\stadiums` folder): since 0.1.8 Mod Studio writes there when Stadium Server is not installed. A stadium of the game picked as a home stadium is lit properly in the match (0.2.4; before, it could be completely dark): Build again for a world made before.

**Clubs the game already has.** A place of a new league can hold one of the game's clubs instead
of a new one: select the place, then **More → Club of the game...**, and search by name, short
name or team ID (**Only clubs in no league** narrows the list). The **Club of the game** window
says under the list where the club plays. The club keeps its name, crest, kits, manager and
players, and plays in your league only. When it plays somewhere in the game (a league, a cup, the
Europa League ...), you pick who takes its place there: **Its place goes to a club of the game
that plays in nothing:** (pick one from the list), or **Its place goes to a new club, named:**
(type a name). **It keeps its places in continental competitions** (0.1.8, #84) lets it go on playing the Champions League, Libertadores or AFC Champions League it is in: a club the continent is all it plays in the game then just moves, and one that also plays a league of the game hands only the league and cups to the club you pick. From the second season on your league's places decide who goes. A pre-season tournament (the *Pre-season friendly Cups* of SPFL26) does not count: the club keeps playing it, as the Premier League's clubs do (0.1.7). **Edit club** on a club of the game changes its name, crest, manager's portrait and stadium, as on *Leagues* for a league of the game (0.1.7). That way no competition of the game changes its number of clubs; the
game's leagues keep their dates only with the number they were made for. National teams, the
classic and default teams and clubs with fewer than 18 players cannot be picked. **New club
here** (in **More**) gives the place back to a new club; it is greyed out unless the club picked
is a club of the game in that place (0.2.4). The club no longer shows under the Master League's
*Other ... clubs* groups.

**NewLife club...** (0.1.8, #83, in **More**) puts clubs of the NewLife Database, with their squads, in the selected place and the places after it: tick one or more clubs (search by club or by league) and each takes its place in order. A league you made by hand gets real clubs that way. It uses the NewLife folder you opened last; the first time, open it on the *NewLife Database* page.

**Insert club** and **Remove club** add a place before the selected club or take one out (10 to
24 clubs); names, crests, managers and player changes move with their clubs. Check the league's
European places, then **Build** again. Any change to a league's clubs needs a **new career**.

**Move to another league...** (0.1.7) takes the selected new club to the end of another new league, with its name, short name, crest, manager, formation, kits, NewLife id and player changes; the league it leaves keeps one club less. A club of the game moves with **Club of the game** instead: take it out of one league, put it in the other.

**The game's leagues** (pick one on *Leagues*): a new name or logo, then **Keep league changes** (**Undo league changes** goes back); **Edit club** for a club's crest, name, manager's portrait and stadium. The Clubs list shows how many players each club will have: its squad, less the players removed or signed by another club, plus the ones added and signed. Such a change is kept in your world's file at once, like every other change.

**Import crests...** (0.1.8, *Clubs* → More; for the game's leagues *Leagues* → More): crests for many clubs at once. Pick a folder of pictures; each is matched to a club by its file name -- the club's name (`Alianza Lima.png`, `alianza_lima_r_l.png`) or its team ID (`2287.png`, the crest packs' `e_2287_r.png`). A name matches only on whole words, and a national team takes a picture by its team ID only (0.2.4; before, "termalica" could go to Mali). Matches of 60% or more are ticked: the same name, written any way (`F.C.`, `Football Club` and the like do not count). When the folder is named after a country (`Africa/Ghana/...`) or a league of your world, or the file name starts with one (football-logos.cc's `poland_cracovia_...`), a club of that country goes first and a club of another country is never ticked. A name only inside the other is ticked (65%) only when it is the one club of that country it fits (`mostaganem` for *ES Mostaganem*); otherwise (`chippa-united` for *United Sport FC*, or no country known) it is a suggestion at 50%, unticked. Check the unticked ones and the *Match* column, and untick a wrong one before **OK**. A club that already has a crest keeps it unless **Replace crests already set** is ticked. The pictures stay in that folder and Build reads them from there, so keep it. (Matching by name is an idea from Xxspedd's crest script.)

**Swap leagues with a club...** (0.1.7, *Leagues*, a league of the game → More): two clubs of the game's leagues trade places -- a promoted club for a relegated one, a club of one country's league for one of another's. Each takes the other's places in the league, the cups and the European competitions, so every league of the game keeps its number of clubs. A club in a new league of your world cannot swap too. **Undo club changes** takes the swap back. Then **Build** again and start a new career.

> **Edit file.** If the game's save folder has an Edit file (`EDIT00000000`), it overrides club
> names. Move it somewhere else to see your names.

### Players

**Players** (a tab of My world) changes the squad of any club: the new clubs of your world and the game's own.
Pick a club (or **More → Players** on Clubs), then a player:

- **Name**, **shirt number**, **position** and the positions they can play (A = natural,
  B = can play there), stronger foot, height, weight, age, nationality, playing style;
- all **abilities** and **skills** (the names are the game's own);
- **Rating**: the rating of the list, made of the abilities the position leans on. Changing
  it moves every ability of the player by the same amount. A player of a new club has no
  name until the Build numbers him (FL P00001 ...); type one in **Name** to give him yours;
  since 0.2.0 such a squad starts at its division's level (about 72 in a top flight down to 57
  from the fifth division);
- **Face**: **Choose...** a face folder (section 8.1). **Clear** gives the game's face back. A
  new player without one gets a face of the regen face pack that fits his nationality, with its
  portrait (0.1.5.5, with the modules installed and `fl26regen` on, section 5). A face made for another player brings that
  player's look of the body too, so the arms and legs have the face's skin colour (0.1.9);
- **Portrait**: **Choose...** a picture (PNG or JPG) for the player's small portrait in the squad
  lists, without a face of his own. Build makes it 180 x 180; it wins over a face folder's portrait;
- **Order up / Order down**: the squad order. The first eleven start the match;
- **Add player** (a copy of the player you pick, with a new id; clubs of the game only),
  **Remove from club** (press it again to take it back). A new club keeps at least 18 players,
  the ones signed for it counted too; clubs of the game have no minimum;
- **Best eleven** puts the strongest player at every place (a player who can also play
  the place, but is registered elsewhere, counts with 6 off, and he stays for his own
  place when it would be left short); **Squad level...** (in **More**) raises or
  lowers every ability of the whole squad;
- **Pitch** (new clubs): the first eleven in the club's formation. Drag a player from the list
  onto a place, or drag one place onto another to swap the two; a click on a place selects the
  player standing there. The formation Build picked for the club shows here; when you change
  its order, the club keeps that formation;
- **Export CSV... / Import CSV...** (in **More**): edit a squad in a spreadsheet. Export first, change the
  cells, import the same columns back.
- **Import a squad from a table...** (in **More**): any table of players becomes the club's squad -- one
  typed by hand, a squad list copied off a website, or an export of another football game. The
  columns are recognised by their names (name, position, age or birth date, nationality,
  height, foot, shirt number, overall, and any ratings) and shown so you can fix one that is
  wrong. What the table does not have comes from the game's own players of the same position
  and rating; ratings on a 1-20 scale are stretched to the game's 40-99. The table's
  players take the club's places in squad order: a new club keeps its 30 places (fewer
  players = the rest leave, down to 18), a club of the game gains or loses players to match.

Every change is written into the world when you **Build**; the game's files stay as they are.
**Undo changes to this player** and **Undo all changes of this club** go back to the game's.

The club list also has **National teams** and **Other clubs (no league)**: the teams the game keeps outside any league (national sides, clubs that only play a cup or a continental competition). Their players are edited the same way.

#### Transfers, national teams, ids, the manager's portrait

- **Sign players...** (a club): a list of every player of the game and of your new clubs, with
  a nationality filter and a name search; pick several with Ctrl or Shift. They move to this
  club: their old club loses them (a transfer). **Transfer to...** does the same from the other
  side: the selected player moves to the club you pick. The list shows *from ...* on the club
  that gets him and *to ...* on the club he leaves; **Remove from club** on either row calls the
  transfer off. A club has at most 40 players. If a club ends up with more than 40 (a national
  team more than 26), Build keeps its first 40 and goes on, and the Build log names the club and
  the players left out; when the club is in your world twice, it names both leagues.
- **Call up players...** (a national team: pick *National teams* in the league list): the list
  opens on the team's country. The players join the national squad **and stay at their clubs**,
  as in the game. **Remove from club** drops a player from the national squad (not from his
  club). A national team has at most 26 players; a player is in one national team at a time.
  Your squad is written into the game's data, but in a Master League career the game picks its
  own national squads, so there your call-ups do not stay.
- A player who joins goes to the end of the squad order with a free shirt number; the squad he
  left closes its order up.
- **Player ID** column: every player's id -- the game's own, the one you typed, or the one the
  last **Build** gave a new player (build once before you make minifaces or faces for new
  players). **Export CSV...** writes it as `player_id`; Import CSV ignores that column.
- **Club ID** (next to the club) and **Player ID** (Basics tab): for your **new** clubs and
  players only. Empty = the next free id at Build. Type one when a kit, crest or face pack was
  made for a certain id. Club ids: from the first id after the game's clubs (71578) up to 81919;
  player ids: above the game's highest up to 399999; never one the game or another new club or
  player already has. The id is used everywhere the world refers to the club or player (squads,
  competitions, kits, crests, manager, faces). The game's own clubs and players keep their ids:
  its kits, faces and your saves are tied to them.
- **Players keep their ids when you build again** (0.2.4). Build finds each of the world's own
  players by who he is (his NewLife id, else his name and birth date) before his place in the
  squad, so a player who moved up the squad or changed clubs keeps his id, and an old career does
  not show him as somebody else.
- **Manager portrait...**: a PNG or JPG for the club's manager. Build makes it 256 x 256 and puts
  it at `common/render/symbol/coach/coach_<manager id>.png`, the game's own place for manager
  portraits. Press it again to take the picture away.

### 8.1 Faces

A face mod is a folder like this (the way face makers share them):

```
<any name>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (or <id>.dds, optional)
```

Choose that folder for a player. At **Build** the face is copied into the world and pointed at
the player, so it works for a new player whose id did not exist when the face was made, and it
never replaces a face of the game. Without a portrait the small player picture in the menus stays
the empty outline; the face itself still shows. A folder with more than one face inside is refused: pick the
one face you mean.

### 8.2 Build, switch on, play

**Keep the world's own Team.bin.** It is in the world folder and holds the world's clubs and its play-offs. Replacing it with the game's own Team.bin drops both, and the line-ups only look fixed because the world's clubs are gone (GitHub #75). Build the world again instead.

**Build** is the first tab of **2. My world**. A note at the top says it is for modders: to play
a ready modpack you do not need it. Under it: the file your world is kept in, the buttons **New
world**, **Open a world...** and **Add leagues** (for a world of your own), and the big
**Build and install** button.

**Build and install** does 0, 2 and 3 below in one press, then shows what is left to do: a
**Build finished** window with a tick for **World built**, **Leagues and clubs**, **Modules
installed and switched on** and **In the game**, and under **Before you play** a reminder to start
a new Master League. It can also **Move the Edit save aside** (an Edit save from before the Build
hides the new names and squads) and **Close the game**. Home's card has a **Go to Build** button
that takes you here. While the world builds, the state line of My world and the bottom bar show
the time so far and the step it is at (`Building... 3:12 · squads: filling them`), and the
window stays free to use. Or step by step, under **Step by step, and Export the world** on the
**Build** tab:

0. **Install the modules** — once, and again after a new version of the program. The files it
   replaces are kept in **Restore points**.
1. **Check the plan** — what will be made; nothing is written.
2. **Build the world**.
3. **Switch it on** — puts it in the game (the active world in `sider.ini`).
4. Start the game, come back and press **After a start: check**. It reads `sider.log` and says,
   module by module, whether the world was taken.

**Activate** on another world's card in My world does step 3 for that world (and swaps the save
folder, section 3.1). The world in the game shows **● Active** instead. Start a new Master League
after activating a different world.

**A new logo or crest builds in seconds** (0.2.4). When only pictures changed since the last
Build (a league's or cup's logo, a club's crest, a country's flag), Build draws just those again
and leaves the rest of the world as it is. Any other change (a name, a club, a player) is a full
Build. A world from a zip is built in full once on your PC; after that its picture changes are
quick too.

**A ready world is not built here** (0.2.4). A world installed from a zip is built already, and
Build would replace it with the world open in Mod Studio. So while a ready world is in the game,
the Build steps are greyed out with a note, Home says **Ready to play**, and Build explains what
to do instead: press **Start the game**, or put your own world in the game first (**Activate**
on its card). Another world (NewLife, a new world) can still be built while the ready one is on:
Build asks first and says it switches the ready world off; **Activate** on its card brings it
back, with its careers. To change the ready world itself: **Make it editable...** (section 3.1).

**Include the Conference League** (Build tab, under World options, on by default) also builds the
Conference League: a league phase of 36 clubs and a February play-off, like the other two. The
Champions League and the Europa League get their league phase of 36 and their February play-off
either way. Off: no Conference League. (Mod Studio 0.1.3 and earlier left the Champions League and Europa
League in the game's groups of four when this was off, which the mod cannot run -- they broke;
Checks flags such a world: build it again.) **Conference League logo** next to it: your own picture
for it; empty: a UECL emblem is drawn (the game has none for it). **Conference League name**
under it: what the game calls it, *FL Conference League* when empty (type *UEFA Conference
League* if you like); a new name needs the world built again. Both are used by **Build only the
European cups...** too.

> **European places.** The places you give your leagues come after the ones the game's own
> leagues have. Each competition takes 36 clubs; places past the 36th get nothing, and
> **Check the plan** says so. New leagues with no places send nobody to Europe, and Home
> warns about it. The title holders come first: the Champions League and Europa League winners
> take two of the Champions League's direct places, the Conference League winner one of the Europa
> League's. The league-phase draw follows UEFA's rules: no club meets a club from its own
> country, and at most two of its opponents come from any one other country.
>
> **The August qualifying.** A *qualifying* place puts the club in the August qualifying of
> that competition: up to three rounds (0.1.7) -- the second qualifying round (days 220 and 225),
> the third (229 and 236) and the play-off (243 and 250; the Champions League's 244 and 251) --
> each of 16 clubs over two legs, the eight strongest squads seeded (second leg at home), two
> clubs of one country kept apart. Winners go on to the next round, from the play-off into the
> league phase. Losers drop as UEFA's do: *Champions League qualifying*'s play-off losers to the
> Europa League, its third round's to the Europa League play-off, its second round's to the
> Europa League third round; *Europa League qualifying* the same way into the Conference League;
> *Conference League qualifying*'s losers are out. The first places listed go to the play-off,
> later ones to the earlier rounds. How many rounds a world gets follows from its places, and
> every Conference League round needs 8 clubs more: 116 places in Europe for the three
> play-offs alone, 132 for all nine rounds. With the game's own places it is the play-offs
> alone; Build's summary says which rounds a world gets (*August qualifying*). Every play-off
> takes 8 places off the direct entrants of the competitions its winners and losers go to: with
> all three, the Champions League takes 28 clubs directly, the Europa League and the Conference
> League 20 each. A place past those is played in that competition's qualifying. Your leagues'
> qualifying places come before the game's (Portugal, Scotland, Greece, Denmark ...).

Then **start a new Master League** (or Become a Legend) career. The new leagues are under their
country in Select Team and Kick Off. In the Kick Off and Edit lists a new Asian country comes
before *Other Clubs (Asia)*, a South American one with the game's (after Colombia, before MLS,
0.1.7), a CONCACAF one after MLS, and African and Oceanian ones (the game
has no section for them) after Asia.

> **Other continents' cups.** When your leagues send clubs to the CAF Champions League, the
> CAF Confederation Cup, the AFC Champions League Two, the AFC Challenge League, the Copa
> Sudamericana, the CONCACAF Champions Cup or the OFC Champions League (the last three new in
> 0.2.0), **Build** makes those cups too. Each gets 32, 16, 8 or 4 clubs: your leagues' places
> first, then the game's own leagues of that continent (Asia, South America, and MLS for the
> CONCACAF one) fill it; for the AFC Challenge League that is the J1 League's 11th-14th, the
> Chinese Super League's 10th-13th and the Saudi Pro League's 11th-14th. With 8
> or more it plays groups of four and then a knockout; below 8, a knockout only. The CONCACAF
> Champions Cup is always a knockout, of 16 clubs at most, like the real one, and two clubs of
> one league do not meet in its first round where that can be avoided. They are filled at the
> end of August, from the league tables. A club already in the Copa Libertadores, its
> qualifying round or the AFC Champions League is not drawn into them. A CAF or OFC cup with fewer
> than 4 places takes the next CAF cup's places first (with two and two, the CAF Champions
> League gets all four), then the next positions of your leagues. **CAF Super Cup** (Build
> tab, World options, on by default) has the winners of the two CAF cups meet once in late July, from a
> career's second season on.
>
> A league that can send a club to the Copa Libertadores, the AFC Champions League or the Club
> World Cup keeps clear of their match days (0.2.4): no league round the day before or after.

> **Country cup draw** (Build tab, World options) decides how the national cups of your leagues are drawn.
> *Seeded* (the default): the top division's clubs get the byes and the later rounds, are spread
> evenly over both halves of the bracket, and meet the lower leagues' clubs rather than each
> other in the early rounds. *Random*: a blind draw. *Off*: the game fills the bracket in list
> order, which puts every top club on one side. In the world file it is the line
> `cupdraw seeded|random|off`; `cupdraw <cup regulation> seeded|random|off` sets one cup.

> **Saves belong to a world.** A career saved with one world in the game needs that same world
> to load. With **Each world keeps its own careers** on (the default, section 3.1), Mod Studio
> keeps each world's careers apart for you.

**Your world saves itself** a moment after each change (the bottom bar says **Your world is
saved**): into its own `.json` file when it has one, otherwise into
`%APPDATA%\FL26ModStudio\recipes\<world>.json`, and Mod Studio opens it again when it starts.
**File → Save your world as...** saves a copy under another name, **File → Open a world...**
brings one back and **File → New world** starts an empty one.

**Build only the European cups...** (Build tab, World options; **Only the European cups...** on Home) builds a world with nothing but the new
Champions League and Europa League -- league phase of 36 and the February play-off -- and the
Conference League when **Include the Conference League** is ticked. No new leagues; the game's
clubs and leagues stay as they are, and your world is not changed. It asks for a world name
(`_FL26Euro` by default), builds it and offers to activate it. Only one world can be in the game, so it
is instead of a world with new leagues: a world with new leagues already has the new format.

> **Exhibition leagues and Master League.** A league ticked *Exhibition only* never plays a
> Master League season, but the game has one team list for Kick Off and Master League, so its
> clubs still show when you pick your club for a new career. Do not start a career with one of
> them. **Check the plan** and **Build** say so.

### 8.3 Limits

| | |
|---|---|
| New leagues per world | No fixed number. Each league, cup and super cup of the world takes one of the game's 255 competitions (the game uses about 90 itself); **2. My world** shows how many are used. Our test world plays 86 new leagues. |
| New countries | 99 |
| Clubs per league | 10 – 24 |
| New clubs in all | about 1,500 (the line at the bottom of the NewLife Database page says how many fit in your game) |
| Times clubs meet | 1 – 4 |
| Split leagues | 2 per world |
| Divisions in one country | down to the 7th |
| Players per new club | 30 at the start (a very big world gets smaller squads, never under 22); remove down to 18; signed players bring it up to 40 |
| Players per national team | 26 |
| National cup | the top division and the one below, up to 44 clubs. Up to 32 the sizes are 2-16, 18, 20, 24, 28, 30 and 32 -- the largest that fits (22 clubs give a cup of 20); 33 to 43 become 32; 44, or a size a shipped cup has, stays; more than 44: the top division alone |

### 8.4 NewLife Database: real clubs and players

The NewLife Database is a separate download with real clubs and players for new leagues: names,
birth dates, positions and ratings on the game's scale, and the clubs' colours. Every club and
player in it has an id of its own that stays the same in every version of the database. It is
not on GitHub: get it from the NewLife channel of our [Discord](https://discord.gg/StQqtk3G3M).
It comes in parts, one per continent (a big one in more than one), plus *Free agents*, each
under 10 MB. Download only the parts you want.

1. Put the parts you downloaded in one folder. Do not unpack them: Mod Studio reads the zips as
   they are. (They are LZMA zips: 7-Zip opens them, Windows' own zip viewer does not.)
2. **2. My world → NewLife Database** (the button on the right of the tabs), then **Open
   NewLife Database...** and pick that folder. (Or drop the folder on **+ Add...**.) The list
   shows every league of those parts: country, clubs, clubs the game already has (*In game*),
   players and level. Click a league to see its clubs. Click a column header (League, Country,
   Clubs, Players, Level) to sort by it, again to turn the order round (0.2.0); the list opens
   sorted by country.
3. Select one or more leagues (Ctrl or Shift for more) and press **Add to your world**. Each
   becomes a new league with its clubs and their squads, the top division of its country. Change
   its division, format, European places and the rest on *Leagues*, like any other league.
4. **Build and install** and start a new career (section 8.2).

- **Your own line-up** (0.1.7): untick a club in the list on the right to leave it out, and
  **Add a club from another league...** to bring in clubs of any league of the release -- this
  season's first division is last season's with two promoted clubs, say. The league's row gets a
  `*`. A club can be in one league of your world only. If it is already in one of your leagues
  under another name, the message names that league and the name the club has there.
- A league takes 10 to 24 clubs, its new clubs and the game's own together; the others are grey. A league of the game itself (the Premier League, the Championship ...) is grey too (0.1.9): it is in the game already, bring it to the NewLife season with **More → Bring the game's leagues to this season...** below. The line at the bottom counts the new clubs
  of your world against the number the game takes.
- Clubs the game already has join the new league as clubs of the game (section 8, *Clubs the
  game already has*), in its last places, with their own names, crests, kits and players. One
  that also plays a competition of the game (Basel and Young Boys play the Europa League) needs
  the club that takes its place there: *Clubs*, pick it, **More → Club of the game...**. Build says
  which ones until then. A club whose only competition of the game is continental (Ludogorets in
  the Champions League qualifying) keeps playing it on its own (0.1.9).
- A player the game already has (the same player under the same name, Urbański at Górnik in
  the game and at Legia in NewLife, say) moves to the NewLife club instead of being made a
  second time (0.1.7): he keeps his face, name and id and takes NewLife's position and ratings.
  He stays where he is when his old club would drop below 18 players, or when an earlier league
  already took him; then he is left out of the NewLife club, not copied (0.1.8).
- A NewLife club takes a world id of its own (0.1.8), in the block the game reads for clubs,
  counting up after the ids the builder gives its own clubs. The mouse over its name on *Clubs*
  shows it (**Team ID**), and a Kit Server's `map.txt` is keyed on it. A world built before 0.1.8 must be
  built again and the career started new for the kits to follow. From 0.1.8 a club keeps the id
  of its first Build (your world remembers it): removing, adding or updating another league no
  longer moves it.
- **A newer NewLife version** (0.1.8): put its parts in a folder (not mixed with the old ones),
  **Open NewLife Database...** that folder and press **More → Update my leagues to this version**. Every
  league you added from an older version is listed with what changes (*16 clubs now, 18 in
  NewLife 1.3 (5 new, 3 not in it)*) and a **Keep my clubs** box: ticked, the league keeps its
  clubs; unticked, it gets the clubs it has in the new version. Either way the squads come from
  the new version, and the league keeps its name, division, format, European places and cups; a
  club that stays keeps its manager and a crest you picked, and clubs of your own you put in the
  league stay. The squads' abilities, positions and the rest come from the new version; a face
  you linked or a portrait you picked on *Players* stays with a player who is still at the club
  (0.2.0, #111). A club of the game whose place went to another club stays a new club in your
  league (0.2.4). Then Build and start a new career.
- **The game's own leagues in the NewLife season** (0.1.8): with a NewLife Database open, press
  **More → Bring the game's leagues to this season...**. Every league of the game the release has is
  listed with what happens to it, each with a box. A club that went up or down between two
  leagues of the game swaps places with one going the other way (Burnley to the Championship,
  Coventry to the Premier League), as *Swap leagues with a club...* does. A club that went down out
  of the game's leagues (Leicester to League One) becomes the club that came up in its place
  (Bolton): its name, short name, crest and squad; its kit, stadium and manager stay. When the
  database has no crest for that club, the place gets the shield of the new club's shirt
  (0.2.4). Every club of the ticked leagues gets its NewLife squad: players the game has join
  from their old club, players it has not are added, and the players NewLife has at another
  club leave. A player NewLife still has at this club stays, as long as the club has room (40
  at most; 0.2.4); the Build log names anyone it had no room for. Ratings are put on the game's
  scale, measured on the players both have, so a star lands where the game rates him (0.2.0;
  before, the top end ran 2 to 4 higher). The leagues keep their number of
  clubs, their format and their cups. Clubs you already changed by hand (a swap, a rename, a
  club of a new league, player changes) stay as they are. Doing it again with a newer version
  replaces what the older one did; **More → Undo the game's leagues** takes it all back. Build and start
  a new career.
- A NewLife club gets a shield crest in its colours and the kit of the game closest to its
  colours, until you give it your own (**Edit club**).

## 9. League packages: share a whole league

A modder makes a league once — clubs, names, crests, logos, squads, faces — and shares **one
`.fl26pack` file**. Anybody adds it to their own world and builds.

The **League packages** page is under **2. My world → More ▾ → League packages**. It lists the
packages in your world, with **Add a package...**, **Make a package...** and **Remove from your
world**.

**Make a package** (**Make a package...** on that page, or **File → Make a league package...**):

1. Name, author, version and a short description.
2. Tick the leagues that go in (**Select all** / **Select none** over the list). A league below
   another new league must go with it.
3. Optionally **also my changes to the game's own leagues, clubs and players**.
4. **What goes in** (0.1.8): everything is ticked; untick what you do not want to share -- **Squads**,
   **Player faces and portraits**, **Crests and league logos**, **Managers**, **Kit colours**, **Home
   stadiums** (the Stadium Server line, not the stadium itself), and (0.2.1) **Kits** (the clubs'
   Kit Server kits) and **Scoreboards** (each league's Scoreboard Server scoreboard). Kits and
   scoreboards are taken from your game as the world is now: whatever kit-server\map.txt and
   scoreboard-server\map_competitions.txt give its clubs and leagues. A package without squads goes on top
   of a squad database that is updated on its own, like NewLife, without putting old squads back.
5. **Save the package...**. The file (`.fl26pack`) holds the pictures, faces, kits and
   scoreboards, not paths on your computer.
   Whoever adds it gets the kits and scoreboards in place with their own team and league ids when
   they Build (Kit Server / Scoreboard Server must be installed); a club they gave a kit line of their
   own on the *Kits* tab keeps that kit (0.2.4), and a package kit stays with its club when a club is
   removed, inserted or moved, or the league is updated to a newer NewLife. Kits add about 10 MB per league and
   a scoreboard about 7 MB, so such a package is often over Discord's 10 MB limit: share it through a
   cloud service (Google Drive, Dropbox, MEGA ...); the program says so when the file is bigger.

**Add a package** (**Add a package...** on that page, **Add a league package** under **Quick
actions** on Home, **File → Add a league package...**, **+ Add...** in My world, or drop it on
**Import your world**, where **Build and install** then starts by itself):

1. The program shows what is inside and asks. A package of several leagues lists them, all ticked:
   untick the ones you do not want (0.2.1). A league below another league of the package brings that
   one with it. Under **What to take** you can also untick parts of it (scoreboards, kits, crests,
   faces ...), e.g. to take the scoreboards from another package.
2. A league with a name you already have: the program asks, and adds it as `Name (Package)` (no: nothing is added).
   A package made without squads goes onto that league instead: its crests and managers land on the
   clubs of the same name, your players stay, and the program says how many clubs it found.
   A package your world already has (the same name) is replaced by the new version (0.1.7): the old
   one's leagues, clubs and player changes go out, the new ones come in.
3. **Build and install**.

Ids are given out when each person builds, from what their own game has, so a package works next
to other packages and next to your own leagues. **Remove from your world** takes a package out
again, including the changes it made to the game's clubs. If a package changes a club your world
already changes (a NewLife club, say), a player both add is added once, and the package's
signings and removals come along (0.2.4).

A league placed below one of the game's leagues works for everybody with the same game version.

### 9.1 Export the world: a built world for another PC

A package needs the other person to build. To hand over the world exactly as you built it,
press **Export...** on the world's card in **2. My world**, or **Export the world...** under
**Step by step, and Export the world** on the Build tab (after the world is built). It saves one
`.zip`:

- `SiderAddons\livecpk\<world>\...`: the whole world folder, with its **world file**
  `fl26world.txt`. The `newfaces` / `faceapp` lines in that file list the new players who get a
  generated face. Without them every new player looks the same.
- `SiderAddons\content\kit-server\<world>\...` and `...\scoreboard-server\<world>\...`: the
  world's **kits** (the Kit Server kits of its clubs, also the ones made from colours and crests)
  and **scoreboards**, each with a `map.txt` / `map_competitions.txt` of only this world's lines.
  Import your world adds those lines to the receiver's maps (a line of theirs for the same club is
  switched off and comes back when the mod is removed). The kits go to the Kit Server the
  receiver's game loads (`content\kits` for SPFL26's own one). A club of the world that wears
  a kit from another pack on your PC (SPFL26's Other Europe, a modpack) takes a copy of that kit
  along, in `<world>\_kits\`, so the receiver does not need that pack.
- `SiderAddons\content\scoreboard-server\<world>\_packs\...`: the **scoreboards of other packs**
  that the switched-on map lines on your PC give the world's competitions (a modpack's boards
  for its leagues, cups and super cups). They come with their map lines, pointed at
  `<world>\_packs\`, so the receiver does not need that pack either. Menu themes are not part of
  a world zip: the game's own menus stay, even when a pack's theme is switched on on your PC.
- `READ ME - FL26 world.txt` and `fl26worldpack.json`: what the receiver needs.

**The receiver needs Mod Studio's modules with the face pack** (`modules\fl26regen_faces.bin`):
installing the zip on **Import your world** puts them in (or **Home → Install now**). The faces
come from that pack, so the zip does not carry them.

To install it, drop the zip on **Import your world** and press **Install the world**. Mod Studio
installs its modules, copies the world, puts `fl26world.txt` in `SiderAddons\modules` (where
`fl26regen` reads it) and puts the world in the game; a newer version of a world you have
replaces the older one. It ends with **Ready to play** and a final check list. Then start a new
Master League career. **Remove** (under **In the game now**) takes the world out again and puts
the previous world file back.

A modpack names its clubs' home stadiums by the folders of its maker's stadium pack. When your
stadium pack keeps a stadium in another folder, Mod Studio finds it by its name; a stadium you do
not have is left out (the club plays where the game puts it), and the final check says how many
clubs have theirs.

**Changing an installed world.** `fl26worldpack.json` holds only the world's name and what it
needs, but the world folder carries `leaguebuilder-plan.json`. When Mod Studio starts with that
world in the game and the game's tables unpacked, it makes your world from that plan and opens
it, so the receiver can see the world's leagues. To change it and build it again on their own
tables, they press **Make it editable...** in My world first (section 3.1).
It is close to the original, not the same: the leagues, clubs, names, crests, Europe, cups,
player changes and the Conference League come back; pre-season cups, cups of the game's
countries, competition names, the game leagues' European places, the league order and the
first-season European clubs do not. Pictures and faces point to the sender's PC: Build draws a
badge for a missing picture and says which.
Mod Studio does not install over a world of the same name that was built on that PC: rename that
world on its card first.

## 10. Tools

**Diagnostics** (**4. Tools**) **— Run the checks** looks at the whole setup: content folders that are on but
missing, modules in the wrong order or switched on twice, map lines that point at nothing,
the world in the game (tab **Your world in the game**; only one world should be on), and the
last `sider.log`. **Copy a report**
puts it all in the clipboard to paste in a forum post or a bug report.

**Restore points** (**4. Tools**): every file the program changed, with the copy from before.
**Put this copy back** restores it. Copies live in `SiderAddons\ModStudio\backups`. **Clean
up...** removes old ones, and always keeps the oldest copy of a file (the one from before Mod
Studio). Deleted and renamed worlds and the copy of your save folder are listed here too.
**Delete this copy for good...** removes the copy of a deleted or copied world for good and frees
its space (it asks first and says how much); after it, that world can not be put back.

**Put Sider back as before Mod Studio...** (Restore points, and the **Game** menu) gets everything
back: it puts back every file Mod Studio changed as it was first (`sider.ini`, CommonLib, the map
files) and takes out what it brought (its modules, the face pack, the worlds and mods installed
with it). Nothing is deleted: it is kept in `SiderAddons\ModStudio\reset-<time>`, and **Undo the
last reset** puts it back.

**Settings** (**5. Settings**): **Game folder**, **Sider folder** (when there is more than one),
**Language**, **Master League careers** (**Each world keeps its own careers (the save folder is
switched with the world)**, section 3.1), **The game's tables** (**Unpack the game's tables**,
**Use another tables folder...**, section 2) and **Open the program's settings folder**.

## 11. When something is wrong

| What you see | What to do |
|---|---|
| *sider.ini not found* | Settings → Game folder: pick the folder with `FL_2026.exe`. |
| *no game tables* | Settings → Unpack the game's tables. |
| *Access is denied*, or Mod Studio says it cannot write into the game folder | The game is under Program Files: press **Restart as administrator**, or move the game to a folder of your own. |
| Mod Studio says a DLL of its modules is missing (`fl26swiss.dll` ...) | An antivirus took it. Add the `SiderAddons` folder as an exclusion in the antivirus, then **Install now** again. |
| A mod does not show in the game | Diagnostics → Run the checks. A content folder higher in the list may have the same file. |
| The game does not start after a change | Restore points → put `sider.ini` back, or switch to a profile that worked. |
| The new league is not in Select Team | Start a *new* career; old careers keep their old leagues. |
| My careers are gone after I switched worlds | They are in `save_<world>` next to the save folder: activate that world again (section 3.1). |
| The goalkeeper is the captain of every new club | The world was built before 0.2.4: Build it again and start a new career. |
| The crest on the shorts of a drawn kit stands sideways | The kit was drawn before 0.2.4. Delete the `kitmaker.txt` files in `SiderAddons\content\kit-server\<your world>` and press **Build and install** again: the kits are drawn again with the crest the right way. |
| Club names are the game's | An Edit file overrides them (section 8). |
| *your leagues send nobody to Europe* | Leagues → pick the top division → **Edit league...** → Europe (the **Top flight** button fills the usual three), then Build again. |
| *the Conference League is on, but its tables are missing* | Build the world again: it was built before the option, or with it off. |
| The Build steps are greyed out | A ready world from a zip is in the game. **Activate** your own world first, or **Make it editable...** (section 8.2). |
| A face does not show | The folder must hold `#Win\face.fpk`; Build again after choosing it. |
| Anything else | Diagnostics → **Copy a report**, and post it with `SiderAddons\sider.log`. |
