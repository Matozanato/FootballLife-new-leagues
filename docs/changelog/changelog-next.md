# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.2.4 (2026-10-18). The version number and the date come when
it is released; until then this page only collects what is done and tested.

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

- **Deleted worlds kept taking the disk (B131).** Delete world moves the world into a copy under
  Restore points so it can come back, and that copy kept its gigabytes with no way to free them from
  Mod Studio. Restore points now has Delete this copy for good... for a deleted or copied world
  (it asks first and says how much it frees), and Delete world says how big the world is and where to
  free that space. (Thanks Vicentico)
