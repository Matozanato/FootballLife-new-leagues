# What's new in FL Mod Studio 0.3.0

0.3.0 (2026-11-04) is the first Mod Studio for **Football Life 2027** too. The same program works
with FL26 and FL27: point it at the game folder (Settings), and it finds FL26's `FL_2026.exe` or
FL27's `FL_2027.exe`, that game's tables and its saves. It also brings the fixes of 0.2.5.2, which
was never released on its own, and everything fixed in the closed beta.

## Before you update

**This is more of a test version: if you don't have to, don't rush to update.** It changes a lot (a
second game, the calendar, promotion and relegation, the European places). The closed beta did not
turn up any big bugs, but that can also mean some were not found yet, and a problem of a career can
show only after a season or more. It does not have to happen. **If 0.2.5.1 works for you, or you are
in a long career you care about, stay on 0.2.5.1 for now** and update once this one has been played
for a while. If you update anyway, keep a copy of your save folder and your old Mod Studio folder
first. For FL27 you need this version.

Worlds and careers of 0.2.5.1 keep working in FL26: Build them once with 0.3.0. The fixes of
transfer money, NewLife squads and Select Team places 76/77/80 need a new Master League to show.

For FL27, use **NewLife Database 1.6b4** (on the Discord, #newlife): older NewLife versions were
made for FL26's clubs.

## Football Life 2027

- **Mod Studio finds FL27.** `FL_2027.exe` and `FL 2027 start.exe` are taken as the game, the
  game's tables come from its season archives (`download\data_s2627.cpk`), and the saves from
  FL27's own folder (`Documents\SPGAME\Football Life\2027\save`), for Mod Studio and for the
  modules in the game. A new player's ids start above FL27's own players.
- **Our modules work next to SmokePatch's.** FL27's exe has changes of its own in many places our
  modules change too. Where both change the same place, ours now goes in front of theirs instead
  of switching itself off: season types, region headings, league flags in Select Team, the
  Conference League table as one list with MP, the Round of 16 match titles.
- **Europe in FL27.** The Champions League and Europa League league phase, the February play-off
  and the knockout are FL27's own, on FL27's dates. Mod Studio decides who gets in (the places of
  each league, including the new ones), plays the summer qualifiers and the August play-off before
  FL27's draw, and sends the losers down to the next competition. The Conference League stays
  Mod Studio's. Played in FL27 over two seasons: 36 clubs in each league phase, the knockouts to
  the end, promotion and relegation, the cups, save and load.
- **Worlds and packs.** A world you build in FL27 uses FL27's tables. The Worldpack and the Europe
  pack zips install and play in FL27 too, with two things for worlds built before this version:
  switching one on now writes the MP column and the region headings for the game's exe.

## Also new

- **The program is called FL Mod Studio now** (it was FL26 Mod Studio): it works with FL27 as well. Only the name you see changes: the window, the menus, the guides. FL26ModStudio.exe, the folder in the zip, %APPDATA%\FL26ModStudio and the fl26 modules keep their names, so updating works as before and nothing of yours moves.
- **Pick which of the game's "Other ..." groups a league replaces in Select Team** (vmican). Leagues > **Places in Select Team**: the Select Team column of each of your leagues is now a list, *Automatic* (as before: the order decides, the game's groups give their place last) or *in place of* Other European Leagues, Other Latin American Teams, Other Clubs (Africa) or Other. The next Build puts the league there whatever the order; that group's own clubs are then not in Select Team. With a South American world, for example, the Other Latin American Teams can make room for a league of yours. In a Master League started after that Build the league's clubs have the group's place too (Team Info lists them under the league; `fl26clubs` answers that slot from the league for the Master League club slot, `pick=1` in the world file).

- **Select Team lists the league's clubs.** Master League > Database > Team Info, League mode
  and the other screens that pick a league and then a club: with the cursor on a league, the
  right panel was an empty red list. It now lists that league's clubs, titled "Team List" ("Teams"
  when the game runs in another language), each club with its crest. Confirm, and it shows the
  players of the club under the cursor, titled "Squad List", as before. The crests come with the
  world: Build writes a copy of the screen's layout with a crest cell into the world, and a world
  built before gets it when it is switched on. FL26 and FL27.

- **Colours in the league tables.** A league's standings show a coloured strip on the left of each
  row whose place means something: blue for the Champions League (the Libertadores and the AFC
  Champions League too), orange for the Europa League, teal for the Conference League, green up a
  division, amber a play-off, red down. The European places come from the world's places for
  each league, up and down from the game's own counts; in the League Phase, 1-8 are green and
  9-24 amber. Build writes the strip's cell into the world's table layout with the MP column; a
  world built with 0.2.5 gets it when it is switched on. FL26 and FL27. (Thanks vmican)

## Fixed

- **NewLife in FL27: no club twice, none taken for another** (NewLife Database 1.6b3 on). FL27 numbers some clubs differently from FL26, and gave seven of FL26's ids to other clubs of the same country (FL26's Meizhou Hakka is Liaoning Tieren in FL27). Mod Studio took those clubs of FL27 for NewLife's FL26 clubs, and NewLife's Liaoning Tieren came in beside FL27's. With 1.6b3 the release says the names a club has in each game: in FL27 Liaoning Tieren is FL27's own club and Meizhou Hakka a new one, in FL26 as before.
- **FL26 and FL27 keep their own tables** (B307). Mod Studio unpacked the game's tables into one folder for both, so after Settings > Game folder was switched to the other game, a Build read the first game's tables (its players and ids) until **Unpack the game's tables** was pressed again. FL27's tables now go in `%APPDATA%\FL26ModStudio\tables27` and are unpacked by themselves the first time FL27 is chosen; FL26's stay in `tables`. A tables folder picked by hand (**Use another tables folder...**) is remembered for each game on its own.
- **Settings names the right save folder after a switch of the game.** With Settings > Game folder switched from FL27 to FL26 (or back), the note under Master League careers still named the first game's save folder; switching a world's careers always used the right one.
- **Regens keep their names after a save is loaded** (regen module). In a career started in the same session, or with a player the game regenerated twice, some regens came back from a load with another name (in FL27, and more rarely in FL26). The name pools are now read from the game's database at the title screen, and a player regenerated a second time keeps the name he got first.
- **FL27: the regen module's portraits are FL27's size** (regen module). The face pack's portraits went out at 180 pixels square, and FL27 only takes its own size: they go out at 128 x 128 now, and so does a player portrait you give in *Players* > **Portrait**. FL26 was not affected. Start FL27 through its launcher (**FL 2027 start.exe**, its shortcut, or **Start the game** in Mod Studio): FL_2027.exe started directly can close while a new Master League is being created or on its first days (see Known issues).
- **Build no longer stops on the players of a club the game does not have.** A world started with FL26 and built for FL27 stopped with "players of 319: nothing to copy a new player from": the two games do not have the same clubs (319 is FL26's SSC Bari, and FL27 has no club 319), so the players added to that club had no squad to be copied from. Build now skips that club's player changes and the log says which club it was.
- **No more crash on the first day of a Champions League qualifying round** (B312, B308). In some worlds (seen with the Europack in FL27 and with a world of 22 leagues in FL26) a qualifying match could keep a club that had since moved out of its place in the game's team list, and the game closed on the day that match was played (often the second qualifying round, early August). The match now takes the club that really plays it, and a career already saved before that round is mended when it is loaded.
- **Leagues > Clubs and names and Players open the league you picked.** They opened those pages on the league last picked there, so with a new league picked on Leagues, Clubs and names still showed another one (Xxspedd).
- **A NewLife league below a league of the game has promotion and relegation with it** (B314). NewLife put every league in as a top division of its own, so Greek Super League 2 played next to the game's Greek league with no clubs going up or down. A NewLife league of a country the game has a league of now goes in as the division below that league (the game's lowest one there, when nothing of yours is under it already); the page says which, and **Leagues** > **Edit** > **Division** changes it. Worlds you already have keep their leagues as they are: there, set the Division by hand and Build.
- **A league can go under the game's split leagues** (B320, juanjose). **Leagues** > **Edit** > **Division** never listed the Scottish Premiership, the 3F Superliga or the Jupiler Pro League: they play a regular phase and then top and bottom groups, and the list only took leagues of one phase. They are in the list now, so a Scottish Championship, a Danish 1st Division or a Challenger Pro League goes under them with promotion and relegation (the regular phase is what the division below links to, as in the Modpack). A NewLife league of Scotland, Denmark or Belgium goes there by itself, as for the other countries (B314).
- **A free European place goes to the club next in line, the others moving up** (B313, pepponeee). When a competition had a place no club of its list took (a world with no cup winner places, or a title holder already in through its league), it went to the next club of a big league not in Europe yet, so the 8th of the Premier League played the Europa League while the 7th stayed in the Conference League. Now the 7th goes up and the 8th takes its Conference League place, as at UEFA. A cup winner keeps the place of its cup.
- **January-December leagues of a country of yours have promotion and relegation** (B315, huliaanos). A new country whose leagues play the calendar year (`season` set to January-December, as Finland, Norway or Sweden) closed its seasons at New Year, but no club went up or down between its leagues: the game's season end never takes a league of a region it has no league of. fl26join now does that exchange itself at New Year, with each pair's numbers from your world (the last of the upper league down, the first of the lower one up, as the game does it), before the new season starts. A league whose season stopped half way, or a split league, moves nobody; a match or two never played (a postponed one) does not hold a league back.
- **The national cup of a January-December country of yours is played** (B318, huliaanos). A new country whose leagues play the calendar year (Finland's Suomen Cup) had its cup on the season's list, but the game offered it before the country's leagues were in, found no clubs for it and left it out of every season. fl26join now puts the cup in right behind those leagues, each season.
- **Install mods: a zip with an empty livecpk folder installs** (B317, Jh). A pack whose livecpk held a folder with no file in it, next to a `root` of the game's own, stopped with "[Errno 2] No such file or directory: ...\livecpk\root (2)\.modstudio". An empty folder is now no part of the install: nothing to copy and no `cpk.root` line for it.

- **Leagues missing from Team Info and the transfer lists (B306).** A league on Select Team
  places 76, 77 or 80 (LigaPro Serie A, SuperSport HNL, Guatemala or TOPsport A lyga in the Europe
  pack) was in Edit and Competition Info but not in Team Info, and its clubs were not on the
  transfer lists: the game gave those clubs no Master League place. Start a new Master League.
- **The first Add to your world froze the window (B303).** The first time a NewLife league was
  added, the window did not answer for about 10 seconds. It now takes a moment.
- **A Documents folder named in other letters, and saves under another number (B296).** With
  Documents in letters outside the system's code page (Georgian, `C:\Users\...\დოკუმენტები`),
  Edit mode could not keep the changes made to clubs past the game's 750, and the final tables
  kept for Europe were not written either. The modules now write in any folder name. They and
  Mod Studio also look for the saves where the game really keeps them: the number in `sys.ini`,
  or, when the game saves under another one (`...\0\save`), that folder. Mod Studio also finds a
  Documents folder moved to OneDrive or another drive. (Thanks GiorgiM)
- **Small clubs of the game buying stars for 70M (B298).** A club of the game that is in none of the
  game's leagues (Zalgiris, HJK, RFS and others in the Europe pack) has no transfer money and no
  followers in the game's tables. Put into a league, it counted as a top club and was paid about
  EUR 250M a season for TV, so it bought Endrick and Estevao. Build now gives these clubs money
  and followers by squad and division, as it does for new clubs. Build your world again and start
  a new Master League. (Thanks vanni11)
- **4.5-star clubs in a fourth division (B299).** A NewLife club with no rated player of its own, in a
  league with none either, kept Mod Studio's stand-in players ("FL P...") at a top club's level:
  70 to 81 in the Polish fourth division. They now come to the division's level. Build your world
  again and start a new Master League. (Thanks Risto)

## Known

- **Start FL27 through its launcher** (**FL 2027 start.exe**, its shortcut, or **Start the game** in
  Mod Studio): FL_2027.exe started on its own can close while a new Master League is being created
  or on its first days.
- **The packs carry FL26's players in FL27.** The Worldpack and Europe pack zips were made with
  FL26, so in FL27 they play with FL26's squads. A world you build yourself in FL27 has FL27's
  players.
- **The Conference League winner does not always get its Europa League place** (pepponeee): seen in
  the second season of a world of 22 leagues. Being looked at.
- **The Austrian Bundesliga does not take a league below it yet**: **Leagues** > **Edit** >
  **Division** does not list it (the game makes it in another way than the split leagues above),
  so NewLife's second Austrian division plays on its own, with no promotion and relegation with it.
- **sider.log shows a Lua error of SmokePatch's `SleeveBadge.lua`** in FL27 for the clubs a world
  adds. The game plays on; it is theirs, not Mod Studio's.
