# FL26 Mod Studio — user guide

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
  `pack` folder and the `README` files stay next to `FL26ModStudio.exe`.
- **Close the game** while you change things. Sider reads its setup when the game starts.

The window is in English. **Settings → Language → Hrvatski** switches it to Croatian.

## 2. First run

1. **Settings → Game folder**: press `...` and pick the folder that holds `FL_2026.exe`.
   The line under it says whether `SiderAddons\sider.ini` was found.
2. If you want new leagues or player changes: **Settings → Unpack the game's tables**. It
   reads the game's clubs, leagues and players into a working folder (a few seconds). Do it
   again only after a game update.
3. Open **Overview**. It shows your setup at a glance and lists problems. Double-click a
   problem to open the page that fixes it.

**Updates.** A few seconds after it starts, the program asks GitHub whether a newer FL26 Mod
Studio is out, and says so only when there is one. **Download and install** fetches the new zip,
checks it against the release's checksum, closes the program, puts the new files over the old
ones and starts it again. Your settings, projects, restore points and the game are not touched.
**Help → Check for updates** asks at any time. If the program sits in a folder Windows will not
let it write to (such as Program Files), it opens the release page instead: unpack the zip
yourself, or move the program to a folder of your own.

## 3. The pages

The list on the left has four groups.

| Group | Pages |
|---|---|
| **Manage** | Overview, Install mods, Content folders, Lua modules, Profiles, Restore points |
| **Game content** | Stadiums, Kits, Balls, Commentary, Music, Other content |
| **League Builder** | New leagues, New clubs, Game's leagues and clubs, Players, League packages, Build |
| **Tools** | Diagnostics, Settings |

## 4. Install mods

Drop a downloaded mod on **Install mods** (`.zip`, `.7z`, a folder, `.lua`, `.cpk` or
`.fl26pack`), or use **Choose a file...**.

The program looks inside and lists each part: what it is and where it will go.

| Part | What happens |
|---|---|
| Content folder (livecpk) | Copied to `SiderAddons\livecpk\<name>` and added to `sider.ini`. |
| Content server files | Copied into the server's `content` folder. Its **map file is merged into yours**: your lines stay and the mod's new lines are added. For a club you have already mapped, the choice next to **Install** decides: *use the mod's*, or *keep mine, add the mod's after*. |
| Lua module | Copied to `SiderAddons\modules` and switched on in the right place of the order. |
| Packed .cpk | Unpacked into a content folder on install. |
| League package | Added to your League Builder recipe (section 9). |
| DLL | **Not installed.** A DLL runs with the game's rights; install one only from a source you trust, by hand. |

Give the mod a name, choose whether new content folders go on top (they win) or at the
bottom, tick what you want and press **Install**. The list below shows every mod installed with
the program. **Remove the mod** deletes the files it added and puts back the files it replaced.

## 5. Content folders and Lua modules

**Content folders** lists every `cpk.root` line of `sider.ini`. Sider looks a file up from the
top down, so the folder higher in the list wins when two have the same file.

- Tick or untick a folder to switch it on or off (the line is commented out, never deleted).
- **To top**, **Up**, **Down** change the order; **Add folder...** adds a folder you already have.
- The size and what is inside (faces, kits, stadiums...) are shown for each folder.
- Nothing is written until you press **Apply**. **Discard** forgets the changes.

**Lua modules** is the same for the `lua.module` lines. The program knows the right order for
the common modules (content servers after the modules they use) and says so when a module sits
in the wrong place. Some modules need a Sider setting (for example Goal Song Server needs
`match-stats.enabled = 1`); the program says which.

Modules of the League Builder keep the order they were installed in.

## 6. Game content: the content servers

**Stadiums, Kits, Balls, Music, Commentary** and **Other content** (scoreboards, menus, referee
kits, sleeve badges and weather) each belong to one content server. Every page has:

- a **status line**: is the module on, is its content folder there;
- a tab per **map file**, shown as a table: which competition, club or stadium gets what.
  Add, change, switch off (the line becomes a comment) or delete rows; pick items from the
  library instead of typing ids. **Save** writes the file; the copy before it goes to Restore
  points;
- the **Library**: what is in the server's content folder, with pictures where there are any.
  Items that no map line uses and map lines that point at missing items are marked;
- **Settings** of the server where it has any (favourite stadium, ball, scoreboard ...).

The program checks the tables before saving: a number where a number goes, no commas inside a
name, an item that exists.

## 7. Profiles

A profile remembers which content folders and modules are on, and in what order. Keep one for
Master League, one for online play, one for testing:

- **Save current setup...** stores what is on now under a name.
- **Switch to it** puts that setup in `sider.ini` (the old `sider.ini` goes to Restore points).
- **Update with current setup** overwrites the profile.

## 8. League Builder: new leagues, clubs and players

The League Builder adds new leagues to the game and changes the game's own. What it makes is a
**world**: a content folder named `_FL26...` that the game reads while it is switched on.

**New leagues → Add league**

| Field | What it means |
|---|---|
| **Name** | The league's name in the game. No two the same. |
| **Country** | Gives the flag and where the league is listed. A country the game has no league for gets a heading of its own. |
| **Clubs** | 10 to 24. |
| **Format** | *Everyone plays everyone*, 1 to 4 times, or *splits in two (Scottish style)*. |
| **Division** | *(top division)*, or the league above it: another new league, or one of the game's. |
| **Up / down** | How many clubs change places with the league above at the end of the season. |
| **Europe** | Top division only: which league position goes to which European competition. **Top flight: 1st UCL, 2nd UEL, 3rd UECL** fills the usual three; **Add place**, **Remove place** and **Clear** for anything else. Each position once, and only positions the league has. Leave it empty for a lower tier. |
| **Logo** | Any picture (PNG with a transparent background looks best). Empty: one is drawn for you. |

**World name** (on the same page) must start with `_FL26`.

**New clubs**: pick the league, then **Edit club** (name, short name, crest), **Paste names...**
or **Load names from file...**. An empty name becomes `<league> 01`, `<league> 02` ...; a club
with no crest gets a numbered badge. Kits are lent from the game's own clubs.
Names keep their letters (FK Željezničar); the three-letter short name has none, as in the game,
so Č, Ž, Đ become C, Z, D there. After **Build** the **Team ID** column shows each club's id in
the game.

**Game's leagues and clubs**: new names, logos and crests for what the game already has.

> **Edit file.** If the game's save folder has an Edit file (`EDIT00000000`), it overrides club
> names. Move it somewhere else to see your names.

### Players

**Players** changes the squad of any club: the new clubs of the recipe and the game's own.
Pick a club (or press **Players** on New clubs), then a player:

- **Name**, **shirt number**, **position** and the positions they can play (A = natural,
  B = can play there), stronger foot, height, weight, age, nationality, playing style;
- all **abilities** and **skills** (the names are the game's own);
- **Face**: **Choose...** a face folder (section 8.1). **Clear** gives the game's face back;
- **Order up / Order down**: the squad order. The first eleven start the match;
- **Add player** (a copy of the player you pick, with a new id), **Remove from club**;
- **Best eleven** puts the strongest player at every place; **Squad level...** raises or
  lowers every ability of the whole squad;
- **Export CSV... / Import CSV...**: edit a squad in a spreadsheet. Export first, change the
  cells, import the same columns back.

Every change is written into the world when you **Build**; the game's files stay as they are.
**Undo changes to this player** and **Undo all changes of this club** go back to the game's.

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

**Build**:

0. **Install the modules** — once, and again after a new version of the program. Files it
   replaces are kept in `SiderAddons\modules\before-builder-1\`.
1. **Check the plan** — what will be made; nothing is written.
2. **Build the world**.
3. **Switch it on** — makes it the active world in `sider.ini`.
4. Start the game, come back and press **After a start: check**. It reads `sider.log` and says,
   module by module, whether the world was taken.

**Include the Conference League** (on the Build page, on by default) also builds the
Conference League, and gives the Champions League and the Europa League their league phase of
36 clubs, with the February play-off of all three. Off: the European cups as the game ships them.

> **European places.** The places you give your leagues come after the ones the game's own
> leagues have. Each competition takes 36 clubs; places past the 36th get nothing, and
> **Check the plan** says so. New leagues with no places send nobody to Europe, and Overview
> warns about it.

Then **start a new Master League** (or Become a Legend) career. The new leagues are under their
country in Select Team and Kick Off.

> **Saves belong to a world.** A career saved with one world on needs that same world to load.

**File → Save recipe** stores everything in a `.json` file; **Open recipe** brings it back.

### 8.3 Limits

| | |
|---|---|
| New leagues per world | 39 |
| Clubs per league | 10 – 24 |
| New clubs in all | 793 |
| Times clubs meet | 1 – 4 |
| Split leagues | 2 per world |
| Divisions in one country | down to the 7th |
| Players per new club | 30 at the start; add and remove as you like |

## 9. League packages: share a whole league

A modder makes a league once — clubs, names, crests, logos, squads, faces — and shares **one
`.fl26pack` file**. Anybody adds it to their own recipe and builds.

**Make a package** (League packages → **Make a package...**, or File → Make a league package):

1. Name, author, version and a short description.
2. Tick the leagues that go in. A league below another new league must go with it.
3. Optionally **also my changes to the game's own leagues, clubs and players**.
4. Save. The file holds the pictures and faces, not paths on your computer.

**Add a package** (League packages → **Add a package...**, File → Add a league package, or
drop it on Install mods):

1. The program shows what is inside and asks.
2. A league with a name you already have is added as `Name (Package)`.
3. **Save the recipe**, then **Build**.

Ids are given out when each person builds, from what their own game has, so a package works next
to other packages and next to your own leagues. **Remove from the recipe** takes a package out
again, including the changes it made to the game's clubs.

A league placed below one of the game's leagues works for everybody with the same game version.

## 10. Tools

**Diagnostics — Run the checks** looks at the whole setup: content folders that are on but
missing, modules in the wrong order or switched on twice, map lines that point at nothing,
League Builder worlds (only one should be on), and the last `sider.log`. **Copy a report**
puts it all in the clipboard to paste in a forum post or a bug report.

**Restore points**: every file the program changed, with the copy from before. **Put this copy
back** restores it. Copies live in `SiderAddons\ModStudio\backups`. **Clean up...** removes old
ones.

## 11. When something is wrong

| What you see | What to do |
|---|---|
| *sider.ini not found* | Settings → Game folder: pick the folder with `FL_2026.exe`. |
| *no game tables* | Settings → Unpack the game's tables. |
| A mod does not show in the game | Diagnostics → Run the checks. A content folder higher in the list may have the same file. |
| The game does not start after a change | Restore points → put `sider.ini` back, or switch to a profile that worked. |
| The new league is not in Select Team | Start a *new* career; old careers keep their old leagues. |
| Club names are the game's | An Edit file overrides them (section 8). |
| *your leagues send nobody to Europe* | New leagues → Edit the top division → Europe (the **Top flight** button fills the usual three), then Build again. |
| *the Conference League is on, but its tables are missing* | Build the world again: it was built before the option, or with it off. |
| A face does not show | The folder must hold `#Win\face.fpk`; Build again after choosing it. |
| Anything else | Diagnostics → **Copy a report**, and post it with `SiderAddons\sider.log`. |
