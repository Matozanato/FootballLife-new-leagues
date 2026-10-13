# Instalar un paquete listo: cada clic, en orden

> [English](../en/install-a-pack.md) · [hrvatski](../hr/install-a-pack.md) · **español** · [português](../pt/install-a-pack.md)

> La otra guía paso a paso: [Crear tus propias ligas y paquetes](make-your-own-leagues.md)
> · cada página explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · preguntas: [faq.md](../../docs/faq.md) (en inglés) · ayuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta guía escribe los nombres de los botones en inglés, tal como salen en la ventana, con el nombre
español entre paréntesis la primera vez. La ventana se puede pasar a español con
**Language** (*Idioma*) → Español.

Esta página es para quien nunca ha abierto Mod Studio y ha recibido algo listo para jugar: un
mundo, un modpack o un paquete de ligas. No explica cómo funciona nada. Solo dice qué pulsar, en
qué orden y qué deberías ver después de cada paso. Haz los pasos en orden y no te saltes
ninguno. Si ves algo distinto de lo que dice un paso, para ahí y ve a
[Si algo sale mal](#si-algo-sale-mal).

Los pasos 1 a 5 son iguales para todos y se hacen una sola vez. Luego elige el camino que
corresponde al archivo que te dieron:

- **Camino A: un mundo listo**, como un solo `.zip` (un modpack, el mundo de un amigo). El camino
  más rápido: no hay nada que construir.
- **Camino C: un paquete de ligas**, un archivo `.fl26pack` que alguien hizo. Mod Studio lo
  construye por ti.

¿Nadie te dio nada y quieres elegir ligas reales tú mismo (de la NewLife Database) o crear las
tuyas? Eso es la otra guía:
[Crear tus propias ligas y paquetes](make-your-own-leagues.md). Haz primero aquí los pasos 1 a 5.

---

## Paso 1. Cierra el juego

El juego tiene que estar cerrado mientras cambias cualquier cosa. Sider lee su configuración solo
cuando arranca el juego. Mira la barra de tareas: ninguna ventana de Football Life, ningún launcher.

## Paso 2. Descarga Mod Studio

1. Abre la [última versión](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. En **Assets**, pulsa `FL26ModStudio-<version>.zip` (por ejemplo `FL26ModStudio-0.2.1.zip`).
3. Clic derecho en el zip descargado → **Extract All...** → elige una carpeta, por ejemplo
   `Documents\FL26 Mod Studio` → **Extract**.

   No ejecutes el programa desde dentro del zip. No saques `FL26ModStudio.exe` de su carpeta:
   las carpetas `_internal` y `pack` que tiene al lado deben quedarse con él.

4. Abre esa carpeta y haz doble clic en `FL26ModStudio.exe`.

**Deberías ver:** una ventana oscura. Arriba: **File, Game, Profiles, Language, Help, Credits**
(*Archivo, Juego, Perfiles, Idioma, Ayuda, Créditos*) y un botón verde **Play** (*Jugar*) a la
derecha. A la izquierda: **Home**, y luego los grupos **LEAGUE BUILDER**, **GAME CONTENT**
(*CONTENIDO DEL JUEGO*) y **MANAGE** (*GESTIONAR*).

Si Windows dice "Windows protected your PC": pulsa **More info** → **Run anyway**.

¿Quieres la ventana en otro idioma? Barra de arriba → **Language** → Hrvatski, Español o Français.

## Paso 3. Dile dónde está tu juego

1. Barra de la izquierda, abajo, en **MANAGE**: pulsa **Settings** (*Ajustes*).
2. Junto a la carpeta del juego, pulsa **Browse...** (*Examinar...*).
3. Elige la carpeta que contiene `FL_2026.exe` (por ejemplo `C:\Football Life 2026`). No
   `SiderAddons`, no una subcarpeta: la carpeta que tiene `FL_2026.exe` dentro.
4. Pulsa **Use this folder** (*Usar esta carpeta*).

**Deberías ver:** debajo de la carpeta, una línea que dice que se encontró `SiderAddons\sider.ini`.

(Lo mismo está en la barra de arriba: **Game → Choose the game folder...**
(*Juego → Elegir la carpeta del juego...*).)

## Paso 4. Desempaqueta las tablas del juego

Todavía en **Settings**: pulsa **Unpack the game's tables** (*Desempaquetar las tablas del
juego*). Espera unos segundos.

**Deberías ver:** una línea que dice que las tablas se desempaquetaron.

Esto se hace una vez. Repítelo solo después de una actualización del juego; Mod Studio la nota y
te pregunta.

Si te saltas este paso, Build dirá más tarde `error: no game tables -- Settings > Unpack the game's tables`.

## Paso 5. Instala los módulos de Mod Studio

1. Barra de la izquierda, en **LEAGUE BUILDER**: pulsa **Build**.
2. Pulsa **0. Install the modules**. Pregunta si los copia: pulsa **Yes**.

**Deberías ver:** en el cuadro de abajo, los módulos listados como instalados.

Las ligas nuevas solo funcionan con estos módulos. También traen el paquete de caras que da su
cara a los jugadores nuevos. Esto se hace una vez, y otra vez después de cada versión nueva de
Mod Studio.

Ahora elige el camino que corresponde a tu archivo.

---

## Camino A: un mundo listo (un .zip)

Úsalo cuando alguien te dio un mundo como zip (un modpack, un mundo exportado).

**A1.** No lo descomprimas tú.

**A2.** Barra de la izquierda, en **MANAGE**: pulsa **Install mods** (*Instalar mods*).

**A3.** Pulsa **Choose a file...** (*Elegir un archivo...*) y elige el zip. (O arrastra el zip a
esa página.)

**A4. Deberías ver:** una lista de lo que hay dentro, por ejemplo el mundo (`_FL26Modpack` o
parecido, marcado como mundo de League Builder), equipaciones y marcadores. Todo está marcado.
Déjalo así.

**A5.** Pulsa **Install** (*Instalar*). Espera hasta que diga que ha terminado. Mod Studio copia
el mundo, pone su archivo de mundo donde lo leen los módulos y activa el mundo.

**A6.** Si pregunta si instala los módulos: di **Yes**.

**No** pulses Build para un mundo listo. Ya está construido. Ve al [Paso 6](#paso-6-inicia-el-juego).

---

## Camino B: construye tus propias ligas

Elegir ligas reales de la NewLife Database, o crear ligas propias, tiene su propia guía, con cada
campo explicado:
[Crear tus propias ligas y paquetes](make-your-own-leagues.md).

---

## Camino C: un paquete de ligas (.fl26pack)

**C1.** Barra de la izquierda, en **LEAGUE BUILDER**: pulsa **League packages** (*Paquetes de
ligas*).

**C2.** Pulsa **Add a package...** (*Añadir un paquete...*) y elige el archivo `.fl26pack`. (O
barra de arriba: **File → Add a league package...** (*Archivo → Añadir un paquete de ligas...*).)

**C3. Deberías ver:** una ventana **Add a league package** (*Añadir un paquete de ligas*) con lo
que hay dentro: su nombre, versión y autor, y luego sus ligas, cada una marcada. Un paquete con
varias ligas tiene **Select all** (*Seleccionar todo*) / **Select none** (*No seleccionar
ninguno*) encima de la lista: desmarca una liga que no quieras. En **What to take** (*Qué tomar*)
puedes desmarcar partes (por ejemplo **Scoreboards ...** (*Marcadores*)). Si no estás seguro,
deja todo marcado. Pulsa **OK**.

Si el paquete tiene una liga con un nombre que ya tienes, pregunta si la añade con un nombre
nuevo: pulsa **Yes**.

**Deberías ver:** una línea verde bajo el título de la página: "Added ... Save the recipe, then
Build to put the leagues in the game."

**C4.** Barra de arriba: **File → Save recipe**. La primera vez se abre una ventana para
guardar: ponle un nombre al archivo y pulsa **Save** (*Guardar*). (La receta es tu lista de
ligas. Guárdala para poder cambiarla más tarde.)

**C5.** Barra de la izquierda: **Build** → el botón azul grande **Build and install** (*Construir
e instalar*) → **Yes**.

Instala los módulos, construye el mundo y lo activa, todo de una vez. Tarda de unos segundos a
unos minutos.

**Deberías ver:** una ventana **Build finished** (*Construcción terminada*) con marcas (World
built, Leagues and clubs, Modules installed and switched on, Switched on in sider.ini). Pulsa
**Done** (*Hecho*). En el cuadro de abajo de la página Build no hay ninguna línea que empiece por
`error:`.

---

## Paso 6. Inicia el juego

Pulsa el botón verde **Play** arriba a la derecha (o **Game → Start the game** (*Juego → Iniciar
el juego*)). Espera al menú del juego.

## Paso 7. Empieza una Liga Máster NUEVA

1. **Master League** → **New game** (no Continue: una carrera antigua no recibe las ligas nuevas).
2. En **Select Team**, desplázate: las ligas nuevas están en la lista, bajo sus países.
3. Elige un club y juega.

Las ligas nuevas también están en **Kick Off** → League, y en **Database → Competition Info**.

## Paso 8. Deja que Mod Studio compruebe que funcionó

1. Cierra el juego.
2. En Mod Studio: **Build** → **4. After a start: check**.

**Deberías ver:** una línea por módulo que dice cuántas ligas leyó del mundo, y al final
`the world works as built`. Una línea que dice `not loaded` o `did NOT read the world file`, y la
última línea `something is wrong -- see the lines above`, te dicen qué está mal.

---

## Si algo sale mal

| Lo que ves | Qué hacer |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | Haz el [Paso 4](#paso-4-desempaqueta-las-tablas-del-juego). |
| No hay ligas nuevas en Select Team | ¿Empezaste una Liga Máster **nueva**? Luego **Build → 4. After a start: check**. Si su registro dice `world file -- 0 leagues`, la receta estaba vacía: vuelve a añadir el paquete (Camino C) y vuelve a construir. |
| El mundo dice que se construyó con `0 leagues, 0 clubs` | Lo mismo: la receta no tenía ligas. Añade algunas primero y luego Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | La comprobación se hizo antes de iniciar el juego. Inícialo hasta el menú principal, ciérralo y vuelve a pulsar **4. After a start: check**. |
| Todos los jugadores nuevos tienen la misma cara | **Build → 0. Install the modules** (trae el paquete de caras) y vuelve a iniciar el juego. |
| El juego se cierra al arrancar | Inícialo otra vez por el launcher (un cierre en los primeros 10 segundos también pasa sin mods). Si sigue cerrándose: **Game → Start the game without mods (safe mode)...** (*Juego → Iniciar el juego sin mods (modo seguro)...*) y pregunta en Discord. |
| Quieres todo como estaba | **MANAGE → Install mods → Remove the mod** (*GESTIONAR → Instalar mods → Quitar el mod*) para un mundo instalado; **MANAGE → Restore points** (*GESTIONAR → Puntos de restauración*) devuelve cualquier archivo que Mod Studio cambió. |

**Para pedir ayuda:** en el [Discord](https://discord.gg/StQqtk3G3M), manda una captura de lo que
ves y tu `sider.log` (**Game → Open sider.log** (*Juego → Abrir sider.log*), o
`SiderAddons\sider.log` en la carpeta del juego).
