# Questions people ask

The first part is about **FL26 Mod Studio**, the program most people use. The second part is
about the command-line scripts it grew out of. Your question is not here? Open an
[issue](https://github.com/Matozanato/FootballLife-new-leagues/issues) with the report
described in [What should I send when something is wrong?](#what-should-i-send-when-something-is-wrong)
Just a question, not a bug? Ask on [Discord](https://discord.gg/StQqtk3G3M).

## FL26 Mod Studio

### I updated Mod Studio. What do I do now?

Every update can change the modules and the world's tables. After updating, go to
**League Builder > Build** and press **0. Install the modules**, then **2. Build the world**
again. Then start a **new Master League career**: a career started before the build was made
with the old world and does not pick up everything that changed.

Download the whole zip from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) and
unzip the whole folder. Since 0.1.3 the program is a folder, not one file: running
`FL26ModStudio.exe` from inside the zip, or copying only the `.exe`, does not work. From 0.1.1
on, *Help > Check for updates* does all of this for you; your settings and projects stay.

### The game crashes a few seconds after I start it

A crash in the first ten seconds or so happens on a clean game too, with none of our modules
installed. It depends on how the game is started. Start it **through the launcher** (the
shortcut the game installed), not by running `FL_2026.exe` directly: measured on our side, the
launcher started it 12 times out of 12, the `.exe` directly only 4 out of 9.

If it still crashes, or it crashes later (in the menus, when a match or a career loads), send
the report described [below](#what-should-i-send-when-something-is-wrong) and say exactly when
it happens.

### The game crashes when I open Edit (a big database or a face pack)

A database, a face pack or another mod that brings its own `PlayerAppearance.bin` with more
than 30,023 records overflows the game's table (FL26 itself has 27,927), and Edit crashes,
usually right after it makes `EDIT00000000` (GitHub #65). The number of players alone is not
the limit: a world of 30,447 players opens Edit fine here.
Since 0.1.9 `fl26regen.dll` caps the load at 30,023, so the game no longer crashes; the players
past that number keep the default look. Install the 0.1.9 modules. Before that, take the mod's
`PlayerAppearance.bin` out.

### LaLiga or Ligue 1 is gone from Select Team, and the game crashes when I scroll a new league

The game's `FL_2026.exe` is not the Steam build the modules know (#62), or another mod changed
it. `fl26caps` then writes nothing (`fl26caps: ABORTED` near the top of `sider.log`), and
without it a new league takes the place of one of the game's in the lists and the game crashes
on its clubs. Since 0.1.7 Mod Studio's *Checks* say so. Put back the Steam `FL_2026.exe`
([install.md](install.md), step 1) and start the game again.

### "Other European Leagues" or "Other Latin American Teams" is gone from Select Team

Select Team has few free places, and four of them belong to the game's "other clubs" groups
(Sparta Prague, APOEL ... / Penarol, LDU Quito ...). Up to 0.1.6 a world of 30 or more leagues
took them (#73). Since 0.1.7 they are the last places a league gets: up to 32 leagues every
group stays, the 33rd and 34th take the small *Other Clubs (Africa)* and *Other* groups, the
35th to 37th play without a place in Select Team, and only the 38th and 39th take the two big
groups. **Check the plan** names each league that takes a place; put the leagues you want to
start a career in first. After updating, **Build the world** again and start a new career.

### My new country is at the bottom of the list, not with the others of its continent

Since 0.1.3 a new country is listed among the countries of its continent, by name (Iceland
between France and Italy). If yours is still at the bottom, you are running an old module or an
old world: press **0. Install the modules** and **2. Build the world** again.

In 0.1.3 a league ticked **Exhibition only** was left out of that order and still went to the
bottom. Fixed in 0.1.3.1: update, then **Build the world** again.

An *Exhibition only* league's clubs still show in the team list when you start a Master League
career, because the game has one list for Kick Off and Master League. Do not pick one of them:
their league never plays a season. Since 0.1.4 the League window, **Check the plan** and
**Build** remind you of this.

### The League window is taller than my screen and I cannot reach Name and Country

A 0.1.3 bug on 1080p screens (and smaller ones, or with Windows scaling above 100%): the window
opens with its top above the screen and does not scroll. Fixed in 0.1.3.1: the window fits the
screen and scrolls. Update Mod Studio (**Help > Check for updates**).

On 0.1.3: when the window opens, the cursor is already in the **Name** field even if you cannot
see it. Type the name, press **Tab**, type the country, and use the mouse for the rest. Setting
Windows' display scaling to 100% also helps.

### How big can a national cup be?

Since 0.1.4, any size up to 44 clubs. (0.1.3 took only 12, 16, 18 or 20 clubs in the top
division, or 36, 40 or 44 with the division below.) The game fills a country's cup with its top
division and the one below it. When the two together have a size a cup of the game has, that
cup is copied; any other number up to 44 plays on the English cup's rounds, and when the number
is not 8, 16, 32 or 64 some clubs get a bye in the first round. With more than 44 clubs the cup
keeps the top division alone. A third division does not change anything: the cup only ever
looks at the first two.

**Why does my cup have 20 clubs when my two divisions have 22?** The game's cup screens can
draw a bracket of 2 to 16, 18, 20, 24, 28, 30 or 32 clubs and nothing in between; a cup of 22
crashed them (#74). So the cup takes the largest of those sizes: the whole top division and the
first clubs of the one below. A field of 33 to 43 clubs becomes 32 (#95). *Check the plan* says
so on the cup's line. This is on purpose, not a bug.

Two other cups have no such limit:
- **League cup** (the tick under the national cup): a knockout of 16, 8 or 4 clubs of the top
  division and the one below, September to December. The clubs past that play a pre-round in
  early September (0.1.7), so a league of 20 leaves nobody out.
- **Pre-season cups** (the button on the New leagues page): a friendly knockout of 4 or 8 clubs
  you invite, from any league, in July.

### My pre-season cup was not played

A Master League career starts in August, after July, so the first pre-season cup is played in
the career's **second** season. That is expected.

### Clubs do not move up or down between my new divisions

Two problems in 0.1.3, both fixed in 0.1.3.1:

- **A new country outside Europe** (South America, Asia, Africa, North America, Oceania): the
  first season plays normally, but at its end (July) the game drops the country's leagues. From
  the second season on they have no clubs and are not played, and nobody moves up or down.
- **A new league that plays January to December** (under Saudi Arabia, Japan, Korea, China,
  Brazil, Chile, Colombia ...): the season is played in full, but at New Year nobody moves up or down.

New leagues in Europe, and new leagues under the game's own European leagues, promote and
relegate normally. There is no workaround in 0.1.3. After updating to 0.1.3.1: **Install the
modules**, **Build the world** again and start a new career (a career started on 0.1.3 keeps
the leagues it already lost).

### Which months does my new league play?

- **A new country** (one the game has no league for): August to May, like Europe.
- **A league under one of the game's own leagues** plays that league's calendar. Under a
  January-to-December league (Saudi Arabia, Japan, Korea, China, Brazil, Chile, Colombia ...) it
  plays **February to December**.
- **Apertura and Clausura** (a league format): September to early January and January to May.

Since 0.1.4 a new country can play **February to December** instead: the **Season** field in
the League window of its top division. Clubs then go up and down at New Year, and every
division below follows it. It cannot be combined with a split, Apertura/Clausura, a national
cup or a league cup yet.

0.2.0 (experimental): the game's own February-December countries **Japan, China, Brazil, Chile
and Saudi Arabia** can play **August to May** instead -- **Seasons of the game's leagues** on the
League Builder page. Their league starts in August, promotion and relegation happen in summer,
their cups move to August-May dates and their continental places come from the table that
ended in May. A division of yours under one of them follows it. Build the world again and start
a new career.

### Clubs I send to the Libertadores qualifying round stay at home

Fixed in 0.1.4 (#33). A club of yours sent to the qualifying round now takes the place of one of
the game's own entries in that round (the last one of the country with the most clubs in it, at
most half the round), so it plays the round. Update, **Install the modules**, **Build the
world** again and start a new career.

Since 0.1.6 the round gives away up to six of its eight places (#66); two stay with the game's
clubs. With more places than that, the leagues listed last get none, and **Check the plan**
says so.

### The same clubs play the Libertadores and the Copa Sudamericana

Fixed in 0.1.4 (#37). A club that is already in the game's Copa Libertadores, its qualifying
round or the AFC Champions League is no longer drawn into the continental cups Mod Studio builds
(Copa Sudamericana, AFC Champions League Two, the CAF cups, and since 0.2.0 the CONCACAF
Champions Cup, the OFC Champions League and the AFC Challenge League).

### Can the cup winner go to the Copa Sudamericana (or the Confederation Cup, the ACL Two)?

Yes, since 0.2.0 (#95). In the League dialog's **Europe** places, set the position to **Cup
winner** and pick the cup. In a new career nobody has won the cup yet, and a winner can already
have a place through the league; in both cases the place goes to the league's next club that
plays no continental cup, the way UEFA does it.

### Is there a cup for North America or Oceania?

Since 0.2.0: the **CONCACAF Champions Cup** (a knockout of up to 16 clubs, like the real one;
MLS fills the places your leagues leave) and the **OFC Champions League** (your leagues' clubs
only, the game has no league in Oceania). A new league in a CONCACAF or OFC country gets them
as its preset.

Asia got a third cup in 0.2.0 as well: the **AFC Challenge League**, below the AFC Champions
League Two, as the Conference League is in Europe. Give it a place with **Add place** in the
League dialog's **Europe** places (*AFC CHL* in the Leagues list); it is built only when a
league of your world sends clubs to it. After your places, the J1 League's 11th-14th, the
Chinese Super League's 10th-13th and the Saudi Pro League's 11th-14th fill it. It plays groups
of four and then a knockout, like ACL Two (a small field is a straight knockout).

### My league table shows the same club on every row

In 0.1.3 and 0.1.3.1, a split league or an Apertura/Clausura league in a new country (Egypt,
Venezuela ...) could show one club's name on every row of a phase table, over the right badges.
The first match between two of them then stopped on *"For games between users, 2 Controllers
are required"*, the phases were not played, and a playoff could come at the wrong time. Fixed in
0.1.4 (#37): each phase gets its own clubs, and a playoff starts at the end of its phase. Update,
**Install the modules**, **Build the world** again and start a new career.

### Where do I get real clubs and players for my new leagues?

From the NewLife Database (since 0.1.5.5): a separate download on the NewLife channel of our
[Discord](https://discord.gg/StQqtk3G3M), in parts per continent. Put the parts in one folder,
open it on **League Builder > NewLife Database**, pick leagues and press **Add to the recipe**:
each becomes a new league with its real clubs and squads. See section 8.4 of the
[Mod Studio guide](mod-studio-guide.md).

### Can I put a club the game already has into my new league?

Yes, since 0.1.4. In *New clubs*, select a place of the new league and press **Club of the
game...**. The club keeps its name, crest, kits, manager and players. If it plays somewhere in
the game (a league, a cup, a continental cup), you choose who takes its place there: a club of
the game that plays in nothing, or a new club you name. That way no competition of the game
changes its number of clubs. **Insert club** and **Remove club** change a league's clubs after it
was built; then **Build** again and start a new career.

### Can I move a club from one league to another?

Since 0.1.7, yes. A new club: *New clubs* > **Move to another league...**, it goes to the end of the
other new league with everything it has. Two clubs of the game's leagues (a promoted one for a
relegated one, say): *Game's leagues and clubs* > **Swap leagues with a club...**; they trade every
place, so the game's leagues keep their size. A club of the game into a new league: **Club of the game**
(see above). Build again and start a new career.

### Can I build only the new European format, with no new leagues?

Yes, since 0.1.4 (#36). On the *Build* page press **Only the new European cups...**: it builds a
world with the new Champions League and Europa League (and the Conference League when it is
ticked), with the game's own leagues and clubs. The scripts way is in
[how-to.md](how-to.md), Part D, Route 1.

**With a database mod (UML and the like):** the world carries its own copy of the competition
and team tables, made from the tables in **Settings**, and by default those are the game's own.
Point Settings to your database's `common\etc\pesdb` folder first, then build. Built from the
game's own tables, the world puts the default leagues back over your database's (#36). Keep the
world above the database mod in sider.ini, or the mod's tables hide the world's (empty league
tables). Since 0.1.7 the *Overview* and *Diagnostics* checks say when either is wrong.
Before 0.1.6 a world with only the European cups also left every league without a schedule at
the start of a career (#54); update and start a new career.

### Can the Premier League (or another league of the game) get a league cup?

Since 0.1.7: **Cups of the game's countries** on the *Build* page. Tick **League cup** next to
the league: 16 clubs of it and the league below (the rest through a pre-round in early
September), September to December. **Super cup** is there
too, only for countries where the game has none (Brazil, Chile, Scotland, Greece, the USA).

### Can I change the European places of the Premier League, LaLiga ...?

Since 0.1.7: **European places of the game's leagues** on the *Build* page. Tick **Own places
for this league** and set them like a new league's. Then build the world again.

### Can I rename the Champions League, the FA Cup ...?

Since 0.1.7: **Competition names** on the *Build* page, for every cup and continental
competition of the game and the continental cups the world builds, with a logo too. The game's
leagues: *Game's leagues and clubs*. The Conference League: its name box on *Build*.

### My cups and the Conference League have no logo

Since 0.1.5.5 every cup the builder makes gets one: the national cup, super cup, league cup,
pre-season cups, the new continental cups and the Conference League (#36; the game has no logo
for competition 174). Without a picture of yours an emblem with the cup's initials is drawn.
Your own: **Cup logos** in the league's window, **Logo** in *Pre-season cups*, and **Conference
League logo** on the *Build* page. Build the world again after you change one.

### Can I change a club's or a player's id?

For your **new** clubs and players, yes, since 0.1.4: **Club ID** next to the club and **Player
ID** on the player's Basics tab. Use it when a kit, crest or face pack was made for a certain id.
A new club's id is from the first one after the game's clubs (71578) up to 81919; a new player's
is above the game's highest, up to 399999. The game's own clubs and players keep their ids: its
kits, faces and your saves are tied to them.

### Can I edit a national team, or move a player to another club?

Yes, since 0.1.4, on the *Players* page. Pick *National teams* in the league list and a country:
**Call up players...** lists the players (it opens on that country) and puts the ones you pick in
the squad, at most 26. They stay at their clubs. In a Master League career the game picks its
own national squads, so the call-ups do not stay there. For a club, **Sign players...** brings players
from any club (a transfer: their old club loses them), and **Transfer to...** sends the selected
player to another club; a club has at most 40 players.

### Can I change the names and ratings of the players of my new clubs?

Yes, since 0.1.3.1: the *Players* page has a **Rating** field (changing it moves every ability
by the same amount), and **Name** takes a name of your own for the players Build makes for a new
club (FL P00001 ...). You can also bring in a whole squad from a table: *Players > Import a squad
from a table*.

### Why was every new club of mine as strong as a top side?

Until 0.2.0 every new club without a squad of its own started with the same copy of one squad
of the game, about 78 on average, so a sixth-tier side was a 4.5-star team. Since 0.2.0 Build
moves that squad to its division's level: about 72 in a top flight, 67 in the second division,
63 in the third, 60 in the fourth and 57 from the fifth down. Every player moves by the same
amount, so the squad keeps its spread. NewLife squads, clubs of the game, and players you edited
on the *Players* page are left as they are.

### Can a player or a manager get a picture without a 3D face?

Since 0.1.5.5, yes. A player: *Players* > select him > **Portrait** > **Choose...** a PNG or JPG;
Build makes it his small portrait in the squad lists (180 x 180). A manager: **Manager picture** in
**Edit club** (new clubs on *New leagues*, the game's clubs on *Game's leagues and clubs*), or
**Manager portrait...** on the *Players* page -- both set the same picture. Build the world again
after you change one.

### Can my new clubs play another formation than 4-2-3-1?

Yes, since 0.1.4 (#23). A new league has a **Formation** list in its window: pick one of the
formations the game's clubs use, and each new club gets a copy of the tactics of a club of the
game with that formation, its best eleven lined up for it. **Edit club** gives a single club
its own. On the *Players* page a new club's first eleven is drawn on a pitch: select a player,
click a place, and he goes there. Build again and start a new career to see it.

### How do I give my new club a home stadium?

Since 0.1.7: **Edit club** > **Home stadium**, pick a stadium of Stadium Server. Mod Studio writes the
line in Stadium Server's `map_teams.txt` with the club's id when you switch the world on, so you never
have to look the id up. Before 0.1.7: the *Stadiums* page, **Home stadiums**, add a line; the club
list there has the new clubs of a built world.

### My new country outside Europe has no clubs and no matches from the second season

A world built before Mod Studio 0.1.4 keeps some leagues of a new country outside Europe under
their continent's code (0.1.3: a top division with a division below it; 0.1.3.1: a league with
no division below it), and in July the game leaves such a league out of the next season. Builds
since 0.1.4 do not. **Checks** names such a league: build the world again and start a new career
(a career already running keeps what it lost).

### I switched the Conference League off and the Champions League / Europa League broke

A 0.1.3 problem, fixed in 0.1.3.1: with the Conference League off, the Champions League and the
Europa League still get their league phase of 36. A world built with it off on 0.1.3 or earlier
has to be built again; **Checks** points it out.

### I closed Mod Studio and my leagues were gone

Before 0.1.4 the leagues lived only in the open recipe until **File → Save recipe**. Since 0.1.4
every **Build** also keeps a copy in `%APPDATA%\FL26ModStudio\recipes\<world>.json`, and Mod
Studio opens the last recipe again when it starts. The world an older version built stays in the
game and keeps working; only its recipe has to be entered again to change it.

### A retired star came back as a 16-year-old with the same name and face

That is the game: in Master League a retiring player is turned back into a 16-year-old in place,
with the same id, name, face and potential. Since 0.1.5 **Install the modules** also puts in
`fl26regen`: a regen gets a new name (a family name and a given name of two other players of
his country), a new potential that his ratings at 16 do not give away, and a new face with the
portrait to match, one of 90 faces from nine parts of the world. The faces come as the livecpk
folder `FL26 Regen Faces`, which the install copies and loads with a `cpk.root` line of its
own. The save does not keep names, so after every load the module finds the regens again and
gives each the same name and face back. It works in new and in running careers.

### Can I switch the regens off?

Yes, since 0.2.0. On **Lua modules** untick **Hide the League Builder's own modules (fl26...)**
so ours show, untick `fl26regen` and press **Apply**. Mod Studio writes that down in
`modules\fl26-off.txt` in the Sider folder, so **Build**, **Install the modules** and switching
worlds leave it off instead of turning it back on, as they do with every other module. The
game then makes its own regens: its own potential and names, no faces from the regen face pack.
Tick it again and **Apply** to switch it back on. Only `fl26regen` can be kept off this way.

### All the players of my new clubs look the same

The game gives a player without a face of his own one default look, and every player of a new
club (or of an imported squad) is such a player. Since 0.1.5.5 the Build lists them in the world
file, and `fl26regen` gives each a face of the regen face pack that fits his nationality, with
the portrait that goes with it, the same face every time. A player you gave a **Face** keeps his
own; one with only a **Portrait** gets the 3D face and keeps his picture. It needs **Install the
modules** (the face pack comes with them), and the world built again with 0.1.5.5.

Before 0.1.9 the 3D face of a new player never showed, only the portrait: the game draws a
player from his appearance record, and a player the Build made has none. 0.1.9 puts one in.
The game has room for about 2,000 of them (FL26 itself fills the rest), so in a world with
more new players the others keep the default look, and sider.log says "appearance table
full". A player you gave a **Face** made for another player takes that player's appearance
too, so his arms and legs have the face's skin colour (GitHub #102).

### What should I send when something is wrong?

1. In Mod Studio: **Tools > Diagnostics > Copy a report**, and paste it into the issue.
2. The files, from your Sider folder:
   - `SiderAddons\sider.log` (written again every time the game starts, so copy it right after
     the problem)
   - `SiderAddons\fl26join.log`, if the problem is about a Master League season
   - `SiderAddons\livecpk\<your world>\fl26world.txt`
3. What you did, what you expected, and what happened instead. A screenshot helps.
4. If the game crashed: the *fault offset* from Windows Event Viewer (*Windows Logs >
   Application*, the error for `FL_2026.exe`).

## The scripts (the older way)

### Is there a program instead of all the scripts?

Yes: FL26 Mod Studio, a Windows program (beta). It installs the modules, builds leagues and
clubs, edits the players of any club, adds faces, installs other mods and content servers,
and keeps restore points. Download it from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest);
the guide is [mod-studio-guide.md](mod-studio-guide.md) ([hrvatski](mod-studio-guide.hr.md)).

### Every new club has the same manager, "Jorge Jesus"

That was a world built before 2026-09-26. A club names its manager by an id in `Team.bin`,
and `mkworld.py` gave each new club a new id without a manager to go with it, so the game
filled every gap with a copy of its first coach. `mkworld.py` now also writes `Coach.bin`,
with a placeholder manager for each new club (`FL M0001`, `FL M0002`, ... with the club's
own country). To fix a world you already have without rebuilding it:

```
python tools\mkcoaches.py <your livecpk world>\common\etc\pesdb --coach C:\fl26\pesdb\common\etc\pesdb\Coach.bin --out Coach.bin
```

then move the new `Coach.bin` into `<your livecpk world>\common\etc\pesdb`. (`--coach` is the
shipped file you unpacked when you built the world.) Delete it again to undo. Checked on
2026-09-26 in Edit > Managers and on the pre-match screen of an exhibition: every club shows
its own manager. Not checked yet: a Master League season with them (sackings, job offers), and
whether a career saved before the change picks them up -- start a new one to be sure.

### How do I rename the new clubs?

The new clubs are called `FL 0001`, `FL 0002` and so on because that is the pattern
`mkworld.py` gives them. There are two ways to change that.

**When you build the world.** `mkworld.py --club-name "My Club %04d"` changes the pattern for
every club it makes (`%04d` is the club's number). `--league-name` does the same for the leagues.
Use this for a different naming style, not for individual names.

**Afterwards, one club at a time: `tools/rename.py`.** The names live in the world's
`common\etc\pesdb\Team.bin`. That file is packed, so a hex editor will not work on it. The
tool unpacks it, changes only the name and the three-letter abbreviation, and packs it again.
Squads, kits, competitions and ids are not touched.

```
python tools\rename.py --root <your livecpk world> --list
```

prints every club in the file: team id, abbreviation, name. Write a CSV file with one club per
line: the team id (or the current name), the new name, and optionally a new abbreviation:

```
72318,Dinamo Example,DIN
FL 0002,Hajduk Example,HAJ
FL 0003,Only The Name Changes
```

and apply it:

```
python tools\rename.py --root <your livecpk world> --names names.csv
```

A name may be up to 69 bytes. The abbreviation must be three plain letters or digits. If any
line is wrong (a club that does not exist, a name that is too long), nothing is written, so a
typo never leaves a half-renamed world. The original file is kept as `Team.bin.bak`.

These are the same two fields `mkworld.py` fills in when it names the clubs. The tool changes
nothing the builder does not already write.

**The managers, the same way.** A file with the club and the manager's new name, one per line:

```
FL 0001,Ivan Example
FL 0002,Marko Example
```

```
python tools\rename.py --root <your livecpk world> --managers managers.csv
```

It renames whoever the club employs, in the world's `Coach.bin` (up to 45 bytes). `--list`
shows each club's current manager. A world built before 2026-09-26 has no `Coach.bin` yet:
run `mkcoaches.py` first (see the question above).

**After renaming, check your Edit save.** If you have
`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000` from before the
change, the game reads it instead of the data files and keeps showing the old names. Move it
somewhere safe (do not just delete it if it holds edits you care about), start the game, and
let Edit mode write a new one. From then on the new save carries the new names.

### Edit mode says "You cannot edit this strip" for my new clubs

Each new club borrows the kit of a club of the game, and that kit is a licensed one: Edit mode
refuses it. Since 0.1.6, tick **Kits you can edit in the game** on the Build page and **Build
the world** again. The new clubs then wear a plain kit that Edit > Teams > Strip changes like
any other, Paste Image included. Move an old `EDIT00000000` aside first if the kits do not
change.

### Kit Server does not show the kits of my new clubs

sider.log says `we have kitserver kits for: <id>, but the team is unlicensed. Disabling kits.`
Kit Server dresses a club only when the club has a kit of its own in the game's data, and with
**Kits you can edit in the game** ticked the new clubs get none (they wear the engine's plain
kit). Untick it on the Build page and **Build the world** again: each new club then borrows a
kit, and Kit Server swaps it for the one your `map.txt` names (the club id from New clubs, e.g.
`71579, ISL\Arema`). The two do not go together: a kit from Kit Server, or a kit you change in
Edit mode.

### Only my new divisions play the FA Cup

Fixed in 0.1.6. The game fills a country's cup from the first league of the country it finds,
and a new League One under the Championship was found before the Premier League, so the FA Cup
went to League One and League Two. Now a new third division or lower leaves the cup to the
Premier League and the Championship. The super cup is filled the same way, and in a test on
2026-10-01 the first club of a new League One played the Community Shield against the champions;
0.1.6 swaps such a club for one of the top flight. **Install the modules**, **Build the world**
again and start a new career.

### Do the new clubs show up in the game's Edit mode?

It depends on which league a club is in.

- **Clubs added to a league the game already has: yes.** Measured on 2026-09-11 with ten clubs
  added to the Premier League. In Edit > Teams > Premier League the list scrolls past
  Wolverhampton to the new clubs, and each one can be opened and edited like any shipped club.
- **Clubs in a new league of our own: yes, with `sider/experimental/fl26editlist.lua`.** Without
  it, no. Edit mode's list of leagues is not read from the data files: one function in the game
  hands every Edit screen the same thirty competition slots, written into its code, so a new
  league whose slot is not among them never appears. The module adds the slots of your leagues
  to that list (it needs `fl26comptab.lua`, loaded before it). Checked on 2026-09-26: with it,
  Edit > Teams, Edit > Players > Edit Player, Transfer and Managers list every added league of
  our test world (32 were missing before), and each opens with its clubs and squads. The "Other" heading (free agents,
  created players) is still there, but it no longer comes last: it sits just before the block
  of added leagues. Edit > Competition Structure and Edit > Competitions have not been checked
  with it.

The new leagues and their clubs do show up where it matters for playing: Kick Off > League,
Master League's Select Team list (with `sider/experimental/fl26comptab.lua` and
`fl26slotnames.lua`) and, with `fl26catlist.lua`, Database > Competition Info.

The same rule about the Edit save applies here too. After you rebuild a world, move the old
`EDIT00000000` aside before deciding that a change did not work. An Edit save written before a
data change hides that change.

### Edit mode forgets what I change on the new clubs

Fixed in 0.1.8 by `fl26edit.dll` (GitHub #55), which Build installs with the other modules.
The game's Edit save holds the changed clubs in three tables (team data, squad, tactics) with
room for 750 clubs each, and every save fills them with the game's own 749 first. So a change to
a club of ours (shirt numbers, formation, colours, a .ted squad) was dropped by the next save.

The module gives those tables room for 2048 clubs. The `EDIT00000000` file stays exactly what
the game writes: the first 749 clubs of each table, so the game without the module still loads
it. The clubs past 749 go to `EDIT00000000.fl26x` next to it, and the previous one is kept as
`EDIT00000000.fl26x.prev` (for when you answer No to "Overwrite data. Proceed?"). Keep the three
files together when you move or back up your Edit save.

Checked on 2026-10-05: a new club's colour changed in Edit mode, saved, and still there after a
restart of the game; a second change answered with No was gone after a restart, and the first
one stayed. In sider.log, `fl26edit: live` means the module is in; `install FAILED` says why it
stood aside (Edit mode then works as before).

### How do I edit the players of the new clubs, if not in Edit mode?

Edit mode reaches a club through its league, so players of a club in a new league can be
reached there only with `fl26editlist.lua` installed (see the question above). Players of clubs
you added to a league the game already has can be edited in Edit mode as usual.

Outside Edit mode, the easiest way is the editor with a window:

```
python tools\playereditor.py --root <your livecpk world>
```

Pick a club, pick a player, change any field, **Apply**, **Save**. **New player** creates one,
**Up** / **Down** change the squad order (the green rows are the starting eleven). It uses the
same checks as the spreadsheet route below.

For many players at once, edit the world's data files with `tools/playeredit.py`, the same way
`rename.py` does clubs. The players live in the world's `common\etc\pesdb\Player.bin`, and
which club each one plays for, with his shirt number and his place in the squad, in
`PlayerAssignment.bin`. Every field of a player is known (see
[player-record.md](player-record.md)), so you can set any of them, and create new players.

**1. Export the club to a spreadsheet.**

```
python tools\playeredit.py --root <your livecpk world> --export club.csv --club 72318
```

writes one line per player of that club with every field under its own name: position,
position ratings, height, weight, age, nationality, foot, the 25 abilities, form, injury
resistance, playing style and the skills, plus club, shirt number and squad order. `--club`
also takes the club's name as `rename.py --list` prints it. Without `--club` you get every
player in the file, including the game's own, which is handy to look up a nationality or a
playing style to copy.

**2. Change what you want** in Excel, LibreOffice or any text editor, and save it as CSV
(UTF-8). You can delete the columns you do not change; an empty cell leaves that field alone.

**3. Import it.**

```
python tools\playeredit.py --root <your livecpk world> --import club.csv
```

Every line is checked first: a rating outside 40-99, an unknown position, a height the game
cannot store, two players with the same squad order. If anything is wrong, nothing is written
and you get the whole list. The original files are kept as `Player.bin.bak` and
`PlayerAssignment.bin.bak`.

**Creating a player.** Write `new` in the `player` column and name the club:

```
player,club,like,name,shirt,Registered Position,Speed,Finishing
new,72318,180590,Ivan Example,27,CF,84,86
```

The new player starts as a copy of the player in `like` (or of the club's first player) and
then takes every value on the line, so fill in as many columns as you like. He gets a new
player id, the shirt number you gave (or the first free one), and the last place in the squad.

**The starting eleven is the first eleven of the squad order.** The formation gives them
their places in a fixed order. For the new clubs' default 4-2-3-1 that is order 0 to 10 =
GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF (a club given another formation in Mod Studio
has that formation's order; `python tools/mktactics.py --base <tables> --list` prints them). To change who starts, change the `order`
column (every player of a club needs a different number). If a goalkeeper sits at order 1
he will start at centre back, which is what a squad written in any other order looks like.

`tools/players.py` still does the three quick jobs it always did (rename, shirt number, copy
a whole player from another) with a four-column CSV; `playeredit.py` does all of that too.

**Then start a new career.** A Master League career takes its own copy of the squads when it
starts, so a career you are already in keeps the old players. If an old `EDIT00000000` is in
your save folder, move it aside first, for the reason given in the first question.

Tested in the game on 2026-09-24: a club's whole squad rewritten this way showed the right
names, positions and ratings in Select Team and Game Plan, and played a Master League match.
If something looks wrong, put the `.bak` files back and open an issue.
