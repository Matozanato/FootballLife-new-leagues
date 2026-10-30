# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.2.5.1. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

- **A Documents folder named in other letters, and saves under another number (B296).** With
  Documents in letters outside the system's code page (Georgian, `C:\Users\...\დოკუმენტები`),
  Edit mode could not keep the changes made to clubs past the game's 750 (`save: cannot write
  ...\???\...` in sider.log), and the final tables kept for Europe were not written either. The
  modules now write in any folder name. They and Mod Studio also look for the saves where the
  game really keeps them: the number in `sys.ini` (SteamID, 2026), or, when the game saves under
  another one (`...\0\save`), that folder. Mod Studio also finds a Documents folder moved to
  OneDrive or another drive. (Thanks GiorgiM)
- **Small clubs of the game buying stars for 70M (B298).** A club of the game that is in none of the
  game's leagues (Zalgiris, HJK, RFS and others in the Europe pack) has no transfer money and no
  followers in the game's tables. Put into a league, it counted as a top club and was paid about
  EUR 250M a season for TV, so it bought Endrick and Estevao. Build now gives these clubs money
  and followers by squad and division, as it does for new clubs. A club of the game with money
  of its own keeps it. Build your world again and start a new Master League. (Thanks vanni11)

## Also new
