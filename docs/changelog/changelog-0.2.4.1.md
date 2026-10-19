# What's new in Mod Studio 0.2.4.1

0.2.4.1 (beta, 2026-10-20) fixes what you reported since 0.2.4 (2026-10-18). Worlds of 0.2.4 keep
working: Build them once with 0.2.4.1, and careers carry on.

## Fixed

- **Kits on FL26 1.0 without the game's updates (B153).** Build said "only pictures changed since
  the last Build" or "no kits: the game's UniformParameter.bin was not unpacked", and the new clubs
  played in blank kits. FL26 1.0 keeps its kit list only in the game's Data archives, and Unpack the
  game's tables read just download\. It now takes it from Data too (the updates' own list still goes
  over it). Tables an older Mod Studio unpacked without it: Build asks once to unpack them again.
  (Thanks ZeDosCaes21)
- **Kits with your own tables (B143).** With Settings > Use another tables folder (a database mod
  or tables edited in another editor) over the game's, Build drew no kit at all and said to unpack
  the game's tables, which did not help. The game's kits file now goes beside your tables (or the
  one your folder has itself), and Build finds it.
- **A world lost to its unfinished Build folder (B150).** When the last step of Build could not put the
  new world in place (a file of it open in the game or a folder window), the old world was already
  deleted and only `<world>.building` was left; the next try said it "has no fl26world.txt". Build
  now moves the old world aside first and puts it back if the new one cannot go in, and says what to
  close. A `.building` folder is never switched on as a world. (Thanks Tysonche35)
- **The world card's league count (B141).** The card of the open world counted a group of clubs in no
  league (the Europack's Croatian clubs) as a league: 81 while open, 80 once another world was open.
  It is 80 both ways now.
- **Rename world and Build's tab (B142).** After Rename world, the tab under Build still showed the old
  name, and when the open world was the copy Build keeps, saving wrote it under the old name again.
  Both follow the new name now.
- **"Refused bytes ... Install now" when another mod had changed the exe (B145).** When the game's
  FL_2026.exe already had another mod's fix at the spot of one of our small crash guards, Mod Studio
  said to press Install now, which cannot help. It now says the exe has another mod's change there,
  that one guard is off and the rest is in, as a warning. (Thanks Schmiddi)
- **"No free competition ids left" now says what to do (B154).** A league added to a world that already
  has all 255 competitions the game takes (the Europack is at 220) stopped Build with only that line.
  It now says the world is full and to untick national or super cups of countries you don't play
  (My world > Cups) or take out a league. (Thanks Tysonche35)
- **Outfield players with the number 1 (B156).** A player Build adds to a squad (a free agent for a club
  short of keepers or players, a transfer, a new player) got the lowest free shirt number whatever his
  position, so a club whose keeper had moved on gave its 1 to a defender or a striker. Keepers now take
  a free keeper's number (1, 12, 13 ...) and everyone else another one. The Players page shows the same
  number Build will give. (Thanks jibibi)
- **Leagues added to a zip world were gone after Make it editable (B146).** Making a ready world
  editable read its recipe back from what the world was built with, so leagues you had already added
  to it (Add a league, a package) were dropped. They now stay, at the end of the list, and the message
  after Make it editable names them. (Thanks Tysonche35)
- **A new club's number 1 worn by a forward (B157).** The players a recipe (NewLife) puts into a new
  club's squad took the shirt numbers of the squad Build first made for the club, whatever their
  position, so at Bourg-en-Bresse a centre forward wore the 1. Now the club's first keeper wears the
  1 and swaps numbers with whoever had it; a recipe that gives its own numbers keeps them.
  (Thanks jibibi)
- **Make a league package stopped on a world from a zip (B148).** "picture ... is missing" with a
  path of the PC that built the world (D:\dev\...), so no league of a Modpack or Europack world could
  be made into a package. A picture or kit folder not on your PC is now taken from the world as it is
  in the game (the league's emblem, the club's crest, the club's Kit Server kits), and what is in
  neither is left out with a line in the log; Build draws a badge for it. (Thanks Biancopr)
- **Your Edit seemed gone after Build of a new world (B155).** Since 0.2.4 each world keeps its own
  save folder, and the Edit data (EDIT00000000) goes with it, so a new world starts with no Edit;
  the note said only "careers". The note now says the Edit data goes with them too. To keep one Edit
  for every world: Settings > untick **Each world keeps its own careers**, then copy EDIT00000000
  from `save_<your old world>` into `save`. (Thanks pepponeee98)
- **The same world built under a new name gave its players other ids (B155b).** 0.2.4 gives a new
  club 30 players, not 22, so a recipe of 0.2.3 built as a new world numbered the new clubs' players
  afresh, and an Edit or a career of the old world showed other people. Build keeps a world's ids only
  for the same world; a world built for the first time now takes the ids of the world of the same
  leagues on your PC, and the log says which one. (Thanks pepponeee98)
- **A Modpack/Europack world lost all its kits at Switch on with SPFL26's kits.lua (B158).** With
  `common\kits.lua` on in sider.ini and no `content\kits` folder, Install mods merged the world's kit
  lines into `content\kit-server\map.txt`, and switching the world on looked for the kits in
  `content\kits`, found none and took every one of those lines out again (only the "added by" header
  stayed). Switch on now picks the kit and scoreboard folders the way Install mods does. (Thanks jibibi)
- **Europack and Modpack worlds made editable stopped Build for their own cups (B159).** These worlds
  were built with some competition ids under 130 (Malta's cup, Egypt's), and Build on this PC only
  hands out 130..255: a Build with nothing changed stopped with "no free competition ids left" for a
  cup, and adding a league stopped too. A world built with such ids now keeps them and the others of
  that kind, and a league taken out gives its cup and super cup ids back. Every other league and cup
  keeps the ids it had, so careers carry on. (Thanks AHMED and Tysonche35)
- **The Players page's rating was not the game's (B53).** Mod Studio showed the mean of a few
  abilities, and the game works its rating out with weights of its own for each position: a
  keeper whose GK abilities average 70 showed 70 and was a 64 in the game. The list, the Rating box
  and Squad level now use the game's own reckoning (fitted to 2500 players of the game: the same
  number for six in ten, never more than two off). The Rating box and Squad level land on the
  number you ask for: every ability moves by the same amount and the few that count most for the
  rating by one more. Build still levels squads as before. (Thanks LaraCroft)

- **Deleted worlds kept taking the disk (B131).** Delete world moves the world into a copy under
  Restore points so it can come back, and that copy kept its gigabytes with no way to free them from
  Mod Studio. Restore points now has Delete this copy for good... for a deleted or copied world
  (it asks first and says how much it frees), and Delete world says how big the world is and where to
  free that space. (Thanks Vicentico)
- **Import crests ticked the wrong club (B139).** A picture whose name only held a club's name (or the
  other way round) was ticked at 70 %: "United Sport FC" of the UAE took nine African "X United"
  crests, Rangers took "rangers-kinshasa", LA Galaxy "ts-galaxy". The country of the pictures now
  counts: the one the folder is named after (`Africa/Ghana/...`, or a league of the world) or the
  file name starts with (football-logos.cc's `poland_cracovia_...`). A club of that country goes
  first, and a club of another country is never ticked. A name only inside the other is ticked (65 %)
  only when it is the one club of that country it fits ("mostaganem" for ES Mostaganem); otherwise
  it is a suggestion at 50 %, unticked. "F.C.",
  "Football Club", "Sporting Club" and NewLife's "(GHA)" no longer stand in the way of the same name.
  (Thanks David)
- **The game's Club World Cup with an empty semi-final (B149).** The game takes its African club
  from Other Clubs (Africa), where it files only Wydad Casablanca. A world with Morocco's league (the
  Modpack) takes Wydad out of that group, so the cup got three clubs for four places: the South
  American champion went straight to the final and there was no third-place match. The fourth
  place now goes to the CAF champion of your world when it has the CAF Champions League, else to
  Wydad from its league. (Thanks Micarodvzla22)
- **The AFC Champions League Two was empty from the second season (B160).** From the second season
  the game puts most of the J1 League into its own AFC Champions League, and a club already in a
  continental cup is passed over, so the Modpack's AFC Champions League Two found 28 clubs for 32
  places and was not played at all. A place no club is left for now goes to the next club of the
  leagues the cup takes its places from, and the log names it. Also, worlds of more than 64 leagues
  kept last season's final table for only the first 64 (Vietnam, Jordan, Kuwait, Bahrain and Oman
  then sent the clubs on top of the live table); now 256. (Thanks bruce_wayne)
- **Menu Server stopped at the game's start with a world that has no menus (B112).** With
  `MenuServer.lua` on in sider.ini and no `content\menu-server\map_competitions.txt` (a world zip
  without menu themes, or the line switched on by hand), the module stopped as it loaded. Switch on
  now puts an empty one there, as it does for Kit Server's map_comp.txt. (Thanks David)
- **The same club on both sides of a Champions League round-of-16 tie (B121).** In a later season the
  game could give the winner of an earlier season's play-off tie for a February one, so a club of the
  top eight (Lyon) also came in as a play-off winner: Lyon v Lyon. A winner that is not one of the
  tie's two clubs is now taken from the tie's own table (else the seeded club), and the log says so.
  (Thanks Micarodvzla22)
- **Restore points in your language (B134).** In Spanish, French, Portuguese and Croatian the
  Reason column of Restore points stayed English ("Switch on: kits map"); it is now said in the
  language of the window, older restore points too. The Leagues page says "1 group of clubs in no
  league", not "1 groups", and the bottom bar says "Switching ... on" or "Exporting ..." while
  it does that, not "Building...". Column names cut short in those languages ("DOSSIERS ACT" on
  Profiles, "VALORACIÓN" on Players) now show whole.
- **"No free player id left below 262144" now says what to do (B161).** A world with too many
  players (90 leagues) stopped Build with only that line, and the game kept the world of the last
  Build, so a league taken out seemed to stay. It now says the world has too many players: take out
  a league or two (Leagues > Remove) and Build again. (Thanks vmican)
- **Remove, Edit and Add lower tier did nothing on the Leagues page after a rename (B161).** Once a
  league of the world had been renamed since the last Build, the list of new leagues stopped half
  way, and with it these three buttons did nothing for every league, with no message. They work
  again. An error in a click like this one is now also written to `errors.log` in Mod Studio's
  settings folder (`%APPDATA%\FL26ModStudio`), so a report can carry it. (Thanks vmican)
- **No kit from Mod Studio in the game with a kits.lua that reads content\kit-server (B165).** Mod
  Studio took for granted that `common\kits.lua` reads `content\kits`, as SPFL26's own does. One that
  reads `content\kit-server` saw none of the kits Build, Switch on or the Kits page wrote: only the
  few lines already in kit-server reached the game. Mod Studio now reads the folder from the Kit and
  Scoreboard Server module itself. (Thanks NedimMM)

## Also new

- **Import crests: one league's clubs only (B144).** A folder of Colombian crests gave "Leones FC" to
  the Leones FC of Ecuador and "Tigres FC" to Bolivia's. **Match to** now lists every league of the
  world too: pick one and only its clubs are matched. A folder named after a league of the world
  (`Torneo DIMAYOR II`) picks that league by itself. Thanks Xxspedd.
- **A short Ko-fi reminder at the first start of a new version.** Once per version, after the quick
  tour, with the link to the Ko-fi page: donating is never required, Not now closes it and it does not
  come back until the next version.
- **A Ko-fi button at the top, next to Credits**: it opens the Ko-fi page in the browser.
