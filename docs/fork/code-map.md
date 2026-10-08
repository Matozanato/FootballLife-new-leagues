# Code map

What every part of Mod Studio does, and what calls what when someone presses Build. Paths are
relative to the repository root.

## The window: `tools/modstudio/`

The window is PySide6. One rule matters more than any other: **the window never builds
anything itself.** Pages edit a recipe (JSON) or the files of Sider's content servers. Build
hands the recipe to `tools/leaguebuilder.py`, which has no UI and can run from the command
line.

| file | what it does |
|---|---|
| `__init__.py` | `VERSION`. mszip names the zip after it, and the updater compares against it |
| `app.py` | main window, menus, left bar (`page_groups()`), the Play header, the update banner, `load_settings` (`%APPDATA%\FL26ModStudio\settings.json`) |
| `project.py` | `Project`: the recipe being edited, the game's unpacked tables (`%APPDATA%\FL26ModStudio\tables`), `touch()` (save + tell other pages), `changed` signal, the copies of recipes a Build keeps |
| `game.py` | `Game`: the folder with `FL_2026.exe`, the Sider folder, `sider.ini`, the Edit save, starting the game, "is it running" |
| `siderini.py` | `sider.ini` as lines: read, switch, reorder and write back byte for byte |
| `modules.py` | Lua modules: where a module's file is, and the order rules (from module readmes and from what files publish as `ctx.<name>`) |
| `roots.py` | `cpk.root` content folders: what each holds and which wins for a file |
| `servers.py`, `mapfile.py` | Sider content servers (kits, stadiums, balls, commentary, music ...): their folders, map files and columns |
| `installer.py` | installs a `.zip` / `.7z` / folder / `.lua` / `.cpk` mod: splits it into parts and puts each where Sider wants it |
| `profiles.py` | named setups (which roots and modules are on, in which order) |
| `backups.py` | restore points: a copy of every file before the program changes it, in `SiderAddons\ModStudio\backups` |
| `checks.py` | health checks as `(level, area, text, page)` rows for Overview and Diagnostics |
| `newlife.py` | a NewLife release as leagues to pick, and the recipe entries for one-click leagues, updates and the game's own leagues (see [newlife-format.md](newlife-format.md)) |
| `updater.py` | looks at the GitHub releases of `REPO`, tag `modstudio-<version>`, downloads the zip, checks its sha256, swaps the program folder |
| `i18n.py` | `_("English text")` looks the text up in `lang/<code>.json`; `LANGUAGES` lists the languages |
| `credits.py` | Help > Credits (keep it in step with the README) |
| `pitch.py` | the formation picture (places, roles) used by the formation pickers |
| `theme.py`, `ui.py` | the look, and the small building blocks every page uses (`Page`, banners, cards, `Job` background runner) |
| `lang/*.json` | translations (hr, es, fr). `i18n.py` also reads `tools/lang/<code>.json`, the League Builder's own texts |
| `assets/` | the icon |

### The pages: `tools/modstudio/pages/`

The left bar comes from `page_groups()` in `app.py`:

| group | page (class) | file | what it edits |
|---|---|---|---|
| | Overview | `overview.py` | the live world, what changed since it was built, one button to build and install it, health checks (`checks.quick`) |
| LEAGUE BUILDER | Leagues | `leagues.py` | every league, the game's and the recipe's, by continent; opens the league window or the game-league panel |
| | New clubs (`NewClubs`) | `builder.py` | the clubs of the recipe's leagues, a club window each (name, crest, kits, manager, stadium) |
| | Players | `players.py` (+ `playerpick.py`, `tableimport.py`) | one club's squad, every field of every player; sign/call up, transfer, CSV import |
| | NewLife | `newlife.py` | pick leagues from a NewLife release, update them, bring the game's leagues to the release's season |
| | Packages | `packages.py` | save leagues as a `.fl26pack`, add one to the recipe |
| | Build | `builder.py` (`Build`) | install modules, build, switch on, check |
| GAME CONTENT | Kits, Stadiums, Balls, Commentary, Music, Other content | `kits.py`, `stadiums.py`, `balls.py`, `commentary.py`, `music.py`, `content.py` | the content servers' map files and libraries; nothing is written until Save |
| MANAGE | Install, Modules, Content folders, Profiles, Restore, Diagnostics, Settings | `install.py`, `modules.py`, `roots.py`, `profiles.py`, `restore.py`, `diagnostics.py`, `settings.py` | mods, `lua.module` lines, `cpk.root` lines, setups, restore points, checks + `sider.log`, game folder / language / tables |
| (not in the bar) | New leagues (`NewLeagues`) | `builder.py` | reached from other pages |

`builder.py` is the biggest file. It also holds the dialogs the League Builder pages share:
`LeagueDialog`, `ClubDialog`, `GameClubDialog`, `EuropeTable`, `PreseasonDialog`,
`CompetitionNamesDialog`, `GameEuropeDialog`, `EuropeFirstDialog`, `GameCupsDialog`,
`StadiumPicker` and others. `GameLeagues` is the panel for a league of the game.

## The builder: `tools/`

| file | role |
|---|---|
| `leaguebuilder.py` | the core: `plan(recipe, base)` checks a recipe and decides every id; `build(pl, base, game)` writes the world folder; `switch_on`, `install_modules`, `check` |
| `fl26world.py` | the world file: writes it (`write_world`), reads it, the European places (`uefa_places`), slot tables (`DEFAULT_SLOT`, `NO_SLOT_IDS`) |
| `mkleague.py` (`M`), `mkworld.py` (`W`) | table records: competitions, regulations, entries, team records, the free id lists |
| `mkteams.py`, `mkplayers.py`, `mkcoaches.py` | new clubs, placeholder squads of 30, managers |
| `lbplayers.py` | the recipe's `players` block applied to the world (edits, add, remove, join, ids, NewLife squads, portraits) |
| `playeredit.py` | the player record by field name (97 fields, CSV texts); `lbplayers` writes through it |
| `lbfaces.py`, `lbassets.py`, `shieldcrest.py`, `mkcrests.py`, `mkemblems.py`, `mkflags.py` | faces, crests (given / shield in shirt colours / numbered), emblems for cups without a picture, flags |
| `mkkits.py`, `kitpics.py` | kits: lent from a game club of the nearest colours, or plain editable ones (`editable_kits`); kit-server folders from pictures |
| `mktactics.py` | formations copied from a club of the game |
| `mksplit.py` | split seasons and Apertura/Clausura phases |
| `mkcup.py` | national cups and super cups copied from a shipped cup |
| `mkccup.py` | our continental, league and pre-season cups (`ccup` lines) |
| `mkuecl.py`, `mkeuropo.py`, `mkreshape.py`, `mkphases.py` | Conference League, the play-offs and qualifying rounds, the 36-club league phase |
| `mkregioncats.py`, `mkregnames.py`, `mkcatflags.py` | the per-world modules `fl26regions.lua` / `fl26regnames.lua` (region names, category flags) |
| `lbstadiums.py` | Stadium Server library and `map_teams.txt` |
| `lbpackage.py` | `.fl26pack` league packages |
| `lbpack.py` | the module pack Build installs (`ORDER`, `BUNDLES`, DLL builds) |
| `uefakey.py` | the UEFA key: European places from a ranking of the countries (the UEFA ranking dialog) |
| `squadimport.py` | squad import from any CSV |
| `siderdir.py`, `siderroot.py`, `flpaths.py` | finding the Sider folder, switching `cpk.root`, environment paths |
| `pesdb.py`, `cpk.py`, `cpkread.py`, `wesys.py` | reading the game's tables and archives |
| `mszip.py` | the release zip |
| `regress018.py`, `buildcheck.py`, `test_*.py`, `langcheck.py` | checks, see [testing.md](testing.md) |
| `patchset.py` and helpers | the `fl26caps` patch-set generator, see [for-developers.md](../for-developers.md) |

## What happens when someone presses Build

*Build and install* on the Build page (`pages/builder.py`, class `Build`, `build_all`) does this:

1. `B.plan(recipe, base)` validates the recipe and decides regulation ids, competition ids,
   regions, tiers, team ids, cups and European places. Any problem is a `BuildError`
   sentence, shown as it is, and nothing else happens.
2. `B.pin_newlife(recipe, base)` writes the world id of every NewLife club into the recipe
   (`newlife_ids`), so the clubs keep their ids in later builds.
3. After the person confirms, the rest runs in a background `Job` (`ui.run_job`). A restore
   point of `sider.ini` is taken first (`backups.snapshot`).
4. `B.install_modules(game)` copies the module pack into Sider's `modules` folder. The pack
   is made beforehand by `lbpack.py` (it copies `sider/*.lua`, bundles the guards, compiles
   the DLLs with zig and adds the regen face pack if there is one). `pack_dir()` finds it
   as `pack` next to the program, inside the frozen program, or as `out/lbpack` in a
   checkout. Every file it replaces is kept first in `modules\before-builder-<n>\`.
   `ensure_modules` writes the `lua.module` lines of `sider.ini` in the order of the pack's
   `modules.txt`, and switches off the modules a bundle replaced (`retired.txt`).
5. `B.build(pl, base, game, replace)` builds the world in `livecpk\<world>.building`, then
   renames it into place:
   - game clubs moved into our leagues, and their swaps (`nopool`);
   - `M.add_league` per league; teams, coaches (`mkcoaches`), tactics (`mktactics`);
   - `M.write_tables`; squads (`mkplayers`); players (`lbplayers.fill_newlife`,
     `fill_tiers`, `apply`), faces (`lbfaces`), portraits;
   - splits (`mksplit`); European competitions (`europe`: `mkreshape`, `mkuecl`,
     `mkeuropo`); national cups (`mkcup`); continental and league cups (`continental`:
     `mkccup`);
   - the world file (`fl26world.from_tables` + every line kind, `write_world`);
   - `pictures()` (crests, logos, flags, emblems, kits), and `region_modules()` (the per-world Lua);
   - `write_manifest`, `keep_added` (pictures put in the world folder by hand survive).
6. `B.switch_on(world, game)` makes the world's `cpk.root` the one active `_FL26` root,
   copies the world file and the per-world modules to `modules\`, and writes the Stadium
   Server and kit maps.
7. After the game has started once, *Check* (`B.check(game)`) reads `sider.log` and reports,
   module by module, whether each one read the world file.

The page also has the steps as separate buttons (install the modules, build, switch on,
check), which call the same functions.

The same steps run from the command line:

```
python tools/leaguebuilder.py plan  my-recipe.json --base <unpacked tables>
python tools/leaguebuilder.py build my-recipe.json --base <...> --game "<game folder>" --replace
python tools/leaguebuilder.py on    _FL26MyWorld --game "<game folder>"
python tools/leaguebuilder.py check --game "<game folder>"
```
