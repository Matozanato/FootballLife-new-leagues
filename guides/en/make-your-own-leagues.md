# Make your own leagues and packs: every click, in order

> **English** · [hrvatski](../hr/make-your-own-leagues.md) · [español](../es/make-your-own-leagues.md) · [português](../pt/make-your-own-leagues.md)

> The other step-by-step guide: [Install a ready pack](install-a-pack.md)
> · every page and option explained: [mod-studio-guide.md](mod-studio-guide.md)
> · questions: [faq.md](../../docs/faq.md) · help: [Discord](https://discord.gg/StQqtk3G3M)

This page takes you from nothing to your own leagues in the game: real leagues with real clubs
and players from the **NewLife Database**, set up the way you want, built, played, and shared
with other people. It says what to click, the exact name of every button and field as Mod Studio
shows it, and what you should see after each step. Do the steps in order. If you see something
different from what a step says, stop there and look in
[If something goes wrong](#if-something-goes-wrong).

Three words you will meet all the time:

- **Recipe**: your list of leagues and everything you set for them. You change it on the
  **LEAGUE BUILDER** pages. It is only a plan: nothing reaches the game until you **Build**.
- **World**: what Build makes from the recipe, a folder whose name starts with `_FL26`
  (`_FL26MyWorld` unless you change it). The game reads it while it is switched on.
- **Build**: the button that turns the recipe into a world and puts it in the game.

**Contents**

- [Before you start: the one-time setup](#before-you-start-the-one-time-setup)
- [Step 1. Get the NewLife Database](#step-1-get-the-newlife-database)
- [Step 2. Open it on the NewLife Database page](#step-2-open-it-on-the-newlife-database-page)
- [Step 3. Pick your leagues](#step-3-pick-your-leagues)
- [Step 4. Choose the clubs of a league](#step-4-choose-the-clubs-of-a-league)
- [Step 5. Add to the recipe](#step-5-add-to-the-recipe)
- [Step 6. The Leagues page: every setting of a league](#step-6-the-leagues-page-every-setting-of-a-league)
- [Step 7. Example: a country with two divisions](#step-7-example-a-country-with-two-divisions)
- [Step 8. The New clubs page: names, crests, kits, clubs of the game](#step-8-the-new-clubs-page-names-crests-kits-clubs-of-the-game)
- [Step 9. The Players page](#step-9-the-players-page)
- [Step 10. Limits that stop a build](#step-10-limits-that-stop-a-build)
- [Step 11. Save the recipe](#step-11-save-the-recipe)
- [Step 12. Build](#step-12-build)
- [Step 13. Play: a NEW Master League, then the check](#step-13-play-a-new-master-league-then-the-check)
- [Step 14. Changing something later](#step-14-changing-something-later)
- [Step 15. Sharing what you made](#step-15-sharing-what-you-made)
- [If something goes wrong](#if-something-goes-wrong)

---

## Before you start: the one-time setup

Do steps 1 to 5 of the other guide first, once:
[close the game](install-a-pack.md#step-1-close-the-game),
[download Mod Studio](install-a-pack.md#step-2-download-mod-studio),
[tell it where your game is](install-a-pack.md#step-3-tell-it-where-your-game-is),
[unpack the game's tables](install-a-pack.md#step-4-unpack-the-games-tables) and
[install Mod Studio's modules](install-a-pack.md#step-5-install-mod-studios-modules).
Then come back here.

Keep the game closed the whole time you work in Mod Studio.

---

## Step 1. Get the NewLife Database

The NewLife Database is a separate download with real clubs and players: names, birth dates,
positions, ratings on the game's scale, and the clubs' colours. It is not on GitHub.

1. Open our [Discord](https://discord.gg/StQqtk3G3M) and go to the **#newlife** channel.
2. Download the parts you want. There is one part per continent (a big continent comes in more
   than one part), plus *Free agents*. Each part is a `.zip` file named `NewLife-...zip`.
3. Make a folder for them, for example `Documents\NewLife`, and put **all** the parts in that
   one folder.
4. **Do not unzip them.** Mod Studio reads the zips as they are. (Windows' own zip viewer
   cannot open them anyway; that is normal.)

When a newer NewLife version comes out, put its parts in a **new** folder. Never mix two
versions in one folder.

## Step 2. Open it on the NewLife Database page

1. Left bar, under **LEAGUE BUILDER**: click **NewLife Database**.
2. Click **Open NewLife Database...** at the top.
3. Pick the folder from Step 1 (the folder, not a zip inside it) and confirm.
4. Wait a few seconds while it reads.

**You should see:** above the list, the NewLife version and the folder, and under them
`Parts:` with the parts it found. Below that, a long list of leagues.

Mod Studio remembers the folder: next time the page opens it by itself.

**Search.** The box above the list, *Search leagues or countries*, keeps only the leagues whose
name or country has what you type. Type `brazil` or `liga`, say. Empty the box to see all again.

**The columns.** Click a column header to sort by it, click again to turn the order round.

| Column | What it tells you |
|---|---|
| **League** | The league's name. A `*` after it means you changed its clubs (Step 4). |
| **Country** | Where it goes in the game. |
| **Clubs** | How many clubs it will have, as you have it set now. |
| **In game** | How many of its clubs the game already has (they keep their own names, crests, kits and players). |
| **Players** | How many players its clubs have in NewLife. |
| **Level** | How strong the league is. Higher is stronger. |
| (last column) | Why a grey league cannot be added. Empty for a league you can add. |

**Why some leagues are grey.** A grey league cannot be added, and the last column says why:

- `a league takes 10 to 24 clubs`: a league in the game has 10 to 24 clubs, new ones and the
  game's together. This one has fewer or more. You can still fix it in Step 4 (add or leave out
  clubs) until it fits.
- `the game's own league: Bring the game's leagues to this season`: the game already has this
  league (the Premier League, the Championship ...). It is not added a second time. The button
  **Bring the game's leagues to this season...** at the top gives the game's own leagues the
  clubs and squads of this NewLife season instead; see
  [8.4 in the full guide](mod-studio-guide.md#84-newlife-database-real-clubs-and-players).

If the page says Mod Studio has no game tables and offers to open Settings: click **Yes** and do
[Unpack the game's tables](install-a-pack.md#step-4-unpack-the-games-tables).

## Step 3. Pick your leagues

1. Click a league in the list to select it. Its row is highlighted.
2. For more than one: hold **Ctrl** and click each one. (Or click the first, hold **Shift**
   and click the last to take everything between them.)

**You should see:** at the bottom of the page a line like
`New clubs in the recipe: 0 of the 793 the game takes.  Selected: 18 more.`

- The **first** number is how many new clubs your recipe already has.
- The **second** is how many new clubs fit in the game in all. Mod Studio works it out from
  your game's tables, so it can be a little different on another game version.
- **Selected** is how many new clubs the leagues you picked would add.

If the recipe and the selection together are more than the game takes, **Add to the recipe**
stays grey: pick fewer leagues.

## Step 4. Choose the clubs of a league

This step is optional. Skip it to take a league exactly as NewLife has it.

Select **one** league (just one). The list on the right shows its clubs: **Club** and
**Players** (how many players NewLife gives it). A club the game already has shows grey, with
`in the game` instead of a number.

- **Leave a club out:** click its tick box to untick it.
- **Bring a club from another league** (this season's first division is last season's with two
  promoted clubs, say): click **Add a club from another league...** under the list.
  1. A window opens with every club of the NewLife parts you opened, each with its league in
     brackets.
  2. Type in the search box to find a club or a league.
  3. Tick one or more clubs. The line under the list says how many you picked.
  4. Click **OK**.

  **You should see:** the club at the end of the list, with `from <its league>` next to it.

**You should see:** the league's row in the list now has a `*`, and its **Clubs** number
changed. A grey league that now has 10 to 24 clubs turns normal.

A club can play in one league only. If you add it to two, Mod Studio stops you in Step 5.

## Step 5. Add to the recipe

With your league or leagues selected, click **Add to the recipe** at the top.

**You should see:** a green line under the page title. What each line means:

| Green line | What it means |
|---|---|
| `Added: <leagues>. Change them on Leagues, New clubs and Players, then Build.` | The leagues are in your recipe, each as the top division of its country, everyone playing everyone twice. Nothing is in the game yet. |
| `<clubs> also play in a competition of the game: on New clubs pick each one and use Club of the game to choose the club that takes its place there.` | These clubs of your new league are clubs the game already has, and they also play somewhere in the game (a league, a cup, the Europa League ...). A club plays in one league only, so its old place needs another club. You choose that club in [Step 8](#clubs-the-game-already-has). Until you do, Build stops with an error that names the club. |
| `<n> players stay at their game club (their club would have too few players).` | Players the game already has normally move to the NewLife club. These stay, so their old club keeps at least 18 players. Nothing to do. |
| `<n> players are not added: another league already has them.` | A league you added earlier already took these players. Nothing to do. |

If an error window says `<club> would play in two leagues (<league> and <league>).`, untick
that club in one of the two leagues (Step 4) and try again.

Want leagues from other continents? Select them too and click **Add to the recipe** again. Each
click adds; it never removes what is there.

---

## Step 6. The Leagues page: every setting of a league

1. Left bar: click **Leagues**.
2. Above the list, click **Ours**: the list shows only the leagues of your recipe. (**All**
   shows every league, the game's too; **Changed**, the game's leagues you changed.) The
   leagues are grouped by continent.
3. Click your league.

**You should see:** on the right, `OURS`, the league's name and logo, and the rows **Country**,
**Clubs**, **Format**, **Division**, **Up / down**, **Europe** and **League ID** (`not built yet`
until the first Build), then the crests of its clubs. Under them the buttons **Edit league...**,
**Add lower tier**, **Clubs and names**, **Players** and **Remove**.

You can drag a league up or down in the list to put the leagues of a continent in order.

4. Click **Edit league...**.

**You should see:** a window called **League** with the fields below, from top to bottom. A
grey field cannot be used with what you set above it (for example a cup on a second division).
The **?** next to **OK** explains the window in short. Nothing is required: the defaults work,
and **Cancel** changes nothing.

| Field | What it is, and what to do |
|---|---|
| **Name** | The league's name in the game. Two leagues cannot have the same name. Keep it under about 38 characters: a longer name shows as an empty row in Kick Off's league list. |
| **Country** | Type a few letters and pick from the list (`korea` finds both Koreas). It gives the flag and where the league is listed in the game. |
| **Clubs** | 10 to 24. For a NewLife league, leave it as it is: a smaller number takes the last clubs out, a bigger one adds made-up clubs at the end. |
| **Clubs in no league** | Leave it at `(no -- a league)`. The other choices (*Other European teams* ...) are for one club, or a few, with no league around them; they go into the game's "Other ..." groups, and most fields below go grey. [More](mod-studio-guide.md#8-league-builder-new-leagues-clubs-and-players). |
| **Format** | Pick one: **everyone plays everyone, times:** and the number (1 to 4; 2 is home and away); **splits in two (Scottish style)**, with `first` *n* `x, then groups` *6/6* *n* `x` (the groups must add up to the clubs); or **Apertura and Clausura, then playoffs of:** *8 clubs*, *4 clubs* or *no playoffs* (two short tournaments a season, 18 clubs at most). |
| **Division** | `(top division)` = the best league of its country. For a second division, pick the league one level up: your new leagues are at the top of the list, then the game's leagues with a number in brackets. `= division 2` next to it shows the level. A league that already has a league under it is grey (`-- under it: ...`): one league can have one league below it. See [Step 7](#step-7-example-a-country-with-two-divisions). |
| **Exhibition only -- not in Master League** | Leave it off. On: the league is only for Kick Off and exhibition matches (legends, a historic season); it never plays a Master League season, and the division, cups and Europe go grey. Do not start a career with one of its clubs. |
| **Season** | Top division only: **August to May** (like Europe) or **February to December** (like Brazil or Japan). A division below follows the league above it. February to December cannot have a split, Apertura/Clausura or the country's cups yet. |
| **Up / down** | 1 to 6: how many clubs change places with the league above at the end of the season. Only means something for a division below another. |
| **Logo** | **Pick picture...** a PNG or JPG for the league (a PNG with a transparent background looks best). **Clear** takes it away. Empty: `(made for you)`, a logo is drawn at Build. |
| **Country flag** | Your own picture of the country's flag. Empty: `(the game's own)`. Leave it empty unless the game has no good flag. |
| **Cup** | Top division only. Tick **National cup** to give the country a knockout cup (this league and the division below it). The box next to it is the cup's name; empty = the league's name + Cup. |
| **Super cup (champion v cup winner)** | One match in late July. Needs **National cup** ticked. |
| **League cup** | Top division only. A second knockout cup, like England's Carabao Cup: this league and the one below, up to 44 clubs. The box is its name; empty = the league's name + League Cup. |
| **Cup logos** | A picture each for the **Cup**, the **Super cup**, the **League cup** and the **Playoffs**. Empty: an emblem with the cup's initials. |
| **Formation** | How the league's clubs line up. Pick one from the list, or leave it empty for the game's default 4-2-3-1. A single club can have its own (Step 8). |
| **Europe** | Top division only: which table position goes to which continental competition. The button that starts with **Top flight:** fills the usual places for the country's continent (for Europe: `Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL`). **Add place** adds a row: pick the **League position** (below 1 it reads **Cup winner**) and the **Competition**. The **✕** on a row removes it, **Clear** removes all. Leave it empty for a second division. |

5. Click **OK**.

**You should see:** the window closes and the rows on the right show what you set.

A NewLife league comes in with no European places. If you want its clubs in the Champions
League and the rest, set **Europe** now; otherwise **1. Check the plan** reminds you with
`no European places: the new leagues send nobody to Europe`.

The meaning of every format, cup and European place in depth (dates, qualifying rounds, cup
sizes):
[section 8 of the full guide](mod-studio-guide.md#8-league-builder-new-leagues-clubs-and-players)
and [8.2](mod-studio-guide.md#82-build-switch-on-play).

**More ▾** (top of the Leagues page) has the tools for the whole world: **Pre-season cups**,
**Cups of the game's countries**, **European places of the game's leagues**, **UEFA ranking**,
**South American places**, **Competition names** (new names and logos for cups and continental
competitions) and **World name and recipe...** (the world's folder name; it must start with
`_FL26`). You do not need any of them for a first world.

**A league with no NewLife clubs.** **Add league** at the top of the Leagues page opens the same
**League** window for a league made from scratch: give it a **Name**, a **Country** and a number
of **Clubs**, and Build makes the clubs with full squads and a manager. You name them on
**New clubs** (Step 8), where **NewLife club...** can also put real clubs into it.

## Step 7. Example: a country with two divisions

Say your NewLife parts have a country's first and second division, here called *First League*
and *Second League*. You want promotion and relegation between them.

1. **NewLife Database**: select *First League* and click **Add to the recipe**. (The top one
   first.)
2. Select *Second League* and click **Add to the recipe**.

   **You should see:** the green `Added:` line each time. Both are now top divisions of the
   same country, which is not yet what you want.

3. **Leagues** → **Ours** → click *Second League* → **Edit league...**.
4. **Division**: open the list and pick *First League* (your leagues are at the top).

   **You should see:** `= division 2` next to it. **Cup**, **League cup**, **Season** and the
   **Top flight** button go grey: those belong to the top division.

5. **Up / down**: how many clubs go up and down between the two, for example `3`.
6. **Europe**: if it has rows, click **Clear**. A second division sends nobody to Europe.
7. Click **OK**.

   **You should see:** on the right, **Division** `2  (below First League)` and **Up / down**
   `3 with First League above`. Click *First League*: its **Up / down** says
   `3 with Second League below`.

8. Click *First League* → **Edit league...** and set what belongs to the top division: **Europe**
   (the **Top flight** button), and if you like **National cup**, **Super cup** and
   **League cup**. Click **OK**.

A third division works the same way: its **Division** is *Second League*. The game goes down to
the 7th division.

**One league under one league.** Two leagues cannot sit under the same league (three regional
groups under one second division, say). The second one shows grey in the **Division** list.

**Under one of the game's leagues.** Your new league can also go under a league the game has:
pick the game's league in **Division** (the ones with a number in brackets). It then plays
promotion and relegation with it.

**Without NewLife.** On **Leagues**, click your top league, then **Add lower tier**: a **League**
window opens with the country, clubs, format and division already filled in. Give it a
**Name** and click **OK**.

---

## Step 8. The New clubs page: names, crests, kits, clubs of the game

1. Left bar: click **New clubs** (or **Clubs and names** on the Leagues page).
2. At the top, **League**: pick one of your leagues.

**You should see:** its clubs with the columns **#**, **Name**, **Short name**, **Team ID**
(`at Build` until the first Build), **Crest** and **Players changed**. NewLife clubs already
have their names, short names and crests. A club with no name shows `<league> 01`,
`<league> 02` ... in grey.

### Name, crest, kits, manager

1. Double-click a club (or select it and click **Edit club**).

**You should see:** a window called **Club** with:

| Field | What to do |
|---|---|
| **Name** | The club's name. Letters with marks (Željezničar) are fine. |
| **Short name** | Three letters or digits. Empty = made from the name. Č, Ž, Đ ... become C, Z, D, as in the game. |
| **Crest** | **Pick picture...** a PNG or JPG. **Clear** takes it away. A club with no crest gets a numbered badge. |
| **Home stadium** | Only when Stadium Server is installed: **Choose stadium...** from your stadium pack, or **Game's own**. |
| **Manager** | The manager's name. Empty: a name made up from players of the club's country. |
| **Manager picture** | A PNG or JPG; the game shows it in Edit mode and the Master League. |
| **Formation** | `As the league (...)` keeps the league's formation; or pick one for this club. |
| **Home kit colours**, **Away kit colours** | Click the two colour squares (shirt, second colour) to choose colours; **None** = Build picks a kit by itself. Build gives the club the game's kit nearest these colours. |

2. Click **OK**.

**You should see:** the new name and crest in the list.

**Kits.** A new club borrows a kit of a game club in its colours. Two options on the **Build**
page change that: **Make kits for the new clubs** (on by default, needs Kit Server installed:
every new club gets home, away, third and goalkeeper kits made in its colours, with its crest)
and **Kits you can edit in the game** (each new club wears a plain kit you can change in the
game's Edit mode). [More in the full guide](mod-studio-guide.md#8-league-builder-new-leagues-clubs-and-players).

**Many clubs at once.** **More ▾** has **Paste names...** and **Load names from file...** (one
name per line, in order) and **Import crests...** (a folder of pictures, matched to clubs by file
name). It also has **Insert club**, **Remove club**, **New club here** and **Move to another
league...**.

### Clubs the game already has

A NewLife league can include clubs the game already has. They show in the list with the
game's name, their **Team ID**, and `(the game's)` under **Crest**. If the green line in Step 5
said they *also play in a competition of the game*, do this for **each** of them:

1. Click the club in the list.
2. Click **Club of the game...**.

**You should see:** a window called **Club of the game**, with the club selected and under the
list a line like `<club> plays in <competitions>. Every one of those competitions keeps its
number of clubs: pick who takes its place there.`

3. Choose who takes its old place:
   - **Its place goes to a club of the game that plays in nothing:** and pick a club from the
     list under it; or
   - **Its place goes to a new club, named:** and type a name. Build makes that club.
4. If the club plays in a continental competition (Champions League, Libertadores ...), there is
   also **It keeps its places in continental competitions**. Ticked, it goes on playing that
   competition and nobody has to take its place there.
5. Click **OK**.

The same button puts any club of the game into a place of your league: select the place,
**Club of the game...**, search by name, short name or team ID (**Only clubs in no league**
narrows the list). **New club here** (in **More ▾**) gives the place back to a new club.

**NewLife club...** puts NewLife clubs, with their squads, in the selected place and the places
after it: tick one or more in the window that opens, then **OK**. It is how a league you made by
hand gets real clubs.

## Step 9. The Players page

NewLife clubs come with full squads, so you do not have to touch this page. It is there if you
want to change a squad.

1. Left bar: click **Players** (or select a club on New clubs and click **Players**).
2. At the top, pick the **League** and the **Club**. (Or type in *Find a club...*.)

**You should see:** the squad with the columns **Order**, **No.**, **Name**, **Pos**, **Age**,
**Rating**, **Foot**, **Changed** and **Player ID**, and the first eleven on a pitch under it.
Click a player: the right side shows him, in the tabs **Basics**, **Positions**, **Abilities**
and **Skills**.

- Change a name, number, position, rating or ability on the right. The change is kept at once.
- **Order up** / **Order down**: the squad order. The first eleven start the match. Or drag a
  player onto a place on the pitch. **Best eleven** puts the strongest player at every place.
- **Sign players...** brings players from other clubs; **Transfer to...** sends the selected
  player to another club.
- **Undo changes to this player** and **Undo all changes of this club** go back.

Everything on this page is in [Players in the full guide](mod-studio-guide.md#players).

---

## Step 10. Limits that stop a build

| Limit | Where you see it |
|---|---|
| New clubs in all: the number on the line `New clubs in the recipe: X of the Y the game takes.` | NewLife Database page: **Add to the recipe** stays grey. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| 10 to 24 clubs in a league | NewLife Database: grey league, `a league takes 10 to 24 clubs`. New clubs: `A league has 10 to 24 clubs.` |
| New leagues per world (39 in our tests) | Build: `error: <n> leagues, but the game has room for <m> ...` |
| One league under one league | **Division** list: grey. Build: `... are all under ...; the game follows one link down from a league ...` |
| Divisions down to the 7th | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 split leagues per world; one split or Apertura/Clausura per country | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| A club in one league only | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| A club of the game that plays somewhere needs a replacement | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Do [Clubs the game already has](#clubs-the-game-already-has). |

All the numbers: [8.3 Limits](mod-studio-guide.md#83-limits).

## Step 11. Save the recipe

1. Top bar: **File → Save recipe**.
2. The first time, a window **Save recipe as...** opens. It suggests the world's name, for
   example `_FL26MyWorld.json`. Pick a folder you will find again (for example
   `Documents\FL26 Mod Studio\recipes`) and click **Save**.

**You should see:** at the bottom of the window, `Recipe saved: <file>`.

After that, **File → Save recipe** saves to the same file without asking. **File → Save recipe
as...** saves a copy under another name. **File → Open recipe...** opens a saved recipe again
(it warns if you have unsaved changes). **File → New recipe** starts an empty one.

Build also keeps a copy of the recipe by itself, and Mod Studio opens the last recipe when it
starts, so what you built is never lost. Save anyway: your own file is the one you can find and
copy.

## Step 12. Build

1. Left bar: click **Build**.

**You should see:** the big blue **Build and install** button, the row **0. Install the
modules**, **1. Check the plan**, **2. Build the world**, **3. Switch it on**, **4. After a
start: check** and **Export the world...**, two cards (**European cups** and **New clubs**)
with options, a line like `World _FL26MyWorld: not built yet · builder modules: installed`,
and a box for the log at the bottom.

2. Click **1. Check the plan** first. It changes nothing; it only reads your recipe.

**You should see:** in the box, a line `world _FL26MyWorld: 2 new leagues, ...` and a line for
each league with its clubs, division and format (`18 clubs x2` is 18 clubs, everyone plays
everyone twice; `division 2  below ... (3 up/down)` is a second division), and its
`European places:`. A line starting with `error:` says what to fix first; see the table at the
end.

3. Click **Build and install**. It asks `Build _FL26MyWorld and make it the live world? ...`:
   click **Yes**.

   If the game's tables are older than the game, it asks first whether to unpack them again:
   click **Yes** (about a minute).

   It installs the modules, builds the world and switches it on, all in one. It takes from a few
   seconds to a few minutes.

**You should see:** a window **Build finished** with a tick on each line: **World built**,
**Leagues and clubs** (`2 leagues · 36 new clubs`), **Modules installed and switched on**,
**Switched on in sider.ini** and **Start the game to play it**. Under **Before you play**:
`Start a new Master League career: a career saved before keeps the old world.` Click **Done**.

If it says **An Edit save from before this Build is in the game's save folder**: click **Move
the Edit save aside**. An old Edit save hides the new names and squads.

**Step by step instead of the big button** (the same result):

1. **1. Check the plan**: as above.
2. **2. Build the world**: builds it. If the world exists, it asks `... exists. Build it again?`:
   **Yes**. The log ends with `Next: 3. Switch it on, then start the game.`
3. **3. Switch it on**: asks `Make _FL26MyWorld the live world in sider.ini?`: **Yes**. The log
   ends with `Start the game, then 4. check.`

**What the log lines mean:**

| Line | Meaning |
|---|---|
| `installing the modules ...`, `modules: ... copied, ... already there` | Mod Studio's modules are put in place. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | The summary of your recipe. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | One league: its ids in the game, its division and format. |
| `European places: 1st Champions League qualifying, ...` | Where its top clubs go. |
| `no European places: the new leagues send nobody to Europe` | A warning, not an error: set **Europe** on a top division if you want it. |
| `building ...` | The world is being written. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | The world is switched on. |
| `error: ...` | Build stopped and nothing changed in the game. Fix what it says (table at the end) and build again. |

The options on the cards (**Include the Conference League**, **Country cup draw**, **Make kits
for the new clubs** ...) are explained in [8.2](mod-studio-guide.md#82-build-switch-on-play). The
defaults are fine.

## Step 13. Play: a NEW Master League, then the check

1. Click the green **Play** button at the top right (or **Game → Start the game**).
2. In the game: **Master League** → **New game**. Not Continue: a career saved before keeps the
   old world.
3. At **Select Team**, scroll: your leagues are in the list, under their countries.
4. Pick a club and play.

Then let Mod Studio check that the game took the world:

1. Close the game (or at least start it once to the main menu).
2. In Mod Studio: **Build** → **4. After a start: check**.

**You should see:** one line per module saying how many leagues it read from the world file, and
at the end `the world works as built`. A line `not loaded` or `did NOT read the world file`, and
at the end `something is wrong -- see the lines above`, mean something did not work: see the
table at the end.

## Step 14. Changing something later

1. Close the game.
2. Open Mod Studio. It opens your last recipe by itself (or **File → Open recipe...**).
3. Change what you want on **NewLife Database**, **Leagues**, **New clubs** or **Players**.
4. **File → Save recipe**.
5. **Build** → **Build and install** → **Yes**.

**Do you need a new career?** Yes: start a new Master League after every change you build.
A career takes its own copy of the leagues, clubs and squads when it starts, so a career you are
already in keeps the old ones. And a career saved with one world needs that same world to load,
so keep the world switched on while you play it.

**A newer NewLife version.** Put its parts in a new folder, **Open NewLife Database...** that
folder, then click **Update my leagues to this version**. Each league keeps its name, division,
format, European places and cups; the clubs and squads come from the new version (the
**Keep my clubs** box keeps your own line-up). Build again and start a new career.
[More](mod-studio-guide.md#84-newlife-database-real-clubs-and-players).

**Take a league out.** **Leagues** → **Ours** → click it → **Remove** → **Yes**. Its clubs and
their player changes go with it.

## Step 15. Sharing what you made

There are two ways. Pick one:

| | League package (`.fl26pack`) | Exported world (`.zip`) |
|---|---|---|
| What it holds | Your leagues as a recipe: clubs, names, crests, logos, squads, faces, and if you like kits and scoreboards. | The world exactly as you built it. |
| The other person | Adds it to their own recipe and builds, so it works next to their own leagues and other packages. | Installs it and plays. Nothing to build, but it replaces any other world they have on. |
| How they install it | [Way C of Install a ready pack](install-a-pack.md#way-c-a-league-package-fl26pack) | [Way A of Install a ready pack](install-a-pack.md#way-a-a-ready-world-one-zip) |

### A league package

1. Left bar: **League packages** → **Make a package...** (or top bar: **File → Make a league
   package...**).

**You should see:** a window **Make a league package**.

2. Fill in **Name** (required), **Author**, **Version** (`1.0` to start) and **Description**.
3. Under **Leagues**, tick the leagues that go in (**Select all** / **Select none**). A league
   below another league must go with it.
4. **Also my changes to the game's own leagues, clubs and players** (only if you changed any):
   tick it to put those in too.
5. Under **What goes in**, everything is ticked: **Squads**, **Player faces and portraits**,
   **Crests and league logos**, **Managers**, **Kit colours**, **Kits**, **Scoreboards** and
   **Home stadiums**. Untick what you do not want to share. Kits add about 10 MB per league and
   a scoreboard about 7 MB.
6. Click **Save the package...**. A save window **Save the package** opens with a name like
   `<name>-1.0.fl26pack`. Pick a folder you will find again (Desktop, Documents ...) and click
   **Save**.

**You should see:** `Saved <file>` with how many leagues, clubs and faces are in it. That one
file is what you share. If it is over 10 MB, Mod Studio says so: Discord will not take it, so
share it through Google Drive, Dropbox, MEGA or similar, or untick **Kits** and **Scoreboards**,
or make one package per league.

More: [9. League packages](mod-studio-guide.md#9-league-packages-share-a-whole-league).

### A whole world (zip)

1. Build first (Step 12). The world must be built.
2. Left bar: **Build** → **Export the world...**.
3. A save window opens with the world's name as the file name (`_FL26MyWorld.zip`), in your
   user folder the first time (after that, in the folder you used last). Pick a folder and click
   **Save**.

**You should see:** after a moment, `Saved <file>` and how many new players get a generated face.
The zip holds the world folder, its world file and a read-me.

The person who installs it needs Mod Studio's modules with the face pack (**Build → 0. Install
the modules**); without them every new player looks the same. The read-me in the zip says so.

More: [9.1 Export the world](mod-studio-guide.md#91-export-the-world-a-built-world-for-another-pc).

---

## If something goes wrong

The messages appear in an error window, in the green or red line under a page's title, or in
the Build log after `error:`. `<...>` stands for a name or number.

| What you see | What to do |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | You picked the wrong folder, or unzipped the parts. Open the folder that holds the `NewLife-...zip` files themselves. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Two NewLife versions are mixed. Keep one version's parts in the folder. |
| `<file> is not a NewLife part (...) -- download it again` | The download broke. Download that part again. |
| A grey league, `a league takes 10 to 24 clubs` | Add or leave out clubs (Step 4) until it has 10 to 24. |
| A grey league, `the game's own league: Bring the game's leagues to this season` | The game has it already. Use **Bring the game's leagues to this season...**. |
| **Add to the recipe** stays grey | Nothing addable is selected, or the selection would pass the new-club limit (the line at the bottom). |
| `<club> would play in two leagues (<league> and <league>).` | Untick the club in one of them. |
| `<league> has no country the game knows.` | This league cannot be added. |
| `A league needs a name and a country.` / `Pick the country from the list.` | In **Edit league...**, fill in **Name**, and pick the **Country** from the list rather than typing it out. |
| `There is already a league called <name>.` | Give the league another name. |
| `European places: position <n> -- the league has <m> clubs` | A row in **Europe** points past the last club. Change or remove it. |
| `European places: position <n> is listed twice` | Two rows have the same position. Remove one. |
| `European places: a cup winner's place, but the country has no cup` | Tick **National cup**, or remove the **Cup winner** row. |
| `Clubs, times and groups must be numbers.` | Under **splits in two**, type the groups as numbers, for example `6/6`. |
| `A league playing February to December has no split, Apertura/Clausura, national cup or league cup yet.` | Set **Season** to **August to May**, or take off the split, Apertura/Clausura or cups. |
| `This division plays February to December with the league above it, and a league playing February to December has no split or Apertura/Clausura yet.` | Give this division **everyone plays everyone**. |
| `Clubs in no league are all new clubs: take the clubs of the game out first (Edit club).` | The league holds clubs of the game. On **New clubs** select each and use **More ▾ → New club here**, then set **Clubs in no league** again. |
| `<league> is below this league; clubs in no league have none.` (or `an exhibition league has none.`) | Another league has this one as its **Division**. Change that league first. |
| `A league has 10 to 24 clubs.` (New clubs) | Insert club / Remove club would leave the league outside 10 to 24. |
| `Open the NewLife Database on the NewLife page first.` | **NewLife club...** needs the NewLife folder: open it on **NewLife Database** once. |
| `Pick the club that takes its place.` / `Give the new club a name.` / `A club cannot take its own place.` | In **Club of the game**, pick a replacement club, or type a name for the new one. |
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| `error: no game folder -- Game > Choose the game folder` | **Game → Choose the game folder...**. |
| `error: the world name must start with _FL26` | **Leagues → More ▾ → World name and recipe...**: a name starting with `_FL26`. |
| `error: nothing to build: add a league or change one of the game's ...` | The recipe is empty. Add leagues (Steps 3 to 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Do [Clubs the game already has](#clubs-the-game-already-has) for that club. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | Same window: type a name next to **Its place goes to a new club, named:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Take the club out of one league (**New club here** on New clubs, or untick it before adding). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Too many new clubs. Remove a league, or clubs. |
| `error: <n> leagues, but the game has room for <m> ...` | Too many new leagues. Remove some. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Only one league can be under a league. Change **Division** of the others. |
| `error: <league>: division 8 -- the rank field stops at 7` | A country goes down to the 7th division. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Give the other leagues **everyone plays everyone**. |
| `The game's tables Mod Studio uses are older than the game: ... Unpack them again first?` | Click **Yes**. |
| `<world> is not built yet: 2. Build the world first.` (Export the world) | Build first, then export. |
| `Give the package a name.` / `Tick at least one league.` / `The recipe has no leagues yet.` | In **Make a league package**, fill in **Name** and tick a league; the recipe needs leagues first. |
| No new leagues at Select Team | Start a **new** Master League. Then **Build → 4. After a start: check**. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Start the game to its main menu, close it, check again. |
| `<module> not loaded` / `did NOT read the world file` | **Build → 0. Install the modules**, then **3. Switch it on**, start the game again and check again. Still wrong: ask on Discord. |
| Club names are the game's, not yours | An old Edit save hides them: **Move the Edit save aside** in the **Build finished** window, or move `EDIT00000000` out of the game's save folder. |
| All new players have the same face | **Build → 0. Install the modules** (it brings the face pack), then start the game again. |

**Asking for help:** on the [Discord](https://discord.gg/StQqtk3G3M), send a screenshot of what
you see, the text of the Build log, and your `sider.log` (**Game → Open sider.log**).
