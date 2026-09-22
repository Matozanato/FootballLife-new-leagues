# Build your world

This generates a Sider `livecpk` root holding new leagues, new placeholder clubs and
placeholder squads, built from **your own** game's tables. Three steps: extract, generate,
activate.

The clubs are deliberately placeholders — `FL League 03`, `FL 0042`, players `FL P17021` —
because the point of this beta is to find out where the game breaks with a lot of them.
Naming and dressing them is ordinary Team.bin and kit editing on top of the same files.

## 1. Extract the pesdb tables from your game

The tables live inside the game's CPK archives under `common/etc/pesdb/`. The tools read
them from a plain folder, so unpack once:

```
python tools\cpkx.py "C:\Football Life 2026\download\<data cpk>" C:\work\pesdb
```

Which CPK holds the current tables depends on your install; the newest data pack wins. Look
for one whose listing (`python tools\cpk.py <file>`) contains `common/etc/pesdb/Team.bin`.
After extraction, `C:\work\pesdb\common\etc\pesdb\` must contain at least:

```
Competition.bin  CompetitionRegulation.bin  CompetitionEntry.bin
Team.bin  Player.bin  PlayerAssignment.bin
```

Tell the tools where things are (a `.bat` or your shell profile is the convenient place):

```
set FL26_DIR=C:\Football Life 2026
set FL26_PESDB=C:\work\pesdb\common\etc\pesdb
```

## 2. Generate leagues, clubs and squads

Two commands. The first builds clubs and competitions, the second gives every new club a
squad. `--out` is the livecpk root; put it under `SiderAddons\livecpk\` with a name that
sorts to the top, for example `_FL26World`.

```
python tools\mkworld.py   --base %FL26_PESDB% --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --leagues 6 --clubs 20
python tools\mkplayers.py --base %FL26_PESDB% --out "C:\Football Life 2026\SiderAddons\livecpk\_FL26World" --per 30 --cap 51729
```

What the options mean:

| option | default | notes |
|---|---|---|
| `--leagues N` | 6 | how many new leagues |
| `--clubs M` | 20 | clubs per league |
| `--sizes A,B,C` | | different sizes, cycled over the run, e.g. `--sizes 24,22,20,18` (10–30 all work; above 30 the round list runs out) |
| `--region N` | 16 | which existing menu region the leagues appear under (16 = England's slot) |
| `--cid-from N` | 130 | first competition id; leave it |
| `--reg-from N` | 1 | first rulebook id, handed out from the free list; **leave it** (see below) |
| `--cap` (mkplayers) | 30001 | must be **51729** with this patch set; it is the player table size |
| `--per` (mkplayers) | 23 | players per club; the budget is 51,729 − 27,927 shipped = 23,802 players ≈ 793 squads of 30, so `--per 30` fits a 39-league world |

`mkworld.py` prints what it did. **Keep that output** — it lists the competition ids and
rulebook ids it used, and you will need it for the check below and for any bug report:

```
competition ids 130, 131, 132, 133, 134, 135
regulation  ids 11, 12, 13, 49, 60, 61
  FL League 01     competition 130  regulation 11   20 clubs 1001-1020
  FL League 02     competition 131  regulation 12   20 clubs 1021-1040
  ...
  wrote Team.bin (863 records)

6 leagues, 120 clubs added; 863 clubs in all
```

(The summary lines show the first eight ids; the per-league lines below them always show
every league's ids.)

### The one check that matters: rulebook ids

A new league gets its fixture dates from a small table inside `fl26caps.lua`, keyed by the
league's **rulebook (regulation) id**. A league whose id is not in that table is never
scheduled: it appears in the menus, you can pick a club from it, and the season generator
simply gives it no matches. The shipped `fl26caps.lua` covers these 39 ids:

```
11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121
138 139 140 143 144 145 146 170 171 173 174 176 178 179 180 181 182 183 184 185
```

`mkworld.py` hands rulebook ids out from the bottom of the free list, so with an unmodified
FL26 install and the default `--reg-from`, the first 39 leagues you build get exactly these
ids. **Compare the `regulation` column of the per-league lines with the list above.** If every id is in
the list, you are fine. If not — more than 39 leagues, a different `--reg-from`, or a data
pack that already uses some of these ids — that league will not be scheduled, and you need a
regenerated patch set: see [for-developers.md](for-developers.md).

The same 39 ids are listed a second time, in `sider/fl26joindll.lua` (`local IDS = { ... }`
near the top). That list says which leagues the module presents to the season on the first
registration day; a league that is dated but not in it is entered only if the game lists it
by itself, which a league standing in a country of its own is not (see
[how-it-works.md](how-it-works.md)). If you changed the ids, edit that list too — it is a
plain text edit, no regeneration needed. Ids in the list that your world does not use are
harmless; the log notes them as `no-record` and moves on.

Why an id decides this at all is explained in [how-it-works.md](how-it-works.md): the dates
come from a switch compiled into the executable, keyed by the id, and most free ids land on
an entry that writes nothing.

### If you build many leagues: spread them over the week

A calendar day holds **280 matches** and the scheduler drops the rest without a word. No
error, no log line, nothing in the world files — a league just plays one round fewer than it
should. Each new league is given a shift of 0 to 6 days so that they do not all want the
same weekday, and the shipped set already carries a spread measured on a 39-league world.

Past about 39 leagues you need your own. `tools/dayplan.py` reads a running season out of
the game, separates the shipped competitions' load from each of your leagues', and prints
the `--date-offsets` argument for `patchset.py` that makes the busiest day as quiet as it
can be:

```
python tools/dayplan.py --set <your set name>
python tools/dayplan.py --set <your set name> --demand   # after the first rollover
```

Then regenerate the set with what it printed and create the season again. Use `--demand`
once a world has rolled over: walking the calendar only counts the matches that were
accepted, so a day that turned matches away still reads as a tidy 280, while the match
records show what was really wanted.

### Sizes worth knowing

Our largest built world: **39 leagues, 793 clubs**, built with `--leagues 39` and sizes
around 20; the world that has been played across four seasons is 39 leagues of exactly 20,
780 clubs. Bigger is possible on paper (1,600 club slots) but **1,536 clubs in total is a
hard wall** in the season generator, and a calendar day holds 280 match ids at most, so the
scheduler runs out of room somewhere past 39 leagues on the same weekdays. Start smaller.
A world of 6 leagues × 20 clubs is a fine first test; 12 leagues with `--sizes 24,22,20,18,16,14`
is a good second.

## 3. Activate the root in sider.ini

Only one such world may be active at a time. Near the top of `sider.ini`, with the other
`cpk.root` lines, add yours **above** the others so it takes precedence:

```ini
cpk.root = ".\livecpk\_FL26World"
```

`tools\siderroot.py _FL26World` does this for you: it comments out every other `_FL26*`
root and enables the one you name, then prints what is active.

To try a different world, build it into a different folder and switch the root line. To go
back to the shipped game, comment the line out. **Delete or move your Master League save
between worlds**: a save carries the club table of the world it was made in.

## 4. Look at it

- Exhibition: both new clubs should be selectable under the region you chose (England by
  default), with placeholder names, and the match should kick off with 22 players in the
  cloned kits.
- Master League: pick a club from a new league, pick a manager; the season should generate
  (retry once or twice if it crashes during generation — see known-issues), and the hub
  should show the standings of your league on the right and four fixtures at the bottom.

### Divisions, and why they matter more than they look

Every league these tools build is a copy of a first-division prototype, which means that by
default **all of your leagues are first divisions**. Two consequences, both measured:

* a first division in a region is offered European places by the engine, so your new clubs
  can turn up in the Champions League;
* the promotion resolver only looks for the league above when the lower league is division 2
  or 3, so three leagues linked as a pyramid but all left as division 1 will never promote
  or relegate anybody.

```
python tools\mkworld.py --base %FL26_PESDB% --out <root> --leagues 9 --tiers 1,2,3 --group-regions 3
```

`--tiers` cycles over the run, `--group-regions` says how many consecutive leagues share a
region -- so the line above builds three three-division pyramids, each one inside its own
region, which is the shape the engine understands. The division *number* stops at three, but
a pyramid does not have to: see [limits.md](limits.md).

`tools\deepen.py` does the other version of this: it takes one of your leagues and puts it
**underneath an existing pyramid**, one division lower -- France and Italy each ship two --
copying the parent's region and calendar shape and writing the promotion link both ways. Run
it again on the league it just made and you get a fourth division, and again for a fifth:

```
python tools\deepen.py --root <root> --league 60 --below 81   # your league becomes Ligue 3
python tools\deepen.py --root <root> --league 61 --below 60   # and this one Ligue 4
```

Anything below the third division promotes upwards out of the box but is never relegated
into, until you install `sider/experimental/fl26deep4.lua` -- one verified byte that makes the engine's
second relegation gate accept a third division as well as a second. `deepen.py` says so when
it builds one. Be aware that this is the one tool here that writes into a shipped
competition's own record (the parent's relegation pointer), in your livecpk copy of the
table. Nothing is replaced, but Ligue 2's bottom clubs now have somewhere to fall.

### Crests and kits, if you want them to look like sides

Every new club is a clone, so in the game it wears the crest and the kit of the club it was
cloned from. Two tools fix that, and neither touches a shipped file: both only write files
for ids no shipped file uses.

```
python tools\mkcrests.py --team-bin <your root>\common\etc\pesdb\Team.bin --flags <your root>
python tools\mkkits.py   --team-bin <your root>\common\etc\pesdb\Team.bin --unipar <UniformParameter.bin> --root <your root>
```

`mkcrests.py` draws a distinct two-tone crest per club and needs `pip install pillow`.
`mkkits.py` lends each club a shipped club's kit definition; run it with no arguments to see
where `UniformParameter.bin` comes out of.

Then go to the [testing guide](testing-guide.md), or, if you are starting from a clean
install, to the [step-by-step walkthrough](step-by-step.md).
