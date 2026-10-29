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