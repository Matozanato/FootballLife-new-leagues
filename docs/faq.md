# Questions people ask

The first part is about **FL Mod Studio**, the program most people use. The second part is
about the command-line scripts it grew out of. Your question is not here? Open an
[issue](https://github.com/Matozanato/FootballLife-new-leagues/issues) with the report
described in [What should I send when something is wrong?](#what-should-i-send-when-something-is-wrong)
Just a question, not a bug? Ask on [Discord](https://discord.gg/StQqtk3G3M).

## FL Mod Studio

### Does Mod Studio work with Football Life 2027?

Yes, from 0.3.0: the same program for FL26 and FL27. In **5. Settings → Game folder** pick the
folder with `FL_2027.exe`. Each game keeps its own tables and saves. In FL27 the Champions League
and Europa League from the league phase on are FL27's own; Mod Studio sends your clubs into them
and plays the qualifying rounds, and the Conference League is Mod Studio's. What is different and
what is not done yet: [guide](../guides/en/mod-studio-guide.md#football-life-2027) ·
[known issues](known-issues.md).

### FL27 closes while a new Master League is being created

Start FL27 through its launcher: **FL 2027 start.exe**, its shortcut, or **Start the game** in Mod
Studio. FL_2027.exe started directly (or Sider and the game exe started apart) can close while a
new Master League is created or on its first days; started through the launcher it did not.

### I updated Mod Studio. What do I do now?

Every update can change the modules and the world's tables. After updating, open **Home**: if
it has a red line about Mod Studio's modules, press **Install now**. Then on **Build and edit
your world** press **Build and install** again. If you play a ready modpack, drop the new
modpack zip on **Import your world** instead: Mod Studio sees it is a newer version of the world you have and
puts it in place of the old one. Then start a **new Master League career**: a career started before the build was made
with the old world and does not pick up everything that changed.

Download the whole zip from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) and
unzip the whole folder. Since 0.1.3 the program is a folder, not one file: running
`FL26ModStudio.exe` from inside the zip, or copying only the `.exe`, does not work. From 0.1.1
on, *Help > Check for updates* does all of this for you; your settings and projects stay.

### The game crashes a few seconds after I start it

A crash in the first ten seconds or so happens on a clean game too, with none of our modules
installed. It depends on how the game is started. Start it **through the launcher** (the
shortcut the game installed), not by running `FL_2026.exe` (or `FL_2027.exe`) directly: measured on our side, the
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
([by-hand.md](developers/by-hand.md#a6-check-your-game-version), step A6) and start the game again.

### "Other European Leagues" or "Other Latin American Teams" is gone from Select Team

Select Team has few free places, and four of them belong to the game's "other clubs" groups
(Sparta Prague, APOEL ... / Penarol, LDU Quito ...). Up to 0.1.6 a world of 30 or more leagues
took them (#73). Since 0.1.7 they are the last places a league gets: up to 32 leagues every
group stays, the 33rd and 34th take the small *Other Clubs (Africa)* and *Other* groups, the
35th to 37th play without a place in Select Team, and only the 38th and 39th take the two big
groups. **Check the plan** names each league that takes a place; put the leagues you want to
start a career in first. After updating, **Build the world** again and start a new career.

That was Mod Studio 0.2.1 and earlier. Now the leagues after the 32nd take regulation ids from 255
downward, each with a Select Team slot of its own (124 up), before any id that sits on one of
those groups: the groups stay and every league is selectable until those ids run out.

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
keeps the top division alone. A third division stays out of the cup unless you tick **Its best
clubs play the country's cup too** in its League dialog:
- Under the game's second division (like National under Ligue 2), the game's cup then takes its
  two divisions and the first clubs of the third: 36, 40 or 44 clubs in all, as the real Coupe de
  France takes the lower leagues.
- In FL 2027, a third division of a new country can join that country's national cup the same
  way, up to 44 clubs.

Start a new career after the Build.

**Why does my cup have 20 clubs when my two divisions have 22?** The game's cup screens can
draw a bracket of 2 to 16, 18, 20, 24, 28, 30 or 32 clubs and nothing in between; a cup of 22
crashed them (#74). So the cup takes the largest of those sizes: the whole top division and the
first clubs of the one below. A field of 33 to 43 clubs becomes 32 (#95). *Check the plan* says
so on the cup's line. This is on purpose, not a bug.

Two other cups have no such limit:
- **League cup** (the tick under the national cup): a single-match knockout of the top
  division and the one below, up to 44 clubs, late September to December. The top
  division's clubs get the byes and start in the second round.
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

Experimental: the game's own February-December countries **Japan, China, Brazil, Chile
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
(Copa Sudamericana, AFC Champions League Two, the CAF cups, the CONCACAF
Champions Cup, the OFC Champions League and the AFC Challenge League).

### Can the cup winner go to the Copa Sudamericana (or the Confederation Cup, the ACL Two)?

Yes (#95). In the League dialog's **Europe** places, set the position to **Cup
winner** and pick the cup. In a new career nobody has won the cup yet, and a winner can already
have a place through the league; in both cases the place goes to the league's next club that
plays no continental cup, the way UEFA does it.

### Is there a cup for North America or Oceania?

Yes: the **CONCACAF Champions Cup** (a knockout of up to 16 clubs, like the real one;
MLS fills the places your leagues leave) and the **OFC Champions League** (your leagues' clubs
only, the game has no league in Oceania). A new league in a CONCACAF or OFC country gets them
as its preset.

Asia has a third cup as well: the **AFC Challenge League**, below the AFC Champions
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
open it on **League Builder > NewLife Database**, pick leagues and press **Add to your world**:
each becomes a new league with its real clubs and squads. See section 8.4 of the
[Mod Studio guide](../guides/en/mod-studio-guide.md), and step by step:
[Make your own leagues and packs](../guides/en/make-your-own-leagues.md).

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
[by-hand.md](developers/by-hand.md#route-1-the-new-format-with-the-games-own-leagues-only-no-new-leagues), Part D, Route 1.

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
the league: it and the league below, up to 44 clubs, one match a round from late September to
December, drawn at random, the league's clubs with the byes. **Super cup** is there
too, only for countries where the game has none (Brazil, Chile, Scotland, Greece, the USA): the
champion against the cup winner, in late July, or at the end of January, after the season, in a
country that plays February to December (Brazil, Chile, the USA). That one needs at least one new
league in the world.
Each of the two takes its own **Logo** in that window.

### Can I change the European places of the Premier League, LaLiga ...?

Since 0.1.7: **European places of the game's leagues** on the *Build* page. Tick **Own places
for this league** and set them like a new league's. Then build the world again.
It works for every top division of the game, also the ones that ship with no European places
(Russia, or the leagues outside Europe). **UEFA ranking** on the same page gives every league its
places by UEFA's rules in one go.

In FL 2027 Belgium's Jupiler Pro League is one league of 18 with no split, and before the next
version its clubs got no European place in an FL 2027 world. Build the world again with the
new version and the Jupiler Pro League has its places again.

### Can I pick the clubs of the first season's Champions League or Europa League?

Yes, since 0.1.8: **First-season European clubs** on the *Build* page. Pick the clubs of the
Champions League, the Europa League and the Conference League league phase of a new career's
first season. The automatic choice fills the places you leave empty. From the second season on,
the league tables decide again.

### Can I put the clubs of a league in my own order in Select Team?

In FL 2027, yes, in the next version: *New clubs* > *More* > **Order in Select Team...**. Drag the
clubs into the order you want, then Build again and start a new career. Without it, and always in
FL26, a league's clubs are listed A-Z. The order of the divisions of a country is not yours to
set: Select Team lists them down the promotion chain, the top division first. The order of the
countries is: **League order** on the *Build* page.

Colombia's Liga BetPlay DIMAYOR and the MLS are two tournaments a season, each with its own
table. **Liga BetPlay DIMAYOR I** (or **MLS First Round**) in that list goes by the first
tournament's table alone; **Liga BetPlay DIMAYOR** (or **Major League Soccer**), just under it,
goes by the whole season: both tables added together, counted when the second tournament ends.
Give places to one of the two, not both.

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
is the first free one above the game's highest, up to 262143 (the game packs a player id
into 18 bits; a higher id crashes the game when a Master League is created). The game's own clubs and players keep their ids: its
kits, faces and your saves are tied to them.

### Do the ids change when I build my world again, or update it?

No. A league, a new club and a new player keep the id the first Build gave them, Build after
Build: when you add or remove a league in front of them, when you rename a club, and when you move
a club to another league of the world. An id a club or player once had is not given to another one
while a free id is left. If you share a world and update it, compare the two zips before you
publish: `python tools/checkids.py <published zip> <new zip>` lists every id that moved.

### Updating a shared world without breaking careers

A Master League career holds the ids of the clubs, players, leagues and cups it was started with.
A new version of a world keeps those careers working only if every one of those ids is still there.
Mod Studio checks that for you. It cannot tell whether an id still stands for the same club: a club
with another name under its old id is taken as the same club renamed, so the Build log and Install
list those clubs for you to look at.

1. **Export the world...** asks for a version name (for example "My World 2"). The zip carries
   the version and a list of every id in it (`fl26ids-ledger.json`). The list also has the
   world's lineage: a code the first version gets and every later version keeps, so another
   author's world with the same name is never taken for yours. Your PC keeps every version you
   shared, by its number (`%APPDATA%\FL26ModStudio\recipes\ledgers`), and the recipe and the
   world's plan get the lineage (`id_lineage`). Every zip gets a number of its own, also a test zip
   and a zip you did not keep, so no two zips of a world share one.
   - Tick **A test zip** to export without keeping the version as "the version you shared last".
     A tester who installed a test zip gets Replace, not Update, for the next real version, unless
     that version has exactly the same ids.
   - If careers of the version before do not go on in the new zip, Export asks whether to keep it
     as the version you shared last. An export from the command line (`release.py`) does not keep
     such a zip.
   - Export and Build stop, and say which file, when the newest version your PC keeps cannot be
     read, or when the recipe has `id_lineage` but no list of that lineage is on this PC (another
     PC, or a new Windows user). Put the `.fl26ids` file of the version you shared last in the
     folder above (its file name does not matter), or set the recipe's `id_ledger` to it. The
     world's plan keeps `id_ledger` too, so an export without the recipe finds it;
     `release.py --recipe` hands the export the recipe itself.
   - *Make it editable* keeps the list of a world you got as a zip (not of a test zip).
2. The next **Build** of that world pins its ids to the latest version of its lineage. A renamed
   club or league keeps its ids, and so does a club moved to another place in its league: its
   players' ids go with it. A renamed player keeps his id when his place is the same and either
   his birth date says he is the same one or the new name is the old one spelt another way: the
   same letters without accents, two letters swapped, or one letter more or less (never one letter
   for another: Petrović and Petković are two players). A birth date of 1 January, or one two
   players of the club share, does not say he is the same one; with such a date he keeps his id
   only by a spelling. The Build log lists the players kept by a spelling.
   A new league or cup gets ids no version gave out, also none of a league or cup taken out. A new
   club (also a NewLife club and a club that takes a game club's places) gets a team id no club of
   the shared version has or had, while free ids are left. A retired player's id is not given to
   another player: the Build stops if it would be. **Check the plan** warns you beforehand if
   something of the shared version would be lost. A league that plays another way than in the
   shared version (clubs, rounds, promotion, relegation) gets a warning in the Build log.
3. If a club, player, league or cup of the shared version is gone, the Build stops and names it.
   If you removed it on purpose (for example, two copies of one player merged into one), press
   **Retire these and Build again**. They are written into the recipe (`id_retire`). Retired
   players: careers go on, and where one was, a career may show a stand-in player. Retired clubs,
   leagues or cups: careers of the shared version cannot go on, because they have them, so Install
   offers those players Replace. A league or cup id that changed, or an id that now belongs to
   another league or cup, cannot be retired: put it back as it was. If a club that is still in the
   world lost most of its players' ids, Build warns that this looks like a squad it did not follow,
   and asks again before it retires them.
4. A player who installs the new zip over the version they have gets **Update** in place of
   Replace when it is a later version of the same lineage made from their version (their version
   is in its list of versions before), every club, league, cup and player id of their version is
   still there, and only players were retired. Their careers and save folders are not touched, so
   they load their career and go on. If an Edit save from before is in the game's save folder,
   Install asks: **Keep it** to continue the career, **Move it aside** for a new Master League. What
   a running career shows of the new version's changes is not checked in the game; for all that is
   new, start a new Master League.
5. **New leagues and cups go after the old ones.** A career also holds the competitions by their
   place in the world's competition tables (`Competition.bin`, `CompetitionRegulation.bin`,
   `CompetitionEntry.bin`). The Build that follows a shared version keeps every row of that version
   where it was, and every entry id stands for the same club in the same competition and place.
   New leagues and cups go after them, wherever they are in your recipe, and new entry ids come
   after the version's highest. A new league under a league of the shared version is not linked
   to it in the tables when it exchanges no clubs with it (promotion and relegation 0), so the old
   league stays as it was. The Build log says what it kept (`rows:`). New leagues and cups only
   show up in a new Master League; Install says how many there are and that your careers go on
   without them.
   - The zip of the version carries the order of its tables in its id list. A version exported
     with an older Mod Studio (every version up to now) has no order in its list. Set the recipe's `id_tables` to that
     version's world zip (or to the world folder installed from it), and the Build reads the order
     there. The Build stops if that zip is another version. A world installed from that zip and
     not built again on this PC is read without the setting. When none of these is there, the
     Build lays the tables out the old way and warns that careers may not go on.
   - Careers of the shared version do not go on when a place in its leagues and cups is gone or
     holds another club, or when a club new to the world is entered in one of them. A career of that
     version has none of the new club's players. Then the Build log, the export and Install say so,
     and Install offers Replace.
   - A league or cup of the shared version whose row changed in place (legs, or a link to a new
     league below that exchanges clubs with it) or that has a new place for a club the world
     already had gets a warning, as a league played another way does. A new club only in new
     leagues and cups is listed, not stopped: a career of the shared version does not play those
     competitions. What such a career does with those clubs is not checked in the game yet.

Install offers Replace with a warning instead when Mod Studio cannot tell the zip is a later version
of the world installed (another lineage: another world with the same name, or one its author started
again), when it is a version of the lineage not made from the one installed (a test zip, or a version
made on another PC), an older version or the same one, when it takes out clubs, leagues or cups of
the version installed, when ids of it are gone, or when a place in its leagues and cups is gone,
holds another club or has a club new to the world, or a row of its competition tables moved (step
5). A world installed from an older zip without a list
gets Update only if its ids are those of a version the new zip comes after (or the new zip's own
ids, when the new zip is not the world's first version: a fix with the same ids), or if at least
90% of its leagues and of
its clubs' names are the new zip's and every id is kept, or at least 90% of its leagues and half of
its clubs' names when every id is kept. A recipe without `id_lineage` pins to a version on your PC
only if at least 60% of that version's leagues or clubs are in it. Between 20% and 60%, Build and
Export ask: **It is that world** writes the lineage into the recipe, **A different world** leaves that
version out from then on.

### I installed a newer version of a world. Where are the files I had changed?

Mod Studio takes the older version out before the new one goes in, so the world is clean. Files
you had added to the world's folder, and files of the world you had changed after installing it,
are not deleted: they are in `SiderAddons\ModStudio\kept\<world>-<time>`, in the same folders as
before. The line shown after the install and the **Ready to play** window name the folder. Copy
back what you still want.

A file you copied over one of the world's files (a face or a kit from another pack) counts as
changed, whatever date it has. For a world installed with an older Mod Studio (0.3.0, or a beta up
to beta 4), Mod Studio can only go by the files' dates: a file you copied there from the same
world's own files is not told apart, and a file you only opened and saved unchanged is kept as well.

### I changed a world I installed from a zip, and the changes were gone

A world from a zip (a Modpack) is built already, and its own recipe is read again from it when you
make it editable. Do it in this order:

1. **2. My world → Make it editable...** (the button shows only for a world from a zip) → **Yes**.
2. Then change what you want: leagues, clubs, cups, trophies, the Build options.
3. Then **Build and install** on the **Build** tab, and start a new Master League.

Changes made before step 1 to the leagues (clubs, names, kits, crests, cups, calendar, format) and
to the world's settings are not kept; players' names and squads, the edit tab, a league you renamed
and a league you added are. While such a world is open, the pages where those changes are made say
so at the top.

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

In Mod Studio older than 0.2.0 every new club without a squad of its own started with the same
copy of one squad of the game, about 78 on average, so a sixth-tier side was a 4.5-star team. Now
Build moves that squad to its division's level: about 72 in a top flight, 67 in the second division,
63 in the third, 60 in the fourth and 57 from the fifth down. Every player moves by the same
amount, so the squad keeps its spread. NewLife squads, clubs of the game, and players you edited
on the *Players* page are left as they are.

### Can a player or a manager get a picture without a 3D face?

Since 0.1.5.5, yes. A player: *Players* > select him > **Portrait** > **Choose...** a PNG or JPG;
Build makes it his small portrait in the squad lists (128 x 128, the size of the game's own portraits). A manager: **Manager picture** in
**Edit club** (new clubs on *New leagues*, the game's clubs on *Game's leagues and clubs*), or
**Manager portrait...** on the *Players* page -- both set the same picture. Build the world again
after you change one.

### Can my new clubs play another formation than 4-2-3-1?

Yes, since 0.1.4 (#23). A new league has a **Formation** list in its window: pick one of the
formations the game's clubs use, and each new club gets a copy of the tactics of a club of the
game with that formation, its best eleven lined up for it. **Edit club** gives a single club
its own. On the *Players* page a new club's first eleven is drawn on a pitch: select a player,
click a place, and he goes there. Build again and start a new career to see it.

A new club with no formation set (for it or its league) does not play a fixed 4-2-3-1:
Build gives it the formation, of those the game's clubs play, that gives
most of its best players their own position, and lines its best eleven up in it. The *Players*
page shows that formation; when you change the club's order there, the club keeps it.

### How do I give my new club a home stadium?

Since 0.1.7: **Edit club** > **Home stadium**, pick a stadium of Stadium Server. Mod Studio writes the
line in Stadium Server's `map_teams.txt` with the club's id when you switch the world on, so you never
have to look the id up. Before 0.1.7: the *Stadiums* page, **Home stadiums**, add a line; the club
list there has the new clubs of a built world.

Without a line of Stadium Server the club plays at a stadium of the game: Build gives every new
club one of the game's stadiums by its league's tier and country; **Edit club** > **Game stadium** picks another one. For a world
you imported (the Modpack): **Stadiums** > **Your world's clubs**, **Game stadiums automatically**
or **Choose a game stadium...**, then Save and start a new Master League.

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
game and keeps working; only its recipe has to be entered again to change it. Today there is no
saving at all: your world saves itself a moment after each change.

### New world replaced my world's leagues

From 0.2.4 to 0.3.0 **File → New world** called every new world `_FL26MyWorld`, and its first
change was saved over `%APPDATA%\FL26ModStudio\recipes\_FL26MyWorld.json`, the recipe of your
own world of that name. The world in the game was not changed (until a **Build** of the new one).
Since the fix a new world gets a free name (`_FL26MyWorld2`, `_FL26MyWorld3`...), and a recipe of
another world is never written over: it is moved to `recipes\<world>.json.prev` first. If it
happened to you before the fix and the world is still in the game: **File → Open a world...**
and pick `leaguebuilder-plan.json` in the world's folder (`livecpk\<world>\`); Mod Studio reads
the world's recipe back from it.

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

Yes. On **Lua modules** untick **Hide Mod Studio's own modules (fl26...)**
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

### I imported kits, but the game still shows the old ones

Clubs that already had a line in Kit Server's `map.txt` keep that line: **Import kits** skips them
unless you tick **Replace kits already set** in the import window. Import again with it ticked,
press **Save** (it writes `map.txt`) and start the game again; Kit Server reads its kits only when
the game starts.

To see what is wrong with a line, tick **Only lines with problems** on the Kits page and hold the
mouse over a yellow line: the reason shows as a tooltip. The most common one is "... not found in
the library": `map.txt` sends the club to a folder (such as `Premier League\Newcastle`) that is
not in Kit Server's kits folder, so the game has nothing to show. The **Library** tab lists the
folders that are really there. Point the line at one of them, or select it and press **Remove**.

A club with two lines switched on wears the kit of the **last** one: Kit Server reads `map.txt`
from top to bottom and each line for the club replaces the one before. Mod Studio marks the
earlier line ("only the last one counts"), and adding or changing a club's line switches its other
lines off.

### The stadium is completely black

Not a Build problem: Stadium Server's `map_teams.txt` sends the home club to a stadium folder
that is missing, or only half installed (a wrong folder name, a wrong slot, a stadium that was
not unpacked whole). The game loads nothing and the stadium is black. Open the **Stadiums** page,
tick **Only lines with problems** and hold the mouse over the club's line to see why. Point it
at a stadium the **Library** tab lists, or remove the line and the club plays in its old stadium
again. Press **Save** and start the game again.

### A player is a free agent, or has no face, in the world I built

A world carries a full copy of the game's database (players, clubs, who plays where) from the
moment it was built, and it sits above the game. Anything newer that a game update or a face
update brings for the same players is covered by that copy. After such an update press
**Settings > Unpack the game's tables** again and **Build** again; then the world has what your
game has now. A ready-made world from somebody else (an exported world, see the guide 9.1) was
built from that person's tables; Mod Studio reads a recipe back from it when it starts with that
world switched on, so you can Build it again on yours (a few parts, such as pre-season cups and
competition names, do not come back: the guide 9.1 lists them).

### I cannot remove any more players from my new club

A new club keeps at least 18 players. In 0.2.1 the Players page counts only the club's own
squad for that rule and forgets the players you signed for it, so it can refuse even when the
list shows 30 or more. Build itself counts the signings. Until the fix, remove one of the signed
players instead (that always works), or leave the extra player in.

### Import your world (or Build and install) says "Windows does not let Mod Studio write in ..."

The game is installed under `C:\Program Files` or `C:\Program Files (x86)`. Windows lets only a
program run as administrator change files there, so Mod Studio cannot copy mods, modules or a
world into the game's `SiderAddons` folder or edit `sider.ini`. Before 0.2.4 this showed up as a
`PermissionError [WinError 5] Access is denied` error. Do one of these:

1. **Run Mod Studio as administrator.** The message has a **Restart as administrator** button
   (Windows asks first), or right-click `FL26ModStudio.exe` > *Run as administrator*. Run as
   administrator, Mod Studio cannot take a file dragged from Explorer: use **Choose a file...**
   on Import your world instead.
2. **Move the game out of Program Files**, for example to `C:\Games\Football Life 2026`
   (copy the whole folder, start the game once from there), then choose the new folder in
   **Settings > Game folder**. This is the better fix: nothing needs administrator rights then.

The Home page shows the same message as long as the game folder is not writable. If Mod Studio
already runs as administrator and still says it, the folder or a file in it is read-only, or
another program (the game, an antivirus) holds it.

### Import your world says "The game folder's path is too long for ... file(s) of this mod"

Windows opens a file only while its whole path, from the drive letter to the file name, is at most
259 characters long, unless long paths are switched on in Windows (they are off by default), and
the game cannot open longer paths even then. A world puts some files deep into
`SiderAddons\livecpk\<world>\...`, so with the game in a folder whose path is long (a Steam
library, a folder in Documents with a long user name) those files would end up past the limit:
they would be missing in the game.

Mod Studio itself is not stopped by the limit: it unpacks and copies such files anyway (before the
fix for B400 the import stopped with `[Errno 2] No such file or directory` on a file in
`trophies\...`). It checks every file before Install and says how long the game folder's path may
be. To fix it, move the game to a shorter folder, for example `C:\Games\FL` (copy the whole
folder, start the game once from there), choose the new folder (**Game ▾**) and import the world
again. If you answer Yes to *Install anyway?*, the world goes in as it is: everything else works,
but the files the message counts are missing in the game.

### An antivirus removed fl26swiss.dll (or another of Mod Studio's DLLs)

Some of Mod Studio's modules are a `.lua` file with a `.dll` next to it in
`SiderAddons\modules`: `fl26swiss.dll`, `fl26join.dll`, `fl26chain.dll`, `fl26clubs.dll`,
`fl26regen.dll`, `fl26edit.dll`, `fl26walk.dll`, `fl26compcache.dll`, `fl26squadlist.dll`,
`fl26confgroups.dll` (FL 2027). They change the game in
memory, which some antivirus programs (Windows Security included) mistake for malware: they
quarantine the DLL a moment after it is copied. The `.lua` stays, so the game starts, but the
parts the DLL runs are silently missing: no European draws, empty league phases, no regens,
cups not played. In `sider.log` it reads `LoadLibraryA failed (err 126)`.

**Install the modules** checks every DLL after the copy and stops with a message that
names the missing file, and **Home** and **Diagnostics** say it as long as one is missing. To fix it:

1. Add the `SiderAddons` folder of the game as an exclusion in your antivirus. Windows Security:
   *Virus & threat protection > Manage settings > Exclusions > Add or remove exclusions > Add an
   exclusion > Folder*, and pick the game's `SiderAddons` folder (for example
   `...\Football Life 2026\SiderAddons`). Other antivirus programs
   have the same thing under "exceptions" or "exclusions".
2. Press **Install now** on **Home** again (or restore the files from
   the antivirus' quarantine).
3. Start a new Master League career if the old one was made without the DLLs.

If every one of them says `LoadLibraryA failed (err 126)` while the DLLs are in `modules`, look at
the game folder's name: Mod Studio 0.2.5 and older could not load the modules' DLLs from a folder
with letters outside plain English ones (`C:\fůtbal lajf\...`). Update Mod Studio, or rename the
folder to plain letters, choose it again in **Settings**, **Install the modules**, and start a
new career. The current version works with any folder name.

### What should I send when something is wrong?

1. In Mod Studio: **Tools > Diagnostics > Copy a report**, and paste it into the issue.
2. The files, from your Sider folder:
   - `SiderAddons\sider.log` (written again every time the game starts, so copy it right after
     the problem)
   - `SiderAddons\fl26join.log`, if the problem is about a Master League season
   - `SiderAddons\livecpk\<your world>\fl26world.txt`
3. What you did, what you expected, and what happened instead. A screenshot helps.
4. If the game crashed: the *fault offset* from Windows Event Viewer (*Windows Logs >
   Application*, the error for `FL_2026.exe` or `FL_2027.exe`).

## The scripts (the older way)

### Is there a program instead of all the scripts?

Yes: FL Mod Studio, a Windows program (beta). It installs the modules, builds leagues and
clubs, edits the players of any club, adds faces, installs other mods and content servers,
and keeps restore points. Download it from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest);
the guides (step by step, and every page explained, in five languages) are in
[guides/](../guides/README.md).

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

### Every match crashes with Kit Server and Kits you can edit in the game

sider.log says `[string "common\kits.lua"]:1143: attempt to index local 'p_home' (a nil value)`.
Fixed by `fl26kitguard` (in `fl26lateguards.lua`): Kit Server picks the goalkeepers'
kits at every kick-off from the shirt colours of the outfield kits, and a new club with an
editable kit has no kit of the game to read them from. The guard hands it a neutral grey for
that pick only, so the match starts. Kit Server still dresses no such club (see above).

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

The same goes for the managers table, which the game keeps at 1300. In a big world
the first "Create Edit Data" used to go back to the menu without making a save, because the
clubs past 749 had managers with no room left. Now it has room for 4096 managers, and the ones
past 1299 go to `EDIT00000000.fl26x` too.

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

Pick a club, pick a player, change any field, **Apply**, **Save**. The fields are in four tabs
(Profile, Positions, Abilities, Skills). **New player** creates one as a copy of the selected
player, **Up** / **Down** change the squad order (the green rows are the starting eleven). It
uses the same checks as the spreadsheet route below: a value the game cannot store (Speed 150,
say) is refused with a message and nothing is changed. Without `--root` it asks for the world
folder (the one that holds `common`). The first Save keeps the originals as `Player.bin.bak`
and `PlayerAssignment.bin.bak`.

For many players at once, edit the world's data files with `tools/playeredit.py`, the same way
`rename.py` does clubs. The players live in the world's `common\etc\pesdb\Player.bin`, and
which club each one plays for, with his shirt number and his place in the squad, in
`PlayerAssignment.bin`. Every field of a player is known (see
[player-record.md](research/player-record.md)), so you can set any of them, and create new players.

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
their places in a fixed order. For the engine's 4-2-3-1, which a new club with no formation keeps once its `order` is set, that is order 0 to 10 =
GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF (a club given another formation in Mod Studio,
or one Build picks from its squad, has that formation's order; `python tools/mktactics.py --base <tables> --list` prints them). To change who starts, change the `order`
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
