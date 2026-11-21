# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.4.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

## New

- **Club World Cup of 32: winning the final now counts as the title.** The final was played and
  won, but the Master League history had no Club World Cup and the match ended without a
  ceremony. A new module, `fl26cwctitle`, comes with the Club World Cup option: the final now
  gives the title (checked in the game), and when a Club World Cup trophy scene is installed in
  Sider's cinematics, the trophy ceremony is played after it (checked in the game). Without such
  a scene the final ends with the game's usual celebration, as before. `trophy=0` / `trophy=1`
  on the world file's `cwc32` line turns the ceremony part off or on whatever is installed.

- **Cups > International, and an OFC place in the Club World Cup of 32.** The Club World Cup moved to
  a new tab of the Cups page, International, which always lists the Intercontinental Cup (the game's
  four-club Club World Cup). *Add Club World Cup* adds the cup of 32. Its places are now 12 UEFA,
  6 CONMEBOL, 5 AFC, 4 CAF, 4 CONCACAF and 1 OFC: the best OFC club of the OFC ranking (with none
  in the ranking, the place goes to the AFC). The Master League and League Mode rankings get an
  OFC screen. FL 2027: the ranking module reads the day and the regulation table where FL 2027's
  limits put them, and Competition Info by confederation lists the Intercontinental next to the
  Club World Cup. Build the world again and install the modules. Not checked in the game yet.
