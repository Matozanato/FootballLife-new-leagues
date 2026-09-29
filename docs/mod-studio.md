# FL26 Mod Studio — how it works

The user guide is [mod-studio-guide.md](mod-studio-guide.md) ([hrvatski](mod-studio-guide.hr.md),
[español](mod-studio-guide.es.md), [français](mod-studio-guide.fr.md)).
This page is for modders and developers: what the program does to the game folder, and the
league package format.

## What it touches

| Where | What |
|---|---|
| `SiderAddons\sider.ini` | `cpk.root` and `lua.module` lines (switched off by commenting, never deleted), and the settings some modules need. |
| `SiderAddons\livecpk\<folder>` | Content folders it installs; League Builder worlds (`_FL26...`). |
| `SiderAddons\modules` | Lua modules it installs; the League Builder's modules. |
| `SiderAddons\content\<server>` | Content server files and their map files. |
| `SiderAddons\ModStudio\` | `backups\` (a copy of every file before it is changed, one folder per day, with an index), `profiles\`, `installed.json` (what each installed mod added and replaced). |
| `%APPDATA%\FL26ModStudio` | The program's settings, the unpacked game tables, and the store of added league packages. |

The game's own files (`download\*.cpk`, the exe) are only read.

Updates (`updater.py`): the check reads the public repository's releases
(`api.github.com/repos/Matozanato/FootballLife-new-leagues/releases`, tags `modstudio-<version>`)
and nothing else is sent. The zip is checked against the sha256 GitHub lists for the asset and
against its size, unpacked to `%TEMP%`, and a batch file copies it over the program's folder once
the program has exited (both processes of the one-file .exe), then starts it again. It writes
`%TEMP%\FL26ModStudio-update.log`.

## Source

`tools/modstudio/`; the window is `app.py`, one file per page in `pages/`.

| File | Job |
|---|---|
| `siderini.py` | Reads and writes `sider.ini` keeping comments, blank lines and order. |
| `roots.py`, `modules.py` | Content folders and modules: what is in them, the known module order, settings a module needs. |
| `servers.py`, `mapfile.py` | The content servers: where their content and map files are, the columns of each map, a map file read and written as rows. |
| `installer.py` | Looks inside a mod, says what each part is, installs it, merges map files, records what it did so it can be removed. |
| `backups.py`, `profiles.py` | Restore points and profiles. |
| `checks.py` | The checks behind Overview and Diagnostics. |
| `updater.py` | Help → Check for updates: the newest `modstudio-<version>` release, download, checksum, the swap after the program exits. |
| `project.py` | The League Builder recipe. The build itself is `tools/leaguebuilder.py`. |
| `lbplayers.py`, `lbfaces.py`, `lbpackage.py` | Player changes, faces, league packages (`tools/`). |

## The world file: `SiderAddons\modules\fl26world.txt`

The League Builder's worlds are read by the Sider modules in its pack (`sider/` and
`sider/experimental/`, installed by Build → *0. Install the modules*). They learn which leagues
a world has from one plain text file, written at Build and copied to `modules\` by *Switch it
on*. A module that finds no file keeps its built-in list, so an install without the builder
behaves exactly as before.

```
# fl26world 1
world _FL26Example
league 11 cid=130 region=60 country=198 slot=3 tier=1 promote=0 demote=2 clubs=12 legs=3 name=First League
league 49 cid=131 region=60 country=198 slot=2 tier=2 above=11 promote=2 demote=0 clubs=16 legs=2 name=Second League
```

- `league <regulation id>` then `key=value` pairs; `name=` is last and takes the rest of the line.
- `slot` = Select Team slot (absent or 123 = none). `country` = Country.bin id (flag,
  Competition Info name). `above` = the league one division up (shipped or new).
  `promote` / `demote` = how many clubs go up from / down out of this league.
- `cup` = the country's domestic cup, written on a second division added under a shipped top
  flight that had none (Germany, Russia, ...). The game fills a country's cup from its first
  league and the league below it, so without this the new second division would take the cup
  over or join it. fl26chain keeps the cup to the top flight's clubs (issue #21). Build also
  writes it on the second division under a new country's top flight when the two together are
  more than a cup can take (44 clubs), so the cup keeps the top division alone.
- `cupall=1` (with `cup`): the shipped country's cup takes **both** divisions, the top one's
  clubs first (issue #32: the DFB-Pokal with a new 2. Bundesliga). Build writes it when the
  cup's calendar dates every round of that field and the field is at most 44 clubs, and raises
  the cup's bracket to that size in the world's tables; otherwise, or with `"cup_top_only": true`
  on the league in the recipe, the cup keeps the top flight's clubs only (plain `cup`).
- `nopool <team id> <team id> ...`: clubs the game already has that now play in a league of
  the world (the recipe's `game_clubs`), and the clubs that took their league places.
  fl26clubs.dll (`fl26_clubs_keep_out`) leaves them out of the Master League's *Other ...
  clubs* groups, so a club does not show twice.
- Unknown keys are ignored, so later versions can add fields without breaking older modules.
- A split league is one `league` line for the regular phase plus
  `split <total> regular=<id> groups=<id>,<id>`.
- `uefa <regulation> <position> <competition> <alt>`: one European place per line, in
  hand-out order. Without any, fl26swiss uses the DLL's own list (shipped leagues only).
  Competitions: 0 Champions League, 1 Europa League, 2 Conference League, 3 Libertadores,
  4 Libertadores qualifying, 5 AFC Champions League, and the four cups the game does not have:
  6 CAF Champions League, 7 CAF Confederation Cup, 8 AFC Champions League Two, 9 Copa
  Sudamericana (only places of the recipe's leagues go to 6-9). A list replaces the DLL's, so Build writes
  the shipped leagues' places first (`fl26world.SHIPPED_ACCESS`, a copy of fl26swiss.c's
  ACCESS) and then the places of the recipe's leagues (their `europe` key, set in the League
  dialog). Each competition takes 36 clubs; places past the 36th get nothing.
- Libertadores qualifying (4) places of new leagues: the round (regulation 8) is set on day 0
  with shipped clubs only, none of them from the pool slot 73 that the other places replace. So
  fl26swiss.c `cont_standins` gives each of our places the place of a shipped club: the last
  listed one of the country with the most clubs in the round, at most half the round; the
  round's ties (1032 ... 4104) follow the same map. sider.log: `... in place of <team> (slot ...)`.
- `season <region> <type>`: the region's season type, in front of the game's own table
  (0x141576140: 0 August-May, 1 January-December; a region it has not got plays August-May).
  fl26join.dll hooks that function (`fl26_join_season_types`, fl26join.log "season types from
  the world file"); fl26joindll.lua and fl26swiss.lua take the leagues of a type-1 region for
  calendar-year ones (registration, New Year promotion, round dates 45..333). Build writes
  `season <region> 1` for a new country whose top division has *February to December*
  (recipe `"season": "calendar"`). `season 28 0` (recipe `saudi_august`, not in the UI) is
  EXPERIMENTAL: the Saudi Pro League 162 then plays August-May, and its cups 164/165 get
  `dates ... like=` lines of the Belgian ones; fl26swiss spreads 162's rounds over a European
  season (`fl26_swiss_european`). Not tested in game.
- `uecl <id> <id> ...`: the Conference League's 36 entrants at the start, written when the
  recipe's `uecl` is on (the default). Build then reshapes the Champions League and the Europa
  League to a league phase of 36 (mkreshape), clones FL_UECL as competition 174 with
  regulations 186 (league phase, group 1210) and 187 (knockout) (`mkuecl.build`), and adds the
  play-offs 188/189 (`mkeuropo.build`). fl26swiss.lua does not read this line yet; it uses
  its own UECL list, the same clubs on the game's own tables.
- The league-phase draw (all three competitions) keeps associations apart, as UEFA does: no
  club meets a club of its own country, and none meets more than two of any one other country.
  A club's country is its league's: the `country=` of a league line of the world file for a
  league of ours (fl26swiss.lua hands the DLL `slot, country` pairs, `fl26_swiss_nations`),
  else the game's own. See [league-phase-swiss-decode.md](league-phase-swiss-decode.md),
  section 13.

- `ccup <groups regulation> ko=<knockout regulation> groups=<n> entry=<reg>:<position>,... name=<text>`:
  a continental cup of the four above, built by `tools/mkccup.py` into the world's tables and
  run by fl26swiss.dll: filled at the end of August from the leagues' tables (a club already in
  another of these cups, or in the game's own Libertadores (regulation 9), its qualifying round
  (8) or the AFC Champions League (15), is skipped), drawn into groups of four, then a knockout
  of 2 x groups clubs. `groups=0` is a straight knockout (then both regulations are the same).
  Build sizes each cup to 32, 16, 8 or 4 clubs: the recipe's places first, and for AFC Champions
  League Two and the Copa Sudamericana the shipped leagues of that continent fill the rest. A
  CAF cup with fewer than 4 places (the game has no African leagues to fill it from) first takes
  the best places of the next CAF cup (the CAF Champions League takes all four of two plus two),
  then the next positions of its own leagues that no place claims; the plan says so in a NOTE.

A new country's own cup is not a line: with `"cup": true` on a top division (and optionally
`"supercup": true`) Build copies a shipped cup (`tools/mkcup.py --like`) into the country's
region, and a super cup from the Belgian one. The game fills a country's cup with its top
division and the one below it. A shipped cup of exactly that many clubs is copied when there is
one (12, 16, 18, 20 for a top division alone; 36, 40, 44 with the one below); any other field up
to 44 clubs gets the English cup, whose calendar dates every round of a field of 9 to 64 clubs,
and the game's own byes handle a field that is not a power of two. Past 44 the cup keeps the top
division alone (`cup` on the second division's line). `"club_coaches"` in a league gives its new
clubs' managers names (empty = `FL Mnnnn`).

Other recipe keys of Mod Studio 0.1.4 (the full list is the docstring of `tools/leaguebuilder.py`
and `tools/lbplayers.py`):

- `"game_clubs": [{"at": <place>, "id": <team id>, "swap": ...}]` on a league: clubs the game
  already has in places of the new league. A club that plays anywhere in the game needs `swap`,
  the club that takes all its places there (a team id of a club of the game in no competition,
  or `{"name": ...}` for a new club), so no competition of the game changes its number of clubs.
  National teams, the special teams and squads under 18 are refused. Written to the world file
  as `nopool`.
- `"club_ids": [<id or "">, ...]` on a league: a new club's team id instead of the next free
  one, above the game's clubs and at most 81919 (the block whose kits are named
  `<id-65536>_ACL_`).
- `"season": "calendar"` on a new country's top division: `season <region> 1` (above).
- `"formation"` / `"club_formations"` on a league: the new clubs' formation, copied from a club
  of the game with that shape (`tools/mktactics.py`).
- Under `"players"`, per club: `"join"` (players who come to the club and keep their record: a
  transfer to a club, a call-up to a national team), `"id"` (a new player's own id, up to
  399999) and `"coach_portrait"` (a picture Build writes to
  `common/render/symbol/coach/coach_<coach id>.png`, 256 x 256).
- A recipe with no leagues and `"uecl"`: the new European format alone, the game's leagues and
  clubs as they are (Build page, *Only the new European cups...*).

Overview and Diagnostics warn when the world that is on has new leagues but no `uefa` line
names one of them, and when its Conference League is on but regulations 186/187/1210 are
missing from its tables.

The builder also keeps a copy in the world folder (`livecpk\<world>\fl26world.txt`).

## New African and Asian leagues: continent (research, not fixed yet)

Reported for an Egyptian league (0.1.3): the Master League board asks for the Copa
Libertadores, League Info says "South American based leagues" and shows no CAF cups, and
Select Team lists it after the Asian leagues. What the exe shows, read statically:

- The confederation code (Competition.bin +6, low three bits: 2 UEFA, 3 AFC, 4 CONMEBOL,
  5 CAF, 6 CONCACAF, 7 OFC) becomes a runtime code through 0x14297d270 (UEFA 1, AFC 2,
  CONCACAF 3, CONMEBOL 5, CAF 6, OFC 0; bits 25..28 of the row's +0x300).
- 0x141511070 turns a regulation into a continent (it follows +0x76 first): UEFA 0 Europe,
  CONMEBOL 1 South America, AFC/OFC 2 Asia, CONCACAF 5, CAF 4, anything else 6. It has 19
  callers, and most of them only know 0, 1 and 2: 0x14154f4f0 (the month window) is always
  false for 4; 0x14133ebb1 maps 0/1/2 to regulations 4/10/16 and nothing else; the Master
  League function at 0x141fc5890 gives 0/1/2 the labels 0x1c/0x1d/0x1e and every other
  continent none. An African league therefore reaches code paths the shipped game never takes.
- The season-end filter 0x141365c50 runs only for UEFA, AFC and CONMEBOL (callers
  0x1413663b8, 0x141366178, 0x141366508), so a CAF-, CONCACAF- or OFC-coded league with a
  league below it would promote nobody. This is why the builder keeps the UEFA code for such
  a top division (`build`: "except a league of our own regions ... with a league below it").
  That league then reads as European to every caller above.
- Select Team slots 28..40 are the South American block of the parameter table. Regulation 60,
  the third id the builder hands out, sits on slot 40 (fl26world.DEFAULT_SLOT). A league there
  is a candidate for the South American wording. This is not confirmed: no reader of the slot's
  kind was found.
- The CAF cups' League Info icons already follow the world's `conf=` (fl26catlist ICONS
  stub). The cups show only when they are built, which needs 4 places or more.
- Select Team: the game has no African block. The `order` line puts CAF countries in a block of
  their own after Asia. That is by design.

To look at in game, on a world with an Egyptian league on regulation 60 and one on 173
(slot 43):
- the board objective and League Info title of both;
- sider.log `fl26catlist: League Info icons ... 60=6`.

If only the one on slot 40 is South American, the fix is to hand African and Asian countries
ids outside slots 28..40 in plan(). If both are, the text comes from the continent. The fix is
then a continent override for our regions in 0x141511070, or the real code for the top division
together with a hook on the filter's compare at 0x141365d0e.

## League packages (`.fl26pack`)

A package is a zip with:

```
manifest.json    {"format": "fl26pack", "format_version": 1, "name", "author", "version",
                  "description", "made_with", "leagues": [{"name", "country", "clubs"}],
                  "clubs", "faces", "edits": {"leagues", "clubs"}, "player_changes"}
recipe.json      the leagues as a recipe has them, the player changes of their clubs, and
                 optionally changes to the game's own leagues, clubs and players
assets/...       the logos, crests and country flags used
faces/<n>/...    faces given to players (#Win, sourceimages, portrait.dds)
```

- Paths in `recipe.json` are relative to the package.
- A package carries **no ids**. Club, player and league ids depend on what else a person's game
  already has, so they are given out when that person builds. That is what lets two packages
  and a person's own leagues live side by side.
- Players of a new club are addressed as `<league>/<k>` (the club's place in its league) and
  by their place in the squad; players of the game's clubs by their game id.
- Adding a package records under `"packs"` in the recipe what came from it, and what a
  changed game club looked like before, so removing it takes out exactly that.

## Faces

A face is `#Win\face.fpk` (+ `face.fpkd`), `sourceimages\#windx11\*.ftex` and optionally a
portrait `.dds`. The id of the player the face was made for appears only inside `face.fpk`, as
the folder of its textures: `/Assets/pes16/model/character/face/real/<id>/sourceimages/`.

At build the face is copied to `Asset\model\character\face\real\<player>\` of the world and that
path is rewritten to the new place of the textures, **with the same length**, so nothing else in
the file moves:

- if the new player id has as many digits as the old one, the textures go under the new id;
- otherwise they go under a folder `m` + a number in base 36, padded to the old id's length
  (`m0000`, `m0001` ...). No player id has a letter, so these never clash with a real face.

The portrait goes to `common\render\symbol\player\<player>.dds`.
