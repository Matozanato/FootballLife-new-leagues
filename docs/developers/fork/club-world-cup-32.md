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
- **Calendar.** Its days are fixed and are not checked against the league and continental
  calendars of the world.
- The game's own clubs pools (the only Africa and Oceania clubs it has) go into the fourth pot.

## In Mod Studio (branch feature/cwc32)

Leagues > More > **Club World Cup** (`ClubWorldCupDialog` in `pages/builder.py`) writes the recipe's
`club_world_cup`: `on`, `every` (years), `first` (the first year it is played), `keep_old`,
`old_name` and `replace`. Build (`leaguebuilder.club_world_cup`, after the super cups):

- `mkcwc.reshape` on competition 1, the knockout on a free regulation id kept from Build to Build
  (cup_ids `cwc:club_world_cup`);
- with `keep_old`, `mkcwc.intercontinental` first copies the shipped four-club cup onto a
  competition and regulation of its own (cup_ids `cwc:intercontinental`). A world with no free
  competition id gives it the ids of a cup it no longer builds: the dialog unticks that cup
  (`cwc_untick`) and `replace` names it, so the first Build pins its old ids (`cwc_pins`);
- the world file gets `cwc32 ko=<reg> every=<n> first=<year> ic=<reg> iccid=<cid>`;
  fl26swiss.lua hands it to `fl26_swiss_cwc`. Without the line the DLL behaves as before
  (knockout 200, every season).

At run time (fl26swiss.c, `cwc_handoff`): the game's four entrants of regulation 1 go to the
Intercontinental every year (set_clubs + register_all, dated with the shipped regulation 1 days),
and the 32-club draw is made only when the year it is played (June after the draw) is in the
cycle. A career saved before has none of the new rows (`cwc_world` and `ic_world` say no) and
keeps the old cup. Not yet played in the game.

### The field (cwc_quota_field, the user's rule of 2026-11-17)

12 UEFA, 6 CONMEBOL, 5 AFC, 5 CAF, 4 CONCACAF (FIFA's shares; the OFC place, with no OFC clubs in
the game, goes to the AFC and the CAF). Each confederation first takes the champions of its
continental cup of the four seasons before the cup (titles of T-4 .. T-1 for a cup played in June
of T; the confederation is the club's country's, from the world file's confed line): the game's
Champions League (4), Libertadores (10) and AFC Champions League (16) knockouts and every cup of
ours the league champions go to. A club with two titles is in once; the places left go to the
best of the confederation ranking. No limit per country. Pots of eight in list order: UEFA 1-4
and CONMEBOL 1-4, UEFA 5-12, then the other sixteen by points.

The titles and the ranking are fl26cwc.dll's (tools/cwcrank, now in the pack: build-cwc.sh,
sider/experimental/fl26cwc.lua): fl26swiss tells it every winner at the teardowns and at the
draw (`fl26_cwc_champion`), it keeps them in each save's ledger (`K_CHAMP`, six years whatever
the window) and hands them back with the ranking (`fl26_cwc_champions`, `fl26_cwc_ranking`).
Its cycle comes from the same cwc32 line (`fl26_cwc_every`). Without fl26cwc.dll, or with a
confederation it cannot fill, the old access list stands in.

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

The scene itself (which cup, which stadium dressing) is the cinematic pack's and Sider's
(`cinematics.lua` of the SP patch, or FL26's `Entrance.lua` through Leagues > More > Trophies):
the knockout's tournament id has to be mapped there like the other ids of competition 1.

### The rankings and their menus, with the option (2026-11-17)

Everything the confederation rankings need now comes with the Club World Cup option; nothing is
installed by hand any more.

- **Modules (the pack).** `sider/experimental/fl26contrank.lua` (the ranking screens, the
  "Ranking CWC" submenu in Master League > Data and League Mode > Data, the screen titles, the
  clubs past the world ranking) and `fl26cwc.lua`/`fl26cwc.dll` (the points). Both are in
  `lbpack.ORDER`, fl26contrank before fl26cwc, and both do nothing unless the world file has a
  `cwc32` line: a world without the cup keeps the game's menus.
- **The world.** The Build (`leaguebuilder.build`, right after `club_world_cup`) calls
  `tools/lbcwcmenu.py`, which writes into the world's livecpk root:
  `common/script/flow/ML/MLMainManu.json` and `League/LeagueMainMenu.json` with the events
  `leaguerankna/as/af` added (`leaguerankeu/sa` too when missing), `Common/CmnLeagueRanking{NA,AS,AF}.json`
  (copies of the game's EU unit) and `<lang>/string/all.str` for all 18 languages with the texts of
  category 0x1a 0x2ac..0x2b6 (UEFA .. CAF, "Ranking <confed>", "Ranking Copa de Clubes" in
  bra/por/spa/mex, "Ranking CWC" elsewhere). Each file is made from the one the game shows now: the
  first non-world livecpk root of sider.ini that has it, else the newest archive. An id already
  used with another text is left alone and logged.
- **The world file** always gets the `confed` line when the cup is on (fl26contrank reads it).
- Old by-hand copies in `livecpk\root` (flows, bra/eng all.str) are covered by the world's and
  can go.
