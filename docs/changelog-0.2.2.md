# What's new in Mod Studio 0.2.2

DRAFT -- not released. Every line below still needs its in-game check before the release.

## Small additions (asked for on Discord)

- League: a name field for the super cup, beside the national cup's and the league cup's
  (empty = the league's name + Super Cup).

- Closing Mod Studio with recipe changes not saved asks whether to save them (they were lost
  without a word; a recipe never saved goes to the copy the next start opens).

- The clubs of a new league, and of a league of the game a new club joins, are listed A-Z in
  Select Team and Edit (FC, AC, SC ... left out, so FC Augsburg sits under A). The game's own
  leagues keep their order.
- Leagues > More > Competition IDs: every league and cup with its competition id and
  regulation ids, from the world switched on, with a button that copies the list.
- More > World name and recipe: "Faces from the regen face pack for new players". Off keeps
  the look the game gives new players, or the one set in the game's Edit mode.

## Easier to use (from the poll)

- File > Changes in this world: everything your recipe changes in one list (clubs of the
  game, leagues, competitions, swaps, squads), and Undo for the lines you pick.
- The status bar says whether your changes are saved; click it, or Ctrl+S, to save. Edits
  of clubs, players and leagues count straight away, there is no Apply to press.
- Build > New clubs: the two kit options say which is which. "Kits made in the clubs'
  colours" comes first; "Plain kits to change in Edit mode" is the alternative and greys the
  first out, since Kit Server does not dress the clubs then.

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
- **Kit Server found no kit for clubs another tool dressed** (Kit Studio, clubs added with
  another editor, Discord). Build's own UniformParameter.bin hid theirs; Build now keeps the
  entries of the other copies Sider serves, and never replaces a kit another mod gave a club.
  A club of the database with no kit at all (added by another editor) gets one lent too.
- **A league played the day after a cup match** (Chile D2 the day after a Copa Chile
  quarter-final, Discord). Rounds kept clear of our own cups and the European days only; Build
  now also hands over the dates of every cup of the league's country, the game's own cups
  too, and the rounds keep at least a day clear of them, in the leagues of the game as well.
- **A renamed league of the game gave its name to a new league** that took its place in the
  world (a Série C came out "Campeonato Carioca", Discord). The old rename now stays with the
  game's league.
- **Competition Info showed a generic flag for Asian and African countries.** Build looked for
  their flag under the wrong name (the game writes Iraq as flag_012). Your own flag for such a
  country now also replaces the game's.
- **The club you manage could lose its Libertadores qualifying place** to a club of a new
  league taking a place there (Discord). Your club is never the one that gives way now.
- New players of a very big world (more than about 4000 player ranges, 80+ leagues) all get
  their regen face; the last clubs' players kept the default look.
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
- A super cup added to a league of the game (Supercopa de Chile, Supercopa Rei) shows in
  League Info beside the country's other cups. It is built as a domestic cup now; a career
  started before keeps the old cup, which still plays, only without the icon.
- League cup hints say late August to mid-March, the dates since 0.2.0.
- Home: Switch world... shows the worlds.
- sider.log says why a qualifying round is not played in a season (GitHub #128, log only).
