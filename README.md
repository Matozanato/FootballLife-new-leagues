# FootballLife — new leagues (public beta)

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-support%20this%20work-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/mata28)

> This is unpaid reverse-engineering work done in spare time. If it is useful to you,
> **[buy me a coffee on Ko-fi](https://ko-fi.com/mata28)** — it keeps the seasons running.

Raise Football Life 2026's hard limits so that **hundreds of new clubs and dozens of new
leagues** fit into a Master League season, using only Sider modules and data files. No
patched executable, no repacked CPKs.

This is a **research beta**. It is published so that people who mod this game can test it,
break it, and tell us where. Read [what works and what does not](#status) before you
install anything, and read the [testing guide](docs/testing-guide.md) if you want to help.

## What it is

Football Life 2026 (PES 2021 engine) keeps every club, coach, competition and fixture in
fixed-size tables inside the executable's memory. Shipped, those tables hold 750 clubs, 1,300
coaches, 300 competition rulebooks and 13,000 match records. Add a few more leagues and the
data simply falls off the end: the season generator drops fixtures without a word, a saved
game loses everything past the shipped count, and a coach lookup lands on the wrong record.

This project does two things:

1. **`sider/fl26caps.lua`** — a runtime patch set of 2,688 byte changes, applied by Sider at
   startup, that grows those tables and every piece of code that indexes them:

   | table | shipped | with fl26caps |
   |---|---|---|
   | clubs | 750 | 1,600 |
   | coaches | 1,300 | 2,600 |
   | competition rulebooks (regulations) | 300 | 600 |
   | players | 30,001 | 46,193 |
   | match records per season | 13,000 | 26,000 |

   Every module verifies the bytes it is about to change and refuses to touch a different
   game build. If anything does not match, the game runs unmodified and `sider.log` says why.

2. **`tools/`** — Python scripts that build a set of new leagues and placeholder clubs
   (with squads) from **your own** game data, as a Sider `livecpk` root. No game data is
   shipped in this repository; everything is generated on your machine from your install.

Plus five small **null-guard modules** that stop known crashes in the game's own code which
the larger world exposes.

## Status

Measured on 2026-09-15 with a test world of **39 new leagues and 793 new clubs** (1,536 clubs
in total), played with a new club as the manager's team.

**Works**

- Exhibition matches between new clubs.
- Starting a Master League season with a new club in a new league: season generates,
  fixtures appear, the Team Sheet shows a real 23-man squad, the hub shows the standings.
- Saving the season and loading it back: the club, the squad, the manager's name, the
  standings and the fixtures all survive. The same save was loaded three times in a row with
  no drift, and the coach and player tables were compared byte for byte before and after.
- Advancing the calendar with matches simulated ("Skip Match"), from the start of the season (1 August)
  to at least late August (the game's day 238) in the 39-league world.
- League sizes from 14 to 33 clubs. Different sizes in the same world.
- Cups can be defined by the same tools (`mkcup.py`), but a cup in a Master League season
  is **not yet verified**.

**Does not work yet / under investigation**

- **A crash at around day 238** (late August, about four weeks in) in the 39-league world, in the game's AI
  lineup pass. It is deterministic from the same save. Two guards (`fl26nullguard4`,
  `fl26nullguard5`) stop the first two faults on that path; the third is being analysed.
  It is not known yet whether smaller worlds hit it. **This is the most useful thing to
  test right now** — see the [testing guide](docs/testing-guide.md).
- **Season generation crashes about one time in two**, in the shipped game's own code,
  regardless of these mods. Just start the season again; it is not data damage.
- Continental competitions for new clubs (Champions League slots) — not attempted.
- New clubs use **placeholder names, cloned kits and cloned squads**. This project proves the
  capacity; dressing the clubs is ordinary Team.bin / kit editing on top of it.
- New leagues appear under an **existing menu region** (England by default) because the menu
  only knows the shipped region slots. More region slots is a separate, unverified patch.
- More than 39 leagues, or leagues built with non-default ids, need a regenerated patch set
  ([why](docs/for-developers.md)).

The full list with details is in [docs/known-issues.md](docs/known-issues.md) and the hard
numbers in [docs/limits.md](docs/limits.md).

## Requirements

- Football Life 2026 with its bundled Sider (`SiderAddons` folder next to `FL_2026.exe`).
  The modules were built against `FL_2026.exe` version **26.0.0.0**, 458,910,720 bytes,
  SHA-256 `7c27ecb303b71331e36f9ccd8ac879f0f0d8c56c754bd4d0d2e9c8353464f847`. A different build
  is refused, safely, at startup.
- Python 3.10 or newer for the world-building tools. No third-party packages are needed to
  build a world. Regenerating the patch set (developers only) needs `capstone`.
- Windows. The tools were only ever run on Windows.

## Quick start

1. **Back up** your save folder
   (`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`) and your `sider.ini`.
2. Follow [docs/install.md](docs/install.md) to install the Sider modules and confirm in
   `sider.log` that every module reports `applied all`.
3. Follow [docs/build-your-world.md](docs/build-your-world.md) to extract your game's tables,
   generate a world, and point `cpk.root` at it.
4. Start an exhibition match between two new clubs, then a Master League season with one of
   them. Then read the [testing guide](docs/testing-guide.md) and report what you see.

## Reporting

Open a GitHub issue. The [testing guide](docs/testing-guide.md#what-to-send) says exactly
what to attach — in short: your `sider.log`, the crash's *fault offset* from Windows Event
Viewer, how you built your world (the `mkworld.py` line and what it printed), and the save
file if the problem is reproducible from a save.

## Layout

```
sider/     fl26caps.lua (generated patch set) and the five fl26nullguard modules
tools/     world builders (mkworld, mkplayers, mkcup ...), pesdb/CPK readers, patchset generator
patches/   the patch set as JSON plus the layout tables the generator reads
docs/      install, build-your-world, testing-guide, known-issues, limits, how-it-works,
           for-developers
```

## Support

Everything here is free and MIT-licensed. Weeks of disassembly, unattended test seasons
and crash dumps went into it, and there is more to do (the day-238 crash, cups, continental
slots, more menu regions). If you want to help it along:
**[ko-fi.com/mata28](https://ko-fi.com/mata28)**. Testing and good bug reports help just as
much — see the [testing guide](docs/testing-guide.md).

## Licence and credits

MIT — see [LICENSE](LICENSE). Football Life 2026, PES 2021 and Sider belong to their
respective authors; nothing of theirs is redistributed here.

The reverse engineering was done from scratch against the game's executable and data
files. If you use the addresses or the layout tables in your own work, a link back is
appreciated.
