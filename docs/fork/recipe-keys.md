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
| `europe_first` | {"ucl": [...], "uel": [...], "uecl": [...]} | clubs of a new career's first league phases, `"<league>/<k>"` or a team id | `first` |
| `game_europe` | {"<reg of a game top division>": [[pos, comp], ...]} | European places of the game's leagues in place of the shipped ones | `uefa` |
| `uefa_rank` | list | Mod Studio's UEFA ranking dialog. Applying it writes `europe`, `game_europe` and `uefa_seed`; Build itself does not read it | none |
| `uefa_seed` | [[league, pos, comp], ...] | the order fl26swiss hands places out in | `uefa` order |
| `game_cups` | list of {league, league_cup, super_cup, name, logo, super_name, super_logo} | a league cup and/or super cup for a country of the game | `ccup`, `dates` |
| `game_seasons` | list of country names | EXPERIMENTAL: Brazil, Chile, China, Japan, Saudi Arabia play August-May | `season <region> 0`, `dates` |
| `saudi_august` | bool | the older form of `game_seasons: ["Saudi Arabia"]` | as above |
| `preseason_cups` | list of {name, clubs, logo} | July knockouts of 4 or 8 invited clubs | `ccup` |
| `ccup_names`, `ccup_logos` | {"6": ..., "7": ..., "0": ...} | names and pictures of the continental cups the world builds | `ccup ... name=` |
| `caf_super_cup`, `caf_super_cup_logo` | bool (default true), picture | the CAF Super Cup when both CAF cups exist | `ccup` |
| `editable_kits` | bool | new clubs get plain kits of their own that Edit mode can paint, not lent licensed ones (#112) | tables |
| `country_order` | `"az"` or a list of country names | League order in Select Team / Kick Off / Edit | `order`, `kickorder` |
| `cup_draw` | `seeded` (default), `random`, `off` | how country cups are drawn | `cupdraw` |
| `newlife_ids` | {"<NewLife id>": world id} | written by Build (`pin_newlife`): the world id each NewLife club got, so it keeps it | tables |
| `newlife_game` | object | written by the NewLife page: what *Bring the game's leagues to this season* changed, so it can be undone or redone | none (it feeds `edits` and `players`) |
| `league_order` | list | Mod Studio's Leagues page row order. Build does not read it | none |

## A league

| key | type | meaning | world file |
|---|---|---|---|
| `name` | text | unique within the recipe | `league ... name=` |
| `country` | `Country.bin` name | flag, Competition Info name, region | `country=`, `conf=` |
| `flag` | picture | replaces the game's flag of that country while the world is on | pictures |
| `logo` | picture | the league's emblem | pictures |
| `clubs` | 10..24 | league size | `clubs=` |
| `legs` | 1..4 | how often each pair meets | `legs=` |
| `above` | league name or a shipped reg id | the league one division up | `above=`, `tier=` |
| `exchange` | number, default 3 | clubs going up and down between the two | `promote=`, `demote=` |
| `split` | {legs, groups: [n, n], group_legs} | Scottish-style split (`mksplit.py`) | `split` |
| `apertura` | true or {"playoff": 8/4/0} | Apertura/Clausura, optional knockout playoff; `playoff_logo` | `split ... carry=0`, `ccup` |
| `season` | `august` (default) or `calendar` | a new country's top division plays February-December | `season <region> 1` |
| `club_names`, `club_abbrs` | lists | names and short names, `""` = made up | tables |
| `club_ids` | list of team ids or `""` | an id a kit, crest or face pack was made for, up to 81919 (`CLUB_ID_MAX`) | tables |
| `club_crests` | list of pictures | crests; `""` = a shield in the club's shirt colours when `club_kits` gives them (`shieldcrest.py`), else a numbered placeholder (`lbassets.py`) | pictures |
| `club_kits`, `club_away_kits` | list of shirt words (`"plain #cd1018 #cd1018 #080808"`) | colours for crests and for picking kits (`mkkits`) | tables |
| `club_coaches` | list of names | managers (`""` = made up, `mkcoaches.py`) | tables |
| `formation`, `club_formations` | formation label or team id | copied tactics (`mktactics.py`) | tables |
| `game_clubs` | [{at, id, swap, keep}] | clubs the game already has, placed in this league | `nopool` |
| `europe` | [[position, competition], ...] | European and continental places (competition numbers in `fl26world.COMPETITIONS`; 6-9 and 13-15 build a cup of ours) | `uefa`, `ccup` |
| `cup`, `cup_name`, `cup_logo` | bool, text, picture | a national cup for a new country's top division | tables, `dates`, `cup=` |
| `cup_top_only` | bool | a shipped country's cup keeps the top flight only (no `cupall`) | `cup=` |
| (none: `above` a shipped league) | | a division under a game league gets that country's cup and super cup on its line, so fl26chain keeps them right | `cup=`, `scup=`, `cuptop=` ... |
| `supercup`, `supercup_name`, `supercup_logo` | | the super cup that goes with `cup` | tables, `dates` |
| `league_cup`, `league_cup_name`, `league_cup_logo` | | a league cup of 16, 8 or 4 clubs | `ccup`, `lpre` |
| `exhibition` | bool | Kick Off only, never in a Master League season | `exhibition=1` |
| `others` | `europe`, `latam`, `asia`, `africa`, `classic` | not a league: clubs for the game's "Other ..." groups | tables only |
| `newlife` | {"version": ..., "clubs": [NewLife club id, ...]} | written by the NewLife page: which release clubs fill the places | tables |

## The `players` block in one paragraph

A club of the game is keyed by its team id and its players by player id. A new club has no id
before Build, so it is keyed `"<league name>/<k>"`, and its players by their place in the squad.
Values are the texts `playeredit.py`'s CSV takes (`"CF"`, `"Right"`, `"85"`), checked at Build.
`join` moves a player with his record (a transfer, or a national-team call-up). `id` picks a new
player's id (Mod Studio stays at or below `PID_MAX` = 399999). The examples are in the docstring of
`tools/lbplayers.py`.

## Adding a key

1. Read and validate it in `plan()` and put what Build needs in the plan (`pl`).
2. Use it in `build()`. If the game needs it at runtime, write a world-file line.
3. Add it to `has_edits()` if it is recipe-level, and to `recipe_from_plan()` if a recipe
   rebuilt from a plan must keep it.
4. Add it to the docstring list at the top of `leaguebuilder.py` and to this page.
5. Add a `tools/test_<name>.py` with plain asserts (see [testing.md](testing.md)).
6. If a page edits it, call `self.project.touch()` after the change, and put the UI strings
   through `_()` and into `lang/*.json`.
