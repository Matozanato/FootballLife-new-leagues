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
