# For developers

Making your own version of Mod Studio: see [forking.md](forking.md) and its chapters in
[fork/](fork/): [code map](fork/code-map.md), [recipe keys](fork/recipe-keys.md),
[world file](fork/world-file.md), [modules and DLLs](fork/modules.md) (including the 0.2.0
`-calendar` constants and what to do when the game exe changes), [building](fork/building.md),
[testing](fork/testing.md), [NewLife release format](fork/newlife-format.md).

## Requirements

- Football Life 2026 with its bundled Sider (`SiderAddons` folder next to `FL_2026.exe`).
  The modules were built against `FL_2026.exe` version **26.0.0.0**, 458,910,720 bytes,
  SHA-256 `7c27ecb303b71331e36f9ccd8ac879f0f0d8c56c754bd4d0d2e9c8353464f847`. A different build
  is refused, safely, at startup.
- Python 3.10 or newer for the world-building tools. No third-party packages are needed to
  build a world. Regenerating the patch set needs `capstone`.
- FL26 Mod Studio from source (`python tools/modstudio_main.py`) needs `PySide6`, `Pillow` and
  `py7zr`; making the release zip (`tools/mszip.py`) also needs `pyinstaller`, `markdown` and
  zig for the DLLs. The release `.exe` needs nothing.
- Windows. The tools were only ever run on Windows.

## Repository layout

```
sider/              fl26caps.lua (generated patch set), the null guards, fl26hdr127.lua,
                    fl26joindll.lua and the compiled fl26join.dll it loads
sider/experimental/ seventeen modules that go further: 192 competitions, the Select Team
                    list (names, slots, club lists, flags, Kick Off order), 64 regions, a
                    3-bit league rank and its relegation gate, an August start, season-end
                    promotion through a pyramid (fl26chain.dll), Super Cup, results-screen and
                    club-change guards, the 2024 European format, league sizes, split
                    seasons and other continents' cups (fl26swiss.dll), country names in
                    Competition Info, the added leagues in Edit mode's team lists
tools/              world builders (mkworld, mkplayers, mkcrests, mkkits, mkcup, mkflags,
                    mkreshape, mkuecl, mkeuropo, mksizes, mktactics, rename, players,
                    playeredit, playereditor ...), pesdb/CPK readers, the patch-set generator
                    and its checkers
tools/modstudio/    FL26 Mod Studio (tools/modstudio_main.py starts it from source,
                    tools/mszip.py makes the release zip) and the League Builder behind it
                    (leaguebuilder, lbplayers, lbfaces, lbpackage, lbpack ...)
tools/native/       the C source of the six DLLs, their build scripts and checksums
patches/            the patch set as JSON plus the layout tables the generator reads
guides/<lang>/      the user guides: install-a-pack, make-your-own-leagues, mod-studio-guide
                    (en, hr, es, pt; fr has mod-studio-guide only), and README.md, the picker
docs/               faq, known-issues, and README.md, the index
docs/changelog/     the release notes and the version history
docs/developers/    for-developers, forking, mod-studio (how it works, package format),
                    by-hand (the manual route with Python), testing-guide
docs/developers/fork/ the fork chapters: code-map, recipe-keys, world-file, modules,
                    building, testing, newlife-format, club-world-cup-32
docs/research/      research-findings (the research log), how-it-works, limits,
                    league-phase-swiss-decode, player-record
```

## FL26 Mod Studio and the world file

The modules read which leagues a world has from `SiderAddons\modules\fl26world.txt`, written
by the League Builder (FL26 Mod Studio, `tools/leaguebuilder.py`). A module that finds no file
keeps its built-in list. The format, what the program touches in the game folder, and the
league package format (`.fl26pack`) are in [mod-studio.md](mod-studio.md).

## Regenerating the patch set

You need to regenerate `fl26caps.lua` when your world's rulebook ids are not all in the
shipped date table (more than 39 leagues built with `mkworld.py`, a non-default `--reg-from`,
a data pack that already uses some of those ids), or when you change a cap.

Requirements: Python 3.10+, `pip install capstone`, the game exe reachable through
`FL26_DIR` (or `FL26_EXE`), and this repository's `patches/` and `sider/fl26caps.template.lua`.

The shipped set (0.2.2, 3510 patches, 792 matches a calendar day, 61,905 players) was generated with (keys 197–255 are the regulation ids the league builder hands a league once
the game's free ids are gone, from 255 down, see `EXTRA_IDS` in `tools/fl26world.py`; the same list is recorded in `patches/<set>.json`, and running
this reproduces the shipped `fl26caps.lua` patch for patch):

```
python tools\patchset.py teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar ^
    --player-cap 61905 ^
    --date-keys 11,49,60,61,62,74,76,93,94,96,98,100,109,110,111,112,113,114,121,138,139,140,143,144,145,146,170,171,173,174,176,178,179,180,181,182,183,184,185,190,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,229,228,227,226,225,224,223,222,221,220,219,218,217,216,215,214,213,212,211,210,209,208,207,206,205,204,203,202,201,200,199,198,197 ^
    --date-offsets 11:1,49:2,60:1,61:2,62:5,74:5,76:2,93:6,94:2,96:2,98:4,100:1,109:1,110:1,111:1,112:4,113:5,114:2,121:2,138:2,139:2,140:2,143:5,144:2,145:2,146:6,170:4,171:6,173:1,174:0,176:1,178:6,179:4,180:0,181:1,182:5,183:1,184:6,185:1,190:2,255:0,254:1,253:2,252:3,251:4,250:5,249:6,248:0,247:1,246:2,245:3,244:4,243:5,242:6,241:0,240:1,239:2,238:3,237:4,236:5,235:6,234:0,233:1,232:2,231:3,230:4,229:5,228:6,227:0,226:1,225:2,224:3,223:4,222:5,221:6,220:0,219:1,218:2,217:3,216:4,215:5,214:6,213:0,212:1,211:2,210:3,209:4,208:5,207:6,206:0,205:1,204:2,203:3,202:4,201:5,200:6,199:0,198:1,197:2 ^
    --cup-keys 186
```

The `-calendar` part widens every calendar day from 280 to 792 match ids (`tools/calwiden.py`,
fed by `patches/calendar-sites.json` and `patches/calendar-tail-sites.json`) and moves the
calendar unit to the top of the edit block, so a career saved under the older
`...-fixtures` set does not load under it. `python tools\calaudit.py patches\<set>.json`
re-checks every calendar reference of the exe against the set. Leave `-calendar` off for the
older layout; the DLLs then need `-DREG_ARRAY_OFF=0x1c84230` (see `tools/native/`).

`--calendar-ids N` asks for another day size (the copier steps in 0x80-byte blocks, so the
sizes are 536, 792, 1048, 1304 ...; 792 is what ships). A big world can need it: a world of
about sixty leagues measured 733-796 matches on its busiest days, past 792. Any size other
than 792 moves the fields past the calendar and the arrays above it, so the modules that read
them by block offset need new constants. The generator prints them:

```
regulations array moves to +0x...                       -> REG_ARRAY_OFF (fl26join, fl26chain)
module constants for this layout: fl26swiss TODAY_OFF 0x..., fl26join TODAY_OFF 0x...,
fl26ctlguard controller table block+0x..., owner handle block+0x...
```

Build the DLLs with those `-D...` values and change the two fl26ctlguard offsets (see
[fork/modules.md](fork/modules.md), "Module constants that changed with it"). A career made
under one size does not load under another.

- `--date-keys` are the rulebook ids of your new leagues (the `regulation ids` line of
  `mkworld.py`). They must be within 1–255. **Passing them is not optional in practice.**
  Leave the flag off and the generator falls back to a single test league: every other
  league's matches are then allocated with no date, nothing ever puts them on a calendar
  day, and those leagues quietly play nothing from the second season onward. That is
  exactly how the set published on 2026-09-16 shipped broken; see
  [known-issues.md](../known-issues.md). The generator now says out loud when it falls back.
- `--date-offsets` assigns each key a weekday shift 0–6. A bare list (`--date-offsets 2,6,5,1`)
  deals shifts round-robin; the `key:shift` form above assigns them one by one. Spreading
  leagues over the emptier weekdays is what keeps the 792-ids-per-day calendar (280 without `-calendar`) from
  overflowing; an even deal is not always the flattest.
- `--cup-keys` gives a regulation a cup's calendar instead of a league's (186 is the
  Conference League's regulation in a world built with `mkuecl.py`).
- `--player-cap` must satisfy `cap ≡ 17 (mod 32)` because of how the second copy is
  memcpy'd; the generator refuses anything else and tells you the nearest valid value.

The generator writes `patches/<set>.json` and `sider/fl26caps.lua`. It refuses to emit a set
while any table reference is unattributed, and it runs two checks that each exist because of
a real load-path bug:

- `check_biased()` — the pre-biased displacements inside the save/load copy code must agree
  with one another (the bug behind "the manager's name disappears after a load").
- `check_copy_fields()` — every occurrence, anywhere in the code section, of an offset the
  copy moves must be either patched or named in `copy.mlcopy.field_scan_allow` with a reason.
  This is what the accessor `0x140af3680` slipped through: its index bounds were raised while
  the base displacements beside them kept the shipped layout, and a loaded season then wrote
  regulation records over the team array.

## What the set name means

`teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar` (3510 patches in 0.2.2): each part is a family of patches
in `layout.json` — grow the team table and relocate it; grow coaches; grow regulations;
raise the player cap in place; install the date-spread stub (since 0.1.7 on a page of its own
at `0x163000000`, which `fl26caps` reserves before it writes); grow the match record table;
relocate the "upper belt" of small tables after it; grow the Master League save/load copy
(`mlcopy`); grow the global fixture table from 2000 to 8000 rounds (`fixtures`); widen every
calendar day from 280 to 792 match ids and move the calendar unit to the top of the edit block
(`calendar`, 0.2.0). Smaller sets exist for bisection but are not shipped here.

## Reading a crash

A fault offset from Event Viewer plus `0x140000000` is the absolute address. Sections:
`.trace` (game code) is where every crash we could reason about lives; `0x1484ed4c0` is
outside it and is the shipped generation crash (it also happens with none of our modules and
no patch set; see known-issues.md). The guards' headers (`fl26nullguard*`, `fl26superguard`, `fl26resultsguard`, `fl26ctlguard`) describe the
disassembly around each guarded site, and the crash table in known-issues.md lists what is
open.

If you enabled minidumps, a stack of return addresses in `.trace` plus the register set is
usually enough to attribute a crash to a table walk; the record strides worth knowing are
players 0x17c, clubs 0x690, coaches 0x258, regulations 0x314, match records 0x254 (596).

## Tools in this repository

| tool | purpose |
|---|---|
| `pesdb.py` | read/write the WESYS-wrapped pesdb tables, record access |
| `cpk.py`, `cpkx.py`, `wesys.py` | list and extract CPK archives; unpack one WESYS file |
| `mkworld.py` | build N leagues of placeholder clubs (and their managers) into a livecpk root |
| `mkleague.py`, `mkteams.py` | the single-league and clubs-only builders mkworld wraps |
| `mkplayers.py` | placeholder squads for the new clubs |
| `mkcoaches.py` | a manager of its own for every new club, for a world built before `mkworld.py` wrote `Coach.bin` |
| `mkcup.py` | a knockout cup among chosen clubs |
| `rename.py` | list the clubs of a world, or rename them (name and abbreviation) or their managers from a CSV file |
| `players.py` | list the players of a world or one club, and change a player's name, shirt number, or copy the playing side (position, abilities, skills) from another player |
| `playeredit.py` | the player editor: export a club (or everything) to CSV with every field by name, import it back with range checks, create new players; field map in [player-record.md](../research/player-record.md) |
| `playereditor.py` | the same editor with a window (tkinter): club list, squad in lineup order, every field in tabs, new players, save |
| `siderroot.py` | switch which `_FL26*` cpk.root is active |
| `patchset.py` + `callindex.py`, `datecave.py`, `copyfields.py`, `impscan.py`, `calwiden.py`, `boundscan.py` | the patch set generator and its helpers (`calwiden.py` widens the calendar for the `-calendar` set; `calaudit.py`, `calstride.py`, `tailscan.py` find and check its sites) |
| `flpaths.py` | where your game is; environment variables |
| `livedump.py` | locate the running game and read its edit block; the reader the next tool needs |
| `dayplan.py` | measure a running season and print the `--date-offsets` day-spread that clears the per-day ceiling (792, or 280 without `-calendar`); reads `FL26_SET`/`--set` for the layout |
| `deepen.py` | put one of your leagues below another as the next division down; `--deep-rank` for real ranks, `--retier` to renumber a chain built before the rank was widened |
| `mkrankpatch.py` | regenerate `sider/experimental/fl26rank.lua` (it finds every site that reads or writes the league rank and emits the same-length rewrite); needs `capstone` |
| `spreadregions.py` | give every added league a region (country) of its own, `--plan own`; needs `sider/experimental/fl26reg64.lua` in the game |
| `mkflags.py` | give every added league its country's flag: works the country out from the league's name (or a `--countries` list) and `Country.bin`, and writes `ID_COUNTRY` in `fl26comptab.lua` and `COUNTRY` in `fl26catlist.lua`. Based on Stagnant09's version (issue #11) |
| `mkphases.py`, `mkreshape.py` | clone a multi-phase competition; change the shape of a phase of a shipped one in place (the 36-club league phase) |
| `mkuecl.py`, `mkeuropo.py` | add the Conference League; give the Europa and Conference League the 9-24 play-off |
| `mkswiss.py` | generate and check the league-phase draw tables compiled into `fl26swiss.dll` |
| `mksizes.py` | set each added league's club count and how many times the clubs meet (you write the plan; format at the top of the script) |
| `native/fl26join.c`, `native/fl26clubs.c`, `native/fl26chain.c`, `native/fl26swiss.c`, `native/fl26regen.c`, `native/fl26edit.c` and their build scripts | the sources of the six DLLs and the one-line `zig cc` build; see [native/README.md](../../tools/native/README.md) and [fork/building.md](fork/building.md) |

Tools we use in development but did not include: the automation harness that plays seasons
unattended with a virtual pad and screen reading, and the disassembly indices. They are tied
to one machine and would mislead more than help. `livedump.py` is the one reader that is
here, because `dayplan.py` cannot work without it and the day-spread problem is one every
large world runs into. It reads the running game only; it writes nothing.

## Contributing

Issues with fault offsets, saves and `mkworld.py` output are the most valuable thing right
now. Pull requests are welcome for anything, fixes and new features alike: we test them and
merge them into the next release (how: [Contributing](../../README.md#contributing)). For
`sider/` and `patches/`, please describe the disassembly evidence in the PR the way the module
headers do.
