# Crear tus propias ligas y paquetes: cada clic, en orden

> [English](../en/make-your-own-leagues.md) · [hrvatski](../hr/make-your-own-leagues.md) · **español** · [português](../pt/make-your-own-leagues.md) · [français](../fr/make-your-own-leagues.md)

> La otra guía paso a paso: [Instalar un paquete listo](install-a-pack.md)
> · cada página y opción explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · preguntas: [faq.md](../../docs/faq.md) (en inglés) · ayuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta guía usa los nombres de los botones en español. La ventana arranca en inglés: pásala a
español con **Idioma (Language)** → Español y vuelve a abrir Mod Studio
([Paso 2 de la otra guía](install-a-pack.md#paso-2-descarga-mod-studio)).

Esta página te lleva de cero a tus propias ligas en el juego: ligas reales con clubes y jugadores
reales de la **NewLife Database**, ajustadas como quieras, construidas, jugadas y compartidas con
otras personas. Dice qué pulsar, el nombre exacto de cada botón y campo tal como lo muestra Mod
Studio, y qué deberías ver después de cada paso. Haz los pasos en orden. Si ves algo distinto de
lo que dice un paso, para ahí y mira en
[Si algo sale mal](#si-algo-sale-mal).

Tres palabras que vas a ver todo el rato:

- **Tu mundo**: tu lista de ligas y todo lo que ajustas para ellas. Lo cambias en las pestañas de
  **2. Mi mundo**, y se guarda solo un momento después de cada cambio. Es solo un plan: nada
  llega al juego hasta que **construyes** (Build).
- **Carpeta del mundo**: lo que Build hace con tu mundo, una carpeta cuyo nombre empieza por
  `_FL26` (`_FL26MyWorld` si no lo cambias). El juego la lee mientras está en el juego (el
  recuadro **MUNDO ACTIVO** arriba en la ventana muestra su nombre).
- **Build** (construir): el botón que convierte tu mundo en esa carpeta y la mete en el juego.

**Contenido**

- [Antes de empezar: la preparación de una sola vez](#antes-de-empezar-la-preparación-de-una-sola-vez)
- [Paso 1. Consigue la NewLife Database](#paso-1-consigue-la-newlife-database)
- [Paso 2. Ábrela en la página NewLife Database](#paso-2-ábrela-en-la-página-newlife-database)
- [Paso 3. Elige tus ligas](#paso-3-elige-tus-ligas)
- [Paso 4. Elige los clubes de una liga](#paso-4-elige-los-clubes-de-una-liga)
- [Paso 5. Agregar a tu mundo](#paso-5-agregar-a-tu-mundo)
- [Paso 6. La pestaña Ligas: cada ajuste de una liga](#paso-6-la-pestaña-ligas-cada-ajuste-de-una-liga)
- [Paso 7. Ejemplo: un país con dos divisiones](#paso-7-ejemplo-un-país-con-dos-divisiones)
- [Paso 8. La pestaña Clubes: nombres, escudos, equipaciones, clubes del juego](#paso-8-la-pestaña-clubes-nombres-escudos-equipaciones-clubes-del-juego)
- [Paso 9. La pestaña Jugadores](#paso-9-la-pestaña-jugadores)
- [Paso 10. Límites que detienen el Build](#paso-10-límites-que-detienen-el-build)
- [Paso 11. Tu mundo se guarda solo](#paso-11-tu-mundo-se-guarda-solo)
- [Paso 12. Construir](#paso-12-construir)
- [Paso 13. Juega: una Liga Máster NUEVA y luego la comprobación](#paso-13-juega-una-liga-máster-nueva-y-luego-la-comprobación)
- [Paso 14. Cambiar algo más tarde](#paso-14-cambiar-algo-más-tarde)
- [Paso 15. Compartir lo que has hecho](#paso-15-compartir-lo-que-has-hecho)
- [Si algo sale mal](#si-algo-sale-mal)

---

## Antes de empezar: la preparación de una sola vez

Haz primero, una vez, los pasos 1 a 3 de la otra guía:
[cierra el juego](install-a-pack.md#paso-1-cierra-el-juego),
[descarga Mod Studio](install-a-pack.md#paso-2-descarga-mod-studio) y
[dile dónde está tu juego](install-a-pack.md#paso-3-dile-dónde-está-tu-juego).
Luego vuelve aquí. Mod Studio desempaqueta solo las tablas del juego, y **Construir e instalar**
(Paso 12) pone sus módulos.

Mantén el juego cerrado todo el tiempo que trabajes en Mod Studio.

Si ahora hay en el juego un mundo listo de un zip (un Modpack), no pasa nada: puedes construir tu
propio mundo junto a él. Build pregunta antes, y saca el mundo listo del juego mientras el tuyo
está dentro. Su tarjeta en **2. Mi mundo** se queda, y **Activar** lo vuelve a poner.

---

## Paso 1. Consigue la NewLife Database

La NewLife Database es una descarga aparte con clubes y jugadores reales: nombres, fechas de
nacimiento, posiciones, valoraciones en la escala del juego y los colores de los clubes. No está
en GitHub.

1. Abre nuestro [Discord](https://discord.gg/StQqtk3G3M) y ve al canal **#newlife**.
2. Descarga las partes que quieras. Hay una parte por continente (un continente grande viene en
   más de una parte), más *Free agents*. Cada parte es un archivo `.zip` llamado `NewLife-...zip`.
3. Crea una carpeta para ellas, por ejemplo `Documents\NewLife`, y pon **todas** las partes en
   esa misma carpeta.
4. **No las descomprimas.** Mod Studio lee los zip tal cual. (El visor de zip de Windows no
   puede abrirlos de todos modos; es normal.)

Cuando salga una versión más nueva de NewLife, pon sus partes en una carpeta **nueva**. Nunca
mezcles dos versiones en una carpeta.

## Paso 2. Ábrela en la página NewLife Database

1. Pulsa **2. Mi mundo** y luego **NewLife Database** (el botón a la derecha, junto a las
   pestañas).
2. Pulsa **Abrir NewLife Database...** arriba.
3. Elige la carpeta del Paso 1 (la carpeta, no un zip de dentro) y confirma.
4. Espera unos segundos mientras la lee.

(O: **2. Mi mundo → + Añadir...**, **Elegir una carpeta...**, elige la carpeta y luego
**Añadir**.)

**Deberías ver:** encima de la lista, la versión de NewLife y la carpeta, y debajo de ellas
`Partes:` con las partes que encontró. Más abajo, una lista larga de ligas.

Mod Studio recuerda la carpeta: la próxima vez la página la abre sola.

**Buscar.** El cuadro encima de la lista, *Buscar ligas o países*, deja solo las ligas cuyo
nombre o país contiene lo que escribes. Escribe `brazil` o `liga`, por ejemplo. Vacía el cuadro
para volver a verlas todas.

**Las columnas.** Pulsa la cabecera de una columna para ordenar por ella, pulsa otra vez para
invertir el orden.

| Columna | Qué te dice |
|---|---|
| **Liga** | El nombre de la liga. Un `*` detrás significa que cambiaste sus clubes (Paso 4). |
| **País** | Dónde va en el juego. |
| **Clubes** | Cuántos clubes tendrá, tal como lo tienes ajustado ahora. |
| **En el juego** | Cuántos de sus clubes ya tiene el juego (conservan sus propios nombres, escudos, equipaciones y jugadores). |
| **Jugadores** | Cuántos jugadores tienen sus clubes en NewLife. |
| **Nivel** | Lo fuerte que es la liga. Más alto es más fuerte. |
| (última columna) | Por qué no se puede añadir una liga gris. Vacía para una liga que puedes añadir. |

**Por qué algunas ligas están en gris.** Una liga gris no se puede añadir, y la última columna
dice por qué:

- `una liga tiene de 10 a 24 clubes`: una liga del juego tiene de 10 a 24 clubes, los nuevos y
  los del juego juntos. Esta tiene menos o más. Aún puedes arreglarlo en el Paso 4 (añadir o
  dejar fuera clubes) hasta que encaje.
- `liga propia del juego: Llevar las ligas del juego a esta temporada`: el juego ya tiene esta
  liga (la Premier League, la Championship ...). No se añade una segunda vez.
  **Más ▾ → Llevar las ligas del juego a esta temporada...** de arriba da en su lugar a las
  ligas del propio juego los clubes y las plantillas de esta temporada de NewLife; ver
  [8.4 en la guía completa](mod-studio-guide.md#84-newlife-database-clubes-y-jugadores-reales).

Si la página dice que Mod Studio no tiene tablas del juego y ofrece abrir Ajustes: pulsa **Sí**
y luego, allí, **Desempaquetar las tablas del juego**.

## Paso 3. Elige tus ligas

1. Pulsa una liga de la lista para seleccionarla. Su fila se resalta.
2. Para más de una: mantén **Ctrl** y pulsa cada una. (O pulsa la primera, mantén **Mayús**
   y pulsa la última para tomar todo lo que hay entre ellas.)

**Deberías ver:** abajo de la página una línea como
`Clubes nuevos en tu mundo: 0 de los 1544 que admite el juego.  Seleccionados: 18 más.`

- El **primer** número es cuántos clubes nuevos tiene ya tu mundo.
- El **segundo** es cuántos clubes nuevos caben en el juego en total (unos 1500). Mod Studio lo
  calcula a partir de las tablas de tu juego, así que puede ser un poco distinto en otra versión
  del juego.
- **Seleccionados** es cuántos clubes nuevos añadirían las ligas que elegiste.

Si tu mundo y la selección juntos pasan de lo que admite el juego, **Agregar a tu mundo** se
queda en gris: elige menos ligas.

## Paso 4. Elige los clubes de una liga

Este paso es opcional. Sáltatelo para tomar una liga exactamente como la tiene NewLife.

Selecciona **una** liga (solo una). La lista de la derecha muestra sus clubes: **Club** y
**Jugadores** (cuántos jugadores le da NewLife). Un club que el juego ya tiene sale en gris, con
`en el juego` en lugar de un número.

- **Dejar un club fuera:** pulsa su casilla para desmarcarla.
- **Traer un club de otra liga** (la primera división de esta temporada es la de la temporada
  pasada con dos ascendidos, por ejemplo): pulsa **Añadir un club de otra liga...** debajo de
  la lista.
  1. Se abre una ventana con todos los clubes de las partes de NewLife que abriste, cada uno con
     su liga entre paréntesis.
  2. Escribe en el cuadro de búsqueda para encontrar un club o una liga.
  3. Marca uno o más clubes. La línea bajo la lista dice cuántos elegiste.
  4. Pulsa **Aceptar**.

  **Deberías ver:** el club al final de la lista, con `de: <su liga>` al lado.

**Deberías ver:** la fila de la liga en la lista tiene ahora un `*`, y su número de **Clubes**
cambió. Una liga gris que ahora tiene de 10 a 24 clubes pasa a normal.

Un club solo puede jugar en una liga. Si lo añades a dos, Mod Studio te para en el Paso 5.

## Paso 5. Agregar a tu mundo

Con tu liga o tus ligas seleccionadas, pulsa **Agregar a tu mundo** arriba.

**Deberías ver:** una línea verde bajo el título de la página. Qué significa cada línea:

| Línea verde | Qué significa |
|---|---|
| `Añadido: <ligas>. Cámbialos en Ligas, Clubes y Jugadores, y luego construye.` | Las ligas están en tu mundo, cada una como primera división de su país, todos contra todos dos veces. Todavía no hay nada en el juego. |
| `<clubes> también juegan una competición del juego: en Clubes elige cada uno y usa Club del juego para escoger el club que ocupa su lugar allí.` | Estos clubes de tu liga nueva son clubes que el juego ya tiene, y también juegan en algún sitio del juego (una liga, una copa, la Europa League ...). Un club juega en una sola liga, así que su sitio antiguo necesita otro club. Ese club lo eliges en el [Paso 8](#clubes-que-el-juego-ya-tiene). Hasta que lo hagas, Build se para con un error que nombra el club. |
| `<n> jugadores se quedan en su club del juego (su club se quedaría con pocos jugadores).` | Los jugadores que el juego ya tiene normalmente pasan al club de NewLife. Estos se quedan, para que su club antiguo conserve al menos 18 jugadores. No hay que hacer nada. |
| `<n> jugadores no se añaden: otra liga ya los tiene.` | Una liga que añadiste antes ya se quedó con estos jugadores. No hay que hacer nada. |

Si una ventana de error dice `<club> jugaría en dos ligas (<liga> y <liga>).`, desmarca ese club
en una de las dos ligas (Paso 4) y vuelve a intentarlo.

¿Quieres ligas de otros continentes? Selecciónalas también y pulsa **Agregar a tu mundo** otra
vez. Cada clic añade; nunca quita lo que ya hay.

---

## Paso 6. La pestaña Ligas: cada ajuste de una liga

1. **2. Mi mundo**, pestaña **Ligas**.
2. Encima de la lista, pulsa **Nuestras**: la lista muestra solo las ligas de tu mundo.
   (**Todas** muestra todas las ligas, también las del juego; **Cambiado**, las ligas del juego
   que cambiaste.) Las ligas están agrupadas por continente.
3. Pulsa tu liga.

**Deberías ver:** a la derecha, `NUESTRO`, el nombre y el logo de la liga, y las filas **País**,
**Clubes**, **Formato**, **División**, **Asc. / desc.**, **Europa** e **ID de la liga** (`sin
construir` hasta el primer Build), y luego los escudos de sus clubes. Debajo, los botones
**Editar liga...**, **Añadir división inferior**, **Clubes y nombres**, **Jugadores** y
**Quitar**.

La lista va por países, y las divisiones de cada país de arriba abajo (Bundesliga, 2. Bundesliga, 3. Liga).
Puedes arrastrar una liga hacia arriba o hacia abajo en la lista para ordenar las ligas de un
continente.

4. Pulsa **Editar liga...**.

**Deberías ver:** una ventana llamada **Liga** con los campos de abajo, de arriba abajo. Un campo
gris no se puede usar con lo que ajustaste encima (por ejemplo una copa en una segunda
división). El **?** junto a **Aceptar** explica la ventana en pocas palabras. Nada es
obligatorio: los valores por defecto funcionan, y **Cancelar** no cambia nada.

| Campo | Qué es y qué hacer |
|---|---|
| **Nombre** | El nombre de la liga en el juego. Dos ligas no pueden tener el mismo nombre. Mantenlo por debajo de unos 38 caracteres: un nombre más largo sale como una fila vacía en la lista de ligas de Kick Off. |
| **País** | Escribe unas letras y elige de la lista (`korea` encuentra las dos Coreas). Da la bandera y el lugar donde aparece la liga en el juego. |
| **Clubes** | De 10 a 24. Para una liga de NewLife, déjalo como está: un número menor quita los últimos clubes, uno mayor añade clubes inventados al final. |
| **Clubes sin liga** | Déjalo en `(no -- una liga)`. Las otras opciones (*Other European teams* ...) son para un club, o unos pocos, sin una liga alrededor; van a los grupos "Other ..." del juego, y la mayoría de los campos de abajo se ponen en gris. [Más](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos). |
| **Formato** | Elige uno: **todos contra todos, vueltas:** y el número (1 a 4; 2 es ida y vuelta); **se divide en dos (estilo escocés)**, con `primero` *n* `x, luego grupos` *6/6* *n* `x` (los grupos deben sumar los clubes); o **Apertura y Clausura, luego liguilla de:** *8 clubes*, *4 clubes* o *sin liguilla* (dos torneos cortos por temporada, 18 clubes como máximo). La división en dos y el Apertura y Clausura son **experimentales**: funcionan, pero aún tienen más fallos que todos contra todos, el formato totalmente probado. La ventana lo dice debajo de los formatos. Para un primer mundo, elige todos contra todos. |
| **División** | `(primera división)` = la mejor liga de su país. Para una segunda división, elige la liga de un nivel más arriba: tus ligas nuevas están arriba de la lista, luego las ligas del juego con un número entre paréntesis. `= división 2` al lado muestra el nivel. Una liga que ya tiene una liga debajo sale en gris (`-- debajo: ...`): una liga puede tener una sola liga debajo. Ver el [Paso 7](#paso-7-ejemplo-un-país-con-dos-divisiones). |
| **Solo exhibición -- no está en la Liga Máster** | Déjalo desactivado. Activado: la liga es solo para Kick Off y partidos amistosos (leyendas, una temporada histórica); nunca juega una temporada de Master League, y la división, las copas y Europa se ponen en gris. No empieces una carrera con uno de sus clubes. |
| **Temporada** | Solo primera división: **agosto a mayo** (como Europa) o **febrero a diciembre** (como Brasil o Japón). Una división de abajo sigue a la liga de arriba. Febrero a diciembre todavía no puede tener división en dos, Apertura/Clausura ni copa de la liga; una copa nacional sí. |
| **Asc. / desc.** | De 1 a 6: cuántos clubes cambian de sitio con la liga de arriba al final de la temporada. Solo tiene sentido para una división debajo de otra. |
| **Logo** | **Elegir imagen...**: un PNG o JPG para la liga (un PNG con fondo transparente queda mejor). **Borrar** lo quita. Vacío: `(se hace solo)`, se dibuja un logo en el Build. |
| **Bandera del país** | Tu propia imagen de la bandera del país. Vacío: `(la del juego)`. Déjalo vacío salvo que el juego no tenga una buena bandera. |
| **Copa** | Solo primera división. Marca **Copa nacional** para dar al país una copa por eliminatorias (esta liga y la división de debajo). El cuadro de al lado es el nombre de la copa; vacío = el nombre de la liga + Cup. |
| **Supercopa (campeón contra ganador de copa)** | Un partido antes de la temporada. Necesita **Copa nacional** marcada. |
| **Copa de la liga** | Solo primera división. Una segunda copa por eliminatorias, como la Carabao Cup de Inglaterra: esta liga y la de debajo, hasta 44 clubes. El cuadro es su nombre; vacío = el nombre de la liga + League Cup. |
| **Logos de las copas** | Una imagen para cada una: **Copa**, **Supercopa**, **Copa de la liga** y **Playoffs**. Vacío: un emblema con las iniciales de la copa. |
| **Formación** | Cómo forman los clubes de la liga. Elige una de la lista, o déjalo vacío y Build elige para cada club la que mejor encaja con su plantilla. Un club puede tener la suya (Paso 8). |
| **Europa** | Solo primera división: qué puesto de la tabla va a qué competición continental. El botón que empieza por **Primera división:** rellena las plazas habituales del continente del país (para Europa: `Primera división: 1.º fase previa UCL, 2.º UEL, 3.º UECL`). **Añadir plaza** añade una fila: elige el **Puesto en la liga** (por debajo de 1 dice **Campeón de copa**) y la **Competición**. La **✕** de una fila la quita, **Borrar** las quita todas. Déjalo vacío para una segunda división. |

5. Pulsa **Aceptar**.

**Deberías ver:** la ventana se cierra y las filas de la derecha muestran lo que ajustaste.

Una liga de NewLife entra sin plazas europeas. Si quieres que sus clubes jueguen la Champions
League y las demás, ajusta **Europa** ahora; si no, **1. Comprobar el plan** te lo recuerda con
`no European places: the new leagues send nobody to Europe`.

El significado de cada formato, copa y plaza europea a fondo (fechas, rondas previas, tamaños de
las copas):
[sección 8 de la guía completa](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos)
y [8.2](mod-studio-guide.md#82-construir-activar-jugar).

**Más ▾** (arriba en la pestaña Ligas) tiene las herramientas para todo el mundo: **Torneos de
pretemporada**, **Copas de nuestros países** (las copas de todas tus ligas en una tabla),
**Copas de los países del juego**, **Plazas europeas de las ligas del juego**, **Clubes europeos
de la primera temporada**, **Ranking UEFA**, **Plazas sudamericanas** (con la casilla **Competiciones modernas de la CONMEBOL**, 0.2.5), **Países de la CONMEBOL sin liga**, **Nombres de las
competiciones** (nombres y logos nuevos para copas y competiciones continentales), **IDs de
competiciones**, **Orden de las ligas**, **Temporadas de las ligas del juego** y **Nombre del
mundo y archivo...** (el nombre de la carpeta del mundo; tiene que empezar por `_FL26`). No
necesitas ninguna para un primer mundo. Las ventanas de copas también están en **Copas ▾**, junto
a las pestañas.

**Una liga sin clubes de NewLife.** **Añadir liga**, arriba en la pestaña Ligas, abre la misma
ventana **Liga** para una liga hecha desde cero: dale un **Nombre**, un **País** y un número de
**Clubes**, y Build hace los clubes con plantillas completas y un entrenador. Les pones nombre en
la pestaña **Clubes** (Paso 8), donde **Club NewLife...** también puede meter clubes reales en
ella.

## Paso 7. Ejemplo: un país con dos divisiones

Digamos que tus partes de NewLife tienen la primera y la segunda división de un país, aquí
llamadas *Primera Liga* y *Segunda Liga*. Quieres ascensos y descensos entre ellas.

1. **NewLife Database**: selecciona *Primera Liga* y pulsa **Agregar a tu mundo**. (Primero la
   de arriba.)
2. Selecciona *Segunda Liga* y pulsa **Agregar a tu mundo**.

   **Deberías ver:** la línea verde `Añadido:` cada vez. Las dos son ahora primeras divisiones
   del mismo país, que todavía no es lo que quieres.

3. **Ligas** → **Nuestras** → pulsa *Segunda Liga* → **Editar liga...**.
4. **División**: abre la lista y elige *Primera Liga* (tus ligas están arriba).

   **Deberías ver:** `= división 2` al lado. **Copa**, **Copa de la liga**, **Temporada** y el
   botón **Primera división** se ponen en gris: esos son de la primera división.

5. **Asc. / desc.**: cuántos clubes suben y bajan entre las dos, por ejemplo `3`.
6. **Europa**: si tiene filas, pulsa **Borrar**. Una segunda división no manda a nadie a Europa.
7. Pulsa **Aceptar**.

   **Deberías ver:** a la derecha, **División** `2  (debajo de Primera Liga)` y **Asc. / desc.**
   `3 con Primera Liga encima`. Pulsa *Primera Liga*: su **Asc. / desc.** dice
   `3 con Segunda Liga debajo`.

8. Pulsa *Primera Liga* → **Editar liga...** y ajusta lo que es de la primera división:
   **Europa** (el botón **Primera división**) y, si quieres, **Copa nacional**, **Supercopa** y
   **Copa de la liga**. Pulsa **Aceptar**.

Una tercera división funciona igual: su **División** es *Segunda Liga*. El juego llega hasta la
7.ª división.

**Una liga debajo de una liga.** Dos ligas no pueden estar debajo de la misma liga (tres grupos
regionales bajo una segunda división, por ejemplo). La segunda sale en gris en la lista de
**División**.

**Debajo de una de las ligas del juego.** Tu liga nueva también puede ir debajo de una liga que
tiene el juego: elige la liga del juego en **División** (las que tienen un número entre
paréntesis). Entonces juega ascensos y descensos con ella.

**Sin NewLife.** En **Ligas**, pulsa tu liga de arriba y luego **Añadir división inferior**: se
abre una ventana **Liga** con el país, los clubes, el formato y la división ya rellenos. Dale un
**Nombre** y pulsa **Aceptar**.

---

## Paso 8. La pestaña Clubes: nombres, escudos, equipaciones, clubes del juego

1. **2. Mi mundo**, pestaña **Clubes** (o **Clubes y nombres** en la pestaña Ligas).
2. Arriba, **Liga**: elige una de tus ligas.

**Deberías ver:** sus clubes con las columnas **#**, **Nombre**, **Abreviatura** y **Jugadores
cambiados**; deja el ratón sobre un nombre para ver su **ID del club** (`en el Build` hasta el
primer Build) y el archivo de su escudo. Los clubes de NewLife ya tienen sus nombres,
abreviaturas y escudos. Un club sin nombre muestra `<liga> 01`, `<liga> 02` ... en gris. Encima
de la lista: **Editar club** y **Más ▾**.

### Nombre, escudo, equipaciones, entrenador

1. Haz doble clic en un club (o selecciónalo y pulsa **Editar club**).

**Deberías ver:** una ventana llamada **Club** con:

| Campo | Qué hacer |
|---|---|
| **Nombre** | El nombre del club. Las letras con marcas (Željezničar) están bien. |
| **Abreviatura** | Tres letras o cifras. Vacío = se hace a partir del nombre. Č, Ž, Đ ... pasan a C, Z, D, como en el juego. |
| **Escudo** | **Elegir imagen...**: un PNG o JPG. **Borrar** lo quita. Un club sin escudo recibe un escudo con número. |
| **Estadio local** | Solo cuando Stadium Server está instalado: **Elegir estadio...** de tu pack de estadios, o **Del juego**. |
| **Entrenador** | El nombre del entrenador. Vacío: un nombre inventado con jugadores del país del club. |
| **Foto del entrenador** | Un PNG o JPG; el juego lo muestra en el modo Edit y en la Master League. |
| **Formación** | `Como la liga (...)` mantiene la formación de la liga; o elige una para este club. |
| **Colores de la equipación local**, **Colores de la equipación visitante** | Pulsa los dos cuadros de color (camiseta, segundo color) para elegir colores; **Ninguno** = Build elige una equipación solo. Build da al club la equipación del juego más parecida a esos colores. |

2. Pulsa **Aceptar**.

**Deberías ver:** el nombre y el escudo nuevos en la lista.

**Equipaciones.** Un club nuevo toma prestada la equipación de un club del juego de sus colores.
Dos opciones de la pestaña **Construcción**, en **Opciones del mundo**, cambian eso:
**Equipaciones con los colores del club** (activada por defecto, necesita Kit Server instalado:
cada club nuevo recibe equipación local, visitante, tercera y de portero hechas en sus colores,
con su escudo) y **Equipaciones simples para el modo Edición** (cada club nuevo lleva una
equipación sencilla que puedes cambiar en el modo Edit del juego).
[Más en la guía completa](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos).

**Capitán y lanzadores.** No tienes que elegirlos: Build da a cada club un capitán y los jugadores
que tiran los penaltis, las faltas y los córneres.

**Muchos clubes a la vez.** **Más ▾** tiene **Pegar nombres...** y **Cargar nombres de un
archivo...** (un nombre por línea, en orden) e **Importar escudos...** (una carpeta de imágenes,
emparejadas con los clubes por el nombre del archivo). También tiene **Jugadores**, **Club del
juego...**, **Club NewLife...**, **Club nuevo aquí**, **Insertar club**, **Quitar club** y
**Mover a otra liga...**.

### Clubes que el juego ya tiene

Una liga de NewLife puede incluir clubes que el juego ya tiene. Salen en la lista con el nombre
del juego (el ratón encima muestra su **ID del club**). Si la línea verde del Paso 5 decía que
*también juegan una competición del juego*, haz esto con **cada uno** de ellos:

1. Pulsa el club en la lista.
2. Pulsa **Más ▾ → Club del juego...**.

**Deberías ver:** una ventana llamada **Club del juego**, con el club seleccionado y bajo la lista
una línea como `<club> juega en <competiciones>. Cada una de esas competiciones mantiene su
número de clubes: elige quién ocupa allí su lugar.`

3. Elige quién ocupa su sitio antiguo:
   - **Su lugar pasa a un club del juego que no juega nada:** y elige un club de la lista de
     debajo; o
   - **Su lugar pasa a un club nuevo, llamado:** y escribe un nombre. Build hace ese club.
4. Si el club juega una competición continental (Champions League, Libertadores ...), también
   está **Conserva sus plazas en competiciones continentales**. Marcada, sigue jugando esa
   competición y nadie tiene que ocupar su lugar allí.
5. Pulsa **Aceptar**.

La misma opción del menú pone cualquier club del juego en un puesto de tu liga: selecciona el
puesto, **Más ▾ → Club del juego...**, y busca por nombre, abreviatura o ID del equipo (**Solo
clubes sin liga** acota la lista). **Club nuevo aquí** (en **Más ▾**) devuelve el puesto a un club
nuevo; sale en gris salvo que un club del juego ocupe el puesto.

**Club NewLife...** (en **Más ▾**) pone clubes de NewLife, con sus plantillas, en el puesto
seleccionado y los siguientes: marca uno o más en la ventana que se abre y luego **Aceptar**. Así
una liga hecha a mano recibe clubes reales.

## Paso 9. La pestaña Jugadores

Los clubes de NewLife vienen con plantillas completas, así que no tienes que tocar esta pestaña.
Está ahí si quieres cambiar una plantilla.

1. **2. Mi mundo**, pestaña **Jugadores** (o selecciona un club en la pestaña **Clubes** y pulsa
   **Más ▾ → Jugadores**).
2. Arriba, elige la **Liga** y el **Club**. (O escribe en *Buscar un club...*.)

**Deberías ver:** la plantilla con las columnas **Orden**, **N.º**, **Nombre**, **Pos.**,
**Edad**, **Valoración**, **Pie**, **Cambiado** e **ID del jugador**, y el once inicial en un
campo debajo. Pulsa un jugador: la parte derecha lo muestra, en las pestañas **Lo básico**,
**Posiciones**, **Capacidades** y **Habilidades**.

- Cambia un nombre, dorsal, posición, valoración o capacidad a la derecha. El cambio se guarda
  enseguida.
- **Subir en el orden** / **Bajar en el orden**: el orden de la plantilla. Los primeros once son
  titulares. O arrastra un jugador a un puesto del campo. **Mejor once** pone al jugador más
  fuerte en cada puesto.
- **Fichar jugadores...** trae jugadores de otros clubes; **Traspasar a...** manda al jugador
  seleccionado a otro club.
- **Deshacer los cambios de este jugador** y **Deshacer todos los cambios de este club** vuelven
  atrás.

Todo lo de esta pestaña está en [Jugadores en la guía completa](mod-studio-guide.md#jugadores).

---

## Paso 10. Límites que detienen el Build

| Límite | Dónde lo ves |
|---|---|
| Clubes nuevos en total (unos 1500): el número de la línea `Clubes nuevos en tu mundo: X de los Y que admite el juego.` | Página NewLife Database: **Agregar a tu mundo** se queda en gris. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| De 10 a 24 clubes en una liga | NewLife Database: liga gris, `una liga tiene de 10 a 24 clubes`. Pestaña Clubes: `Una liga tiene de 10 a 24 clubes.` |
| Ligas nuevas por mundo: sin número fijo. Cada liga y copa ocupa una de las 255 competiciones del juego; **2. Mi mundo** muestra cuántas se usan (**COMPETICIONES**). Nuestro mundo de prueba juega 86 ligas nuevas. | Build: `error: <n> leagues, but the game has room for <m> ...` |
| Una liga debajo de una liga | Lista de **División**: en gris. Build: `... are all under ...; the game follows one link down from a league ...` |
| Divisiones hasta la 7.ª | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 ligas divididas por mundo; una división en dos o Apertura/Clausura por país | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Un club en una sola liga | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Un club del juego que juega algo necesita un sustituto | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Haz [Clubes que el juego ya tiene](#clubes-que-el-juego-ya-tiene). |

Todos los números: [8.3 Límites](mod-studio-guide.md#83-límites).

## Paso 11. Tu mundo se guarda solo

No hay nada que guardar a mano: Mod Studio guarda tu mundo un momento después de cada cambio.

**Deberías ver:** abajo en la ventana, **Tu mundo está guardado**.

**Archivo → Guardar tu mundo como...** guarda una copia con otro nombre, en una carpeta que
elijas (por ejemplo `Documents\FL26 Mod Studio`): ese archivo lo puedes encontrar y copiar.
**Archivo → Abrir un mundo...** vuelve a abrir uno guardado. **Archivo → Mundo nuevo** empieza
uno vacío.

Mod Studio vuelve a abrir tu mundo al iniciarse, así que lo que hiciste nunca se pierde.

## Paso 12. Construir

1. **2. Mi mundo**, pestaña **Construcción** (la primera pestaña).

**Deberías ver:** una nota que dice que Build es para modders, luego el botón grande **Construir
e instalar** y dos desplegables debajo: **Opciones del mundo: copas europeas, copas nacionales,
camisetas y caras de los clubes nuevos** (dos tarjetas, **Copas europeas** y **Clubes nuevos**,
con opciones) y **Paso a paso, y Exportar el mundo** (la fila **0. Instalar los módulos**, **1.
Comprobar el plan**, **2. Construir el mundo**, **3. Activarlo**, **4. Tras iniciar: comprobar** y
**Exportar el mundo...**). Luego una línea como `Mundo _FL26MyWorld: sin construir · módulos de
Mod Studio: instalados`, y un cuadro para el registro abajo. Mientras el mundo se construye, la
línea de arriba de **2. Mi mundo** y la barra de abajo muestran el tiempo que lleva y el paso en
el que está (`Construyendo... 3:12 · squads: filling them`).

2. Abre **Paso a paso, y Exportar el mundo** y pulsa primero **1. Comprobar el plan**. No cambia
   nada; solo lee tu mundo.

**Deberías ver:** en el cuadro, una línea `world _FL26MyWorld: 2 new leagues, ...` y una línea
por cada liga con sus clubes, división y formato (`18 clubs x2` son 18 clubes, todos contra todos
dos veces; `division 2  below ... (3 up/down)` es una segunda división), y sus
`European places:`. Una línea que empieza por `error:` dice qué arreglar primero; mira la tabla
del final.

3. Pulsa **Construir e instalar**. Pregunta `¿Construir _FL26MyWorld y ponerlo en el juego? ...`:
   pulsa **Sí**.

   Si las tablas del juego son más antiguas que el juego, pregunta antes si las desempaqueta de
   nuevo: pulsa **Sí** (uno o dos minutos).

   Pone los módulos de Mod Studio, construye tu mundo y lo pone en el juego, todo de una vez.
   Tarda de unos segundos a unos minutos. Cuando desde el último Build solo cambiaron imágenes
   (un logo, un escudo, una bandera), tarda unos segundos.

**Deberías ver:** una ventana **Construcción terminada** con una marca en cada línea: **Mundo
construido**, **Ligas y clubes** (`2 ligas · 36 clubes nuevos`), **Módulos instalados y
activados**, **En el juego** e **Inicia el juego para jugarlo**. En **Antes de jugar**:
`Empieza una carrera nueva de Liga Máster: una carrera guardada antes conserva el mundo anterior.`
Pulsa **Hecho**.

Si dice que **en la carpeta de partidas del juego hay una partida Edit de antes de este Build**:
pulsa **Apartar el guardado de Edit**. Una partida Edit antigua oculta los nombres y las
plantillas nuevos.

En **2. Mi mundo** la tarjeta de tu mundo está ahora en verde: **● EN EL JUEGO AHORA**.

**Paso a paso en lugar del botón grande** (el mismo resultado, en **Paso a paso, y Exportar el
mundo**):

1. **1. Comprobar el plan**: como arriba.
2. **2. Construir el mundo**: lo construye. Si el mundo existe, pregunta `... ya existe.
   ¿Construirlo de nuevo?`: **Sí**. El registro termina con
   `Siguiente: 3. Activarlo, y luego inicia el juego.`
3. **3. Activarlo**: pregunta `¿Poner _FL26MyWorld en el juego (activarlo en sider.ini)?`:
   **Sí**. El registro termina con `Inicia el juego y luego 4. comprueba.`

**Qué significan las líneas del registro:**

| Línea | Significado |
|---|---|
| `instalando los módulos ...`, `modules: ... copied, ... already there` | Se ponen en su sitio los módulos de Mod Studio. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | El resumen de tu mundo. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Una liga: sus ids en el juego, su división y su formato. |
| `European places: 1st Champions League qualifying, ...` | Adónde van sus mejores clubes. |
| `no European places: the new leagues send nobody to Europe` | Un aviso, no un error: ajusta **Europa** en una primera división si lo quieres. |
| `construyendo ...` | Se está escribiendo el mundo. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | El mundo está en el juego. |
| `error: ...` | Build se paró y no cambió nada en el juego. Arregla lo que dice (tabla del final) y vuelve a construir. |

Las opciones de **Opciones del mundo** (**Incluir la Liga Conferencia**, **Sorteo de la copa
nacional**, **Equipaciones con los colores del club** ...) se explican en
[8.2](mod-studio-guide.md#82-construir-activar-jugar). Los valores por defecto están bien.

## Paso 13. Juega: una Liga Máster NUEVA y luego la comprobación

1. Pulsa el botón verde **Iniciar el juego** arriba a la derecha (o **Juego → Iniciar el juego**).
2. En el juego: **Master League** → **New game**. No Continue: una carrera guardada antes
   conserva el mundo anterior.
3. En **Select Team**, desplázate: tus ligas están en la lista, bajo sus países.
4. Elige un club y juega.

Cada mundo guarda sus propias carreras: cuando otro mundo entra en el juego, Mod Studio aparta
las carreras de este mundo, y las devuelve cuando este mundo vuelve a estar en el juego. No se
borra nada. ([Más](mod-studio-guide.md#31-mi-mundo).)

Luego deja que Mod Studio compruebe que el juego tomó el mundo:

1. Cierra el juego (o al menos inícialo una vez hasta el menú principal).
2. En Mod Studio: **2. Mi mundo** → pestaña **Construcción** → **Paso a paso, y Exportar el
   mundo** → **4. Tras iniciar: comprobar**.

**Deberías ver:** una línea por módulo que dice cuántas ligas leyó del archivo del mundo, y al
final `the world works as built`. Una línea `not loaded` o `did NOT read the world file`, y al
final `something is wrong -- see the lines above`, significan que algo no funcionó: mira la
tabla del final.

## Paso 14. Cambiar algo más tarde

1. Cierra el juego.
2. Abre Mod Studio. Abre tu mundo solo (o **Archivo → Abrir un mundo...**).
3. Cambia lo que quieras en la página **NewLife Database**, o en las pestañas de **2. Mi mundo**:
   **Ligas**, **Clubes** o **Jugadores**. Se guarda solo.
4. **Construir e instalar** (pestaña **Construcción**) → **Sí**.

**¿Necesitas una carrera nueva?** Sí: empieza una Master League nueva después de cada cambio que
construyas. Una carrera toma su propia copia de las ligas, clubes y plantillas al empezar, así que
una carrera en la que ya estás conserva las antiguas. Y una carrera guardada con un mundo necesita
ese mismo mundo para cargarse, así que mantén el mundo en el juego mientras la juegas.

**Después de actualizar Mod Studio.** Construye tu mundo una vez más con la versión nueva y
empieza una carrera nueva. Con la 0.2.4 importa: un mundo construido antes tiene al portero como
capitán de todos los clubes. Build ahora da a cada club un capitán y lanzadores.

**Una versión más nueva de NewLife.** Pon sus partes en una carpeta nueva, **Abrir NewLife
Database...** en esa carpeta y luego **Más ▾ → Actualizar mis ligas a esta versión**. Cada liga
conserva su nombre, división, formato, plazas europeas y copas; los clubes y las plantillas vienen
de la versión nueva (la casilla **Mantener mis clubes** conserva tu propia composición). Vuelve a
construir y empieza una carrera nueva.
[Más](mod-studio-guide.md#84-newlife-database-clubes-y-jugadores-reales).

**Quitar una liga.** **Ligas** → **Nuestras** → púlsala → **Quitar** → **Sí**. Sus clubes y los
cambios de sus jugadores se van con ella.

## Paso 15. Compartir lo que has hecho

Hay dos maneras. Elige una:

| | Paquete de ligas (`.fl26pack`) | Mundo exportado (`.zip`) |
|---|---|---|
| Qué lleva | Tus ligas, listas para añadir a otro mundo: clubes, nombres, escudos, logos, plantillas, caras y, si quieres, equipaciones y marcadores. | El mundo exactamente como lo construiste. |
| La otra persona | Lo añade a su propio mundo y construye, así que funciona junto a sus propias ligas y otros paquetes. | Lo instala y juega. No hay nada que construir, pero sustituye a cualquier otro mundo que tenga en el juego. |
| Cómo lo instala | [Camino C de Instalar un paquete listo](install-a-pack.md#camino-c-un-paquete-de-ligas-fl26pack) | [Camino A de Instalar un paquete listo](install-a-pack.md#camino-a-un-mundo-listo-un-zip) |

### Un paquete de ligas

1. **2. Mi mundo → Más ▾ → Paquetes de ligas → Crear un paquete...** (o barra de arriba:
   **Archivo → Crear un paquete de ligas...**).

**Deberías ver:** una ventana **Crear un paquete de ligas**.

2. Rellena **Nombre** (obligatorio), **Autor**, **Versión** (`1.0` para empezar) y
   **Descripción**.
3. En **Ligas**, marca las ligas que van dentro (**Seleccionar todo** / **No seleccionar
   ninguno**). Una liga que está debajo de otra liga tiene que ir con ella.
4. **También mis cambios en las ligas, clubes y jugadores del propio juego** (solo si cambiaste
   alguno): márcalo para meterlos también.
5. En **Qué va dentro** está todo marcado: **Plantillas**, **Caras y retratos de jugadores**,
   **Escudos y logos de ligas**, **Entrenadores**, **Colores de las equipaciones**,
   **Equipaciones**, **Marcadores** y **Estadios locales**. Desmarca lo que no quieras compartir.
   Las equipaciones suman unos 10 MB por liga y un marcador unos 7 MB.
6. Pulsa **Guardar el paquete...**. Se abre una ventana de guardado **Guardar el paquete** con un
   nombre como `<nombre>-1.0.fl26pack`. Elige una carpeta que vuelvas a encontrar (Escritorio,
   Documentos ...) y pulsa **Guardar**.

**Deberías ver:** `Guardado: <archivo>` con cuántas ligas, clubes y caras lleva. Ese único
archivo es lo que compartes. Si pasa de 10 MB, Mod Studio lo dice: Discord no lo acepta, así que
compártelo por Google Drive, Dropbox, MEGA o algo parecido, o desmarca **Equipaciones** y
**Marcadores**, o haz un paquete por liga.

Más: [9. Paquetes de ligas](mod-studio-guide.md#9-paquetes-de-ligas-comparte-una-liga-entera).

### Un mundo entero (zip)

1. Construye primero (Paso 12). El mundo tiene que estar construido.
2. **2. Mi mundo** → **Exportar...** en la tarjeta del mundo. (O pestaña **Construcción** →
   **Paso a paso, y Exportar el mundo** → **Exportar el mundo...**.)
3. Se abre una ventana de guardado con el nombre del mundo como nombre de archivo
   (`_FL26MyWorld.zip`), en tu carpeta de usuario la primera vez (después, en la carpeta que
   usaste la última vez). Elige una carpeta y pulsa **Guardar**.

**Deberías ver:** al cabo de un momento, `Guardado <archivo>` y cuántos jugadores nuevos reciben
una cara generada. El zip lleva la carpeta del mundo, su archivo de mundo y un léame.

Quien lo instala necesita los módulos de Mod Studio con el paquete de caras; instalar el zip en
**Importa tu mundo** los pone. Sin ellos todos los jugadores nuevos tienen la misma cara. El léame
del zip lo dice.

Más: [9.1 Exportar el mundo](mod-studio-guide.md#91-exportar-el-mundo-un-mundo-construido-para-otro-pc).

---

## Si algo sale mal

Los mensajes salen en una ventana de error, en la línea verde o roja bajo el título de una
página, o en el registro de Build después de `error:`. `<...>` es un nombre o un número.

| Lo que ves | Qué hacer |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Elegiste la carpeta equivocada, o descomprimiste las partes. Abre la carpeta que contiene los propios archivos `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Hay dos versiones de NewLife mezcladas. Deja en la carpeta las partes de una sola versión. |
| `<file> is not a NewLife part (...) -- download it again` | La descarga se rompió. Vuelve a descargar esa parte. |
| Una liga gris, `una liga tiene de 10 a 24 clubes` | Añade o deja fuera clubes (Paso 4) hasta que tenga de 10 a 24. |
| Una liga gris, `liga propia del juego: Llevar las ligas del juego a esta temporada` | El juego ya la tiene. Usa **Llevar las ligas del juego a esta temporada...**. |
| **Agregar a tu mundo** se queda en gris | No hay nada seleccionado que se pueda añadir, o la selección pasaría del límite de clubes nuevos (la línea de abajo). |
| `<club> jugaría en dos ligas (<liga> y <liga>).` | Desmarca el club en una de ellas. |
| `<liga> no tiene un país que el juego conozca.` | Esta liga no se puede añadir. |
| `Una liga necesita un nombre y un país.` / `Elige el país de la lista.` | En **Editar liga...**, rellena **Nombre** y elige el **País** de la lista en lugar de escribirlo entero. |
| `Ya hay una liga llamada <nombre>.` | Dale otro nombre a la liga. |
| `European places: position <n> -- the league has <m> clubs` | Una fila de **Europa** apunta más allá del último club. Cámbiala o quítala. |
| `European places: position <n> is listed twice` | Dos filas tienen el mismo puesto. Quita una. |
| `European places: a cup winner's place, but the country has no cup` | Marca **Copa nacional**, o quita la fila **Campeón de copa**. |
| `Clubes, vueltas y grupos deben ser números.` | En **se divide en dos**, escribe los grupos como números, por ejemplo `6/6`. |
| `Una liga de febrero a diciembre todavía no tiene fase final, Apertura/Clausura ni copa de la liga.` | Pon **Temporada** en **agosto a mayo**, o quita la división en dos, el Apertura/Clausura o la copa de la liga. |
| `Esta división juega de febrero a diciembre con la liga de arriba, y una liga que juega de febrero a diciembre todavía no tiene división en grupos ni Apertura/Clausura.` | Dale a esta división **todos contra todos**. |
| `Los clubes sin liga son todos clubes nuevos: quita primero los clubes del juego (Editar club).` | La liga tiene clubes del juego. En la pestaña **Clubes** selecciona cada uno y usa **Más ▾ → Club nuevo aquí**, y luego vuelve a ajustar **Clubes sin liga**. |
| `<liga> está debajo de esta liga; los clubes sin liga no tienen nada debajo.` (o `una liga de exhibición no tiene ninguna.`) | Otra liga tiene esta como su **División**. Cambia primero esa liga. |
| `Una liga tiene de 10 a 24 clubes.` (pestaña Clubes) | Insertar club / Quitar club dejaría la liga fuera de 10 a 24. |
| `Abre antes la NewLife Database en la página NewLife.` | **Club NewLife...** necesita la carpeta de NewLife: ábrela una vez en **NewLife Database**. |
| `Elige el club que ocupa su lugar.` / `Dale un nombre al club nuevo.` / `Un club no puede ocupar su propio lugar.` | En **Club del juego**, elige un club sustituto, o escribe un nombre para el nuevo. |
| `error: no hay tablas del juego -- Ajustes > Desempaquetar las tablas del juego` | **5. Ajustes → Desempaquetar las tablas del juego**. |
| `error: no hay carpeta del juego -- Juego > Elegir la carpeta del juego` | **Juego → Elegir la carpeta del juego...**. |
| `error: el nombre del mundo debe empezar por _FL26` | **Ligas → Más ▾ → Nombre del mundo y archivo...**: un nombre que empiece por `_FL26`. |
| `error: nada que construir: añade una liga o cambia una del juego ...` | Tu mundo está vacío. Añade ligas (Pasos 3 a 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Haz [Clubes que el juego ya tiene](#clubes-que-el-juego-ya-tiene) con ese club. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | La misma ventana: escribe un nombre junto a **Su lugar pasa a un club nuevo, llamado:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Saca el club de una de las ligas (**Club nuevo aquí** en la pestaña Clubes, o desmárcalo antes de añadirla). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Demasiados clubes nuevos. Quita una liga, o clubes. |
| `error: <n> leagues, but the game has room for <m> ...` | Demasiadas ligas nuevas. Quita algunas. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Solo una liga puede estar debajo de una liga. Cambia la **División** de las otras. |
| `error: <league>: division 8 -- the rank field stops at 7` | Un país llega hasta la 7.ª división. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Dale a las otras ligas **todos contra todos**. |
| `Las tablas del juego que usa Mod Studio son más antiguas que el juego: ... ¿Extraerlas de nuevo primero?` | Pulsa **Sí**. |
| Los pasos de Build y **Construir e instalar** están en gris | El mundo abierto es un mundo listo de un zip: ya está construido. Abre o crea un mundo tuyo (**+ Mundo nuevo** en **2. Mi mundo**, o **Activar** en la tarjeta de tu mundo), o convierte el mundo listo en tuyo con **Hacerlo editable...**. |
| `<mundo> aún no está construido: primero 2. Construir el mundo.` (Exportar el mundo) | Construye primero y luego exporta. |
| `Ponle un nombre al paquete.` / `Marca al menos una liga.` / `Tu mundo todavía no tiene ligas.` | En **Crear un paquete de ligas**, rellena **Nombre** y marca una liga; tu mundo necesita ligas primero. |
| No hay ligas nuevas en Select Team | Empieza una Master League **nueva**. Luego **4. Tras iniciar: comprobar** (Paso 13). |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Inicia el juego hasta su menú principal, ciérralo y vuelve a comprobar. |
| `<module> not loaded` / `did NOT read the world file` | **2. Mi mundo → Construcción → Paso a paso, y Exportar el mundo → 0. Instalar los módulos**, luego **3. Activarlo**, vuelve a iniciar el juego y vuelve a comprobar. ¿Sigue mal? Pregunta en Discord. |
| Los nombres de los clubes son los del juego, no los tuyos | Una partida Edit antigua los oculta: **Apartar el guardado de Edit** en la ventana **Construcción terminada**, o saca `EDIT00000000` de la carpeta de partidas del juego. |
| El portero es el capitán de todos los clubes nuevos | El mundo se construyó antes de la 0.2.4. Vuelve a construirlo y empieza una carrera nueva. |
| El escudo del pantalón de una equipación dibujada sale de lado | La equipación se dibujó antes de la 0.2.4. Borra los archivos `kitmaker.txt` de `SiderAddons\content\kit-server\<tu mundo>` y vuelve a pulsar **Construir e instalar**: las equipaciones se dibujan de nuevo con el escudo bien puesto. |
| Todos los jugadores nuevos tienen la misma cara | **1. Inicio → Instalar ahora** (cuando Inicio dice que los módulos faltan o son antiguos), o **2. Mi mundo → Construcción → Paso a paso, y Exportar el mundo → 0. Instalar los módulos**: trae el paquete de caras. Luego vuelve a iniciar el juego. |

**Para pedir ayuda:** en el [Discord](https://discord.gg/StQqtk3G3M), manda una captura de lo que
ves, el texto del registro de Build y tu `sider.log` (**Juego → Abrir sider.log**).
