# What's new in Mod Studio 0.3.0 (beta)

0.3.0 (DATE) is the first Mod Studio for **Football Life 2027** too. The same program works with
FL26 and FL27: point it at the game folder (Settings), and it finds FL26's `FL_2026.exe` or
FL27's `FL_2027.exe`, that game's tables and its saves. It also brings the fixes of 0.2.5.2,
which was never released on its own.

This is a beta: tell us on Discord what does not work in FL27.

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

- **Select Team lists the league's clubs.** Master League > Database > Team Info, League mode
  and the other screens that pick a league and then a club: with the cursor on a league, the
  right panel was an empty red list. It now lists that league's clubs, titled "Team List" ("Teams"
  when the game runs in another language), each club with its crest. Confirm, and it shows the
  players of the club under the cursor, titled "Squad List", as before. The crests come with the
  world: Build writes a copy of the screen's layout with a crest cell into the world, and a world
  built before gets it when it is switched on. FL26 and FL27.

## Fixed

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

## Known in FL27 (beta)

- **The packs carry FL26's players.** The Worldpack and Europe pack zips were made with FL26, so
  in FL27 they play with FL26's squads. Packs made with FL27 come later; a world you build
  yourself in FL27 has FL27's players.
- **NewLife is not checked on FL27 yet.** It was made for FL26's players.
- **sider.log shows a Lua error of SmokePatch's `SleeveBadge.lua`** for the clubs a world adds.
  The game plays on; it is theirs, not Mod Studio's.

Worlds and careers of 0.2.5.1 keep working in FL26: Build them once with 0.3.0. The fixes of
transfer money, NewLife squads and Select Team places 76/77/80 need a new Master League to show.
