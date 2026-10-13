# What's new in Mod Studio 0.2.2

0.2.2 is the big fix update promised with 0.2.1, and it raises the limits: bigger worlds,
more leagues and more clubs.

## Read this first

- **Careers saved before 0.2.2 do not load** (the game stays on the loading screen). Start a
  new career after Build. Your recipe and your world carry over.
- Install the modules (Install page, or Build and install does it), then **Build** once: the
  new limits need the new modules and a world built with them.
- Not checked in the game yet: see the end of this page.
- **NewLife 1.5 and the FL26 Modpack come a little later**, each with its own post and its own
  list of changes. NewLife 1.5 brings this summer's transfers (about 10,000 players at a new
  club, about 3,300 new players) and ratings below 50 for the weakest leagues; the Modpack is
  our 0.2.2 test world (86 leagues, 1,294 new clubs, their kits and 3D faces) built on it, as
  one zip for Install mods. Mod Studio 0.2.2 works with NewLife 1.4.2 until then.

## Bigger worlds

- **Raised limits.** 2,400 clubs in a world (1,536 before), 3,400 coaches, 61,905 players
  (new clubs get 22-man squads), 255 competitions a season (127 before), 128 menu regions and
  250 Select Team slots, so a league past the game's free ids is still selectable and can
  start a career. Our test world plays 86 new leagues with 1,294 new clubs. New modules:
  `fl26appcap`, `fl26regs600`, `fl26slots250`, `fl26slot7`, `fl26regfast`, `fl26walk`,
  `fl26hdr255` (replaces `fl26hdr127`/`fl26hdr192`), `fl26reg128` (replaces `fl26reg64`).
  Build installs them. **Careers saved before 0.2.2 do not load**: the game stays on the
  loading screen with no message and has to be closed (Task Manager). Start a new career after
  Build, and keep your old Mod Studio folder to finish an old one. Your recipe and world carry
  over. A world now holds up to 97 new leagues (75 before):
  past the game's free ids a league takes a regulation id from 254 down to 197 (255 stays
  out, it means "no league" in places; 196 and below belong to split seasons and the European
  play-offs). The game's date stub knows ids up to 255, so 97 is this layout's ceiling; cups
  are not counted, they take ids above 255. Competition ids are the tighter budget: 121 for
  leagues and cups together (130-255 less the game's five).
- **A Build keeps the ids of leagues already built.** Adding a league in front of others,
  removing one or changing the order used to give every league after it new competition,
  regulation, region and club ids, so a Kit Server map, the scoreboard map and faces lost
  them. Now each league keeps its competition id, regulation id, region, club ids and its
  cups' ids from the last Build; only a new (or renamed) league gets new ones.
- **Faster Master League creation** with a club of a new league: `fl26regfast` drops two
  repeated searches of the regulation table, and `fl26walk` remembers your club and its league
  while the game walks the calendar (a Druga NL career sat 5-10 minutes on the loading screen).
- **Promotion arrows in the standings on every tier** with a league above it (the game drew
  them on the second tier only, and hid the down arrows while doing it).
- The end-of-season Promotion/Relegation screen lists the clubs promoted from the third tier
  or deeper too (the upper column of a Prva NL / Druga NL pair was empty: the game counted
  only a second-division club as promoted).
- The season's match table holds 65,000 matches (46,000 before), and players' looks
  (PlayerAppearance) 65,000 records instead of 30,024, so big databases keep every face.
- New leagues never get a competition id below 130 (those caused conflicts).
- **A NewLife league's clubs the game already has get the NewLife squad too.** Until now
  only the league's new clubs did, and a club of the game in it (Dinamo, Hajduk, Legia,
  Basel...) kept the game's own players, so a player NewLife had moved was still at his old
  club. Update my leagues to this version gives those squads again; Remove league takes
  them away. Bring the game's leagues to this season, done again on a recipe that lost the
  record of the first time, now takes the old squads away before giving the new ones (their
  players counted as taken, and most of the new squad "stayed").

## Small additions (asked for on Discord)

- Competition Info: the Champions League, Europa League and Conference League league phase is
  one table of 36 that scrolls, instead of four pages of nine (Return no longer covers row 9).
  Made by DavidBDJ.

- A February-December league (season "calendar") can have its national cup and super cup:
  the cup plays through the league's own year, the super cup opens it. Made by vmardonesdev
  (GitHub #139).

- **Export the world** takes the world's kits and scoreboards too (Kit Server and Scoreboard
  Server, with their map lines); before, the receiver got the world without its kits. Install
  mods puts the kits where the receiver's Kit Server reads them. A club wearing a kit from
  another pack (SPFL26's Other Europe, a modpack) takes a copy of it along.

- League: a name field for the super cup, beside the national cup's and the league cup's
  (empty = the league's name + Super Cup).

- Closing Mod Studio with recipe changes not saved asks whether to save them (they were lost
  without a word; a recipe never saved goes to the copy the next start opens).

- The clubs of a new league, and of a league of the game a new club joins, are listed A-Z in
  Select Team and Edit (FC, AC, SC ... left out, so FC Augsburg sits under A). The game's own
  leagues keep their order.
- Mod Studio in Português (Brasil) (Language menu).
- Players: the squad list can be dragged taller on a short window (the pitch under it held it
  still).
- Leagues > More > Competition IDs: every league and cup with its competition id and
  regulation ids, from the world switched on, with a button that copies the list.
- Build: "Faces from the regen face pack for new players". Off keeps
  the look the game gives new players, or the one set in the game's Edit mode.

## Easier to use (from the poll)

- **Competition Info: every European qualifying round has its own item** (2nd and 3rd
  qualifying round, play-off round), so you can open each and see who plays whom; before, all
  of them sat under one "Play-offs" item that only showed the current round. The February
  play-off for places 9-24 is named "Knockout round play-offs", "Round of 32" / "First knockout
  round" read "Round of 16", and the Conference League shows its knockouts as a list of ties
  like the Champions and Europa League.
- File > Changes in this world: everything your recipe changes in one list (clubs of the
  game, leagues, competitions, swaps, squads), and Undo for the lines you pick.
- The status bar says whether your changes are saved; click it, or Ctrl+S, to save. Edits
  of clubs, players and leagues count straight away, there is no Apply to press.
- Build > New clubs: the two kit options say which is which. "Kits made in the clubs'
  colours" comes first; "Plain kits to change in Edit mode" is the alternative and greys the
  first out, since Kit Server does not dress the clubs then.

## Fixes

- **20-40 minutes on the loading screen at the end of January** (the winter transfer deadline)
  in a big world. On that day the game rates every player's club against every league and
  asked the same competition question again for each of the 61,905 players. The new module
  `fl26compcache` keeps each answer for the length of one pass: on our test world day 30 now
  takes under a minute. Build installs it.
- **"Create Edit Data" went back to the menu and made no Edit save** in a big world (reported
  on Discord: three leagues of ours worked, the fourth did not). The first save puts every club
  in, and every club's manager with it, but the game's managers table has room for 1300 and our
  test world has 1976. The check the game runs before saving then finds clubs whose manager is
  missing and gives up. `fl26edit` now gives the managers table room for 4096 too; the managers
  past the game's 1299 go to `EDIT00000000.fl26x` with the clubs past 749 (sider.log:
  `fl26edit: save: 1955 / 1955 / 1955 clubs, 1976 managers ...`). A `.fl26x` written by 0.2.1
  still loads.
- **No Europa League round of 16 in the second season** (the play-off was played, then the
  competition ended). Around the play-off draw the game already opens the Europa League's next
  season, and from then on it shows the league phase table of that season, still empty, so the
  play-off winners had no one to meet. `fl26swiss` now takes the league phase table of the
  season that was played when the newest one is empty (sider.log says `the latest season's
  table has 0 rows; season 2026's table (36 rows) is used`).
- **The calendar stops on a day and shows nothing** (national team days, awards and other
  events, GitHub #70, #132). Since 0.2.0 a calendar day holds more matches, and one place in
  the game that reads the day's events still looked at the old spot. `fl26caps.lua` now
  moves that read too (sider.log says `3510 patches`; the last six sites were found by
  nissindiaz, GitHub #135). National team matches that were
  skipped are expected to come back with it.
- **A January-December league in a country with no league of the game never started**
  (Norway and Sweden in the modpack, GitHub #124). Nothing closed its season at New Year, so
  in February it still counted as playing. It now closes with the game's New Year leagues,
  and on the registration day a league whose old rounds have no match left starts its new
  season (the close kept those rounds, so the second season never came).
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
- **New clubs with no kit** although Build makes one in their colours (22 clubs in a big world:
  AFC clubs, Larissa, Huesca, Bari ...). A kit line of an older install whose folder is gone
  counted as "your own kit", so none was made. A line to a missing folder no longer counts: the
  made kit goes in and that line is switched off.
- Players: the "a new club keeps at least 18 players" check counts the players who joined it.
- Best eleven (and the line-up Build gives a new club) lets a player who can also play a
  place take it from a much weaker player registered there: he counts with 6 off, so Rice
  (CMF, can play DMF, 83) starts at DMF over a 62 youth DMF while a real DMF close to him keeps
  the place; a player stays for his own place when it would otherwise be left short. Before,
  the registered position always won, so a club's best midfielder sat on the bench behind
  its weakest.
- A package whose NewLife club list has gaps no longer stops Check the plan.
- A player joined from another database that the game does not have is skipped.
- Import players reads a Spanish or Portuguese foot column ("Pie", "Pierna", "Pé") and its
  values (Izquierda, Zurdo, Diestro, Esquerdo, Canhoto...); every player came out right-footed
  (Discord).
- Check the plan reports a Conference League world without its play-off (regulation 189).
- Check the plan says so when more than 8 Libertadores group stage places are listed
  (the game only leaves the new leagues 8, GitHub #127).
- A super cup added to a league of the game (Supercopa de Chile, Supercopa Rei) shows in
  League Info beside the country's other cups. It is built as a domestic cup now; a career
  started before keeps the old cup, which still plays, only without the icon.
- **Make a package stopped with "PermissionError: [WinError 5] Access denied"** on a
  `scoreboards\<n>` folder (GitHub #141): the game's scoreboard folders can be read-only, and
  the copy kept that. Folders now go in without it.
- Competition Info no longer lists "Knockout round play-offs" twice after the February
  play-off draw (the game's own item already opens that round).
- Competition Info in August: Play-offs stays grey until the play-off is drawn (it opened the
  3rd qualifying round under the Play-offs name), and the Champions League's League Phase stays
  grey until its draw (it opened an empty "Group A").
- **A club could be in two European competitions' August rounds** (Tirana in the Conference
  League qualifying and in the Champions League play-off) after the game was restarted during
  the qualifying: the play-offs were filled from a fresh draw that did not know which clubs the
  rounds already held. A round the game already plays now keeps its clubs, and none of them is
  placed again.
- League cup hints say late August to mid-March, the dates since 0.2.0.
- Home: Switch world... shows the worlds.
- sider.log says why a qualifying round is not played in a season (GitHub #128, log only).
- For forks: `patchset.py --calendar-ids N` builds the set for another calendar day size and
  prints the module constants that layout needs (nissindiaz, GitHub #136).
- Release tool (for forks): `mszip.py` now stops when `FL26_DIR` is not set or the package has
  no regen face pack, instead of printing a note and going on (`--untested`, `--no-faces` let a
  fork's own build through); lbpack finds the face pack from a worktree too.
- Install modules switches off old modules a shipped one replaced, when an old manual
  install still has them: `fl26nullguard3` (replaced by the guards bundle), `fl26hdr127`
  and `fl26hdr192` (by `fl26hdr255`), `fl26reg64` (by `fl26reg128`) and `fl26deep4` (by
  `fl26deeprank`). Each pair overlaps, the second one
  refused its bytes, and the check after Build called that "refused the game's exe".
- Edit mode team lists show the leagues on the new competition slots 124-249 too
  (`fl26editlist` stopped at 123, the old slot count).

## Not checked in the game yet

- The national cup and super cup of a February-December league (GitHub #139): its own tests
  pass, a career with one has not been played yet.
- The sider.log line that says why a qualifying round is not played (GitHub #128): in our test
  world every round is played, so the line never came.
- Export the world with kits: installed and removed again on a second Sider folder, not yet
  played on another PC.

## Known, for a later update

- The Copa Sudamericana still follows the European calendar (filled at the end of August,
  groups November-February) instead of South America's.
