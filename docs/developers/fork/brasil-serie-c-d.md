# Brazil's Série C and Série D (FL27, lab)

This page covers Brazil's third and fourth divisions in their real formats:
- the 2027 transition season;
- the format from 2028 on.

There are no state championships. Everything was played in the lab on FL27, in a world built on the Carabao Cup
world (kcup).

The code lives in four places:
- `tools/native/brasil_engine.h`, included by `fl26swiss.c`;
- the regional mover and the late door in `fl26join.c`;
- the menu and screen hooks in `fl26swiss.c`;
- the `xline` / `jline` readers in the two Lua modules.

## The formats

**Série C, 2027 (transition)**
- One table of 24, single round robin.
- The top 8 go to two quadrangulares, 1-4-5-8 and 2-3-6-7, home and away.
- The first two of each group go up.
- The two group winners play a two-legged final.
- Two clubs go down.

**Série C, 2028 on**
- Two regional groups of 14, home and away.
- Three clubs go down from each group.
- The best four of each group go to the quadrangulares. Their composition is [a confirmar].

**Série D**
- 96 clubs in 16 groups of 6.
- Knockout, every round two legs: 64, 32, 16, quarter-finals, semi-finals, final.
- Six clubs go up:
  - the four semi-finalists;
  - the two winners of the repescagem.
- The repescagem: the quarter-final losers, 1v4 and 2v3 by campaign. A tie on aggregate goes by campaign, with no
  penalties.

## How it is built

**The leagues**
- The divisions are leagues of the recipe:
  - the C (24 clubs);
  - the C's second group ("Grupo B");
  - the two quadrangulares (4 placeholder clubs each);
  - the D's 16 groups.
- `group_of` makes a league a group of another. It writes `lphase <host> <reg> 3`. A group under the same league as
  its host is a sibling: same division, no exchange, and the league above keeps its one link down to the host.
- `group_label` names the group (`lpname`).
- `CLUBS_MIN` is now 4, for the quadrangulares.

**The knockouts**
- The D's knockout is one regulation. A copy of the Libertadores qualifying round is made by the country's script.
- The C's final is also one regulation.
- `brasil_engine.h` makes their rounds with the game's knockout maker.

**The New Year**
- The regional mover (`rgroup` / `rhome` / `rmap`) moves the whole B/C/D pyramid at New Year:
  - Série B: the game's league 163, tier 10;
  - the C's two groups: tier 11;
  - the D's sixteen groups: tier 12.
- Each club arriving in the D goes to its state's group.
- The reserve list (`fl26_join_rpool`) fills the D when it is short.
- `up=255` means who goes up is decided by fl26swiss (`fl26_swiss_promoted`): the D's knockout and the C's
  quadrangulares.
- `fl26_join_rdown` gives a league's direct down for one closing season.
- `fl26_join_rshape` and `fl26_swiss_rshape` change the C from one table of 24 to two groups of 14 in 2028. They
  write the record's clubs and meetings. The save keeps them.

**The quadrangulares (two real leagues)**
- They sleep until the first phase ends. `fl26_join_rlate` makes the door refuse them and keep their placeholder
  list.
- On the fill day, `fl26_swiss_cqleague` fills them (1-4-5-8 / 2-3-6-7), opens the door
  (`fl26_join_late_open`) and registers them (`register_all`).
- The final and the promotion go by their tables.

**Empty-league guard**
- In 2027 the C's second group is empty by design.
- The game divides by a club's squad size or a league's club count, so an empty league crashed it.
- `zdiv_install` guards the five divisions in LayerProcess18 (`0x140fb3a80`) and its siblings.

## The screens (Competition Info)

**The C's menu**
- "Classificação": the C's table.
- "Quadrangulares": `lphase` text 4, a set of leagues behind one item, named by `lpname <0x8000 + host>`. L1 / R1
  go through Quadrangular A and B.
- "Final".

**The D's menu**
- "Classificação": the 16 groups on L1 / R1, each named ("Grupo A1" ...).
- "Mata-mata": every round, one page per round, with the round names from `lpname`.

**Other screens**
- Gols / Assistências add every phase up per player (`rank_handler`).
- Base de dados → Info. da Competição builds its menu in `0x141520040` (`ci_menu2_handler`). It now gets the same
  items.
- "Times participantes" is the panel beside the competition list. It is filled by `0x140b08e20(self, &out, &regs)`,
  called at `0x140b09388` and `0x140b094ce`. `plist_handler` puts the league's live groups after the host, so the D
  lists its 96 clubs instead of the first group's 6.

## The world lines (the lab world, as built)

```
league 219 ... clubs=24 legs=1 ... name=Brasileirao Serie C
league 220 ... clubs=7 legs=2 ... name=Brasileirao Serie C Grupo B
league 221 ... clubs=4 legs=2 ... name=Brasileirao Serie C Quadrangular A
league 222 ... clubs=4 legs=2 ... name=Brasileirao Serie C Quadrangular B
league 223..238 ... tier=4 above=219 clubs=6 legs=2 ... name=Brasileirao Serie D, ... D A2 ... D A16
rcal 219 93 247 169 190 96 4
rcal 221 254 289 0 0 32 32
rcal 223 94 164 0 0 96 4                      (and 224..238 the same)
lphase 219 220 3
lphase 219 221 4
lphase 219 222 4
lphase 223 224 3                              (and 225..238)
lpname 220 Grupo B
lpname 223 Grupo A1                           (and A2..A16)
lpname 32987 Quadrangulares                   (0x8000 + 219: the item of the set)
lpname 315 Final
lpname 314 Mata-mata
xline fl26_swiss_sdko 314 16 223 ... 238 <7 fill days> <14 days>
xline fl26_swiss_cquad 221 315 2 219 220 251 256 263 270 277 284 291 298 305
xline fl26_swiss_cqleague 221 222
xline fl26_swiss_rshape 219 2027 14 2 220 2027 14 2
rgroup 163 tier=10 size=20 up=0 down=4 slot=255
rgroup 219 tier=11 size=14 up=255 down=3 slot=159
rgroup 220 tier=11 size=14 up=255 down=3 slot=158
rgroup 223 tier=12 size=6 up=255 down=0 slot=155   (and 224..238)
rhome <team>:<D group>,...                     (every club by its state)
rmap <D group>:<C group>:163,...
jline fl26_join_rflags 163 4 219 1 220 3
jline fl26_join_rdown 219 2026 2
jline fl26_join_rshape 219 2027 14 2 220 2027 14 2
jline fl26_join_rpool <team ids of the reserve list>
jline fl26_join_rlate 221 4 <4 placeholder team ids> 222 4 <4 placeholder team ids>
```

Season years: FL27 stamps the Brazilian season shown as 2027 as 2026 (`+0x2fc`), so the rules go by the stamp.

The script that writes the country's lines and the club lists is not in this tree. It is lab-only and depends on
the Carabao world's ids. The lists of clubs and the rules come from the CBF regulations, Wikipedia, NewLife 1.6 and
Transfermarkt.

## What was proven, what was not

**Proven in game (FL27, the lab's Carabao world)**
- 2027:
  - the D's 7 rounds with the repescagem, and 6 up;
  - the C: table of 24, quadrangulares, final, 4 up.
- The turn into 2028:
  - B / C / D exchange right;
  - the C in two regional groups of 14, home and away;
  - the D complete, with 4 from the reserve list.
  - Played to day 141 of 2028.

**Proven later (19/11/2026)**
- The quadrangulares as two real leagues:
  - the log shows 12 + 12 matches;
  - dates 12/09–17/10;
  - the final on day 291;
  - 4 up.
- The screens above, confirmed on screen, including the D's 96 participants.

**Not yet**
- The 2027 → 2028 turn with the quadrangulares as leagues.
- The 2028 dates: [a confirmar].
- The 2028 quadrangulares' composition: [a confirmar].
