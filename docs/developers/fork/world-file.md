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
| `ccup` | `ccup 226 ko=226 groups=0 entry=17:1,... fill=253 national=1 days=... name=...` | `leaguebuilder.continental` (via `mkccup`) | fl26swiss (`fl26_swiss_ccup`, `_ccup_opts`, `_ccup_alt`) |
| `lpre` | `lpre 227 cup=226 fill=226 days=246,249 entry=...` | `leaguebuilder.continental` (`mkeuropo.prerounds`) | fl26swiss (`fl26_swiss_lpre`) |
| `confed` | `confed <flag>:<code>,...` | `leaguebuilder.confed_line` | fl26swiss (`fl26_swiss_confed`) |
| `dates` | `dates 203 like=23` | `leaguebuilder.dates_lines` | fl26swiss (`fl26_swiss_datelike`) |
| `season` | `season 39 1` | `leaguebuilder.season_lines` | fl26joindll -> fl26join.dll (`fl26_join_season_types`), fl26swiss |
| `july` | `july 49 205` | `leaguebuilder.july_lines` | fl26swiss (`fl26_swiss_july`) |
| `rcal` | `rcal 76 211 142 354 21 96 16` | `leaguebuilder.rcal_lines` (`tools/realcal.py`) | fl26swiss (`fl26_swiss_rcal`) |
| `first` | `first 0 <team id> ...` | `leaguebuilder.first_lines` | fl26swiss (`fl26_swiss_first`) |
| `order` | `order 1,26,29,...` | `leaguebuilder.order_lines` | fl26catlist |
| `kickorder` | `kickorder <reg>:<place>,...` | `leaguebuilder.kickorder_lines` | fl26comptab |
| `nopool` | `nopool <team id> ...` | `build()` (game clubs moved into our leagues) | fl26clubs -> fl26clubs.dll (`fl26_clubs_keep_out`) |
| `fans` | `fans <class 0-9> <percent> <team id> ...` | `leaguebuilder.club_money` (by squad strength and division) | fl26clubs -> fl26clubs.dll (`fl26_clubs_fans`) |
| `newfaces`, `newfaces3d` | `newfaces 179673-179679 179681` | `lbplayers.new_face_lines` | fl26regen |
| `faceapp` | `faceapp 179700:36912` | `lbplayers.face_app_lines` | fl26regen (`fl26_regen_copy`) |
| `cupdraw` | `cupdraw seeded` (or `cupdraw <reg> random`) | `build()` from the recipe's `cup_draw` | fl26swiss (`fl26_swiss_cupdraw`) |

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
| `scup` | the country's super cup (#29) | fl26chain |
| `exhibition` | 1 = Kick Off only, never registered in a season | fl26joindll, fl26seasonend |
| `kickoff` | the slot this league follows in the Kick Off / Edit lists | fl26comptab |

[mod-studio.md](../mod-studio.md) explains the cup keys, `uefa`, `qround`, `ccup`, `lpre`,
`season`, `confed` and `kickorder` in detail, including the day numbers and the order places
are handed out in. This page doesn't repeat that.

## The kinds not covered in mod-studio.md

- **`dates <our cup> like=<shipped cup>`**: the game dates a cup's rounds by regulation id, with
  a switch over the shipped ids 2..175. A national cup or super cup of ours (id 176 and up) is
  drawn but never dated. fl26swiss asks the game for the dates of the cup it was copied from
  instead. Build also writes these lines for the cups of a game country moved to August-May
  (`game_seasons`).
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
- **`first <0|1|2> <team id> ...`**: the clubs picked by hand (`europe_first`) for the
  Champions League (0), Europa League (1) and Conference League (2) league phases of a new
  career's first season. They go in first and the automatic choice fills the rest. From the
  second season on, league places decide.
- **`order <region>,...`**: the order of regions (countries) in the category lists, with our
  countries in it, following the recipe's `country_order` when it has one.
- **`newfaces <id or lo-hi> ...` / `newfaces3d ...`**: the world's own players, who get a face
  from the regen face pack by nationality (#52). A player with his own face folder is left out. A
  player with only his own portrait goes on a `newfaces3d` line: he gets the 3D face and keeps
  his picture.
- **`faceapp <player>:<face id> ...`**: the player wears the appearance of the face he was
  given (#102).
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
