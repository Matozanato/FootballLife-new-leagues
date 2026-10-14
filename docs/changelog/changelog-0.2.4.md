# What's new in Mod Studio 0.2.4

0.2.4 is a bug-fix update (in progress). Nothing new to learn: Install the modules, Build
once, and your 0.2.2 career keeps working.

## Fixed

- **Cup mode: a saved cup (World Cup, Euro...) could not be loaded.** With the modules the
  load ran for a minute or two and the game closed; without them the same save loaded in
  seconds. The raised club limits had moved the game's tables but not three places where a
  cup save puts its teams, coaches and regulations back on load, so the live season came back
  without teams. Checked in the game: a World Cup save loads in seconds and continues at the
  cup menu. Thanks Vicentico.
- **League Two (and any league with nothing below it): the promotion arrows stuck to the first
  rows of the standings when scrolling.** Thanks Vicentico.
- **Super cups of the game's own leagues** (New leagues > cups of the game's countries) came
  out as a 16-club knockout; they are now a two-club super cup (champion v cup winner), and in
  a February-December country it is played at the end of January. Needs Build again. Thanks
  Vicentico.
- **Build stopped with "players of <club>: no player <n>"** on a recipe written with 0.2.1
  (30-man new clubs). The transfer of a player the club no longer has is skipped with a note in
  the log. Thanks diwwanmago.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) still applies. Your 0.2.2 / 0.2.3 career keeps
  working after this update; a cup saved before 0.2.4 loads too.
