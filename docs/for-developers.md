# For developers

## Regenerating the patch set

You need to regenerate `fl26caps.lua` when your world's rulebook ids are not all in the
shipped date table (more than 39 leagues, a non-default `--reg-from`, a data pack that
already uses some of those ids), or when you change a cap.

Requirements: Python 3.10+, `pip install capstone`, the game exe reachable through
`FL26_DIR` (or `FL26_EXE`), and this repository's `patches/` and `sider/fl26caps.template.lua`.

The shipped set was generated with:

```
python tools\patchset.py teams-coaches-regs-players-dates-matches-upper-mlcopy ^
    --player-cap 46193 ^
    --date-keys 11,12,13,49,60,61,62,63,64,65,66,69,70,71,72,73,74,75,76,77,78,93,94,96,98,100,101,102,109,110,111,112,113,114,121,138,139,140,143 ^
    --date-offsets 11:6,12:5,13:6,49:1,60:2,61:2,62:5,63:6,64:5,65:5,66:2,69:1,70:5,71:4,72:1,73:5,74:2,75:2,76:5,77:5,78:0,93:2,94:2,96:2,98:1,100:2,101:3,102:6,109:1,110:0,111:5,112:1,113:2,114:5,121:1,138:1,139:2,140:3,143:6
```

- `--date-keys` are the rulebook ids of your new leagues (the `regulation ids` line of
  `mkworld.py`). They must be within 1–255.
- `--date-offsets` assigns each key a weekday shift 0–6. A bare list (`--date-offsets 2,6,5,1`)
  deals shifts round-robin; the `key:shift` form above assigns them one by one. Spreading
  leagues over the emptier weekdays is what keeps the 280-ids-per-day calendar from
  overflowing; an even deal is not always the flattest.
- `--player-cap` must satisfy `cap ≡ 17 (mod 32)` because of how the second copy is
  memcpy'd; the generator refuses anything else and tells you the nearest valid value.

The generator writes `patches/<set>.json` and `sider/fl26caps.lua`. It refuses to emit a set
while any table reference is unattributed, and it now fails if the pre-biased displacements
inside the save/load copy code disagree with each other (the bug behind the "manager's name
disappears after a load" symptom).

## What the set name means

`teams-coaches-regs-players-dates-matches-upper-mlcopy`: each part is a family of patches
in `layout.json` — grow the team table and relocate it; grow coaches; grow regulations;
raise the player cap in place; install the date-spread stub; grow the match record table;
relocate the "upper belt" of small tables after it; grow the Master League save/load copy
(`mlcopy`). Smaller sets exist for bisection but are not shipped here.

## Reading a crash

A fault offset from Event Viewer plus `0x140000000` is the absolute address. Sections:
`.trace` (game code) is where every crash we could reason about lives; `0x1484ed4c0` is
outside it and is the shipped generation crash. The five guards' headers describe the
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
| `mkworld.py` | build N leagues of placeholder clubs into a livecpk root |
| `mkleague.py`, `mkteams.py` | the single-league and clubs-only builders mkworld wraps |
| `mkplayers.py` | placeholder squads for the new clubs |
| `mkcup.py` | a knockout cup among chosen clubs |
| `siderroot.py` | switch which `_FL26*` cpk.root is active |
| `patchset.py` + `callindex.py`, `datecave.py`, `copyfields.py` | the patch set generator and its helpers |
| `flpaths.py` | where your game is; environment variables |

Tools we use in development but did not include: the automation harness that plays seasons
unattended with a virtual pad and screen reading, the live memory readers, and the
disassembly indices. They are tied to one machine and would mislead more than help.

## Contributing

Issues with fault offsets, saves and `mkworld.py` output are the most valuable thing right
now. Pull requests are welcome for anything in `tools/`; for `sider/` and `patches/`,
please describe the disassembly evidence in the PR the way the module headers do.
