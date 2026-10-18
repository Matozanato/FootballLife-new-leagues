# Instalar un paquete listo: cada clic, en orden

> [English](../en/install-a-pack.md) · [hrvatski](../hr/install-a-pack.md) · **español** · [português](../pt/install-a-pack.md) · [français](../fr/install-a-pack.md)

> La otra guía paso a paso: [Crear tus propias ligas y paquetes](make-your-own-leagues.md)
> · cada página explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · preguntas: [faq.md](../../docs/faq.md) (en inglés) · ayuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta guía usa los nombres de los botones en español. La ventana arranca en inglés: pásala a
español con **Idioma (Language)** → Español (Paso 2). Hasta entonces los botones salen en inglés.

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
2. En **Assets**, pulsa `FL26ModStudio-<version>.zip` (por ejemplo `FL26ModStudio-0.2.4.zip`).
3. Clic derecho en el zip descargado → **Extraer todo...** → elige una carpeta, por ejemplo
   `Documents\FL26 Mod Studio` → **Extraer**.

   No ejecutes el programa desde dentro del zip. No saques `FL26ModStudio.exe` de su carpeta:
   las carpetas `_internal` y `pack` que tiene al lado deben quedarse con él.

4. Abre esa carpeta y haz doble clic en `FL26ModStudio.exe`.

**Deberías ver:** una ventana oscura. Arriba: los menús **Archivo, Juego, Perfiles, Idioma
(Language), Ayuda**, el botón **Créditos** y un botón verde **Iniciar el juego** a la derecha.
Debajo, recuadros con lo que hay ahora en el juego (**CARPETA DEL JUEGO**, **SIDER**, **MUNDO
ACTIVO** ...), y luego las secciones **1. Inicio**, **2. Mi mundo**, **3. Contenido del juego**,
**4. Herramientas** y **5. Ajustes**.

La primera vez, una tarjeta pequeña te enseña la ventana en diez pasos (el recorrido rápido).
Léela con **Siguiente**, o ciérrala con **Saltar el recorrido**. No cambia nada. **Ayuda →
Recorrido rápido** la vuelve a mostrar.

Si Windows dice "Windows protegió su PC": pulsa **Más información** → **Ejecutar de todas formas**.

¿Quieres la ventana en otro idioma? Barra de arriba → **Idioma (Language)** → Hrvatski, Español,
Português o Français, y luego vuelve a abrir Mod Studio.

## Paso 3. Dile dónde está tu juego

1. Pulsa **5. Ajustes**.
2. Junto a la carpeta del juego, pulsa **Examinar...**.
3. Elige la carpeta que contiene `FL_2026.exe` (por ejemplo `D:\Games\Football Life 2026`). No
   `SiderAddons`, no una subcarpeta: la carpeta que tiene `FL_2026.exe` dentro.
4. Pulsa **Usar esta carpeta**.

**Deberías ver:** debajo de la carpeta, una línea que empieza por `Encontrado: FL_2026.exe` y
nombra la carpeta de Sider y `sider.ini`.

(Lo mismo está en la barra de arriba: **Juego → Elegir la carpeta del juego...**.)

No hay nada más que preparar. En cuanto sabe dónde está tu juego, Mod Studio desempaqueta él
solo las tablas del juego (su lista de clubes, ligas y jugadores), solo la primera vez. Tarda uno
o dos minutos. Los módulos de Mod Studio entran con **Instalar el mundo** (Camino A) o con
**Construir e instalar** (Camino C). Las ligas nuevas solo funcionan con estos módulos, y traen
el paquete de caras que da su cara a los jugadores nuevos. Si **1. Inicio** dice alguna vez que
faltan o son antiguos, pulsa allí **Instalar ahora**.

Ahora elige el camino que corresponde a tu archivo.

---

## Camino A: un mundo listo (un .zip)

Úsalo cuando alguien te dio un mundo como zip (un modpack, un mundo exportado).

**A1.** No lo descomprimas tú.

**A2.** Pulsa **2. Mi mundo** y luego **+ Añadir...** (a la derecha, junto a las pestañas).

**A3.** Pulsa **Elegir un archivo...** y elige el zip. (O arrastra el zip a esa ventana.)
Una línea verde empieza por `Encontrado: un zip de mundo`. Pulsa **Añadir**: se abre la página
**Importa tu mundo** con el zip.

(Otros dos caminos a la misma página: **1. Inicio → Importar un zip de mundo**, o **2. Mi mundo →
Más ▾ → Importar un zip de mundo**, y luego elige el zip.)

**A4. Deberías ver:** una línea que dice qué es, por ejemplo `un mundo listo para jugar
(_FL26Modpack)`, o `una versión más nueva del mundo _FL26Modpack que tienes` si tienes una
anterior, y debajo cuántas ligas trae. Las partes (el mundo, equipaciones, marcadores ...) están
bajo **Más opciones: qué partes, nombre, orden de las carpetas de contenido, líneas de los map**,
todas marcadas. Déjalas así. (Para instalarlo sin las equipaciones, desmárcalas ahí.)

**A5.** Pulsa **Instalar el mundo**. Si ya hay instalada una versión anterior del mismo mundo (un
Modpack anterior), pregunta si la reemplaza: di **Sí**. La anterior se quita primero, así no
queda nada de ella; tus partidas guardadas no se tocan. Espera hasta que diga que ha terminado.
Mod Studio instala sus módulos (los de esta versión), copia el mundo, pone su archivo de mundo
donde lo leen los módulos y pone el mundo en el juego.

**Deberías ver:** `✓ Listo para jugar: pulsa Iniciar el juego y empieza una Master League nueva` y una ventana **Listo para jugar** con una lista de marcas (el mundo,
los módulos, el paquete de caras ...). Si en cambio dice **Casi listo**, te dice qué arreglar.

En **2. Mi mundo** el mundo tiene ahora una tarjeta verde que dice **● EN EL JUEGO AHORA**, con la
etiqueta **Desde zip**.

Un mundo listo no necesita Build: ya está construido. Mientras está en el juego, los pasos de
Build están desactivados. Para construir ligas propias más tarde, pon primero tu propio mundo en
el juego (**Activar** en su tarjeta en **2. Mi mundo**). Ve al [Paso 4](#paso-4-inicia-el-juego).

---

## Camino B: construye tus propias ligas

Elegir ligas reales de la NewLife Database, o crear ligas propias, tiene su propia guía, con cada
campo explicado:
[Crear tus propias ligas y paquetes](make-your-own-leagues.md).

---

## Camino C: un paquete de ligas (.fl26pack)

**C1.** Pulsa **2. Mi mundo** y luego **+ Añadir...** (a la derecha, junto a las pestañas).

**C2.** Pulsa **Elegir un archivo...** y elige el archivo `.fl26pack`. (O arrástralo a esa
ventana.)

**C3. Deberías ver:** una línea verde `Encontrado: paquete de ligas "..."` con cuántas ligas y
clubes tiene, y sus ligas en una lista, cada una marcada. Desmarca una liga que no quieras. Debajo
de la lista: cuántas competiciones tendrá tu mundo (el juego tiene sitio para 255), y que nada
llega al juego hasta **Construir e instalar**. Pulsa **Añadir**.

(Los otros caminos: **2. Mi mundo → Más ▾ → Paquetes de ligas → Añadir un paquete...**, o
**Archivo → Añadir un paquete de ligas...**. Esos muestran una ventana **Añadir un paquete de
ligas**: ahí también puedes desmarcar partes en **Qué tomar**, por ejemplo los marcadores. Si no
estás seguro, deja todo marcado y pulsa **Aceptar**.)

Si el paquete tiene una liga con un nombre que ya tienes, pregunta si la añade con un nombre
nuevo: pulsa **Sí**.

**Deberías ver:** la pestaña **Ligas**, con las ligas del paquete en la lista, y abajo en la
ventana: "Agregado ... Construir e instalar pone sus ligas en el juego."

No hay nada que guardar: tu mundo se guarda solo un momento después de cada cambio (la barra de
abajo dice **Tu mundo está guardado**).

**C4.** Pestaña **Construcción** (la primera pestaña de **2. Mi mundo**) → el botón grande
**Construir e instalar** → **Sí**.

Pone los módulos de Mod Studio, construye tu mundo y lo pone en el juego, todo de una vez. Tarda
de unos segundos a unos minutos; la barra de abajo muestra cuánto lleva.

(Soltar el `.fl26pack` en **Importa tu mundo** hace lo mismo: después de la ventana **Añadir un
paquete de ligas** el paquete entra en tu mundo y **Construir e instalar** empieza solo.)

**Deberías ver:** una ventana **Construcción terminada** con marcas (Mundo construido, Ligas y
clubes, Módulos instalados y activados, En el juego). Pulsa **Hecho**. En el cuadro de abajo de
la pestaña Construcción no hay ninguna línea que empiece por `error:`.

---

## Paso 4. Inicia el juego

Pulsa el botón verde **Iniciar el juego** arriba a la derecha (o **Juego → Iniciar el juego**).
Espera al menú del juego.

## Paso 5. Empieza una Liga Máster NUEVA

1. **Master League** → **New game** (no Continue: una carrera antigua no recibe las ligas nuevas).
2. En **Select Team**, desplázate: las ligas nuevas están en la lista, bajo sus países.
3. Elige un club y juega.

Las ligas nuevas también están en **Kick Off** → League, y en **Database → Competition Info**.

Cada mundo guarda sus propias carreras. Cuando pones otro mundo en el juego, Mod Studio aparta tus
carreras con el mundo al que pertenecen, y las devuelve cuando ese mundo vuelve a estar en el
juego. No se borra nada.

## Paso 6. Deja que Mod Studio compruebe que funcionó

1. Cierra el juego.
2. En Mod Studio: **2. Mi mundo** → pestaña **Construcción** → **Paso a paso, y Exportar el
   mundo** → **4. Tras iniciar: comprobar**.

**Deberías ver:** una línea por módulo que dice cuántas ligas leyó del mundo, y al final
`the world works as built`. Una línea que dice `not loaded` o `did NOT read the world file`, y la
última línea `something is wrong -- see the lines above`, te dicen qué está mal.

---

## Si algo sale mal

| Lo que ves | Qué hacer |
|---|---|
| `error: no hay tablas del juego -- Ajustes > Desempaquetar las tablas del juego` | **5. Ajustes → Desempaquetar las tablas del juego**. |
| No hay ligas nuevas en Select Team | ¿Empezaste una Liga Máster **nueva**? Luego **4. Tras iniciar: comprobar** ([Paso 6](#paso-6-deja-que-mod-studio-compruebe-que-funcionó)). Si su registro dice `world file -- 0 leagues`, tu mundo estaba vacío: vuelve a añadir el paquete (Camino C) y vuelve a construir. |
| El mundo dice que se construyó con `0 leagues, 0 clubs` | Lo mismo: tu mundo no tenía ligas. Añade algunas primero y luego construye. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | La comprobación se hizo antes de iniciar el juego. Inícialo hasta el menú principal, ciérralo y vuelve a pulsar **4. Tras iniciar: comprobar**. |
| **Construir e instalar** está en gris | Hay abierto un mundo listo de un zip (Camino A). No necesita Build. Para construir tus propias ligas, pulsa antes **Activar** en la tarjeta de tu propio mundo en **2. Mi mundo**. |
| Mi carrera antigua ha desaparecido | Se guarda con el mundo en el que se hizo. Pulsa **Activar** en la tarjeta de ese mundo en **2. Mi mundo** y vuelve. |
| Todos los jugadores nuevos tienen la misma cara | **1. Inicio → Instalar ahora** (cuando Inicio dice que los módulos faltan o son antiguos), o **2. Mi mundo → Construcción → Paso a paso, y Exportar el mundo → 0. Instalar los módulos**: trae el paquete de caras. Luego vuelve a iniciar el juego. |
| El juego se cierra al arrancar | Inícialo otra vez por el launcher (un cierre en los primeros 10 segundos también pasa sin mods). Si sigue cerrándose: **Juego → Iniciar el juego sin mods (modo seguro)...** y pregunta en Discord. |
| Quieres todo como estaba | **Importa tu mundo** (**2. Mi mundo → Más ▾ → Importar un zip de mundo**) → selecciónalo en **En el juego ahora** → **Quitar** saca un mundo instalado. **4. Herramientas → Puntos de restauración → Devolver Sider a antes de Mod Studio...** (también en el menú **Juego**) devuelve cada archivo que Mod Studio cambió y quita lo que trajo. No se borra nada: queda guardado en `SiderAddons\ModStudio\reset-<time>`, y **Deshacer el último reinicio** lo vuelve a poner. |

**Para pedir ayuda:** en el [Discord](https://discord.gg/StQqtk3G3M), manda una captura de lo que
ves y tu `sider.log` (**Juego → Abrir sider.log**, o `SiderAddons\sider.log` en la carpeta del juego).
