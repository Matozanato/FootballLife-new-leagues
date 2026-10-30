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

## Also new
