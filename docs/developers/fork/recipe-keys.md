# Recipe keys

A recipe is the JSON file Mod Studio edits and `leaguebuilder.py` builds from. It says what a
person would say ("a league of 16 clubs in Croatia, two legs, under the HNL") and nothing about
ids. Build gives out the ids each time, from what that person's game has.

The full reference is the docstring at the top of `tools/leaguebuilder.py` (league keys and
recipe-level keys) and of `tools/lbplayers.py` (the `players` block). This page lists every key
the code actually reads, checked against `plan()`, `build()`, `has_edits()`,
`recipe_from_plan()`, `newlife_tids()` and `modstudio/newlife.py`. It also shows which
world-file line each key ends up in (see [world-file.md](world-file.md)).

Rules that hold for every key:

- `plan()` validates. A bad value raises `BuildError` with a sentence a person can act on.
  Mod Studio shows that sentence as it is, so keep it plain.
- A key that is missing means the default. Never write a default into a recipe just to have it
  there. Older recipes must keep building, so a new key always needs a default that behaves
  as before.
- `has_edits()` decides whether a recipe without new leagues still changes anything. A new
  recipe-level key that Build reads must be added there too, or a recipe with only that key
  builds as "nothing to do".

## The recipe (top level)

| key | type | meaning | world file |
|---|---|---|---|
| `world` | text, starts with `_FL26` | the world's folder name in `livecpk` (`load_recipe` refuses others) | `world` |
| `leagues` | list | the new leagues, and the "others" groups (below) | `league`, `split` ... |
| `edits` | object | changes to the game's own clubs and leagues: `clubs` {team id: {name, abbr}}, `leagues` {reg id: {name}}, `competitions` {competition id: {name, logo}}, `swaps` [[team id, team id], ...] | tables only |
| `players` | object | per-club player changes (see `lbplayers.py`: `edits`, `add`, `remove`, `join`, `id`, `face`, `portrait`, `coach_portrait`, `stadium`) | `newfaces`, `faceapp` |
| `uecl` | bool, default true | the Conference League and the reshaped 36-club league phases | `uecl`, `qround` |
| `uecl_name`, `uecl_logo` | text, picture | its name and picture | tables, pictures |
| `europe_first` | {"ucl": [...], "uel": [...], "uecl": [...], "afc": [...]} | clubs of a new career's first league phases (and its first AFC Champions League, `afc`), `"<league>/<k>"` or a team id | `first` |
| `game_europe` | {"<reg of a game top division>": [[pos, comp], ...]} | European places of the game's leagues in place of the shipped ones. Any top division of the game, also one with no shipped places. FL 2027's Belgium is `"115"`: the plan's `access_alias` ({"155": 115}, `fl26world.ACCESS_FALLBACK`) moves the shipped places of a regulation the tables lack, and the world then always writes its `uefa` lines | `uefa` |
| `game_europe` | {"<reg of a game top division>": [[pos, comp], ...]} | European places of the game's leagues in place of the shipped ones; Colombia's and the MLS's whole season (119, 51) as well as their first tournament (168, 166), not both | `uefa`, `ccup`, `seasonsum` |
| `uefa_rank` | list | Mod Studio's UEFA ranking dialog. Applying it writes `europe`, `game_europe` and `uefa_seed`; Build itself does not read it | none |
| `uefa_seed` | [[league, pos, comp], ...] | the order fl26swiss hands places out in | `uefa` order |
| `game_cups` | list of {league, league_cup, super_cup, name, logo, super_name, super_logo} | a league cup (`ccup`) and/or super cup for a country of the game; the super cup is a two-club copy of the game's super cup in that country, played at the end of January in a February-December country | `ccup`, tables + `dates` + `gsuper` |
| `game_seasons` | list of country names | EXPERIMENTAL: Brazil, Chile, China, Japan, Saudi Arabia play August-May | `season <region> 0`, `dates` |
| `saudi_august` | bool | the older form of `game_seasons: ["Saudi Arabia"]` | as above |
| `preseason_cups` | list of {name, clubs, logo} | July knockouts of 4 or 8 invited clubs | `ccup` |
| `ccup_names`, `ccup_logos` | {"6": ..., "7": ..., "0": ...} | names and pictures of the continental cups the world builds | `ccup ... name=` |
| `country_rules` | list of names, `["argentina"]` | a country's own rules run inside Build on the tables and the world file just written (`tools/argentina`, [argentina.md](argentina.md)); a league package with those leagues carries it | `lphase`, `lpname`, `sline`, `jline`, `confsub`, `confsubnames`, tables, emblems |
| `caf_super_cup`, `caf_super_cup_logo` | bool (default true), picture | the CAF Super Cup when both CAF cups exist | `ccup` |
| `editable_kits` | bool | new clubs get plain kits of their own that Edit mode can paint, not lent licensed ones (#112) | tables |
| `country_order` | `"az"` or a list of country names | League order in Select Team / Kick Off / Edit | `order`, `kickorder` |
| `cup_draw` | `seeded` (default), `random`, `off` | how country cups are drawn | `cupdraw` |
| `newlife_ids` | {"<NewLife id>": world id} | written by Build (`pin_newlife`): the world id each NewLife club got, so it keeps it | tables |
| `newlife_game` | object | written by the NewLife page: what *Bring the game's leagues to this season* changed, so it can be undone or redone | none (it feeds `edits` and `players`) |
| `league_order` | list | Mod Studio's Leagues page row order. Build does not read it | none |
| `pack_version` | text | the version name Export the world offers by default (`idledger.default_version`); it goes into the zip's `fl26worldpack.json` and id ledger | none |
| `id_lineage` | text (32 hex) | the lineage of the world's id ledgers (`idledger.py`): the first exported version gets one, every later version keeps it, and Export the world writes it into the project's recipe. Build pins only to ledgers of this lineage; Install offers Update only over an installed version of the same lineage. Export also writes it into the world's built plan (`settings`), so an export of a world that is not the open recipe finds it. A recipe with `id_lineage` but no ledger of that lineage on this PC stops Build and Export (put the last version's `.fl26ids` in the ledgers folder, or set `id_ledger`). Without it (and without `id_ledger`), a ledger pins the Build only if at least 60% of its leagues or clubs are the recipe's (`RECIPE_LIKE`); between 20% and 60% (`RECIPE_UNLIKE`) Build and Export ask: *It is that world* writes `id_lineage`, *A different world* writes `id_not_lineages` | ids of `fl26playerids.json`, tables |
| `id_ledger` | path | an id ledger (`idledger.py`, `<world>.<lineage>.<number>.fl26ids`) Build pins its ids to, absolute or relative to the recipe's folder or the recipes folder; its lineage counts when `id_lineage` is not set. Of it, this PC's history of the versions exported (`%APPDATA%\FL26ModStudio\recipes\ledgers\<world>.<first 12 letters of the lineage>.<number>.fl26ids`; an older single `<world>.fl26ids` is read too) and the ledger a zip brought (`livecpk\<world>\fl26ids-ledger.json`), Build takes the latest version (number, then date) of the lineage. A `.fl26ids` file in the folder under another name counts by the world, lineage and number it says. The built plan keeps `id_ledger` as an absolute path (a path the export cuts out of the zip is left out when read back), so an export without the recipe (`release.py`) finds it. `FL26_LEDGER_STORE` puts the history in another folder (the tests). Only the newest file of each lineage in the history is read; when it cannot be read, Build and Export stop and name it. A test zip's ledger (`"test": true`) is never taken. Every number an export gives (also to a test zip or a zip not kept) is in `<world>.<lineage>.issued`, and the next export takes the number after the highest | ids of `fl26playerids.json`, tables |
| `id_not_lineages` | [text (32 hex)] | lineages the author said are another world of the same name (Build's *A different world*): their ledgers never pin a Build or export of this recipe | ids of `fl26playerids.json`, tables |
| `id_retire` | {"clubs"/"players"/"leagues"/"cups": {id: reason}} | ids of the ledger's version taken out on purpose; written by Build's *Retire these and Build again*. Only an id that is gone can be retired: a league or cup whose id changed, or an id now another league's or cup's, stops Build until it is put back. An id of the ledger that is gone and not listed here stops Build (`LedgerProblems`), and so does a retired id given to someone else. An entry the ledger never had is left out, with a line in the Build log. Retired players keep careers going (Install offers Update); a retired club, league or cup does not (Install offers Replace) | none (the check) |
| `_id_spent` | — | not a recipe key: `idledger.pinned_recipe` hands `plan()` every regulation and competition id a version of the ledger had, and no new league or cup takes one | — |

## A league

| key | type | meaning | world file |
|---|---|---|---|
| `name` | text | unique within the recipe | `league ... name=` |
| `country` | `Country.bin` name | flag, Competition Info name, region | `country=`, `conf=` |
| `flag` | picture | replaces the game's flag of that country while the world is on | pictures |
| `logo` | picture | the league's emblem | pictures |
| `clubs` | 10..32 | league size; 29..32 only with `legs` 1 | `clubs=` |
| `legs` | 1..4 | how often each pair meets; rounds (clubs - 1 or clubs, times legs) at most 54 | `legs=` |
| `above` | league name or a shipped reg id | the league one division up | `above=`, `tier=` |
| `exchange` | number, default 3 | clubs going up and down between the two; for a group (below), the clubs it sends up, 0 allowed | `promote=`, `demote=` |
| (none: two or more leagues with the same `above`) | | groups of one division (GitHub #98): three Serie C groups under Serie B, two Regionalliga groups under a 3. Liga, or groups under groups (nine Serie D groups, each `above` one of three Serie C groups). The league above sends down the sum of the groups' `exchange`, every group keeps its size; only the group with the lowest regulation id is linked to the league above in the tables, fl26chain.dll moves the whole set at the season's end (`leaguebuilder.group_sets`). Not with a split, Apertura/Clausura, a February-December season or `cup_join`; in FL 2027 the league above may be split (not Apertura/Clausura: fl26chain moves the set on the total's table and brings the regular phase along); at most 32 leagues a side, 64 sets | `group=`, `gset`, `ghome` |
| `relegate` | number | on one of several leagues above groups: how many it sends down; without it the groups' promoted are shared out evenly between the leagues above | `gset ... up=` |
| `zone_clubs` | list | on a group: the clubs of the leagues above (or further up) whose region it is, so a club relegated into the set goes to its own region's group (Bayern's to Regionalliga Bayern) and not to the one with the most room. A name is a club of the recipe's leagues, a number a team id (a club of the game's own leagues). A club of a group stays in that group. Groups of different levels can name the same club (a Süper Lig club in its TFF 2. Lig group and in its TFF 3. Lig group: one home a level, FL 2027); a name no league has, or a club two groups of one level name, stops Build. Since 16.11.2026 the set's clubs are placed as a whole: as many relegated clubs at home as the groups' places allow (two of Girone A coming down when Girone A sends one up: one goes home, not both somewhere by turn); a club that cannot go home plays the season in another group as a guest (sider.log `(guest: home ... full)`) and goes home at the next season's end when its group has a place (`(guest came home from ...)`), from the standings and `ghome` alone, so a save and a load keep it. A guest at the bottom or top of its table (going down or up further) is not moved home | `ghome` |
| `zone_border` | list of {"club": name or team id, "to": group name} | on a group, in order of preference (16.11.2026): the clubs on its edge that the federation may move to the neighbouring group `to` when more clubs of the group's region come down than it has places (Italy, Hungary, Serbia redraw their groups that way). fl26chain moves the fewest of them that bring every relegated club home, the first listed first; the moved club comes home the season after as a guest. We have no towns or coordinates, so without the key no club is moved for another. Example: `"zone_border": [{"club": "Novara", "to": "Girone B"}]` on Girone A. `club` must be a club of this group, `to` another group of its division (Check the plan names a wrong one) | `gborder` |
| `playoff` | {"places": [first, last], "with": [group names]} or {"tie": true}; `playoff_name`, `playoff_logo` | a promotion play-off after the last round (kind `promo`, `leaguebuilder.promo_cups`): places first..last play for the place of the `exchange`-th club (3 to 6 for the third place up, as the EFL); `with` adds the same places of other groups of the division (group winners playing off); `tie`: the league above's first club going down v this league's last club going up, the winner in the league above. 2, 4, 8, 16 or 32 clubs; leagues of one table each (not Apertura/Clausura). Without `playoff_name` the play-off is called `<league> Relegation Play-off` / `<league> Promotion Play-off`, shortened to 38 characters (`promo_default_name`: "Rel./Prom. Play-off", then "Play-off", then the league's leading words go), since Competition Info draws a longer name blank; a longer `playoff_name` is kept and Check the plan notes it. In a February-December season (FL 2027 only): filled after the leagues' real last weekend and played in December, the last day no later than 29 December (`promo_cal_last`, `CAL_PROMO_END`); not under a split | `ccup` (`fill=`, `days=`), `poff` |
| `split` | {legs, groups: [n, n], group_legs} | Scottish-style split (`mksplit.py`); `group_legs` one number, or one a group in FL 2027 (`[2, 1]`: Cyprus' championship group twice, the relegation group once); up to 46 rounds (35 on the Scottish line from 15 September, longer on fl26swiss `SPLIT_LONG`), up to 32 split leagues, more than one in a country | `split` |
| `apertura` | true or {"playoff": 8/4/0, "legs": 1/2} | Apertura/Clausura, optional knockout playoff (named `<league> Apertura Playoffs` / `... Clausura Playoffs`, kept to 38 characters by `split_playoff_name`: the part after the league's last small word, as "El Salvador Apertura Playoffs"); `legs` 2 plays each tournament twice round (46 dates at most); `playoff_logo` | `split ... carry=0`, `ccup` |
| `season` | `august` (default) or `calendar` | a new country's top division plays February-December | `season <region> 1` |
| `real_calendar` | {first, last, break, days, also} or `false` (0.2.0) | the league's own season dates (`"07-25"`, `"05-23"`, `["12-21", "01-22"]` or null, weekday names); without it the country's real calendar (`tools/realcal.py` COUNTRY, by tier), else the confederation's; `false`: the old calendar | `rcal` |
| `club_names`, `club_abbrs` | lists | names and short names, `""` = made up | tables |
| `club_order` | list of places (from 0) | FL 2027 only: the clubs in Select Team (and Edit) in this order, the places it leaves out after them A-Z; without it A-Z (`club_order()`). Mod Studio: New clubs > More > Order in Select Team. Remove club / Insert club move its places | `CompetitionEntry.bin` order |
| `club_ids` | list of team ids or `""` | an id a kit, crest or face pack was made for, up to 81919 (`CLUB_ID_MAX`) | tables |
| `club_crests` | list of pictures | crests; `""` = a shield in the club's shirt colours when `club_kits` gives them (`shieldcrest.py`), else a numbered placeholder (`lbassets.py`) | pictures |
| `club_kits`, `club_away_kits` | list of shirt words (`"plain #cd1018 #cd1018 #080808"`) | colours for crests and for picking kits (`mkkits`) | tables |
| `club_third_kits` | list of kit words (`"hoops-105 #14285a #f5d000 #f5d000"`), `""` for none | a club's own third kit, worn as it is by the kit Mod Studio draws (`kitpatterns.plan(third=)`); none: the generator picks one | tables |
| `club_coaches` | list of names | managers (`""` = made up, `mkcoaches.py`) | tables |
| `formation`, `club_formations` | formation label or team id | copied tactics (`mktactics.py`) | tables |
| `game_clubs` | [{at, id, swap, keep}] | clubs the game already has, placed in this league | `nopool` |
| `europe` | [[position, competition], ...] | European and continental places (competition numbers in `fl26world.COMPETITIONS`; 6-9 and 13-15 build a cup of ours) | `uefa`, `ccup` |
| `cup`, `cup_name`, `cup_logo` | bool, text, picture | a national cup for a new country's top division | tables, `dates`, `cup=` |
| `cup_top_only` | bool | a shipped country's cup keeps the top flight only (no `cupall`) | `cup=` |
| (none: `above` a shipped league) | | a division under a game league gets that country's cup and super cup on its line, so fl26chain keeps them right | `cup=`, `scup=`, `cuptop=` ... |
| `supercup`, `supercup_name`, `supercup_logo` | | the super cup that goes with `cup` | tables, `dates` |
| `league_cup`, `league_cup_name`, `league_cup_logo` | | a single-match league cup of the division and the one below, up to 44 clubs, on the Carabao Cup's weeks (0.2.0; before, 16, 8 or 4 clubs with a pre-round) | `ccup` (`like=23`) |
| `league_cup_days` | six `"MM-DD"` | FL 2027 only: the league cup's own dates, for the first, second and third round, quarter-final, semi-final and final, in the season's order, 3 days apart at least, none a European day or within two days of a national cup round (`cup_days`) | `ccup ... days=` |
| `trophy`, `trophy_name`, `trophy_logo`, `trophy_days` | bool, text, picture, six `"MM-DD"` | FL 2027 only, a division below the top one (August-May): a third cup like the EFL Trophy / FA Trophy / Copa RFEF, the league cup's single-match knockout of this division and the one below, up to 44 clubs, on `TROPHY_DAYS` (Tuesdays 6 Oct - 3 Mar, final Sunday 5 Apr) or its own; two divisions in a row cannot both have one | `ccup` (`like=23`, code `FL_<rid>_TCUP`), `lcup=` on the division's line |
| `cup_join` | bool | a third division's first clubs join the country's cup: under the game's second division the game's cup (B228, `CUP_JOIN_SIZES`); FL 2027 also under a second division of the recipe, the new country's own cup of the two divisions above (`own_join_field`: 18-32 on the bracket screen's sizes, 36, 40 or 44; never 48, B334) | `cupthird=`, `cupn=` |
| `exhibition` | bool | Kick Off only, never in a Master League season | `exhibition=1` |
| `select_team` | `europe`, `latam`, `africa`, `other` | the league takes the Select Team place of the game's Other European Leagues / Other Latin American Teams / Other Clubs (Africa) / Other group (`fl26world.POOL_PICK`), before the order and the pins; one league a group, not an exhibition league, not `latam` with `conmebol_associations`; the world file line gets `pick=1` (fl26clubs: the clubs get the slot in the Master League too) | Leagues page, Places in Select Team |
| `others` | `europe`, `latam`, `asia`, `africa`, `classic` | not a league: clubs for the game's "Other ..." groups | tables only |
| `newlife` | {"version": ..., "clubs": [NewLife club id, ...]} | written by the NewLife page: which release clubs fill the places | tables |

## The `players` block in one paragraph

A club of the game is keyed by its team id and its players by player id. A new club has no id
before Build, so it is keyed `"<league name>/<k>"`, and its players by their place in the squad.
Values are the texts `playeredit.py`'s CSV takes (`"CF"`, `"Right"`, `"85"`), checked at Build.
`join` moves a player with his record (a transfer, or a national-team call-up). `id` picks a new
player's id (Mod Studio stays at or below `PID_MAX` = 262143: the game packs a player id into 18 bits,
and a world with a higher one crashes when a Master League is created). `shirt` is the player's number
at that club (1-99): a number the recipe gives stays with its player, and anybody else in the squad
who wore it takes a free one (`lbplayers.unique_shirts`); a club with no `shirt` at all is numbered
by position as before. A national team's numbers are its own (a club's `shirt` never reaches the
call-up). Contracts and loans have no place in the game's tables (see
[player-record.md](../../research/player-record.md)), so a recipe cannot carry them. The examples
are in the docstring of `tools/lbplayers.py`.

## Adding a key

1. Read and validate it in `plan()` and put what Build needs in the plan (`pl`).
2. Use it in `build()`. If the game needs it at runtime, write a world-file line.
3. Add it to `has_edits()` if it is recipe-level, and to `recipe_from_plan()` if a recipe
   rebuilt from a plan must keep it.
4. Add it to the docstring list at the top of `leaguebuilder.py` and to this page.
5. Add a `tools/test_<name>.py` with plain asserts (see [testing.md](testing.md)).
6. If a page edits it, call `self.project.touch()` after the change, and put the UI strings
   through `_()` and into `lang/*.json`.
