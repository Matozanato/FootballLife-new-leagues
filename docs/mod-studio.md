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
  writes it on the second division under a new country's top flight when that top flight has
  its own cup (`"cup": true` in the recipe) that the copied cup's round dates only fit alone.
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
- `uecl <id> <id> ...`: the Conference League's 36 entrants at the start, written when the
  recipe's `uecl` is on (the default). Build then reshapes the Champions League and the Europa
  League to a league phase of 36 (mkreshape), clones FL_UECL as competition 174 with
  regulations 186 (league phase, group 1210) and 187 (knockout) (`mkuecl.build`), and adds the
  play-offs 188/189 (`mkeuropo.build`). fl26swiss.lua does not read this line yet; it uses
  its own UECL list, the same clubs on the game's own tables.

- `ccup <groups regulation> ko=<knockout regulation> groups=<n> entry=<reg>:<position>,... name=<text>`:
  a continental cup of the four above, built by `tools/mkccup.py` into the world's tables and
  run by fl26swiss.dll: filled at the end of August from the leagues' tables (a club already in
  another of these cups is skipped), drawn into groups of four, then a knockout of 2 x groups
  clubs. `groups=0` is a straight knockout (then both regulations are the same). Build sizes
  each cup to 32, 16, 8 or 4 clubs: the recipe's places first, and for AFC Champions League Two
  and the Copa Sudamericana the shipped leagues of that continent fill the rest.

A new country's own cup is not a line: with `"cup": true` on a top division (and optionally
`"supercup": true`) Build copies a shipped cup (`tools/mkcup.py --like`, picked by how many
clubs the top division and the one below it have, so the round dates fit) into the country's
region, and a super cup from the Belgian one. The game fills them itself. `"club_coaches"` in a
league gives its new clubs' managers names (empty = `FL Mnnnn`).

Overview and Diagnostics warn when the world that is on has new leagues but no `uefa` line
names one of them, and when its Conference League is on but regulations 186/187/1210 are
missing from its tables.

The builder also keeps a copy in the world folder (`livecpk\<world>\fl26world.txt`).

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
