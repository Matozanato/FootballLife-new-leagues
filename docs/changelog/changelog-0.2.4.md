# What's new in Mod Studio 0.2.4

0.2.4 is a bug-fix update (in progress). Nothing new to learn: Install the modules, Build
once, and your 0.2.2 career keeps working.

## Changed

- **Cups of our countries.** My world > Cups has a new window with the cups of your own leagues in
  one table: for each top division its national cup, super cup and league cup, with the name and
  the logo -- the same fields as Edit league, without opening every league.
- **My world's cards.** The mouse wheel moves the row of worlds left and right, and after the
  world in the game come the newest ones, not A-Z. The logos in Cups of the game's countries fit
  their cells: Pick picture... and Clear side by side, the window as wide as the screen allows.

- **A new look.** A dark, calmer window: the state of the game in boxes across the top (game folder, Sider, world, modules, leagues, pack), numbered sections, Home's ready check as a table with a red bar that names the problem and the button that puts it right, and a status bar at the bottom, in Windows' own font. Tables read better: rows that alternate, a header on its own band, the chosen row in blue (Thanks jibibi). Nothing moved: the same pages, buttons and steps.
- **Export the world takes the scoreboards and menu themes of other packs along.** When the
  switched-on map lines of the Scoreboard Server or Menu Server on your PC give the world's
  competitions (its leagues, cups, super cups, confederation cups) a board or a theme from another
  pack, a modpack's, the zip carries those folders under `<world>\_packs` with their map lines, as
  it already did for kits. The receiver needs nothing else; the themes show with the Menu Server
  module on in `sider.ini`. Guide 9.1.
- **A ready world installs in one click, and a newer version replaces the older one.** Install
  mods shows **Install the world** for a world zip and hides the options a ready world does not
  need. If the same world is installed already (an earlier Modpack), it asks once and takes the
  older one out first, so no file of it stays behind. The modules come along with the world every
  time, without a question. Guide: Install a ready pack, Way A.
- **Build is switched off while a ready world is on.** A world installed from a zip is built
  already; Build would have replaced it with the open recipe. The Build steps are greyed out with
  a note, Home says **Ready to play**, and Build, Plan, Switch on and Only the European cups
  explain what to do instead: press Play, or switch your own world on first. A world installed
  from a zip and built again on this PC counts as your own from then on. Another world (NewLife, a
  new world) can still be built while the ready one is on: Build asks first, says it switches the
  ready world off, and Put in the game on its card brings it back with its careers.

- **My world: one place for your worlds.** The bar across the top has five items: 1. Home, 2. My world, 3. Game content, 4. Tools, 5. Settings. My world takes the place of Build and edit your world, Import your world and NewLife Database:
  - at the top, how many competitions the world in the game has (the game has room for 255) and how many new countries (room for 99), a reminder that changes need a new Master League, and **Build and install** (the same Build as before, with its restore point first);
  - a card for each world on disk. The one in the game is green (**IN THE GAME NOW**, **From zip** for a ready world); the others have **Put in the game**, which switches that world on in sider.ini, switches the other one off (it stays on disk) and opens it. Every card has **Export...**, **Rename** and **Delete**; the world in the game cannot be deleted. **+ New world** starts an empty one;
  - the tabs Leagues, Clubs, Players, Kits, Stadiums and Cups (pre-season cups, cups of the game's countries, competition names), and **+ Add...**: one window for a world zip (Modpack), a league package (.fl26pack) and the NewLife Database. It says what it found; for a league package it lists the leagues to tick and the competitions after adding;
  - **More** has Build details, League packages, Import a world zip, NewLife Database and Content folders.
- **Each world keeps its own Master League careers.** A career is made for one world: in another world its leagues and clubs are not there. Now, every time the world in the game changes (**Put in the game** in My world, **Build and install** of another world, Import your world, Content folders, a profile), the game's save folder changes with it. The careers of the world going out are kept in `save_<world>` next to `save` (in `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`), and the careers of the world coming in come back into `save`; a world with none yet starts with an empty one. The whole folder goes with the world (careers, Become a Legend, the Edit data), except your game settings (the SYSTEM / OPTION files), which come with you into every world. Nothing is ever deleted: before the first switch Mod Studio copies your whole save folder into `SiderAddons\ModStudio\backups\saves\<date>` (Tools > Restore points lists it), and the first time it tells you where your careers went. It does not switch while the game is running, or when a `save_<world>` folder of that name is there already: it says why and changes nothing. **Rename world** renames the world's `save_<world>` with it; **Delete world** leaves it alone (your careers are yours). Don't want it? Settings > **Each world keeps its own careers** turns it off. (Thanks jibibi for the idea)
- **You see how far Build is.** The Build tab, the bar above the tabs and the bottom bar show the
  time Build has taken so far and the step it is at (`Building... 3:12 · squads: filling them`),
  instead of only a blinking "Building...".
- **Keeping the players' ids from the last Build is much faster on a big world.** Build looked
  through every squad place of the world again for each player it gave another id
  (`lbplayers.py`), and a rebuilt Modpack moves thousands. It now finds each player's places
  once.
- **Modules in one line, fixed in one click.** Home and Lua modules say whether Mod Studio's
  modules are installed, up to date and switched on; when not, **Install now** puts them right,
  and the line names the modules that are missing, older or switched off.
  In `sider.ini` Mod Studio's module lines now stand together in one block of their own, with a
  heading, so the rest of the file is easy to read.
- **A final check after a world is installed.** Installing a ready world ends with **Ready to
  play** and a list of ticks (the world, switched on, the modules, the face pack, the content
  servers the world uses, the home stadiums), or **Almost ready** with what to fix: the red
  line under the install is a link (*see what to fix*) that shows the list again.
- **Put Sider back as before Mod Studio, in one click.** Tools > Restore points (and Game >
  Put Sider back as before Mod Studio...) puts back every file Mod Studio changed as it was first
  (sider.ini, CommonLib, the map files) and takes out what it brought in: its modules, the face
  pack, the worlds and the mods installed with it. Nothing is deleted: all of it is kept in
  `SiderAddons\ModStudio\reset-<time>`, and **Undo the last reset** puts it back. Clean up in
  Restore points now always keeps the oldest copy of a file, the one from before Mod Studio.
- **The world in the game is green.** Home > **Switch world...** (or Tools > Content folders with **Show the worlds** ticked) shows the world the game uses now on a green row, its name in bold, with **IN THE GAME NOW** in the Note column, so you see at a glance which of your worlds is on.
- **Delete world and Rename world.** In Content folders, pick a world (Show the worlds ticked) and press **Delete world...** or **Rename world...** under the folder's details, or right-click the world. Delete asks first and deletes nothing for good: the world's folder, its kits and scoreboards, its lines in sider.ini and in the kit and scoreboard maps and its install record go into `SiderAddons\ModStudio\backups\worlds\<world>\<date> deleted`, and Tools > Restore points > **Put this copy back** brings it all back exactly as it was. The last 3 copies of each world are kept. The world in the game (the green one) cannot be deleted: switch another world on, or untick it and press Apply, first. Your world in Mod Studio (its leagues) is not deleted, so you can build it again. Rename changes the name everywhere it is written: the sider.ini line (same place, on or off as it was), the kit and scoreboard folders and their map lines, the world file, your profiles and your world in Mod Studio. The new name must start with `_FL26` (letters, digits, - and _). A career keeps working after a rename: the game never sees the world's name, only the files in it. **Delete from disk...** on a world row now does the same safe Delete world.
- **No more copies next to your files.** Build, Switch on and Install the modules kept the old file next to the new one: `map.txt.before-builder`, `map.txt.prev`, `sider.ini.before-builder`, `fl26world.txt.prev` and folders `modules\before-builder-<n>`, all over your content folders. From now on these copies go into `SiderAddons\ModStudio\backups` and show in Tools > Restore points, where **Put this copy back** puts one back. The first copy of each file (the one from before Mod Studio) is always kept. **Put Sider back as before Mod Studio** finds both the new copies and the old ones an earlier version left next to the files; those old ones are not moved or deleted.
- **Home stadiums of a world from another PC.** A modpack names its clubs' stadiums by the
  folders of its maker's stadium pack. When your stadium pack keeps a stadium under another
  region folder, Mod Studio now finds it by its name; a stadium you do not have is left out (the
  club plays where the game puts it), and the final check says how many clubs have theirs.

- **Your world saves itself.** There is no Save recipe any more: a change is saved a moment
  after you make it, and the bottom bar says **Your world is saved**. File has New world, Open a
  world... and Save your world as... (a copy under another name). The word "recipe" is gone from
  the program: it is **your world** everywhere, and "live" or "switched on" is **in the game**.
- **Import your world, simpler.** Drop a pack (or Choose a file...) and the page says in one line
  what it is: a newer version of a world you have, a ready world, a league package or a mod, with
  the leagues inside. One **Install** button does the rest. The choices are still there, under
  **More options**: which parts (leave the kits out, say), the name, the order of the content
  folders and the map lines. A league package (.fl26pack) dropped here goes into your world and
  Build and install starts. **In the game now** lists what is installed, with **Remove**.
- **The leagues list goes by country, each country's divisions from the top down.** The game's
  leagues and yours stand together (Bundesliga, 2. Bundesliga, 3. Liga), until you drag one;
  then the list keeps your order as before. A world's order of leagues for Build is not changed.
- **Open a world takes you to Build and edit your world, tab Build**, where **Build and install**
  is, instead of a page with only the world's name and file. The bar above the tabs says which
  world it builds: its name and how many leagues and clubs; the Build tab adds the file it is
  kept in.
  **New world**, **Open a world...** and **Add leagues** are there too, for a world of your own.
- **One main button per page.** The Build tab shows **Build and install**; the world's options
  and the single steps with Export the world fold away under **World options** and **Step by
  step**, and stay open or closed as you left them. League packages is a tab of Build and edit
  your world. Players, Clubs, the clubs of a league and NewLife Database keep their main button
  and put the others under **More**; the team id and the crest's file name moved into the
  club's tooltip.
- **The game's tables unpack themselves.** The first time Mod Studio finds the game, it unpacks
  the game's clubs, leagues and players by itself (a minute or two) and says so
  in the bottom bar. **Settings > Unpack the game's tables** is still there for after a game update.

- **New clubs play a formation that fits their squad.** A new club with no formation of its own
  (none set for it or for its league) played the game's fixed 4-2-3-1 whatever its players, so
  every club of the Modpack lined up the same way. Build now gives each such club the formation,
  of those the game's clubs play, that gives most of its best players their own position: two
  strong strikers play two up front, good wingers three forwards, three centre backs three or
  five at the back. Its best eleven goes into that formation, and the Build log says which
  formations were picked. A formation you set stays. The Players page shows the formation picked
  for the club; when you change its order there, the club keeps that formation. Build again.

## Fixed

- **A world zip could bring other competitions' menus and scoreboards, and two menus on one competition.** Export the world also took the lines of the competition ids its leagues use inside the game (cid), which are other competitions' numbers to the Menu and Scoreboard Servers (r7 brought the SPFL, Jupiler, Liga Betplay ... menus, and two on one id, where the Menu Server picks one at random). Export now takes only the ids the maps go by, and one menu per competition.
- **NewLife: Bring the game's leagues to this season** no longer turns players into free agents when the release has them at a club but outside its best 30 (Joao Cancelo at Barcelona): they stay at the club they had, as long as it has room for them (40 at most), and Build's log names anyone it had no room for (B67). Thanks antoniodias_pt
- **Renaming a big world froze Mod Studio for minutes** (a world of 1146 clubs: the window stopped responding for 13 minutes before it said "is now ..."). The rename now runs in the background with "Renaming ..." in the bottom bar and on the world's card, the world cards wait until it is done, and the big files are no longer read and written whole again just to change one name, so it takes seconds.
- **After a rename the world cards changed order, so the same Rename button opened a different world.** A renamed world now keeps its place among the cards (and its "built" time); renaming does not make it the newest world.
- **The new screens were half in English in Spanish, French, Portuguese and Croatian.** The state boxes, the world name and move-club messages, the save switch line, the South American places and the UEFA ranking (its table and notes) now show in your language. Importing a world zip whose world has the name of one you built on this PC now says so before you press Install, in plain words, and tells you to rename that world on its card in My world (it used to stop with a raw "ValueError").
- My world: the Cups tab stayed lit after one of its windows, on the next page too (Build details). A window opened from a menu keeps the mouse, so the button never heard it leave; Cups and More now let go of that look when the window closes and whenever My world shows another page.
- My world: a world card said "1 leagues" and "1 new clubs". It now says "1 league" and "1 new club", in every language.
- **Leagues, a league of the game: "51 players" next to a club with 30** (KV Kortrijk): the Clubs list counted the squad changes, and a signed player twice. It now shows how many players the club will have: its squad, less the players removed or signed by another club, plus the ones added and signed.
- **The Modpack's menu themes stayed on under every other world.** Put in the game switched a ready world's kits and scoreboards with it, but not the menus its zip brought, so another world could show the Modpack's menus on a competition with the same number. Those lines now go on and off with their world, like the scoreboards; your own lines are not touched.
- **Language in the top menu did nothing: Mod Studio stayed in English after a restart.** Picking a language there saved no language at all, so the next start fell back to English (Settings > Language always worked). It now saves the language you pick; the message about the restart is also in Portuguese.
- **A club renamed or swapped into a league could show up in the Master League's "Other ..." list as well** (Estudiantes de Río Cuarto in the Liga Profesional and in Otros latinoamericanos). A place of the game's leagues that NewLife gives another club, or a club of the game swapped into a league, kept the game's "Other ..." group of that place. Build now takes every club with a place in a league out of those groups, as it already did for a club moved into one of your leagues, and the build check flags such a club. Build again and start a new career. (Thanks Xxspedd)
- **NewLife: "would play in two leagues (the recipe and ...)" sent people looking for a club they could not find.** A club renamed in one of your leagues keeps its NewLife link, so the database's club was there under another name. The message now names your league and the name the club has there, e.g. *(your world, Sky Bet League Two: Bletchley Town and Sky Bet League One)*. Rename it back or take that place out, then add the league. (Thanks Uncle Lanscilo)
- **Switching to another world took a ready world's scoreboards out for good.** A world installed from its zip (the Modpack) brings the scoreboards of its leagues; putting another world in the game removed their lines, and putting the Modpack back did not bring them back, so its 86 leagues played with the game's own boards. The lines now stay, switched off while another world is in the game, and come back on with their world. A Modpack that lost them: install its zip again.
- **NewLife: Bring the game's leagues to this season took seven Brazilian clubs of the game for clubs gone down** (Avaí, Vila Nova, Botafogo SP, Novorizontino, Cuiabá, Criciúma, Sport Recife), and gave their places to the database's own copies of the same clubs: names on the wrong crests, and Sport twice. The NewLife Database had them as new clubs since 1.0. From NewLife 1.5b5 on, the database says which club of the game such a club is, and Mod Studio puts it in that club's own place: it keeps its name, crest and id, gets the database's squad, and no place is given away. A NewLife version before 1.5b5 works as it did. A world that has one of these clubs as a new club in a league of its own keeps it there, with the same id; Bring then does not give its name to a place of the game too. For a world made before: open NewLife 1.5b5, Bring the game's leagues to this season again, Build and start a new career. (Thanks Xxspedd)
- **New clubs > More > New club here did nothing, without a word, on a new club's place.** It only undoes Club of the game. It is now greyed out unless the club picked is a club of the game in that place, its tooltip and the page's help say what it does, and it says so if it is reached anyway. (Thanks vmican)
- **NewLife: a club that took a place of the game's leagues kept the crest of the club that went down** when the NewLife Database has no crest picture for it. Such a place now gets the shield of the new club's shirt, as a new club does (or the drawn badge when the database has no shirt for it either); the club keeps its team id. Refresh the game's leagues (NewLife Database) once and Build for a world made before. (Thanks Xxspedd)
- **A league package that changes a club of the game your world already changes (a NewLife club, say) added its new players twice and lost its signings.** Adding the package put its added players after the ones already there, so a player both had came twice (a squad of 63), and the players it signs from other clubs (join) were dropped. Now a player both add is added once (the same id, or the same name and birth date), the package's signings come along, and its removals are added to yours. Remove the package and the club is as it was. (Thanks vmican)
- **Leagues said "League ID: not built yet" for a group of clubs in no league** (Other Africa teams and the like), even right after Build. Such a group never gets a competition; the page now says *no league (Other Africa teams)* and hides Format, Division, Up / down and Europe for it, and Add lower tier is greyed out. (Thanks B2Y26Arabia)
- **Build stopped on "players of 130: 42 players -- a club has at most 40"**, with only a number to go on. A club past 40 players (a national team past 26) after the transfers now keeps its first 40 and Build goes on; the Build log names the club, its league and its id, says which players were left out, and when the club is in your world twice (the usual cause) names both leagues, so you know which one to take it out of. (Thanks vmican)
- **The final check after Import your world said kits.lua (and scoreboards.lua) is not in SiderAddons\modules** on a game that loads SPFL26's own Kit Server and Scoreboard Server: those are in modules\common, and the check only looked in modules. It now looks where sider.ini has them. (Thanks vmican)
- **Import kits with the game under Program Files stopped with a bare "[WinError 5] Access is denied".** Import kits now checks first that Mod Studio may write into the game folder, and Import kits, a content server's Save, putting a restore point back and Move the Edit save aside show the same box as Build when Windows refuses the write: run Mod Studio as administrator (the box has a button for it) or move the game out of Program Files. (Thanks ZéDosCães21)
- **Dragging a file onto Import your world did nothing when Mod Studio runs as administrator.** Windows blocks drag and drop into a program started as administrator; the drop area now says so and points to Choose a file... and Choose a folder.... (Thanks quicksite)
- A scoreboard or menu pack made for another world now lands on the right league: Import your world puts each competition line on the competition its name says in your world (the FL26 Modpack scoreboard zips carry the ids of the full modpack, so League Two went on another league and the game kept its own scoreboard), reads the zips' `map line.txt` too, and says which league your world has not. (Thanks quicksite)
- **Home said "Mod Studio's modules need installing: 2 missing" for ever.** Mod Studio updated over
  an older version kept the old pack's single modules that a bundle has since replaced, and Install
  now copied them in only to move them out again. Those are now left out, and the updater replaces
  the module pack whole. Nothing was wrong in the game. (Thanks Novarama)
- **Build stopped with `IndexError: list index out of range` (in national_cups)** when the
  world had used up every free competition id and a league still had a super cup to make. It
  now stops with the same message as a cup does: no free competition or regulation ids left
  for that super cup, so you know to switch some cups or super cups off.
- **Select Team: a Swiss league of yours sat glued to Greece.** Mod Studio knew the game's Greek league
  by its old PES name, Switzerland, so a Swiss league you add sorted with it in every order and League order
  listed no Greece. It is Greece now; a League order of your own made before needs setting again. (Thanks LaraCroft)

- **Mod Studio closed (Qt6Widgets.dll, c0000005) when a module was ticked on or off in Lua modules**,
  or a folder in Content folders. The list was filled again while Qt was still busy with the ticked
  row; it is now filled a moment later, as NewLife's club list already was (#120). (Thanks vmican)

- **League order, First-season European clubs and Seasons of the game's leagues were gone from the
  leagues page.** The new look left them out of its **More** menu; they are back there (League order
  puts the countries of Select Team and Kick Off in your order).

- **A big world stopped with "the player table is full" although it fits.** The game takes
  61905 players, and Build counted while it worked: the placeholder players a club's own squad
  replaces are taken out only at the end, so a world of 1212 new clubs (the Modpack, 60488
  players when built) stopped halfway. Build now checks the finished world. New clubs get squads
  of 30 when your world names its players; when the finished world is still too big, Build
  says by how much and builds again with smaller squads (never below 22).
- **Some clubs of the game lost a player to a new copy of him when NewLife refreshed them.** The
  name check that keeps a player's game id read "Yıldız" (the Turkish dotless i) and "Yildiz" as
  two names, and "Yann Aurel Bisseck" and "Yann Bisseck" too. Such a player got a new id, so the
  club had him twice or his old self played on elsewhere. The check now folds ı, ß, þ, ð, ħ and ŀ
  like the game does, and a middle name one database leaves out no longer counts.
- **Install mods: a world zip's scoreboards and kits of other packs were gone right after the
  install, and a league package's kits with them.** Install mods ends with Switch on, which
  writes the world's own kit and scoreboard map lines and takes every line of Mod Studio's out
  first. The lines a world zip brings for the scoreboards and menu themes of a modpack
  (`<world>\_packs`) and for kits borrowed from other packs (`<world>\_kits`) end in the same
  tag, so they went out with the rest: a modpack installed from its zip played with the game's
  own scoreboards, and the clubs of the game that had dropped into its leagues wore the wrong
  kit. The world's own package kits and scoreboards went the same way when their source folder
  is on the PC the world was built on (`no folder ..., skipped`). Now Switch on keeps the lines
  a world carries and the lines whose copy is already under the world, and Export the world
  carries them along again from such a PC. The Modpack's scoreboards show after Install mods.
  Thanks Vran, Mob, ELBastos.
- **A world could be built with clubs that have no players; picking one crashed the game.** The
  placeholder squads are handed out in club-id order and stop at the player table's cap (61905
  with the modules installed) without a word in the Build log; a world past the cap -- 1212 new
  clubs with squads of 30 -- got its last 80 clubs with no players at all, and the Build log said
  only `no player 0, skipped` for each of their squad edits. In the game such a club crashes
  when picked, and Become a Legend does not start. Build now stops when the placeholder squads
  do not reach every club, saying how many fit, and stops at the end if any new club has fewer
  than 18 players; Mod Studio's checks say so about a world that is already built (build it again).
  The Build page's own count of the room (Checks) was already right for a Build inside Mod Studio.
- **A database mod that moves the game's leagues (UML 2026 v3) got the wrong countries and the
  wrong NewLife leagues.** With Settings on the mod's tables (**Use another tables folder**),
  Mod Studio still took a game league's country from its slot: UML's Ligue 1, in the Russian
  league's slot, was "Russia" in the UEFA ranking (and left out like Russia), in the July
  starts and in the League order. The country now comes from the clubs the tables put in the
  league. The NewLife Database took "in the game" from the plain game's clubs, so a league
  whose clubs the mod left out or renumbered (the Russian league, Ligue 2) could not be added;
  now a club is in the game only when the tables have it, and the rest are new clubs. With the
  game's own tables nothing changes. Build again. Thanks Yanis.
- **Build switched off your own kits for the clubs of a league package that carries kits.** A
  `map.txt` line you set on the Kits page (`71578, "Serie C\Catania FC"`) was greyed out with
  "(switched off by FL26 Mod Studio)" at every Build, and the package's kit went into
  `<world>\<league>\<club>` with a line of Mod Studio's. Only kits made in the clubs' colours
  gave way to a line of yours; a package's kits did not, which is why it hit one league. Now a
  club with a line of your own (to a kit that is in the library) keeps it, gets no package kit
  and no made kit, and a line of yours an older Build switched off is switched on again at the
  next Build. Package kits also stay with their club when you Remove, Insert or Move a club, or
  update the league to a newer NewLife (they stayed by place, so the clubs below wore the next
  club's kit). Thanks pepponeee98.
- **Build stopped with `KeyError` (in `lbplayers.py`) on a world built before.** A player
  listed at two places (a NewLife club listed twice) was given his id from the last Build twice.
  He now takes it once, and a stale ids file no longer stops Build. With 0.2.3, delete
  `fl26playerids.json` in the world's folder (`SiderAddons\livecpk\<world>`) before each Build.
  Thanks maur0.
- **After a Build again, players showed up as somebody else in an old career.** Build kept the
  id of each of the world's own players by his place in the squad. When a newer NewLife took a
  doubled player out of a squad (B52), everybody after him moved up a place and the ids went with
  the places: in a test rebuild of the Modpack, 1395 players kept their club and name but got
  another id, and 1826 ids belonged to another player than before. Build now finds each player by
  who he is first (his NewLife id, else his name and birth date, else his name when nobody else
  at the club has it) and only then by his place, and a player who changed clubs keeps his id
  too. The id of a player who left the world is not given to anyone else; only when no other id
  under the game's limit is free is one used again, and the Build log says so. The ids file
  (`fl26playerids.json`) now also says who each player is. A NewLife squad added or updated with
  0.2.4 carries each player's NewLife id and birth date; a squad added before is matched by name
  and place.
- **A league with a place in a continental competition of the game played the day before or
  after it, on every continent.** Nacional (Uruguay) had a league round on 22 September and the
  Libertadores quarter-final on the 23rd. The fixture module now knows the days of the game's
  own continental competitions in advance: the Copa Libertadores (qualifying round, group stage,
  knockout), the AFC Champions League (group stage and knockout) and the Club World Cup. A league
  that can send a club to one of them (its places in the world's access list, its country's cup
  winner's place, or the game's own South American and Asian leagues) keeps two days clear of the
  Libertadores and AFC Champions League days and a day clear of the Club World Cup's. A day the
  game gives one of them that is not among the known ones is noted in `sider.log` (`the game's
  reg ... plays N date(s)`) and kept clear by every league dated after it. Thanks antonimus.
- **A January-December league with a European place (Norway, Sweden, Finland, Ireland...) played
  the day before or after a European match.** Only August-May leagues were kept clear of the
  European days by the older scheduler, and the real-calendar scheduler used the wrong season's
  weekdays for the autumn of a league dated in January. Now both keep such a league two days
  clear of the August qualifying rounds of its own year, and clear of the autumn league phase
  and the spring knockouts, each on its own season's weekdays. A league with only a
  Libertadores or AFC place no longer loses the European days for nothing.
- **Both fixture schedulers now read one list of busy days per league** (continental cups of
  ours and of the game, pre-season cups, league cup, European days, national and calendar
  cups), so a day one of them keeps clear is a day the other keeps clear too. A continental cup
  of ours that takes a club through its cup winner (`alt=` places) is now kept clear by that
  league as well.
- **A calendar-year league played the day after its own cup.** The cup's days (the `dates ...
  days=` line of a January-December country) were kept clear only when the league was spaced
  the old way, not by the real-calendar scheduler: the Copa AUF Uruguay's second round on 18
  April, the league on the 19th. Both schedulers keep a day clear of them now, two on the
  first try, like the cup days of every other country. Each January-December country now
  keeps clear of its own cup's days, not of the one world-wide list. Thanks antonimus.
- **FL26 update 2.2 (`data_s25262b.cpk`): Mod Studio read its tables before the older ones.**
  The game's files were taken in alphabetical order, which puts `data_s25262b` before
  `data_s2526b`, so the newest tables were covered by older ones and the version label said
  `data_s2526d`. They are now layered the way the game does it; unpack the tables again
  (Tools, or the next Build does it). Thanks to everyone on the 2.2 update.
- **Second season: the Europa League had no round of 16, and its league phase table was empty
  from February on.** After the July teardown the February play-off is outside the season, and
  the game's start of it opened a new season on the Europa League -- dated by February's year,
  so one season early -- and every look at the league phase table from then on found that empty
  season: the play-off was played, but the round of 16 was never drawn and Competition Info
  showed an empty League Phase. The draw (since 0.2.3, 13 October) already took the fuller table
  of the two seasons; now the play-off and its ties are given the league phase's season year
  before they start, as in a first season, so no second season is opened at all. Needs Install
  the modules; a career that has already passed February of its second season keeps the table
  it has, the next season is right.
- **A February play-off with 7 ties instead of 8 (14 clubs), a qualifying round with 6.** A
  world with more than 300 competition regulations -- the 0.2.1 Modpack has 334 -- lost its
  highest regulation ids with the 0.2.1 modules: the game counts its regulations again after
  every load and looked at the first 300 only, so the last ties of the European rounds (and of
  the Libertadores and AFC groups) never got matches. `fl26regs600.lua`, installed since 0.2.2,
  makes the game count all of them. New: **Checks** now says so when a world has more
  regulations than the modules switched on let the game count, and points at Install the
  modules (a new career is needed). Thanks Micarodvzla22.
- **New clubs: the crest picked in the club dialog did not show in the table** until another
  league was chosen (the pick was saved; only the row was stale). GitHub #140, thanks B2Y26Arabia.
- **Cup mode: a saved cup (World Cup, Euro...) could not be loaded.** With the modules the
  load ran for a minute or two and the game closed; without them the same save loaded in
  seconds. The raised club limits had moved the game's tables but not three places where a
  cup save puts its teams, coaches and regulations back on load, so the live season came back
  without teams. Checked in the game: a World Cup save loads in seconds and continues at the
  cup menu. Thanks Vicentico.
- **League Two (and any league with nothing below it): the promotion arrows stuck to the first
  rows of the standings when scrolling.** Thanks Vicentico.
- **Super cups of the game's own leagues** (New leagues > cups of the game's countries) came
  out as a 16-club knockout; they are now a two-club super cup (champion v cup winner), and in
  a February-December country (the Supercopa de Chile, the Supercopa Rei) it is played at the
  end of January, between the champion and the cup winner of the season just ended. Needs
  Install mods and Build again, then a new career. Thanks Vicentico.
- **A new division under a February-December league of the game** (a J2 under the J.League)
  could send its own champion to that country's super cup. Needs Install mods.
- **NewLife Database: "Bring the game's leagues to this season" skipped the Brasileirão Série B**
  (the game's Série B keeps only 6 of its 20 clubs in the 2026 line-up, and a league with fewer
  than half of its clubs left did not count as the game's own). Thanks Vicentico.
- **Build stopped with "players of <club>: no player <n>"** on a recipe written with 0.2.1
  (30-man new clubs). The transfer of a player the club no longer has is skipped with a note in
  the log. Thanks diwwanmago.

- **A game under `Program Files`: Install mods, Install the modules, Build and Switch on stopped
  with a raw `PermissionError [WinError 5]`.** Windows lets only a program run as administrator
  change files there. Mod Studio now tries the game folder when you choose it and before it
  writes there, and says plainly what to do: run it as administrator (the message has a
  **Restart as administrator** button) or move the game out of Program Files. Home shows the
  same as long as the folder is not writable. FAQ. Thanks Konkubent.
- **An antivirus quarantined our DLLs (`fl26swiss.dll`, `fl26join.dll` ...) right after Install
  the modules, and Mod Studio said nothing**: the game started without the European draws and
  the new cups. Install the modules now checks every DLL it copied (there, and the bytes it
  shipped) and stops with a message that names the file and says to add `SiderAddons` as an
  exclusion in the antivirus and install again; Home, Diagnostics and *4. Check* say the same
  while a DLL a switched-on module needs is missing. FAQ. Thanks bikolunar42.

- **Mod Studio went "Not Responding" while a big world built.** Opening another tab during Build
  (the Modpack: League packages, then back to Build) froze the window until Build was over.
  Build now runs in a process of its own, and the window stays free while it works.
- **Pages were cut off with Windows display scaling at 125 % or 150 %, or in a small window**:
  the buttons were squeezed to a line. Every page now scrolls when it is taller than the window.
- **Pages opened slowly on a big world, and the window stopped every 4 seconds.** On the Modpack
  Home took 4 s to open, Leagues 4.5 s and Clubs 1.4 s: each visit read the built world's plan
  again (about 1 s each time) and made every crest picture again. Both are now kept until the
  file changes: Leagues and Clubs open in about 0.1 s, Home in 0.2 s after the first time. The
  check whether the game is running (every 4 s) took 0.3 s with the window waiting; it now asks
  Windows directly, in a few milliseconds.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) still applies. Your 0.2.2 / 0.2.3 career keeps
  working after this update; a cup saved before 0.2.4 loads too.
