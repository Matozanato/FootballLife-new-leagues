# Argentina: the whole pyramid and its cups (FL 2027)

Argentina's football from the Liga Profesional down to the Torneo Regional Federal Amateur, with the formats the AFA
plays in 2026 and 2027, and the country's cups. It was built and played in the lab on FL 2027 through two whole
seasons and two New Years (2026 → 2027 → 2028). The recipe's leagues come from the NewLife Database 1.6b4. The rules
the game cannot express with leagues alone live in `tools/argentina` and run inside Build.

## How a person gets it

- **A league package**, `Argentina-2026.fl26pack` (89 leagues, 362 clubs' squads): **2. My world** → **+ Add...** →
  the package → **Add** → **Build and install**. Then start a NEW Master League. The package carries the recipe key
  `country_rules: ["argentina"]` (`lbpackage.export` / `add`; `remove` takes it out again).
- **A recipe**: any recipe whose leagues are these, plus `"country_rules": ["argentina"]`.

Needs: FL 2027, the NewLife Database 1.6b4, and the modules of this branch (fl26swiss, fl26join, fl26confgroups,
fl26chain, and their Lua).

## What is in it

| Division | Format (2026) |
|---|---|
| Liga Profesional (the game's, reg 30) | 30 clubs. Apertura (rounds 1-15) and Clausura (16-30) on their own tables, the second clásico round; play-offs of 16 in each half; the Trofeo de Campeones (and its tie-break of the runners-up); relegation by promedio |
| Primera Nacional | 2 zones of 18; the 1st promotion final; the Reducido (the final's loser in the 2nd phase) and its final; interzonal matches |
| Primera B Metropolitana | 22 clubs; the Reducido of the 2nd to the 9th, reseeded each round |
| Federal A | 4 zones; the 2nd phase (Zona Campeonato) and the Reválida as leagues that start mid-season; their knockouts |
| Primera C | 2 zones; the final, the Reducido, the desafiliación and the promotion v the Promocional; interzonal matches |
| Torneo Argentino del Interior | from 2027: 4 zones of 16, play-offs and repescagem (2026: asleep) |
| Torneo Promocional Amateur | 2 zones; the final and the Reducido |
| Torneo Regional Federal Amateur | 8 regions, 70 zones of 2 to 4 clubs; each region's knockout; the 2026 final stage |

The New Year (fl26join's regional pyramid mover): promotions and relegations between all of them by the tables and
the knockouts' results, homes by filiation (direct: Buenos Aires; indirect: by province and region), the Interior's
birth in 2027, zones split again in even parts every year.

The cups (`tools/argentina/copas.py`):

- **Copa Argentina** — the game's own competition (49, reg 59) played as a knockout of 64 in six one-match rounds; 2026
  is the real draw (10/12/2025); from 2027 the LPF's 30 and the quotas of the divisions below. It gives ARG 3.
- **Supercopa Argentina** — the game's own (79, reg 92): the Copa's winner v the Trofeo's (its runner-up when one club
  won both). 2026: Independiente Rivadavia v Estudiantes.
- **Supercopa Internacional** — new: the Trofeo's winner v the Liga's champion (annual table). 2026: Estudiantes v
  Rosario Central.
- **Recopa de Campeones** — new, from 2027: a triangular of the three winners, 3/2/1/0 points.

All of them are filled on 3 January, so Competition Info shows their clubs and ties from the season's start.

Competition Info: the Regional's eight regions behind one entry, "Torneo Regional Federal Amateur" (choosing it shows
them in place, each with its own menu; Back returns). Every knockout is an item of its league's menu, never a
competition of its own; a cup of its own opens on its bracket ("Chave"). Select Team: Argentina's leagues in folders
(each division's zones and phases under one row, the Regional under "Regionais" → region → zones).

Adaptations (the AFA publishes no rule for them) are marked `[adaptação]` and open facts `[a confirmar]` in the
modules' comments.

## How it is built

`leaguebuilder.build()` → after the tables and `fl26world.txt` are written → `argentina.apply(pl, root, base, log)`:

1. new competitions and regulations (copies of the Libertadores qualifying round) for every knockout; the game's
   Copa Argentina and Supercopa Argentina regulations turned into the same kind in place;
2. the world file's lines (below), replacing earlier ones of the same kinds;
3. the competitions' emblems from `tools/argentina/data/logos`.

Data: `data/argentina2026.json` (the 2026 clubs, zones and filiation, NewLife ids), `c_interzonal_2026.json`,
`provincias.json` (the provinces of the Primera Nacional's and Federal A's clubs, from Wikipedia 2026).

Builder rules this needed:

- a league with `"mover": "regional"` may have 2 clubs (`CLUBS_MIN_ZONE`, `clubs_min(L)`): the Regional's zones;
- up to 96 leagues in one group set (`MAX_GSIDE`, fl26chain too).

## World file lines

| kind | what |
|---|---|
| `lphase <host> <reg> <type>` | an item of a competition's Competition Info menu: 1 a knockout (a cup of its own: host = reg), 2 a phase league's table, 3 a zone (L1/R1), 4 a half's table, 5 a final as the last page of a knockout |
| `lpname <id> <text>` | the item's name; `0xC000 + reg*8 + round` a round's title, `0x8000 + reg` a phase item, `0xBF00 + half` a half |
| `sline <export> <numbers...>` | calls an export of fl26swiss.dll: `fl26_swiss_tcup` (a knockout), `_tcupy` (one year's first round, the real 2026 draws), `_mphase` (a league filled mid-season), `_izone` (interzonal matches), `_ldates`, `_lhalf` (the LPF's halves), `_lvmenu` (a level of the competition list), `_filiation` |
| `jline <export> <numbers...>` | calls an export of fl26join.dll: `fl26_join_regional` (tiers, homes, maps, knockout results), `_rflags`, `_rzones`, `_rlate`, `_rprom` (promedios), `_rinvite`, `_rlast`, `_rlasth`, `_rsleep` |
| `confsub slots=<slot>:<folder>,...` | Select Team: a league's folder (fl26confgroups) |
| `confsubnames <folder>:<parent>:<cid>:<name>\|...` | a folder's parent (0: the country), its row's emblem (a competition id, 0 none) and name |

A knockout's sources (fl26swiss `tc_source`): `0x1` a table place (`|0x80` from the bottom, `|0x40` the rest of a
zone), `0x2`/`0x3` a tie's winner/loser (another cup: `reg << 8`; `0x04000000` the loser when the winner is in
already), `0x4` the n-th of a ranked group, `0x5` a fixed club, `0x6` by filiation, `0x7` a half's table, `0x8` the
Trofeo's and the Recopa's sides, `0x9` this season's clubs by squad strength, `0xA` last season's final table, `0xB` a
cup's kept winner / runner-up. Flags: `TC_F_BETTER` (a level tie to the better placed), `TC_F_HOMEBEST`, `TC_F_TRI`
(a triangular).
