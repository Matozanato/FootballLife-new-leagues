# Game content > Trophies

Trophy assignments are now a normal `BuilderPage` named `Trophies` under GAME
CONTENT. They edit the selected `Project.recipe`, not the world activated in
Sider. The old `NewLeagues.trophies()` entry and CUPS > More > Trophies both route
to this page. They do not open another editor or commit changes themselves.

## Shared editor and unchanged backend

The old `pages/builder.py:TrophiesDialog` content is extracted into
`pages/trophies.py:TrophyEditor`. The dialog remains a thin compatibility wrapper
using the same controls. Competition IDs, regulation references, search, folder
selection, double-click selection and No trophy of its own are retained. Existing
unknown competition mappings remain visible instead of being removed.

The storage is still `recipe["trophies"] = {"competition id": "folder"}`. There
are no persistent draft fields. Existing folder strings are not normalized merely
by opening the page. Pick uses the same trophy backend checks; Apply rechecks
edited paths in case files disappeared. Invalid historical entries remain intact
unless explicitly cleared or replaced; Build's existing validation still applies.

`lbtrophies.py`, Entrance.lua integration, phase/final selection, asset copying,
Build/import/export behavior and native DLLs are unchanged. No trophy generation
or competition identity logic is implemented in the page.

## Editing lifecycle

The former dialog used a temporary mapping, committed by OK followed by
`Project.touch()`. The embedded equivalent is explicit Apply/Discard. Picking or
clearing a folder only updates that temporary mapping. Apply patches changed
competition mappings into the current recipe, then calls Project.touch once;
Project's existing Undo/Redo and autosave handle persistence. It does not Build or
install. Save recipe does not implicitly apply the temporary editor state.

The page keeps small in-memory drafts by project path/world name when switching
worlds. They contain trophy fields only, never rosters, players or complete project
snapshots. There is no dependency on the CUPS section-editor lifecycle. Same-world
refresh merges unedited mappings; changed assignments retain their conflict
baseline. A concurrent change to the same mapping blocks Apply without losing the
draft. Changes to unrelated mappings are preserved. Discard reads current project
values, not the values from when the page was first opened. Changing the game
tables while editing requires reviewing/reloading the draft before Apply.

Unapplied changes are labelled, retained during navigation and protected by a
Discard/Cancel warning on application close. In-memory drafts are not serialized
or automatically applied at close.

## Metadata and navigation

Use built tables from `livecpk/<recipe world>/common/etc/pesdb` when present,
otherwise the project's game tables, matching the former dialog's rule. Do not use
Project.world_tables(), which describes worlds activated in Sider. Loading is lazy
and runs in a worker; rows are cached by the relevant regulation-file stamps.
Owner/token/table checks prevent late results from populating another world.
Missing tables leave stored mappings visible and intact. Generated competitions
appear after their world's first Build. Navigation does not reconstruct the editor.

GAME CONTENT order is Balls, Commentary, Music, Trophies, Other content.
Trophies opens the embedded page, not the legacy dialog.

LEAGUES > More removes these migrated entries:

* UEFA ranking
* Trophies
* Cups of the game's countries
* Cups of our countries
* European places of the game's leagues
* First-season European clubs
* South American places

It retains only, in their original order: Pre-season cups, Competition names,
Competition IDs, League order, Seasons of the game's leagues,
and World name and file. Shared methods/dialogs remain where still used; the CUPS
editors, UEFA tools and manual qualification behavior are unchanged.

## Validation

`python tools/test_trophies_page.py` covers the embedded page, per-world drafts,
conflicts, missing/invalid references, Apply/Discard/Undo/Redo, autosave, metadata
reloads, stale workers, navigation/menu callbacks, close protection and window
sizes. Repeat with QT_SCALE_FACTOR=1, 1.25 and 1.5. A copy-only test calls the actual
trophy backend with controlled regulation metadata and verifies its files/index;
it does not Build a world. `test_trophies.ui(<pesdb>)` retains the legacy-wrapper
checks with actual tables. The existing offline Lua checks require optional lupa;
they cannot run in an environment without that test dependency.

The final page/navigation suite contains 46 checks (the earlier 47-check result
predated removal of the South American places shortcut). Previous scaling checks
covered 100%, 125% and 150%
scaling, including Spanish labels. Five legacy dialog checks pass with actual
game tables. Seven existing phase/path checks pass before the offline Lua harness
requires lupa, unavailable in this environment. Existing CUPS, qualification,
UEFA, CONMEBOL Auto Set, world, BUILD layout and navigation suites pass. No full
world Build was performed.
