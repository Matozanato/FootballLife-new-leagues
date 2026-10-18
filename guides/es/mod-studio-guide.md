# FL26 Mod Studio — guía de uso

> [English](../en/mod-studio-guide.md) · [hrvatski](../hr/mod-studio-guide.md) · **español** · [português](../pt/mod-studio-guide.md) · [français](../fr/mod-studio-guide.md)

> **¿Primera vez con Mod Studio?** Dos guías paso a paso, cada clic en orden: [Instalar un paquete listo](install-a-pack.md)
> (alguien te dio un mundo, un modpack o un `.fl26pack`) · [Crear tus propias ligas y paquetes](make-your-own-leagues.md)
> (tú eliges las ligas y las construyes). Esta guía explica cada página y opción a fondo.

> Preguntas frecuentes (actualizar, cierres al arrancar, copas, ascensos, qué enviar cuando algo
> falla), en inglés: [faq.md](../../docs/faq.md) · preguntas y ayuda en [Discord](https://discord.gg/StQqtk3G3M)

FL26 Mod Studio es un solo programa para todo lo que añades a Football Life 2026:

- los **mods** que descargas: estadios, equipaciones, balones, marcadores, comentarios, música,
  caras, módulos Lua;
- los **servidores de contenido** que los sirven (Stadium Server, Ball Server, Kit Server y los
  demás), con sus archivos de mapa editados como tablas en lugar de a mano;
- la **configuración de Sider** en sí: qué carpetas de contenido y módulos están activados, y en
  qué orden;
- **ligas y clubes nuevos** (el League Builder), tus cambios en las ligas, clubes y **jugadores**
  del propio juego, y los **paquetes de ligas** que un modder crea una vez y cualquiera puede
  añadir a su juego.

No se sobrescribe nada del juego. Antes de cambiar un archivo, el programa guarda una copia, y
todo mod que instala se puede volver a quitar.

---

## 1. Antes de empezar

- **Football Life 2026** instalado, con su carpeta `SiderAddons` (FL26 viene con Sider).
- Descomprime el programa donde quieras, p. ej. `Documents\FL26 Mod Studio`. Mantén la carpeta
  entera: las carpetas `_internal` y `pack` y los archivos `README` se quedan junto a `FL26ModStudio.exe`.
- **Cierra el juego** mientras cambias cosas. Sider lee su configuración cuando arranca el juego.

La ventana está en inglés. **Idioma (Language)** en la barra de arriba (o **Ajustes → Idioma**) la
pasa a croata (Hrvatski), español (Español), portugués de Brasil (Português) o francés
(Français). El idioma nuevo se ve la próxima vez que abras Mod Studio.

## 2. Primer inicio

**El recorrido rápido.** La primera vez que abres la 0.2.4, una tarjeta pequeña te enseña dónde
está ahora cada cosa, un sitio cada vez, con un marco naranja alrededor de lo que explica: el
idioma, los recuadros de lo que hay en el juego, **Iniciar el juego**, luego de **1. Inicio** a
**5. Ajustes** y **Ayuda**. Son diez pasos. Mientras dura no cambia nada. **Siguiente** y
**Atrás** avanzan y retroceden, **Saltar el recorrido** lo cierra, y **Ayuda → Recorrido rápido**
lo vuelve a mostrar cuando quieras.

1. **5. Ajustes → Carpeta del juego**: pulsa **Examinar...**, elige la carpeta que contiene
   `FL_2026.exe` y luego **Usar esta carpeta**. La línea de debajo dice qué encontró, p. ej.
   `Encontrado: FL_2026.exe, Sider en SiderAddons, sider.ini.`
2. Las tablas del juego: Mod Studio las desempaqueta solo la primera vez (lee los clubes, ligas
   y jugadores del juego en una carpeta de trabajo; tarda uno o dos minutos, y la barra de abajo
   lo dice). Tras una actualización del juego Build lo nota y ofrece desempaquetarlas de nuevo
   primero; **Ajustes → Las tablas del juego → Desempaquetar las tablas del juego** lo hace a
   mano. **Usar otra carpeta de tablas...** sirve para una base de datos propia, como una carpeta
   `pesdb` en livecpk: desempaqueta primero las tablas del juego y luego elige esa carpeta. Sus
   archivos van encima de los del juego, que ponen lo que a ella le falte. Un mod de base de
   datos que cambia de sitio las ligas del juego (UML 2026 y similares) funciona: cada liga del
   juego toma el país de la mayoría de sus clubes, y NewLife Database solo cuenta un club como
   del juego cuando estas tablas lo tienen (0.2.4).
3. Abre **1. Inicio**. Muestra el mundo que está en el juego (**EN EL JUEGO AHORA**, con **Abrir
   sus ligas** y **Cambiar de mundo...**, que abre **2. Mi mundo**), una tarjeta que dice si tu
   mundo tiene cambios que el juego aún no tiene (**Ir a Construcción** y **Solo las copas
   europeas...**), y la **Comprobación previa**: una tabla con una fila por comprobación (juego,
   Sider, módulos, carpetas de contenido ...). Cuando algo va mal, una barra roja nombra el
   problema y tiene el botón que lo arregla. Cuando los módulos de Mod Studio faltan, son
   antiguos o están desactivados, la fila dice cuáles e **Instalar ahora** los pone. A la
   derecha: **Acciones rápidas** (**Instalar los módulos**, **Construir el mundo otra vez**,
   **Importar un zip de mundo**, **Añadir un paquete de ligas**) y **Últimos cambios** (los
   puntos de restauración más nuevos, **Todos los puntos de restauración**).

**Actualizaciones.** Unos segundos después de arrancar, el programa pregunta a GitHub si ha salido
un FL26 Mod Studio más nuevo, y solo avisa cuando lo hay. **Descargar e instalar** baja el nuevo
zip, lo comprueba con la suma de control de la versión, cierra el programa, pone los archivos
nuevos encima de los antiguos y lo vuelve a abrir. Tus ajustes, mundos, puntos de restauración y
el juego no se tocan. **Ayuda → Buscar actualizaciones...** pregunta en cualquier momento; quita
la marca de **Ayuda → Buscar actualizaciones al iniciar** y el programa solo preguntará entonces.
Si el programa está en una carpeta donde Windows no le deja escribir (como Program Files), abre
en su lugar la página de la versión: descomprime tú el zip, o mueve el programa a una carpeta tuya.

**Carreras de antes de la 0.2.0.** La 0.2.0 permite 792 partidos por día del calendario en lugar de 280, y eso cambia las tablas con las que se guarda una carrera: **una carrera guardada con una versión anterior no carga** (se queda en la pantalla de carga). Empieza una carrera nueva después de actualizar. Tus mundos y datos de Edit no cambian.

**La 0.2.4 y tu carrera.** Una carrera guardada con la 0.2.2 o la 0.2.3 sigue funcionando, y una
copa guardada antes de la 0.2.4 también carga. Un arreglo necesita un Build nuevo: hasta la 0.2.4
el portero era el capitán de todos los clubes de un mundo hecho con Mod Studio. **Construir**
ahora da a cada club y selección que no los tiene un capitán y los jugadores que tiran los
penaltis, las faltas y los córneres. Para tenerlos, **construye** tu mundo otra vez y empieza
una carrera nueva.

**Jugar.** El botón **Iniciar el juego** arriba a la derecha (o **Juego → Iniciar el juego**)
inicia el juego y avisa antes cuando hay módulos en un orden equivocado. Al lado, una etiqueta
dice si todo está listo: **LISTO PARA JUGAR**, **NO ESTÁ LISTO** o **AÚN NO HAY MUNDO**. **Juego →
Iniciar el juego sin mods (modo seguro)...** vuelve a poner la configuración que Mod Studio
encontró la primera vez.

**Créditos.** El botón **Créditos**, junto a **Ayuda**, nombra a todos los que ayudaron a hacer
Mod Studio: los testers, quienes mandaron reportes y logs, y aquellos cuyas ideas están dentro.

**¿Más de una carpeta de Sider?** Sider no tiene por qué llamarse `SiderAddons`. El programa
busca la carpeta junto a `FL_2026.exe` que contiene un `sider.ini`, y también un nivel más abajo
(`sider\patch 1`, `sider\patch 2` ... cuando una carpeta tiene varias copias de Sider). Si hay
varias, **Ajustes → Carpeta de Sider** elige con cuál trabaja; las demás no se tocan.

**¿El juego está en Program Files?** Windows solo deja cambiar archivos ahí a un programa que se
ejecuta como administrador. Cuando Mod Studio no puede escribir en la carpeta del juego, lo dice
(también en **Inicio**) y ofrece **Reiniciar como administrador**. O mueve el juego a una carpeta
tuya.

## 3. Las páginas

Arriba en la ventana, de izquierda a derecha:

- los menús **Archivo**, **Juego**, **Perfiles**, **Idioma (Language)** y **Ayuda**, y **Créditos**;
- el botón **Iniciar el juego** con la etiqueta de estado al lado;
- debajo, recuadros con lo que hay ahora en el juego: **CARPETA DEL JUEGO**, **SIDER**, **MUNDO
  ACTIVO**, **MÓDULOS**, **LIGAS** y **PACK**. Un recuadro rojo nombra el problema; pulsa un
  recuadro para ir a la página donde se arregla;
- luego las secciones numeradas, y abajo de la ventana una barra de estado (listo o el problema,
  lo que está haciendo el programa, **Tu mundo está guardado**, el número de puntos de
  restauración).

| Sección | Qué hay dentro |
|---|---|
| **1. Inicio** | El mundo del juego, la comprobación previa, las acciones rápidas |
| **2. Mi mundo** | Tus mundos como tarjetas, y las pestañas **Construcción**, **Ligas**, **Clubes**, **Jugadores**, **Equipaciones**, **Estadios** y **Copas** (sección 3.1) |
| **3. Contenido del juego** ▾ | **Balones**, **Comentarios**, **Música**, **Otro contenido** |
| **4. Herramientas** ▾ | **Módulos Lua**, **Carpetas de contenido**, **Perfiles**, **Puntos de restauración**, **Diagnóstico** |
| **5. Ajustes** | Carpeta del juego, carpeta de Sider, idioma, carreras de Master League, las tablas del juego |

**Archivo** tiene **Mundo nuevo**, **Abrir un mundo...**, **Guardar tu mundo como...**,
**Cambios en este mundo...** (todo lo que tu mundo cambia en el juego en una sola lista; elige
líneas y pulsa **Deshacer los cambios elegidos** para quitarlas), **Añadir un paquete de
ligas...** y **Crear un paquete de ligas...**. **Juego** abre la carpeta del juego, la carpeta de
Sider, `sider.ini` y `sider.log`, e inicia el juego. **Ayuda** tiene **Guía de uso**, **Recorrido
rápido**, **Buscar actualizaciones...** y **Acerca de FL26 Mod Studio**.

### 3.1 Mi mundo

**2. Mi mundo** es el sitio de tus mundos. Un **mundo** es una carpeta de contenido llamada
`_FL26...` que contiene ligas, clubes y jugadores nuevos; el juego lee uno cada vez (sección 8).

**Arriba**: **COMPETICIONES** (cuántas competiciones tiene el mundo del juego, ligas y copas
juntas; el juego tiene sitio para 255), **PAÍSES NUEVOS** (cuántos países añade; hay sitio para
99), un aviso de que **los cambios necesitan una Master League nueva**, y el estado del mundo
abierto. **▾ Mundos** pliega la fila de tarjetas para dejar sitio, y la vuelve a mostrar.

**Las tarjetas**: una tarjeta por cada mundo del disco. Primero va el mundo del juego, luego los
más nuevos; la rueda del ratón mueve la fila a izquierda y derecha.

- El mundo del juego sale en verde, con **● EN EL JUEGO AHORA** y **● Activo**. Un mundo instalado
  desde un zip lleva la etiqueta **Desde zip**.
- Cualquier otro mundo construido (**NO ESTÁ EN EL JUEGO**) tiene **▶ Activar**: pone ese mundo en
  el juego (activado en `sider.ini`) y saca el que estaba. No se borra nada: el otro mundo se
  queda en el disco con sus propias carreras. Después empieza una Master League nueva.
- Cada tarjeta tiene **Exportar...** (un `.zip` del mundo para otro PC, sección 9.1),
  **Renombrar** y **Borrar**. **Borrar** saca el mundo del juego y del disco, pero lo guarda
  entero en **Puntos de restauración** (sección 5). El mundo del juego no se puede borrar:
  activa antes otro mundo.
- **+ Mundo nuevo**, al final, empieza un mundo vacío tuyo (lo mismo que **Archivo → Mundo
  nuevo**); luego añade sus ligas en **Ligas**.

Si hay dos mundos activados a la vez, la tarjeta verde dice **▶ Dejar solo este**: deja ese mundo
en el juego y desactiva los demás.

**Las pestañas** de debajo de las tarjetas cambian el mundo abierto: **Construcción** (sección
8.2), **Ligas**, **Clubes** y **Jugadores** (sección 8), **Equipaciones** y **Estadios** (sección
6). **Copas ▾** abre las ventanas de copas: **Torneos de pretemporada**, **Copas de nuestros
países**, **Copas de los países del juego** y **Nombres de las competiciones**. A la derecha:

- **NewLife Database** abre la página de NewLife (sección 8.4);
- **+ Añadir...** es una sola ventana para tres cosas: un zip de mundo (un Modpack), un paquete de
  ligas (`.fl26pack`) y la NewLife Database (una carpeta o sus zip). Suelta el archivo encima o
  usa **Elegir un archivo...** / **Elegir una carpeta...**. Dice en una línea verde qué
  encontró; para un paquete de ligas muestra las ligas para marcar y cuántas competiciones
  tendrá el mundo. **Añadir** lo pasa a la página que toca: un zip de mundo a **Importa tu
  mundo** (sección 4), un paquete a tu mundo, la NewLife Database a su página. Nada llega al
  juego hasta **Construir e instalar**;
- **Más ▾** tiene **Paquetes de ligas** (sección 9), **Importar un zip de mundo** (sección 4),
  **NewLife Database** y **Carpetas de contenido** (sección 5).

**Un mundo de un zip** (un Modpack) ya está construido, así que **Construir** está desactivado
para él (sección 8.2). Para cambiarlo igualmente, **Hacerlo editable...**, arriba en Mi mundo, lo
convierte en un mundo tuyo, en el mismo sitio y con su propio nombre. Antes se copia entero a
**Puntos de restauración**. Después de construirlo, empieza una Master League nueva.

**Cada mundo guarda sus propias carreras de Master League** (0.2.4). Una carrera está hecha para un
mundo: en otro mundo sus ligas y clubes no existen. Por eso, cada vez que cambia el mundo del
juego (**Activar**, **Construir e instalar** de otro mundo, Importa tu mundo, Carpetas de
contenido, un perfil), Mod Studio cambia con él la carpeta de partidas guardadas del juego. Las
carreras del mundo que sale se guardan en `save_<mundo>`, junto a `save`, en
`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`. Las carreras del mundo que entra
vuelven a `save`; un mundo que aún no tiene ninguna empieza con una vacía. Toda la carpeta va con
el mundo (carreras, Become a Legend, los datos de Edit), menos los ajustes del juego, que van
contigo a todos los mundos.

No se borra nada: antes del primer cambio Mod Studio copia toda tu carpeta de partidas en
`SiderAddons\ModStudio\backups\saves\<fecha>` (**Puntos de restauración** la muestra), y la
primera vez te dice adónde fueron tus carreras. No cambia la carpeta mientras el juego está
abierto, ni cuando ya existe una carpeta `save_<mundo>` con ese nombre: dice por qué y no cambia
nada. **Renombrar** renombra también la `save_<mundo>` del mundo; **Borrar** la deja en paz (tus
carreras son tuyas). ¿No lo quieres? Desmarca **Ajustes → Cada mundo guarda sus propias carreras
(la carpeta de partidas guardadas cambia con el mundo)**.

**Ligas** (una pestaña de Mi mundo) muestra todas las ligas, las del juego y las tuyas, bajo su
continente; las divisiones de cada país van juntas, de arriba abajo (Bundesliga, 2. Bundesliga,
3. Liga), hasta que arrastras una liga para ponerla en otro sitio. Filtros **Todas**,
**Nuestras** y **Cambiado**, y un cuadro de búsqueda. Elige una: una liga tuya tiene **Editar
liga...**, **Añadir división inferior**, **Clubes y nombres**, **Jugadores** y **Quitar**; una
liga del juego tiene su nombre, logo y clubes (sección 8, "Las ligas del juego"). **Añadir liga**
crea una nueva. **Lugares en Select Team** muestra dónde puso el último Build cada una de tus
ligas. **Más ▾** tiene **Torneos de pretemporada**, **Copas de nuestros países**, **Copas de los
países del juego**, **Plazas europeas de las ligas del juego**, **Clubes europeos de la primera
temporada**, **Ranking UEFA**, **Plazas sudamericanas**, **Nombres de las competiciones**, **IDs
de competiciones**, **Orden de las ligas**, **Temporadas de las ligas del juego** y **Nombre del
mundo y archivo...**. Esta última abre la página con el nombre del mundo y la lista de tus ligas
(las guías antiguas la llaman *Ligas nuevas*).

## 4. Importa tu mundo

**Importa tu mundo** es la página que instala un pack descargado. Llegas a ella con **2. Mi mundo
→ Más ▾ → Importar un zip de mundo**, con **Importar un zip de mundo** en **Acciones rápidas** de
**Inicio** (abre enseguida el selector de archivos), o con **+ Añadir...** en Mi mundo.

Suelta el pack encima (`.zip`, `.7z`, una carpeta, `.lua`, `.cpk` o `.fl26pack`), o usa **Elegir
un archivo...** / **Elegir una carpeta...**. Cuando Mod Studio se ejecuta como administrador,
Windows bloquea el arrastrar y soltar; la página lo dice: usa los dos botones.

El programa mira dentro y dice en una línea qué es: una versión más nueva de un mundo que tienes,
un mundo listo para jugar, un paquete de ligas o un mod, con las ligas que trae. Luego un solo
botón, **Instalar** (**Instalar el mundo** para un mundo). Una versión más nueva de un mundo que
tienes sustituye a la anterior: pregunta una vez, la anterior se quita primero para que no quede
nada de ella, tus partidas guardadas no se tocan y empiezas una Master League nueva con la nueva.
Si en este PC se construyó un mundo con el mismo nombre, lo dice antes de que pulses Instalar y
te pide que primero renombres ese mundo en su tarjeta de Mi mundo.

Las partes, y adónde va cada una, están en el desplegable **Más opciones: qué partes, nombre,
orden de las carpetas de contenido, líneas de los map**:

| Parte | Qué pasa |
|---|---|
| Carpeta de contenido (livecpk) | Se copia en `SiderAddons\livecpk\<nombre>` y se añade a `sider.ini`. |
| Archivos de servidor de contenido | Se copian en la carpeta `content` del servidor. Su **archivo de mapa se combina con el tuyo**: tus líneas se quedan y se añaden las líneas nuevas del mod. Para un club que ya tienes en el mapa decide la opción de **Más opciones**: *usar las del mod*, o *conservar las mías, añadir las del mod detrás*. Un pack de marcadores o de menús hecho para otro mundo va a la competición que dice su nombre en tu mundo, y la página dice qué liga no tiene tu mundo. |
| Módulo Lua | Se copia en `SiderAddons\modules` y se activa en el lugar correcto del orden. |
| .cpk empaquetado | Se desempaqueta en una carpeta de contenido al instalar. |
| Paquete de ligas | Se añade a tu mundo (sección 9). Un `.fl26pack` soltado aquí entra, y **Construir e instalar** empieza solo. |
| Mundo listo | Un mundo construido de **Exportar el mundo** (sección 9.1), o una carpeta `SiderAddons` copiada con `modules\fl26world.txt`. La carpeta del mundo se copia con su propio nombre, su archivo de mundo va a `SiderAddons\modules`, y el mundo se pone en el juego con los módulos de Mod Studio. Termina con **✓ Listo para jugar: pulsa Iniciar el juego y empieza una Master League nueva** y una lista de comprobación final: el mundo, activado, los módulos, el paquete de caras, los servidores de contenido que usa el mundo, los estadios locales. Si falta algo dice **Casi listo** y qué arreglar; la línea roja bajo la instalación (*ver qué arreglar*) vuelve a mostrar la lista. |
| DLL | **No se instala.** Una DLL se ejecuta con los permisos del juego; instálala solo a mano y solo de una fuente en la que confíes. |

En el mismo desplegable puedes desmarcar una parte que no quieras (las equipaciones, por ejemplo,
para instalar un mundo sin equipaciones), ponerle un nombre al mod y elegir si las carpetas de
contenido nuevas van arriba (ganan) o al final. **En el juego ahora** muestra todos los packs
instalados con el programa. **Quitar** borra los archivos que añadió y devuelve los que reemplazó.

La instalación copia primero todos los archivos y escribe las líneas de los map al final, así
que una instalación que se para a medias no deja ninguna línea que apunte a un archivo que falta.
Si eso pasó con una versión anterior, **Diagnóstico** nombra el zip o el mundo: instálalo otra vez
(un mundo construido en tu PC: constrúyelo otra vez).

## 5. Carpetas de contenido y módulos Lua

**Carpetas de contenido** (**4. Herramientas**) muestra las líneas `cpk.root` de `sider.ini`;
los mundos (`_FL26...`) se ven cuando marcas **Mostrar los mundos (_FL26...)**, y **Solo
activadas** oculta el resto. El mundo que usa ahora el juego está en una fila verde, con su nombre
en negrita y **EN EL JUEGO AHORA** en la columna de notas. Sider busca un archivo de arriba abajo,
así que cuando dos carpetas tienen el mismo archivo gana la que está más arriba.

- Marca o desmarca una carpeta para activarla o desactivarla (la línea se convierte en comentario,
  nunca se borra).
- **Arriba del todo**, **Subir**, **Bajar** cambian el orden; **Añadir carpeta...** añade una
  carpeta que ya tienes.
- Para cada carpeta se muestran el tamaño y lo que contiene (caras, equipaciones, estadios...).
- También están **Volver a escanear**, **Quitar de la lista** y **Borrar del disco...**.
- No se escribe nada hasta que pulses **Aplicar**. **Descartar** olvida los cambios.

**Renombrar mundo...** y **Borrar mundo...** (en los detalles de la carpeta cuando eliges un mundo,
o con clic derecho sobre el mundo) hacen lo mismo que **Renombrar** y **Borrar** en la tarjeta de
un mundo en Mi mundo:

- **Borrar mundo...** pregunta antes y no borra nada para siempre. La carpeta del mundo, sus
  equipaciones y marcadores, sus líneas en `sider.ini` y en los mapas de equipaciones y
  marcadores, y su registro de instalación van a
  `SiderAddons\ModStudio\backups\worlds\<mundo>\<fecha> deleted`, y **Puntos de restauración →
  Restaurar esta copia** lo devuelve todo exactamente como estaba. Se guardan las 3 últimas
  copias de cada mundo. El mundo del juego (el verde) no se puede borrar. Tu mundo en Mod Studio
  (sus ligas) no se borra, así que puedes volver a construirlo. **Borrar del disco...** en la fila
  de un mundo hace el mismo borrado seguro.
- **Renombrar mundo...** cambia el nombre en todos los sitios donde está escrito: la línea de
  `sider.ini` (en el mismo lugar, activada o no como estaba), las carpetas de equipaciones y
  marcadores y sus líneas de mapa, el archivo de mundo, tus perfiles y tu mundo en Mod Studio. El
  nombre nuevo debe empezar por `_FL26` (letras, cifras, `-` y `_`). Un mundo grande se renombra
  en segundo plano ("Renombrando ..." en la barra de abajo y en su tarjeta). Una carrera sigue
  funcionando después de renombrar: el juego nunca ve el nombre del mundo, solo los archivos que
  tiene dentro.

**Módulos Lua** (**4. Herramientas**) es lo mismo para las líneas `lua.module`. La línea de arriba
dice si los módulos propios de Mod Studio están instalados, al día y activados; si no, nombra los
que faltan, son antiguos o están desactivados, e **Instalar ahora** lo arregla. El programa conoce
el orden correcto de los módulos habituales (los servidores de contenido después de los módulos
que usan) y avisa cuando un módulo está en un lugar equivocado. Algunos módulos necesitan un
ajuste de Sider (por ejemplo, Goal Song Server necesita `match-stats.enabled = 1`); el programa
dice cuál. Los módulos `fl26...` propios de Mod Studio están ocultos hasta que desmarcas **Ocultar
los módulos propios de Mod Studio (fl26...)**; **Añadir módulo...** añade un módulo que tienes.

Los módulos propios de Mod Studio mantienen el orden en que se instalaron, juntos en un bloque de
`sider.ini` con su propio título. Las líneas antiguas que deja una instalación a mano (un juego de
caps antiguo, un módulo que aparece dos veces) las desactivan **Instalar ahora** y **Construir**.

Desde 0.2.0 las doce pequeñas protecciones contra cierres van en dos archivos, `fl26guards.lua` (las ocho `fl26nullguard`) y `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), así la lista es más corta. sider.log sigue nombrando cada protección en su propia línea. Build desactiva las líneas sueltas antiguas; no hay que hacer nada a mano.

**Sin copias junto a tus archivos** (0.2.4). Cuando Construir, Activar o Instalar los módulos
cambian un archivo, la copia de antes va a `SiderAddons\ModStudio\backups` y aparece en **Puntos
de restauración**, no junto al archivo (ya no hay `map.txt.before-builder` ni
`modules\before-builder-<n>`).

**Desactivar los regens** (0.2.0): `fl26regen` da a los regens nombres nuevos, un potencial
nuevo y una cara del paquete de caras de regens. Para jugar sin él, desmarca **Ocultar los
módulos propios de Mod Studio (fl26...)** para que se vean los nuestros, desmarca
`fl26regen` y pulsa **Aplicar**. Mod Studio lo anota en `modules\fl26-off.txt` en la carpeta de
Sider, así que **Construir**, **Instalar los módulos** y el cambio de mundo lo dejan desactivado
en vez de volver a activarlo, como hacen con todos los demás módulos. El juego hace entonces sus
propios regens: su potencial y sus nombres, sin caras del paquete de caras de regens. Márcalo de
nuevo y pulsa **Aplicar** para volver a activarlo. Solo `fl26regen` se puede mantener
desactivado así.

## 6. Contenido del juego: los servidores de contenido

Cada una de estas páginas pertenece a un servidor de contenido. **Equipaciones** y **Estadios**
son pestañas de **2. Mi mundo**; **Balones**, **Comentarios**, **Música** y **Otro contenido**
están en **3. Contenido del juego**. **Otro contenido** tiene una pestaña para **Marcadores**,
**Menús**, **Equipaciones arbitrales**, **Parches de manga** y **Tiempo**, y **Módulos de
aspecto**. Los módulos propios de SPFL26 para equipaciones, estadios y marcadores (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) leen los mismos archivos de `content\kits`, `content\stadiums` y `content\scoreboards`; cuando el servidor no está instalado, su página edita esos (equipaciones desde 0.1.7, estadios y marcadores desde 0.1.8). Cada página tiene:

- una **línea de estado**: si el módulo está activado y si existe su carpeta de contenido;
- una pestaña por **archivo de mapa**, mostrado como tabla: qué recibe cada competición, club o
  estadio. **Añadir...**, **Cambiar...**, **Copiar**, **Act. / desact.** (la línea pasa a ser un
  comentario) y **Quitar**; elige los elementos de la biblioteca en lugar de escribir ids.
  **Guardar** escribe el archivo; la copia de antes va a Puntos de restauración;
- la **Biblioteca**: lo que hay en la carpeta de contenido del servidor, con imágenes donde las
  hay. Se marcan los elementos que ninguna línea del mapa usa y las líneas que apuntan a
  elementos que faltan;
- los **Ajustes** del servidor, donde los tiene (estadio, balón, marcador favorito ...).

El programa comprueba las tablas antes de guardar: un número donde va un número, sin comas dentro
de un nombre, un elemento que existe. Una línea con un problema sale coloreada: **deja el ratón
encima para ver por qué**. **Solo líneas con problemas** muestra solo esas. Un club que aparece dos
veces también sale marcado: solo cuenta su primera línea. El problema más habitual, "... no está en
la biblioteca", significa que la línea apunta a una carpeta que no está en la carpeta de contenido
del servidor, y el juego no muestra nada ahí (un estadio negro, la equipación antigua del club):
apúntala a una carpeta que muestre la pestaña **Biblioteca**, o quita la línea. **Módulos de
aspecto** (en **Otro contenido**) activa o desactiva los módulos sin archivos de mapa.

Una línea de competición va por una **fase** de la competición, no por la competición: el juego
dice a los servidores de contenido la fase que se juega (la Conference League es 186, 1210, 187,
189 y sus rondas posteriores 1213 ... 8381; la Champions League 2, 3, 4 y las suyas), así que una
línea con el número de la competición (174) nunca se usa. El selector de competiciones ofrece cada
competición otra vez como **(todas las fases: N)**: elígela y se escribe una línea por fase (0.1.9).
Una línea con el número de una competición sale marcada como problema.

**Marcadores de un mundo de un zip.** Un mundo listo (el Modpack) trae los marcadores de sus
ligas. Mientras hay otro mundo en el juego, sus líneas se quedan en **Otro contenido →
Marcadores**, desactivadas, y vuelven a activarse con su mundo. Lo mismo pasa con los temas de
menú que trajo un mundo.

**Importar equipaciones...** (0.1.8, en la pestaña *Equipaciones*): equipaciones para muchos clubes a la vez. Elige una carpeta de equipaciones listas de kit-server -- una carpeta por club, con `p1`, `p2`, `g1` ... y `order.ini`, con el nombre del club (`Dinamo Zagreb`) o su ID de equipo (`2215`). **Emparejar con** elige *Todos los clubes* o *Los clubes nuevos del mundo del juego*. Los emparejamientos del 60% o más salen marcados; revisa los desmarcados y la columna *Coincidencia* antes de **Aceptar** (una carpeta sin pareja dice "ningún club encontrado"). Las equipaciones se copian a la biblioteca de kit-server (`Liga\Club`, como las tenía la carpeta) y cada club recibe una línea en `map.txt`; **Guardar** la escribe. Un club que ya tiene línea la conserva, salvo que esté marcado **Reemplazar las equipaciones ya puestas**. Las equipaciones de un club nuevo van por el ID que le dio Build, así que construye el mundo y déjalo en el juego primero. La carpeta de un club también puede tener imágenes simples de las equipaciones (0.2.0): `p1.png`, `p2.png` ... para las equipaciones y `g1.png` para el portero (mejor 2048 x 2048; también sirven `.jpg` y `.dds`). Mod Studio las convierte en equipaciones de kit-server; los dorsales, los números del pantalón y la fuente del nombre son texturas aparte, así que salen de una equipación que ya está en la biblioteca, elegida en **Números y nombres de** (empieza en la primera equipación de la biblioteca que los tiene; *ninguno*: el juego mantiene las del club). Los colores de `config.txt` se leen de la imagen. La conversión de imágenes es de Xxspedd, de su herramienta de equipaciones. Mod Studio no dibuja equipaciones: las imágenes las pones tú o un creador de equipaciones.

Si tu mundo está construido con **Equipaciones simples para el modo Edición** (sección 8), Kit
Server no viste a los clubes nuevos, así que las equipaciones importadas no se ven en ellos;
**Importar equipaciones** lo dice. Desmarca esa opción en la pestaña **Construcción** y vuelve a
construir.

## 7. Perfiles

Un perfil recuerda qué carpetas de contenido y módulos están activados, y en qué orden. Ten uno
para Master League, otro para jugar online, otro para pruebas (**4. Herramientas → Perfiles**, o
el menú **Perfiles**):

- **Guardar la configuración actual...** guarda con un nombre lo que está activado ahora.
- **Cambiar a este** pone esa configuración en `sider.ini` (el `sider.ini` antiguo va a Puntos
  de restauración).
- **Actualizar con la configuración actual** sobrescribe el perfil; **Borrar** lo quita.
- **Exportar...** / **Importar...** llevan un perfil a otro PC (`.fl26profile.json`).

## 8. League Builder: ligas, clubes y jugadores nuevos

League Builder añade ligas nuevas al juego y cambia las del propio juego. Lo que crea es un
**mundo**: una carpeta de contenido llamada `_FL26...` que el juego lee mientras está en el juego.
Trabajas en las pestañas de **2. Mi mundo**.

**Quitar** (Ligas) borra la liga seleccionada con sus clubes. Para borrar varias a la vez, abre
**Más → Nombre del mundo y archivo...**, elígelas con Ctrl+clic, Mayús+clic o Ctrl+A, y luego
**Quitar** o la tecla Supr.

**Ligas → Añadir liga**

| Campo | Qué significa |
|---|---|
| **Nombre** | El nombre de la liga en el juego. No puede haber dos iguales. |
| **País** | Da la bandera y el lugar donde aparece la liga. Un país para el que el juego no tiene liga recibe un título propio. |
| **Clubes** | De 10 a 24 (de 1 a 24 para clubes sin liga). |
| **Clubes sin liga** | Para un club, o unos pocos, sin una liga alrededor (0.1.8): por ejemplo solo el BATE Borisov de Bielorrusia. Elige el grupo al que van: *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* o *Classic Teams* -- donde el juego guarda sus propios clubes que no juegan en ninguna liga (Dynamo Kyiv, Wydad Casablanca ...). En Select Team aparecen en ese grupo. Tienen nombre, escudo, equipaciones, entrenador, formación, jugadores y estadio como cualquier club nuevo (**Editar club**, **Jugadores**); el nombre de arriba es solo cómo los lista Mod Studio. No juegan liga, copa ni competición europea, y todo lo demás de este diálogo sale en gris. En *Ligas* un grupo así muestra *sin liga (...)* en lugar de un ID de liga. |
| **Formato** | *Todos contra todos*, de 1 a 4 veces, *se divide en dos (estilo escocés)* o *Apertura y Clausura*: dos torneos por temporada (septiembre a principios de enero, enero a mayo), cada uno desde cero puntos, luego una liguilla de 8 o 4 clubes (o ninguna). La tabla de toda la temporada decide ascensos y descensos. 18 clubes como máximo. Una liga dividida tiene 46 jornadas como máximo, antes y después de la división juntas (16 clubes dos veces son 30, así que su grupo más grande dos veces puede tener 8 clubes, 14 jornadas). Por ahora, solo una liga por país puede dividirse o jugar Apertura/Clausura. **La división en dos y el Apertura y Clausura son experimentales** (0.2.4): funcionan, pero aún tienen más fallos abiertos que todos contra todos, el formato totalmente probado. La ventana lo dice debajo de los formatos. Sigue avisando de lo que encuentres. |
| **División** | *(primera división)*, o la liga que tiene encima: otra liga nueva o una del juego. Para poner una liga nueva bajo otra liga nueva en un paso: selecciónala y pulsa **Añadir división inferior** (toma el país, el número de clubes, el formato y los ascensos/descensos de la liga de arriba; solo falta el nombre). Una liga que ya tiene otra liga nueva debajo sale en gris (0.1.9): el juego solo sigue un enlace hacia abajo desde una liga, así que los grupos de una misma división (tres grupos de la Serie C bajo la Serie B) todavía no son posibles. |
| **Asc. / desc.** | Cuántos clubes cambian de sitio con la liga de arriba al final de la temporada. |
| **Temporada** | Solo para la primera división de un país nuevo: *agosto a mayo* (por defecto) o *febrero a diciembre*, como Brasil, Japón o Arabia Saudí: los clubes suben y bajan en Año Nuevo, y las divisiones de abajo la siguen. Todavía no con división en dos, Apertura/Clausura ni copa de la liga -- ni con división en dos o Apertura/Clausura en una división debajo de una liga de febrero a diciembre, también la Liga BetPlay o la J1 League del juego. |
| **Europa** | Solo para primera división: qué puesto de la liga va a qué competición europea. **Primera división: 1.º fase previa UCL, 2.º UEL, 3.º UECL** rellena las tres habituales (*... (fase previa)* son los play-offs de agosto, ver 8.2); **Añadir plaza**, la ✕ de una fila y **Borrar** para todo lo demás. Cada puesto una sola vez, y solo puestos que la liga tiene. Por debajo de 1 el puesto dice **Campeón de copa** (0.1.7): el campeón de la copa del país (un país nuevo necesita **Copa nacional**) -- y si el campeón ya tiene plaza europea por la liga, la plaza baja por la liga al siguiente club, como hace la UEFA. Desde 0.2.0 el campeón de copa también puede ir a las copas que construye Mod Studio (Copa Sudamericana, Copa Confederación CAF, AFC Champions League Two ...); en una carrera nueva, antes de que nadie haya ganado la copa, esa plaza también va al siguiente club de la liga. Una liga del juego también puede tenerla (*Plazas europeas de las ligas del juego*). Déjalo vacío para una categoría inferior. La plantilla sigue al país: Asia recibe la AFC Champions League y la AFC Champions League Two, Sudamérica la Libertadores y la Copa Sudamericana, África la CAF Champions League y la Copa Confederación CAF, Norteamérica y Centroamérica la CONCACAF Champions Cup, Oceanía la OFC Champions League. La **AFC Challenge League** (0.2.0) es la tercera copa de la AFC, por debajo de la AFC Champions League Two, como la Conference League en Europa; se elige con **Añadir plaza** (*AFC CHL* en la lista de ligas). Esas siete copas que el juego no tiene se construyen con el mundo (sección 8.2). Una plaza de *clasificación a la Libertadores* ocupa el sitio de un club del juego en la ronda previa (el último del país con más clubes en ella), como mucho seis de sus ocho plazas; **Comprobar el plan** dice qué ligas se quedan fuera pasado ese número. |
| **Logo** | Cualquier imagen (un PNG con fondo transparente queda mejor). Vacío: se dibuja uno por ti. |
| **Bandera del país** | Tu propia imagen de la bandera del país, estirada al marco de las banderas del juego. Sustituye la bandera de ese país en todo el juego (Select Team, nacionalidad de los jugadores, el encabezado del país en Database > Competition Info) mientras el mundo esté activo. Vacío: la bandera del juego. |
| **Copa** | Solo primera división. **Copa nacional**: el país tiene su propia copa, con el nombre que le des (vacío: `<liga> Cup`). El juego llena la copa de un país con su primera división y la división de debajo, y el tamaño de la copa sigue la fila Copa nacional de los Límites (8.3): el mayor tamaño que la pantalla de la copa dibuja y que cabe, así que 22 clubes dan una copa de 20, primero la primera división. Con más de 44 clubes la copa se queda solo con la primera división. Una segunda división nueva bajo un país que el juego ya tiene (Alemania, Rusia ...) también entra en la copa de ese país, detrás de los clubes de primera, cuando las rondas de la copa encajan con el número de clubes. Una nueva tercera división o inferior (League One bajo la Championship) deja la copa del país a las dos primeras divisiones del juego, como en el juego. **Supercopa (campeón contra ganador de copa)**: además, una supercopa a partido único antes de la temporada. Necesita la copa nacional. |
| **Copa de la liga** | Solo primera división. Una eliminatoria de esta liga y la de abajo, como se juega la Carabao Cup (0.2.0): un partido por ronda, también la semifinal y la final, en las semanas de la Carabao Cup: 27 de agosto, 23 de septiembre, 28 de octubre, los cuartos de final el 23 de diciembre, la semifinal el 14 de enero y la final el domingo 15 de marzo, en días propios, nunca en un día de copa nacional o europeo. Juegan tantos clubes de las dos divisiones como dibuja la pantalla de la copa, hasta 44 (20 + 24: toda la Premier League y la Championship); cuando no son 16 o 32, los clubes de esta liga pasan directamente y empiezan en la segunda ronda. Cada eliminatoria se sortea al azar. Ponle un nombre o déjalo vacío (`<liga> League Cup`). Un mundo construido antes de 0.2.0 mantiene la copa antigua de 16 a ida y vuelta con su ronda previa hasta que lo vuelves a construir; una carrera empezada antes de ese Build juega la copa antigua. |
| **Logos de las copas** | Una imagen para la copa nacional, la supercopa, la copa de la liga y los playoffs del Apertura/Clausura, cada una por separado. Vacío: se dibuja un emblema con las iniciales de la copa. |
| **Solo exhibición -- no está en la Liga Máster** | Para Kick Off y partidos amistosos: una liga histórica, leyendas y cosas así. Sus clubes nunca juegan una temporada de Master League, así que la liga va sola: sin división arriba ni abajo, sin plazas europeas, sin copas. Aun así aparece en la lista de equipos de la Master League; elige tu club en otra liga. |
| **Formación** | Cómo forman los clubes de la liga. Elige una de las formaciones que usan los clubes del juego (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; la lista dice cuántos clubes del juego la usan): cada club nuevo recibe una copia de la táctica de un club del juego con esa formación, y al construir se le coloca su mejor once. Vacío: Build elige para cada club la formación que mejor encaja con su plantilla (0.2.4; antes, un 4-2-3-1 fijo): dos delanteros fuertes juegan con dos arriba, buenos extremos con tres delanteros, tres centrales con tres o cinco atrás. El registro de Build dice qué formaciones eligió. Un club puede tener la suya (**Editar club**). |

**Nombre del mundo** (Ligas → Más → **Nombre del mundo y archivo...**) debe empezar por `_FL26`. Esa página también muestra tus ligas: después de **Construir**, su
columna **ID de la liga** muestra el id de competición de cada liga en el juego, el mismo que lleva
su archivo de logo. La columna **#** es el lugar de la liga en el orden (**Subir** / **Bajar**), y
**Select Team** dice dónde la puso el último Build: *sí*, *en lugar de* uno de los grupos del juego, o
*sin sitio (se juega)*. Un `*` ahí significa que el orden cambió desde entonces: vuelve a construir para
ver dónde va. Arrastrar una liga en la pestaña **Ligas** la mueve solo entre los puestos que ya tienen aquí las ligas de su continente (0.2.0; antes ponía todo el orden por continentes, y las ligas de Norteamérica y Oceanía quedaban siempre al final).

**Torneos de pretemporada** (Ligas → Más, o Mi mundo → Copas): eliminatorias amistosas de 4 u 8 clubes invitados en julio, antes de la temporada, emparejados en el orden en que los pones (el primero contra el segundo ...). Un club es de una liga nueva o un club del juego (su id); al menos uno tiene que ser de una liga nueva, y su país organiza el torneo. Una carrera empieza en agosto, así que el primero se juega en la segunda temporada. Cada torneo puede tener su **Logo**; vacío: se dibuja uno.

**Copas de nuestros países** (Ligas → Más, o Mi mundo → Copas, 0.2.4): las copas de tus propias ligas en una sola tabla. Para cada primera división: su copa nacional, su supercopa y su copa de la liga, cada una con su nombre y su logo. Son los mismos campos que en **Editar liga...**, sin abrir cada liga.

**Copas de los países del juego** (Ligas → Más, o Mi mundo → Copas): una copa de la liga -- la Carabao Cup, por ejemplo -- para ligas del juego. Marca **Copa de la liga** junto a una liga: ella y la liga de debajo, hasta 44 clubes, un partido por ronda desde finales de agosto hasta la final a mediados de marzo, por sorteo, con los clubes de la propia liga pasando directamente a la segunda ronda (0.2.0; la misma copa que la de una liga nueva), en días que el calendario de ligas y copas del juego deja libres. **Supercopa**, el campeón contra el ganador de la copa, solo donde el juego no tiene (Brasil, Chile, Escocia, Grecia, EE. UU.). Es una supercopa a partido único de dos clubes (0.2.4; antes salía como una eliminatoria de 16). Se juega a finales de julio; en un país de febrero a diciembre (la Supercopa de Chile, la Supercopa Rei) se juega a finales de enero, entre el campeón y el ganador de la copa de la temporada que acaba de terminar. Cuando aún no hay ganador de copa (el primer verano de una carrera nueva), o el campeón ganó también la copa, juega el subcampeón de la liga. Nombre vacío: el nombre de la liga y *League Cup* / *Super Cup*. **Logo** junto a cada nombre (0.2.0): una imagen para esa copa; sin ella, un emblema con las iniciales de la copa. Los cambios aquí necesitan **Instalar los módulos** (o Construir e instalar), un Build nuevo y una carrera nueva.

**Plazas europeas de las ligas del juego** (Ligas → Más): qué puestos de la Premier League, LaLiga, la Serie A ... van a qué competición europea. La lista muestra las plazas del juego; marca **Plazas propias para esta liga** para cambiarlas. Una liga sin marcar mantiene las del juego, una liga marcada sin filas no manda a nadie.

**Ranking UEFA** (Ligas → Más, 0.1.7): todas las ligas europeas del mundo -- las del juego y tus
primeras divisiones nuevas -- en una lista, el país más fuerte primero. Arrastra una liga (o
**Subir** / **Bajar**) para cambiar el orden, desmárcala para que no tenga plaza europea, y
**Orden de la UEFA** devuelve la lista al ranking de asociaciones de la UEFA para 2026-27. A la
derecha se ve lo que recibe cada liga, y **Aceptar** lo escribe: las plazas de la clave de la UEFA
para 2024-27 -- el puesto 1 tiene cinco plazas de Champions League, el 6 dos y una de play-off, el
30 una en la segunda ronda previa de la Champions League y tres en la de la Conference League,
etcétera, incluida la plaza del campeón de copa en la Europa League. Un mundo nunca tiene los 55
países de la UEFA, así que las plazas de los puestos que faltan van por turnos a los siguientes
clubes de las ligas más fuertes, una ronda cada vez, y todas las competiciones siguen llenas: con
doce ligas, el 6.º, 7.º y 8.º de Inglaterra van a la fase previa de la Champions League, por
ejemplo. Después de la liga 31 no queda ninguna plaza, y la lista lo dice. Cada ronda previa
admite dieciséis clubes: con los 31 puestos en un mundo, las plazas de los puestos más bajos que
pasan de esos dieciséis no reciben nada (las notas dicen cuáles; los puestos 26 y siguientes
empiezan en realidad en la primera ronda previa, que Mod Studio no tiene). Las plazas de fase
previa van a las rondas en el orden de la clave, el país más fuerte a la ronda más cercana a la
fase de liga. Después aún puedes cambiar a mano las plazas de cualquier liga (*Europa* en la
liga, *Plazas europeas de las ligas del juego*): Build usa las plazas, no el ranking.

**Plazas sudamericanas** (Ligas → Más, 0.1.7, solo lectura): para cada liga sudamericana, las
cuatro del juego y las tuyas, qué puestos van a la Copa Libertadores, a su fase previa y a la Copa
Sudamericana. Las plazas de Libertadores de las ligas del juego son las del juego (Brasil 1.º-4.º y
el campeón de la Copa do Brasil, fase previa 5.º-6.º, etcétera -- lo mismo que muestra el
Competition Info del juego); la Copa Sudamericana es de Mod Studio, así que la lista muestra
cuántos clubes manda a ella cada liga del juego con tus plazas dentro: primero tus ligas, luego
Brasil, Argentina, Chile y Colombia, un club cada una por turnos hasta llegar a 32. Un club que ya
está en la Libertadores o en su fase previa deja su sitio al siguiente de su liga. **Comprobar el
plan** escribe la misma lista siempre que el mundo tiene una plaza de Libertadores o Sudamericana.

**Nombres de las competiciones** (Ligas → Más, o Mi mundo → Copas): un nombre y un logo nuevos para las copas, supercopas y competiciones continentales del juego -- la FA Cup, la Champions League, la Libertadores ... -- y para las copas continentales que construye el mundo (CAF Champions League, Copa Confederación, AFC Champions League Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Champions League, AFC Challenge League, Supercopa CAF). Todas las fases de la competición reciben el nombre. Vacío: el del juego. Las ligas del juego se renombran en *Ligas* (elige una liga del juego).

**IDs de competiciones** (Ligas → Más): todas las competiciones del mundo del juego, ligas y copas, con su id. El juego tiene sitio para 255; Mi mundo muestra cuántas se usan.

**Orden de las ligas** (Ligas → Más, 0.2.0): el orden de los países en Select Team de la Master League y en la lista de equipos de Kick Off / Edit. *Por continente* es el orden del juego (Europa, las Américas, Asia y luego África, cada uno de la A a la Z). *Todos los países de la A a la Z* los pone a todos en una sola serie alfabética, y *Mi propio orden* te deja ordenarlos como quieras (arrastrando, o con Subir / Bajar). Las ligas de un país van juntas, primera división primero, y las competiciones de clubes, los grupos "Other" y Classic Teams van después de los países. Alemania, EE. UU. y Japón están en los grupos "Other" de Select Team, así que solo se mueven en Kick Off. Después vuelve a construir el mundo.

**Temporadas de las ligas del juego** (Ligas → Más, 0.2.0, experimental): Japón, China, Brasil, Chile y Arabia Saudí juegan de febrero a diciembre en el juego. Marca uno y sus ligas juegan de agosto a mayo como Europa: la temporada empieza en agosto, los ascensos y descensos son en verano, sus copas pasan a fechas de agosto a mayo y sus plazas continentales salen de la tabla que terminó en mayo. Una división tuya debajo de una de esas ligas la sigue. Colombia y EE. UU. juegan Apertura y Clausura y no se pueden mover. Vuelve a construir el mundo y empieza una carrera nueva.

**Clubes europeos de la primera temporada** (Ligas → Más, 0.1.8): elige a mano los clubes de la
fase de la Champions League, la Europa League y la Conference League en la primera temporada de
una carrera nueva. Tus clubes entran primero y el juego llena el resto; desde la segunda
temporada deciden las plazas europeas.

**Clubes** (una pestaña de Mi mundo): elige la liga y luego **Editar club** (nombre, abreviatura, escudo; o doble clic en el club). Todo lo demás está en **Más ▾**: **Jugadores**, **Club del juego...**, **Club NewLife...**, **Club nuevo aquí**, **Insertar club**, **Quitar club**, **Mover a otra liga...**, **Pegar nombres...**, **Cargar nombres de un archivo...** e **Importar escudos...**. Un nombre vacío pasa a ser `<liga> 01`, `<liga> 02` ...; un club
sin escudo recibe un escudo con número. Las equipaciones se toman prestadas de los clubes del
propio juego. Una equipación así es con licencia, y el modo Edit no deja cambiarla ("You cannot
edit this strip"): marca **Equipaciones simples para el modo Edición** en la pestaña Construcción
(Opciones del mundo) y los clubes nuevos no toman ninguna prestada; cada uno lleva una equipación
sencilla que Edit > Teams > Strip cambia como la de cualquier otro club, Paste Image incluido.
Con Kit Server instalado, **Equipaciones con los colores del club** (pestaña Construcción,
Opciones del mundo, activado salvo que lo desmarques, 0.2.1) crea a cada club nuevo la local, la
visitante, la tercera y la de portero en los colores de su camiseta (los de NewLife, o los del
escudo si no tiene), con el escudo en el pecho y en el pantalón, para ligas enteras a la vez al
poner el mundo en el juego. Un escudo que pongas después (Importar escudos) pasa a las
equipaciones en la siguiente activación. Un club con equipación propia de Kit Server, o solo con
el escudo numerado, no recibe ninguna. Una línea de equipación tuya en `map.txt` (una que pusiste
en la pestaña *Equipaciones*, hacia una equipación que está en la biblioteca) gana siempre: Build
no hace equipación para ese club, no le pone la equipación de un paquete y deja tu línea activada
(0.2.4; la 0.2.3 la desactivaba en cada Build cuando había una equipación de un paquete de
ligas). Los nombres conservan sus letras (FK Željezničar); la abreviatura de tres letras no lleva
tildes ni marcas, como en el juego, así que ahí Č, Ž, Đ pasan a C, Z, D. El orden de la A a la Z
de una liga en los archivos del juego pone Đakovo en la D y Šibenik en la S (0.2.4). Después de
**Construir**, el ratón sobre el nombre de un club muestra su id en el juego (**ID del club**).

**Caras del pack de caras para los jugadores nuevos** (pestaña Construcción, Opciones del mundo,
activado por defecto): cada jugador nuevo sin cara propia recibe una cara del paquete de caras de
regens que va con su nacionalidad. Desactivado: los jugadores nuevos mantienen el aspecto que les
da el juego, o el que les pongas en el modo Edit del juego. Se aplica en el siguiente Build.

**Entrenador**: en **Editar club** de un club nuevo puedes poner el nombre de su entrenador. Vacío: un nombre inventado con jugadores del país del club (un club croata recibe algo como `Tomislav Krovinović`; el mismo en cada Build), o uno numerado (`FL M0001` ...) si el juego tiene pocos jugadores de ese país. **Foto del entrenador** debajo le da un retrato (lo mismo que **Retrato del entrenador...** en la pestaña Jugadores); *Ligas* (una liga del juego) > **Editar club** la tiene también para los clubes del juego.

**Colores de las equipaciones**: **Colores de la equipación local** y **Colores de la equipación
visitante** en **Editar club**: Build presta la equipación del juego más parecida a ellos, y
**Equipaciones con los colores del club** los usa.

**Formación**: en **Editar club** de un club nuevo puedes darle una formación propia; *Como la liga* mantiene la de la liga. El campo bajo la lista muestra dónde juega cada uno.

**Capitán y lanzadores** (0.2.4): Build da a cada club y selección que no los tiene un capitán (un
jugador con la habilidad Captaincy o, si no hay, el más fuerte y con más experiencia) y sus
lanzadores de penaltis, faltas y córneres, entre los jugadores de campo del once inicial. Un club
del juego que ya los tiene los conserva. Un mundo construido antes de la 0.2.4 tiene al portero
como capitán en todas partes: vuelve a construirlo y empieza una carrera nueva.

**Estadio local** (0.1.7): en **Editar club**, un estadio de la biblioteca de Stadium Server para el club; la ranura y el nombre se rellenan desde la carpeta, cambia el nombre si quieres. Se escribe en el `map_teams.txt` de Stadium Server al poner el mundo en el juego (y al construir otra vez el mundo del juego), así que nunca hay que buscar el id de un club nuevo. Una línea tuya para el mismo club se desactiva mientras tanto, y se activa otra vez cuando el club ya no tiene estadio aquí. *Ligas* (una liga del juego) > **Editar club** lo tiene también para los clubes del juego. Tiene que estar instalado Stadium Server (la pestaña *Estadios*) o el módulo de estadios propio de SPFL26 (`common\stadiums.lua` con su carpeta `content\stadiums`): desde 0.1.8 Mod Studio escribe ahí cuando Stadium Server no está instalado. Un estadio del juego elegido como estadio local se ilumina bien en el partido (0.2.4; antes podía quedar completamente oscuro): vuelve a construir un mundo hecho antes.

**Clubes que el juego ya tiene.** Un puesto de una liga nueva puede tener uno de los clubes del
juego en lugar de uno nuevo: selecciona el puesto, luego **Más → Club del juego...**, y busca por
nombre, abreviatura o ID del equipo (**Solo clubes sin liga** acota la lista). La ventana **Club
del juego** dice bajo la lista dónde juega el club. El club conserva su nombre, escudo,
equipaciones, entrenador y jugadores, y juega solo en tu liga. Si juega algo en el juego (una
liga, una copa, la Europa League ...), eliges quién ocupa allí su lugar: **Su lugar pasa a un club
del juego que no juega nada:** (elige uno de la lista), o **Su lugar pasa a un club nuevo,
llamado:** (escribe un nombre). **Conserva sus plazas en competiciones continentales** (0.1.8, #84) le deja seguir jugando la Champions League, la Libertadores o la AFC Champions League en la que está: un club que en el juego solo juega el continente simplemente se muda, y uno que también juega una liga del juego entrega solo la liga y las copas al club que elijas. Desde la segunda temporada, las plazas de tu liga deciden quién va. Un torneo de pretemporada (las *Pre-season friendly Cups* de SPFL26) no cuenta: el club lo sigue jugando, como los clubes de la Premier League (0.1.7). **Editar club** en un club del juego cambia su nombre, escudo, foto del entrenador y estadio, como en *Ligas* para una liga del juego (0.1.7). Así ninguna competición del juego cambia su
número de clubes; las ligas del juego solo mantienen sus fechas con el número para el que se
hicieron. Las selecciones, los equipos clásicos y por defecto y los clubes con menos de 18
jugadores no se pueden elegir. **Club nuevo aquí** (en **Más**) devuelve el puesto a un club
nuevo; sale en gris salvo que el club elegido sea un club del juego en ese puesto (0.2.4). El club
ya no aparece en los grupos *Other ... clubs* de la Master League.

**Club NewLife...** (0.1.8, #83, en **Más**) pone clubes de la NewLife Database, con sus plantillas, en el puesto seleccionado y los siguientes: marca uno o más clubes (busca por club o por liga) y cada uno ocupa su puesto en orden. Así una liga hecha a mano recibe clubes reales. Usa la carpeta de NewLife que abriste la última vez; la primera vez, ábrela en la página *NewLife Database*.

**Insertar club** y **Quitar club** añaden un puesto antes del club seleccionado o lo quitan (de 10
a 24 clubes); nombres, escudos, entrenadores y cambios de jugadores van con sus clubes. Revisa las
plazas europeas de la liga y vuelve a **Construir**. Cualquier cambio en los clubes de una liga
necesita una **carrera nueva**.

**Mover a otra liga...** (0.1.7) lleva el club nuevo seleccionado al final de otra liga nueva, con su nombre, abreviatura, escudo, entrenador, formación, equipaciones, id de NewLife y cambios de jugadores; la liga que deja se queda con un club menos. Un club del juego se mueve con **Club del juego**: quítalo de una liga y ponlo en la otra.

**Las ligas del juego** (elige una en *Ligas*): un nombre o logo nuevo, y luego **Conservar cambios de la liga** (**Deshacer cambios de la liga** lo deshace); **Editar club** para el escudo, el nombre, la foto del entrenador y el estadio de un club. La lista de Clubes muestra cuántos jugadores tendrá cada club: su plantilla, menos los jugadores quitados o fichados por otro club, más los añadidos y fichados. Un cambio así se guarda enseguida en el archivo de tu mundo, como cualquier otro cambio.

**Importar escudos...** (0.1.8, *Clubes* → Más; para las ligas del juego *Ligas* → Más): escudos para muchos clubes a la vez. Elige una carpeta de imágenes; cada una se empareja con un club por el nombre del archivo -- el nombre del club (`Alianza Lima.png`, `alianza_lima_r_l.png`) o su ID de equipo (`2287.png`, el `e_2287_r.png` de los packs de escudos). Un nombre solo empareja con palabras enteras, y una selección solo toma una imagen por su ID de equipo (0.2.4; antes "termalica" podía ir a Malí). La lista muestra cada emparejamiento con una marca; desmarca uno erróneo antes de **Aceptar**. Un club que ya tiene escudo lo conserva, salvo que esté marcado **Reemplazar los escudos ya puestos**. Las imágenes se quedan en esa carpeta y Build las lee de ahí, así que guárdala. (Emparejar por nombre es una idea del script de escudos de Xxspedd.)

**Intercambiar liga con un club...** (0.1.7, *Ligas*, una liga del juego → Más): dos clubes de las ligas del juego intercambian sus plazas -- un ascendido por un descendido, un club de la liga de un país por uno de otro. Cada uno ocupa las plazas del otro en la liga, las copas y las competiciones europeas, así que cada liga del juego mantiene su número de clubes. Un club que juega en una liga nueva de tu mundo no puede intercambiarse también. **Deshacer cambios del club** quita el intercambio. Luego **Construir** otra vez y empieza una carrera nueva.

> **Archivo Edit.** Si la carpeta de partidas guardadas del juego tiene un archivo Edit
> (`EDIT00000000`), este anula los nombres de los clubes. Muévelo a otro sitio para ver tus nombres.

### Jugadores

**Jugadores** (una pestaña de Mi mundo) cambia la plantilla de cualquier club: los clubes nuevos de tu mundo y los del
propio juego. Elige un club (o **Más → Jugadores** en Clubes) y luego un jugador:

- **Nombre**, **dorsal**, **posición** y las posiciones en las que puede jugar (A = natural,
  B = puede jugar ahí), pie hábil, altura, peso, edad, nacionalidad, estilo de juego;
- todas las **capacidades** y **habilidades** (los nombres son los del propio juego);
- **Valoración**: la valoración de la lista, hecha de las capacidades en las que se apoya la
  posición. Al cambiarla, cada capacidad del jugador se mueve lo mismo. Un jugador de un club
  nuevo no tiene nombre hasta que Build le da uno con número (FL P00001 ...); escribe uno en
  **Nombre** para darle el tuyo; desde 0.2.0 esa plantilla empieza al nivel de su división (unos
  72 en primera, hasta 57 de la quinta división hacia abajo);
- **Cara**: **Elegir...** una carpeta de cara (sección 8.1). **Borrar** devuelve la cara del juego.
  Un jugador nuevo sin ella recibe una cara del paquete de caras de regens que va con su
  nacionalidad, con su retrato (0.1.5.5, con los módulos instalados y `fl26regen` activado,
  sección 5). Una cara hecha para otro jugador trae también el aspecto de su cuerpo, así que
  brazos y piernas tienen el color de piel de esa cara (0.1.9);
- **Retrato**: **Elegir...** una imagen (PNG o JPG) para el retrato pequeño del jugador en las listas
  de la plantilla, sin cara propia. Build la deja en 180 x 180; tiene prioridad sobre el retrato de
  una carpeta de cara;
- **Subir en el orden / Bajar en el orden**: el orden de la plantilla. Los primeros once son
  titulares;
- **Añadir jugador** (una copia del jugador que elijas, con un id nuevo; solo clubes del juego),
  **Quitar del club** (púlsalo otra vez para deshacerlo). Un club nuevo conserva al menos 18
  jugadores, contando los fichados para él; los clubes del juego no tienen mínimo;
- **Mejor once** pone al jugador más fuerte en cada puesto (un jugador que puede jugar ahí
  pero está registrado en otro puesto cuenta con 6 menos, y se queda para su puesto cuando
  este quedaría sin nadie); **Nivel de la plantilla...** (en **Más**) sube o
  baja cada capacidad de toda la plantilla;
- **Campo** (clubes nuevos): los once primeros en la formación del club. Arrastra un jugador de la
  lista a un puesto, o arrastra un puesto sobre otro para cambiar a los dos; un clic en un puesto
  selecciona al jugador que está ahí. Aquí se ve la formación que Build eligió para el club;
  cuando cambias su orden, el club mantiene esa formación;
- **Exportar CSV... / Importar CSV...** (en **Más**): edita una plantilla en una hoja de cálculo. Primero
  exporta, cambia las celdas y vuelve a importar las mismas columnas.
- **Importar una plantilla desde una tabla...** (en **Más**): cualquier tabla de jugadores se convierte en
  la plantilla del club -- escrita a mano, una lista copiada de una web, o una exportación de otro
  juego de fútbol. Las columnas se reconocen por su nombre (nombre, posición, edad o fecha de
  nacimiento, nacionalidad, altura, pie, dorsal, valoración general y cualquier valoración) y se
  muestran para corregir la que esté mal. Lo que la tabla no tiene sale de los jugadores del juego
  de la misma posición y valoración; las valoraciones en una escala de 1-20 se estiran al 40-99
  del juego. Los jugadores de la tabla ocupan las plazas del club en orden de plantilla: un club
  nuevo mantiene sus 30 plazas (con menos jugadores, los demás se van, hasta 18), un club del
  juego gana o pierde jugadores para cuadrar.

Cada cambio se escribe en el mundo cuando pulsas **Construir**; los archivos del juego se quedan
como están. **Deshacer los cambios de este jugador** y **Deshacer todos los cambios de este club**
vuelven a lo del juego.

La lista de clubes también tiene **Selecciones nacionales** y **Otros clubes (sin liga)**: los equipos que el juego tiene fuera de toda liga (selecciones, clubes que solo juegan una copa o una competición continental). Sus jugadores se editan igual.

#### Traspasos, selecciones, ID, el retrato del entrenador

- **Fichar jugadores...** (un club): una lista de todos los jugadores del juego y de tus clubes
  nuevos, con filtro de nacionalidad y búsqueda por nombre; elige varios con Ctrl o Mayús. Pasan
  a este club y su antiguo club los pierde (un traspaso). **Traspasar a...** hace lo mismo desde
  el otro lado: el jugador seleccionado pasa al club que elijas. La lista muestra *de: ...* en el
  club que lo recibe y *a: ...* en el club que deja; **Quitar del club** en cualquiera de las dos
  filas anula el traspaso. Un club tiene como mucho 40 jugadores. Si un club acaba con más de 40
  (una selección con más de 26), Build se queda con sus 40 primeros y sigue, y el registro de
  Build nombra el club y los jugadores que quedaron fuera; si el club está dos veces en tu mundo,
  nombra las dos ligas.
- **Convocar jugadores...** (una selección: elige *Selecciones nacionales* en la lista de ligas): la lista
  se abre en el país de la selección. Los jugadores entran en la selección **y siguen en sus
  clubes**, como en el juego. **Quitar del club** saca al jugador de la selección (no de su
  club). Una selección tiene como mucho 26 jugadores; un jugador está en una sola selección a la
  vez. Tu convocatoria se escribe en los datos del juego, pero en una carrera de la Master League
  el juego elige sus propias selecciones, así que allí tus convocatorias no se mantienen.
- Un jugador que llega va al final del orden de la plantilla con un dorsal libre; la plantilla
  que deja cierra su orden.
- Columna **ID del jugador**: el id de cada jugador -- el del juego, el que escribiste o el que el
  último **Build** dio a un jugador nuevo (haz un Build antes de crear minifaces o caras para
  jugadores nuevos). **Exportar CSV...** lo escribe como `player_id`; Importar CSV ignora esa columna.
- **ID del club** (junto al club) e **ID del jugador** (pestaña Lo básico): solo para tus clubes y
  jugadores **nuevos**. Vacío = el siguiente ID libre en el Build. Escribe uno cuando un pack de
  equipaciones, escudo o caras se hizo para un ID concreto. ID de club: desde el primero tras los
  clubes del juego (71578) hasta 81919; ID de jugador: por encima del más alto del juego hasta
  399999; nunca uno que ya tenga el juego u otro club o jugador nuevo. El ID se usa en todo lo
  que el mundo escribe del club o del jugador (plantillas, competiciones, equipaciones, escudos,
  entrenador, caras). Los clubes y jugadores del juego conservan sus ID: sus equipaciones, caras
  y tus partidas guardadas dependen de ellos.
- **Los jugadores conservan su ID cuando vuelves a construir** (0.2.4). Build encuentra a cada
  jugador propio del mundo por quién es (su id de NewLife o, si no, su nombre y fecha de
  nacimiento) antes que por su puesto en la plantilla, así que un jugador que subió en la
  plantilla o cambió de club conserva su ID, y una carrera antigua no lo muestra como si fuera
  otro.
- **Retrato del entrenador...**: un PNG o JPG para el entrenador del club. Build lo deja en
  256 x 256 y lo pone en `common/render/symbol/coach/coach_<ID del entrenador>.png`, donde el
  juego guarda los retratos de entrenadores. Púlsalo otra vez para quitar la imagen.

### 8.1 Caras

Un mod de caras es una carpeta así (tal como las comparten quienes hacen caras):

```
<cualquier nombre>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (o <id>.dds, opcional)
```

Elige esa carpeta para un jugador. Al **Construir**, la cara se copia en el mundo y se asigna al
jugador, así que funciona para un jugador nuevo cuyo id no existía cuando se hizo la cara, y
nunca reemplaza una cara del juego. Sin retrato, la foto pequeña del jugador en los menús se queda
como una silueta vacía; la cara en sí se ve igual. Una carpeta con más de una cara dentro se
rechaza: elige la cara concreta que quieres.

### 8.2 Construir, activar, jugar

**Conserva el Team.bin del mundo.** Está en la carpeta del mundo y guarda los clubes y los play-offs del mundo. Si lo cambias por el Team.bin del juego, desaparecen, y las alineaciones parecen arregladas solo porque ya no están los clubes (GitHub #75). Mejor vuelve a construir el mundo.

**Construcción** es la primera pestaña de **2. Mi mundo**. Una nota arriba dice que es para
modders: para jugar un modpack listo no la necesitas. Debajo: el archivo donde se guarda tu mundo,
los botones **Mundo nuevo**, **Abrir un mundo...** y **Añadir ligas** (para un mundo tuyo), y el
botón grande **Construir e instalar**.

**Construir e instalar** hace 0, 2 y 3 de abajo en un solo clic, y luego muestra lo que queda por
hacer: una ventana **Construcción terminada** con una marca en **Mundo construido**, **Ligas y
clubes**, **Módulos instalados y activados** y **En el juego**, y en **Antes de jugar** un
recordatorio de empezar una Master League nueva. También puede **Apartar el guardado de Edit**
(un guardado de Edit de antes del Build esconde los nombres y plantillas nuevos) y **Cerrar el
juego**. La tarjeta de Inicio tiene un botón **Ir a Construcción** que te trae aquí. Mientras el
mundo se construye, la línea de estado de Mi mundo y la barra de abajo muestran el tiempo que
lleva y el paso en el que está (`Construyendo... 3:12 · squads: filling them`), y la ventana se
puede seguir usando. O paso a paso, en **Paso a paso, y Exportar el mundo** de la pestaña
**Construcción**:

0. **Instalar los módulos** — una vez, y de nuevo tras una versión nueva del programa. Los
   archivos que reemplaza se guardan en **Puntos de restauración**.
1. **Comprobar el plan** — qué se va a crear; no se escribe nada.
2. **Construir el mundo**.
3. **Activarlo** — lo pone en el juego (el mundo activo en `sider.ini`).
4. Inicia el juego, vuelve y pulsa **Tras iniciar: comprobar**. Lee `sider.log` y dice, módulo a
   módulo, si el mundo se ha cargado.

**Activar** en la tarjeta de otro mundo en Mi mundo hace el paso 3 para ese mundo (y cambia la
carpeta de partidas, sección 3.1). El mundo del juego muestra en su lugar **● Activo**. Empieza
una Master League nueva tras activar un mundo distinto.

**Un logo o escudo nuevo se construye en segundos** (0.2.4). Cuando desde el último Build solo
cambiaron imágenes (el logo de una liga o de una copa, el escudo de un club, la bandera de un
país), Build dibuja solo esas otra vez y deja el resto del mundo como está. Cualquier otro cambio
(un nombre, un club, un jugador) es un Build completo. Un mundo de un zip se construye entero una
vez en tu PC; después, sus cambios de imágenes también son rápidos.

**Un mundo listo no se construye aquí** (0.2.4). Un mundo instalado desde un zip ya está
construido, y Build lo sustituiría por el mundo abierto en Mod Studio. Así que mientras un mundo
listo está en el juego, los pasos de Build salen en gris con una nota, Inicio dice **Listo para
jugar**, y Construcción explica qué hacer en su lugar: pulsar **Iniciar el juego**, o poner antes
tu propio mundo en el juego (**Activar** en su tarjeta). Otro mundo (NewLife, un mundo nuevo) se
puede construir mientras el listo está activado: Build pregunta antes y avisa de que desactiva el
mundo listo; **Activar** en su tarjeta lo devuelve, con sus carreras. Para cambiar el propio
mundo listo: **Hacerlo editable...** (sección 3.1).

**Incluir la Liga Conferencia** (pestaña Construcción, en Opciones del mundo, activado por defecto)
construye también la Liga Conferencia: una fase de liga de 36 clubes y un play-off en febrero,
como las otras dos. La Liga de Campeones y la Liga Europa reciben su fase de liga de 36 y su
play-off de febrero en cualquier caso. Desactivado: sin Liga Conferencia. (Mod Studio 0.1.3 y
anteriores dejaban la Liga de Campeones y la Liga Europa en los grupos de cuatro del juego cuando
estaba desactivado, y el mod no puede llevarlos -- se rompían; Comprobaciones marca ese mundo:
vuelve a construirlo.) **Logo de la Conference League** al lado: tu propia imagen para ella;
vacío: se dibuja un emblema UECL (el juego no tiene ninguno). **Nombre de la Conference League**
debajo: cómo la llama el juego, *FL Conference League* si está vacío (escribe *UEFA Conference
League* si quieres); un nombre nuevo necesita construir el mundo otra vez. Los dos los usa
también **Construir solo las copas europeas...**.

> **Plazas europeas.** Las plazas que das a tus ligas van después de las que tienen las ligas del
> propio juego. Cada competición admite 36 clubes; las plazas más allá de la 36.ª no reciben nada,
> y **Comprobar el plan** lo avisa. Las ligas nuevas sin plazas no mandan a nadie a Europa, e
> Inicio avisa de ello. Los campeones van primero: los ganadores de la Champions League y de la
> Europa League ocupan dos de las plazas directas de la Champions League, y el de la Conference
> League una de la Europa League. El sorteo de la fase de liga sigue las reglas de la UEFA:
> ningún club se enfrenta a un club de su propio país, y como mucho dos de sus rivales son de un
> mismo país distinto.
>
> **La fase previa de agosto.** Una plaza de *(fase previa)* mete al club en la fase previa de
> agosto de esa competición: hasta tres rondas (0.1.7) -- la segunda ronda previa (días 220 y
> 225), la tercera (229 y 236) y el play-off (243 y 250; el de la Champions League 244 y 251) --,
> cada una de 16 clubes a ida y vuelta; los ocho equipos más fuertes son cabezas de serie (vuelta
> en casa) y dos clubes del mismo país nunca se cruzan. Los ganadores pasan a la ronda siguiente,
> y del play-off a la fase de liga. Los perdedores bajan como en la UEFA: en la *Champions League
> (fase previa)*, los del play-off a la Europa League, los de la tercera ronda al play-off de la
> Europa League, los de la segunda a la tercera ronda de la Europa League; la *Europa League (fase
> previa)* igual hacia la Conference League; los perdedores de la *Conference League (fase
> previa)* quedan fuera. Las primeras plazas de la lista van al play-off, las siguientes a las
> rondas anteriores. Cuántas rondas tiene un mundo depende de sus plazas, y cada ronda de la
> Conference League pide 8 clubes más: 116 plazas en Europa para los tres play-offs solos, 132
> para las nueve rondas. Con las plazas del propio juego solo hay play-offs; el resumen de Build
> dice qué rondas tiene el mundo (*fase previa de agosto*). Cada play-off quita 8 plazas directas
> a las competiciones a las que van sus ganadores y perdedores: con los tres, la Champions League
> admite 28 clubes directos, la Europa League y la Conference League 20 cada una. Una plaza más
> allá se juega en la fase previa de esa competición. Las plazas de fase previa de tus ligas van
> antes que las del juego (Portugal, Escocia, Grecia, Dinamarca ...).

Después **empieza una carrera nueva de Master League** (o Become a Legend). Las ligas nuevas están
bajo su país en Select Team y Kick Off. En las listas de Kick Off y Edit un país asiático nuevo va
antes de *Other Clubs (Asia)*, uno sudamericano junto a los del juego (después de Colombia, antes
de la MLS, 0.1.7), uno de la CONCACAF después de la MLS, y los africanos y de Oceanía
(el juego no tiene sección para ellos) después de Asia.

> **Copas de otros continentes.** Cuando tus ligas mandan clubes a la CAF Champions League, la
> Copa Confederación CAF, la AFC Champions League Two, la AFC Challenge League, la Copa
> Sudamericana, la CONCACAF Champions Cup o la OFC Champions League (las tres últimas, nuevas en
> 0.2.0), **Construir** crea también esas copas. Cada una tiene 32, 16, 8 o 4 clubes: primero
> las plazas de tus ligas, luego la completan las ligas del juego de ese continente (Asia,
> Sudamérica, y la MLS para la de la CONCACAF); para la AFC Challenge League son del 11.º al
> 14.º de la J1 League, del 10.º al 13.º de la Superliga china y del 11.º al 14.º de la Saudi
> Pro League. Con 8 o más se juegan grupos de cuatro y luego eliminatorias; con menos de 8,
> solo eliminatorias. La CONCACAF Champions Cup es siempre por eliminatorias, de 16 clubes como
> mucho, como la real, y dos clubes de una misma liga no se cruzan en su primera ronda cuando se
> puede evitar. Se llenan a finales de agosto, con las tablas de las ligas. Un club que ya juega
> la Copa Libertadores, su fase previa o la AFC Champions League no entra en su sorteo. Una copa
> de la CAF o de la OFC con menos de 4 plazas toma primero las plazas de la siguiente copa de la
> CAF (con dos y dos, la CAF Champions League se queda las cuatro), y luego los siguientes
> puestos de tus ligas. **Supercopa de la CAF** (pestaña Construcción, Opciones del mundo,
> activada por defecto) enfrenta a los ganadores de las dos copas de la CAF en un partido a
> finales de julio, desde la segunda temporada de la carrera.
>
> Una liga que puede mandar un club a la Copa Libertadores, a la AFC Champions League o al
> Mundial de Clubes deja libres sus días de partido (0.2.4): no hay jornada de liga el día antes
> ni el día después.

> **Sorteo de la copa nacional** (pestaña Construcción, Opciones del mundo) decide cómo se sortean
> las copas nacionales de tus ligas. *Con cabezas de serie* (por defecto): los clubes de primera
> división pasan directamente y juegan las rondas finales, se reparten por igual entre las dos
> mitades del cuadro y en las primeras rondas se cruzan con clubes de ligas inferiores en lugar
> de entre ellos. *Aleatorio*: un sorteo a ciegas. *Desactivado*: el juego llena el cuadro en el
> orden de la lista, lo que pone a todos los clubes fuertes en un mismo lado. En el archivo del
> mundo es la línea `cupdraw seeded|random|off`; `cupdraw <cup regulation> seeded|random|off`
> ajusta una sola copa.

> **Las partidas guardadas pertenecen a un mundo.** Una carrera guardada con un mundo en el juego
> necesita ese mismo mundo para cargarse. Con **Cada mundo guarda sus propias carreras** activado
> (por defecto, sección 3.1), Mod Studio mantiene separadas las carreras de cada mundo por ti.

**Tu mundo se guarda solo** un momento después de cada cambio (la barra de abajo dice **Tu mundo
está guardado**): en su propio archivo `.json` cuando lo tiene, si no en
`%APPDATA%\FL26ModStudio\recipes\<mundo>.json`, y Mod Studio lo vuelve a abrir al iniciarse.
**Archivo → Guardar tu mundo como...** guarda una copia con otro nombre, **Archivo → Abrir un
mundo...** recupera uno y **Archivo → Mundo nuevo** empieza uno vacío.

**Construir solo las copas europeas...** (pestaña Construcción, Opciones del mundo; **Solo las copas europeas...** en Inicio) construye un mundo solo con la nueva
Champions League y Europa League -- fase liga de 36 y el play-off de febrero -- y la Liga Conferencia cuando **Incluir la Liga Conferencia** está marcado. Sin ligas nuevas; los clubes y ligas
del juego quedan como están y tu mundo no cambia. Pide un nombre de mundo (`_FL26Euro` por
defecto), lo construye y ofrece activarlo. Solo puede estar un mundo en el juego, así que sustituye a
un mundo con ligas nuevas: un mundo con ligas nuevas ya tiene el formato nuevo.

> **Ligas de exhibición y Master League.** Una liga marcada *Solo exhibición* nunca juega una
> temporada de Master League, pero el juego tiene una sola lista de equipos para Kick Off y
> Master League, así que sus clubes siguen apareciendo al elegir club para una carrera nueva. No
> empieces una carrera con uno de ellos. **Comprobar el plan** y **Construir** lo avisan.

### 8.3 Límites

| | |
|---|---|
| Ligas nuevas por mundo | Sin número fijo. Cada liga, copa y supercopa del mundo ocupa una de las 255 competiciones del juego (el propio juego usa unas 90); **2. Mi mundo** muestra cuántas se usan. Nuestro mundo de prueba juega 86 ligas nuevas. |
| Países nuevos | 99 |
| Clubes por liga | 10 – 24 |
| Clubes nuevos en total | unos 1500 (la línea de abajo de la página NewLife Database dice cuántos caben en tu juego) |
| Veces que se enfrentan los clubes | 1 – 4 |
| Ligas que se dividen | 2 por mundo |
| Divisiones en un país | hasta la 7.ª |
| Jugadores por club nuevo | 30 al principio (un mundo muy grande recibe plantillas más pequeñas, nunca de menos de 22); quita hasta dejar 18; con fichajes, hasta 40 |
| Jugadores por selección | 26 |
| Copa nacional | la primera división y la de debajo, hasta 44 clubes. Hasta 32 los tamaños son 2-16, 18, 20, 24, 28, 30 y 32 -- el mayor que cabe (22 clubes dan una copa de 20); de 33 a 43 se quedan en 32; 44 o el tamaño de una copa del juego se queda; más de 44: solo la primera división |

### 8.4 NewLife Database: clubes y jugadores reales

La NewLife Database es una descarga aparte con clubes y jugadores reales para ligas nuevas:
nombres, fechas de nacimiento, posiciones y valoraciones en la escala del juego, y los colores de
los clubes. Cada club y jugador tiene su propio ID, el mismo en todas las versiones de la base.
No está en GitHub: descárgala del canal NewLife de nuestro [Discord](https://discord.gg/StQqtk3G3M).
Viene en partes, una por continente (uno grande en varias), más *Free agents*, cada una de menos
de 10 MB. Descarga solo las partes que quieras.

1. Pon las partes descargadas en una carpeta. No las descomprimas: Mod Studio lee los zip tal
   cual. (Son zip LZMA: 7-Zip los abre, el visor de zip de Windows no.)
2. **2. Mi mundo → NewLife Database** (el botón a la derecha de las pestañas), luego **Abrir
   NewLife Database...** y elige esa carpeta. (O suelta la carpeta en **+ Añadir...**.) La lista
   muestra todas las ligas de esas partes: país, clubes, clubes que el juego ya tiene (*En el
   juego*), jugadores y nivel. Haz clic en una liga para ver sus clubes. Un clic en la cabecera
   de una columna (Liga, País, Clubes, Jugadores, Nivel) ordena por ella, otro clic invierte el
   orden (0.2.0); la lista se abre ordenada por país.
3. Selecciona una o varias ligas (Ctrl o Mayús para más) y pulsa **Agregar a tu mundo**. Cada una
   se convierte en una liga nueva con sus clubes y sus plantillas, primera división de su país.
   Cambia su división, formato, plazas europeas y lo demás en *Ligas*, como cualquier otra.
4. **Construir e instalar** y empieza una carrera nueva (sección 8.2).

- **Tu propia composición** (0.1.7): desmarca un club en la lista de la derecha para dejarlo
  fuera, y **Añadir un club de otra liga...** trae clubes de cualquier liga de la versión -- la
  primera división de esta temporada es la del año pasado con dos ascendidos, por ejemplo. La
  fila de la liga lleva un `*`. Un club solo puede estar en una liga de tu mundo. Si ya está en
  una de tus ligas con otro nombre, el mensaje nombra esa liga y el nombre que tiene allí.
- Una liga admite de 10 a 24 clubes, sus clubes nuevos y los del juego juntos; las demás salen en gris. Una liga que ya es del juego (la Premier League, la Championship ...) también sale en gris (0.1.9): ya está en el juego, llévala a la temporada de NewLife con **Más → Llevar las ligas del juego a esta temporada...** más abajo. La línea de abajo cuenta los clubes
  nuevos de tu mundo frente al número que admite el juego.
- Los clubes que el juego ya tiene entran en la liga nueva como clubes del juego (sección 8,
  *Clubes que el juego ya tiene*), en sus últimos puestos, con su nombre, escudo, equipaciones y
  jugadores. Uno que además juega una competición del juego (el Basilea y el Young Boys juegan la
  Europa League) necesita el club que ocupa su lugar allí: *Clubes*, elígelo, **Más → Club del
  juego...**. Hasta entonces Build dice cuáles son. Un club cuya única competición del juego es
  continental (el Ludogorets en la fase previa de la Champions League) la sigue jugando solo
  (0.1.9).
- Un jugador que el juego ya tiene (el mismo jugador con el mismo nombre, por ejemplo Urbański en
  el Górnik en el juego y en el Legia en NewLife) se va al club NewLife en vez de crearse por
  segunda vez (0.1.7): conserva su cara, nombre e ID y toma la posición y las valoraciones de
  NewLife. Se queda donde está si su club antiguo bajara de 18 jugadores o si una liga anterior ya lo
  tiene; entonces queda fuera del club de NewLife, sin copia (0.1.8).
- Un club NewLife recibe un ID de mundo propio (0.1.8), en el bloque que el juego lee para los
  clubes, detrás de los ID que el constructor da a los suyos. El ratón sobre su nombre en
  *Clubes* lo muestra (**ID del club**), y el `map.txt` del Kit Server va con él. Un mundo hecho
  antes de 0.1.8 hay que construirlo de nuevo y empezar una carrera nueva para que las
  equipaciones le sigan. Desde 0.1.8 un club conserva el ID de su primer Build (tu mundo lo
  recuerda): quitar, añadir o actualizar otra liga ya no lo mueve.
- **Una versión más nueva de NewLife** (0.1.8): pon sus partes en una carpeta (sin mezclarlas con
  las antiguas), **Abrir NewLife Database...** en esa carpeta y pulsa **Más → Actualizar mis ligas
  a esta versión**. Cada liga añadida desde una versión anterior aparece con lo que cambia (*16
  clubes ahora, 18 en NewLife 1.3 (5 nuevos, 3 que no están)*) y una casilla **Mantener mis
  clubes**: marcada, la liga mantiene sus clubes; sin marcar, recibe los clubes que tiene en la
  nueva versión. En los dos casos las plantillas vienen de la nueva versión, y la liga mantiene
  su nombre, división, formato, plazas europeas y copas; un club que se queda conserva su
  entrenador y el escudo que elegiste, y los clubes tuyos que pusiste en la liga se quedan. Las
  capacidades, posiciones y lo demás de las plantillas vienen de la nueva versión; una cara que
  enlazaste o un retrato que elegiste en *Jugadores* se queda con un jugador que sigue en el club
  (0.2.0, #111). Un club del juego cuyo puesto pasó a otro club sigue siendo un club nuevo en tu
  liga (0.2.4). Después Build y carrera nueva.
- **Las propias ligas del juego en la temporada de NewLife** (0.1.8): con una NewLife Database
  abierta, pulsa **Más → Llevar las ligas del juego a esta temporada...**. Cada liga del juego que
  tiene la versión aparece con lo que le pasa, cada una con su casilla. Un club que subió o bajó
  entre dos ligas del juego intercambia su sitio con uno que va en sentido contrario (el Burnley
  a la Championship, el Coventry a la Premier League), como *Intercambiar liga con un club...*.
  Un club que bajó fuera de las ligas del juego (el Leicester a la League One) pasa a ser el club
  que subió en su lugar (el Bolton): nombre, abreviatura, escudo y plantilla; su equipación,
  estadio y entrenador se mantienen. Cuando la base no tiene escudo para ese club, el puesto
  recibe el blasón de la camiseta del club nuevo (0.2.4). Cada club de las ligas marcadas recibe
  su plantilla de NewLife: los jugadores que el juego tiene llegan desde su club antiguo, los que
  no tiene se añaden, y los jugadores que NewLife tiene en otro club se van. Un jugador que
  NewLife aún tiene en este club se queda, mientras el club tenga sitio (40 como mucho; 0.2.4);
  el registro de Build nombra a quien no tuvo sitio. Las valoraciones se pasan a la escala del
  juego, medida con los jugadores que tienen los dos, así que una estrella queda donde la valora
  el juego (0.2.0; antes, la parte alta quedaba de 2 a 4 puntos más arriba). Las ligas mantienen
  su número de clubes, su formato y sus copas. Los clubes que ya cambiaste a mano (un
  intercambio, un nombre, un club de una liga nueva, cambios de jugadores) se quedan como están.
  Hacerlo de nuevo con una versión más nueva reemplaza lo que hizo la anterior; **Más → Deshacer
  las ligas del juego** lo quita todo. Build y carrera nueva.
- Un club NewLife recibe un escudo en forma de blasón con sus colores y la equipación del juego
  de colores más parecidos, hasta que le pongas los tuyos (**Editar club**).

## 9. Paquetes de ligas: comparte una liga entera

Un modder crea una liga una vez — clubes, nombres, escudos, logos, plantillas, caras — y comparte
**un solo archivo `.fl26pack`**. Cualquiera lo añade a su propio mundo y construye.

La página **Paquetes de ligas** está en **2. Mi mundo → Más ▾ → Paquetes de ligas**. Muestra los
paquetes de tu mundo, con **Añadir un paquete...**, **Crear un paquete...** y **Quitar de tu
mundo**.

**Crear un paquete** (**Crear un paquete...** en esa página, o **Archivo → Crear un paquete de
ligas...**):

1. Nombre, autor, versión y una descripción corta.
2. Marca las ligas que van dentro (**Seleccionar todo** / **No seleccionar ninguno** encima de
   la lista). Una liga que está debajo de otra liga nueva debe ir con ella.
3. Si quieres, **también mis cambios en las ligas, clubes y jugadores del propio juego**.
4. **Qué va dentro** (0.1.8): todo viene marcado; desmarca lo que no quieras compartir -- **Plantillas**,
   **Caras y retratos de jugadores**, **Escudos y logos de ligas**, **Entrenadores**, **Colores de las
   equipaciones**, **Estadios locales** (la línea de Stadium Server, no el estadio en sí) y (0.2.1)
   **Equipaciones** (las de Kit Server de los clubes) y **Marcadores** (el de Scoreboard Server de
   cada liga). Las equipaciones y los marcadores se toman de tu juego tal como está el mundo ahora:
   lo que kit-server\map.txt y scoreboard-server\map_competitions.txt dan a sus clubes y ligas. Un
   paquete sin plantillas va encima de una base de plantillas que se actualiza sola, como NewLife,
   sin devolver las plantillas antiguas.
5. **Guardar el paquete...**. El archivo (`.fl26pack`) lleva las imágenes, las caras, las
   equipaciones y los marcadores, no rutas de tu ordenador. Quien lo añade los recibe en su sitio,
   con sus propios ids de equipos y ligas, al construir (hace falta Kit Server / Scoreboard
   Server); un club al que puso una línea de equipación propia en la pestaña *Equipaciones*
   conserva esa equipación (0.2.4), y la equipación de un paquete se queda con su club cuando se
   quita, inserta o mueve un club, o la liga se actualiza a una NewLife más nueva. Las
   equipaciones suman unos 10 MB por liga y un marcador unos 7 MB, así que un paquete así suele
   pasar el límite de 10 MB de Discord: compártelo por un servicio en la nube (Google Drive,
   Dropbox, MEGA ...); el programa lo avisa si el archivo es mayor.

**Añadir un paquete** (**Añadir un paquete...** en esa página, **Añadir un paquete de ligas** en
**Acciones rápidas** de Inicio, **Archivo → Añadir un paquete de ligas...**, **+ Añadir...** en Mi
mundo, o suéltalo en **Importa tu mundo**, donde luego **Construir e instalar** empieza solo):

1. El programa muestra lo que hay dentro y pregunta. Un paquete de varias ligas las lista, todas
   marcadas: desmarca las que no quieras (0.2.1). Una liga que está debajo de otra del paquete
   trae también esa. En **Qué tomar** puedes desmarcar también partes del paquete (marcadores,
   equipaciones, escudos, caras ...), por ejemplo para tomar los marcadores de otro paquete.
2. Una liga con un nombre que ya tienes: el programa pregunta y la añade como `Nombre (Paquete)` (si dices que no, no se añade nada).
   Un paquete hecho sin plantillas va encima de esa liga: sus escudos y entrenadores caen en los
   clubes del mismo nombre, tus jugadores se quedan y el programa dice cuántos clubes encontró.
   Un paquete que tu mundo ya tiene (el mismo nombre) se sustituye por la versión nueva (0.1.7):
   salen las ligas, clubes y cambios de jugadores del viejo y entran los del nuevo.
3. **Construir e instalar**.

Los ids se asignan cuando cada persona construye, según lo que tiene su propio juego, así que un
paquete funciona junto a otros paquetes y junto a tus propias ligas. **Quitar de tu mundo** vuelve
a sacar un paquete, incluidos los cambios que hizo en los clubes del juego. Si un paquete cambia
un club que tu mundo ya cambia (un club NewLife, por ejemplo), un jugador que añaden los dos se
añade una sola vez, y los fichajes y bajas del paquete también entran (0.2.4).

Una liga colocada debajo de una de las ligas del juego funciona para todos los que tengan la misma
versión del juego.

### 9.1 Exportar el mundo: un mundo construido para otro PC

Un paquete necesita que la otra persona construya. Para entregar el mundo exactamente como lo
construiste, pulsa **Exportar...** en la tarjeta del mundo en **2. Mi mundo**, o **Exportar el
mundo...** en **Paso a paso, y Exportar el mundo** de la pestaña Construcción (con el mundo ya
construido). Guarda un solo `.zip`:

- `SiderAddons\livecpk\<mundo>\...`: toda la carpeta del mundo, con su **archivo de mundo**
  `fl26world.txt`. Las líneas `newfaces` / `faceapp` de ese archivo listan los jugadores nuevos
  que reciben una cara generada. Sin ellas todos los jugadores nuevos se ven iguales.
- `SiderAddons\content\kit-server\<mundo>\...` y `...\scoreboard-server\<mundo>\...`: las
  **equipaciones** del mundo (las de Kit Server de sus clubes, también las hechas con colores y
  escudos) y sus **marcadores**, cada uno con un `map.txt` / `map_competitions.txt` con solo las
  líneas de este mundo. Importa tu mundo añade esas líneas a los mapas de quien lo recibe (una
  línea suya para el mismo club se desactiva y vuelve cuando se quita el mod). Las equipaciones
  van al Kit Server que carga el juego de quien lo recibe (`content\kits` para el propio de
  SPFL26). Un club del mundo que lleva una equipación de otro pack de tu PC (Other Europe de
  SPFL26, un modpack) se lleva una copia de esa equipación, en `<mundo>\_kits\`, así que quien lo
  recibe no necesita ese pack.
- `SiderAddons\content\scoreboard-server\<mundo>\_packs\...`: los **marcadores de otros packs**
  que las líneas de mapa activadas en tu PC dan a las competiciones del mundo (los marcadores de
  un modpack para sus ligas, copas y supercopas). Van con sus líneas de mapa, apuntadas a
  `<mundo>\_packs\`, así que quien lo recibe tampoco necesita ese pack. Los temas de menú no
  forman parte de un zip de mundo: se quedan los menús del juego, aunque en tu PC esté activado
  el tema de un pack.
- `READ ME - FL26 world.txt` y `fl26worldpack.json`: lo que necesita quien lo recibe.

**Quien lo recibe necesita los módulos de Mod Studio con el paquete de caras**
(`modules\fl26regen_faces.bin`): instalar el zip en **Importa tu mundo** los pone (o **Inicio →
Instalar ahora**). Las caras salen de ese paquete, así que el zip no las lleva.

Para instalarlo, suelta el zip en **Importa tu mundo** y pulsa **Instalar el mundo**. Mod Studio
instala sus módulos, copia el mundo, pone `fl26world.txt` en `SiderAddons\modules` (donde lo lee
`fl26regen`) y pone el mundo en el juego; una versión más nueva de un mundo que tienes sustituye
a la anterior. Termina con **Listo para jugar** y una lista de comprobación final. Luego empieza
una carrera nueva de Master League. **Quitar** (en **En el juego ahora**) vuelve a sacar el mundo
y devuelve el archivo de mundo anterior.

Un modpack nombra los estadios locales de sus clubes por las carpetas del pack de estadios de
quien lo hizo. Cuando tu pack de estadios tiene un estadio en otra carpeta, Mod Studio lo
encuentra por su nombre; un estadio que no tienes se deja fuera (el club juega donde lo pone el
juego), y la comprobación final dice cuántos clubes tienen el suyo.

**Cambiar un mundo instalado.** `fl26worldpack.json` solo guarda el nombre del mundo y lo que
necesita, pero la carpeta del mundo lleva `leaguebuilder-plan.json`. Cuando Mod Studio arranca con
ese mundo en el juego y las tablas del juego desempaquetadas, crea tu mundo a partir de ese plan
y lo abre, así que quien lo recibe puede ver las ligas del mundo. Para cambiarlo y volver a
construirlo con sus propias tablas, primero pulsa **Hacerlo editable...** en Mi mundo (sección
3.1). Se parece al original, pero no es igual: vuelven las ligas, clubes, nombres, escudos,
Europa, copas, cambios de jugadores y la Conference League; no vuelven los torneos de
pretemporada, las copas de los países del juego, los nombres de las competiciones, las plazas
europeas de las ligas del juego, el orden de las ligas ni los clubes europeos de la primera
temporada. Las imágenes y las caras apuntan al PC de quien lo mandó: Build dibuja un escudo para
cada imagen que falta y dice cuáles. Mod Studio no instala encima de un mundo del mismo nombre
construido en ese PC: renombra antes ese mundo en su tarjeta.

## 10. Herramientas

**Diagnóstico** (**4. Herramientas**) — **Hacer las comprobaciones** revisa toda la configuración:
carpetas de contenido activadas pero que faltan, módulos en un orden equivocado o activados dos
veces, líneas de mapa que no apuntan a nada, el mundo del juego (pestaña **Tu mundo en el
juego**; solo debería haber un mundo activado) y el último `sider.log`. **Copiar un informe** lo
pone todo en el portapapeles para pegarlo en un mensaje de un foro o en un informe de error.

**Puntos de restauración** (**4. Herramientas**): cada archivo que el programa ha cambiado, con la
copia de antes. **Restaurar esta copia** lo devuelve a como estaba. Las copias están en
`SiderAddons\ModStudio\backups`. **Limpiar...** quita las antiguas, y siempre conserva la copia
más antigua de un archivo (la de antes de Mod Studio). Aquí también aparecen los mundos borrados
y renombrados y la copia de tu carpeta de partidas.

**Devolver Sider a antes de Mod Studio...** (Puntos de restauración, y el menú **Juego**) lo
devuelve todo: pone cada archivo que Mod Studio cambió como estaba al principio (`sider.ini`,
CommonLib, los archivos de mapa) y quita lo que trajo (sus módulos, el paquete de caras, los
mundos y mods instalados con él). No se borra nada: queda guardado en
`SiderAddons\ModStudio\reset-<time>`, y **Deshacer el último reinicio** lo vuelve a poner.

**Ajustes** (**5. Ajustes**): **Carpeta del juego**, **Carpeta de Sider** (cuando hay más de una),
**Idioma (Language)**, **Carreras de Master League** (**Cada mundo guarda sus propias carreras (la
carpeta de partidas guardadas cambia con el mundo)**, sección 3.1), **Las tablas del juego**
(**Desempaquetar las tablas del juego**, **Usar otra carpeta de tablas...**, sección 2) y **Abrir
la carpeta de ajustes del programa**.

## 11. Cuando algo va mal

| Lo que ves | Qué hacer |
|---|---|
| *sider.ini not found* | Ajustes → Carpeta del juego: elige la carpeta con `FL_2026.exe`. |
| *no hay tablas del juego* | Ajustes → Desempaquetar las tablas del juego. |
| *Acceso denegado*, o Mod Studio dice que no puede escribir en la carpeta del juego | El juego está en Program Files: pulsa **Reiniciar como administrador**, o mueve el juego a una carpeta tuya. |
| Mod Studio dice que falta una DLL de sus módulos (`fl26swiss.dll` ...) | Un antivirus se la llevó. Añade la carpeta `SiderAddons` como excepción en el antivirus y pulsa otra vez **Instalar ahora**. |
| Un mod no se ve en el juego | Diagnóstico → Hacer las comprobaciones. Puede que una carpeta de contenido más arriba en la lista tenga el mismo archivo. |
| El juego no arranca tras un cambio | Puntos de restauración → devuelve `sider.ini`, o cambia a un perfil que funcionaba. |
| La liga nueva no está en Select Team | Empieza una carrera *nueva*; las carreras antiguas mantienen sus ligas antiguas. |
| Mis carreras desaparecieron al cambiar de mundo | Están en `save_<mundo>` junto a la carpeta de partidas: activa otra vez ese mundo (sección 3.1). |
| El portero es el capitán de todos los clubes nuevos | El mundo se construyó antes de la 0.2.4: vuelve a construirlo y empieza una carrera nueva. |
| Los nombres de los clubes son los del juego | Un archivo Edit los anula (sección 8). |
| *tus ligas no mandan a nadie a Europa* | Ligas → elige la primera división → **Editar liga...** → Europa (el botón **Primera división** rellena las tres habituales), y luego vuelve a construir. |
| *la Liga Conferencia está activada, pero faltan sus tablas* | Vuelve a construir el mundo: se construyó antes de esa opción, o con ella desactivada. |
| Los pasos de Build salen en gris | Hay un mundo listo de un zip en el juego. **Activa** antes tu propio mundo, o usa **Hacerlo editable...** (sección 8.2). |
| Una cara no se ve | La carpeta debe contener `#Win\face.fpk`; vuelve a construir después de elegirla. |
| Cualquier otra cosa | Diagnóstico → **Copiar un informe**, y publícalo junto con `SiderAddons\sider.log`. |
