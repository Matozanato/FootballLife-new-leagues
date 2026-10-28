# What's new in Mod Studio 0.2.4.2

0.2.4.2 (2026-10-21) is a quick fix for one bug of 0.2.4 and 0.2.4.1. Worlds and careers carry on as
they are: there is nothing to Build again.

**Update if you play the Europack (eu4) or a world of your own with many lower divisions.** If
promotion and relegation work in your world, 0.2.4.1 is fine.

## Fixed

- **No promotion or relegation below the second division in big worlds (B186).** The module that
  moves clubs between a second division and the one under it (and lower down: 3 <-> 4 ...) took at
  most 8 such pairs of leagues. The Europack eu4 has 10, so at the start of the game it switched
  itself off (`fl26chain: install FAILED (status 9)` in sider.log): the champions of the Primera
  Federación, Serie C, League One, 3. Liga, National League, French National and the other
  lower divisions stayed where they were, and nobody went down to them. It takes 32 pairs now, and a
  world with even more keeps the first 32 instead of losing them all. In a career already going, it
  works from the next season end; seasons already played stay as they were. Install mods (Home >
  Install now) puts the new module in. (Thanks Ibiss K.B. and Rosev)
