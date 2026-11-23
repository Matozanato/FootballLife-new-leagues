# The world file (`fl26world.txt`)

Build writes one plain-text file per world, `fl26world.txt`. It sits in the world's folder
(`livecpk\<world>\fl26world.txt`), and *Switch it on* copies it to `SiderAddons\modules\`.
That copy is the one the modules read at game start. None of the modules knows about recipes.
Everything the game has to do at runtime reaches it through this file, so it is the bridge
between Mod Studio and the modules.

The rules every reader follows:

- One fact per line. The first word is the line's kind. Lines whose kind a module does not
  know are skipped, and the same goes for keys it does not know. That is how newer
  versions add fields without breaking older modules.
- `#` lines are comments. The first line is `# fl26world 1` (`fl26world.FORMAT`).
- Ids are the game's own: regulation ids (`reg`), competition ids (`cid`), team ids,
  region ids and `Country.bin` ids.
- The modules read the copy in `modules\`. If you change the file by hand, *Switch it on*
  again or copy it there yourself. A module that finds no file keeps its built-in list.

Where it is written: `leaguebuilder.build()` collects the lines and calls
`fl26world.write_world()` once. Most kinds come from small functions in `leaguebuilder.py`,
listed in the table. `fl26world.py` can also write a file for a world that already exists, from its
tables (`python tools/fl26world.py --root <world>`), but it only knows `league`, `split`,
`uefa`, `uecl` and `qround`.

## Every line kind

| kind | example | written by | read by |
|---|---|---|---|
| `world` | `world _FL26Example` | `fl26world.write_world` | `fl26world.read_world` (Build's check, `modstudio/checks.py`) |
| `league` | `league 11 cid=130 region=29 country=191 conf=2 slot=28 tier=1 promote=0 demote=2 clubs=10 legs=2 kickoff=25 name=...` | `fl26world.from_tables` + `build()` (keys below) | fl26joindll, fl26chain, fl26comptab, fl26editlist, fl26catlist, fl26clubs, fl26slotnames, fl26seasonend, fl26swiss |
| `split` | `split 109 regular=191 groups=192,193` (`carry=0` for Apertura/Clausura) | `fl26world.from_tables` (`mksplit` phases) | fl26joindll, fl26chain, fl26swiss |
| `uefa` | `uefa 4 0 0 17` | `fl26world.uefa_places` | fl26swiss (access list), fl26catlist |
| `qround` | `qround 10 2 197` | `leaguebuilder.europe` (`mkeuropo.qualifying`) | fl26swiss (`fl26_swiss_qrounds`) |
| `uecl` | `uecl <team id> ...` | `leaguebuilder.europe` (`mkuecl`) | not read yet: fl26swiss uses its own list |
| `ccup` | `ccup 226 ko=226 groups=0 entry=17:1,... fill=253 national=1 days=... name=...` | `leaguebuilder.continental` (via `mkccup`) | fl26swiss (`fl26_swiss_ccup`, `_ccup_opts`, `_ccup_alt`; `comp=<n>` of a continental cup: `_ccup_zone`, the standings' zone strip) |
| `gsplit` | `gsplit 133 regular=134 groups=135,136` | `fl26world.from_tables` (a league with `splittotal=`: the shipped split season's top and bottom group, formats 13 and 14) | fl26swiss (`fl26_swiss_gsplits`; B425: a national cup's place named on the regular phase is the final table's, and the cup waits for the groups' last round). fl26chain reads the place from the total (`splittotal=`), without this line |
| `lpre` | `lpre 227 cup=226 fill=226 days=246,249 entry=...` | `leaguebuilder.continental` (`mkeuropo.prerounds`) | fl26swiss (`fl26_swiss_lpre`) |
| `lpre ... single=1` | `lpre 705 cup=616 fill=226 days=232,232 entry=... single=1 alt=...` | a continental cup's preliminary round: `leaguebuilder.cup_prelim_lines` (`prepare_cup_prelims`); the Sudamericana's first stage: `sudamericana_first_line` | fl26swiss (`fl26_swiss_lpre`, `_lpre_single`, `_lpre_alt`) |
| `confed` | `confed <flag>:<code>,...` | `leaguebuilder.confed_line` | fl26swiss (`fl26_swiss_confed`) |
| `seasonsum` | `seasonsum 119 parts=168,169` | `leaguebuilder.seasonsum_lines` (a `game_europe` place of Colombia's or the MLS's whole season) | fl26swiss (`fl26_swiss_seasonsum`: the halves' tables added together, `ssum_keep`) |
| `dates` | `dates 203 like=23` | `leaguebuilder.dates_lines` | fl26swiss (`fl26_swiss_datelike`) |
| `gsuper` | `gsuper 255 league=67 cup=68 region=18 conf=4` | `leaguebuilder.gsuper_lines` | fl26joindll -> fl26join.dll (`fl26_join_builder_extra`, `_builder_conf`), fl26swiss (`fl26_swiss_calendar_supercups`) |
| `lphase` | `lphase 49 300 1` | `tools/argentina` | fl26swiss.lua (`fl26_swiss_lphase`): an item of a competition's Competition Info menu ([argentina.md](argentina.md)) |
| `lpname` | `lpname 300 Final do 1º acesso` | `tools/argentina` | fl26swiss.lua: the item's or a round's name |
| `sline` | `sline fl26_swiss_tcup 300 ...` | `tools/argentina` | fl26swiss.lua: calls that export of fl26swiss.dll with the numbers |
| `jline` | `jline fl26_join_regional ...` | `tools/argentina` | fl26joindll.lua: calls that export of fl26join.dll with the numbers |
| `confsub` | `confsub slots=49:1,40:1` | `tools/argentina` | fl26confgroups.lua (`fl26_confgroups_fold`): Select Team folders inside a country |
| `confsubnames` | `confsubnames 1:0:0:Primera Nacional` | `tools/argentina` | fl26confgroups.lua (`fl26_confgroups_fname`) |
| `season` | `season 39 1` | `leaguebuilder.season_lines` | fl26joindll -> fl26join.dll (`fl26_join_season_types`), fl26swiss |
| `july` | `july 49 205` | `leaguebuilder.july_lines` | fl26swiss (`fl26_swiss_july`) |
| `rcal` | `rcal 76 211 142 354 21 96 16` | `leaguebuilder.rcal_lines` (`tools/realcal.py`) | fl26swiss (`fl26_swiss_rcal`) |
| `first` | `first 0 <team id> ...` | `leaguebuilder.first_lines` | fl26swiss (`fl26_swiss_first`) |
| `order` | `order 1,26,29,...` | `leaguebuilder.order_lines` | fl26catlist |
| `kickorder` | `kickorder <reg>:<place>,...` | `leaguebuilder.kickorder_lines` | fl26comptab |
| `nopool` | `nopool <team id> ...` | `build()` (game clubs moved into our leagues) | fl26clubs -> fl26clubs.dll (`fl26_clubs_keep_out`) |
| `fans` | `fans <class 0-9> <percent> <team id> ...` | `leaguebuilder.club_money` (by squad strength and division) | fl26clubs -> fl26clubs.dll (`fl26_clubs_fans`) |
| `fansx` | `fansx <share of 10,000> <team id> ...` (FL 2027; the club also has a `fans` line, whose percent an older module reads) | `leaguebuilder.club_money`, a recipe's `club_money` `share` | fl26clubs -> fl26clubs.dll (`fl26_clubs_fans2`): a finer followers share (base down to 100) and the club's broadcasting fee and sponsors by it |
| `newfaces`, `newfaces3d` | `newfaces 179673-179679 179681` | `lbplayers.new_face_lines` | fl26regen |
| `faceapp` | `faceapp 179700:36912` | `lbplayers.face_app_lines` | fl26regen (`fl26_regen_copy`) |
| `cupdraw` | `cupdraw seeded` (or `cupdraw <reg> random`) | `build()` from the recipe's `cup_draw` | fl26swiss (`fl26_swiss_cupdraw`) |
| `gset` | `gset 0 up=82:4 low=11:1:82,49:1:82,60:2:82` | `leaguebuilder.group_world_lines` (`fl26world.group_lines`) | fl26chain (`fl26_chain_gsets`) |
| `ghome` | `ghome 49 <team id>,...` | `leaguebuilder.group_world_lines` | fl26chain (`fl26_chain_ghomes`) |
| `poff` | `poff 255 up=82 low=60 hold=60:2 entry=60:2,60:5,60:3,60:4` | `leaguebuilder.poff_lines` | fl26chain (`fl26_chain_playoffs`) |

## `league` keys

`league <regulation id>`, then `key=value` pairs. `name=` is always last and takes the rest of
the line. The keys `fl26world.KEYS` knows are:

| key | meaning | used by |
|---|---|---|
| `cid` | competition id | most readers |
| `region` | region (country) id, 29..63 for a new country | fl26joindll, fl26swiss, fl26catlist |
| `country` | `Country.bin` id: flag, Competition Info name, league-phase draw nation | fl26comptab, fl26catlist, fl26swiss |
| `conf` | the country's confederation (2 UEFA, 3 AFC, 4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC) | fl26catlist (League Info icons), fl26swiss |
| `slot` | Select Team slot of the regulation id (`fl26world.DEFAULT_SLOT`); absent or 123 = none | fl26comptab, fl26editlist, fl26clubs, fl26slotnames |
| `tier` | division (1 = top) | fl26chain, fl26joindll |
| `above` | the league one division up (ours or the game's) | fl26chain, fl26seasonend |
| `promote` / `demote` | clubs going up out of / down out of this league | fl26chain |
| `clubs`, `legs` | league size and how often clubs meet | fl26swiss (calendar) |
| `cup` | the country cup this line governs (see below) | fl26chain, fl26swiss |
| `cupall`, `cuptop`, `cuplow`, `cupn` | the cup takes both divisions / top division / lower division / at most n clubs (#32, #74) | fl26chain |
| `scup` | the country's super cup (#29). On a top division's line in a February-December region it is also the league's own super cup, which fl26joindll adds to the New Year season and fl26swiss fills with this league's champion v the `cup=` winner; on a division's line (`above=`) only fl26chain reads it | fl26chain, fl26joindll, fl26swiss |
| `exhibition` | 1 = Kick Off only, never registered in a season | fl26joindll, fl26seasonend |
| `kickoff` | the slot this league follows in the Kick Off / Edit lists: the league before it in its country (by division, then recipe order), the first one its league above or its continent | fl26comptab |
| `group` | the `gset` this league is a group of (GitHub #98): fl26chain makes no pair of it, fl26comptab gives a league of the game above the groups the sum of their `promote` as its `demote`, fl26joindll leaves it out of the New Year pairs | fl26chain, fl26comptab, fl26joindll |

[mod-studio.md](../mod-studio.md) explains the cup keys, `uefa`, `qround`, `ccup`, `lpre`,
`season`, `confed` and `kickorder` in detail, including the day numbers and the order places
are handed out in. This page doesn't repeat that.

## The kinds not covered in mod-studio.md

- **`dates <our cup> like=<shipped cup>`**: the game dates a cup's rounds by regulation id, with
  a switch over the shipped ids 2..175. A national cup or super cup of ours (id 176 and up) is
  drawn but never dated. fl26swiss asks the game for the dates of the cup it was copied from
  instead. Build also writes these lines for the cups of a game country moved to August-May
  (`game_seasons`).
- **`gsuper <reg> league=<reg> cup=<reg> region=<r> conf=<c>`**: a super cup Build gave a league
  of the game (`game_cups` with `super_cup`). A new league names its super cup on its own line
  (`scup=`); a game league has no line, so this one carries the same facts. In a
  February-December region (the shipped ones, or a `season <region> 1` line) fl26joindll adds
  the cup to the season the game builds at New Year, whose list holds only the shipped cups,
  and gives it the region's confederation (`conf`, the Competition.bin code). fl26swiss then
  fills it with the champion of `league` and the winner of `cup` (the league's runner-up when
  the champion won both); `cup=0` means the region has no cup and the game fills it. In an
  August-May region the line changes nothing. Without it (0.2.4 before this fix) the Supercopa
  de Chile and Rei were dated at the end of January but never entered a season.
- **`july <reg> <day>`**: some leagues kick off before the big ones. For such a league,
  fl26swiss brings its rounds before New Year forward by whole weeks, the first one onto that day.
  This applies from the second season on, because a new career starts on 4 August.
- **`rcal <reg> <first> <last> <break from> <break to> <days> <also> [eu]`** (0.2.0): the
  league's real season. Days of the year in 2026's frame (1 January = 0, Saturday 1 August =
  212); an August-May league counts across New Year (first 205, last 142). The break is two days
  inside it (0 0 for none). `days` and `also` are weekday bits, Monday 1 ... Saturday 32, Sunday
  64: the rounds go on `days`, on `also` at a small cost, on any other weekday only when the
  season is too short. `eu` 1 treats the league as one with European clubs; without it fl26swiss
  finds that from the `uefa` lines and the cup draws. fl26swiss dates the league from this line
  alone, every season: the first round on the first weekend, the last on the last, nothing in the
  break, the rounds spread evenly, never within a day of a European league-phase or knockout day
  (two days only when nothing else is left), of a national cup day, of its league cup's days or
  of a pre-season cup its clubs play; an August qualifying day closes only its own day. In a new
  career's first season a league that really starts in July starts on Saturday 8 August. A
  league with no `rcal` line keeps the old calendar (`july` and the spacing). `python
  tools/realcal.py <fl26world.txt> --write` adds the lines to a built world.
- **`first <0|1|2|3> <team id> ...`**: the clubs picked by hand (`europe_first`) for the
  Champions League (0), Europa League (1) and Conference League (2) league phases of a new
  career's first season. They go in first and the automatic choice fills the rest. From the
  second season on, league places decide. 3 is the AFC Champions League: in the career's first
  year (the state file's build date) and only while no place of ours gives a club, the list
  takes the places of the game's pool clubs (club slot 70), up to 32 (`cont_build`), in a
  world with no AFC place of its own too. When there are fewer pool clubs than clubs to put in,
  the rest take the places of the shipped league with the most clubs in the field (`cont_standins`,
  as for the Libertadores qualifying; B302).
- **`order <region>,...`**: the order of regions (countries) in the category lists, with our
  countries in it, following the recipe's `country_order` when it has one.
- **`newfaces <id or lo-hi> ...` / `newfaces3d ...`**: the world's own players, who get a face
  from the regen face pack by nationality (#52). A player with his own face folder is left out. A
  player with only his own portrait goes on a `newfaces3d` line: he gets the 3D face and keeps
  his picture.
- **`faceapp <player>:<face id> ...`**: the player wears the appearance of the face he was
  given (#102).
- **`gset <k> up=<id>:<n>,... low=<id>:<n>:<above id or 0>,...`** (GitHub #98): one set of
  groups of a division. `up` are the leagues above with the clubs each sends down, `low` the
  groups with the clubs each sends up and the league above it (where its promoted go first when
  there is room). The game follows one link down from a league and one up, so only one group of
  the set is linked in the tables; at the season's end fl26chain.dll takes the bottom `n` of
  every league above and the top `n` promotable clubs of every group from the standings, and
  writes the new lists of the whole set at once: each relegated club to its `ghome` group, else
  a group under the league it fell from, else the group with the most room; each promoted club
  to its group's league above when there is room. Every league keeps its size, no club is in two
  leagues; when the counts do not add up, a club is in none of the set's leagues or a standings
  table is short, nothing moves and sider.log says why (`group set ... nothing moved -- ...`).
- **`ghome <league> <team id>,...`**: the clubs a group was built with and the clubs above that
  the recipe gives it (`zone_clubs`). A club relegated into the set goes to its own group (a
  region) when it has one. Since 16.11.2026 fl26chain places the set's clubs together
  (`group_assign`): first as many relegated clubs at home as there are places, then guests (a
  club of the set in a group that is not its `ghome`) back home, then the fewest `gborder`
  moves; what does not fit goes by the old rules. Guests are read from the standings and the
  `ghome` lines each season's end, nothing is kept between seasons, so a save and a load change
  nothing. A set whose leagues above are the groups of another set is moved after that set
  whatever the order of the `gset` lines. sider.log names each club:
  `group set N: club <team> <from> -> <to> (home|guest: home X full|guest came home from X|
  border club: makes room in X|no home group in the set|promoted)`.
- **`gborder <league> <team id>:<group>,...`** (16.11.2026, recipe `zone_border`): clubs of the
  group that may move to the named neighbour group when a relegated club of the group's region
  needs the place, in order of preference. fl26chain.dll takes them with
  `fl26_chain_gborders`; a DLL without that export logs `rebuild it` and moves the groups
  without them. A world without `gborder` lines moves no club for another.
- **`poff <ko> up=<id> low=<id> [hold=<id>:<place>] entry=<id>:<place>,...`**: a promotion
  play-off, the knockout regulation `ko` (a `ccup` line of kind promo, filled after the last
  round). With `hold`, the club the counts put on that place swaps with the play-off's winner
  when the winner is not that club; without it (a tie of the league above's place and this
  league's) the winner ends in `up`, the loser in `low`. fl26chain.dll decides the winner from
  the match table (aggregate goals, then penalties) and needs every tie played and one club
  left; else the counts stand (`play-off ... no winner (...) -- the counts stand`).
- **`cupdraw seeded|random|off`** applies to every country cup. `cupdraw <reg> ...` applies to one cup.
  The recipe's `cup_draw` decides it, and the default is `seeded`. `test_cup_draw.py` checks it.

## Adding a line kind

1. Write it in `build()`, in the list handed to `fl26world.write_world` (or in a
   `..._lines(pl, ...)` helper next to the others).
2. Read it in the module: `line:match("^%s*<kind>%s+...")` in the Lua loader, then pass it
   to the DLL through an exported function. fl26swiss.lua's `read_world` is the model.
3. Log what the module took (`sider.log`). Diagnostics and `leaguebuilder.check()` read
   those lines to tell a person whether the world was taken.
4. Add a row to this table.
