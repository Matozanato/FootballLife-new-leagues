# Crear tus propias ligas y paquetes: cada clic, en orden

> [English](../en/make-your-own-leagues.md) · [hrvatski](../hr/make-your-own-leagues.md) · **español** · [português](../pt/make-your-own-leagues.md)

> La otra guía paso a paso: [Instalar un paquete listo](install-a-pack.md)
> · cada página y opción explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · preguntas: [faq.md](../../docs/faq.md) (en inglés) · ayuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta guía escribe los nombres de los botones en inglés, tal como salen en la ventana, con el nombre
español entre paréntesis la primera vez. La ventana se puede pasar a español con
**Language** (*Idioma*) → Español.

Esta página te lleva de cero a tus propias ligas en el juego: ligas reales con clubes y jugadores
reales de la **NewLife Database**, ajustadas como quieras, construidas, jugadas y compartidas con
otras personas. Dice qué pulsar, el nombre exacto de cada botón y campo tal como lo muestra Mod
Studio, y qué deberías ver después de cada paso. Haz los pasos en orden. Si ves algo distinto de
lo que dice un paso, para ahí y mira en
[Si algo sale mal](#si-algo-sale-mal).

Tres palabras que vas a ver todo el rato:

- **Receta**: tu lista de ligas y todo lo que ajustas para ellas. La cambias en las páginas de
  **LEAGUE BUILDER**. Es solo un plan: nada llega al juego hasta que pulsas **Build**.
- **Mundo**: lo que Build hace con la receta, una carpeta cuyo nombre empieza por `_FL26`
  (`_FL26MyWorld` si no lo cambias). El juego lo lee mientras está activado.
- **Build**: el botón que convierte la receta en un mundo y lo mete en el juego.

**Contenido**

- [Antes de empezar: la preparación de una sola vez](#antes-de-empezar-la-preparación-de-una-sola-vez)
- [Paso 1. Consigue la NewLife Database](#paso-1-consigue-la-newlife-database)
- [Paso 2. Ábrela en la página NewLife Database](#paso-2-ábrela-en-la-página-newlife-database)
- [Paso 3. Elige tus ligas](#paso-3-elige-tus-ligas)
- [Paso 4. Elige los clubes de una liga](#paso-4-elige-los-clubes-de-una-liga)
- [Paso 5. Añadir a la receta](#paso-5-añadir-a-la-receta)
- [Paso 6. La página Leagues: cada ajuste de una liga](#paso-6-la-página-leagues-cada-ajuste-de-una-liga)
- [Paso 7. Ejemplo: un país con dos divisiones](#paso-7-ejemplo-un-país-con-dos-divisiones)
- [Paso 8. La página New clubs: nombres, escudos, equipaciones, clubes del juego](#paso-8-la-página-new-clubs-nombres-escudos-equipaciones-clubes-del-juego)
- [Paso 9. La página Players](#paso-9-la-página-players)
- [Paso 10. Límites que detienen el Build](#paso-10-límites-que-detienen-el-build)
- [Paso 11. Guarda la receta](#paso-11-guarda-la-receta)
- [Paso 12. Build](#paso-12-build)
- [Paso 13. Juega: una Liga Máster NUEVA y luego la comprobación](#paso-13-juega-una-liga-máster-nueva-y-luego-la-comprobación)
- [Paso 14. Cambiar algo más tarde](#paso-14-cambiar-algo-más-tarde)
- [Paso 15. Compartir lo que has hecho](#paso-15-compartir-lo-que-has-hecho)
- [Si algo sale mal](#si-algo-sale-mal)

---

## Antes de empezar: la preparación de una sola vez

Haz primero, una vez, los pasos 1 a 5 de la otra guía:
[cierra el juego](install-a-pack.md#paso-1-cierra-el-juego),
[descarga Mod Studio](install-a-pack.md#paso-2-descarga-mod-studio),
[dile dónde está tu juego](install-a-pack.md#paso-3-dile-dónde-está-tu-juego),
[desempaqueta las tablas del juego](install-a-pack.md#paso-4-desempaqueta-las-tablas-del-juego) e
[instala los módulos de Mod Studio](install-a-pack.md#paso-5-instala-los-módulos-de-mod-studio).
Luego vuelve aquí.

Mantén el juego cerrado todo el tiempo que trabajes en Mod Studio.

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

1. Barra de la izquierda, en **LEAGUE BUILDER**: pulsa **NewLife Database**.
2. Pulsa **Open NewLife Database...** (*Abrir NewLife Database...*) arriba.
3. Elige la carpeta del Paso 1 (la carpeta, no un zip de dentro) y confirma.
4. Espera unos segundos mientras la lee.

**Deberías ver:** encima de la lista, la versión de NewLife y la carpeta, y debajo de ellas
`Parts:` con las partes que encontró. Más abajo, una lista larga de ligas.

Mod Studio recuerda la carpeta: la próxima vez la página la abre sola.

**Buscar.** El cuadro encima de la lista, *Search leagues or countries* (*Buscar ligas o
países*), deja solo las ligas cuyo nombre o país contiene lo que escribes. Escribe `brazil` o
`liga`, por ejemplo. Vacía el cuadro para volver a verlas todas.

**Las columnas.** Pulsa la cabecera de una columna para ordenar por ella, pulsa otra vez para
invertir el orden.

| Columna | Qué te dice |
|---|---|
| **League** (*Liga*) | El nombre de la liga. Un `*` detrás significa que cambiaste sus clubes (Paso 4). |
| **Country** (*País*) | Dónde va en el juego. |
| **Clubs** (*Clubes*) | Cuántos clubes tendrá, tal como lo tienes ajustado ahora. |
| **In game** (*En el juego*) | Cuántos de sus clubes ya tiene el juego (conservan sus propios nombres, escudos, equipaciones y jugadores). |
| **Players** (*Jugadores*) | Cuántos jugadores tienen sus clubes en NewLife. |
| **Level** (*Nivel*) | Lo fuerte que es la liga. Más alto es más fuerte. |
| (última columna) | Por qué no se puede añadir una liga gris. Vacía para una liga que puedes añadir. |

**Por qué algunas ligas están en gris.** Una liga gris no se puede añadir, y la última columna
dice por qué:

- `a league takes 10 to 24 clubs`: una liga del juego tiene de 10 a 24 clubes, los nuevos y los
  del juego juntos. Esta tiene menos o más. Aún puedes arreglarlo en el Paso 4 (añadir o dejar
  fuera clubes) hasta que encaje.
- `the game's own league: Bring the game's leagues to this season`: el juego ya tiene esta liga
  (la Premier League, la Championship ...). No se añade una segunda vez. El botón
  **Bring the game's leagues to this season...** (*Llevar las ligas del juego a esta
  temporada...*) de arriba da en su lugar a las ligas del propio juego los clubes y las
  plantillas de esta temporada de NewLife; ver
  [8.4 en la guía completa](mod-studio-guide.md#84-newlife-database-clubes-y-jugadores-reales).

Si la página dice que Mod Studio no tiene tablas del juego y ofrece abrir Settings: pulsa
**Yes** y haz
[Unpack the game's tables](install-a-pack.md#paso-4-desempaqueta-las-tablas-del-juego)
(*Desempaquetar las tablas del juego*).

## Paso 3. Elige tus ligas

1. Pulsa una liga de la lista para seleccionarla. Su fila se resalta.
2. Para más de una: mantén **Ctrl** y pulsa cada una. (O pulsa la primera, mantén **Shift**
   y pulsa la última para tomar todo lo que hay entre ellas.)

**Deberías ver:** abajo de la página una línea como
`New clubs in the recipe: 0 of the 793 the game takes.  Selected: 18 more.`

- El **primer** número es cuántos clubes nuevos tiene ya tu receta.
- El **segundo** es cuántos clubes nuevos caben en el juego en total. Mod Studio lo calcula a
  partir de las tablas de tu juego, así que puede ser un poco distinto en otra versión del juego.
- **Selected** es cuántos clubes nuevos añadirían las ligas que elegiste.

Si la receta y la selección juntas pasan de lo que admite el juego, **Add to the recipe**
(*Añadir a la receta*) se queda en gris: elige menos ligas.

## Paso 4. Elige los clubes de una liga

Este paso es opcional. Sáltatelo para tomar una liga exactamente como la tiene NewLife.

Selecciona **una** liga (solo una). La lista de la derecha muestra sus clubes: **Club** y
**Players** (cuántos jugadores le da NewLife). Un club que el juego ya tiene sale en gris, con
`in the game` en lugar de un número.

- **Dejar un club fuera:** pulsa su casilla para desmarcarla.
- **Traer un club de otra liga** (la primera división de esta temporada es la de la temporada
  pasada con dos ascendidos, por ejemplo): pulsa **Add a club from another league...**
  (*Añadir un club de otra liga...*) debajo de la lista.
  1. Se abre una ventana con todos los clubes de las partes de NewLife que abriste, cada uno con
     su liga entre paréntesis.
  2. Escribe en el cuadro de búsqueda para encontrar un club o una liga.
  3. Marca uno o más clubes. La línea bajo la lista dice cuántos elegiste.
  4. Pulsa **OK**.

  **Deberías ver:** el club al final de la lista, con `from <its league>` al lado.

**Deberías ver:** la fila de la liga en la lista tiene ahora un `*`, y su número de **Clubs**
cambió. Una liga gris que ahora tiene de 10 a 24 clubes pasa a normal.

Un club solo puede jugar en una liga. Si lo añades a dos, Mod Studio te para en el Paso 5.

## Paso 5. Añadir a la receta

Con tu liga o tus ligas seleccionadas, pulsa **Add to the recipe** arriba.

**Deberías ver:** una línea verde bajo el título de la página. Qué significa cada línea:

| Línea verde | Qué significa |
|---|---|
| `Added: <leagues>. Change them on Leagues, New clubs and Players, then Build.` | Las ligas están en tu receta, cada una como primera división de su país, todos contra todos dos veces. Todavía no hay nada en el juego. |
| `<clubs> also play in a competition of the game: on New clubs pick each one and use Club of the game to choose the club that takes its place there.` | Estos clubes de tu liga nueva son clubes que el juego ya tiene, y también juegan en algún sitio del juego (una liga, una copa, la Europa League ...). Un club juega en una sola liga, así que su sitio antiguo necesita otro club. Ese club lo eliges en el [Paso 8](#clubes-que-el-juego-ya-tiene). Hasta que lo hagas, Build se para con un error que nombra el club. |
| `<n> players stay at their game club (their club would have too few players).` | Los jugadores que el juego ya tiene normalmente pasan al club de NewLife. Estos se quedan, para que su club antiguo conserve al menos 18 jugadores. No hay que hacer nada. |
| `<n> players are not added: another league already has them.` | Una liga que añadiste antes ya se quedó con estos jugadores. No hay que hacer nada. |

Si una ventana de error dice `<club> would play in two leagues (<league> and <league>).`,
desmarca ese club en una de las dos ligas (Paso 4) y vuelve a intentarlo.

¿Quieres ligas de otros continentes? Selecciónalas también y pulsa **Add to the recipe** otra
vez. Cada clic añade; nunca quita lo que ya hay.

---

## Paso 6. La página Leagues: cada ajuste de una liga

1. Barra de la izquierda: pulsa **Leagues** (*Ligas*).
2. Encima de la lista, pulsa **Ours**: la lista muestra solo las ligas de tu receta. (**All**
   muestra todas las ligas, también las del juego; **Changed**, las ligas del juego que
   cambiaste.) Las ligas están agrupadas por continente.
3. Pulsa tu liga.

**Deberías ver:** a la derecha, `OURS`, el nombre y el logo de la liga, y las filas **Country**,
**Clubs**, **Format**, **Division**, **Up / down**, **Europe** (*Europa*) y **League ID** (*ID de
la liga*) (`not built yet` hasta el primer Build), y luego los escudos de sus clubes. Debajo, los
botones **Edit league...** (*Editar liga...*), **Add lower tier** (*Añadir división inferior*),
**Clubs and names** (*Clubes y nombres*), **Players** y **Remove**.

Puedes arrastrar una liga hacia arriba o hacia abajo en la lista para ordenar las ligas de un
continente.

4. Pulsa **Edit league...**.

**Deberías ver:** una ventana llamada **League** con los campos de abajo, de arriba abajo. Un
campo gris no se puede usar con lo que ajustaste encima (por ejemplo una copa en una segunda
división). El **?** junto a **OK** explica la ventana en pocas palabras. Nada es obligatorio:
los valores por defecto funcionan, y **Cancel** no cambia nada.

| Campo | Qué es y qué hacer |
|---|---|
| **Name** (*Nombre*) | El nombre de la liga en el juego. Dos ligas no pueden tener el mismo nombre. Mantenlo por debajo de unos 38 caracteres: un nombre más largo sale como una fila vacía en la lista de ligas de Kick Off. |
| **Country** | Escribe unas letras y elige de la lista (`korea` encuentra las dos Coreas). Da la bandera y el lugar donde aparece la liga en el juego. |
| **Clubs** | De 10 a 24. Para una liga de NewLife, déjalo como está: un número menor quita los últimos clubes, uno mayor añade clubes inventados al final. |
| **Clubs in no league** (*Clubes sin liga*) | Déjalo en `(no -- a league)`. Las otras opciones (*Other European teams* ...) son para un club, o unos pocos, sin una liga alrededor; van a los grupos "Other ..." del juego, y la mayoría de los campos de abajo se ponen en gris. [Más](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos). |
| **Format** | Elige uno: **everyone plays everyone, times:** y el número (de 1 a 4; 2 es ida y vuelta); **splits in two (Scottish style)**, con `first` *n* `x, then groups` *6/6* *n* `x` (los grupos deben sumar los clubes); o **Apertura and Clausura, then playoffs of:** (*Apertura y Clausura, luego liguilla de:*) *8 clubs* (*8 clubes*), *4 clubs* (*4 clubes*) o *no playoffs* (*sin liguilla*) (dos torneos cortos por temporada, 18 clubes como máximo). |
| **Division** | `(top division)` = la mejor liga de su país. Para una segunda división, elige la liga un nivel por encima: tus ligas nuevas están arriba de la lista, luego las ligas del juego con un número entre paréntesis. `= division 2` al lado muestra el nivel. Una liga que ya tiene una liga debajo sale en gris (`-- under it: ...`): una liga puede tener una sola liga debajo. Ver el [Paso 7](#paso-7-ejemplo-un-país-con-dos-divisiones). |
| **Exhibition only -- not in Master League** (*Solo exhibición -- no está en la Liga Máster*) | Déjalo desactivado. Activado: la liga es solo para Kick Off y partidos de exhibición (leyendas, una temporada histórica); nunca juega una temporada de Liga Máster, y la división, las copas y Europa se ponen en gris. No empieces una carrera con uno de sus clubes. |
| **Season** (*Temporada*) | Solo primera división: **August to May** (*agosto a mayo*) (como en Europa) o **February to December** (*febrero a diciembre*) (como en Brasil o Japón). Una división de abajo sigue a la liga de encima. Febrero a diciembre todavía no puede tener división en grupos, Apertura/Clausura ni las copas del país. |
| **Up / down** | De 1 a 6: cuántos clubes cambian de sitio con la liga de encima al final de la temporada. Solo tiene sentido para una división debajo de otra. |
| **Logo** | **Pick picture...** un PNG o JPG para la liga (un PNG con fondo transparente queda mejor). **Clear** lo quita. Vacío: `(made for you)`, se dibuja un logo al hacer Build. |
| **Country flag** (*Bandera del país*) | Tu propia imagen de la bandera del país. Vacío: `(the game's own)`. Déjalo vacío salvo que el juego no tenga una buena bandera. |
| **Cup** (*Copa*) | Solo primera división. Marca **National cup** (*Copa nacional*) para dar al país una copa eliminatoria (esta liga y la división de debajo). El cuadro de al lado es el nombre de la copa; vacío = el nombre de la liga + Cup. |
| **Super cup (champion v cup winner)** (*Supercopa (campeón contra ganador de copa)*) | Un partido a finales de julio. Necesita **National cup** marcado. |
| **League cup** (*Copa de la liga*) | Solo primera división. Una segunda copa eliminatoria, como la Carabao Cup de Inglaterra: esta liga y la de abajo, hasta 44 clubes. El cuadro es su nombre; vacío = el nombre de la liga + League Cup. |
| **Cup logos** (*Logos de las copas*) | Una imagen para cada una: la **Cup**, la **Super cup** (*Supercopa*), la **League cup** y los **Playoffs**. Vacío: un emblema con las iniciales de la copa. |
| **Formation** (*Formación*) | Cómo forman los clubes de la liga. Elige una de la lista, o déjalo vacío para el 4-2-3-1 por defecto del juego. Un club puede tener la suya (Paso 8). |
| **Europe** | Solo primera división: qué puesto de la tabla va a qué competición continental. El botón que empieza por **Top flight:** rellena las plazas habituales del continente del país (para Europa: `Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL` (*Primera división: 1.º fase previa UCL, 2.º UEL, 3.º UECL*)). **Add place** (*Añadir plaza*) añade una fila: elige el **League position** (*Puesto en la liga*) (por debajo de 1 dice **Cup winner** (*Campeón de copa*)) y la **Competition** (*Competición*). La **✕** de una fila la quita, **Clear** las quita todas. Déjalo vacío para una segunda división. |

5. Pulsa **OK**.

**Deberías ver:** la ventana se cierra y las filas de la derecha muestran lo que ajustaste.

Una liga de NewLife entra sin plazas europeas. Si quieres a sus clubes en la Champions League y
las demás, ajusta **Europe** ahora; si no, **1. Check the plan** te lo recuerda con
`no European places: the new leagues send nobody to Europe`.

El significado de cada formato, copa y plaza europea a fondo (fechas, rondas previas, tamaños de
las copas):
[sección 8 de la guía completa](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos)
y [8.2](mod-studio-guide.md#82-construir-activar-jugar).

**More ▾** (*Más*) (arriba de la página Leagues) tiene las herramientas para todo el mundo:
**Pre-season cups** (*Torneos de pretemporada*), **Cups of the game's countries** (*Copas de los
países del juego*), **European places of the game's leagues** (*Plazas europeas de las ligas del
juego*), **UEFA ranking** (*Ranking UEFA*), **South American places** (*Plazas sudamericanas*),
**Competition names** (*Nombres de las competiciones*) (nombres y logos nuevos para copas y
competiciones continentales) y **World name and recipe...** (*Nombre del mundo y receta...*) (el
nombre de la carpeta del mundo; debe empezar por `_FL26`). No necesitas ninguna de ellas para un
primer mundo.

**Una liga sin clubes de NewLife.** **Add league** arriba de la página Leagues abre la misma
ventana **League** para una liga hecha desde cero: dale un **Name**, un **Country** y un número
de **Clubs**, y Build crea los clubes con plantillas completas y un entrenador. Les pones nombre
en **New clubs** (Paso 8), donde **NewLife club...** (*Club NewLife...*) también puede meter
clubes reales en ella.

## Paso 7. Ejemplo: un país con dos divisiones

Supón que tus partes de NewLife tienen la primera y la segunda división de un país, aquí
llamadas *First League* y *Second League*. Quieres ascensos y descensos entre ellas.

1. **NewLife Database**: selecciona *First League* y pulsa **Add to the recipe**. (La de arriba
   primero.)
2. Selecciona *Second League* y pulsa **Add to the recipe**.

   **Deberías ver:** la línea verde `Added:` cada vez. Las dos son ahora primeras divisiones del
   mismo país, que todavía no es lo que quieres.

3. **Leagues** → **Ours** → pulsa *Second League* → **Edit league...**.
4. **Division**: abre la lista y elige *First League* (tus ligas están arriba).

   **Deberías ver:** `= division 2` al lado. **Cup**, **League cup**, **Season** y el botón
   **Top flight** se ponen en gris: son cosa de la primera división.

5. **Up / down**: cuántos clubes suben y bajan entre las dos, por ejemplo `3`.
6. **Europe**: si tiene filas, pulsa **Clear**. Una segunda división no manda a nadie a Europa.
7. Pulsa **OK**.

   **Deberías ver:** a la derecha, **Division** `2  (below First League)` y **Up / down**
   `3 with First League above`. Pulsa *First League*: su **Up / down** dice
   `3 with Second League below`.

8. Pulsa *First League* → **Edit league...** y ajusta lo que es de la primera división:
   **Europe** (el botón **Top flight**), y si quieres **National cup**, **Super cup** y
   **League cup**. Pulsa **OK**.

Una tercera división funciona igual: su **Division** es *Second League*. El juego llega hasta la
7.ª división.

**Una liga bajo una liga.** Dos ligas no pueden estar bajo la misma liga (tres grupos regionales
bajo una segunda división, por ejemplo). La segunda sale en gris en la lista **Division**.

**Bajo una de las ligas del juego.** Tu liga nueva también puede ir bajo una liga que tiene el
juego: elige la liga del juego en **Division** (las que tienen un número entre paréntesis).
Entonces juega ascensos y descensos con ella.

**Sin NewLife.** En **Leagues**, pulsa tu liga de arriba y luego **Add lower tier**: se abre una
ventana **League** con el país, los clubes, el formato y la división ya rellenados. Dale un
**Name** y pulsa **OK**.

---

## Paso 8. La página New clubs: nombres, escudos, equipaciones, clubes del juego

1. Barra de la izquierda: pulsa **New clubs** (o **Clubs and names** en la página Leagues).
2. Arriba, **League**: elige una de tus ligas.

**Deberías ver:** sus clubes con las columnas **#**, **Name**, **Short name**, **Team ID** (*ID
del club*) (`at Build` hasta el primer Build), **Crest** y **Players changed** (*Jugadores
cambiados*). Los clubes de NewLife ya tienen sus nombres, nombres cortos y escudos. Un club sin
nombre muestra `<league> 01`, `<league> 02` ... en gris.

### Nombre, escudo, equipaciones, entrenador

1. Haz doble clic en un club (o selecciónalo y pulsa **Edit club**).

**Deberías ver:** una ventana llamada **Club** con:

| Campo | Qué hacer |
|---|---|
| **Name** | El nombre del club. Las letras con tildes y signos (Željezničar) están bien. |
| **Short name** | Tres letras o cifras. Vacío = se hace a partir del nombre. Č, Ž, Đ ... pasan a C, Z, D, como en el juego. |
| **Crest** | **Pick picture...** un PNG o JPG. **Clear** lo quita. Un club sin escudo recibe una insignia numerada. |
| **Home stadium** (*Estadio local*) | Solo cuando Stadium Server está instalado: **Choose stadium...** (*Elegir estadio...*) de tu paquete de estadios, o **Game's own** (*Del juego*). |
| **Manager** (*Entrenador*) | El nombre del entrenador. Vacío: un nombre inventado a partir de jugadores del país del club. |
| **Manager picture** (*Foto del entrenador*) | Un PNG o JPG; el juego lo muestra en Edit mode y en la Liga Máster. |
| **Formation** | `As the league (...)` mantiene la formación de la liga; o elige una para este club. |
| **Home kit colours** (*Colores de la equipación local*), **Away kit colours** (*Colores de la equipación visitante*) | Pulsa los dos cuadrados de color (camiseta, segundo color) para elegir colores; **None** (*Ninguno*) = Build elige una equipación por sí solo. Build da al club la equipación del juego más parecida a estos colores. |

2. Pulsa **OK**.

**Deberías ver:** el nombre y el escudo nuevos en la lista.

**Equipaciones.** Un club nuevo toma prestada una equipación de un club del juego en sus colores.
Dos opciones de la página **Build** cambian eso: **Make kits for the new clubs** (*Crear
equipaciones para los clubes nuevos*) (activada por defecto, necesita Kit Server instalado: cada
club nuevo recibe equipaciones local, visitante, tercera y de portero hechas en sus colores, con
su escudo) y **Kits you can edit in the game** (*Equipaciones que puedes editar en el juego*)
(cada club nuevo lleva una equipación lisa que puedes cambiar en el Edit mode del juego).
[Más en la guía completa](mod-studio-guide.md#8-league-builder-ligas-clubes-y-jugadores-nuevos).

**Muchos clubes a la vez.** **More ▾** tiene **Paste names...** y **Load names from file...** (un
nombre por línea, en orden) e **Import crests...** (*Importar escudos...*) (una carpeta de
imágenes, emparejadas con los clubes por el nombre de archivo). También tiene **Insert club**
(*Insertar club*), **Remove club** (*Quitar club*), **New club here** (*Club nuevo aquí*) y
**Move to another league...** (*Mover a otra liga...*).

### Clubes que el juego ya tiene

Una liga de NewLife puede incluir clubes que el juego ya tiene. Salen en la lista con el nombre
del juego, su **Team ID** y `(the game's)` en **Crest**. Si la línea verde del Paso 5 decía que
*también juegan en una competición del juego* (*also play in a competition of the game*), haz
esto para **cada** uno de ellos:

1. Pulsa el club en la lista.
2. Pulsa **Club of the game...** (*Club del juego...*).

**Deberías ver:** una ventana llamada **Club of the game** (*Club del juego*), con el club
seleccionado y bajo la lista una línea como `<club> plays in <competitions>. Every one of those
competitions keeps its number of clubs: pick who takes its place there.`

3. Elige quién ocupa su sitio antiguo:
   - **Its place goes to a club of the game that plays in nothing:** (*Su lugar pasa a un club
     del juego que no juega nada:*) y elige un club de la lista de debajo; o
   - **Its place goes to a new club, named:** (*Su lugar pasa a un club nuevo, llamado:*) y
     escribe un nombre. Build crea ese club.
4. Si el club juega una competición continental (Champions League, Libertadores ...), también
   está **It keeps its places in continental competitions** (*Conserva sus plazas en
   competiciones continentales*). Marcado, sigue jugando esa competición y nadie tiene que
   ocupar su sitio allí.
5. Pulsa **OK**.

El mismo botón pone cualquier club del juego en un sitio de tu liga: selecciona el sitio,
**Club of the game...**, busca por nombre, nombre corto o team ID (**Only clubs in no league**
(*Solo clubes sin liga*) acota la lista). **New club here** (en **More ▾**) devuelve el sitio a
un club nuevo.

**NewLife club...** pone clubes de NewLife, con sus plantillas, en el sitio seleccionado y los
sitios siguientes: marca uno o más en la ventana que se abre y luego **OK**. Así es como una
liga que hiciste a mano recibe clubes reales.

## Paso 9. La página Players

Los clubes de NewLife vienen con plantillas completas, así que no tienes que tocar esta página.
Está ahí por si quieres cambiar una plantilla.

1. Barra de la izquierda: pulsa **Players** (o selecciona un club en New clubs y pulsa
   **Players**).
2. Arriba, elige la **League** y el **Club**. (O escribe en *Find a club...* (*Buscar un
   club...*).)

**Deberías ver:** la plantilla con las columnas **Order** (*Orden*), **No.** (*N.º*), **Name**,
**Pos** (*Pos.*), **Age** (*Edad*), **Rating** (*Valoración*), **Foot** (*Pie*), **Changed** y
**Player ID** (*ID del jugador*), y el once inicial en un campo debajo. Pulsa un jugador: la
parte derecha lo muestra, en las pestañas **Basics** (*Lo básico*), **Positions**
(*Posiciones*), **Abilities** (*Capacidades*) y **Skills** (*Habilidades*).

- Cambia un nombre, dorsal, posición, valoración o capacidad a la derecha. El cambio se guarda
  al momento.
- **Order up** (*Subir en el orden*) / **Order down** (*Bajar en el orden*): el orden de la
  plantilla. Los once primeros empiezan el partido. O arrastra un jugador a un sitio del campo.
  **Best eleven** (*Mejor once*) pone al jugador más fuerte en cada sitio.
- **Sign players...** (*Fichar jugadores...*) trae jugadores de otros clubes; **Transfer to...**
  (*Traspasar a...*) manda al jugador seleccionado a otro club.
- **Undo changes to this player** (*Deshacer los cambios de este jugador*) y **Undo all changes
  of this club** (*Deshacer todos los cambios de este club*) vuelven atrás.

Todo lo de esta página está en [Jugadores en la guía completa](mod-studio-guide.md#jugadores).

---

## Paso 10. Límites que detienen el Build

| Límite | Dónde lo ves |
|---|---|
| Clubes nuevos en total: el número de la línea `New clubs in the recipe: X of the Y the game takes.` | Página NewLife Database: **Add to the recipe** se queda en gris. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| De 10 a 24 clubes en una liga | NewLife Database: liga gris, `a league takes 10 to 24 clubs`. New clubs: `A league has 10 to 24 clubs.` |
| Ligas nuevas por mundo (39 en nuestras pruebas) | Build: `error: <n> leagues, but the game has room for <m> ...` |
| Una liga bajo una liga | Lista **Division**: gris. Build: `... are all under ...; the game follows one link down from a league ...` |
| Divisiones hasta la 7.ª | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 ligas divididas por mundo; una liga dividida o de Apertura/Clausura por país | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Un club en una sola liga | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Un club del juego que juega en algún sitio necesita un sustituto | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Haz [Clubes que el juego ya tiene](#clubes-que-el-juego-ya-tiene). |

Todos los números: [8.3 Límites](mod-studio-guide.md#83-límites).

## Paso 11. Guarda la receta

1. Barra de arriba: **File → Save recipe** (*Archivo → Save recipe*).
2. La primera vez se abre una ventana **Save recipe as...**. Propone el nombre del mundo, por
   ejemplo `_FL26MyWorld.json`. Elige una carpeta que vuelvas a encontrar (por ejemplo
   `Documents\FL26 Mod Studio\recipes`) y pulsa **Save** (*Guardar*).

**Deberías ver:** abajo de la ventana, `Recipe saved: <file>`.

Después de eso, **File → Save recipe** guarda en el mismo archivo sin preguntar. **File → Save
recipe as...** guarda una copia con otro nombre. **File → Open recipe...** vuelve a abrir una
receta guardada (avisa si tienes cambios sin guardar). **File → New recipe** (*Archivo → Receta
nueva*) empieza una vacía.

Build también guarda por su cuenta una copia de la receta, y Mod Studio abre la última receta al
arrancar, así que lo que construiste nunca se pierde. Guarda de todos modos: tu propio archivo es
el que puedes encontrar y copiar.

## Paso 12. Build

1. Barra de la izquierda: pulsa **Build**.

**Deberías ver:** el botón azul grande **Build and install** (*Construir e instalar*), la fila
**0. Install the modules**, **1. Check the plan**, **2. Build the world**, **3. Switch it on**,
**4. After a start: check** y **Export the world...** (*Exportar el mundo...*), dos tarjetas
(**European cups** (*Copas europeas*) y **New clubs**) con opciones, una línea como
`World _FL26MyWorld: not built yet · builder modules: installed`, y un cuadro para el registro
abajo.

2. Pulsa primero **1. Check the plan**. No cambia nada; solo lee tu receta.

**Deberías ver:** en el cuadro, una línea `world _FL26MyWorld: 2 new leagues, ...` y una línea
por liga con sus clubes, división y formato (`18 clubs x2` son 18 clubes, todos contra todos dos
veces; `division 2  below ... (3 up/down)` es una segunda división), y sus
`European places:`. Una línea que empieza por `error:` dice qué arreglar primero; mira la tabla
del final.

3. Pulsa **Build and install**. Pregunta `Build _FL26MyWorld and make it the live world? ...`:
   pulsa **Yes**.

   Si las tablas del juego son más antiguas que el juego, pregunta primero si las desempaqueta
   otra vez: pulsa **Yes** (un minuto, más o menos).

   Instala los módulos, construye el mundo y lo activa, todo de una vez. Tarda de unos segundos
   a unos minutos.

**Deberías ver:** una ventana **Build finished** (*Construcción terminada*) con una marca en cada
línea: **World built** (*Mundo construido*), **Leagues and clubs** (*Ligas y clubes*)
(`2 leagues · 36 new clubs`), **Modules installed and switched on** (*Módulos instalados y
activados*), **Switched on in sider.ini** (*Activado en sider.ini*) y **Start the game to play
it** (*Inicia el juego para jugarlo*). En **Before you play** (*Antes de jugar*):
`Start a new Master League career: a career saved before keeps the old world.` Pulsa **Done**
(*Hecho*).

Si dice **An Edit save from before this Build is in the game's save folder**: pulsa **Move
the Edit save aside** (*Apartar el guardado de Edit*). Un guardado de Edit antiguo esconde los
nombres y las plantillas nuevos.

**Paso a paso en lugar del botón grande** (el mismo resultado):

1. **1. Check the plan**: como arriba.
2. **2. Build the world**: lo construye. Si el mundo existe, pregunta `... exists. Build it again?`:
   **Yes**. El registro termina con `Next: 3. Switch it on, then start the game.`
3. **3. Switch it on**: pregunta `Make _FL26MyWorld the live world in sider.ini?`: **Yes**. El
   registro termina con `Start the game, then 4. check.`

**Qué significan las líneas del registro:**

| Línea | Significado |
|---|---|
| `installing the modules ...`, `modules: ... copied, ... already there` | Se ponen en su sitio los módulos de Mod Studio. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | El resumen de tu receta. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Una liga: sus ids en el juego, su división y su formato. |
| `European places: 1st Champions League qualifying, ...` | Adónde van sus mejores clubes. |
| `no European places: the new leagues send nobody to Europe` | Un aviso, no un error: ajusta **Europe** en una primera división si lo quieres. |
| `building ...` | Se está escribiendo el mundo. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | El mundo está activado. |
| `error: ...` | Build se paró y no cambió nada en el juego. Arregla lo que dice (tabla del final) y vuelve a construir. |

Las opciones de las tarjetas (**Include the Conference League** (*Incluir la Liga
Conferencia*), **Country cup draw** (*Sorteo de la copa nacional*), **Make kits for the new
clubs** ...) se explican en [8.2](mod-studio-guide.md#82-construir-activar-jugar). Los valores
por defecto están bien.

## Paso 13. Juega: una Liga Máster NUEVA y luego la comprobación

1. Pulsa el botón verde **Play** (*Jugar*) arriba a la derecha (o **Game → Start the game**
   (*Juego → Iniciar el juego*)).
2. En el juego: **Master League** → **New game**. No Continue: una carrera guardada antes
   conserva el mundo antiguo.
3. En **Select Team**, desplázate: tus ligas están en la lista, bajo sus países.
4. Elige un club y juega.

Luego deja que Mod Studio compruebe que el juego tomó el mundo:

1. Cierra el juego (o al menos inícialo una vez hasta el menú principal).
2. En Mod Studio: **Build** → **4. After a start: check**.

**Deberías ver:** una línea por módulo que dice cuántas ligas leyó del archivo de mundo, y al
final `the world works as built`. Una línea `not loaded` o `did NOT read the world file`, y al
final `something is wrong -- see the lines above`, significan que algo no funcionó: mira la tabla
del final.

## Paso 14. Cambiar algo más tarde

1. Cierra el juego.
2. Abre Mod Studio. Abre tu última receta por sí solo (o **File → Open recipe...**).
3. Cambia lo que quieras en **NewLife Database**, **Leagues**, **New clubs** o **Players**.
4. **File → Save recipe**.
5. **Build** → **Build and install** → **Yes**.

**¿Necesitas una carrera nueva?** Sí: empieza una Liga Máster nueva después de cada cambio que
construyas. Una carrera toma su propia copia de las ligas, los clubes y las plantillas cuando
empieza, así que una carrera en la que ya estás conserva los antiguos. Y una carrera guardada con
un mundo necesita ese mismo mundo para cargarse, así que mantén el mundo activado mientras la
juegas.

**Una versión más nueva de NewLife.** Pon sus partes en una carpeta nueva, abre esa carpeta con
**Open NewLife Database...** y luego pulsa **Update my leagues to this version** (*Actualizar
mis ligas a esta versión*). Cada liga conserva su nombre, división, formato, plazas europeas y
copas; los clubes y las plantillas vienen de la versión nueva (la casilla **Keep my clubs**
(*Mantener mis clubes*) conserva tu propia composición). Vuelve a construir y empieza una
carrera nueva.
[Más](mod-studio-guide.md#84-newlife-database-clubes-y-jugadores-reales).

**Quitar una liga.** **Leagues** → **Ours** → púlsala → **Remove** → **Yes**. Sus clubes y los
cambios de sus jugadores se van con ella.

## Paso 15. Compartir lo que has hecho

Hay dos maneras. Elige una:

| | Paquete de ligas (`.fl26pack`) | Mundo exportado (`.zip`) |
|---|---|---|
| Qué lleva | Tus ligas como receta: clubes, nombres, escudos, logos, plantillas, caras y, si quieres, equipaciones y marcadores. | El mundo exactamente como lo construiste. |
| La otra persona | Lo añade a su propia receta y construye, así que funciona junto a sus propias ligas y otros paquetes. | Lo instala y juega. No hay nada que construir, pero sustituye a cualquier otro mundo que tenga activado. |
| Cómo lo instala | [Camino C de Instalar un paquete listo](install-a-pack.md#camino-c-un-paquete-de-ligas-fl26pack) | [Camino A de Instalar un paquete listo](install-a-pack.md#camino-a-un-mundo-listo-un-zip) |

### Un paquete de ligas

1. Barra de la izquierda: **League packages** (*Paquetes de ligas*) → **Make a package...**
   (*Crear un paquete...*) (o barra de arriba: **File → Make a league package...** (*Archivo →
   Crear un paquete de ligas...*)).

**Deberías ver:** una ventana **Make a league package** (*Crear un paquete de ligas*).

2. Rellena **Name** (obligatorio), **Author** (*Autor*), **Version** (*Versión*) (`1.0` para
   empezar) y **Description** (*Descripción*).
3. En **Leagues**, marca las ligas que van dentro (**Select all** (*Seleccionar todo*) /
   **Select none** (*No seleccionar ninguno*)). Una liga que está debajo de otra liga debe ir
   con ella.
4. **Also my changes to the game's own leagues, clubs and players** (solo si cambiaste alguno):
   márcalo para meterlos también.
5. En **What goes in** (*Qué va dentro*), todo está marcado: **Squads**, **Player faces and
   portraits** (*Caras y retratos de jugadores*), **Crests and league logos** (*Escudos y logos
   de ligas*), **Managers** (*Entrenadores*), **Kit colours** (*Colores de las equipaciones*),
   **Kits** (*Equipaciones*), **Scoreboards** (*Marcadores*) y **Home stadiums** (*Estadios
   locales*). Desmarca lo que no quieras compartir. Las equipaciones suman unos 10 MB por liga y
   un marcador unos 7 MB.
6. Pulsa **Save the package...** (*Guardar el paquete...*). Se abre una ventana para guardar,
   **Save the package** (*Guardar el paquete*), con un nombre como `<name>-1.0.fl26pack`. Elige
   una carpeta que vuelvas a encontrar (Escritorio, Documentos ...) y pulsa **Save**.

**Deberías ver:** `Saved <file>` con cuántas ligas, clubes y caras lleva. Ese único archivo es lo
que compartes. Si pasa de 10 MB, Mod Studio lo dice: Discord no lo acepta, así que compártelo por
Google Drive, Dropbox, MEGA o similar, o desmarca **Kits** y **Scoreboards**, o haz un paquete
por liga.

Más: [9. Paquetes de ligas](mod-studio-guide.md#9-paquetes-de-ligas-comparte-una-liga-entera).

### Un mundo entero (zip)

1. Construye primero (Paso 12). El mundo tiene que estar construido.
2. Barra de la izquierda: **Build** → **Export the world...**.
3. Se abre una ventana para guardar con el nombre del mundo como nombre de archivo
   (`_FL26MyWorld.zip`), en tu carpeta de usuario la primera vez (después, en la última carpeta
   que usaste). Elige una carpeta y pulsa **Save**.

**Deberías ver:** al cabo de un momento, `Saved <file>` y cuántos jugadores nuevos reciben una
cara generada. El zip lleva la carpeta del mundo, su archivo de mundo y un léeme.

Quien lo instala necesita los módulos de Mod Studio con el paquete de caras (**Build → 0. Install
the modules**); sin ellos todos los jugadores nuevos se ven iguales. El léeme del zip lo dice.

Más: [9.1 Export the world](../en/mod-studio-guide.md#91-export-the-world-a-built-world-for-another-pc)
(en inglés).

---

## Si algo sale mal

Los mensajes salen en una ventana de error, en la línea verde o roja bajo el título de una
página, o en el registro de Build después de `error:`. `<...>` representa un nombre o un número.

| Lo que ves | Qué hacer |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Elegiste la carpeta equivocada, o descomprimiste las partes. Abre la carpeta que contiene los propios archivos `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Hay dos versiones de NewLife mezcladas. Deja en la carpeta solo las partes de una versión. |
| `<file> is not a NewLife part (...) -- download it again` | La descarga se estropeó. Vuelve a descargar esa parte. |
| Una liga gris, `a league takes 10 to 24 clubs` | Añade o deja fuera clubes (Paso 4) hasta que tenga de 10 a 24. |
| Una liga gris, `the game's own league: Bring the game's leagues to this season` | El juego ya la tiene. Usa **Bring the game's leagues to this season...**. |
| **Add to the recipe** se queda en gris | No hay nada añadible seleccionado, o la selección pasaría el límite de clubes nuevos (la línea de abajo). |
| `<club> would play in two leagues (<league> and <league>).` | Desmarca el club en una de ellas. |
| `<league> has no country the game knows.` | Esta liga no se puede añadir. |
| `A league needs a name and a country.` / `Pick the country from the list.` | En **Edit league...**, rellena **Name** y elige el **Country** de la lista en lugar de escribirlo entero. |
| `There is already a league called <name>.` | Dale otro nombre a la liga. |
| `European places: position <n> -- the league has <m> clubs` | Una fila de **Europe** apunta más allá del último club. Cámbiala o quítala. |
| `European places: position <n> is listed twice` | Dos filas tienen el mismo puesto. Quita una. |
| `European places: a cup winner's place, but the country has no cup` | Marca **National cup**, o quita la fila **Cup winner**. |
| `Clubs, times and groups must be numbers.` | En **splits in two**, escribe los grupos como números, por ejemplo `6/6`. |
| `A league playing February to December has no split, Apertura/Clausura, national cup or league cup yet.` | Pon **Season** en **August to May**, o quita la división en grupos, el Apertura/Clausura o las copas. |
| `This division plays February to December with the league above it, and a league playing February to December has no split or Apertura/Clausura yet.` | Dale a esta división **everyone plays everyone**. |
| `Clubs in no league are all new clubs: take the clubs of the game out first (Edit club).` | La liga tiene clubes del juego. En **New clubs** selecciona cada uno y usa **More ▾ → New club here**, luego vuelve a ajustar **Clubs in no league**. |
| `<league> is below this league; clubs in no league have none.` (o `an exhibition league has none.`) | Otra liga tiene esta como su **Division**. Cambia primero esa liga. |
| `A league has 10 to 24 clubs.` (New clubs) | Insert club / Remove club dejaría la liga fuera de 10 a 24. |
| `Open the NewLife Database on the NewLife page first.` | **NewLife club...** necesita la carpeta de NewLife: ábrela una vez en **NewLife Database**. |
| `Pick the club that takes its place.` / `Give the new club a name.` / `A club cannot take its own place.` | En **Club of the game**, elige un club sustituto, o escribe un nombre para el nuevo. |
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables** (*Ajustes → Desempaquetar las tablas del juego*). |
| `error: no game folder -- Game > Choose the game folder` | **Game → Choose the game folder...** (*Juego → Elegir la carpeta del juego...*). |
| `error: the world name must start with _FL26` | **Leagues → More ▾ → World name and recipe...**: un nombre que empiece por `_FL26`. |
| `error: nothing to build: add a league or change one of the game's ...` | La receta está vacía. Añade ligas (pasos 3 a 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Haz [Clubes que el juego ya tiene](#clubes-que-el-juego-ya-tiene) para ese club. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | La misma ventana: escribe un nombre junto a **Its place goes to a new club, named:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Saca el club de una liga (**New club here** en New clubs, o desmárcalo antes de añadir). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Demasiados clubes nuevos. Quita una liga, o clubes. |
| `error: <n> leagues, but the game has room for <m> ...` | Demasiadas ligas nuevas. Quita algunas. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Solo puede haber una liga bajo una liga. Cambia la **Division** de las demás. |
| `error: <league>: division 8 -- the rank field stops at 7` | Un país llega como mucho a la 7.ª división. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Dale a las demás ligas **everyone plays everyone**. |
| `The game's tables Mod Studio uses are older than the game: ... Unpack them again first?` | Pulsa **Yes**. |
| `<world> is not built yet: 2. Build the world first.` (Export the world) | Construye primero, luego exporta. |
| `Give the package a name.` / `Tick at least one league.` / `The recipe has no leagues yet.` | En **Make a league package**, rellena **Name** y marca una liga; antes la receta necesita ligas. |
| No hay ligas nuevas en Select Team | Empieza una Liga Máster **nueva**. Luego **Build → 4. After a start: check**. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Inicia el juego hasta su menú principal, ciérralo y vuelve a comprobar. |
| `<module> not loaded` / `did NOT read the world file` | **Build → 0. Install the modules**, luego **3. Switch it on**, vuelve a iniciar el juego y vuelve a comprobar. Si sigue mal: pregunta en Discord. |
| Los nombres de los clubes son los del juego, no los tuyos | Un guardado de Edit antiguo los esconde: **Move the Edit save aside** en la ventana **Build finished**, o saca `EDIT00000000` de la carpeta de guardado del juego. |
| Todos los jugadores nuevos tienen la misma cara | **Build → 0. Install the modules** (trae el paquete de caras) y vuelve a iniciar el juego. |

**Para pedir ayuda:** en el [Discord](https://discord.gg/StQqtk3G3M), manda una captura de lo que
ves, el texto del registro de Build y tu `sider.log` (**Game → Open sider.log** (*Juego → Abrir
sider.log*)).
