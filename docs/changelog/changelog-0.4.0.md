# What's new in FL Mod Studio 0.4.0

0.4.0 (2026-11-21) brings everything made and fixed in the closed beta since 0.3.0. Most of it is
for **Football Life 2027** and for very big worlds: worlds of hundreds of leagues build, install
and play, an update of a world you share keeps your players' careers going, new faces for regens,
split leagues and Apertura/Clausura, UEFA qualifying as UEFA plays it, a third cup for the lower
divisions, trophies in FL27, and many fixes of what you reported. FL26 gets the fixes; what is
FL 2027 only says so.

## Before you update

- **Keep a copy of your save folder and your old Mod Studio folder** before you update, as always.
- **Install the modules again** after the update (**Home > Install now**): many fixes are in our
  modules in the game.
- **A running career keeps what its save holds.** A career keeps its own copy of the clubs,
  squads and competitions, so new leagues, cups and clubs of an update of a world come only in a
  new Master League. Your career goes on with the leagues it has.
- **New licence.** From 0.4.0 Mod Studio is under the FL Mod Studio License (see `LICENSE`): it
  stays free to use, change and share; selling it and removing the "Powered by FL ModStudio" mark
  are not allowed. 0.3.0 and older stay under the MIT License.

## Fixed

- **A renamed league keeps its clubs' money** (D17, our test of 0.4.0, FL 2027). After *Edit league...* gave a league a new name, its clubs' transfer budget, followers and fame from the recipe (`club_money`) stayed under the old name, and the next Build gave its clubs Build's estimate instead. The same money now also moves with its club on *Insert club*, *Remove club*, *Move club* and when a league's last clubs are taken out; before, a club could get the money of the club next to it. Build the world again. A league renamed with an earlier beta is not repaired: its clubs' money is still under the old name in the recipe.
- **Check the plan is in your language** (D17). In Español, Français, Português and Hrvatski most of the plan stayed English: the line of team ids, the player changes, the European places of the game's leagues, the play-offs for promotion, the super cups, the cups, the Select Team notes and more. The line that counts the megabytes while Mod Studio keeps a copy of a world (a restore point) is translated too.
- **After an Update of a world, no player in a running career is called "Players"** (B496, beta 5). When a new version of a world merged two copies of one player and dropped one id, a career of the version before still had the player of that id; the world had no name for him, so the game showed "Players" with no face in the squad list. Our module (fl26regen) now gives such a player a name from the name pool, the same one at every load. sider.log says how many ("... named whose id the world no longer has"). Install the modules again. Checked in the game on a test build of this fix: no "Players" left, the same names after a save, restart and load.
- **Install says, while it reads a zip, that Install or Update comes when it is done** (B498, Jeyspeed). A big world takes a few minutes to read, and until then the page showed no Update button, so it looked as if Update did not work.
- **Colombia: Primera C Especial and Primera C exchange clubs again at New Year** (B494, antonimus): nobody was relegated from Primera C Especial and nobody promoted from Primera C. The game's own season end moves clubs only in every other pair of a country's leagues, and in Colombia its count starts one league lower, because the Liga BetPlay is a season of two tournaments; our module (fl26chain) took the other pair. It now counts from Primera B in such a country, so the two leagues exchange 2 and 2 every New Year. No other country changes. sider.log now also names every pair our module leaves to the game's season end ("new year: 428<->960 -- ... left to the game's season end"). Install the modules again (fl26chain.lua, fl26join.dll). Checked in the game on a test build of this beta: at New Year Primera C Especial and Primera C exchanged 2 and 2, and it held after a save, restart and load.
- **FL27: the two legs of a European qualifying tie are no longer two days apart** (B463, Luka: a Conference League 3rd qualifying round on 19 and 21 August). All three competitions' August rounds (Champions League, Europa League, Conference League: 2nd and 3rd qualifying round, play-off) now play the second leg a week after the first where the days before FL27's own league phase (8 September) allow it, always on a Tuesday, Wednesday or Thursday. 2026/27: 2nd qualifying round 11 and 18 August, 3rd 20 and 25 August, play-off 27 August and 2 September; 2027/28: 10/17, 19/24 August, 26 August / 2 September. The 3rd qualifying round is five days apart every season (Thursday, then Tuesday): three rounds of a week each do not fit between the start of a new season (5 August) and the league phase. A career in progress keeps the dates of the rounds already drawn; the rounds after them take the new ones. FL26 is unchanged (one leg a week since 0.2.0). Checked in the game on an earlier test build of this beta.
- **A Master League saved before 1 August and loaded again no longer enters the world's leagues twice** (B488, reported on Steam Deck with a big world on FL 2027): on 1 August the January-December leagues and the split leagues went into the season a second time, the calendar then showed no league matches and the result screen named another league. Our module now also asks the save and the game date what it used to remember only for the session that made the career. Careers saved by an earlier version load the same way. Not checked in the game yet.
- **FL27, Be a Legend: the matchday page opened from the Calendar shows your own competition** (B470/B465, with a big world). Pressing cross on a match day in your club's calendar opened another league's matchday with the same round number (13 January, EFL Championship matchday 22, showed "Tercera División A, matchday 22"; matchday 1 showed "China League One"). The Calendar keeps only part of the match's number, and in a world with more than 65,536 matches two matches share it; the page took the other one. Our module (fl26match) now gives the page the match the Calendar row shows. The result screen after a match was already right. Install the modules again (fl26match.dll). Checked in the game on a test build of this beta.
- **FL27: Individual Titles and Team of the Competition open for the continental cups** (B470, morpheus). In Competition Info they were grey all season for the Champions League, the Conference League, the CAF and OFC Champions Leagues, the AFC Champions League Two and other cups, while the CONCACAF Champions Cup had them. The game turns them on only when every phase of a cup has its awards, and the phases a world adds (qualifying rounds, play-offs, the world's continental cups) had none. Our module (fl26swiss) now has them passed over at that one check, as the game passes over the phases of its own cups, and the single groups of a cup's group stage with them: the game marks a group the way it marks a league, so the cups with groups (Conference League, CAF Champions League and Confederation Cup, AFC Champions League Two and Challenge League, OFC Champions League, Copa Sudamericana) stayed grey after the first fix. Leagues and the awards at the season's end are not changed. The AFC Champions League is the game's own cup, and the game itself leaves the two items out of its menu (none of its phases has awards in the game's table); that is not changed. Install the modules again. Checked in the game on a test build of this beta, also after a restart (B470d).
- **FL27: the UEFA Super Cup is played every summer** (B470). From the second season on it had no clubs and was never played: the game emptied it at the end of the season and did not fill it again. When the game has left it empty, fl26swiss now puts in last season's Champions League and Europa League winners; a Super Cup the game has filled is left as it is. sider.log names every fill, and once a season why one was left alone; `fl26superguard` also logs every Super Cup setup it skips. Install the modules again. Checked in the game on a test build of this beta: the second season's Super Cup was played.
- **FL27: the Europa League's participants no longer include last season's knockout clubs** (B470). From the second season on the page listed the clubs of the new league phase next to last season's knockout (57 clubs, one club twice). At the start of July the game empties the Champions League's knockout but not the Europa League's; fl26swiss now empties it too, after the game's day, and keeps its winner for the UEFA Super Cup. sider.log says so once ("Europa League knockout 6: the season close left last season's ..."). Install the modules again. Checked in the game on a test build of this beta, with a career started on an earlier beta world and updated (B470b).
- **FL27: a continental cup's preliminary round is no longer a second cup of the same name in Competition Info** (B470). The round carries its cup's name, so Competition Info listed it after the real cup: the CAF and CONCACAF cups and the OFC Champions League came twice, the OFC one with two clubs and a grey bracket. It is hidden there now and still played. Install the modules again. Not checked in the game yet.
- **FL27: Competition Info by confederation shows each confederation's own cups** (B495, beta 4). On the right side, "+ CONMEBOL" showed the Club World Cup and the Europa League, UEFA had no Europa or Conference League, AFC showed the Libertadores, and CAF, CONCACAF and OFC only the Club World Cup. The game's list holds the cups' phases, and our module (fl26confgroups) compared their numbers with the cups' own; it now looks up the cup of each phase, so every confederation shows its continental cups and the Club World Cup. Install the modules again. Not checked in the game yet.
- **FL27: the league phase table of the Champions League and the Europa League shows every club** (B503, jeremy1979_). Competition Info paged the table of 36 clubs, and each page held nine rows while the screen shows eight: the ninth (places 9, 18 and 27) sat under the Return bar. Now both are one table of all 36 that scrolls, as on FL26 and as the Conference League already was on FL27 (david.bdj's table). Install the modules again. Not checked in the game yet.
- **A cup whose field the bracket screen has no layout for no longer closes the game** (B475, edln, FL 2027, the Worldpack). The world's Liga Profesional has 26 clubs, so the game made the Copa Argentina a cup of 26, and its bracket screen (Competition Info > the cup > Fixtures, and the page the game opens after your match of a round) closed the game: it draws 2-16, 18, 20, 24, 28, 30 and 32 clubs only. It now shows such a cup's clubs on the first places and hides the rest; every field it drew before looks as it did. The cup keeps its size (see known issues). New module fl26nullguard14, in fl26guards.lua; FL26 has the same code. Install the modules again. Checked in the game on a test build of this beta (the same module): the version without it closed the game at that screen, this one did not.
- **Become a Legend: the day after the second season's end no longer closes the game** (B491, vanni11, FL 2027, an edited Europe pack). From 1 to 2 July of the second season the game closed (`c0000409`): a season-end step looks up every player of a team's list, and one player was not there. That player is now skipped, as the game skips an empty place (new module fl26nullguard15, in fl26guards.lua). Why the player is missing is not known yet (see known issues). Install the modules again. On a test build of this beta a career went past 1-2 July of its second season without closing; that the guard was what kept it going is not shown yet.
- **Regens and new players get faces of their own, from the pack.** 0.3.0 and the betas shipped an old face pack of 103 faces taken from the game's players, so many regens looked like a real player and like each other. The pack now has the pool of 32,760 faces made for it: every face is new, drawn from how the game's own players of that part of the world look, in 11 groups. A new group, South-East Asia, takes Indonesia and its neighbours and Polynesia; South Asia is only India, Pakistan, Bangladesh, Bhutan, Nepal, Sri Lanka and the Maldives; Melanesia (Fiji) gets African faces, Kazakhstan and Kyrgyzstan East Asian, Uzbekistan, Tajikistan and Turkmenistan those of the Middle East and North Africa, Belize Latin American. Their small pictures (the team sheet, Game Plan) come from 100 portraits for now, the whole head down to the top of the shirt: every face shows the portrait closest to it, so a few players share one. More portraits come in later updates. Install the modules again. Checked in the game on a test build of this beta (faces by region and the portraits, the same after a save and restart).
- **A play-off's name shows in Competition Info** (B489, Dolokhov, a Hungarian world). A play-off the recipe gives no name was called "<league> Relegation Play-off" or "... Promotion Play-off", and past 38 characters Competition Info drew it as a crest with no name, as Kick Off does with a league's name. Build now keeps such a name to 38 characters: "Rel." or "Prom. Play-off", then "Play-off", then the league's first words go one by one, and no two play-offs get the same name. A `playoff_name` of the recipe is kept as it is; Check the plan writes a NOTE when it is longer than 38. Build the world again.
- **An Apertura or Clausura playoff's name shows in Competition Info too.** Build named them "<league> Apertura Playoffs", and past 38 characters Competition Info draws the name blank, as with the play-offs above ("Primera División de El Salvador Apertura Playoffs", 49). Too long, the name is now the country's part of the league's name: "El Salvador Apertura Playoffs", "Guatemala Clausura Playoffs". Build the world again. Not checked in the game yet.
- **Kits and scoreboards of a newer package go into a world that came from a zip** (found while building a big world: HNL's new scoreboard never went in). A world installed from a zip and made editable brought its kit and scoreboard folders with the dates they got when they came out of the zip, and Build took those for folders you had changed yourself: it kept them ("changed by you, kept") and the package's newer files were never copied, without a word. Mod Studio now tells a folder that only came out of a zip from one you changed by hand; a folder you did change is still kept. Build the world again.
- **The game's clubs in no league can be edited again** (GitHub #140, B2Y26Arabia). Since 0.1.8 the Leagues page hid the group the game keeps them in, so *Edit club...* (a crest, a name) could not reach them. They are a row under Other now, "Other clubs (no league)", with their clubs on the right as a league's. National teams stay on Players (*Call up players...*). Checked through the Mod Studio exe on a test build of this beta.
- **Edit league > Logo shows the league's logo in a world from a zip.** After *Make it editable...* it said "(file moved or deleted)", because the logo's picture was on the PC that made the world. It now shows the logo the world has, and OK leaves the recipe as it was. Checked through the Mod Studio exe on a test build of this beta.
- **A club you rename keeps its id.** Build kept a new club's team id by the club's name, so a club
  renamed between two Builds got a new id, and a Build later the id it had went to another club:
  a kit, crest or face made for that id turned up on the wrong club. A club renamed where it
  stands, and a club moved to another league of your world, now keep their id, and an id a club
  once had is not given to another club while a free one is left (the world remembers them).
  For a world you update and share, `tools/checkids.py <published zip> <new zip>` compares every
  league's, club's and player's id and stops on any that moved.
- **Installing a newer version of a world no longer deletes your own files.** The older version is
  taken out first, and its whole folder went with it, with any file you had put there yourself. Now
  a file you added to the world's folder, and a file of the world you changed after installing it
  (a kit, a crest), is kept in `SiderAddons\ModStudio\kept\<world>-<time>`, in the same folders
  as it had. The question before the install says so, and a line after it names the folder. The
  new version still goes in clean; put your files back from there if you still want them. The
  last line after the install and the **Ready to play** window name the folder too (the first line
  that said it was replaced by "ready to play" a few seconds later), and Mod Studio's own kit
  index (`kitmaker-index.json`) is no longer kept and counted as a file you changed.
- **A file you copied over one of a world's files is kept too** when a newer version of the world goes in (B487, pop1806: a face from another pack was deleted). Such a file keeps its own older date, and Mod Studio went by the date only; it now checks that the file is still the one the install put there (its size, its date and, for a zip, its checksum).
- **A league you renamed in a world from a zip before *Make it editable...* is no longer there twice** (B487, pop1806). After *Make it editable...* it is one league under the name you gave it, with its clubs and players, and Build keeps its ids. Players you changed before *Make it editable...* (names, squads) and changes on the edit tab (game clubs, leagues, competitions, swaps) are kept too; they reach the game with the Build after it.
- **A world from a zip says, on the pages it concerns, that changes there are not kept until *Make it editable...*** (B487, pop1806). Changes to its leagues, clubs, cups and settings made before *My world > Make it editable...* were lost without a word. Build, Leagues, Clubs, Cups, New leagues, League packages, NewLife Database and Trophies now show a line at the top while such a world is open; it goes as soon as the world is made editable. Editing is not blocked.
- **Import your world says whether a world zip is newer, older or the same.** A zip older than
  the world you have was called "a newer version". Mod Studio now compares when the two zips
  were made; where it cannot tell (a folder, a world installed before this version) it says
  "another version".
- **Players: a Save button.** A name typed for a player was taken when you left the field, with
  nothing to press and nothing that said so. *Save* (beside *Undo changes to this player*) takes
  what you typed, writes your world to its file at once and says "Saved". The game shows it after
  Build, as before.
- **FL27: the Europa League's Group stage and rankings are no longer grey in Competition Info** (B459).
  The league phase was played, but the menu kept "Group stage", "Goal Ranking" and "Assist Ranking" grey
  all season, so its table could not be opened. "Play-offs" stays grey there: FL27's Europa League has
  no separate play-off round, its knockout phase holds it.
- **Every group of a division now shows its promotion and relegation places in the table** (B458).
  In a division played in groups (Serie C Girone A / B / C, and every other set of groups) only the
  first group had the coloured strip at its promotion places; the other groups' tables showed
  nothing, although their clubs went up and down correctly at the season's end. All groups show
  them now. FL 2027 only.
- **Build no longer says "the club was not built, skipped" for the game's own clubs** (B433). A club
  of the game that plays in one of your leagues keeps its own squad; Build made a placeholder squad
  for it all the same and then threw it away with that line, once per such club. Nothing was wrong
  with those clubs, and the line is gone.
- **A button that fails now says so.** An unexpected error in a click was only written to
  `errors.log` in Mod Studio's settings folder: the button seemed to do nothing. The status line at
  the bottom now says that it did not work and names that file, so you can send it with your report.
- **Build's log no longer fills with "picture not on this PC"** when you build a world that came from a zip
  and that you made editable: its crests and logos were made on the maker's PC, so every one of them
  got a line (thousands for a large world) and the lines that matter were lost among them. Build now
  says the first five and then how many more; the pictures themselves are kept as before.
- **"Install the world" no longer stops the window at its end** with a large world (B419): the
  last check read the world's whole plan in the window itself (about 3 seconds with a very large
  world); it now reads it in the background like the rest of the install.
- **The window no longer stops after the Build click with a very large world** (B480). With the
  largest world we test with, the window stood still twice before Build started (4 to 9 seconds in our measurement):
  getting the Build ready and saving the copy of your world that Build keeps ran in the window
  itself. Both now run in the background; the Build buttons stay off meanwhile and the line at the
  bottom says what it is doing. At the end of a world zip install and after *Make it editable...*,
  the pages you are not looking at are filled a moment later instead of all at once (about 1 s of
  a stopped window with that world, now under 0.5 s after *Make it editable...* and about 0.6 s
  at the end of a zip install), and the copy of the world's recipe the install keeps is written
  in pieces (another stop of about 1 s). The files are the same, byte for byte. Measured on a copy
  of that world outside the game; not checked through the Mod Studio exe yet.
  A second round (B480) takes the rest of the way off the window too: the look into a world zip
  before Install, the end of the install, *Make it editable...* (a large piece of the old world is
  now let go in the background), Build and install, the first opening of Leagues after a Build,
  and *Edit league...* with OK or Cancel. Outside the game, on a world of that size, no
  stop on that way is longer than 0.5 s now (the end of a zip install included). Not checked
  through the Mod Studio exe yet.
- **An exported world no longer names the folders of the PC it was built on** (B430). Build
  writes the pictures, kit folders and trophies a world was made from into the world's plan by
  their full path (`C:/Users/<your name>/...`), and Export put that plan into the zip as it was:
  whoever got the zip could read the maker's Windows user name and folder names. Export now cuts
  every such path down to `source/d<n>/<its last part>` in the zip's copy of
  `leaguebuilder-plan.json`, `leaguebuilder-input.json` and `trophies/trophies.json`, and says how
  many it cut. The world in your own game keeps its files, so Build and Make editable work on
  your PC as before; on another PC those folders never existed and Mod Studio takes the copies
  the world carries, as it always did. For world makers: `python tools/checkworldzip.py
  <world.zip> [word ...]` reads every text file of a zip and says whether one still holds a path
  of a disk (or a word you give it: your name, a folder). Notes of your own that lie inside a kit
  or scoreboard folder still travel with it -- keep those elsewhere. **Zips exported before this
  update carry the paths**: export the world again to share it without them.

- **A NewLife player the game already has no longer comes in twice** (B421, reported on Reddit:
  "many duplicate players", "top players without clubs"). The database and the game write some
  names differently: "Marc-André ter Stegen" and the game's "M. ter Stegen", "Everton Cebolinha"
  and "Éverton". Build took the two for different players: the database's became a new player
  with a made face, and the game's lost his club and sat with the free agents. Build now also
  takes them for one player when the database gives his id in the game under another spelling,
  when the game has a player of that nationality, age and height at the very same club, or when
  the name is only cut short or has a part left out and nationality, age and height all fit.
  One shared word ("Gabriel") away from his club is still not enough. With NewLife 1.6b4 and
  FL 2027 that is some 550 more players who keep their id, face and club. Build your world
  again; a career already started keeps the players it has. Not yet checked in the game.
- **A check for the same player twice**, for world makers: `python tools/checktwins.py <world>
  <the game's tables>` lists a game player without a club beside an added player who is him, and
  fails the world when there is one.
- **The board's objectives meeting no longer offers "the UEFA Champions League" to a club of a new
  Asian or South American league** (B395). Since 0.2.0 the objective itself was the AFC Champions
  League or the Libertadores for such a club, but the meeting's own lines took the cup from another
  place in the game and went on naming the Champions League. Both now ask the same thing (seen in
  FL 2027; FL 2026 has the same code at that place). No new Build is needed, only the new modules (Install the modules). The game has no
  board objective for the African, North and Central American or Oceanian cups: a club of a new
  league there is still told about the Champions League (see known issues).
- **Cups > Continental > Qualification lists Colombia's and the MLS's whole season** (B414). The
  page offered only *Liga BetPlay DIMAYOR I* and *MLS First Round*, so continental places could
  only go by the first tournament's table. *Liga BetPlay DIMAYOR* and *Major League Soccer* are in
  the list again, as in the older places dialog: places given there go by both tournaments' tables
  added together. Give places to one of the two, not both.

- **No more Lua error of SmokePatch's `SleeveBadge.lua` at the matches of a world's leagues and
  cups.** Its `content\SleeveBadge\map.txt` has no line for a competition a world adds, and its
  module stopped with an error at each of their matches (sider.log: `attempt to concatenate local
  'folder'`, line 367). Switching a world on now gives each of its competitions a line there, to a
  folder named as the world; SmokePatch's own lines and yours are left as they are, and the lines
  go again with the world. The matches look as before (no sleeve badge); a badge put in
  `content\SleeveBadge\<world>\badge` is worn. Switch the world on again (or Build) to get them.
  The world's European qualifying rounds, promotion play-offs, preliminary rounds and split groups
  get their lines too, and a cup gets the lines of its later rounds and groups (the game numbers
  them as the cup's id plus 1024 for each): the first match of a career in the Conference
  League's first qualifying round still gave the error.

- **Paste manager names and Paste short names** (a league's clubs, *More*) and the tip of
  *Import transfers...* are translated in Español, Français, Português and Hrvatski (B407): they
  showed in English.

- **FL27: League Info on a confederation's row shows its continental cups** (B402). On "+ UEFA",
  "+ CONMEBOL" ... in Select Team of a new Master League the panel showed the Club World Cup, three
  Intercontinental cups and two empty emblems; it now shows that confederation's own cups -- UCL,
  UEL, UECL for UEFA, the Libertadores and the Sudamericana for CONMEBOL, and the continental cups
  the world adds -- and no league above or below. Install the modules again; no new Build needed.

- **Import your world no longer stops with `[Errno 2] No such file or directory`** on a file in
  `trophies\...` (B400, a big world). On a PC with Windows' long paths switched off (the default),
  a file whose whole path passed 259 characters could not be unpacked or copied. Mod Studio now
  unpacks, copies and removes such files anyway, and before Install it checks every file against
  the game folder: when the game sits in a folder whose path is too long for the game to open
  some of them, it says how many and how long the folder's path may be
  ([FAQ](../faq.md#import-your-world-says-the-game-folders-path-is-too-long-for--files-of-this-mod)).
  The trophies of a world no longer carry the unpacked copy of their `.fpk` files that GzsTool
  leaves beside them (the game reads the `.fpk`): a big world's longest path in the game was
  217 characters after the game folder and is 160 now, also for a world zip made before the fix.

- **Import your world says at once when a zip is packed in a way it cannot read** (B386, reported
  by acoco75). A zip made with Deflate64 (Windows uses it for a file over 2 GB) was looked
  through to the end and then answered "That compression method is not supported". Mod Studio now
  says so before it unpacks anything, and how to go on: unpack the zip (7-Zip, or right click >
  Extract All) and use *Choose a folder...* on what came out. A league package packed that way
  gets a clear message too.
- **New clubs: the Team ID column after Insert club** (B305, reported by evannoteven). After
  *Insert club* every club under the new one showed the id of the club above it until the next
  Build, and the new club an id it would never get. The column goes by the club's name now, as
  the Build itself keeps the ids; a club the Build has not seen yet shows "at Build".
- **Build no longer stops with "nothing to copy a new player from"** after NewLife's *Bring the
  game's leagues* on a club the game left without a squad. Its new players are now made from the
  first player who joins it.

- **NewLife no longer takes legends out of the Classic Teams.** A NewLife player of a lower
  league with the same name as a legend (Marcelo, Fernandinho, Nene) was moved from his Classic
  team to the NewLife club, with the lower league's ratings. He now becomes a new player of that
  club, and the Classic Teams and the Master League's default squads stay whole.

- **A world for FL 2027 cannot go into FL26 by mistake** (and an FL26 world not into FL 2027).
  Build and Export now write which game a world is for. Mod Studio refuses to install it, to put
  it in the game (My world, Content folders) or to Build a recipe of the other game, and says
  where it goes. A world too big for FL26 (over 2400 clubs or 61905 players, like a world of 200 leagues)
  is refused there even when it was made before this. If such a world is copied in by hand, the
  game shows a message at the start and closes before it loads anything, so the game and its
  saves are not touched.

- **In a world of more than 4096 new clubs, the last ones were rich as the top club.** The
  followers module took at most 4096 clubs, so the rest of a very big world counted again as the
  best club in the ranking in a career: many times the followers and the top TV money. It now takes
  16384, and its log says when a world has more than that. Install the modules again.

- **The national cup of a January-December country of ours had no clubs and played no match**
  (the Suomen Cup, NM Cupen, Svenska Cupen; reported by huliaanos and Uncle Lanscilo). Its
  Competition Info said "The lineup of teams eligible for this competition has not been decided",
  and opening its Fixtures could close the game. The cup now gets its league's clubs when it joins
  the season. A career already running gets them at its next New Year.
- **The FA Cup and the Coupe de France stopped at the quarter-finals when the best clubs of a
  third division of ours played them too** (reported by rwee, FL27). The cup was drawn before
  those clubs were in it, and a field of 48 left some clubs without a place in the bracket. The
  third division's clubs now join before the draw, and the cup takes at most 44 clubs (the FA
  Cup's own field). Build the world again and start a new career to get it.
- **Your own club started in the Copa Libertadores group stage in the first season** (reported by
  pczim123, Brazil, FL27). When the game's first-season field had a club that has to play the
  qualifying rounds, the stand-in that took its group place could be your club, and your club is
  never moved out for one of ours. The stand-in is now never your club. Start a new career to get
  it.
- **The Copa Sudamericana no longer plays from August to May** (reported by Vicentico). Its group
  stage ran from late November to February, so a club could play it and the next Libertadores at
  the same time. It now plays February to December on the Libertadores' days, like the real one,
  in every world (until now only the World Modpack had it). A recipe with
  `"sudamericana_calendar": false` keeps the old calendar. Build the world again and start a new
  career to get it.

- **Ratings are the game's own number.** The Players page, the Sign / Call up list, Export
  players and the check for 90+ players of a new world now work a player's rating out with the
  game's formula (the one TEditor uses), so they show what the game shows. Before, the Players
  page was a point or two off for almost half the players, and the 90+ check put the game's stars
  about seven under (it saw an 89 as an 80), so it only caught a real 95 or so. Squads are built
  as before: Build's own level measure is not changed.

- **The coloured strip in the league tables now marks every continental place**, not only the
  Champions League, Libertadores and AFC Champions League ones (reported for Brazil in a modern
  CONMEBOL world: 1-4 were blue, 5-6 and 7-12 had no colour). Blue is a confederation's top cup
  (also the Libertadores qualifying phases, the CAF Champions League, the CONCACAF Champions Cup
  and the OFC Champions League), orange the one below (the Copa Sudamericana and its first stage,
  the CAF Confederation Cup, the AFC Champions League Two), teal the third (the AFC Challenge
  League). Install the modules again; a world built before this gets it too, unless a
  continental cup was given a name of its own -- then build the world again. FL26 and FL27.
- **League Info said "Promotion/Relegation Off"** for regional groups (a division played in
  regional groups below one league) and for the leagues next to a split league (the second
  division under a league with a championship round, or that league's own league below), with
  no league above or below, although their clubs go up and down. The game's tables link only one
  group of a set (linking all of them makes the game move clubs through every one), and our
  play-offs and splits move the others; the page now shows "On" and the league above and below
  from the world file, also for the phases of a split league (its regular season and its
  championship and relegation groups). Nothing changes in who goes up or down; with Promotion/Relegation Off in
  the Master League settings the page still reads "Off". Install the modules again, no new Build
  needed. FL26 and FL27. Not yet checked in the game.
- **sider.log shows every promotion and relegation of a big world.** In a world of a few hundred
  leagues the season end wrote more than fl26chain's log could hold, so the lines that say who went
  up and down were lost and some lines came out cut in two. The log now holds 16 times as much, hands
  over whole lines only, and says how many lines it had to drop if it ever fills up.

- **Select Team and Kick Off: a country's leagues in order of their divisions.** A league
  followed its league above, so two groups of the same division had the next division's groups
  between them (the Turkish 2. Lig groups with the 3. Lig groups in the middle), and groups of one
  division went by their place in the file (Groupe B, C, then A). Now a country's leagues go one
  after another, top division first, and within a division in the recipe's order. FL 2027's
  Belgian league (one league, no regular season of its own) is known now: a Belgian second
  division of ours sat at the end of Europe's leagues. Build the world again. FL26 and FL27.
- **FL 2027: three leagues had no place in Select Team** in a very big world
  (the three regulation ids the game has no slot for were handed out while ids with a slot were
  still free). Those ids now go last, and a league built on one moves to a free id with a slot
  (no career can have started in it). Build the world again.

- **The window no longer stands still with a very big world.** *Activate* (My world) stopped the
  window for 7-8 seconds after the switch and the Cups page for more than 2 seconds the first
  time it was opened; no stop is longer than about half a second now. What changed: the Cups
  page builds the tab on screen first and the other two right after, the open world is read in
  the background, the sizes of the world backups (Restore) are counted only when that page is
  opened, and a kit or stadium library folder is listed once instead of three times. With the
  pictures of a big world of your own on the PC (300 league logos), the first visit of Leagues,
  New leagues and Cups after a start stopped the window for 2 to 5 seconds: the small pictures
  are now made in the background as soon as the world opens. The reading in the background also
  rests every few milliseconds and takes the world's file in pieces, so the window keeps moving
  while it goes on (it stood for up to 1.5 seconds in the middle of *Activate* with the biggest
  world), and the New clubs page no longer reads club crests while another page is on screen.

- **My world: the line under the cards no longer ends in the middle of a word** when the world's
  state takes two sentences: the first one is shown, the whole text is in the tooltip. The dim
  line of a card is no longer cut at the card's edge (Português, a world with a long name).

- **Open a world / Save as** start in the folder used last, then in the open world's folder, and
  only then in Documents.

- **Build: the line about Mod Studio's modules says what the box at the top says.** It said
  "installed" as long as sider.ini loaded them, also beside "3 older" at the top.

## New

- **A world zip can carry a notice from its author.** A recipe's `notice` (a text, or a list of lines) goes into the world's zip as NOTICE.txt, and Install shows it first in what the zip holds ("From the author of <world>:"). A world without one looks as before.
- **New licence: the FL Mod Studio License.** Mod Studio stays free to use, change and share. Selling it and removing the "Powered by FL ModStudio" mark are not allowed. The packs and worlds you make with it are yours. Versions up to 0.3.0 and the parts our contributors shared under MIT stay under MIT. LICENSE.txt and LICENSE-MIT.txt are in the zip.
- **Updating a shared world keeps its players' careers.** Export the world now asks for a version
  and puts a list of every id of the world into the zip. The next Build of that world keeps those
  ids. If a club, player, league or cup of the shared version is gone, Build stops and names it,
  and *Retire these and Build again* marks the ones taken out on purpose. A player who installs the
  new zip over the version they have gets **Update** when it is a later version of the same world
  (its lineage), keeps every id of theirs and retires only players: their careers and save folders
  stay and go on, and Install asks about an Edit save from before. Another world with the same name,
  a version not made from the one installed, an older version, or one that takes out clubs, leagues
  or cups gets Replace with a warning. A
  league that replaces another takes ids no version had, and a club moved to another place keeps
  its players' ids. Export keeps every shared version by its number (also from the command line,
  `release.py`), gives every zip a number of its own, has a *test zip* option (a tester on a test
  zip gets Replace for the next real version unless its ids are the same), and stops if the newest
  list of the version before cannot be read or the recipe's lineage has no list on this PC (a
  `.fl26ids` file of it put in the ledgers folder counts under any name). A world installed from a
  zip without a list gets Update from a later zip with the same ids (a fix). A club
  with another name under its old id is listed in the Build log and on Install. See the FAQ,
  "Updating a shared world without breaking careers". In our test a career of
  a big world's version before went on in its next version made this way. New leagues and cups
  of an update come only in a new Master League (next point).
- **An update of a world you share keeps the leagues and cups of the version before where they
  were** (mato: an update must never break a career of the version before). Build lays the world's
  competition tables out as the version shared last had them: every league, cup and place at its
  row, every entry the same club; new leagues and cups go after them and appear only in a new
  Master League. Install's Update says how many there are and that your careers go on without
  them. When a place of the version before is gone, holds another club, or gets a club new to
  the world, Build and Export say that careers of it do not go on and Install offers Replace.
  For a version exported before 0.4.0, set the recipe's `id_tables` to its world zip. See the
  FAQ, *Updating a shared world without breaking careers*, step 5, and
  `tools/check_update_ids.py <old zip> <new zip>`. Not checked in the game yet.
- **A start screen.** Mod Studio opens with its name drawn over the lines of a pitch and
  "by Matozanato" under it, while the window gets ready (about four seconds), then fades into the
  window. `FL26_NO_SPLASH=1` leaves it out.

- **Animations.** A section slides to the side its button is on and the next one comes in behind
  it; the tabs of *My world* and of every window with tabs do the same, and the orange line under
  the open section travels to the next button. A button's colour comes softly when the pointer is
  on it (the coloured ones -- Build and install, Activate, Start the game -- get a light around
  them), a dialog rises into its place and fades out when it closes, menus and drop-down lists
  fade in, the mouse wheel glides over a long page, the panel of a league fades to the next league,
  a new line in the status bar slides in and the world cards of *My world* come up one after
  another. Nothing waits for them: every button answers at once.
  *Settings > Program > Animations* switches them off.
  (Beta 2 already meant to fade a page into the next, but the picture of the old page lay under
  the new one and nobody ever saw it.)

- **Sharper small icons.** Back and Forward are drawn as lines at the size of the screen instead
  of a text character, and the arrows of the drop-down lists and number boxes are smooth at
  100 % and at 125-200 % scaling.

## New in FL 2027 (FL26 keeps its cups as they are)

- **A preliminary round for a continental cup.** A cup of a world holds 32 clubs (the CONCACAF
  Champions Cup 16), so a world with more countries than that left most of them out. A league's
  places can now be marked to enter their cup through a preliminary round (the recipe key
  `europe_pre`): one match a tie on 20 August, the strongest v the weakest, the weaker club at
  home; the winners take the places the direct entrants leave. The round is a competition of its
  own, named `<cup> Preliminary Round`, with the cup's emblem. This is a first, simple format --
  the real ones (two legs, two rounds) come later. No dialog for it yet.
  A cup whose places all go through its preliminary round is still its confederation's
  champions' cup when champions play the round (its winner is kept for the Club World Cup), and
  a league with a place in a preliminary round is kept clear of the round's day and the cup's
  days, like a league with a direct place.

- **A promotion play-off in a country that plays February to December.** A league's `playoff`
  (League Builder: Play-off) was refused there ("... of one August-May table each"), so Norway's
  and Sweden's tie between the top division's third from the bottom and the third of the one
  below, or the Icelandic and Chilean play-off of the 2nd to 5th, could not be made. It is taken
  now: the play-off is filled when the last of its leagues is over and played in December, three
  days apart, the last day no later than 29 December, a day clear of the country's cup; its winner
  moves at New Year, with the other clubs. A season that leaves no days for it before New Year is
  refused with that message. A split or Apertura/Clausura in such a country is still not
  possible. Build the world again. Not yet checked in the game.

- **Select Team and Competition Info by confederation.** With a big world the league list of
  Select Team (Master League New, Kick Off, Edit) and the country grid of Competition Info were one
  long list. They now start with one row per confederation: UEFA, CONMEBOL, CONCACAF, AFC, CAF and
  OFC, with the number of leagues. Confirm on one opens it: its leagues (in Competition Info its
  countries) come right under it, and the cursor goes to the first. Confirm on it again, or Back,
  closes it; Confirm on another one switches. A country goes by its own confederation (Australia
  is in the AFC, Israel and Kazakhstan in UEFA). National teams, Other, Classic Teams and the club
  competitions stay where they were. Build the world again and install the modules again. Not yet
  checked in the game.

- **A new country's cup of 33 to 43 clubs is no longer cut to 32.** Two divisions of 18 and 20 now
  play a cup of 36, of 20 and 22 one of 40 (the Coupe de France's fields, whose bracket the game
  draws), the top division and the first clubs of the one below. Build the world again.

- **A third cup for the lower divisions** (request #4), like the EFL Trophy, the FA Trophy or the
  Copa RFEF: tick *Third cup* on a division below the top one. It is a one-match-a-round knockout of
  that division and the one below it, up to 44 clubs, from October to a final in April, on Tuesdays
  that keep clear of the league cup and the country's cup.
- **A new country's third division can play its national cup**: tick *Its best clubs play the
  country's cup too* on the third division, and the cup takes the two divisions above and the
  first clubs of the third, up to 44 clubs.
- **Your own dates for the league cup and the third cup**: *Cup days*, six dates (day.month).
- **Your own order of a league's clubs in Select Team** (request #6): *New clubs* > *More* >
  *Order in Select Team...*. Drag the clubs into order. Clubs you leave where they are follow
  A-Z, and *A-Z* puts the game's order back. Build again and start a new career.
- **Leagues of 8 and 9 clubs** (FL 2027 only; FL26 stays at 10), like Turkmenistan's Ýokary Liga,
  eight clubs meeting four times. Not yet played through a whole season in the game.
- **Trophies in FL 2027** (Leagues > More > Trophies). FL 2027 has no Entrance.lua: Switch on now
  writes the world's trophies in SmokePatch's `modules\common\cinematics.lua` the same way (one
  marked block, the rest of the file untouched). Competitions without a trophy of yours keep
  SmokePatch's. Not yet checked in the game.
- **A trophy of its own for every competition** (recipe key `trophy_variants`, FL 2027 only):
  name one or more trophy folders as bases (`{"bases": ["<folder>", ...]}`) and Build gives each
  competition with no trophy of yours and none of SmokePatch's a variant of a base: the cup in
  another metal, its ribbons and plinth in the competition's colours, its logo on the plates, and
  the flags and banners of the ceremony in its colours with its logo and name. Only textures
  change; the models and the ceremony stay the base's. A competition gets the same variant every
  Build, and no two competitions of a world look alike. A variant made by the last Build is taken
  again. `tools/mktrophyvariants.py` makes one by hand, or a preview picture of it. Not yet checked
  in the game.
- **A club's own money from the recipe** (recipe key `club_money`): a recipe can give each club,
  new or of the game, its transfer budget, followers and how famous it is, instead of Build's
  estimate from its squad and division. Not yet checked in the game.
- **FL27: small clubs have small followings and a small income** (recipe key `club_money`,
  `share`). In a big world half of the new clubs showed the same followers, and every club outside
  the game's own club ranking was paid the same broadcasting fee and sponsor money each season,
  whatever its size: a second-division side with wages of 1.4M got 4.1M a season. A recipe can now
  give a club a finer share: its followers go down to a few hundred, and its broadcasting fee and
  sponsors go down with them -- never below what its wages need. Install the modules again and
  Build the world again; a world built before keeps working as it was.
- **Relegated into the right regional group.** A league with groups below it (three Serie C
  groups, five Regionalliga) can now give each group the clubs above it that belong to its region
  (recipe key `zone_clubs`): a club relegated into the groups goes to its own region's group, as in
  real life, not to the one with the most room. A club can be named at each level (a Süper Lig
  club in its TFF 2. Lig group and again in its TFF 3. Lig group), so it drops into its region
  every time it has a place there. When two clubs of one region come down and their group sends
  only one up, the other plays a season in a neighbouring group and goes home the season after
  (sider.log names every club and why); a recipe can name the border clubs a federation would
  move instead (`zone_border`). Install the modules again (fl26chain.dll); Build again only for
  `zone_border`. Not yet checked in the game.
- **Groups no longer change in the middle of a season.** The game runs its season-end step at New Year and in the autumn too, and a set of groups was moved there by the half-season's table (or last season's) until the real season end put it right; a set now moves only in the pass where the game itself closes its upper league's season, and sider.log says `group set N ...: not its season's end, untouched` for every other pass and `season end` for that one. Install the modules again (fl26chain.dll). Not yet checked in the game.
- **Split leagues and Apertura/Clausura as in real life** (FL 2027 only; FL26 keeps one a country
  and two a world): up to 32 split leagues in a world and more than one in a country (Denmark's
  three divisions, both Mexican ones), seasons of up to 46 rounds (Switzerland 33 + 5), Apertura
  and Clausura twice round (`"legs": 2`, Costa Rica), groups that meet a different number of
  times (`"group_legs": [2, 1]`: Cyprus, Israel, Romania), and a promotion play-off under a split
  league (its places are the places in the relegation group), and regional groups under a split
  league (the four Srpska liga groups under the Prva liga Srbije). A split whose groups differ in
  size (Cyprus 6 + 8, Romania 6 + 10) or that has three groups (Czechia, Bulgaria) has no final
  table of its own in the game, so nobody went up or down from it; its final order now comes from
  its groups (the championship group first, then the next), and its clubs go up and down from
  that. The game keeps no table for a split's groups either, so each group's final order is
  counted from its matches (points, goal difference, goals scored), regular phase included. Bulgaria's regular phase never ended and its groups stayed empty: with
  more than 65,535 matches in a world, a fixture keeps only the last 16 bits of a match id, and
  when the game asked whether the league's season was over it got a cup match with the same last
  bits, still unplayed. A fixture's match is now always the one of the fixture's own competition
  (fl26match). A split league also gets a competition id under 255 -- a free one, or the id of a
  league that is no split, which takes the split's instead -- and only when no league has such an
  id left does it stay past 255, on an id whose last byte no other league or cup has. Build the
  world again to get it. Not yet played through a whole season in the game.

## Fixed in FL 2027

- **A new Master League with a very big world no longer dies while it is made** (B408). The
  world's seasons have more than 65535 matches and its database more than 65535
  players, which needs our `fl26match` module, and Mod Studio did not install it: the career
  closed the game at the end of its loading. **Home > Install now** puts it in now (FL 2027 only;
  in FL26 it does nothing).
- **A Kick Off between two clubs of a new league no longer wears another league's badge and
  scoreboard** (B427, pop1806: the J.League's badge in a Serbian league). FL
  2027's own modules (sleeve badges, scoreboards, referee kits, match balls) ask SmokePatch's
  `CommonLib` which league two clubs share, and CommonLib reads a league's number as one byte. A
  big world has leagues numbered past 255, so league 553 was read as 41, the J.League, and its
  clubs were counted as J.League clubs. `fl26slotnames` now gives CommonLib every such league
  under its own number, right after the game reads the file, and takes its clubs out of the
  league they had been read into. Nothing of SmokePatch's is changed on disk. FL 2027 only (FL26
  has no league past 255). Install the modules again (**Home > Install now**); no new Build.
- **A relegation play-off under the Scottish Premiership is played by the club that finished
  11th** (B425, found in the second season of our season test). The Premiership is a
  split season of the game's own: 33 rounds, then the top six and the bottom six play five more.
  A play-off of a league built under it (the Championship's runner-up v the Premiership's 11th)
  took the 11th after the 33 rounds, and was filled while the bottom six were still playing. When
  another club ended 11th, the wrong club had played: the real 11th went down without a match and
  the Championship's runner-up went up even when it lost. The play-off now waits for the groups'
  last round and takes the final table's place, and the season's end moves the clubs by the same
  table. The same goes for a league built under the Danish Superliga. Install the modules again
  (**Home > Install now**); a world built before this beta gets it for the Scottish league
  without a new Build, for the Danish one with the next Build.
- **A group league keeps its own place in the game's league table after the season** (B418,
  found in the season test of beta 2 on a big world; beta 1 had it too). At the season's end
  `fl26chain` gives every club a group league ends with that league's slot, and it read the slot
  from the first club the league held. One club the game itself had marked with the league
  above's slot was enough for the whole group to get that one: from the second season on about
  half of the group leagues carried another league's slot. The slot now comes from the world file
  (`league ... slot=`), and for a league it does not name from most of its clubs; the log says
  when a league's clubs carried another. The seasons after it were played either way, and what a
  player could see of it is not known. Install the modules again (**Home > Install now**); no new
  Build is needed. Not yet checked in the game.
- **Groups of one division in a February-December country** (B404). Build refused
  groups under a league that plays February to December, so Argentina's Primera Nacional could
  not be its two zones under the Liga Profesional. A set of groups is now fine when all of it, the
  league above too, plays the one season; groups of a February-December and an August-May season
  together are still refused, as are a split, Apertura/Clausura and cup_join in a set.
- **A calendar-year league no longer stops another league's season at New Year.** A league whose
  season had just ended could hand its old round to another competition's matches, which were then
  moved into the next season, so that league's regular phase never ended (Israel: no split groups,
  nobody up or down). Build the world again and start a new career.

- **A league was listed as "Other" in Select Team** in a world of more than 172 leagues: the
  173rd took a Select Team place the game keeps for its own "Other" group (special teams). No league takes that place any more; a world can have 379 leagues
  instead of 380. Build the world again; the league moves to a place of its own.
- **Promotion and relegation play-offs were never played** (the 2. Bundesliga relegation
  play-off, the Eerste Divisie, the TFF 1. Lig and the others under a league). The play-off took
  its clubs as soon as its leagues were over, and its matches were never made, so no club went up
  or down through it. It now makes its matches itself, as a cup does on its fill day, and its
  winner is kept when the last match is played, so the season end still knows it after the new
  season's fixtures are made. The same went for a Clausura play-off that took its clubs at the
  end of the Clausura. A career that has a play-off filled with no matches gets them before its
  first day. Install the modules again; a career gets it at the end of its season.

- **FL27: Select Team's attack, midfield and defence numbers of weak clubs are no longer all 39.**
  The game showed no number below 39, so the clubs of the small leagues all read 39 / 39 / 39. A
  weak line now shows its own number, down to 26; a number of 40 or more is what it was. Install
  the modules again; no new Build needed. FL 2027 only; FL26 stays as it was. Not yet checked in
  the game.
- **FL27: new players show the rating they were made for.** Build brings the players of a new
  club (the placeholder squads, and the ones that stay at a NewLife club) to their level with the
  game's own rating now, the same number the Players page shows, so a squad meant to be 63 shows
  63 in the game. Before, it measured with a rough mean of a few abilities, and a player could
  come out six or more better or worse than meant. FL26 builds squads as before. Build the world
  again to get it.
- **Belgium had no club in Europe in an FL 2027 world** (request #5). FL 2027 plays the Jupiler
  Pro League as one league of 18 with no split (regulation 115), and the European access list
  still named FL26's regular phase (155), which FL 2027 does not have. Build now gives Belgium's
  places to 115 when the tables have no 155. The *European places of the game's leagues* window
  shows them, and own places for the Jupiler Pro League replace them. Build the world again.
  FL26 worlds stay as they are.
- **FL27: a division under the game's Argentine league began in February on matchday 14 or 21**
  (reported by Quemer07 and Frosscar). FL 2027 plays Argentina from February to December, and Mod
  Studio still dated the divisions below the Liga Profesional August to May: the season took them
  in at New Year with the first rounds gone, and ended them half way. Mod Studio now reads from
  the game which countries play February to December, so on FL27 those divisions (and a super
  cup added to the Liga Profesional) play February to December with it, from matchday 1, with
  promotion and relegation at New Year. FL26 is unchanged. Build the world again and start a new
  career to get it.
- **Colombia's continental places can go by the whole season** (Vicentico). The game plays the Liga BetPlay DIMAYOR as two tournaments with a table each, and a place given to **Liga BetPlay DIMAYOR I** went by the first one (the Apertura) alone. **European places of the game's leagues** now also lists **Liga BetPlay DIMAYOR**, the whole season: its places go by both tables added together (points, then goal difference, then goals), counted when the second tournament ends, and they fill the Libertadores and the Copa Sudamericana of the next year. The same for the MLS (**Major League Soccer**, under **MLS First Round**). A career begun after the first tournament counts the second one alone that year; until a season has ended, the places go by the first tournament as before. Not yet checked in the game: build the world again and play to the next January.
- **Libertadores places of the game's leagues without the modern pre-rounds.** With the classic Libertadores, a game league given Libertadores places in **European places of the game's leagues** kept the game's own as well: Chile given only its champion still sent its 2nd and 3rd to the qualifying round, and a place moved to the Copa Sudamericana played both cups. Now a league given Libertadores places of its own plays exactly those: a club of it (or of its cup) that the game put in and that holds none of them makes room for the next place of ours, else for another CONMEBOL club. The title holders stay. Leagues given no Libertadores place keep the game's places as before. Not yet checked in the game.
## Football Life 2027

- **A first qualifying round in July** (FL27 only; FL26 stays as it was). In a world whose
  European places fill it, the Champions League and the Conference League get a first qualifying
  round of 32 clubs, played in July, and a second qualifying round of 32 after it. The champions
  of the world's European leagues that have no place of their own (one league per country, in
  UEFA's association order) start in the Champions League's first round, so every UEFA
  association is in Europe. The winners go on to the second round; the Champions League's losers
  drop to the Conference League's second round. The Europa League has no qualifying round of its
  own: its third qualifying round and play-off take the Champions League's losers, and its
  qualifying places go to the Conference League's first round. 88 clubs in the qualifying (64
  before). The play-offs and the league phases are as before. The first round is played from a
  career's **second summer**: in the first season the second rounds take the clubs it would have
  sent them. Build the world again with this Mod Studio to get it; a world whose places do not
  fill the July round keeps the August rounds, and Build says which one it got.
- **UEFA qualifying as UEFA plays it** (FL27 only; FL26 stays as it was). A world whose European
  places fill it now gets every round: the Champions League's first round (32 clubs) and the
  Europa League's (16) in July, the second and third rounds of all three competitions, and
  play-offs of 32 for the Europa League and the Conference League. The losers drop as at UEFA:
  both first rounds' to the Conference League's second round, the Champions League's later
  rounds' to the Europa League, the Europa League's to the Conference League. 112 clubs in the
  qualifying; 28 / 12 / 4 go straight into the league phases, which stay 36 each. Build the world
  again to get it; it is played from a career's second summer (the first season as before), and
  a world whose places do not fill it gets the July round above, or the August rounds.
- **A bigger Conference League qualifying** (FL27 only; FL26 stays as it was). A world with enough
  Conference League places now also gets a Conference League first qualifying round in July, and
  its rounds are as big as the game takes: 62 clubs in the first and second rounds, 40 in the third
  and the play-off. 170 clubs in the qualifying instead of 112, 74 of them in the Conference League
  (16 before). Its league phase is the play-off's 20 winners and the 16 clubs that lose the Europa
  League play-off. The Champions and Europa League rounds stay as they are. Build the world again
  to get it; it is played from a career's second summer, and Build says which rounds it got.
- **Belgium's places counted once.** Build, choosing the qualifying rounds, counted Belgium's shipped places under
  both its FL 2026 and its FL 2027 id, three Champions League places too many in a big world. A
  Champions League qualifying list up to three short is now filled from the big five, and Build
  says so.
- **Check the plan counts FL27's rounds.** For a FL27 world with the July first qualifying round,
  Check the plan and the head of a Build's log said "Champions League qualifying has 54 places
  listed for 32 clubs; the last 22 get none" -- FL26's count; the Build itself gave every place a
  tie. The summary now counts as the Build does: the direct entrants of FL27's format (28 / 12 /
  4 or 0) and a line with each qualifying's places against its clubs, so a hole that the big five
  will fill is seen before the Build.

## Kits

- **More kits for new clubs.** The kits Mod Studio makes for new clubs (Kits made in the clubs'
  colours, needs Kit Server) are drawn in patterns of a library of more than 100: stripes,
  pinstripes, hoops, bands, halves, quarters, sashes, chevrons, checks, diamonds, dots, waves,
  fades, side panels, yokes, contrast sleeves and collar and cuff trims. Every club gets a home, an
  away and a third kit and a goalkeeper's, in colours clearly apart from each other, the same at
  every Build. A club with only a numbered badge now gets kits too, in colours picked by its name.
  The kits made before are drawn again at the next Build.
- **Shirts of new clubs worn out, not tucked in.** Half of the kits made for new clubs took the
  "tight kit" setting from the club whose numbers they borrow, and the game then shows the shirt
  tucked into the shorts (the Kick Off walkout and the line-up). Every kit Mod Studio makes from
  pictures now has the tight kit off, as most clubs of the game; the next Build writes them again.
- **All kits of a new club can be picked.** The game offers a team only as many kits as its entry in
  the kit colour table (UniColor.bin) says, and a team missing from that table gets two. New clubs
  had no entry, so in Kits before a match only the home and the away kit could be chosen. Build now
  writes the table with an entry for every club with kits made or imported (home, away, third and
  goalkeeper's), keeping the game's own entries as they are.
- **League Info: "Lower League" of a league in the middle is the league below it** (B420). A league
  with one above and one below -- the National League, Austria's 2. Liga, a country's second division
  over regional groups -- showed itself as its own lower league: the game's page knows a pair of
  leagues only, and for a league that has one above it writes the league itself as the lower one.
  `fl26catlist` now hands the page the league below (the game's own link, or the first group of the
  set below it, as the promotion line already did). A league with nothing below it shows itself, as
  the game's own second divisions do. No new Build needed, only the modules installed again.
  In beta 4 the fix never went in: another of our modules (fl26compcache) puts its jump on a
  function `fl26catlist` only calls, and it took that for bytes it did not know (sider.log:
  "League Info's lower league left alone"). It now accepts such a jump there. Not checked in the
  game yet.
- **A new icon.** The program's icon is now `>fl_` with "// mod studio" under it, in the colours of
  the top bar.
- **No red "NOT READY" while a world zip is switched on.** Import your world installs the zip first
  and switches the world on after; for that minute the header said "NOT READY, 2 modules missing"
  in red, though nothing was wrong. It now says "Working..." until the switch is done. The status
  bar no longer keeps "First start: Mod Studio unpacks the game's tables" after they are unpacked.
