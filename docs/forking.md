# Making your own fork of FL26 Mod Studio

> **0.2.0 is the last release of FL26 Mod Studio with new features.** After it this repository
> only gets bug fixes, about once a week. New features are what forks are for, and this page
> and the chapters below are written so that you can carry the project on without us.

Mod Studio is MIT licensed (see `LICENSE`). Fork it, rename it, change it, ship it: no
permission needed. Keep the licence file and the copyright line, and say in your README that
your fork is based on FL26 Mod Studio. That is all the licence asks.

This page is the map: what lives where, how to run and build it, and how to add the usual
things (a page, a recipe key, a module, a translation). The details are in the chapters:

| chapter | what is in it |
|---|---|
| [fork/code-map.md](fork/code-map.md) | every file of the program and the builder, every page, and what calls what when someone presses Build |
| [fork/recipe-keys.md](fork/recipe-keys.md) | every recipe key the code reads, its type, its meaning and the world-file line it becomes |
| [fork/world-file.md](fork/world-file.md) | every line kind of `fl26world.txt`, the code that writes it and the modules that read it |
| [fork/modules.md](fork/modules.md) | every Sider module and DLL: load order, bundles, exports, hooks, status codes; the 0.2.0 `-calendar` patch set; what to do when the game exe changes |
| [fork/building.md](fork/building.md) | zig and the DLL build scripts, checksums, the module pack, PyInstaller and `mszip.py`, the version, pointing the updater at your releases |
| [fork/testing.md](fork/testing.md) | every test and what it proves, `regress018.py`, `buildcheck.py`, the C tests, and the in-game checklist |
| [fork/newlife-format.md](fork/newlife-format.md) | the NewLife release format as Mod Studio reads it |
| [fork/club-world-cup-32.md](fork/club-world-cup-32.md) | the unfinished 32-club Club World Cup (2025 format): the table script and the module code that exist, and what is missing to put it in Mod Studio |

## What you need

- **Windows** and a copy of Football Life 2026 (PES 2021 with the SP Football Life patch) to
  test with.
- **Python 3.11 or newer** with `PySide6`, `Pillow` and `capstone`
  (`pip install PySide6 Pillow capstone`). `py7zr` is optional (7z kit and face packs).
- **zig 0.16.0** for the six DLLs in `tools/native/` (`ZIG=<path to zig.exe>`). The module
  pack compiles them, so you need it for a release and whenever you change their C source.
- **PyInstaller** and **markdown** for a release (`pip install pyinstaller markdown`).

## Run it from source

```
cd tools
python modstudio_main.py
```

The first start asks for the game folder and unpacks the game's tables into
`%APPDATA%\FL26ModStudio\tables` (Settings > Unpack the game's tables). Your settings are in
`%APPDATA%\FL26ModStudio\settings.json`. A fork that wants its own settings and tables next to
the official ones changes the folder name in `APPDIR` (`tools/modstudio/app.py`; the tables and
recipe copies of `project.py` follow it) and in `CACHE` (`tools/modstudio/newlife.py`).

## The parts

```
tools/modstudio_main.py       the entry point (the window)
tools/modstudio/app.py        main window, left bar (page_groups), menus, updater
tools/modstudio/pages/*.py    one file per page: leagues, builder (New clubs, Build), players,
                              newlife, kits, stadiums, install, modules, diagnostics ...
tools/modstudio/project.py    the recipe being edited and the game's tables, shared by pages
tools/modstudio/game.py       the game folder, the exe, sider.ini, the Edit save
tools/modstudio/i18n.py       translations: _("English text") looks up lang/<code>.json
tools/leaguebuilder.py        the League Builder core: recipe -> plan -> world (no UI)
tools/mk*.py                  the generators leaguebuilder calls: mkleague (regulations),
                              mkteams, mkplayers, mkcup, mkccup, mkswiss, mkuecl, mkcrests ...
tools/fl26world.py            reads and writes the world file the modules read
tools/lbpack.py               the module pack Build installs (sider/*.lua + the DLLs)
tools/mszip.py                the release: frozen exe + pack + guides -> one zip
sider/*.lua                   the Sider modules that are always on (fl26caps: table sizes ...)
sider/experimental/*.lua      the rest: fl26swiss (UEFA cups), fl26chain (promotion),
                              fl26edit, the crash guards ...
tools/native/*.c              fl26join, fl26clubs, fl26chain, fl26swiss, fl26regen, fl26edit
                              (built with zig)
docs/                         the guides (mod-studio-guide.md and its hr/es/fr copies)
```

The split that matters: **the window never builds anything itself.** Every page edits the
recipe (a JSON file), and Build hands the recipe to `leaguebuilder.py`. Anything you can do in
the window you can also do from the command line:

```
python tools/leaguebuilder.py plan  my-recipe.json --base <the unpacked pesdb folder>
python tools/leaguebuilder.py build my-recipe.json --base <...> --game "<game folder>" --replace
python tools/leaguebuilder.py on    _FL26MyWorld --game "<game folder>"
python tools/leaguebuilder.py check --game "<game folder>"
```

`plan` checks the recipe and prints what it would build; `build` writes the world into
`SiderAddons\livecpk` (`--replace` when it exists already); `on` switches it on; `check` reads
`sider.log` after a game start. The recipe keys are listed in the docstring at the top of
`leaguebuilder.py` and, checked against the code, in [fork/recipe-keys.md](fork/recipe-keys.md).

## The world file

Build writes `SiderAddons\modules\fl26world.txt`, a plain text file with one line per fact
(a league, its regulation id, its European places, a cup, the calendar, the draw ...). The
modules read it at game start; none of them knows anything about a recipe. When you add a
feature that the game has to do at runtime, this is the bridge: a recipe key, a world-file
line written in `leaguebuilder.py` (via `tools/fl26world.py`), and a module that reads the
line. [fork/world-file.md](fork/world-file.md) lists every line kind with its writer and
readers; `docs/mod-studio.md` explains the cup, European and calendar lines in depth.

## Adding things

**A recipe key.** Read it in `leaguebuilder.plan()` (validate it there and raise `BuildError`
with a sentence a person understands), use it in `build()`, and add it to the docstring list.
If the game needs it at runtime, write a world-file line. Add a small `tools/test_<name>.py`
next to the others (plain asserts, run with `python tools/test_<name>.py`).

**A field on a page.** Pages read and write `self.project.recipe` and call
`self.project.touch()` after a change (it saves the recipe and tells the other pages).
Pages that show recipe data connect to `self.project.changed`. Look at a small page first (`pages/balls.py`,
`pages/music.py`), then at `pages/builder.py` for the League Builder pages.

**A new page.** A class in `pages/<name>.py` with `title`, `hint` and `help`, then one entry in
`page_groups()` in `app.py`. Group `None` builds a page that has no place in the left bar
(another page opens it).

**A Sider module.** A `.lua` file in `sider/experimental/`, added to `ORDER` in `lbpack.py`
(the load order) so it goes into the pack, or to one of its `BUNDLES` for a small guard. Build
installs the pack and makes every module of `ORDER` a live `lua.module` line of `sider.ini`
(`install_modules` in `leaguebuilder.py`). Sider's
Lua has no `pcall`, `debug` or `rawget`: check every value before you index it, and log what
you do. `fl26kitguard.lua` is a short example of wrapping a function another module calls.
Patching game code: `sider/fl26caps.lua` shows the pattern (verify the original bytes,
then write); the addresses in this repository are for `FL_2026.exe` of 458,910,720 bytes
(Football Life 2026 v2.0, file version 26.0.0.0; v2.2, 26.2.0.3, has the same size and is
known to work).
Every module and DLL is listed in [fork/modules.md](fork/modules.md).

**A translation.** Every UI string is `_("English text")`. Add the English text as a key in
`tools/modstudio/lang/<code>.json` with its translation. `python tools/langcheck.py` lists what
each language is missing. A new language: copy `es.json`, translate, and add it to
`LANGUAGES` in `i18n.py`.

## Checking before a release

```
python tools/regress018.py --base <pesdb>      builds every test recipe and checks each world
python tools/buildcheck.py <world pesdb> --base <pesdb>
python tools/test_cup_draw.py                  (and the other test_*.py)
python tools/langcheck.py
```

Then test in the game: a new Master League career in a world with your change, played past
the first matchday and, for anything that touches seasons, past the season change, then saved
and loaded. The full list and what each test proves: [fork/testing.md](fork/testing.md).

## Building a release

```
python tools/mszip.py
```

It freezes the window with PyInstaller (a folder, not one file: one-file exes start slowly
because antivirus scans the unpacked copy every time), builds the module pack with `lbpack.py`,
turns the guides into HTML and zips it all into `out/FL26ModStudio-<version>.zip`. It refuses
to package a file that contains a drive path or a user name. The version is `VERSION` in
`tools/modstudio/__init__.py`.

The updater (`tools/modstudio/updater.py`) looks at this repository's GitHub releases. A fork
points it at its own repository (`REPO`), or nobody gets your updates (and your users get
ours). Releases are tagged `modstudio-<version>` with the zip attached. Details, and the regen
face pack (`FL26_REGEN_FACES`), are in [fork/building.md](fork/building.md).

## Rules that keep a fork out of trouble

- **No game files in the repository or the zip**: no tables, no CPKs, no renders, no kits or
  faces made from game assets. Mod Studio reads them from the person's own game at runtime.
- **No real club crests, league logos or brand assets** in the repository. People bring
  their own through the Kits / crest / logo pages.
- **No other people's mods** inside your release without their permission. Mod Studio
  installs what the person already has.
- **Credit who helped you**, the way the README here does.

## Where to ask

The FL Mod Studio Discord (the invite is in the README) has a forum for mods; forks are
welcome there.
