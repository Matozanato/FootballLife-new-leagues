# Testing guide

The point of this beta is to find where a big world breaks. You do not need to understand
anything about the patches to help; you need patience, a fresh save slot, and the habit of
writing down what you did before something went wrong.

## Before you start

- Modules installed and `sider.log` shows six `applied all` lines ([install.md](install.md)).
- A world built and active ([build-your-world.md](build-your-world.md)), and you kept the
  `mkworld.py` output.
- Saves backed up. Use an empty save slot for testing.

## Enable crash dumps (once)

A crash in FL26 just closes the game. Two things turn that into a report we can act on.

**Event Viewer** always records it: *Windows Logs → Application*, an *Error* from
`Application Error` naming `FL_2026.exe`. The line we need is **Exception offset** (or
*Fault offset*), a hex number like `0x000000000149a6ed`. That number tells us exactly which
instruction died.

**A minidump** lets us read the crash's memory. Optional but very valuable. Enable Windows
Error Reporting local dumps once (an admin PowerShell):

```powershell
$k = "HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\FL_2026.exe"
New-Item -Path $k -Force | Out-Null
Set-ItemProperty $k DumpFolder "C:\fl26-dumps"
Set-ItemProperty $k DumpType 1 -Type DWord
Set-ItemProperty $k DumpCount 5 -Type DWord
```

Dumps then appear in `C:\fl26-dumps\` (mini dumps, tens of MB). Zip one and attach it.

## The tests, in order of usefulness

### T1 — Play past late August

*The* open problem. In our 39-league world the game dies deterministically around
**day 238** (the game's day-of-year counter; about four weeks into the season, roughly the
last week of August) in
the AI lineup pass, on a club that has no eligible player for a slot. Two guards catch the
first two faults; a third is still being worked on. We do not know yet whether smaller
worlds, bigger squads, or different sizes avoid it.

Do: start a Master League with a new club. Save after the first match. Use *Forward Time →
Skip Match* to move through the calendar, saving every few weeks into the same slot. Note
the date on the hub when it crashes.

Report: the date, your world (`mkworld.py` line + its output), the fault offset, the save
file from just before the crash, whether it crashes again from that save (load it and skip
one match). Both outcomes are useful — "crashed again at the same date" and "played through
to Christmas" alike.

Variations that would answer real questions: `--per 25` or `--per 28` (bigger squads);
fewer leagues (6, 12, 20); different sizes; a shipped club as your team instead of a new one.

### T2 — Save and load

Save a season, quit to the title screen, load it. Check: your club's name and manager under
the club header on Team Sheet, the standings panel on the hub, the four upcoming fixtures,
the squad and their ratings on the Team Sheet. Load the same save twice more.

Report anything that differs between the fresh season and the loaded one. (Until 2026-09-15
the manager's name and the standings went missing on load; that is fixed — please confirm.)

### T3 — Season generation

Start a new Master League five times in a row with a new club. Count how many generations
crash before the hub appears. Our number is about one in two, and it happens on the shipped
game as well; we want to know if it is worse or better with your world.

### T4 — Exhibition and match play

Play (not skip) an exhibition between two new clubs and, in Master League, play your own
club's match. Anything odd on the pitch, in the pre-match menus, or in the post-match
tables is worth a note. Kits will be clones of the source clubs; that is expected.

### T5 — League sizes and shapes

Build a world with `--sizes 24,22,20,18,16,14`. Check that Competition Info for each new
league states the right club count and fixture count ("Contested by 24 teams, 46 Home & Away
Fixtures"). Check the end-of-season promotion/relegation if you get that far.

### T6 — Cups (unverified territory)

`tools\mkcup.py` adds a knockout cup among your new clubs the same way `mkleague.py` adds a
league. Nobody has taken a cup through a Master League season yet. If you try, report
whether it draws, whether the rounds are dated, and whether your club is entered.

### T7 — Things we have not looked at

Transfers involving new clubs, youth teams, the Manager's Office finances of a placeholder
club, the League mode (not Master League) with a new league, and a second season. Any of
these reaching an obvious problem is a finding.

## What to send

Open a GitHub issue with:

1. **What you did**, step by step, and what you expected.
2. **`sider.log`** from that run (it is overwritten every start, so copy it right away).
3. The **fault offset** from Event Viewer, and the minidump if you enabled it.
4. Your **world**: the exact `mkworld.py` / `mkplayers.py` commands and the `mkworld.py`
   output (competition ids, regulation ids, sizes).
5. For crashes reproducible from a save: the save file
   (`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\ML0000000<n>`).
6. Screenshots of anything visual.

One issue per problem. "It crashed" with a fault offset and a save is worth more than a
paragraph of impressions without them.

## What not to report (yet)

- Placeholder names, cloned kits, cloned squads, all clubs "from England": known, by design
  for this beta.
- The one-in-two generation crash on its own, unless your rate is very different.
- Anything with other mods active. Please test with only these modules and your world.
