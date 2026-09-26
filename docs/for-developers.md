# For developers

## Regenerating the patch set

You need to regenerate `fl26caps.lua` when your world's rulebook ids are not all in the
shipped date table (more than 39 leagues, a non-default `--reg-from`, a data pack that
already uses some of those ids), or when you change a cap.

Requirements: Python 3.10+, `pip install capstone`, the game exe reachable through
`FL26_DIR` (or `FL26_EXE`), and this repository's `patches/` and `sider/fl26caps.template.lua`.

The shipped set was generated with:

```
python tools\patchset.py teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures ^
    --player-cap 51729 ^
    --date-keys 11,49,60,61,62,74,76,93,94,96,98,100,109,110,111,112,113,114,121,138,139,140,143,144,145,146,170,171,173,174,176,178,179,180,181,182,183,184,185,190 ^
    --date-offsets 11:1,49:2,60:1,61:2,62:5,74:5,76:2,93:6,94:2,96:2,98:4,100:1,109:1,110:1,111:1,112:4,113:5,114:2,121:2,138:2,139:2,140:2,143:5,144:2,145:2,146:6,170:4,171:6,173:1,174:0,176:1,178:6,179:4,180:0,181:1,182:5,183:1,184:6,185:1,190:2 ^
    --cup-keys 186
```

- `--date-keys` are the rulebook ids of your new leagues (the `regulation ids` line of
  `mkworld.py`). They must be within 1–255. **Passing them is not optional in practice.**
  Leave the flag off and the generator falls back to a single test league: every other
  league's matches are then allocated with no date, nothing ever puts them on a calendar
  day, and those leagues quietly play nothing from the second season onward. That is
  exactly how the set published on 2026-09-16 shipped broken; see
  [known-issues.md](known-issues.md). The generator now says out loud when it falls back.
- `--date-offsets` assigns each key a weekday shift 0–6. A bare list (`--date-offsets 2,6,5,1`)
  deals shifts round-robin; the `key:shift` form above assigns them one by one. Spreading
  leagues over the emptier weekdays is what keeps the 280-ids-per-day calendar from
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

`teams-coaches-regs-players-dates-matches-upper-mlcopy`: each part is a family of patches
in `layout.json` — grow the team table and relocate it; grow coaches; grow regulations;
raise the player cap in place; install the date-spread stub; grow the match record table;
relocate the "upper belt" of small tables after it; grow the Master League save/load copy
(`mlcopy`). Smaller sets exist for bisection but are not shipped here.

## Reading a crash

A fault offset from Event Viewer plus `0x140000000` is the absolute address. Sections:
`.trace` (game code) is where every crash we could reason about lives; `0x1484ed4c0` is
outside it and is the shipped generation crash (it also happens with none of our modules and
no patch set; see known-issues.md). The five guards' headers describe the
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
| `playeredit.py` | the player editor: export a club (or everything) to CSV with every field by name, import it back with range checks, create new players; field map in [player-record.md](player-record.md) |
| `playereditor.py` | the same editor with a window (tkinter): club list, squad in lineup order, every field in tabs, new players, save |
| `siderroot.py` | switch which `_FL26*` cpk.root is active |
| `patchset.py` + `callindex.py`, `datecave.py`, `copyfields.py`, `impscan.py`, `calwiden.py`, `boundscan.py` | the patch set generator and its helpers (`calwiden.py` is only used by the unpublished calendar-widening set, but the generator imports it) |
| `flpaths.py` | where your game is; environment variables |
| `livedump.py` | locate the running game and read its edit block; the reader the next tool needs |
| `dayplan.py` | measure a running season and print the `--date-offsets` day-spread that clears the 280-per-day ceiling |
| `deepen.py` | put one of your leagues below another as the next division down; `--deep-rank` for real ranks, `--retier` to renumber a chain built before the rank was widened |
| `mkrankpatch.py` | regenerate `sider/experimental/fl26rank.lua` (it finds every site that reads or writes the league rank and emits the same-length rewrite); needs `capstone` |
| `spreadregions.py` | give every added league a region (country) of its own, `--plan own`; needs `sider/experimental/fl26reg64.lua` in the game |
| `mkphases.py`, `mkreshape.py` | clone a multi-phase competition; change the shape of a phase of a shipped one in place (the 36-club league phase) |
| `mkuecl.py`, `mkeuropo.py` | add the Conference League; give the Europa and Conference League the 9-24 play-off |
| `mkswiss.py` | generate and check the league-phase draw tables compiled into `fl26swiss.dll` |
| `mksizes.py` | set each added league's club count and how many times the clubs meet (you write the plan; format at the top of the script) |
| `native/fl26join.c`, `native/fl26clubs.c`, `native/fl26chain.c`, `native/fl26swiss.c` and their build scripts | the sources of the four DLLs and the one-line `zig cc` build; see [native/README.md](../tools/native/README.md) |

Tools we use in development but did not include: the automation harness that plays seasons
unattended with a virtual pad and screen reading, and the disassembly indices. They are tied
to one machine and would mislead more than help. `livedump.py` is the one reader that is
here, because `dayplan.py` cannot work without it and the day-spread problem is one every
large world runs into. It reads the running game only; it writes nothing.

## Contributing

Issues with fault offsets, saves and `mkworld.py` output are the most valuable thing right
now. Pull requests are welcome for anything in `tools/`; for `sider/` and `patches/`,
please describe the disassembly evidence in the PR the way the module headers do.
