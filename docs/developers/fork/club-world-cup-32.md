# Club World Cup with 32 clubs (unfinished, not in Mod Studio)

The 2025 format -- 32 clubs, eight groups of four played once, then a single-match knockout of
sixteen -- works in the game, but it was never wired into Mod Studio. The code is here for anyone
who wants to finish it. Mod Studio itself does not use it, and nothing below is supported.

## What exists

- **`tools/mkcwc.py`** reshapes competition 1 (the Club World Cup) in the tables: regulation 1
  becomes the group stage (a copy of the Libertadores group stage with one round, replicas
  1025, 2049 ... 8193) and a new regulation, 200 by default (`--ko`), the knockout of sixteen.
  `--dry` prints the plan and writes nothing.

  ```
  python tools/mkcwc.py --base <pesdb dir> --out <livecpk root> [--ko 200] [--dry]
  ```

- **`tools/native/fl26swiss.c`** already carries the run-time half (search `CWC_`): when the game
  hands the Club World Cup its entrants on regulation 1, the field is replaced by 32 clubs from
  league tables (the access list in the source, pots of eight), drawn into eight groups with the
  game's own group draw, handed over to the knockout when the groups end, and dated
  (`CWC_GROUP_DAYS` / `CWC_KO_DAYS`). A world without the reshaped rows (no regulation 200 or no
  replica 1025) is left alone, which is why it is inert in every Mod Studio world.

Tested once in a private world (two seasons in one session): 48/48 group matches and 16/16
knockout matches played, and the July teardown was clean.

## What is missing

- **Mod Studio integration.** `leaguebuilder.py` does not call `mkcwc.py`; the rows have to be
  written into the world by hand or by a new Build step. Check that the knockout regulation id
  is not one the builder already hands out in that world (pass a free one with `--ko`, and change
  `CWC_KO` in fl26swiss.c to match).
- **A configurable field.** The 32 places come from a fixed access list in fl26swiss.c, not from
  the recipe.
- **Every four years.** It plays every season (mid-December); the real one is every four years
  in summer.
- **Calendar.** Its days are not checked against the league and continental calendars of the
  world. Since 2026-11-22 they are checked against the national-team days (`cwc_plan` in
  fl26swiss.c, from B254's `nt_day`: the qualifiers' windows every year, a tournament in its own
  year): the seven two-day rounds of the template (153/154 ... 177/178) stay where they are when no
  national-team day is within the span or a day either side, otherwise the whole cup moves clear
  of them (rounds 4, then 3 days apart, days 152..179: 2 June, two days after the Champions League final, to 29 June; the July rollover is day 181), otherwise each round takes the first two
  free days. Log: "Club World Cup -- national-team days: ... rounds on ..." and B254's new
  "window days:" line. A Become a Legend player called up had a national-team match among the
  rounds. Not checked in the game yet.
- The game's own clubs pools (the only Africa and Oceania clubs it has) go into the fourth pot.

## In Mod Studio (branch feature/cwc32)

Since the merge of 0.4.0 (2026-11-21, branch feature/cwc32-fl27): **Cups > International**
(`InternationalEditor` in `pages/international.py`, the fourth tab of the Cups page). It always
lists the Intercontinental Cup (the game's four-club Club World Cup); **Add Club World Cup** adds the
cup of 32 and Apply writes the recipe's
`club_world_cup`: `on`, `every` (years), `first` (the first year it is played), `keep_old`,
`old_name` and `replace`. Build (`leaguebuilder.club_world_cup`, after the super cups):

- `mkcwc.reshape` on competition 1, the knockout on a free regulation id kept from Build to Build
  (cup_ids `cwc:club_world_cup`);
- with `keep_old`, `mkcwc.intercontinental` first copies the shipped four-club cup onto a
  competition and regulation of its own (cup_ids `cwc:intercontinental`). A world with no free
  competition id gives it the ids of a cup it no longer builds: the dialog unticks that cup
  (`cwc_untick`) and `replace` names it, so the first Build pins its old ids (`cwc_pins`);
- the logos (2026-11-21, a Logo field on each of the tab's two cups): the cup of 32's is
  `club_world_cup.logo`, written on competition 1 (none keeps the game's emblem). The
  Intercontinental's is the game's Club World Cup's, `edits.competitions["1"].logo`, the key
  Competition Names keeps it under, so it is the same whether the cup of 32 is on or not; with the
  cup of 32 on, `picture_jobs` writes it on the Intercontinental's id instead of 1, and with none
  the Intercontinental gets the game's own emblem of competition 1 from the install (`game_emblem`,
  as the Pre-Libertadores gets the Libertadores'). Until then the Intercontinental's new id had no
  emblem of its own;
- the world file gets `cwc32 ko=<reg> every=<n> first=<year> ic=<reg> iccid=<cid>`;
  fl26swiss.lua hands it to `fl26_swiss_cwc`. Without the line the DLL behaves as before
  (knockout 200, every season).

At run time (fl26swiss.c, `cwc_handoff`): the game's four entrants of regulation 1 go to the
Intercontinental every year (set_clubs + register_all, dated with the shipped regulation 1 days),
and the 32-club draw is made only when the year it is played (June after the draw) is in the
cycle. A career saved before has none of the new rows (`cwc_world` and `ic_world` say no) and
keeps the old cup. Not yet played in the game.

### The field (cwc_quota_field, the user's rule of 2026-11-17)

12 UEFA, 6 CONMEBOL, 5 AFC, 4 CAF, 4 CONCACAF and 1 OFC (since 2026-11-21; FIFA's shares, the host's
place to the AFC). The OFC place is the best OFC club of the ranking, no title first; with no OFC club
in the ranking it goes to the AFC. Until 21.11.: 5 AFC, 5 CAF and no OFC place. Each confederation first takes the champions of its
continental cup of the four seasons before the cup (titles of T-4 .. T-1 for a cup played in June
of T; the confederation is the club's country's, from the world file's confed line): the game's
Champions League (4), Libertadores (10) and AFC Champions League (16) knockouts and every cup of
ours the league champions go to. A club with two titles is in once; the places left go to the
best of the confederation ranking. Ties of points are broken by the game's world Club Ranking position, then the club id (2026-11-21; before, the field's qsort and the screen's sort each left ties in their own order, so a tied 12th UEFA place could differ from the screen): fl26cwc's list has that order, the confederation screens take it as their sort key and the pots follow it. No limit per country. Pots of eight in list order: UEFA 1-4
and CONMEBOL 1-4, UEFA 5-12, then the other sixteen by points.

The titles and the ranking are fl26cwc.dll's (tools/cwcrank, now in the pack: build-cwc.sh,
sider/experimental/fl26cwc.lua): fl26swiss tells it every winner at the teardowns and at the
draw (`fl26_cwc_champion`), it keeps them in each save's ledger (`K_CHAMP`, six years whatever
the window) and hands them back with the ranking (`fl26_cwc_champions`, `fl26_cwc_ranking`).
Its cycle comes from the same cwc32 line (`fl26_cwc_every`). The ranking's window resets the day
after each draw (day 333 of T-1 for the cup of T; until 2026-11-21 it was day 153 of T, after the
draw, which left the draw year's continental points out of the next cup's ranking), so the draw
reads the whole window and everything played after it counts for the next cup. Without fl26cwc.dll the old access
list stands in.

**A confederation that cannot fill its places (the user's rule, 2026-11-21).** A world without a
continent's continental cup (removed, or never made) has no titles and no ranking points for it
(points come only from continental matches), and a world without its clubs has nobody at all. Each
place left after the titles and the confederation's ranking goes to the best club of the whole
ranking not yet in, whatever its confederation (the OFC's place still goes to the AFC first). Only
when the whole ranking has fewer than 32 clubs (a first season with few continental matches) do the
game's four entrants and then the old access list fill the rest, whatever the confederation; still
short, the old access list picks the whole field. Until 21.11. the game's entrants and the access
list came first for each confederation: with fixed regulation ids (another league in a Mod Studio
world) and no CAF or OFC club in the list, a world without the CAF's cup gave its four places to
the ranking anyway, and one without the AFC's could take a wrong club.

The Build says so (`leaguebuilder.cwc_short_confeds` / `cwc_short_text`, a `warning:` line after
the Club World Cup's): the UEFA's, CONMEBOL's and the AFC's cups are the game's and always there;
a plan with no CAF cup (6 or 7), no CONCACAF cup (13) or no OFC cup (14) in its `ccups` is named
with where its places go. Cups > International shows the same, in red under the field, from the
last Build's plan.

**Which matches give points (2026-11-18).** The DLL knows the ids that are the same in every
world: the game's Champions League (2-4), Europa League (5, 6), Libertadores (8-10) and AFC
Champions League (15, 16), and the Conference League with the two play-offs (186-189, fixed by
mkuecl / mkeuropo). Everything else Mod Studio builds -- the UEFA qualifying rounds, the
Sudamericana and its first stage and play-off, the Libertadores phases 1 and 2, the CAF, AFC and
CONCACAF cups of its own -- takes the first free ids of each world (`free_comp_ids`), so the
Build writes them on a world file line (`leaguebuilder.cwc_points_lines`, with the cwc32 line only):

```
cwcpts 255=uq 256=uq 257=usq ... 309=gr 310=- 311=sgr 312=s 313=-
```

`u` UEFA (its own scoring), `s` a secondary cup (half), `q` a qualifying or preliminary round
(half), `g` a group stage, `r` one regulation per group or tie (`reg + 1024 * k`), `-` none of
them. The cup's confederation and kind come from its `fl26world.CCUPS` number (6 CAF Champions
League, 7 Confederation Cup, 8 ACL Two, 9 Sudamericana, 13 CONCACAF, 14 OFC, 15 AFC Challenge
League; 7, 8, 9 and 15 secondary), the CONMEBOL helpers from their `cup_ids` keys, the UEFA
rounds from the qround lines (competition 10 the Champions League, 11 and 12 secondary).
fl26cwc.lua hands the line to `fl26_cwc_comps`. A regulation not on it gives no points; a world
file without the line (a Build of before 18.11.) gives points for the game's ids only, so the
world has to be built again. Until then the DLL had one world's ids written in (255..260,
277..288, 309..313); in another world those could be a league or a national cup, and every match
of it would have counted as continental. The ledger keeps the points a match was given, so the
change counts from the matches played after it.

### The final's title and trophy (fl26cwctitle, 2026-11-18)

Winning the final gave no Master League title and no trophy ceremony. Both came from the
knockout being a regulation the exe has never heard of; `sider/experimental/fl26cwctitle.lua`
(in `lbpack.ORDER` after fl26cwc, Lua only, on with the world's `cwc32` line) fixes them:

- **The title.** A live regulation record has a "next phase" link at `+0x78` (loader
  `0x1414f1cfd` -> `0x1414c9f40`, from the phase chain: dword `+0x10` bits 18-20 of the
  neighbouring row). The knockout had `+0x78 = 1` (the group stage, a chained phase); the
  Champions League (4), Libertadores (10), AFC (16) and Intercontinental knockouts have `0xffff`.
  The coach history's title filter `0x140fce0b0` (event 0x17 from `EventCompeResultListener`,
  `StateTitleCheck 0x140fb8710`) takes only phases with `+0x76` and `+0x78` = `0xffff`, so the
  final never reached the champion check `0x14151b3e0` -> record `0x140fcc870` (70-slot table at
  block `+0x1798ca8`), although the game knew the winner. The module puts the link back to
  `0xffff` before every match and every 256 file loads (a skipped final has no `set_teams`).
  Measured on an old save converted by fl26cwc's `mg_check`; whether a new career gets the same
  link was not checked. **Checked in the game:** the title went into the career history.
- **The ceremony.** The match's trophy id comes from a fixed table built in `0x141e54xxx` (330
  pairs {tournament, trophy}, not found = `0xd9`, none). The "has a ceremony" test `0x140a7f290`
  reads it directly -- Sider's `trophy_rewrite` only swaps the scene's trophy at `0x141f51855` --
  so the knockout (not in the table) ended with the generic celebration. The shipped Club World
  Cup pair is tournament 1 -> trophy `0xb0` (`mov eax,1` at `0x141e54979`, stored at
  `[rbp+0x658]`); regulation 1 is the group stage now and never has a final, so the module gives
  the pair to the knockout (four bytes, checked first). That is done only when a Club World Cup
  trophy scene is installed -- `end_trophy_01_acl.fdc` under `content\cinematics` or
  `content\Entrance`, in `FIFA Club World Cup`, `CWC`, `Club World Cup`, or the `Final` folder of a
  pack split by phase (`FIFA Club World Cup\Final`, `FIFA Club World Cup 2025\Final`: About PES's
  "Entrance FIFA Club World Cup 2025 V3") -- or the `cwc32` line says `trophy=1`; `trophy=0`
  keeps it off.
  Without a scene the final keeps the game's generic celebration (the players celebrate, then the
  end-of-match menu). **Checked in the game** (SP Football Life with the "FIFA Club World Cup"
  cinematic pack and its `cinematics.lua` sending the knockout's tournament to entry 16): the
  ceremony is played. The cup on screen is whatever the pack puts in `prop\cup_afc_cl_hi` (the
  ACL ceremony's cup): in that older pack the Intercontinental Cup, in the V3 pack's `Final` the
  2025 Club World Cup trophy (`fcwccup1/2` textures). A pack split by phase needs its ids mapped
  per phase: the knockout with `match_info` 53 -> `Final`, the knockout otherwise -> `Knockout`,
  regulation 1 and its replicas (1025 ... 8193 in a Mod Studio world, not the 1071 ... 8239 of the
  pack's notes) -> `Groupstage`.

- **The Intercontinental (2026-11-21, FL27).** Its final (regulation `ic=` of the cwc32 line) had
  no ceremony either: the table's one Club World Cup pair goes to the knockout, and the
  Intercontinental's id is in no pair. The lookup's "not found" (`mov eax,0xd9; jmp` at
  `0x141e55284`, r8w the tournament looked for) becomes `jmp [0x141e552c4]`, a pointer kept in the
  int3 padding after the function, into a VirtualAlloc'd stub: `0xb0` for the Intercontinental,
  `0xd9` for any other id, then back to `0x141e55292`. `0xb0` is the game's own Club World Cup
  ceremony, so no scene is needed (a cinematics module that maps the id plays its own); `trophy=0`
  keeps it off. Its `+0x78` link is cleared like the knockout's. Its dates (`ic_dates`): the
  shipped regulation 1's records came back as day 348 round `0x2e` kind 0 (first leg), day 349 round `0x2e`
  kind 1 (second leg), 352 `0x35` and `0x36` kind 2, so the calendar showed a home-and-away
  semi-final with no opponent; every record is kind 2 now. Not checked in the game yet.

The scene itself (which cup, which stadium dressing) is the cinematic pack's and Sider's
(`cinematics.lua` of the SP patch, or FL26's `Entrance.lua` through Leagues > More > Trophies):
the knockout's tournament id has to be mapped there like the other ids of competition 1.

### The rankings and their menus, with the option (2026-11-17)

Everything the confederation rankings need now comes with the Club World Cup option; nothing is
installed by hand any more.

- **Modules (the pack).** `sider/experimental/fl26contrank.lua` (the ranking screens, the
  "Ranking CWC" submenu in Master League > Data, League Mode > Data and Become a Legend > Data, the screen titles, the
  clubs past the world ranking) and `fl26cwc.lua`/`fl26cwc.dll` (the points). Both are in
  `lbpack.ORDER`, fl26contrank before fl26cwc, and both do nothing unless the world file has a
  `cwc32` line: a world without the cup keeps the game's menus.
- **The world.** The Build (`leaguebuilder.build`, right after `club_world_cup`) calls
  `tools/lbcwcmenu.py`, which writes into the world's livecpk root:
  `common/script/flow/ML/MLMainManu.json`, `League/LeagueMainMenu.json` and `BL/BLMainMenu.json` with the events
  `leaguerankna/as/af` added (`leaguerankeu/sa` too when missing), `Common/CmnLeagueRanking{NA,AS,AF}.json`
  (copies of the game's EU unit) and `<lang>/string/all.str` for all 18 languages with the texts of
  category 0x1a 0x2ac..0x2b6 (UEFA .. CAF, "Ranking <confed>", "Ranking Copa de Clubes" in
  bra/por/spa/mex, "Ranking CWC" elsewhere). Each file is made from the one the game shows now: the
  first non-world livecpk root of sider.ini that has it, else the newest archive. An id already
  used with another text is left alone and logged.
- **The world file** always gets the `confed` line when the cup is on (fl26contrank reads it).
- Old by-hand copies in `livecpk\root` (flows, bra/eng all.str) are covered by the world's and
  can go.

### FL27 and 0.4.0 (2026-11-21, feature/cwc32-fl27)

- **Merged onto FL Mod Studio 0.4.0.** The Club World Cup moved from Leagues > More to Cups >
  International (Leagues > More > Club World Cup, where a page still calls it, opens that tab).
- **The OFC ranking.** fl26contrank has a sixth screen, Common/CmnLeagueRankingOC (confederation 7),
  button 97 "OFC" (text 0x2b7) on the Ranking page of ML and League Mode, title "Ranking OFC"
  (0x2b8). 97 was checked on FL_2027.exe: the default case of the three id switches, not in the button
  table, not a category (95 is not: the availability switch has a case for it). Its reg2 stub of six
  units moved from 0x6a0 to 0x1300 (the five-unit one ran into the button names at 0x720 with a
  sixth). lbcwcmenu writes the OC flow and the two texts.
- **The same exe sites.** Every site fl26contrank patches is the same in FL_2027.exe (read from the
  file); fl26cwctitle's trophy pair at 0x141e54979 too.
- **Offsets of FL27's caps set.** fl26cwc read the day at a fixed block+0x19115e4 and 600 regulation
  rows; it now reads both from the caps set installed (tools/native/fl26layout.h, lay_today,
  lay_regcap), and logs them ("layout: ...").
- **16-bit competition ids.** mkcwc and cwc_localize read the competition id with M.reg_cid /
  M.comp_cid (FL27's big worlds have ids past 255).
- **fl26confgroups (FL27).** The Intercontinental is on every confederation's side of Competition
  Info next to the Club World Cup, and out of League Info as the Club World Cup is (B402): the
  world line's `fifa=<cid>:1`, fl26_confgroups_fifa.
- **mkcwc on FL27's tables**: competition 1 is the shipped one-row cup (reg 1, four clubs) and the
  Libertadores group stage is at reg 8 as in FL26: reshape and the Intercontinental copy work.

fl26contrank's stub for the clubs past the world ranking tests the slot the way the world ranking
build (0x141324ded) does now: at init it reads that site, and when fl26slot7 has made it a jmp to
its 9-bit stub, the page's flag at +0x1220 is 1 and the stub reads `+0x41c | +0x41b << 8` (else
the game's `+0x41c & 0x7f`). Until 21.11.2026 it always tested 7 bits, so a club on slot 251 or
379 was in no confederation list, and one such club inside the world's 750 also pushed the
stub's skip count one club too far (tools/contrank/gen3.py makes the stub).

**The points column again (fl26cwc, 21.11.2026).** On the confederation screens the league column
shows the club's CWC points (header "Pontos") and only clubs with more than 0 points are listed --
also while nobody has any (the list is then empty; until 21.11. everyone was shown at 0). After
the two fl26contrank changes of 21.11. it showed the league names: the 9-bit slot test moved the
extra stub's tail from +0x159 to +0x184, so fl26cwc turned down the whole hook ("lists:
fl26contrank's stub is not the one expected"), and its trampolines at cave+0x1300/0x1310 were under
the new six-unit reg2 stub (0x1300..0x1387). fl26cwc now looks for the tail in the stub's first
0x400 bytes, and its trampolines are at cave+0x1480 (the column) and +0x1490 (the header).

**Become a Legend (2026-11-21, not yet tested in the game).** Until now the cup was made and
tested in Master League and League Mode only. The cup itself (fl26swiss, fl26match, fl26cwctitle)
does not look at the mode; three things did:

- **The ledger.** fl26cwc took only `ML0000000N` and `LG0000000N` as saves; BAL saves to
  `BL0000000N` (its own three slots), so a BAL career's points were never written beside the save
  and were gone after a load. `save_name` takes `BL` too (`BL0000000N.fl26cwc`).
- **The menu.** BAL has a menu class of its own, `MainMenuBLData` (vtable 0x1426bb158, found by its
  RTTI), page-based like ML's, with tables of its own: buttons at 0x1426ba790 (35 entries, no 87,
  no category 91), one page table at 0x1426bab60 (no `[menu+0xa0]` choice), root
  `1 | 2 108 6 4 7 8` with the 7th slot free and the Data page (index 5) `7 | 60 61 30 90 88 89` as
  in ML. A scan of every rip-relative disp32 into the two tables finds three readers only: the
  lookup by id (slot 2, 0x140bbe800, `cmp eax,0x23`), the mailbox scan (0x140bbef20, `cmp ebx,0x23`)
  and the tree builder call (0x140bbdd7a `mov r8d,7`, 0x140bbdd80 `lea rdx`, builder 0x140cd0bb0 as
  ML's). Its enabled switch (slot 1, 0x140bbe880) sends 86..97 to its default. fl26contrank's
  `m.bl_menu` makes the ML copies for it at page +0x1a00 (buttons) and +0x1cc0 (pages); a mismatch
  leaves only the BAL menu alone (log "no ranking in the Become a Legend menu").
- **The flow.** `BL/BLMainMenu.json` ships `12_leaguerankeu` and `23_leagueranksa`; lbcwcmenu adds
  `leaguerankna/as/af/oc` to it as to the ML and League flows.

The title of the final in a BAL career (the player's history, not the coach's) is not checked.

Known, not done: Copy B's match table fix (League Mode) is in the FL26 caps set only; FL27's
sets (patches/*.fl27*.json) have not been made again with it.
