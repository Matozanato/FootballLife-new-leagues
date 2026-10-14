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

Los pasos 1 a 3 son iguales para todos y se hacen una sola vez. Luego elige el camino que
corresponde al archivo que te dieron:

- **Camino A: un mundo listo**, como un solo `.zip` (un modpack, el mundo de un amigo). El camino
  más rápido: no hay nada que construir.
- **Camino C: un paquete de ligas**, un archivo `.fl26pack` que alguien hizo. Mod Studio lo
  construye por ti.

¿Nadie te dio nada y quieres elegir ligas reales tú mismo (de la NewLife Database) o crear las
tuyas? Eso es la otra guía:
[Crear tus propias ligas y paquetes](make-your-own-leagues.md). Haz primero aquí los pasos 1 a 3.

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
derecha. A la izquierda: **Home** (*Inicio*), luego **YOUR WORLD** (*TU MUNDO*: **Build and
edit your world** (*Construye y edita tu mundo*), **Import your world** (*Importa tu mundo*),
**NewLife Database**), **GAME CONTENT** (*CONTENIDO DEL JUEGO*), **TOOLS** (*HERRAMIENTAS*) y,
abajo del todo, **Settings** (*Ajustes*).

Si Windows dice "Windows protected your PC": pulsa **More info** → **Run anyway**.

¿Quieres la ventana en otro idioma? Barra de arriba → **Language** → Hrvatski, Español o Français.

## Paso 3. Dile dónde está tu juego

1. Barra de la izquierda, abajo del todo: pulsa **Settings** (*Ajustes*).
2. Junto a la carpeta del juego, pulsa **Browse...** (*Examinar...*).
3. Elige la carpeta que contiene `FL_2026.exe` (por ejemplo `C:\Football Life 2026`). No
   `SiderAddons`, no una subcarpeta: la carpeta que tiene `FL_2026.exe` dentro.
4. Pulsa **Use this folder** (*Usar esta carpeta*).

**Deberías ver:** debajo de la carpeta, una línea que dice que se encontró `SiderAddons\sider.ini`.

(Lo mismo está en la barra de arriba: **Game → Choose the game folder...**
(*Juego → Elegir la carpeta del juego...*).)

No hay nada más que preparar. En cuanto sabe dónde está tu juego, Mod Studio desempaqueta él
solo las tablas del juego (su lista de clubes, ligas y jugadores), solo la primera vez. Los
módulos de Mod Studio entran con **Install the world** (*Instalar el mundo*, camino A) o con
**Build and install** (*Construir e instalar*, camino C). Las ligas nuevas solo funcionan con
estos módulos, y traen el paquete de caras que da su cara a los jugadores nuevos. Si **Home**
dice alguna vez que faltan o son antiguos, pulsa allí **Install now** (*Instalar ahora*).

Ahora elige el camino que corresponde a tu archivo.

---

## Camino A: un mundo listo (un .zip)

Úsalo cuando alguien te dio un mundo como zip (un modpack, un mundo exportado).

**A1.** No lo descomprimas tú.

**A2.** Barra de la izquierda, en **YOUR WORLD**: pulsa **Import your world** (*Importa tu mundo*).

**A3.** Pulsa **Choose a file...** (*Elegir un archivo...*) y elige el zip. (O arrastra el zip a
esa página.)

**A4. Deberías ver:** una línea que dice qué es, por ejemplo `a ready world to play
(_FL26Modpack)` (*un mundo listo para jugar*), o `a newer version of the world _FL26Modpack you
have` (*una versión más nueva del mundo que ya tienes*) si tienes una anterior, y debajo cuántas
ligas trae. Las partes (el mundo, equipaciones, marcadores ...) están bajo **More options: which
parts, name, order of the content folders, map lines** (*Más opciones: qué partes, nombre, orden
de las carpetas de contenido, líneas de los map*), todas marcadas. Déjalas así. (Para instalarlo
sin las equipaciones, desmárcalas ahí.)

**A5.** Pulsa **Install the world** (*Instalar el mundo*). Si ya hay instalada una versión anterior
del mismo mundo (un Modpack anterior), pregunta si la reemplaza: di **Yes**. La anterior se quita
primero, así no queda nada de ella; tus partidas guardadas no se tocan. Espera hasta que diga que
ha terminado. Mod Studio instala sus módulos (los de esta versión), copia el mundo, pone su
archivo de mundo donde lo leen los módulos y pone el mundo en el juego.

**Deberías ver:** `✓ Ready to play: press Play and start a new Master League` (*Listo para jugar:
pulsa Play y empieza una Master League nueva*) y una ventana **Ready to play** (*Listo para
jugar*) con una lista de marcas (el mundo, los módulos, el paquete de caras ...). Si en cambio dice
**Almost ready** (*Casi listo*), te dice qué arreglar.

Un mundo listo no necesita Build: ya está construido. Mientras está en el juego, los pasos de
Build están apagados (0.2.4). Para construir ligas propias más tarde, pon primero tu propio mundo
en el juego (**Home → Switch world...** (*Inicio → Cambiar de mundo...*)). Ve al
[Paso 4](#paso-4-inicia-el-juego).

---

## Camino B: construye tus propias ligas

Elegir ligas reales de la NewLife Database, o crear ligas propias, tiene su propia guía, con cada
campo explicado:
[Crear tus propias ligas y paquetes](make-your-own-leagues.md).

---

## Camino C: un paquete de ligas (.fl26pack)

**C1.** Barra de la izquierda, en **YOUR WORLD**: pulsa **Build and edit your world** (*Construye
y edita tu mundo*) y luego la pestaña **League packages** (*Paquetes de ligas*).

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

**Deberías ver:** una línea verde bajo el título de la página: "Added ... Build and install puts
its leagues in the game." (*Agregado ... Construir e instalar pone sus ligas en el juego.*)

No hay nada que guardar: tu mundo se guarda solo un momento después de cada cambio (la barra de
abajo dice **Your world is saved**, *Tu mundo está guardado*).

**C4.** Pestaña **Build** (junto a **League packages**) → el botón azul grande **Build and
install** (*Construir e instalar*) → **Yes**.

Pone los módulos de Mod Studio, construye tu mundo y lo pone en el juego, todo de una vez. Tarda
de unos segundos a unos minutos.

(Soltar el `.fl26pack` en **Import your world** hace lo mismo: después de la ventana de C3 el
paquete entra en tu mundo y **Build and install** empieza solo.)

**Deberías ver:** una ventana **Build finished** (*Construcción terminada*) con marcas (World
built, Leagues and clubs, Modules installed and switched on, In the game). Pulsa **Done**
(*Hecho*). En el cuadro de abajo de la página Build no hay ninguna línea que empiece por
`error:`.

---

## Paso 4. Inicia el juego

Pulsa el botón verde **Play** arriba a la derecha (o **Game → Start the game** (*Juego → Iniciar
el juego*)). Espera al menú del juego.

## Paso 5. Empieza una Liga Máster NUEVA

1. **Master League** → **New game** (no Continue: una carrera antigua no recibe las ligas nuevas).
2. En **Select Team**, desplázate: las ligas nuevas están en la lista, bajo sus países.
3. Elige un club y juega.

Las ligas nuevas también están en **Kick Off** → League, y en **Database → Competition Info**.

## Paso 6. Deja que Mod Studio compruebe que funcionó

1. Cierra el juego.
2. En Mod Studio: **Build and edit your world** → pestaña **Build** → **Step by step, and Export
   the world** (*Paso a paso, y Exportar el mundo*) → **4. After a start: check**.

**Deberías ver:** una línea por módulo que dice cuántas ligas leyó del mundo, y al final
`the world works as built`. Una línea que dice `not loaded` o `did NOT read the world file`, y la
última línea `something is wrong -- see the lines above`, te dicen qué está mal.

---

## Si algo sale mal

| Lo que ves | Qué hacer |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables** (*Ajustes → Desempaquetar las tablas del juego*). |
| No hay ligas nuevas en Select Team | ¿Empezaste una Liga Máster **nueva**? Luego **4. After a start: check** ([Paso 6](#paso-6-deja-que-mod-studio-compruebe-que-funcionó)). Si su registro dice `world file -- 0 leagues`, tu mundo estaba vacío: vuelve a añadir el paquete (Camino C) y vuelve a construir. |
| El mundo dice que se construyó con `0 leagues, 0 clubs` | Lo mismo: tu mundo no tenía ligas. Añade algunas primero y luego Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | La comprobación se hizo antes de iniciar el juego. Inícialo hasta el menú principal, ciérralo y vuelve a pulsar **4. After a start: check**. |
| Todos los jugadores nuevos tienen la misma cara | **Home → Install now** (*Inicio → Instalar ahora*, cuando Home dice que los módulos faltan o son antiguos), o **Build and edit your world → Build → Step by step, and Export the world → 0. Install the modules**: trae el paquete de caras. Luego vuelve a iniciar el juego. |
| El juego se cierra al arrancar | Inícialo otra vez por el launcher (un cierre en los primeros 10 segundos también pasa sin mods). Si sigue cerrándose: **Game → Start the game without mods (safe mode)...** (*Juego → Iniciar el juego sin mods (modo seguro)...*) y pregunta en Discord. |
| Quieres todo como estaba | **Import your world** → selecciónalo en **In the game now** (*En el juego ahora*) → **Remove** (*Quitar*) saca un mundo instalado. **TOOLS → Restore points → Put Sider back as before Mod Studio...** (*HERRAMIENTAS → Puntos de restauración → Devolver Sider a antes de Mod Studio...*, también en el menú **Game**) devuelve cada archivo que Mod Studio cambió y quita lo que trajo. No se borra nada: queda guardado en `SiderAddons\ModStudio\reset-<time>`, y **Undo the last reset** (*Deshacer el último reinicio*) lo vuelve a poner. |

**Para pedir ayuda:** en el [Discord](https://discord.gg/StQqtk3G3M), manda una captura de lo que
ves y tu `sider.log` (**Game → Open sider.log** (*Juego → Abrir sider.log*), o
`SiderAddons\sider.log` en la carpeta del juego).
