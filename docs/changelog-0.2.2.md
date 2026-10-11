# What's new in Mod Studio 0.2.2

DRAFT -- not released. Every line below still needs its in-game check before the release.

## Small additions (asked for on Discord)

- League: a name field for the super cup, beside the national cup's and the league cup's
  (empty = the league's name + Super Cup).

- Closing Mod Studio with recipe changes not saved asks whether to save them (they were lost
  without a word; a recipe never saved goes to the copy the next start opens).

## Fixes

- **The calendar stops on a day and shows nothing** (national team days, awards and other
  events, GitHub #70, #132). Since 0.2.0 a calendar day holds more matches, and one place in
  the game that reads the day's events still looked at the old spot. `fl26caps.lua` now
  moves that read too (sider.log says `3504 patches`). National team matches that were
  skipped are expected to come back with it.
- **A January-December league in a country with no league of the game never started**
  (Norway and Sweden in the modpack, GitHub #124). Nothing closed its season at New Year, so
  in February it still counted as playing. It now closes with the game's New Year leagues.
- **Copa Sudamericana and Libertadores could share a club** in a first season while the next
  club in the league got neither (GitHub #132: Alianza Lima). Both cups now count a league's
  places the same way, and a club with a Libertadores place does not take a Sudamericana one.
- **Faces linked to new players by id stayed linked** after a change elsewhere in the world
  (a league added above, GitHub #126). Build keeps each player's id from the last Build when
  his name is the same.
- Kits made for new clubs and package kits and scoreboards now go where your Kit Server and
  Scoreboard Server read them, also on a clean SPFL26 (GitHub #129).
- Switch on puts `fl26caps` before the other modules of ours in sider.ini when it was further
  down (then it refused the game and sider.log said MISMATCH).
- The country cup draw (cup_draw random or seeded) rewrites only the clubs the cup's entry
  list holds (GitHub #122).
- League > Division lists two clubs beside each of the game's leagues, so a slot a patch gave
  another country (Greece in Smoke Patch's "Switzerland") can be told apart.
- With a league order (A-Z or your own) the "Other European / Latin American / Asian" groups
  stay after the last country of their continent instead of going after every country.
- Import kits replaces a map line whose kit folder is missing, instead of keeping it.
- Players: the "a new club keeps at least 18 players" check counts the players who joined it.
- A package whose NewLife club list has gaps no longer stops Check the plan.
- A player joined from another database that the game does not have is skipped.
- Check the plan says so when more than 8 Libertadores group stage places are listed
  (the game only leaves the new leagues 8, GitHub #127).
- League cup hints say late August to mid-March, the dates since 0.2.0.
- Home: Switch world... shows the worlds.
- sider.log says why a qualifying round is not played in a season (GitHub #128, log only).
