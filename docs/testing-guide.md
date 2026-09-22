# Testing guide

The point of this beta is to find where a big world breaks. You do not need to understand
anything about the patches to help; you need patience, a fresh save slot, and the habit of
writing down what you did before something went wrong.

If you have not installed it yet, do that first with
[step-by-step.md](step-by-step.md), which walks a stock install through to a playing season.
This file picks up where that one ends: what to try once it runs, and in what order.

## Before you start

- Modules installed and `sider.log` shows nine `applied all` lines plus `fl26joindll:
  installed` ([install.md](install.md)).
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

### T1 — Play as deep into the season as you can

Until 2026-09-16 the game died a day after matchday 1 here, every time; that was our bug and
it is fixed (see [known-issues](known-issues.md)). Since then one world here has played
**four seasons end to end**, across rollovers and New Year, with saves and loads in between.
What nobody has done is run one on a different machine, on a different install, past a few
matchdays. How far you get is the most useful number you can send us — and a long career is
still genuinely open territory, because the season's competition table only ever fills up.

Do: start a Master League with a new club. Save after the first match. Use *Forward Time →
Skip Match* to move through the calendar, saving every few weeks into the same slot. Note
the date on the hub when it crashes.

Report: the date, your world (`mkworld.py` line + its output), the fault offset, the save
file from just before the crash, and whether it crashes again from that save (load it and
skip one match). Both outcomes are useful — "crashed again at the same date" and "played
through to Christmas" alike. The shipped game also has a random crash of its own (fault
offset `0x84ed4c0`); if you see that one, load your checkpoint and carry on.

Variations that would answer real questions: `--per 25` or `--per 28` (bigger squads);
fewer leagues (6, 12, 20); different sizes; a shipped club as your team instead of a new one.

### T1b — Every added league gets its season (new on 2026-09-22)

`fl26join.dll` is one day old in public and was measured in exactly one run, on one world,
on one machine. This test is the one that tells us whether it holds up elsewhere. It takes
one season creation and a few minutes of Forward Time.

**Set-up.** Any world; the six-league default from step-by-step is fine. Start a Master
League with a club from one of the *added* leagues. Note the date the hub shows when it
first appears.

**Check, in this order, and write down each answer:**

1. **When did the season open?** August or January. January is expected when your club's
   league is one the game does not list by itself; it is not a failure, but we want to know
   which worlds produce it. (Before this module, a January season never got any matches.)
2. **`SiderAddons\fl26join.log`, first lines.** After `hooks live` you should see
   `builder 1: include list has 55 ids [...]` — the game's own creation-time list — and,
   for any of your ids the builder asked about, `door(ID) refused by us: the builder asked
   at creation; it enters via register_all instead`. That refusal is deliberate.
3. **Forward Time past the first registration day** (about two weeks into a January
   season; for an August season it is the following February — advance in *Skip Match*
   steps and watch the log). The log gains
   `register_all 1: game gave N ids [...], we appended 39 -> M (0 of ours already in a
   season)` and then one `door(ID) -> YES  ours flag on kind 1 clubs 20` per league that
   exists in your world, and `-> no ... no-record` for the listed ids your world does not
   have. **Send this block whatever it says.** A `-> no` with `flag OFF`, or a `YES` for a
   league that then has no fixtures, are the two things we most want to see.
4. **League Info for every added league**, not only yours. Each one should now state its
   fixture count and show dated rounds. Count how many of your leagues have fixtures and how
   many do not, and name the ones that do not, with their rulebook ids from `mkworld.py`.
5. **Your own league's table** starts filling from its first round (August in the
   calendar). If the season opened in January, that is a few months of Forward Time away;
   the days in between are empty for your club and that is expected.
6. **Press F10 in the game** at any point after the registration day. The module writes a
   counter line to `sider.log` of the form
   `fl26joindll: F10 report -- register_all R, ids appended A, refused X, entered E, builds B, door D (refused F, ours O)`
   — counts since the game started: registration calls seen, ids we appended, ids we
   refused at the builder, competitions that entered, builder runs, door questions. Paste
   that line into the report; it is how we tell "the hook never fired" from "it fired and
   the game said no".
7. **The second registration date** (about three months later) should add
   `register_all 2: ... (N of ours already in a season)` with N equal to the number of
   leagues that entered at the first — nothing is registered twice. If N is smaller, or a
   league appears in League Info with two sets of fixtures, that is a bug; send the log.
8. **If you reach the rollover** — the end of the season and the start of the next — what
   League Info shows for the added leagues in the new season is the single most valuable
   unknown right now. Fixtures again, nothing, or something odd: any of the three is a
   finding.

**Report:** the answers to 1–8, the whole `fl26join.log`, `sider.log`, the `mkworld.py`
output, and which club you started with. Please also say whether `fl26hdr127.lua` or the
experimental `fl26hdr192.lua` was installed.

### T2 — Save and load

Save a season, quit to the title screen, load it. Check: your club's name and manager under
the club header on Team Sheet, the standings panel on the hub, the four upcoming fixtures,
the squad and their ratings on the Team Sheet. Load the same save twice more.

Report anything that differs between the fresh season and the loaded one. (Until 2026-09-15
the manager's name and the standings went missing on load; that is fixed — please confirm.)

### T3 — Season generation

Start a new Master League five times in a row with a new club. Count how many generations
crash before the hub appears, and at which step (the manager-settings screen is where the
shipped crash strikes; the board meeting used to be a second one, fixed by
`fl26nullguard9.lua`). Our number on 2026-09-22 was three of five at the manager-settings
step, and it happens on the shipped game as well; we want to know if it is worse or better
with your world.

### T4 — Exhibition and match play

Play (not skip) an exhibition between two new clubs and, in Master League, play your own
club's match. Anything odd on the pitch, in the pre-match menus, or in the post-match
tables is worth a note. Kits will be clones of the source clubs; that is expected.

### T5 — League sizes and shapes

Build a world with `--sizes 24,22,20,18,16,14`. Check that Competition Info for each new
league states the right club count and fixture count ("Contested by 24 teams, 46 Home & Away
Fixtures"). Check the end-of-season promotion/relegation if you get that far.

### T6 — Cups

`tools\mkcup.py` adds a knockout cup among your new clubs the same way `mkleague.py` adds a
league, and a cup has now been played through a Master League season with every round dated.
It has one rule that is easy to get wrong: the game fills a cup from the **first league in its
region** — the lowest competition id — and ignores the cup's own entry list, and the shipped
cup calendar only has dates for a sixteen-club bracket. So make that feeder league a
**sixteen-club** league. With twenty, one round lands on a date that does not exist and never
plays.

Worth reporting: whether it draws, whether every round is dated, whether your club is
entered, and what happens if the feeder league is not sixteen clubs on your install.

### T7 — Things we have not looked at

Transfers involving new clubs, youth teams, the Manager's Office finances of a placeholder
club, and the League mode (not Master League) with a new league. Any of these reaching an
obvious problem is a finding. (Second and later seasons are no longer on this list — four
have been played end to end — but long careers still are: the competition table only fills
up, and nothing has been run far enough to say where it stops.)

## What to send

Open a GitHub issue with:

1. **What you did**, step by step, and what you expected.
2. **`sider.log`** from that run (it is overwritten every start, so copy it right away),
   and **`fl26join.log`** from the same folder for anything to do with leagues, fixtures or
   the start of the season (that one is appended to, not overwritten; the run you mean is
   the last `hooks live` block).
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

If this project is useful to you, you can support it at
[ko-fi.com/mata28](https://ko-fi.com/mata28).
