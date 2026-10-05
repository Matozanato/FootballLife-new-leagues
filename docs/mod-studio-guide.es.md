# FL26 Mod Studio — guía de uso

> Preguntas frecuentes (actualizar, cierres al arrancar, copas, ascensos, qué enviar cuando algo
> falla), en inglés: [faq.md](faq.md) · preguntas y ayuda en [Discord](https://discord.gg/StQqtk3G3M)

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

La ventana está en inglés. **Settings → Language → Español** la pasa a español.

## 2. Primer inicio

1. **Ajustes → Carpeta del juego**: pulsa `...` y elige la carpeta que contiene `FL_2026.exe`.
   La línea de debajo dice si se encontró `SiderAddons\sider.ini`. Sider puede tener otro
   nombre o estar un nivel más abajo (`sider\patch 1` ...); si hay varios, **Settings → Sider folder** elige con cuál trabaja el programa.
2. Si quieres ligas nuevas o cambios de jugadores: **Ajustes → Desempaquetar las tablas del
   juego**. Lee los clubes, ligas y jugadores del juego en una carpeta de trabajo (unos
   segundos). Solo hay que repetirlo tras una actualización del juego.
3. Abre **Resumen**. Muestra tu configuración de un vistazo y una lista de problemas. Haz doble
   clic en un problema para abrir la página que lo arregla.

**Actualizaciones.** Unos segundos después de arrancar, el programa pregunta a GitHub si ha salido
un FL26 Mod Studio más nuevo, y solo avisa cuando lo hay. **Descargar e instalar** baja el nuevo
zip, lo comprueba con la suma de control de la versión, cierra el programa, pone los archivos
nuevos encima de los antiguos y lo vuelve a abrir. Tus ajustes, proyectos, puntos de restauración
y el juego no se tocan. **Ayuda → Buscar actualizaciones** pregunta en cualquier momento; quita la
marca de **Ayuda → Buscar actualizaciones al iniciar** y el programa solo preguntará entonces. Si
el programa está en una carpeta donde Windows no le deja escribir (como Program Files), abre en su
lugar la página de la versión: descomprime tú el zip, o mueve el programa a una carpeta tuya.

**Créditos.** El botón **Créditos**, junto a **Ayuda**, nombra a todos los que ayudaron a hacer
Mod Studio: los testers, quienes mandaron reportes y logs, y aquellos cuyas ideas están dentro.

**¿Más de una carpeta de Sider?** Sider no tiene por qué llamarse `SiderAddons`. El programa
busca la carpeta junto a `FL_2026.exe` que contiene un `sider.ini`; si hay varias, **Ajustes →
Carpeta de Sider** elige con cuál trabaja.

## 3. Las páginas

La lista de la izquierda tiene cuatro grupos.

| Grupo | Páginas |
|---|---|
| **Gestionar** | Resumen, Instalar mods, Carpetas de contenido, Módulos Lua, Perfiles, Puntos de restauración |
| **Contenido del juego** | Estadios, Equipaciones, Balones, Comentarios, Música, Otro contenido |
| **League Builder** | NewLife Database, Ligas nuevas, Clubes nuevos, Ligas y clubes del juego, Jugadores, Paquetes de ligas, Construir |
| **Herramientas** | Diagnóstico, Ajustes |

## 4. Instalar mods

Suelta un mod descargado en **Instalar mods** (`.zip`, `.7z`, una carpeta, `.lua`, `.cpk` o
`.fl26pack`), o usa **Elegir un archivo...**.

El programa mira dentro y enumera cada parte: qué es y adónde irá.

| Parte | Qué pasa |
|---|---|
| Carpeta de contenido (livecpk) | Se copia en `SiderAddons\livecpk\<nombre>` y se añade a `sider.ini`. |
| Archivos de servidor de contenido | Se copian en la carpeta `content` del servidor. Su **archivo de mapa se combina con el tuyo**: tus líneas se quedan y se añaden las líneas nuevas del mod. Para un club que ya tienes en el mapa decide la opción junto a **Instalar**: *usar las del mod*, o *conservar las mías, añadir las del mod detrás*. |
| Módulo Lua | Se copia en `SiderAddons\modules` y se activa en el lugar correcto del orden. |
| .cpk empaquetado | Se desempaqueta en una carpeta de contenido al instalar. |
| Paquete de ligas | Se añade a tu receta de League Builder (sección 9). |
| DLL | **No se instala.** Una DLL se ejecuta con los permisos del juego; instálala solo a mano y solo de una fuente en la que confíes. |

Ponle un nombre al mod, elige si las carpetas de contenido nuevas van arriba (ganan) o al final,
marca lo que quieras y pulsa **Instalar**. La lista de abajo muestra todos los mods instalados con
el programa. **Quitar el mod** borra los archivos que añadió y devuelve los que reemplazó.

## 5. Carpetas de contenido y módulos Lua

**Carpetas de contenido** muestra cada línea `cpk.root` de `sider.ini`. Sider busca un archivo de
arriba abajo, así que cuando dos carpetas tienen el mismo archivo gana la que está más arriba.

- Marca o desmarca una carpeta para activarla o desactivarla (la línea se convierte en comentario,
  nunca se borra).
- **Arriba del todo**, **Subir**, **Bajar** cambian el orden; **Añadir carpeta...** añade una
  carpeta que ya tienes.
- Para cada carpeta se muestran el tamaño y lo que contiene (caras, equipaciones, estadios...).
- No se escribe nada hasta que pulses **Aplicar**. **Descartar** olvida los cambios.

**Módulos Lua** es lo mismo para las líneas `lua.module`. El programa conoce el orden correcto de
los módulos habituales (los servidores de contenido después de los módulos que usan) y avisa
cuando un módulo está en un lugar equivocado. Algunos módulos necesitan un ajuste de Sider (por
ejemplo, Goal Song Server necesita `match-stats.enabled = 1`); el programa dice cuál.

Los módulos de League Builder mantienen el orden en que se instalaron.

## 6. Contenido del juego: los servidores de contenido

**Estadios, Equipaciones, Balones, Música, Comentarios** y **Otro contenido** (marcadores, menús,
equipaciones arbitrales, parches de manga y tiempo) pertenecen cada uno a un servidor de
contenido. Los módulos propios de SPFL26 para equipaciones, estadios y marcadores (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) leen los mismos archivos de `content\kits`, `content\stadiums` y `content\scoreboards`; cuando el servidor no está instalado, su página edita esos (equipaciones desde 0.1.7, estadios y marcadores desde 0.1.8). Cada página tiene:

- una **línea de estado**: si el módulo está activado y si existe su carpeta de contenido;
- una pestaña por **archivo de mapa**, mostrado como tabla: qué recibe cada competición, club o
  estadio. Añade, cambia, desactiva (la línea pasa a ser un comentario) o borra filas; elige los
  elementos de la biblioteca en lugar de escribir ids. **Guardar** escribe el archivo; la copia
  de antes va a Puntos de restauración;
- la **Biblioteca**: lo que hay en la carpeta de contenido del servidor, con imágenes donde las
  hay. Se marcan los elementos que ninguna línea del mapa usa y las líneas que apuntan a
  elementos que faltan;
- los **Ajustes** del servidor, donde los tiene (estadio, balón, marcador favorito ...).

El programa comprueba las tablas antes de guardar: un número donde va un número, sin comas dentro
de un nombre, un elemento que existe.

**Importar equipaciones...** (0.1.8, en la página *Kits*): equipaciones para muchos clubes a la vez. Elige una carpeta de equipaciones listas de kit-server -- una carpeta por club, con `p1`, `p2`, `g1` ... y `order.ini`, con el nombre del club (`Dinamo Zagreb`) o su ID de equipo (`2215`). La lista muestra cada emparejamiento con una marca; desmarca uno erróneo antes de **Aceptar**. Las equipaciones se copian a la biblioteca de kit-server (`Liga\Club`, como las tenía la carpeta) y cada club recibe una línea en `map.txt`; **Save** la escribe. Un club que ya tiene línea la conserva, salvo que esté marcado **Reemplazar las equipaciones ya puestas**. Las equipaciones de un club nuevo del League Builder van por el ID que le dio Build: haz Build del mundo y déjalo activado primero. Mod Studio no crea equipaciones: las texturas (`.ftex`) vienen listas de un creador de equipaciones.

## 7. Perfiles

Un perfil recuerda qué carpetas de contenido y módulos están activados, y en qué orden. Ten uno
para Master League, otro para jugar online, otro para pruebas:

- **Guardar la configuración actual...** guarda con un nombre lo que está activado ahora.
- **Cambiar a este** pone esa configuración en `sider.ini` (el `sider.ini` antiguo va a Puntos
  de restauración).
- **Actualizar con la configuración actual** sobrescribe el perfil.

## 8. League Builder: ligas, clubes y jugadores nuevos

League Builder añade ligas nuevas al juego y cambia las del propio juego. Lo que crea es un
**mundo**: una carpeta de contenido llamada `_FL26...` que el juego lee mientras está activada.

**Ligas nuevas → Añadir liga**

| Campo | Qué significa |
|---|---|
| **Nombre** | El nombre de la liga en el juego. No puede haber dos iguales. |
| **País** | Da la bandera y el lugar donde aparece la liga. Un país para el que el juego no tiene liga recibe un título propio. |
| **Clubes** | De 10 a 24. |
| **Formato** | *Todos contra todos*, de 1 a 4 veces, *se divide en dos (estilo escocés)* o *Apertura y Clausura*: dos torneos por temporada (septiembre a principios de enero, enero a mayo), cada uno desde cero puntos, luego una liguilla de 8 o 4 clubes (o ninguna). La tabla de toda la temporada decide ascensos y descensos. 18 clubes como máximo. Una liga dividida tiene 46 jornadas como máximo, antes y después de la división juntas (16 clubes dos veces son 30, así que su grupo más grande dos veces puede tener 8 clubes, 14 jornadas). Por ahora, solo una liga por país puede dividirse o jugar Apertura/Clausura. |
| **División** | *(primera división)*, o la liga que tiene encima: otra liga nueva o una del juego. Para poner una liga nueva bajo otra liga nueva en un paso: selecciónala y pulsa **Añadir división inferior** (toma el país, el número de clubes, el formato y los ascensos/descensos de la liga de arriba; solo falta el nombre). |
| **Asc. / desc.** | Cuántos clubes cambian de sitio con la liga de arriba al final de la temporada. |
| **Temporada** | Solo para la primera división de un país nuevo: *agosto a mayo* (por defecto) o *febrero a diciembre*, como Brasil, Japón o Arabia Saudí: los clubes suben y bajan en Año Nuevo, y las divisiones de abajo la siguen. Todavía no con división en grupos, Apertura/Clausura, copa nacional ni copa de la liga. |
| **Europa** | Solo para primera división: qué puesto de la liga va a qué competición europea. **Primera división: 1.º fase previa UCL, 2.º UEL, 3.º UECL** rellena las tres habituales (*... (fase previa)* son los play-offs de agosto, ver 8.2); **Añadir plaza**, **Quitar plaza** y **Borrar** para todo lo demás. Cada puesto una sola vez, y solo puestos que la liga tiene. Por debajo de 1 el puesto dice **Campeón de copa** (0.1.7): el campeón de la copa del país (un país nuevo necesita **Copa nacional**) -- y si el campeón ya tiene plaza europea por la liga, la plaza baja por la liga al siguiente club, como hace la UEFA. Una liga del juego también puede tenerla (*Plazas europeas de las ligas del juego*). Déjalo vacío para una categoría inferior. La plantilla sigue al país: Asia recibe la AFC Champions League y la AFC Champions League Two, Sudamérica la Libertadores y la Copa Sudamericana, África la CAF Champions League y la Copa Confederación CAF. Esas cuatro copas que el juego no tiene se construyen con el mundo (sección 8.2). Una plaza de *clasificación a la Libertadores* ocupa el sitio de un club del juego en la ronda previa (el último del país con más clubes en ella), como mucho seis de sus ocho plazas; **Comprobar el plan** dice qué ligas se quedan fuera pasado ese número. |
| **Logo** | Cualquier imagen (un PNG con fondo transparente queda mejor). Vacío: se dibuja uno por ti. |
| **Bandera del país** | Tu propia imagen de la bandera del país, estirada al marco de las banderas del juego. Sustituye la bandera de ese país en todo el juego (Select Team, nacionalidad de los jugadores, el encabezado del país en Database > Competition Info) mientras el mundo esté activo. Vacío: la bandera del juego. |
| **Copa** | Solo primera división. **Copa nacional**: el país tiene su propia copa, con el nombre que le des (vacío: `<liga> Cup`). El juego llena la copa de un país con su primera división y la división de debajo, y el tamaño de la copa sigue la fila Copa nacional de los Límites (8.3): el mayor tamaño que la pantalla de la copa dibuja y que cabe, así que 22 clubes dan una copa de 20, primero la primera división. Con más de 44 clubes la copa se queda solo con la primera división. Una segunda división nueva bajo un país que el juego ya tiene (Alemania, Rusia ...) también entra en la copa de ese país, detrás de los clubes de primera, cuando las rondas de la copa encajan con el número de clubes. Una nueva tercera división o inferior (League One bajo la Championship) deja la copa del país a las dos primeras divisiones del juego, como en el juego. **Supercopa**: además, una supercopa a partido único antes de la temporada, el campeón contra el ganador de la copa. |
| **Copa de la liga** | Solo primera división. Una eliminatoria de 16, 8 o 4 clubes de esta liga y la de abajo, por posición, el más fuerte contra el más débil: ida y vuelta en cada ronda, la final a un partido, de septiembre a diciembre. Los clubes que pasan de 16, 8 o 4 juegan antes una ronda previa (0.1.7): los últimos puestos, el más fuerte contra el más débil, ida y vuelta el 4 y el 7 de septiembre; los ganadores ocupan los últimos puestos de la copa, contra sus clubes más fuertes. Una liga de 20: del 1.º al 12.º directos a octavos, del 13.º al 20.º en cuatro eliminatorias previas. Ponle un nombre o déjalo vacío (`<liga> League Cup`). |
| **Logos de las copas** | Una imagen para la copa nacional, la supercopa, la copa de la liga y los playoffs del Apertura/Clausura, cada una por separado. Vacío: se dibuja un emblema con las iniciales de la copa. |
| **Solo exhibición -- no está en la Liga Máster** | Para Kick Off y partidos amistosos: una liga histórica, leyendas y cosas así. Sus clubes nunca juegan una temporada de Liga Máster, así que la liga va sola: sin división arriba ni abajo, sin plazas europeas, sin copas. Aun así aparece en la lista de equipos de la Liga Máster; elige tu club en otra liga. |
| **Formación** | Cómo forman los clubes de la liga. Elige una de las formaciones que usan los clubes del juego (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; la lista dice cuántos clubes del juego la usan): cada club nuevo recibe una copia de la táctica de un club del juego con esa formación, y al construir se le coloca su mejor once. Vacío: la del juego, un 4-2-3-1 fijo. Un club puede tener la suya (**Editar club**). |

**Nombre del mundo** (en la misma página) debe empezar por `_FL26`. Después de **Construir**, la
columna **ID de la liga** muestra el id de competición de cada liga en el juego, el mismo que lleva
su archivo de logo.

**Torneos de pretemporada** (botón en la misma página): eliminatorias amistosas de 4 u 8 clubes invitados en julio, antes de la temporada, emparejados en el orden en que los pones (el primero contra el segundo ...). Un club es de una liga nueva o un club del juego (su id); al menos uno tiene que ser de una liga nueva, y su país organiza el torneo. Una carrera empieza en agosto, así que el primero se juega en la segunda temporada. Cada torneo puede tener su **Logo**; vacío: se dibuja uno.

**Copas de los países del juego** (botón en la misma página): una copa de la liga -- la Carabao Cup, por ejemplo -- para ligas del juego. Marca **Copa de la liga** junto a una liga: 16 clubes de ella y de la de abajo, por posición (los que pasan de 16, por una ronda previa a principios de septiembre, 0.1.7), un partido por ronda de finales de septiembre a diciembre, en días que el calendario de ligas y copas del juego deja libres. **Supercopa**, el campeón contra el ganador de la copa a finales de julio, solo donde el juego no tiene (Brasil, Chile, Escocia, Grecia, EE. UU.); una carrera nueva aún no tiene ganador de copa, así que la primera se juega el segundo verano. Nombre vacío: el nombre de la liga y *League Cup* / *Super Cup*.

**Plazas europeas de las ligas del juego** (botón en la misma página): qué puestos de la Premier League, LaLiga, la Serie A ... van a qué competición europea. La lista muestra las plazas del juego; marca **Plazas propias para esta liga** para cambiarlas. Una liga sin marcar mantiene las del juego, una liga marcada sin filas no manda a nadie.

**Ranking UEFA** (misma página, 0.1.7): todas las ligas europeas del mundo -- las del juego y tus
primeras divisiones nuevas -- en una lista, el país más fuerte primero. Arrastra una liga (o
**Subir** / **Bajar**) para cambiar el orden, desmárcala para que no tenga plaza europea, y
**Orden de la UEFA** devuelve la lista al ranking de asociaciones de la UEFA para 2026-27. A la
derecha se ve lo que recibe cada liga, y **OK** lo escribe: las plazas de la clave de la UEFA para
2024-27 -- el puesto 1 tiene cinco plazas de Champions League, el 6 dos y una de play-off, el 30 una
en la segunda ronda previa de la Champions League, etcétera, incluida la plaza del campeón de copa
en la Europa League. Un mundo nunca tiene los 55 países de la UEFA, así que las plazas de los
puestos que faltan van por turnos a los siguientes clubes de las ligas más fuertes, una ronda cada
vez, y todas las competiciones siguen llenas: con doce ligas, el 6.º, 7.º y 8.º de Inglaterra van a
la fase previa de la Champions League, por ejemplo. Después de la liga 30 no queda ninguna plaza, y
la lista lo dice. Las plazas de fase previa van a las rondas en el orden de la clave, el país más
fuerte a la ronda más cercana a la fase de liga. Después aún puedes cambiar a mano las plazas de
cualquier liga (*Europa* en la liga, *Plazas europeas de las ligas del juego*): Construir usa las
plazas, no el ranking.

**Plazas sudamericanas** (misma página, 0.1.7, solo lectura): para cada liga sudamericana, las
cuatro del juego y las tuyas, qué puestos van a la Copa Libertadores, a su fase previa y a la Copa
Sudamericana. Las plazas de Libertadores de las ligas del juego son las del juego (Brasil 1.º-4.º y
el campeón de la Copa do Brasil, fase previa 5.º-6.º, etcétera -- lo mismo que muestra el
Competition Info del juego); la Copa Sudamericana es de Mod Studio, así que la lista muestra
cuántos clubes manda a ella cada liga del juego con tus plazas dentro: primero tus ligas, luego
Brasil, Argentina, Chile y Colombia, un club cada una por turnos hasta llegar a 32. Un club que ya
está en la Libertadores o en su fase previa deja su sitio al siguiente de su liga. **Comprobar el
plan** escribe la misma lista siempre que el mundo tiene una plaza de Libertadores o Sudamericana.

**Nombres de las competiciones** (botón en la misma página): un nombre y un logo nuevos para las copas, supercopas y competiciones continentales del juego -- la FA Cup, la Champions League, la Libertadores ... -- y para las copas continentales que construye el mundo (CAF Champions League, Copa Confederación, AFC Champions League Two, Copa Sudamericana, Supercopa CAF). Todas las fases de la competición reciben el nombre. Vacío: el del juego. Las ligas del juego se renombran en *Game's leagues and clubs*.

**Clubes nuevos**: elige la liga y luego **Editar club** (nombre, abreviatura, escudo), **Pegar
nombres...** o **Cargar nombres de un archivo...**. Un nombre vacío pasa a ser `<liga> 01`,
`<liga> 02` ...; un club sin escudo recibe un escudo con número. Las equipaciones se toman
prestadas de los clubes del propio juego. Una equipación así es con licencia, y el modo Edit no
deja cambiarla ("You cannot edit this strip"): marca **Equipaciones que puedes editar en el juego**
en la página Construir y los clubes nuevos no toman ninguna prestada; cada uno lleva una equipación
sencilla que Edit > Teams > Strip cambia como la de cualquier otro club, Paste Image incluido.
Los nombres conservan sus letras (FK Željezničar); la abreviatura de tres letras no lleva tildes
ni marcas, como en el juego, así que ahí Č, Ž, Đ pasan a C, Z, D. Después de **Construir**, la
columna **ID del club** muestra el id de cada club en el juego.

**Entrenador**: en **Editar club** de un club nuevo puedes poner el nombre de su entrenador. Vacío: uno numerado (`FL M0001` ...). **Foto del entrenador** debajo le da un retrato (lo mismo que **Retrato del entrenador...** en la página Jugadores); *Ligas y clubes del juego* > **Editar club** la tiene también para los clubes del juego.

**Formación**: en **Editar club** de un club nuevo puedes darle una formación propia; *Como la liga* mantiene la de la liga. El campo bajo la lista muestra dónde juega cada uno.

**Estadio local** (0.1.7): en **Editar club**, un estadio de la biblioteca de Stadium Server para el club; la ranura y el nombre se rellenan desde la carpeta, cambia el nombre si quieres. Se escribe en el `map_teams.txt` de Stadium Server al activar el mundo (y al construir otra vez el mundo activo), así que nunca hay que buscar el id de un club nuevo. Una línea tuya para el mismo club se desactiva mientras tanto, y se activa otra vez cuando el club ya no tiene estadio aquí. *Ligas y clubes del juego* > **Editar club** lo tiene también para los clubes del juego. Tiene que estar instalado Stadium Server (página *Estadios*) o el módulo de estadios propio de SPFL26 (`common\stadiums.lua` con su carpeta `content\stadiums`): desde 0.1.8 Mod Studio escribe ahí cuando Stadium Server no está instalado.

**Clubes que el juego ya tiene.** Un puesto de una liga nueva puede tener uno de los clubes del
juego en lugar de uno nuevo: selecciona el puesto, luego **Club del juego...**, y busca por nombre
o ID del equipo (**Solo clubes sin liga** acorta la lista). El club conserva su nombre, escudo,
equipaciones, entrenador y jugadores, y juega solo en tu liga. Si juega algo en el juego (una
liga, una copa, la Europa League ...), eliges quién ocupa allí su lugar: un club del juego que no
juega nada, o un club nuevo con el nombre que le des. **Conserva sus plazas en competiciones continentales** (0.1.8, #84) le deja seguir jugando la Champions League, la Libertadores o la AFC Champions League en la que está: un club que en el juego solo juega el continente simplemente se muda, y uno que también juega una liga del juego entrega solo la liga y las copas al club que elijas. Desde la segunda temporada, las plazas de tu liga deciden quién va. Un torneo de pretemporada (las *Pre-season friendly Cups* de SPFL26) no cuenta: el club lo sigue jugando, como los clubes de la Premier League (0.1.7). **Editar club** en un club del juego cambia su nombre, escudo, foto del entrenador y estadio, como en *Ligas y clubes del juego* (0.1.7). Así ninguna competición del juego cambia su
número de clubes; las ligas del juego solo mantienen sus fechas con el número para el que se
hicieron. Las selecciones, los equipos clásicos y por defecto y los clubes con menos de 18
jugadores no se pueden elegir. **Club nuevo aquí** devuelve el puesto a un club nuevo. El club ya
no aparece en los grupos *Other ... clubs* de la Master League.

**Club NewLife...** (0.1.8, #83) pone clubes de la NewLife Database, con sus plantillas, en el puesto seleccionado y los siguientes: marca uno o más clubes (busca por club o por liga) y cada uno ocupa su puesto en orden. Así una liga hecha a mano recibe clubes reales. Abre antes la NewLife Database en la página *NewLife*.

**Insertar club** y **Quitar club** añaden un puesto antes del club seleccionado o lo quitan (de 10
a 24 clubes); nombres, escudos, entrenadores y cambios de jugadores van con sus clubes. Revisa las
plazas europeas de la liga y vuelve a **Construir**. Cualquier cambio en los clubes de una liga
necesita una **carrera nueva**.

**Mover a otra liga...** (0.1.7) lleva el club nuevo seleccionado al final de otra liga nueva, con su nombre, abreviatura, escudo, entrenador, formación, equipaciones, id de NewLife y cambios de jugadores; la liga que deja se queda con un club menos. Un club del juego se mueve con **Club del juego**: quítalo de una liga y ponlo en la otra.

**Ligas y clubes del juego**: nombres, logos y escudos nuevos para lo que el juego ya tiene.

**Importar escudos...** (0.1.8, en esta página y en *Clubes nuevos*): escudos para muchos clubes a la vez. Elige una carpeta de imágenes; cada una se empareja con un club por el nombre del archivo -- el nombre del club (`Alianza Lima.png`, `alianza_lima_r_l.png`) o su ID de equipo (`2287.png`, el `e_2287_r.png` de los packs de escudos). La lista muestra cada emparejamiento con una marca; desmarca uno erróneo antes de **Aceptar**. Un club que ya tiene escudo lo conserva, salvo que esté marcado **Reemplazar los escudos ya puestos**. Las imágenes se quedan en esa carpeta y Build las lee de ahí, así que guárdala. (Emparejar por nombre es una idea del script de escudos de Xxspedd.)

**Intercambiar liga con un club...** (0.1.7): dos clubes de las ligas del juego intercambian sus plazas -- un ascendido por un descendido, un club de la liga de un país por uno de otro. Cada uno ocupa las plazas del otro en la liga, las copas y las competiciones europeas, así que cada liga del juego mantiene su número de clubes. Un club que juega en una liga nueva de la receta no puede intercambiarse también. **Deshacer cambios del club** quita el intercambio. Luego **Construir** otra vez y empieza una carrera nueva.

> **Archivo Edit.** Si la carpeta de partidas guardadas del juego tiene un archivo Edit
> (`EDIT00000000`), este anula los nombres de los clubes. Muévelo a otro sitio para ver tus nombres.

### Jugadores

**Jugadores** cambia la plantilla de cualquier club: los clubes nuevos de la receta y los del
propio juego. Elige un club (o pulsa **Jugadores** en Clubes nuevos) y luego un jugador:

- **nombre**, **dorsal**, **posición** y las posiciones en las que puede jugar (A = natural,
  B = puede jugar ahí), pie hábil, altura, peso, edad, nacionalidad, estilo de juego;
- todas las **capacidades** y **habilidades** (los nombres son los del propio juego, en inglés);
- **Valoración**: la valoración de la lista, hecha de las capacidades en las que se apoya la
  posición. Al cambiarla, cada capacidad del jugador se mueve lo mismo. Un jugador de un club
  nuevo no tiene nombre hasta que la construcción le da uno con número (FL P00001 ...);
  escribe uno en **Nombre** para darle el tuyo;
- **Cara**: **Elegir...** una carpeta de cara (sección 8.1). **Borrar** devuelve la cara del juego.
  Un jugador nuevo sin ella recibe una cara del paquete de caras de regens que va con su
  nacionalidad, con su retrato (0.1.5.5, con los módulos instalados);
- **Retrato**: **Elegir...** una imagen (PNG o JPG) para el retrato pequeño del jugador en las listas
  de la plantilla, sin cara propia. El Build la deja en 180 x 180; tiene prioridad sobre el retrato de
  una carpeta de cara;
- **Subir en el orden / Bajar en el orden**: el orden de la plantilla. Los primeros once son
  titulares;
- **Añadir jugador** (una copia del jugador que elijas, con un id nuevo; solo clubes del juego),
  **Quitar del club** (un club nuevo conserva al menos 18 jugadores);
- **Mejor once** pone al jugador más fuerte en cada puesto; **Nivel de la plantilla...** sube o
  baja cada capacidad de toda la plantilla;
- **Campo** (clubes nuevos): los once primeros en la formación del club. Elige un jugador en la
  lista y haz clic en un puesto para ponerlo ahí; quien estaba ahí toma su lugar en el orden de la plantilla;
- **Exportar CSV... / Importar CSV...**: edita una plantilla en una hoja de cálculo. Primero
  exporta, cambia las celdas y vuelve a importar las mismas columnas.
- **Importar una plantilla desde una tabla...**: cualquier tabla de jugadores se convierte en
  la plantilla del club -- escrita a mano, una lista copiada de una web, una exportación de
  Football Manager o EA FC. Las columnas se reconocen por su nombre (nombre, posición, edad o
  fecha de nacimiento, nacionalidad, altura, pie, dorsal, valoración general y cualquier
  valoración) y se muestran para corregir la que esté mal. Lo que la tabla no tiene sale de
  los jugadores del juego de la misma posición y valoración; las valoraciones 1-20 de Football
  Manager se estiran al 40-99 del juego. Los jugadores de la tabla ocupan las plazas del club
  en orden de plantilla: un club nuevo mantiene sus 30 plazas (con menos jugadores, los demás
  se van, hasta 18), un club del juego gana o pierde jugadores para cuadrar.

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
  filas anula el traspaso. Un club tiene como mucho 40 jugadores.
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
- **Retrato del entrenador...**: un PNG o JPG para el entrenador del club. El Build lo deja en
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

**Construir**:

0. **Instalar los módulos** — una vez, y de nuevo tras una versión nueva del programa. Los
   archivos que reemplaza se guardan en `SiderAddons\modules\before-builder-1\`.
1. **Comprobar el plan** — qué se va a crear; no se escribe nada.
2. **Construir el mundo**.
3. **Activarlo** — lo convierte en el mundo activo en `sider.ini`.
4. Inicia el juego, vuelve y pulsa **Tras iniciar: comprobar**. Lee `sider.log` y dice, módulo a
   módulo, si el mundo se ha cargado.

**Incluir la Liga Conferencia** (en la página Construir, activado por defecto) construye también
la Liga Conferencia: una fase de liga de 36 clubes y un play-off en febrero, como las otras dos.
La Liga de Campeones y la Liga Europa reciben su fase de liga de 36 y su play-off de febrero en
cualquier caso. Desactivado: sin Liga Conferencia. (Mod Studio 0.1.3 y anteriores dejaban la Liga de Campeones
y la Liga Europa en los grupos de cuatro del juego cuando estaba desactivado, y el mod no puede
llevarlos -- se rompían; Comprobaciones marca ese mundo: vuelve a construirlo.) **Logo de la
Conference League** al lado: tu propia imagen para ella; vacío: se dibuja un emblema UECL (el juego
no tiene ninguno). **Nombre de la Conference League** debajo: cómo la llama el juego, *FL Conference
League* si está vacío (escribe *UEFA Conference League* si quieres); un nombre nuevo necesita
construir el mundo otra vez. Los dos los usa también **Solo las nuevas copas europeas...**.

> **Plazas europeas.** Las plazas que das a tus ligas van después de las que tienen las ligas del
> propio juego. Cada competición admite 36 clubes; las plazas más allá de la 36.ª no reciben nada,
> y **Comprobar el plan** lo avisa. Las ligas nuevas sin plazas no mandan a nadie a Europa, y
> Resumen avisa de ello. Los campeones van primero: los ganadores de la Champions League y de la
> Europa League ocupan dos de las plazas directas de la Champions League, y el de la Conference League
> una de la Europa League. El sorteo de la fase de liga sigue las reglas de la UEFA: ningún club
> se enfrenta a un club de su propio país, y como mucho dos de sus rivales son de un mismo
> país distinto.
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

Después **empieza una nueva carrera de Master League** (o Become a Legend). Las ligas nuevas están
bajo su país en Select Team y Kick Off. En las listas de Kick Off y Edit un país asiático nuevo va
antes de *Other Clubs (Asia)*, uno sudamericano junto a los del juego (después de Colombia, antes
de la MLS, 0.1.7), uno de la CONCACAF después de la MLS, y los africanos y de Oceanía
(el juego no tiene sección para ellos) después de Asia.

> **Copas de otros continentes.** Cuando tus ligas mandan clubes a la CAF Champions League, la
> Copa Confederación CAF, la AFC Champions League Two o la Copa Sudamericana, **Construir**
> crea también esas copas. Cada una tiene 32, 16, 8 o 4 clubes: primero las plazas de tus ligas,
> luego la completan las ligas del juego de ese continente (Asia y Sudamérica). Con 8 o más se
> juegan grupos de cuatro y luego eliminatorias; con menos de 8, solo eliminatorias. Se llenan a
> finales de agosto, con las tablas de las ligas. Un club que ya juega la Copa Libertadores, su
> fase previa o la AFC Champions League no entra en su sorteo. Una copa de la CAF con menos de 4
> plazas toma primero las plazas de la siguiente copa de la CAF (con dos y dos, la CAF Champions
> League se queda las cuatro), y luego los siguientes puestos de tus ligas. **Supercopa de la
> CAF** (página Construir, activada por defecto) enfrenta a los ganadores de las dos copas de la
> CAF en un partido a finales de julio, desde la segunda temporada de la carrera.

> **Las partidas guardadas pertenecen a un mundo.** Una carrera guardada con un mundo activado
> necesita ese mismo mundo para cargarse.

**Archivo → Guardar receta** guarda todo en un archivo `.json`; **Abrir receta** lo recupera.
**Construir** también guarda una copia de la receta en
`%APPDATA%\FL26ModStudio\recipes\<mundo>.json`, y Mod Studio abre la última receta al
iniciarse, así que cerrarlo sin guardar no pierde nada de lo construido.

**Solo las nuevas copas europeas...** (página Construir) construye un mundo solo con la nueva
Champions League y Europa League -- fase liga de 36 y el play-off de febrero -- y la Liga Conferencia cuando **Incluir la Liga Conferencia** está marcado. Sin ligas nuevas; los clubes y ligas
del juego quedan como están y tu receta no cambia. Pide un nombre de mundo (`_FL26Euro` por
defecto), lo construye y ofrece activarlo. Solo puede estar activado un mundo, así que sustituye a
un mundo con ligas nuevas: un mundo con ligas nuevas ya tiene el formato nuevo.

> **Ligas de exhibición y Master League.** Una liga marcada *Solo exhibición* nunca juega una
> temporada de Master League, pero el juego tiene una sola lista de equipos para Kick Off y Liga
> Master, así que sus clubes siguen apareciendo al elegir club para una carrera nueva. No empieces
> una carrera con uno de ellos. **Comprobar el plan** y **Construir** lo avisan.

### 8.3 Límites

| | |
|---|---|
| Ligas nuevas por mundo | 39 |
| Clubes por liga | 10 – 24 |
| Clubes nuevos en total | 793 |
| Veces que se enfrentan los clubes | 1 – 4 |
| Ligas que se dividen | 2 por mundo |
| Divisiones en un país | hasta la 7.ª |
| Jugadores por club nuevo | 30 al principio; quita hasta dejar 18; con fichajes, hasta 40 |
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
2. **League Builder > NewLife Database > Abrir NewLife Database...** y elige esa carpeta. La
   lista muestra todas las ligas de esas partes: país, clubes, clubes que el juego ya tiene
   (*En el juego*), jugadores y nivel. Haz clic en una liga para ver sus clubes.
3. Selecciona una o varias ligas (Ctrl o Shift para más) y pulsa **Añadir a la receta**. Cada una
   se convierte en una liga nueva con sus clubes y sus plantillas, primera división de su país.
   Cambia su división, formato, plazas europeas y lo demás en *Ligas nuevas*, como cualquier otra.
4. **Construir**, activa el mundo y empieza una carrera nueva (sección 8.2).

- **Tu propia composición** (0.1.7): desmarca un club en la lista de la derecha para dejarlo
  fuera, y **Añadir un club de otra liga...** trae clubes de cualquier liga de la base -- la
  primera división de esta temporada es la del año pasado con dos ascendidos, por ejemplo. La
  fila de la liga lleva un `*`. Un club solo puede estar en una liga de la receta.
- Una liga admite de 10 a 24 clubes, sus clubes nuevos y los del juego juntos; las demás salen en gris. La línea de abajo cuenta los clubes
  nuevos de la receta frente a los 793 que admite un mundo.
- Los clubes que el juego ya tiene entran en la liga nueva como clubes del juego (sección 8),
  en sus últimos puestos, con su nombre, escudo, equipaciones y jugadores. Uno que además juega
  una competición del juego (el Basilea y el Young Boys juegan la Europa League) necesita el club
  que ocupa su lugar allí: *Clubes nuevos*, elígelo, **Club del juego**. Hasta entonces Build
  dice cuáles son.
- Un jugador que el juego ya tiene (el mismo jugador con el mismo nombre, por ejemplo Urbański en
  el Górnik en el juego y en el Legia en NewLife) se va al club NewLife en vez de crearse por
  segunda vez (0.1.7): conserva su cara, nombre e ID y toma la posición y las valoraciones de
  NewLife. Se queda donde está si su club antiguo bajara de 18 jugadores o si una liga anterior ya lo
  tiene; entonces queda fuera del club de NewLife, sin copia (0.1.7.2).
- Un club NewLife recibe un ID de mundo propio (0.1.7.2), en el bloque que el juego lee para los
  clubes, detrás de los ID que el constructor da a los suyos. La columna **ID de club** de la
  página Clubes nuevos lo muestra, y el `map.txt` del Kit Server va con él. Un mundo hecho antes
  de 0.1.7.2 hay que construirlo de nuevo y empezar una carrera nueva para que las equipaciones
  le sigan.
- **Una versión más nueva de NewLife** (0.1.8): pon sus partes en una carpeta (sin mezclarlas con
  las antiguas), **Abrir NewLife Database...** en esa carpeta y pulsa **Actualizar mis ligas a esta
  versión**. Cada liga añadida desde una versión anterior aparece con lo que cambia y una casilla
  **Mantener mis clubes**: marcada, la liga mantiene sus clubes; sin marcar, recibe los clubes que
  tiene en la nueva versión. En los dos casos las plantillas vienen de la nueva versión, y la liga
  mantiene su nombre, división, formato, plazas europeas y copas. Los cambios de jugadores hechos
  en *Jugadores* para esos clubes se reemplazan. Después Build y carrera nueva.
- **Las propias ligas del juego en la temporada de NewLife** (0.1.8): con una NewLife Database
  abierta, pulsa **Llevar las ligas del juego a esta temporada...**. Cada liga del juego que tiene
  la versión aparece con lo que le pasa, cada una con su casilla. Un club que subió o bajó entre
  dos ligas del juego intercambia su sitio con uno que va en sentido contrario (el Burnley a la
  Championship, el Coventry a la Premier League), como *Intercambiar liga con un club...*. Un club que
  bajó fuera de las ligas del juego (el Leicester a la League One) pasa a ser el club que subió en
  su lugar (el Bolton): nombre, nombre corto, escudo y plantilla; su equipación, estadio y
  entrenador se mantienen. Cada club de las ligas marcadas recibe su plantilla de NewLife: los
  jugadores que el juego tiene llegan desde su club antiguo, los que no tiene se añaden, el resto
  se va como agentes libres. Las ligas mantienen su número de clubes, su formato y sus copas. Los
  clubes que ya cambiaste a mano (un intercambio, un nombre, un club de una liga nueva, cambios de
  jugadores) se quedan como están. Hacerlo de nuevo con una versión más nueva reemplaza lo que hizo
  la anterior; **Deshacer las ligas del juego** lo quita todo. Build y carrera nueva.
- Un club NewLife recibe un escudo en forma de blasón con sus colores y la equipación del juego
  de colores más parecidos, hasta que le pongas los tuyos (**Editar club**).

## 9. Paquetes de ligas: comparte una liga entera

Un modder crea una liga una vez — clubes, nombres, escudos, logos, plantillas, caras — y comparte
**un solo archivo `.fl26pack`**. Cualquiera lo añade a su propia receta y construye.

**Crear un paquete** (Paquetes de ligas → **Crear un paquete...**, o Archivo → Crear un paquete de
ligas):

1. Nombre, autor, versión y una descripción corta.
2. Marca las ligas que van dentro (**Seleccionar todo** / **No seleccionar ninguno** encima de
   la lista). Una liga que está debajo de otra liga nueva debe ir con ella.
   Un paquete que la receta ya tiene (el mismo nombre) se sustituye por la versión nueva (0.1.7):
   salen las ligas, clubes y cambios de jugadores del viejo y entran los del nuevo.
3. Si quieres, **también mis cambios en las ligas, clubes y jugadores del propio juego**.
4. **Qué va dentro** (0.1.8): todo viene marcado; desmarca lo que no quieras compartir -- **Plantillas**,
   **Caras y retratos de jugadores**, **Escudos y logos de ligas**, **Entrenadores**, **Colores de las
   equipaciones**, **Estadios locales** (la línea de Stadium Server, no el estadio en sí). Un paquete sin
   plantillas va encima de una base que se actualiza sola, como NewLife, sin devolver las plantillas antiguas.
5. Guarda. El archivo lleva las imágenes y las caras, no rutas de tu ordenador.

**Añadir un paquete** (Paquetes de ligas → **Añadir un paquete...**, Archivo → Añadir un paquete de
ligas, o suéltalo en Instalar mods):

1. El programa muestra lo que hay dentro y pregunta.
2. Una liga con un nombre que ya tienes se añade como `Nombre (Paquete)`.
   Un paquete hecho sin plantillas va encima de esa liga: sus escudos y entrenadores caen en los
   clubes del mismo nombre, tus jugadores se quedan y el programa dice cuántos clubes encontró.
3. **Guardar receta** y luego **Construir**.

Los ids se asignan cuando cada persona construye, según lo que tiene su propio juego, así que un
paquete funciona junto a otros paquetes y junto a tus propias ligas. **Quitar de la receta** vuelve
a sacar un paquete, incluidos los cambios que hizo en los clubes del juego.

Una liga colocada debajo de una de las ligas del juego funciona para todos los que tengan la misma
versión del juego.

## 10. Herramientas

**Diagnóstico — Hacer las comprobaciones** revisa toda la configuración: carpetas de contenido
activadas pero que faltan, módulos en un orden equivocado o activados dos veces, líneas de mapa que
no apuntan a nada, mundos de League Builder (solo debería haber uno activado) y el último
`sider.log`. **Copiar un informe** lo pone todo en el portapapeles para pegarlo en un mensaje de un
foro o en un informe de error.

**Puntos de restauración**: cada archivo que el programa ha cambiado, con la copia de antes.
**Restaurar esta copia** lo devuelve a como estaba. Las copias están en
`SiderAddons\ModStudio\backups`. **Limpiar...** quita las antiguas.

## 11. Cuando algo va mal

| Lo que ves | Qué hacer |
|---|---|
| *sider.ini not found* | Ajustes → Carpeta del juego: elige la carpeta con `FL_2026.exe`. |
| *no game tables* | Ajustes → Desempaquetar las tablas del juego. |
| Un mod no se ve en el juego | Diagnóstico → Hacer las comprobaciones. Puede que una carpeta de contenido más arriba en la lista tenga el mismo archivo. |
| El juego no arranca tras un cambio | Puntos de restauración → devuelve `sider.ini`, o cambia a un perfil que funcionaba. |
| La liga nueva no está en Select Team | Empieza una carrera *nueva*; las carreras antiguas mantienen sus ligas antiguas. |
| Los nombres de los clubes son los del juego | Un archivo Edit los anula (sección 8). |
| *tus ligas no mandan a nadie a Europa* | Ligas nuevas → Editar la primera división → Europa (el botón **Primera** rellena las tres habituales), y luego vuelve a construir. |
| *la Liga Conferencia está activada, pero faltan sus tablas* | Vuelve a construir el mundo: se construyó antes de esa opción, o con ella desactivada. |
| Una cara no se ve | La carpeta debe contener `#Win\face.fpk`; vuelve a construir después de elegirla. |
| Cualquier otra cosa | Diagnóstico → **Copiar un informe**, y publícalo junto con `SiderAddons\sider.log`. |
