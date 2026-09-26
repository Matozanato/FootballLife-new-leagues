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

### T8 — The experimental modules (the menus, the regions, the rank)

Eight modules in `sider\experimental\` were built and verified against the executable on
21-22 September, and `fl26editlist` on 26 September, and watched working in the menus of a
running game. **None of them has been
through a season.** That gap is the whole reason they are published, and this is the test
that closes it. Read
[sider/experimental/README.md](../sider/experimental/README.md) first — several depend on
each other, and two carry a slot list you must fill in from your own world.

Add them **one at a time**, in the order that file gives, starting the game and reading
`sider.log` after each. A module that finds bytes it does not recognise writes nothing and
says so; that log line is a useful report on its own, because it means your install differs
from ours and names where.

**T8a — Select Team (`fl26comptab`, then `fl26slotnames`, then `fl26clubs`).** Open the team
selection list for Master League and for Kick Off.

1. Are all of your leagues in the list, or only some? Name the ones missing, with their
   rulebook ids.
2. Does each of your leagues sit under a **heading that makes sense**, or under a shipped
   one ("Classic Teams", "Other European Leagues", "Asia-Oceania") over a league of yours?
   And the other way round: is any **heading blank**? A slot with no league of yours on it
   should keep the heading it always had.
3. Does each show **its own twenty clubs**, or national teams, foreign clubs, or an empty
   list?
4. Pick a club from one of them and start a season. It has to be selectable *and* playable;
   the list is built separately from the season.
5. Send the `fl26comptab: id N -> row R slot S` lines from `sider.log` with your answers.
   They are the map from your leagues to the slots the other two modules act on.

**T8b — Regions (`fl26reg64`).** Build a world spread over several regions, including at
least one above 28, e.g.
`python tools\mkworld.py --base %FL26_PESDB% --out <root> --leagues 9 --regions 16,20,30`.

1. Do the leagues appear grouped by region in the competition lists?
2. A region above 24 has no heading of its own and borrows the previous country's name —
   expected, and worth confirming rather than reporting as a surprise. Which name did it
   borrow?
3. Without the module, a league on a region of 29 or more falls back to the default region
   instead. Confirming that difference in your install is a useful result.

**T8c — Deep pyramids (`fl26rank` + `fl26deeprank`, with `fl26deep4` off).** Build a pyramid
four or five divisions deep, either with `--tiers` or with `tools\deepen.py --deep-rank`;
if you built it before installing `fl26rank.lua`, run `python tools\deepen.py --root <root>
--retier <top league ids>` first.

1. **League Info for each division.** It should name the league above and the league below
   correctly. The symptom this fixes is a fourth division showing *itself* as its own lower
   league.
2. **Play to the end of a season and let it roll over.** Then: did anybody actually go up or
   down, in which divisions, and how many clubs? This is the unanswered question — the gate
   is fixed, the movement has never been watched.
3. If nothing moves, say so with the divisions and their ranks. That is as useful as
   movement, and it is what we expect to need next.

**T8d — 192 competitions (`fl26hdr192`).** Only worth testing on a long career: the count of
competitions a season holds only ever rises, and 127 was reached at 124 after four seasons
here. Report the season number and whether league tables still start from zero after each
rollover. Remember it replaces `fl26hdr127.lua` and that switching between them means
starting a new season.

**T8e — Edit mode (`fl26editlist`, after `fl26comptab`).** Move your old `EDIT00000000` aside
first (see the FAQ). Open Edit > Teams, Edit > Players > Edit Player, Transfer and Managers.

1. Is every league of yours in the list? Name the ones missing, with their rulebook ids, and
   send the `fl26editlist: N more league headings ..., slots ...` line from `sider.log`.
2. Does each open with its own clubs, and each club with its own squad?
3. Is the "Other" heading still there (it should be, just before the block of your leagues)?
   In Managers: does each of your clubs have its own manager (`FL M0001`, `FL M0002`, ...)?
   If they all say "Jorge Jesus", your world has no `Coach.bin` yet: see the FAQ.
4. Change something small on one of your clubs, save the Edit data, restart: is it kept?
   (Move that Edit save aside again before you rebuild your world, or it hides the rebuild.)

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
- Cosmetic gaps in the experimental modules that their README already states: a region above
  24 borrowing a country's heading, a league above the slot ceiling still missing from Select
  Team. Report what the README does *not* already say.

If this project is useful to you, you can support it at
[ko-fi.com/mata28](https://ko-fi.com/mata28).
