# Making your own fork of FL26 Mod Studio

Mod Studio is MIT licensed (see `LICENSE`). Fork it, rename it, change it, ship it: no
permission needed. Keep the licence file and the copyright line, and say in your README that
your fork is based on FL26 Mod Studio. That is all the licence asks.

This page is the map: what lives where, how to run and build it, and how to add the usual
things (a page, a recipe key, a module, a translation). After 0.2.0 this repository only gets
bug fixes, so new features are what forks are for.

## What you need

- **Windows** and a copy of Football Life 2026 (PES 2021 with the SP Football Life patch) to
  test with.
- **Python 3.11 or newer** with `PySide6`, `Pillow` and `capstone`
  (`pip install PySide6 Pillow capstone`). `py7zr` is optional (7z kit and face packs).
- **zig** (0.16) for the four DLLs in `tools/native/`. Only needed when you change their C
  source; the built DLLs ship in the release zip.
- **PyInstaller** for the `.exe` (`pip install pyinstaller`). Only needed for a release.

## Run it from source

```
cd tools
python modstudio_main.py
```

The first start asks for the game folder and unpacks the game's tables into
`%APPDATA%\FL26ModStudio\tables` (Settings > Unpack the game's tables). Your settings are in
`%APPDATA%\FL26ModStudio\settings.json`. A fork that wants its own settings and tables next to
the official ones changes the folder name in `tools/modstudio/app.py` (`load_settings`) and
`tools/modstudio/project.py`.

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
tools/native/*.c              fl26join, fl26clubs, fl26chain, fl26swiss (built with zig)
docs/                         the guides (mod-studio-guide.md and its hr/es/fr copies)
```

The split that matters: **the window never builds anything itself.** Every page edits the
recipe (a JSON file), and Build hands the recipe to `leaguebuilder.py`. Anything you can do in
the window you can also do from the command line:

```
python tools/leaguebuilder.py plan  my-recipe.json --base <the unpacked pesdb folder>
python tools/leaguebuilder.py build my-recipe.json --base <...> --game "<game folder>"
```

`plan` checks the recipe and prints what it would build; `build` writes the world into
`SiderAddons` and switches it on. The recipe keys are listed in the docstring at the top of
`leaguebuilder.py`, and that list is the reference.

## The world file

Build writes `SiderAddons\modules\fl26world.txt`, a plain text file with one line per fact
(a league, its regulation id, its European places, a cup, the calendar, the draw ...). The
modules read it at game start; none of them knows anything about a recipe. When you add a
feature that the game has to do at runtime, this is the bridge: a recipe key, a world-file
line written in `leaguebuilder.py` (via `tools/fl26world.py`), and a module that reads the
line. `docs/mod-studio.md` describes the lines.

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
then write); the addresses in this repository are for the FL26 exe (26.1.1c).

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
the first matchday and, for anything that touches seasons, past the season change.

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
points it at its own repository, or nobody gets your updates (and your users get ours).

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
