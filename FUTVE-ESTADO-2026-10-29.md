# Liga FUTVE en FL26 — estado del desarrollo

**Fecha:** 29/10/2026 (pruebas de la mañana/tarde) · **Rama:** `v025-futve`
**Plan de referencia:** `docs/developers/fork/futve-playoff.md`

---

## 1. El formato que se está implementando

La Liga FUTVE de FL26 pasa a:

- **Apertura**: 2 grupos de 4 (días 3, 5, 7, 9, 11 y 13) + **Final del Apertura** el día 15, entre los dos ganadores de grupo. Es una competición aparte (2 clubes, un partido).
- **Clausura**: 2 grupos de 4 (días 145-160) + **Final del Clausura** el día 164.
- **Final del FUTVE**: el día **167**, entre el campeón del Apertura y el del Clausura. Si es el mismo club, **no se juega** y el título es directo; si son distintos, se juega.
- Después, las plazas continentales (fase posterior del plan).

## 2. Diseño técnico ya fijado

| Competición | id | Regulación | Día | Notas |
|---|---|---|---|---|
| Apertura (grupos) | 134 | 259 (+ réplicas) | 3-13 | grupos de 4, `adv=1` |
| Final del Apertura | **142** | 261 | 15 | competición aparte, 2 clubes |
| Clausura (grupos) | 135 | 260 (+ réplicas) | 145-160 | grupos de 4, `adv=1` |
| Final del Clausura | **129** | 262 | 164 | competición aparte, 2 clubes |
| Final del FUTVE | **175** | 263 | 167 | `src=261,262`, `fill=0` |

Claves del diseño:

- Los ids **142/129/175** son los que la lista del **builder 1** del exe da caso. `143/144` **no tienen caso**: por eso el primer intento con 142/143/144 fallaba con el nulo `0x141333485`. El **129 reemplaza** la competición base del mundo con ese id.
- La 175 entra en la temporada por el builder (`enter_season(175)`); las 142/129 también. Las finales son competiciones propias, no el KO del playoff.
- **175 sin entradas placeholder**: sus 2 filas `191:1,192:1` hacían que el juego contara "Liga FUTVE" como ganada antes de la final (palmarés, ver §5). Ahora el mundo se genera con **1.437 entradas** y 175 con 0; el DLL llena el KO y el `setcl` cuando tiene los dos campeones.
- El **join** registra las ligas 191/192 y las 133-136; las 142/129/175 entran por el builder 1.
- Las finales usan la entrada de la **UEFA Europa League F** (261/262) y la **UEFA Champions League F** (263) del `cinematics.lua`; `cinematicsB.lua` da la escena `Final\st001`. `trophy_rewrite` = `entry 16` (el trofeo UEL/UCL de las carpetas `content/cinematics` del usuario).

## 3. Lo que está hecho y probado

- **Fase A (caso mismo campeón)**: la liga, la Final del Apertura y la Final del Clausura se juegan como competiciones aparte; el **palmarés** muestra "Liga FUTVE", "Final del Apertura", "Final del Clausura" y "Copa Venezuela"; el título directo de la Final del FUTVE **sí aparece** en el palmarés (foto del usuario). Todo correcto salvo la celebración (§4.2).
- **Ids y builder 1**: 142/129/175 validados; 143/144 descartados por falta de caso.
- **Días**: la Final del Clausura pasó de 163 a **164** y la del FUTVE de 166 a **167** para no chocar con la Libertadores (reg 10: 163, 223, 258...).
- **Logos** de 134/135/142/129/175 (30 emblemas) y **cinemáticas** (UEL/UCL + `Final\st001`) en el sandbox.
- **Sandbox** (`futve_test.py`): instala 40 archivos (mundo, DLL, `fl26swiss.lua`, cinemáticas, 30 logos), hace backup/restore de todo (incluidos logs, caches, sider.ini, save) y valida con `--self-test`.
- **DLL** (`fl26swiss.c`):
  - `ccup_final_note` se llama para **toda final KO** (`if (ko || g_ccup[k].ko)`), no sólo cuando el flag `ko` viene a 1.
  - `ko_final_winner` recorre **todos los tipos de ronda** `0x00-0x3f` (la final usa `kind 0x2`) y deja un **log de diagnóstico** (rondas encontradas, tipo, slots, clubes, ganador en crudo) si no lee ganador.
  - `ccup_src_winner`/`g_ccup_win`: el campeón de cada final se guarda para la 175.
- **`futve_finals.py`**: genera el mundo de las finales; filtra las filas 175; verifica 175 con 0 entradas; los tests (38 comprobaciones) y el self-test pasan.

## 4. Dónde estamos detenidos (los dos bloqueos)

### 4.1 La Final del FUTVE no se juega (263/175 nunca aparece)

Evidencia del último test (`out/futve/tests/20261029-121419`):

```
cup reg 261 -- 0 round(s), 0 single-slot final(s), no winner read
cup reg 262 -- 0 round(s), 0 single-slot final(s), no winner read
cup 263 -- its two champions are not known yet (00000000, 00000000); not filled
cup reg 262 borrowed record 0: day 227 round 0x35 kind 0x2 -> day 164
```

Causa: **el `ko_round(261/262)` devuelve 0 rondas** porque la final no tiene ronda propia en la tabla: se juega sobre la **ronda prestada del cup 128** (el `kolike=128` de la línea `ccup`). El `winner_now`/los derechos también devuelve 0 para estas competiciones. Sin campeones el 263 no se llena y el 175 no se juega.

Lo que falta:

- que `ko_final_winner`/`ccup_ko_winner` lean la ronda de la final **desde la regulación prestada 128** (el `kolike` de la copa), o
- leer directamente los **registros de competición/carrera** que usa el palmarés (donde "Final del Apertura 1"/"Final del Clausura 1" ya están) para la temporada actual.

El juego está abierto pero **el proceso no es visible desde el sandbox** (`Get-Process` vacío; el juego/Sider corren elevados/fuera de la sesión) y la carpeta de guardado visible sólo tiene `save\EDIT00000000`; no se puede leer la memoria ni el save de la carrera desde aquí. Opciones: lanzar el juego/Sider sin elevación, dar la ruta real del save de carrera, o un volcado de memoria de `FL_2026.exe`.

### 4.2 La celebración/trofeo de las finales no sale

- La **entrada** de final sí funciona (`cinematics.lua`/`cinematicsB`).
- La **ceremonia posterior con trofeo** no: es la tabla de trofeos del juego (`trophy-table copy count: 167`); nuestras competiciones (142/129/175) no están en ella. El `trophy_rewrite`/`entry 16` no la dispara.
- La vía `lbtrophies`/`Entrance.lua` se **abandonó**: `Entrance.lua` enraíza en `content\Entrance`, carpeta que **no existe** en la instalación; el usuario tiene el trofeo/celebración de UCL/UEL en `content/cinematics` y pide usar el **módulo cinematics**, no `Entrance`.
- Pendiente: conseguir que el juego muestre la ceremonia de copa con los trofeos UEL/UCL del usuario desde `content/cinematics` (tabla de trofeos/escena posterior), o documentarlo como limitación.

### 4.3 Resuelto esta mañana: "Liga FUTVE" prematuro en el palmarés

- Síntoma: con el Clausura sin jugar, el palmarés ya mostraba "Liga FUTVE 1".
- Causa: las **entradas placeholder** de la 175 (`191:1,192:1`) en `CompetitionEntry.bin`; el juego las contaba como título.
- Arreglo: el mundo se genera **sin filas de la 175** (1.437 entradas, 175 con 0). Falta confirmarlo en la próxima prueba con el palmarés abierto antes de la final.

## 5. Estado del palmarés (dato importante)

El palmarés del técnico **no lee** nuestro DLL ni el `fl26world.txt`: lee los **registros de competición de la carrera** (el campeón de cada competición en la temporada, en el save del Master League). Por eso el título directo de la Final del FUTVE aparece como "Liga FUTVE" aunque el DLL no jugara el partido. El DLL sólo decide que la 175 se resuelve y con qué campeón; el registro lo hace el juego.

## 6. Próximos pasos (en orden)

1. **Rejecutar la prueba de la fase 3** con el mundo nuevo (175 sin entradas) y comprobar en el palmarés que "Liga FUTVE" **no** aparece antes de la final del 167.
2. **Campeones de las finales**: implementar la lectura desde el `kolike` (128) o desde los registros de carrera; con eso el 263 se llena y el 175 aparece en el calendario del 167.
3. **Celebración**: resolver la ceremonia de trofeo desde `content/cinematics` (o documentar la limitación del juego).
4. **Fase de plazas continentales** (siguiente bloque del plan).

## 7. Comandos útiles

```powershell
# prueba completa de la fase 3 (sandbox con backup/restore)
python tools/futve_test.py --phase 3 --game "G:\Games\SP Football Life 2026"

# regenerar el mundo de las finales (base fase 2, sin filas 175)
python tools/futve_finals.py --base out/futve/world-phase2/common/etc/pesdb `
  --world out/futve/world-phase2/fl26world.txt --out out/futve

# logos y cinemáticas
python tools/futve_logo.py --make
python tools/futve_cinematics.py --make --game "G:\Games\SP Football Life 2026"

# DLL (zig; cache en out/tmp para no tocar AppData)
$env:ZIG_GLOBAL_CACHE_DIR="$PWD\out\tmp\zig-global"
$env:ZIG_LOCAL_CACHE_DIR="$PWD\out\tmp\zig-local"
out\tools\py\ziglang\zig.exe cc -shared -target x86_64-windows-gnu -O2 -s `
  -I tools/native tools/native/fl26swiss.c -o out/futve/bin/fl26swiss.dll -lkernel32

# tests
python tools/test_futve_finals.py
python tools/futve_test.py --self-test
```

## 8. Archivos y commits relevantes

- `tools/futve_finals.py` — mundo de las finales (cids 142/129/175, 175 sin entradas).
- `tools/futve_test.py` — sandbox de la fase 3 (40 archivos, backup/restore, evidencia).
- `tools/futve_cinematics.py` — `cinematics.lua`/`cinematicsB.lua` para 261/262/263.
- `tools/futve_logo.py` — 30 emblemas de 134/135/142/129/175.
- `tools/native/fl26swiss.c` — `ccup_final_note`, `ko_final_winner` (0x00-0x3f + diagnóstico), `ccup_src_winner`.
- `tools/lbtrophies.py` — vía de trofeos **abandonada** (Entrance.lua/content\Entrance).
- `out/futve/world-finals` — mundo generado (1.437 entradas, 175 con 0).
- `out/futve/bin/fl26swiss.dll` — DLL 431.104 bytes (última compilación).
- Commits: `62dee65` (trofeo UEL/UCL + nota 261), `ff8aa8e` (164/167), `961fa9f` (entry 42, obsoleto), `a38af2e` (0x20-0x3f), `eedb5b4` (diagnóstico), `8536f0f` (solo cinematics), `c600a12` (trofeos, después revertido), y el cambio pendiente de la 175 sin entradas.
- Evidencia: `out/futve/tests/20261029-121419` (0 rondas), `20261029-111908` (262 sin ganador), `20261029-102130` (DLL original, 307.712 bytes).
---

## 9. Revisión de la tarde (29/10): causa real del bloqueo §4.1 y arreglo

Comparando la evidencia de **todas** las pruebas (`out/futve/tests/*`), el bloqueo §4.1 no es la ronda prestada del cup 128. Son tres fallos encadenados:

1. **Regresión de `62dee65` (10:40).** `if (ko || g_ccup[k].ko)` hace que `ccup_final_note` corra en la progresión **de los grupos** (reg 260, día 160), cuatro días antes de que se juegue la final del 164. Lee 0, escribe "its final is over on day 160, but no winner was read" y el `said_year` bloquea la temporada: la progresión real de la 262 (día 164) ya no lee nada. Antes de ese commit la lectura funcionaba: `20261029-094102` → `cup 262 -- its final is over on day 164: champion 45ee4002`. Los commits `a38af2e`/`eedb5b4`/`0b43aa0` (tipos de ronda 0x00-0x3f) persiguen una causa que no era.
2. **La 263 nunca se llenaba en junio.** `fill=0` no "reintenta cada tick": `ccup_fill()` sólo corre en la progresión del **reg 2** (agosto, día ~252). Entre el 164 y el 167 nadie la llena. Además, en agosto el respaldo `cup_winner()` (código de derechos) devolvía el campeón de la temporada anterior: `20261029-102130` → "45ed8006 won both feeding cups" cuando la 262 la ganó luego 45ee4002.
3. **La 263 no tenía fecha 167.** `kolike=128` se rechazaba para una copa sin grupos ("left out"), así que su KO habría tomado el calendario de la UCL.

**Ojo con el 261:** desde la prueba de las 09:41 el Apertura **no se llenó en ninguna prueba** (no hay "cup 261 -- its fill day", ni grupos 259, ni partidos 1283/261 en `schedule_entry`; el registro salta de noviembre de 2025 al día 159 de 2026). `ccup_of(261)` sí devuelve `ko=1` (en `085940` se leyó "champion 45ed8006" el día 15). Hay que confirmar cómo se avanzó el calendario en esas pruebas (¿Fast Forward/sim?).

### Cambios en `tools/native/fl26swiss.c` (sin commit)

- `prog_handler`: la nota sólo en la progresión del propio KO (`ko`) y sólo para finales de play-off (`adv`) o finales de dos copas (`src`).
- `ccup_final_note(k, started)`: no bloquea la temporada si no lee ganador (reintenta en la siguiente progresión); guarda el campeón en `g_cupwin` y llama a `state_store()` → queda en `fl26swiss-state.bin` y sobrevive a cargar partida entre el 164 y el 167.
- `ccup_fill_finals()` (nuevo): al leerse el campeón de una final, llena en ese momento la final de dos copas que alimenta (263) si ya se conocen los dos campeones; si son el mismo, título directo como antes.
- `ccup_src_winner()`: para copas nuestras sólo vale el campeón **de esta temporada** (desde la final hasta el rollover de julio); nunca el código de derechos antes de la final. Si el día de la final ya pasó, la copa se llenó esta temporada y no hubo nota, la lee entonces.
- `ccup_fill()`: no vuelve a llenar una final de dos copas ya llenada esta temporada.
- `fl26_swiss_ccup_kolike`: acepta `kolike` también en un KO directo → la 263 se fecha el **167** con el registro del 128.

DLL recompilada con zig 0.16.0 → `out/futve/bin/fl26swiss.dll` (433.152 bytes). La anterior queda en `out/futve/bin/fl26swiss-0b43aa0.dll`. `test_ccup_league.c` y `test_chain_apclau.c` compilan; falta ejecutarlos en Windows (`python tools/test_futve_playoff.py`).

### Qué buscar en el `sider.log` de la próxima prueba

```
cup 261 -- its fill day 3 (day 3)                          ← el Apertura se llena
cup 261 -- its final is over on day 15: champion XXXXXXXX (kept in the state file)
cup 263 -- the final of 261 is over on day 15; the other feeding final is not (...)
cup 262 -- its final is over on day 164: champion YYYYYYYY (kept in the state file)
cup 263 -- both feeding finals over on day 164: filled now (its day 167)
cup reg 263 dated as reg 128 (its knockout): 1 record(s), days 167..167
```

Con el mismo campeón: `cup 263 -- XXXXXXXX won both feeding cups (261, 262); the final is not played`.

### §4.2 (ceremonia): lo que dicen los logs

En `102130` el `trophy_rewrite` del `cinematics.lua` se llamó **sólo antes** de la final 262 ("---- UEFA Europa League F" ×3) y **ninguna vez después**: el juego decide que no hay ceremonia sin preguntar a Sider. Además `trophy_rewrite` devuelve el `entry` global que dejó el último `make_key`, no decide por su argumento `tournament_id`. Siguiente paso de diagnóstico: hacer que `trophy_rewrite` registre su `tournament_id` y decida por él, y comparar contra una final que sí tenga ceremonia (Copa Venezuela o una final UEL) para ver en qué momento la pide el juego.

### Fast Forward y log (añadido)

- El log del DLL era un búfer de 64 KB que el `.lua` vacía cada 32 cargas de archivo; con Fast Forward casi no hay cargas y las líneas se **perdían sin aviso** (por eso en `124205` no hay nada del DLL entre el día 311 y el 160). Ahora: búfer de 1 MB, `drain` de hasta 256 bloques, y si aun así se pierde algo sale `AVISO -- N line(s) of this log lost`.
- Nuevo `ccup_jump_check`: si el calendario salta sobre un día de llenado (copa aún vacía) o un día de partido de una copa llenada esa temporada, sale `AVISO -- the calendar jumped over day D (...) of cup C`. Esa temporada no vale como prueba.
- Checklist de la fase 3 (`futve_test.py`): tramos donde no usar Fast Forward (días ~354..16 y ~138..168), y corregidos los ids 144→175 / 142/143/144→142/129/175.
- `futve_cinematics.py`: `trophy_rewrite` registra cada vez que el juego lo llama (torneo, `match_info`, `entry`) y devuelve 16 para 261/262/263 según su argumento.
- DLL: 434.688 bytes.

### Primer partido de grupos del Apertura perdido (prueba 13:34)

`ccup_fill_ahead` y `ccup_fill_days` salían con `if (d < 1) return;`, pero el día 0 (1 de enero) es real: es la última jornada del 191. El Apertura no se llenaba al acabar su fase regular, sino el día 3, el mismo día de su primera jornada de grupos, que ya había pasado (`cup 261 -- its fill day 3 (day 3)` y luego el calendario empieza en `match_info=1`). El Clausura no lo sufre porque su fase regular acaba el 142 y se llena antes del 145. Arreglado: `d < 0` (−1 = sin día). DLL de 434.688 bytes, recompilada.

## 10. Reglas del formato (confirmadas por Felix, 29/10 tarde) y lo que falta

- **Apertura** y **Clausura**: fase regular de 14 clubes, 13 fechas → los 8 mejores a playoff en 2 grupos de 4 → los ganadores de grupo juegan la **final** → título "Campeón del Apertura" / "Campeón del Clausura".
- **Liga FUTVE** (el título de liga): **sólo** para el ganador de la **Final del FUTVE, ida y vuelta**, entre los campeones del Apertura y del Clausura; si el mismo club ganó las dos finales, el título se le asigna automáticamente, sin final.
- La tabla acumulada **no** da título.

Diferencias con lo implementado:

1. La Final del FUTVE (263/175) es hoy **a un partido** (día 167, calendario del 128). Debe ser **ida y vuelta**.
2. El juego da el título "Liga FUTVE" (liga 11, cid 130) al **líder de la tabla acumulada** el día 142 (`reg 11 -- Apertura + Clausura table ... kept as the final table`). Debe ir al campeón de la 263, que se conoce el 164 (caso directo) o tras la vuelta.
3. En el caso directo (mismo campeón) el palmarés no recibe nada: la 175 no se juega y el juego sólo anota títulos de competiciones que terminan.

Corrección: la "Fase A" de ayer y §4.3 confundieron el título de la liga 130 (tabla acumulada) con el título directo de la 175.
- **Tabla acumulada: se conserva** (requisito para los cupos a Libertadores, fase posterior). Ya existe: `reg 11 -- Apertura + Clausura table from 182 matches kept as the final table` (sólo las 2×91 jornadas de fase regular, sin playoffs), guardada en `fl26swiss-state.bin` como tabla final de la liga 11. Lo que se cambie del título de liga no debe tocar esa tabla.

## 11. Prueba B (29/10 noche) y cambios

- **Fallo:** tras cargar el save previo a la final del Clausura y perderla, no apareció la Final del FUTVE. Causa: el campeón del Clausura de la primera pasada (45ed8006, guardado el día 164) seguía como válido; `ccup_final_note` salía sin leer el resultado nuevo y la 263 se quedaba con "won both". **Arreglo:** la progresión de la propia final siempre relee al ganador y reemplaza el guardado (`champion X replaces the kept Y`); la 263 recuerda con qué dos campeones se decidió y se decide de nuevo si cambian (`its feeding champions changed ... decided again`).
- **Final del FUTVE ida y vuelta:** la fila y el calendario de la 263 se copian de la Supercopa de España (reg 87: 2 clubes, la única final de dos clubes con el bit de gol de visitante, que sólo se lee a dos partidos), con el gol de visitante apagado (empate global → prórroga y penales). `days=167,171`, `kolike=87`. El DLL reparte un día por registro cuando hay tantos registros como días. Mundo regenerado en `out/futve/world-finals`. **A confirmar en juego:** `cup reg 263 borrowed record 0 ... -> day 167` y `record 1 ... -> day 171`.
- **Sonda de títulos (solo lectura):** los días 12-18, 139-145 y 161-175 la DLL compara el bloque de la carrera con el del día anterior y anota en el log los cambios que ponen al club del usuario (o un id de competición nuestro junto a él): `title probe day D ...`. Sirve para encontrar dónde escribe el juego "Liga FUTVE" (día 142) y "Final del Apertura" (día 15). Es el primer paso para mover/escribir títulos.
- DLL 436.736 bytes.

## 12. La sonda encontró el palmarés (prueba del 29/10 noche)

Filas de 12 bytes `{u32 cid, u16 reg, u8 1, u8 x, u32 0}` en `blk+0x17b59f0..` (blk = owner+0x48), sólo con títulos del club del usuario:

| fila | cid | reg | byte | cuándo se escribe |
|---|---|---|---|---|
| 0x17b59f0 | 130 Liga FUTVE | 191 (fase regular Apertura) | 0x0d | día 0 |
| 0x17b59fc | 142 Final del Apertura | 261 | 0x00 | día 15 (tras la final) |
| 0x17b5a08 | 131 Copa Venezuela | 255 | 0x00 | (entre 17 y 139) |
| 0x17b5a14 | 130 Liga FUTVE | 192 (fase regular Clausura) | 0x0d | día 142 |
| 0x17b5a20 | 130 Liga FUTVE | 11 (tabla acumulada) | 0x0d | día 142 |

Las vacías son `ffffffff ffff 00 00 00000000`. Además hay una lista `{u16 reg, u32 club}` de ganadores (261 en `0x1798ca8`, 11 en `0x1799938`).

Conclusión: el juego da "Liga FUTVE" por **cada fase regular** (191 y 192) y por la tabla acumulada (11). Es la lógica de liga del juego; la DLL no la escribe. El arreglo será quitar esas filas (cid 130 con reg 191/192/11) cuando las escriba el juego, y poner una fila `(130, …, 1, 0x0d)` sólo cuando el club gane la Final del FUTVE o las dos finales. Antes de escribir hace falta la estructura completa (inicio de la lista, cabecera, contador): la DLL de la próxima prueba vuelca esas zonas (`title dump day D blk+...`) cada vez que cambian.
- Dato de Felix: con las tres filas cid 130 el palmarés muestra **"Liga FUTVE 1"**. La pantalla agrupa por competición (y, previsiblemente, por temporada): basta una fila cid 130 para que cuente. El arreglo debe quitar **las tres** y dejar como mucho una.

## 13. Prueba B2 (15:37): la 263 se llenó pero no se jugó

- Bien: Apertura completo (relleno el día 0), Clausura perdido 45ed8006 v 45ee0000, `cup 263 -- the final of its two feeding cups: 45ed8006 v 45ee0000`, la 263 llenada, fechada y arrancada el día 164.
- Mal 1: **sin registros de partido**. `ccup_fill_one` recibió el `started` de la progresión de la 262, y el juego sólo registra los ids de `started` cuando la progresión informa un cambio. **Arreglo:** `ccup_fill_finals` llena con `started = 0` → `register_all` propio (`knockout registered, N match record(s)`).
- Mal 2: la Supercopa de España (reg 87) también es **un solo registro** en FL26 (fechado 171). Vuelve la final probada (fila FA Cup, calendario 128, día **167**). Para la ida y vuelta, la DLL registra una vez por sesión `calendar survey reg N -- ...` de 4, 6, 7, 10, 16, 23, 87, 122, 128, 151, 159: hace falta un torneo del juego con final a dos registros.
- Palmarés: al perder la final del Clausura se añadió `(129, 262, 0x00, 0x01)`: el par de bytes parece {campeón, subcampeón}.
- DLL 437.760 bytes.

## 14. Ida y vuelta: cómo decide el juego los partidos de una eliminatoria (leído en FL_2026.exe)

- El calendario de cada regulación lo da el despachador `0x14157f810` (tabla de saltos por reg id). Los registros son `{u32 día, u32 ronda, u32 tipo}` con tipo **0 = ida, 1 = vuelta, 2 = partido único**.
- Las supercopas (86-91, 95, 128-130) usan `0x141581f90`: tabla `0x14298e7c0` con **las dos piernas** (224/0, 227/1) y después un "modo de piernas" del registro de la regulación: `+0x300 >> 29`, que el parser llena desde **CompetitionRegulation +0x10 bits 9-11** (`0x1414f814d`, setter `0x1414c9ed0`):
  - 0 → `0x14157f720`: quita las idas y deja todo a partido único (FA Cup, supercopas, Copa Personalizada 48).
  - 1 → `0x14157f790`: dos partidos salvo la final (UCL 4, Libertadores 10, Copa de Bélgica 122).
  - 2 → ninguno: **todo a dos partidos, final incluida** (AFC Champions League 16, Dinamarca 151).
- Por eso la Supercopa de España (modo 0) volvió con un solo registro.
- **Arreglo:** la 263 lleva modo 2 en su regulación (`d10 = 2ac00400`) y la DLL, al pedir prestado el calendario del 128, vuelve a poner la ida delante del único registro (el vector ya tenía sitio para los dos): `cup reg 263: reg 128's one-match final made two legs (ida y vuelta)`, días 167 y 171. Sin gol de visitante; empate global → prórroga y penales.
- Herramientas usadas: `tools/exe-re/` (desensamblador con capstone, búsqueda de tablas de calendario, referencias y la tabla de saltos).

## 15. Título "Liga FUTVE" (implementado, falta probar)

Volcado del 29/10 (prueba 16:23): el bloque de honores de la temporada del usuario está en `blk+0x17b59e4`:
cabecera `e9070801 ea07061e 0680ed45` (2025-08-01, 2026-06-30, club) y 15 filas de 12 bytes. Al final de la temporada tenía:
`(130,191,1,0d) (142,261,1,0) (131,255,1,0) (130,192,1,0d) (130,11,1,0d) (129,262,0,1) (175,263,1,0)`.

- `honours_fix()` (cada día, sólo de enero a junio): quita las filas de la liga partida (regs 11/191/192) y la victoria en la 263; si el campeón de la Final del FUTVE (o el de ambas finales) es el club del usuario, añade **una** fila `(cid de la liga, 11, 1, 0x0d)` → "Liga FUTVE". La derrota en la 263 conserva su fila de subcampeón. Log: `honours -- day D: N row(s) ... taken out, the Liga FUTVE given/not given`.
- El cid llega del mundo (`league 11 cid=130` + `split 11 ...`) por la nueva exportación `fl26_swiss_title_league` (fl26swiss.lua).
- Si la cabecera no coincide (año, mes, club) no toca nada y lo dice una vez.
- Pendiente aparte: las noticias de la Master League no tratan la ida y vuelta como final (los registros son ida/vuelta, tipo 0/1, no "final única", tipo 2).
- DLL 440.832 bytes.

## 16. Noticias de "final" con ida y vuelta (investigación, sin cambios)

- `match_info` (Sider) es la ronda: 53 = 0x35 = final. Las dos piernas de la 263 llegan con `match_info=53`, igual que las finales únicas 261/262.
- Registro de partido: `+4 u16 reg, +6 u8 ronda, +7 flags`: 0x40 jugado, bits 4-5 = tipo (0 ida, 1 vuelta, 2 único). Vistos: final única `06013520`, ida `07013500`, vuelta `07013510`.
- El juego separa "partido único" de "ida/vuelta" con `dword(+4) & 0x30000000 == 0x20000000` en: el decisor de eliminatorias `0x14133181d`, el predicado `0x14154fc70` (para una copa eliminatoria —tipo 3— devuelve "sí" sólo si el partido es único; lo llaman 10+ sitios: 0x140ab8cfb, 0x140c4f3eb, 0x140cd6aaf, 0x140ed7e45…) y `0x141fc76d0`.
- `0x14154e6c0` asigna a la final (ronda 0x35) de ciertas regulaciones del juego (10, 23, 24, 26, 27, 28, 89, 137, 142, 164) un código propio; nuestras 261-263 no están, y aun así las finales únicas sí salieron en las noticias.
- Hipótesis: las noticias tratan como final sólo un partido de ronda 0x35 **y** único (tipo 2). La vuelta (tipo 1) no cuenta. Siguiente paso propuesto: una sonda que anote quién llama a `0x14154fc70` para los partidos de la 263 frente a los de la 262, para encontrar el generador de noticias.
- Scripts: `tools/exe-re/pat*.py`.
- **Sonda añadida** (DLL 441.344 bytes): gancho de solo lectura en `0x14154fc70` (15 bytes copiados al trampolín, firma comprobada). Por cada combinación distinta (llamador, regulación 261/262/263, tipo de pierna, respuesta) escribe una vez `single-match probe -- caller 0x... asks about reg R, round 0x35, leg kind K: yes/no`. Comparar los llamadores de la 262 (única, sale en noticias) con los de la 263 (ida/vuelta, no sale).

## 17. Playoff del Apertura contado doble (30/10)

Desde que el Apertura se llena el día 0 (`ccup_fill_ahead` al acabar la fase regular 191), cada partido de grupos se registraba **dos veces**: el grupo se registra solo (`24 under its groups`) y además se metía en el `started` de la progresión del 191, que devuelve 1 (`groups filled by 0x141343d70 -> 1`), así que el juego lo volvía a registrar → puntos y partidos jugados dobles. El Clausura no: la progresión del 192 devuelve 0. **Arreglo:** `ccup_fill_ahead` llena con `started = 0`. La carrera de esa prueba conserva los partidos duplicados; hace falta carrera nueva.

Ya visto en esa prueba: `honours -- day 1: 1 row(s) of league 11 ... taken out, the Liga FUTVE not given` → el título de la fase regular del Apertura ya no aparece.

## 18. El Palmarés lee el historial de ganadores (30/10)

Captura de Felix tras ganar la Final del FUTVE: "Liga FUTVE 1" (ya antes de la vuelta) y "Final del FUTVE 1", aunque el bloque de la temporada tenía sólo una fila de liga. La pantalla cuenta el **historial de ganadores**: entradas `{u16 reg, u16 0, u32 club}` en `blk+0x1790000..0x17b0000`, una racha por competición y una entrada por temporada (261 en `+0x1798ca8`, 11 en `+0x1799938` el día 142, 263 en `+0x1799f80` tras la vuelta).

`winners_fix()` (dentro de `honours_fix`, enero-junio): las entradas de la 263 quedan sin club (el título "Final del FUTVE" no existe); la entrada de esta temporada de la liga 11 (la última de su racha, una vez pasado el relleno del Clausura) lleva al campeón de la Liga FUTVE, o ningún club mientras no se decida. Log: `winners history -- day D: blk+... reg R club X -> Y`. DLL 442.880 bytes.

## 19. Estado al cierre del 29-30/10 y prueba siguiente

**Confirmado en juego:** primer partido del playoff del Apertura (relleno el día 0); playoff del Apertura contado una sola vez (§17, confirmado por Felix); Final del FUTVE ida (167) y vuelta (171) cuando se pierde el Clausura; noticias de "la gran final" y de la victoria con ida y vuelta; fila de liga del bloque de la temporada corregida (`honours -- day 1 / 143 / 172`).

**Corregido, falta probar (DLL 440.832 bytes, `out/futve/bin`):**
- "Liga FUTVE" y "Final del FUTVE" en el Palmarés vía el historial de ganadores (§18).
- Quitadas las sondas ya innecesarias (pregunta "partido único" y repaso de calendarios). Se mantiene la sonda/volcado de títulos (sólo lectura) para verificar §18.
- Checklist de la fase 3 de `futve_test.py` reescrito con lo que hay que ver.

**Pendiente:**
- Celebración con trofeo tras las finales (tampoco la tiene la Copa Venezuela).
- Comentaristas (final, clasificación/eliminación en grupos): sin investigar.
- Supercopa de Venezuela (`scup=256`): comprobar que toma al campeón de la Liga FUTVE (la final), no al líder de la tabla acumulada.
- Plazas a Libertadores desde la tabla acumulada (fase siguiente).
- Nada de esto está en commits: cambios en `tools/native/fl26swiss.c`, `sider/experimental/fl26swiss.lua`, `tools/futve_finals.py`, `tools/futve_cinematics.py`, `tools/futve_test.py`, `tools/exe-re/`, `out/futve/*`.

## 20. Prueba 3 del 30/10: el Palmarés del técnico sigue mostrando ambos títulos

El log muestra la DLL corrigiendo **al día siguiente**: `winners history -- day 143: reg 11 club 45ed8006 -> ffffffff` y `day 172: reg 11 -> 45ed8006, reg 263 -> ffffffff`; bloque de la temporada corregido los días 1, 143 y 172. Dos posibilidades:
1. **Momento:** el juego escribe el título en la progresión (día 142 / tras la vuelta del 171) y la DLL corregía en el bucle del día siguiente; mirado ese mismo día, se ve sin corregir. **Arreglo:** `honours_fix()` también justo después de la progresión de la liga partida (191/192 y el total 11) y de cada final nuestra.
2. **Otro registro:** el Palmarés **del técnico** puede leer un tercer registro sin el club al lado. La sonda ahora anota también cualquier hueco de cid 130/175 que se llene en cualquier parte del bloque (región ampliada a 128 MB y su tamaño real en el log).
DLL 441.344 bytes.

## 21. Búsqueda en toda la memoria (30/10 tarde)

Save cargado tras el día 142 con la DLL que busca: **0 coincidencias** de las filas de 12 bytes `(130, 191|192|11, 1, 0x0d)` en 4,3 GB de memoria de lectura/escritura (días 165 y 167), y los dos registros conocidos corregidos (bloque de la temporada sin fila 130; historial `blk+0x1799938` = `{11, ffffffff}`). Aun así el Palmarés del técnico muestra "Liga FUTVE". Lo lee de otro formato. Nueva búsqueda (DLL 442.880 bytes): además pares de u16 `130` junto a `11/191/192` o junto a `2025/2026`, en cualquier orden, alineados a 2 bytes; se leen a mano.

## 22. Títulos: solución provisional por nombres (30/10)

La comparación de memoria alrededor del día 142 (progresión del 192 y día completo) no mostró ningún contador: sólo las filas y el historial ya corregidos. El "1" del Palmarés del técnico viene de un sitio no localizado (registro del técnico fuera de la carrera o cálculo de la pantalla). Mientras se busca el origen en el ejecutable:
- **Nombres:** reg 11 (total de la liga partida, cid 130) = "Tabla acumulada FUTVE" (lo que el juego premia el día 142); reg 263 (Final del FUTVE, cid 175) = "Liga FUTVE". `tools/futve_finals.py` (`LEAGUE_TITLE`, `FF_TITLE`), mundo regenerado; la línea `ccup 263` lleva `cid=175`.
- **DLL:** deja las filas de 11 y 263 del juego y el historial de ganadores tal cual; quita las filas de las fases regulares (191/192) y de finales perdidas; si un club gana las dos finales (sin Final del FUTVE), le añade la fila `(175, 263, 1, 0)` → "Liga FUTVE" (la entrada del historial no, falta saber dónde). Las sondas de títulos quedan apagadas (`FL26_TITLE_PROBES 0`).
- **Hueco conocido:** en el caso automático puede que el Palmarés no cuente el título si el número sale de otra parte. Solución de fondo: encontrar en el ejecutable el reparto del título de liga.
DLL 439.296 bytes.

## 23. Crash al cerrar el Clausura tras cargar un save (30/10 16:27)

Save cargado en el día ~132 → `fl26join.log`: `tables: with [] without [11 191 192 81 82 133 134 135 136]` (las tablas de la liga partida no vuelven con el save), `register_all: 11 is flagged in a season but has no table -- appended` y, al acabar la última jornada del Clausura (día 142), `enter 11: season 2025 is over (final table), +0x2fc reset so the new one can enter` → el juego se cae. Las carreras jugadas de corrido (pruebas 00:04 y 09:42) pasan el día 142 sin esa línea. El cuelgue de las 16:19 tiene la misma línea. **No es el cambio de títulos:** es la carga de un save a mitad de la liga partida (pendiente "Saves", fase 6, en el plan). Mientras tanto: pruebas de corrido, sin cargar saves antes del día 143.

## 24. Nombres confirmados; título automático (30/10 tarde)

Felix: "Tabla acumulada FUTVE" y "Liga FUTVE" (la final) salen bien. Falta el caso automático: ganó Apertura y Clausura y el Palmarés no muestra "Liga FUTVE", aunque la DLL añadió la fila `(175, 263, 1, 0)` el día 164. Hipótesis: para la temporada en curso el Palmarés pregunta al juego quién ganó cada competición (código de derechos `0x1415799e0`, tipo 0), y para una final sin jugar responde "nadie".
- **Gancho en `0x1415799e0`** (15 bytes, firma comprobada): para la final de dos copas, si el mismo club ganó las dos finales que la alimentan esta temporada, responde ese club.
- **Historial de ganadores:** se escribe la entrada `{263, campeón}` en la ranura de esta temporada de la final (la de la liga 11 + 0x648, visto en dos carreras), para que el título quede también después de julio.
DLL 440.832 bytes.

## 25. Liga FUTVE automática en el Palmarés (resuelto, 2026-10-30)

- El Palmarés del técnico cuenta los títulos desde la vitrina de trofeos: blk+0x1798ab0 (cabecera, club del usuario), registros de 0x648 bytes desde blk+0x1798ca8, en orden de obtención, cada uno empieza por {u16 reg, u16 0, u32 club}; el primer hueco libre tiene reg 0xffff.
- El u16 en blk+0x1798b82 NO es el contador (seguía en 3 con 4 registros).
- winners_fix: si el mismo club ganó Final del Apertura (261) y Final del Clausura (262), copia el registro anterior en el primer hueco, con reg 263 y el club → aparece "Liga FUTVE" con el logo de la final, sin jugar 167/171.
- Confirmado en juego: día 164, "added as title 5 (reg 263, blk+0x179a5c8)".
- Pendiente: verificar que el siguiente título que gane el juego no pise ese registro (contador real aún sin localizar).

## 26. Cierre al cargar partidas a mitad de temporada (descartado)

- Según Felix, solo pasó con partidas guardadas de versiones anteriores de los cambios. Con partidas de la versión actual no ocurre, así que no es un pendiente. Si vuelve a pasar con una partida nueva, revisar fl26join (reg 11).

## 27. Supercopa de Venezuela (reg 256) — título y rivales (2026-10-30)

- El juego no escribe el título de una supercopa nuestra (registrada por aug_scup_fill_days fuera de su propio recorrido). Prueba: ICC (107) entró a la vitrina el día 220; la Supercopa ganada el día 227, nada.
- supercup_title_fix (días 182-330): partido jugado y ganado por el club del usuario → registro copiado en el primer hueco de la vitrina con reg 256. No se repite si hay un 256 entre los tres últimos.
- cabinet_watch: log diario (sólo lectura) de la vitrina y del bloque de temporada cuando cambian.
- Rivales (Felix): campeón de la Liga FUTVE (ganador de la Final del FUTVE, o el que ganó Apertura y Clausura) contra el campeón de la Copa Venezuela (255); si es el mismo club, contra el subcampeón de la Copa Venezuela. Mundo: `scupcup=255` en la línea `league 11` (fl26swiss.lua lo pasa como copa de la supercopa); DLL: futve_champion_kept + knockout_runner_now(255).

## 28. Ceremonia de trofeo de nuestras finales (2026-10-30)

- Prueba: al terminar la Final del Clausura el juego llama a `trophy_rewrite` (262 → 16) al pitazo y antes de las estadísticas; aun así no hay ceremonia.
- Sitios de Sider (escaneo `sider site`): trophy-check en RVA 0x1f51855 (`mov ecx,[rbx+0x498]` → `call 0x141e554b0`), trophy-table en 0x1e552ab.
- Preparación del partido 0x141f51780..: bloque de presentación (rdi) +0x5170 torneo (ya reescrito, 16), +0x5174 trofeo, +0x5179 "tipo de partido decisivo". El tipo sale de 0x140a7f370/3b0/3e0 (liga/copa/otro) con el torneo del partido `[rbx+0x498]`, y **todo id ≥ 0xda (218) se toma como 0** → nuestras competiciones (255..263) quedan con tipo 0.
- Flujo posterior 0x1423f0ae0: tipo → caso (5179: 1→1, 4→2, 5→3, 6→4, 8..b→1, resto 0); para el trofeo 16, caso 3 → estado 0x10017 (ceremonia de final), si no 0x10008 (fin normal).
- Arreglo: gancho en 0x141f519b9 (`ceremony_fix`): si el torneo es una final nuestra (ko de ccup; 263 sólo el día de la vuelta; supercopas aug; 255 con c31a==4) y el tipo es 0 → tipo 5. Registra `ceremony -- day ...` con c319/c31a/c31b/c31c/c324/e904.
- Pruebas 30.10. noche: (1) sin línea: today() es -1 en el partido y el gancho salía antes; (2) cuelgue: el stub dejaba la pila desalineada (sub rsp,0x28 → 0x20); (3) el partido no lleva 262 sino **217** (`tournament 217 (as 34, trophy 32): c31a 4, e904 13, kind 0`); (4) con 217 + ronda final (c31a 4) + día de final nuestra → tipo 5 puesto (`a final of ours: kind 5 ..., reg 262`), **y aun así no hay ceremonia**. Con +0x5170 = 34 el caso es el de la UEL (tid 5, 32..34): tipo 5 → estado 0x10032, el mismo camino que una final de la UEL. Falta una referencia: los valores de un partido del juego que sí tenga ceremonia (el gancho registra todos los partidos).
- Referencia ICC (día 219, con ceremonia): `tournament 118 (as 118, trophy 117), c31a 0, e904 22, kind 9`. En el flujo posterior (0x1423f0ae0) el grupo 118..120 da el estado 0x1002f (ceremonia) con tipo 9 y los indicadores +7 de los dos equipos (+0x291f, +0x514f). El grupo por defecto (id > 0xaf, el nuestro 217) da 0x1002f con tipo 5 si ningún equipo tiene +0x2914 == 1. El nuestro llegaba como 34 (grupo AFC, estado 0x10032) y no mostraba nada.
- DLL: al estado inicial 0x10000, una final nuestra se encamina por la vía de la ICC (118, tipo 9) o, si no, por la de defecto (217, tipo 5); se registra el estado de entrada y el de salida de cada pasada (`post-match entry/end`).
- ICC con registro completo (día 219): `tournament 120, kind 9, trophy 117`, flags +7 de los dos equipos en 1 de forma natural, estado de salida 0x1002f → ceremonia.
- Supercopa por la vía de la ICC (118, tipo 9, flags +7 forzados) y luego también con el trofeo 117: estado de salida 0x1002f, **igual que la ICC, y sin ceremonia**. El bloque de presentación queda igual; lo que distingue a la ICC está fuera de él: el partido (e904 22 vs 13, c318 03020000 vs 08020400, c31a 0 vs 4, m+8 1 vs 0) o la competición (la ICC la cierra el juego; la Supercopa la registramos nosotros).
- Estado actual (FL26_CER_ICC 0): la final nuestra conserva solo el tipo 5 (ambiente de final: tifos y pancartas, confirmado por Felix); la vía ICC y el cambio de trofeo, apagados. Siguiente paso: seguir el estado 0x1002f después del partido (quién lanza la escena) o probar con la Final del Clausura (competición que el juego sí cierra).
- Volcados (fl26cer_d219_t120_* ICC, fl26cer_d227_t217_* Supercopa) — bloque del partido (rbx):
  - +0x498.. contexto de la competición: ICC `tid 120 (0x78), +0x49c 117, 04 03, 01, campeón 45ed8006` y una tabla de 4 clubes con sus datos (+0x4bc.., copia en +0x80c.. y +0xbf38..). **La ICC es un torneo de formato liga**: su ceremonia es la de un título por tabla. Supercopa: `0x498 = 217, 0x49c = 217, 02 01, 0`, clubes ffffffff, +0xbf38.. vacío.
  - El contexto lo copia 0x140fdad5c.. desde una fuente (r14: +0x10 tid, +0x14 → +0x49c, +0x18 → +0x4a0 ...), setter de +0x498 en 0x1414dfd90.
  - Conclusión: el juego trata todo id ≥ 0xda (218) como competición desconocida (217) en el contexto del partido; nuestras competiciones (255..263) no llevan tipo, trofeo, campeón ni tabla. La ICC no es buena referencia para una final de copa (es liga).
  - Vías: (a) que nuestras finales usen un id de regulación < 218 (uno libre o de una competición que el mundo no use); (b) reescribir el contexto (+0x498/+0x49c/+0x4a0..) con el de una copa del juego; (c) una referencia de final de copa real del juego.
- Referencia buena (31.10.): final de la Copa Libertadores en Kick Off > Copa, ganada, **con ceremonia**: `tournament 26 (as 26, trophy 23), c31a 4, e904 02, kind 5` (natural), contexto `+0x498 26, +0x49c 23, +0x4a0 10 04, +0x4a4 9`, estado de salida **0x10028** con `+5214 1, +5218 10` (quién levanta la copa). Nuestras finales terminaban en 0x1002f/0x10032, sin ese cálculo.
- DLL: la final nuestra se presenta como la de la Libertadores (bloque de presentación: torneo 26, trofeo 23, tipo 5 → 0x10028). El partido y su competición siguen siendo los nuestros.
- 31.10.: con `trophy_rewrite` devolviendo 10 (la entrada de la Libertadores, como FL), el juego mismo arma la final nuestra con el contexto de la Libertadores (`+0x498 26, +0x49c 23, +0x4a0 0x410, +0x4a4 9`, tipo 5) y llega a 0x10028 — sin ceremonia. La final de la Libertadores de referencia fue en Master League. Diferencias que quedan: los indicadores de cada equipo (+0xe900 5 vs 0, +0xe904 0x13 vs 0x02, +0xeb04 1 vs 0, +0xeb14.. 76/3.5/23 vs 0), +0x2/+0x4 del bloque (0/6 vs 1/0x0b) y la regulación de la carrera en +0x5390 (262 vs 10).
- DLL siguiente: los indicadores +0xe900/+0xe904/+0xeb04 de los dos equipos como los de la Libertadores; y el día de una final nuestra se registra quién consulta el código de derechos (fuente, tipo, respuesta, dirección que llama).
- 31.10. prueba perdida por error mío: usé `pcall` en fl26swiss.lua y cinematics.lua, y **el Lua de Sider no tiene pcall** (ML_FastForward.lua y PCCEFootballDetails.lua ya lo decían). fl26swiss.lua no se activó (sin log del DLL) y el trophy_rewrite de cinematics.lua falló en cada llamada (sin el 10). Revertido. La copia del momento final ahora la hace el DLL solo: la preparación del partido se repite en cada consulta de trofeo (inicio, goles, descanso, final), así que el último volcado `fl26cer_d<día>_t<reg>_last_*.bin` es el del pitazo final.
- 31.10. Final del Clausura con los indicadores de equipo igualados a los de la Libertadores (0/0x2/0) + contexto 26/23/0x410/9 + presentación 26/23/5 → estado 0x10028, **sin ceremonia**. El código de derechos no recibe ninguna consulta por 262 del juego al pitazo final (solo una desde fuera del exe, 0x7ffe...). Entre el comienzo y el final del partido el bloque del partido solo cambia en +0x496 (0x00 → 0x40) y datos de jugadores. Falta la copia del pitazo final de la Libertadores para comparar: el DLL ahora vuelca el "último" de cualquier final (c31a 4).
- CustomExhibitionMatch.lua (mochnaufals): `ctx.mis` apunta a la info del partido del juego, con el id de **competición** (Competition.bin) en +0x00 y +0x84; cambiarlo da el trofeo y el estilo de una competición en un amistoso. Su nota: en Exhibición con la competición cambiada (y match_info 53) **no hay celebración**; en la final a un partido de la KONAMI Cup (un torneo de verdad del modo Copa) **siempre** la hay. Coincide con lo nuestro: los ids de presentación no bastan; la ceremonia la dispara la lógica de la competición del modo que la termina. fl26swiss.lua registra ahora `ctx.mis` (competición en +0/+0x84 y 40 enteros) en cada cambio de torneo/match_info.
- 31.10. Final del Clausura con además la regulación de la carrera en el bloque del partido (+0x5390) en 10: **sin ceremonia**. `ctx.mis`: competición 129 (+0 y +0x84). Los archivos que carga el juego (registro de fl26swiss.lua) muestran el porqué de fondo: tras el pitazo final se reproduce la escena normal de fin de partido (`fixdemo\timeup\cut_data\tu_full_*`), luego la de resultado (`fixdemo\result\...`) y la pantalla de estadísticas; **nunca se pide nada de `fixdemo\end\cut_data`** (END_TROPHY_*). La elección de la escena de trofeo la hace el motor del partido al pitazo final con `common\demo\fixdemo\end\table_end.bin` (extraída de dt12_g4.cpk a $HOME/re/te). Siguiente paso, sin juego: descifrar sus condiciones (qué campos exige END_TROPHY_01_CUP/ACL/ICC) y buscar en el exe quién la lee.
- 31.10. (sin juego) Sistema de escenas: `table_end.bin` se registra como tabla 7 de las demos (0x141f337ee). Las demos se eligen con un lenguaje de condiciones cuyos nombres están en el exe (tablas de punteros a cadenas en 0x14344a870..0x14344d700): tipo de demo (`KIND_TIMEUP`, `KIND_VICTRY`, `CUTID_CUP_LIFT`...), serie de competición (`CUP_LIB`, `CUP_ACL`, `CUP_KONAMI`... 335 entradas), fase (`GL`, `TOURNAMENT`, `CUP_FINAL`, `FINAL_TOURNAMENT`), y la **situación del objetivo** (`CHAMPION`, `WIN_GROUP`, `ACHIEVED`, `ACHIEVED_TODAY`, `FOR_WIN_LEAGUE`, `CUP`, `KNOCKOUT`...). Lo mismo usan los comentaristas (por eso ya dicen "final"). Hipótesis fuerte: la escena de trofeo (`KIND_VICTRY`) pide que la situación del equipo en la competición del partido sea "campeón, logrado hoy", y esa situación la calcula la lógica de competiciones de la carrera, que no cubre las nuestras. Siguiente: localizar quién evalúa CHAMPION/ACHIEVED_TODAY para el partido y por qué deja fuera nuestras competiciones.
- 31.10. Final de la Libertadores medida de punta a punta (ML00000002, día 331, con ceremonia): en el bloque del partido **nada cambia entre el inicio y el pitazo final** fuera de los datos de jugadores; o sea, "campeón hoy" no se marca ahí. Diferencias con nuestra final al pitazo: el historial de la competición dentro del bloque (+0xb70.., +0x6140.. goleadores, por equipo +0xe9b8../+0xeb98..; lleno en la Libertadores, vacío en la nuestra) y la info del partido de Sider (`ctx.mis`): Libertadores `comp 5, +0x04 1, ... +0x58 10, +0x5c 23, +0x60 5, +0x84 5`; nuestra `comp 129, +0x04 0, ... +0x84 129`. Las rondas de eliminatoria de nuestras finales sí existen (kind 0x35, 1 cruce, ganador leído).
- Experimento siguiente (fl26swiss.lua, CER_MIS): en una final nuestra (match_info 53) `ctx.mis` toma competición 5 en +0x00 y +0x84 y +0x04 = 1, como la final de la Libertadores.
- 31.10. `ctx.mis` con competición 5 y +0x04 = 1 en la Final del Clausura: aplicado (al terminar el partido el juego deja `ctx.mis` en 0), **sin ceremonia**; Palmarés sin nada de Libertadores. Apagado (CER_MIS false). fl26swiss.lua guarda ahora sus líneas (las del DLL, archivos, mis) también en `SiderAddons\fl26swiss-session-NNN.log`, una por sesión: el sider.log de la final de la Libertadores se perdió al abrir el juego otra vez.
- 31.10. Comentaristas: en nuestras finales hablan de "final" al empezar, **nunca de título** → el juego no sabe que el partido da un campeón. Competition.bin: la Libertadores (5) y la ICC (100-102) están en la región 1 (`+3 = 0x08`, "club internacional"), la FA Cup en la 2 (0x10); **nuestras competiciones (129 CFI, 131 CUP, 132 SUPER, 142 AFI, 175 FFU) en la región 29 (0xe8)**, fuera de las 0..28 que conoce el juego (la añade el mod). Hipótesis: la serie de competición (CUP_LIB, CUP_ENG...) con que el juego clasifica la competición para comentarios y escenas sale de la región; sin serie, ni título ni ceremonia. Experimento: en la copia instalada (livecpk\_FL26MyWorld, la restaura FIN) esas cinco filas pasan a la región 1 (0x08).
- 31.10. Región 1 para nuestras competiciones: **sin ceremonia** (revertido en la copia instalada).
- Siguiente: rastreo de quién lee la tabla de escenas. fl26swiss.lua registra `livecpk_data_ready` (la dirección de cada tabla `fixdemo\...\table_*.bin` que lee el juego); en una final (match_info 53) la de `table_end.bin` va a `fl26_swiss_guard`: PAGE_GUARD + manejador vectorizado que anota cada instrucción que lee el búfer (RIP, desplazamientos leídos, consulta de trofeo en que ocurrió), re-arma con un paso simple, se informa en cada consulta de trofeo y cada día, y se apaga al día siguiente o tras 4 millones de toques. Solo lectura.
- 31.10. Rastreo de table_end.bin en la final de la Libertadores (sesión 002): 29 instrucciones la leen, **todas al cargarla** (antes del partido, ninguna al pitazo). El lector es un objeto de flujo en 0x1423dca90..0x1423dcdfd con arreglos por tipo sobre el búfer: +0xe8 floats (0x17450.., 2676 = cabecera[0]), +0x100 enteros (0x19e20.., 5352 = cabecera[3]), +0x108 u16 (0x1f1c0.., ~24850 lecturas), +0x110 bytes (0x2b3e2.., 1928 = cabecera[5]), +0x118 cadenas (0x2bb6a..), +0xf0 desplazamientos de nombres (0x3c..). Es decir: table_end.bin es un programa compilado (códigos u16 con operandos de esas tablas) que el juego decodifica al cargar; la elección al pitazo usa lo decodificado. Las condiciones no llevan nombre en el archivo: son números que el motor resuelve con tipos como `EndDemoStatus`, `ObjectiveKind`, `ObjectiveCheckKind`, `CompetitionKindEx`, `RegionForCompe`, `MatchMeanning` (nombres en 0x1425d4018..0x1425d4208, tabla de tipos en 0x14344a588..).
- Vía propuesta (sin parchear el exe, como el resto de FL): descifrar ese programa offline y servir por livecpk una table_end.bin con la entrada de trofeo condicionada a algo que nuestras finales sí cumplen.
- 31.10. Formato de table_end.bin (en curso): lo deserializa 0x141f40c80.. (objeto en r13): u16 nº de categorías (si 1, se relee) → pares u16/u16 en r13+0x98; nombres (cadenas) → r13+0xc8; u16 nº de entradas → registros de 0x78 bytes en r13+0xb0 (por entrada: hasta 10 u16 y hasta 10 cadenas, contados por dos bytes leídos antes); subobjetos de condiciones por 0x141ed3c80 (7 bytes de conteo en +0x60..+0x65,+0x69 y listas de objetos de 0x38/0x40 bytes). Lector: 0x1423dce10 (abre), 0x1423dcac0 u16, 0x1423dcae0 byte, 0x1423dcbc0 entero, 0x1423dca90 float, 0x1423dcb00 cadena. Copias: out/futve/re/table_end.bin (extraída de dt12_g4.cpk) y los flujos de pantalla; scripts en tools/exe-re (cpk.py lee el TOC de un CPK, disp_find/imm_find/rangefind buscan en el exe).
- Requisito (Felix, 31.10.): la ceremonia es del **ganador del partido**, sea o no el club del usuario: si el usuario pierde, celebra el rival. La condición de la tabla no puede mirar al usuario; quién levanta la copa ya lo calcula el juego (estado 0x10028: +0x5214 el lado ganador, +0x5218 el jugador). Casos: ganador por penales; en la Final del FUTVE a dos partidos, el ganador del global en la vuelta.
- 31.10. (sin juego) Formato completo de table_end.bin (deserializador 0x141f40c00, tipo 7): parte A (pares u16 + nombres de categoría), parte B (entradas de 0x78: hasta 10 u16, hasta 10 cadenas, entero +0x68, float +0x6c, entero +0x70), parte C (pares + nombres) y parte D (cortes de 0x38: tipo, float, enteros, bytes, u16, tríos de bytes). Lo decodificado queda en el gestor de demos (singleton 0x140a7cc00): mgr+0x168+tipo*0x20 = {pares, nombres, nº, entradas} y mgr+0x8+tipo*0x20 = {pares, nombres, nº, cortes}. **La tabla no contiene condiciones con nombre**: es un catálogo de escenas; quién elige `KIND_VICTRY` lo decide el código según la situación del objetivo. Modificar la tabla sola no basta.
- Siguiente rastreo (fl26swiss.dll, cer_guard_end): en la preparación de cualquier final (c31a 4 o final nuestra) el DLL toma el gestor de demos y pone páginas de guarda sobre lo **decodificado** de la tabla 7 (pares, nombres, entradas, pares de cortes, cortes), varias zonas a la vez (gt_add). Quien lo lea al pitazo final es el selector de escena: comparar su camino en la Libertadores (con ceremonia) y en la nuestra (sin) dice qué condición falla. Solo lectura.
- 31.10. FIN borró las tres partidas ML (creadas durante la prueba del 30.10 22:34, así que no estaban en su copia inicial). Recuperadas desde `out/futve/tests/20261030-223457/evidence/save/save/` (idénticas byte a byte). futve_test.py: `keep_save` — FIN ya no borra ni revierte los archivos ML* de la carpeta de partidas; el resto sí se restaura.
- 31.10. (pedido de Felix) Las carreras de prueba son del sandbox: viven en `out/futve/careers/` (ignorado por git; ML00000000/01/02). Al iniciar una prueba se copian a la carpeta de partidas; al dar FIN (o ABORTAR/--restore) cada ML* que la sesión creó o cambió vuelve al almacén con su progreso y sale de la carpeta. Una carrera propia del usuario con el mismo nombre queda en el snapshot y vuelve en FIN. Se quitó `keep_save`.
- 31.10. Primer intento de cer_guard_end colgó la carga: vigilaba al preparar la final la tabla decodificada ANTERIOR, que la carga libera y reutiliza (una lectura de archivo sobre página con guarda falla). Corregido: solo vigila desde la 2.ª consulta y si la tabla ya se recargó; se apaga en el postpartido, el día siguiente o a las 300 000 lecturas.
- 31.10. Prueba (sesión 002: Libertadores día 331 con ceremonia + Final del Clausura 262 sin ella): la guarda sobre lo decodificado de la tabla 7 en el gestor (pares, nombres, entradas, cortes) **no registró ningún lector** en ninguno de los dos partidos, ni siquiera durante la ceremonia de la Libertadores → la reproducción no usa esas copias del gestor (o el gestor guarda otra cosa en esos campos). Hallazgo clave del registro de archivos: al pitazo final la Libertadores pide `fixdemo\end\cut_data\end_timeup_03`, `end_joy_*` y luego `end_trophy_01_cupclubsouth` + `dml_end_trophy04_cup_conmebol_libe`; la nuestra pide `fixdemo\timeup\cut_data\tu_full_*` y `tu_pickup_undershirt_*`. Es decir, la decisión no está dentro de la tabla end: **al pitazo el juego elige qué tabla de escenas usar, `end` (partido que decide un título) o `timeup` (partido normal)**; nuestra final cae en `timeup` antes de llegar a ninguna condición de trofeo. Siguiente: localizar esa elección (quién pide la demo de tipo 7 frente a la de timeup al final del partido).
- 31.10. Cabecera del bloque del partido (volcados fl26cer_*): Libertadores `01 00 01 00 0b 07 01 32 | 01 00 00 00`, ICC `01 00 01 00 08 07 01 2b | 01 ..` (ambas con ceremonia); Clausura nuestra `01 00 00 00 06 07 01 33 | 00 ..`, Supercopa nuestra `01 00 01 00 08 07 01 2c | 00 ..` (sin). **El dword +8 vale 1 solo donde hubo ceremonia.** El vocabulario de entorno del partido del exe empieza por `DECIDEMATCH` (0x14344d610: DECIDEMATCH, HOMEAWAY, 1STLEG, 2NDLEG, EXTIME, PKMATCH, ONLINE, ENTERDEMO). Hipótesis: +8 = "este partido decide un título" → al pitazo el juego usa la tabla `end` (tipo 7) en lugar de `timeup` (tipo 6; registro 0x141f33680: 1 ent, 2 foul, 3 goal, 4 pk, 5 change, 6 timeup, 7 end, 8 result, 9 mode). Experimento: en el partido decisivo nuestro (hit) +2 = 1 y +8 = 1. El rastreo de guarda queda apagado (CER_GUARD 0).
- 31.10. Sesión 003 (Final del Clausura con +2 = 1 y +8 = 1 todo el partido): **sigue pidiendo `timeup\tu_full_*`, sin ceremonia**. +8 no es (o no basta). Apagado (CER_DECIDE 0). Pista estática: 0x141f58229.. es un selector que elige entre los tipos de demo 5..8 (`mov eax,7` / `mov eax,6` con cmov según banderas en dil), candidato a la elección end/timeup; sin confirmar.
- Siguiente medición (sin cambios en el partido): `fl26_swiss_stack` — fl26swiss.lua la llama cuando el juego pide un archivo de `fixdemo\end\cut_data` o `fixdemo\timeup\cut_data`, y el DLL registra la pila del hilo (direcciones del exe). Comparar la pila de la Libertadores (end) con la nuestra (timeup) señala el código que elige.
- 31.10. Sesión 004 (pilas): las peticiones de escenas (end en la Libertadores, timeup en la nuestra) vienen del mismo hilo (3456), pero RtlCaptureStackBackTrace se corta en el trampolín de Sider (sin datos de desenrollado): ningún marco del juego. fl26_swiss_stack ahora también recorre la pila cruda (qwords que apuntan al exe justo después de una instrucción call = direcciones de retorno). Copia del log en out/futve/re/sessions-20261031/fl26swiss-session-004-stack.log.
- 31.10. Sesión 005 (preparada): además de la pila cruda, la final decisiva nuestra lleva la cabecera completa de la final de la ICC (+2 1, +4 8, +8 1; CER_DECIDE 1). La Libertadores no se toca: su pila sigue siendo la referencia.
- 31.10. Sesión 005: el juego se cerró en el medio tiempo de la Libertadores, en la primera lectura cruda de la pila (último log: tu_half_cmn_01_cam). Corregido: solo valores dentro de las secciones ejecutables del exe y con la página comprobada (VirtualQuery: comprometida, legible, sin guarda) antes de leer los bytes de la instrucción call.
- 31.10. Sesión 006: mismo cierre en la primera pila. Causa probable: el recorrido usaba la base de la pila del TIB y hasta 0x20000 bytes; si Sider ejecuta el Lua en otra pila (o la región es más corta) se lee memoria no comprometida. Ahora: el límite es la región comprometida de la pila actual (VirtualQuery, máx. 0x10000) y no se lee nada del exe en tiempo de juego (solo se anotan valores dentro de sus secciones ejecutables; se verifican fuera de línea).
- 31.10. Sesión 007 (pila cruda, sin cierre): todas las peticiones de escenas (medio tiempo y final, Libertadores y nuestra) tienen la misma pila: 1415ab7f2 … 1414b0ae4 141b3779c — el hilo de carga de archivos, no la lógica del partido. Cabecera ICC (+2 1, +4 8, +8 1) en nuestra final: sigue timeup. Apagado (CER_DECIDE 0).
- Estático: 0x141f577b0(this, petición) es el despachador de escenas: petición +4 = tabla (2 foul y 9 mode aparte, 10..16 otra función, el resto 0x141f58160 que la reproduce). Gancho nuevo en su entrada (demo_install): registra cada petición; en una final nuestra, la petición 6 del pitazo final (más de 60 s después de la primera 6, la del medio tiempo, y con +0x496 bit 0x40) pasa a 7 → escenas `end` del propio juego (CER_END 1).
- 31.10. Sesión 008: 0x141f577b0 **no** es el despachador de escenas: sus peticiones son listas de tipo 0 (11), 1 (11), 2 (3) y una 10, al empezar, en el descanso y al final, nunca 6/7. Gancho apagado (DEMO_HOOK 0). Copia del log en sessions-20261031.
- Archivos .fdc (extraídos a out/futve/re/fdc): cada uno es un elemento de una escena (cabecera u32 = tipo de elemento: tu_full_00_cut 1, end_timeup_03 4, end_trophy_01_cupclubsouth 6) y referencia animaciones (.gani/.seq) y utilería (cup_club_south_hi.fpk), **no a otros .fdc**: qué elementos forman una escena lo dice la tabla. Un cambio de archivo por archivo (timeup → trophy) no compone una escena de trofeo válida.
- Balance del día: descartados como disparador de la escena de trofeo: tipo de presentación, contexto ICC/Libertadores, banderas de equipo, reglamento de la carrera, ctx.mis, región de la competición, cabecera del partido (+2/+4/+8). La decisión es end (7) vs timeup (6) al pitazo; falta localizar en el exe dónde se pide la escena por número de tabla. Siguiente trabajo sin juego: seguir desde el registro de tablas (0x141f33680: objetos de tabla con su índice en el contenedor rcx+0x440) hasta la función que reproduce una tabla por índice, y sus llamadores con 6/7.
- 31.10. Estático (sin juego): el lector por tipo del gestor no aparece con desplazamientos fijos (0x228..0x260, 0xc8..0x100) ni con índice*0x20+0x168 en la zona de demos (el único `shl 5 / +0x168` es 0x141edb3c0, otra estructura por lado de equipo). El contenedor de objetos de tabla (this+0x440, 0x141f33688) tampoco tiene lectores claros. Conclusión: la búsqueda estática a ciegas no converge.
- Medición nueva (sesión 009, solo lectura): cuando el hilo de carga pide un archivo de escena, el DLL suspende un instante el hilo del partido (el que ejecuta la preparación, g_match_tid), copia sus registros y hasta 64 KiB de su pila, lo reanuda y después registra los valores que caen en el código del exe. Esa pila sí es la de la lógica que pidió la escena.
- 31.10. Sesión 009 (Libertadores): el "hilo del partido" (el que ejecuta la preparación) es un hilo trabajador del sistema de tareas del juego (entrada 141b3779c, despacho 141b64c86); cambia entre partidos (38232, 39280) y al pedir las escenas casi siempre está ocioso. Muestras útiles pocas y no relacionadas (0x140e93xxx: actualización de interfaz/sonido; sus `mov eax,7/6` son mapeos de interfaz). La lógica que pide la escena corre en otro trabajador: el muestreo no la encuentra.
- 31.10. Último intento (sesión 010, acordado con Felix: si falla se documenta y se pasa a otra cosa): **préstamo de competición**. En la final decisiva nuestra, el registro del partido de la carrera (ko_match, +4 = reglamento) toma el reglamento 10 (Copa Libertadores) durante el partido; vuelve al suyo en la escena de resultado del pitazo (`result_env_full`, fl26swiss.lua → fl26_swiss_borrow_end) o, como red, al día siguiente (bucle diario). La detección de la final reconoce el registro prestado (g_borrow_mr). Pilas apagadas (CER_STACKS 0). Riesgo: si algo de la carrera lee el registro antes de devolverlo, podría tocar la Libertadores: tras la prueba, salir sin guardar.
- 31.10. Sesión 010 (préstamo del reglamento 10 en el registro del partido): aplicado y devuelto en `result_env_full` como estaba previsto; **sigue `timeup\tu_full_*`, sin ceremonia**. Apagado (CER_BORROW 0).

### 29. Ceremonia de trofeo — estado al cierre del 31.10. (aparcada)
- **Qué pasa**: al pitazo final el juego elige el juego de escenas `end` (tabla 7: `end_timeup_*` → `end_joy_*` → `end_trophy_*`, con la copa) cuando el partido cierra una competición, o `timeup` (tabla 6: `tu_full_*`, `tu_pickup_*`) si no. Nuestras finales caen siempre en `timeup`; la Libertadores y la ICC en `end`. Los comentaristas tampoco hablan de título: el juego no considera que el partido decida nada.
- **Descartado** (cada uno probado en una final nuestra, sin cambio): presentación kind 5 / 26 / 23; vía ICC (118, kind 9, trofeo 117); contexto del bloque del partido 26/23/0x410/9; trophy_rewrite → 10 (el juego rellena el contexto él mismo); banderas de equipo 0/0x2/0; reglamento de la carrera en el bloque (+0x5390 = 10); `ctx.mis` competición 5 y +4 = 1; región 1 en Competition.bin; cabecera del partido (+2/+8, y +2/+4/+8 como la ICC); préstamo del reglamento 10 en el registro de la carrera durante el partido.
- **Mediciones que no encontraron el punto de decisión**: guardas sobre table_end.bin cruda (solo se lee al cargar) y decodificada (ningún lector durante el partido, ni en la Libertadores); pilas de las peticiones de archivos (hilo de carga), pila cruda (mismo hilo), muestreo del hilo de la preparación (trabajador del sistema de tareas, ocioso); el gancho a 0x141f577b0 (no es el despachador de escenas).
- **Lo que sí se sabe del exe**: registro de tablas de escenas 0x141f33680 (1 ent … 6 timeup, 7 end, 8 result, 9 mode); deserializador 0x141f40c00; gestor de demos 0x140a7cc00 (+0x168+tipo*0x20, +0x8+tipo*0x20); vocabulario de condiciones (EndDemoStatus, ObjectiveKind CHAMPION, ObjectiveCheckKind ACHIEVED_TODAY, MatchEnv DECIDEMATCH 0x14344d610…). Hipótesis más sólida: la escena `end` exige que la lógica de objetivos de la carrera marque al equipo como campeón "logrado hoy" en la competición del partido, y esa lógica no cubre competiciones con id ≥ 218.
- **Qué queda activo**: el gancho de la preparación (presentación 26/23/kind 5, contexto 26/23/0x410/9, banderas, +0x5390 10) y trophy_rewrite 10 en cinematics.lua: no dan ceremonia, pero tampoco causan problemas conocidos (ambiente de final correcto). Diagnósticos apagados: CER_GUARD, CER_DECIDE, CER_STACKS, CER_BORROW, DEMO_HOOK = 0. Para el PR: quitar o dejar tras opción.
- **Si se retoma**: buscar quién evalúa `ObjectiveCheckKind` / `ACHIEVED_TODAY` (las tablas de nombres en 0x14344a870..0x14344d700 se usan para analizar cadenas; seguir sus usuarios hasta el evaluador), o la opción de ids < 218 solo para las finales.

### 30. Ids prestados (idea de Felix, 31.10.) — hallazgo y prueba decisiva
- **El mapa reglamento → torneo del exe**: 0x141e53910 (cx = reglamento | etapa << 10) busca en 330 pares fijos (extraídos: reg 10 → 26 final de la Libertadores, 6 → 21 final de la UEL, 4 → 14 final de la UCL, 23 → 121 FA Cup…) y responde **0xd9 = 217 para todo lo demás**: es el 217 que llevan todos nuestros partidos. Clasificadores por torneo: 0x141e552d0 (tipo: 10 = final de copa —14, 21, 26, 121, 176, 191—; 11 = genérico, también la ICC 118-120), 0x141e554b0 (trofeo: 26 → 23, 118 → 117, 30 → 27).
- Reglamentos del juego base que este mundo **no usa** y que el exe conoce (candidatos a préstamo): 12/13/14 → 29/30/31 (la Sudamericana original; la de FL26 es la 257/258 propia), 33 → 129, 49 → 114, 60-66, 69-78 (78 → 26), 93/94 → 157/158, 98 → 130, 100-102, 142 → 140. Tipo 10 (final): 30, 129, 130, 140, 149.
- Nota: los ids de **competición** (Competition.bin) ya son bajos (130 Liga FUTVE, 131 Copa, 132 Supercopa, 142/129/175 finales); los ≥ 218 son los reglamentos 255, 256, 259-263, de 16 bits (byte +2 y +3 del registro: 261 = 05 01, sin colisión con la UEL 5).
- Prueba (sesión 011, TMAP_HOOK 1): gancho en 0x141e53910 — para 255, 256, 261, 262, 263 responde 30 (final de la Sudamericana original, tipo 10, trofeo 27) y registra quién pregunta. Disfraz de presentación apagado (CER_PRES 0) para ver el comportamiento propio del juego. Sin renumerar nada del mundo.
- 31.10. **Sesión 011: FUNCIONA.** Final del Clausura (262) con el mapa reglamento → torneo respondiendo 30: al pitazo el juego pide por sí solo las escenas `end` (end_timeup_01b, end_joy_*, …) y Felix ve la celebración con copa. Sin disfraz de presentación (CER_PRES 0). Quién pregunta el mapa por 262: 0x141fc61e8, 0x141fc656a, 0x141fc678c, 0x141fc68b0, 0x141fc7958, 0x141fc7ebf, 0x141fc8611, 0x141fc8dd8, 0x141fc8f45 y 0x141fca0ee (muchas veces), todos en la preparación del partido. Log: out/futve/re/sessions-20261031/fl26swiss-session-011-tmap-OK.log. **Confirma la hipótesis: la escena de trofeo depende de que el reglamento del partido tenga un torneo conocido en el mapa del exe.**
- Pendiente para dejarlo bien: (1) qué trofeo/nombre muestra y si el Palmarés queda bien al guardar; (2) que celebre el rival si el usuario pierde; (3) la Final del FUTVE a dos partidos — el mapa no distingue ida y vuelta: la ida podría dar ceremonia (responder 217 en la ida); (4) Copa Venezuela y Supercopa; (5) un torneo prestado por final, configurable en el fichero del mundo, y quitar el resto de experimentos (presentación, banderas, contexto, diagnósticos) para el PR.
- 31.10. Final del FUTVE a dos partidos: tmap_handler responde 217 (sin torneo, sin ceremonia) a 263 cuando el partido del usuario de hoy es la ida (registro del partido +7 bits 4-5 = 0, la misma lectura que ceremony_fix); la vuelta responde 30. Palmarés tras guardar la final del Clausura con el préstamo: correcto (Felix).

## FASE 4 — Liga FUTVE de enero a diciembre (empezada 31.10.)
Decisiones de Felix: solo para la Liga FUTVE (sin tocar Mod Studio), calendario como el real 2026, carrera nueva. **La fase 3 queda congelada**: su DLL, Lua y fuente en out/futve/phase3 (sha DLL c349cdcd…), y futve_test `--phase 3` instala esas copias; `--phase 4` usa out/futve/bin, el Lua del repo, el mundo out/futve/world-calendar y las carreras out/futve/careers-phase4.

Real 2026 (Wikipedia): 14 clubes; Apertura 29 ene – 7 jun (todos contra todos, dos cuadrangulares de 4, final entre los ganadores); Clausura desde el 31 jul, mismo formato; Gran Final entre ambos campeones en diciembre; tabla acumulada para Libertadores/Sudamericana y descenso.

Lo que hay en 0.2.5: `season <región> 1` hace de una región de las nuestras una de enero-diciembre (fl26joindll/fl26join, fl26swiss calyear: rondas entre el día 45 y el 333); Mod Studio **rechaza** Apertura/Clausura en esas regiones porque las fases del split se datan sobre la línea escocesa (agosto-mayo, split_dates/SCOT_DAYS). Las ligas nuestras de enero-diciembre entran en su temporada el **día 41** (registro del id 9 por 0x141343bf0 + fl26join): su primera jornada no puede ser antes de mediados de febrero, y en una carrera que empieza en agosto la primera temporada de la liga empieza el febrero siguiente.

Plan:
1. Mundo world-calendar = world-finals + `season 29 1` + días explícitos para las fases 191/192 (línea nueva solo de la fase 4, p. ej. `splitdays <reg> d,d,...`) + ccup 259/260/263 con días de calendario + Copa Venezuela (255) como copa de año natural + Supercopa (256) a finales de enero.
2. DLL (solo la copia de la fase 4): split_dates usa los días explícitos si los hay; revisar las ventanas de días de lo propio de la FUTVE (honours_fix/winners_fix "enero-junio", supercup_title_fix 182-330, títulos, rellenos).
3. Días propuestos (2026, 1 ene = 0): Apertura 13 jornadas sáb 44 (14 feb) … 128 (9 may); cuadrangulares 135-153; final 157 (dom 7 jun). Clausura 13 jornadas sáb 212 (1 ago) … 296 (24 oct); cuadrangulares 300-324; final 331 (28 nov). Gran Final ida 339 (6 dic), vuelta 346 (13 dic).
- 31.10. Fechas confirmadas por Felix (las propuestas). Hecho:
  - `tools/futve_calendar.py` → out/futve/world-calendar (desde world-finals, que no se toca): `season 29 1`, `splitdays 191 44..128` y `splitdays 192 212..296` (13 sábados cada uno), ccup 259 fill=129 gdays=135,139,142,146,149,153 days=157; ccup 260 fill=297 gdays=300,303,310,314,317,324 days=331; ccup 263 days=339,346; `dates 255 like=23 days=69,111,167,230,265,286,321` (miércoles); `dates 256 like=97 days=30`.
  - fl26swiss.lua (repo): lee `splitdays` → `fl26_swiss_splitdays`; la Supercopa de calendario toma `scupcup=` (antes solo cup1).
  - fl26swiss.dll (out/futve/bin, solo fase 4; sha 396581dd…): `fl26_swiss_splitdays` + split_dates con días propios; calendar_scup_fill_days con el campeón de las finales (futve_champion_kept) y el subcampeón de la Copa si coincide; supercup_title_fix también para supercopas de calendario (días 20-120); `futve_cal()`: ccup_season_win cuenta desde el 1 de enero para las finales de la FUTVE (la del Apertura de junio vale en diciembre), honours_fix desde el día 120, apclau_keep desde el 290.
  - futve_test `--phase 4` (lista de comprobación 4).
- Riesgos a mirar en la prueba: que fl26join acepte `season 29 1` para la región 29 (la nuestra, añadida por el mod); el bloque de temporada del Palmarés de un club de región de calendario (honours_fix); el cupo a Libertadores desde la tabla acumulada al cerrar el año; la primera temporada de la carrera (agosto→febrero sin Liga FUTVE).
- 31.10. (Felix: "Tabla acumulada FUTVE" en Selección de equipos, no le gusta) Fase 4: futve_calendar.py devuelve al reglamento 11 el nombre "Liga FUTVE" (todas las ranuras menos la 9) solo en world-calendar. El DLL de la fase 4 (futve_cal()) quita del Palmarés el título que el juego da al líder de la tabla acumulada: fila de temporada del 11 fuera (honours_fix), registro(s) del 11 fuera del armario de trofeos del usuario (compactando), y el historial de ganadores del 11 con el campeón de las finales (winners_fix). El título real sigue siendo el de la Final del FUTVE (175 "Liga FUTVE"). La fase 3 sigue con "Tabla acumulada FUTVE". (Una carpeta suelta creada por error, world-calendar/common/etc/pesdb/common, movida a out/futve/_to_delete.)
- 31.10. Primera prueba de la fase 4 (carrera nueva): la carrera empieza el 1 de enero de 2025 (club de región de calendario) y el Apertura (191) queda en los días 44..128 (splitdays) — bien. Pero el DLL metió en la Libertadores 2025 al 1.º de la lista de la Liga FUTVE (Táchira, sin tabla todavía) y al 2.º en la previa. Felix: la primera temporada, solo competiciones locales. Arreglado (fase 4): sin tabla final guardada de la Liga FUTVE, sus plazas de Libertadores/previa quedan para los clubes del pool (cont_build) y sus entradas en copas nuestras (Sudamericana 257, 11:3…) quedan vacías. La Jornada 1 de la Libertadores sin rival es el sorteo de grupos aún no hecho (tras la previa, días 34/41).
- 31.10. (Felix: ningún choque de fechas, selecciones incluidas) Días de la fase 4 rehechos contra los días de la Libertadores del juego (gc_seed: 34 41 | 62 76 83 104 118 139 | 163 223 258 265 296 303 324 331, varios en sábado) y el Mundial de Clubes (348-352), siempre ≥ 2 días: Apertura 13 sáb 44..128, grupos 132,135,142,146,149,153, final 157; Clausura 13 sáb **205..289** (25 jul..17 oct), grupos 293,300,307,310,314,317, final **321** (mié 18 nov); Final del FUTVE **338, 345**; Copa Venezuela mié **69,97,125,167,230,251,279**; Supercopa 30. Comprobado sin choques ni días propios a menos de 2. Las ventanas FIFA del juego (regs 36-40) solo se conocen en marcha: el DLL de la fase 4 (`futve_clash_report`, una vez por año) lista sus días exactos y cada choque de un día venezolano con ellas, la Libertadores, el Mundial de Clubes y las copas nuestras (Sudamericana). Instalado en el juego (DLL, Lua, mundo).
- Pendiente CONMEBOL moderna (Mod Studio 0.2.5 "conmebol": "modern", PR #146): hace falta la receta de Mod Studio de Felix (no está en las carpetas conectadas; en SiderAddons\ModStudio solo hay copias de sider.ini). Supuesto: la preparo yo y Felix hace Build; luego se rehacen world-finals/world-calendar encima.
- 31.10. Prueba larga fase 4 (fast forward a diciembre, sesión 002): calendario correcto; primera temporada sin Libertadores ("its places stay with the pool"); Táchira ganó Apertura (157) y Clausura (321) → Liga FUTVE automática el día 321: armario 261/262/263, honours "Liga FUTVE given"; ningún título del 11 apareció. Informe de choques: ventanas FIFA del juego **88 91 94 | 153 156 159 | 182-203 | 244 247 | 279 282 | 314 317** → 14 choques (y AFC, que no afecta a clubes venezolanos: quitada del informe). Días rehechos: Apertura 44,51,58,65,72,79,86,100,107,111,114,121,128; grupos 132,135,142,146,149,151; final **167**; Clausura 205,212,219,226,233,236,240,254,261,268,271,275,289; grupos 293,300,307,310,320,327; final **335**; Final del FUTVE **342, 345**; Copa 69,97,125,174,230,251,286. Comprobado: 0 choques, nada propio a < 2 días. Pendiente: la tabla acumulada (11) no se guardó como tabla final al cerrar el Clausura (sin línea de apclau_keep); el DLL ahora dice por qué (partidos jugados) — necesaria para la Libertadores de la 2.ª temporada.
- 31.10. Segunda temporada sin Liga FUTVE (Felix). Causa (fl26join.log): en Año Nuevo fl26join cierra la liga 11 de calendario ("closed with their region: [11]") pero no sus fases; el 191 conservó la marca de temporada y su tabla del año anterior y register_all lo dio por "ya en temporada": solo entró el 11, sin Apertura. Arreglo (DLL fase 4): el gancho de teardown de fl26swiss añade a la lista de Año Nuevo las fases (191, 192) de un split nuestro de enero-diciembre. Además la Copa Venezuela (255) **no entró en ninguna temporada** ni en el primer año: fl26joindll solo mete en el constructor de Año Nuevo la copa nacional del `cup=` de la línea de liga (la nuestra no lo tenía) → futve_calendar.py añade `cup=255` a la línea `league 11`. La Libertadores sí funcionó (Táchira en grupos en el 2.º año).
- 31.10. Con `cup=255` la Copa entra en la lista del constructor de Año Nuevo ("appended 2 calendar cup(s) [255 256]") pero sigue sin jugarse: el constructor solo enseña a la puerta los ids con la marca de temporada (+0x304 bit 8), y el teardown de Año Nuevo (fl26swiss la cierra con la copa cuyo calendario usa) la deja limpia — ni puerta ni enter_season(255). (La función de copas nacionales de enero-diciembre de 0.2.2, #139, nunca se probó en una carrera.) Arreglo fase 4: `futve_copa_fill` (días 1-66, una vez al año, sin partidos propios): campo = clubes de la liga (191 o 11), marca puesta, start_stage y register_all(255), como la Supercopa de calendario. Sin choques de fechas en esta carrera (0 clashes).
- 31.10. Segundo año aún sin Liga FUTVE: añadir 191/192 a la lista de Año Nuevo no sirve, fl26join los saca ("ours kept out: [191 192]"). Lo que los deja fuera es el test de register_all del día 41 (en temporada + con tabla = "ya en temporada"; el 191 no está en la lista de ligas de calendario de fl26join). Arreglo fase 4: `futve_phase_reopen` (días 1-40, una vez al año) borra la marca de temporada (+0x304 bit 8) de la fase regular de un split nuestro de calendario; register_all la añade con su liga el día 41 y la puerta (que reinicia el año de temporada de lo nuestro) la inscribe. La Copa de este año tampoco: el DLL con futve_copa_fill no se había podido instalar (juego abierto).
- 31.10. (Felix: ver todo el año en el calendario; ¿por qué el Clausura y la Copa aparecen a mitad de año?) El cierre de julio de fl26join (TD_EXTRA de fl26joindll: los grupos de un split van al cierre de julio; el 191 como liga "nuestra" no de calendario) borraba el Apertura en julio. Fase 4 instala su propio fl26joindll.lua (out/futve/phase4, desde el instalado; futve_test PHASE_MODULES): los grupos de una liga de enero-diciembre ya no van al cierre de julio, y sus fases (191, 192) entran en la lista de calendario de fl26join (fl26_join_calendar) → se cierran en Año Nuevo con la liga y vuelven a entrar con ella el día 41. Pendiente/explicado: el Clausura (192) lo llena el juego cuando acaba el Apertura (fase de grupo del split); la Copa y los cuadrangulares se sortean ronda a ronda.
- 31.10. (Felix: las 26 jornadas del Apertura y del Clausura son seguras, que estén desde enero) `futve_clausura_early` (DLL fase 4, días 41-120, una vez al año): en cuanto el Apertura (191) tiene sus partidos y el Clausura (192) ninguno, el DLL le pone los clubes del Apertura, la marca de temporada, start_stage y register_all(192) → split_dates le da sus splitdays (205..289). En mayo, al acabar el Apertura, prog_handler_inner ya no llama a la función de reparto del juego (0x141343d70) si el grupo tiene partidos. Solo para splits de calendario con carry=0 y un grupo (Apertura/Clausura).
- 31.10. (Felix: a fin de año faltan en el calendario los cuadrangulares y la final del Apertura) Los borraba el propio fl26swiss: su gancho del cierre de julio añade todas las copas del mundo (259/260/263 incluidas). Fase 4: con futve_cal() las copas de la Liga FUTVE (adv= o src=) se quedan fuera del cierre de julio y se cierran en Año Nuevo con las fases (lista `fut` del teardown de Año Nuevo). Además, en esta carrera la Copa (14 clubes) se sorteó con 2 exentos a cuartos: primera ronda 69, cuartos 174, semis 230, final 251 (el juego reparte sus rondas entre las 7 fechas por su numeración; 97, 125 y 286 quedan sin uso).
- 31.10. (Felix: 2.º año ganado todo otra vez, el Palmarés sigue en "Liga FUTVE 1") Armario del 2.º año: [0]261 [1]255 [2]262 [3]263 (año 1) [4]256 (Supercopa, día 31, añadida por el DLL) [5]10 Libertadores [6]1 Mundial de Clubes (el juego). Faltan los del 2.º año: 261, 262, 255 (el juego no los añadió esta vez) y 263 (el DLL no lo añadió: su comprobación "ya está en el armario" mira todos los registros, no los de esta temporada). Para saber cómo distingue el juego la temporada de un registro, el DLL vuelca una vez por sesión los primeros 0x80 bytes de cada registro (cabinet_watch). Rareza a mirar: "cup 263 -- its feeding champions changed ... the final of 262 is over on day 121" en el 2.º año.
- 31.10. Felix ve en el Palmarés 2 Final del Apertura, 2 Copa, 2 Final del Clausura (el juego los cuenta bien aunque el armario solo tenga un registro de cada uno: el recuento sale de otro sitio) y **1 Liga FUTVE**: el único que falla es el que pone el DLL. Arreglo: marcas de título (regulación, año natural) guardadas en fl26swiss-state.bin (tipo 4, STATE_TITLE); en la fase 4 el "ya está en el armario" de la Liga FUTVE automática mira la marca de este año, no cualquier registro del 263. Se aplica mientras el día del título (o después) siga en el mismo año natural (honours_fix desde el día 120).
- 31.10. Informe de choques ampliado (fase 4): además de ventanas/torneos FIFA, Libertadores y Mundial de Clubes, ahora lee del propio calendario del juego (listas de partidos por día + registro de cada partido) los días con partidos de la Copa Sudamericana (257/258 y sus filas) y de amistosos de selecciones (reg 56). Se repite cada semana (los grupos de la Sudamericana se hacen en agosto) y solo anota los choques nuevos.
- 31.10. Palmarés con dos filas "Liga FUTVE 1" (captura de Felix). Registros del armario: [3]263 (copia del de la Final del Clausura) y [5]263 (copia del de la Supercopa): el Palmarés agrupa por más que la regulación. Arreglo: el modelo de un registro añadido por el DLL es un registro del mismo título si lo hay (Liga FUTVE automática y Supercopa); y cabinet_watch (fase 4) iguala cada vez los bytes de un 263/256 posterior a los del primero (registra el rango que difería). Además, el 2.º Liga FUTVE se dio en junio (día 167), antes de tiempo: ccup_src_winner releía el ganador del Clausura del año anterior con la ordinal de julio (el día 335 "pasado" el día 121). Con futve_cal() usa el día del año.

### Cierre de la fase 4 (31.10.)
- Palmarés resuelto: cada registro del armario tiene clubes desde +4 y fechas desde +0x324 ({u16 año, u8 mes, u8 día}); el Palmarés cuenta las fechas. `rec_append` añade club y fecha; los registros duplicados se fusionan. "Liga FUTVE 2" confirmado en el juego.
- Sudamericana (ccup 257/258, agosto–mayo): 2 choques (327/328 y 335/335) con el cierre del Clausura. Se deja para la fase 5.
- Copia congelada en out/futve/phase4/ (DLL sha1 7aa13304…).
- Fase 5 = competiciones CONMEBOL modernas; ver el doc del proyecto claude/fase5-conmebol-moderna.md (no perder nada del mundo actual, que ya difiere de la receta).
- Supercopa (256): las victorias se añaden al mismo registro, controladas por las marcas de título. Las temporadas pasadas se recuperan con save/fl26swiss-palmares.txt ("256 2026 2027 2028"). "Supercopa 3" confirmado en el juego.
- FASE 4 CERRADA (31.10.). DLL final sha1 65c5b8d7… en out/futve/phase4/.

## FASE 5 — CONMEBOL moderna (empezada 01.11.)
- tools/futve_conmebol.py: a partir del mundo de la fase 4 (out/futve/world-calendar) y de la receta recuperada del plan instalado, añade solo lo CONMEBOL con las funciones del builder: FL_SUDA1 (cid 136, reg 264, día 40), Recopa (143/265, día 55), FL_SUDAPO (144/266, días 144/161), FL_LIBQ (145; F1 267 días 6/13, F2 268 días 18/25), Sudamericana 133/257/258 recreada (cal=1). Verifica que contra la fase 4 solo cambie lo CONMEBOL. Salida: out/futve/world-phase5 (con emblemas y emblems.json).
- Reparto: Venezuela real (2 G, 1 F2, 1 F1, 4 S1); Bolivia/Uruguay 2 G; Ecuador 2 G+F2+F1; Paraguay 2 G+F2; Perú 2 G+F1; el resto a Brasil, Argentina, Chile y Colombia.
- DLL de la fase 5 (out/futve/phase5/fl26swiss.dll):
  - futve_cont_club: las 8 posiciones de la reg 11 = campeón, mejor de la tabla acumulada, subcampeón, siguiente, perdedores de las finales del Apertura y del Clausura, y 2 siguientes;
  - los perdedores de las finales se guardan (cupwin 0xf000|ko);
  - en la 1.ª temporada las plazas venezolanas de las fases previas van a 168:16..20, 67:16, 30:19..;
  - el reporte de choques cuenta las fases previas.
- futve_test.py: --phase 5; la fase 4 queda apuntando a su copia congelada (phase4/).
- Ajustes durante la prueba (01.11.):
  - el orden de las filas de la fase 4 se conserva (keep_order);
  - futve_final_title_fix escribe el título de las finales del Apertura y del Clausura cuando el juego no lo hace (le pasó a la del Apertura con la Sudamericana en octavos), comprobando el ganador en el propio juego;
  - para decidir si un título ya está, se mira el armario de trofeos (cab_has_year), no las marcas del archivo de estado, que sobreviven entre carreras;
  - un registro nuevo de Supercopa o de Liga FUTVE se crea limpio (sin las fechas de la plantilla);
  - el archivo del palmarés se usa una vez y se renombra a .applied;
  - las ventanas de los perdedores y campeones de las finales pasan a 300 días;
  - los avisos y los choques de la Recopa solo cuentan su último día;
  - logos de la Sudamericana, la Recopa y la Conference tomados de G:\Downloads (futve_conmebol --logos).
- Prueba (01.11.): carrera nueva, 2025 a 2028. 0 choques de fechas cada año (también con los torneos de selecciones de 2026 y 2028). Las plazas venezolanas siguen la regla real cada año. Libertadores, Sudamericana y Recopa completas. Palmarés correcto.
- FASE 5 CERRADA (01.11.). Copia congelada en out/futve/phase5/ (DLL sha1 b9f7fea4…, fl26swiss.c, fl26swiss.lua, fl26world.txt, futve_conmebol.py, emblems/). El mundo está en out/futve/world-phase5. Para volver a ella: futve_test.py --phase 5.

## FASE 6 — entregable de FL26 Mod Studio (definida 01.11.)
- Objetivo: refactorizar y adaptar todo el desarrollo FUTVE (fases 3–5) para que funcione como característica normal de FL26 Mod Studio: claves de receta, un Build que genere el mundo completo, y un DLL/Lua sin ids fijos (255/256/259–263, 129/142/175, reg 11, MINE, SUB).
- Regla: el resultado en el juego tiene que ser el mismo que el de la fase 5 congelada (referencia de comparación).
- Plan y tabla de piezas a convertir: doc del proyecto claude/fase6-entregable-mod-studio.md.
- Requisito 1 (Felix): lo que FL26 Mod Studio genere con cualquiera de sus configuraciones tiene que ser compatible con la funcionalidad final. Las opciones nuevas son opcionales (sin ellas, todo igual que antes), se combinan con las existentes y no hay ids fijos ni choques. Se prueba con una matriz de recetas.
- Requisito 2 (Felix): nada de pruebas en el juego. Verificación con el Build en una carpeta falsa (tablas, mundo, emblemas), el Lua contra los archivos del mundo, los arneses del DLL (tools/native/test_*.c, hay que hacerlos correr fuera de Windows) y los logs de las fases 3–5 como casos de prueba.
