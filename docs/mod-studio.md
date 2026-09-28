# FL26 Mod Studio — how it works

The user guide is [mod-studio-guide.md](mod-studio-guide.md) ([hrvatski](mod-studio-guide.hr.md)).
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
- Unknown keys are ignored, so later versions can add fields without breaking older modules.
- A split league is one `league` line for the regular phase plus
  `split <total> regular=<id> groups=<id>,<id>`.
- `uefa <regulation> <position> <competition> <alt>`: one European place per line, in
  hand-out order. Without any, fl26swiss uses the DLL's own list (shipped leagues only).

The builder also keeps a copy in the world folder (`livecpk\<world>\fl26world.txt`).

## League packages (`.fl26pack`)

A package is a zip with:

```
manifest.json    {"format": "fl26pack", "format_version": 1, "name", "author", "version",
                  "description", "made_with", "leagues": [{"name", "country", "clubs"}],
                  "clubs", "faces", "edits": {"leagues", "clubs"}, "player_changes"}
recipe.json      the leagues as a recipe has them, the player changes of their clubs, and
                 optionally changes to the game's own leagues, clubs and players
assets/...       the logos and crests used
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
