# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.3.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

- **Club World Cup of 32: winning the final now counts as the title.** The final was played and
  won, but the Master League history had no Club World Cup and the match ended without a
  ceremony. A new module, `fl26cwctitle`, comes with the Club World Cup option: the final now
  gives the title (checked in the game), and when a Club World Cup trophy scene is installed in
  Sider's cinematics, the trophy ceremony is played after it (checked in the game). Without such
  a scene the final ends with the game's usual celebration, as before. `trophy=0` / `trophy=1`
  on the world file's `cwc32` line turns the ceremony part off or on whatever is installed.
