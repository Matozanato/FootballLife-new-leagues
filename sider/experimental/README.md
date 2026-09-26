# Experimental modules

Everything in this folder does something the modules one level up do not, and **none of it
has been checked by anyone but us, on anything but our test world**. They are here because
the fastest way to find out whether they work is for more than one person to run them. They
were built and verified against the exe between 2026-09-21 and 2026-09-24. Most were watched
working in a running game, and the season-end group (`fl26augseason`, `fl26seasonend`,
`fl26chain`, with `fl26hdr192`) has now been played through a July rollover and on past the
New Year after it. The menu modules have not been through a season.

Install them exactly like the others (copy into `SiderAddons\modules\`, add a
`lua.module = "..."` line), **one at a time**, and read `sider.log` afterwards. Every one of
them reads the bytes it is about to change first and writes nothing at all if a single site
disagrees, so the worst case is a log line saying it found something else and a game that
runs exactly as it did before.

## What is here

| file | what it changes | the risk |
|---|---|---|
| `fl26hdr192.lua` | the season's competition header from 100 to **192** entries, instead of the 127 that `fl26hdr127.lua` gives | 192 needs a redirect at each of thirteen bounds rather than a single byte; the stubs go into the spare tail of the code section, where the null guards also live |
| `fl26comptab.lua` | the **Select Team** list, so leagues that had no slot in it become selectable, and rows that inherited a shipped competition's name stop displaying it | it hands out free slots in a table the menu reads; if your install's table differs it aborts and says which slot disagreed |
| `fl26slotnames.lua` | the **section heading** seven of those slots draw, which is hard-coded in the exe ("Classic Teams" over a league of yours) | it points seven slots at the switch's empty case, so the menu falls back to the competition's own name, and to the original heading when your world has no competition on that slot. The default list is safe in any world |
| `fl26clubs.lua` + `fl26clubs.dll` | the **club list** the Select Team screen shows for nine slots where the game builds the wrong one (national teams, classic teams, foreign clubs, or nothing at all) | it replaces two functions that read those lists and answers from the league's own rulebook instead, and a slot it cannot answer for falls back to the game's own answer. Since 2026-09-26 it also stops new leagues' clubs from landing in the Copa Libertadores / Club World Cup filler pools when a Master League is created (issue #8): the loader changes three bytes of the game's slot switch (slots 28, 71, 74) and the DLL leaves our clubs out of pool slots 69/73/75 for that one step. Only careers created after the update get it |
| `fl26rank.lua` | the **league rank** (first division, second, third) from a 2-bit field to a 3-bit one, so a pyramid can be more than three deep and the game can tell D3, D4 and D5 apart | 147 sites, every one an in-place rewrite of the same length; it moves the field into a bit the shipped loader never sets, and the group count keeps five bits (31 groups) |
| `fl26deeprank.lua` | the **relegation gate**, so a club goes down from any division, not only the second | replaces `fl26deep4.lua`; load it AFTER `fl26rank.lua` and turn `fl26deep4.lua` off, or the bytes will not match |
| `fl26deep4.lua` | one byte, so that a **third** division relegates into a fourth | superseded by `fl26rank` + `fl26deeprank`, which do it properly; kept for anyone who wants the one-byte version without the rank change |
| `fl26reg64.lua` | the number of **regions** (countries the menus group by) from 29 to **64** | one instruction: the shipped code masks the region to five bits and throws away anything from 29 up, while the runtime field it feeds is six bits wide. Every shipped row keeps the region it had |
| `fl26augseason.lua` | a Master League career in one of the added leagues **starts in August** (day 212) instead of 1 January | one jump: the lookup that picks the season type knows only the shipped regions 2..28, and a region of 29 or more fell through to "calendar year". Needs `fl26reg64.lua` (a league only reaches region 29+ with it). **Known side effect:** in an August-start career the Champions League play-off is registered after its own two dates, so on its own it gets no matches and the European competitions never start. With `fl26swiss` installed the DLL runs the play-off itself and all three competitions start (measured 2026-09-24) |
| `fl26superguard.lua` | the **UEFA Super Cup setup** no longer crashes when the Champions League or Europa League entry it looks for is missing | one bounds check. When an entry is missing, that season has no Super Cup instead of a crash. Seen in an August-start career without `fl26swiss`; the play-off problem above is the likely cause. With `fl26swiss` the Super Cup was set up normally in the first and the third season of a run on 2026-09-25. Keep the guard installed anyway |
| `fl26seasonend.lua` | the **end-of-season filter**: the French and Italian leagues take part in the European season end (so a league below Ligue 2 or Serie B can go up and down), and one league without a final table no longer stops promotion for its whole group | two redirects. Works with the updated `fl26join.dll`, which it leaves the final say to; without the DLL it drops only the league that cannot be moved |
| `fl26chain.lua` + `fl26chain.dll` | **promotion and relegation through three or more divisions**. The game exchanges clubs only across every other joint of a chain; the DLL completes the joints it skips, using the game's own standings and its own list writer | its `CHAINS` and `PROTECT` lists are **our** world's league ids and must be replaced with yours; the promote/demote counts must match the `COUNTS` table in `fl26comptab.lua`. Measured: the French and Italian chains moved 3 up and 3 down at every joint at the 2026-09-23 rollover, and on 2026-09-24 all five chains of the league-size world (the fifth is Championship -> an added England D3) did the same. Up to 8 chains |
| `fl26swiss.lua` + `fl26swiss.dll` | the **2024 European format**: the Champions League, Europa League and a new Conference League each play one league phase of 36 clubs (8 opponents each in the first two, 6 in the Conference League), then a knockout play-off for places 9-24, then a fixed bracket from the round of 16 to the final. It also fills all three from a **UEFA access list** (which league position goes where, 36 clubs per competition) and dates leagues of 10 to 24 clubs over the whole season | it replaces the game's schedule builder for the listed regulations only and runs the game's own code for everything else. Needs a world built with the European tools (see *The European format and league sizes* below). Its regulation ids are our world's and are written in the source; its access list names only the shipped leagues |
| `fl26catlist.lua` | **Database -> Competition Info** lists the countries of the added leagues, each under its own country's name (Croatia, Serbia, Norway ...), instead of leaving them out | it copies the game's list of 28 regions and appends 29..63, and answers "which country is this region" for the regions in its `COUNTRY` table. That same answer is also asked by the end-of-season code that hands out European places, so the added leagues are now treated there as the shipped leagues are. The flags on that screen are still borrowed from other countries |

## Order, and which of these need each other

They are not independent. This is the order they were run in here:

```ini
lua.module = "fl26comptab.lua"     ; first: it prints "id N -> row R slot S" for every league
lua.module = "fl26slotnames.lua"   ; the default slot list works in any world
lua.module = "fl26clubs.lua"       ; same
lua.module = "fl26rank.lua"
lua.module = "fl26deeprank.lua"    ; after rank, and with fl26deep4 off
lua.module = "fl26reg64.lua"
lua.module = "fl26augseason.lua"   ; needs reg64
lua.module = "fl26superguard.lua"
lua.module = "fl26seasonend.lua"
lua.module = "fl26chain.lua"       ; after comptab (the counts must agree)
lua.module = "fl26catlist.lua"     ; after reg64
lua.module = "fl26swiss.lua"
```

`fl26hdr192.lua` goes where `fl26hdr127.lua` was, after `fl26joindll.lua`.

**Use `fl26hdr192.lua` *instead of* `fl26hdr127.lua`, never both.** They patch the same
thirteen places, so whichever runs second will find bytes it does not recognise and abort.
A season already on disk was built against whatever header width was installed when it was
created. Switching between 127 and 192 means starting a new season.

## Lists you must edit for your own world

Besides the two `SLOTS` tables described below: `COUNTS` in `fl26comptab.lua` (how many clubs each of your leagues
promotes and relegates), `CHAINS` / `PROTECT` in `fl26chain.lua`, `REGS` and `UECL` in
`fl26swiss.lua` and `COUNTRY` in `fl26catlist.lua`. All of them ship with our test world's ids.
The `ACCESS` list in `tools/native/fl26swiss.c` names only the shipped leagues, so it fits
any world; add your own leagues to it (and rebuild the DLL) if they should play in Europe.

`fl26clubs.lua` carries a `SLOTS` table near the top, and the numbers in it are the slots
**our** test world happened to land on. (`fl26slotnames.lua` has one too, but since
2026-09-25 you can leave it as it is: a slot with no league of yours on it keeps its
original heading.) A competition slot is
not a property of your league; it is handed out by `fl26comptab.lua` at boot, and it says so
in `sider.log`:

```
[fl26comptab.lua] fl26comptab:   id 180 -> row 179 slot  75
```

Read the slot of each of your leagues from those lines and put those numbers in. **Never
guess a slot.** `fl26slotnames.lua` names, for each slot, the case byte it expects to find
and the heading that case draws today — if your install disagrees it changes nothing and
logs what it saw, which is the report we want.

## What `fl26rank.lua` and `fl26reg64.lua` are for, in one paragraph each

**Rank.** Every rulebook carries its place in the national pyramid, and the game keeps it in
two bits, which count to three. Build a fourth and a fifth division and all of D3, D4 and D5
carry the value 3; the League Info panel then shows France D4 as its own lower league, and
the end-of-season mover cannot tell which way anybody goes. `fl26rank.lua` moves the field
down one bit so it counts to seven. If you have already built a deep pyramid, renumber it
with `python tools\deepen.py --root <your root> --retier <top league ids>` — without that
the leagues still all read 3, because that is what is stored in the file.

**Regions.** A region is the country a competition is grouped under in the menus. The
shipped parser throws away any region of 29 or more, although the runtime field is six bits
and holds 64. `fl26reg64.lua` rewrites that one instruction. **The caveat that matters:**
the menu's *heading* for a region comes from a separate table of 24 rows, and a region with
no row there does not draw a blank — it draws the heading of whatever country was looked up
before it. So regions 29 and up work as groupings and borrow a name. The module that gives
them headings of their own copies the game's own rows, and the version that exists carries
those rows inside itself as a blob of shipped bytes; this repository does not redistribute
game data, so it will be published once it copies them out of memory at startup instead.

## The European format and league sizes (`fl26swiss`)

This is the newest part (2026-09-24) and the one with the most moving pieces, so here is the
whole route and exactly what has been seen working.

**What you get.** The Champions League and the Europa League keep their shipped competition
ids, but their group stage becomes one league phase of 36 clubs. A new competition, the
Conference League, is added the same way. Each of the three then plays: a league phase (8
opponents each, two from each pot of nine, over 16 matchdays; 6 opponents from six pots of
six over 12 matchdays for the Conference League), a two-legged play-off between places 9-24,
and a knockout from the round of 16 to the final whose bracket is fixed in advance. The
added leagues get real sizes: 10 clubs playing four times (36 rounds), 12 playing three
times (33), 16, 18, 22 and 24 clubs (46 rounds), next to the 20-club leagues.

**Building the world.** Start from a world built as in [build-your-world](../../docs/build-your-world.md),
with its leagues spread one region per league (`tools/spreadregions.py --root <root> --plan own`,
needs `fl26reg64.lua`). Then, each step writing a new livecpk root (`--out`) from the previous one:

```
python tools\mkreshape.py --base <root>\common\etc\pesdb --out <root2> ^
       --reshape UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:- --reshape UEFA_EUROPE_LEAGUE:1:groups:36:1:-
python tools\mkuecl.py   --src <root2> --out <root3>
python tools\mkeuropo.py --src <root3> --out <root4>
python tools\mksizes.py  --src <root4> --out <root5> --plan sizes.json
python tools\deepen.py --root <root5> --league 174 --below 79  --deep-rank --top
python tools\deepen.py --root <root5> --league 176 --below 174 --deep-rank
python tools\deepen.py --root <root5> --league 179 --below 96  --deep-rank --top
```

With those three lines in, add `{ 79, 174, 3, 3 }` to `CHAINS` in `fl26chain.lua` (the
comment above that table says why only then).

`mkreshape.py` copies only the three competition tables, so copy the rest of the world into
`<root2>` first. `mkuecl.py` prints a `local UECL = { ... }` line; put it into
`fl26swiss.lua`. The last three lines are our world's choices (two 24-club divisions under the
Championship, a 22-club second division under reg 96); leave them out if you do not want them,
and write `sizes.json` for your own leagues (one line per league: club count and how many
times the clubs meet; the format is at the top of `tools/mksizes.py`).

**This modifies two shipped competitions.** The Champions League and Europa League rows in
your own livecpk copy are changed, and the 18 shipped group rows that a 36-club single group
no longer needs are dropped. Nothing in the game's own files is touched; removing the root
undoes it.

**Measured in the game (2026-09-24, one world, one career in an added league):**

- all three league phases filled with 36 clubs and played; the Champions League
  quarter-finals follow the bracket (the shipped code draws them at random, which the DLL
  undoes, logging `quarter-finals put back in bracket order`);
- a first season played from August past the end of May with no stall, and the five
  promotion chains moving 3 up and 3 down at the rollover;
- the second season: every league size given the right number of rounds (10 clubs x 4 = 36,
  12 x 3 = 33, 12 x 4 = 44, 22 x 2 = 42, 24 x 2 = 46), and the August draw filling all three
  competitions from the final tables of the season before:
  `access -- 36/36/36 (108 positions from last season's tables, 0 from list order, 0 missing)`;
- **Database -> Competition Info** (fixed late on 2026-09-24): the Europa League and the
  Conference League now show their 36-club league-phase table under *Group stage*, as the
  Champions League does. Before, the item was greyed out for both all autumn, and opening
  *Knockout Phase* before the knockout draw crashed the game, for all three competitions.
  That item is now left out of the menu until the knockout phase is under way. The sider.log
  lines are `knockout item guard live` and `group stage item live`.
  Update 2026-09-25: the play-off for places 9-24 used to appear as *W-L Table*. It is now
  called *Play-offs*, stays grey until the play-off is drawn (the Conference League draw comes
  in December, the Europa League one in February), and then shows the ties. The page heading
  still reads *Group stage - Matchday ...*; that is the game's own heading and harmless. The
  extra sider.log line is `play-off names live`.

**What is not right yet, plainly:**

- The final tables the access list reads are kept **in the DLL's memory**, captured at the
  summer rollover (around day 176). If the game is restarted between then and the August draw
  (around day 244), they are gone and the draw falls back to league order. In the first
  season there are no final tables yet, so it uses league order anyway.
- The Conference League play-off is played in December, straight after its league phase,
  not in February as in the real competition.
- The access list names only the shipped leagues (since 2026-09-26). Until then it also
  named our world's new leagues by regulation id, and a world whose leagues landed on the
  same ids sent them to Europe as those countries (issue #8). New leagues get no European
  places unless you add them to `ACCESS` in `tools/native/fl26swiss.c`; the places left open
  are topped up from the big five.
- The regulation ids and the size plan are our world's. A world built with the same tools
  and defaults gets the same ids; anything else needs them edited.
- The game crashes now and then in its own protected code (see
  [known-issues](../../docs/known-issues.md)); on 2026-09-24 that was five times in about
  four hours of simulated play. Save often.

## What to report, for any of them

The `sider.log` lines the module wrote, what you expected to see in the game, and what you
saw instead. A module that refuses its patches is not a disaster and is still worth
reporting — the lines it writes name the addresses, which is exactly what is needed to find
out how your build differs. For the four that change menus (`comptab`, `slotnames`,
`clubs`, `reg64`), a screenshot of the screen that is wrong is worth more than a
description of it.

The compiled `fl26clubs.dll`, `fl26chain.dll` and `fl26swiss.dll` are built from
`tools/native/fl26clubs.c`, `tools/native/fl26chain.c` and `tools/native/fl26swiss.c`; their checksums and the build lines are in [tools/native/README.md](../../tools/native/README.md).
