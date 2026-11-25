# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.4.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

- **Club World Cup of 32: no more national-team matches in the middle of the cup.** The cup was
  always played on the same June days, and the June international window fell among them: in
  Become a Legend a player called up had a national-team match between two Club World Cup rounds
  (in the Master League the same happened to a manager who also runs a national team). The cup now
  reads the national-team days of the year, the same days the leagues already keep clear (B254),
  and moves its rounds clear of them, between 2 and 29 June (the season turns on 1 July): the whole cup after or before
  the window when it fits, otherwise at least never on a national-team day. Only a new draw (late
  November) gets the new days; a cup already drawn keeps its days. Not checked in the game yet.

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

- **The Intercontinental's final has its title ceremony, and its semi-finals are one match.** With
  the cup of 32 on, the Intercontinental final ended with the game's generic celebration: the
  game's one Club World Cup trophy went to the cup of 32, and the Intercontinental had none. It now
  gets the Club World Cup trophy too, so its final has the ceremony the old cup had, and its final
  gives the Master League title the way the cup of 32's does. The calendar showed its semi-final as
  home and away with no opponent; its rounds are dated as one match each now. `trophy=0` on the
  `cwc32` line turns the ceremony off for both cups. Install the modules again; no new Build
  needed. Not checked in the game yet.

- **Club World Cup of 32 in Become a Legend.** The cup was played in Become a Legend careers too,
  but their confederation points were never saved with the career (the ranking module knew only
  Master League and League Mode saves), and the Become a Legend menu had no "Ranking CWC". The
  points now go with a Become a Legend save as with the others, and Become a Legend > Data gets the
  same Ranking submenu (UEFA, CONMEBOL, CONCACAF, AFC, CAF, OFC). Build the world again and
  install the modules. Not checked in the game yet.

- **Club World Cup of 32: no more three European clubs in a group in a first season.** A cup
  drawn in the first season of a career had no South American and no CONCACAF club: their
  continental cups start in February, so by the draw in November none of their clubs had ranking
  points, their ten places went to the next ten European clubs, and six groups had three UEFA
  clubs. A confederation without enough clubs in its ranking now takes its places from its best
  clubs in the game's world Club Ranking; only what is still missing goes to the best of the
  whole ranking. Install the modules again; it shows in the next
  draw. Not checked in the game yet.
